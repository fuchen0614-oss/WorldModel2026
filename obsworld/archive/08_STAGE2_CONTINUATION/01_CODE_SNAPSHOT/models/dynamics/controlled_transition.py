"""One shared controlled state transition for Direct24 and rollout models."""

from __future__ import annotations

import torch
import torch.nn as nn

from .interval_driver_encoder import IntervalDriverEncoder


class ControlledTransition(nn.Module):
    """Apply a variable-length D/C/delta-t segment to a latent state.

    The wrapped ``StateDynamicsModule`` remains the actual residual dynamics
    network.  This wrapper owns the only legal conversion from a variable
    length 24-D driver path to its transition condition, which prevents Direct
    and rollout variants from quietly using different weather summaries.
    """

    def __init__(
        self,
        interval_driver_encoder: IntervalDriverEncoder,
        horizon_encoder: nn.Module,
        state_dynamics: nn.Module,
        *,
        use_D: bool = True,
        use_G: bool = True,
        use_h: bool = True,
        residual_scale_init: float = 1.0,
    ):
        super().__init__()
        if not hasattr(interval_driver_encoder, "out_dim"):
            raise TypeError("interval_driver_encoder must expose out_dim")
        if not hasattr(horizon_encoder, "out_dim"):
            raise TypeError("horizon_encoder must expose out_dim")
        for name in ("latent_dim", "driver_dim", "geo_dim", "time_dim"):
            if not hasattr(state_dynamics, name):
                raise TypeError(f"state_dynamics must expose {name}")
        if int(interval_driver_encoder.out_dim) != int(state_dynamics.driver_dim):
            raise ValueError(
                "Interval driver summary dimension does not match dynamics.driver_dim: "
                f"{interval_driver_encoder.out_dim} vs {state_dynamics.driver_dim}"
            )
        if int(horizon_encoder.out_dim) != int(state_dynamics.time_dim):
            raise ValueError(
                "Horizon encoder dimension does not match dynamics.time_dim: "
                f"{horizon_encoder.out_dim} vs {state_dynamics.time_dim}"
            )
        if residual_scale_init < 0:
            raise ValueError("residual_scale_init must be non-negative")

        self.interval_driver_encoder = interval_driver_encoder
        self.horizon_encoder = horizon_encoder
        self.state_dynamics = state_dynamics
        self.use_D = bool(use_D)
        self.use_G = bool(use_G)
        self.use_h = bool(use_h)
        # A single LayerScale-style factor gives long rollouts a stable
        # residual knob without changing latent width or adding per-step heads.
        self.residual_scale = nn.Parameter(torch.tensor(float(residual_scale_init)))

    def forward(
        self,
        state: torch.Tensor,
        d_segment: torch.Tensor,
        d_mask_segment: torch.Tensor,
        calendar_segment: torch.Tensor,
        delta_t_segment: torch.Tensor,
        geo_tokens: torch.Tensor,
        *,
        return_diagnostics: bool = False,
    ) -> torch.Tensor | dict[str, torch.Tensor]:
        """Return the next state after one segment, without target access.

        ``d_segment`` can be a single five-day token (rollout) or a longer
        prefix (Direct24/partition direct branch).  No future RGBN target or
        future target mask appears in this interface.
        """

        if state.dim() != 3:
            raise ValueError(f"state must be [B,N,D], got {tuple(state.shape)}")
        batch, tokens, state_dim = state.shape
        if state_dim != int(self.state_dynamics.latent_dim):
            raise ValueError(
                f"state dim must be {self.state_dynamics.latent_dim}, got {state_dim}"
            )
        if geo_tokens.shape != (batch, tokens, int(self.state_dynamics.geo_dim)):
            raise ValueError(
                "geo_tokens must align with state as [B,N,Dg], got "
                f"{tuple(geo_tokens.shape)} for state={tuple(state.shape)}"
            )

        if self.use_D:
            used_d = d_segment
            used_mask = d_mask_segment
        else:
            # Keep C/delta-t below.  Clearing only D values/missingness is the
            # correct no-D intervention, not an accidental no-time model.
            used_d = torch.zeros_like(d_segment)
            used_mask = torch.zeros_like(d_mask_segment)
        driver = self.interval_driver_encoder(
            used_d,
            used_mask,
            calendar_segment,
            delta_t_segment,
        )
        elapsed_days = delta_t_segment.sum(dim=1)
        time_embedding = self.horizon_encoder(elapsed_days)
        if not self.use_h:
            time_embedding = torch.zeros_like(time_embedding)
        used_geo = geo_tokens if self.use_G else torch.zeros_like(geo_tokens)

        proposed = self.state_dynamics(
            state,
            driver=driver["summary"],
            geo=used_geo,
            time_delta=time_embedding,
        )
        next_state = state + self.residual_scale * (proposed - state)
        if not return_diagnostics:
            return next_state
        return {
            "state": next_state,
            "proposed_state": proposed,
            "driver_summary": driver["summary"],
            "driver_tokens": driver["tokens"],
            "driver_segment_valid": driver["segment_valid"],
            "driver_observed_fraction": driver["observed_fraction"],
            "driver_pool_weights": driver["pool_weights"],
            "elapsed_days": elapsed_days,
            "time_embedding": time_embedding,
        }

    def get_config(self) -> dict:
        return {
            "use_D": self.use_D,
            "use_G": self.use_G,
            "use_h": self.use_h,
            "residual_scale_init": float(self.residual_scale.detach().cpu()),
            "driver": self.interval_driver_encoder.get_config(),
        }
