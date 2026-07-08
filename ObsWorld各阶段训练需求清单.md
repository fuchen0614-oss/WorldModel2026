# ObsWorld 各阶段训练需求与推荐配置（权威汇总）

基于：`23_Step_Epoch换算与各阶段训练时长权威汇总.md`（v1.0 canonical）

---

## 核心换算基础（SSL4EO-S12）

**数据集规模：**
- 地点数：243,968
- 每地点季节数：4
- 全季展平：976k 样本

**当前配置：**
- Global batch：4096（8 卡 × 512/卡）
- 训练模式：Dual (S1/S2 轮流)
- random_season：True

**换算公式：**
```
Steps/epoch（三种口径）:
  A. 数据集遍历：59.6 steps（每次遍历 244k 地点）
  B. S2-only 全季：238.3 steps（遍历 976k 样本）
  C. Dual S2 视角：476.6 steps（S2 每 2 步训 1 次）

对标顶会用 C（Dual S2 视角全季覆盖 epoch）
```

---

## 阶段 0：数据巡检 ❌ 不训练

- **任务**：数据 audit，生成 manifest、field_mask
- **产物**：数据质量报告
- **时间**：1 次性脚本，几小时

---

## 阶段 1：观测编码器预训练（MAE）

### 训练需求

| 档位 | Total Steps | S2 全季 epoch (C) | vs SSL4EO baseline | 推荐度 |
|------|------------|------------------|-------------------|--------|
| 最低对齐 | 47,660 | 100 | 1.0× | 论文 baseline 门槛 |
| **推荐（当前已完成）** | **95,320** | **200** | **2.0×** | ⭐ **对齐 SatMAE 改进版** |
| 理想上限 | 143,000 | 300 | 3.0× | 收益递减，不推荐 |

### 结论

✅ **你当前 95k 已完成，完全达标**
- 对齐 SatMAE (NeurIPS 2022, 200 epoch)
- 是 SSL4EO baseline 的 2 倍
- DOFA (ICLR 2025) 说"beyond 80 epoch marginal gain"

❌ **不需要再加 step**
- 若想提升 EuroSAT，应扩模型（ViT-S/22M → ViT-B/86M）
- 而非加训练量

### 文献依据

- SSL4EO-S12 (IGARSS 2023): 100 epoch
- SatMAE (NeurIPS 2022): 200 epoch, "longer is better"
- DOFA (ICLR 2025): ">80 epoch marginal gain"

---

## 阶段 1.5：成像解耦续训（FiLM + 对比学习）

### 训练需求

| 档位 | Total Steps | S2 全季 epoch (C) | 说明 |
|------|------------|------------------|------|
| 最低 | 15,000 | 31 | 快速验证 FiLM 有效性 |
| **推荐** | **30,000** | **63** | ⭐ **续训标准量** |
| 理想 | 47,660 | 100 | 充分收敛 |

### 配置

```yaml
# configs/train/stage1_5_film.yaml
max_steps: 30000  # ≈ 63 S2 全季 epoch
```

### 为什么不需要 95k？

1. **续训标准**：GFM (CVPR 2023) 续训 100 ep + 蒸馏 vs 从头 800 ep
   - 续训量 = 基训的 30%–50%
   - 你的：30k = 95k × 31.5% ✅

2. **FiLM 模块小**：
   - phi_encoder + FiLM：仅 2.9M 参数
   - 零初始化，收敛快

3. **加权保护**：
   - `w_decouple=0.5` 避免破坏 MAE 特征

### 建议改进

**渐进 loss 权重**（optional）:
```python
# step 0–10k:  w_decouple = 0.1   # FiLM warm up
# step 10k–20k: w_decouple = 0.5   # 逐步增强
# step 20k–30k: w_decouple = 1.0   # 最终目标
```

---

## 阶段 2：状态动力学（关键阶段）

### ⚠️ 重要说明

**阶段 2 不用 SSL4EO 数据集！**
- 用 EarthNet2021 / DynamicEarthNet / Sen1Floods11
- 样本数完全不同
- **必须按各数据集单独算 epoch**

### 训练需求（按数据集）

| 数据集 | 样本数 | 建议 batch | Steps/epoch | 推荐 total epoch | 推荐 steps |
|--------|-------|-----------|------------|----------------|-----------|
| **EarthNet2021 mini** | ~32,000 | 128 | 250 | **50–80** | **12,500–20,000** |
| DynamicEarthNet | ~75 cube | 16 | 5 | 200–300 | 1,000–1,500 |
| Sen1Floods11 | ~4,831 | 64 | 75 | 100 | 7,500 |

### 训练策略

