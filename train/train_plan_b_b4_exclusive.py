#!/usr/bin/env python
"""plan-b-pvt · Phase-II EXCLUSIVE-route trainer (audit-fixed; IMPLEMENT + SMOKE only).

Teacher/student STRICTLY separate:
  * student   = ObsWorldB4Exclusive (the ONLY final inference model); warm-started from
                --student-init (Phase-I b4 OR a Phase-A/B exclusive checkpoint).
  * teacher   = a SEPARATE frozen PVTContextformerQ built from --teacher-b4 (ALWAYS the
                original frozen Phase-I B4). Never the (possibly-updated) student q. Its
                SHA is asserted unchanged across the run.

Losses (models/plan_b_b4_exclusive.ObsWorldB4Exclusive.loss):
  L_fore(pred,y) + λ_distill·(pred→teacher) + λ_resid·(residual→ stopgrad(teacher−prior)) + λ_vic
  + Stage-B: cmp/con on the exclusive composed path.

Stage A: student q FROZEN; train branch; alpha warm-up 0.1→1 then fixed.
Stage B: alpha FIXED 1 (no re-warmup); unfreeze ONLY --unfreeze-q-prefixes of student q at
         0.05–0.1× LR (teacher frozen). For contextformer6M the last stage + head are:
         --unfreeze-q-prefixes "core.blocks.2.,core.head."
FP32 only. Saves checkpoint_best (by val) AND checkpoint_last. Does NOT auto-run.
"""
from __future__ import annotations

import argparse
import hashlib
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

# xarray-free top-level so the pure helpers below are importable without a data/xarray stack.
from models.encoders.pvt_contextformer_q import PVTContextformerQ, contextformer6m_hparams  # noqa: E402
from models.plan_b_b4_exclusive import ObsWorldB4Exclusive, load_exclusive_from_b4  # noqa: E402


def rank0():
    return int(os.environ.get("LOCAL_RANK", 0)) == 0


def is_dist():
    return dist.is_available() and dist.is_initialized()


def log(m):
    if rank0():
        print(m, flush=True)


def _seed_everything(seed):
    """Explicit reproducible seeding: torch(+cuda)/numpy/python. Same seed across the 4
    tournament configs so only lr/a2-lambda differ."""
    import random
    import numpy as np
    random.seed(seed); np.random.seed(seed)
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)


def _seed_worker(worker_id):
    # torch already derives each worker's torch.initial_seed() as base_seed+worker_id, so it
    # is per-worker unique already. Adding +worker_id again double-counts (and collides across
    # ranks). Standard PyTorch recipe = torch.initial_seed() % 2**32.
    import random
    import numpy as np
    s = torch.initial_seed() % (2 ** 32)
    np.random.seed(s); random.seed(s)


def state_sha(sd) -> str:
    h = hashlib.sha256()
    for k in sorted(sd):
        h.update(k.encode()); h.update(sd[k].detach().cpu().numpy().tobytes())
    return h.hexdigest()


def build_teacher(hp, teacher_b4_sd, dev):
    """SEPARATE frozen full-weather teacher (own tensors; from the ORIGINAL Phase-I B4)."""
    teacher = PVTContextformerQ(hp)
    q_sd = {k[len("q."):]: v for k, v in teacher_b4_sd.items() if k.startswith("q.")}
    miss, unexp = teacher.load_state_dict(q_sd, strict=False)
    teacher.to(dev).eval()
    for p in teacher.parameters():
        p.requires_grad_(False)
    log(f"teacher(full-weather, FROZEN) from --teacher-b4: missing={len(list(miss))} unexpected={len(list(unexp))}")
    return teacher


def load_student_init(model, init_ck):
    """Warm-start student. Accepts Phase-I b4 (arch ObsWorldB4) OR an exclusive checkpoint."""
    sd = init_ck["b4_state_dict"]
    arch = (init_ck.get("contract_cfg", {}) or {}).get("arch") or init_ck.get("arch")
    if arch == "ObsWorldB4Exclusive":
        miss, unexp = model.load_state_dict(sd, strict=False)          # exclusive -> exclusive
        assert (init_ck.get("contract_cfg", {}) or {}).get("route_version", model.ROUTE_VERSION) == model.ROUTE_VERSION, \
            "route_version mismatch on exclusive resume"
        return list(miss), list(unexp), "exclusive"
    miss, unexp = load_exclusive_from_b4(model, sd)                    # Phase-I b4 -> exclusive (drops gate)
    return miss, unexp, "phase1_b4"


