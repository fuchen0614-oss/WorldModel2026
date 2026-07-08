---
title: "23 Step/Epoch 换算与各阶段训练时长权威汇总"
version: v1.0（canonical）
created: 2026-07-01
author: Zhijian Liu & Claude Opus 4.8
project: ObsWorld
status: ⭐ 本文是所有 step/epoch 相关表述的权威来源，若与其他文档冲突以本文为准
supersedes:
  - 16_各阶段训练步数与epoch调研报告.md（§1.2 换算表使用错误 global batch）
  - 15_Stage1与Stage1.5完整训练指南.md（§3.4 训练配置里 batch_size 语义未标清）
consolidates:
  - 18_Step与Epoch对应关系详细推导.md
  - 19_Step与Epoch混淆点澄清_基于代码验证.md
  - 20_训练设置选择_论文发表视角分析.md
tags: [step, epoch, batch-size, random-season, dual-mode, canonical]
---

# 23 Step/Epoch 换算与各阶段训练时长权威汇总

> [!important] 一句话结论
> **Global batch = 4096（8 卡 × 512/卡）**，**Stage 1 已完成 95k steps ≈ 200 全季覆盖 epoch（S2 视角）= SSL4EO 基线的 2 倍**。所有阶段的 step 数换算都基于本文 §1 的权威公式。

---

## 0. 文档定位

### 为什么要有这份文档

早期 15、16 号文档在换算 step ↔ epoch 时使用了错误的 global batch（把 `batch_size: 64` 误读为 global batch，实际是 per-GPU），导致：

- 16 号建议"Stage 1 应跑 380k–760k step"（基于 global batch 256 算的）
- 而实际 global batch 是 4096，正确的 100-epoch 只需要 ~24k step

18、19、20 号文档陆续修正了这个错误，但结论散落在三份文档里，配置文件的注释也不统一。**本文一次性收敛所有换算，作为后续训练与论文写作的唯一参考。**

### 与其他文档的关系

| 文档 | 与本文关系 |
|------|-----------|
| [[10ObsWorld 完整实验流程与字段设计]] | 阶段划分总纲，本文补 step 数 |
| [[15_Stage1与Stage1.5完整训练指南]] | 早期指南，§3.4 tiny 版配置已过期 → step 数以本文为准 |
| [[17_周报_2026W26]] | 历史记录（已冻结） |
| ~~16 各阶段训练步数与 epoch 调研报告~~ | 已删除，22 篇顶会调研合并至本文 §9 附录 A |
| ~~18 Step 与 Epoch 对应关系详细推导~~ | 已删除，三种 epoch 定义合并至本文 §2、§3 |
| ~~19 Step 与 Epoch 混淆点澄清（基于代码验证）~~ | 已删除，代码语义验证合并至本文 §5 |
| ~~20 训练设置选择：论文发表视角分析~~ | 已删除，论文对标视角合并至本文 §4.2、§7 |
| [[22_dgh数据构建完整方案]] | Stage 2 数据准备，本文 §4.4 引用其 dgh_v1_minimal |

---

## 1. 权威数字锚点（一切换算的基础）

### 1.1 数据集参数（`metadata.parquet` 精确计数）

```yaml
数据集: SSL4EO-S12-v1.1（train split）
地点数 N_loc:      243,968          # metadata parquet 行数
每地点季节数:      4                # zarr 内 bands 第 0 维
S1/S2 tar 文件数:  477 / 477        # 相同（配对采样）
```

### 1.2 训练配置（`configs/train/stage1_vits_dual_staged.yaml` 实测）

```yaml
GPU 数:            8
Per-GPU batch:     512              # yaml 里的 batch_size 字段
Global batch B:    4096             # = 8 × 512
random_season:     true
training_mode:     dual (S1/S2 轮流)
```

### 1.3 核心公式（所有换算都从这里出发）

```text
【公式 1】1 sample-epoch (random_season) = N_loc / B
        = 243,968 / 4,096
        = 59.6 steps

【公式 2】1 full-coverage epoch = 4 × sample-epoch (random_season)
        = 238.3 steps

【公式 3】Dual 模式下，S2 训练次数 = total_steps / 2
        （每 step 只训一个模态，S2 训练频率减半）

【公式 4】S2 视角全季覆盖 epoch = (total_steps / 2) / 238.3
        = total_steps / 476.6
```

---

## 2. 三种 epoch 定义 —— 何时用哪个

