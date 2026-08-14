# TerraState-V2 — Runbook (doc 88 唯一训练主线)

> Isolated worktree `WorldModel2026-planb-v2train`, branch `plan-b-v2-train`.
> This runbook is the operator reference for the doc-88 UNIQUE training line: build the
> frozen future-state cache, run the single 3-stage training, resume, and export
> checkpoints. It does **not** touch the B-session evaluator/protocol files, and it does
> **not** auto-start a full run.

## 0. What this line is

One inference model (`TerraStateV2`), one loss, one run, three stages.

```
history ─► q ─► z_t ─────────────────────────────►┐   (context-only prior b_h; reads NO future weather)
full24 + static geography + h ─► shared T ─► z_{t+h}│─► O ─► y = b_h + alpha·O(z_{t+h}),  alpha = 1 (fixed buffer)
```

Loss (fixed weights; exactly one KD):
`L = 1.0·L_GT + 0.5·L_KD + λ_s·L_future_state`,  `L_future_state = 1 − cos(LN z_{t+20}, LN z*_{t+20})`.

λ_s schedule: `0→0.02` linear over 0–20%, `0.02` over 20–80%, `0.01` over 80–100%.
Stages: **1** [0,20%) q frozen · **2** [20%,80%) q frozen + forced 80% boundary ckpt ·
**3** [80%,100%] unfreeze only q's last transformer block (`core.blocks.2.`) at q_lr = 0.033×branch_lr.

Status: **single-process smoke 15/15 PASS · 2-process DDP smoke 7/7 PASS** (CPU/gloo).

## 0.1 FROZEN official weight chain (doc 88 §4.1 — NO free choice)

Exactly one initialisation, enforced fail-closed in code:

