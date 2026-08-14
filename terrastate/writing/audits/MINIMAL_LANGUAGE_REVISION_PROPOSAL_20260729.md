# TerraState AAAI-27 最小语言修订候选稿

日期：2026-07-29  
性质：只读语言候选；不构成正文写入  
权威事实源：`paper/main.tex` 与当前 `paper/main.pdf`

## 1. 范围与输入裁决

本候选只处理 `FINAL_LANGUAGE_AAAI_STYLE_AUDIT_20260729.md` 指定的 8 个
P1：摘要 5 项、Method §3.4 一项、Experiments §4.2 一项和 Table 3 caption
一项。公式、引用、图片、表格数值、三项 contributions 和其余正文均不在候选
范围内。

已完整核对：

- `paper/main.tex`；
- `FINAL_LANGUAGE_AAAI_STYLE_AUDIT_20260729.md`；
- `示例/gai.pdf` 的正文与全部 7 个批注；
- `示例/main2--ztt.pdf` 的正文与全部 6 个批注。

两份批注 PDF 与当前 `paper/main.pdf` 的提取文本完全一致。`main2--ztt.pdf`
仅作为语言批注来源：其中关于 Figure 2 的旧内容不进入本候选；其第 3 页
“插个句号”意见在当前正文中已经满足，关于 `KD teacher` 和
`future-state target encoder` 斜体的意见不属于本轮 8 个 P1，也不进入本候选。

## 2. 完整英文摘要候选

下列版本完整保持当前顺序：

> 任务与价值 → weather-driven forecasting framing → 固定时域像素精度的证据
> 缺口 → 可能遗漏的内部失败 → TerraState 身份 → state / transition /
> readout → 可证伪接口 → 单句实验结果。

```latex
High-resolution satellite time series are a primary tool for monitoring
vegetation, agriculture, and ecosystem response. Forecasting from these
series is increasingly formulated as a weather-driven task: predicting
future land-surface observations from cloud-obscured image histories and
meteorological drivers. Yet such models are primarily evaluated by
fixed-horizon pixel accuracy, which cannot establish whether an internal
representation functions as a forecast-bearing, weather-responsive
predictive state. An accurate forecaster may still ignore the weather
forcing, collapse toward persistence, or expose a latent state that does
not actually carry the forecast---failures that standard error metrics
cannot detect. We introduce \textbf{TerraState}, a testable
predictive-state world model. TerraState infers a spatial predictive state
from cloud-masked histories. A shared transition advances this state under
future weather, geography, and elapsed time, and a state readout converts
the advanced state into an explicit contribution to the final forecast.
Rather than treating architecture alone as evidence that a world state
exists, TerraState makes its predictive-state claim falsifiable through
state-contribution removal, a supporting identity-transition control, and
matched interventions comparing actual future weather with matched-donor
and normalized-mean weather. On GreenEarthNet under temporal distribution
shift, TerraState retains useful forecasting skill; state removal degrades
validation and OOD-t performance, and actual weather yields lower
complete-window loss than both controls on a frozen heat--drought subset.
```

### 2.1 结果句校准

候选逐字采用任务推荐的结果句，仅将排版中的 en dash 写为 LaTeX
`heat--drought`：

> On GreenEarthNet under temporal distribution shift, TerraState retains
> useful forecasting skill; state removal degrades validation and OOD-t
> performance, and actual weather yields lower complete-window loss than
> both controls on a frozen heat–drought subset.

该句为 33 词，处于目标 30–45 词内。它逐项保留：

- GreenEarthNet temporal distribution shift；
- useful forecasting skill；
- state removal 对 Validation 和 OOD-t 的性能影响；
- frozen heat–drought subset；
- actual weather 相对两个 controls 的 complete-window loss 方向。

未保留 paired CI、精确数值和联合性质结论，是按任务要求压缩摘要结果，而不是改变
结果：这些限定和数字仍由正文、Table 2、Table 3 和 Figure 3 承担。句中没有新增
显著性、因果、反事实、composition 或 extreme-specific enhancement 主张。

