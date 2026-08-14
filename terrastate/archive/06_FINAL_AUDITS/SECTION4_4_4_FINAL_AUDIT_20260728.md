# TerraState Section 4.4 独立最终审计

**审计日期：** 2026-07-28  
**审计对象：** 最新 Section 4.4 “Weather-Forcing Response”、Table 3、Figure 3 的事实接口及四份中英文文本  
**审计性质：** 独立、只读的 AAAI 写作、冻结证据、主张边界、镜像同步与编译版面终审  
**权威正文：** `paper/main.tex`  
**目标 venue：** AAAI-27 Main Technical Track

---

## 1. 最终结论

# SECTION4_4_4_FROZEN

最新版 Section 4.4 已达到冻结标准。修改前审计的三个 Major 均已关闭：

1. 结果段现已按“结论先行 → 最小 matched-control setting → forecast-output
   response → complete-window fidelity → 有限世界模型解释”组织；
2. 4.4、当前五列表 3、Figure 3 状态和 Q3 相关 Conclusion 已在四份文本中同步；
3. Table 3 虽仍位于 PDF 第 8 页、References 旁边，但其内容、caption、字号、
   边界和阅读恢复性均合规；安全的 `[!t]` 试验没有改善位置，当前已恢复 `[t]`。
   该事项登记为 **DEFERRED TO FINAL LAYOUT GATE**，不是 4.4 的科学、写作或
   编译阻塞。

Q3 的两层证据得到清楚区分：

- 天气替换产生可报告的 forecast-output change；
- actual weather 相较两条冻结 control 在完整 20 步预测窗口上具有更高的
  predictive fidelity。

所有样本数、统计量、方向、置信区间和 subset 范围均与冻结 JSON 一致。正文没有
增加 detectability threshold、显著性检验、因果、反事实、物理真实性、极端天气
特异增强、composition、non-collapse 或 Q4 主张。

**并行修改告警（不计入 4.4 问题）：** 审计结束 SHA 回归发现，另一个窗口在
本审计进行期间修改了 Section 4.1 内的 Table 1，并同步改动三份 Markdown 镜像
及重新编译的 `main.pdf/main.log`。Table 1 新增了若干 `mean \(\pm\) std`、
`public baselines` 和 `Single training run` 表述。该改动不属于 4.4 revision，
且与本任务声明的 Table 1 冻结/不讨论 single-run 约束存在表面冲突。Section 4.4、
Table 3、Figure 3、Section 3、4.2、4.3 及 Q3 证据的局部 SHA 均未变化，因此
不撤销本节冻结；但主监督窗口必须在任何**全篇冻结**前独立处理这项越界并行改动。

### 问题计数

| 等级 | 数量 | 结论 |
|---|---:|---|
| Critical | **0** | 无事实、统计、证据或编译阻塞 |
| Major | **0** | 三个修改前 Major 全部关闭 |
| Minor | **0** | Table 3 页面位置作为全篇 layout gate 登记，不计入 4.4 问题 |

平均质量评分：**4.9 / 5.0**。

---

## 2. 审计范围、材料和路径说明

已按指定事实优先级读取并核对：

1. `paper/main.tex`；
2. `MANUSCRIPT_ZH_FULL.md`；
3. `MANUSCRIPT.md`；
4. `MANUSCRIPT_ZH.md`；
5. `SECTION4_4_4_AAAI_AUDIT_20260728.md`；
6. `SECTION4_4_4_REVISION_LOG_20260728.md`；
7. `SECTION4_4_3_FINAL_AUDIT_20260728.md`；
8. `METHOD_3_4_FINAL_AUDIT_20260728.md`；
9. `RESULTS_CLAIM_EVIDENCE_AUDIT.md`；
10. `evidence_workspace/raw/release/q3_extreme_state_audit.json`；
11. Figure 3 current-exact audit；
12. `figure_workspace/FIG3_V2_DATA_TRACE.md`；
13. `paper/main.log`；
14. `paper/main.aux`；
15. `paper/main.pdf`。

任务给出的第 11 项路径
`evidence_workspace/FIG3_V2_CURRENT_EXACT_AUDIT.md` 当前不存在；实际权威文件为：

`figure_workspace/FIG3_V2_CURRENT_EXACT_AUDIT.md`

本审计读取了该文件。它记录的 Figure 3 PDF SHA、84 对完整性、点坐标、方向与
当前磁盘文件一致。此处只是路径更正，不构成审计问题。

