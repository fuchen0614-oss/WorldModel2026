"""Shared observation/state/geo/decoder core for formal Stage2-v2 models."""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from data.earthnet_fields import make_neutral_s2_phi
from data.stage2_contract import assert_model_batch_has_no_evaluation_fields


class ObsWorldV2Core(nn.Module):
    """Own the parts that Direct24, rollout, and partition must share.

    The core intentionally does not consume future target pixels, target masks,
    or official evaluation masks.  Its state initializer sees only history;
    transition wrappers then decide how an allowed future D/C/delta-t path is
    traversed.
    """

    def __init__(
        self,
        *,
        band_adapter: nn.Module,
        encoder: nn.Module,
        phi_encoder: Optional[nn.Module],
        state_projector: nn.Module,
        context_aggregator: nn.Module,
        geo_tokenizer: nn.Module,
        decoder: nn.Module,
        use_phi_encoder: bool = True,
    ):
        super().__init__()
        self.band_adapter = band_adapter
        self.encoder = encoder
        self.phi_encoder = phi_encoder
        self.state_projector = state_projector
        self.context_aggregator = context_aggregator
        self.geo_tokenizer = geo_tokenizer
        self.decoder = decoder
        self.use_phi_encoder = bool(use_phi_encoder)

        # The EarthNet main task has no compatible per-frame acquisition
        # metadata.  This fixed neutral reference preserves Stage1.5 encoder
        # compatibility without pretending that phi is an active Stage2 input.
        if self.phi_encoder is not None:
            self.phi_encoder.requires_grad_(False)
        if hasattr(self.encoder, "patch_embed") and hasattr(
            self.encoder.patch_embed, "s1_proj"
        ):
            self.encoder.patch_embed.s1_proj.requires_grad_(False)
        if hasattr(self.encoder, "modality_embed_s1"):
            self.encoder.modality_embed_s1.requires_grad_(False)

    def encode_observations(
        self,
        observations: torch.Tensor,
        pixel_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Encode ``[B,T,4,H,W]`` observations to ``[B,T,N,Dz]`` states."""

        if observations.dim() != 5:
            raise ValueError(
                "observations must be [B,T,C,H,W], got "
                f"{tuple(observations.shape)}"
            )
        batch, frames, _, height, width = observations.shape
        x = observations
        if pixel_mask is not None:
            if pixel_mask.shape != (batch, frames, height, width):
                raise ValueError(
                    "pixel_mask must match observations as [B,T,H,W], got "
                    f"{tuple(pixel_mask.shape)}"
                )
            x = x * pixel_mask.to(dtype=x.dtype, device=x.device).unsqueeze(2)
        adapted = self.band_adapter(x)
        flat = adapted.reshape(batch * frames, adapted.shape[2], height, width)

        phi_embedding = None
        if self.use_phi_encoder and self.phi_encoder is not None:
            neutral_phi = make_neutral_s2_phi(batch * frames, flat.device)
            phi_embedding = self.phi_encoder(neutral_phi)
        tokens, _, _ = self.encoder(
            flat,
            "S2",
            mask_ratio=0.0,
            phi_embed=phi_embedding,
        )
        states = self.state_projector(tokens)
        return states.reshape(batch, frames, states.shape[1], states.shape[2])

    def initialize_state(self, batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        """Build a context-only belief state and continuous token coverage."""

        assert_model_batch_has_no_evaluation_fields(batch)
        for name in ("x_context", "context_mask"):
            if name not in batch:
                raise KeyError(f"Stage2-v2 core is missing {name!r}")
        x_context = batch["x_context"]
        context_mask = batch["context_mask"]
        context_states = self.encode_observations(x_context, context_mask)
        coverage = pixel_mask_to_token_coverage(
            context_mask,
            context_states.shape[2],
        )
        try:
            state, state_valid_mask = self.context_aggregator(
                context_states,
                coverage,
                return_valid_mask=True,
            )
        except TypeError as exc:
            raise TypeError(
                "Formal Stage2-v2 requires a coverage-aware ContextStateAggregator; "
                "update models/dynamics/context_state_aggregator.py first"
            ) from exc
        return {
            "state": state,
            "state_valid_mask": state_valid_mask,
            "context_token_coverage": coverage,
            "context_states": context_states,
        }

    def encode_geo(
        self,
        geo: torch.Tensor,
        geo_mask: Optional[torch.Tensor],
        *,
        expected_tokens: int,
    ) -> torch.Tensor:
        """Encode G and verify it is token-aligned with the state grid."""

        tokens = self.geo_tokenizer(geo, geo_mask)
        if tokens.shape[1] != expected_tokens:
            raise ValueError(
                "GeoTokenizer token count must match context state token count: "
                f"geo={tokens.shape[1]}, state={expected_tokens}. Configure "
                "the v2 128/8 geo grid to match the 256/16 observation grid."
            )
        return tokens

    def decode_states(self, states: torch.Tensor) -> dict[str, torch.Tensor]:
        """Decode one state or a time sequence without changing its order."""

        if states.dim() == 3:
            return self.decoder(states)
        if states.dim() != 4:
            raise ValueError(f"states must be [B,N,D] or [B,T,N,D], got {tuple(states.shape)}")
        batch, steps, tokens, dim = states.shape
        decoded = self.decoder(states.reshape(batch * steps, tokens, dim))
        out: dict[str, torch.Tensor] = {}
        for name, value in decoded.items():
            out[name] = value.reshape(batch, steps, *value.shape[1:])
        return out


def pixel_mask_to_token_coverage(pixel_mask: torch.Tensor, num_tokens: int) -> torch.Tensor:
    """Pool clear-pixel fractions into the square state-token grid."""

    if pixel_mask.dim() != 4:
        raise ValueError(
            f"pixel_mask must be [B,T,H,W], got {tuple(pixel_mask.shape)}"
        )
    grid = int(round(num_tokens ** 0.5))
    if grid * grid != num_tokens:
        raise ValueError(f"Cannot map {num_tokens} state tokens onto a square grid")
    batch, frames, height, width = pixel_mask.shape
    coverage = F.adaptive_avg_pool2d(
        pixel_mask.reshape(batch * frames, 1, height, width).float(),
        output_size=(grid, grid),
    )
    return coverage.reshape(batch, frames, num_tokens).clamp(0.0, 1.0)
