#!/usr/bin/env python
"""M0 three-way parameter audit (read-only).

Cross-checks every training parameter that controls the exact-resume schedule across
three INDEPENDENT sources:

  A. PARENT checkpoint  (checkpoint_boundary80.pt: top-level fields + `args` + `sha`)
  B. the original run log (run1/train.log -- what the process actually printed)
  C. TERRASTATE_V2_RUNBOOK.md section 4 (the canonical documented command)

and records the FROZEN value that the resume launch must use.  Nothing is written
outside this ops directory; no checkpoint is modified.

Discrepancies are NOT auto-resolved: each row carries `consistent` plus a note.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import torch

PARENT = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb-v2train/runs/terrastate_v2/run1/checkpoint_boundary80.pt")
TRAINLOG = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb-v2train/runs/terrastate_v2/run1/train.log")
RUNBOOK = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/TERRASTATE_V2_RUNBOOK.md")
HERE = Path(__file__).resolve().parent

# Values documented in RUNBOOK section 4 (canonical full-training command).  Transcribed
# ONCE here and then asserted against the file text below, so a runbook edit cannot
# silently diverge from this audit.
RUNBOOK_CLI = {
    "per_gpu_batch": ("--per-gpu-batch 8", 8),
    "global_batch": ("--global-batch 64", 64),
    "max_epochs": ("--max-epochs 40", 40),
    "branch_lr": ("--branch-lr 3e-5", 3e-5),
    "q_lr_scale": ("--q-lr-scale 0.033", 0.033),
    "weight_decay": ("--weight-decay 0.0", 0.0),
    "grad_clip": ("--grad-clip 1.0", 1.0),
    "lr_warmup_steps": ("--lr-warmup-steps 300", 300),
    "unfreeze_q_prefixes": ('--unfreeze-q-prefixes "core.blocks.2."', "core.blocks.2."),
    "val_interval": ("--val-interval 1000", 1000),
    "ckpt_interval": ("--ckpt-interval 2000", 2000),
    "seed": ("--seed 42", 42),
}


def parse_trainlog(text: str) -> dict:
    out: dict = {}
    m = re.search(
        r"world=(\d+) per_gpu=(\d+) accum=(\d+) global_batch=(\d+) "
        r"updates/epoch=(\d+) total_steps=(\d+) boundary80=(\d+)", text)
    if m:
        (out["world_size"], out["per_gpu_batch"], out["accum"], out["global_batch"],
         out["updates_per_epoch"], out["total_steps"], out["boundary80"]) = [int(x) for x in m.groups()]
    for name in ("branch", "q"):
        mm = re.search(rf"opt '{name}': tensors=(\d+) base_lr=([0-9.eE+-]+)", text)
        if mm:
            out[f"opt_{name}_tensors"] = int(mm.group(1))
            out[f"opt_{name}_base_lr_logged"] = float(mm.group(2))
    mm = re.search(r"\[boundary80\] forced checkpoint saved at step (\d+)", text)
    if mm:
        out["boundary80_saved_at_step"] = int(mm.group(1))
    for a, b in re.findall(r"\[stage\] (\d) -> (\d) at step (\d+); trainable_q=(\d+)", text)[:0]:
        pass
    for g in re.finditer(r"\[stage\] (\d) -> (\d) at step (\d+); trainable_q=(\d+)", text):
        out[f"stage_{g.group(1)}_to_{g.group(2)}"] = {
            "step": int(g.group(3)), "trainable_q": int(g.group(4))}
    mm = re.search(r"done step=(\d+) best_val=([0-9.]+) teacher_unchanged=(\w+) "
                   r"stage3_qgrad_seen=(\w+)", text)
    if mm:
        out["done_step"] = int(mm.group(1))
        out["done_best_val"] = float(mm.group(2))
        out["teacher_unchanged"] = mm.group(3) == "True"
        out["stage3_qgrad_seen"] = mm.group(4) == "True"
    mm = re.search(r"train cache OK: (\d+) cubes.*?h=(\d+) mmap=(\w+) size=([0-9.]+)GB", text)
    if mm:
        out["train_cache_cubes"] = int(mm.group(1))
        out["cache_horizon_h"] = int(mm.group(2))
        out["train_cache_mmap"] = mm.group(3)
        out["train_cache_size_gb"] = float(mm.group(4))
    mm = re.search(r"val cache OK: (\d+) cubes", text)
    if mm:
        out["val_cache_cubes"] = int(mm.group(1))
    mm = re.search(r"student INITIAL q/projector SHA = ([0-9a-f]+)", text)
    if mm:
        out["q_projector_init_sha256_prefix"] = mm.group(1)
    return out


def main():
    ck = torch.load(PARENT, map_location="cpu", weights_only=False)
    cargs = dict(ck["args"])
    logtext = TRAINLOG.read_text(errors="replace")
    lg = parse_trainlog(logtext)
    rb = RUNBOOK.read_text(errors="replace")

    rows = []

    def row(name, ckpt_val, log_val, rb_val, frozen, note="", *, compare=True):
        srcs = [v for v in (ckpt_val, log_val, rb_val) if v is not None]
        consistent = (not compare) or all(v == srcs[0] for v in srcs)
        rows.append({
            "parameter": name,
            "checkpoint": ckpt_val,
            "train_log": log_val,
            "runbook": rb_val,
            "frozen_value_for_resume": frozen,
            "consistent": bool(consistent),
            "note": note,
        })

    # ---- runbook literal presence check ------------------------------------------
    rb_missing = [k for k, (lit, _) in RUNBOOK_CLI.items() if lit not in rb]
    rb_val = {k: v for k, (_, v) in RUNBOOK_CLI.items()}

    # ---- schedule-defining parameters --------------------------------------------
    row("per_gpu_batch", cargs["per_gpu_batch"], lg.get("per_gpu_batch"), rb_val["per_gpu_batch"], 8)
    row("global_batch", cargs["global_batch"], lg.get("global_batch"), rb_val["global_batch"], 64,
        "resume asserts int(ck['global_batch'])==args.global_batch")
    row("world_size", int(ck["world_size"]), lg.get("world_size"), 8, 8,
        "runbook uses --nproc_per_node=8")
    row("accum", int(ck["accum"]), lg.get("accum"), 1, 1,
        "accum = global_batch // (per_gpu*world) = 64//64; resume asserts equality")
    row("max_epochs", cargs["max_epochs"], None, rb_val["max_epochs"], 40,
        "total_steps = max_epochs * updates_per_epoch; must reproduce 14880")
    row("max_steps", cargs["max_steps"], None, 0, 0, "0 => epochs govern the schedule")
    row("total_steps", int(ck["total_steps"]), lg.get("total_steps"), None, 14880,
        "top-level checkpoint field; resume asserts rk['total_steps']==total_steps")
    row("updates_per_epoch", None, lg.get("updates_per_epoch"), None, 372,
        "len(loader)//accum with drop_last=True over 23816 cubes / (8 ranks x bs8)")
    row("boundary80", None, lg.get("boundary80"), None, 11904,
        "int(0.80*14880); == parent checkpoint step")
    row("branch_lr", cargs["branch_lr"], None, rb_val["branch_lr"], 3e-5)
    row("q_lr_scale", cargs["q_lr_scale"], None, rb_val["q_lr_scale"], 0.033)
    row("weight_decay", cargs["weight_decay"], None, rb_val["weight_decay"], 0.0)
    row("grad_clip", cargs["grad_clip"], None, rb_val["grad_clip"], 1.0)
    row("lr_warmup_steps", cargs["lr_warmup_steps"], None, rb_val["lr_warmup_steps"], 300)
    row("unfreeze_q_prefixes", cargs["unfreeze_q_prefixes"], None,
        rb_val["unfreeze_q_prefixes"], "core.blocks.2.")
    row("seed", cargs["seed"], None, rb_val["seed"], 42)
    row("val_interval", cargs["val_interval"], None, rb_val["val_interval"], 1000)
    row("ckpt_interval", cargs["ckpt_interval"], None, rb_val["ckpt_interval"], 2000)
    row("log_interval", cargs["log_interval"], None, 50, 50)
    row("num_workers", cargs["num_workers"], None, None, 8,
        "not schedule-affecting (DataLoader worker count)")
    row("state_dim", cargs["state_dim"], None, 256, 256)
    row("device", cargs["device"], None, "cuda", "cuda")
    row("deterministic", cargs["deterministic"], None, False, False,
        "False => train sampler shuffles; exact data order restored via "
        "sampler.set_epoch(epoch) + rng_states_by_rank")
    row("cache_fail_closed_gb", cargs["cache_fail_closed_gb"], None, None, 4.0)
    row("alpha", float(ck["alpha"]), None, 1.0, 1.0, "fixed non-learnable buffer")
    row("loss_weights.gt", ck["loss_weights"]["gt"], None, 1.0, 1.0)
    row("loss_weights.kd", ck["loss_weights"]["kd"], None, 0.5, 0.5)
    row("lambda_state@11904", float(ck["lambda_state"]), None, 0.01, 0.01,
        "stage-3 value LAM_LATE; lambda_state_at(11904,14880)=0.01")

    # ---- resume-position fields (checkpoint only) --------------------------------
    row("resume.step", int(ck["step"]), lg.get("boundary80_saved_at_step"), None, 11904,
        "first post-resume update is number 11905", compare=True)
    row("resume.epoch", int(ck["epoch"]), None, None, 31,
        "11904/372 = 32 completed epochs => epoch index 31 was the last one finished; "
        "the trainer restarts the loop AT epoch 31 and fast-forwards micro_in_epoch",
        compare=False)
    row("resume.micro_in_epoch", int(ck["micro_in_epoch"]), None, None, 372,
        "== updates_per_epoch => the resumed epoch 31 is fully consumed and the loop "
        "should advance to epoch 32", compare=False)
    row("resume.stage", int(ck["stage"]), None, None, 2,
        "RECORDED stage is 2 because the boundary checkpoint is written BEFORE the "
        "2->3 switch (train.log: save then '[stage] 2 -> 3 at step 11904'). An exact "
        "resume must therefore enter stage 3 BEFORE its first update -- this is the "
        "M2/M3 bug.", compare=False)
    row("resume.q_freeze.trainable_q", ck["q_freeze"]["trainable_q"], None, None, [],
        "empty in the parent; must become the 12 core.blocks.2.* tensors after the fix",
        compare=False)
    row("resume.best_val", float(ck["best_val"]), None, None, 0.31334985432787643,
        "carried forward so post-resume val comparisons keep the same baseline",
        compare=False)

    # ---- data / cache identity ---------------------------------------------------
    row("sha.q_projector_init_sha256", ck["sha"]["q_projector_init_sha256"],
        lg.get("q_projector_init_sha256_prefix"), None,
        ck["sha"]["q_projector_init_sha256"],
        "train.log prints only the 16-char prefix", compare=False)
    row("sha.train_manifest_sha256", ck["sha"]["train_manifest_sha256"], None, None,
        ck["sha"]["train_manifest_sha256"], "verified separately by check_data_manifest.py")
    row("sha.val_manifest_sha256", ck["sha"]["val_manifest_sha256"], None, None,
        ck["sha"]["val_manifest_sha256"], "verified separately by check_data_manifest.py")
    row("sha.train_cache_sha256", ck["sha"]["train_cache_sha256"], None, None,
        ck["sha"]["train_cache_sha256"],
        "this is the cache CONFIG sha (schema/protocol/field_order/horizon/patch rule/"
        "q_projector sha) -- identical for train and val BY DESIGN, not a copy/paste bug")
    row("sha.val_cache_sha256", ck["sha"]["val_cache_sha256"], None, None,
        ck["sha"]["val_cache_sha256"], "same config sha as train (see above)")
    row("train_cache_cubes", None, lg.get("train_cache_cubes"), None, 23816)
    row("val_cache_cubes", None, lg.get("val_cache_cubes"), None, 952)
    row("cache_horizon_h", None, lg.get("cache_horizon_h"), None, 20)

    # ---- paths -------------------------------------------------------------------
    row("args.train_dir", cargs["train_dir"], None, None,
        "/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/train",
        "ORIGINAL /tmp staging dir no longer exists; substitution is legal ONLY if "
        "data_manifest_sha256 matches (checked by check_data_manifest.py). relpath keys "
        "are root-relative so the cache still resolves.", compare=False)
    row("args.val_dir", cargs["val_dir"], None, None,
        "/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/val_chopped",
        "same as train_dir", compare=False)
    row("args.train_cache", cargs["train_cache"], None, None, cargs["train_cache"],
        "12.5GB cache stays in place (registry-by-path only)", compare=False)
    row("args.val_cache", cargs["val_cache"], None, None, cargs["val_cache"], "", compare=False)
    row("args.student_init", cargs["student_init"], None, None, cargs["student_init"],
        "resolved via the artifact registry; SHA must equal sha.student_init_sha256",
        compare=False)
    row("args.teacher_b4", cargs["teacher_b4"], None, None, cargs["teacher_b4"],
        "resolved via the artifact registry; q.* SHA must equal sha.teacher_sha256",
        compare=False)
    row("args.output_dir", cargs["output_dir"], None, None,
        "<NEW dir under terrastate/runs/resume11904_to14880/>",
        "MUST NOT reuse the original run1 dir -- historical outputs are read-only",
        compare=False)

    inconsistent = [r["parameter"] for r in rows if not r["consistent"]]
    payload = {
        "audit_kind": "terrastate_v2_resume_11904_to_14880_parameter_audit",
        "generated_by": "ops/resume11904_to14880/20260818_112933/make_parameter_audit.py",
        "sources": {
            "checkpoint": str(PARENT),
            "checkpoint_file_sha256": "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd",
            "train_log": str(TRAINLOG),
            "runbook": str(RUNBOOK),
        },
        "runbook_literals_missing": rb_missing,
        "train_log_parsed": lg,
        "rows": rows,
        "n_rows": len(rows),
        "inconsistent_parameters": inconsistent,
        "all_consistent": not inconsistent and not rb_missing,
        "arithmetic_self_consistency": {
            "total_steps_minus_parent_step": 14880 - 11904,
            "remaining_updates": 2976,
            "updates_per_epoch": 372,
            "remaining_epochs": 2976 / 372,
            "epochs_range": "32..39 inclusive (start_epoch index 31 fully consumed)",
            "boundary80_formula": "int(0.80 * 14880) == 11904",
            "ok": (14880 - 11904) == 2976 and 2976 % 372 == 0,
        },
        "stage_boundary_semantics": {
            "stage_at_11904": 3,
            "recorded_stage_in_parent": int(ck["stage"]),
            "evidence": "train.log: '[boundary80] forced checkpoint saved at step 11904' "
                        "immediately followed by '[stage] 2 -> 3 at step 11904; trainable_q=12'",
            "requirement": "the first post-resume update (#11905) must run in stage 3 with "
                           "exactly the 12 core.blocks.2.* q tensors trainable, and the run "
                           "must NOT re-save checkpoint_boundary80.pt",
        },
    }
    dest = HERE / "parameter_audit.json"
    dest.write_text(json.dumps(payload, indent=2, sort_keys=False, default=str))
    print(f"rows={len(rows)} inconsistent={inconsistent} runbook_missing={rb_missing}")
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
