# TerraState AAAI-27 Section 4.2 独立终审

**审计日期：** 2026-07-28  
**审计对象：** Section 4.2 “Forecasting Performance under Temporal Shift”、
Table 1 及四份中英文文本  
**审计性质：** 只读的 AAAI 主结果写作、事实、主张边界与格式终审  
**权威正文：** `paper/main.tex`  
**目标 venue：** AAAI-27 Main Technical Track  

## 1. 最终结论

# SECTION4_4_2_FROZEN

当前 4.2 已达到正式 AAAI 方法论文主结果段的结构与论证要求，可以冻结。一个约
110 词的五句段落依次完成：

1. 直接回答 Q1；
2. 报告 OOD-t 样本量及两个核心指标；
3. 解释前 25 个预测日的较低误差；
4. 透明呈现并非统一领先的 mixed metric profile；
5. 将 Q1 限定为 Q2/Q3 内部状态检验的 forecasting prerequisite。

段落既没有回避 Table 1 中的不利指标，也没有为非领先表现长篇辩护。它没有使用
SOTA、competitive、non-inferiority 或等价性语言，没有把 Table 1 写成世界模型
属性的证明，也没有用 Q2/Q3 结果反向替 Q1 辩护。

`most favorable relative dimension in the table` 的事实含义由 Table 1 支持：
\(\mathrm{RMSE}_{25}=0.082\) 是 TerraState 在所列指标中的最有利相对表现。该表达
不声称逐列最优或统计等价。它可以通过终审，仅保留一项不阻塞冻结的英文自然度
Minor。

### 问题计数

| 等级 | 数量 | 结论 |
|---|---:|---|
| Critical | **0** | 无事实、证据或主张边界错误 |
| Major | **0** | 无结构、表格或镜像同步问题 |
| Minor | **1** | 一处可选英文措辞精化，不影响理解或冻结 |

平均质量评分：**4.7 / 5.0**。

---

## 2. 审计基线与读取范围

已核对：

1. `paper/main.tex` 当前 4.1、4.2、4.3 及 Table 1；
2. `MANUSCRIPT_ZH_FULL.md` 当前 4.2；
3. `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md` 当前 4.2 与 Table 1；
4. `SECTION4_4_2_AAAI_AUDIT_20260728.md`；
5. `SECTION4_4_2_REVISION_LOG_20260728.md`；
6. `SECTION4_4_1_FINAL_AUDIT_20260728.md`；
7. `SECTION4_AAAI_PRE_REVISION_AUDIT_20260728.md`；
8. `SECTION4_FINAL_AAAI_AUDIT_20260728.md`；
9. `evidence_workspace/results_ledger.json`；
10. `EXPERIMENTS_RESULTS_AAAI_WRITING_AUDIT.md`；
11. 当前 `paper/main.log`、`paper/main.aux` 和 `paper/main.pdf`。

本轮采用作者最新确认的事实优先级：

- Q1--Q3 使用同一个最终 TerraState 模型；
- 最终模型完成 40 epochs / 14,880 updates；
- 11,904/boundary80 已失效；
- 4.1 已冻结，本轮没有重开其训练身份、统计单位或模型选择合同。

历史 ledger 中的 11,904/boundary80 只视为待同步历史记录，不用于否定当前 4.2，
也不计入问题数量。

### 2.1 当前 SHA-256 基线

