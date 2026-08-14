#!/usr/bin/env python
"""Build immutable train-only statistics for the formal Stage2-v2 path.

The script reads exactly the files listed in a frozen *train* manifest.  It
does not reuse the legacy ``dgh_stats_train.json`` because the two contracts
normalize different quantities at different stages of aggregation.

Typical formal invocation (after the data audit is complete)::

    python scripts/build_earthnet_conditioning_stats.py \
      --config configs/train/stage2_earthnet_v2_data.yaml \
      --data-root /path/to/EarthNet2021 \
      --manifest-path artifacts/.../manifests/train.json \
      --output artifacts/.../conditioning_stats_v2_train.json \
      --require-full-train

For a cheap code-only smoke check, pass ``--max-files 64`` and do *not* use
the resulting file for a formal run: its ``is_full_train`` field is false.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import (
    _infer_data_format,
    _xarray_to_hw,
    _xarray_to_time,
)
from data.earthnet_conditioning import EOBS_VARIABLES, conditioning_schema_dict
from data.earthnet_manifest import (
    DATASET_ID,
    MANIFEST_SCHEMA_VERSION,
    PROTOCOL_ID,
    records_digest,
    resolve_dataset_root,
)
from train.train_stage2_earthnet import load_config


class _RunningMoments:
    """Numerically adequate streaming moments for scalar/raster valid values."""

    def __init__(self, width: int = 1):
        self.sum = np.zeros(width, dtype=np.float64)
        self.sum_sq = np.zeros(width, dtype=np.float64)
        self.count = np.zeros(width, dtype=np.int64)

    def update_columns(self, values: np.ndarray) -> None:
        array = np.asarray(values, dtype=np.float64)
        if array.ndim != 2 or array.shape[1] != self.sum.shape[0]:
            raise ValueError(
                f"Expected [N,{self.sum.shape[0]}] values, got {array.shape}"
            )
        valid = np.isfinite(array)
        self.sum += np.where(valid, array, 0.0).sum(axis=0)
        self.sum_sq += np.where(valid, array * array, 0.0).sum(axis=0)
        self.count += valid.sum(axis=0)

    def update_flat(self, values: np.ndarray) -> None:
        array = np.asarray(values, dtype=np.float64).reshape(-1)
        valid = np.isfinite(array)
        self.sum[0] += np.where(valid, array, 0.0).sum()
        self.sum_sq[0] += np.where(valid, array * array, 0.0).sum()
        self.count[0] += int(valid.sum())

    def mean_std(self) -> tuple[np.ndarray, np.ndarray]:
        counts = np.maximum(self.count, 1)
        mean = self.sum / counts
        variance = np.maximum(self.sum_sq / counts - mean * mean, 0.0)
        std = np.sqrt(variance)
        # A one-value/constant smoke set is not a valid formal statistic, but
        # emitting 1 keeps its loader semantics finite and clearly auditable.
        mean[self.count == 0] = 0.0
        std[(self.count <= 1) | (std <= 1e-12)] = 1.0
        return mean, std


def _read_v2_daily_and_dem(path: Path) -> tuple[np.ndarray, np.ndarray]:
    try:
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError(
            "EarthNet2021x conditioning statistics require xarray and netCDF4."
        ) from exc

    with xr.open_dataset(path, cache=False) as cube:
        required = [*(f"eobs_{name}" for name in EOBS_VARIABLES), "cop_dem"]
        missing = [name for name in required if name not in cube.variables]
        if missing:
            raise KeyError(f"{path}: v2 stats require {missing}")
        daily = np.stack(
            [
                _xarray_to_time(cube[f"eobs_{name}"], f"eobs_{name}")
                for name in EOBS_VARIABLES
            ],
            axis=1,
        ).astype(np.float32)
        if daily.shape[0] < 150:
            raise ValueError(
                f"{path}: expected at least 150 daily E-OBS values, got {daily.shape[0]}"
            )
        dem = _xarray_to_hw(cube["cop_dem"], "cop_dem").astype(np.float32)
    return daily[:150], dem


def _summarize_conditioning_file(
    path_text: str,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    float,
    float,
    int,
    np.ndarray,
    np.ndarray,
]:
    """Read one cube and return mergeable sufficient statistics.

    This function is deliberately module-level so it can run in a separate
    process.  Returning only sums/counts keeps parent-process memory bounded
    and makes the final reduction deterministic because the parent merges
    records in manifest order.
    """

    path = Path(path_text)
    if _infer_data_format(path, "auto") != "netcdf":
        raise ValueError(
            f"{path}: Stage2-v2 conditioning statistics only support NetCDF cubes"
        )
    daily, dem = _read_v2_daily_and_dem(path)
    daily_values = np.asarray(daily, dtype=np.float64)
    daily_valid = np.isfinite(daily_values)
    geo_values = np.asarray(dem, dtype=np.float64).reshape(-1)
    geo_valid = np.isfinite(geo_values)
    window_valid = daily_valid.reshape(30, 5, len(EOBS_VARIABLES))
    return (
        np.where(daily_valid, daily_values, 0.0).sum(axis=0),
        np.where(daily_valid, daily_values * daily_values, 0.0).sum(axis=0),
        daily_valid.sum(axis=0).astype(np.int64),
        float(np.where(geo_valid, geo_values, 0.0).sum()),
        float(np.where(geo_valid, geo_values * geo_values, 0.0).sum()),
        int(geo_valid.sum()),
        window_valid.any(axis=1).sum(axis=0).astype(np.int64),
        window_valid.all(axis=1).sum(axis=0).astype(np.int64),
    )


def _merge_conditioning_summary(
    daily_moments: _RunningMoments,
    geo_moments: _RunningMoments,
    summary: tuple[
        np.ndarray,
        np.ndarray,
        np.ndarray,
        float,
        float,
        int,
        np.ndarray,
        np.ndarray,
    ],
) -> tuple[np.ndarray, np.ndarray]:
    """Merge one file's sufficient statistics into the global accumulators."""

    (
        daily_sum,
        daily_sum_sq,
        daily_count,
        geo_sum,
        geo_sum_sq,
        geo_count,
        any_valid_window,
        all_five_valid_window,
    ) = summary
    daily_moments.sum += daily_sum
    daily_moments.sum_sq += daily_sum_sq
    daily_moments.count += daily_count
    geo_moments.sum[0] += geo_sum
    geo_moments.sum_sq[0] += geo_sum_sq
    geo_moments.count[0] += geo_count
    return any_valid_window, all_five_valid_window


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_conditioning_stats(
    files: Sequence[Path],
    *,
    manifest_sha256: str,
    manifest_path: str,
    is_full_train: bool,
    created_by_git_commit: str | None = None,
    progress_every: int = 1000,
    workers: int = 1,
) -> dict[str, Any]:
    """Compute the JSON payload used by :class:`ConditioningStatsV2`.

    The public function is intentionally testable without invoking argparse or
    writing to the repository.  It fails instead of silently skipping an
    invalid cube, because skipping changes the claimed train population.
    """

    if not files:
        raise ValueError("Cannot build Stage2-v2 conditioning statistics from zero files")
    if workers < 1:
        raise ValueError("workers must be at least 1")
    daily_moments = _RunningMoments(width=len(EOBS_VARIABLES))
    geo_moments = _RunningMoments(width=1)
    any_valid_window = np.zeros(len(EOBS_VARIABLES), dtype=np.int64)
    all_five_valid_window = np.zeros(len(EOBS_VARIABLES), dtype=np.int64)

    worker_count = min(int(workers), len(files))
    path_texts = [str(path) for path in files]
    if worker_count == 1:
        summaries = map(_summarize_conditioning_file, path_texts)
        executor = None
    else:
        # NetCDF/HDF5 handles are opened only inside child processes.  This is
        # safer than threaded reads and gives bounded I/O concurrency on a
        # network filesystem.  ``map`` preserves manifest order, so the parent
        # reduction and output provenance remain deterministic.
        chunk_size = max(1, len(files) // (worker_count * 8))
        executor = ProcessPoolExecutor(max_workers=worker_count)
        summaries = executor.map(
            _summarize_conditioning_file,
            path_texts,
            chunksize=chunk_size,
        )
    try:
        print(
            f"conditioning stats start: files={len(files)}, workers={worker_count}",
            flush=True,
        )
        for index, summary in enumerate(summaries, start=1):
            file_any_valid, file_all_five_valid = _merge_conditioning_summary(
                daily_moments,
                geo_moments,
                summary,
            )
            any_valid_window += file_any_valid
            all_five_valid_window += file_all_five_valid
            if progress_every > 0 and index % progress_every == 0:
                print(f"conditioning stats processed {index}/{len(files)}", flush=True)
    finally:
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)

    daily_mean, daily_std = daily_moments.mean_std()
    geo_mean, geo_std = geo_moments.mean_std()
    denominator = max(len(files) * 30, 1)
    schema = conditioning_schema_dict()
    raw_daily_variance = np.maximum(
        daily_moments.sum_sq / np.maximum(daily_moments.count, 1)
        - (daily_moments.sum / np.maximum(daily_moments.count, 1)) ** 2,
        0.0,
    )
    zero_variance = [
        name
        for name, count, variance in zip(
            EOBS_VARIABLES, daily_moments.count, raw_daily_variance
        )
        if int(count) <= 1 or float(variance) <= 1e-12
    ]
    geo_zero_variance = bool(
        int(geo_moments.count[0]) <= 1
        or np.isclose(
            geo_moments.sum_sq[0] / max(int(geo_moments.count[0]), 1),
            (geo_moments.sum[0] / max(int(geo_moments.count[0]), 1)) ** 2,
        )
    )
    return {
        **schema,
        "fit_split": "train",
        "manifest_sha256": manifest_sha256,
        "manifest_path": manifest_path,
        "num_files": len(files),
        "is_full_train": bool(is_full_train),
        "daily_mean": dict(zip(EOBS_VARIABLES, daily_mean.tolist())),
        "daily_std": dict(zip(EOBS_VARIABLES, daily_std.tolist())),
        "daily_valid_count": dict(
            zip(EOBS_VARIABLES, [int(value) for value in daily_moments.count])
        ),
        "daily_valid_fraction": dict(
            zip(
                EOBS_VARIABLES,
                (daily_moments.count / max(len(files) * 150, 1)).tolist(),
            )
        ),
        "window_any_valid_fraction": dict(
            zip(EOBS_VARIABLES, (any_valid_window / denominator).tolist())
        ),
        "window_all_five_valid_fraction": dict(
            zip(EOBS_VARIABLES, (all_five_valid_window / denominator).tolist())
        ),
        "g_variable": "cop_dem",
        "g_mean": float(geo_mean[0]),
        "g_std": float(geo_std[0]),
        "g_valid_count": int(geo_moments.count[0]),
        "g_zero_variance": geo_zero_variance,
        "zero_variance_daily_variables": zero_variance,
        "created_by_git_commit": created_by_git_commit or _git_commit(),
    }


