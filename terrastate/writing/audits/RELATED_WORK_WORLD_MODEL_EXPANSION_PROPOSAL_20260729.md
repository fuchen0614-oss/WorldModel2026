# TerraState Related Work 世界模型谱系扩充提案

日期：2026-07-29  
性质：只读候选；本文件不授权直接写入正文。  
权威正文：`paper/main.tex`  
最终状态：**READY_FOR_INDEPENDENT_RELATED_WORK_AUDIT**

## 0. 提案结论

建议把当前三段 Related Work 重组为四段：

1. Weather-conditioned EO forecasting；
2. World models: latent dynamics to interactive environments；
3. EO world models and forcing-conditioned simulation；
4. Predictive states and testability。

该结构不是为了机械增加引用，而是补齐目前缺失的两层定位：

- 从 latent control models 到高维 interactive environments 的正式 world-model 谱系；
- 从 future-observation supervision 到 world-model-specific evaluation 的可检验状态谱系。

推荐新增 8 篇正式论文，正文唯一引用将由 22 篇变为 **30 篇**；`ha2018worldmodels` 同时由 arXiv *World Models* 修正为 NeurIPS 2018 正式论文 *Recurrent World Models Facilitate Policy Evolution*，但该修正不增加唯一引用数。

四段英文候选正文为 **450 词**（不计 paragraph 标题与 citation 命令），位于用户要求的 450–520 词下限。引用均承担明确论断；每个 citation cluster 不超过 4 篇。

## 1. 冻结输入与边界

### 1.1 权威文件 SHA-256

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `304db26cc894ba73641c8b2d09acd5fd3f36da1a9f54c6f7b7480b07be52a5d2` |
| `paper/main.pdf` | `f9c3fce5e209b3506c0afa44e4c742b209ad21168f855419ae4e41c3aca2daed` |
| `paper/references.bib` | `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3` |

### 1.2 已继承的质量文件

- `RELATED_WORK_LITERATURE_AND_WRITING_AUDIT.md`
- `SECTION1_2_AAAI_WRITING_CALIBRATION_AND_PREAUDIT_20260728.md`
- `SECTION2_FINAL_AUDIT_20260728.md`
- `FINAL_LANGUAGE_AAAI_STYLE_AUDIT_20260729.md`
- `REFERENCE_COVERAGE_AND_PAGE_LIMIT_AUDIT_20260729.md`
- `evidence_workspace/CLAIM_EVIDENCE_MAP.md`

### 1.3 不得变化的主张边界

- TerraState 是 weather-driven EO forecasting 中的 testable predictive-state world model，不是通用 world model 定义；
- Q1 是 forecasting prerequisite；
- Q2 state removal 是 primary，\(T\!\rightarrow I\) 只是 supporting；
- Q3 是 complete 20-step forecast-window fidelity；
- 不写 causal、counterfactual、complete physical state、recursive composition、Q4、SOTA 或严格排名；
- 不把控制、规划、交互式视频生成或驾驶闭环能力迁移给 TerraState；
- 不否定 EO-WM、VegSim、Diaconu 等工作的既有 response/state 能力；
- Related Work 只建立谱系与缺口，不提前报告 TerraState 实验结果。

## 2. 当前 Related Work 的反向提纲

### 2.1 Paragraph 1 — Weather-conditioned EO forecasting

当前职责：

1. EarthNet2021 与 GreenEarthNet/Contextformer 定义任务；
2. Diaconu et al. 承担天气输入和输出响应；
3. ConvLSTM、PredRNN、SimVP、Earthformer、MCVD、VegeDiff、ViT-Koop概括预测范式；
4. 段末把 TerraState 定位为输出评价之外的 state/forcing path test。

当前优点：

- benchmark、天气响应、确定性/生成式预测和显式 EO latent transition 均已覆盖；
- 对既有工作保持公平，没有声称它们只看精度。

当前不足：

- 模型密度高，仍略像压缩后的 citation list；
- world-model 基础谱系被挤到第三段，读者无法先理解该术语为何横跨多种架构。

### 2.2 Paragraph 2 — EO world models and forcing-conditioned simulation

当前职责：

1. 明确 EO-WM、VegSim、cloud-aware observability 均为 recent preprints；
2. 区分 probabilistic EO forecasting、scenario-conditioned latent rollout 与 observation-availability forecasting；
3. 段末定位 TerraState 的 removable state contribution 与 actual-vs-control complete-window fidelity。

当前优点：

- 是当前最成熟、最公平的近邻段；
- 没有将 TerraState 写成 EO-WM/VegSim 的替代品。

当前不足：

- 段前缺少一般 world-model 谱系，EO 世界模型出现得略突然；
- “天气作为预测对象”和“天气作为外生 forcing”的区别尚未显式说出。

### 2.3 Paragraph 3 — Predictive-state and latent-dynamics foundations

当前职责：

1. PSR 定义 state；
2. World Models、PlaNet、Dreamer建立 latent dynamics；
3. I-JEPA/V-JEPA 提供 representation prediction；
4. LatentTSF 提供“预测准确不保证 latent order”反例；
5. PLSM 提供 action-conditioned latent regularization；
6. 段末落到 TerraState 的 future anchor、on-path state 和 interventions。

