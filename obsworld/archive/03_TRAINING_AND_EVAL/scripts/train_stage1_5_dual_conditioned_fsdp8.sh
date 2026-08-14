#!/bin/bash
set -euo pipefail

cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

mkdir -p logs
TS=$(date +%Y%m%d_%H%M%S)
LOG="logs/stage1_5_dual_conditioned_vits_${TS}.log"

echo "Starting canonical Stage1.5 dual-conditioned ViT-S; log=${LOG}"
torchrun --nproc_per_node=8 --nnodes=1 \
  --rdzv_backend=c10d --rdzv_endpoint=localhost:0 \
  train/train_stage1_5_dual_conditioned.py \
  --config configs/train/stage1_5_dual_conditioned_vits.yaml \
  2>&1 | tee "${LOG}"
