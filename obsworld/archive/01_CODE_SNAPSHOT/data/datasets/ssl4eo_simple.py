"""
简化版 SSL4EO 双模态 DataLoader
用于绕过 ssl4eo_dual.py 的 WebDataset hang 问题

设计原则：
- 直接用 tarfile 顺序读，不依赖 WebDataset IterableDataset
- 手动实现 shard 切分（按 rank 和 worker_id）
- 简单可靠，无复杂 pipeline
"""
import os
import io
import random
import tarfile
import zipfile
from typing import List, Dict, Any, Optional
from pathlib import Path

import numpy as np
import torch
import zarr
from zarr.storage import KVStore
from torch.utils.data import IterableDataset, DataLoader

# 复用原始 dataloader 的 ZipFileStore 和归一化（保证与 Stage 1.5 完全一致）
from .ssl4eo import ZipFileStore, normalize_image


class SimpleSSL4EODualDataset(IterableDataset):
    """简化版双模态 SSL4EO 数据集

    假设：
    - S1 和 S2 的 tar 文件一一对应（按文件名排序后）
    - 每个 tar 内的样本按 __key__ 对齐
    """

    def __init__(
        self,
        s1_tar_list: List[str],
        s2_tar_list: List[str],
        random_season: bool = True,
        normalize: bool = True,
        infinite: bool = True,
        seed: int = 0,
    ):
        super().__init__()
        assert len(s1_tar_list) == len(s2_tar_list), \
            f"S1/S2 tar 数量不一致: {len(s1_tar_list)} vs {len(s2_tar_list)}"

        self.s1_tars = sorted(s1_tar_list)
        self.s2_tars = sorted(s2_tar_list)
        self.random_season = random_season
        self.normalize = normalize
        self.infinite = infinite
        self.seed = seed

        # 关键修复：在 __init__（主进程，DataLoader fork 之前）就确定 rank/world_size，
        # 存为实例属性。绝不能在 worker 子进程里调用 dist.*（NCCL 不是 fork-safe，会死锁）。
        import torch.distributed as dist
        if dist.is_available() and dist.is_initialized():
            self.rank = dist.get_rank()
            self.world_size = dist.get_world_size()
        else:
            self.rank = 0
            self.world_size = 1

    def _get_my_shards(self) -> List[int]:
        """按 rank 和 worker_id 切分 shard 索引（rank/world_size 已在 __init__ 缓存）"""
        n_shards = len(self.s1_tars)
        indices = list(range(n_shards))

        # 按 rank 切分（用缓存值，不在 worker 里调 dist.*）
        indices = indices[self.rank::self.world_size]

        # 按 worker 切分
        worker_info = torch.utils.data.get_worker_info()
        if worker_info is not None:
            indices = indices[worker_info.id::worker_info.num_workers]

        return indices

    def _parse_zarr_zip(self, zarr_bytes: bytes) -> Optional[np.ndarray]:
        """从 zarr.zip 字节流解析图像 [4, C, H, W]

        使用与原始 ssl4eo_dual.py 相同的方法：
        zipfile.ZipFile -> ZipFileStore -> KVStore -> zarr.open
        数据 key 是 'bands'，形状 [4 seasons, C, 264, 264]
        """
        try:
            bio = io.BytesIO(zarr_bytes)
            zf = zipfile.ZipFile(bio, 'r')
            store = KVStore(ZipFileStore(zf))
            root = zarr.open(store, mode='r')
            arr = np.array(root['bands'])  # [4, C, 264, 264]
            return arr
        except Exception as e:
            return None

    def _read_tar_pairs(self, s1_tar_path: str, s2_tar_path: str):
        """从一对 tar 文件中流式读取配对样本。

        关键优化（修复 I/O 风暴）：S1/S2 tar 成员顺序完全一致（已验证），
        所以用 tarfile 的流式迭代逐成员配对，**不把整个 tar 载入内存**。
        旧实现把整个 S1 tar（~2GB）读进 dict 才 yield 第一个样本，128 个 worker
        同时这么干 = 启动 I/O 风暴，首 batch 要几分钟。

        流式迭代 `for member in tf` 顺序读取，第一个样本立刻可用。
        """
        try:
            # 用流式模式打开（'r|' 比 'r' 更省内存，但 'r' 也支持顺序迭代）
            with tarfile.open(s1_tar_path, 'r') as tf_s1, \
                 tarfile.open(s2_tar_path, 'r') as tf_s2:

                it_s1 = iter(tf_s1)
                it_s2 = iter(tf_s2)

                for m_s1, m_s2 in zip(it_s1, it_s2):
                    # 跳过非 zarr.zip 成员（保持两边同步）
                    if not m_s1.name.endswith('.zarr.zip'):
                        continue
                    if not m_s2.name.endswith('.zarr.zip'):
                        continue

                    k1 = m_s1.name.replace('.zarr.zip', '').split('/')[-1]
                    k2 = m_s2.name.replace('.zarr.zip', '').split('/')[-1]
                    # 顺序一致性校验（不一致就跳过这一对，不阻塞）
                    if k1 != k2:
                        continue

                    s1_bytes = tf_s1.extractfile(m_s1).read()
                    s2_bytes = tf_s2.extractfile(m_s2).read()
                    yield k1, s1_bytes, s2_bytes
        except Exception as e:
            print(f"[Warning] 读取 tar 失败: {s1_tar_path}, {e}")
        except Exception as e:
            print(f"[Warning] 读取 tar 失败: {s1_tar_path}, {e}")

    def _process_pair(self, key: str, s1_bytes: bytes, s2_bytes: bytes) -> Optional[Dict]:
        """解析并处理一对样本"""
        s1_arr = self._parse_zarr_zip(s1_bytes)
        s2_arr = self._parse_zarr_zip(s2_bytes)

        if s1_arr is None or s2_arr is None:
            return None

        # 选择季节
        if self.random_season:
            season_idx = random.randint(0, 3)
        else:
            season_idx = 0  # 默认第一个季节

        s1_img = s1_arr[season_idx]  # [2, H, W]
        s2_img = s2_arr[season_idx]  # [12, H, W]

        # 归一化（复用原始方法，与 Stage 1.5 完全一致）
        if self.normalize:
            s1_img = normalize_image(s1_img, 'S1GRD')
            s2_img = normalize_image(s2_img, 'S2L2A')
        else:
            s1_img = s1_img.astype(np.float32)
            s2_img = s2_img.astype(np.float32)

        # 中心裁剪 264 -> 256（与原始 ssl4eo_dual.py 一致，start=4）
        if s2_img.shape[-1] == 264:
            s = 4
            s1_img = s1_img[:, s:s+256, s:s+256]
            s2_img = s2_img[:, s:s+256, s:s+256]

        return {
            'sample_key': key,
            's1_image': torch.from_numpy(s1_img),
            's2_image': torch.from_numpy(s2_img),
        }

    def __iter__(self):
        my_shards = self._get_my_shards()
        random.seed(self.seed + (torch.utils.data.get_worker_info().id if torch.utils.data.get_worker_info() else 0))

        epoch = 0
        while True:
            # 打乱 shard 顺序
            shuffled_shards = my_shards.copy()
            random.shuffle(shuffled_shards)

            for shard_idx in shuffled_shards:
                s1_tar = self.s1_tars[shard_idx]
                s2_tar = self.s2_tars[shard_idx]

                for key, s1_bytes, s2_bytes in self._read_tar_pairs(s1_tar, s2_tar):
                    sample = self._process_pair(key, s1_bytes, s2_bytes)
                    if sample is not None:
                        yield sample

            if not self.infinite:
                break
            epoch += 1


