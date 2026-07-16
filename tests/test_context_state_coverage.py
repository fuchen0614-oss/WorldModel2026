from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from models.dynamics.context_state_aggregator import ContextStateAggregator


def test_context_aggregator_uses_coverage_and_zeros_unobserved_tokens():
    torch.manual_seed(0)
    aggregator = ContextStateAggregator(
        state_dim=4,
        hidden_dim=8,
        max_context_frames=10,
        min_token_clear_fraction=0.25,
        zero_unobserved_tokens=True,
    )
    states = torch.randn(1, 3, 4, 4)
    coverage = torch.tensor(
        [[[1.0, 0.2, 0.0, 0.5], [1.0, 0.1, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]]]
    )

    result, valid = aggregator(states, coverage, return_valid_mask=True)

    assert valid.tolist() == [[True, False, False, True]]
    assert torch.allclose(result[:, 1:3], torch.zeros_like(result[:, 1:3]))
    assert torch.isfinite(result).all()
