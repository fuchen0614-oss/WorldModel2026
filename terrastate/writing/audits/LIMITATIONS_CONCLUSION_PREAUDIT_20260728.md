# TerraState AAAI-27 Limitations and Conclusion 修改前独立预审

**审计日期：** 2026-07-28  
**审计性质：** 独立、只读的 AAAI 写作结构、主张边界、双语镜像与 PDF 预审  
**权威正文：** `paper/main.tex`  
**目标 venue：** AAAI-27 Main Technical Track  

## 1. 总体 verdict

# LIMITATIONS_CONCLUSION_PREAUDIT_COMPLETE_READY_FOR_REVISION

当前 Limitations 的科学事实和证据边界总体准确：它正确区分预测表示与完整物理
状态、条件预测忠实度与因果/反事实正确性，也保留了 hot-dry 特异增强不成立、
GreenEarthNet 单数据集、光学观测与未观测变量等必要限制。它没有反向否定 Q2/Q3，
也没有构成防御性失败清单。

主要问题有三项：

1. Limitations 末句重新提出 temporal composition，会无意义地唤起已经退出主线
   的 Q4，并可能让世界模型审稿人把它当作缺失的必要实验；
2. Conclusion 当前主要是 Q1/Q2/Q3 的五句结果摘要，没有充分概括
   history-derived predictive state、shared weather-conditioned transition、
   on-path state contribution 和 test interfaces，也缺少“本文把内部状态宣称
   转化为可检验问题”这一 broader takeaway；
3. 两个精简 Markdown 的 Limitations/Conclusion 仍保留 single-run、
   public-versus-local ranking 和 composition-open wording，与权威
   `main.tex` 及完整中文镜像不一致。

以上均为一轮写作与镜像同步即可解决的问题，不需要新实验、重算数值、修改
Section 1--4 或改变证据边界。

### 问题计数

| 等级 | 数量 | 结论 |
|---|---:|---|
| Critical | **0** | 没有事实、数值或证据方向错误 |
| Major | **3** | Q4 重引、Conclusion 收束不足、精简镜像不一致 |
| Minor | **2** | 业务天气表述略模糊；Q2 conclusion 句的 `positive` 不够直接 |
| Optional | **2** | 可进一步减少重复边界；最终排版时改善章节跨栏连续性 |

---

## 2. 审计范围与事实基线

本轮只审计：

- `paper/main.tex` 的 `Limitations and Scope` 与 `Conclusion`；
- `MANUSCRIPT_ZH_FULL.md` 对应完整中文；
- `MANUSCRIPT.md` 与 `MANUSCRIPT_ZH.md` 的对应精简镜像；
- 当前 Abstract、冻结 Introduction、Method 主线、Q1--Q3 结果、
  Figure 3/Table 3 与结尾章节的必要接口；
- 现有 `paper/main.pdf` 的结尾页面呈现。

采用的冻结事实：

- Q1：TerraState 在 GreenEarthNet OOD-t 保留有用预测能力；
- Q2：state removal 是 primary evidence，移除状态贡献会降低预测质量；
- Q3：在冻结 matched protocol 上，actual future weather 相较 donor/mean
  controls 具有更高的完整 20 步 forecast-window fidelity；
- 不支持 SOTA、因果效应、反事实正确性、完整物理状态、extreme-specific
  enhancement、Q4/composition 或 non-collapse。

作者最新确认的 40 epochs / 14,880 updates 最终模型身份优先于历史审计中的旧
11,904/boundary80 记录。本轮没有重开训练身份，也没有修改任何结果。

---

## 3. Limitations 逐段职责

当前 Limitations 共 3 段、约 141 个英文词。

| 段落 | 当前唯一职责 | 具体内容 | 审计 |
|---|---|---|---|
| P1，`main.tex:690--693` | 定义 representation scope 与 deployment forcing gap | predictive representation ≠ complete physical state；实验使用 observed future weather，业务预报可能降低性能 | **PASS WITH MINOR** |
| P2，`main.tex:695--701` | 限定 Q3、hot-dry 和 Q2 的证据含义 | fidelity ≠ causal/counterfactual；无 extreme-specific enhancement；state path carries increment ≠ all information indispensable | **PASS** |
| P3，`main.tex:703--707` | 定义 external validity 与观测限制 | 单 GreenEarthNet temporal-shift setting；cloud/soil moisture/irrigation/vegetation-type 限制；最后重提 composition | **PASS EXCEPT FINAL SENTENCE** |

