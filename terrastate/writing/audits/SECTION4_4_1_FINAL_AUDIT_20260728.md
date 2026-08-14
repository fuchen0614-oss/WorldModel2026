# TerraState AAAI-27 Section 4.1 独立终审

**审计日期：** 2026-07-28  
**审计性质：** 只读写作、事实、双语与表格格式终审  
**权威正文：** `paper/main.tex`  
**中文主镜像：** `MANUSCRIPT_ZH_FULL.md`  
**审计范围：** Section 4.1、Table 1--3 的 AAAI 格式，以及 4.1 与
4.2--4.4 的必要接口  

## 1. 最终结论

## SECTION4_4_1_FROZEN

当前 Section 4.1 已达到正式 AAAI 方法论文实验设置的结构和表达要求，可以冻结。
它以清楚的五段顺序建立实验契约：

> questions → dataset/protocol → metrics/statistical units →
> comparison purpose → minimal implementation/model selection

4.1 正确地把 Q1 定位为 forecasting prerequisite，把 Q2/Q3 定位为同一最终模型
上的内部性质检验；没有把论文写成 benchmark，也没有把 Q2/Q3 写成重新训练的普通
ablation。当前实现段已经从工程日志收敛为合理的最小信息集合。

作者最新确认的训练身份在英文正文、完整中文镜像和两个简版 Markdown 镜像中一致：
Q1--Q3 使用同一个完成 40 epochs / 14,880 updates 完整训练协议的最终模型。
当前 4.1 中不存在 11,904 或 boundary80 表述。

旧 `evidence_workspace/results_ledger.json` 与旧
`METHOD_3_3_FINAL_AUDIT_20260728.md` 仍保存 11,904/boundary80 历史身份。依据本轮
作者明确的事实优先级，这些只构成**待同步的历史记录**，不构成当前 4.1 的事实错误，
也不计入 Critical/Major/Minor。

### 问题计数

| 等级 | 数量 | 结论 |
|---|---:|---|
| Critical | **0** | 无事实、统计、训练身份或主张阻断 |
| Major | **0** | 无结构、双语或 AAAI 表格格式问题 |
| Minor | **1** | 一处不影响理解的英文措辞精化项 |

平均质量评分：**4.7 / 5.0**。

---

## 2. 审计基线与读取范围

已核对：

1. `paper/main.tex` 当前 Section 4.1、Table 1--3 及 4.2--4.4 接口；
2. `MANUSCRIPT_ZH_FULL.md` 对应完整中文；
3. `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md` 对应 4.1 镜像；
4. `SECTION4_AAAI_PRE_REVISION_AUDIT_20260728.md`；
5. `SECTION4_4_1_REVISION_LOG_20260728.md`；
6. `SECTION4_FINAL_AAAI_AUDIT_20260728.md`；
7. `SECTIONWISE_WRITING_ROADMAP.md`；
8. `EXPERIMENTS_RESULTS_AAAI_WRITING_AUDIT.md`；
9. `evidence_workspace/results_ledger.json`；
10. `vendor/AuthorKit27/AuthorKit27/AnonymousSubmission2027.tex`；
11. `METHOD_3_2_FINAL_AUDIT_20260728.md`；
12. `METHOD_3_3_FINAL_AUDIT_20260728.md`；
13. `METHOD_3_4_FINAL_AUDIT_20260728.md`；
14. 当前 `paper/main.log` 与 `paper/main.pdf`。

审计时当前文件 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `9fbdcecd6bb9c633061a8060bf6a90188a36706774e4d07421ef968f5e4ec76e` |
| `MANUSCRIPT_ZH_FULL.md` | `50051d4ed77e424248e6e982f8a8820f1a9f3ea52df89757898021b1104fc4a4` |
| `MANUSCRIPT.md` | `8458b4f7f31d7d7818fc813017dfa5b2ff08861da0d49dfda2c7b5826939e7fb` |
| `MANUSCRIPT_ZH.md` | `b4ca861a423be7b19df1076d6d5b29896e026e86ad336f61b0cb98920abc7f94` |
| `paper/main.pdf` | `794f63b490410ab9d96abfb101542bd2455e7b53afb8452f2507672931d9ac5f` |
| `paper/main.log` | `69dc854b70a445daae3ecd76ce576d7a9a39eb87fba0eedd9903f766abc1c0ea` |

---

## 3. 逐段反向提纲