## 3. 原摘要与候选摘要质量报告

### 3.1 计数规则

采用可复核的英语词计数：去除 LaTeX 命令外壳后按英语/数字 token 计数；
`fixed-horizon`、`weather-responsive`、`20-step`、`OOD-t` 和
`heat–drought` 各计为一个词。句号、问号和感叹号用于分句；分号不另起句。

| 项目 | 原摘要 | 候选摘要 |
|---|---:|---:|
| 总词数 | 224 | 207 |
| 句子数 | 7 | 9 |
| 每句词数 | 33, 25, 30, 8, 36, 33, 59 | 15, 22, 24, 30, 8, 9, 29, 37, 33 |
| 最长句 | S7，59 词 | S8，37 词 |
| 是否有一句承担超过两个主要信息角色 | 是：S5、S7 | 否 |

### 3.2 每句唯一职责

#### 原摘要

| 句子 | 词数 | 唯一职责审计 |
|---|---:|---|
| S1 | 33 | 同时承担任务价值和 forecasting framing；两个角色的主语搭配不自然。 |
| S2 | 25 | 固定时域像素精度的证据缺口；职责清楚，但 `typically ... primarily` 重复。 |
| S3 | 30 | 三类内部失败及标准误差指标的盲点；两个紧密相关角色，可接受。 |
| S4 | 8 | TerraState 身份；职责单一。 |
| S5 | 36 | 同时承担 state inference、transition 和 readout 三层机制；超过两个主要角色。 |
| S6 | 33 | 可证伪接口；职责单一，内部列出三种接口。 |
| S7 | 59 | 同时承担 Q1、Q2、Q3、CI 和联合性质结论；明显超载。 |

#### 候选摘要

| 句子 | 词数 | 唯一职责 |
|---|---:|---|
| S1 | 15 | 任务与应用价值。 |
| S2 | 22 | weather-driven forecasting framing 及输入/输出。 |
| S3 | 24 | 固定时域像素精度的证据缺口。 |
| S4 | 30 | 可能被输出指标遗漏的内部失败。 |
| S5 | 8 | TerraState 身份。 |
| S6 | 9 | history-derived predictive state。 |
| S7 | 29 | shared transition 与 state readout；两个连续机制角色。 |
| S8 | 37 | 可证伪接口；一个修辞角色，内部保持 primary/supporting/control 层级。 |
| S9 | 33 | 单句实验结果；一个证据汇总角色，按 Q1→Q2→Q3 平行展开。 |

### 3.3 `with` 与 `while` 在摘要中的位置

#### 原摘要

- S6：`compare actual future weather with ...`。这是清楚的
  `compare A with B`，无需修改。
- S7：`..., with paired confidence intervals excluding zero, while, on a
  frozen ... subset, ...`。`with` 补充 CI、`while` 引入 Q3、`on ... subset`
  又作为插入语，三层结构叠加，构成真实解析风险。

#### 候选摘要

- S8 保留 `comparing actual future weather with ...`，属于正常
  `compare A with B`。
- 不再使用 `while`。这是压缩超载结果句的局部结果，并非为降低词频而机械替换。

### 3.4 逐句对照

#### 对照 1：任务价值与 forecasting framing

**Original**

> High-resolution satellite time series are a primary tool for monitoring
> vegetation, agriculture, and ecosystem response, and are increasingly cast
> as weather-driven forecasting: predicting future land-surface observations
> from cloud-obscured image histories and meteorological drivers.

**Candidate**

> High-resolution satellite time series are a primary tool for monitoring
> vegetation, agriculture, and ecosystem response. Forecasting from these
> series is increasingly formulated as a weather-driven task: predicting
> future land-surface observations from cloud-obscured image histories and
> meteorological drivers.

**Language rationale**

把 monitoring tool 和 forecasting task 分成两个主语明确的句子，避免将 time
series 本身写成被 `cast as forecasting` 的对象。

**Meaning preserved**

