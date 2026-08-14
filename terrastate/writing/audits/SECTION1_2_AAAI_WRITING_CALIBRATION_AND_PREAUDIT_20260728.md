# TerraState Section 1–2 AAAI 写作校准与修改前独立审计

**审计日期：** 2026-07-28  
**审计性质：** 只读调研与修改前审计  
**正文权威版本：** `paper/main.tex`；`MANUSCRIPT_ZH_FULL.md` 为当前完整中文对照  
**总体写作判定：** Section 1 = **REVISE**；Section 2 = **REVISE**  
**任务完成状态：** `CALIBRATION_COMPLETE_READY_FOR_SECTION1_REVISION`

## 1. 最终结论

当前 Introduction 已经具备成熟论文开场的完整骨架：任务背景、输出精度的证据缺口、预测状态视角、TerraState 概览、结果预告和三项贡献都已出现，且顺序基本正确。它“差点意思”的主要原因不是缺段，而是三个定位动作尚未完全分开：

1. 第一段把本文选择的 world-modeling 视角写成了 EO forecasting 的必然定义；
2. 第三段把 TerraState 的具体干预判据写成了“预测状态在经验上有意义”的定义条件，容易形成“先自定标准、再宣布满足”的印象；
3. 方法和证据概览使用较多 `Q1/Q2/Q3`、`removable`、`frozen controls` 和完整 20 步协议语言，呈现出审计/协议文档感，而不是先建立科学问题、再自然给出证据的 AAAI Introduction。

当前 Related Work 的三组顺序是合理的：任务与预测方法 → 最接近的 EO world models → 预测状态与潜动力学基础。重要近邻的技术定位总体准确，也没有把预印本误写成正式录用论文。但是第一段仍偏模型名单，第三段尾部的 structured-operator/group-action 工作离当前 Q1–Q3 主线较远，并会重新唤起已排除的 composition/Q4 方向。两个精简镜像 `MANUSCRIPT.md` 和 `MANUSCRIPT_ZH.md` 还保留旧的 endpoint Q3 叙事与 composition 探索句，已与 `main.tex` 和 `MANUSCRIPT_ZH_FULL.md` 不一致。

本轮没有发现阻塞性引文缺口。建议先修 Section 1，再按其最终定位压缩 Section 2；本轮不直接修改任何正文。

## 2. 审计范围、输入与版本状态

### 2.1 已读取输入

- `paper/main.tex`
- `MANUSCRIPT_ZH_FULL.md`
- `MANUSCRIPT.md`
- `MANUSCRIPT_ZH.md`
- `METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md`
- `SECTION4_4_1_FINAL_AUDIT_20260728.md`
- `SECTION4_4_2_FINAL_AUDIT_20260728.md`
- `SECTION4_4_3_FINAL_AUDIT_20260728.md`
- `SECTION4_4_4_REVISION_LOG_20260728.md`
- `SECTION4_4_4_FINAL_AUDIT_20260728.md`（在本审计进行期间由并行会话生成，交付前已补读）
- `RESULTS_CLAIM_EVIDENCE_AUDIT.md`
- `paper/references.bib`
- `paper/main.pdf`

`METHOD_SECTION3_GLOBAL_FINAL_AUDIT_20260728.md` 在审计时不存在；该项按“如存在”处理，不构成阻塞。方法事实由当前 `main.tex`、canonical spec 和现有 Section 4 审计交叉核对。

### 2.2 关键输入哈希

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `3fa2fe271fcc77f7e3cd9c77f095408ed9e514106cc952ca62e09e6cb913a51f` |
| `MANUSCRIPT_ZH_FULL.md` | `ed606a806110d4c85a5d3243a052d3f3f4238d40b34588e6d14c19f9ef906ee8` |
| `MANUSCRIPT.md` | `3e59a8f05f5e320cfe01f6c48c8bb2f646fb54e74582de918feb9a62548afac6` |
| `MANUSCRIPT_ZH.md` | `4867fad7c8d4da43be3ce468e2a8e8458a96328cfd74c2d3023baef0ce200e33` |
| `METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md` | `ff2c745489ccfda5019a84f001d65403426b2c84c82d4d4a4f1f10cbdd4d1365` |
| `SECTION4_4_4_FINAL_AUDIT_20260728.md` | `d3f9486cf0f3efcc845dd757646d92a6964390069a6f979dc964aef6789ff793` |
| `RESULTS_CLAIM_EVIDENCE_AUDIT.md` | `e8f4f4dcfc4055fb79fc76b59cd6b338222118c6c2ed23115899f6add65b5b0f` |
| `paper/references.bib` | `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659` |
| `paper/main.pdf` | `e27142265a6cc5944e7da086d37e72dfeebc8c6ee335445758422ee806ef33d0` |

上述为交付前复核哈希。审计期间，并行 Section 4.4/Table 1 会话更新了若干文件的其他区段并重新编译 PDF；复核确认 `main.tex` 的 Section 1–2 文字仍与本报告逐段审计的版本一致。当前 `main.tex` 的 Section 1–2 片段 SHA-256 为 `6e428acf3a5816bc49a197b8c28628319eeaa0690e753efecb3ac5e8762f8624`。

### 2.3 当前权威关系

- `main.tex` 与 `MANUSCRIPT_ZH_FULL.md` 的 Section 1–2 主张强度和 Q3 完整窗口叙事一致。
- `MANUSCRIPT.md` 与 `MANUSCRIPT_ZH.md` 是较旧精简镜像：仍使用 `endpoint`、`correct predictive direction`，并保留 composition 为探索方向的句子。
- 当前 PDF 中 Section 1–2 与 `main.tex` 一致；Figure 1 在源码中位于第一段之后，正文首次解释性引用在方法概览段，阅读时机自然。
- 并行会话已完成 4.4 终审，`SECTION4_4_4_FINAL_AUDIT_20260728.md` 的结论为 `SECTION4_4_4_FROZEN`。该结论确认 Q3 的 84 对、response statistic、完整窗口 fidelity、方向和区间均与冻结 JSON 一致；本报告据此使用 Q3 稳定事实，但不扩大其主张边界。

## 3. AAAI 写作锚点：科学定位与写作风格分开使用

本次实际阅读了五篇 AAAI Proceedings 正式论文的全文或官方全文 PDF。以下记录只提炼结构动作，不把这些论文的技术主张迁移到 TerraState。

### 3.1 锚点总表

