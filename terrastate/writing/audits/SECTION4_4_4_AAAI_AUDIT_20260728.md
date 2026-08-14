# TerraState Section 4.4 AAAI 写作与证据审计

**审计日期：** 2026-07-28  
**审计性质：** 独立、只读审计  
**审计范围：** Section 4.4 “Weather-Forcing Response”、Table 3、Figure 3 中的 Q3 证据、四份中英文文本及其与 Limitations/Conclusion 的必要接口  
**最终状态：** `READY_FOR_4_4_REVISION`

---

## 1. 最终结论

当前 Q3 的**冻结证据成立且数值一致**：84 对冻结匹配样本完整，Figure 3 panels (b,c)、Table 3 与冻结 JSON 在样本数、损失方向、效应均值、地理簇置信区间和描述性计数上均一致；不存在需要重跑实验、重绘 Figure 3 或修改结果数值的证据阻塞。

当前版本尚不能冻结 Section 4.4，原因是三类呈现问题：

1. 权威英文 4.4 仍以 “Q3 tests whether...” 重新提问开场，且仅称天气替换产生 “nonzero masked forecast-output changes”，没有按既有 Method 3.4 审计要求命名并报告实际的 forecast-output response statistic。由此，“输出发生变化”与“变化具有完整窗口预测保真度”虽在概念上分开，但第一层证据报告不完整。
2. `MANUSCRIPT.md` 与 `MANUSCRIPT_ZH.md` 仍保留旧的 endpoint 语义、旧七列表 3，以及“Figure 3 未接入当前 PDF”的失效状态，与权威 `main.tex` 和完整中文镜像不一致。
3. 当前 PDF 中 Q3 正文位于第 5–6 页、Figure 3 位于第 7 页，而 Table 3 被浮动至第 8 页、紧邻 References；表格本身合规且未裁切，但结果链的阅读顺序不够紧凑。

因此：

- **Critical：0**
- **Major：3**
- **Minor：2**
- **证据状态：PASS**
- **写作与镜像状态：需要最小修订**
- **最终判定：`READY_FOR_4_4_REVISION`**

本结论不重新打开 Section 4.1–4.3、Table 1–2、Q1/Q2 或 40 epochs / 14,880 updates 的最终模型身份。

---

## 2. 审计依据与事实优先级

本审计按以下优先级裁决冲突：

1. 作者最新确认事实与冻结 Q3 JSON；
2. Figure 3 最终精确证据审计和数据追踪；
3. Method 3.4 最终审计；
4. 当前 `paper/main.tex`；
5. `MANUSCRIPT_ZH_FULL.md`；
6. `MANUSCRIPT.md` 与 `MANUSCRIPT_ZH.md`；
7. 历史证据和整合文档。

由此，冻结 JSON 中的 `endpoint_fidelity` 仅被视为 legacy internal field name。论文中的科学 estimand 是**完整 20 步预测窗口上的逐 minicube masked MSE**，不是单独的 \(h=20\) 终点误差。

---

## 3. 当前 Section 4.4 反向提纲

当前 4.4 在排除 Figure 3 和 Table 3 环境后共有 9 个句子，简单英文词元计数约 160。各句职责如下。

| 句次 | 当前内容职责 | 审计 |
|---|---|---|
| 1 | 重新提出 Q3：状态介导路径是否以预测窗口保真度响应未来天气 | **需要重写。** 只是提问，未结论先行 |
| 2 | 声明 84 个冻结匹配对及预声明 extreme-weather stratum | 必须保留，但可与下一句压缩 |
| 3 | 定义 matched-donor：只替换未来天气，且匹配季节、地理和质量 | 必要协议信息；与 Method 3.4 略重复 |
| 4 | 定义 normalized mean：冻结全局 z-score 空间中的零 | 必要但可压缩至同一句 |
| 5 | 导航 Figure 3、Table 2 和 Table 3 | 自然，但 Table 2 在 4.4 中不是主要导航对象，可更聚焦 Q3 |
| 6 | 声明两种替换产生非零 forecast-output change | 正确区分了 response 层，但**未命名统计量、未报告量级** |
| 7 | 声明 actual 的完整 20 步窗口损失低于两条 control | 正确给出 fidelity 方向 |
| 8 | 报告 donor 与 mean 的 control-minus-actual effect 和 cluster CI | 数值、方向和 CI 类型均正确 |
| 9 | 给出有限结论：路径响应天气，actual 更忠实地预测观测窗口 | 基本准确；宜增加 frozen matched protocol 范围限定 |

