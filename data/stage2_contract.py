"""Explicit batch contract for ObsWorld Stage 2.

The contract keeps the meanings of D/G/h separate from tensor plumbing.  It
is intentionally independent of a dataset implementation so synthetic tests,
EarthNet loaders, and future datasets can validate the same interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

import torch


@dataclass(frozen=True)
class Stage2FieldSpec:
    """Semantic metadata for one Stage 2 batch field."""

    name: str
    role: str
    known_at_inference: bool
    shape: str
    unit: str


STAGE2_FIELD_SPECS: Tuple[Stage2FieldSpec, ...] = (
    Stage2FieldSpec("x_context", "observed optical context", True, "[B,Tc,C,H,W]", "reflectance"),
    Stage2FieldSpec("context_mask", "context valid-pixel mask", True, "[B,Tc,H,W]", "binary"),
    Stage2FieldSpec("D", "future driver trajectory", True, "[B,Tt,D]", "normalized feature units"),
    Stage2FieldSpec("D_mask", "future driver validity mask", True, "[B,Tt,D]", "binary"),
    Stage2FieldSpec("G", "geographic raster prior", True, "[B,Cg,H,W]", "dataset-scaled elevation/geo"),
    Stage2FieldSpec("G_mask", "geographic validity mask", True, "[B,Cg,H,W]", "binary"),
    Stage2FieldSpec("h", "prediction horizon", True, "[B,Tt]", "days"),
    Stage2FieldSpec("x_target", "future optical target", False, "[B,Tt,C,H,W]", "reflectance"),
    Stage2FieldSpec("target_mask", "future target valid-pixel mask", False, "[B,Tt,H,W]", "binary"),
    # These fields are intentionally documented before they become required:
    # the current EarthNet loader folds calendar/weather-window information
    # into D, while Stage 1.5/rollout work will expose them explicitly.
    Stage2FieldSpec("calendar", "explicit calendar features", True, "[B,Tt,K]", "sin/cos or categorical"),
    Stage2FieldSpec("delta_t", "step duration", True, "[B,Tt]", "days"),
    Stage2FieldSpec("obs_age", "age of each context observation", True, "[B,Tc]", "days"),
    Stage2FieldSpec("weather_path", "future weather/scenario path", True, "[B,Tt,K]", "driver units"),
)

REQUIRED_STAGE2_FIELDS = (
    "x_context",
    "context_mask",
    "D",
    "D_mask",
    "G",
    "G_mask",
    "h",
)


def _require_tensor(batch: Mapping[str, torch.Tensor], name: str) -> torch.Tensor:
    if name not in batch:
        raise KeyError(f"Stage2 batch is missing required field: {name}")
    value = batch[name]
    if not isinstance(value, torch.Tensor):
        raise TypeError(f"Stage2 field {name!r} must be a torch.Tensor, got {type(value).__name__}")
    return value


def validate_stage2_batch(
    batch: Mapping[str, torch.Tensor],
    *,
    require_targets: bool = True,
) -> None:
    """Validate shape-level invariants shared by Stage 2 loaders and models.

    This function deliberately does not enforce numeric ranges: reflectance
    scaling and D normalization are dataset/config responsibilities.  It does
    enforce that temporal dimensions cannot be accidentally confused with the
    horizon vector or driver trajectory.
    """

    for name in REQUIRED_STAGE2_FIELDS:
        _require_tensor(batch, name)

    x_context = _require_tensor(batch, "x_context")
    context_mask = _require_tensor(batch, "context_mask")
    drivers = _require_tensor(batch, "D")
    driver_mask = _require_tensor(batch, "D_mask")
    geo = _require_tensor(batch, "G")
    geo_mask = _require_tensor(batch, "G_mask")
    horizon = _require_tensor(batch, "h")

    if x_context.dim() != 5:
        raise ValueError(f"x_context must have shape [B,T,C,H,W], got {tuple(x_context.shape)}")
    b, context_steps, _, height, width = x_context.shape
    if context_mask.shape != (b, context_steps, height, width):
        raise ValueError(
            "context_mask must match x_context as [B,T,H,W], "
            f"got {tuple(context_mask.shape)} for {tuple(x_context.shape)}"
        )

    if drivers.dim() != 3:
        raise ValueError(f"D must have shape [B,T,D], got {tuple(drivers.shape)}")
    if driver_mask.shape != drivers.shape:
        raise ValueError(f"D_mask must match D, got {tuple(driver_mask.shape)} vs {tuple(drivers.shape)}")
    target_steps = drivers.shape[1]
    if horizon.shape != (b, target_steps):
        raise ValueError(
            f"h must have shape [B,T] matching D, got {tuple(horizon.shape)} vs {(b, target_steps)}"
        )

    if geo.dim() != 4:
        raise ValueError(f"G must have shape [B,C,H,W], got {tuple(geo.shape)}")
    if geo.shape[0] != b or geo_mask.shape != geo.shape:
        raise ValueError(f"G_mask must match G, got {tuple(geo_mask.shape)} vs {tuple(geo.shape)}")
    if geo.shape[-2:] != (height, width):
        raise ValueError(
            f"G spatial size must match x_context, got {tuple(geo.shape[-2:])} vs {(height, width)}"
        )

    if require_targets:
        x_target = _require_tensor(batch, "x_target")
        target_mask = _require_tensor(batch, "target_mask")
        if x_target.dim() != 5 or x_target.shape[:2] != (b, target_steps) or x_target.shape[-2:] != (height, width):
            raise ValueError(
                "x_target must have shape [B,T,C,H,W] matching D and x_context spatially, "
                f"got {tuple(x_target.shape)}"
            )
        if target_mask.shape != (b, target_steps, height, width):
            raise ValueError(
                f"target_mask must have shape {(b, target_steps, height, width)}, got {tuple(target_mask.shape)}"
            )


def stage2_field_table() -> Tuple[dict, ...]:
    """Return serializable field metadata for logging and preflight reports."""

    return tuple(spec.__dict__.copy() for spec in STAGE2_FIELD_SPECS)
