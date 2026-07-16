#!/bin/bash
#SBATCH --job-name=stage1_5_60k
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --gres=gpu:8
#SBATCH --time=48:00:00

set -e

echo "=========================================="
echo "Stage 1.5 训练启动（60k steps）"
echo "=========================================="
echo "时间: $(date)"
echo "配置: stage1_5_dual_conditioned_vits_60k.yaml"
echo "目标: 60,000 steps ≈ 126 全季覆盖 epoch"
echo "预计耗时: ~33 小时（按 2.0s/step 估算）"
echo "=========================================="
echo ""

# 环境变量
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export OMP_NUM_THREADS=8
export PYTHONPATH=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026:$PYTHONPATH

# Conda 环境
source /csy-opt/cog8/zjliu17/miniconda3/etc/profile.d/conda.sh
conda activate WorldModel
export PATH="$CONDA_PREFIX/bin:$PATH"

# 配置文件
CONFIG="configs/train/stage1_5_dual_conditioned_vits_60k.yaml"
LOG="/tmp/train_stage1_5_60k2.log"

# 创建必要目录
mkdir -p checkpoints/stage1_5_dual_conditioned_vits_60k2
mkdir -p logs/stage1_5_dual_conditioned_vits_60k2

echo "配置文件: $CONFIG"
echo "日志文件: $LOG"
echo ""
echo "开始训练..."
echo ""

# 启动训练
OMP_NUM_THREADS=8 torchrun \
    --nproc_per_node=8 \
    --master_port=29604 \
    -m train.train_stage1_5_dual_conditioned \
    --config $CONFIG \
    2>&1 | tee $LOG

echo ""
echo "=========================================="
echo "训练完成！"
echo "时间: $(date)"
echo "=========================================="
echo ""
echo "Checkpoint 位置:"
echo "  checkpoints/stage1_5_dual_conditioned_vits_60k2/"
echo ""
echo "TensorBoard 日志:"
echo "  logs/stage1_5_dual_conditioned_vits_60k2/"
echo ""
echo "查看训练日志:"
echo "  tail -f $LOG"
echo ""
