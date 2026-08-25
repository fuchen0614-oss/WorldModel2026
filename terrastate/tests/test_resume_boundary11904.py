#!/usr/bin/env python
"""CPU regression suite for the 80%-boundary EXACT-RESUME contract (step 11,904 case).

Scaled-down structural replica of the real situation
---------------------------------------------------
Real run : total_steps=14880, updates/epoch=372, boundary80=11904, parent saved at
           step 11904 with `stage: 2` recorded, micro_in_epoch=372 (== a FULL epoch),
           epoch=31; the original process switched 2->3 immediately AFTER saving.
This test: total_steps=10,    updates/epoch=2,   boundary80=8,     parent saved at
           step 8 with `stage: 2` recorded, micro_in_epoch=2 (== a FULL epoch),
           epoch=3; same save-then-switch ordering.

So `checkpoint_boundary80.pt` here reproduces the exact awkward property of the real
parent: the recorded stage is 2, while the NEXT scheduled update already belongs to
stage 3.

Contract asserted (R1..R11).  R2/R3/R4/R6/R7/R8 FAIL against the pre-fix trainer because
it does `current_stage = int(rk["stage"])`, which (a) runs one extra stage-2 update and
(b) re-fires the 2->3 transition and re-writes a boundary80 checkpoint one step late.
R9/R10/R11 fail because completed-resume no-op, output-dir protection and parent lineage
do not exist yet.

Run (CPU only, no CUDA context, no network):
    CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
    NUMEXPR_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false \
    <WorldModel-python> tests/test_resume_boundary11904.py --data-root runs/resume_regression

Exit 0 iff every check passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch  # noqa: E402
from torch.utils.data import Dataset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from models.terrastate_v2 import TerraStateV2, warm_start_terrastate_v2  # noqa: E402
from train.terrastate_future_state_cache import FrozenFutureStateEncoder, build_cache  # noqa: E402
from train.terrastate_v2_common import atomic_torch_save  # noqa: E402
from train.train_terrastate_v2 import build_argparser, run_training  # noqa: E402

SYNTH_H = 32
N_TRAIN, N_VAL = 4, 2
TOTAL_STEPS = 10          # -> boundary80 = int(0.8*10) = 8
BOUNDARY = 8
PER_GPU, GLOBAL_BATCH = 2, 2      # accum=1
UPDATES_PER_EPOCH = N_TRAIN // PER_GPU     # 2  -> step 8 ends epoch index 3 exactly
UNFREEZE_PREFIX = "core.blocks.2."

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""), flush=True)
    return bool(ok)


class SyntheticCubeDataset(Dataset):
    """Deterministic in-memory cubes with the GreenEarthNet dict schema (incl. the
    filepath/cubename ids collate_with_ids needs).  No xarray, no disk, no network."""

    def __init__(self, n, root, H=SYNTH_H, W=SYNTH_H, T=30, seed=0):
        self.filepaths = [f"{root}/synth_{i}.nc" for i in range(n)]
        self.root, self.H, self.W, self.T, self.seed = root, H, W, T, seed

    def __len__(self):
        return len(self.filepaths)

    def __getitem__(self, i):
        g = torch.Generator().manual_seed(self.seed * 100003 + i)
        dyn = torch.rand(self.T, 5, self.H, self.W, generator=g)
        wx = torch.randn(self.T, 24, generator=g)
        mask = (torch.rand(self.T, 1, self.H, self.W, generator=g) < 0.03).float() * 4.0
        static = torch.randn(5, self.H, self.W, generator=g)
        lc = torch.randint(0, 50, (1, self.H, self.W), generator=g).float()
        return {"dynamic": [dyn, wx], "dynamic_mask": [mask], "static": [static],
                "static_mask": [], "landcover": lc,
                "filepath": self.filepaths[i], "cubename": f"synth_{i}"}


def factory(split, d):
    n = N_TRAIN if split == "train" else N_VAL
    return SyntheticCubeDataset(n, d, seed=7 if split == "train" else 11)


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()
def build_fixture(root: Path):
    """Random student-init + tiny synthetic future-state caches (single process, CPU)."""
    cache_dir = root / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    train_root, val_root = "synthetic/train", "synthetic/val"      # id-only strings
    hp = contextformer6m_hparams(pvt_pretrained=False)
    torch.manual_seed(4242)
    model = TerraStateV2(hp, contract_cfg={"state_dim": 256, "freeze_b0": True})
    init_path = cache_dir / "student_init.pt"
    atomic_torch_save({"b4_state_dict": model.state_dict(), "contract_cfg": model.config(),
                       "arch": model.ARCH}, init_path)
    warm_start_terrastate_v2(model, torch.load(init_path, map_location="cpu", weights_only=False))
    enc = FrozenFutureStateEncoder(model.q, model.projector, model.context_len,
                                   model.target_len, model.patch_size,
                                   lc_min=model.lc_min, lc_max=model.lc_max)
    for split, rootstr, n in (("train", train_root, N_TRAIN), ("val", val_root, N_VAL)):
        ds = SyntheticCubeDataset(n, rootstr, seed=7 if split == "train" else 11)
        blob = build_cache(ds, enc, torch.device("cpu"), root=rootstr, split=split,
                           student_init_path=str(init_path),
                           student_init_sha256="resume-regression", per_gpu_batch=1)
        atomic_torch_save(blob, cache_dir / f"{split}_future_state_cache.pt")
    return {"init_path": str(init_path), "train_root": train_root, "val_root": val_root,
            "train_cache": str(cache_dir / "train_future_state_cache.pt"),
            "val_cache": str(cache_dir / "val_future_state_cache.pt")}


def make_args(fx, out_dir, *, resume="", extra=()):
    argv = [
        "--train-dir", fx["train_root"], "--val-dir", fx["val_root"],
        "--train-cache", fx["train_cache"], "--val-cache", fx["val_cache"],
        "--student-init", fx["init_path"], "--teacher-b4", fx["init_path"],
        "--output-dir", str(out_dir), "--device", "cpu",
        "--per-gpu-batch", str(PER_GPU), "--global-batch", str(GLOBAL_BATCH),
        "--num-workers", "0", "--max-steps", str(TOTAL_STEPS),
        "--branch-lr", "3e-5", "--q-lr-scale", "0.033", "--lr-warmup-steps", "1",
        "--val-interval", "10000", "--ckpt-interval", "10000", "--log-interval", "1",
        "--unfreeze-q-prefixes", UNFREEZE_PREFIX, "--seed", "42", "--deterministic",
    ]
    if resume:
        argv += ["--resume", str(resume)]
    argv += list(extra)
    return build_argparser().parse_args(argv)
def stages_of(loss_log):
    return {r["step"]: r["stage"] for r in loss_log}


def totals_of(loss_log):
    return {r["step"]: r["total"] for r in loss_log}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="runs/resume_regression")
    a = ap.parse_args()
    root = Path(a.data_root)
    root.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(0)

    fx = build_fixture(root)

    # ---------------- reference: uninterrupted 10-update run -------------------------
    ref_dir = root / "ref"
    ref = run_training(make_args(fx, ref_dir), dataset_factory=factory)
    ref_boundary = ref_dir / "checkpoint_boundary80.pt"
    ref_stages, ref_totals = stages_of(ref["loss_log"]), totals_of(ref["loss_log"])

    check("R1: reference run reaches the schedule end with the boundary saved",
          ref["step"] == TOTAL_STEPS and ref["boundary80"] == BOUNDARY
          and ref_boundary.is_file() and ref["final_stage"] == 3
          and ref["q_grad_seen_stage3"],
          f"step={ref['step']} boundary80={ref['boundary80']} stage={ref['final_stage']}")

    pck = torch.load(ref_boundary, map_location="cpu", weights_only=False)
    pck_sha_before = sha256_file(ref_boundary)
    ref_last_sha_before = sha256_file(ref_dir / "checkpoint_last.pt")
    check("R2: parent checkpoint reproduces the real 11,904 shape "
          "(step==boundary, stage RECORDED as 2, micro==full epoch, q fully frozen)",
          int(pck["step"]) == BOUNDARY and int(pck["stage"]) == 2
          and int(pck["micro_in_epoch"]) == UPDATES_PER_EPOCH
          and int(pck["epoch"]) == BOUNDARY // UPDATES_PER_EPOCH - 1
          and pck["q_freeze"]["trainable_q"] == []
          and int(pck["total_steps"]) == TOTAL_STEPS,
          f"step={pck['step']} stage={pck['stage']} epoch={pck['epoch']} "
          f"micro={pck['micro_in_epoch']} trainable_q={len(pck['q_freeze']['trainable_q'])}")

    # the reference proves the update AFTER the boundary belongs to stage 3
    check("R3: in the reference, update boundary+1 already runs in stage 3",
          ref_stages.get(BOUNDARY + 1) == 3,
          f"stage(step {BOUNDARY + 1})={ref_stages.get(BOUNDARY + 1)} "
          f"all={ {k: v for k, v in sorted(ref_stages.items()) if k >= BOUNDARY} }")
    # ---------------- the exact-resume under test ------------------------------------
    res_dir = root / "resume"
    res = run_training(make_args(fx, res_dir, resume=ref_boundary), dataset_factory=factory)
    res_stages, res_totals = stages_of(res["loss_log"]), totals_of(res["loss_log"])

    check("R4: resumed run executes EXACTLY the remaining updates (no extra update)",
          res["step"] == TOTAL_STEPS and sorted(res_totals) == list(range(BOUNDARY + 1, TOTAL_STEPS + 1)),
          f"step={res['step']} logged_steps={sorted(res_totals)} "
          f"expected={list(range(BOUNDARY + 1, TOTAL_STEPS + 1))}")

    check("R5: FIRST post-resume update runs in stage 3 (no extra stage-2 update)",
          res_stages.get(BOUNDARY + 1) == 3,
          f"stage(step {BOUNDARY + 1})={res_stages.get(BOUNDARY + 1)} all={sorted(res_stages.items())}")

    check("R6: resumed run does NOT re-write a boundary80 checkpoint",
          not (res_dir / "checkpoint_boundary80.pt").exists(),
          f"exists={(res_dir / 'checkpoint_boundary80.pt').exists()}")

    check("R7: exactly the unfreeze-prefix q tensors are trainable and get gradient",
          res["q_grad_seen_stage3"] and res["n_trainable_q"] == ref["n_trainable_q"]
          and res["n_trainable_q"] > 0,
          f"q_grad_seen={res['q_grad_seen_stage3']} n_trainable_q={res['n_trainable_q']} "
          f"(ref {ref['n_trainable_q']})")

    tol_rows = []
    aligned = bool(res_totals)
    for s, v in sorted(res_totals.items()):
        rv = ref_totals.get(s)
        ok = rv is not None and abs(rv - v) <= 1e-4 * (abs(rv) + 1e-3)
        aligned = aligned and ok
        tol_rows.append(f"{s}:{'' if ok else '!'}{v:.8f}vs{(rv if rv is not None else float('nan')):.8f}")
    check("R8: resumed loss trajectory matches the uninterrupted reference",
          aligned, " ".join(tol_rows))

    check("R8b: resumed FINAL weights match the uninterrupted reference bit-exactly",
          res["model_sha"] == ref["model_sha"],
          f"resume={res['model_sha'][:16]} ref={ref['model_sha'][:16]}")
    # ---------------- completed-resume no-op -----------------------------------------
    # Resuming from a checkpoint that is ALREADY at total_steps must do zero updates and
    # must not write anything (pre-fix: the step>=total_steps test only runs AFTER an
    # update, so one extra update is executed past the schedule).
    done_ck = ref_dir / "checkpoint_last.pt"
    noop_dir = root / "noop"
    noop = run_training(make_args(fx, noop_dir, resume=done_ck), dataset_factory=factory)
    noop_ckpts = sorted(p.name for p in noop_dir.glob("checkpoint*.pt")) if noop_dir.exists() else []
    check("R9: resuming a COMPLETED checkpoint is a no-op (0 updates, no checkpoint written)",
          noop["step"] == TOTAL_STEPS and not noop["loss_log"] and not noop_ckpts,
          f"step={noop['step']} n_logged={len(noop['loss_log'])} wrote={noop_ckpts}")

    # ---------------- output-dir overwrite protection --------------------------------
    # Pointing a run at a directory that already holds checkpoints must FAIL CLOSED.
    protected = False
    detail = ""
    try:
        run_training(make_args(fx, ref_dir, resume=ref_boundary), dataset_factory=factory)
        detail = "no exception raised — historical outputs would be overwritten"
    except (OSError, RuntimeError, AssertionError, SystemExit) as e:   # FileExistsError is an OSError
        protected = "output" in str(e).lower() or "exist" in str(e).lower()
        detail = f"{type(e).__name__}: {str(e)[:120]}"
    check("R10: refuses to write into a directory that already contains checkpoints",
          protected, detail)
    # the pre-existing outputs must be byte-identical regardless of the rejected launch
    b_now, l_now = sha256_file(ref_boundary), sha256_file(ref_dir / "checkpoint_last.pt")
    check("R10b: pre-existing checkpoints in that directory are byte-identical afterwards",
          b_now == pck_sha_before and l_now == ref_last_sha_before,
          f"boundary80_stable={b_now == pck_sha_before} last_stable={l_now == ref_last_sha_before}")

    # ---------------- parent/child lineage ------------------------------------------
    child = torch.load(res_dir / "checkpoint_last.pt", map_location="cpu", weights_only=False)
    lin = child.get("lineage") or {}
    check("R11: child checkpoints record parent path + sha256 + step (provenance chain)",
          lin.get("parent_step") == BOUNDARY
          and lin.get("parent_file_sha256") == pck_sha_before
          and str(lin.get("parent_path", "")).endswith("checkpoint_boundary80.pt")
          and lin.get("resumed") is True,
          f"lineage={json.dumps(lin, default=str)[:220]}")

    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n==== RESUME-BOUNDARY REGRESSION {n_pass}/{len(RESULTS)} PASSED ====", flush=True)
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
