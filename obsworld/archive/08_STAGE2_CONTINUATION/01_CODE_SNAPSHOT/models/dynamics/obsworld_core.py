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
        ndvi_head: Optional[nn.Module] = None,
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
        # Optional A' NDVI residual head O_ndvi(zh): decodes a bounded NDVI delta
        # on a history-only last-valid-NDVI baseline. The scale is initialised
        # SMALL BUT NON-ZERO so the untrained prediction is near-persistence yet
        # every NDVI-head weight receives gradient from step 1. A zero init makes
        # d(loss)/d(head) == 0 (tanh(0*r) has zero slope in the head), which is
        # fine on one GPU but crashes DDP (find_unused_parameters=False) because
        # the whole head is an unused parameter. Every correction is still read
        # from the transitioned state zh (no history bypass).
        self.ndvi_head = ndvi_head
        self.ndvi_residual_scale = (
            nn.Parameter(torch.full((), 0.1)) if ndvi_head is not None else None
        )
        if self.ndvi_head is not None and hasattr(self.ndvi_head, "mask_token"):
            # Mirror EarthNetObservationDecoder: the MAE mask token is never used
            # in full-sequence decoding, so it would be an unused parameter and
            # crash DDP (find_unused_parameters=False). Freeze it.
            self.ndvi_head.mask_token.requires_grad_(False)

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
            # Per-pixel last cloud-free reflectance, used as an optional decoder
            # baseline for residual prediction (Plan A). Never touches the state.
            "last_valid_rgbn": last_valid_pixels(x_context, context_mask),
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

    def decode_states(
        self,
        states: torch.Tensor,
        baseline: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        """Decode one state or a time sequence without changing its order.

        ``baseline`` (``[B,C,H,W]``) enables residual decoding: it is broadcast
        over any step dimension and added inside the decoder. ``None`` keeps the
        original absolute-decode behaviour, so existing models are unaffected.
        """

        if states.dim() == 3:
            if baseline is None:
                return self.decoder(states)
            return self.decoder(states, baseline=baseline)
        if states.dim() != 4:
            raise ValueError(f"states must be [B,N,D] or [B,T,N,D], got {tuple(states.shape)}")
        batch, steps, tokens, dim = states.shape
        flat = states.reshape(batch * steps, tokens, dim)
        if baseline is None:
            decoded = self.decoder(flat)
        else:
            flat_baseline = (
                baseline.unsqueeze(1)
                .expand(batch, steps, *baseline.shape[1:])
                .reshape(batch * steps, *baseline.shape[1:])
            )
            decoded = self.decoder(flat, baseline=flat_baseline)
        out: dict[str, torch.Tensor] = {}
        for name, value in decoded.items():
            out[name] = value.reshape(batch, steps, *value.shape[1:])
        return out

    def decode_ndvi(
        self,
        states: torch.Tensor,
        baseline_ndvi: torch.Tensor,
    ) -> torch.Tensor:
        """A' NDVI residual head: ndvi = clamp(baseline + tanh(scale*O_ndvi(z)), -1, 1).

        ``states`` is ``[B,N,D]`` or ``[B,T,N,D]``; ``baseline_ndvi`` is the
        history-only last-valid NDVI (``[B,Hc,Wc]`` or ``[B,1,Hc,Wc]``), broadcast
        over steps and bilinearly resized to the head grid. The zero-initialised
        scale makes the untrained prediction exactly persistence, and the
        correction is read only from the transitioned state (no history bypass).
        """

        if self.ndvi_head is None or self.ndvi_residual_scale is None:
            raise RuntimeError("decode_ndvi called but no NDVI head was configured")
        squeeze = states.dim() == 3
        if squeeze:
            states = states.unsqueeze(1)
        batch, steps, tokens, dim = states.shape
        residual = self.ndvi_head(states.reshape(batch * steps, tokens, dim))
        if isinstance(residual, dict):
            residual = residual["mean"]
        residual = residual.reshape(batch, steps, *residual.shape[1:])  # [B,T,1,H,W]
        base = baseline_ndvi
        if base.dim() == 3:
            base = base.unsqueeze(1)  # [B,1,Hc,Wc]
        if base.shape[-2:] != residual.shape[-2:]:
            base = F.interpolate(
                base, size=residual.shape[-2:], mode="bilinear", align_corners=False
            )
        base = base.unsqueeze(1)  # [B,1,1,H,W] -> broadcasts over the step dim
        ndvi = (base + torch.tanh(self.ndvi_residual_scale * residual)).clamp(-1.0, 1.0)
        return ndvi.squeeze(1) if squeeze else ndvi


def last_valid_pixels(x_context: torch.Tensor, context_mask: torch.Tensor) -> torch.Tensor:
    """Per-pixel most-recent cloud-free reflectance over the context frames.

    ``x_context`` is ``[B,T,C,H,W]`` and ``context_mask`` is ``[B,T,H,W]`` with 1
    = clear.  For each pixel the latest clear frame is selected; pixels never
    clear fall back to the temporal mean.  Returns ``[B,C,H,W]`` (a persistence
    baseline for residual decoding; it never enters the latent state).
    """

    if x_context.dim() != 5:
        raise ValueError(f"x_context must be [B,T,C,H,W], got {tuple(x_context.shape)}")
    batch, frames, channels, height, width = x_context.shape
    mask = context_mask.to(dtype=x_context.dtype)  # [B,T,H,W]
    ramp = torch.arange(1, frames + 1, device=x_context.device, dtype=x_context.dtype)
    score = mask * ramp.view(1, frames, 1, 1)  # latest clear frame -> largest score
    last_idx = score.argmax(dim=1)  # [B,H,W]
    has_valid = mask.sum(dim=1) > 0  # [B,H,W]
    gather_idx = last_idx.view(batch, 1, 1, height, width).expand(batch, 1, channels, height, width)
    latest = torch.gather(x_context, 1, gather_idx).squeeze(1)  # [B,C,H,W]
    mean_ctx = x_context.mean(dim=1)  # [B,C,H,W]
    return torch.where(has_valid.unsqueeze(1), latest, mean_ctx)


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
