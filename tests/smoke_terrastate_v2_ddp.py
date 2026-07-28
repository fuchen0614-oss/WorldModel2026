#!/usr/bin/env python
"""Real 2-process DDP smoke for the TerraState-V2 trainer (CPU / gloo, tiny SYNTHETIC data).

Verifies the multi-process concerns the single-process smoke cannot:
  * no collective deadlock through the FULL run incl. checkpoint_last save;
  * no-FS configuration is identical on every rank and effective lambda_s stays zero;
  * both ranks' updated model params are IDENTICAL;
  * boundary80 + checkpoint_last saved before stage3; clean synchronized exit;
  * exact resume runs >=1 further update.

Dual-mode single file:
  * DRIVER (no RANK in env): builds a random student-init + tiny synthetic future-state
    caches (single process), then subprocess-launches `torchrun --nproc_per_node=2` of ITSELF
    in WORKER mode, then reads the per-rank q-consistency files and asserts, then does a
    resume torchrun.
  * WORKER (RANK set by torchrun): builds a synthetic-dataset factory and calls run_training,
    then writes qconsist_rank{r}.json.

Run:  CUDA_VISIBLE_DEVICES="" <WorldModel-python> tests/smoke_terrastate_v2_ddp.py --data-root runs/smoke_v2
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import torch
from torch.utils.data import Dataset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams
from models.terrastate_v2 import TerraStateV2, warm_start_terrastate_v2
from train.terrastate_future_state_cache import FrozenFutureStateEncoder, build_cache
from train.terrastate_v2_common import atomic_torch_save
from train.train_terrastate_v2 import build_argparser, run_training

SYNTH_H = 32
N_TRAIN, N_VAL = 4, 2       # val divisible by world=2 -> exact single==multi val


class SyntheticCubeDataset(Dataset):
    """Deterministic in-memory cubes with the exact GreenEarthNet dict schema (incl. the
    filepath/cubename ids collate_with_ids needs). No xarray / no disk."""

    def __init__(self, n, root, H=SYNTH_H, W=SYNTH_H, T=30, seed=0):
        self.filepaths = [f"{root}/synth_{i}.nc" for i in range(n)]
        self.root, self.H, self.W, self.T, self.seed = root, H, W, T, seed

    def __len__(self):
        return len(self.filepaths)

    def __getitem__(self, i):
        g = torch.Generator().manual_seed(self.seed * 100003 + i)
        dyn = torch.rand(self.T, 5, self.H, self.W, generator=g)                 # sen2 in [0,1]
        wx = torch.randn(self.T, 24, generator=g)                               # full24 (normalized)
        # sparse clouds (~3% pixels) so the CF-consistent fully-clear 4x4 rule still yields
        # a healthy fraction of valid target patches (dense 50% clouds -> ~0 fully-clear).
        mask = (torch.rand(self.T, 1, self.H, self.W, generator=g) < 0.03).float() * 4.0
        static = torch.randn(5, self.H, self.W, generator=g)
        lc = torch.randint(0, 50, (1, self.H, self.W), generator=g).float()     # landcover incl [10,40]
        return {"dynamic": [dyn, wx], "dynamic_mask": [mask], "static": [static],
                "static_mask": [], "landcover": lc,
                "filepath": self.filepaths[i], "cubename": f"synth_{i}"}


def _factory(split, d):
    n = N_TRAIN if split == "train" else N_VAL
    return SyntheticCubeDataset(n, d, seed=7 if split == "train" else 11)


# ----------------------------------------------------------------------- WORKER
def worker():
    argv = [a for a in sys.argv[1:] if a != "--worker"]
    args = build_argparser().parse_args(argv)
    res = run_training(args, dataset_factory=_factory)
    lr = int(os.environ.get("LOCAL_RANK", 0))
    outp = os.environ["QCONSIST_OUT"].format(rank=lr)
    json.dump({"rank": lr, "q_last_block_sha": res["q_last_block_sha"],
               "q_grad_seen_stage3": res["q_grad_seen_stage3"], "n_trainable_q": res["n_trainable_q"],
               "step": res["step"], "final_stage": res["final_stage"],
               "model_sha": res["model_sha"], "future_state_scale": res["future_state_scale"],
               "stop_after_step": res["stop_after_step"], "global_batch": res["global_batch"],
               "accum": res["accum"],
               "effective_lambdas": [r["effective_lambda_state"] for r in res["loss_log"]]},
              open(outp, "w"))


# ----------------------------------------------------------------------- DRIVER
def _torchrun(worker_args, out_dir, extra_env=None):
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "TOKENIZERS_PARALLELISM": "false",
           "OMP_NUM_THREADS": "1", "QCONSIST_OUT": str(Path(out_dir) / "qconsist_rank{rank}.json")}
    if extra_env:
        env.update(extra_env)
    cmd = [sys.executable, "-m", "torch.distributed.run", "--standalone",
           "--nproc_per_node=2", str(Path(__file__).resolve()), "--worker"] + worker_args
    print("+ torchrun:", " ".join(cmd[3:]), flush=True)
    subprocess.run(cmd, env=env, check=True)


def driver(data_root):
    root = Path(data_root) / "ddp"
    for sub in ("cache", "run", "resume"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    train_root, val_root = "synthetic/train", "synthetic/val"           # id-only strings (no disk)
    cache_dir = root / "cache"

    # 1) random student-init + frozen target encoder + synthetic caches (single process)
    hp = contextformer6m_hparams(pvt_pretrained=False)
    torch.manual_seed(123)
    model = TerraStateV2(hp, contract_cfg={"state_dim": 256, "freeze_b0": True})
    init_path = cache_dir / "student_init.pt"
    atomic_torch_save({"b4_state_dict": model.state_dict(), "contract_cfg": model.config(),
                       "arch": model.ARCH}, init_path)
    warm_start_terrastate_v2(model, torch.load(init_path, map_location="cpu", weights_only=False))
    enc = FrozenFutureStateEncoder(model.q, model.projector, model.context_len, model.target_len,
                                   model.patch_size, lc_min=model.lc_min, lc_max=model.lc_max)
    for split, rootstr, n in (("train", train_root, N_TRAIN), ("val", val_root, N_VAL)):
        ds = SyntheticCubeDataset(n, rootstr, seed=7 if split == "train" else 11)
        blob = build_cache(ds, enc, torch.device("cpu"), root=rootstr, split=split,
                           student_init_path=str(init_path), student_init_sha256="ddp-smoke", per_gpu_batch=1)
        atomic_torch_save(blob, cache_dir / f"{split}_future_state_cache.pt")
        print(f"[driver] {split} synthetic cache: {blob['provenance']['n_cubes']} cubes "
              f"P={blob['provenance']['patches_per_cube']} n_nan={blob['sanity']['n_nan']}", flush=True)

    train_cache = str(cache_dir / "train_future_state_cache.pt")
    val_cache = str(cache_dir / "val_future_state_cache.pt")

    def base(od, per_gpu=1, gb=2, max_steps=5, resume=""):
        a = ["--train-dir", train_root, "--val-dir", val_root,
             "--train-cache", train_cache, "--val-cache", val_cache,
             "--student-init", str(init_path), "--teacher-b4", str(init_path),
             "--output-dir", od, "--device", "cpu", "--per-gpu-batch", str(per_gpu),
             "--global-batch", str(gb), "--num-workers", "0", "--max-steps", str(max_steps),
             "--future-state-scale", "0", "--stop-after-step", "4",
             "--branch-lr", "3e-5", "--q-lr-scale", "0.033", "--lr-warmup-steps", "1",
             "--val-interval", "1000", "--ckpt-interval", "3", "--log-interval", "1",
             "--unfreeze-q-prefixes", "core.blocks.2.", "--deterministic"]
        if resume:
            a += ["--resume", resume]
        return a

    # 2) no-FS 2-process DDP run: total schedule 5, exact 80% boundary/stop at step 4.
    run_out = str(root / "run")
    _torchrun(base(run_out, max_steps=5), run_out)

    # 3) read per-rank q-consistency + assert
    q0 = json.load(open(Path(run_out) / "qconsist_rank0.json"))
    q1 = json.load(open(Path(run_out) / "qconsist_rank1.json"))
    results = []

    def ck(name, ok, detail=""):
        results.append((name, bool(ok), detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""), flush=True)

    ck("D1: both ranks stop at boundary in stage 2", q0["final_stage"] == 2 and q1["final_stage"] == 2,
       f"stages={q0['final_stage']},{q1['final_stage']}")
    ck("D2: no stage-3 q gradient/unfreeze on either rank",
       not q0["q_grad_seen_stage3"] and not q1["q_grad_seen_stage3"]
       and q0["n_trainable_q"] == q1["n_trainable_q"] == 0,
       f"n_trainable_q={q0['n_trainable_q']},{q1['n_trainable_q']}")
    ck("D3: both ranks' updated full model params IDENTICAL",
       q0["model_sha"] == q1["model_sha"] and q0["model_sha"] != "",
       f"sha={q0['model_sha'][:16]}")
    ck("D4: boundary80 + checkpoint_last saved (no deadlock, clean exit)",
       (Path(run_out) / "checkpoint_boundary80.pt").exists() and (Path(run_out) / "checkpoint_last.pt").exists())
    ck("D5: both ranks use scale=0, stop=4, unchanged global batch/accum",
       q0["step"] == q1["step"] == 4
       and q0["future_state_scale"] == q1["future_state_scale"] == 0.0
       and q0["stop_after_step"] == q1["stop_after_step"] == 4
       and q0["global_batch"] == q1["global_batch"] == 2
       and q0["accum"] == q1["accum"] == 1
       and q0["effective_lambdas"] and all(x == 0.0 for x in q0["effective_lambdas"]),
       f"steps={q0['step']},{q1['step']}")

    # 4) exact resume: continue from step-3 checkpoint, run >=1 more update, clean exit
    step3 = Path(run_out) / "checkpoint_step3.pt"
    resume_out = str(root / "resume")
    _torchrun(base(resume_out, max_steps=5, resume=str(step3)), resume_out)
    r0 = json.load(open(Path(resume_out) / "qconsist_rank0.json"))
    r1 = json.load(open(Path(resume_out) / "qconsist_rank1.json"))
    ck("D6: DDP resume ran >=1 further update to completion",
       r0["step"] == 4 and r1["step"] == 4, f"resumed steps={r0['step']},{r1['step']}")
    ck("D7: resumed ranks identical, scale=0, and still stage2",
       r0["model_sha"] == r1["model_sha"] and r0["final_stage"] == r1["final_stage"] == 2
       and r0["future_state_scale"] == r1["future_state_scale"] == 0.0,
       f"resume sha={r0['model_sha'][:16]}")

    npass = sum(1 for _, ok, _ in results if ok)
    print(f"\n==== DDP SMOKE {npass}/{len(results)} PASSED ====", flush=True)
    sys.exit(0 if npass == len(results) else 1)


def main():
    if os.environ.get("RANK") is not None or "--worker" in sys.argv:
        worker()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="runs/smoke_v2")
    driver(ap.parse_args().data_root)


if __name__ == "__main__":
    main()