### 3.1 结构成熟度判断

当前结构是：

> 重新定义问题 → 复述 control → 图表导航 → response 定性陈述 → fidelity 数值 → 结论

更成熟的 AAAI 机制结果结构应为：

> 结论 → 最小 matched-control setting → 可测 output response → fidelity effect/CI → 有限解释与边界

当前稿件不是工程日志，也没有宣传式语言；主要不足是结论出现得过晚、协议铺垫比例偏高，以及 response statistic 没有落实到可复核的名称和量级。

---

## 4. 推荐修改后的信息槽

建议采用“**短开场 + 图表 + 一个结果段**”，共 2 个短段落、7–8 句、约 150–180 个英文词。无需增加新实验或新阈值。

### 槽 1：结论先行

- 直接回答 Q3：
  - the state-mediated path responds detectably to supplied future weather；
  - actual weather has greater complete-window predictive fidelity than both frozen controls under the matched protocol。
- 不以 “Q3 tests whether...” 或 “As shown in...” 开场。

### 槽 2：最小 matched-control setting

- 84 frozen matched pairs；
- predeclared extreme-weather stratum；
- 固定历史、初始状态、静态地理、查询时距、readout、样本和 ground-truth window；
- 只替换进入共享转移的 future-weather sequence。

### 槽 3：压缩 control 定义

- matched donor：season-, geography-, and quality-matched future weather；
- normalized mean：zero in the frozen global z-score space。

两种 control 可在一个句子中定义，无需再次展开 Method 3.4 的完整构造。

### 槽 4：图表导航

- Figure 3 panels (b,c)：展示所有 84 对逐 pair 分布；
- Table 3：给 exact aggregate、effect、CI 和描述性计数。

### 槽 5：forecast-output response

明确命名：

> per-minicube masked mean absolute forecast difference over the common forecast mask

并报告冻结均值：

- actual vs matched donor：0.03592；
- actual vs normalized mean：0.08137；
- 两类替换在 84/84 对上均为有限正值。

这些数值只说明替换天气后输出发生可报告变化；不得称为显著性检验，也不得事后新增 detectability threshold。

### 槽 6：forecast-window response fidelity

- matched donor：\(\Delta\mathrm{Loss}=0.00257\)，geographic-cluster 95% CI \([0.00112,0.00399]\)；
- normalized mean：\(\Delta\mathrm{Loss}=0.01126\)，95% CI \([0.00547,0.01708]\)；
- \(\Delta\mathrm{Loss}=\mathrm{Loss}_{control}-\mathrm{Loss}_{actual}\)；
- 两个区间均排除零，因此 actual 的完整窗口 masked MSE 更低。

### 槽 7：有限世界模型含义

- 路径使用所提供的 future weather；
- actual weather 对观测未来窗口的预测保真度高于两个冻结 control；
- 与 Q2 合并后，支持 forecast-bearing and weather-responsive predictive state。

### 槽 8：极短 scope phrase

建议只保留一处范围限定：

> under the frozen matched protocol

如需防止 extreme-weather stratum 被误读，可加一个短语说明该结果不建立 extreme-specific enhancement；完整负结果继续留在 Limitations，无需在 4.4 重复限制清单。

---

## 5. Q3 两层证据审计

| 证据层 | 固定/改变内容 | 统计量 | 能支持 | 不能支持 | 当前状态 |
|---|---|---|---|---|---|
| A. Forecast-output response | 固定历史、状态、地理、时距、readout、样本和 mask；只替换 future weather | 逐 minicube、共同预测 mask 下的 masked mean absolute forecast difference | 声明的天气路径影响预测输出 | 响应方向正确、因果效应、反事实正确性 | **证据 PASS；正文命名与量级报告不完整** |
| B. Forecast-window response fidelity | actual 与两条冻结 control 比较 | 完整 20 步窗口 masked MSE 的 control-minus-actual 差；geographic-cluster CI | actual 对观测窗口比两个 control 具有更高预测保真度 | 物理真实性、普遍天气 grounding、extreme-specific enhancement | **PASS** |

### 5.1 Response statistic 独立核对

冻结 JSON：

- `models.exclusive.q3_donor_fidelity.response_magnitude.extreme_actual_vs_donor.mean`
  = 0.035918147763281706；
