# TerraState AAAI-27 Section 4.2 修改前独立审计

**审计日期：** 2026-07-28  
**审计性质：** 只读 AAAI 主结果写作、事实与双语审计  
**审计对象：** Section 4.2 “Forecasting Performance under Temporal Shift”、
Table 1 及其与 4.1/4.3 的接口  
**权威正文：** `paper/main.tex`  
**目标 venue：** AAAI-27 Main Technical Track  

## 1. 最终结论

# READY_FOR_4_2_REVISION

当前 4.2 的事实、数字和结论方向均正确，但尚未达到成熟 AAAI 主结果段的写作质量。
权威正文只有约 30 个英文词和两句：

1. `Table 1 summarizes Q1` 只承担表格导航，没有直接回答 Q1；
2. 第二句给出 \(R^2\)、RMSE、样本量和 useful-skill 结论，但没有解释 Table 1
   的 mixed metric profile、performance trade-off 或 Q1 与 Q2/Q3 的关系。

因此，4.2 目前更像内部结果记录，而不是“结论 → 证据 → 取舍 → 科学意义”的正式
主结果段。冻结数据足以完成写作修订，不需要新实验、重算指标或修改 Table 1。

### 问题计数

| 等级 | 数量 | 说明 |
|---|---:|---|
| Critical | **0** | Q1 数字、方向与允许主张均正确 |
| Major | **3** | 主结果结构不足、mixed profile/trade-off 缺失、简版镜像过时 |
| Minor | **1** | Table 1 caption 的自包含性可更强，但不阻塞且本轮不得修改 |

当前 4.2 平均质量评分：**2.7 / 5.0**。

---

## 2. 读取基线与事实优先级

已核对：

1. `paper/main.tex` 当前 4.2、Table 1 及相邻 4.1/4.3；
2. `MANUSCRIPT_ZH_FULL.md` 对应中文；
3. `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md` 对应镜像；
4. `SECTION4_AAAI_PRE_REVISION_AUDIT_20260728.md`；
5. `SECTION4_4_1_REVISION_LOG_20260728.md`；
6. `SECTION4_FINAL_AAAI_AUDIT_20260728.md`；
7. `EXPERIMENTS_RESULTS_AAAI_WRITING_AUDIT.md`；
8. `SECTIONWISE_WRITING_ROADMAP.md`；
9. `evidence_workspace/results_ledger.json`；
10. `evidence_workspace/FINAL_EVIDENCE_AUDIT_20260728.md`；
11. 本地 AAAI 实验写作锚点；
12. `vendor/AuthorKit27/AuthorKit27/AnonymousSubmission2027.tex`；
13. 当前 `paper/main.log` 与 `paper/main.pdf`。

本轮采用作者最新确认事实：

- Q1--Q3 使用同一个最终 TerraState 模型；
- 该模型完成 40 epochs / 14,880 updates；
- 11,904/boundary80 已失效；
- 旧 ledger、旧 3.3 audit 或旧 evidence audit 中的历史身份不得恢复。

旧文件中的 11,904/boundary80 以及 Published/Local panel 叙述只作为历史状态记录，
不用于判断当前权威正文的 Q1 数字。

---

## 3. AAAI 主结果写作锚点

本轮直接检查了五篇本地正式 AAAI 论文的主结果原文。以下只提炼结构，不复制句子，
也不建议把这些写作锚点加入 TerraState 参考文献。

### 3.1 SparseWorld（AAAI 2026）

**论文：** *SparseWorld: A Flexible, Adaptive, and Efficient 4D Occupancy
World Model Powered by Sparse and Dynamic Queries*  
**本地文件：** `literature/aaai_figure_anchors/aaai26_sparseworld.pdf`  
**官方页面：** <https://ojs.aaai.org/index.php/AAAI/article/view/37347>

- Main Results 先规定相同输入历史和未来预测时域，再进入各任务结果；
- 结果段不是只写 “Table 1 compares”，而是立即给出关键趋势和少量数字；
- 明确承认 mIoU 强、IoU 没有明显优势，形成真实 mixed profile；
- 对指标差异只给保留性的可能解释，没有把指标差直接当作机制证明；
- 每个结果任务通常一个 4--8 句段落，后接定性图或下一任务；
- 可借鉴：诚实写出强项与弱项，不因主指标不是全面领先而回避表格；
- 不应照搬：其 superior、exceptional 等宣传措辞及 occupancy-specific 机制归因。