| 对象 | SHA-256 |
|---|---|
| `paper/main.tex` | `f6859f34c0585715bb59d6ebf4bc8fa96640874b3f030c0a931252c9cf4f6aa3` |
| 当前 Section 4.2 区块 | `1255639a23e12090bece746b81f879ac3adcaa3af789d018adb22c3898666740` |
| Table 1 完整 `table*` 环境 | `ec5b1dd99126d54306894f5263c9f1dad6247ae2c805899fc00e0d75c2f3cfce` |
| Table 1 `tabular` | `e138d52fbfb8c374a48cd6342d8cc5b53a4f95773e228805092b4501dedbdf36` |
| Table 1 caption 正文 | `2f0f82661d756fd2673eb02fba825f3e5eaadefdb09a0ad60987b3ab66adb832` |
| `MANUSCRIPT_ZH_FULL.md` | `c65ca3f9f6ade20951bf129945c6b0e938530e185755969c569f99df09c80b4c` |
| `MANUSCRIPT.md` | `01a89e1133509878ad7743a31a221399ce7d2f0c1be4d05aa51f25fb61e064e2` |
| `MANUSCRIPT_ZH.md` | `47899d628bf3a6c7e6d230e7888230a57254e72840d99766670fd2dccb434d2e` |
| `paper/main.pdf` | `d1e4b8dded5d477a6bbd89d04b00875c8051b0edd61769a0aa1630e0c721fa6d` |
| `paper/main.log` | `623b0edb3267d7293ada03640fd7875f1f64618307d80ab90d1df1edc88c9164` |

---

## 3. 逐句终审

当前 4.2 为一个段落、五句话；修订日志采用的 LaTeX-aware 计数为约 110 个英文词。

### 3.1 句 1：Q1 结论

> `TerraState retains useful forecasting skill on the GreenEarthNet OOD-t
> split under temporal distribution shift.`

| 检查项 | 判断 |
|---|---|
| 是否直接回答 Q1 | **PASS**；首句即给出 useful-skill 结论 |
| 是否准确限定数据与 split | **PASS**；GreenEarthNet、OOD-t、temporal distribution shift 均明确 |
| `retains useful forecasting skill` 是否受支持 | **PASS**；正 \(R^2\)、有限 RMSE 与完整 1,904-minicube OOD-t 结果支持这一限定表述 |
| 是否暗示 competitive/SOTA | **否** |
| 是否像表格导航 | **否**；Table 引用留给下一句 |

该句结论先行、范围明确，是成熟 AAAI 主结果开场。

### 3.2 句 2：核心数字

> `Across 1,904 minicubes, it obtains R²=0.56935 and RMSE=0.15059
> (Table 1).`

| 检查项 | 判断 |
|---|---|
| 样本量 | **PASS**：1,904 |
| \(R^2\) | **PASS**：0.56935 |
| RMSE | **PASS**：0.15059 |
| Table 1 引用 | **PASS**；作为句末证据入口自然 |
| 是否逐格复述 | **否**；只保留两个核心 Q1 指标 |

该句数字选择克制，没有重复 NSE、bias、RMSE25 和参数量的完整表格内容。

### 3.3 句 3：短时域表现

> `Its RMSE25=0.082 indicates low error over the first 25 forecast days and
> represents TerraState's most favorable relative dimension in the table.`

| 检查项 | 判断 |
|---|---|
| \(\mathrm{RMSE}_{25}=0.082\) | **PASS**；是冻结值的正确显示精度 |
| 前 25 forecast days | **PASS**；与 4.1 和 Table 1 caption 定义一致 |
| `low error` | **PASS WITH TABLE SCOPE**；0.082 位于表中最低的一组短时域误差值附近 |
| `most favorable relative dimension` 的事实性 | **PASS**；RMSE25 是 TerraState 相对排名最有利的指标 |
| 是否声称逐列最优 | **否**；没有使用 best、outperforms 或 lowest |
| 是否暗示统计等价 | **否** |
| 英文自然度 | **PASS WITH MINOR STYLE NOTE**；`relative dimension` 略抽象，但含义明确 |

该句不是自我宣传或内部审计语言。它透明指出 TerraState 的相对强项，同时避免
“nearly matches”“competitive with the best”等未经检验的表达。

如作者未来做纯语言精化，可选的最小替代为：

> `Its RMSE25=0.082 indicates low error over the first 25 forecast days and
> is TerraState's strongest relative result in Table 1.`

