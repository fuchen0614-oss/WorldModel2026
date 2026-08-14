# TerraState `Limitations and Scope` 与 `Conclusion` 独立终审

审计日期：2026-07-28  
审计性质：只读 AAAI 写作、技术一致性、证据边界、双语镜像与 PDF 终审  
权威正文：`paper/main.tex`  
最终判定：**LIMITATIONS_CONCLUSION_FROZEN**

## 1. 最终 verdict

**LIMITATIONS_CONCLUSION_FROZEN**

| 等级 | 数量 | 结论 |
|---|---:|---|
| Critical | **0** | 无事实、证据方向或核心主张错误 |
| Major | **0** | 无结构、主线收束或世界模型身份问题 |
| Minor | **1** | 一项非阻塞的 PDF 分页连续性问题 |
| Optional | **1** | 一项不影响冻结的末句词类精化建议 |

修订后的 Limitations 以三段、150 个英文词完成：

> representation/deployment scope → intervention evidence boundary → external validity

修订后的 Conclusion 以一段、109 个英文词完成：

> problem → method → principal evidence → broader significance

从疲惫但公平的 AAAI 审稿人视角，结尾已经能够一次复述 TerraState 的问题、方法身份、Q1--Q3 证据与更广泛意义。它没有把 TerraState 降格为普通 EO 精度预测器，也没有把“可检验预测状态”写成一套脱离模型设计的评测技巧。

## 2. 审计范围与事实优先级

已完整读取用户指定的全部材料：

1. `paper/main.tex` 的 Abstract、Introduction、Related Work、Method 概览、Section 4.2--4.4、Limitations、Conclusion 及相关 captions；
2. `paper/main.pdf`，重点检查第 7--9 页，并向前检查第 6 页的 Limitations 起始边界；
3. `MANUSCRIPT_ZH_FULL.md`；
4. `MANUSCRIPT.md`；
5. `MANUSCRIPT_ZH.md`；
6. `LIMITATIONS_CONCLUSION_PREAUDIT_20260728.md`；
7. `LIMITATIONS_CONCLUSION_REVISION_LOG_20260728.md`；
8. `SECTION1_FINAL_AUDIT_20260728.md`；
9. `SECTION2_FINAL_AUDIT_20260728.md`；
10. `FIG3_SINGLECOL_LAYOUT_FINAL_AUDIT_20260728.md`；
11. `SECTION4_4_1_FINAL_AUDIT_20260728.md`；
12. `SECTION4_4_2_FINAL_AUDIT_20260728.md`；
13. `SECTION4_4_3_FINAL_AUDIT_20260728.md`；
14. `SECTION4_4_4_FINAL_AUDIT_20260728.md`；
15. `RESULTS_CLAIM_EVIDENCE_AUDIT.md`；
16. `METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md`。

本终审没有继承 revision log 的通过结论，而是重新进行逐段、逐句、claim--evidence、禁用内容、镜像、跨章节和 PDF 检查。

事实优先级采用当前冻结正文与最新局部终审。较早的 `RESULTS_CLAIM_EVIDENCE_AUDIT.md` 和 Method canonical audit 中保留的 endpoint、旧 checkpoint 或 composition 历史术语，只作为修订过程记录；它们已被当前 Section 3--4、作者确认事实和最新冻结审计覆盖，不用于恢复旧主张。

## 3. Limitations 三段反向提纲

| 段落 | 唯一职责 | 句子功能 | 证据/范围边界 | 判定 |
|---|---|---|---|---|
| P1，`main.tex:689--694` | Representation and deployment scope | 先说明学到的是 future-predictive representation；再排除 complete physical state；随后区分 realized future meteorology 与 operational forecasts，并声明 deployment gap 未量化 | 不声称已经测得业务天气输入导致的性能下降 | **PASS** |
| P2，`main.tex:696--701` | Intervention evidence boundary | 将 matched-control 结果限定为 conditional predictive fidelity；排除 causal/counterfactual；报告 hot-dry null；限定 state-removal 的最大含义 | Q2 只支持显式状态路径承载 measurable increment，不支持全部输出/历史信息必须经过状态 | **PASS** |
| P3，`main.tex:703--706` | External validity | 限定 GreenEarthNet temporal shift；排除跨数据集泛化；说明 cloud screening 与未观测地表因素 | 不重启 Q4，不制造新实验承诺 | **PASS** |

