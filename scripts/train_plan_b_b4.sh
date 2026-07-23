#!/usr/bin/env bash
# plan-b-pvt · B4 (TerraState) launcher (8×H200 DDP).
# Same data / split / evaluator as B0 (train / val_chopped / ood-t frozen for final test).
# TerraState losses on the shared state (all masked, B0 protocol):
#   --lambda-fore  masked direct-endpoint forecast   --lambda-resid  ungated r* (anti-starvation)
#   --lambda-cmp   direct+composed endpoint          --lambda-con    direct/composed consistency
#   --lambda-vic   VICReg anti-collapse              --freeze-b0     1=stage1 (frozen), 0=stage2 (joint)
#
#   Local CPU synthetic training smoke (no GPU, no data):
#     CUDA_VISIBLE_DEVICES="" PYTHON=/mnt/data/public_tools/miniconda3/envs/fastwam-vjepa/bin/python \
#     $PYTHON scripts/smoke_b4_train.py
#   Server 1-GPU real-data smoke (3 steps):
#     GPUS=1 PER_GPU_BATCH=2 MAX_STEPS=3 NUM_WORKERS=2 VAL_INTERVAL=3 CKPT_INTERVAL=999999 \
#     bash scripts/train_plan_b_b4.sh
#   Full B4a (8 GPU, warm-start + frozen B0):
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
FREEZE_B0="${FREEZE_B0:-1}"
LAMBDA_FORE="${LAMBDA_FORE:-1.0}"
LAMBDA_RESID="${LAMBDA_RESID:-1.0}"
LAMBDA_CMP="${LAMBDA_CMP:-0.0}"     # Phase I: cmp OFF (ramp to ~0.1 in Phase II after accuracy stabilises)
LAMBDA_CON="${LAMBDA_CON:-0.0}"     # Phase I: con OFF (ramp in Phase II)
LAMBDA_VIC="${LAMBDA_VIC:-0.05}"    # audit: 1.0 makes VICReg dominate prediction losses ~3.8x
RESUME_B4="${RESUME_B4:-}"          # full b4_state_dict to resume (Phase II / stage 2; empty=fresh)
BACKBONE_LR_SCALE="${BACKBONE_LR_SCALE:-0.1}"   # q/backbone LR multiplier (stage-2 joint fine-tune)
NUM_WORKERS="${NUM_WORKERS:-8}"
LOG_INTERVAL="${LOG_INTERVAL:-50}"
VAL_INTERVAL="${VAL_INTERVAL:-1000}"
CKPT_INTERVAL="${CKPT_INTERVAL:-2000}"

mkdir -p "$OUTPUT_DIR"
echo "GPUS=$GPUS PER_GPU_BATCH=$PER_GPU_BATCH MAX_EPOCHS=$MAX_EPOCHS MAX_STEPS=$MAX_STEPS LR=$LR FREEZE_B0=$FREEZE_B0"
echo "LAMBDAS fore=$LAMBDA_FORE resid=$LAMBDA_RESID cmp=$LAMBDA_CMP con=$LAMBDA_CON vic=$LAMBDA_VIC"
echo "DATA_GEN=$DATA_GEN INIT_CKPT=$INIT_CKPT OUTPUT_DIR=$OUTPUT_DIR"

PYTHON="${PYTHON:-python}"
"$PYTHON" -m torch.distributed.run --standalone --nproc_per_node="$GPUS" -m train.train_plan_b_b4 \
  --train-dir "$DATA_GEN/train" --val-dir "$DATA_GEN/val_chopped" \
  --init-ckpt "$INIT_CKPT" --output-dir "$OUTPUT_DIR" \
  --per-gpu-batch "$PER_GPU_BATCH" --max-epochs "$MAX_EPOCHS" --max-steps "$MAX_STEPS" \
  --lr "$LR" --freeze-b0 "$FREEZE_B0" --backbone-lr-scale "$BACKBONE_LR_SCALE" --resume-b4 "$RESUME_B4" \
  --lambda-fore "$LAMBDA_FORE" --lambda-resid "$LAMBDA_RESID" --lambda-cmp "$LAMBDA_CMP" \
  --lambda-con "$LAMBDA_CON" --lambda-vic "$LAMBDA_VIC" --num-workers "$NUM_WORKERS" \
  --log-interval "$LOG_INTERVAL" --val-interval "$VAL_INTERVAL" --ckpt-interval "$CKPT_INTERVAL" \
  2>&1 | tee -a "$OUTPUT_DIR/train.log"
