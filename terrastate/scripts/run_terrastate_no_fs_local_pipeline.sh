#!/usr/bin/env bash
#
# One-shot node-local pipeline for the single registered TerraState ablation:
#   stage immutable inputs to /tmp -> verify -> train to boundary80 -> verify -> hash.
#
# Formal Q1/Q2 evaluation is intentionally not run here: the TerraState-V2 runbook
# assigns it to the separate frozen B-session evaluator, which is not part of this
# worktree. This script never runs Q3.

set -eo pipefail

ACTION=${1:-run}

V2=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb-v2train
MAIN=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb
SOURCE_DATA=/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet
SOURCE_CACHE=$V2/runs/terrastate_v2/cache

LOCAL_STAGE=/tmp/zjliu17_mix_stage_v2
LOCAL_TRAIN=$LOCAL_STAGE/train
LOCAL_VAL=$LOCAL_STAGE/val_chopped
LOCAL_CACHE=$LOCAL_STAGE/cache
LOCAL_TRAIN_CACHE=$LOCAL_CACHE/train_future_state_cache.pt
LOCAL_VAL_CACHE=$LOCAL_CACHE/val_future_state_cache.pt

SOURCE_TRAIN_CACHE=$SOURCE_CACHE/train_future_state_cache.pt
SOURCE_VAL_CACHE=$SOURCE_CACHE/val_future_state_cache.pt
STUDENT=$MAIN/runs/planb_excl_tournament/stageA_rescue_20260726_173149/MAIN/checkpoint_last.pt
TEACHER=$MAIN/checkpoints/plan_b_b4a/checkpoint_best.pt
FULL_CKPT=$V2/runs/terrastate_v2/run1/checkpoint_boundary80.pt

OUT=$V2/runs/terrastate_v2_ablation/no_future_state_anchor_seed42
TRAIN_LOG=$OUT/train.log
TRAIN_PID_FILE=$OUT/train.pid
PIPELINE_LOG=/tmp/terrastate_no_fs_local_pipeline.log
PIPELINE_PID_FILE=/tmp/terrastate_no_fs_local_pipeline.pid
STAGE_MARKER=$LOCAL_STAGE/.terrastate_local_stage_verified

CONDA_SH=/csy-opt/cog8/zjliu17/miniconda3/etc/profile.d/conda.sh
BASE_IMPLEMENTATION_COMMIT=ea14a381b7f86fc0fbed2150e693ddaf69eb1270
FULL_CKPT_SHA256=644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

die() {
  log "PIPELINE_FAILED: $*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || die "missing file: $1"
}

require_dir() {
  [[ -d "$1" ]] || die "missing directory: $1"
}

status() {
  echo "pipeline_log=$PIPELINE_LOG"
  echo "local_stage=$LOCAL_STAGE"
  echo "output=$OUT"
  if [[ -f "$PIPELINE_PID_FILE" ]]; then
    pipeline_pid=$(cat "$PIPELINE_PID_FILE")
    if kill -0 "$pipeline_pid" 2>/dev/null; then
      echo "PIPELINE_RUNNING pid=$pipeline_pid"
      ps -fp "$pipeline_pid" || true
    else
      echo "PIPELINE_NOT_RUNNING pid=$pipeline_pid"
    fi
  else
    echo "NO_PIPELINE_PID"
  fi
  if [[ -d "$LOCAL_STAGE" ]]; then
    du -sh "$LOCAL_STAGE" 2>/dev/null || true
    printf 'local train nc='
    find "$LOCAL_TRAIN" -type f -name '*.nc' 2>/dev/null | wc -l
    printf 'local val nc='
    find "$LOCAL_VAL" -type f -name '*.nc' 2>/dev/null | wc -l
  fi
  bash "$V2/scripts/run_terrastate_no_fs_ablation.sh" status 2>/dev/null || true
  if [[ -f "$PIPELINE_LOG" ]]; then
    echo "===== pipeline log tail ====="
    tail -40 "$PIPELINE_LOG"
  fi
}

if [[ "$ACTION" == "status" ]]; then
  status
  exit 0
fi
[[ "$ACTION" == "run" ]] || die "usage: $0 {run|status}"

printf '%s\n' "$$" > "$PIPELINE_PID_FILE"
trap 'rm -f "$PIPELINE_PID_FILE"' EXIT

log "PIPELINE_START host=$(hostname) pid=$$"

require_dir "$V2"
require_dir "$MAIN"
require_dir "$SOURCE_DATA/train"
require_dir "$SOURCE_DATA/val_chopped"
require_file "$SOURCE_TRAIN_CACHE"
require_file "$SOURCE_VAL_CACHE"
require_file "$STUDENT"
require_file "$TEACHER"
require_file "$FULL_CKPT"
require_file "$CONDA_SH"

[[ ! -e "$OUT" ]] || die "output already exists and will not be overwritten: $OUT"

