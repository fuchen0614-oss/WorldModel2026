"""Pure acquisition-condition encoder for Stage 1.5 dual conditioning."""

from typing import Dict, Optional

import torch
import torch.nn as nn

from .imaging_condition_encoder import SunElevationEncoder, SARGeometryEncoder


class PureImagingConditionEncoder(nn.Module):
    """Encode only acquisition metadata, excluding semantic shortcuts.

    Modality codes follow ``data.phi_loader``: 0=S2L2A and 1=S1GRD.
    S2 uses solar elevation; S1 uses orbit/platform geometry. Location,
    season, day-of-year, DEM, and cloud appearance are intentionally absent.
    """

    def __init__(
        self,
        embed_dim: int = 384,
        sun_dim: int = 64,
        sar_geom_dim: int = 64,
        dropout: float = 0.0,
        condition_dropout: float = 0.10,
        use_sar_geometry: bool = True,
    ):
        super().__init__()
        if not 0.0 <= condition_dropout < 1.0:
            raise ValueError("condition_dropout must be in [0, 1)")
        self.embed_dim = embed_dim
        self.condition_dropout = condition_dropout
        self.use_sar_geometry = use_sar_geometry
        self.sun_encoder = SunElevationEncoder(sun_dim)
        self.sar_encoder = SARGeometryEncoder(embed_dim=sar_geom_dim) if use_sar_geometry else None
        fused_dim = sun_dim + (sar_geom_dim if use_sar_geometry else 0)
        self.fuse = nn.Sequential(
            nn.Linear(fused_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim, embed_dim),
            nn.LayerNorm(embed_dim),
        )

    def forward(
        self,
        phi: Dict[str, torch.Tensor],
        drop_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        modality = phi["modality"]
        time_valid = phi.get("time_valid", torch.ones_like(modality)).gt(0)
        sun = phi.get("sun_elevation")
        if sun is None:
            sun = torch.full(modality.shape, float("nan"), device=modality.device)

        is_s2 = modality.eq(0)
        sun_valid = time_valid & is_s2 & torch.isfinite(sun)
        sun_feat = self.sun_encoder(sun, sun_valid.float()) * is_s2.unsqueeze(-1)

        features = [sun_feat]
        if self.sar_encoder is not None:
            is_s1 = modality.eq(1)
            features.append(self.sar_encoder(phi) * is_s1.unsqueeze(-1))

        embedding = self.fuse(torch.cat(features, dim=-1))
        if drop_mask is None and self.training and self.condition_dropout > 0:
            drop_mask = torch.rand(modality.shape[0], device=modality.device) < self.condition_dropout
        if drop_mask is not None:
            embedding = embedding.masked_fill(drop_mask.bool().unsqueeze(-1), 0.0)
        return embedding

    def get_config(self) -> dict:
        return {
            "embed_dim": self.embed_dim,
            "condition_dropout": self.condition_dropout,
            "pure_acquisition_fields": True,
            "use_sar_geometry": self.use_sar_geometry,
        }
