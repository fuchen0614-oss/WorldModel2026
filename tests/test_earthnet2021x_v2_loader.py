from __future__ import annotations

from datetime import date

import numpy as np
import pytest


torch = pytest.importorskip("torch")
xr = pytest.importorskip("xarray")

from data.datasets.earthnet2021 import (
    EarthNet2021Config,
    EarthNet2021Dataset,
    _xarray_time_slice_to_thw,
    collate_earthnet2021,
    resize_stage2_v2_context_on_device,
)
from data.earthnet_conditioning import (
    CONDITIONING_DATASET_ID,
    EOBS_AGGREGATIONS,
    EOBS_VARIABLES,
    FULL24_FEATURE_NAMES,
    ConditioningStatsV2,
)
from data.stage2_contract import validate_stage2_v2_batch


def _identity_stats() -> ConditioningStatsV2:
    return ConditioningStatsV2.from_mapping(
        {
            "schema_version": 2,
            "dataset": CONDITIONING_DATASET_ID,
            "fit_split": "train",
            "daily_variable_order": list(EOBS_VARIABLES),
            "aggregation_order": list(EOBS_AGGREGATIONS),
            "feature_names": list(FULL24_FEATURE_NAMES),
            "daily_mean": {name: 0.0 for name in EOBS_VARIABLES},
            "daily_std": {name: 1.0 for name in EOBS_VARIABLES},
            "g_variable": "cop_dem",
            "g_mean": 100.0,
            "g_std": 50.0,
            "num_files": 1,
        },
        source="synthetic-v2-stats",
    )


def _write_cube(path):
    time = np.arange(
        np.datetime64("2018-04-28"),
        np.datetime64("2018-04-28") + np.timedelta64(150, "D"),
    )
    shape = (150, 8, 8)
    fields = {
        "s2_B02": (("time", "lat", "lon"), np.full(shape, 0.1, np.float32)),
        "s2_B03": (("time", "lat", "lon"), np.full(shape, 0.2, np.float32)),
        "s2_B04": (("time", "lat", "lon"), np.full(shape, 0.3, np.float32)),
        "s2_B8A": (("time", "lat", "lon"), np.full(shape, 0.5, np.float32)),
        "s2_mask": (("time", "lat", "lon"), np.zeros(shape, np.float32)),
        "cop_dem": (("lat", "lon"), np.full((8, 8), 200.0, np.float32)),
    }
    for index, name in enumerate(EOBS_VARIABLES):
        fields[f"eobs_{name}"] = (
            ("time",),
            np.arange(150, dtype=np.float32) + 100.0 * index,
        )
    xr.Dataset(
        fields,
        coords={"time": time, "lat": np.arange(8), "lon": np.arange(8)},
    ).to_netcdf(path)


def test_earthnet2021x_v2_loader_emits_frozen_path_contract(tmp_path):
    split_dir = tmp_path / "earthnet2021x" / "train" / "34TDP"
    split_dir.mkdir(parents=True)
    path = split_dir / "34TDP_2018-04-28_2018-09-24_000.nc"
    _write_cube(path)

    config = EarthNet2021Config(
        root=str(tmp_path),
        split="train",
        data_format="netcdf",
        stage2_protocol="earthnet2021x_path_v2",
        file_glob="**/*.nc",
        model_img_size=16,
        context_img_size=16,
        eval_img_size=8,
        target_img_size=8,
        geo_img_size=8,
        conditioning_stats=_identity_stats(),
        use_train_holdout=False,
        strict=True,
    )
    dataset = EarthNet2021Dataset(config)
    sample = dataset[0]
    batch = collate_earthnet2021([sample])
    validate_stage2_v2_batch(batch)

    assert tuple(sample["x_context"].shape) == (10, 4, 16, 16)
    assert tuple(sample["x_target"].shape) == (20, 4, 8, 8)
    assert tuple(sample["G"].shape) == (1, 8, 8)
    assert tuple(sample["D_path"].shape) == (30, 24)
    assert tuple(sample["C_path"].shape) == (30, 2)
    assert tuple(sample["delta_t_path"].shape) == (30,)
    assert tuple(sample["D_valid_day_count"].shape) == (30, 8)
    assert torch.all(sample["D_mask"] == 1)
    assert torch.all(sample["D_valid_day_count"] == 5)
    assert sample["D_path"][0, 0].item() == pytest.approx(2.0)
    assert sample["D_path"][0, 8].item() == pytest.approx(0.0)
    assert sample["D_path"][0, 16].item() == pytest.approx(4.0)
    # D_path[10] is the first future interval: daily positions 50..54.
    assert sample["D_path"][10, 0].item() == pytest.approx(52.0)
    assert torch.equal(sample["h"], torch.arange(5, 101, 5).float())
    assert torch.allclose(sample["G"], torch.full((1, 8, 8), 2.0))
    assert sample["start_date"] == "2018-04-28"
    assert sample["meta"]["conditioning_stats_source"] == "synthetic-v2-stats"

    expected_day = date(2018, 4, 30).timetuple().tm_yday
    assert sample["C_path"][0, 0].item() == pytest.approx(
        np.sin(2.0 * np.pi * expected_day / 365.25)
    )


