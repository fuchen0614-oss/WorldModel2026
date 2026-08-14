# TerraState AAAI-27 Section 4：修改前 AAAI 写作质量审计

审计日期：2026-07-28  
审计性质：只读写作与表格格式审计  
目标 venue：AAAI-27 Main Technical Track，方法型实证论文  
最终状态：**READY_FOR_4_1_REVISION**

---

## 0. 范围与结论

### 0.1 本轮实际审计范围

本报告只审计：

- Section 4 Experiments；
- 4.1 Experimental Setup；
- 4.2 Forecasting Performance under Temporal Shift；
- 4.3 Load-Bearing Predictive State；
- 4.4 Weather-Forcing Response；
- Table 1、Table 2、Table 3；
- Section 4 与 Limitations、Conclusion 的必要接口。

明确排除：

- Figure 1–3 及其 caption、内部文字、字号、源文件与浮动位置；
- 全篇分页和页数限制；
- Abstract、Introduction、Related Work；
- 已冻结 Section 3 的任何修改；
- 代码、checkpoint、实验输出与证据文件。

因此，图像是否仍在修改**不阻塞**本报告对 Section 4 的判断。

### 0.2 核心结论

当前 Section 4 的冻结数字、统计方向和 Q1–Q3 主张边界正确，具备进入逐小节
修改的事实基础。写作层面存在两个主要问题：

1. **4.1 实现段过重。** 参数计数、运行时 shape、完整训练课程和 selected
   checkpoint 的实际路径集中在一个段落，使实验设置呈现工程审计感。
2. **4.2 结果段过薄。** 当前只报告 TerraState 的 \(R^2\) 与 RMSE，没有解释
   Table 1 的混合性能轮廓、诚实取舍及 Q1 在世界模型证据链中的前提地位。

此外存在一个独立的官方格式问题：

3. **Table 1–3 的 caption 全部位于表格上方，违反 AAAI-27 Author Kit。**
   官方模板明确要求 table number 和 caption 位于表格下方，caption 为
   10pt Roman。这是一个覆盖三张表的 **MAJOR FORMAT** 问题。

### 0.3 问题计数

| 等级 | 数量 | 说明 |
|---|---:|---|
| Critical | **0** | 无事实、统计或证据阻断 |
| Major | **3** | 4.1 过载、4.2 过薄、三表 caption 位置违规 |
| Minor | **7** | 段落顺序、解释层级和表格自包含性问题 |

### 0.4 4.1–4.4 当前总评分

以下评分评价写作质量；三表 caption 的官方格式违规另行计入 Major，不重复拉低
每个结果小节的科学写作分。

| 小节 | 当前评分（1–5） | 判断 |
|---|---:|---|
| 4.1 Experimental Setup | **3.4** | 协议正确，但 implementation/model selection 过载 |
| 4.2 Forecasting Performance under Temporal Shift | **2.8** | 结论正确，但主结果解释明显不足 |
| 4.3 Load-Bearing Predictive State | **4.3** | 证据链完整，只需结论前置与轻度压缩 |
| 4.4 Weather-Forcing Response | **4.1** | 控制与 fidelity 链路清楚，需改善层级和复述 |

---

## 1. 读取基线与事实优先级

### 1.1 已完整读取

1. `paper/main.tex`；
2. `MANUSCRIPT_ZH_FULL.md`；
3. `SECTION4_FINAL_AAAI_AUDIT_20260728.md`；
4. `EXPERIMENTS_RESULTS_AAAI_WRITING_AUDIT.md`；
5. `SECTIONWISE_WRITING_ROADMAP.md`；
6. `METHOD_3_2_FINAL_AUDIT_20260728.md`；
7. `METHOD_3_3_FINAL_AUDIT_20260728.md`；
8. `METHOD_3_4_FINAL_AUDIT_20260728.md`；
9. `evidence_workspace/results_ledger.json`；
10. `vendor/AuthorKit27/AuthorKit27/AnonymousSubmission2027.tex`；
11. `literature/experiment_writing_anchors/` 及已下载的 SparseWorld、
    WorldAgen、Drive-OccWorld 正式论文。

### 1.2 本报告采用的事实优先级

冻结证据与 provenance  
\(>\) 冻结 Section 3 事实与接口  
\(>\) 当前英文正文  
\(>\) 中文镜像  
\(>\) 旧写作审计建议。

AAAI 表格格式以本地 AAAI-27 Author Kit 为最高依据。

### 1.3 与旧 Section 4 终审的关系

`SECTION4_FINAL_AAAI_AUDIT_20260728.md` 已正确冻结三表数值和 Q1–Q3 科学
结论，但它把“caption 位于表格上方”仅记录为当前状态，没有按 AAAI-27
Author Kit 判为违规。本报告不推翻其科学内容结论，只修正这一**格式判定**。

---

## 2. AAAI 正式实验章节锚点

本节直接检查正式论文的 Experiments/Results 原文，只借鉴信息顺序、段落职责和
论证方式，不复制句子，也不建议把这些锚点机械加入 TerraState 参考文献。

### 2.1 ReconVLA（AAAI 2026）

**正式题名：** *ReconVLA: Reconstructive Vision-Language-Action Model as
Effective Robot Perceiver*  
**官方链接：**
[AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/38921)

