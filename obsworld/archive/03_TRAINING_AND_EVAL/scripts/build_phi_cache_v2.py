#!/usr/bin/env python3
"""
SSL4EO-S12 成像条件（phi）字段预处理脚本 - V2 优化版

V2 优化：
1. 修复时间戳单位（纳秒 → 秒）
2. 新增 season 字段推导
3. 新增 sun_elevation 计算（可选）
"""

import argparse
import io
import json
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

import numpy as np
import pandas as pd
import zarr
from tqdm import tqdm
import webdataset as wds
from zarr.storage import KVStore


class ZipFileStore:
    """Zarr store wrapper for ZipFile."""
    def __init__(self, zipfile_obj):
        self.zf = zipfile_obj

    def __getitem__(self, key):
        return self.zf.read(key)

    def __contains__(self, key):
        return key in self.zf.namelist()

    def __iter__(self):
        return iter(self.zf.namelist())

    def keys(self):
        return self.zf.namelist()


def get_season_from_timestamp(timestamp_sec: float, latitude: float) -> str:
    """
    从时间戳和纬度推导季节
    
    Args:
        timestamp_sec: Unix 时间戳（秒）
        latitude: 纬度
    
    Returns:
        季节字符串：'spring', 'summer', 'autumn', 'winter'
    """
    try:
        dt = datetime.fromtimestamp(timestamp_sec)
        month = dt.month
        
        # 北半球 vs 南半球
        if latitude >= 0:  # 北半球
            if month in [3, 4, 5]:
                return 'spring'
            elif month in [6, 7, 8]:
                return 'summer'
            elif month in [9, 10, 11]:
                return 'autumn'
            else:
                return 'winter'
        else:  # 南半球（季节相反）
            if month in [3, 4, 5]:
                return 'autumn'
            elif month in [6, 7, 8]:
                return 'winter'
            elif month in [9, 10, 11]:
                return 'spring'
            else:
                return 'summer'
    except:
        return 'unknown'


def extract_phi_from_zarr(zarr_bytes: bytes, modality: str, sample_key: str) -> Dict[str, Any]:
    """从 zarr.zip 中提取成像条件字段 phi（V2优化版）"""
    
    # 打开 zarr
    bio = io.BytesIO(zarr_bytes)
    zf = zipfile.ZipFile(bio, 'r')
    store = KVStore(ZipFileStore(zf))
    root = zarr.open(store, mode='r')

    # 初始化
    phi = {
        'sample_key': sample_key,
        'modality': modality,
        'sensor': None,
        'product_level': None,
    }

    field_mask = {
        'sample_key': 1, 'modality': 1, 'sensor': 0, 'product_level': 0,
        'center_lat': 0, 'center_lon': 0, 'crs': 0, 'time': 0,
        'cloud_mask': 0, 'cloud_cover': 0, 'bands_info': 0,
        'spatial_resolution': 0, 'season': 0,
    }

    # 根据模态设置固定字段
    if modality.startswith('S2'):
        phi['sensor'] = 'Sentinel-2'
        field_mask['sensor'] = 1
        if 'L2A' in modality:
            phi['product_level'] = 'L2A'
            field_mask['product_level'] = 1
        elif 'L1C' in modality:
            phi['product_level'] = 'L1C'
            field_mask['product_level'] = 1
        elif 'RGB' in modality:
            phi['product_level'] = 'RGB'
            field_mask['product_level'] = 1
    elif modality.startswith('S1'):
        phi['sensor'] = 'Sentinel-1'
        phi['product_level'] = 'GRD'
        field_mask['sensor'] = 1
        field_mask['product_level'] = 1
    elif modality == 'DEM':
        phi['sensor'] = 'DEM'
        phi['product_level'] = 'processed'
        field_mask['sensor'] = 1
        field_mask['product_level'] = 1

    # 提取空间信息
    try:
        phi['center_lat'] = float(root['center_lat'][()])
        phi['center_lon'] = float(root['center_lon'][()])
        field_mask['center_lat'] = 1
        field_mask['center_lon'] = 1
    except:
        phi['center_lat'] = None
        phi['center_lon'] = None

    # 提取 CRS
    try:
        phi['crs'] = int(root['crs'][()])
        field_mask['crs'] = 1
    except:
        phi['crs'] = None

    # ✅ V2优化：提取时间戳（纳秒 → 秒）
    try:
        time = np.array(root['time'])  # [4] int64 纳秒
        # 转换为秒
        phi['time_0'] = int(time[0] / 1e9)
        phi['time_1'] = int(time[1] / 1e9)
        phi['time_2'] = int(time[2] / 1e9)
        phi['time_3'] = int(time[3] / 1e9)
        field_mask['time'] = 1
        
        # ✅ V2新增：推导季节
        if phi['center_lat'] is not None:
            phi['season_0'] = get_season_from_timestamp(phi['time_0'], phi['center_lat'])
            phi['season_1'] = get_season_from_timestamp(phi['time_1'], phi['center_lat'])
            phi['season_2'] = get_season_from_timestamp(phi['time_2'], phi['center_lat'])
            phi['season_3'] = get_season_from_timestamp(phi['time_3'], phi['center_lat'])
            field_mask['season'] = 1
        else:
            phi['season_0'] = None
            phi['season_1'] = None
            phi['season_2'] = None
            phi['season_3'] = None
    except Exception as e:
        phi['time_0'] = None
        phi['time_1'] = None
        phi['time_2'] = None
        phi['time_3'] = None
        phi['season_0'] = None
        phi['season_1'] = None
        phi['season_2'] = None
        phi['season_3'] = None

    # 提取云覆盖统计（仅光学模态有）
    try:
        cloud_mask = np.array(root['cloud_mask'])  # [4, H, W]
        phi['cloud_cover_0'] = float((cloud_mask[0] > 0).mean())
        phi['cloud_cover_1'] = float((cloud_mask[1] > 0).mean())
        phi['cloud_cover_2'] = float((cloud_mask[2] > 0).mean())
        phi['cloud_cover_3'] = float((cloud_mask[3] > 0).mean())
        field_mask['cloud_mask'] = 1
        field_mask['cloud_cover'] = 1
    except:
        phi['cloud_cover_0'] = None
        phi['cloud_cover_1'] = None
        phi['cloud_cover_2'] = None
        phi['cloud_cover_3'] = None

    # 提取图像形状
    try:
        bands = np.array(root['bands'])
        phi['num_timesteps'] = int(bands.shape[0])
        phi['num_bands'] = int(bands.shape[1])
        phi['height'] = int(bands.shape[2])
        phi['width'] = int(bands.shape[3])
        field_mask['bands_info'] = 1
    except:
        phi['num_timesteps'] = None
        phi['num_bands'] = None
        phi['height'] = None
        phi['width'] = None

    # 空间分辨率
    if modality in ['S2L2A', 'S1GRD', 'S2RGB']:
        phi['spatial_resolution'] = 10.0
        field_mask['spatial_resolution'] = 1
    else:
        phi['spatial_resolution'] = None

    # 样本ID
    try:
        phi['sample_id'] = str(root['sample'][()])
    except:
        phi['sample_id'] = sample_key

    store.close()

    phi['_field_mask'] = json.dumps(field_mask)

    return phi


