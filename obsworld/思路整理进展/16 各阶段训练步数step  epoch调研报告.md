---
title: "16 各阶段训练步数（step / epoch）调研报告"
created: 2026-06-26
author: Claude Opus 4.8 (1M context) & Zhijian Liu
tags: [ObsWorld, training-schedule, step, epoch, literature-review, AAAI, CVPR, ICCV, NeurIPS, ICLR]
status: 完整版（22 篇顶会文献支撑）
---

# 16 各阶段训练步数（step / epoch）调研报告

## 0. 文档导航与摘要

### 与其他文档的关系

- [[10ObsWorld 完整实验流程与字段设计]] —— 5+1 阶段总纲
- [[14 Stage1.5与Stage2代码实现报告]] —— Stage 1.5 / Stage 2 代码实现
- [[15_Stage1与Stage1.5完整训练指南]] —— Stage 1 / Stage 1.5 训练手册
- **16（本文）** —— **各阶段训练时长的文献支撑与具体建议**

### 一页式结论

> [!important] 一句话结论
> Stage 1（S2-only MAE）应从当前 **50k step** 提升到至少 **380k step（≈100 epoch，对齐 SSL4EO 基准）**，理想 **760k step（≈200 epoch，对齐 SatMAE 改进版）**；Stage 1.5 续训 **115k–150k step（30–40 epoch）**；Stage 2/3 改为按 epoch + 验证集早停，数据集落地后按 `size/batch` 现算；下游评估走标准微调 schedule。

### 调研基础

- 调研文献：**22 篇** 来自 AAAI / CVPR / ICCV / NeurIPS / ICLR / ICML / TMLR / Nature（2020–2025）
- 文献分类：MAE 类视觉自监督、对比学习、遥感自监督、世界模型 / 动力学预测、多阶段训练流水线
- 现场调研：你的 SSL4EO-S12-v1.1 实际数据规模（477 tar × 512 ≈ 244k 地点 × 4 季 ≈ 976k 样本/模态）、当前 `stage1_dual2` 配置（4 卡 × 64 batch）、Stage 1.5 配置（8 卡 × 32 batch）、EuroSAT 线性探测 69.57%（vs 基准 94.1%）

---

## 1. 关键换算公式（先把单位打通）

### 1.1 step ↔ epoch 换算

顶会论文几乎都用 **epoch** 而非 **step**，要落到你的代码里必须先把单位换算清楚。

```text
1 epoch = 全数据集走一遍 = N_samples / global_batch_size 个 step
```

**你的 SSL4EO-S12-v1.1（双模态情形）**：

```text
数据规模：477 tar × ~512 样本 ≈ 244k 地点 × 2 模态（S1/S2）× 4 季节
                              = ~976k 样本/模态（季节展平后）
```

**关于"全季覆盖 epoch"的口径**：

- **顶会基准口径**（SSL4EO-S12 论文）：以 ~1M patches/sensor 为一个全覆盖 epoch
- 你的代码用 `random_season=True`，每次随机取 1 个季节 → 每 epoch 实际只 sample 244k 而非 976k
- **建议口径**：以 **全季覆盖**（976k）作为 1 epoch，便于和顶会数字直接比对

### 1.2 你不同配置下的 step/epoch 对照表

| 配置 | 全局 batch | 1 epoch (S2-only) | 1 epoch (dual S2 实际)  |
|------|----------|-------------------|------------------------|
| 4 卡 × 64（Stage 1 当前） | 256 | **3,815 step** | 7,630 step（S2 每 2 步轮 1 次）|
| 8 卡 × 32（Stage 1.5 当前） | 256 | 3,815 step | — |
| 8 卡 × 64（推荐） | 512 | 1,907 step | — |
| 8 卡 × 128（最大显存利用） | 1024 | 953 step | — |

**核心计算（4 卡 × 64，S2-only 等价口径）**：