- **Setup 顺序：** 实验节先列待回答问题，再说明模拟环境、任务和评测单位。
- **主结果首句：** 先规定同一 baseline 上比较哪些 paradigm，随后才指向表格。
- **表后解释：** 从表中选择能回答 paradigm 差异的关键趋势，解释为何某些方案
  有收益、某些方案受冗余或训练难度限制；没有把每格数字重写一遍。
- **trade-off：** 明确报告显式 grounding 有收益但存在视觉冗余，CoT grounding
  甚至明显退化。
- **层级：** paradigm comparison、行为分析、ablation、总体比较和真实任务
  分开。
- **典型段长：** 一个结果功能通常约 4–8 句；设置子段约 2–5 句。
- **可借鉴：** 保留 Q1–Q3 路线；各结果段使用“结论 → 关键证据 → 解释”。
- **不可借用：** 机器人 grounding、attention 与操作泛化结论。

### 2.2 CADYT（AAAI 2026）

**正式题名：** *Causal Structure Learning for Dynamical Systems with
Theoretical Score Analysis*  
**官方链接：**
[AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/40999)

- **Setup 顺序：** 实现选择 → baselines → 数据系统 → metrics → evaluation
  protocol；公共设置只说明一次。
- **主结果首句：** 先说明当前验证的是 sanity/false-positive robustness 或
  structure recovery，再报告结果。
- **表后解释：** 不同 metric 分段解释：NSHD、F1、AUPRC 各自回答不同问题。
- **trade-off：** 承认不规则采样使所有方法退化，同时限定相对结论；积分阶数
  的收益与低阶退化分别陈述。
- **层级：** sanity check、主结果、integration-order analysis、复杂系统与
  Discussion 分开。
- **典型段长：** 每个 metric/result 单元约 3–6 句；Setup 为一个较密但单一
  职责的统一段。
- **可借鉴：** 4.1 一次定义 estimand/CI；4.3/4.4 各自只解释对应证据。
- **不可借用：** 因果发现、结构恢复与理论 guarantee 语言。

### 2.3 SparseWorld（AAAI 2026）

**正式题名：** *SparseWorld: A Flexible, Adaptive, and Efficient 4D
Occupancy World Model Powered by Sparse and Dynamic Queries*  
**官方链接：**
[AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/37347)

- **Setup 顺序：** Dataset and Metrics → Implementation Details → Main
  Results。
- **主结果首句：** 先明确共享输入历史和预测时域，再说明 Table 1 比较哪类
  forecasting。
- **表后解释：** 选择 mIoU、速度和长时域退化等关键维度解释，不逐行复述。
- **trade-off：** 正面承认 IoU 没有明显优势，并提出 metric-specific 的可能
  原因；该限制没有掩盖主结果。
- **层级：** 4D forecasting、planning、qualitative analysis 和 ablation 分开。
- **典型段长：** 主结果任务约 5–8 句；实现细节集中为一个段，不散落到结果段。
- **可借鉴：** 4.2 应诚实描述 mixed metric profile，而非只报本方法两个数字。
- **不可借用：** sparse query、自回归 occupancy、速度与规划性能主张。

### 2.4 WorldAgen（AAAI 2026）

**正式题名：** *WorldAgen: Unified State-Action Prediction with Test-Time
World Model Training*  
**官方链接：**
[AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/38925)

- **Setup 顺序：** Datasets → Implementation Details → Results by benchmark。
- **主结果首句：** 先宣布结果覆盖 CALVIN 与 LIBERO，再分别指向相应表格。
- **表后解释：** 每个 benchmark 选少数对比，连接到测试时适应这一设计目的。
- **trade-off：** ablation 中明确报告数据增多后的收益递减和轻微回落。
- **层级：** 主 benchmark 结果与 world-modeling、LoRA rank、data volume 等
  ablation 分开。
- **典型段长：** benchmark 结果约 3–5 句；单个 ablation 约 3–6 句。
- **可借鉴：** 主结果与机制诊断分层；TerraState 的 Q2/Q3 应保持 intervention
  叙事，不能改写成普通 retraining ablation。
- **不可借用：** action prediction、test-time training 与机器人适应结论。

### 2.5 Drive-OccWorld（AAAI 2025）

**正式题名：** *Driving in the Occupancy World: Vision-Centric 4D Occupancy
Forecasting and Planning via World Models for Autonomous Driving*  
**官方链接：**
[AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/33010)

- **Setup 顺序：** Tasks Definition → Metrics；随后分别报告 forecasting、
  controllability、planning 和 ablation。
- **主结果首句：** 先声明验证“预测质量与条件可控性”两类能力，再进入具体任务。
- **表后解释：** 关键数值后解释它们对应未来状态、动态对象或规划表现的含义。
- **trade-off：** 真实轨迹与预测轨迹在 planning 和 forecasting 上产生不同
  取舍，论文先陈述差异，再给出保留性的可能解释。
- **层级：** forecasting、controllability、planning 与组件 ablation 独立。
- **典型段长：** 每个主任务约 3–7 句；ablation 子段约 3–5 句。
- **可借鉴：** 表负责 exact aggregate，正文负责性能含义和边界。
- **不可借用：** action-controllable generation、occupancy/flow 排名或规划安全。

### 2.6 从锚点归纳出的 Section 4 写作规律

1. Setup 先建立公共实验契约，再进入任务结果。
2. 主结果第一句必须直接回答问题或声明验证对象，不能只写
   “Table X summarizes...”
