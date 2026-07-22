#!/usr/bin/env bash
# plan-b-pvt · B4 (ObsWorldB4 shared-z world model) launcher (8×H200 DDP).
# Same data/recipe as B0; adds JEPA (--lambda-dyn) + VICReg (--lambda-vic) on shared z.
#
#   Local GPU smoke (4-7, synthetic, no data) — sanity before the real run:
#     CUDA_VISIBLE_DEVICES=4,5,6,7 PYTHON=/mnt/data/public_tools/miniconda3/envs/fastwam-vjepa/bin/python \
#     python scripts/smoke_b4_train.py
#   Server 1-GPU real-data smoke (3 steps):
#     GPUS=1 PER_GPU_BATCH=2 MAX_STEPS=3 NUM_WORKERS=2 VAL_INTERVAL=3 CKPT_INTERVAL=999999 \
#     bash scripts/train_plan_b_b4.sh
#   Full B4a (8 GPU, warm-start + aux only):
#     bash scripts/train_plan_b_b4.sh
#   B4b later (SSL4EO-pretrained init): INIT_CKPT=checkpoints/plan_b_ssl4eo/... OUTPUT_DIR=checkpoints/plan_b_b4b \
#     bash scripts/train_plan_b_b4.sh
set -euo pipefail

GPUS="${GPUS:-8}"
DATA_GEN="${DATA_GEN:-/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet}"
INIT_CKPT="${INIT_CKPT:-checkpoints/contextformer_official/contextformer6M/seed42.ckpt}"
OUTPUT_DIR="${OUTPUT_DIR:-checkpoints/plan_b_b4a}"
PER_GPU_BATCH="${PER_GPU_BATCH:-8}"
MAX_EPOCHS="${MAX_EPOCHS:-40}"
MAX_STEPS="${MAX_STEPS:-0}"
LR="${LR:-1e-5}"
LAMBDA_DYN="${LAMBDA_DYN:-1.0}"
LAMBDA_VIC="${LAMBDA_VIC:-1.0}"
NUM_WORKERS="${NUM_WORKERS:-8}"
LOG_INTERVAL="${LOG_INTERVAL:-50}"
VAL_INTERVAL="${VAL_INTERVAL:-1000}"
CKPT_INTERVAL="${CKPT_INTERVAL:-2000}"

mkdir -p "$OUTPUT_DIR"
echo "GPUS=$GPUS PER_GPU_BATCH=$PER_GPU_BATCH MAX_EPOCHS=$MAX_EPOCHS MAX_STEPS=$MAX_STEPS LR=$LR"
echo "LAMBDA_DYN=$LAMBDA_DYN LAMBDA_VIC=$LAMBDA_VIC"
echo "DATA_GEN=$DATA_GEN INIT_CKPT=$INIT_CKPT OUTPUT_DIR=$OUTPUT_DIR"

PYTHON="${PYTHON:-python}"
"$PYTHON" -m torch.distributed.run --standalone --nproc_per_node="$GPUS" -m train.train_plan_b_b4 \
  --train-dir "$DATA_GEN/train" --val-dir "$DATA_GEN/val_chopped" \
  --init-ckpt "$INIT_CKPT" --output-dir "$OUTPUT_DIR" \
  --per-gpu-batch "$PER_GPU_BATCH" --max-epochs "$MAX_EPOCHS" --max-steps "$MAX_STEPS" \
  --lr "$LR" --lambda-dyn "$LAMBDA_DYN" --lambda-vic "$LAMBDA_VIC" --num-workers "$NUM_WORKERS" \
  --log-interval "$LOG_INTERVAL" --val-interval "$VAL_INTERVAL" --ckpt-interval "$CKPT_INTERVAL" \
  2>&1 | tee -a "$OUTPUT_DIR/train.log"
