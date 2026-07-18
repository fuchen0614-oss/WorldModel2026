"""Single-seed val_dev comparison for Observation Correction strategies.

The script evaluates the same reveal schedule for U, No-update, and Restart.
VanillaFilter is included only when a separately trained capacity-matched
checkpoint is supplied; an untrained randomly initialized filter is never
reported as a baseline result.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Subset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import EarthNet2021Config, EarthNet2021Dataset, collate_earthnet2021
from eval.forecast_metrics import ForecastMetricAccumulator
from models.losses.earthnet_forecasting import EarthNetForecastLoss
from train.observation_correction_schedule import build_observation_correction_inputs
from train.train_stage2_earthnet import (
    create_stage2_model,
    forward_stage2_model,
    load_config,
    load_stage2_model_state,
    move_batch_to_device,
    prepare_stage2_batch_for_model,
    stage2_supervision_for_output,
)


def _masked_mean(values: torch.Tensor, mask: torch.Tensor) -> float:
    values = values.float()
    mask = mask.to(dtype=values.dtype, device=values.device)
    return float((values * mask).sum().detach().cpu() / mask.sum().clamp_min(1.0).detach().cpu())


def _strategy_metrics(out: dict, batch: dict, supervision: dict) -> dict[str, float]:
    pred = out["pred"]
    target = supervision["target"]
    mask = supervision["target_mask"]
    if mask is None:
        mask = torch.ones_like(target[:, :, 0])
    per_step = (pred.float() - target.float()).abs().mean(dim=2)
    result: dict[str, float] = {}
    for index, day in ((4, 25), (9, 50)):
        if index < pred.shape[1]:
            result[f"MAE_day{day}"] = _masked_mean(per_step[:, index], mask[:, index])
    reveal = batch["_correction_reveal_mask"][:, : pred.shape[1]]
    time = torch.arange(pred.shape[1], device=pred.device)[None, :]
    first_reveal = torch.where(
        reveal.gt(0), time, torch.full_like(time, pred.shape[1])
    ).amin(dim=1)
    post = time > first_reveal[:, None]
    no_reveal = first_reveal.ge(pred.shape[1])
    post = torch.where(no_reveal[:, None], torch.zeros_like(post), post)
    pre = ~post
    result["MAE_pre_reveal"] = _masked_mean(per_step, mask * pre[:, :, None, None])
    result["MAE_post_reveal"] = (
        _masked_mean(per_step, mask * post[:, :, None, None])
        if bool(post.any())
        else float("nan")
    )
    return result


@torch.no_grad()
def evaluate_strategy(
    model,
    loader,
    loss_fn,
    data_cfg,
    *,
    strategy: str,
    seed: int,
    device: torch.device,
) -> dict[str, float | int | str]:
    model.eval()
    raw_model = model.module if hasattr(model, "module") else model
    raw_model.correction_strategy = strategy
    accum = ForecastMetricAccumulator(
        red_index=data_cfg.band_spec.red_index,
        nir_index=data_cfg.band_spec.nir_index,
    )
    sums: dict[str, float] = {}
    count = 0
    extra_sums: dict[str, float] = {}
    for batch_index, batch in enumerate(loader):
        batch = move_batch_to_device(batch, device)
        # Restore the deferred context resize on device before the model, just
        # as the trainer does prior to build_observation_correction_inputs.
        batch = prepare_stage2_batch_for_model(batch, data_cfg)
        generator = torch.Generator(device="cpu").manual_seed(seed + batch_index)
        correction = build_observation_correction_inputs(
            batch,
            rollout_steps=batch["x_target"].shape[1],
            generator=generator,
        )
        batch["_correction_reveal_mask"] = correction["reveal_mask"]
        out = forward_stage2_model(
            model,
            batch,
            correction_inputs=correction,
        )
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
        batch_size = int(batch["x_target"].shape[0])
        count += batch_size
        for name, value in losses.items():
            sums[name] = sums.get(name, 0.0) + float(value.detach().cpu()) * batch_size
        for name, value in _strategy_metrics(out, batch, supervision).items():
            if value == value:
                extra_sums[name] = extra_sums.get(name, 0.0) + value * batch_size
        accum.update(
            out["pred"],
            supervision["target"],
            supervision["target_mask"],
            supervision["horizons"],
            batch["x_context"],
            batch["context_mask"],
        )
    metrics = {f"loss/{name}": value / max(count, 1) for name, value in sums.items()}
    metrics.update(accum.compute())
    metrics.update({name: value / max(count, 1) for name, value in extra_sums.items()})
    metrics.update({"strategy": strategy, "num_samples": count})
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument(
        "--vanilla-filter-checkpoint",
        default=None,
        help=(
            "Optional separately trained capacity-matched VanillaFilter checkpoint. "
            "Without it the baseline is recorded as not_evaluated."
        ),
    )
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--manifest-path", required=True)
    parser.add_argument("--conditioning-stats-path", required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    config["data"].update(
        {
            "root": args.data_root,
            "split": "val",
            "manifest_path": args.manifest_path,
            "conditioning_stats_path": args.conditioning_stats_path,
            "require_manifest": True,
        }
    )
    config["data"].setdefault("manifest_paths", {})["val"] = args.manifest_path
    config["model"]["encoder"]["from_checkpoint"] = None
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data_cfg = EarthNet2021Config.from_config(config["data"], split="val")
    dataset = EarthNet2021Dataset(data_cfg)
    if args.max_samples > 0:
        dataset = Subset(dataset, range(min(args.max_samples, len(dataset))))
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
    load_stage2_model_state(model, checkpoint.get("model_state_dict", checkpoint), strict=True)
    loss_fn = EarthNetForecastLoss.from_config(
        config["loss"],
        red_index=data_cfg.band_spec.red_index,
        nir_index=data_cfg.band_spec.nir_index,
    ).to(device)

    results = {"u": evaluate_strategy(model, loader, loss_fn, data_cfg, strategy="u", seed=args.seed, device=device)}
    for strategy in ("no_update", "restart"):
        results[strategy] = evaluate_strategy(model, loader, loss_fn, data_cfg, strategy=strategy, seed=args.seed, device=device)
    if args.vanilla_filter_checkpoint:
        vanilla_config = copy.deepcopy(config)
        vanilla_config["model"].setdefault("observation_correction", {})[
            "strategy"
        ] = "vanilla_filter"
        vanilla_checkpoint = torch.load(
            args.vanilla_filter_checkpoint,
            map_location="cpu",
            weights_only=False,
        )
        vanilla_model = create_stage2_model(vanilla_config, device)
        load_stage2_model_state(
            vanilla_model,
            vanilla_checkpoint.get("model_state_dict", vanilla_checkpoint),
            strict=True,
        )
        results["vanilla_filter"] = evaluate_strategy(
            vanilla_model,
            loader,
            loss_fn,
            data_cfg,
            strategy="vanilla_filter",
            seed=args.seed,
            device=device,
        )
    else:
        results["vanilla_filter"] = {
            "strategy": "vanilla_filter",
            "status": "not_evaluated",
            "reason": "supply a separately trained capacity-matched VanillaFilter checkpoint before reporting this baseline",
        }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "stage2_observation_correction_val",
                "checkpoint": str(Path(args.checkpoint).expanduser().resolve()),
                "vanilla_filter_checkpoint": (
                    str(Path(args.vanilla_filter_checkpoint).expanduser().resolve())
                    if args.vanilla_filter_checkpoint
                    else None
                ),
                "manifest_path": str(Path(args.manifest_path).expanduser().resolve()),
                "seed": args.seed,
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
