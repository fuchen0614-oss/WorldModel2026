# TerraState AAAI-27 最终语法、学术表达与 AAAI 写作风格审计

审计日期：2026-07-29  
审计性质：独立、只读、逐句语言与版面呈现审计  
权威正文：`paper/main.tex`  
最终状态：**READY_FOR_MINIMAL_LANGUAGE_REVISION**

## 1. 范围、冻结输入与判定原则

### 1.1 输入 SHA-256

| 输入 | SHA-256 | 用途 |
|---|---|---|
| `paper/main.tex` | `5fe0a77682e715e51fa2a25442157d4e39c0d7c5f99c0b1663658000622fcd92` | 唯一正文事实源；完整逐句审计 |
| `示例/gai.pdf` | `6ca186cf8ed9b6ca16abd733c04688393ff044daf6eb5533ee201af50f643948` | 只读取第一页正文和 7 个 PDF 批注对象 |
| `paper/main.pdf` | `f4a77def9e89809565ef382230da30a45e22e5d665c1e1d547579087f8ba0d58` | 8 页；检查断词、标点和版面呈现 |

`gai.pdf` 第一页确有 7 个 annotation，第二页及以后无 annotation。本报告逐条裁决
这 7 条意见，不把批注者的个人偏好自动视为语法规则。

### 1.2 审计边界

本轮不修改正文、PDF、Markdown 镜像、图片、表格、引用或实验；不重新编译。所有
建议都必须保持：

- 40 epochs / 14,880 updates；
- Q1--Q3 的定义、数字、统计单位、证据层级和结论；
- state removal 为 Q2 primary，\(T\to I\) 为 supporting；
- Q3 为完整 20 步窗口的 conditional predictive fidelity；
- 非因果、非反事实、非完整物理状态、非通用模拟器、非 composition、非 SOTA 的边界。

否定句按语义审计，而非机械删除。表达“证据不能建立什么”的 `cannot`/`does not`
属于认识论边界，除非存在等价且更清楚的表达，否则必须保留。

### 1.3 优先级

- **P0：** 明确语法错误，或文字歧义可能改变技术含义；
- **P1：** 明显影响可读性、逻辑或 AAAI 专业表达；
- **P2：** 纯风格、节奏或局部惯用性偏好，可不修改。

## 2. 总体结论

当前稿不存在 P0。全文语法稳定、段落职责清楚、术语一致，摘要与引言已经形成成熟
AAAI 方法论文常见的：

> 任务 → 固定时域输出评测的缺口 → predictive-state 问题 → TerraState 机制 →
> Q1--Q3 证据

主要语言问题集中在摘要的 5 个局部位置：开头主语与谓语的语义搭配、重复副词、三层
分词并列、`by architecture` 的搭配，以及最后一条结果长句。它们适合一次最小语言
修订，不需要重写摘要结构，更不需要改变任何主张。

全文去重后的问题计数：

| 优先级 | 数量 |
|---|---:|
| P0 | **0** |
| P1 | **8** |
| P2 | **6** |

## 3. AAAI 写作结构校准

本轮只学习正式 AAAI 论文的组织动作，不复制其句子或技术主张。

### 3.1 正式锚点

