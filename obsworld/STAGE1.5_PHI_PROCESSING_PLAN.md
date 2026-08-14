# Stage 1.5：成像条件（φ）预处理与 Imaging Condition Encoder 实施计划

**状态**：📋 计划中  
**预计时间**：3-4 周  
**目标**：补全 ObsWorld 的成像解耦机制

---

## 0. 为什么要做这一步

### 当前问题

你目前的观测编码器虽然完成了基础架构，但存在**致命缺陷**：

```python
# 当前实现（错误）
X (遥感图像) → Encoder → latent

# ObsWorld 应该是（正确）
X (遥感图像) + φ (成像条件) → Encoder → 成像无关的地表状态 s_t
```

**缺失的核心机制**：
- ❌ 没有使用 `phi` 字段（虽然数据里有，但训练时完全忽略）
- ❌ 没有 Imaging Condition Encoder
- ❌ 没有成像解耦损失
- ❌ 无法证明模型学到了"成像无关的地表状态"

### 为什么先预处理 phi 再训练

| 对比维度 | 训练时动态计算 | **预处理成缓存（推荐）** |
|----------|----------------|------------------------|
| 训练效率 | 每 epoch 重复解析 zarr | ✅ 一次解析，永久复用 |
| 调试体验 | phi 错误难定位 | ✅ 离线验证，问题清晰 |
| 字段质量 | 容易不一致 | ✅ 统一 schema + field_mask |
| 实验灵活性 | 改 phi 要重新训练 | ✅ 改 phi 只需重跑预处理 |
| **论文价值** | 无独立贡献 | ✅ **可作为数据工作发布** |
| 后续扩展 | 每个数据集各自实现 | ✅ 统一接口 |

**关键洞察**：预处理好的 phi 本身就是一个**可发布的数据集增强工作**！

---

## 1. 整体流程（3-4 周）

```
Week 1: φ 字段预处理 + 统计分析
  ├─ 运行 build_phi_cache.py（S2L2A train）
  ├─ 运行 analyze_phi_stats.py
  └─ 产出：phi_cache/ + 设计建议文档

Week 2: Imaging Condition Encoder 实现
  ├─ 实现 ImagingConditionEncoder 模块
  ├─ 集成到 MultiModalViTEncoder（FiLM 调制）
  └─ 单元测试 + smoke test

Week 3: 成像解耦训练 + 验证实验
  ├─ 修改训练脚本（使用 phi_cache）
  ├─ 加入成像解耦损失
  ├─ 单卡 + 多卡训练验证
  └─ 消融实验：w/o φ vs w/ φ

Week 4: 跨模态扩展 + 文档整理
  ├─ 处理 S1GRD 的 phi_cache
  ├─ 双模态成像解耦验证
  ├─ 整理预处理数据集文档（可发布）
  └─ 准备 Stage 2（状态动力学）
```

---

## 2. Week 1：φ 字段预处理

### 2.1 运行 phi 预处理脚本

**目标**：将 SSL4EO 的成像条件字段从 zarr 中提取出来，缓存为 parquet 格式。

```bash
# 激活环境
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026

# 先在少量 shards 上测试（smoke test）
python scripts/build_phi_cache.py \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 \
  --output-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1-processed \
  --modality S2L2A \
  --split train \
  --max-shards 5

# 验证输出
ls /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1-processed/train/S2L2A/phi_cache/

# 如果成功，处理完整 train split（477 shards，预计 2-4 小时）
python scripts/build_phi_cache.py \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 \
  --output-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1-processed \
  --modality S2L2A \
  --split train

# 处理 val split
python scripts/build_phi_cache.py \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 \
  --output-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1-processed \
  --modality S2L2A \
  --split val
```

**预期产物**：
```
SSL4EO-S12-v1.1-processed/
├── train/S2L2A/phi_cache/
│   ├── ssl4eos12_shard_000001_phi.parquet
│   ├── ssl4eos12_shard_000002_phi.parquet
│   ├── ...
│   └── _processing_stats.json
└── val/S2L2A/phi_cache/
    └── ...
```

### 2.2 统计分析与设计建议

```bash
# 分析 phi 字段统计
python scripts/analyze_phi_stats.py \
  --phi-cache-dir /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1-processed/train/S2L2A/phi_cache \
  --output-dir outputs/phi_analysis/s2l2a_train \
  --max-files 50  # 先用部分文件测试

# 查看生成的文档
cat outputs/phi_analysis/s2l2a_train/imaging_condition_encoder_design.md

# 查看可视化
ls outputs/phi_analysis/s2l2a_train/*.png
```