该替代不改变事实或主张强度；**不修改也可以冻结**。

### 3.4 句 4：Mixed metric profile

> `The overall profile is mixed: RMSE=0.151 lies within the numerical range
> of several learned forecasters, whereas its R² and NSE are not the largest
> values in the table.`

| 检查项 | 判断 |
|---|---|
| `mixed profile` 是否自然 | **PASS**；直接、透明且不防御 |
| RMSE \(=0.151\) 的范围判断 | **PASS**；表中 learned forecasters 覆盖 0.140--0.160，且多行显示 0.150/0.160 |
| \(R^2\) 不是最大值 | **PASS**；Table 1 最大显示值为 0.620 |
| NSE 不是最大值 | **PASS**；Table 1 最大显示值为 0.090 |
| 是否暗示统计等价 | **否**；只写 `numerical range`，没有 equivalent/on par |
| 是否过度强调不利结果 | **否**；仅一句完成必要透明披露 |
| 是否需要压缩 | **否**；当前长度和逻辑清楚 |

这一句解决了修改前“选择性只报两个指标”的风险，也没有把差距归因于
predictive-state architecture。

### 3.5 句 5：Q1 → Q2/Q3 接口

> `Q1 therefore establishes the forecasting prerequisite for the
> predictive-state analysis; Q2 and Q3 separately evaluate the same model's
> state contribution and weather response through the controlled
> interventions reported in the following sections.`

| 检查项 | 判断 |
|---|---|
| Q1 的地位 | **PASS**；forecasting prerequisite，不是 world-model sufficient proof |
| Q2 的职责 | **PASS**；state contribution |
| Q3 的职责 | **PASS**；weather response |
| 是否保持同一模型身份 | **PASS**；明确 `the same model` |
| 是否提前泄露结果 | **否**；只声明后续问题职责，没有复述 Q2/Q3 数字或 verdict |
| 句子是否过长 | **可读且可接受**；分号正确分隔 prerequisite 与后续 evidence |
| 是否必须拆句 | **否** |

普通动词 `reported` 出现在 “interventions reported in the following sections”
中，不是被禁止的 `Reported` 表格来源标签。

---

## 4. Q1 冻结事实核对

本轮不重算、不重新选择，以作者确认值为当前最高优先级。

| 项目 | 作者确认精确值 | 当前正文/Table 1 显示 | 判定 |
|---|---:|---:|---|
| OOD-t 样本量 | 1,904 minicubes | 1,904 | **PASS** |
| \(R^2\) | 0.5693493611664086 | 0.56935 / 0.569 | **PASS** |
| RMSE | 0.1505941190915099 | 0.15059 / 0.151 | **PASS** |
| NSE | -0.09865622945212116 | -0.099 | **PASS** |
| \(|\mathrm{Bias}|\) | 0.10082936645631536 | 0.101 | **PASS** |
| \(\mathrm{RMSE}_{25}\) | 0.08204982450297288 | 0.082 | **PASS** |
| 参数量 | 7.18M | 7.18M | **PASS** |

所有正文和表格显示值均为作者确认值在各自显示精度下的正确舍入。当前 4.2 没有
将这些结果重新解释为 SOTA、等价性、non-inferiority 或 negligible accuracy
cost。

---

## 5. 整体写作质量

| 必要信息槽 | 当前是否具备 | 判断 |
|---|---:|---|
| 1. Q1 结论 | 是 | **PASS** |
| 2. 核心数字 | 是 | **PASS** |
| 3. 短时域表现 | 是 | **PASS** |
| 4. Mixed metric profile | 是 | **PASS** |
| 5. Q1→Q2/Q3 接口 | 是 | **PASS** |

### 5.1 AAAI 主结果段成熟度

- **不像内部结果记录：** 没有 checkpoint、gate、qualifier、provenance 或
  audit 语言；