### 3.1 第一段：representation and deployment scope

- `future-predictive representation` 与 future-state anchoring、forecast path 和 Q1--Q3 方法合同一致；
- `does not recover a complete physical land-surface state` 是必要 ontology 边界，不否定 predictive-state world-model 身份；
- `realized future meteorology` 准确描述当前评测条件；
- operational forecasts 的 prediction error 与潜在 input-distribution difference 被写成可能影响 state evolution/forecast quality，而非已经量化的下降；
- `we do not quantify this deployment gap` 清楚关闭证据边界，篇幅短，不构成自我削弱。

### 3.2 第二段：intervention evidence boundary

- `conditional predictive fidelity` 与 Q3 的完整窗口 control-minus-actual loss 一致；
- causal identification 与 counterfactual correctness 只在否定语境出现；
- hot-dry interaction interval 跨零，因此 `does not support extreme-specific enhancement` 完全准确；
- state removal 的含义被限制为 explicit state-mediated path carries a measurable forecast increment；
- 没有声称全部预测信息、全部历史内容或所有输出分量只能经过该状态。

### 3.3 第三段：external validity

- 单一 GreenEarthNet temporal-shift setting 与当前实验范围一致；
- `does not establish cross-dataset generality` 没有被 Conclusion 反向突破；
- cloud screening、soil moisture、irrigation、vegetation type 均是与 EO 地表预测直接相关的限制；
- 已完全删除原 `Temporal composition remains unexplored...` 句；
- 段落以真实 observability/modeling boundary 收束，没有留下 Q4、composition 或 future-work 清单。

## 4. Conclusion 逐句功能

| 句子 | 功能 | 技术内容 | 判定 |
|---|---|---|---|
| S1，`main.tex:710--711` | Problem | 准确预测本身不能建立模型形成并使用 internal world state；`by themselves` 保留了像素预测的价值 | **PASS** |
| S2，`main.tex:711--713` | Method identity, part 1 | history-derived spatial predictive state、shared weather-conditioned transition、explicit state-mediated final contribution | **PASS** |
| S3，`main.tex:714--715` | Method identity, part 2 | future-state anchoring 塑造 representation；post-training removal/substitution interfaces 检验其作用 | **PASS** |
| S4，`main.tex:716--718` | Principal evidence | useful OOD-t skill、removal-induced degradation、actual-vs-frozen-control complete-window fidelity | **PASS** |
| S5，`main.tex:719--721` | Broader significance | 将 internal predictive-state claim 从 architecture naming/assertion 转化为可经验检验和否证的问题 | **PASS** |

### 4.1 Problem

首句与 Introduction 的核心科学问题同构。它没有否认 accurate EO forecasting 的应用价值，而只说明 accuracy 不能单独证明 internal state formation/use。

### 4.2 Method

S2--S3 已覆盖用户指定的全部必要组件：

- spatial predictive state inferred from history；
- shared weather-conditioned transition；
- explicit state-mediated contribution；
- future-state anchoring；
- post-training state-removal and weather-substitution interfaces。

这两句没有展开公式、损失、训练阶段或统计协议，同时足以表明 TerraState 是一个方法，而不是单独 benchmark 或事后评测套件。

### 4.3 Evidence

S4 只概括三个冻结层级：

- Q1：useful OOD-t forecast skill；
- Q2：state removal causes measurable degradation；
- Q3：actual future weather has greater complete-window fidelity than frozen controls。

无数字、样本数、CI、排名或显著性堆叠；没有把 Q3 提升为因果、反事实或完整物理正确性。

### 4.4 Broader significance

末句准确且自信地收束了全文。它：

- 回应 Abstract/Introduction 的 `testable` 与 `falsifiable` 叙事；
- 将意义落在内部 predictive-state claim 的经验可检验性，而不是 SOTA；
- 不暗示 TerraState 提出了世界模型的唯一合法定义；
- 不声称所有内部世界状态、完整物理状态或任意反事实均已验证。

“claim → architectural assertion → testable/falsifiable question”的词类转换略带修辞性，但科学含义清楚，不构成理解或可信度问题。

