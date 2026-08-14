# TerraState Related Work 扩充应用后独立回归终审

日期：2026-07-29  
任务性质：只读、应用后回归终审  
审计对象：受控应用后的正文、BibTeX、PDF 与三份 Markdown 镜像

## 1. 最终判定

**READY_FOR_FINAL_GLOBAL_FREEZE_AUDIT**

问题计数：

| 等级 | 数量 |
|---|---:|
| P0 | **0** |
| P1 | **0** |
| P2 | **1** |

判定依据：

- `main.tex` 的新增 Section 2 四段与通过二次审计的候选逐段一致，严格词数为 409；
- `Limitations and Scope` 与获批的 91 词候选一致，`Conclusion` 与获批的 76 词候选一致；
- Abstract、Introduction、Method、Experiments 的当前局部 SHA 与应用记录所列修改前后共同 SHA 完全一致；
- 当前 BibTeX 只增加指定六篇文献，并将 `ha2018worldmodels` 完整切换为正式 NeurIPS 2018 版本；
- Genie 的 PMLR 正式作者数经本轮独立重数为 **25**，当前 BibTeX 也是 25，顺序一致；
- 引用图为 28 个唯一 key，missing=0，duplicate=0；
- Introduction → Related Work → Method → Q1/Q2/Q3 连续，TerraState 保持方法主体；
- 三份镜像的对应正文和引用集合同步，中译没有提高主张强度；
- PDF 为 9 页，第 7 页完整结束正文，第 8–9 页仅含 References；
- 编译日志无 error、undefined citation/reference、BibTeX warning 或 overfull box。

唯一 P2 是 7 个 underfull hbox 与 1 个 underfull vbox 的工具警告；逐页渲染未见裁切、重叠、标题悬空或异常空白，不影响冻结。

## 2. 审计范围与当前文件身份

### 2.1 SHA-256

| 文件 | 当前 SHA-256 | 与作者给定值 |
|---|---|---|
| `RELATED_WORK_WORLD_MODEL_EXPANSION_APPLICATION_LOG_20260729.md` | `35314e82c818fa37c3a76660b564d432be87897e1466e04f2cb6609144f11e75` | 输入记录 |
| `RELATED_WORK_WORLD_MODEL_EXPANSION_SECOND_AUDIT_20260729.md` | `603d2d01e5cccdc2cabd5f8e2051af5558c54745ab3dfae73e92cc5558c6e635` | 输入记录 |
| `paper/main.tex` | `05a89a3f9329cd55af1bf98222db12ebf96eb5e20377948c81bd5b0a9a117ded` | **MATCH** |
| `paper/references.bib` | `4fd6cec24ab29d097ad4fa28fdd4f8479fe059ed05e5db57a3b4023a0210cf8a` | **MATCH** |
| `paper/main.pdf` | `6d85dcdcaa31e6b637a632ee5b491d85324b88a0860edf063c76904b87b870c0` | **MATCH** |
| `MANUSCRIPT.md` | `d5e1d532536619cbae7e055542e55ae0176b090a4deb99583038feb1110ba22e` | 当前事实源 |
| `MANUSCRIPT_ZH.md` | `1b8920dfe9f22e4332c5f60fb82af6ecc3988ad3aa358dc9f0529a0b4b2a8504` | 当前事实源 |
| `MANUSCRIPT_ZH_FULL.md` | `98084ad43570d3d8c48d5a6f2ef7fc5e877aeb575ff37f5a0469cd1c48df504f` | 当前事实源 |

### 2.2 审计方法

本轮没有以 application log 的 PASS 声明代替核验，而是独立执行：

1. 重新提取 `main.tex` 的 Section 2、Limitations、Conclusion；
2. 与两份获批提案候选逐段规范化空白后比较；
3. 重新计算冻结区块 SHA；
4. 重新运行只读 citation inventory；
5. 对七个新建/变更 BibTeX identity 逐项对照官方来源；
6. 重新从 PMLR 页面提取 Genie 作者字段并独立计数、比序；
7. 重新读取 `main.log`、`main.blg`、`main.bbl` 和 9 页 PDF；
8. 渲染并肉眼检查 Section 2 所在页及第 7–9 页；
9. 独立比较英文正文、英文镜像和两份中文镜像。

没有重新编译，也没有写入临时结果到论文目录。

## 3. 实际修改范围回归

### 3.1 `main.tex`

当前局部 SHA 按“从本节标题开始并包含下一节标题”这一应用记录口径复算：

