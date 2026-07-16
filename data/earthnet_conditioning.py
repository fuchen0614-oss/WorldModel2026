"""Formal Stage2-v2 conditioning protocol for EarthNet2021x.

The project keeps the historical nine-dimensional Direct-DGH representation
for regression experiments.  This module intentionally does *not* extend that
representation.  It defines the separate, frozen v2 contract used by the
world-model path:

* eight daily E-OBS variables are standardized with train-only daily stats;
* every consecutive five days become one 24-D mean/min/max token;
* partial missingness is retained through a matching feature mask;
* calendar, step duration, and Copernicus DEM remain separate conditions.

Keeping this logic in one small module prevents a particularly easy-to-miss
failure mode: a loader, a statistics script, and a future model each silently
using a different feature order or normalization order.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import json
import math
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np


CONDITIONING_STATS_SCHEMA_VERSION = 2
CONDITIONING_DATASET_ID = "greenearthnet/earthnet2021x"
V2_PROTOCOL_NAMES: tuple[str, ...] = (
    "greenearthnet_path_v2",
    "earthnet_path_v2",
    "path_v2",
)
LEGACY_PROTOCOL_NAMES: tuple[str, ...] = (
    "legacy_direct9",
    "legacy_cumulative9",
    "legacy",
    "direct9",
)

# This is the order used by the public GreenEarthNet loader.  Feature order is
# aggregation-major below, so a weight trained for one order cannot be reused
# with a variable-major implementation even though both have 24 dimensions.
EOBS_VARIABLES: tuple[str, ...] = (
    "fg",
    "hu",
    "pp",
    "qq",
    "rr",
    "tg",
    "tn",
    "tx",
)
EOBS_AGGREGATIONS: tuple[str, ...] = ("mean", "min", "max")
EOBS_NETCDF_VARIABLES: tuple[str, ...] = tuple(
    f"eobs_{name}" for name in EOBS_VARIABLES
)

# The compact ablation deliberately keeps the four fields that were closest to
# the legacy DGH formulation.  It preserves v2 temporal alignment, daily
# normalization, and missingness semantics; only the variable subset changes.
CORE12_VARIABLES: tuple[str, ...] = ("rr", "tg", "hu", "qq")


def feature_names(
    variable_order: Sequence[str] = EOBS_VARIABLES,
    aggregation_order: Sequence[str] = EOBS_AGGREGATIONS,
) -> tuple[str, ...]:
    """Return the canonical aggregation-major conditioning feature order."""

    return tuple(
        f"{aggregation}_{variable}"
        for aggregation in aggregation_order
        for variable in variable_order
    )


def is_stage2_v2_protocol(name: str) -> bool:
    """Whether ``name`` selects the frozen formal E-OBS path contract."""

    return str(name).strip().lower() in V2_PROTOCOL_NAMES


def is_known_stage2_protocol(name: str) -> bool:
    """Return whether a protocol name is explicit rather than a typo fallback."""

    normalized = str(name).strip().lower()
    return normalized in V2_PROTOCOL_NAMES or normalized in LEGACY_PROTOCOL_NAMES


FULL24_FEATURE_NAMES: tuple[str, ...] = feature_names()
CORE12_FEATURE_INDICES: tuple[int, ...] = tuple(
    aggregation_index * len(EOBS_VARIABLES) + EOBS_VARIABLES.index(variable)
    for aggregation_index in range(len(EOBS_AGGREGATIONS))
    for variable in CORE12_VARIABLES
)
CORE12_FEATURE_NAMES: tuple[str, ...] = tuple(
    FULL24_FEATURE_NAMES[index] for index in CORE12_FEATURE_INDICES
)


@dataclass(frozen=True)
class ConditioningStatsV2:
    """Validated train-only normalization values for the v2 protocol."""

    daily_mean: np.ndarray
    daily_std: np.ndarray
    g_mean: float
    g_std: float
    source: str
    manifest_sha256: Optional[str] = None
    num_files: Optional[int] = None
    is_identity_smoke_stats: bool = False

    @classmethod
    def identity(cls) -> "ConditioningStatsV2":
        """Return explicit identity stats for synthetic/unit smoke tests only.

        Production configurations set ``require_conditioning_stats=true`` and
        therefore cannot reach this fallback.  Naming it explicitly avoids
        accidentally treating a no-stats data loader as a formal experiment.
        """

        return cls(
            daily_mean=np.zeros(len(EOBS_VARIABLES), dtype=np.float32),
            daily_std=np.ones(len(EOBS_VARIABLES), dtype=np.float32),
            g_mean=0.0,
            g_std=1.0,
            source="identity_smoke_stats",
            is_identity_smoke_stats=True,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "ConditioningStatsV2":
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"Stage2-v2 conditioning stats not found: {source}")
        with source.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls.from_mapping(payload, source=str(source))

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
        *,
        source: str = "in_memory",
    ) -> "ConditioningStatsV2":
        """Validate the on-disk schema before any sample is normalized."""

        schema_version = int(payload.get("schema_version", -1))
        if schema_version != CONDITIONING_STATS_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported conditioning stats schema: "
                f"expected={CONDITIONING_STATS_SCHEMA_VERSION}, got={schema_version}"
            )
        if payload.get("dataset") != CONDITIONING_DATASET_ID:
            raise ValueError(
                "Unexpected conditioning dataset: "
                f"expected={CONDITIONING_DATASET_ID!r}, got={payload.get('dataset')!r}"
            )
        if payload.get("fit_split") != "train":
            raise ValueError(
                "Stage2-v2 conditioning stats must be fitted only on split='train', "
                f"got {payload.get('fit_split')!r}"
            )
        _require_exact_order(
            payload.get("daily_variable_order"), EOBS_VARIABLES, "daily_variable_order"
        )
        _require_exact_order(
            payload.get("aggregation_order"), EOBS_AGGREGATIONS, "aggregation_order"
        )
        _require_exact_order(
            payload.get("feature_names"), FULL24_FEATURE_NAMES, "feature_names"
        )
        if payload.get("g_variable") != "cop_dem":
            raise ValueError(
                "conditioning stats g_variable differs from the frozen protocol: "
                f"expected='cop_dem', got={payload.get('g_variable')!r}"
            )

        daily_mean = _ordered_numeric_values(
            payload.get("daily_mean"), EOBS_VARIABLES, "daily_mean"
        )
        daily_std = _ordered_numeric_values(
            payload.get("daily_std"), EOBS_VARIABLES, "daily_std"
        )
        if not np.isfinite(daily_mean).all() or not np.isfinite(daily_std).all():
            raise ValueError(f"Stage2-v2 conditioning stats {source} contain non-finite daily values")
        if np.any(daily_std <= 0):
            raise ValueError(f"Stage2-v2 conditioning stats {source} contain non-positive daily_std")

        try:
            g_mean = float(payload["g_mean"])
            g_std = float(payload["g_std"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Stage2-v2 conditioning stats {source} must contain finite g_mean/g_std"
            ) from exc
        if not math.isfinite(g_mean) or not math.isfinite(g_std) or g_std <= 0:
            raise ValueError(
                f"Stage2-v2 conditioning stats {source} contain invalid g_mean/g_std"
            )

        manifest_sha256 = payload.get("manifest_sha256")
        if manifest_sha256 is not None and not isinstance(manifest_sha256, str):
            raise TypeError("conditioning manifest_sha256 must be a string when present")
        num_files = payload.get("num_files")
        if num_files is not None:
            try:
                num_files = int(num_files)
            except (TypeError, ValueError) as exc:
                raise TypeError("conditioning num_files must be an integer when present") from exc
            if num_files <= 0:
                raise ValueError("conditioning num_files must be positive")
        return cls(
            daily_mean=daily_mean.astype(np.float32),
            daily_std=daily_std.astype(np.float32),
            g_mean=g_mean,
            g_std=g_std,
            source=source,
            manifest_sha256=manifest_sha256,
            num_files=num_files,
        )


@dataclass(frozen=True)
class AggregatedConditioning:
    """One sample's 5-day E-OBS path and audit-only valid-day counts."""

    values: np.ndarray
    mask: np.ndarray
    valid_day_count: np.ndarray