| 锚点 | 年份与正式链接 | 锚点类型 | 与 TerraState 的相关性 |
|---|---|---|---|
| *Driving in the Occupancy World: Vision-Centric 4D Occupancy Forecasting and Planning via World Models for Autonomous Driving* | AAAI-25；[官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/33010)，[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/33010/35165) | A+B | 世界模型身份、历史状态/条件/未来预测链；Introduction 的完整结果预告与贡献组织 |
| *Learning Hybrid Dynamics Models with Simulator-Informed Latent States* | AAAI-24；[官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/29075)，[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/29075/30035) | A+B | 潜状态必须由机制和作用证明，而非只靠命名；问题—限制—机制顺序成熟 |
| *SparseWorld: A Flexible, Adaptive, and Efficient 4D Occupancy World Model Powered by Sparse and Dynamic Queries* | AAAI-26；[官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/37347)，[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/37347/41309) | A+B | 近期 world-model 方法；从已有表示范式的具体局限过渡到模型组件与量化结果 |
| *iTrendRNN: An Interpretable Trend-Aware RNN for Meteorological Spatiotemporal Prediction* | AAAI-24；[官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/30217)，[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/30217/32164) | A+B | 科学/气象时空预测；用可解释机制回应“准确但不透明”的问题 |
| *Modeling Latent Non-Linear Dynamical System over Time Series* | AAAI-25；[官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/33269)，[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/33269/35424) | A+B | 潜状态与动力学；显式研究问题、技术挑战和方法身份的写法尤其成熟 |

其中，A 表示科学定位锚点，B 表示写作风格锚点。相同论文可以同时服务两类目的，但本报告分别使用：科学定位只比较任务、状态和动力学机制；写作校准只比较段落职责和论证顺序。

### 3.2 Drive-OccWorld

- **Introduction 段落职责：** 先从端到端自动驾驶进展和安全/泛化不足切入；随后引入 world models 和现有路线的缺口；再用 Figure 1 描述“预测未来世界—基于未来选择规划”的整体推理；之后明确提出 Drive-OccWorld，并按三个能力组织方法概览；最后给出量化结果和贡献。
- **Gap 出现位置：** 第二段，紧接已有 world-model 路线之后。
- **方法概览位置：** gap 和总推理链之后，不在第一段直接堆模块。
- **结果预告：** Introduction 中给出明确的量化收益，不只写“有效”。
- **Contributions：** 模型身份、关键模块、规划结合和实验验证按不同层级列出。
- **Related Work：** 以 2D image world models、3D/occupancy world models、端到端驾驶等主题分组；先说明一类工作解决什么，再说明本文落点。
- **可借鉴动作：** 先让读者接受任务和结构问题，再落地模型名；方法概览围绕能力而非模块清单；结果预告提供一两个有辨识度的数字。
- **不宜照搬：** 驾驶中的 action、planning、closed-loop rollout 和 controllability 不能类比成 TerraState 的因果天气控制。

### 3.3 Simulator-Informed Latent States

- **Introduction 段落职责：** 从动力学学习和递归模型的物理意义/误差累积问题开始；介绍物理模拟器和 hybrid modeling；指出许多可用模拟器是黑箱、内部状态不可访问；提出用 observer 从输出中恢复信息并影响 learned latent states；再说明 residual branch 保留灵活性；最后概括实验效果和贡献。
- **Gap 出现位置：** 第三段，且由前两段逐步收窄，不在开头直接宣布。
- **方法概览位置：** 问题边界和关键挑战之后。
- **结果预告：** 既报告预测改进，也说明机制带来的误差累积控制。
- **Contributions：** 新问题设置、机制、理论/算法和实验职责分开。
- **Related Work：** 围绕 physics-informed learning、hybrid modeling 和 latent-state estimation 的比较维度组织。
- **可借鉴动作：** 把“为什么普通预测不足”落实到可观察的结构问题；把潜状态的作用写成计算路径，而不是名词定义。
- **不宜照搬：** TerraState 没有物理模拟器、observer 或物理一致性保证，不能借用该论文的物理意义措辞。

### 3.4 SparseWorld

- **Introduction 段落职责：** 从 occupancy world model 的应用价值进入；依次审视 encode-then-forecast、dense grid 和固定范围/计算成本的局限；提出 sparse and dynamic queries 的总思路；分别概括感知、预测和训练组件；随后给出显著的定量结果和贡献。
- **Gap 出现位置：** 第二至第四段逐层形成，具体到表示和推理成本。
- **方法概览位置：** 多个 gap 被明确后，连续三段说明机制。
- **结果预告：** 给出相对提升和效率量级。
- **Contributions：** 一项模型、一组模块、一项训练策略、一项实证结果。
- **Related Work：** 3D occupancy prediction、4D occupancy world models、端到端驾驶三组；组内先分类，再指出采用的路线。
- **可借鉴动作：** gap 必须落到结构差异；结果预告要与前述缺口对应。
- **不宜照搬：** 该文的 Introduction 较长、组件段较多，TerraState 篇幅不适合复刻；其 SOTA 叙事也不适用于当前证据。

### 3.5 iTrendRNN

- **Introduction 段落职责：** 从气象预测意义和深度模型有效但不透明切入；提出“演化可表示为增量/趋势”的核心观察；按三类 trend 和融合模块概括方法；最后用贡献列表合并机制和实验。
- **Gap 出现位置：** 第一段末，紧随领域进展。
- **方法概览位置：** 核心观察之后，先解释为什么，再解释三个模块。
- **结果预告：** 主要放在贡献和摘要中，Introduction 正文不堆协议。
- **Contributions：** 总框架、三个可解释趋势、关键单元和实验分析。
- **Related Work：** spatiotemporal prediction 与 explainable AI 两组；每组先分类现有路线，结尾转向本文的透明/自解释目标。
- **可借鉴动作：** 用一个清楚、可验证的核心观察连接 gap 与机制；Related Work 每段最后明确本文差异。
- **不宜照搬：** “interpretable”在该文有特定模块含义；TerraState 的 intervention-based testability 不能直接称为完整可解释性。

### 3.6 LaNoLem

