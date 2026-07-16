#!/usr/bin/env python
"""Audit a local EarthNet2021x mirror and optionally compare it with S3."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


SPLITS = ("train", "iid", "ood", "extreme", "seasonal")
S3_ENDPOINT = "https://s3.bgc-jena.mpg.de:9000"
S3_PREFIX = "earthnet/earthnet2021x"
EOBS_VARIABLES = (
    "eobs_fg",
    "eobs_hu",
    "eobs_pp",
    "eobs_qq",
    "eobs_rr",
    "eobs_tg",
    "eobs_tn",
    "eobs_tx",
)
LEGACY_DGH_REQUIRED_VARIABLES = (
    "s2_B02",
    "s2_B03",
    "s2_B04",
    "s2_B8A",
    "s2_mask",
    "eobs_hu",
    "eobs_qq",
    "eobs_rr",
    "eobs_tg",
)
EARTHNET2021X_STANDARD_REQUIRED_VARIABLES = (
    "s2_B02",
    "s2_B03",
    "s2_B04",
    "s2_B8A",
    "s2_mask",
    "s2_dlmask",
    "s2_SCL",
    *EOBS_VARIABLES,
    "esawc_lc",
    "geom_cls",
    "cop_dem",
)
DEM_VARIABLES = ("nasa_dem", "alos_dem", "cop_dem")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check EarthNet2021x split coverage and NetCDF integrity."
    )
    parser.add_argument(
        "--schema",
        choices=("earthnet2021x-standard", "legacy-dgh"),
        default="earthnet2021x-standard",
        help=(
            "earthnet2021x-standard requires all eight E-OBS fields and "
            "standard evaluation variables; legacy-dgh checks only the old "
            "9-D path."
        ),
    )
    parser.add_argument(
        "--root",
        required=True,
        help="EarthNet parent, earthnet2021x root, or one split directory.",
    )
    parser.add_argument(
        "--required-splits",
        nargs="+",
        default=["all"],
        choices=[*SPLITS, "all"],
        help="Splits that must exist. Use train for immediate training or all for the full benchmark.",
    )
    parser.add_argument(
        "--scan-mode",
        choices=("none", "metadata", "full"),
        default="metadata",
        help="metadata opens sampled files; full also reads required arrays.",
    )
    parser.add_argument(
        "--max-files-per-split",
        type=int,
        default=20,
        help="Files inspected per split in metadata mode; 0 inspects every file.",
    )
    parser.add_argument(
        "--compare-remote",
        action="store_true",
        help="Compare local relative paths with the official anonymous S3 listing.",
    )
    parser.add_argument(
        "--compare-sizes",
        action="store_true",
        help="Also stat every local file and compare byte sizes; slow on network filesystems.",
    )
    parser.add_argument("--proxy", help="Optional HTTP proxy for the S3 client.")
    parser.add_argument("--output", help="Optional JSON report path.")
    return parser.parse_args()


def resolve_dataset_root(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.name in SPLITS:
        return path.parent
    if path.name.lower() == "earthnet2021x":
        return path
    nested = path / "earthnet2021x"
    if nested.is_dir():
        return nested
    return path


def choose_evenly(files: list[Path], limit: int) -> list[Path]:
    if limit <= 0 or len(files) <= limit:
        return files
    if limit == 1:
        return [files[0]]
    indices = {
        round(index * (len(files) - 1) / (limit - 1))
        for index in range(limit)
    }
    return [files[index] for index in sorted(indices)]


def discover_netcdf_files(split_root: Path) -> list[Path]:
    """Walk once without a separate stat call for every file."""

    files: list[Path] = []
    if not split_root.is_dir():
        return files
    for directory, _, filenames in os.walk(split_root):
        base = Path(directory)
        files.extend(base / name for name in filenames if name.endswith(".nc"))
    files.sort()
    return files


def audit_netcdf(
    path: Path,
    read_arrays: bool,
    required_variables: tuple[str, ...],
) -> dict[str, Any]:
    try:
        import numpy as np
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError(
            "NetCDF scanning requires xarray and a backend such as netCDF4. "
            "Install repository requirements first."
        ) from exc

    result: dict[str, Any] = {"path": str(path), "ok": False}
    try:
        with xr.open_dataset(path, decode_times=False, cache=False) as cube:
            variables = set(cube.variables)
            missing = sorted(set(required_variables) - variables)
            has_dem = any(name in variables for name in DEM_VARIABLES)
            sizes = {name: int(value) for name, value in cube.sizes.items()}
            problems: list[str] = []
            if missing:
                problems.append(f"missing variables: {missing}")
            if not has_dem:
                problems.append(f"missing DEM; expected one of {DEM_VARIABLES}")
            for dimension in ("time", "lat", "lon"):
                if sizes.get(dimension, 0) <= 0:
                    problems.append(f"missing or empty dimension: {dimension}")
            if sizes.get("time", 0) < 150:
                problems.append(f"time dimension shorter than 150: {sizes.get('time', 0)}")
            if read_arrays and not problems:
                names_to_read = list(required_variables)
                if not any(name in names_to_read for name in DEM_VARIABLES):
                    names_to_read.append(next(v for v in DEM_VARIABLES if v in variables))
                for name in names_to_read:
                    values = cube[name].values
                    if values.size == 0:
                        problems.append(f"empty variable: {name}")
                    elif not np.issubdtype(values.dtype, np.number):
                        problems.append(f"non-numeric variable: {name}")
            result.update(
                {
                    "ok": not problems,
                    "sizes": sizes,
                    "missing_variables": missing,
                    "eobs_variables": [name for name in EOBS_VARIABLES if name in variables],
                    "dem_variables": [name for name in DEM_VARIABLES if name in variables],
                    "problems": problems,
                }
            )
    except Exception as exc:  # A report is more useful than stopping at the first bad cube.
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def local_split_report(
    dataset_root: Path,
    split: str,
    scan_mode: str,
    max_files: int,
    required_variables: tuple[str, ...],
) -> tuple[dict[str, Any], list[Path]]:
    split_root = dataset_root / split
    print(f"[audit] discovering local {split} files under {split_root}", flush=True)
    files = discover_netcdf_files(split_root)
    print(f"[audit] found {len(files)} local {split} NetCDF files", flush=True)
    tile_counts = Counter(path.parent.name for path in files)
    selected = (
        files
        if scan_mode == "full"
        else choose_evenly(files, max_files)
        if scan_mode == "metadata"
        else []
    )
    inspections = []
    for index, path in enumerate(selected, start=1):
        print(
            f"[audit] opening {split} sample {index}/{len(selected)}: {path.name}",
            flush=True,
        )
        inspections.append(
            audit_netcdf(
                path,
                read_arrays=(scan_mode == "full"),
                required_variables=required_variables,
            )
        )
    selected_sizes = {
        str(path): path.stat().st_size
        for path in selected
        if path.exists()
    }
    report = {
        "directory": str(split_root),
        "exists": split_root.is_dir(),
        "num_files": len(files),
        "num_regions": len(tile_counts),
        "files_per_region": {
            "min": min(tile_counts.values(), default=0),
            "median": _median(tile_counts.values()),
            "max": max(tile_counts.values(), default=0),
        },
        "total_bytes": None,
        "size_scope": (
            "selected_files_only"
            if selected
            else "not_collected"
        ),
        "zero_byte_files": [
            path for path, size in selected_sizes.items() if size == 0
        ],
        "scanned_files": len(inspections),
        "scan_failures": [item for item in inspections if not item["ok"]],
    }
    return report, files


def _median(values: Iterable[int]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def remote_listing(split: str, proxy: str | None) -> dict[str, int]:
    try:
        import s3fs
    except ImportError as exc:
        raise RuntimeError(
            "--compare-remote requires s3fs (installed by the earthnet package)."
        ) from exc
    client_kwargs = {"endpoint_url": S3_ENDPOINT, "region_name": "thuringia"}
    config_kwargs = {"proxies": {"http": proxy, "https": proxy}} if proxy else {}
    s3 = s3fs.S3FileSystem(
        anon=True,
        client_kwargs=client_kwargs,
        config_kwargs=config_kwargs,
    )
    prefix = f"{S3_PREFIX}/{split}"
    print(
        f"[audit] requesting official S3 listing for {split}; "
        "the server may take several minutes",
        flush=True,
    )
    details = s3.find(prefix, detail=True)
    print(f"[audit] official S3 listing returned {len(details)} objects", flush=True)
    output: dict[str, int] = {}
    for remote_path, metadata in details.items():
        if not remote_path.endswith(".nc"):
            continue
        relative = remote_path[len(prefix) + 1 :]
        output[relative] = int(metadata.get("size", -1))
    return output


def compare_with_remote(
    split: str,
    split_root: Path,
    local_files: list[Path],
    proxy: str | None,
    compare_sizes: bool,
) -> dict[str, Any]:
    remote = remote_listing(split, proxy)
    local_paths = {
        path.relative_to(split_root).as_posix(): path for path in local_files
    }
    missing = sorted(set(remote) - set(local_paths))
    extra = sorted(set(local_paths) - set(remote))
    size_mismatches = []
    if compare_sizes:
        common = sorted(set(local_paths) & set(remote))
        for index, name in enumerate(common, start=1):
            if index == 1 or index % 1000 == 0 or index == len(common):
                print(
                    f"[audit] comparing local sizes {index}/{len(common)}",
                    flush=True,
                )
            local_size = local_paths[name].stat().st_size
            if remote[name] >= 0 and local_size != remote[name]:
                size_mismatches.append(
                    {
                        "path": name,
                        "local_bytes": local_size,
                        "remote_bytes": remote[name],
                    }
                )
    complete = not missing and not extra and (
        not compare_sizes or not size_mismatches
    )
    return {
        "remote_num_files": len(remote),
        "sizes_compared": compare_sizes,
        "missing_files_count": len(missing),
        "extra_files_count": len(extra),
        "size_mismatches_count": (
            len(size_mismatches) if compare_sizes else None
        ),
        "missing_files_preview": missing[:50],
        "extra_files_preview": extra[:50],
        "size_mismatches_preview": size_mismatches[:50],
        "complete": complete,
    }


def main() -> int:
    args = parse_args()
    dataset_root = resolve_dataset_root(Path(args.root))
    required_variables = (
        EARTHNET2021X_STANDARD_REQUIRED_VARIABLES
        if args.schema == "earthnet2021x-standard"
        else LEGACY_DGH_REQUIRED_VARIABLES
    )
    required = set(SPLITS if "all" in args.required_splits else args.required_splits)
    report: dict[str, Any] = {
        "dataset_root": str(dataset_root),
        "required_splits": sorted(required),
        "scan_mode": args.scan_mode,
        "schema": args.schema,
        "required_variables": list(required_variables),
        "remote_comparison_requested": args.compare_remote,
        "remote_size_comparison_requested": args.compare_sizes,
        "splits": {},
    }
    all_stems: list[str] = []
    failed = False

    for split in SPLITS:
        split_scan_mode = args.scan_mode if split in required else "none"
        split_report, files = local_split_report(
            dataset_root,
            split,
            split_scan_mode,
            args.max_files_per_split,
            required_variables,
        )
        if split in required:
            all_stems.extend(path.stem for path in files)
        if split in required and (not split_report["exists"] or not files):
            failed = True
        if split in required and (
            split_report["zero_byte_files"] or split_report["scan_failures"]
        ):
            failed = True
        if args.compare_remote and split in required:
            try:
                remote_report = compare_with_remote(
                    split,
                    dataset_root / split,
                    files,
                    args.proxy,
                    args.compare_sizes,
                )
                split_report["remote"] = remote_report
                if not remote_report["complete"]:
                    failed = True
            except Exception as exc:
                split_report["remote_error"] = f"{type(exc).__name__}: {exc}"
                failed = True
        report["splits"][split] = split_report

    duplicate_ids = sorted(
        name for name, count in Counter(all_stems).items() if count > 1
    )
    report["duplicate_minicube_ids_count"] = len(duplicate_ids)
    report["duplicate_minicube_ids_preview"] = duplicate_ids[:50]
    if duplicate_ids:
        failed = True
    report["status"] = "PASS" if not failed else "FAIL"
    report["meaning"] = (
        "All requested checks passed."
        if not failed
        else "One or more required splits, files, variables, or remote objects are missing/corrupt."
    )

    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
