# TerraState AAAI-27 提交前引用与 BibTeX 最终只读审计

审计日期：2026-07-28（UTC）  
审计范围：仅 `paper/main.tex` 与 `paper/references.bib`  
最终判定：**CITATION_BIB_FINAL_REVISE**

## 1. 结论

本次对 `main.tex` 的全部引用命令、22 个正文已引用 BibTeX 条目和全部
citation-bearing claims 进行了逐项检查，并以官方 proceedings、期刊/DOI、
PMLR、OpenReview、arXiv 和论文全文作为主要证据。

结论如下：

- 引用图完整：没有 undefined citation、缺失 key 或重复 key。
- 22 个已引用工作的身份、作者顺序、年份和正式/预印本版本均可确认；没有发现
  会把一篇工作误认成另一篇工作的 metadata 错误。
- 当前 BibTeX 对 VegeDiff、LatentTSF、EO-WM、VegSim、cloud observability
  等易混淆工作的版本身份处理正确。
- 20 处引用命令所邻接的具体 attribution 均得到原文支持；没有
  `unsupported` 或 `unable to verify` 的 citation-bearing claim。
- Table 1 的公共数值与 GreenEarthNet 正式论文 Table 2 完全一致，但 Table 1
  及其 comparison paragraph 没有直接引用数值来源。这是确认的提交前引用归因
  缺口。
- Introduction 对“标准 EO 预测证据主要是固定窗口输出精度”的概括有文献事实
  基础，但当前句子没有邻接引用，属于较弱的综合判断归因。

因此，本轮不是 bibliography identity failure，也不需要改动 Table 1 数值；只需
完成一轮很小的引用归因修复后再冻结。

## 2. 审计边界与输入 SHA-256

### 2.1 权威输入

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `1fe12204bad54b2b18a8debd5792cab9dff85a1e342cc35ca8df0e9a2d6eaab9` |
| `paper/references.bib` | `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659` |
| `FULL_TEXT_GLOBAL_CONSISTENCY_AUDIT_20260728.md` | `e0a104bbf8108a4f3886bb7c4d6908f29e15de53f5f0af90b4c0e03de15ba8b2` |
| `SECTION2_FINAL_AUDIT_20260728.md` | `8125dcb5cace88dd5f6c61483b497b9762d3f00e17733f4e62533fcb10c17e60` |
| `evidence_workspace/PUBLIC_BASELINES.md` | `eee41e90ea12ec9e939620863eace4aa888b99f47eb36bc162ed918d824b8fd0` |
| `evidence_workspace/TABLE_NOTES.md` | `3c485f58e354dfe7bbec506464a62a2f5e85a29610861aef19da12eabc593f04` |

### 2.2 明确排除

本轮没有审计 Markdown 镜像、附录、Reproducibility Checklist、Figure 视觉内容、
实验代码、模型权重或训练服务器；没有执行 LaTeX 编译。

## 3. 引用图完整性

静态抽取使用 `cite-bib-check` 的只读 `citation_inventory.py`，没有动态 citation
macro、未解析输入文件或 `\nocite{*}`。

| 项目 | 数量 |
|---|---:|
| TeX 文件 | 1 |
| citation commands | 20 |
| cited-key occurrences | 28 |
| unique cited keys | 22 |
| BibTeX entries | 24 |
| undefined/missing cited keys | 0 |
| duplicate BibTeX keys | 0 |
| unused entries | 2 |
| unknown citation commands | 0 |
| unresolved TeX inputs | 0 |

### 3.1 已引用 key

`albughdadi2026observability`, `assran2023ijepa`, `bardes2024vjepa`,
`benson2024multimodal`, `diaconu2022weather`, `gao2022earthformer`,
`gao2022simvp`, `ha2018worldmodels`, `hafner2019planet`,
`hafner2020dreamer`, `iele2026vegsim`, `littman2001predictive`,
`luo2026eowm`, `requenamesa2021earthnet`, `saanum2024simplifying`,
`shi2015convlstm`, `shinohara2025vitkoop`, `voleti2022mcvd`,
`wang2017predrnn`, `wang2022pvtv2`, `yang2026latenttsf`,
`zhao2024vegediff`.

