"""Token-aligned geographic conditioning for Stage 2 dynamics."""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class GeoTokenizer(nn.Module):
    """Pool elevation-like rasters to the state-token grid."""

    def __init__(
        self,
        in_channels: int = 1,
        geo_dim: int = 16,
        img_size: int = 256,
        patch_size: int = 16,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.geo_dim = geo_dim
        self.img_size = img_size
        self.patch_size = patch_size
        self.grid_size = img_size // patch_size
        self.proj = nn.Sequential(
            nn.LayerNorm(in_channels),
            nn.Linear(in_channels, geo_dim),
            nn.GELU(),
            nn.LayerNorm(geo_dim),
        )
        self.missing_embedding = nn.Parameter(torch.zeros(geo_dim))

    def forward(self, geo: torch.Tensor, valid_mask: torch.Tensor = None) -> torch.Tensor:
        """Return [B,N,geo_dim] tokens from [B,C,H,W]."""

        if geo.dim() != 4:
            raise ValueError(f"Expected geo [B,C,H,W], got {tuple(geo.shape)}")
        if geo.shape[1] != self.in_channels:
            raise ValueError(f"Expected {self.in_channels} geo channels, got {geo.shape[1]}")
        if geo.shape[-2:] != (self.img_size, self.img_size):
            geo = F.interpolate(geo, size=(self.img_size, self.img_size), mode="bilinear", align_corners=False)
        if valid_mask is None:
            valid_mask = torch.ones_like(geo[:, :1])
        else:
            valid_mask = valid_mask.to(dtype=geo.dtype, device=geo.device)
            if valid_mask.shape[-2:] != (self.img_size, self.img_size):
                valid_mask = F.interpolate(
                    valid_mask, size=(self.img_size, self.img_size), mode="nearest"
                )
        numerator = F.avg_pool2d(
            geo * valid_mask,
            kernel_size=self.patch_size,
            stride=self.patch_size,
        )
        denominator = F.avg_pool2d(
            valid_mask,
            kernel_size=self.patch_size,
            stride=self.patch_size,
        )
        pooled = numerator / denominator.clamp_min(1e-6)
        b, c, gh, gw = pooled.shape
        if gh != self.grid_size or gw != self.grid_size:
            raise ValueError(f"Unexpected geo token grid {(gh, gw)}; expected {(self.grid_size, self.grid_size)}")
        tokens = pooled.flatten(2).transpose(1, 2)  # [B,N,C]
        encoded = self.proj(tokens)
        token_valid = denominator.flatten(2).transpose(1, 2).gt(0)
        return torch.where(
            token_valid,
            encoded,
            self.missing_embedding.view(1, 1, -1),
        )

    def get_config(self) -> dict:
        return {
            "in_channels": self.in_channels,
            "geo_dim": self.geo_dim,
            "img_size": self.img_size,
            "patch_size": self.patch_size,
        }