本轮没有重新打开：

- Abstract；
- Introduction；
- Section 3；
- Section 4.1–4.3；
- Table 1–2；
- Q1/Q2；
- 40 epochs / 14,880 updates 最终模型身份；
- Figure 1–3 文件。

上述列表描述本审计的实际审查范围和写入行为；审计期间检测到的外部 Table 1
并行改动单独记录于第 10 节，不归因于本审计，也不纳入 4.4 严重度计数。

---

## 3. 修改前三个 Major 的闭环

### 3.1 M1：4.4 机制结果链

| 修改前问题 | 当前实现 | 终审 |
|---|---|---|
| 首句重新提出 “Q3 tests whether...” | 首句直接给出 detectable response 和 greater complete-window fidelity | **CLOSED** |
| Control 定义铺垫过长 | 84-pair setting 与固定量一条句子；两条 control 合并定义 | **CLOSED** |
| Output response statistic 未命名 | 明确为 per-minicube masked mean absolute forecast difference over the common forecast mask | **CLOSED** |
| Output response 未量化 | 报告 0.03592、0.08137，以及 84/84 有限正值 | **CLOSED** |
| Response 与 fidelity 层级不够显式 | 第 5 句报告 output change；第 6–7 句报告 fidelity 与有限解释 | **CLOSED** |
| 结果结论出现过晚 | 第 1 句结论先行，第 7 句用 frozen matched protocol 收束 | **CLOSED** |

当前 4.4 在去除 Figure 3/Table 3 环境后共有 **7 句**。保守的 LaTeX 去除后
词数为 **178**；修订日志的另一计数口径为约 179 词。该一词差异来自 LaTeX
引用/数学记号分词，不构成内容问题。

当前采用：

> 短结论/协议段 → Figure 3 → Table 3 → 结果段

七个句子分别承担：

1. 直接回答 Q3；
2. 声明 84 对 matched setting、固定量和唯一改变量；
3. 压缩定义 donor 与 normalized mean；
4. 区分 Figure 3 的逐 pair 职责和 Table 3 的 aggregate 职责；
5. 报告 forecast-output response statistic；
6. 报告完整窗口 \(\Delta\)Loss 和 geographic-cluster CI；
7. 在 frozen matched protocol 下给出 Q2+Q3 的有限 predictive-state 解释。

没有重复句、工程 gate、checkpoint、审计口吻或宣传式语言。句 2 和句 6 信息密度
较高，但并未造成语义歧义或 PDF overfull，整体长度符合成熟 AAAI 机制结果段。

**M1：CLOSED。**

### 3.2 M2：四份镜像同步

审计区间限定为本任务明确指定的 4.4、Table 3、Figure 3 状态及 Q3 相关
Conclusion。

| 项目 | `main.tex` | 完整中文 | 英文简版 | 中文简版 | 终审 |
|---|---:|---:|---:|---:|---|
| 结论先行 | 是 | 是 | 是 | 是 | PASS |
| 84 frozen matched pairs | 是 | 是 | 是 | 是 | PASS |
| 固定量与唯一 future-weather 替换 | 是 | 是 | 是 | 是 | PASS |
| Season/geography/quality donor | 是 | 是 | 是 | 是 | PASS |
| Normalized mean 的 frozen z-score 零 | 是 | 是 | 是 | 是 | PASS |
| Response statistic 名称 | 是 | 自然中文对译 | 是 | 自然中文对译 | PASS |
| 0.03592 / 0.08137 | 是 | 是 | 是 | 是 | PASS |
| 完整 20 步窗口 fidelity | 是 | 是 | 是 | 是 | PASS |
| 五列表 3 | 是 | 是 | 是 | 是 | PASS |
| Figure 3 已接入 | 是 | 是 | 是 | 是 | PASS |
| 旧“未接入/未来接入口”状态 | 无 | 无 | 无 | 无 | PASS |
| Q3 相关 Conclusion | 完整窗口 | 完整窗口 | 完整窗口 | 完整窗口 | PASS |
| Supports 是否增强为 proves/证明 | 否 | 否 | 否 | 否 | PASS |

四个 4.4 区块均包含全部必要显示数字，且均无 `endpoint/终点`、旧 Figure 3
状态或 `proves/证明`。

