#!/usr/bin/env python
"""plan-b-pvt · Phase-II EXCLUSIVE-route trainer (audit-approved; IMPLEMENT + SMOKE only).

Teacher/student are STRICTLY separate:
  * student  = ObsWorldB4Exclusive (the ONLY thing that becomes the final inference model).
  * teacher  = a SEPARATE frozen PVTContextformerQ copy (full-weather B0), requires_grad=False,
               eval, no_grad. It never enters the student's state_dict / param count, and its
               weights stay bit-identical even after Stage B unfreezes the student's q.

Losses (models/plan_b_b4_exclusive.ObsWorldB4Exclusive.loss):
  L_fore(pred,y) + λ_distill·(pred→teacher) + λ_resid·(residual→ stopgrad(teacher−prior)) + λ_vic
  + Stage-B: cmp/con on the exclusive composed path.

Stage A: student q FROZEN; train projector/weather/geo/fuse/T/O; alpha warm-up 0.1→1 then fixed;
         NO cmp/con. Goal: recover Table-1 accuracy + get Q2 to turn positive (confirmed by eval,
         NOT assumed).
Stage B (only after A passes Q1+Q2): unfreeze student q last-stage/head @ 0.05–0.1× LR; teacher
         stays frozen; ramp cmp/con.

This file does NOT auto-run; launch is deliberate. No mixed precision (FP32).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from types import SimpleNamespace
from pathlib import Path

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset  # noqa: E402
from models.encoders.pvt_contextformer_q import PVTContextformerQ, contextformer6m_hparams  # noqa: E402
from models.plan_b_b4_exclusive import ObsWorldB4Exclusive, load_exclusive_from_b4  # noqa: E402
from train.train_plan_b_contextformer import collate, to_device, log, is_dist, rank0  # noqa: E402


def build_teacher(hp, b4_state_dict, dev):
    """SEPARATE frozen full-weather teacher (its own tensors; not shared with the student q)."""
    teacher = PVTContextformerQ(hp)
    q_sd = {k[len("q."):]: v for k, v in b4_state_dict.items() if k.startswith("q.")}
    miss, unexp = teacher.load_state_dict(q_sd, strict=False)
    teacher.to(dev).eval()
    for p in teacher.parameters():
        p.requires_grad_(False)
    log(f"teacher(full-weather, FROZEN): loaded q  missing={len(list(miss))} unexpected={len(list(unexp))}")
    return teacher


@torch.no_grad()
def teacher_forecast(teacher, data, cl, tl):
    return teacher.encode(data, pred_start=cl, preds_length=tl)[0].detach()


def unfreeze_q_by_prefix(model, prefixes):
    """Stage B: unfreeze ONLY student-q params whose name starts with one of `prefixes`
    (e.g. the last PVT stage + forecast head). Returns the count unfrozen."""
    n = 0
    for name, p in model.q.named_parameters():
        if any(name.startswith(pre) for pre in prefixes):
            p.requires_grad_(True); n += 1
    model.freeze_b0 = False
    return n


def alpha_at(step, warmup, lo=0.1, hi=1.0):
    if warmup <= 0 or step >= warmup:
        return hi
    return lo + (hi - lo) * (step / warmup)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-dir", required=True); ap.add_argument("--val-dir", required=True)
    ap.add_argument("--warmstart-b4", required=True, help="Phase-I b4 checkpoint to warm-start student + build teacher")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--per-gpu-batch", type=int, default=8); ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--max-epochs", type=int, default=40); ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--lr", type=float, default=1e-5); ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--grad-clip", type=float, default=1.0)
    ap.add_argument("--log-interval", type=int, default=50); ap.add_argument("--val-interval", type=int, default=1000)
    ap.add_argument("--ckpt-interval", type=int, default=2000); ap.add_argument("--state-dim", type=int, default=256)
    ap.add_argument("--stage", choices=("A", "B"), default="A")
    ap.add_argument("--alpha-warmup", type=int, default=500, help="steps to ramp alpha 0.1->1 (then fixed 1)")
    ap.add_argument("--unfreeze-q-prefixes", default="", help="Stage B: comma list of q param-name prefixes to unfreeze")
    ap.add_argument("--backbone-lr-scale", type=float, default=0.05)
    ap.add_argument("--lambda-fore", type=float, default=1.0); ap.add_argument("--lambda-distill", type=float, default=1.0)
    ap.add_argument("--lambda-resid", type=float, default=1.0); ap.add_argument("--lambda-vic", type=float, default=0.05)
    ap.add_argument("--lambda-cmp", type=float, default=0.0); ap.add_argument("--lambda-con", type=float, default=0.0)
    args = ap.parse_args()

    local_rank = int(os.environ.get("LOCAL_RANK", 0)); world = int(os.environ.get("WORLD_SIZE", 1))
    if world > 1:
        dist.init_process_group("nccl", device_id=torch.device("cuda", local_rank)); torch.cuda.set_device(local_rank)
    dev = torch.device("cuda", local_rank) if torch.cuda.is_available() else torch.device("cpu")
    out = Path(args.output_dir)
    if rank0():
        out.mkdir(parents=True, exist_ok=True)

    hp = contextformer6m_hparams(pvt_pretrained=False)
    ck = torch.load(args.warmstart_b4, map_location="cpu", weights_only=False)
    b4_sd = ck["b4_state_dict"]
    stage_a = (args.stage == "A")
    cfg = {"state_dim": args.state_dim, "freeze_b0": stage_a}          # Stage A: q frozen
    student = ObsWorldB4Exclusive(hp, contract_cfg=cfg).to(dev)
    miss, unexp = load_exclusive_from_b4(student, b4_sd)
    log(f"student EXCLUSIVE warm-start: missing={miss} unexpected={unexp}  (expect missing⊆[alpha], unexpected=[gate])")
    teacher = build_teacher(hp, b4_sd, dev)                            # SEPARATE frozen copy

    if not stage_a:
        prefixes = [s for s in args.unfreeze_q_prefixes.split(",") if s]
        assert prefixes, "Stage B requires --unfreeze-q-prefixes (e.g. last stage + head); refuse full unfreeze"
        n = unfreeze_q_by_prefix(student, prefixes)
        log(f"Stage B: unfroze {n} student-q tensors matching {prefixes}")

    lambdas = SimpleNamespace(fore=args.lambda_fore, distill=args.lambda_distill, resid=args.lambda_resid,
                              vic=args.lambda_vic, cmp=args.lambda_cmp, con=args.lambda_con)
    n_q_train = sum(1 for p in student.q.parameters() if p.requires_grad)
    log(f"student q trainable: {n_q_train}/{sum(1 for _ in student.q.parameters())}  stage={args.stage}")
    student.train()
    if world > 1:
        student = DDP(student, device_ids=[local_rank], find_unused_parameters=True)

    m = student.module if hasattr(student, "module") else student
    q_params = [p for p in m.q.parameters() if p.requires_grad]
    branch_params = [p for n, p in m.named_parameters() if not n.startswith("q.") and p.requires_grad]
    groups = []
    if branch_params:
        groups.append({"params": branch_params, "lr": args.lr, "name": "branch"})
    if q_params:
        groups.append({"params": q_params, "lr": args.lr * args.backbone_lr_scale, "name": "q_last_stage_head"})
    opt = torch.optim.AdamW(groups if groups else list(m.parameters()), betas=(0.9, 0.999),
                            weight_decay=args.weight_decay)
    for g in opt.param_groups:
        log(f"  opt '{g['name']}': tensors={len(g['params'])} lr={g['lr']:.2e}")

    train_ds = GreenEarthNetContextformerDataset(args.train_dir, dl_cloudmask=True)
    val_ds = GreenEarthNetContextformerDataset(args.val_dir, dl_cloudmask=True)
    sampler = DistributedSampler(train_ds, shuffle=True) if world > 1 else None
    loader = DataLoader(train_ds, batch_size=args.per_gpu_batch, sampler=sampler, shuffle=(sampler is None),
                        num_workers=args.num_workers, collate_fn=collate, pin_memory=True, drop_last=True)
    steps_per_epoch = max(len(loader), 1)
    total_steps = args.max_steps if args.max_steps > 0 else args.max_epochs * steps_per_epoch
    log(f"steps/epoch={steps_per_epoch} total_steps={total_steps} alpha_warmup={args.alpha_warmup}")

    cl, tl = m.context_len, m.target_len
    step, t0, done = 0, time.time(), False
    for epoch in range(10_000):
        if done:
            break
        if sampler is not None:
            sampler.set_epoch(epoch)
        for batch in loader:
            data = to_device(batch, dev)
            m.alpha.fill_(alpha_at(step, args.alpha_warmup))          # non-learnable schedule
            with torch.no_grad():
                t_pred = teacher_forecast(teacher, data, cl, tl)      # SEPARATE frozen teacher
            opt.zero_grad(set_to_none=True)
            pred, aux = student(data, t_pred, lambdas) if hasattr(student, "module") else m.loss(data, t_pred, lambdas)
            loss = aux["total"]
            if not torch.isfinite(loss):
                log(f"WARN non-finite loss @ {step}; skip"); step += 1; continue
            loss.backward()
            if args.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(m.parameters(), args.grad_clip)
            opt.step(); step += 1
            if step % args.log_interval == 0:
                lg = {k: float(v) for k, v in aux["logs"].items() if k != "alpha"}
                log(f"step {step}/{total_steps} loss={loss.item():.5f} alpha={float(m.alpha):.3f} "
                    + " ".join(f"{k}={v:.4f}" for k in ("fore", "distill", "resid", "vic_var", "cmp", "con") if k in lg))
            if rank0() and step % args.ckpt_interval == 0:
                torch.save({"b4_state_dict": m.state_dict(), "contract_cfg": m.config(), "arch": m.ARCH,
                            "step": step, "stage": args.stage, "args": vars(args)}, out / f"checkpoint_step{step}.pt")
            if step >= total_steps:
                done = True; break
    if rank0():
        torch.save({"b4_state_dict": m.state_dict(), "contract_cfg": m.config(), "arch": m.ARCH,
                    "step": step, "stage": args.stage, "args": vars(args)}, out / "checkpoint_last.pt")
        log(f"done stage={args.stage} step={step} out={out}")
    if is_dist():
        dist.barrier(); dist.destroy_process_group()


if __name__ == "__main__":
    main()
