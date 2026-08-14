#!/usr/bin/env python
"""plan-b-pvt · Stage1.8 factorization training (SSL4EO L1C/L2A, 8-GPU DDP).

Trains Stage18Factorizer (q + phi + O_product) on the cached paired subset with
recon + cross-render + paired-state losses. Small (~hundreds of steps): produces
the Table-2 / Fig-3 world-model evidence (phi-controlled cross-product rendering).

Launch: scripts/train_stage1_8.sh   (or directly via torch.distributed.run)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*Grad strides do not match.*")

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.ssl4eo_l1c_l2a_paired import SSL4EOL1CL2APairedDataset  # noqa: E402
from models.stage1_8_factorizer import Stage18Factorizer  # noqa: E402


def is_dist():
    return dist.is_available() and dist.is_initialized()


def rank0():
    return (not is_dist()) or dist.get_rank() == 0


def log(msg):
    if rank0():
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--per-gpu-batch", type=int, default=32)
    ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--max-epochs", type=int, default=30)
    ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--lambda-paired", type=float, default=1.0)
    ap.add_argument("--pvt-pretrained", action="store_true")
    ap.add_argument("--log-interval", type=int, default=20)
    ap.add_argument("--ckpt-interval", type=int, default=500)
    args = ap.parse_args()

    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    world = int(os.environ.get("WORLD_SIZE", 1))
    if world > 1:
        dist.init_process_group("nccl", device_id=torch.device("cuda", local_rank))
        torch.cuda.set_device(local_rank)
    dev = torch.device("cuda", local_rank) if torch.cuda.is_available() else torch.device("cpu")

    out = Path(args.output_dir)
    if rank0():
        out.mkdir(parents=True, exist_ok=True)

    model = Stage18Factorizer(in_ch=4, state_dim=256, pvt_pretrained=args.pvt_pretrained).to(dev)
    model.train()
    if world > 1:
        model = DDP(model, device_ids=[local_rank], find_unused_parameters=False)

    ds = SSL4EOL1CL2APairedDataset(args.cache_dir)
    log(f"paired samples={len(ds)}")
    sampler = DistributedSampler(ds, shuffle=True) if world > 1 else None
    loader = DataLoader(
        ds, batch_size=args.per_gpu_batch, sampler=sampler, shuffle=(sampler is None),
        num_workers=args.num_workers, pin_memory=True, drop_last=True,
        persistent_workers=args.num_workers > 0,
    )
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.999))

    steps_per_epoch = max(len(loader), 1)
    total_steps = args.max_steps if args.max_steps > 0 else args.max_epochs * steps_per_epoch
    log(f"steps/epoch={steps_per_epoch}  total_steps={total_steps}  lr={args.lr}")

    step, t0, done = 0, time.time(), False
    for epoch in range(10_000):
        if done:
            break
        if sampler is not None:
            sampler.set_epoch(epoch)
        for batch in loader:
            l1c, l2a = batch["l1c"].to(dev), batch["l2a"].to(dev)
            opt.zero_grad(set_to_none=True)
            out_d = model(l1c, l2a, lambda_paired=args.lambda_paired)
            out_d["total"].backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            step += 1
            if step % args.log_interval == 0:
                ips = step / (time.time() - t0)
                log(f"step {step}/{total_steps}  total={out_d['total'].item():.4f} "
                    f"recon={out_d['recon'].item():.4f} cross={out_d['cross'].item():.4f} "
                    f"paired={out_d['paired'].item():.4f}  {ips:.2f} it/s")
            if rank0() and (step % args.ckpt_interval == 0 or step == total_steps):
                core = (model.module if hasattr(model, "module") else model)
                torch.save({"model_state_dict": core.state_dict(), "step": step, "args": vars(args)},
                           out / "checkpoint_last.pt")
            if step >= total_steps:
                done = True
                break

    if rank0():
        log(f"done. steps={step}  out={out}")
    if is_dist():
        dist.barrier()
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
