# TerraState AAAI-27 修订后全文与格式回归审计

日期：2026-07-29 UTC  
最终判定：`READY_FOR_AAAI_TEXT_REVIEWER_AUDIT`

## 1. 严重度汇总

| 级别 | 数量 | 结论 |
|---|---:|---|
| Critical | 0 | 无阻断问题 |
| Major | 0 | 四路审计要求的 Major 均已关闭 |
| Minor | 0 | 无新增未解决项 |
| Informational | 2 类 | 14 个 underfull hbox、2 个 underfull vbox；目视无裁切或异常留白 |

既有 `DEFERRED_FIGURE_ISSUES_20260728.md` 中 Figure 1/2 的图内内容问题
仍按作者要求保持延期，不属于本轮文本审稿门禁，也未被修改。

## 2. 全文一致性

- Introduction 已限定为 standard EO forecasting benchmarks，并邻接
  EarthNet2021 与 GreenEarthNet 引用。
- Introduction 结果预告为 \(R^2=0.569\)、RMSE \(=0.151\)；Section 4
  与表格仍为 0.56935、0.15059。
- KD teacher 输入已最小补入 past weather，仍明确 no future EO。
- Table 2 已有显式自然正文引用。
- `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md`、`MANUSCRIPT_ZH_FULL.md` 已同步
  上述文字和本轮压缩后的 Table/Figure 3 caption 语义。
- 英文投稿正文、英文镜像与两份中文镜像均保持 Q3 为完整 20-step
  forecast window；没有 endpoint-only Q3。
- 投稿正文、英文镜像和中文精简镜像中的 `Q4` 均为 0。完整中文稿仅在
  文末“证据边界导航”中保留一条既有的“不主张 Q4”说明，不是正文主张，
  且不是本轮新增。

## 3. 引用与 BibTeX

- Introduction 与 Table 1 的 GreenEarthNet/EarthNet2021 引用邻接通过。
- `shinohara2025vitkoop`：两位作者与 DOI 均已修复，citation key 未变。
- `ha2018worldmodels`：保留可识别的 arXiv *World Models* 条目；这是明确
  的版本选择裁决，不是残留错误。
- BibTeX 完整运行；`main.blg` 报告 `warning$ -- 0`，即 BibTeX warning
  为 0。
- undefined citation/reference：0。

## 4. 正文复现信息

以下事实逐项存在且未改变：

- one final model for Q1--Q3；
- 40 epochs；
- 14,880 updates；
- global batch size 64；
- Q2/Q3 frozen-forward interventions、no retraining；
- Q2 state removal primary；
- \(T_\psi\!\rightarrow I\) supporting；
- Q3 complete 20-step forecast-window fidelity。

没有加入 seed、single-run、重复实验次数、硬件、checkpoint、cache、服务器
或代码公开承诺。

## 5. 数字回归

Figure 3 QA JSON 与冻结记录重新逐项核对：

| 条目 | 冻结值 | 结果 |
|---|---|---|
| Validation state removal | 0.01616252595360122, CI [0.006432408120151691, 0.02590229577842624], n=589 | PASS |
| Validation \(T\to I\) | 0.017417428921451206, CI [0.007824839508750908, 0.026960749441100905] | PASS |
| OOD-t state removal | 0.021997768589881533, CI [0.014219898623411737, 0.03017606928017251], n=1019 | PASS |
| OOD-t \(T\to I\) | 0.024015932710944276, CI [0.016086752271438905, 0.032169788967835664] | PASS |
| Q3 pair count | 84 | PASS |
| donor-minus-actual | 0.002565468112672014 | PASS |
| mean-minus-actual | 0.011261332329706334 | PASS |
| above diagonal | 56/84, 69/84 | PASS |
| missing/non-finite | 0 | PASS |

Table 1--3 的全部数字与列结构未改变。正文仍含精确 Q1
0.56935/0.15059，Introduction 只做显示精度舍入。

## 6. AAAI 格式与页数

| 门禁 | 结果 |
|---|---|
| PDF 页面 | 8 |
| 纸张 | 612 × 792 pt, US Letter |
| 双栏与官方 margins | 未改 |
| 主内容最后一页 | 第 7 页 |
| References-only 边界 | 第 8 页首个非空文本为 `References` |
| Figure 3 | 第 5 页、标准单栏 `figure[t]` |
| Table 1 | 第 7 页；Q1 首次讨论第 6 页 |
| Table 2 | 第 7 页；Q2 首次讨论第 6 页 |
| Table 3 | 第 7 页 |
| Limitations / Conclusion | 第 7 页完整结束 |
| 负 `vspace/vskip` | 0 |
| `[H]` | 0 |
| `resizebox/scalebox` | 0 |
| LaTeX `trim/clip/viewport` | 0 |
| LaTeX errors | 0 |
| undefined citations/references | 0 |
| overfull hbox/vbox | 0 / 0 |
| underfull hbox/vbox | 14 / 2，仅记录；目视无异常 |

Figure 3 在 0.80 栏宽时仍会把 Conclusion 推到第 8 页；0.79 是通过
references-only 门禁的最大已验证宽度。144 dpi 全页预览确认坐标、CI、图例、
散点、对角线计数、caption 和表格均可辨认，无裁切、重叠或列侵入。

## 7. PDF 字体与 Figure 3 技术回归

- `pdffonts paper/main.pdf`：
  - Identity-H：0；
  - Type 3：0；
  - non-embedded fonts：0；
  - 其余均为嵌入的 Type 1。
- Figure 3 投稿技术 PDF 为矢量轮廓，无字体资源；LaTeX 不执行禁用的
  `trim/clip`，白边已在外部文件中裁去。
- Figure 3 原脚本、原 SVG/PDF/PNG、QA JSON、data trace 和全部冻结数据
  SHA 未改变。
- Figure 1/2 正式文件 SHA 与修订前完全相同。

## 8. 禁止项扫描

投稿正文与英文/中文精简镜像中下列字符串均为 0：

- `Published/Local`
- `single-seed`
- `single-run`
- `±`
- `SOTA`
- `11,904`
- `boundary80`
- `Stage A`
- `Stage B`
- `B0`
- `B4`
- `Q4`

未新增 composition、因果、反事实、完整物理状态或严格排名主张。

## 9. 最终文件

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `699bea9183899a5ab976addc715db97ad1c5127ef840b157045c71fdd45b4195` |
| `paper/main.pdf` | `7b7f66ac075d8e6ec9c2c1f8116424fc8006dc5473e8b6ade327a06c3b4fec23` |
| `paper/references.bib` | `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3` |
| `MANUSCRIPT.md` | `1602fa96b899eb79d6b3e66402504fe86960c63a8760a2140d3ee4633dc8d81c` |
| `MANUSCRIPT_ZH.md` | `bf8581f3d8bb20f43a560a17451f731fcd4f56e1b2107c3c50a987f083f8987f` |
| `MANUSCRIPT_ZH_FULL.md` | `5949a6ea117057dcac70dd38e6995b4b98c14ed6b244fb8564043a59488ee976` |
| Figure 3 outlined/cropped PDF | `b9049a5a66990a7d026b2049aa4956c817ea3b6764ae5466d16d14197584d17e` |

## 10. 结论

四路审计要求的唯一最小修订已经完成。正文、引用、BibTeX、复现信息、
页面边界、Table 位置、Figure 3 字体技术门禁、数字与中英文镜像均通过本轮
回归。

`READY_FOR_AAAI_TEXT_REVIEWER_AUDIT`