| 区块 | 当前唯一职责 | 首句与段落纯度 | 终审 |
|---|---|---|---|
| Evaluation questions | 定义一个预测前提和两个内部性质；固定同一最终模型与无重训练身份 | 首句直接建立实验逻辑；列表并行、无结果预告 | **PASS** |
| Dataset and protocol | 定义 GreenEarthNet、输入/预测窗口、空间规格、OOD-t 与选模隔离 | 首句明确 common evaluation setting；只承担协议职责 | **PASS** |
| Metrics and statistical units | 区分 Q1 dataset-level 指标、Q2 两种 estimand 和 Q3 cluster-aware window loss | 首句准确说明统计单位分层；信息密但均为必要契约 | **PASS** |
| Comparison purpose | 说明 Table 1 只建立 Q1 forecasting context，并与 Q2/Q3 分工 | 采用“目的 → 方法类别 → 证据职责”顺序，不再是 baseline 清单 | **PASS** |
| Implementation and model selection | 给出最少训练配置、最终模型身份与 validation-only selection | 三句完成复现核心与选择边界；无 checkpoint、阶段或内部审计语言 | **PASS** |

### 3.1 五段顺序

当前严格遵循：

1. questions；
2. dataset/protocol；
3. metrics/statistics；
4. comparison purpose；
5. minimal implementation/model selection。

没有出现设置与结果交叉、实现信息前置或在 metric 之前解释结果的情况。

### 3.2 工程日志与 AI 式表达

未发现：

- checkpoint 路径、SHA、内部阶段、boundary、运行时 tensor shape；
- training log、gate、audit、qualifier、candidate 等内部审计语气；
- 空泛的 superior、novel、remarkable、comprehensive；
- 逐项复述 Section 3 的架构或训练身份；
- 提前复述 4.2--4.4 的结果数值。

4.1 可以在不依赖 Figure 1--3 的情况下独立理解。

---

## 4. 指定措辞终审

| 表达 | 判断 | 理由 |
|---|---|---|
| `one forecasting prerequisite and two internal properties` | **PASS** | 准确概括 Q1 与 Q2/Q3 的层级，不把 Q1 单独写成世界模型充分证据 |
| `alter only its frozen forward computation` | **PASS WITH MINOR STYLE NOTE** | 科学含义清楚：同一模型、无重训练、只改 forward intervention；但英语略压缩，可选改为 `alter only the frozen model's forward computation` |
| Comparison purpose 的正面作用说明 | **PASS** | 先说明 forecasting comparisons 为 Q1 建立 performance context，再说明 Q2/Q3 承担内部性质证据 |
| `rather than by table rank` | **PASS / 建议保留** | 不是过度防御，而是用最短措辞阻止把 Table 1 排名误当作 load-bearing/weather-response 证据 |
| implementation 段 | **PASS** | 7.18M、AdamW、40 epochs、14,880 updates、batch 64、non-\(q\) LR 与 selection rule 构成合理最小集合 |
| validation-only selection | **PASS** | `selected solely by validation forecasting performance` 明确；dataset 段又明确 OOD-t 与 Q2/Q3 不参与选择 |

唯一 Minor 是上述 `alter only its frozen forward computation` 的惯用性问题。它不造成
歧义，不要求在进入 4.2 前修改。

---

## 5. 科学事实与统计口径核对

### 5.1 Dataset

| 核对项 | 当前 4.1 | 判定 |
|---|---|---|
| 30 个五日 composites | 明确 | **PASS** |
| 空间大小 | \(128\times128\) | **PASS** |
| 地面采样 | 20 m | **PASS** |
| 历史窗口 | 前 10 个 composites | **PASS** |
| 预测窗口 | 后 20 个 composites | **PASS** |
| OOD-t | 1,904 minicubes | **PASS** |
| 附加输入 | aligned meteorology、cloud/quality masks、static geography | **PASS** |

### 5.2 Q1

| 核对项 | 判定 |
|---|---|
| \(R^2\) | **PASS** |
| RMSE | **PASS** |
| NSE | **PASS** |
| absolute prediction bias | **PASS** |
| \(\mathrm{RMSE}_{25}\) | **PASS** |
| 定义为前 25 forecast days | **PASS** |

### 5.3 Q2

