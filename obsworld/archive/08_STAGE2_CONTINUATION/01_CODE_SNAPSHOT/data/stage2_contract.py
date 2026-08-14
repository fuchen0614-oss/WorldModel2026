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
    Stage2FieldSpec(
        "official_eval_mask",
        "official future evaluation clear-pixel mask",
        False,
        "[B,Tt,H,W]",
        "binary; evaluation only",
    ),
    Stage2FieldSpec(
        "official_eval_eligibility",
        "official high-quality pixel eligibility",
        False,
        "[B,H,W]",
        "binary; evaluation only",
    ),
    # These fields are intentionally documented before they become required:
    # the current EarthNet loader folds calendar/weather-window information
    # into D, while Stage 1.5/rollout work will expose them explicitly.
    Stage2FieldSpec("calendar", "explicit calendar features", True, "[B,Tt,K]", "sin/cos or categorical"),
    Stage2FieldSpec("delta_t", "step duration", True, "[B,Tt]", "days"),
    Stage2FieldSpec("obs_age", "age of each context observation", True, "[B,Tc]", "days"),
    Stage2FieldSpec("weather_path", "future weather/scenario path", True, "[B,Tt,K]", "driver units"),
    # Frozen Stage2-v2 path protocol.  D_path covers the full 150-day cube;
    # D_path[:, 10] is the first interval that evolves the final context state
    # into the first future state.  It deliberately coexists with legacy D.
    Stage2FieldSpec("D_path", "full24 or physical4 five-day driver path", True, "[B,30,D], D∈{24,4}", "protocol-specific train-normalized aggregate"),
    Stage2FieldSpec("C_path", "5-day midpoint calendar path", True, "[B,30,2]", "sin/cos day-of-year"),
    Stage2FieldSpec("delta_t_path", "duration of each conditioning interval", True, "[B,30]", "days"),
    Stage2FieldSpec("D_valid_day_count", "audit-only raw weather valid-day count", False, "[B,30,8] or [B,30,4]", "days; not a model input"),
    # Observation-correction inputs are deliberately separate from the normal
    # model view.  During training/evaluation they are generated from an
    # explicit reveal schedule; unrevealed future targets must never enter the
    # Direct/Rollout state machine.
    Stage2FieldSpec("observations", "revealed future optical observation", False, "[B,T,C,H,W]", "reflectance; correction-only"),
    Stage2FieldSpec("observation_mask", "revealed clear-pixel support", False, "[B,T,H,W]", "binary; correction-only"),
    Stage2FieldSpec("reveal_mask", "future acquisition reveal schedule", False, "[B,T]", "binary; correction-only"),
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

MODEL_INPUT_FIELDS = REQUIRED_STAGE2_FIELDS
OPTIONAL_MODEL_INPUT_FIELDS = (
    "context_phi",
    "calendar",
    "delta_t",
    "obs_age",
    "weather_path",
)
TRAINING_SUPERVISION_FIELDS = ("x_target", "target_mask")
EVALUATION_ONLY_FIELDS = ("official_eval_mask", "official_eval_eligibility")
OBSERVATION_CORRECTION_FIELDS = ("observations", "observation_mask", "reveal_mask")


STAGE2_V2_REQUIRED_FIELDS = (
    "x_context",
    "context_mask",
    "D_path",
    "D_mask",
    "C_path",
    "delta_t_path",
    "G",
    "G_mask",
    "h",
)
STAGE2_V2_MODEL_INPUT_FIELDS = STAGE2_V2_REQUIRED_FIELDS
STAGE2_V2_AUDIT_ONLY_FIELDS = ("D_valid_day_count",)
STAGE2_V2_DRIVER_DIMS = (24, 4)


def is_stage2_v2_batch(batch: Mapping[str, torch.Tensor]) -> bool:
    """Whether a batch selects the formal path-based contract."""

    return "D_path" in batch


