#!/usr/bin/env bash
set -euo pipefail

# Explicit official EarthNet closure for a checkpoint selected on complete
# val_dev.  The target directory is intentionally required: scoring a
# prediction directory against an implicit/guessed target is not evidence.
: "${CONFIG:?set CONFIG to the resolved Stage2 config}"
: "${CHECKPOINT:?set CHECKPOINT to the selected checkpoint}"
: "${DATA_ROOT:?set DATA_ROOT to the EarthNet root}"
: "${SPLIT:?set SPLIT to iid/ood/extreme/seasonal/test}"
: "${PREDICTION_DIR:?set PREDICTION_DIR for exported NPZ files}"
: "${TARGET_DIR:?set TARGET_DIR to the official EarthNet target directory}"
: "${SCORE_DIR:?set SCORE_DIR for official score outputs}"

predict_args=(
  --config "$CONFIG"
  --checkpoint "$CHECKPOINT"
  --data-root "$DATA_ROOT"
  --split "$SPLIT"
  --output-dir "$PREDICTION_DIR"
  --batch-size "${BATCH_SIZE:-8}"
  --num-workers "${NUM_WORKERS:-4}"
  --conditioning-stats-path "${CONDITIONING_STATS_PATH:?set CONDITIONING_STATS_PATH}"
  --manifest-path "${MANIFEST_PATH:?set MANIFEST_PATH for the selected split}"
  --hash-mode sha256
)
if [[ -n "${EXTERNAL_DRIVER_ROOT:-}" ]]; then
  predict_args+=(--external-driver-root "$EXTERNAL_DRIVER_ROOT")
fi
if [[ -n "${DGH_STATS_PATH:-}" ]]; then
  predict_args+=(--dgh-stats-path "$DGH_STATS_PATH")
fi

python eval/predict_stage2_earthnet.py \
  "${predict_args[@]}"

python eval/score_earthnet_prediction_dir.py \
  --prediction-dir "$PREDICTION_DIR" \
  --target-dir "$TARGET_DIR" \
  --workers "${SCORE_WORKERS:--1}" \
  --output-dir "$SCORE_DIR"