def _load_train_files(
    config_path: str,
    *,
    data_root: str | None,
    manifest_path: str,
    max_files: int,
) -> tuple[list[Path], int, dict[str, Any]]:
    config = load_config(config_path)
    if not isinstance(config, dict) or not isinstance(config.get("data"), dict):
        raise ValueError(f"{config_path} must contain a top-level data mapping")
    data = config["data"]
    root_text = data_root or data.get("root")
    if not root_text:
        raise ValueError("A data root is required via --data-root or config data.root")

    dataset_root = resolve_dataset_root(root_text)
    manifest_source = Path(manifest_path)
    manifest = json.loads(manifest_source.read_text(encoding="utf-8"))
    if int(manifest.get("schema_version", -1)) != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported manifest schema in {manifest_source}: "
            f"{manifest.get('schema_version')!r}"
        )
    if manifest.get("dataset") != DATASET_ID:
        raise ValueError(
            f"Unexpected dataset in {manifest_source}: {manifest.get('dataset')!r}"
        )
    if manifest.get("protocol") != PROTOCOL_ID:
        raise ValueError(
            f"Unexpected manifest protocol in {manifest_source}: "
            f"expected={PROTOCOL_ID!r}, got={manifest.get('protocol')!r}"
        )

    records = manifest.get("files")
    if not isinstance(records, list):
        raise TypeError(f"Manifest {manifest_source} has no list-valued 'files' field")
    if int(manifest.get("num_files", -1)) != len(records):
        raise ValueError(f"Manifest {manifest_source} num_files does not match records")
    if manifest.get("files_sha256") != records_digest(records):
        raise ValueError(f"Manifest {manifest_source} record digest is invalid")

    manifest_role = str(manifest.get("role", manifest.get("split", "")))
    if manifest_role != "train":
        raise ValueError(
            "conditioning stats require a role='train' manifest, got "
            f"role={manifest_role!r}, split={manifest.get('split')!r}"
        )
    digest = manifest.get("files_sha256")
    if not isinstance(digest, str) or not digest:
        raise ValueError("train manifest has no valid files_sha256")

    all_files: list[Path] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise TypeError(f"Manifest {manifest_source} contains a non-object record")
        relative_text = str(record.get("path", ""))
        relative = Path(relative_text)
        if not relative_text or relative.is_absolute() or ".." in relative.parts:
            raise ValueError(
                f"Unsafe manifest path in {manifest_source}: {relative_text!r}"
            )
        if relative_text in seen:
            raise ValueError(
                f"Duplicate manifest path in {manifest_source}: {relative_text}"
            )
        seen.add(relative_text)
        all_files.append(dataset_root / relative)

    if [str(record["path"]) for record in records] != sorted(seen):
        raise ValueError(f"Manifest {manifest_source} records are not path-sorted")
    if not all_files:
        raise FileNotFoundError("The supplied train manifest contains zero files")

    selected = all_files if max_files <= 0 else all_files[:max_files]
    print(
        "conditioning stats manifest loaded: "
        f"files={len(all_files)}, selected={len(selected)}, root={dataset_root}",
        flush=True,
    )
    return selected, len(all_files), manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-root")
    parser.add_argument("--manifest-path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="0 means the full frozen train manifest; a positive value is smoke-only.",
    )
    parser.add_argument(
        "--require-full-train",
        action="store_true",
        help="Reject a smoke subset and require every record in the train manifest.",
    )
    parser.add_argument("--progress-every", type=int, default=1000)
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "Number of NetCDF reader processes. Use a modest value (typically 8) "
            "on shared storage; this is total preprocessing concurrency, not GPU count."
        ),
    )
    args = parser.parse_args()

    if args.max_files < 0:
        raise ValueError("--max-files must be non-negative")
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    print(f"conditioning stats loading manifest: {args.manifest_path}", flush=True)
    files, manifest_total, manifest = _load_train_files(
        args.config,
        data_root=args.data_root,
        manifest_path=args.manifest_path,
        max_files=args.max_files,
    )
    is_full_train = len(files) == manifest_total
    if args.require_full_train and not is_full_train:
        raise ValueError(
            f"--require-full-train received only {len(files)}/{manifest_total} manifest files"
        )
    report = build_conditioning_stats(
        files,
        manifest_sha256=manifest["files_sha256"],
        manifest_path=str(Path(args.manifest_path).resolve()),
        is_full_train=is_full_train,
        progress_every=args.progress_every,
        workers=args.workers,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
