#!/usr/bin/env python
"""Build train-only normalization statistics for EarthNet Stage2 D features."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import (
    EarthNet2021Config,
    _build_driver_features,
    _discover_npz_files,
    _earthnet2021x_driver_spec,
    _extract_meso_features,
    _extract_netcdf_weather,
    _infer_data_format,
    _load_external_drivers,
    _parse_start_date,
    _xarray_start_date,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/train/stage2_earthnet_main.yaml")
    parser.add_argument("--data-root", type=str)
    parser.add_argument("--external-driver-root", type=str)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-files", type=int)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Fail if any configured D feature is absent from the train split.",
    )
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if args.data_root:
        config["data"]["root"] = args.data_root
    if args.external_driver_root:
        config["data"]["external_driver_root"] = args.external_driver_root
    config["data"]["dgh_stats_path"] = None
    config["data"]["split"] = "train"
    data_cfg = EarthNet2021Config.from_config(config["data"], split="train")
    files = _discover_npz_files(data_cfg)
    if args.max_files:
        files = files[: args.max_files]
    if not files:
        raise FileNotFoundError(
            f"No train files matching {data_cfg.file_glob!r} found under "
            f"{data_cfg.root}"
        )

    dim = data_cfg.driver_spec.dim
    sums = np.zeros(dim, dtype=np.float64)
    sums_sq = np.zeros(dim, dtype=np.float64)
    counts = np.zeros(dim, dtype=np.int64)

    for index, path in enumerate(files, start=1):
        data_format = _infer_data_format(path, data_cfg.data_format)
        time_offset_days = 0
        driver_spec = data_cfg.driver_spec
        if data_format == "netcdf":
            try:
                import xarray as xr
            except ImportError as exc:
                raise RuntimeError(
                    "EarthNet2021x statistics require xarray and netCDF4."
                ) from exc
            with xr.open_dataset(path, cache=False) as cube:
                meso = _extract_netcdf_weather(cube, data_cfg)
                start_date = _xarray_start_date(cube) or _parse_start_date(path.name)
            external_drivers = None
            external_channel_map = None
            driver_spec = _earthnet2021x_driver_spec(data_cfg)
            time_offset_days = data_cfg.netcdf_s2_offset_days
        else:
            with np.load(path, allow_pickle=True) as cube:
                arrays = {key: cube[key] for key in cube.files}
            meso = _extract_meso_features(
                arrays,
                crop_size=data_cfg.meso_crop_size,
            )
            start_date = _parse_start_date(path.name)
            external_drivers, external_channel_map = _load_external_drivers(
                path, data_cfg
            )
        features, mask = _build_driver_features(
            meso=meso,
            num_targets=data_cfg.target_frames,
            context_frames=data_cfg.context_frames,
            frame_interval_days=data_cfg.frame_interval_days,
            meso_steps_per_image=data_cfg.meso_steps_per_image,
            driver_spec=driver_spec,
            start_date=start_date,
            external_drivers=external_drivers,
            external_channel_map=external_channel_map,
            time_offset_days=time_offset_days,
        )
        valid = mask > 0
        sums += np.where(valid, features, 0.0).sum(axis=0)
        sums_sq += np.where(valid, features * features, 0.0).sum(axis=0)
        counts += valid.sum(axis=0)
        if index % 1000 == 0:
            print(f"processed {index}/{len(files)}", flush=True)

    safe_counts = np.maximum(counts, 1)
    mean = sums / safe_counts
    variance = np.maximum(sums_sq / safe_counts - mean * mean, 0.0)
    std = np.sqrt(variance)
    mean[counts == 0] = 0.0
    std[counts <= 1] = 1.0

    report = {
        "dataset": (
            "EarthNet2021x"
            if data_cfg.data_format in {"netcdf", "nc", "earthnet2021x"}
            else "EarthNet2021"
        ),
        "fit_split": "train",
        "num_files": len(files),
        "target_frames_per_file": data_cfg.target_frames,
        "expected_valid_count_per_feature": len(files) * data_cfg.target_frames,
        "feature_names": data_cfg.driver_spec.feature_names,
        "driver_mean": mean.tolist(),
        "driver_std": std.tolist(),
        "valid_count": counts.tolist(),
        "valid_fraction": (
            counts / max(len(files) * data_cfg.target_frames, 1)
        ).tolist(),
        "missing_features": [
            name
            for name, count in zip(data_cfg.driver_spec.feature_names, counts)
            if count == 0
        ],
        "incomplete_features": [
            name
            for name, count in zip(data_cfg.driver_spec.feature_names, counts)
            if count < len(files) * data_cfg.target_frames
        ],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.require_complete and report["incomplete_features"]:
        raise RuntimeError(
            "Incomplete D construction; these features are not valid for every "
            f"train horizon: {report['incomplete_features']}"
        )


if __name__ == "__main__":
    main()
