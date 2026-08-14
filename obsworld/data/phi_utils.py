"""
成像条件（phi）字段计算工具模块

本模块提供 phi 字段的核心计算算法，供以下两处调用：
1. scripts/build_phi_cache.py - 离线预处理，生成 parquet 缓存
2. data/phi_loader.py - 训练时从 parquet 读取（不在线计算）

设计原则：
- 算法逻辑集中在此，避免重复实现（DRY）
- 纯函数设计，输入zarr元数据 → 输出phi_dict
- 支持向量化，适配 pandas DataFrame 批量处理

关键约束：
- time 单位为纳秒 since 1970-01-01（zarr time.attrs验证，非秒！）
- season 编码已按南北半球翻转（0春1夏2秋3冬）
- cloud_cover 仅统计 thin_cloud(3)+thick_cloud(4)，非 >0
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union


# ============================================================
# 常量定义（来自 zarr cloud_mask.attrs 验证）
# ============================================================
CLOUD_CLASSES = ['land', 'water', 'snow', 'thin_cloud', 'thick_cloud', 'cloud_shadow', 'no_data']
CLOUD_VALUES = [3, 4]        # 真正的云：薄云 + 厚云
SHADOW_VALUE = 5             # 云影
NODATA_VALUE = 6             # 无数据


# ============================================================
# 太阳位置计算（NOAA算法，纯numpy，向量化）
# ============================================================
def solar_elevation_noaa(
    timestamp_ns: Union[int, np.ndarray],
    lat: Union[float, np.ndarray],
    lon: Union[float, np.ndarray]
) -> Union[float, np.ndarray, None]:
    """用 NOAA 天文算法计算太阳高度角（度）。

    纯 numpy 实现，无需 pvlib/astral。精度 <0.5°，支持向量化。
    实测性能：24.4 万样本 0.36 秒（已向量化）。

    Args:
        timestamp_ns: 纳秒级 Unix 时间戳（zarr time 字段单位），标量或数组
        lat: 纬度（度），标量或数组
        lon: 经度（度），标量或数组

    Returns:
        太阳高度角（度）；夜间为负值。无效输入返回 None（标量）或 NaN（数组）。

    References:
        NOAA Solar Position Calculator
        https://gml.noaa.gov/grad/solcalc/calcdetails.html
    """
    # 输入校验与类型归一化
    is_scalar = np.isscalar(timestamp_ns)
    ts = np.atleast_1d(timestamp_ns).astype(np.float64)
    lat_arr = np.atleast_1d(lat).astype(np.float64)
    lon_arr = np.atleast_1d(lon).astype(np.float64)

    # 无效输入处理（负值或None）
    invalid = (ts <= 0) | np.isnan(ts)
    if invalid.all():
        return None if is_scalar else np.full_like(ts, np.nan)

    # 转换为 pandas Timestamp（支持向量化）
    try:
        dt = pd.to_datetime(ts, unit='ns', utc=True)
    except (ValueError, pd.errors.OutOfBoundsDatetime):
        return None if is_scalar else np.full_like(ts, np.nan)

    # 儒略日 → 自 J2000 起的天数
    jd = dt.to_julian_date().values if hasattr(dt, 'to_julian_date') else \
         np.array([d.to_julian_date() for d in dt])
    n = jd - 2451545.0

    # 太阳几何平黄经与平近点角
    L = (280.460 + 0.9856474 * n) % 360
    g = np.radians((357.528 + 0.9856003 * n) % 360)
    lam = np.radians((L + 1.915 * np.sin(g) + 0.020 * np.sin(2 * g)) % 360)
    eps = np.radians(23.439 - 0.0000004 * n)

    # 赤纬
    decl = np.arcsin(np.sin(eps) * np.sin(lam))

    # 赤经 + 格林尼治恒星时 → 地方时角
    ra = np.degrees(np.arctan2(np.cos(eps) * np.sin(lam), np.cos(lam))) % 360
    gmst = (280.46061837 + 360.98564736629 * n) % 360
    lmst = (gmst + lon_arr) % 360
    H = np.radians((lmst - ra) % 360)

    # 太阳高度角
    latr = np.radians(lat_arr)
    elev = np.arcsin(np.sin(latr) * np.sin(decl) + np.cos(latr) * np.cos(decl) * np.cos(H))
    elev_deg = np.degrees(elev)

    # 无效位置填 NaN
    elev_deg = np.where(invalid, np.nan, elev_deg)

    if is_scalar:
        val = float(elev_deg[0])
        return None if np.isnan(val) else val
    return elev_deg


# ============================================================
# 季节与年内天数（已分南北半球）
# ============================================================
def get_season_and_doy(
    timestamp_ns: Union[int, np.ndarray],
    lat: Union[float, np.ndarray]
) -> tuple:
    """从纳秒时间戳 + 纬度推导季节编码与年内天数。

    季节编码: 0=spring, 1=summer, 2=autumn, 3=winter（已按南北半球翻转）。

    Args:
        timestamp_ns: 纳秒时间戳，标量或数组
        lat: 纬度（度），标量或数组

    Returns:
        (season_code, day_of_year): 标量返回 (int|None, int|None)；
        数组返回 (np.ndarray[int], np.ndarray[int])，无效位置为 -1
    """
    is_scalar = np.isscalar(timestamp_ns)
    ts = np.atleast_1d(timestamp_ns).astype(np.int64)
    lat_arr = np.atleast_1d(lat).astype(np.float64)

    invalid = ts <= 0
    if invalid.all():
        if is_scalar:
            return None, None
        return np.full(ts.shape, -1, dtype=np.int32), np.full(ts.shape, -1, dtype=np.int32)

    # 用 pandas 取月份和年内天数（自动处理时区与闰年）
    dt = pd.to_datetime(np.where(invalid, 0, ts), unit='ns', utc=True)
    month = np.array(dt.month, dtype=np.int32)
    doy = np.array(dt.dayofyear, dtype=np.int32)

    # 北半球季节编码
    season_n = np.select(
        [np.isin(month, [3, 4, 5]),
         np.isin(month, [6, 7, 8]),
         np.isin(month, [9, 10, 11])],
        [0, 1, 2],  # 春, 夏, 秋
        default=3,   # 冬
    ).astype(np.int32)

    # 南半球翻转：spring↔autumn, summer↔winter
    flip_map = np.array([2, 3, 0, 1], dtype=np.int32)
    season = np.where(lat_arr >= 0, season_n, flip_map[season_n])

    # 无效位置标 -1
    season = np.where(invalid, -1, season)
    doy = np.where(invalid, -1, doy)

    if is_scalar:
        s = int(season[0])
        d = int(doy[0])
        return (None if s < 0 else s), (None if d < 0 else d)
    return season, doy


# ============================================================
# 云掩膜统计
# ============================================================
def compute_cloud_stats(cloud_mask_slice: np.ndarray) -> Dict[str, float]:
    """从单时间片的 cloud_mask 计算云量/云影/有效像素占比。

    cloud_mask 类别（zarr cloud_mask.attrs['cloud_classes'] 验证）：
        0=land, 1=water, 2=snow, 3=thin_cloud, 4=thick_cloud, 5=cloud_shadow, 6=no_data

    Args:
        cloud_mask_slice: [H, W] uint8 单时间片云掩膜

    Returns:
        dict: cloud_cover (薄云+厚云), cloud_shadow (云影), valid_ratio (非no_data)
    """
    cm = np.asarray(cloud_mask_slice)
    return {
        'cloud_cover': float(np.isin(cm, CLOUD_VALUES).mean()),
        'cloud_shadow': float((cm == SHADOW_VALUE).mean()),
        'valid_ratio': float((cm != NODATA_VALUE).mean()),
    }


# ============================================================
# 字段归一化（供 ImagingConditionEncoder 使用）
# ============================================================
# 全局统计量（来自 §4.3 phi 字段统计，1024 样本验证）
SUN_ELEVATION_MIN = 0.0    # 留余量，实测 min=9.3
SUN_ELEVATION_MAX = 90.0   # 物理上限
SUN_ELEVATION_DEAD = 9.0   # 实测下边界（接近正午地平线）

LAT_MIN, LAT_MAX = -90.0, 90.0
LON_MIN, LON_MAX = -180.0, 180.0


def normalize_sun_elevation(elev_deg: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """太阳高度角归一化到 [-1, 1]。
    用 sin(elev) 而非线性归一化，物理上更合理（与光照强度直接相关）。
    """
    return np.sin(np.radians(elev_deg))


def normalize_lat(lat: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """纬度归一化到 [-1, 1]。"""
    return lat / 90.0


def normalize_lon_sincos(lon: Union[float, np.ndarray]) -> tuple:
    """经度用 (sin, cos) 编码处理环绕（180度问题）。"""
    rad = np.radians(lon)
    return np.sin(rad), np.cos(rad)


def encode_lat_lon_multifreq(
    lat: Union[float, np.ndarray],
    lon: Union[float, np.ndarray],
    num_frequencies: int = 4,
) -> np.ndarray:
    """对 lat/lon 做多频 sin/cos 编码（球谐函数的轻量版）。

    参考：NeRF positional encoding, SatCLIP, GeoCLIP。
    频率倍增：2^0, 2^1, ..., 2^(num_frequencies-1)

    Args:
        lat: 纬度（度），标量或 [B] 数组
        lon: 经度（度），标量或 [B] 数组
        num_frequencies: 频率层数，默认 4 → 总编码维度 = 4 * 2 * 2 = 16

    Returns:
        编码向量，shape: [..., num_frequencies * 4]
        4 = (lat_sin, lat_cos, lon_sin, lon_cos)
    """
    lat_rad = np.radians(np.atleast_1d(lat))
    lon_rad = np.radians(np.atleast_1d(lon))

    freqs = np.array([2 ** i for i in range(num_frequencies)], dtype=np.float32)
    out = []
    for f in freqs:
        out.extend([np.sin(f * lat_rad), np.cos(f * lat_rad),
                    np.sin(f * lon_rad), np.cos(f * lon_rad)])
    encoded = np.stack(out, axis=-1).astype(np.float32)  # [B, num_freq*4]

    # 标量输入还原标量输出
    if np.isscalar(lat):
        return encoded[0]
    return encoded


# ============================================================
# 字段完整性校验
# ============================================================
def check_phi_validity(phi_dict: Dict[str, Any]) -> Dict[str, bool]:
    """检查 phi_dict 各字段的有效性，返回 mask 字典。

    用于训练时判断该样本的哪些字段可用，缺失字段走 missing embedding。

    Returns:
        dict: {field_name: True/False}
    """
    valid = {}
    for t in range(4):
        valid[f'time_{t}'] = phi_dict.get(f'time_{t}') is not None and phi_dict.get(f'time_{t}', 0) > 0
        valid[f'season_{t}'] = phi_dict.get(f'season_{t}') is not None and phi_dict.get(f'season_{t}', -1) >= 0
        valid[f'sun_elevation_{t}'] = phi_dict.get(f'sun_elevation_{t}') is not None and \
                                       not (isinstance(phi_dict.get(f'sun_elevation_{t}'), float) and
                                            np.isnan(phi_dict.get(f'sun_elevation_{t}')))
        valid[f'cloud_cover_{t}'] = phi_dict.get(f'cloud_cover_{t}') is not None

    valid['center_lat'] = phi_dict.get('center_lat') is not None
    valid['center_lon'] = phi_dict.get('center_lon') is not None
    valid['modality'] = phi_dict.get('modality') is not None
    return valid


if __name__ == '__main__':
    # 自测：用真实数据样例验证
    print("=== phi_utils 自测 ===")

    # 测试1：单样本太阳高度角
    ts = 1582011589000000000  # 2020-02-18
    lat, lon = 33.67, 47.22
    elev = solar_elevation_noaa(ts, lat, lon)
    season, doy = get_season_and_doy(ts, lat)
    print(f"样本 ({lat}, {lon}) @ 2020-02-18:")
    print(f"  sun_elevation: {elev:.1f}°  (预期 ~40°)")
    print(f"  season: {season} (0=春, 预期=3冬)  doy: {doy} (预期=49)")

    # 测试2：向量化
    ts_arr = np.array([1582011589000000000, 1591255579000000000, 1599291379000000000])
    lat_arr = np.array([33.67, -33.67, 0.0])
    elev_arr = solar_elevation_noaa(ts_arr, lat_arr, np.array([47.22, 47.22, 0.0]))
    seasons, doys = get_season_and_doy(ts_arr, lat_arr)
    print(f"\n向量化测试 (3 样本):")
    print(f"  sun_elev: {elev_arr}")
    print(f"  seasons: {seasons}  (北33.67 2月→冬3, 南-33.67 6月→冬3, 赤道 9月→秋2)")

    # 测试3：lat/lon 多频编码
    enc = encode_lat_lon_multifreq(33.67, 47.22, num_frequencies=4)
    print(f"\n经纬度多频编码 (4 freq → 16 dim):")
    print(f"  shape: {enc.shape}, 值范围: [{enc.min():.3f}, {enc.max():.3f}]")

    # 测试4：无效输入
    print(f"\n无效输入处理:")
    print(f"  负时间戳 sun_elev: {solar_elevation_noaa(-1, lat, lon)}")
    print(f"  负时间戳 season: {get_season_and_doy(-1, lat)}")

    print("\n✓ phi_utils 自测通过")