| Role | Source (arch) | Loader rule |
|---|---|---|
| **student init** | the **exclusive MAIN-last** checkpoint ONLY — `arch: ObsWorldB4Exclusive` (the accuracy-first rescue MAIN run's `checkpoint_last.pt`) | `--student-init`; load requires arch∈{ObsWorldB4Exclusive,TerraStateV2} **and** missing==[]∧unexpected==[]. A **raw Phase-I B4 is rejected** (it lacks the `alpha` buffer). |
| **KD teacher** | the **original strong Phase-I B4** `checkpoint_best` → `checkpoints/plan_b_b4a/checkpoint_best.pt` (server repo; R²≈0.512) | `--teacher-b4`; only its `q.*` is loaded into a frozen encoder, requires missing==[]∧unexpected==[]; teacher SHA asserted unchanged across the run. |
| **future-target encoder** | a frozen COPY of the **student's init-time q+projector** | built inside the cache builder from `--student-init`; its `q/projector` SHA must equal the trainer's initial student SHA (verified at load). |

> **Fail-closed provenance (resolved on the 8×H200 server, NOT on this box):** the exclusive
> MAIN-last **exact path** and both checkpoints' **SHA256** could NOT be parsed from evaluation
> artifacts present on this audit box (`/csy-mix02` is not mounted here; no `plan_b_b4a`,
> no exclusive checkpoint, no exclusive eval JSON locally). Per the fail-closed rule these are
> **NOT guessed**. Resolve + record them on the server before the formal run:
> ```bash
> # on the server (repo /csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb):
> TEACHER=checkpoints/plan_b_b4a/checkpoint_best.pt            # Phase-I B4 (settled runbook)
> STUDENT=<exclusive MAIN rescue run>/checkpoint_last.pt       # locate the MAIN-last dir on the server
> sha256sum "$TEACHER" "$STUDENT"                              # record both SHAs into the run log
> python -c "import torch;print('teacher arch',torch.load('$TEACHER',map_location=\"cpu\",weights_only=False).get('arch'))"
> python -c "import torch;print('student arch',torch.load('$STUDENT',map_location=\"cpu\",weights_only=False).get('arch'))"  # must be ObsWorldB4Exclusive
> ```
> The loaders enforce arch + exact-key rules, so a wrong file fails loudly rather than training silently.


## 1. Environment (both servers)

```bash
# This server (WorldModel env has torch 2.12 + xarray):
WM=/mnt/data/users/luzheng/workspace/iclr/czj/WorldModel2026/.conda/envs/WorldModel/bin/python
# 8×H200 server (per ENVIRONMENT.md): conda env `WorldModel`
source scripts/activate_worldmodel.sh          # or: conda activate WorldModel
cd <repo>/WorldModel2026-planb-v2train
```

Files that make up this line (all NEW; nothing existing modified):
- `models/terrastate_v2.py` — model + doc-88 loss + evaluator API + leak asserts
- `train/terrastate_v2_common.py` — id-preserving collate, SHAs, RNG capture/restore
- `train/terrastate_future_state_cache.py` — frozen target encoder + cache build/load
- `scripts/build_future_state_cache.py` — cache CLI
- `train/train_terrastate_v2.py` — 3-stage trainer with exact-resume
- `tests/smoke_terrastate_v2.py` — CPU smoke (13 checks)

## 2. Tiny smoke — THIS server only (CPU; never a full run)

GPUs on this box are in use by others → run on **CPU**.

```bash
# (fixtures already created under runs/smoke_v2/data/{train,val}; symlinks to real cubes)
CUDA_VISIBLE_DEVICES="" TOKENIZERS_PARALLELISM=false \
  $WM tests/smoke_terrastate_v2.py --data-root runs/smoke_v2
```

Standalone tiny cache build (2–4 cubes), if you want just the cache path:

```bash
CUDA_VISIBLE_DEVICES="" $WM scripts/build_future_state_cache.py \
  --student-init runs/smoke_v2/cache/student_init.pt \
  --train-dir runs/smoke_v2/data/train --val-dir runs/smoke_v2/data/val \
  --out-dir runs/smoke_v2/cache --limit 4 --per-gpu-batch 2 --device cpu
```

## 3. FULL cache build — 8×H200 server

Point `--train-dir`/`--val-dir` at the server's real GreenEarthNet splits, and
`--student-init` at the **exclusive MAIN-last** checkpoint (§0.1; NOT a raw Phase-I B4 — the
loader rejects that).

```bash
DATA=/path/to/GreenEarthNet            # server-local; unchanged from B4 runs
STUDENT=<exclusive MAIN-last>/checkpoint_last.pt   # arch ObsWorldB4Exclusive (§0.1)
CACHE=runs/terrastate_v2/cache

$WM scripts/build_future_state_cache.py \
  --student-init "$STUDENT" \
  --train-dir "$DATA/train" --val-dir "$DATA/val_chopped" \
  --out-dir "$CACHE" --per-gpu-batch 8 --num-workers 8 --device cuda \
  --min-coverage 0.02        # fail-closed: STOP if valid-patch coverage < 2% (do NOT relax the mask rule)
# writes: $CACHE/{train,val}_future_state_cache.pt (+ .json sidecars: provenance incl. coverage/mask_sha + sanity)
```

### Cache sanity check (read the sidecars)

```bash
$WM - <<'PY'
import json
for s in ("train","val"):
    p=f"runs/terrastate_v2/cache/{s}_future_state_cache.pt.json"
    d=json.load(open(p)); sv=d["sanity"]; pv=d["provenance"]
    print(s, "n_cubes",pv["n_cubes"],"h",pv["horizon_h"],"n_nan",sv["n_nan"],
          "zero_var_dims",sv["n_zero_var_dims"],"eff_rank",round(sv["effective_rank"],2),
          "movement_cos",round(sv["movement_cos_from_context"],3),
          "q/proj_sha",pv["q_projector_sha256"][:12],"manifest_sha",pv["data_manifest_sha256"][:12])
    assert sv["n_nan"]==0 and sv["n_zero_var_dims"]==0, "cache sanity FAILED"
print("cache sanity OK")
PY
```

## 4. FULL training — 8×H200 DDP (single run; doc-88 defaults)

`--global-batch 64` is held constant by gradient accumulation, so 8×8 = 64 (accum 1).
LR/effective-updates are identical to any other factorisation.

```bash
DATA=/path/to/GreenEarthNet
CACHE=runs/terrastate_v2/cache
OUT=runs/terrastate_v2/run1
STUDENT=<exclusive MAIN-last>/checkpoint_last.pt          # arch ObsWorldB4Exclusive (§0.1)
TEACHER=checkpoints/plan_b_b4a/checkpoint_best.pt          # ORIGINAL strong Phase-I B4 (§0.1)

python -m torch.distributed.run --standalone --nproc_per_node=8 \
  -m train.train_terrastate_v2 \
  --train-dir "$DATA/train" --val-dir "$DATA/val_chopped" \
  --train-cache "$CACHE/train_future_state_cache.pt" \
  --val-cache   "$CACHE/val_future_state_cache.pt" \
  --student-init "$STUDENT" --teacher-b4 "$TEACHER" \
  --output-dir "$OUT" \
  --per-gpu-batch 8 --global-batch 64 --max-epochs 40 \
  --branch-lr 3e-5 --q-lr-scale 0.033 --weight-decay 0.0 --grad-clip 1.0 \
  --lr-warmup-steps 300 --unfreeze-q-prefixes "core.blocks.2." \
  --val-interval 1000 --ckpt-interval 2000 --seed 42
```

Single-GPU equivalent (same global batch via accum=8): `--nproc_per_node=1 --per-gpu-batch 8 --global-batch 64`.

## 5. Interrupt & exact resume

The trainer checkpoints save model/optimizer/scheduler/scaler(disabled)/epoch/step/
micro-position/RNG(all ranks)/stage/q-freeze-set/all SHAs. Resume from any of them:

```bash
python -m torch.distributed.run --standalone --nproc_per_node=8 \
  -m train.train_terrastate_v2 \
  ... (identical args as §4) ... \
  --resume "$OUT/checkpoint_last.pt"
```

Resume asserts arch, `q_projector_init_sha256`, and `total_steps` match (schedule unchanged).

## 6. Watch training state

```bash
tail -f "$OUT/loss_log.jsonl"                       # per-step {step,stage,lambda_state,gt,kd,future_state}
grep '\[val\]'  "$OUT"/*.log 2>/dev/null            # val future_state + gt
grep '\[stage\]\|\[boundary80\]' "$OUT"/*.log 2>/dev/null
ls -la "$OUT"/checkpoint_*.pt
```

## 7. Checkpoint inventory + SHA export

```bash
$WM - "$OUT" <<'PY'
import sys, glob, os, torch, hashlib, json
out=sys.argv[1]; rows=[]
for p in sorted(glob.glob(os.path.join(out,"checkpoint_*.pt"))):
    ck=torch.load(p, map_location="cpu", weights_only=False)
    fsha=hashlib.sha256(open(p,"rb").read()).hexdigest()
    rows.append({"ckpt":os.path.basename(p),"step":ck["step"],"stage":ck["stage"],
                 "lambda_state":ck["lambda_state"],"best_val":ck["best_val"],
                 "alpha":ck["alpha"],"file_sha256":fsha[:16],
                 "teacher_sha":ck["sha"]["teacher_sha256"][:12],
                 "qproj_init_sha":ck["sha"]["q_projector_init_sha256"][:12]})
print(json.dumps(rows, indent=2))
json.dump(rows, open(os.path.join(out,"checkpoint_manifest.json"),"w"), indent=2)
PY
```

## 8. Checkpoint selection (doc 88 §6.3 — post-hoc, NOT in this repo's scope)

Pre-registered candidates: `checkpoint_boundary80.pt` (candidate `stage2_end_boundary80`),
`checkpoint_fsval_best.pt` (candidate `future_state_val_best` — best **non-intervention
future-state validation loss**, explicitly NOT auto-final), `checkpoint_last.pt`
(candidate `last`). Every checkpoint carries a `selection_note` and a `candidate` field.
Selection = **validation Q1 qualifier first**, then min non-intervention future-state val
loss among Q1-passing candidates. Q1–Q4 evaluation uses the B-session evaluator (separate;
do NOT modify from here).

## 9. Multi-process / full-scale hardening notes

- **Val under DDP** is split by `DistributedSampler(shuffle=False, drop_last=False)` and
  aggregated as global masked **sum/count** → identical number on 1 vs N GPUs (no 8×
  redundant full-val passes).
- **Cache loading** uses `torch.load(mmap=True)` so N ranks share ONE page-cached copy of
  the (~12GB) cache in CPU RAM (not GPU). It prints size / mmap-status / RSS. If a cache
  exceeds `--cache-fail-closed-gb` (default 4.0) and mmap is unavailable, the trainer
  **refuses to load** (fail-closed) instead of letting every rank materialise a full copy.
- **Checkpoint saves** are deadlock-safe: every save path (best/boundary80/interval/last)
  is entered by ALL ranks (the RNG all-gather is a collective); only rank0 writes the file.
