"""Losses for credible Stage 1.5 state estimation."""

from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


def _zero_like(x: torch.Tensor) -> torch.Tensor:
    return x.sum() * 0.0


class CrossModalVICRegLoss(nn.Module):
    """Align near-contemporaneous S1/S2 state while preventing collapse."""

    def __init__(self, invariance_weight=25.0, variance_weight=25.0, covariance_weight=1.0):
        super().__init__()
        self.invariance_weight = invariance_weight
        self.variance_weight = variance_weight
        self.covariance_weight = covariance_weight

    @staticmethod
    def _variance(x: torch.Tensor) -> torch.Tensor:
        std = torch.sqrt(x.var(dim=0, unbiased=False) + 1e-4)
        return F.relu(1.0 - std).mean()

    @staticmethod
    def _covariance(x: torch.Tensor) -> torch.Tensor:
        if x.shape[0] < 2:
            return _zero_like(x)
        x = x - x.mean(dim=0)
        cov = x.T @ x / (x.shape[0] - 1)
        offdiag = cov - torch.diag(torch.diagonal(cov))
        return offdiag.square().sum() / x.shape[1]

    def forward(self, z_s1: torch.Tensor, z_s2: torch.Tensor,
                valid_mask: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        if valid_mask is not None:
            keep = valid_mask.bool()
            z_s1, z_s2 = z_s1[keep], z_s2[keep]
        if z_s1.shape[0] < 2:
            zero = _zero_like(z_s1)
            return {"total": zero, "invariance": zero, "variance": zero, "covariance": zero}
        inv = F.mse_loss(z_s1, z_s2)
        var = self._variance(z_s1) + self._variance(z_s2)
        cov = self._covariance(z_s1) + self._covariance(z_s2)
        total = self.invariance_weight * inv + self.variance_weight * var + self.covariance_weight * cov
        return {"total": total, "invariance": inv, "variance": var, "covariance": cov}


class PhiCrossCovarianceLoss(nn.Module):
    """Penalize linear leakage from state into fixed raw acquisition fields."""

    @staticmethod
    def _raw_features(phi: Dict[str, torch.Tensor], modality: str) -> torch.Tensor:
        ref = phi["modality"]
        if modality == "S2":
            sun = torch.nan_to_num(phi["sun_elevation"], nan=0.0)
            valid = (phi["time_valid"] > 0).float()
            return torch.stack([torch.sin(torch.deg2rad(sun)), valid], dim=-1)
        orbit = phi.get("s1_orbit_direction", torch.full_like(ref, -1))
        rel = phi.get("s1_relative_orbit", torch.full_like(ref, -1))
        sat = phi.get("s1_satellite", torch.full_like(ref, -1))
        orbit_oh = F.one_hot(orbit.clamp(0, 1), 2).float() * orbit.ge(0).unsqueeze(-1)
        sat_oh = F.one_hot(sat.clamp(0, 1), 2).float() * sat.ge(0).unsqueeze(-1)
        angle = 2.0 * torch.pi * rel.clamp_min(0).float() / 175.0
        rel_valid = rel.ge(1).float()
        return torch.cat([orbit_oh, sat_oh, torch.stack([
            torch.sin(angle) * rel_valid, torch.cos(angle) * rel_valid, rel_valid
        ], dim=-1)], dim=-1)

    def forward(self, state: torch.Tensor, phi: Dict[str, torch.Tensor], modality: str) -> torch.Tensor:
        nuisance = self._raw_features(phi, modality)
        if state.shape[0] < 2:
            return _zero_like(state)
        state = (state - state.mean(0)) / (state.std(0, unbiased=False) + 1e-4)
        nuisance = (nuisance - nuisance.mean(0)) / (nuisance.std(0, unbiased=False) + 1e-4)
        cross_cov = state.T @ nuisance / max(1, state.shape[0] - 1)
        return cross_cov.square().mean()


class FeatureAnchorLoss(nn.Module):
    """Keep conditioned encoder semantics close to the frozen Stage 1 teacher."""

    def forward(self, student_tokens: torch.Tensor, teacher_tokens: torch.Tensor) -> torch.Tensor:
        student = F.normalize(student_tokens.mean(dim=1), dim=-1)
        teacher = F.normalize(teacher_tokens.mean(dim=1), dim=-1)
        return (1.0 - (student * teacher).sum(dim=-1)).mean()


def masked_pixel_reconstruction_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    patch_mask: torch.Tensor,
    quality_mask: Optional[torch.Tensor] = None,
    loss_type: str = "l1",
) -> torch.Tensor:
    """Average reconstruction error on masked, valid pixels and channels."""
    b, c, h, w = pred.shape
    side = int(patch_mask.shape[1] ** 0.5)
    patch = h // side
    pixel_mask = patch_mask.reshape(b, 1, side, side)
    pixel_mask = pixel_mask.repeat_interleave(patch, 2).repeat_interleave(patch, 3)
    if quality_mask is not None:
        if quality_mask.dim() == 3:
            quality_mask = quality_mask.unsqueeze(1)
        pixel_mask = pixel_mask * quality_mask.to(pixel_mask.dtype)
    error = (pred - target).abs() if loss_type == "l1" else (pred - target).square()
    denom = pixel_mask.sum().clamp_min(1.0) * c
    return (error * pixel_mask).sum() / denom


def s2_clear_pixel_mask(cloud_mask: torch.Tensor) -> torch.Tensor:
    """Mask Sentinel-2 no-data, saturated, shadow, cloud and cirrus classes."""
    cloud_mask = cloud_mask.long()
    invalid = (
        cloud_mask.eq(0) | cloud_mask.eq(1) | cloud_mask.eq(3)
        | cloud_mask.eq(8) | cloud_mask.eq(9) | cloud_mask.eq(10)
    )
    return ~invalid
