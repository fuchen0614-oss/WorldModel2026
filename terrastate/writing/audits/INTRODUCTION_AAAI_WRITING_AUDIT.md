# TerraState Introduction：AAAI 写作锚点与修订审计

> 状态：RESEARCH COMPLETE / REVISION BASIS  
> 日期：2026-07-27  
> 审计对象：`paper/main.tex` 第 52--129 行的 Introduction

## 1. 一手 AAAI 写作锚点

### 1.1 ReconVLA（AAAI-26）

- 官方论文：
  https://ojs.aaai.org/index.php/AAAI/article/view/38921
- Introduction 信息顺序：
  1. VLA 的任务背景与已有能力；
  2. 把“准确视觉 grounding”收窄为核心需求；
  3. 用观察到的 attention failure 提出具体问题；
  4. 解释现有显式 grounding 方案为什么没有解决根因；
  5. 给出 reconstructive mechanism；
  6. 简要总结实验覆盖；
  7. 列出贡献。
- 可借鉴原则：缺口必须落到一个可观察的机制失败，而不能停留在“精度仍可提升”。
- 不应照搬：其引言包含较多数据集建设和实验宣传；TerraState 的核心不是数据集或
  SOTA，因此应更克制。

### 1.2 LLM2CLIP（AAAI-26）

- 官方论文：
  https://ojs.aaai.org/index.php/AAAI/article/view/37427
- Introduction 信息顺序：
  1. 先明确 CLIP 的方法身份和应用地位；
  2. 说明现有表示能力在新需求下为何不足；
  3. 形成一个明确研究问题；
  4. 拆出两个具体技术挑战；
  5. 方法逐一回应挑战；
  6. 用一小段概括经验结果；
  7. 列出贡献。
- 可借鉴原则：方法身份必须在第一段明确；挑战和模块是一一对应关系。
- 不应照搬：它在引言贡献中使用很多具体增益数字。TerraState 的卖点不是绝对
  Q1 数字，详细数值应留在 Results。

### 1.3 WorldAgen（AAAI-26）

- 官方论文：
  https://ojs.aaai.org/index.php/AAAI/article/view/38925
- Introduction 信息顺序：
  1. 说明 VLA 与 world modeling 的关系；
  2. 指出静态预训练在分布偏移下的根本限制；
  3. 把缺口写成研究问题；
  4. 立即给出两个方法组件；
  5. 用一句“reframes world modeling ...”总结概念变化；
  6. 列出方法和经验贡献。
- 可借鉴原则：world model 不是在贡献列表才突然出现，而是在背景、缺口、方法和
  概念总结中持续充当组织轴。
- 不应照搬：WorldAgen 的 world model 以机器人状态/动作与测试时适应为中心；
  TerraState 必须采用适合部分可观测 EO 与外生天气驱动的定义。

### 1.4 Model Change for Description Logic Concepts（AAAI-26）

- 官方论文：
  https://ojs.aaai.org/index.php/AAAI/article/view/39008
- Introduction 信息顺序：
  1. 给出大问题；
  2. 解释为什么已有形式不适合目标场景；
  3. 用具体例子逐步定义 eviction、reception、revision；
  4. 由例子导出正式问题和贡献；
  5. 说明违反直觉的主要发现。
- 可借鉴原则：核心术语必须在读者第一次需要它时直观定义，而不是等到贡献列表或
  Method 才补定义。
- 不应照搬：理论论文可以用长例子替代实验动机；TerraState 需要更快进入模型和
  可验证缺口。

### 1.5 High-Pass Matters（AAAI-26）

- 官方论文：
  https://ojs.aaai.org/index.php/AAAI/article/view/39469
- 摘要和引言所体现的主线：
  常用范式 → 被忽略的结构成分 → 理论问题 → 理论洞见 → 由洞见导出的模型 →
  实验验证。
- 可借鉴原则：方法应被写成对根因的直接回应。TerraState 对应的是：
  endpoint accuracy 看不见内部状态是否承担预测，因此把状态放入预测闭环并实施
  匹配干预。

## 2. 从锚点归纳出的 Introduction 规范

AAAI 并没有禁止引言出现实验结果。上述方法论文通常会在贡献列表之前或贡献列表中
提供经验概述。关键区别在于：

- **允许**：一小段定性总结或少量最关键数字，用来说明方法主张获得了什么支持；
- **不理想**：在引言中复述所有指标、样本数、两套统计量和 null result；
- **必须**：结果概述只能在问题、方法身份和机制已经讲清楚之后出现；
- **必须**：Introduction 的结果强度不得高于 Results 和 Limitations。

对 TerraState，最稳妥的做法是保留一个两句的定性 evidence preview：

1. Q1 保留有效 OOD-t 预测能力；
2. Q2 配对区间不跨零，Q3 真实天气优于两个控制。

详细 \(R^2\)、RMSE、official delta、paired mean、CI、样本数和 hot--dry null 均
留在 Results/Limitations。

## 3. 当前引言的主要问题

### MAJOR-1：世界模型身份出现过晚