**三阶段**（引自 22 号文档）:

1. **Stage 2a**：单数据集跑通（冻结编码器）
   - 先在 EarthNet mini 跑通架构
   - 验证 dgh 注入、rollout、不确定性建模

2. **Stage 2b**：多数据集联合训练
   - field_mask + task_id 门控
   - 3 个数据集混合

3. **Stage 2c**：解冻编码器微调
   - lr = dynamics_lr / 10
   - 联合优化

### 配置

```yaml
# configs/train/stage2_dynamics.yaml
max_steps: 20000  # EarthNet mini, 约 80 epoch
# ⚠️ 占位值，等 loader 落地后按上表重算
```

### 关键

❗ **早停由验证集 rollout 指标决定，不按 step 硬停**
- 监控：multi-step prediction error
- 物理一致性验证

---

## 阶段 3：条件观测解码

### 训练需求

- **网络**：轻量 U-Net / MAE decoder
- **Epoch**：50–80（按 EarthNet 数据算）
- **策略**：与 Stage 2 **串行训练**（Stage 2 冻结后再训 decoder）

### 配置

```yaml
# configs/train/stage3_decoder.yaml
max_steps: 15000  # EarthNet, 约 60 epoch
# 第一版不上扩散模型（太重）
```

---

## 阶段 4：下游任务微调

### 训练需求（标准微调 schedule）

| 任务 | Epoch | Batch | 说明 |
|------|-------|-------|------|
| EuroSAT 分类 | 150 | 256 | Linear probing / Full fine-tune |
| Sen1Floods11 洪水分割 | 100 | 16 | 语义分割 |
| DynamicEarthNet LULC | 100 | 8 | 土地覆盖分类 |
| 线性探测（评估用） | 50–100 | 256 | 只训线性头 |

### 注意

- 这是**微调**，不是预训练
- Epoch 按各下游任务数据集大小算
- 不是 SSL4EO 的 epoch

---

## 阶段 5：基础模型对比

### 训练需求

- **方式**：Frozen encoder / LoRA / Full fine-tune
- **Epoch**：30–100（按任务定）
- **重点**：公平对比（同任务同评估协议）

### 对比基线

- Prithvi-EO (NASA)
- SatMAE
- ScaleMAE
- SSL4EO-S12 官方
- Random init (ablation)

---

## 总训练时间估算（完整 5 阶段）

| 阶段 | Steps | 单 step 时间 | 总时间 | GPU-hours (8×H200) |
|------|-------|------------|--------|-------------------|
| Stage 1 | 95,000 | 1.97s | **52h** | **416** |
| Stage 1.5 | 30,000 | ~2.0s | 17h | 136 |
| Stage 2a-c | 20,000 | ~3.0s | 17h | 136 |
| Stage 3 | 15,000 | ~2.5s | 10h | 80 |
| Stage 4-5 | varies | — | ~20h | 160 |
| **总计** | | | **~116h** | **~928** |

**注**：Stage 1 已完成，剩余约 64 小时（512 GPU-hours）

---

## 快速决策表

| 你的问题 | 答案 |
|---------|------|
| Stage 1 需要重跑吗？ | ❌ **不需要**，95k = 200 epoch 已完全达标 |
| Stage 1 需要再加 step 吗？ | ❌ **不需要**，已是 baseline 2 倍 |
| Stage 1.5 用多少 step？ | ✅ **30k steps**（63 epoch），续训标准量 |
| Stage 2 用多少 step？ | ✅ **20k steps**（EarthNet 80 epoch） |
| Stage 3 用多少 step？ | ✅ **15k steps**（60 epoch） |
| 是否需要"季节展平"重跑？ | ❌ **不需要**，random_season 已是合理策略 |

---

## 关键澄清

### ✅ 你当前的 95k = 200 全季覆盖 epoch

**不是**：
- ❌ 800 epoch（那是 random-season 口径，不对标顶会）
- ❌ 100 epoch（那是误算 batch=2048 的结果）

**是**：
- ✅ 200 全季覆盖 epoch（S2 视角，对标 SatMAE）
- ✅ SSL4EO baseline 的 2 倍
- ✅ 完全符合论文级训练量

### 为什么 4 个 random-season epoch = 1 个全季 epoch？

```
Random-season: 每个地点随机选 1 季
  → 遍历 4 次，期望每季被见 1 次

全季覆盖: 每个地点的 4 季都取
  → 遍历 1 次，确定每季被见 1 次

期望相同 → 等价（用于对标顶会）
```

---

生成时间：2026-06-28  
数据来源：`23_Step_Epoch换算与各阶段训练时长权威汇总.md` (canonical)