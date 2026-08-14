# TerraState AAAI-27 四路审计合并最小修订日志

日期：2026-07-29 UTC  
范围：正文最小引用修复、ViT-Koop BibTeX 修复、Table 1/2 与 Figure 3
合法排版、Figure 3 字体技术导出、中英文镜像同步。  
最终状态：`READY_FOR_AAAI_TEXT_REVIEWER_AUDIT`

## 1. 权威与冻结边界

本轮完整核对了用户指定的正文、三份文本镜像、四份既有审计、Figure 3
trace，以及本地保存的 AAAI-27 Author Kit。Author Kit 权威副本为
`vendor/AuthorKit27/AuthorKit27/AnonymousSubmission2027.tex`，SHA-256 为
`035ebdb17e57885a1fd43a188fd17777bdbf90f1fda1a1e000c49c7f52ce1f9d`。
Main Technical Track 页数规则以
<https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/> 为准。

以下科学事实保持冻结：同一完整训练模型用于 Q1--Q3；40 epochs、14,880
updates、global batch size 64；Q2 state removal 为主要干预，
\(T_\psi\!\rightarrow I\) 为支持性诊断；Q3 为完整 20-step forecast
window；Q2/Q3 不重训练；未加入 Q4、因果、反事实、完整物理状态、SOTA
或严格排名主张。

## 2. 修改前后 SHA-256

| 文件 | 修改前 | 修改后 |
|---|---|---|
| `paper/main.tex` | `1fe12204bad54b2b18a8debd5792cab9dff85a1e342cc35ca8df0e9a2d6eaab9` | `699bea9183899a5ab976addc715db97ad1c5127ef840b157045c71fdd45b4195` |
| `paper/main.pdf` | `5f3931e373643d7aa3674fa3517e2e4f1e58f1632bd279b513d11f28bc021691` | `7b7f66ac075d8e6ec9c2c1f8116424fc8006dc5473e8b6ade327a06c3b4fec23` |
| `paper/references.bib` | `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659` | `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3` |
| `MANUSCRIPT.md` | `82b7b2059f639a3cb257190ac6e0efb2462c54558be6e328f2741e78664b7229` | `1602fa96b899eb79d6b3e66402504fe86960c63a8760a2140d3ee4633dc8d81c` |
| `MANUSCRIPT_ZH.md` | `f4c3f7c1ce449816d48639deedd4382bf936581ce422e26772ccd9292433ef96` | `bf8581f3d8bb20f43a560a17451f731fcd4f56e1b2107c3c50a987f083f8987f` |
| `MANUSCRIPT_ZH_FULL.md` | `0577238cd6d9561fb9ca7ea9fa4d8275da74a5b5f447e1d0407c4390d66099c6` | `5949a6ea117057dcac70dd38e6995b4b98c14ed6b244fb8564043a59488ee976` |

编译同时正常更新了 `paper/main.aux`、`main.bbl`、`main.blg` 和 `main.log`。

## 3. 正文与引用修复

1. Introduction 将泛化表述限定为 standard EO forecasting benchmarks，并
   与 EarthNet2021、GreenEarthNet 引用相邻；没有把该判断扩大到全部 EO
   世界模型工作。
2. Introduction 的结果预告改为三位小数 \(R^2=0.569\)、
   \(\mathrm{RMSE}=0.151\)；Section 4 和表格仍保留 0.56935、0.15059。
3. Experimental Setup 的 Table 1 比较设置邻接加入
   `\cite{benson2024multimodal}`。
4. §4.3 首段加入 `Table~\ref{tab:q2}`，并保持 state removal
   primary、\(T_\psi\!\rightarrow I\) supporting 的层级。
5. §3.3 KD teacher 输入补入最小短语 `past weather`；其输入现在明确为
   EO observation history、past weather、static geography、完整未来天气，
   且不含 future EO。

## 4. BibTeX 裁决

- `shinohara2025vitkoop` 保持 citation key 不变，作者改为
  Takayuki Shinohara and Hidetaka Saomoto，并加入 DOI
  `10.1109/ICCVW69036.2025.00296`。
- `ha2018worldmodels` 继续引用题名为 *World Models* 的
  `arXiv:1803.10122`。此前“必须切换正式版本”的意见被裁决为版本选择，
  不是已确认的元数据错误，因此没有把它替换为题名不同的论文。
- 未扩大到 DOI 批量补全、PVT v2 issue、VegeDiff article number 或未使用
  条目清理。

## 5. 排版试验与最终选择

所有试验均使用标准浮动体；未使用负 `vspace/vskip`、`[H]`、
`resizebox/scalebox`、margin/column-gap/line-spacing 修改或正文删减。

1. 原位置：9 页；Figure 3 在第 8 页，与 References 同页，失败。
2. Figure 2 提前、Figure 3 留在 Q3 后：Figure 3 仍在第 8 页，失败。
3. Figure 3 移到 Method 末端：总页数降至 8，但 Conclusion 仍延伸到
   第 8 页，失败。
4. Figure 2 后立即声明 Figure 3：Figure 2 第 4 页、Figure 3 第 5 页，
   但全栏宽时 Conclusion 仍有一段落入第 8 页。
