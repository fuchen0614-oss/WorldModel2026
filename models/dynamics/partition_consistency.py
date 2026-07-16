"""Control-aware temporal partition consistency for ObsWorld Stage2-v2.

The formal first variant compares one ten-day transition against two
consecutive five-day transitions over *exactly the same* D/C/delta-t path.
It is deliberately not called a generic semigroup loss: weather and calendar
controls vary through time, so only the supplied control path is composable.
"""

from __future__ import annotations

from typing import Dict, Mapping, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from data.earthnet_fields import compute_ndvi


def sample_two_step_partition_start(
    rollout_steps: int,
    *,
    device: torch.device,
) -> int:
    """Uniformly sample a legal 10-day-vs-5+5 anchor for one minibatch.

    A start ``j`` uses rollout state ``s_j`` and ends at future target
    ``j + 1``.  Therefore a current curriculum of length ``L`` has exactly
    ``L - 1`` legal anchors.  The global torch RNG is checkpointed by the
    trainer, making this stochastic choice recoverable on resume.
    """

    if rollout_steps < 2:
        raise ValueError(
            "Two-step partition consistency requires at least two active "
            f"rollout steps, got {rollout_steps}"
        )
    return int(torch.randint(rollout_steps - 1, (1,), device=device).item())


class PartitionConsistencyLoss(nn.Module):
    """Losses tying direct and composed controlled transitions together.

    There are intentionally no learnable layers here.  In particular,
    ``LayerNorm(..., elementwise_affine=False)`` prevents a trainable
    projection from making the two state paths artificially agree while the
    underlying dynamics remains inconsistent.
    """

    def __init__(
        self,
        *,
        red_index: int,
        nir_index: int,
        w_state: float = 0.10,
        w_observation: float = 0.10,
        w_ndvi: float = 0.05,
        w_endpoint: float = 0.50,
        endpoint_ndvi_weight: float = 0.50,
    ):
        super().__init__()
        weights = {
            "state": w_state,
            "observation": w_observation,
            "ndvi": w_ndvi,
            "endpoint": w_endpoint,
            "endpoint_ndvi_weight": endpoint_ndvi_weight,
        }
        negative = [name for name, value in weights.items() if value < 0]
        if negative:
            raise ValueError(f"Partition loss weights must be non-negative: {negative}")
        self.red_index = int(red_index)
        self.nir_index = int(nir_index)
        self.w_state = float(w_state)
        self.w_observation = float(w_observation)
        self.w_ndvi = float(w_ndvi)
        self.w_endpoint = float(w_endpoint)
        self.endpoint_ndvi_weight = float(endpoint_ndvi_weight)

    @classmethod
    def from_config(
        cls,
        loss_config: Mapping[str, object],
        *,
        red_index: int,
        nir_index: int,
    ) -> "PartitionConsistencyLoss":
        raw = loss_config.get("partition", {})
        if raw is None:
            raw = {}
        if not isinstance(raw, Mapping):
            raise TypeError("loss.partition must be a mapping when present")
        return cls(
            red_index=red_index,
            nir_index=nir_index,
            w_state=float(raw.get("state", 0.10)),
            w_observation=float(raw.get("observation", 0.10)),
            w_ndvi=float(raw.get("ndvi", 0.05)),
            w_endpoint=float(raw.get("direct_endpoint", raw.get("endpoint", 0.50))),
            endpoint_ndvi_weight=float(raw.get("endpoint_ndvi_weight", 0.50)),
        )

    def forward(
        self,
        *,
        z_direct: torch.Tensor,
        z_composed: torch.Tensor,
        pred_direct: torch.Tensor,
        pred_composed: torch.Tensor,
        target: torch.Tensor,
        target_mask: Optional[torch.Tensor],
        state_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """Calculate fixed-projection state and observation-space losses.

        ``target`` and ``target_mask`` are supplied by the trainer *after* the
        model forward.  They never enter the state transition interface.
        Both partition branches receive the same terminal target; otherwise a
        low latent gap alone could be satisfied by a degenerate constant
        state.
        """

        _validate_state_pair(z_direct, z_composed, state_mask)
        _validate_observation_triplet(pred_direct, pred_composed, target, target_mask)

        direct_normalized = F.layer_norm(
            z_direct,
            normalized_shape=(z_direct.shape[-1],),
            weight=None,
            bias=None,
        )
        composed_normalized = F.layer_norm(
            z_composed,
            normalized_shape=(z_composed.shape[-1],),
            weight=None,
            bias=None,
        )
        # Symmetric stop-gradient: each path is optimized toward the other,
        # but neither path becomes a moving target in the same term.
        state_forward = _masked_mean(
            (direct_normalized - composed_normalized.detach()).pow(2).mean(dim=-1),
            state_mask,
        )
        state_reverse = _masked_mean(
            (direct_normalized.detach() - composed_normalized).pow(2).mean(dim=-1),
            state_mask,
        )
        state = 0.5 * (state_forward + state_reverse)

        observation = _masked_huber(pred_direct, pred_composed, target_mask)
        ndvi = _masked_l1(
            compute_ndvi(pred_direct, self.red_index, self.nir_index).clamp(-1.0, 1.0),
            compute_ndvi(pred_composed, self.red_index, self.nir_index).clamp(-1.0, 1.0),
            target_mask,
        )

        endpoint_direct_obs = _masked_huber(pred_direct, target, target_mask)
        endpoint_composed_obs = _masked_huber(pred_composed, target, target_mask)
        target_ndvi = compute_ndvi(target, self.red_index, self.nir_index).clamp(-1.0, 1.0)
        endpoint_direct_ndvi = _masked_l1(
            compute_ndvi(pred_direct, self.red_index, self.nir_index).clamp(-1.0, 1.0),
            target_ndvi,
            target_mask,
        )
        endpoint_composed_ndvi = _masked_l1(
            compute_ndvi(pred_composed, self.red_index, self.nir_index).clamp(-1.0, 1.0),
            target_ndvi,
            target_mask,
        )
        endpoint_direct = endpoint_direct_obs + self.endpoint_ndvi_weight * endpoint_direct_ndvi
        endpoint_composed = endpoint_composed_obs + self.endpoint_ndvi_weight * endpoint_composed_ndvi
        endpoint = 0.5 * (endpoint_direct + endpoint_composed)

        total = (
            self.w_state * state
            + self.w_observation * observation
            + self.w_ndvi * ndvi
            + self.w_endpoint * endpoint
        )
        return {
            "state": state,
            "observation": observation,
            "ndvi": ndvi,
            "endpoint": endpoint,
            "endpoint_direct": endpoint_direct,
            "endpoint_composed": endpoint_composed,
            "endpoint_direct_obs": endpoint_direct_obs,
            "endpoint_composed_obs": endpoint_composed_obs,
            "endpoint_direct_ndvi": endpoint_direct_ndvi,
            "endpoint_composed_ndvi": endpoint_composed_ndvi,
            # Diagnostics are retained separately from the weighted objective.
            "state_gap": _masked_mean(
                (direct_normalized - composed_normalized).pow(2).mean(dim=-1),
                state_mask,
            ),
            "state_std_direct": z_direct.float().std(dim=(1, 2), unbiased=False).mean(),
            "state_std_composed": z_composed.float().std(dim=(1, 2), unbiased=False).mean(),
            "total": total,
        }


def _validate_state_pair(
    z_direct: torch.Tensor,
    z_composed: torch.Tensor,
    state_mask: Optional[torch.Tensor],
) -> None:
    if z_direct.dim() != 3 or z_direct.shape != z_composed.shape:
        raise ValueError(
            "Partition states must be matching [B,N,D] tensors, got "
            f"direct={tuple(z_direct.shape)}, composed={tuple(z_composed.shape)}"
        )
    if state_mask is not None and state_mask.shape != z_direct.shape[:2]:
        raise ValueError(
            "partition state_mask must be [B,N], got "
            f"{tuple(state_mask.shape)} for states={tuple(z_direct.shape)}"
        )


def _validate_observation_triplet(
    pred_direct: torch.Tensor,
    pred_composed: torch.Tensor,
    target: torch.Tensor,
    target_mask: Optional[torch.Tensor],
) -> None:
    if pred_direct.dim() != 4 or pred_direct.shape != pred_composed.shape:
        raise ValueError(
            "Partition predictions must be matching [B,C,H,W] tensors, got "
            f"direct={tuple(pred_direct.shape)}, composed={tuple(pred_composed.shape)}"
        )
    if target.shape != pred_direct.shape:
        raise ValueError(
            "Partition terminal target must match prediction geometry, got "
            f"target={tuple(target.shape)}, pred={tuple(pred_direct.shape)}"
        )
    if target_mask is not None and target_mask.shape != pred_direct.shape[:1] + pred_direct.shape[-2:]:
        raise ValueError(
            "Partition target_mask must be [B,H,W], got "
            f"{tuple(target_mask.shape)} for pred={tuple(pred_direct.shape)}"
        )


def _masked_huber(
    prediction: torch.Tensor,
    target: torch.Tensor,
    mask: Optional[torch.Tensor],
) -> torch.Tensor:
    per_pixel = F.smooth_l1_loss(prediction, target, reduction="none").mean(dim=1)
    return _masked_mean(per_pixel, mask)


def _masked_l1(
    prediction: torch.Tensor,
    target: torch.Tensor,
    mask: Optional[torch.Tensor],
) -> torch.Tensor:
    return _masked_mean((prediction - target).abs(), mask)


def _masked_mean(values: torch.Tensor, mask: Optional[torch.Tensor]) -> torch.Tensor:
    if mask is None:
        return values.mean()
    if values.shape != mask.shape:
        raise ValueError(
            f"Partition mask shape {tuple(mask.shape)} does not match values {tuple(values.shape)}"
        )
    numeric_mask = mask.to(dtype=values.dtype, device=values.device)
    return (values * numeric_mask).sum() / numeric_mask.sum().clamp_min(1.0)