| 统计对象 | 当前表达 | 判定 |
|---|---|---|
| Official \(\Delta R^2\) | full 与 intervention 的 dataset-level score 差 | **PASS** |
| Paired mean | mean per-minicube paired \(\Delta R^2\) | **PASS** |
| Interval | paired-bootstrap 95% CI | **PASS** |
| 三者分离 | 明确使用 `separately from` | **PASS** |

未把 paired CI 误配给 official dataset-level delta。

### 5.4 Q3

| 核对项 | 当前表达 | 判定 |
|---|---|---|
| Loss unit | masked MSE | **PASS** |
| 时间范围 | complete 20-step forecast window | **PASS** |
| 不确定性单位 | geographic clusters | **PASS** |
| matched-control dependence | cluster resampling preserves dependence | **PASS** |

没有把 Q3 写成单独 \(h=20\) endpoint，也没有将 fidelity 写成因果或物理真实性。

---

## 6. 训练身份核对

本轮采用作者最新确认事实，不从旧 audit/ledger 恢复旧身份。

| 核对项 | 当前 4.1 | 判定 |
|---|---|---|
| 完整训练长度 | 40 epochs | **PASS** |
| 完整更新数 | 14,880 updates | **PASS** |
| Q1--Q3 模型 | 同一个完成完整训练的最终模型 | **PASS** |
| Q2/Q3 是否重训练 | 否；只改变冻结 forward computation | **PASS** |
| Optimizer | AdamW | **PASS** |
| Global batch | 64 | **PASS** |
| Non-\(q\) learning rate | \(3\times10^{-5}\) | **PASS** |
| 选模依据 | validation forecasting performance only | **PASS** |
| OOD-t 参与选模 | 否 | **PASS** |
| Q2/Q3 结果参与选模 | 否 | **PASS** |
| 11,904/boundary80 是否出现在当前 4.1 | 否 | **PASS** |

### 6.1 历史记录同步说明

以下文件仍含旧身份：

- `evidence_workspace/results_ledger.json`；
- `METHOD_3_3_FINAL_AUDIT_20260728.md`。

这两处属于历史 provenance/audit 状态，与作者本轮明确覆盖后的当前训练事实不一致。
按照本轮约束：

- 不修改这些文件；
- 不用它们否定当前 4.1；
- 不将其计为 4.1 的 Critical、Major 或 Minor；
- 后续若做全局 provenance 整理，应另开同步任务并保留历史可追溯性。

---

## 7. 世界模型主线与章节职责

| 关系 | 当前 4.1 是否建立 | 判定 |
|---|---|---|
| Q1 是 forecasting prerequisite | 明确 | **PASS** |
| Q2 检验 state-mediated contribution | 明确 | **PASS** |
| Q3 检验 future-weather response fidelity | 明确 | **PASS** |
| Table 1 只定位 forecasting utility | Comparison purpose 明确限定 | **PASS** |
| 内部状态属性由 Q2/Q3 同模型干预支持 | 明确 | **PASS** |
| 不把论文写成 benchmark | 无排名或 SOTA 叙事 | **PASS** |
| 不把 Q2/Q3 写成 retrained ablation | 明确无 retraining | **PASS** |
| 遥感 + 世界模型 + 可检验预测状态主线 | 数据、状态性质和天气响应三者连接完整 | **PASS** |

4.1 没有加入 Q4/composition，也没有让 Table 1 的输出性能替代 Q2/Q3 的内部证据。

---

## 8. Table 1--3 AAAI-27 compliance

### 8.1 官方要求

AAAI-27 Author Kit 明确要求：

- table caption 位于表格下方；
- caption 为 10pt Roman；
- table body 原则上 10pt，必要时允许 9pt；
- 不得使用 `\resizebox` 或其他整体缩放命令；
- 可使用 `\tabcolsep` 压缩列间距；
- 内容不得进入 margin 或 gutter。

### 8.2 LaTeX 源检查

| 检查项 | Table 1 | Table 2 | Table 3 |
|---|---|---|---|
| `tabular → caption → label` | **PASS** | **PASS** | **PASS** |
| caption 位于表格下方 | **PASS** | **PASS** | **PASS** |
| `\small` 只包围 table body | **PASS** | **PASS** | **PASS** |
| `booktabs` | **PASS** | **PASS** | **PASS** |
| 无竖线/密集 `\hline` | **PASS** | **PASS** | **PASS** |
| 无 `resizebox/scalebox` | **PASS** | **PASS** | **PASS** |
| 无 negative `vspace/vskip` | **PASS** | **PASS** | **PASS** |
| caption 后紧跟 label | **PASS** | **PASS** | **PASS** |

