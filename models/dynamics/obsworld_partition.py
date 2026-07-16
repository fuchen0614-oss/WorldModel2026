"""Partition-consistent open-loop ObsWorld wrapper.

This thin wrapper deliberately reuses :class:`ObsWorldRolloutModel` for the
main 5-day trajectory.  Its only extra work is to evaluate the same shared
controlled transition over a legal two-token interval and over its exact
one-token-plus-one-token decomposition.
"""

from __future__ import annotations

from typing import Iterable, Optional

import torch

from data.stage2_contract import assert_model_batch_has_no_evaluation_fields, validate_stage2_v2_batch

from .obsworld_rollout import ObsWorldRolloutModel


class ObsWorldPartitionModel(ObsWorldRolloutModel):
    """Open-loop rollout plus a control-aware 10-day partition branch.

    The ordinary output remains a normal recursive 20×5-day forecast.  When
    ``partition_start`` is supplied during training, the returned
    ``partition`` mapping contains two endpoint predictions for the same
    target: one direct 10-day transition and one composed 5-day + 5-day
    transition.  No target pixels or target masks cross this model boundary.
    """

    forecast_mode = "obsworld_partition_24d"

    def forward(
        self,
        batch: dict[str, torch.Tensor],
        *,
        selected_steps: Optional[Iterable[int] | torch.Tensor] = None,
        max_rollout_steps: Optional[int] = None,
        partition_start: Optional[int | torch.Tensor] = None,
        detach_partition_start: bool = True,
    ) -> dict[str, torch.Tensor | dict[str, torch.Tensor]]:
        output = super().forward(
            batch,
            selected_steps=selected_steps,
            max_rollout_steps=max_rollout_steps,
        )
        if partition_start is not None:
            output["partition"] = self._two_step_partition(
                batch,
                output,
                partition_start=partition_start,
                detach_partition_start=detach_partition_start,
            )
        return output

    def _two_step_partition(
        self,
        batch: dict[str, torch.Tensor],
        rollout_output: dict[str, torch.Tensor],
        *,
        partition_start: int | torch.Tensor,
        detach_partition_start: bool,
    ) -> dict[str, torch.Tensor]:
        """Return direct and composed endpoints for one legal 5+5 split."""

        assert_model_batch_has_no_evaluation_fields(batch)
        validate_stage2_v2_batch(batch, require_targets=False)
        start = _normalize_partition_start(partition_start)
        z_rollout = rollout_output["z_rollout"]
        active_steps = int(z_rollout.shape[1])
        if start < 0 or start + 2 > active_steps:
            raise ValueError(
                "partition_start must leave two active five-day intervals: "
                f"start={start}, active_rollout_steps={active_steps}"
            )

        z_start = (
            rollout_output["z_context"]
            if start == 0
            else z_rollout[:, start - 1]
        )
        # The main rollout remains end-to-end.  Detaching only this auxiliary
        # branch prevents its extra transitions from backpropagating through
        # earlier rollout states and changing the memory/training budget.
        if detach_partition_start:
            z_start = z_start.detach()

        first = self.future_start_index + start
        second = first + 1
        d_path = batch["D_path"]
        d_mask = batch["D_mask"]
        calendar = batch["C_path"]
        delta_t = batch["delta_t_path"]
        geo_tokens = rollout_output["geo_tokens"]

        # Both branches use byte-for-byte identical two-token control paths:
        # [first:second+1] == [first:first+1] followed by [second:second+1].
        direct = self.transition(
            z_start,
            d_path[:, first : second + 1],
            d_mask[:, first : second + 1],
            calendar[:, first : second + 1],
            delta_t[:, first : second + 1],
            geo_tokens,
            return_diagnostics=True,
        )
        mid = self.transition(
            z_start,
            d_path[:, first : first + 1],
            d_mask[:, first : first + 1],
            calendar[:, first : first + 1],
            delta_t[:, first : first + 1],
            geo_tokens,
            return_diagnostics=True,
        )
        composed = self.transition(
            mid["state"],
            d_path[:, second : second + 1],
            d_mask[:, second : second + 1],
            calendar[:, second : second + 1],
            delta_t[:, second : second + 1],
            geo_tokens,
            return_diagnostics=True,
        )

        decoded = self.core.decode_states(
            torch.stack((direct["state"], composed["state"]), dim=1)
        )
        partition: dict[str, torch.Tensor] = {
            "start_index": torch.tensor(start, device=z_start.device, dtype=torch.long),
            "endpoint_index": torch.tensor(start + 1, device=z_start.device, dtype=torch.long),
            "z_start": z_start,
            "z_direct": direct["state"],
            "z_mid": mid["state"],
            "z_composed": composed["state"],
            "pred_direct": decoded["mean"][:, 0],
            "pred_composed": decoded["mean"][:, 1],
            "state_valid_mask": rollout_output["state_valid_mask"],
            "direct_elapsed_days": direct["elapsed_days"],
            "compose_elapsed_days": torch.stack(
                (mid["elapsed_days"], composed["elapsed_days"]), dim=1
            ),
            "direct_driver_observed_fraction": direct[
                "driver_observed_fraction"
            ].mean(dim=1),
            "compose_driver_observed_fraction": torch.stack(
                (
                    mid["driver_observed_fraction"].mean(dim=1),
                    composed["driver_observed_fraction"].mean(dim=1),
                ),
                dim=1,
            ),
        }
        if "logvar" in decoded:
            partition["pred_direct_logvar"] = decoded["logvar"][:, 0]
            partition["pred_composed_logvar"] = decoded["logvar"][:, 1]
        return partition


def _normalize_partition_start(value: int | torch.Tensor) -> int:
    if isinstance(value, torch.Tensor):
        if value.numel() != 1:
            raise ValueError(
                "partition_start tensor must contain one shared minibatch anchor, "
                f"got shape {tuple(value.shape)}"
            )
        return int(value.detach().cpu().item())
    if isinstance(value, bool):
        raise TypeError("partition_start must be an integer, not bool")
    return int(value)