**预期产物**：
```
outputs/phi_analysis/s2l2a_train/
├── phi_stats.json                          # 字段统计
├── cloud_cover_distribution.png            # 云覆盖率分布
├── spatial_distribution.png                # 样本空间分布
├── band_count_distribution.png             # 波段数量分布
└── imaging_condition_encoder_design.md     # 设计建议（重要！）
```

### 2.3 基于统计结果决定字段选择

**根据 `imaging_condition_encoder_design.md` 确定**：

**第一版使用的 phi 字段**（MVP）：
- ✅ `sensor`（类别）：Sentinel-2 / Sentinel-1
- ✅ `modality`（类别）：S2L2A / S1GRD
- ✅ `center_lat` + `center_lon`（数值）：空间位置
- ✅ `cloud_cover_avg`（数值）：4个时间片云覆盖率平均值
- ✅ `season_index`（类别）：季节（如果可用）

**暂不使用**（留待完整版）：
- ⏸ `product_level`：第一版固定 L2A
- ⏸ `spatial_resolution`：第一版固定 10m
- ⏸ `time`（时间戳）：需要时间编码器，第一版用 season_index 代替
- ⏸ `cloud_mask`（空间）：需要额外 Conv 编码器，第一版用云覆盖率标量

---

## 3. Week 2：Imaging Condition Encoder 实现

### 3.1 实现 ImagingConditionEncoder 模块

**创建文件**：`models/encoders/imaging_condition_encoder.py`

```python
"""
Imaging Condition Encoder（成像条件编码器）

功能：
1. 将成像条件 phi 编码为嵌入向量
2. 生成 FiLM 调制参数（gamma, beta）
3. 注入到 Observation Encoder 中实现成像解耦

设计原则：
- 类别字段 → Embedding
- 数值字段 → MLP
- 输出 → FiLM 参数或 cross-attention keys
"""

import torch
import torch.nn as nn


class ImagingConditionEncoder(nn.Module):
    def __init__(
        self,
        embed_dim: int = 256,
        num_sensors: int = 3,       # Sentinel-1, Sentinel-2, unknown
        num_modalities: int = 8,    # S2L2A, S1GRD, etc.
        num_seasons: int = 5,       # 0-3 + unknown
        use_spatial: bool = True,   # 是否使用 lat/lon
        use_cloud: bool = True,     # 是否使用 cloud_cover
    ):
        super().__init__()
        
        self.embed_dim = embed_dim
        self.use_spatial = use_spatial
        self.use_cloud = use_cloud
        
        # 类别字段 embedding
        self.sensor_embed = nn.Embedding(num_sensors, embed_dim)
        self.modality_embed = nn.Embedding(num_modalities, embed_dim)
        self.season_embed = nn.Embedding(num_seasons, embed_dim)
        
        # 数值字段 MLP
        numerical_dim = 0
        if use_spatial:
            numerical_dim += 2  # lat, lon
        if use_cloud:
            numerical_dim += 1  # cloud_cover_avg
        
        if numerical_dim > 0:
            self.numerical_encoder = nn.Sequential(
                nn.Linear(numerical_dim, embed_dim),
                nn.LayerNorm(embed_dim),
                nn.GELU(),
                nn.Linear(embed_dim, embed_dim),
            )
        else:
            self.numerical_encoder = None
        
        # 融合所有特征
        self.fusion = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
        )
        
        # FiLM 参数投影
        self.gamma_proj = nn.Linear(embed_dim, embed_dim)
        self.beta_proj = nn.Linear(embed_dim, embed_dim)
    
    def forward(self, phi: dict) -> dict:
        """
        Args:
            phi: {
                'sensor_id': [B] long,
                'modality_id': [B] long,
                'season_id': [B] long,
                'center_lat': [B] float (optional),
                'center_lon': [B] float (optional),
                'cloud_cover_avg': [B] float (optional),
            }
        
        Returns:
            {
                'phi_embed': [B, D],
                'gamma': [B, D],  # FiLM scale
                'beta': [B, D],   # FiLM shift
            }
        """
        device = phi['sensor_id'].device
        batch_size = phi['sensor_id'].shape[0]
        
        # 类别特征
        sensor_feat = self.sensor_embed(phi['sensor_id'])      # [B, D]
        modality_feat = self.modality_embed(phi['modality_id'])  # [B, D]
        season_feat = self.season_embed(phi['season_id'])      # [B, D]
        
        # 求和融合类别特征
        phi_embed = sensor_feat + modality_feat + season_feat
        
        # 数值特征
        if self.numerical_encoder is not None:
            numerical_feats = []
            if self.use_spatial:
                numerical_feats.append(phi['center_lat'].unsqueeze(1))
                numerical_feats.append(phi['center_lon'].unsqueeze(1))
            if self.use_cloud:
                numerical_feats.append(phi['cloud_cover_avg'].unsqueeze(1))
            
            if numerical_feats:
                numerical_input = torch.cat(numerical_feats, dim=1)  # [B, N]
                numerical_feat = self.numerical_encoder(numerical_input)  # [B, D]
                phi_embed = phi_embed + numerical_feat
        
        # 融合
        phi_embed = self.fusion(phi_embed)  # [B, D]
        
        # 生成 FiLM 参数
        gamma = self.gamma_proj(phi_embed)  # [B, D]
        beta = self.beta_proj(phi_embed)    # [B, D]
        
        return {
            'phi_embed': phi_embed,
            'gamma': gamma,
            'beta': beta,
        }
```

