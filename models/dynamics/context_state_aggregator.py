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
        min_token_clear_fraction: float = 0.05,
        zero_unobserved_tokens: bool = False,
    ):
        super().__init__()
        if not 0.0 <= min_token_clear_fraction <= 1.0:
            raise ValueError("min_token_clear_fraction must be in [0, 1]")
        self.state_dim = state_dim
        self.max_context_frames = max_context_frames
        # Keep the legacy 0.05 default so existing Direct-DGH checkpoints keep
        # their old boolean-mask behavior.  Formal v2 configs set 0.25 and
        # additionally pass continuous token coverage.
        self.min_token_clear_fraction = float(min_token_clear_fraction)
        # Keep this opt-in for legacy Direct-DGH checkpoints.  Formal v2
        # explicitly enables it because a completely unobserved token must not
        # acquire a learned LayerNorm bias and masquerade as a state estimate.
        self.zero_unobserved_tokens = bool(zero_unobserved_tokens)
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

    def forward(
        self,
        states: torch.Tensor,
        valid_mask: Optional[torch.Tensor] = None,
        *,
        return_valid_mask: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        """Aggregate states.

        Args:
            states: [B,T,N,D]
            valid_mask: [B,T] or [B,T,N] boolean validity, or float coverage
                in [0,1]. Coverage=0 is always excluded. Positive coverage
                affects attention continuously; first/last state selection uses
                ``min_token_clear_fraction``.
            return_valid_mask: when true, additionally return [B,N] marking
                positions with at least one usable context observation.
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
            coverage = torch.ones(b, t, n, dtype=states.dtype, device=states.device)
        else:
            coverage = valid_mask.to(device=states.device, dtype=states.dtype)
            if coverage.dim() == 2:
                coverage = coverage[:, :, None].expand(b, t, n)
            if coverage.shape != (b, t, n):
                raise ValueError(
                    f"Expected valid_mask [B,T] or [B,T,N], got {tuple(valid_mask.shape)}"
                )
            if not torch.isfinite(coverage).all():
                raise ValueError("context coverage/valid_mask must be finite")
            coverage = coverage.clamp(0.0, 1.0)

        attention_valid = coverage.gt(0.0)
        state_valid = coverage.ge(self.min_token_clear_fraction)

        temporal_states = states + self.time_embedding[:t].view(1, t, 1, d)
        raw_scores = self.score(temporal_states).squeeze(-1)  # [B,T,N]
        # A positive but low clear fraction remains usable, but gets a
        # proportionally lower attention logit.  log(coverage) is finite after
        # the explicit zero mask and avoids a hard arbitrary visibility gate.
        raw_scores = raw_scores + torch.log(coverage.clamp_min(1e-6))
        raw_scores = raw_scores.masked_fill(~attention_valid, -1e4)
        weights = torch.softmax(raw_scores, dim=1)
        weights = weights * attention_valid.to(dtype=weights.dtype)
        weights = weights / weights.sum(dim=1, keepdim=True).clamp_min(1e-6)
        attended = (states * weights.unsqueeze(-1)).sum(dim=1)

        last = _last_valid_state(states, state_valid)
        first = _first_valid_state(states, state_valid)
        trend = last - first
        aggregated = self.out_norm(
            last + self.adapter(attended) + self.trend_adapter(trend)
        )
        state_valid_mask = state_valid.any(dim=1)
        if self.zero_unobserved_tokens:
            # Do not let LayerNorm's learned bias create a nonzero latent
            # state at locations that had no valid context observation at all.
            aggregated = torch.where(
                state_valid_mask.unsqueeze(-1),
                aggregated,
                torch.zeros_like(aggregated),
            )
        if return_valid_mask:
            return aggregated, state_valid_mask
        return aggregated

    def get_config(self) -> dict:
        return {
            "state_dim": self.state_dim,
            "max_context_frames": self.max_context_frames,
            "min_token_clear_fraction": self.min_token_clear_fraction,
            "zero_unobserved_tokens": self.zero_unobserved_tokens,
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
