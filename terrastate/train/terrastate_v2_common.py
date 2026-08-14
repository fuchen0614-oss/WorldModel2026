"""Shared, dependency-light helpers for the TerraState-V2 (doc 88) single training line.

NEW FILE — does NOT modify any existing/stable module. Kept import-light on purpose
(only torch/std-lib at module top level, NO xarray/dataset imports) so the trainer's
pure helpers stay importable without a data stack — same discipline as the b4/exclusive
trainers.

Provides:
  * collate_with_ids / to_device_with_ids — like train.train_plan_b_contextformer.collate
    but ALSO carries the per-cube "filepath"/"cubename" lists (the stock collate DROPS
    them). The trainer needs these to look up frozen future-state targets by relative path.
  * relpath_of — stable, cross-server cube identity (doc 87 relative-path philosophy).
  * state_sha / module_pair_sha256 / canonical_json_sha256 — provenance / weight SHAs.
  * capture_rng_state / restore_rng_state — exact resume of python/numpy/torch/cuda RNG.
  * seed_everything / seed_worker / dist helpers — mirror the b4 trainers verbatim.

full24 field order is aggregation-major: [8 means | 8 mins | 8 maxes] (see
data/greenearthnet_contextformer_dataset.py and data/earthnet_conditioning.py).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path
from typing import Iterable, List

import torch
import torch.distributed as dist

# --- full24 canonical layout (aggregation-major) ----------------------------------
EOBS_VARS = ("fg", "hu", "pp", "qq", "rr", "tg", "tn", "tx")
EOBS_AGG = ("mean", "min", "max")
FULL24_FIELD_ORDER: List[str] = [f"{agg}_{v}" for agg in EOBS_AGG for v in EOBS_VARS]  # 24


# --- distributed / logging (identical idiom to train_plan_b_b4_exclusive) ----------
def is_dist() -> bool:
    return dist.is_available() and dist.is_initialized()


def rank0() -> bool:
    return (not is_dist()) or dist.get_rank() == 0


def local_rank() -> int:
    return int(os.environ.get("LOCAL_RANK", 0))


def world_size() -> int:
    return int(os.environ.get("WORLD_SIZE", 1))


def log(msg: str) -> None:
    if rank0():
        import time
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --- seeding (mirror train_plan_b_b4_exclusive._seed_everything / _seed_worker) -----
def seed_everything(seed: int) -> None:
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def seed_worker(worker_id: int) -> None:
    import numpy as np
    s = torch.initial_seed() % (2 ** 32)
    np.random.seed(s)
    random.seed(s)


# --- collate that PRESERVES per-cube ids (stock collate drops filepath/cubename) ----
def collate_with_ids(samples: list) -> dict:
    """Same tensor layout as train.train_plan_b_contextformer.collate, PLUS the
    per-cube "filepath"/"cubename" string lists so future-state targets can be looked
    up by relative path. Order of the id lists matches the batch (cube-major) order."""
    return {
        "dynamic": [
            torch.stack([s["dynamic"][0] for s in samples]),
            torch.stack([s["dynamic"][1] for s in samples]),
        ],
        "dynamic_mask": [torch.stack([s["dynamic_mask"][0] for s in samples])],
        "static": [torch.stack([s["static"][0] for s in samples])],
        "landcover": torch.stack([s["landcover"] for s in samples]),
        "filepath": [str(s["filepath"]) for s in samples],
        "cubename": [str(s["cubename"]) for s in samples],
    }


def to_device_with_ids(batch: dict, dev) -> dict:
    """Move tensors to device; keep the "filepath"/"cubename" string lists as-is."""
    out = {
        "dynamic": [batch["dynamic"][0].to(dev), batch["dynamic"][1].to(dev)],
        "dynamic_mask": [batch["dynamic_mask"][0].to(dev)],
        "static": [batch["static"][0].to(dev)],
        "landcover": batch["landcover"].to(dev),
    }
    if "filepath" in batch:
        out["filepath"] = list(batch["filepath"])
    if "cubename" in batch:
        out["cubename"] = list(batch["cubename"])
    return out


# --- stable cube identity ----------------------------------------------------------
def relpath_of(filepath: str, root) -> str:
    """Cube identity relative to the split root (e.g. 'MAM22/minicube_xxx.nc'). Falls
    back to basename if `filepath` is not under `root`. Symlinks are NOT resolved so the
    key equals the on-disk relative layout the loader iterated (cross-server portable)."""
    if root is None:
        return os.path.basename(str(filepath))
    try:
        rp = os.path.relpath(str(filepath), str(root))
    except ValueError:
        return os.path.basename(str(filepath))
    if rp.startswith(".."):
        return os.path.basename(str(filepath))
    return rp


def data_manifest_sha256(filepaths: Iterable[str], root) -> str:
    """Data fingerprint = SHA256 over sorted (relpath, size_bytes) pairs (doc 87 §5.5).
    Does NOT hash cube contents (too slow); size+relpath is the frozen fingerprint."""
    h = hashlib.sha256()
    rows = []
    for fp in filepaths:
        relp = relpath_of(fp, root)
        try:
            sz = os.path.getsize(fp)
        except OSError:
            sz = -1
        rows.append((relp, sz))
    for relp, sz in sorted(rows):
        h.update(relp.encode()); h.update(str(sz).encode())
    return h.hexdigest()


# --- SHAs (weights + config) -------------------------------------------------------
def state_sha(sd: dict) -> str:
    """SHA256 over a state_dict's sorted (key, tensor-bytes). Same helper the exclusive
    trainer uses for the teacher/student weight-identity assertion."""
    h = hashlib.sha256()
    for k in sorted(sd):
        v = sd[k]
        h.update(k.encode())
        h.update(v.detach().cpu().numpy().tobytes())
    return h.hexdigest()


def module_pair_sha256(q_module, projector_module) -> str:
    """Frozen (q, projector) identity — the future-state target encoder fingerprint.
    Trainer's INITIAL student.q/projector must produce the same SHA as the cache's."""
    sd = {}
    for k, v in q_module.state_dict().items():
        sd["q." + k] = v
    for k, v in projector_module.state_dict().items():
        sd["projector." + k] = v
    return state_sha(sd)


def canonical_json_sha256(payload) -> str:
    """Stable JSON digest (sort_keys, tight separators) — the config SHA."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