### 3.2 ReconVLA（AAAI 2026）

**论文：** *ReconVLA: Reconstructive Vision-Language-Action Model as Effective
Robot Perceiver*  
**本地文件：** `literature/experiment_writing_anchors/aaai26_reconvla.pdf`  
**官方页面：** <https://ojs.aaai.org/index.php/AAAI/article/view/38921>

- Paradigm comparison 先说明同一 baseline 上比较哪些方案，再进入 Table 1；
- 表后立即解释 EG 的改善、CG 的明显退化及其训练/信息冗余取舍；
- 不是逐格复述所有 success rates，而是挑能区分 paradigm 的趋势；
- 后续 naturally 转到 attention visualization 和 ablation；
- 一个主结论通常由一段约 5--8 句承担；
- 可借鉴：主表应服务于一个科学判断，并自然引出机制证据；
- 不应照搬：其 “superiority” 和由结果直接归因于机制的较强表达。

### 3.3 WorldAgen（AAAI 2026）

**论文：** *WorldAgen: Unified State-Action Prediction with Test-Time World
Model Training*  
**本地文件：** `literature/aaai_figure_anchors/aaai26_worldagen.pdf`  
**官方页面：** <https://ojs.aaai.org/index.php/AAAI/article/view/38925>

- Results 开头先说明覆盖 CALVIN 与 LIBERO，再按 benchmark 各用一个结果单元；
- 每个结果单元从 Table 导航迅速过渡到主要趋势，而不是罗列每一行；
- 主 benchmark 后转向 world-modeling ablation，使 performance 与 mechanism
  各承担不同职责；
- data-volume ablation 明确报告先改善、后轻微回落和 diminishing returns；
- 可借鉴：mixed outcome 不削弱论文，反而使结论边界更可信；
- 不应照搬：跨任务 consistent gains、robustness 等超出 TerraState Q1 的表述。

### 3.4 Drive-OccWorld（AAAI 2025）

**论文：** *Driving in the Occupancy World: Vision-Centric 4D Occupancy
Forecasting and Planning via World Models for Autonomous Driving*  
**本地文件：** `literature/aaai_figure_anchors/aaai25_drive_occworld.pdf`  
**官方页面：** <https://ojs.aaai.org/index.php/AAAI/article/view/33010>

- 主结果节首句先声明验证 forecasting quality 和 controllability 两类能力；
- 随后按 inflated forecasting、fine-grained forecasting 和 controllability
  分别解释；
- 每段选择一两个关键差值和对应含义，不重复整表；
- 定量主结果之后再连接 qualitative visualization 或 planning；
- 可借鉴：Q1、Q2/Q3 应分层，Table 1 不必承担内部状态性质；
- 不应照搬：由 benchmark 提升直接推出世界知识或安全性的强机制归因。

### 3.5 CADYT（AAAI 2026）

**论文：** *Causal Structure Learning for Dynamical Systems with Theoretical
Score Analysis*  
**本地文件：** `literature/experiment_writing_anchors/aaai26_cadyt.pdf`  
**官方页面：** <https://ojs.aaai.org/index.php/AAAI/article/view/40999>

- Results 第一段先说明 sanity check 的科学功能，再报告 false-positive 结果；
- 后续按 NSHD、F1、AUPRC 的不同职责解释，而不是把多指标压成一个“最好”；
- 明确指出所有方法在 irregular sampling 下均有退化，同时限定相对结论；
- 每个 metric/result 单元约 3--6 句；
- 可借鉴：多指标应解释各自回答什么，mixed profile 应显式呈现；
- 不应照搬：causal discovery、structure recovery 或理论保证语言。

### 3.6 共同规律

五篇锚点共同显示：

1. 主结果第一句应回答问题或说明当前验证对象，而不只是 “Table X shows”；
2. Table 导航是句中辅助，不是段落结论；
3. 一段通常只选 1--3 个决策性数字；
4. 指标不统一领先时，应明确 mixed profile 和 trade-off；
5. 正文解释结果含义，表格保存完整 aggregate；
6. 机制或内部属性应由后续专门实验承担；
7. 一个 4--6 句、约 100--130 词的段落足以完成 TerraState Q1；
8. 诚实描述不利指标比回避主表更成熟，但无需为结果写长篇辩护。