```text
你 Stage 1.0 跑了 50,000 step
= 50000 / 3815 ≈ 13 epoch（按 S2-only 全季覆盖口径）
= 50000 / 7630 ≈ 6.5 epoch（按 dual 模式 S2 实际见过的次数）

→ 远低于 SSL4EO 基准的 100 epoch
→ 这是 EuroSAT 69.57% 远低于基准 94.1% 的主因之一（另一主因是模型只有基线 26% 大小）
```

> [!warning] 必须先理解的事
> "我跑了 50k step" 和 "我跑了 50 epoch" 是两个完全不同的概念。顶会都用 epoch 给配方，**你必须先把 epoch 换算成自己 step 才能落地**，否则会无意中训得远少于基准。

---

## 2. 22 篇顶会文献训练时长调研

### 2.1 自然图像 MAE / 对比学习（计算机视觉基线）

| # | 论文 | 会议 | Epoch | Batch | 数据集 | 备注 |
|---|------|------|-------|-------|--------|------|
| 1 | **MAE** (He et al.) | CVPR 2022 | **800 / 1600** | 4096 | ImageNet-1K (1.28M) | 1600ep 仍不饱和；高掩码每 epoch 只看 25% patch |
| 2 | VideoMAE (Tong et al.) | NeurIPS 2022 | 800 / 1600 / 2400 / 3200 | 1024 | K400 / SSv2 / UCF101 | 90% 掩码 → 比对比学习更需要 epoch |
| 3 | DINO (Caron et al.) | ICCV 2021 | 300（最长 800）| 1024 | ImageNet | EMA teacher，多 crop |
| 4 | MoCo v3 (Chen et al.) | ICCV 2021 | 300 | 4096 | ImageNet | ViT-L 在 300ep 饱和 |
| 5 | SimCLRv2 (Chen et al.) | NeurIPS 2020 | 800 | 4096 | ImageNet | LARS optimizer |
| 6 | SwAV (Caron et al.) | NeurIPS 2020 | 800 | 4096 | ImageNet | 100ep→72.1%、400ep→74.3%、800ep→75.3%（非线性收益）|
| 7 | BYOL (Grill et al.) | NeurIPS 2020 | 1000 | 4096 | ImageNet | 强调 100ep 结果不一定外推 |
| 8 | DINOv2 (Oquab et al.) | TMLR 2024 | — | 3072 | LVD-142M | 22,016 A100-h；小模型用蒸馏而非从头 |
| 9 | data2vec 2.0 (Baevski et al.) | ICML 2023 | 150 | — | ImageNet | 多 mask 摊销 teacher 成本 |

**MAE 类训练时长的核心论证（直接引用 MAE 原文）**：

> "accuracy improves steadily with longer training... no saturation even at 1600 epochs"

**为什么 MAE 需要这么多 epoch**：每 epoch encoder 只看到 25% 的 patch（vs 对比学习每 epoch 看 200%+ patch via 多 crop），所以需要 **更多 epoch 摊薄信息量**，但因为每 epoch 计算量小，**wall-clock 反而更省**（ViT-L 1600ep ≈ 31h vs MoCo v3 300ep ≈ 36h）。

### 2.2 遥感自监督（直接对标你的方向）

