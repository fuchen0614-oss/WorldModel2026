#!/bin/bash
# ============================================================
# Stage 1 多卡 FSDP 训练（可指定 GPU 数量，默认 4 卡）
# 用法:
#   bash scripts/train_fsdp_multi.sh            # 默认 4 卡，正式训练步数
#   bash scripts/train_fsdp_multi.sh 3          # 3 卡
#   bash scripts/train_fsdp_multi.sh 4 5000     # 4 卡，5000 步
#   GPUS=0,1,2 bash scripts/train_fsdp_multi.sh 3   # 指定具体 GPU
# ============================================================

cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

NPROC=${1:-4}          # 第 1 个参数：GPU 数量，默认 4
MAX_STEPS=${2:-2000}   # 第 2 个参数：训练步数，默认 2000

# 若用户用 GPUS 环境变量指定了具体卡号，则限定可见 GPU
if [ -n "$GPUS" ]; then
  export CUDA_VISIBLE_DEVICES=$GPUS
  echo "限定可见 GPU: CUDA_VISIBLE_DEVICES=$GPUS"
fi

echo "启动 FSDP 训练: ${NPROC} 卡, ${MAX_STEPS} 步"

torchrun \
  --nproc_per_node=${NPROC} \
  --nnodes=1 \
  --rdzv_backend=c10d \
  --rdzv_endpoint=localhost:0 \
  train/train_stage1_ssl4eo.py \
  --config configs/train/stage1_fsdp.yaml \
  --max-steps ${MAX_STEPS} \
  --checkpoint-interval 500
