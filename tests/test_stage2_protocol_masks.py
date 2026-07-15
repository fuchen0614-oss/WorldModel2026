from __future__ import annotations

import pytest
import torch

from data.stage2_contract import (
    assert_model_batch_has_no_evaluation_fields,
    evaluation_only_view,
    model_input_view,
    training_supervision_view,
    validate_stage2_batch,
)


def _batch() -> dict[str, torch.Tensor]:
    return {
        "x_context": torch.zeros(2, 10, 4, 8, 8),
        "context_mask": torch.ones(2, 10, 8, 8),
        "D": torch.zeros(2, 20, 9),
        "D_mask": torch.ones(2, 20, 9),
        "G": torch.zeros(2, 1, 8, 8),
        "G_mask": torch.ones(2, 1, 8, 8),
        "h": torch.arange(5, 101, 5).repeat(2, 1).float(),
        "x_target": torch.zeros(2, 20, 4, 8, 8),
        "target_mask": torch.ones(2, 20, 8, 8),
        "official_eval_mask": torch.ones(2, 20, 8, 8),
        "official_eval_eligibility": torch.ones(2, 8, 8),
    }


def test_three_mask_roles_are_disjoint_at_model_boundary():
    batch = _batch()
    validate_stage2_batch(batch, require_targets=True, require_evaluation=True)

    inputs = model_input_view(batch)
    supervision = training_supervision_view(batch)
    evaluation = evaluation_only_view(batch)

    assert "context_mask" in inputs
    assert "target_mask" not in inputs
    assert "official_eval_mask" not in inputs
    assert set(supervision) == {"x_target", "target_mask"}
    assert set(evaluation) == {
        "official_eval_mask",
        "official_eval_eligibility",
    }
    assert_model_batch_has_no_evaluation_fields(inputs)
    with pytest.raises(ValueError, match="Evaluation-only"):
        assert_model_batch_has_no_evaluation_fields(batch)


def test_latent_target_ablation_still_excludes_official_masks():
    view = model_input_view(_batch(), include_training_targets=True)
    assert "x_target" in view and "target_mask" in view
    assert "official_eval_mask" not in view
    assert "official_eval_eligibility" not in view
