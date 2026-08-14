#!/usr/bin/env python
# Build train-only statistics for the original physical DGH protocol.
# Formal runs read only the frozen role=train manifest; --max-files is smoke-only.

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import (
    _infer_data_format,
    _xarray_to_hw,
    _xarray_to_time,
)
from data.earthnet_physical_conditioning import (
    PHYSICAL4_DEFAULT_SOLAR_SCALE,
    PHYSICAL4_RAW_VARIABLES,
    PHYSICAL4_FEATURE_NAMES,
    aggregate_physical_dgh_path,
    canonicalize_physical4_daily,
    compute_vpd_kpa,
    physical4_schema_dict,
)
from train.train_stage2_earthnet import load_config
from scripts.build_earthnet_conditioning_stats import _load_train_files


class _RunningMoments:
    def __init__(self, width: int):
        self.sum = np.zeros(width, dtype=np.float64)
        self.sum_sq = np.zeros(width, dtype=np.float64)
        self.count = np.zeros(width, dtype=np.int64)

    def update_columns(self, values: np.ndarray, mask: np.ndarray) -> None:
        values = np.asarray(values, dtype=np.float64)
        mask = np.asarray(mask, dtype=bool)
        if values.shape != mask.shape or values.ndim != 2:
            raise ValueError(f"values/mask must have matching [N,D] shape, got {values.shape} and {mask.shape}")
        self.sum += np.where(mask, values, 0.0).sum(axis=0)
        self.sum_sq += np.where(mask, values * values, 0.0).sum(axis=0)
        self.count += mask.sum(axis=0).astype(np.int64)

    def mean_std(self) -> tuple[np.ndarray, np.ndarray]:
        count = np.maximum(self.count, 1)
        mean = self.sum / count
        variance = np.maximum(self.sum_sq / count - mean * mean, 0.0)
        std = np.sqrt(variance)
        mean[self.count == 0] = 0.0
        std[(self.count <= 1) | (std <= 1e-12)] = 1.0
        return mean, std


