#!/usr/bin/env python3
"""
build_geo_dem.py —— 从 SSL4EO-S12-v1.1 的 DEM 模态离线抽取地理先验 G（高程 + 坡度 + 坡向）

定位（见 18 §3.3 / 20 报告）：DEM 是 ObsWorld 柱2 动力学最干净、且数据集自带、零下载的
地理先验 G。SSL4EO 自带 DEM 模态（477 train shard，同 sample_key 对齐 S1/S2），目前未用。

本脚本（Stage1 阶段，先抽“逐样本标量统计”，不落 raster 省空间）：
- 读 DEM zarr 的 bands[0,0]（[264,264] int16，单位米，10m 像元）；
- 派生 slope（坡度,°）、aspect（坡向,°）：numpy 梯度，dx=dy=10m；
- 每样本输出标量统计：elevation mean/std/min/max、slope mean/std、aspect 的 sin/cos 均值
  （aspect 是角度，直接平均会在 0/360 处出错，故存 sin/cos）；
- 全部带 field_mask（DEM 有效性），无 NaN。

隔离/安全：不覆盖 phi_processed/；输出新目录 geo_processed/{split}/DEM/；
只读输入、CPU/IO-only、不占 GPU。建议 nice -n 19 ionice -c3 后台跑。

说明：raster 级 DEM/slope（供 dynamics 像素级 G）留到 Stage2 真正需要时再抽，避免现在占空间。
"""
import argparse
import io
import json
import time
import zipfile
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import webdataset as wds
import zarr
from zarr.storage import KVStore

PIXEL_M = 10.0  # SSL4EO DEM 像元 10m
DEM_NODATA_ABS = 1e6  # 异常哨兵


class ZipFileStore(MutableMapping):
    """与 build_phi_cache.py 一致的只读 zarr store（KVStore 包裹）。"""
    def __init__(self, zf):
        self.zf = zf

    def __getitem__(self, k):
        try:
            return self.zf.read(k)
        except KeyError:
            raise KeyError(k)

    def __contains__(self, k):
        try:
            self.zf.getinfo(k); return True
        except KeyError:
            return False

    def keys(self):
        return iter(self.zf.namelist())

    def __iter__(self):
        return self.keys()

    def __len__(self):
        return len(self.zf.namelist())

    def __setitem__(self, k, v):
        raise NotImplementedError

    def __delitem__(self, k):
        raise NotImplementedError


def derive_slope_aspect(dem: np.ndarray, px: float = PIXEL_M):
    """由高程图派生坡度(°)与坡向(°)。dem: [H,W] float。"""
    dzdy, dzdx = np.gradient(dem, px, px)  # 注意 np.gradient 返回 (axis0=y, axis1=x)
    slope_rad = np.arctan(np.hypot(dzdx, dzdy))
    slope_deg = np.degrees(slope_rad)
    # 坡向：从正北顺时针，0-360；平地(梯度~0)坡向无意义，单独标记
    aspect_rad = np.arctan2(dzdy, -dzdx)
    aspect_deg = (np.degrees(aspect_rad) + 360.0) % 360.0
    flat = np.hypot(dzdx, dzdy) < 1e-6
    return slope_deg, aspect_deg, flat


def extract_geo_record(sample_key: str, zarr_bytes: bytes) -> Dict[str, Any]:
    zf = zipfile.ZipFile(io.BytesIO(zarr_bytes))
    g = zarr.open(KVStore(ZipFileStore(zf)), mode='r')
    b = g['bands'][...]                       # [1,1,264,264] int16
    dem = np.asarray(b[0, 0], dtype=np.float32)
    valid = np.isfinite(dem) & (np.abs(dem) < DEM_NODATA_ABS)
    rec: Dict[str, Any] = {'sample_key': sample_key}
    if valid.sum() < 16:
        # DEM 几乎全无效
        rec.update({
            'dem_mean': np.nan, 'dem_std': np.nan, 'dem_min': np.nan, 'dem_max': np.nan,
            'slope_mean': np.nan, 'slope_std': np.nan,
            'aspect_sin': np.nan, 'aspect_cos': np.nan,
            'dem_valid': 0,
        })
        return rec
    dem_v = dem[valid]
    slope, aspect, flat = derive_slope_aspect(np.nan_to_num(dem, nan=float(dem_v.mean())))
    sl_v = slope[valid]
    # aspect 仅在非平地处有意义
    asp_mask = valid & (~flat)
    if asp_mask.sum() > 0:
        a = np.radians(aspect[asp_mask])
        asin, acos = float(np.sin(a).mean()), float(np.cos(a).mean())
    else:
        asin, acos = 0.0, 0.0
    rec.update({
        'dem_mean': float(dem_v.mean()), 'dem_std': float(dem_v.std()),
        'dem_min': float(dem_v.min()), 'dem_max': float(dem_v.max()),
        'slope_mean': float(sl_v.mean()), 'slope_std': float(sl_v.std()),
        'aspect_sin': asin, 'aspect_cos': acos,
        'dem_valid': 1,
    })
    return rec


