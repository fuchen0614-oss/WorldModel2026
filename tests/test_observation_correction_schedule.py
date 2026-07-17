from __future__ import annotations

import torch

from train.observation_correction_schedule import (
    build_observation_correction_inputs,
    sample_reveal_mask,
)


def test_reveal_schedule_is_no_reveal_or_exactly_one_reveal():
    generator = torch.Generator().manual_seed(7)
    reveal = sample_reveal_mask(
        256,
        20,
        device=torch.device("cpu"),
        generator=generator,
    )
    counts = reveal.sum(dim=1)
    assert set(counts.tolist()).issubset({0.0, 1.0})
    selected = reveal.bool()
    if selected.any():
        indices = selected.nonzero(as_tuple=False)[:, 1]
        assert int(indices.min()) >= 2
        assert int(indices.max()) <= 15


def test_correction_inputs_keep_targets_outside_the_base_model_view():
    batch = {
        "x_target": torch.rand(2, 20, 4, 8, 8),
        "target_mask": torch.ones(2, 20, 8, 8),
    }
    values = build_observation_correction_inputs(
        batch,
        rollout_steps=20,
        generator=torch.Generator().manual_seed(3),
    )
    assert set(values) == {"observations", "observation_mask", "reveal_mask"}
    assert values["observations"].shape == batch["x_target"].shape
    assert values["reveal_mask"].shape == (2, 20)
