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
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import (
    EarthNet2021Config,
    _discover_npz_files,
    _infer_data_format,
    _xarray_to_hw,
    _xarray_to_time,
)
from data.earthnet_conditioning import EOBS_VARIABLES, conditioning_schema_dict


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
) -> dict[str, Any]:
    """Compute the JSON payload used by :class:`ConditioningStatsV2`.

    The public function is intentionally testable without invoking argparse or
    writing to the repository.  It fails instead of silently skipping an
    invalid cube, because skipping changes the claimed train population.
    """

    if not files:
        raise ValueError("Cannot build Stage2-v2 conditioning statistics from zero files")
    daily_moments = _RunningMoments(width=len(EOBS_VARIABLES))
    geo_moments = _RunningMoments(width=1)
    any_valid_window = np.zeros(len(EOBS_VARIABLES), dtype=np.int64)
    all_five_valid_window = np.zeros(len(EOBS_VARIABLES), dtype=np.int64)

    for index, path in enumerate(files, start=1):
        if _infer_data_format(path, "auto") != "netcdf":
            raise ValueError(
                f"{path}: Stage2-v2 conditioning statistics only support NetCDF cubes"
            )
        daily, dem = _read_v2_daily_and_dem(path)
        daily_moments.update_columns(daily)
        geo_moments.update_flat(dem)
        daily_valid = np.isfinite(daily).reshape(30, 5, len(EOBS_VARIABLES))
        any_valid_window += daily_valid.any(axis=1).sum(axis=0)
        all_five_valid_window += daily_valid.all(axis=1).sum(axis=0)
        if progress_every > 0 and index % progress_every == 0:
            print(f"conditioning stats processed {index}/{len(files)}", flush=True)

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
    with Path(config_path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or not isinstance(config.get("data"), dict):
        raise ValueError(f"{config_path} must contain a top-level data mapping")
    data = config["data"]
    if data_root:
        data["root"] = data_root
    data.update(
        {
            "split": "train",
            "stage2_protocol": "greenearthnet_path_v2",
            "data_format": "netcdf",
            "file_glob": "**/*.nc",
            "manifest_path": manifest_path,
            "manifest_paths": {},
            "require_manifest": True,
            # The formal manifest itself is the training population.  A local
            # development holdout must not silently remove records from stats.
            "use_train_holdout": False,
            "conditioning_stats_path": None,
            "require_conditioning_stats": False,
            "strict": False,
        }
    )
    data_cfg = EarthNet2021Config.from_config(data, split="train")
    all_files = _discover_npz_files(data_cfg)
    if not all_files:
        raise FileNotFoundError("The supplied train manifest resolves to zero files")
    selected = all_files if max_files <= 0 else all_files[:max_files]
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("split") != "train":
        raise ValueError(
            f"conditioning stats require a train manifest, got split={manifest.get('split')!r}"
        )
    digest = manifest.get("files_sha256")
    if not isinstance(digest, str) or not digest:
        raise ValueError("train manifest has no valid files_sha256")
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
    args = parser.parse_args()

    if args.max_files < 0:
        raise ValueError("--max-files must be non-negative")
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
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
