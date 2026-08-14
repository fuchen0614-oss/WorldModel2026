#!/bin/bash
# 双模态 Stage 1 单卡 smoke test（10 steps）

cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026

source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

python train/train_stage1_dual.py \
  --config configs/train/stage1_dual.yaml \
  --max-steps 10 \
  --checkpoint-interval 10 \
  2>&1 | tee logs/dual_smoke_single.log
