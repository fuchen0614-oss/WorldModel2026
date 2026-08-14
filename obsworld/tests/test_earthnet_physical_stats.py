from __future__ import annotations

import importlib
import json
from pathlib import Path

import numpy as np
import pytest

xr = pytest.importorskip("xarray")

from data.earthnet_physical_conditioning import (  # noqa: E402
    PHYSICAL4_FEATURE_NAMES,
    PHYSICAL4_PROTOCOL,
    PhysicalDGHStats,
    canonicalize_physical4_daily,
)

MODULE = importlib.import_module("scripts.build_earthnet_physical_stats")


def _write_cube(path: Path, *, cube_index: int = 0, include_s2: bool = False) -> None:
    time = np.arange(
        np.datetime64("2018-04-28") + np.timedelta64(cube_index, "D"),
        np.datetime64("2018-04-28") + np.timedelta64(cube_index + 150, "D"),
    )
    fields = {
        "cop_dem": (("lat", "lon"), np.arange(16, dtype=np.float32).reshape(4, 4) + cube_index),
        "eobs_rr": (("time",), np.linspace(0.0, 5.0, 150, dtype=np.float32)),
        "eobs_tg": (("time",), np.linspace(10.0, 25.0, 150, dtype=np.float32)),
        "eobs_hu": (("time",), np.full(150, 50.0, dtype=np.float32)),
        "eobs_qq": (("time",), np.full(150, 100.0, dtype=np.float32)),
    }
    if cube_index == 1:
        values = fields["eobs_rr"][1].copy()
        values[0] = np.nan
        fields["eobs_rr"] = (("time",), values)
    if include_s2:
        shape = (150, 4, 4)
        for name, value in (("s2_B02", 1000.0), ("s2_B03", 1200.0), ("s2_B04", 1400.0), ("s2_B8A", 1800.0)):
            fields[name] = (("time", "lat", "lon"), np.full(shape, value, dtype=np.float32))
        fields["s2_mask"] = (("time", "lat", "lon"), np.zeros(shape, dtype=np.float32))
    xr.Dataset(
        fields,
        coords={"time": time, "lat": np.arange(4), "lon": np.arange(4)},
    ).to_netcdf(path)


def test_physical_stats_schema_and_all_five_coverage(tmp_path):
    paths = []
    for index in range(2):
        path = tmp_path / f"34TDP_2018-04-28_2018-09-24_{index:03d}.nc"
        _write_cube(path, cube_index=index)
        paths.append(path)

    report = MODULE.build_physical_stats(
        paths,
        manifest_sha256="frozen-physical-manifest",
        manifest_path="/immutable/train_dev.json",
        is_full_train=False,
        created_by_git_commit="test-commit",
        progress_every=0,
        workers=1,
    )
    stats = PhysicalDGHStats.from_mapping(report)

    assert report["driver_protocol"] == PHYSICAL4_PROTOCOL
    assert report["feature_names"] == list(PHYSICAL4_FEATURE_NAMES)
    assert report["feature_valid_count"]["precip_sum_5d"] == 59
    assert report["feature_valid_count"]["temp_mean_5d"] == 60
    assert report["window_all_five_valid_fraction"]["rr"] == pytest.approx(59 / 60)
    assert report["vpd_window_all_five_valid_fraction"] == pytest.approx(1.0)
    assert stats.g_std > 0
    assert stats.manifest_sha256 == "frozen-physical-manifest"


def test_physical_stats_parallel_matches_serial(tmp_path):
    paths = []
    for index in range(3):
        path = tmp_path / f"34TDP_2018-04-28_2018-09-24_{index:03d}.nc"
        _write_cube(path, cube_index=index)
        paths.append(path)
    kwargs = {
        "manifest_sha256": "digest",
        "manifest_path": "/immutable/train.json",
        "is_full_train": True,
        "created_by_git_commit": "test-commit",
        "progress_every": 0,
    }
    serial = MODULE.build_physical_stats(paths, workers=1, **kwargs)
    parallel = MODULE.build_physical_stats(paths, workers=2, **kwargs)
    assert parallel["feature_valid_count"] == serial["feature_valid_count"]
    assert parallel["raw_daily_valid_count"] == serial["raw_daily_valid_count"]
    assert parallel["feature_mean"] == pytest.approx(serial["feature_mean"])
    assert parallel["feature_std"] == pytest.approx(serial["feature_std"])
    assert parallel["g_mean"] == pytest.approx(serial["g_mean"])
    assert parallel["g_std"] == pytest.approx(serial["g_std"])
    assert parallel["vpd_clip_value"] == pytest.approx(serial["vpd_clip_value"])


