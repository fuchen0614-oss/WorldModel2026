# TerraState AAAI-27 参考文献覆盖与七页边界专项审计

审计日期：2026-07-29  
审计性质：只读审计；未修改 `main.tex`、`main.pdf`、`references.bib`、`main.bbl` 或任何论文内容。  
权威输入：

- `paper/main.tex`
- `paper/main.pdf`
- `paper/references.bib`
- `paper/main.bbl`

## 0. 结论摘要

- **REFERENCE_COVERAGE: TARGETED_ADDITIONS_NEEDED**
- **PAGE_LIMIT: MINIMAL_FIX_REQUIRED**

当前参考文献数量本身不是问题：正文实际引用 22 篇，已经覆盖天气驱动 EO 预测、EO 世界模型以及 predictive-state/latent-dynamics 三条线的基本骨架。主要缺口集中在第三条线：

1. 缺少“以未来观测监督内部状态”的直接基础工作；
2. 缺少“输出表现良好仍不足以证明内部世界模型成立”的正式评测先例；
3. 当前 `ha2018worldmodels` 仍是题为 *World Models* 的 arXiv 条目，而不是 NeurIPS 2018 正式论文 *Recurrent World Models Facilitate Policy Evolution*。

因此无需重写 Related Work，也不建议机械增加引用。最小方案是新增 2 篇有明确职责的正式论文，并纠正 1 个版本身份。

页面方面，当前 PDF 共 8 页，但第 8 页顶部仍有 Conclusion 的最后两行，随后才开始 References。AAAI-27 明确要求第 7 页之后只能放参考文献，因此当前版本不合规；不过只需回收 2 行即可消除现有越界。考虑新增正文引用可能引发换行，建议实际预留 5–6 个单栏正文行，仍属于最小修复，不需要大规模重排。

## 1. 文件身份与审计可复现信息

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `304db26cc894ba73641c8b2d09acd5fd3f36da1a9f54c6f7b7480b07be52a5d2` |
| `paper/main.pdf` | `f9c3fce5e209b3506c0afa44e4c742b209ad21168f855419ae4e41c3aca2daed` |
| `paper/references.bib` | `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3` |
| `paper/main.bbl` | `266d0a680c3cf47a2711b09ba7b2ef6c0459d6dbdbfaa8b2118a8da3032e152b` |

计数方法：

- 从 `main.tex` 解析全部 `\cite{...}` 命令及 citation key；
- 以 `references.bib` 的 BibTeX entry 为条目集合；
- 以 `main.bbl` 的 `thebibliography` 与 `\bibitem` 为最终渲染核验；
- 按 `\section` 边界统计正文分布。

## 2. 引用总体统计

| 指标 | 当前值 |
|---|---:|
| `\cite` 命令数 | 22 |
| citation-key 出现次数 | 31 |
| 唯一正文引用文献 | 22 |
| BibTeX 条目 | 24 |
| `main.bbl` 渲染条目 | 22 |
| 缺失 BibTeX key | 0 |
| 重复 BibTeX key | 0 |
| 未使用 BibTeX 条目 | 2 |

未使用条目：

1. `chen2023deeposg`
2. `wang2026groupactions`

这两个未使用条目不会影响当前编译结果。它们是否清理属于书目维护问题，不是本次覆盖缺口；不建议为了“整洁”扩大本轮修改。

引用集中度：

- `benson2024multimodal`：6 次；
- `requenamesa2021earthnet`：3 次；
- `littman2001predictive`、`yang2026latenttsf`：各 2 次；
- 其余被引用文献：各 1 次。

`benson2024multimodal` 的较高频次有明确职责：既定义数据/benchmark 上下文，又承担对比实验与方法配置来源，不属于无意义重复。

## 3. 各 Section 引用分布

| Section | `\cite` 命令 | key 出现次数 | 唯一文献数 | 主要职责 |
|---|---:|---:|---:|---|
| Abstract/题头 | 0 | 0 | 0 | 摘要不放引用，正常 |
| Introduction | 5 | 6 | 4 | benchmark、精度证据缺口、PSR 动机、latent temporal disorder |
| Related Work | 14 | 21 | 21 | 三条研究线的主体覆盖 |
| Method | 1 | 2 | 2 | GreenEarthNet 配置与 PVT v2 |
| Experiments | 2 | 2 | 1 | GreenEarthNet 对比与数据协议 |
| Limitations | 0 | 0 | 0 | 主要为本文证据边界，无强制外引需求 |
| Conclusion | 0 | 0 | 0 | 总结本文结果，无强制外引需求 |

