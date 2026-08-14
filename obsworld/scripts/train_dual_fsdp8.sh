#!/bin/bash
# 双模态 Stage 1 FSDP 8 卡训练（50k steps）

cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026

source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

torchrun --nproc_per_node=8 --nnodes=1 \
  --rdzv_backend=c10d --rdzv_endpoint=localhost:0 \
  train/train_stage1_dual.py \
  --config configs/train/stage1_dual.yaml \
  --max-steps 50000 \
  --checkpoint-interval 2500 \
  2>&1 | tee logs/stage1_dual_8gpu_50k.log