### 3.1 组织是否符合 AAAI

前两段和 P3 前两句已经自然形成：

> applicability scope → evidence boundary → external validity

这符合成熟 AAAI 方法论文 Limitations 的常见组织。它不是逐条列出“我们没做什么”，
而是围绕三类边界组织：

1. 模型表示与部署输入；
2. 干预证据能够说明什么；
3. 数据与观测范围。

问题只出现在最后一句：它把结构从“现有证据的边界”切换为“另一个未完成的世界模型
性质”，使段落尾部失焦。

---

## 4. Limitations 关键问题审计

### 4.1 是否过度削弱论文

总体**没有**过度削弱。必要负向表述都有明确正向对象：

- “not a complete physical state”限定的是 state ontology，不否定其
  forecast-bearing role；
- “not causal/counterfactual”限定的是 Q3 识别强度，不否定 matched predictive
  fidelity；
- “not every component is indispensable”限定的是 Q2 范围，不否定 state path
  carries a measurable increment；
- hot-dry null 只否定 extreme-specific enhancement，不否定 actual-vs-control
  fidelity。

P2 虽包含较多否定词，但每句都关闭一个真实的过度解释通道，当前仍属于必要边界，
而不是防御性自我否定。

### 4.2 预测状态与完整物理状态

`TerraState learns a future-predictive representation ...; it does not recover
a complete physical land-surface state.` 与冻结 Introduction、Method 和 Abstract
一致。该边界在 Introduction 已出现一次，但在正式 Limitations 中再次出现是合理的：
Introduction 负责定位，Limitations 负责集中声明适用范围。无需完全删除，只需避免
在 Conclusion 再重复一遍。

### 4.3 条件忠实度与因果/反事实

`Matched-versus-control weather response measures conditional predictive
fidelity, not causal identification or counterfactual correctness.` 是准确且必要的
Q3 边界。它没有把 detectable output change 直接等同于 correct response，也没有
把 actual-vs-control loss difference 提升为天气的因果效应。

### 4.4 业务天气预报

当前句：

> `Future weather is supplied as an observed exogenous input, so performance
> with operational weather forecasts may be lower.`

科学方向正确，但 `observed exogenous input` 容易让读者暂时困惑“future weather
为何 observed”。真正需要表达的是：当前评测条件化于事后实现的真实未来天气，
而业务部署输入是带误差和潜在分布偏移的预报天气；论文没有测量这部分退化。

这是 **Minor**，不是证据错误。后续最小修订应明确：

- evaluation uses realized/observed future meteorology；
- operational forecasts introduce forecast error and possible input shift；
- 该部署差距尚未被本研究量化。

不得凭空加入性能下降数值。

### 4.5 单数据集、光学观测与未观测变量

P3 前两句准确覆盖：

- GreenEarthNet 单数据集和一个 temporal-shift setting；
- 无 cross-dataset generality；
- optical target 受 cloud screening 影响；
- soil moisture、irrigation、vegetation type 等未观测因素。

这些限制与 EO 任务直接相关，不是通用模板句，应保留。

### 4.6 `Temporal composition remains unexplored as a core empirical claim`

**审计结论：建议从最终主文 Limitations 删除，不建议保留。**

原因：

1. Q4/composition 已正式退出 Abstract、Introduction、Method 核心问题和
   Section 4 证据链；
2. 当前论文没有基于 composition 提出正向主张，因此无需专门声明没有验证它；
3. 在 world-model 论文末尾主动写出该性质，会向审稿人提示作者曾将其视为必要
   但未完成；
4. 句中的 `as a core empirical claim` 带有内部决策记录感，不像自然的
   applicability limitation；
5. 它削弱 P3 原本清楚的 dataset/observability 收束。

如果作者希望保留未来方向，建议用与当前证据直接相邻的方向收尾，例如跨数据集、
operational-weather uncertainty 或更完整的地表驱动变量；不应重新命名 Q4，也
不应把 composition 列为审稿人必须追问的缺失实验。

该问题是**定位型 Major**，尽管只涉及一句。

---

## 5. Conclusion 逐句职责