### 3.2 未使用条目

| Key | 当前作用 | 判定 |
|---|---|---|
| `chen2023deeposg` | 已退出正文的 operator/composition 分支 | 未使用；信息性报告，不是错误 |
| `wang2026groupactions` | 已退出正文的 group-action/composition 分支 | 未使用；信息性报告，不是错误 |

二者不会被标准 BibTeX 流程输出到最终参考文献列表。是否删除属于 bibliography
hygiene 选择，不是本轮通过条件。

## 4. 自动筛查结果及人工裁定

### 4.1 Bib-Check

- Repository：<https://github.com/LeoJ-xy/Bib-Check>
- Resolved commit：`19e8edbeeec7e07710e2c9f38a8912369698685b`
- 模式：online check-only
- 写回参数：无；没有使用 `--fix`、`--autofix`、`--inplace` 或
  `--aggressive`
- 输入 Bib SHA：`e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659`
- 结果：24 entries；12 `OK`，12 `WARNING`，0 `ERROR`
- warning types：8 `CANDIDATE_FOUND_NO_DOI`、3
  `LOW_CONFIDENCE_CANDIDATE`、1 `YEAR_MISMATCH`、1 `VENUE_MISMATCH`

所有 warning 均经一手来源裁定：

1. EarthNet2021、GreenEarthNet、SimVP、ViT-Koop、Diaconu 和 I-JEPA
   的 IEEE DOI 建议是合法的可选 metadata 补充；缺少 DOI 不改变当前正式
   proceedings identity。
2. `ha2018worldmodels` 的 Zenodo DOI 是存档版本 DOI，不应被自动当作 formal
   venue DOI；当前 arXiv 版本记录是自洽的。
3. `hafner2019planet` 的 2018 年警告来自预印本年份；正式 ICML/PMLR 版本为
   2019，当前 BibTeX 正确。
4. `hafner2020dreamer` 被错误匹配到一本无关书籍章节，产生错误 DOI 和 venue
   warning；ICLR 2020 OpenReview 记录确认当前 BibTeX 正确。
5. LatentTSF、PSR 和 V-JEPA 的低置信度来自近期论文/旧 proceedings metadata/
   TMLR 索引差异，已由论文 PDF 与官方记录确认。

### 4.2 WisPaper True Cite

- 检查日期：2026-07-28 UTC
- 24 entries 中 19 个非 `@misc` 条目进入 API，5 个 `@misc` 被工具跳过。
- 19 个返回项均为 `verified=true`、title score = 1，但工具把 19 个全部标为
  warning；主要原因是完整 venue 名与缩写不一致，以及 `Last, First`、LaTeX
  重音字符和显示名造成的 author boolean mismatch。
- 5 个跳过项中，正文使用的 4 个为 World Models、EO-WM、VegSim 和
  cloud-observability；均已用官方 arXiv 页面人工核验。另一个跳过项
  `wang2026groupactions` 未被正文引用。

True Cite 的 0 pass / 19 warning 是该接口的字段匹配表现，不是 19 个真实
bibliography errors。

## 5. 已引用条目的逐条 metadata 核验

“Bib 状态”中的 `OK` 表示当前记录的工作身份与引用版本自洽；“可选补全”不计为
错误，也不构成本轮强制修改。

