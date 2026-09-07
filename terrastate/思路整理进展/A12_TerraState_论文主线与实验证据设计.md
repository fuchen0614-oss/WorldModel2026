# TerraState：研究主线、方法主张与实验证据设计

> **文档用途**：本文档冻结 TerraState 论文的科学问题、方法身份、核心主张、实验协议、图表结构与完成标准。所有正文、实验和可视化均围绕同一条研究主线组织。  
> **模型名称**：正文中的 `TerraState` 默认指最终模型 `TerraState-C1`。  
> **证据状态**：`已完成` 表示已有可追溯结果；`部分完成` 表示核心结果已有但缺多种子或跨数据验证；`待完成` 表示尚无可用于论文结论的正式证据。  
> **图表体系**：主文按 **8 Figures（图）+ 7 Tables（表）** 组织。图表数量不是目标，完整且不重复的证据链才是目标。

---

# 第一部分：论文的唯一研究主线

## 1. 论文身份

TerraState 是一个面向高分辨率地球观测序列的天气驱动世界模型。它从稀疏、受云遮挡且部分可观测的历史遥感影像中初始化显式空间预测状态，并在给定未来天气驱动下，通过共享的变跨度状态转移持续推进该状态。

本文不把“能够生成未来影像”直接等同于“拥有世界模型”。TerraState 对世界状态提出更强、可证伪的要求：状态不仅要支持预测，还要真实承担预测结果、响应提供的外部天气、能够在中间时刻保存和继续使用，并在相同天气路径下使直接推进与分段推进得到近似一致的未来。

因此，论文的研究对象不是某个网络隐藏层是否有趣，而是：

> **构建并验证一个具有可复用空间预测状态的天气驱动遥感世界模型。**

## 2. 核心科学问题

### 2.1 最终表述

> **在部分可观测、天气驱动的高分辨率地球观测场景中，能否构建一个遥感世界模型，学习真正面向未来的空间预测状态，使不同时间跨度的状态转移能够组合，并使中间状态继续承担后续预测？**

英文建议表述：

> **Can a weather-driven Earth-observation world model learn an explicit spatial predictive state that remains sufficient for future prediction and supports compositional state transitions across different temporal spans under partial observability?**

### 2.2 这项科学问题包含什么

该问题包含五个不可拆开的部分：

1. **Partial observability（部分可观测性）**：卫星观测受云、采样周期、缺测和未观测人类活动影响，单帧影像不是完整地表状态。
2. **External forcing（外部驱动）**：天气是推动植被和地表变化的重要外生输入。模型应当在给定天气路径下推进状态，但天气不是智能体动作。
3. **Spatial predictive state（空间预测状态）**：模型学习的是保留像素级空间结构、能够支撑未来预测的状态，而不是仅用于一次前向计算的普通隐藏特征。
4. **Variable-span transition（变跨度状态转移）**：同一状态转移算子能够处理不同长度的天气片段，而不是为每个预测终点学习互不相关的映射。
5. **Continuation and composition（持续推进与组合）**：直接处理完整时间段与依次处理若干子时间段，应当在保持预测准确的前提下到达近似一致的终点。

### 2.3 为什么固定时距预测不足以回答这个问题

标准遥感预测通常学习：

```text
history + future weather -> fixed future observations
```

该形式可以得到准确输出，但准确输出本身不能证明模型维护了可继续使用的世界状态。模型可能：

- 针对每个 horizon（预测时距）直接从历史特征计算终点；
- 让所谓动态状态被 context prior（上下文先验）旁路，使状态本身不承担输出；
- 使用天气作为静态条件标签，而没有形成稳定的驱动响应；
- 在一次完整调用时预测准确，但从中间状态继续时产生明显路径依赖；
- 直接推进和分段推进都输出合理图像，却实际上表示了两个不一致的内部世界。

因此，世界模型的关键问题不是“能否一次性预测未来”，而是：

> **模型是否维护了一个能够代表当前世界、接受外部驱动并继续生成未来的状态。**

### 2.4 可持续推进状态的科学意义

不同时间跨度的状态转移能否组合，检验的是模型是否学到了稳定的动力学表示。如果：

```text
T_{u[a:c]}(s_a) ≈ T_{u[b:c]}(T_{u[a:b]}(s_a)),  a < b < c
```

那么在同一天气路径下，从 `a` 直接推进到 `c`，与先推进到 `b`、保存状态、再继续到 `c`，应当得到近似一致的状态和预测。

这一性质具有三层意义：

1. **表示意义**：中间状态确实保留了后续预测所需的信息，而不是只服务于当前输出。
2. **动力学意义**：状态转移不是相互独立的终点回归器，而是能够跨时间跨度组合的共享演化算子。
3. **运行意义**：模型可以在新天气预报到达时从当前状态继续，无需重复读取完整历史；也可以从同一状态出发比较不同天气条件下的未来。

本文检验的是上述状态表示和条件动力学性质，不把结果夸大为完整物理模拟、因果反事实或决策规划。

## 3. 为什么属于世界模型研究

### 3.1 世界模型的操作性定义

在本文范围内，一个天气驱动的遥感世界模型至少需要具备：

```text
观测编码：历史地球观测 -> 当前空间预测状态
状态转移：当前状态 + 外部天气路径 -> 未来状态
状态读出：未来状态 -> 可验证的未来地球观测
状态复用：状态可以保存、恢复、续推和条件分支
行为验证：预测、承载、驱动响应和持续一致均可被证伪
```

TerraState 的世界模型身份由上述可运行结构和 Q1-Q4 证据共同支撑，而不是由名称或视觉上是否像生成模型决定。

### 3.2 “预测状态学习”与“世界模型”的关系

Predictive state learning（预测状态学习）是 TerraState 的技术基础，不是与世界模型相互排斥的另一个类别：

- **研究对象**是天气驱动的遥感世界模型；
- **核心内部表示**是显式空间预测状态；
- **核心动力学机制**是共享变跨度状态转移；
- **核心训练方法**是 recursive factual supervision（递归事实监督）；
- **核心行为性质**是状态承载、天气响应和持续推进一致性。

规划和论文正文均建议避免“一等建模对象”这一不直观说法，统一表述为：

> **TerraState 把空间预测状态作为模型的核心训练对象和运行接口，而不是一次性预测过程中的普通隐藏特征。**

### 3.3 世界模型范围

TerraState 应被准确限定为：

> **a domain world model of satellite-observed vegetation and land-surface dynamics（卫星观测植被与地表动力学的领域世界模型）**

该限定意味着：

- 模型描述的是遥感可见的植被和地表状态，不声称覆盖完整大气、海洋、土地利用与人类社会系统；
- 天气是模型使用的外生驱动，不声称由模型联合预测；
- 未观测管理活动、灾害、传感器误差和云遮挡构成不可约不确定性；
- 当前输出是确定性或条件期望型预测，不声称完整刻画未来概率分布；
- 状态是任务相关的预测状态，不声称等同于真实世界的完备物理状态。

## 4. 论文题目与摘要级主旨

### 4.1 建议题目

**TerraState: A Weather-Driven Earth Observation World Model with Continuation-Consistent Predictive States**

题目中三个关键信号分别是：

- `World Model（世界模型）`：明确本文是在构建模型，而不是只研究现有网络表示；
- `Continuation-Consistent Predictive States（持续推进一致的预测状态）`：点出最有辨识度的科学性质；
- `Weather-Driven Earth Observation（天气驱动地球观测）`：限定领域、观测方式和外部驱动。

### 4.2 一句话主旨

> **TerraState 学习一个受天气驱动、真实承担未来预测且可持续推进的空间世界状态，并通过直接/分段路径的一致性检验其跨时间组合能力。**

### 4.3 摘要级中文草案

高分辨率地球观测预测通常从固定历史窗口生成预设时间范围内的未来影像，但准确的固定时距预测并不必然意味着模型维护了能够继续使用的世界状态。本文研究在稀疏、受云遮挡且部分可观测的遥感序列中，如何学习受未来天气驱动的显式空间预测状态。我们提出 TerraState，一个面向植被与地表动力学的天气驱动地球观测世界模型。TerraState 通过共享的变跨度状态转移推进空间状态，并使用递归事实监督，使真实未来标签经由中间状态和多段转移直接监督模型，从而把“中间状态必须继续承担后续预测”写入训练路径。除多步预测精度外，我们从状态承载、天气条件响应以及直接/分段推进一致性三个方面检验其世界模型性质。实验将在 GreenEarthNet 和独立地球观测数据集上，与遥感预测、视频预测和天气感知模型进行同协议比较，并通过同参数的 C0R/C1 对照隔离递归事实监督的作用。该研究将遥感世界模型的评价从“能否生成合理未来”推进到“是否维护了可保存、可续推、受外部驱动且跨时间分段一致的空间预测状态”。

### 4.4 可直接使用的论文定位段落

现有地球观测预测方法主要关注从固定历史窗口生成给定时距的未来观测，近期遥感世界模型进一步引入概率生成、天气条件和情景模拟。然而，能够生成未来并不自动意味着模型维护了一个可复用的世界状态：内部表征可能未真正承担输出，也可能只能在训练规定的完整窗口内工作，一旦在中间时刻保存并继续推进便发生路径依赖。为此，我们提出 TerraState，一个面向高分辨率植被与地表动力学的天气驱动地球观测世界模型。TerraState 把显式空间预测状态作为核心训练对象和运行接口，并通过共享的变跨度状态转移支持直接推进、暂停继续和条件分支。尤其是，递归事实监督使真实未来标签经过中间状态和多段转移监督模型，从而把“中间状态必须继续代表当前世界”写进事实预测路径。除标准多步预测外，我们进一步检验状态承载、天气响应及直接/分段推进一致性，从而将遥感世界模型的评价从“是否产生合理未来”扩展到“内部状态是否能够持续代表并推进同一个观测世界”。

---

# 第二部分：相关研究中的准确位置

## 5. 相邻研究路线

