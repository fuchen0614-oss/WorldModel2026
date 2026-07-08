#!/bin/bash
# Stage 1 大 Batch 训练脚本

cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026

# 激活环境
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

# 8 卡训练
torchrun --nproc_per_node=8 \
  train/train_stage1_ssl4eo.py \
  --config configs/train/stage1_long_v2.yaml \
  --max-steps 50000 \
  --viz-interval 2000 \
  --mask-ratio 0.75

