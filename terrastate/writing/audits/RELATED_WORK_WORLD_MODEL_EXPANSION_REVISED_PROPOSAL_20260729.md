# TerraState Related Work 世界模型谱系扩充返修提案

日期：2026-07-29  
任务性质：仅修改提案，不写入论文  
依据：`RELATED_WORK_WORLD_MODEL_EXPANSION_INDEPENDENT_AUDIT_20260729.md`

## 1. 返修结论

本提案保留四段式叙事，但将目标从“增加到约 30 篇引用”改为“每篇新增文献必须承担不可替代的叙事职责”。英文候选由原提案约 450 词收紧为 **409 词**，形成：

> weather-conditioned EO forecasting  
> → broader world-model paradigms  
> → EO-specific world models under external forcing  
> → predictive-state semantics and testability  
> → Section 3 的具体方法响应

新增建议从 8 篇减为 6 篇：保留 MuZero、IRIS、Genie、Drive-OccWorld、Predictive-State Decoders 和 Vafa et al.；删除职责重复的 DreamerV3 与 TD-MPC2。P1、P2 均不再以 TerraState 结尾，P3 才首次明确本文的互补生态位，P4 正向交给 Section 3。

本文件只是第二轮独立审计的候选输入。它不授权修改正文、BibTeX、PDF、镜像、图表或实验文件，也不将预计页数写成已实现结果。

## 2. 冻结输入与写入边界

### 2.1 输入 SHA-256

| 输入 | SHA-256 |
|---|---|
| `RELATED_WORK_WORLD_MODEL_EXPANSION_INDEPENDENT_AUDIT_20260729.md` | `b8f91d4f10640972c7d32e8a39d297bc9ee68042da82884d83a89824e867bd3c` |
| `RELATED_WORK_WORLD_MODEL_EXPANSION_PROPOSAL_20260729.md` | `f620de0c157ea418dc521c180643bdcf516223fdbf85334f87799f25a598b982` |
| `paper/main.tex` | `304db26cc894ba73641c8b2d09acd5fd3f36da1a9f54c6f7b7480b07be52a5d2` |
| `paper/references.bib` | `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3` |
| `paper/main.pdf` | `f9c3fce5e209b3506c0afa44e4c742b209ad21168f855419ae4e41c3aca2daed` |

### 2.2 本轮边界

- 唯一新产物是本返修提案。
- `main.tex`、`references.bib`、`main.pdf`、所有 `MANUSCRIPT*`、图表、caption 和实验文件保持不变。
- 本轮不编译，不声称 9 页目标已经满足。
- 所有文献元数据与支撑结论继承独立审计对官方 proceedings、期刊页面、PMLR、OpenReview 和 DOI 的核验。

## 3. P0/P1 逐项关闭表

| 审计项 | 原问题 | 本轮处理 | 关闭证据 | 状态 |
|---|---|---|---|---|
| P0-1 | TD-MPC2 作者元数据错误 | 从候选正文、新增引用集合和实施建议中删除 TD-MPC2 | 英文候选无 `hansen2024tdmpc2`；不再携带错误元数据 | **CLOSED** |
| P1-1 | 四段均以 TerraState 结尾，叙事反复回退 | P1 以内部状态问题收束；P2 以 EO 需要 task-specific predictive-state account 收束；仅 P3/P4 逐步引入本文 | P1、P2 末句均不含 `TerraState` | **CLOSED** |
| P1-2 | DreamerV3/TD-MPC2 职责重复，IRIS/Genie 职责未分开 | 删除 DreamerV3、TD-MPC2；IRIS 明确为 tokenized world model 中的 agent learning，Genie 明确为从视频学习 action-controllable environments | P2 为 MuZero、IRIS、Genie、Drive-OccWorld 分配独立句内职责 | **CLOSED** |
| P1-3 | P2 使用 `claims none`，呈 rebuttal 语气 | 改为正向概括不同 world-model objectives，并导向 EO 的 task-specific predictive state | P2 末句只承担上位谱系到 EO 的桥接 | **CLOSED** |
| P1-4 | P3 使用 `not a second version` 和 `without claiming` 连续防御 | 改为 `Complementing these objectives, TerraState examines ...`，直接写互补研究对象 | P3 不再罗列本文不具备的能力 | **CLOSED** |
| P1-5 | Vafa et al. 的适用范围被过度泛化 | 严格限定为 `In automaton-governed generative-model settings` | 不把该结论泛化到所有生成模型或 EO | **CLOSED** |
| P1-6 | P4 未把文献缺口积极交给具体方法机制 | 末句明确 `on-path predictive state`、`shared weather-conditioned transition`、`state-removal`、`weather-control interfaces` | 与 Method 3.1 的计算路径和接口直接对接 | **CLOSED** |
| P1-7 | 原 Conclusion 压缩删掉 shared transition 与 future-state anchoring | 新压缩候选显式保留二者，并保留 Q1–Q3 方向和边界 | 见第 9.2 节候选 | **CLOSED** |