### 8.3 PDF 字号与版面

当前 `main.pdf` 的 PDF text spans 显示：

- 三张 table caption：`TeXGyreTermesX-Regular`，约 **9.96pt**；
- 三张 table body：约 **8.97pt**；
- 因此 caption 符合 nominal 10pt Roman，body 符合必要时 9pt 的下限；
- Table 1、Table 2 位于 PDF 第 7 页；
- Table 3 位于 PDF 第 8 页；
- 表格和 caption 均在页面/栏宽边界内；
- 未发现表格文字重叠、裁切、margin intrusion 或 gutter intrusion。

几何顺序也与源码一致：

- Table 1 body 底部约 \(y=180.4\)，caption 从 \(y=193.6\) 开始；
- Table 2 body 底部约 \(y=344.4\)，caption 从 \(y=353.8\) 开始；
- Table 3 body 底部约 \(y=373.6\)，caption 从 \(y=387.0\) 开始。

### 8.4 表格科学内容回归

当前表体 SHA-256 与 `SECTION4_4_1_REVISION_LOG_20260728.md` 记录一致：

| Table | 当前 tabular SHA-256 | 判定 |
|---|---|---|
| Table 1 | `e138d52fbfb8c374a48cd6342d8cc5b53a4f95773e228805092b4501dedbdf36` | **UNCHANGED** |
| Table 2 | `a372f2ae9fa3ce9d80298fee89453e1565e0eeabc269e671537baad42ebb069b` | **UNCHANGED** |
| Table 3 | `c33059fe7767b658cc70d193e83567ce34053f9d153e815dcd84122b48c8d991` | **UNCHANGED** |

caption 文案 SHA-256 同样与修订日志一致：

| Table | 当前 caption SHA-256 | 判定 |
|---|---|---|
| Table 1 | `2f0f82661d756fd2673eb02fba825f3e5eaadefdb09a0ad60987b3ab66adb832` | **UNCHANGED** |
| Table 2 | `2690aad11f7a8000b79d14fefacbc130a571f92230eac83673952973a93d9d1b` | **UNCHANGED** |
| Table 3 | `884c9a73d62adf4a93b398a4ffb370a6f4970a1a99559e02cc589d016c55d566` | **UNCHANGED** |

因此数值、行列、CI、方向、reference/破折号和 caption 文案未因格式调整而改变。

### 8.5 标签与引用

当前 `main.aux`：

- `tab:forecast` → Table 1，PDF 第 7 页；
- `tab:q2` → Table 2，PDF 第 7 页；
- `tab:q3` → Table 3，PDF 第 8 页。

无 undefined 或 multiply-defined table reference。

**Table 1--3 AAAI 格式总判定：PASS。**

---

## 9. 中英文与 Markdown 镜像同步

### 9.1 逐项核对

| 项目 | 英文权威稿 | 中文主镜像 | 两个简版镜像 | 判定 |
|---|---|---|---|---|
| 五段顺序 | questions → implementation | 同序 | 同序 | **PASS** |
| Q1--Q3 定义 | 一致 | 同强度 | 一致 | **PASS** |
| 30/10/20 composites、128×128、20 m | 完整 | 完整 | 完整 | **PASS** |
| OOD-t 1,904 | 完整 | 完整 | 完整 | **PASS** |
| Q1 指标 | 完整 | 完整 | 完整 | **PASS** |
| Q2 statistical units | 三类分离 | 三类分离 | 三类分离 | **PASS** |
| Q3 20-step window/cluster | 完整 | 完整 | 完整 | **PASS** |
| 40 epochs / 14,880 updates | 完整 | 完整 | 完整 | **PASS** |
| validation-only selection | 明确 | 明确 | 明确 | **PASS** |
| comparison purpose | 相同职责 | 相同职责 | 相同职责 | **PASS** |
| 世界模型主线强度 | prerequisite + two properties | 同强度 | 同强度 | **PASS** |

中文采用“预测前提”“状态介导贡献”“完整预测窗口”“只依据验证集预测表现”等自然
解释，没有把英文中的 evaluate/support 提升为“证明”，也没有另建一套事实。

### 9.2 范围说明

两个简版 Markdown 镜像在 4.1 之外仍保留较旧的 Section 3/结果呈现内容。本轮只审核
其 4.1 对应镜像，因此不把其余章节历史状态计入本轮问题；当前四份 **4.1 本身**
保持一致。

