from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")
nn = torch.nn

from models.dynamics.obsworld_direct_path import ObsWorldDirectPathModel


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

    def decode_states(self, states, baseline=None):
        # Signature mirrors the production ObsWorldV2Core.decode_states, which
        # accepts an optional residual ``baseline``. The tiny stand-in decoder is
        # absolute (baseline-independent), so the argument is accepted and unused.
        batch, steps = states.shape[:2]
        # A deterministic decoder that exposes every endpoint state's first dim.
        value = states[..., 0].mean(dim=2).view(batch, steps, 1, 1, 1)
        return {"mean": value.expand(batch, steps, 4, 2, 2)}


class _PrefixSumTransition(nn.Module):
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
        delta = (d_segment * d_mask_segment).sum(dim=(1, 2)).view(-1, 1, 1)
        next_state = state + delta
        if not return_diagnostics:
            return next_state
        return {
            "state": next_state,
            # ``delta`` is broadcast over state tokens as [B,1,1].  The
            # production transition reports a vector diagnostic per sample,
            # so flatten the two singleton axes before constructing the tiny
            # stand-in summary.
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


def test_direct_path_uses_only_prefix_weather_for_each_endpoint():
    model = ObsWorldDirectPathModel(_TinyCore(), _PrefixSumTransition())
    base = _batch()
    changed = _batch()
    # Future local index 7 is D_path index 17; it must not affect endpoints
    # before index 7 and must affect that endpoint and all later endpoints.
    changed["D_path"][:, 17, 0] = 3.0

    first = model(base)
    second = model(changed)

    assert first["pred"].shape == (1, 20, 4, 2, 2)
    assert torch.equal(first["step_indices"], torch.arange(20))
    assert torch.allclose(first["pred"][:, :7], second["pred"][:, :7])
    assert not torch.allclose(first["pred"][:, 7:], second["pred"][:, 7:])


def test_direct_path_ignores_future_target_tensors_and_supports_subset_decoding():
    model = ObsWorldDirectPathModel(_TinyCore(), _PrefixSumTransition())
    batch = _batch()
    base = model(batch, selected_steps=[0, 5, 19])
    batch["x_target"] = torch.rand(1, 20, 4, 2, 2)
    batch["target_mask"] = torch.zeros(1, 20, 2, 2)
    with_targets = model(batch, selected_steps=[0, 5, 19])

    assert torch.equal(base["step_indices"], torch.tensor([0, 5, 19]))
    assert base["pred"].shape[1] == 3
    assert torch.allclose(base["pred"], with_targets["pred"])