| 定义 | Steps/epoch (B=4096) | 何时用 |
|------|---------------------|--------|
| **A. 数据集遍历 epoch**（dataloader 视角，含 random_season） | **59.6** | 训练日志、监控进度 |
| **B. Sample-epoch 全季覆盖**（单模态视角，与 SSL4EO 论文一致） | **238.3** | 单模态训练（S2-only）与顶会对标 |
| **C. Sample-epoch 全季覆盖 · Dual S2 视角** ⭐ | **476.6** | Dual 模式与顶会对标的**正式口径** |

> [!important] 对标顶会用哪个？
> **Dual 模式训练时，用定义 C（S2 视角全季覆盖）** 与 SSL4EO-S12 论文 baseline（100 epoch，单模态全季）对标。这是 18/19/20 号文档协商一致的结论。

---

## 3. 关键换算表（复制即用）

### 3.1 Steps → Epoch（Dual 模式，S2 视角，全季覆盖口径）

| Steps | 数据集遍历 epoch (A) | Sample-ep 全季 S2-only (B) | **S2 视角全季 (C) ⭐** | vs SSL4EO 基线 (100 ep) |
|-------|--------------------|---------------------------|----------------------|-----------------------|
| 5,000 | 84 | 21 | **10.5** | 0.1× |
| 10,000 | 168 | 42 | **21** | 0.2× |
| 23,830 | 400 | 100 | **50** | 0.5× |
| **47,660** | **800** | **200** | **100** | **1.0×（对齐基线）** |
| 71,490 | 1200 | 300 | **150** | 1.5× |
| **95,320** | **1600** | **400** | **200** | **2.0×（当前 Stage 1 训练量）** ⭐ |
| 142,980 | 2400 | 600 | **300** | 3.0× |

### 3.2 Epoch → Steps（反查表）

| 目标 S2 视角全季 epoch (C) | 对应 total steps | 说明 |
|--------------------------|-----------------|------|
| 50 | 23,830 | 0.5× baseline，quick check |
| **100** | **47,660** | **对齐 SSL4EO baseline** |
| 150 | 71,490 | 1.5× baseline，续训中间点 |
| **200** | **95,320** | **对齐 SatMAE 改进版 / 当前训练量** ⭐ |
| 300 | 142,980 | 长训练，收益递减区 |

### 3.3 其他 batch 配置的换算（防止未来改 batch 时出错）

同样的 total_steps 下，改变 global batch 会改变 epoch 数。**batch 翻倍 → 同 step 数下 epoch 减半**。

| Global batch | Steps/epoch (定义 C) | 100 epoch 需要多少 step |
|-------------|---------------------|----------------------|
| 1024（8×128） | 1,906 | 190,600 |
| 2048（8×256） | 953 | 95,300 |
| **4096（8×512）当前** | **476.6** | **47,660** |
| 8192（8×1024） | 238.3 | 23,830 |

> [!tip] 公式速记
> Steps/epoch(C) = N_loc × 4 × 2 / B = 1,951,744 / B

---

## 4. 各阶段 step/epoch 权威推荐

### 4.1 阶段 0：数据巡检

- **不训练**，只跑一次数据 audit 脚本
- 产物：manifest、field_mask 规则、smoke test
- 参考：11、13 号文档

### 4.2 阶段 1：SSL4EO 观测编码器预训练（MAE）

| 档位 | Total Steps | S2 视角全季 epoch (C) | vs SSL4EO baseline | 状态 |
|------|------------|---------------------|-------------------|------|
| 最低对齐 | 47,660 | 100 | 1.0× | 论文 baseline 门槛 |
| **推荐（当前）** | **95,320** | **200** | **2.0×** | ⭐ **对齐 SatMAE 改进版，已完成** |
| 理想上限 | 143,000 | 300 | 3.0× | DOFA "beyond 80 ep marginal"，不推荐再加 |

**结论**：当前 95k 已经完全达到论文级训练量，**不需要再加 step**。若想进一步提升 EuroSAT，应扩模型容量（如从 ViT-S/22M 到 ViT-B/86M）而不是加 step。

**文献依据**（详见 16 号文档 §2）：
- SSL4EO-S12（IGARSS 2023）：100 epoch 全季覆盖
- SatMAE（NeurIPS 2022）：200 epoch，明确说 "longer is better"
- DOFA（ICLR 2025）：">80 epoch marginal gain"
- MAE（CVPR 2022）：ImageNet 800-1600 epoch，但 ImageNet 数据量是 SSL4EO 的 5×，不可直接类比

### 4.3 阶段 1.5：成像解耦续训（FiLM + 对比学习）

