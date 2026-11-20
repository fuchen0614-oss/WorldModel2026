"""Explicit stage1 topology continuation; existing exact-resume rules stay strict."""
import hashlib
import math
from pathlib import Path

_RUNTIME_ARGS = {"runtime_world_size", "output_dir", "resume", "allow_existing_out", "handoff_dir", "handoff_token", "handoff_timeout", "train_dir", "val_dir", "val_split_manifest", "q4_partition_manifest", "parent_ckpt", "config"}
_SOURCE_CHANGES = {"train/train_spanworld_full_base.py", "train/topology_migration.py"}
_PATH_SHAS = {"config_sha256", "val_split_manifest_path", "q4_partition_manifest_path", "parent_logical_id"}

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def verified_load(path, expected):
    if len(expected) != 64 or digest(path) != expected:
        raise ValueError("migration checkpoint SHA mismatch")
    import torch
    return torch.load(path, map_location="cpu", weights_only=False)

def validate_migration(old, current_args, current_shas, world, accum):
    if (old.get("training_stage"), old.get("world_size"), old.get("accum"), world, accum) != ("stage1",2,2,4,1):
        raise ValueError("only stage1 2x8x2 to 4x8x1 migration is supported")
    if old.get("micro_in_epoch") != 0 or old.get("completion_reason") != "epoch_complete":
        raise ValueError("migration needs a committed complete data epoch")
    if old.get("global_batch") != 32 or old.get("total_steps") != 29800 or not 0 < old.get("step",0) < 29800 or old.get("epoch",0) <= 0:
        raise ValueError("migration budget/boundary invalid")
    schedule = old.get("scheduler_state_dict", {})
    if schedule.get("last_epoch") != old["step"]:
        raise ValueError("saved scheduler step differs from effective step")
    if schedule.get("_last_lr") != [g["lr"] for g in old.get("optimizer_state_dict", {}).get("param_groups", [])]:
        raise ValueError("saved scheduler and optimizer learning rates disagree")
    a,b=old["args"],current_args
    for key in set(a)|set(b):
        if key in _RUNTIME_ARGS or key.startswith("migration_"):
            continue
        if a.get(key)!=b.get(key):
            raise ValueError(f"migration scientific argument differs: {key}")
    oldsha=old["sha"]
    for key in set(oldsha)|set(current_shas):
        if key in _PATH_SHAS or key=="source_sha256":
            continue
        if oldsha.get(key)!=current_shas.get(key):
            raise ValueError(f"migration provenance differs: {key}")
    for key in set(oldsha["source_sha256"])|set(current_shas["source_sha256"]):
        if key not in _SOURCE_CHANGES and oldsha["source_sha256"].get(key)!=current_shas["source_sha256"].get(key):
            raise ValueError(f"migration scientific source differs: {key}")
    for key in ("train_manifest_sha256", "val_manifest_sha256", "parent_file_sha256", "val_split_manifest_sha256"):
        if not oldsha.get(key) or oldsha[key]!=current_shas.get(key):
            raise ValueError(f"migration requires identical verified {key}")

def validate_best(old, best):
    selected=old.get("rmse_best")
    if not selected or not math.isfinite(selected.get("score",float("nan"))):
        raise ValueError("missing finite selected best")
    if (best.get("epoch"),best.get("step"),best.get("rmse_best"),best.get("sha")) != (selected["epoch"],selected["step"],selected,old["sha"]):
        raise ValueError("source best disagrees with committed last")
    if not any(row.get("epoch")==selected["epoch"] and row.get("step")==selected["step"] and row.get("RMSE_LC")==selected["score"] for row in old.get("validation_history",[])):
        raise ValueError("selected best absent from validation history")

def reconcile(out, last, ck):
    from train.c1_checkpoint import copy_atomic, read
    best=ck["rmse_best"]
    if best:
        target=out/"best_val.pt"
        migration=ck.get("lineage",{}).get("topology_migration",{})
        from train.efficiency_continuation import inherited_best_matches
        efficiency_present = target.exists() and inherited_best_matches(ck, read(target), target)
        inherited_present = efficiency_present or target.exists() and best == migration.get("inherited_best") and digest(target) == migration.get("best_source_sha256")
        if best["epoch"]==ck["epoch"] and not inherited_present:
            copy_atomic(last,target)
        saved=read(target)
        if (saved["epoch"],saved["step"],saved["rmse_best"])!=(best["epoch"],best["step"],best):
            raise ValueError("best weights/history mismatch")
        if saved["sha"] != ck["sha"]:
            migration=ck.get("lineage",{}).get("topology_migration",{})
            if not efficiency_present and (best!=migration.get("inherited_best") or digest(target)!=migration.get("best_source_sha256")):
                raise ValueError("unverified inherited best provenance")
    if ck["epoch"] and ck["epoch"]%20==0:
        copy_atomic(last,out/f"epoch_{ck['epoch']:03d}.pt")

def commit(out, ck):
    import os, torch
    from train.c1_checkpoint import copy_atomic, read
    last=out/"last.pt";staged=out/"last.staging"
    with staged.open("wb") as f:
        torch.save(ck,f);f.flush();os.fsync(f.fileno())
    check=read(staged)
    if any(check[k]!=ck[k] for k in ("epoch","step","sha","rmse_best")):
        raise ValueError("staged checkpoint metadata mismatch")
    if last.exists():copy_atomic(last,out/"last_previous.pt")
    staged.replace(last);reconcile(out,last,ck)
