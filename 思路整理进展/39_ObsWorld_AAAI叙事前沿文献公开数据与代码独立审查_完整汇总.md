# ObsWorld：AAAI 叙事、前沿文献、公开数据、实验闭环与代码问题独立总审查（v2 最终主线决议）

> 文档状态：独立总文档 / 后续工作的首要入口  
> 最后更新：2026-07-12  
> 研究对象：遥感世界模型（Remote-Sensing World Model，遥感世界模型）  
> 目标会议：AAAI  
> 重要说明：本文件不依赖任何聊天记录、会话编号或个人记忆。后续任何研究者、工程人员或智能体均应先阅读本文件，再按本文列出的绝对路径检查代码、数据和原始论文。

---

## 0. 文档身份、项目地址与使用规则

### 0.1 唯一需要记住的本地地址

| 内容 | 绝对路径 | 用途 |
|---|---|---|
| 项目根目录 | D:\Mine Program\codexwork\CVPRAAAI投稿 | 本项目全部材料的根目录 |
| 当前代码目录 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026 | 模型、数据、训练、评测与配置的真实实现 |
| 现有文档目录 | D:\Mine Program\codexwork\CVPRAAAI投稿\output | 历史方案、实验记录与本总文档 |
| 思路草稿目录 | D:\Mine Program\codexwork\CVPRAAAI投稿\idea | 未经完全验证的研究想法，只能作为候选，不是事实来源 |
| 本总文档 | D:\Mine Program\codexwork\CVPRAAAI投稿\output\39_ObsWorld_AAAI叙事前沿文献公开数据与代码独立审查_完整汇总.md | 后续继续本项目时的首要入口 |

后续工作不需要读取或依赖会话 019f3cef-4afc-7553-9b0c-5832ed8a9926，也不应要求用户重新交代历史上下文。需要的信息应从以下三类来源恢复：

1. 本文档：记录当前独立判断、风险、路线、实验逻辑和证据标准。
2. D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026：确认模型实际上做了什么。
3. 本文列出的论文、数据集官方页面和代码文件：核验随时间可能变化的信息。

### 0.2 证据优先级

发生冲突时，应采用以下优先级：

1. 实际代码、真实数据字段、可复现实验结果；
2. 数据集官方说明、论文原文、官方评测协议；
3. 本总文档中的审查判断；
4. output 中的旧文档；
5. idea 中的草稿和未经验证的设想。

output 和 idea 中的内容不能直接当作事实。特别是 33、34、35 虽然写成“最终”“定稿”，经本轮代码与前沿文献审查后，已经不能继续被视为真正终稿。当前正在运行的某个实验也不应反过来定义论文理论；可以先跑通工程，但最终论文结构必须由可验证的科学主张决定。

### 0.3 不可改变的项目边界

### 0.4 2026-07-13 v2 最终主线决议：本节优先于后文的旧 RQ 编号

> [!important] 本次修订的性质
> 本文档仍保留原始独立审查、代码问题和扩展实验记录，但从本节起，最终论文叙事、实验组织和实现优先级以本节为准。后文中将八组实验编号为 RQ1–RQ8 的写法，改视为扩展证据库；正文固定为四个核心研究问题。这样不是删除信息，而是避免首篇 AAAI 论文被过多外围目标淹没。

#### v2 的最终中心主张

> ObsWorld 是一个观测扎根的地表过程世界模型。它从稀疏、异构且受采集过程影响的遥感观测中估计预测性地表过程状态；在真实外生驱动轨迹下，以共享短步状态转移推进该状态；并将其解码为可被后续卫星观测核验的结果。

该主张保留“模拟真实世界发生什么”的目标，但仅声称可由公开数据检验的事实重演、事实预测和给定驱动下的条件推演。它不声称恢复绝对真实状态、严格因果反事实或完整地球模拟器。

#### v2 的符号分工

| 符号 | 角色 | 不能混淆为 |
|---|---|---|
| z | 预测性地表过程状态 | 已被直接测量的真实物理状态 |
| D | 随时间变化的外生天气驱动 | 日历、预测跨度或因果干预 |
| G | 静态地理背景 | 核心动力学贡献本身 |
| calendar 与 Δt | 季节和真实时间尺度 | 普通观测噪声 |
| φ | 已知观测过程条件 | 未来未知云或未来质量真值 |
| T | 共享短步状态转移机制 | 与 D、G、h 并列的新输入 |
| O | 观测模型或解码器 | 已被证实的半物理方程 |

#### v2 的模型决议：先成对比较，后选择单一最终机制

当前 Stage 2 定义为 Stage 2-D，也就是 direct multi-horizon prediction。它保留为强预测基线。新增 Stage 2-R，即用同一个短步 T 重复调用的 rollout 模型。

在第一轮正式比较中，二者必须是两套独立、严格配对的训练运行：

1. 同一 Stage 1.5 encoder 初始化；
2. 同一 observation decoder 架构和初始化；
3. 同一输入字段、mask、数据切分、参数量级、优化预算、随机种子集合；
4. 只改变动力学拓扑：Stage 2-D 一次预测终点，Stage 2-R 重复短步推进；
5. 两者均在真实未来和真实隐藏中间帧上评估。

不应在机制成立前，将二者混合成一个有 direct shortcut 的模型并只汇报其最好端点。这样的 hybrid 可以在 Stage 4 探索，但不能替代直接的机制检验。

最终论文只应按预注册式门槛选择一种主模型：

| 结果 | 最终选择与写法 |
|---|---|
| Stage 2-R 在 RQ3 明确成立，且 RQ1 与 direct 竞争或差距在置信区间/预设容忍范围内 | 以 rollout 作为 ObsWorld 主模型，direct 作为强基线 |
| Stage 2-R 的长跨度略弱，但在隐藏帧、驱动响应和同化上明显更强 | 论文明确分工：direct 用于端点预测，rollout 用于过程重演；不得声称 rollout 是所有指标最优 |
| Stage 2-R 对真实未来和中间帧均不成立 | 不用 hybrid 掩盖；保留 direct 并将论文降级为结构化条件预测，或停止强世界模型主张 |

#### v2 的四个核心研究问题

| 核心 RQ | 必须实验 | 直接证明 |
|---|---|---|
| RQ1：事实预测 | 官方 IID/OOD 主表、horizon 曲线 | 模型对真实发生的未来负责 |
| RQ2：状态—观测分工 | L1C/L2A 产品实验、语义/未来 probe、最终 checkpoint 重验 | z 不是简单产品外观，也没有丢掉有用地表信息 |
| RQ3：事实重演与可组合转移 | 遮挡清晰中间帧、direct/teacher-forced/free rollout | 同一短步机制能够跨越未观测区间重演过程 |
| RQ4：驱动与更新 | true/no/calendar/shuffle/wrong-year D；同化为增强 | 天气提供季节之外的事实预测信息；可选证明新观测能修正状态 |

原第 10 节中的 RQ5–RQ8，以及不确定性、主动采集、复杂半物理观测模型，全部转为补充材料或 Stage 4 增强项，不再阻塞首篇闭环。

#### v2 的下游与 Foundation Model 决议

独立下游任务不是发表必要条件。RQ1–RQ4 已经构成任务、机制、事实验证的闭环。为增强应用说服力，正文或补充材料应加入一个与主任务同源的决策相关评测，例如基于预测 NDVI 的植被衰退检测、衰退起始时间误差或严重度误差；它不需要训练另一个世界模型，也不应把论文引向建筑/洪涝等不同物理过程。

Foundation Model 的 2×2 是 Stage 4 的强增强项，而不是主线前置条件：轻量 encoder 与 Foundation encoder 分别搭配 direct 和 rollout。理想结果是 Foundation Model 在两种动力学头上均提高事实预测，且 rollout 相对 direct 的机制收益在两种 encoder 上均存在；最理想的右下角，即 Foundation encoder 加 rollout，在 RQ3/RQ4 最强并在 RQ1 保持竞争力。

#### v2 的优先级

P0：字段契约、DEM、mask、B8A adapter、probe、官方协议和消融配置。  
P1：重训不可旁路的 Stage 1.5，修复 Stage 2-D，新增并验证 Stage 2-R，完成 RQ1–RQ4。  
P2：同化、Foundation 2×2、EO-WM 专项诊断、极端/OOD 扩展。  
P3：不确定性、半物理几何、主动采集。

本项目始终是一个遥感世界模型，不应退化成普通天气条件预测器，也不应扩张成无法由公开数据支持的“完整地球模拟器”。最稳妥的研究对象是：

> 从异构、缺失且受采集条件影响的遥感观测中估计具有预测意义的地表状态，并在外生驱动轨迹下对该状态进行可组合的未来推演，必要时利用新观测更新状态。

---

## 1. 一页结论：现在能不能投 AAAI

### 1.1 结论

ObsWorld 的方向符合 AAAI 对方法型、机制型世界模型工作的基本口味，但当前 33–35 文档描述的方案和当前代码实现还不能直接支撑完整投稿。问题不是“遥感世界模型这个方向不行”，也不是“只有公开数据就做不了”，而是下列三件事同时存在：

1. 与最新 EO-WM 的表层叙事重叠已经很高；
2. 当前最独特的“状态—观测分工、组合动力学、同化更新”尚未被代码和专门实验坐实；
3. 现有实现及评测中有多项会使已有结果失去解释力的 P0 级问题。

因此最高成功率路线不是把现有文字润色得更像“世界模型”，而是把核心主张收紧到可被公开数据直接检验的机制，并让每一个主张都对应一组不可被普通预测主表替代的实验。

### 1.2 推荐中心主张

英文建议：

> ObsWorld learns an acquisition-robust predictive land-surface state from heterogeneous Earth observations and evolves it through compositional transitions conditioned on exogenous driver trajectories.

中文释义：

> ObsWorld 从异构地球观测中学习对采集条件更稳健、对未来具有预测能力的地表状态，并依据外生驱动轨迹对该状态进行可组合转移。

更通俗地说：卫星看到的影像不是地表本身，而是“地表状态经过传感器、太阳角度、大气、产品处理、云等观测过程以后形成的结果”。本模型希望先估计较稳定的内部地表状态，再让该状态随天气等外生条件演化，最后根据目标观测条件重新生成未来观测。

### 1.3 为什么这仍然不是 EO-WM 的简单复刻

EO-WM 已经把“部分可观测、天气驱动的遥感未来预测”做得很强，因此“我们也输入天气预测未来影像”不再足以构成新颖性。ObsWorld 应把贡献放在不同的正交轴上：