**中英文 4.1 同步总判定：PASS。**

---

## 10. 4.1 与 4.2--4.4 的接口

| 后续小节 | 4.1 提供的入口 | 是否提前泄露结果 | 判定 |
|---|---|---|---|
| 4.2 Q1 | OOD-t、Q1 metrics、Table 1 comparison purpose | 否 | **PASS** |
| 4.3 Q2 | state contribution、official/paired estimand、paired CI | 否 | **PASS** |
| 4.4 Q3 | actual/donor/mean 问题、20-step masked MSE、cluster uncertainty | 否 | **PASS** |

4.1 只建立共同契约，4.2--4.4 负责实际结果。章节职责分离清楚。

---

## 11. 编译与 PDF 回归

当前构建状态：

| 项目 | 结果 |
|---|---|
| PDF | `paper/main.pdf` |
| 页数 | **9** |
| PDF 与 main.tex 时间关系 | PDF/log 在当前 main.tex 后约 11 秒生成，构建对应当前源 |
| LaTeX error | **0** |
| Undefined citation | **0** |
| Undefined reference | **0** |
| Multiply-defined label | **0** |
| Overfull hbox/vbox | **0** |
| Underfull hbox | **7** |
| Underfull vbox | 未在当前筛查中形成阻断 |

7 个 underfull 均未造成裁切或越栏，也不构成 4.1 的写作或格式问题。当前 PDF 可见
4.1 的 14,880-update final-model identity，表格顺序和引用正常。

---

## 12. 质量评分

评分标准：1=明显不达标；3=基本可用；4=投稿成熟；5=高度成熟。

| 维度 | 分数 | 判断 |
|---|---:|---|
| AAAI 结构 | **5.0** | 五段顺序清楚，公共实验契约先行 |
| 首句力度 | **4.5** | 直接给出 prerequisite/properties 层级；可读性强 |
| 段落单一职责 | **5.0** | 五个区块职责互不混杂 |
| 科学契约完整性 | **5.0** | dataset、metric、estimand、selection 与模型身份完整 |
| 世界模型主线连接 | **4.8** | Table 1 与 Q2/Q3 的证据职责分离明确 |
| claim--evidence 对齐 | **5.0** | 无 SOTA、因果、composition 或内部性质越界 |
| 英文自然度 | **4.3** | 整体自然；仅 frozen-forward 句有轻微压缩感 |
| 简洁度 | **4.7** | implementation 已显著压缩且未损失契约 |
| 中英文一致性 | **4.8** | 四份 4.1 数字、顺序和强度一致 |
| Table 1--3 官方格式 | **5.0** | caption、字号、顺序、作用域和版面均合规 |
| 与冻结 Section 3 的质量一致性 | **4.8** | 达到相同的段落纯度与术语克制 |
| **平均分** | **4.7 / 5.0** | **达到冻结目标** |

---

## 13. Critical / Major / Minor 清单

### Critical（0）

未发现。

### Major（0）

未发现。

### Minor（1）

**M1：一处英语可选精化，不影响冻结。**

- **位置：** `paper/main.tex:484--486`；
- **当前：** `Q2 and Q3 alter only its frozen forward computation and require no retraining`；
- **判断：** 事实准确、可理解，但 `its frozen forward computation` 略显压缩；
- **可选最小修复：** `Q2 and Q3 alter only the frozen model's forward computation and require no retraining`；
- **是否必须在进入 4.2 前修复：** 否；
- **是否改变事实或证据：** 否。

### 不计数的历史同步项

旧 ledger 和旧 3.3 audit 中的 11,904/boundary80 身份应由独立 provenance
同步任务处理。本轮禁止修改，且作者已明确它们不用于否定当前 4.1。

---

## 14. 冻结判断

当前 4.1 满足：

- 平均分不低于 4.0；
- Critical = 0；
- Major = 0；
- 14,880 final-model identity 清楚且四份 4.1 同步；
- validation-only selection 与干预隔离清楚；
- Table 1--3 符合 AAAI-27 caption、字号和缩放规则；
- 没有修改或越过 Section 3、Q1--Q3 数值及证据边界。

因此最终状态为：

# SECTION4_4_1_FROZEN

可以进入 Section 4.2 修改。后续不得恢复 11,904/boundary80，不得借 4.2 修改重开
4.1 的训练身份、统计单位或 Table 1--3 格式。
