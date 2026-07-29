#!/usr/bin/env bash
#
# Formal Q1/Q2-only evaluation for the registered no-future-state ablation.
# Runs val_chopped and ood-t_chopped on the fixed boundary80 checkpoint.
# Q3 is never invoked.

set -eo pipefail

ACTION=${1:-run}

V2=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb-v2train
DATA=/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet
LOCAL_STAGE=/tmp/zjliu17_mix_stage_v2
LOCAL_VAL=$LOCAL_STAGE/val_chopped
LOCAL_OODT=$LOCAL_STAGE/ood-t_chopped

TRAIN_OUT=$V2/runs/terrastate_v2_ablation/no_future_state_anchor_seed42
CKPT=$TRAIN_OUT/checkpoint_boundary80.pt
EVAL_ROOT=$TRAIN_OUT/evaluation_q1q2
VAL_OUT=$EVAL_ROOT/val_chopped
OODT_OUT=$EVAL_ROOT/ood-t_chopped
VAL_MANIFEST=$EVAL_ROOT/val_chopped_manifest.json
OODT_MANIFEST=$V2/evaluations/greenearthnet_oodt_20260719_214234/greenearthnet_oodt_chopped_manifest.json

PIPELINE_LOG=/tmp/terrastate_no_fs_q1q2.log
PID_FILE=/tmp/terrastate_no_fs_q1q2.pid
CONDA_SH=/csy-opt/cog8/zjliu17/miniconda3/etc/profile.d/conda.sh
EVALUATOR_BASE_COMMIT=0ca6750

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

die() {
  log "Q1Q2_FAILED: $*" >&2
  exit 1
}

status() {
  echo "evaluation_root=$EVAL_ROOT"
  echo "pipeline_log=$PIPELINE_LOG"
  if [[ -f "$PID_FILE" ]]; then
    eval_pid=$(cat "$PID_FILE")
    if kill -0 "$eval_pid" 2>/dev/null; then
      echo "Q1Q2_RUNNING pid=$eval_pid"
      ps -fp "$eval_pid" || true
    else
      echo "Q1Q2_NOT_RUNNING pid=$eval_pid"
    fi
  else
    echo "NO_Q1Q2_PID"
  fi
  for result in \
    "$VAL_OUT/state_contract_exclusive.json" \
    "$OODT_OUT/state_contract_exclusive.json" \
    "$EVAL_ROOT/full_vs_no_fs_q1q2.json"; do
    [[ -f "$result" ]] && ls -lh "$result"
  done
  [[ -f "$PIPELINE_LOG" ]] && tail -60 "$PIPELINE_LOG"
}

if [[ "$ACTION" == "status" ]]; then
  status
  exit 0
fi
[[ "$ACTION" == "run" ]] || die "usage: $0 {run|status}"

printf '%s\n' "$$" > "$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT

log "Q1Q2_PIPELINE_START host=$(hostname) pid=$$"

[[ -f "$CONDA_SH" ]] || die "missing conda initialization: $CONDA_SH"
# shellcheck disable=SC1090
source "$CONDA_SH"
conda activate WorldModel

[[ -f "$CKPT" ]] || die "missing boundary80 checkpoint: $CKPT"
[[ -f "$TRAIN_OUT/PIPELINE_COMPLETE" ]] || die "training pipeline is not marked complete"
[[ -d "$LOCAL_VAL" ]] || die "missing local val_chopped: $LOCAL_VAL"
[[ -d "$DATA/ood-t_chopped" ]] || die "missing source ood-t_chopped: $DATA/ood-t_chopped"
[[ -f "$OODT_MANIFEST" ]] || die "missing frozen OOD-t manifest: $OODT_MANIFEST"

git -C "$V2" merge-base --is-ancestor "$EVALUATOR_BASE_COMMIT" HEAD ||
  die "Git HEAD does not contain frozen Q1/Q2 evaluator base $EVALUATOR_BASE_COMMIT"

python - "$CKPT" <<'PY'
import sys
import torch

ck = torch.load(sys.argv[1], map_location="cpu", weights_only=False, mmap=True)
assert ck["step"] == 11904
assert ck["stage"] == 2
assert ck["future_state_scale"] == 0.0
assert ck["effective_lambda_state"] == 0.0
assert ck["q_freeze"]["trainable_q"] == []
print("CHECKPOINT_OK step=11904 stage=2 scale=0")
PY

gpu_processes=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null |
  sed '/^[[:space:]]*$/d' || true)
[[ -z "$gpu_processes" ]] || {
  nvidia-smi >&2
  die "GPU compute processes are already running"
}

