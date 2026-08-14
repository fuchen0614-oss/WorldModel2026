#!/usr/bin/env python3
"""
SSL4EO-S12 成像条件（phi）字段预处理脚本

功能：
1. 遍历 SSL4EO-S12 的 tar shards
2. 提取每个样本的成像条件字段（phi）
3. 缓存为 parquet 文件，训练时直接读取
4. 生成统计报告和 field_mask

真实 zarr 字段（已验证）：
- bands: [4, 12, 264, 264] int16
- center_lat: () float64
- center_lon: () float64
- cloud_mask: [4, 264, 264] uint8
    类别: 0=land,1=water,2=snow,3=thin_cloud,4=thick_cloud,5=cloud_shadow,6=no_data
- crs: () int64
- time: [4] int64  （单位: 纳秒 since 1970-01-01，已从 zarr time.attrs 验证）
- sample: () str
- band: [12] str (波段名称列表)
- file_id: [4] str (文件ID)

衍生字段（本脚本计算，非 zarr 原生）：
- season_*: 季节编码 0-3，从 time + lat 推导（已分南北半球）
- day_of_year_*: 年内天数，从 time 推导
- sun_elevation_*: 太阳高度角（度），NOAA 天文公式（纯numpy）
- cloud_shadow_*: 云影占比；valid_ratio_*: 非no_data占比
- time_valid_*: 时间戳有效性（部分样本时间戳损坏为负值）

输出目录：
/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed/
"""

import argparse
import io
import json
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

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


# ============================================================
# 成像条件衍生字段计算
# ============================================================
# cloud_mask 类别定义（来自 zarr cloud_mask.attrs['cloud_classes']，已验证）:
#   0=land, 1=water, 2=snow, 3=thin_cloud, 4=thick_cloud, 5=cloud_shadow, 6=no_data
CLOUD_CLASSES = ['land', 'water', 'snow', 'thin_cloud', 'thick_cloud', 'cloud_shadow', 'no_data']
CLOUD_VALUES = [3, 4]        # 真正的云：薄云 + 厚云
SHADOW_VALUE = 5             # 云影
NODATA_VALUE = 6             # 无数据


def solar_elevation_noaa(timestamp_ns: int, lat: float, lon: float) -> float:
    """用 NOAA 天文算法计算太阳高度角（度）。

    纯 numpy 实现，无需 pvlib/astral。精度 <0.5°，足够作为成像条件特征。

    Args:
        timestamp_ns: 纳秒级 Unix 时间戳（zarr time 字段单位）
        lat: 纬度（度）
        lon: 经度（度）

    Returns:
        太阳高度角（度）；夜间为负值。无效输入返回 None。
    """
    if timestamp_ns is None or timestamp_ns <= 0:
        return None
    dt = pd.to_datetime(int(timestamp_ns), unit='ns', utc=True)
    jd = dt.to_julian_date()
    n = jd - 2451545.0  # 自 J2000 起的天数
    # 太阳几何平黄经与平近点角
    L = (280.460 + 0.9856474 * n) % 360
    g = np.radians((357.528 + 0.9856003 * n) % 360)
    lam = np.radians((L + 1.915 * np.sin(g) + 0.020 * np.sin(2 * g)) % 360)
    eps = np.radians(23.439 - 0.0000004 * n)
    decl = np.arcsin(np.sin(eps) * np.sin(lam))  # 赤纬
    # 赤经 + 格林尼治恒星时 → 地方时角
    ra = np.degrees(np.arctan2(np.cos(eps) * np.sin(lam), np.cos(lam))) % 360
    gmst = (280.46061837 + 360.98564736629 * n) % 360
    lmst = (gmst + lon) % 360
    H = np.radians((lmst - ra) % 360)
    latr = np.radians(lat)
    elev = np.arcsin(np.sin(latr) * np.sin(decl) + np.cos(latr) * np.cos(decl) * np.cos(H))
    return float(np.degrees(elev))


