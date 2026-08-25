#!/usr/bin/env python
"""M5: freeze an IMMUTABLE launch manifest for the exact-resume 11,904 -> 14,880 run.

Everything the formal run needs is pinned here BEFORE any GPU is touched: repo HEAD, the
single tracked diff, key-file SHA256s, the artifact registry revision, the four resolved
weight artifacts, the frozen data/cache fingerprints, the full torchrun command, and the
arithmetic that must reproduce (total_steps==14880, boundary80==11904).

Writes launch_manifest.json mode 0444. Refuses to overwrite an existing manifest.
Read-only w.r.t. everything outside this ops directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TS_ROOT = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate")
OPS = TS_ROOT / "ops/resume11904_to14880/20260818_112933"
OUT = OPS / "launch_manifest.json"
PY = "/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python"
REG = TS_ROOT / "artifacts/weight_registry.json"

DATA_TRAIN = "/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/train"
DATA_VAL = "/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/val_chopped"
CACHE_DIR = "/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb-v2train/runs/terrastate_v2/cache"

KEY_FILES = [
    "train/train_terrastate_v2.py",
    "train/terrastate_v2_common.py",
    "train/terrastate_future_state_cache.py",
    "models/terrastate_v2.py",
    "models/encoders/pvt_contextformer_q.py",
    "data/greenearthnet_contextformer_dataset.py",
    "tests/test_resume_boundary11904.py",
    "tests/smoke_terrastate_v2.py",
    "tests/smoke_terrastate_v2_ddp.py",
    "tools/resolve_artifact.py",
    "artifacts/weight_registry.json",
]


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def git(*a) -> str:
    return subprocess.run(["git", *a], cwd=TS_ROOT, capture_output=True, text=True).stdout.strip()


def git_raw(*a) -> str:
    """Unstripped stdout. `git status --short` encodes state in a FIXED 3-char prefix
    ('XY '), so stripping the stream would eat the leading space of ' M path' and shift
    every path by one character."""
    return subprocess.run(["git", *a], cwd=TS_ROOT, capture_output=True, text=True).stdout


def status_modified() -> list[str]:
    out = []
    for l in git_raw("status", "--short").splitlines():
        xy, path = l[:2], l[3:]
        if "M" in xy or "T" in xy or "A" in xy or "D" in xy or "R" in xy:
            out.append({"xy": xy, "path": path})
    return out


def resolve(logical_id: str) -> dict:
    """Resolve through the M1 resolver so the manifest records verified store paths."""
    r = subprocess.run([PY, str(TS_ROOT / "tools/resolve_artifact.py"), logical_id, "--json"],
                       cwd=TS_ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"resolver failed for {logical_id} rc={r.returncode}: {r.stderr[:400]}")
    return json.loads(r.stdout)


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"REFUSING to overwrite an existing frozen manifest: {OUT}")

    reg = json.loads(REG.read_text())

    ids = {
        "resume_parent": "terrastate/v2/legacy-boundary11904@v1",
        "student_init": "obsworld/b4-exclusive/student-main-last-step14880@v1",
        "teacher_b4": "obsworld/b4/teacher-best-step13000@v1",
        "historical_reference": "terrastate/v2/historical-full14880@v1",
        "train_cache": "terrastate/v2/future-state-cache-train@v1",
        "val_cache": "terrastate/v2/future-state-cache-val@v1",
    }
    resolved = {k: resolve(v) for k, v in ids.items()}

    # ---- frozen hyper-parameters (from the parent checkpoint args; see parameter_audit.json)
    hp = {
        "state_dim": 256, "per_gpu_batch": 8, "global_batch": 64, "num_workers": 8,
        "max_epochs": 40, "max_steps": 0, "branch_lr": 3e-05, "q_lr_scale": 0.033,
        "weight_decay": 0.0, "grad_clip": 1.0, "lr_warmup_steps": 300,
        "unfreeze_q_prefixes": "core.blocks.2.", "seed": 42, "log_interval": 50,
        "val_interval": 1000, "ckpt_interval": 2000, "cache_fail_closed_gb": 4.0,
        "future_state_scale": 1.0, "deterministic": False, "allow_existing_out": False,
    }

    # ---- arithmetic that MUST reproduce, else the resume assertion fires ------------------
    n_train, world, accum = 23816, 8, 1
    per_rank = n_train // world
    batches = per_rank // hp["per_gpu_batch"]
    upd = max(batches // accum, 1)
    total_steps = hp["max_epochs"] * upd
    boundary80 = int(0.80 * total_steps)
    assert total_steps == 14880 and boundary80 == 11904 and upd == 372, "arithmetic drift"

    run_dir = f"runs/resume11904_to14880/{OPS.name}"
    cmd = [
        PY, "-m", "torch.distributed.run", "--standalone", "--nproc_per_node=8",
        "-m", "train.train_terrastate_v2",
        "--train-dir", DATA_TRAIN, "--val-dir", DATA_VAL,
        "--train-cache", resolved["train_cache"]["resolved_path"],
        "--val-cache", resolved["val_cache"]["resolved_path"],
        "--student-init", resolved["student_init"]["resolved_path"],
        "--teacher-b4", resolved["teacher_b4"]["resolved_path"],
        "--output-dir", run_dir,
        "--resume", resolved["resume_parent"]["resolved_path"],
        "--state-dim", "256",
        "--per-gpu-batch", "8", "--global-batch", "64",
        "--num-workers", "8", "--max-epochs", "40",
        "--future-state-scale", "1.0",
        "--branch-lr", "3e-5", "--q-lr-scale", "0.033",
        "--weight-decay", "0.0", "--grad-clip", "1.0",
        "--lr-warmup-steps", "300", "--unfreeze-q-prefixes", "core.blocks.2.",
        "--seed", "42", "--log-interval", "50",
        "--val-interval", "1000", "--ckpt-interval", "2000",
        "--device", "cuda", "--cache-fail-closed-gb", "4.0",
    ]

    # Guard 13 (protect the workspace): the ONLY tracked file this task may have modified is
    # the trainer. If anything else shows as modified/added/deleted, freezing a launch manifest
    # would be recording someone else's uncommitted work as part of my run -> fail closed.
    mods = status_modified()
    assert [m["path"] for m in mods] == ["train/train_terrastate_v2.py"], (
        f"unexpected tracked modifications: {mods} (expected only train/train_terrastate_v2.py)")

    diff_path = OPS / "m3_trainer.diff"
    man = {
        "schema": "terrastate_launch_manifest_v1",
        "purpose": "exact-resume of the TerraState-V2 unique training line from step 11,904 to 14,880",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "ops_dir": str(OPS),
        "workdir": str(TS_ROOT),
        "python": PY,
        "repo": {
            "head": git("rev-parse", "HEAD"),
            "head_subject": git("log", "-1", "--format=%s"),
            "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "tracked_files_modified": status_modified(),
            "tracked_files_modified_expected": ["train/train_terrastate_v2.py"],
            "diff_file": diff_path.name,
            "diff_sha256": sha256_file(diff_path),
            "no_commit": True, "no_push": True, "no_git_add": True,
        },
        "key_file_sha256": {f: sha256_file(TS_ROOT / f) for f in KEY_FILES},
        "artifact_registry": {
            "path": "terrastate/artifacts/weight_registry.json",
            "schema": reg.get("schema"),
            "revision": reg.get("revision"),
            "sha256": sha256_file(REG),
        },
        "artifacts_resolved": resolved,
        "data": {
            "train_dir": DATA_TRAIN, "val_dir": DATA_VAL,
            "train_manifest_sha256": "17c645d92e9dd4c38ce5bf14a412115c5f6622109cff3c19118b098e604b2554",
            "val_manifest_sha256": "555d44c0d59ab3902cf7d929ca86ce8bf4e3ce7cfda66c1c72b45a2ed3fd76c9",
            "n_train_cubes": 23816, "n_val_cubes": 952,
            "cache_config_sha256_both_splits": "2a14f0a4c3653f38ee52155d38c38f76d01cc234a5fb301a3dfb512ee0101a66",
            "cache_config_note": ("config_sha256 is a PROTOCOL fingerprint (no split/content), so "
                                  "train==val BY DESIGN; data identity is data_manifest_sha256 + mask_sha256"),
            "evidence": "data_manifest_check.json (all_match=true, three-way agreement)",
        },
        "hyperparameters_frozen": hp,
        "arithmetic": {
            "n_train_cubes": n_train, "world_size": world, "per_rank": per_rank,
            "batches_per_rank_drop_last": batches, "accum": accum,
            "updates_per_epoch": upd, "total_steps": total_steps, "boundary80": boundary80,
            "parent_step": 11904, "remaining_updates": total_steps - 11904,
            "epochs_to_run": "32..39 inclusive (start_epoch=31 is fully skipped: micro_in_epoch==372==full epoch)",
            "must_hold": "total_steps==14880 and boundary80==11904, else the resume assertion fires",
        },
        "expected_behaviour": {
            "first_post_resume_update": 11905,
            "first_post_resume_stage": 3,
            "stage_recomputed_from": "stage_at(11904, 14880)==3 (parent RECORDS stage 2 — that is the saved update's stage)",
            "trainable_q_tensors": 12,
            "trainable_q_prefix": "core.blocks.2.",
            "no_new_boundary80": "suppressed: parent step == boundary80",
            "lambda_state": "0.01 (STAGE3, late) for every remaining update",
            "val_at_steps": [12000, 13000, 14000, 14880],
            "interval_ckpt_at_steps": [12000, 14000],
            "final_checkpoint": "checkpoint_last.pt at step 14880",
            "data_order_restoration": "exact — world=8 DistributedSampler(seed=42, epoch) fully determines the order, and the resume point sits on an epoch boundary",
            "median_throughput_original_run_it_s": 1.57,
            "compute_estimate_minutes": round((total_steps - 11904) / 1.57 / 60, 1),
            "plus_one_skipped_epoch_io": "epoch 31 is re-iterated and discarded (372 batches of loader I/O, no compute)",
        },
        "command": cmd,
        "command_str": " ".join(cmd),
        "output_dir_relative": run_dir,
        "output_dir_absolute": str(TS_ROOT / run_dir),
        "output_dir_must_not_exist": True,
        "env": {
            "TOKENIZERS_PARALLELISM": "false",
            "NCCL_ASYNC_ERROR_HANDLING": "1",
            "PYTHONUNBUFFERED": "1",
            "note": "CUDA_VISIBLE_DEVICES intentionally UNSET so all 8 GPUs are used; never a subset",
        },
        "cpu_gate": {
            "test_resume_boundary11904": "13/13 PASS",
            "smoke_terrastate_v2_ddp": "7/7 PASS",
            "smoke_terrastate_v2": "19/20 PASS (only 13/iso, a pre-existing committed-repo condition)",
            "evidence": "m4_cpu_gate.json",
            "bit_exact": "R8b: resumed final weights == uninterrupted reference (e6d4ca3fda535f61)",
        },
        "preconditions_before_launch": [
            "all 8 GPUs: memory.used < 1024 MiB AND utilization < 5% for 10 consecutive 60s polls (>=10 min stable idle)",
            "no non-task process holds any target GPU; partial-GPU launch is FORBIDDEN",
            "output_dir does not exist (guard_output_dir would refuse anyway)",
            "no other TerraState training process started by this task is alive",
        ],
        "forbidden": [
            "kill/pause/renice/migrate any process not started by this task",
            "sudo; MIG/clock/power/persistence changes; crontab edits",
            "training on a subset of GPUs or alongside another user's job",
            "lowering the idle bar because the wait is long",
            "overwriting historical outputs; deleting or moving original weights",
            "git add / commit / push",
        ],
        "immutable": True,
    }

    OUT.write_text(json.dumps(man, ensure_ascii=False, indent=2))
    os.chmod(OUT, 0o444)
    print(f"FROZEN {OUT}")
    print(f"  head            = {man['repo']['head'][:12]}  branch={man['repo']['branch']}")
    print(f"  tracked modified= {man['repo']['tracked_files_modified']}")
    print(f"  registry rev    = {man['artifact_registry']['revision']}")
    print(f"  total_steps     = {total_steps}  boundary80={boundary80}  remaining={total_steps-11904}")
    print(f"  output_dir      = {run_dir}")
    print(f"  manifest sha256 = {sha256_file(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
