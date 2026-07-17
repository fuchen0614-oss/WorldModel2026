"""Deterministic reveal schedules for the Observation Correction U runs."""

from __future__ import annotations

from typing import Optional

import torch

from data.stage2_contract import observation_correction_view


def sample_reveal_mask(
    batch_size: int,
    steps: int,
    *,
    device: torch.device,
    generator: Optional[torch.Generator] = None,
    reveal_probability: float = 0.5,
    min_reveal_step: int = 2,
    max_reveal_step: int = 15,
) -> torch.Tensor:
    """Sample the frozen RQ2 schedule: no reveal or exactly one reveal.

    The reveal index is zero-based and inclusive.  For the formal 20-step
    horizon this is steps 2--15, matching the experiment plan.  A short
    curriculum with fewer than three steps has no legal reveal and therefore
    produces the no-reveal branch only.
    """

    if batch_size <= 0 or steps <= 0:
        raise ValueError("batch_size and steps must be positive")
    if not 0.0 <= reveal_probability <= 1.0:
        raise ValueError("reveal_probability must lie in [0,1]")
    if min_reveal_step < 0 or max_reveal_step < min_reveal_step:
        raise ValueError("reveal step bounds are invalid")
    reveal = torch.zeros(batch_size, steps, device=device)
    if steps <= min_reveal_step:
        return reveal
    upper = min(max_reveal_step, steps - 1)
    random_device = (
        torch.device(getattr(generator, "device", "cpu"))
        if generator is not None
        else device
    )
    draws = torch.rand(batch_size, generator=generator, device=random_device).to(device)
    selected = draws < float(reveal_probability)
    if not bool(selected.any()):
        return reveal
    indices = torch.randint(
        min_reveal_step,
        upper + 1,
        (batch_size,),
        generator=generator,
        device=random_device,
    ).to(device)
    rows = torch.arange(batch_size, device=device)[selected]
    reveal[rows, indices[selected]] = 1.0
    return reveal


def build_observation_correction_inputs(
    batch: dict[str, torch.Tensor],
    *,
    rollout_steps: int,
    generator: Optional[torch.Generator] = None,
    reveal_probability: float = 0.5,
) -> dict[str, torch.Tensor]:
    """Build explicit correction-only inputs from training supervision.

    This is the one controlled place where future targets are used as a
    simulated revealed observation.  The base model input is still produced
    by ``model_input_view`` and never contains these tensors.
    """

    for name in ("x_target", "target_mask"):
        if name not in batch:
            raise KeyError(f"Stage2 correction schedule requires {name}")
    target = batch["x_target"]
    target_mask = batch["target_mask"]
    if target.dim() != 5 or target_mask.shape != (target.shape[0], target.shape[1], target.shape[-2], target.shape[-1]):
        raise ValueError("x_target/target_mask have incompatible shapes")
    if not 1 <= rollout_steps <= target.shape[1]:
        raise ValueError(f"rollout_steps must lie in [1,{target.shape[1]}], got {rollout_steps}")
    reveal_mask = sample_reveal_mask(
        target.shape[0],
        rollout_steps,
        device=target.device,
        generator=generator,
        reveal_probability=reveal_probability,
    )
    # Keep the full target-length tensors so the wrapper can validate the
    # schedule independently of the active curriculum prefix.
    full_reveal = torch.zeros(target.shape[0], target.shape[1], device=target.device)
    full_reveal[:, :rollout_steps] = reveal_mask
    return observation_correction_view(
        {
            "observations": target,
            "observation_mask": target_mask,
            "reveal_mask": full_reveal,
        }
    )