3. 正文只选支撑结论的最少数字；表格保留完整精确结果。
4. mixed performance 应明确写成 trade-off，不能选择性跳过。
5. 主结果、同模型干预和限制应分层。
6. 解释必须受 protocol 约束，不能由数值差异直接跳到因果或物理结论。
7. 一个结果段通常承担一个结论，长度以约 3–7 句为常见区间；长度服务于
   “结论—证据—解释—边界”，而不是机械追求句数。

---

## 3. 当前 Section 4 反向提纲

| 编号与位置 | 当前唯一职责 | 首句力度 | 单一中心信息 | 是否工程/日志/审计化 | 是否缺解释 | 建议 |
|---|---|---|---|---|---|---|
| E0，4.1 开场，`main.tex:488–499` | 提出 Q1–Q3，声明两项干预不重训练 | **强** | 是 | 否 | 否 | 保留，轻度压缩 |
| E1，Dataset and protocol，`501–509` | 数据、历史/未来窗口、OOD-t 与选模边界 | **强** | 是 | 否 | 否 | 保留 |
| E2，Metrics，`511–520` | 定义 Q1–Q3 metric、estimand 和 CI 单位 | **强** | 是 | 否 | 否 | 保留并按 Q1/Q2/Q3 分句 |
| E3，Comparisons，`522–524` | 列出 Table 1 的方法类别 | **中** | 是 | 略模板化 | **是**；缺比较目的 | 重写为“目的 + 类别” |
| E4，Implementation/model selection，`526–547` | 本应给最少实现与选择信息 | **中** | **否**；同时承担约十项职责 | **是**；像工程 provenance 汇总 | 解释被细节淹没 | 大幅压缩/后移 |
| T1，`549–574` | 完整回答 Q1 的指标轮廓 | 不适用 | 是 | 否 | 表本身完整 | 科学内容保留；caption 移到下方 |
| Q1-1，4.2，`576–580` | 回答是否保留 useful OOD-t skill | **弱**；先做表导航 | 是 | 否 | **明显缺失** | 重写 |
| Q2-1，4.3 开场，`582–587` | 定义主干预与 supporting diagnostic | **强** | 是 | 否 | 轻微：尚未先给结果结论 | 保留并收紧 |
| T2，`589–617` | 区分 official 与 paired effect，回答 Q2 | 不适用 | 是 | 否 | 表本身完整 | 科学内容保留；caption 移到下方 |
| Q2-2，4.3 结果，`619–626` | 退化、paired CI、load-bearing 与 \(T=\mathrm{Id}\) 边界 | **中**；先复述 official drop | 是 | 否 | 否 | 改为结论先行 |
| Q3-1，4.4 开场，`628–635` | 定义 84 对与两种 control | **强** | 是 | 否 | 否 | 保留但减少 Method 3.4 复述 |
| T3，`654–676` | 给 Q3 matched subset 的 exact aggregate 与 CI | 不适用 | 是 | 否 | 表本身完整 | 科学内容保留；caption 移到下方 |
| Q3-2，4.4 结果，`678–686` | 输出响应、fidelity delta/CI 与 weather-responsive 含义 | **中强** | 基本是 | 否 | 轻微：response 与 fidelity 层级可更清楚 | 重排 |
| L1，Limitations，`690–693` | 非完整物理 state 与 supplied-weather 条件 | **强** | 是 | 否 | 否 | 保留 |
| L2，Limitations，`695–701` | 非因果、非反事实、非 extreme-specific 与 branch 范围 | **强** | 信息略多但同属证据边界 | 否 | 否 | 保留 |
| L3，Limitations，`703–707` | 数据集、观测与 composition 外推边界 | **强** | 是 | 否 | 否 | 保留 |
| C1，Conclusion，`711–719` | 回答 Q1–Q3 并形成联合结论 | **强** | 是 | 否 | 否 | 最后仅做节奏收口 |

说明：`main.tex:637–652` 的 Figure 相关导航、环境与 caption 按用户要求完全排除，
不进入本轮问题计数或修改规划。

---

## 4. 逐段问题审计

### 4.1 E0：问题列表

- **唯一职责：** 给出 Q1–Q3 阅读路线；
- **判断：** 合格。Q1 是 forecast prerequisite，Q2/Q3 是内部性质；
- **是否 AI 式：** 否；
- **重复：** 与 Introduction 有必要呼应，但不是冗余动机复述；
- **动作：** 保留；不要在列表后重新解释完整论文贡献。

### 4.2 E1：Dataset and protocol

- **唯一职责：** 建立 GreenEarthNet、10→20 window、OOD-t 和 selection
  boundary；
- **判断：** 合格，段落清楚；
- **重复：** 与 Method 输入定义有轻微交叉，但此处承担 evaluation protocol，
  属于必要重复；
- **动作：** 保留。

### 4.3 E2：Metrics

- **唯一职责：** 一次定义 Q1–Q3 的统计对象；
- **判断：** 合格，尤其正确区分 official dataset-level \(\Delta R^2\) 与
  per-minicube paired effect；
- **风险：** 信息密集，但属于必要统计契约，不是内部审计腔；
- **动作：** 保留；后续可按 Q1、Q2、Q3 的顺序收紧句法。

### 4.4 E3：Comparisons

