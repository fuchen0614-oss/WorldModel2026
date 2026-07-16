"""Shared variable-length conditioning encoder for Stage2-v2 transitions.

The legacy Direct-DGH path receives one already-accumulated 9-D vector per
target.  The formal world-model path instead consumes an ordered segment of
five-day 24-D E-OBS tokens.  This module is deliberately shared by Direct24,
open-loop rollout, and future partition consistency branches, so a difference
between those models cannot be attributed to three unrelated weather heads.
"""

from __future__ import annotations

from typing import Sequence

import torch
import torch.nn as nn

from data.earthnet_conditioning import FULL24_FEATURE_NAMES


class IntervalDriverEncoder(nn.Module):
    """Encode one or more ordered D/C/delta-t tokens into a segment summary.

    ``D_mask`` is a feature-level availability indicator, not a time padding
    mask.  Even an entirely missing D token remains meaningful through its
    calendar and duration fields, so the encoder never drops it or produces a
    NaN.  This is essential for a fair ``no_D`` ablation: it removes measured
    weather values while retaining time/season information.
    """

    def __init__(
        self,
        input_dim: int = 24,
        calendar_dim: int = 2,
        token_dim: int = 64,
        hidden_dim: int = 128,
        out_dim: int = 32,
        num_layers: int = 2,
        num_heads: int = 4,
        dropout: float = 0.0,
        max_segment_length: int = 20,
        feature_names: Sequence[str] = FULL24_FEATURE_NAMES,
    ):
        super().__init__()
        if input_dim != len(FULL24_FEATURE_NAMES):
            raise ValueError(
                "Formal IntervalDriverEncoder requires the frozen 24-D E-OBS "
                f"layout, got input_dim={input_dim}"
            )
        if tuple(feature_names) != tuple(FULL24_FEATURE_NAMES):
            raise ValueError(
                "IntervalDriverEncoder feature_names differ from the frozen "
                "Stage2-v2 FULL24_FEATURE_NAMES order"
            )
        if calendar_dim != 2:
            raise ValueError("Stage2-v2 calendar path must have exactly sin/cos dimensions")
        if token_dim <= 0 or hidden_dim <= 0 or out_dim <= 0:
            raise ValueError("token_dim, hidden_dim, and out_dim must be positive")
        if num_layers <= 0 or num_heads <= 0 or token_dim % num_heads:
            raise ValueError(
                "num_layers/num_heads must be positive and token_dim divisible by num_heads"
            )
        if max_segment_length <= 0:
            raise ValueError("max_segment_length must be positive")

        self.input_dim = input_dim
        self.calendar_dim = calendar_dim
        self.token_dim = token_dim
        self.out_dim = out_dim
        self.max_segment_length = max_segment_length
        self.feature_names = tuple(feature_names)

        self.driver_value_mask = nn.Sequential(
            nn.LayerNorm(input_dim * 2),
            nn.Linear(input_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, token_dim),
        )
        self.calendar = nn.Sequential(
            nn.Linear(calendar_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, token_dim),
        )
        self.duration = nn.Sequential(
            nn.Linear(1, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, token_dim),
        )
        self.position = nn.Parameter(torch.zeros(max_segment_length, token_dim))
        nn.init.trunc_normal_(self.position, std=0.02)
        layer = nn.TransformerEncoderLayer(
            d_model=token_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 2,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
            norm_first=True,
        )
        self.temporal = nn.TransformerEncoder(layer, num_layers=num_layers)
        self.token_norm = nn.LayerNorm(token_dim)
        self.pool_score = nn.Sequential(
            nn.LayerNorm(token_dim),
            nn.Linear(token_dim, 1),
        )
        self.summary = nn.Sequential(
            nn.LayerNorm(token_dim),
            nn.Linear(token_dim, out_dim),
            nn.GELU(),
            nn.LayerNorm(out_dim),
        )

    def forward(
        self,
        d_segment: torch.Tensor,
        d_mask_segment: torch.Tensor,
        calendar_segment: torch.Tensor,
        delta_t_segment: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        """Encode a segment with common length ``L`` across the batch.

        Args:
            d_segment: normalized E-OBS values ``[B,L,24]``.
            d_mask_segment: matching binary availability mask ``[B,L,24]``.
            calendar_segment: five-day calendar sin/cos ``[B,L,2]``.
            delta_t_segment: positive duration in days ``[B,L]``.
        """

        _validate_segment_inputs(
            d_segment,
            d_mask_segment,
            calendar_segment,
            delta_t_segment,
            input_dim=self.input_dim,
            calendar_dim=self.calendar_dim,
            max_segment_length=self.max_segment_length,
        )
        mask = d_mask_segment.to(dtype=d_segment.dtype, device=d_segment.device)
        masked_values = d_segment * mask
        duration = torch.log1p(delta_t_segment.to(dtype=d_segment.dtype)).unsqueeze(-1)
        length = d_segment.shape[1]
        token = (
            self.driver_value_mask(torch.cat([masked_values, mask], dim=-1))
            + self.calendar(calendar_segment.to(dtype=d_segment.dtype))
            + self.duration(duration)
            + self.position[:length].view(1, length, self.token_dim)
        )
        tokens = self.token_norm(self.temporal(token))

        # Calendar/duration stay valid when D is completely missing.  A small
        # finite availability prior makes observed windows preferred without
        # accidentally assigning zero total weight to an all-missing segment.
        observed_fraction = mask.mean(dim=-1)
        score = self.pool_score(tokens).squeeze(-1)
        score = score + torch.log(observed_fraction.clamp_min(0.05))
        weights = torch.softmax(score, dim=1)
        pooled = (tokens * weights.unsqueeze(-1)).sum(dim=1)
        segment_valid = observed_fraction.gt(0.0)
        return {
            "tokens": tokens,
            "summary": self.summary(pooled),
            "segment_valid": segment_valid,
            "observed_fraction": observed_fraction,
            "pool_weights": weights,
        }

    def get_config(self) -> dict:
        return {
            "input_dim": self.input_dim,
            "calendar_dim": self.calendar_dim,
            "token_dim": self.token_dim,
            "out_dim": self.out_dim,
            "max_segment_length": self.max_segment_length,
            "feature_names": list(self.feature_names),
        }


def _validate_segment_inputs(
    d_segment: torch.Tensor,
    d_mask_segment: torch.Tensor,
    calendar_segment: torch.Tensor,
    delta_t_segment: torch.Tensor,
    *,
    input_dim: int,
    calendar_dim: int,
    max_segment_length: int,
) -> None:
    if d_segment.dim() != 3:
        raise ValueError(f"D segment must be [B,L,{input_dim}], got {tuple(d_segment.shape)}")
    batch, length, features = d_segment.shape
    if features != input_dim:
        raise ValueError(f"D segment final dim must be {input_dim}, got {features}")
    if length <= 0 or length > max_segment_length:
        raise ValueError(
            f"D segment length must lie in [1,{max_segment_length}], got {length}"
        )
    if d_mask_segment.shape != d_segment.shape:
        raise ValueError(
            "D segment/mask shape mismatch: "
            f"{tuple(d_segment.shape)} vs {tuple(d_mask_segment.shape)}"
        )
    if calendar_segment.shape != (batch, length, calendar_dim):
        raise ValueError(
            f"calendar segment must be [B,L,{calendar_dim}], got {tuple(calendar_segment.shape)}"
        )
    if delta_t_segment.shape != (batch, length):
        raise ValueError(
            f"delta_t segment must be [B,L], got {tuple(delta_t_segment.shape)}"
        )
    if not torch.isfinite(d_segment).all():
        raise ValueError("D segment must be finite after Stage2-v2 normalization")
    if not torch.isfinite(calendar_segment).all():
        raise ValueError("calendar segment must be finite")
    if not torch.isfinite(delta_t_segment).all() or torch.any(delta_t_segment <= 0):
        raise ValueError("delta_t segment must be finite and strictly positive")
    if not torch.all((d_mask_segment == 0) | (d_mask_segment == 1)):
        raise ValueError("D segment mask must be binary")
