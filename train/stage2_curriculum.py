"""Deterministic rollout curriculum helpers for formal Stage2-v2 training."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


ROLLOUT_FORECAST_MODES = frozenset({"rollout", "rollout_t5", "rollout_t5_24d", "rollout_t5_physical4"})
PARTITION_FORECAST_MODES = frozenset(
    {"obsworld_partition_24d", "obsworld_partition_physical4", "rollout_partition", "partition"}
)


def is_rollout_forecast_mode(mode: object) -> bool:
    return str(mode).strip().lower() in ROLLOUT_FORECAST_MODES | PARTITION_FORECAST_MODES


def is_partition_forecast_mode(mode: object) -> bool:
    return str(mode).strip().lower() in PARTITION_FORECAST_MODES


def rollout_length_for_step(
    schedule: Sequence[Mapping[str, Any]] | None,
    optimizer_step: int,
    *,
    target_steps: int = 20,
) -> int:
    """Return the active open-loop length from a checked schedule.

    The result is a pure function of the optimizer step and saved config, so
    resuming a checkpoint cannot accidentally restart training at a two-step
    rollout.  A missing schedule means full-length rollout, which is useful
    for already stable experiments and unit tests.
    """

    if optimizer_step < 0:
        raise ValueError(f"optimizer_step must be non-negative, got {optimizer_step}")
    if target_steps <= 0:
        raise ValueError(f"target_steps must be positive, got {target_steps}")
    if not schedule:
        return target_steps
    previous_start = -1
    previous_length = 0
    active_length: int | None = None
    for index, phase in enumerate(schedule):
        if not isinstance(phase, Mapping):
            raise TypeError(f"rollout_curriculum[{index}] must be a mapping")
        if "start_step" not in phase or "length" not in phase:
            raise KeyError(
                f"rollout_curriculum[{index}] requires start_step and length"
            )
        start = int(phase["start_step"])
        length = int(phase["length"])
        if start < 0 or start <= previous_start:
            raise ValueError(
                "rollout_curriculum start_step values must be strictly increasing "
                f"and non-negative; phase {index} has {start} after {previous_start}"
            )
        if not 1 <= length <= target_steps:
            raise ValueError(
                f"rollout_curriculum[{index}].length must lie in [1,{target_steps}], "
                f"got {length}"
            )
        if length < previous_length:
            raise ValueError(
                "rollout_curriculum lengths must be non-decreasing so a resumed "
                "run cannot shorten its open-loop horizon"
            )
        if index == 0 and start != 0:
            raise ValueError("rollout_curriculum must start at optimizer step 0")
        if start <= optimizer_step:
            active_length = length
        previous_start = start
        previous_length = length
    if active_length is None:  # defensive; index 0/start=0 proves unreachable
        raise AssertionError("rollout curriculum has no active phase")
    return active_length


def current_rollout_length(config: Mapping[str, Any], optimizer_step: int) -> int:
    """Resolve current length for an entire config, returning 20 for Direct."""

    model = config.get("model", {})
    mode = model.get("forecast_mode", model.get("mode", "direct"))
    target_steps = int(model.get("target_steps", 20))
    if not is_rollout_forecast_mode(mode):
        return target_steps
    training = config.get("training", {})
    if not bool(training.get("open_loop", True)):
        raise ValueError(
            "A rollout-named Stage2-v2 configuration must set training.open_loop=true"
        )
    if bool(training.get("teacher_forcing_future_state", False)):
        raise ValueError(
            "Formal Stage2-v2 rollout forbids teacher_forcing_future_state; "
            "the next state must be the previous prediction."
        )
    return rollout_length_for_step(
        training.get("rollout_curriculum"),
        optimizer_step,
        target_steps=target_steps,
    )


def partition_loss_scale(config: Mapping[str, Any], optimizer_step: int) -> float:
    """Return the immutable warm-up multiplier for partition losses.

    This is deliberately a pure function of the saved configuration and
    optimizer step.  Before ``warmup_start_step`` the auxiliary branches are
    not evaluated at all; after that point their fixed weights ramp linearly
    to one.  The primary rollout loss remains active throughout.
    """

    if optimizer_step < 0:
        raise ValueError(f"optimizer_step must be non-negative, got {optimizer_step}")
    model = config.get("model", {})
    mode = model.get("forecast_mode", model.get("mode", "direct"))
    if not is_partition_forecast_mode(mode):
        return 0.0
    training = config.get("training", {})
    raw = training.get("partition")
    if not isinstance(raw, Mapping):
        raise TypeError(
            "Stage2 partition mode requires a training.partition mapping"
        )
    if not bool(raw.get("enabled", False)):
        raise ValueError(
            "Stage2 partition mode requires training.partition.enabled=true; "
            "do not silently run the main-method wrapper without its loss."
        )
    start = int(raw.get("warmup_start_step", 0))
    warmup_steps = int(raw.get("warmup_steps", 0))
    if start < 0 or warmup_steps < 0:
        raise ValueError(
            "training.partition warmup_start_step and warmup_steps must be non-negative"
        )
    if optimizer_step < start:
        return 0.0
    if warmup_steps == 0:
        return 1.0
    return min(1.0, (optimizer_step - start) / float(warmup_steps))


def partition_training_settings(config: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return validated small partition settings for the model forward."""

    model = config.get("model", {})
    mode = model.get("forecast_mode", model.get("mode", "direct"))
    if not is_partition_forecast_mode(mode):
        return None
    # Calling the pure scale at zero also validates enabled/start/warmup.
    partition_loss_scale(config, optimizer_step=0)
    raw = config.get("training", {}).get("partition", {})
    detach = raw.get("detach_partition_start", True)
    if not isinstance(detach, bool):
        raise TypeError("training.partition.detach_partition_start must be boolean")
    return {
        "detach_partition_start": detach,
        "warmup_start_step": int(raw.get("warmup_start_step", 0)),
        "warmup_steps": int(raw.get("warmup_steps", 0)),
    }


def curriculum_checkpoint_state(config: Mapping[str, Any], optimizer_step: int) -> dict[str, Any]:
    """Small explicit provenance block stored alongside each Stage2 checkpoint."""

    model = config.get("model", {})
    partition_settings = partition_training_settings(config)
    raw_partition_loss = config.get("loss", {}).get("partition", {})
    if raw_partition_loss is None:
        raw_partition_loss = {}
    if partition_settings is not None and not isinstance(raw_partition_loss, Mapping):
        raise TypeError("loss.partition must be a mapping for obsworld_partition_24d")
    return {
        "forecast_mode": str(model.get("forecast_mode", model.get("mode", "direct"))),
        "optimizer_step": int(optimizer_step),
        "rollout_length": current_rollout_length(config, optimizer_step),
        "schedule": list(config.get("training", {}).get("rollout_curriculum", [])),
        "partition_schedule": partition_settings,
        "partition_loss_scale": partition_loss_scale(config, optimizer_step),
        "partition_loss": dict(raw_partition_loss) if partition_settings is not None else None,
    }