## 5. AAAI 写作定式审计

### 5.1 Limitations

| 检查项 | 结论 | 说明 |
|---|---|---|
| applicability/representation scope 起笔 | PASS | 直接限定 state ontology 与部署 forcing |
| evidence boundary 居中 | PASS | Q2、Q3 和 hot-dry 的最大安全解释集中在一段 |
| external validity 收束 | PASS | 数据、光学观测与未观测变量构成自然尾段 |
| 诚实但不自我削弱 | PASS | 每项否定都关闭真实过度解释，不否定核心正向证据 |
| 无防御性失败清单 | PASS | 三段各有统一主题，不按“未做事项”逐条罗列 |
| 不重复 Introduction | PASS | physical-state 边界在此承担正式 scope 职责，没有重讲完整动机 |
| 无 future-work 列表 | PASS | 没有扩展跨数据集、业务天气或新变量为承诺 |
| 无 Q4/composition | PASS | 第三段删除了旧 composition 尾句 |
| 篇幅 | PASS | 正文 150 词，紧凑但信息完整 |

### 5.2 Conclusion

| 检查项 | 结论 | 说明 |
|---|---|---|
| Problem | PASS | 恢复 output accuracy 与 internal-state evidence 的差别 |
| Method | PASS | 用两句说明机制和测试接口，不写公式 |
| Evidence | PASS | 一句压缩 Q1--Q3，不朗读表格 |
| Significance | PASS | 以 falsifiable internal claim 收束世界模型贡献 |
| 自信程度 | PASS | 末句有明确 takeaway，不以 limitation 清单结尾 |
| 协议/审计文档感 | PASS | 无 gate、verdict、checkpoint、estimand 或内部工程叙事 |
| AI 模板化语言 | PASS | 无空泛宣传词；每句承担具体内容 |
| 篇幅 | PASS | 109 词，适合单段结论 |

## 6. 世界模型主线收束

一个审稿人在读完 Conclusion 后可以准确复述：

1. 仅有 EO 输出精度不足以说明模型形成并使用内部状态；
2. TerraState 以 history-derived spatial predictive state、shared weather-conditioned transition 和 on-path state contribution 构造预测；
3. future-state anchoring 约束表示，两个 post-training interfaces 使 state use 与 forcing response 可检验；
4. Q1 建立预测前提，Q2 建立 removable forecast contribution，Q3 建立 actual-vs-control complete-window fidelity；
5. 贡献不是宣布一个完整物理世界状态，而是把 predictive-state world-model claim 变成可否证的实证问题。

因此：

- “可检验预测状态”表现为模型设计与证据接口的共同贡献，不是独立评测技巧；
- TerraState 的遥感身份来自 EO history、weather forcing、geography 和 NDVI forecasting；
- 世界模型身份来自 state construction、shared state transition、on-path readout 与 forcing intervention；
- 与普通 EO predictor 的结构差别在 Conclusion 中可以恢复；
- 结尾没有口号大于实质，也没有内部审计报告语气。

## 7. Claim--evidence 对照

