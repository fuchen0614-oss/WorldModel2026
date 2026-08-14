# TerraState Related Work 世界模型谱系扩充第二次独立终审

日期：2026-07-29  
审计性质：只读、独立终审  
审计对象：`RELATED_WORK_WORLD_MODEL_EXPANSION_REVISED_PROPOSAL_20260729.md`

## 1. 最终判定

**READY_FOR_CONTROLLED_APPLICATION**

独立核验结果：

- 首次审计的 **P0 = 1** 与 **P1 = 7** 均已在实际英文候选和实施方案中关闭；
- 本轮新增问题计数：**P0 = 0，P1 = 0，P2 = 1**；
- 四段已经形成连续的
  `EO forecasting → general world models → EO world models → predictive-state testability → Method`
  递进；
- 6 篇新增文献均有独立句子职责；候选 Related Work 含 27 个唯一 key，与正文其他位置独有的 `wang2022pvtv2` 合并后，实施态预计为 **28 个唯一引用**；
- 409 词候选处于规定的 405–420 词区间；
- 主文第 7 页结束、References 延伸至第 8–9 页具有条件可行性，但只能在受控写入、等量安全压缩和正式编译后确认。

本判定只表示返修提案可以进入受控应用，不表示 `main.tex`、`references.bib`、页数或排版已经完成变更。

## 2. 审计范围与输入身份

### 2.1 输入 SHA-256

| 文件 | SHA-256 |
|---|---|
| `RELATED_WORK_WORLD_MODEL_EXPANSION_REVISED_PROPOSAL_20260729.md` | `9b60b40aed4a43b10f87602d83d69ad82e0940c99e8878fb349434bcd38cda93` |
| `RELATED_WORK_WORLD_MODEL_EXPANSION_INDEPENDENT_AUDIT_20260729.md` | `b8f91d4f10640972c7d32e8a39d297bc9ee68042da82884d83a89824e867bd3c` |
| `paper/main.tex` | `304db26cc894ba73641c8b2d09acd5fd3f36da1a9f54c6f7b7480b07be52a5d2` |
| `paper/references.bib` | `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3` |
| `evidence_workspace/CLAIM_EVIDENCE_MAP.md` | `d84ab20e8c470e732b7fd64f51575909949b3590366362067548c32d1559c88f` |
| `paper/main.pdf`（仅用于现状页边界读取） | `f9c3fce5e209b3506c0afa44e4c742b209ad21168f855419ae4e41c3aca2daed` |

局部区块：

| 区块 | SHA-256 |
|---|---|
| 返修提案英文四段候选 | `570f99aea838bb1b9a63fc88e8e5951072305b07914c419377af23408760a54e` |
| 返修提案 Conclusion 压缩区块 | `e03c9eafee80c433cb0d6caec922477ee2d9a18cc928bc1867d4ad195cdf74ff` |
| 当前 `main.tex` Related Work 区块 | `4714bbf9896f4d10bbe5c8b8f8a1738570ca4763925a7abfe61d18f160f6e1ce` |

### 2.2 独立性

本报告重新检查了英文候选、当前正文计算路径、当前 BibTeX、claim–evidence 边界、官方出版页面和当前 PDF 页边界。返修提案中的 `CLOSED`、词数和引用数量声明均未被直接当作结论。

## 3. 首次 P0/P1 逐项复核

| 首次问题 | 独立检查 | 实际关闭证据 | 本轮判定 |
|---|---|---|---|
| **P0-1：TD-MPC2 作者元数据错误** | 检查英文候选和新增 key 集合 | 候选正文不含 TD-MPC2，也不建议新增 `hansen2024tdmpc2`；该工作只在问题关闭说明中被提及 | **CLOSED** |
| **P1-1：四段都以 TerraState 结尾** | 检查四段末句 | P1 以 explicit internal-state question 收束；P2 以 task-specific predictive-state account 收束；两句均不含 TerraState | **CLOSED** |
| **P1-2：新增文献职责重复** | 分解 P2 每个引用的原子职责 | DreamerV3、TD-MPC2 已从候选删除；MuZero、IRIS、Genie、Drive-OccWorld 分别承担 task-relevant targets、tokenized-world agent、action-controllable environment、occupancy-to-planning | **CLOSED** |
| **P1-3：P2 使用 `claims none`** | 搜索候选正文并审查段末语义 | 防御句已删除，P2 以不同 downstream objectives 的正向综合结束 | **CLOSED** |
| **P1-4：P3 使用 `not a second version` / `without claiming`** | 搜索候选正文并审查最近邻定位 | 两个表达均已删除；改为 `Complementing these objectives, TerraState examines ...` | **CLOSED** |
| **P1-5：Vafa et al. 范围过宽** | 对照 NeurIPS 正式论文 | 候选明确限定为 `automaton-governed generative-model settings`，与论文的 deterministic-finite-automaton 设定一致 | **CLOSED** |
| **P1-6：P4 将 TerraState 降格为测试接口** | 对照 Method 3.1 | P4 末句同时包含 on-path predictive state、shared weather-conditioned transition、state-removal 和 weather-control interfaces | **CLOSED** |
| **P1-7：Conclusion 压缩删除方法身份** | 对照冻结 Conclusion 和返修候选 | 新候选保留 history-derived spatial state、shared transition、explicit forecast contribution、future-state anchoring 和两个 post-training tests | **CLOSED** |