---

## 4. 当前 4.2 反向提纲

当前权威正文：

> `Table 1 summarizes Q1.`
>
> TerraState reports \(R^2=0.56935\), RMSE \(=0.15059\), \(n=1{,}904\)，
> 并据此称其在 temporal shift 下保留 useful predictive skill。

| 句子 | 当前职责 | 判断 |
|---|---|---|
| 句 1 | 表格导航 | **不足**：未直接回答 Q1 |
| 句 2 | 两个指标、样本量和限定结论 | **事实正确但解释不足** |

当前没有：

- Table 1 的代表性比较；
- \(\mathrm{RMSE}_{25}\)、NSE 或 bias 所呈现的 mixed profile；
- 哪个维度较强、哪个维度存在差距；
- “保留 utility、但不统一领先”的 trade-off；
- Q1 只是预测前提、Q2/Q3 才检验内部状态的过渡。

### 4.1 逐项回答

| 审计问题 | 结论 |
|---|---|
| 首句是否只有导航 | **是** |
| 当前段落是否过短 | **是**；约 30 个英文词 |
| 是否缺少代表性比较 | **是** |
| 是否缺少 mixed metric profile | **是** |
| 是否缺少 trade-off | **是** |
| 是否缺少 Q1→Q2/Q3 接口 | **是** |
| useful predictive skill 是否有证据 | **是**；正 \(R^2\)、有限 RMSE、完整 OOD-t 样本支持限定表述 |
| 是否应直接使用 `competitive` | **不建议** |
| 是否应改用精确数字描述 | **是** |
| 是否有回避主表的观感风险 | **有**；只提两个指标而不解释其余列 |
| 是否应长篇为 Q1 辩护 | **否**；一个紧凑段落即可 |
| 是否像成熟 AAAI 主结果段 | **尚未达到** |

---

## 5. Q1 冻结事实核对

本轮不重算、不重新选择，只核对作者确认值与当前显示。

| 项目 | 冻结精确值 | Table 1 / 正文显示 | 判定 |
|---|---:|---:|---|
| OOD-t minicubes | 1,904 | 1,904 | **PASS** |
| \(R^2\) | 0.5693493611664086 | 0.569 / 0.56935 | **PASS** |
| RMSE | 0.1505941190915099 | 0.151 / 0.15059 | **PASS** |
| NSE | -0.09865622945212116 | -0.099 | **PASS** |
| \(|\mathrm{Bias}|\) | 0.10082936645631536 | 0.101 | **PASS** |
| \(\mathrm{RMSE}_{25}\) | 0.08204982450297288 | 0.082 | **PASS** |
| 参数量 | 7.18M | 7.18M | **PASS** |

当前 4.2 的 `useful predictive skill under temporal distribution shift` 是限定、
可支持的 Q1 结论。它不等于 SOTA、non-inferiority 或 world-model proof。

---

## 6. Table 1 mixed metric profile

### 6.1 TerraState 的实际性能轮廓

| 维度 | 表中位置与含义 | 可安全解释 |
|---|---|---|
| \(R^2=0.569\) | 高于 Persistence、Previous year 和 Earthformer；低于若干其他行 | 有正向解释力，但不是领先指标 |
| RMSE \(=0.151\) | 位于多种 learned forecaster 的 0.150--0.160 显示范围内 | 总体误差保持在代表性学习方法的相同数量级 |
| NSE \(=-0.099\) | 优于若干负 NSE 行，但低于 PredRNN、SimVP、Contextformer | 明确不是统一领先 |
| \(|\mathrm{Bias}|=0.101\) | 介于表中 0.100 与 0.110 的相邻显示值之间 | 偏差不异常，但不是主卖点 |
| \(\mathrm{RMSE}_{25}=0.082\) | 低于除 0.080 行之外的其他显示值 | TerraState 最强的相对维度是短时域误差 |
| 7.18M parameters | 与若干中等规模方法处于相近量级，远小于 60.6M 行 | 只作规模背景，不推出效率优势 |

