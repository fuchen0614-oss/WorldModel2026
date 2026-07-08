#!/usr/bin/env python3
"""
build_phi_v3_s1geom.py —— 为 S1GRD 构建 phi v3 的 SAR 几何字段（asc/desc + relative_orbit + satellite）

设计（见 任务描述相关/19 + outputs/20_S1几何字段审查报告.md）：
- 数据源：S1GRD zarr 的 `file_id`（完整原始 S1 产品 ID，每时间片一个）。
- 离线解析：卫星 / 绝对轨道号 → 相对轨道（ESA 公式）；绝对轨道 + 成像时刻 + center_lon → asc/desc（LST 法）。
- incidence angle：STAC 不暴露、annotation 反查昂贵 → 仅占位，field_mask=0，不写真值。

隔离保证：
- **不修改** build_phi_cache.py；**不覆盖** phi_processed/。
- 输出到新目录 phi_processed_v3_s1geom/{split}/S1GRD/。
- 与现有 phi 对齐：sample_key = tar __key__；时间片 0..3 与 zarr 原生顺序一致（与 season_t 等对齐）。

缺失处理（规避 [[phi-parquet-nan-int-fields]] 坑）：
- 类别/整数列用 -1 哨兵表示缺失；几何有效性单列 s1_geom_valid_t（1/0）。
- 不产生 NaN（incidence 占位列用 float NaN，但有独立 field_mask，且 encoder 走 missing embedding）。

只读输入、CPU/IO-only、不占 GPU。建议 nice -n 19 ionice -c3 后台跑。
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import webdataset as wds

# 复用 audit 脚本的解析函数
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_s1_metadata import parse_s1_product_id, orbit_direction_from_lst, ZipFileStore  # noqa: E402

import io
import zipfile
import zarr
from zarr.storage import KVStore

ORBIT_CODE = {'descending': 0, 'ascending': 1}   # -1 = missing
SAT_CODE = {'S1A': 0, 'S1B': 1}                   # -1 = missing


def read_fileid_and_lon(zarr_bytes: bytes) -> Dict[str, Any]:
    """从 S1GRD zarr 字节流读取 file_id[4] 与 center_lon（标量）。"""
    zf = zipfile.ZipFile(io.BytesIO(zarr_bytes))
    g = zarr.open(KVStore(ZipFileStore(zf)), mode='r')
    fid = g['file_id'][...]
    fid = fid.tolist() if fid.ndim else [fid.item()]
    lon = g['center_lon'][...]
    lon = float(lon.item()) if lon.ndim == 0 else float(lon[0])
    return {'file_id': fid, 'center_lon': lon}


def build_s1geom_record(sample_key: str, file_ids: List[str], center_lon: float,
                        n_steps: int = 4) -> Dict[str, Any]:
    """对单个样本的 4 个时间片产品 ID，构造 phi v3 几何字段记录。"""
    rec: Dict[str, Any] = {'sample_key': sample_key}
    for t in range(n_steps):
        pid = file_ids[t] if t < len(file_ids) else None
        p = parse_s1_product_id(pid) if pid else None
        if p:
            od = orbit_direction_from_lst(p['start'], center_lon)
            rec[f's1_orbit_direction_{t}'] = ORBIT_CODE.get(od, -1)
            rec[f's1_relative_orbit_{t}'] = int(p['rel_orbit'])
            rec[f's1_satellite_{t}'] = SAT_CODE.get(p['mission'], -1)
            rec[f's1_abs_orbit_{t}'] = int(p['abs_orbit'])
            rec[f's1_geom_valid_{t}'] = 1 if od is not None else 0
        else:
            rec[f's1_orbit_direction_{t}'] = -1
            rec[f's1_relative_orbit_{t}'] = -1
            rec[f's1_satellite_{t}'] = -1
            rec[f's1_abs_orbit_{t}'] = -1
            rec[f's1_geom_valid_{t}'] = 0
        # incidence 占位（不取真值），field_mask=0
        rec[f's1_incidence_angle_{t}'] = np.nan
        rec[f's1_incidence_valid_{t}'] = 0
    return rec


def process_shard(shard_path: str, n_steps: int = 4) -> pd.DataFrame:
    records = []
    for sample in wds.WebDataset(shard_path):
        try:
            key = sample['__key__']
            zb = sample['zarr.zip']
            info = read_fileid_and_lon(zb)
            records.append(build_s1geom_record(key, info['file_id'], info['center_lon'], n_steps))
        except Exception as e:
            print(f"  Warning: sample {sample.get('__key__','?')} failed: {e}", flush=True)
            continue
    return pd.DataFrame(records)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-root', default='/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1')
    ap.add_argument('--split', default='train', choices=['train', 'val'])
    ap.add_argument('--max-shards', type=int, default=2, help='小样本默认 2；全量用 -1')
    ap.add_argument('--out-name', default='phi_processed_v3_s1geom')
    ap.add_argument('--resume', action='store_true', help='跳过已生成 parquet 的 shard（断点续跑）')
    args = ap.parse_args()

    data_dir = Path(args.data_root) / args.split / 'S1GRD'
    out_dir = Path(args.data_root) / args.out_name / args.split / 'S1GRD'
    out_dir.mkdir(parents=True, exist_ok=True)

    shards = sorted(data_dir.glob('*.tar'))
    if args.max_shards is not None and args.max_shards >= 0:
        shards = shards[:args.max_shards]

    # 进度文件：每完成一个 shard 落盘一次，供外部 watch/可视化
    progress_path = out_dir.parent.parent / f'_v3_s1geom_progress_{args.split}.json'

    print("=" * 70)
    print(f"phi v3 S1 几何字段构建 | split={args.split} | shards={len(shards)} | resume={args.resume}")
    print(f"输出: {out_dir}  (不覆盖 phi_processed/)")
    print(f"进度: {progress_path}")
    print("=" * 70)

    total = 0
    valid_geom = 0
    orbit_dist = {}
    t_start = time.time()
    for i, sp in enumerate(shards):
        out_file = out_dir / f"{sp.stem}_phi_s1geom.parquet"
        if args.resume and out_file.exists():
            print(f"[skip] {sp.name}（已存在）", flush=True)
            continue
        print(f"[shard {i+1}/{len(shards)}] {sp.name} ...", flush=True)
        df = process_shard(str(sp))
        if df.empty:
            print("  (空)"); continue
        df.to_parquet(out_file, index=False, compression='snappy')
        # 统计
        shard_valid = 0
        for t in range(4):
            v = int(df[f's1_geom_valid_{t}'].sum())
            shard_valid += v
            valid_geom += v
            total += len(df)
            for od in df[f's1_orbit_direction_{t}']:
                orbit_dist[int(od)] = orbit_dist.get(int(od), 0) + 1
        # 落盘进度
        done = i + 1
        elapsed = time.time() - t_start
        eta_min = (elapsed / done) * (len(shards) - done) / 60.0 if done else 0
        progress = {
            'split': args.split,
            'shards_total': len(shards),
            'shards_done': done,
            'pct': round(100.0 * done / len(shards), 2),
            'last_shard': sp.name,
            'last_samples': len(df),
            'cum_timestep_slots': total,
            'cum_geom_valid': valid_geom,
            'elapsed_min': round(elapsed / 60.0, 1),
            'eta_min': round(eta_min, 1),
            'updated': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        with open(progress_path, 'w') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
        print(f"  写入 {out_file.name}: {len(df)} 样本 | 进度 {done}/{len(shards)} ({progress['pct']}%) ETA {eta_min:.0f}min", flush=True)

    stats = {
        'split': args.split, 'n_shards': len(shards),
        'n_timestep_slots': total,
        'geom_valid_slots': valid_geom,
        'geom_valid_rate': round(valid_geom / max(total, 1), 4),
        'orbit_direction_code_dist': {str(k): v for k, v in orbit_dist.items()},
        'note': 'orbit_code: 0=descending,1=ascending,-1=missing; incidence 占位 field_mask=0',
    }
    with open(out_dir.parent.parent / f'_v3_s1geom_stats_{args.split}.json', 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print("\n=== 统计 ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == '__main__':
    main()