当前 Conclusion 为 1 个段落、5 句、约 84 个英文词。

| 句子 | 当前职责 | 终审 |
|---|---|---|
| S1，`main.tex:711--712` | 声明 TerraState 使 EO world model 的 predictive state 在 forecast path 内可直接检验 | **PASS；是正确开场** |
| S2，`main.tex:712` | 概述 Q1 useful OOD-t skill | **PASS** |
| S3，`main.tex:713--714` | 概述 Q2 state contribution 与 paired intervals | **PASS WITH MINOR**；`is positive` 不如直接写 removal-induced degradation |
| S4，`main.tex:714--716` | 概述 Q3 actual-vs-controls complete-window loss | **PASS** |
| S5，`main.tex:717--719` | 联合收束为 forecast-bearing/weather-responsive state under frozen protocol | **PASS；但仍是证据结论，不是 broader significance** |

### 5.1 当前结构

当前实际结构是：

> method identity → Q1 result → Q2 result → Q3 result → joint claim

这条链科学上正确，却缺少成熟 AAAI Conclusion 常见的两个中间/末端功能：

- **method recap：** TerraState 具体通过什么机制使 state 可检验；
- **broader takeaway：** 这项工作对 EO world-model research 的评价方式改变了
  什么。

因此 Conclusion 读起来更像 Results 的压缩版，而不是全文的最终学术收束。

---

## 6. Conclusion 的 AAAI 结构差距

### 6.1 首句和研究问题

S1 很好地重新提出方法身份：

> `TerraState makes the predictive state of an EO world model directly
> testable within its forecasting path.`

它同时包含 TerraState、predictive state、EO world model、testable 和 forecast
path，是当前 Conclusion 最有力的一句，应作为后续修订的语义核心保留。

但它没有显式重述科学问题的另一半：future weather 如何通过 state transition
影响 forecast。下一句应进入机制，而不是立刻进入 Q1 数字摘要。

### 6.2 方法机制缺失

Conclusion 没有提到：

- history-derived spatial predictive state；
- shared weather-conditioned transition；
- state readout / on-path additive contribution；
- state-removal 和 weather-substitution interfaces。

不需要重述公式或训练目标，但至少应有一句把这四点压缩成“方法如何实现可检验性”。
否则审稿人读完结尾只记得三项结果，而不容易恢复 TerraState 与普通 forecaster 的
方法差异。

### 6.3 结果摘要比例过高

S2--S4 三句全部是结果，约占 Conclusion 主体的一半以上。它们的方向准确，但与
Section 4、Abstract 和 Introduction 的 evidence preview 重复。

成熟的结尾应把三项结果压缩为一到两句：

- Q1 是 forecasting prerequisite；
- Q2/Q3 共同建立 load-bearing + weather-responsive；
- 不需要重报全部统计形式，更不需要数值。

### 6.4 Broader takeaway 缺失

S5 只再次陈述 core claim，没有回答：

> 本文改变了什么研究实践？

当前最有根据、又不越界的 broader significance 是：

- EO world-model claims 不应只依赖架构命名或最终像素精度；
- TerraState 展示了一种把 state use 与 forcing response 暴露为可干预、
  可证伪性质的方法型路径。

这不是宣布领域唯一标准，也不是声称 TerraState 证明了普遍 world-model 定义。
它只是总结本文的可迁移研究观点，正好对应冻结 Introduction 的第一条贡献。

### 6.5 自信与边界

当前 Conclusion 没有 SOTA、因果、完整物理状态或通用模拟器越界，也没有在权威
`main.tex` 中重复 Limitations 清单。这一点应保持。

后续修订不应把 causal、extreme-specific、composition 和 cross-dataset 等全部
限制重新塞进 Conclusion。Limitations 已承担这些边界；Conclusion 应用一句
`under the evaluated/frozen protocol` 保持范围后，以正向意义收尾。

该问题属于**结构型 Major**。

---

## 7. AAAI 写作校准

本轮使用已经完成校准的正式 AAAI 锚点，只比较段落功能和论证顺序，不复制其措辞
或技术主张。

