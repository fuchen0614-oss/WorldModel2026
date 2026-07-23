"""Losses for ObsWorld Stage 2 EarthNet forecasting."""

from __future__ import annotations

from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from data.earthnet_fields import compute_ndvi


class EarthNetForecastLoss(nn.Module):
    """Composite loss for future observation + latent dynamics supervision."""

    def __init__(
        self,
        red_index: int = 2,
        nir_index: int = 3,
        w_obs: float = 1.0,
        w_ndvi: float = 0.5,
        w_latent: float = 0.2,
        w_delta: float = 0.1,
        w_smooth: float = 0.02,
        w_ndvi_main: float = 0.0,
        w_ndvi_consistency: float = 0.0,
        obs_loss: str = "huber",
    ):
        super().__init__()
        self.red_index = red_index
        self.nir_index = nir_index
        self.w_obs = w_obs
        self.w_ndvi = w_ndvi
        self.w_latent = w_latent
        self.w_delta = w_delta
        self.w_smooth = w_smooth
        # A' accuracy-aligned terms (off by default): masked-L2 NDVI on the direct
        # NDVI head over the evaluator-aligned vegetation mask, and a consistency
        # term tying the direct NDVI to the NDVI implied by predicted red/nir.
        self.w_ndvi_main = w_ndvi_main
        self.w_ndvi_consistency = w_ndvi_consistency
        self.obs_loss = obs_loss

    @classmethod
    def from_config(cls, config: dict, red_index: int, nir_index: int) -> "EarthNetForecastLoss":
        weights = config.get("weights", {})
        return cls(
            red_index=red_index,
            nir_index=nir_index,
            w_obs=float(weights.get("obs", 1.0)),
            w_ndvi=float(weights.get("ndvi", 0.5)),
            w_latent=float(weights.get("latent", 0.2)),
            w_delta=float(weights.get("delta", 0.1)),
            w_smooth=float(weights.get("smooth", 0.02)),
            w_ndvi_main=float(weights.get("ndvi_main", 0.0)),
            w_ndvi_consistency=float(weights.get("ndvi_consistency", 0.0)),
            obs_loss=str(config.get("obs_loss", "huber")),
        )

    def forward(
        self,
        pred: torch.Tensor,
        target: torch.Tensor,
        target_mask: Optional[torch.Tensor] = None,
        z_pred: Optional[torch.Tensor] = None,
        z_target: Optional[torch.Tensor] = None,
        z_context: Optional[torch.Tensor] = None,
        z_target_mask: Optional[torch.Tensor] = None,
        horizons: Optional[torch.Tensor] = None,
        ndvi_pred: Optional[torch.Tensor] = None,
        veg_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """Compute losses.

        Args:
            pred/target: [B,T,C,H,W] reflectance-space tensors.
            target_mask: [B,T,H,W] valid pixels.
            z_pred/z_target: [B,T,N,D].
            z_context: [B,N,D].
        """

        out: Dict[str, torch.Tensor] = {}
        out["obs"] = _masked_reconstruction_loss(pred, target, target_mask, self.obs_loss)
        total = self.w_obs * out["obs"]

        out["ndvi"] = _masked_l1(
            compute_ndvi(pred, self.red_index, self.nir_index).clamp(-1.0, 1.0),
            compute_ndvi(target, self.red_index, self.nir_index).clamp(-1.0, 1.0),
            target_mask,
        )
        total = total + self.w_ndvi * out["ndvi"]

        # A' accuracy-aligned NDVI head supervision. ``ndvi_pred`` is [B,T,1,H,W]
        # (or [B,T,H,W]) from O_ndvi(zh); the main term is masked-L2 against the
        # target NDVI over the evaluator-aligned vegetation-clear mask, matching
        # the metric the official evaluator scores. A consistency term ties the
        # direct NDVI to the NDVI implied by the reflectance head so the two
        # outputs cannot diverge. Both terms are weight-gated (0 by default), so
        # legacy configs are byte-for-byte unaffected.
        if ndvi_pred is not None:
            ndvi_pred_hw = ndvi_pred.squeeze(2) if ndvi_pred.dim() == 5 else ndvi_pred
            target_ndvi = compute_ndvi(target, self.red_index, self.nir_index).clamp(-1.0, 1.0)
            veg = veg_mask if veg_mask is not None else target_mask
            out["ndvi_main"] = _masked_mean((ndvi_pred_hw - target_ndvi).pow(2), veg)
            total = total + self.w_ndvi_main * out["ndvi_main"]
            pred_ndvi = compute_ndvi(pred, self.red_index, self.nir_index).clamp(-1.0, 1.0)
            out["ndvi_consistency"] = _masked_l1(ndvi_pred_hw, pred_ndvi, veg)
            total = total + self.w_ndvi_consistency * out["ndvi_consistency"]
        else:
            out["ndvi_main"] = pred.new_zeros(())
            out["ndvi_consistency"] = pred.new_zeros(())

        if z_pred is not None and z_target is not None:
            out["latent"] = _latent_cosine_loss(z_pred, z_target, z_target_mask)
            total = total + self.w_latent * out["latent"]
        else:
            out["latent"] = pred.new_zeros(())

        if z_pred is not None and z_target is not None and z_context is not None:
            out["delta"] = _delta_alignment_loss(
                z_pred, z_target, z_context, z_target_mask
            )
            total = total + self.w_delta * out["delta"]
        else:
            out["delta"] = pred.new_zeros(())

        if z_pred is not None and z_pred.shape[1] > 1:
            out["smooth"] = _temporal_smoothness(z_pred, horizons)
            total = total + self.w_smooth * out["smooth"]
        else:
            out["smooth"] = pred.new_zeros(())

        out["total"] = total
        return out


def _masked_reconstruction_loss(pred: torch.Tensor, target: torch.Tensor, mask: Optional[torch.Tensor], kind: str) -> torch.Tensor:
    if kind == "l1":
        per = (pred - target).abs().mean(dim=2)
    elif kind == "mse":
        per = (pred - target).pow(2).mean(dim=2)
    else:
        per = F.smooth_l1_loss(pred, target, reduction="none").mean(dim=2)
    return _masked_mean(per, mask)


def _masked_l1(pred: torch.Tensor, target: torch.Tensor, mask: Optional[torch.Tensor]) -> torch.Tensor:
    return _masked_mean((pred - target).abs(), mask)


def _masked_mean(per: torch.Tensor, mask: Optional[torch.Tensor]) -> torch.Tensor:
    if mask is None:
        return per.mean()
    m = mask.to(dtype=per.dtype, device=per.device)
    return (per * m).sum() / m.sum().clamp_min(1.0)


def _latent_cosine_loss(
    z_pred: torch.Tensor,
    z_target: torch.Tensor,
    mask: Optional[torch.Tensor],
) -> torch.Tensor:
    zp = F.normalize(z_pred, dim=-1)
    zt = F.normalize(z_target.detach(), dim=-1)
    return _masked_mean(1.0 - (zp * zt).sum(dim=-1), mask)


def _delta_alignment_loss(
    z_pred: torch.Tensor,
    z_target: torch.Tensor,
    z_context: torch.Tensor,
    mask: Optional[torch.Tensor],
) -> torch.Tensor:
    base = z_context[:, None].expand_as(z_pred)
    pred_delta = z_pred - base
    target_delta = z_target.detach() - base.detach()
    per_token = F.smooth_l1_loss(
        pred_delta,
        target_delta,
        reduction="none",
    ).mean(dim=-1)
    return _masked_mean(per_token, mask)


def _temporal_smoothness(
    z_pred: torch.Tensor,
    horizons: Optional[torch.Tensor],
) -> torch.Tensor:
    if horizons is None:
        return (z_pred[:, 1:] - z_pred[:, :-1]).pow(2).mean()
    if horizons.shape[:2] != z_pred.shape[:2]:
        raise ValueError(
            f"horizon shape {tuple(horizons.shape)} does not match z_pred {tuple(z_pred.shape)}"
        )
    gaps = (horizons[:, 1:] - horizons[:, :-1]).clamp_min(1.0)
    velocity = (z_pred[:, 1:] - z_pred[:, :-1]) / gaps[:, :, None, None]
    if velocity.shape[1] < 2:
        return velocity.pow(2).mean()
    return (velocity[:, 1:] - velocity[:, :-1]).pow(2).mean()
