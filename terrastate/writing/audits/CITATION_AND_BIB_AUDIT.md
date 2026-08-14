# TerraState 引用与 BibTeX 深度审计

审计日期：2026-07-27  
权威正文：`paper/main.tex`  
文献库：`paper/references.bib`

> 结果接入后复核：正文仍使用 30 个唯一引用键，文献库仍为 30 个唯一
> 条目；缺失、重复、未使用和 undefined citation 均为 0。Q1–Q3 接入没有新增
> 外部事实性文献主张，也没有改变 Published 面板的已核验来源。

## 1. 总结

- 正文共有 33 个 citation command、49 次键出现、30 个唯一引用键；BibTeX 共有 30 条。
- 缺失键 0、重复键 0、未使用条目 0、未知引用命令 0、未解析输入 0。
- 最终 BibTeX/LaTeX 编译无 undefined citation、undefined reference 或 multiply-defined label。
- 逐条检查没有发现会改变论文 novelty 定位的 claim-to-source mismatch。
- 已直接修正可由一手来源确定的元数据与 AAAI BibTeX 格式问题；没有为了增加数量而新增引用。
- EO-WM、VegSim、Observability Forecasting、LatentTSF 与 World Models as Group Actions 截至审计日仍按 arXiv 预印本处理；投稿前必须再次核验其 venue 状态。

## 2. 已修正（corrected）

1. `benson2024multimodal`：标题改为官方的 “Multi-modal Learning for Geospatial Vegetation Forecasting”。
2. `ebel2023uncrtaints`：页码由错误的 2085–2095 改为官方 2086–2096，并补 DOI `10.1109/CVPRW59228.2023.00202`。
3. `wang2023ssl4eo`：第二作者由错误的 “Nassim Al Braham” 改为 “Nassim Ait Ali Braham”，并补 DOI `10.1109/MGRS.2023.3281651`。
4. `luo2026eowm`、`iele2026vegsim`、`albughdadi2026observability`、`yang2026latenttsf`、`wang2026groupactions`、`ha2018worldmodels`、`bardes2024vjepa`：由把 arXiv 伪装成期刊的 `@article + journal={arXiv preprint...}` 改为 AAAI Author Kit 要求的 `@misc + eprint + archivePrefix`。
5. 补入官方 NeurIPS 页面提供的 DOI：Earthformer、MCVD、PLSM、SatMAE、CROMA。AAAI 的 `.bst` 当前不显示这些 DOI，但 BibTeX 元数据已完整。
6. Introduction 中把作者作为句法成分的两处引用改为 `\citet{}`；其余事实性括号引用继续使用 `\cite{}`。
7. VegeDiff 的稳定引用键仍为 `zhao2024vegediff`，但条目年份正确保留为期刊发表年 2025；不为改键而破坏正文映射。

## 3. 逐条核验

状态含义：

- **Verified**：标题、作者、年份、载体及可用页码/DOI/arXiv ID 与一手来源一致。
- **Corrected**：本轮发现并已修正至少一项字段。
- **Recheck**：当前元数据准确，但投稿前需重新检查 2026 预印本的录用/版本状态。

