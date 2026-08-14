"""
基于 WebDataset 的 SSL4EO-S12 数据加载器。

本模块使用 WebDataset 为 SSL4EO-S12 数据集提供流式数据加载器，
可高效加载包含 zarr.zip 文件的 tar 分片（shard）。

SSL4EO-S12 数据集包含以 zarr 格式存储于 tar 归档中的多季节、多模态卫星影像。
每个样本由 4 个季节的观测组成，对应 Sentinel-2 L2A 数据的 12 个光谱波段。

主要特性：
- 从 tar 分片流式读取，避免将整个数据集载入内存
- 支持多种模态（S2L2A、S2RGB 等）
- 可选的随机季节选择，用于时序数据增强
- 高效的 zarr 解析与元数据提取

数据结构：
- S2L2A: shape [4_seasons, 12_bands, 264, 264], dtype int16
- S2RGB: shape [4_seasons, 3_bands, 264, 264], dtype uint8
- 每个样本包含云掩膜（cloud mask）、坐标和时序信息

Returns:
    dict: {
        'image': Tensor [T,C,H,W]，若 random_season=True 则为 [C,H,W],
        'phi': {
            'sensor': str（例如 'S2L2A'）,
            'season': int (0-3) 或 int 列表,
            'cloud_mask': Tensor [T,H,W] 或 [H,W],
            'lat': float,
            'lon': float,
            'time': Tensor [T] 或标量,
        },
        'modality': str,
        'sample_id': str,
        'field_mask': {'image': 1, 'phi': 1, ...}
    }
"""

import io
import json
import os
import random
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import torch
import webdataset as wds
import zarr
from zarr.storage import KVStore


class ZipFileStore:
    """将 ZipFile 包装为可在 zarr 2.x 中使用的 zarr store。"""

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


class SSL4EOConfig:
    """SSL4EO 数据集加载的配置。

    Attributes:
        modality: 传感器/模态类型（例如 'S2L2A'、'S2RGB'、'S1GRD'、'DEM'、'LULC'、'NDVI'）。
        split: 数据集划分（'train' 或 'val'）。
        random_season: 若为 True，则随机选择一个季节；否则返回全部 4 个季节。
        base_path: 包含 SSL4EO-S12 数据的根目录。
        shard_pattern: 匹配 tar 分片的模式（默认：所有分片）。
        normalize: 若为 True，则根据模态将图像归一化到 [0, 1] 范围。
        cache_size: 用于预取的 WebDataset 缓存大小（默认：100）。
    """

    def __init__(
        self,
        modality: str = "S2L2A",
        split: str = "train",
        random_season: bool = False,
        base_path: str = "/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1",
        shard_pattern: str = "*.tar",
        normalize: bool = False,
        cache_size: int = 100,
    ):
        """初始化 SSL4EO 配置。

        Args:
            modality: 传感器/模态类型。
            split: 数据集划分（'train' 或 'val'）。
            random_season: 是否随机选择单个季节。
            base_path: SSL4EO-S12 数据集的根目录。
            shard_pattern: 用于匹配 tar 分片的 glob 模式。
            normalize: 是否对图像进行归一化。
            cache_size: 预取的样本数量。
        """
        self.modality = modality
        self.split = split
        self.random_season = random_season
        self.base_path = base_path
        self.shard_pattern = shard_pattern
        self.normalize = normalize
        self.cache_size = cache_size

        # 校验 modality
        valid_modalities = ["S2L2A", "S2RGB", "S1GRD", "S2L1C", "DEM", "LULC", "NDVI"]
        if modality not in valid_modalities:
            raise ValueError(f"Unknown modality: {modality}. Valid options: {valid_modalities}")

        # 校验 split
        if split not in ["train", "val"]:
            raise ValueError(f"Unknown split: {split}. Valid options: ['train', 'val']")

        # 构造分片路径
        self.shard_path = os.path.join(base_path, split, modality, shard_pattern)


