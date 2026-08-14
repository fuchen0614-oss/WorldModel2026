# TerraState AAAI-27 Section 1 Introduction 独立终审

**审计日期：** 2026-07-28  
**审计性质：** 独立、只读的 AAAI 叙事、定位、证据、双语与 PDF 终审  
**权威正文：** `paper/main.tex`  
**目标 venue：** AAAI-27 Main Technical Track  

## 1. 最终结论

# SECTION1_FROZEN

修订后的 Introduction 已达到可冻结质量。当前正文以 5 个正文段落和 3 条贡献
形成稳定论证链：

> task and prior progress → output-level evidence gap → falsifiable scientific
> question → TerraState mechanism and test interfaces → Q1--Q3 evidence preview
> → viewpoint / method / evidence contributions

它没有把所有 EO forecasting 强行定义为 world modeling，而是明确写成本文采用的
`predictive-state world-modeling perspective`；也没有先把 TerraState 的具体
干预协议宣布为领域唯一标准。TerraState 的身份、方法机制和证据之间关系清楚：
历史推断的预测状态位于预测路径上，未来天气只通过共享转移推进该状态，状态贡献
移除和天气路径替换使相关主张能够被经验否证。

Q1--Q3 预告与冻结结果一致：OOD-t 数字准确，Q2 只主张状态贡献移除导致性能下降，
Q3 只主张在冻结匹配子集上真实天气具有更高的完整 20 步预测窗口保真度。正文没有
恢复 SOTA、严格排名、因果或反事实正确性、完整物理状态、hot-dry 特异增强、
Q4/composition、non-collapse、11,904/boundary80 或来源/运行次数叙事。

英文和三份 Introduction 镜像的正文段落、数字和主张强度一致。现有 PDF 在第 1--2
页连续呈现 Introduction；Figure 1 位于第 2 页顶部，没有打断“科学问题→方法概览”
的逻辑，也没有裁切、重叠或异常留白。

### 问题计数

| 等级 | 数量 | 结论 |
|---|---:|---|
| Critical | **0** | 无科学事实、核心证据或严重引用错误 |
| Major | **0** | 无世界模型定位、主线或段落结构阻塞 |
| Minor | **1** | 中文/精简镜像的 Figure 1 说明仍指向旧的“推理与训练监督”版本；不影响投稿正文或 Introduction 冻结 |
| Optional | **2** | P4 密度和 Figure 1 后的跨页续句可在最终排版门禁自然优化 |

综合评分：**4.8 / 5.0**。

---

## 2. 逐段反向提纲

| 单元 | 唯一职责 | 首句与信息纯度 | 与前后段关系 | 终审 |
|---|---|---|---|---|
| P1，`main.tex:57--68` | 建立 EO 任务、现实输入条件与本文采用的 predictive-state world-modeling 视角 | 任务先行；EarthNet2021/GreenEarthNet 提供进展背景；world modeling 明确写成本文视角 | 为 P2 的证据缺口提供任务基础 | **PASS** |
| P2，`main.tex:83--90` | 说明 fixed-window pixel accuracy 无法单独验证 state use 与 weather-driven state advancement | 先承认预测质量进展，再限定证据缺口；没有否定像素预测价值 | 从 progress 自然过渡到 gap | **PASS** |
| P3，`main.tex:92--101` | 给出 predictive-state 概念锚点、可复述科学问题、TerraState 身份与一次性范围边界 | 科学问题在模型机制前出现；没有写具体 CI、阈值或评测合同 | 从 gap 过渡到 method identity | **PASS** |
| P4，`main.tex:103--113` | 概括 history→state→shared transition→readout→forecast，并说明 future anchor 与两个测试接口 | 109 词、5 句；信息较密但职责单一，无工程阶段或损失公式 | 回答 P3 问题，并为 P5 的证据预告搭桥 | **PASS** |
| P5，`main.tex:115--122` | 给出与缺口同构的 Q1、Q2、Q3 headline evidence | 一个 Q1 数字句、一个 Q2 方向句、一个 Q3 完整窗口句和联合结论 | 直接回答 P3 的问题 | **PASS** |
| Contributions，`main.tex:124--136` | 分离科学观点、方法机制与同模型证据 | 三条层级不同，无重复包装 | 冻结全文承诺在 Q1--Q3 | **PASS** |

