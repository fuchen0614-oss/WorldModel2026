"""Epoch transactions. last.pt is authoritative, derived files are repairable."""
from pathlib import Path
import shutil

import torch


def read(path):
    return torch.load(path, map_location="cpu", weights_only=False)


def copy_atomic(src, dst):
    temporary = dst.with_suffix(".staging")
    shutil.copyfile(src, temporary)
    temporary.replace(dst)


def reconcile(out, last, ck):
    epoch = ck["epoch"]
    best = ck["rmse_best"]
    if best:
        path = out / "best_val.pt"
        if best["epoch"] == epoch:
            copy_atomic(last, path)
        saved = read(path)
        if (saved["epoch"], saved["step"], saved["rmse_best"], saved["sha"]) != (
            best["epoch"], best["step"], best, ck["sha"]
        ):
            from train.efficiency_continuation import inherited_best_matches
            if not inherited_best_matches(ck, saved, path):
                raise ValueError("best weights and last history disagree")
    if epoch and epoch % 20 == 0:
        path = out / f"epoch_{epoch:03d}.pt"
        copy_atomic(last, path)
        saved = read(path)
        if (saved["epoch"], saved["step"], saved["sha"]) != (epoch, ck["step"], ck["sha"]):
            raise ValueError("snapshot metadata mismatch")


def commit(out, ck):
    last = out / "last.pt"
    staged = out / "last.staging"
    with staged.open("wb") as f:
        torch.save(ck, f)
        f.flush()
        import os
        os.fsync(f.fileno())
    loaded = read(staged)
    if (loaded["epoch"], loaded["step"], loaded["sha"], loaded["rmse_best"]) != (
        ck["epoch"], ck["step"], ck["sha"], ck["rmse_best"]
    ):
        raise ValueError("staged checkpoint metadata mismatch")
    del loaded
    if last.exists():
        copy_atomic(last, out / "last_previous.pt")
    staged.replace(last)
    reconcile(out, last, ck)