Related Work 内部三条线：

| 文献线 | `\cite` 命令 | key 出现次数 | 唯一文献数 |
|---|---:|---:|---:|
| A. Weather-conditioned EO/vegetation forecasting | 6 | 10 | 10 |
| B. EO world models与 forcing-conditioned simulation | 3 | 3 | 3 |
| C. Predictive-state representations、latent dynamics与可检验状态 | 5 | 8 | 8 |

分布判断：引用并未过少地集中在单一领域，但 C 线的“内部状态如何被未来监督”与“如何检验隐含世界模型”仍各缺一个直接来源。

## 4. 三条文献线的覆盖审计

### 4.1 A. Weather-conditioned EO / vegetation forecasting

当前覆盖：

- EarthNet2021：任务、数据与固定预测窗口；
- GreenEarthNet/Contextformer：多模态植被预测与当前实验基准；
- Diaconu et al.：天气信息在地表预测中的作用分析；
- ConvLSTM、PredRNN、SimVP、Earthformer：时空预测骨架；
- MCVD、VegeDiff：生成式预测；
- ViT-Koop：压缩 EO 状态与 Koopman 演化。

判断：

- 对“weather-conditioned future EO raster forecasting”的直接竞争面覆盖充分；
- GreenEarthNet 和 Diaconu 已经支撑天气输入与天气响应，不需要再补一批泛气候模型；
- 未发现一篇已正式发表于 AAAI/CVPR/ICCV/NeurIPS/ICLR/ICML、且同时具备 TerraState 的“显式预测状态 + 天气共享转移 + 状态移除 + actual/donor/mean 完整窗口检验”的直接同构竞争者。

结论：**本线无需强制新增文献。**

### 4.2 B. EO world models与 forcing-conditioned simulation

当前覆盖：

- EO-WM；
- VegSim；
- cloud-aware observability world model。

三篇均为 2026 preprint，正文已经用 “Recent preprints” 明确限定身份。这不是写作错误，而是该 EO 子方向仍处于快速形成阶段。

相邻的 AAAI 驾驶 world models、ICML weather/climate foundation models、ICLR satellite generative models可以提供广义背景，但它们通常是：

- action-conditioned autonomous-driving simulation；
- weather/climate field prediction；
- satellite image generation或representation learning；

而不是 TerraState 所研究的 weather-conditioned land-surface observation forecasting。机械加入会稀释论文的 EO 任务边界。

结论：**本线的直接工作覆盖目前可接受；无需为了拥有更多正式会议条目而补泛 world-model 文献。**

### 4.3 C. Predictive-state、latent dynamics与可干预/可检验状态

当前覆盖：

- Littman et al.：经典 predictive-state representation；
- Ha & Schmidhuber、PlaNet、Dreamer：latent world models；
- I-JEPA、V-JEPA：representation prediction；
- LatentTSF：输出准确与 latent temporal order 可脱钩；
- PLSM：作用于 latent state 的 action regularization。

真正缺失：

1. **future-observation supervision of internal state**：TerraState 的 future-state anchor 目前只有 JEPA 方向的宽泛背景，没有最贴近“让内部状态预测未来观测”的直接先例；
2. **world-model-specific evaluation gap**：论文核心论证是输出指标不能单独建立内部 world-model claim，目前只有 LatentTSF 支撑 latent temporal disorder，缺少直接讨论“隐含世界模型评测”的正式工作。

结论：**本线需要 2 个定向补充，但不需要扩写为新的 Related Work 小节。**

## 5. 定向候选与裁决

### 5.1 必须补充：Predictive-State Decoders

- **标题**：*Predictive-State Decoders: Encoding the Future into Recurrent Networks*
- **作者**：Arun Venkatraman, Nicholas Rhinehart, Wen Sun, Lerrel Pinto, Martial Hebert, Byron Boots, Kris Kitani, J. Andrew Bagnell
- **年份/场所**：NIPS 2017, Advances in Neural Information Processing Systems 30
- **正式来源**：[NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2017/hash/61b4a64be663682e8cb037d9719ad8cd-Abstract.html)
- **应支持的具体论断**：内部状态可以通过附加预测监督，被显式训练为承载未来观测信息的 predictive state。
- **建议插入位置**：
  - 首选：`main.tex` 约第 185–190 行，Related Work 的 “Predictive-state and latent-dynamics foundations” 中，在经典 PSR 定义之后、JEPA 之前；
  - 可采用一句最小邻接说明，不需要在 Method 再重复引用。