- **Introduction 段落职责：** 先介绍从数据发现非线性动力学的进展；指出时间依赖在现有方法中利用不足；用一个显式问题句定义研究任务；拆出潜状态建模和联合估计的两个技术挑战；随后提出 LaNoLem 及其两个核心组成，再进入结果与贡献。
- **Gap 出现位置：** 第二段。
- **方法概览位置：** 研究问题和两个挑战都明确之后。
- **结果预告：** 概括动力学估计的竞争性和预测优势。
- **Contributions：** 问题形式化、潜非线性模型/优化、复杂度选择和实证。
- **Related Work：** 围绕 dynamical-system identification、latent-state estimation 和 symbolic/nonlinear modeling 建立共同比较轴。
- **可借鉴动作：** 用一句科学问题收束 gap；先列挑战，再让每个方法组件逐一回应挑战。
- **不宜照搬：** TerraState 不做方程发现、稀疏系统辨识或可解释物理方程恢复。

## 4. AAAI Introduction 的共同结构规律

五篇锚点虽领域不同，但成熟开场普遍遵循以下动作：

1. **先定义任务与现实价值，不先定义作者的方法。** 第一段通常告诉读者输入、输出、应用和困难。
2. **先承认已有进展，再收窄到一个具体缺口。** gap 不是“现有方法都不行”，而是某种评价、表示、效率或机制尚未覆盖。
3. **在提出模型名前形成一个可复述的科学问题或设计要求。** 最成熟的论文让读者在看到模型名之前已知道为什么需要它。
4. **方法概览以“机制如何回应缺口”为主。** 模块名只有在承担明确功能时出现。
5. **结果预告与 gap 同构。** 若 gap 是状态作用，预告应说明状态干预结果；若 gap 是天气响应，预告应说明真实天气相对控制更忠实，而不是只给总体精度。
6. **Contributions 区分观点、方法、证据。** 不把一个长句同时写成问题、结构、训练和实验。
7. **限制性表述通常很少但明确。** 一句限定“不是因果模拟器/完整物理状态”足够；不需要在每段重复防御。
8. **公式和实现细节留到 Method。** Introduction 可以说 history → state → forcing-conditioned transition → forecast，但不需要提前写完整评测协议。

对 TerraState 的直接含义是：现有六段功能无需推倒重来，但需要把“本文的科学视角”“模型机制”“操作性证据判据”分开。

## 5. AAAI Related Work 的共同结构规律

1. 小节/段落标题代表一个**比较维度**，而不只是论文集合。
2. 每组先用一到两句定义该路线解决什么，再按两到三个子范式综合引用，避免逐篇摘要。
3. 对最接近工作给予更具体、也更公平的介绍；对远缘基础工作只保留与本文接口直接相关的部分。
4. 每组最后一句回答“TerraState 在同一比较维度上增加了什么”，而不是泛称“不同于现有方法”。
5. Introduction 的 gap 不应在 Related Work 中原样重复；Related Work 的职责是证明定位的准确性。
6. 预印本与正式论文必须明确区分，特别是最新近邻。
7. 一个 300–400 词的 Related Work 可以有较高引用密度，但每句话仍应有一个中心判断，不能以架构名串联代替论证。

## 6. 当前 Section 1 逐段反向提纲

当前正文（不含 Figure 1 caption）约 574 个英文词：五个正文段、一个引导句和三条 contribution bullets。Figure 1 caption 另约 70 词。

| 段落 | 当前首句 | 唯一职责 | 与前段关系与新概念 | 读者读完后知道什么 | 重复/时机 | 问题与严重度 |
|---|---|---|---|---|---|---|
| P1 | “High-resolution Earth-observation (EO) time series support localized monitoring…” | 定义任务、部分观测、天气/地理驱动，并引出 EarthNet2021/GreenEarthNet | 开篇；引入 partial observation、future forcing 和 predictive state | EO 预测输入/输出、数据不完备性与主要 benchmark | 在首段同时完成任务定义和 world-model 定性，略过早 | “is therefore a partially observed world-modeling problem”把本文视角写成必然事实；“The model must infer…”把选择的结构写成所有模型义务。**MAJOR** |
| P2 | “Progress on this task is measured primarily by fixed-horizon output accuracy.” | 建立输出准确不等于内部状态承载预测的 gap | 从任务过渡到证据不足；引入 routes around state、weak forcing use、latent disorder | 论文不只问预测是否准，还问状态是否参与、天气是否推进状态 | 与 RW 第一段末有轻微重复，但时机正确 | `declared state` 尚未定义；`fixed-horizon`容易被理解为单终点而非固定预测窗口；整体 gap 清楚。**MINOR** |
| P3 | “Following the predictive-state view of defining state through future observables…” | 引入预测状态视角、TerraState 的可检验思想及边界 | 回答 P2；引入 removable contribution、actual-vs-control fidelity、非因果边界和两个近邻 | TerraState 主张比完整物理状态/因果模拟器更窄 | 过早进入完整 20 步 masked loss 与 frozen controls；近邻比较与 Section 2 重叠 | 把 Q2/Q3 具体成功判据写成“state empirically meaningful”的定义，形成自定标准风险；协议语言过强。**MAJOR** |
| P4 | “As summarized in Figure 1, TerraState realizes this definition in one forecasting model.” | 方法总览和 Q1–Q3 证据链 | 从观点进入实现；引入 context-only branch、spatial state、shared transition、readout、future anchor | 能复述主要计算链和三类检验 | 128 词、7 句，部分细节与 Method 3.1–3.4 重复 | 结构准确，但 Q 编号和干预细节密集，像内部合同；可压缩为机制链+证据接口。**MAJOR** |
| P5 | “Experiments on GreenEarthNet show that TerraState retains useful forecasting skill under temporal shift.” | 概述主要实证发现 | 对应 P4 的三项问题 | Q1 有用、Q2 paired CI 排除零、Q3 actual 优于两控制 | 时机正确，无实验细节溢出 | 方向正确但过于定性；成熟 AAAI 开场通常至少给一个 headline 数字。**MINOR** |
| P6 | “Our contributions are:” | 三项贡献 | 总结全文 | 观点/架构、future-state anchor、证据链 | 三条总体不重复，但第一条同时承担观点与架构，第二条只承担训练机制 | 需要重新平衡成“问题/观点—方法—证据”；不能新增主张。**MINOR** |

### 6.1 Section 1 已完成的功能

- EO 部分观测、云遮挡、天气与地理驱动背景：**已完成**。
- 现有 EO 预测以输出质量为主要证据：**已完成，但应缩小主张范围**。
- 输出准确不等于形成/使用预测状态：**已完成，是当前最强 gap 句群**。
- 世界模型与预测状态的结构问题：**已完成，但视角和普遍定义未完全分开**。
- TerraState 关键观点：**已完成**。
- 方法概览：**已完成，略过细**。
- Q1–Q3 证据概览：**已完成，表达偏协议化**。
- 三项贡献：**已完成，层级需要重平衡**。