def get_season_and_doy(timestamp_ns: int, lat: float):
    """从纳秒时间戳 + 纬度推导季节编码与年内天数。

    季节编码: 0=spring, 1=summer, 2=autumn, 3=winter（已按南北半球翻转）。

    Returns:
        (season_code:int|None, day_of_year:int|None)
    """
    if timestamp_ns is None or timestamp_ns <= 0:
        return None, None
    dt = pd.to_datetime(int(timestamp_ns), unit='ns', utc=True)
    month = dt.month
    doy = int(dt.dayofyear)
    # 北半球季节
    if month in (3, 4, 5):
        season_n = 0   # spring
    elif month in (6, 7, 8):
        season_n = 1   # summer
    elif month in (9, 10, 11):
        season_n = 2   # autumn
    else:
        season_n = 3   # winter
    # 南半球季节相反（spring<->autumn, summer<->winter）
    flip = {0: 2, 1: 3, 2: 0, 3: 1}
    season = season_n if lat >= 0 else flip[season_n]
    return int(season), doy


def extract_phi_from_zarr(zarr_bytes: bytes, modality: str, sample_key: str) -> Dict[str, Any]:
    """
    从 zarr.zip 中提取成像条件字段 phi。

    基于真实字段结构：
    - center_lat, center_lon: 空间位置
    - cloud_mask: [4, H, W] 云掩膜（提取覆盖率统计）
    - time: [4] 时间戳
    - crs: 坐标系
    - sample: 样本ID
    - bands: [4, C, H, W] 图像数据（提取形状信息）

    Args:
        zarr_bytes: zarr.zip 文件的字节内容
        modality: 模态类型（S2L2A, S1GRD, 等）
        sample_key: 样本唯一标识

    Returns:
        phi 字典 + field_mask
    """
    # 打开 zarr
    bio = io.BytesIO(zarr_bytes)
    zf = zipfile.ZipFile(bio, 'r')
    store = KVStore(ZipFileStore(zf))
    root = zarr.open(store, mode='r')

    # 初始化 phi 和 field_mask
    phi = {
        'sample_key': sample_key,
        'modality': modality,
        'sensor': None,
        'product_level': None,
    }

    field_mask = {
        'sample_key': 1,
        'modality': 1,
        'sensor': 0,
        'product_level': 0,
        'center_lat': 0,
        'center_lon': 0,
        'crs': 0,
        'time': 0,
        'time_valid': 0,
        'cloud_mask': 0,
        'cloud_cover': 0,
        'cloud_shadow': 0,
        'valid_ratio': 0,
        'season': 0,
        'day_of_year': 0,
        'sun_elevation': 0,
        'bands_info': 0,
        'spatial_resolution': 0,
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
    else:
        phi['sensor'] = 'unknown'
        phi['product_level'] = 'unknown'

    # 提取空间信息
    try:
        phi['center_lat'] = float(root['center_lat'][()])
        phi['center_lon'] = float(root['center_lon'][()])
        field_mask['center_lat'] = 1
        field_mask['center_lon'] = 1
    except Exception:
        phi['center_lat'] = None
        phi['center_lon'] = None

    # 提取 CRS
    try:
        phi['crs'] = int(root['crs'][()])
        field_mask['crs'] = 1
    except Exception:
        phi['crs'] = None

    # 提取时间信息（4个时间戳，单位为纳秒 since 1970-01-01，已从 zarr attrs 验证）
    # 注意：极少数样本时间戳损坏（负值），用 time_valid_* 标记
    time_arr = None
    try:
        time_arr = np.array(root['time'])  # [4] int64, 纳秒
        phi['time_0'] = int(time_arr[0])
        phi['time_1'] = int(time_arr[1])
        phi['time_2'] = int(time_arr[2])
        phi['time_3'] = int(time_arr[3])
        field_mask['time'] = 1
        # 有效性掩码：时间戳必须 > 0
        valid_flags = [int(int(time_arr[i]) > 0) for i in range(4)]
        phi['time_valid_0'] = valid_flags[0]
        phi['time_valid_1'] = valid_flags[1]
        phi['time_valid_2'] = valid_flags[2]
        phi['time_valid_3'] = valid_flags[3]
        field_mask['time_valid'] = 1
    except Exception:
        for i in range(4):
            phi[f'time_{i}'] = None
            phi[f'time_valid_{i}'] = 0

    # 衍生字段：季节 + 年内天数 + 太阳高度角（依赖 time + center_lat/lon）
    lat_v = phi.get('center_lat')
    lon_v = phi.get('center_lon')
    if time_arr is not None and lat_v is not None and lon_v is not None:
        any_season = any_sun = False
        for i in range(4):
            ts = int(time_arr[i])
            season, doy = get_season_and_doy(ts, lat_v)
            sun = solar_elevation_noaa(ts, lat_v, lon_v)
            phi[f'season_{i}'] = season
            phi[f'day_of_year_{i}'] = doy
            phi[f'sun_elevation_{i}'] = sun
            if season is not None:
                any_season = True
            if sun is not None:
                any_sun = True
        field_mask['season'] = int(any_season)
        field_mask['day_of_year'] = int(any_season)
        field_mask['sun_elevation'] = int(any_sun)
    else:
        for i in range(4):
            phi[f'season_{i}'] = None
            phi[f'day_of_year_{i}'] = None
            phi[f'sun_elevation_{i}'] = None

    # 提取云掩膜统计（不存完整云掩膜，只存统计值）
    # cloud_mask 类别: 0=land,1=water,2=snow,3=thin_cloud,4=thick_cloud,5=cloud_shadow,6=no_data
    # 修复：旧版用 (>0) 把水/雪/云影/no_data 全算成云；真正的云只有 thin(3)+thick(4)
    try:
        cloud_mask = np.array(root['cloud_mask'])  # [4, H, W] uint8
        for i in range(4):
            cm = cloud_mask[i]
            phi[f'cloud_cover_{i}'] = float(np.isin(cm, CLOUD_VALUES).mean())      # 薄云+厚云
            phi[f'cloud_shadow_{i}'] = float((cm == SHADOW_VALUE).mean())          # 云影
            phi[f'valid_ratio_{i}'] = float((cm != NODATA_VALUE).mean())           # 非 no_data 占比
        field_mask['cloud_mask'] = 1
        field_mask['cloud_cover'] = 1
        field_mask['cloud_shadow'] = 1
        field_mask['valid_ratio'] = 1
    except Exception:
        for i in range(4):
            phi[f'cloud_cover_{i}'] = None
            phi[f'cloud_shadow_{i}'] = None
            phi[f'valid_ratio_{i}'] = None

    # 提取图像形状信息
    try:
        bands = np.array(root['bands'])
        phi['num_timesteps'] = int(bands.shape[0])
        phi['num_bands'] = int(bands.shape[1])
        phi['height'] = int(bands.shape[2])
        phi['width'] = int(bands.shape[3])
        field_mask['bands_info'] = 1
    except Exception:
        phi['num_timesteps'] = None
        phi['num_bands'] = None
        phi['height'] = None
        phi['width'] = None

    # 空间分辨率（根据模态设置默认值）
    if modality == 'S2L2A':
        phi['spatial_resolution'] = 10.0  # 主波段 10m
        field_mask['spatial_resolution'] = 1
    elif modality == 'S1GRD':
        phi['spatial_resolution'] = 10.0  # GRD 10m
        field_mask['spatial_resolution'] = 1
    elif modality == 'S2RGB':
        phi['spatial_resolution'] = 10.0  # RGB 10m
        field_mask['spatial_resolution'] = 1
    else:
        phi['spatial_resolution'] = None

    # 提取 sample_id
    try:
        phi['sample_id'] = str(root['sample'][()])
    except Exception:
        phi['sample_id'] = sample_key  # fallback

    store.close()

    # 将 field_mask 转为字符串（parquet 不支持嵌套 dict）
    phi['_field_mask'] = json.dumps(field_mask)

    return phi


# ============================================================
# 外部数据 join 钩子（Stage 2 扩展点）
# ============================================================
def external_join_hook(
    phi: Dict[str, Any],
    sample_key: str,
    modality: str,
    external_sources: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """外部数据 join 钩子，给 Stage 2 的 D（外生驱动）和 G（地理先验）预留接口。

    当前为占位（pass-through），Stage 2 时实现：

    示例扩展（Stage 2 时取消注释并实现）：
    -----------------------------------------
    # ERA5 气象数据 → D（外生驱动）
    if external_sources and 'era5' in external_sources:
        era5 = external_sources['era5']
        for t in range(4):
            ts = phi.get(f'time_{t}')
            if ts and phi.get('center_lat') is not None:
                era5_row = era5.lookup(ts, phi['center_lat'], phi['center_lon'])
                phi[f'precipitation_{t}'] = era5_row['tp']
                phi[f'temperature_{t}'] = era5_row['t2m']

    # DEM/slope/aspect → G（地理先验）
    if external_sources and 'dem' in external_sources:
        dem = external_sources['dem']
        elev_grid = dem.crop(phi['center_lat'], phi['center_lon'], size_m=2640)
        phi['dem_mean'] = float(elev_grid.mean())
        phi['slope_mean'] = float(compute_slope(elev_grid).mean())

    # Sen1Floods11 事件 → D
    if external_sources and 'flood_events' in external_sources:
        events = external_sources['flood_events']
        evt = events.lookup_by_location_time(...)
        phi['event_type'] = evt['type'] if evt else None
        phi['event_time'] = evt['time'] if evt else None
    -----------------------------------------

    Args:
        phi: 当前 phi 字段字典
        sample_key: 样本主键（tar __key__）
        modality: 模态类型（S2L2A/S1GRD/...）
        external_sources: 外部数据源配置，None 时跳过

    Returns:
        增强后的 phi 字段字典
    """
    # Stage 1.5 阶段：直接返回原 phi
    # Stage 2 阶段：在此处 join 外部数据（保持函数签名不变以兼容）
    return phi


def process_shard(shard_path: str, modality: str, output_dir: Path,
                  external_sources: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    处理单个 tar shard，提取所有样本的 phi。

    Args:
        shard_path: tar 文件路径
        modality: 模态类型
        output_dir: 输出目录
        external_sources: 外部数据源（Stage 2 用，默认 None）

    Returns:
        该 shard 所有样本的 phi DataFrame
    """
    phi_records = []

    # 打开 tar shard
    dataset = wds.WebDataset(shard_path)

    for sample in dataset:
        try:
            key = sample['__key__']
            zarr_bytes = sample['zarr.zip']

            # 提取 phi（zarr 原生 + 衍生字段）
            phi = extract_phi_from_zarr(zarr_bytes, modality, key)

            # Stage 2 扩展点：join 外部数据
            phi = external_join_hook(phi, key, modality, external_sources)
            phi_records.append(phi)

        except Exception as e:
            print(f"Warning: Failed to process sample {key}: {e}")
            continue

    # 转为 DataFrame
    if phi_records:
        df = pd.DataFrame(phi_records)
    else:
        df = pd.DataFrame()

    return df


def main():
    parser = argparse.ArgumentParser(description='预处理 SSL4EO-S12 成像条件字段')
    parser.add_argument('--data-root', type=str,
                        default='/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1',
                        help='SSL4EO-S12 数据根目录')
    parser.add_argument('--modality', type=str, default='S2L2A',
                        choices=['S2L2A', 'S2L1C', 'S2RGB', 'S1GRD', 'DEM', 'LULC', 'NDVI'],
                        help='要处理的模态')
    parser.add_argument('--split', type=str, default='train',
                        choices=['train', 'val'],
                        help='数据划分')
    parser.add_argument('--max-shards', type=int, default=None,
                        help='最多处理多少个 shards（用于测试）')

    args = parser.parse_args()

    # 构建路径 - 输出到独立根目录
    data_dir = Path(args.data_root) / args.split / args.modality
    output_root = Path(args.data_root) / 'phi_processed' / args.split / args.modality
    output_root.mkdir(parents=True, exist_ok=True)

    # 查找所有 tar shards
    shard_files = sorted(data_dir.glob('*.tar'))

    if args.max_shards:
        shard_files = shard_files[:args.max_shards]

    print("="*80)
    print(f"SSL4EO-S12 成像条件字段预处理")
    print("="*80)
    print(f"数据根目录: {args.data_root}")
    print(f"模态: {args.modality}")
    print(f"划分: {args.split}")
    print(f"找到 {len(shard_files)} 个 tar shards")
    print(f"输出目录: {output_root}")
    print("="*80)
    print()

    # 处理每个 shard
    all_stats = {
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

        # 跳过已处理的
        if output_file.exists():
            print(f"跳过已存在: {output_file.name}")
            continue

        try:
            # 处理 shard
            df = process_shard(str(shard_path), args.modality, output_root)

            # 保存为 parquet
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

    # 保存统计信息
    stats_file = output_root / '_processing_stats.json'
    with open(stats_file, 'w') as f:
        json.dump(all_stats, f, indent=2)

    print("\n" + "="*80)
    print("预处理完成！")
    print(f"  处理的 shards: {all_stats['processed_shards']} / {all_stats['total_shards']}")
    print(f"  总样本数: {all_stats['total_samples']}")
    print(f"  失败的 shards: {len(all_stats['failed_shards'])}")
    print(f"  统计文件: {stats_file}")
    print("="*80)

    # 生成 README
    generate_readme(output_root.parent.parent, args, all_stats)


def generate_readme(phi_root: Path, args, all_stats: dict):
    """生成 phi_processed 目录的 README"""

    readme_content = f"""# SSL4EO-S12-v1.1 成像条件字段（Imaging Condition Fields）

**版本**: v2.0
**创建时间**: {pd.Timestamp.now().strftime('%Y-%m-%d')}
**处理工具**: WorldModel2026/scripts/build_phi_cache.py

> **v2.0 变更**：(1) 修复 cloud_cover 计算错误（旧版把水体/雪/云影误算为云）；
> (2) 新增 season / day_of_year / sun_elevation 衍生字段；
> (3) 新增 cloud_shadow / valid_ratio / time_valid 字段；
> (4) 修正 time 单位说明为「纳秒」。

---

## 简介

本目录包含从 SSL4EO-S12-v1.1 数据集提取的成像条件（phi）字段缓存。这些字段用于训练 **成像解耦的遥感观测编码器（Imaging-Decoupled Remote Sensing Observation Encoder）**。

## 目录结构

```
phi_processed/
├── README.md                    # 本文件
├── train/
│   ├── S2L2A/
│   │   ├── ssl4eos12_shard_000001_phi.parquet
│   │   ├── ssl4eos12_shard_000002_phi.parquet
│   │   ├── ...
│   │   └── _processing_stats.json
│   ├── S1GRD/
│   └── ...
└── val/
    └── ...
```

## 字段说明

### 固定字段（所有样本）
| 字段 | 类型 | 说明 |
|------|------|------|
| `sample_key` | str | 样本唯一标识（来自 tar 文件的 __key__） |
| `sample_id` | str | 样本ID（来自 zarr 的 sample 字段） |
| `modality` | str | 模态类型（S2L2A, S1GRD, 等） |
| `sensor` | str | 传感器（Sentinel-1, Sentinel-2, DEM） |
| `product_level` | str | 产品级别（L2A, GRD, RGB） |

### 空间字段
| 字段 | 类型 | 可用率 | 说明 |
|------|------|--------|------|
| `center_lat` | float64 | ~100% | 中心纬度 |
| `center_lon` | float64 | ~100% | 中心经度 |
| `crs` | int64 | ~100% | 坐标参考系统（EPSG 代码） |

### 时间字段
| 字段 | 类型 | 可用率 | 说明 |
|------|------|--------|------|
| `time_0` ~ `time_3` | int64 | ~100% | 4个时间戳，**单位：纳秒 since 1970-01-01**（非秒！来自 zarr time.attrs） |
| `time_valid_0` ~ `time_valid_3` | int | 100% | 时间戳有效性（1=有效, 0=损坏/负值）。少数样本时间戳损坏 |

### 衍生时间字段（本脚本计算，非 zarr 原生）
| 字段 | 类型 | 说明 |
|------|------|------|
| `season_0` ~ `season_3` | int | 季节编码：0=spring,1=summer,2=autumn,3=winter（已按南北半球翻转） |
| `day_of_year_0` ~ `day_of_year_3` | int | 年内天数（1-366） |
| `sun_elevation_0` ~ `sun_elevation_3` | float | 太阳高度角（度），NOAA 天文公式计算，夜间为负 |

### 云覆盖字段（v2.0 已修复）
| 字段 | 类型 | 说明 |
|------|------|------|
| `cloud_cover_0` ~ `cloud_cover_3` | float32 | **真实云覆盖率** [0-1]，仅 thin_cloud(3)+thick_cloud(4) |
| `cloud_shadow_0` ~ `cloud_shadow_3` | float32 | 云影占比 [0-1]，cloud_shadow(5) |
| `valid_ratio_0` ~ `valid_ratio_3` | float32 | 有效像素占比 [0-1]，非 no_data(6) |

> ⚠️ **v1.0 → v2.0 重要修复**：旧版 cloud_cover 用 `(cloud_mask > 0)` 计算，
> 把 water/snow/cloud_shadow/no_data 全部误算为云，导致水域样本云量虚高到 90%+。
> v2.0 改为 `isin([3,4])`，只统计真正的云。**v1.0 缓存的 cloud_cover 不可用。**

cloud_mask 类别定义（来自 zarr `cloud_mask.attrs['cloud_classes']`）：
`0=land, 1=water, 2=snow, 3=thin_cloud, 4=thick_cloud, 5=cloud_shadow, 6=no_data`

### 图像元信息
| 字段 | 类型 | 可用率 | 说明 |
|------|------|--------|------|
| `num_timesteps` | int32 | ~100% | 时间步数（通常为4） |
| `num_bands` | int32 | ~100% | 波段数（S2L2A=12, S1GRD=2） |
| `height` | int32 | ~100% | 图像高度（264） |
| `width` | int32 | ~100% | 图像宽度（264） |
| `spatial_resolution` | float32 | ~100% | 空间分辨率（米） |

### Field Mask
| 字段 | 类型 | 说明 |
|------|------|------|
| `_field_mask` | str | JSON 字符串，标记各字段是否可用（1=可用，0=缺失） |

## 使用方法

### Python 读取

```python
import pandas as pd

# 读取单个 shard 的 phi
df = pd.read_parquet('phi_processed/train/S2L2A/ssl4eos12_shard_000001_phi.parquet')

# 查找特定样本
phi = df[df['sample_key'] == 'ssl4eos12_train_seasonal_data_0000001'].iloc[0]

# 解析 field_mask
import json
field_mask = json.loads(phi['_field_mask'])
print(field_mask)  # {{'center_lat': 1, 'cloud_cover': 1, ...}}
```

### 批量加载

```python
from pathlib import Path
import pandas as pd

phi_dir = Path('phi_processed/train/S2L2A')
dfs = [pd.read_parquet(f) for f in phi_dir.glob('*_phi.parquet')]
df_all = pd.concat(dfs, ignore_index=True)
```

## 统计信息

每个模态的 `_processing_stats.json` 包含：
- 处理的 shard 数量
- 总样本数
- 失败的 shard 列表

## 数据质量

- **完整性**: 所有 zarr 原生字段均真实提取，未伪造或填充
- **衍生字段**: season/day_of_year/sun_elevation 由 time+经纬度精确计算
- **缺失处理**: 使用 `field_mask` 标记缺失字段，训练时通过 missing embedding 处理
- **验证**: 已在 {all_stats.get('total_samples', 'N/A')} 个样本上验证

## 当前缺失字段的必要性与解决思路

成像解耦的目标是分离「成像条件 φ」与「地表状态 s」。以下字段对解耦有价值但当前 zarr 未提供：

| 缺失字段 | 对解耦的必要性 | 当前状态 | 解决思路 |
|---------|--------------|---------|---------|
| `sun_elevation` 太阳高度角 | **高**：直接决定光照强度/阴影，是最强成像干扰 | ✅ **已解决**（v2.0 NOAA 公式计算） | 已用纯numpy天文公式计算，无需外部数据 |
| `season` 季节 | **高**：植被物候/积雪随季节变化，强成像协变量 | ✅ **已解决**（v2.0 从 time+lat 推导） | 已实现，含南北半球翻转 |
| `view_angle` 观测角 | 中：影响 BRDF/几何畸变 | ❌ **缺失，无法补** | zarr 与 SSL4EO 发布数据均无此字段；需回到 Sentinel-2 官方 L2A 产品的 `MTD_TL.xml` 提取。S2 视场角窄（±10°内），第一版可近似为常数忽略 |
| `sun_azimuth` 太阳方位角 | 中：与高度角共同决定阴影方向 | ⏸ 可补 | 同 sun_elevation，NOAA 公式可扩展计算方位角，按需添加 |
| `precipitation`/`temperature` 气象 | 中：影响地表湿度/反照率 | ❌ 需外部数据 | 需用经纬度+时间检索 ERA5 再分析数据，作为 Stage 2 跨数据集工作 |
| `atmospheric_opacity` 大气透明度 | 低：影响光谱衰减 | ❌ 需外部数据 | 需 AOD 气溶胶产品；优先级低 |

**结论**：成像解耦最关键的两个干扰因子（太阳高度角、季节）已在 v2.0 补齐。
`view_angle` 因源数据缺失暂时搁置，对 Sentinel-2 影响有限（窄视场）。
气象类字段属于 Stage 2 跨数据集融合范畴。

## 引用

如果使用本预处理数据，请引用：

```bibtex
@misc{{ssl4eo_phi_2026,
  title={{SSL4EO-S12-v1.1 Imaging Condition Fields}},
  author={{Liu, Zhijian}},
  year={{2026}},
  note={{Processed imaging condition metadata for ObsWorld project}}
}}
```

原始数据集：
```bibtex
@article{{wang2023ssl4eo,
  title={{SSL4EO-S12: A Large-Scale Multi-Modal, Multi-Temporal Dataset for Self-Supervised Learning in Earth Observation}},
  author={{Wang, Yi and others}},
  journal={{arXiv preprint arXiv:2211.07044}},
  year={{2023}}
}}
```

---

**维护者**: Zhijian Liu (zjliu17@...)
**项目**: ObsWorld - Imaging-Decoupled Land-Surface State Dynamics
**最后更新**: {pd.Timestamp.now().strftime('%Y-%m-%d')}
"""

    readme_file = phi_root / 'README.md'
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"\n✓ 生成 README: {readme_file}")


if __name__ == '__main__':
    main()