> [!warning] ⚠️ 更正说明（2026-07-03）
> 本节 v1.0 版本错误地套用了 Stage 1 的换算关系（476.6 steps/epoch），导致 epoch 数高估 2 倍。Stage 1.5 的配置与 Stage 1 完全不同：
> - Batch 小 4 倍（1024 vs 4096）
> - 无 dual 轮流的 /2 因子（每步同时训 S1+S2）
> - 正确换算：**953 steps/epoch**（详见 §4.3.1）
> 
> 已同步至 [[Stage1.5_完整训练执行方案_FINAL]] §20。

#### 4.3.1 正确的换算关系（⭐ 重要）

**Stage 1.5 的配置与 Stage 1 不同，不能直接套用 §1.3 的公式！**

```yaml
# Stage 1.5 配置（configs/train/stage1_5_dual_conditioned_vits.yaml）
GPU 数:            8
Per-GPU batch:     64              # vs Stage 1 的 512
Gradient accum:    2               # vs Stage 1 的 1
Effective batch:   1,024           # = 8 × 64 × 2  (vs Stage 1 的 4096)
训练模式:          每步同时训 S1+S2  # vs Stage 1 的 dual 轮流
```

**换算公式**：
```text
【Stage 1.5 公式】1 全季覆盖 epoch = N_loc × 4季 / B_eff
                = 243,968 × 4 / 1,024
                = 953 steps/epoch  ← 是 Stage 1 (476.6) 的 2 倍
```

**为什么是 2 倍？**
- Batch 小 4 倍 (1024 vs 4096) → steps/epoch ×4
- 无 dual /2 因子（每步都训 S2）→ steps/epoch ÷2
- 净效应：×4 ÷2 = ×2

#### 4.3.2 训练量推荐

| 档位 | Total Steps | 全季覆盖 epoch | 占 Stage1 比例 | 说明 |
|------|------------|---------------|--------------|------|
| 最低 | 15,000 | 15.74 | 7.9% | 快速验证 FiLM 有效性 |
| **推荐** | **30,000** | **31.48** | **15.7%** | ⭐ **续训标准量，配置默认值** |
| 充分 | 47,660 | 50.01 | 25.0% | 充分收敛 |
| 理想 | 57,180 | 60.00 | 30.0% | 对齐续训上限（30%） |

**当前配置**（`configs/train/stage1_5_dual_conditioned_vits.yaml`）：`max_steps: 30000` ✅

**为什么 30k (31.48 epoch) 够用？**
- 续训阶段（continual pretraining）标准是基训的 **15-30%**（GFM CVPR 2023: 续训 100 ep vs 从头 800 ep = 12.5%）
- 31.48 / 200 = **15.74%**，落在文献区间，偏保守但可接受
- FiLM/phi_encoder 是零初始化的小模块（2.9M 参数），收敛快
- **10k step (10.49 epoch) 设为 Go/No-Go 门槛**，可根据收敛情况调整到 50k

**建议训练策略**（详见 [[Stage1.5_完整训练执行方案_FINAL]] §20.4）：
1. 先跑 30k，每 5k 存 checkpoint
2. 10k 时做关键验证（φ 泄漏测试、对齐损失）
3. 若 loss 已平 → 可提前停；若还在降 → 延长到 50k

#### 4.3.3 易错点警示

> [!danger] 常见错误：直接套用 Stage 1 的换算
> 
> **错误推理**：
> - "Stage 1 的 95k = 200 epoch"
> - "Stage 1 的 476.6 steps/epoch"
> - "所以 Stage 1.5 的 30k = 30000/476.6 = 63 epoch" ❌
> 
> **为什么错**：
> 1. Stage 1.5 的 batch 配置完全不同（1024 vs 4096）
> 2. Stage 1.5 无 dual 轮流（每步都训 S2，vs Stage 1 每 2 步训 1 次）
> 3. 两个错误方向相反，恰好抵消成 2 倍差异
> 
> **正确做法**：
> - 永远从第一性原理算：`steps/epoch = N_samples / B_effective`
> - 确认当前阶段的 batch size、accumulation、训练模式
> - 不要跨阶段复制数字

**为什么 v1.0 会出错**：
- 本文 v1.0 (2026-07-01) 写成时，Stage 1.5 的配置文件头部注释尚未完善
- 错误地假设"同一数据集 → 换算关系相同"
- Stage 1.5 的详细文档（25 号）在 2026-07-03 才定稿
- 现已修正，并在 §4.3.3 补充防错检查清单

### 4.4 阶段 2：状态动力学

> [!warning] 阶段 2 不能用全季覆盖 epoch 换算
> 阶段 2 用的是 EarthNet2021 / DynamicEarthNet / Sen1Floods11，**样本数与 SSL4EO 完全不同**。必须按每个数据集的 `N_samples / global_batch` 单独算。

