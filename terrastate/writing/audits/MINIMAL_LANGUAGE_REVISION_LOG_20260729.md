# TerraState AAAI-27 最小语言修订记录（2026-07-29）

## 1. 范围与权威源

- 权威候选：`MINIMAL_LANGUAGE_REVISION_PROPOSAL_20260729.md`
- 投稿权威正文：`paper/main.tex`
- 同步镜像：`MANUSCRIPT.md`、`MANUSCRIPT_ZH.md`、`MANUSCRIPT_ZH_FULL.md`
- 本轮仅落实下列 8 个已批准 P1；未执行任何 P2，也未自行润色候选。

## 2. 已落实的 8 个 P1

### P1-1 — Abstract：任务价值与 forecasting framing

- **Location:** Abstract，开头任务 framing。
- **Before:** “High-resolution satellite time series are a primary tool for monitoring vegetation, agriculture, and ecosystem response, and are increasingly cast as weather-driven forecasting: predicting future land-surface observations from cloud-obscured image histories and meteorological drivers.”
- **After:** “High-resolution satellite time series are a primary tool for monitoring vegetation, agriculture, and ecosystem response. Forecasting from these series is increasingly formulated as a weather-driven task: predicting future land-surface observations from cloud-obscured image histories and meteorological drivers.”
- **Meaning preserved:** 是。监测价值、受云遮挡的历史影像、气象驱动和未来地表观测全部保留。
- **Evidence boundary preserved:** 是。没有扩大任务范围或增加应用效果主张。

### P1-2 — Abstract：`typically evaluated primarily`

- **Location:** Abstract，固定时域像素精度的证据缺口。
- **Before:** “Yet such models are typically evaluated primarily by fixed-horizon pixel accuracy, which cannot establish whether an internal representation functions as a forecast-bearing, weather-responsive predictive state.”
- **After:** “Yet such models are primarily evaluated by fixed-horizon pixel accuracy, which cannot establish whether an internal representation functions as a forecast-bearing, weather-responsive predictive state.”
- **Meaning preserved:** 是。仍将固定时域像素精度限定为主要评价证据。
- **Evidence boundary preserved:** 是。`cannot establish` 保留；没有把像素精度写成无价值。

### P1-3 — Abstract：state / transition / readout 三层机制

- **Location:** Abstract，TerraState 机制句。
- **Before:** “TerraState structures forecasting around a spatial predictive state inferred from cloud-masked histories, advanced by a shared transition conditioned on future weather, geography, and elapsed time, and read out as an explicit contribution to the final forecast.”
- **After:** “TerraState infers a spatial predictive state from cloud-masked histories. A shared transition advances this state under future weather, geography, and elapsed time, and a state readout converts the advanced state into an explicit contribution to the final forecast.”
- **Meaning preserved:** 是。history → state → shared transition → state readout → forecast contribution 的顺序不变。
- **Evidence boundary preserved:** 是。未来天气未进入 history encoder；未加入递归 rollout 或完整物理状态主张。

### P1-4 — Abstract：architecture-alone 表述

- **Location:** Abstract，可证伪接口句。
- **Before:** “Rather than asserting a world state by architecture, TerraState makes this claim falsifiable through state-contribution removal, a supporting identity-transition control, and matched interventions that compare actual future weather with matched-donor and normalized-mean weather.”
- **After:** “Rather than treating architecture alone as evidence that a world state exists, TerraState makes its predictive-state claim falsifiable through state-contribution removal, a supporting identity-transition control, and matched interventions comparing actual future weather with matched-donor and normalized-mean weather.”
- **Meaning preserved:** 是。state removal、supporting identity-transition control 和两类天气对照均保留。
- **Evidence boundary preserved:** 是。未概括或贬低 conventional models，且 supporting 层级不变。

### P1-5 — Abstract：单句结果压缩

- **Location:** Abstract，最后一句。
- **Before:** “On GreenEarthNet under temporal distribution shift, TerraState retains useful forecasting skill; removing its state contribution degrades performance on both validation and OOD-t splits, with paired confidence intervals excluding zero, while, on a frozen heat--drought subset, actual weather yields lower masked loss over the complete 20-step forecast window than matched-donor and normalized-mean controls, supporting a load-bearing and weather-responsive predictive state.”
- **After:** “On GreenEarthNet under temporal distribution shift, TerraState retains useful forecasting skill; state removal degrades validation and OOD-t performance, and actual weather yields lower complete-window loss than both controls on a frozen heat--drought subset.”
- **Meaning preserved:** 是。GreenEarthNet temporal shift、useful skill、Validation/OOD-t state removal、frozen heat--drought subset 及 actual weather 相对两条控制的 complete-window loss 方向均保留。
- **Evidence boundary preserved:** 是。按批准方案删除摘要中的重复 CI、精确数字和联合性质结论；正文、Table 2、Table 3 与 Figure 3 仍保留完整证据。没有加入因果、反事实、composition 或 extreme-specific enhancement 主张。

### P1-6 — Method §3.4：detectable response statistic

- **Location:** §3.4 `Testable Predictive-State Interfaces`。
- **Before:** “A response is \emph{detectable} when actual and control weather produce a nonzero, reportable masked forecast-output response statistic under the same forecast mask.”
- **After:** “A response is \emph{detectable} when the masked mean absolute forecast difference between actual and control weather, computed per minicube over the common forecast mask, is nonzero.”
- **Meaning preserved:** 是。将 Results 已使用的统计量名称明确回填到定义中。
- **Evidence boundary preserved:** 是。未引入阈值、显著性门槛或新统计量。

### P1-7 — Experiments §4.2：relative dimension