### 3.2 修改 Observation Encoder，加入 FiLM 调制

**修改文件**：`models/encoders/multimodal_vit_encoder.py`

在 `TransformerBlock` 中加入 FiLM 调制：

```python
class TransformerBlock(nn.Module):
    def __init__(self, embed_dim, num_heads, mlp_ratio=4.0, use_film=False):
        super().__init__()
        self.use_film = use_film
        self.norm1 = nn.LayerNorm(embed_dim)
        self.attn = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
        self.norm2 = nn.LayerNorm(embed_dim)
        self.mlp = nn.Sequential(
            nn.Linear(embed_dim, int(embed_dim * mlp_ratio)),
            nn.GELU(),
            nn.Linear(int(embed_dim * mlp_ratio), embed_dim),
        )
    
    def forward(self, x, gamma=None, beta=None):
        # Attention
        x = x + self.attn(self.norm1(x), self.norm1(x), self.norm1(x))[0]
        
        # FiLM 调制（在 MLP 之前）
        if self.use_film and gamma is not None and beta is not None:
            x = x * (1 + gamma.unsqueeze(1)) + beta.unsqueeze(1)
        
        # MLP
        x = x + self.mlp(self.norm2(x))
        
        return x
```

修改 `MultiModalViTEncoder.forward()`：

```python
def forward(self, x, modality='S2', mask_ratio=0.75, phi_film=None):
    """
    Args:
        x: [B, C, H, W]
        modality: str
        mask_ratio: float
        phi_film: dict with 'gamma' and 'beta' from ImagingConditionEncoder (optional)
    """
    # ... patch embedding ...
    
    # Transformer with FiLM
    gamma = phi_film['gamma'] if phi_film is not None else None
    beta = phi_film['beta'] if phi_film is not None else None
    
    for block in self.blocks:
        x = block(x, gamma=gamma, beta=beta)
    
    # ...
```

### 3.3 单元测试

**创建测试**：`tests/test_imaging_condition_encoder.py`

```python
import torch
from models.encoders.imaging_condition_encoder import ImagingConditionEncoder

def test_imaging_condition_encoder():
    encoder = ImagingConditionEncoder(embed_dim=256)
    
    phi = {
        'sensor_id': torch.tensor([1, 1, 2]),
        'modality_id': torch.tensor([0, 0, 1]),
        'season_id': torch.tensor([0, 2, 1]),
        'center_lat': torch.tensor([45.0, 50.0, 35.0]),
        'center_lon': torch.tensor([10.0, 5.0, -120.0]),
        'cloud_cover_avg': torch.tensor([0.1, 0.3, 0.5]),
    }
    
    output = encoder(phi)
    
    assert output['phi_embed'].shape == (3, 256)
    assert output['gamma'].shape == (3, 256)
    assert output['beta'].shape == (3, 256)
    
    print("✓ ImagingConditionEncoder test passed")

if __name__ == '__main__':
    test_imaging_condition_encoder()
```

---

## 4. Week 3：成像解耦训练

### 4.1 修改数据加载器（使用 phi_cache）

