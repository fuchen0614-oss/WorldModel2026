from __future__ import annotations

import pytest

from train.stage2_curriculum import (
    curriculum_checkpoint_state,
    current_rollout_length,
    partition_loss_scale,
    partition_training_settings,
    rollout_length_for_step,
)


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


def test_partition_warmup_is_pure_and_requires_an_explicit_enabled_block():
    config = {
        "model": {"forecast_mode": "obsworld_partition_24d", "target_steps": 20},
        "training": {
            "open_loop": True,
            "teacher_forcing_future_state": False,
            "rollout_curriculum": SCHEDULE,
            "partition": {
                "enabled": True,
                "detach_partition_start": True,
                "warmup_start_step": 5,
                "warmup_steps": 10,
            },
        },
    }
    assert partition_loss_scale(config, 0) == 0.0
    assert partition_loss_scale(config, 5) == 0.0
    assert partition_loss_scale(config, 10) == 0.5
    assert partition_loss_scale(config, 15) == 1.0
    assert partition_training_settings(config) == {
        "detach_partition_start": True,
        "warmup_start_step": 5,
        "warmup_steps": 10,
    }
    checkpoint = curriculum_checkpoint_state(config, 15)
    assert checkpoint["partition_loss_scale"] == 1.0
    assert checkpoint["partition_schedule"]["detach_partition_start"] is True

    config["training"]["partition"]["enabled"] = False
    with pytest.raises(ValueError, match="enabled=true"):
        partition_loss_scale(config, 5)


def test_physical4_rollout_and_partition_modes_use_same_curriculum():
    from train.stage2_curriculum import current_rollout_length, partition_loss_scale
    rollout = {
        "model": {"forecast_mode": "rollout_t5_physical4", "target_steps": 20},
        "training": {
            "open_loop": True,
            "teacher_forcing_future_state": False,
            "rollout_curriculum": [{"start_step": 0, "length": 2}, {"start_step": 5, "length": 20}],
        },
    }
    assert current_rollout_length(rollout, 0) == 2
    assert current_rollout_length(rollout, 5) == 20
    partition = {
        "model": {"forecast_mode": "obsworld_partition_physical4"},
        "training": {"partition": {"enabled": True, "warmup_start_step": 2, "warmup_steps": 2}},
    }
    assert partition_loss_scale(partition, 1) == 0.0
    assert partition_loss_scale(partition, 3) == 0.5