| 路线 | 代表工作 | 典型能力 | 与本文最接近之处 | TerraState 必须证明的差异 |
|---|---|---|---|---|
| 高分辨率遥感预测 | [GreenEarthNet / Contextformer](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html) | 多模态历史编码、像素级多步预测、OOD 评测 | 相同数据和基础预测任务 | 不只输出固定窗口未来，还维护可续推状态 |
| 视频预测 | ConvLSTM、PredRNN、SimVP | 强时空建模、递归或并行生成未来帧 | 可作为预测精度和长时退化基线 | 普通视频预测不自动具有显式、可恢复且受天气驱动的世界状态 |
| 概率地球观测生成 | [EO-WM](https://arxiv.org/abs/2606.27277) | 多光谱概率预测、天气响应和不确定性 | 都关心遥感未来与外部天气 | TerraState 聚焦密集空间状态、状态承载和直接/分段一致性 |
| 天气情景植被模拟 | [VegSim](https://arxiv.org/abs/2606.21961) | 潜在状态、递归动力学、天气情景和分位数预测 | 是最接近的世界模型同行 | TerraState 必须强调像素级空间状态、事实路径监督和状态组合审计 |
| 遥感理解与生成统一模型 | [RS-WorldModel](https://arxiv.org/abs/2603.14941) | 文本、变化理解、未来场景生成 | 名称和世界模型愿景相邻 | 本文专注可定量验证的连续地表动力学，不以语言条件和感知质量为核心 |

## 6. 不应采用的宽泛缺口

以下说法风险过高，不应写入摘要或引言：

- “现有遥感模型都不能递归预测”；
- “现有遥感世界模型都不使用天气”；
- “首次将潜状态用于植被预测”；
- “首次进行天气情景模拟”；
- “只要能够预测未来就是世界模型”。

更准确的研究缺口是：

> **已有方法越来越擅长生成未来、使用天气或模拟条件情景，但高分辨率内部状态通常没有被明确设计为可保存、可继续推进且可审计的模型接口；同一状态在不同时间分段路径下是否持续代表同一个观测世界，也缺少直接验证。**

## 7. 本文与相邻方法的关系

- 相对 Contextformer：TerraState 从 fixed-window predictor（固定窗口预测器）发展为具有显式运行状态的 weather-driven simulator（天气驱动有状态模拟器）。
- 相对视频预测基线：TerraState 不以单纯更高 R² 为唯一目标，而要求中间状态具备承载、驱动响应和持续推进性质。
- 相对概率式地球观测世界模型：TerraState 当前不竞争完整概率生成，主要贡献是 dense reusable state（密集可复用状态）及其行为审计。
- 相对天气情景植被模拟：TerraState 不把“天气驱动递归潜状态”作为唯一独特性，而把独特性收紧为 **像素级空间状态 + 状态承载检验 + 递归事实监督 + 留出分段组合检验**。

---

# 第三部分：方法设计

## 8. 形式化问题定义

设：

- `x_{1:t}`：截至时刻 `t` 的历史地球观测影像；
- `m_{1:t}`：云和无效像素掩膜；
- `u_{a:b}`：时间区间 `[a,b]` 的天气驱动序列；
- `g`：地理、季节或其他静态/缓变条件；
- `s_t`：模型在时刻 `t` 的运行时世界状态；
- `z_t`：运行时状态中的动态空间状态；
- `P_h`：由历史上下文形成的 horizon-specific context prior（时距相关上下文先验）；
- `T`：共享的变跨度状态转移；
- `O`：状态读出器；
- `y_{t+h}`：真实未来观测或目标 NDVI；
- `y_hat_{t+h}`：模型预测。

模型执行过程为：

```text
s_t = initialize(x_{1:t}, m_{1:t}, g)
s_{t+h} = advance(s_t, u_{t:t+h})
y_hat_{t+h} = decode(s_{t+h})
```

当前实现的运行时状态应诚实定义为：

```text
runtime_state = {
  context_prior P,
  dynamic_state z,
  geography g,
  current_offset
}
```

这比声称 `z` 单独包含全部世界信息更符合实际结构。

## 9. TerraState 组成

### 9.1 Context backbone（上下文骨干）

PVT-v2/Contextformer 用于编码多尺度历史遥感上下文。它提供成熟的空间表示能力，是 TerraState 的视觉上下文骨干，但不是本文主要方法贡献。论文无需把工作包装成 PVT 改进，也不需要对 PVT 的每一层做穷尽消融。

### 9.2 Context prior（上下文先验支路）

历史上下文直接形成预测先验 `P_h`。该支路提高固定时距预测稳定性，但也产生关键科学风险：模型可能主要依赖先验，动态状态仅作微小修正。因此图和公式必须公开该支路，并通过 Q2 的 `alpha=0/prior-only` 干预检验状态是否真实承担输出。

### 9.3 Explicit spatial predictive state（显式空间预测状态）

状态投影器从上下文特征形成初始动态状态 `z_0`。该状态保留空间结构，由后续共享转移持续更新，并经状态读出器贡献到像素级未来预测。

### 9.4 Shared variable-span transition（共享变跨度状态转移）

共享转移 `T` 接收当前状态、某一时间片段内的天气以及时间/地理条件：

```text
z_b = T(z_a, u[a:b], g, a, b)
```

同一 `T` 既可以一次处理完整区间，也可以对多个子区间重复调用。权重共享是“不同时间跨度可组合”的结构前提，但不能单独保证组合一致，因此仍需递归事实监督和 Q4 验证。

### 9.5 State readout（状态读出）

预测由上下文先验与状态贡献共同形成：

```text
y_hat_h = P_h + alpha * O(z_h)
```

`alpha=1` 为完整模型，`alpha=0` 关闭动态状态贡献，形成 prior-only（仅先验）干预。该干预不重新训练网络，因此能够更直接地检查最终输出是否依赖显式状态。

### 9.6 Runtime state interface（运行时状态接口）

论文方法与代码应统一为四个操作：

```text
initialize(history) -> runtime_state
advance(runtime_state, weather_segment) -> runtime_state'
decode(runtime_state) -> prediction
branch(runtime_state, weather_A/weather_B) -> alternative conditional futures
```

其中：

- `initialize` 从历史观测形成可运行状态；
- `advance` 只读取当前状态和新增天气片段，不重新编码完整历史；
- `decode` 从任意合法中间状态输出预测；
- `branch` 从同一状态复制多个分支，输入不同未来天气。

## 10. Recursive factual supervision（递归事实监督）

### 10.1 核心思想

真正的方法贡献不是在训练后检查隐藏状态，而是让真实未来标签通过递归状态路径监督模型。对终点 `H`，C1 的事实预测可以经过中间状态：

```text
z_k = T(z_0, u[0:k])
z_H = T(z_k, u[k:H])
y_hat_H = P_H + O(z_H)
L_factual = L(y_hat_H, y_H)
```

由于事实预测误差必须经过 `z_k` 和后续共享转移反向传播，中间状态被直接训练为能够继续承担后续预测的状态。

核心表述固定为：

> **把“中间状态能够继续代表模型所理解的当前世界”写进真实预测监督路径，而不是训练完成后再临时检查一个 hidden state。**

### 10.2 C0R 与 C1 的机制对照

C0R 与 C1 使用相同模型模块、参数规模、随机数、训练样本、端点和预算。两者核心差异是事实预测监督的计算路径：

```text
C0R: z_0 -------- T[u_0:H] --------> z_H  -> y_hat_H -> factual loss
C1:  z_0 -> T[u_0:k] -> z_k -> T[u_k:H] -> z'_H -> y_hat'_H -> factual loss
```

正式 C0R/C1 实验中的显式状态一致性和输出一致性损失权重均为 0。因此，C1 与 C0R 的 Q4 差异不能归因于额外一致性正则或参数量，主要归因于 recursive factual path（递归事实路径）。

### 10.3 为什么 Q4 不是“把同一个循环暂停一下”

- direct path（直接路径）对整个天气区间执行一次变跨度转移；
- segmented path（分段路径）对若干天气子区间重复调用共享转移；
- 两条路径共享权重和总天气路径，但计算图、状态更新次数和中间状态不同；
- 训练 partitions（训练分段方式）与 held-out partitions（留出分段方式）互斥；
- Q4 同时检查 direct accuracy、segmented accuracy 和两者差距，不能通过“两条路径都很差但彼此相近”获得通过。

这使 Q4 成为对变跨度状态转移可组合性的非平凡检验。

---

# 第四部分：论文主张与贡献

## 11. 四项可证伪主张

| 主张 | 核心问题 | 必要证据 | 失败时如何收窄结论 |
|---|---|---|---|
| **Q1 Prediction（预测能力）** | TerraState 是否首先是合格的多步地球观测预测器？ | 两数据集、强基线、多时距、OOD、定量与定性 | 不得声称具有竞争力；世界模型性质仍不能弥补基础预测失效 |
| **Q2 Load-bearing state（状态承载）** | 显式状态是否真实贡献到最终输出？ | full vs prior-only、配对效应、CI、时距与空间图 | 只能称状态为辅助表示，不能称核心世界状态 |
| **Q3 Weather response（天气响应）** | 模型是否使用所提供的未来天气？ | actual vs donor/mean、天气感知基线、轨迹和地图 | 只能称为时序预测器，不能强调天气驱动模拟 |
| **Q4 Continuation consistency（持续推进一致性）** | 中间状态能否继续预测，并使直接/分段推进近似一致？ | C0R/C1、多终点、多分段、留出 partitions、多种子、两数据集 | 只能称可预测状态，不能称可复用或持续推进的世界状态 |

四项主张的逻辑顺序是：

```text
Q1 会预测
 -> Q2 状态真实承担预测
 -> Q3 状态受外部天气驱动
 -> Q4 状态能够跨时间分段持续推进
 -> 可复用的天气驱动遥感世界状态
```

## 12. 论文贡献建议

### Contribution 1：模型

提出 TerraState，一个面向高分辨率植被与地表动力学的天气驱动地球观测世界模型。模型把显式空间预测状态作为核心训练对象和运行接口，并支持初始化、推进、解码和天气条件分支。

### Contribution 2：训练机制

提出共享变跨度状态转移与递归事实监督，使真实未来目标经过多段状态转移路径监督模型，从训练层面要求中间状态继续承担后续预测，而不是仅在训练后分析隐藏状态。

### Contribution 3：可证伪验证框架

建立预测能力、状态承载、天气响应和持续推进一致性四项互补检验，并通过同参数 C0R/C1 对照隔离持续推进能力的来源。

### Contribution 4：遥感实证

在高分辨率地球观测基准和独立数据集上，以同协议强基线、多种子、OOD 划分、空间可视化和计算成本评测，验证可复用空间预测状态的有效性和边界。

## 13. 贡献成立所需的最小逻辑闭环

论文最终必须同时满足：

1. C1 的预测能力没有因为递归状态设计而明显坍塌；
2. 移除状态读出后性能稳定下降；
3. 真实天气相对错配/均值天气具有稳定的终点保真优势；
4. C1 的直接/分段差距显著小于 C0R，且两条路径都保持有效预测；
5. 上述结论至少在一个真正独立的数据集上获得方向一致的确认；
6. 统计结论跨多个随机种子稳定；
7. 模型状态能够实际保存和恢复，而不只是图中概念。

若只满足 Q1-Q3，论文可以支持“承担预测且响应天气的显式状态”，但不足以支撑最核心的 continuation-consistent reusable state（持续推进一致的可复用状态）主张。

---

# 第五部分：实验总体设计

## 14. 实验设计原则

所有实验遵守以下原则：

1. **预测能力与世界模型性质分开评价**：Q1 回答是否会预测，Q2-Q4 回答内部状态是否具备主张的行为性质。
2. **外部基线与内部消融分开**：Contextformer、PredRNN 等回答“其他方法能预测到什么程度”；C0R/C1 和功能干预回答“本文机制为什么有效”。
3. **主数据集做完整验证，独立数据集做外部确认**：完整消融无需在所有数据集机械重复，但核心 Q1-Q4 必须有跨数据证据。
4. **同协议优先于照抄论文数字**：只在输入、输出、mask、预测时距和 scorer 可比时进行直接排名。
5. **图与表互补**：表格给精确总体数值和统计判定，图展示时间过程、样本分布、空间现象和失败边界。
6. **协议先冻结、结果后查看**：样本 manifest、分段方式、指标、阈值、聚类单位和排除规则必须在确认实验前固定。
7. **负结果不隐藏**：热旱特异性、跨数据不稳定或某些时距退化均应如实报告，并相应收窄主张。

## 15. 数据集角色

### 15.1 GreenEarthNet

GreenEarthNet 是完整机制验证数据集，承担：

- Q1 的 IID、OOD-t、OOD-s、OOD-st 四类预测评测；
- C1 与外部强基线的同协议比较；
- C0R/C1 完整机制对照；
- Q2 状态承载的四 split、多种子评测；
- Q3 actual/donor/mean weather（真实/错配/均值天气）完整干预；
- Q4 多终点、多分段、多种子和 held-out partition（留出分段）评测；
- 主要定性图、时距曲线和空间行为图。

### 15.2 独立第二数据集

首选 EarthNet2023-Africa，前提是完成数据许可、任务协议、时间步、目标变量和评价指标审计。第二数据集的作用是提供跨地区、跨生态和跨数据协议的外部有效性，而不是简单增加样本数量。

第二数据集必须遵循独立训练流程：

```text
GreenEarthNet:
  train Contextformer_G / video baselines_G / C0R_G / C1_G
  -> Table 1, Fig. 3, Fig. 5, complete Q2-Q4

EarthNet2023-Africa:
  adapt input/output dimensions and time grid
  train official/strong baselines_A / Contextformer_A / C0R_A / C1_A
  -> Table 2, Fig. 4, Fig. 5, compact Q2-Q4 confirmation
```

不得把 `C1_G` 权重直接拿到 Africa 推理后称为第二数据集主结果。若另外研究跨区域迁移，应单独命名为 transfer/zero-shot（迁移/零样本）实验，不能代替独立训练结果。

### 15.3 数据独立性要求

第二数据集必须在以下至少三个维度与 GreenEarthNet 形成真实差异：

- 地理区域；
- 生态/气候分布；
- 数据采样或任务协议；
- 训练和测试样本来源；
- 原生评价指标。

若候选数据与 GreenEarthNet/EarthNet2021 存在强继承、重切分或样本高度重叠，不能仅以版本号不同声称“独立数据集”。需要进行空间范围、时间范围、源影像和 cube ID 的重合审计，并在论文数据集章节公开关系。

## 16. 比较模型体系

### 16.1 无学习基线

- Persistence（持续性）：复制最后一个有效观测或协议规定的持续性预测；
- Climatology（气候态）：若合法参考轨道和历史统计可获得，则按官方协议实现；
- Previous Year（上一年同期）：仅在数据具备可靠同期参考时使用；
- 无法满足官方依赖的基线标记为 `n.a.` 或说明受阻，不猜造结果。

### 16.2 时序与视频预测基线

- ConvLSTM；
- PredRNN；
- SimVP；
- 根据第二数据集官方生态增加一个合法、可复现的强视频预测模型。

这些模型主要参加 Q1。除非其具有明确、可恢复且同构的运行状态接口，否则不强行参加 Q2/Q4。

### 16.3 遥感预测强基线

- Contextformer/PVT-v2：主数据集的直接强基线和 TerraState 的上下文骨干参照；
- 第二数据集官方强基线：用于 native metric（原生指标）比较；
- 可合法复现的直接遥感世界模型同行：根据任务、通道、空间分辨率和预测时距决定放入直接排名或协议差异矩阵。

### 16.4 TerraState 内部模型

- **C1 / TerraState**：共享变跨度转移 + recursive factual path；
- **C0R**：与 C1 同结构、同参数、同预算，事实预测走 direct path；
- **prior-only / alpha=0**：关闭状态读出，用于 Q2；
- **identity-T**：转移置为恒等，用作辅助功能干预；
- **donor weather / mean weather**：用于 Q3 条件天气对照；
- **w/o geography**：可选训练消融，用于分析静态条件贡献；
- **C2/C3 consistency variants**：仅当 C1 多种子不稳定时作为增强实验，不默认替代 C1。

## 17. 模型覆盖规则

| 证据 | GreenEarthNet | 独立第二数据集 | 外部基线要求 |
|---|---|---|---|
| Q1 主预测 | 全部合法基线 + C0R/C1，多种子四 split | 官方/强基线 + Contextformer_A + C0R_A/C1_A | 必须充分 |
| 核心消融 | Contextformer、C0R、C1、功能干预完整报告 | 只做 C0R_A/C1_A 核心确认 | Contextformer 仅作外部参照 |
| Q2 状态承载 | C1 三种子 × 四 split；C0R 汇总可入消融表 | C1_A 精简 full/prior-only | 普通基线无需参加 |
| Q3 天气响应 | C1 必做；C0R 和天气感知基线作行为对照 | C1_A 必做；增加一个天气感知基线 | 无天气模型记 `n.a.` |
| Q4 持续推进 | C0R/C1，多终点、多分段、多种子 | C0R_A/C1_A 精简确认 | 无状态接口模型无需参加 |
| 效率 | PredRNN、Contextformer、C0R、C1 | 可只给主数据集同硬件结果 | 同一测量环境 |

## 18. 训练公平性

C0R/C1 的机制对照必须固定：

- 相同数据和 manifest；
- 相同输入、目标、mask 和数据增强；
- 相同模型模块和参数量；
- 相同初始化规则和随机种子集合；
- 相同 optimizer、学习率计划、batch size、epoch 与早停策略；
- 相同事实预测端点；
- 相同显式 consistency loss 权重，正式主比较中均为 0；
- 唯一核心差分是 factual path（事实监督路径）为 direct 或 recursive。

外部模型比较必须固定：

- 同一测试 manifest；
- 同一有效像素 mask；
- 同一预测时距；
- 同一输出变量和反归一化；
- 同一 scorer；
- 多随机种子或明确说明官方确定性权重；
- 参数、FLOPs 和速度按同一输入尺寸测量。

## 19. 指标体系

### 19.1 共同预测指标

- `R²`：使用 pooled/global aggregation（全局汇总口径）；
- `RMSE`：对合法像素按冻结方式汇总；
- `MAE`：可作为稳定性辅助指标；
- 分 horizon 指标：显示长时退化；
- 每个数据集原生指标：用于与该数据集已有工作比较；
- common NDVI metrics（共同 NDVI 指标）：用于观察两个数据集上的同类行为，但不直接比较绝对难度。

### 19.2 Q2 指标

```text
Delta R² = R²(full) - R²(prior-only)
Delta RMSE = RMSE(prior-only) - RMSE(full)
```

同时报告：

- official aggregate effect（官方聚合效应）；
- paired per-cube/per-tile effect（配对逐样本/地块效应）；
- geo-cluster bootstrap CI（地理聚类自助置信区间）；
- 状态贡献随 horizon 的变化。

### 19.3 Q3 指标

```text
Delta Loss_donor = Loss(donor weather) - Loss(actual weather)
Delta Loss_mean  = Loss(mean weather)  - Loss(actual weather)
```

正值表示真实天气具有更高预测保真。必须同时给出 actual/control 的 R²、RMSE、效应差、CI 和样本量。响应被解释为 conditional response fidelity（条件响应保真），不是因果效应。

### 19.4 Q4 指标

至少报告：

- direct RMSE/R²；
- segmented RMSE/R²；
- relative degradation（相对退化）；
- direct/segmented output gap（输出差距）；
- direct/segmented state gap（状态差距，需定义尺度）；
- 多 endpoint、多 partition、多 segment count；
- cluster bootstrap CI；
- gate 判定及其预先冻结阈值。

必须使用 pooled/global R² 与 RMSE 作为主要端点。短序列单 cube 的 R² 容易出现低方差与聚合病理，不作为绝对门槛。

## 20. 统计与复现协议

### 20.1 随机种子

- 外部 learned baselines（学习基线）至少 3 个种子；
- C1 至少 3 个种子，与主基线统计口径一致；
- C0R/C1 使用相同种子配对；
- 表中报告 mean±std，关键差异报告配对 CI。

### 20.2 聚类单位

遥感 cube 之间可能共享地块、地区或时间信息，因此 bootstrap 不应默认把所有像素当成独立样本。优先按 tile/region（地块/地区）聚类；若按 cube 聚类，需要说明同地块相关性如何处理。

### 20.3 预冻结对象

- 数据 manifest 和哈希；
- 训练/验证/测试划分；
- Q4 endpoints；
- train partitions 与 held-out partitions；
- segment counts；
- pooled R²/RMSE 公式；
- bootstrap 单位和次数；
- gate 阈值；
- 无效像素和样本排除规则；
- 定性样例选择规则；
- 最终绘图数据文件。

### 20.4 每项实验应保存的产物

1. **Protocol（协议）**：配置、manifest、随机种子、模型权重、环境与命令；
2. **Raw outputs（原始输出）**：逐样本预测、状态摘要、mask 和必要元数据；
3. **Statistics（统计）**：机械汇总 JSON/CSV、CI、样本量、排除计数；
4. **Presentation（呈现）**：表格行、绘图数据、定性样例 manifest 和最终图像。

---

# 第六部分：具体实验包

## 21. E1：Q1 多步预测能力

### 21.1 研究问题

TerraState 是否在保持可复用状态机制的同时，仍具有与强遥感和视频预测器竞争的多步预测能力？

### 21.2 实验设计

- GreenEarthNet：IID、OOD-t、OOD-s、OOD-st 四 split；
- 每种 learned model 至少 3 seeds；
- 比较 Persistence、ConvLSTM、PredRNN、SimVP、Contextformer、C0R、C1；
- 报告总体 R²/RMSE、分 horizon 曲线和固定定性样例；
- 第二数据集独立训练官方基线、强视频基线、Contextformer_A、C0R_A、C1_A；
- 同时报告 native metrics 和 common NDVI metrics。

### 21.3 当前证据

GreenEarthNet 外部 learned baselines 已完成 `3 seeds × 4 splits = 48/48` 个同协议评测，Persistence 完成四 split；C1 已完成一个种子的四 split。

| Method | IID R² / RMSE | OOD-t R² / RMSE | OOD-s R² / RMSE | OOD-st R² / RMSE |
|---|---:|---:|---:|---:|
| ConvLSTM | 0.5107 / 0.1557 | 0.5483 / 0.1615 | 0.4761 / 0.1622 | 0.5234 / 0.1610 |
| PredRNN | **0.5414 / 0.1423** | **0.5925 / 0.1474** | **0.5087 / 0.1494** | **0.5635 / 0.1479** |
| SimVP | 0.4988 / 0.1461 | 0.5616 / 0.1492 | 0.4650 / 0.1529 | 0.5275 / 0.1553 |
| Contextformer | 0.5333 / 0.1484 | 0.5877 / **0.1431** | 0.5021 / 0.1549 | 0.5567 / **0.1473** |
| **TerraState-C1, seed 1** | 0.5220 / 0.1555 | 0.5726 / 0.1509 | 0.4949 / 0.1621 | 0.5408 / 0.1542 |

现有证据支持“具有竞争力且未因状态机制发生预测坍塌”，不支持“达到精度 SOTA”。

### 21.4 完成标准

- C1 补齐至少两个独立种子；
- C0R/C1 完成同种子配对；
- 逐 horizon 结果和 95% CI 可机械生成；
- 两数据集定性图和误差图完成；
- 第二数据集主表完成；
- 结论使用 competitive（有竞争力）而非 state of the art，除非最终结果事实改变。

## 22. E2：Q2 状态承载

### 22.1 研究问题

显式动态状态 `z` 是否真实影响最终预测，还是输出主要由 context prior 提供？

### 22.2 核心干预

保持同一模型、输入、权重和上下文先验，仅设置：

```text
full:       y_hat = P + 1 * O(z)
prior-only: y_hat = P + 0 * O(z)
```

该干预直接移除状态读出贡献，不引入另一个重新训练模型。

### 22.3 当前证据

| Split | Full R² | Prior-only R² | Official Delta R² | Paired mean Delta R² | 95% CI | 判定 |
|---|---:|---:|---:|---:|---|---|
| IID | 0.522028 | 0.488350 | 0.033679 | 0.031381 | [0.025315, 0.037247] | LOAD_BEARING |
| OOD-t | 0.572604 | 0.555527 | 0.017077 | 0.018935 | [0.010882, 0.026923] | LOAD_BEARING |
| OOD-s | 0.494874 | 0.461436 | 0.033439 | 0.028741 | [0.024551, 0.032919] | LOAD_BEARING |
| OOD-st | 0.540760 | 0.523713 | 0.017047 | 0.021049 | [0.015030, 0.027153] | LOAD_BEARING |

### 22.4 补充证据

- 状态贡献随 horizon 的曲线；
- per-cube/per-tile 效应分布；
- 状态贡献高、中、低的冻结空间案例；
- 新种子重复；
- C1_A 在独立数据集上的精简 full/prior-only 验证。

### 22.5 解释边界

Q2 能证明状态对输出具有不可忽略的功能贡献，不能证明状态包含全部未来信息或等同于真实物理状态。identity-T（恒等转移）只作为辅助证据，因为 decoder 可能接收到训练分布外状态。

## 23. E3：Q3 条件天气响应

### 23.1 研究问题

从同一历史或中间状态出发，模型是否根据所提供的未来天气产生不同预测，并且真实天气路径是否具有更高终点预测保真？

### 23.2 天气对照

- `actual weather（真实天气）`：样本真实未来天气；
- `matched donor weather（匹配错配天气）`：来自匹配地区/季节但不同样本或时期的天气；
- `mean weather（均值天气）`：按冻结规则构造的平均天气；
- 三条分支共享完全相同的历史和初始状态。

### 23.3 当前证据

| 比较 | Delta Loss | 95% geo-cluster CI | 结论 |
|---|---:|---|---|
| Actual vs donor | 0.002053 | [0.000761, 0.003452] | PASS |
| Actual vs mean | 0.010140 | [0.004839, 0.015558] | PASS |

极端子集：

| Weather | R² | RMSE |
|---|---:|---:|
| Actual | **0.634493** | **0.147289** |
| Donor | 0.588372 | 0.156135 |
| Mean | 0.557833 | 0.192398 |

Hot-dry interaction（热旱交互）为 `-0.000302`，95% CI `[-0.002841, 0.002582]`，未通过。因此论文可以主张一般条件天气响应保真，不能主张模型对热旱事件具有额外特异增强。

### 23.4 必须补充

- Contextformer 或代表性天气感知基线的 actual/donor/mean 对照；
- C0R 的天气响应，用于区分“使用天气”和“持续状态一致”两个能力；
- 天气变量轨迹、预测 NDVI 轨迹、终点地图和差异图；
- 新种子或独立数据集的精简验证；
- donor matching（错配天气匹配）规则和泄漏审计。

### 23.5 解释边界

该实验是 conditional response test（条件响应检验），不是因果反事实。真实天气更优说明模型利用了与目标一致的未来条件，不能单独证明天气变化导致了观测变化。

## 24. E4：Q4 持续推进与组合一致性

### 24.1 研究问题

在相同初始状态和天气路径下，直接推进与分段推进是否保持预测准确并到达近似一致的状态/输出？该性质是否由递归事实监督产生？

### 24.2 评测路径

```text
Direct:    z_0 ---------------- T[u_0:H] ----------------> z_H
Segmented: z_0 -> T[u_0:h1] -> z_h1 -> ... -> T[u_hk:H] -> z'_H
```

两条路径共享：

- 初始状态；
- 完整天气序列；
- 总预测终点；
- 转移参数；
- 解码器和评价指标。

### 24.3 当前锁定证据

| Model | Horizon | Direct RMSE / R² | Worst segmented degradation | Q4 gates | 判定 |
|---|---:|---:|---:|---|---|
| C1 | 10 | 0.1377 / 0.630 | **0.8%** | 4/4 PASS | PASS |
| C1 | 15 | 0.1596 / 0.493 | **1.0%** | 4/4 PASS | PASS |
| C1 | 20 | 0.1617 / 0.531 | **1.2%** | 4/4 PASS | PASS |
| C0R | 10 | 0.1369 / 0.634 | 9.2% | 2/4 PASS | FAIL |
| C0R | 15 | 0.1600 / 0.491 | 9.1% | 2/4 PASS | FAIL |
| C0R | 20 | 0.1628 / 0.525 | 14.7% | 2/4 PASS | FAIL |

现有结果说明 C1 与 C0R 的 direct accuracy 接近，但 C1 的分段退化约为 0.8%-1.2%，C0R 为 9.1%-14.7%。这正是机制对照需要呈现的结构：递归事实监督主要改善持续推进性质，而不是通过显著改变单次直接预测精度取胜。

### 24.4 R² 聚合口径

原 per-cube R² `G_abs` 腿产生的 `4/19` 属于聚合规格问题，不作为有效负面结论。同批封存统计量中 pooled-RMSE 腿 `19/19` 通过；使用相同充分统计量修正为 pooled-R² 后，三种资格口径也均为 `19/19`。

论文中的正确写法是：

> **修正后的事实端点非劣审计为 19/19 通过，同时披露原 per-cube R² 规格及其聚合问题。**

不得把结果写成“原 per-cube 门预注册通过”。

### 24.5 确认实验

- C0R/C1 至少 3 个配对种子；
- endpoints 建议覆盖 `h=10/15/20` 及数据允许的更长时距；
- segment counts 覆盖 2/3/4 段；
- 使用训练未见的 partitions；
- 同时报告 direct accuracy、segmented accuracy 和两者差距；
- 输出层与状态层均报告一致性；
- 独立数据集使用 `C0R_A/C1_A` 做精简复验；
- 运行前冻结所有 pooled 指标和 gate。

### 24.6 失败判定

以下任一情况都会削弱 Q4：

- C1 和 C0R 的分段退化差异在多种子下消失；
- C1 只在训练见过的分段方式上一致；
- direct/segmented 很接近，但两者预测都显著失真；
- 状态可以在内存中连续计算，但序列化恢复后结果改变；
- 第二数据集方向相反且无法由时间分辨率或协议解释。

## 25. E5：核心机制消融

### 25.1 研究问题

预测能力、状态承载、天气响应和持续推进分别由哪些结构或训练机制产生？

### 25.2 推荐消融矩阵

| Model/intervention | Explicit state | Shared T | Weather | Recursive factual path | 主要回答 |
|---|:---:|:---:|:---:|:---:|---|
| Contextformer | × | × | ✓ | × | 外部预测骨干能做到什么 |
| C0R | ✓ | ✓ | ✓ | × | 有相同结构但没有递归事实监督时怎样 |
| **C1** | ✓ | ✓ | ✓ | ✓ | 完整模型 |
| C1 prior-only | 状态读出关闭 | ✓ | ✓ | ✓ | 状态是否承载输出 |
| C1 identity-T | ✓ | identity | 受限 | ✓ | 正常状态转移是否必要 |
| C1 donor/mean weather | ✓ | ✓ | 对照天气 | ✓ | 模型是否使用真实天气 |
| C1 w/o geography | ✓ | ✓ | ✓ | ✓ | 静态地理条件贡献 |

### 25.3 表达规则

- Contextformer 是外部基线，不称为严格内部消融；
- C0R 是 C1 最重要的同构控制；
- prior-only、identity-T、weather controls 是功能干预，不是完整重新训练模型；
- 不需要在第二数据集重复全部功能干预；第二数据集只确认 C0R/C1 和最核心 Q2/Q3；
- 消融表同时放 Q1、Q2、Q3、Q4 的紧凑指标，详细数值分别进入对应结果表。

## 26. E6：效率与状态接口

### 26.1 研究问题

显式状态和分段推进是否带来可接受的参数、显存、推理时间和状态存储成本？

### 26.2 指标

- 参数量；
- FLOPs/sample；
- 峰值显存；
- 每 epoch 训练时间；
- direct inference time；
- segmented inference time；
- runtime state size；
- save/load time；
- 从保存状态恢复后的数值一致性；
- 相对重新编码完整历史的时间节省。

### 26.3 测量协议

- 相同 GPU、CUDA、精度、输入尺寸和 batch size；
- 预热后重复测量并报告均值和波动；
- I/O 与纯模型计算分别报告；
- state save/load 使用相同序列化格式；
- 比较“恢复状态继续”与“重新读取完整历史再预测”的端到端耗时。

## 27. E7：不确定性与边界

TerraState 当前主要输出确定性预测。稿件至少应提供：

- 多种子预测波动；
- ensemble calibration（集成校准）或残差覆盖率；
- 误差随 horizon、云量、有效观测数量和动态幅度的变化；
- 典型、高动态和困难场景的固定可视化；
- 对未观测管理活动和极端事件的局限讨论。

若资源允许，可探索共享状态上的 quantile head（分位数输出头）并报告 Pinball loss、PICP 或 CRPS；该增强不能以破坏 Q1-Q4 为代价，也不应抢占主线。

---

# 第七部分：八张主图设计

## 28. 图表统一原则

> **表格负责给出可复核的总体数值，图负责展示这些数值背后的时间过程、空间现象和样本分布。图与表服务于同一科学主张，但不得把相同的汇总数字换一种形式重复呈现。**

所有图遵守：

- 同一方法跨图使用相同颜色；
- C1 使用主色，C0R 使用明确但中性的对照色；
- direct 使用实线，segmented 使用虚线；
- actual/donor/mean weather 在天气曲线、预测轨迹和地图边框中保持同色；
- NDVI 图共享物理范围和色标，误差图使用从 0 开始的独立顺序色标；
- 所有地图标出无效区，不把云和缺测显示为正常数值；
- 子图标签、字体和线宽满足双栏缩放后可读；
- 主图不使用大面积装饰性流程框替代结果；
- 定性样例选择规则预先冻结，避免 cherry-picking（选择性展示）。

## 29. Fig. 1：科学问题与世界模型运行契约

### 一句话目的

说明为什么准确的固定时距预测不等于拥有世界模型，并定义 TerraState 将接受的四项可证伪检验。

### 推荐题目

**From Fixed-Horizon EO Forecasting to Reusable-State World Modeling**  
**从固定时距地球观测预测到可复用状态世界建模**

### 面板设计

- **(a) Partial observation（部分可观测）**：绘制连续但不可完全观测的真实地表过程、稀疏/云遮挡卫星观测和相对密集的天气驱动。
- **(b) Fixed-horizon forecasting（固定时距预测）**：历史和天气直接映射到固定未来；标注输出可以准确，但不要求中间状态可保存和续推。
- **(c) Reusable predictive world state（可复用预测世界状态）**：历史初始化状态，状态沿天气片段推进，并支持 direct、pause/resume 和 branch。
- **(d) Falsifiable contract（可证伪运行契约）**：Q1 prediction、Q2 load-bearing、Q3 forcing response、Q4 continuation/composition。

### 草图

```text
(a) latent land process + sparse/cloudy observations + dense weather forcing
                     ↓
(b) history -------------------------------> fixed future output
    accurate output != reusable state
                     ↓
(c) history -> s_0 -> s_k -> s_H -> prediction
                  ├─ save/resume
                  └─ weather branch A/B
    direct s_H ≈ segmented s'_H
                     ↓
(d) Q1 forecast | Q2 load-bearing | Q3 forcing | Q4 continuation
```

### 图注核心句

> Accurate fixed-horizon forecasts do not necessarily imply a reusable predictive state. TerraState learns weather-driven spatial state transitions and tests whether the learned state remains load-bearing, forcing-responsive, and continuation-consistent across temporal partitions.

### 完成标准

- 世界模型名称在图中央明确出现；
- 图中能一眼看出普通预测与可复用状态建模的差异；
- Q1-Q4 与后文图表编号一致；
- 不出现网络层级细节；
- 天气标为 external forcing，不标为 action；
- 图注不暗示因果反事实。

## 30. Fig. 2：TerraState-C1 架构与递归事实监督

### 一句话目的

展示 TerraState 的完整状态系统，并说明递归事实监督如何把中间状态的续推能力写入真实预测路径。

### 面板设计

- **(a) Context initialization（上下文初始化）**：历史 EO、历史天气和地理进入 PVT-v2/Contextformer，得到 context prior 和初始状态。
- **(b) Shared variable-span transition（共享变跨度转移）**：未来天气、地理和时间编码驱动共享 `T`，生成未来状态。
- **(c) State readout and API（状态读出与接口）**：绘制 `P_h + alpha O(z_h)` 以及 `initialize/advance/decode/branch`。
- **(d) C0R/C1 factual paths（事实路径）**：同参数、同样本、同端点；C0R 走 direct factual path，C1 走 recursive factual path。
- **(e) Train/held-out partitions（训练/留出分段）**：说明 Q4 使用训练未见的时间切分。

### 草图

```text
EO history + past weather + geography
                |
     PVT-v2 / Contextformer backbone
        |                         |
 context prior P_h          state projector -> z_0
                                      |
future weather segment -> shared T -> z_h -> O(z_h)
                                      |
                         y_hat_h = P_h + alpha O(z_h)

C0R: z_0 -------- T[0:H] --------> z_H  -> factual prediction loss
C1:  z_0 -> T[0:k] -> z_k -> T[k:H] -> z'_H -> factual prediction loss

same parameters, seeds, endpoints and explicit consistency lambda = 0
```

### 必须公开的结构

- PVT-v2/Contextformer 标注为 context backbone，不作为本文创新；
- context prior 必须画出，不能隐藏旁路；
- 共享 `T` 在不同分段使用同一个符号和参数标记；
- 递归事实监督箭头必须从真实未来标签回到递归预测路径；
- `runtime_state={P,z,g,offset}` 与实际代码一致；
- C0R/C1 唯一核心差分必须视觉上突出。

### 完成标准

- 代码和图中的输入、状态、转移与输出逐项一致；
- save/load/resume demo 可以调用相同接口；
- 图中不把功能干预误画成训练模块；
- 方法公式能够直接引用图中符号。

## 31. Fig. 3：GreenEarthNet 多时距定性预测

### 一句话目的

展示主数据集上的真实空间预测质量、空间细节保持和长时退化特征。

### 推荐布局

| Rows（行） | Columns（列） |
|---|---|
| IID、OOD-t、OOD-s、OOD-st 的冻结样例 | Last context、GT、Persistence、PredRNN、Contextformer、C1、absolute error |
| 典型、高动态和困难场景 | short/mid/long horizons 建议 h=5/10/20 |

### 样例选择

- 按 C1 per-cube RMSE 的 `P25/P50/P75` 冻结典型难度；
- 另按真实 NDVI 动态幅度冻结一个高动态样例；
- 可加入一个有解释价值的 challenging case（困难样例），但不强制在主图设置“失败案例”专门行；
- 系统性失败或完整高误差样例网格放补充材料；
- 所有方法使用同一 cube、同一时间点、同一 mask 和同一色标。

### 草表

| Split/sample | Last context | GT h=5/10/20 | Persistence | PredRNN | Contextformer | C1 | Error maps |
|---|---|---|---|---|---|---|---|
| IID / P25 | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] |
| OOD-t / P50 | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] |
| OOD-s / P75 | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] |
| OOD-st / high dynamic | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] | [待导出] |