def unfreeze_q_by_prefix(model, prefixes):
    """Stage B: FIRST freeze ALL student q, THEN unfreeze ONLY names matching a prefix.
    Asserts: >0 matched, every unmatched q frozen, trainable set == matched set."""
    for p in model.q.parameters():
        p.requires_grad_(False)
    matched = set()
    for name, p in model.q.named_parameters():
        if any(name.startswith(pre) for pre in prefixes):
            p.requires_grad_(True); matched.add(name)
    assert matched, f"Stage B: no student-q param matched {prefixes}"
    unmatched_train = [n for n, p in model.q.named_parameters() if n not in matched and p.requires_grad]
    assert not unmatched_train, f"Stage B: unmatched q trainable: {unmatched_train[:5]}"
    trainable = {n for n, p in model.q.named_parameters() if p.requires_grad}
    assert trainable == matched, "Stage B: trainable set != matched set"
    model.freeze_b0 = False
    return sorted(matched)


def lr_factor(step, warmup, total):
    """LR warm-up (linear) then cosine decay to ~0. Applies to LR ONLY — never to alpha."""
    import math
    if warmup > 0 and step < warmup:
        return step / max(1, warmup)
    if total <= warmup:
        return 1.0
    prog = (step - warmup) / max(1, total - warmup)
    return 0.5 * (1.0 + math.cos(math.pi * min(1.0, prog)))


def sched_lambdas(base, step, total, a2_start_frac, a2_lambda, cmp_start_frac=0.0, cmp_ramp_frac=0.0):
    """Segmented A1/A2 loss schedule + Stage-B composition ramp (spec 五.2). A1 (first a2_start_frac):
    distill=resid=1. A2 (after): distill=resid=a2_lambda. fore stays 1. Composition terms
    (cmp/con/state_con/vic_future) are 0 before cmp_start_frac*total, then ramp LINEARLY to their base
    weight over cmp_ramp_frac*total. With base cmp/con/state_con/vic_future=0 (Stage A) this is a no-op."""
    lam = SimpleNamespace(**vars(base))
    if step >= int(a2_start_frac * total):
        lam.distill = base.distill * a2_lambda
        lam.resid = base.resid * a2_lambda
    start = int(cmp_start_frac * total); ramp = max(1, int(cmp_ramp_frac * total))
    frac = 0.0 if step < start else min(1.0, (step - start) / ramp)
    for k in ("cmp", "con", "state_con", "vic_future"):
        if hasattr(base, k):
            setattr(lam, k, getattr(base, k) * frac)
    return lam


@torch.no_grad()
def _log_conflict(model, terms):
    """First-N-steps diagnostic (no PCGrad/GradNorm yet): per-loss grad NORM and pairwise
    grad COSINE on T (transition) and O (o_delta). `terms` = {name: loss_tensor}. Recomputes
    grads per term with retain_graph; caller must NOT have called backward yet."""
    import itertools
    m = model.module if hasattr(model, "module") else model
    tparams = [p for p in m.transition.parameters() if p.requires_grad]
    oparams = [p for p in m.o_delta.parameters() if p.requires_grad]

    def flat(loss, params):
        g = torch.autograd.grad(loss, params, retain_graph=True, allow_unused=True)
        return torch.cat([(gi if gi is not None else torch.zeros_like(p)).reshape(-1) for gi, p in zip(g, params)])
    out = {}
    for tag, params in (("T", tparams), ("O", oparams)):
        if not params:
            continue
        gs = {k: flat(v, params) for k, v in terms.items()}
        for k, v in gs.items():
            out[f"gnorm_{tag}_{k}"] = float(v.norm())
        for a, b in itertools.combinations(gs, 2):
            na, nb = gs[a].norm(), gs[b].norm()
            out[f"gcos_{tag}_{a}x{b}"] = float((gs[a] @ gs[b]) / (na * nb + 1e-12))
    return out


