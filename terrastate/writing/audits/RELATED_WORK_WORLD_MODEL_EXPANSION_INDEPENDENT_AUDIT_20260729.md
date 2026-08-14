# TerraState Related Work 世界模型谱系扩充提案独立联合审计

审计日期：2026-07-29  
审计性质：独立、只读的叙事—文献—语言—篇幅联合审计  
待审对象：`RELATED_WORK_WORLD_MODEL_EXPANSION_PROPOSAL_20260729.md`  
正文事实源：`paper/main.tex`  
最终判定：**REVISION_REQUIRED**

## 1. 执行摘要

四段式方向本身成立：

> weather-conditioned EO forecasting  
> → broader world-model paradigms  
> → EO-specific world models under external forcing  
> → predictive-state semantics and testability  
> → TerraState Method

与当前三段相比，它能补上一般 world-model 谱系和专门的 state-testability
谱系，也能更清楚地解释 TerraState 为什么既不是普通 EO 精度模型，也不是控制、
规划或交互视频生成模型。

但当前提案尚不适合直接应用：

1. `TD-MPC2` 的作者元数据与 ICLR 官方 proceedings 不一致：官方记录为
   **Nick Hansen**，提案写成 **Nicklas Hansen**；
2. 四段均以 `TerraState ...` 结尾，导致 P1→P2、P2→P3 在已经介绍本文后又退回
   上位背景，递进链不够自然；
3. P2 中 DreamerV3/TD-MPC2 承担完全相同的实际句子职责，IRIS/Genie 的不同职责
   也没有写出来；“新增 8 篇”因而尚未通过必要性门禁；
4. P2 的 `TerraState claims none ...` 与 P3 的
   `TerraState is therefore not a second version ...` 明显带有 rebuttal/防御语气；
5. Vafa et al. 的结论来自 deterministic-finite-automaton 所刻画的生成模型设置，
   当前句子省略该范围，引用强度略宽；
6. P4 末句主要介绍 post-training tests，没有把读者自然交给 Section 3 的
   on-path predictive state 和 shared transition；
7. 提案的 Conclusion 压缩删掉了 `shared weather-conditioned transition` 和
   `future-state anchoring`，会削弱已经冻结的结论方法身份，不能按现稿直接采用。

问题计数：

| 等级 | 数量 |
|---|---:|
| P0 | **1** |
| P1 | **7** |
| P2 | **4** |

因此，本轮判定为 **REVISION_REQUIRED**。这些问题均可通过一轮局部调整解决，
不需要推翻四段结构、不需要新增实验，也不需要扩大文献范围。

## 2. 审计范围与输入身份

### 2.1 输入 SHA-256

| 文件 | SHA-256 |
|---|---|
| `RELATED_WORK_WORLD_MODEL_EXPANSION_PROPOSAL_20260729.md` | `f620de0c157ea418dc521c180643bdcf516223fdbf85334f87799f25a598b982` |
| `paper/main.tex` | `304db26cc894ba73641c8b2d09acd5fd3f36da1a9f54c6f7b7480b07be52a5d2` |
| `paper/main.pdf` | `f9c3fce5e209b3506c0afa44e4c742b209ad21168f855419ae4e41c3aca2daed` |
| `paper/references.bib` | `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3` |
| `RELATED_WORK_LITERATURE_AND_WRITING_AUDIT.md` | `6f9be77bfbcf234b8b04164a4f5c357933365f9f83fa7e5985424bba85813f88` |
| `SECTION1_2_AAAI_WRITING_CALIBRATION_AND_PREAUDIT_20260728.md` | `8b911acb17197a97966aa6c2be0697488c031f8e2012f9a9acad350c9ea163c9` |
| `SECTION1_FINAL_AUDIT_20260728.md` | `58ea63ee615d288c08c856d364b5de4b629e8dfab7fbc2e2b56a125540cddd5d` |
| `SECTION2_FINAL_AUDIT_20260728.md` | `8125dcb5cace88dd5f6c61483b497b9762d3f00e17733f4e62533fcb10c17e60` |
| `METHOD_GLOBAL_POSITIONING_AUDIT_20260728.md` | `7223bab798f94563531a851d805c5e03835934bd5040d75740ceeb9af463b92a` |
| `FINAL_LANGUAGE_AAAI_STYLE_AUDIT_20260729.md` | `24a0f8ae1c3f854f5d24a7025eb3c22f9467a0057662bccfe6595e2cab3ae7d3` |
| `REFERENCE_COVERAGE_AND_PAGE_LIMIT_AUDIT_20260729.md` | `9bf154588b912c9e5c164fc57a2fad8212608f12080b9b0122241724d290b3b7` |
| `evidence_workspace/CLAIM_EVIDENCE_MAP.md` | `d84ab20e8c470e732b7fd64f51575909949b3590366362067548c32d1559c88f` |

用户列出的根目录 `CLAIM_EVIDENCE_MAP.md` 不存在；本审计读取了项目内唯一同名文件
`evidence_workspace/CLAIM_EVIDENCE_MAP.md`。该路径解析明确，不构成阻塞。

### 2.2 当前局部区块 SHA-256

| 区块 | SHA-256 |
|---|---|
| Introduction | `2b7673f66dc0eb94810bc3fec64fd1c3feb85aa4128d8b04f61f8f8648806fae` |
| Related Work | `e6609d90667a20d41e196bca0c1da50e6b928428e707439b6368d155eee4bc94` |
| Method 3.1 | `68324eb4381a776660c61efca5824a543b2f4edcb943a4b9acadf89895cd4321` |

