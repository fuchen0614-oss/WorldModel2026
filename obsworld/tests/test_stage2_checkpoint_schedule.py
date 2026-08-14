from __future__ import annotations

import pytest

from train.stage2_checkpoint import (
    parse_epoch_checkpoint_epochs,
    parse_epoch_checkpoint_steps,
)


def test_epoch_checkpoint_schedule_is_validated_and_sorted_by_step():
    assert parse_epoch_checkpoint_steps(
        {
            "epoch_checkpoint_steps": [
                {"step": 71400, "tag": "epoch200"},
                {"step": 35700, "tag": "epoch100"},
            ]
        }
    ) == {35700: "epoch100", 71400: "epoch200"}


def test_epoch_checkpoint_schedule_rejects_duplicate_or_unsafe_entries():
    with pytest.raises(ValueError, match="duplicate"):
        parse_epoch_checkpoint_steps(
            {
                "epoch_checkpoint_steps": [
                    {"step": 10, "tag": "epoch10"},
                    {"step": 10, "tag": "epoch10b"},
                ]
            }
        )
    with pytest.raises(ValueError, match="invalid"):
        parse_epoch_checkpoint_steps(
            {"epoch_checkpoint_steps": [{"step": 10, "tag": "epoch/10"}]}
        )


def test_epoch_checkpoint_epochs_are_unique_and_sorted():
    assert parse_epoch_checkpoint_epochs(
        {"epoch_checkpoint_epochs": [200, 100, 100, 150]}
    ) == (100, 150, 200)

    with pytest.raises(ValueError, match="positive"):
        parse_epoch_checkpoint_epochs({"epoch_checkpoint_epochs": [0, 100]})
