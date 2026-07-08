#!/usr/bin/env python3
"""
watch_phi_v3_progress.py —— phi v3 / DEM 全量构建进度可视化

读取 build_phi_v3_s1geom.py 与 build_geo_dem.py 落盘的进度 JSON，
打印带进度条的状态。支持 --loop 持续刷新。

用法：
  # 看一次
  python scripts/watch_phi_v3_progress.py
  # 每 10s 刷新一次（Ctrl-C 退出）
  python scripts/watch_phi_v3_progress.py --loop 10
"""
import argparse
import json
import os
import time
from pathlib import Path

ROOT = '/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1'

# (任务名, 进度文件相对路径)
TASKS = [
    ('S1几何 train', 'phi_processed_v3_s1geom/_v3_s1geom_progress_train.json'),
    ('S1几何 val',   'phi_processed_v3_s1geom/_v3_s1geom_progress_val.json'),
    ('DEM    train', 'geo_processed/_geo_dem_progress_train.json'),
    ('DEM    val',   'geo_processed/_geo_dem_progress_val.json'),
]


def bar(pct, width=30):
    filled = int(round(pct / 100.0 * width))
    return '█' * filled + '░' * (width - filled)


def render(root):
    lines = []
    lines.append("=" * 64)
    lines.append(f" phi v3 / DEM 构建进度  @ {time.strftime('%H:%M:%S')}")
    lines.append("=" * 64)
    for name, rel in TASKS:
        p = Path(root) / rel
        if not p.exists():
            lines.append(f"  {name:14s} | 未开始")
            continue
        try:
            d = json.load(open(p))
        except Exception:
            lines.append(f"  {name:14s} | (读取中)")
            continue
        pct = d.get('pct', 0)
        done = d.get('shards_done', 0)
        tot = d.get('shards_total', 0)
        eta = d.get('eta_min', 0)
        upd = d.get('updated', '')
        lines.append(f"  {name:14s} |{bar(pct)}| {pct:5.1f}%  {done}/{tot}  ETA {eta:.0f}min")
        lines.append(f"  {'':14s} | 更新 {upd}")
    lines.append("=" * 64)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=ROOT)
    ap.add_argument('--loop', type=int, default=0, help='秒；>0 则持续刷新')
    args = ap.parse_args()
    if args.loop <= 0:
        print(render(args.root))
        return
    try:
        while True:
            os.system('clear')
            print(render(args.root))
            print(f"\n(每 {args.loop}s 刷新，Ctrl-C 退出)")
            time.sleep(args.loop)
    except KeyboardInterrupt:
        print("\n已退出")


if __name__ == '__main__':
    main()
