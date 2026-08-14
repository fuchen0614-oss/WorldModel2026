from __future__ import annotations

import pytest
import torch

from data.stage2_contract import (
    assert_model_batch_has_no_evaluation_fields,
    model_input_view,
    observation_correction_view,
    validate_stage2_batch,
    validate_stage2_v2_batch,
)


def _v2_batch() -> dict[str, torch.Tensor]:
    batch_size = 2
    delta_t = torch.full((batch_size, 30), 5.0)
    return {
        "x_context": torch.zeros(batch_size, 10, 4, 16, 16),
        "context_mask": torch.ones(batch_size, 10, 16, 16),
        "D_path": torch.zeros(batch_size, 30, 24),
        "D_mask": torch.ones(batch_size, 30, 24),
        "D_valid_day_count": torch.full((batch_size, 30, 8), 5, dtype=torch.long),
        "C_path": torch.zeros(batch_size, 30, 2),
        "delta_t_path": delta_t,
        "G": torch.zeros(batch_size, 1, 8, 8),
        "G_mask": torch.ones(batch_size, 1, 8, 8),
        "h": torch.arange(5, 101, 5).repeat(batch_size, 1).float(),
        "x_target": torch.zeros(batch_size, 20, 4, 8, 8),
        "target_mask": torch.ones(batch_size, 20, 8, 8),
        "official_eval_mask": torch.ones(batch_size, 20, 8, 8),
        "official_eval_eligibility": torch.ones(batch_size, 8, 8),
    }


def test_v2_contract_allows_distinct_context_and_target_geometry():
    batch = _v2_batch()
    validate_stage2_v2_batch(batch, require_evaluation=True)
    # The generic validator automatically dispatches based on D_path.
    validate_stage2_batch(batch, require_evaluation=True)

    inputs = model_input_view(batch)
    assert set(inputs) == {
        "x_context", "context_mask", "D_path", "D_mask", "C_path",
        "delta_t_path", "G", "G_mask", "h",
    }
    assert "D_valid_day_count" not in inputs
    assert "x_target" not in inputs
    assert "official_eval_mask" not in inputs
    assert_model_batch_has_no_evaluation_fields(inputs)


def test_v2_contract_catches_wrong_future_horizon_alignment():
    batch = _v2_batch()
    batch["h"][:, 0] = 10.0
    with pytest.raises(ValueError, match="cumsum"):
        validate_stage2_v2_batch(batch)


def test_v2_model_view_excludes_targets_even_for_audit_rich_batch():
    batch = _v2_batch()
    view = model_input_view(batch, include_training_targets=True)
    assert "x_target" in view and "target_mask" in view
    assert "D_valid_day_count" not in view
    assert "official_eval_mask" not in view


def test_v2_contract_accepts_physical4_layout_when_explicitly_expected():
    batch = _v2_batch()
    batch["D_path"] = torch.zeros(2, 30, 4)
    batch["D_mask"] = torch.ones(2, 30, 4)
    batch["D_valid_day_count"] = torch.full((2, 30, 4), 5, dtype=torch.long)
    validate_stage2_v2_batch(batch, expected_driver_dim=4)
    with pytest.raises(ValueError, match="configured driver encoder"):
        validate_stage2_v2_batch(batch, expected_driver_dim=24)


def test_observation_correction_view_is_explicit_and_not_part_of_model_view():
    values = observation_correction_view(
        {
            "observations": torch.zeros(2, 20, 4, 8, 8),
            "observation_mask": torch.ones(2, 20, 8, 8),
            "reveal_mask": torch.zeros(2, 20),
        }
    )
    assert set(values) == {"observations", "observation_mask", "reveal_mask"}
    with pytest.raises(KeyError, match="missing fields"):
        observation_correction_view(
            {
                "observations": torch.zeros(2, 20, 4, 8, 8),
                "observation_mask": torch.ones(2, 20, 8, 8),
            }
        )
