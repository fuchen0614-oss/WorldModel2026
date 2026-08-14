# TerraState Section 4 最终 AAAI 审计

**审计日期：** 2026-07-28  
**权威正文：** `paper/main.tex`  
**中文镜像：** `MANUSCRIPT_ZH_FULL.md`  
**冻结证据：** `evidence_workspace/results_ledger.json` 及 release evidence bundle  
**审计范围：** Section 4、Table 1–3、中文同步、定点 Limitations 修订与最终编译  

## 1. 最终结论

**SECTION4_CONTENT_PASS_WITH_GLOBAL_PAGINATION_BLOCKER**

Section 4 的问题结构、三张表、结果解释和中英文镜像已经与冻结 Q1–Q3 证据一致，
可以冻结科学内容。未发现实验数值混写、虚构结果或主张越界。

当前仍有一个全篇级版面问题：在 Figure 2 和 Figure 3 均保持主文、尺寸及图像文件
不变的约束下，正文视觉内容延续至第 8 页，参考文献从第 9 页开始。若最终 AAAI
匿名稿要求正文止于第 7 页，该问题必须由后续全篇图表取舍或版面任务处理，不能通过
改写 Q1–Q3 证据、缩小到不可读字号或使用负间距解决。

### 问题计数

- **Critical：0**
- **Major：1**（全篇正文页数；不属于 Section 4 科学内容错误）
- **Minor：1**（非溢出的 underfull 警告）

## 2. 修改前后结构

| 修改前 | 修改后 | 审计判断 |
|---|---|---|
| 4.1 Evaluation Questions and Protocol | 4.1 Experimental Setup | 先问题、再数据、指标、比较与实现 |
| 4.2 Q1: Forecast Skill under Temporal Shift | 4.2 Forecasting Performance under Temporal Shift | 正常报告预测表现，不使用防御性比较语言 |
| 4.3 Q2: A Load-Bearing Predictive State | 4.3 Load-Bearing Predictive State | 主证据与辅助诊断层级明确 |
| 4.4 Q3: Weather-Forcing Response | 4.4 Weather-Forcing Response | 保留同一问题，改为完整预测窗口口径 |
| Table 1 的 Published/Local 双面板 | 统一的七列预测性能表 | 单表回答 Q1 |
| Table 2 将 full→intervention 与 paired 行混排 | full/state removed/T=Id 三行结构 | official 与 paired estimand 分列 |
| Table 3 合并 R²/RMSE | R²、RMSE、ΔLoss、计数独立列 | 精确回答 Q3，且不冒充完整 OOD-t |

Section 4 的最终顺序为：

1. Evaluation questions；
2. Dataset and protocol；
3. Metrics；
4. Comparisons；
5. Implementation and model selection；
6. Q1；
7. Q2；
8. Q3。

未增加 Ablation subsection，也未预留未完成实验。

## 3. Table 1 最终结构与数值

最终列：

`Method | R² ↑ | RMSE ↓ | NSE ↑ | |Bias| ↓ | RMSE25 ↓ | #Params`

| Method | R² | RMSE | NSE | \|Bias\| | RMSE25 | #Params |
|---|---:|---:|---:|---:|---:|---:|
| Persistence | 0.000 | 0.230 | -1.280 | 0.170 | 0.090 | 0 |
| Previous year | 0.560 | 0.200 | -0.400 | 0.140 | 0.180 | 0 |
| Climatology | 0.580 | 0.180 | -0.340 | 0.130 | 0.160 | 0 |
| ConvLSTM | 0.580 | 0.160 | -0.130 | 0.110 | 0.110 | 1.0M |
| Earthformer | 0.520 | 0.160 | -0.130 | 0.100 | 0.090 | 60.6M |
| PredRNN | 0.620 | 0.150 | 0.030 | 0.100 | 0.100 | 1.4M |
| SimVP | 0.600 | 0.150 | 0.030 | 0.090 | 0.100 | 6.6M |
| Contextformer | 0.620 | 0.140 | 0.090 | 0.090 | 0.080 | 6.1M |
| **TerraState** | 0.569 | 0.151 | -0.099 | 0.101 | 0.082 | 7.18M |

检查结果：

- 每个指标列采用统一三位小数；
- TerraState 仅加粗方法名，没有伪装为逐列最优；
- 无 A/B 面板、来源列、Published、Reported 或 Local 标签；
- 无 `±`；
- caption 只说明 GreenEarthNet temporal shift、指标方向和 RMSE25 含义；
- 表格使用 `table*`、`booktabs`，无竖线。