- `models.exclusive.q3_donor_fidelity.response_magnitude.extreme_actual_vs_mean.mean`
  = 0.08136940104443402；
- 每项 \(n=84\)；
- 逐 pair 检查为 84/84 有限正值，无缺失、无非有限值。

Method 3.4 最终审计已经明确：实际 evaluator 使用的是完整 forecast mask 下的逐 minicube masked mean absolute output difference。Section 4 可以补充名称和报告尺度，但不能增加冻结协议中不存在的阈值或显著性门槛。

---

## 6. 冻结 Q3 数值核对

### 6.1 样本与统计单位

| 项目 | 冻结值 | 审计 |
|---|---:|---|
| Frozen matched pairs | 84 | PASS |
| `q3_donor_rows` 行数 | 84 | PASS |
| 唯一 extreme sample key | 84 | PASS |
| 唯一 matched pair tuple | 84 | PASS |
| Geographic clusters | 31 | PASS |
| Missing / non-finite | 0 | PASS |
| Donor unique controls | 45 | PASS；不能写成 45 geographic clusters |

84 对 pair 不是 84 个独立地理区域；主 CI 正确采用 31 个 geographic clusters 的 cluster bootstrap。

### 6.2 Aggregate 与 fidelity

| Weather | \(R^2\) 冻结值 / 文中显示 | RMSE 冻结值 / 文中显示 | Control-minus-actual \(\Delta\)Loss | Geographic-cluster 95% CI | Actual lower |
|---|---|---|---|---|---|
| Actual | 0.625351646… / 0.6254 | 0.149151626… / 0.1492 | reference | — | — |
| Matched donor | 0.589340493… / 0.5893 | 0.158418932… / 0.1584 | 0.002565468… / 0.00257 | [0.001118712…, 0.003987491…] / [0.00112, 0.00399] | 56/84 |
| Normalized mean | 0.543006479… / 0.5430 | 0.197093689… / 0.1971 | 0.011261332… / 0.01126 | [0.005465625…, 0.017079932…] / [0.00547, 0.01708] | 69/84 |

核对结论：

- Table 3：PASS；
- 当前 4.4 正文：PASS；
- Figure 3 panels (b,c)：PASS；
- 冻结 JSON：PASS；
- \(\Delta\)Loss 方向始终为 control minus actual；
- 正值始终表示 actual weather 误差更低；
- 两个 CI 均为 geographic-cluster 95% CI，未与 paired-bootstrap CI 混写；
- 56/84 和 69/84 仅为 descriptive counts，没有被解释为新增显著性检验。

### 6.3 Q1 与 Q3 subset 隔离

- Q3 matched subset：\(R^2=0.6254\)、RMSE \(=0.1492\)；
- 完整 OOD-t Q1：\(R^2=0.56935\)、RMSE \(=0.15059\)。

当前 `main.tex`、Table 3 caption 和完整中文镜像均明确 Q3 数值只适用于 84-pair matched subset，没有把 0.6254 泛化为完整 OOD-t 结果。

---

## 7. 完整窗口与 endpoint 术语审计

| 位置 | 当前语义 | 结论 |
|---|---|---|
| `paper/main.tex` 4.1/3.4/4.4 | complete 20-step forecast-window masked loss | PASS |
| Table 3 caption | complete 20-step forecast-window masked loss | PASS |
| Figure 3 caption | full 20-step forecast-window masked MSE | PASS |
| 当前 Conclusion | complete 20-step forecast window | PASS |
| `MANUSCRIPT_ZH_FULL.md` | 完整 20 步预测窗口 | PASS |
| `MANUSCRIPT.md` 4.4、Figure 3 状态、Conclusion | endpoint loss / endpoint prediction | **FAIL，需同步** |
| `MANUSCRIPT_ZH.md` 4.4、Figure 3 状态 | 终点损失 / 观测终点 | **FAIL，需同步** |
| 冻结 JSON `endpoint_fidelity` | legacy internal key | 允许保留键名，不可据此改变论文定义 |
| 历史 evidence ledger/EVIDENCE | 仍有 endpoint 旧称 | 历史文档问题，不构成当前证据失败 |

简版 Markdown 中的 endpoint 表述可能被读成单独 \(h=20\) 或最后时刻误差，必须在后续镜像同步中改为完整 20 步预测窗口，但本审计不直接修改。

---

## 8. 极端天气主张边界

冻结探索性 hot-dry interaction：