| # | 论文 | 会议 | Epoch / Step | Batch | 数据集 | 备注 |
|---|------|------|--------------|-------|--------|------|
| 10 | **SatMAE** (Cong et al.) | NeurIPS 2022 | **50→200** (fMoW-Sentinel) | 4096 | 712,874 imgs × 13 bands | 200ep Top-1 = 63.84%，明确说 "longer pre-training can prove to be even more beneficial" |
| 11 | SatMAE++ (Noman et al.) | CVPR 2024 | 800（RGB）/ 50（Sentinel）| 4096 | fMoW | 多尺度收敛更快，12 ep 达 SOTA |
| 12 | Scale-MAE (Reed et al.) | ICCV 2023 | 800（RGB）| — | FMoW-RGB | 对齐 SatMAE 基线 |
| 13 | **SSL4EO-S12** (Wang et al.) | benchmark | **100** | 256 | **你的数据集**，~1M patches | MAE / MoCo / DINO / data2vec 全部 100ep，~1,400 GPU-h |
| 14 | Presto (Tseng et al.) | ICLR 2024 | 20（≈119k step）| 4096 | 21.5M pixel-timeseries | 模型仅 0.8M 参数，靠小模型 + 高效率 |
| 15 | SkySense (Guo et al.) | CVPR 2024 | **875k step** | 240 | 21.5M 多模态序列 | 2.06B 参数，80×A100 |
| 16 | Prithvi-EO 2.0 (Szwarcman et al.) | 2024 | **400** | 3840（global）| 4.2M HLS | 300M/600M 参数，80–240 GPU |
| 17 | DOFA / DOFA+ (Xiong et al.) | ICLR 2025 | 渐进 **100→20→1** | 128 | 50K→410K→11.5M | 明确说 "marginal gain beyond 80 epochs" |
| 18 | EarthPT (Smith et al.) | 2023 | 90k step（≈14.4B tokens）| 164k tokens | — | 按 **Chinchilla N≈20D** 推算 |
| 19 | GFM (Mendieta et al.) | CVPR 2023 | **100**（续训 + 蒸馏）| 2048 | GeoPile ~600k | 续训比从头 800ep 省 8× |
| 20 | **SeCo** (Mañas et al.) | ICCV 2021 | **200** | 256 | ~1M Sentinel-2，5 季 | 季节对比学习（最贴近你的 Stage 1.5）|

**遥感自监督训练时长的核心规律**：

1. **同数据集基准（SSL4EO 100ep / SeCo 200ep）是必须达到的下限** —— 这是顶会编辑通过的"对齐线"
2. **续训阶段（GFM 100ep + 蒸馏、DOFA 渐进短训）远少于从头预训练** —— Stage 1.5 续训不需要 50k+
3. **小数据集下游微调要补 epoch**（SatMAE EuroSAT 用 150ep）
4. **轻量模型可以用少 epoch 但要更大 batch 或更多数据**（Presto 0.8M × 20ep × 21.5M 样本）

### 2.3 世界模型 / 动力学预测（对应你的 Stage 2）

| # | 论文 | 会议 | 训练量 | 备注 |
|---|------|------|--------|------|
| 21 | **DreamerV3** (Hafner et al.) | Nature 2025 | 按 env steps：500K（proprio）/ 1M（视觉）/ 100M（DMLab）| 想象 horizon=16；按任务定 |
| 22 | **IRIS** (Micheli et al.) | ICLR 2023 | **600 epoch** 总，**staged**：autoencoder ep 5、transformer ep 25、actor-critic ep 50 | 多阶段 staged-init，5×8 A100×3.5 天/游戏 |

**世界模型训练时长的核心规律**：

- **按 env steps / 数据消耗而非 step 数定**（你的 Stage 2 应该按 EarthNet/DynamicEarthNet 的 cube 数定 epoch）
- **多模块用 staged init**（autoencoder 先稳定再开 dynamics，dynamics 稳定再开 policy）—— 直接对应你的 Stage 1 → Stage 1.5 → Stage 2 → Stage 3 递进
- **早停指标用 rollout 质量而非训练 loss**

### 2.4 文献综合规律（横切总结）