def model_input_view(
    batch: Mapping[str, torch.Tensor],
    *,
    include_training_targets: bool = False,
) -> dict[str, torch.Tensor]:
    """Return the only fields permitted to cross the model boundary.

    The default view contains inference-time information only.  A legacy
    latent-target ablation may explicitly request training targets, but
    evaluation-only masks are never forwarded under either mode.
    """

    if is_stage2_v2_batch(batch):
        return stage2_v2_model_input_view(
            batch,
            include_training_targets=include_training_targets,
        )

    missing = [name for name in MODEL_INPUT_FIELDS if name not in batch]
    if missing:
        raise KeyError(f"Stage2 model inputs are missing fields: {missing}")
    names = [*MODEL_INPUT_FIELDS]
    names.extend(name for name in OPTIONAL_MODEL_INPUT_FIELDS if name in batch)
    if include_training_targets:
        missing_targets = [
            name for name in TRAINING_SUPERVISION_FIELDS if name not in batch
        ]
        if missing_targets:
            raise KeyError(
                f"Latent-target ablation is missing fields: {missing_targets}"
            )
        names.extend(TRAINING_SUPERVISION_FIELDS)
    return {name: batch[name] for name in names}


def stage2_v2_model_input_view(
    batch: Mapping[str, torch.Tensor],
    *,
    include_training_targets: bool = False,
) -> dict[str, torch.Tensor]:
    """Return only legal v2 model inputs, excluding targets and audit fields."""

    missing = [name for name in STAGE2_V2_MODEL_INPUT_FIELDS if name not in batch]
    if missing:
        raise KeyError(f"Stage2-v2 model inputs are missing fields: {missing}")
    names = [*STAGE2_V2_MODEL_INPUT_FIELDS]
    if include_training_targets:
        missing_targets = [
            name for name in TRAINING_SUPERVISION_FIELDS if name not in batch
        ]
        if missing_targets:
            raise KeyError(
                f"Stage2-v2 latent-target ablation is missing fields: {missing_targets}"
            )
        names.extend(TRAINING_SUPERVISION_FIELDS)
    return {name: batch[name] for name in names}


def training_supervision_view(
    batch: Mapping[str, torch.Tensor],
) -> dict[str, torch.Tensor]:
    missing = [name for name in TRAINING_SUPERVISION_FIELDS if name not in batch]
    if missing:
        raise KeyError(f"Stage2 training supervision is missing fields: {missing}")
    return {name: batch[name] for name in TRAINING_SUPERVISION_FIELDS}


def observation_correction_view(
    batch: Mapping[str, torch.Tensor],
) -> dict[str, torch.Tensor]:
    """Return only explicitly revealed observations for the U update.

    This helper is intentionally opt-in.  ``model_input_view`` never includes
    these fields, which keeps the no-update Direct/Rollout paths causally
    identical even when a loader batch carries future supervision tensors.
    """

    missing = [name for name in OBSERVATION_CORRECTION_FIELDS if name not in batch]
    if missing:
        raise KeyError(f"Observation-correction inputs are missing fields: {missing}")
    observations = batch["observations"]
    observation_mask = batch["observation_mask"]
    reveal_mask = batch["reveal_mask"]
    if not isinstance(observations, torch.Tensor) or observations.dim() != 5:
        raise ValueError("observations must be a tensor with shape [B,T,C,H,W]")
    if not isinstance(observation_mask, torch.Tensor) or observation_mask.shape != (
        observations.shape[0], observations.shape[1], observations.shape[-2], observations.shape[-1]
    ):
        raise ValueError("observation_mask must match observations as [B,T,H,W]")
    if not isinstance(reveal_mask, torch.Tensor) or reveal_mask.shape not in {
        (observations.shape[0], observations.shape[1]),
        (observations.shape[0], observations.shape[1], 1),
    }:
        raise ValueError("reveal_mask must be [B,T] or [B,T,1]")
    if not torch.isfinite(reveal_mask).all() or (reveal_mask < 0).any() or (reveal_mask > 1).any():
        raise ValueError("reveal_mask must lie in [0,1]")
    return {
        "observations": observations,
        "observation_mask": observation_mask,
        "reveal_mask": reveal_mask.reshape(observations.shape[0], observations.shape[1]),
    }


def evaluation_only_view(
    batch: Mapping[str, torch.Tensor],
) -> dict[str, torch.Tensor]:
    return {name: batch[name] for name in EVALUATION_ONLY_FIELDS if name in batch}