| 结尾章节主张 | 冻结证据/方法事实 | 是否支持 | 最大安全边界 |
|---|---|---|---|
| TerraState learns a future-predictive representation | future-state target、transitioned state、forecast readout；Q1--Q3 使用同一最终模型 | **SUPPORTED AS METHOD IDENTITY** | 不等于经典 PSR sufficient statistic 或 complete physical state |
| It does not recover a complete physical state | 当前方法只建模 EO predictive representation；无物理状态识别证据 | **SUPPORTED SCOPE NEGATION** | 只能否定，不反推普通预测器身份 |
| Operational-weather deployment gap is unquantified | 当前实验使用 realized future meteorology，未评测业务天气预报输入 | **SUPPORTED** | 只说可能影响，不给下降幅度 |
| Matched intervention measures conditional fidelity | Q3 control-minus-actual complete-window masked loss | **SUPPORTED** | 限于冻结 matched protocol 和 84-pair subset |
| Non-causal/non-counterfactual | 输入替换不是因果识别设计，无任意 counterfactual guarantee | **SUPPORTED BOUNDARY** | 不把较低 loss 改写成因果效应 |
| Hot-dry result does not support extreme-specific enhancement | interaction mean 约 0.00044，geo-cluster 95% CI \([-0.00216,0.00320]\) 跨零 | **SUPPORTED NEGATIVE RESULT** | 不否定总体 actual-vs-control fidelity |
| Explicit state path carries a measurable increment | Validation state-removal paired mean 0.01616、CI \([0.00643,0.02590]\)；OOD-t 0.02200、CI \([0.01422,0.03018]\) | **SUPPORTED** | 不表示全部输出或历史信息必须经过 state |
| Useful OOD-t skill | 完整 GreenEarthNet OOD-t：\(R^2=0.56935\)、RMSE \(=0.15059\) | **SUPPORTED** | 不支持 SOTA、strict ranking 或 accuracy win |
| Actual weather has greater complete-window fidelity | donor-minus-actual 0.00257，CI \([0.00112,0.00399]\)；mean-minus-actual 0.01126，CI \([0.00547,0.01708]\) | **SUPPORTED** | 仅限完整 20-step matched-subset window；非 endpoint-only、非因果 |
| Predictive-state claim is empirically testable and falsifiable | explicit \(b_h+r_h\) path、state removal、weather substitution 与预先声明的判断边界 | **SUPPORTED** | 说明该 TerraState claim 可检验，不是领域唯一 world-model definition |

Conclusion 的联合主张依赖 Q1 prerequisite + Q2 + Q3，而不是由 Q3 单独建立。

## 8. 禁止内容回归检查

对 `main.tex` 的 Limitations/Conclusion 及三份 Markdown 镜像对应 Section 5--6 进行了语境化扫描。

| 禁止内容 | 当前状态 | 语义判定 |
|---|---|---|
| Q4 | 0 次 | PASS |
| composition / compositional dynamics / temporal composition | 0 次 | PASS |
| non-collapse / group action | 0 次 | PASS |
| SOTA / state of the art / strict ranking | 0 次 | PASS |
| causal simulator | 0 次 | PASS |
| counterfactual correctness | Limitations 中出现 | 合法否定：`not ... counterfactual correctness` |
| complete physical state | Limitations 中出现 | 合法否定：`does not recover...` |
| extreme-specific enhancement | Limitations 中出现 | 合法否定：证据 `does not support` |
| 11,904 / boundary80 | 0 次 | PASS |
| single-run / single training run | 0 次 | PASS |
| Published/Local / public-versus-local | 0 次 | PASS |
| endpoint-only Q3 / endpoint | 0 次 | PASS |
| `±` / `\pm` | 0 次 | PASS |

否定性边界没有被机械误报为正向主张。

## 9. 中英文镜像

### 9.1 权威英文与 `MANUSCRIPT.md`

`MANUSCRIPT.md` 的 Sections 5--6 与 `main.tex` 逐段、逐句同强度：

- 三段 Limitations 的顺序和职责一致；
- 109 词 Conclusion 的五句功能一致；
- 无 single-run、Published/Local、composition-open 或 endpoint-only 叙事；
- `may differ/can affect` 没有被改成确定的 deployment failure。

### 9.2 两份中文镜像

`MANUSCRIPT_ZH_FULL.md` 与 `MANUSCRIPT_ZH.md` 的 Sections 5--6 文本一致，且与英文语义对应：

- `future-predictive representation` → “未来预测表示”；
- `realized future meteorology` → “实际发生的未来气象条件”；
- `operational weather forecasts` → “业务天气预报”；
- `state-mediated path` → “状态介导路径”；
- `complete-window fidelity` → “完整窗口预测保真度”；
- `frozen controls` → “冻结对照”；
- `testable and falsifiable question` → “可以接受经验检验和否证的问题”。

中文使用“可能影响”“尚未量化”“支持”“不能证明”，没有增强为必然下降、完全证明或完整世界状态。

### 9.3 范围说明

本项判定针对用户指定的 Sections 5--6。两个 compact mirrors 在其他旧章节中的历史措辞不属于本轮结尾章节审计，也没有被用来重新打开冻结 Section 1--4；Sections 5--6 本身已清除指定的全部旧叙事。

## 10. 跨章节一致性