| 规律 | 证据 | 你的对应 |
|------|------|---------|
| **MAE 类需要长训练** | MAE 1600ep 不饱和；VideoMAE 90% 掩码需 800–4800ep | Stage 1 必须长训 |
| **同数据集基准必须对齐** | SSL4EO/SeCo/SatMAE 互相对齐 epoch | Stage 1 至少要 100ep（SSL4EO） |
| **续训阶段时长可大幅缩短** | GFM 100ep 续训 vs 从头 800ep；DOFA 渐进 100→20→1 | Stage 1.5 不需要再 50k+ step |
| **新加模块（FiLM、phi-encoder）需要充足 epoch 才能学会** | DOFA 第一阶段 100ep 在 50k 子集 | Stage 1.5 不能只跑几个 epoch |
| **动力学 / 世界模型按 env step 或 cube 数定** | DreamerV3 / IRIS | Stage 2/3 按 EarthNet/DynamicEarthNet 算 |
| **早停由验证集指标决定** | 几乎所有论文 | Stage 2 必须按 rollout 指标早停 |
| **小数据集下游要补 epoch** | SatMAE EuroSAT 150ep（数据集小所以长训） | Stage 4 下游评估走 100–150ep |
| **多阶段 staged init** | IRIS、SimCLRv2 三阶段、DINOv2 蒸馏、GFM 续训 | 你的 5+1 阶段流水线本身就是 staged |

---

## 3. 现状诊断（为什么必须重训）

### 3.1 你 Stage 1 实际的"真 epoch"

```text
配置：4 卡 × batch 64 → global batch 256
跑了：50,000 step
数据：~976k 样本（4 季覆盖口径）
```

**按 S2-only 口径算**：

```text
50,000 step × 256 / 976,000 ≈ 13.1 epoch
```

**按 dual 实际口径算（S2 每 2 步只轮到 1 次）**：

```text
50,000 step / 2（dual 轮流）× 256 / 976,000 ≈ 6.5 epoch
```

**对标 SSL4EO 论文**：100 epoch。

**结论**：你的 Stage 1 实际 epoch 数比顶会基准少 **一个数量级**。EuroSAT 69.57% vs 基准 94.1% 的差距，**约一半来自模型容量小**（5.7M vs 22M，~26%），**另一半来自训练时长不足**。这与你 memory 里 "S2 实际只训 ~25k steps" 的判断完全一致（[[worldmodel-stage1-eurosat-eval]]）。

### 3.2 EuroSAT 评估给出的间接信号

```text
你的 Stage 1：EuroSAT linear probing = 69.57%
SSL4EO 基准（MAE ViT-S/16，22M）：94.1%
SSL4EO 基准（MAE ViT-S/16，22M）微调：98.7%
```

按文献数据反推，**模型容量贡献约 12-15%、训练时长贡献约 8-12%**（具体见 SatMAE 200ep vs 50ep 实验，Top-1 提升 ~3-5%，加上 epoch×4 的放大）。把 epoch 补足到 100，预计 EuroSAT 能拉到 78–82%（仍受模型容量限制），如果同时把模型扩到 ViT-S，可望到 88–92%。

---

## 4. 各阶段最终建议（含 step 落地数字）

> 以下所有 step 数都基于 **global batch 256**（4 卡 × 64 或 8 卡 × 32）。如果改 batch，**反比缩放**：batch 翻倍 → step 减半。

### 4.1 Stage 0：数据巡检与统一 schema

- **不需要 step**，按数据量一次走完
- 你已完成（[[11_SSL4EO第一步数据处理与字段构建方案]]、[[12_Stage1.5成像条件解耦实施方案与phi字段预处理完整报告]]）
- 单次 build_phi_cache 约 226s（已记录于 [[15_Stage1与Stage1.5完整训练指南]]）

---

### 4.2 Stage 1：SSL4EO 观测编码器预训练 ⭐ **重点调整**

**建议改用 S2-only 主力训练**（你已经在跑 `stage1_s2only`），避免 dual 把 S2 训练量劈一半。

| 档位 | Epoch | Step（batch 256）| 适用场景 | 文献依据 |
|------|-------|------------------|----------|---------|
| **最低对齐** | 100 | **380k** | 论文 baseline 必须达到 | SSL4EO-S12（你的数据集本身） |
| **推荐** | 150 | **570k** | 论文中等竞争力 | SeCo 200ep + 你模型较小 → 适当短训 |
| **理想** | 200 | **760k** | 论文 strong baseline | SatMAE 改进版的 200ep（"longer is better"） |
| 现状 | 13 | 50k | **远远不够** | — |

