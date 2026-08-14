"""Condition encoders for Stage2 external drivers and forecast horizons."""

from __future__ import annotations

import torch
import torch.nn as nn


class DriverEncoder(nn.Module):
    """Encode D values together with an explicit missing-value mask."""

    def __init__(
        self,
        in_dim: int = 9,
        hidden_dim: int = 64,
        out_dim: int = 32,
        dropout: float = 0.0,
    ):
        super().__init__()
        self.in_dim = in_dim
        self.out_dim = out_dim
        self.net = nn.Sequential(
            nn.LayerNorm(in_dim * 2),
            nn.Linear(in_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, out_dim),
            nn.LayerNorm(out_dim),
        )

    def forward(self, values: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
        if values.shape != valid_mask.shape:
            raise ValueError(
                f"driver values/mask shape mismatch: {tuple(values.shape)} vs {tuple(valid_mask.shape)}"
            )
        if values.shape[-1] != self.in_dim:
            raise ValueError(f"Expected driver in_dim={self.in_dim}, got {values.shape[-1]}")
        mask = valid_mask.to(dtype=values.dtype, device=values.device)
        return self.net(torch.cat([values * mask, mask], dim=-1))

    def get_config(self) -> dict:
        return {"in_dim": self.in_dim, "out_dim": self.out_dim}


class HorizonEncoder(nn.Module):
    """Encode lead time using linear and logarithmic day-scale features."""

    def __init__(
        self,
        out_dim: int = 16,
        hidden_dim: int = 32,
        max_h_days: float = 100.0,
    ):
        super().__init__()
        self.out_dim = out_dim
        self.max_h_days = float(max_h_days)
        self.net = nn.Sequential(
            nn.Linear(2, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, out_dim),
            nn.LayerNorm(out_dim),
        )

    def forward(self, horizons: torch.Tensor) -> torch.Tensor:
        normalized = (horizons.float() / max(self.max_h_days, 1.0)).clamp_min(0.0)
        log_scaled = torch.log1p(horizons.float().clamp_min(0.0)) / torch.log1p(
            horizons.new_tensor(max(self.max_h_days, 1.0)).float()
        )
        return self.net(torch.stack([normalized, log_scaled], dim=-1))

    def get_config(self) -> dict:
        return {
            "out_dim": self.out_dim,
            "max_h_days": self.max_h_days,
        }