| 数据集 | 典型样本数 | 建议 batch | Steps/epoch | 推荐 total epoch |
|--------|-----------|-----------|------------|----------------|
| EarthNet2021 mini-cube | ~32,000 | 128 | 250 | 50–80 |
| DynamicEarthNet | ~75 cube（大）| 16 | 5 | 200–300 |
| Sen1Floods11 | ~4,831 | 64 | 75 | 100 |

**当前配置**（`stage2_dynamics.yaml`）：`max_steps: 50000` ← **占位骨架，等 loader 落地后按上表重算**

**强制规则**（引自 22 号文档 §3.5）：
1. Stage 2a 单数据集跑通架构（冻结编码器）
2. Stage 2b 多数据集联合训练（field_mask + task_id 门控）
3. Stage 2c 解冻编码器联合微调（lr 是主 lr 的 1/10）
4. **早停由验证集 rollout 指标决定，不按 step 硬停**

### 4.5 阶段 3：条件观测解码

- 轻量 U-Net / MAE decoder：50–80 epoch（按 EarthNet 数据算）
- 与 Stage 2 建议**串行训练**（Stage 2 冻结后再训 decoder），第一版不上扩散模型

### 4.6 阶段 4：下游任务微调

按标准微调 schedule（不是预训练）：

| 任务 | Epoch | Batch |
|------|-------|-------|
| EuroSAT 分类 | 150 | 256 |
| Sen1Floods11 洪水分割 | 100 | 16 |
| DynamicEarthNet LULC | 100 | 8 |
| 线性探测（评估用） | 50–100 | 256 |

### 4.7 阶段 5：基础模型对比

Frozen encoder / LoRA / Full fine-tune，30–100 epoch 按任务定。重点是**公平对比**（同任务同评估协议），不是堆 step。

---

## 5. 常见误解与澄清

### 误解 1："95k = 100 epoch"

**错误来源**：把 global batch 误算为 2048（8×256）
**正确**：global batch = 4096（8×512），95k = 200 全季覆盖 epoch（S2 视角）

### 误解 2："50k = 420 epoch"

**错误来源**：把 `random_season` sample-epoch 直接当"epoch"，且没除以 dual 的 /2
**正确**：50k / 476.6 = 105 全季覆盖 epoch（S2 视角）

### 误解 3："我应该再加 step 到 380k"

**错误来源**：16 号文档 §4.2 基于错误 batch=256 的推荐
**正确**：当前 95k 已经是 SSL4EO baseline 的 2 倍，属于 SatMAE 改进版区间，**不需要再加**

### 误解 4："random_season=True 让每个 epoch 只看 1/4 数据"

**语义澄清**（见 `data/datasets/ssl4eo_dual.py:171-178`）：
- ✅ 每个 tar 样本内部有 4 季，`random_season=True` 是从 4 季里选 1 个返回
- ✅ dataloader 仍然遍历全部 244k 个样本
- ✅ 期望上 4 个 dataloader-epoch 覆盖所有季节 → 换算成"全季覆盖 epoch"要除以 4

### 误解 5："Dual 模式下 S2 每 step 都消耗数据"

**代码事实**（见 `train/train_stage1_dual.py:110-135`）：
- 每 step 从 dataloader 取 1 个 batch（batch 里同时有 s1、s2）
- 根据 `step % 2` 只用其中一个模态做前向+反向
- 数据消耗：**每 step 消耗 1 个 batch**；训练量：**每模态 = total_steps / 2 次梯度更新**

### 误解 6："Stage 1.5 可以直接套用 Stage 1 的换算关系"⚠️

**错误来源**：本文 v1.0 的 §4.3（已在 v1.2 修正）
**错误推理**：
- "Stage 1 的 95k = 200 epoch，换算系数 476.6 steps/epoch"
- "Stage 1.5 也用 SSL4EO 数据集，应该一样"
- "所以 30k / 476.6 = 63 epoch" ❌

**为什么错**：
1. **Batch 配置不同**：Stage 1.5 的 effective batch = 1024（8×64×2），而 Stage 1 是 4096
2. **训练模式不同**：Stage 1.5 每步同时训 S1+S2，而 Stage 1 是 dual 轮流（S2 每 2 步训 1 次）
3. **净效应**：batch 小 4 倍 → steps/epoch ×4；无 /2 因子 → steps/epoch ÷2；净效应 = ×2

**正确做法**：
```python
# Stage 1.5 的配置
B_eff = 8 GPU × 64 batch × 2 accum = 1,024
steps_per_epoch = 975,872 / 1,024 = 953  # 是 Stage 1 (476.6) 的 2 倍
30,000 steps / 953 = 31.48 epoch ✅
```