| AAAI 锚点 | 可借鉴的结尾功能 | TerraState 当前差距 |
|---|---|---|
| Drive-OccWorld | 先恢复核心问题和模型身份，再将主要结果连接到更广泛方法意义 | 当前恢复身份后立刻逐项列结果，缺 broader takeaway |
| Simulator-Informed Latent States | 用一句机制说明 latent state 为什么具有方法意义，再用受限证据收束 | 当前没有 shared transition/on-path contribution 的机制 recap |
| SparseWorld | 结论压缩组件和实证收益，不逐表复述 | TerraState 的三句结果仍接近逐项摘要 |
| iTrendRNN | 将“准确预测之外还能理解什么”作为结尾意义，而不是只重复指标 | TerraState 尚未明确“从 output-only evaluation 到 internal testability”的改变 |
| LaNoLem | problem → method → evidence → implication 四步完整 | 当前缺 method 和 implication 两步 |

对 Limitations，这些锚点的共同规律是按 scope/evidence/external validity 组织，而
不是枚举所有未来可能研究的问题。TerraState 前 7 句基本符合；composition 末句
偏离该规律。

---

## 8. 世界模型主线收束质量

### 8.1 当前能够收束的主线

当前结尾已经正确表达：

- TerraState 学到的是 predictive representation，不是完整物理状态；
- state-mediated contribution carries measurable forecast increment；
- actual weather 在 matched protocol 上具有更高 complete-window fidelity；
- 联合证据支持 forecast-bearing and weather-responsive predictive state。

### 8.2 当前缺失的主线动作

尚未充分表达：

1. `testable` 来自 state 在 forecast path 上，而非来自命名；
2. future weather 通过 shared transition 影响 evolved state；
3. state removal 和 weather substitution 是方法的一部分，而不是结果阶段临时
   拼接的普通 ablation；
4. 本文贡献的 broader significance 是使 internal-state claim 可经验否证。

这些缺失不会推翻现有证据，但会让 Conclusion 低估 TerraState 的方法型贡献。

**世界模型主线收束：3.6/5。**

---

## 9. Claim--evidence 边界

| 结尾可出现的主张 | 证据 | 最大安全强度 | 当前状态 |
|---|---|---|---|
| Useful OOD-t forecast skill | \(R^2=0.56935\)、RMSE \(=0.15059\) | `retains useful forecasting skill` | **准确** |
| State-mediated path carries prediction | state removal 在 Validation/OOD-t 降低表现，paired CIs 排除零 | `load-bearing measurable forecast increment` | **准确** |
| Transition involvement | \(T\to I\) supporting diagnostic | supporting only，不写 necessity | Conclusion 未单独提，合理 |
| Detectable weather response | 84/84 substitutions 产生有限正 output difference | state-mediated path responds detectably | Conclusion 以 fidelity 联合表达，未越界 |
| Actual weather full-window fidelity | donor/mean control-minus-actual effects 的 cluster CIs 排除零 | `greater complete-window fidelity under frozen matched protocol` | **准确** |
| Forecast-bearing, weather-responsive predictive state | Q1 prerequisite + Q2 + Q3 | 限定 TerraState 和 evaluated/frozen protocol | **准确** |
| Complete physical state | 无 | 只可否定 | Limitations 正确否定 |
| Causal/counterfactual correctness | 无识别设计 | 只可否定 | Limitations 正确否定 |
| Extreme-specific enhancement | hot-dry interval crosses zero | 不支持 | Limitations 正确否定 |
| Composition/Q4 | 未作为核心验证 | 不应在结尾主动重提 | Limitations 与精简 Conclusion 仍重提 |

没有发现需要新实验才能修复的 Conclusion 主张。后续任务是重新分配已有事实的叙事
位置，而不是增强证据。

---

## 10. 是否存在过度自我削弱

### Limitations

整体**不存在实质性过度自我削弱**。当前每项限制都有必要的 claim-boundary
功能。唯一自我制造的风险是 composition 末句：它不是现有正向主张的必要边界，
却会创建新的审稿问题。

### Conclusion

权威 Conclusion 没有负向限制清单，因此不防御。但它通过连续三个结果句把方法型
贡献压缩成实验摘要，形成的是“贡献表达不足”，而不是“过度承认失败”。

修订方向应是增加机制与意义，而不是删除 Q1/Q2/Q3 或强化宣传。

---

## 11. 中英文与镜像一致性

### 11.1 权威英文与完整中文