首次审计的四项 P2 写作建议也已实质落实：

1. `evidence centers on forecast outputs` 替代抽象的 `assess predicted observations`；
2. P2 以 `World-model research supplies ...` 引入本文综合，不把 taxonomy 写成公认唯一定义；
3. weather-as-forcing 使用正向定义，不另开未引用的 weather-model 综述；
4. `observed-weather forecast` 已统一为 `weather-conditioned EO forecast`。

## 4. 四段叙事与段间递进

### 4.1 反向提纲

| 段落 | 首句职责 | 主体职责 | 末句职责 | 是否完成 |
|---|---|---|---|---|
| P1 — Weather-conditioned EO forecasting | 定义 EO 输入与预测目标 | 以 deterministic、probabilistic、compressed-state/weather-response 三类综合现有工作 | 从输出证据收紧到 explicit internal state 问题 | **PASS** |
| P2 — World models: latent dynamics to interactive environments | 解释为何从输出预测转向一般 world-model 语境 | 用 latent rollout、task-relevant prediction、tokenized interaction、occupancy forecasting 区分目标 | 引出 EO 中 task-specific predictive-state account | **PASS** |
| P3 — EO world models and forcing-conditioned simulation | 将一般结构落到部分观测 EO 与外部环境驱动 | 公平区分 EO-WM、VegSim 和 observability model | 首次明确 TerraState 的 removable contribution 与 complete-window fidelity 生态位 | **PASS** |
| P4 — Predictive states and testability | 定义 state semantics、supervision 与 evaluation 问题 | PSR/PSD、JEPA、LatentTSF、PLSM、scoped Vafa 各承担不同基础 | 正向交给 Section 3 的 state–transition–interface 设计 | **PASS** |

### 4.2 四个过渡

- **P1 → P2：成立。** P1 的末句把问题从输出转到内部状态；P2 首句随即说明一般 world-model 文献为何是这一转向的上位语境。
- **P2 → P3：成立。** P2 以 task-specific EO account 收束；P3 首句立即解释该结构在部分观测、外部驱动的 EO 中需要专门化。
- **P3 → P4：成立。** P3 确认 EO 已有 forcing-conditioned world models；P4 转而处理“内部状态应如何定义、监督和评价”这一尚未闭合的问题。
- **P4 → Method：成立。** 末句不是泛泛说“我们增加评测”，而是明确构造 on-path state、shared transition 和两个干预接口。

整体递进没有“介绍 TerraState 后又退回一般背景”的回摆。P3 与 P4 连续两次出现 TerraState 是有意的渐进收束：前者定位 EO 最近邻差异，后者交付具体方法响应，职责不重复。

## 5. 引用集合、职责与谱系覆盖

### 5.1 数量核对

只读 citation inventory 对当前 `main.tex` / `references.bib` 的结果为：

- 当前正文唯一引用 key：22；
- 当前 BibTeX 条目：24；
- missing key：0；
- duplicate key：0；
- 当前未使用条目：`chen2023deeposg`、`wang2026groupactions`。

返修候选的四段 Related Work 含 **27 个唯一 key**。它保留当前正文已引用的 21 个 Related Work key并新增 6 个；正文 Method/Table 1 另有候选四段未使用的 `wang2022pvtv2`。因此受控应用后的全文集合为：

> 27（Related Work） + 1（正文其他位置独有的 PVT v2） = **28 个唯一引用**

“预计 28”是正确集合运算，不是把引用数量作为写作目标。Deep-OSG 和 group-action 条目仍可留在 `.bib` 中作为未使用条目，但不得恢复到正文。

### 5.2 六篇新增工作的不可替代职责