- **唯一职责：** 应解释 Table 1 为什么设置这些 comparison；
- **当前问题：** 只有四类方法的清单，没有说明这些比较用于定位 forecasting
  utility，而不是定义 world-model validity；
- **AI 式风险：** 句子略像通用模板；
- **动作：** 重写一到两句，加入比较目的，不增加来源标签或严格排名。

### 4.5 E4：Implementation and model selection

- **当前实际承担：**
  1. 架构回顾；
  2. 总参数口径；
  3. 两阶段 trainable 参数数；
  4. state/runtime shape；
  5. optimizer；
  6. epochs/updates/batch/warmup/cosine/clip；
  7. learning rate；
  8. \(\lambda_s\) 全课程；
  9. partial unfreezing；
  10. candidate selection；
  11. selected checkpoint 实际训练路径。
- **判断：** 明显超过单段职责，且与 Section 3 的专业段落纯度不一致；
- **工程/审计感来源：** `unique nn.Parameter scalars`、runtime reshape、对未经历
  最后阶段的逐项反向说明；
- **重复：** 架构回顾重复 3.2，训练身份/目标背景重复 3.3；
- **动作：** 大幅压缩。保留“被评估模型是谁、核心配置、如何选择、实际冻结
  身份”，其余放复现材料或后移。

### 4.6 Q1-1：4.2 唯一结果段

- **当前职责：** 回答 Q1；
- **首句问题：** “Table 1 summarizes Q1”只是导航，不是结果结论；
- **缺少内容：**
  - 与代表性方法的诚实位置；
  - mixed metric profile；
  - TerraState 的 performance trade-off；
  - Q1 与可检验 world-model 主线的连接；
- **当前结论是否支持：** 支持。\(R^2=0.56935\)、RMSE \(=0.15059\) 足以支持
  useful skill；
- **动作：** 重写成“结论 → 最少数字 → mixed profile → trade-off →
  prerequisite 连接”。

### 4.7 Q2-1 与 Q2-2：4.3

- **完整链路：** state removal 主干预 → official/paired 退化 → 两个 split 的
  CI 排除零 → load-bearing → \(T=\mathrm{Id}\) 仅 supporting；
- **判断：** 链路完整；
- **首句：** 开场定义问题有力；结果段可先给 load-bearing 结论，再给 official
  与 paired evidence；
- **是否逐格复述：** 否，只提取必要数字；
- **边界：** 正确说明 identity transition 可能使 readout 接收分布外 state；
- **动作：** 轻度重排，不改变证据。

### 4.8 Q3-1 与 Q3-2：4.4

- **完整链路：** matched-control design → output response → actual-weather
  fidelity advantage → weather-responsive meaning → Limitations 的非因果边界；
- **判断：** 基本完整；
- **重复：** actual/donor/mean 的角色与 Method 3.4 有必要呼应，但可以减少接口
  固定量的隐性复述；
- **层级问题：** “nonzero output changes”与“actual 的 window loss 更低”是
  两层证据，应明确：
  - 前者说明天气路径被模型使用；
  - 后者加 CI 才支持 forecast-window fidelity；
- **是否逐格复述：** 否；正文选择两个 \(\Delta\)Loss 与 CI，合理；
- **动作：** 重排而非扩写。

### 4.9 Limitations 接口

当前限制准确覆盖：

- 非完整 physical state；
- supplied observed weather 与 operational forecast 的差异；
- 非 causal identification；
- 非 counterfactual correctness；
- hot-dry interaction 不支持 extreme-specific enhancement；
- state-mediated branch 不代表所有信息都必须经过 state；
- 单数据集与光学观测限制；
- composition 未验证。

这些限制**没有否定**：

- Q2 的 state-mediated contribution 在冻结协议下 load-bearing；
- Q3 的 actual weather 相对两条冻结 control 具有更高 forecast-window fidelity。

因此 Limitations 应保留，不需要把限制清单重新塞回每个结果段。

### 4.10 Conclusion 接口

Conclusion 已依次回答：

1. Q1：retains useful OOD-t skill；
2. Q2：state-mediated contribution 为正且 paired intervals 排除零；
3. Q3：actual weather 在完整 20-step window 上损失更低；
4. 联合结论：在 frozen protocol 下，predictive state carries forecast
   information and responds more faithfully to actual weather。

中间三句略像实验清单，但最后一句完成了世界模型主线合成。无需重开结论，只需在
4.1–4.4 修改完成后做术语与节奏收口。

---

## 5. Table 1–3：AAAI-27 官方格式审计

### 5.1 Author Kit 的直接要求

本地官方文件：
`vendor/AuthorKit27/AuthorKit27/AnonymousSubmission2027.tex`

关键要求：

- 第 583–588 行：table 正文应使用 **10pt Roman**；必要时可降至 **9pt**；
- 不得使用 `\resizebox` 或其他整体缩放命令；
- 可使用 `\setlength{\tabcolsep}{...}` 压缩列间距；
- 过宽表格应使用双栏，仍不合适时应拆表；
- 第 590 行：table number 与 caption **必须位于表格下方，而非上方**；
- table caption 必须为 **10pt Roman**，不得整体加粗或斜体。

Author Kit 自己的 Table 1/2 示例也采用：

`tabular → caption → label`

### 5.2 当前共同格式状态

当前 Table 1–3 均采用：

`caption → label → small → tabular`

因此三张表都违反了“caption under the table”的明确规则。

