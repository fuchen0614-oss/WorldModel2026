# A10 · TerraState 面向 TIP 的叙事升级、实验图表与实施总纲

> **核对基线**：2026-09-04，代码提交 `8b616b4`，分支 `q4-eval-percube-eligibility`。  
> **事实来源优先级**：最新结果 JSON / 机械汇总表 > [A04 Candidate C 总账](./A04_TerraState_CandidateC_实现训练与实验总账.md)、[A06 Table 1 数值来源](./A06_TerraState_主表Table1_当前数值与来源.md)、[A08 E1 机械汇总](./A08_E1主表_同协议重跑结果.md) > 旧规划文档 > [AAAI 旧稿](../submission/main.tex)。  
> **本文定位**：在不否定现有 AAAI 成稿和代码基础的前提下，冻结一条面向 IEEE TIP 的主线，并把后续工作落实到模型、实验、图表和执行顺序。  
> **状态标记**：`已完成` 表示已有可追溯结果；`部分完成` 表示结论成立但统计或覆盖不足；`待完成` 表示尚未形成论文证据；`受阻` 表示当前缺少合法数据、权重或协议。

---

## 0. 先给结论：本项目现在是什么、还差什么

TerraState 不应再被写成“一篇研究遥感预测器内部状态是否有用的分析论文”，也不应只写成“在 Contextformer 上加入若干状态模块后提升预测精度”。面向 TIP，最合适的身份是：

> **TerraState 是一个面向天气驱动高分辨率地球观测序列的世界模型。它将历史观测压缩为显式空间预测状态，在外部天气驱动下持续推进该状态，并要求状态既真实承担预测、又能在分段推进、暂停继续和条件分支时保持一致。**

论文研究的不是“某个现有模型有没有世界状态”，而是**提出并验证一个具备可复用预测状态的遥感世界模型**。Q1-Q4 是证明模型具备这些性质的行为证据，不是论文的最终研究对象。

当前代码已经实现了这条主线的核心模型 `TerraState-C1`，Q1-Q4 均有正式结果，E1 的同协议基线重跑也已经完成。因此，当前问题不是推翻模型重来，而是完成四类闭环：

1. **统计闭环**：C1 从单种子补到多种子，C0R/C1 形成严格同预算对照；现有锁定 Q4 已在修正后的 pooled（汇总）端点口径上 19/19 通过，后续再做跨种子与独立数据确认。
2. **外部有效性闭环**：加入一个与 GreenEarthNet 真正独立的数据集，首选 EarthNet2023-Africa；EarthNet2021 只作为同源旧协议兼容实验。
3. **同期同行闭环**：在 Contextformer 等预测基线之外，正面回应 VegSim 与 EO-WM，区分密集空间状态、概率生成、天气情景和持续推进审计。
4. **论文表达闭环**：把旧 AAAI 稿中的“固定窗口、非递归、Q1-Q3”改写为“可推进状态、分段连续性、Q1-Q4”，并用 8 图 7 表将每项主张对应到直接证据。这里的 15 项不是数量指标，而是当前最完整且不重复的主文证据结构。

**客观判断**：这条叙事有资格支撑 TIP 级投稿，但不是仅凭当前单数据集和单种子结果就已经稳妥。它的强点是“世界模型定义可操作、模型机制与验证问题一一对应”；真正决定能否站住的，是后续能否证明这些性质不是 GreenEarthNet 上的一次性现象，也不是牺牲预测能力换来的实验构造。

---

# 第一部分：总纲

## 1. TIP 版本的唯一主线

### 1.1 科学问题：为什么这不是普通的遥感预测问题

#### 1.1.1 最终科学问题

> **在部分可观测、天气驱动的高分辨率地球观测场景中，能否构建一个遥感世界模型，学习真正面向未来的空间预测状态，使不同时间跨度的状态转移能够组合，并使中间状态继续承担后续预测？**

这句话同时固定了五个边界：

1. **研究对象是遥感世界模型**，不是对任意预测网络隐藏层的事后解释。
2. **观测条件是部分可观测**：云遮挡、时间采样稀疏以及未观测的人类活动意味着模型不能简单把最后一帧当成完整世界。
3. **动力学受天气驱动**：未来天气是外部 forcing（外生驱动），模型要在给定驱动路径下推进地表状态，但不把天气误称为 agent action（智能体动作）。
4. **核心建模对象是空间预测状态**：它不是网络计算中顺便产生、用完即丢的 hidden state（隐藏状态），而是需要被明确学习、持续更新、保存调用并接受行为检验的状态。
5. **关键性质是 continuation consistency（持续推进一致性）**：不同时间跨度的转移应当可组合，中间状态应当继续代表模型所理解的当前世界，而不是只能支撑一次固定窗口输出。

规划稿中可以用“一等建模对象”概括第 4 点，但论文正文建议换成更直接的表述：

> **TerraState 把空间预测状态作为模型的核心训练对象和运行接口，而不是一次性预测过程中的普通隐藏特征。**

#### 1.1.2 这个科学问题为什么有意义

现有遥感时序预测通常检验 `history -> fixed future`（历史到固定未来）的输出误差。该范式能够回答“模型在指定预测窗口内准不准”，却不能自动回答以下问题：

- 模型是否维护了一个能够代表当前地表条件的内部状态，还是每个终点都由历史特征直接重算；
- 中间状态是否包含继续预测所需的信息，还是只对本次输出有用；
- 同一未来天气路径被一次处理或拆成数段处理时，模型是否仍在模拟同一个世界；
- 状态保存后能否在不重新读取完整历史的条件下恢复、续推，并对另一条天气路径形成条件分支。

这些不是软件层面的“暂停按钮”问题，而是 **predictive state learning（预测状态学习）与 externally driven dynamics identification（外部驱动动力系统辨识）** 的问题。若直接推进和分段推进产生完全不同的终点，就说明转移算子可能只学会了“从初始历史到指定时距的捷径”，中间状态并未稳定表示正在演化的世界。反之，若一个状态同时满足预测充分性、状态承载、天气响应和跨时间分段组合一致性，它才更接近可运行的遥感世界状态。

其应用意义也必须克制而具体：可复用状态允许长时间序列被分批处理，允许在新天气预报到达时从当前状态继续，而无需重复编码完整历史；还允许从同一状态出发比较不同天气情景。本文证明的是这些操作的模型基础和预测一致性，不直接宣称因果推断、决策规划或完整地球系统模拟。

#### 1.1.3 “世界模型”在这里没有消失

`predictive state learning（预测状态学习）` 是 TerraState 的技术基础，不是替代“世界模型”的另一个论文类别。世界模型身份来自四个彼此关联的要素：

```text
观测历史 -> 显式空间世界状态
外部天气 -> 受驱动的共享状态转移
状态读出 -> 可验证的未来地球观测
状态接口 -> 保存、恢复、续推与条件分支
```

因此，本文的世界模型不是靠命名成立，而是靠一个可证伪的运行契约成立：状态必须真实承担输出（Q2），必须使用给定天气（Q3），并且必须在直接与分段推进下保持组合一致（Q4），同时维持合格预测能力（Q1）。

#### 1.1.4 最终主旨表述

> **TerraState 是一个面向高分辨率地球观测的天气驱动世界模型。它从稀疏且部分可观测的历史影像中学习显式空间预测状态，并通过共享的变跨度状态转移持续模拟地表未来。不同于仅生成固定长度未来序列的预测方法，TerraState 要求中间状态能够继续承担后续预测，并使同一天气路径下的直接推进与分段推进保持近似一致。**

真正的方法贡献应进一步压缩为：

> **通过 recursive factual supervision（递归事实监督），把“中间状态能够继续代表模型所理解的当前世界”写进真实预测监督路径，而不是训练完成后再临时检查一个 hidden state（隐藏状态）。**

这一定义使论文同时保持两种身份：在应用对象上，它是天气驱动的遥感世界模型；在可检验的技术问题上，它研究可复用空间预测状态及变跨度状态转移的组合性。

### 1.2 截至 2026-09 的研究版图：我们不是在真空中定义“世界模型”

目前与本项目最接近的工作已经不只是 Contextformer。至少需要区分四条路线：