def test_physical_loader_returns_four_dimensional_path(tmp_path):
    path = tmp_path / "train" / "34TDP_2018-04-28_2018-09-24_000.nc"
    path.parent.mkdir(parents=True)
    _write_cube(path, include_s2=True)
    stats_report = MODULE.build_physical_stats(
        [path],
        manifest_sha256="digest",
        manifest_path="/immutable/train.json",
        is_full_train=True,
        progress_every=0,
    )
    stats_path = tmp_path / "physical4_stats.json"
    stats_path.write_text(json.dumps(stats_report), encoding="utf-8")

    from data.datasets.earthnet2021 import EarthNet2021Config, EarthNet2021Dataset

    config = EarthNet2021Config.from_config(
        {
            "root": str(tmp_path),
            "split": "train",
            "data_format": "netcdf",
            "stage2_protocol": "earthnet2021x_path_v2",
            "driver_protocol": "physical4_v1",
            "file_glob": "**/*.nc",
            "context_frames": 10,
            "target_frames": 20,
            "frame_interval_days": 5,
            "netcdf_s2_offset_days": 4,
            "model_img_size": 4,
            "context_img_size": 4,
            "target_img_size": 4,
            "geo_img_size": 4,
            "eval_img_size": 4,
            "formal_dem_variable": "cop_dem",
            "netcdf_dem_variables": ["cop_dem"],
            "conditioning_stats_path": str(stats_path),
            "require_conditioning_stats": True,
            "require_manifest": False,
            "use_train_holdout": False,
            "strict": True,
            "band_spec": {"input_bands": ["blue", "green", "red", "nir"], "target_bands": ["blue", "green", "red", "nir"]},
        }
    )
    sample = EarthNet2021Dataset(config)[0]
    assert tuple(sample["D_path"].shape) == (30, 4)
    assert tuple(sample["D_mask"].shape) == (30, 4)
    assert tuple(sample["D_valid_day_count"].shape) == (30, 4)
    assert tuple(sample["G"].shape) == (1, 4, 4)
    assert sample["meta"]["driver_protocol"] == PHYSICAL4_PROTOCOL



def test_physical_preflight_accepts_matching_manifest_and_stats(tmp_path):
    from data.earthnet_manifest import build_manifest, write_manifest
    from scripts import preflight_stage2_earthnet as preflight

    cube = tmp_path / "train" / "34TDP_2018-04-28_2018-09-24_000.nc"
    cube.parent.mkdir(parents=True)
    _write_cube(cube, include_s2=True)
    manifest_path = write_manifest(build_manifest(tmp_path, "train"), tmp_path / "train_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stats_report = MODULE.build_physical_stats(
        [cube],
        manifest_sha256=manifest["files_sha256"],
        manifest_path=str(manifest_path),
        is_full_train=True,
        progress_every=0,
    )
    stats_path = tmp_path / "physical4_stats.json"
    stats_path.write_text(json.dumps(stats_report), encoding="utf-8")
    config = {
        "data": {
            "root": str(tmp_path),
            "split": "train",
            "data_format": "netcdf",
            "stage2_protocol": "earthnet2021x_path_v2",
            "driver_protocol": "physical4_v1",
            "file_glob": "**/*.nc",
            "context_frames": 10,
            "target_frames": 20,
            "frame_interval_days": 5,
            "netcdf_s2_offset_days": 4,
            "model_img_size": 4,
            "context_img_size": 4,
            "target_img_size": 4,
            "geo_img_size": 4,
            "eval_img_size": 4,
            "formal_dem_variable": "cop_dem",
            "netcdf_dem_variables": ["cop_dem"],
            "manifest_path": str(manifest_path),
            "require_manifest": True,
            "verify_manifest_exists": False,
            "use_train_holdout": False,
            "conditioning_stats_path": str(stats_path),
            "require_conditioning_stats": True,
            "strict": True,
        },
        "training": {
            "require_conditioning_stats": True,
            "require_full_conditioning_stats": True,
            "require_all_driver_features": True,
            "min_driver_valid_fraction": 0.9,
            "require_geo": True,
        },
    }
    data_report = preflight._scan_data(config, max_files=0)
    stats_check = preflight._check_stats(config)
    assert data_report["fatal_reasons"] == []
    assert data_report["driver_protocol"] == PHYSICAL4_PROTOCOL
    assert data_report["D_path_valid_fraction"]["precip_sum_5d"] == pytest.approx(1.0)
    assert stats_check["driver_protocol"] == PHYSICAL4_PROTOCOL
    assert stats_check["driver_coverage_ok"] is True


def test_physical4_unit_adapter_is_explicit_and_rejects_invalid_humidity():
    raw = np.asarray(
        [[1.0, 293.15, 0.5, 100.0], [2.0, 293.15, 0.5, 200.0]],
        dtype=np.float32,
    )
    converted = canonicalize_physical4_daily(raw)
    assert converted[:, 1].tolist() == pytest.approx([20.0, 20.0])
    assert converted[:, 2].tolist() == pytest.approx([50.0, 50.0])
    assert converted[:, 3].tolist() == pytest.approx([8.64, 17.28])
    invalid = raw.copy()
    invalid[0, 2] = 120.0
    with pytest.raises(ValueError, match="refusing to clip"):
        canonicalize_physical4_daily(invalid)