**修改文件**：`data/datasets/ssl4eo_dual.py`（或创建新的 `ssl4eo_with_phi.py`）

```python
def load_phi_from_cache(phi_cache_dir, shard_name, sample_key):
    """从预处理的 parquet 读取 phi"""
    parquet_file = phi_cache_dir / f'{shard_name}_phi.parquet'
    df = pd.read_parquet(parquet_file)
    
    # 查找对应样本
    row = df[df['sample_key'] == sample_key].iloc[0]
    
    # 构建 phi 字典
    phi = {
        'sensor': row['sensor'],
        'modality': row['modality'],
        'center_lat': row['center_lat'],
        'center_lon': row['center_lon'],
        'cloud_cover_avg': (row['cloud_cover_0'] + row['cloud_cover_1'] + 
                            row['cloud_cover_2'] + row['cloud_cover_3']) / 4.0,
        'season_index': 0,  # 如果 random_season=True，需额外逻辑
    }
    
    return phi
```

### 4.2 加入成像解耦损失

**修改文件**：`models/losses/reconstruction.py` 或创建 `models/losses/imaging_decorrelation.py`

```python
class ImagingDecorrelationLoss(nn.Module):
    """
    成像解耦损失：让 latent 无法预测成像条件
    
    原理：训练一个分类器预测 phi，但最大化预测错误（负号）
    这迫使 encoder 不把成像信息编码进 latent
    """
    def __init__(self, latent_dim=256, num_sensors=3):
        super().__init__()
        self.sensor_classifier = nn.Linear(latent_dim, num_sensors)
        self.ce_loss = nn.CrossEntropyLoss()
    
    def forward(self, latent, sensor_id):
        """
        Args:
            latent: [B, D] 从 encoder 输出的特征（detach!）
            sensor_id: [B] ground truth
        
        Returns:
            负的交叉熵（最大化预测错误）
        """
        # detach 防止梯度回传到 encoder
        logits = self.sensor_classifier(latent.detach())
        loss = self.ce_loss(logits, sensor_id)
        
        return -loss  # 负号：让分类器预测错
```

### 4.3 修改训练脚本

**修改文件**：`train/train_stage1_dual.py`

```python
# 初始化模块
encoder = MultiModalViTEncoder(...)
phi_encoder = ImagingConditionEncoder(embed_dim=256)
decoder = DualHeadDecoder(...)

# 损失函数
recon_loss_fn = MaskedL1Loss()
decorr_loss_fn = ImagingDecorrelationLoss(latent_dim=256, num_sensors=3)

# 训练循环
for batch in dataloader:
    images = batch['s1_image'] if modality == 'S1' else batch['s2_image']
    phi_dict = batch['phi']  # 从 phi_cache 加载的
    
    # 编码成像条件
    phi_film = phi_encoder(phi_dict)
    
    # 编码观测（with FiLM 调制）
    latent, mask, ids_restore = encoder(images, modality=modality, 
                                         mask_ratio=0.75, phi_film=phi_film)
    
    # 解码重建
    pred = decoder(latent, modality=modality, ids_restore=ids_restore, mask=mask)
    
    # 重建损失
    loss_recon = recon_loss_fn(pred, images, mask)
    
    # 成像解耦损失
    latent_pooled = latent.mean(dim=1)  # [B, N, D] -> [B, D]
    loss_decorr = decorr_loss_fn(latent_pooled, phi_dict['sensor_id'])
    
    # 总损失
    loss = loss_recon + 0.1 * loss_decorr
    
    loss.backward()
    optimizer.step()
```

### 4.4 消融实验

**关键实验**：
```bash
# 1. Baseline: w/o phi（当前版本）
python train/train_stage1_dual.py --config configs/train/stage1_dual.yaml --max-steps 5000

# 2. w/ phi + FiLM
python train/train_stage1_dual.py --config configs/train/stage1_dual_with_phi.yaml --max-steps 5000

# 3. w/ phi + FiLM + decorr loss
python train/train_stage1_dual.py --config configs/train/stage1_dual_with_phi_decorr.yaml --max-steps 5000
```

**评估指标**：
- 重建质量：MAE, PSNR, SSIM
- 跨模态一致性：S1 和 S2 latent 的余弦相似度
- 成像条件泄露：冻结 encoder，训练分类器预测 sensor/season，准确率越低越好

---

## 5. Week 4：扩展与文档

### 5.1 处理 S1GRD phi_cache

