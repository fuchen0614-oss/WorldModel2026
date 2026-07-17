"""Visibility-safe observation correction for the ObsWorld state machine.

This module is independent from the EarthNet loader and Stage2 trainer.  It
makes the online contract executable before wiring it into a formal run:

* a future step is predicted before its optional observation is consumed;
* an unavailable observation is an exact no-op;
* partial token support is weighted by continuous ``q``; and
* staleness is updated only from reveal support.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import torch
import torch.nn as nn


def _token_scalar(
    value: torch.Tensor,
    *,
    batch: int,
    tokens: int,
    name: str,
) -> torch.Tensor:
    """Normalize ``[B]``, ``[B,N]`` or ``[B,N,1]`` to ``[B,N]``."""

    if value.dim() == 1 and value.shape[0] == batch:
        value = value[:, None].expand(batch, tokens)
    elif value.dim() == 2 and value.shape == (batch, 1):
        value = value.expand(batch, tokens)
    elif value.dim() == 2 and value.shape == (batch, tokens):
        pass
    elif value.dim() == 3 and value.shape == (batch, tokens, 1):
        value = value[..., 0]
    else:
        raise ValueError(
            f"{name} must have shape [B], [B,1], [B,N] or [B,N,1], "
            f"got {tuple(value.shape)} for B={batch}, N={tokens}"
        )
    return value


def _validate_finite_range(value: torch.Tensor, *, name: str) -> None:
    if not torch.isfinite(value).all():
        raise ValueError(f"{name} must contain only finite values")
    if (value < 0).any() or (value > 1).any():
        raise ValueError(f"{name} must lie in [0,1]")


def update_staleness(
    age_before: torch.Tensor,
    q_obs: torch.Tensor,
    elapsed_days: torch.Tensor | float,
    reveal: Optional[torch.Tensor] = None,
) -> dict[str, torch.Tensor]:
    """Advance and partially reset token staleness.

    ``age_before`` is the age immediately before the current prediction.  The
    elapsed interval is added first; a revealed token then receives a
    continuous reset proportional to its visible support ``q_obs``.
    """

    if age_before.dim() != 2:
        raise ValueError(f"age_before must be [B,N], got {tuple(age_before.shape)}")
    batch, tokens = age_before.shape
    q = _token_scalar(q_obs, batch=batch, tokens=tokens, name="q_obs")
    _validate_finite_range(q, name="q_obs")
    if not torch.isfinite(age_before).all() or (age_before < 0).any():
        raise ValueError("age_before must be finite and non-negative")

    if not isinstance(elapsed_days, torch.Tensor):
        elapsed = torch.full_like(age_before, float(elapsed_days))
    else:
        elapsed = _token_scalar(
            elapsed_days.to(device=age_before.device, dtype=age_before.dtype),
            batch=batch,
            tokens=tokens,
            name="elapsed_days",
        )
    if not torch.isfinite(elapsed).all() or (elapsed < 0).any():
        raise ValueError("elapsed_days must be finite and non-negative")

    if reveal is None:
        reveal_tokens = torch.ones_like(q)
    else:
        reveal_tokens = _token_scalar(
            reveal.to(device=age_before.device, dtype=age_before.dtype),
            batch=batch,
            tokens=tokens,
            name="reveal",
        )
        _validate_finite_range(reveal_tokens, name="reveal")
    effective_q = q * reveal_tokens
    age_prior = age_before + elapsed
    age_posterior = age_prior * (1.0 - effective_q)
    return {
        "age_prior": age_prior,
        "age_posterior": age_posterior,
        "effective_q": effective_q,
    }


class ObservationCorrectionCell(nn.Module):
    """Apply one visibility-weighted residual correction to a belief state."""

    def __init__(
        self,
        *,
        state_dim: int,
        feature_dim: int,
        hidden_dim: int = 128,
    ) -> None:
        super().__init__()
        if state_dim <= 0 or feature_dim <= 0 or hidden_dim <= 0:
            raise ValueError("state_dim, feature_dim and hidden_dim must be positive")
        self.state_dim = int(state_dim)
        self.feature_dim = int(feature_dim)
        self.hidden_dim = int(hidden_dim)
        self.state_norm = nn.LayerNorm(self.state_dim)
        input_dim = self.state_dim + self.feature_dim + 2
        self.gate = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
        )
        self.residual = nn.Sequential(
            nn.Linear(self.feature_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, self.state_dim),
        )

    def forward(
        self,
        state_prior: torch.Tensor,
        residual: torch.Tensor,
        q_obs: torch.Tensor,
        staleness_prior: torch.Tensor,
        reveal: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        """Return posterior state and diagnostics for one prediction step."""

        if state_prior.dim() != 3:
            raise ValueError(f"state_prior must be [B,N,D], got {tuple(state_prior.shape)}")
        if residual.dim() != 3:
            raise ValueError(f"residual must be [B,N,F], got {tuple(residual.shape)}")
        batch, tokens, state_dim = state_prior.shape
        if state_dim != self.state_dim:
            raise ValueError(f"state_prior last dim must be {self.state_dim}, got {state_dim}")
        if residual.shape != (batch, tokens, self.feature_dim):
            raise ValueError(
                "residual must be [B,N,feature_dim], got "
                f"{tuple(residual.shape)} for B={batch}, N={tokens}, F={self.feature_dim}"
            )
        if staleness_prior.shape != (batch, tokens):
            raise ValueError(f"staleness_prior must be [B,N], got {tuple(staleness_prior.shape)}")
        if not torch.isfinite(state_prior).all():
            raise ValueError("state_prior must contain only finite values")

        q = _token_scalar(q_obs, batch=batch, tokens=tokens, name="q_obs")
        _validate_finite_range(q, name="q_obs")
        if reveal is None:
            reveal_tokens = torch.ones_like(q)
        else:
            reveal_tokens = _token_scalar(
                reveal.to(device=state_prior.device, dtype=state_prior.dtype),
                batch=batch,
                tokens=tokens,
                name="reveal",
            )
            _validate_finite_range(reveal_tokens, name="reveal")
        effective_q = q * reveal_tokens
        clean_residual = torch.nan_to_num(residual, nan=0.0, posinf=0.0, neginf=0.0)
        clean_staleness = torch.nan_to_num(staleness_prior, nan=0.0, posinf=0.0, neginf=0.0)
        features = torch.cat(
            [
                self.state_norm(state_prior),
                clean_residual,
                effective_q.unsqueeze(-1),
                clean_staleness.unsqueeze(-1),
            ],
            dim=-1,
        )
        gate = torch.sigmoid(self.gate(features))
        delta = self.residual(clean_residual)
        candidate = state_prior + effective_q.unsqueeze(-1) * gate * delta
        # ``where`` makes q=0 an exact identity by construction.
        posterior = torch.where(effective_q.unsqueeze(-1) > 0, candidate, state_prior)
        return {
            "state": posterior,
            "gate": gate,
            "delta": delta,
            "effective_q": effective_q,
        }


class VanillaFilterCell(nn.Module):
    """Capacity-matched additive filter baseline for the U ablation.

    This intentionally has no learned visibility gate.  It receives the same
    state/residual/support/staleness inputs as :class:`ObservationCorrectionCell`
    and applies a single learned update scaled by ``effective_q``.  The
    wrapper can therefore evaluate ``vanilla_filter`` without changing the
    data contract.  Its parameter count is reported by the caller rather than
    silently presented as a trained scientific baseline.
    """

    def __init__(self, *, state_dim: int, feature_dim: int, hidden_dim: int = 128) -> None:
        super().__init__()
        if state_dim <= 0 or feature_dim <= 0 or hidden_dim <= 0:
            raise ValueError("state_dim, feature_dim and hidden_dim must be positive")
        self.state_dim = int(state_dim)
        self.feature_dim = int(feature_dim)
        self.hidden_dim = int(hidden_dim)
        self.state_norm = nn.LayerNorm(self.state_dim)
        self.update = nn.Sequential(
            nn.Linear(self.state_dim + self.feature_dim + 2, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, self.state_dim),
        )

    def forward(
        self,
        state_prior: torch.Tensor,
        residual: torch.Tensor,
        q_obs: torch.Tensor,
        staleness_prior: torch.Tensor,
        reveal: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        if state_prior.dim() != 3:
            raise ValueError(f"state_prior must be [B,N,D], got {tuple(state_prior.shape)}")
        batch, tokens, state_dim = state_prior.shape
        if state_dim != self.state_dim:
            raise ValueError(f"state_prior last dim must be {self.state_dim}, got {state_dim}")
        if residual.shape != (batch, tokens, self.feature_dim):
            raise ValueError(
                "residual must be [B,N,feature_dim], got "
                f"{tuple(residual.shape)} for B={batch}, N={tokens}, F={self.feature_dim}"
            )
        if staleness_prior.shape != (batch, tokens):
            raise ValueError(f"staleness_prior must be [B,N], got {tuple(staleness_prior.shape)}")
        q = _token_scalar(q_obs, batch=batch, tokens=tokens, name="q_obs")
        _validate_finite_range(q, name="q_obs")
        if reveal is None:
            reveal_tokens = torch.ones_like(q)
        else:
            reveal_tokens = _token_scalar(
                reveal.to(device=state_prior.device, dtype=state_prior.dtype),
                batch=batch,
                tokens=tokens,
                name="reveal",
            )
            _validate_finite_range(reveal_tokens, name="reveal")
        effective_q = q * reveal_tokens
        clean_residual = torch.nan_to_num(residual, nan=0.0, posinf=0.0, neginf=0.0)
        clean_staleness = torch.nan_to_num(staleness_prior, nan=0.0, posinf=0.0, neginf=0.0)
        features = torch.cat(
            [
                self.state_norm(state_prior),
                clean_residual,
                effective_q.unsqueeze(-1),
                clean_staleness.unsqueeze(-1),
            ],
            dim=-1,
        )
        delta = self.update(features)
        candidate = state_prior + effective_q.unsqueeze(-1) * delta
        posterior = torch.where(effective_q.unsqueeze(-1) > 0, candidate, state_prior)
        return {
            "state": posterior,
            "gate": torch.ones_like(effective_q).unsqueeze(-1),
            "delta": delta,
            "effective_q": effective_q,
        }


class ObservationCorrectionRollout(nn.Module):
    """Predict then optionally correct a sequence of belief states.

    The transition callback receives ``(state, step_index)`` and returns the
    next prior state.  ``prior_feature_fn`` maps that prior state to the
    observation feature grid.  Feature/mask tensors for unrevealed steps may
    be arbitrary: the corresponding update is disabled by ``reveal_mask``.
    """

    def __init__(self, cell: ObservationCorrectionCell) -> None:
        super().__init__()
        self.cell = cell

    def forward(
        self,
        initial_state: torch.Tensor,
        transition_step: Callable[[torch.Tensor, int], torch.Tensor],
        prior_feature_fn: Callable[[torch.Tensor, int], torch.Tensor],
        observed_features: torch.Tensor,
        q_path: torch.Tensor,
        reveal_mask: torch.Tensor,
        *,
        elapsed_days: torch.Tensor | float = 1.0,
        initial_staleness: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        if initial_state.dim() != 3:
            raise ValueError(f"initial_state must be [B,N,D], got {tuple(initial_state.shape)}")
        batch, tokens, _ = initial_state.shape
        if observed_features.dim() != 4:
            raise ValueError(
                f"observed_features must be [B,T,N,F], got {tuple(observed_features.shape)}"
            )
        steps = observed_features.shape[1]
        if observed_features.shape[0] != batch or observed_features.shape[2] != tokens:
            raise ValueError(
                "observed_features must align with initial_state batch/tokens, got "
                f"{tuple(observed_features.shape)}"
            )
        if observed_features.shape[3] != self.cell.feature_dim:
            raise ValueError(
                f"observed_features feature dim must be {self.cell.feature_dim}, "
                f"got {observed_features.shape[3]}"
            )
        if q_path.shape != (batch, steps, tokens):
            raise ValueError(f"q_path must be {(batch, steps, tokens)}, got {tuple(q_path.shape)}")
        if reveal_mask.shape not in {(batch, steps), (batch, steps, tokens)}:
            raise ValueError(
                "reveal_mask must be [B,T] or [B,T,N], got "
                f"{tuple(reveal_mask.shape)}"
            )
        reveal_path = reveal_mask.to(device=initial_state.device, dtype=initial_state.dtype)
        _validate_finite_range(reveal_path, name="reveal_mask")
        if initial_staleness is None:
            age = torch.zeros(batch, tokens, device=initial_state.device, dtype=initial_state.dtype)
        else:
            if initial_staleness.shape != (batch, tokens):
                raise ValueError(
                    f"initial_staleness must be {(batch, tokens)}, got {tuple(initial_staleness.shape)}"
                )
            age = initial_staleness.to(device=initial_state.device, dtype=initial_state.dtype)

        state = initial_state
        prior_states: list[torch.Tensor] = []
        posterior_states: list[torch.Tensor] = []
        residuals: list[torch.Tensor] = []
        age_priors: list[torch.Tensor] = []
        age_posteriors: list[torch.Tensor] = []
        effective_qs: list[torch.Tensor] = []
        gates: list[torch.Tensor] = []

        for step in range(steps):
            prior = transition_step(state, step)
            if prior.shape != state.shape:
                raise ValueError(
                    f"transition_step changed state shape at step {step}: "
                    f"{tuple(state.shape)} -> {tuple(prior.shape)}"
                )
            prior_feature = prior_feature_fn(prior, step)
            expected = (batch, tokens, self.cell.feature_dim)
            if prior_feature.shape != expected:
                raise ValueError(
                    f"prior_feature_fn at step {step} must return {expected}, "
                    f"got {tuple(prior_feature.shape)}"
                )
            q_step = q_path[:, step]
            reveal_step = reveal_path[:, step]
            residual = observed_features[:, step] - prior_feature.detach()
            age_info = update_staleness(age, q_step, elapsed_days, reveal_step)
            correction = self.cell(
                prior,
                residual,
                q_step,
                age_info["age_prior"],
                reveal_step,
            )
            state = correction["state"]
            prior_states.append(prior)
            posterior_states.append(state)
            residuals.append(residual)
            age_priors.append(age_info["age_prior"])
            age_posteriors.append(age_info["age_posterior"])
            effective_qs.append(correction["effective_q"])
            gates.append(correction["gate"])
            age = age_info["age_posterior"]

        return {
            "prior_states": torch.stack(prior_states, dim=1),
            "posterior_states": torch.stack(posterior_states, dim=1),
            "final_state": state,
            "residuals": torch.stack(residuals, dim=1),
            "age_priors": torch.stack(age_priors, dim=1),
            "age_posteriors": torch.stack(age_posteriors, dim=1),
            "effective_q": torch.stack(effective_qs, dim=1),
            "gate": torch.stack(gates, dim=1),
        }
