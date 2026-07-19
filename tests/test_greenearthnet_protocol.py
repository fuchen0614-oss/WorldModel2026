from __future__ import annotations

import numpy as np
import pytest

xr = pytest.importorskip("xarray")

from eval.greenearthnet_protocol import (
    PREDICTION_GRID_CLIMATOLOGY_DAILY,
    compute_pixel_metrics,
    expected_climatology_prediction_times,
    expected_prediction_times,
    make_prediction_dataset,
    summarize_score_parquets,
    summarize_scores,
    target_ndvi,
    validate_prediction_dataset,
)


def _target_cube() -> xr.Dataset:
    time = np.arange(
        np.datetime64("2019-01-01"),
        np.datetime64("2019-01-01") + np.timedelta64(150, "D"),
    )
    lat = np.arange(2)
    lon = np.arange(3)
    phase = np.linspace(0, 4 * np.pi, 150, dtype=np.float32)
    ndvi = 0.35 + 0.25 * np.sin(phase)
    red = np.full((150, 2, 3), 0.2, dtype=np.float32)
    nir_1d = 0.2 * (1.0 + ndvi) / (1.0 - ndvi)
    nir = np.broadcast_to(nir_1d[:, None, None], red.shape).copy()
    clear = np.zeros_like(red, dtype=np.int16)
    scl = np.full_like(red, 4, dtype=np.int16)
    return xr.Dataset(
        {
            "s2_B04": (("time", "lat", "lon"), red),
            "s2_B8A": (("time", "lat", "lon"), nir),
            "s2_dlmask": (("time", "lat", "lon"), clear),
            "s2_SCL": (("time", "lat", "lon"), scl),
            "esawc_lc": (("lat", "lon"), np.full((2, 3), 10, np.int16)),
            "geom_cls": (("lat", "lon"), np.ones((2, 3), np.int16)),
            "cop_dem": (("lat", "lon"), np.ones((2, 3), np.float32)),
        },
        coords={"time": time, "lat": lat, "lon": lon},
    )


def _perfect_prediction(target: xr.Dataset) -> xr.Dataset:
    times = expected_prediction_times(target)
    values = target_ndvi(target).sel(time=times).values.astype(np.float32)
    return xr.Dataset(
        {"ndvi_pred": (("time", "lat", "lon"), values)},
        coords={"time": times, "lat": target.lat, "lon": target.lon},
    )


def test_official_metrics_are_perfect_for_ground_truth_prediction():
    target = _target_cube()
    prediction = _perfect_prediction(target)
    validate_prediction_dataset(target, prediction)
    frame = compute_pixel_metrics(target, prediction).reset_index()
    frame["id"] = "cube"
    frame["season"] = "region"
    assert len(frame) == 6
    summary = summarize_scores(frame)
    assert summary["rmse"] == pytest.approx(0.0, abs=1e-7)
    assert summary["biasabs"] == pytest.approx(0.0, abs=1e-7)
    assert summary["R2"] == pytest.approx(1.0, abs=1e-6)
    assert summary["nse"] == pytest.approx(1.0, abs=1e-6)
    assert summary["rmse_0_5"] == pytest.approx(0.0, abs=1e-7)


def test_prediction_export_uses_rgbn_and_official_times():
    target = _target_cube()
    times = expected_prediction_times(target)
    red = target.s2_B04.sel(time=times).values
    nir = target.s2_B8A.sel(time=times).values
    rgbn = np.stack([red * 0, red * 0, red, nir], axis=1)
    prediction = make_prediction_dataset(target, rgbn)
    validate_prediction_dataset(target, prediction)
    np.testing.assert_allclose(
        prediction.ndvi_pred.values,
        target_ndvi(target).sel(time=times).values,
        atol=1e-6,
    )


def test_timestamp_mismatch_is_rejected():
    target = _target_cube()
    prediction = _perfect_prediction(target).assign_coords(
        time=expected_prediction_times(target).values + np.timedelta64(1, "D")
    )
    with pytest.raises(ValueError, match="timestamps"):
        validate_prediction_dataset(target, prediction)


def test_streaming_parquet_aggregation_matches_in_memory(tmp_path):
    target = _target_cube()
    prediction = _perfect_prediction(target)
    prediction["ndvi_pred"] = prediction.ndvi_pred * 0.9 + 0.01
    frame = compute_pixel_metrics(target, prediction).reset_index()
    frame["id"] = "cube"
    frame["season"] = "region"
    expected = summarize_scores(frame)
    frame.to_parquet(tmp_path / "scores_en21x_region.parquet", index=False)
    actual = summarize_score_parquets(tmp_path)
    for key in ("nse", "rmse", "R2", "biasabs", "rmse_0_5"):
        assert actual[key] == pytest.approx(expected[key], rel=1e-7, abs=1e-7)



def test_public_climatology_daily_grid_is_explicit_and_valid():
    target = _target_cube()
    times = expected_climatology_prediction_times(target)
    assert times.size == 100
    prediction = xr.Dataset(
        {"ndvi_pred": (("time", "lat", "lon"), target_ndvi(target).sel(time=times).values)},
        coords={"time": times, "lat": target.lat, "lon": target.lon},
    )
    validate_prediction_dataset(
        target,
        prediction,
        prediction_grid=PREDICTION_GRID_CLIMATOLOGY_DAILY,
    )
    frame = compute_pixel_metrics(
        target,
        prediction,
        prediction_grid=PREDICTION_GRID_CLIMATOLOGY_DAILY,
    )
    assert not frame.empty