段落顺序符合成熟 AAAI 方法论文常见定式。没有先宣布模型再补动机，也没有把
Introduction 写成实验日志、评测合同或内部审计。

---

## 3. AAAI 叙事定式审计

| AAAI 叙事槽 | 当前落点 | 判断 |
|---|---|---|
| 1. 任务与现实价值 | P1 前两句 | **PASS** |
| 2. 已有进展 | P1 的 EarthNet2021 / GreenEarthNet；P2 首句承认预测质量提高 | **PASS** |
| 3. 输出精度留下的证据缺口 | P2 | **PASS** |
| 4. 可复述科学问题 | P3 斜体问句 | **PASS** |
| 5. TerraState 方法身份 | P3 `a testable predictive-state world model for weather-driven EO forecasting` | **PASS** |
| 6. 机制如何回应缺口 | P4 的显式 state path、shared transition、readout 与 test interfaces | **PASS** |
| 7. 与缺口同构的结果预告 | P5 的 Q1 useful skill、Q2 degradation、Q3 full-window fidelity | **PASS** |
| 8. 观点/方法/证据三层贡献 | 三条 contributions | **PASS** |

与预审使用的 Drive-OccWorld、Simulator-Informed Latent States、SparseWorld、
iTrendRNN 和 LaNoLem 等 AAAI 写作锚点相比，当前版本采用的是其共同的结构动作：
先建立任务与具体缺口，再给出可复述问题；方法组件只在解释如何回答该问题时出现；
结果预告直接对应缺口。正文没有复制锚点论文的措辞或技术主张。

### 协议文档感与 AI 式表达

- 不再使用 `declared state`、Q 编号列表、完整评测判据、内部 gate 或 checkpoint
  语言来定义科学问题。
- 没有 `novel`, `remarkable`, `comprehensive`, `superior` 等空泛宣传词。
- P3 只保留一次物理/因果/通用模拟器边界，避免反复防御。
- P4 是全篇最密段落，但 5 句分别承担 state construction、transition、readout、
  training anchor 和 post-training interfaces，仍保持单一总职责。

**AAAI 结构成熟度：4.9/5。**

---

## 4. 世界模型定位审计

### 4.1 定位链条

当前逻辑可以由审稿人一次复述为：

1. EO forecasting 是部分观测且受外部天气驱动的预测任务；
2. 本文选择 predictive-state world modeling 作为科学视角，而非宣称这是 EO
   forecasting 的唯一正确定义；
3. 输出精度不能单独验证内部状态是否承担预测、天气是否推进该状态；
4. TerraState 把预测状态置于可观测 forecast path，并隔离 future-weather
   transition；
5. Q2/Q3 通过干预检验上述性质，因此 `testable` 不是装饰性称呼。

### 4.2 指定风险检查

| 风险 | 当前状态 | 判断 |
|---|---|---|
| 将所有 EO forecasting 重新命名为 world modeling | 使用 `We study this task from ... perspective` | **已消除** |
| 自定有利标准再宣布满足 | 先引用 predictive-state view，再提出本文问题；具体判据留在 Method/Results | **已消除** |
| 只说做了干预，却未说明其世界模型意义 | P2 先说明 state/forcing evidence gap，P3 再提出科学问题 | **已消除** |
| 把 predictive state 写成完整物理状态 | P3 明确排除 | **已消除** |
| 把 weather response 写成 causal/counterfactual correctness | P3 排除 causal simulator；P5 只写 matched fidelity | **已消除** |
| 把固定时域预测器包装成通用模拟器 | 明确排除 general-purpose generative simulator；未声称 rollout/composition | **已消除** |
| `testable`、`predictive state`、`world model` 缺少连接 | P2 gap、P3 identity、P4 on-path interfaces 构成完整连接 | **已消除** |