| 新增工作 | 候选句职责 | 为什么不是重复引用 | 必要性 |
|---|---|---|---|
| MuZero | 说明 learned model 可以只预测 planning-relevant policy/value/reward | 区别于 World Models/PlaNet/Dreamer 的 latent observation rollout/imagination | **独立且必要** |
| IRIS | 说明 agent 可在由 discrete tokens 与 autoregressive dynamics 构成的 world model 中学习 | 不等同于 Genie 的环境生成目标 | **独立且必要** |
| Genie | 说明可从视频学习 action-controllable generated environments | 不承担 IRIS 的 agent-learning 或 Drive-OccWorld 的 occupancy-planning 职责 | **独立且必要** |
| Drive-OccWorld | 连接 action-conditioned 4D occupancy forecasting 与 driving planning | 为高维空间状态和正式 AAAI world-model 语境提供独立例子 | **独立且必要** |
| Predictive-State Decoders | 说明 future-observation prediction 可作为 recurrent internal state 的显式监督 | 是 TerraState future-state anchoring 最直接的概念先例，现有 PSR/JEPA 不替代该职责 | **独立且必要** |
| Vafa et al. | 提供特定 automaton-governed generative-model setting 中专门 world-model evaluation 揭示标准诊断遗漏问题的先例 | 与 LatentTSF 的 temporally disordered latent 证据互补 | **独立且必要，必须保留范围限定** |

28 篇预计唯一引用已覆盖：

1. weather-conditioned EO task 与 benchmark；
2. deterministic、probabilistic 和 explicit latent-transition forecasting；
3. latent-control、task-relevant、tokenized-interactive 与 occupancy world-model paradigms；
4. EO forcing、scenario simulation 与 observability world models；
5. PSR、future-observation supervision、representation prediction、latent-quality counterexample、action-effect regularization 与专门 world-model evaluation。

该覆盖足以支撑本文谱系。继续加入 DreamerV3、TD-MPC2 或其他热门 world-model 工作只会增加重叠与页面成本。

## 6. 正式元数据与引文强度

所有来源均以正式出版页面或官方 proceedings 为准。返修提案表中的 `et al.` 是提案级简写，受控写入 BibTeX 时仍须复制完整作者列表和顺序。

