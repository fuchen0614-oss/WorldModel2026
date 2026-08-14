from __future__ import annotations

import pytest


torch = pytest.importorskip("torch")
nn = torch.nn

from models.dynamics.obsworld_partition import ObsWorldPartitionModel


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
        delta = (d_segment * d_mask_segment).sum(dim=(1, 2)).view(-1, 1, 1)
        next_state = state + delta
        if not return_diagnostics:
            return next_state
        return {
            "state": next_state,
            "driver_summary": delta.reshape(-1, 1).expand(-1, 3),
            "driver_observed_fraction": d_mask_segment.mean(dim=-1),
            "elapsed_days": delta_t_segment.sum(dim=1),
        }


def _batch() -> dict:
    return {
        "x_context": torch.zeros(1, 10, 4, 4, 4),
        "context_mask": torch.ones(1, 10, 4, 4),
        "D_path": torch.zeros(1, 30, 24),
        "D_mask": torch.ones(1, 30, 24),
        "C_path": torch.zeros(1, 30, 2),
        "delta_t_path": torch.full((1, 30), 5.0),
        "G": torch.zeros(1, 1, 2, 2),
        "G_mask": torch.ones(1, 1, 2, 2),
        "h": torch.arange(5, 101, 5).view(1, 20).float(),
    }


def test_partition_uses_exact_same_two_token_control_path_as_composition():
    model = ObsWorldPartitionModel(_TinyCore(), _AdditiveTransition())
    batch = _batch()
    # Five-day driver increments are 1, 2, 3 at local future indices 0,1,2.
    batch["D_path"][:, 10, 0] = 1.0
    batch["D_path"][:, 11, 0] = 2.0
    batch["D_path"][:, 12, 0] = 3.0

    output = model(
        batch,
        selected_steps=[0, 1, 2],
        max_rollout_steps=3,
        partition_start=1,
    )
    partition = output["partition"]

    assert partition["start_index"].item() == 1
    assert partition["endpoint_index"].item() == 2
    # The start is s_1=1.  Both paths then add the exact 2+3 controls.
    assert partition["z_start"][0, 0, 0].item() == 1.0
    assert partition["z_direct"][0, 0, 0].item() == 6.0
    assert partition["z_composed"][0, 0, 0].item() == 6.0
    assert partition["direct_elapsed_days"].item() == 10.0
    assert partition["compose_elapsed_days"].tolist() == [[5.0, 5.0]]


def test_partition_rejects_anchor_without_two_active_intervals():
    model = ObsWorldPartitionModel(_TinyCore(), _AdditiveTransition())
    with pytest.raises(ValueError, match="leave two active"):
        model(_batch(), max_rollout_steps=2, partition_start=1)


def test_partition_transition_ignores_future_pixel_supervision_tensors():
    model = ObsWorldPartitionModel(_TinyCore(), _AdditiveTransition())
    batch = _batch()
    batch["D_path"][:, 10, 0] = 1.0
    baseline = model(batch, max_rollout_steps=2, partition_start=0)
    batch["x_target"] = torch.rand(1, 20, 4, 2, 2)
    batch["target_mask"] = torch.zeros(1, 20, 2, 2)
    with_targets = model(batch, max_rollout_steps=2, partition_start=0)

    assert torch.allclose(
        baseline["partition"]["z_direct"],
        with_targets["partition"]["z_direct"],
    )
    assert torch.allclose(
        baseline["partition"]["z_composed"],
        with_targets["partition"]["z_composed"],
    )