### 完成标准

- 至少包含短、中、长三个时距；
- 同时展示 Persistence 和强模型，检查是否只是复制末帧；
- 图像与误差色标统一且可读；
- 不把 Table 1 的总体数字复制成大面积柱状图；
- 样例 manifest、原始预测和拼图脚本可追溯。

## 32. Fig. 4：独立数据集定性预测

### 一句话目的

展示 TerraState 在独立地区、生态条件和数据协议下的空间预测质量与外部有效性。

### 推荐布局

| Rows | Columns |
|---|---|
| 2 个典型样例、1 个高动态样例、1 个困难样例 | Last context、GT short/mid/long、Persistence_A、官方/视频强基线、Contextformer_A、C1_A、error map |

困难样例用于避免只展示漂亮结果，但“失败边界”不作为主图标题或强制中心。只有发现具有明确科学解释的系统性问题，例如极端云量、观测稀疏或气候分布外区域，才在主文讨论；普通失败样例进入补充材料。

### 草表

| Sample | Last context | GT short/mid/long | Persistence_A | Strong baseline_A | Contextformer_A | C1_A | Error map |
|---|---|---|---|---|---|---|---|
| Typical 1 | -- | -- | -- | -- | -- | -- | -- |
| Typical 2 | -- | -- | -- | -- | -- | -- | -- |
| High dynamic | -- | -- | -- | -- | -- | -- | -- |
| Challenging | -- | -- | -- | -- | -- | -- | -- |