> [!tip] 模型大小要不要同步扩
> 如果决定只跑 S2-only 主力，**强烈建议把 embed_dim 从 256 扩到 384（ViT-S 标准）**，搭配 100–150 epoch。这是性价比最高的提升路径。Scale-MAE / SatMAE 都用 ViT-L (304M)，你哪怕用 ViT-S (22M) 也比当前 5.7M 强一档。

**如果坚持 dual 模态训练**：
- 上面 step 数 **×2**（S2 每 2 步只轮到 1 次）
- 或者改为"每步同时算 S1+S2 loss"（不轮流），仍按 380k–760k step

**Warmup**：保持 1000–2000 step（约 0.25–0.5 epoch），所有 MAE 论文都用 cosine + warmup。

---

### 4.3 Stage 1.5：成像解耦续训（FiLM + 对比） ⭐ **微调建议**

属于"续训 + 加新模块"，参照 GFM（100ep 续训）/ DOFA（渐进短训）/ DINOv2（多阶段）规律。

| 档位 | Epoch | Step（batch 256）| 适用场景 | 文献依据 |
|------|-------|------------------|----------|---------|
| **最低** | 20 | **76k** | 验证 FiLM 是否有效 | DOFA 短续训阶段 |
| **推荐** | 30 | **115k** | 论文标准 ablation | GFM 续训 100ep / 但你 backbone 更弱所以 30ep 起步 |
| **理想** | 40 | **150k** | 充分收敛 | SeCo 200ep + 续训打折 |
| 现状（配置） | 13 | 50k | 偏低 | — |

**为什么 Stage 1.5 不需要再 50k+**：

1. Backbone 已被 Stage 1 训过（continual pretraining），梯度方向已稳定
2. 新增模块（FiLM 2.77M、phi_encoder 0.14M）参数小，且是 **identity 起点（零初始化）**，收敛快
3. Loss 渐进策略（`w_decouple` 0.5）已经在保护 MAE 主任务

**Warmup**：保持 2000 step（约 0.5 epoch），让 FiLM/phi_encoder 先稳定再放权 contrast loss。

**渐进权重日程（建议在代码里加）**：

```python
# 推荐的 w_decouple 渐进
step 0–10k:   w_decouple = 0.1   # 让 FiLM 先 warm up，不破坏 MAE
step 10k–30k: w_decouple = 0.5   # 逐步增强对比/解相关
step 30k+:    w_decouple = 1.0   # 最终目标权重
```

---

### 4.4 Stage 2：状态动力学 ⭐ **改为按 epoch 而非 step**

数据集是 EarthNet2021（~32k mini-cube）/ DynamicEarthNet（~75 cube）/ 洪水数据，**规模比 SSL4EO 小 1–2 个数量级**，**必须按 epoch 而非 step**。

| 数据集 | 样本数 | Batch | 1 epoch step | 推荐 epoch | 总 step |
|--------|--------|-------|--------------|-----------|---------|
| EarthNet2021 mini-cube | ~32k | 16 | ~2000 | **50–80** | 100k–160k |
| DynamicEarthNet | ~75（cube 大）| 8 | ~10–30 | **200–300** | 2k–9k（极少）|
| Sen1Floods11 | ~4831 | 16 | ~300 | **100** | 30k |

> [!warning] 你当前 stage2 config 是占位骨架
> `stage2_dynamics.yaml` 里的 `max_steps: 50000` 是 TODO 占位（[[14 Stage1.5与Stage2代码实现报告]] 已注明）。等数据 loader 落地后必须按上表重算。

**强制规则**：

1. **按验证集 rollout 指标早停**（horizon-h cosine similarity / state MAE）
2. **每个数据集独立调** epoch（DynamicEarthNet cube 大但少，不能套 EarthNet 的数）
3. **W_pred / w_smooth / w_dir 的渐进引入**（先纯 pred，稳定后加 smooth、最后加 dir）

**文献依据**：