两个 compact mirror 在其冻结、非本轮授权的 Abstract/Introduction/Section 3
等位置仍保留历史普通 `endpoint/终点` 措辞。依据本任务的明确范围约束，这些位置
不作为 4.4 问题，也不在本轮重新审查或建议修改。当前 4.4、Table 3、Figure 3
和 Q3 相关 Conclusion 已不会把 Q3 scientific estimand 误写成单独
\(h=20\) 终点误差。

**M2：CLOSED。**

### 3.3 M3：Table 3 页面位置

| 检查项 | 当前结果 |
|---|---|
| Source placement specifier | `[t]` |
| `[!t]` 安全试验 | 已执行，未改变第 8 页位置 |
| Trial 后是否恢复 | 是，恢复 `[t]` |
| Table 3 页面 | 第 8 页 |
| References 页面 | 第 8 页 |
| 裁切 / 重叠 / 越界 | 无 |
| Caption 位置 | 表格下方 |
| Body nominal size | 约 9 pt |
| Caption size/style | 约 10 pt Roman |
| `resizebox/scalebox` | 无 |
| Negative `\vspace` | 无 |
| 自包含性 | PASS |

Table 3 表体边界约为：

- \(x=56.27\)–287.99 pt；
- \(y=56.85\)–124.31 pt。

Caption 边界约为：

- \(x=54.00\)–292.49 pt；
- \(y=137.72\)–202.48 pt。

References 标题从 \(y\approx224.47\) pt 开始，表注与 References 之间存在可见
间隔。Table 3 完整占据左栏，References 的右栏从页首开始，未发现内容覆盖。

正文自身完整报告 response/fidelity 的定义和决定性数字；Figure 3 caption 与
Table 3 caption 均自包含。因此，即使 Table 3 延后，读者仍能恢复 Q3 证据链。
在 `[!t]` 无效且不允许脆弱排版技巧的条件下，该位置不应阻止 4.4 冻结。

**M3：CLOSED AS `DEFERRED TO FINAL LAYOUT GATE`。**

---

## 4. Forecast-output response 终审

### 4.1 统计量

当前正文准确写为：

> per-minicube masked mean absolute forecast difference over the common
> forecast mask

这与冻结 evaluator 和 Method 3.4 最终审计一致。它是 forecast-output
statistic，不是 latent-state movement，也不是完整窗口 fidelity loss。

### 4.2 冻结结果

| Weather substitution | Frozen exact mean | 正文显示 | \(n\) | Finite | Positive |
|---|---:|---:|---:|---:|---:|
| Actual vs matched donor | 0.035918147763281706 | 0.03592 | 84 | 84/84 | 84/84 |
| Actual vs normalized mean | 0.08136940104443402 | 0.08137 | 84 | 84/84 | 84/84 |

逐行重算：

- donor response 最小值 0.0039939322，最大值 0.1537346542；
- normalized-mean response 最小值 0.0179388877，最大值 0.1862810105；
- 缺失、NaN、Inf、零值和负值均为 0。

### 4.3 解释边界

当前文字只把这些值解释为：替换 transition 的 future-weather input 后，
forecast output 发生可报告变化。

当前没有：

- 新增 detectability threshold；
- 把有限正值称为显著性检验；
- 用 response magnitude 单独证明方向正确；
- 推出 causal effect 或 counterfactual correctness。

**Forecast-output response：PASS。**

---

## 5. Forecast-window fidelity 终审

### 5.1 Scientific estimand

当前科学 estimand 始终为：

> masked MSE over the complete 20-step forecast window

方向始终为：

\[
\Delta\mathrm{Loss}
=\mathrm{Loss}_{\mathrm{control}}
-\mathrm{Loss}_{\mathrm{actual}}.
\]

正值表示 control loss 更高、actual weather 误差更低。

冻结 JSON 的 `endpoint_fidelity` 只作为 legacy internal field name 保留，
没有改变论文的完整窗口定义。

### 5.2 数值与区间

| Control | Exact \(\Delta\)Loss | 显示值 | Geographic-cluster 95% CI exact | 显示区间 | CI excludes 0 |
|---|---:|---:|---|---|---|
| Matched donor | 0.002565468112672014 | 0.00257 | [0.0011187122087714869, 0.003987491067301663] | [0.00112, 0.00399] | 是 |
| Normalized mean | 0.011261332329706334 | 0.01126 | [0.005465624536528642, 0.0170799320898515] | [0.00547, 0.01708] | 是 |

