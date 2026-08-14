# TerraState AAAI-27 投稿成熟度、Figure 1、引用与版面最终审计

审计日期：2026-07-27  
权威正文：`paper/main.tex`  
最终审计 PDF：`paper/main.pdf`  
PDF SHA-256：`c0642ea5270be4e75847916bd13d40d6a3b4ae7d19f7f98e694d90197797b61d`

## 1. 执行结论

TerraState 当前已经达到**结果接入前的 submit-ready 写作与格式状态**：

- 标题、冻结摘要、一个 TerraState、\(q\!\rightarrow z_t\!\rightarrow
  T\!\rightarrow z_{t+h}\!\rightarrow O\) 和 Q1/Q2/Q3 核心主线保持不动；
- Figure 1 已从“方法与验证平分视觉中心”的 v2，收敛为“方法闭环主导、
  验证证据降为次级条带”的 v3；
- Method、训练目标、三阶段 curriculum、同检查点干预、实验协议、三张结果表、
  三档结果句和双语阅读稿已经完整；
- AAAI-27 当前可机械检查的格式项全部通过；
- 没有填写任何本地 Q1–Q4 假数字，也没有把 cache sanity 或训练启动事实写成结果。

但它尚不能称为**科学结论层面的 submit-ready**。唯一最终 checkpoint、validation
选择记录、matched-backbone 公平性和 Q1–Q3 真实结果仍是投稿前硬阻塞项；Q4 是否保留
取决于真实证据。冻结摘要中与 Q2/Q3/Q4 绑定的能力形容词也只能由最终结果兑现。

## 2. 严重度审计

### CRITICAL：本轮发现并已修复

1. **第 8 页曾残留 Conclusion 正文。** AAAI-27 要求第 8–9 页 exclusively
   references；在提升表格字号后，Conclusion 最后一句一度溢到第 8 页。已通过删除
   重复性结论措辞收回第 7 页，没有使用负间距、缩小字体或改样式。最终第 8 页以
   `References` 开始，第 8–9 页只有参考文献。
2. **Table 1/3 曾低于官方 9pt 下限。** `\scriptsize` 和 `\footnotesize` 已全部
   改为 `\small`（9pt），只使用 Author Kit 明确允许的局部 `\tabcolsep` 调整；三表
   均未使用 `\resizebox`、`\scalebox` 或整体缩放。
3. **v3 原始小字号与细图标线在论文缩放后不足下限。** Figure 1 最小源字号已提升到
   19pt，按 `0.98\textwidth` 缩放后约 9.45pt；最细源线宽已提升到 1.1pt，成品约
   0.55pt。图中文字改用 Times-like 可嵌入矢量字体。

### MAJOR：本轮已修复

1. v2 的右侧验证区约占三分之一，容易让论文被误判为 diagnostic/benchmark paper；
   v3 改为方法主导结构并已接入正文。
2. v3 明确分开 \(q_\theta\) 与 \(P_\rho\)，并同时呈现 GT、KD、future-state 三项
   唯一训练监督和冻结 full-weather teacher。
3. teacher、observed future EO 和 target cache 均被隔离到 training-only 色带；
   没有任何训练支路连入实线推理路径。
4. Q4 在图、正文、表格和双语稿中均降级为 optional post-training extension；正文
   使用 AAAI-27 的正式名称 `Supplementary Document`，不再把它误写为不受页限的正文
   appendix。
5. 公开稿中的研发标签 “Matched B4” 已改为 `matched backbone`；内部 schema 仍保留
   B4 标识以维持 provenance。
6. BibTeX 元数据、arXiv 类型和作者式引用已完成一手来源核验与可确定修正。

### MAJOR：只能由最终实验解决

1. 冻结唯一 checkpoint、serialized config、SHA、validation-only 选择记录和
   one-shot OOD-t 锁。
2. Q1：同协议本地 matched backbone 与 TerraState 的真实指标、配对区间和
   win/tie/loss。