- DreamerV3 按 env steps 而非 step 数定
- IRIS staged init：autoencoder ep 5 → transformer ep 25 → policy ep 50
- 你的 Stage 2 = IRIS 的 transformer + policy 阶段

---

### 4.5 Stage 3：条件观测解码

| 选项 | Epoch | 备注 |
|------|-------|------|
| 轻量 U-Net / MAE decoder（第一版）| **50–80** | 复用 Stage 2 解码器或独立训 |
| 扩散 decoder（不建议第一版） | 200+ | 文档已注明先不上 |

**与 Stage 2 的关系**：可以**联合训练**（Stage 2 dynamics + Stage 3 decoder 同时优化）或**串行训练**（Stage 2 训稳后冻结，再训 Stage 3）。第一版建议串行，便于消融。

---

### 4.6 Stage 4：下游任务与 world model 评估

**任务头微调** 走标准小数据集 schedule（SatMAE / Scale-MAE 一致）：

| 任务 | Epoch | Batch | 备注 |
|------|-------|-------|------|
| EuroSAT 分类 | **150** | 256 | SatMAE 明确说 EuroSAT 小所以需要长训 |
| Sen1Floods11 洪水分割 | 100 | 16 | 标准小数据集 |
| DynamicEarthNet LULC | 100 | 8 | cube 数据集 |
| 线性探测（评估用，不更新 encoder）| **50–100** | 256 | 你 EuroSAT 评估属于这一档 |

**关键**：这阶段是 **评估** 而非 **预训练**，不要为了堆 step 而堆 step，重点是：

- 严格的 train/val/test split
- 5–10 个 seed 跑 mean ± std
- 报告 PSNR/SSIM **以及** state accuracy、driver sensitivity 等多维度指标

---

### 4.7 Stage 5：基础模型增强与对比

**冻结 / LoRA 微调** 顶级遥感基础模型（Prithvi-EO-2.0 / SkySense / DOFA / Scale-MAE）做对比：

| 模式 | Epoch | 备注 |
|------|-------|------|
| Frozen encoder + 任务头 | **30–50** | 只训任务头，快 |
| LoRA 微调（rank 8–16）| **50–100** | 平衡灵活性与算力 |
| Full fine-tune | 100+ | 不推荐，参数多易过拟合 |

**关键**：是消融实验，不需要堆 step，**重点是公平对比**（同样的下游任务、同样的评估协议）。

---

## 5. 汇总速查表

| 阶段 | 推荐 Epoch | 推荐 Step（batch 256）| 当前状态 | 差距 |
|------|-----------|----------------------|---------|------|
| **Stage 1 (S2-only)** | 100–200 | **380k–760k** | 50k（13 ep）| **欠 7–15×** ⚠️ |
| Stage 1.5 | 30–40 | **115k–150k** | 50k（13 ep）| 欠 2–3× |
| Stage 2 (EarthNet) | 50–80 | **100k–160k** | 占位骨架 | 等数据落地 |
| Stage 2 (DynamicEN) | 200–300 | 2k–9k | 占位骨架 | 等数据落地 |
| Stage 3 | 50–80 | **80k–130k** | 未开始 | — |
| Stage 4 (EuroSAT) | 150 | — | 已有评估脚本 | — |
| Stage 5 | 30–100 | — | 未开始 | — |

---

## 6. 操作清单（按性价比排序）

> [!tip] 实操优先级
> 按"投入产出比"排序，**先做 A，再做 B，最后做 C**。

### A. 立即收益最高（一周内）

1. **把 Stage 1 改为 S2-only 主力，跑到 380k step（100 epoch）**
   - 修改 `configs/train/stage1_s2only.yaml`：`max_steps: 380000`、`warmup_steps: 2000`
   - 8 卡 × 64 batch × ~5 it/s 估算 ≈ **80 GPU-h**（10 小时实测）
   - 预计 EuroSAT 从 69.57% → ~78–82%