后续建议统一为：

```latex
\begin{table...}[t]
\centering
{\small
\setlength{\tabcolsep}{...}
\begin{tabular}{...}
...
\end{tabular}
}
\caption{...}
\label{...}
\end{table...}
```

要点：

- 必须先结束 `\small` 的局部分组，再调用 `\caption`；
- 不能只是把现有 `\caption` 剪切到 `\end{tabular}` 后而让 `\small` 继续生效，
  否则 caption 可能随局部字号降为 9pt，继续违反 10pt caption 要求；
- `\label` 继续紧跟 `\caption`，确保引用编号正确。

### 5.3 Table 1 审计

| 检查项 | 当前状态 | 判定 |
|---|---|---|
| 唯一职责 | Q1 temporal-shift forecasting profile | PASS |
| caption 位置 | 表格上方 | **MAJOR FORMAT** |
| caption 字体 | 当前在 `\small` 前，默认 10pt Roman | PASS；移动后须保持 |
| 表体字号 | `\small`，即约 9pt | ALLOWED；官方允许必要时 9pt |
| 单/双栏 | 七列，使用 `table*` | PASS |
| booktabs | `\toprule/\midrule/\bottomrule` | PASS |
| 竖线/密集 hline | 无 | PASS |
| resizebox/scalebox | 无 | PASS |
| 指标方向 | headers 明示 \(R^2\uparrow\)、RMSE\(\downarrow\)、NSE\(\uparrow\)、bias\(\downarrow\)、RMSE25\(\downarrow\) | PASS |
| 小数位 | 五个性能指标统一 3 位；参数量使用可读单位 | PASS |
| reference/破折号/CI | 不适用 | PASS |
| setting 自包含 | 写 GreenEarthNet temporal shift 与 RMSE25；未直接写 OOD-t 和 \(n=1{,}904\) | MINOR，可更精确 |
| caption 长度 | 简洁，没有逐格复述 | PASS |

建议：不改变表内数值；caption 移到表下，并在不显著增长的前提下明确 OOD-t
setting。是否加入 \(n=1{,}904\) 可与 Table 2 的 sample-size 表达统一决定。

### 5.4 Table 2 审计

| 检查项 | 当前状态 | 判定 |
|---|---|---|
| 唯一职责 | Q2 state contribution + supporting transition diagnostic | PASS |
| caption 位置 | 表格上方 | **MAJOR FORMAT** |
| caption 字体 | 当前默认 10pt Roman | PASS；移动后须保持 |
| 表体字号 | `\small`，约 9pt | ALLOWED |
| 单/双栏 | 六列，使用 `table*` | PASS |
| booktabs | 使用 | PASS |
| 竖线/密集 hline | 无；split 间一条 `\midrule` 合理 | PASS |
| resizebox/scalebox | 无 | PASS |
| 指标方向 | \(R^2\)、official \(\Delta R^2\) 有箭头；caption 定义 full-minus-intervention | PASS |
| official/paired 分离 | 独立列，未把 paired CI 配给 official delta | PASS |
| 小数位 | 所有 score/effect/CI 统一 5 位 | PASS |
| reference 与破折号 | Full 行使用 lowercase `reference` 和 em dash；两 split 一致 | PASS |
| CI 格式 | `[low, high]`，空格和位数一致 | PASS |
| 样本量 | paired units 的 Validation \(n=589\)、OOD-t \(n=1{,}019\) 未在表或 caption 中出现 | **MINOR** |
| caption 自包含 | estimand、paired bootstrap、主辅层级清楚；可再明确正值表示干预退化 | PASS WITH MINOR |
| caption 长度 | 信息密集但仍服务于必要定义 | PASS |

建议：不修改任何 effect/CI；caption 放到表下。为提高统计自包含性，可在 caption
或紧邻表注中简洁报告两个 split 的 paired unit \(n\)，并明确 positive
full-minus-intervention 表示干预后 skill 降低。

### 5.5 Table 3 审计

| 检查项 | 当前状态 | 判定 |
|---|---|---|
| 唯一职责 | Q3 frozen matched subset 的 exact aggregate | PASS |
| caption 位置 | 表格上方 | **MAJOR FORMAT** |
| caption 字体 | 当前默认 10pt Roman | PASS；移动后须保持 |
| 表体字号 | `\small`，约 9pt | ALLOWED；五列单栏下具有必要性 |
| 单/双栏 | 五列，使用单栏 `table` | PASS |
| booktabs | 使用 | PASS |
| 竖线/密集 hline | 无 | PASS |
| resizebox/scalebox | 无 | PASS |
| 指标方向 | header 与 caption 明确；control-minus-actual 正值 favor actual | PASS |
| 小数位 | \(R^2\)/RMSE 4 位，effect/CI 5 位；按列一致 | PASS |
| reference 与破折号 | 与 Table 2 一致 | PASS |
| CI 格式 | `[low, high]`，位数一致 | PASS |
| 样本量 | caption 明确 84 frozen pairs | PASS |
| 计数 | 56/84、69/84 明确为 descriptive | PASS |
| subset 边界 | caption 明确 \(R^2\)/RMSE 仅用于 matched subset | PASS |
| caption 长度 | 较长但自包含；未重复正文全部结论 | PASS |

