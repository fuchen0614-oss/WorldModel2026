"""Project the explicit Stage 1.5 state tokens into decoder token space."""

from __future__ import annotations

import torch
import torch.nn as nn


class StateReconstructionBridge(nn.Module):
    """Bridge the state bottleneck to a legacy MAE decoder interface.

    The pretrained Stage 1 decoder expects encoder-width tokens (384 in the
    canonical setup), while the explicit land-surface state is narrower
    (256).  Keeping this projection separate lets us load the Stage 1 decoder
    weights unchanged while making the Stage 1.5 reconstruction path pass
    through the state projector.
    """

    def __init__(self, state_dim: int = 256, decoder_dim: int = 384):
        super().__init__()
        self.state_dim = state_dim
        self.decoder_dim = decoder_dim
        self.norm = nn.LayerNorm(state_dim)
        self.proj = nn.Linear(state_dim, decoder_dim)

    def forward(self, state_tokens: torch.Tensor) -> torch.Tensor:
        if state_tokens.dim() != 3:
            raise ValueError(
                f"Expected state tokens [B,N,D], got {tuple(state_tokens.shape)}"
            )
        if state_tokens.shape[-1] != self.state_dim:
            raise ValueError(
                f"Expected state width {self.state_dim}, got {state_tokens.shape[-1]}"
            )
        return self.proj(self.norm(state_tokens))

    def get_config(self) -> dict:
        return {"state_dim": self.state_dim, "decoder_dim": self.decoder_dim}