for local_track in "$LOCAL_VAL" "$LOCAL_OODT"; do
  if [[ -L "$local_track" ]]; then
    link_target=$(readlink "$local_track")
    log "UNLINK local staging symlink $local_track -> $link_target"
    unlink "$local_track"
  fi
  mkdir -p "$local_track"
done
mkdir -p "$EVAL_ROOT"
# GreenEarthNet chopped tracks may contain symlinked cubes. Formal manifests
# resolve paths and correctly reject links that escape LOCAL_STAGE, so materialize
# the targets with -L instead of preserving symlinks.
log "STAGE materialized val_chopped -> $LOCAL_VAL"
rsync -aL --delete --whole-file --info=progress2 "$DATA/val_chopped/" "$LOCAL_VAL/"
log "STAGE materialized ood-t_chopped -> $LOCAL_OODT"
rsync -aL --delete --whole-file --info=progress2 "$DATA/ood-t_chopped/" "$LOCAL_OODT/"

remaining_links=$(find "$LOCAL_VAL" "$LOCAL_OODT" -type l -print -quit)
[[ -z "$remaining_links" ]] ||
  die "local evaluation tracks still contain symlinks: $remaining_links"

log "FREEZE val_chopped manifest"
python "$V2/scripts/freeze_greenearthnet_chopped_protocol.py" \
  --eval-root "$LOCAL_STAGE" \
  --track val_chopped \
  --output "$VAL_MANIFEST" \
  --hash-mode sha256

log "VERIFY manifests and exact target counts"
python - "$VAL_MANIFEST" "$OODT_MANIFEST" "$LOCAL_STAGE" <<'PY'
import json
import sys
from data.earthnet_manifest import load_manifest_files

val_manifest, ood_manifest, root = sys.argv[1:]
for split, path, expected in (
    ("val_chopped", val_manifest, 952),
    ("ood-t_chopped", ood_manifest, 1904),
):
    payload = json.load(open(path))
    files = load_manifest_files(
        path,
        root,
        expected_split=split,
        expected_protocol="greenearthnet_cvpr2024_chopped_v1",
        verify_exists=True,
    )
    assert len(files) == expected, (split, len(files), expected)
    assert payload["role"] == split
    print(f"MANIFEST_OK split={split} n={len(files)} files_sha256={payload['files_sha256']}")
PY

log "EVAL val_chopped Q1/Q2 only"
CUDA_VISIBLE_DEVICES=0 python "$V2/eval/eval_b4_exclusive_contract.py" \
  --ckpt "$CKPT" \
  --val-dir "$LOCAL_VAL" \
  --data-manifest "$VAL_MANIFEST" \
  --dataset-root "$LOCAL_STAGE" \
  --split val_chopped \
  --output-dir "$VAL_OUT" \
  --sections q1q2 \
  --workers 8 \
  --batch-size 1 \
  --num-data-workers 4 \
  --device cuda \
  2>&1 | tee "$EVAL_ROOT/val_chopped.log"

log "EVAL ood-t_chopped Q1/Q2 only"
CUDA_VISIBLE_DEVICES=0 python "$V2/eval/eval_b4_exclusive_contract.py" \
  --ckpt "$CKPT" \
  --val-dir "$LOCAL_OODT" \
  --data-manifest "$OODT_MANIFEST" \
  --dataset-root "$LOCAL_STAGE" \
  --split ood-t_chopped \
  --output-dir "$OODT_OUT" \
  --sections q1q2 \
  --workers 8 \
  --batch-size 1 \
  --num-data-workers 4 \
  --device cuda \
  2>&1 | tee "$EVAL_ROOT/ood-t_chopped.log"

log "SUMMARIZE Full TerraState vs w/o future-state anchor"
python "$V2/scripts/summarize_terrastate_no_fs_q1q2.py" \
  --val-json "$VAL_OUT/state_contract_exclusive.json" \
  --ood-json "$OODT_OUT/state_contract_exclusive.json" \
  --output-json "$EVAL_ROOT/full_vs_no_fs_q1q2.json" \
  --output-md "$EVAL_ROOT/full_vs_no_fs_q1q2.md"

find "$EVAL_ROOT" -type f ! -name SHA256SUMS.txt -print0 |
  sort -z |
  xargs -0 sha256sum > "$EVAL_ROOT/SHA256SUMS.txt"
touch "$EVAL_ROOT/Q1Q2_COMPLETE"
touch "$EVAL_ROOT/Q3_NOT_RUN"

log "Q1Q2_COMPLETE summary=$EVAL_ROOT/full_vs_no_fs_q1q2.json"
log "Q3_NOT_RUN"