- **没有选择性隐藏主表：** 主动披露 \(R^2\)/NSE 并非最高；
- **没有过度辩解：** 非领先信息只占一句，没有“虽然……但是我们不刷榜”的防御式
  叙述；
- **自信与诚实平衡：** 首句正面回答 Q1，后面透明限定性能轮廓；
- **没有 AI 式空泛表达：** 无 remarkable、comprehensive、superior 等形容词；
- **没有重复句：** 五句话各承担一个独立职责；
- **长度合适：** 约 110 词，位于修改前审计建议的 100--130 词区间；
- **段落数合适：** Q1 是预测前提，一个段落足够，不应扩成两段为结果辩护。

整体结构符合：

> conclusion → key numbers → short-horizon strength → mixed profile →
> prerequisite/evidence bridge

---

## 6. 主张边界与风险词扫描

### 6.1 允许的最强结论

当前 4.2 严格支持：

- TerraState retains useful forecasting skill on GreenEarthNet OOD-t；
- \(\mathrm{RMSE}_{25}=0.082\) 表明较低的前 25 天预测误差；
- Table 1 呈现非统一领先的 mixed metric profile；
- Q1 建立后续内部状态分析的 forecasting prerequisite。

### 6.2 禁止项扫描

对英文权威 4.2、完整中文及两个简版 4.2/Table 1 区间进行语境化扫描：

| 禁止项 | 命中与分类 | 判定 |
|---|---|---|
| SOTA / state of the art | 0 | **PASS** |
| best-performing / uniformly superior | 0 | **PASS** |
| competitive with the best | 0 | **PASS** |
| nearly matches | 0 | **PASS** |
| non-inferior / statistically equivalent | 0 | **PASS** |
| negligible accuracy cost | 0 | **PASS** |
| 将差距归因于 state architecture | 0 | **PASS** |
| Table 1 证明 world model | 0 | **PASS** |
| 其他方法没有 state | 0 | **PASS** |
| 用 Q2/Q3 结果为 Q1 辩护 | 0 | **PASS** |
| Published/Local/Source 表格标签 | 0 | **PASS** |
| `Reported` 来源标签 | 0；英文句 5 的小写 `reported` 是普通谓语 | **PASS** |
| baseline 来源/本地复现/seed/run | 0 | **PASS** |
| 11,904/boundary80 | 0 | **PASS** |
| Q4/composition | 0 | **PASS** |
| 中文“领先” | 只出现在“并非统一领先”的合法否定中 | **PASS** |

没有需要削弱或删除的 Q1 主张。

---

## 7. Table 1 冻结回归

### 7.1 内容 SHA 回归

当前 Table 1 与 `SECTION4_4_2_REVISION_LOG_20260728.md` 的冻结记录一致：

| 对象 | 当前 SHA-256 | 修订日志基线 | 判定 |
|---|---|---|---|
| 完整 `table*` 环境 | `ec5b1dd99126d54306894f5263c9f1dad6247ae2c805899fc00e0d75c2f3cfce` | 同值 | **UNCHANGED** |
| `tabular` 内容 | `e138d52fbfb8c374a48cd6342d8cc5b53a4f95773e228805092b4501dedbdf36` | 同值 | **UNCHANGED** |
| caption 正文 | `2f0f82661d756fd2673eb02fba825f3e5eaadefdb09a0ad60987b3ab66adb832` | 4.1 冻结基线同值 | **UNCHANGED** |

完整环境 SHA 一致同时确认行、列、数值、caption、label 与字号作用域均未变化。

### 7.2 源码与 PDF 格式

