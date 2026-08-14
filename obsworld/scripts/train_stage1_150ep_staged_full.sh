#!/bin/bash
# Stage 1 完整流程：等待 staged 数据准备 → 训练 → 清理
set -e

cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel 2>/dev/null || true

CKPT_DIR="checkpoints/stage1_150ep_viz"
LOG_DIR="logs/stage1_150ep_viz"
STAGED_ROOT="/dev/shm/zjliu17_ssl4eo"
S1_TMP="/tmp/zjliu17_ssl4eo_s1"

# 1. 等待 staged 数据准备完成
echo "[$(date)] 等待 staged 数据准备完成..."
while [ ! -f /tmp/setup_staged_data.log ] || ! grep -q "Staged 数据准备完成" /tmp/setup_staged_data.log 2>/dev/null; do
  sleep 30
done
echo "[$(date)] ✓ Staged 数据已就绪"

# 2. 验证数据
echo "[$(date)] 验证 staged 数据..."
if [ ! -d "${STAGED_ROOT}/train/S2L2A" ]; then
  echo "❌ 错误: S2L2A 目录不存在"
  exit 1
fi
if [ ! -L "${STAGED_ROOT}/train/S1GRD" ]; then
  echo "❌ 错误: S1GRD 软链不存在"
  exit 1
fi
echo "[$(date)] ✓ 数据验证通过"

# 3. 启动训练
mkdir -p "${CKPT_DIR}" "${LOG_DIR}"
echo ""
echo "========================================"
echo "  Stage 1: 150 epoch 训练 (Staged 加速)"
echo "========================================"
echo "  配置: configs/train/stage1_150ep_viz.yaml"
echo "  数据: /dev/shm (S2) + /tmp (S1)"
echo "  预计速度: ~2.5 秒/step (vs 网络盘 7-10s)"
echo "  总时长: ~50 小时 (vs 网络盘 140h)"
echo "========================================"
echo ""
echo "[$(date)] 开始训练..."

torchrun --nproc_per_node=8 --nnodes=1 \
  --rdzv_backend=c10d --rdzv_endpoint=localhost:0 \
  train/train_stage1_dual.py \
  --config configs/train/stage1_150ep_viz.yaml \
  2>&1 | tee "${LOG_DIR}/train.log"

TRAIN_EXIT=$?

# 4. 训练结束后清理 staged 数据
echo ""
echo "[$(date)] ========================================"
if [ $TRAIN_EXIT -eq 0 ]; then
  echo "[$(date)] ✓ 训练正常完成"
else
  echo "[$(date)] ⚠ 训练异常退出 (exit code: $TRAIN_EXIT)"
fi
echo "[$(date)] 开始清理 staged 数据..."
echo "[$(date)] ========================================"

echo "[$(date)] 删除 /dev/shm S2 数据 (842GB)..."
rm -rf "${STAGED_ROOT}"
echo "[$(date)] ✓ /dev/shm 已清理"

echo "[$(date)] 删除 /tmp S1 数据 (168GB)..."
rm -rf "${S1_TMP}"
echo "[$(date)] ✓ /tmp 已清理"

echo ""
echo "[$(date)] ========================================"
echo "[$(date)] 全部完成！"
echo "[$(date)] ========================================"
echo "  Checkpoints: ${CKPT_DIR}/"
echo "  日志: ${LOG_DIR}/train.log"
echo "  Staged 数据: 已清理"
echo "[$(date)] ========================================"