def _read_physical_file(
    path_text: str,
    solar_scale: float = PHYSICAL4_DEFAULT_SOLAR_SCALE,
) -> tuple[np.ndarray, float, float, int]:
    path = Path(path_text)
    if not np.isfinite(float(solar_scale)) or float(solar_scale) <= 0:
        raise ValueError(f"solar_scale must be positive and finite, got {solar_scale}")
    if _infer_data_format(path, "auto") != "netcdf":
        raise ValueError(f"{path}: physical4 statistics require NetCDF cubes")
    try:
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError("physical4 statistics require xarray and netCDF4") from exc
    with xr.open_dataset(path, cache=False) as cube:
        required = [*(f"eobs_{name}" for name in PHYSICAL4_RAW_VARIABLES), "cop_dem"]
        missing = [name for name in required if name not in cube.variables]
        if missing:
            raise KeyError(f"{path}: physical4 stats require {missing}")
        daily = canonicalize_physical4_daily(
            np.stack(
                [
                    _xarray_to_time(cube["eobs_rr"], "eobs_rr"),
                    _xarray_to_time(cube["eobs_tg"], "eobs_tg"),
                    _xarray_to_time(cube["eobs_hu"], "eobs_hu"),
                    _xarray_to_time(cube["eobs_qq"], "eobs_qq"),
                ],
                axis=1,
            ),
            solar_scale=float(solar_scale),
        )
        if daily.shape[0] < 150:
            raise ValueError(f"{path}: expected at least 150 daily rows, got {daily.shape[0]}")
        dem = _xarray_to_hw(cube["cop_dem"], "cop_dem").astype(np.float64).reshape(-1)
    valid = np.isfinite(dem)
    return daily[:150], float(np.where(valid, dem, 0.0).sum()), float(np.where(valid, dem * dem, 0.0).sum()), int(valid.sum())


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _read_summaries(
    files: Sequence[Path],
    workers: int,
    progress_every: int,
    solar_scale: float,
) -> list[tuple[np.ndarray, float, float, int]]:
    worker_count = min(max(int(workers), 1), len(files))
    paths = [str(path) for path in files]
    print(f"physical4 stats start: files={len(paths)}, workers={worker_count}", flush=True)
    if worker_count == 1:
        iterator = map(_read_physical_file, paths, [float(solar_scale)] * len(paths))
        executor = None
    else:
        executor = ProcessPoolExecutor(max_workers=worker_count)
        iterator = executor.map(
            _read_physical_file,
            paths,
            [float(solar_scale)] * len(paths),
            chunksize=max(1, len(paths) // (worker_count * 8)),
        )
    summaries = []
    try:
        for index, summary in enumerate(iterator, start=1):
            summaries.append(summary)
            if progress_every > 0 and index % progress_every == 0:
                print(f"physical4 stats read {index}/{len(paths)}", flush=True)
    finally:
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
    return summaries


def build_physical_stats(
    files: Sequence[Path],
    *,
    manifest_sha256: str,
    manifest_path: str,
    is_full_train: bool,
    created_by_git_commit: str | None = None,
    progress_every: int = 1000,
    workers: int = 1,
    vpd_clip_quantile: float = 0.995,
    vpd_clip_value: float | None = None,
    netcdf_solar_scale: float = PHYSICAL4_DEFAULT_SOLAR_SCALE,
) -> dict[str, Any]:
    if not files:
        raise ValueError("Cannot build physical4 statistics from zero files")
    if not 0.0 < float(vpd_clip_quantile) <= 1.0:
        raise ValueError("vpd_clip_quantile must lie in (0,1]")
    if workers < 1:
        raise ValueError("workers must be at least 1")

    summaries = _read_summaries(files, workers, progress_every, float(netcdf_solar_scale))
    vpd_values: list[np.ndarray] = []
    raw_daily_valid = np.zeros(4, dtype=np.int64)
    raw_any_windows = np.zeros(4, dtype=np.int64)
    raw_all_five_windows = np.zeros(4, dtype=np.int64)
    vpd_all_five_windows = 0
    for daily, _, _, _ in summaries:
        finite = np.isfinite(daily)
        raw_daily_valid += finite.sum(axis=0).astype(np.int64)
        window_valid = finite.reshape(30, 5, 4)
        raw_any_windows += window_valid.any(axis=1).sum(axis=0).astype(np.int64)
        raw_all_five_windows += window_valid.all(axis=1).sum(axis=0).astype(np.int64)
        vpd = compute_vpd_kpa(daily[:, 1], daily[:, 2])
        vpd_finite = np.isfinite(vpd)
        if vpd_finite.any():
            vpd_values.append(vpd[vpd_finite].astype(np.float32))
        vpd_all_five_windows += int((finite[:, 1] & finite[:, 2]).reshape(30, 5).all(axis=1).sum())

    if vpd_clip_value is None:
        if not vpd_values:
            raise ValueError("physical4 train files contain no finite VPD values")
        clip = float(np.quantile(np.concatenate(vpd_values), float(vpd_clip_quantile)))
    else:
        clip = float(vpd_clip_value)
    if not np.isfinite(clip) or clip <= 0:
        raise ValueError(f"vpd_clip_value must be positive and finite, got {clip}")

    feature_moments = _RunningMoments(width=4)
    feature_valid = np.zeros(4, dtype=np.int64)
    geo_moments = _RunningMoments(width=1)
    for index, (daily, dem_sum, dem_sum_sq, dem_count) in enumerate(summaries, start=1):
        path = aggregate_physical_dgh_path(daily)
        values = path.values.astype(np.float32).copy()
        values[:, 0] = np.log1p(np.maximum(values[:, 0], 0.0))
        values[:, 2] = np.minimum(values[:, 2], clip)
        values[:, 3] = np.log1p(np.maximum(values[:, 3], 0.0))
        mask = path.mask > 0
        feature_moments.update_columns(values, mask)
        feature_valid += mask.sum(axis=0).astype(np.int64)
        geo_moments.sum[0] += dem_sum
        geo_moments.sum_sq[0] += dem_sum_sq
        geo_moments.count[0] += dem_count
        if progress_every > 0 and index % progress_every == 0:
            print(f"physical4 stats reduced {index}/{len(summaries)}", flush=True)

    feature_mean, feature_std = feature_moments.mean_std()
    g_mean, g_std = geo_moments.mean_std()
    denominator = max(len(files) * 30, 1)
    daily_denominator = max(len(files) * 150, 1)
    return {
        **physical4_schema_dict(),
        "fit_split": "train",
        "manifest_sha256": manifest_sha256,
        "manifest_path": manifest_path,
        "num_files": len(files),
        "is_full_train": bool(is_full_train),
        "feature_mean": dict(zip(PHYSICAL4_FEATURE_NAMES, feature_mean.tolist())),
        "feature_std": dict(zip(PHYSICAL4_FEATURE_NAMES, feature_std.tolist())),
        "feature_valid_count": dict(zip(PHYSICAL4_FEATURE_NAMES, [int(x) for x in feature_valid])),
        "feature_valid_fraction": dict(zip(PHYSICAL4_FEATURE_NAMES, (feature_valid / denominator).tolist())),
        "raw_daily_valid_count": dict(zip(PHYSICAL4_RAW_VARIABLES, [int(x) for x in raw_daily_valid])),
        "raw_daily_valid_fraction": dict(zip(PHYSICAL4_RAW_VARIABLES, (raw_daily_valid / daily_denominator).tolist())),
        "window_any_valid_fraction": dict(zip(PHYSICAL4_RAW_VARIABLES, (raw_any_windows / denominator).tolist())),
        "window_all_five_valid_fraction": dict(zip(PHYSICAL4_RAW_VARIABLES, (raw_all_five_windows / denominator).tolist())),
        "vpd_window_all_five_valid_fraction": float(vpd_all_five_windows / denominator),
        "vpd_valid_count": int(sum(len(values) for values in vpd_values)),
        "vpd_clip_quantile": float(vpd_clip_quantile),
        "vpd_clip_value": clip,
        "vpd_clip_policy": "train_quantile" if vpd_clip_value is None else "fixed_override",
        "netcdf_solar_scale": float(netcdf_solar_scale),
        "g_variable": "cop_dem",
        "g_mean": float(g_mean[0]),
        "g_std": float(g_std[0]),
        "g_valid_count": int(geo_moments.count[0]),
        "created_by_git_commit": created_by_git_commit or _git_commit(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-root")
    parser.add_argument("--manifest-path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-files", type=int, default=0, help="0 means the full frozen manifest")
    parser.add_argument("--require-full-train", action="store_true")
    parser.add_argument("--progress-every", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--vpd-clip-quantile", type=float, default=0.995)
    parser.add_argument("--vpd-clip-value", type=float)
    args = parser.parse_args()
    if args.max_files < 0 or args.workers < 1:
        raise ValueError("--max-files must be non-negative and --workers must be positive")
    merged_config = load_config(args.config)
    configured_scale = float(
        merged_config.get("data", {}).get(
            "netcdf_solar_scale", PHYSICAL4_DEFAULT_SOLAR_SCALE
        )
    )
    files, manifest_total, manifest = _load_train_files(
        args.config,
        data_root=args.data_root,
        manifest_path=args.manifest_path,
        max_files=args.max_files,
    )
    is_full_train = len(files) == manifest_total
    if args.require_full_train and not is_full_train:
        raise ValueError(f"--require-full-train received {len(files)}/{manifest_total} files")
    report = build_physical_stats(
        files,
        manifest_sha256=manifest["files_sha256"],
        manifest_path=str(Path(args.manifest_path).resolve()),
        is_full_train=is_full_train,
        progress_every=args.progress_every,
        workers=args.workers,
        vpd_clip_quantile=args.vpd_clip_quantile,
        vpd_clip_value=args.vpd_clip_value,
        netcdf_solar_scale=configured_scale,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