def parse_zarr_sample(zarr_bytes: bytes, modality: str, random_season: bool = False) -> Dict[str, Any]:
    """解析 zarr.zip 文件并提取图像数据与元数据。

    Args:
        zarr_bytes: zarr.zip 文件的原始字节。
        modality: 模态类型（例如 'S2L2A'、'S2RGB'）。
        random_season: 若为 True，则随机选择一个季节；否则返回所有季节。

    Returns:
        包含以下内容的字典：
            - image: numpy 数组 [T,C,H,W] 或 [C,H,W]
            - phi: 元数据字典，含 sensor、season、cloud_mask、lat、lon、time
            - modality: str
            - sample_id: str
            - field_mask: 指示哪些字段存在的字典
    """
    # 从 zip 字节打开 zarr store
    bio = io.BytesIO(zarr_bytes)
    zf = zipfile.ZipFile(bio, 'r')
    store = KVStore(ZipFileStore(zf))
    root = zarr.open(store, mode='r')

    # 提取图像数据：S2L2A 的 shape 为 [4, 12, 264, 264]
    bands = np.array(root['bands'])  # [T, C, H, W]

    # 提取元数据
    cloud_mask = np.array(root['cloud_mask'])  # [T, H, W]
    center_lat = float(root['center_lat'][()])
    center_lon = float(root['center_lon'][()])
    time = np.array(root['time'])  # [T]
    sample_id = str(root['sample'][()]) if 'sample' in root else "unknown"

    # 季节选择
    if random_season:
        season_idx = random.randint(0, 3)
        image = bands[season_idx]  # [C, H, W]
        cloud_mask_out = cloud_mask[season_idx]  # [H, W]
        time_out = np.array([time[season_idx]])  # 使其成为 shape 为 [1] 的数组
        season_out = season_idx
    else:
        image = bands  # [T, C, H, W]
        cloud_mask_out = cloud_mask  # [T, H, W]
        time_out = time  # [T]
        season_out = list(range(4))

    # 构造输出
    result = {
        'image': image,
        'phi': {
            'sensor': modality,
            'season': season_out,
            'cloud_mask': cloud_mask_out,
            'lat': center_lat,
            'lon': center_lon,
            'time': time_out,
        },
        'modality': modality,
        'sample_id': sample_id,
        'field_mask': {
            'image': 1,
            'phi': 1,
            'modality': 1,
            'sample_id': 1,
        }
    }

    store.close()
    return result


def normalize_image(image: np.ndarray, modality: str) -> np.ndarray:
    """根据模态特定的取值范围对图像进行归一化。

    Args:
        image: 待归一化的图像数组。
        modality: 决定归一化策略的模态类型。

    Returns:
        归一化到 [0, 1] 范围的图像。
    """
    if modality == "S2L2A":
        # S2L2A: int16，取值范围通常为 0-10000
        image = image.astype(np.float32)
        image = np.clip(image, 0, 10000) / 10000.0
    elif modality == "S2RGB":
        # S2RGB: uint8，取值范围 0-255
        image = image.astype(np.float32) / 255.0
    elif modality == "S1GRD":
        # S1GRD: SAR 数据，通常需要不同的归一化方式
        # 目前先使用简单的 min-max 归一化
        image = image.astype(np.float32)
        image = (image - image.min()) / (image.max() - image.min() + 1e-8)
    else:
        # 通用归一化
        image = image.astype(np.float32)
        if image.max() > 1.0:
            image = image / 255.0

    return image


