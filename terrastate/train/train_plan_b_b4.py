#!/usr/bin/env python
"""plan-b-pvt · B4 = TerraState training (horizon-conditioned load-bearing residual).

ŷ = ŷ_B0 + gate·O_δ(T(z_t, weather, geo, h))  on a FROZEN B0 (stage 1). All losses are
masked NDVI on B0's protocol (clear × vegetation), computed inside the model:
  --lambda-fore   masked DIRECT-endpoint forecast (all 20 horizons)
  --lambda-resid  UNGATED residual r*=y−sg(ŷ_B0) supervision (anti-starvation)
  --lambda-cmp    direct+composed endpoint over TRAIN partitions  (Phase I default 0)
  --lambda-con    direct/composed consistency                     (Phase I default 0)
  --lambda-vic    VICReg anti-collapse on z_t                     (default 0.05; 1.0 dominates)

Strong-baseline-recoverable: gate zero-init -> ŷ==B0 at init. --freeze-b0 1 (stage 1)
trains only the TerraState branch; 0 (stage 2) joint fine-tunes B0 at a lower LR.
Phased schedule (doc84): Phase I fore/resid only; Phase II ramp cmp/con after accuracy
stabilises. --resume-b4 loads a FULL b4_state_dict (not just B0 core).

Launch: scripts/train_plan_b_b4.sh   (local CPU synthetic smoke: scripts/smoke_b4_train.py)
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
# reuse the B0 trainer's data plumbing verbatim (single source of truth)
from train.train_plan_b_contextformer import (  # noqa: E402
    collate, to_device, log, is_dist, rank0,
)


@torch.no_grad()
def validate(model, loader, loss_fn, dev, max_batches=50):
    """Val loss = masked NDVI on the LOAD-BEARING direct forecast ŷ = B0 + gate·residual."""
    model.eval()
    tot, n = 0.0, 0
    for i, batch in enumerate(loader):
        if i >= max_batches:
            break
        data = to_device(batch, dev)
        preds = model(data)                    # ŷ_direct (no lambdas)
        loss, _ = loss_fn(preds, data)
        if torch.isfinite(loss):
            tot += loss.item(); n += 1
    model.train()
    if is_dist():
        # reduce the raw SUM and COUNT, then divide (reducing per-rank averages is wrong)
        t = torch.tensor([tot, n], device=dev, dtype=torch.float64)
        dist.all_reduce(t, op=dist.ReduceOp.SUM)
        return (t[0] / t[1]).item() if t[1] > 0 else float("inf")
    return tot / max(n, 1)


def _save_b4(model, path, step, val, args):
    """Save the FULL ObsWorldB4 (b4_state_dict) + complete contract_cfg (dims, mask bounds,
    train+held-out partitions) so export/resume rebuild the identical model."""
    m = model.module if hasattr(model, "module") else model
    torch.save(
        {
            "b4_state_dict": m.state_dict(),
            "contract_cfg": m.config(),
            "step": step, "val_loss": val, "arch": "ObsWorldB4",
            "lambdas": {"fore": args.lambda_fore, "resid": args.lambda_resid,
                        "cmp": args.lambda_cmp, "con": args.lambda_con, "vic": args.lambda_vic},
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
    ap.add_argument("--freeze-b0", type=int, default=1, help="1=freeze B0 (stage 1); 0=joint fine-tune (stage 2)")
    ap.add_argument("--lambda-fore", type=float, default=1.0, help="masked DIRECT-endpoint forecast (B0 protocol)")
    ap.add_argument("--lambda-resid", type=float, default=1.0, help="UNGATED residual r* supervision (anti-starvation)")
    ap.add_argument("--lambda-cmp", type=float, default=0.0,
                    help="direct+composed masked endpoint (Phase I=0; ramp to ~0.1 in Phase II)")
    ap.add_argument("--lambda-con", type=float, default=0.0, help="direct/composed consistency (ramp in Phase II)")
    ap.add_argument("--lambda-vic", type=float, default=0.05,
                    help="VICReg anti-collapse weight (0.05 keeps 25·var+cov ~O(1); "
                         "audit: 1.0 dominates the prediction losses ~3.8x)")
    ap.add_argument("--resume-b4", default="", help="resume a FULL b4_state_dict ckpt (NOT just B0 core)")
    ap.add_argument("--backbone-lr-scale", type=float, default=0.1,
                    help="q/backbone LR = lr*scale for stage-2 joint fine-tune (--freeze-b0 0)")
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
    contract_cfg = {"state_dim": args.state_dim, "freeze_b0": bool(args.freeze_b0)}
    resume_ck = None
    if args.resume_b4:
        resume_ck = torch.load(args.resume_b4, map_location="cpu", weights_only=False)
        # keep the checkpoint's STRUCTURAL fields (dims/mask/partitions), but let the CLI
        # OVERRIDE runtime freeze_b0 — otherwise a freeze_b0=true Phase-I ckpt would silently
        # re-freeze q even when Phase II passes --freeze-b0 0.
        contract_cfg = dict(resume_ck.get("contract_cfg", contract_cfg))
        contract_cfg["freeze_b0"] = bool(args.freeze_b0)
    model = ObsWorldB4(hp, contract_cfg=contract_cfg).to(dev)
    lambdas = SimpleNamespace(fore=args.lambda_fore, resid=args.lambda_resid,
                              cmp=args.lambda_cmp, con=args.lambda_con, vic=args.lambda_vic)
    log(f"B4 TerraState  state_dim={args.state_dim}  freeze_b0={bool(args.freeze_b0)}  lambdas={vars(lambdas)}")
    if resume_ck is not None:
        miss, unexp = model.load_state_dict(resume_ck["b4_state_dict"], strict=True)
        log(f"RESUME full b4 {args.resume_b4}: missing={len(list(miss))} unexpected={len(list(unexp))} "
            f"step={resume_ck.get('step')} (optimizer/scheduler NOT restored)")
    elif args.init_ckpt:
        miss, unexp = load_official_ckpt(model.q.core, args.init_ckpt, strict=True)
        log(f"warm-start q.core {args.init_ckpt}: missing={len(miss)} unexpected={len(unexp)}")
    # runtime freeze must match the CLI, NOT the checkpoint (resume must not silently re-freeze q)
    n_q_train = sum(1 for p in model.q.parameters() if p.requires_grad)
    log(f"q requires_grad: {n_q_train}/{sum(1 for _ in model.q.parameters())}  (freeze_b0={bool(args.freeze_b0)})")
    assert (n_q_train == 0) == bool(args.freeze_b0), \
        f"freeze_b0={bool(args.freeze_b0)} but q trainable count={n_q_train}"
    model.train()
    if world > 1:
        # B0 frozen (stage 1) -> its params get no grad; branch params all do. find_unused for safety.
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

    # optimizer by MODULE IDENTITY (not a temp attr): branch @ lr, q/backbone @ lr*scale.
    m = model.module if hasattr(model, "module") else model
    q_params = [p for p in m.q.parameters() if p.requires_grad]
    branch_params = [p for n, p in m.named_parameters() if not n.startswith("q.") and p.requires_grad]
    groups = []
    if branch_params:
        groups.append({"params": branch_params, "lr": args.lr, "name": "branch(T/O/head/proj/enc)"})
    if q_params:
        groups.append({"params": q_params, "lr": args.lr * args.backbone_lr_scale, "name": "q_backbone"})
    opt = torch.optim.AdamW(groups if groups else list(m.parameters()),
                            betas=(0.9, 0.999), weight_decay=args.weight_decay)
    n_req = sum(1 for p in m.parameters() if p.requires_grad)
    log(f"trainable tensors={n_req}/{sum(1 for _ in m.parameters())}  "
        f"trainable params={sum(p.numel() for p in m.parameters() if p.requires_grad)/1e6:.3f}M")
    for g in opt.param_groups:
        log(f"  opt group '{g.get('name','?')}': tensors={len(g['params'])} "
            f"params={sum(p.numel() for p in g['params'])/1e6:.3f}M lr={g['lr']:.2e}")
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
            preds, aux = model(data, lambdas=lambdas)          # masked losses (fore/resid/cmp/con/vic) inside aux
            loss = aux["total"]
            logs = {k: float(v) for k, v in aux["logs"].items()}
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
                m = model.module if hasattr(model, "module") else model
                gnorm = lambda mod: sum(p.grad.norm().item() ** 2 for p in mod.parameters()
                                        if p.grad is not None) ** 0.5
                extra = " ".join(f"{k}={logs[k]:.4f}" for k in ("fore", "resid", "cmp_ep", "con", "vic_var", "gate") if k in logs)
                log(f"step {step}/{total_steps}  loss={loss.item():.5f}  {extra}  {ips:.2f} it/s "
                    f"| grad we={gnorm(m.weather_enc):.2e} T={gnorm(m.transition):.2e} Oδ={gnorm(m.o_delta):.2e}")
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
