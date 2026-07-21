"""EarthNet observation decoder for Stage 2 future-state tokens."""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from .light_decoder import LightDecoder


class EarthNetObservationDecoder(nn.Module):
    """Decode predicted state tokens to EarthNet target bands."""

    def __init__(
        self,
        in_dim: int = 256,
        out_channels: int = 4,
        patch_size: int = 16,
        img_size: int = 256,
        depth: int = 3,
        num_heads: int = 4,
        decoder_embed_dim: int = 192,
        mlp_ratio: float = 4.0,
        dropout: float = 0.0,
        decoder_mode: str = "transformer",
        predict_logvar: bool = False,
        output_activation: str = "sigmoid",
        residual: bool = False,
    ):
        super().__init__()
        self.out_channels = out_channels
        self.predict_logvar = predict_logvar
        self.output_activation = output_activation
        # Residual (Plan A / Contextformer-style): decode a bounded delta and
        # anchor it on a per-pixel last-valid baseline, so the model starts near
        # persistence and learns the change. Backward compatible: default off.
        self.residual = bool(residual)
        channels = out_channels * (2 if predict_logvar else 1)
        self.decoder = LightDecoder(
            in_dim=in_dim,
            out_channels=channels,
            patch_size=patch_size,
            img_size=img_size,
            depth=depth,
            num_heads=num_heads,
            decoder_embed_dim=decoder_embed_dim,
            mlp_ratio=mlp_ratio,
            dropout=dropout,
            decoder_mode=decoder_mode,
        )
        # Full Stage2 token grids never invoke MAE mask-token restoration.
        if hasattr(self.decoder, "mask_token"):
            self.decoder.mask_token.requires_grad_(False)

    def forward(
        self,
        state_tokens: torch.Tensor,
        baseline: Optional[torch.Tensor] = None,
    ) -> dict:
        y = self.decoder(state_tokens)
        if self.residual and baseline is not None:
            # ``y`` is a raw reflectance-space residual; anchor on the
            # last-valid baseline. tanh bounds the per-step change to +/-1.
            if baseline.shape[-2:] != y.shape[-2:]:
                baseline = F.interpolate(
                    baseline, size=y.shape[-2:], mode="bilinear", align_corners=False
                )
            if not self.predict_logvar:
                return {"mean": (baseline + torch.tanh(y)).clamp(0.0, 1.0)}
            raw_mean, logvar = y[:, : self.out_channels], y[:, self.out_channels:]
            return {
                "mean": (baseline + torch.tanh(raw_mean)).clamp(0.0, 1.0),
                "logvar": logvar.clamp(-10.0, 5.0),
            }
        if not self.predict_logvar:
            return {"mean": self._activate(y)}
        mean, logvar = y[:, : self.out_channels], y[:, self.out_channels:]
        return {"mean": self._activate(mean), "logvar": logvar.clamp(-10.0, 5.0)}

    def _activate(self, value: torch.Tensor) -> torch.Tensor:
        if self.output_activation == "sigmoid":
            return torch.sigmoid(value)
        if self.output_activation == "clamp":
            return value.clamp(0.0, 1.0)
        if self.output_activation in {"none", "identity"}:
            return value
        raise ValueError(f"Unknown output_activation: {self.output_activation}")

    def get_config(self) -> dict:
        cfg = self.decoder.get_config()
        cfg.update({
            "predict_logvar": self.predict_logvar,
            "output_activation": self.output_activation,
            "residual": self.residual,
        })
        return cfg
