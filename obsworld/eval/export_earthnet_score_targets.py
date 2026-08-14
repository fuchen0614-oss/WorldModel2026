#!/usr/bin/env python
"""Materialize manifest-pinned EarthNetScore targets from raw EarthNet2021x.

The official EarthNet toolkit scores target NPZ files rather than the raw
NetCDF release.  This adapter makes that conversion explicit, deterministic,
and hash-bound.  It does *not* claim parity with a separately downloaded
official target tree: use ``eval/verify_earthnet_score_targets.py`` when such a
reference tree is available, and keep Table 1 ENS values provisional until the
parity report passes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - progress is cosmetic
    def tqdm(iterable, *args, **kwargs):
        return iterable

from data.earthnet_manifest import load_manifest_files, resolve_dataset_root, write_json_atomic
from eval.earthnet_table1 import (
    TABLE1_SCHEMA_VERSION,
    atomic_save_npz,
    collect_output_records,
    earthnet_target_highresdynamic,
    raw_cube_from_netcdf,
    source_manifest_identity,
    target_relative_path,
    temporal_contract,
    validate_existing_output,
)
from eval.stage2_evaluation_provenance import prediction_records_digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a manifest-backed EarthNetScore target NPZ tree from raw NetCDF."
    )
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--split", required=True, choices=("iid", "ood", "extreme", "seasonal", "train", "val"))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target-manifest", default=None)
    parser.add_argument("--hash-mode", choices=("none", "sha256"), default="sha256")
    parser.add_argument("--verify-manifest-sizes", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_manifest = source_manifest_identity(args.manifest)
    dataset_root = resolve_dataset_root(args.dataset_root)
    output_root = Path(args.output_dir).expanduser().resolve()
    manifest_path = (
        Path(args.target_manifest).expanduser().resolve()
        if args.target_manifest
        else output_root / "target_manifest.json"
    )
    identity = {
        "kind": "earthnet2021_raw_netcdf_to_earthnetscore_target",
        "split": args.split,
        "source_manifest": source_manifest,
        "temporal_contract": temporal_contract(),
        "rgbn_channels": ["s2_B02", "s2_B03", "s2_B04", "s2_B8A"],
        "invalid_mask": "not_finite_or_s2_mask_gt_zero",
    }
    validate_existing_output(
        output_root,
        manifest_path,
        expected_identity=identity,
        suffix=".npz",
        overwrite=args.overwrite,
    )
    sources = load_manifest_files(
        args.manifest,
        dataset_root,
        expected_split=args.split,
        verify_exists=True,
        verify_sizes=args.verify_manifest_sizes,
    )
    expected: dict[str, str] = {}
    written = 0
    for source in tqdm(sources, desc=f"EarthNetScore targets {args.split}"):
        sample_id = source.stem
        relative = target_relative_path(sample_id)
        if relative in expected:
            raise ValueError(f"Duplicate sample output path: {relative}")
        expected[relative] = sample_id
        output = output_root / relative
        if output.is_file() and not args.overwrite:
            continue
        raw = raw_cube_from_netcdf(source)
        atomic_save_npz(output, highresdynamic=earthnet_target_highresdynamic(raw))
        written += 1

    records = collect_output_records(
        output_root,
        expected,
        suffix=".npz",
        hash_mode=args.hash_mode,
    )
    payload = {
        "schema_version": TABLE1_SCHEMA_VERSION,
        "kind": "earthnet2021_score_target_manifest",
        "format": "earthnet2021_npz_highresdynamic_rgbn_cloud",
        "output_dir": str(output_root),
        "split": args.split,
        "hash_mode": args.hash_mode,
        "num_targets": len(records),
        "files": records,
        "files_sha256": prediction_records_digest(records),
        "identity": identity,
        "adapter_parity_status": "raw_adapter_unverified",
        "written": written,
    }
    write_json_atomic(payload, manifest_path)
    print(f"targets={output_root}")
    print(f"num_targets={len(records)}")
    print(f"target_manifest={manifest_path}")
    print("adapter_parity_status=raw_adapter_unverified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
