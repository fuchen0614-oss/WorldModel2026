"""Stage 1.5: dual-ended acquisition conditioning and explicit state tokens.

Canonical factorization:
    state_t = Encoder(image_t, phi_t)
    image_hat_t = AuxiliaryDecoder(state_features_t, phi_t)

Only near-contemporaneous S1/S2 pairs are aligned.  Cross-season invariance and
shuffle-phi invariance are intentionally absent because they erase real change
or contradict conditional inference.
"""

import argparse
import math
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, Tuple

import torch
import torch.distributed as dist
import torch.nn as nn
import torch.optim as optim
import yaml
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.ssl4eo_dual import SSL4EODualConfig, create_ssl4eo_dual_dataset
from models.decoders.dual_head_decoder import DualHeadDecoder
from models.encoders.multimodal_vit_encoder import MultiModalViTEncoder
from models.encoders.multimodal_vit_encoder_film import MultiModalViTEncoderFiLM
from models.encoders.pure_imaging_condition_encoder import PureImagingConditionEncoder
from models.encoders.state_projection import SpatialStateProjector
from models.losses.stage1_5_state import (
    CrossModalVICRegLoss, FeatureAnchorLoss, PhiCrossCovarianceLoss,
    masked_pixel_reconstruction_loss, s2_clear_pixel_mask,
)
from train.fsdp_utils import (
    barrier, cleanup_distributed, get_full_optim_state_dict, get_full_state_dict,
    is_distributed, is_main_process, setup_distributed, wrap_model_fsdp2,
)


def log_main(message: str) -> None:
    if is_main_process():
        print(message, flush=True)


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def to_device(values: Dict[str, torch.Tensor], device: torch.device) -> Dict[str, torch.Tensor]:
    return {k: v.to(device, non_blocking=True) if torch.is_tensor(v) else v for k, v in values.items()}


def create_models(config: dict):
    model_cfg = config["model"]
    enc_cfg = {k: v for k, v in model_cfg["encoder"].items() if k != "type"}
    phi_cfg = {k: v for k, v in model_cfg["phi_encoder"].items() if k != "type"}
    dec_cfg = {k: v for k, v in model_cfg["decoder"].items() if k != "type"}
    state_cfg = {k: v for k, v in model_cfg["state_projector"].items() if k != "type"}
    encoder = MultiModalViTEncoderFiLM(**enc_cfg)
    phi_encoder = PureImagingConditionEncoder(**phi_cfg)
    decoder = DualHeadDecoder(**dec_cfg)
    state_projector = SpatialStateProjector(**state_cfg)
    teacher_cfg = {k: enc_cfg[k] for k in (
        "img_size", "s1_channels", "s2_channels", "patch_size", "embed_dim",
        "depth", "num_heads", "mlp_ratio", "dropout")}
    teacher = MultiModalViTEncoder(**teacher_cfg)
    return encoder, phi_encoder, decoder, state_projector, teacher


def load_stage1_checkpoint(encoder, decoder, teacher, checkpoint_path: str) -> dict:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    enc_state = checkpoint["encoder_state_dict"]
    dec_state = checkpoint["decoder_state_dict"]

    info = encoder.load_stage1_encoder_weights(enc_state, strict=False)
    bad_missing = [k for k in info["new_params"] if ".film." not in k]
    if info["unexpected"] or bad_missing or info["loaded_from_stage1"] != len(enc_state):
        raise RuntimeError(
            "Stage1 encoder is not fully compatible: "
            f"loaded={info['loaded_from_stage1']}/{len(enc_state)}, "
            f"unexpected={info['unexpected'][:5]}, bad_missing={bad_missing[:5]}"
        )
    dec_result = decoder.load_state_dict(dec_state, strict=False)
    bad_dec_missing = [k for k in dec_result.missing_keys if ".film." not in k]
    if dec_result.unexpected_keys or bad_dec_missing:
        raise RuntimeError(
            f"Stage1 decoder mismatch: unexpected={dec_result.unexpected_keys[:5]}, "
            f"bad_missing={bad_dec_missing[:5]}"
        )
    teacher.load_state_dict(enc_state, strict=True)
    teacher.requires_grad_(False).eval()
    return {
        "global_step": checkpoint.get("global_step"),
        "encoder_tensors": len(enc_state),
        "new_encoder_tensors": len(info["new_params"]),
        "new_decoder_tensors": len(dec_result.missing_keys),
    }


def _all_gather_with_grad(tensor: torch.Tensor) -> torch.Tensor:
    if not is_distributed():
        return tensor
    from torch.distributed.nn.functional import all_gather
    return torch.cat(all_gather(tensor), dim=0)


