"""
用于 SSL4EO-S12 数据集的 Lightning DataModule。

本模块将 SSL4EO 的 WebDataset 实现封装为 Lightning 风格的
DataModule，便于与训练流程集成。
"""

from typing import Optional

from torch.utils.data import DataLoader

from data.datasets.ssl4eo import SSL4EOConfig, collate_fn, create_ssl4eo_dataset


class SSL4EODataModule:
    """用于 SSL4EO-S12 数据集的 PyTorch Lightning DataModule。

    本 DataModule 负责为 SSL4EO-S12 数据集创建训练和验证 dataloader，
    并支持可配置的参数。

    Args:
        modality: 传感器/模态类型（如 'S2L2A'、'S2RGB'、'S1GRD'）。
        batch_size: 每个 batch 的样本数量。
        num_workers: 用于数据加载的工作进程数量。
        random_season: 若为 True，则随机选择一个季节；否则返回全部 4 个季节。
        base_path: 包含 SSL4EO-S12 数据的根目录。
        normalize: 若为 True，则将图像归一化到 [0, 1] 范围。
        cache_size: 用于预取的 WebDataset 缓存大小。
        shard_pattern: 用于匹配 tar shard 的模式。

    Example:
        >>> dm = SSL4EODataModule(
        ...     modality='S2L2A',
        ...     batch_size=32,
        ...     num_workers=4,
        ...     random_season=True
        ... )
        >>> dm.setup('fit')
        >>> train_loader = dm.train_dataloader()
        >>> val_loader = dm.val_dataloader()
    """

    def __init__(
        self,
        modality: str = "S2L2A",
        batch_size: int = 32,
        num_workers: int = 4,
        random_season: bool = False,
        base_path: str = "/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1",
        normalize: bool = False,
        cache_size: int = 100,
        shard_pattern: str = "*.tar",
    ):
        super().__init__()
        self.modality = modality
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.random_season = random_season
        self.base_path = base_path
        self.normalize = normalize
        self.cache_size = cache_size
        self.shard_pattern = shard_pattern

        # 存储配置以便延迟初始化
        self.train_config = None
        self.val_config = None

    def setup(self, stage: Optional[str] = None):
        """设置训练和验证配置。

        Args:
            stage: 当前阶段（'fit'、'validate'、'test' 或 'predict'）。
        """
        if stage == 'fit' or stage is None:
            # 创建训练配置
            self.train_config = SSL4EOConfig(
                modality=self.modality,
                split='train',
                random_season=self.random_season,
                base_path=self.base_path,
                shard_pattern=self.shard_pattern,
                normalize=self.normalize,
                cache_size=self.cache_size,
            )

            # 创建验证配置
            self.val_config = SSL4EOConfig(
                modality=self.modality,
                split='val',
                random_season=self.random_season,
                base_path=self.base_path,
                shard_pattern=self.shard_pattern,
                normalize=self.normalize,
                cache_size=self.cache_size,
            )

    def train_dataloader(self) -> DataLoader:
        """创建训练 dataloader。

        Returns:
            启用了 shuffle 的训练集 DataLoader。
        """
        if self.train_config is None:
            self.setup('fit')

        dataset = create_ssl4eo_dataset(
            config=self.train_config,
            batch_size=None,  # batch 划分由 DataLoader 处理
            num_workers=self.num_workers,
            shuffle=True,
        )

        return DataLoader(
            dataset,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            collate_fn=collate_fn,
            pin_memory=True,
        )

    def val_dataloader(self) -> DataLoader:
        """创建验证 dataloader。

        Returns:
            不启用 shuffle 的验证集 DataLoader。
        """
        if self.val_config is None:
            self.setup('fit')

        dataset = create_ssl4eo_dataset(
            config=self.val_config,
            batch_size=None,  # batch 划分由 DataLoader 处理
            num_workers=self.num_workers,
            shuffle=False,
        )

        return DataLoader(
            dataset,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            collate_fn=collate_fn,
            pin_memory=True,
        )


if __name__ == "__main__":
    # 简单测试
    dm = SSL4EODataModule(
        modality="S2L2A",
        batch_size=4,
        num_workers=2,
        random_season=True,
        normalize=True,
    )

    dm.setup('fit')

    print("测试训练 dataloader...")
    train_loader = dm.train_dataloader()
    for batch in train_loader:
        print(f"Train batch image shape: {batch['image'].shape}")
        break

    print("\n测试验证 dataloader...")
    val_loader = dm.val_dataloader()
    for batch in val_loader:
        print(f"Val batch image shape: {batch['image'].shape}")
        break

    print("\nDataModule 测试完成！")
