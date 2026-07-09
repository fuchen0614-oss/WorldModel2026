"""End-to-end ObsWorld Stage 2 model for EarthNet forecasting."""

from __future__ import annotations

import copy
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from data.earthnet_fields import make_neutral_s2_phi


class ObsWorldStage2Model(nn.Module):
    """Stage2 wrapper: context observations -> state dynamics -> future images."""

    def __init__(
        self,
        band_adapter: nn.Module,
        encoder: nn.Module,
        phi_encoder: Optional[nn.Module],
        state_projector: nn.Module,
        context_aggregator: nn.Module,
        driver_encoder: nn.Module,
        horizon_encoder: nn.Module,
        geo_tokenizer: nn.Module,
        dynamics: nn.Module,
        decoder: nn.Module,
        target_band_adapter: Optional[nn.Module] = None,
        max_h_days: float = 100.0,
        use_phi_encoder: bool = True,
        compute_latent_targets: bool = True,
        use_D: bool = True,
        use_G: bool = True,
        use_h: bool = True,
    ):
        super().__init__()
        self.band_adapter = band_adapter
        self.target_band_adapter = (
            target_band_adapter if target_band_adapter is not None else copy.deepcopy(band_adapter)
        )
        self.target_band_adapter.requires_grad_(False)
        self.encoder = encoder
        if hasattr(self.encoder, "patch_embed") and hasattr(
            self.encoder.patch_embed, "s1_proj"
        ):
            self.encoder.patch_embed.s1_proj.requires_grad_(False)
        if hasattr(self.encoder, "modality_embed_s1"):
            self.encoder.modality_embed_s1.requires_grad_(False)
        self.phi_encoder = phi_encoder
        # EarthNet does not provide Stage1.5 acquisition metadata. The neutral
        # phi path remains a fixed pretrained missing-condition reference.
        if self.phi_encoder is not None:
            self.phi_encoder.requires_grad_(False)
        self.state_projector = state_projector
        self.context_aggregator = context_aggregator
        self.driver_encoder = driver_encoder
        self.horizon_encoder = horizon_encoder
        self.geo_tokenizer = geo_tokenizer
        self.dynamics = dynamics
        self.decoder = decoder
        self.max_h_days = float(max_h_days)
        self.use_phi_encoder = use_phi_encoder
        self.compute_latent_targets = compute_latent_targets
        self.use_D = use_D
        self.use_G = use_G
        self.use_h = use_h

    def encode_observations(
        self,
        x: torch.Tensor,
        pixel_mask: Optional[torch.Tensor] = None,
        use_target_adapter: bool = False,
    ) -> torch.Tensor:
        """Encode [B,T,C,H,W] EarthNet observations to [B,T,N,state_dim]."""

        if x.dim() != 5:
            raise ValueError(f"Expected x [B,T,C,H,W], got {tuple(x.shape)}")
        b, t, _, h, w = x.shape
        if pixel_mask is not None:
            x = x * pixel_mask.to(dtype=x.dtype, device=x.device).unsqueeze(2)
        adapter = self.target_band_adapter if use_target_adapter else self.band_adapter
        x12 = adapter(x)
        flat = x12.reshape(b * t, x12.shape[2], h, w)

        phi_embed = None
        if self.use_phi_encoder and self.phi_encoder is not None:
            phi = make_neutral_s2_phi(b * t, flat.device)
            phi_embed = self.phi_encoder(phi)

        tokens, _, _ = self.encoder(flat, "S2", mask_ratio=0.0, phi_embed=phi_embed)
        states = self.state_projector(tokens)
        return states.reshape(b, t, states.shape[1], states.shape[2])

    def forward(self, batch: dict) -> dict:
        x_context = batch["x_context"]
        x_target = batch["x_target"]
        context_mask = batch.get("context_mask")
        drivers = batch["D"]
        driver_mask = batch["D_mask"]
        geo = batch["G"]
        geo_mask = batch.get("G_mask")
        horizons = batch["h"]

        context_states = self.encode_observations(x_context, context_mask)
        valid_context = None
        if context_mask is not None:
            valid_context = _pixel_mask_to_token_mask(
                context_mask,
                context_states.shape[2],
            )
        z_context = self.context_aggregator(context_states, valid_context)

        b, hf, _ = drivers.shape
        n = z_context.shape[1]
        geo_tokens = self.geo_tokenizer(geo, geo_mask)
        driver_embedding = self.driver_encoder(drivers, driver_mask)
        horizon_embedding = self.horizon_encoder(horizons)

        z_in = z_context[:, None].expand(b, hf, n, z_context.shape[-1]).reshape(b * hf, n, -1)
        d_in = driver_embedding.reshape(b * hf, driver_embedding.shape[-1])
        g_in = geo_tokens[:, None].expand(b, hf, n, geo_tokens.shape[-1]).reshape(b * hf, n, -1)
        h_in = horizon_embedding.reshape(b * hf, horizon_embedding.shape[-1])
        if not self.use_D:
            d_in = torch.zeros_like(d_in)
        if not self.use_G:
            g_in = torch.zeros_like(g_in)
        if not self.use_h:
            h_in = torch.zeros_like(h_in)

        z_pred = self.dynamics(z_in, driver=d_in, geo=g_in, time_delta=h_in)
        decoded = self.decoder(z_pred)
        pred = decoded["mean"].reshape(b, hf, decoded["mean"].shape[1], decoded["mean"].shape[2], decoded["mean"].shape[3])

        out = {
            "pred": pred,
            "z_pred": z_pred.reshape(b, hf, z_pred.shape[1], z_pred.shape[2]),
            "z_context": z_context,
        }

        if self.compute_latent_targets:
            with torch.no_grad():
                # Keep context and target in the same evolving 4->12 band space
                # while stopping the target branch from receiving gradients.
                self.target_band_adapter.load_state_dict(self.band_adapter.state_dict())
                z_target = self.encode_observations(
                    x_target,
                    batch.get("target_mask"),
                    use_target_adapter=True,
                )
            out["z_target"] = z_target
            if batch.get("target_mask") is not None:
                out["z_target_mask"] = _pixel_mask_to_token_mask(
                    batch["target_mask"],
                    z_target.shape[2],
                )
        return out


def _pixel_mask_to_token_mask(pixel_mask: torch.Tensor, num_tokens: int) -> torch.Tensor:
    """Pool [B,T,H,W] clear masks to the square encoder token grid."""

    if pixel_mask.dim() != 4:
        raise ValueError(
            f"Expected pixel mask [B,T,H,W], got {tuple(pixel_mask.shape)}"
        )
    grid = int(round(num_tokens ** 0.5))
    if grid * grid != num_tokens:
        raise ValueError(f"Cannot map {num_tokens} tokens to a square grid")
    b, t, h, w = pixel_mask.shape
    pooled = F.adaptive_avg_pool2d(
        pixel_mask.reshape(b * t, 1, h, w).float(),
        output_size=(grid, grid),
    )
    return pooled.reshape(b, t, num_tokens).gt(0.05)