当前第一段主要是 EO 数据集和预测方法综述。读者直到第二段末尾才看到
`world state`，直到贡献列表才明确看到 `predictive-state world model`。

**修订原则：** 第一段直接把任务定义为 partially observed world-modeling
problem，并立刻给出“历史观测 → 预测状态 → 外生天气转移 → 未来可观测量”的
直观定义。

### MAJOR-2：世界模型的判据没有完整表达

当前第三段只定义“两个可测性质”，但没有先说明 TerraState 为什么是 world
model。这样容易被理解为给普通 forecaster 添加两个 diagnostics。

**修订原则：** 先定义完整状态闭环，再说明 TerraState 的额外要求是该状态必须
位于预测路径且可通过匹配干预检验。

### MAJOR-3：第一段承担了 Related Work 的任务

当前第一段连续列举 recurrent、convolutional、transformer、diffusion、
uncertainty、EO-WM 和 VegSim，方法身份反而被推迟。

**修订原则：** 第一段只保留 EarthNet2021/GreenEarthNet 作为任务来源。模型类别和
最近工作差异留给 Related Work。

### MAJOR-4：结果预览过细

当前结果段包含：

- OOD-t 样本数；
- Q1 的两个精确指标；
- Q2 official delta；
- Q2 paired means 和 CI；
- Q3 方向；
- hot--dry null。

这些细节应由 Results 和 Limitations 承担。

**修订原则：** 引言只保留定性证据链，不报告具体小数，不讨论 exploratory null。

### MINOR-1：`forecast closure` 早于直观解释

该术语在引言中容易表现为工程内部接口。

**修订原则：** 先写“the advanced state makes an explicit contribution to the
final forecast”，正式公式和 forecast closure 留到 Method。

## 4. TerraState 引言的段落设计

### Paragraph 1：任务与世界模型身份

- EO 的应用价值与部分可观测性；
- 天气和静态地理决定地表演化；
- 把任务明确写成 partially observed world-modeling problem；
- 直观定义“状态—转移—可观测预测”闭环；
- 用 EarthNet2021/GreenEarthNet 确立公开任务背景。

### Paragraph 2：结构性缺口

- 现有工作主要按 endpoint accuracy 选择；
- 精度对有用模型是必要的，但不能证明内部预测状态；
- 两种具体失败：预测绕开声明状态；未来天气使用很弱；
- 提出核心问题。

### Paragraph 3：操作性定义与研究位置

- TerraState 采用何种 world-model 定义；
- predictive state 的两个可测性质；
- 与完整物理状态、因果模拟器划清边界；
- 与 EO-WM 输出响应、VegSim latent rollout 的关系。

### Paragraph 4：方法回应

- 历史编码与 context-only forecast；
- spatial predictive state；
- shared weather-conditioned transition；
- state readout 与显式加法；
- future-observation state anchor；
- Q1--Q3 与方法组件一一对应。

### Paragraph 5：证据预览

- 只定性报告 Q1--Q3；
- 不出现数字、样本数和 hot--dry null；
- 不使用 SOTA、competitive 或 causal。

### Contributions

1. 问题与模型：把天气驱动 EO 预测表述为可检验预测状态世界建模；
2. 方法洞见：未来观测状态锚定位于预测路径中的 transitioned state；
3. 证据：同一选定模型上的 Q1--Q3。

## 5. 句级 claim--evidence 计划

| 计划主张 | 类型 | 依据 |
|---|---|---|
| 任务是部分可观测、天气驱动的 world modeling | BACKGROUND / FORMULATION | EarthNet2021、GreenEarthNet；本文形式化 |
| world model 推断状态、由外生天气推进并映射回观测 | METHOD IDENTITY | Eq. 1 与代码事实 |
| endpoint accuracy 不能证明内部状态承担预测 | PROBLEM CLAIM | 逻辑区分；LatentTSF 支持精度与潜表示结构可分离 |
| 状态必须贡献预测且正确使用天气 | METHOD DEFINITION | Q2/Q3 冻结合同 |
| future-state anchor 不进入推理 | METHOD FACT | 唯一训练合同 |
| useful OOD-t skill | SUPPORTED / QUALIFIED | Q1 |
| state contribution is load-bearing | SUPPORTED | Q2 state ablation |
| actual weather is more faithful than controls | SUPPORTED / QUALIFIED | Q3 |
| causal、complete physical state、extreme enhancement | UNSUPPORTED | 不进入正面主张 |

## 6. 写后复审标准

- 第一段结束前必须出现 world-modeling problem 和直观定义；
- 第二段结束时审稿人应清楚“为什么单靠精度不够”；
- 第三段结束时应清楚 TerraState 与普通 forecaster + diagnostic 的差别；
- 方法段每个组件都必须回应前面的缺口；
- 结果段不得与 Results 争夺细节；
- 三条贡献分别对应问题、方法和证据，不重复；
- Figure 1 的首次引用必须紧邻方法概述；
- 引言不能引入 Q4、composition、SOTA 或 matched-backbone。

