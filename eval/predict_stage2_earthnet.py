#!/usr/bin/env python
"""Export ObsWorld predictions in the official EarthNet2021 NPZ layout."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import (
    EarthNet2021Config,
    EarthNet2021Dataset,
    collate_earthnet2021,
)
from eval.stage2_evaluation_provenance import (
    build_stage2_evaluation_provenance,
    output_file_record,
    prediction_records_digest,
    verify_checkpoint_contract,
    write_evaluation_sidecar,
)
from train.train_stage2_earthnet import (
    create_stage2_model,
    forward_stage2_model,
    load_config,
    load_stage2_model_state,
    move_batch_to_device,
    prepare_stage2_batch_for_model,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument(
        "--split",
        default="iid",
        choices=["train", "val", "iid", "ood", "extreme", "seasonal", "test"],
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--external-driver-root")
    parser.add_argument("--dgh-stats-path")
    parser.add_argument("--conditioning-stats-path")
    parser.add_argument("--manifest-path")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--output-size", type=int, default=128)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--hash-mode",
        choices=["none", "sha256"],
        default="sha256",
        help="Digest each exported NPZ in prediction_manifest.json (sha256 is formal default).",
    )
    parser.add_argument(
        "--prediction-manifest",
        default=None,
        help="Defaults to <output-dir>/prediction_manifest.json.",
    )
    parser.add_argument(
        "--allow-checkpoint-contract-mismatch",
        action="store_true",
        help="Allow an explicitly labeled legacy/compatibility export.",
    )
    parser.add_argument(
        "--allow-nonstandard-output-size",
        action="store_true",
        help="Allow a formal manifest-backed run to export a size other than eval_img_size.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    config["data"]["root"] = args.data_root
    config["data"]["split"] = args.split
    # Official test context cubes contain 10 optical frames and no targets.
    config["data"]["strict"] = False
    if args.external_driver_root:
        config["data"]["external_driver_root"] = args.external_driver_root
    if args.dgh_stats_path:
        config["data"]["dgh_stats_path"] = args.dgh_stats_path
    if args.conditioning_stats_path:
        config["data"]["conditioning_stats_path"] = args.conditioning_stats_path
    if args.manifest_path:
        config["data"]["manifest_path"] = args.manifest_path
        manifest_paths = config["data"].get("manifest_paths")
        if isinstance(manifest_paths, dict):
            manifest_paths[args.split] = args.manifest_path
        config["data"]["require_manifest"] = True
    config["model"]["encoder"]["from_checkpoint"] = None
    config["model"]["compute_latent_targets"] = False

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    contract_verification = verify_checkpoint_contract(
        checkpoint,
        config,
        allow_mismatch=args.allow_checkpoint_contract_mismatch,
    )

    data_cfg = EarthNet2021Config.from_config(config["data"], split=args.split)
    if (
        data_cfg.require_manifest
        and args.output_size != data_cfg.eval_img_size
        and not args.allow_nonstandard_output_size
    ):
        raise ValueError(
            "Formal manifest-backed export must use the configured eval_img_size "
            f"({data_cfg.eval_img_size}), got --output-size={args.output_size}. "
            "Pass --allow-nonstandard-output-size only for a clearly labeled debug export."
        )
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

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = create_stage2_model(config, device)
    load_stage2_model_state(
        model,
        checkpoint.get("model_state_dict", checkpoint),
        strict=True,
    )
    model.eval()

    output_root = Path(args.output_dir).expanduser().resolve()
    manifest_path = (
        Path(args.prediction_manifest).expanduser().resolve()
        if args.prediction_manifest
        else output_root / "prediction_manifest.json"
    )
    _validate_existing_output_directory(
        output_root,
        manifest_path,
        checkpoint_path=args.checkpoint,
        split=args.split,
        dataset_size=len(dataset),
        hash_mode=args.hash_mode,
        runtime_contract_sha256=contract_verification["runtime_contract_sha256"],
        overwrite=args.overwrite,
    )
    expected_outputs: dict[str, str] = {}
    target_steps = int(config["model"].get("target_steps", 20))
    with torch.no_grad():
        for batch in tqdm(loader, desc=f"predict EarthNet {args.split}"):
            batch = move_batch_to_device(batch, device)
            # Mirror the trainer: when defer_context_resize_to_device is set the
            # loader returns native context rasters, so restore the encoder input
            # size on-device before the model, exactly as training/validation do.
            batch = prepare_stage2_batch_for_model(batch, data_cfg)
            pred = forward_stage2_model(model, batch)["pred"].float().clamp(0, 1)
            if pred.shape[1] != target_steps:
                raise RuntimeError(
                    "Formal Stage2 export must contain the full future path: "
                    f"expected {target_steps} frames, got {pred.shape[1]}"
                )
            pred = _resize_predictions(pred, args.output_size).cpu().numpy()
            for index, meta in enumerate(batch["meta"]):
                cubename = meta["sample_id"]
                tile = cubename[:5]
                path = output_root / tile / f"{cubename}.npz"
                relative = path.relative_to(output_root).as_posix()
                if relative in expected_outputs:
                    raise RuntimeError(f"Duplicate prediction output path: {relative}")
                expected_outputs[relative] = cubename
                if path.exists() and not args.overwrite:
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                highresdynamic = np.transpose(
                    pred[index],
                    (2, 3, 1, 0),
                ).astype(np.float32)
                _atomic_save_prediction(path, highresdynamic)

    output_records = _collect_prediction_records(
        output_root,
        expected_outputs,
        hash_mode=args.hash_mode,
    )
    provenance = build_stage2_evaluation_provenance(
        config,
        checkpoint_path=args.checkpoint,
        checkpoint=checkpoint,
        split=args.split,
        manifest_path=data_cfg.manifest_path,
        conditioning_stats_path=data_cfg.conditioning_stats_path,
        contract_verification=contract_verification,
        evaluator="eval.predict_stage2_earthnet",
        invocation={
            "batch_size": int(args.batch_size),
            "num_workers": int(args.num_workers),
            "output_size": int(args.output_size),
            "hash_mode": args.hash_mode,
            "overwrite": bool(args.overwrite),
        },
        device=str(device),
    )
    prediction_manifest = {
        "schema_version": 1,
        "kind": "stage2_prediction_manifest",
        "format": "earthnet2021_npz_highresdynamic",
        "output_dir": str(output_root),
        "split": args.split,
        "output_size": int(args.output_size),
        "prediction_steps": target_steps,
        "hash_mode": args.hash_mode,
        "num_predictions": len(output_records),
        "files": output_records,
        "files_sha256": prediction_records_digest(output_records),
        "provenance": provenance,
    }
    write_evaluation_sidecar(manifest_path, prediction_manifest)

    print(f"predictions={output_root}")
    print(f"num_cubes={len(output_records)}")
    print(f"prediction_manifest={manifest_path}")


def _atomic_save_prediction(path: Path, highresdynamic: np.ndarray) -> None:
    """Write an NPZ through fsync + replacement so a crash cannot score a half file."""

    temporary = path.with_name(f".{path.stem}.{os.getpid()}.tmp.npz")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, highresdynamic=highresdynamic)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON sidecar: {path}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object in {path}")
    return payload


def _validate_existing_output_directory(
    output_root: Path,
    manifest_path: Path,
    *,
    checkpoint_path: str,
    split: str,
    dataset_size: int,
    hash_mode: str,
    runtime_contract_sha256: str,
    overwrite: bool,
) -> None:
    """Forbid silently mixing predictions from different checkpoints/runs."""

    existing_files = sorted(output_root.rglob("*.npz")) if output_root.exists() else []
    if not existing_files and not manifest_path.exists():
        return
    if overwrite:
        return
    if not manifest_path.is_file():
        raise FileExistsError(
            f"Prediction directory {output_root} already contains NPZ files but has "
            "no prediction_manifest.json. Refusing to mix an untracked prior export; "
            "use a fresh output directory or --overwrite after inspecting it."
        )
    manifest = _load_json_object(manifest_path)
    provenance = manifest.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValueError("Existing prediction manifest has no valid provenance object")
    source_checkpoint = provenance.get("checkpoint")
    if not isinstance(source_checkpoint, Mapping):
        raise ValueError("Existing prediction manifest has no valid checkpoint identity")
    # New training provenance stores the checkpoint path only in the export
    # sidecar, so compare the concrete export identity whenever it is present.
    current_file_sha = _sha256_from_path(checkpoint_path)
    if source_checkpoint.get("sha256") != current_file_sha:
        raise ValueError(
            "Existing prediction manifest belongs to a different checkpoint. "
            "Use a new output directory instead of mixing prediction files."
        )
    if manifest.get("split") != split or int(manifest.get("num_predictions", -1)) != dataset_size:
        raise ValueError(
            "Existing prediction manifest has a different split or sample count; "
            "use a separate output directory."
        )
    source_contract = provenance.get("contract_verification")
    if not isinstance(source_contract, Mapping):
        raise ValueError("Existing prediction manifest has no valid contract verification")
    if source_contract.get("runtime_contract_sha256") != runtime_contract_sha256:
        raise ValueError(
            "Existing prediction manifest has a different Stage2 runtime contract; "
            "use a separate output directory."
        )
    if manifest.get("hash_mode") != hash_mode:
        raise ValueError(
            "Existing prediction manifest uses a different hash mode; use a fresh "
            "output directory to keep its integrity record unambiguous."
        )
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ValueError("Existing prediction manifest has no valid files list")
    for record in files:
        if not isinstance(record, Mapping) or not isinstance(record.get("path"), str):
            raise ValueError("Existing prediction manifest contains an invalid file record")
        source = output_root / record["path"]
        current = output_file_record(source, root=output_root, hash_mode=hash_mode)
        for key in ("size_bytes", "sha256"):
            if key in record and current.get(key) != record.get(key):
                raise ValueError(
                    f"Existing prediction file does not match its manifest: {record['path']}"
                )


def _sha256_from_path(path: str) -> str:
    from train.stage2_provenance import sha256_file

    return sha256_file(path)


def _collect_prediction_records(
    output_root: Path,
    expected_outputs: Mapping[str, str],
    *,
    hash_mode: str,
) -> list[dict[str, Any]]:
    """Ensure output contains exactly this run's expected files, then hash them."""

    actual = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*.npz")
        if path.is_file()
    }
    expected = set(expected_outputs)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing[:5]}")
        if extra:
            details.append(f"extra={extra[:5]}")
        raise RuntimeError(
            "Prediction directory does not contain exactly the current frozen split "
            "outputs; refusing to write a misleading manifest (" + "; ".join(details) + ")"
        )
    records: list[dict[str, Any]] = []
    for relative in sorted(expected):
        record = output_file_record(output_root / relative, root=output_root, hash_mode=hash_mode)
        record["sample_id"] = expected_outputs[relative]
        records.append(record)
    return records


def _resize_predictions(pred: torch.Tensor, size: int) -> torch.Tensor:
    b, t, c, h, w = pred.shape
    if (h, w) == (size, size):
        return pred
    resized = F.interpolate(
        pred.reshape(b * t, c, h, w),
        size=(size, size),
        mode="bilinear",
        align_corners=False,
    )
    return resized.reshape(b, t, c, size, size)


if __name__ == "__main__":
    main()