| 冻结区块 | 本轮实测 SHA-256 | 应用记录的修改前后共同 SHA | 判定 |
|---|---|---|---|
| Abstract | `86d59f313f2c09925f357b9bff0924685cc75b48f46ffd3fcc6691ec269a53e0` | 同左 | **UNCHANGED** |
| Introduction | `09233d4eb27f2814f69dc1cb3df075a883aa22d1e4f0bb027c472d37c2d70e32` | 同左 | **UNCHANGED** |
| Method | `ab3faa77b35306692636b6f76478db05a21871dfc4cf781f1d50398dcbee4f4f` | 同左 | **UNCHANGED** |
| Experiments | `be0f5f75e6e7cf526b6bbbd9f4bca70b4d9a83b9b7eea90d5f307839a8dedd06` | 同左 | **UNCHANGED** |

三个授权区块的独立比对：

| 应用区块 | 获批来源 | 本轮比对 | 规范化正文 SHA-256 |
|---|---|---|---|
| Section 2，P1 | Revised proposal §5.1 | 逐字一致 | `9124c8801efd0e9203e4248d8b105eb4eb0bc0f804ed811da4a016bf58eddde0` |
| Section 2，P2 | Revised proposal §5.2 | 逐字一致 | `bd6b4f12a941a99ebfca076cfe4135d76141a29ecb28b51aa66fcfb54ab0c9ae` |
| Section 2，P3 | Revised proposal §5.3 | 逐字一致 | `504257f7a007e34796cd12b0749fb594b8ffbddee93a19a728b3f507bba80ad5` |
| Section 2，P4 | Revised proposal §5.4 | 逐字一致 | `40ee6302df547aa3c95b6215a773039a59d5c12d38111d29ae7613d64c1bdf40` |
| Limitations | Original proposal §12.3 | 逐字一致 | `baaa169a51e690ca6fe601d2ca1c5fb2120baf8e22598c5907995ab62ab0707c` |
| Conclusion | Revised proposal §9.2 | 逐字一致 | `77c6674a8fb8e2ae21f2ed1a4ec74b6f12b6fb14f51c91a7cae9c89fdb53cec8` |

结论：`main.tex` 的实质改动严格落在 Section 2、Limitations 和 Conclusion。公式、Method、Experiments、Table 1–3、captions、Q1–Q3 数值及 40 epochs / 14,880 updates 身份未被该应用改变。

### 3.2 `references.bib`

当前条目数由 24 增至 30：

- 新增且仅新增：
  `schrittwieser2020muzero`、
  `micheli2023iris`、
  `bruce2024genie`、
  `yang2025driveoccworld`、
  `venkatraman2017predictivestate`、
  `vafa2024evaluating`；
- `ha2018worldmodels` 从 arXiv `@misc` 完整切换为正式 NeurIPS 2018 `@inproceedings`；
- 其余原有 key 均保留；
- DreamerV3、TD-MPC2 未加入；
- `chen2023deeposg`、`wang2026groupactions` 仍只是未使用 BibTeX 条目，没有恢复正文引用。

### 3.3 镜像与 PDF

- 三份 `MANUSCRIPT*` 只同步对应 Section 2、Limitations、Conclusion 及引用导航；
- `main.pdf` 是上述授权文本和 BibTeX 的派生编译产物；
- 没有发现 Figure、Table 或实验内容因本轮应用发生变化。

**范围判定：PASS。**

## 4. 409 词候选一致性

词数口径：

- 只统计四段 prose；
- 去除 `\paragraph{...}` 和 `\cite{...}`；
- 普通连字符复合词计一个 token；
- `state--transition--prediction` 计三个并列词。

独立复算：**409 词**。

四个段落的正文在规范化空白后分别与通过第二次审计的候选逐字相同，citation key 和标点也一致。没有在应用阶段自由加写、删写或替换句子。

**候选一致性：PASS。**

## 5. 跨章节叙事链