### 6.2 Figure 1 引用时机

Figure 1 的解释性引用位于观点段之后、方法概览段开头，符合锚点论文“先 gap/观点，后总图”的常见节奏。源码浮动体位于 P1 后不等于正文逻辑在 P1 已开始解释图片。当前引用时机可保留；本审计不提出任何图片修改。

## 7. 当前 Section 2 逐段反向提纲

当前 Related Work 约 308 个英文词，3 个 paragraph，引用 23 个不同 BibTeX key。信息密度高，但第一、三段的主题凝聚力不如第二段。

| 段落 | 当前首句 | 唯一职责 | 组织方式 | 最后如何定位 TerraState | 主要问题 | 严重度 |
|---|---|---|---|---|---|---|
| Weather-driven EO forecasting | “EarthNet2021 established land-surface forecasting…” | 交代 EO 预测任务、主要模型范式和输出级评价 | benchmark → weather ConvLSTM → GreenEarthNet → generic deterministic/generative/Koopman 列表 | TerraState 暴露 state-mediated path 并检验预测作用和天气响应 | 96 词容纳 10 组引用，偏名单；“Across these forecasting paradigms”后的概括范围过宽；generic video models 与 EO 近邻混在一起 | **MAJOR** |
| EO world models and forcing response | “Two concurrent preprints are especially close.” | 公平比较 EO-WM、VegSim 和 cloud-observability 工作 | 每篇给任务、机制、评价，再说明 TerraState 不替代它们 | removable state contribution + complete-window actual-weather fidelity | 是三段中最成熟的一段；`concurrent`是时间敏感状态，投稿前需复核 | **MINOR** |
| Predictive states and latent dynamics | “Predictive-state representations define state through predictions of future observables…” | 建立 PSR、latent world model、JEPA、LatentTSF、PLSM 等理论/方法背景 | 基础定义 → 现代 world models → representation prediction → latent disorder/control regularization → TerraState | future anchor + state on forecast path + intervention tests | I-JEPA 与 EO 动力学关系间接；最后 structured operator/group action 离主线远，并暗示 composition/Q4 | **MAJOR** |

### 7.1 三组是否足够

三组足够覆盖当前论文定位，无需新增第四个大组。关键是调整组内比较轴：

- 第一组比较“预测目标、天气接口和主要评价证据”；
- 第二组比较“是否显式建模状态、如何输入未来 forcing、如何验证 forcing response”；
- 第三组比较“状态如何被定义/监督，以及状态是否位于预测路径上”。

## 8. 当前优势

### 8.1 Section 1

- 六个核心功能全部存在，主叙事没有散到 Q4、composition、non-collapse 或 SOTA。
- P2 的结构性问题具体而可复述，不是空泛的“现有方法不可解释”。
- P4 的计算链与当前 Method 一致：history → predictive state；future weather → shared direct-horizon transition；advanced state → explicit state contribution → output。
- P5 没有把 Q3 subset \(R^2=0.6254\) 写成完整 OOD-t 结果，也没有夸大 hot-dry。
- 限制句明确排除了完整物理状态和因果模拟器，主张边界安全。
- Contribution 3 已按 Q1/Q2/Q3 的实际证据强度组织，没有宣称严格排名。

### 8.2 Section 2

- 三段顺序与 Introduction 和 Method 一致。
- EO-WM 与 VegSim 得到具体而公平的介绍，没有被贬为“不可检验”。
- 预印本状态在正文中明确标出。
- Diaconu 的天气扰动、EO-WM 的 output response、VegSim 的 scenario rollout 与 TerraState 的 state-path intervention 被正确区分。
- PSR、LatentTSF 和 PLSM 各自承担不同定位功能，不是同义引用。
- 现有句子没有把其他 EO 方法统一排除出 world models。

## 9. 问题清单

### 9.1 Critical

**NONE。** 没有发现会使 Section 1–2 科学结论失效的关键引用错误或与冻结证据相反的主张。

### 9.2 Major

1. **将研究视角写成任务的必然定义。**  
   当前：“Forecasting … is therefore a partially observed world-modeling problem.”  
   风险：审稿人可能认为作者先把 EO forecasting 重新命名为 world modeling。应改成功能等价的“本文从预测状态世界建模视角研究该任务”，并保留 partial observation 和 exogenous forcing 的论据。

2. **将本文评测判据写成预测状态的普遍经验定义。**  
   当前：“For that state to be empirically meaningful here, its contribution must be removable … and actual future weather must yield lower masked loss…”  
   风险：PSR 的科学定义、TerraState 的结构设计和本论文的 operational tests 混在一起。应先说明 predictive state 的未来可观测含义，再说“we test this claim through…”。

3. **Introduction 的方法概览过度协议化。**  
   P3–P4 连续出现 removable、without retraining、complete 20-step、frozen controls、Q1/Q2/Q3。科学证据链正确，但文字像 evaluation contract。应保留机制链，压缩协议细节到 Section 4。

4. **Related Work 第一段偏枚举。**  
   ConvLSTM、PredRNN、SimVP、Earthformer、MCVD、VegeDiff、ViT-Koop 在很短篇幅中并列，缺少统一比较轴。应按 deterministic forecast、probabilistic forecast、explicit latent transition 三类综合，而不是逐名列举。

5. **Related Work 第三段尾部偏离冻结主线。**  
   `Deep-OSG` 与 `World Models as Group Actions` 服务 composition/structured operator，而 Q4 明确不是正文主张。保留会让审稿人期待未提供的 composition 实验。建议删除该尾句及对应 Section 2 引用，除非正文其他核心段确有必要。

6. **精简镜像与权威正文不一致。**  
   `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md` 仍写 endpoint、correct predictive direction 和 composition exploratory extension；这与当前完整窗口 Q3 和 Q4 排除不一致。后续正文修订完成后必须统一同步，但本轮不修改。

### 9.3 Minor

