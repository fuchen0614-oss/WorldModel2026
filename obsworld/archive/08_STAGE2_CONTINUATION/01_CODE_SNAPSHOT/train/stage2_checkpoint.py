"""Deterministic data-order and resume state for Stage2 training.

Saving only model/optimizer RNG is insufficient when a shuffled DataLoader is
recreated after a restart: the resumed job can silently replay the first
batches of an epoch.  These small, dependency-light helpers make the data
position an explicit checkpoint invariant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sized

import torch
from torch.utils.data import Sampler


def parse_epoch_checkpoint_steps(config: Mapping[str, Any]) -> dict[int, str]:
    """Validate configured named checkpoints keyed by optimizer step.

    Stage2 uses optimizer steps as its canonical progress unit.  A formal
    EarthNet run may additionally request a small number of human-readable
    epoch tags (for example ``epoch100``), without saving a checkpoint at
    every epoch.  The returned mapping is deliberately independent of the
    dataset and can therefore be tested before a trainer is launched.
    """

    entries = config.get("epoch_checkpoint_steps", [])
    if entries is None:
        return {}
    if not isinstance(entries, (list, tuple)):
        raise TypeError("epoch_checkpoint_steps must be a list of mappings")

    result: dict[int, str] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise TypeError("each epoch_checkpoint_steps entry must be a mapping")
        if "step" not in entry or "tag" not in entry:
            raise ValueError("each epoch checkpoint entry requires step and tag")
        step = int(entry["step"])
        tag = str(entry["tag"]).strip()
        if step <= 0:
            raise ValueError(f"epoch checkpoint step must be positive, got {step}")
        # Tags become filenames; keep them portable and shell-safe.
        if not tag or not tag.replace("_", "").isalnum():
            raise ValueError(f"invalid epoch checkpoint tag: {tag!r}")
        previous = result.get(step)
        if previous is not None and previous != tag:
            raise ValueError(
                f"duplicate epoch checkpoint step {step}: {previous!r} vs {tag!r}"
            )
        result[step] = tag
    return result


def parse_epoch_checkpoint_epochs(config: Mapping[str, Any]) -> tuple[int, ...]:
    """Return unique positive epoch numbers for dynamic checkpoint tagging."""

    entries = config.get("epoch_checkpoint_epochs", [])
    if entries is None:
        return ()
    if not isinstance(entries, (list, tuple)):
        raise TypeError("epoch_checkpoint_epochs must be a list of integers")
    epochs = tuple(sorted({int(entry) for entry in entries}))
    if any(epoch <= 0 for epoch in epochs):
        raise ValueError(
            "epoch checkpoint numbers must be positive, got "
            f"{epochs!r}"
        )
    return epochs


class EpochRandomSampler(Sampler[int]):
    """A deterministic permutation defined only by ``seed`` and ``epoch``."""

    def __init__(self, data_source: Sized, *, seed: int):
        self.data_source = data_source
        self.seed = int(seed)
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        if epoch < 0:
            raise ValueError(f"epoch must be non-negative, got {epoch}")
        self.epoch = int(epoch)

    def __iter__(self):
        generator = torch.Generator()
        generator.manual_seed(self.seed + self.epoch)
        yield from torch.randperm(len(self.data_source), generator=generator).tolist()

    def __len__(self) -> int:
        return len(self.data_source)


@dataclass(frozen=True)
class Stage2DataPosition:
    """The next unconsumed batch at an optimizer-step checkpoint boundary."""

    epoch: int
    next_batch_index: int
    loader_length: int
    micro_step: int
    world_size: int
    batch_size: int
    accumulation_steps: int

    def __post_init__(self) -> None:
        if self.epoch < 0:
            raise ValueError("epoch must be non-negative")
        if self.loader_length <= 0:
            raise ValueError("loader_length must be positive")
        if not 0 <= self.next_batch_index < self.loader_length:
            raise ValueError(
                "next_batch_index must lie in [0,loader_length), got "
                f"{self.next_batch_index} for loader_length={self.loader_length}"
            )
        if self.micro_step < 0 or self.world_size <= 0:
            raise ValueError("micro_step must be non-negative and world_size positive")
        if self.batch_size <= 0 or self.accumulation_steps <= 0:
            raise ValueError("batch_size and accumulation_steps must be positive")

    def as_dict(self) -> dict[str, int]:
        return {
            "epoch": self.epoch,
            "next_batch_index": self.next_batch_index,
            "loader_length": self.loader_length,
            "micro_step": self.micro_step,
            "world_size": self.world_size,
            "batch_size": self.batch_size,
            "accumulation_steps": self.accumulation_steps,
        }


def next_data_position(
    *,
    epoch: int,
    completed_batch_index: int,
    loader_length: int,
    micro_step: int,
    world_size: int,
    batch_size: int,
    accumulation_steps: int,
) -> Stage2DataPosition:
    """Return the next logical batch, normalizing an end-of-epoch boundary."""

    if not 0 <= completed_batch_index < loader_length:
        raise ValueError(
            "completed_batch_index must lie in [0,loader_length), got "
            f"{completed_batch_index} for loader_length={loader_length}"
        )
    next_epoch = int(epoch)
    next_index = int(completed_batch_index) + 1
    if next_index == loader_length:
        next_epoch += 1
        next_index = 0
    return Stage2DataPosition(
        epoch=next_epoch,
        next_batch_index=next_index,
        loader_length=int(loader_length),
        micro_step=int(micro_step),
        world_size=int(world_size),
        batch_size=int(batch_size),
        accumulation_steps=int(accumulation_steps),
    )


def restore_data_position(
    payload: Mapping[str, Any] | None,
    *,
    loader_length: int,
    world_size: int,
    batch_size: int,
    accumulation_steps: int,
    expected_micro_step: int,
) -> Stage2DataPosition | None:
    """Validate a saved position against the currently requested run shape.

    ``None`` denotes an older checkpoint that predates exact-resume metadata;
    callers may choose a documented epoch-zero fallback but must never claim
    it is bitwise-equivalent recovery.
    """

    if payload is None:
        return None
    if not isinstance(payload, Mapping):
        raise TypeError("checkpoint data_position must be a mapping")
    try:
        position = Stage2DataPosition(
            epoch=int(payload["epoch"]),
            next_batch_index=int(payload["next_batch_index"]),
            loader_length=int(payload["loader_length"]),
            micro_step=int(payload["micro_step"]),
            world_size=int(payload["world_size"]),
            batch_size=int(payload["batch_size"]),
            accumulation_steps=int(payload["accumulation_steps"]),
        )
    except KeyError as exc:
        raise KeyError(f"checkpoint data_position is missing {exc.args[0]!r}") from exc

    expected = {
        "loader_length": int(loader_length),
        "world_size": int(world_size),
        "batch_size": int(batch_size),
        "accumulation_steps": int(accumulation_steps),
        "micro_step": int(expected_micro_step),
    }
    actual = position.as_dict()
    mismatches = [
        f"{name}: checkpoint={actual[name]!r}, current={value!r}"
        for name, value in expected.items()
        if actual[name] != value
    ]
    if mismatches:
        raise ValueError(
            "Exact Stage2 resume requires the same loader/world/batch/"
            "accumulation position; "
            + "; ".join(mismatches)
        )
    return position