| 位置 | 当前职责 | 与下一环的接口 | 判定 |
|---|---|---|---|
| Introduction | 建立“固定时域输出精度不足以确认内部预测状态”的 gap，并提出 forecast-bearing / weather-responsive state 问题 | P1 先回到 EO forecasting 的现有范式与证据类型 | **PASS** |
| Related Work P1 | EO forecasting：deterministic、probabilistic、latent/weather-response routes | 从 forecast outputs 收紧到 explicit internal state | **PASS** |
| Related Work P2 | general world models：latent rollout、task-relevant targets、tokenized interaction、occupancy forecasting | 说明不同目标共享 state–transition–prediction 结构，导向 EO-specific state account | **PASS** |
| Related Work P3 | EO world models：forcing、scenario simulation、observability | 精确定位 removable state contribution 与 actual-vs-control fidelity | **PASS** |
| Related Work P4 | predictive-state semantics、future-observation supervision、latent quality 与专门评估 | 交给 on-path state、shared transition、state-removal、weather-control interfaces | **PASS** |
| Method 3.1–3.4 | 实现 `history → z_t → T_\psi → z_{t+h} → r_h → b_h+r_h`，并定义两个冻结干预接口 | Section 4 用同一最终模型回答 Q1–Q3 | **PASS** |
| Q1 | 证明模型保留有用 OOD-t 预测能力 | 为内部状态检验提供 forecasting prerequisite | **PASS** |
| Q2 | state removal 为 primary，identity transition 为 supporting | 支持 state-mediated forecast contribution load-bearing | **PASS** |
| Q3 | actual future weather 相对 donor/mean controls 的 complete-window fidelity | 支持 bounded weather-responsive predictive state | **PASS** |

没有出现 Introduction 设问与 Related Work gap 不一致、Related Work 提出 Method 未回答的问题，或 Conclusion 强于 Q1–Q3 的情况。

## 6. TerraState 方法主体检查

Section 2 的最终交接为：

> `Section 3 therefore constructs TerraState around an on-path predictive state, a shared weather-conditioned transition, and state-removal and weather-control interfaces that make this bounded claim testable.`

该句先给出：

1. on-path predictive state；
2. shared weather-conditioned transition；

再给出：

3. state-removal interface；
4. weather-control interface。

Method 随后展开 projector、direct-per-horizon transition、state readout 和 additive forecast contribution；Conclusion 同时保留 state、transition、forecast contribution 与 future-state anchoring。因此 TerraState 是暴露可检验接口的方法模型，不是附加在普通预测器外部的评测包装。

**方法主体判定：PASS。**

## 7. 七个变更文献的正式元数据

本表直接以官方期刊、Proceedings、PMLR、ICLR 或 NeurIPS 页面核验；未沿用前一份报告的作者计数。

