from __future__ import annotations

import numpy as np
import pytest

from data.earthnet_physical_conditioning import (
    PHYSICAL4_FEATURE_NAMES,
    PhysicalDGHStats,
    aggregate_physical_dgh_path,
    compute_vpd_kpa,
    physical4_schema_dict,
    transform_physical_dgh_path,
)


def test_vpd_uses_celsius_and_rh_percent_and_is_zero_at_saturation():
    vpd = compute_vpd_kpa(np.asarray([20.0, 20.0]), np.asarray([100.0, 50.0]))
    assert vpd[0] == pytest.approx(0.0, abs=1e-7)
    assert vpd[1] == pytest.approx(1.169, rel=2e-3)


def test_vpd_rejects_out_of_range_humidity_instead_of_guessing():
    with pytest.raises(ValueError, match="refusing to guess units"):
        compute_vpd_kpa(np.asarray([20.0]), np.asarray([101.0]))


def test_physical_path_aggregates_original_four_weather_fields():
    daily = np.asarray(
        [
            [1.0, 10.0, 50.0, 2.0],
            [2.0, 11.0, 60.0, 3.0],
            [3.0, 12.0, 70.0, 4.0],
            [4.0, 13.0, 80.0, 5.0],
            [5.0, 14.0, 90.0, 6.0],
        ],
        dtype=np.float32,
    )
    path = aggregate_physical_dgh_path(daily, num_steps=1, days_per_step=5)
    assert tuple(path.values.shape) == (1, 4)
    assert path.values[0, 0] == pytest.approx(15.0)
    assert path.values[0, 1] == pytest.approx(12.0)
    assert path.values[0, 3] == pytest.approx(20.0)
    assert np.all(path.mask == 1.0)
    assert np.all(path.valid_day_count == 5)


def test_original_all_five_day_policy_masks_partial_windows():
    daily = np.ones((5, 4), dtype=np.float32)
    daily[2, 0] = np.nan
    path = aggregate_physical_dgh_path(daily, num_steps=1, days_per_step=5)
    assert path.mask[0, 0] == 0.0
    assert path.values[0, 0] == 0.0
    assert np.all(path.mask[0, 1:] == 1.0)


def test_transform_masks_invalid_features_and_applies_log_clip_normalization():
    daily = np.ones((5, 4), dtype=np.float32)
    daily[:, 0] = 1.0
    daily[:, 3] = 3.0
    path = aggregate_physical_dgh_path(daily, num_steps=1, days_per_step=5)
    stats = PhysicalDGHStats(
        feature_mean=np.zeros(4, dtype=np.float32),
        feature_std=np.ones(4, dtype=np.float32),
        vpd_clip_value=0.01,
    )
    transformed = transform_physical_dgh_path(path, stats)
    assert transformed.values[0, 0] == pytest.approx(np.log1p(5.0))
    assert transformed.values[0, 3] == pytest.approx(np.log1p(15.0))
    assert np.isfinite(transformed.values).all()


def test_stats_schema_is_explicit_and_rejects_wrong_feature_order():
    payload = {
        **physical4_schema_dict(),
        "fit_split": "train",
        "feature_mean": [0.0] * 4,
        "feature_std": [1.0] * 4,
        "vpd_clip_value": 2.0,
    }
    stats = PhysicalDGHStats.from_mapping(payload)
    assert tuple(PHYSICAL4_FEATURE_NAMES) == tuple(stats_feature_names(payload))
    bad = dict(payload)
    bad["feature_names"] = list(reversed(PHYSICAL4_FEATURE_NAMES))
    with pytest.raises(ValueError, match="feature_names"):
        PhysicalDGHStats.from_mapping(bad)


def stats_feature_names(payload):
    return payload["feature_names"]