### 2.3 当前引用图

对当前 `main.tex` 与 `references.bib` 的只读静态清点结果：

- citation commands：22；
- citation-key occurrences：31；
- unique cited keys：22；
- BibTeX entries：24；
- missing keys：0；
- duplicate keys：0；
- unused entries：2（`chen2023deeposg`、`wang2026groupactions`）。

这些是当前冻结稿状态，不是扩充提案应用后的状态。

## 3. AAAI Related Work 结构基准

本审计阅读了四篇正式 AAAI 论文的全文 Related Work，而不是只看摘要。

| 正式论文 | 年份/官方来源 | Related Work 组织动作 | 对 TerraState 的可借鉴点 | 不宜照搬 |
|---|---|---|---|---|
| *Driving in the Occupancy World: Vision-Centric 4D Occupancy Forecasting and Planning via World Models for Autonomous Driving* | AAAI-25；[官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/33010) | 先以 2D image world models 和 3D volume world models 定义两条表示路线，再从表示/输出形式导向 occupancy forecasting 与 planning | 按“状态以什么形式表示、如何进入下游任务”分类 | 组内模型名较密；action、autoregressive rollout 和 planning 不能迁移给 TerraState |
| *GLAM: Global-Local Variation Awareness in Mamba-based World Model* | AAAI-25；[官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/33880) | 分为 world models 与 state-space models，两组分别支撑模型身份和具体序列模块 | 一般 world-model 背景应只保留对本文组件有解释力的类别 | world-model 段存在明显 citation density，不能作为堆模型名的许可 |
| *Battling the Non-stationarity in Time Series Forecasting via Test-time Adaptation* | AAAI-25；[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/33965/36120) | 首句明确因篇幅而收窄范围；围绕 non-stationarity 处理方式综合工作，随后指出 train-distribution 限制，并区分 online TSF 与 TSF-TTA | 最成熟的动作是“限定研究范围 → 综合机制 → 精确缺口 → 本文任务边界” | 不能把其 test-time adaptation 叙事迁移给 TerraState |
| *Modeling Latent Non-Linear Dynamical System over Time Series* | AAAI-25；[官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/33269) | 以 nonlinear dynamics 与 time-series analysis 两类要求组织，并用统一能力维度比较 | 每组应由共同技术要求统领，而非按年份排列 | 该文使用较多 `none/cannot` 与逐项排除，TerraState 不应复制这种防御密度 |

### 3.1 共同规律

1. **段首先限定研究范围。** 成熟 Related Work 不以论文名开场，而以任务、
   表示、动力学或评测问题定义本段。
2. **代表工作服务于比较轴。** 引用按机制或目标综合；模型名只有在解释该类别
   内部差异时才展开。
3. **缺口由同一比较维度导出。** 不是笼统写“prior work is limited”，而是说明
   既有目标与本文目标在 state、transition、forcing、evaluation 等哪一维不同。
4. **最后一段负责交给 Method。** Related Work 末尾应让 Section 3 的设计成为
   前述缺口的自然响应，而不是突然列出本文所有模块和结果。
5. **引用密度不是质量本身。** Drive-OccWorld/GLAM 中较密的模型列表是可见风险；
   TAFAS 的范围限定和机制综合更适合作为 TerraState 的写作基准。

### 3.2 对候选四段的总体校准

候选的研究顺序优于当前三段，专业度和逻辑密度基本达到 AAAI 方法论文正常水平；
真正未达标的是段尾组织。当前四段均先给文献再以 `TerraState ...` 自我定位，形成
四次近乎相同的“背景 → 我们”循环。优秀的四段递进更适合：

- P1 以内部预测路径问题收束；
- P2 以上位 world-model 目标差异收束；
- P3 开始明确 TerraState 的 EO 生态位；
- P4 把 state semantics/testability 交给 Method。

## 4. 当前四段反向提纲

| 段落 | 当前唯一职责 | 实际论证动作 | 当前段尾 | 判定 |
|---|---|---|---|---|
| P1 Weather-conditioned EO forecasting | 建立任务和输出预测范式 | benchmark → deterministic/probabilistic → compressed state/weather response → 输出证据概括 | 直接介绍 TerraState 的 exposed state path | **职责成立；段尾需调整** |
| P2 World models | 建立一般 state–transition–future prediction 谱系 | latent control → task-relevant planning → scaling → tokenized generation → occupancy planning | 用否定句声明 TerraState 不具备这些能力 | **谱系成立；引用与语气需收紧** |
| P3 EO world models | 从一般谱系落到 EO 和外生 forcing | EO-WM → VegSim → observability → weather target/forcing distinction | 两句连续排除 TerraState 是什么 | **近邻事实成立；段尾不合格** |
| P4 Predictive states and testability | 给 state semantics、supervision 和 evaluation 基础 | PSR/PSD → JEPA → latent counterexample/control regularization → implicit-WM evaluation | 只以两个 intervention interface 结束 | **文献链成立；Method handoff 不完整** |

## 5. 跨 Section 叙事映射

