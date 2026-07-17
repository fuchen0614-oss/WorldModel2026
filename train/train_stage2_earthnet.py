"""Train ObsWorld Stage 2 on EarthNet2021 standard forecasting."""

from __future__ import annotations

import argparse
import copy
from contextlib import nullcontext
from dataclasses import dataclass, field
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
import torch.distributed as dist
import torch.nn as nn
import torch.optim as optim
import yaml
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, Subset
from torch.utils.data.distributed import DistributedSampler

try:
    from torch.utils.tensorboard import SummaryWriter
except ImportError:
    SummaryWriter = None

try:
    from tqdm import tqdm
except ImportError:
    class _NullProgress:
        def __init__(self, *args, **kwargs):
            pass

        def update(self, *args, **kwargs):
            pass

        def set_postfix(self, *args, **kwargs):
            pass

    def tqdm(iterable=None, *args, **kwargs):
        return iterable if iterable is not None else _NullProgress()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import (
    EarthNet2021Config,
    EarthNet2021Dataset,
    collate_earthnet2021,
    resize_stage2_v2_context_on_device,
)
from data.earthnet_conditioning import FULL24_FEATURE_NAMES, is_stage2_v2_protocol
from data.earthnet_physical_conditioning import PHYSICAL4_FEATURE_NAMES, PHYSICAL4_PROTOCOL
from data.stage2_contract import is_stage2_v2_batch, model_input_view
from models.adapters.earthnet_band_adapter import EarthNetInputAdapter
from models.adapters.geo_tokenizer import GeoTokenizer
from models.decoders.earthnet_observation_decoder import EarthNetObservationDecoder
from models.dynamics.context_state_aggregator import ContextStateAggregator
from models.dynamics.condition_encoders import DriverEncoder, HorizonEncoder
from models.dynamics.obsworld_factory import create_obsworld_v2_model
from models.dynamics.partition_consistency import (
    PartitionConsistencyLoss,
    sample_two_step_partition_start,
)
from models.dynamics.obsworld_stage2 import ObsWorldStage2Model
from models.dynamics.state_dynamics_module import StateDynamicsModule
from models.encoders.multimodal_vit_encoder_film import MultiModalViTEncoderFiLM
from models.encoders.pure_imaging_condition_encoder import PureImagingConditionEncoder
from models.encoders.state_projection import SpatialStateProjector
from models.losses.earthnet_forecasting import EarthNetForecastLoss
from eval.forecast_metrics import ForecastMetricAccumulator
from train.stage2_curriculum import (
    curriculum_checkpoint_state,
    current_rollout_length,
    is_direct_forecast_mode,
    is_partition_forecast_mode,
    is_observation_correction_mode,
    is_rollout_forecast_mode,
    partition_loss_scale,
    partition_training_settings,
)
from train.observation_correction_schedule import build_observation_correction_inputs
from train.stage2_checkpoint import (
    EpochRandomSampler,
    Stage2DataPosition,
    next_data_position,
    parse_epoch_checkpoint_epochs,
    parse_epoch_checkpoint_steps,
    restore_data_position,
)
from train.stage2_provenance import (
    atomic_torch_save,
    build_stage2_run_provenance,
    write_run_provenance,
)
from train.fsdp_utils import barrier, cleanup_distributed, is_main_process, setup_distributed


def log_main(message: str) -> None:
    if is_main_process():
        print(message, flush=True)


def load_config(path: str) -> dict:
    """Load YAML, optionally deep-merging a nearby ``_base_`` configuration.

    Stage2 variants differ mainly in forecast wrapper and training losses.  A
    small explicit inheritance mechanism keeps Direct24/Rollout/Partition
    configs matched rather than inviting a silent drift in decoder width or
    data protocol.  Lists are intentionally replaced, not concatenated.
    """

    return _load_config_path(Path(path), ancestors=())


def _load_config_path(path: Path, *, ancestors: tuple[Path, ...]) -> dict:
    source = path.expanduser().resolve()
    if source in ancestors:
        chain = " -> ".join(str(item) for item in (*ancestors, source))
        raise ValueError(f"Cyclic Stage2 config _base_ chain: {chain}")
    with source.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"Config {source} must be a top-level mapping")
    base = payload.pop("_base_", None)
    if base is None:
        return payload
    if not isinstance(base, str) or not base.strip():
        raise TypeError(f"Config {source} _base_ must be a non-empty relative path")
    base_path = (source.parent / base).resolve()
    inherited = _load_config_path(base_path, ancestors=(*ancestors, source))
    return _deep_merge_config(inherited, payload)