返修后提案级计数：**P0 = 0，P1 = 0**。是否满足受控写入门禁仍须由第二次独立审计裁决。

## 4. 四段反向提纲与过渡

| 段落 | 唯一职责 | 内部组织 | 段尾功能 |
|---|---|---|---|
| P1 — Weather-conditioned EO forecasting | 建立 EO 任务、预测范式和现有证据层级 | benchmark → deterministic/probabilistic → compressed latent/weather-response analysis | 提出“显式内部状态是否进入预测并响应天气”的窄问题，不介绍 TerraState |
| P2 — World models: latent dynamics to interactive environments | 给出上位 world-model 语境并区分不同目标 | latent rollout/imagination → task-relevant targets → tokenized/interactive generation → occupancy forecasting/planning | 说明共同结构需要在 EO 中获得 task-specific predictive-state 解释，不介绍 TerraState |
| P3 — EO world models and forcing-conditioned simulation | 把上位结构落到部分观测、外生天气驱动的 EO | EO-WM → VegSim → observability boundary → weather as exogenous input | 以互补方式定位 TerraState 的 removable contribution 与 complete-window fidelity |
| P4 — Predictive states and testability | 建立 predictive-state 语义、监督方式和专门评估需求 | PSR/PSD → JEPA → LatentTSF → PLSM → scoped Vafa | 正向交给 Section 3 的 state、transition 和 intervention interfaces |

四个过渡可以分别用一句话解释：

1. **P1 → P2：** 当问题从预测输出转向内部表示时，需要借助更广义 world-model 文献中的 state–transition–prediction 结构。
2. **P2 → P3：** 该结构在 EO 中必须适应部分观测地表过程与外生天气 forcing，而不能直接继承控制或交互生成目标。
3. **P3 → P4：** 已有 EO world models 展示了 forcing 与场景输出，但内部状态的语义和可检验性仍需要 predictive-state 与 evaluation 文献来界定。
4. **P4 → Method：** 文献缺口具体导出一个位于预测路径上的状态、共享天气条件转移，以及状态移除和天气控制接口。

## 5. 英文候选正文

计数口径：仅统计四段 prose，忽略 paragraph 标题和 `\cite{...}` 命令；普通连字符复合词按一个 token 计，LaTeX 的 `state--transition--prediction` 按三个并列词计。总计 **409 词**，位于要求的 405–420 词区间。

### 5.1 Weather-conditioned EO forecasting

Weather-conditioned EO forecasting predicts future land-surface observations from satellite histories, meteorology, and geographic context. EarthNet2021 formalized this guided video-prediction setting, and GreenEarthNet/Contextformer refined it for vegetation dynamics and temporal shift \cite{requenamesa2021earthnet,benson2024multimodal}. Deterministic methods use recurrent, convolutional, or transformer predictors \cite{shi2015convlstm,wang2017predrnn,gao2022simvp,gao2022earthformer}, whereas video-diffusion models represent multiple plausible futures \cite{voleti2022mcvd,zhao2024vegediff}. ViT-Koop advances a compressed EO state, and prior weather-response analysis perturbs meteorological inputs at the output level \cite{shinohara2025vitkoop,diaconu2022weather}. Across these strands, evidence centers on forecast outputs, with some studies also analyzing weather response or learned representations. This leaves a narrower question about whether an explicit internal state participates in the prediction path and responds to supplied weather.

### 5.2 World models: latent dynamics to interactive environments

World-model research supplies the broader context for this shift from output prediction to explicit internal state. A control-oriented lineage compresses observations and learns latent transitions for rollout, planning, or imagination \cite{ha2018worldmodels,hafner2019planet,hafner2020dreamer}. MuZero predicts planning-relevant policy, value, and reward \cite{schrittwieser2020muzero}. IRIS learns an agent inside a tokenized world model, whereas Genie learns action-controllable environments from video \cite{micheli2023iris,bruce2024genie}. Drive-OccWorld connects action-conditioned occupancy forecasting to driving planning \cite{yang2025driveoccworld}. These examples share a state--transition--prediction structure but optimize different downstream objectives, motivating a task-specific account of predictive state in EO.

