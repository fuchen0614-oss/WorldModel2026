#!/usr/bin/env python
"""TerraState-V2 UNIQUE training line (doc 88 §4 / §E). IMPLEMENT + SMOKE only — this
script does NOT auto-start a full run.

Single run, THREE stages, ONE loss  L = 1.0*L_GT + 0.5*L_KD + lambda_s*L_future_state:

  Stage 1  [0%,20%)  : q FROZEN; train projector/weather_enc/geo_enc/fuse/T(transition)/O(o_delta);
                       lambda_s warms 0 -> 0.02.
  Stage 2  [20%,80%) : q FROZEN; three loss terms fixed (lambda_s = 0.02); interval ckpts;
                       FORCED 80% boundary checkpoint.
  Stage 3  [80%,100%]: unfreeze ONLY the last q transformer block (default 'core.blocks.2.');
                       q LR = q_lr_scale (0.02-0.05) x branch LR; lambda_s -> 0.01; GT/KD unchanged.

alpha is a fixed non-learnable buffer == 1.0 (inherited; NEVER scheduled). FP32. AdamW.
warmup(linear)+cosine on OPTIMIZER steps. grad clip 1.0. gradient accumulation keeps a
constant --global-batch (default 64) across any (per_gpu x world) factorisation, so single-
card and 8-card DDP share the same effective updates and LR schedule. The KD teacher is a
SEPARATE frozen full-weather B4 (never `self`); its SHA is asserted unchanged. The frozen
future-state target comes from a PRE-BUILT cache (built by scripts/build_future_state_cache.py)
and is passed IN as a tensor — inference never reads it.

Checkpoints save+restore EXACTLY: model / optimizer / scheduler / scaler(disabled record) /
epoch / step / micro-position / RNG(all ranks) / stage / q freeze-set / cache+config+manifest
SHAs / teacher+student-init SHAs.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from contextlib import nullcontext
from pathlib import Path

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import PVTContextformerQ, contextformer6m_hparams  # noqa: E402
from models.terrastate_v2 import TerraStateV2, warm_start_terrastate_v2  # noqa: E402
from train.terrastate_future_state_cache import FutureStateCache  # noqa: E402
from train.terrastate_v2_common import (  # noqa: E402
    FULL24_FIELD_ORDER, atomic_torch_save, canonical_json_sha256, capture_rng_state,
    collate_with_ids, log, module_pair_sha256, restore_rng_state, seed_everything,
    seed_worker, state_sha, to_device_with_ids,
)

# doc-88 default schedule fractions / lambda_s values (frozen; not CLI-tunable).
STAGE1_FRAC, STAGE3_FRAC = 0.20, 0.80
LAM_WARM_TARGET, LAM_MID, LAM_LATE = 0.02, 0.02, 0.01


# ------------------------------------------------------------------ schedules
def lr_factor(step: int, warmup: int, total: int) -> float:
    if warmup > 0 and step < warmup:
        return step / max(1, warmup)
    if total <= warmup:
        return 1.0
    prog = (step - warmup) / max(1, total - warmup)
    return 0.5 * (1.0 + math.cos(math.pi * min(1.0, prog)))


def lambda_state_at(step: int, total: int) -> float:
    frac = step / max(1, total)
    if frac < STAGE1_FRAC:
        return LAM_WARM_TARGET * (frac / STAGE1_FRAC)   # linear 0 -> 0.02
    if frac < STAGE3_FRAC:
        return LAM_MID                                  # 0.02
    return LAM_LATE                                      # 0.01


def lambda_state_values(step: int, total: int, future_state_scale: float) -> tuple[float, float]:
    """Return (scheduled/raw lambda_s, effective lambda_s).

    ``future_state_scale`` is an explicit ablation multiplier.  Its CLI default is 1.0,
    so the production schedule and loss are bit-for-bit unchanged unless the ablation is
    deliberately requested.
    """
    raw = lambda_state_at(step, total)
    return raw, raw * future_state_scale


def stage_at(step: int, total: int) -> int:
    frac = step / max(1, total)
    if frac < STAGE1_FRAC:
        return 1
    if frac < STAGE3_FRAC:
        return 2
    return 3


# ------------------------------------------------------------------ freeze/unfreeze
def apply_stage(raw, stage: int, unfreeze_prefixes):
    """Set q freeze state for a stage. Stage 1/2: q fully FROZEN. Stage 3: unfreeze ONLY
    params whose name matches `unfreeze_prefixes` (default the last transformer block).
    Returns the sorted list of trainable q param names."""
    for p in raw.q.parameters():
        p.requires_grad_(False)
    trainable = []
    if stage >= 3:
        matched = []
        for name, p in raw.q.named_parameters():
            if any(name.startswith(pre) for pre in unfreeze_prefixes):
                p.requires_grad_(True)
                matched.append(name)
        assert matched, f"stage 3: no q param matched {unfreeze_prefixes}"
        unmatched_train = [n for n, p in raw.q.named_parameters() if n not in matched and p.requires_grad]
        assert not unmatched_train, f"stage 3: unmatched q trainable: {unmatched_train[:5]}"
        raw.freeze_b0 = False        # let grad flow through q on the context-only prior pass
        trainable = sorted(matched)
    else:
        raw.freeze_b0 = True
    return trainable


def build_optimizer(raw, branch_lr: float, q_lr_scale: float, weight_decay: float):
    """AdamW, param groups by module identity. q group holds ALL q params (frozen ones are
    simply never stepped until unfrozen at stage 3), at q_lr = branch_lr * q_lr_scale, so the
    q/branch LR RATIO is preserved by the shared cosine factor across the whole run."""
    branch_params = [p for n, p in raw.named_parameters() if not n.startswith("q.")]
    q_params = [p for n, p in raw.named_parameters() if n.startswith("q.")]
    groups = [{"params": branch_params, "lr": branch_lr, "name": "branch"}]
    if q_params:
        groups.append({"params": q_params, "lr": branch_lr * q_lr_scale, "name": "q"})
    return torch.optim.AdamW(groups, betas=(0.9, 0.999), weight_decay=weight_decay)


def build_teacher(hp, teacher_b4_sd, dev, *, require_exact=True):
    """FAIL-CLOSED teacher build. The KD teacher is the ORIGINAL strong Phase-I B4: we load
    its `q.*` (context+full-weather backbone) into a frozen PVTContextformerQ and REQUIRE an
    exact load (missing==[] and unexpected==[]) — no print-and-continue."""
    teacher = PVTContextformerQ(hp)
    q_sd = {k[len("q."):]: v for k, v in teacher_b4_sd.items() if k.startswith("q.")}
    if not q_sd:
        raise RuntimeError("teacher-b4 checkpoint has no 'q.*' keys (expected a Phase-I B4 b4_state_dict).")
    miss, unexp = teacher.load_state_dict(q_sd, strict=False)
    miss, unexp = list(miss), list(unexp)
    if require_exact and (miss or unexp):
        raise RuntimeError(f"FAIL-CLOSED teacher q.* load rejected: missing={miss[:8]} "
                           f"unexpected={unexp[:8]} (require missing==[] and unexpected==[]).")
    teacher.to(dev).eval()
    for p in teacher.parameters():
        p.requires_grad_(False)
    log("teacher(full-weather Phase-I B4, FROZEN): q.* loaded EXACT (missing=0 unexpected=0)")
    return teacher


def is_dist():
    return dist.is_available() and dist.is_initialized()


def rank0():
    return int(os.environ.get("LOCAL_RANK", 0)) == 0


@torch.no_grad()
def validate_v2(model, loader, cache, dev):
    """Non-intervention val (doc 88 §6.3): global L_future_state (selection metric) + L_GT.

    Under DDP the val set is SPLIT across ranks by DistributedSampler(shuffle=False,
    drop_last=False) (built in run_training) so each rank scores only its shard. We
    accumulate UNREDUCED masked sums+counts (NOT per-batch means) and all_reduce them, so
    the result is the exact GLOBAL masked mean — identical to a single card and independent
    of world size / batching (no 8x redundant full-val passes)."""
    raw = model.module if hasattr(model, "module") else model
    cl, tl = raw.context_len, raw.target_len
    raw.eval()
    fs_num = fs_den = gt_num = gt_den = 0.0
    for batch in loader:
        data = to_device_with_ids(batch, dev)
        parts = raw.forecast_parts(data)
        pred = parts["pred"]
        z_star, pmask = cache.gather(batch["filepath"], dev)
        # future-state: sum of (1-cos) over VALID patches + valid-patch count
        zf = torch.nn.functional.layer_norm(parts["z_future"], (parts["z_future"].shape[-1],))
        zs = torch.nn.functional.layer_norm(z_star, (z_star.shape[-1],))
        per = 1.0 - torch.nn.functional.cosine_similarity(zf, zs, dim=-1)
        m = pmask.to(per.dtype)
        fs_num += float((per * m).sum()); fs_den += float(m.sum())
        # GT: masked NDVI squared-error sum + valid-pixel count (same selection as the loss)
        lc = data["landcover"]
        lc_mask = ((lc >= raw.lc_min) & (lc <= raw.lc_max)).type_as(pred)
        cloud = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).type_as(pred)
        valid = cloud * lc_mask.unsqueeze(1)
        targ = data["dynamic"][0][:, cl:cl + tl, 0:1]
        gt_num += float((((pred - targ) ** 2) * valid).sum()); gt_den += float(valid.sum())
    raw.train()
    if is_dist():
        t = torch.tensor([fs_num, fs_den, gt_num, gt_den], device=dev, dtype=torch.float64)
        dist.all_reduce(t, op=dist.ReduceOp.SUM)
        fs_num, fs_den, gt_num, gt_den = t.tolist()
    return (fs_num / max(fs_den, 1e-8)), (gt_num / max(gt_den, 1e-8))


# ------------------------------------------------------------------ checkpoint schema
def make_checkpoint(raw, opt, sched, *, epoch, step, micro_in_epoch, stage, trainable_q,
                    unfreeze_prefixes, best_val, total_steps, accum, world, global_batch,
                    shas, args, lambda_state_raw, lambda_state_effective, gathered_rng):
    return {
        "arch": raw.ARCH, "route_version": raw.ROUTE_VERSION,
        "b4_state_dict": raw.state_dict(), "contract_cfg": raw.config(),
        "optimizer_state_dict": opt.state_dict(),
        "scheduler_state_dict": sched.state_dict(),
        "scaler": {"enabled": False, "state": None, "note": "FP32 training; GradScaler disabled"},
        "epoch": epoch, "step": step, "micro_in_epoch": micro_in_epoch,
        "stage": stage, "q_freeze": {"trainable_q": trainable_q, "unfreeze_prefixes": unfreeze_prefixes},
        "rng_state": capture_rng_state(),
        "rng_states_by_rank": gathered_rng,
        "best_val": best_val,
        # Keep the legacy key as the weight actually applied to the loss.  The explicit
        # raw/effective pair makes an ablation checkpoint unambiguous.
        "lambda_state": lambda_state_effective,
        "lambda_state_raw": lambda_state_raw,
        "effective_lambda_state": lambda_state_effective,
        "future_state_scale": float(args.future_state_scale),
        "total_steps": total_steps, "accum": accum, "world_size": world, "global_batch": global_batch,
        "alpha": float(raw.alpha), "sha": shas, "args": vars(args),
        "loss_weights": {"gt": raw.W_GT, "kd": raw.W_KD,
                         "future_state_scale": float(args.future_state_scale)},
        "selection_note": ("This checkpoint is NOT automatically final. Final selection (doc 88 "
                           "§6.3): satisfy validation Q1 first, then pick the min non-intervention "
                           "future-state val loss among candidates {stage2_end_boundary80, "
                           "future_state_val_best, last}."),
    }


def _gather_rng():
    st = capture_rng_state()
    if not is_dist():
        return [st]
    out = [None for _ in range(dist.get_world_size())]
    dist.all_gather_object(out, st)
    return out


# ------------------------------------------------------------------ main training
def run_training(args, dataset_factory=None) -> dict:
    """`dataset_factory(split, dir) -> Dataset` is a TEST SEAM (DDP smoke injects a tiny
    synthetic dataset); default = the real GreenEarthNet dataset. It does not change the
    model / loss / schedule / contract."""
    if dataset_factory is None:
        from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
        dataset_factory = lambda split, d: GreenEarthNetContextformerDataset(d, dl_cloudmask=True)

    if not math.isfinite(args.future_state_scale) or args.future_state_scale < 0:
        raise ValueError("--future-state-scale must be finite and >= 0")
    if args.stop_after_step < 0:
        raise ValueError("--stop-after-step must be >= 0")

    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    world = int(os.environ.get("WORLD_SIZE", 1))
    seed_everything(args.seed + local_rank)
    use_cuda = torch.cuda.is_available() and args.device != "cpu"
    if world > 1:
        dist.init_process_group("nccl" if use_cuda else "gloo",
                                device_id=(torch.device("cuda", local_rank) if use_cuda else None))
        if use_cuda:
            torch.cuda.set_device(local_rank)
    dev = torch.device("cuda", local_rank) if use_cuda else torch.device("cpu")
    out = Path(args.output_dir)
    if rank0():
        out.mkdir(parents=True, exist_ok=True)

    hp = contextformer6m_hparams(pvt_pretrained=False)
    init_ck = torch.load(args.student_init, map_location="cpu", weights_only=False)
    teach_ck = torch.load(args.teacher_b4, map_location="cpu", weights_only=False)
    student_init_sha = state_sha(init_ck["b4_state_dict"])
    student = TerraStateV2(hp, contract_cfg={"state_dim": args.state_dim, "freeze_b0": True}).to(dev)
    miss, unexp, src = warm_start_terrastate_v2(student, init_ck)
    log(f"student warm-start EXACT ({src}): missing=0 unexpected=0")

    # INITIAL frozen target-encoder identity (must equal the cache's) — computed BEFORE training.
    q_proj_init_sha = module_pair_sha256(student.q, student.projector)
    log(f"student INITIAL q/projector SHA = {q_proj_init_sha[:16]}")

    teacher = build_teacher(hp, teach_ck["b4_state_dict"], dev)
    teacher_sha0 = state_sha(teacher.state_dict())

    # future-state caches (built offline); verify they match the frozen target encoder.
    # mmap=True so N DDP ranks share ONE page-cached copy; fail-closed if a big cache
    # cannot be mmap'd (would OOM CPU RAM under 8 ranks).
    train_cache = FutureStateCache(args.train_cache, args.train_dir,
                                   fail_closed_gb=args.cache_fail_closed_gb, verbose=rank0())
    val_cache = FutureStateCache(args.val_cache, args.val_dir,
                                 fail_closed_gb=args.cache_fail_closed_gb, verbose=rank0())
    for name, c in (("train", train_cache), ("val", val_cache)):
        c.verify(q_projector_sha256=q_proj_init_sha, field_order=FULL24_FIELD_ORDER,
                 horizon_h=student.target_len)
        log(f"{name} cache OK: {len(c)} cubes, q/proj SHA match, h={c.provenance['horizon_h']} "
            f"mmap={c.mmap_ok} size={c.size_bytes/1e9:.3f}GB")

    unfreeze_prefixes = [s for s in args.unfreeze_q_prefixes.split(",") if s]

    # ---- data ------------------------------------------------------------------------
    train_ds = dataset_factory("train", args.train_dir)
    val_ds = dataset_factory("val", args.val_dir)
    shuffle = not args.deterministic
    sampler = DistributedSampler(train_ds, shuffle=shuffle, seed=args.seed) if world > 1 else None
    gen = torch.Generator(); gen.manual_seed(args.seed)
    loader = DataLoader(train_ds, batch_size=args.per_gpu_batch, sampler=sampler,
                        shuffle=(sampler is None and shuffle), num_workers=args.num_workers,
                        collate_fn=collate_with_ids, pin_memory=use_cuda, drop_last=True,
                        generator=gen, worker_init_fn=seed_worker)
    # val: SPLIT across ranks (no 8x redundant full-val); validate_v2 all_reduces sum/count.
    val_sampler = DistributedSampler(val_ds, shuffle=False, drop_last=False) if world > 1 else None
    val_loader = DataLoader(val_ds, batch_size=args.per_gpu_batch, sampler=val_sampler, shuffle=False,
                            num_workers=args.num_workers, collate_fn=collate_with_ids,
                            pin_memory=use_cuda)

    # ---- global-batch / accumulation -------------------------------------------------
    denom = args.per_gpu_batch * world
    assert args.global_batch % denom == 0, (
        f"--global-batch {args.global_batch} not divisible by per_gpu({args.per_gpu_batch}) x world({world})")
    accum = args.global_batch // denom
    updates_per_epoch = max(len(loader) // accum, 1)
    total_steps = args.max_steps if args.max_steps > 0 else args.max_epochs * updates_per_epoch
    boundary80 = int(STAGE3_FRAC * total_steps)
    stop_after_step = args.stop_after_step if args.stop_after_step > 0 else total_steps
    if stop_after_step > total_steps:
        raise ValueError(f"--stop-after-step {stop_after_step} exceeds scheduled total_steps {total_steps}")
    log(f"world={world} per_gpu={args.per_gpu_batch} accum={accum} global_batch={args.global_batch} "
        f"updates/epoch={updates_per_epoch} total_steps={total_steps} boundary80={boundary80} "
        f"stop_after_step={stop_after_step}")
    raw0, effective0 = lambda_state_values(0, total_steps, args.future_state_scale)
    log(f"future_state_scale={args.future_state_scale:g} "
        f"lambda_state_raw(step0)={raw0:.6f} effective_lambda_state(step0)={effective0:.6f}")

    cl, tl = student.context_len, student.target_len

    # ---- optimizer / scheduler (built once; q group present from the start) ----------
    opt = build_optimizer(student, args.branch_lr, args.q_lr_scale, args.weight_decay)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda=lambda s: lr_factor(s, args.lr_warmup_steps, total_steps))
    for g in opt.param_groups:
        log(f"  opt '{g['name']}': tensors={len(g['params'])} base_lr={g['lr']:.2e}")

    # ---- provenance SHAs recorded in every checkpoint --------------------------------
    shas = {
        "q_projector_init_sha256": q_proj_init_sha,
        "teacher_sha256": teacher_sha0, "student_init_sha256": student_init_sha,
        "student_init_path": args.student_init, "teacher_b4_path": args.teacher_b4,
        "train_cache_sha256": train_cache.provenance.get("config_sha256"),
        "val_cache_sha256": val_cache.provenance.get("config_sha256"),
        "train_manifest_sha256": train_cache.provenance.get("data_manifest_sha256"),
        "val_manifest_sha256": val_cache.provenance.get("data_manifest_sha256"),
        "config_sha256": canonical_json_sha256({k: getattr(args, k) for k in sorted(vars(args))}),
    }

    # ---- resume ----------------------------------------------------------------------
    start_epoch, step, resume_micro = 0, 0, 0
    best_val = float("inf")
    current_stage = 1
    if args.resume:
        rk = torch.load(args.resume, map_location="cpu", weights_only=False)
        assert rk["arch"] == student.ARCH, "resume arch mismatch"
        assert rk["sha"]["q_projector_init_sha256"] == q_proj_init_sha, "resume q/proj SHA mismatch"
        assert rk["total_steps"] == total_steps, "resume total_steps mismatch (schedule changed)"
        for sha_key in (
            "teacher_sha256", "student_init_sha256",
            "train_cache_sha256", "val_cache_sha256",
            "train_manifest_sha256", "val_manifest_sha256",
        ):
            assert rk["sha"].get(sha_key) == shas.get(sha_key), (
                f"resume {sha_key} mismatch: checkpoint={rk['sha'].get(sha_key)} "
                f"current={shas.get(sha_key)}")
        assert int(rk["global_batch"]) == args.global_batch, "resume global_batch mismatch"
        assert int(rk["accum"]) == accum, "resume gradient-accumulation mismatch"
        resume_scale = float((rk.get("args") or {}).get(
            "future_state_scale", rk.get("future_state_scale", 1.0)))
        assert resume_scale == float(args.future_state_scale), (
            f"resume future_state_scale mismatch: checkpoint={resume_scale} "
            f"CLI={args.future_state_scale}")
        current_stage = int(rk["stage"])
        apply_stage(student, current_stage, unfreeze_prefixes)   # restore freeze-set BEFORE loading opt
        student.load_state_dict(rk["b4_state_dict"], strict=True)
        opt.load_state_dict(rk["optimizer_state_dict"])
        sched.load_state_dict(rk["scheduler_state_dict"])
        start_epoch = int(rk["epoch"]); step = int(rk["step"]); resume_micro = int(rk["micro_in_epoch"])
        best_val = float(rk["best_val"])
        rng_by_rank = rk.get("rng_states_by_rank") or [rk["rng_state"]]
        restore_rng_state(rng_by_rank[min(local_rank, len(rng_by_rank) - 1)])
        log(f"RESUME step={step} epoch={start_epoch} micro={resume_micro} stage={current_stage} "
            f"best_val={best_val:.5f}")
    else:
        current_stage = stage_at(step, total_steps)
        apply_stage(student, current_stage, unfreeze_prefixes)

    student.train()
    # DDP device_ids must be None on CPU/gloo (only set on CUDA/nccl).
    ddp_device_ids = [local_rank] if use_cuda else None
    model = DDP(student, device_ids=ddp_device_ids, find_unused_parameters=True) if world > 1 else student

    loss_log = []
    log_path = out / "loss_log.jsonl"
    q_grad_seen_stage3 = False

    def save(path, epoch, micro_in_epoch, vloss, candidate=None):
        # MUST be called by ALL ranks: _gather_rng() is a collective (all_gather_object);
        # only the actual file write is rank0. Calling this behind `if rank0()` deadlocks DDP.
        raw = model.module if hasattr(model, "module") else model
        trainable_q = sorted(n for n, p in raw.q.named_parameters() if p.requires_grad)
        gathered_rng = _gather_rng()                                  # <-- collective; all ranks
        lambda_raw, lambda_effective = lambda_state_values(
            step, total_steps, args.future_state_scale)
        ck = make_checkpoint(raw, opt, sched, epoch=epoch, step=step, micro_in_epoch=micro_in_epoch,
                             stage=current_stage, trainable_q=trainable_q, unfreeze_prefixes=unfreeze_prefixes,
                             best_val=best_val, total_steps=total_steps, accum=accum, world=world,
                             global_batch=args.global_batch, shas=shas, args=args,
                             lambda_state_raw=lambda_raw,
                             lambda_state_effective=lambda_effective, gathered_rng=gathered_rng)
        ck["candidate"] = candidate                                  # which pre-registered candidate this is
        if rank0():
            atomic_torch_save(ck, path)

    def maybe_transition(new_stage):
        nonlocal model, current_stage
        if new_stage != current_stage:
            # FORCED 80% boundary checkpoint at the stage2->3 unfreeze edge (doc 88 §4.3).
            if current_stage == 2 and new_stage == 3:
                save(out / "checkpoint_boundary80.pt", epoch, micro_in_epoch, None,
                     candidate="stage2_end_boundary80")
                log(f"  [boundary80] forced checkpoint saved at step {step}")
                # An exact boundary-stop run must not enter partial q unfreezing.  The
                # forced checkpoint above is stage 2 and is the only formal ablation
                # checkpoint; leave the in-memory model in stage 2 before terminating.
                if args.stop_after_step == step:
                    log(f"  [stop] requested at boundary80 step {step}; stage 3 not entered")
                    return
            trainable_q = apply_stage(model.module if hasattr(model, "module") else model,
                                      new_stage, unfreeze_prefixes)
            if world > 1:                      # re-wrap DDP so the reducer sees the new grad set
                model = DDP(model.module, device_ids=ddp_device_ids, find_unused_parameters=True)
            log(f"  [stage] {current_stage} -> {new_stage} at step {step}; trainable_q={len(trainable_q)}")
            current_stage = new_stage

    done = False
    t0 = time.time(); t_prev, step_prev = t0, step
    micro_in_epoch = resume_micro
    for epoch in range(start_epoch, 10_000_000):
        if done:
            break
        if sampler is not None:
            sampler.set_epoch(epoch)
        skip = resume_micro if epoch == start_epoch else 0
        micro_idx = 0
        window_finite = True
        for batch in loader:
            if micro_idx < skip:                 # fast-forward to the resumed data position
                micro_idx += 1
                continue
            data = to_device_with_ids(batch, dev)
            z_star, pmask = train_cache.gather(batch["filepath"], dev)
            with torch.no_grad():
                teacher_pred = teacher.encode(data, pred_start=cl, preds_length=tl)[0].detach()
            lam_s_raw, lam_s = lambda_state_values(step, total_steps, args.future_state_scale)
            in_window = (micro_idx - skip) % accum
            is_boundary = (in_window == accum - 1)
            sync_ctx = model.no_sync() if (world > 1 and not is_boundary) else nullcontext()
            with sync_ctx:
                _, aux = model(data, teacher_pred, z_star, pmask, lam_s)
                loss = aux["total"] / accum
                window_finite = window_finite and bool(torch.isfinite(loss))
                loss.backward()
            micro_idx += 1
            micro_in_epoch = micro_idx
            if not is_boundary:
                continue

            finite = window_finite
            if is_dist():
                f = torch.tensor([1.0 if finite else 0.0], device=dev)
                dist.all_reduce(f, op=dist.ReduceOp.MIN)
                finite = f.item() > 0.5
            if not finite:
                log(f"WARN non-finite loss window @ step {step}; skip update (all ranks)")
                opt.zero_grad(set_to_none=True); window_finite = True
                sched.step(); step += 1
                maybe_transition(stage_at(step, total_steps))
                if stop_after_step < total_steps and step >= stop_after_step:
                    done = True
                    break
                continue

            raw_m = model.module if hasattr(model, "module") else model
            if current_stage == 3 and not q_grad_seen_stage3:        # verify unfrozen q block trains
                for _n, _p in raw_m.q.named_parameters():
                    if _p.requires_grad and _p.grad is not None and torch.isfinite(_p.grad).any():
                        q_grad_seen_stage3 = True
                        break
            if args.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(raw_m.parameters(), args.grad_clip)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            step += 1; window_finite = True

            if rank0():
                lg = {k: float(v) for k, v in aux["logs"].items() if k not in ("alpha",)}
                loss_log.append({"step": step, "stage": current_stage,
                                 "future_state_scale": float(args.future_state_scale),
                                 "lambda_state_raw": lam_s_raw,
                                 "lambda_state": lam_s,
                                 "effective_lambda_state": lam_s,
                                 "total": float(aux["total"]), "gt": lg.get("gt"),
                                 "kd": lg.get("kd"), "future_state": lg.get("future_state")})
            if step % args.log_interval == 0 and rank0():
                now = time.time(); ips = (step - step_prev) / max(now - t_prev, 1e-6); t_prev, step_prev = now, step
                l = aux["logs"]
                log(f"step {step}/{total_steps} st{current_stage} {ips:.2f}it/s "
                    f"lam_s_raw={lam_s_raw:.4f} lam_s_effective={lam_s:.4f} "
                    f"fs_scale={args.future_state_scale:g} lr={sched.get_last_lr()[0]:.2e} "
                    f"total={float(l['total']):.5f} gt={float(l['gt']):.5f} "
                    f"kd={float(l['kd']):.5f} fs={float(l['future_state']):.5f}")

            maybe_transition(stage_at(step, total_steps))
            if stop_after_step < total_steps and step >= stop_after_step:
                done = True
                break

            if step % args.val_interval == 0 or step == total_steps:
                vfs, vgt = validate_v2(model, val_loader, val_cache, dev)
                improved = vfs < best_val
                log(f"  [val] step {step} future_state={vfs:.5f} gt={vgt:.5f} (best {best_val:.5f})")
                if improved:
                    best_val = vfs
                    # NOTE: 'future-state-val best' candidate — NOT automatically the final
                    # checkpoint. Final = Q1 qualifier first, then min non-intervention
                    # future-state val loss among {boundary80, fsval_best, last} (doc 88 §6.3).
                    save(out / "checkpoint_fsval_best.pt", epoch, micro_in_epoch, vfs,
                         candidate="future_state_val_best")
                    log(f"  saved future-state-val best={vfs:.5f} -> checkpoint_fsval_best.pt "
                        f"(candidate only; final selection is post-hoc)")
            if args.ckpt_interval > 0 and step % args.ckpt_interval == 0:
                save(out / f"checkpoint_step{step}.pt", epoch, micro_in_epoch, None, candidate="interval")
            if step >= total_steps:
                done = True; break
        resume_micro = 0  # only skip within the resumed epoch

    # checkpoint_last: ALL ranks call save() (it does a collective _gather_rng internally,
    # only rank0 writes the file). Gating this behind `if rank0()` would deadlock DDP.
    save(out / "checkpoint_last.pt", epoch, micro_in_epoch, None, candidate="last")
    if rank0():
        log_path.write_text("\n".join(json.dumps(r) for r in loss_log))
    assert state_sha(teacher.state_dict()) == teacher_sha0, "teacher weights changed during training!"
    raw_m = model.module if hasattr(model, "module") else model
    tq = {n: p for n, p in raw_m.q.named_parameters() if p.requires_grad}
    q_last_block_sha = state_sha(tq) if tq else ""
    log(f"done step={step} best_val={best_val:.5f} teacher_unchanged=True "
        f"stage3_qgrad_seen={q_grad_seen_stage3} out={out}")
    if is_dist():
        dist.barrier(); dist.destroy_process_group()
    return {"step": step, "best_val": best_val, "total_steps": total_steps,
            "loss_log": loss_log, "boundary80": boundary80, "accum": accum,
            "global_batch": args.global_batch, "final_stage": current_stage,
            "future_state_scale": float(args.future_state_scale),
            "stop_after_step": stop_after_step,
            "model_sha": state_sha(raw_m.state_dict()),
            "q_grad_seen_stage3": q_grad_seen_stage3, "q_last_block_sha": q_last_block_sha,
            "n_trainable_q": len(tq)}


def build_argparser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-dir", required=True); ap.add_argument("--val-dir", required=True)
    ap.add_argument("--train-cache", required=True); ap.add_argument("--val-cache", required=True)
    ap.add_argument("--student-init", required=True, help="Phase-I b4 OR exclusive warm-start")
    ap.add_argument("--teacher-b4", required=True, help="frozen full-weather B4 (KD teacher source)")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--resume", default="", help="checkpoint to exactly resume from")
    ap.add_argument("--state-dim", type=int, default=256)
    ap.add_argument("--per-gpu-batch", type=int, default=8)
    ap.add_argument("--global-batch", type=int, default=64, help="held constant via grad accumulation")
    ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--max-epochs", type=int, default=40)
    ap.add_argument("--max-steps", type=int, default=0, help=">0 overrides epochs (smoke)")
    ap.add_argument("--stop-after-step", type=int, default=0,
                    help=">0 stops execution at this update without changing the planned schedule/total_steps")
    ap.add_argument("--future-state-scale", type=float, default=1.0,
                    help="explicit multiplier on scheduled lambda_s; use 0 only for the no-FS-anchor ablation")
    ap.add_argument("--branch-lr", type=float, default=3e-5)
    ap.add_argument("--q-lr-scale", type=float, default=0.033, help="q LR = branch LR x this (doc: 0.02-0.05)")
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--grad-clip", type=float, default=1.0)
    ap.add_argument("--lr-warmup-steps", type=int, default=300, help="linear LR warm-up (doc: 200-500)")
    ap.add_argument("--unfreeze-q-prefixes", default="core.blocks.2.",
                    help="stage-3 q unfreeze (doc 88: last transformer block only)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--log-interval", type=int, default=50)
    ap.add_argument("--val-interval", type=int, default=1000)
    ap.add_argument("--ckpt-interval", type=int, default=2000)
    ap.add_argument("--device", default="cuda", help="'cpu' forces CPU (smoke)")
    ap.add_argument("--cache-fail-closed-gb", type=float, default=4.0,
                    help="if a cache exceeds this size AND cannot be mmap'd, refuse to load (per-rank OOM guard)")
    ap.add_argument("--deterministic", action="store_true", help="shuffle=False for exact resume tests")
    return ap


def main():
    run_training(build_argparser().parse_args())


if __name__ == "__main__":
    main()
