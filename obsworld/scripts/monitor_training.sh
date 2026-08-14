#!/bin/bash
# Stage 1 训练实时监控脚本

cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026

LOG_FILE="logs/stage1_150ep_viz/train.log"

# 清屏
clear

echo "=========================================="
echo "  Stage 1 训练实时监控"
echo "=========================================="
echo ""

# 1. 训练进程状态
echo "【1. 训练进程】"
if ps aux | grep "train_stage1_dual.py" | grep -v grep > /dev/null; then
  echo "✓ 训练进程运行中"
  TRAIN_TIME=$(ps -p $(pgrep -f "train_stage1_dual.py" | head -1) -o etime= 2>/dev/null | xargs)
  echo "  运行时长: ${TRAIN_TIME:-未知}"
else
  echo "✗ 训练进程未运行"
fi
echo ""

# 2. 训练进度
echo "【2. 训练进度】"
if [ -f "$LOG_FILE" ]; then
  # 提取最新的 step 信息
  LATEST_STEP=$(grep -oE "step [0-9]+" "$LOG_FILE" | tail -1 | awk '{print $2}')
  if [ -n "$LATEST_STEP" ]; then
    PROGRESS=$(echo "scale=2; $LATEST_STEP / 71500 * 100" | bc)
    echo "  当前 step: $LATEST_STEP / 71,500 (${PROGRESS}%)"

    # 计算预计完成时间
    STEPS_REMAINING=$((71500 - LATEST_STEP))
    # 获取最近速度
    RECENT_SPEED=$(tail -100 "$LOG_FILE" | grep -oE "[0-9]+\.[0-9]+s/it" | tail -10 | awk '{sum+=$1; n++} END {if(n>0) printf "%.2f", sum/n}')
    if [ -n "$RECENT_SPEED" ]; then
      HOURS_REMAINING=$(echo "scale=1; $STEPS_REMAINING * $RECENT_SPEED / 3600" | bc)
      echo "  预计剩余: ${HOURS_REMAINING} 小时"
    fi
  else
    echo "  等待第一个 step..."
  fi
else
  echo "  日志文件未生成"
fi
echo ""

# 3. 训练速度和 Loss
echo "【3. 最近 5 步统计】"
if [ -f "$LOG_FILE" ]; then
  tail -200 "$LOG_FILE" | grep -E "S1=.*S2=" | tail -5 | while read line; do
    echo "  $line" | sed 's/.*step [0-9]*): //' | sed 's/it\[.*\], //'
  done

  echo ""
  echo "  平均速度: $(tail -100 "$LOG_FILE" | grep -oE "[0-9]+\.[0-9]+s/it" | tail -10 | awk '{sum+=$1; n++} END {if(n>0) printf "%.2f s/step", sum/n}')"
fi
echo ""

# 4. GPU 使用
echo "【4. GPU 状态】"
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader | \
  awk -F, '{printf "  GPU%s: %3s利用率  %5s/%5s显存  %s°C\n", $1, $2, $3, $4, $5}'
echo ""

# 5. Checkpoints
echo "【5. 已保存 Checkpoints】"
CKPT_DIR="checkpoints/stage1_150ep_viz"
if [ -d "$CKPT_DIR" ]; then
  CKPT_COUNT=$(ls -1 "$CKPT_DIR"/*.pt 2>/dev/null | wc -l)
  echo "  已保存: $CKPT_COUNT 个"
  if [ $CKPT_COUNT -gt 0 ]; then
    echo "  最新: $(ls -t "$CKPT_DIR"/*.pt 2>/dev/null | head -1 | xargs basename)"
  fi
else
  echo "  暂无 checkpoint"
fi
echo ""

# 6. 可视化
echo "【6. TensorBoard】"
if ps aux | grep "tensorboard.*6006" | grep -v grep > /dev/null; then
  echo "  ✓ TensorBoard 运行中"
  echo "  访问: http://$(hostname -I | awk '{print $1}'):6006"
else
  echo "  ✗ TensorBoard 未运行"
  echo "  启动: tensorboard --logdir logs/stage1_150ep_viz --port 6006 --bind_all"
fi
echo ""

echo "=========================================="
echo "监控命令:"
echo "  实时日志: tail -f $LOG_FILE"
echo "  GPU 监控: watch -n 1 nvidia-smi"
echo "  重新运行: bash scripts/monitor_training.sh"
echo "=========================================="
