"""Deterministic rollout curriculum helpers for formal Stage2-v2 training."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


ROLLOUT_FORECAST_MODES = frozenset({"rollout", "rollout_t5", "rollout_t5_24d"})


def is_rollout_forecast_mode(mode: object) -> bool:
    return str(mode).strip().lower() in ROLLOUT_FORECAST_MODES


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


def curriculum_checkpoint_state(config: Mapping[str, Any], optimizer_step: int) -> dict[str, Any]:
    """Small explicit provenance block stored alongside each Stage2 checkpoint."""

    model = config.get("model", {})
    return {
        "forecast_mode": str(model.get("forecast_mode", model.get("mode", "direct"))),
        "optimizer_step": int(optimizer_step),
        "rollout_length": current_rollout_length(config, optimizer_step),
        "schedule": list(config.get("training", {}).get("rollout_curriculum", [])),
    }