**根本教训**：**不同阶段的换算必须独立验证，禁止跨阶段复制数字。**

---

## 5.5 通用换算检查清单（防错 SOP）

每次进行 step ↔ epoch 换算时，**必须**按以下流程操作：

### ✅ 第 1 步：确认数据集参数
```yaml
数据集名称: _______
样本总数 N_samples: _______
是否有季节维度: □ 是（几季？___）  □ 否
```

### ✅ 第 2 步：确认训练配置（从 config 文件读取）
```yaml
GPU 数量: _______
Per-GPU batch size: _______
Gradient accumulation steps: _______
→ Effective global batch = GPU数 × per-GPU × accumulation = _______
```

### ✅ 第 3 步：确认训练模式
```yaml
模态处理方式:
  □ 单模态（S2-only / S1-only）
  □ Dual 轮流（S1/S2 交替，每模态只占一半 step）
  □ 每步同时训 S1+S2（Stage 1.5 / 配对训练）
  □ 其他: _______
```

### ✅ 第 4 步：计算 steps/epoch（第一性原理）
```python
# 基础公式
if 有季节维度 and 用全季覆盖口径:
    N_total = N_samples × 季节数
else:
    N_total = N_samples

# 是否有 dual 轮流的 /2 因子？
if 训练模式 == "Dual 轮流" and 你关心某单一模态:
    divisor = 2
else:
    divisor = 1

steps_per_epoch = N_total / (B_effective × divisor)
```

### ✅ 第 5 步：交叉验证（至少两种方式）
```python
# 方式 1：直接除
target_steps / steps_per_epoch = ___ epoch

# 方式 2：样本吞吐
target_steps × B_effective = ___ 总样本数
___ 总样本数 / N_total = ___ epoch

# 方式 3：相对其他阶段（如果有已知基准）
已知阶段的 steps_per_epoch = ___
当前阶段 vs 已知阶段的 batch 比例 = ___
当前阶段 vs 已知阶段的 dual 因子比例 = ___
→ 当前 steps_per_epoch = 已知 × batch比例 × dual比例 = ___
```

### ✅ 第 6 步：文档记录检查
```yaml
是否在配置文件头部写明换算关系: □ 是  □ 否
是否在权威文档中记录: □ 是  □ 否
是否与其他文档冲突: □ 否  □ 是（冲突文档: _______）
```

### 🚨 红旗警示（出现以下情况立即停止，重新验证）

- [ ] 直接从另一个阶段复制了 steps/epoch 数字
- [ ] 计算结果与直觉严重不符（如续训 epoch 超过基训）
- [ ] 配置文件的注释与实际计算不一致
- [ ] 多份文档给出的 epoch 数不同
- [ ] 没有用至少两种方式交叉验证

### 示例：Stage 1 vs Stage 1.5 对比

| 检查项 | Stage 1 | Stage 1.5 | 是否相同？ |
|--------|---------|-----------|-----------|
| 数据集 | SSL4EO-S12 | SSL4EO-S12 | ✅ 相同 |
| N_samples | 975,872 | 975,872 | ✅ 相同 |
| Per-GPU batch | 512 | 64 | ❌ **不同** |
| Accumulation | 1 | 2 | ❌ **不同** |
| Effective batch | 4,096 | 1,024 | ❌ **不同（4倍）** |
| 训练模式 | Dual 轮流 | 同时训 S1+S2 | ❌ **不同** |
| Dual /2 因子 | 有 | 无 | ❌ **不同** |
| **Steps/epoch** | **476.6** | **953** | ❌ **不同（2倍）** |

**结论**：尽管数据集相同，但换算关系完全不同，**不能**直接套用。

---

## 6. 配置文件落地模板

所有 `configs/train/*.yaml` 应在顶部加以下注释块：

```yaml
# ============================================================
# Step/Epoch 换算（权威：任务描述相关/23_Step_Epoch换算与各阶段训练时长权威汇总.md）
# ============================================================
# 数据集: SSL4EO-S12-v1.1, 243,968 locations × 4 seasons
# 训练模式: Dual (S1/S2 alternating), random_season=true
# Global batch: 8 GPU × 512/GPU = 4096
#
# Steps/epoch（三种口径）:
#   A. 数据集遍历 epoch:           59.6 steps
#   B. Sample-epoch S2-only 全季:  238.3 steps
#   C. Sample-epoch Dual S2 视角:  476.6 steps  ⭐ 对标顶会用这个
#
# 本 config 的 max_steps = XXX
#   ≈ XXX / 476.6 = YYY 全季覆盖 epoch（S2 视角）
#   vs SSL4EO baseline (100 epoch): Z.Z×
# ============================================================
```

