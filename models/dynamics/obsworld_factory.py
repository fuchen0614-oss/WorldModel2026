"""Factories for formal Stage2-v2 model variants.

The old ``ObsWorldStage2Model`` remains the legacy 9-D Direct-DGH baseline.
This factory is deliberately separate so a config cannot silently turn an old
checkpoint/model class into a path-based world-model run merely by changing a
string called ``mode``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

from models.adapters.earthnet_band_adapter import EarthNetInputAdapter
from models.adapters.geo_tokenizer import GeoTokenizer
from models.decoders.earthnet_observation_decoder import EarthNetObservationDecoder
from models.decoders.light_decoder import LightDecoder
from models.encoders.multimodal_vit_encoder_film import MultiModalViTEncoderFiLM
from models.encoders.pure_imaging_condition_encoder import PureImagingConditionEncoder
from models.encoders.state_projection import SpatialStateProjector

from .condition_encoders import HorizonEncoder
from .context_state_aggregator import ContextStateAggregator
from .controlled_transition import ControlledTransition
from .interval_driver_encoder import IntervalDriverEncoder
from data.earthnet_conditioning import FULL24_FEATURE_NAMES
from data.earthnet_physical_conditioning import PHYSICAL4_FEATURE_NAMES, is_physical4_protocol
from .obsworld_core import ObsWorldV2Core
from .obsworld_direct_path import ObsWorldDirectPathModel
from .obsworld_partition import ObsWorldPartitionModel
from .obsworld_rollout import ObsWorldRolloutModel
from .obsworld_correction import ObsWorldCorrectionModel
from .state_dynamics_module import StateDynamicsModule


V2_DIRECT_MODES = frozenset({
    "direct_path", "direct_path_24d", "direct24", "direct_path_physical4",
})
V2_ROLLOUT_MODES = frozenset({
    "rollout", "rollout_t5", "rollout_t5_24d", "rollout_t5_physical4",
})
V2_CORRECTION_MODES = frozenset({
    "rollout_t5_24d_correction",
    "rollout_t5_physical4_correction",
})
V2_PARTITION_MODES = frozenset(
    {"obsworld_partition_24d", "obsworld_partition_physical4", "rollout_partition", "partition"}
)
V2_DRIVER_PROTOCOLS = frozenset({"full24", "physical4_v1"})


def create_obsworld_v2_model(
    config: dict[str, Any],
    device: torch.device | str = "cpu",
) -> nn.Module:
    """Create the formal path-based Direct24 model from an explicit v2 config."""

    data_cfg = config.get("data", {})
    if str(data_cfg.get("stage2_protocol", "")).lower() not in {
        "earthnet2021x_path_v2",
        "earthnet_path_v2",
        "path_v2",
    }:
        raise ValueError(
            "create_obsworld_v2_model requires data.stage2_protocol="
            "earthnet2021x_path_v2 (or its explicit alias)"
        )
    model_cfg = config.get("model", {})
    family = str(model_cfg.get("family", "obsworld_stage2_v2")).lower()
    if family != "obsworld_stage2_v2":
        raise ValueError(
            "Formal path factory requires model.family='obsworld_stage2_v2', "
            f"got {family!r}"
        )
    mode = str(model_cfg.get("forecast_mode", "direct_path_24d")).lower()
    if mode not in V2_DIRECT_MODES | V2_ROLLOUT_MODES | V2_CORRECTION_MODES | V2_PARTITION_MODES:
        raise ValueError(
            "Stage2-v2 currently implements Direct24, five-day open-loop "
            "rollout, observation-correction rollout, and 10-day-vs-5+5 "
            "partition rollout; "
            f"unsupported forecast_mode={mode!r}"
        )
    driver_protocol = str(model_cfg.get("driver_protocol", "full24")).lower()
    if is_physical4_protocol(driver_protocol):
        driver_protocol = "physical4_v1"
    elif driver_protocol in {"full24", "eobs24", "full_24"}:
        driver_protocol = "full24"
    else:
        raise ValueError(
            "Stage2-v2 supports only the explicit full24 or physical4_v1 driver path; "
            f"got model.driver_protocol={driver_protocol!r}."
        )
    data_driver_protocol = str(data_cfg.get("driver_protocol", "full24")).lower()
    if is_physical4_protocol(data_driver_protocol):
        data_driver_protocol = "physical4_v1"
    elif data_driver_protocol in {"full24", "eobs24", "full_24"}:
        data_driver_protocol = "full24"
    if data_driver_protocol != driver_protocol:
        raise ValueError(
            "model.driver_protocol and data.driver_protocol must match: "
            f"model={driver_protocol!r}, data={data_driver_protocol!r}"
        )

    encoder_cfg = _component_config(model_cfg, "encoder", excluded={
        "type", "from_checkpoint", "freeze", "unfreeze_at_step",
        "unfreeze_last_blocks", "unfreeze_state_projector",
    })
    phi_cfg = _component_config(model_cfg, "phi_encoder", excluded={"type"})
    state_cfg = _component_config(model_cfg, "state_projector", excluded={"type"})
    band_cfg = _component_config(model_cfg, "band_adapter", excluded={"type"})
    context_cfg = _component_config(model_cfg, "context_aggregator", excluded={"type"})
    geo_cfg = _component_config(model_cfg, "geo_tokenizer", excluded={"type"})
    interval_cfg = _component_config(
        model_cfg,
        "interval_driver_encoder",
        excluded={"type"},
    )
    expected_driver_names = (
        PHYSICAL4_FEATURE_NAMES if driver_protocol == "physical4_v1" else FULL24_FEATURE_NAMES
    )
    interval_cfg.setdefault("input_dim", len(expected_driver_names))
    interval_cfg.setdefault("feature_names", list(expected_driver_names))
    horizon_cfg = _component_config(model_cfg, "horizon_encoder", excluded={"type"})
    dynamics_cfg = _component_config(model_cfg, "dynamics", excluded={"type"})
    decoder_cfg = _component_config(model_cfg, "decoder", excluded={"type"})

    encoder = MultiModalViTEncoderFiLM(**encoder_cfg)
    phi_encoder = PureImagingConditionEncoder(**phi_cfg)
    state_projector = SpatialStateProjector(**state_cfg)
    band_adapter = EarthNetInputAdapter(**band_cfg)
    context_aggregator = ContextStateAggregator(**context_cfg)
    geo_tokenizer = GeoTokenizer(**geo_cfg)
    interval_encoder = IntervalDriverEncoder(**interval_cfg)
    horizon_encoder = HorizonEncoder(**horizon_cfg)
    dynamics = StateDynamicsModule(**dynamics_cfg)
    decoder = EarthNetObservationDecoder(**decoder_cfg)
    _validate_v2_dimensions(
        encoder,
        state_projector,
        context_aggregator,
        geo_tokenizer,
        interval_encoder,
        horizon_encoder,
        dynamics,
        decoder,
    )

    checkpoint_path = model_cfg.get("encoder", {}).get("from_checkpoint")
    if checkpoint_path:
        load_stage15_modules(
            checkpoint_path,
            encoder=encoder,
            phi_encoder=phi_encoder,
            state_projector=state_projector,
        )

    conditions = model_cfg.get("conditions", {})
    ndvi_head = None
    if bool(model_cfg.get("ndvi_head", False)):
        # A' NDVI residual head: same token->pixel decoder geometry as O, one
        # output channel (NDVI delta), no output activation (raw residual; the
        # core bounds it with tanh and a zero-init scale on a last-valid NDVI base).
        ndvi_head = LightDecoder(
            in_dim=decoder_cfg["in_dim"],
            out_channels=1,
            patch_size=decoder_cfg["patch_size"],
            img_size=decoder_cfg["img_size"],
            depth=int(decoder_cfg.get("depth", 3)),
            num_heads=int(decoder_cfg.get("num_heads", 4)),
            decoder_embed_dim=int(decoder_cfg.get("decoder_embed_dim", 192)),
            mlp_ratio=float(decoder_cfg.get("mlp_ratio", 4.0)),
            dropout=float(decoder_cfg.get("dropout", 0.0)),
            decoder_mode=str(decoder_cfg.get("decoder_mode", "transformer")),
        )
    core = ObsWorldV2Core(
        band_adapter=band_adapter,
        encoder=encoder,
        phi_encoder=phi_encoder,
        state_projector=state_projector,
        context_aggregator=context_aggregator,
        geo_tokenizer=geo_tokenizer,
        decoder=decoder,
        use_phi_encoder=bool(model_cfg.get("use_phi_encoder", True)),
        ndvi_head=ndvi_head,
    )
    transition = ControlledTransition(
        interval_driver_encoder=interval_encoder,
        horizon_encoder=horizon_encoder,
        state_dynamics=dynamics,
        use_D=bool(conditions.get("use_D", True)),
        use_G=bool(conditions.get("use_G", True)),
        use_h=bool(conditions.get("use_h", True)),
        residual_scale_init=float(model_cfg.get("residual_scale_init", 1.0)),
    )
    future_start_index = int(model_cfg.get("future_start_index", 10))
    target_steps = int(model_cfg.get("target_steps", 20))
    if (future_start_index, target_steps) != (10, 20):
        raise ValueError(
            "earthnet2021x_path_v2 freezes future_start_index=10 and "
            f"target_steps=20, got ({future_start_index}, {target_steps})"
        )
    if mode in V2_DIRECT_MODES:
        wrapper_cls = ObsWorldDirectPathModel
    elif mode in V2_ROLLOUT_MODES:
        wrapper_cls = ObsWorldRolloutModel
    elif mode in V2_CORRECTION_MODES:
        correction_cfg = model_cfg.get("observation_correction", {})
        if not isinstance(correction_cfg, dict):
            raise TypeError("model.observation_correction must be a mapping")
        model = ObsWorldCorrectionModel(
            core=core,
            transition=transition,
            forecast_mode=mode,
            future_start_index=future_start_index,
            target_steps=target_steps,
            strategy=str(correction_cfg.get("strategy", "u")),
            correction_hidden_dim=int(correction_cfg.get("hidden_dim", 128)),
            staleness_scale_days=float(correction_cfg.get("staleness_scale_days", 100.0)),
        )
        _configure_v2_freezing(model, model_cfg)
        return model.to(device)
    else:
        wrapper_cls = ObsWorldPartitionModel
    model = wrapper_cls(
        core=core,
        transition=transition,
        future_start_index=future_start_index,
        target_steps=target_steps,
    )
    _configure_v2_freezing(model, model_cfg)
    return model.to(device)


def _component_config(
    model_cfg: dict[str, Any],
    name: str,
    *,
    excluded: set[str],
) -> dict[str, Any]:
    if name not in model_cfg:
        raise KeyError(f"Formal Stage2-v2 config is missing model.{name}")
    value = model_cfg[name]
    if not isinstance(value, dict):
        raise TypeError(f"model.{name} must be a mapping")
    return {key: value for key, value in value.items() if key not in excluded}


def _validate_v2_dimensions(
    encoder: MultiModalViTEncoderFiLM,
    state_projector: SpatialStateProjector,
    context_aggregator: ContextStateAggregator,
    geo_tokenizer: GeoTokenizer,
    interval_encoder: IntervalDriverEncoder,
    horizon_encoder: HorizonEncoder,
    dynamics: StateDynamicsModule,
    decoder: EarthNetObservationDecoder,
) -> None:
    checks = (
        ("state_projector.state_dim", state_projector.state_dim, "dynamics.latent_dim", dynamics.latent_dim),
        ("context_aggregator.state_dim", context_aggregator.state_dim, "dynamics.latent_dim", dynamics.latent_dim),
        ("geo_tokenizer.geo_dim", geo_tokenizer.geo_dim, "dynamics.geo_dim", dynamics.geo_dim),
        ("interval_driver_encoder.out_dim", interval_encoder.out_dim, "dynamics.driver_dim", dynamics.driver_dim),
        ("horizon_encoder.out_dim", horizon_encoder.out_dim, "dynamics.time_dim", dynamics.time_dim),
        ("decoder input dim", decoder.decoder.in_dim, "dynamics.latent_dim", dynamics.latent_dim),
        (
            "encoder token count",
            encoder.get_num_patches(),
            "geo_tokenizer token count",
            geo_tokenizer.grid_size ** 2,
        ),
        (
            "encoder token count",
            encoder.get_num_patches(),
            "decoder token count",
            decoder.decoder.num_patches,
        ),
    )
    mismatches = [
        f"{left_name}={left} != {right_name}={right}"
        for left_name, left, right_name, right in checks
        if left != right
    ]
    if mismatches:
        raise ValueError("Invalid Stage2-v2 dimensions: " + "; ".join(mismatches))


def load_stage15_modules(
    checkpoint_path: str | Path,
    *,
    encoder: nn.Module,
    phi_encoder: nn.Module,
    state_projector: nn.Module,
) -> None:
    """Load only the three Stage1.5 modules that define the initializer."""

    source = Path(checkpoint_path)
    if not source.is_file():
        raise FileNotFoundError(f"Stage1.5 checkpoint not found: {source}")
    checkpoint = torch.load(source, map_location="cpu", weights_only=False)
    expected = {
        "encoder_state_dict": encoder,
        "phi_encoder_state_dict": phi_encoder,
        "state_projector_state_dict": state_projector,
    }
    missing = [name for name in expected if name not in checkpoint]
    if missing:
        raise KeyError(f"Stage1.5 checkpoint {source} is missing sections: {missing}")
    for name, module in expected.items():
        module.load_state_dict(checkpoint[name], strict=True)


def _configure_v2_freezing(model: nn.Module, model_cfg: dict[str, Any]) -> None:
    """Mirror Stage1.5 warmup policy without adding train-loop branches."""

    encoder_cfg = model_cfg.get("encoder", {})
    warmup_parameters: list[nn.Parameter] = []
    if bool(encoder_cfg.get("freeze", True)):
        model.core.encoder.requires_grad_(False)
        if model.core.phi_encoder is not None:
            model.core.phi_encoder.requires_grad_(False)
        model.core.state_projector.requires_grad_(False)
        blocks_to_unfreeze = int(encoder_cfg.get("unfreeze_last_blocks", 0))
        if blocks_to_unfreeze:
            if not hasattr(model.core.encoder, "blocks"):
                raise AttributeError("Encoder has no blocks for progressive unfreezing")
            for block in model.core.encoder.blocks[-blocks_to_unfreeze:]:
                block.requires_grad_(True)
                warmup_parameters.extend(block.parameters())
        if bool(encoder_cfg.get("unfreeze_state_projector", True)):
            model.core.state_projector.requires_grad_(True)
            warmup_parameters.extend(model.core.state_projector.parameters())

    # These two modules are structurally bypassed by their ablations. Freeze
    # them so DDP does not report an unused trainable parameter.
    if not model.transition.use_G:
        model.core.geo_tokenizer.requires_grad_(False)
    if not model.transition.use_h:
        model.transition.horizon_encoder.requires_grad_(False)
    object.__setattr__(model, "_warmup_frozen_parameters", list(warmup_parameters))