| Key | 核验后的正式身份 | Volume/pages 或文章号 | DOI/arXiv | Bib 状态与版本裁定 | 一手来源 |
|---|---|---|---|---|---|
| `requenamesa2021earthnet` | Requena-Mesa, Benson, Reichstein, Runge, Denzler；CVPR Workshops 2021 | 1132–1142 | DOI `10.1109/CVPRW53098.2021.00124` | **OK**；当前未写 DOI，仅为可选补全 | [CVF](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/html/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.html) |
| `benson2024multimodal` | Benson et al.；CVPR 2024 | 27788–27799 | DOI `10.1109/CVPR52733.2024.02625` | **OK**；作者顺序、重音字符正确；DOI 可选补全 | [CVF](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html) |
| `shi2015convlstm` | Shi et al.；NeurIPS/NIPS 2015 | vol. 28；802–810 | 无正式 DOI | **OK with completeness note**；当前 Bib 未写可核验页码，但官方 NeurIPS BibTeX 本身也留空 | [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2015/hash/07563a3fe3bbe7e3ba84431ad9d055af-Abstract.html) |
| `wang2017predrnn` | Wang et al.；NeurIPS/NIPS 2017 | vol. 30；879–888 | 无正式 DOI | **OK with completeness note**；当前 Bib 未写可核验页码，工作身份无误 | [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2017/hash/e5f6ad6ce374177eef023bf5d0c018b6-Abstract.html) |
| `gao2022simvp` | Gao, Tan, Wu, Li；CVPR 2022 | 3170–3180 | DOI `10.1109/CVPR52688.2022.00317` | **OK**；DOI 可选补全 | [CVF](https://openaccess.thecvf.com/content/CVPR2022/html/Gao_SimVP_Simpler_Yet_Better_Video_Prediction_CVPR_2022_paper.html) |
| `gao2022earthformer` | Gao et al.；NeurIPS 2022 | vol. 35；25390–25403 | DOI `10.52202/068431-1841` | **OK** | [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2022/hash/a2affd71d15e8fedffe18d0219f4837a-Abstract-Conference.html) |
| `voleti2022mcvd` | Voleti, Jolicoeur-Martineau, Pal；NeurIPS 2022 | vol. 35；23371–23385 | DOI `10.52202/068431-1698` | **OK**；冒号/连接号及 Chris/Christopher 是非实质显示差异 | [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2022/hash/944618542d80a63bbec16dfbd2bd689a-Abstract-Conference.html) |
| `zhao2024vegediff` | Zhao, Chen, Zhang, Xiao, Bai；IEEE TGRS 2025 | vol. 63；1–14；article 4410214 | DOI `10.1109/TGRS.2025.3564317` | **OK**；formal 版本为五位作者；key 含 2024 不改变 2025 年份 | [IEEE DOI](https://doi.org/10.1109/TGRS.2025.3564317) |
| `luo2026eowm` | Luo et al.；arXiv preprint 2026 | n/a | arXiv `2606.27277` | **OK**；未混写正式 venue | [arXiv](https://arxiv.org/abs/2606.27277) |
| `iele2026vegsim` | Iele, Mulero Ayllón, Soda, Tortora；arXiv preprint 2026 | n/a | arXiv `2606.21961` | **OK**；未混写正式 venue | [arXiv](https://arxiv.org/abs/2606.21961) |
| `albughdadi2026observability` | Mohanad Albughdadi；arXiv preprint 2026 | n/a | arXiv `2607.13651` | **OK**；未混写正式 venue | [arXiv](https://arxiv.org/abs/2607.13651) |
| `shinohara2025vitkoop` | Takayuki Shinohara；ICCV Workshops 2025 | 2835–2844 | DOI `10.1109/ICCVW69036.2025.00296` | **OK**；DOI 可选补全 | [CVF](https://openaccess.thecvf.com/content/ICCV2025W/SEA/html/Shinohara_ViT-Koop_Vision-Transformer-Koopman_Operators_for_Efficient_Time-Series_Forecasting_of_Earth-Observation_Data_ICCVW_2025_paper.html) |
| `diaconu2022weather` | Diaconu, Saha, Günnemann, Zhu；CVPR Workshops 2022 | 1362–1371 | DOI `10.1109/CVPRW56347.2022.00142` | **OK**；姓名重音与作者顺序正确；DOI 可选补全 | [CVF](https://openaccess.thecvf.com/content/CVPR2022W/EarthVision/html/Diaconu_Understanding_the_Role_of_Weather_Data_for_Earth_Surface_Forecasting_CVPRW_2022_paper.html) |
| `yang2026latenttsf` | Yang et al.；ICML 2026 | PMLR 306；当前正式 PDF 未给可独立确认的最终 page range | arXiv `2602.00297` 为对应预印本 | **OK with unresolved optional field**；正式 PDF 确认 ICML/PMLR 身份，不应降格为 preprint | [paper](https://openreview.net/pdf/f9677f148205ffd26d7535baccb38a68009925d1.pdf), [arXiv](https://arxiv.org/abs/2602.00297) |
| `ha2018worldmodels` | David Ha, Jürgen Schmidhuber；arXiv preprint 2018 | n/a | arXiv `1803.10122` | **OK**；`@misc` 与当前引用版本相符 | [arXiv](https://arxiv.org/abs/1803.10122) |
| `hafner2019planet` | Hafner et al.；ICML 2019 | PMLR 97:2555–2565 | 无 DOI | **OK**；2018 是预印本时间，不应替换正式 2019 年份 | [PMLR](https://proceedings.mlr.press/v97/hafner19a.html) |
| `hafner2020dreamer` | Hafner, Lillicrap, Ba, Norouzi；ICLR 2020 | 无 volume/pages | OpenReview `S1lOTC4tDS` | **OK**；Bib-Check 的书籍 DOI 匹配为无关 false positive | [OpenReview PDF](https://openreview.net/pdf?id=S1lOTC4tDS) |
| `littman2001predictive` | Littman, Sutton, Singh；NeurIPS/NIPS 2001 | vol. 14；1555–1561 | 无 DOI | **OK with source inconsistency note**；官方网页索引漏列 Singh，但论文 PDF 明确列出三位作者；当前 Bib 正确 | [NeurIPS PDF](https://proceedings.neurips.cc/paper/2001/file/1e4d36177d71bbb3558e43af9577d70e-Paper.pdf) |
| `assran2023ijepa` | Assran et al.；CVPR 2023 | 15619–15629 | DOI `10.1109/CVPR52729.2023.01499` | **OK**；DOI 可选补全 | [CVF](https://openaccess.thecvf.com/content/CVPR2023/html/Assran_Self-Supervised_Learning_From_Images_With_a_Joint-Embedding_Predictive_Architecture_CVPR_2023_paper.html) |
| `bardes2024vjepa` | Bardes et al.；TMLR 2024 | TMLR 无传统 volume/pages | OpenReview `QaCCuDfBk2` | **OK**；accepted TMLR 版本与当前作者顺序一致 | [OpenReview](https://openreview.net/forum?id=QaCCuDfBk2), [arXiv](https://arxiv.org/abs/2404.08471) |
| `saanum2024simplifying` | Saanum, Dayan, Schulz；NeurIPS 2024 | vol. 37；38355–38382 | DOI `10.52202/079017-1212` | **OK** | [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2024/hash/43ba0466af2b1ac76aa85d8fbec714e3-Abstract-Conference.html) |
| `wang2022pvtv2` | Wang et al.；Computational Visual Media 2022 | vol. 8, issue 3；415–424 | DOI `10.1007/s41095-022-0274-8` | **OK**；当前 Bib 省略 issue 3，不影响工作身份 | [Springer](https://link.springer.com/article/10.1007/s41095-022-0274-8) |

### 5.1 Metadata 总裁定

- **Confirmed wrong title/author/year/venue/pages/DOI/arXiv identity：0**
- 可选 metadata 完整性项：
  - 六个 CVF/IEEE proceedings 条目可补 DOI；
  - ConvLSTM、PredRNN 和 PSR 可补历史卷册页码；
  - PVT v2 可补 issue 3；
  - LatentTSF 的最终 PMLR page range 在当前可访问正式 PDF 中尚不可确认。
- 这些项不改变正文 attribution，也不要求在提交前全部补齐。若补，必须按同一正式
  版本成组补充，不能把 arXiv 年份与 proceedings 字段混合。

## 6. Citation-to-claim 支撑审计

Verdict 定义：

- `supported`：原文直接支持当前强度；
- `partially supported`：只支持部分原子主张或较弱版本；
- `unsupported`：原文不支持或相反；
- `unable to verify`：一手材料不足以裁定。

| `main.tex` 行 | Key | 原子主张与引用角色 | Verdict | 原文依据 |
|---:|---|---|---|---|
| 61–63 | `requenamesa2021earthnet` | EarthNet2021 将过去 Sentinel-2、地形和未来天气条件下的地表预测形式化为 guided video prediction | **supported** | 官方摘要及任务定义明确给出 satellite imagery、topography、future weather |
| 63–65 | `benson2024multimodal` | GreenEarthNet 聚焦 vegetation、改进 cloud mask、提供 temporal-shift evaluation 和 weather-conditioned forecasting | **supported** | 主文 Sec. 3.3–3.4、test-set definition 与 Contextformer 描述 |
| 83–90 | `yang2026latenttsf` | 准确 observation forecasts 可与时间结构混乱的 latent representations 共存 | **supported** | 论文将该现象定义并实证为 “Latent Chaos” |
| 92–94 | `littman2001predictive` | predictive state 可通过未来 observables 而非假设隐藏物理变量来定义 | **supported** | 摘要和正文以 action-conditional predictions of future observations 定义状态 |
| 140–143 | `requenamesa2021earthnet` | EarthNet2021 建立 weather-conditioned EO forecasting 任务 | **supported** | 官方任务定义 |
| 143–144 | `benson2024multimodal` | GreenEarthNet/Contextformer 将任务细化为 vegetation dynamics | **supported** | 正式 CVPR 论文的 dataset 与 model contribution |
| 144–146 | `diaconu2022weather` | 天气输入具有预测价值，并研究单变量天气改变下的输出响应 | **supported** | 摘要、weather ablation 与 generative single-variable simulations |
| 146–148 | `shi2015convlstm`, `wang2017predrnn`, `gao2022simvp`, `gao2022earthformer` | recurrent、convolutional、transformer deterministic predictors 的方法身份 | **supported** | 各原论文的架构和预测任务；其 GreenEarthNet adaptations 另由本段前引 Benson et al. 支持 |
| 149–150 | `voleti2022mcvd`, `zhao2024vegediff` | probabilistic video/diffusion 路线可表示多个可能未来 | **supported** | MCVD 为 probabilistic conditional diffusion；VegeDiff 明确 probabilistically captures uncertainty and multiple potential futures |
| 150–152 | `shinohara2025vitkoop` | ViT-Koop 用线性 Koopman operator 推进 compressed EO latent state | **supported** | 官方摘要和方法描述 |
| 159–163 | `luo2026eowm` | EO-WM 的 partially observed/weather-driven framing、climatology/anomaly/accumulated stress 和两类 output diagnostics | **supported** | arXiv 摘要及全文方法/benchmark 定义 |
| 163–166 | `iele2026vegsim` | VegSim 从 sparse NDVI history 推断 latent vegetation state，在用户天气下 recurrent rollout 并输出 NDVI quantiles | **supported** | arXiv 摘要直接给出全部组件 |
| 166–168 | `albughdadi2026observability` | cloud-aware world model 预测 usable acquisition 是否及何时出现，而非未来 land-surface pixels | **supported** | arXiv task definition |
| 176–179 | `littman2001predictive` | PSR 用未来可观测量预测定义状态 | **supported** | 同上；正文没有外推 classical sufficient-statistic guarantee |
| 179–181 | `ha2018worldmodels`, `hafner2019planet`, `hafner2020dreamer` | compact latent dynamics 用于 prediction/planning/control | **supported** | World Models 的压缩时空模型、PlaNet 的 latent planning、Dreamer 的 latent imagination |
| 181–183 | `assran2023ijepa`, `bardes2024vjepa` | I-JEPA/V-JEPA 进行 representation prediction 而非 raw-pixel reconstruction | **supported** | 两篇论文均明确预测 feature/target representations，V-JEPA 明确无 pixel reconstruction |
| 183–185 | `yang2026latenttsf` | 强 observation forecast 不保证有序 latent temporal structure | **supported** | 论文核心问题和实验 |
| 185–187 | `saanum2024simplifying` | PLSM 正则化 action 对 latent-state change 的作用，属于 agent-action/control setting | **supported** | NeurIPS 摘要和方法目标 |
| 253–264 | `wang2022pvtv2`, `benson2024multimodal` | PVT v2 与 Contextformer backbone 的方法身份 | **supported** | PVT v2 正式论文与 Contextformer architecture；“本模型使用 pretrained 实例”是 TerraState 自身实现事实，不由外文献代替证明 |
| 507–515 | `benson2024multimodal` | GreenEarthNet 的 30 个五日合成、10/20 history/forecast、128×128、20 m、meteorology/masks/geography 与 temporal-shift protocol | **supported** | GreenEarthNet Sec. 3.1、3.3–3.4；`1,904` 是本文冻结 manifest 的本地样本数，不是被外文献强行支持的数字 |

### 6.1 支撑统计

| Verdict | citation-command rows |
|---|---:|
| supported | 20 |
| partially supported | 0 |
| unsupported | 0 |
| unable to verify | 0 |

上述统计针对存在引用命令的 attribution。未带邻接引用的外部综合判断另列于第 8
节，不能用“20/20 supported”掩盖 missing-citation 问题。

## 7. Table 1 来源、类别与引用接口

### 7.1 数值核验

`main.tex:545–570` 中 Persistence、Previous year、Climatology、ConvLSTM、
Earthformer、PredRNN、SimVP 和 Contextformer 的所有 central values 与参数量，
均逐格匹配 Benson et al., CVPR 2024 主文 Table 2。

源论文的报告方式为：

- ConvLSTM、PredRNN、SimVP、Contextformer：三次随机种子的 mean ± standard
  deviation；
- Earthformer：一条 seed；
- 非学习基线：确定性计算。

当前 Table 1 只保留 central values，没有改低任何公共方法数值，也没有把所有结果
描述成 single-seed、没有使用 Published/Local 标签、没有 `±`、SOTA 或严格排名
措辞。正文明确说明 Q2/Q3 不由 table rank 建立。

### 7.2 方法类别

| Table 1 类别 | 方法 | 来源支持 | 判定 |
|---|---|---|---|
| non-learning | Persistence、Previous year、Climatology | GreenEarthNet Table 2 的 `NON-ML` 分组 | supported |
| recurrent | ConvLSTM | ConvLSTM 原论文；GreenEarthNet 的 weather-conditioned adaptation | supported |
| video prediction | PredRNN、SimVP | 原论文方法身份；GreenEarthNet Sec. 3.5 adaptation | supported |
| transformer-based | Earthformer、Contextformer | Earthformer 原论文；Contextformer/GreenEarthNet 正式论文 | supported |

### 7.3 确认的归因缺口

Table 1 caption 和 `main.tex:530–536` 的 comparison paragraph 都没有直接引用
`benson2024multimodal`。`main.tex:507–509` 虽在数据协议段引用该论文，但该引用的
邻接语义是 dataset/protocol，不能清楚承担后续整张公共数值表的来源归因。

这是**来源引用缺失，不是数值错误**。最小修复只需在 comparison sentence 或
Table 1 caption 邻接加入 `\cite{benson2024multimodal}`，并可用一句极短表注说明
“central/mean values are reported from the original publication; uncertainty is omitted for
compactness”。不需要加入 Published/Local、seed、single-run 或 `±`。

## 8. Confirmed errors

### E1 — Table 1 公共数值缺少直接来源引用

- **位置：** `paper/main.tex:530–570`
- **当前内容：** 公开 baseline 数值和参数量被直接列出，但 comparison paragraph
  与 caption 均无来源 citation。
- **一手证据：** Benson et al., CVPR 2024, Table 2；本地冻结论文
  `evidence_workspace/raw/sources/greenearthnet_cvpr2024.pdf` 的数值与当前表
  逐格相同。
- **影响：** 数字正确，但审稿人无法从表格邻接位置判断其出处和 central-value
  省略规则。
- **严重度：** Minor
- **最小方向：** 加一个邻接 `\cite{benson2024multimodal}`；不改数值和表格
  比较叙事。
- **本轮是否修复：** 否；只读审计。

## 9. Probable issues

### P1 — Introduction 的跨文献概括引用邻接偏弱

- **位置：** `paper/main.tex:83–90`
- **当前表述：** “Their primary evidence, however, remains pixel accuracy over a
  fixed forecast window.”
- **裁定：** EarthNet2021、GreenEarthNet 以及 Section 2 审阅的预测方法总体上
  支持“标准 benchmark 主要报告 output-level forecast metrics”；正文也没有说
  所有工作只做 pixel accuracy，并在 Section 2 公平承认 Diaconu、EO-WM 等
  response diagnostics。因此主张方向不是 unsupported。
- **问题：** 当前段落唯一 citation 位于稍后的 LatentTSF 反例，它不能承担
  EO benchmark/forecasting-literature 的整体经验概括。
- **影响：** 审稿人可能把该句理解为无来源的 field-wide generalization。
- **严重度：** Minor
- **最小方向：** 用已有 EarthNet2021/GreenEarthNet 引用邻接限定到“standard
  EO benchmarks/evaluations”，或在不扩大强度的前提下把现有引用移至该原子主张。
- **本轮是否修复：** 否；只读审计。

### P2 — 可选 metadata 完整性

ConvLSTM、PredRNN、PSR 的历史卷册页码和若干 CVF 论文 DOI 未写入 BibTeX；
PVT v2 未写 issue 3；LatentTSF 当前没有最终 page range。它们均不造成错误引用或
版本混写，故不进入 Critical/Major/Minor 计数。若作者统一补全，应一次只采用正式
版本 metadata，不应自动接受模糊匹配工具建议。

## 10. Tool-only warnings

| 工具警告 | 人工裁定 |
|---|---|
| Bib-Check 对六个 CVF/IEEE entries 建议 DOI | 合法但可选的 metadata enrichment；不是 identity error |
| Bib-Check 给 World Models 建议 Zenodo DOI | 存档 DOI；不应强制替换当前 arXiv version identity |
| Bib-Check 将 PlaNet 判为 2018 | 匹配到预印本年份；正式 ICML/PMLR 年份 2019 正确 |
| Bib-Check 给 Dreamer 匹配无关书籍 DOI/venue | false positive；ICLR 2020 OpenReview 记录已确认 |
| Bib-Check 对 LatentTSF/PSR/V-JEPA 低置信度 | recent/legacy/TMLR indexing；论文与官方记录已人工确认 |
| True Cite 的 author warnings | 姓名顺序、LaTeX 重音与显示名解析造成；作者逐项人工匹配 |
| True Cite 的 venue warnings | `CVPR`/完整 proceedings 名、NeurIPS/预印本索引等缩写差异 |
| True Cite 跳过五个 `@misc` | 四个正文已引用 `@misc` 已用 arXiv 人工确认；一个未使用 |

自动工具没有提供 citation-to-claim 支撑证明，所有实质性主张均另行阅读原文裁定。

## 11. 建议的最小修复清单

提交前建议只做以下两项文本级引用修复：

1. 在 Table 1 的 comparison sentence 或 caption 邻接加入
   `\cite{benson2024multimodal}`，明确公共行取自 GreenEarthNet 正式论文
   Table 2；不改任何数值。
2. 为 Introduction 的 “primary evidence ... pixel accuracy over a fixed forecast
   window” 加入已有 benchmark 引用并把适用范围限定在标准 EO
   benchmark/evaluation；不要改成“所有现有方法”或更强否定。

非强制的 bibliography hygiene：

- 可统一补全已确认的 DOI、旧 NeurIPS 页码和 PVT issue；
- 可保留或删除两个未使用 composition 条目；
- 不要接受 Bib-Check 的 Dreamer DOI，也不要把 PlaNet 改为 2018；
- 不要把 LatentTSF 改写成 preprint；
- 不需要加入 Published/Local、seed、single-run、`±`、SOTA 或严格排名说明。

## 12. 问题计数

| 等级 | 数量 | 内容 |
|---|---:|---|
| Critical | **0** | 无 |
| Major | **0** | 无 |
| Minor | **2** | Table 1 来源引用缺失；Introduction 跨文献概括引用邻接偏弱 |

未使用条目、工具-only warnings 和可选 metadata 补全不计入上述问题数。

## 13. 最终判定

**CITATION_BIB_FINAL_REVISE**

判定原因不是文献身份、公开数字或 citation-to-claim 内容错误，而是仍有两处可在一轮
内完成的引用归因问题。完成上述最小修复并重新运行 citation inventory 后，若
missing/duplicate 仍为零，即具备进入最终 citation freeze 的条件。

## 14. 只读声明

本轮没有修改 `paper/main.tex`、`paper/references.bib`、Table 1、任何正文、
Markdown 镜像、附录、Figure、实验、代码、模型或数据；没有执行 LaTeX 编译或
自动修复。唯一新建文件为本审计报告。

