#!/usr/bin/env python
"""Export ObsWorld RGBN forecasts to official GreenEarthNet NetCDF files.

Formal export is provenance-bound: it verifies the checkpoint/runtime contract,
applies the same on-device input preparation as training, and writes a hashed
prediction_manifest.json so a GreenEarthNet-protocol score is reproducible and
cannot be silently mixed across checkpoints.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

import torch
import torch.nn.functional as F
import xarray as xr
from torch.utils.data import DataLoader

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import (  # noqa: E402
    EarthNet2021Config,
    EarthNet2021Dataset,
    collate_earthnet2021,
)
from eval.greenearthnet_protocol import make_prediction_dataset  # noqa: E402
from eval.stage2_evaluation_provenance import (  # noqa: E402
    build_stage2_evaluation_provenance,
    output_file_record,
    prediction_records_digest,
    verify_checkpoint_contract,
    write_evaluation_sidecar,
)
from train.train_stage2_earthnet import (  # noqa: E402
    create_stage2_model,
    forward_stage2_model,
    load_config,
    load_stage2_model_state,
    move_batch_to_device,
    prepare_stage2_batch_for_model,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--split",
        required=True,
        help="GreenEarthNet track name for this export. Pinned explicitly (no "
        "default) so the frozen manifest role is never silently exported under a "
        "mismatched track such as ood-t vs ood.",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dgh-stats-path")
    parser.add_argument(
        "--conditioning-stats-path",
        help="Train-only conditioning stats path required by the physical4 config.",
    )
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--hash-mode",
        choices=["none", "sha256"],
        default="sha256",
        help="Digest each exported NetCDF in prediction_manifest.json (sha256 is formal default).",
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
    args = parser.parse_args()

    config = load_config(args.config)
    config["data"].update(
        {
            "root": args.data_root,
            "split": args.split,
            "manifest_path": args.manifest,
            "require_manifest": True,
            "strict": True,
        }
    )
    if args.dgh_stats_path:
        config["data"]["dgh_stats_path"] = args.dgh_stats_path
    if args.conditioning_stats_path:
        config["data"]["conditioning_stats_path"] = args.conditioning_stats_path
    config["model"]["encoder"]["from_checkpoint"] = None
    # Formal export never sends future observations/masks through the model.
    config["model"]["compute_latent_targets"] = False

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

    target_steps = int(config["model"].get("target_steps", 20))
    expected_outputs: dict[str, str] = {}
    written = 0
    skipped = 0
    with torch.no_grad():
        for batch in tqdm(loader, desc=f"export GreenEarthNet {args.split}"):
            batch = move_batch_to_device(batch, device)
            # Match training/validation: restore the deferred context resize on
            # device before the model (no-op unless defer_context_resize_to_device).
            batch = prepare_stage2_batch_for_model(batch, data_cfg)
            prediction = forward_stage2_model(model, batch)["pred"].float().clamp(0, 1)
            if prediction.shape[1] != target_steps:
                raise RuntimeError(
                    "Formal GreenEarthNet export must contain the full future path: "
                    f"expected {target_steps} frames, got {prediction.shape[1]}"
                )
            for index, metadata in enumerate(batch["meta"]):
                target_path = Path(metadata["path"])
                relative = f"{target_path.parent.name}/{target_path.name}"
                if relative in expected_outputs:
                    raise RuntimeError(f"Duplicate export output path: {relative}")
                expected_outputs[relative] = metadata["sample_id"]
                output_path = output_root / target_path.parent.name / target_path.name
                if output_path.exists() and not args.overwrite:
                    skipped += 1
                    continue
                with xr.open_dataset(target_path) as target:
                    height = int(target.sizes["lat"])
                    width = int(target.sizes["lon"])
                    rgbn = prediction[index]
                    if tuple(rgbn.shape[-2:]) != (height, width):
                        rgbn = F.interpolate(
                            rgbn,
                            size=(height, width),
                            mode="bilinear",
                            align_corners=False,
                        )
                    prediction_cube = make_prediction_dataset(
                        target,
                        rgbn.cpu().numpy(),
                        red_index=data_cfg.band_spec.red_index,
                        nir_index=data_cfg.band_spec.nir_index,
                    ).load()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                _atomic_write_netcdf(output_path, prediction_cube)
                written += 1

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
        evaluator="eval.export_greenearthnet_predictions",
        invocation={
            "batch_size": int(args.batch_size),
            "num_workers": int(args.num_workers),
            "hash_mode": args.hash_mode,
            "overwrite": bool(args.overwrite),
            "written": written,
            "skipped_existing": skipped,
        },
        device=str(device),
    )
    prediction_manifest = {
        "schema_version": 1,
        "kind": "greenearthnet_prediction_manifest",
        "format": "greenearthnet_ndvi_netcdf",
        "output_dir": str(output_root),
        "split": args.split,
        "prediction_steps": target_steps,
        "hash_mode": args.hash_mode,
        "num_predictions": len(output_records),
        "written": written,
        "skipped_existing": skipped,
        "files": output_records,
        "files_sha256": prediction_records_digest(output_records),
        "provenance": provenance,
    }
    write_evaluation_sidecar(manifest_path, prediction_manifest)

    print(f"predictions={output_root}")
    print(f"num_cubes={len(output_records)}")
    print(f"prediction_manifest={manifest_path}")
    return 0


def _atomic_write_netcdf(path: Path, cube: "xr.Dataset") -> None:
    """Write a NetCDF through a temp file + replacement so a crash cannot score a half file."""

    temporary = path.with_name(f".{path.stem}.{os.getpid()}.tmp.nc")
    cube.to_netcdf(temporary, encoding={"ndvi_pred": {"dtype": "float32"}})
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
    """Forbid silently mixing GreenEarthNet exports from different checkpoints/runs."""

    existing_files = sorted(output_root.rglob("*.nc")) if output_root.exists() else []
    if not existing_files and not manifest_path.exists():
        return
    if overwrite:
        return
    if not manifest_path.is_file():
        raise FileExistsError(
            f"Export directory {output_root} already contains NetCDF files but has "
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
        for path in output_root.rglob("*.nc")
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
            "Export directory does not contain exactly the current frozen split "
            "outputs; refusing to write a misleading manifest (" + "; ".join(details) + ")"
        )
    records: list[dict[str, Any]] = []
    for relative in sorted(expected):
        record = output_file_record(output_root / relative, root=output_root, hash_mode=hash_mode)
        record["sample_id"] = expected_outputs[relative]
        records.append(record)
    return records


if __name__ == "__main__":
    raise SystemExit(main())