### 完成标准

- C1_A 和对照模型均在第二数据集上独立训练或按合法协议适配；
- 展示数据集原生目标；若可计算 NDVI，再增加共同 NDVI 视图；
- 样例规则在查看最终模型优劣前冻结；
- 与 Fig. 3 保持色标语义一致，但不因形式统一而删除第二数据集特有通道。

## 33. Fig. 5：两数据集预测时距与 OOD 退化

### 一句话目的

展示误差随真实未来时距的累积过程，定位 C1 的预测竞争力、长期边界和 OOD 代价。

### 面板设计

- **(a) GreenEarthNet R²-horizon**：四 split 使用 `2×2` small multiples；
- **(b) GreenEarthNet RMSE-horizon**：与 `(a)` 共享横轴和模型图例；
- **(c) 第二数据集 native metric-horizon**：按官方时间单位报告；
- **(d) 第二数据集 common NDVI metric-horizon**：报告共同 NDVI R²/RMSE。

### 草图

```text
GreenEarthNet R²↑             GreenEarthNet RMSE↓
IID / OOD-t / OOD-s / OOD-st IID / OOD-t / OOD-s / OOD-st
[PredRNN, Contextformer, C1]  [PredRNN, Contextformer, C1]
with 95% CI                   with 95% CI

Africa native metric↑         Africa NDVI R²/RMSE
[pending]                     [pending]
```