`paper/main.tex` 和 `MANUSCRIPT_ZH_FULL.md` 的 Limitations/Conclusion 语义一致：

- predictive representation ≠ complete physical state；
- observed future weather 与 operational forecast 的差距；
- conditional fidelity ≠ causal/counterfactual correctness；
- hot-dry 不支持 extreme-specific enhancement；
- Q2 不意味着所有信息不可替代；
- GreenEarthNet/optical/unobserved-variable scope；
- current Conclusion 的 Q1--Q3 和 frozen-protocol 联合结论。

中文使用“支持”而非“证明”，没有放大主张。

### 11.2 两个精简镜像的实质差异

`MANUSCRIPT.md` 和 `MANUSCRIPT_ZH.md` 仍包含权威主文已删除的内容：

1. `one selected training run / 一次训练`；
2. `reported public values and frozen local evaluation` 及严格跨实现排名；
3. Conclusion 把 `temporal composition`、causal、extreme-specific 和 broader
   generalization 一起列为开放问题；
4. 精简 Conclusion 是一个长句的 results + limitations 合并版本，而不是当前
   权威 Conclusion 的五句结构。

这会造成两种风险：

- 作者按精简镜像审稿时会误以为 single-run、public/local 和 composition 仍属于
  正式结尾；
- 中文/英文镜像不再是同一主张边界，后续修订容易把已经清理的旧叙事带回
  `main.tex`。

这是**镜像同步 Major**。后续应以修订后的 `main.tex` 为唯一英文权威，先同步
`MANUSCRIPT_ZH_FULL.md`，再同步两个精简镜像的 Section 5--6。不得借同步修改
Section 1--4 的冻结内容。

**双语主镜像：4.9/5；四份文本整体一致性：3.4/5。**

---

## 12. PDF 页面与排版观察

只读检查当前 `paper/main.pdf`，未重新编译。

| 项目 | 当前状态 | 判断 |
|---|---|---|
| PDF 总页数 | 9 | 记录 |
| Limitations 起点 | 第 6 页右栏，约 \(y=493\) pt | 可读 |
| Limitations P1--P2 | 第 6 页右栏 | 连续 |
| Limitations P3 前部 | 第 6 页右栏底部 | 连续 |
| P3 末尾 | 第 7 页左栏 \(y\approx531\) pt 续接 | **可读** |
| Conclusion 标题 | 第 7 页左栏 \(y\approx563\) pt | 可读 |
| Conclusion 正文 | 第 7 页左栏内完整排布至 \(y\approx698\) pt | 连续、可读 |
| 裁切/重叠/越界 | 未发现 | **PASS** |
| Overfull | 当前 `main.log` 无 overfull | **PASS** |
| LaTeX errors / undefined refs | 未发现阻塞记录 | **PASS** |

Limitations 第三段跨页，但 Conclusion 已完整落在第 7 页左栏，没有跨栏断裂。
当前不构成阻塞性版面问题。由于文本即将修订，最终仍应在一次正常编译后复核章节
连续性；不得为此使用负 `\vspace`、极小字号或破坏已审核图件。

该项列为 **Optional layout gate**，不属于科学或写作 Major。

---

## 13. Critical / Major / Minor / Optional

### Critical（0）

无。

### Major（3）

#### M1 — Limitations 重启 Q4/composition

- **位置：** `paper/main.tex:706--707`；
- **原文：** `Temporal composition remains unexplored as a core empirical claim.`
- **问题：** 主动提示已退出主线的 Q4，且 `as a core empirical claim` 带内部
  决策记录感；
- **审稿人影响：** 世界模型审稿人可能把 composition 视为作者承认但遗漏的必要
  验证；
- **最小修订方向：** 删除该句；如需 future-work 收尾，改用跨数据集、
  operational-weather uncertainty 或未观测地表驱动等已在当前 scope 中出现的
  方向；
- **修复类型：** writing/positioning。

#### M2 — Conclusion 缺少方法 recap 与 broader takeaway

- **位置：** `paper/main.tex:711--719`；
- **问题：** S2--S4 连续复述 Q1/Q2/Q3，未概括 shared transition、on-path
  contribution 和 test interfaces，也未说明从 architecture/output-only claim
  到 falsifiable internal-state claim 的意义；