def _deep_merge_config(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_config(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def move_batch_to_device(batch: dict, device: torch.device) -> dict:
    """Move tensor leaves recursively while leaving metadata on the CPU.

    The current EarthNet batch is shallow, but formal Stage2 deliberately
    leaves room for a future nested acquisition-condition dictionary.  Moving
    only top-level values would then fail late with a CPU/GPU device mismatch.
    """

    return _move_value_to_device(batch, device)


def _move_value_to_device(value, device: torch.device):
    if torch.is_tensor(value):
        return value.to(device, non_blocking=True)
    if isinstance(value, dict):
        return {key: _move_value_to_device(item, device) for key, item in value.items()}
    if isinstance(value, list):
        return [_move_value_to_device(item, device) for item in value]
    if isinstance(value, tuple):
        return tuple(_move_value_to_device(item, device) for item in value)
    return value


def prepare_stage2_batch_for_model(
    batch: dict,
    data_cfg: EarthNet2021Config,
) -> dict:
    """Apply GPU-side, protocol-preserving input preparation when requested."""

    if (
        is_stage2_v2_protocol(data_cfg.stage2_protocol)
        and data_cfg.defer_context_resize_to_device
    ):
        return resize_stage2_v2_context_on_device(
            batch,
            context_img_size=int(data_cfg.context_img_size or data_cfg.model_img_size),
        )
    return batch


@dataclass
class Stage2PerformanceWindow:
    """Low-overhead timing window emitted only at the logging interval.

    ``data_wait_s`` is host wall time spent waiting for the next DataLoader
    batch.  CUDA events separately measure H2D transfer, optional GPU-side
    input preparation, and forward/backward/optimizer execution.  Event
    completion is synchronized only when the window is reported, not per
    optimizer step.
    """

    start_time: float = field(default_factory=time.perf_counter)
    data_wait_s: float = 0.0
    local_sample_count: int = 0
    optimizer_updates: int = 0
    transfer_events: list[tuple[Any, Any]] = field(default_factory=list)
    input_events: list[tuple[Any, Any]] = field(default_factory=list)
    compute_events: list[tuple[Any, Any]] = field(default_factory=list)

    def add_cuda_events(
        self,
        *,
        transfer: Optional[tuple[Any, Any]],
        input_prepare: Optional[tuple[Any, Any]],
        compute: Optional[tuple[Any, Any]],
    ) -> None:
        if transfer is not None:
            self.transfer_events.append(transfer)
        if input_prepare is not None:
            self.input_events.append(input_prepare)
        if compute is not None:
            self.compute_events.append(compute)

    @staticmethod
    def _event_seconds(events: list[tuple[Any, Any]]) -> float:
        return sum(start.elapsed_time(end) for start, end in events) / 1000.0

    def summarize(self, *, device: torch.device, world_size: int) -> dict[str, float]:
        """Return global slowest-rank timing and global sample throughput."""

        wall_time_s = time.perf_counter() - self.start_time
        if device.type == "cuda":
            # [PROFILE] Resolve all events together at the reporting cadence.
            torch.cuda.synchronize(device)
            transfer_time_s = self._event_seconds(self.transfer_events)
            input_time_s = self._event_seconds(self.input_events)
            compute_time_s = self._event_seconds(self.compute_events)
        else:
            transfer_time_s = 0.0
            input_time_s = 0.0
            compute_time_s = 0.0

        timings = torch.tensor(
            [
                self.data_wait_s,
                transfer_time_s,
                input_time_s,
                compute_time_s,
                wall_time_s,
            ],
            dtype=torch.float64,
            device=device,
        )
        samples = torch.tensor(
            float(self.local_sample_count), dtype=torch.float64, device=device
        )
        if dist.is_available() and dist.is_initialized():
            # DDP step rate is dictated by the slowest rank, while samples are
            # the sum across ranks.
            dist.all_reduce(timings, op=dist.ReduceOp.MAX)
            dist.all_reduce(samples, op=dist.ReduceOp.SUM)

        updates = max(self.optimizer_updates, 1)
        data_s, transfer_s, input_s, compute_s, wall_s = timings.detach().cpu().tolist()
        global_samples = float(samples.item())
        return {
            "data_wait_s_per_update": data_s / updates,
            "h2d_s_per_update": transfer_s / updates,
            "gpu_input_s_per_update": input_s / updates,
            "gpu_compute_s_per_update": compute_s / updates,
            "wall_s_per_update": wall_s / updates,
            "global_samples_per_s": global_samples / max(wall_s, 1e-12),
        }


def format_stage2_training_progress(
    *,
    step: int,
    max_steps: int,
    epoch: int,
    losses: dict[str, float],
    learning_rates: list[float],
    performance: dict[str, float],
) -> str:
    """Render one concise, grep-friendly Stage2 progress line."""

    def loss_value(name: str) -> str:
        value = losses.get(name)
        return "n/a" if value is None else f"{value:.5f}"

    return (
        f"train step={step}/{max_steps} epoch={epoch + 1} "
        f"loss={loss_value('total')} obs={loss_value('obs')} ndvi={loss_value('ndvi')} "
        f"lr={learning_rates[0]:.3e} "
        f"data={performance['data_wait_s_per_update']:.3f}s "
        f"h2d={performance['h2d_s_per_update']:.3f}s "
        f"gpu_input={performance['gpu_input_s_per_update']:.3f}s "
        f"gpu_compute={performance['gpu_compute_s_per_update']:.3f}s "
        f"wall={performance['wall_s_per_update']:.3f}s "
        f"throughput={performance['global_samples_per_s']:.1f} samples/s"
    )


def reduce_stage2_loss_scalars(losses: dict[str, torch.Tensor]) -> dict[str, float]:
    """Average scalar losses across DDP ranks only at log time."""

    names = sorted(
        name
        for name, value in losses.items()
        if torch.is_tensor(value) and value.numel() == 1
    )
    if not names:
        return {}
    values = torch.stack([losses[name].detach().float() for name in names])
    if dist.is_available() and dist.is_initialized():
        dist.all_reduce(values, op=dist.ReduceOp.SUM)
        values /= dist.get_world_size()
    return dict(zip(names, values.detach().cpu().tolist()))


def build_stage2_train_loader(
    dataset,
    *,
    sampler,
    batch_size: int,
    num_workers: int,
    epoch: int,
    process_seed: int,
    prefetch_factor: int = 2,
    persistent_workers: bool = True,
) -> DataLoader:
    """Create a deterministic Stage2 loader without advancing global RNG.

    The sampler's permutation is a pure ``seed + epoch`` function.  It is
    updated by the outer training loop, while keeping worker processes alive
    across epochs avoids repeated xarray imports and NetCDF-worker startup.
    EarthNet Stage2 has no stochastic worker-side augmentation, so persistent
    workers do not alter the frozen data order or resume semantics.
    """

    if hasattr(sampler, "set_epoch"):
        sampler.set_epoch(epoch)
    if num_workers < 0:
        raise ValueError(f"num_workers must be non-negative, got {num_workers}")
    if prefetch_factor <= 0:
        raise ValueError(f"prefetch_factor must be positive, got {prefetch_factor}")
    loader_generator = torch.Generator()
    loader_generator.manual_seed(int(process_seed))
    loader_kwargs = {
        "batch_size": batch_size,
        "sampler": sampler,
        "shuffle": False,
        "num_workers": num_workers,
        "pin_memory": True,
        "drop_last": True,
        "collate_fn": collate_earthnet2021,
        "generator": loader_generator,
    }
    if num_workers > 0:
        # One prefetched B64 batch per worker is intentionally conservative:
        # it overlaps NetCDF decoding without multiplying NAS/RAM pressure.
        loader_kwargs["persistent_workers"] = bool(persistent_workers)
        loader_kwargs["prefetch_factor"] = int(prefetch_factor)
    return DataLoader(
        dataset,
        **loader_kwargs,
    )


def forward_stage2_model(
    model: nn.Module,
    batch: dict,
    *,
    selected_steps: Optional[torch.Tensor] = None,
    max_rollout_steps: Optional[int] = None,
    partition_start: Optional[int] = None,
    detach_partition_start: bool = True,
    correction_inputs: Optional[dict[str, torch.Tensor]] = None,
) -> dict:
    """Forward only the protocol-approved batch partition through the model."""

    raw_model = model.module if isinstance(model, DDP) else model
    include_targets = bool(getattr(raw_model, "compute_latent_targets", False))
    inputs = model_input_view(batch, include_training_targets=include_targets)
    forecast_mode = getattr(raw_model, "forecast_mode", None)
    if is_direct_forecast_mode(forecast_mode):
        if max_rollout_steps is not None or partition_start is not None:
            raise ValueError("Direct24 does not accept rollout or partition arguments")
        return model(inputs, selected_steps=selected_steps)
    if is_partition_forecast_mode(forecast_mode):
        return model(
            inputs,
            selected_steps=selected_steps,
            max_rollout_steps=max_rollout_steps,
            partition_start=partition_start,
            detach_partition_start=detach_partition_start,
        )
    if is_observation_correction_mode(forecast_mode):
        if partition_start is not None:
            raise ValueError("Observation correction cannot be combined with a partition branch")
        return model(
            inputs,
            selected_steps=selected_steps,
            max_rollout_steps=max_rollout_steps,
            correction_inputs=correction_inputs,
        )
    if is_rollout_forecast_mode(forecast_mode):
        if partition_start is not None:
            raise ValueError(
                "A plain rollout wrapper cannot receive a partition branch; "
                "use forecast_mode=obsworld_partition_24d."
            )
        return model(
            inputs,
            selected_steps=selected_steps,
            max_rollout_steps=max_rollout_steps,
        )
    if selected_steps is not None:
        raise ValueError(
            "selected_steps is supported only by the Stage2-v2 Direct24 model; "
            "legacy Direct-DGH must use select_horizons()."
        )
    return model(inputs)


def create_stage2_model(config: dict, device: torch.device) -> nn.Module:
    if is_stage2_v2_protocol(config.get("data", {}).get("stage2_protocol", "")):
        return create_obsworld_v2_model(config, device)
    model_cfg = config["model"]
    enc_cfg = {k: v for k, v in model_cfg["encoder"].items()
               if k not in {
                   "type",
                   "from_checkpoint",
                   "freeze",
                   "unfreeze_at_step",
                   "unfreeze_last_blocks",
                   "unfreeze_state_projector",
               }}
    phi_cfg = {k: v for k, v in model_cfg["phi_encoder"].items() if k != "type"}
    state_cfg = {k: v for k, v in model_cfg["state_projector"].items() if k != "type"}
    adapter_cfg = {k: v for k, v in model_cfg["band_adapter"].items() if k != "type"}
    geo_cfg = {k: v for k, v in model_cfg["geo_tokenizer"].items() if k != "type"}
    agg_cfg = {k: v for k, v in model_cfg["context_aggregator"].items() if k != "type"}
    driver_cfg = {k: v for k, v in model_cfg["driver_encoder"].items() if k != "type"}
    horizon_cfg = {k: v for k, v in model_cfg["horizon_encoder"].items() if k != "type"}
    dyn_cfg = {k: v for k, v in model_cfg["dynamics"].items() if k != "type"}
    dec_cfg = {k: v for k, v in model_cfg["decoder"].items() if k != "type"}

    encoder = MultiModalViTEncoderFiLM(**enc_cfg)
    phi_encoder = PureImagingConditionEncoder(**phi_cfg)
    state_projector = SpatialStateProjector(**state_cfg)
    band_adapter = EarthNetInputAdapter(**adapter_cfg)
    geo_tokenizer = GeoTokenizer(**geo_cfg)
    context_aggregator = ContextStateAggregator(**agg_cfg)
    driver_encoder = DriverEncoder(**driver_cfg)
    horizon_encoder = HorizonEncoder(**horizon_cfg)
    dynamics = StateDynamicsModule(**dyn_cfg)
    decoder = EarthNetObservationDecoder(**dec_cfg)
    _validate_stage2_dimensions(
        state_projector,
        context_aggregator,
        driver_encoder,
        horizon_encoder,
        geo_tokenizer,
        dynamics,
        decoder,
    )

    ckpt_path = model_cfg["encoder"].get("from_checkpoint")
    if ckpt_path:
        load_stage15_checkpoint(ckpt_path, encoder, phi_encoder, state_projector)

    if bool(model_cfg["encoder"].get("freeze", True)):
        encoder.requires_grad_(False)
        phi_encoder.requires_grad_(False)
        state_projector.requires_grad_(False)
    conditions = model_cfg.get("conditions", {})
    if not bool(conditions.get("use_D", True)):
        driver_encoder.requires_grad_(False)
    if not bool(conditions.get("use_G", True)):
        geo_tokenizer.requires_grad_(False)
    if not bool(conditions.get("use_h", True)):
        horizon_encoder.requires_grad_(False)

    model = ObsWorldStage2Model(
        band_adapter=band_adapter,
        encoder=encoder,
        phi_encoder=phi_encoder,
        state_projector=state_projector,
        context_aggregator=context_aggregator,
        driver_encoder=driver_encoder,
        horizon_encoder=horizon_encoder,
        geo_tokenizer=geo_tokenizer,
        dynamics=dynamics,
        decoder=decoder,
        max_h_days=float(config["data"].get("max_h_days", 100.0)),
        use_phi_encoder=bool(model_cfg.get("use_phi_encoder", True)),
        compute_latent_targets=bool(model_cfg.get("compute_latent_targets", False)),
        use_D=bool(conditions.get("use_D", True)),
        use_G=bool(conditions.get("use_G", True)),
        use_h=bool(conditions.get("use_h", True)),
        mode=str(model_cfg.get("mode", "direct")),
    )
    warmup_frozen = []
    if bool(model_cfg["encoder"].get("freeze", True)):
        num_blocks = int(model_cfg["encoder"].get("unfreeze_last_blocks", 0))
        if num_blocks > 0:
            if not hasattr(encoder, "blocks"):
                raise AttributeError("Encoder has no blocks for progressive unfreezing")
            for block in encoder.blocks[-num_blocks:]:
                block.requires_grad_(True)
                warmup_frozen.extend(block.parameters())
        if bool(model_cfg["encoder"].get("unfreeze_state_projector", True)):
            state_projector.requires_grad_(True)
            warmup_frozen.extend(state_projector.parameters())
    object.__setattr__(model, "_warmup_frozen_parameters", list(warmup_frozen))
    return model.to(device)


def require_stage15_initializer_if_formal(config: dict, *, resume_from: Optional[str]) -> None:
    """Reject an accidental random-initializer formal v2 experiment.

    A synthetic smoke config may set ``require_stage15_checkpoint=false``.
    Paper-facing v2 configs set it true and must either name the frozen
    Stage1.5 checkpoint or resume an already complete Stage2 checkpoint.
    """

    if not is_stage2_v2_protocol(config.get("data", {}).get("stage2_protocol", "")):
        return
    if resume_from:
        return
    model_cfg = config.get("model", {})
    if not bool(model_cfg.get("require_stage15_checkpoint", False)):
        return
    checkpoint = model_cfg.get("encoder", {}).get("from_checkpoint")
    if not checkpoint:
        raise RuntimeError(
            "Formal Stage2-v2 requires the frozen Stage1.5 state-bridge "
            "checkpoint. Pass --stage15-checkpoint <checkpoint_step_*.pt> "
            "or set model.encoder.from_checkpoint; a random initializer is "
            "allowed only in an explicitly marked smoke config."
        )


def _validate_stage2_dimensions(
    state_projector,
    context_aggregator,
    driver_encoder,
    horizon_encoder,
    geo_tokenizer,
    dynamics,
    decoder,
) -> None:
    checks = [
        ("state_projector.state_dim", state_projector.state_dim, "dynamics.latent_dim", dynamics.latent_dim),
        ("context_aggregator.state_dim", context_aggregator.state_dim, "dynamics.latent_dim", dynamics.latent_dim),
        ("driver_encoder.out_dim", driver_encoder.out_dim, "dynamics.driver_dim", dynamics.driver_dim),
        ("horizon_encoder.out_dim", horizon_encoder.out_dim, "dynamics.time_dim", dynamics.time_dim),
        ("geo_tokenizer.geo_dim", geo_tokenizer.geo_dim, "dynamics.geo_dim", dynamics.geo_dim),
        ("decoder input dim", decoder.decoder.in_dim, "dynamics.latent_dim", dynamics.latent_dim),
    ]
    mismatches = [
        f"{left_name}={left} != {right_name}={right}"
        for left_name, left, right_name, right in checks
        if left != right
    ]
    if mismatches:
        raise ValueError("Invalid Stage2 dimensions: " + "; ".join(mismatches))


def load_stage15_checkpoint(path: str, encoder, phi_encoder, state_projector) -> None:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Stage1.5 checkpoint not found: {source}")
    checkpoint = torch.load(source, map_location="cpu", weights_only=False)
    required = {
        "encoder_state_dict": encoder,
        "phi_encoder_state_dict": phi_encoder,
        "state_projector_state_dict": state_projector,
    }
    missing_sections = [key for key in required if key not in checkpoint]
    if missing_sections:
        raise KeyError(
            f"Stage1.5 checkpoint {source} is missing required sections: {missing_sections}"
        )
    for key, module in required.items():
        module.load_state_dict(checkpoint[key], strict=True)
        log_main(f"loaded {key} from {source}")


def _upgrade_legacy_geo_tokenizer_state_dict(state_dict: dict) -> dict:
    """Map older GeoTokenizer parameter names onto the current module layout.

    Older Stage2 checkpoints used:
        LayerNorm(1) -> Linear -> GELU -> LayerNorm(geo_dim)
    The current GeoTokenizer removes the leading LayerNorm(1), so the learned
    Linear/LayerNorm parameters shift from proj.{1,3} to proj.{0,2}.
    """

    remapped = dict(state_dict)
    old_prefix = "geo_tokenizer.proj."
    if f"{old_prefix}1.weight" not in remapped and f"{old_prefix}3.weight" not in remapped:
        return remapped
    if f"{old_prefix}0.weight" in remapped and tuple(remapped[f"{old_prefix}0.weight"].shape) == (1,):
        remapped.pop(f"{old_prefix}0.weight", None)
        remapped.pop(f"{old_prefix}0.bias", None)
    if f"{old_prefix}1.weight" in remapped:
        remapped[f"{old_prefix}0.weight"] = remapped.pop(f"{old_prefix}1.weight")
    if f"{old_prefix}1.bias" in remapped:
        remapped[f"{old_prefix}0.bias"] = remapped.pop(f"{old_prefix}1.bias")
    if f"{old_prefix}3.weight" in remapped:
        remapped[f"{old_prefix}2.weight"] = remapped.pop(f"{old_prefix}3.weight")
    if f"{old_prefix}3.bias" in remapped:
        remapped[f"{old_prefix}2.bias"] = remapped.pop(f"{old_prefix}3.bias")
    return remapped


def load_stage2_model_state(model: nn.Module, checkpoint_state: dict, strict: bool = True) -> None:
    """Load a Stage2 checkpoint, including known backward-compatibility fixes."""

    model.load_state_dict(
        _upgrade_legacy_geo_tokenizer_state_dict(checkpoint_state),
        strict=strict,
    )


def build_optimizer(model: nn.Module, config: dict) -> optim.Optimizer:
    opt_cfg = config["optimizer"]
    warmup_ids = {
        id(parameter)
        for parameter in getattr(model, "_warmup_frozen_parameters", [])
    }
    new_params = [
        parameter
        for parameter in model.parameters()
        if parameter.requires_grad and id(parameter) not in warmup_ids
    ]
    backbone_params = [
        parameter
        for parameter in model.parameters()
        if parameter.requires_grad and id(parameter) in warmup_ids
    ]
    if not new_params and not backbone_params:
        raise RuntimeError("No trainable parameters found for Stage2.")
    groups = []
    if new_params:
        groups.append({"params": new_params, "lr": float(opt_cfg.get("lr", 1e-4))})
    if backbone_params:
        groups.append({
            "params": backbone_params,
            "lr": float(opt_cfg.get("backbone_lr", 1e-5)),
        })
    return optim.AdamW(
        groups,
        weight_decay=float(opt_cfg.get("weight_decay", 0.05)),
        betas=tuple(opt_cfg.get("betas", [0.9, 0.95])),
    )


def build_scheduler(optimizer, config: dict):
    train_cfg = config["training"]
    max_steps = int(train_cfg["max_steps"])
    warmup = int(train_cfg.get("warmup_steps", 1000))
    opt_cfg = config["optimizer"]
    new_lr = float(opt_cfg.get("lr", 1e-4))
    backbone_lr = float(opt_cfg.get("backbone_lr", new_lr))
    new_min_lr = float(opt_cfg.get("min_lr", 1e-6))
    backbone_min_lr = float(opt_cfg.get("backbone_min_lr", new_min_lr))

    def make_lambda(start_lr: float, end_lr: float):
        floor = end_lr / max(start_lr, 1e-12)

        def fn(step: int):
            if step < warmup:
                return (step + 1) / max(1, warmup)
            progress = min(1.0, (step - warmup) / max(1, max_steps - warmup))
            return floor + (1.0 - floor) * 0.5 * (
                1.0 + math.cos(progress * math.pi)
            )

        return fn

    lambdas = []
    for group in optimizer.param_groups:
        group_lr = float(group["lr"])
        end_lr = (
            backbone_min_lr
            if math.isclose(group_lr, backbone_lr, rel_tol=0.0, abs_tol=1e-15)
            else new_min_lr
        )
        lambdas.append(make_lambda(group_lr, end_lr))
    return optim.lr_scheduler.LambdaLR(optimizer, lambdas)


def suppress_backbone_warmup_gradients(model: nn.Module, optimizer_step: int, config: dict) -> None:
    unfreeze_at = int(
        config["model"]["encoder"].get("unfreeze_at_step", 0)
    )
    if optimizer_step >= unfreeze_at:
        return
    raw_model = model.module if isinstance(model, DDP) else model
    for parameter in getattr(raw_model, "_warmup_frozen_parameters", []):
        parameter.grad = None


def select_horizons(batch: dict, horizons_per_sample: int) -> dict:
    if horizons_per_sample <= 0:
        return batch
    tf = batch["x_target"].shape[1]
    if horizons_per_sample >= tf:
        return batch
    # Stratified short/mid/long sampling with deterministic shape per batch.
    thirds = [
        torch.arange(0, max(1, tf // 3)),
        torch.arange(max(1, tf // 3), max(2, 2 * tf // 3)),
        torch.arange(max(2, 2 * tf // 3), tf),
    ]
    selected = []
    for group in thirds:
        if len(group) > 0 and len(selected) < horizons_per_sample:
            selected.append(group[torch.randint(0, len(group), (1,)).item()])
    while len(selected) < horizons_per_sample:
        selected.append(torch.randint(0, tf, (1,)).item())
    idx = torch.tensor(sorted(set(int(i) for i in selected)), dtype=torch.long)
    # If dedup reduced count, pad randomly.
    while len(idx) < horizons_per_sample:
        extra = torch.randint(0, tf, (1,), dtype=torch.long)
        idx = torch.unique(torch.cat([idx, extra])).sort().values
    idx = idx[:horizons_per_sample]
    for key in ("x_target", "target_mask", "D", "D_mask", "h"):
        batch[key] = batch[key].index_select(1, idx.to(batch[key].device))
    return batch


def select_v2_horizon_indices(
    target_steps: int,
    horizons_per_sample: int,
    *,
    device: torch.device,
    always_include_last: bool = False,
) -> Optional[torch.Tensor]:
    """Choose Direct24 supervision endpoints without mutating the v2 batch.

    Direct24 needs the complete ``D_path`` to construct each legal prefix;
    slicing the batch in the legacy way would lose the first-future alignment.
    We therefore ask the model to decode a subset and slice *only* the
    supervision tensors afterwards.  ``always_include_last`` reserves the
    longest currently available endpoint (100 days once the curriculum reaches
    20) for the formal long-range evidence. Returning ``None`` means decode
    every currently available step, which is used by validation and early
    short-rollout curriculum phases.
    """

    if target_steps <= 0:
        raise ValueError(f"target_steps must be positive, got {target_steps}")
    if horizons_per_sample <= 0 or horizons_per_sample >= target_steps:
        return None

    # For the normal six-endpoint schedule choose short, mid, and long
    # horizons first, then fill the remainder uniformly without replacement.
    groups = (
        torch.arange(0, max(1, target_steps // 3), device=device),
        torch.arange(max(1, target_steps // 3), max(2, 2 * target_steps // 3), device=device),
        torch.arange(max(2, 2 * target_steps // 3), target_steps, device=device),
    )
    if horizons_per_sample == 1:
        group_order = (groups[2],)
    elif horizons_per_sample == 2:
        group_order = (groups[0], groups[2])
    else:
        group_order = groups
    chosen: list[int] = [target_steps - 1] if always_include_last else []
    for group in group_order:
        if len(chosen) >= horizons_per_sample or group.numel() == 0:
            continue
        candidates = [value for value in group.tolist() if int(value) not in chosen]
        if candidates:
            chosen.append(
                int(candidates[torch.randint(len(candidates), (1,), device=device).item()])
            )

    available = torch.tensor(
        [index for index in range(target_steps) if index not in chosen],
        device=device,
        dtype=torch.long,
    )
    if len(chosen) < horizons_per_sample:
        order = torch.randperm(available.numel(), device=device)
        chosen.extend(
            int(value)
            for value in available[order[: horizons_per_sample - len(chosen)]].tolist()
        )
    return torch.tensor(sorted(chosen), dtype=torch.long, device=device)


def stage2_supervision_for_output(batch: dict, output: dict) -> dict[str, Optional[torch.Tensor]]:
    """Align target tensors with a possibly sparse Direct24 model output.

    This is deliberately outside the model boundary: target pixels remain
    training supervision and cannot influence a Direct24 state prediction.
    """

    if "x_target" not in batch:
        raise KeyError("Stage2 training/validation batch is missing x_target")
    target = batch["x_target"]
    target_mask = batch.get("target_mask")
    horizons = batch.get("h")
    steps = output.get("step_indices")
    if steps is not None:
        steps = torch.as_tensor(steps, dtype=torch.long, device=target.device)
        if steps.dim() != 1 or steps.numel() == 0:
            raise ValueError("Direct24 output step_indices must be a non-empty [K] tensor")
        if torch.any(steps < 0) or torch.any(steps >= target.shape[1]):
            raise ValueError(
                "Direct24 output step_indices do not index the batch target horizon: "
                f"steps={steps.tolist()}, target_steps={target.shape[1]}"
            )
        target = target.index_select(1, steps)
        if target_mask is not None:
            target_mask = target_mask.index_select(1, steps)
        if horizons is not None:
            horizons = horizons.index_select(1, steps)
    if output["pred"].shape[:2] != target.shape[:2]:
        raise ValueError(
            "Stage2 output/target temporal shape mismatch: "
            f"pred={tuple(output['pred'].shape[:2])}, target={tuple(target.shape[:2])}"
        )
    return {
        "target": target,
        "target_mask": target_mask,
        "horizons": horizons,
    }


def partition_supervision_for_output(batch: dict, partition: dict) -> dict[str, torch.Tensor]:
    """Select the shared terminal target for a model-produced partition pair.

    The model exposes only its chosen endpoint index.  This helper performs
    all target/mask selection outside the model boundary, so the direct and
    composed state transitions cannot inspect future RGBN observations.
    """

    for name in ("x_target", "target_mask"):
        if name not in batch:
            raise KeyError(f"Partition supervision requires batch field {name!r}")
    if "endpoint_index" not in partition:
        raise KeyError("Partition model output is missing endpoint_index")
    target = batch["x_target"]
    target_mask = batch["target_mask"]
    endpoint_index = torch.as_tensor(
        partition["endpoint_index"],
        device=target.device,
        dtype=torch.long,
    )
    if endpoint_index.numel() != 1:
        raise ValueError(
            "Partition endpoint_index must contain one shared minibatch endpoint, "
            f"got shape {tuple(endpoint_index.shape)}"
        )
    endpoint_index = endpoint_index.reshape(1)
    if int(endpoint_index.item()) < 0 or int(endpoint_index.item()) >= target.shape[1]:
        raise ValueError(
            "Partition endpoint_index lies outside x_target: "
            f"endpoint={int(endpoint_index.item())}, target_steps={target.shape[1]}"
        )
    return {
        "target": target.index_select(1, endpoint_index).squeeze(1),
        "target_mask": target_mask.index_select(1, endpoint_index).squeeze(1),
        "endpoint_index": endpoint_index,
    }


def capture_rng_state() -> dict:
    """Capture this process's stochastic state for an exact future restart."""

    cuda_state = None
    if torch.cuda.is_available():
        device_index = torch.cuda.current_device()
        cuda_state = {
            "device_index": device_index,
            "state": torch.cuda.get_rng_state(device_index),
        }
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch.get_rng_state(),
        "cuda": cuda_state,
    }


def _gather_rng_states(local_state: dict) -> list[dict]:
    """Gather one RNG state per DDP rank before rank zero writes a checkpoint."""

    if not (dist.is_available() and dist.is_initialized()):
        return [local_state]
    states: list[object] = [None] * dist.get_world_size()
    dist.all_gather_object(states, local_state)
    if not all(isinstance(state, dict) for state in states):
        raise RuntimeError("Failed to gather one valid RNG state from every DDP rank")
    return list(states)  # type: ignore[return-value]


def save_checkpoint(
    path: str,
    step: int,
    model: nn.Module,
    optimizer,
    scheduler,
    config: dict,
    best_validation: Optional[dict] = None,
    provenance: Optional[dict] = None,
    data_position: Optional[Stage2DataPosition] = None,
) -> None:
    # All ranks must enter this function for a DDP checkpoint.  The former
    # rank-zero-only implementation restored rank zero's random stream on
    # every worker after a restart, which is not an exact distributed resume.
    local_rng_state = capture_rng_state()
    rng_states_by_rank = _gather_rng_states(local_rng_state)
    distributed_checkpoint = len(rng_states_by_rank) > 1
    if not is_main_process():
        if distributed_checkpoint:
            barrier()
        return
    raw_model = model.module if isinstance(model, DDP) else model
    payload = {
        "global_step": step,
        "model_state_dict": raw_model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "config": config,
        "best_validation": best_validation,
        "curriculum": curriculum_checkpoint_state(config, step),
        "provenance": provenance,
        "data_position": data_position.as_dict() if data_position is not None else None,
        # ``rng_state`` remains for compatibility with earlier single-process
        # checkpoints. ``rng_states_by_rank`` is the exact DDP representation.
        "rng_state": rng_states_by_rank[0],
        "rng_states_by_rank": rng_states_by_rank,
        "exact_resume": {
            "schema_version": 1,
            "rng_states_by_rank": len(rng_states_by_rank),
            "data_position": data_position is not None,
        },
    }
    atomic_torch_save(payload, path)
    log_main(f"checkpoint saved: {path}")
    if distributed_checkpoint:
        barrier()


def restore_rng_state(
    checkpoint: dict,
    *,
    rank: Optional[int] = None,
    world_size: Optional[int] = None,
) -> bool:
    """Restore this rank's RNG state and return whether recovery is exact.

    Old checkpoints carry only rank zero's RNG stream. They remain loadable on
    one process, but a multi-rank continuation must be marked non-exact rather
    than silently reusing rank zero's stream everywhere.
    """

    if rank is None:
        rank = dist.get_rank() if dist.is_available() and dist.is_initialized() else 0
    if world_size is None:
        world_size = (
            dist.get_world_size()
            if dist.is_available() and dist.is_initialized()
            else 1
        )
    states_by_rank = checkpoint.get("rng_states_by_rank")
    if states_by_rank is not None:
        if not isinstance(states_by_rank, list) or len(states_by_rank) != world_size:
            raise ValueError(
                "Exact Stage2 resume requires one saved RNG state per current "
                f"DDP rank: checkpoint={len(states_by_rank) if isinstance(states_by_rank, list) else 'invalid'}, "
                f"current={world_size}"
            )
        if not 0 <= rank < len(states_by_rank) or not isinstance(states_by_rank[rank], dict):
            raise ValueError(f"Checkpoint has no valid RNG state for rank {rank}")
        state = states_by_rank[rank]
        exact = True
    else:
        state = checkpoint.get("rng_state")
        exact = world_size == 1
    if not state:
        return False
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"])
    cuda_state = state.get("cuda")
    if torch.cuda.is_available() and cuda_state is not None:
        if isinstance(cuda_state, dict):
            torch.cuda.set_rng_state(
                cuda_state["state"],
                device=int(cuda_state.get("device_index", torch.cuda.current_device())),
            )
        else:
            # Compatibility with checkpoints written before per-rank states.
            torch.cuda.set_rng_state_all(cuda_state)
    return exact


@torch.no_grad()
def validate_stage2(
    model: nn.Module,
    loader: DataLoader,
    loss_fn: EarthNetForecastLoss,
    data_cfg: EarthNet2021Config,
    device: torch.device,
    max_batches: int = 0,
    correction_config: Optional[dict] = None,
    correction_seed: int = 42,
) -> dict:
    """Run deterministic held-out validation on the main process.

    Observation-correction models use the same fixed reveal contract as the
    training/evaluation helpers.  Keeping this schedule here matters because
    ``checkpoint_best.pt`` must compare U checkpoints under a deterministic
    U protocol, rather than silently selecting them with the no-reveal path.
    Direct and plain Rollout models retain the original validation path.
    """

    was_training = model.training
    model.eval()
    loss_sums = {}
    sample_count = 0
    metrics = ForecastMetricAccumulator(
        red_index=data_cfg.band_spec.red_index,
        nir_index=data_cfg.band_spec.nir_index,
    )
    raw_model = model.module if isinstance(model, DDP) else model
    correction_mode = is_observation_correction_mode(
        getattr(raw_model, "forecast_mode", None)
    )
    correction_generator = (
        torch.Generator(device="cpu").manual_seed(int(correction_seed))
        if correction_mode
        else None
    )
    correction_config = correction_config or {}
    for batch_index, batch in enumerate(loader):
        if max_batches > 0 and batch_index >= max_batches:
            break
        batch = move_batch_to_device(batch, device)
        batch = prepare_stage2_batch_for_model(batch, data_cfg)
        amp = (
            torch.autocast(device_type="cuda", dtype=torch.bfloat16)
            if device.type == "cuda"
            else torch.autocast(device_type="cpu", enabled=False)
        )
        correction_inputs = None
        if correction_mode:
            correction_inputs = build_observation_correction_inputs(
                batch,
                rollout_steps=batch["x_target"].shape[1],
                generator=correction_generator,
                reveal_probability=float(
                    correction_config.get("reveal_probability", 0.5)
                ),
            )
        with amp:
            out = forward_stage2_model(
                model,
                batch,
                correction_inputs=correction_inputs,
            )
            supervision = stage2_supervision_for_output(batch, out)
            losses = loss_fn(
                out["pred"],
                supervision["target"],
                supervision["target_mask"],
                z_pred=out.get("z_pred"),
                z_target=out.get("z_target"),
                z_context=out.get("z_context"),
                z_target_mask=out.get("z_target_mask"),
                horizons=supervision["horizons"],
            )
        batch_size = int(batch["x_context"].shape[0])
        sample_count += batch_size
        for name, value in losses.items():
            loss_sums[name] = loss_sums.get(name, 0.0) + (
                float(value.detach().float().cpu()) * batch_size
            )
        metrics.update(
            out["pred"],
            supervision["target"],
            supervision["target_mask"],
            supervision["horizons"],
            batch["x_context"],
            batch["context_mask"],
        )
    if was_training:
        model.train()
    if sample_count == 0:
        raise RuntimeError("Stage2 validation loader produced no samples")
    result = {
        f"loss/{name}": value / sample_count
        for name, value in loss_sums.items()
    }
    result.update(metrics.compute())
    result["num_samples"] = sample_count
    return result


def configure_stage2_runtime_performance(config: dict, device: torch.device) -> None:
    """Set conservative GPU runtime knobs that preserve numerical protocol."""

    if device.type != "cuda":
        return
    performance_cfg = config.get("performance", {})
    allow_tf32 = bool(performance_cfg.get("allow_tf32", True))
    cudnn_benchmark = bool(performance_cfg.get("cudnn_benchmark", True))
    matmul_precision = str(
        performance_cfg.get("float32_matmul_precision", "high")
    ).lower()
    if matmul_precision not in {"highest", "high", "medium"}:
        raise ValueError(
            "performance.float32_matmul_precision must be one of "
            f"highest/high/medium, got {matmul_precision!r}"
        )
    torch.backends.cuda.matmul.allow_tf32 = allow_tf32
    if hasattr(torch.backends.cudnn, "allow_tf32"):
        torch.backends.cudnn.allow_tf32 = allow_tf32
    torch.backends.cudnn.benchmark = cudnn_benchmark
    if hasattr(torch, "set_float32_matmul_precision"):
        torch.set_float32_matmul_precision(matmul_precision)
    log_main(
        "Stage2 runtime: "
        f"tf32={allow_tf32}, cudnn_benchmark={cudnn_benchmark}, "
        f"float32_matmul_precision={matmul_precision}"
    )


def _log_driver_coverage(
    dataset: EarthNet2021Dataset,
    data_cfg: EarthNet2021Config,
    max_samples: int = 8,
) -> dict:
    if is_stage2_v2_protocol(data_cfg.stage2_protocol):
        return _log_v2_driver_coverage(dataset, data_cfg, max_samples=max_samples)
    return _log_legacy_driver_coverage(dataset, data_cfg, max_samples=max_samples)


def _log_legacy_driver_coverage(
    dataset: EarthNet2021Dataset,
    data_cfg: EarthNet2021Config,
    max_samples: int = 8,
) -> dict:
    count = min(len(dataset), max_samples)
    coverage = torch.zeros(data_cfg.driver_spec.dim, dtype=torch.float64)
    total = 0
    geo_valid = 0.0
    geo_total = 0
    for index in range(count):
        sample = dataset[index]
        driver_mask = sample["D_mask"].double()
        coverage += driver_mask.sum(dim=0)
        total += driver_mask.shape[0]
        geo_mask = sample["G_mask"].double()
        geo_valid += float(geo_mask.sum())
        geo_total += geo_mask.numel()
    rates = coverage / max(total, 1)
    summary = ", ".join(
        f"{name}={rate:.3f}"
        for name, rate in zip(data_cfg.driver_spec.feature_names, rates.tolist())
    )
    log_main(f"Stage2 D valid-rate over {count} samples: {summary}")
    geo_rate = geo_valid / max(geo_total, 1)
    log_main(f"Stage2 G elevation valid-rate over {count} samples: {geo_rate:.3f}")
    missing = [
        name
        for name, rate in zip(data_cfg.driver_spec.feature_names, rates.tolist())
        if rate == 0
    ]
    if missing:
        log_main(
            "warning: these D features are absent in the inspected samples and "
            f"will be mask-filled: {missing}"
        )
    result = {
        name: rate
        for name, rate in zip(data_cfg.driver_spec.feature_names, rates.tolist())
    }
    result["__geo_elevation__"] = geo_rate
    return result


def _log_v2_driver_coverage(
    dataset: EarthNet2021Dataset,
    data_cfg: EarthNet2021Config,
    max_samples: int = 8,
) -> dict:
    """Log the selected frozen path layout without scanning the full dataset."""

    count = min(len(dataset), max_samples)
    if count <= 0:
        raise RuntimeError("Cannot audit driver coverage of an empty Stage2-v2 dataset")
    physical = data_cfg.driver_protocol == PHYSICAL4_PROTOCOL
    driver_names = tuple(PHYSICAL4_FEATURE_NAMES if physical else FULL24_FEATURE_NAMES)
    coverage = torch.zeros(len(driver_names), dtype=torch.float64)
    total = 0
    geo_valid = 0.0
    geo_total = 0
    for index in range(count):
        sample = dataset[index]
        driver_mask = sample["D_mask"].double()
        if driver_mask.shape[-1] != len(driver_names):
            raise ValueError(
                f"Stage2-v2 {data_cfg.driver_protocol} D_mask dimension differs from "
                f"configured layout: got {driver_mask.shape[-1]}, expected {len(driver_names)}"
            )
        coverage += driver_mask.sum(dim=0)
        total += driver_mask.shape[0]
        geo_mask = sample["G_mask"].double()
        geo_valid += float(geo_mask.sum())
        geo_total += geo_mask.numel()
    rates = coverage / max(total, 1)
    summary = ", ".join(
        f"{name}={rate:.3f}"
        for name, rate in zip(driver_names, rates.tolist())
    )
    log_main(
        f"Stage2-v2 {data_cfg.driver_protocol} D valid-rate over {count} samples: {summary}"
    )
    geo_rate = geo_valid / max(geo_total, 1)
    log_main(f"Stage2-v2 cop_dem valid-rate over {count} samples: {geo_rate:.3f}")
    missing = [
        name for name, rate in zip(driver_names, rates.tolist()) if rate == 0
    ]
    if missing:
        log_main(
            f"warning: {data_cfg.driver_protocol} features absent in inspected "
            f"samples and will be mask-filled: {missing}"
        )
    result = dict(zip(driver_names, rates.tolist()))
    result["__geo_elevation__"] = geo_rate
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--num-workers", type=int)
    parser.add_argument("--prefetch-factor", type=int)
    parser.add_argument(
        "--persistent-workers",
        type=int,
        choices=(0, 1),
        help="Override DataLoader persistent_workers (1=true, 0=false).",
    )
    parser.add_argument(
        "--log-interval",
        type=int,
        help="Optimizer updates between stdout/TensorBoard loss and timing reports.",
    )
    parser.add_argument("--data-root", type=str)
    parser.add_argument("--external-driver-root", type=str)
    parser.add_argument("--dgh-stats-path", type=str)
    parser.add_argument("--conditioning-stats-path", type=str)
    parser.add_argument("--manifest-path", type=str)
    parser.add_argument("--validation-manifest-path", type=str)
    parser.add_argument("--require-manifest", action="store_true")
    parser.add_argument("--stage15-checkpoint", type=str)
    parser.add_argument("--checkpoint-dir", type=str)
    parser.add_argument("--log-dir", type=str)
    parser.add_argument("--checkpoint-interval", type=int)
    parser.add_argument("--validation-interval", type=int)
    parser.add_argument("--validation-max-samples", type=int)
    parser.add_argument("--validation-max-batches", type=int)
    parser.add_argument("--resume-from", type=str)
    parser.add_argument(
        "--stop-after-steps",
        type=int,
        help=(
            "Cleanly stop after this global optimizer step while preserving the "
            "configured max_steps/schedule for a later exact resume."
        ),
    )
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    rank, local_rank, world_size, distributed = setup_distributed()
    device = torch.device(f"cuda:{local_rank}" if torch.cuda.is_available() else "cpu")
    config = load_config(args.config)
    if args.max_steps is not None:
        config["training"]["max_steps"] = args.max_steps
    if args.batch_size is not None:
        config["data"]["batch_size"] = args.batch_size
    if args.num_workers is not None:
        config["data"]["num_workers"] = args.num_workers
    if args.prefetch_factor is not None:
        config["data"]["prefetch_factor"] = args.prefetch_factor
    if args.persistent_workers is not None:
        config["data"]["persistent_workers"] = bool(args.persistent_workers)
    if args.log_interval is not None:
        config["log_interval"] = args.log_interval
    if args.data_root is not None:
        config["data"]["root"] = args.data_root
    if args.external_driver_root is not None:
        config["data"]["external_driver_root"] = args.external_driver_root
    if args.dgh_stats_path is not None:
        config["data"]["dgh_stats_path"] = args.dgh_stats_path
    if args.conditioning_stats_path is not None:
        config["data"]["conditioning_stats_path"] = args.conditioning_stats_path
    if args.manifest_path is not None:
        config["data"]["manifest_path"] = args.manifest_path
        manifest_paths = config["data"].get("manifest_paths")
        if isinstance(manifest_paths, dict):
            manifest_paths[str(config["data"].get("split", "train"))] = args.manifest_path
    if args.validation_manifest_path is not None:
        config["data"].setdefault("manifest_paths", {})["val"] = args.validation_manifest_path
    if args.require_manifest:
        config["data"]["require_manifest"] = True
    if args.stage15_checkpoint is not None:
        config["model"]["encoder"]["from_checkpoint"] = args.stage15_checkpoint
    if args.checkpoint_dir is not None:
        config["checkpoint_dir"] = args.checkpoint_dir
    if args.log_dir is not None:
        config["log_dir"] = args.log_dir
    if args.validation_interval is not None:
        config.setdefault("validation", {})["interval"] = args.validation_interval
    if args.validation_max_samples is not None:
        config.setdefault("validation", {})["max_samples"] = (
            args.validation_max_samples
        )
    if args.validation_max_batches is not None:
        config.setdefault("validation", {})["max_batches"] = (
            args.validation_max_batches
        )
    checkpoint_interval = args.checkpoint_interval or int(config.get("checkpoint_interval", 5000))
    epoch_checkpoint_steps = parse_epoch_checkpoint_steps(config)
    epoch_checkpoint_epochs = parse_epoch_checkpoint_epochs(config)
    if epoch_checkpoint_steps and epoch_checkpoint_epochs:
        raise ValueError(
            "Configure either epoch_checkpoint_steps or "
            "epoch_checkpoint_epochs, not both."
        )
    resume_from = args.resume_from or config.get("resume_from")
    # Preserve this before a Stage2 resume clears the initializer from the
    # live config.  The run provenance must still say which frozen Stage1.5
    # state bridge started the original experiment whenever it is available.
    stage15_checkpoint_for_provenance = config["model"]["encoder"].get(
        "from_checkpoint"
    )
    if resume_from:
        # A Stage2 checkpoint already contains the complete encoder. Resuming
        # must not depend on the original Stage1.5 file still being present.
        config["model"]["encoder"]["from_checkpoint"] = None
    require_stage15_initializer_if_formal(config, resume_from=resume_from)
    seed = int(args.seed if args.seed is not None else config["training"].get("seed", 42))
    process_seed = seed + rank
    random.seed(process_seed)
    np.random.seed(process_seed)
    torch.manual_seed(process_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(process_seed)
    log_main(f"Stage2 random seed: {seed}")

    configure_stage2_runtime_performance(config, device)
    max_steps = int(config["training"]["max_steps"])
    accum_steps = int(config["training"].get("gradient_accumulation_steps", 1))
    horizons_per_sample = int(config["training"].get("horizons_per_sample", 0))
    log_interval = int(config.get("log_interval", 50))
    if log_interval <= 0:
        raise ValueError(f"log_interval must be positive, got {log_interval}")
    stop_after_steps = args.stop_after_steps
    if stop_after_steps is not None:
        if stop_after_steps <= 0:
            raise ValueError("--stop-after-steps must be positive")
        if stop_after_steps > max_steps:
            raise ValueError(
                "--stop-after-steps cannot exceed the configured --max-steps: "
                f"stop_after={stop_after_steps}, max_steps={max_steps}"
            )

    data_cfg = EarthNet2021Config.from_config(config["data"], split=config["data"].get("split", "train"))
    dataset = EarthNet2021Dataset(data_cfg)
    coverage = _log_driver_coverage(dataset, data_cfg)
    is_v2 = is_stage2_v2_protocol(data_cfg.stage2_protocol)
    if is_v2:
        # Validate curriculum structure before allocating a large model.  This
        # is also the explicit guard against accidentally enabling teacher
        # forcing under a rollout-named configuration.
        current_rollout_length(config, optimizer_step=0)
        partition_training_settings(config)
        if bool(config["training"].get("require_dgh_stats", False)):
            raise ValueError(
                "earthnet2021x_path_v2 must not require legacy DGH statistics; "
                "use data.conditioning_stats_path and "
                "scripts/build_earthnet_conditioning_stats.py instead."
            )
        if bool(config["training"].get("require_full_conditioning_stats", True)):
            stats = data_cfg.conditioning_stats
            if stats is None or stats.is_identity_smoke_stats:
                stats_script = (
                    "scripts/build_earthnet_physical_stats.py"
                    if data_cfg.driver_protocol == PHYSICAL4_PROTOCOL
                    else "scripts/build_earthnet_conditioning_stats.py"
                )
                raise RuntimeError(
                    "Formal Stage2-v2 training requires non-identity train-only "
                    f"{data_cfg.driver_protocol} statistics. Run {stats_script} "
                    "on the frozen train manifest and pass --conditioning-stats-path."
                )
        driver_names = (
            PHYSICAL4_FEATURE_NAMES
            if data_cfg.driver_protocol == PHYSICAL4_PROTOCOL
            else FULL24_FEATURE_NAMES
        )
    else:
        if bool(config["training"].get("require_dgh_stats", True)):
            if not config["data"].get("dgh_stats_path"):
                raise RuntimeError(
                    "Formal Stage2 training requires train-only D normalization stats. "
                    "Run scripts/build_earthnet_dgh_stats.py and pass --dgh-stats-path."
                )
        driver_names = tuple(data_cfg.driver_spec.feature_names)
    if bool(config["training"].get("require_all_driver_features", True)):
        absent = [name for name in driver_names if coverage[name] == 0]
        if absent:
            raise RuntimeError(
                "Formal Stage2 training is missing configured D features: "
                f"{absent}. Provide a complete driver source or correct the data protocol."
            )
    minimum_driver_coverage = float(config["training"].get("min_driver_valid_fraction", 0.0))
    if minimum_driver_coverage > 0:
        low_coverage = [
            f"{name}={coverage[name]:.3f}"
            for name in driver_names
            if coverage[name] < minimum_driver_coverage
        ]
        if low_coverage:
            raise RuntimeError(
                "Stage2 driver valid-rate falls below "
                f"min_driver_valid_fraction={minimum_driver_coverage:.3f}: {low_coverage}"
            )
    if bool(config["training"].get("require_geo", True)):
        if coverage["__geo_elevation__"] == 0:
            raise RuntimeError(
                "Formal Stage2 training requires valid elevation G, but the "
                "inspected EarthNet samples contain none."
            )
    sampler = (
        DistributedSampler(
            dataset,
            num_replicas=world_size,
            rank=rank,
            shuffle=True,
            seed=seed,
        )
        if distributed
        else EpochRandomSampler(dataset, seed=seed)
    )
    train_batch_size = int(config["data"]["batch_size"])
    train_num_workers = int(config["data"].get("num_workers", 4))
    train_prefetch_factor = int(config["data"].get("prefetch_factor", 2))
    train_persistent_workers = bool(config["data"].get("persistent_workers", True))
    loader = build_stage2_train_loader(
        dataset,
        sampler=sampler,
        batch_size=train_batch_size,
        num_workers=train_num_workers,
        epoch=0,
        process_seed=process_seed,
        prefetch_factor=train_prefetch_factor,
        persistent_workers=train_persistent_workers,
    )
    if len(loader) == 0:
        raise RuntimeError(
            f"Stage2 DataLoader has zero batches: samples={len(dataset)}, "
            f"batch_size={config['data']['batch_size']}, drop_last=True"
        )
    if epoch_checkpoint_epochs:
        if len(loader) % accum_steps != 0:
            raise ValueError(
                "epoch_checkpoint_epochs requires loader length divisible by "
                "gradient_accumulation_steps so named checkpoints land on "
                "unambiguous optimizer-step boundaries: "
                f"loader_length={len(loader)}, accumulation_steps={accum_steps}"
            )
        steps_per_epoch = len(loader) // accum_steps
        epoch_checkpoint_steps = {
            epoch * steps_per_epoch: f"epoch{epoch}"
            for epoch in epoch_checkpoint_epochs
        }
    log_main(
        f"EarthNet samples: {len(dataset)}; batch={config['data']['batch_size']}; "
        f"distributed={distributed}; workers={train_num_workers}; "
        f"persistent_workers={train_persistent_workers and train_num_workers > 0}; "
        f"prefetch_factor={train_prefetch_factor if train_num_workers > 0 else 'n/a'}; "
        f"defer_context_resize_to_device={data_cfg.defer_context_resize_to_device}"
    )

    validation_cfg = config.get("validation", {})
    validation_interval = int(validation_cfg.get("interval", 0))
    validation_loader = None
    validation_data_cfg = None
    if is_main_process() and validation_interval > 0:
        validation_data_cfg = EarthNet2021Config.from_config(
            config["data"],
            split=str(validation_cfg.get("split", "val")),
        )
        validation_dataset = EarthNet2021Dataset(validation_data_cfg)
        max_validation_samples = int(validation_cfg.get("max_samples", 0))
        if (
            max_validation_samples > 0
            and len(validation_dataset) > max_validation_samples
        ):
            indices = np.linspace(
                0,
                len(validation_dataset) - 1,
                num=max_validation_samples,
                dtype=np.int64,
            ).tolist()
            validation_dataset = Subset(validation_dataset, indices)
        validation_num_workers = int(
            validation_cfg.get("num_workers", config["data"].get("num_workers", 4))
        )
        validation_loader_kwargs = {
            "batch_size": int(
                validation_cfg.get("batch_size", config["data"]["batch_size"])
            ),
            "shuffle": False,
            "num_workers": validation_num_workers,
            "pin_memory": True,
            "drop_last": False,
            "collate_fn": collate_earthnet2021,
        }
        if validation_num_workers > 0:
            validation_loader_kwargs["persistent_workers"] = bool(
                validation_cfg.get(
                    "persistent_workers",
                    config["data"].get("persistent_workers", True),
                )
            )
            validation_loader_kwargs["prefetch_factor"] = int(
                validation_cfg.get(
                    "prefetch_factor",
                    config["data"].get("prefetch_factor", 2),
                )
            )
        validation_loader = DataLoader(
            validation_dataset,
            **validation_loader_kwargs,
        )
        log_main(
            f"EarthNet validation monitor samples: {len(validation_dataset)}; "
            f"interval={validation_interval}"
        )

    model = create_stage2_model(config, device)
    total_params = sum(parameter.numel() for parameter in model.parameters())
    trainable_params = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    log_main(
        f"Stage2 parameters: total={total_params / 1e6:.2f}M, "
        f"trainable={trainable_params / 1e6:.2f}M"
    )
    if is_main_process() and epoch_checkpoint_steps:
        tags = ", ".join(
            f"{tag}@step{step}" for step, tag in sorted(epoch_checkpoint_steps.items())
        )
        log_main(f"named epoch checkpoints: {tags}")
    if distributed:
        model = DDP(
            model,
            device_ids=[local_rank] if device.type == "cuda" else None,
            find_unused_parameters=False,
        )
    optimizer = build_optimizer(model, config)
    scheduler = build_scheduler(optimizer, config)
    optimizer_step = 0
    best_validation = {
        "metric": str(validation_cfg.get("primary_metric", "loss/total")),
        "mode": str(validation_cfg.get("mode", "min")),
        "value": None,
        "step": None,
    }
    resume_checkpoint = None
    resume_data_position = None
    resume_rng_is_exact = True
    if resume_from:
        resume_checkpoint = torch.load(resume_from, map_location="cpu", weights_only=False)
        raw_model = model.module if isinstance(model, DDP) else model
        load_stage2_model_state(raw_model, resume_checkpoint["model_state_dict"], strict=True)
        optimizer.load_state_dict(resume_checkpoint["optimizer_state_dict"])
        scheduler.load_state_dict(resume_checkpoint["scheduler_state_dict"])
        optimizer_step = int(resume_checkpoint.get("global_step", 0))
        if resume_checkpoint.get("best_validation"):
            best_validation = dict(resume_checkpoint["best_validation"])
        resume_rng_is_exact = restore_rng_state(
            resume_checkpoint,
            rank=rank,
            world_size=world_size,
        )
        resume_data_position = restore_data_position(
            resume_checkpoint.get("data_position"),
            loader_length=len(loader),
            world_size=world_size,
            batch_size=train_batch_size,
            accumulation_steps=accum_steps,
            expected_micro_step=optimizer_step * accum_steps,
        )
        saved_curriculum = resume_checkpoint.get("curriculum")
        if saved_curriculum is not None:
            expected_curriculum = curriculum_checkpoint_state(config, optimizer_step)
            for name in (
                "forecast_mode",
                "observation_correction",
                "rollout_length",
                "schedule",
                "partition_schedule",
                "partition_loss",
            ):
                if saved_curriculum.get(name) != expected_curriculum.get(name):
                    raise ValueError(
                        "Stage2 resume curriculum differs from the checkpoint: "
                        f"{name} saved={saved_curriculum.get(name)!r}, "
                        f"configured={expected_curriculum.get(name)!r}. "
                        "Do not resume a Direct/rollout run under a changed schedule."
                    )
        if resume_data_position is None or not resume_rng_is_exact:
            missing_parts = []
            if resume_data_position is None:
                missing_parts.append("data-position metadata")
            if not resume_rng_is_exact:
                missing_parts.append("one RNG state per DDP rank")
            log_main(
                "warning: resume checkpoint predates exact recovery metadata "
                f"({', '.join(missing_parts)}); falling back where necessary and "
                "not claiming bitwise recovery"
            )
        if stop_after_steps is not None and stop_after_steps <= optimizer_step:
            raise ValueError(
                "--stop-after-steps must be greater than the resumed global step: "
                f"stop_after={stop_after_steps}, resumed_step={optimizer_step}"
            )
        log_main(f"resumed Stage2 from {resume_from} at optimizer_step={optimizer_step}")
    loss_fn = EarthNetForecastLoss.from_config(
        config["loss"],
        red_index=data_cfg.band_spec.red_index,
        nir_index=data_cfg.band_spec.nir_index,
    ).to(device)
    partition_loss_fn = (
        PartitionConsistencyLoss.from_config(
            config["loss"],
            red_index=data_cfg.band_spec.red_index,
            nir_index=data_cfg.band_spec.nir_index,
        ).to(device)
        if is_partition_forecast_mode(config.get("model", {}).get("forecast_mode"))
        else None
    )
    partition_settings = partition_training_settings(config) if is_v2 else None
    run_provenance = None
    if is_main_process():
        run_provenance = build_stage2_run_provenance(
            config,
            train_manifest_path=data_cfg.manifest_path,
            validation_manifest_path=(
                validation_data_cfg.manifest_path
                if validation_data_cfg is not None
                else None
            ),
            conditioning_stats_path=data_cfg.conditioning_stats_path,
            stage15_checkpoint_path=stage15_checkpoint_for_provenance,
            resume_checkpoint_path=resume_from,
            parent_provenance=(
                resume_checkpoint.get("provenance") if resume_checkpoint else None
            ),
            device=device,
            world_size=world_size,
        )
        provenance_paths = write_run_provenance(
            run_provenance,
            (
                Path(config["checkpoint_dir"]) / "run_provenance.json",
                Path(config["log_dir"]) / "run_provenance.json",
            ),
        )
        log_main(
            "Stage2 provenance written: "
            + ", ".join(str(path) for path in provenance_paths)
        )
    writer = (
        SummaryWriter(config["log_dir"])
        if is_main_process() and SummaryWriter is not None
        else None
    )
    if is_main_process() and SummaryWriter is None:
        log_main("warning: tensorboard is not installed; scalar logging is disabled")

    micro_step = optimizer_step * accum_steps
    epoch = resume_data_position.epoch if resume_data_position is not None else 0
    next_batch_index = (
        resume_data_position.next_batch_index
        if resume_data_position is not None
        else 0
    )
    last_data_position = (
        resume_data_position
        if resume_data_position is not None
        else Stage2DataPosition(
            epoch=epoch,
            next_batch_index=next_batch_index,
            loader_length=len(loader),
            micro_step=micro_step,
            world_size=world_size,
            batch_size=train_batch_size,
            accumulation_steps=accum_steps,
        )
    )
    model.train()
    optimizer.zero_grad(set_to_none=True)
    progress = tqdm(
        total=max_steps,
        initial=optimizer_step,
        disable=not is_main_process(),
        desc="Stage2 EarthNet",
    )
    # [PROFILE] The window is reduced only every ``log_interval`` updates, so
    # its timing events do not force a per-step CUDA synchronization.
    performance_window = Stage2PerformanceWindow()
    while optimizer_step < max_steps and (
        stop_after_steps is None or optimizer_step < stop_after_steps
    ):
        if hasattr(sampler, "set_epoch"):
            sampler.set_epoch(epoch)
        # Reuse the worker pool across epochs.  The sampler still provides the
        # deterministic epoch-specific permutation and the loader's iterator
        # resets its index queues for each new epoch.
        epoch_loader = loader
        batch_request_time = time.perf_counter()
        for batch_index, batch in enumerate(epoch_loader):
            batch_arrival_time = time.perf_counter()
            if batch_index < next_batch_index:
                batch_request_time = time.perf_counter()
                continue
            performance_window.data_wait_s += batch_arrival_time - batch_request_time

            transfer_events = None
            input_events = None
            compute_events = None
            if device.type == "cuda":
                transfer_start = torch.cuda.Event(enable_timing=True)
                transfer_end = torch.cuda.Event(enable_timing=True)
                input_start = torch.cuda.Event(enable_timing=True)
                input_end = torch.cuda.Event(enable_timing=True)
                compute_start = torch.cuda.Event(enable_timing=True)
                compute_end = torch.cuda.Event(enable_timing=True)
                transfer_start.record()
            batch = move_batch_to_device(batch, device)
            if device.type == "cuda":
                transfer_end.record()
                input_start.record()
            batch = prepare_stage2_batch_for_model(batch, data_cfg)
            if device.type == "cuda":
                input_end.record()
                compute_start.record()
                transfer_events = (transfer_start, transfer_end)
                input_events = (input_start, input_end)
            selected_steps = None
            max_rollout_steps = None
            partition_start = None
            correction_inputs = None
            partition_scale = 0.0
            if is_stage2_v2_batch(batch):
                raw_model = model.module if isinstance(model, DDP) else model
                correction_mode = is_observation_correction_mode(
                    getattr(raw_model, "forecast_mode", None)
                )
                rollout_mode = is_rollout_forecast_mode(
                    getattr(raw_model, "forecast_mode", None)
                )
                partition_mode = is_partition_forecast_mode(
                    getattr(raw_model, "forecast_mode", None)
                )
                available_steps = (
                    current_rollout_length(config, optimizer_step)
                    if rollout_mode
                    else batch["x_target"].shape[1]
                )
                max_rollout_steps = available_steps if rollout_mode else None
                correction_cfg = config.get("training", {}).get(
                    "observation_correction", {}
                )
                supervise_all = correction_mode and bool(
                    correction_cfg.get("supervise_all_horizons", True)
                )
                selected_steps = (
                    None
                    if supervise_all
                    else select_v2_horizon_indices(
                        available_steps,
                        horizons_per_sample,
                        device=device,
                        always_include_last=True,
                    )
                )
                if correction_mode:
                    correction_inputs = build_observation_correction_inputs(
                        batch,
                        rollout_steps=available_steps,
                        reveal_probability=float(
                            correction_cfg.get("reveal_probability", 0.5)
                        ),
                    )
                if partition_mode:
                    partition_scale = partition_loss_scale(config, optimizer_step)
                    if partition_scale > 0.0:
                        partition_start = sample_two_step_partition_start(
                            available_steps,
                            device=device,
                        )
            else:
                batch = select_horizons(batch, horizons_per_sample)
            should_update = (micro_step + 1) % accum_steps == 0
            sync_context = (
                nullcontext()
                if should_update or not isinstance(model, DDP)
                else model.no_sync()
            )
            amp = torch.autocast(device_type="cuda", dtype=torch.bfloat16) if device.type == "cuda" else torch.autocast(device_type="cpu", enabled=False)
            with sync_context:
                with amp:
                    out = forward_stage2_model(
                        model,
                        batch,
                        selected_steps=selected_steps,
                        max_rollout_steps=max_rollout_steps,
                        partition_start=partition_start,
                        detach_partition_start=bool(
                            (partition_settings or {}).get(
                                "detach_partition_start", True
                            )
                        ),
                        correction_inputs=correction_inputs,
                    )
                    supervision = stage2_supervision_for_output(batch, out)
                    losses = loss_fn(
                        out["pred"],
                        supervision["target"],
                        supervision["target_mask"],
                        z_pred=out.get("z_pred"),
                        z_target=out.get("z_target"),
                        z_context=out.get("z_context"),
                        z_target_mask=out.get("z_target_mask"),
                        horizons=supervision["horizons"],
                    )
                    if partition_start is not None:
                        if partition_loss_fn is None:
                            raise AssertionError(
                                "A partition branch was sampled without a partition loss"
                            )
                        partition = out.get("partition")
                        if not isinstance(partition, dict):
                            raise KeyError(
                                "obsworld_partition_24d forward did not return partition outputs"
                            )
                        terminal = partition_supervision_for_output(batch, partition)
                        partition_losses = partition_loss_fn(
                            z_direct=partition["z_direct"],
                            z_composed=partition["z_composed"],
                            pred_direct=partition["pred_direct"],
                            pred_composed=partition["pred_composed"],
                            target=terminal["target"],
                            target_mask=terminal["target_mask"],
                            state_mask=partition.get("state_valid_mask"),
                        )
                        for name, value in partition_losses.items():
                            if name != "total":
                                losses[f"partition_{name}"] = value
                        losses["partition_unscaled_total"] = partition_losses["total"]
                        losses["partition_scale"] = losses["total"].new_tensor(
                            partition_scale
                        )
                        losses["partition_total"] = (
                            partition_losses["total"] * partition_scale
                        )
                        losses["total"] = losses["total"] + losses["partition_total"]
                    loss = losses["total"] / accum_steps
                if not torch.isfinite(loss):
                    components = {
                        name: float(value.detach().float().cpu())
                        for name, value in losses.items()
                    }
                    sample_ids = [
                        item.get("sample_id", item.get("path", "<unknown>"))
                        for item in batch.get("meta", [])
                    ]
                    raise FloatingPointError(
                        f"Non-finite Stage2 loss: {components}; samples={sample_ids}"
                    )
                loss.backward()

            micro_step += 1
            performance_window.local_sample_count += int(batch["x_context"].shape[0])
            last_data_position = next_data_position(
                epoch=epoch,
                completed_batch_index=batch_index,
                loader_length=len(loader),
                micro_step=micro_step,
                world_size=world_size,
                batch_size=train_batch_size,
                accumulation_steps=accum_steps,
            )
            if should_update:
                suppress_backbone_warmup_gradients(
                    model,
                    optimizer_step,
                    config,
                )
                grad_clip = float(config["training"].get("grad_clip", 1.0))
                if grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(
                        model.parameters(),
                        grad_clip,
                        error_if_nonfinite=True,
                    )
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                if device.type == "cuda":
                    compute_end.record()
                    compute_events = (compute_start, compute_end)
                performance_window.add_cuda_events(
                    transfer=transfer_events,
                    input_prepare=input_events,
                    compute=compute_events,
                )
                optimizer_step += 1
                performance_window.optimizer_updates += 1
                progress.update(1)

                if optimizer_step % log_interval == 0:
                    learning_rates = scheduler.get_last_lr()
                    log = reduce_stage2_loss_scalars(losses)
                    performance = performance_window.summarize(
                        device=device,
                        world_size=world_size,
                    )
                    if is_main_process():
                        progress.set_postfix(
                            {
                                "loss": f"{log.get('total', float('nan')):.4f}",
                                "obs": f"{log.get('obs', float('nan')):.4f}",
                                "ndvi": f"{log.get('ndvi', float('nan')):.4f}",
                            }
                        )
                        log_main(
                            format_stage2_training_progress(
                                step=optimizer_step,
                                max_steps=max_steps,
                                epoch=epoch,
                                losses=log,
                                learning_rates=learning_rates,
                                performance=performance,
                            )
                        )
                    if writer is not None:
                        writer.add_scalar(
                            "train/lr_new_modules",
                            learning_rates[0],
                            optimizer_step,
                        )
                        if len(learning_rates) > 1:
                            writer.add_scalar(
                                "train/lr_backbone",
                                learning_rates[1],
                                optimizer_step,
                            )
                        for name, value in log.items():
                            writer.add_scalar(f"train/{name}", value, optimizer_step)
                        for name, value in performance.items():
                            writer.add_scalar(
                                f"performance/{name}", value, optimizer_step
                            )
                        if "rollout_steps" in out:
                            writer.add_scalar(
                                "train/rollout_steps",
                                float(out["rollout_steps"].detach().cpu()),
                                optimizer_step,
                            )
                        if "state_delta_norm" in out:
                            writer.add_scalar(
                                "train/state_delta_norm",
                                float(out["state_delta_norm"].detach().float().mean().cpu()),
                                optimizer_step,
                            )

            if not should_update:
                if device.type == "cuda":
                    compute_end.record()
                    compute_events = (compute_start, compute_end)
                performance_window.add_cuda_events(
                    transfer=transfer_events,
                    input_prepare=input_events,
                    compute=compute_events,
                )

            if should_update:
                if (
                    validation_interval > 0
                    and optimizer_step > 0
                    and optimizer_step % validation_interval == 0
                ):
                    save_best_checkpoint = False
                    barrier()
                    if is_main_process():
                        raw_model = model.module if isinstance(model, DDP) else model
                        validation_metrics = validate_stage2(
                            raw_model,
                            validation_loader,
                            loss_fn,
                            validation_data_cfg,
                            device,
                            max_batches=int(validation_cfg.get("max_batches", 0)),
                            correction_config=config.get("training", {}).get(
                                "observation_correction", {}
                            ),
                            correction_seed=seed,
                        )
                        metric_name = best_validation["metric"]
                        if metric_name not in validation_metrics:
                            raise KeyError(
                                f"Validation primary_metric={metric_name!r} is absent; "
                                f"available={sorted(validation_metrics)}"
                            )
                        metric_value = float(validation_metrics[metric_name])
                        previous = best_validation.get("value")
                        improved = (
                            previous is None
                            or (
                                best_validation["mode"] == "min"
                                and metric_value < float(previous)
                            )
                            or (
                                best_validation["mode"] == "max"
                                and metric_value > float(previous)
                            )
                        )
                        summary = ", ".join(
                            f"{name}={value:.5f}"
                            for name, value in validation_metrics.items()
                            if isinstance(value, (int, float))
                            and name in {"loss/total", "MAE", "NDVI_MAE", "skill_vs_persistence"}
                        )
                        log_main(f"validation step={optimizer_step}: {summary}")
                        if writer is not None:
                            for name, value in validation_metrics.items():
                                if isinstance(value, (int, float)):
                                    writer.add_scalar(
                                        f"validation/{name}",
                                        value,
                                        optimizer_step,
                                    )
                        if improved:
                            best_validation.update(
                                {"value": metric_value, "step": optimizer_step}
                            )
                            save_best_checkpoint = True
                            log_main(
                                f"new best {metric_name}={metric_value:.6f} "
                                f"at step={optimizer_step}"
                            )
                    if distributed:
                        synchronized_validation = [
                            dict(best_validation),
                            save_best_checkpoint,
                        ]
                        dist.broadcast_object_list(synchronized_validation, src=0)
                        best_validation = dict(synchronized_validation[0])
                        save_best_checkpoint = bool(synchronized_validation[1])
                    if save_best_checkpoint:
                        # Every DDP rank participates so this checkpoint also
                        # carries its own RNG stream and is safe to resume.
                        save_checkpoint(
                            os.path.join(
                                config["checkpoint_dir"],
                                "checkpoint_best.pt",
                            ),
                            optimizer_step,
                            model,
                            optimizer,
                            scheduler,
                            config,
                            best_validation=best_validation,
                            provenance=run_provenance,
                            data_position=last_data_position,
                        )
                    else:
                        # Match save_checkpoint's internal distributed barrier
                        # when validation did not produce a new best model.
                        barrier()

                if optimizer_step > 0 and optimizer_step % checkpoint_interval == 0:
                    save_checkpoint(
                        os.path.join(config["checkpoint_dir"], f"checkpoint_step_{optimizer_step}.pt"),
                        optimizer_step,
                        model,
                        optimizer,
                        scheduler,
                        config,
                        best_validation=best_validation,
                        provenance=run_provenance,
                        data_position=last_data_position,
                    )

                named_tag = epoch_checkpoint_steps.get(optimizer_step)
                if named_tag is not None:
                    save_checkpoint(
                        os.path.join(
                            config["checkpoint_dir"],
                            f"checkpoint_{named_tag}_step_{optimizer_step}.pt",
                        ),
                        optimizer_step,
                        model,
                        optimizer,
                        scheduler,
                        config,
                        best_validation=best_validation,
                        provenance=run_provenance,
                        data_position=last_data_position,
                    )

            if should_update and (
                optimizer_step % log_interval == 0
                or (
                    validation_interval > 0
                    and optimizer_step > 0
                    and optimizer_step % validation_interval == 0
                )
                or (
                    optimizer_step > 0
                    and optimizer_step % checkpoint_interval == 0
                )
                or optimizer_step in epoch_checkpoint_steps
            ):
                # Do not let rank-zero validation or checkpoint serialization
                # contaminate the next training-window throughput estimate.
                performance_window = Stage2PerformanceWindow()

            # The next ``for`` iteration obtains a new batch only after this
            # point, so checkpoint/validation work is not misreported as data
            # waiting time in the performance trace.
            batch_request_time = time.perf_counter()

            if optimizer_step >= max_steps or (
                stop_after_steps is not None and optimizer_step >= stop_after_steps
            ):
                break
        epoch += 1
        next_batch_index = 0

    if optimizer_step % checkpoint_interval != 0:
        save_checkpoint(
            os.path.join(config["checkpoint_dir"], f"checkpoint_step_{optimizer_step}.pt"),
            optimizer_step,
            model,
            optimizer,
            scheduler,
            config,
            best_validation=best_validation,
            provenance=run_provenance,
            data_position=last_data_position,
        )
    if stop_after_steps is not None and optimizer_step == stop_after_steps:
        log_main(
            "Stage2 stopped cleanly at requested optimizer step "
            f"{optimizer_step}; resume from its checkpoint with the same "
            "--max-steps/configuration."
        )
    if writer is not None:
        writer.close()
    cleanup_distributed()


if __name__ == "__main__":
    main()
