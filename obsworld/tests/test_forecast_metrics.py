from __future__ import annotations

import math

import pytest


torch = pytest.importorskip("torch")

from eval.forecast_metrics import ForecastMetricAccumulator


def test_persistence_metric_resizes_high_resolution_context_to_target_grid():
    """Stage2-v2 context and evaluation grids intentionally have different sizes."""

    accumulator = ForecastMetricAccumulator(red_index=2, nir_index=3)
    pred = torch.zeros(1, 3, 4, 4, 4)
    target = torch.zeros_like(pred)
    clear_mask = torch.ones(1, 3, 4, 4)
    horizons = torch.tensor([[5.0, 10.0, 100.0]])
    context = torch.stack(
        [
            torch.zeros(4, 8, 8),
            torch.ones(4, 8, 8),
        ],
        dim=0,
    ).unsqueeze(0)
    context_mask = torch.ones(1, 2, 8, 8)

    accumulator.update(
        pred,
        target,
        clear_mask,
        horizons,
        context,
        context_mask,
    )
    result = accumulator.compute()

    assert result["MAE"] == pytest.approx(0.0)
    assert result["persistence_MAE"] == pytest.approx(1.0)


def test_skill_is_undefined_when_persistence_has_zero_error():
    accumulator = ForecastMetricAccumulator(red_index=2, nir_index=3)
    pred = torch.zeros(1, 1, 4, 4, 4)
    accumulator.update(
        pred,
        pred.clone(),
        torch.ones(1, 1, 4, 4),
        torch.tensor([[5.0]]),
        torch.zeros(1, 1, 4, 8, 8),
        torch.ones(1, 1, 8, 8),
    )
    assert math.isnan(accumulator.compute()["skill_vs_persistence"])