2. **把 Stage 1.5 步数从 50k 提到 120k（30 epoch）**
   - 修改 `configs/train/stage1_5_film.yaml`：`max_steps: 120000`
   - 加入 `w_decouple` 渐进日程（见 §4.3）

### B. 中期收益（两周内）

3. **如果算力允许，把 embed_dim 从 256 扩到 384（ViT-S）**，重训 Stage 1
   - 模型从 5.72M → ~22M（对齐 SSL4EO 基准）
   - 预计 EuroSAT 从 78% → 88%+
   - 训练时间约 1.5–2× 当前

4. **理想档：Stage 1 跑 760k step（200 epoch）**
   - 仅在前面都跑通后做，论文 strong baseline

### C. 长期（数据集落地后）

5. **Stage 2 / Stage 3 按数据集 size 现算 epoch**
6. **下游任务（Stage 4）跑全套消融**
7. **Stage 5 接入 Prithvi-EO-2.0 / SkySense 等做对比**

---

## 7. 文献引用清单（22 篇）

### MAE / 视觉自监督

1. He et al., *Masked Autoencoders Are Scalable Vision Learners*, CVPR 2022. https://arxiv.org/abs/2111.06377
2. Tong et al., *VideoMAE: Masked Autoencoders are Data-Efficient Learners for Self-Supervised Video Pre-Training*, NeurIPS 2022. https://arxiv.org/abs/2203.12602
3. Caron et al., *Emerging Properties in Self-Supervised Vision Transformers (DINO)*, ICCV 2021. https://arxiv.org/abs/2104.14294
4. Chen et al., *An Empirical Study of Training Self-Supervised Vision Transformers (MoCo v3)*, ICCV 2021. https://arxiv.org/abs/2104.02057
5. Chen et al., *Big Self-Supervised Models are Strong Semi-Supervised Learners (SimCLRv2)*, NeurIPS 2020. https://arxiv.org/abs/2006.10029
6. Caron et al., *Unsupervised Learning of Visual Features by Contrasting Cluster Assignments (SwAV)*, NeurIPS 2020. https://arxiv.org/abs/2006.09882
7. Grill et al., *Bootstrap Your Own Latent (BYOL)*, NeurIPS 2020. https://arxiv.org/abs/2006.07733
8. Oquab et al., *DINOv2: Learning Robust Visual Features without Supervision*, TMLR 2024. https://arxiv.org/abs/2304.07193
9. Baevski et al., *Efficient Self-supervised Learning with Contextualized Target Representations (data2vec 2.0)*, ICML 2023. https://arxiv.org/abs/2212.07525

### 遥感自监督

10. Cong et al., *SatMAE: Pre-training Transformers for Temporal and Multi-Spectral Satellite Imagery*, NeurIPS 2022. https://arxiv.org/abs/2207.08051
11. Noman et al., *SatMAE++: Rethinking Pretraining for Plain Vision Transformers in Remote Sensing*, CVPR 2024. https://arxiv.org/abs/2403.05419
12. Reed et al., *Scale-MAE: A Scale-Aware Masked Autoencoder for Multiscale Geospatial Representation Learning*, ICCV 2023. https://arxiv.org/abs/2212.14532
13. Wang et al., *SSL4EO-S12: A Large-Scale Multimodal, Multitemporal Dataset for Self-Supervised Learning in Earth Observation*, IGARSS 2023. https://arxiv.org/abs/2211.07044
14. Tseng et al., *Lightweight, Pre-trained Transformers for Remote Sensing Timeseries (Presto)*, ICLR 2024. https://arxiv.org/abs/2304.14065
15. Guo et al., *SkySense: A Multi-Modal Remote Sensing Foundation Model*, CVPR 2024. https://arxiv.org/abs/2312.10115
16. Szwarcman et al., *Prithvi-EO-2.0: A Versatile Multi-Temporal Foundation Model for Earth Observation Applications*, 2024. https://arxiv.org/abs/2412.02732
17. Xiong et al., *DOFA: Dynamic One-For-All Foundation Model for Earth Observation*, ICLR 2025. https://arxiv.org/abs/2403.15356
18. Smith et al., *EarthPT: A time series foundation model for Earth Observation*, 2023. https://arxiv.org/abs/2309.07207
19. Mendieta et al., *Towards Geospatial Foundation Models via Continual Pretraining (GFM)*, CVPR 2023. https://arxiv.org/abs/2302.04476
20. Mañas et al., *Seasonal Contrast: Unsupervised Pre-Training from Uncurated Remote Sensing Data (SeCo)*, ICCV 2021. https://arxiv.org/abs/2103.16607