def collate_fn(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """用于对 SSL4EO 样本进行批处理（batching）的 collate 函数。

    Args:
        batch: 样本字典组成的列表。

    Returns:
        包含堆叠后张量的批处理字典。
    """
    if not batch:
        return {}

    # 堆叠图像
    images = torch.stack([sample['image'] for sample in batch], dim=0)

    # 收集 phi 元数据
    phi_batch = {
        'sensor': [sample['phi']['sensor'] for sample in batch],
        'season': [sample['phi']['season'] for sample in batch],
        'cloud_mask': torch.stack([sample['phi']['cloud_mask'] for sample in batch], dim=0),
        'lat': torch.tensor([sample['phi']['lat'] for sample in batch], dtype=torch.float32),
        'lon': torch.tensor([sample['phi']['lon'] for sample in batch], dtype=torch.float32),
        'time': torch.stack([sample['phi']['time'] for sample in batch], dim=0),
    }

    # 收集其他字段
    modalities = [sample['modality'] for sample in batch]
    sample_ids = [sample['sample_id'] for sample in batch]
    field_masks = [sample['field_mask'] for sample in batch]

    return {
        'image': images,
        'phi': phi_batch,
        'modality': modalities,
        'sample_id': sample_ids,
        'field_mask': field_masks,
    }


def create_ssl4eo_dataset(
    config: SSL4EOConfig,
    batch_size: Optional[int] = None,
    num_workers: int = 4,
    shuffle: bool = True,
) -> wds.WebDataset:
    """为 SSL4EO-S12 创建基于 WebDataset 的数据加载器。

    本函数构造一个流式数据加载器，读取包含 zarr.zip 文件的 tar 分片，
    对其进行解析，并产出（yield）批处理后的样本。

    Args:
        config: 指定数据集参数的 SSL4EOConfig。
        batch_size: DataLoader 的批大小。若为 None，则返回未分批的数据集。
        num_workers: 数据加载所用的 worker 进程数量。
        shuffle: 是否对数据集进行打乱。

    Returns:
        为 SSL4EO-S12 流式加载配置好的 WebDataset 实例。

    Example:
        >>> config = SSL4EOConfig(modality='S2L2A', split='train', random_season=True)
        >>> dataset = create_ssl4eo_dataset(config, batch_size=32, shuffle=True)
        >>> for batch in dataset:
        ...     images = batch['image']  # [B, C, H, W]
        ...     metadata = batch['phi']
        ...     # 此处编写训练代码
    """
    # 构造 WebDataset 流水线
    dataset = wds.WebDataset(
        config.shard_path,
        shardshuffle=shuffle,
        nodesplitter=wds.split_by_node,
    )

    if shuffle:
        dataset = dataset.shuffle(config.cache_size)

    def process_sample(sample):
        """处理来自 tar 分片的单个样本。"""
        # WebDataset 以字典形式提供样本，键包括 '__key__'、'zarr.zip' 等
        key = sample['__key__']
        zarr_bytes = sample['zarr.zip']

        # 解析 zarr
        parsed = parse_zarr_sample(
            zarr_bytes,
            modality=config.modality,
            random_season=config.random_season
        )

        # 如有需要则进行归一化
        if config.normalize:
            parsed['image'] = normalize_image(parsed['image'], config.modality)

        # 转换为张量
        parsed['image'] = torch.from_numpy(parsed['image']).float()
        parsed['phi']['cloud_mask'] = torch.from_numpy(parsed['phi']['cloud_mask']).float()
        parsed['phi']['time'] = torch.from_numpy(parsed['phi']['time']).long()

        # 中心裁剪到 256x256（264 -> 256，可被 16 整除）
        if parsed['image'].shape[-1] == 264 and parsed['image'].shape[-2] == 264:
            crop_size = 256
            start = (264 - crop_size) // 2  # 4
            parsed['image'] = parsed['image'][..., start:start+crop_size, start:start+crop_size]
            parsed['phi']['cloud_mask'] = parsed['phi']['cloud_mask'][..., start:start+crop_size, start:start+crop_size]

        return parsed

    dataset = dataset.map(process_sample, handler=wds.warn_and_continue)

    # 分批处理
    if batch_size is not None:
        dataset = dataset.batched(batch_size, collation_fn=collate_fn)

    return dataset


def get_ssl4eo_dataloader(
    config: SSL4EOConfig,
    batch_size: int = 32,
    num_workers: int = 4,
    shuffle: bool = True,
) -> torch.utils.data.DataLoader:
    """获取用于 SSL4EO-S12 数据集的 PyTorch DataLoader。

    这是一个便捷函数，封装了 create_ssl4eo_dataset 并返回标准的 PyTorch DataLoader。

    Args:
        config: 指定数据集参数的 SSL4EOConfig。
        batch_size: 每个批次的样本数量。
        num_workers: 用于并行数据加载的 worker 进程数量。
        shuffle: 是否打乱样本。

    Returns:
        PyTorch DataLoader 实例。

    Example:
        >>> config = SSL4EOConfig(
        ...     modality='S2L2A',
        ...     split='train',
        ...     random_season=True,
        ...     normalize=True
        ... )
        >>> dataloader = get_ssl4eo_dataloader(config, batch_size=16, num_workers=4)
        >>> for batch in dataloader:
        ...     images = batch['image']  # [16, 12, 264, 264] 或 [16, 1, 12, 264, 264]
        ...     print(f"Batch shape: {images.shape}")
        ...     break
    """
    dataset = create_ssl4eo_dataset(
        config=config,
        batch_size=None,  # 分批由 DataLoader 处理
        num_workers=num_workers,
        shuffle=shuffle,
    )

    # 使用 WebDataset 创建 DataLoader
    dataloader = torch.utils.data.DataLoader(
        dataset,
        batch_size=batch_size,
        num_workers=num_workers,
        collate_fn=collate_fn,
        pin_memory=True,
    )

    return dataloader


# 使用示例与测试
if __name__ == "__main__":
    # 测试配置
    config = SSL4EOConfig(
        modality="S2L2A",
        split="train",
        random_season=True,
        normalize=True,
    )

    print(f"Loading SSL4EO dataset:")
    print(f"  Modality: {config.modality}")
    print(f"  Split: {config.split}")
    print(f"  Shard path: {config.shard_path}")
    print(f"  Random season: {config.random_season}")

    # 创建数据集
    dataset = create_ssl4eo_dataset(config, batch_size=4, shuffle=True)

    # 测试迭代
    print("\nTesting dataset iteration...")
    for i, batch in enumerate(dataset):
        if i >= 1:  # 仅测试第一个批次
            break

        print(f"\nBatch {i}:")
        print(f"  Image shape: {batch['image'].shape}")
        print(f"  Image dtype: {batch['image'].dtype}")
        print(f"  Cloud mask shape: {batch['phi']['cloud_mask'].shape}")
        print(f"  Latitude: {batch['phi']['lat']}")
        print(f"  Longitude: {batch['phi']['lon']}")
        print(f"  Season: {batch['phi']['season']}")
        print(f"  Sample IDs: {batch['sample_id']}")
        print(f"  Field mask: {batch['field_mask'][0]}")

    print("\nDataset test complete!")
