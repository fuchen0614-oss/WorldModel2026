#!/usr/bin/env bash
#
# Reliable server launcher for the single TerraState ablation:
#   w/o future-state anchoring (effective lambda_s == 0).
#
# This intentionally uses the persistent GreenEarthNet directories instead of the
# historical /tmp staging tree.  `preflight` proves that their relative file/size
# manifest exactly matches the already-frozen future-state caches before `launch`
# is allowed.
#
# Usage:
#   bash scripts/run_terrastate_no_fs_ablation.sh preflight
#   bash scripts/run_terrastate_no_fs_ablation.sh launch
#   bash scripts/run_terrastate_no_fs_ablation.sh status
#   bash scripts/run_terrastate_no_fs_ablation.sh verify

set -uo pipefail

ACTION=${1:-preflight}

V2=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb-v2train
MAIN=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb
DATA=/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet
TRAIN=/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/train
VAL=/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/val_chopped
OODT=/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/ood-t_chopped

TRAIN_CACHE=$V2/runs/terrastate_v2/cache/train_future_state_cache.pt
VAL_CACHE=$V2/runs/terrastate_v2/cache/val_future_state_cache.pt
STUDENT=$MAIN/runs/planb_excl_tournament/stageA_rescue_20260726_173149/MAIN/checkpoint_last.pt
TEACHER=$MAIN/checkpoints/plan_b_b4a/checkpoint_best.pt
FULL_CKPT=$V2/runs/terrastate_v2/run1/checkpoint_boundary80.pt

OUT=${TERRASTATE_ABLATION_OUT:-$V2/runs/terrastate_v2_ablation/no_future_state_anchor_seed42}
TRAIN_LOG=$OUT/train.log
PID_FILE=$OUT/train.pid
CKPT=$OUT/checkpoint_boundary80.pt

CONDA_SH=/csy-opt/cog8/zjliu17/miniconda3/etc/profile.d/conda.sh
BASE_IMPLEMENTATION_COMMIT=ea14a381b7f86fc0fbed2150e693ddaf69eb1270
FULL_CKPT_SHA256=644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd

FAILURES=0

ok() {
  printf 'OK   %s\n' "$*"
}

bad() {
  printf 'FAIL %s\n' "$*" >&2
  FAILURES=$((FAILURES + 1))
}

check_dir() {
  if [[ -d "$1" ]]; then
    ok "dir  $1"
  else
    bad "dir  $1"
  fi
}

check_file() {
  if [[ -f "$1" ]]; then
    ok "file $1"
  else
    bad "file $1"
  fi
}

activate_env() {
  if [[ ! -f "$CONDA_SH" ]]; then
    bad "conda initialization missing: $CONDA_SH"
    return 1
  fi
  # shellcheck disable=SC1090
  source "$CONDA_SH"
  if ! conda activate WorldModel; then
    bad "cannot activate conda environment WorldModel"
    return 1
  fi
  ok "conda environment WorldModel"
}

