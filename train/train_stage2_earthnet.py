"""Train ObsWorld Stage 2 on EarthNet2021 standard forecasting."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import math
import os
import random
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import torch
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

from data.datasets.earthnet2021 import EarthNet2021Config, EarthNet2021Dataset, collate_earthnet2021
from data.earthnet_conditioning import FULL24_FEATURE_NAMES, is_stage2_v2_protocol
from data.stage2_contract import is_stage2_v2_batch, model_input_view
from models.adapters.earthnet_band_adapter import EarthNetInputAdapter
from models.adapters.geo_tokenizer import GeoTokenizer
from models.decoders.earthnet_observation_decoder import EarthNetObservationDecoder
from models.dynamics.context_state_aggregator import ContextStateAggregator
from models.dynamics.condition_encoders import DriverEncoder, HorizonEncoder
from models.dynamics.obsworld_factory import create_obsworld_v2_model
from models.dynamics.obsworld_stage2 import ObsWorldStage2Model
from models.dynamics.state_dynamics_module import StateDynamicsModule
from models.encoders.multimodal_vit_encoder_film import MultiModalViTEncoderFiLM
from models.encoders.pure_imaging_condition_encoder import PureImagingConditionEncoder
from models.encoders.state_projection import SpatialStateProjector
from models.losses.earthnet_forecasting import EarthNetForecastLoss
from eval.forecast_metrics import ForecastMetricAccumulator
from train.fsdp_utils import barrier, cleanup_distributed, is_main_process, setup_distributed


def log_main(message: str) -> None:
    if is_main_process():
        print(message, flush=True)


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


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


def forward_stage2_model(
    model: nn.Module,
    batch: dict,
    *,
    selected_steps: Optional[torch.Tensor] = None,
) -> dict:
    """Forward only the protocol-approved batch partition through the model."""

    raw_model = model.module if isinstance(model, DDP) else model
    include_targets = bool(getattr(raw_model, "compute_latent_targets", False))
    inputs = model_input_view(batch, include_training_targets=include_targets)
    if getattr(raw_model, "forecast_mode", None) == "direct_path_24d":
        return model(inputs, selected_steps=selected_steps)
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
) -> Optional[torch.Tensor]:
    """Choose Direct24 supervision endpoints without mutating the v2 batch.

    Direct24 needs the complete ``D_path`` to construct each legal prefix;
    slicing the batch in the legacy way would lose the first-future alignment.
    We therefore ask the model to decode a subset and slice *only* the
    supervision tensors afterwards.  Returning ``None`` means full 20-step
    decoding, which is used by validation and by small smoke runs.
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
    chosen: list[int] = []
    for group in group_order:
        if len(chosen) >= horizons_per_sample or group.numel() == 0:
            continue
        chosen.append(int(group[torch.randint(group.numel(), (1,), device=device)].item()))

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


def save_checkpoint(
    path: str,
    step: int,
    model: nn.Module,
    optimizer,
    scheduler,
    config: dict,
    best_validation: Optional[dict] = None,
) -> None:
    if not is_main_process():
        return
    raw_model = model.module if isinstance(model, DDP) else model
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "global_step": step,
        "model_state_dict": raw_model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "config": config,
        "best_validation": best_validation,
        "rng_state": {
            "python": random.getstate(),
            "numpy": np.random.get_state(),
            "torch": torch.get_rng_state(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        },
    }
    temporary = f"{path}.tmp"
    torch.save(payload, temporary)
    os.replace(temporary, path)
    log_main(f"checkpoint saved: {path}")


def restore_rng_state(checkpoint: dict) -> None:
    state = checkpoint.get("rng_state")
    if not state:
        return
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"])
    if torch.cuda.is_available() and state.get("cuda") is not None:
        torch.cuda.set_rng_state_all(state["cuda"])