- **审稿人影响：** 结尾容易被理解为一般预测模型的结果摘要，低估 TerraState 的
  方法型世界模型贡献；
- **最小修订方向：** 保留 S1 语义，增加一句机制 recap；把 Q1--Q3 压缩为一至
  两句；用一句 bounded broader takeaway 收尾；
- **修复类型：** writing-fixable。

#### M3 — 精简镜像 Section 5--6 与权威正文不一致

- **位置：** `MANUSCRIPT.md:204--214`、`MANUSCRIPT_ZH.md:202--212`；
- **问题：** 仍保留 single-run、public/local ranking 和 composition-open
  叙事，Conclusion 结构也不同；
- **审稿人/作者影响：** 正式 PDF 不受影响，但作者审阅和后续同步可能恢复已废弃
  主张；
- **最小修订方向：** 以修订后的 `main.tex` 为准，只同步 Section 5--6；
- **修复类型：** mirror synchronization。

### Minor（2）

#### m1 — 业务天气表述不够精确

- **位置：** `paper/main.tex:692--693`；
- **问题：** `observed future weather` 与 `operational forecasts` 的输入差异未
  展开；
- **影响：** 读者可能不清楚是 forecast error、distribution shift，还是模型本身
  已在业务天气上失败；
- **最小方向：** 明确当前条件化于 realized weather，业务预报误差/shift 尚未
  评估；不添加数值。

#### m2 — Q2 conclusion 句的 `positive` 略含糊

- **位置：** `paper/main.tex:713--714`；
- **问题：** `Its state-mediated contribution is positive` 不如“removing the
  contribution degrades prediction”直接对应干预；
- **影响：** 轻微；不会造成 estimand 错误；
- **最小方向：** 在结论的 evidence 句中采用 intervention→degradation 的自然
  表述，不复述 CI 细节。

### Optional（2）

1. Limitations 中 physical/causal 边界与 Introduction 有意重复；后续可通过更
   紧凑的句法减少重复感，但不应删除必要 scope。
2. 最终 layout gate 可观察修订后的篇幅是否使 Limitations/Conclusion 更连续；
   不应通过脆弱排版技巧强制处理。

---

## 14. 评分

评分标准：1=明显不成熟；3=基本可用但需修订；4=投稿成熟；5=高度成熟。

| 维度 | 分数 / 5 | 判断 |
|---|---:|---|
| Limitations 组织结构 | **4.2** | scope→evidence→external validity 基本成熟 |
| Limitations 证据边界 | **4.9** | physical/causal/Q2/Q3/hot-dry 均准确 |
| Limitations 自信与克制 | **4.3** | 不过度自我削弱；composition 末句例外 |
| Q4/composition 主线纪律 | **3.0** | 权威 Limitations 和精简 Conclusion 重新唤起 |
| 业务部署边界 | **4.0** | 方向正确，realized-vs-operational 差异可更精确 |
| Conclusion 结构 | **3.2** | identity 开场正确，但偏 Results 摘要 |
| Conclusion 方法概括 | **2.8** | 缺 shared transition/on-path contribution/interfaces |
| Conclusion broader takeaway | **2.7** | 未说明可检验性对 EO world modeling 的方法意义 |
| Claim--evidence 对齐 | **4.9** | 没有越界，数字和方向正确 |
| 英文自然度 | **4.6** | 简洁专业；主要是信息槽缺失而非语法问题 |
| 完整中英文镜像 | **4.9** | 权威英文与完整中文一致 |
| 四份文本一致性 | **3.4** | 两个精简镜像保留旧结尾叙事 |
| PDF 呈现 | **4.1** | 无阻塞；结尾被 Figure 3 和跨栏分割 |
| **综合** | **3.9 / 5.0** | **证据安全，需一轮结尾写作修订** |

---

## 15. 一轮即可完成的最小修订蓝图

### 15.1 Limitations：保持 3 段，约 120--145 词

#### 段 1：Representation and deployment scope

保留：

- predictive representation ≠ complete physical land-surface state；
- current evaluation uses realized future meteorology。

精化：

- operational forecasts contain forecast error and may shift the input
  distribution；
- 该 deployment gap 未在本文量化。

#### 段 2：Evidence boundary

保留并轻压缩：

- matched predictive fidelity ≠ causal/counterfactual correctness；
- hot-dry interaction 不支持 extreme-specific enhancement；
- state-mediated branch carries measurable increment，但不承载全部信息。