是。监测价值、cloud-obscured histories、meteorological drivers 和 future
land-surface observations 全部保留。

**Claim/evidence boundary preserved**

是。未扩大任务范围，也未增加关于应用效果或数据覆盖的新主张。

#### 对照 2：固定时域像素精度的证据缺口

**Original**

> Yet such models are typically evaluated primarily by fixed-horizon pixel
> accuracy, which cannot establish whether an internal representation
> functions as a forecast-bearing, weather-responsive predictive state.

**Candidate**

> Yet such models are primarily evaluated by fixed-horizon pixel accuracy,
> which cannot establish whether an internal representation functions as a
> forecast-bearing, weather-responsive predictive state.

**Language rationale**

删除相邻且功能重叠的 `typically`，保留 `primarily` 对评价重心的限定。

**Meaning preserved**

是。仍然说明固定时域像素精度是主要评价证据。

**Claim/evidence boundary preserved**

是。核心 `cannot establish` 原样保留，没有降格为“能力较弱”，也没有写成像素
精度毫无价值。

#### 对照 3：可能遗漏的内部失败

**Original**

> An accurate forecaster may still ignore the weather forcing, collapse toward
> persistence, or expose a latent state that does not actually carry the
> forecast---failures that standard error metrics cannot detect.

**Candidate**

> An accurate forecaster may still ignore the weather forcing, collapse toward
> persistence, or expose a latent state that does not actually carry the
> forecast---failures that standard error metrics cannot detect.

**Language rationale**

无修改。该句不属于需要修复的 5 个摘要 P1；三类 failure mode 和
`cannot detect` 都承担必要的科学问题边界。

**Meaning preserved**

完全一致。

**Claim/evidence boundary preserved**

完全一致；没有把内部失败写成已经在所有模型中观察到的事实。

#### 对照 4：方法身份

**Original**

> We introduce \textbf{TerraState}, a testable predictive-state world model.

**Candidate**

> We introduce \textbf{TerraState}, a testable predictive-state world model.

**Language rationale**

无修改。句子短、身份清楚。

**Meaning preserved**

完全一致。

**Claim/evidence boundary preserved**

完全一致。

#### 对照 5：state / transition / readout

**Original**

> TerraState structures forecasting around a spatial predictive state inferred
> from cloud-masked histories, advanced by a shared transition conditioned on
> future weather, geography, and elapsed time, and read out as an explicit
> contribution to the final forecast.

**Candidate**

> TerraState infers a spatial predictive state from cloud-masked histories. A
> shared transition advances this state under future weather, geography, and
> elapsed time, and a state readout converts the advanced state into an
> explicit contribution to the final forecast.

**Language rationale**

将三层 reduced-relative 并列拆为 state construction 和
transition/readout 两句；使用主动动词保持执行顺序可恢复。

**Meaning preserved**

是。仍为 history → predictive state → shared transition under future
weather/geography/time → explicit forecast contribution。

**Claim/evidence boundary preserved**

是。没有让 future weather 进入 history encoder，没有写成 recursive rollout，
也没有声称完整物理状态。

#### 对照 6：可证伪接口

**Original**

> Rather than asserting a world state by architecture, TerraState makes this
> claim falsifiable through state-contribution removal, a supporting
> identity-transition control, and matched interventions that compare actual
> future weather with matched-donor and normalized-mean weather.

**Candidate**

> Rather than treating architecture alone as evidence that a world state
> exists, TerraState makes its predictive-state claim falsifiable through
> state-contribution removal, a supporting identity-transition control, and
> matched interventions comparing actual future weather with matched-donor and
> normalized-mean weather.

**Language rationale**

把不自然的 `asserting ... by architecture` 改为
`treating architecture alone as evidence`，并把 `this claim` 的回指明确为
`predictive-state claim`。保留 `Rather than`，没有采用被禁止的
`Unlike conventional models ...`。

**Meaning preserved**

是。三类接口及 identity transition 的 supporting 层级不变。

**Claim/evidence boundary preserved**