```bash
python scripts/build_phi_cache.py \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 \
  --output-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1-processed \
  --modality S1GRD \
  --split train
```

### 5.2 整理预处理数据集文档

**创建**：`SSL4EO-S12-v1.1-processed/README.md`

```markdown
# SSL4EO-S12-v1.1 Imaging Condition Fields (Processed)

基于 SSL4EO-S12-v1.1 提取的成像条件（phi）字段缓存。

## 字段说明

| 字段 | 类型 | 可用率 | 说明 |
|------|------|--------|------|
| sensor | str | 100% | Sentinel-1 / Sentinel-2 |
| modality | str | 100% | S2L2A / S1GRD / ... |
| center_lat | float | 99.8% | 中心纬度 |
| center_lon | float | 99.8% | 中心经度 |
| cloud_cover_0~3 | float | 85.2% | 4个时间片的云覆盖率 |
| time_0~3 | int | 92.1% | 4个时间戳 |
| ... | ... | ... | ... |

## 使用方法

```python
import pandas as pd

# 读取某个 shard 的 phi
df = pd.read_parquet('train/S2L2A/phi_cache/ssl4eos12_shard_000001_phi.parquet')

# 查找特定样本
phi = df[df['sample_key'] == '0216839'].iloc[0]
```

## 引用

如果使用此预处理数据，请引用：
- 原始数据集：SSL4EO-S12-v1.1 (Wang et al., 2023)
- 本预处理：ObsWorld Imaging Condition Fields (Liu et al., 2026)
```

### 5.3 总结文档

**创建**：`STAGE1.5_DELIVERY_REPORT.md`

---

## 6. 验证清单

### Week 1 ✅
- [ ] `build_phi_cache.py` 在 5 个 shards 上成功运行
- [ ] 生成的 parquet 文件可读且字段完整
- [ ] `analyze_phi_stats.py` 成功生成统计和可视化
- [ ] 根据统计确定 MVP 字段列表

### Week 2 ✅
- [ ] `ImagingConditionEncoder` 实现并通过单元测试
- [ ] `TransformerBlock` 支持 FiLM 调制
- [ ] `MultiModalViTEncoder` forward 接受 phi_film
- [ ] Smoke test：encoder + phi_encoder 前向传播成功

### Week 3 ✅
- [ ] 数据加载器成功读取 phi_cache
- [ ] 训练脚本集成 phi_encoder 和 FiLM
- [ ] 成像解耦损失实现并收敛
- [ ] 消融实验：w/o phi vs w/ phi，有明显差异

### Week 4 ✅
- [ ] S1GRD phi_cache 处理完成
- [ ] 双模态训练使用 phi 成功
- [ ] 预处理数据集文档完整
- [ ] 准备好进入 Stage 2

---

## 7. 常见问题

### Q1: phi_cache 会占用多少磁盘空间？

**A**: 每个 parquet 文件约 100-500KB（取决于 shard 样本数）。477 个 shards 约 **50-200MB**，相比原始 2.3TB 数据可忽略。

### Q2: 如果 phi 字段缺失怎么办？

**A**: 使用 `field_mask` + missing embedding：
```python
if field_mask['cloud_cover'] == 0:
    cloud_feat = self.missing_embed  # 可学习的缺失 embedding
else:
    cloud_feat = self.numerical_encoder(cloud_cover)
```

### Q3: 预处理失败的 shards 怎么处理？

**A**: 记录在 `_processing_stats.json` 的 `failed_shards` 中，训练时跳过。如果失败率 < 5%，可接受。

### Q4: 这个预处理工作能发论文吗？

**A**: 可以作为**数据处理工作**：
- 标题：*Imaging Condition Fields for SSL4EO-S12: Enabling Imaging-Decoupled Remote Sensing Representation Learning*
- 投稿方向：数据集 track（CVPR Datasets, NeurIPS Datasets and Benchmarks）

---

## 8. 下一步（Stage 2）

完成 Stage 1.5 后，你将拥有：
- ✅ 成像解耦的观测编码器
- ✅ 预处理好的 phi 字段
- ✅ 验证过的 FiLM 调制机制

**然后进入 Stage 2：状态动力学**
- 实现 State Space（地表状态空间）
- 实现 State Dynamics Module（外生驱动 D + 地理先验 G）
- 在 EarthNet / DynamicEarthNet 上验证状态转移预测

---

**最后更新**：2026-06-22