不新增：

- transition necessity；
- causal grounding；
- arbitrary counterfactual validity。

#### 段 3：External validity and observability

保留：

- GreenEarthNet temporal-shift single setting；
- no cross-dataset generality；
- cloud-screened optical targets；
- soil moisture、irrigation、vegetation type 等未观测变量。

删除：

- `Temporal composition remains unexplored as a core empirical claim.`

如需一句未来方向，只从当前三类 scope 自然延伸，不出现 Q4/composition。

### 15.2 Conclusion：1 段、4 句、约 100--125 词

#### 句 1：Problem and contribution

恢复本文改变的核心问题：

- 将 weather-driven EO world model 的 internal predictive-state claim 从
  architecture/output-only assertion 转化为可检验问题。

可保留当前 S1 的语义。

#### 句 2：Method mechanism

用一句概括：

- history-derived predictive state；
- shared weather-conditioned transition；
- on-path readout/additive contribution；
- removal/substitution test interfaces。

不写公式、loss 或训练阶段。

#### 句 3：Principal evidence

把 Q1--Q3 压缩为一句或两句：

- useful OOD-t forecasting prerequisite；
- state removal degrades prediction；
- actual weather has higher full-window fidelity than frozen controls。

不需要重报数值或 CI 形式。

#### 句 4：Broader significance

正向、受限地收尾：

- under the evaluated/frozen protocol；
- TerraState demonstrates an auditable link among predictive state,
  exogenous forcing, and observable forecasts；
- 对 EO world modeling 的意义是 internal claims can be made falsifiable。

禁止在末句重新列出 causal、extreme、composition、cross-dataset 等限制；这些已由
Limitations 承担。

### 15.3 镜像同步

修订顺序必须是：

1. `paper/main.tex`；
2. `MANUSCRIPT_ZH_FULL.md`；
3. `MANUSCRIPT.md`；
4. `MANUSCRIPT_ZH.md`。

只同步 Section 5--6，不重开冻结 Section 1 或 Section 4。同步后应确认四份文本均
无 Q4/composition、single-run、Published/Local/public-versus-local 或 endpoint-only
Q3 叙事。

### 15.4 修订后门禁

一轮修订完成后只需检查：

- Conclusion 是否恢复 problem→method→evidence→significance；
- Limitations 是否不再重启 Q4；
- 四份镜像是否同强度；
- PDF 是否仍无 overfull/cutoff，并观察结尾跨栏是否自然改善。

不需要新增引用、实验、表格或数字。

---

## 16. 文件 SHA-256 与只读声明

### 16.1 审计开始时 SHA-256

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `52cda549b1939e179acd81933732cc48e5d13a6b5265d0bd3bd38cd8f02aa2b3` |
| `paper/main.pdf` | `a2fcf8f83af05368a0535c078033eb12e6687243dcf73f6a99fff4beda1d5206` |
| `MANUSCRIPT_ZH_FULL.md` | `18c4637b50805c1169a7b5588e58ee9830dbb331ccd8146436e900154ee80815` |
| `MANUSCRIPT.md` | `ea801022bc815b51faeaebb9756138fc7e3caa643d5802dcd5beedd01cb98a07` |
| `MANUSCRIPT_ZH.md` | `eda2683e266c9ae37669c0c20741f7bf92879389aed9799305c02714728b7d94` |
| `SECTION1_FINAL_AUDIT_20260728.md` | `58ea63ee615d288c08c856d364b5de4b629e8dfab7fbc2e2b56a125540cddd5d` |
| `SECTION1_2_AAAI_WRITING_CALIBRATION_AND_PREAUDIT_20260728.md` | `8b911acb17197a97966aa6c2be0697488c031f8e2012f9a9acad350c9ea163c9` |
| `SECTION4_4_1_FINAL_AUDIT_20260728.md` | `63a7e28680da8e70635259e1dc5072c4b254a428eff68d2a4bc8b20841a6b447` |
| `SECTION4_4_2_FINAL_AUDIT_20260728.md` | `a4cb2cb6424318117770155820134e296e95f4e689302e1fa8aceac468ab44ed` |
| `SECTION4_4_3_FINAL_AUDIT_20260728.md` | `cf01a6f6c5ffd08c6ab3624a7f2b09c1099f914e61b6bcabd60100d027456308` |
| `SECTION4_4_4_FINAL_AUDIT_20260728.md` | `d3f9486cf0f3efcc845dd757646d92a6964390069a6f979dc964aef6789ff793` |
| `RESULTS_CLAIM_EVIDENCE_AUDIT.md` | `e8f4f4dcfc4055fb79fc76b59cd6b338222118c6c2ed23115899f6add65b5b0f` |

