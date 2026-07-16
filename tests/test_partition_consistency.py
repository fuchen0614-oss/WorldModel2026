from __future__ import annotations

import pytest


torch = pytest.importorskip("torch")

from models.dynamics.partition_consistency import (
    PartitionConsistencyLoss,
    sample_two_step_partition_start,
)


def test_partition_start_is_uniformly_legal_for_active_rollout_prefix():
    torch.manual_seed(3)
    starts = {
        sample_two_step_partition_start(5, device=torch.device("cpu"))
        for _ in range(50)
    }
    assert starts
    assert starts <= {0, 1, 2, 3}
    with pytest.raises(ValueError, match="at least two"):
        sample_two_step_partition_start(1, device=torch.device("cpu"))


def test_symmetric_stop_gradient_updates_both_partition_paths():
    torch.manual_seed(5)
    z_direct = torch.randn(2, 3, 4, requires_grad=True)
    z_composed = torch.randn(2, 3, 4, requires_grad=True)
    prediction_direct = torch.rand(2, 4, 3, 3, requires_grad=True)
    prediction_composed = torch.rand(2, 4, 3, 3, requires_grad=True)
    target = torch.rand(2, 4, 3, 3)
    loss_fn = PartitionConsistencyLoss(
        red_index=2,
        nir_index=3,
        w_state=1.0,
        w_observation=0.0,
        w_ndvi=0.0,
        w_endpoint=0.0,
    )

    losses = loss_fn(
        z_direct=z_direct,
        z_composed=z_composed,
        pred_direct=prediction_direct,
        pred_composed=prediction_composed,
        target=target,
        target_mask=torch.ones(2, 3, 3),
        state_mask=torch.ones(2, 3, dtype=torch.bool),
    )
    losses["total"].backward()

    assert z_direct.grad is not None and z_direct.grad.abs().sum() > 0
    assert z_composed.grad is not None and z_composed.grad.abs().sum() > 0
    # Zero-weighted observation terms may retain a zero-gradient graph under
    # PyTorch, but they must not change either prediction tensor.
    assert prediction_direct.grad is not None and prediction_direct.grad.abs().sum() == 0
    assert prediction_composed.grad is not None and prediction_composed.grad.abs().sum() == 0


def test_both_partition_branches_receive_the_same_terminal_observation_target():
    zeros = torch.zeros(1, 2, 3)
    target = torch.zeros(1, 4, 2, 2)
    direct = torch.full_like(target, 0.2)
    composed = torch.full_like(target, 0.4)
    losses = PartitionConsistencyLoss(
        red_index=2,
        nir_index=3,
        w_state=0.0,
        w_observation=0.0,
        w_ndvi=0.0,
        w_endpoint=1.0,
        endpoint_ndvi_weight=0.0,
    )(
        z_direct=zeros,
        z_composed=zeros,
        pred_direct=direct,
        pred_composed=composed,
        target=target,
        target_mask=torch.ones(1, 2, 2),
    )

    assert losses["endpoint_direct"] < losses["endpoint_composed"]
    assert torch.allclose(
        losses["endpoint"],
        0.5 * (losses["endpoint_direct"] + losses["endpoint_composed"]),
    )