| 维度 | EO-WM 已经强覆盖的内容 | ObsWorld 应重点证明的内容 |
|---|---|---|
| 主任务 | 天气驱动的长期遥感预测 | 共享潜在地表状态的估计与演化 |
| 观测问题 | 部分观测、生成式预测 | 地表状态与观测条件的显式分工 |
| 动力学 | 大模型条件预测 | 可组合的状态转移，而非只按目标跨度直接回归 |
| 新观测到来 | 不是最突出的主线 | 状态同化/更新，即用新观测修正内部状态 |
| 大模型角色 | 大型扩散生成器是主体 | 大模型可作为编码/解码器，ObsWorld 贡献是机制 |
| 声明边界 | 天气驱动预测与可靠性 | 观测稳健状态、受控推演、组合一致性和状态更新 |

如果最终只实现“领域专用、外生驱动条件下的预测模型”，同时没有独立状态证据、组合转移或同化证据，那么用户关于“这不就和 EO-WM 一样了吗”的担心是成立的。只有将上述机制真正实现并直接验证，ObsWorld 才能保持自己的论文身份。

### 1.4 当前最紧急的六件事

在解释任何新结果前，应先完成：

1. 修复单通道 DEM 经 LayerNorm 后变成常数的问题；
2. 修复 B8A/NIR 波段索引错误；
3. 让观测解码必须经过 state bottleneck（状态瓶颈），不再绕开状态变量；
4. 让目标观测条件 φ 真正进入解码器，并重写无泄漏的 φ 探针；
5. 将 D、日历、h 和 G 拆清，避免 D 直接泄露目标跨度；
6. 统一 GreenEarthNet 官方数据身份和官方指标协议。

在这六项修复前，继续扩大训练规模只会更快地产生难以解释的结果。

---

## 2. 关键概念科普与严格边界

### 2.1 什么是世界模型

World Model（世界模型）不是一个只会生成未来图片的模型。对本项目而言，最低限度应包含：

1. State inference（状态推断）：从不完整观测估计内部状态；
2. State transition（状态转移）：内部状态随时间和外部驱动变化；
3. Observation model（观测模型）：同一内部状态在不同传感器或采集条件下会形成不同观测；
4. 可选的 Assimilation（同化/状态更新）：新观测到来后修正当前状态；
5. 可检验的 Rollout（推演）：能够连续或分段向未来推进，而不是仅记住目标天数对应的输出模板。

用符号表示：

~~~
状态推断：
qθ(s_t | x_≤t, φ_≤t, mask)

受控状态转移：
Tθ(s_t, u_t:t+Δ, c, Δ) → s_t+Δ

观测生成：
pψ(x_t | s_t, φ_t)

可选状态更新：
Aθ(s_prior, x_new, φ_new, mask_new) → s_posterior
~~~

其中：

- x：卫星观测影像；
- s 或 z：内部地表状态；
- φ：采集/观测条件，例如传感器、产品级别、太阳角、视角、云质量；
- u 或 D：随时间变化的外生驱动，例如温度、降水、辐射；
- c 或 G：相对静态的地理背景，例如高程、土地背景；
- Δ 或 h：时间跨度；
- mask：云、无效像素和缺测掩膜。

### 2.2 状态不是“绝对真实地球状态”

公开数据没有给出一个完美的真实潜状态标签。因此本文所说的 state（状态）应严格理解为：

> 对观测条件相对稳健、保留地表语义、并对未来有预测价值的内部表示。

不能写成：

- 恢复了唯一真实的地表物理状态；
- 完全解耦了所有观测因素；
- 建成了完整地球模拟器。

可以写成：

- acquisition-robust state（对采集条件更稳健的状态）；
- predictive state（预测性状态）；
- partially factorized observation/state representation（部分因子化的观测—状态表示）。

### 2.3 外生驱动不等于因果干预

Exogenous driver（外生驱动）是模型输入中由系统外部提供的时间轨迹，例如天气。模型在同一状态下替换两条天气轨迹，得到两个不同未来，只能证明 controllability（可控性）和 driver-conditioned response（驱动条件响应），不能自动证明 causal effect（因果效应）。

应严格区分：

1. Model scenario branch（模型情景分支）：同一 z 输入两条真实天气轨迹，看模型如何分支。证明模型能受条件控制。
2. Matched observational response（匹配观测响应）：匹配地点、季节、初始状态后，比较不同真实天气下的真实未来。提供较强的观测性证据。
3. Causal counterfactual（因果反事实）：同一地块在完全相同条件下同时经历两种天气并获得两个真实未来。现有公开观测数据不支持。

论文主线应停留在前两层，除非另加具有已知生成机制的合成/半合成实验和明确的因果识别假设。

### 2.4 组合动力学是什么

Compositional transition（可组合状态转移）是指长跨度转移可以由多个短跨度转移近似组成。例如：

~~~
直接推进：
z_100 = T(z_0, D_0:100)

分段推进：
z_30  = T(z_0,  D_0:30)
z'_100 = T(z_30, D_30:100)
~~~

如果 z_100 和 z'_100 都接近真实第 100 天状态，且彼此接近，说明模型更像可推进的动力学系统。只证明两者彼此接近还不够，因为它们可能“一致地错”。

### 2.5 同化是什么

Assimilation（同化）是指先根据历史观测得到一个预测状态；当未来某一时刻出现新的、可能有云或缺波段的遥感观测后，模型更新内部状态，再预测剩余未来。它比“把所有图像重新拼起来再预测”更能体现内部状态的作用，也是 ObsWorld 与普通一次性预测器拉开差距的潜在强点。

---

## 3. 现有训练方案、真实实现与原证明逻辑

### 3.1 原方案的总叙

原方案大体设计了三类训练阶段与多类实验：

- Stage 1 学习通用遥感编码；
- Stage 1.5 希望把地表状态 z 与观测条件 φ 分开，并通过重建、对齐和泄漏探针证明状态更稳健；
- Stage 2 使用历史状态、天气驱动 D、地理信息 G 和预测跨度 h 预测未来状态，再解码成未来多光谱影像。

原实验逻辑大体是：

1. 未来影像/NDVI 主表证明模型“能预测”；
2. D/G/h 消融证明条件模块“有用”；
3. φ 泄漏探针与跨模态对齐证明 z 更接近地表状态；
4. weather response（天气响应）实验说明模型会随天气改变预测；
5. uncertainty（不确定性）与 transfer（迁移）实验说明模型知道何时不可靠且状态可复用；
6. 多类证据共同证明 ObsWorld 是遥感世界模型，而不是普通预测器。

这个逻辑方向本身合理，但当前存在两个结构性缺口：

1. 多数证据仍是“最终预测变好”的间接证据，缺少对状态和转移机制的直接测试；
2. 文档中计划的若干能力在真实代码里没有实现，或者评测脚本无法支持相应结论。

### 3.2 当前 Stage 2 的真实数据流

根据 D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026 的当前代码，Stage 2 主要流程是：

~~~
GreenEarthNet / EarthNet 历史多光谱观测
    ↓
Stage 1.5 编码器
    ↓
历史状态 token
    ↓
上下文聚合器
    ↓
D / G / h 条件动力学
    ↓
若干目标时刻的未来状态 token
    ↓
EarthNetObservationDecoder
    ↓
未来 4 波段影像与 NDVI
~~~

当前主要损失是：

- observation loss（观测重建/预测损失）；
- NDVI loss（植被指数损失）；
- latent loss（潜状态监督）；
- delta loss（变化量损失）；
- smoothness loss（平滑损失）。

当前配置的大致权重为：

~~~
observation = 1.0
NDVI       = 0.5
latent     = 0.2
delta      = 0.1
smooth     = 0.02
~~~

相关配置：

D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\configs\train\stage2_earthnet_main.yaml

### 3.3 当前实现实际上能证明什么

在修复后、且按官方协议评测的前提下，当前直接多跨度 Stage 2 最多能证明：

> 一个由历史遥感表示、天气/地理/跨度条件驱动的未来多光谱与植被预测器具有一定性能。

它现在还不能充分证明：

- z 是经过有效状态瓶颈的观测稳健状态；
- φ 与 z 已经合理分工；
- D/G/h 各自独立贡献了预期信息；
- 转移能够按多个时间段组合；
- 新观测可以更新内部状态；
- 不确定性被真正学习并校准；
- 天气替换产生了正确而非仅仅敏感的响应。

---

## 4. 对 33–35“主线定稿”的独立复核

重点文档：

- D:\Mine Program\codexwork\CVPRAAAI投稿\output\33_ObsWorld AAAI最终叙事与实验闭环.md
- D:\Mine Program\codexwork\CVPRAAAI投稿\output\34_ObsWorld主线定稿与实验方案_全量整合翻新版.md
- D:\Mine Program\codexwork\CVPRAAAI投稿\output\35_ObsWorld方案关键问答与实现路线_全量整合翻新版.md

### 4.1 哪些判断可以保留

以下思想应保留：

- 项目始终围绕遥感世界模型，而不是普通气象预测；
- 将地表状态、观测条件、外生驱动、静态地理背景和时间跨度概念分开；
- 用公开数据建立多阶段证据链；
- 允许普通像素指标不是全部第一，但机制证据必须直接成立；
- 大模型可以承担编码/解码能力，ObsWorld 的贡献可以是状态与动力学机制；
- 需要 OOD（分布外）、极端事件、缺测和可靠性边界。

### 4.2 哪些表述已经过强

以下表述应降级或删除：

- “完全解耦地表状态与成像因素”改为“提高对采集条件的稳健性”；
- “真实世界状态”改为“具有地表语义和未来预测价值的潜状态”；
- “天气反事实/因果响应”改为“天气条件情景分支和匹配观测响应”；
- “D/G/h 消融即可证明动力学”改为“仅证明条件可能有用，还需组合转移和内部状态评价”；
- “主线已定稿”改为“候选主线，需 P0 修复与最小闭环验证后冻结”；
- “Stage 1.5 已证明 φ 泄漏降低”暂停使用，因为当前探针脚本存在致命评测问题。

### 4.3 世界模型概念是否被弱化

确实存在弱化风险，但不是因为使用了领域专用数据或外生驱动。一个世界模型可以是 domain-specific（领域专用）的，也可以依赖 exogenous inputs（外生输入）。真正的弱化发生在：

- 没有明确内部状态，只在图像特征上做回归；
- 没有可推进或可组合的状态转移；
- 观测模型不依赖明确状态瓶颈；
- 条件变化只改变输出，却没有正确性或一致性证据；
- 每个 horizon（预测跨度）都独立输出，无法连续 rollout；
- 新观测不能更新内部状态。

所以问题不是名称，而是行为证据。只要状态推断、状态转移、观测生成、组合性和可选同化中至少前三项被严格实现并验证，领域专用不会削弱世界模型身份。