当前优点：

- 状态定义、表示监督、潜动力学和 intervention 接口已经形成基本链条。

当前不足：

- control-oriented world models 与 predictive-state/testability 被压在同一段；
- 缺少 Predictive-State Decoders 这一 future-observation supervision 直接先例；
- 缺少专门讨论 implicit world-model evaluation 的正式工作；
- 当前 `ha2018worldmodels` 仍引用 arXiv 版本身份。

## 3. 新版本四段式反向提纲

| 段落 | 段首研究范围 | 范式综合 | 与本文相关的限制/空缺 | 段末 TerraState 区别 | 建议词数 |
|---|---|---|---|---|---:|
| 1. Weather-conditioned EO forecasting | 定义从 EO history、meteorology、geography 预测 future land-surface observations | benchmark；deterministic；probabilistic；compressed-state/weather-response | 主要证据仍落在 predicted observations，虽已有 response/representation analysis | 保留输出评价，同时直接检查 exposed state path | 97 |
| 2. World models: latent dynamics to interactive environments | world model 是预测范式族，不是单一架构 | latent planning/imagination；task-relevant model targets；tokenized interactive generation；occupancy planning | 各路线的 downstream objective 不同 | TerraState 不主张 control/planning/generation，只研究 EO forecast 内部状态是否实际起作用 | 111 |
| 3. EO world models and forcing-conditioned simulation | 把一般 world-model 思想落到部分观测 geospatial processes | EO-WM；VegSim；observability | weather target 与 exogenous forcing 必须区分 | 研究 observed-weather EO forecast 内部状态，不复制 EO-WM/VegSim 目标 | 116 |
| 4. Predictive states and testability | 内部状态编码什么、如何监督和验证 | PSR/PSD；JEPA；LatentTSF/PLSM；implicit-WM evaluation | output accuracy 不能单独建立 state contribution 或 forcing mediation | 用 state-removal/weather-control interfaces 检验本文限定的 state claim | 126 |

阅读顺序：

> EO 任务与预测范式  
> \(\rightarrow\) 一般 world-model 谱系及目标差异  
> \(\rightarrow\) EO world models 与外生 forcing  
> \(\rightarrow\) predictive state 如何被监督并检验。

该顺序比“EO forecasting → EO-WM → 混合基础工作”更容易让 AAAI 审稿人理解：TerraState 位于 EO forecasting 与 predictive-state testability 的交叉点，而不是通过重新命名 forecasting 获得 world-model 身份。

## 4. 英文逐段完整候选

以下文本为 LaTeX-ready 候选，但本轮未写入 `main.tex`。

### 4.1 Weather-conditioned EO forecasting

> **Weather-conditioned EO forecasting.** Weather-conditioned EO forecasting predicts future land-surface observations from satellite histories, meteorology, and geographic context. EarthNet2021 formalized this guided video-prediction setting, and GreenEarthNet/Contextformer refined it for vegetation dynamics and temporal shift \cite{requenamesa2021earthnet,benson2024multimodal}. Deterministic methods use recurrent, convolutional, or transformer predictors \cite{shi2015convlstm,wang2017predrnn,gao2022simvp,gao2022earthformer}, whereas video-diffusion models represent multiple plausible futures \cite{voleti2022mcvd,zhao2024vegediff}. ViT-Koop instead advances a compressed EO state, and prior weather-response analysis perturbs meteorological inputs at the output level \cite{shinohara2025vitkoop,diaconu2022weather}. These studies primarily assess predicted observations, sometimes together with response or representation analyses. TerraState retains output evaluation but asks whether an exposed state path contributes to the forecast and responds to supplied weather.

### 4.2 World models: latent dynamics to interactive environments

> **World models: latent dynamics to interactive environments.** World models comprise several predictive paradigms rather than a single architecture. A control-oriented lineage compresses observations and learns latent transitions for rollout, planning, or imagined behavior \cite{ha2018worldmodels,hafner2019planet,hafner2020dreamer}. MuZero narrows model targets to quantities relevant for planning, whereas DreamerV3 and TD-MPC2 scale learned dynamics across diverse control domains \cite{schrittwieser2020muzero,hafner2025dreamerv3,hansen2024tdmpc2}. Generative routes use tokenized dynamics to simulate interactive high-dimensional futures, as in IRIS and Genie, while Drive-OccWorld couples action-conditioned occupancy forecasting to driving planning \cite{micheli2023iris,bruce2024genie,yang2025driveoccworld}. These lines share a state, transition, and future-prediction structure, but their objectives range from control and planning to interactive generation. TerraState claims none of those downstream capabilities: it studies whether a predictive state is empirically active within a weather-driven EO forecast.

### 4.3 EO world models and forcing-conditioned simulation

> **EO world models and forcing-conditioned simulation.** EO world models specialize this broader idea to partially observed geospatial processes under external environmental drivers. Recent preprints make the connection explicit. EO-WM structures weather forcing for probabilistic EO forecasting and output-response diagnostics \cite{luo2026eowm}. VegSim rolls a latent vegetation state under user-specified weather for scenario-conditioned simulation \cite{iele2026vegsim}. A cloud-aware model predicts future observation availability rather than land-surface pixels \cite{albughdadi2026observability}. This setting differs from weather models that predict meteorology itself: here, future weather is an exogenous input used to forecast future EO observations. TerraState is therefore not a second version of EO-WM or VegSim. It focuses on the internal predictive state used by the observed-weather forecast, testing that path without claiming probabilistic simulation, recursive scenario rollout, or causal counterfactual validity.

