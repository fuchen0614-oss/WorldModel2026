"""Temporal aggregation of Stage1.5 state tokens for EarthNet context frames."""

import torch
import torch.nn as nn
from typing import Optional


class ContextStateAggregator(nn.Module):
    """Aggregate [B,T,N,D] state tokens into one context state [B,N,D].

    The module keeps a residual connection from the last valid state, so the
    starting behavior is close to persistence while still allowing historical
    trend cues to enter the dynamics model.
    """

    def __init__(
        self,
        state_dim: int = 256,
        hidden_dim: int = 256,
        dropout: float = 0.0,
        max_context_frames: int = 32,
    ):
        super().__init__()
        self.state_dim = state_dim
        self.max_context_frames = max_context_frames
        self.time_embedding = nn.Parameter(
            torch.zeros(max_context_frames, state_dim)
        )
        nn.init.trunc_normal_(self.time_embedding, std=0.02)
        self.score = nn.Sequential(
            nn.LayerNorm(state_dim),
            nn.Linear(state_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )
        self.adapter = nn.Sequential(
            nn.LayerNorm(state_dim),
            nn.Linear(state_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, state_dim),
        )
        self.trend_adapter = nn.Sequential(
            nn.LayerNorm(state_dim),
            nn.Linear(state_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, state_dim),
        )
        self.out_norm = nn.LayerNorm(state_dim)
        nn.init.zeros_(self.adapter[-1].weight)
        nn.init.zeros_(self.adapter[-1].bias)
        nn.init.zeros_(self.trend_adapter[-1].weight)
        nn.init.zeros_(self.trend_adapter[-1].bias)

    def forward(self, states: torch.Tensor, valid_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Aggregate states.

        Args:
            states: [B,T,N,D]
            valid_mask: [B,T] or [B,T,N] with 1/True for usable observations.
        """

        if states.dim() != 4:
            raise ValueError(f"Expected states [B,T,N,D], got {tuple(states.shape)}")
        b, t, n, d = states.shape
        if d != self.state_dim:
            raise ValueError(f"Expected state_dim={self.state_dim}, got {d}")
        if t > self.max_context_frames:
            raise ValueError(
                f"Context length {t} exceeds max_context_frames={self.max_context_frames}"
            )
        if valid_mask is None:
            valid_mask = torch.ones(b, t, n, dtype=torch.bool, device=states.device)
        else:
            valid_mask = valid_mask.to(device=states.device).bool()
            if valid_mask.dim() == 2:
                valid_mask = valid_mask[:, :, None].expand(b, t, n)
            if valid_mask.shape != (b, t, n):
                raise ValueError(
                    f"Expected valid_mask [B,T] or [B,T,N], got {tuple(valid_mask.shape)}"
                )

        temporal_states = states + self.time_embedding[:t].view(1, t, 1, d)
        raw_scores = self.score(temporal_states).squeeze(-1)  # [B,T,N]
        raw_scores = raw_scores.masked_fill(~valid_mask, -1e4)
        weights = torch.softmax(raw_scores, dim=1)
        weights = weights * valid_mask.to(dtype=weights.dtype)
        weights = weights / weights.sum(dim=1, keepdim=True).clamp_min(1e-6)
        attended = (states * weights.unsqueeze(-1)).sum(dim=1)

        last = _last_valid_state(states, valid_mask)
        first = _first_valid_state(states, valid_mask)
        trend = last - first
        return self.out_norm(
            last + self.adapter(attended) + self.trend_adapter(trend)
        )

    def get_config(self) -> dict:
        return {
            "state_dim": self.state_dim,
            "max_context_frames": self.max_context_frames,
        }


def _last_valid_state(states: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
    b, t, n, d = states.shape
    time_index = torch.arange(t, device=states.device).view(1, t, 1)
    last_idx = torch.where(valid_mask, time_index, -1).amax(dim=1)
    last_idx = torch.where(last_idx.ge(0), last_idx, t - 1)
    gather_idx = last_idx[:, None, :, None].expand(b, 1, n, d)
    gathered = states.gather(dim=1, index=gather_idx).squeeze(1)
    has_valid = valid_mask.any(dim=1).unsqueeze(-1)
    return torch.where(has_valid, gathered, torch.zeros_like(gathered))


def _first_valid_state(states: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
    b, t, n, d = states.shape
    time_index = torch.arange(t, device=states.device).view(1, t, 1)
    first_idx = torch.where(valid_mask, time_index, t).amin(dim=1)
    first_idx = torch.where(first_idx.lt(t), first_idx, 0)
    gather_idx = first_idx[:, None, :, None].expand(b, 1, n, d)
    gathered = states.gather(dim=1, index=gather_idx).squeeze(1)
    has_valid = valid_mask.any(dim=1).unsqueeze(-1)
    return torch.where(has_valid, gathered, torch.zeros_like(gathered))
