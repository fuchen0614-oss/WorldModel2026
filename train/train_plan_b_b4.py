#!/usr/bin/env python
"""plan-b-pvt · B4 training = ObsWorldB4 (shared-z world model) forecasting fine-tune.

Same data / loss / budget / recipe as B0 (train_plan_b_contextformer.py) — the ONLY
difference is the model (ObsWorldB4) and two aux λ on the SHARED state z:
  --lambda-dyn  : JEPA latent-future (transition predicts future state, stop-grad)
  --lambda-vic  : VICReg anti-collapse (variance hinge + covariance decorrelation)

Strong-baseline-recoverable: with both λ=0 the forward is byte-identical B0.

Ablation ladder:
  B4a = warm-start official ckpt + (dyn,vic)>0            (aux-only, cheapest test of "does the world model help")
  B4b = SSL4EO-pretrained encoder init + (dyn,vic)>0      (adds the representation lever)

Launch (server 8×H200):
  torchrun --standalone --nproc_per_node=8 -m train.train_plan_b_b4 \
    --train-dir $DATA_GEN/train --val-dir $DATA_GEN/val_chopped \
    --init-ckpt checkpoints/contextformer_official/contextformer6M/seed42.ckpt \
    --output-dir checkpoints/plan_b_b4a --per-gpu-batch 8 --max-epochs 40 --lr 1e-5 \
    --lambda-dyn 1.0 --lambda-vic 1.0
Local GPU training smoke (4-7 only, synthetic): scripts/smoke_b4_train.py
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import warnings
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

warnings.filterwarnings("ignore", message=".*Grad strides do not match.*")

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset  # noqa: E402
from models.encoders.pvt_contextformer_q import contextformer6m_hparams, load_official_ckpt  # noqa: E402
from models.losses.masked_l2_ndvi import MaskedL2NDVILoss  # noqa: E402
from models.plan_b_b4 import ObsWorldB4  # noqa: E402
# reuse the B0 trainer's data/eval plumbing verbatim (single source of truth)
from train.train_plan_b_contextformer import (  # noqa: E402
    collate, to_device, validate, log, is_dist, rank0,
)


def _save_b4(model, path, step, val, args):
    """Save the WHOLE ObsWorldB4 (q.core + projector + transition + renderer)."""
    m = model.module if hasattr(model, "module") else model
    torch.save(
        {
            "b4_state_dict": m.state_dict(),
            "core_state_dict": m.q.core.state_dict(),  # for scoring via from_checkpoint
            "step": step, "val_loss": val, "arch": "ObsWorldB4",
            "lambdas": {"dyn": args.lambda_dyn, "vic": args.lambda_vic},
            "args": vars(args),
        },
        path,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-dir", required=True)
    ap.add_argument("--val-dir", required=True)
    ap.add_argument("--init-ckpt", default="", help="official/B0 ckpt to warm-start the shared encoder+backbone")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--per-gpu-batch", type=int, default=8)
    ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--max-epochs", type=int, default=40)
    ap.add_argument("--max-steps", type=int, default=0, help=">0 overrides epochs (smoke)")
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--grad-clip", type=float, default=1.0)
    ap.add_argument("--log-interval", type=int, default=50)
    ap.add_argument("--val-interval", type=int, default=1000)
    ap.add_argument("--ckpt-interval", type=int, default=2000)
    ap.add_argument("--state-dim", type=int, default=256)
    ap.add_argument("--lambda-dyn", type=float, default=1.0, help="JEPA latent-future weight")
    ap.add_argument("--lambda-vic", type=float, default=1.0, help="VICReg anti-collapse weight")
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

    hp = contextformer6m_hparams(pvt_pretrained=(args.init_ckpt == ""))
    model = ObsWorldB4(hp, contract_cfg={"state_dim": args.state_dim, "n_products": 2}).to(dev)
    lambdas = SimpleNamespace(dyn=args.lambda_dyn, vic=args.lambda_vic)
    log(f"B4 ObsWorld  state_dim={args.state_dim}  lambda_dyn={args.lambda_dyn}  lambda_vic={args.lambda_vic}")
    if args.init_ckpt:
        miss, unexp = load_official_ckpt(model.q.core, args.init_ckpt, strict=True)
        log(f"warm-start q.core {args.init_ckpt}: missing={len(miss)} unexpected={len(unexp)}")
    model.train()
    if world > 1:
        # renderer is unused during forecasting fine-tune -> allow unused params
        model = DDP(model, device_ids=[local_rank], find_unused_parameters=True)

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

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.999), weight_decay=args.weight_decay)
    steps_per_epoch = max(len(train_loader), 1)
    total_steps = args.max_steps if args.max_steps > 0 else args.max_epochs * steps_per_epoch
    log(f"steps/epoch={steps_per_epoch}  total_steps={total_steps}")

    best_val, step, t0, done = float("inf"), 0, time.time(), False
    for epoch in range(10_000):
        if done:
            break
        if train_sampler is not None:
            train_sampler.set_epoch(epoch)
        for batch in train_loader:
            data = to_device(batch, dev)
            opt.zero_grad(set_to_none=True)
            preds, aux = model(data, lambdas=lambdas)          # training: full-seq preds + aux on shared z
            loss, logs = loss_fn(preds, data)
            loss = loss + aux["total"]
            logs.update({k: float(v) for k, v in aux["logs"].items()})
            if not torch.isfinite(loss):
                log(f"WARN non-finite loss at step {step}; skipping")
                opt.zero_grad(set_to_none=True); step += 1; continue
            loss.backward()
            if args.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
            opt.step()
            step += 1

            if step % args.log_interval == 0:
                ips = step / (time.time() - t0)
                extra = " ".join(f"{k}={logs[k]:.4f}" for k in ("latent_future", "vic_var", "vic_cov") if k in logs)
                log(f"step {step}/{total_steps}  loss={loss.item():.5f}  {extra}  {ips:.2f} it/s")
            if step % args.val_interval == 0 or step == total_steps:
                vloss = validate(model, val_loader, loss_fn, dev)
                log(f"  [val] step {step}  val_loss={vloss:.5f}  (best {best_val:.5f})")
                if rank0() and vloss < best_val:
                    best_val = vloss
                    _save_b4(model, out / "checkpoint_best.pt", step, vloss, args)
                    log(f"  saved best (val_loss={vloss:.5f})")
            if rank0() and step % args.ckpt_interval == 0:
                _save_b4(model, out / f"checkpoint_step{step}.pt", step, None, args)
            if step >= total_steps:
                done = True; break

    if rank0():
        _save_b4(model, out / "checkpoint_last.pt", step, None, args)
        log(f"done. best_val={best_val:.5f}  out={out}")
    if is_dist():
        dist.barrier(); dist.destroy_process_group()


if __name__ == "__main__":
    main()