### 4.4 Predictive states and testability

> **Predictive states and testability.** Predictive-state and representation-learning work asks what an internal state encodes and how claims about it can be directly evaluated. Classical predictive-state representations define state through future observables, and Predictive-State Decoders explicitly supervise recurrent states to predict those observables \cite{littman2001predictive,venkatraman2017predictivestate}. I-JEPA and V-JEPA learn predictive representations without reconstructing raw pixels \cite{assran2023ijepa,bardes2024vjepa}. LatentTSF shows that accurate forecasts can coexist with temporally disordered latents \cite{yang2026latenttsf}. PLSM constrains action effects in a control setting \cite{saanum2024simplifying}. Separate evaluation work shows that strong conventional diagnostics need not imply a coherent implicit world model \cite{vafa2024evaluating}. Together, these results leave an EO-specific question: output accuracy alone cannot establish that an exposed state carries prediction or mediates external forcing. TerraState addresses this question through post-training state-removal and weather-control interfaces, without treating those tests as a universal definition of world modeling.

## 5. 中文逐段对应版本

中文用于作者审阅逻辑，不建议直接作为逐字回译模板。

### 5.1 天气条件驱动的 EO 预测

天气条件驱动的 EO 预测利用卫星观测历史、气象信息和地理环境来预测未来地表观测。EarthNet2021 将其正式化为引导式视频预测任务，GreenEarthNet/Contextformer 又将其扩展到植被动力学和时间分布偏移评测。现有确定性路线包括循环、卷积和 Transformer 预测器，视频扩散路线则表示多个可能未来。ViT-Koop 显式推进压缩后的 EO 状态，既有天气响应工作也通过改变气象输入分析输出变化。这些研究主要评价预测观测，有时辅以响应或表示分析。TerraState 保留输出层评价，但进一步询问：暴露出来的状态路径是否真正对预测作出贡献，并对输入天气作出响应。

### 5.2 从潜动力学到交互环境的世界模型

世界模型不是一种固定架构，而是一组服务不同目标的预测范式。面向控制的路线通常压缩观测并学习潜在转移，用于 rollout、规划或想象中的策略学习。MuZero 将模型目标收缩为对规划有用的量，DreamerV3 和 TD-MPC2 则把学习到的动力学扩展到多种控制领域。另一条生成式路线使用离散或 tokenized dynamics 模拟高维交互未来，例如 IRIS 与 Genie；Drive-OccWorld 则把动作条件下的占据预测接入自动驾驶规划。这些路线都包含某种状态、转移和未来预测，但其目标分别偏向控制、规划或交互生成。TerraState 不继承这些下游能力，而是研究天气驱动 EO 预测中的内部预测状态是否实际参与该预测。

### 5.3 EO 世界模型与 forcing 条件模拟

EO 世界模型把上述一般思想具体化到外部驱动下的部分可观测地理过程。近期预印本已明确建立这一联系：EO-WM 对天气 forcing 进行结构化建模，用于概率 EO 预测和输出响应诊断；VegSim 在用户指定天气下推进潜在植被状态，进行情景条件模拟；cloud-aware 模型则预测未来观测是否可用，而不是未来地表像素。这里必须区分“把天气作为预测目标”和“把未来天气作为外生输入”：TerraState 属于后者，用未来天气预测 EO 地表观测。因此，TerraState 不是 EO-WM 或 VegSim 的第二版本。它聚焦 observed-weather forecast 内部所使用的预测状态，并检验该路径，但不主张概率模拟、递归情景 rollout 或因果反事实有效性。

### 5.4 预测状态与可检验性

预测状态和表示学习工作关注内部状态编码了什么，以及对这种状态的主张应如何验证。经典 PSR 通过未来可观测量定义状态，Predictive-State Decoders 则显式监督循环网络状态去预测这些未来观测。I-JEPA 和 V-JEPA 在不重建原始像素的情况下学习预测表示。LatentTSF 表明准确预测可以与时间顺序混乱的潜表示并存；PLSM 则在控制场景下约束动作对潜状态的影响。另有研究指出，常规诊断表现良好并不必然意味着模型恢复了连贯的隐含世界模型。这些工作共同留下一个 EO 特定问题：输出精度本身不能证明暴露状态承担预测或介导外部 forcing。TerraState 通过训练后的状态移除和天气控制接口检验这一问题，但不把本文测试写成世界模型的唯一普遍定义。

## 6. 每句承担的写作职责

### 6.1 Paragraph 1