**批量更新**（不涉及功能改动）：
- `stage1_vits_dual_staged.yaml`：`max_steps: 95000  # ≈ 200 S2 全季 epoch，SSL4EO baseline 2×`
- `stage1_5_film.yaml`：`max_steps: 30000  # ≈ 63 S2 全季 epoch，续训标准量`
- `stage1_dual.yaml`（旧版）：加"deprecated，见 vits_dual_staged"注释

---

## 7. 论文写作对应文本（Method 章节可直接用）

```markdown
### Pretraining Setup

We pretrain the observation encoder on SSL4EO-S12 (243,968 locations, each with 
4 seasonal Sentinel-1/Sentinel-2 pairs). Training uses a dual-modality alternating 
scheme (S1/S2 on odd/even steps) with `random_season` sampling as data augmentation.

Given a global batch size of 4,096 (8 × 512), we train for 95,000 steps, which 
corresponds to **200 full-coverage epochs from the S2 modality perspective** 
(computed as 95,000 / 476.6, where 476.6 = 243,968 × 4 × 2 / 4,096). This is 
**2× the SSL4EO-S12 baseline** (100 epochs) and aligned with SatMAE's improved 
variant (200 epochs). The 2× factor accounts for the fact that dual-modality 
alternating training allocates only half of each step's gradient updates to 
each modality.
```

---

## 8. 附录：18/19/20 号文档合并说明

本文合并并统一了以下三份历史文档的结论：

| 原文档 | 保留价值 | 结论合并去向 |
|--------|---------|-------------|
| 18_Step与Epoch对应关系详细推导 | 三种 epoch 定义的推导过程 | 本文 §2、§3 |
| 19_Step与Epoch混淆点澄清_基于代码验证 | 基于源码的语义验证 | 本文 §5 |
| 20_训练设置选择_论文发表视角分析 | 论文写作视角 + 顶会对标 | 本文 §4.2、§7 |

三份文档仍保留在原位（供审阅历史推理链），但**任何冲突以本文为准**。

---

## 9. 附录 A —— 22 篇顶会文献训练时长调研

> 本附录整合自原 16 号文档 §2，作为 §4 各阶段推荐的文献依据。

### A.1 自然图像 MAE / 对比学习（计算机视觉基线）

| # | 论文 | 会议 | Epoch | Batch | 数据集 | 备注 |
|---|------|------|-------|-------|--------|------|
| 1 | **MAE** (He et al.) | CVPR 2022 | **800 / 1600** | 4096 | ImageNet-1K (1.28M) | 1600ep 仍不饱和；高掩码每 epoch 只看 25% patch |
| 2 | VideoMAE (Tong et al.) | NeurIPS 2022 | 800–3200 | 1024 | K400 / SSv2 / UCF101 | 90% 掩码 → 比对比学习更需要 epoch |
| 3 | DINO (Caron et al.) | ICCV 2021 | 300（最长 800）| 1024 | ImageNet | EMA teacher，多 crop |
| 4 | MoCo v3 (Chen et al.) | ICCV 2021 | 300 | 4096 | ImageNet | ViT-L 在 300ep 饱和 |
| 5 | SimCLRv2 (Chen et al.) | NeurIPS 2020 | 800 | 4096 | ImageNet | LARS optimizer |
| 6 | SwAV (Caron et al.) | NeurIPS 2020 | 800 | 4096 | ImageNet | 100→72.1%、400→74.3%、800→75.3%（非线性收益）|
| 7 | BYOL (Grill et al.) | NeurIPS 2020 | 1000 | 4096 | ImageNet | 强调 100ep 结果不外推 |
| 8 | DINOv2 (Oquab et al.) | TMLR 2024 | — | 3072 | LVD-142M | 22,016 A100-h；小模型用蒸馏而非从头 |
| 9 | data2vec 2.0 (Baevski et al.) | ICML 2023 | 150 | — | ImageNet | 多 mask 摊销 teacher 成本 |

**MAE 核心论证**（引自 MAE 原文）：*"accuracy improves steadily with longer training... no saturation even at 1600 epochs"*。原因：encoder 每 epoch 只看到 25% patch（vs 对比学习 200%+ patch via 多 crop），需要更多 epoch 摊薄，但 wall-clock 反而更省。

### A.2 遥感自监督（直接对标 ObsWorld）

