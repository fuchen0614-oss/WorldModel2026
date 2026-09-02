# A06 · 主表 Table 1：当前数值、来源与待办

> 建档 2026-08-31。本文只做一件事：把**外部基线**与**我们自己的结果**放在同一张表里核对，
> 并标清每个数字的来源与身份。此前这张合并表**不存在于任何文件中**——基线在归档手稿
> （`archive/01_MANUSCRIPT/`），C1 的数字在 [A04 §18](./A04_TerraState_CandidateC_实现训练与实验总账.md)，
> 两者从未合并。
>
> **协议**：GreenEarthNet OOD-t（`ood-t_chopped`，1,904 minicubes），官方 LC-balanced scorer，bs=1。

---

## 1. 合并表（按 A01 §3.1 要求分栏）

### 1.1 外部基线 —— **文献数字，非同协议自跑**

来源：Vitus Benson et al., *Multi-modal Learning for Geospatial Vegetation Forecasting*,
CVPR 2024, Table 2。论文 SHA-256 `61625380…`，补充材料 `88602702…`（见
`archive/04_RESULTS_EVIDENCE/historical_release_provenance/archived_pre_final_current/PUBLIC_BASELINES.md`）。

| Method | R²↑ | RMSE↓ | NSE↑ | \|Bias\|↓ | RMSE25↓ | #Params | 种子 |
|---|---:|---:|---:|---:|---:|---:|---|
| Persistence | 0.000 | 0.230 | −1.280 | 0.170 | 0.090 | 0 | 确定性 |
| Previous year | 0.560 | 0.200 | −0.400 | 0.140 | 0.180 | 0 | 确定性 |
| Climatology | 0.580 | 0.180 | −0.340 | 0.130 | 0.160 | 0 | 确定性 |
| ConvLSTM | 0.580 | 0.160 | −0.130 | 0.110 | 0.110 | 1.0M | 3 seeds 均值 |
| Earthformer | 0.520 | 0.160 | −0.130 | 0.100 | 0.090 | 60.6M | **1 seed** |
| PredRNN | 0.620 | 0.150 | 0.030 | 0.100 | 0.100 | 1.4M | 3 seeds 均值 |
| SimVP | 0.600 | 0.150 | 0.030 | 0.090 | 0.100 | 6.6M | 3 seeds 均值 |
| Contextformer | 0.620 | 0.140 | 0.090 | 0.090 | 0.080 | 6.1M | 3 seeds 均值 |

### 1.2 本项目 —— **自跑，同一评测器与 manifest**

| Method | R²↑ | RMSE↓ | NSE↑ | \|Bias\|↓ | RMSE25↓ | #Params | 种子 |
|---|---:|---:|---:|---:|---:|---:|---|
| TerraState-V2 `boundary80` / 11,904 **（手稿 Table 1 当前用的就是这一行）** | 0.569349 | 0.150594 | −0.098656 | 0.100829 | 0.082050 | 7.18M | 1 seed |
| TerraState-V2 @14,880（E0 复评的 canonical checkpoint） | 0.569278 | 0.150627 | −0.099753 | 0.100810 | STATUS.md 未登记 | 7.18M | 1 seed |
| **TerraState-C1（新，本表建议替换行）** | **0.572604** | **0.150941** | **−0.106477** | **0.101345** | **0.082394** | **7.18M** | 1 seed |

> ⚠️ **两个 V2 checkpoint 不要混。** 手稿正文写的 `R²=0.56935 / RMSE=0.15059` 与表行的
> `NSE=-0.099` 都对应 **boundary80 / 11,904**，不是 14,880。下面 §3 的对照一律以 boundary80 为基准。

论文三位小数呈现：

| Method | R²↑ | RMSE↓ | NSE↑ | \|Bias\|↓ | RMSE25↓ | #Params |
|---|---:|---:|---:|---:|---:|---:|
| TerraState-V2（boundary80，手稿现行） | 0.569 | 0.151 | −0.099 | 0.101 | 0.082 | 7.18M |
| **TerraState-C1** | **0.573** | **0.151** | **−0.106** | **0.101** | **0.082** | **7.18M** |

---

## 2. 三条必须随表披露的事实

### 2.1 基线是文献数字，不是同协议自跑

A01 §3.1：「自跑与文献数字分栏；无法同协议复现的文献数字只能单列为 reference，
不与自跑结果混成同一排名」。当前手稿把两者混在一张表里排名，**这是 Table 1 最大的可攻击点**。
E1 的核心工作就是把 Contextformer 等在同一 manifest / mask / scorer / 时域下重跑。

### 2.2 种子数不一致

基线中 ConvLSTM / PredRNN / SimVP / Contextformer 是 3 seeds 均值，Earthformer 是 1 seed，
非 ML 方法确定性；**TerraState 两行都只有 1 seed**。既不能说"公开值都是单种子"，
也不能说"都是三种子均值"。多 seed 是 TerraState 侧公认的缺口。

### 2.3 R² 与 RMSE 在本表上给出**不同排名**