def load_conditioning_stats_v2(
    path: Optional[str | Path],
    *,
    require: bool = False,
) -> ConditioningStatsV2:
    """Load formal stats, or an explicitly labeled identity smoke fallback."""

    if path:
        return ConditioningStatsV2.from_file(path)
    if require:
        raise ValueError(
            "Formal Stage2-v2 requires data.conditioning_stats_path; identity "
            "statistics are permitted only for synthetic/smoke validation."
        )
    return ConditioningStatsV2.identity()


def aggregate_eobs_path(
    daily_raw: np.ndarray,
    stats: ConditioningStatsV2,
    *,
    num_steps: int = 30,
    days_per_step: int = 5,
) -> AggregatedConditioning:
    """Normalize daily E-OBS, then aggregate consecutive windows.

    ``daily_raw`` must have columns ordered as :data:`EOBS_VARIABLES`.  The
    operation intentionally uses skip-NaN aggregation: a feature is valid if
    at least one day for its variable exists in that five-day segment.  A
    fully missing segment becomes value zero plus mask zero, never NaN.
    """

    daily = np.asarray(daily_raw, dtype=np.float32)
    if daily.ndim != 2 or daily.shape[1] != len(EOBS_VARIABLES):
        raise ValueError(
            "daily_raw must be [days,8] in EOBS_VARIABLES order, got "
            f"{daily.shape}"
        )
    required_days = num_steps * days_per_step
    if daily.shape[0] < required_days:
        raise ValueError(
            f"Need at least {required_days} daily E-OBS values for {num_steps} "
            f"segments, found {daily.shape[0]}"
        )

    daily = daily[:required_days]
    standardized = np.full_like(daily, np.nan, dtype=np.float32)
    finite = np.isfinite(daily)
    standardized[finite] = (
        (daily[finite] - np.broadcast_to(stats.daily_mean, daily.shape)[finite])
        / np.broadcast_to(stats.daily_std, daily.shape)[finite]
    )

    values = np.zeros((num_steps, len(FULL24_FEATURE_NAMES)), dtype=np.float32)
    mask = np.zeros_like(values)
    valid_day_count = np.zeros((num_steps, len(EOBS_VARIABLES)), dtype=np.int64)
    variable_count = len(EOBS_VARIABLES)
    for step in range(num_steps):
        window = standardized[step * days_per_step : (step + 1) * days_per_step]
        valid = np.isfinite(window)
        counts = valid.sum(axis=0)
        valid_day_count[step] = counts
        for variable_index, count in enumerate(counts.tolist()):
            if count == 0:
                continue
            observed = window[valid[:, variable_index], variable_index]
            values[step, variable_index] = float(np.mean(observed))
            values[step, variable_count + variable_index] = float(np.min(observed))
            values[step, 2 * variable_count + variable_index] = float(np.max(observed))
            mask[step, variable_index] = 1.0
            mask[step, variable_count + variable_index] = 1.0
            mask[step, 2 * variable_count + variable_index] = 1.0
    return AggregatedConditioning(
        values=values,
        mask=mask,
        valid_day_count=valid_day_count,
    )