1. `fixed-horizon output accuracy` 可被理解为单一终点；建议改成固定预测窗口内的 output accuracy。
2. `declared state` 在模型和“declared”含义出现前使用，带内部协议语感。
3. P4 为 128 词、7 句，是 Introduction 最重的一段，可压缩约 25–35 词。
4. P5 没有任何 headline 数字。可以仅加入 Q1 的 OOD-t \(R^2=0.56935\)、RMSE \(=0.15059\)，并用一句话概括 Q2/Q3；不需堆全部 CI。
5. Contribution 1 同时承担科学观点和架构，Contribution 2 只承担 future-state anchor；层级略不平衡。
6. `principal evidence concerns the quality of predicted observations` 是跨多范式综合判断，应限定为“in the cited forecasting studies”或“their primary reported evaluations”。
7. I-JEPA 是静态图像 representation prediction 锚点，不直接建模 EO 动力学；可与 V-JEPA 合并成一句基础背景，或只保留更接近时序预测的工作。
8. `concurrent preprints` 截至本审计日准确，但属于会变化的元数据，应在提交/相机稿前复核。
9. `testable`、`predictive state`、`forecast path` 在 P2–P4 高频重复，可减少一次，不影响术语一致性。

## 10. Section 1 目标蓝图

### 10.1 推荐结构

保留六个功能单元，但把 P3 的“观点”和 P4 的“机制/证据接口”重新分工。建议正文总计 **490–540 英文词**（不含 Figure 1 caption），比当前约 574 词压缩 35–80 词。

| 目标段 | 唯一职责 | 推荐句数 | 推荐词数 | 核心过渡功能 |
|---|---|---:|---:|---|
| P1 任务与意义 | 定义 weather-guided EO forecasting、部分观测、输入输出和应用背景；只说本文采用 world-modeling lens | 3–4 | 80–95 | 从真实 EO 条件过渡到“为什么预测状态视角合理” |
| P2 现有进展与评价范式 | 承认 EarthNet2021/GreenEarthNet 与模型进展；说明主要报告 output skill | 3 | 65–80 | 从“预测更准”过渡到“准确仍不能回答内部状态问题” |
| P3 核心缺口与科学问题 | 解释 predictive state 的未来可观测含义；提出状态是否承载预测、是否响应 forcing 的问题 | 3–4 | 75–90 | 从文献概念过渡到本文可证伪问题，不写具体 loss/CI |
| P4 TerraState 观点和方法 | 明确 “we introduce TerraState”；概括 history → state → shared forcing-conditioned transition → explicit forecast contribution；一句提 future anchor | 4–5 | 105–120 | Figure 1 在此引用；从机制过渡到可干预接口 |
| P5 主要发现 | 一句 Q1 headline 数字；一句 Q2 paired evidence；一句 Q3 complete-window fidelity；一句边界可选 | 3–4 | 70–90 | 让结果逐一回答 P3 的科学问题 |
| P6 三项贡献 | 观点/问题、方法、证据各一条 | 3 bullets | 85–100 | 把全文承诺冻结在 Q1–Q3 |

### 10.2 当前内容的保留、移动、压缩、删除

| 当前内容 | 动作 | 理由 |
|---|---|---|
| P1 对云遮挡、稀疏观测、天气和地理的说明 | 保留并轻压缩 | 是 world-modeling framing 的事实基础 |
| “is therefore a partially observed world-modeling problem” | 改写功能，不保留必然语气 | 将作者视角与领域普遍定义分开 |
| “does an accurate forecaster expose a state…”问题句 | 保留 | 是最清楚的科学问题 |
| PSR 对未来可观测量的定义 | 保留 | 提供科学定位，不是自定标准 |
| complete 20-step masked loss、without retraining、frozen controls | 从 P3 移出；在 P4/P5 只保留高层表述 | 避免 Introduction 像协议 |
| EO-WM/VegSim 对比 | 压缩为一句或移到 Section 2 | P3 当前承担过多 Related Work 功能 |
| P4 的 history/state/transition/readout 链 | 保留 | TerraState 的技术辨识度核心 |
| Q1/Q2/Q3 三个编号 | 最多保留一次 | 科学问题应先用自然语言表达 |
| P5 定性结果 | 保留并加入一个 Q1 headline 数字 | 提升 AAAI 结果预告成熟度 |
| 限制“not complete physical state or causal simulator” | 保留一次，可放 P3 末或 P5 末 | 一句足够，避免防御性重复 |

### 10.3 Figure 1 和方法粒度

- Figure 1 应在 P4 第一句或第二句引用。
- Introduction 保留到 \(q/P/T/O\) 的功能层面即可，不需要符号名、公式、训练系数或干预统计细节。
- 必须清楚说出显式预测闭环：状态不是旁路 probe，而是经 readout 对最终预测作出可移除贡献。
- 不需要在 Introduction 解释 direct-horizon transition、\(\alpha\equiv1\)、identity transition 或 teacher/target encoder 的冻结细节。

## 11. Section 2 目标蓝图

建议保留三个段落/小标题，总计 **330–390 英文词**。当前 308 词不是绝对过短，但因为 23 个引用集中，读起来更像压缩列表；稍微增加主题句和比较句，同时删去远缘工作，反而会更清楚。

| 推荐标题 | 覆盖论文 | 统一比较维度 | 段末 TerraState 定位 | 推荐词数 |
|---|---|---|---|---:|
| Weather-conditioned EO forecasting | EarthNet2021、Diaconu、GreenEarthNet/Contextformer、VegeDiff、ViT-Koop；ConvLSTM/PredRNN/SimVP/Earthformer/MCVD 只做综合背景 | 输入条件、预测目标、deterministic/probabilistic、主要 reported evaluation | TerraState 不取代输出评分，而是增加 state-mediated contribution 与 forcing-response 检验 | 105–125 |
| EO world models and forcing-conditioned simulation | EO-WM、VegSim；cloud-aware observability 作为不同目标的边界例子 | 是否显式状态、forcing 如何进入、是否 recurrent rollout、response 如何评价 | TerraState 的特异点是同一 observed-weather forecaster 中的 removable state path 和 actual-vs-frozen-control complete-window fidelity | 115–135 |
| Predictive-state and latent-dynamics foundations | PSR、World Models/PlaNet/Dreamer、V-JEPA/JEPA、LatentTSF、PLSM | 状态的定义、训练监督、动力学结构、状态是否进入预测/控制 | TerraState 把 future-representation anchor 与 on-path state intervention 结合，但不声称因果、composition 或完整物理状态 | 105–125 |

### 11.1 引用移动、保留、补充或删除