建议：科学内容和列结构保留，只调整 caption 顺序和字号作用域。若后续压缩 caption，
不得删除 20-step window、control-minus-actual 方向、geo-cluster CI、84 pairs
和 matched-subset 限定。

### 5.6 三表共同结论

| 项目 | 总结 |
|---|---|
| Caption 位置 | **三表均不合规，必须移到表下** |
| 推荐顺序 | **tabular → caption → label** |
| Caption 字体 | 当前是正常 Roman；移动后必须脱离 `\small` 保持 10pt |
| 表体字号 | 当前 9pt，在官方允许范围内 |
| Booktabs | 全部合规 |
| 竖线/密集横线 | 无 |
| 整体缩放 | 无 |
| 方向与 estimand | 总体清楚 |
| 小数位和 CI | 按表/按列一致 |
| 样本量 | Table 3 清楚；Table 2 paired \(n\) 未显示 |
| 三表职责 | 分别只回答 Q1、Q2、Q3，合格 |

---

## 6. 4.1–4.4 推荐信息槽

以下仅规定信息结构，不直接撰写最终英文。

### 6.1 4.1 Experimental Setup

#### 槽 1：开场与三个问题

- 一句话声明 Section 4 评估一个预测前提和两个内部行为性质；
- Q1：useful forecast skill；
- Q2：state contribution；
- Q3：weather-response fidelity；
- 明确 Q2/Q3 使用同一 selected TerraState model，无 retraining。

#### 槽 2：Dataset/protocol

- GreenEarthNet；
- 30 个五日 composite；
- 前 10 步历史、后 20 步预测；
- NDVI、meteorology、mask、static geography 对齐；
- OOD-t \(n=1{,}904\)；
- validation-only model selection；
- OOD-t 与 intervention 结果不参与选择。

#### 槽 3：Metrics/statistics

- Q1：\(R^2\)、RMSE、NSE、absolute bias、\(\mathrm{RMSE}_{25}\)；
- Q2：
  - official dataset-level \(\Delta R^2\)；
  - paired per-minicube mean \(\Delta R^2\)；
  - paired-bootstrap 95% CI；
  - 两种 estimand 分离；
- Q3：
  - complete 20-step forecast-window masked MSE；
  - control-minus-actual 方向；
  - geographic-cluster 95% CI。

#### 槽 4：Comparisons

- 先说明目的：为 Q1 提供代表性 forecasting context；
- 再列 non-learning、recurrent、video-prediction、transformer categories；
- 不把 comparison 写成 world-model validity test；
- 不增加来源分组、SOTA 或严格排名。

#### 槽 5：最少必要 implementation/model selection

主文建议保留：

- 实现与 Section 3 的 \(q/P/T/O\) 结构一致；
- 总参数量的简洁口径（Table 1 需要）；
- optimizer、batch、主 learning rate、计划长度的最小复现集合；
- selected model 只按 validation forecasting 选择；
- selected checkpoint 位于 80% boundary；
- selected model 的 history operator 在实际训练路径中保持冻结。

建议压缩或后移：

- 两阶段精确 trainable parameter counts；
- runtime `[1024B,256]`；
- warmup/cosine/clip 的逐项日志式列举；
- \(\lambda_s\) 每个阶段的完整课程细节；
- 未经历 final phase 的长篇反向说明；
- Section 3 已解释的架构和 training identity。

压缩原则：不删改事实，只让主文回答“评估的是哪个模型、核心训练配置是什么、
如何被选择”。

### 6.2 4.2 Forecasting Performance under Temporal Shift

#### 槽 1：结论

- 首句直接回答 Q1：TerraState retains useful forecasting skill under OOD-t；
- 同时明确这是 world-model evidence chain 的 forecasting prerequisite。

#### 槽 2：关键数字

- \(n=1{,}904\)；
- \(R^2=0.56935\)；
- RMSE \(=0.15059\)；
- 只在解释 trade-off 时引用一个额外有意义的指标，不搬运整张表。

#### 槽 3：代表性方法的诚实比较

- Table 1 呈现 mixed metric profile，不是统一领先；
- TerraState 的 RMSE 与多种学习预测器处于相近数值范围；
- \(\mathrm{RMSE}_{25}=0.082\) 接近表中的较低数值；
- 某些方法在 \(R^2\)、RMSE 或 NSE 上更高/更低；
- 只描述表中事实，不做严格跨实现排名。

#### 槽 4：性能取舍

- TerraState 没有为了可检验状态而失去全部 forecast utility；
- 同时不声称其在 Table 1 上全面优于代表性预测器；
- 不能把指标差异直接归因于显式状态结构。

#### 槽 5：对世界模型论文的作用

- Q1 只建立“值得继续检验内部状态”的预测前提；
- Q2/Q3 才承担 state contribution 与 forcing response 的核心证据；
- 不提前复述 Q2/Q3 数字。

#### 槽 6：禁止越界

- SOTA、best-performing、uniformly superior；
- non-inferiority；
- strict cross-paper ranking；
- 用 Q1 单独证明 world model；
- 宣称其他预测器都没有 state；
- 对性能差异作未经隔离的机制归因。

### 6.3 4.3 Load-Bearing Predictive State

#### 槽 1：科学问题

- 同一 frozen model 上，移除显式 state contribution 是否降低预测质量？

#### 槽 2：state removal 主干预

- state removal 是 defining/primary intervention；
- 不称 retrained ablation；
- official 和 paired estimand 分开。