是。没有概括或贬低 conventional models；只说明 architecture alone 不是本文
采用的证据。

#### 对照 7：实验结果

**Original**

> On GreenEarthNet under temporal distribution shift, TerraState retains useful
> forecasting skill; removing its state contribution degrades performance on
> both validation and OOD-t splits, with paired confidence intervals excluding
> zero, while, on a frozen heat--drought subset, actual weather yields lower
> masked loss over the complete 20-step forecast window than matched-donor and
> normalized-mean controls, supporting a load-bearing and weather-responsive
> predictive state.

**Candidate**

> On GreenEarthNet under temporal distribution shift, TerraState retains useful
> forecasting skill; state removal degrades validation and OOD-t performance,
> and actual weather yields lower complete-window loss than both controls on a
> frozen heat--drought subset.

**Language rationale**

将 59 词压缩为 33 词，去除 `with ... while, on ...` 的嵌套；用三个平行证据
分句依次表达 Q1、Q2 和 Q3。结果部分仍只有一个句子。

**Meaning preserved**

是。任务要求列出的五项结果信息全部保留。摘要不再重复 CI 和精确数字，但正文与
表图仍完整报告。

**Claim/evidence boundary preserved**

是。没有将 paired CI 改写成新的显著性结论，没有把 frozen subset 外推至完整
OOD-t，也没有直接在结果句中宣称因果、反事实或证明 world model。

## 4. 其余 3 个 P1 最小候选

### 4.1 Method §3.4：detectable response statistic

**Original**

> A response is \emph{detectable} when actual and control weather produce a
> nonzero, reportable masked forecast-output response statistic under the same
> forecast mask.

**Minimal candidate**

> A response is \emph{detectable} when the masked mean absolute forecast
> difference between actual and control weather, computed per minicube over
> the common forecast mask, is nonzero.

**修改理由**

`reportable` 不是统计定义。候选直接复用 Results 中已经存在的统计量名称和 common
forecast mask，不引入 threshold 或显著性门槛。

**是否改变统计量或技术含义**

否。候选只是把当前 Results 已报告的
`per-minicube masked mean absolute forecast difference over the common
forecast mask` 回填到定义中。

**是否增加新的术语或主张**

否。`masked mean absolute forecast difference`、`per minicube` 和
`common forecast mask` 均已存在于当前 Results。

### 4.2 Experiments §4.2：relative dimension

**Original**

> Its $\mathrm{RMSE}_{25}=0.082$ indicates low error over the first 25 forecast
> days and represents TerraState's most favorable relative dimension in the
> table.

**Minimal candidate**

> Its $\mathrm{RMSE}_{25}=0.082$ indicates low error over the first 25 forecast
> days and is the metric on which TerraState compares most favorably with the
> listed methods.

**修改理由**

用常见的 metric-level comparison 取代审计式名词组合
`most favorable relative dimension`，并保留后句的 mixed-profile 语境。

**是否改变统计量或技术含义**

否。数值、25-day 范围和表内相对比较均不变。

**是否增加新的术语或主张**

否。没有加入 SOTA、best、rank 或严格优于其他方法的表述。

### 4.3 Table 3 caption：complete-window control-minus-actual loss

**Original**

> Weather interventions on 84 frozen matched pairs. $\Delta$Loss is complete
> 20-step-window control-minus-actual masked loss (positive favors actual);
> intervals are geographic-cluster 95\% CIs and counts are descriptive.
> $R^2$ and RMSE apply only to the matched subset.

**Minimal candidate**

> Weather interventions on 84 frozen matched pairs. $\Delta$Loss is the masked
> loss over the complete 20-step forecast window, computed as control minus
> actual (positive values favor actual); intervals are geographic-cluster
> 95\% CIs and counts are descriptive. $R^2$ and RMSE apply only to the
> matched subset.

**修改理由**

先定义 loss 的时间作用域，再用独立短语说明差值方向，消除连续前置名词堆叠。

**是否改变统计量或技术含义**

否。仍为完整 20 步窗口、control minus actual，且正值 favor actual。