def _all_gather_mask(mask: torch.Tensor) -> torch.Tensor:
    if not is_distributed():
        return mask
    gathered = [torch.empty_like(mask) for _ in range(dist.get_world_size())]
    dist.all_gather(gathered, mask)
    return torch.cat(gathered, dim=0)


def scheduled_weights(step: int, config: dict) -> Dict[str, float]:
    loss_cfg = config["training"]["loss_weights"]
    ramp_end = max(1, int(loss_cfg.get("ramp_end_step", 10000)))
    progress = min(1.0, step / ramp_end)
    out = {"mae": float(loss_cfg.get("mae", 1.0)), "anchor": float(loss_cfg.get("anchor", 0.1))}
    for name in ("alignment", "nuisance"):
        start = float(loss_cfg[f"{name}_start"])
        end = float(loss_cfg[f"{name}_end"])
        out[name] = start + progress * (end - start)
    return out


def stage_for_step(step: int, config: dict) -> int:
    freeze_new = int(config["training"].get("new_modules_only_steps", 2000))
    partial = int(config["training"].get("partial_unfreeze_steps", 10000))
    return 1 if step < freeze_new else (2 if step < partial else 3)


def apply_training_stage(encoder, phi_encoder, decoder, state_projector, stage: int, film_start: int) -> None:
    for module in (encoder, phi_encoder, decoder, state_projector):
        module.requires_grad_(False)
    phi_encoder.requires_grad_(True)
    state_projector.requires_grad_(True)
    for name, parameter in encoder.named_parameters():
        if ".film." in name:
            parameter.requires_grad_(True)
    for name, parameter in decoder.named_parameters():
        if ".film." in name:
            parameter.requires_grad_(True)
    if stage >= 2:
        encoder.norm.requires_grad_(True)
        for block in encoder.blocks[film_start:]:
            block.requires_grad_(True)
    if stage >= 3:
        encoder.requires_grad_(True)
        decoder.requires_grad_(True)


def build_optimizer(model: nn.ModuleDict, config: dict) -> optim.Optimizer:
    opt_cfg = config["optimizer"]
    new_params, base_params = [], []
    for name, parameter in model.named_parameters():
        if name.startswith("phi_encoder.") or name.startswith("state_projector.") or ".film." in name:
            new_params.append(parameter)
        else:
            base_params.append(parameter)
    return optim.AdamW([
        {"params": base_params, "lr": float(opt_cfg["base_lr"]), "group_name": "pretrained"},
        {"params": new_params, "lr": float(opt_cfg["new_lr"]), "group_name": "new"},
    ], weight_decay=float(opt_cfg.get("weight_decay", 0.05)),
       betas=tuple(opt_cfg.get("betas", [0.9, 0.95])))


def build_scheduler(optimizer, max_steps: int, warmup: int, config: dict):
    opt_cfg = config["optimizer"]
    starts = [float(opt_cfg["base_lr"]), float(opt_cfg["new_lr"])]
    minima = [float(opt_cfg["base_min_lr"]), float(opt_cfg["new_min_lr"])]

    def make_lambda(start, minimum):
        floor = minimum / start
        def fn(step):
            if step < warmup:
                return (step + 1) / max(1, warmup)
            progress = min(1.0, (step - warmup) / max(1, max_steps - warmup))
            return floor + (1.0 - floor) * 0.5 * (1.0 + math.cos(math.pi * progress))
        return fn
    return optim.lr_scheduler.LambdaLR(
        optimizer, [make_lambda(s, m) for s, m in zip(starts, minima)])


