#!/bin/bash
# ============================================================
# 内存安全监控 —— 防止占用运存导致全节点 OOM
# ============================================================
# 这是共享节点。我们的 S2 数据占用 ~841G 运存。
# 若别人突然起大任务、全节点可用内存过低,Linux OOM Killer 可能杀进程。
# 本脚本盯着全节点可用内存,低于阈值就告警(提醒你手动让路)。
#
# 用法: bash scripts/monitor_memory.sh   (建议在单独 tmux 里跑)
# ============================================================

THRESHOLD_GB=150   # 全节点可用内存低于此值告警

echo "============================================================"
echo "内存安全监控启动 (阈值: 可用 < ${THRESHOLD_GB}GB 告警)"
echo "============================================================"

while true; do
  AVAIL=$(free -g | awk '/Mem/{print $7}')
  SHM=$(df -BG /dev/shm | tail -1 | awk '{gsub("G","",$3); print $3}')
  TS=$(date '+%H:%M:%S')

  if [ "$AVAIL" -lt "$THRESHOLD_GB" ]; then
    echo "[$TS] ⚠️⚠️ 告警: 全节点可用内存仅 ${AVAIL}GB (<${THRESHOLD_GB}GB)!"
    echo "        我们的运存占用: ${SHM}GB"
    echo "        风险: 别人任务或你的训练可能被 OOM Killer 杀掉"
    echo "        建议: 考虑停训练 + 运行 cleanup_staged_data.sh 释放运存"
  else
    echo "[$TS] ✓ 可用内存 ${AVAIL}GB | 运存占用 ${SHM}GB | 正常"
  fi
  sleep 120
done