两个区间均来自 31 个 geographic clusters 的 cluster bootstrap。正文与
Table 3 没有把它们写成 paired-bootstrap CI。

### 5.3 Aggregate subset 与完整 OOD-t 隔离

| 范围 | \(R^2\) | RMSE |
|---|---:|---:|
| Q3 的 84-pair matched subset / Actual | 0.6254 | 0.1492 |
| 完整 OOD-t Q1 | 0.56935 | 0.15059 |

Table 3 caption 明确写出 \(R^2\) 和 RMSE 只适用于 matched subset。
正文、Figure 3、Table 3 和四份审计区间均未把 0.6254 写成完整 OOD-t 结果。

**Forecast-window fidelity：PASS。**

---

## 6. 样本与控制协议

| 检查项 | 冻结/当前事实 | 终审 |
|---|---|---|
| Frozen matched pairs | 84 | PASS |
| JSON top-level / protocol / fidelity \(n\) | 84 / 84 / 84 | PASS |
| `q3_donor_rows` | 84 | PASS |
| 唯一 extreme key | 84 | PASS |
| 唯一 pair tuple | 84 | PASS |
| Unique donor controls | 45 | PASS |
| Geographic clusters | 31 | PASS |
| Fixed quantities | history、initial state、geography、horizon、readout、sample、mask、ground-truth window | PASS |
| 唯一改变量 | 输入 transition 的 future-weather sequence | PASS |
| Matched donor | season-, geography-, and quality-matched | PASS |
| Normalized mean | frozen global z-score space 中的零 | PASS |
| 56/84 / 69/84 | descriptive counts | PASS |
| 84 pairs 是否写成 84 geographic regions | 否 | PASS |

45 个 donor control 的复用没有删除或复制任何 extreme-weather pair。84 对不能解释为
84 个独立 geographic clusters；当前正文没有这样表述。

---

## 7. 世界模型主线与主张边界

### 7.1 当前支持的最强主张

- The state-mediated path responds detectably to supplied future weather.
- Actual weather has greater complete-window predictive fidelity than both
  frozen controls under the matched protocol.
- Together with Q2, the evidence supports a forecast-bearing,
  weather-responsive predictive state.

首句和末句分别使用 matched protocol / frozen matched protocol 进行范围限定。
世界模型主张来自 Q1–Q3 的联合证据，不是 Q3 单独证明的普遍定义。

### 7.2 当前没有越界

| 禁止主张 | 当前状态 |
|---|---|
| Causal effect / causal simulator | 未主张；Limitations 明确否定 |
| Counterfactual correctness | 未主张；Limitations 明确否定 |
| Physical truth / complete physical state | 未主张；Limitations 明确否定 |
| Universal weather grounding | 未出现 |
| Arbitrary weather interventions are valid | 未出现 |
| Extreme-specific enhancement | 未主张；Limitations 明确负结果 |
| Extreme response stronger than ordinary weather | 未出现 |
| Temporal composition / Q4 | 未在 4.4 提出 |
| Non-collapse | 未出现 |
| Q3 alone proves a universal world-model definition | 未出现 |

Hot-dry donor \(\Delta\)Loss interaction 的冻结结果仍为：

- mean \(=0.0004360789\)，约 0.00044；
- geographic-cluster 95% CI
  \([-0.0021624635,0.0031997651]\)，约 \([-0.00216,0.00320]\)；
- 区间跨零。

当前 Limitations 明确写出不支持 extreme-specific enhancement。4.4 只说明样本来自
predeclared extreme-weather stratum，没有把 stratum 来源改写成特异增强证据。

**世界模型主线与主张边界：PASS。**

---

## 8. Figure 3 与 Table 3 职责

### 8.1 Figure 3 事实回归

- Figure 3 PDF：
  `figure_workspace/export/fig3_behavior_v2.pdf`
- SHA-256：
  `bbf0444dd18c5c910e2bd3d3dcadeccb57e28d3b2bfeee930e004545b351c990`

| 检查项 | 终审 |
|---|---|
| Panel (a) state removal 为 primary | PASS |
| Panel (a) \(T\to I\) 为 open/smaller supporting marker | PASS |
| Panels (b,c) 各显示 84 点 | PASS |
| Panels (b,c) 坐标范围一致 | PASS |
| \(y=x\) 上方表示 control MSE 更高 | PASS |
| 56/84 与 69/84 | 由全量冻结行计算的 descriptive counts |
| 手工筛点 / 缺失点 | 无 |
| 新机制、Q4、因果或极端增强主张 | 无 |

