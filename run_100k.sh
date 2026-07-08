#!/bin/bash
# Stage 1 训练脚本 - 100K steps，大 batch size

cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026

# 激活环境
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

# 8 卡训练，100k steps
torchrun --nproc_per_node=8 \
  train/train_stage1_ssl4eo.py \
  --config configs/train/stage1_long_v2.yaml \
  --max-steps 100000 \
  --viz-interval 5000 \
  --mask-ratio 0.75
