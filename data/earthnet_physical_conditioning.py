"""Original physical DGH conditioning for the additive Stage2 path.

This module deliberately does not modify :mod:`data.earthnet_conditioning`.
The existing full24 contract remains the default Stage2-v2 implementation.
``physical4_v1`` is an explicit, separately named candidate that keeps the
four weather variables from the original DGH design while sharing the same
five-day path, calendar, DEM, horizon, and missingness audit boundaries.

Raw columns must already be in the audited canonical units:

* ``rr``: millimetres per day;
* ``tg``: degrees Celsius;
* ``hu``: relative humidity in percent [0, 100];
* ``qq``: MJ / m^2 / day.

Unit conversion belongs in the future dataset/statistics adapter. This module
intentionally rejects implausible humidity instead of silently guessing units.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np


PHYSICAL4_PROTOCOL = "physical4_v1"
PHYSICAL4_RAW_VARIABLES: tuple[str, ...] = ("rr", "tg", "hu", "qq")
PHYSICAL4_FEATURE_NAMES: tuple[str, ...] = (
    "precip_sum_5d",
    "temp_mean_5d",
    "vpd_mean_5d",
    "srad_sum_5d",
)
PHYSICAL4_STATS_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PhysicalDGHPath:
    """Canonical, unnormalized five-day physical DGH weather path."""

    values: np.ndarray
    mask: np.ndarray
    valid_day_count: np.ndarray


@dataclass(frozen=True)
class PhysicalDGHStats:
    """Train-only statistics for the transformed physical4 features."""

    feature_mean: np.ndarray
    feature_std: np.ndarray
    vpd_clip_value: float
    source: str = "in_memory"
    manifest_sha256: Optional[str] = None
    num_files: Optional[int] = None
    is_identity_smoke_stats: bool = False

    @classmethod
    def identity(cls) -> "PhysicalDGHStats":
        """Return explicit identity values for unit/smoke tests only."""

        return cls(
            feature_mean=np.zeros(len(PHYSICAL4_FEATURE_NAMES), dtype=np.float32),
            feature_std=np.ones(len(PHYSICAL4_FEATURE_NAMES), dtype=np.float32),
            vpd_clip_value=1.0,
            source="identity_smoke_stats",
            is_identity_smoke_stats=True,
        )

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
        *,
        source: str = "in_memory",
    ) -> "PhysicalDGHStats":
        """Validate a physical4 stats payload before normalizing values."""

        if int(payload.get("schema_version", -1)) != PHYSICAL4_STATS_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported physical4 stats schema: "
                f"expected={PHYSICAL4_STATS_SCHEMA_VERSION}, "
                f"got={payload.get('schema_version')!r}"
            )
        if payload.get("dataset") != "earthnet2021x":
            raise ValueError(
                "Unexpected physical4 stats dataset: "
                f"{payload.get('dataset')!r}"
            )
        if payload.get("driver_protocol") != PHYSICAL4_PROTOCOL:
            raise ValueError(
                "physical4 stats driver_protocol must be "
                f"{PHYSICAL4_PROTOCOL!r}, got {payload.get('driver_protocol')!r}"
            )
        if payload.get("fit_split") != "train":
            raise ValueError(
                "physical4 stats must be fitted on split='train', "
                f"got {payload.get('fit_split')!r}"
            )
        _require_exact_order(
            payload.get("feature_names"), PHYSICAL4_FEATURE_NAMES, "feature_names"
        )
        transform = payload.get("feature_transform")
        expected_transform = ["log1p", "identity", "clip_vpd", "log1p"]
        if transform != expected_transform:
            raise ValueError(
                "physical4 feature_transform differs from the frozen protocol: "
                f"expected={expected_transform!r}, got={transform!r}"
            )

        mean = _ordered_vector(payload.get("feature_mean"), "feature_mean")
        std = _ordered_vector(payload.get("feature_std"), "feature_std")
        if not np.isfinite(mean).all() or not np.isfinite(std).all():
            raise ValueError("physical4 feature statistics must be finite")
        if np.any(std <= 0):
            raise ValueError("physical4 feature_std must be positive")
        try:
            clip = float(payload["vpd_clip_value"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("physical4 stats require vpd_clip_value") from exc
        if not math.isfinite(clip) or clip <= 0:
            raise ValueError("physical4 vpd_clip_value must be positive and finite")

        num_files = payload.get("num_files")
        if num_files is not None:
            num_files = int(num_files)
            if num_files <= 0:
                raise ValueError("physical4 stats num_files must be positive")
        manifest_sha256 = payload.get("manifest_sha256")
        if manifest_sha256 is not None and not isinstance(manifest_sha256, str):
            raise TypeError("physical4 manifest_sha256 must be a string")
        return cls(
            feature_mean=mean,
            feature_std=std,
            vpd_clip_value=clip,
            source=source,
            manifest_sha256=manifest_sha256,
            num_files=num_files,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "PhysicalDGHStats":
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"physical4 stats not found: {source}")
        with source.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls.from_mapping(payload, source=str(source))


def compute_vpd_kpa(
    temp_c: np.ndarray,
    relative_humidity_percent: np.ndarray,
) -> np.ndarray:
    """Compute daily VPD in kPa from Celsius temperature and RH percentage.

    Non-finite input pairs remain NaN. Finite humidity outside [0, 100] is a
    hard error: silently treating a [0, 1] fraction as a percentage would
    create a plausible-looking but scientifically wrong forcing path.
    """

    temperature = np.asarray(temp_c, dtype=np.float32)
    humidity = np.asarray(relative_humidity_percent, dtype=np.float32)
    if temperature.shape != humidity.shape:
        raise ValueError(
            "temperature and relative humidity must have the same shape: "
            f"{temperature.shape} vs {humidity.shape}"
        )
    finite_humidity = humidity[np.isfinite(humidity)]
    if np.any((finite_humidity < 0.0) | (finite_humidity > 100.0)):
        raise ValueError(
            "relative humidity must be in [0,100] percent; refusing to guess units"
        )
    output = np.full(temperature.shape, np.nan, dtype=np.float32)
    valid = np.isfinite(temperature) & np.isfinite(humidity)
    if not np.any(valid):
        return output
    t = temperature[valid].astype(np.float64)
    rh = humidity[valid].astype(np.float64)
    saturation = 0.6108 * np.exp(17.27 * t / (t + 237.3))
    output[valid] = np.maximum(saturation * (1.0 - rh / 100.0), 0.0).astype(
        np.float32
    )
    return output


def aggregate_physical_dgh_path(
    daily_raw: np.ndarray,
    *,
    num_steps: int = 30,
    days_per_step: int = 5,
    require_all_days: bool = True,
) -> PhysicalDGHPath:
    """Aggregate canonical daily ``[rr,tg,hu,qq]`` values into a path.

    The default preserves the original DGH rule: a five-day feature is valid
    only when all required daily values are finite. ``require_all_days=False``
    is available for diagnostics, but must not be used by formal training
    without an explicit protocol decision.
    """

    raw = np.asarray(daily_raw, dtype=np.float32)
    if raw.ndim != 2 or raw.shape[1] != len(PHYSICAL4_RAW_VARIABLES):
        raise ValueError(
            "daily_raw must be [days,4] in rr/tg/hu/qq order, got "
            f"{raw.shape}"
        )
    required_days = int(num_steps) * int(days_per_step)
    if raw.shape[0] < required_days:
        raise ValueError(
            f"Need at least {required_days} daily rows, found {raw.shape[0]}"
        )
    if num_steps <= 0 or days_per_step <= 0:
        raise ValueError("num_steps and days_per_step must be positive")

    values = np.zeros((num_steps, len(PHYSICAL4_FEATURE_NAMES)), dtype=np.float32)
    mask = np.zeros_like(values)
    valid_day_count = np.zeros((num_steps, len(PHYSICAL4_RAW_VARIABLES)), dtype=np.int64)
    raw = raw[:required_days]
    for step in range(num_steps):
        window = raw[step * days_per_step : (step + 1) * days_per_step]
        rr, tg, hu, qq = window.T
        vpd = compute_vpd_kpa(tg, hu)
        channels = (rr, tg, vpd, qq)
        validity = np.asarray(
            [
                np.isfinite(rr).sum(),
                np.isfinite(tg).sum(),
                np.isfinite(vpd).sum(),
                np.isfinite(qq).sum(),
            ]
        )
        valid_day_count[step] = np.isfinite(window).sum(axis=0).astype(np.int64)
        for feature_index, channel in enumerate(channels):
            finite = np.isfinite(channel)
            valid = bool(validity[feature_index] == days_per_step) if require_all_days else bool(validity[feature_index] > 0)
            if not valid:
                continue
            if feature_index in (0, 3):
                if np.any(channel[finite] < 0.0):
                    raise ValueError(
                        f"{PHYSICAL4_FEATURE_NAMES[feature_index]} contains negative values"
                    )
                values[step, feature_index] = float(np.sum(channel[finite]))
            else:
                values[step, feature_index] = float(np.mean(channel[finite]))
            mask[step, feature_index] = 1.0
    return PhysicalDGHPath(values=values, mask=mask, valid_day_count=valid_day_count)


def transform_physical_dgh_path(
    path: PhysicalDGHPath,
    stats: PhysicalDGHStats,
) -> PhysicalDGHPath:
    """Apply the frozen feature transforms and train-only normalization."""

    values = np.asarray(path.values, dtype=np.float32).copy()
    mask = np.asarray(path.mask, dtype=np.float32).copy()
    if values.shape[-1] != len(PHYSICAL4_FEATURE_NAMES):
        raise ValueError(f"expected physical4 values, got {values.shape}")
    values[..., 0] = np.log1p(np.maximum(values[..., 0], 0.0))
    values[..., 3] = np.log1p(np.maximum(values[..., 3], 0.0))
    values[..., 2] = np.minimum(values[..., 2], float(stats.vpd_clip_value))
    values = (values - stats.feature_mean) / stats.feature_std
    values[mask <= 0] = 0.0
    values[~np.isfinite(values)] = 0.0
    return PhysicalDGHPath(
        values=values.astype(np.float32),
        mask=mask,
        valid_day_count=np.asarray(path.valid_day_count, dtype=np.int64),
    )


def physical4_schema_dict() -> dict[str, Any]:
    """Return the immutable protocol fields for provenance and stats files."""

    return {
        "schema_version": PHYSICAL4_STATS_SCHEMA_VERSION,
        "dataset": "earthnet2021x",
        "driver_protocol": PHYSICAL4_PROTOCOL,
        "raw_variable_order": list(PHYSICAL4_RAW_VARIABLES),
        "feature_names": list(PHYSICAL4_FEATURE_NAMES),
        "feature_transform": ["log1p", "identity", "clip_vpd", "log1p"],
        "missingness_policy": "all_five_days_required",
        "vpd_formula_version": "tetens_17.27_237.3_kpa_rh_percent_v1",
        "g_variable": "cop_dem",
    }


def _require_exact_order(actual: Any, expected: Sequence[str], field_name: str) -> None:
    if actual is None or list(actual) != list(expected):
        raise ValueError(
            f"physical4 {field_name} differs from the frozen protocol: "
            f"expected={list(expected)!r}, got={actual!r}"
        )


def _ordered_vector(value: Any, field_name: str) -> np.ndarray:
    if isinstance(value, Mapping):
        value = [value[name] for name in PHYSICAL4_FEATURE_NAMES]
    array = np.asarray(value, dtype=np.float32)
    if array.shape != (len(PHYSICAL4_FEATURE_NAMES),):
        raise ValueError(
            f"physical4 {field_name} must have shape (4,), got {array.shape}"
        )
    return array
