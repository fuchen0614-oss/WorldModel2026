#!/bin/bash
# Stage 1 多卡 FSDP smoke test（2 卡，10 步）
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
torchrun \
  --nproc_per_node=2 \
  --nnodes=1 \
  train/train_stage1_ssl4eo.py \
  --config configs/train/stage1_fsdp.yaml \
  --max-steps 10
