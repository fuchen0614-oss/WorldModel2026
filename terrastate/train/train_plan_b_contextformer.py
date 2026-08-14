#!/usr/bin/env python
"""plan-b-pvt · B0 matched fine-tune of the reproduced Contextformer.

Trains the vendored ContextFormer (PVTContextformerQ) on GreenEarthNet train
with MaskedL2NDVILoss, on 8×H200 via torchrun DDP. This is the Gate-0 matched
baseline (B0): all ablation rows B1-B4 (state contract) share this init/data/
budget; with the contract off, this IS B0.

Faithful to the official recipe: at train time the model runs with token-masking
(mtm) active (model.train()); the loss is masked L2 on target-window NDVI over
clear + vegetation + valid-prediction pixels.

Launch (via scripts/train_plan_b_ctx.sh, or directly):
  torchrun --standalone --nproc_per_node=8 -m train.train_plan_b_contextformer \
    --train-dir $DATA_GEN/train --val-dir $DATA_GEN/val_chopped \
    --init-ckpt checkpoints/contextformer_official/contextformer6M/seed42.ckpt \
    --output-dir checkpoints/plan_b_b0 --per-gpu-batch 8 --max-epochs 40 --lr 1e-5
Smoke (1 GPU, few steps): add --max-steps 3 --per-gpu-batch 2
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from contextlib import nullcontext
from pathlib import Path

# benign DDP perf hint from the PVT conv grad layout — floods the log, mute it
warnings.filterwarnings("ignore", message=".*Grad strides do not match.*")

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.greenearthnet_contextformer_dataset import (  # noqa: E402
    GreenEarthNetContextformerDataset,
)
from models.encoders.pvt_contextformer_q import (  # noqa: E402
    PVTContextformerQ,
    contextformer6m_hparams,
    load_official_ckpt,
)
from models.losses.masked_l2_ndvi import MaskedL2NDVILoss  # noqa: E402


def collate(samples):
    return {
        "dynamic": [
            torch.stack([s["dynamic"][0] for s in samples]),
            torch.stack([s["dynamic"][1] for s in samples]),
        ],
        "dynamic_mask": [torch.stack([s["dynamic_mask"][0] for s in samples])],
        "static": [torch.stack([s["static"][0] for s in samples])],
        "landcover": torch.stack([s["landcover"] for s in samples]),
    }


def to_device(batch, dev):
    return {
        "dynamic": [batch["dynamic"][0].to(dev), batch["dynamic"][1].to(dev)],
        "dynamic_mask": [batch["dynamic_mask"][0].to(dev)],
        "static": [batch["static"][0].to(dev)],
        "landcover": batch["landcover"].to(dev),
    }


def is_dist():
    return dist.is_available() and dist.is_initialized()


def rank0():
    return (not is_dist()) or dist.get_rank() == 0


def log(msg):
    if rank0():
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


@torch.no_grad()
def validate(model, loader, loss_fn, dev, max_batches=50):
    model.eval()
    tot, n = 0.0, 0
    for i, batch in enumerate(loader):
        if i >= max_batches:
            break
        data = to_device(batch, dev)
        # eval mode: must pass pred_start/preds_length explicitly (c_l=pred_start),
        # else default pred_start=0 masks every frame.
        preds = model(data, pred_start=10, preds_length=20)
        loss, _ = loss_fn(preds, data)
        if torch.isfinite(loss):
            tot += loss.item()
            n += 1
    model.train()
    val = tot / max(n, 1)
    if is_dist():
        t = torch.tensor([val, n], device=dev, dtype=torch.float64)
        dist.all_reduce(t, op=dist.ReduceOp.SUM)
        val = (t[0] / t[1]).item() if t[1] > 0 else float("inf")
    return val


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-dir", required=True)
    ap.add_argument("--val-dir", required=True)
    ap.add_argument("--init-ckpt", default="", help="official ckpt to warm-start from")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--per-gpu-batch", type=int, default=8)
    ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--max-epochs", type=int, default=40)
    ap.add_argument("--max-steps", type=int, default=0, help=">0 overrides epochs (smoke)")
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--milestones", type=int, nargs="*", default=[])
    ap.add_argument("--gamma", type=float, default=0.1)
    ap.add_argument("--grad-clip", type=float, default=1.0)
    ap.add_argument("--log-interval", type=int, default=50)
    ap.add_argument("--val-interval", type=int, default=1000)
    ap.add_argument("--ckpt-interval", type=int, default=2000)
    ap.add_argument("--bf16", action="store_true",
                    help="opt-in bf16 autocast (default fp32; this model + bf16 is unstable, "
                         "and fp32 matches the official/parity setup)")
    # --- ObsWorld state contract (B1-B4). Default off = B0. ---
    ap.add_argument("--use-state", action="store_true", help="B1+: add state projector")
    ap.add_argument("--use-latent-future", action="store_true", help="B2+: latent-future consistency")
    ap.add_argument("--lambda-dyn", type=float, default=0.0, help="weight of latent-future loss")
    args = ap.parse_args()

    # DDP init
    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    world = int(os.environ.get("WORLD_SIZE", 1))
    if world > 1:
        dist.init_process_group("nccl", device_id=torch.device("cuda", local_rank))
        torch.cuda.set_device(local_rank)
    dev = torch.device("cuda", local_rank) if torch.cuda.is_available() else torch.device("cpu")

    out = Path(args.output_dir)
    if rank0():
        out.mkdir(parents=True, exist_ok=True)

    # Model (base contextformer6M) + optional official warm-start + optional contract
    hp = contextformer6m_hparams(pvt_pretrained=(args.init_ckpt == ""))
    contract_cfg = None
    if args.use_state or args.use_latent_future or args.lambda_dyn > 0:
        contract_cfg = {
            "use_state": args.use_state or args.use_latent_future,
            "use_latent_future": args.use_latent_future or args.lambda_dyn > 0,
        }
    model = PVTContextformerQ(hp, contract_cfg=contract_cfg).to(dev)
    use_contract = contract_cfg is not None
    from types import SimpleNamespace
    lambdas = SimpleNamespace(dyn=args.lambda_dyn)
    log(f"contract: {contract_cfg}  lambda_dyn={args.lambda_dyn}")
    if args.init_ckpt:
        miss, unexp = load_official_ckpt(model.core, args.init_ckpt, strict=True)
        log(f"warm-start {args.init_ckpt}: missing={len(miss)} unexpected={len(unexp)}")
    model.train()
    if world > 1:
        model = DDP(model, device_ids=[local_rank], find_unused_parameters=False)

    loss_fn = MaskedL2NDVILoss(
        lc_min=10, lc_max=40, context_length=10, target_length=20,
        ndvi_pred_idx=0, ndvi_targ_idx=0, pred_mask_value=-1, scale_by_std=False,
    )

    train_ds = GreenEarthNetContextformerDataset(args.train_dir, dl_cloudmask=True)
    val_ds = GreenEarthNetContextformerDataset(args.val_dir, dl_cloudmask=True)
    log(f"train cubes={len(train_ds)}  val cubes={len(val_ds)}")

    train_sampler = DistributedSampler(train_ds, shuffle=True) if world > 1 else None
    train_loader = DataLoader(
        train_ds, batch_size=args.per_gpu_batch, sampler=train_sampler,
        shuffle=(train_sampler is None), num_workers=args.num_workers,
        collate_fn=collate, pin_memory=True, drop_last=True, persistent_workers=args.num_workers > 0,
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.per_gpu_batch, shuffle=False,
        num_workers=args.num_workers, collate_fn=collate, pin_memory=True,
    )

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.999),
                            weight_decay=args.weight_decay)
    sched = torch.optim.lr_scheduler.MultiStepLR(opt, milestones=args.milestones, gamma=args.gamma) \
        if args.milestones else None
    use_bf16 = args.bf16 and dev.type == "cuda"

    steps_per_epoch = max(len(train_loader), 1)
    total_steps = args.max_steps if args.max_steps > 0 else args.max_epochs * steps_per_epoch
    log(f"steps/epoch={steps_per_epoch}  total_steps={total_steps}  bf16={use_bf16}")

    best_val = float("inf")
    step = 0
    t0 = time.time()
    done = False
    for epoch in range(10_000):
        if done:
            break
        if train_sampler is not None:
            train_sampler.set_epoch(epoch)
        for batch in train_loader:
            data = to_device(batch, dev)
            opt.zero_grad(set_to_none=True)
            ctx = torch.autocast("cuda", dtype=torch.bfloat16) if use_bf16 else nullcontext()
            with ctx:
                if use_contract:
                    preds, contract = model(data, with_contract=True, lambdas=lambdas)
                else:
                    preds = model(data)
                    contract = None
            preds_l = preds.float() if use_bf16 else preds
            loss, logs = loss_fn(preds_l, data)
            if contract is not None:
                loss = loss + (contract["total"].float() if use_bf16 else contract["total"])
                logs.update({k: v for k, v in contract["logs"].items()})
            if not torch.isfinite(loss):
                log(f"WARN non-finite loss at step {step}; skipping")
                opt.zero_grad(set_to_none=True)
                step += 1
                continue
            loss.backward()
            if args.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
            opt.step()
            if sched:
                sched.step()
            step += 1

            if step % args.log_interval == 0:
                ips = step / (time.time() - t0)
                log(f"step {step}/{total_steps}  loss={loss.item():.5f}  lr={opt.param_groups[0]['lr']:.2e}  {ips:.2f} it/s")
            if step % args.val_interval == 0 or step == total_steps:
                vloss = validate(model, val_loader, loss_fn, dev)
                log(f"  [val] step {step}  val_loss={vloss:.5f}  (best {best_val:.5f})")
                if rank0() and vloss < best_val:
                    best_val = vloss
                    _save(model, out / "checkpoint_best.pt", step, vloss, args)
                    log(f"  saved best (val_loss={vloss:.5f})")
            if rank0() and step % args.ckpt_interval == 0:
                _save(model, out / f"checkpoint_step{step}.pt", step, None, args)
            if step >= total_steps:
                done = True
                break

    if rank0():
        _save(model, out / "checkpoint_last.pt", step, None, args)
        log(f"done. best_val={best_val:.5f}  out={out}")
    if is_dist():
        dist.barrier()
        dist.destroy_process_group()


def _save(model, path, step, val, args):
    core = (model.module if hasattr(model, "module") else model).core
    torch.save(
        {
            "core_state_dict": core.state_dict(),
            "step": step,
            "val_loss": val,
            "arch": "contextformer6M",
            "args": vars(args),
        },
        path,
    )


if __name__ == "__main__":
    main()