| Introduction claim | Related Work 应建立的文献缺口 | Method response | Q1/Q2/Q3 evidence |
|---|---|---|---|
| 固定窗口输出精度不能单独验证内部状态 | EO forecasting 已覆盖 deterministic、probabilistic、latent-transition 与 weather-response 路线，但主要证据对象仍是 forecast outputs | 显式 \(b_h+r_h\) 预测闭环和可移除的 state-mediated contribution | Q1 先确认 useful skill；Q2 state removal 检验 state contribution |
| 准确输出可以与有问题的 latent representation 共存 | LatentTSF 提供 latent-order 反例；Vafa et al. 提供特定生成模型设置下的 world-model-specific evaluation 先例 | future-state anchoring 塑造 transitioned state；state removal 检验该状态是否实际进入预测 | Q2 paired effects 和 official \(\Delta R^2\) |
| future meteorology 是否真正推进状态不能由输出准确自动推出 | Diaconu/EO-WM 已研究 output response；VegSim 已研究 weather-conditioned latent scenario rollout，但目标和证据接口不同 | future weather 只进入 shared transition；Q3 只替换该路径 | Q3 detectable response + actual-vs-donor/mean complete-window fidelity |
| TerraState 是限定的 predictive-state EO world model，不是通用 agent simulator | 一般 world models 服务 control、planning、interactive generation 和 occupancy prediction等不同目标；EO 需要任务特定的 state semantics | history-derived state → shared forcing-conditioned transition → on-path readout → test interfaces | Q1–Q3 联合支持 forecast-bearing、weather-responsive state；不支持控制、规划、因果或 composition |

这张映射能够闭合。当前候选的问题不在于提出了 Method 未解决的问题，而在于 P2/P3
通过否定句保护边界、P4 又只突出测试接口，使 Method 的积极机制响应不够突出。

## 6. 四段职责审计

### 6.1 P1 — Weather-conditioned EO forecasting

**PASS 的部分**

- 首句清楚定义输入与输出；
- EarthNet2021、GreenEarthNet/Contextformer、Diaconu 的职责公平；
- deterministic、probabilistic、compressed-state 三类范式成立；
- `primarily` 与 `sometimes` 避免“所有既有工作只看精度”的绝对化。

**需要调整**

- 段末立即写 `TerraState retains ...`，使下一段再回到一般 world models 时发生
  叙事回退；
- `These studies primarily assess predicted observations` 略抽象，可直接写
  evidence centers on forecast outputs；
- 本段更适合以“内部状态是否进入预测路径”的问题收束，而不是第一次完整定位
  TerraState。

### 6.2 P2 — World models: latent dynamics to interactive environments

**PASS 的部分**

- `world model` 被明确处理为本文的综合分类，而非单一架构；
- latent control/imagination、task-relevant planning、interactive generation、
  occupancy planning 四个上位语境都是真实存在的路线；
- 没有把这些能力写进 TerraState 的方法事实。

**需要调整**

- `DreamerV3 and TD-MPC2 scale ...` 让两篇承担同一个句子职责；scaling 也不是
  TerraState 需要建立的独立范式；
- IRIS/Genie 被放在同一个 `tokenized dynamics` 槽位，实际差异没有写出：
  IRIS 是在离散 token world model 内训练 Atari agent，Genie 是从视频学习
  action-controllable environment generation；
- `TerraState claims none of those downstream capabilities` 是审稿回复式语气；
- P2 更适合以“这些路线具有共同 state–transition–prediction 结构但服务不同
  downstream objectives”结束，再由 P3 落到 EO。

### 6.3 P3 — EO world models and forcing-conditioned simulation

**PASS 的部分**

- EO-WM、VegSim、cloud-aware observability 的任务事实和 preprint 身份准确；
- weather-as-target 与 weather-as-exogenous-forcing 的区分有助于保护 EO 范围；
- 没有把 EO-WM/VegSim 降格为“不是 world model”。

**需要调整**

- `TerraState is therefore not a second version of EO-WM or VegSim` 是用户明确要求
  避免的句型；
- 下一句再用 `without claiming ...` 连续排除 probabilistic/rollout/causal，
  把本应最重要的最近邻定位写成防御清单；
- `observed-weather forecast` 是内部化、略难恢复的术语；
- 应正向写为：TerraState complementing these objectives，研究一个
  weather-conditioned EO forecast 中 state contribution 和 forcing fidelity
  是否可检验。

### 6.4 P4 — Predictive states and testability

**PASS 的部分**

- PSR → PSD 的 future-observation supervision 链直接服务 future-state anchoring；
- JEPA 只承担 representation prediction，不被迫证明 TerraState world-model 身份；
- LatentTSF、PLSM 和 Vafa et al. 分别承担 latent quality、driver/action
  regularization 和专门评测职责；
- `output accuracy alone cannot establish ...` 是必要认识论边界，不应机械删除。

**需要调整**

- Vafa et al. 只在 deterministic-automaton-governed 的生成模型设置中直接证明
  conventional diagnostics 会漏掉 incoherence；当前句省略范围；
- 最后一句直接跳到 post-training interfaces，容易让 TerraState 看起来是评测
  技巧，而不是具有 explicit state、shared transition 和 on-path contribution
  的方法；
- 应以“Section 3 构造怎样的 state/transition/path，并由哪些接口检验”完成交接。

## 7. 段落间过渡审计

| 过渡 | 应回答的问题 | 当前能否一句解释 | 当前问题 | 判定 |
|---|---|---|---|---|
| P1 → P2 | 为什么从 EO outputs 转向一般 world models？ | 勉强：因为问题从输出转到内部状态 | P1 已经介绍 TerraState，P2 又退回一般谱系 | **P1** |
| P2 → P3 | 为什么一般谱系要落到 EO forcing？ | 可以：相同 state–transition 结构在 EO 中受 partial observation 和 exogenous weather 约束 | P2 的防御式 TerraState 结尾打断这一步 | **P1** |
| P3 → P4 | 为什么已有 EO world models 后还需 state semantics/testability？ | 可以：已有工作有 forcing/rollout/response，但内部 state claim 仍需单独语义和证据 | 当前缺显式桥句 | **P2** |
| P4 → Method | 为什么文献导出 TerraState 设计？ | 部分：interfaces 回答 testability | 未提 on-path state 与 shared transition 的积极设计响应 | **P1** |