```
Climatology:     R² 0.580   RMSE 0.180   RMSE25 0.160
TerraState-C1:   R² 0.573   RMSE 0.151   RMSE25 0.082
```

按 R²，气候均值优于我们；按 RMSE 与 RMSE25，我们大幅优于它（RMSE25 好一倍）。
原因是官方 R² 为 **LC-balanced 加权平均**而 RMSE 为 **pooled** ——
与 A04 §19 记录的 `G_abs` R² 腿问题属同一类聚合口径现象。

手稿正文已如实处理了这一点（`MANUSCRIPT.md:251`）：
「The overall profile is mixed: RMSE lies within the numerical range of several learned
forecasters, whereas its R² and NSE are not the largest values in the table」，
并以 RMSE25 作为最有利的比较维度。**这个处理是诚实的，建议保留。**

---

## 3. V2 → C1 的逐指标变化

基准为 **boundary80 / 11,904**（手稿现行行）：

| 指标 | V2 boundary80 | C1 | 变化 |
|---|---:|---:|---|
| R² ↑ | 0.569349 | 0.572604 | **+0.003255 更好** |
| RMSE ↓ | 0.150594 | 0.150941 | +0.000347 略差 |
| NSE ↑ | −0.098656 | −0.106477 | −0.007821 略差 |
| \|bias\| ↓ | 0.100829 | 0.101345 | +0.000516 略差 |
| RMSE25 ↓ | 0.082050 | 0.082394 | +0.000344 略差 |

**5 项中 1 好 4 差。** 唯一安全的表述是「C1 与 V2 事实预测持平」，
不得写「C1 更准」——没有配对显著性检验，且指标方向不一致。

逐土地覆盖的 R² 则是**四类一致提升**（描述性观察，未经检验）：

| 地类 | V2 R² | C1 R² | Δ |
|---|---:|---:|---:|
| forest | 0.5521 | 0.5528 | +0.0007 |
| shrub | 0.5562 | 0.5577 | +0.0015 |
| grass | 0.5845 | 0.5882 | +0.0037 |
| crop | 0.5847 | 0.5917 | +0.0070 |

pooled RMSE 则是混合的（shrub +0.0018 拖累），这正是 §2.3 那条口径差异的来源。

---

## 4. 数据来源

| 行 | 来源 |
|---|---|
| 外部基线 | CVPR 2024 Table 2（SHA 已冻结），经 `PUBLIC_BASELINES.md` 审计 |
| TerraState-V2 boundary80 | `archive/04_RESULTS_EVIDENCE/historical_release_provenance/oodt_q1q2_state_contract_exclusive.json` |
| TerraState-V2 @14,880 | `STATUS.md` 头条指标表（由 E0 v3 工件机械生成；未登记 RMSE25） |
| TerraState-C1 | `evaluations/candidate_c_q1q2q3_20260830T072737Z/oodt/state_contract_exclusive.json`（SHA `936a91cd40369c93…`，manifest `a2f66cde7efc2929…`，checkpoint `474f94340763e9ba…`） |

---

## 5. 待办

- [x] **E1：基线同协议重跑**（§2.1）。**已完成**，结果见
      [A08](./A08_E1主表_同协议重跑结果.md)：四个学习型基线各 3 seeds × 4 split（48/48）
      + Persistence + TerraState-C1，全部同一 manifest / mask / scorer。
      关键发现：同协议下四个基线的 R² 一律比文献低 0.028–0.038、NSE 低 0.06–0.10，
      而 RMSE / bias / RMSE25 贴合——是 LC-balanced vs pooled 的聚合口径差，不是复现失败。
- [ ] ~~E1 原待办~~（保留原文供追溯）：这是 Table 1 站得住的前提。
      **家底已盘清，见 [A07](./A07_E1基线家底_权重代码数据在哪怎么取.md)**：四个基线的官方权重
      （3 seeds 齐）、官方配置、非 ML 基线实现、四个 chopped split **全部就绪**；
      唯一待做的是把 ConvLSTM / PredRNN / SimVP 三个 `nn.Module` 移植到现代 torch
      （Contextformer 已有成功模板）。纯推理，不需要 GPU。
- [x] **四 split 覆盖**。**已完成** —— IID / OOD-t / OOD-s / OOD-st 四列齐全。
      C1 在四个 split 上按 R² 一律排第 3/5（PredRNN > Contextformer > **C1** > 另两个），
      排位高度一致，不是单一 split 的偶然。
- [ ] **多 seed**（§2.2）。至少 C1 补 1–2 个种子。
- [ ] **`outperform climatology` 一列缺失**。源表有此列，我们的评测器不产出该指标；
      要么补实现，要么在表中明确标 `n.a.` 并说明原因。
- [ ] **决定手稿是否换行**。若换成 C1，需同步更新至少三处：
      `MANUSCRIPT.md:245`（表行）、`:251`（正文 `0.56935 / 0.15059`）、`:19`（摘要 `R²=0.569`），
      以及 `archive/01_MANUSCRIPT/paper/main.tex` 中的对应位置。**整行一起换，不能只改 R²。**