git -C "$V2" merge-base --is-ancestor "$BASE_IMPLEMENTATION_COMMIT" HEAD ||
  die "Git HEAD does not contain no-FS implementation $BASE_IMPLEMENTATION_COMMIT"

full_sha=$(sha256sum "$FULL_CKPT" | awk '{print $1}')
[[ "$full_sha" == "$FULL_CKPT_SHA256" ]] ||
  die "frozen full checkpoint SHA mismatch: got=$full_sha expected=$FULL_CKPT_SHA256"

# Conda activation is deliberately done without `set -u`: conda hooks may inspect
# unset CONDA_BACKUP_* variables on this cluster.
# shellcheck disable=SC1090
source "$CONDA_SH"
conda activate WorldModel
log "conda=$CONDA_PREFIX"

gpu_count=$(nvidia-smi -L 2>/dev/null | wc -l | tr -d ' ')
[[ "$gpu_count" == "8" ]] || die "visible GPU count=$gpu_count; expected 8"

gpu_processes=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null |
  sed '/^[[:space:]]*$/d' || true)
[[ -z "$gpu_processes" ]] || {
  nvidia-smi >&2
  die "one or more GPUs already have compute processes"
}

mkdir -p "$LOCAL_TRAIN" "$LOCAL_VAL" "$LOCAL_CACHE"

source_bytes=$(du -sb \
  "$SOURCE_DATA/train" \
  "$SOURCE_DATA/val_chopped" \
  "$SOURCE_TRAIN_CACHE" \
  "$SOURCE_VAL_CACHE" | awk '{s += $1} END {print s+0}')
local_bytes=$(du -sb "$LOCAL_TRAIN" "$LOCAL_VAL" "$LOCAL_CACHE" |
  awk '{s += $1} END {print s+0}')
available_bytes=$(df -PB1 /tmp | awk 'NR==2 {print $4}')
extra_bytes=$((source_bytes > local_bytes ? source_bytes - local_bytes : 0))
reserve_bytes=$((10 * 1024 * 1024 * 1024))
log "disk source_bytes=$source_bytes existing_local_bytes=$local_bytes available_bytes=$available_bytes reserve_bytes=$reserve_bytes"
(( available_bytes > extra_bytes + reserve_bytes )) ||
  die "insufficient /tmp space: need_extra=$extra_bytes reserve=$reserve_bytes available=$available_bytes"

rm -f "$STAGE_MARKER"
log "STAGE train -> $LOCAL_TRAIN"
rsync -a --delete --whole-file --info=progress2 "$SOURCE_DATA/train/" "$LOCAL_TRAIN/"
log "STAGE val_chopped -> $LOCAL_VAL"
rsync -a --delete --whole-file --info=progress2 "$SOURCE_DATA/val_chopped/" "$LOCAL_VAL/"
log "STAGE train cache -> $LOCAL_TRAIN_CACHE"
rsync -a --whole-file --info=progress2 "$SOURCE_TRAIN_CACHE" "$LOCAL_TRAIN_CACHE"
log "STAGE val cache -> $LOCAL_VAL_CACHE"
rsync -a --whole-file --info=progress2 "$SOURCE_VAL_CACHE" "$LOCAL_VAL_CACHE"

log "VERIFY local data/cache identities"
python - "$LOCAL_TRAIN" "$LOCAL_TRAIN_CACHE" "$LOCAL_VAL" "$LOCAL_VAL_CACHE" <<'PY'
import hashlib
import os
import sys
from pathlib import Path

import torch


def manifest(files, root):
    rows = sorted((p.relative_to(root).as_posix(), os.path.getsize(p)) for p in files)
    h = hashlib.sha256()
    for relpath, size in rows:
        h.update(relpath.encode())
        h.update(str(size).encode())
    return len(rows), h.hexdigest()


for split, root_arg, cache_arg in (
    ("train", sys.argv[1], sys.argv[2]),
    ("val", sys.argv[3], sys.argv[4]),
):
    root = Path(root_arg)
    cache = torch.load(cache_arg, map_location="cpu", weights_only=False, mmap=True)
    files = sorted(root.rglob("*.nc"))
    disk_keys = {p.relative_to(root).as_posix() for p in files}
    cache_keys = set(cache["targets"])
    if disk_keys != cache_keys:
        raise SystemExit(
            f"FAIL {split} keys: disk={len(disk_keys)} cache={len(cache_keys)} "
            f"missing={sorted(cache_keys-disk_keys)[:5]} extra={sorted(disk_keys-cache_keys)[:5]}"
        )
    count, got = manifest(files, root)
    expected = cache["provenance"]["data_manifest_sha256"]
    if got != expected:
        raise SystemExit(f"FAIL {split} manifest: got={got} expected={expected}")
    print(f"OK {split}: n={count} manifest_sha256={got}")
print("LOCAL_STAGE_OK")
PY