- donor \(\Delta\)Loss interaction mean = 0.0004360789，约 0.00044；
- geographic-cluster 95% CI =
  \([-0.0021624635,0.0031997651]\)，约 \([-0.00216,0.00320]\)；
- 区间跨零；
- 不支持 hot-dry / extreme-specific enhancement。

当前权威 `main.tex` 的 Limitations 对此处理正确：

- 可以说 Q3 在预声明 extreme-weather stratum 上评估；
- 可以说 actual weather 优于两条冻结 control；
- 没有声称极端天气响应强于普通天气；
- 没有把 Q3 写成独立的极端天气预测 benchmark；
- 没有声称 causal effect 或 counterfactual correctness。

把该负结果主要放在 Limitations 是合理的。4.4 最多增加一个极短 scope phrase，避免结果段变成限制清单。当前 Conclusion 使用 “under the frozen protocol”，范围强度正确。

---

## 9. Figure 3 审计

### 9.1 精确文件与追踪

- 文件：`figure_workspace/export/fig3_behavior_v2.pdf`
- SHA-256：`bbf0444dd18c5c910e2bd3d3dcadeccb57e28d3b2bfeee930e004545b351c990`
- 版面：7.0 × 2.55 inch，矢量 PDF；
- 图中文字最小设计字号约 7.5 pt；
- 当前最终精确审计：PASS。

旧 `FIG3_V2_EVIDENCE_AUDIT.md` 中记录的是更早候选 PDF 哈希；当前精确版本应以
`FIG3_V2_CURRENT_EXACT_AUDIT.md` 和 `FIG3_V2_DATA_TRACE.md` 为准。

### 9.2 Q3 panels (b,c)

| 检查项 | 结果 |
|---|---|
| 每个 panel 点数 | 84，全部显示 |
| x 轴 | actual-weather full-window masked MSE |
| y 轴 | matched-donor / normalized-mean full-window masked MSE |
| 坐标范围 | panels (b,c) 一致 |
| \(y=x\) 方向 | 上方表示 control error 更高、actual 更优 |
| Above-diagonal count | 56/84、69/84，由数据计算 |
| 缺失或筛点 | 无 |
| 新主张 | 无 |
| Q4 / causal / extreme enhancement | 未引入 |

Panel (a) 只可视化已冻结 Q2 证据；state removal 为 filled primary marker，\(T\to I\) 为 open supporting marker。它没有改变 Q2 主辅层级。本审计不重新打开 Q2。

### 9.3 可读性与职责

- Figure 3 的 Q3 panels 展示逐 pair 分布和方向；
- Table 3 给 exact aggregate；
- 正文应给 response/fidelity 的科学解释；
- 三者科学职责互补，没有数值冲突；
- 当前正文未逐点复述 Figure 3；
- Figure 3 没有引入正文之外的新机制。

Figure 3 本体无需修改。

---

## 10. Table 3 AAAI 与科学表达审计

| 检查项 | 结果 |
|---|---|
| 只回答 Q3 | PASS |
| 84-pair matched subset 范围 | PASS |
| Actual/donor/mean 数值 | PASS |
| \(\Delta\)Loss 方向 | PASS |
| Geographic-cluster CI | PASS |
| Descriptive count | PASS |
| Caption 位于表体下方 | PASS |
| 源码顺序 tabular → caption → label | PASS |
| Caption 默认 Roman、约 10 pt | PASS |
| 表体约 9 pt | PASS |
| Booktabs、无竖线 | PASS |
| 无 resizebox/scalebox | PASS |
| 无 negative vspace | PASS |
| 无裁切、重叠或 margin intrusion | PASS |
| 自包含性 | PASS |

当前 Table 3 表体在 PDF 第 8 页的边界约为 \(x=56.27\)–287.99 pt、\(y=56.85\)–124.31 pt；caption 约为 \(x=54.00\)–292.49 pt、\(y=137.72\)–202.48 pt，均在页面范围内。

唯一主要版面问题不是表格本体，而是浮动顺序：Table 3 出现在第 8 页 References 开始处，距离第 5–6 页的 Q3 解释较远。后续 revision 应通过调整 Table 3 源码位置或正常浮动参数使其靠近 Q3；不得用负 `\vspace`、极小字体或改变结果解决。

`evidence_workspace/tables/table3_q3.tex` 是未接入当前主稿的历史导出，仍采用旧 endpoint 语义和旧 caption 位置。它不影响当前 `main.tex`，但应在后续交接中标为 superseded，避免误接回正文。

