"""Open-loop rollout with an explicit observation-correction update.

The wrapper keeps the causal order visible in code:

1. transition the previous posterior state to a prior;
2. decode/evaluate that prior as the forecast for the current step;
3. if a reveal is available, encode the revealed observation and update the
   posterior state used by the *next* transition.

Future target tensors therefore cross the model boundary only through the
explicit ``correction_inputs`` argument.  The ordinary Stage2 input view does
not contain them, so Direct/Rollout models remain unchanged.
"""

from __future__ import annotations

from typing import Iterable, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from data.stage2_contract import (
    assert_model_batch_has_no_evaluation_fields,
    validate_stage2_v2_batch,
)

from .obsworld_core import ObsWorldV2Core, pixel_mask_to_token_coverage
from .obsworld_direct_path import normalize_selected_steps
from .observation_correction import (
    ObservationCorrectionCell,
    update_staleness,
    VanillaFilterCell,
)


class ObsWorldCorrectionModel(nn.Module):
    """Causal rollout plus the visibility-weighted U/Filter/Restart update."""

    def __init__(
        self,
        core: ObsWorldV2Core,
        transition: nn.Module,
        *,
        forecast_mode: str,
        future_start_index: int = 10,
        target_steps: int = 20,
        strategy: str = "u",
        correction_hidden_dim: int = 128,
        staleness_scale_days: float = 100.0,
    ) -> None:
        super().__init__()
        if future_start_index < 0 or target_steps <= 0:
            raise ValueError("future_start_index must be non-negative and target_steps positive")
        strategy = str(strategy).strip().lower()
        if strategy not in {"u", "no_update", "restart", "vanilla_filter"}:
            raise ValueError(
                "Observation correction strategy must be one of "
                "u/no_update/restart/vanilla_filter, got "
                f"{strategy!r}"
            )
        if staleness_scale_days <= 0:
            raise ValueError("staleness_scale_days must be positive")
        self.core = core
        self.transition = transition
        self.forecast_mode = str(forecast_mode)
        self.future_start_index = int(future_start_index)
        self.target_steps = int(target_steps)
        self.correction_strategy = strategy
        self.staleness_scale_days = float(staleness_scale_days)
        state_dim = int(core.state_projector.state_dim)
        self.correction_cell = (
            ObservationCorrectionCell(
                state_dim=state_dim,
                feature_dim=state_dim,
                hidden_dim=int(correction_hidden_dim),
            )
            if strategy == "u"
            else None
        )
        self.vanilla_filter_cell = (
            VanillaFilterCell(
                state_dim=state_dim,
                feature_dim=state_dim,
                hidden_dim=int(correction_hidden_dim),
            )
            if strategy == "vanilla_filter"
            else None
        )

    def forward(
        self,
        batch: dict[str, torch.Tensor],
        *,
        selected_steps: Optional[Iterable[int] | torch.Tensor] = None,
        max_rollout_steps: Optional[int] = None,
        correction_inputs: Optional[dict[str, torch.Tensor]] = None,
    ) -> dict[str, torch.Tensor]:
        assert_model_batch_has_no_evaluation_fields(batch)
        validate_stage2_v2_batch(
            batch,
            require_targets=False,
            expected_driver_dim=getattr(
                getattr(self.transition, "interval_driver_encoder", None),
                "input_dim",
                None,
            ),
        )
        rollout_steps = self._resolve_rollout_steps(max_rollout_steps)
        requested = normalize_selected_steps(
            selected_steps,
            total_steps=(rollout_steps if selected_steps is None else self.target_steps),
            device=batch["D_path"].device,
        )
        if int(requested.max()) >= rollout_steps:
            raise ValueError(
                "selected_steps request a future state outside the active rollout "
                f"curriculum: max requested={int(requested.max())}, "
                f"rollout_steps={rollout_steps}"
            )

        observations, observation_mask, reveal_mask = self._prepare_correction_inputs(
            correction_inputs,
            batch_size=batch["D_path"].shape[0],
            rollout_steps=rollout_steps,
            device=batch["D_path"].device,
        )
        initialized = self.core.initialize_state(batch)
        state = initialized["state"]
        state0 = state
        geo_tokens = self.core.encode_geo(
            batch["G"],
            batch.get("G_mask"),
            expected_tokens=state.shape[1],
        )

        d_path = batch["D_path"]
        mask_path = batch["D_mask"]
        calendar_path = batch["C_path"]
        delta_path = batch["delta_t_path"]
        end = self.future_start_index + self.target_steps
        if d_path.shape[1] < end:
            raise ValueError(
                "D_path is too short for formal future offset/length: "
                f"need {end}, got {d_path.shape[1]}"
            )
        future_d = d_path[:, self.future_start_index:end]
        future_mask = mask_path[:, self.future_start_index:end]
        future_calendar = calendar_path[:, self.future_start_index:end]
        future_dt = delta_path[:, self.future_start_index:end]

        prior_states: list[torch.Tensor] = []
        posterior_states: list[torch.Tensor] = []
        driver_summaries = []
        observed_fractions = []
        state_delta_norms = []
        correction_gates = []
        effective_qs = []
        age_priors = []
        age_posteriors = []
        age = torch.zeros(
            state.shape[0], state.shape[1], device=state.device, dtype=state.dtype
        )

        for step in range(rollout_steps):
            result = self.transition(
                state,
                future_d[:, step : step + 1],
                future_mask[:, step : step + 1],
                future_calendar[:, step : step + 1],
                future_dt[:, step : step + 1],
                geo_tokens,
                return_diagnostics=True,
            )
            prior = result["state"]
            prior_states.append(prior)
            driver_summaries.append(result["driver_summary"])
            observed_fractions.append(result["driver_observed_fraction"].mean(dim=1))
            state_delta_norms.append((prior - state).norm(dim=-1).mean(dim=-1))

            q_step = torch.zeros(
                state.shape[0], state.shape[1], device=state.device, dtype=state.dtype
            )
            reveal_step = torch.zeros_like(q_step)
            residual = torch.zeros(
                state.shape[0], state.shape[1], state.shape[2],
                device=state.device, dtype=state.dtype,
            )
            observed_state = torch.zeros_like(prior)
            if observations is not None and observation_mask is not None and reveal_mask is not None:
                reveal_scalar = reveal_mask[:, step]
                if bool(reveal_scalar.gt(0).any()):
                    obs_step = observations[:, step]
                    mask_step = observation_mask[:, step]
                    obs_step, mask_step = self._resize_to_encoder(obs_step, mask_step)
                    observed_state = self.core.encode_observations(
                        obs_step.unsqueeze(1), mask_step.unsqueeze(1)
                    )[:, 0]
                    prior_image = self.core.decode_states(prior)["mean"]
                    prior_image, _ = self._resize_to_encoder(
                        prior_image, torch.ones(
                            prior_image.shape[0], prior_image.shape[-2], prior_image.shape[-1],
                            device=prior_image.device, dtype=prior_image.dtype,
                        )
                    )
                    predicted_state = self.core.encode_observations(
                        prior_image.unsqueeze(1), mask_step.unsqueeze(1)
                    )[:, 0]
                    residual = observed_state - predicted_state.detach()
                    q_step = pixel_mask_to_token_coverage(
                        mask_step.unsqueeze(1), state.shape[1]
                    )[:, 0].to(dtype=state.dtype)
                    reveal_step = reveal_scalar[:, None].expand_as(q_step).to(dtype=state.dtype)

            age_info = update_staleness(
                age,
                q_step if self.correction_strategy != "no_update" else torch.zeros_like(q_step),
                future_dt[:, step],
                reveal_step,
            )
            if self.correction_strategy == "u":
                correction = self.correction_cell(
                    prior,
                    residual,
                    q_step,
                    age_info["age_prior"] / self.staleness_scale_days,
                    reveal_step,
                )
                posterior = correction["state"]
                gate = correction["gate"]
                effective_q = correction["effective_q"]
            elif self.correction_strategy == "vanilla_filter":
                correction = self.vanilla_filter_cell(
                    prior,
                    residual,
                    q_step,
                    age_info["age_prior"] / self.staleness_scale_days,
                    reveal_step,
                )
                posterior = correction["state"]
                gate = correction["gate"]
                effective_q = correction["effective_q"]
            elif self.correction_strategy == "restart":
                # A transparent capacity-free baseline: replace visible token
                # states by the encoded observation, with fractional support
                # blending for partially clear tokens.
                effective_q = q_step * reveal_step
                posterior = prior + effective_q.unsqueeze(-1) * (observed_state - prior)
                gate = torch.ones_like(effective_q).unsqueeze(-1)
            else:  # no_update
                effective_q = torch.zeros_like(q_step)
                posterior = prior
                gate = torch.zeros_like(effective_q).unsqueeze(-1)

            state = posterior
            age = age_info["age_posterior"]
            posterior_states.append(posterior)
            correction_gates.append(gate)
            effective_qs.append(effective_q)
            age_priors.append(age_info["age_prior"])
            age_posteriors.append(age_info["age_posterior"])

        prior_rollout = torch.stack(prior_states, dim=1)
        posterior_rollout = torch.stack(posterior_states, dim=1)
        z_pred = prior_rollout.index_select(1, requested)
        decoded = self.core.decode_states(z_pred)
        return {
            "pred": decoded["mean"],
            "z_pred": z_pred,
            "z_rollout": prior_rollout,
            "z_posterior": posterior_rollout,
            "z_context": state0,
            "state_valid_mask": initialized["state_valid_mask"],
            "context_token_coverage": initialized["context_token_coverage"],
            "geo_tokens": geo_tokens,
            "step_indices": requested,
            "rollout_steps": torch.tensor(rollout_steps, dtype=torch.long, device=state0.device),
            "driver_summary": torch.stack(driver_summaries, dim=1),
            "driver_observed_fraction": torch.stack(observed_fractions, dim=1),
            "state_delta_norm": torch.stack(state_delta_norms, dim=1),
            "correction_gate": torch.stack(correction_gates, dim=1),
            "correction_effective_q": torch.stack(effective_qs, dim=1),
            "staleness_prior": torch.stack(age_priors, dim=1),
            "staleness_posterior": torch.stack(age_posteriors, dim=1),
            **({"pred_logvar": decoded["logvar"]} if "logvar" in decoded else {}),
        }

    def _prepare_correction_inputs(
        self,
        correction_inputs: Optional[dict[str, torch.Tensor]],
        *,
        batch_size: int,
        rollout_steps: int,
        device: torch.device,
    ) -> tuple[Optional[torch.Tensor], Optional[torch.Tensor], Optional[torch.Tensor]]:
        if correction_inputs is None:
            return None, None, None
        required = ("observations", "observation_mask", "reveal_mask")
        missing = [name for name in required if name not in correction_inputs]
        if missing:
            raise KeyError(f"correction_inputs is missing fields: {missing}")
        observations = correction_inputs["observations"]
        observation_mask = correction_inputs["observation_mask"]
        reveal_mask = correction_inputs["reveal_mask"]
        if observations.dim() != 5:
            raise ValueError(
                "correction_inputs.observations must be [B,T,C,H,W], got "
                f"{tuple(observations.shape)}"
            )
        if observations.shape[0] != batch_size or observations.shape[1] < rollout_steps:
            raise ValueError(
                "correction observations must cover the active rollout: "
                f"got {tuple(observations.shape)}, B={batch_size}, T>={rollout_steps}"
            )
        if observation_mask.shape[:2] != observations.shape[:2] or observation_mask.dim() != 4:
            raise ValueError(
                "correction_inputs.observation_mask must be [B,T,H,W] aligned with observations"
            )
        if reveal_mask.shape not in {(batch_size, observations.shape[1]), (batch_size, observations.shape[1], 1)}:
            raise ValueError(
                "correction_inputs.reveal_mask must be [B,T] or [B,T,1], got "
                f"{tuple(reveal_mask.shape)}"
            )
        reveal_mask = reveal_mask.reshape(batch_size, -1)
        if not torch.isfinite(reveal_mask).all() or (reveal_mask < 0).any() or (reveal_mask > 1).any():
            raise ValueError("correction_inputs.reveal_mask must lie in [0,1]")
        return (
            observations[:, :rollout_steps].to(device=device),
            observation_mask[:, :rollout_steps].to(device=device),
            reveal_mask[:, :rollout_steps].to(device=device),
        )

    def _resize_to_encoder(
        self,
        observations: torch.Tensor,
        mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        encoder_size = getattr(self.core.encoder, "img_size", None)
        if encoder_size is None:
            return observations, mask
        size = int(encoder_size)
        if observations.shape[-2:] == (size, size):
            return observations, mask
        observations = F.interpolate(
            observations,
            size=(size, size),
            mode="bilinear",
            align_corners=False,
        )
        mask = F.interpolate(
            mask.unsqueeze(1).float(),
            size=(size, size),
            mode="nearest",
        ).squeeze(1)
        return observations, mask

    def _resolve_rollout_steps(self, requested: Optional[int]) -> int:
        if requested is None:
            return self.target_steps
        steps = int(requested)
        if not 1 <= steps <= self.target_steps:
            raise ValueError(
                "max_rollout_steps must lie in [1,target_steps], got "
                f"{steps} for target_steps={self.target_steps}"
            )
        return steps