| 对照对象 | 结论 | 说明 |
|---|---|---|
| Frozen Abstract | **PASS** | 同样以 output accuracy gap、testable predictive state、state removal 和 full-window weather controls 为主线 |
| Frozen Introduction | **PASS** | Conclusion 回答其科学问题，并复现 history→state→transition→forecast 与 Q1--Q3 证据链 |
| Frozen Related Work | **PASS** | 结尾保留 bounded, testable predictive-state 定位，没有把 operational tests 升格为唯一世界模型定义 |
| Section 3 Method | **PASS** | Conclusion 包含 shared transition、on-path contribution、future-state anchor 和两个 interfaces；无 recursive composition |
| Section 4.2/Q1 | **PASS** | 只写 useful OOD-t skill，不声称领先 |
| Section 4.3/Q2 | **PASS** | removal-induced measurable degradation；未称全部信息经过 state |
| Section 4.4/Q3 | **PASS** | actual-vs-frozen-control complete-window fidelity；未增强为因果、反事实或 extreme-specific |
| Figure 3 caption | **PASS** | 完整 20 步窗口、state removal primary、\(T\!\to I\) supporting、84 pairs 均不与结尾冲突 |
| 三条 Contributions | **PASS** | Conclusion 依次恢复 problem/viewpoint、method、evidence，并以 falsifiability 收束 |

未发现结尾章节自身冲突，也未发现需要同步其他冻结章节的科学冲突。不同章节的细节粒度差异符合各自功能。

## 11. PDF 第 7--9 页视觉检查

本轮没有重新编译；通过当前 `paper/main.pdf` 的实际渲染、文本块几何与页面顺序进行只读检查。为确认 Limitations 的跨页起点，额外查看了第 6 页末部。

| 检查项 | 当前状态 | 判定 |
|---|---|---|
| 总页数 | 9 | 正常 |
| Limitations 起点 | 第 6 页右栏，Figure 2/Section 4.4 后 | 可读 |
| Limitations P1--P2 | 第 6 页右栏连续 | PASS |
| Limitations P3 | 第 6 页右栏起句，第 7 页左栏续接 | PASS WITH MINOR |
| Conclusion 标题 | 第 7 页左栏，标题下有充足正文 | 无孤立标题 |
| Conclusion 正文 | 第 7 页左栏开始、右栏完成 | 完整、正常双栏阅读顺序 |
| Conclusion 与 References | Conclusion 在第 7 页结束；References 从第 8 页开始 | PASS |
| Figure 3 | 第 8 页左栏标准单栏图，caption 完整 | 保持 `FIG3_SINGLECOL_LAYOUT_FROZEN` |
| References | 第 8 页图下及右栏开始，第 9 页左栏结束 | 阅读顺序正常 |
| 裁切/重叠/跨栏侵入 | 未发现 | PASS |
| 异常空白 | 第 9 页 bibliography 尾页右栏及下部留白 | 正常文献尾页，不是结尾章节排版故障 |
| Overfull | 当前 log 未记录 overfull hbox/vbox | PASS |

唯一分页问题是 P3 中的 `Optical` 在第 6 页末拆为 `Op-`、第 7 页续为 `tical`，且页顶 Table 1--3 位于两部分之间。语义仍能恢复，没有裁切、覆盖、标题悬空或正文丢失，因此列为 Minor，而非阻塞性排版问题。

当前 9 页是正常可提交的排版结果。Figure 3 的单栏布局没有打断 Conclusion，也没有把 References 推到异常独立空白页。

## 12. Critical / Major / Minor / Optional

### Critical（0）

NONE。

### Major（0）

NONE。

### Minor（1）

#### m1 — Limitations 第三段跨页并被页顶浮动表格隔开

- **位置：** `main.tex:703--706` 对应 PDF 第 6--7 页；`Optical` 显示为第 6 页末 `Op-`、第 7 页 `tical`；
- **原因：** 双栏浮动表格占据第 7 页页顶，第三段在页边界处被拆分；
- **对审稿人理解的影响：** 造成一次短暂阅读中断，但不改变句义、证据边界或章节顺序；
- **最小方向：** 仅在以后因其他原因重新打开全篇 layout gate 时，优先让该句自然连续；不得为此修改冻结科学内容、缩小字号、使用负间距或重开 Figure 3；
- **冻结影响：** 无。

### Optional（1）