def test_v2_requires_cop_dem_even_if_a_legacy_dem_is_available(tmp_path):
    split_dir = tmp_path / "earthnet2021x" / "train" / "34TDP"
    split_dir.mkdir(parents=True)
    path = split_dir / "34TDP_2018-04-28_2018-09-24_000.nc"
    _write_cube(path)
    with xr.open_dataset(path) as cube:
        modified = cube.drop_vars("cop_dem").load()
    modified["nasa_dem"] = (("lat", "lon"), np.ones((8, 8), np.float32))
    modified.to_netcdf(path, mode="w")

    config = EarthNet2021Config(
        root=str(tmp_path),
        split="train",
        data_format="netcdf",
        stage2_protocol="earthnet2021x_path_v2",
        file_glob="**/*.nc",
        conditioning_stats=_identity_stats(),
        use_train_holdout=False,
        strict=True,
    )
    with pytest.raises(KeyError, match="cop_dem"):
        _ = EarthNet2021Dataset(config)[0]


def test_v2_rejects_unsupported_split_instead_of_falling_back_to_dataset_root(tmp_path):
    split_dir = tmp_path / "earthnet2021x" / "train" / "34TDP"
    split_dir.mkdir(parents=True)
    _write_cube(split_dir / "34TDP_2018-04-28_2018-09-24_000.nc")

    config = EarthNet2021Config(
        root=str(tmp_path),
        split="ood-t",
        data_format="netcdf",
        stage2_protocol="earthnet2021x_path_v2",
        file_glob="**/*.nc",
        conditioning_stats=_identity_stats(),
        use_train_holdout=False,
        strict=True,
    )
    with pytest.raises(ValueError, match="does not support split"):
        EarthNet2021Dataset(config)


def test_v2_optical_reader_slices_time_before_materializing_values():
    source = xr.DataArray(
        np.arange(150 * 2 * 3, dtype=np.float32).reshape(150, 2, 3),
        dims=("time", "lat", "lon"),
    )

    selected = _xarray_time_slice_to_thw(source, "synthetic_s2", slice(4, None, 5))

    assert selected.shape == (30, 2, 3)
    assert np.array_equal(selected, source.values[4::5])


def test_v2_can_defer_context_resize_until_after_batch_transfer(tmp_path):
    split_dir = tmp_path / "earthnet2021x" / "train" / "34TDP"
    split_dir.mkdir(parents=True)
    _write_cube(split_dir / "34TDP_2018-04-28_2018-09-24_000.nc")

    config = EarthNet2021Config(
        root=str(tmp_path),
        split="train",
        data_format="netcdf",
        stage2_protocol="earthnet2021x_path_v2",
        file_glob="**/*.nc",
        model_img_size=16,
        context_img_size=16,
        eval_img_size=8,
        target_img_size=8,
        geo_img_size=8,
        defer_context_resize_to_device=True,
        conditioning_stats=_identity_stats(),
        use_train_holdout=False,
        strict=True,
    )
    raw_batch = collate_earthnet2021([EarthNet2021Dataset(config)[0]])
    assert tuple(raw_batch["x_context"].shape) == (1, 10, 4, 8, 8)
    assert tuple(raw_batch["context_mask"].shape) == (1, 10, 8, 8)

    model_batch = resize_stage2_v2_context_on_device(
        raw_batch,
        context_img_size=16,
    )
    validate_stage2_v2_batch(model_batch)
    assert tuple(model_batch["x_context"].shape) == (1, 10, 4, 16, 16)
    assert tuple(model_batch["context_mask"].shape) == (1, 10, 16, 16)
    assert tuple(model_batch["x_target"].shape) == (1, 20, 4, 8, 8)
    # The raw worker output stays native; the model-ready view is a copy.
    assert tuple(raw_batch["x_context"].shape) == (1, 10, 4, 8, 8)
