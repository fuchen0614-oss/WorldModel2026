# TerraState 写作工作区

AAAI-27 投稿的**全部写作过程材料**，以及我与 Codex 的对话原文。
与 `../submission/`（已提交的最终件）和 `../archive/`（精选归档）互补：
这里保留的是**过程**——手稿演化、逐节审计、图表打磨、引用核查、以及决策是怎么做出来的。

## 目录

| 路径 | 内容 |
|---|---|
| `codex_conversations/` | **我与 Codex 的对话原文**（未改写）。先读 `00_INDEX.md` |
| `MANUSCRIPT.md` / `MANUSCRIPT_ZH.md` / `MANUSCRIPT_ZH_FULL.md` | 手稿英文版与中文镜像 |
| `audits/` | 73 篇逐节审计与修订日志（Section 1–4、Method 3.2–3.4、Abstract、Related Work、Limitations、引用、格式、语言、全局一致性） |
| `paper/figures/` | 图的全部历史变体与可编辑源（pptx / svg / py） |
| `figure_workspace/` | 图 3 的最终导出与图源脚本 |
| `chinese_review/` | 中文完整审阅版（`main_zh.tex` / PDF） |
| `evidence_workspace/` | 证据台账 |
| `citation_audit/` | 引用与 bib 核查 |

## codex_conversations/ 是什么

我在定稿前后与 Codex 的多轮讨论，涉及：

- **期刊路线**：AAAI 若未中如何转投；TGRS / JSTARS / ISPRS JPRS / RSE / TIP 的适配度；已发表近邻分析
- **下游任务**：要不要加、加哪些（洪水检测、地表变化、城市扩张、时序预测）、领域先例怎么做的
- **AAAI 叙事**：主表不算惊艳时怎么立论、"尺子"是什么、摘要与标题打磨
- **双线规划**：TerraState 线与 Stage1–1.5 线是否合并

原文保留，因为里面的**推理过程和反对意见**比结论本身更有用。

⚠️ 这些是**探讨**，不是已完成的结果。最终冻结的口径以
`../思路整理进展/88_TerraState_full24唯一条件合同_...20260726.md` 与
`../../obsworld/思路整理进展/89_双线推进_...20260813.md` 为准。

## 不在这里的东西

以下被有意排除，不要以为丢了：

- LaTeX 工具链（`_audit/` 下的 TinyTeX、tectonic，652 MB）
- 第三方论文 PDF（`literature/`、`示例/`，约 280 MB，版权原因不入库）
- 重复的 `build_review_*` 编译副本
- `main.pdf` / `main.tex` / Reproducibility Checklist —— 在 `../submission/`
- LaTeX 编译副产物（`.aux` / `.log` / `.fls` / `.fdb_latexmk` / `.bbl`）