- **Location:** §4.2 `Forecasting Performance under Temporal Shift`。
- **Before:** “Its $\mathrm{RMSE}_{25}=0.082$ indicates low error over the first 25 forecast days and represents TerraState's most favorable relative dimension in the table.”
- **After:** “Its $\mathrm{RMSE}_{25}=0.082$ indicates low error over the first 25 forecast days and is the metric on which TerraState compares most favorably with the listed methods.”
- **Meaning preserved:** 是。数值、25-day 作用域和表内相对比较不变。
- **Evidence boundary preserved:** 是。未加入 SOTA、best、rank 或严格优于主张。

### P1-8 — Table 3 caption：complete-window loss 定义

- **Location:** Table 3 caption。
- **Before:** “Weather interventions on 84 frozen matched pairs. $\Delta$Loss is complete 20-step-window control-minus-actual masked loss (positive favors actual); intervals are geographic-cluster 95\% CIs and counts are descriptive. $R^2$ and RMSE apply only to the matched subset.”
- **After:** “Weather interventions on 84 frozen matched pairs. $\Delta$Loss is the masked loss over the complete 20-step forecast window, computed as control minus actual (positive values favor actual); intervals are geographic-cluster 95\% CIs and counts are descriptive. $R^2$ and RMSE apply only to the matched subset.”
- **Meaning preserved:** 是。完整 20 步窗口、control-minus-actual 方向、84 对、CI 和描述性计数均不变。
- **Evidence boundary preserved:** 是。未改变统计量、样本、方向或显著性含义。

## 3. 镜像同步

- `MANUSCRIPT.md` 已同步上述完整英文摘要和 3 个正文 P1。
- `MANUSCRIPT_ZH.md` 与 `MANUSCRIPT_ZH_FULL.md` 已同步自然中文语义；中文摘要未加入 CI、精确数字或更强联合结论。
- 中文 §3.4 明确为共同预测掩膜上逐 minicube 计算的掩膜平均绝对预测差。
- 中文 §4.2 与 Table 3 表注分别保持 metric-level comparison 和完整 20 步窗口的 control-minus-actual 定义。

## 4. 回归门禁

- **P2 修改数量：0。**
- **实验数值变化数量：0。** 修改前后数值集合一致；训练事实、结果值、CI、样本数和 split 均未改变。批准的新摘要删除了一处对正文已有 “20-step” 作用域的重复表述，但没有改变任何数值的身份或取值。
- **引用变化数量：0。** `\cite`、`\ref`、`\label` 的数量、顺序和内容均一致。
- **公式变化数量：0。** 8 个 `equation` 环境逐字节一致。
- **Figure 内容变化数量：0。** 三个 `\includegraphics` 路径和三张正式图哈希均不变。
- **Table 数据/结构变化数量：0。** 3 个 `tabular` 环境逐字节一致；仅 Table 3 的已批准 caption 语言发生变化。
- **Contributions 变化数量：0。**
- `paper/main.tex` 的修改相对基线恰为 4 个 diff hunk：完整摘要、§3.4、§4.2、Table 3 caption。

## 5. 摘要与编译检查

- 最终摘要：207 词，9 句。
- 每句词数：15 / 22 / 24 / 30 / 8 / 9 / 29 / 37 / 33。
- 最长句：37 词（可证伪接口句）。
- 结果句：33 词，且仍为一个句子。
- 编译：`latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex` 成功。
- PDF：US Letter，8 页。
- LaTeX error：0；undefined citation/reference：0；overfull hbox/vbox：0。
- 可见元素：Abstract 第 1 页；Figure 1/2/3 分别位于第 2/4/5 页；Table 1/2/3、Limitations、Conclusion 位于第 7 页；References 位于第 8 页。
- 仅存在既有类型的 underfull 警告，未造成裁切、重叠或栏间侵入。

## 6. SHA-256

| 文件 | 修改前 | 修改后 |
|---|---|---|
| `paper/main.tex` | `5fe0a77682e715e51fa2a25442157d4e39c0d7c5f99c0b1663658000622fcd92` | `304db26cc894ba73641c8b2d09acd5fd3f36da1a9f54c6f7b7480b07be52a5d2` |
| `paper/main.pdf` | `f4a77def9e89809565ef382230da30a45e22e5d665c1e1d547579087f8ba0d58` | `f9c3fce5e209b3506c0afa44e4c742b209ad21168f855419ae4e41c3aca2daed` |
| `MANUSCRIPT.md` | `1602fa96b899eb79d6b3e66402504fe86960c63a8760a2140d3ee4633dc8d81c` | `07579ab6c8cc78ab93b114a141d94e70a85b7d70693c6124e4913f1e686a6094` |
| `MANUSCRIPT_ZH.md` | `bf8581f3d8bb20f43a560a17451f731fcd4f56e1b2107c3c50a987f083f8987f` | `d3f16021b91bf30291201a58e9d83ca0070648927870c67f3f0335e7c11d5a56` |
| `MANUSCRIPT_ZH_FULL.md` | `5949a6ea117057dcac70dd38e6995b4b98c14ed6b244fb8564043a59488ee976` | `8e94bce246fc4d6411517e3afab4f3db06e06996c5f29402f901713df0982338` |

未修改的关键文件：

- `paper/references.bib`: `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3`
- Figure 1: `14e32ab755b1c8edb8f35f0764e68041cdaf6c1c3797dcbe1d9ddaef4842c4a6`
- Figure 2: `8fed0b7c4f2cb727d2e7726e72c0ffc2fb4c3f4f26db127e330c0a0e2fe80153`
- Figure 3: `b9049a5a66990a7d026b2049aa4956c817ea3b6764ae5466d16d14197584d17e`

## 7. 状态

`READY_FOR_FINAL_BLIND_REGRESSION_AUDIT`