## 4. Table 2 最终结构与数值

最终列：

`Split | Configuration | R² ↑ | RMSE ↓ | Official ΔR² ↑ | Paired ΔR² [95% CI]`

| Split | Configuration | R² | RMSE | Official ΔR² | Paired ΔR² [95% CI] |
|---|---|---:|---:|---:|---:|
| Validation | Full TerraState | 0.49732 | 0.15729 | reference | — |
| Validation | State removed | 0.48611 | 0.17101 | 0.01121 | 0.01616 [0.00643, 0.02590] |
| Validation | T=Id | 0.48542 | 0.26102 | 0.01191 | 0.01742 [0.00782, 0.02696] |
| OOD-t | Full TerraState | 0.56935 | 0.15059 | reference | — |
| OOD-t | State removed | 0.54938 | 0.16519 | 0.01997 | 0.02200 [0.01422, 0.03018] |
| OOD-t | T=Id | 0.54766 | 0.25832 | 0.02169 | 0.02402 [0.01609, 0.03217] |

检查结果：

- official dataset-level ΔR² 与 per-minicube paired effect/CI 分列；
- Full 行为 reference；
- State removed 是正文主证据；
- T=Id 只支持 transition involvement；
- caption 明确两类统计量的差别；
- 正文没有把 official delta 配上 paired CI；
- 表格使用 `table*`、`booktabs`，无竖线。

## 5. Table 3 最终结构与数值

最终列：

`Future weather | R² ↑ | RMSE ↓ | ΔLoss [95% CI] ↑ | Actual lower`

| Future weather | R² | RMSE | ΔLoss [geo-cluster 95% CI] | Actual lower loss |
|---|---:|---:|---:|---:|
| Actual | 0.6254 | 0.1492 | reference | — |
| Matched donor | 0.5893 | 0.1584 | 0.00257 [0.00112, 0.00399] | 56/84 |
| Normalized mean | 0.5430 | 0.1971 | 0.01126 [0.00547, 0.01708] | 69/84 |

检查结果：

- 明确限定为 84 个冻结匹配样本对；
- ΔLoss 定义为 `Loss(control) - Loss(actual)`，caption 明确区间为
  geographic-cluster 95% CI；
- 正值方向准确表示 actual weather 误差更低；
- 56/84 与 69/84 仅为描述性计数；
- R² 与 RMSE 明确只属于 Q3 匹配子集；
- Table 3 给精确汇总，Figure 3 给逐样本分布；
- 表格在单栏内使用 `\small`，未缩放整体表格、未低于既有表格字号；
- 通过拆行保持五列结构，无 overfull，使用 `booktabs` 且无竖线。

## 6. Claim–evidence 映射

| 问题 | 当前最强主张 | 冻结证据 | 正文强度 |
|---|---|---|---|
| Q1 | TerraState retains useful predictive skill under temporal distribution shift. | OOD-t 1,904 minicubes；R²=0.56935，RMSE=0.15059；Table 1 其余指标 | **匹配**；未声称 SOTA 或最优 |
| Q2 | The explicit state-mediated contribution is load-bearing on validation and OOD-t. | State removal 的 official ΔR² 分别为 0.01121/0.01997；paired CIs 均排除零 | **匹配**；主干预与辅助诊断分层 |
| Q2 support | The learned transition is involved in prediction. | T=Id 同方向退化，但 readout 可能接收训练分布外状态 | **匹配**；只作 supporting diagnostic |
| Q3 detectability | Weather substitution changes forecast output under the fixed mask. | 冻结 evaluator 的 masked forecast-output response 为非零可报告值 | **匹配**；未把 latent movement 当作唯一证据 |
| Q3 fidelity | Actual weather has greater forecast-window response fidelity than both controls on the frozen matched subset. | 两个 control-minus-actual ΔLoss 的 geographic-cluster CIs 均为正 | **匹配**；完整 20 步窗口，不是 h=20 endpoint |
| 联合结论 | TerraState exposes a useful, load-bearing, weather-responsive predictive state under the frozen setting. | Q1 + Q2 + Q3 | **匹配**；无因果、完整物理状态、极端增强或 composition 扩张 |

## 7. 禁止项扫描

对英文 Section 4 与 Limitations、中文 Section 4 与 Limitations 进行扫描：

