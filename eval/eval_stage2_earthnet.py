"""Evaluate a Stage2 checkpoint on an EarthNet split with ObsWorld losses."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
import yaml
from torch.utils.data import DataLoader

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import EarthNet2021Config, EarthNet2021Dataset, collate_earthnet2021
from eval.earthnet_standard_metrics import (
    OFFICIAL_EARTHNET2021_PROTOCOL,
    EarthNetScoreAccumulator,
)
from eval.forecast_metrics import ForecastMetricAccumulator
from eval.stage2_evaluation_provenance import (
    build_stage2_evaluation_provenance,
    json_safe,
    verify_checkpoint_contract,
    write_evaluation_sidecar,
)
from models.losses.earthnet_forecasting import EarthNetForecastLoss
from train.train_stage2_earthnet import (
    create_stage2_model,
    forward_stage2_model,
    load_config,
    load_stage2_model_state,
    move_batch_to_device,
    prepare_stage2_batch_for_model,
    stage2_supervision_for_output,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--split", default="val")
    parser.add_argument("--data-root", type=str)
    parser.add_argument("--external-driver-root", type=str)
    parser.add_argument("--dgh-stats-path", type=str)
    parser.add_argument("--conditioning-stats-path", type=str)
    parser.add_argument("--manifest-path", type=str)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--output", default=None)
    parser.add_argument("--official-score", action="store_true")
    parser.add_argument(
        "--per-cube-output",
        type=str,
        default=None,
        help=(
            "When --official-score is set, write per-cube ENS/subscores to this "
            "JSON path. Required for downstream bootstrap CIs / paired significance."
        ),
    )
    parser.add_argument(
        "--allow-checkpoint-contract-mismatch",
        action="store_true",
        help=(
            "Allow an explicitly labeled legacy/compatibility evaluation when "
            "the checkpoint config does not match the current Stage2 contract."
        ),
    )
    args = parser.parse_args()

    config = load_config(args.config)
    if args.data_root is not None:
        config["data"]["root"] = args.data_root
    if args.external_driver_root is not None:
        config["data"]["external_driver_root"] = args.external_driver_root
    if args.dgh_stats_path is not None:
        config["data"]["dgh_stats_path"] = args.dgh_stats_path
    if args.conditioning_stats_path is not None:
        config["data"]["conditioning_stats_path"] = args.conditioning_stats_path
    if args.manifest_path is not None:
        config["data"]["manifest_path"] = args.manifest_path
        manifest_paths = config["data"].get("manifest_paths")
        if isinstance(manifest_paths, dict):
            manifest_paths[args.split] = args.manifest_path
        config["data"]["require_manifest"] = True
    config["data"]["split"] = args.split
    # A Stage2 checkpoint already contains the complete state initializer. The
    # original Stage1.5 path is provenance, not an evaluation dependency.
    config["model"]["encoder"]["from_checkpoint"] = None
    config["model"]["compute_latent_targets"] = False

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    contract_verification = verify_checkpoint_contract(
        checkpoint,
        config,
        allow_mismatch=args.allow_checkpoint_contract_mismatch,
    )
    data_cfg = EarthNet2021Config.from_config(config["data"], split=args.split)
    dataset = EarthNet2021Dataset(data_cfg)
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True,
        drop_last=False,
        collate_fn=collate_earthnet2021,
    )

    model = create_stage2_model(config, device)
    state = checkpoint.get("model_state_dict", checkpoint)
    load_stage2_model_state(model, state, strict=True)
    model.eval()

    loss_fn = EarthNetForecastLoss.from_config(
        config["loss"],
        red_index=data_cfg.band_spec.red_index,
        nir_index=data_cfg.band_spec.nir_index,
    ).to(device)

    sums = {}
    count = 0
    official = EarthNetScoreAccumulator(data_cfg.eval_img_size) if args.official_score else None
    forecast_metrics = ForecastMetricAccumulator(
        red_index=data_cfg.band_spec.red_index,
        nir_index=data_cfg.band_spec.nir_index,
    )
    with torch.no_grad():
        for batch in tqdm(loader, desc=f"eval {args.split}"):
            batch = move_batch_to_device(batch, device)
            # Match training/validation: restore the deferred context resize on
            # device before the model (no-op unless defer_context_resize_to_device).
            batch = prepare_stage2_batch_for_model(batch, data_cfg)
            out = forward_stage2_model(model, batch)
            supervision = stage2_supervision_for_output(batch, out)
            losses = loss_fn(
                out["pred"],
                supervision["target"],
                supervision["target_mask"],
                z_pred=out.get("z_pred"),
                z_target=out.get("z_target"),
                z_context=out.get("z_context"),
                z_target_mask=out.get("z_target_mask"),
                horizons=supervision["horizons"],
            )
            bs = batch["x_target"].shape[0]
            count += bs
            for key, value in losses.items():
                sums[key] = sums.get(key, 0.0) + float(value.detach().cpu()) * bs
            forecast_metrics.update(
                out["pred"],
                supervision["target"],
                supervision["target_mask"],
                supervision["horizons"],
                batch["x_context"],
                batch["context_mask"],
            )
            if official is not None:
                official.update(
                    out["pred"],
                    supervision["target"],
                    supervision["target_mask"],
                    [item["sample_id"] for item in batch["meta"]],
                )

    metrics = {key: value / max(count, 1) for key, value in sums.items()}
    metrics["num_samples"] = count
    metrics.update(forecast_metrics.compute())
    if official is not None:
        metrics.update(official.compute())
        # Self-describe the temporal protocol so downstream never mistakes a
        # truncated-diagnostic split (extreme/seasonal at 10->20 under the frozen
        # 30-token earthnet2021x layout) for an official-protocol ENS.
        proto = OFFICIAL_EARTHNET2021_PROTOCOL.get(args.split)
        metrics["eval_context_frames"] = int(data_cfg.context_frames)
        metrics["eval_target_frames"] = int(data_cfg.target_frames)
        if proto is not None:
            match = (
                int(data_cfg.context_frames) == proto["context"]
                and int(data_cfg.target_frames) == proto["target"]
            )
            metrics["official_protocol_context"] = int(proto["context"])
            metrics["official_protocol_target"] = int(proto["target"])
            metrics["official_protocol_match"] = bool(match)
            metrics["is_truncated_diagnostic"] = bool(not match)
        if args.per_cube_output:
            per_cube_path = Path(args.per_cube_output).expanduser()
            per_cube_path.parent.mkdir(parents=True, exist_ok=True)
            with open(per_cube_path, "w") as fp:
                json.dump(
                    {
                        "split": args.split,
                        "checkpoint": str(Path(args.checkpoint).resolve()),
                        "eval_context_frames": int(data_cfg.context_frames),
                        "eval_target_frames": int(data_cfg.target_frames),
                        "rows": official.per_cube(),
                    },
                    fp,
                    allow_nan=False,
                )
    provenance = build_stage2_evaluation_provenance(
        config,
        checkpoint_path=args.checkpoint,
        checkpoint=checkpoint,
        split=args.split,
        manifest_path=data_cfg.manifest_path,
        conditioning_stats_path=data_cfg.conditioning_stats_path,
        contract_verification=contract_verification,
        evaluator="eval.eval_stage2_earthnet",
        invocation={
            "official_score": bool(args.official_score),
            "batch_size": int(args.batch_size),
            "num_workers": int(args.num_workers),
        },
        device=str(device),
    )
    result = json_safe({
        "metrics": metrics,
        "provenance": provenance,
    })
    console_summary = {
        "metrics": result["metrics"],
        "contract_verification": {
            key: result["provenance"]["contract_verification"].get(key)
            for key in (
                "checked",
                "matches",
                "override_used",
                "checkpoint_contract_sha256",
                "runtime_contract_sha256",
            )
        },
        "output": str(Path(args.output).expanduser().resolve()) if args.output else None,
    }
    print(json.dumps(console_summary, indent=2, ensure_ascii=False, allow_nan=False))

    if args.output is not None:
        write_evaluation_sidecar(args.output, result)


if __name__ == "__main__":
    main()
