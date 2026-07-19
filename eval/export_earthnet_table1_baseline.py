#!/usr/bin/env python
"""Export no-leakage Persistence / training-climatology Table 1 baselines.

Both baselines use exactly the frozen raw NetCDF manifest supplied for IID or
OOD.  Persistence consumes only context frames.  Climatology is fitted only
from an explicitly supplied role=train manifest and is cache-bound to it.
Outputs are either EarthNetScore RGBN NPZs or GreenEarthNet-style NDVI NetCDFs
so the existing scorers can be reused without reimplementing metrics.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - progress is cosmetic
    def tqdm(iterable, *args, **kwargs):
        return iterable

from data.earthnet_manifest import (
    GREENEARTHNET_CHOPPED_PROTOCOL_ID,
    PROTOCOL_ID,
    load_manifest_files,
    manifest_protocol_spec,
    resolve_manifest_root,
    write_json_atomic,
)
from eval.earthnet_table1 import (
    TABLE1_SCHEMA_VERSION,
    DoyClimatology,
    atomic_save_npz,
    atomic_write_netcdf,
    climatology_sidecar_path,
    collect_output_records,
    fit_doy_climatology,
    greenearthnet_relative_path,
    load_climatology_cache,
    persistence_rgbn,
    raw_cube_from_netcdf,
    save_climatology_cache,
    source_manifest_identity,
    target_relative_path,
    temporal_contract,
    validate_existing_output,
)
from eval.greenearthnet_protocol import make_prediction_dataset
from eval.stage2_evaluation_provenance import prediction_records_digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--manifest-protocol",
        default=PROTOCOL_ID,
        help="Protocol of --manifest; OOD-t requires greenearthnet_cvpr2024_chopped_v1.",
    )
    parser.add_argument(
        "--split",
        required=True,
        help="Exact frozen manifest role (for example ood-t_chopped); no aliasing.",
    )
    parser.add_argument("--baseline", required=True, choices=("persistence", "climatology"))
    parser.add_argument("--format", required=True, choices=("earthnet_npz", "greenearthnet_netcdf"))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prediction-manifest", default=None)
    parser.add_argument("--hash-mode", choices=("none", "sha256"), default="sha256")
    parser.add_argument("--verify-manifest-sizes", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--climatology-cache",
        help="Required for --baseline climatology; NPZ cache fitted from training only.",
    )
    parser.add_argument(
        "--climatology-train-manifest",
        help="Required for --baseline climatology; frozen raw role=train manifest.",
    )
    parser.add_argument(
        "--climatology-train-manifest-protocol",
        default=PROTOCOL_ID,
        help="Protocol of the training-only climatology manifest (raw EarthNet default).",
    )
    parser.add_argument(
        "--climatology-train-dataset-root",
        help="Defaults to --dataset-root; use only if the training NetCDF root differs.",
    )
    parser.add_argument(
        "--fit-climatology",
        action="store_true",
        help="Fit and atomically cache climatology when it does not already exist.",
    )
    return parser.parse_args()


def _require_climatology(args: argparse.Namespace) -> tuple[DoyClimatology, dict[str, object]]:
    if not args.climatology_cache or not args.climatology_train_manifest:
        raise ValueError(
            "--baseline climatology requires --climatology-cache and "
            "--climatology-train-manifest"
        )
    train_root = args.climatology_train_dataset_root or args.dataset_root
    manifest_protocol_spec(args.climatology_train_manifest_protocol)
    train_identity = source_manifest_identity(args.climatology_train_manifest)
    train_dataset_root = resolve_manifest_root(
        train_root,
        protocol=args.climatology_train_manifest_protocol,
    )
    cache = Path(args.climatology_cache).expanduser().resolve()
    if not cache.exists():
        if not args.fit_climatology:
            raise FileNotFoundError(
                f"Climatology cache does not exist: {cache}. Pass --fit-climatology "
                "to fit it from the explicit training manifest."
            )
        paths = load_manifest_files(
            args.climatology_train_manifest,
            train_dataset_root,
            expected_split="train",
            expected_protocol=args.climatology_train_manifest_protocol,
            verify_exists=True,
        )
        print(f"fitting training-only climatology from {len(paths)} raw cubes")
        fitted = fit_doy_climatology(tqdm(paths, desc="fit Table1 climatology"))
        save_climatology_cache(
            cache,
            fitted,
            training_manifest=train_identity,
            training_dataset_root=train_dataset_root,
        )
    climatology = load_climatology_cache(
        cache,
        expected_training_manifest=train_identity,
        expected_training_dataset_root=train_dataset_root,
    )
    return climatology, {
        "cache": str(cache),
        "cache_sidecar": str(climatology_sidecar_path(cache)),
        "training_manifest": train_identity,
        "training_dataset_root": str(train_dataset_root),
        "training_manifest_protocol": args.climatology_train_manifest_protocol,
    }


def main() -> int:
    args = parse_args()
    manifest_protocol_spec(args.manifest_protocol)
    if args.manifest_protocol == GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        raise ValueError(
            "This raw-RGBN baseline is an internal EarthNet2021x diagnostic only. "
            "For formal GreenEarthNet chopped Table 1 baselines, use "
            "eval/generate_baseline_predictions.py so Persistence/Climatology "
            "match the public protocol definitions."
        )
    dataset_root = resolve_manifest_root(
        args.dataset_root,
        protocol=args.manifest_protocol,
    )
    source_identity = source_manifest_identity(args.manifest)
    output_root = Path(args.output_dir).expanduser().resolve()
    suffix = ".npz" if args.format == "earthnet_npz" else ".nc"
    manifest_path = (
        Path(args.prediction_manifest).expanduser().resolve()
        if args.prediction_manifest
        else output_root / "prediction_manifest.json"
    )
    climatology: DoyClimatology | None = None
    climatology_info: dict[str, object] | None = None
    if args.baseline == "climatology":
        climatology, climatology_info = _require_climatology(args)
    baseline_contract: dict[str, object] = {
        "name": args.baseline,
        "persistence_semantics": (
            "last_clear_context_pixel_repeat; never_observed_context_pixel=zero_reflectance"
            if args.baseline == "persistence"
            else None
        ),
        "climatology": climatology_info,
    }
    identity = {
        "kind": "earthnet2021_table1_baseline_prediction",
        "format": args.format,
        "split": args.split,
        "manifest_protocol": args.manifest_protocol,
        "source_manifest": source_identity,
        "baseline": baseline_contract,
        "temporal_contract": temporal_contract(),
    }
    validate_existing_output(
        output_root,
        manifest_path,
        expected_identity=identity,
        suffix=suffix,
        overwrite=args.overwrite,
    )
    sources = load_manifest_files(
        args.manifest,
        dataset_root,
        expected_split=args.split,
        expected_protocol=args.manifest_protocol,
        verify_exists=True,
        verify_sizes=args.verify_manifest_sizes,
    )
    expected: dict[str, str] = {}
    written = 0
    for source in tqdm(sources, desc=f"{args.baseline} {args.split} {args.format}"):
        sample_id = source.stem
        relative = (
            target_relative_path(sample_id)
            if args.format == "earthnet_npz"
            else greenearthnet_relative_path(source)
        )
        if relative in expected:
            raise ValueError(f"Duplicate baseline output path: {relative}")
        expected[relative] = sample_id
        output = output_root / relative
        if output.is_file() and not args.overwrite:
            continue
        raw = raw_cube_from_netcdf(source)
        if args.baseline == "persistence":
            prediction = persistence_rgbn(raw)
        else:
            assert climatology is not None
            prediction = climatology.predict(
                raw.future_dates,
                raw.rgbn.shape[-2],
                raw.rgbn.shape[-1],
            )
        if args.format == "earthnet_npz":
            highresdynamic = prediction.transpose(2, 3, 1, 0).astype(np.float32)
            atomic_save_npz(output, highresdynamic=highresdynamic)
        else:
            with xr.open_dataset(source, decode_times=True, cache=False) as target:
                nc = make_prediction_dataset(target, prediction).load()
            atomic_write_netcdf(output, nc)
        written += 1

    records = collect_output_records(
        output_root,
        expected,
        suffix=suffix,
        hash_mode=args.hash_mode,
    )
    payload = {
        "schema_version": TABLE1_SCHEMA_VERSION,
        "kind": "earthnet2021_table1_baseline_prediction_manifest",
        "format": args.format,
        "output_dir": str(output_root),
        "split": args.split,
        "manifest_protocol": args.manifest_protocol,
        "source_manifest": source_identity,
        "hash_mode": args.hash_mode,
        "num_predictions": len(records),
        "files": records,
        "files_sha256": prediction_records_digest(records),
        "identity": identity,
        "written": written,
    }
    write_json_atomic(payload, manifest_path)
    print(f"predictions={output_root}")
    print(f"num_cubes={len(records)}")
    print(f"prediction_manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