3. Q2：closure cut 主证据与 \(T\!\rightarrow I\) 辅证是否支持 load-bearing。
4. Q3：matched/normalized-mean/donor 是否同时产生预测、状态和输出层面的证据，并
   通过 context-prior invariant。
5. 可选 Q4：只有在 endpoint guard、broken-path 对照和 anti-collapse 同时成立时才能
   保留正面组合性表述；若弱或未运行，应把 Table 3/小节移入 Supplementary Document
   或删除对应主张。
6. 冻结摘要仍存在三项结果依赖风险：
   - `requiring this state to carry the forecast` 最多只能由 Q2 支持为“状态分支承载
     超出 prior 的可测预测增量”，不能偷换成“全部预测只经过状态”；
   - 摘要的 shuffled/zeroed-driver 措辞与正文正式
     matched/normalized-mean/donor 控制并非逐字一致；
   - `composition-consistent` 与 `non-degenerate` 依赖可选 Q4。若 Q4 不支持，作者
     必须在结果后决定是否解除摘要冻结。

### MINOR：保留并记录

1. Table 1–3 当前集中在第 7 页，视觉上仍像结果接入模板页。它们分别紧跟第 6 页的
   Q1、Q2/Q3、Q4 首次引用，浮动距离可以接受；真实结果、区间和发现句进入后再决定
   最终拆分，不提前做不可逆排版。
2. 第 9 页只有最后五条参考文献，页面偏稀。这是自然分页，不应通过压缩参考文献或
   牺牲可读性强行变成 8 页。
3. 最终 log 仅有 2 个 bibliography underfull hbox（Ha/Schmidhuber 与 ViT-Koop
   条目）和 1 个浮动页 underfull vbox；没有内容溢出或可见排版缺陷。
4. 2026 concurrent preprints 的 venue 状态须在上传前再查一次。

## 3. AAAI-27 官方格式审计

官方依据：

