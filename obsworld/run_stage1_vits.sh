#!/usr/bin/env bash
# ============================================================
# Stage 1 ViT-S/16 双模态 MAE 预训练启动脚本
# ============================================================
# ⚠️ 注意：本脚本目前不会自动启动训练。当你准备好启动时，
#         直接执行本脚本即可（它会在 tmux 会话 s1vits 内前台启动）。
#
# 当前状态（写于本脚本创建时）：
#   - Stage 1.5 仍在 tmux 会话 s15 跑（不要打扰它）
#   - 本 Stage 1 重训需要 8 张卡，会和 Stage 1.5 抢资源
#   - 启动前请确认 Stage 1.5 已结束或你愿意停掉它
#
# 配置：
#   model:      ViT-S/16 (embed=384, depth=12, heads=6, ~22M params)
#   batch:      每卡 512 × 8 卡 = global 4096
#   max_steps:  95,000 (= 200 S2 patch-epoch)
#   ckpt:       每 2500 step 一个，在 47500/71500/95000 额外复制 epoch100/150/200 tag
#   wall-clock: 预计 8-20 小时（取决于实测 throughput）
# ============================================================

set -e
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026

# 检查 Stage 1.5 是否还在跑（避免抢资源）
if pgrep -f "train_stage1_5_film" > /dev/null; then
    echo "❌ 检测到 Stage 1.5 还在跑（PID: $(pgrep -f train_stage1_5_film | head))"
    echo "   先用以下命令停掉它："
    echo "     tmux send-keys -t s15 C-c"
    echo "     pkill -9 -f train_stage1_5_film"
    echo "   或者等它跑完再启动本脚本。"
    exit 1
fi

# 检查 GPU 是否空闲
USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '{s+=$1}END{print s}')
if [ "$USED" -gt 1000 ]; then
    echo "⚠️ 警告：GPU 上还有 ${USED} MiB 显存被占用，可能有其他进程。"
    echo "   建议先 nvidia-smi 检查后再启动。"
    read -p "  继续? (y/N) " yn
    [ "$yn" != "y" ] && exit 1
fi

CONFIG=configs/train/stage1_vits_dual.yaml
SESSION=s1vits
LOG=/tmp/train8_vits.log

echo "============================================================"
echo "启动 Stage 1 ViT-S 训练"
echo "============================================================"
echo "  config:  $CONFIG"
echo "  session: tmux $SESSION"
echo "  log:     $LOG"
echo ""
echo "进度查看："
echo "  tmux attach -t $SESSION              # 实时查看 (Ctrl+b d 退出)"
echo "  grep -E 'Step [0-9]+/' $LOG | tail   # 查 loss"
echo "  ls checkpoints/stage1_vits_dual/     # 看 ckpt"
echo "============================================================"
echo ""

# 启动 tmux 会话并运行训练（前台输出可通过 attach 实时看到）
tmux new-session -d -s "$SESSION" -x 220 -y 50
tmux send-keys -t "$SESSION" "cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026" C-m
tmux send-keys -t "$SESSION" "source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel" C-m
tmux send-keys -t "$SESSION" "export PATH=\"\$CONDA_PREFIX/bin:\$PATH\"" C-m
tmux send-keys -t "$SESSION" "unset CUDA_VISIBLE_DEVICES" C-m
tmux send-keys -t "$SESSION" \
    "OMP_NUM_THREADS=8 torchrun --nproc_per_node=8 --master_port=29601 -m train.train_stage1_vits --config $CONFIG 2>&1 | tee $LOG" C-m

echo "✅ 已在 tmux 会话 '$SESSION' 中启动训练"
echo ""
echo "实时查看："
echo "  tmux attach -t $SESSION"
echo ""
echo "首个 step 行出现需要 ~3-5 分钟（FSDP 初始化 + 首批数据加载）"
