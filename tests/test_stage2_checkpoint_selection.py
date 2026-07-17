from __future__ import annotations

from pathlib import Path

import pytest

from eval.checkpoint_selection import discover_checkpoint_candidates, select_best_candidate


def test_discover_checkpoint_candidates_prefers_named_milestones(tmp_path: Path):
    for name in (
        "checkpoint_best.pt",
        "checkpoint_epoch100_step_4400.pt",
        "checkpoint_epoch200_step_8800.pt",
        "checkpoint_step_1000.pt",
    ):
        (tmp_path / name).write_bytes(b"x")
    found = discover_checkpoint_candidates(tmp_path)
    assert [path.name for path in found] == [
        "checkpoint_best.pt",
        "checkpoint_epoch100_step_4400.pt",
        "checkpoint_epoch200_step_8800.pt",
    ]
    found_all = discover_checkpoint_candidates(tmp_path, include_step_checkpoints=True)
    assert "checkpoint_step_1000.pt" in {path.name for path in found_all}


def test_select_best_candidate_records_invalid_metrics_and_winner():
    selection = select_best_candidate(
        [
            {"checkpoint": "a.pt", "metrics": {"MAE": 0.4}},
            {"checkpoint": "b.pt", "metrics": {"MAE": 0.2}},
            {"checkpoint": "c.pt", "metrics": {"MAE": float("nan")}},
        ],
        metric="MAE",
        mode="min",
    )
    assert selection["selected_checkpoint"] == "b.pt"
    assert selection["selected_metric"] == pytest.approx(0.2)
    assert selection["candidates"][2]["selection_metric"] is None


def test_select_best_candidate_rejects_all_invalid_metrics():
    with pytest.raises(ValueError, match="finite metric"):
        select_best_candidate(
            [{"checkpoint": "a.pt", "metrics": {"MAE": None}}],
            metric="MAE",
        )
