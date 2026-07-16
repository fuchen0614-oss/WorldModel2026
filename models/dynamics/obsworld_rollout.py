"""Open-loop five-day rollout model for the formal Stage2-v2 contract."""

from __future__ import annotations

from typing import Iterable, Optional

import torch
import torch.nn as nn

from data.stage2_contract import assert_model_batch_has_no_evaluation_fields, validate_stage2_v2_batch

from .controlled_transition import ControlledTransition
from .obsworld_core import ObsWorldV2Core
from .obsworld_direct_path import normalize_selected_steps


class ObsWorldRolloutModel(nn.Module):
    """Predict future states by repeatedly applying one shared transition.

    No teacher forcing is present in this wrapper: after the context-only
    initializer produces ``s0``, each call receives the preceding *predicted*
    state plus the next five-day driver token.  ``z_rollout`` retains all
    states traversed by the current curriculum length; ``z_pred`` contains
    just the endpoints selected for RGBN/NDVI supervision.
    """

    forecast_mode = "rollout_t5_24d"

    def __init__(
        self,
        core: ObsWorldV2Core,
        transition: ControlledTransition,
        *,
        future_start_index: int = 10,
        target_steps: int = 20,
    ):
        super().__init__()
        if future_start_index < 0 or target_steps <= 0:
            raise ValueError("future_start_index must be non-negative and target_steps positive")
        self.core = core
        self.transition = transition
        self.future_start_index = int(future_start_index)
        self.target_steps = int(target_steps)

    def forward(
        self,
        batch: dict[str, torch.Tensor],
        *,
        selected_steps: Optional[Iterable[int] | torch.Tensor] = None,
        max_rollout_steps: Optional[int] = None,
    ) -> dict[str, torch.Tensor]:
        """Run an open-loop rollout and decode selected endpoint states.

        Args:
            selected_steps: zero-based future endpoints to decode.  They are
                always indexes in the full 20-step future, even when the
                training curriculum currently limits the rollout length.
            max_rollout_steps: current curriculum length in ``[1,20]``.
                Omitted means the formal full 20-step trajectory.
        """

        assert_model_batch_has_no_evaluation_fields(batch)
        validate_stage2_v2_batch(batch, require_targets=False)
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

        initialized = self.core.initialize_state(batch)
        state = initialized["state"]
        state0 = state
        geo_tokens = self.core.encode_geo(
            batch["G"],
            batch.get("G_mask"),
            expected_tokens=state.shape[1],
        )
        future_d = d_path[:, self.future_start_index:end]
        future_mask = mask_path[:, self.future_start_index:end]
        future_calendar = calendar_path[:, self.future_start_index:end]
        future_dt = delta_path[:, self.future_start_index:end]

        states = []
        driver_summaries = []
        observed_fractions = []
        state_delta_norms = []
        for step in range(rollout_steps):
            # Crucially, `state` is reassigned to the previous prediction;
            # no x_target-derived latent is ever available in this wrapper.
            result = self.transition(
                state,
                future_d[:, step : step + 1],
                future_mask[:, step : step + 1],
                future_calendar[:, step : step + 1],
                future_dt[:, step : step + 1],
                geo_tokens,
                return_diagnostics=True,
            )
            next_state = result["state"]
            states.append(next_state)
            driver_summaries.append(result["driver_summary"])
            observed_fractions.append(result["driver_observed_fraction"].mean(dim=1))
            state_delta_norms.append((next_state - state).norm(dim=-1).mean(dim=-1))
            state = next_state

        z_rollout = torch.stack(states, dim=1)
        z_pred = z_rollout.index_select(1, requested)
        decoded = self.core.decode_states(z_pred)
        return {
            "pred": decoded["mean"],
            "z_pred": z_pred,
            "z_rollout": z_rollout,
            "z_context": state0,
            "state_valid_mask": initialized["state_valid_mask"],
            "context_token_coverage": initialized["context_token_coverage"],
            "geo_tokens": geo_tokens,
            "step_indices": requested,
            "rollout_steps": torch.tensor(
                rollout_steps,
                dtype=torch.long,
                device=state0.device,
            ),
            "driver_summary": torch.stack(driver_summaries, dim=1),
            "driver_observed_fraction": torch.stack(observed_fractions, dim=1),
            "state_delta_norm": torch.stack(state_delta_norms, dim=1),
            **({"pred_logvar": decoded["logvar"]} if "logvar" in decoded else {}),
        }

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