def select_core12(path_values: np.ndarray) -> np.ndarray:
    """Select the fixed 12-D compact ablation from a full 24-D path."""

    values = np.asarray(path_values)
    if values.shape[-1] != len(FULL24_FEATURE_NAMES):
        raise ValueError(
            f"D_core12 expects final dim {len(FULL24_FEATURE_NAMES)}, got {values.shape}"
        )
    return values[..., list(CORE12_FEATURE_INDICES)]


def build_calendar_path(
    start_date: Optional[date],
    *,
    num_steps: int = 30,
    days_per_step: int = 5,
) -> np.ndarray:
    """Build midpoint sin/cos calendar features for each 5-day segment.

    A missing date returns a zero vector only for non-formal smoke use.  The
    dataset loader rejects it when ``strict`` is enabled, so a formal run never
    silently loses calendar information.
    """

    path = np.zeros((num_steps, 2), dtype=np.float32)
    if start_date is None:
        return path
    for step in range(num_steps):
        midpoint = start_date + timedelta(days=days_per_step * step + days_per_step // 2)
        angle = 2.0 * math.pi * midpoint.timetuple().tm_yday / 365.25
        path[step] = (math.sin(angle), math.cos(angle))
    return path


def build_delta_t_path(
    *,
    num_steps: int = 30,
    days_per_step: int = 5,
) -> np.ndarray:
    """Return the explicit duration associated with every path token."""

    return np.full((num_steps,), float(days_per_step), dtype=np.float32)


def normalize_cop_dem(
    raw_dem: np.ndarray,
    stats: ConditioningStatsV2,
) -> tuple[np.ndarray, np.ndarray]:
    """Normalize Copernicus DEM and retain a separate validity raster."""

    raw = np.asarray(raw_dem, dtype=np.float32)
    mask = np.isfinite(raw).astype(np.float32)
    values = np.zeros_like(raw, dtype=np.float32)
    valid = mask > 0
    values[valid] = (raw[valid] - float(stats.g_mean)) / float(stats.g_std)
    return values, mask


def conditioning_schema_dict() -> dict[str, Any]:
    """Return serializable fixed protocol metadata for reports/checkpoints."""

    return {
        "schema_version": CONDITIONING_STATS_SCHEMA_VERSION,
        "dataset": CONDITIONING_DATASET_ID,
        "daily_variable_order": list(EOBS_VARIABLES),
        "aggregation_order": list(EOBS_AGGREGATIONS),
        "feature_names": list(FULL24_FEATURE_NAMES),
        "core12_feature_names": list(CORE12_FEATURE_NAMES),
        "g_variable": "cop_dem",
    }


def _require_exact_order(
    actual: Any,
    expected: Sequence[str],
    field_name: str,
) -> None:
    if actual is None or list(actual) != list(expected):
        raise ValueError(
            f"conditioning stats {field_name} differs from the frozen protocol: "
            f"expected={list(expected)}, got={actual!r}"
        )


def _ordered_numeric_values(
    value: Any,
    order: Sequence[str],
    field_name: str,
) -> np.ndarray:
    if isinstance(value, Mapping):
        missing = [name for name in order if name not in value]
        extras = sorted(set(value) - set(order))
        if missing or extras:
            raise ValueError(
                f"conditioning stats {field_name} keys mismatch: "
                f"missing={missing}, extras={extras}"
            )
        values = [value[name] for name in order]
    else:
        values = value
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (len(order),):
        raise ValueError(
            f"conditioning stats {field_name} must contain {len(order)} values in "
            f"EOBS order, got shape={array.shape}"
        )
    return array
