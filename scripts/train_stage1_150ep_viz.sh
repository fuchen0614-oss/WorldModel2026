#!/bin/bash
# Stage 1: 从初始权重训练 150 epoch，带可视化
# 150 epoch ≈ 71,500 steps (S2 视角 dual 模式，476.6 steps/epoch)
# 100 epoch (47,500 steps) 会额外保存带 epoch100 tag 的 checkpoint
set -e  # 只保留 -e，去掉 -u 避免 conda 变量问题

cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel 2>/dev/null || true

# 输出目录（已在配置文件中指定）
CKPT_DIR="checkpoints/stage1_150ep_viz"
LOG_DIR="logs/stage1_150ep_viz"

mkdir -p "${CKPT_DIR}" "${LOG_DIR}"

echo "=== Stage 1: 150 epoch 从初始权重训练 ==="
echo "  配置文件: configs/train/stage1_150ep_viz.yaml"
echo "  Checkpoint 目录: ${CKPT_DIR}"
echo "  日志目录: ${LOG_DIR}"
echo ""
echo "  训练参数:"
echo "    - 总步数: 71,500 steps (150 epoch)"
echo "    - Checkpoint 间隔: 每 2500 steps (共 29 个)"
echo "    - 100 epoch 重点保存: checkpoint_epoch100_step_47500.pt"
echo "    - 可视化间隔: 每 500 steps"
echo ""
echo "  查看训练:"
echo "    - 实时日志: tail -f ${LOG_DIR}/train.log"
echo "    - TensorBoard: tensorboard --logdir ${LOG_DIR}"
echo ""
echo "  预计训练时间: ~150 小时 (8×H200, 约6天)"
echo ""

# 直接启动，不等待用户确认（适合后台运行）
echo "开始训练..."
echo ""

torchrun --nproc_per_node=8 --nnodes=1 \
  --rdzv_backend=c10d --rdzv_endpoint=localhost:0 \
  train/train_stage1_dual.py \
  --config configs/train/stage1_150ep_viz.yaml \
  2>&1 | tee "${LOG_DIR}/train.log"

echo ""
echo "=== 训练完成 ==="
echo "Checkpoints 位置: ${CKPT_DIR}/"
echo "  - 常规: checkpoint_step_{2500,5000,...,71500}.pt"
echo "  - 100 epoch: checkpoint_epoch100_step_47500.pt"
echo "  - 150 epoch: checkpoint_epoch150_step_71500.pt"
echo ""
echo "可视化结果: ${LOG_DIR}/visualizations/"

