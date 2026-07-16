from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest


xr = pytest.importorskip("xarray")

from data.earthnet_conditioning import EOBS_VARIABLES, ConditioningStatsV2
from data.earthnet_manifest import build_manifest, write_manifest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_earthnet_conditioning_stats.py"
SPEC = importlib.util.spec_from_file_location("build_earthnet_conditioning_stats", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

PREFLIGHT_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "preflight_stage2_earthnet.py"
PREFLIGHT_SPEC = importlib.util.spec_from_file_location("preflight_stage2_earthnet", PREFLIGHT_SCRIPT)
PREFLIGHT = importlib.util.module_from_spec(PREFLIGHT_SPEC)
assert PREFLIGHT_SPEC.loader is not None
PREFLIGHT_SPEC.loader.exec_module(PREFLIGHT)


def test_stats_v2_records_train_manifest_provenance_and_validity(tmp_path):
    path = tmp_path / "34TDP_2018-04-28_2018-09-24_000.nc"
    time = np.arange(
        np.datetime64("2018-04-28"),
        np.datetime64("2018-04-28") + np.timedelta64(150, "D"),
    )
    fields = {
        "cop_dem": (("lat", "lon"), np.arange(16, dtype=np.float32).reshape(4, 4))
    }
    for index, name in enumerate(EOBS_VARIABLES):
        values = np.arange(150, dtype=np.float32) + 10.0 * index
        if name == "fg":
            values[0] = np.nan
        fields[f"eobs_{name}"] = (("time",), values)
    xr.Dataset(
        fields,
        coords={"time": time, "lat": np.arange(4), "lon": np.arange(4)},
    ).to_netcdf(path)

    report = MODULE.build_conditioning_stats(
        [path],
        manifest_sha256="frozen-manifest-digest",
        manifest_path="/immutable/train.json",
        is_full_train=False,
        created_by_git_commit="test-commit",
        progress_every=0,
    )
    stats = ConditioningStatsV2.from_mapping(report)

    assert report["manifest_sha256"] == "frozen-manifest-digest"
    assert report["is_full_train"] is False
    assert report["daily_valid_count"]["fg"] == 149
    assert report["window_any_valid_fraction"]["fg"] == pytest.approx(1.0)
    assert report["window_all_five_valid_fraction"]["fg"] == pytest.approx(29 / 30)
    assert report["g_variable"] == "cop_dem"
    assert stats.num_files == 1
    assert stats.manifest_sha256 == "frozen-manifest-digest"


def test_stats_v2_parallel_reduction_matches_single_process(tmp_path):
    paths = []
    for cube_index in range(3):
        path = tmp_path / f"34TDP_2018-04-28_2018-09-24_{cube_index:03d}.nc"
        time = np.arange(
            np.datetime64("2018-04-28"),
            np.datetime64("2018-04-28") + np.timedelta64(150, "D"),
        )
        fields = {
            "cop_dem": (
                ("lat", "lon"),
                np.arange(16, dtype=np.float32).reshape(4, 4) + cube_index,
            )
        }
        for index, name in enumerate(EOBS_VARIABLES):
            values = np.arange(150, dtype=np.float32) + 10.0 * index + cube_index
            if name == "fg" and cube_index == 1:
                values[0] = np.nan
            fields[f"eobs_{name}"] = (("time",), values)
        xr.Dataset(
            fields,
            coords={"time": time, "lat": np.arange(4), "lon": np.arange(4)},
        ).to_netcdf(path)
        paths.append(path)

    common = {
        "manifest_sha256": "frozen-manifest-digest",
        "manifest_path": "/immutable/train.json",
        "is_full_train": True,
        "created_by_git_commit": "test-commit",
        "progress_every": 0,
    }
    serial = MODULE.build_conditioning_stats(paths, workers=1, **common)
    parallel = MODULE.build_conditioning_stats(paths, workers=2, **common)

    assert parallel["num_files"] == serial["num_files"]
    assert parallel["daily_valid_count"] == serial["daily_valid_count"]
    assert parallel["g_valid_count"] == serial["g_valid_count"]
    assert parallel["daily_mean"] == pytest.approx(serial["daily_mean"])
    assert parallel["daily_std"] == pytest.approx(serial["daily_std"])
    assert parallel["g_mean"] == pytest.approx(serial["g_mean"])
    assert parallel["g_std"] == pytest.approx(serial["g_std"])
    assert parallel["window_any_valid_fraction"] == pytest.approx(
        serial["window_any_valid_fraction"]
    )
    assert parallel["window_all_five_valid_fraction"] == pytest.approx(
        serial["window_all_five_valid_fraction"]
    )


def test_v2_preflight_accepts_matching_full_manifest_and_stats(tmp_path):
    dataset_root = tmp_path / "earthnet2021x"
    cube_dir = dataset_root / "train" / "34TDP"
    cube_dir.mkdir(parents=True)
    path = cube_dir / "34TDP_2018-04-28_2018-09-24_000.nc"
    time = np.arange(
        np.datetime64("2018-04-28"),
        np.datetime64("2018-04-28") + np.timedelta64(150, "D"),
    )
    fields = {
        "s2_B02": (("time", "lat", "lon"), np.ones((150, 4, 4), np.float32)),
        "s2_B03": (("time", "lat", "lon"), np.ones((150, 4, 4), np.float32)),
        "s2_B04": (("time", "lat", "lon"), np.ones((150, 4, 4), np.float32)),
        "s2_B8A": (("time", "lat", "lon"), np.ones((150, 4, 4), np.float32)),
        "s2_mask": (("time", "lat", "lon"), np.zeros((150, 4, 4), np.float32)),
        "cop_dem": (("lat", "lon"), np.arange(16, dtype=np.float32).reshape(4, 4)),
    }
    for index, name in enumerate(EOBS_VARIABLES):
        fields[f"eobs_{name}"] = (
            ("time",),
            np.arange(150, dtype=np.float32) + index,
        )
    xr.Dataset(
        fields,
        coords={"time": time, "lat": np.arange(4), "lon": np.arange(4)},
    ).to_netcdf(path)

    manifest_path = write_manifest(
        build_manifest(tmp_path, "train"), tmp_path / "train_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stats_payload = MODULE.build_conditioning_stats(
        [path],
        manifest_sha256=manifest["files_sha256"],
        manifest_path=str(manifest_path),
        is_full_train=True,
        created_by_git_commit="test-commit",
        progress_every=0,
    )
    stats_path = tmp_path / "conditioning_stats_v2_train.json"
    stats_path.write_text(json.dumps(stats_payload), encoding="utf-8")

    config = {
        "data": {
            "root": str(tmp_path),
            "split": "train",
            "data_format": "netcdf",
            "stage2_protocol": "earthnet2021x_path_v2",
            "file_glob": "**/*.nc",
            "context_frames": 10,
            "target_frames": 20,
            "frame_interval_days": 5,
            "netcdf_s2_offset_days": 4,
            "model_img_size": 8,
            "context_img_size": 8,
            "eval_img_size": 4,
            "target_img_size": 4,
            "geo_img_size": 4,
            "formal_dem_variable": "cop_dem",
            "manifest_path": str(manifest_path),
            "require_manifest": True,
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
    data_report = PREFLIGHT._scan_data(config, max_files=0)
    stats_report = PREFLIGHT._check_stats(config)

    assert data_report["fatal_reasons"] == []
    assert data_report["D_path_valid_fraction"]["mean_fg"] == pytest.approx(1.0)
    assert stats_report["is_full_train"] is True
    assert stats_report["g_variable"] == "cop_dem"
