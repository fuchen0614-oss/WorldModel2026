"""
双模态 SSL4EO-S12 数据加载器：S1 GRD + S2 L2A 配对。

本模块扩展自 ssl4eo.py，同时加载 S1GRD 和 S2L2A 数据，
按 sample_id 配对同一地理位置的两个模态。

数据结构：
- S1GRD: [4_seasons, 2_bands(VV/VH), 264, 264], dtype float32
- S2L2A: [4_seasons, 12_bands, 264, 264], dtype int16
- 两者共享相同的 tar shard 编号和 sample_id

Stage 1.5 增强：
- 集成 PhiCache，从 parquet 读取预处理好的 phi 字段（sun_elevation/season/cloud 等）
- 按 sample_key join（sample_key 在 tar 中为 __key__）
"""

import io
import json
import os
import random
import zipfile
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.distributed as dist
import webdataset as wds
import zarr
from braceexpand import braceexpand
from torch.utils.data import DataLoader, IterableDataset
from zarr.storage import KVStore

from .ssl4eo import ZipFileStore, normalize_image
from ..phi_loader import PhiCache, batch_phi_dicts_to_tensors


class SSL4EODualConfig:
    """双模态 SSL4EO 数据集加载配置。

    Attributes:
        split: 数据集划分（'train' 或 'val'）
        random_season: 若为 True，则随机选择一个季节；否则返回全部 4 个季节
        base_path: 包含 SSL4EO-S12 数据的根目录
        shard_pattern: 匹配 tar 分片的模式（默认：所有分片）
        normalize: 若为 True，则根据模态将图像归一化
        cache_size: 用于预取的 WebDataset 缓存大小（默认：100）
        use_phi_cache: 是否从 parquet 加载 phi 字段（Stage 1.5 开启）
        phi_cache_root: phi_processed 根目录（默认 base_path/phi_processed）
        two_view: 季节对比模式（D1）。每样本取 2 个不同季节构成正例对。
    """

    def __init__(
        self,
        split: str = "train",
        random_season: bool = False,
        base_path: str = "/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1",
        shard_pattern: str = "*.tar",
        normalize: bool = True,
        cache_size: int = 100,
        use_phi_cache: bool = False,
        phi_cache_root: Optional[str] = None,
        two_view: bool = False,
        v3_geom_root: Optional[str] = None,
        conditioned_pair: bool = False,
    ):
        self.split = split
        self.random_season = random_season
        self.base_path = base_path
        self.shard_pattern = shard_pattern
        self.normalize = normalize
        self.cache_size = cache_size
        self.use_phi_cache = use_phi_cache
        self.phi_cache_root = phi_cache_root or os.path.join(base_path, 'phi_processed')
        # phi v3 S1 SAR 几何根目录（方案 A：启用 use_sar_geometry 时 merge 进 S1 phi）
        self.v3_geom_root = v3_geom_root
        # ⭐ 季节对比模式（D1）：每个样本取 2 个不同季节作为正例对
        self.two_view = two_view
        self.conditioned_pair = conditioned_pair
        if self.two_view and self.conditioned_pair:
            raise ValueError("two_view and conditioned_pair are mutually exclusive")

        # 校验 split
        if split not in ["train", "val"]:
            raise ValueError(f"Unknown split: {split}. Valid: ['train', 'val']")

        # 构造两个模态的 shard 路径（os 已在模块顶部 import）
        self.s1_shard_path = os.path.join(base_path, split, "S1GRD", shard_pattern)
        self.s2_shard_path = os.path.join(base_path, split, "S2L2A", shard_pattern)