| # | 论文 | 会议 | Epoch / Step | Batch | 数据集 | 备注 |
|---|------|------|--------------|-------|--------|------|
| 10 | **SatMAE** (Cong et al.) | NeurIPS 2022 | **50→200** (fMoW-Sentinel) | 4096 | 712,874 imgs × 13 bands | 200ep Top-1 = 63.84%，"longer is better" |
| 11 | SatMAE++ (Noman et al.) | CVPR 2024 | 800（RGB）/ 50（Sentinel）| 4096 | fMoW | 多尺度收敛快，12ep 达 SOTA |
| 12 | Scale-MAE (Reed et al.) | ICCV 2023 | 800（RGB）| — | FMoW-RGB | 对齐 SatMAE 基线 |
| 13 | **SSL4EO-S12** (Wang et al.) | benchmark | **100** | 256 | **本项目数据集**，~1M patches | MAE/MoCo/DINO/data2vec 全部 100ep |
| 14 | Presto (Tseng et al.) | ICLR 2024 | 20（≈119k step）| 4096 | 21.5M pixel-timeseries | 模型仅 0.8M 参数 |
| 15 | SkySense (Guo et al.) | CVPR 2024 | **875k step** | 240 | 21.5M 多模态序列 | 2.06B 参数，80×A100 |
| 16 | Prithvi-EO 2.0 (Szwarcman et al.) | 2024 | **400** | 3840 | 4.2M HLS | 300M/600M 参数 |
| 17 | DOFA / DOFA+ (Xiong et al.) | ICLR 2025 | 渐进 **100→20→1** | 128 | 50K→410K→11.5M | "marginal gain beyond 80 epochs" |
| 18 | EarthPT (Smith et al.) | 2023 | 90k step（≈14.4B tokens）| 164k tokens | — | Chinchilla N≈20D |
| 19 | GFM (Mendieta et al.) | CVPR 2023 | **100**（续训 + 蒸馏）| 2048 | GeoPile ~600k | 续训比从头 800ep 省 8× |
| 20 | **SeCo** (Mañas et al.) | ICCV 2021 | **200** | 256 | ~1M Sentinel-2，5 季 | 季节对比学习（最贴近 Stage 1.5）|

### A.3 世界模型 / 动力学预测（对应 Stage 2）

| # | 论文 | 会议 | 训练量 | 备注 |
|---|------|------|--------|------|
| 21 | **DreamerV3** (Hafner et al.) | Nature 2025 | 按 env steps：500K / 1M / 100M | 想象 horizon=16 |
| 22 | **IRIS** (Micheli et al.) | ICLR 2023 | **600 epoch** 总，**staged**：AE ep 5 → Transformer ep 25 → AC ep 50 | 多阶段 staged-init |

### A.4 综合规律

| 规律 | 证据 | ObsWorld 对应 |
|------|------|--------------|
| MAE 类需要长训练 | MAE 1600ep 不饱和 | Stage 1 至少 100ep（已 200ep✅） |
| 同数据集基准必须对齐 | SSL4EO/SeCo/SatMAE 互相对齐 | Stage 1 至少 SSL4EO 100ep |
| 续训阶段时长可大幅缩短 | GFM 100ep 续训 vs 从头 800ep | Stage 1.5 只需 30ep 左右 |
| 动力学模型按 env step 或 cube 数定 | DreamerV3 / IRIS | Stage 2/3 按数据集算 |
| 早停由验证集指标决定 | 几乎所有论文 | Stage 2 按 rollout 早停 |
| 小数据集下游要补 epoch | SatMAE EuroSAT 150ep | Stage 4 走 100–150ep |
| 多阶段 staged init | IRIS / SimCLRv2 / DINOv2 / GFM | 你的 5+1 阶段就是 staged |

### A.5 文献引用清单

**MAE / 视觉自监督**：

1. He et al., *MAE*, CVPR 2022. https://arxiv.org/abs/2111.06377
2. Tong et al., *VideoMAE*, NeurIPS 2022. https://arxiv.org/abs/2203.12602
3. Caron et al., *DINO*, ICCV 2021. https://arxiv.org/abs/2104.14294
4. Chen et al., *MoCo v3*, ICCV 2021. https://arxiv.org/abs/2104.02057
5. Chen et al., *SimCLRv2*, NeurIPS 2020. https://arxiv.org/abs/2006.10029
6. Caron et al., *SwAV*, NeurIPS 2020. https://arxiv.org/abs/2006.09882
7. Grill et al., *BYOL*, NeurIPS 2020. https://arxiv.org/abs/2006.07733
8. Oquab et al., *DINOv2*, TMLR 2024. https://arxiv.org/abs/2304.07193
9. Baevski et al., *data2vec 2.0*, ICML 2023. https://arxiv.org/abs/2212.07525

**遥感自监督**：