建议的递进分工：

- P1：以 exposed internal path 的问题收束；
- P2：以 task-dependent world-model objectives 收束；
- P3：首次明确 TerraState 的 EO-specific focus；
- P4：明确把读者交给 Section 3 的 state–transition–interface 设计。

## 8. 英文逐句问题

### 8.1 P0（1）

#### P0-1 — `TD-MPC2` 作者元数据

**Location:** Proposal §8.3  
**Original:** `Nicklas Hansen; Hao Su; Xiaolong Wang`  
**Problem:** 当前 ICLR 2024 官方 proceedings 的作者字段为
`Nick Hansen, Hao Su, Xiaolong Wang`。  
**Minimal revision sentence/field:** `author = {Hansen, Nick and Su, Hao and Wang, Xiaolong}`  
**Citation-duty/scientific-meaning effect:** 不改变 TD-MPC2 的技术职责，但必须使用
正式版本的当前作者元数据；若按本报告建议删除该冗余引用，则无需新增该条目。  
**Priority:** P0

### 8.2 P1（7）

#### P1-1 — 四段均以 TerraState 结尾

**Location:** P1-S6、P2-S6、P3-S7/S8、P4-S8  
**Original:** `TerraState retains ...` / `TerraState claims none ...` /
`TerraState is therefore not ...` / `TerraState addresses ...`  
**Problem:** 四次重复“本段文献 → TerraState”，使中间两次转场先落到本文、再退回
背景，缺少持续收紧的文献论证。  
**Minimal revision sentence:** P1 以
`This leaves a narrower question about whether an explicit internal state participates in the prediction path and responds to supplied weather.`
结束；P2 以 task-dependent objectives 结束，只在 P3/P4 明确 TerraState。  
**Citation-duty/scientific-meaning effect:** 不改变任何引用职责或 TerraState 主张，
只改变叙事顺序。  
**Priority:** P1

#### P1-2 — 新增文献职责重复

**Location:** P2-S3、P2-S4  
**Original:** `DreamerV3 and TD-MPC2 scale learned dynamics across diverse control domains.`  
`... as in IRIS and Genie ...`  
**Problem:** DreamerV3/TD-MPC2 在实际句子中职责完全相同；IRIS/Genie 虽有不同
机制，却被写成同一例子。当前文本不能证明 8 篇均有独立正文职责。  
**Minimal revision sentence:**  
`MuZero predicts planning-relevant policy, value, and reward, while IRIS learns an agent inside a tokenized world model and Genie learns action-controllable environments from video.`  
Drive-OccWorld 可另用一句承担 occupancy-to-planning。建议移除 TD-MPC2；DreamerV3
也可不进入正文，因为现有 Dreamer 已建立 imagination lineage。  
**Citation-duty/scientific-meaning effect:** 收紧引用而不改变 taxonomy；避免把
scaling 当成与 TerraState 直接相关的范式。  
**Priority:** P1

#### P1-3 — P2 防御式结尾

**Location:** P2-S6  
**Original:** `TerraState claims none of those downstream capabilities: it studies whether a predictive state is empirically active within a weather-driven EO forecast.`  
**Problem:** `claims none` 像 rebuttal，先列 TerraState 不会什么，再说它做什么，
削弱方法气势。  
**Minimal revision sentence:**  
`These examples share a state--transition--prediction structure but optimize different downstream objectives, motivating a task-specific account of predictive state in EO.`  
**Citation-duty/scientific-meaning effect:** 保留 control/planning/generation 与 EO 的
能力边界，不新增 TerraState 能力。  
**Priority:** P1

#### P1-4 — P3 连续防御句

**Location:** P3-S7/S8  
**Original:** `TerraState is therefore not a second version of EO-WM or VegSim. It focuses ... without claiming probabilistic simulation, recursive scenario rollout, or causal counterfactual validity.`  
**Problem:** 第一行是提案明确要求避免的“不是某工作的第二版”；第二行继续以
`without claiming` 列排除项。最近邻差异应写成正向比较维度。  
**Minimal revision sentence:**  
`Complementing these objectives, TerraState examines whether the state used by a weather-conditioned EO forecast makes a removable contribution and whether actual forcing yields greater complete-window fidelity than frozen controls.`  
**Citation-duty/scientific-meaning effect:** EO-WM、VegSim、observability 的职责不变；
TerraState 仍不主张 causal/counterfactual validity，但无需在 Related Work 重复
完整否定清单。  
**Priority:** P1

#### P1-5 — Vafa et al. 的范围省略

**Location:** P4-S6  
**Original:** `Separate evaluation work shows that strong conventional diagnostics need not imply a coherent implicit world model \cite{vafa2024evaluating}.`  
**Problem:** 原论文针对由 deterministic finite automata 描述的生成模型任务，
并不直接评估 EO latent states。当前一般化句子虽使用 `need not`，但
`strong conventional diagnostics` 和适用域仍过宽。  
**Minimal revision sentence:**  
`In automaton-governed generative-model settings, dedicated evaluation further reveals incoherence missed by standard diagnostics \cite{vafa2024evaluating}.`  
**Citation-duty/scientific-meaning effect:** 使引用回到原论文直接支持的范围；仍可
作为“world-model claim 需要专门评价”的概念先例，但不直接证明 TerraState gap。  
**Priority:** P1

