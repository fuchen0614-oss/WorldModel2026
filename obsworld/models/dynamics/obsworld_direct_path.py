"""Formal matched Direct24 model for the Stage2-v2 path contract."""

from __future__ import annotations

from typing import Iterable, Optional

import torch
import torch.nn as nn

from data.stage2_contract import assert_model_batch_has_no_evaluation_fields, validate_stage2_v2_batch

from .controlled_transition import ControlledTransition
from .obsworld_core import ObsWorldV2Core


class ObsWorldDirectPathModel(nn.Module):
    """Predict selected endpoints directly from the same context state ``s0``.

    This is intentionally *not* a recursive model.  For horizon ``j`` it calls
    the shared transition exactly once with the prefix ``D_fut[:j+1]``.  It is
    therefore the fair control for a rollout model that uses the same raw
    24-D path, encoder, decoder, Geo tokens, and transition parameter budget.
    """

    forecast_mode = "direct_path_24d"

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
    ) -> dict[str, torch.Tensor]:
        """Return endpoint states/pixels for zero-based future step indices.

        ``selected_steps=None`` decodes all 20 future timestamps for formal
        evaluation.  Training can request a sorted subset to save decoder
        memory; the state transition for every selected endpoint remains a
        direct one-shot prefix transition.
        """

        assert_model_batch_has_no_evaluation_fields(batch)
        validate_stage2_v2_batch(
            batch, require_targets=False,
            expected_driver_dim=getattr(
                getattr(self.transition, "interval_driver_encoder", None),
                "input_dim",
                None,
            ),
        )
        requested = normalize_selected_steps(
            selected_steps,
            total_steps=self.target_steps,
            device=batch["D_path"].device,
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
        state0 = initialized["state"]
        geo_tokens = self.core.encode_geo(
            batch["G"],
            batch.get("G_mask"),
            expected_tokens=state0.shape[1],
        )
        future_d = d_path[:, self.future_start_index:end]
        future_mask = mask_path[:, self.future_start_index:end]
        future_calendar = calendar_path[:, self.future_start_index:end]
        future_dt = delta_path[:, self.future_start_index:end]

        endpoint_states = []
        driver_summaries = []
        observed_fraction = []
        state_delta_norms = []
        for step in requested.tolist():
            result = self.transition(
                state0,
                future_d[:, : step + 1],
                future_mask[:, : step + 1],
                future_calendar[:, : step + 1],
                future_dt[:, : step + 1],
                geo_tokens,
                return_diagnostics=True,
            )
            state = result["state"]
            endpoint_states.append(state)
            driver_summaries.append(result["driver_summary"])
            # Prefix lengths differ across endpoints, so keep a scalar
            # availability diagnostic per endpoint rather than attempting to
            # stack ragged [B,L] paths.
            observed_fraction.append(
                result["driver_observed_fraction"].mean(dim=1)
            )
            state_delta_norms.append((state - state0).norm(dim=-1).mean(dim=-1))

        states = torch.stack(endpoint_states, dim=1)
        last_valid_rgbn = initialized.get("last_valid_rgbn")
        decoded = self.core.decode_states(states, baseline=last_valid_rgbn)
        output = {
            "pred": decoded["mean"],
            "z_pred": states,
            "z_context": state0,
            "state_valid_mask": initialized["state_valid_mask"],
            "context_token_coverage": initialized["context_token_coverage"],
            "geo_tokens": geo_tokens,
            "step_indices": requested,
            "driver_summary": torch.stack(driver_summaries, dim=1),
            "driver_observed_fraction": torch.stack(observed_fraction, dim=1),
            "state_delta_norm": torch.stack(state_delta_norms, dim=1),
            **({"pred_logvar": decoded["logvar"]} if "logvar" in decoded else {}),
        }
        if getattr(self.core, "ndvi_head", None) is not None and last_valid_rgbn is not None:
            # History-only last-valid NDVI baseline (EarthNet bands: red=2, nir=3).
            red = last_valid_rgbn[:, 2]
            nir = last_valid_rgbn[:, 3]
            baseline_ndvi = ((nir - red) / (nir + red + 1e-6)).clamp(-1.0, 1.0)
            output["ndvi_pred"] = self.core.decode_ndvi(states, baseline_ndvi)
        return output


def normalize_selected_steps(
    selected_steps: Optional[Iterable[int] | torch.Tensor],
    *,
    total_steps: int,
    device: torch.device,
) -> torch.Tensor:
    if selected_steps is None:
        return torch.arange(total_steps, device=device, dtype=torch.long)
    steps = torch.as_tensor(selected_steps, dtype=torch.long, device=device).flatten()
    if steps.numel() == 0:
        raise ValueError("selected_steps must contain at least one future endpoint")
    if torch.any(steps < 0) or torch.any(steps >= total_steps):
        raise ValueError(
            f"selected_steps must lie in [0,{total_steps - 1}], got {steps.tolist()}"
        )
    if torch.unique(steps).numel() != steps.numel():
        raise ValueError("selected_steps must not contain duplicates")
    # Sorted outputs make it impossible for a caller to accidentally align a
    # decoded step with the wrong target frame.
    return steps.sort().values