def assert_model_batch_has_no_evaluation_fields(
    batch: Mapping[str, torch.Tensor],
) -> None:
    leaked = sorted(set(batch) & set(EVALUATION_ONLY_FIELDS))
    if leaked:
        raise ValueError(
            "Evaluation-only fields reached the Stage2 model: "
            f"{leaked}. Build the input with model_input_view()."
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
    require_evaluation: bool = False,
) -> None:
    """Validate shape-level invariants shared by Stage 2 loaders and models.

    This function deliberately does not enforce numeric ranges: reflectance
    scaling and D normalization are dataset/config responsibilities.  It does
    enforce that temporal dimensions cannot be accidentally confused with the
    horizon vector or driver trajectory.
    """

    if is_stage2_v2_batch(batch):
        validate_stage2_v2_batch(
            batch,
            require_targets=require_targets,
            require_evaluation=require_evaluation,
        )
        return

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

    if require_evaluation:
        official_mask = _require_tensor(batch, "official_eval_mask")
        eligibility = _require_tensor(batch, "official_eval_eligibility")
        if official_mask.shape != (b, target_steps, height, width):
            raise ValueError(
                "official_eval_mask must match future targets as [B,T,H,W], "
                f"got {tuple(official_mask.shape)}"
            )
        if eligibility.shape != (b, height, width):
            raise ValueError(
                "official_eval_eligibility must have shape [B,H,W], "
                f"got {tuple(eligibility.shape)}"
            )


