#!/bin/bash
# Stage 1 单卡 smoke test（10 步）
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
python train/train_stage1_ssl4eo.py \
  --config configs/train/stage1_single.yaml \
  --max-steps 10