Figure 3 文件冻结正确。本终审没有进行美术重审，也不提出重绘建议。

### 8.2 Table 3

| 检查项 | 终审 |
|---|---|
| 五列结构 | PASS |
| Actual / donor / mean 数值 | PASS |
| \(\Delta\)Loss 与 CI | PASS |
| Caption 位于表格下方 | PASS |
| Complete 20-step definition | PASS |
| Control-minus-actual 方向 | PASS |
| Geographic-cluster CI | PASS |
| Descriptive counts | PASS |
| Matched subset 范围 | PASS |
| 与 Table 1 作严格排名 | 否 |
| Booktabs、无竖线 | PASS |
| 无 resizebox/scalebox/negative vspace | PASS |

### 8.3 三者分工

| 载体 | 当前职责 | 终审 |
|---|---|---|
| 正文 | 解释两层证据及有限世界模型含义 | PASS |
| Figure 3 | 展示全部逐 pair 分布与方向 | PASS |
| Table 3 | 给 exact aggregate、CI 和描述性 count | PASS |

三者互补，不逐格重复，也没有数值或主张冲突。

---

## 9. 中英文写作质量

### 9.1 英文

- 首句直接、专业，避免重新提问；
- 两个 control 的定义被压缩为一条句子；
- response statistic 与 fidelity estimand 使用不同术语；
- 结尾使用 `under the frozen matched protocol`，范围清楚；
- 没有内部审计、gate、checkpoint 或宣传语气；
- 7 句、约 178–179 词，信息密度高但自然可读。

### 9.2 中文

`MANUSCRIPT_ZH_FULL.md` 与 `MANUSCRIPT_ZH.md` 使用：

- “逐 minicube 掩膜平均绝对预测差”对应 output response；
- “完整 20 步预测窗口上的掩膜损失/完整窗口保真度”对应 fidelity；
- “支持一个承载预测且响应天气的预测状态”对应 supports；
- 没有翻译为因果响应、物理真实性或“证明世界状态”。

四份文本在审计区间的数字、证据顺序、术语和主张强度一致。

**中英文质量与镜像：PASS。**

---

## 10. 冻结回归

### 10.1 审计开始与结束文件 SHA-256

| 文件 | 开始 SHA-256 | 结束 SHA-256 | 判断 |
|---|---|---|---|
| `paper/main.tex` | `3fa2fe271fcc77f7e3cd9c77f095408ed9e514106cc952ca62e09e6cb913a51f` | `3b26e4e63e4a027bbc212512f3771a6a540c8c37923cefe15da54fc966ace23d` | **并行外部改动** |
| `MANUSCRIPT_ZH_FULL.md` | `ed606a806110d4c85a5d3243a052d3f3f4238d40b34588e6d14c19f9ef906ee8` | `47d9c3b47c50c009f4bcff5ea92eb098c07af024ca391a134a85e1f3bcab72eb` | **并行外部改动** |
| `MANUSCRIPT.md` | `3e59a8f05f5e320cfe01f6c48c8bb2f646fb54e74582de918feb9a62548afac6` | `e960f5207eabce2b514996d1e07fc77cbd519e0f52a7dc922eae192bed8628e4` | **并行外部改动** |
| `MANUSCRIPT_ZH.md` | `4867fad7c8d4da43be3ce468e2a8e8458a96328cfd74c2d3023baef0ce200e33` | `ecc76d79e1b45ed860a9bdec3d3961c91b8fe589ef5a2ceb34c16691d125b19a` | **并行外部改动** |
| `paper/main.pdf` | `71a9082ec742bb1a4fa9009d5ba73adaff4f04adc310f9bd9b36d622a1e47caa` | `82345e60828d5b79c45ac0648215834f747de6bd8819e8bf5b629ceeba6212d0` | 由并行 Table 1 改动重新编译 |
| `paper/main.log` | `e78b41ad919ddfb22b0925bb7b52cb8391ec9983c87d83224ae28ece57a0cd55` | `22c40ab142068ac1e5bf018fa0f4e1814d8f1b714899fa34a96df95cb975dcd8` | 由并行重新编译改变 |
| `paper/main.aux` | `40f1d7bee22991f4f5efaa055fe3ba6131bfa5a6d0c0ab78bf1524564f4d74e2` | 同左 | UNCHANGED |
| Q3 frozen JSON | `9dae43b9a8a4fcdf0a73ef91daa58c189a88e769541ce295046cd0e938497041` | 同左 | UNCHANGED |
| `results_ledger.json` | `d1f8ec7d7a51fae87afc8ba9dbc27905c6816434dc5554980d2e7c2eb472c4b2` | 同左 | UNCHANGED |
| Figure 3 PDF | `bbf0444dd18c5c910e2bd3d3dcadeccb57e28d3b2bfeee930e004545b351c990` | 同左 | UNCHANGED |

