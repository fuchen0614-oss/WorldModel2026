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
        w_ndvi_lc_mse: float = 0.0,
        w_ndvi_time_bias: float = 0.0,
        w_ndvi_time_ccc: float = 0.0,
        lc_min_pixels: int = 32,
        ccc_min_obs: int = 5,
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
        # Metric-aligned terms (off by default). These mirror the official
        # GreenEarthNet scoring structure: per-pixel reductions over the future
        # horizon, then a LANDCOVER-MACRO average over classes {10,20,30,40}.
        #   - ndvi_lc_mse: land-cover-macro masked NDVI MSE (main objective).
        #   - ndvi_time_bias: land-cover-macro mean |per-pixel temporal bias|.
        #   - ndvi_time_ccc: land-cover-macro mean per-pixel (1 - Lin's CCC).
        # All three are weight-gated (default 0.0) so legacy configs are
        # byte-for-byte unaffected, and every reduction is numerically guarded so
        # they can never emit NaN/Inf (empty-class / low-obs paths return a
        # grad-carrying zero).
        self.w_ndvi_lc_mse = w_ndvi_lc_mse
        self.w_ndvi_time_bias = w_ndvi_time_bias
        self.w_ndvi_time_ccc = w_ndvi_time_ccc
        self.lc_min_pixels = int(lc_min_pixels)
        self.ccc_min_obs = int(ccc_min_obs)
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
            w_ndvi_lc_mse=float(weights.get("ndvi_lc_mse", 0.0)),
            w_ndvi_time_bias=float(weights.get("ndvi_time_bias", 0.0)),
            w_ndvi_time_ccc=float(weights.get("ndvi_time_ccc", 0.0)),
            lc_min_pixels=int(config.get("lc_min_pixels", 32)),
            ccc_min_obs=int(config.get("ccc_min_obs", 5)),
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
        landcover: Optional[torch.Tensor] = None,
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

            # Metric-aligned NDVI terms. Computed only when their weight is > 0 so
            # legacy runs pay no extra compute and their loss total is byte-for-byte
            # unchanged. Each is land-cover-macro over classes {10,20,30,40} and
            # degrades to the plain veg-masked reduction when land cover is absent
            # or all-zero (so ndvi_lc_mse is a strict superset of ndvi_main).
            need_lc = self.w_ndvi_lc_mse > 0.0
            need_bias = self.w_ndvi_time_bias > 0.0
            need_ccc = self.w_ndvi_time_ccc > 0.0
            if need_lc:
                out["ndvi_lc_mse"] = _ndvi_lc_mse(
                    ndvi_pred_hw, target_ndvi, veg, landcover, self.lc_min_pixels
                )
                total = total + self.w_ndvi_lc_mse * out["ndvi_lc_mse"]
            else:
                out["ndvi_lc_mse"] = pred.new_zeros(())
            if need_bias:
                out["ndvi_time_bias"] = _ndvi_time_bias(
                    ndvi_pred_hw, target_ndvi, veg, landcover
                )
                total = total + self.w_ndvi_time_bias * out["ndvi_time_bias"]
            else:
                out["ndvi_time_bias"] = pred.new_zeros(())
            if need_ccc:
                out["ndvi_time_ccc"] = _ndvi_time_ccc(
                    ndvi_pred_hw, target_ndvi, veg, landcover, self.ccc_min_obs
                )
                total = total + self.w_ndvi_time_ccc * out["ndvi_time_ccc"]
            else:
                out["ndvi_time_ccc"] = pred.new_zeros(())
        else:
            out["ndvi_main"] = pred.new_zeros(())
            out["ndvi_consistency"] = pred.new_zeros(())
            out["ndvi_lc_mse"] = pred.new_zeros(())
            out["ndvi_time_bias"] = pred.new_zeros(())
            out["ndvi_time_ccc"] = pred.new_zeros(())

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


# Land-cover classes scored by the official GreenEarthNet macro-average.
_LANDCOVER_CLASSES = (10.0, 20.0, 30.0, 40.0)
_CCC_EPS = 1.0e-6


def _veg_float(pred: torch.Tensor, veg: Optional[torch.Tensor]) -> torch.Tensor:
    """[B,T,H,W] float veg mask (ones when unspecified)."""
    if veg is None:
        return torch.ones_like(pred)
    return veg.to(dtype=pred.dtype, device=pred.device)


def _landcover_bthw(
    landcover: Optional[torch.Tensor], ref: torch.Tensor
) -> Optional[torch.Tensor]:
    """Broadcast a static/[B,1,..]/[B,T,..] land-cover map to ``ref``'s [B,T,H,W].

    Returns ``None`` when land cover is absent OR carries no scored class
    (all-zero == "unknown"), which routes callers to the global fallback.
    """
    if landcover is None:
        return None
    lc = landcover.to(dtype=ref.dtype, device=ref.device)
    if lc.dim() == 3:  # [B,H,W] static map
        lc = lc.unsqueeze(1)
    if lc.dim() != 4:
        return None
    b, t, h, w = ref.shape
    if lc.shape[1] == 1 and t != 1:
        lc = lc.expand(b, t, lc.shape[2], lc.shape[3])
    if lc.shape[-2:] != (h, w):
        lc = F.interpolate(lc, size=(h, w), mode="nearest")
    # No scored class present -> treat as unavailable (degrade path).
    present = torch.zeros((), dtype=torch.bool, device=lc.device)
    for c in _LANDCOVER_CLASSES:
        present = present | (lc == c).any()
    if not bool(present):
        return None
    return lc