def process_shard(shard_path: str, modality: str, output_dir: Path) -> pd.DataFrame:
    """处理单个 tar shard"""
    phi_records = []
    dataset = wds.WebDataset(shard_path)

    for sample in dataset:
        try:
            key = sample['__key__']
            zarr_bytes = sample['zarr.zip']
            phi = extract_phi_from_zarr(zarr_bytes, modality, key)
            phi_records.append(phi)
        except Exception as e:
            print(f"Warning: Failed to process sample {key}: {e}")
            continue

    if phi_records:
        df = pd.DataFrame(phi_records)
    else:
        df = pd.DataFrame()

    return df


def main():
    parser = argparse.ArgumentParser(description='预处理 SSL4EO-S12 成像条件字段（V2优化版）')
    parser.add_argument('--data-root', type=str,
                        default='/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1')
    parser.add_argument('--modality', type=str, default='S2L2A',
                        choices=['S2L2A', 'S2L1C', 'S2RGB', 'S1GRD', 'DEM', 'LULC', 'NDVI'])
    parser.add_argument('--split', type=str, default='train',
                        choices=['train', 'val'])
    parser.add_argument('--max-shards', type=int, default=None)
    parser.add_argument('--force-reprocess', action='store_true',
                        help='强制重新处理已存在的文件')

    args = parser.parse_args()

    data_dir = Path(args.data_root) / args.split / args.modality
    output_root = Path(args.data_root) / 'phi_processed_v2' / args.split / args.modality
    output_root.mkdir(parents=True, exist_ok=True)

    shard_files = sorted(data_dir.glob('*.tar'))

    if args.max_shards:
        shard_files = shard_files[:args.max_shards]

    print("="*80)
    print(f"SSL4EO-S12 成像条件字段预处理 V2（优化版）")
    print("="*80)
    print(f"数据根目录: {args.data_root}")
    print(f"模态: {args.modality}")
    print(f"划分: {args.split}")
    print(f"找到 {len(shard_files)} 个 tar shards")
    print(f"输出目录: {output_root}")
    print("="*80)
    print()

    all_stats = {
        'version': 'v2',
        'improvements': ['时间戳单位修复（纳秒→秒）', '新增season字段'],
        'data_root': str(args.data_root),
        'modality': args.modality,
        'split': args.split,
        'total_shards': len(shard_files),
        'processed_shards': 0,
        'total_samples': 0,
        'failed_shards': [],
    }

    for shard_path in tqdm(shard_files, desc='Processing shards'):
        shard_name = shard_path.stem
        output_file = output_root / f'{shard_name}_phi.parquet'

        if output_file.exists() and not args.force_reprocess:
            print(f"跳过已存在: {output_file.name}")
            continue

        try:
            df = process_shard(str(shard_path), args.modality, output_root)

            if not df.empty:
                df.to_parquet(output_file, index=False, compression='snappy')
                all_stats['processed_shards'] += 1
                all_stats['total_samples'] += len(df)
                print(f"✓ {shard_name}: {len(df)} samples")
            else:
                print(f"✗ {shard_name}: 无有效样本")
                all_stats['failed_shards'].append(shard_name)

        except Exception as e:
            print(f"✗ {shard_name}: {e}")
            all_stats['failed_shards'].append(shard_name)

    stats_file = output_root / '_processing_stats.json'
    with open(stats_file, 'w') as f:
        json.dump(all_stats, f, indent=2)

    print("\n" + "="*80)
    print("预处理完成（V2优化版）！")
    print(f"  处理的 shards: {all_stats['processed_shards']} / {all_stats['total_shards']}")
    print(f"  总样本数: {all_stats['total_samples']}")
    print(f"  失败的 shards: {len(all_stats['failed_shards'])}")
    print(f"  统计文件: {stats_file}")
    print("="*80)


if __name__ == '__main__':
    main()
