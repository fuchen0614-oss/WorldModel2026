# TerraState AAAI-27 Writing Workspace

本目录是新建、独立的 AAAI-27 写作区。既有 `WorldModel2026` 与当前训练代码、配置、checkpoint、实验输出及历史 Markdown 均保持只读。

## 核心文件

- `paper/main.tex`：AAAI-27 匿名投稿权威稿；任何正文修改均以它为准。
- `MANUSCRIPT.md`：与 LaTeX 正文同步的英文 Markdown 阅读版，包含冻结的中英文摘要。
- `MANUSCRIPT_ZH.md`：与当前正文同步的中文阅读版。
- `AUTHOR_NOTES.md`：唯一 TerraState 的 claim–evidence–artifact 映射、证据门槛和风险说明。
- `RESULT_INGESTION_SCHEMA.md`：Q1–Q4 每个表格单元、发现句和 provenance 的结果接入口；不是新 benchmark。
- `paper/main.pdf`：当前可编译 PDF。
- `paper/figures/terrastate_overview.tex`：保留不动的 Figure 1 v1 TikZ 图源。
- `paper/figures/terrastate_overview_v2.tex/pdf/png`：保留的 Figure 1 v2 候选。
- `paper/figures/terrastate_overview_v3.tex/pdf/png`：保留的 Figure 1 v3 历史版本。
- `paper/figures/terrastate_method_overview.tex/pdf`：当前接入正文的 Figure 1（TerraState 方法闭环）。
- `paper/figures/terrastate_operational_verification.tex/pdf`：当前接入正文的 Figure 2（同一模型上的干预设计）。
- `paper/figures/terrastate_behavioral_evidence_column.tex/pdf/png`：当前接入正文的单栏 Figure 3（Q2/Q3 行为证据）；全宽备选及其数据位于同目录和 `paper/figures/data/`。
- `paper/references.bib`：正文参考文献库。
- `FIGURE1_AAAI_ANCHOR_AUDIT.md`：AAAI Figure 1 一手锚点、v2/v3 与 A/B/C 方案审计。
- `CITATION_AND_BIB_AUDIT.md`：逐条引用、元数据与 claim-to-source 审计。
- `PAPER_FIGURE_CITATION_LAYOUT_AUDIT.md`：本轮投稿成熟度、官方格式、逐页布局与严重度总报告。
- `paper/ReproducibilityChecklist.tex`：官方 checklist 原文件，尚未以虚构答案填充。
- `vendor/AuthorKit27/`：下载的 AAAI-27 官方 author kit。
- `literature/`：本轮核验的重点论文 PDF 与本地文本，仅作研究记录。

## 冻结边界

标题、TerraState 单模型定位、`q\rightarrow T\rightarrow O` 方法主线以及 Q1–Q3
证据结构保持冻结。英文摘要已按 2026-07-27 作者关于最终结果接入的明确指令更新，
中文摘要与之同步。正文只能接入冻结记录中已有的数值；没有真实数组的定性图不得进入
渲染稿。Q4/composition 仍是可选扩展，不作为核心已验证主张。

## 编译

在 `paper/` 目录执行：

```bash
PATH=/mnt/data/users/luzheng/workspace/iclr/czj/.tools/texlive-2026/bin/x86_64-linux:$PATH \
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

当前使用项目根目录下的本地 TeX Live 2026；为满足官方 `aaai2027.sty`，本地安装了 `newtx`、`fontaxes`、`psnfss`、`courier` 和 `placeins` 等依赖。官方 `.sty`/`.bst` 文件未改动。

## 写作工作流

1. 先在 `AUTHOR_NOTES.md` 核对唯一模型、选择记录和结果身份；
2. 按 `RESULT_INGESTION_SCHEMA.md` 在 `paper/main.tex` 中接入可追溯结果；
3. 同步更新 `MANUSCRIPT.md`；
4. 重编译并检查页数、匿名性、字体、引用与 overfull boxes；
5. 只有真实证据支持时，才把结果段从条件式改成事实式；
6. 提交前按官方要求填写 reproducibility checklist。

## 当前状态

- 官方 submission 样式；
- 匿名作者；
- 英文标题保持不变；中英文摘要已经按最终 Q1–Q3 证据同步；
- Q1–Q3 已从冻结结果记录接入正文；Q4 保持探索性、未进入核心结论；
- 英文 LaTeX、英文 Markdown 和中文 Markdown 的章节、数值与主张强度已同步；
- Figure 1 解释方法闭环，Figure 2 解释干预协议，Figure 3 展示 Q2/Q3 行为证据；
- 当前 PDF 共 9 页；全部非参考文献内容在第 7 页结束，参考文献从第 8 页开始，第 8–9 页仅含参考文献；
- 强制重编译无 LaTeX error、overfull box、未解析引用或交叉引用；
- 30 个引用键均可解析，缺失、重复与 unused 均为 0；
- PDF 为 US Letter、匿名，全部字体对象均嵌入为 Type 1；
- 三张表均使用官方允许的 9pt `\small`，未使用整体缩放；Figure 1 最小成品字号约 9.4pt、最细成品线宽约 0.55pt；
- 无 `TBD` 或方括号结果占位，未填入任何推测数字；
- 原始 checkpoint 与逐样本 Q1–Q3 导出包在当前可见工作区中不可用，因此本轮身份核对
  以冻结结果记录为依据；投稿归档前仍需对原始发布包重新计算哈希并逐项复核。

当前剩余工作包括：归档并复核原始 checkpoint、serialized config、validation-only
selection record、manifests 与 Q1–Q3 JSON/CSV；如要加入逐样本分布或定性地图，需由
实验侧提供冻结数组与样本选择记录；决定是否运行并在附录报告 Q4；提交前更新 2026
并行预印本文献元数据并填写官方 reproducibility checklist。
