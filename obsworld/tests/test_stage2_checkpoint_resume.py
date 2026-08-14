from __future__ import annotations

import random

import numpy as np
import pytest


torch = pytest.importorskip("torch")
nn = torch.nn

from train.train_stage2_earthnet import (
    capture_rng_state,
    restore_rng_state,
    save_checkpoint,
)
from train.stage2_checkpoint import (
    EpochRandomSampler,
    next_data_position,
    restore_data_position,
)


def _config() -> dict:
    return {
        "model": {"forecast_mode": "direct_path_24d", "target_steps": 20},
        "training": {"rollout_curriculum": [], "seed": 17},
    }


def _seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _one_step(model, optimizer, scheduler) -> tuple[float, int]:
    # This imitates the trainer's stochastic horizon choice and uses all three
    # saved RNG families, making the resume assertion stronger than a fixed
    # batch-only optimizer check.
    horizon = int(torch.randint(0, 20, (1,)).item())
    jitter = float(random.random() + np.random.random())
    x = torch.tensor([[1.0, -0.5]])
    target = torch.tensor([[0.25]])
    prediction = model(x + jitter * 0.01)
    loss = (prediction - target).pow(2).mean() + horizon * 1e-4
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    optimizer.step()
    scheduler.step()
    return float(loss.detach()), horizon


def _new_training_state(initial_state):
    model = nn.Linear(2, 1)
    model.load_state_dict(initial_state)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda _: 1.0)
    return model, optimizer, scheduler


def test_checkpoint_resume_is_exact_for_model_optimizer_scheduler_and_rng(tmp_path):
    _seed_all(17)
    initial_model = nn.Linear(2, 1)
    initial_state = {key: value.detach().clone() for key, value in initial_model.state_dict().items()}

    _seed_all(17)
    continuous_model, continuous_optimizer, continuous_scheduler = _new_training_state(initial_state)
    continuous = [
        _one_step(continuous_model, continuous_optimizer, continuous_scheduler)
        for _ in range(4)
    ]

    _seed_all(17)
    first_model, first_optimizer, first_scheduler = _new_training_state(initial_state)
    interrupted = [
        _one_step(first_model, first_optimizer, first_scheduler)
        for _ in range(2)
    ]
    checkpoint_path = tmp_path / "checkpoint.pt"
    save_checkpoint(
        str(checkpoint_path),
        2,
        first_model,
        first_optimizer,
        first_scheduler,
        _config(),
        provenance={"unit_test": True},
    )

    resumed_model, resumed_optimizer, resumed_scheduler = _new_training_state(initial_state)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    resumed_model.load_state_dict(checkpoint["model_state_dict"])
    resumed_optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    resumed_scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
    assert restore_rng_state(checkpoint)
    resumed = [
        _one_step(resumed_model, resumed_optimizer, resumed_scheduler)
        for _ in range(2)
    ]

    assert interrupted == continuous[:2]
    assert resumed == continuous[2:]
    for key, expected in continuous_model.state_dict().items():
        torch.testing.assert_close(resumed_model.state_dict()[key], expected, rtol=0, atol=0)
    assert checkpoint["provenance"] == {"unit_test": True}
    assert checkpoint["exact_resume"] == {
        "schema_version": 1,
        "rng_states_by_rank": 1,
        "data_position": False,
    }


def _epoch_batches(sampler, *, epoch: int, batch_size: int) -> list[list[int]]:
    """Mirror a drop_last shuffled loader without touching global RNG."""

    sampler.set_epoch(epoch)
    indices = list(iter(sampler))
    usable = len(indices) // batch_size * batch_size
    return [
        indices[start : start + batch_size]
        for start in range(0, usable, batch_size)
    ]


def _one_indexed_step(model, optimizer, scheduler, batch_indices) -> tuple[float, int, tuple[int, ...]]:
    """A tiny training step whose value depends on sampler ordering and RNG."""

    horizon = int(torch.randint(0, 20, (1,)).item())
    jitter = float(random.random() + np.random.random())
    x = torch.tensor([[float(batch_indices[0]), float(batch_indices[1])]])
    target = torch.tensor([[0.25]])
    prediction = model(x * 0.1 + jitter * 0.01)
    loss = (prediction - target).pow(2).mean() + horizon * 1e-4
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    optimizer.step()
    scheduler.step()
    return float(loss.detach()), horizon, tuple(batch_indices)


