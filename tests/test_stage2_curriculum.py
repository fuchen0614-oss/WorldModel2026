from __future__ import annotations

import pytest

from train.stage2_curriculum import current_rollout_length, rollout_length_for_step


SCHEDULE = [
    {"start_step": 0, "length": 2},
    {"start_step": 2_000, "length": 4},
    {"start_step": 6_000, "length": 8},
    {"start_step": 12_000, "length": 12},
    {"start_step": 20_000, "length": 20},
]


@pytest.mark.parametrize(
    ("step", "expected"),
    [(0, 2), (1_999, 2), (2_000, 4), (9_999, 8), (20_000, 20)],
)
def test_rollout_curriculum_is_a_pure_function_of_optimizer_step(step, expected):
    assert rollout_length_for_step(SCHEDULE, step, target_steps=20) == expected


def test_rollout_curriculum_rejects_teacher_forcing_and_nonmonotone_schedule():
    config = {
        "model": {"forecast_mode": "rollout_t5_24d", "target_steps": 20},
        "training": {
            "teacher_forcing_future_state": True,
            "rollout_curriculum": SCHEDULE,
        },
    }
    with pytest.raises(ValueError, match="teacher_forcing"):
        current_rollout_length(config, 0)
    config["training"]["teacher_forcing_future_state"] = False
    config["training"]["open_loop"] = False
    with pytest.raises(ValueError, match="open_loop"):
        current_rollout_length(config, 0)
    with pytest.raises(ValueError, match="non-decreasing"):
        rollout_length_for_step(
            [{"start_step": 0, "length": 4}, {"start_step": 1, "length": 2}],
            1,
            target_steps=20,
        )
