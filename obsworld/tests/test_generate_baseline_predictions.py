"""Tests for eval/generate_baseline_predictions.py (item2 Persistence baseline)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.generate_baseline_predictions import persistence_ndvi
from eval.greenearthnet_protocol import (
    expected_prediction_times,
    target_ndvi,
    validate_prediction_dataset,
)


def _target(n_time: int = 150, n_lat: int = 5, n_lon: int = 5, unclear_pixel=None) -> xr.Dataset:
    time = np.arange(n_time)
    lat = np.arange(n_lat, dtype=float)
    lon = np.arange(n_lon, dtype=float)
    ndvi = (0.3 + 0.002 * time)[:, None, None] * np.ones((n_time, n_lat, n_lon))
    b04 = np.full((n_time, n_lat, n_lon), 0.2)
    b8a = b04 * (1.0 + ndvi) / (1.0 - ndvi)
    dlmask = np.zeros((n_time, n_lat, n_lon))
    if unclear_pixel is not None:
        py, px = unclear_pixel
        dlmask[:, py, px] = 1.0  # never clear at this pixel
    thw = ("time", "lat", "lon")
    return xr.Dataset(
        {
            "s2_B8A": (thw, b8a),
            "s2_B04": (thw, b04),
            "s2_dlmask": (thw, dlmask),
            "s2_SCL": (thw, np.full((n_time, n_lat, n_lon), 4.0)),
        },
        coords={"time": time, "lat": lat, "lon": lon},
    )


def test_persistence_equals_last_clear_context_value():
    target = _target()
    pred = persistence_ndvi(target)
    validate_prediction_dataset(target, pred)  # correct dims/time/coords
    # The public persistence reference keeps five-daily context frames
    # 4,9,...,49; the final permitted context observation is index 49.
    start = int(expected_prediction_times(target).values[0])
    assert start == 54
    last_ctx_ndvi = float(target_ndvi(target).isel(time=49).mean())
    values = pred["ndvi_pred"].values
    assert np.allclose(values, last_ctx_ndvi, atol=1e-4)
    # Held constant across all 20 target steps.
    assert np.allclose(values, values[0][None], atol=1e-7)


def test_never_clear_pixel_falls_back_to_half():
    target = _target(unclear_pixel=(0, 0))
    pred = persistence_ndvi(target)
    assert np.allclose(pred["ndvi_pred"].values[:, 0, 0], 0.5, atol=1e-6)
    # A clear pixel is unaffected.
    last_ctx = float(target_ndvi(target).isel(time=49, lat=1, lon=1))
    assert np.allclose(pred["ndvi_pred"].values[:, 1, 1], last_ctx, atol=1e-4)