### 16.2 关键局部区块 SHA-256

| 对象 | SHA-256 |
|---|---|
| `main.tex` Limitations | `02c7944f2122bcad29fc05a2762ab957648f3f050445e8570ea975c9508fe76c` |
| `main.tex` Conclusion | `8b31a9ac48ee3c6ea1d8e2263d09710513341b198b6dad237a627d42a67ef5bd` |
| `MANUSCRIPT_ZH_FULL.md` Section 5--6 | `41ee11d917337a16130a2d87b21372001b0de96a06f898ad0c8cb68b17427e8b` |
| `MANUSCRIPT.md` Section 5--6 | `b9cdecc3f924d689d95e16f36aaf694f5f4f7d330561c5bc39abb23ba4c117d0` |
| `MANUSCRIPT_ZH.md` Section 5--6 | `e2aa5371a156063badaf9b637af7fc0144da0535a853ad85e0e2d6160d2136d6` |

### 16.3 只读声明

本轮：

- 没有修改 `paper/main.tex`、任何 `MANUSCRIPT`、`paper/main.pdf`、
  Figure/Table、BibTeX、实验、模型或证据文件；
- 没有重新编译 LaTeX，也没有改写 `.aux/.log`；
- 唯一写入是新建本报告
  `LIMITATIONS_CONCLUSION_PREAUDIT_20260728.md`；
- PDF 检查仅使用现有文件的文本层、页面几何和当前 `main.log`。

### 16.4 审计结束时并行回归

审计结束前，其他并行工作更新了 `paper/main.tex` 与 `paper/main.pdf` 的整文件
内容；本审计没有执行这些更新。结束时整文件 SHA-256 为：

| 文件 | 结束时 SHA-256 | 与开始时关系 |
|---|---|---|
| `paper/main.tex` | `fffadb68876166ad12a93b2f50634494877dce44385ba5a9d809fe06d610b09a` | 整文件变化 |
| `paper/main.pdf` | `a9108b654853a6df50a1350783051ba5fdafb81430d856a6c316ed0a5d9c8ba6` | 整文件变化；结束回归时再次由并行编译刷新 |
| `MANUSCRIPT_ZH_FULL.md` | `18c4637b50805c1169a7b5588e58ee9830dbb331ccd8146436e900154ee80815` | 未变 |
| `MANUSCRIPT.md` | `ea801022bc815b51faeaebb9756138fc7e3caa643d5802dcd5beedd01cb98a07` | 未变 |
| `MANUSCRIPT_ZH.md` | `eda2683e266c9ae37669c0c20741f7bf92879389aed9799305c02714728b7d94` | 未变 |

采用与开始时相同的局部提取口径复核后：

| 对象 | 开始与结束 SHA-256 | 结论 |
|---|---|---|
| `main.tex` Limitations | `02c7944f2122bcad29fc05a2762ab957648f3f050445e8570ea975c9508fe76c` | 未变 |
| `main.tex` Conclusion | `8b31a9ac48ee3c6ea1d8e2263d09710513341b198b6dad237a627d42a67ef5bd` | 未变 |

因此，整文件变化来自本审计目标之外的并行修改，不影响 Limitations/Conclusion 的
文本判断。报告中的 PDF 页面观察已按结束时最新 PDF 重新核对。

---

## 17. 最终状态

# LIMITATIONS_CONCLUSION_PREAUDIT_COMPLETE_READY_FOR_REVISION

证据与主张边界无阻塞。一轮最小写作修订即可：

1. 删除 Limitations 的 composition 末句并精化 operational-weather scope；
2. 将 Conclusion 从结果摘要改为 problem→method→evidence→broader significance；
3. 同步三份 Markdown 的 Section 5--6；
4. 只做一次编译与结尾页面回归，不新增实验或主张。
