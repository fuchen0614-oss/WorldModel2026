from datetime import date

import numpy as np

from scripts.build_earthnet_era5_sidecars import (
    _daily_accumulation,
    _precipitation_to_mm,
    _radiation_to_mj,
    _temperature_to_celsius,
    vapor_pressure_deficit_kpa,
)


def test_vpd_and_era5_unit_conversions():
    temperature = _temperature_to_celsius(
        np.asarray([293.15, 283.15]),
        "K",
    )
    dewpoint = _temperature_to_celsius(
        np.asarray([283.15, 283.15]),
        "kelvin",
    )
    vpd = vapor_pressure_deficit_kpa(temperature, dewpoint)
    assert vpd[0] > 1.0
    assert abs(float(vpd[1])) < 1e-6
    np.testing.assert_allclose(
        _precipitation_to_mm(np.asarray([0.001]), "m"),
        [1.0],
    )
    np.testing.assert_allclose(
        _radiation_to_mj(np.asarray([1e6]), "J m**-2"),
        [1.0],
    )


def test_cumulative_and_incremental_daily_aggregation():
    start = date(2017, 1, 1)
    times = np.arange(
        np.datetime64("2017-01-01T00"),
        np.datetime64("2017-01-03T01"),
        np.timedelta64(1, "h"),
    ).astype("datetime64[ns]")

    cumulative = np.zeros(times.shape[0], dtype=np.float32)
    cumulative[24] = 3.0
    cumulative[48] = 7.0
    np.testing.assert_allclose(
        _daily_accumulation(times, cumulative, start, 2, "cumulative"),
        [3.0, 7.0],
    )

    incremental = np.ones(times.shape[0], dtype=np.float32)
    incremental[0] = 999.0  # Previous day's 00 UTC accumulation is ignored.
    np.testing.assert_allclose(
        _daily_accumulation(times, incremental, start, 2, "incremental"),
        [24.0, 24.0],
    )
