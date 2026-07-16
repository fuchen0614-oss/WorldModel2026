from __future__ import annotations

import torch

from models.dynamics.observation_correction import (
    ObservationCorrectionCell,
    ObservationCorrectionRollout,
    update_staleness,
)


def _cell() -> ObservationCorrectionCell:
    torch.manual_seed(7)
    return ObservationCorrectionCell(state_dim=3, feature_dim=2, hidden_dim=8)


def test_q_zero_is_exact_identity_and_staleness_only_ages():
    cell = _cell()
    state = torch.randn(2, 4, 3)
    residual = torch.randn(2, 4, 2)
    age = torch.ones(2, 4)
    output = cell(state, residual, torch.zeros(2, 4), age, torch.ones(2))

    assert torch.equal(output["state"], state)
    age_output = update_staleness(age, torch.zeros(2, 4), 5.0, torch.ones(2))
    assert torch.equal(age_output["age_prior"], torch.full_like(age, 6.0))
    assert torch.equal(age_output["age_posterior"], torch.full_like(age, 6.0))


def test_rollout_predicts_before_update_and_partial_support_is_local():
    model = ObservationCorrectionRollout(_cell())
    initial = torch.zeros(1, 2, 3)
    observed = torch.zeros(1, 2, 2, 2)
    # Step 0 reveals only token 0; step 1 has no reveal.  The observation is
    # constructed relative to the predicted state, not the initial state.
    observed[:, 0, 0] = 2.0
    q_path = torch.tensor([[[1.0, 0.0], [0.0, 0.0]]])
    reveal = torch.tensor([[1.0, 0.0]])

    def transition(state: torch.Tensor, step: int) -> torch.Tensor:
        return state + 1.0

    def features(state: torch.Tensor, step: int) -> torch.Tensor:
        return state[..., :2]

    output = model(initial, transition, features, observed, q_path, reveal, elapsed_days=5.0)
    # Prior at step 0 is one, so the residual for token 0 is one.  Token 1 has
    # no support and must remain exactly at its prior state.
    assert torch.equal(output["prior_states"][0, 0], torch.ones(2, 3))
    assert torch.equal(output["posterior_states"][0, 0, 1], torch.ones(3))
    assert torch.equal(output["effective_q"][0, 0, 1], torch.tensor(0.0))
    assert torch.equal(output["age_posteriors"][0, 0, 1], torch.tensor(5.0))
    assert torch.equal(output["age_posteriors"][0, 0, 0], torch.tensor(0.0))
    assert output["posterior_states"][0, 0, 0].ne(output["prior_states"][0, 0, 0]).any()


def test_unrevealed_future_features_and_masks_cannot_change_rollout():
    rollout = ObservationCorrectionRollout(_cell())
    initial = torch.randn(1, 3, 3)
    observed = torch.randn(1, 3, 3, 2)
    q_path = torch.rand(1, 3, 3)
    reveal = torch.tensor([[0.0, 1.0, 0.0]])

    def transition(state: torch.Tensor, step: int) -> torch.Tensor:
        return state + (step + 1) * 0.1

    def features(state: torch.Tensor, step: int) -> torch.Tensor:
        return state[..., :2]

    first = rollout(initial, transition, features, observed, q_path, reveal, elapsed_days=5.0)
    changed_observed = observed.clone()
    changed_q = q_path.clone()
    changed_observed[:, 0] = torch.randn_like(changed_observed[:, 0]) * 100
    changed_observed[:, 2] = torch.randn_like(changed_observed[:, 2]) * 100
    changed_q[:, 0] = 1.0
    changed_q[:, 2] = 1.0
    second = rollout(
        initial,
        transition,
        features,
        changed_observed,
        changed_q,
        reveal,
        elapsed_days=5.0,
    )

    assert torch.equal(first["posterior_states"], second["posterior_states"])
    assert torch.equal(first["age_posteriors"], second["age_posteriors"])
    assert torch.equal(first["final_state"], second["final_state"])

