from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from data.earthnet_conditioning import (
    CONDITIONING_DATASET_ID,
    CORE12_FEATURE_NAMES,
    CORE12_FEATURE_INDICES,
    EOBS_AGGREGATIONS,
    EOBS_VARIABLES,
    FULL24_FEATURE_NAMES,
    ConditioningStatsV2,
    aggregate_eobs_path,
    build_calendar_path,
    select_core12,
)
from data.datasets.earthnet2021 import EarthNet2021Config


def _stats() -> ConditioningStatsV2:
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
            "g_mean": 10.0,
            "g_std": 2.0,
            "num_files": 1,
        },
        source="unit-test",
    )


def test_24d_aggregation_is_aggregation_major_and_preserves_partial_missingness():
    daily = np.stack(
        [np.arange(150, dtype=np.float32) + 100.0 * index for index in range(8)],
        axis=1,
    )
    # fg has four valid values in the first window; hu is entirely absent.
    daily[1, 0] = np.nan
    daily[:5, 1] = np.nan

    result = aggregate_eobs_path(daily, _stats())

    assert result.values.shape == (30, 24)
    assert result.mask.shape == (30, 24)
    assert result.valid_day_count.shape == (30, 8)
    assert FULL24_FEATURE_NAMES[:10] == (
        "mean_fg", "mean_hu", "mean_pp", "mean_qq", "mean_rr",
        "mean_tg", "mean_tn", "mean_tx", "min_fg", "min_hu",
    )
    assert result.valid_day_count[0, 0] == 4
    assert result.values[0, 0] == pytest.approx(2.25)
    assert result.values[0, 8] == pytest.approx(0.0)
    assert result.values[0, 16] == pytest.approx(4.0)
    assert np.all(result.values[0, [1, 9, 17]] == 0.0)
    assert np.all(result.mask[0, [1, 9, 17]] == 0.0)
    # Window 10 is the first future transition, covering daily indices 50..54.
    assert result.values[10, 0] == pytest.approx(52.0)
    assert np.all(result.mask[10] == 1.0)


def test_core12_is_a_fixed_subset_of_the_full_path():
    path = np.arange(30 * 24, dtype=np.float32).reshape(30, 24)
    core = select_core12(path)
    assert core.shape == (30, 12)
    assert np.array_equal(core, path[:, list(CORE12_FEATURE_INDICES)])
    assert CORE12_FEATURE_NAMES == (
        "mean_rr", "mean_tg", "mean_hu", "mean_qq",
        "min_rr", "min_tg", "min_hu", "min_qq",
        "max_rr", "max_tg", "max_hu", "max_qq",
    )


def test_calendar_uses_each_five_day_midpoint():
    calendar = build_calendar_path(date(2020, 1, 1))
    expected_day = date(2020, 1, 3).timetuple().tm_yday
    expected = np.sin(2.0 * np.pi * expected_day / 365.25)
    assert calendar.shape == (30, 2)
    assert calendar[0, 0] == pytest.approx(expected)
    assert not np.allclose(calendar[0], calendar[1])


def test_stats_reject_variable_order_that_would_make_24d_weights_incompatible():
    payload = {
        "schema_version": 2,
        "dataset": CONDITIONING_DATASET_ID,
        "fit_split": "train",
        "daily_variable_order": list(reversed(EOBS_VARIABLES)),
        "aggregation_order": list(EOBS_AGGREGATIONS),
        "feature_names": list(FULL24_FEATURE_NAMES),
        "daily_mean": {name: 0.0 for name in EOBS_VARIABLES},
        "daily_std": {name: 1.0 for name in EOBS_VARIABLES},
        "g_variable": "cop_dem",
        "g_mean": 0.0,
        "g_std": 1.0,
    }
    with pytest.raises(ValueError, match="daily_variable_order"):
        ConditioningStatsV2.from_mapping(payload)


def test_v2_config_refuses_to_mislabel_legacy_dgh_stats_as_v2_stats():
    with pytest.raises(ValueError, match="legacy dgh_stats_path"):
        EarthNet2021Config.from_config(
            {
                "root": "/unused",
                "stage2_protocol": "earthnet2021x_path_v2",
                "dgh_stats_path": "/old/9d.json",
                "strict": False,
            }
        )