当前最强身份表述
`a testable predictive-state world model for weather-driven EO forecasting`
恰好限定了对象、视角和应用范围，不构成普遍世界模型定义。

**世界模型定位：4.8/5。**

---

## 5. Claim--evidence 对照

| Introduction claim | 位置 | 证据/事实 | 支持强度与边界 | 终审 |
|---|---|---|---|---|
| EO task 使用 cloud-obscured history、past meteorology、geography 和 future weather | P1 | EarthNet2021、GreenEarthNet 及 Method input contract | 任务描述 | **SUPPORTED** |
| Pixel accuracy 不能单独建立 on-path state use 或 weather-driven state advancement | P2 | 逻辑缺口；LatentTSF 支持准确输出可伴随无序 latent representation | `cannot by itself`，未否定输出评价 | **SUPPORTED_WITH_SCOPE** |
| Predictive state 通过 future observables 而非假定隐藏物理变量刻画 | P3 | `littman2001predictive` | 借用 predictive-state view；未声称 TerraState 等同完整经典 PSR | **SUPPORTED_WITH_SCOPE** |
| TerraState 是 testable predictive-state world model | P3--P4 | q→P→T→O、显式 additive state contribution、Q2/Q3 interfaces | 操作性、限定于 weather-driven EO forecasting | **SUPPORTED_WITH_SCOPE** |
| Future EO representation 只在训练期锚定 transitioned state | P4 | Method 3.3 frozen future-state target；inference 不使用 future EO | 方法事实 | **SUPPORTED** |
| OOD-t \(R^2=0.56935\)、RMSE \(=0.15059\) | P5 | 冻结完整 OOD-t Q1，1,904 minicubes | useful skill；无 SOTA、strict ranking 或 equivalence | **SUPPORTED** |
| State removal reduces performance on Validation and OOD-t，paired CIs exclude zero | P5 | Q2 primary state-removal evidence | 不表示全部预测信息都经过 state | **SUPPORTED** |
| Actual weather has lower masked loss than donor/mean on the complete 20-step window | P5 | 84-pair frozen Q3 matched subset；两个 geographic-cluster CIs 排除零 | 只限 matched subset/frozen protocol；非因果、非反事实 | **SUPPORTED_WITH_SCOPE** |
| Joint evidence supports a load-bearing, weather-responsive predictive state | P5 | Q1 prerequisite + Q2 state contribution + Q3 detectable response/fidelity | `under the evaluated protocol` | **SUPPORTED_WITH_SCOPE** |

### 5.1 明确未出现的越界

- 没有把 Q3 subset 的 \(R^2=0.6254\) 写成完整 OOD-t；
- 没有 hot-dry/extreme-specific enhancement；
- 没有 Q4、composition 或 non-collapse；
- 没有 11,904、boundary80、Published/Local/Source、seed/run、`\(\pm\)`；
- 没有 SOTA、best-performing、non-inferiority 或严格排名；
- 没有声称全部 forecast information 只能经过 state；
- 没有 causal effect、counterfactual correctness 或 complete physical state。

`METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md` 中保留的
11,904/boundary80 是历史审计身份，已被作者最新确认和冻结 4.1 的
40 epochs / 14,880 updates 最终模型身份覆盖。Introduction 不报告训练步数，
因此没有恢复该历史冲突。

**Claim--evidence 对齐：5.0/5。**

---

## 6. 贡献列表审计