### 6.2 应如何叙述

推荐将 mixed profile 明确写成：

- TerraState 在完整 OOD-t 上保留 useful skill；
- RMSE 处于代表性 learned forecasters 的相同数值区间；
- \(\mathrm{RMSE}_{25}=0.082\) 显示较低的短时域误差；
- \(R^2\) 与 NSE 不领先，因此该表不是统一性能优势；
- 不能把这一差距或强项归因于显式状态结构，因为 Table 1 没有隔离该机制。

### 6.3 不建议的叙述

- 只提 \(R^2\)/RMSE 而不提 mixed profile；
- 把 \(\mathrm{RMSE}_{25}\) 写成全面 superior；
- 把 RMSE 0.151 与 0.150 写成 statistically equivalent；
- 把 \(R^2\)/NSE 差距解释为世界模型结构的代价；
- 用 Q2/Q3 的成功反向掩盖 Q1 的非领先指标。

---

## 7. 允许与禁止的最强表述

| 候选表述 | 支持级别 | 审计结论 |
|---|---|---|
| `retains useful forecasting skill` | **SUPPORTED** | 推荐；须限定于 GreenEarthNet OOD-t/temporal shift |
| `preserves practical forecast utility` | **AMBIGUOUS** | `practical` 没有操作阈值，建议不用 |
| `exhibits a mixed metric profile` | **SUPPORTED** | 推荐作为分析框架，不必逐字写进正文 |
| `achieves low short-horizon error` | **SUPPORTED_WITH_SCOPE** | 可用；最好同时给 \(\mathrm{RMSE}_{25}=0.082\) |
| `Q1 establishes the forecasting prerequisite for state diagnostics` | **SUPPORTED** | 推荐，准确连接 Q2/Q3 |
| `the internal claims are evaluated separately in Q2 and Q3` | **SUPPORTED** | 推荐作为段尾接口 |
| `competitive` | **PARTIALLY SUPPORTED / 不推荐裸用** | 容易暗示综合排名；用精确指标轮廓替代 |
| `competitive short-horizon error` | **SUPPORTED_WITH_SCOPE but unnecessary** | 即使加限定，也不如直接写 0.082 清楚 |
| `nearly matches Contextformer` | **UNSUPPORTED** | 无等价检验，禁止 |
| `only a small accuracy cost` | **UNSUPPORTED** | 没有预设 cost 标准，禁止 |
| `uniformly superior` / `outperforms all` | **UNSUPPORTED** | 与 Table 1 直接冲突 |
| `non-inferior` / `statistically equivalent` | **UNSUPPORTED** | 无相应检验 |
| `Table 1 proves a world model` | **UNSUPPORTED** | Q1 只建立预测前提 |

### 推荐的最强 Q1 表述

> **TerraState retains useful forecasting skill under temporal shift; Q1
> establishes the forecasting prerequisite for, but not the internal-state
> evidence supplied by, Q2 and Q3.**

这一表述充分利用 Q1，又不将 Table 1 写成排名胜利或世界模型证明。

---

## 8. 推荐信息槽

不直接撰写最终英文；后续 4.2 可按以下五个句子职责组织。

### 槽 1：结论先行

- 直接回答 Q1；
- 结论限定为 temporal-shift OOD-t；
- 使用 `retains useful forecasting skill`；
- 不以 `Table 1 summarizes...` 开场。

### 槽 2：核心结果

- \(n=1{,}904\)；
- \(R^2=0.56935\)；
- RMSE \(=0.15059\)；
- Table 1 作为括号式或句末证据入口。

### 槽 3：代表性强项

- \(\mathrm{RMSE}_{25}=0.082\)；
- 将其解释为较低的前 25 天误差；
- 可说明它是 TerraState 表中最强的相对维度；
- 不必搬运所有 baseline 数字。

### 槽 4：mixed profile 与 trade-off

- RMSE 与多种 learned forecaster 处于相同显示范围；
- 同时明确 \(R^2\)/NSE 不领先；
- 结论是“保留 forecast utility，但不是统一 metric leadership”；
- 不为差距寻找未经隔离的机制原因。

### 槽 5：世界模型接口