### 完成标准

- 横轴使用真实天数或清楚定义的数据时间步；
- C1 多种子置信带与基线统计口径一致；
- 不用总体均值柱状图替代时距曲线；
- 两数据集不因时间分辨率不同而强行共享同一横轴刻度；
- 可选择一个最有解释力的 land-cover/weather 分层进入补充材料。

## 34. Fig. 6：Q2 状态承载的时间、分布与空间证据

### 一句话目的

展示显式状态贡献在何时出现、由哪些样本驱动、发生在什么空间区域。

### 面板设计

- **(a) Intervention protocol（干预协议）**：同一模型从 `alpha=1` 变为 `alpha=0`；
- **(b) Horizon dependence（时距依赖）**：状态贡献的 Delta R²/Delta RMSE 随时距变化；
- **(c) Sample distribution（样本分布）**：per-cube/per-tile ECDF 或 violin，标出零效应线和 CI；
- **(d) Spatial cases（空间案例）**：GT、full、prior-only、误差图和 state contribution map。

### 草图

```text
(a) full: P + O(z)   vs   prior-only: P

(b) Delta metric
     ^  IID / OOD-t / OOD-s / OOD-st
     |  [horizon curves]
   0 +-----------------------------> forecast days

(c) [per-cube/per-tile effect distributions]

(d) GT | Full | Prior-only | Error full | Error prior | Contribution map
```

### 面板关系

`(a)-(d)` 全部制作并组成一张综合图，不是四选一。Table 4 已提供四 split 的精确 Delta R² 和 CI，因此 Fig. 6 不能只把 Table 4 画成四根柱。若版面不足，完整四 split 分布放补充材料，主文仍保留时距趋势、分布摘要和空间案例。

### 当前可用锚点

- IID paired mean Delta R²：`0.031381 [0.025315, 0.037247]`；
- OOD-t：`0.018935 [0.010882, 0.026923]`；
- OOD-s：`0.028741 [0.024551, 0.032919]`；
- OOD-st：`0.021049 [0.015030, 0.027153]`。

### 完成标准

- 使用真实 per-sample/per-tile 结果，而非模拟分布；
- 零效应线、样本量、聚类单位和 CI 方法写入图注；
- 空间样例按贡献分位冻结；
- 使用“load-bearing contribution”，不写“state contains all information”。

## 35. Fig. 7：Q3 天气响应轨迹与空间分支

### 一句话目的

从天气输入、预测时间轨迹到空间终点完整展示条件天气分支如何影响模型未来。

### 面板设计

- **(a) Weather trajectories（天气轨迹）**：actual/donor/mean 的温度、降水及关键天气变量；
- **(b) Predicted NDVI trajectories（预测 NDVI 轨迹）**：三条预测与 GT，共享 `(a)` 时间轴；
- **(c) Endpoint maps（终点地图）**：GT、actual、donor、mean；
- **(d) Difference/error maps（差异/误差图）**：actual-donor、actual-mean 及相对 GT 的误差变化。

### 草图

```text
(a) weather: actual ──  donor --  mean ..
                       |
(b) NDVI: GT / actual / donor / mean trajectories
                       |
(c) GT | Actual | Donor | Mean endpoint maps
                       |
(d) Actual-Donor | Actual-Mean | error-change maps
```

### 面板关系

`(a)-(d)` 全部制作并组成一张综合图，不是从“天气、轨迹、终点地图、差异图”中选择一个。Table 5 负责精确 Delta Loss、CI 和极端子集数字，Fig. 7 不再增加重复的总体柱状图。

### 当前可用锚点

- Actual vs donor Delta Loss：`0.002053 [0.000761, 0.003452]`；
- Actual vs mean Delta Loss：`0.010140 [0.004839, 0.015558]`；
- extreme subset actual：`R²=0.634493, RMSE=0.147289`；
- hot-dry interaction 未通过，不作为主图中心。

### 完成标准

- 天气曲线和 NDVI 曲线时间严格对齐；
- actual/donor/mean 跨所有面板颜色一致；
- 地图展示相同样本、时间和色标；
- 图注使用 conditional branch/response，不使用 causal counterfactual；
- 至少一个代表性样例能够看出天气输入变化对应的轨迹和空间变化。

## 36. Fig. 8：Q4 持续推进与组合一致性

### 一句话目的

证明中间状态能够继续承担后续预测，并通过 C0R/C1 的量级差异说明该性质来自递归事实监督。

### 面板设计

- **(a) Direct/segmented protocol（直接/分段协议）**：相同初态、天气路径和共享 `T`，不同计算图；
- **(b) Degradation curves（退化曲线）**：不同 horizon 和 segment count 下 C1/C0R 的相对 RMSE 退化与 CI；
- **(c) State/output gap distributions（状态/输出差距分布）**：展示差异是否由少量样本驱动；
- **(d) Spatial endpoint comparison（空间终点比较）**：GT、C1 direct/segmented/diff、C0R direct/segmented/diff。

### 草图

```text
(a) Direct:    z_0 -------- T[0:H] --------> z_H
    Segmented: z_0 -> T[0:k] -> z_k -> T[k:H] -> z'_H

(b) Relative degradation↓
    C1:  0.8% / 1.0% / 1.2% at h=10/15/20
    C0R: 9.2% / 9.1% / 14.7%
    [final: curves over segment counts with CI]

(c) [C1/C0R state gap and output gap distributions]

(d) GT | C1-direct | C1-segmented | C1-diff |
        C0R-direct | C0R-segmented | C0R-diff
```

### 面板关系

`(a)-(d)` 全部制作并组成一张综合图。Table 6 已负责精确 gate、endpoint 和 19/19 统计，因此 Fig. 8 不放大面积 PASS/FAIL 矩阵，也不把表格数字简单改成柱状图。

### 完成标准

- C0R/C1 使用配对种子、相同 endpoint 和 partition；
- 曲线覆盖多个 horizon 与 2/3/4 段；
- direct 和 segmented 各自的绝对准确性同时可见；
- 状态距离的归一化方式明确；
- 地图使用相同样例和色标；
- 图注正确披露 per-cube R² 聚合问题和修正 pooled 口径；
- 第二数据集结果若版面允许作为小面板，否则由 Table 6 和补充材料承担。

---

# 第八部分：七张主表设计

## 37. Table 1：GreenEarthNet 同协议预测主表

### 一句话目的

在相同数据、mask、scorer 和预测时距下，比较 TerraState 与无学习、视频预测和遥感预测基线的 Q1 表现。

### 表格模板与当前结果