@torch.no_grad()
def validate_stage2(
    model: nn.Module,
    loader: DataLoader,
    loss_fn: EarthNetForecastLoss,
    data_cfg: EarthNet2021Config,
    device: torch.device,
    max_batches: int = 0,
) -> dict:
    """Run deterministic held-out validation on the main process."""

    was_training = model.training
    model.eval()
    loss_sums = {}
    sample_count = 0
    metrics = ForecastMetricAccumulator(
        red_index=data_cfg.band_spec.red_index,
        nir_index=data_cfg.band_spec.nir_index,
    )
    for batch_index, batch in enumerate(loader):
        if max_batches > 0 and batch_index >= max_batches:
            break
        batch = move_batch_to_device(batch, device)
        amp = (
            torch.autocast(device_type="cuda", dtype=torch.bfloat16)
            if device.type == "cuda"
            else torch.autocast(device_type="cpu", enabled=False)
        )
        with amp:
            out = forward_stage2_model(model, batch)
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
    """Log formal 24-D path availability without reusing legacy DGH names."""

    count = min(len(dataset), max_samples)
    if count <= 0:
        raise RuntimeError("Cannot audit driver coverage of an empty Stage2-v2 dataset")
    coverage = torch.zeros(len(FULL24_FEATURE_NAMES), dtype=torch.float64)
    total = 0
    geo_valid = 0.0
    geo_total = 0
    for index in range(count):
        sample = dataset[index]
        driver_mask = sample["D_mask"].double()
        if driver_mask.shape[-1] != len(FULL24_FEATURE_NAMES):
            raise ValueError(
                "Stage2-v2 D_mask feature dimension differs from formal full24: "
                f"got {driver_mask.shape[-1]}"
            )
        coverage += driver_mask.sum(dim=0)
        total += driver_mask.shape[0]
        geo_mask = sample["G_mask"].double()
        geo_valid += float(geo_mask.sum())
        geo_total += geo_mask.numel()
    rates = coverage / max(total, 1)
    summary = ", ".join(
        f"{name}={rate:.3f}"
        for name, rate in zip(FULL24_FEATURE_NAMES, rates.tolist())
    )
    log_main(f"Stage2-v2 full24 D valid-rate over {count} samples: {summary}")
    geo_rate = geo_valid / max(geo_total, 1)
    log_main(f"Stage2-v2 cop_dem valid-rate over {count} samples: {geo_rate:.3f}")
    missing = [
        name
        for name, rate in zip(FULL24_FEATURE_NAMES, rates.tolist())
        if rate == 0
    ]
    if missing:
        log_main(
            "warning: these formal full24 features are absent in inspected "
            f"samples and will be mask-filled: {missing}"
        )
    result = {
        name: rate
        for name, rate in zip(FULL24_FEATURE_NAMES, rates.tolist())
    }
    result["__geo_elevation__"] = geo_rate
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--num-workers", type=int)
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
    resume_from = args.resume_from or config.get("resume_from")
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

    torch.backends.cuda.matmul.allow_tf32 = True
    max_steps = int(config["training"]["max_steps"])
    accum_steps = int(config["training"].get("gradient_accumulation_steps", 1))
    horizons_per_sample = int(config["training"].get("horizons_per_sample", 0))

    data_cfg = EarthNet2021Config.from_config(config["data"], split=config["data"].get("split", "train"))
    dataset = EarthNet2021Dataset(data_cfg)
    coverage = _log_driver_coverage(dataset, data_cfg)
    is_v2 = is_stage2_v2_protocol(data_cfg.stage2_protocol)
    if is_v2:
        if bool(config["training"].get("require_dgh_stats", False)):
            raise ValueError(
                "earthnet2021x_path_v2 must not require legacy DGH statistics; "
                "use data.conditioning_stats_path and "
                "scripts/build_earthnet_conditioning_stats.py instead."
            )
        if bool(config["training"].get("require_full_conditioning_stats", True)):
            stats = data_cfg.conditioning_stats
            if stats is None or stats.is_identity_smoke_stats:
                raise RuntimeError(
                    "Formal Stage2-v2 training requires non-identity train-only "
                    "conditioning statistics. Run "
                    "scripts/build_earthnet_conditioning_stats.py on the frozen "
                    "train manifest and pass --conditioning-stats-path."
                )
        driver_names = FULL24_FEATURE_NAMES
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
    sampler = DistributedSampler(dataset, num_replicas=world_size, rank=rank, shuffle=True) if distributed else None
    loader = DataLoader(
        dataset,
        batch_size=int(config["data"]["batch_size"]),
        sampler=sampler,
        shuffle=(sampler is None),
        num_workers=int(config["data"].get("num_workers", 4)),
        pin_memory=True,
        drop_last=True,
        collate_fn=collate_earthnet2021,
    )
    if len(loader) == 0:
        raise RuntimeError(
            f"Stage2 DataLoader has zero batches: samples={len(dataset)}, "
            f"batch_size={config['data']['batch_size']}, drop_last=True"
        )
    log_main(f"EarthNet samples: {len(dataset)}; batch={config['data']['batch_size']}; distributed={distributed}")

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
        validation_loader = DataLoader(
            validation_dataset,
            batch_size=int(
                validation_cfg.get("batch_size", config["data"]["batch_size"])
            ),
            shuffle=False,
            num_workers=int(
                validation_cfg.get("num_workers", config["data"].get("num_workers", 4))
            ),
            pin_memory=True,
            drop_last=False,
            collate_fn=collate_earthnet2021,
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
    if resume_from:
        resume_checkpoint = torch.load(resume_from, map_location="cpu", weights_only=False)
        raw_model = model.module if isinstance(model, DDP) else model
        load_stage2_model_state(raw_model, resume_checkpoint["model_state_dict"], strict=True)
        optimizer.load_state_dict(resume_checkpoint["optimizer_state_dict"])
        scheduler.load_state_dict(resume_checkpoint["scheduler_state_dict"])
        optimizer_step = int(resume_checkpoint.get("global_step", 0))
        if resume_checkpoint.get("best_validation"):
            best_validation = dict(resume_checkpoint["best_validation"])
        restore_rng_state(resume_checkpoint)
        log_main(f"resumed Stage2 from {resume_from} at optimizer_step={optimizer_step}")
    loss_fn = EarthNetForecastLoss.from_config(
        config["loss"],
        red_index=data_cfg.band_spec.red_index,
        nir_index=data_cfg.band_spec.nir_index,
    ).to(device)
    writer = (
        SummaryWriter(config["log_dir"])
        if is_main_process() and SummaryWriter is not None
        else None
    )
    if is_main_process() and SummaryWriter is None:
        log_main("warning: tensorboard is not installed; scalar logging is disabled")

    micro_step = optimizer_step * accum_steps
    epoch = 0
    model.train()
    optimizer.zero_grad(set_to_none=True)
    progress = tqdm(
        total=max_steps,
        initial=optimizer_step,
        disable=not is_main_process(),
        desc="Stage2 EarthNet",
    )
    while optimizer_step < max_steps:
        if sampler is not None:
            sampler.set_epoch(epoch)
        for batch in loader:
            batch = move_batch_to_device(batch, device)
            selected_steps = None
            if is_stage2_v2_batch(batch):
                selected_steps = select_v2_horizon_indices(
                    batch["x_target"].shape[1],
                    horizons_per_sample,
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
                optimizer_step += 1
                progress.update(1)

                if is_main_process() and optimizer_step % int(config.get("log_interval", 50)) == 0:
                    learning_rates = scheduler.get_last_lr()
                    log = {k: float(v.detach().cpu()) for k, v in losses.items()}
                    progress.set_postfix({"loss": f"{log['total']:.4f}", "obs": f"{log['obs']:.4f}", "ndvi": f"{log['ndvi']:.4f}"})
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

                if (
                    validation_interval > 0
                    and optimizer_step > 0
                    and optimizer_step % validation_interval == 0
                ):
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
                            )
                            log_main(
                                f"new best {metric_name}={metric_value:.6f} "
                                f"at step={optimizer_step}"
                            )
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
                    )
                    barrier()

            if optimizer_step >= max_steps:
                break
        epoch += 1

    if optimizer_step % checkpoint_interval != 0:
        save_checkpoint(
            os.path.join(config["checkpoint_dir"], f"checkpoint_step_{optimizer_step}.pt"),
            optimizer_step,
            model,
            optimizer,
            scheduler,
            config,
            best_validation=best_validation,
        )
    if writer is not None:
        writer.close()
    cleanup_distributed()


if __name__ == "__main__":
    main()
