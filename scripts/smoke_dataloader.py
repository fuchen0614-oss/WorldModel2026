"""
SSL4EO DataModule 的冒烟测试（smoke test）。

本脚本从训练集（train split）加载一个 batch，并执行基础诊断：
- 打印 batch 的 keys、shapes、dtypes
- 打印 image tensor 的 min/max
- 可视化并将第一张图像保存为 PNG
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch

# 将上级目录加入 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.datamodules.ssl4eo_dm import SSL4EODataModule


def visualize_image(image: torch.Tensor, save_path: str):
    """将 image tensor 可视化并保存为 PNG。

    Args:
        image: 形状为 [C, H, W] 或 [T, C, H, W] 的 image tensor
        save_path: 可视化结果的保存路径
    """
    # 转为 numpy
    img = image.cpu().numpy()

    # 处理多时相（multi-temporal）情况
    if img.ndim == 4:
        # [T, C, H, W] —— 取第一个时相步（temporal step）
        print(f"Multi-temporal image detected: {img.shape}")
        img = img[0]  # [C, H, W]
        print(f"Using first temporal step: {img.shape}")

    # 归一化到 [0, 1] 以便可视化
    img_min = img.min()
    img_max = img.max()
    if img_max > img_min:
        img = (img - img_min) / (img_max - img_min)
    else:
        img = np.zeros_like(img)

    # 处理不同的通道配置
    if img.shape[0] >= 3:
        # 使用前 3 个通道作为 RGB
        rgb = img[:3].transpose(1, 2, 0)  # [H, W, 3]
    elif img.shape[0] == 1:
        # 单通道 —— 灰度图
        rgb = img[0]  # [H, W]
    else:
        # 2 通道 —— 使用第一个通道
        rgb = img[0]

    # 创建画布
    plt.figure(figsize=(8, 8))
    if rgb.ndim == 2:
        plt.imshow(rgb, cmap='gray')
    else:
        plt.imshow(rgb)
    plt.title(f'SSL4EO Image (shape: {image.shape})')
    plt.axis('off')
    plt.tight_layout()

    # 保存
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved visualization to: {save_path}")
    plt.close()


def main():
    print("=" * 80)
    print("SSL4EO DataModule Smoke Test")
    print("=" * 80)

    # 使用 S2L2A 模态初始化 DataModule
    print("\nInitializing DataModule with S2L2A modality...")
    dm = SSL4EODataModule(
        modality="S2L2A",
        batch_size=4,
        num_workers=2,
        random_season=False,  # 保留所有时相步以便可视化
        normalize=True,
        shard_pattern="ssl4eos12_shard_{000001..000477}.tar",  # Webdataset 花括号模式
    )

    # 初始化设置
    dm.setup('fit')
    print("DataModule setup complete.")

    # 获取训练 dataloader
    print("\nLoading train dataloader...")
    train_loader = dm.train_dataloader()

    # 加载一个 batch
    print("Fetching first batch...")
    batch = next(iter(train_loader))

    print("\n" + "=" * 80)
    print("BATCH DIAGNOSTICS")
    print("=" * 80)

    # 打印 batch 的 keys
    print("\nBatch keys:")
    for key in batch.keys():
        print(f"  - {key}")

    # 打印 shapes 和 dtypes
    print("\nBatch structure:")
    print(f"  image:")
    print(f"    Shape: {batch['image'].shape}")
    print(f"    Dtype: {batch['image'].dtype}")
    print(f"    Min: {batch['image'].min().item():.4f}")
    print(f"    Max: {batch['image'].max().item():.4f}")
    print(f"    Mean: {batch['image'].mean().item():.4f}")
    print(f"    Std: {batch['image'].std().item():.4f}")

    print(f"\n  phi (metadata):")
    for key, value in batch['phi'].items():
        if isinstance(value, torch.Tensor):
            print(f"    {key}: shape={value.shape}, dtype={value.dtype}")
        elif isinstance(value, list):
            print(f"    {key}: list of length {len(value)}, first={value[0]}")
        else:
            print(f"    {key}: {type(value).__name__}")

    print(f"\n  modality: {batch['modality'][:2]}... (showing first 2)")
    print(f"  sample_id: {batch['sample_id'][:2]}... (showing first 2)")
    print(f"  field_mask: {batch['field_mask'][0]}")

    # 第一张图像的每通道（per-channel）额外统计信息
    print("\n" + "-" * 80)
    print("Per-channel statistics for first image:")
    print("-" * 80)
    first_image = batch['image'][0]  # [T, C, H, W] 或 [C, H, W]

    if first_image.ndim == 4:
        # 多时相
        print(f"Shape: [T={first_image.shape[0]}, C={first_image.shape[1]}, "
              f"H={first_image.shape[2]}, W={first_image.shape[3]}]")
        # 在时相维度上取平均以计算每通道统计量
        img_channels = first_image.mean(dim=0)  # [C, H, W]
    else:
        print(f"Shape: [C={first_image.shape[0]}, H={first_image.shape[1]}, "
              f"W={first_image.shape[2]}]")
        img_channels = first_image

    num_channels = img_channels.shape[0]
    print(f"\nNumber of channels: {num_channels}")
    print(f"{'Channel':<10} {'Min':<12} {'Max':<12} {'Mean':<12} {'Std':<12}")
    print("-" * 58)
    for c in range(num_channels):
        channel_data = img_channels[c]
        print(f"{c:<10} "
              f"{channel_data.min().item():<12.6f} "
              f"{channel_data.max().item():<12.6f} "
              f"{channel_data.mean().item():<12.6f} "
              f"{channel_data.std().item():<12.6f}")

    # 可视化第一张图像
    print("\n" + "=" * 80)
    print("VISUALIZATION")
    print("=" * 80)

    output_dir = Path(__file__).parent.parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    save_path = output_dir / "ssl4eo_sample.png"

    visualize_image(batch['image'][0], str(save_path))

    print("\n" + "=" * 80)
    print("SMOKE TEST COMPLETE")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  Modality: S2L2A")
    print(f"  Batch size: {batch['image'].shape[0]}")
    print(f"  Image shape: {batch['image'].shape}")
    print(f"  Data type: {batch['image'].dtype}")
    print(f"  Value range: [{batch['image'].min().item():.4f}, {batch['image'].max().item():.4f}]")
    print(f"  Visualization saved: {save_path}")
    print()


if __name__ == "__main__":
    main()