#### O1 — Conclusion 末句的修辞性词类转换

- **位置：** `main.tex:719--721`；
- **原文核心：** `turns an internal predictive-state claim ... from an architectural assertion into an empirically testable and falsifiable question`；
- **原因：** `claim/assertion/question` 在同一句中发生修辞性类别转换；
- **对审稿人理解的影响：** 无实质影响；主语、对比和 broader takeaway 均清楚；
- **可选最小方向：** 仅在未来全篇 copyedit 时考虑统一为“使该 claim 可经验检验和否证”或使用同一命题词类；当前无需修改；
- **冻结影响：** 无。

## 13. 评分

评分范围为 1--5。

| 维度 | 分数 | 主要依据 |
|---|---:|---|
| Limitations 结构成熟度 | **4.9** | scope → evidence boundary → external validity，三段职责唯一 |
| Limitations 诚实性与不过度削弱 | **4.9** | 关闭过度解释，但保留 Q2/Q3 正向结论 |
| Conclusion 四步结构 | **4.9** | problem → method → evidence → significance 完整 |
| 世界模型主线收束 | **4.9** | predictive state、weather transition、on-path contribution 与 falsifiability 连接清楚 |
| 方法身份清晰度 | **4.8** | 不是 benchmark；机制与接口均可从结尾恢复 |
| Claim--evidence 对齐 | **5.0** | Q1--Q3、hot-dry null 与非因果边界完全一致 |
| 英文自然度 | **4.8** | 专业紧凑；仅末句有可选修辞精化 |
| 中文镜像质量 | **4.9** | 自然、同强度，无 “may”→“必然” 或 support→prove 放大 |
| 跨章节一致性 | **4.9** | 与 Abstract、Section 1--4、Figure 3 和 contributions 无冲突 |
| PDF 视觉呈现 | **4.2** | 无阻塞；Limitations P3 有一次跨页/浮动表格阅读中断 |

所有核心评分均不低于 4/5。

## 14. 文件与局部区块 SHA-256

### 14.1 当前文件

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `1fe12204bad54b2b18a8debd5792cab9dff85a1e342cc35ca8df0e9a2d6eaab9` |
| `paper/main.pdf` | `5f3931e373643d7aa3674fa3517e2e4f1e58f1632bd279b513d11f28bc021691` |
| `paper/main.log`（只读） | `630577816ffd7a011c262173dfe0bd339d1753761350de5d17d1e36ac63b4af7` |
| `MANUSCRIPT_ZH_FULL.md` | `0577238cd6d9561fb9ca7ea9fa4d8275da74a5b5f447e1d0407c4390d66099c6` |
| `MANUSCRIPT.md` | `8c8c47c00bc1ebc7337269f268539dfb9869fb73bc9a4feb2cc385a0ac3ebe21` |
| `MANUSCRIPT_ZH.md` | `d957d421af7efafb73d94ebd4775b3a1c150f01574d927c22197d27ac4c2f4ac` |
| `figure_workspace/export/fig3_behavior_singlecol.pdf` | `3b9c764152a867b2d1aef1b82b5661eb18bbd613236cb37dc45d58dfac7f0a53` |

### 14.2 权威正文局部区块

| 区块 | 提取口径 | SHA-256 |
|---|---|---|
| Limitations | 含 `\section{Limitations and Scope}`，不含 `\section{Conclusion}` | `e4f1456ff2609d44d8f74ad66474e6e8a831184cd59cdffdd0411f6dba4fa186` |
| Conclusion | 含 `\section{Conclusion}`，不含 `\bibliography` | `21f9dadc2155a1d21c48e1c2456cc9fdc05dc088eaa0e9510ee21d244337f5b1` |

### 14.3 Markdown 局部区块

