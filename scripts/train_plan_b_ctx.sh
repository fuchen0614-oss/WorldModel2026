#!/usr/bin/env bash
# plan-b-pvt · B0 matched fine-tune launcher (8×H200 DDP).
# Env-var driven. Trains reproduced Contextformer on GreenEarthNet train.
#
#   Smoke (1 GPU, real data, 3 steps):
#     GPUS=1 PER_GPU_BATCH=2 MAX_STEPS=3 NUM_WORKERS=2 VAL_INTERVAL=3 CKPT_INTERVAL=999999 \
#     bash scripts/train_plan_b_ctx.sh
#   Full B0 (8 GPU):
#     bash scripts/train_plan_b_ctx.sh
set -euo pipefail

GPUS="${GPUS:-8}"
DATA_GEN="${DATA_GEN:-/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet}"
INIT_CKPT="${INIT_CKPT:-checkpoints/contextformer_official/contextformer6M/seed42.ckpt}"
OUTPUT_DIR="${OUTPUT_DIR:-checkpoints/plan_b_b0}"
PER_GPU_BATCH="${PER_GPU_BATCH:-8}"
MAX_EPOCHS="${MAX_EPOCHS:-40}"
MAX_STEPS="${MAX_STEPS:-0}"
LR="${LR:-1e-5}"
NUM_WORKERS="${NUM_WORKERS:-8}"
LOG_INTERVAL="${LOG_INTERVAL:-50}"
VAL_INTERVAL="${VAL_INTERVAL:-1000}"
CKPT_INTERVAL="${CKPT_INTERVAL:-2000}"

mkdir -p "$OUTPUT_DIR"
echo "GPUS=$GPUS PER_GPU_BATCH=$PER_GPU_BATCH MAX_EPOCHS=$MAX_EPOCHS MAX_STEPS=$MAX_STEPS LR=$LR"
echo "DATA_GEN=$DATA_GEN INIT_CKPT=$INIT_CKPT OUTPUT_DIR=$OUTPUT_DIR"

# Use the active python's torch.distributed.run (robust; no torchrun-on-PATH needed).
# Set PYTHON=/path/to/env/bin/python to override if the env is not activated.
PYTHON="${PYTHON:-python}"
"$PYTHON" -m torch.distributed.run --standalone --nproc_per_node="$GPUS" -m train.train_plan_b_contextformer \
  --train-dir "$DATA_GEN/train" --val-dir "$DATA_GEN/val_chopped" \
  --init-ckpt "$INIT_CKPT" --output-dir "$OUTPUT_DIR" \
  --per-gpu-batch "$PER_GPU_BATCH" --max-epochs "$MAX_EPOCHS" --max-steps "$MAX_STEPS" \
  --lr "$LR" --num-workers "$NUM_WORKERS" \
  --log-interval "$LOG_INTERVAL" --val-interval "$VAL_INTERVAL" --ckpt-interval "$CKPT_INTERVAL" \
  2>&1 | tee -a "$OUTPUT_DIR/train.log"