- Published / Reported / Local 标签：**0**
- 公开数值取得方式或本地复现说明：**0**
- single seed / one run / single run：**0**
- strict ranking / best-performing / SOTA：**0**
- matched-backbone 未冻结比较：**0**
- Q4/composition 成功主张：**0**
- causal / counterfactual 正向主张：**0**
- extreme-specific enhancement 正向主张：**0**

必要的限制仍只在 Limitations 中保留：

- non-causal / non-counterfactual；
- not a complete physical state；
- no extreme-specific enhancement；
- no cross-dataset generality；
- temporal composition remains untested；
- operational weather forecasts may differ from supplied observed weather。

## 8. 冻结内容回归证明

### Section 3

修改前后英文 Method 区间 SHA-256 均为：

`f05781674feee6e79d35337deb24f8ea8aaa947f396fc5e0af667a80adf20da6`

修改前后中文 Section 3 区间 SHA-256 均为：

`5ed0956369b74eb4c4b3b3653d596e1ba5197bc65378e46a170ef2d2a68bd2b9`

### 公式

全部 `equation` 环境修改前后 SHA-256 均为：

`f2460777ec69922f3d942c48b3671026f4ebf74c834c7d4572174717a9ef67ac`

### Figure 1–3 图像文件

| 图像 | 修改前后 SHA-256 |
|---|---|
| `paper/figures/terrastate_method_overview.pdf` | `844871dcd2da30f9acb565509ad96a46b7fa440a3f94349d0ebd4ef33a00337f` |
| `paper/figures/terrastate_architecture_fig2_author_slide1.pdf` | `47cc851497f6ef8c05104dfe1917b036164d47d976460df486377f69bf5e6409` |
| `figure_workspace/export/fig3_behavior_v2.pdf` | `bbf0444dd18c5c910e2bd3d3dcadeccb57e28d3b2bfeee930e004545b351c990` |

结论：Section 3、Equation (1)–(8) 与 Figure 1–3 图像资产均未修改。

## 9. 编译与版面审计

编译命令使用工作区内 TeX Live 2026：

`latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`

结果：

- PDF：`paper/main.pdf`
- 总页数：**9**
- Section 4 正文起始：**第 5 页**
- Table 1：**第 6 页**
- Table 2：**第 6 页**
- Table 3：**第 6 页**
- Figure 2：**第 7 页**
- Figure 3：**第 8 页**
- References 起始：**第 9 页**
- LaTeX errors：**0**
- undefined citations：**0**
- undefined references：**0**
- multiply-defined labels：**0**
- overfull boxes：**0**
- underfull hboxes：**8**
- underfull vboxes：**1**
- 表格 caption：均位于表格上方，且后紧接 `\label`
- 表格风格：`booktabs`，无竖线
- 字体：PDF 中使用的 Type1/TrueType 字体均为嵌入子集

逐页渲染位于：

`paper/build_review_section4_final_20260728_final/`

目视结果：

- Table 1–3 均无裁切、重叠或列越界；
- Table 3 的五列在单栏中可读；
- Figure 3 与 Table 2/3 不重叠；
- Figure 2 与 Figure 3 保持原图；
- 双栏正文阅读顺序正常；
- Figure 2、Figure 3 因尺寸与双栏浮动规则分别占据第 7、8 页，是当前正文超出
  第 7 页的直接原因。

## 10. 严重度说明与冻结判断

### Critical：0

没有事实错误、统计量混写、虚构结果、冻结内容回退或不受支持的核心主张。

### Major：1

**全篇分页。** 正文视觉内容延续至第 8 页，而参考文献从第 9 页开始。该问题不能在
不触碰冻结 Figure 2/3 职责或全篇布局的情况下由 Section 4 科学写作单独解决。

### Minor：1

编译记录 8 个 underfull hbox 和 1 个 underfull vbox；均不产生裁切或越界。其中
Section 4 的 Q3 问题句有一处 underfull，属于最终全篇排版校对项。

### 是否冻结 Section 4

**可以冻结 Section 4 的科学内容、三张表和中英文措辞。**

在最终投稿 PDF 冻结前仍需一次独立的全篇分页决策，使正文满足最终页数要求。该任务
不得通过改变本报告中的 Q1–Q3 数字、estimand、主张强度或 Figure 3 证据方向完成。

最终状态：

`SECTION4_TEXT_TABLES_EVIDENCE_FROZEN`

`GLOBAL_PAGINATION_PENDING`