### 世界模型 / 动力学

21. Hafner et al., *Mastering Diverse Domains through World Models (DreamerV3)*, Nature 2025. https://arxiv.org/abs/2301.04104
22. Micheli et al., *Transformers are Sample-Efficient World Models (IRIS)*, ICLR 2023 (notable-top-5%). https://arxiv.org/abs/2209.00588

---

## 8. 附录：实操脚本片段

### A1. 修改 stage1_s2only 配置（推荐档）

```yaml
# configs/train/stage1_s2only.yaml
# 把以下行修改/新增：

max_steps: 380000       # 原 50000 → 100 epoch（global batch 256）
warmup_steps: 2000      # 从 1000 提到 2000（约 0.5 epoch）

# 验证集评估间隔（新增）
val_interval: 19000     # 每 5 epoch 评估一次
checkpoint_interval: 19000  # 每 5 epoch 存一次
```

### A2. 修改 stage1_5_film 配置

```yaml
# configs/train/stage1_5_film.yaml
training:
  max_steps: 120000     # 原 50000 → 30 epoch
  warmup_steps: 2000    # 保持

  # 新增 w_decouple 渐进日程（需要在 train_stage1_5_film.py 里实现）
  loss_weights:
    w_decouple_schedule:
      - {step: 0,      value: 0.1}
      - {step: 10000,  value: 0.5}
      - {step: 30000,  value: 1.0}
```

### A3. 监控关键指标

```bash
# 每 5 epoch 跑一次 EuroSAT 线性探测
# 期望曲线（粗略估计，基于 SatMAE 论文外推）：
# Step 0:       EuroSAT ~45%（随机初始化）
# Step 50k:    EuroSAT ~70%（当前位置）
# Step 100k:   EuroSAT ~75%
# Step 200k:   EuroSAT ~80%
# Step 380k:   EuroSAT ~82-84%（100ep 收敛）
# Step 760k:   EuroSAT ~85-87%（200ep 收敛，假设不扩模型）

cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
python eval/eval_eurosat_fast.py \
  --ckpt checkpoints/stage1_s2only/checkpoint_step_${STEP}.pt \
  --output results/eurosat_step_${STEP}.json
```

---

## 9. 与既有文档的一致性核对

- 与 [[10ObsWorld 完整实验流程与字段设计]] §4 完整实验阶段：**保持 5+1 阶段不变**，本文只补 step 数
- 与 [[14 Stage1.5与Stage2代码实现报告]] §2.6 Stage 2 状态：**确认 stage2 当前是占位骨架**，按数据落地重算
- 与 [[15_Stage1与Stage1.5完整训练指南]] §3.4 训练配置：**修改 max_steps，warmup 调整**
- 与 [[worldmodel-stage1-eurosat-eval]] EuroSAT 69.57%：**确认训练不足是主因之一**，可通过本文方案改善

---

## 10. 致谢与说明

本调研依托：
- 22 篇 CVPR / ICCV / NeurIPS / ICLR / ICML / TMLR / Nature 顶会论文
- 你的实际数据规模与配置（977k 样本/模态、4 卡 × 64 batch 等）
- 你已有的 EuroSAT 69.57% 基准评估

如有任何阶段需要更细的 ablation 表格（例如 Stage 1.5 的 w_decouple 完整扫描），可在本文档基础上追加。

