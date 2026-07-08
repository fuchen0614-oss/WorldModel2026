#!/usr/bin/env python3
"""
最小测试脚本：直接测试 DataLoader 能否迭代出第一个 batch
用于定位 hang 的具体位置
"""
import os
import sys
import time
import yaml
import torch
import torch.distributed as dist

# 加入项目路径
sys.path.insert(0, '/csy-mix02/cog8/zjliu17/Agent/WorldModel2026')

from data.datasets.ssl4eo_dual import SSL4EODualConfig, create_ssl4eo_dual_dataset

def main():
    # 初始化分布式（单卡测试）
    os.environ['RANK'] = '0'
    os.environ['WORLD_SIZE'] = '1'
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '29602'

    dist.init_process_group(backend='nccl', init_method='env://')
    torch.cuda.set_device(0)

    print("=" * 60)
    print("DataLoader 最小测试")
    print("=" * 60)

    # 加载配置
    config_path = 'configs/train/stage1_vits_dual.yaml'
    with open(config_path) as f:
        config = yaml.safe_load(f)

    data_cfg = config['data']
    print(f"配置: batch={data_cfg['batch_size']}, workers={data_cfg['num_workers']}")

    # 创建 SSL4EODualConfig
    data_root = data_cfg['data_root']
    print(f"\n[1/5] 创建 SSL4EODualConfig...")
    t0 = time.time()
    dual_config = SSL4EODualConfig(
        base_path=data_root,
        shard_pattern=data_cfg.get('shard_pattern', '*.tar'),
        split=data_cfg.get('split', 'train'),
        random_season=data_cfg.get('random_season', True),
        normalize=data_cfg.get('normalize', True),
        cache_size=data_cfg.get('cache_size', 100),
    )
    print(f"  ✓ 耗时 {time.time()-t0:.1f}s")

    # 创建 DataLoader
    print(f"\n[2/5] 创建 DataLoader...")
    t0 = time.time()
    dataloader = create_ssl4eo_dual_dataset(
        dual_config,
        batch_size=data_cfg['batch_size'],
        num_workers=data_cfg['num_workers'],
        prefetch_factor=data_cfg.get('prefetch_factor', 4),
        shuffle=True,
        infinite=True,
        seed=42,
    )
    print(f"  ✓ 耗时 {time.time()-t0:.1f}s")

    # 创建 iterator
    print(f"\n[3/5] 创建 iterator (iter(dataloader))...")
    t0 = time.time()
    iterator = iter(dataloader)
    print(f"  ✓ 耗时 {time.time()-t0:.1f}s")

    # 获取第一个 batch
    print(f"\n[4/5] 获取第一个 batch (next(iterator))...")
    print("  这一步通常最慢（首次数据加载 + worker fork + tar 解压）")
    print("  预计 30-120 秒...")
    t0 = time.time()

    try:
        batch = next(iterator)
        elapsed = time.time() - t0
        print(f"  ✓ 成功！耗时 {elapsed:.1f}s")
        print(f"\n[5/5] Batch 信息:")
        for k, v in batch.items():
            if isinstance(v, torch.Tensor):
                print(f"  {k}: shape={v.shape}, dtype={v.dtype}")
            else:
                print(f"  {k}: {type(v)}")

        print("\n" + "=" * 60)
        print("✅ DataLoader 测试成功！")
        print("=" * 60)

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()

    dist.destroy_process_group()

if __name__ == '__main__':
    main()