| 贡献 | 实际层级 | 是否独立 | 证据边界 | 判断 |
|---|---|---|---|---|
| Contribution 1 | 科学问题/观点：把 state contribution 与 forcing response 变成可证伪问题 | 与方法和结果分开 | 不宣称领域唯一 world-model 定义 | **PASS** |
| Contribution 2 | 方法：显式 state-mediated path、shared weather-conditioned transition、future-state anchoring | 三个机制共同定义 TerraState | Future anchor 被作为方法组件，不被包装成已单独证明有效的训练技巧 | **PASS** |
| Contribution 3 | 证据：同一训练模型上的 forecasting prerequisite、state contribution、actual-vs-control full-window fidelity | 与前两条互补 | 不加入 Q4、SOTA、因果或极端增强 | **PASS** |

三条贡献回答了“本文提出了什么”：

- 一个可证伪的 EO predictive-state world-modeling 问题；
- 一个使该问题可操作化的 TerraState 方法；
- 一条在同一模型上闭环的 Q1--Q3 证据链。

没有把训练工程阶段包装为独立创新，也没有把匹配干预协议包装成通用 benchmark。

**贡献列表质量：4.8/5。**

---

## 7. 英文写作与引用

### 7.1 英文质量

- 主语和谓语稳定；没有悬空逻辑或中式英语。
- `predictive state`、`state contribution`、`future weather/forcing`、
  `shared transition` 和 `context-only prediction` 用法稳定。
- P3 的 scientific question 简短可复述，P5 数字发挥 headline-result
  作用但没有压过世界模型主线。
- 511 词左右（修订日志口径，不含 Figure 1 caption）的篇幅落在预审建议的
  490--540 词区间。
- P3 约 86 词，P4 约 109 词；P4 最密但仍可在一次阅读中恢复计算路径。
- 首次解释性 Figure 1 引用位于 P4 开头，即 gap 与 method identity 已建立之后，
  时机合理。

### 7.2 引用邻接与 BibTeX

Introduction 使用 4 个 citation key，全部存在于 `paper/references.bib`：

| Key | 邻接主张 | 支持性 | 判断 |
|---|---|---|---|
| `requenamesa2021earthnet` | guided video prediction、past Sentinel-2/topography/future meteorology | 直接 | **PASS** |
| `benson2024multimodal` | vegetation cloud masking、temporal shift、weather-conditioned forecasting | 直接 | **PASS** |
| `yang2026latenttsf` | accurate outputs can coexist with temporally disordered latent representations | 直接 | **PASS** |
| `littman2001predictive` | state characterized through future observables | 直接，但 TerraState 未声称完整 PSR 保证 | **PASS** |

没有悬空 citation，也没有用一条 citation 支撑过宽的 TerraState 结果主张。

**英文自然度：4.7/5；引用准确性：4.9/5。**

---

## 8. 中文与精简镜像

### 8.1 Introduction 正文

`MANUSCRIPT_ZH_FULL.md` 的五段正文和三条贡献与英文逐段对应：

- task、progress、gap、question、method、evidence 的顺序一致；
- \(R^2=0.56935\)、RMSE \(=0.15059\)、Validation/OOD-t 和完整 20 步窗口均一致；
- `under the evaluated protocol` 自然译为“在当前评测协议下”；
- `supports` 译为“支持”，未增强为“证明”；
- “承载预测且响应天气”没有扩张为完整物理或因果世界状态。

`MANUSCRIPT.md` 和 `MANUSCRIPT_ZH.md` 的 Introduction 正文也已清除旧
endpoint-only Q3、Q4/composition 和 non-collapse 表述。任务要求明确排除的两个
精简镜像其他章节历史内容，本报告没有据此重新打开 Section 2--4。

### 8.2 非阻塞镜像问题

**Minor M1：Figure 1 的镜像说明未同步当前投稿图。**

- **位置：** `MANUSCRIPT_ZH_FULL.md`、`MANUSCRIPT.md` 和
  `MANUSCRIPT_ZH.md` 中紧随贡献列表的 Figure 1 说明；