| 句号 | 句子职责 | 引用职责 |
|---|---|---|
| P1-S1 | 首句定义 EO forecasting 的输入与输出范围 | 无需引用；由后句 benchmark 来源具体化 |
| P1-S2 | 用 EarthNet2021/GreenEarthNet 建立任务和 temporal-shift 语境 | benchmark/task identity |
| P1-S3 | 按 deterministic 与 probabilistic 两类综合模型，避免逐篇摘要 | architecture-family background |
| P1-S4 | 补充 explicit EO state 与既有 weather-response analysis | compressed-state/weather-response |
| P1-S5 | 公平概括现有评价重点，不说“只看精度” | 跨文献综合判断，使用 `primarily/sometimes` 限定 |
| P1-S6 | 在同一比较轴上给出 TerraState 区别 | 本文定位，不提前写结果 |

### 6.2 Paragraph 2

| 句号 | 句子职责 | 引用职责 |
|---|---|---|
| P2-S1 | 明确 world model 没有唯一架构定义 | 后续三类正式工作共同支撑这一综合 |
| P2-S2 | 建立 latent rollout/planning/imagination 主线 | World Models、PlaNet、Dreamer |
| P2-S3 | 建立 task-relevant model target 与 scalable control 主线 | MuZero、DreamerV3、TD-MPC2 |
| P2-S4 | 建立 tokenized interactive generation 与 occupancy-planning 主线 | IRIS、Genie、Drive-OccWorld |
| P2-S5 | 综合共同结构与不同用途 | 不把某一篇强迫为统一 world-model 定义 |
| P2-S6 | 明确 TerraState 不具备上述 downstream capabilities | 安全边界与 EO 任务落点 |

### 6.3 Paragraph 3

| 句号 | 句子职责 | 引用职责 |
|---|---|---|
| P3-S1 | 从一般谱系转向 EO/geospatial world models | 范围句 |
| P3-S2 | 明确随后三篇均是 recent preprints | 版本身份限定 |
| P3-S3 | 概括 EO-WM 的 forcing structure 与 output response | EO-WM 身份与机制 |
| P3-S4 | 概括 VegSim 的 latent scenario rollout | VegSim 身份与机制 |
| P3-S5 | 用 observability work 划定不同预测目标 | cloud-aware task boundary |
| P3-S6 | 区分 weather-as-target 与 weather-as-forcing | 防止把气象 world model 与 EO forecasting 混同 |
| P3-S7 | 否定简单“第二个 EO-WM/VegSim”的定位 | 最近邻公平性 |
| P3-S8 | 给出 TerraState 的内部状态检验落点及能力边界 | 不报告结果、不声称 causal |

### 6.4 Paragraph 4

| 句号 | 句子职责 | 引用职责 |
|---|---|---|
| P4-S1 | 定义 state semantics 与 testability 的研究范围 | 范围句 |
| P4-S2 | 连接 PSR 定义与 future-observation supervision | Littman + Predictive-State Decoders |
| P4-S3 | 提供非像素重建式 representation prediction 背景 | I-JEPA/V-JEPA |
| P4-S4 | 说明 forecast accuracy 与 latent temporal order 可脱钩 | LatentTSF |
| P4-S5 | 提供 driver/action effect regularization 的邻近概念 | PLSM，并明确 control setting |
| P4-S6 | 提供 world-model-specific evaluation gap | Vafa et al. |
| P4-S7 | 把文献综合收束为 EO-specific gap | 必要的 epistemic `cannot establish` |
| P4-S8 | 以 TerraState 两类接口结束，但不宣讲实验结果 | 本文区别与非普遍定义边界 |

## 7. 引用保留、新增、修正与删除

### 7.1 数量变化

| 项目 | 当前 | 候选实施后 |
|---|---:|---:|
| 全文唯一正文引用 | 22 | **30** |
| Related Work 唯一引用 | 21 | **29** |
| Method-only 额外唯一引用 | 1（PVT v2） | 1 |
| 正文删除引用 | 0 | 0 |
| 正式版本身份修正 | 0 | 1（World Models） |

### 7.2 保留的当前正文引用

全部 22 个现有正文引用保留：

- EO task/forecasting：`requenamesa2021earthnet`、`benson2024multimodal`、`diaconu2022weather`、`shi2015convlstm`、`wang2017predrnn`、`gao2022simvp`、`gao2022earthformer`、`voleti2022mcvd`、`zhao2024vegediff`、`shinohara2025vitkoop`；
- EO world models：`luo2026eowm`、`iele2026vegsim`、`albughdadi2026observability`；
- state/dynamics：`ha2018worldmodels`、`hafner2019planet`、`hafner2020dreamer`、`littman2001predictive`、`assran2023ijepa`、`bardes2024vjepa`、`yang2026latenttsf`、`saanum2024simplifying`；
- Method：`wang2022pvtv2`。

### 7.3 新增的 8 个建议 key

| 建议 key | 正式工作 | 段落 |
|---|---|---|
| `schrittwieser2020muzero` | MuZero | P2 |
| `hafner2025dreamerv3` | DreamerV3 正式 Nature 版本 | P2 |
| `hansen2024tdmpc2` | TD-MPC2 | P2 |
| `micheli2023iris` | IRIS | P2 |
| `bruce2024genie` | Genie | P2 |
| `yang2025driveoccworld` | Drive-OccWorld | P2 |
| `venkatraman2017predictivestate` | Predictive-State Decoders | P4 |
| `vafa2024evaluating` | Evaluating the World Model Implicit in a Generative Model | P4 |