- **必要性**：**必须补充**。
- **与 TerraState 的差异**：该工作面向通用 recurrent networks、filtering、imitation learning 与 reinforcement learning；没有 EO、外生天气、共享 transition、状态贡献移除或天气替换检验。它支撑的是 future-state supervision 的方法谱系，不是 TerraState 的任务与证据贡献。

### 5.2 必须补充：Evaluating the World Model Implicit in a Generative Model

- **标题**：*Evaluating the World Model Implicit in a Generative Model*
- **作者**：Keyon Vafa, Justin Y. Chen, Ashesh Rambachan, Jon Kleinberg, Sendhil Mullainathan
- **年份/场所**：NeurIPS 2024, Advances in Neural Information Processing Systems 37
- **正式来源**：[NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/2f6a6317bada76b26a4f61bb70a7db59-Abstract-Conference.html)
- **应支持的具体论断**：标准生成表现或已有诊断良好，并不自动意味着模型恢复了连贯的内部世界模型；world-model claim 需要专门的结构性评测。
- **建议插入位置**：
  - 首选：`main.tex` 约第 187–193 行，在 LatentTSF 句之后加一句相邻评测背景；
  - 备选：Introduction 的 “output accuracy ... cannot by itself establish” 之后，但这会增加首页换行压力，因此不如 Related Work 稳妥。
- **必要性**：**必须补充**。
- **与 TerraState 的差异**：该工作在有限自动机、游戏、逻辑与导航任务上评估 generative model 的隐含世界结构；TerraState 不恢复自动机，也不提出通用 world-model coherence metric，而是针对 EO 模型建立 state-removal 与 weather-control 的操作性证据合同。

### 5.3 必须修正版本身份：World Models