- **当前状态：** 权威 `main.tex` 使用
  `terrastate_concept_overview_author_20260728.png`，caption 是“testable EO
  world-modeling contract”；三个 Markdown 镜像仍将 Figure 1 称为
  “inference and training supervision / 推理路径与训练监督”，完整中文镜像还
  指向旧 `terrastate_method_overview.*`；
- **原因：** 这是冻结 Figure 1 环境之外的阅读镜像残留，不是 Introduction
  正文或投稿 PDF 的事实错误；
- **审稿人影响：** 对正式 AAAI PDF 无影响，但作者若只看 Markdown 可能误以为
  Figure 1 仍是旧方法训练图；
- **最小后续方向：** 在独立 Figure/mirror 同步任务中，仅把 Markdown 的
  Figure 1 标题、路径和说明同步到当前概念图；不得借此改动 Introduction 正文或
  Figure 1 文件。本项不阻止 Section 1 冻结。

**中文正文质量：4.9/5；Introduction 镜像一致性：4.7/5。**

---

## 9. 跨章节一致性

| 接口 | 一致性 | 说明 |
|---|---|---|
| Frozen Abstract | **PASS** | 同样采用 useful skill、state removal、complete-window actual-vs-control fidelity 和 bounded predictive-state claim |
| Section 2 | **PASS** | EO-WM/VegSim/PSR/LatentTSF 定位与 Introduction 的 gap 一致；Section 2 的 composition-oriented 背景是后续独立写作 TODO，不构成 Introduction 主张 |
| Section 3 opening | **PASS** | history-only \(q/P\)、shared weather-conditioned \(T\)、state readout \(O\)、\(b_h+r_h\) 与 P4 一致 |
| Section 4.1--4.4 | **PASS** | Q1 prerequisite、Q2 primary state removal、Q3 output response/full-window fidelity 均与 P5 一致 |
| Limitations | **PASS** | 非完整物理状态、非因果/反事实、无 extreme-specific enhancement、无 composition claim 均保留 |
| Conclusion | **PASS** | 在 frozen protocol 下收束为 carries forecast information + responds more faithfully to actual weather |
| Figure 1 caption | **PASS** | 正式 caption 的 output gap、exposed state path 和 Q1--Q3 与 Introduction 同构 |

没有发现需要通过削弱 Introduction 来迁就其他章节的事实冲突。

**跨章节一致性：4.8/5。**

---

## 10. PDF 视觉检查

只读检查当前 `paper/main.pdf`，未重新编译。

| 项目 | 当前 PDF | 判断 |
|---|---|---|
| 总页数 | 9 | 记录 |
| Introduction 起点 | 第 1 页左栏下部 | **PASS** |
| P1--P4 阅读 | 第 1 页连续跨栏 | **PASS** |
| Figure 1 | 第 2 页顶部，图像约 \(x=59.0\)--553.0、\(y=54.0\)--279.7\) pt | **PASS** |
| Figure 1 caption | 第 2 页 \(y\approx289.8\)--332.7\) pt | **PASS** |
| P5 与 contributions | 第 2 页 Figure 1 下方左栏 | **PASS** |
| Section 2 起点 | 第 2 页左栏 contributions 后，右栏继续 Related Work | **PASS** |
| 裁切/重叠/越界 | 未发现 | **PASS** |
| 异常留白 | 未发现 | **PASS** |

Figure 1 的视觉位置没有插入 P3 科学问题与 P4 方法概览之间：两者均在第 1 页完成，
Figure 1 随后位于第 2 页顶部。P5 的首句在第 1 页末开始，并在 Figure 1 后续接；
LaTeX 还把 `forecasting` 在页边界分成 `forecast-` / `ing`。这属于可读但略不理想
的普通浮动/分页节奏，不构成 Section 1 的 Minor；若最终全篇 layout gate 因其他
图表自然重排，可优先避免这一跨页续句，禁止为此使用负间距或牺牲字号。