| Method（方法） | Seeds | IID R² / RMSE | OOD-t R² / RMSE | OOD-s R² / RMSE | OOD-st R² / RMSE | Params |
|---|---:|---:|---:|---:|---:|---:|
| Persistence | deterministic | 0.0000 / 0.2213 | 0.0000 / 0.2157 | 0.0000 / 0.2258 | 0.0000 / 0.2183 | 0 |
| Climatology | -- | -- | -- | -- | -- | 0 |
| Previous Year | -- | -- | -- | -- | -- | 0 |
| ConvLSTM | 3 | 0.5107 / 0.1557 | 0.5483 / 0.1615 | 0.4761 / 0.1622 | 0.5234 / 0.1610 | 1.04M |
| PredRNN | 3 | **0.5414 / 0.1423** | **0.5925 / 0.1474** | **0.5087 / 0.1494** | **0.5635 / 0.1479** | 1.43M |
| SimVP | 3 | 0.4988 / 0.1461 | 0.5616 / 0.1492 | 0.4650 / 0.1529 | 0.5275 / 0.1553 | 6.59M |
| Contextformer | 3 | 0.5333 / 0.1484 | 0.5877 / **0.1431** | 0.5021 / 0.1549 | 0.5567 / **0.1473** | 6.06M |
| C0R | 3 | -- | -- | -- | -- | 7.18M |
| **TerraState-C1** | **1（待补 2）** | 0.5220 / 0.1555 | 0.5726 / 0.1509 | 0.4949 / 0.1621 | 0.5408 / 0.1542 | 7.18M |
| Earthformer | -- | n.a. | n.a. | n.a. | n.a. | -- |

### 排版规则

- 无学习、视频预测、遥感预测和本文模型分组；
- 每个单元格最终报告 mean±std；
- 每列最佳值加粗，第二值下划线；
- 不把不同协议的论文数字与本地同协议结果混排；
- `n.a.` 必须有脚注说明原因；
- Params 只作辅助，完整效率进入 Table 7。

### 当前结论

C1 在四个 split 均具备竞争力，但当前低于 PredRNN 和 Contextformer 的最佳值。论文应强调“状态机制没有导致预测能力坍塌”，而不是声称 SOTA。

## 38. Table 2：独立数据集预测主表

### 一句话目的

验证 TerraState 的预测能力是否在独立地区、生态与任务协议下成立，同时满足官方比较和跨数据共同观察。

### 表格模板

| Method | Seeds | Native val metric↑（原生验证指标） | Native test metric↑（原生测试指标） | NDVI R²↑ | NDVI RMSE↓ | Params |
|---|---:|---:|---:|---:|---:|---:|
| Persistence_A | -- | -- | -- | -- | -- | 0 |
| Climatology_A | -- | -- | -- | -- | -- | 0 |
| Official baseline A | -- | -- | -- | -- | -- | -- |
| Strong video baseline_A | -- | -- | -- | -- | -- | -- |
| Contextformer_A | -- | -- | -- | -- | -- | -- |
| C0R_A | -- | -- | -- | -- | -- | -- |
| **TerraState-C1_A** | -- | -- | -- | -- | -- | -- |

### 指标解释

- `native metrics` 用于与第二数据集已有方法公平比较；
- `common NDVI metrics` 用于观察 TerraState 在两个数据集上的同类植被预测行为；
- 不将两个数据集绝对 R² 直接排名，因为数据难度、时间跨度和 mask 不同；
- Table 2 只回答 Q1，C1_A 的 Q2-Q4 进入 Table 4-6。

### 完成标准

- 数据集官方 split 和 scorer 已核对；
- C0R_A/C1_A 独立训练；
- 至少 3 seeds 或给出资源限制和 CI；
- 官方基线与本文模型输入信息公平；
- Fig. 4 和 Fig. 5 的数据与本表一致。

## 39. Table 3：核心机制与消融

### 一句话目的

证明 TerraState 的持续推进性质来自共享状态机制与递归事实监督，而不是参数增加、骨干差异或后处理。

### 结构矩阵

| Model/intervention | Explicit state | Shared T | Weather | Recursive factual path | 说明 |
|---|:---:|:---:|:---:|:---:|---|
| Contextformer | × | × | ✓ | × | 外部预测骨干参照 |
| C0R | ✓ | ✓ | ✓ | × | 同构直接事实路径控制 |
| **C1** | ✓ | ✓ | ✓ | ✓ | 完整 TerraState |
| C1 prior-only | 状态读出关闭 | ✓ | ✓ | ✓ | Q2 功能干预 |
| C1 identity-T | ✓ | identity | 受限 | ✓ | 状态转移辅助干预 |
| C1 donor weather | ✓ | ✓ | donor | ✓ | Q3 错配天气控制 |
| C1 mean weather | ✓ | ✓ | mean | ✓ | Q3 均值天气控制 |
| C1 w/o geography | ✓ | ✓ | ✓ | ✓ | 可选静态条件训练消融 |

### 紧凑数值模板

| Model/intervention | OOD-t R²↑ | Q2 Delta R²↑ | Q3 Delta Loss↑ | Q4 worst degradation↓ | Params | 结论 |
|---|---:|---:|---:|---:|---:|---|
| Contextformer | 0.5877 | n.a. | -- | n.a. | 6.06M | 强外部预测基线 |
| C0R | -- | -- | -- | 14.7%* | 7.18M | Q4 FAIL |
| **C1** | **0.572604** | **0.017077** | **0.002053** | **1.2%*** | 7.18M | Q2/Q3/Q4 PASS |
| C1 prior-only | 0.555527 | control | -- | -- | same | 状态读出关闭 |
| C1 identity-T | 0.554934 | support | -- | -- | same | 辅助证据 |
| C1 donor weather | -- | -- | control | -- | same | 条件对照 |
| C1 mean weather | -- | -- | control | -- | same | 条件对照 |
| C1 w/o geography | -- | -- | -- | -- | -- | 待完成 |

`*` 当前锚点取 `h=20` 的最差分段退化；终稿应在表头或脚注固定口径。

### 完成标准

- C0R/C1 使用配对 3 seeds；
- Q1、Q2、Q3、Q4 的紧凑指标均有统一来源；
- 详细 split、CI 和 endpoint 不塞入该表，分别由 Table 4-6 承担；
- 不将 Contextformer 称为内部消融；
- 不需要让所有视频基线参加结构消融。

## 40. Table 4：Q2 状态承载

### 一句话目的

精确报告显式状态对最终输出的贡献、置信区间和跨数据稳定性。

### 表格模板与当前结果

| Dataset/Split | Model | Seeds | Full R²↑ | Prior-only R²↑ | Official Delta R²↑ | Paired mean Delta R²↑ | 95% CI | Decision |
|---|---|---:|---:|---:|---:|---:|---|---|
| GreenEarthNet / IID | C1_G | 1 | 0.522028 | 0.488350 | **0.033679** | 0.031381 | [0.025315, 0.037247] | **LOAD_BEARING** |
| GreenEarthNet / OOD-t | C1_G | 1 | 0.572604 | 0.555527 | **0.017077** | 0.018935 | [0.010882, 0.026923] | **LOAD_BEARING** |
| GreenEarthNet / OOD-s | C1_G | 1 | 0.494874 | 0.461436 | **0.033439** | 0.028741 | [0.024551, 0.032919] | **LOAD_BEARING** |
| GreenEarthNet / OOD-st | C1_G | 1 | 0.540760 | 0.523713 | **0.017047** | 0.021049 | [0.015030, 0.027153] | **LOAD_BEARING** |
| GreenEarthNet / all splits | C1_G | 3 | -- | -- | -- | -- | [--, --] | -- |
| Independent dataset / Test | C1_A | -- | -- | -- | -- | -- | [--, --] | -- |

### 完成标准

- 四 split × 三种子完整；
- 表尾给跨 seed 汇总；
- CI 聚类单位明确；
- 第二数据集用独立训练 C1_A 精简复验；
- 与 Fig. 6 的时距和分布数据一致；
- 不要求普通基线参加无法定义的状态移除干预。

## 41. Table 5：Q3 条件天气响应

### 一句话目的

精确检验真实天气是否比错配和均值天气提供更高终点保真，并与天气感知基线区分。

### 表格模板与当前结果

| Dataset/Subset | Model | Comparison | R² actual↑ | R² control↑ | RMSE actual↓ | RMSE control↓ | Delta Loss↑ | 95% geo-cluster CI | Decision |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| GreenEarthNet / Overall | Contextformer | Actual vs donor | -- | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet / Overall | Contextformer | Actual vs mean | -- | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet / Overall | C0R_G | Actual vs donor/mean | -- | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet / Overall | **C1_G** | Actual vs donor | -- | -- | -- | -- | **0.002053** | **[0.000761, 0.003452]** | **PASS** |
| GreenEarthNet / Overall | **C1_G** | Actual vs mean | -- | -- | -- | -- | **0.010140** | **[0.004839, 0.015558]** | **PASS** |
| GreenEarthNet / Extreme | **C1_G** | Actual vs donor | **0.634493** | 0.588372 | **0.147289** | 0.156135 | -- | [--, --] | actual > donor |
| GreenEarthNet / Extreme | **C1_G** | Actual vs mean | **0.634493** | 0.557833 | **0.147289** | 0.192398 | -- | [--, --] | actual > mean |
| GreenEarthNet / Hot-dry | **C1_G** | Interaction | n.a. | n.a. | n.a. | n.a. | **-0.000302** | **[-0.002841, 0.002582]** | **FAIL** |
| Independent / Overall | Weather baseline_A | Actual vs control | -- | -- | -- | -- | -- | [--, --] | -- |
| Independent / Overall | **C1_A** | Actual vs control | -- | -- | -- | -- | -- | [--, --] | -- |

### 完成标准

- Contextformer 或代表性天气感知基线完成同类控制；
- C0R_G 完成天气响应以解耦 Q3 和 Q4；
- donor matching 规则冻结；
- 第二数据集至少完成 actual vs mean，条件允许再做 donor；
- 热旱负结果在主表保留；
- 与 Fig. 7 的天气、轨迹和地图一致。

## 42. Table 6：Q4 持续推进与组合一致性

### 一句话目的

精确报告 C0R/C1 在不同终点、分段数和留出分段方式下的直接/分段准确性与一致性。

### 已完成锁定结果

| Dataset | Model | Horizon | Direct RMSE↓ / R²↑ | Worst segmented degradation↓ | Q4 gates | Status |
|---|---|---:|---:|---:|---|---|
| GreenEarthNet locked | **C1** | 10 | 0.1377 / 0.630 | **0.8%** | 4/4 PASS | **PASS** |
| GreenEarthNet locked | **C1** | 15 | 0.1596 / 0.493 | **1.0%** | 4/4 PASS | **PASS** |
| GreenEarthNet locked | **C1** | 20 | 0.1617 / 0.531 | **1.2%** | 4/4 PASS | **PASS** |
| GreenEarthNet locked | C0R | 10 | 0.1369 / 0.634 | 9.2% | 2/4 PASS | **FAIL** |
| GreenEarthNet locked | C0R | 15 | 0.1600 / 0.491 | 9.1% | 2/4 PASS | **FAIL** |
| GreenEarthNet locked | C0R | 20 | 0.1628 / 0.525 | 14.7% | 2/4 PASS | **FAIL** |

### 确认实验模板

| Dataset | Model | Seeds | Horizon | Partition | Direct RMSE↓ | Segmented RMSE↓ | Relative degradation↓ | Pooled R²↑ | 95% CI | Gate |
|---|---|---:|---:|---|---:|---:|---:|---:|---|---|
| GreenEarthNet confirm | C0R_G | -- | 10/15/20 | 2/3/4 segments | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet confirm | **C1_G** | -- | 10/15/20 | 2/3/4 segments | -- | -- | -- | -- | [--, --] | -- |
| Independent dataset | C0R_A | -- | -- | -- | -- | -- | -- | -- | [--, --] | -- |
| Independent dataset | **C1_A** | -- | -- | -- | -- | -- | -- | -- | [--, --] | -- |