| 检查项 | 当前状态 | 判定 |
|---|---|---|
| `tabular → caption → label` | 是 | **PASS** |
| Caption 位于表格下方 | 是 | **PASS** |
| Caption 字体 | PDF 约 9.96 pt、Roman | **PASS** |
| Table body 字体 | PDF 约 8.97 pt，即 nominal 9 pt | **PASS** |
| Booktabs | 使用 | **PASS** |
| 竖线 | 无 | **PASS** |
| `resizebox/scalebox` | 无 | **PASS** |
| Negative spacing | 无 | **PASS** |
| Overfull / margin intrusion | 无 | **PASS** |
| TerraState 强调 | 只加粗方法名 | **PASS** |
| `tab:forecast` 引用 | 正常解析为 Table 1 | **PASS** |

当前 `main.pdf` 共 9 页，Table 1 位于第 7 页。全篇分页明确排除在本轮之外；其位置
不改变 Table 1 的科学内容与格式判定。

### 7.3 两个简版 Markdown

自动逐行核对显示：

- `MANUSCRIPT.md` Table 1：9 行、7 列，九行数值与权威 Table 1 一致；
- `MANUSCRIPT_ZH.md` Table 1：9 行、7 列，九行数值与权威 Table 1 一致；
- `MANUSCRIPT_ZH_FULL.md` Table 1 同样一致；
- 无 Published/Reported/Local/Source 面板、来源列或旧双表结构。

**Table 1 最终判定：UNCHANGED / PASS。**

---

## 8. 中英文与镜像同步

### 8.1 逐句语义

| 信息 | 英文权威稿 | 完整中文 | 英/中简版 | 判定 |
|---|---|---|---|---|
| GreenEarthNet OOD-t temporal shift | 明确 | 明确 | 明确 | **PASS** |
| Useful forecasting skill | `retains useful` | “保留有效预测能力” | 同强度 | **PASS** |
| 1,904 minicubes | 1,904 | 1,904 | 1,904 | **PASS** |
| \(R^2=0.56935\) | 一致 | 一致 | 一致 | **PASS** |
| RMSE \(=0.15059\) | 一致 | 一致 | 一致 | **PASS** |
| \(\mathrm{RMSE}_{25}=0.082\) | 一致 | 一致 | 一致 | **PASS** |
| 前 25 forecast days | 明确 | “前 25 个预测日” | 同义 | **PASS** |
| Most favorable relative dimension | 明确 | “相对最有利的性能维度” | 同义 | **PASS** |
| Mixed profile | 明确 | “并非统一领先的混合轮廓” | 同义 | **PASS** |
| \(R^2\)/NSE 非最大 | 明确 | 明确 | 明确 | **PASS** |
| Q1 prerequisite | 明确 | “预测前提” | 同义 | **PASS** |
| Q2/Q3 职责 | state contribution / weather response | 状态贡献 / 天气响应 | 同义 | **PASS** |

### 8.2 主张强度

中文没有将英文增强为：

- 领先或最优；
- 竞争性最佳；
- 几乎无精度损失；
- 与最佳方法等价；
- Table 1 证明世界模型。

四份文本形成同一条叙事：

> OOD-t 上保留有效预测能力 → 短时域误差是相对强项 → 整体指标不统一领先 →
> Q1 只建立 Q2/Q3 的预测前提。

**中英文与镜像同步：PASS。**

---

## 9. 4.1 与 4.3 接口

| 接口 | 当前 4.2 的处理 | 判定 |
|---|---|---|
| 从 4.1 接入 | 承接 OOD-t、Q1 metrics 和 comparison purpose，不重复训练配置 | **PASS** |
| 4.1 冻结身份 | 不重开 40 epochs/14,880 updates、selection 或 statistical units | **PASS** |
| 向 4.3 过渡 | 只预告 state contribution 与 weather response 的独立检验 | **PASS** |
| 是否提前泄露 Q2/Q3 | 不给数字、CI 或 verdict | **PASS** |
| 是否用 Q2/Q3 为 Q1 辩护 | 否 | **PASS** |

Q1 的职责没有喧宾夺主，也没有过于单薄。它确认预测本身具有使用价值，再把内部状态
属性交给后续干预证据。

