from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pytest

xr = pytest.importorskip("xarray")

from eval.earthnet_table1 import (
    earthnet_target_highresdynamic,
    fit_doy_climatology,
    persistence_rgbn,
    raw_cube_from_netcdf,
)


def _write_raw_cube(path: Path) -> None:
    time = np.datetime64("2020-01-01") + np.arange(150).astype("timedelta64[D]")
    lat = np.array([0.0, 1.0])
    lon = np.array([10.0, 11.0, 12.0])
    shape = (150, 2, 3)
    base = np.arange(150, dtype=np.float32)[:, None, None] * np.ones(shape, dtype=np.float32)
    fields = {
        "s2_B02": (("time", "lat", "lon"), 1000.0 + base),
        "s2_B03": (("time", "lat", "lon"), 2000.0 + base),
        "s2_B04": (("time", "lat", "lon"), 3000.0 + base),
        "s2_B8A": (("time", "lat", "lon"), 5000.0 + base),
        "s2_mask": (("time", "lat", "lon"), np.zeros(shape, dtype=np.float32)),
    }
    # The latest context frame is sample index 49. Make one pixel cloudy so
    # Persistence must fall back to the previous sampled clear context frame 44.
    fields["s2_mask"][1][49, 0, 0] = 1.0
    # The first future frame is sample index 54, so the target adapter must
    # mark this location invalid in its fifth EarthNetScore channel.
    fields["s2_mask"][1][54, 1, 2] = 1.0
    xr.Dataset(fields, coords={"time": time, "lat": lat, "lon": lon}).to_netcdf(path)


def test_raw_adapter_and_persistence_follow_stage2_temporal_contract(tmp_path):
    source = tmp_path / "32TQR_2020-01-01_cube.nc"
    _write_raw_cube(source)

    raw = raw_cube_from_netcdf(source)
    assert raw.rgbn.shape == (30, 4, 2, 3)
    assert raw.clear.shape == (30, 2, 3)
    assert raw.dates[0] == date(2020, 1, 5)  # raw daily index 4
    assert raw.dates[10] == date(2020, 2, 24)  # raw daily index 54
    assert raw.rgbn[0, 0, 0, 0] == pytest.approx(0.1004)

    target = earthnet_target_highresdynamic(raw)
    assert target.shape == (2, 3, 5, 20)
    assert target[1, 2, 4, 0] == pytest.approx(1.0)
    assert target[0, 0, 4, 0] == pytest.approx(0.0)

    prediction = persistence_rgbn(raw)
    assert prediction.shape == (20, 4, 2, 3)
    # Pixel (0, 0) cannot use context token 9/raw index 49 and must use token
    # 8/raw index 44, while a clear pixel keeps the final context raw index 49.
    assert prediction[:, 0, 0, 0] == pytest.approx(np.full(20, 0.1044))
    assert prediction[:, 0, 1, 1] == pytest.approx(np.full(20, 0.1049))


def test_training_only_climatology_predicts_calendar_days(tmp_path):
    source = tmp_path / "32TQR_2020-01-01_cube.nc"
    _write_raw_cube(source)

    climatology = fit_doy_climatology([source])
    raw = raw_cube_from_netcdf(source)
    prediction = climatology.predict(raw.future_dates[:2], height=2, width=3)

    assert prediction.shape == (2, 4, 2, 3)
    # The one training cube has an observation on every listed future date
    # except one unrelated invalid pixel, so its day-of-year mean remains the
    # raw reflectance value after Stage2's 1/10000 normalization.
    assert prediction[0, 0, 0, 0] == pytest.approx(raw.future_rgbn[0, 0, 0, 0])
    assert prediction[1, 3, 1, 2] == pytest.approx(raw.future_rgbn[1, 3, 1, 2])
