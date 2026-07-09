"""Band adapter for feeding EarthNet optical bands into the Stage1.5 S2 encoder."""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn


class EarthNetInputAdapter(nn.Module):
    """Map EarthNet bands to the channel count expected by Stage1.5.

    The adapter is deliberately learnable. Zero-filling missing Sentinel-2
    channels is fine for a sanity check, but a trained adapter is safer for the
    main run because EarthNet target bands and SSL4EO S2L2A 12-band inputs are
    asymmetric.
    """

    def __init__(
        self,
        in_channels: int = 4,
        out_channels: int = 12,
        hidden_channels: int = 32,
        mode: str = "linear",
        source_to_canonical: Optional[list] = None,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.mode = mode
        self.source_to_canonical = (
            list(source_to_canonical)
            if source_to_canonical is not None
            else ([1, 2, 3, 7] if in_channels == 4 and out_channels == 12 else None)
        )
        if mode == "linear":
            self.net = nn.Conv2d(in_channels, out_channels, kernel_size=1)
        elif mode == "mlp":
            self.net = nn.Sequential(
                nn.Conv2d(in_channels, hidden_channels, kernel_size=1),
                nn.GELU(),
                nn.Conv2d(hidden_channels, out_channels, kernel_size=1),
            )
        else:
            raise ValueError(f"Unknown adapter mode: {mode}")
        self._init_weights()

    def _init_weights(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Conv2d):
                nn.init.kaiming_normal_(module.weight, mode="fan_out")
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
        if self.mode == "linear" and self.source_to_canonical is not None:
            if len(self.source_to_canonical) != self.in_channels:
                raise ValueError(
                    "source_to_canonical must contain one output index per input channel"
                )
            with torch.no_grad():
                self.net.weight.zero_()
                if self.net.bias is not None:
                    self.net.bias.zero_()
                for source_idx, canonical_idx in enumerate(self.source_to_canonical):
                    if not 0 <= canonical_idx < self.out_channels:
                        raise ValueError(
                            f"canonical channel index {canonical_idx} is outside [0, {self.out_channels})"
                        )
                    self.net.weight[canonical_idx, source_idx, 0, 0] = 1.0

    def forward(self, x: torch.Tensor, band_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Adapt either [B,C,H,W] or [B,T,C,H,W] tensors."""

        squeeze_time = False
        if x.dim() == 4:
            x = x.unsqueeze(1)
            squeeze_time = True
        if x.dim() != 5:
            raise ValueError(f"Expected [B,C,H,W] or [B,T,C,H,W], got {tuple(x.shape)}")
        b, t, c, h, w = x.shape
        if c != self.in_channels:
            raise ValueError(f"Expected {self.in_channels} input channels, got {c}")

        if band_mask is not None:
            if band_mask.dim() == 1:
                band_mask = band_mask.view(1, 1, c, 1, 1)
            elif band_mask.dim() == 2:
                band_mask = band_mask.view(b, 1, c, 1, 1)
            x = x * band_mask.to(dtype=x.dtype, device=x.device)

        y = self.net(x.reshape(b * t, c, h, w))
        y = y.reshape(b, t, self.out_channels, h, w)
        return y[:, 0] if squeeze_time else y

    def get_config(self) -> dict:
        return {
            "in_channels": self.in_channels,
            "out_channels": self.out_channels,
            "mode": self.mode,
            "source_to_canonical": self.source_to_canonical,
        }