# --- RNG capture / restore (exact resume; doc 88 §E checkpoint) --------------------
def capture_rng_state() -> dict:
    import numpy as np
    st = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        st["cuda"] = torch.cuda.get_rng_state_all()
    return st


def restore_rng_state(st: dict) -> None:
    import numpy as np
    if st is None:
        return
    random.setstate(st["python"])
    np.random.set_state(st["numpy"])
    torch.set_rng_state(_as_byte_tensor(st["torch"]))
    if torch.cuda.is_available() and st.get("cuda") is not None:
        torch.cuda.set_rng_state_all([_as_byte_tensor(x) for x in st["cuda"]])


def _as_byte_tensor(x):
    # torch.save round-trips ByteTensors fine; guard against numpy/list drift.
    if isinstance(x, torch.Tensor):
        return x.to(torch.uint8).cpu()
    return torch.as_tensor(x, dtype=torch.uint8)


def atomic_torch_save(payload, path) -> None:
    """tmpfile + fsync + os.replace atomic write (mirrors stage2_provenance pattern)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        torch.save(payload, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def rss_bytes() -> int:
    """Current resident-set size (bytes) of this process, for the cache memory guard."""
    try:
        with open("/proc/self/statm") as f:
            resident_pages = int(f.read().split()[1])
        return resident_pages * os.sysconf("SC_PAGE_SIZE")
    except Exception:
        try:
            import resource
            return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
        except Exception:
            return -1