preflight() {
  FAILURES=0
  echo "==== TerraState no-FS preflight ===="
  echo "repo=$V2"
  echo "train=$TRAIN"
  echo "val=$VAL"
  echo "out=$OUT"

  for directory in "$V2" "$MAIN" "$DATA" "$TRAIN" "$VAL" "$OODT"; do
    check_dir "$directory"
  done
  for file in "$TRAIN_CACHE" "$VAL_CACHE" "$STUDENT" "$TEACHER" "$FULL_CKPT"; do
    check_file "$file"
  done

  if [[ -d "$V2/.git" || -f "$V2/.git" ]]; then
    local head
    head=$(git -C "$V2" rev-parse HEAD 2>/dev/null || true)
    echo "INFO git_head=$head"
    if git -C "$V2" merge-base --is-ancestor "$BASE_IMPLEMENTATION_COMMIT" HEAD 2>/dev/null; then
      ok "Git contains no-FS implementation $BASE_IMPLEMENTATION_COMMIT"
    else
      bad "Git HEAD does not contain $BASE_IMPLEMENTATION_COMMIT"
    fi
  else
    bad "not a Git worktree: $V2"
  fi

  if [[ -f "$FULL_CKPT" ]]; then
    local got_sha
    got_sha=$(sha256sum "$FULL_CKPT" | awk '{print $1}')
    if [[ "$got_sha" == "$FULL_CKPT_SHA256" ]]; then
      ok "frozen full checkpoint SHA256=$got_sha"
    else
      bad "frozen full checkpoint SHA mismatch: got=$got_sha want=$FULL_CKPT_SHA256"
    fi
  fi

  local gpu_count
  gpu_count=$(nvidia-smi -L 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$gpu_count" == "8" ]]; then
    ok "visible GPU count=8"
  else
    bad "visible GPU count=$gpu_count (need 8)"
  fi

  activate_env || true

  if [[ -f "$TRAIN_CACHE" && -f "$VAL_CACHE" && -d "$TRAIN" && -d "$VAL" ]]; then
    python - "$TRAIN" "$TRAIN_CACHE" "$VAL" "$VAL_CACHE" <<'PY'
import hashlib
import os
import sys
from pathlib import Path

import torch

def rel_manifest_sha(files, root):
    rows = []
    for path in files:
        rows.append((path.relative_to(root).as_posix(), os.path.getsize(path)))
    h = hashlib.sha256()
    for relpath, size in sorted(rows):
        h.update(relpath.encode())
        h.update(str(size).encode())
    return h.hexdigest()

for split, root_arg, cache_arg in (
    ("train", sys.argv[1], sys.argv[2]),
    ("val", sys.argv[3], sys.argv[4]),
):
    root = Path(root_arg)
    cache = torch.load(cache_arg, map_location="cpu", weights_only=False, mmap=True)
    files = sorted(root.rglob("*.nc"))
    disk_keys = {path.relative_to(root).as_posix() for path in files}
    cache_keys = set(cache["targets"])
    if disk_keys != cache_keys:
        missing = sorted(cache_keys - disk_keys)[:5]
        extra = sorted(disk_keys - cache_keys)[:5]
        raise SystemExit(
            f"FAIL {split} cache/data key mismatch: disk={len(disk_keys)} "
            f"cache={len(cache_keys)} missing={missing} extra={extra}"
        )
    got_sha = rel_manifest_sha(files, root)
    want_sha = cache["provenance"]["data_manifest_sha256"]
    if got_sha != want_sha:
        raise SystemExit(
            f"FAIL {split} cache/data manifest mismatch: got={got_sha} want={want_sha}"
        )
    print(
        f"OK   {split} persistent data == frozen cache: "
        f"n={len(files)} manifest_sha256={got_sha}"
    )
PY
    if [[ $? -ne 0 ]]; then
      bad "persistent GreenEarthNet data is not identical to frozen cache"
    fi
  fi

  if [[ -e "$OUT" ]]; then
    echo "INFO output already exists: $OUT"
    ls -la "$OUT" 2>/dev/null | sed -n '1,30p'
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "INFO existing training process is alive: PID=$(cat "$PID_FILE")"
    fi
  else
    ok "output does not exist"
  fi

  if [[ "$FAILURES" -ne 0 ]]; then
    echo "PREFLIGHT_FAILED count=$FAILURES" >&2
    return 1
  fi
  echo "PREFLIGHT_OK"
}

launch() {
  if ! preflight; then
    echo "LAUNCH_REFUSED: fix the printed FAIL lines first." >&2
    return 1
  fi
  if [[ -e "$OUT" ]]; then
    echo "LAUNCH_REFUSED: output already exists; it will not be overwritten: $OUT" >&2
    return 1
  fi

  mkdir -p "$OUT"
  {
    date -u '+%Y-%m-%dT%H:%M:%SZ'
    git -C "$V2" rev-parse HEAD
    nvidia-smi
    sha256sum "$STUDENT" "$TEACHER" "$FULL_CKPT"
  } > "$OUT/launch_provenance.txt"

  cd "$V2" || return 1
  nohup env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 PYTHONUNBUFFERED=1 \
    torchrun --standalone --nproc_per_node=8 \
    -m train.train_terrastate_v2 \
    --train-dir "$TRAIN" \
    --val-dir "$VAL" \
    --train-cache "$TRAIN_CACHE" \
    --val-cache "$VAL_CACHE" \
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

  local train_pid=$!
  printf '%s\n' "$train_pid" > "$PID_FILE"
  sleep 3
  if ! kill -0 "$train_pid" 2>/dev/null; then
    echo "LAUNCH_FAILED: torchrun exited immediately." >&2
    tail -100 "$TRAIN_LOG" >&2
    return 1
  fi
  echo "LAUNCH_OK pid=$train_pid"
  echo "status: bash $V2/scripts/run_terrastate_no_fs_ablation.sh status"
  echo "log:    tail -f $TRAIN_LOG"
}

status() {
  echo "out=$OUT"
  if [[ ! -f "$PID_FILE" ]]; then
    echo "NO_PID_FILE"
  else
    local train_pid
    train_pid=$(cat "$PID_FILE")
    if kill -0 "$train_pid" 2>/dev/null; then
      echo "RUNNING pid=$train_pid"
      ps -fp "$train_pid" || true
    else
      echo "NOT_RUNNING pid=$train_pid"
    fi
  fi
  if [[ -f "$TRAIN_LOG" ]]; then
    grep -E 'total_steps=|step [0-9]+/|boundary80|effective|done step=|Traceback|Error' \
      "$TRAIN_LOG" | tail -50
  else
    echo "NO_TRAIN_LOG"
  fi
}

verify() {
  if [[ ! -f "$CKPT" ]]; then
    echo "VERIFY_FAILED: boundary checkpoint missing: $CKPT" >&2
    return 1
  fi
  if [[ ! -f "$TRAIN_LOG" ]] || ! grep -q 'done step=11904' "$TRAIN_LOG"; then
    echo "VERIFY_FAILED: training log has no done step=11904" >&2
    return 1
  fi

  activate_env || return 1
  python - "$CKPT" "$FULL_CKPT" <<'PY'
import sys
import torch

new = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
full = torch.load(sys.argv[2], map_location="cpu", weights_only=False)

assert new["step"] == 11904
assert new["stage"] == 2
assert new["total_steps"] == 14880
assert new["global_batch"] == 64
assert new["accum"] == 1
assert new["q_freeze"]["trainable_q"] == []
assert new["contract_cfg"]["freeze_b0"] is True
assert new["future_state_scale"] == 0.0
assert new["effective_lambda_state"] == 0.0
assert new["args"]["stop_after_step"] == 11904
assert new["loss_weights"]["gt"] == 1.0
assert new["loss_weights"]["kd"] == 0.5

for key in (
    "q_projector_init_sha256",
    "teacher_sha256",
    "student_init_sha256",
    "train_cache_sha256",
    "val_cache_sha256",
    "train_manifest_sha256",
    "val_manifest_sha256",
):
    assert new["sha"][key] == full["sha"][key], key

print("VERIFY_OK step=11904 stage=2 total_steps=14880 scale=0 q_trainable=0")
PY
}

case "$ACTION" in
  preflight)
    preflight
    ;;
  launch)
    launch
    ;;
  status)
    status
    ;;
  verify)
    verify
    ;;
  *)
    echo "Usage: $0 {preflight|launch|status|verify}" >&2
    exit 2
    ;;
esac