- [AAAI-27 Main Technical Track Call](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/)
- [AAAI-27 Submission Instructions](https://aaai.org/conference/aaai/aaai-27/submission-instructions/)
- [AAAI-27 Supplementary Material](https://aaai.org/conference/aaai/aaai-27/supplementary-material/)
- 本地官方模板：`vendor/AuthorKit27/AuthorKit27/AnonymousSubmission2027.tex`

| 项目 | 官方依据 | 当前事实 | 判定 |
|---|---|---|---|
| 模板入口 | Author Kit 177–196 | `letterpaper` + `\usepackage[submission]{aaai2027}` | PASS |
| 样式文件 | Author Kit 204–212 | 本地 `aaai2027.sty/.bst` 与 vendor SHA-256 完全相同 | PASS |
| 匿名性 | Author Kit 177–185；网站 155–157 | `Anonymous Submission`、空 affiliations、无 acknowledgments | PASS |
| PDF 元数据 | Author Kit 181 | title/author/subject/keywords 为空，无路径或身份泄漏 | PASS |
| 页数 | CFP 159–161；网站 155–157 | 9 页；非参考文献内容止于第 7 页；第 8–9 页仅 references | PASS |
| Checklist | 网站 187–192 | 不放入主 PDF；须在 OpenReview 指定字段单独上传 | PENDING USER UPLOAD |
| Supplement | 官网 145–157 | Q4 如外移，使用单独 Supplementary Document；主文保持自洽 | PASS |
| 纸张与 PDF | 网站 155；Author Kit 394–408 | 612×792 pt US Letter，PDF 1.7，无密码 | PASS |
| 字体 | Author Kit 220–243、417–426 | 27 个字体对象全部嵌入，Type 3 为 0 | PASS |
| 正文样式 | Author Kit 504–505 | 官方 10pt Times-like 双栏，无自定义行距 | PASS |
| Figure 字号/线宽 | Author Kit 581、605 | 最小约 9.45pt；最细约 0.55pt；Times-like call-outs | PASS |
| 灰度/色盲 | Author Kit 601–608 | 颜色外还有线型、边框与明度编码；灰度预览可辨 | PASS |
| Table 字号 | Author Kit 583–590 | 全部 9pt；caption 位于表下；无整体缩放 | PASS |
| 浮动体位置 | Author Kit 573 | Figure 1 第 2 页顶部；三表在首次引用后的下一页 | PASS |
| 禁止压缩 | Author Kit 43–78、387–414 | 无 geometry/balance/titlesec、负间距、页面断点或布局宏 | PASS |
| 引用与参考文献 | Author Kit 657–680 | natbib + 官方 bst；30/30 键可解析 | PASS |
| 链接/书签 | Author Kit 239 | PDF 内链接 0、注释 0；未加载 hyperref | PASS |

补充说明：

- 审稿阶段官网只要求主 PDF；v1/v2、审计截图和下载文献留在写作工作区不会进入该
  PDF。若录用后提交 source archive，必须只打包 `main.tex` 实际使用的图、
  `references.bib` 与官方 style/bst，不把旧图、审计图或 build 目录打包。
- 官方 checklist 必须单独填写和上传；当前 `ReproducibilityChecklist.tex` 没有用
  虚构答案填充，这是正确状态，但尚不是完成状态。

## 4. 最终 PDF 页面事实

| 页码 | 内容与布局判断 |
|---:|---|
| 1 | 冻结标题、匿名作者、冻结摘要、Introduction 主问题与方法差异；密度较高但属于正常 AAAI 首页面貌。 |
| 2 | Figure 1 顶部通栏；caption 后继续 Introduction/contributions 并进入 Related Work。方法在审稿人第一次需要结构图时出现。 |
| 3 | Related Work 收束，进入 Problem Definition、state inference 与 shared transition。 |
| 4 | Forecast closure、direct/composed query 与训练目标/curriculum。 |
| 5 | 训练细节、matched diagnostics 与 Experiments protocol 开始。 |
| 6 | 实验设置、Q1–Q4 evidence-ready scaffold、Limitations。 |
| 7 | Table 1、Table 2、optional Table 3 和完整 Conclusion；所有表均为 9pt。 |
| 8 | 从 `References` 开始，只有参考文献。 |
| 9 | 参考文献续页，只有参考文献。 |

浮动体判断：

- Figure 1 未远离首次方法介绍，也没有把 Method 切到难以理解的位置；
- Table 1 紧随 Q1、Table 2 紧随 Q2/Q3、Table 3 紧随 optional Q4 的下一页；
- 三表集中是当前 TBD scaffold 的可接受临时状态。真实置信区间可能改变列宽和分页，
  最终结果前不应把该布局当作冻结版；
- 目前不预留空白的真实定性图 float。正文和 schema 已保留定性证据入口；只有真实
  数组、validation-frozen 样本、统一色标和 provenance 全部存在后才允许加入。

## 5. Figure 1：AAAI 锚点

详细逐图记录与本地页截图见 `FIGURE1_AAAI_ANCHOR_AUDIT.md` 和
`literature/aaai_figure_anchors/`。本轮使用了六篇 AAAI 主会一手锚点：

1. **Drive-OccWorld**, AAAI 2025：
   [官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/33010)；
   Figure 1 / PDF 第 2 页，方法 Figure 2 / 第 3 页。
2. **GLAM: Global-Local Variation Awareness in Mamba-based World Model**,
   AAAI 2025：
   [官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/33880)；
   Figure 1 / 第 1 页，方法 Figure 2 / 第 3 页。
3. **SparseWorld**, AAAI 2026：
   [官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/37347)；
   Figure 1 / 第 1 页，方法 Figure 2 / 第 3 页。
4. **Object-Centric World Models for Causality-Aware Reinforcement Learning
   (STICA)**, AAAI 2026：
   [官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/39642)；
   Figure 1 / 第 2 页。
5. **Perceiving the Knowledge Boundary: Uncertainty-Guided Exploration and
   Imagination for World Models**, AAAI 2026：
   [官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/39576)；
   Figure 1 / 第 2 页，方法 Figure 2 / 第 4 页。
6. **WorldAgen: Unified State-Action Prediction with Test-Time World Model
   Training**, AAAI 2026：
   [官方页面](https://ojs.aaai.org/index.php/AAAI/article/view/38925)；
   Figure 1 / 第 2 页，Figure 2 / 第 4 页。

共同方法论而非具体构图：

- AAAI 没有统一的“流程图长相”；稳定原则是单一阅读方向、明显语义分区、方法主链
  最大、caption 可独立解释；
- world-model 方法图首先回答 input/state/dynamics/output，训练与验证处于第二层；
- 真实图像能增加任务直觉，但不能用未冻结样本或示意结果冒充真实预测；
- 颜色只作辅助，箭头样式、边框和空间层级必须在灰度中仍成立。

没有把这些锚点加入 TerraState 正文引用，也没有复刻其配色、图标或构图。

## 6. Figure 1 v2、方案 A/B/C 与 v3

### v2 的优点

- TikZ 矢量、通栏，已区分 inference/training/post-training；
- 基本画出状态推进、context prior、closure 与 Q2/Q3 干预；
- Q4 已有灰色降级，版面高度较低。

### v2 的主要问题

- verification 区与方法区等高且约占三分之一，第一眼像“新评测协议”；
- \(q_\theta\) 与 \(P_\rho\) 合并，context backbone 与 state projector 边界含糊；
- 只突出 future-state alignment，没有完整呈现
  \(\mathcal L_{\rm GT}+0.5\mathcal L_{\rm KD}
  +\lambda_s\mathcal L_{\rm future-state}\)；
- frozen KD teacher 缺失，future observation 支路仍有被误读为推理输入的风险；
- 没有把世界模型闭环置于绝对视觉中心。

### 三方案结论

完整评分见 Figure 审计文件：

- A（保留左右双区）33/40：改动小，但 benchmark 误判风险仍在；
- B（方法主导 + 验证条带）39/40：方法第一印象、主线、页面成本最平衡；
- C（方法 Figure 1 + 验证 Figure 2）36/40：结构最纯，但当前新增一张协议图不值得
  额外版面。

因此采用 **方案 B**。

### v3 验收

- v3 已接入 `main.tex`，v1/v2 源文件均保留；
- 第一层是
  history/context \(\rightarrow q_\theta\rightarrow P_\rho\rightarrow z_t
  \rightarrow T_\psi\rightarrow z_{t+h}\rightarrow O_\omega
  \rightarrow +b_h\rightarrow\widehat y\)；
- past meteorology/static \(g\) 进入 q；full24 future weather/static \(g\)/
  horizon \(h\) 进入 shared T；future weather 不进入 \(b_h\)；
- GT、冻结 full-weather KD teacher、\(h=20\) future-state anchor 在独立橙色
  training-only 区；
- Q1–Q3 只占底部同检查点条带，Q4 以灰色虚线标为 optional；
- 三阶段 curriculum 保留在正文，避免把优化工程流程挤入推理图；
- 矢量源、彩色/灰度预览、论文尺度预览和 v2/v3 对比均已生成；
- 图中 EO/forecast 小矩形是明确的矢量示意槽，不是实验图片或结果。

最终第一印象符合目标：审稿人先看到“一个天气驱动、预测状态进入预测闭环的
方法型世界模型”，再看到 Q1–Q4 是验证同一模型的证据链。

## 7. 引用与 BibTeX 审计

完整逐条表和依据链接见 `CITATION_AND_BIB_AUDIT.md`。

最终 inventory：

- citation commands：33；
- citation-key occurrences：49；
- unique citation keys：30；
- BibTeX entries：30；
- missing：0；
- duplicate：0；
- unused：0；
- undefined citation/reference：0。

已确定并修正：

1. Contextformer 标题改为官方 `Multi-modal Learning for Geospatial
   Vegetation Forecasting`。
2. UnCRtainTS 页码改为 2086–2096并补 DOI。
3. SSL4EO-S12 作者 `Nassim Ait Ali Braham` 修正并补 DOI。
4. EO-WM、VegSim、Observability Forecasting、LatentTSF、World Models as
   Group Actions、World Models、V-JEPA 等 arXiv-only 工作不再伪装成期刊条目。
5. Earthformer、MCVD、PLSM、SatMAE、CROMA 补入一手 proceedings DOI。
6. 首次方法位置已引用 PVT v2；作者作句法成分的两处改为 `\citet{}`，括号事实引用
   继续使用 `\cite{}`。
7. GreenEarthNet/Contextformer Table 2 的 published panel 已逐项核对；标准差只在
   原表提供处写入，并在 caption 标为 `where available`。Published 与 Local panel
   明确分隔，不作跨协议严格排名。

未发现需要立即改变 novelty 叙事的 claim-to-source mismatch，也没有为了引用数量或
Figure 视觉参考而机械加入不相关论文。

投稿前重新核验 venue 状态：

- EO-WM (`2606.27277`)；
- VegSim (`2606.21961`)；
- Observability Forecasting (`2607.13651`)；
- LatentTSF (`2602.00297`)；
- World Models as Group Actions (`2605.24578`)。

## 8. 疲惫但公平的 reviewer 视角

### 第一页

第一页能够在有限时间内给出任务、固定像素精度的缺口、TerraState 的闭环结构、
EO-WM/VegSim 的差异和 Q1–Q4 证据链。Introduction 的主要风险不再是“协议压过方法”，
而是最终 Q2/Q3 是否足以证明所选能力形容词。

### 方法创新的可见性

贡献 2 已表现为“用未来观测状态锚定 transitioned state”的方法洞见，而不是损失配方
堆砌。Figure 1、贡献列表、Problem Definition 和 Method 使用同一条
prior-plus-state-closure 叙事。

### benchmark 误判

Intro 与 Limitations 集中声明本文不是 benchmark；v3 将验证条带视觉降级，正文也把
Q1–Q3 写成 same-checkpoint evidence，而不是“提出一套新尺子”。误判风险从 v2 的
MAJOR 降为 MINOR。

### Results 诚实性

Results 仍是 evidence-ready scaffold：TBD、方括号字段、PASS/PARTIAL/FAIL 模板都留在
源文件，没有被写成已发生事实。Q4 没有被用于掩盖 Q2，也没有训练 composition
objective。

### 双语同步

`main.tex`、`MANUSCRIPT.md`、`MANUSCRIPT_ZH.md` 的章节顺序、公式、Figure/Table
编号、Q1–Q4 层级和主张强度一致。中文稿使用自然解释，但没有提前把 TBD 结论写成
“已证明”。

## 9. 修改文件

正文与控制文件：

- `paper/main.tex`
- `MANUSCRIPT.md`
- `MANUSCRIPT_ZH.md`
- `AUTHOR_NOTES.md`
- `README.md`
- `paper/references.bib`

Figure 1：

- `paper/figures/terrastate_overview_v3.tex`
- `paper/figures/terrastate_overview_v3.pdf`
- `paper/figures/terrastate_overview_v3.png`
- `paper/figures/terrastate_overview_v3_grayscale.png`
- `paper/figures/terrastate_overview_v3_paperscale.pdf/png`
- `paper/figures/terrastate_overview_v2_v3_paperscale_comparison.pdf/png`

审计与文献：

- `FIGURE1_AAAI_ANCHOR_AUDIT.md`
- `CITATION_AND_BIB_AUDIT.md`
- `PAPER_FIGURE_CITATION_LAYOUT_AUDIT.md`
- `literature/aaai_figure_anchors/`
- `citation_audit/`

编译与逐页复核：

- `paper/main.pdf`
- `build_review_20260727_final/page_01.png`–`page_09.png`
- `build_review_20260727_final/facts.json`
- `build_review_20260727_final/verification.json`

`RESULT_INGESTION_SCHEMA.md` 已复核并继续作为结果接入口；本轮没有为了迁就排版或
论文叙事修改实验 schema。

## 10. 最终实验端 handoff

结果端仍需按 `RESULT_INGESTION_SCHEMA.md` 提供：

```text
final_result_package/
├── manifest.json
├── artifact_registry.json
├── validation_selection.json
├── q1_forecast.csv
├── q1_paired.csv
├── q2_load_bearing.csv
├── q3_driver.csv
├── q4_composition.csv                 # optional
├── q4_state_summary.csv               # optional
├── matched_b4_fairness.json
├── q2_q3_thresholds.json
├── q4_guard_and_retention.json        # optional
├── q4_broken_path_manifest.json       # optional
├── qualitative_manifest.json          # only if a real panel is used
└── raw/
    ├── state_contract_exclusive.json
    ├── commands.txt
    └── environment.txt
```

硬性身份字段包括：

- final checkpoint、serialized config、checkpoint/config SHA；
- validation-only selection criterion 与选择记录；
- train/validation/OOD-t manifest、mask、aggregation、scorer/evaluator SHA；
- matched-backbone 公平性与 confound；
- Q3 donor/normalizer/threshold manifests 和 prior-invariance；
- 同一 checkpoint 被 Q1–Q3/optional Q4 使用；
- OOD-t 不参与 checkpoint、阈值、donor rule 或措辞选择。

结果接入后才执行：

1. fail-closed schema/identity 检查；
2. 填 Table 1–3 的真实槽；
3. 每项只保留 PASS/PARTIAL/FAIL 中证据支持的一档；
4. 校准 Results、Limitations、Conclusion 和冻结摘要风险；
5. 根据 Q4 强度决定 Table 3 正文或 Supplementary Document；
6. 再做一次真实数字条件下的列宽、浮动体、页数、引用和 PDF 终检；
7. 完成并单独上传 AAAI reproducibility checklist。

## 11. 边界确认

- 冻结英文标题：未改；
- 冻结英文摘要及对应中文摘要：未改；
- TerraState 名称、单模型定位、\(q\!\rightarrow T\!\rightarrow O\) 主线：未改；
- Q1/Q2/Q3 核心、Q4 optional、validation-only selection、非 benchmark 定位：未改；
- 训练代码、评测代码、配置、checkpoint、实验输出：均未修改；
- 没有 commit、push、更新 Codex/Claude 配置或触碰写作区以外文件。
## 2026-07-27 Phase 2 双图正式接入补充审计

作者已批准 Figure 1/2 的双层信息职责。本轮只更新图稿、caption、镜像稿与
排版；标题、冻结摘要、方法合同、Q1–Q4 主张强度、实验代码和结果均未改动。

- Figure 1 已切换为纯方法闭环
  `paper/figures/terrastate_method_overview.pdf`，位于正式 PDF 第 2 页；
- Figure 2 已接入
  `paper/figures/terrastate_operational_verification.pdf`，位于第 6 页；
- Figure 1 的未来 EO、冻结 teacher 与目标状态只存在于橙色虚线
  training-only 区域，未进入实线推理链；
- Figure 2 从一个冻结 TerraState checkpoint 发出 Q1–Q4 查询，但匹配骨干
  明确画为独立训练并冻结的 Q1 参考；Q2 突出 closure cut，Q3 只替换进入
  \(T_\psi\) 的未来天气，Q4 使用灰色虚线降级；
- hot-dry 仅作为预注册评测分层，不是模型输入、训练目标或第四种天气臂；
- Figure 3 只在真实 Q2/Q3 数组、置信区间或冻结定性样本到位后生成，当前
  正式 PDF 没有可见的 TBD 图框。

正式 `paper/main.pdf` 为 9 页 US Letter：Conclusion 在第 7 页结束，第
8–9 页仅参考文献。为避免第 7 页继续堆放三张空结果表，可选 Q4 Table 3
已可逆地移至 `paper/supplementary_q4_table.tex`；若最终 Q4 证据足够强才
恢复正文，否则进入 Supplementary Document。Table 1–2 仍在第 7 页。

最终日志无 LaTeX error、BibTeX warning、undefined citation/reference 或
overfull box；仅有 1 处页面 underfull vbox 和 2 处参考文献断行 underfull
hbox。全部 32 个 PDF 字体对象已嵌入。最新逐页渲染位于
`build_review_20260727_phase2_final/`。
