from __future__ import annotations

import pytest


torch = pytest.importorskip("torch")
nn = torch.nn

from models.dynamics.obsworld_rollout import ObsWorldRolloutModel


class _TinyCore(nn.Module):
    def initialize_state(self, batch):
        batch_size = batch["x_context"].shape[0]
        return {
            "state": torch.zeros(batch_size, 4, 3, device=batch["x_context"].device),
            "state_valid_mask": torch.ones(batch_size, 4, dtype=torch.bool, device=batch["x_context"].device),
            "context_token_coverage": torch.ones(batch_size, 10, 4, device=batch["x_context"].device),
        }

    def encode_geo(self, geo, geo_mask, *, expected_tokens):
        assert expected_tokens == 4
        return torch.zeros(geo.shape[0], 4, 2, device=geo.device)

    def decode_states(self, states):
        batch, steps = states.shape[:2]
        value = states[..., 0].mean(dim=2).view(batch, steps, 1, 1, 1)
        return {"mean": value.expand(batch, steps, 4, 2, 2)}


class _AdditiveTransition(nn.Module):
    def forward(
        self,
        state,
        d_segment,
        d_mask_segment,
        calendar_segment,
        delta_t_segment,
        geo_tokens,
        *,
        return_diagnostics=False,
    ):
        assert d_segment.shape[1] == 1  # rollout must use local 5-day tokens
        delta = (d_segment * d_mask_segment).sum(dim=(1, 2)).view(-1, 1, 1)
        next_state = state + delta
        if not return_diagnostics:
            return next_state
        return {
            "state": next_state,
            "driver_summary": delta.reshape(-1, 1).expand(-1, 3),
            "driver_observed_fraction": d_mask_segment.mean(dim=-1),
        }


def _batch() -> dict:
    batch_size = 1
    return {
        "x_context": torch.zeros(batch_size, 10, 4, 4, 4),
        "context_mask": torch.ones(batch_size, 10, 4, 4),
        "D_path": torch.zeros(batch_size, 30, 24),
        "D_mask": torch.ones(batch_size, 30, 24),
        "C_path": torch.zeros(batch_size, 30, 2),
        "delta_t_path": torch.full((batch_size, 30), 5.0),
        "G": torch.zeros(batch_size, 1, 2, 2),
        "G_mask": torch.ones(batch_size, 1, 2, 2),
        "h": torch.arange(5, 101, 5).view(1, 20).float(),
    }


def test_rollout_reuses_predicted_state_and_is_causal_in_future_driver_order():
    model = ObsWorldRolloutModel(_TinyCore(), _AdditiveTransition())
    batch = _batch()
    # D_path index 12 is local future step 2.  It cannot affect rollout
    # states at 5/10 days, but does affect every later recursive state.
    batch["D_path"][:, 12, 0] = 2.0

    output = model(batch, selected_steps=[0, 1, 2, 4], max_rollout_steps=5)

    assert output["z_rollout"].shape == (1, 5, 4, 3)
    assert output["step_indices"].tolist() == [0, 1, 2, 4]
    values = output["z_rollout"][0, :, 0, 0].tolist()
    assert values == [0.0, 0.0, 2.0, 2.0, 2.0]
    assert output["pred"].shape == (1, 4, 4, 2, 2)


def test_short_rollout_default_decodes_only_active_curriculum_prefix():
    model = ObsWorldRolloutModel(_TinyCore(), _AdditiveTransition())
    output = model(_batch(), max_rollout_steps=2)

    assert output["step_indices"].tolist() == [0, 1]
    assert int(output["rollout_steps"]) == 2
    assert output["pred"].shape[1] == 2


def test_rollout_rejects_supervision_endpoint_beyond_curriculum_length():
    model = ObsWorldRolloutModel(_TinyCore(), _AdditiveTransition())
    with pytest.raises(ValueError, match="outside the active rollout"):
        model(_batch(), selected_steps=[2], max_rollout_steps=2)
