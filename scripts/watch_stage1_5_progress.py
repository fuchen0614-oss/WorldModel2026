#!/usr/bin/env python3
"""
watch_stage1_5_progress.py —— Stage 1.5 方案A 训练进度可视化

读取 TensorBoard event 文件，打印带进度条的训练状态：
step/epoch 进度、各 loss 曲线趋势、ETA。支持 --loop 持续刷新。

用法：
  python scripts/watch_stage1_5_progress.py            # 看一次
  python scripts/watch_stage1_5_progress.py --loop 30  # 每 30s 刷新（Ctrl-C 退出）
"""
import argparse
import glob
import os
import time

LOG_DIR = '/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs/stage1_5_film'
MAX_STEPS = 30000
STEPS_PER_EPOCH = 119.125  # 243968 样本 / batch 2048


def bar(pct, width=32):
    filled = int(round(pct / 100.0 * width))
    return '█' * filled + '░' * (width - filled)


def load_scalars(log_dir):
    """从 TensorBoard event 文件读取所有 scalar，返回 {tag: [(step, value), ...]}。"""
    try:
        from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    except ImportError:
        return None, "未安装 tensorboard，无法解析 event 文件"
    files = glob.glob(os.path.join(log_dir, 'events.out.tfevents.*'))
    if not files:
        return None, f"未找到 event 文件: {log_dir}"
    ea = EventAccumulator(log_dir, size_guidance={'scalars': 0})
    ea.Reload()
    out = {}
    for tag in ea.Tags().get('scalars', []):
        out[tag] = [(s.step, s.value) for s in ea.Scalars(tag)]
    return out, None


def trend(series, n=5):
    """返回最近值 + 简易趋势箭头（对比 n 步前）。"""
    if not series:
        return "—", ""
    last = series[-1][1]
    if len(series) > n:
        prev = series[-1 - n][1]
        arrow = "↓" if last < prev else ("↑" if last > prev else "→")
    else:
        arrow = ""
    return f"{last:.4f}", arrow


def render(log_dir):
    lines = []
    lines.append("=" * 60)
    lines.append(f" Stage 1.5 方案A 训练进度  @ {time.strftime('%H:%M:%S')}")
    lines.append("=" * 60)

    scalars, err = load_scalars(log_dir)
    if err:
        lines.append(f"  {err}")
        lines.append("=" * 60)
        return "\n".join(lines)

    total_series = scalars.get('train/total', [])
    if not total_series:
        lines.append("  暂无训练数据（训练可能刚启动）")
        lines.append("=" * 60)
        return "\n".join(lines)

    step = total_series[-1][0]
    pct = 100.0 * step / MAX_STEPS
    epoch = step / STEPS_PER_EPOCH
    lines.append(f"  进度: [{bar(pct)}] {pct:5.1f}%")
    lines.append(f"  step {step:>6}/{MAX_STEPS}  |  epoch {epoch:6.1f}/{MAX_STEPS/STEPS_PER_EPOCH:.0f}")
    lines.append("-" * 60)

    # 各 loss
    for tag, label in [
        ('train/total', 'total     '),
        ('train/mae_s2', 'mae_s2    '),
        ('train/mae_s1', 'mae_s1    '),
        ('train/consistency', 'InfoNCE   '),
        ('train/decorr', 'decorr    '),
        ('train/lr', 'lr        '),
    ]:
        val, arrow = trend(scalars.get(tag, []))
        lines.append(f"  {label} {val:>10} {arrow}")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log-dir', default=LOG_DIR)
    ap.add_argument('--loop', type=int, default=0, help='秒；>0 时持续刷新')
    args = ap.parse_args()

    if args.loop > 0:
        try:
            while True:
                os.system('clear')
                print(render(args.log_dir))
                time.sleep(args.loop)
        except KeyboardInterrupt:
            print("\n已退出。")
    else:
        print(render(args.log_dir))


if __name__ == '__main__':
    main()