贡献列表完整位于第 2 页左栏，没有拥挤、裁切或异常断裂；Section 2 起始位置自然。

**PDF 呈现：4.5/5。**

---

## 11. 问题清单

### Critical（0）

无。

### Major（0）

无。修改前审计中的三个 Introduction Major 均已关闭：

1. world modeling 已从任务必然定义改为本文研究视角；
2. predictive-state 概念与 TerraState 的 operational tests 已分开；
3. 方法概览已从 Q1--Q3 协议列表改为机制链与两个高层测试接口。

### Minor（1）

#### M1 — Markdown Figure 1 说明仍是旧版本

- **位置：** 三个 Markdown 镜像中 Introduction 后的 Figure 1 说明；
- **原因：** 标题、路径和内容仍描述旧的 inference/training-supervision 图；
- **影响：** 不影响投稿 `main.tex/main.pdf`，但可能误导作者的 Markdown 审阅；
- **最小方向：** 后续只做 Figure/mirror 路径与说明同步，不重开 Section 1 正文；
- **冻结影响：** 无。

### Optional（2）

1. **P4 密度。** `main.tex:103--113` 是 109 词的最密段落，但 5 句职责清楚，
   当前不需要为压缩而损失机制链。
2. **跨页续句。** P5 首句跨 Figure 1 页面续接；可在最终 layout gate 自然改善，
   当前不需要改正文或浮动参数。

---

## 12. 评分

评分标准：1=明显不成熟；3=可用但需实质修改；4=投稿成熟；5=高度成熟。

| 核心维度 | 分数 / 5 | 判断 |
|---|---:|---|
| AAAI 叙事结构 | **4.9** | task→gap→question→method→evidence→contributions 完整 |
| 世界模型定位 | **4.8** | 科学视角与领域唯一标准分开；testability 来源清楚 |
| 科学问题清晰度 | **4.9** | 一句可复述且与 Q2/Q3 同构 |
| 方法概览 | **4.8** | 机制链准确，无训练流水线化 |
| Claim--evidence 对齐 | **5.0** | Q1--Q3 数字、范围和联合结论严格受证据支持 |
| 贡献列表 | **4.8** | 观点、方法、证据三层清楚 |
| 英文自然度与简洁度 | **4.7** | 约 511 词，P4 略密但无协议文档感 |
| 引用与定位 | **4.9** | 4 个引文均存在且邻接主张准确 |
| 中文正文质量 | **4.9** | 逐段同强度，无 bounded-claim 放大 |
| 中英文/镜像一致性 | **4.7** | Introduction 正文一致；Figure 1 Markdown 说明有非阻塞残留 |
| 跨章节一致性 | **4.8** | 与 Abstract、Method、Q1--Q3、Limitations、Conclusion 一致 |
| PDF 视觉呈现 | **4.5** | 无阻塞；仅有普通跨页续句 |
| **平均分** | **4.8 / 5.0** | **达到冻结标准** |

---

## 13. 文件 SHA-256 与只读范围声明