---

## 11. Figure 3、Table 3 与正文分工

| 载体 | 应承担的唯一职责 | 当前表现 |
|---|---|---|
| Figure 3 | 展示 Q2 效应区间和 Q3 的 84 对逐 pair 分布、方向及异质性 | PASS |
| Table 3 | 给 Q3 matched subset 的 exact aggregates、effect、cluster CI 与描述性计数 | PASS |
| Section 4.4 正文 | 结论先行；区分 output response 与 window fidelity；解释有限世界模型含义 | PARTIAL |

不存在科学重复或冲突；问题主要是正文尚未报告 output-response statistic，以及 Table 3 的实际浮动位置削弱了阅读连续性。

---

## 12. 四份中英文文本一致性

| 文本 | 4.4/Q3 数值 | 完整窗口语义 | Table 3 | Figure 3 状态 | 结论强度 | 总评 |
|---|---|---|---|---|---|---|
| `paper/main.tex` | 正确 | 正确 | 当前五列 | 已接入 | 合法有限 | PASS，需写作结构修订 |
| `MANUSCRIPT_ZH_FULL.md` | 正确 | 正确 | 当前五列 | 已接入并可预览 | 与英文一致 | PASS |
| `MANUSCRIPT.md` | 数值基本正确 | 仍写 endpoint | 旧七列 | 错称未接入 | 旧 endpoint 表述 | MAJOR SYNC FAIL |
| `MANUSCRIPT_ZH.md` | 数值基本正确 | 仍写终点 | 旧七列 | 错称正式 PDF 不显示 | 旧终点表述 | MAJOR SYNC FAIL |

完整中文镜像没有把 “supports” 强化为“证明”，也没有把 forecast-window fidelity 翻译成物理真实性。两个简版镜像则需要一次定向同步：

1. 将 4.4 改为与权威 main 同一结果链；
2. 把 endpoint 改为完整 20 步预测窗口；
3. 将 Table 3 同步为当前五列结构；
4. 删除 Figure 3 “未接入/未来接入口”状态；
5. 同步当前 Figure 3 三面板职责与 caption 语义；
6. 将 Conclusion 的 endpoint 改为 complete-window fidelity；
7. 不改 Q1/Q2、Section 3 或任何数值。

---

## 13. 允许与禁止的最强主张

### 13.1 当前证据允许

- Both weather substitutions produce detectable forecast-output responses.
- The state-mediated path responds to supplied future weather.
- Actual weather yields lower complete-window masked loss than both frozen controls.
- Actual weather has greater forecast-window predictive fidelity under the frozen matched protocol.
- Together with Q2, TerraState exposes a forecast-bearing and weather-responsive predictive state.
- The response result is evaluated on a predeclared extreme-weather stratum.

### 13.2 当前证据禁止

- causal effect / causal simulator；
- counterfactual correctness；
- physical truth；
- complete physical world state；
- arbitrary weather interventions are valid；
- universal weather grounding；
- extreme-specific enhancement；
- extreme-weather response is stronger than ordinary-weather response；
- 完整 OOD-t \(R^2=0.6254\)；
- Q3 证明 temporal composition、non-collapse 或 Q4；
- Q3 单独证明普遍世界模型定义。

当前权威英文、完整中文、Figure 3 和 Table 3 均未越界；简版镜像主要是语义陈旧，而不是过度声称 causal/extreme-specific 结论。

---

## 14. Critical / Major / Minor

### Critical：0

没有发现冻结数据错误、样本缺失、方向反转、CI 类型误用、Figure 3 点数不全或需要重跑实验的问题。

### Major：3

#### M1. Section 4.4 机制结果链尚未完成

- **位置：** 4.4 首句及 “Both substitutions produce nonzero...” 句。
- **问题：** 首句重新提问而非结论先行；output response statistic 未命名、未给量级。
- **影响：** 读者能够理解 fidelity，但不能从结果段独立复核“响应发生”的具体观察量。
- **最小修复：** 结论前置；补充 masked mean absolute forecast difference 及 0.03592/0.08137；不新增阈值或显著性检验。

#### M2. 两个简版 Markdown 与权威稿失同步

- **位置：** `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md` 的 4.4、Table 3、Figure 3 状态与 Conclusion。
- **问题：** endpoint 语义、旧七列表、Figure 3 未接入等陈述均已失效。
- **影响：** 四份中英文文本不能形成同一科学定义和当前投稿状态。
- **最小修复：** 仅同步 Q3 相关区块，不改任何数值和冻结章节。