10. Cong et al., *SatMAE*, NeurIPS 2022. https://arxiv.org/abs/2207.08051
11. Noman et al., *SatMAE++*, CVPR 2024. https://arxiv.org/abs/2403.05419
12. Reed et al., *Scale-MAE*, ICCV 2023. https://arxiv.org/abs/2212.14532
13. Wang et al., *SSL4EO-S12*, IGARSS 2023. https://arxiv.org/abs/2211.07044
14. Tseng et al., *Presto*, ICLR 2024. https://arxiv.org/abs/2304.14065
15. Guo et al., *SkySense*, CVPR 2024. https://arxiv.org/abs/2312.10115
16. Szwarcman et al., *Prithvi-EO 2.0*, 2024. https://arxiv.org/abs/2412.02732
17. Xiong et al., *DOFA*, ICLR 2025. https://arxiv.org/abs/2403.15356
18. Smith et al., *EarthPT*, 2023. https://arxiv.org/abs/2309.07207
19. Mendieta et al., *GFM*, CVPR 2023. https://arxiv.org/abs/2302.04476
20. Mañas et al., *SeCo*, ICCV 2021. https://arxiv.org/abs/2103.16607

**世界模型 / 动力学**：

21. Hafner et al., *DreamerV3*, Nature 2025. https://arxiv.org/abs/2301.04104
22. Micheli et al., *IRIS*, ICLR 2023 (notable-top-5%). https://arxiv.org/abs/2209.00588

---

## 10. 附录 B —— 历史推导过程（合并说明）

本文合并了以下四份文档，原文档已删除，主要内容已收敛于此：

| 原文档 | 主要贡献 | 已合并至 |
|--------|---------|---------|
| 16 各阶段训练步数与 epoch 调研报告 | 22 篇顶会训练时长调研 | 本文 §9（附录 A）|
| 18 Step 与 Epoch 对应关系详细推导 | 三种 epoch 定义 + S1/S2 对等性证明 | 本文 §2、§3 |
| 19 Step 与 Epoch 混淆点澄清（基于代码） | `random_season` / dual / global batch 三处代码语义核对 | 本文 §5 |
| 20 训练设置选择：论文发表视角 | 论文对标口径 + 写作视角 | 本文 §4.2、§7 |

**关键错误更正记录**：

1. **早期误算**（16 号原文 §1.2）：把 `batch_size: 64` 当作 global batch，实际是 per-GPU
   - 错误结论："Stage 1 应跑 380k–760k step"
   - 正确结论：global batch 4096 时，100 epoch 只需 47k step
2. **early "420 epoch" 说法**（18 号原文提到）：把 random-season sample-epoch 当"epoch"，且没考虑 dual /2
   - 正确：50k / 476.6 = 105 全季覆盖 epoch（S2 视角）
3. **early "200 patch-epoch" 表述**（17 号周报）：正确，等同本文的 S2 视角全季覆盖 epoch

---

## 11. 版本日志

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-01 | 建立权威汇总，合并 18/19/20 号；标注 15/16 号过期段落 |
| v1.1 | 2026-07-01 | 完整吸收 16 号顶会调研（§9 附录 A），删除 16/18/19/20 号原文档 |
| **v1.2** | **2026-07-03** | **修正 §4.3 Stage 1.5 换算错误（63→31.48 epoch）；补充易错点说明** |

---

**v1.2 重要修正说明**：

v1.0 版本的 §4.3 错误地将 Stage 1.5 的 30k steps 换算为 63 epoch，原因是直接套用了 Stage 1 的 476.6 steps/epoch。实际上：

- Stage 1.5 的 batch 配置与 Stage 1 完全不同（1024 vs 4096）
- Stage 1.5 无 dual 轮流模式（每步同时训 S1+S2）
- 正确换算：**953 steps/epoch**，30k steps = **31.48 epoch**

此错误导致对训练量的误判（实际续训占比 15.7%，v1.0 误以为 31.5%）。已同步至 [[Stage1.5_完整训练执行方案_FINAL]] §20（该文档定稿于 2026-07-03，包含正确换算）。

**教训**：
1. 不同阶段的 batch/accumulation/训练模式可能不同，**禁止跨阶段复制换算关系**
2. 换算时必须从第一性原理出发：`steps/epoch = N_samples / B_effective`
3. 配置文件头部注释应明确列出换算公式，防止误用

---

**维护规则**：
1. 未来若改动 batch_size / GPU 数 / random_season / dual 模式，**必须更新本文 §1.2 和 §3.3**
2. **每个阶段的换算必须独立验证**，不得直接套用其他阶段的 steps/epoch
3. 新增训练脚本时，在 config 顶部粘贴 §6 的注释块并填写对应数字
4. 论文写作、周报、审稿回复涉及 epoch/step 时，**引用本文而非旧文档**