- Q1 防止论文只讨论不可用的内部状态；
- Q1 只是 forecasting prerequisite；
- 状态贡献和天气响应分别由 Q2/Q3 同模型干预检验；
- 不提前复述 Q2/Q3 数字。

### 8.1 是否采用用户建议的六槽结构

用户提出的“结论 → 核心数字 → 代表性比较 → mixed profile → trade-off →
世界模型接口”逻辑正确。为避免一段过长，建议把“代表性比较、mixed profile、
trade-off”合并为两个句子，而不是各写一段。

---

## 9. 推荐段落数与长度

**推荐：一个段落，5 句，约 100--130 个英文词。**

原因：

- Q1 是必要前提，不是论文的定义性贡献，不宜扩成两个结果段；
- 一个段落足以完成 conclusion、numbers、mixed profile、trade-off 和 bridge；
- 低于约 80 词仍可能显得回避 Table 1；
- 超过约 150 词容易变成对非领先表现的长篇辩护；
- Table 1 已保存所有 exact aggregate，正文无须逐行复述。

建议句子分配：

1. 结论；
2. \(n/R^2/\mathrm{RMSE}\)；
3. \(\mathrm{RMSE}_{25}\) 强项；
4. \(R^2/NSE\) 非领先的 mixed profile；
5. Q1→Q2/Q3 过渡。

---

## 10. Table 1 事实与格式审计

### 10.1 科学表达

| 检查项 | 结果 |
|---|---|
| 数值与作者冻结表一致 | **PASS** |
| 所有 metric 方向 | **PASS**；headers 给出 ↑/↓ |
| 性能指标小数位 | **PASS**；统一三位 |
| 参数量 | **PASS**；0、M 单位清楚 |
| TerraState 强调方式 | **PASS**；仅方法名加粗，没有逐列伪造最佳 |
| Table 1 唯一职责 | **PASS**；只回答 Q1 forecasting profile |
| caption 指明 temporal distribution shift | **PASS** |
| caption 定义 RMSE25 | **PASS** |
| caption 给出 lower-is-better 指标 | **PASS** |

### 10.2 AAAI-27 格式

| 检查项 | 结果 |
|---|---|
| `tabular → caption → label` | **PASS** |
| caption 位于表格下方 | **PASS** |
| caption 约 10pt Roman | **PASS**；PDF 约 9.96pt |
| body 不小于 9pt | **PASS**；PDF 约 8.97pt nominal 9pt |
| `booktabs` | **PASS** |
| 无竖线 | **PASS** |
| 无 `resizebox/scalebox` | **PASS** |
| 无 negative spacing | **PASS** |
| 裁切、越栏、margin intrusion | **PASS** |
| label/reference | **PASS** |

Table 1 当前 tabular SHA-256：
`e138d52fbfb8c374a48cd6342d8cc5b53a4f95773e228805092b4501dedbdf36`。

caption SHA-256：
`2f0f82661d756fd2673eb02fba825f3e5eaadefdb09a0ad60987b3ab66adb832`。

### 10.3 Caption 自包含性

caption 已说明 GreenEarthNet、temporal distribution shift、
\(\mathrm{RMSE}_{25}\) 定义和误差方向，足以避免误读。它没有直接写 `OOD-t` 和
\(n=1{,}904\)，因此若脱离正文单独阅读，自包含性仍可更强。

该项只记为 **Minor**：

- 4.1 和 4.2 已明确 OOD-t 与样本量；
- 当前 caption 科学含义不错误；
- 用户冻结 Table 1 数值、结构和 caption 文案，本轮不修改；
- 后续 4.2 只需在正文保留 \(n=1{,}904\)，不必借机改表。

### 10.4 Table 与正文分工

目标分工应为：

- **Table 1：** 所有方法、所有指标、参数量和显示精度；
- **4.2：** Q1 结论、最少数字、mixed profile、trade-off 和 Q2/Q3 接口。

当前 Table 1 已完成其职责；4.2 尚未完成后半部分。

**Table 1 总判定：PASS（附一个非阻塞自包含性 Minor）。**

---

## 11. 世界模型主线检查

修改后的 4.2 应保持：