{
  date -u '+verified_at=%Y-%m-%dT%H:%M:%SZ'
  echo "host=$(hostname)"
  echo "train=$LOCAL_TRAIN"
  echo "val=$LOCAL_VAL"
  echo "train_cache=$LOCAL_TRAIN_CACHE"
  echo "val_cache=$LOCAL_VAL_CACHE"
} > "$STAGE_MARKER"

[[ ! -e "$OUT" ]] || die "output appeared concurrently: $OUT"
mkdir -p "$OUT"

{
  date -u '+%Y-%m-%dT%H:%M:%SZ'
  echo "host=$(hostname)"
  echo "git_commit=$(git -C "$V2" rev-parse HEAD)"
  echo "train_dir=$LOCAL_TRAIN"
  echo "val_dir=$LOCAL_VAL"
  echo "train_cache=$LOCAL_TRAIN_CACHE"
  echo "val_cache=$LOCAL_VAL_CACHE"
  echo "future_state_scale=0"
  echo "stop_after_step=11904"
  echo "planned_total_steps=14880"
  nvidia-smi
  sha256sum "$STUDENT" "$TEACHER" "$FULL_CKPT" "$LOCAL_TRAIN_CACHE" "$LOCAL_VAL_CACHE"
} > "$OUT/launch_provenance.txt"

# Copying can take long enough for cluster occupancy to change. Re-check immediately
# before torchrun so the pipeline never starts on newly occupied GPUs.
gpu_processes=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null |
  sed '/^[[:space:]]*$/d' || true)
[[ -z "$gpu_processes" ]] || {
  nvidia-smi >&2
  die "GPU compute processes appeared during staging; refusing to launch"
}

cd "$V2"
log "TRAIN_START output=$OUT"
env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 PYTHONUNBUFFERED=1 \
  "$CONDA_PREFIX/bin/torchrun" --standalone --nproc_per_node=8 \
  -m train.train_terrastate_v2 \
  --train-dir "$LOCAL_TRAIN" \
  --val-dir "$LOCAL_VAL" \
  --train-cache "$LOCAL_TRAIN_CACHE" \
  --val-cache "$LOCAL_VAL_CACHE" \
  --student-init "$STUDENT" \
  --teacher-b4 "$TEACHER" \
  --output-dir "$OUT" \
  --state-dim 256 \
  --per-gpu-batch 8 \
  --global-batch 64 \
  --num-workers 8 \
  --max-epochs 40 \
  --max-steps 0 \
  --future-state-scale 0 \
  --stop-after-step 11904 \
  --branch-lr 3e-5 \
  --q-lr-scale 0.033 \
  --weight-decay 0 \
  --grad-clip 1 \
  --lr-warmup-steps 300 \
  --unfreeze-q-prefixes core.blocks.2. \
  --seed 42 \
  --log-interval 50 \
  --val-interval 1000 \
  --ckpt-interval 2000 \
  --device cuda \
  --cache-fail-closed-gb 4 \
  > "$TRAIN_LOG" 2>&1 < /dev/null &

train_pid=$!
printf '%s\n' "$train_pid" > "$TRAIN_PID_FILE"
log "TRAIN_PID=$train_pid"

set +e
wait "$train_pid"
train_rc=$?
set -e
[[ "$train_rc" == "0" ]] || die "torchrun exited with rc=$train_rc; see $TRAIN_LOG"

log "TRAIN_EXIT_OK"
bash "$V2/scripts/run_terrastate_no_fs_ablation.sh" verify

python - "$OUT/checkpoint_boundary80.pt" "$OUT/training_result_summary.json" <<'PY'
import json
import sys

import torch

ck = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
summary = {
    "status": "TRAINING_COMPLETE_VERIFIED",
    "checkpoint": sys.argv[1],
    "step": ck["step"],
    "stage": ck["stage"],
    "total_steps": ck["total_steps"],
    "global_batch": ck["global_batch"],
    "future_state_scale": ck["future_state_scale"],
    "lambda_state_raw": ck["lambda_state_raw"],
    "effective_lambda_state": ck["effective_lambda_state"],
    "loss_weights": ck["loss_weights"],
    "q_trainable": ck["q_freeze"]["trainable_q"],
    "evaluation_status": "PENDING_SEPARATE_FROZEN_B_SESSION_Q1_Q2",
    "q3_status": "NOT_RUN",
}
with open(sys.argv[2], "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
PY

find "$OUT" -maxdepth 1 -type f ! -name SHA256SUMS.txt -print0 |
  sort -z |
  xargs -0 sha256sum > "$OUT/SHA256SUMS.txt"
touch "$OUT/PIPELINE_COMPLETE"

log "PIPELINE_COMPLETE checkpoint=$OUT/checkpoint_boundary80.pt"
log "summary=$OUT/training_result_summary.json"
log "sha256=$OUT/SHA256SUMS.txt"