### 5.3 EO world models and forcing-conditioned simulation

In EO, this shared structure must be specialized to partially observed geospatial processes under external environmental drivers. Recent preprints make this connection explicit. EO-WM structures weather forcing for probabilistic EO forecasting and output-response diagnostics \cite{luo2026eowm}. VegSim rolls a latent vegetation state under user-specified weather for scenario-conditioned simulation \cite{iele2026vegsim}. A cloud-aware model instead predicts future observation availability rather than land-surface pixels \cite{albughdadi2026observability}. Here, future weather is an exogenous input for forecasting EO observations rather than the prediction target itself. Complementing these objectives, TerraState examines whether the state used by a weather-conditioned EO forecast makes a removable contribution and whether actual forcing yields greater complete-window fidelity than frozen controls.

### 5.4 Predictive states and testability

Predictive-state work asks how internal state is defined, supervised, and evaluated. Classical predictive-state representations define state through future observables, and Predictive-State Decoders explicitly supervise recurrent states to predict those observables \cite{littman2001predictive,venkatraman2017predictivestate}. I-JEPA and V-JEPA learn predictive representations without reconstructing raw pixels \cite{assran2023ijepa,bardes2024vjepa}. LatentTSF shows that accurate forecasts can coexist with temporally disordered latents \cite{yang2026latenttsf}, while PLSM constrains action effects in a control setting \cite{saanum2024simplifying}. In automaton-governed generative-model settings, dedicated evaluation further reveals incoherence missed by standard diagnostics \cite{vafa2024evaluating}. Together, these works motivate an EO-specific test: output accuracy alone cannot establish that an exposed state carries prediction or mediates weather forcing. Section 3 therefore constructs TerraState around an on-path predictive state, a shared weather-conditioned transition, and state-removal and weather-control interfaces that make this bounded claim testable.

## 6. 对应中文译文

### 6.1 天气条件驱动的 EO 预测

天气条件驱动的 EO 预测根据卫星观测历史、气象信息和地理背景预测未来地表观测。EarthNet2021 将这一任务形式化为带引导信息的视频预测，GreenEarthNet/Contextformer 又将其细化到植被动态和时间分布偏移场景 \cite{requenamesa2021earthnet,benson2024multimodal}。确定性方法采用循环、卷积或 Transformer 预测器 \cite{shi2015convlstm,wang2017predrnn,gao2022simvp,gao2022earthformer}，视频扩散模型则表征多种可能的未来 \cite{voleti2022mcvd,zhao2024vegediff}。ViT-Koop 推进压缩 EO 状态，已有天气响应分析则在输出层面考察气象输入扰动 \cite{shinohara2025vitkoop,diaconu2022weather}。总体而言，这些路线的证据主要围绕预测输出展开，也有部分工作分析天气响应或学习到的表示。由此留下一个更具体的问题：显式内部状态是否实际参与预测路径，并对给定天气作出响应。

### 6.2 从潜动力学到交互环境的世界模型

世界模型研究为从输出预测转向显式内部状态提供了更广泛的语境。面向控制的一条路线压缩观测并学习潜在转移，用于 rollout、规划或想象 \cite{ha2018worldmodels,hafner2019planet,hafner2020dreamer}。MuZero 预测与规划相关的策略、价值和奖励 \cite{schrittwieser2020muzero}。IRIS 在 token 化世界模型中学习智能体，而 Genie 从视频中学习可由动作控制的环境 \cite{micheli2023iris,bruce2024genie}。Drive-OccWorld 将动作条件下的占据预测与驾驶规划相连接 \cite{yang2025driveoccworld}。这些工作共享状态—转移—预测结构，却优化不同的下游目标，因此需要针对 EO 任务说明 predictive state 的具体含义。

### 6.3 EO 世界模型与 forcing 条件模拟

在 EO 中，这一共同结构必须适配外部环境驱动下的部分观测地理过程。近期预印本已明确建立这种联系。EO-WM 为概率 EO 预测和输出响应诊断组织天气 forcing \cite{luo2026eowm}。VegSim 在用户指定天气下推进潜在植被状态，用于情景条件模拟 \cite{iele2026vegsim}。另一项 cloud-aware 模型预测的是未来观测可用性，而非未来地表像素 \cite{albughdadi2026observability}。在这里，未来天气是预测 EO 观测的外生输入，而不是预测目标本身。作为对这些目标的补充，TerraState 检验天气条件 EO 预测所使用的状态是否对输出作出可移除贡献，以及真实 forcing 相比冻结控制是否具有更高的完整窗口忠实度。

