#!/usr/bin/env bash
# ============================================================
# Stage 1 ViT-S 训练 —— 混合存储(STAGED)版启动脚本
# ============================================================
# 数据从运存(/dev/shm 放 S2) + 本地盘(/tmp 放 S1)读取,绕开慢网络盘。
# data_root 指向门面目录 /dev/shm/zjliu17_ssl4eo (S2真目录 + S1软链)。
#
# ⭐ 自动清理: 训练正常结束/出错/被 Ctrl-C 时, trap 会自动删临时副本。
#    原始数据集 /csy-mix02/.../TrainData 永不触碰。
#
# 用法: bash run_stage1_vits_staged.sh
# ============================================================

set -e
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026

CONFIG=configs/train/stage1_vits_dual_staged.yaml
SESSION=s1vits_staged
LOG=/tmp/train8_vits_staged.log
CLEANUP=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/scripts/cleanup_staged_data.sh

# 校验门面目录就绪
if [ ! -d /dev/shm/zjliu17_ssl4eo/train/S2L2A ] || [ ! -e /dev/shm/zjliu17_ssl4eo/train/S1GRD ]; then
    echo "❌ 门面目录未就绪,先确认数据已搬完。"
    exit 1
fi

echo "============================================================"
echo "启动 Stage 1 ViT-S 训练 (混合存储版)"
echo "============================================================"
echo "  config:   $CONFIG"
echo "  data:     S2→/dev/shm(运存)  S1→/tmp(本地盘)"
echo "  session:  tmux $SESSION"
echo "  log:      $LOG"
echo "  清理:     训练结束自动调用 $CLEANUP --force"
echo "============================================================"

# 在 tmux 里跑训练。
# ⚠️ 不自动删数据: 崩溃/中断时保留,以便从 checkpoint 续训 + 后续 Stage 复用。
#    训练结束由外部监控通知用户,用户用 cleanup_staged_data.sh 手动清理。
tmux new-session -d -s "$SESSION" -x 220 -y 50
tmux send-keys -t "$SESSION" "cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026" C-m
tmux send-keys -t "$SESSION" "source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel" C-m
tmux send-keys -t "$SESSION" "export PATH=\"\$CONDA_PREFIX/bin:\$PATH\"" C-m
tmux send-keys -t "$SESSION" "unset CUDA_VISIBLE_DEVICES" C-m
tmux send-keys -t "$SESSION" \
    "OMP_NUM_THREADS=8 torchrun --nproc_per_node=8 --master_port=29603 -m train.train_stage1_vits --config $CONFIG 2>&1 | tee $LOG; echo; echo '============================================='; echo '训练已结束。如不再需要,运行以下命令清理临时副本:'; echo \"  bash $CLEANUP\"; echo '============================================='" C-m

echo "✅ 已在 tmux '$SESSION' 启动"
echo "   实时查看: tmux attach -t $SESSION"
echo "   清理(训练彻底用完后手动): bash $CLEANUP"