@torch.no_grad()
def validate(model, loader, loss_fn, dev, max_batches=0):
    """max_batches=0 => FULL val (no biased prefix). >0 truncates (dev only)."""
    from train.train_plan_b_contextformer import to_device  # lazy (server-only)
    m = model.module if hasattr(model, "module") else model
    m.eval(); tot, n = 0.0, 0
    for i, batch in enumerate(loader):
        if max_batches > 0 and i >= max_batches:
            break
        data = to_device(batch, dev)
        preds = m(data)                                                # exclusive inference forecast
        loss, _ = loss_fn(preds, data)
        if torch.isfinite(loss):
            tot += loss.item(); n += 1
    m.train()
    if is_dist():
        t = torch.tensor([tot, n], device=dev, dtype=torch.float64); dist.all_reduce(t, op=dist.ReduceOp.SUM)
        return (t[0] / t[1]).item() if t[1] > 0 else float("inf")
    return tot / max(n, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-dir", required=True); ap.add_argument("--val-dir", required=True)
    ap.add_argument("--student-init", required=True, help="Phase-I b4 OR exclusive A/B checkpoint (warm-start student)")
    ap.add_argument("--teacher-b4", required=True, help="ALWAYS the original frozen Phase-I B4 (teacher source)")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--per-gpu-batch", type=int, default=8); ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--max-epochs", type=int, default=40); ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--lr", type=float, default=1e-5); ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--grad-clip", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=42, help="explicit reproducible seed (torch/cuda/numpy/random + DataLoader)")
    ap.add_argument("--log-interval", type=int, default=50); ap.add_argument("--val-interval", type=int, default=1000)
    ap.add_argument("--val-max-batches", type=int, default=0,
                    help="0 => FULL val (tournament selection). >0 truncates val (dev/debug only, biased).")
    ap.add_argument("--early-stop-patience", type=int, default=5,
                    help="stop after N consecutive full-val no-improvements (0 disables). Best+last always saved.")
    ap.add_argument("--early-stop-min-epochs", type=int, default=10,
                    help="never early-stop before this many completed epochs")
    ap.add_argument("--ckpt-interval", type=int, default=2000); ap.add_argument("--state-dim", type=int, default=256)
    ap.add_argument("--stage", choices=("A", "B"), default="A")
    ap.add_argument("--lr-warmup-steps", type=int, default=200, help="linear LR warm-up steps (alpha is NEVER scheduled)")
    ap.add_argument("--a2-start-frac", type=float, default=0.25, help="fraction of steps after which A2 loss weights apply")
    ap.add_argument("--a2-lambda", type=float, default=0.5, help="A2 multiplier on distill+resid (e.g. 0.5 or 0.25)")
    ap.add_argument("--grad-diag-steps", type=int, default=100, help="log per-loss grad norm+cosine on T/O for first N steps")
    ap.add_argument("--unfreeze-q-prefixes", default="")
    ap.add_argument("--backbone-lr-scale", type=float, default=0.05)
    ap.add_argument("--lambda-fore", type=float, default=1.0); ap.add_argument("--lambda-distill", type=float, default=1.0)
    ap.add_argument("--lambda-resid", type=float, default=1.0); ap.add_argument("--lambda-vic", type=float, default=0.05)
    ap.add_argument("--lambda-cmp", type=float, default=0.0); ap.add_argument("--lambda-con", type=float, default=0.0)
    ap.add_argument("--lambda-state-con", type=float, default=0.0, help="Stage-B latent (LayerNorm) consistency; 0=OFF")
    ap.add_argument("--lambda-vic-future", type=float, default=0.0, help="Stage-B anti-collapse on transitioned z_h; 0=OFF")
    ap.add_argument("--cmp-start-frac", type=float, default=0.5, help="Stage-B: fraction of steps before composition losses turn on")
    ap.add_argument("--cmp-ramp-frac", type=float, default=0.25, help="Stage-B: linear ramp fraction to full cmp/con/state_con/vic_future")
    args = ap.parse_args()

    # lazy (server-only) heavy imports so this module's helpers import without xarray
    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
    from models.losses.masked_l2_ndvi import MaskedL2NDVILoss
    from train.train_plan_b_contextformer import collate, to_device

    local_rank = int(os.environ.get("LOCAL_RANK", 0)); world = int(os.environ.get("WORLD_SIZE", 1))
    _seed_everything(args.seed + local_rank)                           # reproducible; +rank so DDP ranks differ
    if world > 1:
        dist.init_process_group("nccl", device_id=torch.device("cuda", local_rank)); torch.cuda.set_device(local_rank)
    dev = torch.device("cuda", local_rank) if torch.cuda.is_available() else torch.device("cpu")
    out = Path(args.output_dir)
    if rank0():
        out.mkdir(parents=True, exist_ok=True)

    hp = contextformer6m_hparams(pvt_pretrained=False)
    init_ck = torch.load(args.student_init, map_location="cpu", weights_only=False)
    teach_ck = torch.load(args.teacher_b4, map_location="cpu", weights_only=False)
    student_init_sha = state_sha(init_ck["b4_state_dict"])
    student = ObsWorldB4Exclusive(hp, contract_cfg={"state_dim": args.state_dim, "freeze_b0": True}).to(dev)
    miss, unexp, src = load_student_init(student, init_ck)
    log(f"student warm-start ({src}): missing={miss} unexpected={unexp}")

    teacher = build_teacher(hp, teach_ck["b4_state_dict"], dev)
    teacher_sha0 = state_sha(teacher.state_dict())
    log(f"teacher SHA(before) = {teacher_sha0[:16]}")

    if args.stage == "A":
        for p in student.q.parameters():
            p.requires_grad_(False)                                    # q frozen
        student.freeze_b0 = True
    else:
        prefixes = [s for s in args.unfreeze_q_prefixes.split(",") if s]
        assert prefixes, "Stage B requires --unfreeze-q-prefixes (e.g. 'core.blocks.2.,core.head.')"
        assert args.lambda_cmp > 0 or args.lambda_con > 0, \
            "Stage B must enable composition (--lambda-cmp/--lambda-con > 0) or Q4 gets NO training signal (spec 五/objective)."
        unf = unfreeze_q_by_prefix(student, prefixes)
        log(f"Stage B: unfroze {len(unf)} q tensors: {unf[:6]}{' ...' if len(unf) > 6 else ''}")
    student.alpha.fill_(1.0)                                           # alpha FIXED 1.0 in BOTH stages (never scheduled)

    lambdas = SimpleNamespace(fore=args.lambda_fore, distill=args.lambda_distill, resid=args.lambda_resid,
                              vic=args.lambda_vic, cmp=args.lambda_cmp, con=args.lambda_con,
                              state_con=args.lambda_state_con, vic_future=args.lambda_vic_future)
    log(f"student q trainable: {sum(1 for p in student.q.parameters() if p.requires_grad)}/"
        f"{sum(1 for _ in student.q.parameters())}  stage={args.stage}")
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
        groups.append({"params": q_params, "lr": args.lr * args.backbone_lr_scale, "name": "q_unfrozen"})
    opt = torch.optim.AdamW(groups if groups else list(m.parameters()), betas=(0.9, 0.999),
                            weight_decay=args.weight_decay)
    for g in opt.param_groups:
        log(f"  opt '{g['name']}': tensors={len(g['params'])} lr={g['lr']:.2e}")

    loss_fn = MaskedL2NDVILoss(lc_min=10, lc_max=40, context_length=m.context_len, target_length=m.target_len,
                               ndvi_pred_idx=0, ndvi_targ_idx=0, pred_mask_value=-1, scale_by_std=False)
    train_ds = GreenEarthNetContextformerDataset(args.train_dir, dl_cloudmask=True)
    val_ds = GreenEarthNetContextformerDataset(args.val_dir, dl_cloudmask=True)
    sampler = DistributedSampler(train_ds, shuffle=True, seed=args.seed) if world > 1 else None
    _gen = torch.Generator(); _gen.manual_seed(args.seed)
    loader = DataLoader(train_ds, batch_size=args.per_gpu_batch, sampler=sampler, shuffle=(sampler is None),
                        num_workers=args.num_workers, collate_fn=collate, pin_memory=True, drop_last=True,
                        generator=_gen, worker_init_fn=_seed_worker)
    val_loader = DataLoader(val_ds, batch_size=args.per_gpu_batch, shuffle=False,
                            num_workers=args.num_workers, collate_fn=collate, pin_memory=True)
    steps_per_epoch = max(len(loader), 1)
    total_steps = args.max_steps if args.max_steps > 0 else args.max_epochs * steps_per_epoch
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda=lambda s: lr_factor(s, args.lr_warmup_steps, total_steps))
    log(f"steps/epoch={steps_per_epoch} total_steps={total_steps} lr_warmup={args.lr_warmup_steps} "
        f"a2_start={int(args.a2_start_frac*total_steps)} a2_lambda={args.a2_lambda} alpha=FIXED 1.0")

    def save(path, step, vloss):
        torch.save({"b4_state_dict": m.state_dict(), "contract_cfg": m.config(), "arch": m.ARCH,
                    "route_version": m.ROUTE_VERSION, "step": step, "stage": args.stage,
                    "val_loss": vloss, "alpha": float(m.alpha), "seed": args.seed, "teacher_sha256": teacher_sha0,
                    "student_init_sha256": student_init_sha, "args": vars(args)}, path)

    cl, tl = m.context_len, m.target_len
    best_val, no_improve, step, t0, done = float("inf"), 0, 0, time.time(), False
    t_prev, step_prev = t0, 0                                          # windowed it/s (excludes startup+val)
    for epoch in range(10_000):
        if done:
            break
        if sampler is not None:
            sampler.set_epoch(epoch)
        for batch in loader:
            data = to_device(batch, dev)
            lam_step = sched_lambdas(lambdas, step, total_steps, args.a2_start_frac, args.a2_lambda,
                                     cmp_start_frac=args.cmp_start_frac, cmp_ramp_frac=args.cmp_ramp_frac)
            with torch.no_grad():
                t_pred = teacher.encode(data, pred_start=cl, preds_length=tl)[0].detach()
            opt.zero_grad(set_to_none=True)
            _, aux = student(data, t_pred, lam_step)                   # DUAL-signature forward (DDP-safe)
            loss = aux["total"]
            finite = bool(torch.isfinite(loss))
            if is_dist():                                              # symmetric skip: if ANY rank non-finite, ALL skip
                fflag = torch.tensor([1.0 if finite else 0.0], device=dev)
                dist.all_reduce(fflag, op=dist.ReduceOp.MIN)
                finite = fflag.item() > 0.5
            if not finite:
                log(f"WARN non-finite loss @ {step} (some rank); skip on ALL ranks"); step += 1; sched.step(); continue
            if step < args.grad_diag_steps and not is_dist() and len(aux.get("terms", {})) >= 2:
                conf = _log_conflict(m, aux["terms"])                  # grad norm + pairwise cosine on T/O (diagnose only)
                log("  [gconf] " + " ".join(f"{k}={v:+.3e}" for k, v in conf.items()))
            loss.backward()
            if args.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(m.parameters(), args.grad_clip)
            opt.step(); sched.step(); step += 1

            if step % args.log_interval == 0:
                now = time.time(); ips = (step - step_prev) / max(now - t_prev, 1e-6); t_prev, step_prev = now, step
                lg = {k: float(v) for k, v in aux["logs"].items() if k != "alpha"}
                log(f"step {step}/{total_steps} {ips:.2f}it/s loss={loss.item():.5f} lr={sched.get_last_lr()[0]:.2e} "
                    f"a2={'Y' if step>=int(args.a2_start_frac*total_steps) else 'N'} "
                    + " ".join(f"{k}={lg[k]:.4f}" for k in ("fore", "distill", "resid", "vic_var", "cmp", "con") if k in lg))
            if step % args.val_interval == 0 or step == total_steps:
                vloss = validate(student, val_loader, loss_fn, dev, max_batches=args.val_max_batches)
                improved = vloss < best_val
                log(f"  [val] step {step} epoch={epoch} val_loss={vloss:.5f} (best {best_val:.5f}) "
                    f"no_improve={no_improve}{'' if args.val_max_batches == 0 else ' (TRUNCATED val — not selection-grade)'}")
                if improved:
                    best_val = vloss; no_improve = 0
                    if rank0():
                        save(out / "checkpoint_best.pt", step, vloss); log(f"  saved best {vloss:.5f}")
                else:
                    no_improve += 1
                # early stop: only after >= min epochs, then `patience` consecutive full-val no-improvements.
                # best_val/no_improve are updated identically on every rank (validate() all-reduces vloss),
                # so all ranks decide `done` together — no DDP desync.
                if (args.early_stop_patience > 0 and epoch >= args.early_stop_min_epochs
                        and no_improve >= args.early_stop_patience):
                    log(f"  [early-stop] epoch={epoch}>={args.early_stop_min_epochs} & {no_improve} consecutive "
                        f"vals w/o improve >= patience {args.early_stop_patience} — stopping (best+last saved)")
                    done = True; break
            if rank0() and step % args.ckpt_interval == 0:
                save(out / f"checkpoint_step{step}.pt", step, None)
            if step >= total_steps:
                done = True; break

    assert state_sha(teacher.state_dict()) == teacher_sha0, "teacher weights changed during training!"
    if rank0():
        save(out / "checkpoint_last.pt", step, None)
        log(f"done stage={args.stage} step={step} best_val={best_val:.5f} teacher_sha_unchanged=True out={out}")
    if is_dist():
        dist.barrier(); dist.destroy_process_group()


if __name__ == "__main__":
    main()
