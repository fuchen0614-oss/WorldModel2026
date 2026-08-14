#!/usr/bin/env python3
"""
探查 SSL4EO-S12-v1.1 数据集的结构。
"""

import argparse
import os
import tarfile
import tempfile
from pathlib import Path
import numpy as np
import zarr


def inspect_dataset(data_root):
    """探查 SSL4EO-S12-v1.1 数据集的结构。"""
    data_root = Path(data_root)

    print("=" * 80)
    print(f"SSL4EO-S12-v1.1 Dataset Inspection")
    print(f"Data root: {data_root}")
    print("=" * 80)
    print()

    # 检查各个数据划分（split）
    splits = ["train", "val"]
    modalities = ["S2L2A", "S2RGB", "S1GRD", "DEM", "LULC", "NDVI"]

    print("DATASET STRUCTURE:")
    print("-" * 80)

    split_info = {}
    for split in splits:
        split_path = data_root / split
        if not split_path.exists():
            print(f"  {split}: NOT FOUND")
            continue

        print(f"  {split}/")
        split_info[split] = {}

        for modality in modalities:
            modality_path = split_path / modality
            if modality_path.exists():
                # 统计 tar 文件数量
                tar_files = list(modality_path.glob("*.tar"))
                split_info[split][modality] = len(tar_files)
                print(f"    {modality}: {len(tar_files)} shards")
            else:
                split_info[split][modality] = 0
                print(f"    {modality}: NOT FOUND")

    print()
    print("MODALITY SUMMARY TABLE:")
    print("-" * 80)
    print(f"{'Modality':<12} {'Train Shards':<15} {'Val Shards':<15}")
    print("-" * 80)

    for modality in modalities:
        train_count = split_info.get("train", {}).get(modality, 0)
        val_count = split_info.get("val", {}).get(modality, 0)
        print(f"{modality:<12} {train_count:<15} {val_count:<15}")

    print("-" * 80)
    print()

    # 从 S2L2A 中解压并解析一个 tar 文件
    print("DETAILED S2L2A SAMPLE INSPECTION:")
    print("-" * 80)

    s2l2a_path = data_root / "train" / "S2L2A"
    if s2l2a_path.exists():
        tar_files = sorted(s2l2a_path.glob("*.tar"))
        if tar_files:
            sample_file = tar_files[0]
            print(f"Inspecting: {sample_file.name}")
            print()

            try:
                # 打开 tar 文件并查找其中的 zarr 内容
                with tarfile.open(sample_file, 'r') as tar:
                    members = tar.getmembers()
                    print(f"Tar contains {len(members)} files")
                    print()

                    # 查找 tar 中的第一个 zarr.zip 文件
                    zarr_member = None
                    for member in members:
                        if member.name.endswith('.zarr.zip'):
                            zarr_member = member
                            break

                    if zarr_member:
                        print(f"Found zarr file: {zarr_member.name}")
                        print()

                        # 解压到临时位置
                        with tempfile.TemporaryDirectory() as tmpdir:
                            tar.extract(zarr_member, tmpdir)
                            zarr_path = Path(tmpdir) / zarr_member.name

                            # 从 zip 中打开 zarr
                            from zarr.storage import ZipStore
                            store = ZipStore(zarr_path, mode='r')
                            root = zarr.open_group(store, mode='r')

                            print("Zarr structure:")
                            print(f"  Root keys: {list(root.keys())}")
                            print()

                            # 探查每个数组
                            for key in sorted(root.keys()):
                                arr = root[key]
                                print(f"  {key}:")
                                print(f"    Shape: {arr.shape}")
                                print(f"    Dtype: {arr.dtype}")
                                print(f"    Chunks: {arr.chunks}")

                                # 加载数据以检查 NaN/Inf
                                # 处理标量数组
                                if arr.shape == ():
                                    data = arr[()]
                                    print(f"    Value: {data}")
                                else:
                                    data = arr[:]

                                    if np.issubdtype(arr.dtype, np.floating):
                                        nan_count = np.isnan(data).sum()
                                        inf_count = np.isinf(data).sum()
                                        print(f"    NaN count: {nan_count}")
                                        print(f"    Inf count: {inf_count}")

                                        if data.size > 0:
                                            valid_data = data[~np.isnan(data) & ~np.isinf(data)]
                                            if valid_data.size > 0:
                                                print(f"    Min (valid): {valid_data.min():.6f}")
                                                print(f"    Max (valid): {valid_data.max():.6f}")
                                                print(f"    Mean (valid): {valid_data.mean():.6f}")
                                    elif data.dtype == np.object_ or data.dtype.kind in ['U', 'S']:
                                        print(f"    Sample values: {data.flat[:min(3, data.size)].tolist()}")
                                    elif np.issubdtype(arr.dtype, np.integer):
                                        print(f"    Min: {data.min()}")
                                        print(f"    Max: {data.max()}")

                                print()

                            store.close()
                    else:
                        print("No zarr.zip files found in tar archive")
                        print(f"Sample file names: {[m.name for m in members[:5]]}")

            except Exception as e:
                print(f"Error reading tar file: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("No tar files found in S2L2A/train")
    else:
        print("S2L2A train directory not found")

    print()
    print("=" * 80)
    print("Inspection complete")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Inspect SSL4EO-S12-v1.1 dataset structure"
    )
    parser.add_argument(
        "--data-root",
        type=str,
        default="/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1",
        help="Path to SSL4EO-S12-v1.1 dataset root directory"
    )

    args = parser.parse_args()
    inspect_dataset(args.data_root)


if __name__ == "__main__":
    main()