def train_micro_step(batch, device, encoder, phi_encoder, decoder, state_projector, teacher,
                     losses, config, optimizer_step: int):
    s1 = batch["s1_image"].to(device, non_blocking=True)
    s2 = batch["s2_image"].to(device, non_blocking=True)
    phi_s1 = to_device(batch["s1_phi"], device)
    phi_s2 = to_device(batch["s2_phi"], device)
    cloud = batch["cloud_mask"].to(device, non_blocking=True)
    delta = batch["time_delta_days"].to(device)
    pair_valid = batch["time_pair_valid"].to(device) & delta.le(float(config["data"]["pair_max_days"]))
    mask_ratio = float(config["training"].get("mask_ratio", 0.75))
    recon_kind = config["training"].get("recon_loss", "l1")

    amp = torch.autocast(device_type="cuda", dtype=torch.bfloat16) if device.type == "cuda" else torch.autocast(device_type="cpu", enabled=False)
    with amp:
        pe_s1 = phi_encoder(phi_s1)
        pe_s2 = phi_encoder(phi_s2)
        lat_s1, mask_s1, ids_s1 = encoder(s1, "S1", mask_ratio, phi_embed=pe_s1)
        lat_s2, mask_s2, ids_s2 = encoder(s2, "S2", mask_ratio, phi_embed=pe_s2)
        rec_s1 = decoder(lat_s1, "S1", ids_s1, mask_s1, phi_embed=pe_s1)
        rec_s2 = decoder(lat_s2, "S2", ids_s2, mask_s2, phi_embed=pe_s2)
        mae_s1 = masked_pixel_reconstruction_loss(rec_s1, s1, mask_s1, loss_type=recon_kind)
        mae_s2 = masked_pixel_reconstruction_loss(
            rec_s2, s2, mask_s2, quality_mask=s2_clear_pixel_mask(cloud), loss_type=recon_kind)
        mae = 0.5 * (mae_s1 + mae_s2)

        state_s1 = state_projector(lat_s1)
        state_s2 = state_projector(lat_s2)
        pooled_s1 = state_projector.pool(state_s1)
        pooled_s2 = state_projector.pool(state_s2)
        global_s1 = _all_gather_with_grad(pooled_s1)
        global_s2 = _all_gather_with_grad(pooled_s2)
        global_valid = _all_gather_mask(pair_valid)
        aligned = losses["alignment"](global_s1, global_s2, global_valid)
        nuisance = 0.5 * (
            losses["nuisance"](pooled_s1, phi_s1, "S1")
            + losses["nuisance"](pooled_s2, phi_s2, "S2"))

        with torch.no_grad():
            teacher_s1 = teacher(s1, "S1", mask_ratio=0.0)[0]
            teacher_s2 = teacher(s2, "S2", mask_ratio=0.0)[0]
        anchor = 0.5 * (
            losses["anchor"](lat_s1, teacher_s1)
            + losses["anchor"](lat_s2, teacher_s2))
        weights = scheduled_weights(optimizer_step, config)
        total = (weights["mae"] * mae + weights["alignment"] * aligned["total"]
                 + weights["nuisance"] * nuisance + weights["anchor"] * anchor)

    logs = {
        "total": total.detach().item(), "mae_s1": mae_s1.detach().item(),
        "mae_s2": mae_s2.detach().item(), "alignment": aligned["total"].detach().item(),
        "invariance": aligned["invariance"].detach().item(),
        "nuisance": nuisance.detach().item(), "anchor": anchor.detach().item(),
        "pair_valid_rate": pair_valid.float().mean().item(),
        "time_delta_days": delta.mean().item(),
    }
    return total, logs