1. TerraState 先具有可用的 EO 预测能力；
2. Q1 排除“内部表示可讨论但预测本身不可用”的退化情形；
3. 世界模型身份不由 Table 1 排名决定；
4. Q2 承担 load-bearing state contribution 的主证据；
5. Q3 承担 weather-response fidelity 的证据；
6. 4.2 不复述 Q2/Q3 数字，也不把后续干预用于辩护 Q1。

最佳叙事不是“性能一般，但我们不是刷榜”，而是：

> 先正面陈述 Q1 已通过，再透明呈现指标轮廓，最后说明论文接下来检验的性质与
> Table 1 不同。

这能同时避免宣传式和防御式语气。

---

## 12. 中英文与镜像审计

### 12.1 权威英文与完整中文

`paper/main.tex` 与 `MANUSCRIPT_ZH_FULL.md` 当前一致：

- 都先作 Table 1 导航；
- 都报告 \(n=1{,}904\)、\(R^2=0.56935\)、RMSE \(=0.15059\)；
- 英文 `useful predictive skill` 对应中文“保留有效预测能力”；
- 中文没有增强为领先、最优或 competitive。

**权威英文 ↔ 完整中文：PASS。**

### 12.2 两个简版镜像

`MANUSCRIPT.md` 与 `MANUSCRIPT_ZH.md` 的 4.2 仍使用过时版本：

- `published panel provides context` / “公开面板只提供背景”；
- `local OOD-t` / “本地 OOD-t”；
- `limited claim` / “限定主张”；
- 相邻简版 Table 1 仍是旧的 Published/Reported/Local panel。

这些内容与当前 `main.tex` 和 `MANUSCRIPT_ZH_FULL.md` 的统一 Table 1 不一致，
也与本轮禁止恢复 Published/Local/Source 标签的要求冲突。

该问题不改变 Q1 数字，但会形成第二套实验叙述，判为 **Major mirror-sync issue**。
后续 4.2 修改时：

- 以 `main.tex` 为唯一英文事实源；
- 同步 `MANUSCRIPT_ZH_FULL.md`；
- 将两个简版镜像的 4.2 prose 同步到同一结构与强度；
- 不从旧镜像复制 Published/Local/strict-panel 语言；
- 简版 Table 1 的历史状态应由镜像同步任务处理，不得反向修改权威 Table 1。

### 12.3 后续 mixed profile 的中文写法

中文可以自然表达为：

- “在时间偏移下保留有效预测能力”；
- “指标呈现非统一领先的混合轮廓”；
- “前 25 天误差较低”；
- “整体 \(R^2\) 与 NSE 并非表中最佳”；
- “Q1 建立预测前提，Q2/Q3 分别检验状态贡献与天气响应”。

应避免：

- “竞争性最优”；
- “几乎不损失精度”；
- “仅以很小代价换来世界模型能力”；
- “虽然性能一般，但是……”；
- 长篇解释为什么没有领先。

---

## 13. 质量评分

评分：1=明显不达标；3=基本可用；4=投稿成熟；5=高度成熟。

| 维度 | 当前分数 | 判断 |
|---|---:|---|
| AAAI 主结果结构 | **2.5** | 只有导航和单句结果 |
| 首句力度 | **2.0** | 未回答 Q1 |
| 结果解释深度 | **2.0** | 没有 profile、trade-off 或意义解释 |
| 数字选择 | **3.5** | 两个主数字正确且克制，但漏掉最有解释力的 RMSE25 |
| mixed profile 表达 | **1.0** | 完全缺失 |
| trade-off 表达 | **1.5** | 完全缺失，但不应写成辩解 |
| 世界模型主线接口 | **2.5** | 4.1 已铺垫，4.2 自身未承接 |
| claim--evidence 对齐 | **5.0** | useful-skill 结论严格受证据支持 |
| 英文自然度 | **4.5** | 句子自然，但功能不足 |
| 简洁度 | **3.0** | 短而不完整，不等于成熟简洁 |
| Table 1 与正文分工 | **2.5** | Table 完整，正文未承担解释职责 |
| 中英文一致性 | **2.5** | 权威双语一致；两个简版镜像过时 |
| **平均分** | **2.7 / 5.0** | **需要写作修订** |

---

## 14. Critical / Major / Minor

### Critical（0）

