#!/usr/bin/env python
"""Audit a candidate GreenEarthNet / EarthNet2021x composite data layout.

Why this exists
---------------
The names ``EarthNet2021x`` and ``GreenEarthNet`` are related in the public
code, but they do *not* by themselves identify one evaluation protocol.  A
common server layout has a full raw ``earthnet2021x`` release in one location
and already-chopped GreenEarthNet validation/test tracks in another.  Mixing
them by a recursive glob would make a result irreproducible and can silently
mix the legacy EarthNet2021 ENS protocol with the CVPR-2024 GreenEarthNet
protocol.

This script is deliberately read-only.  It reports the two roots separately,
checks the directory-level prerequisites for the official GreenEarthNet main
track, and can inspect a few NetCDF schemas when xarray is available.  It
does not claim that file counts alone prove an official release, and it never
creates symlinks or downloads data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RAW_SPLITS = ("train", "iid", "ood", "extreme", "seasonal")
GREEN_TRACKS = (
    "val_chopped",
    "iid_chopped",
    "ood-t_chopped",
    "ood-s_chopped",
    "ood-st_chopped",
)
PRIMARY_GREEN_TRACKS = ("val_chopped", "ood-t_chopped")
REQUIRED_GREEN_SCHEMA_FIELDS = (
    "s2_B02",
    "s2_B03",
    "s2_B04",
    "s2_B8A",
    "s2_mask",
    "s2_dlmask",
    "s2_SCL",
    "eobs_fg",
    "eobs_hu",
    "eobs_pp",
    "eobs_qq",
    "eobs_rr",
    "eobs_tg",
    "eobs_tn",
    "eobs_tx",
    "esawc_lc",
    "geom_cls",
    "cop_dem",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit for a candidate GreenEarthNet protocol assembled "
            "from an EarthNet2021x raw root and an optional chopped-track root."
        )
    )
    parser.add_argument(
        "--raw-root",
        required=True,
        help=(
            "Root containing the raw EarthNet2021x release, or its parent. "
            "It must supply train/ for any GreenEarthNet training run."
        ),
    )
    parser.add_argument(
        "--eval-root",
        help=(
            "Root containing val_chopped/iid_chopped/ood-*_chopped. Defaults "
            "to the resolved raw root when all tracks live together."
        ),
    )
    parser.add_argument(
        "--sample-schema",
        action="store_true",
        help=(
            "Open evenly-spaced NetCDF samples with xarray and check the fields "
            "needed by the Stage2-v2 loader and GreenEarthNet evaluator."
        ),
    )
    parser.add_argument(
        "--max-files-per-group",
        type=int,
        default=3,
        help="Maximum number of NetCDF samples opened for each group (default: 3).",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON report path. Parent directories are created.",
    )
    parser.add_argument(
        "--strict-main",
        action="store_true",
        help=(
            "Return exit code 2 unless train/, val_chopped/, and "
            "ood-t_chopped/ are present and nonempty; with --sample-schema, "
            "also require sampled schemas to pass."
        ),
    )
    return parser.parse_args()


def resolve_raw_root(root: str | Path) -> Path:
    """Resolve a parent directory or the physical ``earthnet2021x`` root."""

    candidate = Path(root).expanduser().resolve()
    if candidate.name.lower() == "earthnet2021x":
        return candidate
    nested = candidate / "earthnet2021x"
    return nested if nested.is_dir() else candidate


def discover_netcdf_files(root: Path) -> list[Path]:
    """Return sorted NetCDF files without a second tree walk or glob fallback."""

    if not root.is_dir():
        return []
    paths: list[Path] = []
    for directory, _, filenames in os.walk(root):
        base = Path(directory)
        paths.extend(base / name for name in filenames if name.endswith(".nc"))
    paths.sort()
    return paths


def choose_evenly(paths: list[Path], limit: int) -> list[Path]:
    if limit < 0:
        raise ValueError("--max-files-per-group must be non-negative")
    if limit == 0 or len(paths) <= limit:
        return paths
    if limit == 1:
        return [paths[0]]
    indices = {
        round(index * (len(paths) - 1) / (limit - 1))
        for index in range(limit)
    }
    return [paths[index] for index in sorted(indices)]


def group_report(root: Path, name: str) -> tuple[dict[str, Any], list[Path]]:
    group_root = root / name
    paths = discover_netcdf_files(group_root)
    regions = Counter(path.parent.name for path in paths)
    return (
        {
            "directory": str(group_root),
            "exists": group_root.is_dir(),
            "is_symlink": group_root.is_symlink(),
            "num_netcdf_files": len(paths),
            "num_regions": len(regions),
            "files_per_region": {
                "min": min(regions.values(), default=0),
                "max": max(regions.values(), default=0),
            },
            "first_relative_path": (
                paths[0].relative_to(group_root).as_posix() if paths else None
            ),
        },
        paths,
    )


def inspect_schema(paths: Iterable[Path]) -> dict[str, Any]:
    """Inspect fields/dimensions while keeping all data arrays lazy."""

    try:
        import xarray as xr
    except ImportError as exc:
        return {
            "available": False,
            "ok": False,
            "error": (
                "xarray is unavailable; activate the WorldModel environment before "
                "using --sample-schema (" + type(exc).__name__ + ")"
            ),
            "samples": [],
        }

    samples: list[dict[str, Any]] = []
    for path in paths:
        result: dict[str, Any] = {"path": str(path), "ok": False}
        try:
            with xr.open_dataset(path, decode_times=False, cache=False) as cube:
                variables = set(cube.variables)
                missing = sorted(set(REQUIRED_GREEN_SCHEMA_FIELDS) - variables)
                sizes = {key: int(value) for key, value in cube.sizes.items()}
                problems: list[str] = []
                if missing:
                    problems.append(f"missing fields: {missing}")
                for dimension in ("time", "lat", "lon"):
                    if sizes.get(dimension, 0) <= 0:
                        problems.append(f"missing or empty dimension: {dimension}")
                if sizes.get("time", 0) < 150:
                    problems.append(
                        f"time dimension is shorter than the 150-day protocol: {sizes.get('time', 0)}"
                    )
                result.update(
                    {
                        "ok": not problems,
                        "missing_fields": missing,
                        "sizes": sizes,
                        "problems": problems,
                    }
                )
        except Exception as exc:  # Keep the report useful for partially corrupt releases.
            result["error"] = f"{type(exc).__name__}: {exc}"
        samples.append(result)
    return {
        "available": True,
        "ok": bool(samples) and all(sample.get("ok", False) for sample in samples),
        "samples": samples,
    }


def audit_layout(
    raw_root: str | Path,
    *,
    eval_root: str | Path | None = None,
    sample_schema: bool = False,
    max_files_per_group: int = 3,
) -> dict[str, Any]:
    """Return a JSON-serializable layout/schema report without changing data."""

    raw = resolve_raw_root(raw_root)
    evaluation = Path(eval_root).expanduser().resolve() if eval_root else raw

    raw_groups: dict[str, dict[str, Any]] = {}
    raw_paths: dict[str, list[Path]] = {}
    for name in RAW_SPLITS:
        report, paths = group_report(raw, name)
        raw_groups[name] = report
        raw_paths[name] = paths

    track_groups: dict[str, dict[str, Any]] = {}
    track_paths: dict[str, list[Path]] = {}
    for name in GREEN_TRACKS:
        report, paths = group_report(evaluation, name)
        track_groups[name] = report
        track_paths[name] = paths

    has_train = bool(raw_groups["train"]["num_netcdf_files"])
    has_val = bool(track_groups["val_chopped"]["num_netcdf_files"])
    has_ood_t = bool(track_groups["ood-t_chopped"]["num_netcdf_files"])
    layout_ready = has_train and has_val and has_ood_t
    missing_main = [
        label
        for label, present in (
            ("raw-root/train", has_train),
            ("eval-root/val_chopped", has_val),
            ("eval-root/ood-t_chopped", has_ood_t),
        )
        if not present
    ]

    schema: dict[str, Any] = {"requested": sample_schema, "groups": {}}
    if sample_schema:
        inspected = {
            "train": choose_evenly(raw_paths["train"], max_files_per_group),
            **{
                name: choose_evenly(track_paths[name], max_files_per_group)
                for name in PRIMARY_GREEN_TRACKS
            },
        }
        for name, paths in inspected.items():
            schema["groups"][name] = inspect_schema(paths)
    schema_ready = (
        not sample_schema
        or all(group.get("ok", False) for group in schema["groups"].values())
    )

    if layout_ready and schema_ready:
        recommendation = (
            "Candidate layout is ready for a separately frozen GreenEarthNet "
            "protocol manifest. Before a paper run, also verify raw/chopped "
            "sample identity and use the CVPR-2024 evaluator only."
        )
    elif has_train and has_ood_t:
        recommendation = (
            "Training data and the OOD-t test track exist, but the official "
            "GreenEarthNet validation track is missing or empty. Do not label a "
            "run as the full official GreenEarthNet protocol; use a documented "
            "train-only development holdout only for code pilots."
        )
    elif has_train:
        recommendation = (
            "Raw training data exist, but the required GreenEarthNet chopped "
            "main-track layout is incomplete. Keep this root separate from any "
            "legacy EarthNet2021 ENS experiment."
        )
    else:
        recommendation = (
            "No usable raw train split was found. Do not start a Stage2 training "
            "run from this layout."
        )

    return {
        "schema_version": 1,
        "candidate_protocol": "greenearthnet_cvpr2024_v1",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_root": str(raw),
        "evaluation_root": str(evaluation),
        "raw_release_groups": raw_groups,
        "greenearthnet_track_groups": track_groups,
        "readiness": {
            "raw_train_available": has_train,
            "official_validation_available": has_val,
            "official_ood_t_available": has_ood_t,
            "layout_ready_for_greenearthnet_main": layout_ready,
            "schema_ready_for_greenearthnet_main": schema_ready,
            "missing_main_requirements": missing_main,
            "recommendation": recommendation,
        },
        "schema_audit": schema,
        "notes": [
            "File counts are inventory evidence only; they do not prove split provenance.",
            "The script never merges raw/chopped roots and never falls back to a root-wide glob.",
            "A legacy EarthNet2021 ENS experiment and the GreenEarthNet CVPR-2024 evaluator are mutually exclusive paper protocols.",
        ],
    }


def main() -> int:
    args = parse_args()
    report = audit_layout(
        args.raw_root,
        eval_root=args.eval_root,
        sample_schema=args.sample_schema,
        max_files_per_group=args.max_files_per_group,
    )
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")

    ready = bool(report["readiness"]["layout_ready_for_greenearthnet_main"])
    if args.sample_schema:
        ready = ready and bool(report["readiness"]["schema_ready_for_greenearthnet_main"])
    return 0 if (ready or not args.strict_main) else 2


if __name__ == "__main__":
    raise SystemExit(main())