#### 槽 3：Validation 与 OOD-t 证据

- Validation official drop \(0.01121\)；
- OOD-t official drop \(0.01997\)；
- 用于说明 dataset-level 结果规模。

#### 槽 4：paired CI

- Validation paired mean \(0.01616\)，95% CI
  \([0.00643,0.02590]\)，\(n=589\)；
- OOD-t paired mean \(0.02200\)，95% CI
  \([0.01422,0.03018]\)，\(n=1{,}019\)；
- 两个 CI 都排除零。

#### 槽 5：load-bearing 解释

- 移除 \(r_h\) 后 paired forecast quality 稳定下降；
- 因而 state-mediated contribution 在两个 split 承载可测 forecast increment；
- 不把 additive architecture 本身当作证据。

#### 槽 6：\(T=\mathrm{Id}\) 的地位和边界

- 只称 supporting diagnostic of transition involvement；
- readout 可能接收训练分布外 state；
- 不支持 transition necessity；
- 不与 state removal 同级。

### 6.4 4.4 Weather-Forcing Response

#### 槽 1：matched-control setting

- 84 frozen matched pairs；
- predeclared extreme-weather stratum；
- 31 geographic clusters；
- matched donor 在 season、geography、quality 上匹配。

#### 槽 2：actual、donor、mean 的角色

- actual：样本自身 future weather；
- donor：只替换 future-weather sequence；
- normalized mean：冻结 global z-score space 中的零；
- history、state、geography、horizon、readout 与 target window 固定。

#### 槽 3：output response

- 两种 substitution 均改变 forecast output；
- 这一层只支持 weather path 被使用；
- 不将任意 nonzero change 写成 fidelity 或因果性。

#### 槽 4：forecast-window fidelity

- 完整 20-step masked MSE；
- \(\Delta L=L_{\rm control}-L_{\rm actual}\)；
- 正值表示 actual weather 误差更低。

#### 槽 5：关键数值与 CI

- matched donor：\(0.00257\)，geo-cluster 95% CI
  \([0.00112,0.00399]\)；
- normalized mean：\(0.01126\)，95% CI
  \([0.00547,0.01708]\)；
- 两条 CI 均为正。

#### 槽 6：weather-responsive 含义

- substitution 改变输出；
- actual weather 相对两条声明的 control 具有更高 complete-window fidelity；
- 联合支持 frozen matched protocol 下的 weather-responsive predictive state。

#### 槽 7：边界

- 非 causal effect；
- 非 counterfactual correctness；
- 非 physical truth；
- 非 extreme-specific enhancement；
- 非单独 \(h=20\) endpoint；
- 非 Q4/composition；
- 不泛化为任意 controls。

---

## 7. Claim–Evidence 映射

| 问题/主张 | 冻结证据 | 允许的最强表达 | 不允许 |
|---|---|---|---|
| Q1 useful forecasting skill | OOD-t \(n=1{,}904\)，\(R^2=0.56935\)，RMSE \(=0.15059\) | retains useful forecasting skill under temporal shift | SOTA、best、non-inferior、strict ranking |
| Q2 load-bearing state contribution | Val paired \(0.01616\) CI \([0.00643,0.02590]\)；OOD-t \(0.02200\) CI \([0.01422,0.03018]\) | state-mediated contribution is load-bearing on both splits | 所有预测都经 state、完整 physical state |
| Q2 supporting transition | \(T=\mathrm{Id}\) 同方向退化 | supports transition involvement | transition necessity、defining evidence |
| Q3 output response | fixed-path weather substitution 改变 forecast output | future-weather input affects forecast behavior through declared path | causal response、counterfactual correctness |
| Q3 fidelity | 84 pairs；donor/mean control-minus-actual delta 与 cluster CI 均为正 | actual weather has greater complete-window predictive fidelity than two frozen controls | 任意 control 普遍成立、endpoint-only、physical fidelity |
| 联合主张 | Q1 + Q2 primary + Q3 matched protocol | TerraState exposes a forecast-bearing, weather-responsive predictive state under the frozen protocol | proves a world model、普遍定义、composition |
| extreme-specific guard | interaction CI 跨零 | evidence does not support extreme-specific enhancement | hot-dry enhancement |

Q2/Q3 是同一 selected model 上的 matched intervention，不是重新训练的普通
ablation。该身份必须在后续修改中保持。

---

## 8. 质量评分

评分：1=明显不达标；2=较弱；3=基本可用；4=投稿成熟；5=非常成熟。

| 维度 | 4.1 | 4.2 | 4.3 | 4.4 |
|---|---:|---:|---:|---:|
| AAAI 结构 | 4 | 2 | 4 | 4 |
| 首句力度 | 4 | 2 | 4 | 4 |
| 段落单一职责 | 2 | 5 | 4 | 4 |
| 结果解释深度 | 3 | 1 | 5 | 4 |
| 世界模型主线连接 | 4 | 2 | 5 | 5 |
| claim–evidence 对齐 | 5 | 5 | 5 | 5 |
| 英文自然度 | 4 | 4 | 4 | 4 |
| 简洁度 | 2 | 3 | 4 | 3 |
| 表格与正文分工 | 3 | 2 | 4 | 4 |
| 与 Section 3 质量一致性 | 3 | 2 | 4 | 4 |
| **平均分** | **3.4** | **2.8** | **4.3** | **4.1** |