- **当前条目**：`ha2018worldmodels`，题为 *World Models*，`@misc`，arXiv:1803.10122。
- **正式论文**：*Recurrent World Models Facilitate Policy Evolution*
- **作者**：David Ha, Jürgen Schmidhuber
- **年份/场所**：NeurIPS 2018, Advances in Neural Information Processing Systems 31
- **正式来源**：[NeurIPS proceedings](https://papers.nips.cc/paper/2018/hash/2de5d16682c3c35007e4e92982f1a2ba-Abstract.html)
- **应支持的具体论断**：compact latent dynamics/world models can support prediction and control。
- **建议插入位置**：正文 citation key 与现有位置可保持不变；只需将该 key 的 BibTeX identity 改为正式 NeurIPS 论文，避免把 arXiv 题名、arXiv id 和 proceedings metadata 混用。
- **必要性**：**必须修正**，但这是 1 个版本替换，不是新增 1 篇引用。
- **与 TerraState 的差异**：该工作是 action-conditioned RL environment modeling 与 policy evolution；TerraState 是 exogenous-weather-conditioned EO forecasting，并以预测状态的可干预性为核心。

裁决：当前 arXiv 条目作为一篇独立预印文本并非“虚假文献”，但它**仍不是用户要求核对的 NeurIPS 2018 正式版本**。若正文意图引用正式 world-model 基础工作，应切换至正式论文身份。

### 5.4 不建议补充：Self-Predictive Representations

- **标题**：*Data-Efficient Reinforcement Learning with Self-Predictive Representations*
- **作者**：Max Schwarzer, Ankesh Anand, Rishab Goel, R. Devon Hjelm, Aaron Courville, Philip Bachman
- **年份/场所**：ICLR 2021
- **正式来源**：[OpenReview](https://openreview.net/forum?id=uCQfPZwRaUu)
- **可支持论断**：通过预测未来 latent targets 学习状态表征。
- **潜在插入位置**：future-state/JEPA 句附近。
- **必要性**：**不建议补充**。
- **与 TerraState 的差异**：该工作是 Atari 中的 action-conditioned RL representation learning。加入 Predictive-State Decoders 后，此处的方法谱系已经足够；继续加入 SPR 会与 I-JEPA/V-JEPA 重复。

### 5.5 不建议补充：Predictive State Recurrent Neural Networks

- **标题**：*Predictive State Recurrent Neural Networks*
- **作者**：Carlton Downey, Ahmed Hefny, Byron Boots, Geoffrey J. Gordon, Boyue Li
- **年份/场所**：NIPS 2017, Advances in Neural Information Processing Systems 30
- **正式来源**：[NeurIPS proceedings](https://proceedings.neurips.cc/paper/2017/hash/2bb0502c80b7432eee4c5847a5fd077b-Abstract.html)
- **可支持论断**：predictive-state filtering 与 recurrent networks 的结合。
- **潜在插入位置**：经典 PSR 句之后。
- **必要性**：**不建议补充**。
- **与 TerraState 的差异**：该工作强调 PSR/RNN filtering 与学习，不是 future-state target 或 post-training intervention。Littman + Predictive-State Decoders 已覆盖所需基础。

### 5.6 不建议补充：ClimaX

- **标题**：*ClimaX: A Foundation Model for Weather and Climate*
- **作者**：Tung Nguyen, Johannes Brandstetter, Ashish Kapoor, Jayesh K. Gupta, Aditya Grover
- **年份/场所**：ICML 2023, Proceedings of Machine Learning Research 202
- **正式来源**：[PMLR](https://proceedings.mlr.press/v202/nguyen23a.html)
- **可支持论断**：多变量 weather/climate field modeling。
- **潜在插入位置**：forcing-conditioned simulation 背景。
- **必要性**：**不建议补充**。
- **与 TerraState 的差异**：ClimaX 的预测对象本身是 weather/climate fields；TerraState 将未来天气作为外生 forcing 来预测 EO land-surface observations。加入会扩大而非收紧相关工作范围。

## 6. 22 篇是否足够

判断不能只看数量：

- **A 线**：10 篇，直接 benchmark、天气作用与主要预测范式均已覆盖，充分；
- **B 线**：3 篇，数量少但都是最直接的新兴 EO world-model 工作，且正文诚实标为 preprints，基本充分；
- **C 线**：8 篇，数量看似充足，但缺少两个“职责唯一”的正式来源，因此仍需定向补充。

加入 2 篇后，正文唯一引用将由 22 增至 24；同时将 World Models 从 arXiv identity 切换为正式 NeurIPS identity。该规模足以覆盖论文横跨的三个研究群体，不需要追求更高引用数。

## 7. 第七页边界精确审计

### 7.1 当前 PDF 状态

- 页面尺寸：US Letter，612 × 792 pt；
- 总页数：8；
- 第 8 页并非 references-only。

第 8 页顶部存在的全部非参考文献内容恰好为 Conclusion 最后一句的后两行：

> modeling from an architectural assertion into an empirically  
> testable and falsifiable question.

对应完整句子：

> TerraState thereby turns an internal predictive-state claim in weather-driven EO world modeling from an architectural assertion into an empirically testable and falsifiable question.

定位信息：

- 非参考正文块约为 `x=54.0–292.5 pt, y=56.4–77.3 pt`；
- 左栏 `References` 标题约从 `y=90.0 pt` 开始；
- 第 8 页右栏参考文献从页顶附近开始。

因此不存在“只有标题或浮动标记”的解释空间：第 8 页明确含两行主文。

### 7.2 AAAI-27 规则与裁决

AAAI-27 Main Technical Track CFP 明确规定：

> 7 pages of main content, maximum total 9; pages beyond page 7 are reserved exclusively for references.

权威来源：[AAAI-27 Main Technical Track Call](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/)

当前裁决：**不合规，但属于最小越界。**

### 7.3 需要回收多少空间

- 消除当前越界的硬下限：**2 个单栏正文行**；
- 新增 2 篇引用若只在 Related Work 各承担一句，正文换行预计新增约 **1–2 行**；
- BibTeX 新增条目会增加 References 高度，但第 8 页仍有明显剩余空间，且总上限为 9 页；它们不构成七页主文边界的直接风险；
- 为避免字体度量、作者年份 citation 长度和浮动重排造成反复，建议目标回收：**5–6 个单栏正文行**。

这不是要求一次性删掉 5–6 行核心内容，而是建议用两个小幅去重修改形成安全余量。

## 8. 三个最小压缩方案

以下均为候选建议，本次审计未写入正文。

### 方案 1：只压缩 Conclusion 的重复收束

优先级：最高。

当前最后一句：

> TerraState thereby turns an internal predictive-state claim in weather-driven EO world modeling from an architectural assertion into an empirically testable and falsifiable question.

候选：

> TerraState therefore makes its internal predictive-state claim empirically testable and falsifiable.

预计效果：

- 减少约 13 个英文词；
- 大概率恰好回收当前溢出的 2 行；
- 不删除 Q1–Q3 结果、方法身份或限制声明；
- “weather-driven EO” 已在 Conclusion 前文与全篇多次建立，因此此处属于去重。

风险：加入两句新文献背景后，安全余量可能不足。

### 方案 2：方案 1 + 压缩 Limitations 中重复边界

优先级：推荐的稳健最小方案。

当前第二段可压缩为：

> Weather controls establish conditional predictive fidelity, not causal or counterfactual validity; the hot-dry interval crosses zero and does not support extreme-specific enhancement. State removal isolates a measurable state-mediated increment but does not imply that all outputs or historical information pass through this state.

预计效果：

- 在方案 1 基础上再回收约 2–3 个单栏行；
- 完整保留：
  - 非 causal；
  - 非 counterfactual；
  - 不支持 extreme-specific enhancement；
  - state removal 不代表全部信息必须通过该状态。

综合预计可回收约 4–5 行，通常足以吸收两条定向引用产生的换行。

### 方案 3：方案 1 + 方案 2 后仍不足时，压缩 Table 3 caption

优先级：第三；仅在重编译仍越界时使用。

当前 caption 的主要重复是 `frozen matched pairs`、control-minus-actual 定义和 subset 作用域的展开。候选：

> Weather interventions on 84 frozen pairs. $\Delta$Loss is masked loss over the complete 20-step forecast window (control minus actual; positive favors actual); intervals are geographic-cluster 95\% CIs, counts are descriptive, and $R^2$/RMSE apply only to this subset.

预计效果：

- 约再回收 1–2 个单栏行；
- 保留 84 pairs、完整 20-step window、符号方向、CI 类型、descriptive counts 与 subset metric scope；
- 不修改 Figure 3 或 Table 3 的数据与含义。

不建议：

- 改字体、页边距、行距、列间距或模板；
- 使用负 `\vspace`；
- 缩小图内文字；
- 删除 Q1–Q3 结果、限制声明或实验定义；
- 为省空间移除必要文献。

## 9. 推荐的唯一最小修改清单

按实施顺序：

1. 将 `ha2018worldmodels` 的 arXiv 条目替换为正式 NeurIPS 2018 *Recurrent World Models Facilitate Policy Evolution* 元数据，正文 key 可保持不变；
2. 在 Related Work 的 predictive-state/latent-dynamics 段定向加入：
   - Venkatraman et al., 2017, *Predictive-State Decoders*；
   - Vafa et al., 2024, *Evaluating the World Model Implicit in a Generative Model*；
3. 不扩写 A/B 两条线，不机械添加 ClimaX、SPR、PSRNN 或泛驾驶 world models；
4. 先压缩 Conclusion 最后一句；
5. 为两条新增引用预留换行，进一步压缩 Limitations 第二段；
6. 重编译后只有仍存在越界时，才压缩 Table 3 caption；
7. 验证第 8 页首个可见内容为 `References` 或参考条目，且第 8–9 页不存在任何主文、caption、表格或图。

## 10. 最终判定

### REFERENCE_COVERAGE: TARGETED_ADDITIONS_NEEDED

理由：现有 22 篇的领域骨架合理，A/B 线无需扩写；C 线缺少 future-state supervision 与 world-model-specific evaluation 两项直接正式来源，同时 World Models 使用的仍是 arXiv identity。属于可用 2 篇新增 + 1 个版本修正解决的定向缺口，不是重大文献空白。

### PAGE_LIMIT: MINIMAL_FIX_REQUIRED

理由：第 8 页只有 Conclusion 最后两行属于非参考内容，违反 AAAI-27 references-only 边界；通过 Conclusion 去重即可消除现有越界，配合一处 Limitations 去重可为新增引用提供稳健余量，无需改变模板、图像或核心内容。