### 完成标准

- 多种子和 held-out partitions 完成；
- 主指标统一使用 pooled R²/RMSE；
- 直接与分段的绝对准确性均报告；
- state gap 和 output gap 定义可复现；
- 修正后的端点非劣 19/19 口径和原聚合问题同时说明；
- 与 Fig. 8 的曲线、分布和地图来源一致。

## 43. Table 7：计算与状态接口成本

### 一句话目的

说明显式状态、分段推进和状态保存恢复的额外代价，并量化相对重复编码完整历史的收益。

### 表格模板

| Method | Params↓ | FLOPs/sample↓ | Peak VRAM↓ | Train time/epoch↓ | Direct inference↓ | Segmented inference↓ | Runtime state size↓ | Save/load time↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PredRNN | **1.43M** | -- | -- | -- | -- | n.a. | n.a. | n.a. |
| Contextformer | **6.06M** | -- | -- | -- | -- | n.a. | n.a. | n.a. |
| C0R | **7.18M** | -- | -- | -- | -- | -- | -- | -- |
| **TerraState-C1** | **7.18M** | -- | -- | -- | -- | -- | -- | -- |

### 附加比较

建议增加一组运行场景：

| Operation | Full-history re-encode | Resume from saved state | Relative saving |
|---|---:|---:|---:|
| Advance one new weather segment | -- | -- | -- |
| Create two weather branches | -- | -- | -- |
| Restore state and decode | n.a. | -- | n.a. |

### 完成标准

- 所有模型在同一硬件、精度和输入尺寸测量；
- 报告预热、重复次数和统计波动；
- 计算与文件 I/O 分开；
- 保存后恢复结果与连续内存推进在数值容差内一致；
- 不只报参数量而省略速度和状态大小。

---

# 第九部分：图表叙事顺序

## 44. 主文阅读路径

1. **Fig. 1** 提出科学问题：为什么固定时距预测不足以证明存在世界状态。
2. **Fig. 2** 给出方法答案：显式状态、共享变跨度转移和递归事实监督。
3. **Table 1 + Fig. 3** 证明主数据集上的基础预测能力和空间质量。
4. **Table 2 + Fig. 4** 证明独立数据集上的外部有效性。
5. **Fig. 5** 展示两个数据集的时距退化和 OOD 边界。
6. **Table 3** 隔离完整模型、C0R 和功能干预的机制差异。
7. **Table 4 + Fig. 6** 证明显式状态真实承担预测。
8. **Table 5 + Fig. 7** 证明模型使用给定天气形成条件未来。
9. **Table 6 + Fig. 8** 证明状态能够持续、分段一致地推进，且该性质来自递归事实监督。
10. **Table 7** 交代计算成本、状态大小和保存恢复代价。

## 45. 图表与正文的对应关系

| 正文章节 | 核心图表 | 本节必须得出的结论 |
|---|---|---|
| Introduction（引言） | Fig. 1 | 固定预测准确不等于可复用世界状态，科学问题成立 |
| Method（方法） | Fig. 2 | TerraState 如何构造状态并用递归事实监督训练续推能力 |
| Forecasting experiments（预测实验） | Table 1-2、Fig. 3-5 | 模型具有竞争力，并公开跨数据、OOD 和长时边界 |
| Mechanism study（机制研究） | Table 3 | C1 的关键差异是递归事实路径，而非参数量 |
| State intervention（状态干预） | Table 4、Fig. 6 | 显式状态真实承担输出 |
| Weather intervention（天气干预） | Table 5、Fig. 7 | 模型使用给定天气，但不声称因果反事实 |
| Continuation audit（持续推进审计） | Table 6、Fig. 8 | C1 的中间状态可续推且跨时间分段近似一致 |
| Efficiency and limitations（效率与限制） | Table 7 | 新能力的工程代价和适用边界透明 |

## 46. Q2-Q4 为什么各有一图一表

| 主张 | 表格内容 | 图形内容 | 重复红线 |
|---|---|---|---|
| Q2 | 每个 split/seed 的 full、prior-only、效应、CI 和判定 | 效应随时距变化、样本分布、空间贡献位置 | 不能只把四个 Delta R² 画成柱状图 |
| Q3 | actual/donor/mean 的精确指标、效应、CI 和负结果 | 天气输入、NDVI 轨迹、终点地图和差异图 | 不能只把两行 Delta Loss 改成柱状图 |
| Q4 | endpoint/partition/seed 的直接、分段、CI 和 gate | 退化过程、C1/C0R 量级、状态/输出分布和地图 | 不能只画 19/19 大勾号或重复 gate 矩阵 |

同一主张的图和表有关联，但作用不同。表格类似可复核的测量报告，图类似模型行为记录。只有二者共同存在，审稿人才能同时判断“总体结论是否显著”和“该结论在时间、空间及样本层面如何发生”。

---

# 第十部分：实验执行优先级

## 47. P0：首先封闭核心因果链

### P0-1 冻结模型和评测身份

**任务**：冻结 C1/C0R 配置、参数量、事实训练路径、训练 partitions、held-out partitions、Q4 pooled 指标与 gate。

**产物**：

- 论文默认配置；
- 模型结构哈希和权重索引；
- 数据 manifest；
- Q4 protocol JSON；
- C0R/C1 差分说明；
- Fig. 2 可追溯结构清单。

**完成判定**：代码、配置、公式、图示和实验日志对同一模型给出一致定义。

### P0-2 C1 多种子预测

**任务**：补齐 C1 至少 3 seeds × GreenEarthNet 四 split，并导出总体和逐 horizon 结果。

**产物**：Table 1 mean±std、Fig. 5 置信带、Table 4 多种子 Q2、Table 6 多种子 Q4。

**完成判定**：主要预测和行为结论方向跨种子稳定；若不稳定，必须报告并调整主张。

### P0-3 C0R/C1 严格同预算确认

**任务**：使用配对种子、相同端点和预算补齐 C0R/C1 的 Q1、Q2 和 Q4。

**产物**：Table 3、Table 6 和 Fig. 8。

**完成判定**：C1 的持续推进优势在多种子下保持，且 direct prediction 不因机制发生明显坍塌。

### P0-4 生成现有结果图

**任务**：不等待第二数据集，先从已有 JSON 和预测缓存生成 GreenEarthNet 的 Fig. 3、5、6、7、8 草图。

**产物**：

- 固定样例 manifest；
- 逐 horizon 绘图数据；
- Q2 per-sample 分布；
- Q3 天气/NDVI 轨迹和地图；
- Q4 C0R/C1 曲线、分布和空间终点。

**完成判定**：每个图都能追溯到冻结结果；没有用示意数据冒充实验数据。

### P0-5 状态保存、恢复与继续接口

**任务**：实现统一 `initialize/advance/decode/branch` 薄接口，以及 state save/load/resume 测试。

**产物**：Fig. 2 API、Table 7 state size/save/load time、数值一致性测试。

**完成判定**：保存后恢复推进与内存连续推进在冻结容差内一致，并且无需重新编码完整历史。

### P0-6 直接同行比较

**任务**：核对与当前遥感世界模型/天气情景模型的输入、输出、分辨率和指标。能够同协议复现的进入结果表，不能直接比较的进入能力与协议矩阵。

**产物**：Table 1-3 的可比行或 Related Work/补充材料中的协议矩阵。

**完成判定**：不以任务不一致的论文数字构造虚假排行榜，也不只与较早的视频预测模型比较。

## 48. P1：跨数据与完整呈现

### P1-1 独立数据集审计

**任务**：审计数据许可、空间/时间范围、与 GreenEarthNet 的样本重合、目标变量、mask、时间分辨率和官方指标。

**产物**：数据审计记录、输入/输出适配规范、训练和评测 manifest。

**完成判定**：能够证明该数据提供真实的外部有效性，而不是同一数据的版本重切分。

### P1-2 第二数据集预测

**任务**：训练无学习基线、官方/视频强基线、Contextformer_A、C0R_A 和 C1_A。

**产物**：Table 2、Fig. 4、Fig. 5 第二数据集面板。

**完成判定**：native metrics 和 common NDVI metrics 均可复现，定性样例按冻结规则生成。

### P1-3 第二数据集 Q2-Q4 精简复验

**任务**：在独立训练的 C1_A 上复验状态承载和天气响应，在 C0R_A/C1_A 上复验持续推进。

**产物**：Table 4-6 的独立数据集行；必要时 Fig. 6-8 增加紧凑小面板。

**完成判定**：核心效应方向一致；若不一致，依据数据时间尺度和观测条件解释并收窄结论，不隐藏冲突。

### P1-4 效率和不确定性

**任务**：完成 FLOPs、显存、训练/推理速度、状态大小、保存恢复成本和最基本的不确定性评测。

**产物**：Table 7、补充材料 calibration plots（校准图）。

**完成判定**：测量环境一致，所有数字有原始日志，模型限制被明确报告。

## 49. P2：根据核心结果决定的增强项

| 增强项 | 启动条件 | 作用 | 停止条件 |
|---|---|---|---|
| Latent consistency loss（状态一致性损失） | C1 多种子 Q4 波动大 | 直接约束状态路径 | 损害 Q1 或不能稳定改善 Q4 |
| Output consistency loss（输出一致性损失） | 状态一致但输出仍不稳定 | 约束直接/分段输出 | 只改善自一致却降低真实预测 |
| Quantile/probabilistic head（分位数/概率头） | 确定性边界成为主要审稿风险 | 提供预测不确定性 | 抢占主线、预算过高或破坏状态机制 |
| Geography ablation（地理消融） | 需要拆分静态条件贡献 | 分析地理先验作用 | 对主要结论无解释价值 |
| 更长 horizon | 数据具有可靠长时真值 | 检验持续推进极限 | 缺测和目标噪声主导指标 |

P2 不用于“堆实验”。只有当它解决明确风险或解释已观察结果时才进入主文，否则放补充材料或停止。

## 50. 完成度总表

| 实验/产物 | 当前状态 | 尚缺内容 | 优先级 |
|---|---|---|---|
| GreenEarthNet 外部基线 | 已完成 | 最终排版与来源脚注 | P0 |
| C1 GreenEarthNet Q1 | 部分完成 | 2 个以上种子、逐时距 CI | P0 |
| Q2 状态承载 | 核心完成 | 多种子、时距/分布/地图、独立数据复验 | P0/P1 |
| Q3 天气响应 | 核心完成 | 天气基线、轨迹/地图、多种子或跨数据 | P0/P1 |
| Q4 持续推进 | 核心完成 | 多种子、留出分段确认、独立数据复验 | P0/P1 |
| C0R/C1 机制对照 | 部分完成 | 配对种子 Q1/Q2/Q4 完整表 | P0 |
| Fig. 1 科学问题 | 可立即完成 | 矢量绘制与图注 | P0 |
| Fig. 2 方法架构 | 可立即完成 | API 与最终代码核对 | P0 |
| GreenEarthNet 结果图 | 待制作 | 固定样例、曲线、分布和地图 | P0 |
| 独立数据集 | 待完成 | 审计、适配、训练和评测 | P1 |
| 效率与状态接口 | 部分完成 | 除参数量外全部指标 | P1 |
| 不确定性边界 | 待完成 | 校准或覆盖率、误差分层 | P1/P2 |

---

# 第十一部分：论文结构

## 51. Abstract（摘要）

摘要按五句逻辑组织：

1. 固定窗口遥感预测的局限；
2. 可复用空间预测状态的科学问题；
3. TerraState 和递归事实监督；
4. Q1-Q4 与两数据集实验；
5. 主要事实结论和遥感世界模型意义。

摘要不得只罗列模块，也不得在没有最终多种子和第二数据集数字前写具体最优百分比。