#### M3. Table 3 的 PDF 阅读顺序不理想

- **位置：** PDF 第 8 页。
- **问题：** Table 3 出现在 References 开始页，距离第 5–6 页 4.4 正文和第 7 页 Figure 3 较远。
- **影响：** Q3 的“正文解释—逐 pair 图—aggregate 表”链条被跨页拉开。
- **最小修复：** revision 时只调整 Table 3 环境的源码位置或正常浮动参数，使其靠近 4.4；保持表格本体、caption、字号和数据不变。

### Minor：2

#### m1. 历史 Table 3 导出文件可能造成误接

`evidence_workspace/tables/table3_q3.tex` 仍有旧 endpoint 与旧表注位置。该文件不是当前权威表格；建议在后续交接记录中标为 superseded。

#### m2. 旧 Figure 3 证据审计的 candidate hash 已过期

`evidence_workspace/FIG3_V2_EVIDENCE_AUDIT.md` 记录较早候选导出的 SHA；当前精确审计与数据追踪已经锁定 `bbf044...`。这不影响当前 Figure 3 的证据有效性，但建议后续状态文档明确最终哈希来源。

---

## 15. 质量评分

| 维度 | 评分 / 5 | 说明 |
|---|---:|---|
| AAAI 结果结构 | 3.5 | 证据顺序基本完整，但不是结论先行 |
| 首句力度 | 2.5 | 重新提问，未直接回答 Q3 |
| Output response / fidelity 层级 | 3.5 | 概念分开，但 response statistic 未命名和量化 |
| 统计表达 | 4.8 | 样本、方向、effect 与 cluster CI 准确 |
| 世界模型主线 | 4.5 | 清楚服务 weather-responsive predictive state |
| Claim–evidence 对齐 | 4.8 | 无因果、反事实、极端增强越界 |
| 英文自然度 | 4.2 | 专业清楚，开头略像协议说明 |
| 简洁度 | 4.0 | 约 160 词合理，但 control 定义可压缩 |
| Figure 3 与 Table 3 分工 | 4.0 | 科学职责互补；实际浮动位置不理想 |
| 表格和图注质量 | 4.5 | 自包含、方向清楚、格式合规 |
| 中英文与镜像一致性 | 2.5 | 权威双语一致，两个简版严重陈旧 |
| 与冻结 4.1–4.3 的质量一致性 | 3.6 | 证据质量一致，结果写作结构尚未达到同一完成度 |
| **平均** | **3.9** | 科学证据通过，写作与同步尚需 revision |

---

## 16. 编译与 PDF 只读检查

### 16.1 编译

| 检查项 | 结果 |
|---|---:|
| LaTeX errors | 0 |
| Undefined citations/references | 0 |
| Multiply-defined labels | 0 |
| Overfull boxes | 0 |
| Underfull hboxes | 7，普通非阻塞 |
| PDF 页数 | 9 |

### 16.2 页面位置

- Section 4.4：第 5 页末至第 6 页；
- Figure 3：第 7 页；
- Table 3：第 8 页；
- References：第 8 页开始。

Figure 3 与 Table 3 均无裁切、重叠或越界；Figure 3 在双栏宽度下可读。主要版面问题是 Table 3 与 4.4 的距离，而不是图表本体。

---

## 17. 冻结回归与并行安全

### 17.1 审计开始与结束文件 SHA-256

