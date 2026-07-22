#!/usr/bin/env bash
# plan-b-pvt · Stage1.8 factorization launcher (8-GPU DDP).
#   conda activate WorldModel
#   export PYTHON=/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python
#   CACHE_DIR=/tmp/zjliu17_l1c_l2a_cache bash scripts/train_stage1_8.sh
set -euo pipefail

GPUS="${GPUS:-8}"
CACHE_DIR="${CACHE_DIR:-/tmp/${USER}_l1c_l2a_cache}"
OUTPUT_DIR="${OUTPUT_DIR:-checkpoints/plan_b_stage1_8}"
PER_GPU_BATCH="${PER_GPU_BATCH:-32}"
MAX_EPOCHS="${MAX_EPOCHS:-30}"
MAX_STEPS="${MAX_STEPS:-0}"
LR="${LR:-3e-4}"
NUM_WORKERS="${NUM_WORKERS:-8}"
PYTHON="${PYTHON:-python}"

mkdir -p "$OUTPUT_DIR"
echo "GPUS=$GPUS PER_GPU_BATCH=$PER_GPU_BATCH MAX_EPOCHS=$MAX_EPOCHS CACHE_DIR=$CACHE_DIR"
"$PYTHON" -m torch.distributed.run --standalone --nproc_per_node="$GPUS" -m train.train_stage1_8_factorize \
  --cache-dir "$CACHE_DIR" --output-dir "$OUTPUT_DIR" \
  --per-gpu-batch "$PER_GPU_BATCH" --max-epochs "$MAX_EPOCHS" --max-steps "$MAX_STEPS" \
  --lr "$LR" --num-workers "$NUM_WORKERS" \
  2>&1 | tee -a "$OUTPUT_DIR/train.log"