### 7.4 删除

- **正文引用删除：0。**
- `chen2023deeposg` 与 `wang2026groupactions` 当前是 BibTeX 中的未使用条目；本提案不恢复它们，也不要求本轮清理，因为 Q4/composition 仍不进入正文。

## 8. 每篇新增文献的正式来源与支持关系

### 8.1 MuZero

- **正式标题**：*Mastering Atari, Go, chess and shogi by planning with a learned model*
- **作者**：Julian Schrittwieser; Ioannis Antonoglou; Thomas Hubert; Karen Simonyan; Laurent Sifre; Simon Schmitt; Arthur Guez; Edward Lockhart; Demis Hassabis; Thore Graepel; Timothy Lillicrap; David Silver
- **年份/正式场所**：2020, *Nature* 588, 604–609
- **DOI/官方来源**：[10.1038/s41586-020-03051-4](https://www.nature.com/articles/s41586-020-03051-4)
- **具体支持句**：P2-S3，“MuZero narrows model targets to quantities relevant for planning.”
- **为何不能由现有引用替代**：World Models/PlaNet/Dreamer主要建立 latent rollout 与 imagination；MuZero明确代表“不要求重建全部环境、只预测规划相关量”的 task-relevant model lineage。
- **与 TerraState 的区别**：MuZero面向 agent action、tree search、reward/value/policy；TerraState预测 EO observations，不执行规划或策略搜索。

### 8.2 DreamerV3 正式版本

- **正式标题**：*Mastering diverse control tasks through world models*
- **作者**：Danijar Hafner; Jurgis Pasukonis; Jimmy Ba; Timothy Lillicrap
- **年份/正式场所**：2025, *Nature* 640, 647–653
- **DOI/官方来源**：[10.1038/s41586-025-08744-2](https://www.nature.com/articles/s41586-025-08744-2)
- **具体支持句**：P2-S3，“DreamerV3 and TD-MPC2 scale learned dynamics across diverse control domains.”
- **为何不能由现有引用替代**：当前 Dreamer 2020 证明 latent imagination 的基本路线；DreamerV3 的正式版本承担跨 150+ tasks、fixed-configuration generality/scaling 的后续谱系，而不是重复 Dreamer 身份。
- **与 TerraState 的区别**：DreamerV3 在交互环境中学习 actor/critic 并想象 action outcomes；TerraState 没有 policy、reward 或 imagined behavior learning。
- **版本注意**：正式 Nature 标题不是早期 arXiv 标题 *Mastering Diverse Domains through World Models*；BibTeX 必须采用 Nature 的正式题名和元数据。

### 8.3 TD-MPC2

- **正式标题**：*TD-MPC2: Scalable, Robust World Models for Continuous Control*
- **作者**：Nicklas Hansen; Hao Su; Xiaolong Wang
- **年份/正式场所**：ICLR 2024
- **官方来源**：[ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/cf73d57b6dcda32b293df7c2d5341f49-Abstract-Conference.html)
- **具体支持句**：P2-S3，同 DreamerV3 一起支撑 scalable learned dynamics for diverse continuous control。
- **为何不能由现有引用替代**：PlaNet/Dreamer 是 model-based planning/imagination 基础，TD-MPC2 特别代表 decoder-free implicit world model、latent trajectory optimization 与 large multi-task scaling。
- **与 TerraState 的区别**：TD-MPC2 优化控制轨迹和任务回报；TerraState解码 future EO raster，不做 continuous control。

### 8.4 IRIS

- **正式标题**：*Transformers are Sample-Efficient World Models*
- **作者**：Vincent Micheli; Eloi Alonso; François Fleuret
- **年份/正式场所**：ICLR 2023
- **官方来源**：[ICLR official page](https://iclr.cc/virtual/2023/oral/12543)；[OpenReview identity](https://openreview.net/forum?id=vhFu1Acb0xb)
- **具体支持句**：P2-S4，“Generative routes use tokenized dynamics to simulate interactive high-dimensional futures.”
- **为何不能由现有引用替代**：现有 World Models/Dreamer 使用 recurrent latent dynamics；IRIS 直接代表 discrete autoencoder + autoregressive Transformer 的 tokenized world-model路线。
- **与 TerraState 的区别**：IRIS 在 Atari 中从生成世界模型学习策略；TerraState 使用空间 predictive state 预测 land-surface observations，不训练游戏 agent。

### 8.5 Genie

- **正式标题**：*Genie: Generative Interactive Environments*
- **作者**：Jake Bruce; Michael D. Dennis; Ashley Edwards; Jack Parker-Holder; Yuge Shi; Edward Hughes; Matthew Lai; Aditi Mavalankar; Richie Steigerwald; Chris Apps; Yusuf Aytar; Sarah Maria Elisabeth Bechtle; Feryal Behbahani; Stephanie C. Y. Chan; Nicolas Heess; Lucy Gonzalez; Simon Osindero; Sherjil Ozair; Scott Reed; Jingwei Zhang; Konrad Zolna; Jeff Clune; Nando De Freitas; Satinder Singh; Tim Rocktäschel
- **年份/正式场所**：ICML 2024, PMLR 235:4603–4623
- **官方来源**：[PMLR](https://proceedings.mlr.press/v235/bruce24a.html)
- **具体支持句**：P2-S4，支撑从未标注视频学习 latent actions 和 action-controllable interactive environments 的生成式谱系。
- **为何不能由现有引用替代**：IRIS 是 Atari agent 的 tokenized world model；Genie 代表更广义的 video-trained interactive environment generation 和 latent action learning。
- **与 TerraState 的区别**：Genie生成可交互虚拟世界；TerraState不生成开放式环境，也不学习 latent action space。

### 8.6 Drive-OccWorld

- **正式标题**：*Driving in the Occupancy World: Vision-Centric 4D Occupancy Forecasting and Planning via World Models for Autonomous Driving*
- **作者**：Yu Yang; Jianbiao Mei; Yukai Ma; Siliang Du; Wenqing Chen; Yijie Qian; Yuxiang Feng; Yong Liu
- **年份/正式场所**：AAAI 2025, 39(9):9327–9335
- **DOI/官方来源**：[10.1609/aaai.v39i9.33010](https://ojs.aaai.org/index.php/AAAI/article/view/33010)
- **具体支持句**：P2-S4，“Drive-OccWorld couples action-conditioned occupancy forecasting to driving planning.”
- **为何不能由现有引用替代**：Genie/IRIS支撑生成式交互环境；Drive-OccWorld提供正式 AAAI 场所中“高维未来状态预测进入下游 planning”的具体 world-model实例。
- **与 TerraState 的区别**：Drive-OccWorld预测 action-conditioned 4D occupancy 并选择驾驶轨迹；TerraState以 observed future weather 为 forcing，不做 ego-action planning。

### 8.7 Predictive-State Decoders

- **正式标题**：*Predictive-State Decoders: Encoding the Future into Recurrent Networks*
- **作者**：Arun Venkatraman; Nicholas Rhinehart; Wen Sun; Lerrel Pinto; Martial Hebert; Byron Boots; Kris Kitani; J. Andrew Bagnell
- **年份/正式场所**：NIPS 2017, Advances in Neural Information Processing Systems 30
- **官方来源**：[NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2017/hash/61b4a64be663682e8cb037d9719ad8cd-Abstract.html)
- **具体支持句**：P4-S2，“Predictive-State Decoders explicitly supervise recurrent states to predict future observables.”
- **为何不能由现有引用替代**：Littman定义 classical PSR，I-JEPA/V-JEPA预测 representations；PSD最直接支撑“通过额外 future-observation objective 约束内部 recurrent state”的训练谱系。
- **与 TerraState 的区别**：PSD面向 filtering、imitation learning 与 RL，不包含 EO weather forcing、显式 raster contribution、state removal 或 weather controls。

### 8.8 Evaluating the World Model Implicit in a Generative Model

- **正式标题**：*Evaluating the World Model Implicit in a Generative Model*
- **作者**：Keyon Vafa; Justin Y. Chen; Ashesh Rambachan; Jon Kleinberg; Sendhil Mullainathan
- **年份/正式场所**：NeurIPS 2024, Advances in Neural Information Processing Systems 37
- **DOI/官方来源**：[NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/2f6a6317bada76b26a4f61bb70a7db59-Abstract-Conference.html)，DOI `10.52202/079017-0846`
- **具体支持句**：P4-S6，“strong conventional diagnostics need not imply a coherent implicit world model.”
- **为何不能由现有引用替代**：LatentTSF只说明准确 observation forecast 可与 temporally disordered latent representations 并存；Vafa et al. 直接讨论 implicit world-model claim 应如何接受专门评测。
- **与 TerraState 的区别**：该工作在 deterministic finite automata、game、logic、navigation 中评价 model recovery；TerraState不恢复 automaton，也不提出通用 coherence metric，而是提供 EO-specific operational interfaces。

## 9. World Models 正式版本修正

当前：

- key：`ha2018worldmodels`
- title：*World Models*
- type：`@misc`
- identity：arXiv:1803.10122

建议保留 key，但把条目身份统一替换为：

- **正式标题**：*Recurrent World Models Facilitate Policy Evolution*
- **作者**：David Ha; Jürgen Schmidhuber
- **年份/正式场所**：NeurIPS 2018, Advances in Neural Information Processing Systems 31
- **官方来源**：[NeurIPS proceedings](https://proceedings.neurips.cc/paper/2018/hash/2de5d16682c3c35007e4e92982f1a2ba-Abstract.html)
- **正文职责**：P2-S2 的 compressed observations + predictive recurrent dynamics + policy learning。

不得把 arXiv 标题/identifier 与 NeurIPS venue 混成一个 synthetic BibTeX record。选择正式版本时应完整使用正式版本题名、作者、venue、volume 与 year。

## 10. 为什么其他相邻工作不进入本提案

以下工作可能相关，但没有独立正文职责，因此不建议为增加页数而加入：

- ClimaX：预测 weather/climate fields，本任务把 weather 当外生 forcing；
- Data-Efficient RL with Self-Predictive Representations：与 PSD、JEPA 的 representation-prediction 职责重复；
- Predictive State Recurrent Neural Networks：与 Littman + PSD 的 PSR/RNN 谱系重复；
- SparseWorld 等更多 driving world models：Drive-OccWorld 已足以承担 AAAI occupancy-planning 例子；
- RemoteBAGEL、RS-WorldModel：任务更接近文本/方向条件下的遥感生成，且目前为预印本；
- `wang2026groupactions`、`chen2023deeposg`：主要引向 composition/structured-operator 议题，和冻结 Q1–Q3 主线不一致。

## 11. 词数与页面预算

### 11.1 词数

采用“移除 citation 命令与 LaTeX 控制词、保留正文词”的一致口径：

| 项目 | 词数 |
|---|---:|
| 当前 Related Work 正文，不含 3 个 paragraph 标题 | 约 348 |
| 当前正文，含 paragraph 标题 | 约 361 |
| 既有审计/作者使用的可见近似值 | 约 377 |
| 新候选正文，不含 4 个 paragraph 标题 | **450** |
| 净增加（相对 348 词严格口径） | **102** |

“当前约 377 词”与严格源文件计数并不矛盾：前者接近 PDF 中包含标题及 author–year citation 展开后的可见文本；页面预算以编译结果为最终准据。

四段词数：

| 段落 | 词数 |
|---|---:|
| P1 | 97 |
| P2 | 111 |
| P3 | 116 |
| P4 | 126 |
| 合计 | **450** |

### 11.2 主文行数变化估计

- 新正文比严格当前正文多 102 词；
- 在当前 AAAI 双栏字号和列宽下，预计增加约 **10–13 个单栏正文行**；
- 新增 author–year citation 的长度可能再造成 1–2 行 reflow；
- 当前 Conclusion 已有 2 行越到第 8 页；
- 因此安全目标是回收约 **13–16 个单栏等效行**。

### 11.3 References 页数

- 当前 `main.bbl` 渲染 22 条参考文献，基本占满第 8 页；
- 新增 8 条后预计渲染 30 条；
- MuZero 与 Genie 作者列表较长，新增书目预计明显超过半栏；
- 在主文严格收回第 7 页后，References 很可能从第 8 页延伸到第 9 页。

这满足“最终 PDF 9 页、第 8–9 页仅 References”的目标，但仍必须在实际写入和完整编译后核验，不能以估算代替格式门禁。

## 12. 为七页边界准备的最小等量压缩方案

本节只提出候选，不修改任何正文。

### 12.1 第一层：Related Work 内部已经采用紧凑组织

候选已执行以下压缩：

- 不逐篇解释 ConvLSTM/PredRNN/SimVP/Earthformer；
- World Models/PlaNet/Dreamer 合为一条 latent-control lineage；
- MuZero/DreamerV3/TD-MPC2 合为 task-relevant/scalable control；
- IRIS/Genie/Drive-OccWorld 合为 interactive high-dimensional futures；
- EO-WM/VegSim/observability 各只保留一项任务辨识度；
- TerraState 每段只出现一次，不重复完整 Q1–Q3。

因此 8 篇新增引用只使 Related Work 达到 450 词下限，而不是膨胀到 550–650 词。

### 12.2 第二层：压缩 Conclusion 的重复收束

当前 Conclusion：约 109 词。  
候选：约 64 词，预计节省 **45 词 / 4–5 个单栏行**。

> TerraState makes internal predictive-state claims in weather-driven EO forecasting empirically testable. Its exposed state path enables post-training state-removal and weather-substitution tests on one model. Under the evaluated protocol, TerraState retains useful OOD-t skill, degrades after state removal, and gives actual weather greater complete-window fidelity than frozen controls. These results support a forecast-bearing, weather-responsive predictive state without establishing a complete physical or causal world model.

保留：任务、方法身份、Q1–Q3 方向和非物理/非因果边界。  
删除：与 Introduction/Contributions 重复的 state/transition/readout 再枚举。

### 12.3 第三层：压缩 Limitations 的重复边界

当前 Limitations：约 150 词。  
候选：约 91 词，预计节省 **59 词 / 5–7 个单栏行**。

> TerraState learns a future-predictive representation from satellite history and supplied meteorology, not a complete physical land-surface state. Its transitions use realized future weather; deployment with forecast meteorology may introduce unmeasured distribution shift.
>
> Weather controls establish conditional predictive fidelity, not causal or counterfactual validity. The hot-dry interval does not support extreme-specific enhancement, and state removal isolates a measurable state-mediated increment without implying that all information passes through this state.
>
> Evaluation is limited to GreenEarthNet temporal shift. Cloud screening and unobserved soil moisture, irrigation, and vegetation type may also limit the learned dynamics.

保留全部必要边界：

- 非 complete physical state；
- realized-vs-forecast weather deployment gap；
- 非 causal/counterfactual；
- 不支持 extreme-specific enhancement；
- state removal 不代表全部信息通过 state；
- 单数据集与未观测因素限制。

### 12.4 第四层：必要时压缩 Table 3 caption

当前 caption：约 49 词。  
候选：约 34 词，预计节省 **15 词 / 1–2 个单栏行**。

> Weather interventions on 84 frozen pairs. \(\Delta\)Loss is complete-window masked loss (control minus actual; positive favors actual); intervals are geographic-cluster 95\% CIs, counts are descriptive, and \(R^2\)/RMSE apply only to this subset.

保留：

- 84 frozen pairs；
- complete-window；
- control-minus-actual 方向；
- positive favors actual；
- geographic-cluster CI；
- descriptive counts；
- subset-only \(R^2\)/RMSE。

### 12.5 等量预算汇总

| 来源 | 预计节省 |
|---|---:|
| Conclusion | 45 词 |
| Limitations | 59 词 |
| Table 3 caption（必要时） | 15 词 |
| 合计 | **119 词** |

候选 Related Work 相对严格当前计数增加 102 词；上述压缩可净回收约 17 词，并吸收当前第 8 页的两行越界。由于 citation reflow 与 float placement 非线性，正式实施时应：

1. 先应用 450 词 Related Work + Conclusion + Limitations 压缩并编译；
2. 只有主文仍超过第 7 页时才使用 Table 3 caption 候选；
3. 若仍差 1–2 行，停止并重新审查 Related Work 的修饰词，不得改字体、模板、图片或实验定义。

预计结果：7 页主文 + 2 页 References，总 PDF 9 页。

## 13. 自审表

评分范围：1–5。

| 维度 | 分数 | 自审结果 |
|---|---:|---|
| Clarity | 4.8 | 四段首句均定义范围；每段最后一句说明 TerraState 区别。P2 不要求读者先接受单一 world-model 定义。 |
| Flow | 4.8 | EO forecasting → general WM → EO WM → predictive-state testability，层级由任务到谱系再回到本文问题。 |
| Terminology | 4.9 | `state`、`transition`、`future prediction`、`forcing`、`observed-weather forecast` 与正文一致；未引入 causal simulator 或 composition。 |
| Claim–evidence alignment | 4.9 | 每篇新文献只支持官方论文明确声明的机制或任务；TerraState 区别不借用其控制/生成结果。 |
| Citation completeness | 4.9 | 新增 PSD 和 implicit-WM evaluation 两项缺口；一般 world-model 谱系覆盖 control、task-relevant prediction、interactive generation 与 occupancy planning。 |
| AAAI-style similarity | 4.7 | 按研究范式而非年份组织；正式 AAAI Drive-OccWorld 作为一个职责明确的例子，而非风格照搬。 |
| Page-budget safety | 4.3 | 450 词已取建议下限，并给出 119 词等量压缩；最终仍需实际 LaTeX 编译确认 citation/float reflow。 |

### 13.1 语言门禁

- 每段首句均明确研究范围：PASS；
- 每段均按“范式 → 代表工作 → 与本文有关的空缺 → TerraState 区别”组织：PASS；
- 单个引用括号最多 4 篇：PASS；
- 无 citation dump 式逐篇摘要：PASS；
- 无 SOTA、first-ever、unprecedented：PASS；
- 无控制、规划或生成能力迁移：PASS；
- 无 Q4/composition：PASS；
- 无 causal/counterfactual/complete-state 主张：PASS；
- `cannot establish` 仅出现一次并承担必要认识论边界：PASS；
- 未机械清除 `while/with/does not/not`，也未形成否定句堆叠：PASS。

### 13.2 Claim–evidence 边界

| 候选主张 | 支撑 | 状态 |
|---|---|---|
| World models 是多种 predictive paradigms，而非唯一架构 | latent control、task-relevant planning、interactive generation、occupancy planning 四类正式工作 | 支持为综合分类，不写成公认唯一 taxonomy |
| Future-observation supervision 可塑造 internal predictive state | Predictive-State Decoders | supported |
| 常规诊断良好不必然意味着 coherent implicit world model | Vafa et al. 2024 | supported，限定在其研究设定；不外推为 TerraState 已证明 coherence |
| 输出精度单独不足以建立 EO state contribution/forcing mediation | 逻辑缺口 + LatentTSF + Vafa et al. | supported as motivation |
| TerraState 有 post-training state/weather interfaces | 当前 Method | supported；Related Work 不报告其结果 |
| TerraState 完成 planning/control/interactive generation | 无 | 明确不主张 |

## 14. 实施时的唯一推荐顺序

1. 独立审计本提案的文献职责与四段语言；
2. 若通过，再向 `references.bib` 加 8 个正式条目并修正 World Models identity；
3. 用本文件英文候选替换 Section 2；
4. 同步中文镜像；
5. 先编译检查引用、唯一条目数和 bibliography 身份；
6. 按 Section 12 顺序回收篇幅；
7. 最终确认第 1–7 页为主文，第 8–9 页只含 References；
8. 若任何格式或证据门禁失败，回退到最后一个合法状态，不通过压缩字体、负间距或删限制解决。

## 15. 只读声明

本轮未修改：

- `paper/main.tex`
- `paper/main.pdf`
- `paper/references.bib`
- `MANUSCRIPT.md`
- `MANUSCRIPT_ZH.md`
- `MANUSCRIPT_ZH_FULL.md`
- 任何 Figure、Table、caption、实验、证据或代码。

唯一新增文件为本提案。

# READY_FOR_INDEPENDENT_RELATED_WORK_AUDIT