def process_shard(shard_path: str) -> pd.DataFrame:
    records = []
    for sample in wds.WebDataset(shard_path):
        try:
            key = sample['__key__']
            records.append(extract_geo_record(key, sample['zarr.zip']))
        except Exception as e:
            print(f"  Warning: {sample.get('__key__','?')} failed: {e}", flush=True)
            continue
    return pd.DataFrame(records)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-root', default='/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1')
    ap.add_argument('--split', default='train', choices=['train', 'val'])
    ap.add_argument('--max-shards', type=int, default=2, help='小样本默认 2；全量用 -1')
    ap.add_argument('--out-name', default='geo_processed')
    ap.add_argument('--resume', action='store_true')
    args = ap.parse_args()

    data_dir = Path(args.data_root) / args.split / 'DEM'
    out_dir = Path(args.data_root) / args.out_name / args.split / 'DEM'
    out_dir.mkdir(parents=True, exist_ok=True)
    progress_path = out_dir.parent.parent / f'_geo_dem_progress_{args.split}.json'

    shards = sorted(data_dir.glob('*.tar'))
    if args.max_shards is not None and args.max_shards >= 0:
        shards = shards[:args.max_shards]

    print("=" * 70)
    print(f"DEM 地理先验抽取 | split={args.split} | shards={len(shards)} | resume={args.resume}")
    print(f"输出: {out_dir}  进度: {progress_path}")
    print("=" * 70)

    total = 0
    valid_dem = 0
    t0 = time.time()
    for i, sp in enumerate(shards):
        out_file = out_dir / f"{sp.stem}_geo_dem.parquet"
        if args.resume and out_file.exists():
            print(f"[skip] {sp.name}", flush=True); continue
        print(f"[shard {i+1}/{len(shards)}] {sp.name} ...", flush=True)
        df = process_shard(str(sp))
        if df.empty:
            print("  (空)"); continue
        df.to_parquet(out_file, index=False, compression='snappy')
        total += len(df)
        valid_dem += int(df['dem_valid'].sum())
        done = i + 1
        elapsed = time.time() - t0
        eta = (elapsed / done) * (len(shards) - done) / 60.0
        prog = {'split': args.split, 'shards_total': len(shards), 'shards_done': done,
                'pct': round(100.0 * done / len(shards), 2), 'last_shard': sp.name,
                'cum_samples': total, 'cum_dem_valid': valid_dem,
                'elapsed_min': round(elapsed / 60.0, 1), 'eta_min': round(eta, 1),
                'updated': time.strftime('%Y-%m-%d %H:%M:%S')}
        with open(progress_path, 'w') as f:
            json.dump(prog, f, indent=2, ensure_ascii=False)
        print(f"  写入 {out_file.name}: {len(df)} | {done}/{len(shards)} ({prog['pct']}%) ETA {eta:.0f}min", flush=True)

    stats = {'split': args.split, 'n_shards': len(shards), 'n_samples': total,
             'dem_valid': valid_dem, 'dem_valid_rate': round(valid_dem / max(total, 1), 4),
             'fields': ['dem_mean', 'dem_std', 'dem_min', 'dem_max', 'slope_mean',
                        'slope_std', 'aspect_sin', 'aspect_cos', 'dem_valid'],
             'note': 'G 地理先验逐样本标量；raster 级留待 Stage2'}
    with open(out_dir.parent.parent / f'_geo_dem_stats_{args.split}.json', 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print("\n=== 统计 ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == '__main__':
    main()