def parse_dual_sample(
    s1_zarr_bytes: bytes,
    s2_zarr_bytes: bytes,
    random_season: bool = False,
    sample_key: Optional[str] = None,
    phi_cache_s1: Optional[PhiCache] = None,
    phi_cache_s2: Optional[PhiCache] = None,
    two_view: bool = False,
    conditioned_pair: bool = False,
) -> Dict[str, Any]:
    """解析 S1 和 S2 的 zarr.zip 文件，返回配对的双模态样本。

    Args:
        s1_zarr_bytes: S1GRD zarr.zip 原始字节
        s2_zarr_bytes: S2L2A zarr.zip 原始字节
        random_season: 若为 True，则随机选择一个季节；否则返回所有季节
        sample_key: tar 的 __key__（= parquet sample_key），用于 join phi 缓存。
        phi_cache_s1 / phi_cache_s2: PhiCache 实例。
        two_view: ⭐ 季节对比模式（D1）。为 True 时随机选 **2 个不同季节**，
            返回 view1 / view2 两套 (s1_image, s2_image, season_idx)，
            并附带各自季节对应的单时间片 phi（phi_s1_v1/v2, phi_s2_v1/v2 + season_idx）。

    Returns:
        dict。two_view=False 时同旧行为；two_view=True 时含：
            - s1_image_v1/v2, s2_image_v1/v2: [C,H,W]
            - season_v1, season_v2: int（选中的季节索引 t）
            - phi_s1 / phi_s2: 完整 phi_dict（4 季都在，供 dataloader 按 t 取片）
            - sample_key, sample_id

    注意：phi join 主键是 tar 的 __key__（sample_key），**不是** zarr 的 sample 字段。
    """
    import random

    # 解析 S1GRD
    bio_s1 = io.BytesIO(s1_zarr_bytes)
    zf_s1 = zipfile.ZipFile(bio_s1, 'r')
    store_s1 = KVStore(ZipFileStore(zf_s1))
    root_s1 = zarr.open(store_s1, mode='r')

    s1_bands = np.array(root_s1['bands'])  # [4, 2, 264, 264]
    s1_sample_id = str(root_s1['sample'][()])

    # 解析 S2L2A
    bio_s2 = io.BytesIO(s2_zarr_bytes)
    zf_s2 = zipfile.ZipFile(bio_s2, 'r')
    store_s2 = KVStore(ZipFileStore(zf_s2))
    root_s2 = zarr.open(store_s2, mode='r')

    s2_bands = np.array(root_s2['bands'])  # [4, 12, 264, 264]
    s2_cloud_mask = np.array(root_s2['cloud_mask'])  # [4, 264, 264]
    center_lat = float(root_s2['center_lat'][()])
    center_lon = float(root_s2['center_lon'][()])
    time = np.array(root_s2['time'])  # [4]
    s2_sample_id = str(root_s2['sample'][()])

    # 校验两个模态的 sample_id 一致
    assert s1_sample_id == s2_sample_id, \
        f"Sample ID mismatch: S1={s1_sample_id}, S2={s2_sample_id}"

    # phi 缓存查表（完整 4 季 dict，dataloader 再按选中的 t 取单片）
    phi_s1_full = None
    phi_s2_full = None
    if phi_cache_s1 is not None:
        phi_s1_full = phi_cache_s1.lookup_or_default(sample_key) if sample_key is not None \
            else {f: None for f in phi_cache_s1.fields}
    if phi_cache_s2 is not None:
        phi_s2_full = phi_cache_s2.lookup_or_default(sample_key) if sample_key is not None \
            else {f: None for f in phi_cache_s2.fields}

    # ===== Stage1.5 双端条件化：同一季节索引的 S1/S2 配对 =====
    if conditioned_pair:
        t = random.randrange(4) if random_season else 0
        result = {
            's1_image': s1_bands[t], 's2_image': s2_bands[t],
            'season_idx': t, 'cloud_mask': s2_cloud_mask[t],
            'sample_id': s1_sample_id, 'sample_key': sample_key,
        }
        if phi_s1_full is not None:
            result['phi_s1'] = phi_s1_full
        if phi_s2_full is not None:
            result['phi_s2'] = phi_s2_full
        store_s1.close()
        store_s2.close()
        return result

    # ===== ⭐ 季节对比模式（D1）：选 2 个不同季节 =====
    if two_view:
        t1, t2 = random.sample(range(4), 2)  # 不重复的两季
        result = {
            's1_image_v1': s1_bands[t1], 's2_image_v1': s2_bands[t1], 'season_v1': t1,
            's1_image_v2': s1_bands[t2], 's2_image_v2': s2_bands[t2], 'season_v2': t2,
            'cloud_mask_v1': s2_cloud_mask[t1], 'cloud_mask_v2': s2_cloud_mask[t2],
            'sample_id': s1_sample_id,
            'sample_key': sample_key,
        }
        if phi_s1_full is not None:
            result['phi_s1'] = phi_s1_full
        if phi_s2_full is not None:
            result['phi_s2'] = phi_s2_full
        store_s1.close()
        store_s2.close()
        return result

    # ===== 旧行为：单季 / 全季 =====
    if random_season:
        season_idx = random.randint(0, 3)
        s1_image = s1_bands[season_idx]
        s2_image = s2_bands[season_idx]
        cloud_mask_out = s2_cloud_mask[season_idx]
        time_out = np.array([time[season_idx]])
        season_out = season_idx
    else:
        s1_image = s1_bands
        s2_image = s2_bands
        cloud_mask_out = s2_cloud_mask
        time_out = time
        season_out = list(range(4))

    result = {
        's1_image': s1_image,
        's2_image': s2_image,
        'phi': {
            's1_sensor': 'S1GRD',
            's2_sensor': 'S2L2A',
            'season': season_out,
            'cloud_mask': cloud_mask_out,
            'lat': center_lat,
            'lon': center_lon,
            'time': time_out,
        },
        'sample_id': s1_sample_id,
        'sample_key': sample_key,
    }
    if phi_s1_full is not None:
        result['phi_s1'] = phi_s1_full
    if phi_s2_full is not None:
        result['phi_s2'] = phi_s2_full

    store_s1.close()
    store_s2.close()
    return result