| 工作 | 正式元数据核验 | 候选原子主张 | 支撑判定 |
|---|---|---|---|
| MuZero | Julian Schrittwieser et al.; *Mastering Atari, Go, chess and shogi by planning with a learned model*; Nature 588:604–609; 2020; DOI [10.1038/s41586-020-03051-4](https://doi.org/10.1038/s41586-020-03051-4) | 模型预测 planning-relevant policy、value、reward | **supported**；Nature 摘要直接列出三类预测 |
| IRIS | Vincent Micheli, Eloi Alonso, François Fleuret; *Transformers are Sample-Efficient World Models*; ICLR 2023 oral; [ICLR official page](https://iclr.cc/virtual/2023/oral/12543), OpenReview `vhFu1Acb0xb` | agent learns inside a tokenized world model | **supported**；官方摘要说明 discrete autoencoder、autoregressive Transformer 和 agent learning |
| Genie | Jake Bruce et al.（PMLR 正式记录 26 位作者）; *Genie: Generative Interactive Environments*; ICML 2024; PMLR 235:4603–4623; [PMLR](https://proceedings.mlr.press/v235/bruce24a.html) | 从视频学习 action-controllable environments | **supported**；正式摘要直接支持 |
| Drive-OccWorld | Yu Yang, Jianbiao Mei, Yukai Ma, Siliang Du, Wenqing Chen, Yijie Qian, Yuxiang Feng, Yong Liu; *Driving in the Occupancy World: Vision-Centric 4D Occupancy Forecasting and Planning via World Models for Autonomous Driving*; AAAI 39(9):9327–9335; 2025; DOI [10.1609/aaai.v39i9.33010](https://doi.org/10.1609/aaai.v39i9.33010) | action-conditioned occupancy forecasting 与 driving planning 相连接 | **supported**；AAAI 摘要直接描述 action conditions、occupancy forecasting 和 end-to-end planning |
| Predictive-State Decoders | Arun Venkatraman, Nicholas Rhinehart, Wen Sun, Lerrel Pinto, Martial Hebert, Byron Boots, Kris Kitani, J. Bagnell; *Predictive-State Decoders: Encoding the Future into Recurrent Networks*; NIPS 30; 2017; [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2017/hash/61b4a64be663682e8cb037d9719ad8cd-Abstract.html) | 显式监督 recurrent state 预测 future observations | **supported**；正式摘要直接支持 |
| Vafa et al. | Keyon Vafa, Justin Y. Chen, Ashesh Rambachan, Jon Kleinberg, Sendhil Mullainathan; *Evaluating the World Model Implicit in a Generative Model*; NeurIPS 37:26941–26975; 2024; DOI [10.52202/079017-0846](https://doi.org/10.52202/079017-0846) | automaton-governed generative-model settings 中专门评估发现标准诊断遗漏的不一致 | **supported**；候选强度与正式论文的 DFA 范围一致 |
| World Models 正式版本 | David Ha, Jürgen Schmidhuber; *Recurrent World Models Facilitate Policy Evolution*; NeurIPS 31; 2018; [NeurIPS proceedings](https://proceedings.neurips.cc/paper/2018/hash/2de5d16682c3c35007e4e92982f1a2ba-Abstract.html) | compressed representations、recurrent world model、policy/imagination lineage | **supported**；必须把当前 `@misc` 的 arXiv identity 整体切换为正式 `@inproceedings`，不得混写两个版本 |

建议 entry type：

- MuZero：`@article`；
- IRIS、Genie、Predictive-State Decoders、Vafa et al.、World Models：`@inproceedings`；
- Drive-OccWorld：按 AAAI OJS 正式 volume/issue 记录采用 `@article` 最直接；若全库统一采用 `@inproceedings`，也必须完整保留 AAAI 39(9)、页码和 DOI。

没有发现元数据或引文强度层面的 P0/P1。当前 `references.bib` 尚未包含 6 个新增 key，且 `ha2018worldmodels` 仍是 arXiv 条目，这是受控应用阶段必须完成的预期变更，不是返修提案遗漏。

## 7. 写作语气与 TerraState 方法身份

### 7.1 防御式措辞

候选正文不含：

- `claims none`；
- `not a second version`；
- `without claiming`；
- `Unlike prior work, we are novel`；
- `first-ever`、`unprecedented` 或 SOTA 宣传。

P3 使用 `Complementing these objectives`，以共同比较维度定位最近邻；P4 使用 `Section 3 therefore constructs ...`，以机制响应收束。语气自信而非 rebuttal 化。

### 7.2 引用堆砌

- P1 的四篇 deterministic work 和两篇 probabilistic work 是范式级 citation cluster，句法上由类别统摄，不是逐篇摘要。
- P2 每篇新增 work 都有不同宾语和研究目标，没有机械列名。
- P3 只具体说明三个最接近 EO world-model objectives。
- P4 按 state definition → supervision → representation prediction → latent quality/control regularization → evaluation 递进。

模型名密度较高，但每个名称都有比较轴和句法职责，未达到 citation dump。

### 7.3 是否把 TerraState 降格为评测工具

没有。P4 的最终交接明确先构造：

1. on-path predictive state；
2. shared weather-conditioned transition；

再暴露：

3. state-removal interface；
4. weather-control interface。

这与当前 Method 的 `history → z_t → T_\psi → z_{t+h} → r_h → b_h+r_h` 计算路径一致。测试接口依附于方法结构，而不是取代方法结构。

## 8. P4 与 Conclusion 专项检查

### 8.1 P4 → Method

末句：

> `Section 3 therefore constructs TerraState around an on-path predictive state, a shared weather-conditioned transition, and state-removal and weather-control interfaces that make this bounded claim testable.`

判定：**PASS**。

- `on-path predictive state` 对应 Q2 的主要状态移除接口；
- `shared weather-conditioned transition` 对应未来天气唯一进入的声明路径；
- `state-removal` 对应 Q2 primary；
- `weather-control` 对应 Q3 actual-vs-donor/mean substitutions；
- `bounded claim` 防止将接口扩大为通用 world-model 定义。

### 8.2 Conclusion 压缩

返修候选共约 76 词，保留：

- history-derived spatial state；
- shared weather-conditioned transition；
- explicit forecast contribution；
- future-state anchoring；
- state-removal 与 weather-substitution；
- Q1 useful OOD-t skill；
- Q2 state-removal degradation；
- Q3 actual-weather complete-window fidelity；
- 非 complete physical / causal world model 的边界。

判定：**PASS**。它不再把 TerraState 收缩为“预测器 + 两个测试”。

## 9. 词数与页面可行性

### 9.1 词数复核

采用提案声明的严格口径：

- 只统计四段英文 prose；
- 去除 paragraph 标题与 `\cite{...}`；
- 普通连字符复合词计一个 token；
- LaTeX `state--transition--prediction` 计三个并列词。

独立复算结果：**409 词**。  
当前正文 Related Work：约 348 词。  
净增加：约 **61 词**。

### 9.2 当前页边界

当前 PDF 为 **8 页**：

- 第 7 页包含实验尾部、Limitations 和 Conclusion 大部；
- Conclusion 最后两行位于第 8 页；
- References 从第 8 页开始，并在当前第 8 页结束。

返修 Conclusion 从当前约 109 词减至约 76 词，节省约 33 词。仅采用 Related Work 和 Conclusion 两项时，主文仍净增加约 28 词，不能据此保证 Conclusion 回到第 7 页。

若同时采用第一次审计已裁决为边界安全的约 91 词 Limitations 压缩（当前约 150 词，节省约 59 词），主文相对当前状态净减少约 31 词，足以使“第 7 页结束正文”成为合理目标。新增 6 条正式参考文献预计会让 References 从当前单页延伸至第 8–9 页。

判定：

- **409 词 Related Work：PASS**；
- **主文第 7 页收口：条件可行，尚未编译确认**；
- **References 占第 8–9 页：可行但尚未编译确认**；
- 不允许通过字号、页边距、负 `vspace` 或删减证据边界来实现页数。

## 10. Q1–Q3 与能力边界

| 检查项 | 候选实际语义 | 判定 |
|---|---|---|
| Q1 | Related Work 不提前写数值；Conclusion 只说 useful OOD-t skill | **PASS** |
| Q2 | `removable contribution` / `state-removal`，没有把全部预测信息归于状态 | **PASS** |
| Q3 | actual forcing 相对 frozen controls 的 complete-window fidelity | **PASS** |
| Q4/composition/non-collapse | 只在提案边界和删除说明中作为禁止项出现，不进入候选正文 | **PASS** |
| causal/counterfactual | 候选正文不作正向主张；Conclusion 仅以否定边界出现 | **PASS** |
| complete physical state | 仅作为 Conclusion 的否定边界 | **PASS** |
| control/planning | 只描述 MuZero、World Models/PlaNet/Dreamer、PLSM、Drive-OccWorld 等他作的正式目标 | **PASS** |
| TerraState 的 control/planning 能力 | 未赋予 | **PASS** |
| SOTA/严格排名 | 候选正文无此主张 | **PASS** |

P4 的 `mediates weather forcing` 由紧邻的 `bounded claim`、P3 的 frozen-control fidelity 和全文现有非因果定义共同限定，不构成 causal mediation 主张。

## 11. 问题分级

### P0

**0。** 未发现事实错误、错误元数据、虚假引用或 TerraState 能力越界。

### P1

**0。** 未发现叙事链断裂、关键职责重复、防御式定位、Method 交接缺失或 claim–evidence 冲突。

### P2

**1。**

1. **Location:** Proposal §9 page plan.  
   **Issue:** 页面目标仍是估算；409 词 Related Work 加 76 词 Conclusion 本身不足以保证主文在第 7 页结束。  
   **Impact:** 不影响叙事、文献或科学正确性，但影响最终版面门禁。  
   **Controlled-application action:** 同时采用已经审计为边界安全的 Limitations 去重方案或等量安全压缩，并在正式编译后检查第 7 页结尾、第 8–9 页 References、undefined citations 和 overfull boxes。不得把估算写成已实现事实。

该 P2 是实施阶段验证项，不要求再次返修本提案。

## 12. 受控应用的最小门禁

1. 仅用本提案四段候选替换 Section 2；
2. 新增六个正式 BibTeX 条目，使用官方完整作者顺序；
3. 将 `ha2018worldmodels` 整体切换为正式 NeurIPS 2018 identity；
4. 不加入 DreamerV3、TD-MPC2、Deep-OSG 或 group-action 引用；
5. 保留本提案的 Conclusion 安全压缩；若页边界需要，同时采用已审计的 Limitations 去重方案；
6. 编译后确认全文唯一引用为 28、missing/duplicate key 为 0；
7. 确认正文在第 7 页结束，第 8–9 页仅含 References；
8. 回归检查 Q1–Q3、Method 3.1、Limitations 和 Conclusion 的主张强度不变；
9. 受控应用完成后再执行局部引用、语言和版面回归，不在本轮修改任何正文。

## 13. 只读声明

本轮未修改：

- `paper/main.tex`；
- `paper/references.bib`；
- `paper/main.pdf`；
- 任何 `MANUSCRIPT*`；
- Figure、Table、caption；
- 实验、模型、结果或证据文件。

本轮唯一新建文件为：

`RELATED_WORK_WORLD_MODEL_EXPANSION_SECOND_AUDIT_20260729.md`

# READY_FOR_CONTROLLED_APPLICATION