| 文件 | Limitations SHA-256 | Conclusion SHA-256 | Sections 5--6 combined SHA-256 |
|---|---|---|---|
| `MANUSCRIPT.md` | `2761bf2bd15ae7704acda7d74cd593daecb1e1ff95eac59b06aa4ed66422b43f` | `1cb596d1f3c6e30eb61afc318b6805c7706151585b535e6b509fff7a4b02ba0c` | `af09fdc9fba66e26d6e9ab939d2a9a9e6d56e8486b77fa1c93c15fa4c3a31e15` |
| `MANUSCRIPT_ZH.md` | `b166d8728f2124f445ccf1307ee94fbb11dcb4531c97814e3dd9e5dbe248feba` | `632d6bb513fc7b5a23d0b5e339dbf0bc142f8269ccfe574d200c2e50e97eb524` | `d10049bf4621a1324e80aa11f0df87955f4944e3a9b35db0ad226fbacc6f6ddd` |
| `MANUSCRIPT_ZH_FULL.md` | `fa8d08f1ce8ec29213e15432e9e9265f4a058004c6e0ea9772f95da54d262b4f` | `da0503b3385889b8b329475bfa0d5143f996036b9ca44c1281df1359524af990` | `e045e28191546532982471ca2ad1d123e4033652b6a76a4ab9fc9f51c3b62a6b` |

### 14.4 主要审计输入

| 文件 | SHA-256 |
|---|---|
| `LIMITATIONS_CONCLUSION_PREAUDIT_20260728.md` | `93b8501d3ce423a70552f401cc62c2cc3c24cd037f9ba141ad61f440810091f2` |
| `LIMITATIONS_CONCLUSION_REVISION_LOG_20260728.md` | `52819904b8075eefe34ec15d699afdaa8196835a9cb6dacec45e6bf3afed69b8` |
| `SECTION1_FINAL_AUDIT_20260728.md` | `58ea63ee615d288c08c856d364b5de4b629e8dfab7fbc2e2b56a125540cddd5d` |
| `SECTION2_FINAL_AUDIT_20260728.md` | `8125dcb5cace88dd5f6c61483b497b9762d3f00e17733f4e62533fcb10c17e60` |
| `FIG3_SINGLECOL_LAYOUT_FINAL_AUDIT_20260728.md` | `700efbba489fb2c905944267747f415910425c2a9fb8e043a8386a1673af7492` |
| `SECTION4_4_1_FINAL_AUDIT_20260728.md` | `63a7e28680da8e70635259e1dc5072c4b254a428eff68d2a4bc8b20841a6b447` |
| `SECTION4_4_2_FINAL_AUDIT_20260728.md` | `a4cb2cb6424318117770155820134e296e95f4e689302e1fa8aceac468ab44ed` |
| `SECTION4_4_3_FINAL_AUDIT_20260728.md` | `cf01a6f6c5ffd08c6ab3624a7f2b09c1099f914e61b6bcabd60100d027456308` |
| `SECTION4_4_4_FINAL_AUDIT_20260728.md` | `d3f9486cf0f3efcc845dd757646d92a6964390069a6f979dc964aef6789ff793` |
| `RESULTS_CLAIM_EVIDENCE_AUDIT.md` | `e8f4f4dcfc4055fb79fc76b59cd6b338222118c6c2ed23115899f6add65b5b0f` |
| `METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md` | `ff2c745489ccfda5019a84f001d65403426b2c84c82d4d4a4f1f10cbdd4d1365` |

## 15. 冻结判定

冻结条件逐项满足：

- Critical = 0；
- Major = 0；
- Limitations 没有重新引出 Q4；
- Conclusion 完成 problem → method → evidence → significance；
- 世界模型主线清楚且自信；
- Q1--Q3 与 hot-dry null 没有证据越界；
- 英中 Sections 5--6 镜像一致；
- 所有核心评分均 \(\ge 4/5\)；
- PDF 无阻塞性裁切、重叠、标题悬空或 Figure 3 干扰。

唯一 Minor 是已有 PDF 的跨页断词与浮动间隔，不影响主线理解、事实可信度或可提交性。因此，Limitations 与 Conclusion 可以冻结。

## 16. 只读声明

本轮未修改 `paper/main.tex`、`paper/main.pdf`、任何 MANUSCRIPT、`references.bib`、Abstract、Section 1--4、Figure 1--3、Table 1--3、实验、证据、代码、模型或数据；未运行 LaTeX 编译。PDF 页面渲染仅在内存中完成，没有生成临时预览文件。

唯一新建文件为：

`LIMITATIONS_CONCLUSION_FINAL_AUDIT_20260728.md`

**FINAL STATUS: LIMITATIONS_CONCLUSION_FROZEN**