| 路线 | 代表工作 | 主要对象与长处 | 尚未覆盖的核心问题 | 与 TerraState 的关系 |
|---|---|---|---|---|
| 高分辨率确定性预测 | [GreenEarthNet / Contextformer](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html) | 20 m 像素级植被预测，多模态上下文和强预测基线 | 主要按固定窗口输出与预测指标评价，没有把可恢复状态作为核心训练对象和运行接口 | TerraState 的预测底座与必须公平比较的强基线 |
| 概率式多光谱生成 | [EO-WM](https://arxiv.org/abs/2606.27277) | 128×128 多光谱概率预测，天气气候态/异常/累积胁迫建模，强调天气响应指标 | 公开论文的中心是生成分布和 forcing response（驱动响应），不是显式状态的 load-bearing（承载性）或 direct/segmented equivalence（直接/分段等价） | 与 Q3 高度相邻，迫使我们把独特性放在空间状态与 Q4 上 |
| 情景条件植被模拟 | [VegSim](https://arxiv.org/abs/2606.21961) | 从 minicube 聚合 NDVI 历史形成潜状态，以递归动力学输出分位数，并支持人为天气情景 | 当前输出与监督主要是 minicube 级聚合 NDVI；论文未把状态承载、保存后继续和分段一致性作为验证目标 | **最接近的直接同行**；“天气驱动递归潜状态”本身已不能作为我们的独有点 |
| 遥感理解与生成统一 | [RS-WorldModel](https://arxiv.org/abs/2603.14941) | 文本辅助的变化理解和未来场景生成，规模与任务覆盖广 | 不以天气驱动的连续地表状态估计为中心 | 名称相似但任务范式不同，不是最直接实验对手 |

由此，TerraState 的论文空位必须收紧为：

> **一个在 20 m 密集空间网格上运行的、天气驱动的可复用预测状态模型；其贡献不仅是能递归预测或更换天气，而是显式证明该空间状态真实承担像素级未来、能从中间状态继续运行，并在完整天气路径与任意分段路径下保持近似一致。**

这里的独特性是一个**组合型但不含糊的技术命题**：

```text
高分辨率空间状态
+ 状态真实承载输出（Q2）
+ 对已知天气路径产生可验证响应（Q3）
+ 直接/分段推进一致（Q4）
+ 普通预测精度不坍塌（Q1）
= TerraState 的可复用遥感世界状态
```

因此，后续引言不能再写“现有方法都不能响应天气”或“现有世界模型都没有递归潜状态”，这两句会被 EO-WM/VegSim 直接反驳。更准确的缺口是：**已有工作越来越会生成未来和操纵 forcing（外部驱动），但很少把高分辨率内部状态本身当作可保存、可续推、可审计的模型接口，也很少验证同一状态在不同时间分段下是否代表同一个持续世界。**


### 1.3 我们的准确定位

TerraState 不是通用地球系统模型，也不是包含大气、海洋、土地利用和人类活动全部变量的“完整世界”。它应被限定为：

> **a domain world model of satellite-observed vegetation dynamics（卫星观测植被动力学的领域世界模型）**

这个限定不会降低论文档次，反而能避免“只预测 NDVI 为什么敢叫世界模型”的攻击。世界模型的价值在于显式状态和可运行动力学，而不是变量数量越多越好。TerraState 的对象是遥感可见的植被/地表动态，天气是外部 forcing（驱动），未观测管理活动、灾害和传感器缺失构成不可约不确定性。

在相邻工作中，TerraState 应这样站位：

- 相对 Contextformer：从 fixed-window predictor（固定窗口预测器）提升为 stateful simulator（有状态模拟器）。
- 相对 EO-WM：不竞争大规模概率视频生成，而强调 dense reusable state（密集可复用状态）和 continuation audit（持续推进审计）。
- 相对 VegSim：不再声称首次做天气递归潜状态，而强调 **像素级空间状态 + load-bearing test（承载检验）+ segmented continuation test（分段续推检验）**。
- 相对通用遥感世界模型：聚焦一个可定量验证的物理/生态过程，不依赖文本想象质量或 FID 来定义“世界”。

### 1.4 建议标题

**TerraState: A Weather-Driven Earth Observation World Model with Continuation-Consistent Predictive States**

标题保留 `TerraState`，强调三个真正有辨识度的部分：

- `World Model`（世界模型）：明确本文构建模型，而不是只分析某个预测器的内部表示。
- `Continuation-Consistent Predictive States`（持续推进一致的预测状态）：状态可以继续预测，直接与分段推进近似一致，而不是一次性中间特征。
- `Weather-Driven Earth Observation`（天气驱动地球观测）：限定遥感场景与外源驱动，避免泛化成无边界的通用世界模型口号。

### 1.5 一句话贡献

> We introduce TerraState, a weather-driven Earth-observation world model that learns an explicit spatial predictive state which is load-bearing for forecasting, responsive to supplied future weather, and continuation-consistent under direct and segmented rollout.

对应中文：

> 我们提出 TerraState：一个天气驱动的地球观测世界模型。它学习显式空间预测状态，该状态真实承担未来预测、响应给定天气，并在直接推进与分段推进之间保持连续一致。

### 1.6 四项核心主张与证据

| 主张 | 它回答什么 | 主要证据 | 当前状态 |
|---|---|---|---|
| C1：预测能力 | 模型首先能否完成遥感多步预测，而不是只满足漂亮定义 | Q1、Table 1、Table 2、Fig. 3-5 | GreenEarthNet 已完成单种子；独立数据集待补 |
| C2：状态承载 | 最终输出是否真正依赖显式动态状态 | Q2、`full` vs `alpha=0/prior-only`、Fig. 6、Table 4 | 四个 split 均为 load-bearing，已完成 |
| C3：驱动响应 | 预测状态是否按提供的未来天气发生有意义变化 | Q3、actual vs donor/mean weather、Fig. 7、Table 5 | 响应保真成立；热旱特异性不成立 |
| C4：持续模拟 | 同一路径一次推进与分段继续是否到达相近状态/结果 | Q4、C0R vs C1、Fig. 8、Table 6 | C1 四门通过；修正后端点非劣 19/19 通过；待多种子和独立数据增强 |

四项主张之间的逻辑关系是：**会预测是入场券，状态承载说明不是旁路装饰，天气响应说明状态受外部驱动，分段一致性说明它能被持续推进。** 四者合起来，才使“世界模型”称谓比普通遥感预测器更可信。

### 1.7 数学上应当表达的性质

设历史观测编码为初始状态 `s_a`，未来天气路径为 `u[a:b]`，共享状态转移为 `T`。核心性质不是抽象地宣称“满足半群”，而是验证天气路径条件下的组合一致性：

```text
T_{u[a:c]}(s_a) ≈ T_{u[b:c]}( T_{u[a:b]}(s_a) )
```

直观含义：在同一段未来天气下，“直接预测 100 天”和“推进 30 天，保存状态，再继续 70 天”应当得到相近终点，并且两条路径都应保持预测准确。

对于当前带 context prior（上下文先验支路）的实现，运行时状态应诚实地定义为：

```text
runtime_state（运行时状态） = {context_prior（上下文先验）, dynamic_state z（动态状态）, geography（地理信息）, current_offset（当前偏移）}
```

由此可给出四个明确接口：

```text
initialize(history) -> runtime_state
advance(runtime_state, weather_segment) -> runtime_state'
decode(runtime_state) -> prediction
branch(runtime_state, weather_A/weather_B) -> alternative futures
```

这比声称“`z` 包含世界的一切”更准确，也与当前 `prior（先验预测） + alpha * O(z_h)（状态读出）` 的实现一致。

### 1.8 模型身份冻结

- **最终模型固定为 TerraState-C1**：历史编码、显式状态、天气/地理/时间条件、共享分段转移、状态解码。
- **PVT-v2/Contextformer 是视觉上下文骨干，不是主要创新点**。无需把论文写成 PVT 改进论文，也无需对 PVT 每层做穷尽消融。
- **C0R 是 C1 的关键同构控制组**：参数量、训练预算和模块相同，区别集中于 factual path 的 `direct` 与 `recursive`，用于证明持续推进能力来自训练机制，而非参数增加。
- **TerraState-V2 不再是 TIP 主模型，也不进入预测主表**：它只是开发历史中的前代参考。若版面允许，可在补充材料用一行说明从固定时距映射到 C1 的演进；若版面紧张，完全可以不报告 V2 数值。
- **Contextformer 是外部强基线/底座参照**：它回答普通预测器可以做到什么，不应伪装成 TerraState 内部的严格消融。
- **C2/C3 暂不升为主模型**：C2 可加入 latent direct/composed consistency，C3 再加入 output consistency；只有当它们多种子显著改善 Q4 且不伤害 Q1 时，才考虑替换 C1，否则放补充材料或不做。

### 1.9 TerraState-V2 到底还需不需要

直接答案是：**需要保留代码和实验档案，不需要保留为主文角色。**

TIP 主文从头到尾只把 C1 称为 `TerraState`。V2 有三个可能用途：

1. 在开发历史或补充材料中说明为什么从 direct horizon mapping（直接时距映射）转向 shared recursive transition（共享递归转移）。
2. 当审稿人问“相比 AAAI 版本新增了什么”时，作为内部版本证据。
3. 若 V2 已有结果且加入成本几乎为零，可放 `Table Sx`，但不要让它占主表行数、贡献点或摘要篇幅。

真正不可删除的是 C0R，因为 C0R 与 C1 构成干净机制对照；V2 不能替代 C0R。后续所有新训练、第二数据集和主图均优先 C1/C0R，不再为 V2 追加大规模实验。

### 1.10 中英文术语约定

为降低目前文档中英文切换造成的理解成本，规划稿中首次出现统一写成“English（中文）”；最终英文论文只保留英文，中文括注不进入投稿稿件。

| 英文术语 | 中文含义 | 本文使用边界 |
|---|---|---|
| world model | 世界模型 | 可维护状态并按驱动模拟未来的模型，不等于大模型 |
| reusable spatial predictive state | 可复用空间预测状态 | 能保存、续推、解码和分支的密集状态 |
| load-bearing state | 真实承载预测的状态 | 移除状态后预测显著退化，不是装饰变量 |
| weather forcing | 天气外部驱动 | 推进地表状态的外生输入，不称为 agent action（智能体动作） |
| direct rollout | 直接推进 | 从初态一次走到目标终点 |
| segmented rollout | 分段推进 | 在中间点保存状态后继续走到同一终点 |
| continuation consistency | 持续推进一致性 | direct 与 segmented 在准确且同路径条件下近似一致 |
| conditional response fidelity | 条件响应保真 | 对给定天气的响应与观测更吻合，不等于因果效应 |
| context prior | 上下文先验支路 | 从历史上下文直接提供的预测基线，需要在状态定义中公开 |
| factual path | 事实训练路径 | 训练时生成真实预测输出所走的 direct/recursive 路径 |
| donor weather | 匹配错配天气 | 来自匹配其他样本/时期的天气对照 |
| native metric | 数据集原生指标 | 与该数据集已有论文直接比较的官方指标 |
| common metric | 跨数据集共同指标 | NDVI R²/RMSE 等统一口径 |

---

## 2. 相比 AAAI 原稿，我们究竟拔高了什么

当前 `submission/main.tex` 仍然是旧稿身份：Q1-Q3、固定预测窗口、直接推进各时距，并明确写有 “It does not recursively roll out” 和干预“不测试 composition”。TIP 版本不是简单扩写实验，而是改变论文中心。

| 维度 | 原 AAAI 叙事 | TIP 新叙事 | 实质提升 |
|---|---|---|---|
| 论文对象 | 检验一个遥感预测模型中是否存在可测试预测状态 | 构建一个可持续推进、可复用的遥感世界模型 | 从“研究模型现象”转为“提出模型与能力” |
| 世界模型定义 | 状态可预测、可干预 | 状态承载 + 天气驱动 + 分段连续 + 可恢复/分支 | 定义更完整且可操作 |
| 时间动力学 | 对每个 horizon 直接从初态映射 | 共享转移沿天气段递归推进，并支持任意分段 | 从固定时距映射升级为过程模型 |
| 核心模型 | TerraState-V2 | TerraState-C1 | 与新定义一致的最终实现 |
| 核心问题 | Q1-Q3 | Q1-Q4 | 新增持续模拟与组合一致性 |
| 状态用途 | 用于一次预测和干预 | 可保存、继续、比较和分支 | 从中间特征变成运行时模型状态 |
| 对照逻辑 | Contextformer/V2 与若干干预 | 外部基线 + C0R/C1 严格机制对照 + 功能干预 | 区分预测性能、机制来源和状态行为 |
| 数据证据 | GreenEarthNet 单数据体系 | GreenEarthNet 主审计 + 独立区域/协议复现 | 从域内成立扩展到外部有效性 |
| 论文价值 | 预测状态的可测试性 | 可持续空间预测状态的模型设计与验证范式 | 对世界模型和遥感时序建模均有方法贡献 |
| 主结果口径 | 倾向用某个 R² 数字证明模型有效 | 明确承认预测非 SOTA，以行为能力和可靠统计为主 | 避免被精度榜单反向击穿 |

### 2.1 原 AAAI 主旨、新 TIP 主旨，以及我们实际改变了什么

#### 原 AAAI 稿到底主张什么

原稿的中心命题不是一般的“我们提出了一个世界模型”，而是：

> **TerraState 是一个 testable predictive-state world model（可检验预测状态世界模型）。历史观测形成的空间状态不仅要能支持预测，还应真实贡献到最终输出，并对未来天气产生可验证响应。**

原稿围绕这个命题设置三问：

| 原稿问题 | 实际证明内容 | 在原主旨中的作用 |
|---|---|---|
| Q1 Forecasting performance（预测性能） | TerraState 保留有用的遥感预测能力 | 证明模型首先是可工作的预测器 |
| Q2 State contribution（状态贡献） | 移除 state-mediated contribution（状态支路）后性能下降 | 证明显式状态不是装饰 |
| Q3 Weather-forcing response（天气驱动响应） | actual weather（真实天气）优于 donor/mean controls（错配/均值对照） | 证明预测会使用给定天气 |

因此，AAAI 原稿最终能够支持的结论是：**存在一个 forecast-bearing, weather-responsive predictive state（承担预测且响应天气的预测状态）**。它的重点是“内部状态的主张能否被证伪和验证”。

但原稿同时明确限定：对于每个预测时距，模型都从同一个初态 `z_t` 出发，使用对应天气前缀执行一次 direct transition（直接转移）；它 **does not recursively roll out（不递归推进）**，原 Q2/Q3 干预也 **do not test composition（不检验组合性）**。所以原稿没有主张该状态可以被保存、继续推进，或者分段运行后仍代表同一个持续世界。

#### 现在 TIP 稿要主张什么

TIP 的中心命题应升级为：

> **TerraState-C1 是一个天气驱动的遥感世界模型。它学习真正面向未来的显式空间预测状态，使不同时间跨度的状态转移能够组合，并使中间状态继续承担后续预测；由此，状态可以按天气序列递归推进、在中间时刻保存与恢复，并在直接推进和分段推进下保持近似一致。**

在新主旨中，Q1-Q3 没有被丢弃，但它们的角色发生了变化：

- Q1-Q3 是“这个状态值得被持续推进”的必要前提。
- Q4 是“这个状态是否真的构成持续世界模型”的新增定义性证据。
- C0R/C1 是定位 Q4 来自何种训练机制的新增严格对照。
- 第二独立数据集用于证明这套性质不是 GreenEarthNet 特有现象。

#### 从 AAAI 到 TIP 的实际差分

| 层次 | AAAI 原稿 | TIP 新稿 | 必须落实的变化 |
|---|---|---|---|
| 核心研究问题 | 能否得到一个可检验、承担预测且响应天气的内部状态？ | 该状态能否成为可保存、可继续运行且分段一致的世界状态？ | 摘要、引言和实验总问题全部改写 |
| 最终模型 | TerraState-V2 | TerraState-C1 | 主文方法、图和公式只以 C1 为最终模型 |
| 状态转移 | 从同一 `z_t` 对每个 horizon 做一次直接映射 | 同一共享转移按天气片段递归推进 | 由 Candidate C/C1 落实 |
| 状态身份 | 被分析和干预的内部表征 | 可被调用、保存、恢复、继续和分支的运行时状态 | 增加 `initialize/advance/decode/branch` 接口 |
| 验证问题 | Q1 + Q2 + Q3 | Q1 + Q2 + Q3 + **Q4 continuation** | 增加 direct/segmented 多终点、多分段验证 |
| 训练监督 | 各时距的事实输出由一次 direct transition 监督 | 真实未来标签经过多段共享转移形成 recursive factual path | 将“中间状态可继续预测”写入训练，而非只在训练后检查 |
| 机制归因 | 主要依赖 V2 与功能干预 | C0R/C1 同参数、同预算严格对照 | 证明提升不是参数量或骨干带来的 |
| 证据范围 | 主要在 GreenEarthNet 的既定验证/OOD 协议 | 四 split、多种子、独立第二数据集 | 增加统计与外部有效性 |
| 最终结论 | 状态对预测有用且响应天气 | 状态有用、响应天气，并能持续、分段一致地模拟未来 | 世界模型主张从 snapshot state（快照状态）升级为 operational state（可运行状态） |

#### 最直观的一句话

> **AAAI 原稿证明“模型里面确实有一个有用、会响应天气的预测状态”；TIP 新稿要证明“这个状态不只是一次预测时可分析的中间量，而是可以保存、续推、分支并持续代表同一观测世界的模型状态”。**

这才是本次工作的实质拔高。增加数据集、多种子和图表本身只是把证据做扎实；真正改变论文层次的是 **V2 到 C1 的动力学改变，以及 Q1-Q3 的‘状态有效性’与 Q4 的‘状态可持续运行性’共同组成新的中心命题**。

反过来说，如果最终只是把 Q4 作为一张附加表塞进旧稿，而摘要仍然主讲“testable predictive state”、方法仍以 V2 为中心、状态也没有实际 pause/resume（暂停/恢复）接口，那么审稿人仍会把它看作 AAAI 稿的加长版，而不是一篇主旨升级后的 TIP 论文。

### 2.2 可直接放进引言的定位段落草案

> 现有地球观测预测方法主要关注从固定历史窗口生成给定时距的未来观测，近期遥感世界模型进一步引入概率生成、天气条件和情景模拟。然而，能够生成未来并不自动意味着模型维护了一个可复用的世界状态：内部表征可能未真正承担输出，也可能只能在训练规定的完整窗口内工作，一旦在中间时刻保存并继续推进便发生路径依赖。为此，我们提出 TerraState，一个面向高分辨率植被动力学的天气驱动地球观测世界模型。TerraState 把显式空间预测状态作为核心训练对象和运行接口，并通过共享的变跨度状态转移支持直接推进、暂停继续和条件分支。尤其是，递归事实监督使真实未来标签经过中间状态和多段转移监督模型，从而把“中间状态必须继续代表当前世界”写进事实预测路径。除标准多步预测外，我们进一步检验状态承载、天气响应及直接/分段推进一致性，从而将遥感世界模型的评价从“是否产生合理未来”扩展到“内部状态是否能够持续代表并推进同一个观测世界”。

这段文字的关键不是声称所有前人都不会递归，而是把缺口放在**状态是否可验证、可恢复且路径一致**。这与当前同行事实相容，也能自然引出 Q1-Q4。

### 2.3 真正新增的贡献

1. **机制新增**：C1 使用共享的变跨度状态转移与 recursive factual supervision（递归事实监督），使同一状态可以按天气序列继续推进，并让中间状态直接接受真实未来预测目标的监督。
2. **能力新增**：支持 direct rollout、pause/resume 和 conditional branch 三种统一调用方式。
3. **验证新增**：Q4 直接检验“持续模拟”而不只检验单次预测；C0R/C1 提供近似单变量机制对照。
4. **定义新增**：将遥感世界模型从泛泛的“能预测未来”收紧为可检查的四项行为标准。
5. **论文定位新增**：从 GreenEarthNet 上的预测方法，扩展为天气驱动地球观测序列中的预测状态建模问题。

### 2.4 没有被证据支持、不得随叙事一起拔高的内容

- 不声称 TerraState 在 GreenEarthNet 上达到 SOTA；当前 C1 在四个 split 均落后 PredRNN 和 Contextformer，但优于部分基线。
- 不声称 `z` 是完备物理状态或包含所有世界信息；当前输出仍有 context prior（上下文先验支路）。
- 不声称 actual/donor/mean weather 是真实因果反事实；只能称 conditional response fidelity。
- 不声称热旱场景存在特异增强；当前 hot-dry interaction 未通过。
- 不把旧 `compare/q4_compare.json` 中 per-cube R²（逐 cube 决定系数）版 `G_abs` 的 `4/19 FAIL` 当作有效负面结论：该 R² 聚合腿存在规格错误。有效的 pooled-RMSE（汇总均方根误差）腿同期 19/19 通过，使用同批封存充分统计量修正为 pooled-R² 后三种资格口径也均为 19/19，因此当前有效结论是“修正后的事实端点非劣审计 19/19 通过”。写作时必须同时披露原规格错误，不能把它改写成“原 per-cube 门预注册通过”。
- 不声称可无限期无误差滚动；论文应报告误差随时距和分段数增长的边界。

---

## 3. 最新代码与实验家底核对

### 3.1 代码层面

| 项目 | 对应实现 | 核对结论 |
|---|---|---|
| TerraState-V2 | [`models/terrastate_v2.py`](../models/terrastate_v2.py) | 前代固定时距状态模型，保留为参考 |
| Candidate C / C1 | [`models/terrastate_candidate_c.py`](../models/terrastate_candidate_c.py) | 已实现共享分段状态转移；C1 为 recursive factual path |
| C0R | 同一 Candidate C 实现与配置分支 | 与 C1 同构，关键差异为 direct factual path |
| Contextformer/PVT-v2 骨干 | `PVTContextformerQ` 及现有模型代码 | 是上下文编码骨干，不是论文主要贡献 |
| Q1-Q4 评测 | A04 对应脚本、manifest 和结果 JSON | C1 四项均已有正式结果 |
| E1 汇总 | A07/A08 及 `collect_e1_table.py` | 同协议可获得基线已跑完并机械汇总 |

代码核对表明 C0R/C1 的比较并非“给同一个循环换名字”：

- Candidate C 的 direct（直接）与 composed/segmented（组合/分段）使用同一个转移模块 `F`，但走不同计算图，因此 Q4 检验的是非平凡的时间组合性质。
- 训练分段与 held-out partitions（留出分段方式）彼此分离，避免只记住少数固定切法。
- C1 与 C0R 的结构差分集中在 factual path（事实预测路径）：C1 的真实端点监督经过递归路径，C0R 经过直接路径。
- 两个实验臂共享随机数、样本端点、参数规模与显式一致性损失配置；正式 C1/C0R 中相关 consistency loss（显式一致性损失）权重均为 0。因此，现有量级差异能够更干净地归因于递归事实监督路径，而不是额外损失或额外参数。

这组实现事实应成为 Fig. 2、Table 3 和方法章节的中心，而不能只埋在 Q4 评测脚本说明里。

### 3.2 E1 已完成，完成到什么程度

**E1 不能再写成“待做”**。在 GreenEarthNet chopped 协议上，Contextformer、ConvLSTM、PredRNN、SimVP 已完成 `3 seeds × 4 splits = 48/48` 个 learned-baseline 评测，Persistence 完成 `4/4`，TerraState-C1 完成四个 split 的 seed 1。全部使用同一 manifest、mask、scorer 和 forecast horizon，共覆盖 22,320 个 minicubes。

| Split | PredRNN R² | Contextformer R² | **C1 R²** | ConvLSTM R² | SimVP R² | C1 当前位置 |
|---|---:|---:|---:|---:|---:|---|
| IID | 0.5414 | 0.5333 | **0.5220** | 0.5107 | 0.4988 | 3/5 |
| OOD-t | 0.5925 | 0.5877 | **0.5726** | 0.5483 | 0.5616 | 3/5 |
| OOD-s | 0.5087 | 0.5021 | **0.4949** | 0.4761 | 0.4650 | 3/5 |
| OOD-st | 0.5635 | 0.5567 | **0.5408** | 0.5234 | 0.5275 | 3/5 |

因此 E1 的正确结论是：

- **已证明 C1 具备有竞争力的预测能力，不是为了世界模型性质而失去基本预测能力。**
- **未证明 C1 是精度 SOTA，主文不得把 Table 1 写成“全面优于所有预测器”。**
- learned baselines 的三种子已完成，但 C1 仍只有一个种子，因此最终主表的统计公平性尚未闭环。
- Climatology / Previous Year 因官方脚本依赖当前不存在的 `iidx` reference track 而受阻，不应猜造协议。
- Earthformer 官方发布中没有可用权重，应诚实标为 `n.a.`，除非后续自行复现训练。

### 3.2.1 与 AAAI 原稿精度的直接对照：重点看 OOD-t

AAAI 原稿只把 GreenEarthNet `OOD-t` 作为 Q1 主线，报告 TerraState-V2 的 `R²=0.569349`、`RMSE=0.150594`；当前本地同协议评测得到 C1 的 `R²=0.572604`、`RMSE=0.150941`。因此，**从 V2 到 C1 的事实预测整体持平**：R² 微增 `+0.003255`，RMSE 微增（变差）`+0.000347`。两个指标方向不一致且没有跨模型配对显著性检验，不能写成“C1 比 AAAI 版本更准”，但足以支持“新增递归持续状态能力没有明显牺牲 OOD-t 精度”。

更直观的变化出现在**相对强基线的表面差距**。AAAI 表中的基线是既有论文数字；A08 则把官方权重放到与 C1 相同的 manifest、mask、scorer 和 forecast horizon（预测时距）下重评。因此下表既说明当前真实位置，也说明不能把旧表和新表混成一个排行榜：

| OOD-t 对照 | AAAI 原稿 | 本地同协议结果 | 差距变化 |
|---|---:|---:|---:|
| TerraState 版本自身 R²↑ | V2 `0.569349` | C1 `0.572604` | `+0.003255`，持平量级 |
| TerraState 版本自身 RMSE↓ | V2 `0.150594` | C1 `0.150941` | `+0.000347`，轻微变差 |
| Contextformer − TerraState R² gap↓（差距） | `0.620000-0.569349=0.050651` | `0.5877-0.572604≈0.015096` | 缩小约 `0.035555`（约 70%） |
| TerraState − Contextformer RMSE gap↓（差距） | `0.150594-0.140000=0.010594` | `0.150941-0.1431≈0.007841` | 缩小约 `0.002753`（约 26%） |
| PredRNN − TerraState R² gap↓（差距） | `0.620000-0.569349=0.050651` | `0.5925-0.572604≈0.019896` | 缩小约 `0.030755` |
| TerraState − PredRNN RMSE gap↓（差距） | `0.150594-0.150000=0.000594` | `0.150941-0.1474≈0.003541` | 反而扩大约 `0.002947` |

四个本地 split 上，C1 相对 Contextformer 的 R² 差距约为 `0.0072–0.0159`，RMSE 差距约为 `0.0069–0.0078`；其中 `OOD-t` 分别约为 `0.0151` 和 `0.0078`。所以最稳妥的论文表述是：

> **AAAI 原稿中 TerraState 在 OOD-t 上相对 Contextformer 的 R²/RMSE 差距看起来约为 0.0507/0.0106；统一协议本地重评后，C1 的对应差距约为 0.0151/0.0078。差距缩小主要来自公平评测口径与模型版本共同变化，不能全部归因于 C1 精度提升；C1 相对 V2 本身应表述为持平。**

当前 C1 仍是单种子，而 Contextformer/PredRNN 是三种子均值；这张审计表用于解释量级，不替代最终多种子显著性结果。

### 3.3 Q1-Q4 当前证据

| 问题 | 最新结论 | 可安全写入主文的范围 | 尚需补充 |
|---|---|---|---|
| Q1 预测 | 四个 split 均完成；C1 与 V2 接近，非 SOTA | competitive forecasting across IID/OOD splits | C1 多种子、独立数据集 |
| Q2 状态承载 | 四个 split 的 `full - alpha0` 均显著为正 | explicit state is load-bearing | 多种子复核；可视化 |
| Q3 天气响应 | actual 优于 donor 与 mean；endpoint fidelity 通过 | state/prediction responds faithfully to supplied weather | 独立数据集复现；不得写 causal |
| Q3 热旱子集 | hot-dry interaction CI 跨 0 | 不作正面主张 | 可作为边界/负结果放补充材料 |
| Q4 分段连续 | C1 四门通过，C0R 失败关键门；修正后的 pooled 端点非劣 19/19 | C1 is continuation-consistent on the locked audit（C1 在锁定审计上具备持续推进一致性） | 多种子与独立数据确认；新实验继续预先冻结 pooled 规格 |

Q2 的四个 split 均达到 `LOAD_BEARING`；官方 R² 差异约为 `+0.017` 至 `+0.034`。Q3 中 actual 相对 donor 的 ΔLoss 为 `+0.002053`，相对 mean weather 为 `+0.010140`，但 hot-dry interaction 为 `-0.000302` 且置信区间跨 0。Q4 中 C1 的分段退化约为 1% 量级，而 C0R 可达到约 9%-15%，这是目前最能区分普通预测器与持续状态模型的结果。

---

## 4. 缺漏总表：我们已有何物，还缺什么

| 编号 | 论文所需证据/产物 | 当前已有 | 状态 | 缺口与下一动作 | 对应图表 |
|---|---|---|---|---|---|
| G1 | 最终模型 C1 | 代码、权重、配置、四 split 结果 | 已完成 | 冻结命名与默认配置，避免继续漂移 | Fig. 2, Table 3 |
| G2 | E1 同协议强基线 | 4 learned baselines 三种子四 split，Persistence | 已完成 | 只需纳入最终排版；Climatology/PY 保留受阻说明 | Table 1 |
| G3 | C1 多种子预测 | seed 1 四 split | 部分完成 | 至少补 2 个独立种子，报告 mean±std/CI | Table 1, Fig. 5 |
| G4 | 状态承载 Q2 | 四 split 全部 load-bearing | 已完成 | 新种子重复并制作分布/地图 | Fig. 6, Table 4 |
| G5 | 天气响应 Q3 | actual/donor/mean 完成 | 已完成 | 新种子或独立数据集复现；明确非因果 | Fig. 7, Table 5 |
| G6 | 持续模拟 Q4 | C1 四门通过、C0R 失败关键门；修正后的 pooled 端点非劣审计 19/19 通过 | 已完成核心证据 | 多种子和独立数据按事先冻结的 pooled 规格做增强确认 | Fig. 8, Table 6 |
| G7 | 干净机制消融 | C0R/C1 已有 Q4 关键结果 | 部分完成 | 同 seed/预算补齐四 split Q1、Q2、Q4 汇总 | Table 3 |
| G8 | 独立第二数据集 | 尚无 | 待完成 | 首选 EarthNet2023-Africa；适配输入、时间步和指标 | Fig. 4-5, Table 2 |
| G9 | 第二数据集行为验证 | 尚无 | 待完成 | 独立训练后复现 Q1，并对 C1/C0R 做精简 Q2-Q4 | Table 2、4-6, Fig. 4-8 |
| G10 | 多时距退化曲线 | 结果中有部分 endpoint 信息 | 部分完成 | 统一导出逐 horizon R²/RMSE/CI | Fig. 5 |
| G11 | 高质量定性结果 | 尚未形成论文级固定样例板 | 待完成 | 固定样例选择规则，输出 GT/基线/C1/error | Fig. 3-4 |
| G12 | 模型复杂度与运行成本 | 参数量已有，其他不全 | 部分完成 | 测 FLOPs、显存、训练/推理速度、分段开销 | Table 7 |
| G13 | 明确的状态 API | 机制上具备，尚未统一封装展示 | 部分完成 | 增加 initialize/advance/decode/branch 薄封装与 demo | Fig. 2 |
| G14 | TIP 全文改写 | AAAI 旧稿仍为 Q1-Q3/V2 | 待完成 | 重写标题、摘要、引言、方法、实验和限制 | 全文 |
| G15 | 统计与复现实务 | manifests/JSON 较完整 | 部分完成 | 统一 seed、CI、显著性、日志索引和表格生成 | 全部表格 |
| G16 | 2026 直接同行覆盖 | 已完成 EO-WM/VegSim 论文级定位核对，尚未协议复现 | 部分完成 | 优先复现 VegSim 同口径点预测；EO-WM 做协议对齐或明确非同任务 | Table 1/2/3、Related Work |
| G17 | 预测不确定性边界 | 当前 C1 为确定性输出 | 待完成 | 至少报告多种子/ensemble calibration（集成校准）；资源允许再做共享状态的 quantile head（分位数输出头） | Table 2/7 或补充材料 |

**关键解释**：E1 已经完成，不等于 Table 1 已经完全封版。E1 解决的是“可合法获得的外部基线是否在同协议下重跑”；Table 1 封版还需要 C1 多种子，二者不能混为一件事。

---

# 第二部分：图表总体设计

## 5. 主文建议采用 8 图 + 7 表

“图表总数至少 12”不是 TIP 的硬性规则。本稿建议采用 **8 Figures（图）+ 7 Tables（表）= 15 项主文图表**，原因不是凑数量，而是旧的 5 图方案把科学问题与模型结构、两个数据集的定性结果与时距曲线压得过密。拆分后，每张图只承担一个清晰问题，也能让两个数据集都获得可审查的空间预测证据。

若后续页数紧张，优先压缩表格行、合并补充材料，不应重新把科学立论、模型结构和定性结果挤回同一张图。15 项是当前最理想的证据结构，不是必须机械保留的配额。

### 5.1 理想图表状态总览

| 编号 | 图表内容 | 回答的审稿问题 | 当前基础 | 完成状态 |
|---|---|---|---|---|
| **Fig. 1** | 从 fixed-horizon EO forecasting（固定时距地球观测预测）到 reusable-state world modeling（可复用状态世界建模）的科学问题与四项运行契约 | 为什么已有遥感预测器还不够？本文研究的问题为什么属于世界模型？ | 科学问题已冻结；尚无图 | 待绘制 |
| **Fig. 2** | TerraState-C1 架构与 recursive factual supervision（递归事实监督）：PVT/Contextformer、context prior（上下文先验）、显式状态、共享变跨度转移、C0R/C1 路径差分 | 你提出了什么机制？为什么中间状态会被训练成可续推状态？ | C1/C0R 代码已有；旧图仍按 V2 | 待重画 |
| **Fig. 3** | GreenEarthNet 定性预测：GT、Persistence、PredRNN、Contextformer、C1、绝对误差图，覆盖短/中/长时距及典型/困难样例 | 主数据集上模型到底预测出了什么？是否复制、过平滑或长时坍缩？ | 模型结果已有，论文级图板没有 | 待导出 |
| **Fig. 4** | EarthNet2023-Africa 定性预测：同类方法布局，包含典型样例与失败案例 | 独立地区、生态与协议下的空间预测是否仍可信？ | 数据和模型尚未训练 | 待完成 |
| **Fig. 5** | 两数据集随 horizon（预测时距）变化的 R²/RMSE 曲线，GreenEarthNet 覆盖 IID/OOD-t/OOD-s/OOD-st，并给多种子 CI | 长时误差如何累积？C1 的竞争力和代价在哪些时距出现？ | GreenEarthNet 汇总值有，逐时距/多种子不全 | 部分完成 |
| **Fig. 6** | Q2 状态承载：干预示意、效应随时距变化、样本分布/CI 和空间贡献图 | 显式状态是否真实承担输出，还是可被旁路替代？ | 四 split Q2 完成 | 待制图 |
| **Fig. 7** | Q3 天气响应：actual/donor/mean 天气轨迹、NDVI 预测轨迹、终点地图和差异图 | 模型是否使用所提供的未来天气，并产生可解释的条件分支？ | Q3 完成 | 待制图 |
| **Fig. 8** | Q4 持续推进：协议示意、C1/C0R 随分段数和时距的退化、状态/输出距离、空间终点图 | 中间状态能否继续代表当前世界？该性质是否来自递归事实路径？ | 锁定审计核心结论成立；修正后端点非劣 19/19 | 待制图并扩展确认 |
| **Table 1** | GreenEarthNet 四 split 同协议预测主表，mean±std | 基础预测竞争力如何？与强基线是否公平？ | E1 已完成；C1 单种子 | 部分完成 |
| **Table 2** | EarthNet2023-Africa 预测主表：重新训练后的 native metrics + common NDVI metrics | 预测能力是否跨独立区域、生态和协议成立？ | 无 | 待完成 |
| **Table 3** | 核心机制消融：Contextformer、C0R、C1 与功能干预；V2 只在补充材料可选出现 | 贡献来自共享转移与递归事实监督，还是参数/底座变化？ | 主要模型和部分结果已有 | 部分完成 |
| **Table 4** | Q2 数值表：主数据集 C1 四 split/多 seed + 第二数据集 C1 精简复验 | 状态承载效应是否稳定、显著且可跨数据复现？ | 单 seed 四 split 已有 | 部分完成 |
| **Table 5** | Q3 数值表：C1、C0R、天气感知基线的 actual vs donor/mean；第二数据集精简复验 | C1 的天气响应是否超过无信息、错配天气和普通条件预测器？ | C1 已有，基线与第二数据集待补 | 部分完成 |
| **Table 6** | Q4 数值表：两数据集 C0R/C1 的多 endpoint、多 partition、多 segment 数 | 分段连续性是否系统成立、可跨数据复现，且确实来自 recursive path？ | 旧锁定审计已有 | 部分完成 |
| **Table 7** | 参数、FLOPs、显存、训练/推理时间、direct/segmented 开销 | 新能力是否以不可接受的计算代价换来？ | 参数量已有 | 待完成 |

### 5.2 图表之间的叙事顺序

1. Fig. 1 先提出科学问题并定义世界模型的可证伪运行契约。
2. Fig. 2 再说明 C1 如何用共享变跨度转移和递归事实监督实现这一契约。
3. Table 1-2、Fig. 3-5 证明它首先是两个数据集上的合格预测器，并公开长时预测边界。
4. Fig. 6 / Table 4 证明显式状态不是装饰。
5. Fig. 7 / Table 5 证明状态受提供的未来天气驱动。
6. Fig. 8 / Table 6 证明状态可以持续、分段推进。
7. Table 3 回答这些能力来自哪项机制，而非参数或底座变化。
8. Table 7 交代计算、状态存储和恢复的工程代价。

这个顺序应贯穿摘要、引言贡献点、实验问题和结论，避免正文一会儿讲预测、一会儿讲状态、一会儿再返回架构。

### 5.2.1 为什么 Q2-Q4 各有一张图和一张表，不是“水图表”

**一项主张同时配图和表在 TIP 中是正常写法，但前提是二者承担不同证据功能。** 最终遵守一句统一原则：

> **表格负责给出可复核的总体数值，图负责展示这些数值背后的时间过程、空间现象和样本分布。图与表服务于同一科学主张，但不得把相同的汇总数字换一种形式重复呈现。**

更直观地说，表格是“测量报告”，图是“行为录像”。表格精确记录 CI、样本量、seed 和判定；图让审稿人看见效应如何随时距变化、发生在什么空间区域、由哪些样本驱动，以及失败模式是什么。IEEE 对 TIP 并没有“至少 12 个图表”的硬规则，真正的硬约束是常规论文初投稿总页数；IEEE 图形规范也明确支持 `(a)(b)(c)` 多子图。近期 TIP 论文也常把定量表与定性图、收敛/注意力/机制图配对使用。

> **版式依据**：IEEE SPS 的 [Information for Authors](https://signalprocessingsociety.org/publications-resources/information-authors) 规定常规论文初投稿总页数，而没有规定图表最低数量；[Guidelines for Preparing Electronic Graphics](https://signalprocessingsociety.org/publications-resources/guidelines-preparing-electronic-graphics) 明确说明多子图的组织方式。以 TIP 2025 的 [RSB-Pose](https://arxiv.org/abs/2311.14242) 为例，其用 Table I/II 报定量主结果、Fig. 5 展示定性姿态，又用 Table III 报消融、Fig. 6-8 展示收敛、细化和注意力行为。可借鉴的是“同一论点的数值证据与行为证据互补”，不是机械模仿图表数量。

| 主张 | 表格不可替代的内容 | 图不可替代的内容 | 判定是否重复 |
|---|---|---|---|
| Q2 状态承载 | Table 4：每个 dataset/split/seed 的 full、prior-only、ΔR²、CI、判定 | Fig. 6：效应随时距变化、样本分布及真实空间贡献/误差案例 | 互补；若 Fig. 6 只画 Table 4 的四根柱，则重复 |
| Q3 天气响应 | Table 5：actual-vs-donor/mean 的精确 ΔLoss、CI、R² 和边界结论 | Fig. 7：输入天气如何不同、预测轨迹如何分叉、空间终点如何变化 | 互补；若只把两行 ΔLoss 改成柱状图，则重复 |
| Q4 持续推进 | Table 6：各 endpoint/partition/seed 的 direct、segmented、CI 和 gate | Fig. 8：退化随分段数/时距的过程、C1/C0R 量级差、状态/输出路径及空间终点 | 互补；若只把 19/19 画成大勾号，则重复 |

因此 8 图 7 表不是数量指标，而是当前的**最优证据分工**。排版超页时，优先把完整数值网格、额外 seed/split 和 gate matrix（门控矩阵）移到补充材料，不能删除 Fig. 3-4 的预测可视化，也不能让 Fig. 6-8 退化成表格数字的彩色复制。

### 5.3 是否必须有预测结果图：必须，而且不能只放一张“好看案例”

答案是明确的：**需要同时有 quantitative results（定量结果）和 qualitative results（定性结果）**。Table 1/2 告诉审稿人平均误差与统计排名，Fig. 3-4 则像目标检测论文中的检测框可视化一样，让人检查模型到底预测出了什么；Fig. 5 单独承担预测时距退化，避免把空间图压缩得无法阅读。

遥感预测的定性图至少能暴露表格看不到的五类问题：

1. 预测是否只复制最后一帧，即 persistence-like behavior（类持续性行为）。
2. 空间边界是否被抹平，是否出现过度平滑。
3. 绿化/衰退的相位是否提前或滞后，即 seasonal phase lag（季节相位偏移）。
4. 长时预测是否向均值坍缩。
5. 云/无效区、耕地边界和局地异常是否处理一致。

因此 Fig. 3 和 Fig. 4 不是装饰，而是两个数据集 Q1 的必要证据。每个数据集的图最少应包含：

```text
历史末帧（Last context）
| 真值（Ground truth）
| Persistence（持续性基线）
| 强预测基线
| Contextformer
| TerraState-C1
| 每个方法的绝对误差图（Absolute-error map）
```

并且至少展示 short/mid/long horizon（短/中/长时距）三个时间点。两个数据集各自成图：GreenEarthNet 的四 split 和模型较多，EarthNet2023-Africa 还需同时展示典型及失败样例；硬塞入一张图会导致地图过小。Fig. 6-8 中也应保留真实空间预测图，使状态承载、天气响应和分段一致不只停留在标量曲线层面。

---

# 第三部分：每一张图的详细安排

## 6. Fig. 1：科学问题与遥感世界模型运行契约

### 目的

在文章第一页完成立论：**准确生成固定长度未来，不等于模型已经维护了可继续使用的世界状态。** 该图不画具体网络层，而是说明遥感场景为何需要可复用状态、本文检验什么性质，以及这些性质为何构成世界模型问题。

### 推荐面板

- **(a) Partial observation（部分可观测）**：真实地表状态不可完全观测；卫星观测时间稀疏且受云遮挡，天气驱动较密集。图中区分 latent land state（潜在地表状态）与 satellite observation（卫星观测），说明模型必须从不完整观测维持预测状态。
- **(b) Fixed-horizon forecasting（固定时距预测）**：历史和天气一次性映射到指定未来。标出“output can be accurate（输出可以准确）”但“intermediate state need not be reusable（中间状态未必可复用）”，避免把普通预测器画成反面稻草人。
- **(c) Reusable predictive world state（可复用预测世界状态）**：从历史初始化 `s_t`，随后按天气片段推进；直接、暂停/恢复和天气分支共享同一状态接口。
- **(d) Falsifiable contract（可证伪运行契约）**：用四个紧凑问题框列出 Q1 prediction（预测能力）、Q2 load-bearing（状态承载）、Q3 forcing response（驱动响应）、Q4 continuation/composition（持续推进/组合一致）。

### 必须标清

- 图标题建议为 **From Fixed-Horizon EO Forecasting to Reusable-State World Modeling（从固定时距地球观测预测到可复用状态世界建模）**。
- “world model（世界模型）”必须出现在图中央的研究对象上，不能只藏在 Q4 或图注中。
- 将科学目标写成“中间状态继续承担后续预测”，不要写成仅仅“程序可以 pause（暂停）”。
- 天气标为 external forcing（外部驱动），不是 agent action（智能体动作）；branch（分支）是条件情景，不是因果反事实。
- 图中不出现 PVT 层数、卷积核或训练损失细节；这些属于 Fig. 2。

### 排版

- 建议双栏通栏、单行四面板 `(a)-(d)`；`(b)` 与 `(c)` 使用相同输入，形成最直接的视觉对照。
- 历史观测、天气驱动、世界状态、预测输出使用四种稳定颜色；灰色表示不可观测真实过程。
- 只保留组合关系 `T_{a:c}(s_a) ≈ T_{b:c}(T_{a:b}(s_a))`，不堆叠网络公式。
- `(d)` 四个检验按 Q1-Q4 顺序排列，并用细线回指 `(c)` 中被检验的模型行为。

### 当前与待办

- 科学问题、四项契约和术语已经冻结，可以立即绘制草图。
- 需要最后确认数据示意中的传感器、天气变量和时间尺度与两个数据集一致。
- 该图不依赖第二数据集实验完成，应该最先封版；旧 AAAI 架构图不能代替它。

### 推荐图注核心句

> Accurate fixed-horizon forecasts do not necessarily imply a reusable predictive state. TerraState learns weather-driven spatial state transitions and tests whether the learned state remains load-bearing, forcing-responsive, and continuation-consistent across temporal partitions.

对应中文：**准确的固定时距预测并不必然意味着模型拥有可复用的预测状态。TerraState 学习天气驱动的空间状态转移，并检验该状态在不同时间分段下是否持续承担预测、响应外部驱动并保持推进一致。**

---

## 7. Fig. 2：TerraState-C1 架构与递归事实监督

### 目的

让审稿人在一张图内看懂 TerraState 不是“Contextformer + 一个 latent（潜变量）”，并明确 C1 相比 AAAI/V2 和 C0R 真正新增的训练机制：**共享变跨度状态转移 + recursive factual supervision（递归事实监督）**。

### 推荐面板

- **(a) State initialization（状态初始化）**：历史 Sentinel-2/NDVI、过去天气和地理信息进入 PVT-v2/Contextformer context backbone（上下文骨干），得到 context prior `P_h`（上下文先验）和初始动态状态 `z_0`。
- **(b) Shared variable-span transition（共享变跨度转移）**：未来天气、地理和时间编码驱动同一个 `T`；`T` 可接收不同长度天气片段并反复调用，输出 `z_k`。
- **(c) Readout and runtime state（读出与运行时状态）**：明确绘出 `y_hat_k=P_h+alpha O(z_k)`，并公开运行时状态 `{P, z, geography, offset}`，对应 `initialize/advance/decode/branch` 四个接口。
- **(d) C0R vs C1 factual path（C0R/C1 事实路径）**：相同初态、随机数、端点、参数和训练预算；C0R 的事实目标经 direct path（直接路径）监督，C1 经多个共享转移的 recursive path（递归路径）监督。
- **(e) Train/held-out temporal partitions（训练/留出时间分段）**：训练使用的分段模式和 Q4 留出分段模式分离，说明组合一致性不是记忆固定切法。

### 面板执行口径

`(a)-(e)` 都属于同一张 Fig. 2，不是五选一。主视觉链为 `(a)->(b)->(c)`；`(d)` 放在下方横向对照并用高亮色标出唯一结构差分；`(e)` 作为紧凑角标或小矩阵。若页宽不足，可把完整 partition list（分段列表）移到方法表或补充材料，但 `(d)` 不能删除。

### 必须标清

- `PVT-v2/Contextformer` 是 context backbone（上下文骨干），不是本文创新；图中使用中性灰色。
- context prior（上下文先验支路）绕过动态状态，不能隐藏，否则 Q2 的 `alpha=0/prior-only` 干预无法解释。
- shared `T`（共享转移）在每个片段权重完全共享，使用同一图形和参数标记。
- C1 与 C0R 的显式 consistency loss（组合一致性损失）权重均为 0；正式差异来自真实预测监督所走的事实路径，而不是额外正则项。
- “recursive factual supervision”旁边添加中文“递归事实监督”，并用真实未来标签箭头连接每个递归终点。

### 排版

- 双栏通栏；上半部分是状态初始化、推进、读出，下半部分是 C0R/C1 训练路径对照。
- 状态使用固定绿色，天气使用橙色，观测/真值使用紫红或洋红，骨干与先验使用中性灰；避免整图只使用蓝色深浅。
- 公式只保留 `z_0=S(E(x))`、`z_b=T(z_a,u[a:b])`、`y_hat=P+alpha O(z_b)`；损失细节放方法节。

### 当前与待办

- 当前模型代码足以绘制 `(a)-(e)`，C1/C0R 的计算图差异已经核对。
- 需要补统一 `initialize/advance/decode/branch` 薄接口和最小 save/load demo，使图示能力与代码调用完全一致。
- 旧 AAAI/V2 图可以作为重画素材，但必须删除“不递归、不测试 composition（组合性）”的旧中心逻辑。

---

## 8. Fig. 3：GreenEarthNet 多时距定性预测

### 目的

以真实像素地图证明 C1 首先是一个合格的高分辨率地球观测预测模型，并让审稿人直接检查平均 R²/RMSE 无法暴露的复制最后一帧、过平滑、相位滞后、边界丢失和长时均值坍缩。

### 推荐布局

- **列**：Last context（历史末帧）、GT（真值）、Persistence（持续性基线）、PredRNN、Contextformer、C1、各方法 absolute-error map（绝对误差图）。若列宽不足，保留一个最强视频预测基线，不同时删除 Persistence 与 Contextformer。
- **时间**：每个样例展示 short/mid/long horizon（短/中/长时距），建议 `h=5/10/20`；GT 与预测必须使用完全相同的 mask 和色标。
- **行**：IID、OOD-t、OOD-s、OOD-st 各至少一个样例；再加入一个 high-dynamic（高动态）或明确失败样例。

### 样例冻结规则

1. 在查看最终排版效果前，按 C1 per-cube RMSE（逐样本均方根误差）的 `P25/P50/P75` 和 NDVI 动态幅度冻结候选。
2. 所有方法使用同一 cube、同一时点、同一有效像素和同一色标。
3. 主文同时包含典型与困难案例，完整随机样例网格及全 20 帧序列放补充材料。
4. 图注公开样例选择规则，避免只展示最漂亮预测。

### 排版与当前状态

- 建议双栏通栏，地图宽度优先；误差图统一使用从 0 开始的顺序色标。
- 每个方法标签下方可放一行该样例的 RMSE，但不能把 Table 1 全部数字搬进图中。
- GreenEarthNet 权重和评测结果已有，当前缺固定样例 manifest、预测缓存统一导出和论文级拼图。

---

## 9. Fig. 4：EarthNet2023-Africa 独立数据集定性预测

### 目的

让第二数据集不仅在 Table 2 中提供一个平均分，还能证明 TerraState 在独立地区、生态条件和数据协议下仍能产生空间上可解释的未来；这张图承担 external validity（外部有效性）的视觉证据。

### 推荐布局

- 使用与 Fig. 3 尽量一致的列：Last context、GT short/mid/long、Persistence、该数据集合法强基线、Contextformer_A、C1_A、absolute-error map。
- 至少展示两个典型样例、一个高动态样例和一个失败样例；若官方任务输出不完全等同于 NDVI，需同时展示 native target（原生预测目标）和可计算的 NDVI，不可只展示对本文有利的派生通道。
- 方法均应在 EarthNet2023-Africa 上独立训练或按官方允许的预训练协议适配；不能拿 GreenEarthNet 的 C1_G 权重直接推理后称为 Table 2/Fig. 4 主结果。

### 与 Fig. 3 的关系

两图不是重复：Fig. 3 覆盖 GreenEarthNet 四 split 和主方法对照；Fig. 4 检验跨地区、跨生态和跨协议的空间泛化，并主动展示失败边界。统一列顺序和色标语义，使审稿人可以跨图比较，但不要为了形式一致而删除第二数据集的原生变量。

### 当前与待办

- 当前尚无第二数据集训练和图像结果，所有面板留空。
- 完成数据审计后先冻结可视化变量、mask、horizon 映射和样例规则，再训练 C0R_A/C1_A 及基线。
- 若 EarthNet2023-Africa 最终不可合法或公平适配，应更换真正独立的数据集，而不是用 EarthNet2021/GreenEarthNet 的近重复版本冒充独立验证。

---

## 10. Fig. 5：两数据集预测时距与 OOD 退化曲线

### 目的

量化预测误差如何随未来时距增长，说明 C1 的竞争力、长时边界和 OOD 代价出现在哪里；该图回答时间过程，Table 1-2 回答总体精确数值。

### 推荐面板

- **(a) GreenEarthNet R²-horizon**：四个 split 使用 `2x2` small multiples（小多图），方法颜色固定，C1 多种子报告 95% CI。
- **(b) GreenEarthNet RMSE-horizon**：与 `(a)` 共享横轴和图例。
- **(c) EarthNet2023-Africa native metric-horizon**：按官方时间步报告原生指标。
- **(d) EarthNet2023-Africa NDVI metric-horizon**：报告共同 NDVI R²/RMSE，以便和主数据集观察同类趋势，但不跨数据集直接排名绝对值。

### 面板执行口径

`(a)-(d)` 都应生成并组成一张图；它们不是四选一。若 Africa 原生指标本身不能逐时距计算，可将 `(c)` 改为官方时间块曲线，并在图注说明。不得只画总体均值柱状图，因为那会重复 Table 1-2。

### 排版与当前状态

- x 轴使用真实预测天数或明确时间步，不只写抽象 `h`；两数据集时间分辨率不同则分别标注。
- 相同方法在全图保持同色，C1 用主色，Contextformer 和最佳视频基线用两种中性色；置信带不要遮住主要曲线。
- GreenEarthNet 已有总体数值和部分 endpoint 信息，仍需统一导出逐 horizon 结果并补 C1 多种子；Africa 全部待补。

---

## 11. Fig. 6：显式状态是否承载预测

### 目的

直接回答：模型是否主要依赖 context prior（上下文先验支路），显式动态状态只是装饰？

### 推荐面板

- **(a) Intervention protocol（干预协议）**：同一输入和参数，仅将 `alpha` 从 1 设为 0，区分 full（完整模型）与 prior-only（仅上下文先验），说明被删除的是 state readout（状态读出）而非重新训练另一模型。
- **(b) Horizon dependence（时距依赖）**：`ΔR²` 或 `ΔRMSE` 随预测时距变化，验证动态状态在何时开始承担主要作用。
- **(c) Distribution（效应分布）**：per-cube/per-tile（逐样本/逐地块）效应的 ECDF/violin（经验累积分布/小提琴图），配零效应线和 cluster bootstrap CI（聚类自助法置信区间）。
- **(d) Spatial cases（空间案例）**：GT、full、prior-only、各自误差及 state-contribution map（状态贡献图）；按贡献高/中/低的冻结分位样例选择。

### 面板执行口径

`(a)-(d)` 均制作并组成一张 Fig. 6，不是四选一：`(a)` 只定义 full/prior-only 干预，`(b)` 展示状态贡献随时距变化，`(c)` 展示样本/地块效应分布与 CI，`(d)` 展示真实空间贡献和误差。Table 4 已承担精确汇总数值，因此 Fig. 6 不再把四个 split 画成简单柱状图。若版面不足，完整四 split 分布可移到补充材料，但主文至少保留时距、分布摘要和空间案例。

### 排版

- 左半部分做统计，右半部分做空间案例。
- 零效应线必须明显；CI、样本量和聚类单位写在图注。
- 使用“load-bearing state contribution”，不使用“state contains all information”。

### 当前与待办

- 四 split 均已通过，官方 ΔR² 约 `+0.017` 到 `+0.034`。
- 需为新增种子复跑相同干预并统一导出绘图数据。
- `T_identity` 可作为补充面板，但需注明 decoder 接收到训练分布外状态的混杂，不应单独承担核心结论。

---

## 12. Fig. 7：天气驱动与条件分支

### 目的

展示同一个历史/中间状态在不同未来天气输入下生成不同的合理未来，并用 actual weather（真实天气）的更高 endpoint fidelity（终点响应保真）证明模型没有忽略天气。

### 推荐面板

- **(a) Weather trajectories（天气轨迹）**：从同一 `runtime_state（运行时状态）` 输入 actual、matched donor、mean weather（真实、匹配错配、均值天气），绘制温度、降水等关键变量随时间的差异；分支结构嵌在面板角落。
- **(b) Predicted NDVI trajectories（预测 NDVI 轨迹）**：三条预测与 GT（真值）的区域均值/分位带，和 `(a)` 严格共享时间轴。
- **(c) Spatial endpoint maps（空间终点图）**：GT、actual、donor、mean 的终点预测及统一色标。
- **(d) Difference/error maps（差异/误差图）**：actual-donor、actual-mean 的预测差异以及相对 GT 的误差变化，展示天气响应发生在何处。

### 面板执行口径

完整结果包应生成 `(a)-(d)` 并组成一张 Fig. 7，而不是从中任选一个：`(a)` actual/donor/mean 天气轨迹，`(b)` 对应 NDVI 预测轨迹与 GT，`(c)` GT/actual/donor/mean 终点地图，`(d)` actual-control 差异/误差图。分支结构用图角的小示意即可；精确 ΔLoss、CI 和极端子集数值由 Table 5 承担，不再增加重复的柱状汇总面板。

### 排版与措辞

- 图中直接标注 `conditional branch（条件分支）`，不要写 `causal intervention（因果干预）`。
- actual、donor、mean 使用在天气曲线、预测轨迹和地图边框中一致的颜色。
- 负结果 hot-dry interaction 不必占主图大面积，但应在 Table 5 和补充材料诚实报告，并可选择一个失败案例作为 Fig. 7 的边界说明。

### 当前与待办

- Q3 主比较已完成：actual 优于 donor 和 mean，endpoint fidelity 通过。
- 热旱特异增强未通过，因此主图重点是一般天气响应，不把故事押在极端事件上。
- 第二数据集若天气字段允许，至少复现 actual vs mean；matched donor 需重新定义匹配规则并冻结。

---

## 13. Fig. 8：持续模拟与分段一致性

### 目的

这是 TIP 新主线最关键的图。它要把“预测未来”和“维护可继续推进的世界状态”视觉上分开。

### 推荐面板

- **(a) Direct vs segmented protocol（直接/分段推进协议）**：相同初态、终点和天气路径，对照一次变跨度调用 `[0,H]` 与多次调用 `[0,h1]+[h1,h2]+...+[hk,H]`；强调两条路径使用同一个 `T`，但计算图不同。
- **(b) Degradation curve（退化曲线）**：x 轴为分段数，按 horizon（预测时距）分面，y 轴为相对 RMSE 增量；C1 与 C0R 同图并带 CI。
- **(c) State/output gap（状态/输出差距）**：direct 与 segmented 的状态距离、输出距离或样本分布，证明差异不是仅由一个总体均值驱动。
- **(d) Spatial example（空间案例）**：GT、C1-direct、C1-segmented、两者差异、C0R-direct、C0R-segmented 及两者差异，使用统一色标。

### 面板执行口径

完整结果包生成 `(a)-(d)` 并组成一张 Fig. 8：`(a)` 定义 direct/segmented 协议，`(b)` 展示 C1/C0R 退化随时距和分段数的趋势，`(c)` 展示 state/output gap（状态/输出差距）的分布或路径，`(d)` 展示空间终点图。Table 6 已精确记录 gate（门控）、CI 与 19/19 结论，因此主图不再重复 gate matrix（门控矩阵）或大面积通过标记。

### 评测规格

- 在运行前冻结：样本 manifest、endpoints、partitions、segment counts、pooled R²/RMSE、相对退化阈值、bootstrap 单位和排除规则。
- 主指标使用 pooled/global R² 与 RMSE；不得再把短序列单 cube R² 当作绝对门。
- 同时报 direct accuracy 和 composed accuracy，防止“二者都很差但彼此接近”也被判定一致。
- C1/C0R 必须同参数、同 seed、同训练预算、同评测输入。

### 排版

- C1 使用主色，C0R 使用中性对照色；direct 实线、segmented 虚线。
- 主图突出约 1% 对约 9%-15% 的量级差异，但以完整数据和 CI 为准，不只写单个最漂亮数字。
- 图注明确旧锁定评测中的 per-cube R² gate（逐 cube 决定系数门）因聚合病理无效；同批封存统计量的 pooled-RMSE 腿及修正 pooled-R² 端点审计均为 19/19，本图据此报告有效结果。

### 当前与待办

- 已有 C1 四门通过、C0R 在组成一致和状态保留上失败的锁定证据；有效的事实端点非劣结论为 19/19 通过。
- 历史 `4/19` 仅作为错误 per-cube R² 聚合的审计记录保留，不再作为 Q4 结论；论文同时披露“原规格错误”和“修正 pooled 结果 19/19”，不得声称原错误门本身通过。
- 新的未触碰样本/第二数据集仍在运行前冻结 pooled 规格，但其定位是跨样本、跨数据确认，不是把当前 Q4 从失败补成通过。
- 多种子完成后，报告 seed 间 Q4 退化分布，而非只有一次 gate（门控）结果。

---

# 第四部分：每一张表的详细安排

## 14. Table 1：GreenEarthNet 同协议预测主表

**一句话目的**：在主数据集的完全相同协议下，证明 C1 首先是一个有竞争力的多步遥感预测器，并给 Q2-Q4 提供性能前提。

### 行与分组

- Persistence、Climatology、Previous Year：能合法运行的传统参考；受阻项用脚注说明，不填猜测值。
- ConvLSTM、PredRNN、SimVP、Contextformer：A08 的同协议重跑结果。
- TerraState-C1：最终模型，必须多种子后封版。
- TerraState-V2 不进主表；需要时只放补充材料 `Table Sx`。

### 列

```text
Method | Params | IID R²/RMSE | OOD-t R²/RMSE | OOD-s R²/RMSE | OOD-st R²/RMSE
```

NSE、Bias、RMSE25 可放第二行或补充表，避免横向过宽。正文主表报告 mean±std；显著性符号只用于预先定义的配对检验。

### 终稿版式模板（数值先留空）

| Method（方法） | Params（参数量） | IID R²↑ | IID RMSE↓ | OOD-t R²↑ | OOD-t RMSE↓ | OOD-s R²↑ | OOD-s RMSE↓ | OOD-st R²↑ | OOD-st RMSE↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Persistence（持续性） | 0 | -- | -- | -- | -- | -- | -- | -- | -- |
| Climatology（气候态）* | 0 | -- | -- | -- | -- | -- | -- | -- | -- |
| ConvLSTM | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| PredRNN | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| SimVP | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Contextformer | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| **TerraState-C1 (ours)（本文）** | -- | -- | -- | -- | -- | -- | -- | -- | -- |

`*` 若 `iidx` reference track（参考轨迹）仍不可恢复，则该行保留为 `n.a.` 并在脚注解释，不使用猜测实现。正文横向空间不足时，将每个 split 的 R²/RMSE 合并成 `R² / RMSE` 两行表头。

2026 年直接同行需要额外处理：VegSim 使用 minicube 聚合 NDVI 和另一套指标，EO-WM 使用 EarthNet2021 四通道多光谱协议，不能把论文数值直接塞入上表并排序。优先增加一个 `Protocol-aligned direct-peer evaluation（协议对齐的直接同行评测）` 区块：将 C1 空间输出聚合到 VegSim 的时间序列口径，或在其公开代码上用相同 split/metric 重跑；EO-WM 只在任务真正对齐时作定量比较。

### 当前结论写法

“C1 在四种分布设置下保持有竞争力的预测性能，同时提供普通预测器不具备的显式状态行为。”不要写“C1 achieves SOTA forecasting accuracy”。

### 完成条件

- [x] learned baselines 三种子四 split 同协议结果
- [x] Persistence 四 split
- [x] C1 seed 1 四 split
- [ ] C1 至少另外两个 seed
- [ ] VegSim 同口径点预测比较或明确的 protocol mismatch（协议不一致）说明
- [ ] 自动表格脚本输出 mean±std 和统计标记

---

## 15. Table 2：EarthNet2023-Africa 独立数据集主表

**一句话目的**：在第二个独立数据集上重新训练并评测各方法，验证 TerraState 的预测能力和核心状态性质不是 GreenEarthNet 上的一次性结果。

### 为什么选它

GreenEarthNet 与 EarthNet2021 复用训练地点、预测器尺寸和大量协议设计，不能被包装成两个独立数据集。EarthNet2023-Africa 在地理区域、生态分布、观测周期和数据配置上更独立，又保持“卫星观测 + 天气驱动 + 多步植被预测”的任务同构性，适合验证主张的外部有效性。

### Table 2 究竟怎样产生：必须重新训练，不是把 Table 1 权重直接拿来预测

Table 1 和 Table 2 对应两套独立训练流程：

```text
GreenEarthNet train
  -> 训练 C0R_G / C1_G / baselines_G
  -> 在 GreenEarthNet IID、OOD-t、OOD-s、OOD-st 上评测
  -> 形成 Table 1，并提供主数据集 Q2-Q4 结果

EarthNet2023-Africa train
  -> 适配数据通道、时间步、天气变量、mask 和 scorer
  -> 从相同类型的通用初始化重新训练 C0R_A / C1_A / baselines_A
  -> 在 EarthNet2023-Africa 官方验证/测试划分上评测
  -> 形成 Table 2；同一套 C0R_A/C1_A 权重再提供 Table 4-6 的 Q2-Q4 精简复验
```

因此，**不是**把 GreenEarthNet 上训练好的 `C1_G` 直接拿到 Africa 测试集做 zero-shot prediction（零样本预测）。那样测到的主要是 domain transfer（域迁移），不是本文所需的跨数据集方法有效性。

主实验保持“同一模型原理、不同数据集独立训练、不同权重”：

- C1 的状态定义、共享递归转移和训练原则保持不变。
- 允许修改数据适配器、输入输出通道、时间分辨率、归一化、mask 和数据集原生 scorer。
- 每个基线也应在 EarthNet2023-Africa 上使用官方权重或按其合理方案重新训练，不能只重新训练 C1。
- 若另外想研究 `C1_G -> Africa` 的迁移能力，应单独增加 `Transfer/zero-shot（迁移/零样本）` 实验，不能替代 Table 2。

### 行

- 数据集官方/公认的 persistence、climatology 和强基线。
- 一个强视频预测基线。
- Contextformer 或同级 transformer 预测器。
- C0R。
- C1。

不需要把所有 GreenEarthNet 基线原样搬过去；核心是包含当地公认强方法和 C0R/C1 严格机制对照。

### 列

```text
Method | Native validation metric(s) | Native test metric(s) | NDVI R² | NDVI RMSE | Params
```

- `Native metric(s)` 用于与该数据集文献公平比较。
- `NDVI R²/RMSE` 用于与 GreenEarthNet 共享行为尺度。
- Table 2 只回答 Q1 预测问题；Africa 权重上的 Q2、Q3、Q4 分别进入 Table 4、5、6，不挤在预测主表中。

### 终稿版式模板（数值先留空）

| Method（方法） | Native val metric↑（原生验证指标） | Native test metric↑（原生测试指标） | NDVI R²↑ | NDVI RMSE↓ | Params（参数量） |
|---|---:|---:|---:|---:|---:|
| Persistence（持续性） | -- | -- | -- | -- | 0 |
| Official baseline A（官方基线 A） | -- | -- | -- | -- | -- |
| Strong video baseline（强视频预测基线） | -- | -- | -- | -- | -- |
| Contextformer / Transformer baseline | -- | -- | -- | -- | -- |
| C0R_A（机制控制组） | -- | -- | -- | -- | -- |
| **TerraState-C1_A (ours)（本文）** | -- | -- | -- | -- | -- |

如果官方原生指标本身包含多个子项，应使用分组表头或拆到补充材料；主文保留 1 个官方总指标和共同 NDVI 指标即可。

### 实施要求

- 从通用初始化分别训练，不使用 GreenEarthNet checkpoint，除非明确把实验定义为 transfer。
- 先审计经纬度、时间、产品和样本来源重叠。
- 只改 dataset adapter、时间步/天气维度、归一化和输出头；不改变 C1 的状态定义与共享转移原则。
- 基线使用同一输入信息和 mask，避免 TerraState 独占未来天气或静态变量。

---

## 16. Table 3：核心机制与消融定位

**一句话目的**：用同参数 C0R/C1 和冻结模型功能干预，定位预测状态、天气驱动和递归事实路径各自贡献了什么。

### 理想矩阵

| Model/intervention（模型/干预） | Type（类型） | Explicit state（显式状态） | Shared transition（共享转移） | Weather forcing（天气驱动） | Recursive factual path（递归事实路径） | Forecast（预测） | Load-bearing（承载） | Continuation（分段一致） | Role（论文作用） |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| Contextformer | 外部/底座基线 | × | × | 可条件输入 | × | ✓ | 不适用 | 不适用 | 普通强预测器参照 |
| C0R | **严格机制控制** | ✓ | ✓ | ✓ | × | ✓ | 待统一 | 弱/失败 | 排除参数量与模块数量解释 |
| **C1 最终模型** | **主模型** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 完整主张 |
| C1 prior-only / `alpha=0` | 功能干预 | 状态被关闭 | 保留但不读出 | ✓ | ✓ | 下降 | 对照项 | 可测 | 证明状态贡献 |
| C1 identity-T | 功能干预 | ✓ | 恒等 | ✓ | ✓ | 下降预期 | 支持性 | 失败预期 | 证明演化重要；有 OOD 混杂 |
| C1 mean weather | 功能干预 | ✓ | ✓ | 均值替代 | ✓ | 下降预期 | ✓ | 可测 | 天气信息量对照 |
| C1 donor weather | 功能干预 | ✓ | ✓ | 匹配错配 | ✓ | 下降预期 | ✓ | 可测 | 条件响应对照 |
| C1 w/o geo | 训练消融，可选 | ✓ | ✓ | ✓ | ✓ | 待测 | 待测 | 待测 | 地理条件贡献 |
| C2 | 可选增强 | ✓ | ✓ + latent consistency | ✓ | ✓ | 待测 | 待测 | 待测 | 仅在 C1 不稳时试验 |
| C3 | 可选增强 | ✓ | ✓ + latent/output consistency | ✓ | ✓ | 待测 | 待测 | 待测 | 仅在显著净收益时采用 |

TerraState-V2 不出现在这个主文矩阵中。若需要保留开发演进，另设补充表 `Table Sx: From V2 to C1（从 V2 到 C1 的版本演进）`，不与严格消融混排。

### 表中必须避免的混淆

- `Contextformer -> C1` 同时变化很多，不是严格单变量消融；它是外部基线。
- `V2 -> C1` 同时改变了状态推进方式和训练/调用语义，是版本演进参考。
- **C0R -> C1 才是回答“recursive factual path 是否产生 continuation consistency”的关键消融。**
- prior-only、identity-T、weather replacement 是对同一已训练模型的功能干预，不应与重新训练的架构消融混成一种实验。

### 数值列建议

主表紧凑报告 `R²`, `full-alpha0 ΔR²`, `actual-donor ΔLoss`, `segmented degradation`。更完整的四 split 和 CI 分别转到 Table 4-6。

### 数值版式模板（数值先留空）

| Model/intervention（模型/干预） | R²↑ | State ΔR²↑（状态贡献） | Weather ΔLoss↑（天气保真） | Seg. degr.↓（分段退化） | Same params?（同参数） | Interpretation（结论） |
|---|---:|---:|---:|---:|:---:|---|
| Contextformer | -- | n.a. | -- | n.a. | n.a. | 外部预测基线 |
| C0R | -- | -- | -- | -- | ✓ | direct-path 机制控制 |
| **C1** | -- | -- | -- | -- | ✓ | 最终模型 |
| C1 prior-only（仅先验） | -- | 参照项 | -- | -- | ✓ | 关闭状态读出 |
| C1 identity-T（恒等转移） | -- | -- | -- | -- | ✓ | 关闭状态演化 |
| C1 mean weather（均值天气） | -- | -- | 参照项 | -- | ✓ | 移除有效天气信息 |
| C1 donor weather（错配天气） | -- | -- | 参照项 | -- | ✓ | 错配条件对照 |

### Table 3-6 的数据集与模型覆盖规则

不需要执行“两个数据集上的所有基线都跑 Q2-Q4”。Q2-Q4 检验的对象不同，适用模型也不同：

| 表 | 检验对象 | GreenEarthNet 主数据集 | EarthNet2023-Africa 第二数据集 | 普通基线是否需要 |
|---|---|---|---|---|
| **Table 3 消融** | 本文机制由什么产生 | **完整消融只在这里做**：Contextformer、C0R、C1、prior-only、identity-T、weather controls | 不重复全套消融；只保留 C0R/C1 核心对照 | Contextformer 作为外部参照；其他基线不需要 |
| **Table 4 / Q2** | C1 的显式状态是否承担输出 | C1 三种子 × 四 split 完整报告；C0R 汇总可留在 Table 3 | 用独立训练的 `C1_A` 做 full vs prior-only 精简复验 | 不需要；普通基线没有同构的状态支路可移除 |
| **Table 5 / Q3** | 模型是否真实使用未来天气 | C1 必做；C0R 与 Contextformer 也运行 actual/donor/mean，形成行为对照 | `C1_A` 必做；再选一个使用天气的强基线作对照 | **需要代表性天气基线**；无天气输入模型填 n.a. |
| **Table 6 / Q4** | 状态能否直接/分段一致推进 | C0R 与 C1 必做，多终点、多分段、多种子 | 独立训练的 `C0R_A/C1_A` 做精简确认 | 不需要；没有可恢复状态接口的模型无法公平做 Q4 |

换句话说：

- **完整 ablation（消融）只放第一个数据集**，这是常规且合理的。
- **第二数据集不是再做一次所有消融**，而是复验决定主旨真假的核心性质：C1 的 Q2、Q3，以及 C0R/C1 的 Q4。
- **Q2 是本文模型内部干预**，不要求所有基线参与。
- **Q3 是天气行为比较**，应加入能够读取天气的代表性基线，否则无法说明 C1 的天气保真是否超出普通条件预测器。
- **Q4 是状态接口测试**，只对 C0R/C1 和真正暴露等价状态接口的同行模型适用，普通预测基线不硬凑。

---

## 17. Table 4：Q2 状态承载

**一句话目的**：检验移除 C1 的动态状态贡献后预测是否稳定变差，从而证明显式状态真实承担输出而不是装饰。

### 行

四个 GreenEarthNet split × 三个 C1 seed；表尾给跨 seed 汇总。第二数据集用独立训练的 `C1_A` 给一组精简复验。C0R 的状态贡献汇总放 Table 3，不要求在 Table 4 展开所有 split。

### 列

```text
Dataset/Split | Model | Full R² | Prior-only R² | ΔR² | ΔRMSE | 95% CI | Load-bearing decision
```

### 统计

- 首选以 tile/geo cluster 为重采样单位，避免像素或 cube 被当作完全独立样本。
- 同时报告 effect size 和 CI，不只报告 p-value。
- 阈值/decision rule 在新增种子结果出来前冻结。

### 当前基础

GreenEarthNet 四 split 已全部通过，现有结果足以建立表结构；待加入多种子和第二数据集区块。

### 终稿版式模板（数值先留空）

| Dataset/Split（数据集/划分） | Model（模型） | Seed（种子） | Full R²↑（完整模型） | Prior-only R²↑（仅先验） | ΔR²↑ | ΔRMSE↑ | 95% cluster CI（聚类置信区间） | Decision（判定） |
|---|---|---:|---:|---:|---:|---:|---|---|
| GreenEarthNet / IID | C1_G | -- | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet / OOD-t | C1_G | -- | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet / OOD-s | C1_G | -- | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet / OOD-st | C1_G | -- | -- | -- | -- | -- | [--, --] | -- |
| EarthNet2023-Africa / Test | C1_A | -- | -- | -- | -- | -- | [--, --] | -- |
| **Across-split/seed（跨划分/种子）** | C1 | all | -- | -- | -- | -- | [--, --] | -- |

---

## 18. Table 5：Q3 天气响应

**一句话目的**：检验模型在真实天气下是否比错配/均值天气更贴近观测，并与可使用天气的代表性基线比较条件响应能力。

### 行

- Overall: actual vs donor；actual vs mean。
- Extreme subset: actual vs donor；actual vs mean。
- Hot-dry interaction：作为边界结果保留。
- GreenEarthNet 上加入 C0R 和 Contextformer 的同干预比较。
- 第二数据集用独立训练的 C1_A 和一个 weather-aware baseline（天气感知基线）做对应比较。

### 列

```text
Dataset/Subset | Model | Comparison | ΔLoss | 95% cluster CI | R²_actual | R²_control | Fidelity decision
```

### 当前应填入的核心事实

- Overall actual vs donor：`ΔLoss = +0.002053`，geo-cluster CI `[+0.000761,+0.003452]`。
- Overall actual vs mean：`ΔLoss = +0.010140`，geo-cluster CI `[+0.004839,+0.015558]`。
- Hot-dry interaction：`-0.000302`，CI `[-0.002841,+0.002582]`，不通过。

表题使用 `Conditional weather-response fidelity`，不要使用 `causal effect`。

### 终稿版式模板（数值先留空）

| Dataset/Subset（数据集/子集） | Model（模型） | Comparison（比较） | ΔLoss↑ | 95% geo-cluster CI（地理聚类置信区间） | R² actual↑（真实天气） | R² control↑（对照天气） | Decision（判定） |
|---|---|---|---:|---|---:|---:|---|
| GreenEarthNet / Overall | Contextformer | Actual vs Mean（真实 vs 均值） | -- | [--, --] | -- | -- | -- |
| GreenEarthNet / Overall | C0R_G | Actual vs Donor（真实 vs 错配） | -- | [--, --] | -- | -- | -- |
| GreenEarthNet / Overall | **C1_G** | Actual vs Donor（真实 vs 错配） | -- | [--, --] | -- | -- | -- |
| GreenEarthNet / Overall | **C1_G** | Actual vs Mean（真实 vs 均值） | -- | [--, --] | -- | -- | -- |
| GreenEarthNet / Extreme | **C1_G** | Actual vs Donor/Mean（真实 vs 对照） | -- | [--, --] | -- | -- | -- |
| GreenEarthNet / Hot-dry | **C1_G** | Interaction（交互效应） | -- | [--, --] | n.a. | n.a. | -- |
| EarthNet2023-Africa / Overall | Weather baseline_A | Actual vs Control（真实 vs 对照） | -- | [--, --] | -- | -- | -- |
| EarthNet2023-Africa / Overall | **C1_A** | Actual vs Control（真实 vs 对照） | -- | [--, --] | -- | -- | -- |

现有正式数值应由结果脚本填入，不在人工模板中重复抄录。`ΔLoss > 0` 的方向必须在表注定义，例如 `Loss_control - Loss_actual`，避免正负号歧义。

---

## 19. Table 6：Q4 持续推进与组合一致性

**一句话目的**：比较 C0R/C1 的直接推进与分段推进，证明 C1 的状态可以暂停后继续且不会产生明显路径依赖。

### 行

- C0R 与 C1 分开。
- 每个 endpoint / horizon。
- 每个 partition 方案，例如 2 段、3 段、更多不均匀分段。
- 多 seed 汇总。
- GreenEarthNet 新确认评测与 EarthNet2023-Africa 分区。

### 列

```text
Model | Horizon | Partition | Direct RMSE | Segmented RMSE | Relative degradation | Direct-composed pooled R² | 95% CI | Gate
```

### 必须补的修正

- 删除/降级旧 per-cube R²（逐 cube 决定系数）`G_abs`，主结论使用 pooled R²/RMSE（汇总决定系数/均方根误差）和直接/分段各自准确度。
- 明确记录：旧 per-cube R² 腿产生 `4/19 FAIL`，但该统计量因低方差 cube 导致无界负值而被确认存在规格错误；同期 pooled-RMSE 腿 `19/19 PASS`，同批封存统计量重算 pooled-R² 后三种资格口径均 `19/19 PASS`。**有效结论是修正后的端点非劣审计 19/19 通过。**
- 新 protocol（协议）仍须在看结果前锁定并写入 JSON manifest（清单），用于多种子和独立数据增强。
- 主文同时报告失败的 C0R，不只展示 C1 pass（通过）。

### 当前基础

锁定集 476 cubes / 40 tiles 已证明 C1 与 C0R 有量级差异：C1 单臂四门通过，C0R 失败关键门，C1 分段退化约 0.8%-1.2%，C0R 约 9.1%-14.7%；修正后的事实端点非劣审计为 19/19 通过。因此 Table 6 已有支撑 C4 的核心证据，后续多种子和 EarthNet2023-Africa 用于提高统计稳定性与外部有效性。

| 当前锁定 Q4 结论 | 结果 | 论文处理 |
|---|---:|---|
| C1 单臂 continuation gates（持续推进门） | 4/4 PASS | 主文正面证据 |
| C0R 关键 continuation gates | FAIL | 主文机制对照 |
| 原 per-cube R² `G_abs` 腿 | 4/19 FAIL | 规格错误，仅保留审计记录 |
| 同期 pooled-RMSE 腿 | 19/19 PASS | 有效端点非劣证据 |
| 修正 pooled-R² 重算 | 19/19 PASS（三种资格口径一致） | 有效端点非劣证据；注明为规格诊断后的修正结果 |

### 终稿版式模板（数值先留空）

| Dataset（数据集） | Model（模型） | Horizon（时距） | Partition（分段） | Direct RMSE↓（直接） | Segmented RMSE↓（分段） | Rel. degr.↓（相对退化） | Direct-composed pooled R²↑（终态一致） | 95% CI | Gate（门控） |
|---|---|---:|---|---:|---:|---:|---:|---|---|
| GreenEarthNet-confirm（新确认集） | C0R | -- | 2 segments（2 段） | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet-confirm（新确认集） | C0R | -- | 3 segments（3 段） | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet-confirm（新确认集） | **C1** | -- | 2 segments（2 段） | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet-confirm（新确认集） | **C1** | -- | 3 segments（3 段） | -- | -- | -- | -- | [--, --] | -- |
| EarthNet2023-Africa | C0R | -- | -- | -- | -- | -- | -- | [--, --] | -- |
| EarthNet2023-Africa | **C1** | -- | -- | -- | -- | -- | -- | [--, --] | -- |

若 horizon/partition 组合很多，主表只保留三个代表终点和两种分段，完整网格放 `Table Sx`；不要把几十行塞进主文导致核心量级看不出来。

---

## 20. Table 7：复杂度与运行成本

**一句话目的**：量化可保存状态和分段推进带来的参数、显存、速度与存储代价，回答新增能力是否具有合理工程成本。

### 行

至少包括 Contextformer、PredRNN、C0R、C1。C0R/C1 参数应相同，由实测确认；V2 仅在补充材料可选加入。

### 列

```text
Method | Params | FLOPs/sample | Peak VRAM | Train time/epoch | Direct inference | Segmented inference | State size
```

### 计量规则

- 固定 batch size、输入尺寸、horizon、GPU、精度模式和 dataloader 配置。
- 报告均值和预热后的标准差/分位数。
- `State size` 给出保存一个中间 runtime state 的 MB，直接支撑 pause/resume 的工程意义。
- segmented 比 direct 多出的调用开销必须诚实报告。

### 终稿版式模板（数值先留空）

| Method（方法） | Params↓（参数量） | FLOPs/sample↓ | Peak VRAM↓（峰值显存） | Train time/epoch↓（训练） | Direct infer.↓（直接推理） | Segmented infer.↓（分段推理） | State size↓（状态大小） |
|---|---:|---:|---:|---:|---:|---:|---:|
| PredRNN | -- | -- | -- | -- | -- | n.a. | n.a. |
| Contextformer | -- | -- | -- | -- | -- | n.a. | n.a. |
| C0R | -- | -- | -- | -- | -- | -- | -- |
| **TerraState-C1** | -- | -- | -- | -- | -- | -- | -- |

所有速度在表注写明 GPU、batch size（批大小）、input shape（输入尺寸）、forecast horizon（预测时距）和 precision（数值精度）。

---

# 第五部分：数据集与比较策略

## 21. 数据集角色冻结

| 数据集 | 与 GreenEarthNet 的关系 | 论文角色 | 要做的实验 | 是否计作独立数据集 |
|---|---|---|---|:---:|
| **GreenEarthNet** | 当前主数据集 | 完整 Q1-Q4、全消融、四 split、主可视化 | Table 1、3-7；Fig. 3、5-8 | 主数据集 |
| **EarthNet2023-Africa** | 地理、生态与协议更独立，任务仍同构 | 独立外部验证 | 各方法独立训练形成 Q1 主表；用 C1/C0R 权重精简复验 Q2-Q4 | **是** |
| EarthNet2021 | 与 GreenEarthNet 强同源/增强前代关系 | 旧协议兼容性或补充实验 | official RGB+NIR/ENS 或清楚标为 NDVI-only | **否** |
| DeepExtremeCubes | 全球极端事件数据，任务协议差异较大 | 可选压力测试 | 若重新定义多步协议，测试极端事件稳健性 | 可算外部，但不宜作首选第二主表 |

### 指标原则

每个数据集同时使用两套口径：

1. **原生指标**：与该数据集文献和官方榜单比较。
2. **共同指标**：NDVI R²、RMSE、NSE，以及 Q2-Q4 行为指标，用于跨数据集比较 TerraState 的性质。

如果做 EarthNet2021，官方任务预测 RGB+NIR 并计算 ENS；只预测 NDVI 的结果不能直接与完整 ENS 排名比较，必须分栏并写清任务差异。

### 第二数据集是否换模型框架

不换主模型。第二数据集应直接使用同一 TerraState-C1 原理和 C0R/C1 配置，只做必要的数据适配。若换成另一个强基线后再“嫁接我们的机制”，会使跨数据集结果无法判断来自机制还是框架，也削弱“我们提出一个世界模型”的身份。

合理做法是：

- 当地强方法作为外部比较；
- Contextformer/同级预测器作为普通预测参照；
- C0R/C1 作为本文内部严格机制对照；
- 可选做一次 encoder swap 放补充材料，证明机制不完全绑定 PVT-v2，但不把它变成主线必需项。

---

# 第六部分：实施优先级与完成标准

## 22. P0：先封住会直接击穿主线的缺口

### P0-1 冻结 C1 论文身份与协议

**动作**：冻结 C1 配置、输入输出、损失、checkpoint 命名和四项主张；建立一份 machine-readable experiment registry，记录 seed、commit、manifest、checkpoint、scorer 和结果 JSON。

**完成标准**：后续所有图表都能从 registry 追溯到单一代码提交和结果文件；不再出现 V2/C1 数字混用。

### P0-2 补 C1 多种子

**动作**：至少新增两个独立 seed，优先复用基线的 `27/42/97` 或在运行前固定等价集合；四 split 全评测。

**输出**：Table 1 mean±std、Fig. 5 horizon CI、Table 4 Q2 多种子、Table 6 Q4 多种子。

**原因**：当前外部基线三种子而 C1 单种子，是最容易被审稿人直接指出的不公平项。

### P0-3 扩展确认 Q4

**动作**：在未查看结果的新 manifest（清单）或独立数据集上冻结 endpoints（终点）、partitions（分段方案）、segment counts（分段数）、pooled R²/RMSE（汇总指标）、阈值、CI（置信区间）和排除规则后再运行。

**输出**：Fig. 8、Table 6 的确认性结果，以及 preregistration/protocol JSON。

**原因**：Q4 是 TIP 新叙事的中心。旧 per-cube R² gate（逐 cube 决定系数门）的规格问题已经由封存充分统计量诊断并以 pooled 口径得到 19/19；新增实验负责检验该结论能否跨 seed（种子）和跨数据保持，而不是重新决定旧错误门是否通过。

### P0-4 补齐 C0R/C1 干净对照

**动作**：同 seed、同预算、同输入和 checkpoint 选择规则，在四 split 汇总 Q1/Q2/Q4；确认参数量完全一致。

**输出**：Table 3 主消融和 Fig. 8 对照曲线。

**原因**：这是证明贡献来自 recursive shared transition 训练机制，而不是新增参数的最关键对照。

### P0-5 补直接同行的协议级比较

**动作**：把 VegSim 和 EO-WM 纳入正式 related-work audit（同行工作审计），逐项记录输入、输出粒度、数据集、指标、概率性、状态接口和代码/权重可用性。VegSim 与本任务最接近，应优先用其公开协议重跑，或将 C1 的密集预测聚合到相同 minicube-level（小立方体聚合）口径比较 point metrics（点预测指标）。

**输出**：同行能力对照矩阵、协议差异说明、可比较指标结果；根据任务一致程度放 Table 1/3 或补充材料。

**原因**：完成于 2024 基线集合的 E1 仍然有效，但不足以单独覆盖 2026 年已经出现的“遥感世界模型”直接同行。EO-WM 的四通道 EarthNet2021 协议与本项目不完全一致，不得直接抄其论文数字与 C1 排名。

### P0-6 先生成 GreenEarthNet 五张结果图草稿

**动作**：先独立绘制不依赖新实验的 Fig. 1-2，再从已有 JSON 和预测缓存生成 Fig. 3、5-8 的草图，先检查数据是否足够，再做视觉精修。Fig. 4 等第二数据集结果完成后再封版。

**输出**：固定绘图 CSV/JSON、样例清单、可复现脚本和初版 PDF。

**原因**：尽早暴露逐 horizon、per-sample 或空间缓存缺失，避免所有训练结束后才发现无法作图。

---

## 23. P1：完成 TIP 级外部有效性与论文闭环

### P1-1 EarthNet2023-Africa 数据审计与适配

**动作**：核对许可、split、变量、时间步、云/无效 mask、天气可用性和空间重叠；编写独立 adapter 与 scorer wrapper。

**完成标准**：一个小规模 overfit test、一个 deterministic evaluation test、数据统计表和重叠审计报告全部通过。

### P1-2 第二数据集强基线

**动作**：优先运行官方/公认强基线、Persistence/Climatology、一个视频预测器、Contextformer 或同级 transformer；所有方法共享输入信息与 scorer。

**输出**：Table 2 baseline 区块。

### P1-3 第二数据集训练 C0R/C1

**动作**：从相同通用初始化训练 C0R/C1，多种子；除 adapter 和必要维度外不改变状态机制。

**输出**：Table 2 的 Q1 预测主表、Fig. 4 第二数据集定性结果与 Fig. 5 时距曲线；同一套 Africa 权重进一步产生 Table 4 的 Q2、Table 5 的 Q3、Table 6 的 Q4 精简复验，并视版面进入 Fig. 6-8 的第二数据集小面板。

**完成标准**：C1 保持有竞争力预测，Q2 状态承载、Q3 天气响应和 Q4 分段一致至少在独立数据上完成精简复验；若某项不成立，必须据实收窄主张。

### P1-4 复杂度与工程接口

**动作**：实现/整理 `initialize/advance/decode/branch`；测量 Params、FLOPs、VRAM、推理时间和 state size。

**输出**：Fig. 2 对应的可执行 demo、Table 7。

### P1-5 补一个克制的不确定性评测

**动作**：C1 继续作为最终状态模型，不改造成 diffusion model（扩散模型）。先利用多种子 checkpoint 构成 deep ensemble（深度集成），报告 prediction interval coverage（预测区间覆盖率）与 sharpness（区间锐度）；若计算资源允许，再增加只替换 decoder 的 `C1-UQ` quantile head（分位数输出头），状态转移和 Q2-Q4 机制保持不变。

**输出**：补充材料中的 calibration plot（校准图）和 CRPS/Pinball/PICP 等指标；如结果稳定，可在 Table 2/7 增加紧凑列。

**边界**：多种子 spread（离散度）主要反映 epistemic uncertainty（认知不确定性），不能冒充完整 aleatoric uncertainty（数据不确定性）。这一项用于回应 EO 未来多解性，不提升为第二条主线。

### P1-6 重写论文

按如下顺序修改，而不是在旧稿上零散加段落：

1. 标题、摘要、引言贡献点先统一主线。
2. 方法改为 C1 和 runtime state，删除“does not recursively roll out”。
3. 实验改为 Q1-Q4 + 两数据集 + C0R/C1。
4. 结果按“预测 -> 承载 -> 驱动 -> 连续”排序。
5. 讨论中明确 context prior（上下文先验支路）、非因果天气分支、有限 horizon（预测时距）和计算成本。
6. 最后再更新结论、图注、附录和所有旧数值。

当 **P0 全部完成，并且 P1-1 至 P1-3 的独立数据集核心结果成立** 时，这条 TIP 主叙事才达到最低可信闭环：不是只靠定义自证世界模型，而是有同协议预测能力、严格机制对照、持续推进证据和跨数据集复现。Fig. 1-8、Table 1-7 随后应全部封版，不能只完成实验而缺少可审阅呈现。

---

## 24. P2：增强项，不应阻塞主线

| 项目 | 何时值得做 | 成功后放哪里 | 失败如何处理 |
|---|---|---|---|
| C2 latent consistency | C1 多种子 Q4 波动较大 | Table 3/6 或补充材料 | 不替换 C1，报告试验即可 |
| C3 output consistency | C2 改善状态但输出仍不一致 | Table 3/6 或补充材料 | 若伤害 Q1 则放弃 |
| w/o geography 训练消融 | 需要拆解静态条件贡献 | Table 3/补充材料 | 作为分析，不影响主线 |
| encoder swap | 审稿风险集中在“仅依赖 PVT” | 补充材料 | 一次代表性实验足够 |
| EarthNet2021 legacy | 需要与旧文献/ENS 协议衔接 | 补充材料 | 不计作独立数据集 |
| DeepExtremeCubes | 主结果完成后强化极端事件讨论 | 补充材料或额外表 | 不为它重写整条主线 |
| 下游状态探针 | 有明确生态变量或任务可测 | 分析节/补充材料 | 避免无目标 linear probing |

这些实验的原则是“增强解释或覆盖”，不能反过来让论文重新分裂为多个主线。尤其不要同时把极端事件、因果反事实、通用 backbone 和下游迁移都写成核心贡献。

---

# 第七部分：执行产物与论文写作控制

## 25. 每个实验必须留下的四类产物

1. **协议**：config、manifest、seed、commit、环境和预先定义的指标/阈值。
2. **原始结果**：逐 cube/tile/horizon 的 machine-readable JSON/Parquet，而不只有终端均值。
3. **机械汇总**：表格 CSV/Markdown/LaTeX 由脚本生成，延续 A08 的做法。
4. **图形输入**：绘图脚本只读取冻结结果，不在脚本内重新选择样例或改变统计口径。

建议每个主实验使用统一目录：

```text
results/<experiment_id>/
  protocol.json
  manifest.txt
  metrics_per_sample.parquet
  metrics_summary.json
  predictions/               # 仅保存固定可视化子集或可重建索引
  table.csv
  figure_data.csv
  provenance.txt
```

## 26. 图表排版共同规则

- 所有图统一模型颜色、split 顺序和指标箭头。
- 地图/NDVI 使用相同数值范围；error map 单独色标。
- 主表数字统一小数位，mean±std 与 CI 不混写。
- 最优值加粗、次优值下划线；C1 不是最佳时不人为突出其预测数值，可用模型名加粗表示本文方法。
- 图注独立可读：写清数据集、样本量、seed、CI 单位、mask 和比较方向。
- 主文只放结论所需面板，完整 split/seed/horizon 网格放补充材料。
- 不用大面积流程装饰替代结果；Fig. 3-8 必须以真实统计和真实预测为主体。

## 27. 主张到证据的最终映射

| 论文句子 | 必须紧邻引用的证据 | 不满足时怎么办 |
|---|---|---|
| TerraState is competitive in multi-step EO forecasting | Table 1、Table 2、Fig. 3-5 | 收窄为单数据集或特定 split |
| Its explicit state is load-bearing | Fig. 6、Table 4 | 不得只用 attention/可视化代替干预 |
| It responds to supplied future weather | Fig. 7、Table 5 | 写 conditional，不写 causal |
| It supports continuation-consistent rollout（支持持续推进一致性） | Fig. 8、Table 6、C0R/C1 | 当前锁定证据支持 GreenEarthNet 单种子结论；若后续跨种子/跨数据不稳定，则收窄泛化范围，不能抹去冲突结果 |
| The property comes from the proposed training mechanism | Table 3、C0R/C1 同预算对照 | 若 C0R/C1 差异不稳，需调整机制或主张 |
| The finding generalizes beyond one benchmark | Table 2 | 无独立数据集就删除该句 |

---

## 28. 最终验收清单

### 模型与协议

- [ ] C1 名称、架构、默认配置和 checkpoint 选择规则冻结。
- [ ] runtime state 与四个 API 和 Fig. 2 完全一致。
- [ ] C0R/C1 唯一关键差异有代码级和配置级记录。
- [x] 旧 Q4 的 per-cube R² 规格错误与 pooled 修正结果已形成审计记录；有效端点结论为 19/19。
- [ ] 新增种子/数据集的 Q4 protocol（协议）在结果生成前冻结。

### 实验

- [x] E1 可获得 learned baselines 同协议三种子四 split 完成。
- [x] C1 seed 1 四 split Q1 完成。
- [x] C1 四 split Q2 完成。
- [x] C1 Q3 actual/donor/mean 完成。
- [x] C1/C0R 锁定 Q4 完成：C1 四门通过、C0R 失败关键门；per-cube R² 规格错误已识别，修正后的 pooled 端点审计 19/19 通过。
- [ ] C1 另外两个 seed 完成。
- [ ] C0R/C1 四 split 同预算对照完成。
- [ ] 按预先冻结 pooled 规格完成 Q4 多种子与独立数据增强确认。
- [ ] VegSim 完成协议级对齐、可复现比较或明确不可比说明；EO-WM 完成任务差异审计。
- [ ] EarthNet2023-Africa 的基线、C0R/C1 与核心行为验证完成。
- [ ] 效率评测完成。
- [ ] 不确定性校准至少完成 deep-ensemble 版本，或在限制中明确不覆盖概率未来。

### 图表与稿件

- [ ] Fig. 1-8 均由冻结定义、代码或结果生成并有可追溯输入。
- [ ] Fig. 3-4 含 GT、Persistence、强基线、Contextformer、C1、误差图及短/中/长时距，不以单一漂亮样例代替定性评测。
- [ ] Table 1-7 机械生成或至少有唯一数据源。
- [ ] 旧 AAAI 的 Q1-Q3、V2、非递归描述和旧数字全部清理。
- [ ] 摘要、引言、方法、实验和结论使用同一四主张顺序。
- [ ] 限制部分明确：非 SOTA、context prior（上下文先验支路）、非因果、有限 horizon（预测时距）、Q4 原规格错误及修正后的 19/19。

---

## 29. 本轮自查后新增的风险判断

| 风险 | 为什么真实存在 | 本文应如何处理 | 优先级 |
|---|---|---|---|
| “天气驱动递归潜状态”已被 VegSim 覆盖 | VegSim 已公开 recurrent latent dynamics（递归潜动力学）和 scenario-conditioned simulation（情景条件模拟） | 不再声称这两个元素单独首创；强调 20 m 密集状态、Q2 承载和 Q4 分段一致，并做同协议比较 | **P0** |
| “天气响应评测”已被 EO-WM 覆盖 | EO-WM 已提出 extreme/paired weather-response diagnostics（极端/配对天气响应诊断） | 将 Q3 定位为四项状态证据之一，不把它单独写成唯一贡献；必要时复用公开 benchmark 交叉验证 | **P0/P1** |
| 当前 C1 是确定性模型 | 遥感未来受云、管理活动和未观测变量影响，多解性客观存在 | 不强行改成扩散模型；补深度集成校准，资源允许时做 C1-UQ 分位数头，并明确主贡献仍是状态连续性 | **P1** |
| “高分辨率空间状态”可能只停留在名词 | 若只报告区域平均 R²，审稿人看不到空间状态的价值 | Fig. 3-8 必须包含真实像素图、时间过程或样本分布；补 land-cover/boundary/heterogeneity（地类/边界/异质性）分层误差 | **P0/P1** |
| pause/resume 可能只是数学重排 | 没有实际状态序列化接口时，工程能力容易被认为是图示包装 | 实现 state save/load demo，验证不重编码历史即可继续，并在 Fig. 2 对齐接口、Table 7 报 state size 与恢复开销 | **P1** |
| context prior（上下文先验支路）削弱“状态自足”表述 | 输出不是只由 `z` 解码 | 将 runtime state（运行时状态）明确定义为 `{prior（先验）,z（动态状态）,geo（地理信息）,offset（偏移）}`，依靠 Q2 证明动态状态承载，绝不声称 `z` 完备 | 已控制 |
| 图表数量看似足够但证据重复 | 12 个图表若只是同一 R² 的不同画法，不增加可信度 | 每张图表固定一个审稿问题；预测、承载、驱动、连续、泛化、效率各自有独立证据 | 已控制 |
| V2 稀释最终模型身份 | V2/C1 同时大量出现会像两套方法 | 主文只称 C1 为 TerraState；V2 仅保留代码档案和可选补充表 | 已控制 |

### 自查后的最终增补结论

1. **预测定性图是必需项**，已明确由 Fig. 3-4 分别承担两个数据集，并在 Fig. 6-8 保留行为对应的空间案例。
2. **V2 不是 TIP 主文必需项**，已从 Table 1 和 Table 3 主模板撤下；C0R 才是不能删的机制对照。
3. **7 张表均已有可直接照填的版式模板**，数值空位使用 `--`，不适用项使用 `n.a.`。
4. **英文术语均增加中文释义原则和术语表**；正式英文稿再移除中文括注。
5. **新增 2026 直接同行风险**：后续不能只对标 Contextformer，需要至少协议级回应 VegSim 与 EO-WM。
6. **新增不确定性边界**：它是有价值的补强，但不能吞掉“可复用空间状态”这条唯一主线。

---

## 30. 最终定位复述

TerraState 的 TIP 版本不靠“我们把预测器叫作世界模型”成立，也不靠自定义一把只对自己有利的尺子成立。它的论证应当是：

> 许多遥感时序模型仍以固定窗口预测精度为主要目标，近期工作虽已引入概率生成、递归潜状态和天气情景模拟，但能生成或分支未来仍不自动证明模型维护了一个可保存、可审计且分段一致的高分辨率世界状态。TerraState 因此把显式空间预测状态设为模型的一等对象，并用共享的天气驱动转移持续推进它。我们不仅比较预测精度，还检验该状态是否真实承担输出、是否响应已知天气，以及直接推进与暂停后继续是否一致。C0R/C1 的同构对照用于定位机制来源，独立数据集用于证明这种能力不是单一基准上的偶然现象。

这条主线比 AAAI 原稿更高的地方，不是把“世界模型”四个字写得更大，而是**模型从固定窗口预测器升级为可持续调用的状态系统，证据从 Q1-Q3 的局部性质升级为预测、承载、驱动、连续四项闭环，并进一步要求严格机制对照和跨数据集复现。**

只要后续严格按本总纲补齐多种子、新 Q4 和独立数据集，现有代码无需推倒重做；主要工作是把已经成立的 C1 机制变成统计充分、外部有效、图表清楚且主张克制的一篇完整 TIP 论文。