| Key | 当前 BibTeX identity | 官方核验 | 判定 |
|---|---|---|---|
| `schrittwieser2020muzero` | Julian Schrittwieser, Ioannis Antonoglou, Thomas Hubert, Karen Simonyan, Laurent Sifre, Simon Schmitt, Arthur Guez, Edward Lockhart, Demis Hassabis, Thore Graepel, Timothy Lillicrap, David Silver；Nature 588:604–609；2020；DOI `10.1038/s41586-020-03051-4` | [Nature version of record](https://doi.org/10.1038/s41586-020-03051-4) | **PASS**；`Chess/Shogi` 的标题大小写差异不改变 work identity |
| `micheli2023iris` | Vincent Micheli, Eloi Alonso, François Fleuret；*Transformers are Sample-Efficient World Models*；ICLR 2023；OpenReview `vhFu1Acb0xb` | [ICLR official page](https://iclr.cc/virtual/2023/oral/12543) | **PASS**；无虚构页码 |
| `bruce2024genie` | Jake Bruce 至 Tim Rocktäschel；ICML 2024；PMLR 235:4603–4623 | [PMLR official record](https://proceedings.mlr.press/v235/bruce24a.html) | **PASS**；见 §7.1 的独立作者重数 |
| `yang2025driveoccworld` | Yu Yang, Jianbiao Mei, Yukai Ma, Siliang Du, Wenqing Chen, Yijie Qian, Yuxiang Feng, Yong Liu；AAAI 39(9):9327–9335；2025；DOI `10.1609/aaai.v39i9.33010` | [AAAI official record](https://ojs.aaai.org/index.php/AAAI/article/view/33010) | **PASS** |
| `venkatraman2017predictivestate` | Arun Venkatraman, Nicholas Rhinehart, Wen Sun, Lerrel Pinto, Martial Hebert, Byron Boots, Kris M. Kitani, J. Andrew Bagnell；NIPS 30:1172–1183；2017 | [NeurIPS official record](https://proceedings.neurips.cc/paper_files/paper/2017/hash/61b4a64be663682e8cb037d9719ad8cd-Abstract.html) | **PASS** |
| `vafa2024evaluating` | Keyon Vafa, Justin Y. Chen, Ashesh Rambachan, Jon Kleinberg, Sendhil Mullainathan；NeurIPS 37:26941–26975；2024；DOI `10.52202/079017-0846` | [NeurIPS official record](https://proceedings.neurips.cc/paper_files/paper/2024/hash/2f6a6317bada76b26a4f61bb70a7db59-Abstract-Conference.html) | **PASS** |
| `ha2018worldmodels` | David Ha, Jürgen Schmidhuber；*Recurrent World Models Facilitate Policy Evolution*；NeurIPS 31:2455–2467；2018 | [NeurIPS official record](https://proceedings.neurips.cc/paper/2018/hash/2de5d16682c3c35007e4e92982f1a2ba-Abstract.html) | **PASS**；不再混用 arXiv 题名、ID 或 entry type |

### 7.1 Genie 作者独立重数

PMLR 官方 BibTeX 的作者顺序为：

1. Jake Bruce
2. Michael D. Dennis
3. Ashley Edwards
4. Jack Parker-Holder
5. Yuge Shi
6. Edward Hughes
7. Matthew Lai
8. Aditi Mavalankar
9. Richie Steigerwald
10. Chris Apps
11. Yusuf Aytar
12. Sarah Maria Elisabeth Bechtle
13. Feryal Behbahani
14. Stephanie C.Y. Chan
15. Nicolas Heess
16. Lucy Gonzalez
17. Simon Osindero
18. Sherjil Ozair
19. Scott Reed
20. Jingwei Zhang
21. Konrad Zolna
22. Jeff Clune
23. Nando De Freitas
24. Satinder Singh
25. Tim Rocktäschel

本轮从 PMLR 页面直接提取 `author` 字段并以 `and` 独立分割：

- 官方作者数：**25**；
- 当前 BibTeX 作者数：**25**；
- 规范化重音、缩写空格与标点后，作者顺序：**完全一致**。

第二次审计报告中“PMLR 正式记录 26 位作者”的说法是报告计数笔误。应用记录已经指出该错误，当前 `references.bib`、`main.bbl` 和 PDF 均使用正确的 25 人列表；因此它不是当前 P0/P1。

## 8. 新增 citation-to-claim 支撑

| `main.tex` 位置 | 引用 | 原子主张 | 官方证据 | 判定 |
|---|---|---|---|---|
| P2 | `schrittwieser2020muzero` | MuZero 预测 planning-relevant policy、value、reward | Nature 摘要直接列出三类 prediction targets | **supported** |
| P2 | `micheli2023iris` | IRIS 在 tokenized world model 中学习 agent | ICLR 摘要说明 discrete autoencoder、autoregressive Transformer 与 agent learning | **supported** |
| P2 | `bruce2024genie` | Genie 从视频学习 action-controllable environments | PMLR 摘要直接描述从视频训练和 action-controllable virtual worlds | **supported** |
| P2 | `yang2025driveoccworld` | Drive-OccWorld 将 action-conditioned occupancy forecasting 连接到 driving planning | AAAI 摘要直接描述 action conditions、4D occupancy forecasting 和 end-to-end planning | **supported** |
| P4 | `venkatraman2017predictivestate` | PSD 显式监督 recurrent internal state 预测 future observations | NeurIPS 摘要直接描述 additional state supervision | **supported** |
| P4 | `vafa2024evaluating` | automaton-governed generative-model setting 中，专门评估发现标准诊断遗漏的不一致 | NeurIPS 摘要明确限定 deterministic finite automaton 并报告 existing diagnostics 与 coherence 的落差 | **supported** |
| P2 | `ha2018worldmodels` | control-oriented lineage 使用压缩观测与 recurrent latent transition 支持 policy/imagination | NeurIPS 正式摘要与论文方法直接支持 | **supported** |

IRIS 与 Genie 虽位于同一句，但分别支持 agent learning 与 action-controllable environment generation，不是重复职责。Vafa 的结论保持 DFA/automaton 范围，没有外推到 EO latent states。

**新增引用支撑：PASS。**

## 9. 引用图完整性

只读运行：

```text
python .../cite-bib-check/scripts/citation_inventory.py \
  --bib paper/references.bib \
  --tex paper/main.tex \
  --output <temporary-directory>/inventory.json
```

结果：

| 项目 | 数量 |
|---|---:|
| TeX files | 1 |
| citation commands | 24 |
| cited-key occurrences | 37 |
| unique cited keys | **28** |
| BibTeX entries | 30 |
| missing keys | **0** |
| duplicate keys | **0** |
| unused entries | 2 |
| unknown citation commands | 0 |
| unresolved inputs | 0 |

未使用条目仅为 `chen2023deeposg` 和 `wang2026groupactions`；未使用不构成投稿错误。

**引用图：PASS。**

## 10. 禁止主张与 Q1–Q3 边界

| 检查项 | 当前语义 | 判定 |
|---|---|---|
| Q1 | Conclusion 只写 useful OOD-t skill；没有 SOTA 或严格排名 | **PASS** |
| Q2 | `removable contribution`、`state-removal`；没有声称全部信息必须经状态 | **PASS** |
| Q3 | actual weather 相对 frozen controls 的 complete-window fidelity | **PASS** |
| Q4 / composition / non-collapse | 新 Section 2、Limitations、Conclusion 中不存在正向主张 | **PASS** |
| causal / counterfactual | 仅在 Limitations/Conclusion 作为否定边界 | **PASS** |
| complete physical state | 仅作为否定边界 | **PASS** |
| control / planning | 只用于准确描述 MuZero、World Models/PlaNet/Dreamer、PLSM 和 Drive-OccWorld 等他作目标 | **PASS** |
| TerraState control/planning capability | 未赋予 | **PASS** |
| SOTA / strict ranking | 不存在 | **PASS** |
| extreme-specific enhancement | Limitations 明确说 hot-dry interval 不支持 | **PASS** |

P4 的 `mediates weather forcing` 由 `bounded claim`、P3 的 frozen-control fidelity 和紧邻非因果边界限定，没有被写成因果 mediation。

## 11. 英文逐句与 AAAI 可读性

### 11.1 Section 2

| 段落 | 语法与句法 | 连接关系 | 术语与语气 | 判定 |
|---|---|---|---|---|
| P1 | 主谓、并列和 citation placement 正确；长句均由类别统摄 | task → paradigms → evidence → internal-state question | `forecast outputs`、`supplied weather` 稳定；无绝对化攻击 | **PASS** |
| P2 | MuZero、IRIS、Genie、Drive-OccWorld 各有明确谓词 | general lineage → differentiated objectives → EO-specific state | control/planning 只属于相关工作；无防御式 TerraState 清单 | **PASS** |
| P3 | EO-WM、VegSim、observability 各一句，修饰语指向清楚 | general WM → EO specialization → exogenous forcing → TerraState niche | `Complementing these objectives` 公平、自信 | **PASS** |
| P4 | state definition、supervision、representation、evaluation 顺序清楚 | foundations → failure of output-only inference → Method response | Vafa 范围充分限定；末句不把方法降格为 evaluation wrapper | **PASS** |

没有 comma splice、悬垂修饰、时态漂移、代词指向不明、机械 `however` 或 rebuttal 化短语。模型名密度较高，但均被范式句法组织，不构成 citation dump。

### 11.2 Limitations

三段职责为：

1. representation/deployment scope；
2. intervention evidence boundary；
3. external validity。

`not causal or counterfactual`、hot-dry null、all-information boundary、single-dataset scope 和未观测因素均保留。压缩没有把限制写成失败清单，也没有重新引出 Q4。

**判定：PASS。**

### 11.3 Conclusion

四句完成：

1. problem/testability；
2. method identity；
3. Q1–Q3 evidence；
4. bounded takeaway。

第二句保留 shared weather-conditioned transition 和 future-state anchoring；第三句的三个并列证据语法完整；最终句明确限制 complete physical / causal world model。整体简洁、自信，不像审计报告。

**判定：PASS。**

## 12. 中英文镜像

### 12.1 英文镜像

移除标题格式并规范化 citation 语法后：

| 区块 | `main.tex` vs `MANUSCRIPT.md` |
|---|---|
| Section 2 prose | **完全一致** |
| Limitations | **完全一致** |
| Conclusion | **完全一致** |

### 12.2 中文镜像

`MANUSCRIPT_ZH.md` 与 `MANUSCRIPT_ZH_FULL.md` 的三个相关区块正文哈希一致：

| 区块 | 规范化 SHA-256 |
|---|---|
| Related Work | `df843563b26acb6d6333085cd0f3ef7c293a9665541b5e92349e6f66d52e3667` |
| Limitations | `f7715235b52e6465f8b3bcebe8e70bfef15944b854105f35d1e552227a8c2a73` |
| Conclusion | `2bf5471cb00902ed542f5e2ed2ddb090162f0f06402e36bdc2068d5010141265` |

语义检查：

- `empirically testable` → “能够接受经验检验”，没有译成“已经证明”；
- `removable contribution` → “可移除贡献”，强度一致；
- `greater complete-window fidelity` → “更高的完整窗口保真度”，没有译成因果正确性；
- `does not support extreme-specific enhancement` → “不支持极端天气特异增强”；
- `without implying that all information passes through this state` → “不意味着所有信息都通过该状态”；
- `without establishing a complete physical or causal world model` → “不建立完整物理或因果世界模型”。

三个镜像的引用 key 集合均为 28，和 `main.tex` 相比 missing=0、extra=0。`MANUSCRIPT_ZH_FULL.md` 的非投稿导航保留边界提示，但没有加强投稿主张。

**镜像判定：PASS。**

## 13. PDF 与编译产物

### 13.1 PDF 独立读取

通过 PDF page tree 与逐页文本/渲染检查：

| 检查项 | 本轮结果 |
|---|---|
| 总页数 | **9** |
| page media box | 每页 612 × 792 pt，US Letter |
| 第 7 页 | Results 尾部、Table 1–3、完整 Limitations、完整 Conclusion；正文在本页结束 |
| 第 8 页 | 仅 `References` 及参考文献 |
| 第 9 页 | 仅参考文献续页 |
| Section 2 所在页 | 段落连续，无裁切、重叠或异常间距 |
| 第 7 页结尾 | Conclusion 无孤立残句或跨页 |
| 第 8–9 页 | 无正文、Figure、Table 或 caption 混入 |
| 模板异常 | 未见字体、页边距、栏宽或标题样式异常 |

第 9 页只含最后三条参考文献并有较大自然余白，但这符合“第 8–9 页仅 References”的目标，不是模板错误。

### 13.2 构建日志

当前 `.log`、`.blg`、`.bbl` 与 PDF 的时间顺序一致；`main.log` 明确记录：

> `Output written on main.pdf (9 pages, 11951640 bytes).`

诊断：

| 项目 | 数量 / 结果 |
|---|---|
| LaTeX errors / fatal errors | **0** |
| undefined citations | **0** |
| undefined references | **0** |
| multiply-defined labels | **0** |
| BibTeX warnings/errors | **0 / 0** |
| overfull hbox / vbox | **0 / 0** |
| underfull hbox / vbox | 7 / 1 |
| `main.bbl` bibitems | **28** |

Underfull warnings 中两条位于新 Section 2 的首段行区间；对对应 PDF 页的 1.5× 渲染检查没有发现不可接受的字间距或版面破坏。其余 warnings 位于既有正文。它们是非阻塞工具警告。

**PDF/构建判定：PASS WITH NON-BLOCKING P2。**

## 14. P0 / P1 / P2

### P0

**0。**

没有发现：

- 错误或虚假文献 identity；
- Genie 作者缺失、增添或乱序；
- missing/duplicate citation key；
- Q1–Q3 数字或结论被改变；
- causal、counterfactual、complete physical state、SOTA 等正向越界。

### P1

**0。**

没有发现：

- 未授权正文区块变化；
- 四段候选偏离；
- 叙事链断裂；
- TerraState 被降格为评测包装；
- 新引用范围扩大；
- 英中主张强度冲突；
- PDF 页边界、undefined citation/reference、overfull 或模板阻塞。

### P2

**1。**

#### P2-1 — Underfull 工具警告

- **Location:** `paper/main.log`，7 个 underfull hbox、1 个 underfull vbox；其中两条覆盖 Section 2 首段。
- **Issue:** TeX 报告局部行填充不足。
- **Independent visual result:** Section 2 页和第 7–9 页没有明显异常空隙、裁切、重叠或不可读行。
- **Impact:** 不影响语义、引用、主线或提交版面可信度。
- **Action:** 最终全局冻结审计中保留为 tool-only warning；不建议为消除日志数字而重新改写已通过的正文。

## 15. 只读声明

本轮未修改：

- `paper/main.tex`；
- `paper/references.bib`；
- `paper/main.pdf`；
- `MANUSCRIPT.md`；
- `MANUSCRIPT_ZH.md`；
- `MANUSCRIPT_ZH_FULL.md`；
- Figure、Table、caption；
- 实验、模型、数据或证据文件。

本轮唯一新建文件为：

`RELATED_WORK_WORLD_MODEL_EXPANSION_POST_APPLICATION_REGRESSION_AUDIT_20260729.md`

# READY_FOR_FINAL_GLOBAL_FREEZE_AUDIT