---

## 5. 最新前沿重叠与差异化空间

### 5.1 EO-WM 是必须正面处理的最近邻工作

EO-WM 预印本发布于 2026-06-25：

- [EO-WM: Earth Observation World Modeling](https://arxiv.org/abs/2606.27277)

其已经覆盖：

- partially observed weather-driven world modeling（部分观测、天气驱动世界建模）；
- EarthNet 10 帧历史预测 20 帧未来；
- DEM 与时空元数据；
- climatology–anomaly decomposition（气候态—异常分解）；
- cumulative physical stress（累积物理胁迫）；
- Extreme Summer（极端夏季）和 Seasonal Matched-Pair（季节匹配对）基准；
- DHR、PDC 等响应指标；
- CRPS、coverage、spread–skill 等概率可靠性指标；
- 约 387M 参数的扩散模型。

因此，以下内容不能再单独作为 ObsWorld 的核心新颖点：

- 第一个天气驱动遥感世界模型；
- 第一个 EarthNet 条件长期预测模型；
- 第一个研究极端天气响应的遥感世界模型；
- 第一个做天气情景替换或匹配对的工作；
- 第一个做概率不确定性的工作。

如果采用 EO-WM 的基准或思想，应明确引用并写成“adopt/extend（采用/扩展）”，不能包装成自创。

### 5.2 其他拥挤的邻近工作

- [RS-WorldModel](https://arxiv.org/abs/2603.14941)：遥感世界模型与生成式建模路线。
- [Remote Sensing-Oriented World Model](https://arxiv.org/abs/2509.17808)：面向遥感的世界模型路线。

这说明“遥感 + 世界模型 + 未来生成”本身已经是拥挤赛道。ObsWorld 的标题、摘要、贡献点和实验必须落在可验证的结构差异上。

### 5.3 推荐差异化

最值得押注的三层差异是：

1. Observation/state factorization（观测—状态分工）：同一地表状态在 L1C/L2A、不同传感器或不同采集质量下形成不同观测。
2. Compositional controlled transition（可组合受控转移）：长跨度状态转移能由短跨度状态转移组成，并且二者都接近真实未来。
3. Assimilative state update（同化式状态更新）：新观测到来后更新内部状态，改善后续预测。

天气响应和不确定性仍可以保留，但应作为支撑项而非最核心新颖点。

---

## 6. AAAI 前沿论文的实验设计规律

### 6.1 共通闭环

对 AAAI-24、AAAI-25 和 AAAI-26 的相关工作审查后，可抽象出下列证据链：

~~~
中心主张
  ↓
普通任务能力：至少能完成目标任务
  ↓
模块必要性：去掉模块发生什么
  ↓
机制真实性：内部状态/响应是否按论文所说工作
  ↓
OOD 与压力测试：地域、时间、缺测、噪声、极端条件
  ↓
下游效用或可靠性：这种机制为什么值得存在
  ↓
适用边界：哪里失败，失败是否击穿中心主张
~~~

AAAI 并不要求所有传统指标第一，但中心主张必须有不能被普通预测主表替代的专门实验。负结果可以接受，只要它限制的是适用范围，而不是推翻中心机制。

### 6.2 15 篇高相关论文及可迁移经验

| 论文 | 主要实验设计 | 对 ObsWorld 的直接启示 |
|---|---|---|
| [ST-ReP, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/33465) | 6 个跨领域数据集；冻结表征后用 Ridge 等轻量头；低样本比例；组件消融与效率 | 声称 z 是状态，必须用冻结 z 和简单探针证明，不能只看复杂解码器 |
| [VQLTI, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/35070) | 24–120 h 多跨度；理想再分析输入与真实可用预报输入两套；潜空间诊断；物理约束消融 | 外部大模型可提供驱动，但要区分理想未来天气与实际可用天气，公开报告退化 |
| [Multi-source precipitation forecasting, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/35077) | 12→36 长序列；多阈值强降水指标；随时长退化曲线；视觉质量 | 允许某些指标不第一，但核心优势必须预先定义并在对应指标上成立 |
| [SatCLIP, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/32457) | 9 个任务；整洲 OOD；few-shot/zero-shot；10 次初始化 | 地域 OOD 要整块隔离；稳定统计比随机 patch 切分更重要 |
| [Drive-OccWorld, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/33010) | 未来状态预测→动作条件可控未来→规划收益；动作上界分析 | 世界模型身份来自预测、可控性和下游效用的链条，而非单一生成主表 |
| [GLAM, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/33880) | 显式状态变化；等容量控制；5 种子；rollout 长度敏感性 | 若声称状态变化，应直接评估 Δz 和长短转移，排除“只是模型更大” |
| [Causal Inference over Time, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/33626) | 观测预测与干预预测严格分开；合成已知系统；oracle；95% CI | 公开观测数据不能直接支持天气因果结论 |
| [GraFITi, AAAI-24](https://ojs.aaai.org/index.php/AAAI/article/view/29560) | 高缺失、不规则采样；5 折；异步和稀疏压力测试；明确失效模式 | 缺测/不规则时间应成为专门压力测试；可以承认明确失败区域 |
| [ST-FiT, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/33310) | 明确 RQ；目标节点全留出；5%–100% 数据曲线；3 种子 | 先定义 RQ，再让每张表回答一个 RQ；必须列清监督预算 |
| [LLMGeovec, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/33879) | 多任务、多 backbone 成对加模块；控制总维度；报告速度显存 | “大模型 + 我们机制”应做 2×2 成对实验，证明收益来自机制 |
| [Satellite augmentation study, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/35028) | 4 数据集、13 增强、5 次训练、统计显著性；大量负结果 | 系统性的混合结果也可成为贡献，但不能事后挑最好结果 |
| [Knowledge Boundary, AAAI-26](https://ojs.aaai.org/index.php/AAAI/article/view/39576) | 多领域、5 种子；不确定性随 rollout；风险筛选；ensemble 消融 | 不确定性必须与真实误差、OOD 和筛选后的风险下降相关 |
| [WorldAgen, AAAI-26](https://ojs.aaai.org/index.php/AAAI/article/view/38925) | 世界建模辅助头；去掉未来预测后下游行为显著下降；噪声鲁棒 | 证明世界建模目标有意义，最好展示状态对下游/适应有不可替代价值 |
| [Dynamic Sparsity, AAAI-26](https://ojs.aaai.org/index.php/AAAI/article/view/39658) | 直接审计动力学先验；报告不显著增益；明确条件边界 | 不应把“分离、稀疏、组合”当先验事实，必须独立审计 |
| [EOT-WM, AAAI-26](https://ojs.aaai.org/index.php/AAAI/article/view/38403) | CogVideoX-2B + 新控制机制；控制指标；未见轨迹；模块消融 | 使用大生成器不削弱原创性，前提是新机制有独立输入、损失和行为证据 |

补充可关注：

- [SparQT, AAAI-26](https://ojs.aaai.org/index.php/AAAI/article/view/39897)
- [SparseWorld, AAAI-26](https://ojs.aaai.org/index.php/AAAI/article/view/37347)
- [S²-KD, AAAI-26](https://ojs.aaai.org/index.php/AAAI/article/view/37091)
- [Learning Deep Dissipative Dynamics, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/34175)
- [LaNoLem, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/33269)
- [Cherry-Picking, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/34224)

Cherry-Picking 的核心警示是：只挑少量数据集会显著提高“某方法看起来最好”的概率；数据集从 3 个扩到 6 个后，错误识别最佳方法的概率明显下降。ObsWorld 不需要盲目堆数据，但至少应有“主动力学数据 + 状态证据数据 + 外部/OOD 数据”三种独立角色。

### 6.3 AAAI 对“不理想结果”的实际容忍边界

可以接受：

- 像素指标略逊，但机制指标、长跨度或强事件指标明显更好；
- 使用实际可得天气后比理想真值天气退化；
- 某些 zero-shot/OOD 场景没有增益；
- 不同 backbone 上增益大小不一，但方向大体一致；
- 明确定位到某类缺测、快速动力学或长跨度失败。

通常不可接受：

- 中心主张没有专门实验；
- 状态、动力学、可控性都不成立却继续称世界模型；
- 主要提升只来自更大参数量、更多预训练数据或更强 backbone；
- 用观测天气替换直接宣称因果；
- OOD 划分存在地点或时间泄漏；
- 只有少数漂亮案例，没有总体统计；
- 核心模块去掉后没有稳定差异。

---

## 7. 代码与评测的详细问题清单

本节按 P0/P1/P2 分类。P0 表示在解释主结果前必须修复；P1 表示形成 AAAI 最小闭环必须完成；P2 表示增强论文但可后置。

### 7.1 P0-1：单通道高程被 LayerNorm 消成常数

位置：

D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\adapters\geo_tokenizer.py，第 28–33 行附近。

问题：GeoTokenizer 对输入通道执行 LayerNorm(in_channels)。当 in_channels=1 时，每个位置只有一个标量，归一化后的均值就是该标量本身、方差为零，输出会退化为常数。当前 G=elevation（高程）因此几乎没有真正携带高程差异。

影响：

- 任何“G 有/无”的结论都不可解释；
- G 无增益可能是实现错误，不是地形无用；
- 模型可能只在使用归一化层的偏置。

建议：

- 对单通道连续变量先做全数据统计标准化或稳健分位数标准化；
- 使用 Linear/Conv 投影，不在单个标量通道维上做 LayerNorm；
- 在进入 tokenizer 前后打印每批次均值、标准差、最小/最大值；
- 做“原高程、随机高程、常数高程”三组测试。

验收：不同高程输入必须产生有差异的 geo token，且梯度能回到 geo 投影层。

### 7.2 P0-2：NIR 波段索引错误

位置：

- D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\data\datasets\earthnet2021.py，第 250 行附近读取 s2_B8A；
- D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\data\earthnet_fields.py，第 16–19 行附近，B08 为索引 7、B8A 为索引 8；
- D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\configs\train\stage2_earthnet_main.yaml，第 54–55 行附近却把 NIR 配为 7。

问题：数据实际使用 B8A，但 NDVI/NIR 配置指向 B08 的位置。若当前张量按 fields 顺序组织，则 NIR 应为索引 8。

影响：

- NDVI 计算可能使用错误波段；
- NDVI loss、主指标和所有植被结论都会被污染；
- 即使训练曲线正常，也不代表预测的是正确植被指数。

建议：

- 统一建立具名 band map，不再在配置里手写魔法数字；
- 添加单元测试：从已知红光/NIR 小张量计算 NDVI；
- 从真实样本随机抽取并和原 NetCDF/官方脚本逐像素核对。

### 7.3 P0-3：Stage 1.5 的状态瓶颈被重建路径绕开

位置：

D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\train\train_stage1_5_dual_conditioned.py，第 208–218 行附近。

问题：decoder 直接从 encoder 的 384 维 latent 重建，而 256 维 state_projector 只用于 alignment/nuisance loss。也就是说，重建不需要通过论文声称的状态 z。

影响：

- 不能证明 R(z, φ) 能从状态和观测条件重建；
- encoder 可把所有观测因素保存在旁路 latent 中；
- 即使 nuisance probe 下降，也不能说明解码器真正使用了“状态—观测分工”。

建议：

- 强制所有重建/预测经过 z：encoder → state projector → z → φ-conditioned decoder；
- 如确需保留高频 skip，应单独消融并限制 skip 不携带全局观测条件；
- 做 no-z、no-φ、bypass 和 bottleneck 维度消融。

### 7.4 P0-4：Stage 2 的 φ 实际未生效

位置：

- D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\dynamics\obsworld_stage2.py，第 87–92 行附近创建 neutral φ；
- D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\decoders\earthnet_observation_decoder.py，第 50 行附近只接收 state tokens。

问题：Stage 2 解码器没有使用目标时刻的真实观测条件 φ_future，而是固定中性条件或完全无条件。

影响：

- 当前 Stage 2 不是 p(x_future | z_future, φ_future)；
- 无法证明状态与观测条件分工；
- 预测误差可能混合了地表状态误差和观测过程误差。

建议：

- 明确未来目标 φ 包含哪些在预测时可用的字段；
- 将 φ 通过 FiLM、条件归一化或 cross-attention 注入 decoder；
- 对同一个 z 做 L1C/L2A 或不同合法 φ 的交叉解码；
- 不可在 φ 中放目标影像本身才知道的信息。

### 7.5 P0-5：现有 φ 泄漏探针不能作为论文证据

位置：

D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\eval\eval_phi_leakage_probe_fixed.py

具体问题：

- 第 75–86 行附近没有给 encoder 传真实 φ；
- 把第一个 patch token 当作 CLS 删除，但当前 encoder 没有 CLS；
- Stage 1 基线使用随机初始化的 state projector；
- 第 273–294 行附近用同一个 validation loader 训练和评价 probe；
- 因此可能同时存在表示抽取错误、基线不公平和数据泄漏。

影响：旧文档 28/29 中的 sun MAE、orbit accuracy、satellite accuracy 等数字不能继续作为正式证据。它们只能标记为“历史探索结果，已因评测缺陷失效，待重跑”。

建议：

- 固定 train/validation/test 三组空间独立样本；
- 对每个模型使用公平、确定且相同维度的表示；
- 明确 encoder 是否需要 φ，并按真实接口传入；
- 不删除不存在的 CLS；
- 线性 probe 与小 MLP probe 分开；
- 报告多个随机种子和置信区间；
- 语义 probe 与 nuisance probe 同时报告，防止模型只是丢失全部信息。

### 7.6 P0-6：D 与 h/日历严重混淆

位置：

D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\data\datasets\earthnet2021.py，第 822–856 行附近。

问题：D 包含从最后历史日期累积到目标日期的累积量，还包含目标 day-of-year（年内日序）。因此 D 本身泄露目标跨度和季节。删除 h 后性能不变，不能说明 h 无用；模型可能从 D 恢复 h。

建议将输入拆为：

- D_path：逐日或分段天气轨迹；
- Calendar（日历）：DOY、月份等周期信息；
- G_static：高程等静态背景；
- Δt：每一步实际时间间隔；
- h：只表示请求的目标跨度，或直接由转移步数产生。

消融必须是条件独立的：

- true D；
- no D；
- within-season shuffled D（同季节内打乱）；
- wrong-year D（同地点错年份）；
- calendar only；
- D without calendar；
- direct h head；
- stepwise transition。

### 7.7 P0-7：当前多跨度预测不是 rollout

位置：

- D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\dynamics\obsworld_stage2.py，第 121–133 行附近；
- D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\dynamics\state_dynamics_module.py，第 142–150 行附近。

问题：同一个 z_context 被复制给各个 horizon，各目标状态独立生成；核心模块在空间 token 上做残差变换，而不是把上一步预测状态作为下一步输入。

影响：

- 这是 direct multi-horizon prediction（直接多跨度预测），不是 sequential rollout（连续推演）；
- 不能做真正的 30+70 与 100 天组合；
- “动力学”表述会被审稿人质疑为条件回归。

建议：

- 实现共享的日步/5 日步 transition cell；
- 每步读取对应 D 片段和实际 Δt；
- 训练时混合 teacher forcing 与 free rollout；
- direct h-conditioned head 保留为强基线，而不是删除；
- 加 composition loss，但必须同时检查真实未来误差。

### 7.8 P0-8：训练目标编码器是移动的，存在循环监督风险

位置：

D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\dynamics\obsworld_stage2.py，第 142–152 行附近。

问题：每次 forward 复制 band adapter 状态，目标未来状态由同一个正在训练的 encoder/projector 产生，只做 stop-gradient，不是稳定的 frozen/EMA teacher（冻结/指数滑动教师）。

影响：

- 目标表示随训练移动；
- latent loss 可能被共同漂移或塌缩满足；
- 像素损失能部分抑制，但不能保证状态目标稳定。

建议：

- 使用 frozen target encoder 或 EMA teacher；
- 记录 target z 方差、协方差、范数和跨样本距离；
- 设置 collapse alarm（塌缩报警）；
- 最终在独立语义 probe 上验证。

### 7.9 P0-9：数据集身份和官方指标协议不一致

官方说明：

- [GreenEarthNet 官方仓库](https://github.com/vitusbenson/greenearthnet)

EarthNet2021x/en21x 是 GreenEarthNet 开发期名称，不是第三个独立数据集。当前代码的数据字段更接近 GreenEarthNet，但文档和评估仍大量围绕旧 EarthNetScore/ENS。

建议：

- 主动力学数据统一称 GreenEarthNet；
- 主表使用官方 clear-pixel、植被类别、观测数量和 NDVI 变化筛选；
- 主指标使用 R²、RMSE、NSE、absolute bias 和 climatology outperformance；
- 旧 EarthNet2021 ENS 仅作为单独的兼容性补充，不能混在同一主表。

### 7.10 P1：会削弱证据但不一定阻塞首轮训练的问题

1. 云/token 掩膜过松  
   D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\dynamics\obsworld_stage2.py，第 161–176 行附近，只要 patch 中超过约 5% 清晰像素就判有效。大部分被云遮挡的 patch 仍可能进入 latent supervision。应使用清晰比例加权或更严格阈值，并做阈值敏感性。

2. 上下文聚合器不理解不规则真实时间  
   D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\dynamics\context_state_aggregator.py 使用顺序式 learned time embedding，trend 主要是 last-first，没有真实天数间隔。若声称处理不规则观测，应显式输入时间戳/Δt，并做随机删帧、间隔扰动实验。

3. 天气响应脚本只测“敏感”，不测“正确”  
   D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\eval\weather_response_stage2.py 主要统计 NDVI 均值差和像素变化。一个错误模型也可能对天气非常敏感。应加入真实未来、matched pairs、错误年份天气和方向一致性；天气变量组合必须来自真实轨迹，避免人为构造物理不一致情景。

4. 天气脚本的数据接口可能与当前数据不一致  
   脚本要求 external-driver-root，但当前 NetCDF 已嵌入天气。应统一驱动读取接口，先在小样本上校验时序、单位和日期。

5. 验证主指标仍偏向 MAE  
   当前配置的 primary metric 不是 GreenEarthNet 官方核心指标，也不是机制/OOD 指标。保存最佳模型时应同时监测官方主指标与状态/组合验证指标，避免只优化像素平均误差。

6. Stage 2 解冻 encoder 可能破坏 Stage 1.5 性质  
   当前配置在 Stage 2 后期解冻 encoder。若这样做，必须在最终 Stage 2 checkpoint 上重跑全部状态/φ 探针，或使用冻结、EMA、SSL4EO replay 避免遗忘。

7. 不确定性尚未实现  
   stage2_earthnet_main.yaml 中 predict_logvar=false，损失也没有消费 logvar。文档中的 uncertainty 目前只是设想，不能写成已具备能力。

### 7.11 P2：增强项

- 增加 assimilation/update 模块；
- 增加 ensemble 或 calibrated probabilistic head；
- 加入 AnySat/TerraMind 等 foundation encoder 2×2 测试；
- 加入 DeepExtremeCubes 外部极端验证；
- 加入 DynamicEarthNet 或 FLUXNET 独立语义验证；
- 加入性能、显存、吞吐和参数量报告；
- 建立每个数据字段的单位、缺测、缩放和时间对齐自动测试。

---

## 8. 公开数据审查：能解决什么，不能解决什么

### 8.1 总判断

只有公开数据不是致命问题。AAAI 大量论文完全建立在公开基准上。真正限制来自：没有单个公开数据集同时提供多传感器、多观测条件、连续未来影像、稠密外生驱动、独立真实地表状态和受控天气干预。

因此最高成功率方法是“分组件验证、共享状态接口”：

~~~
SSL4EO-S12 v1.1
  → 观测条件与共享状态的部分分离

GreenEarthNet
  → 外生驱动下的状态转移与主预测能力

DeepExtremeCubes
  → 全球、极端和事件外泛化

DynamicEarthNet 或 FLUXNET
  → 独立动态语义或生态物理意义
~~~

关键约束：这些实验必须共享同一套 state interface（状态接口）和尽量相同的最终编码器/checkpoint。若在 SSL4EO 和 GreenEarthNet 上训练两个完全不同、互不相连的模型，它们不能共同证明一个统一世界模型。Stage 2 后必须重新验证 Stage 1.5 的状态性质，或采用 frozen/EMA encoder 和 SSL4EO replay。

### 8.2 数据集角色总表

| 数据集 | 最适合承担的证据 | 可以严格声称 | 不能声称/主要风险 |
|---|---|---|---|
| SSL4EO-S12 v1.1 | 状态—观测分工、跨产品表示、语义 probe | 对 L1C/L2A 产品处理条件更稳健，保留 LULC/NDVI 语义 | 不能证明绝对真实状态；S1/S2 通常非同时 |
| GreenEarthNet | 主动力学、驱动条件预测、组合性、时空 OOD | 外生驱动条件下的植被状态/观测预测 | 不能证明天气因果；主要是欧洲生长季 |
| 原始 EarthNet2021 | 旧 guided forecasting 兼容基准 | 在已知未来观测天气下的未来影像预测 | 云掩膜与 ENS 协议较旧；不是运营天气预报 |
| DeepExtremeCubes | 全球极端与事件 OOD | 极端条件下的关联预测、事件外泛化、驱动一致响应 | 极端过采样、空间自相关强；无真实反事实 |
| SEN12MS-CR-TS | 云与多模态压力测试 | 自然云污染下的状态鲁棒性 | S1/S2 最多相差约两周；无云目标可能来自另一时刻 |
| DynamicEarthNet | 独立动态语义、变化检测 | 潜状态包含土地覆盖并跟踪月尺度变化 | 无天气驱动；Planet Fusion 是融合产品 |
| CropHarvest | 农业语义外部 probe | 全球作物/非作物或作物类型迁移 | 标准数据是点级 12×18 特征，不适合空间动力学 |
| FLUXNET/FluxnetEO | 独立生态物理 probe | z 是否包含 GPP/ET/NEE 等生态信息 | 像素与通量塔足迹尺度匹配较难 |

### 8.3 SSL4EO-S12 v1.1

来源：

- [SSL4EO-S12 v1.1 论文](https://arxiv.org/abs/2503.00168)
- [SSL4EO-S12 v1.1 数据卡](https://huggingface.co/datasets/embed2scale/SSL4EO-S12-v1.1)
- [官方仓库](https://github.com/DLR-MF-DAS/SSL4EO-S12-v1.1)

规模与内容：约 246,144 个地点，每地点四季，包含 Sentinel-1 GRD、Sentinel-2 L1C/L2A、RGB、NDVI、DEM、LULC 和云掩膜。

最干净的配对不是 S1/S2，而是同一次 Sentinel-2 采集对应的 L1C 和 L2A。二者共享采集时间和地表内容，但产品处理不同，适合直接测试：

~~~
E(L1C) → z → O(z, φ_L1C) → L1C
E(L1C) → z → O(z, φ_L2A) → L2A
E(L2A) → z → O(z, φ_L1C) → L1C
E(L2A) → z → O(z, φ_L2A) → L2A
~~~

注意事项：

- S1/S2 可能相差数日到二十多日，不可直接当完全相同状态；
- NDVI 来自 S2 波段，是相关语义而非独立真实状态；
- LULC probe 只评价 clear pixels，排除云、阴影、雪和无数据；
- 按城市或空间块切分，不能随机 patch；
- 官方曾修复 S1 时间排序，应使用修复版或本地按时间戳核验。

### 8.4 GreenEarthNet

来源：

- [CVPR 2024 论文页面](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html)
- [论文 PDF](https://openaccess.thecvf.com/content/CVPR2024/papers/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.pdf)
- [官方仓库](https://github.com/vitusbenson/greenearthnet)

它应成为主动力学数据，提供：

- 10 个历史和 20 个未来的 5 日 Sentinel-2 序列；
- 约 150 天逐日天气；
- 风速、相对湿度、短波辐射、降水、海平面气压、平均/最低/最高温；
- 较可靠云掩膜；
- OOD-t、OOD-s、OOD-st；
- R²、RMSE、NSE、bias、climatology outperformance。

公开强基线 Contextformer 的大致结果：

- R²：0.62；
- RMSE：0.14；
- NSE：0.09；
- absolute bias：0.09；
- climatology outperformance：66.8% ± 0.3，三种子。

严格限制：

- 目标期间使用的是已观测天气，不等于实际部署时可获得的未来天气预报；
- 收割、火灾、灌溉、管理等未观测因素仍影响未来；
- 因而应称 guided/driver-conditioned forecasting（驱动条件预测），不能称严格天气因果。

### 8.5 原始 EarthNet2021

来源：

- [EarthNet2021 论文](https://arxiv.org/abs/2104.10066)

可作为旧基准兼容，但不建议继续作为主数据身份。旧 ENS/EarthNetScore 可以放补充材料，主文应切到 GreenEarthNet 的官方协议。还需明确：

- EarthNet2021x/en21x 是 GreenEarthNet 的开发名；
- 已知未来天气属于理想 guided setting（带真实未来驱动的理想设置）；
- 不能据此声称生产环境季节预测能力。

### 8.6 DeepExtremeCubes

来源：

- [DeepExtremeCubes 数据论文](https://arxiv.org/abs/2406.18179)

约 4 万个全球 minicube，覆盖 2016–2022，包含 Sentinel-2、ERA5-Land、复合高温—干旱事件、DEM、LULC 和云掩膜。

它是最值得加入的第三个数据集，因为能测试欧洲常规生长季之外的全球、极端、事件外泛化。必须：

- 使用官方空间折；
- 增加 event-ID holdout；
- 正常/极端分别报告；
- 不随机切分；
- 不把 2022 年无标签日期自动当非极端；
- 不用输入中的 ERA5 去预测同样由 ERA5 定义的事件标签并称为机制证据；
- 说明数据对极端区域过采样，必要时分层或重加权。

### 8.7 SEN12MS-CR-TS

来源：

- [官方页面](https://patricktum.github.io/cloud_removal/sen12mscrts/)
- [论文](https://arxiv.org/abs/2201.09613)

适合作为 cloud stress test（云压力测试），比较清晰输入、云污染输入和 S1 辅助输入得到的 z。但不能当严格同状态真值，因为 S1/S2 和所谓无云目标可能来自不同日期。

### 8.8 DynamicEarthNet

来源：

- [CVPR 2022 论文](https://openaccess.thecvf.com/content/CVPR2022/html/Toker_DynamicEarthNet_Daily_Multi-Spectral_Satellite_Dataset_for_Semantic_Change_Segmentation_CVPR_2022_paper.html)

包含 75 个全球 AOI、2018–2019 每日 Planet Fusion 多光谱影像和每月七类人工 LULC。适合做：

- frozen z 的 LULC probe；
- z 变化与人工标注变化的同步性；
- 稳定区域状态稳定、真实变化区域状态变化；
- Sentinel-2 到 Planet 的跨传感器迁移。

它没有天气驱动，不适合作为主动力学训练集。

### 8.9 CropHarvest 与 FLUXNET

- [CropHarvest 官方论文页](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/54229abfcfa5649e7003b83dd4755294-Abstract-round2.html)
- [CropHarvest 官方仓库](https://github.com/nasaharvest/cropharvest)
- [FluxnetEO 数据论文](https://bg.copernicus.org/articles/19/2805/2022/)
- [FLUXNET 数据系统](https://fluxnet.org/fluxnet-data-system/)

CropHarvest 标准处理是点级 12×18 月度特征，若论文不强调农业迁移，优先级低于 DynamicEarthNet。FLUXNET 能提供更独立的 GPP、ET、NEE 生态物理证据，但需要处理通量塔足迹和卫星像素的尺度匹配，适合 P2。

### 8.10 公开数据的最终边界

公开数据足以证明：

- 观测条件稳健性；
- 地表语义保留；
- 外生驱动条件预测；
- 组合状态转移；
- 地域、时间、极端和事件 OOD；
- 新观测同化是否改善未来预测；
- 不确定性是否与实际误差相关。

公开数据不足以直接证明：

- 唯一、绝对真实的内部地表状态；
- 天气对地表变化的严格因果效应；
- 完整物理地球模拟器；
- 在未知未来天气条件下的实际运营效果，除非额外输入真实可获得的天气预报产品。

---

## 9. 推荐的新模型框架

### 9.1 总体表述

原方案是“历史遥感表示 + D/G/h → 各未来时刻表示 → 未来影像”。推荐方案是在保留已有编码器和主要训练资产的基础上，将它改造成：

> 观测条件感知的状态推断器先从异构、缺失观测中形成共享地表状态；共享的短步转移单元按真实外生驱动轨迹推进该状态；观测解码器再依据目标采集条件生成未来观测；当中间新观测出现时，同化模块更新状态。状态分工、转移组合性、驱动有效性和同化收益分别由独立实验验证，共同支持遥感世界模型身份。

### 9.2 模块分解

#### A. State encoder（状态编码器）

~~~
z_t = qθ(x_≤t, φ_≤t, time_≤t, mask_≤t)
~~~

要求：

- 输入真实时间间隔，不只输入帧序号；
- 对缺测、云和不同波段使用显式 mask；
- 重建和预测都必须经过 z bottleneck；
- z 保留地表语义且减少产品/轨道等 nuisance（干扰）可恢复性。

#### B. Observation decoder（观测解码器）

~~~
x_hat_t = pψ(z_t, φ_target, mask_request)
~~~

要求：

- φ_target 必须真实进入解码；
- 同一 z 能生成不同合法产品/采集条件下的观测；
- φ 不得含只有看见目标影像才知道的信息；
- 在 SSL4EO L1C/L2A 上做交叉解码。

#### C. Controlled transition（受控状态转移）

推荐先实现共享 5 日 transition cell，而不是直接上复杂 Neural ODE：

~~~
z_t+5 = Tθ(z_t, D_t:t+5, G, calendar_t:t+5, Δt)
~~~

连续调用得到长跨度：

~~~
z_t+10  = T(T(z_t, D_0:5), D_5:10)
...
z_t+100 = T(...T(z_t)...)
~~~

为什么先用 5 日步：

- 与 GreenEarthNet 观测间隔自然对应；
- 实现、调试和对齐更简单；
- 容易做 direct vs composed；
- 比直接 h head 更像转移机制；
- 不需要为了“高级感”引入难以稳定训练的连续 ODE。

直接 h-conditioned head 应保留为 baseline（基线），用来证明共享步进机制的价值。

#### D. Assimilation/update（同化/更新）

~~~
z_prior    = rollout(z_t, D)
z_posterior = A(z_prior, x_new, φ_new, mask_new)
~~~

最低可行版本可以是 gated residual update（门控残差更新），不必一开始实现复杂 Kalman Filter。关键实验是：中间新观测到来后，更新状态是否使剩余未来预测更准，并且云更多时更新权重是否合理降低。

#### E. Stable target state（稳定目标状态）

未来 z 的监督使用 frozen encoder 或 EMA teacher。训练中监控：

- 每维方差；
- batch 内平均距离；
- 特征协方差谱；
- z 范数；
- 语义 probe；
- nuisance probe。

#### F. Uncertainty（不确定性）

不确定性暂列 P1/P2，不应挤占核心机制。优先采用：

- 3–5 个模型的 ensemble；
- 或简单 heteroscedastic head（异方差头）；
- 再做 uncertainty-error correlation、risk-coverage 和 OOD/horizon 趋势。

只输出 log-variance 而没有校准实验不构成贡献。

### 9.3 φ、D、G、calendar、h 的清晰分工

| 符号 | 中文 | 应包含 | 不应包含 |
|---|---|---|---|
| φ | 观测/采集条件 | 传感器、产品级别、太阳/视角、波段可用性、质量信息 | 目标地表语义、目标未来天气、可直接泄露标签的信息 |
| D/u | 外生驱动轨迹 | 逐日温度、降水、辐射、湿度等 | 目标 DOY、由目标跨度计算的隐式标识 |
| G/c | 静态地理背景 | DEM、坡度、可选静态土地背景 | 时间变化天气 |
| calendar | 日历 | DOY、季节周期、真实日期编码 | 天气累计量 |
| h/Δ | 时间跨度 | 实际推进天数/步数 | 重复塞入 D 的目标日期 |
| mask | 有效性 | 云、无数据、波段缺失、清晰比例 | 由预测误差反推的目标信息 |

建议把 season/DOY 从 nuisance φ 中移出，单独作为 calendar。季节既不是纯传感器干扰，也不是天气本身，它对植被状态演化有真实预测价值。

---

## 10. 完整实验链：每个实验证明什么，共同证明什么

### 10.1 总叙

推荐方案设计八组实验。实验 1 证明模型确实学到观测条件与共享地表内容的分工；实验 2 证明共享状态没有通过“丢掉一切”来伪装稳健，而保留地表语义和未来信息；实验 3 证明模型在标准公开任务上具有基本预测能力；实验 4 证明状态转移可以分段组合而不仅是按 h 直接回归；实验 5 证明真实外生驱动带来事实预测增益并能形成合理情景分支；实验 6 证明新观测能更新内部状态；实验 7 证明上述机制能迁移到地域、时间和极端事件分布外；实验 8 证明模型能够识别自己的可靠性边界。前两组证明 state，第三组证明 ordinary capability，第四和第五组证明 dynamics/controllability，第六组证明 world-model update，第七和第八组证明泛化与可用边界；它们共同证明 ObsWorld 是一个结构化遥感世界模型，而不是普通天气条件视频预测器。

### 10.2 RQ1：状态与观测条件是否真正分工

Research Question 1（研究问题 1）：

> 对同一采集的 L1C/L2A，模型能否用共享 z 表示共同地表内容，并用 φ 控制产品差异？

数据：SSL4EO 同采集 L1C/L2A，按城市/空间块隔离。

四向交叉解码：

~~~
L1C → z → L1C
L1C → z → L2A
L2A → z → L1C
L2A → z → L2A
~~~

基线/消融：

- no-φ decoder；
- separate encoders/decoders；
- shared encoder but no bottleneck；
- contrastive-only；
- 完整 shared z + φ-conditioned decoder；
- 不同 z 维度；
- 有/无高频 skip。

指标：

- clear-pixel MAE/RMSE；
- SAM（Spectral Angle Mapper，光谱角）；
- SSIM（结构相似度）；
- product probe accuracy（产品类型探针准确率，越低越好但不能牺牲语义）；
- clear-pixel LULC/NDVI probe（越高越好）。

理想证据：

- 完整模型交叉解码显著优于 no-φ 和 no-bottleneck；
- product probe 显著下降；
- LULC/NDVI 保留至少约 95% 的可用性能；
- 结论写“more acquisition-robust（更稳健）”，不要求探针降到随机水平。

### 10.3 RQ2：z 是否是有用状态，而不是压缩噪声

问题：

> 冻结 z 后，简单模型能否恢复地表语义并预测未来，同时难以恢复无关采集因素？

对比表示：

- Stage 1；
- 修复后的 Stage 1.5；
- 最终 Stage 2 checkpoint；
- 一个通用 EO foundation encoder，例如 AnySat；
- 原始像素统计或普通 autoencoder。

简单下游头：

- Linear/Ridge；
- 小 MLP；
- 不允许复杂 decoder 代替表示质量。

任务：

- LULC；
- NDVI/未来 NDVI；
- change/stability（变化/稳定）；
- product/satellite/orbit/sun-angle nuisance；
- 可选 DynamicEarthNet 人工变化或 FLUXNET GPP/ET。

必须在最终 Stage 2 后重跑，证明动力学训练没有破坏状态性质。

### 10.4 RQ3：标准未来预测是否达到基本竞争力

数据：GreenEarthNet 官方 IID、OOD-t、OOD-s、OOD-st。

基线：

- persistence（持续性）；
- previous year（前一年）；
- climatology（气候平均）；
- ConvLSTM；
- PredRNN；
- SimVP；
- Earthformer；
- Contextformer；
- 当前 direct h head；
- 推荐 stepwise ObsWorld。

指标：官方 R²、RMSE、NSE、absolute bias、climatology outperformance。必要时补充按 horizon 的 NDVI MAE、光谱误差和可视化，但不得替代官方主表。

该实验只证明“能预测”，不能单独证明世界模型。

### 10.5 RQ4：转移是否可组合且正确

比较：

~~~
Direct-100:
z_100 = F_direct(z_0, D_0:100, h=100)

Stepwise-100:
z'_100 = T_5(...T_5(z_0, D_0:5)..., D_95:100)

Chunked:
30+70, 50+50, 20+30+50
~~~

评价三种误差：

1. direct prediction error：z_100/其解码结果对真实未来；
2. composed prediction error：z'_100/其解码结果对真实未来；
3. composition gap：direct 与 composed 之间的差。

必要对照：

- 无 composition loss；
- 有 composition loss；
- 等参数 direct head；
- 共享 transition 与每跨度独立 head；
- teacher-forced 与 free rollout；
- 不同 rollout 长度。

通过标准：

- direct 和 composed 都优于简单基线；
- composition regularization 显著减少 gap；
- 主预测性能下降不超过约 2%–5%；
- gap 随跨度增长的曲线可解释。

如果只减少 direct/composed 差异但真实误差恶化，说明模型只是“一致地平滑/一致地错”，不能支持主张。

### 10.6 RQ5：D 是否真的贡献驱动信息

对照必须包括：

- true D；
- no D；
- within-season/geography shuffled D；
- wrong-year D；
- calendar only；
- aggregate-only D；
- historical-only D；
- true future observed weather；
- 若可行，真实天气预报产品输入。

响应实验：

- 同一 z 替换两条真实存在且匹配季节/地区的天气轨迹；
- 在真实 matched samples 上检查预测差异方向是否与观测未来差异一致；
- 按正常/极端和 OOD 分层；
- 不要独立修改温度、降水等统计量造出物理不一致天气。

能支持的结论：

> 真实外生驱动提高事实未来预测，并使模型产生与匹配观测一致的条件响应。

不能支持：

> 模型识别了降水/温度的严格因果效应。

### 10.7 RQ6：新观测能否同化到内部状态

数据：GreenEarthNet，可人为隐藏和释放中间帧。

协议：

1. 用前 10 帧得到 z_0；
2. 先预测到第 k 个未来时刻；
3. 提供该时刻的部分新观测；
4. 更新 z；
5. 预测剩余时段。

比较：

- no update；
- 把新影像直接追加历史后从头编码；
- gated state update；
- 完整 update + mask/φ；
- 清晰观测、云污染、波段缺失、不同比例 clear pixels。

指标：

- 更新后的剩余未来官方指标提升；
- posterior state 与真实未来 encoder state 的距离；
- 更新幅度与观测质量的关系；
- 新观测错误/严重云污染时是否过度更新。

这是非常有价值的世界模型证据。如果时间不足可放 P2，但若做成功，能明显区别于 EO-WM 式一次性预测。

### 10.8 RQ7：机制能否跨地域、时间和极端事件泛化

第一层：GreenEarthNet OOD-t、OOD-s、OOD-st。  
第二层：DeepExtremeCubes 官方空间折 + event-ID holdout。

分层报告：

- normal vs extreme；
- 不同植被类型；
- 不同大洲/气候带；
- 短、中、长 horizon；
- true D vs no-D；
- direct vs composed。

至少一个外部数据集必须出现正迁移，才能支持“不只适配单一欧洲基准”的结论。

### 10.9 RQ8：可靠性边界是否可识别

如果实现不确定性，最低实验：

- uncertainty 与逐样本真实误差的 Spearman/Pearson 相关；
- risk–coverage curve（风险—覆盖率曲线）；
- calibration/coverage；
- horizon 增大时不确定性是否合理上升；
- OOD/extreme/云增加时是否上升；
- 按不确定性丢弃高风险样本后，保留样本误差是否下降。

若不确定性实验弱，不要把它列为核心贡献；可将 failure detection（失败检测）留作补充或未来工作。

### 10.10 大模型 + ObsWorld 的 2×2 必要性

Foundation model（基础大模型）不是项目身份所必需，但对提升结果、验证机制可插拔性很有价值。建议至少选一个：

- [AnySat, CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Astruc_AnySat_One_Earth_Observation_Model_for_Many_Resolutions_Scales_and_CVPR_2025_paper.html)
- [TerraMind, ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/papers/Jakubik_TerraMind_Large-Scale_Generative_Multimodality_for_Earth_Observation_ICCV_2025_paper.pdf)

做下列配对：

| 编码/解码骨干 | 直接预测 | 加 ObsWorld 机制 |
|---|---:|---:|
| 轻量骨干 | A | B |
| EO foundation backbone | C | D |

解释：

- B>A：机制在轻量骨干上有效；
- D>C：机制在大骨干上仍有效；
- C>A：大模型本身能力更强；
- D 最好且 B、D 都有机制增益：最理想。

公平性要求：

- 尽量控制参数量/训练步数；
- 报告参数、显存、训练速度；
- 明确 foundation model 是否冻结；
- 不能只比较 A 与 D，否则无法区分大模型收益和机制收益。

最终表述：整个系统是遥感世界模型；ObsWorld 的论文贡献是 state/transition/assimilation mechanism（状态、转移和同化机制），foundation model 负责部分感知或生成能力。

---

## 11. 指标、统计、成功线与允许的不理想结果

### 11.1 主预测成功线

最低要求：

- 稳定优于 persistence 和 climatology；
- NSE 为正；
- climatology outperformance 超过 50% 才是最基本有效，目标应为约 60%–67% 或更高；
- OOD-s/t/st 不应只在一个划分偶然提升；
- 主结果至少 3 个随机种子。

若与 Contextformer 等强基线相差约 5%–10%，但状态分工、组合动力学、同化或极端泛化明显更强，仍可能形成一篇机制型 AAAI 论文。若连 climatology 都无法稳定超过，主动力学不成立，不能靠其他故事补救。

### 11.2 状态成功线

- nuisance probe 显著下降；
- LULC/NDVI/未来预测 probe 保留约 95% 或更高；
- L1C/L2A 交叉解码优于 no-φ/no-bottleneck；
- 最终 Stage 2 checkpoint 仍保有上述性质；
- 不要求 nuisance 降到随机，否则可能以损失真实信息为代价。

### 11.3 组合成功线

- composed rollout 和 direct prediction 都比简单基线准确；
- composition gap 通过正则后显著减小；
- 主预测技能下降不超过约 2%–5%；
- paired bootstrap 或 Wilcoxon 的置信区间/检验排除零效应；
- 报告 gap 随 rollout 长度的增长。

### 11.4 驱动成功线

- true D 在事实预测上稳定优于 no-D、shuffled-D、wrong-year-D；
- 增益在 OOD 或 extreme 上不应全部消失；
- 情景分支方向与 matched observational response 至少在总体上相符；
- 如果 D 只在 IID 上有微小增益，主张应降级为“条件辅助”，不能称核心动力学。

### 11.5 统计协议

- 主表、核心状态实验、组合实验和 D 对照至少 3 seeds；
- SatCLIP 类轻量 probe 可做 5–10 次不同 probe 初始化；
- 报 mean ± standard deviation 或 95% CI；
- 对同一样本的模型差异使用 paired bootstrap；
- 多 horizon 曲线同时报 effect size；
- 不以训练过程中曾出现的最好单点代替独立测试结果；
- 超参数只在 validation 选择，test 只运行最终冻结方案。

### 11.6 允许出现的不理想结果

- 像素生成不如大型 diffusion，但状态/动力学更可解释；
- G 平均增益小，但在空间 OOD 或山地子集有效；
- φ nuisance 未降到随机，但显著下降且语义保留；
- composition gap 随长跨度上升，但短中跨度显著改善；
- 一个 OOD 子集较弱，但总体仍超过简单基线且原因明确；
- 实际天气预报输入比真值天气退化；
- uncertainty 不够强，此时从核心贡献移除。

### 11.7 不允许出现的结果

- 主任务不能超过 climatology；
- true D 与 no-D/shuffled-D 无差异，却继续强调驱动；
- z 的 nuisance 下降伴随语义和未来预测大幅下降；
- direct/composed 彼此一致但都明显偏离真实未来；
- Stage 2 后所有状态性质消失；
- 只有随机 patch split 成功；
- 主要提升只能由参数量或 foundation backbone 解释；
- 不修复 probe 泄漏仍引用旧数字；
- 把模型敏感性写成真实因果规律。

---

## 12. 训练方案与实验安排的推荐重排

### 12.1 总体训练顺序

~~~
阶段 0：数据与评测审计
  → 修复 band、DEM、mask、日期、单位和官方指标

阶段 1：观测/状态因子化
  → SSL4EO L1C/L2A
  → 强制 z bottleneck + φ decoder
  → state/nuisance/semantic probes

阶段 2：受控动力学
  → GreenEarthNet
  → frozen/EMA target encoder
  → direct head baseline + shared 5-day transition

阶段 3：组合与驱动闭环
  → composition tests
  → true/no/shuffled/wrong-year D
  → OOD-t/s/st

阶段 4：增强世界模型身份
  → assimilation
  → DeepExtreme external/event OOD
  → foundation 2×2

阶段 5：可靠性与扩展
  → ensemble/uncertainty
  → DynamicEarthNet or FLUXNET
~~~

### 12.2 P0：任何正式结论之前

1. 修复 GeoTokenizer 单通道归一化；
2. 修复 NIR/B8A 索引并核对 NDVI；
3. 重构 Stage 1.5，重建强制经过 z；
4. 将 φ_future 接入 decoder；
5. 重写无泄漏 probe；
6. 拆分 D/calendar/h/G；
7. 实现稳定 target encoder；
8. 统一 GreenEarthNet 官方协议；
9. 建立小样本 overfit、shape、数值范围、mask、日期和单位测试；
10. 将旧 28/29 probe 结果标记为无效待重跑。

### 12.3 P1：AAAI 最小可投稿闭环

必须形成以下五张核心表/图：

1. SSL4EO L1C/L2A 状态—观测分工表；
2. 最终 z 的 semantic/nuisance/predictive probe 表；
3. GreenEarthNet 官方 IID/OOD 主表；
4. direct vs composed transition 图表；
5. true/no/shuffled/wrong-year D 驱动对照表。

另需：

- 至少 3 seeds；
- Contextformer 等强基线；
- 参数/计算公平性；
- 失败案例；
- 明确 causal boundary；
- 最终 Stage 2 后重跑状态实验。

仅做到 P1，如果五项核心证据都稳定，已经可能形成结构完整的 AAAI 投稿。

### 12.4 P2：提高上限

优先顺序：

1. DeepExtremeCubes 全球极端/事件 OOD；
2. assimilation/update；
3. AnySat 2×2；
4. DynamicEarthNet 或 FLUXNET 独立语义；
5. uncertainty/reliability；
6. 更大型生成器和高视觉质量。

### 12.5 8×H200 应该怎样使用

8×H200 解决算力，但不能补足数据中不存在的因果监督。最高价值用途不是只把一个模型放大，而是：

- 3–5 seeds；
- 多个严格 split；
- direct/stepwise/composition 消融；
- D 的多种负对照；
- 轻量与 foundation backbone 配对；
- OOD 与 extreme 分层；
- ensemble uncertainty；
- 大批量特征缓存和统一 probe。

建议先用单卡/少卡完成小规模正确性测试，再用多卡进行冻结方案。不要让分布式训练掩盖 band、mask、日期和数据泄漏等基础错误。

---

## 13. 论文主线、贡献与写作边界

### 13.1 推荐标题方向

示例，不是必须逐字使用：

> ObsWorld: Acquisition-Robust Predictive States and Compositional Dynamics for Earth Observation

中文：

> ObsWorld：面向地球观测的采集稳健预测状态与可组合动力学

避免把标题中心写成 Weather-Driven Earth Observation World Model，因为这会直接撞向 EO-WM 的主表述。

### 13.2 推荐摘要逻辑

1. 问题：卫星影像混合了地表变化与观测过程，现有条件预测器常把二者一起建模；
2. 缺口：这限制了状态复用、跨产品预测和可组合推演；
3. 方法：共享地表状态 + φ 条件观测模型 + 外生驱动共享转移，可选同化；
4. 实验：L1C/L2A 状态分工、GreenEarthNet 官方主表、组合性、驱动对照、OOD/极端；
5. 结论：不宣称绝对真实状态或因果，而宣称 acquisition-robust predictive state 和 compositional driver-conditioned evolution。

### 13.3 推荐三项核心贡献

1. 提出一个结构化遥感世界模型，将潜在地表状态、观测条件和外生驱动明确分工；
2. 提出/实现可组合的共享状态转移，并通过直接与分段推进、真实未来和驱动负对照进行专门验证；
3. 建立跨产品状态证据、官方主预测、时空/极端 OOD 和可选同化/可靠性组成的实验闭环。

如果 assimilation 没完成，不要写入核心贡献；可改为第三项的跨数据集验证协议。

### 13.4 可以使用的措辞

- acquisition-robust（对采集条件更稳健）；
- predictive land-surface state（预测性地表状态）；
- partially factorized（部分因子化）；
- driver-conditioned state evolution（驱动条件状态演化）；
- compositional transition（可组合转移）；
- scenario response（情景响应）；
- observationally matched response（观测匹配响应）；
- guided forecasting（带未来驱动的预测）；
- state assimilation/update（状态同化/更新）。

### 13.5 禁止或慎用措辞

- true/ground-truth latent state（真实潜状态），除非是合成数据；
- complete disentanglement（完全解耦）；
- causal effect/counterfactual（因果效应/反事实），除非满足因果识别；
- full Earth simulator（完整地球模拟器）；
- operational seasonal forecast（运营季节预报），除非用真实可得天气预报；
- first weather-driven EO world model（第一个天气驱动地球观测世界模型）；
- state-of-the-art（最先进），除非按同协议完整比较并显著领先。

---

## 14. 风险矩阵与失败后的降级路线

| 风险 | 发现方式 | 对主线影响 | 最佳处理 |
|---|---|---|---|
| φ probe 降不下来 | 独立 test probe | 状态分工变弱 | 改称观测条件感知状态；加强交叉解码而非完全解耦 |
| 语义与 nuisance 一起下降 | 双 probe | 核心失败 | 重构 bottleneck/损失，不能靠文字补救 |
| stepwise 预测弱于 direct | RQ4 | 组合动力学风险 | direct 作主预测；stepwise 限定短中跨度或改为 consistency regularizer |
| composition gap 小但真实误差大 | 真实未来对照 | 核心失败 | 增加 factual loss/teacher，不能称组合正确 |
| D 无增益 | D 负对照 | 驱动主张失败 | 检查时间、单位、泄漏与聚合；仍无增益则降级为无 D 状态模型 |
| G 无增益 | 修复后 G 消融 | 非致命 | 将 G 降为可选背景，不列核心贡献 |
| GreenEarthNet 不及强基线 | 官方主表 | 可容忍有限差距 | 若状态/组合/OOD 强，可定位机制论文；差距过大则先提升预测 |
| DeepExtreme 外部弱 | event OOD | 泛化范围缩小 | 诚实限定欧洲/植被域，分析域偏移 |
| foundation 只带来大模型收益 | 2×2 | 插件机制不成立 | 保留轻量主模型，不以大模型作为贡献 |
| uncertainty 不校准 | reliability | 非致命 | 移出核心贡献 |
| assimilation 无收益 | RQ6 | 可选贡献失败 | 放未来工作，不影响 P1 最小闭环 |

最关键原则：可以降级外围主张，不能掩盖状态和动力学核心证据的失败。如果状态分工和组合转移两者都无法成立，论文应停止使用当前强世界模型叙事，重新定义为条件预测方法。

---

## 15. 建议的论文实验表格布局

### Table 1：普通预测能力

GreenEarthNet IID/OOD-t/OOD-s/OOD-st，官方五指标，列清输入数据和未来天气是否可用。

### Table 2：状态—观测分工

SSL4EO 四向 L1C/L2A 交叉解码 + product probe + LULC/NDVI probe。

### Table 3：状态的预测充分性

Stage 1、Stage 1.5、最终 Stage 2、AnySat 等冻结表示，用 Ridge/Linear/MLP 预测未来与语义。

### Table 4：机制消融

no-φ、no bottleneck、no D、no G、calendar only、direct head、stepwise transition、no composition loss。

### Figure 1：组合动力学

30+70、50+50、20+30+50 的真实误差与 composition gap 随跨度曲线。

### Figure 2：驱动真实性

true/no/shuffled/wrong-year D 在 IID/OOD/extreme 的 paired effect；再展示有限的真实轨迹情景分支。

### Table/Figure 3：外部与可靠性

DeepExtreme event OOD，或 assimilation/update，或 risk–coverage。根据实现成熟度选择，不要把所有设想都塞进主文。

### Supplementary（补充材料）

- 旧 EarthNet2021 ENS；
- 更多可视化和失败案例；
- mask/阈值敏感性；
- 超参数；
- 单位与数据字段核验；
- 每个 seed；
- 计算开销；
- 不确定性；
- 更多 backbone。

---

## 16. 工程验收清单

### 16.1 数据层

- [ ] 波段名到索引只有一个权威映射；
- [ ] B8A/NIR 经真实样本核对；
- [ ] NDVI 与官方/独立计算一致；
- [ ] 天气变量单位、缩放、累积窗口全部核对；
- [ ] D、calendar、h 不互相泄漏；
- [ ] 真实日期和 Δt 进入模型；
- [ ] DEM tokenizer 输出非零方差；
- [ ] clear/cloud/no-data mask 语义统一；
- [ ] split 无地点、年份和事件泄漏；
- [ ] GreenEarthNet 官方样本过滤复现。

### 16.2 模型层

- [ ] 重建/预测强制经过 z；
- [ ] φ_target 真实进入 decoder；
- [ ] target encoder frozen 或 EMA；
- [ ] z 不塌缩；
- [ ] stepwise transition 真正读取上一步 z；
- [ ] 逐步 D 切片与日期对齐；
- [ ] direct baseline 与 stepwise 参数量记录；
- [ ] assimilation 使用 mask/φ；
- [ ] uncertainty 若声明则真正进入损失。

### 16.3 评测层

- [ ] probe train/val/test 分离；
- [ ] 不再删除不存在的 CLS；
- [ ] Stage 1 与 Stage 1.5/2 比较维度公平；
- [ ] 最终 Stage 2 checkpoint 重跑 probe；
- [ ] 官方 GreenEarthNet 指标；
- [ ] direct/composed 都对真实未来；
- [ ] D 有 no/shuffle/wrong-year 对照；
- [ ] 至少 3 seeds；
- [ ] paired statistics；
- [ ] OOD 和 extreme 分层；
- [ ] 负结果与失败案例保留。

### 16.4 论文层

- [ ] 摘要不声称绝对真实状态；
- [ ] 不把情景响应写成因果；
- [ ] 明确未来天气是真值还是预报；
- [ ] 正面引用 EO-WM；
- [ ] 每个 claim 对应一个专门实验；
- [ ] 大模型 2×2 排除骨干混淆；
- [ ] 所有表格协议和监督预算清楚；
- [ ] 旧 probe 结果不再使用。

---

## 17. 关键代码文件索引

后续无需依赖聊天记忆，直接按以下路径核查：

| 主题 | 文件 |
|---|---|
| Stage 2 主配置 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\configs\train\stage2_earthnet_main.yaml |
| Stage 2 总模型 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\dynamics\obsworld_stage2.py |
| 状态动力学模块 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\dynamics\state_dynamics_module.py |
| 上下文聚合器 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\dynamics\context_state_aggregator.py |
| EarthNet 观测解码器 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\decoders\earthnet_observation_decoder.py |
| 地理 tokenizer | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\adapters\geo_tokenizer.py |
| EarthNet/GreenEarthNet 数据读取 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\data\datasets\earthnet2021.py |
| 波段字段 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\data\earthnet_fields.py |
| Stage 1.5 训练 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\train\train_stage1_5_dual_conditioned.py |
| φ 泄漏 probe | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\eval\eval_phi_leakage_probe_fixed.py |
| 天气响应评测 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\eval\weather_response_stage2.py |
| 旧 EarthNet 指标 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\eval\earthnet_standard_metrics.py |

首次接手建议依次执行只读检查：

1. 阅读本文件；
2. 打开上述配置和核心模型；
3. 核对 P0 问题是否仍存在；
4. 查看 git diff/当前未提交改动，保护用户已有修改；
5. 查阅相应数据集官方协议；
6. 再决定修复和实验，不需要用户复述项目历史。

---

## 18. 中英文术语表

| English | 中文 | 本项目中的通俗解释 |
|---|---|---|
| World model | 世界模型 | 用内部状态描述系统，并让状态随条件向未来演化的模型 |
| Earth observation / EO | 地球观测 | 卫星、航空等对地表的观测 |
| Remote sensing | 遥感 | 不接触目标，通过传感器获取地表信息 |
| Latent state | 潜状态/内部状态 | 模型内部用于表示地表、不能直接看到的向量或 token |
| Observation model | 观测模型 | 内部状态在特定传感器/采集条件下如何形成影像 |
| State transition | 状态转移 | 当前内部状态如何变成未来内部状态 |
| Exogenous driver | 外生驱动 | 从系统外部提供、影响状态变化的天气等轨迹 |
| Acquisition condition | 采集条件 | 传感器、产品、太阳角度、视角、云等观测条件 |
| Nuisance factor | 干扰因素 | 与目标地表语义无关、但可能影响影像的因素 |
| Bottleneck | 瓶颈 | 强迫信息经过受限表示，防止旁路偷带全部信息 |
| Factorization | 因子化/分工 | 让不同变量承担不同来源的信息，不等于完全数学独立 |
| Disentanglement | 解耦 | 让因素尽量分离；公开数据通常只能证明部分解耦 |
| Rollout | 推演 | 将模型状态一步步向未来推进 |
| Compositionality | 组合性 | 多个短转移组合后接近一个长转移 |
| Assimilation | 同化 | 新观测到来后更新内部状态 |
| Teacher forcing | 教师强制 | 训练下一步时输入真实上一步状态 |
| Free rollout | 自由推演 | 下一步使用模型自己预测的上一步状态 |
| EMA teacher | 指数滑动教师 | 用参数的平滑副本提供较稳定的训练目标 |
| OOD | 分布外 | 测试地点、时间、事件等不属于训练分布 |
| IID | 同分布 | 训练和测试大体来自相同分布 |
| Probe | 探针 | 冻结表示后训练简单模型，检查其中含有什么信息 |
| Leakage | 泄漏 | 训练或输入中意外包含了测试/目标答案或替代线索 |
| Ablation | 消融 | 删除/替换某组件以判断它是否必要 |
| Baseline | 基线 | 用来公平比较的已有方法或简单方法 |
| Persistence | 持续性基线 | 假设未来与最后观测相同 |
| Climatology | 气候平均基线 | 用历史同季节平均作为未来 |
| Counterfactual | 反事实 | 同一对象在另一种干预下本会发生什么 |
| Causal effect | 因果效应 | 改变某因素本身导致的结果差异 |
| Scenario branch | 情景分支 | 模型在不同条件输入下生成不同未来，不等于真实因果 |
| Calibration | 校准 | 模型说 80% 可信时，长期看是否约 80% 正确/覆盖 |
| Risk–coverage | 风险—覆盖率 | 丢弃最不确定样本后，保留样本误差如何变化 |
| Foundation model | 基础大模型 | 用大规模数据预训练、可迁移到多任务的通用模型 |
| Backbone | 骨干网络 | 负责主要特征提取或生成的基础网络 |

---

## 19. 最终决策与后续继续规则

### 19.1 最终决策

1. 保留 ObsWorld 与遥感世界模型身份；
2. 不再把“天气驱动预测”当最主要新颖点；
3. 将中心改为“采集稳健预测状态 + 可组合受控状态转移”，assimilation 作为高价值增强；
4. 将 EO-WM 视为必须正面对标和引用的最近邻，而不是过度围绕它改写全文；
5. 使用 SSL4EO + GreenEarthNet 形成最小闭环，DeepExtremeCubes 作为最高价值外部数据；
6. 基础大模型不是必需，但建议做一个 2×2 以证明机制可插拔；
7. 公开数据足以支持 AAAI 叙事，但不支持绝对真实状态、完整地球模拟和严格天气因果；
8. P0 修复前，不将现有结果解释成正式科学结论。

### 19.2 后续最短行动路径

~~~
先修 P0
  ↓
在小数据上验证数值、mask、时间和状态瓶颈
  ↓
重跑 SSL4EO 状态/观测证据
  ↓
GreenEarthNet 官方主表 + D 负对照
  ↓
实现并验证共享 5 日转移与组合性
  ↓
最终 checkpoint 重跑全部状态 probe
  ↓
至少 3 seeds
  ↓
根据结果决定 DeepExtreme、assimilation、AnySat 和 uncertainty 的优先级
~~~

### 19.3 给后续接手者的明确说明

- 项目地址固定为 D:\Mine Program\codexwork\CVPRAAAI投稿；
- 代码地址固定为 D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026；
- 历史文档和本文件输出地址为 D:\Mine Program\codexwork\CVPRAAAI投稿\output；
- 草稿地址为 D:\Mine Program\codexwork\CVPRAAAI投稿\idea；
- 不需要用户再提供会话上下文；
- 不应依赖某个聊天任务的记忆；
- 不应盲信 output/idea，必须按代码、数据和论文核验；
- 当前正在运行的实验可以继续用于工程跑通，但不代表理论已经定稿；
- 任何修改都应围绕“遥感世界模型”这一不可变项目边界；
- 若本文件与最新代码冲突，应先记录冲突，再以可复现实现和真实实验更新本文件。

---

## 20. 最简明的总叙，可直接用于团队沟通

> 原方案通过 Stage 1/1.5 学习遥感表示并尝试分离状态 z 与观测条件 φ，再通过 Stage 2 使用天气 D、地理背景 G 和跨度 h 预测未来状态与影像；原计划以预测主表、D/G/h 消融、φ 泄漏、天气响应、不确定性和迁移共同证明遥感世界模型。独立审查发现，这一方向仍有 AAAI 价值，但当前实现存在状态瓶颈旁路、φ 未进入 Stage 2 解码、DEM 失效、NIR 索引错误、probe 泄漏、D/h 混淆和无真正 rollout 等关键问题，同时最新 EO-WM 已覆盖一般天气驱动遥感预测。因此推荐把论文中心收紧为“从异构观测中学习采集稳健、具有地表语义和未来预测能力的内部状态，并在外生驱动轨迹下进行可组合状态转移”，用 SSL4EO 证明状态—观测分工，用 GreenEarthNet 证明标准预测、驱动有效性和组合动力学，用 DeepExtremeCubes 证明全球极端/事件外泛化，并在最终 checkpoint 上重复状态验证；这些实验一个证明状态、一个证明普通预测能力、一个证明动力学、一个证明可控性、一个证明泛化，共同构成完整而不过度声称因果的遥感世界模型证据链。