5. 尝试 `[b]`：Figure 3 被延迟到第 8 页，失败。
6. 交换 Figure 2/3 声明顺序：图移到第 3/4 页，但没有解决第 8 页正文，
   且离 Results 更远，拒绝。
7. 提前 Table 1 声明：Table 1 提前到首次讨论之前，Table 2 反而延迟到
   第 8 页，拒绝。
8. 单独缩小 Figure 3：约 0.65 栏宽才满足边界，但纸面预览明显损害
   可读性，拒绝。
9. 最终采用组合方案：Figure 3 使用通过边界门禁的最大试验宽度
   `0.79\columnwidth`；Table 1/2 保持 9 pt `\small`，仅将局部
   `\arraystretch` 设为 0.70 并压缩自包含 caption；Table 3 与 Figure 3
   caption 同样做语义等价压缩。所有表格数值、列和统计定义不变。

最终页面为：

- Figure 1：第 2 页；
- Figure 2：第 4 页；
- Figure 3：第 5 页；
- Q1、Q2、Q3 首次结果讨论：第 6 页；
- Table 1、2、3：第 7 页；
- Limitations 与 Conclusion：第 7 页完整结束；
- References：第 8 页，且第 8 页首个非空文本即 `References`。

Table 1/2 因此位于首次讨论的随后一页，符合当前页或随后一页的要求。

## 6. Figure 3 技术导出

原始可编辑源、正式 single-column SVG/PDF/PNG、QA JSON、冻结 JSON 和
data trace 均未改。为消除 Identity-H：

1. 用 Ghostscript 10.07.1 的 `pdfwrite` 与 `-dNoOutputFonts` 将文字转为
   矢量轮廓，生成
   `figure_workspace/export/fig3_behavior_singlecol_aaai.pdf`；
2. 按 Author Kit 要求在图文件外部裁去原 PDF 的 5 pt 顶部和 7.5 pt
   底部空白，生成
   `figure_workspace/export/fig3_behavior_singlecol_aaai_cropped.pdf`；
3. `main.tex` 直接包含外部已裁剪 PDF，不使用 LaTeX `trim/clip`。

| 技术文件 | SHA-256 |
|---|---|
| `fig3_behavior_singlecol_aaai.pdf` | `c78c27bb82c0bce5b6809446b3d51a53eb22a2700198a97db3bc34dc492dc03e` |
| `fig3_behavior_singlecol_aaai_cropped.pdf` | `b9049a5a66990a7d026b2049aa4956c817ea3b6764ae5466d16d14197584d17e` |

裁剪后 media box 为 237.6 × 239.5 pt；文件无 font resource、无
Identity-H、无 Type 3，且保持矢量。相同有效画面 4× 栅格核对得到
MAE 1.651/255、PSNR 27.33 dB；差异来自轮廓化后的抗锯齿，数据点、CI、
文字、线型、配色和布局均未改变。

## 7. 冻结文件回归

| 冻结对象 | 修改前后 SHA-256 |
|---|---|
| Figure 1 正式 PNG | `cad4c85d4787babb3eee6f10fb12e86537da2c71ab6534656fd144f1ea587fd0` |
| Figure 2 正式 PNG | `9192e1d0f66253bad3391ac7208a5de91e663586157776fa8c8d30a46aa714f5` |
| Figure 3 single-column 脚本 | `4bbe7d71613c5358352688dac93dc417598d42728074af86890dd955d5ad31d0` |
| Figure 3 原 SVG | `399ebcd4335aabc4ea0dcbd46a279a6789b5af14a5ea237ebe9bd3ea88cca503` |
| Figure 3 原 PDF | `3b9c764152a867b2d1aef1b82b5661eb18bbd613236cb37dc45d58dfac7f0a53` |
| Figure 3 原 PNG | `9299c97fe61bf123dcdfa761e92cf056c4dbfaebefe5bcc662975049840919ed` |
| Figure 3 QA JSON | `e5405316086836c0d6583b2abde0fcfe1dc8b3e76caa9165e041bd9e97ea43cf` |
| Figure 3 data trace | `dcbaead6ac9fc7165ea9813006c186d6dc00188e3837887afe71100252c512c0` |
| Validation Q2 JSON | `33b40d3e6bf6e0190c9415a9e0421e9809063356dcba2350890defeeed35f2d9` |
| OOD-t Q2 JSON | `7ebc0569d705a9991ac8b8d17c42113c9da052b2bec73f7c28d021e28a65a051` |
| Q3 JSON | `9dae43b9a8a4fcdf0a73ef91daa58c189a88e769541ce295046cd0e938497041` |
| Results ledger | `d1f8ec7d7a51fae87afc8ba9dbc27905c6816434dc5554980d2e7c2eb472c4b2` |

## 8. 最终 QA 预览

- 第 5 页（Figure 3）：
  `figure_workspace/qa/consolidated_revision_final_page5.png`
- 第 7 页（Tables、Limitations、Conclusion）：
  `figure_workspace/qa/consolidated_revision_final_page7.png`
- 第 8 页（References only）：
  `figure_workspace/qa/consolidated_revision_final_page8.png`

最终编译使用 `pdflatex → bibtex → pdflatex → pdflatex`。详细门禁结果见
`POST_REVISION_TEXT_FORMAT_REGRESSION_AUDIT_20260729.md`。

