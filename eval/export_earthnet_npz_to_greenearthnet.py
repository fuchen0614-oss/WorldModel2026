#!/usr/bin/env python
"""Convert a verified RGBN NPZ prediction tree into GreenEarthNet NDVI NetCDFs.

Stage2 already exports the complete RGBN trajectory once for EarthNetScore.
This converter reuses that immutable export for the repository's NDVI scorer,
rather than loading the model and running a second inference pass. It only
reads raw target NetCDF metadata for target timestamps and spatial coordinates;
the predicted values remain the verified NPZ values.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import xarray as xr

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(iterable, *args, **kwargs):
        return iterable

from data.earthnet_manifest import (
    PROTOCOL_ID,
    load_manifest_files,
    manifest_protocol_spec,
    resolve_manifest_root,
    write_json_atomic,
)
from eval.earthnet_table1 import (
    TABLE1_SCHEMA_VERSION,
    atomic_write_netcdf,
    collect_output_records,
    greenearthnet_relative_path,
    source_manifest_identity,
    target_relative_path,
    temporal_contract,
    validate_existing_output,
)
from eval.greenearthnet_protocol import make_prediction_dataset
from eval.score_table1_earthnet import validate_manifest_tree
from eval.stage2_evaluation_provenance import prediction_records_digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a manifest-verified EarthNet RGBN NPZ tree to NDVI NetCDF."
    )
    parser.add_argument("--prediction-dir", required=True)
    parser.add_argument("--prediction-manifest", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--manifest-protocol",
        default=PROTOCOL_ID,
        help="Raw EarthNet2021x protocol for this legacy RGBN-to-NDVI bridge.",
    )
    parser.add_argument("--split", required=True, choices=("iid", "ood", "extreme", "seasonal", "train", "val"))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output-manifest", default=None)
    parser.add_argument("--hash-mode", choices=("none", "sha256"), default="sha256")
    parser.add_argument("--verify-manifest-sizes", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def _expected_npz_paths(sources: list[Path]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for source in sources:
        sample_id = source.stem
        relative = target_relative_path(sample_id)
        if relative in expected:
            raise ValueError(f"Duplicate input prediction path: {relative}")
        expected[relative] = sample_id
    return expected


def _require_same_paths(
    validation: dict[str, object],
    expected: dict[str, str],
) -> None:
    paths = validation.get("paths")
    if not isinstance(paths, list):
        raise ValueError("The input prediction manifest did not expose output paths")
    observed = set(str(path) for path in paths)
    required = set(expected)
    if observed != required:
        missing = sorted(required - observed)
        extra = sorted(observed - required)
        details = []
        if missing:
            details.append(f"manifest_missing={missing[:5]}")
        if extra:
            details.append(f"manifest_extra={extra[:5]}")
        raise ValueError(
            "Prediction export does not select exactly the requested frozen split ("
            + "; ".join(details)
            + ")"
        )


def _load_rgbn_prediction(path: Path) -> np.ndarray:
    with np.load(path, allow_pickle=False) as payload:
        if "highresdynamic" not in payload:
            raise KeyError(f"{path} has no highresdynamic prediction array")
        array = np.asarray(payload["highresdynamic"], dtype=np.float32)
    if array.ndim != 4 or array.shape[2] < 4:
        raise ValueError(f"{path}: expected [H,W,>=4,T], got {array.shape}")
    if array.shape[-1] != temporal_contract()["target_steps"]:
        raise ValueError(
            f"{path}: expected {temporal_contract()['target_steps']} future frames, "
            f"got {array.shape[-1]}"
        )
    return np.transpose(array[:, :, :4, :], (3, 2, 0, 1)).astype(np.float32, copy=False)


def main() -> int:
    args = parse_args()
    prediction_root = Path(args.prediction_dir).expanduser().resolve()
    manifest_protocol_spec(args.manifest_protocol)
    if args.manifest_protocol != PROTOCOL_ID:
        raise ValueError(
            "This RGBN NPZ converter is only for the raw EarthNet2021x diagnostic "
            "protocol. Use eval/export_greenearthnet_predictions.py for frozen "
            "GreenEarthNet chopped tracks."
        )
    prediction_manifest = Path(args.prediction_manifest).expanduser().resolve()
    dataset_root = resolve_manifest_root(args.dataset_root, protocol=args.manifest_protocol)
    sources = load_manifest_files(
        args.manifest,
        dataset_root,
        expected_split=args.split,
        expected_protocol=args.manifest_protocol,
        verify_exists=True,
        verify_sizes=args.verify_manifest_sizes,
    )
    expected_npz = _expected_npz_paths(sources)
    input_validation = validate_manifest_tree(
        prediction_root,
        prediction_manifest,
        artifact="RGBN prediction",
    )
    _require_same_paths(input_validation, expected_npz)

    output_root = Path(args.output_dir).expanduser().resolve()
    output_manifest = (
        Path(args.output_manifest).expanduser().resolve()
        if args.output_manifest
        else output_root / "prediction_manifest.json"
    )
    source_identity = source_manifest_identity(args.manifest)
    identity = {
        "kind": "earthnet_npz_to_greenearthnet_ndvi",
        "source_manifest": source_identity,
        "source_prediction_manifest": input_validation["manifest"],
        "source_prediction_files_sha256": input_validation["files_sha256"],
        "split": args.split,
        "temporal_contract": temporal_contract(),
    }
    validate_existing_output(
        output_root,
        output_manifest,
        expected_identity=identity,
        suffix=".nc",
        overwrite=args.overwrite,
    )

    expected_outputs: dict[str, str] = {}
    written = 0
    for source in tqdm(sources, desc=f"convert RGBN to GreenEarthNet {args.split}"):
        sample_id = source.stem
        relative = greenearthnet_relative_path(source)
        if relative in expected_outputs:
            raise ValueError(f"Duplicate converted NetCDF path: {relative}")
        expected_outputs[relative] = sample_id
        output = output_root / relative
        if output.is_file() and not args.overwrite:
            continue
        rgbn = _load_rgbn_prediction(prediction_root / target_relative_path(sample_id))
        with xr.open_dataset(source, decode_times=True, cache=False) as target:
            spatial_shape = (int(target.sizes["lat"]), int(target.sizes["lon"]))
            if tuple(rgbn.shape[-2:]) != spatial_shape:
                raise ValueError(
                    f"{source}: RGBN NPZ spatial shape={tuple(rgbn.shape[-2:])} "
                    f"does not match target={spatial_shape}. Re-export predictions "
                    "at the frozen evaluation resolution instead of interpolating "
                    "inside the scorer bridge."
                )
            converted = make_prediction_dataset(target, rgbn).load()
        atomic_write_netcdf(output, converted)
        written += 1

    records = collect_output_records(
        output_root,
        expected_outputs,
        suffix=".nc",
        hash_mode=args.hash_mode,
    )
    payload = {
        "schema_version": TABLE1_SCHEMA_VERSION,
        "kind": "greenearthnet_prediction_manifest",
        "format": "greenearthnet_ndvi_netcdf",
        "output_dir": str(output_root),
        "split": args.split,
        "manifest_protocol": args.manifest_protocol,
        "source_manifest": source_identity,
        "prediction_steps": temporal_contract()["target_steps"],
        "hash_mode": args.hash_mode,
        "num_predictions": len(records),
        "files": records,
        "files_sha256": prediction_records_digest(records),
        "provenance": {
            "evaluator": "eval.export_earthnet_npz_to_greenearthnet",
            "source_prediction_validation": input_validation,
            "source_manifest": source_identity,
            "temporal_contract": temporal_contract(),
        },
        "identity": identity,
        "written": written,
    }
    write_json_atomic(payload, output_manifest)
    print(f"predictions={output_root}")
    print(f"num_cubes={len(records)}")
    print(f"prediction_manifest={output_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