### 13.1 审计输入 SHA-256

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `8191d0ba1de07711a5969dcb3822fe1aecd3669e5711c8d7ec58b10a540a8200` |
| `paper/main.pdf` | `b35c21365f3f93545ce758a48fc1cd6cfcf7eba554ff9b6bf8605ad07b6ae306` |
| `paper/references.bib` | `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659` |
| `MANUSCRIPT_ZH_FULL.md` | `1d26cdc8d3037116b79d3741a7be0fdeac3aae19794453a6cf23fabfd0bd2510` |
| `MANUSCRIPT.md` | `08481eb5c5bb529429978a60d600d87b51118a02a1425736e333a6b94f0c66a7` |
| `MANUSCRIPT_ZH.md` | `614d94e59df4882b1fc45294567ef12ec99db75cc489d763b336f4530bec635b` |
| `SECTION1_REVISION_LOG_20260728.md` | `dba1bbbade481e46bd166e770533e1b1050eb209efae8285cee030188f588132` |
| `SECTION1_2_AAAI_WRITING_CALIBRATION_AND_PREAUDIT_20260728.md` | `8b911acb17197a97966aa6c2be0697488c031f8e2012f9a9acad350c9ea163c9` |
| `METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md` | `ff2c745489ccfda5019a84f001d65403426b2c84c82d4d4a4f1f10cbdd4d1365` |
| `SECTION4_4_1_FINAL_AUDIT_20260728.md` | `63a7e28680da8e70635259e1dc5072c4b254a428eff68d2a4bc8b20841a6b447` |
| `SECTION4_4_2_FINAL_AUDIT_20260728.md` | `a4cb2cb6424318117770155820134e296e95f4e689302e1fa8aceac468ab44ed` |
| `SECTION4_4_3_FINAL_AUDIT_20260728.md` | `cf01a6f6c5ffd08c6ab3624a7f2b09c1099f914e61b6bcabd60100d027456308` |
| `SECTION4_4_4_FINAL_AUDIT_20260728.md` | `d3f9486cf0f3efcc845dd757646d92a6964390069a6f979dc964aef6789ff793` |
| `RESULTS_CLAIM_EVIDENCE_AUDIT.md` | `e8f4f4dcfc4055fb79fc76b59cd6b338222118c6c2ed23115899f6add65b5b0f` |

### 13.2 关键局部区块 SHA-256

| 对象 | SHA-256 |
|---|---|
| Introduction 区块 | `ce34d1ca444bf783eb4ccad116bfb1f4a9dde7f67a1d03dddd328eff04bc2b92` |
| Related Work 区块 | `6ebf7a733cae749c2eb5ea17a163f4d652e2a3834b24b249194f7505abc50d34` |
| Method opening（至 Architecture 前） | `f2aef39aaec412303a2eacf1277bb9f5ae98d4ee01480a082b01b92c233fc5cb` |
| Figure 1 environment | `a977039948dafba50f4c6117fb41827c284d497c4ad3a80f2d1b0635fe7439ee` |
| 完整中文 Introduction 区块 | `2285cae439bae2330f5b2a6794562088bf59ed1d75a2184ffe4d8c758ea15c69` |
| 英文精简 Introduction 区块 | `b3bb69be4770db6b682848a26bde13c1b4e3706afe96ba334eb36d71f7102f2d` |
| 中文精简 Introduction 区块 | `7ed6a7c39658043fc663034fc948984f760e070fa5c5af61677853e33e53f117` |

### 13.3 只读声明

本轮：

- 没有修改 `paper/main.tex`、`paper/main.pdf`、任何 `MANUSCRIPT`、BibTeX、
  Section 2--4、Abstract、Figure、Table、实验或证据文件；
- 没有重新编译 LaTeX，也没有改写 `.aux/.log`；
- 唯一写入是新建本报告
  `SECTION1_FINAL_AUDIT_20260728.md`；
- PDF 检查通过现有文件的文本层、图像位置和页面几何完成。

---

## 14. 冻结判定

当前 Introduction 满足全部冻结条件：

- Critical = 0；
- Major = 0；
- 世界模型身份、科学问题和 TerraState 方法关系清楚；
- 核心主张没有越过冻结证据边界；
- 正文不再具有明显协议/审计文档感；
- AAAI 结构、英文自然度、主线力度、跨章节一致性均不低于 4/5；
- 中文 Introduction 与英文同强度；
- PDF 无阻塞性视觉问题。

唯一 Minor 是 Markdown 中旧 Figure 1 说明的同步问题，它既不属于投稿正文，也不
改变 Introduction 的科学叙事或 PDF，因而不阻止冻结。

最终状态：

# SECTION1_FROZEN