### 6.4 预测状态与可检验性

预测状态研究关注内部状态如何定义、如何接受监督以及如何评价。经典预测状态表示以未来可观测量定义状态，Predictive-State Decoders 则显式监督循环状态预测这些未来可观测量 \cite{littman2001predictive,venkatraman2017predictivestate}。I-JEPA 和 V-JEPA 无需重建原始像素即可学习预测性表示 \cite{assran2023ijepa,bardes2024vjepa}。LatentTSF 表明准确预测可以与时间顺序混乱的潜表示同时存在 \cite{yang2026latenttsf}；PLSM 则在控制场景中约束动作效应 \cite{saanum2024simplifying}。在由自动机规则支配的生成模型设定中，专门评估还揭示了标准诊断未能发现的不一致 \cite{vafa2024evaluating}。这些工作共同导出一个 EO 特定的检验问题：仅凭输出精度，无法确认一个显式状态是否承载预测或介导天气 forcing。因此，Section 3 围绕位于预测路径上的 predictive state、共享天气条件转移，以及 state-removal 和 weather-control 接口构建 TerraState，使这一有边界的主张能够接受检验。

## 7. 新增文献引用职责表

| 建议 key | 正式来源 | 英文候选中的唯一职责 | Support verdict | 与其他新增项的边界 | 决定 |
|---|---|---|---|---|---|
| `schrittwieser2020muzero` | Schrittwieser et al., *Mastering Atari, Go, chess and shogi by planning with a learned model*, Nature 588, 2020, DOI `10.1038/s41586-020-03051-4` | 支撑 world model 可预测 planning-relevant policy/value/reward，而非完整观测 | **supported** | 不替代 PlaNet/Dreamer 的 latent rollout 身份 | **保留** |
| `micheli2023iris` | Micheli, Alonso, Fleuret, *Transformers are Sample-Efficient World Models*, ICLR 2023, OpenReview `vhFu1Acb0xb` | 支撑在 tokenized world model 内训练 agent | **supported** | 与 Genie 的环境生成职责不同 | **保留** |
| `bruce2024genie` | Bruce et al., *Genie: Generative Interactive Environments*, ICML 2024, PMLR 235:4603–4623 | 支撑从视频学习 action-controllable environments | **supported** | 不承担 agent-learning 或 occupancy-planning 职责 | **保留** |
| `yang2025driveoccworld` | Yang et al., *Driving in the Occupancy World: Vision-Centric 4D Occupancy Forecasting and Planning via World Models for Autonomous Driving*, AAAI 39(9), 2025, DOI `10.1609/aaai.v39i9.33010` | 支撑 action-conditioned occupancy forecasting 与 driving planning 的连接 | **supported** | 提供高维 occupancy 与正式 AAAI world-model 语境 | **保留** |
| `venkatraman2017predictivestate` | Venkatraman et al., *Predictive-State Decoders: Encoding the Future into Recurrent Networks*, NIPS 30, 2017 | 支撑以 future-observation prediction 显式监督 recurrent state | **supported** | 是 future-state supervision 的直接先例 | **保留** |
| `vafa2024evaluating` | Vafa et al., *Evaluating the World Model Implicit in a Generative Model*, NeurIPS 37, 2024, DOI `10.52202/079017-0846` | 仅支撑 automaton-governed generative-model settings 中专门评估可发现标准诊断遗漏的不一致 | **supported after scope restriction** | 与 LatentTSF 的 latent temporal order 证据互补，不外推为普遍定理 | **保留并限定** |

### 7.1 删除项

| 工作 | 删除原因 | 对叙事的影响 |
|---|---|---|
| DreamerV3 | 与现有 Dreamer 及原 TD-MPC2 scaling 句职责重叠；不是建立本文 world-model 上位语境所必需 | 无损；PlaNet/Dreamer 已覆盖 latent planning/imagination 谱系 |
| TD-MPC2 | 与 DreamerV3 职责重复，且原提案元数据存在 P0 | 无损；删除同时关闭元数据错误，不再以引用数量为目标 |

### 7.2 World Models 正式版本处理

若后续进入受控写入，`ha2018worldmodels` 应保持同一 key，但元数据应完整切换到 David Ha 与 Jürgen Schmidhuber 的正式 NeurIPS 2018 论文 *Recurrent World Models Facilitate Policy Evolution*。不得混用 arXiv 标题、arXiv ID 与正式 venue。这是版本纠正，不增加引用数量。

## 8. 主张—证据边界

