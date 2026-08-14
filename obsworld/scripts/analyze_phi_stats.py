#!/usr/bin/env python3
"""
分析预处理好的 phi 缓存，生成统计报告

功能：
1. 加载所有 phi parquet 文件
2. 统计字段完整性（field_mask 分析）
3. 生成成像条件分布可视化
4. 为 Imaging Condition Encoder 设计提供数据依据
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from tqdm import tqdm


def load_all_phi(phi_cache_dir: Path, max_files: int = None) -> pd.DataFrame:
    """加载所有 phi parquet 文件并合并"""
    parquet_files = sorted(phi_cache_dir.glob('*_phi.parquet'))

    if max_files:
        parquet_files = parquet_files[:max_files]

    dfs = []
    for pf in tqdm(parquet_files, desc='Loading phi files'):
        try:
            df = pd.read_parquet(pf)
            dfs.append(df)
        except Exception as e:
            print(f"Warning: Failed to load {pf.name}: {e}")

    if not dfs:
        raise ValueError("No phi files loaded")

    return pd.concat(dfs, ignore_index=True)


def analyze_field_mask(df: pd.DataFrame) -> Dict:
    """分析 field_mask，统计字段可用性"""
    if '_field_mask' not in df.columns:
        return {'error': 'No _field_mask column found'}

    # 解析 field_mask
    field_masks = df['_field_mask'].apply(json.loads)

    # 统计每个字段的可用率
    field_stats = {}
    all_keys = set()
    for fm in field_masks:
        all_keys.update(fm.keys())

    for key in sorted(all_keys):
        available = [fm.get(key, 0) for fm in field_masks]
        field_stats[key] = {
            'available_count': sum(available),
            'total_count': len(available),
            'availability_rate': sum(available) / len(available),
        }

    return field_stats


def analyze_phi_distribution(df: pd.DataFrame, output_dir: Path):
    """分析 phi 字段分布"""

    # 1. 云覆盖率分布（4个时间片）
    cloud_cols = ['cloud_cover_0', 'cloud_cover_1', 'cloud_cover_2', 'cloud_cover_3']
    if all(col in df.columns for col in cloud_cols):
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        for i, col in enumerate(cloud_cols):
            ax = axes[i // 2, i % 2]
            data = df[col].dropna()
            ax.hist(data, bins=50, alpha=0.7, edgecolor='black')
            ax.set_title(f'{col} Distribution (N={len(data)})')
            ax.set_xlabel('Cloud Cover Ratio')
            ax.set_ylabel('Count')
            ax.axvline(data.mean(), color='red', linestyle='--', label=f'Mean={data.mean():.3f}')
            ax.legend()

        plt.tight_layout()
        plt.savefig(output_dir / 'cloud_cover_distribution.png', dpi=150)
        plt.close()
        print(f"✓ 生成云覆盖率分布图")

    # 2. 空间分布（经纬度）
    if 'center_lat' in df.columns and 'center_lon' in df.columns:
        fig, ax = plt.subplots(figsize=(12, 8))

        lat = df['center_lat'].dropna()
        lon = df['center_lon'].dropna()

        # 2D 直方图
        h = ax.hist2d(lon, lat, bins=100, cmap='YlOrRd')
        plt.colorbar(h[3], ax=ax, label='Sample Count')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_title(f'Spatial Distribution (N={len(lat)})')

        plt.tight_layout()
        plt.savefig(output_dir / 'spatial_distribution.png', dpi=150)
        plt.close()
        print(f"✓ 生成空间分布图")

    # 3. 波段数量分布
    if 'num_bands' in df.columns:
        fig, ax = plt.subplots(figsize=(8, 6))
        band_counts = df['num_bands'].value_counts().sort_index()
        ax.bar(band_counts.index, band_counts.values, edgecolor='black')
        ax.set_xlabel('Number of Bands')
        ax.set_ylabel('Count')
        ax.set_title('Band Count Distribution')

        for i, v in zip(band_counts.index, band_counts.values):
            ax.text(i, v, str(v), ha='center', va='bottom')

        plt.tight_layout()
        plt.savefig(output_dir / 'band_count_distribution.png', dpi=150)
        plt.close()
        print(f"✓ 生成波段数量分布图")


def generate_encoder_design_doc(field_stats: Dict, df: pd.DataFrame, output_dir: Path):
    """
    根据 phi 统计生成 Imaging Condition Encoder 设计建议
    """
    doc = []
    doc.append("# Imaging Condition Encoder 设计建议")
    doc.append(f"\n基于 {len(df)} 个样本的统计分析\n")

    doc.append("## 1. 字段可用性分析\n")
    doc.append("| 字段 | 可用率 | 可用样本数 | 建议处理方式 |")
    doc.append("|------|--------|-----------|------------|")

    for field, stats in sorted(field_stats.items(), key=lambda x: -x[1]['availability_rate']):
        rate = stats['availability_rate']
        count = stats['available_count']

        if rate >= 0.95:
            recommendation = "✅ 直接使用"
        elif rate >= 0.7:
            recommendation = "⚠️ 使用 + Missing Embedding"
        elif rate >= 0.3:
            recommendation = "❌ 可选特征（field_mask=0时跳过）"
        else:
            recommendation = "❌ 不建议使用"

        doc.append(f"| {field} | {rate:.1%} | {count} | {recommendation} |")

    doc.append("\n## 2. Imaging Condition Encoder 架构建议\n")

    # 类别字段
    categorical_fields = []
    if field_stats.get('sensor', {}).get('availability_rate', 0) > 0.9:
        categorical_fields.append('sensor')
    if field_stats.get('modality', {}).get('availability_rate', 0) > 0.9:
        categorical_fields.append('modality')
    if field_stats.get('product_level', {}).get('availability_rate', 0) > 0.9:
        categorical_fields.append('product_level')

    doc.append("### 2.1 类别字段（Categorical）")
    doc.append("```python")
    doc.append("# 建议使用 Embedding Layer")
    for field in categorical_fields:
        doc.append(f"self.{field}_embed = nn.Embedding(num_{field}, embed_dim)")
    doc.append("```\n")

    # 数值字段
    numerical_fields = []
    if 'center_lat' in df.columns and df['center_lat'].notna().mean() > 0.9:
        numerical_fields.extend(['center_lat', 'center_lon'])
    if 'cloud_cover_0' in df.columns and df['cloud_cover_0'].notna().mean() > 0.7:
        numerical_fields.extend(['cloud_cover_0', 'cloud_cover_1', 'cloud_cover_2', 'cloud_cover_3'])

    doc.append("### 2.2 数值字段（Numerical）")
    doc.append("```python")
    doc.append("# 建议使用 MLP 编码")
    doc.append("self.numerical_encoder = nn.Sequential(")
    doc.append(f"    nn.Linear({len(numerical_fields)}, hidden_dim),")
    doc.append("    nn.LayerNorm(hidden_dim),")
    doc.append("    nn.GELU(),")
    doc.append("    nn.Linear(hidden_dim, embed_dim),")
    doc.append(")")
    doc.append("```\n")

    # 空间字段
    doc.append("### 2.3 空间字段（Spatial）")
    doc.append("```python")
    doc.append("# cloud_mask 建议处理方式：")
    doc.append("# 1. 与 image 一起输入到 Observation Encoder")
    doc.append("# 2. 或通过轻量 Conv 提取全局特征")
    doc.append("self.cloud_encoder = nn.Sequential(")
    doc.append("    nn.Conv2d(1, 16, kernel_size=8, stride=8),  # 256->32")
    doc.append("    nn.GELU(),")
    doc.append("    nn.AdaptiveAvgPool2d(1),  # Global pooling")
    doc.append("    nn.Flatten(),")
    doc.append("    nn.Linear(16, embed_dim),")
    doc.append(")")
    doc.append("```\n")

    doc.append("## 3. FiLM 调制建议\n")
    doc.append("```python")
    doc.append("# 将所有 phi 特征融合后生成 FiLM 参数")
    doc.append("phi_embed = cat([sensor_embed, numerical_embed, cloud_embed])  # [B, D]")
    doc.append("gamma = self.gamma_proj(phi_embed)  # [B, D] -> [B, D]")
    doc.append("beta = self.beta_proj(phi_embed)   # [B, D] -> [B, D]")
    doc.append("")
    doc.append("# 在 Transformer 层中调制特征")
    doc.append("x = x * (1 + gamma.unsqueeze(1)) + beta.unsqueeze(1)")
    doc.append("```\n")

    doc.append("## 4. 推荐的第一版实现\n")
    doc.append("**最小可行版本（MVP）**：")
    doc.append("- 类别字段：sensor + modality")
    doc.append("- 数值字段：center_lat + center_lon")
    doc.append("- 空间字段：cloud_cover（标量，4个时间片平均）")
    doc.append("- 调制方式：FiLM（简单有效）\n")

    doc.append("**完整版（后续扩展）**：")
    doc.append("- 增加：product_level, spatial_resolution")
    doc.append("- 增加：time（时间戳编码）")
    doc.append("- 增加：cloud_mask（空间特征）")
    doc.append("- 调制方式：FiLM + Cross-Attention\n")

    # 保存文档
    doc_file = output_dir / 'imaging_condition_encoder_design.md'
    with open(doc_file, 'w') as f:
        f.write('\n'.join(doc))

    print(f"✓ 生成设计建议文档: {doc_file}")


def main():
    parser = argparse.ArgumentParser(description='分析 phi 缓存统计')
    parser.add_argument('--phi-cache-dir', type=str, required=True,
                        help='phi_cache 目录路径')
    parser.add_argument('--output-dir', type=str, required=True,
                        help='输出目录')
    parser.add_argument('--max-files', type=int, default=None,
                        help='最多加载多少个文件（用于快速测试）')

    args = parser.parse_args()

    phi_cache_dir = Path(args.phi_cache_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*60)
    print("加载 phi 缓存...")
    print("="*60)

    df = load_all_phi(phi_cache_dir, args.max_files)

    print(f"\n✓ 加载完成: {len(df)} 个样本")
    print(f"  字段数: {len(df.columns)}")
    print(f"  内存占用: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB\n")

    # 分析 field_mask
    print("="*60)
    print("分析字段可用性...")
    print("="*60)

    field_stats = analyze_field_mask(df)

    print("\n字段可用性统计：")
    for field, stats in sorted(field_stats.items(), key=lambda x: -x[1]['availability_rate']):
        print(f"  {field:20s}: {stats['availability_rate']:6.1%}  ({stats['available_count']:,} / {stats['total_count']:,})")

    # 保存统计 JSON
    stats_json = {
        'total_samples': len(df),
        'field_availability': field_stats,
    }

    # 数值字段统计
    numerical_stats = {}
    for col in df.columns:
        if col == '_field_mask':
            continue
        if df[col].dtype in ['float64', 'float32', 'int64', 'int32']:
            try:
                numerical_stats[col] = {
                    'count': int(df[col].notna().sum()),
                    'mean': float(df[col].mean()),
                    'std': float(df[col].std()),
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                }
            except Exception:
                pass

    stats_json['numerical_stats'] = numerical_stats

    stats_file = output_dir / 'phi_stats.json'
    with open(stats_file, 'w') as f:
        json.dump(stats_json, f, indent=2)

    print(f"\n✓ 保存统计信息: {stats_file}")

    # 生成可视化
    print("\n" + "="*60)
    print("生成可视化...")
    print("="*60 + "\n")

    analyze_phi_distribution(df, output_dir)

    # 生成设计建议
    print("\n" + "="*60)
    print("生成 Imaging Condition Encoder 设计建议...")
    print("="*60 + "\n")

    generate_encoder_design_doc(field_stats, df, output_dir)

    print("\n" + "="*60)
    print("分析完成！")
    print("="*60)


if __name__ == '__main__':
    main()