def _ndvi_lc_mse(
    pred: torch.Tensor,
    target: torch.Tensor,
    veg: Optional[torch.Tensor],
    landcover: Optional[torch.Tensor],
    min_pixels: int,
) -> torch.Tensor:
    """Land-cover-macro veg-masked NDVI MSE over [B,T,H,W].

    per-class MSE_c = sum((pred-true)^2 * veg * [lc==c]) / clamp_min(sum(mask_c), min_pixels)
    term = mean over classes c with sum(mask_c) >= min_pixels.
    Degrades to the plain veg-masked MSE (== ndvi_main) when land cover is
    absent or carries no scored class.
    """
    se = (pred - target).pow(2)
    veg_f = _veg_float(pred, veg)
    lc = _landcover_bthw(landcover, pred)
    if lc is None:
        return _masked_mean(se, veg_f)
    class_vals = []
    for c in _LANDCOVER_CLASSES:
        mask_c = veg_f * (lc == c).to(dtype=pred.dtype)
        count = mask_c.sum()
        if float(count.detach()) >= float(min_pixels):
            class_vals.append((se * mask_c).sum() / count.clamp_min(float(min_pixels)))
    if class_vals:
        return torch.stack(class_vals).mean()
    return _masked_mean(se, veg_f)


def _per_pixel_time_stats(
    pred: torch.Tensor,
    target: torch.Tensor,
    veg_f: torch.Tensor,
):
    """Per-pixel temporal reductions over the veg-valid time axis.

    Returns (n_obs[B,H,W], mean_pred, mean_true) with the per-pixel observation
    count NOT clamped (callers apply their own eligibility threshold); means use
    a clamped denominator so pixels with no observation stay finite (they are
    later excluded by the n_obs guard).
    """
    n_obs = veg_f.sum(dim=1)
    denom = n_obs.clamp_min(1.0)
    mean_pred = (pred * veg_f).sum(dim=1) / denom
    mean_true = (target * veg_f).sum(dim=1) / denom
    return n_obs, mean_pred, mean_true


def _macro_over_pixels(
    values: torch.Tensor,
    pixel_mask: torch.Tensor,
    landcover: Optional[torch.Tensor],
    ref: torch.Tensor,
    anchor: torch.Tensor,
) -> torch.Tensor:
    """Land-cover-macro mean of a per-pixel [B,H,W] quantity.

    ``pixel_mask`` [B,H,W] flags eligible pixels. Macro-averages the per-class
    mean over eligible pixels of ``values`` across classes {10,20,30,40}. When
    land cover is unavailable (or empty for every class), degrades to the plain
    mean over eligible pixels. When no pixel is eligible at all, returns a
    grad-carrying zero (``anchor.sum() * 0`` -> never NaN/Inf).
    """
    pmask = pixel_mask.to(dtype=values.dtype)
    lc = _landcover_bthw(landcover, ref)
    if lc is not None:
        lc_hw = lc[:, 0]  # land cover is static over the time axis
        class_vals = []
        for c in _LANDCOVER_CLASSES:
            m = pmask * (lc_hw == c).to(dtype=values.dtype)
            count = m.sum()
            if float(count.detach()) >= 1.0:
                class_vals.append((values * m).sum() / count.clamp_min(1.0))
        if class_vals:
            return torch.stack(class_vals).mean()
    total_count = pmask.sum()
    if float(total_count.detach()) >= 1.0:
        return (values * pmask).sum() / total_count.clamp_min(1.0)
    return anchor.sum() * 0.0


def _ndvi_time_bias(
    pred: torch.Tensor,
    target: torch.Tensor,
    veg: Optional[torch.Tensor],
    landcover: Optional[torch.Tensor],
) -> torch.Tensor:
    """Land-cover-macro mean of |per-pixel temporal bias| (true - pred)."""
    veg_f = _veg_float(pred, veg)
    n_obs, mean_pred, mean_true = _per_pixel_time_stats(pred, target, veg_f)
    bias = (mean_true - mean_pred).abs()
    eligible = (n_obs >= 1.0).to(dtype=pred.dtype)
    return _macro_over_pixels(bias, eligible, landcover, pred, pred)


def _ndvi_time_ccc(
    pred: torch.Tensor,
    target: torch.Tensor,
    veg: Optional[torch.Tensor],
    landcover: Optional[torch.Tensor],
    min_obs: int,
) -> torch.Tensor:
    """Land-cover-macro mean of per-pixel (1 - Lin's CCC) over the time axis.

    Per pixel, over veg-valid steps:
        CCC = 2*cov / (var_pred + var_true + (mean_pred-mean_true)^2 + eps)
    Only pixels with n_obs >= ``min_obs`` are eligible; all denominators are
    clamped and ``eps`` guards the CCC ratio, so the term is finite by
    construction and returns a grad-carrying zero if nothing is eligible.
    """
    veg_f = _veg_float(pred, veg)
    n_obs, mean_pred, mean_true = _per_pixel_time_stats(pred, target, veg_f)
    denom = n_obs.clamp_min(1.0)
    dp = (pred - mean_pred.unsqueeze(1)) * veg_f
    dt = (target - mean_true.unsqueeze(1)) * veg_f
    var_pred = (dp * dp).sum(dim=1) / denom
    var_true = (dt * dt).sum(dim=1) / denom
    cov = (dp * dt).sum(dim=1) / denom
    ccc = (2.0 * cov) / (
        var_pred + var_true + (mean_pred - mean_true).pow(2) + _CCC_EPS
    )
    one_minus_ccc = 1.0 - ccc
    eligible = (n_obs >= float(min_obs)).to(dtype=pred.dtype)
    return _macro_over_pixels(one_minus_ccc, eligible, landcover, pred, pred)



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