| 候选表述 | 文献或本文职责 | 最大允许含义 | 禁止外推 |
|---|---|---|---|
| world models share a state–transition–prediction structure but optimize different objectives | P2 的综合 taxonomy | 本文为组织文献采用的比较框架 | 不宣称这是学界唯一定义 |
| explicit internal state participates in the prediction path and responds to supplied weather | P1 收束的研究问题 | 为 TerraState 的方法动机建立窄问题 | 不提前宣告 Q2/Q3 已成功 |
| removable contribution | TerraState Q2 接口 | 冻结模型中显式状态路径承载可测预测增量 | 不代表所有信息必须经过状态 |
| actual forcing yields greater complete-window fidelity than frozen controls | TerraState Q3 接口与冻结证据 | 条件预测忠实度 | 不解释为因果效应或反事实正确性 |
| dedicated evaluation reveals incoherence | Vafa et al. | 仅限 automaton-governed generative-model settings | 不外推到所有生成模型、EO 模型或 TerraState |
| bounded claim testable | P4→Method handoff | 可检验 on-path state contribution 和 weather response | 不引入完整物理状态、递归组合或通用模拟能力 |

本候选不写 Q1–Q3 数值，不引入 Q4、composition、non-collapse、SOTA 或严格排名，也不把控制、规划、交互生成能力赋予 TerraState。

## 9. 篇幅与等量压缩方案

### 9.1 Related Work

- 英文候选：**409 词**；
- 建议新增：**6 篇**，不以总引用数 30 为目标；
- 相比原约 450 词候选减少约 41 词；
- 最终行数、参考文献页数和总页数必须在获准写入并正式编译后确认。

### 9.2 Conclusion 安全压缩候选

以下仅是页面预算候选，不写入正文。它保留 shared weather-conditioned transition 与 future-state anchoring：

> TerraState makes internal predictive-state claims in weather-driven EO forecasting empirically testable. It combines a history-derived spatial state, a shared weather-conditioned transition, an explicit forecast contribution, and future-state anchoring with post-training state-removal and weather-substitution tests. Under the evaluated protocol, TerraState retains useful OOD-t skill, forecast performance degrades after state removal, and actual weather gives greater complete-window fidelity than frozen controls. These results support a forecast-bearing, weather-responsive predictive state without establishing a complete physical or causal world model.

该候选保留：

- problem：内部 predictive-state claim 的可检验性；
- method：history-derived state、shared transition、forecast contribution、future-state anchoring 和两个 post-training interfaces；
- evidence：Q1 有用预测能力、Q2 state removal 退化、Q3 actual-vs-control complete-window fidelity；
- boundary：不建立 complete physical 或 causal world model。

### 9.3 其他压缩纪律

- Limitations 如需压缩，必须继续保留非因果/非反事实边界、hot-dry null、state removal 不代表全部信息经状态、单数据集和观测限制。
- Table 3 caption 仅在正式编译仍有必要时压缩，且不得删 estimand、符号方向、paired unit 或 bootstrap 信息。
- 不修改字号、行距、页边距、模板，不使用负 `vspace`，不压缩图内内容。
- 预计 9 页只是实施目标；本提案没有编译，不能宣称页面目标已经实现。

## 10. 第二次独立审计门禁

进入受控写入前应再次确认：

1. 英文 prose 仍为 405–420 词；
2. P1、P2 末句不出现 TerraState；
3. DreamerV3、TD-MPC2 不在候选正文和新增 key 集合中；
4. MuZero、IRIS、Genie、Drive-OccWorld、Predictive-State Decoders、Vafa et al. 各有独立职责；
5. Vafa 仍有 automaton-governed generative-model scope；
6. P4 末句完整保留 on-path state、shared transition、state-removal 和 weather-control interfaces；
7. Conclusion 压缩若采用，必须保留 shared transition 与 future-state anchoring；
8. 不恢复 Q4/composition、因果或反事实正确性、完整物理状态、控制/规划能力归属、SOTA 或严格排名；
9. 正式写入后必须重新编译，实际确认主文第 7 页结束且第 8–9 页仅为 References；
10. 第二次独立审计给出 P0=0、P1=0 后，方可进入受控写入。

## 11. 只修改提案的声明

本轮仅新建：

`RELATED_WORK_WORLD_MODEL_EXPANSION_REVISED_PROPOSAL_20260729.md`

未修改 `paper/main.tex`、`paper/references.bib`、`paper/main.pdf`、任何 `MANUSCRIPT*`、Figure、Table、caption、实验结果或其他论文文件。

# READY_FOR_SECOND_INDEPENDENT_AUDIT