- **保留：** EarthNet2021、Diaconu、GreenEarthNet、EO-WM、VegSim、PSR、LatentTSF、PLSM。
- **保留但综合化：** ConvLSTM、PredRNN、SimVP、Earthformer、MCVD、VegeDiff、ViT-Koop、World Models、PlaNet、Dreamer、JEPA。
- **可删除：** Deep-OSG、World Models as Group Actions；它们主要服务 composition/structured-operator 议题。
- **不建议仅为“最新”补入：** RS-WorldModel、RemoteBAGEL、Earth-o1。前两者主要是文本/方向条件的遥感场景生成或空间外推，后者是大气系统模型；都不是 GreenEarthNet 型天气驱动的地表观测预测状态检验。
- **cloud-aware observability：** 可保留一句，也可因篇幅删除；其价值是划清“latent EO world model 但不同预测目标”的边界，不是 TerraState 的直接 baseline。

### 11.2 避免论文罗列的方法

- 每段最多使用三类范式，不按年份逐篇写摘要。
- 对 generic backbone 采用一组引用支撑一句综合判断。
- 对 EO-WM 和 VegSim 保留独立句，因为它们是最近邻。
- 每段最后只给一个具体 TerraState 区别，不重复完整 Q1–Q3。

## 12. 当前引用与近邻论文状态核验

### 12.1 逐项核验