未发现：

- Q1 数字错误；
- sample size 错误；
- useful-skill 结论越界；
- SOTA、non-inferiority 或 world-model proof；
- Table 1 数值或格式破坏。

### Major（3）

#### M1：主结果段结构不完整

- **位置：** `paper/main.tex` 4.2 首句及整段；
- **问题：** 以 Table 导航开场，全文约 30 词，没有形成结论先行的 AAAI 结果段；
- **审稿风险：** Q1 看起来像尚未写完的结果接口；
- **修复类型：** writing-fixable；
- **最小动作：** 改为一个 5 句、100--130 词的结果段。

#### M2：选择性报告，缺少 mixed profile 与 trade-off

- **位置：** 4.2 第二句之后；
- **问题：** 只报告 \(R^2\)/RMSE，不解释 \(\mathrm{RMSE}_{25}\) 强项及
  \(R^2\)/NSE 非领先；
- **审稿风险：** 容易被解读为回避 Table 1 的不利列；
- **修复类型：** analysis-fixable with existing table；
- **最小动作：** 加两句，分别说明短时域强项和非统一领先的 profile，不归因于机制。

#### M3：简版 Markdown 镜像过时

- **位置：** `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md` 的 4.2；
- **问题：** 仍引用 Published/Local 双 panel，与当前权威 Table 1 和完整中文不一致；
- **审稿风险：** 后续整合时可能恢复已删除的来源分组和防御性表述；
- **修复类型：** writing/mirror synchronization；
- **最小动作：** 后续只同步 4.2 prose；禁止把旧 panel 语言复制回正文。

### Minor（1）

#### m1：Table 1 caption 未直接给 OOD-t 名称和样本量

- **位置：** Table 1 caption；
- **问题：** 脱离正文时，自包含性可更强；
- **影响：** 4.1/4.2 已补全，不影响正确理解；
- **动作：** 本轮及后续 4.2 修订均不修改 caption；正文保留 \(n=1{,}904\) 即可。

---

## 15. 精确、最小的后续修改建议

### Priority 1

- **Issue：** 第一词功能错误；
- **Required edit：** 用 Q1 结论开场，把 Table 引用移到核心数字句；
- **Where：** 4.2 第一句；
- **Evidence needed：** 无新证据；
- **Status：** writing-fixable。

### Priority 2

- **Issue：** mixed profile 缺失；
- **Required edit：** 只增加两项解释：
  1. \(\mathrm{RMSE}_{25}=0.082\) 是低短时域误差；
  2. \(R^2\)/NSE 不领先；
- **Where：** 核心数字句之后；
- **Evidence needed：** 仅使用现有 Table 1；
- **Status：** analysis-fixable with frozen results。

### Priority 3

- **Issue：** Q1 与核心世界模型证据脱节；
- **Required edit：** 段尾用一句说明 Q1 是 forecasting prerequisite，Q2/Q3
  分别检验 state contribution 与 weather response；
- **Where：** 4.2 最后一句；
- **Evidence needed：** 无；
- **Status：** writing-fixable。

### Priority 4

- **Issue：** 简版镜像过时；
- **Required edit：** 英文权威稿确定后，同步三个 Markdown 中的 4.2；不得恢复
  Published/Local/Source；
- **Where：** 4.2 对应镜像；
- **Evidence needed：** 无；
- **Status：** mirror synchronization。

### 不需要做

- 不改 Q1 数字；
- 不改 Table 1；
- 不新增 baseline 或实验；
- 不讨论 baseline 来源、seed/run 数；
- 不修改 4.1、4.3、4.4；
- 不恢复 11,904/boundary80；
- 不使用 `competitive`、SOTA 或等价性语言。

---

## 16. 最终状态

# READY_FOR_4_2_REVISION

理由：

1. Critical = 0；
2. Q1 冻结事实和 Table 1 均正确；
3. 当前问题全部可用已有 Table 1 通过写作和镜像同步解决；
4. 不需要新实验、统计检验或证据变更；
5. 推荐修订范围可严格限制在一个 100--130 词英文段落及对应中文/Markdown 镜像；
6. 修订后应重新检查是否仍出现裸 `competitive`、过度辩护或旧 Published/Local
   panel 语言。