#### P1-6 — P4 到 Method 的积极机制不足

**Location:** P4-S8  
**Original:** `TerraState addresses this question through post-training state-removal and weather-control interfaces ...`  
**Problem:** 只突出测试接口，会把本文方法降格为 evaluation wrapper；Section 3
真正构造的是 on-path state、shared weather-conditioned transition 和显式
state contribution。  
**Minimal revision sentence:**  
`Section 3 therefore constructs TerraState around an on-path predictive state, a shared weather-conditioned transition, and state-removal and weather-control interfaces that make this bounded claim testable.`  
**Citation-duty/scientific-meaning effect:** 不需要外引；准确映射当前 Method 3.1，
不增加实验结论。  
**Priority:** P1

#### P1-7 — Conclusion 压缩删除核心方法身份

**Location:** Proposal §12.2  
**Original:** `Its exposed state path enables post-training state-removal and weather-substitution tests on one model.`  
**Problem:** 相对冻结 Conclusion，该压缩删除 shared transition 和
future-state anchoring，使结论更像“预测器 + 两个测试”，不利于收束 world-model
方法身份。  
**Minimal revision sentence:**  
`TerraState combines a history-derived spatial state, a shared weather-conditioned transition, an explicit forecast contribution, and future-state anchoring with post-training state-removal and weather-substitution tests.`  
**Citation-duty/scientific-meaning effect:** 不改变证据，只保留被冻结的方法组件。
若篇幅仍不足，应优先从 P2 冗余引用和修饰语回收，而不是删这两个组件。  
**Priority:** P1

### 8.3 P2（4）

| Location | Original | 问题 | 可选最小方向 |
|---|---|---|---|
| P1-S5 | `These studies primarily assess predicted observations ...` | `assess predicted observations` 略抽象 | 改为 `evidence centers on forecast outputs`，保持 `some studies also ...` |
| P2-S1 | `World models comprise several predictive paradigms rather than a single architecture.` | 容易被读成权威 taxonomy | 改为 `World-model research spans several predictive paradigms.`，明确是本文综合 |
| P3-S6 | `This setting differs from weather models that predict meteorology itself ...` | 引入一个未展开、未引用的外部领域 | 正向写 `Here, future weather is an exogenous input for forecasting EO observations rather than the prediction target.` |
| P3/P4 | `observed-weather forecast`、多层 `state / transition / prediction / forcing` 名词串 | 前者像内部术语，后者局部密度高 | 统一为 `weather-conditioned EO forecast`；每句只保留一个主要比较中心 |

## 9. 新增 8 篇与 World Models 正式版本核验

### 9.1 元数据与引用职责

