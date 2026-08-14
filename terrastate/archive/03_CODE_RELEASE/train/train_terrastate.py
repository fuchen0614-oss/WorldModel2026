#!/usr/bin/env python
"""Train TerraState with forecast, distillation, and future-state objectives."""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

import torch
import torch.distributed as dist
import torch.nn.functional as F
import yaml
from torch.nn.parallel import DistributedDataParallel
from torch.utils.data import DataLoader, DistributedSampler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.dataset import GreenEarthNetDataset  # noqa: E402
from models.terrastate import HistoryOperator, TerraState, load_checkpoint  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--initial-checkpoint", required=True)
    parser.add_argument("--teacher-checkpoint", required=True)
    parser.add_argument("--future-state-cache", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--resume")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_yaml(path):
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def schedule_weight(update, total):
    fraction = update / max(total, 1)
    if fraction < 0.2:
        return 0.02 * fraction / 0.2
    if fraction < 0.8:
        return 0.02
    return 0.01


def learning_rate_factor(update, warmup, total):
    if update < warmup:
        return update / max(warmup, 1)
    progress = (update - warmup) / max(total - warmup, 1)
    return 0.5 * (1.0 + math.cos(math.pi * min(progress, 1.0)))


def move(value, device):
    if torch.is_tensor(value):
        return value.to(device)
    if isinstance(value, list):
        return [move(item, device) for item in value]
    if isinstance(value, dict):
        return {key: move(item, device) for key, item in value.items()}
    return value


def model_state(payload):
    if not isinstance(payload, dict):
        return payload
    return payload.get("model_state_dict", payload.get("state_dict", payload))


def load_teacher(path, device):
    teacher = HistoryOperator(pvt_pretrained=False)
    payload = torch.load(path, map_location="cpu", weights_only=False)
    state = model_state(payload)
    history_state = {
        key[2:]: value for key, value in state.items() if key.startswith("q.")
    }
    if not history_state:
        history_state = state
    teacher.load_state_dict(history_state, strict=True)
    teacher.to(device).eval()
    for parameter in teacher.parameters():
        parameter.requires_grad_(False)
    return teacher


class FutureStateCache:
    def __init__(self, path):
        self.payload = torch.load(path, map_location="cpu", weights_only=False)

    def get(self, paths, device):
        states, masks = [], []
        for path in paths:
            record = self.payload.get(path)
            if record is None:
                record = self.payload.get(Path(path).name)
            if record is None:
                raise KeyError(f"Future-state cache has no entry for {path}")
            states.append(record["state"])
            masks.append(record["mask"])
        return (
            torch.cat(states, dim=0).to(device),
            torch.cat(masks, dim=0).to(device),
        )


def ground_truth_loss(prediction, batch):
    start, steps = 10, 20
    target = batch["dynamic"][0][:, start : start + steps, :1]
    clear = (batch["dynamic_mask"][0][:, start : start + steps] < 1).float()
    vegetation = (
        (batch["landcover"] >= 10) & (batch["landcover"] <= 40)
    ).float()
    per_pixel = ((prediction - target).square() * clear).sum(1) / (
        clear.sum(1) + 1e-8
    )
    valid_prediction = (prediction != -1).any(1).float()
    weight = vegetation * valid_prediction
    return (per_pixel * weight).sum() / (weight.sum() + 1e-8)


def distillation_loss(prediction, teacher_prediction, batch):
    target_mask = (batch["dynamic_mask"][0][:, 10:30] < 1).float()
    vegetation = (
        (batch["landcover"] >= 10) & (batch["landcover"] <= 40)
    ).float().unsqueeze(1)
    valid = target_mask * vegetation
    return (
        (prediction - teacher_prediction.detach()).square() * valid
    ).sum() / (valid.sum() + 1e-8)


def future_state_loss(state, target, mask):
    state = F.layer_norm(state, (state.shape[-1],))
    target = F.layer_norm(target.detach(), (target.shape[-1],))
    values = 1.0 - F.cosine_similarity(state, target, dim=-1)
    mask = mask.to(values.dtype)
    return (values * mask).sum() / (mask.sum() + 1e-6)


def main():
    args = parse_args()
    config = load_yaml(args.config)
    training = config["training"]
    if args.dry_run:
        print(
            f"epochs={training['epochs']} "
            f"optimizer_updates={training['optimizer_updates']} "
            f"global_batch={training['global_batch']}"
        )
        return

    world_size = int(os.environ.get("WORLD_SIZE", "1"))
    rank = int(os.environ.get("RANK", "0"))
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    if world_size > 1:
        dist.init_process_group("nccl" if args.device == "cuda" else "gloo")
    device = torch.device(
        f"cuda:{local_rank}" if args.device == "cuda" else args.device
    )

    model = TerraState(
        state_dim=config["model"]["state_dim"],
        weather_dim=config["model"]["weather_dim"],
        geography_dim=config["model"]["geography_dim"],
        horizon_dim=config["model"]["horizon_dim"],
        condition_dim=config["model"]["condition_dim"],
        history_pretrained=False,
    )
    load_checkpoint(model, args.initial_checkpoint, strict=True)
    model.to(device)
    teacher = load_teacher(args.teacher_checkpoint, device)
    cache = FutureStateCache(args.future_state_cache)

    dataset = GreenEarthNetDataset(args.data_root)
    sampler = (
        DistributedSampler(dataset, world_size, rank, shuffle=True)
        if world_size > 1
        else None
    )
    per_device = int(config["data"]["per_device_batch"])
    loader = DataLoader(
        dataset,
        batch_size=per_device,
        sampler=sampler,
        shuffle=sampler is None,
        num_workers=int(config["data"]["workers"]),
        drop_last=True,
    )
    accumulation = int(training["global_batch"]) // (per_device * world_size)
    if accumulation < 1 or per_device * world_size * accumulation != int(
        training["global_batch"]
    ):
        raise ValueError("Global batch is incompatible with process count")

    branch = [
        parameter
        for name, parameter in model.named_parameters()
        if not name.startswith("q.")
    ]
    history = [
        parameter
        for name, parameter in model.named_parameters()
        if name.startswith("q.")
    ]
    optimizer = torch.optim.AdamW(
        [
            {
                "params": branch,
                "lr": float(training["branch_learning_rate"]),
            },
            {
                "params": history,
                "lr": float(training["history_learning_rate"]),
            },
        ],
        betas=tuple(training["betas"]),
        weight_decay=float(training["weight_decay"]),
    )
    total_updates = int(training["optimizer_updates"])
    warmup = int(training["learning_rate_warmup_updates"])
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer,
        lambda update: learning_rate_factor(update, warmup, total_updates),
    )
    update = 0
    start_epoch = 0
    if args.resume:
        payload = torch.load(args.resume, map_location="cpu", weights_only=False)
        model.load_state_dict(payload["model_state_dict"], strict=True)
        optimizer.load_state_dict(payload["optimizer_state_dict"])
        scheduler.load_state_dict(payload["scheduler_state_dict"])
        update = int(payload["optimizer_update"])
        start_epoch = int(payload["epoch"])

    wrapped = (
        DistributedDataParallel(model, device_ids=[local_rank])
        if world_size > 1 and device.type == "cuda"
        else DistributedDataParallel(model)
        if world_size > 1
        else model
    )
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    optimizer.zero_grad(set_to_none=True)
    for epoch in range(start_epoch, int(training["epochs"])):
        if sampler is not None:
            sampler.set_epoch(epoch)
        for micro, batch in enumerate(loader):
            if update >= total_updates:
                break
            enable_history = update >= int(0.8 * total_updates)
            model.set_history_trainable(enable_history, final_block_only=True)
            batch = move(batch, device)
            with torch.no_grad():
                teacher_prediction, _ = teacher.encode(
                    batch, pred_start=10, preds_length=20
                )
            target_state, patch_mask = cache.get(batch["filepath"], device)
            parts = wrapped(batch, return_parts=True)
            prediction = parts["prediction"]
            loss_gt = ground_truth_loss(prediction, batch)
            loss_kd = distillation_loss(prediction, teacher_prediction, batch)
            loss_fs = future_state_loss(
                parts["advanced_states"][:, -1], target_state, patch_mask
            )
            weight_fs = schedule_weight(update, total_updates)
            loss = loss_gt + 0.5 * loss_kd + weight_fs * loss_fs
            (loss / accumulation).backward()
            if (micro + 1) % accumulation == 0:
                torch.nn.utils.clip_grad_norm_(
                    model.parameters(), float(training["gradient_clip_norm"])
                )
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                update += 1
        if rank == 0:
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "scheduler_state_dict": scheduler.state_dict(),
                    "optimizer_update": update,
                    "epoch": epoch + 1,
                    "config": config,
                },
                output / "checkpoint_last.pt",
            )
        if update >= total_updates:
            break
    if update != total_updates:
        raise RuntimeError(
            f"Training ended at update {update}; expected {total_updates}"
        )
    if world_size > 1:
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
