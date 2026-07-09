from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest


torch = pytest.importorskip("torch")
xr = pytest.importorskip("xarray")

from data.datasets.earthnet2021 import EarthNet2021Config, EarthNet2021Dataset


def test_earthnet2021x_netcdf_contract_and_driver_windows(tmp_path):
    split_dir = tmp_path / "earthnet2021x" / "train" / "34TDP"
    split_dir.mkdir(parents=True)
    path = split_dir / (
        "34TDP_2018-04-28_2018-09-24_"
        "3769_3897_4921_5049_58_138_76_156.nc"
    )
    time = np.arange(
        np.datetime64("2018-04-28"),
        np.datetime64("2018-04-28") + np.timedelta64(150, "D"),
    )
    shape = (150, 8, 8)
    cube = xr.Dataset(
        {
            "s2_B02": (("time", "lat", "lon"), np.full(shape, 0.1, np.float32)),
            "s2_B03": (("time", "lat", "lon"), np.full(shape, 0.2, np.float32)),
            "s2_B04": (("time", "lat", "lon"), np.full(shape, 0.3, np.float32)),
            "s2_B8A": (("time", "lat", "lon"), np.full(shape, 0.5, np.float32)),
            "s2_mask": (("time", "lat", "lon"), np.zeros(shape, np.float32)),
            "eobs_rr": (("time",), np.ones(150, np.float32)),
            "eobs_tg": (("time",), np.full(150, 20.0, np.float32)),
            "eobs_hu": (("time",), np.full(150, 50.0, np.float32)),
            "eobs_qq": (("time",), np.full(150, 100.0, np.float32)),
            "nasa_dem": (("lat", "lon"), np.full((8, 8), 500.0, np.float32)),
        },
        coords={"time": time, "lat": np.arange(8), "lon": np.arange(8)},
    )
    cube.to_netcdf(path)

    config = EarthNet2021Config(
        root=str(tmp_path),
        split="train",
        data_format="netcdf",
        file_glob="**/*.nc",
        model_img_size=8,
        use_train_holdout=False,
        strict=True,
    )
    sample = EarthNet2021Dataset(config)[0]

    assert tuple(sample["x_context"].shape) == (10, 4, 8, 8)
    assert tuple(sample["x_target"].shape) == (20, 4, 8, 8)
    assert tuple(sample["D"].shape) == (20, 9)
    assert torch.all(sample["D_mask"] == 1)
    assert torch.allclose(sample["h"], torch.arange(5, 101, 5).float())
    assert sample["start_date"] == "2018-04-28"
    assert torch.allclose(sample["G"], torch.full((1, 8, 8), 0.25))

    first_driver = sample["D"][0]
    assert first_driver[2].item() == pytest.approx(5.0)
    assert first_driver[3].item() == pytest.approx(1.0)
    assert first_driver[4].item() == pytest.approx(20.0)
    assert first_driver[5].item() == pytest.approx(1.169, rel=1e-3)
    assert first_driver[6].item() == pytest.approx(1.169, rel=1e-3)
    assert first_driver[7].item() == pytest.approx(43.2, rel=1e-5)
    assert first_driver[8].item() == pytest.approx(8.64, rel=1e-5)

    target_date = date(2018, 4, 28) + timedelta(days=54)
    expected_sin = np.sin(2.0 * np.pi * target_date.timetuple().tm_yday / 365.25)
    assert first_driver[0].item() == pytest.approx(expected_sin)