**是否增加新的术语或主张**

否。没有改变 CI、样本数、subset 作用域或 weather-fidelity 结论。

## 5. `with` / `while` 专项门禁

当前 `main.tex` 共检查到 34 个 `with` 和 12 个 `while`。

### 5.1 真正需要修改的风险

仅发现一处：摘要原 S7（`main.tex:48--50`）：

> ..., with paired confidence intervals excluding zero, while, on a frozen
> heat--drought subset, ...

风险来自 `with` 补充结构、`while` 对比结构和 `on ... subset` 插入语叠加，而非
任一单词本身错误。摘要候选通过压缩结果句消除该嵌套，不作全局替换。

### 5.2 已核对且无需修改的正常用法

- `compare A with B`：摘要 matched interventions（line 45）及
  `compare TerraState with ...`（line 561），**无需修改**。
- `train with AdamW`（line 569），**无需修改**。
- `With ... denoting ...`（line 363），**无需修改**。
- `while retaining ...`（line 338），**无需修改**。
- 清楚的对比/并行从句：Figure 1 caption（line 75）、Introduction
  state removal/weather substitution（line 113）、Related Work（lines 155,
  182）、Figure 2 caption（line 265）、transition encoders（line 299）、
  Q3 Results（line 643）、Limitations（line 706）和 Conclusion
  （lines 715, 718），**均无需修改**。
- 其余 `with` 用于无歧义的输入组合、工具/模型实例化、mask/CI 属性、数学条件或
  `together with` 补充（lines 60, 63, 90, 119, 152, 163, 185, 210,
  215, 262, 264, 278, 294, 309, 344, 380, 388--392, 449, 480, 540,
  622, 635, 637, 685, 712），**均无需修改**。

结论：不存在需要按词频减少 `with` 或 `while` 的问题。

## 6. 冻结边界与 claim–evidence 回归

| 候选表达 | 现有证据 | 状态 |
|---|---|---|
| useful forecasting skill under temporal distribution shift | Q1 / Table 1 | supported；未改数值或排名语气 |
| state removal degrades Validation and OOD-t performance | Q2 / Table 2 / Figure 3(a) | supported；primary 层级不变 |
| actual weather has lower complete-window loss than both controls on the frozen subset | Q3 / Table 3 / Figure 3(b,c) | supported；方向、窗口和 subset 作用域不变 |
| architecture alone is not used as evidence for the predictive-state claim | state-removal, supporting identity diagnostic, weather substitution | supported as evidentiary framing；未概括 prior work |

冻结回归：

- 40 epochs / 14,880 updates：未触及；
- 所有数字、CI、样本数和 split：未触及；
- Q1 prerequisite、Q2 primary、identity supporting、Q3 fidelity：未改变；
- Q3 仍是 complete 20-step window，仍为 control minus actual；
- frozen subset 作用域保持；
- `cannot establish`、`cannot detect` 保留；
- 非因果、非反事实、非 composition、非完整物理状态边界未改变；
- contributions、公式、表格、图片和引用没有候选修改；
- future-state-anchor 消融未进入正文；
- Q4 未重新进入正文。

## 7. 五维自审

1. **Contribution：** 候选不重写三项贡献，也不增加方法身份。
2. **Writing clarity：** 摘要最长句由 59 词降至 37 词；三层机制和超载结果被拆清。
3. **Experimental strength：** 不增加新实验或显著性措辞，仅压缩摘要重复信息。
4. **Evaluation completeness：** Q1--Q3 的摘要证据各保留一次；完整定义仍由正文承担。
5. **Method soundness：** future-information boundary、direct per-horizon transition、
   readout closure 和 intervention hierarchy 均未改变。

## 8. 只读声明

本文件仅提出候选。本轮不应据此自动修改或编译 `paper/main.tex`、
`paper/main.pdf`、任何 Markdown 镜像、图片、表格、引用或实验文件。

# READY_FOR_AUTHOR_AND_SUPERVISOR_REVIEW
