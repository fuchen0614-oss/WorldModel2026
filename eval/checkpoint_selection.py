"""Pure helpers for complete validation checkpoint selection."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Mapping


def discover_checkpoint_candidates(
    checkpoint_dir: str | Path,
    *,
    include_step_checkpoints: bool = False,
    explicit: Iterable[str | Path] = (),
) -> list[Path]:
    """Discover paper-facing checkpoint milestones in a deterministic order.

    ``checkpoint_best.pt`` and named epoch checkpoints are always included.
    Ordinary 1000-step snapshots are opt-in because evaluating every snapshot
    over the full val_dev split is usually an accidental multi-day job.
    """

    root = Path(checkpoint_dir).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"checkpoint directory not found: {root}")
    paths: dict[str, Path] = {}
    for path in root.glob("checkpoint_best.pt"):
        if path.is_file():
            paths[path.name] = path
    for path in root.glob("checkpoint_epoch*_step_*.pt"):
        if path.is_file():
            paths[path.name] = path
    if include_step_checkpoints:
        for path in root.glob("checkpoint_step_*.pt"):
            if path.is_file():
                paths[path.name] = path
    for value in explicit:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"explicit checkpoint not found: {path}")
        paths[path.name] = path
    candidates = list(paths.values())
    if not candidates:
        raise FileNotFoundError(
            "No checkpoint_best.pt or named epoch checkpoint was found in "
            f"{root}; pass --checkpoint explicitly."
        )
    return sorted(candidates, key=lambda item: item.name)


def select_best_candidate(
    evaluations: Iterable[Mapping[str, object]],
    *,
    metric: str,
    mode: str = "min",
) -> dict[str, object]:
    """Select the best finite metric while preserving all candidate records."""

    mode = str(mode).lower()
    if mode not in {"min", "max"}:
        raise ValueError(f"selection mode must be min or max, got {mode!r}")
    records = [dict(item) for item in evaluations]
    valid = []
    for record in records:
        value = record.get("metrics", {}).get(metric) if isinstance(record.get("metrics"), Mapping) else None
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            record["selection_metric"] = float(value)
            valid.append(record)
        else:
            record["selection_metric"] = None
    if not valid:
        raise ValueError(f"No candidate produced a finite metric {metric!r}")
    winner = min(valid, key=lambda item: (item["selection_metric"], str(item.get("checkpoint")))) if mode == "min" else max(valid, key=lambda item: (item["selection_metric"], str(item.get("checkpoint"))))
    return {
        "schema_version": 1,
        "metric": metric,
        "mode": mode,
        "selected_checkpoint": winner.get("checkpoint"),
        "selected_metric": winner["selection_metric"],
        "candidates": records,
    }
