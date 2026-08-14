#!/bin/bash
# Phi Leakage Probe 监控脚本

LOG_FILE="logs/eval_probes/phi_leakage_30k_run1.log"
PID_FILE="/tmp/phi_probe_pid.txt"

echo "3666622" > $PID_FILE

while true; do
    if [ ! -f "$LOG_FILE" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ 日志文件不存在"
        break
    fi

    # 检查进程是否还在运行
    PID=$(cat $PID_FILE 2>/dev/null)
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 进程已结束，检查结果..."

        # 检查是否成功完成
        if grep -q "最终结果对比" "$LOG_FILE"; then
            echo "🎉 验证完成！提取结果..."
            tail -100 "$LOG_FILE"
        else
            echo "⚠️ 进程异常退出，查看错误..."
            tail -50 "$LOG_FILE"
        fi
        break
    fi

    # 显示当前进度
    LAST_LINE=$(tail -1 "$LOG_FILE")
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 运行中: $LAST_LINE"

    # 每 5 分钟检查一次
    sleep 300
done