def collate_simple_dual(batch: List[Dict]) -> Dict[str, torch.Tensor]:
    """简单的 batch collate 函数"""
    return {
        's1_image': torch.stack([b['s1_image'] for b in batch]),
        's2_image': torch.stack([b['s2_image'] for b in batch]),
    }


def create_simple_dual_dataloader(
    data_root: str,
    split: str = 'train',
    batch_size: int = 64,
    num_workers: int = 8,
    random_season: bool = True,
    normalize: bool = True,
    infinite: bool = True,
    seed: int = 0,
    prefetch_factor: int = 4,
) -> DataLoader:
    """创建简化版双模态 DataLoader"""

    # 枚举 tar 文件
    s1_dir = Path(data_root) / split / 'S1GRD'
    s2_dir = Path(data_root) / split / 'S2L2A'

    s1_tars = sorted(s1_dir.glob('*.tar'))
    s2_tars = sorted(s2_dir.glob('*.tar'))

    assert len(s1_tars) > 0, f"未找到 S1 tar 文件: {s1_dir}"
    assert len(s2_tars) > 0, f"未找到 S2 tar 文件: {s2_dir}"

    dataset = SimpleSSL4EODualDataset(
        s1_tar_list=[str(p) for p in s1_tars],
        s2_tar_list=[str(p) for p in s2_tars],
        random_season=random_season,
        normalize=normalize,
        infinite=infinite,
        seed=seed,
    )

    # 注：实测 spawn 在本环境会卡（worker 重新 import 项目模块链过重），
    # 故用默认 fork。worker 数不宜过多（8 卡 × N workers，N>8 时 fork 大父进程易卡）。
    return DataLoader(
        dataset,
        batch_size=batch_size,
        num_workers=num_workers,
        collate_fn=collate_simple_dual,
        pin_memory=True,
        persistent_workers=(num_workers > 0),
        prefetch_factor=(prefetch_factor if num_workers > 0 else None),
    )