| 键 | 状态 | 核验结论与一手来源 |
|---|---|---|
| `requenamesa2021earthnet` | Verified | CVPR Workshops 2021，1132–1142；[CVF 官方页](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/html/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.html)。 |
| `benson2024multimodal` | Corrected | CVPR 2024，27788–27799；标题大小写已与 [CVF 官方页](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html) 一致。 |
| `shi2015convlstm` | Verified | NeurIPS 2015，作者、标题、卷 28 与 [NeurIPS 官方页](https://proceedings.neurips.cc/paper_files/paper/2015/hash/07563a3fe3bbe7e3ba84431ad9d055af-Abstract.html) 一致；官方 BibTeX 未给页码。 |
| `wang2017predrnn` | Verified | NeurIPS 2017，作者、标题、卷 30 与 [NeurIPS 官方页](https://proceedings.neurips.cc/paper_files/paper/2017/hash/e5f6ad6ce374177eef023bf5d0c018b6-Abstract.html) 一致；官方 BibTeX 未给页码。 |
| `gao2022simvp` | Verified | CVPR 2022，3170–3180；[CVF 官方页](https://openaccess.thecvf.com/content/CVPR2022/html/Gao_SimVP_Simpler_Yet_Better_Video_Prediction_CVPR_2022_paper.html)。 |
| `gao2022earthformer` | Corrected | NeurIPS 2022，25390–25403，DOI `10.52202/068431-1841`；[NeurIPS 官方页](https://proceedings.neurips.cc/paper_files/paper/2022/hash/a2affd71d15e8fedffe18d0219f4837a-Abstract-Conference.html)。 |
| `voleti2022mcvd` | Corrected | NeurIPS 2022，23371–23385，DOI `10.52202/068431-1698`；[NeurIPS 官方页](https://proceedings.neurips.cc/paper_files/paper/2022/hash/944618542d80a63bbec16dfbd2bd689a-Abstract-Conference.html)。 |
| `zhao2024vegediff` | Verified | IEEE TGRS 63 (2025)，1–14，DOI `10.1109/TGRS.2025.3564317`；[DOI 记录](https://doi.org/10.1109/TGRS.2025.3564317)。期刊最终作者为五人，当前条目正确。 |
| `luo2026eowm` | Corrected / Recheck | arXiv:2606.27277；当前只主张预印本身份；[arXiv 一手记录](https://arxiv.org/abs/2606.27277)。 |
| `iele2026vegsim` | Corrected / Recheck | arXiv:2606.21961；当前只主张预印本身份；[arXiv 一手记录](https://arxiv.org/abs/2606.21961)。 |
| `albughdadi2026observability` | Corrected / Recheck | arXiv:2607.13651；当前只主张预印本身份；[arXiv 一手记录](https://arxiv.org/abs/2607.13651)。 |
| `shinohara2025vitkoop` | Verified | ICCV Workshops 2025，2835–2844；[CVF 官方页](https://openaccess.thecvf.com/content/ICCV2025W/SEA/html/Shinohara_ViT-Koop_Vision-Transformer-Koopman_Operators_for_Efficient_Time-Series_Forecasting_of_Earth-Observation_Data_ICCVW_2025_paper.html)。 |
| `diaconu2022weather` | Verified | CVPR Workshops 2022，1362–1371；[CVF 官方页](https://openaccess.thecvf.com/content/CVPR2022W/EarthVision/html/Diaconu_Understanding_the_Role_of_Weather_Data_for_Earth_Surface_Forecasting_CVPRW_2022_paper.html)。 |
| `yang2026latenttsf` | Corrected / Recheck | arXiv:2602.00297；摘要直接支持“准确预测可伴随时序混乱潜表示”的叙述；[arXiv 一手记录](https://arxiv.org/abs/2602.00297)。 |
| `wang2026groupactions` | Corrected / Recheck | arXiv:2605.24578，页面状态为 under review；正文只称 concurrent work；[arXiv 一手记录](https://arxiv.org/abs/2605.24578)。 |
| `chen2023deeposg` | Verified | JCP 493，112498，DOI `10.1016/j.jcp.2023.112498`；[出版社页面](https://www.sciencedirect.com/science/article/pii/S0021999123005934)。 |
| `ha2018worldmodels` | Corrected | arXiv:1803.10122；未虚构会议载体；[arXiv 一手记录](https://arxiv.org/abs/1803.10122)。 |
| `hafner2019planet` | Verified | ICML 2019 / PMLR 97，2555–2565；[PMLR 官方页](https://proceedings.mlr.press/v97/hafner19a.html)。 |
| `hafner2020dreamer` | Verified | ICLR 2020；标题、作者与 [OpenReview 论文](https://openreview.net/forum?id=S1lOTC4tDS) 一致。 |
| `littman2001predictive` | Verified | NeurIPS 2001，三名作者（包括 Satinder Singh）由官方 PDF 题首页确认；[NeurIPS 官方页](https://proceedings.neurips.cc/paper_files/paper/2001/hash/1e4d36177d71bbb3558e43af9577d70e-Abstract.html)。 |
| `assran2023ijepa` | Verified | CVPR 2023，15619–15629；[CVF 官方页](https://openaccess.thecvf.com/content/CVPR2023/html/Assran_Self-Supervised_Learning_From_Images_With_a_Joint-Embedding_Predictive_Architecture_CVPR_2023_paper.html)。 |
| `bardes2024vjepa` | Corrected | arXiv:2404.08471；当前未添加未经确认的正式 venue；[arXiv 一手记录](https://arxiv.org/abs/2404.08471)。 |
| `saanum2024simplifying` | Corrected | NeurIPS 2024，38355–38382，DOI `10.52202/079017-1212`；[NeurIPS 官方页](https://proceedings.neurips.cc/paper_files/paper/2024/hash/43ba0466af2b1ac76aa85d8fbec714e3-Abstract-Conference.html)。 |
| `wang2023ssl4eo` | Corrected | IEEE GRSM 11(3)，98–106，DOI `10.1109/MGRS.2023.3281651`；[IEEE 官方页](https://ieeexplore.ieee.org/document/10261879/)。 |
| `manas2021seco` | Verified | ICCV 2021，9414–9423；[CVF 官方页](https://openaccess.thecvf.com/content/ICCV2021/html/Manas_Seasonal_Contrast_Unsupervised_Pre-Training_From_Uncurated_Remote_Sensing_Data_ICCV_2021_paper.html)。 |
| `cong2022satmae` | Corrected | NeurIPS 2022，197–211，DOI `10.52202/068431-0015`；[NeurIPS 官方页](https://proceedings.neurips.cc/paper_files/paper/2022/hash/01c561df365429f33fcd7a7faa44c985-Abstract-Conference.html)。 |
| `fuller2023croma` | Corrected | NeurIPS 2023，5506–5538，DOI `10.52202/075280-0241`；[NeurIPS 官方页](https://proceedings.neurips.cc/paper_files/paper/2023/hash/11822e84689e631615199db3b75cd0e4-Abstract-Conference.html)。 |
| `guo2024skysense` | Verified | CVPR 2024，27672–27683；[CVF 官方页](https://openaccess.thecvf.com/content/CVPR2024/html/Guo_SkySense_A_Multi-Modal_Remote_Sensing_Foundation_Model_Towards_Universal_Interpretation_CVPR_2024_paper.html)。 |
| `ebel2023uncrtaints` | Corrected | CVPR Workshops 2023，2086–2096，DOI `10.1109/CVPRW59228.2023.00202`；[CVF 官方页](https://openaccess.thecvf.com/content/CVPR2023W/EarthVision/html/Ebel_UnCRtainTS_Uncertainty_Quantification_for_Cloud_Removal_in_Optical_Satellite_Time_CVPRW_2023_paper.html)。 |
| `wang2022pvtv2` | Verified | *Computational Visual Media* 8，415–424，DOI `10.1007/s41095-022-0274-8`；[Springer 版本页](https://link.springer.com/article/10.1007/s41095-022-0274-8)。 |

## 4. Table 1 / Contextformer 数值核验

`paper/main.tex` 的 Published panel 与 Contextformer 论文 Table 2 逐项一致：

- Persistence：\(0.00, 0.23, -1.28, 0.17, 21.8, 0.09\)；
- Previous year：\(0.56, 0.20, -0.40, 0.14, 19.3, 0.18\)；
- Climatology：\(0.58, 0.18, -0.34, 0.13, \mathrm{n.a.}, 0.16\)；
- ConvLSTM、PredRNN、SimVP、Contextformer 的均值与标准差一致；
- Earthformer 为论文中明确的一次运行，因此没有伪造标准差；
- TerraState 表格把 RMSE25 放在 Outperformance 之前，但对应数值已按列名正确重排；
- caption 的 “three seeds where available” 与原论文“可用模型三随机种子、Earthformer 单次运行”的说明一致。

来源：[Contextformer / GreenEarthNet 官方 CVF 页面](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html)及本地核验副本 `literature/contextformer_cvpr2024.pdf`。

Published 与 Local 两个面板仍明确分隔；本轮把投稿正文中的研发名称 “Matched B4” 改为公开显示名 “matched backbone”，但内部 schema/provenance 可继续使用 B4 标识。没有跨协议声称严格排名。

## 5. Claim-to-source 审计

### Verified

- EarthNet2021、GreenEarthNet/Contextformer 的任务定义、云掩膜、时间偏移和 20 m 预测设置由对应原论文支持。
- VegeDiff 的“概率建模植被变化不确定性”与 MCVD 的多未来预测定位由原论文支持。
- EO-WM 的部分可观测、天气驱动、climatology/anomaly/stress 分解及 response evaluation 由 arXiv 原文支持。
- VegSim 的潜在植被状态、未来天气 rollout、NDVI quantile 与 scenario simulation 由 arXiv 原文支持。
- LatentTSF 的“预测准确不保证潜状态时序有序”叙述由原文支持。
- PLSM 的“正则化动作对潜状态变化的依赖”叙述与 NeurIPS 摘要一致。
- Deep-OSG 的 semigroup-aware variable-time autonomous operator 描述准确；正文明确说明 TerraState 的有序、不可逆天气 forcing 不等同于该代数设置。
- World Models as Group Actions 只被称为 concurrent work，正文没有把它写成已录用论文或把 group action 强加给 TerraState。
- UnCRtainTS 被用于支持光学时间序列去云与不确定性建模，范围准确。

### Corrected

- Introduction 原先以两个孤立的括号引用承担句法成分；现改为 “the tests of `\citet{...}` / the rollout of `\citet{...}`”，使 natbib 语义与语法一致。
- “output-level weather-response benchmarks” 改为更准确的 “output-level weather-response tests”，避免把相关工作误写成独立 benchmark。

### Missing

- 没有发现支撑当前非结果性主张所必需但缺失的引用。
- 未新增 AAAI Figure 锚点论文引用，因为它们只服务于视觉审计，不构成 TerraState 的问题边界、方法来源或实验比较。

### Uncertain / 投稿前重检

- 2026 五篇并行预印本的 venue、版本号、作者顺序和标题可能在投稿前变化。必须按 arXiv/正式 proceedings 的最新一手记录重检，不能根据搜索摘要页升级为“已录用”。
- V-JEPA 当前仍按 arXiv 版本引用；若投稿前出现正式版本，只在元数据确定后更新。
- Local 结果、统计显著性、置信区间和 replication seed 均尚未产生；引用审计不能替代真实结果 provenance。

## 6. Citation placement 与 citation dumping

- `\cite{}` 用于括号式事实支撑；`\citet{}` 只在作者引用成为句子语法成分或 Table 1 caption 明确指向 Benson 等人时使用。
- 没有二手来源替代关键论断；表格数值直接回到 Contextformer 原论文。
- Related Work 的密集引用主要出现在“模型家族”和“EO 预训练家族”两处。它们各自承担一个清楚的分类句，而不是用同一引用支撑多个不相关事实，暂不构成 citation dumping。
- 不建议为达到某个引用数量继续机械添加文献。当前 30 篇已覆盖 EO forecasting、EO world models、predictive state、latent dynamics、future-feature prediction、EO representation learning及最接近的并行工作。

## 7. 工具与 provenance

- Citation inventory：`citation_audit/citation_inventory.json` 与 `.txt`。
- NeurIPS 官方 BibTeX 快照：`citation_audit/official_bib/`。
- Contextformer 原文：`literature/contextformer_cvpr2024.pdf`。
- Bib-Check 尝试记录：`citation_audit/bib_check_raw/`。该工具在当前版本因 `ArxivClient` 缺失 `search` 方法而失败，不能把失败输出当作文献证据。
- True Cite 原始输出：`citation_audit/true_cite_raw.json`。其字符串匹配把姓名顺序和缩写 venue 大量误报为 warning，因此只作为定位线索；最终结论来自上述一手来源的人工核验。

## 8. 建议新增 / 删除

### 建议新增

- 当前无必须新增项。Related Work 已覆盖 EO forecasting、EO world models、
  predictive-state/world-model concepts、structured latent dynamics 和最接近的
  EO 方法。
- AAAI Figure 锚点只用于视觉组织审计，不构成 TerraState 的方法来源、最接近工作
  或实验比较，因此不加入正文参考文献。
- 若 2026 concurrent preprint 在投稿前出现正式 proceedings/期刊版本，只更新原条目
  元数据与正文载体措辞，不重复新增同一工作的第二个键。

### 建议删除

- 当前无建议删除项。30 个条目全部被正文使用，且每个条目都服务于问题边界、
  方法来源、最接近工作或实验比较。
- 若最终删去 optional Q4 的全部正文讨论，可重新检查 Deep-OSG 与 group-actions
  引用是否仍有必要；在当前版本中二者直接界定“天气分段查询不等于群/半群定理”，
  因而暂时保留。

## 9. 2026-07-27 最小元数据更新

- `yang2026latenttsf` 已由 arXiv `@misc` 更新为 ICML 2026 正式会议条目：
  *Proceedings of the 43rd International Conference on Machine Learning*，
  PMLR 306。核验依据为 ICML/OpenReview 正式论文 PDF 的 proceedings 页脚；在
  PMLR 尚未公布稳定文章页码时未猜测 `pages` 字段。
- `bardes2024vjepa` 已由 arXiv `@misc` 更新为 *Transactions on Machine
  Learning Research* 正式期刊条目，并按 TMLR 官方 BibTeX 将作者名从
  `Mahmoud Assran` 修正为 `Mido Assran`，保留正式 OpenReview URL：
  `https://openreview.net/forum?id=QaCCuDfBk2`。
- 其余 28 个条目未改动。重新盘点得到 30 个正文引用键与 30 个 BibTeX 键：
  missing 0、unused 0、duplicate 0、undefined citation 0。