### 10.2 局部区块与图表 SHA

| 对象 | SHA-256 | 回归 |
|---|---|---|
| Abstract | `d067709e98b84830d0c5a3cd78ac1f51904e5a42ac0b70abb993186ab64721ab` | FROZEN / UNCHANGED |
| Introduction | `d171277066f1ce281947278340568e3867ad05d1e881eabbe3cb5ef2a54a24c9` | FROZEN / UNCHANGED |
| Section 3 | `b054a42ed0783ad8bfbfa731bef5137cde11b68a58f1048ce12ad14fc4dbdf7d` | FROZEN / UNCHANGED |
| Section 4.1（含 Table 1） | `9feea977ba80119b27150811ca2cb50471f7bf0c8380d7e2aad95466cf8b5f45` → `d1c99173944c16378dd4e18800d3ed38ca7aa5c990938d517a330d931d5eedbe` | **并行外部改动；非 4.4** |
| Section 4.2 | `1255639a23e12090bece746b81f879ac3adcaa3af789d018adb22c3898666740` | FROZEN / UNCHANGED |
| Section 4.3 | `393750e4bb4f8e23703ebac4dd0ccd510257e5b62f00b216a32fe15b9a5a9d3a` | FROZEN / UNCHANGED |
| Section 4.4 | `2f9326e7ea63a6622f3e84e3c7d0f1e68133a127843a8ac10ade429a8082bff5` | 审计对象 / UNCHANGED |
| Table 1 body | `e138d52fbfb8c374a48cd6342d8cc5b53a4f95773e228805092b4501dedbdf36` → `f7a14cd38d187a25c41bc17ac08181870f3bf837def01fb80298ed8fdbbcb02e` | **并行外部改动；非 4.4** |
| Table 2 body | `a372f2ae9fa3ce9d80298fee89453e1565e0eeabc269e671537baad42ebb069b` | FROZEN / UNCHANGED |
| Table 3 environment | `f2f9dd7ec9f212ce132d7e597d2be04085b54d9979327783d81eaacc552dc55d` | UNCHANGED |
| Table 3 tabular | `c33059fe7767b658cc70d193e83567ce34053f9d153e815dcd84122b48c8d991` | UNCHANGED |
| Figure 1 environment | `a977039948dafba50f4c6117fb41827c284d497c4ad3a80f2d1b0635fe7439ee` | FROZEN / UNCHANGED |
| Figure 2 environment | `4a78d8fc2859071a5747fc5c0bebfa90b15ca6c61e9e050ae528dd304b9be256` | FROZEN / UNCHANGED |
| Figure 3 environment | `bb50e15a2b30fa1625d7f2981454607a49f2df500937974d9cc35640f398dad6` | FROZEN / UNCHANGED |

局部回归证明并行变更仅落在 Section 4.1 内的 Table 1 及相应镜像/编译产物：

- Section 4.4、Table 3、Figure 3 环境和 Figure 3 PDF 均未变化；
- Section 3、4.2、4.3、Table 2、Abstract、Introduction 均未变化；
- Q3 JSON、ledger 和 Figure 3 drawing script 均未变化；
- 本审计本身只写入本报告。

因此并行变更不构成 4.4 回退，但违反“Table 1 已冻结”的全篇工作流假设。主监督
窗口应以独立 Table 1/4.1 审计决定保留或回退；本报告不修改或裁决该并行内容。

---

## 11. 编译与 PDF

### 11.1 编译日志

| 检查项 | 结果 |
|---|---:|
| PDF generated | PASS |
| 总页数 | 9 |
| LaTeX errors | 0 |
| Undefined references | 0 |
| Undefined citations | 0 |
| Multiply-defined labels | 0 |
| Overfull boxes | 0 |
| Underfull diagnostics | 8，非阻塞 |