def validate_stage2_v2_batch(
    batch: Mapping[str, torch.Tensor],
    *,
    require_targets: bool = True,
    require_evaluation: bool = False,
    expected_driver_dim: Optional[int] = None,
) -> None:
    """Validate the frozen 30-token Stage2-v2 data contract.

    Unlike legacy Stage2, context, target, and geographic tensors are allowed
    to have different spatial sizes.  That distinction is necessary for a
    256x256 Stage1.5 context encoder and native 128x128 EarthNet targets/DEM.
    """

    for name in STAGE2_V2_REQUIRED_FIELDS:
        _require_tensor(batch, name)

    x_context = _require_tensor(batch, "x_context")
    context_mask = _require_tensor(batch, "context_mask")
    drivers = _require_tensor(batch, "D_path")
    driver_mask = _require_tensor(batch, "D_mask")
    calendar = _require_tensor(batch, "C_path")
    delta_t = _require_tensor(batch, "delta_t_path")
    geo = _require_tensor(batch, "G")
    geo_mask = _require_tensor(batch, "G_mask")
    horizon = _require_tensor(batch, "h")

    if x_context.dim() != 5:
        raise ValueError(
            f"x_context must have shape [B,T,C,H,W], got {tuple(x_context.shape)}"
        )
    batch_size, context_steps, _, context_height, context_width = x_context.shape
    if context_mask.shape != (batch_size, context_steps, context_height, context_width):
        raise ValueError(
            "context_mask must match x_context as [B,T,H,W], "
            f"got {tuple(context_mask.shape)} for {tuple(x_context.shape)}"
        )
    if context_steps != 10:
        raise ValueError(f"Stage2-v2 fixes Tc=10, got Tc={context_steps}")

    if drivers.dim() != 3:
        raise ValueError(
            f"D_path must have shape [B,Td,Kd], got {tuple(drivers.shape)}"
        )
    if drivers.shape[0] != batch_size or drivers.shape[1] != 30:
        raise ValueError(
            "Stage2-v2 fixes D_path to [B,30,D] with 30 five-day tokens, got "
            f"{tuple(drivers.shape)}"
        )
    driver_dim = int(drivers.shape[2])
    if driver_dim not in STAGE2_V2_DRIVER_DIMS:
        raise ValueError(
            "Stage2-v2 supports only the frozen full24 or physical4 D layouts, got "
            f"D={driver_dim}"
        )
    if expected_driver_dim is not None and driver_dim != int(expected_driver_dim):
        raise ValueError(
            "D_path dimension does not match the configured driver encoder: "
            f"batch={driver_dim}, expected={int(expected_driver_dim)}"
        )
    if driver_mask.shape != drivers.shape:
        raise ValueError(
            f"D_mask must match D_path, got {tuple(driver_mask.shape)} vs {tuple(drivers.shape)}"
        )
    if calendar.shape != (batch_size, 30, 2):
        raise ValueError(
            f"C_path must have shape [B,30,2], got {tuple(calendar.shape)}"
        )
    if delta_t.shape != (batch_size, 30):
        raise ValueError(
            f"delta_t_path must have shape [B,30], got {tuple(delta_t.shape)}"
        )
    if not torch.isfinite(drivers).all() or not torch.isfinite(calendar).all():
        raise ValueError("Stage2-v2 D_path/C_path must be finite after loader normalization")
    if not torch.isfinite(delta_t).all() or torch.any(delta_t <= 0):
        raise ValueError("Stage2-v2 delta_t_path must be finite and strictly positive")
    if not torch.all((driver_mask == 0) | (driver_mask == 1)):
        raise ValueError("Stage2-v2 D_mask must be binary")

    if horizon.shape != (batch_size, 20):
        raise ValueError(f"Stage2-v2 h must have shape [B,20], got {tuple(horizon.shape)}")
    expected_horizon = torch.cumsum(delta_t[:, context_steps:], dim=1)
    if not torch.allclose(
        horizon.to(dtype=expected_horizon.dtype), expected_horizon, atol=1e-4, rtol=1e-5
    ):
        raise ValueError(
            "Stage2-v2 h must equal cumsum(delta_t_path[:, 10:]); this protects "
            "the first-future-token alignment."
        )

    if geo.dim() != 4 or geo.shape[0] != batch_size or geo.shape[1] != 1:
        raise ValueError(
            "Stage2-v2 G must have shape [B,1,Hg,Wg], got "
            f"{tuple(geo.shape)}"
        )
    if geo_mask.shape != geo.shape:
        raise ValueError(f"G_mask must match G, got {tuple(geo_mask.shape)} vs {tuple(geo.shape)}")
    if not torch.isfinite(geo).all():
        raise ValueError("Stage2-v2 G must be finite after DEM normalization")

    if "D_valid_day_count" in batch:
        valid_day_count = _require_tensor(batch, "D_valid_day_count")
        expected_audit_dim = 4 if driver_dim == 4 else 8
        if valid_day_count.shape != (batch_size, 30, expected_audit_dim):
            raise ValueError(
                "D_valid_day_count must have the protocol raw-variable width, got "
                f"{tuple(valid_day_count.shape)}; expected {expected_audit_dim} for D={driver_dim}"
            )
        if torch.any(valid_day_count < 0) or torch.any(valid_day_count > 5):
            raise ValueError("D_valid_day_count must lie in [0,5]")

    if require_targets:
        x_target = _require_tensor(batch, "x_target")
        target_mask = _require_tensor(batch, "target_mask")
        if x_target.dim() != 5 or x_target.shape[:2] != (batch_size, 20):
            raise ValueError(
                "x_target must have shape [B,20,C,Ht,Wt], got "
                f"{tuple(x_target.shape)}"
            )
        target_height, target_width = x_target.shape[-2:]
        if target_mask.shape != (batch_size, 20, target_height, target_width):
            raise ValueError(
                "target_mask must match x_target as [B,20,Ht,Wt], got "
                f"{tuple(target_mask.shape)}"
            )
        if geo.shape[-2:] != (target_height, target_width):
            raise ValueError(
                "Stage2-v2 G must use the target/native geometry, got "
                f"G={tuple(geo.shape[-2:])}, target={tuple(x_target.shape[-2:])}"
            )

    if require_evaluation:
        official_mask = _require_tensor(batch, "official_eval_mask")
        eligibility = _require_tensor(batch, "official_eval_eligibility")
        if not require_targets:
            raise ValueError("Stage2-v2 evaluation validation also requires target geometry")
        x_target = _require_tensor(batch, "x_target")
        target_height, target_width = x_target.shape[-2:]
        if official_mask.shape != (batch_size, 20, target_height, target_width):
            raise ValueError(
                "official_eval_mask must match v2 targets as [B,20,Ht,Wt], got "
                f"{tuple(official_mask.shape)}"
            )
        if eligibility.shape != (batch_size, target_height, target_width):
            raise ValueError(
                "official_eval_eligibility must have shape [B,Ht,Wt], got "
                f"{tuple(eligibility.shape)}"
            )


def stage2_field_table() -> Tuple[dict, ...]:
    """Return serializable field metadata for logging and preflight reports."""

    return tuple(spec.__dict__.copy() for spec in STAGE2_FIELD_SPECS)