1. [Driving in the Occupancy World: Vision-Centric 4D Occupancy Forecasting and Planning via World Models for Autonomous Driving](https://ojs.aaai.org/index.php/AAAI/article/view/33010)，AAAI 2025。  
   开场由 autonomous-driving task 进入 world-model gap，再给 forecasting/planning
   身份、组件和实验结论。
2. [GLAM: Global-Local Variation Awareness in Mamba-based World Model](https://ojs.aaai.org/index.php/AAAI/article/view/33880)，AAAI 2025。  
   先给 MBRL/sample-efficiency 问题，再把缺口落在 state variation reasoning，
   随后给 global/local 两个机制和结果。
3. [Battling the Non-stationarity in Time Series Forecasting via Test-time Adaptation](https://ojs.aaai.org/index.php/AAAI/article/view/33965)，AAAI 2025。  
   从时间序列任务与应用进入 non-stationarity gap，再给 test-time adaptation
   insight、方法身份、机制和实验。
4. [Rethinking Irregular Time Series Forecasting: A Simple Yet Effective Baseline](https://ojs.aaai.org/index.php/AAAI/article/view/39563)，AAAI 2026。  
   从 irregular forecasting 的任务价值进入 data irregularity/complexity 两个
   challenge，再给 framework、核心模块、结果和 contributions。

### 3.2 对 TerraState 的校准结论

这些论文共同说明：AAAI 风格不要求所有句子都短，也不要求避免所有否定；关键是让
每个否定服务于一个清楚的 gap，并在其后迅速给出方法洞察、机制和证据。

TerraState 已经做到：

- 摘要第一部分给任务与评测缺口；
- 方法名称在 gap 后立即出现；
- predictive state、shared transition、state readout 和 interventions 构成紧凑
  方法概览；
- 结果按 forecasting skill → state contribution → weather fidelity 展开；
- 引言以六段完成 task → gap → question → method → evidence → contributions。

因此，当前问题是局部句子负载，而不是 AAAI 叙事结构失败。

## 4. `gai.pdf` 七条批注逐条裁决

### 批注 1

**Location:** Abstract，`main.tex:29--32`  
**Original:** `High-resolution satellite time series are a primary tool for monitoring ... and are increasingly cast as weather-driven forecasting: predicting ...`  
**Verdict:** **VALID**  
**Problem:** 不是主谓一致错误，而是语义施事搭配不自然。`satellite time series`
可以是监测工具，但 time series 本身不宜被 `cast as weather-driven forecasting`；
被建模为 forecasting task 的应是预测问题/使用这些序列的建模设置。批注所说“读起来
不舒服”有明确语言依据。  
**Minimal revision direction:** 保留第一句的任务价值，把“日益被表述为天气驱动
预测”明确落到 forecasting task/setting，而不是 time series 本身；可拆成两句。  
**Technical-meaning risk:** **中。** 修改主语时必须保留输入为 cloud-obscured
histories + meteorological drivers、输出为 future land-surface observations。  
**Priority:** **P1**

### 批注 2

**Location:** Abstract，`main.tex:32--38`  
**Original:** `... pixel accuracy, which cannot establish ... failures that standard error metrics cannot detect.`  
**Verdict:** **INVALID**  
**Problem:** “不要用 cannot，改成能力弱”是个人风格偏好，并会改变认识论含义。本文
主张不是标准指标“表现较弱”，而是输出精度**单独不足以建立**内部状态是否承载预测；
这一逻辑边界正是论文问题。后一个 `cannot detect` 也指输出误差无法区分若干内部失败
机制，并非无依据的绝对贬低。  
**Minimal revision direction:** 保留两个必要的 epistemic boundary。若压缩摘要，
可以减少周围冗余，但不能改成 `has weak ability to`。  
**Technical-meaning risk:** **高。** 按批注修改会把“证据不充分”误写成连续程度上的
“能力较弱”，削弱核心 gap。  
**Priority:** **不构成问题**

### 批注 3

**Location:** Abstract，`main.tex:33--35`  
**Original:** `a forecast-bearing, weather-responsive predictive state`  
**Verdict:** **INVALID**  
**Problem:** 逗号正确。`forecast-bearing` 和 `weather-responsive` 是并列的坐标性复合
形容词，共同修饰 `predictive state`；此处不是 comma splice，也不是逗号后缺句子。
摘要中列举 `vegetation, agriculture, and ecosystem response`、`future weather,
geography, and elapsed time` 的 Oxford comma 也正确。  
**Minimal revision direction:** 无需修改标点。  
**Technical-meaning risk:** **中。** 删除逗号会把两个独立性质读成层级修饰，反而降低
清晰度。  
**Priority:** **不构成问题**

### 批注 4

**Location:** Abstract，`main.tex:32--38`，从 `Yet such models ...` 到
`cannot detect`  
**Original:** `Yet such models are typically evaluated primarily ... An accurate forecaster may still ...`  
**Verdict:** **PARTLY VALID**  
**Problem:** 两句语法正确，也不能笼统称为“中式英语”。真正问题是
`typically evaluated primarily` 两个频率/主次副词叠加，以及第二句同时承载三种
failure mode 和 metric limitation。逻辑顺序本身是清楚的：评价范式 → 不能建立的
内部性质 → 可能漏检的失败。  
**Minimal revision direction:** 删除一个重复副词，并在不删除 `cannot establish /
cannot detect` 的前提下压缩 failure list 或调整句间节奏。  
**Technical-meaning risk:** **中。** 必须继续保留 weather ignoring、persistence 和
off-path latent state 三类风险。  
**Priority:** **P1**

### 批注 5

**Location:** Abstract，`main.tex:39--42`  
**Original:** `TerraState structures forecasting around a spatial predictive state inferred ..., advanced ..., and read out ...`  
**Verdict:** **PARTLY VALID**  
**Problem:** `inferred / advanced / read out` 是语法正确的平行 reduced-relative
结构，Oxford comma 也正确；`read out` 作为动词短语应写两词，不应改成名词性的
`read-out`。但一句中连续嵌入 state source、transition condition 和 output role，
首次阅读负载较高。批注建议拆句有价值；“多用定语从句”本身不是质量保证。  
**Minimal revision direction:** 最多拆为两句：第一句说明 history-derived state，
第二句说明 future-conditioned advancement 与 explicit output contribution。保持
state → transition → readout 的顺序。  
**Technical-meaning risk:** **高。** 拆句不能误写为 recursive rollout，也不能让
future weather 看似进入 history encoder。  
**Priority:** **P1**

### 批注 6

**Location:** Abstract，`main.tex:42--46`  
**Original:** `Rather than asserting a world state by architecture, TerraState makes this claim falsifiable through ...`  
**Verdict:** **INVALID**（对朋友提供的完整替换句）  
**Problem:** 当前句的 `by architecture` 确有搭配不够自然的问题，但朋友的建议句
`Unlike conventional models that fix world states through architectural design ...`
存在事实风险：

- `conventional models` 范围过宽；
- `fix world states through architectural design` 不是当前文献审计支持的统一事实；
- `state contribution ablation` 易被理解为训练型 ablation，而实际是 frozen
  state removal；
- `identity-transition baseline controls` 把 supporting diagnostic 写成 baseline；
- `real ... forcing`、`weather references` 不如 actual/matched-donor/
  normalized-mean 精确。

因此该替换不能使用。  
**Minimal revision direction:** 只修当前 `asserting ... by architecture` 的搭配，
把对比焦点放在“architecture alone 不是证据，本文提供可证伪接口”，不要对全部
conventional models 作事实概括。  
**Technical-meaning risk:** **高。** 直接采用朋友句会改变 prior-work positioning 和
Q2 证据层级。  
**Priority:** 当前句的搭配问题为 **P1**；朋友替换句本身 **INVALID**

### 批注 7

**Location:** Abstract，`main.tex:46--52`  
**Original:** `On GreenEarthNet ... retains useful forecasting skill; removing ... while, on a frozen heat--drought subset, actual weather ...`  
**Verdict:** **PARTLY VALID**  
**Problem:** 批注对句子冗长和 `while, on ...` 节奏别扭的判断有效。该句在一个分号
结构中同时压入 Q1、Q2、Q3，且 `while` 后又插入逗号包围的前置介词短语，增加解析
负担。但 `retains useful forecasting skill` 是正常学术表达，`load-bearing` 是本文
明确定义的术语，不是中式口语。  
**Minimal revision direction:** 按证据层级拆成两句：Q1/Q2 一句，Q3 与联合结论一句；
保持 subset、complete 20-step window、paired CI 和 controls 的作用域。  
**Technical-meaning risk:** **高。** 不能把 subset \(R^2\) 暗示为完整 OOD-t，也不能
把 Q3 写成因果结果。  
**Priority:** **P1**

### 4.1 批注汇总

| 裁决 | 数量 | 批注编号 |
|---|---:|---|
| VALID | **1** | 1 |
| PARTLY VALID | **3** | 4、5、7 |
| INVALID | **3** | 2、3、6 |

## 5. 特别核验项

### 5.1 `Forecasting future land-surface observations requires combining ...`

**判定：正确，无需修改。**

`Forecasting + object` 作主语，`requires combining A with B, C, and D` 是标准英语
结构。`sparse, cloud-obscured satellite histories` 的修饰关系清楚，Oxford comma
正确。可换成 `requires integrating` 只是个人偏好，没有语法或 AAAI 风格收益。

### 5.2 `typically evaluated primarily`

**判定：P1 表达冗余。**

`typically` 描述频率，`primarily` 描述主次，逻辑上并不矛盾，但相邻使用显得拗口。
保留其中一个即可保持原意。

### 5.3 `cannot establish / cannot detect`

**判定：应保留其认识论功能。**

- `cannot establish`：输出精度单独不足以证明内部状态性质；
- `cannot detect`：标准输出误差无法区分特定内部 failure modes。

二者不是语气消极，而是论文科学问题的边界。可调整周边句式，但不能降成
`is weak at`。

### 5.4 Oxford comma 与破折号

**判定：正确。**

- 摘要中的三项列表均正确使用 Oxford comma；
- `forecast-bearing, weather-responsive` 的逗号正确；
- `forecast---failures` 编译为 em dash，用于引出前述 failures 的同位解释，正确；
- `heat--drought` 编译为 en dash，表达复合关系，可接受。

### 5.5 `inferred / advanced / read out`

**判定：语法平行、技术顺序正确，但句子偏密。**

可以拆句改善首次阅读，不应将三者改成含义不同的 `encoded / generated / decoded`
而不核对代码路径。

### 5.6 `Rather than asserting ...`

**判定：逻辑安全，搭配可优化。**

`Rather than` 的主语控制正确，修饰 TerraState 的做法；问题只是
`asserting a world state by architecture` 不够自然。对比应继续针对 evidentiary
practice，不应变成对 conventional models 的普遍指控。

### 5.7 最后一条 GreenEarthNet 结果句

**判定：需要局部拆分。**

统计作用域正确、分号合法、`while` 也不造成语法错误；但 Q1--Q3 同句使摘要的主要
证据不易扫读。拆句是可读性修复，不是结果重写。

### 5.8 朋友提供的 `Unlike conventional models ...`

**判定：事实不安全，不应采用。**

它过度概括 prior work，并把 state removal、identity diagnostic 和 weather controls
换成不够精确的术语。当前稿应局部修搭配，而不是通过攻击 prior models 增强语气。

## 6. 全文逐句语言问题

以下计数对与 `gai.pdf` 重叠的问题去重。

### 6.1 P0（0）

未发现主谓一致、冠词、单复数、时态、介词、comma splice 或标点错误会改变技术含义。
公式、表格和 captions 中的复合句虽密集，但语法可恢复。

### 6.2 P1（8）

#### P1-1

**Location:** Abstract，`main.tex:29--32`  
**Original:** `High-resolution satellite time series ... are increasingly cast as weather-driven forecasting ...`  
**Verdict:** 需要局部修改。  
**Problem:** 同一主语同时承担 “monitoring tool” 和 “forecasting setting” 两种语义
角色，后半谓语搭配不自然。  
**Minimal revision direction:** 将 forecasting framing 的主语改为 task/setting，
保留原输入输出定义。  
**Technical-meaning risk:** 中。  
**Priority:** P1

#### P1-2

**Location:** Abstract，`main.tex:32--34`  
**Original:** `typically evaluated primarily by fixed-horizon pixel accuracy`  
**Verdict:** 需要精简。  
**Problem:** 连续副词造成冗余，不是语法错误。  
**Minimal revision direction:** 保留 `typically` 或 `primarily` 之一。  
**Technical-meaning risk:** 低。  
**Priority:** P1

#### P1-3

**Location:** Abstract，`main.tex:39--42`  
**Original:** `a spatial predictive state inferred ..., advanced ..., and read out ...`  
**Verdict:** 平行正确但阅读负载偏高。  
**Problem:** 一个名词短语承载来源、转移条件和输出功能三层机制。  
**Minimal revision direction:** 拆成最多两句；保持三步顺序及 future-weather 信息边界。  
**Technical-meaning risk:** 高。  
**Priority:** P1

#### P1-4

**Location:** Abstract，`main.tex:42--46`  
**Original:** `Rather than asserting a world state by architecture ...`  
**Verdict:** 逻辑正确，搭配不够自然。  
**Problem:** `assert ... by architecture` 带有内部审计式压缩感。  
**Minimal revision direction:** 将对比落在“architectural form alone”与“empirical
tests”之间，不增加对 prior models 的普遍判断。  
**Technical-meaning risk:** 高。  
**Priority:** P1

#### P1-5

**Location:** Abstract，`main.tex:46--52`  
**Original:** `On GreenEarthNet ...; removing ... while, on a frozen ... subset, actual weather ...`  
**Verdict:** 建议拆分。  
**Problem:** Q1--Q3、CI、subset、controls 和联合结论挤在一个句子中；`while, on ...`
虽合法但节奏不自然。  
**Minimal revision direction:** 按 Q1/Q2 与 Q3/联合结论拆成两句，不删任何限定词。  
**Technical-meaning risk:** 高。  
**Priority:** P1

#### P1-6

**Location:** Method §3.4，`main.tex:476--479`  
**Original:** `a nonzero, reportable masked forecast-output response statistic`  
**Verdict:** 表达偏审计式且 `reportable` 含义模糊。  
**Problem:** `reportable` 不是统计定义，读者无法从该词知道观测量；Results 已明确该
观测量是 common-mask per-minicube masked mean absolute forecast difference。  
**Minimal revision direction:** 若进行语言修订，使用 Results 已有的统计量名称，
不要新增 threshold、显著性门槛或指标。  
**Technical-meaning risk:** 高。  
**Priority:** P1

#### P1-7

**Location:** Experiments §4.2，`main.tex:579--581`  
**Original:** `represents TerraState's most favorable relative dimension in the table`  
**Verdict:** 含义可懂但不够自然。  
**Problem:** `relative dimension` 是审计/比较报告式名词组合，不是常见实验写法。  
**Minimal revision direction:** 用更直接的“该指标是表中 TerraState 相对表现最强的
一项”功能表达；仍保留 mixed profile 和非排名语气。  
**Technical-meaning risk:** 中。  
**Priority:** P1

#### P1-8

**Location:** Table 3 caption，`main.tex:670--672`  
**Original:** `complete 20-step-window control-minus-actual masked loss`  
**Verdict:** 统计方向正确，但名词堆叠影响快速解析。  
**Problem:** 时间范围、方向和 loss 类型连续前置，caption 扫读困难。  
**Minimal revision direction:** 先命名 masked loss 的时间范围，再以独立从句说明
control minus actual 和 positive-favors-actual；不得改变符号方向。  
**Technical-meaning risk:** 高。  
**Priority:** P1

### 6.3 P2（6）

#### P2-1

**Location:** Introduction，`main.tex:100--102`  
**Original:** `Its scope is deliberately narrower than recovering a complete physical state or building ...`  
**Verdict:** 可接受，但比较项略不对称。  
**Problem:** `scope` 与两个 gerund activity 比较，语义可恢复但不够轻巧。  
**Minimal revision direction:** 若润色，改成 scope excludes/does not seek those aims
的等价限定；不能删除范围边界。  
**Technical-meaning risk:** 中。  
**Priority:** P2

#### P2-2

**Location:** Related Work，`main.tex:153--154`  
**Original:** `Their primary evaluations concern predicted observations ...`  
**Verdict:** 正确但略抽象。  
**Problem:** `concern predicted observations` 不如 `focus on prediction outputs/
forecast quality` 直接。  
**Minimal revision direction:** 只做同义、同强度改写。  
**Technical-meaning risk:** 低。  
**Priority:** P2

#### P2-3

**Location:** Related Work，`main.tex:190--192`  
**Original:** `It does not claim classical PSR sufficient-statistic guarantees, a causal or complete physical state, or compositional dynamics.`  
**Verdict:** 证据边界必须保留，列表语义类别略不平行。  
**Problem:** 列表混合 `guarantees`、`state` 和 `dynamics` 三种名词类别；不影响理解。  
**Minimal revision direction:** 若改，只统一“does not claim X / recover Y / establish Z”
的语法角色，不删除任何边界。  
**Technical-meaning risk:** 高。  
**Priority:** P2

#### P2-4

**Location:** Method §3.3，`main.tex:348--350`  
**Original:** `the EO observation history, past weather ...`  
**Verdict:** 信息正确，轻微重复。  
**Problem:** EO 已含 observation，`EO observation history` 略冗余。  
**Minimal revision direction:** 使用全文更稳定的 `EO history`。  
**Technical-meaning risk:** 低。  
**Priority:** P2

#### P2-5

**Location:** Experiments §4.1，`main.tex:522--525`  
**Original:** `Q2 and Q3 alter only its frozen forward computation ...`  
**Verdict:** 可理解，所有格和 frozen 的附着略生硬。  
**Problem:** `its` 回指 final model，但 `frozen` 更自然地修饰 model 而非
forward computation。  
**Minimal revision direction:** 将含义明确为“only alter the frozen model's forward
computation”；保持 no retraining。  
**Technical-meaning risk:** 中。  
**Priority:** P2

#### P2-6

**Location:** Table 1 caption，`main.tex:512--514`  
**Original:** `RMSE, absolute bias, and RMSE25 are lower-is-better.`  
**Verdict:** ML caption 中可接受的简写，略显口语化/标签化。  
**Problem:** `lower-is-better` 作表语是领域常见 shorthand，但不如 `lower values
indicate better performance` 正式。  
**Minimal revision direction:** 仅在统一 caption 风格时调整。  
**Technical-meaning risk:** 低。  
**Priority:** P2

## 7. 否定句专项审计

### 7.1 必须保留的证据边界

| 位置 | 否定表达 | 裁决 |
|---|---|---|
| Abstract / Introduction | output accuracy `cannot establish` internal-state use | 核心 gap，保留 |
| Abstract | standard error metrics `cannot detect` listed internal failures | 核心 gap，保留 |
| Method 3.1 | neither future EO nor future forcing enters \(q_\theta\) | 信息边界，保留 |
| Method 3.2 | transition `does not recursively roll out` | 防止 composition 误读，保留 |
| Figure 2 caption | `not composition or causal effects` | 明确硬约束，保留 |
| Method 3.4 | `does not estimate a causal effect, guarantee counterfactual correctness ...` | 证据边界，保留 |
| Q2 Results | `does not establish transition necessity` | supporting-only 边界，保留 |
| Limitations | non-causal/non-counterfactual、hot-dry null、cross-dataset limitation | 必须保留 |
| Conclusion | accurate forecasts `do not by themselves establish` internal state | 全文收束句，保留 |

### 7.2 可正向组织但无需机械修改

- `TerraState does not replace those aims` 可正向表述为 TerraState
  `complements those aims by ...`，语义可等价；当前句本身无错。
- `It does not claim ...` 可将不同边界拆成平行动词，但不能删除任何一项。
- `without exposing future observations at inference` 是能力与信息边界的紧凑表达，
  无需改成肯定句。

全文没有因 `cannot / does not / not` 使用过多而形成防御性失败清单。真正应处理的是
少数句子的负载和搭配，不是否定词数量。

## 8. 摘要 AAAI 风格审计

| 必需功能 | 当前落点 | 判定 |
|---|---|---|
| 任务 | 高分辨率 satellite time series + weather-driven forecasting | **完成；首句搭配需局部修** |
| 现有评测缺口 | fixed-horizon pixel accuracy 无法建立内部 predictive-state 性质 | **完成且有力** |
| 核心观点 | 不凭 architecture 命名，而使 state claim 可证伪 | **完成；搭配可优化** |
| 方法实现 | history-derived state → shared weather transition → readout contribution | **完成；一句偏密** |
| Q1--Q3 证据 | useful skill、state-removal degradation、actual-vs-controls fidelity | **完整且未越界；结果句偏长** |

### 摘要是否需要局部重写

**需要一次局部语言修订，但不需要结构重写。**

建议只处理 P1-1 至 P1-5。当前 task → gap → insight → method → evidence 顺序应完整
保留；不要增加 prior-work 攻击句，不要删掉 causal/composition 等必要边界，也不要
把 Q1--Q3 改成排行榜叙事。

## 9. 引言 AAAI 风格审计

### 9.1 反向提纲

| 段落 | 唯一职责 | 判定 |
|---|---|---|
| P1 | EO task value、输入/输出、EarthNet/GreenEarthNet setting、world-modeling perspective | PASS |
| P2 | fixed-window accuracy 的 evidentiary gap 与 latent-state failure modes | PASS |
| P3 | predictive-state foundation、科学问题、TerraState identity 和范围 | PASS |
| P4 | Figure 1 方法概览：state→transition→readout→training anchor→interfaces | PASS |
| P5 | Q1→Q2→Q3 evidence preview | PASS |
| P6 | 三项 contributions | PASS |

引言严格形成：

> 任务价值 → 固定时域精度不足以检验内部状态 → predictive-state 问题 →
> TerraState → 实验证据 → 三项贡献

段首句职责清楚，段间关系是任务收窄、缺口、理论支点、方法回应、证据、总结，没有
明显 AI 模板化口号或内部审计报告感。

### 9.2 引言结构是否符合 AAAI

**符合。** 当前结构成熟度高，不应为语言润色重新排序、合并段落或扩写 Related
Work。P2-1 是局部句法偏好，不构成结构返修。

## 10. 贡献列表审计

### Contribution 1

`We frame weather-driven EO world modeling around a falsifiable question ...`

- 清楚突出“可证伪/可检验的 EO world-modeling 问题”；
- 不声称这是世界模型的唯一合法定义；
- 不把其他 EO 方法排除出 world-modeling 范畴；
- 强度合适。

**判定：PASS。**

### Contribution 2

`We introduce TerraState, which combines an explicit state-mediated forecast
path, a shared weather-conditioned transition, and future-state anchoring ...`

- 覆盖显式状态路径、共享 transition 和训练方法；
- 没有误写成 recursive、causal 或 complete physical simulator；
- 与 Section 3 逐项对应。

**判定：PASS。**

### Contribution 3

`We evaluate the same trained model at three levels ...`

- Q1 为 useful temporal-shift forecasting；
- Q2 为 Validation/OOD-t load-bearing state contribution；
- Q3 为 actual-vs-donor/mean complete-window fidelity；
- 没有把 subset score 当完整 OOD-t，也没有加入 Q4/SOTA。

**判定：PASS。**

### 总结

贡献列表既未越界，也不明显过弱。它采用“问题/观点 → 方法 → 证据”的三分结构，
与成熟 AAAI 方法论文一致。最小语言修订不应重写贡献列表。

## 11. PDF 语言与版面呈现

### 11.1 总体

- 当前 `main.pdf` 为 8 页；
- 所有章节、公式、三张图、三张表、Limitations、Conclusion 和 References 均可见；
- 未发现文字裁切、重叠、栏间侵入、标题悬空或标点丢失；
- 公式编号和 caption 顺序可读；
- 第 7 页同时容纳三张表及结尾章节，密度较高但仍可阅读，不构成语言阻塞。

### 11.2 自动断词

PDF 中存在大量 AAAI 双栏自动断词，例如 `pre-dicting`、`TerraS-tate`、
`contri-bution`、`fore-cast` 和跨行的 `OOD-` / `t`。这些都来自 TeX 排版，不是
源文件拼写或语法错误，按任务要求不计入 P0/P1/P2。

个别 caption label 与正文在 PDF text extraction 中会被拼接为
`Figure 3:State`、`favorsactual`；高分辨率视觉检查显示正文仍可辨认，没有源文件
漏空格的证据，因此不判为语法错误。最终排版门禁可再次检查，但不应据 OCR/text
extraction 结果修改正文。

## 12. 最小语言修订边界

### 应进入最小修订

1. 摘要 P1-1 至 P1-5；
2. Method 中 `nonzero, reportable` 的学术表达；
3. Q1 Results 的 `most favorable relative dimension`；
4. Table 3 caption 的名词堆叠。

### 可选

P2 六项只在不增加篇幅、不改变事实且不破坏冻结结构时处理。

### 禁止借机修改

- 14,880 updates；
- 任何 Q1--Q3 数字、split、CI、样本数、统计方向或结论；
- `cannot establish`、非因果/非反事实、非 composition 等必要边界；
- 方法计算链、训练目标、future-information boundary；
- contribution 三分结构；
- 引用和最近邻定位；
- SOTA、complete physical state 或 general-purpose simulator 等新主张。

## 13. 最终汇总

| 项目 | 结论 |
|---|---|
| `gai.pdf` 批注 | VALID 1；PARTLY VALID 3；INVALID 3 |
| 全文 P0/P1/P2 | **0 / 8 / 6** |
| 摘要 | 需要局部语言修订；不需结构重写 |
| 引言 | 符合 AAAI 任务→缺口→问题→方法→证据→贡献结构 |
| 贡献列表 | 不越界、不明显过弱，可保持 |
| `cannot / does not / not` | 大多数承担必要证据或信息边界，不应机械删除 |
| PDF | 自动断词不算语法错误；无阻塞性版面问题 |
| 是否适合进入最小语言修订 | **是** |

## 14. 只读声明

本轮没有修改或重新编译 `paper/main.tex`、`paper/main.pdf`、`示例/gai.pdf`、
Markdown 镜像、图片、表格、实验、结果、引用库或任何其他现有文件。唯一新建文件为
本报告。

# READY_FOR_MINIMAL_LANGUAGE_REVISION