评分解释：

- 4.1 的 factual contract 很强，但 E4 明显拉低段落纯度与简洁度；
- 4.2 的 claim alignment 正确，低分来自缺少比较和解释；
- 4.3 已是成熟结果段，主要是叙事顺序问题；
- 4.4 证据与边界正确，仍可减少 Method 复述并强化两层证据。

---

## 9. Critical / Major / Minor 清单

### 9.1 Critical（0）

未发现：

- Q1–Q3 数字或方向错误；
- official 与 paired effect 混写；
- Q3 window loss 被误写成单独 endpoint；
- 主张扩大为 causal、counterfactual、physical、composition 或
  extreme-specific；
- 中英文主张强度冲突。

### 9.2 Major（3）

#### M1：4.1 implementation/model-selection 段过载

- **位置：** `main.tex:526–547`；
- **类型：** writing-fixable / reproducibility organization；
- **审稿风险：** 实验设置像工程审计记录，主 protocol 被细节淹没；
- **动作：** 保留最少核心配置与 selected-model identity，其余压缩或后移；
- **不需要：** 新实验或证据变化。

#### M2：4.2 尚未形成 AAAI 主结果段

- **位置：** `main.tex:576–580`；
- **类型：** writing-fixable / analysis-fixable with existing table；
- **审稿风险：** Table 1 的比较价值与 trade-off 未被解释，Q1 看起来只是自报
  两个数字；
- **动作：** 结论 → 最少数字 → mixed profile → trade-off → prerequisite；
- **不需要：** 新 baseline 或数值变化。

#### M3：Table 1–3 caption 位于表格上方

- **位置：** `main.tex:551–554`、`591–596`、`656–661`；
- **类型：** **MAJOR FORMAT / table**；
- **官方依据：** AAAI-27 Author Kit 第 590 行明确要求 caption under table；
- **动作：** 三表统一改为 `tabular → caption → label`；
- **额外约束：** `\small` 只包住 tabular，caption 保持 10pt Roman；
- **不需要：** 修改表格数值、列职责或宽度策略。

### 9.3 Minor（7）

1. **Comparisons 只有类别清单。** 缺少“用于定位 Q1 forecasting utility”的
   目的句。
2. **4.3 结论延迟。** 应先给 load-bearing 结论，再给 official/paired evidence。
3. **4.4 开场与 Method 3.4 有轻度重复。** 保留 control setting，压缩接口复述。
4. **Q3 output-response statistic 未在 Section 4 命名。** 可说明其是固定 mask
   下的 forecast-output response；不得新增事后阈值。
5. **Q3 response 与 fidelity 层级不够显式。** 前者说明使用路径，后者才有
   cluster CI 支撑。
6. **Conclusion 中间呈 Q1–Q3 清单节奏。** 待小节完成后只做节奏收口。
7. **Table 2 未显示 paired sample sizes。** 冻结的 \(n=589/1{,}019\) 应在
   caption 或紧邻表注中简洁呈现；Table 1 的 OOD-t setting/\(n\) 可同步统一。

---

## 10. 推荐修改顺序

### Step 1：4.1

先固定统一实验契约：

> questions → dataset/protocol → metrics/statistics → comparison purpose →
> minimal implementation/model selection

退出条件：

- implementation 不再像工程日志；
- 不改变 selected TerraState model identity；
- 不讨论来源标签、公开数值取得、seed/run 次数；
- Q1–Q3 的 statistic unit 一次定义。

### Step 2：Table 1–3 官方格式

- 只移动 caption/label，并正确限定表体字号作用域；
- caption 为 10pt Roman；
- 表体可保持必要的 9pt；
- 不改任何数值、CI、样本量、列结构或职责。

### Step 3：4.2

- 首句直接回答 Q1；
- 解释 mixed metric profile；
- 写出诚实 performance trade-off；
- 把 Q1 定位为 prerequisite；
- 不写 SOTA、strict ranking 或 non-inferiority。

### Step 4：4.4

- 压缩 Method 重复；
- 分开 output response 与 fidelity；
- 保留 complete 20-step window、两项 delta/CI 和 frozen-control 边界；
- 不写 causal、counterfactual 或 extreme-specific。

### Step 5：4.3

- 保留现有完整证据链；
- 把 load-bearing 结论前置；
- 保持 state removal primary、\(T=\mathrm{Id}\) supporting。

### Step 6：Limitations/Conclusion 接口复核

- Limitations 保留必要边界；
- Conclusion 不重复完整限制清单；
- frozen protocol 和 matched controls 的范围不丢失；
- 中英文同步。

---

## 11. 最终状态

# READY_FOR_4_1_REVISION

依据：

1. Section 4 没有 Critical 事实或证据问题；
2. Q1–Q3 冻结结果足够支持写作重组；
3. 4.1 的修改只需信息压缩与职责分离；
4. 4.2 的增强可完全使用现有 Table 1；
5. 4.3/4.4 的科学证据链已经成立；
6. 三表 caption 的官方格式问题有明确、局部且不改变数据的修复路径；
7. Figure 1–3 的后续状态不阻塞本轮 Section 4 修改。

后续修改必须继续遵守：

> Q1 是预测前提；Q2 是 load-bearing state 的主证据；Q3 是
> external-forcing grounding。正文解释结论，表格给 exact aggregate，
> Limitations 限定外推。

