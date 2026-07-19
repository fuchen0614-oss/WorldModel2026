"""Tests for eval/stage2_result_statistics.py (item3 main-experiment stats)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.greenearthnet_protocol import expected_prediction_times, target_ndvi
from eval.stage2_result_statistics import (
    aggregate_horizon_curves,
    paired_per_cube_frame,
    per_horizon_ndvi_metrics,
    tile_cluster_paired_bootstrap,
    tile_of,
)


def _synthetic_target(n_time: int = 150, n_lat: int = 6, n_lon: int = 6) -> xr.Dataset:
    """A fully-clear, temporally-varying, HQ-eligible synthetic minicube."""

    time = np.arange(n_time)
    lat = np.arange(n_lat, dtype=float)
    lon = np.arange(n_lon, dtype=float)
    phase = (lat[:, None] + lon[None, :]) * 0.3
    ndvi = 0.5 + 0.2 * np.sin(2 * np.pi * time[:, None, None] / 30.0 + phase[None])
    b04 = np.full((n_time, n_lat, n_lon), 0.2, dtype=float)
    b8a = b04 * (1.0 + ndvi) / (1.0 - ndvi)
    zeros = np.zeros((n_time, n_lat, n_lon), dtype=float)
    scl = np.full((n_time, n_lat, n_lon), 4, dtype=float)
    thw = ("time", "lat", "lon")
    coords = {"time": time, "lat": lat, "lon": lon}
    return xr.Dataset(
        {
            "s2_B8A": (thw, b8a),
            "s2_B04": (thw, b04),
            "s2_dlmask": (thw, zeros),
            "s2_SCL": (thw, scl),
            "esawc_lc": (("lat", "lon"), np.full((n_lat, n_lon), 10.0)),
            "geom_cls": (("lat", "lon"), np.zeros((n_lat, n_lon))),
            "cop_dem": (("lat", "lon"), np.zeros((n_lat, n_lon))),
        },
        coords=coords,
    )


def _prediction_from_ndvi(target: xr.Dataset, offset: float = 0.0) -> xr.Dataset:
    times = expected_prediction_times(target)
    true = target_ndvi(target).sel(time=times)
    pred = (true + offset).clip(-1, 1)
    return xr.Dataset({"ndvi_pred": pred})


def test_perfect_prediction_gives_zero_rmse_unit_r2():
    target = _synthetic_target()
    pred = _prediction_from_ndvi(target, offset=0.0)
    frame = per_horizon_ndvi_metrics(target, pred, cube_id="29SND_x")
    assert list(frame["horizon_day"]) == [5 * (i + 1) for i in range(20)]
    scored = frame[frame["n"] > 0]
    assert len(scored) == 20
    assert scored["rmse"].max() < 1e-6
    r2 = scored["r2_spatial"].dropna()
    assert len(r2) >= 18 and (r2 > 0.999).all()


def test_constant_offset_rmse_matches_offset():
    target = _synthetic_target()
    pred = _prediction_from_ndvi(target, offset=0.1)
    frame = per_horizon_ndvi_metrics(target, pred)
    scored = frame[frame["n"] > 0]
    assert np.allclose(scored["rmse"], 0.1, atol=1e-6)


def test_aggregate_pooling_matches_single_cube():
    target = _synthetic_target()
    pred = _prediction_from_ndvi(target, offset=0.05)
    f1 = per_horizon_ndvi_metrics(target, pred, cube_id="a")
    f2 = per_horizon_ndvi_metrics(target, pred, cube_id="b")
    pooled = aggregate_horizon_curves([f1, f2])
    assert np.allclose(pooled["rmse"], f1["rmse"], atol=1e-9, equal_nan=True)
    # Two identical cubes: pooled global-mean R2 == per-cube R2.
    assert np.allclose(pooled["r2_spatial"], f1["r2_spatial"], atol=1e-9, equal_nan=True)
    assert (pooled["n"] == 2 * f1["n"]).all()


def test_bootstrap_identical_models_ci_contains_zero():
    rng = np.random.default_rng(0)
    ids = [f"{t}_{k}" for t in ("29SND", "30UMC", "31TCJ") for k in range(20)]
    vals = rng.normal(0.3, 0.05, size=len(ids))
    a = pd.DataFrame({"id": ids, "rmse": vals})
    b = pd.DataFrame({"id": ids, "rmse": vals.copy()})
    paired = paired_per_cube_frame(a, b, value_col="rmse")
    out = tile_cluster_paired_bootstrap(paired, n_boot=500)
    assert out["ci_low"] <= 0.0 <= out["ci_high"]
    assert out["significant"] is False
    assert out["n_clusters"] == 3


def test_bootstrap_uniformly_better_model_is_significant():
    ids = [f"{t}_{k}" for t in ("29SND", "30UMC", "31TCJ", "32ULC") for k in range(15)]
    base = pd.DataFrame({"id": ids, "rmse": np.full(len(ids), 0.30)})
    model = pd.DataFrame({"id": ids, "rmse": np.full(len(ids), 0.25)})
    paired = paired_per_cube_frame(base, model, value_col="rmse")
    assert np.allclose(paired["diff"], 0.05)
    out = tile_cluster_paired_bootstrap(paired, n_boot=500)
    assert out["ci_low"] > 0.0
    assert out["significant"] is True


def test_nan_metrics_are_dropped_not_propagated():
    # A cube with a NaN metric (e.g. r2 undefined) must not poison the CI.
    ids = [f"{t}_{k}" for t in ("29SND", "30UMC") for k in range(10)]
    a = pd.DataFrame({"id": ids, "r2": np.full(len(ids), 0.4)})
    b = pd.DataFrame({"id": ids, "r2": np.full(len(ids), 0.5)})
    a.loc[0, "r2"] = np.nan  # one undefined value
    paired = paired_per_cube_frame(a, b, value_col="r2")
    assert len(paired) == len(ids) - 1  # NaN row dropped
    out = tile_cluster_paired_bootstrap(paired, n_boot=300)
    assert np.isfinite(out["ci_low"]) and np.isfinite(out["ci_high"])


def test_single_cluster_raises():
    ids = [f"29SND_{k}" for k in range(10)]  # one tile only
    a = pd.DataFrame({"id": ids, "rmse": np.linspace(0.2, 0.4, len(ids))})
    b = pd.DataFrame({"id": ids, "rmse": np.linspace(0.25, 0.45, len(ids))})
    paired = paired_per_cube_frame(a, b, value_col="rmse")
    with pytest.raises(ValueError, match="clusters"):
        tile_cluster_paired_bootstrap(paired, n_boot=100)


def test_tile_of_and_empty_guards():
    assert tile_of("29SND_2017-06-10_...") == "29SND"
    with pytest.raises(ValueError):
        tile_cluster_paired_bootstrap(pd.DataFrame({"diff": []}))
    with pytest.raises(ValueError):
        aggregate_horizon_curves([])
