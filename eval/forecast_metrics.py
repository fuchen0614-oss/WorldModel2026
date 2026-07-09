"""Streaming EarthNet forecasting metrics for the ObsWorld main table."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict

import torch

from data.earthnet_fields import compute_ndvi


class ForecastMetricAccumulator:
    def __init__(self, red_index: int = 2, nir_index: int = 3):
        self.red_index = red_index
        self.nir_index = nir_index
        self.sums = defaultdict(float)
        self.counts = defaultdict(float)

    def update(
        self,
        pred: torch.Tensor,
        target: torch.Tensor,
        clear_mask: torch.Tensor,
        horizons: torch.Tensor,
        context: torch.Tensor,
        context_mask: torch.Tensor,
    ) -> None:
        mask = clear_mask.float()
        channel_error = (pred.float() - target.float()).abs().mean(dim=2)
        persistence_frame = _last_clear_observation(
            context[:, :, : target.shape[2]],
            context_mask,
        )
        persistence = persistence_frame[:, None].expand_as(target)
        persistence_error = (persistence.float() - target.float()).abs().mean(dim=2)
        ndvi_error = (
            compute_ndvi(pred.float(), self.red_index, self.nir_index).clamp(-1, 1)
            - compute_ndvi(target.float(), self.red_index, self.nir_index).clamp(-1, 1)
        ).abs()

        self._add("MAE", channel_error, mask)
        self._add("NDVI_MAE", ndvi_error, mask)
        self._add("persistence_MAE", persistence_error, mask)

        long_mask = mask * horizons.ge(60).float()[:, :, None, None]
        self._add("long_horizon_MAE", channel_error, long_mask)

        for horizon in torch.unique(horizons.detach()).tolist():
            horizon_mask = mask * horizons.eq(horizon).float()[:, :, None, None]
            self._add(f"MAE_h{int(round(horizon))}", channel_error, horizon_mask)
            self._add(f"NDVI_MAE_h{int(round(horizon))}", ndvi_error, horizon_mask)

    def _add(self, name: str, values: torch.Tensor, mask: torch.Tensor) -> None:
        self.sums[name] += float((values * mask).sum().detach().cpu())
        self.counts[name] += float(mask.sum().detach().cpu())

    def compute(self) -> Dict[str, float]:
        result = {
            name: self.sums[name] / max(self.counts[name], 1.0)
            for name in sorted(self.sums)
        }
        if "MAE" in result and "persistence_MAE" in result:
            result["skill_vs_persistence"] = 1.0 - (
                result["MAE"] / max(result["persistence_MAE"], 1e-8)
            )
        return result


def _last_clear_observation(
    context: torch.Tensor,
    clear_mask: torch.Tensor,
) -> torch.Tensor:
    b, t, c, h, w = context.shape
    time_index = torch.arange(t, device=context.device).view(1, t, 1, 1)
    last_idx = torch.where(clear_mask.gt(0), time_index, -1).amax(dim=1)
    last_idx = last_idx.clamp_min(0)
    gather_idx = last_idx[:, None, None].expand(b, 1, c, h, w)
    return context.gather(dim=1, index=gather_idx).squeeze(1)