## 52. Introduction（引言）

### Paragraph 1：应用背景

说明高分辨率地球观测预测在植被监测、生态变化和天气情景分析中的价值，以及云遮挡、稀疏观测和外部天气驱动带来的部分可观测问题。

### Paragraph 2：现有范式

说明大多数方法关注从固定历史窗口生成固定未来，近期工作已扩展到概率生成、天气条件和情景模拟。

### Paragraph 3：核心缺口

指出生成未来不自动意味着存在可保存和续推的世界状态；状态可能不承担输出，直接/分段路径可能不一致。

### Paragraph 4：科学问题

正式提出“能否学习真正面向未来的空间预测状态，使不同时间跨度转移可组合，并使中间状态继续承担预测”。Fig. 1 在此出现。

### Paragraph 5：方法

介绍显式状态、共享变跨度转移、递归事实监督和状态接口。Fig. 2 在方法节展开。

### Paragraph 6：验证逻辑

介绍 Q1-Q4，不把这些问题写成彼此孤立的实验，而写成世界模型运行契约的递进证据。

### Paragraph 7：贡献

用第 12 节四项贡献，避免重复摘要或把数据集本身当作创新。

## 53. Related Work（相关工作）

建议分为：

1. High-resolution Earth-observation forecasting；
2. Video prediction and spatiotemporal modeling；
3. Earth-observation world models and weather-conditioned simulation；
4. Predictive-state representations and compositional dynamics。

相关工作最后用一个短段落明确 TerraState 的位置：不以“首次递归”或“首次使用天气”为空位，而以密集空间预测状态、递归事实监督和持续推进审计为核心。

## 54. Method（方法）

建议结构：

1. Problem formulation；
2. Context encoding and state initialization；
3. Weather-driven variable-span transition；
4. State readout and runtime interface；
5. Recursive factual supervision；
6. Direct and segmented rollout；
7. Training objective and implementation details。

方法节必须明确 context prior 的存在、运行时状态构成以及 C0R/C1 的事实路径差异。

## 55. Experiments（实验）

建议结构：

1. Datasets and protocols；
2. Baselines and implementation details；
3. Q1 forecasting performance；
4. Q2 load-bearing state；
5. Q3 weather-conditioned response；
6. Q4 continuation consistency；
7. Mechanism ablations；
8. Efficiency, uncertainty and limitations。

每节开头先写假设和判定标准，再写结果。不要先展示有利数字，之后才补定义。

## 56. Discussion and Limitations（讨论与局限）

需要主动讨论：

- 领域世界模型与完整地球系统模型的区别；
- 确定性预测无法表达多模态未来；
- 未观测管理活动、灾害与传感器缺失；
- 天气干预是条件响应而非因果效应；
- 长时误差仍会累积，组合一致不等于无限期准确；
- context prior 意味着运行状态不应被简化为 `z`；
- 热旱特异增强未得到支持；
- 第二数据集差异及跨区域适用范围。

## 57. Conclusion（结论）

结论应回到科学问题：TerraState 是否学习了一个能够继续代表当前观测世界的状态。结论顺序为预测能力、状态承载、天气响应、持续推进，再陈述对遥感世界模型设计和评价的意义。

---

# 第十二部分：主张边界与写作控制

## 58. 可以主张的内容

在现有核心结果和计划实验完成后，可使用：

- `weather-driven Earth-observation world model`；
- `explicit spatial predictive state`；
- `load-bearing state contribution`；
- `conditional response to supplied future weather`；
- `continuation-consistent direct and segmented rollout`；
- `recursive factual supervision improves state reusability`；
- `competitive multi-step forecasting performance`；
- `reusable runtime state supporting save, resume and conditional branching`。

## 59. 不应主张的内容

除非未来新增直接证据，否则不得使用：

- “complete Earth system model（完整地球系统模型）”；
- “state contains the full physical world（状态包含完整物理世界）”；
- “causal weather intervention（天气因果干预）”；
- “counterfactual prediction（反事实预测）”；
- “planning or control（规划或控制）”；
- “indefinitely stable rollout（无限期稳定推进）”；
- “state-of-the-art accuracy（最先进精度）”；
- “specific robustness to hot-dry extremes（对热旱极端的特异稳健性）”；
- “all existing world models lack recurrence or weather conditioning”。

## 60. 术语表

| 英文术语 | 中文含义 | 使用边界 |
|---|---|---|
| world model | 世界模型 | 维护状态并按驱动模拟未来，不等于大模型 |
| domain world model | 领域世界模型 | 对特定地表过程建模，不覆盖完整地球系统 |
| spatial predictive state | 空间预测状态 | 保留空间结构并支撑未来预测的任务相关状态 |
| reusable state | 可复用状态 | 可保存、恢复、续推、解码和分支 |
| load-bearing state | 承担预测的状态 | 移除状态贡献后预测显著退化 |
| external forcing | 外部驱动 | 推进状态的外生天气输入，不称为智能体动作 |
| direct rollout | 直接推进 | 一次变跨度调用到目标终点 |
| segmented rollout | 分段推进 | 经一个或多个中间状态继续到同一终点 |
| continuation consistency | 持续推进一致性 | 直接和分段推进在准确前提下近似一致 |
| compositional transition | 可组合状态转移 | 长跨度转移可由若干子跨度转移近似组成 |
| recursive factual supervision | 递归事实监督 | 真实预测目标经递归状态路径监督模型 |
| factual path | 事实路径 | 训练时产生真实目标预测并接受事实损失的路径 |
| context prior | 上下文先验 | 从历史上下文直接形成的预测支路 |
| conditional branch | 条件分支 | 在不同给定天气下生成未来，不等于因果反事实 |
| native metric | 数据集原生指标 | 用于与该数据集已有工作比较 |
| common metric | 共同指标 | 跨数据观察同类行为，不代表数据难度相同 |

## 61. 结果写作模板

### Q1

> TerraState maintains competitive multi-step forecasting performance across IID and out-of-distribution splits while introducing an explicit reusable state. Its contribution is therefore not based on sacrificing the underlying forecasting task, although it does not consistently outperform the strongest accuracy-oriented predictors.

### Q2

> Removing the state-mediated readout consistently degrades prediction across all evaluated splits, showing that the explicit spatial state is functionally load-bearing rather than an unused auxiliary representation.

### Q3

> Predictions conditioned on the observed future weather achieve higher endpoint fidelity than matched donor and mean-weather controls, indicating that TerraState uses the supplied forcing. This experiment measures conditional response fidelity and is not interpreted as a causal intervention.

### Q4

> TerraState preserves endpoint accuracy under held-out temporal partitions, whereas the parameter-matched direct-path control exhibits substantially larger degradation. This contrast supports the role of recursive factual supervision in learning continuation-consistent predictive states.

## 62. 审稿风险与对应证据

| 潜在质疑 | 为什么成立 | 必须提供的回答 |
|---|---|---|
| “只是 Contextformer 加模块” | 使用相同上下文骨干 | Fig. 2、C0R/C1、Table 3 说明真正贡献是状态转移与事实路径 |
| “只是一种普通递归预测器” | 视频预测也可递归 | Q2 状态承载、Q3 驱动、Q4 留出分段组合审计共同回答 |
| “暂停继续只是代码技巧” | 任意张量都可以保存 | 不重编码历史的 state API、held-out partitions、C0R/C1 量级差、Table 7 |
| “自定义指标只对自己有利” | Q2-Q4 包含专门行为指标 | 同时报告标准 Q1、pooled R²/RMSE、CI、公开协议和失败条件 |
| “状态由 context prior 旁路” | 输出确实包含 prior | 公开公式和 Fig. 2；Q2 alpha=0 干预；空间贡献图 |
| “天气响应不独特” | 同行已使用天气 | 加天气感知基线；独特性放在可复用空间状态和 Q4 |
| “单数据集自证” | 当前主要证据来自 GreenEarthNet | 独立数据集重新训练和 Q2-Q4 精简复验 |
| “C1 精度不够强” | 当前低于最强基线 | 使用 competitive 表述，强调性质提升不牺牲预测，并诚实排名 |
| “Q4 指标修正不可信” | 曾出现 per-cube R² 聚合问题 | 披露原问题、封存统计量、修正 pooled 公式和新确认实验 |
| “确定性未来不符合世界不确定性” | 遥感未来确有多模态性 | 多种子/校准边界；必要时探索概率头，不夸大当前能力 |

---

# 第十三部分：最终验收

## 63. 模型验收

- [ ] 论文默认 `TerraState` 唯一指向 C1；
- [ ] C0R/C1 只有事实路径这一核心差分；
- [ ] `runtime_state` 定义与代码一致；
- [ ] `initialize/advance/decode/branch` 可实际调用；
- [ ] 状态可保存、恢复并在数值容差内继续；
- [ ] Fig. 2、方法公式和实现不存在结构矛盾。

## 64. 实验验收

- [ ] GreenEarthNet C1 至少 3 seeds × 4 splits；
- [ ] C0R/C1 配对种子、相同预算和相同端点；
- [ ] Q2 四 split、多种子和独立数据精简复验；
- [ ] Q3 C1、C0R、天气感知基线和独立数据复验；
- [ ] Q4 多终点、多分段、held-out partitions、多种子和独立数据复验；
- [ ] 所有 Q4 主结果使用冻结 pooled 指标；
- [ ] 第二数据集独立性、许可和协议完成审计；
- [ ] Table 7 除参数量外的效率指标完成；
- [ ] 负结果和冲突结果没有被删除。

## 65. 图表验收

- [ ] Fig. 1 清晰定义科学问题和世界模型运行契约；
- [ ] Fig. 2 清晰展示共享状态转移和递归事实监督；
- [ ] Fig. 3-4 包含典型、高动态和困难样例，但不把失败案例作为主图硬性中心；
- [ ] Fig. 5 报告逐时距与 CI，而非总体均值柱状图；
- [ ] Fig. 6-8 均由完整多面板组成，并与 Table 4-6 互补；
- [ ] Table 1-7 均有唯一数据源；
- [ ] 所有空值在投稿前填充、标为 n.a. 或有明确脚注；
- [ ] 色标、mask、模型颜色、图例和统计口径统一；
- [ ] 所有定性样例有冻结 manifest 和原始预测文件。

## 66. 论文主线验收

读者在只阅读标题、摘要、Fig. 1、Fig. 2 和贡献列表后，应能准确复述：

> **TerraState 构建了一个天气驱动的高分辨率地球观测世界模型。该模型学习显式空间预测状态，并通过共享变跨度转移与递归事实监督，使中间状态能够继续承担后续预测；论文通过预测能力、状态承载、天气响应和直接/分段一致性验证这一状态是否真正可复用。**

如果读者仍将论文概括为“Contextformer 加了状态模块”“分析隐藏状态是否有用”或“提出一组新的遥感预测指标”，说明标题、摘要、Fig. 1、Fig. 2 或贡献列表尚未围绕唯一主线写清楚。

## 67. 最终总述

TerraState 的研究价值不建立在给普通预测器更换名称，也不建立在只对自身有利的评价尺度上。论文首先接受标准遥感预测任务的检验，再依次验证显式状态是否承担输出、是否响应未来天气、是否能够在不同时间分段下持续推进，并通过同参数 C0R/C1 对照定位递归事实监督的作用。

最终应形成如下完整论证：

```text
部分可观测、天气驱动的高分辨率地球观测问题
 -> 显式空间预测状态
 -> 共享变跨度状态转移
 -> 递归事实监督
 -> Q1 标准预测能力
 -> Q2 状态真实承载预测
 -> Q3 使用给定天气形成条件未来
 -> Q4 中间状态可续推且跨时间分段一致
 -> 两数据集、多种子、强基线和效率验证
 -> 一个可证伪、可运行且边界清楚的遥感领域世界模型
```