8 条 underfull 包含 7 个 hbox 和 1 个 vbox。它们没有造成 4.4、Figure 3 或
Table 3 的裁切、越界或阅读破坏，按任务要求不升级。

### 11.2 页面位置与几何

| 对象 | 页面 | 状态 |
|---|---:|---|
| Section 4.4 标题与开场 | 5 | 完整 |
| 4.4 control 定义和结果段 | 6 | 完整 |
| Figure 3 | 7 | 完整、可读、无重叠 |
| Table 3 | 8 | 完整、无裁切；靠近 References |
| References | 8–9 | 正常 |

在并行 Table 1 扩展后的当前 PDF 中，Figure 3 的可见内容约位于第 7 页
\(y=376.1\)–622.8 pt；Conclusion 约从 \(y=646.0\) pt 继续，二者没有重叠。
Figure 3 的 panel axis labels、56/84、
69/84 和 caption 均可从 PDF 提取。

Table 3 caption 位于表体下方；其下方至 References 标题存在间隔。当前阅读顺序
不是最紧凑布局，但可以恢复且不违反科学或格式契约。

**编译与 PDF：PASS。**

---

## 12. 质量评分

评分标准：1=明显不达标；3=可用但需要修改；4=投稿成熟；5=高度成熟。

| 维度 | 分数 / 5 | 判断 |
|---|---:|---|
| AAAI 结果结构 | **4.9** | 结论—协议—两层证据—有限解释完整 |
| 首句力度 | **4.9** | 直接回答 Q3，并明确 matched-protocol 范围 |
| Output response / fidelity 层级 | **5.0** | 观察量、解释和统计判据清楚分离 |
| 统计表达 | **5.0** | 数值、方向、CI 类型、sample/subset 均准确 |
| 世界模型主线 | **4.9** | 与 Q2 联合支持 weather-responsive predictive state |
| Claim–evidence 对齐 | **5.0** | 无因果、反事实、物理或极端增强越界 |
| 英文自然度 | **4.8** | 专业紧凑，无内部记录语气 |
| 简洁度 | **4.8** | 7 句、约 178–179 词，职责清楚 |
| Figure / Table / 正文分工 | **4.7** | 科学分工清楚；Table 3 位置留作全篇 layout gate |
| 中英文一致性 | **5.0** | 四份审计区间同步，中文未增强主张 |
| 与冻结 4.1–4.3 的一致性 | **4.9** | 达到相同结果段纯度和专业度 |
| **平均分** | **4.9 / 5.0** | **达到冻结标准** |

---

## 13. Critical / Major / Minor

### Critical（0）

未发现。

### Major（0）

修改前的 M1、M2、M3 均已关闭。M3 以全篇最终 layout gate 形式保留，不构成
Section 4.4 Major。

### Minor（0）

未发现需要在 4.4 冻结前继续修改的局部写作、证据、镜像、表格或编译问题。

审计期间的 Table 1 并行改动属于 4.4 范围外的冻结回归告警，不计入本节
Critical/Major/Minor；它必须由主监督窗口单独处理。

---

## 14. 冻结判断

当前 Section 4.4 满足全部冻结条件：

- Critical = 0；
- Major = 0；
- 平均分 \(4.9\ge4.0\)；
- Q3 数值与 estimand 全部准确；
- forecast-output response 与 forecast-window fidelity 清楚分层；
- 两个 geographic-cluster CI 均排除零；
- 主张没有越过 frozen matched protocol；
- 4.4、Table 3、Figure 3 状态和 Q3 相关 Conclusion 在四份文本中同步；
- Figure 3/Table 3/正文职责清楚；
- 编译和 PDF 无阻塞；
- Table 3 页面位置已正确降级为全篇最终 layout gate。

因此最终状态为：

# SECTION4_4_4_FROZEN

后续不得借 Section 1、Section 2、全篇审计或最终排版重新打开 4.4 的 Q3 数值、
complete-window estimand、response/fidelity 层级或证据边界。Table 3 的页面位置
只允许在最终全篇 layout gate 中通过合规浮动调整处理，不得使用负间距、极小字号、
resizebox、数据修改或 Figure 修改。

本审计不启动 Section 1、Section 2 或全篇审计，等待主监督窗口确认。
在主监督窗口确认并行 Table 1 改动之前，不应宣告**全篇**冻结；这一告警不改变
本报告的 `SECTION4_4_4_FROZEN` 局部结论。