def save_checkpoint(path: str, step: int, model, encoder, phi_encoder, decoder,
                    state_projector, optimizer, config):
    states = {
        "encoder_state_dict": get_full_state_dict(encoder),
        "phi_encoder_state_dict": get_full_state_dict(phi_encoder),
        "decoder_state_dict": get_full_state_dict(decoder),
        "state_projector_state_dict": get_full_state_dict(state_projector),
        "optimizer_state_dict": get_full_optim_state_dict(model, optimizer),
    }
    if is_main_process():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save({"global_step": step, "config": config, **states}, path)
        log_main(f"checkpoint saved: {path}")
    barrier()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--checkpoint-interval", type=int)
    parser.add_argument("--batch-size", type=int, help="Per-rank override for smoke tests.")
    parser.add_argument("--num-workers", type=int, help="DataLoader worker override.")
    parser.add_argument("--accumulation-steps", type=int, help="Gradient accumulation override.")
    args = parser.parse_args()
    rank, local_rank, world_size, distributed = setup_distributed()
    config = load_config(args.config)
    if args.max_steps is not None:
        config["training"]["max_steps"] = args.max_steps
    if args.batch_size is not None:
        config["data"]["batch_size"] = args.batch_size
    if args.num_workers is not None:
        config["data"]["num_workers"] = args.num_workers
    if args.accumulation_steps is not None:
        config["training"]["gradient_accumulation_steps"] = args.accumulation_steps
    max_steps = int(config["training"]["max_steps"])
    accum_steps = int(config["training"].get("gradient_accumulation_steps", 1))
    checkpoint_interval = args.checkpoint_interval or int(config.get("checkpoint_interval", 5000))
    device = torch.device(f"cuda:{local_rank}" if torch.cuda.is_available() else "cpu")

    encoder, phi_encoder, decoder, state_projector, teacher = create_models(config)
    source = config["resume_from"]
    if not os.path.exists(source):
        raise FileNotFoundError(f"required Stage1 checkpoint missing: {source}")
    load_info = load_stage1_checkpoint(encoder, decoder, teacher, source)
    log_main(f"strict Stage1 load OK: {load_info}")
    for module in (encoder, phi_encoder, decoder, state_projector, teacher):
        module.to(device)

    if distributed:
        encoder = wrap_model_fsdp2(encoder, "bf16")
        phi_encoder = wrap_model_fsdp2(phi_encoder, "bf16")
        decoder = wrap_model_fsdp2(decoder, "bf16")
        state_projector = wrap_model_fsdp2(state_projector, "bf16")
    model = nn.ModuleDict({
        "encoder": encoder, "phi_encoder": phi_encoder,
        "decoder": decoder, "state_projector": state_projector,
    })
    optimizer = build_optimizer(model, config)
    scheduler = build_scheduler(
        optimizer, max_steps, int(config["training"].get("warmup_steps", 1000)), config)
    film_start = int(config["model"]["encoder"]["film_start_layer"])
    current_stage = stage_for_step(0, config)
    apply_training_stage(encoder, phi_encoder, decoder, state_projector, current_stage, film_start)

    data_cfg = config["data"]
    dataset_cfg = SSL4EODualConfig(
        split=data_cfg.get("split", "train"), random_season=True,
        base_path=data_cfg["data_root"], normalize=data_cfg.get("normalize", True),
        cache_size=data_cfg.get("cache_size", 500), shard_pattern=data_cfg["shard_pattern"],
        use_phi_cache=True, phi_cache_root=data_cfg["phi_cache_root"],
        v3_geom_root=data_cfg.get("v3_geom_root"), conditioned_pair=True,
    )
    loader = create_ssl4eo_dual_dataset(
        dataset_cfg, batch_size=int(data_cfg["batch_size"]),
        num_workers=int(data_cfg.get("num_workers", 4)), shuffle=True,
        infinite=distributed, prefetch_factor=int(data_cfg.get("prefetch_factor", 2)), seed=local_rank)

    losses = {
        "alignment": CrossModalVICRegLoss(**config["training"].get("vicreg", {})).to(device),
        "nuisance": PhiCrossCovarianceLoss().to(device),
        "anchor": FeatureAnchorLoss().to(device),
    }
    writer = None
    if is_main_process():
        Path(config["log_dir"]).mkdir(parents=True, exist_ok=True)
        writer = SummaryWriter(config["log_dir"])

    encoder.train(); phi_encoder.train(); decoder.train(); state_projector.train(); teacher.eval()
    iterator = tqdm(loader, disable=not is_main_process(), desc="Stage1.5 dual-conditioned")
    optimizer.zero_grad(set_to_none=True)
    step = micro = 0
    log_accum: Dict[str, float] = {}
    for batch in iterator:
        wanted_stage = stage_for_step(step, config)
        if wanted_stage != current_stage:
            current_stage = wanted_stage
            apply_training_stage(encoder, phi_encoder, decoder, state_projector, current_stage, film_start)
            log_main(f"entered training stage {current_stage} at optimizer step {step}")
        total, logs = train_micro_step(
            batch, device, encoder, phi_encoder, decoder, state_projector,
            teacher, losses, config, step)
        (total / accum_steps).backward()
        for key, value in logs.items():
            log_accum[key] = log_accum.get(key, 0.0) + value / accum_steps
        micro += 1
        if micro % accum_steps:
            continue
        torch.nn.utils.clip_grad_norm_(model.parameters(), float(config["training"].get("grad_clip", 1.0)))
        optimizer.step(); optimizer.zero_grad(set_to_none=True); scheduler.step(); step += 1

        if writer is not None:
            for key, value in log_accum.items():
                writer.add_scalar(f"train/{key}", value, step)
            for index, group in enumerate(optimizer.param_groups):
                writer.add_scalar(f"train/lr_{group.get('group_name', index)}", group["lr"], step)
        if step % int(config.get("log_interval", 50)) == 0:
            log_main(
                f"step={step}/{max_steps} stage={current_stage} total={log_accum['total']:.4f} "
                f"mae=({log_accum['mae_s1']:.4f},{log_accum['mae_s2']:.4f}) "
                f"align={log_accum['alignment']:.4f} nuisance={log_accum['nuisance']:.4f} "
                f"valid={log_accum['pair_valid_rate']:.3f}")
        log_accum = {}
        if step % checkpoint_interval == 0:
            save_checkpoint(
                os.path.join(config["checkpoint_dir"], f"checkpoint_step_{step}.pt"),
                step, model, encoder, phi_encoder, decoder, state_projector, optimizer, config)
        if step >= max_steps:
            break

    save_checkpoint(
        os.path.join(config["checkpoint_dir"], f"checkpoint_step_{step}.pt"),
        step, model, encoder, phi_encoder, decoder, state_projector, optimizer, config)
    if writer is not None:
        writer.close()
    cleanup_distributed()


if __name__ == "__main__":
    main()
