#!/usr/bin/env python
"""测试双模态数据加载器能否正常工作。"""

import sys
sys.path.insert(0, '/csy-mix02/cog8/zjliu17/Agent/WorldModel2026')

from data.datasets.ssl4eo_dual import SSL4EODualConfig, create_ssl4eo_dual_dataset

print("创建双模态配置...")
config = SSL4EODualConfig(
    split="train",
    random_season=True,
    normalize=True,
    shard_pattern="ssl4eos12_shard_{000001..000002}.tar",  # 只用前2个shard
)

print(f"S1 shard path: {config.s1_shard_path}")
print(f"S2 shard path: {config.s2_shard_path}")

print("\n创建数据集...")
dataset = create_ssl4eo_dual_dataset(
    config,
    batch_size=2,
    num_workers=0,
    shuffle=False,
)

print("\n开始迭代...")
for i, batch in enumerate(dataset):
    print(f"Batch {i}:")
    print(f"  S1 shape: {batch['s1_image'].shape}")
    print(f"  S2 shape: {batch['s2_image'].shape}")
    print(f"  Sample IDs: {batch['sample_id'][:2]}")

    if i >= 2:  # 只测试前3个batch
        break

print("\n数据加载测试成功！")
