"""
phi 字段 parquet 缓存加载器

启动时全量预加载 phi_processed/ 下的 parquet 到内存索引（~68MB/split），
训练时按 sample_key 1:1 查表获取 phi_dict。

设计理由（见 任务描述相关/14_*）：
- 未来 Stage2 要 join ERA5 气象、Sen1Floods11 事件等外部数据，必须离线 join 到 parquet
- 在线计算无法支持外部数据
- 已验证：sample_key 与 sample_id 1:1 映射，精简后总内存 ~68MB

关键约束：
- 多进程 DataLoader worker 每个会复制一份索引（68MB × num_workers），需在配置中控制
- FSDP 各 rank 独立加载，与分布式无冲突
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

import numpy as np
import pandas as pd


# ============================================================
# phi 字段精简列表（只保留训练用到的字段，省内存）
# ============================================================
PHI_FIELDS_CORE = [
    'sample_key',           # 主键
    'modality',
    'center_lat', 'center_lon',
]

PHI_FIELDS_TIME = [f'{prefix}_{t}' for prefix in
                   ['time', 'time_valid', 'season', 'day_of_year', 'sun_elevation']
                   for t in range(4)]

PHI_FIELDS_CLOUD = [f'{prefix}_{t}' for prefix in
                    ['cloud_cover', 'cloud_shadow', 'valid_ratio']
                    for t in range(4)]

PHI_FIELDS_ALL = PHI_FIELDS_CORE + PHI_FIELDS_TIME + PHI_FIELDS_CLOUD

# phi v3：S1 SAR 几何字段（存在 phi_processed_v3_s1geom/{split}/S1GRD/*_phi_s1geom.parquet）
# 由 scripts/build_phi_v3_s1geom.py 生成，按 sample_key 与 S1GRD phi 对齐后 merge 进索引。
PHI_V3_SAR_GEOM_FIELDS = ['sample_key'] + [
    f'{prefix}_{t}' for prefix in
    ['s1_orbit_direction', 's1_relative_orbit', 's1_satellite',
     's1_incidence_angle', 's1_incidence_valid', 's1_geom_valid']
    for t in range(4)
]


# ============================================================
# PhiCache 主类
# ============================================================
class PhiCache:
    """phi 字段内存索引。

    用法：
        cache = PhiCache(phi_root='.../phi_processed', split='train', modality='S2L2A')
        phi_dict = cache.lookup('ssl4eos12_train_seasonal_data_0000001')
        # phi_dict 是单样本的 {field_name: value} 字典

    分布式：每个 rank 独立加载，无需通信。
    多进程：worker_init_fn 中重新实例化避免 fork 时的内存爆炸（见 build_phi_cache_for_worker）。
    """

    def __init__(
        self,
        phi_root: str,
        split: str = 'train',
        modality: str = 'S2L2A',
        fields: Optional[List[str]] = None,
        verbose: bool = True,
        v3_geom_root: Optional[str] = None,
    ):
        """
        Args:
            phi_root: phi_processed 根目录（如 .../SSL4EO-S12-v1.1/phi_processed）
            split: 'train' 或 'val'
            modality: 'S2L2A' 或 'S1GRD'
            fields: 要保留的列名列表；None 表示用 PHI_FIELDS_ALL（精简版）
            verbose: 是否打印加载日志
            v3_geom_root: phi v3 S1 几何根目录（如 .../phi_processed_v3_s1geom）。
                仅对 modality='S1GRD' 生效：按 sample_key merge S1 SAR 几何字段。
        """
        self.phi_root = Path(phi_root)
        self.split = split
        self.modality = modality
        self.fields = fields or PHI_FIELDS_ALL
        self.verbose = verbose
        self.v3_geom_root = Path(v3_geom_root) if v3_geom_root else None

        # 加载所有 parquet 并构建索引
        self._index = self._build_index()

    def _build_index(self) -> Dict[str, Dict[str, Any]]:
        """加载 parquet 并构建 sample_key → phi_dict 索引。"""
        phi_dir = self.phi_root / self.split / self.modality
        if not phi_dir.exists():
            raise FileNotFoundError(f"phi 缓存目录不存在: {phi_dir}")

        parquet_files = sorted(phi_dir.glob('*_phi.parquet'))
        if not parquet_files:
            raise FileNotFoundError(f"未找到 parquet 文件: {phi_dir}")

        if self.verbose:
            print(f"[PhiCache] 加载 {self.split}/{self.modality}: {len(parquet_files)} 个文件...")

        # 批量读取，只保留需要的列
        dfs = []
        for pf in parquet_files:
            df = pd.read_parquet(pf, columns=self._get_actual_columns(pf))
            dfs.append(df)
        full_df = pd.concat(dfs, ignore_index=True)

        # phi v3：按 sample_key merge S1 SAR 几何字段（仅 S1GRD）
        if self.v3_geom_root is not None and self.modality == 'S1GRD':
            full_df = self._merge_v3_geom(full_df)

        # 构建索引：sample_key → row dict
        # 用 to_dict('records') 一次性转换，再用 sample_key 做 key
        records = full_df.to_dict('records')
        index = {rec['sample_key']: rec for rec in records}

        if self.verbose:
            mem_mb = full_df.memory_usage(deep=True).sum() / 1024 ** 2
            print(f"[PhiCache] 索引完成: {len(index)} 样本, 内存 ~{mem_mb:.1f} MB")

        return index

    def _merge_v3_geom(self, full_df: pd.DataFrame) -> pd.DataFrame:
        """按 sample_key merge phi v3 S1 SAR 几何字段进主 phi DataFrame。

        v3 文件：v3_geom_root/{split}/S1GRD/*_phi_s1geom.parquet
        left join：主 phi 有而 v3 无的样本，几何字段填 NaN → 下游走 encoder 的 missing embedding。
        """
        v3_dir = self.v3_geom_root / self.split / 'S1GRD'
        if not v3_dir.exists():
            if self.verbose:
                print(f"[PhiCache] ⚠️ v3 几何目录不存在，跳过 merge: {v3_dir}")
            return full_df

        v3_files = sorted(v3_dir.glob('*_phi_s1geom.parquet'))
        if not v3_files:
            if self.verbose:
                print(f"[PhiCache] ⚠️ 未找到 v3 几何 parquet，跳过 merge: {v3_dir}")
            return full_df

        # 读 v3，只取几何字段（与 sample_key）
        v3_schema = pd.read_parquet(v3_files[0], columns=None).columns.tolist()
        v3_cols = [c for c in PHI_V3_SAR_GEOM_FIELDS if c in v3_schema]
        v3_dfs = [pd.read_parquet(f, columns=v3_cols) for f in v3_files]
        v3_df = pd.concat(v3_dfs, ignore_index=True)
        v3_df = v3_df.drop_duplicates(subset='sample_key')

        n_before = len(full_df)
        merged = full_df.merge(v3_df, on='sample_key', how='left')
        assert len(merged) == n_before, \
            f"v3 merge 后行数变化 {n_before}→{len(merged)}（sample_key 可能有重复）"

        if self.verbose:
            geom_col = 's1_geom_valid_0' if 's1_geom_valid_0' in merged.columns else None
            hit = merged['s1_orbit_direction_0'].notna().sum() if 's1_orbit_direction_0' in merged.columns else 0
            print(f"[PhiCache] v3 S1 几何 merge: {len(v3_df)} 条 → 命中 {hit}/{n_before} 样本")

        return merged

    def _get_actual_columns(self, pf: Path) -> List[str]:
        """获取 parquet 文件中实际存在的列（与 self.fields 求交集）。"""
        # 只在第一次调用时检查，假设所有 parquet 列相同
        if not hasattr(self, '_actual_cols_cache'):
            schema = pd.read_parquet(pf, columns=None).columns.tolist()
            self._actual_cols_cache = [c for c in self.fields if c in schema]
        return self._actual_cols_cache

    def lookup(self, sample_key: str) -> Optional[Dict[str, Any]]:
        """按 sample_key 查询 phi 字段。

        Returns:
            phi_dict: {field_name: value}；查不到返回 None
        """
        return self._index.get(sample_key)

    def lookup_or_default(self, sample_key: str) -> Dict[str, Any]:
        """查询 phi，查不到时返回带全 None 的 dict（训练时不中断）。

        Returns:
            phi_dict（保证非空，缺失字段为 None）
        """
        result = self.lookup(sample_key)
        if result is not None:
            return result
        # 构造空 dict（用于训练时缺失值降级到 missing embedding）
        return {f: None for f in self.fields}

    def __len__(self) -> int:
        return len(self._index)

    def __contains__(self, sample_key: str) -> bool:
        return sample_key in self._index

    def keys(self):
        return self._index.keys()


# ============================================================
# 外部数据 join 钩子（Stage 2 扩展接口）
# ============================================================
def join_external_data(
    phi_dict: Dict[str, Any],
    sample_key: str,
    external_sources: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """外部数据 join 接口（Stage 2 用，当前为占位）。

    Stage 2 时将在此处 join：
    - ERA5 气象数据（precipitation, temperature）→ D（外生驱动）
    - Sen1Floods11 事件数据（event_type, event_time）→ D
    - DEM/slope/aspect → G（地理先验）
    - permanent_water/water_distance → G

    实现路径：
    1. 在 build_phi_cache.py 中预 join 外部数据到 parquet 新列（推荐，性能最优）
    2. 或在此处运行时 join（适合频繁变化的外部数据）

    Args:
        phi_dict: 现有 phi 字段
        sample_key: 样本主键
        external_sources: 外部数据源配置（Stage 2 启用）

    Returns:
        增强后的 phi_dict（当前直接返回原 dict）
    """
    # TODO[Stage2]: 实现外部数据 join
    # if external_sources is not None and 'era5' in external_sources:
    #     era5_data = external_sources['era5'].lookup_by_sample(sample_key)
    #     phi_dict.update({'precipitation': era5_data['tp'], 'temperature': era5_data['t2m']})
    return phi_dict


# ============================================================
# 批处理用：phi_dict 列表 → torch dict（供 collate_fn 调用）
# ============================================================
def batch_phi_dicts_to_tensors(
    phi_dicts: List[Dict[str, Any]],
    device: Optional[str] = None,
) -> Dict[str, Any]:
    """将 batch 的 phi_dict 列表转换为统一格式的 tensor dict。

    数值字段 → float tensor；类别字段 → long tensor；缺失值 → NaN/-1。

    Args:
        phi_dicts: [B] 个 phi_dict
        device: 目标设备（None 表示 CPU）

    Returns:
        dict: 字段名 → tensor，每个 tensor 形状为 [B] 或 [B, 4]（时序字段）
    """
    import torch
    B = len(phi_dicts)
    out = {}

    # 单值字段（[B]）
    for fname in ['center_lat', 'center_lon']:
        vals = [d.get(fname) for d in phi_dicts]
        vals = [v if v is not None else np.nan for v in vals]
        out[fname] = torch.tensor(vals, dtype=torch.float32)

    # modality（类别字符串 → int code）
    modality_codes = {'S2L2A': 0, 'S1GRD': 1, 'S2L1C': 2, 'S2RGB': 3, 'DEM': 4, 'LULC': 5}
    out['modality'] = torch.tensor(
        [modality_codes.get(d.get('modality'), -1) for d in phi_dicts],
        dtype=torch.long
    )

    # 时序字段（[B, 4]）
    for prefix, dtype in [
        ('time', torch.long),
        ('time_valid', torch.long),
        ('season', torch.long),
        ('day_of_year', torch.long),
        ('sun_elevation', torch.float32),
        ('cloud_cover', torch.float32),
        ('cloud_shadow', torch.float32),
        ('valid_ratio', torch.float32),
    ]:
        mat = []
        for d in phi_dicts:
            row = [d.get(f'{prefix}_{t}') for t in range(4)]
            # 缺失值填充
            if dtype == torch.long:
                row = [v if v is not None else -1 for v in row]
            else:
                row = [v if v is not None and not (isinstance(v, float) and np.isnan(v)) else np.nan for v in row]
            mat.append(row)
        out[prefix] = torch.tensor(mat, dtype=dtype)

    if device is not None:
        out = {k: v.to(device) for k, v in out.items()}

    return out


def batch_phi_single_timestep_to_tensors(
    phi_dicts: List[Dict[str, Any]],
    season_indices: List[int],
    device: Optional[str] = None,
) -> Dict[str, Any]:
    """⭐ 单时间片版（D3）：每个样本按选中的季节 t 取对应时间片字段。

    与 batch_phi_dicts_to_tensors 的区别：时序字段（sun_elevation/season/cloud 等）
    输出为标量 [B]（取 `{prefix}_{t}`），而非 4 季 [B,4]。
    单值字段（lat/lon/modality）与原函数一致。

    Args:
        phi_dicts: [B] 个 phi_dict（含 sun_elevation_0..3 等列）
        season_indices: [B] 每个样本选中的季节 t（与图像选的季节一致）
        device: 目标设备

    Returns:
        dict: 字段名 → tensor，时序字段为 [B]，供单时间片 ImagingConditionEncoder 消费
    """
    import torch
    B = len(phi_dicts)
    assert len(season_indices) == B, "season_indices 长度须等于 batch"
    out = {}

    # 单值字段（[B]）
    for fname in ['center_lat', 'center_lon']:
        vals = [d.get(fname) for d in phi_dicts]
        vals = [v if v is not None else np.nan for v in vals]
        out[fname] = torch.tensor(vals, dtype=torch.float32)

    modality_codes = {'S2L2A': 0, 'S1GRD': 1, 'S2L1C': 2, 'S2RGB': 3, 'DEM': 4, 'LULC': 5}
    out['modality'] = torch.tensor(
        [modality_codes.get(d.get('modality'), -1) for d in phi_dicts],
        dtype=torch.long
    )

    # 时序字段：按各样本选中的 t 取标量 → [B]
    for prefix, dtype in [
        ('time', torch.long),
        ('time_valid', torch.long),
        ('season', torch.long),
        ('day_of_year', torch.long),
        ('sun_elevation', torch.float32),
        ('cloud_cover', torch.float32),
        ('cloud_shadow', torch.float32),
        ('valid_ratio', torch.float32),
    ]:
        col = []
        for d, t in zip(phi_dicts, season_indices):
            v = d.get(f'{prefix}_{t}')
            missing = v is None or (isinstance(v, float) and np.isnan(v))
            if dtype == torch.long:
                col.append(-1 if missing else int(v))
            else:
                col.append(np.nan if missing else v)
        out[prefix] = torch.tensor(col, dtype=dtype)

    # phi v3：S1 SAR 几何字段（仅当 phi_dict 含这些列时才发出，缺省走 encoder 的 missing）
    # 命名约定：build_phi_v3_s1geom.py 写出 s1_orbit_direction_t / s1_relative_orbit_t /
    #           s1_satellite_t / s1_incidence_angle_t / s1_incidence_valid_t
    _SAR_GEOM_FIELDS = [
        ('s1_orbit_direction', torch.long),
        ('s1_relative_orbit', torch.long),
        ('s1_satellite', torch.long),
        ('s1_incidence_angle', torch.float32),
        ('s1_incidence_valid', torch.long),
    ]
    has_sar_geom = any(f'{p}_0' in phi_dicts[0] for p, _ in _SAR_GEOM_FIELDS) if phi_dicts else False
    if has_sar_geom:
        for prefix, dtype in _SAR_GEOM_FIELDS:
            col = []
            for d, t in zip(phi_dicts, season_indices):
                v = d.get(f'{prefix}_{t}')
                missing = v is None or (isinstance(v, float) and np.isnan(v))
                if dtype == torch.long:
                    col.append(-1 if missing else int(v))
                else:
                    col.append(np.nan if missing else v)
            # 输出键去掉 _t 后缀，供单时间片 SARGeometryEncoder 直接消费
            out[prefix] = torch.tensor(col, dtype=dtype)

    if device is not None:
        out = {k: v.to(device) for k, v in out.items()}

    return out
_GLOBAL_PHI_CACHES: Dict[str, PhiCache] = {}
def get_phi_cache(
    phi_root: str,
    split: str,
    modality: str,
    **kwargs
) -> PhiCache:
    """获取全局共享的 PhiCache 实例（同进程内不重复加载）。"""
    cache_key = f"{phi_root}::{split}::{modality}"
    if cache_key not in _GLOBAL_PHI_CACHES:
        _GLOBAL_PHI_CACHES[cache_key] = PhiCache(phi_root, split, modality, **kwargs)
    return _GLOBAL_PHI_CACHES[cache_key]


if __name__ == '__main__':
    # 自测
    print("=== PhiCache 自测 ===")
    cache = PhiCache(
        phi_root='/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed',
        split='train',
        modality='S2L2A',
    )
    print(f"\n索引大小: {len(cache)}")

    # 取第一个 key 测试
    first_key = next(iter(cache.keys()))
    phi = cache.lookup(first_key)
    print(f"\n示例查询 sample_key={first_key}:")
    print(f"  lat/lon: {phi['center_lat']:.2f}, {phi['center_lon']:.2f}")
    print(f"  sun_elev_0~3: {[phi[f'sun_elevation_{t}'] for t in range(4)]}")
    print(f"  season_0~3: {[phi[f'season_{t}'] for t in range(4)]}")
    print(f"  cloud_cover_0~3: {[phi[f'cloud_cover_{t}'] for t in range(4)]}")

    # 测试 batch → tensor
    keys = list(cache.keys())[:3]
    batch = [cache.lookup(k) for k in keys]
    tensors = batch_phi_dicts_to_tensors(batch)
    print(f"\nbatch_to_tensors (3 样本):")
    for k, v in tensors.items():
        print(f"  {k}: shape={v.shape}, dtype={v.dtype}")

    # 缺失键测试
    missing = cache.lookup_or_default('not_exist_key_999')
    print(f"\n缺失键 fallback: lat={missing['center_lat']}, season_0={missing.get('season_0')}")

    print("\n✓ PhiCache 自测通过")
