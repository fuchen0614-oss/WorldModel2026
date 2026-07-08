"""Explicit spatial state interface shared by Stage 1.5 and future Stage 2."""

import torch
import torch.nn as nn


class SpatialStateProjector(nn.Module):
    """Project conditioned ViT tokens into a stable state-token space."""

    def __init__(self, in_dim: int = 384, state_dim: int = 256, hidden_dim: int = 512):
        super().__init__()
        self.in_dim = in_dim
        self.state_dim = state_dim
        self.net = nn.Sequential(
            nn.LayerNorm(in_dim),
            nn.Linear(in_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, state_dim),
            nn.LayerNorm(state_dim),
        )

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        return self.net(tokens)

    @staticmethod
    def pool(state_tokens: torch.Tensor) -> torch.Tensor:
        return state_tokens.mean(dim=1)

    def get_config(self) -> dict:
        return {"in_dim": self.in_dim, "state_dim": self.state_dim}