def _run_indexed_steps(
    model,
    optimizer,
    scheduler,
    *,
    sampler: EpochRandomSampler,
    epoch: int,
    next_batch_index: int,
    micro_step: int,
    steps: int,
) -> tuple[list[tuple[float, int, tuple[int, ...]]], object]:
    """Run ``steps`` while producing the exact next-batch checkpoint state."""

    batch_size = 2
    loader_length = len(sampler) // batch_size
    history = []
    # The caller restores its checkpoint RNG and supplies a fresh sampler; the
    # data-position object is sufficient to continue from the right batch.
    while len(history) < steps:
        batches = _epoch_batches(sampler, epoch=epoch, batch_size=batch_size)
        for batch_index, batch_indices in enumerate(batches):
            if batch_index < next_batch_index:
                continue
            history.append(_one_indexed_step(model, optimizer, scheduler, batch_indices))
            micro_step += 1
            position = next_data_position(
                epoch=epoch,
                completed_batch_index=batch_index,
                loader_length=loader_length,
                micro_step=micro_step,
                world_size=1,
                batch_size=batch_size,
                accumulation_steps=1,
            )
            if len(history) == steps:
                return history, position
        epoch += 1
        next_batch_index = 0
    raise AssertionError("unreachable")


def test_checkpoint_resume_restores_data_order_across_epoch_boundary(tmp_path):
    """A restart must not replay early shuffled batches or alter later RNG."""

    _seed_all(9)
    initial = nn.Linear(2, 1)
    initial_state = {key: value.detach().clone() for key, value in initial.state_dict().items()}

    _seed_all(9)
    continuous_model, continuous_optimizer, continuous_scheduler = _new_training_state(initial_state)
    continuous, _ = _run_indexed_steps(
        continuous_model,
        continuous_optimizer,
        continuous_scheduler,
        sampler=EpochRandomSampler(range(7), seed=31),
        epoch=0,
        next_batch_index=0,
        micro_step=0,
        steps=4,
    )

    _seed_all(9)
    first_model, first_optimizer, first_scheduler = _new_training_state(initial_state)
    interrupted, position = _run_indexed_steps(
        first_model,
        first_optimizer,
        first_scheduler,
        sampler=EpochRandomSampler(range(7), seed=31),
        epoch=0,
        next_batch_index=0,
        micro_step=0,
        steps=2,
    )
    checkpoint_path = tmp_path / "checkpoint_with_position.pt"
    save_checkpoint(
        str(checkpoint_path),
        2,
        first_model,
        first_optimizer,
        first_scheduler,
        _config(),
        data_position=position,
    )

    resumed_model, resumed_optimizer, resumed_scheduler = _new_training_state(initial_state)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    resumed_model.load_state_dict(checkpoint["model_state_dict"])
    resumed_optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    resumed_scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
    assert restore_rng_state(checkpoint)
    restored_position = restore_data_position(
        checkpoint["data_position"],
        loader_length=3,
        world_size=1,
        batch_size=2,
        accumulation_steps=1,
        expected_micro_step=2,
    )
    assert restored_position is not None
    resumed, _ = _run_indexed_steps(
        resumed_model,
        resumed_optimizer,
        resumed_scheduler,
        sampler=EpochRandomSampler(range(7), seed=31),
        epoch=restored_position.epoch,
        next_batch_index=restored_position.next_batch_index,
        micro_step=restored_position.micro_step,
        steps=2,
    )

    assert interrupted == continuous[:2]
    assert resumed == continuous[2:]
    for key, expected in continuous_model.state_dict().items():
        torch.testing.assert_close(resumed_model.state_dict()[key], expected, rtol=0, atol=0)


def test_resume_rejects_changed_loader_shape_or_accumulation():
    position = next_data_position(
        epoch=0,
        completed_batch_index=0,
        loader_length=3,
        micro_step=1,
        world_size=1,
        batch_size=2,
        accumulation_steps=1,
    )
    with pytest.raises(ValueError, match="batch_size"):
        restore_data_position(
            position.as_dict(),
            loader_length=3,
            world_size=1,
            batch_size=4,
            accumulation_steps=1,
            expected_micro_step=1,
        )


def test_rank_specific_rng_state_is_required_for_exact_distributed_resume():
    _seed_all(101)
    rank_zero_state = capture_rng_state()
    _seed_all(202)
    rank_one_state = capture_rng_state()
    rank_one_next = (random.random(), float(np.random.random()), torch.rand(1))

    checkpoint = {"rng_states_by_rank": [rank_zero_state, rank_one_state]}
    _seed_all(999)
    assert restore_rng_state(checkpoint, rank=1, world_size=2)
    actual_next = (random.random(), float(np.random.random()), torch.rand(1))
    assert actual_next[:2] == rank_one_next[:2]
    torch.testing.assert_close(actual_next[2], rank_one_next[2], rtol=0, atol=0)

    with pytest.raises(ValueError, match="one saved RNG state per current DDP rank"):
        restore_rng_state(
            {"rng_states_by_rank": [rank_zero_state]},
            rank=1,
            world_size=2,
        )