| 工作 | 核验状态与原始链接 | 当前相邻主张是否支持 | TerraState 的真实区别 | 建议 |
|---|---|---|---|---|
| EarthNet2021 | 正式 CVPRW 2021，Requena-Mesa et al., pp. 1132–1142；[官方页面](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/html/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.html) | 支持由过去 Sentinel-2、地形和未来天气引导的未来卫星观测预测 | TerraState 使用 GreenEarthNet 任务并增加状态路径干预 | 保留 |
| GreenEarthNet / Contextformer | 正式 CVPR 2024，Benson et al., pp. 27788–27799；[官方页面](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html) | 支持 vegetation-focused dataset、cloud mask、OOD splits、weather-conditioned forecaster | TerraState 不是新 benchmark，而是预测状态结构与检验 | 保留 |
| Diaconu et al. weather ConvLSTM | 正式 CVPRW 2022；[官方页面](https://openaccess.thecvf.com/content/CVPR2022W/EarthVision/html/Diaconu_Understanding_the_Role_of_Weather_Data_for_Earth_Surface_Forecasting_CVPRW_2022_paper.html) | 论文同时报告天气输入对预测性能的重要性，并通过单变量天气变化做生成式响应分析；当前句有直接支持 | TerraState 的 Q3 是冻结 matched/mean controls 上的输出变化和 actual-weather fidelity，不是单变量情景展示 | 保留并公平说明其已有 response analysis |
| EO-WM | arXiv:2606.27277v1，2026-06-25；[arXiv](https://arxiv.org/abs/2606.27277)，[全文 HTML](https://arxiv.org/html/2606.27277v1)；截至审计日未见正式 venue | 支持部分可观测 weather-driven framing、climatology/anomaly/stress 条件和 extreme/seasonal matched-pair output diagnostics | EO-WM 是概率视频扩散与 output-level forcing diagnostics；TerraState 检验 on-path state contribution 和 actual-vs-control complete-window fidelity | 继续标记为 preprint；当前技术描述准确 |
| VegSim | arXiv:2606.21961v1，2026-06-20；[arXiv](https://arxiv.org/abs/2606.21961)，[全文 HTML](https://arxiv.org/html/2606.21961v1)；截至审计日未见正式 venue | 支持从稀疏 NDVI 历史推断 latent state、在未来天气下 recurrent rollout、解码 NDVI quantiles，并明确说场景响应不是 causal estimate | VegSim 强调 user-defined scenario simulation；TerraState 强调同一 spatial forecast state 的显式贡献和冻结控制 fidelity | 继续标记为 preprint；当前描述准确 |
| VegeDiff | 正式 IEEE TGRS 2025, vol. 63, article 4410214, 1–14；DOI [10.1109/TGRS.2025.3564317](https://doi.org/10.1109/TGRS.2025.3564317)，[作者机构全文](https://sgos.nju.edu.cn/_upload/article/files/95/a5/21bb720d49be9d2509183d9ec29d/759770ba-0b92-4ee4-94ae-7bb819290c51.pdf) | 支持 latent diffusion、多可能未来、动态气象与静态环境条件 | 不检验 TerraState 式 on-path state removal | 保留；BibTeX key 中 `2024` 只是内部 key，entry 年份 2025 正确 |
| ViT-Koop | 正式 ICCVW 2025, pp. 2835–2844；[官方页面](https://openaccess.thecvf.com/content/ICCV2025W/SEA/html/Shinohara_ViT-Koop_Vision-Transformer-Koopman_Operators_for_Efficient_Time-Series_Forecasting_of_Earth-Observation_Data_ICCVW_2025_paper.html) | 支持 ViT autoencoder 压缩 EO 序列并由线性 Koopman operator 推进 latent state | 重点是效率与预测质量，不是状态承载干预或天气替换 fidelity | 保留但避免暗示其状态未经任何结构验证 |
| LatentTSF | ICML 2026 正式论文，PMLR 306；[最终论文 PDF](https://openreview.net/pdf/f9677f148205ffd26d7535baccb38a68009925d1.pdf)，[ICML 2026 官方下载索引](https://icml.cc/Downloads/2026) | 直接支持“准确 observation forecast 可能伴随时间结构混乱的 latent representation” | TerraState 不采用其 latent forecasting paradigm，而是用 future representation anchor 和 intervention tests | 当前正式 venue 写法正确；不要称为 preprint |
| Predictive Representations of State | NIPS 2001，Littman, Sutton, Singh；[官方页面](https://proceedings.neurips.cc/paper_files/paper/2001/hash/1e4d36177d71bbb3558e43af9577d70e-Abstract.html)，[官方 PDF](https://proceedings.neurips.cc/paper/2001/file/1e4d36177d71bbb3558e43af9577d70e-Paper.pdf) | 支持以 action-conditional future-observation predictions 表示 state，而非依赖假定的生成隐藏状态 | TerraState 借用未来可观测联系，但没有建立完整 PSR 理论或 sufficient-statistic 保证 | 保留，需避免宣称 TerraState 等同经典 PSR |
| PLSM | 正式 NeurIPS 2024；[官方页面](https://proceedings.neurips.cc/paper_files/paper/2024/hash/43ba0466af2b1ac76aa85d8fbec714e3-Abstract-Conference.html)，[官方 PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/43ba0466af2b1ac76aa85d8fbec714e3-Paper-Conference.pdf) | 支持正则化 latent dynamics，使动作引起的状态变化更可预测/更少依赖当前 state | PLSM 是 agent action/control setting；TerraState 是 exogenous observed weather 与预测 fidelity | 当前句基本准确，建议注明概念性关联 |
| Cloud-aware observability world model | arXiv:2607.13651v1，2026-07-15；[arXiv](https://arxiv.org/abs/2607.13651)，[全文 HTML](https://arxiv.org/html/2607.13651v1)；截至审计日未见正式 venue | 直接支持其任务是预测观测是否可用及何时恢复，而非地表像素预测 | 目标不同，不是 TerraState baseline | 若篇幅紧可删；若保留必须继续标为 preprint |
| World Models as Group Actions | arXiv:2605.24578v1，页面明确 `Under review`；[arXiv](https://arxiv.org/abs/2605.24578) | 支持 identity/inverse/composition 的 group-action consistency | TerraState 不验证 composition/Q4 | 建议从 Section 2 删除 |

### 12.2 其他最新工作检索结论

- *Remote Sensing-Oriented World Model* / RemoteBAGEL（[arXiv:2509.17808](https://arxiv.org/abs/2509.17808)）研究方向条件的相邻遥感图块生成，任务不是天气驱动的同地点时间预测。
- *RS-WorldModel: a Unified Model for Remote Sensing Understanding and Future Sense Forecasting*（[arXiv:2603.14941](https://arxiv.org/abs/2603.14941)）研究变化理解与文本引导未来场景生成，仍是预印本，和 TerraState 的 GreenEarthNet 状态干预并不直接。
- *Earth-o1: A Grid-free Observation-native Atmospheric World Model*（[arXiv:2605.06337](https://arxiv.org/abs/2605.06337)）是大气观测原生天气模型，不是地表 EO 视频预测近邻。

在本次限定检索范围内，没有发现比 EO-WM、VegSim、GreenEarthNet/Contextformer、Diaconu weather-response analysis 和 LatentTSF 更需要立即纳入定位的工作。该结论是范围受限的审计判断，不是完整系统综述。

### 12.3 引用准确性警告

- Section 2 的 23 个引用 key 均存在于当前 `references.bib`，未发现缺失 key。
- `zhao2024vegediff` 的 key 年份与正式发表年份不同，但 entry 的 `year={2025}`、标题、五位正式版作者和 DOI 正确；key 无需为了外观而强制改动。
- Diaconu 论文在 CVF 页面与 IEEE/DLR 记录间存在页码起点显示差一页的出版编排差异；当前 CVF 引用页码 1362–1371 可接受。
- `Across these forecasting paradigms, the principal evidence...` 是作者综合判断，不是某一篇论文的直接原句；建议限定范围而不是继续扩大。
- `concurrent preprints` 当前准确，但必须在最终投稿日前再次检查 EO-WM、VegSim、cloud-observability 的 venue 状态。

## 13. Claim–evidence 边界

| Section 1–2 可出现的主张 | 证据与状态 | 推荐边界 | 禁止扩展 |
|---|---|---|---|
| EO forecasting 可从部分可观测、天气驱动的 world-modeling 视角研究 | EO 数据条件、EarthNet2021、GreenEarthNet、EO-WM；**supported as a framing** | 写成“we study/view/formulate” | 不写成所有 EO forecasting 的唯一或必然定义 |
| 输出准确不能单独证明内部状态承载预测 | 逻辑上成立；LatentTSF 给出相邻 representation-level 证据；**supported** | “cannot by itself establish” | 不写“所有现有模型都绕开状态” |
| TerraState 的状态介导贡献承载预测 | Q2 Val/OOD-t state-removal paired CI 均排除零；**supported** | `load-bearing state-mediated contribution` | 不把 identity transition \(T\to I\) 写成定义性核心证据 |
| TerraState 保留有效预测能力 | Q1 OOD-t \(R^2=0.56935\)、RMSE \(=0.15059\)；**supported** | `useful forecasting skill under temporal shift` | 不写 SOTA、严格排名或竞争最优 |
| 状态路径响应所提供的未来天气 | Q3 84 对替换均产生正有限输出变化；**supported as detectable response** | `weather-responsive` 或 `responds to supplied forcing` | 不写因果天气效应或 counterfactual correctness |
| actual weather 比 donor/mean 控制具有更高完整窗口保真度 | donor \(\Delta Loss=0.00257\), CI \([0.00112,0.00399]\)；mean \(0.01126\), CI \([0.00547,0.01708]\)；**supported** | 明确是 complete 20-step window、冻结 matched subset | 不把 subset \(R^2=0.6254\) 写成完整 OOD-t |
| Q2+Q3 支持 forecast-bearing and weather-responsive predictive state | 同一冻结模型上的 state removal 与 weather replacement；**supported with bounded interpretation** | 强调 operational/testable、not full physical state | 不写成完整世界状态、生成模拟器或因果模拟器 |
| hot-dry-specific enhancement | interaction CI 跨零；**unsupported** | 如涉及，只能作为负结果/限制 | 不得正向宣传 extreme-specific enhancement |
| temporal composition / non-collapse / Q4 | 未作为核心验证；**unsupported for main claim** | Section 1–2 不出现 | 不恢复 structured composition 叙事 |
| 公开方法严格可比或单种子 | 协议不统一；**unsupported** | Section 1–2 不做排名叙事 | 不写 Published/Local、seed、run 或人为比较 |

### 13.1 Q2/Q3 统计语义提醒

- Q2 的 paired mean 只能与 paired bootstrap CI 搭配；dataset-level official \(\Delta R^2\) 是独立统计量。Introduction 不需要展开这一区别，但若加入数字不得混配。
- Q3 差值方向是 `control loss − actual loss`；正值表示 actual weather 的预测窗口损失更低。Introduction 宜用自然语言表达，避免只给无方向定义的正数。
- Q3 response magnitude 与 endpoint/full-window fidelity 是不同 estimand；当前 Introduction 只需要后者的结论，不应把 detectable movement 当成 correctness。

## 14. 与摘要、方法、结果和图片的一致性

### 14.1 与冻结 Abstract

- 当前 `main.tex` Section 1 使用 complete forecast window，和冻结 Abstract 一致。
- 没有 SOTA、因果、composition、non-collapse 或 hot-dry enhancement 冲突。
- 两个精简镜像的 endpoint 叙事与冻结 Abstract 不一致，后续应以权威正文为准同步；不建议反向改 Abstract。

### 14.2 与 Method

- history encoder、spatial predictive state、shared weather-conditioned direct-horizon transition、state readout 和 context-only path 的概览一致。
- Introduction 没有把 transition 写成 recursive rollout 或 composition。
- future representation 只在训练时作为 anchor，未被写成推理输入。
- 建议修订后仍保持“future weather 进入 transition，而非 history encoder”的信息边界。

### 14.3 与 Results

- Q1、Q2、Q3 的现有定性预告均与当前结果方向一致。
- Section 1 没有恢复 11,904/boundary80。
- 旧 `RESULTS_CLAIM_EVIDENCE_AUDIT.md` 中的 endpoint wording 已被当前 4.4 完整窗口修订日志和 `main.tex` supersede；不能据旧审计回退。

### 14.4 与 Figure 1–3

- Figure 1 在方法概览处引用，文字和“预测能力—状态贡献—天气响应”三层概念一致。
- 本任务默认 Figure 1–3 正确；没有提出重绘、替换、重新导出或布局修改。
- Section 1–2 不应增加超出 Figure 1–3 当前证据边界的因果、Q4、极端天气增强或 SOTA 解释。

## 15. 建议的精确后续修改顺序

1. **先锁定 `main.tex` 为 Section 1–2 唯一英文权威版本。**
2. **修 P1：** 把 world-modeling 从领域必然定义改成本文研究视角，同时保留 partial observation 和 future forcing 的事实依据。
3. **修 P2：** 保留核心科学问题；把 `fixed-horizon`、`declared state` 改成自然学术语言。
4. **修 P3：** 分开 PSR 科学含义、TerraState 观点和本文 operational tests；删除或后移完整 20 步 masked-loss 协议细节。
5. **压缩 P4：** 只保留 history → state → transition → explicit contribution、future anchor 和高层 intervention interface；减少 Q 编号。
6. **增强 P5：** 加入一个 Q1 headline 数字，Q2/Q3 用各一句有边界的证据概述；不堆全部统计量。
7. **重平衡 contributions：** 第一条问题/观点，第二条完整方法（显式 state path + future anchor），第三条冻结证据链。
8. **再修 Section 2 第一段：** 从模型名单改成三类预测/评价范式。
9. **保留并轻修第二段：** 继续公平区分 EO-WM、VegSim 与 TerraState；投稿前复核 preprint 状态。
10. **收紧第三段：** 保留 PSR/latent dynamics/LatentTSF/PLSM，移除 composition-oriented 尾句。
11. **英文权威版本稳定后同步 `MANUSCRIPT_ZH_FULL.md`，再同步两个精简镜像。**
12. **最后进行一次引用邻接检查和 PDF 肉眼检查。** 该步骤应由获得写权限的正文会话执行，本轮不实施。

## 16. 必须保持冻结的内容

- Abstract 全文。
- Figure 1–3 的图像、布局、caption 和导出文件。
- Method 的实际计算路径和信息边界。
- Q1 OOD-t \(R^2=0.56935\)、RMSE \(=0.15059\)。
- Q2 state-removal 为主要证据，Validation 和 OOD-t 的 paired CI 排除零；\(T\to I\) 只作支持性诊断。
- Q3 84 对冻结 matched setting、detectable response、actual-vs-donor/mean complete-window fidelity 及差值方向。
- hot-dry 不支持 extreme-specific enhancement。
- Q4/composition/non-collapse 不作为正文核心主张。
- 不宣称 SOTA、严格排名、因果效应、counterfactual correctness、完整物理状态或 generative simulator。
- 不恢复 11,904/boundary80、旧 endpoint 结论或 subset \(R^2=0.6254\) 作为完整 OOD-t。
- 不在 Section 1–2 引入 Published/Local、seed、run 或公开数字来源叙事。

## 17. 评分

评分标准：1 = 明显不成熟或不可靠；3 = 基本成立但需实质修订；5 = 可冻结并作为全文模板。

| 维度 | Section 1 | Section 2 | 主要理由 |
|---|---:|---:|---|
| AAAI 结构成熟度 | 4 | 4 | 主骨架完整；S1 需分开视角/机制/判据，S2 需减少列表感 |
| 问题动机 | 4 | 4 | 部分观测与天气驱动明确；相关工作也围绕任务展开 |
| gap 清晰度 | 4 | 3 | S1 的核心问题清楚；S2 第一段的比较轴略散 |
| 世界模型定位 | 3 | 4 | S1 有“自定义后宣布满足”的风险；S2 对近邻区分较公平 |
| 方法概览 | 4 | 3 | S1 机制链准确但过细；S2 只需承担定位，不应重复方法 |
| 结果预告 | 3 | 3 | S1 有方向无 headline 数字；S2 正确克制、不应写结果 |
| contribution 质量 | 4 | 4 | 三条证据边界安全；S1 第一、二条层级仍需重平衡 |
| Related Work 组织 | 4 | 3 | S1 与 RW 边界尚可；S2 第一段名单化、第三段尾部漂移 |
| 近邻定位 | 4 | 4 | EO-WM、VegSim、cloud work 的区别准确且公平 |
| 引用准确性 | 4 | 4 | 未发现关键错误；若干综合句需缩小范围，预印本状态需复核 |
| 英文自然度 | 4 | 4 | 语法和术语稳定；P3–P4 有协议/审计文档感 |
| 与摘要/方法/结果一致性 | 4 | 4 | 权威正文一致；两个精简镜像仍有 endpoint/Q4 陈旧内容 |

## 18. 最终建议

- **当前 Section 1 不应立即冻结。** 它不需要大改结构，但需要一次有明确边界的定位修订。
- **当前 Section 2 不应在 Section 1 之前单独定稿。** 最接近工作定位已基本稳定，但最后一句“TerraState 的区别”应服从修订后的 Introduction 科学问题。
- **推荐先修改 Section 1，再修改 Section 2。**
- 修改后应先由作者肉眼检查是否仍有“作者自定 world-model 标准”的感觉，再决定是否推广为其他段落的写作模板。
- 本轮调研与审计已经完成，没有关键近邻或引用状态无法核验。

`CALIBRATION_COMPLETE_READY_FOR_SECTION1_REVISION`