---

## 10. 编译与 PDF 只读检查

当前构建对应当前 `main.tex`：

- PDF：`paper/main.pdf`；
- 总页数：9；
- 4.2：PDF 第 5 页；
- Table 1：PDF 第 7 页；
- LaTeX errors：0；
- undefined citations：0；
- undefined references：0；
- overfull boxes：0；
- underfull hboxes：7；
- Table 1 无裁切、重叠或 margin intrusion；
- 4.2 五句话在单栏内阅读顺序正常。

普通 underfull 不影响 4.2 理解或 Table 1 格式，不计入本轮问题。全篇页数与浮动位置
按任务约束不作判定。

---

## 11. 质量评分

评分标准：1=明显不达标；3=基本可用；4=投稿成熟；5=高度成熟。

| 维度 | 分数 | 判断 |
|---|---:|---|
| AAAI 主结果结构 | **4.8** | 五句完成完整结果论证链 |
| 首句力度 | **4.8** | 直接回答 Q1 并限定 OOD-t |
| 数字选择 | **4.8** | 核心数字克制，Table 保留完整汇总 |
| Mixed profile 表达 | **4.7** | 强弱指标同时可见，无等价性暗示 |
| Trade-off 表达 | **4.5** | 诚实但不过度防御；不作机制归因 |
| 世界模型主线接口 | **4.8** | Q1 prerequisite 与 Q2/Q3 职责清楚 |
| Claim--evidence 对齐 | **5.0** | useful-skill 强度与证据严格匹配 |
| 英文自然度 | **4.2** | 整体自然；`relative dimension` 略抽象 |
| 简洁度 | **4.8** | 约 110 词，一个段落，无表格朗读 |
| Table 1 与正文分工 | **4.8** | Table 给 aggregate，正文给结论和取舍 |
| 中英文一致性 | **4.8** | 四份文本与统一 Table 1 同步 |
| 与冻结 4.1 质量一致性 | **4.7** | 达到相同段落纯度和术语克制 |
| **平均分** | **4.7 / 5.0** | **达到冻结标准** |

---

## 12. Critical / Major / Minor

### Critical（0）

未发现事实错误、unsupported central claim、Table 1 回退或致命审稿风险。

### Major（0）

未发现段落结构、证据、双语或表格职责问题。修改前审计的三个 Major 均已解决：

1. 主结果段由约 30 词扩展为结论先行的五句结构；
2. mixed profile 与 performance trade-off 已可见；
3. 两个简版 Markdown 和统一 Table 1 已同步。

### Minor（1）

**M1：`most favorable relative dimension` 可选自然度精化。**

- **精确位置：** 4.2 第 3 句；
- **当前事实：** 正确，且不构成 SOTA、逐列最优或统计等价性主张；
- **局部风险：** `relative dimension` 略抽象，不如 `relative result` 直接；
- **最小替代：**
  `is TerraState's strongest relative result in Table 1`；
- **是否必须修改：** 否；
- **是否影响冻结：** 否；
- **是否需要新证据：** 否。

---

## 13. 冻结判断

当前 4.2 满足：

- 平均分 \(\ge 4.0\)；
- Critical = 0；
- Major = 0；
- Q1 数字、样本量和显示精度正确；
- useful-skill 结论不越过证据；
- mixed profile 透明但不防御；
- Q1→Q2/Q3 接口准确且不泄露结果；
- Table 1 完全未变、格式合规；
- 四份中英文文本和简版 Table 1 同步；
- 没有恢复 11,904/boundary80、Published/Local 或 Q4/composition。

因此最终状态为：

# SECTION4_4_2_FROZEN

后续不得借 4.3/4.4 修改重新打开 4.2 的 Q1 数值、Table 1、主张强度或 4.1
训练身份。若全篇最后统一措辞，可选择性将 `relative dimension` 改为
`relative result`，但这不是冻结前置条件。