| 文件 | 开始 SHA-256 | 结束 SHA-256 | 结果 |
|---|---|---|---|
| `paper/main.tex` | `7e2e5f33a6584a0d1558041e27cf31fd4c4124c9aa1cfcd33b642874a28e11c2` | `7e2e5f33a6584a0d1558041e27cf31fd4c4124c9aa1cfcd33b642874a28e11c2` | UNCHANGED |
| `MANUSCRIPT_ZH_FULL.md` | `7c987ff0a581efa70fcad56ae5eecf24ebf107794b5f29c7694b5222ad828469` | `7c987ff0a581efa70fcad56ae5eecf24ebf107794b5f29c7694b5222ad828469` | UNCHANGED |
| `MANUSCRIPT.md` | `91b1de611e21c0d6f283e68e90af374804834dead982e1dce9b53c01943270db` | `91b1de611e21c0d6f283e68e90af374804834dead982e1dce9b53c01943270db` | UNCHANGED |
| `MANUSCRIPT_ZH.md` | `b3d88f0d5a07e8984b0c102ec56522dbb38b8e8e0b3f2e68dd5abd0ee9303354` | `b3d88f0d5a07e8984b0c102ec56522dbb38b8e8e0b3f2e68dd5abd0ee9303354` | UNCHANGED |
| `paper/main.log` | `0cedde3c65f077cf8d782261ae537a6b126f9a45f18b254753219f46e39fd63d` | `0cedde3c65f077cf8d782261ae537a6b126f9a45f18b254753219f46e39fd63d` | UNCHANGED |
| `paper/main.pdf` | `4238bcdbde2785f8a135f27165f4340e50af1de358501a97cfebecb36d8cbcd6` | `4238bcdbde2785f8a135f27165f4340e50af1de358501a97cfebecb36d8cbcd6` | UNCHANGED |

### 17.2 局部区块 SHA-256

| 区块 | SHA-256 | 回归结论 |
|---|---|---|
| Section 3 | `b054a42ed0783ad8bfbfa731bef5137cde11b68a58f1048ce12ad14fc4dbdf7d` | FROZEN / UNCHANGED |
| Section 4.1 | `9feea977ba80119b27150811ca2cb50471f7bf0c8380d7e2aad95466cf8b5f45` | FROZEN / UNCHANGED |
| Section 4.2 | `1255639a23e12090bece746b81f879ac3adcaa3af789d018adb22c3898666740` | FROZEN / UNCHANGED |
| Section 4.3 | `393750e4bb4f8e23703ebac4dd0ccd510257e5b62f00b216a32fe15b9a5a9d3a` | FROZEN / UNCHANGED |
| Section 4.4 | `017ba3a9643c878a4cd885709d7cddd634859fef759b050059f4ae5964da74b4` | 审计对象 / UNCHANGED |
| Table 3 env | `f2f9dd7ec9f212ce132d7e597d2be04085b54d9979327783d81eaacc552dc55d` | UNCHANGED |
| Figure 3 env | `bb50e15a2b30fa1625d7f2981454607a49f2df500937974d9cc35640f398dad6` | UNCHANGED |
| Abstract | `d067709e98b84830d0c5a3cd78ac1f51904e5a42ac0b70abb993186ab64721ab` | UNCHANGED |
| Introduction | `d171277066f1ce281947278340568e3867ad05d1e881eabbe3cb5ef2a54a24c9` | UNCHANGED |

冻结 Q3 JSON SHA-256：

`9dae43b9a8a4fcdf0a73ef91daa58c189a88e769541ce295046cd0e938497041`

当前 Figure 3 export SHA-256：

`bbf0444dd18c5c910e2bd3d3dcadeccb57e28d3b2bfeee930e004545b351c990`

审计期间没有修改 Section 3、Section 4.1–4.3、Table 1–2、Q1/Q2 事实、Abstract、Introduction、Figure 1–3 或任何实验/证据文件。

---

## 18. 最小后续修改顺序

1. **先改权威英文 4.4：** 结论前置；压缩 control 定义；命名并报告 output-response statistic；保持现有 fidelity 数字、方向和 CI 不变。
2. **同步 `MANUSCRIPT_ZH_FULL.md`：** 只跟随新 4.4 结果结构和 response statistic，不改变现有事实。
3. **同步两个简版镜像：** 更新 4.4、Table 3、Figure 3 状态与 Conclusion；删除 endpoint 单时刻歧义。
4. **只优化 Table 3 浮动位置：** 使其靠近 Q3，但不改数据、caption、字号或图表。
5. **回归检查：** 重新核对四份文本、Figure 3 SHA、Table 3 数值、完整 20 步窗口语义以及 PDF 阅读顺序。

无需：

- 重跑 Q3；
- 修改冻结 JSON；
- 重绘或重新导出 Figure 3；
- 修改 Table 3 数值；
- 增加 Q4；
- 重新打开 Section 4.1–4.3；
- 恢复 11,904/boundary80；
- 增加 causal、counterfactual 或 extreme-specific 主张。

---

## 19. 最终状态

`READY_FOR_4_4_REVISION`

科学证据已经充分支持冻结范围内的 Q3 主张；当前阻碍仅为可修复的 AAAI 结果结构、简版镜像同步和 Table 3 阅读顺序问题，不是 Q3 证据阻塞。