def collate_dual_fn(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """双模态样本的 collate 函数。"""
    if not batch:
        return {}

    # 堆叠图像
    s1_images = torch.stack([sample['s1_image'] for sample in batch], dim=0)
    s2_images = torch.stack([sample['s2_image'] for sample in batch], dim=0)

    # 收集 phi 元数据
    phi_batch = {
        's1_sensor': [sample['phi']['s1_sensor'] for sample in batch],
        's2_sensor': [sample['phi']['s2_sensor'] for sample in batch],
        'season': [sample['phi']['season'] for sample in batch],
        'cloud_mask': torch.stack([sample['phi']['cloud_mask'] for sample in batch], dim=0),
        'lat': torch.tensor([sample['phi']['lat'] for sample in batch], dtype=torch.float32),
        'lon': torch.tensor([sample['phi']['lon'] for sample in batch], dtype=torch.float32),
        'time': torch.stack([sample['phi']['time'] for sample in batch], dim=0),
    }

    sample_ids = [sample['sample_id'] for sample in batch]
    sample_keys = [sample.get('sample_key') for sample in batch]

    out = {
        's1_image': s1_images,
        's2_image': s2_images,
        'phi': phi_batch,
        'sample_id': sample_ids,
        'sample_key': sample_keys,
    }

    # Stage 1.5：若样本带 PhiCache 查到的 phi_dict，转成 tensor dict
    # （供 ImagingConditionEncoder 直接消费）。缺失字段已在 phi_loader 填为 NaN/-1。
    if 'phi_s1' in batch[0]:
        out['s1_phi'] = batch_phi_dicts_to_tensors([s['phi_s1'] for s in batch])
    if 'phi_s2' in batch[0]:
        out['s2_phi'] = batch_phi_dicts_to_tensors([s['phi_s2'] for s in batch])

    return out


def collate_dual_two_view_fn(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """⭐ 季节对比模式 collate（D1）。

    每个样本含 view1/view2 两套图像 + 各自季节索引，以及完整 4 季 phi dict。
    本函数把两视图的图像分别堆叠，并按各视图选中的季节 t 取**单时间片** phi。
    """
    if not batch:
        return {}
    from ..phi_loader import batch_phi_single_timestep_to_tensors

    out = {
        's1_image_v1': torch.stack([b['s1_image_v1'] for b in batch], dim=0),
        's2_image_v1': torch.stack([b['s2_image_v1'] for b in batch], dim=0),
        's1_image_v2': torch.stack([b['s1_image_v2'] for b in batch], dim=0),
        's2_image_v2': torch.stack([b['s2_image_v2'] for b in batch], dim=0),
        'cloud_mask_v1': torch.stack([b['cloud_mask_v1'] for b in batch], dim=0),
        'cloud_mask_v2': torch.stack([b['cloud_mask_v2'] for b in batch], dim=0),
        'sample_key': [b.get('sample_key') for b in batch],
        'sample_id': [b['sample_id'] for b in batch],
    }
    season_v1 = [int(b['season_v1']) for b in batch]
    season_v2 = [int(b['season_v2']) for b in batch]
    out['season_v1'] = torch.tensor(season_v1, dtype=torch.long)
    out['season_v2'] = torch.tensor(season_v2, dtype=torch.long)

    # 单时间片 phi：按各视图选中的季节 t 取对应字段（D3）
    if 'phi_s1' in batch[0]:
        p_s1 = [b['phi_s1'] for b in batch]
        out['s1_phi_v1'] = batch_phi_single_timestep_to_tensors(p_s1, season_v1)
        out['s1_phi_v2'] = batch_phi_single_timestep_to_tensors(p_s1, season_v2)
    if 'phi_s2' in batch[0]:
        p_s2 = [b['phi_s2'] for b in batch]
        out['s2_phi_v1'] = batch_phi_single_timestep_to_tensors(p_s2, season_v1)
        out['s2_phi_v2'] = batch_phi_single_timestep_to_tensors(p_s2, season_v2)
    return out


def collate_dual_conditioned_pair_fn(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Collate one same-season-index S1/S2 pair for dual-conditioned Stage1.5."""
    if not batch:
        return {}
    from ..phi_loader import batch_phi_single_timestep_to_tensors

    season_indices = [int(b['season_idx']) for b in batch]
    out = {
        's1_image': torch.stack([b['s1_image'] for b in batch], dim=0),
        's2_image': torch.stack([b['s2_image'] for b in batch], dim=0),
        'cloud_mask': torch.stack([b['cloud_mask'] for b in batch], dim=0),
        'season_idx': torch.tensor(season_indices, dtype=torch.long),
        'sample_key': [b.get('sample_key') for b in batch],
        'sample_id': [b['sample_id'] for b in batch],
    }
    if 'phi_s1' in batch[0]:
        out['s1_phi'] = batch_phi_single_timestep_to_tensors(
            [b['phi_s1'] for b in batch], season_indices)
    if 'phi_s2' in batch[0]:
        out['s2_phi'] = batch_phi_single_timestep_to_tensors(
            [b['phi_s2'] for b in batch], season_indices)

    if 's1_phi' in out and 's2_phi' in out:
        t1, t2 = out['s1_phi']['time'], out['s2_phi']['time']
        valid = out['s1_phi']['time_valid'].gt(0) & out['s2_phi']['time_valid'].gt(0)
        delta_ns = (t1 - t2).abs().to(torch.float64)
        out['time_delta_days'] = (delta_ns / 86_400_000_000_000.0).to(torch.float32)
        out['time_pair_valid'] = valid
    return out


def _expand_and_filter(shard_path: str) -> List[str]:
    """展开 brace 模式（如 {000001..000477}）并过滤出实际存在的 shard 文件。

    优化：使用缓存避免每次初始化时对 477 个文件逐个 os.path.exists（NFS 慢）。
    缓存文件：{data_root}/.shard_cache_{hash}.txt
    """
    import hashlib
    import pickle

    # 生成 cache key（基于 shard_path）
    cache_key = hashlib.md5(shard_path.encode()).hexdigest()[:16]
    # 推导 data_root（取 shard_path 的父目录的父目录，假设是 .../train/S2L2A/*.tar）
    try:
        sample_expanded = list(braceexpand(shard_path))[:1]
        if sample_expanded:
            data_root = os.path.dirname(os.path.dirname(sample_expanded[0]))
        else:
            data_root = "/tmp"
    except:
        data_root = "/tmp"

    cache_file = os.path.join(data_root, f".shard_cache_{cache_key}.pkl")

    # 尝试加载缓存
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                cached = pickle.load(f)
            # 验证缓存有效性：只检查第一个和最后一个文件是否存在
            if len(cached) >= 2 and os.path.exists(cached[0]) and os.path.exists(cached[-1]):
                return cached
        except:
            pass  # 缓存损坏，重新构建

    # 缓存未命中或失效，重新枚举（只在 rank 0 做，避免 8 个 rank 并发 stat）
    import torch.distributed as dist
    if dist.is_available() and dist.is_initialized():
        rank = dist.get_rank()
    else:
        rank = 0

    if rank == 0:
        # 先用 braceexpand 处理 {x..y} 模式，再用 glob 处理 * 通配符
        import glob as glob_module
        expanded = list(braceexpand(shard_path))
        shards = []
        for pattern in expanded:
            # 如果包含 * 或 ? 通配符，用 glob 展开
            if '*' in pattern or '?' in pattern:
                shards.extend(glob_module.glob(pattern))
            elif os.path.exists(pattern):
                shards.append(pattern)

        if not shards:
            raise FileNotFoundError(f"未找到任何匹配的 shard: {shard_path}")
        shards = sorted(shards)
        # 写缓存
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(shards, f)
        except:
            pass  # 写失败不影响训练
    else:
        # 非 rank 0 等待 rank 0 写完缓存
        shards = None

    # 广播给其他 rank（避免它们也去 stat 文件）
    if dist.is_available() and dist.is_initialized():
        from torch.distributed import broadcast_object_list
        shards_list = [shards]
        broadcast_object_list(shards_list, src=0)
        shards = shards_list[0]

    if not shards:
        raise FileNotFoundError(f"未找到任何匹配的 shard: {shard_path}")

    return shards


def _process_pair(
    s1_sample, s2_sample, config: SSL4EODualConfig,
    phi_cache_s1: Optional[PhiCache] = None,
    phi_cache_s2: Optional[PhiCache] = None,
) -> Optional[Dict[str, Any]]:
    """把一对原始 WebDataset 样本解析、归一化、裁剪为张量字典。失败返回 None。

    关键：S1/S2 的 __key__ 一致（已实测验证），用它作为 phi join 的 sample_key。
    支持 two_view 模式（D1）：返回 view1/view2 两套图像。
    """
    try:
        s1_key = s1_sample.get('__key__')
        s2_key = s2_sample.get('__key__')
        assert s1_key == s2_key, f"__key__ mismatch: S1={s1_key}, S2={s2_key}"
        sample_key = s1_key

        parsed = parse_dual_sample(
            s1_sample['zarr.zip'], s2_sample['zarr.zip'], config.random_season,
            sample_key=sample_key,
            phi_cache_s1=phi_cache_s1,
            phi_cache_s2=phi_cache_s2,
            two_view=config.two_view,
            conditioned_pair=config.conditioned_pair,
        )

        def _prep(arr_s1, arr_s2, cmask):
            """归一化 + to-tensor + 中心裁剪 264→256。"""
            if config.normalize:
                arr_s1 = normalize_image(arr_s1, 'S1GRD')
                arr_s2 = normalize_image(arr_s2, 'S2L2A')
            t_s1 = torch.from_numpy(arr_s1).float()
            t_s2 = torch.from_numpy(arr_s2).float()
            t_cm = torch.from_numpy(cmask).float()
            if t_s1.shape[-1] == 264:
                s = 4
                t_s1 = t_s1[..., s:s + 256, s:s + 256]
                t_s2 = t_s2[..., s:s + 256, s:s + 256]
                t_cm = t_cm[..., s:s + 256, s:s + 256]
            return t_s1, t_s2, t_cm

        if config.two_view:
            v1 = _prep(parsed['s1_image_v1'], parsed['s2_image_v1'], parsed['cloud_mask_v1'])
            v2 = _prep(parsed['s1_image_v2'], parsed['s2_image_v2'], parsed['cloud_mask_v2'])
            parsed['s1_image_v1'], parsed['s2_image_v1'], parsed['cloud_mask_v1'] = v1
            parsed['s1_image_v2'], parsed['s2_image_v2'], parsed['cloud_mask_v2'] = v2
            return parsed

        if config.conditioned_pair:
            pair = _prep(parsed['s1_image'], parsed['s2_image'], parsed['cloud_mask'])
            parsed['s1_image'], parsed['s2_image'], parsed['cloud_mask'] = pair
            return parsed

        # 单/全季旧行为
        if config.normalize:
            parsed['s1_image'] = normalize_image(parsed['s1_image'], 'S1GRD')
            parsed['s2_image'] = normalize_image(parsed['s2_image'], 'S2L2A')
        parsed['s1_image'] = torch.from_numpy(parsed['s1_image']).float()
        parsed['s2_image'] = torch.from_numpy(parsed['s2_image']).float()
        parsed['phi']['cloud_mask'] = torch.from_numpy(parsed['phi']['cloud_mask']).float()
        parsed['phi']['time'] = torch.from_numpy(parsed['phi']['time']).long()
        if parsed['s1_image'].shape[-1] == 264:
            start = 4
            parsed['s1_image'] = parsed['s1_image'][..., start:start + 256, start:start + 256]
            parsed['s2_image'] = parsed['s2_image'][..., start:start + 256, start:start + 256]
            parsed['phi']['cloud_mask'] = parsed['phi']['cloud_mask'][..., start:start + 256, start:start + 256]
        return parsed
    except Exception as e:
        print(f"[警告] 样本处理失败: {e}")
        return None


class SSL4EODualIterableDataset(IterableDataset):
    """双模态 SSL4EO IterableDataset。

    关键设计：S1 和 S2 必须读取相同编号、相同顺序的 shard 才能保证配对正确，
    因此不能用 WebDataset 内置的 nodesplitter（它对两个流独立打乱/切分会错位）。
    本类显式按 (rank, worker) 把 **同一份 shard 索引列表** 切分给每个加载单元，
    再分别构造 S1/S2 的 WebDataset 读这批 shard，zip 后保证逐样本对齐。

    - 多进程：每个 DataLoader worker 拿到 rank 内 shard 的不相交子集，真正并行解压。
    - shuffle：用同一随机种子打乱 S1/S2 的 shard 顺序，再加配对级 shuffle buffer。
    - infinite：分布式下数据耗尽自动重头，避免某 rank 先跑完导致 NCCL 卡死。
    """

    def __init__(
        self,
        config: SSL4EODualConfig,
        shuffle: bool = True,
        infinite: bool = False,
        shuffle_buffer: int = 1000,
        seed: int = 0,
    ):
        super().__init__()
        self.config = config
        self.shuffle = shuffle
        self.infinite = infinite
        self.shuffle_buffer = shuffle_buffer
        self.seed = seed

        # phi 缓存延迟构建：在 worker 进程内首次使用时加载（见 _get_phi_caches）。
        # 不在 __init__ 加载，避免主进程加载的大索引被 fork 复制 num_workers 份后又重复加载。
        self._phi_cache_s1 = None
        self._phi_cache_s2 = None
        self._phi_caches_ready = False

        # 展开并校验两个模态的 shard 列表，要求一一对应
        self.s1_shards = _expand_and_filter(config.s1_shard_path)
        self.s2_shards = _expand_and_filter(config.s2_shard_path)
        if len(self.s1_shards) != len(self.s2_shards):
            raise ValueError(
                f"S1/S2 shard 数量不一致: S1={len(self.s1_shards)}, S2={len(self.s2_shards)}"
            )

    def _get_phi_caches(self):
        """延迟加载 PhiCache（每个 worker 进程独立加载一次）。

        config.use_phi_cache=False 时返回 (None, None)，保持旧行为（从 zarr 内联提取）。
        """
        if not self.config.use_phi_cache:
            return None, None
        if not self._phi_caches_ready:
            worker_info = torch.utils.data.get_worker_info()
            wid = worker_info.id if worker_info is not None else 0
            verbose = (wid == 0)  # 只让 worker0 打印加载日志，避免刷屏
            self._phi_cache_s1 = PhiCache(
                self.config.phi_cache_root, self.config.split, 'S1GRD', verbose=verbose,
                v3_geom_root=getattr(self.config, 'v3_geom_root', None),
            )
            self._phi_cache_s2 = PhiCache(
                self.config.phi_cache_root, self.config.split, 'S2L2A', verbose=verbose,
            )
            self._phi_caches_ready = True
        return self._phi_cache_s1, self._phi_cache_s2

    def _shard_indices_for_this_unit(self) -> List[int]:
        """按 (rank, worker) 把 shard 索引切分给当前加载单元。"""
        n = len(self.s1_shards)
        indices = list(range(n))

        # 1) 分布式：按 rank 切
        if dist.is_available() and dist.is_initialized():
            rank = dist.get_rank()
            world_size = dist.get_world_size()
        else:
            rank, world_size = 0, 1
        indices = indices[rank::world_size]

        # 2) 多进程：按 worker 再切一层
        worker_info = torch.utils.data.get_worker_info()
        if worker_info is not None:
            indices = indices[worker_info.id::worker_info.num_workers]

        return indices

    def _build_pair_stream(self, shard_indices: List[int], epoch: int):
        """为给定 shard 索引构造一个 S1/S2 配对样本流（单趟，不循环）。"""
        idx = list(shard_indices)
        if self.shuffle:
            # S1/S2 用同一序列打乱，保证配对不错位
            rng = random.Random(self.seed + epoch)
            rng.shuffle(idx)

        s1_urls = [self.s1_shards[i] for i in idx]
        s2_urls = [self.s2_shards[i] for i in idx]
        if not s1_urls:
            return

        # phi 缓存（仅在 worker 内首次构建一次）
        phi_cache_s1, phi_cache_s2 = self._get_phi_caches()

        # 单元内已切好 shard，关掉 WebDataset 自身的 node/worker 切分
        ds_s1 = wds.WebDataset(
            s1_urls, shardshuffle=False, nodesplitter=None,
            workersplitter=None, empty_check=False, handler=wds.warn_and_continue,
        ).decode()
        ds_s2 = wds.WebDataset(
            s2_urls, shardshuffle=False, nodesplitter=None,
            workersplitter=None, empty_check=False, handler=wds.warn_and_continue,
        ).decode()

        for s1_sample, s2_sample in zip(ds_s1, ds_s2):
            parsed = _process_pair(
                s1_sample, s2_sample, self.config,
                phi_cache_s1=phi_cache_s1, phi_cache_s2=phi_cache_s2,
            )
            if parsed is not None:
                yield parsed

    def __iter__(self):
        shard_indices = self._shard_indices_for_this_unit()

        def raw_stream():
            epoch = 0
            while True:
                yield from self._build_pair_stream(shard_indices, epoch)
                if not self.infinite:
                    break
                epoch += 1

        stream = raw_stream()

        # 配对级 shuffle buffer：在样本层面再打乱，弥补关闭 shardshuffle 的随机性
        if self.shuffle and self.shuffle_buffer > 1:
            stream = wds.filters.shuffle(self.shuffle_buffer)(stream)

        return stream


def create_ssl4eo_dual_dataset(
    config: SSL4EODualConfig,
    batch_size: Optional[int] = None,
    num_workers: int = 4,
    shuffle: bool = False,
    infinite: bool = False,
    prefetch_factor: int = 4,
    seed: int = 0,
):
    """创建双模态数据 DataLoader（多进程并行加载）。

    Returns:
        若 batch_size 为 None：返回未分批的 IterableDataset；
        否则返回 PyTorch DataLoader（多进程 + prefetch + pin_memory）。
    """
    dataset = SSL4EODualIterableDataset(
        config,
        shuffle=shuffle,
        infinite=infinite,
        shuffle_buffer=config.cache_size if shuffle else 1,
        seed=seed,
    )

    if not batch_size:
        return dataset

    if config.conditioned_pair:
        collate = collate_dual_conditioned_pair_fn
    elif config.two_view:
        collate = collate_dual_two_view_fn
    else:
        collate = collate_dual_fn
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        num_workers=num_workers,
        collate_fn=collate,
        pin_memory=True,
        drop_last=True,
        persistent_workers=(num_workers > 0),
        prefetch_factor=(prefetch_factor if num_workers > 0 else None),
    )
    return loader


if __name__ == "__main__":
    # 测试双模态数据加载（含 Stage 1.5 phi 缓存集成）
    config = SSL4EODualConfig(
        split="train",
        random_season=True,
        normalize=True,
        use_phi_cache=True,   # Stage 1.5：开启 phi 缓存 join
        shard_pattern="ssl4eos12_shard_{000001..000002}.tar",  # 只测前 2 个 shard
    )

    print(f"双模态 SSL4EO 数据集加载测试 (use_phi_cache={config.use_phi_cache}):")
    print(f"  Split: {config.split}")
    print(f"  S1 shard path: {config.s1_shard_path}")
    print(f"  S2 shard path: {config.s2_shard_path}")
    print(f"  phi_cache_root: {config.phi_cache_root}")

    # num_workers=0 便于在主进程内直接调试 phi join
    dataset = create_ssl4eo_dual_dataset(config, batch_size=4, num_workers=0, shuffle=False)

    print("\n迭代测试...")
    for i, batch in enumerate(dataset):
        if i >= 1:
            break

        print(f"\nBatch {i}:")
        print(f"  S1 image shape: {batch['s1_image'].shape}")
        print(f"  S2 image shape: {batch['s2_image'].shape}")
        print(f"  Cloud mask shape: {batch['phi']['cloud_mask'].shape}")
        print(f"  Sample keys: {batch['sample_key']}")
        if 's2_phi' in batch:
            print(f"  s2_phi 字段: {list(batch['s2_phi'].keys())}")
            print(f"    sun_elevation: shape={batch['s2_phi']['sun_elevation'].shape}, "
                  f"值={batch['s2_phi']['sun_elevation'][0].tolist()}")
            print(f"    season: {batch['s2_phi']['season'][0].tolist()}")
            print(f"    center_lat/lon: {batch['s2_phi']['center_lat'].tolist()}, "
                  f"{batch['s2_phi']['center_lon'].tolist()}")
            print(f"    cloud_cover: {batch['s2_phi']['cloud_cover'][0].tolist()}")
        if 's1_phi' in batch:
            print(f"  s1_phi modality codes: {batch['s1_phi']['modality'].tolist()}")

    print("\n数据集测试完成！")