| 工作 | 正式元数据与官方来源 | 候选承担句 | Support verdict | 与其他新增项重复 | 是否需要 |
|---|---|---|---|---|---|
| MuZero | Julian Schrittwieser, Ioannis Antonoglou, Thomas Hubert, Karen Simonyan, Laurent Sifre, Simon Schmitt, Arthur Guez, Edward Lockhart, Demis Hassabis, Thore Graepel, Timothy Lillicrap, David Silver. 2020. *Mastering Atari, Go, chess and shogi by planning with a learned model*. **Nature 588**, 604–609. DOI [10.1038/s41586-020-03051-4](https://doi.org/10.1038/s41586-020-03051-4). | planning-relevant model targets | **supported** | 与 PlaNet/Dreamer 都属 control，但“只预测 planning-relevant quantities”职责独立 | **保留** |
| DreamerV3 | Danijar Hafner, Jurgis Pasukonis, Jimmy Ba, Timothy Lillicrap. 2025. *Mastering diverse control tasks through world models*. **Nature 640**, 647–653. DOI [10.1038/s41586-025-08744-2](https://doi.org/10.1038/s41586-025-08744-2). | diverse-domain scaling | **supported**；正式题名和版本正确 | 与现有 Dreamer 和 TD-MPC2 的正文职责高度重合 | **可删；非必要** |
| TD-MPC2 | **Nick Hansen**, Hao Su, Xiaolong Wang. 2024. *TD-MPC2: Scalable, Robust World Models for Continuous Control*. **ICLR 2024**, 47376–47405. [官方 proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/cf73d57b6dcda32b293df7c2d5341f49-Abstract-Conference.html). | diverse-domain scaling | 技术句 **supported**；提案作者字段错误 | 与 DreamerV3 同句同职责 | **建议删除；若保留必须修元数据** |
| IRIS | Vincent Micheli, Eloi Alonso, François Fleuret. 2023. *Transformers are Sample-Efficient World Models*. **ICLR 2023**. [官方 OpenReview 论文](https://openreview.net/forum?id=vhFu1Acb0xb). | tokenized dynamics / agent in imagined world | **supported** | 与 Genie 都属 generative/tokenized route，但 agent-learning 目标不同 | **保留时必须写出独立职责** |
| Genie | Jake Bruce, Michael D. Dennis, Ashley Edwards, Jack Parker-Holder, Yuge Shi, Edward Hughes, Matthew Lai, Aditi Mavalankar, Richie Steigerwald, Chris Apps, Yusuf Aytar, Sarah Maria Elisabeth Bechtle, Feryal Behbahani, Stephanie C. Y. Chan, Nicolas Heess, Lucy Gonzalez, Simon Osindero, Sherjil Ozair, Scott Reed, Jingwei Zhang, Konrad Zolna, Jeff Clune, Nando De Freitas, Satinder Singh, Tim Rocktäschel. 2024. *Genie: Generative Interactive Environments*. **ICML 2024 / PMLR 235**, 4603–4623. [PMLR](https://proceedings.mlr.press/v235/bruce24a.html). | action-controllable environment generation from video | **supported** | 与 IRIS 的生成式路线相邻，但训练来源和交互目标不同 | **保留** |
| Drive-OccWorld | Yu Yang, Jianbiao Mei, Yukai Ma, Siliang Du, Wenqing Chen, Yijie Qian, Yuxiang Feng, Yong Liu. 2025. *Driving in the Occupancy World: Vision-Centric 4D Occupancy Forecasting and Planning via World Models for Autonomous Driving*. **AAAI 39(9)**, 9327–9335. DOI [10.1609/aaai.v39i9.33010](https://doi.org/10.1609/aaai.v39i9.33010). | action-conditioned occupancy forecasting → planning | **supported** | 与 Genie/IRIS 不同，承担高维 occupancy state 和正式 AAAI 语境 | **保留** |
| Predictive-State Decoders | Arun Venkatraman, Nicholas Rhinehart, Wen Sun, Lerrel Pinto, Martial Hebert, Byron Boots, Kris Kitani, J. Bagnell. 2017. *Predictive-State Decoders: Encoding the Future into Recurrent Networks*. **NIPS 30**. [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2017/hash/61b4a64be663682e8cb037d9719ad8cd-Abstract.html). | future-observation supervision of recurrent state | **supported** | 无；是 future-state supervision 的直接先例 | **必须保留** |
| Vafa et al. | Keyon Vafa, Justin Y. Chen, Ashesh Rambachan, Jon Kleinberg, Sendhil Mullainathan. 2024. *Evaluating the World Model Implicit in a Generative Model*. **NeurIPS 37**. DOI [10.52202/079017-0846](https://doi.org/10.52202/079017-0846). | conventional diagnostics may miss world-model incoherence | 当前句 **partially supported**；加 automaton/generative-model scope 后 **supported** | 与 LatentTSF 互补：一个是 latent temporal order，一个是 implicit-WM evaluation | **保留并限定** |

### 9.2 World Models 版本

正式版本为：

- David Ha, Jürgen Schmidhuber；
- *Recurrent World Models Facilitate Policy Evolution*；
- NeurIPS 2018，Advances in Neural Information Processing Systems 31；
- [官方 proceedings](https://proceedings.neurips.cc/paper/2018/hash/2de5d16682c3c35007e4e92982f1a2ba-Abstract.html)。

提案要求把当前 `@misc` *World Models* 完整切换为正式 NeurIPS identity 是正确的。
不得把 arXiv 标题/ID 与正式 venue 混为一个条目。正式论文足以支持 compressed
spatiotemporal representation、recurrent world model 和 policy-learning 语境。

### 9.3 必要性裁决

不建议以“30 篇”作为成功条件。建议受控应用时：

- 必须新增：PSD、Vafa；
- 高价值谱系新增：MuZero、Genie、Drive-OccWorld；
- 可保留但需明确独立职责：IRIS；
- 可删除：DreamerV3；
- 建议删除：TD-MPC2（并同时消除当前 P0）；若坚持保留，必须修正作者元数据并
  明确 decoder-free implicit control model 的独立职责。

采用上述最小谱系后，新增为 6 篇、全文唯一引用约 28 篇；这已经完整覆盖提案要求的
latent control、task-relevant prediction、tokenized/interactive generation、
occupancy world modeling、future-observation supervision 和 implicit-WM
evaluation。引用数 30 本身没有科学意义。

## 10. 现有 22 篇的候选职责复核

| Key/工作 | 候选中的职责 | 裁决 |
|---|---|---|
| `requenamesa2021earthnet` | guided EO video-prediction task | supported |
| `benson2024multimodal` | vegetation dynamics、temporal shift、Contextformer | supported |
| `diaconu2022weather` | weather-input value 与 output-level response | supported |
| `shi2015convlstm` | recurrent spatiotemporal prediction background | supported；不是 TerraState 同协议证据 |
| `wang2017predrnn` | recurrent predictive learning background | supported |
| `gao2022simvp` | convolutional/video prediction background | supported |
| `gao2022earthformer` | transformer Earth-system forecasting background | supported |
| `voleti2022mcvd` | stochastic/multiple-future video prediction | supported |
| `zhao2024vegediff` | probabilistic vegetation forecasting | supported；正式年份仍为 2025 |
| `shinohara2025vitkoop` | compressed EO state + Koopman transition | supported |
| `luo2026eowm` | structured weather forcing + probabilistic EO/output diagnostics | supported；preprint |
| `iele2026vegsim` | latent vegetation state + weather-conditioned recurrent scenario rollout | supported；preprint |
| `albughdadi2026observability` | future acquisition observability，不是 land-surface pixels | supported；preprint |
| `ha2018worldmodels` | compressed recurrent world model / policy learning | supported after coherent formal-version switch |
| `hafner2019planet` | latent dynamics for planning from pixels | supported |
| `hafner2020dreamer` | latent imagination for behavior learning | supported |
| `littman2001predictive` | state through future observables | supported with no classical-PSR guarantee transferred |
| `assran2023ijepa` | representation prediction without raw-pixel reconstruction | supported |
| `bardes2024vjepa` | video representation prediction | supported |
| `yang2026latenttsf` | accurate forecasts with temporally disordered latents | supported |
| `saanum2024simplifying` | action effects / state-invariant latent dynamics in control | supported with control-setting qualifier |
| `wang2022pvtv2` | Method 中 PVT v2 backbone identity | supported；不需要塞入扩充的 Related Work |

现有 22 篇不需要因本次扩充而删除。Deep-OSG/group-action 两个未使用 BibTeX 项也
不得恢复到正文。

## 11. 主张—证据边界

| 候选主张 | 文献/方法支撑 | 最大允许表述 | 越界检查 |
|---|---|---|---|
| world-model research spans several paradigms | control、planning、interactive generation、occupancy work | 明确为本文综合分类 | 不写成学界唯一 taxonomy |
| TerraState belongs in world-model context | explicit state、weather-conditioned transition、readout、test interfaces | bounded predictive-state EO world model | 不赋予 control/planning/generation |
| future-observation supervision can shape internal state | PSD + current future-state anchor | training lineage and motivation | 不宣称 PSD 证明 TerraState load-bearing |
| output diagnostics may miss internal-state defects | LatentTSF + scoped Vafa evidence | motivates dedicated state evidence | 不把 Vafa 的 automaton coherence 直接当 EO 结论 |
| EO-WM/VegSim already model forcing/scenarios | official preprints | fair complementary positioning | 不写它们不是 world models |
| TerraState tests state contribution | Method + Q2 | state removal primary；T→I supporting | 不写 all information passes through state |
| TerraState tests weather response/fidelity | Method + Q3 | actual-vs-frozen-control complete-window fidelity | 不写 causal/counterfactual validity |
| broader world-model lineage proves TerraState is universal | 无 | 禁止 | PASS：候选没有正向宣称，但防御语气需改 |
| Q4/composition | 无冻结证据 | 不进入正文 | PASS |

## 12. 页数与压缩风险

### 12.1 当前 PDF 的独立核验

- 当前 PDF：**8 页**；
- 第 8 页顶部仍有 Conclusion 最后 **2 行**，随后才开始 References；
- 第 8 页不是 references-only；
- 当前 22 条 References 约占 1.7–1.8 个双栏页面列；
- 因此当前稿在七页主文边界上已有最小越界。

### 12.2 扩充提案的估算

- 当前 Related Work：严格口径约 348 词；
- 提案候选：450 词；
- 净增加约 102 词；
- 8 条新增书目中 MuZero、Genie 等作者表较长，References 延伸到第 9 页是合理
  预期；
- 但“最终 9 页且第 8–9 页仅 References”尚未通过编译验证，只能写为目标。

### 12.3 三项压缩裁决

| 压缩项 | 保留核心信息情况 | 裁决 |
|---|---|---|
| Proposal Conclusion 109→64 词 | 保留 problem、interfaces、Q1–Q3 和 non-causal boundary，但删除 shared transition 与 future-state anchor | **P1，不可原样采用** |
| Proposal Limitations 150→91 词 | 保留 non-causal、non-counterfactual、hot-dry null、all-information boundary、single-dataset 和观测限制 | **可采用为篇幅候选** |
| Table 3 caption 49→34 词 | 保留 84 pairs、20-step window、符号方向、cluster CI、descriptive counts 和 subset metrics | **仅编译仍越界时使用** |

### 12.4 更安全的等量原则

1. 先删除 P2 中没有独立职责的 DreamerV3/TD-MPC2 scaling 句；
2. 保持四段总词数约 405–420，而不是把 450 当硬下限；
3. Limitations 可采用提案的 91 词压缩；
4. Conclusion 必须保留 shared transition 与 future-state anchoring，可压缩重复
   修饰语而不能删除身份组件；
5. 只有编译后主文仍越过第 7 页，才使用 Table 3 caption 候选；
6. 不改字号、行距、页边距、模板、图内内容，不使用负 `vspace`。

采用约 410 词 Related Work + 安全的 Limitations/Conclusion 去重后，9 页目标
具有可行性；最终状态仍必须由正式编译确认。

## 13. 只用于审计建议的最小英文修订候选

以下候选不写入正文。它保留四段链条，删去无独立职责的 DreamerV3/TD-MPC2，
按本报告口径为 409 词；所有技术主张仍受当前 Q1–Q3 边界约束。

### Weather-conditioned EO forecasting

> Weather-conditioned EO forecasting predicts future land-surface observations
> from satellite histories, meteorology, and geographic context. EarthNet2021
> formalized this guided video-prediction setting, and
> GreenEarthNet/Contextformer refined it for vegetation dynamics and temporal
> shift \cite{requenamesa2021earthnet,benson2024multimodal}. Deterministic
> methods use recurrent, convolutional, or transformer predictors
> \cite{shi2015convlstm,wang2017predrnn,gao2022simvp,gao2022earthformer},
> whereas video-diffusion models represent multiple plausible futures
> \cite{voleti2022mcvd,zhao2024vegediff}. ViT-Koop advances a compressed EO
> state, and prior weather-response analysis perturbs meteorological inputs at
> the output level \cite{shinohara2025vitkoop,diaconu2022weather}. Across these
> strands, evidence centers on forecast outputs, with some studies also
> analyzing weather response or learned representations. This leaves a narrower
> question about whether an explicit internal state participates in the
> prediction path and responds to supplied weather.

### World models: latent dynamics to interactive environments

> World-model research supplies the broader context for this shift from output
> prediction to explicit internal state. A control-oriented lineage compresses
> observations and learns latent transitions for rollout, planning, or
> imagination \cite{ha2018worldmodels,hafner2019planet,hafner2020dreamer}.
> MuZero predicts planning-relevant policy, value, and reward
> \cite{schrittwieser2020muzero}. IRIS learns an agent inside a tokenized world
> model, whereas Genie learns action-controllable environments from video
> \cite{micheli2023iris,bruce2024genie}. Drive-OccWorld connects
> action-conditioned occupancy forecasting to driving planning
> \cite{yang2025driveoccworld}. These examples share a
> state--transition--prediction structure but optimize different downstream
> objectives, motivating a task-specific account of predictive state in EO.

### EO world models and forcing-conditioned simulation

> In EO, this shared structure must be specialized to partially observed
> geospatial processes under external environmental drivers. Recent preprints
> make this connection explicit. EO-WM structures weather forcing for
> probabilistic EO forecasting and output-response diagnostics
> \cite{luo2026eowm}. VegSim rolls a latent vegetation state under
> user-specified weather for scenario-conditioned simulation
> \cite{iele2026vegsim}. A cloud-aware model instead predicts future observation
> availability rather than land-surface pixels
> \cite{albughdadi2026observability}. Here, future weather is an exogenous input
> for forecasting EO observations rather than the prediction target itself.
> Complementing these objectives, TerraState examines whether the state used by
> a weather-conditioned EO forecast makes a removable contribution and whether
> actual forcing yields greater complete-window fidelity than frozen controls.

### Predictive states and testability

> Predictive-state work asks how internal state is defined, supervised, and
> evaluated. Classical predictive-state representations define state through
> future observables, and Predictive-State Decoders explicitly supervise
> recurrent states to predict those observables
> \cite{littman2001predictive,venkatraman2017predictivestate}. I-JEPA and V-JEPA
> learn predictive representations without reconstructing raw pixels
> \cite{assran2023ijepa,bardes2024vjepa}. LatentTSF shows that accurate forecasts
> can coexist with temporally disordered latents
> \cite{yang2026latenttsf}, while PLSM constrains action effects in a control
> setting \cite{saanum2024simplifying}. In automaton-governed generative-model
> settings, dedicated evaluation further reveals incoherence missed by standard
> diagnostics \cite{vafa2024evaluating}. Together, these works motivate an
> EO-specific test: output accuracy alone cannot establish that an exposed
> state carries prediction or mediates weather forcing. Section 3 therefore
> constructs TerraState around an on-path predictive state, a shared
> weather-conditioned transition, and state-removal and weather-control
> interfaces that make this bounded claim testable.

该候选只改变叙事和文献职责，不改变：

- Q1 forecasting prerequisite；
- Q2 state removal primary / \(T\to I\) supporting；
- Q3 actual-vs-donor/mean complete-window fidelity；
- 非 causal、非 counterfactual、非 complete physical state、非 composition、
  非 SOTA 的边界。

## 14. P0/P1/P2 汇总与一轮最小返修集合

### P0（1）

1. 修正或删除 TD-MPC2：若保留，作者必须按官方 proceedings 写为 Nick Hansen。

### P1（7）

1. P1、P2 不再以 TerraState 结尾，消除两次叙事回退；
2. 删除无独立职责的 TD-MPC2；DreamerV3 也不作为引用数量目标保留；
3. 明确区分 IRIS 与 Genie 的实际职责；
4. 将 P2 `claims none` 改为 task-dependent objective 的正向收束；
5. 将 P3 `not a second version / without claiming` 改为
   `Complementing these objectives ...`；
6. 给 Vafa et al. 增加 automaton-governed generative-model scope；
7. P4 末句补回 on-path state 和 shared transition；Conclusion 压缩保留
   shared transition 与 future-state anchoring。

### P2（4）

1. `assess predicted observations` 可改为 `evidence centers on forecast outputs`；
2. 把 taxonomy 明确写成本文综合；
3. weather-as-forcing 用正向定义，避免引入未展开的 weather-model 综述；
4. 将 `observed-weather forecast` 统一为 `weather-conditioned EO forecast`。

完成上述 P0/P1 后，四段结构即可进入受控写入和正式编译门禁，不需要新一轮大规模
文献调研。

## 15. 五维自审

| 维度 | 当前提案 | 主要原因 |
|---|---:|---|
| Contribution positioning | 4.4/5 | 四段能解释 TerraState 的 EO predictive-state 生态位 |
| Writing clarity | 3.8/5 | 四次 TerraState 结尾和 P2/P3 防御句破坏递进 |
| Claim–evidence alignment | 4.4/5 | 大部分职责受支持；Vafa 范围需限定 |
| Citation necessity | 3.6/5 | PSD/Vafa 必要，但 DreamerV3/TD-MPC2 实际职责重复 |
| Method-design handoff | 3.9/5 | P4 有 testability，但未充分交给 on-path state/shared transition |
| Page-budget safety | 3.7/5 | 估算合理；Conclusion 压缩需修，最终必须编译 |

## 16. 最终判定与只读声明

**最终判定：REVISION_REQUIRED**

判定理由：

- P0 = 1；
- P1 = 7；
- 当前不满足“P0=0 且 P1=0 才能进入受控写入”的门禁；
- 问题均为一轮局部文献职责、过渡、语气和压缩调整，不需要改变论文主线。

本轮没有修改：

- `paper/main.tex`；
- `paper/references.bib`；
- `paper/main.pdf`；
- `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md`、`MANUSCRIPT_ZH_FULL.md`；
- 任何 Figure、Table、caption、实验结果或其他论文文件。

唯一新建文件为本独立审计报告。

# REVISION_REQUIRED
