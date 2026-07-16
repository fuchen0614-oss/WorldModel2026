from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")
nn = torch.nn

from models.dynamics.controlled_transition import ControlledTransition
from models.dynamics.interval_driver_encoder import IntervalDriverEncoder


class _AdditiveDynamics(nn.Module):
    """Tiny deterministic transition used to isolate conditioning semantics."""

    latent_dim = 4
    driver_dim = 8
    geo_dim = 2
    time_dim = 3

    def forward(self, state, driver=None, geo=None, time_delta=None):
        driver_term = driver[:, :4].unsqueeze(1)
        geo_term = geo.mean(dim=-1, keepdim=True)
        time_term = time_delta[:, :1].unsqueeze(1)
        return state + driver_term + geo_term + time_term


class _SimpleHorizon(nn.Module):
    out_dim = 3

    def forward(self, elapsed_days):
        return torch.stack(
            [elapsed_days, elapsed_days * 0.5, elapsed_days * 0.25], dim=-1
        )


def _encoder() -> IntervalDriverEncoder:
    return IntervalDriverEncoder(
        input_dim=24,
        token_dim=16,
        hidden_dim=24,
        out_dim=8,
        num_layers=1,
        num_heads=4,
        max_segment_length=20,
        dropout=0.0,
    )


@pytest.mark.parametrize("length", [1, 2, 4])
def test_interval_driver_encoder_accepts_variable_segment_lengths(length):
    torch.manual_seed(0)
    encoder = _encoder()
    d = torch.randn(2, length, 24)
    mask = torch.ones_like(d)
    calendar = torch.randn(2, length, 2)
    dt = torch.full((2, length), 5.0)

    result = encoder(d, mask, calendar, dt)

    assert result["tokens"].shape == (2, length, 16)
    assert result["summary"].shape == (2, 8)
    assert result["segment_valid"].shape == (2, length)
    assert torch.isfinite(result["summary"]).all()


def test_interval_driver_encoder_is_finite_when_all_weather_is_missing():
    encoder = _encoder()
    d = torch.zeros(2, 2, 24)
    mask = torch.zeros_like(d)
    calendar = torch.tensor([[[0.0, 1.0], [0.1, 0.9]]]).repeat(2, 1, 1)
    dt = torch.full((2, 2), 5.0)

    result = encoder(d, mask, calendar, dt)

    assert not result["segment_valid"].any()
    assert torch.isfinite(result["tokens"]).all()
    assert torch.isfinite(result["summary"]).all()
    assert torch.allclose(result["pool_weights"].sum(dim=1), torch.ones(2))


def test_no_d_intervention_keeps_calendar_and_duration_but_removes_weather_values():
    torch.manual_seed(3)
    transition = ControlledTransition(
        _encoder(),
        _SimpleHorizon(),
        _AdditiveDynamics(),
        use_D=False,
        use_G=True,
        use_h=True,
    ).eval()
    state = torch.zeros(1, 3, 4)
    geo = torch.zeros(1, 3, 2)
    mask = torch.ones(1, 1, 24)
    calendar = torch.tensor([[[0.0, 1.0]]])
    dt = torch.tensor([[5.0]])

    first = transition(state, torch.zeros(1, 1, 24), mask, calendar, dt, geo)
    changed_weather = transition(
        state,
        torch.full((1, 1, 24), 100.0),
        mask,
        calendar,
        dt,
        geo,
    )
    changed_calendar = transition(
        state,
        torch.zeros(1, 1, 24),
        mask,
        torch.tensor([[[1.0, 0.0]]]),
        dt,
        geo,
    )

    assert torch.allclose(first, changed_weather)
    assert not torch.allclose(first, changed_calendar)
