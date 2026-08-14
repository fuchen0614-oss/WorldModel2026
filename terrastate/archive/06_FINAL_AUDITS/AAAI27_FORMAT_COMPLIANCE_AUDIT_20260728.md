# TerraState AAAI-27 官方格式合规只读审计

**审计日期：** 2026-07-28（UTC）  
**审计性质：** 只读；未重新编译、未修改正文、表格、图片、参考文献或 PDF。  
**审计对象：** `paper/aaai2027.sty`、`paper/aaai2027.bst`、`paper/main.tex`、`paper/main.pdf`、`paper/main.log`、`paper/main.bbl`、`paper/references.bib`。  
**明确排除：** Figure 1–3 的视觉质量、内容、设计、图内字号、线条、颜色和清晰度；supplementary、appendix、Reproducibility Checklist 内容；科学主张与实验数值。

> 范围说明：Figure 3 的视觉设计未被审计。但是，非参考文献内容占用第 8 页，以及导入对象带来的 PDF 字体编码，分别属于全局页数边界和 PDF 技术合规问题，因此按官方硬规则记录。

## 1. 官方资料、版本与完整性

### 1.1 官方来源

- AAAI-27 官方会议页：<https://aaai.org/conference/aaai/aaai-27/>
- AAAI-27 Main Technical Track CFP：<https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/>
- 官方 Author Kit 入口：<https://aaai.org/authorkit27/>
- 官方 Author Kit 直接下载：<https://aaai.org/wp-content/uploads/2026/05/AuthorKit27.zip>
- 查阅及下载时间：**2026-07-28 23:46:35 UTC**
- HTTP `Last-Modified`：**Thu, 28 May 2026 15:54:36 GMT**
- HTTP `ETag`：`"6a18653c-53daef"`
- ZIP 大小：5,495,535 bytes
- ZIP SHA-256：`e28c6ac9bc6eb3b4e2d849547d2cefb5162610ee39d0a12e0dc62d1126b44a7d`

### 1.2 Author Kit 文件版本与 SHA

| 官方文件 | 版本/日期 | SHA-256 |
|---|---|---|
| `AnonymousSubmission2027.tex` | `TemplateVersion (2027.1)`；ZIP 时间 2026-05-28 13:04:28 | `035ebdb17e57885a1fd43a188fd17777bdbf90f1fda1a1e000c49c7f52ce1f9d` |
| `aaai2027.sty` | 内部声明 `2027/05/04 AAAI 2027 Submission format`；ZIP 时间 2026-05-18 16:21:04 | `391bce82815bf698b8e382dd3ae7e30c75d7ab46df140cb295b1266016bc8623` |
| `aaai2027.bst` | ZIP 时间 2026-05-04 16:09:48 | `5db7765ba99de5c1e4686f9b3940a0add9c5e702f2164514462bec130ccb6e3c` |

本地 `vendor/AuthorKit27/AuthorKit27/` 中的上述三份文件与当前官方下载内容逐字节一致。`paper/aaai2027.sty` 和 `paper/aaai2027.bst` 也分别与官方文件逐字节一致。因此：

- 本地 style 未被修改：**PASS**
- 本地 bibliography style 未被修改：**PASS**
- 模板版本：**AAAI-27 / TemplateVersion 2027.1**

### 1.3 当前论文文件指纹

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `1fe12204bad54b2b18a8debd5792cab9dff85a1e342cc35ca8df0e9a2d6eaab9` |
| `paper/main.pdf` | `5f3931e373643d7aa3674fa3517e2e4f1e58f1632bd279b513d11f28bc021691` |
| `paper/main.log` | `630577816ffd7a011c262173dfe0bd339d1753761350de5d17d1e36ac63b4af7` |
| `paper/main.bbl` | `05da278681f579ed69384fe5e84c299bde3075defd5b9a811255e4c93e64128f` |
| `paper/references.bib` | `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659` |

## 2. 执行摘要与最终判定

当前稿件正确使用未修改的 AAAI-27 submission style，页面尺寸、双栏几何、正文主字体、表格字号与 caption 位置、匿名作者信息、PDF metadata、引用样式、字体嵌入、Type 3 字体、链接、越界和 LaTeX 错误等多数项目均通过。

当前存在三个影响正式合规的核心问题：

1. **Critical：第 8 页并非仅含参考文献。** Figure 3 及其 caption 位于第 8 页上方，References 从同页中部开始。Main Track 明确规定最多 7 页正文、总长最多 9 页，且第 7 页之后必须专用于参考文献。
2. **Major：PDF 含两个 Identity-H 字体资源。** 两个资源均已嵌入且不是 Type 3，但官方 Author Kit 明确要求移除或转轮廓处理 CID/Identity-H 字体。它们位于第 8 页导入对象中；这是 PDF 技术检查，不是 Figure 视觉质量判断。
3. **Major：Table 1 和 Table 2 与首次讨论位置相隔超过官方建议范围。** 两表均排到第 7 页，而相应讨论已在第 5 页出现；Table 2 还没有正文中的显式 `Table~\ref{tab:q2}` 引用。

因此最终判定为：

## `AAAI27_FORMAT_COMPLIANCE_REVISE`

## 3. 模板、页面与全局结构

### 3.1 模板和预置

`paper/main.tex` 使用：

```tex
\documentclass[letterpaper]{article}
\usepackage[submission]{aaai2027}
```

`url`、`graphicx`、`natbib`、`caption` 和 `\frenchspacing` 的加载方式与 Author Kit 一致；`booktabs`、`amsmath`、`amssymb` 未改变模板几何或正文样式。`\setcounter{secnumdepth}{1}` 属于官方明确允许的节编号设置。

源码未发现：

- `geometry`、`hyperref`、`titlesec`、`setspace`、`float`、`stfloats` 等禁用包；
- 负 `\vspace`/`\vskip`；
- `\resizebox`/`\scalebox`；
- `\tiny`；
- `\addtolength`；
- 自定义正文行距、页边距、栏距或 section spacing；
- `\clearpage`、`\newpage`、`\pagebreak` 等强制压排命令。

结论：**PASS**。

### 3.2 页面尺寸、双栏和边距

PDF 共 9 页，所有页面均为：

- MediaBox：612 × 792 pt；
- CropBox：612 × 792 pt；
- 对应 US Letter 8.5 × 11 inch；
- 旋转角度 0；
- 页面尺寸完全一致。

本地 style 定义：

- `\textwidth = 7.0in`
- `\textheight = 9.0in`
- `\columnsep = 0.375in`

PDF 文本边界实测为横向约 54–558 pt，与左右各 0.75 inch 的官方几何一致。逐页对象边界检查未发现超出 MediaBox/CropBox 的对象。正文保持双栏，未发现正文或公式侵入页边距或栏间距。

结论：**PASS**。

### 3.3 页数与 references 边界

- 总页数：9，满足 Main Track 的“最大总长度 9 页”。
- Conclusion 位于第 7 页。
- `main.aux` 明确记录 `fig:behavior` 在第 8 页。
- PDF 中 Figure 3 及其 caption 占第 8 页约 y=56–393 pt。
- References 标题从第 8 页约 y=414 pt 开始，并延续到第 9 页。

Main Track CFP 明确规定：“Submissions are limited to 7 pages of main content, with a maximum total length of 9 pages. Any pages beyond page 7 are reserved exclusively for references.”

因此，虽然总页数为 9，**第 8 页混有非参考文献内容，仍构成硬性不合规**。

结论：**FAIL / Critical**。

## 4. 匿名与投稿信息

### 4.1 PDF 和正文匿名性

- 使用 `[submission]` 模式；
- 源码作者为 `Anonymous Submission`；
- `\affiliations{}` 为空；
- PDF 显示 `Anonymous submission`；
- 无单位、邮箱、致谢、个人主页或代码主页；
- 无作者身份式自引措辞，如 “our previous work”；
- PDF 正文未检出用户名、工作区绝对路径、邮箱、GitHub URL 或主页；
- 文件名 `main.pdf`/`main.tex` 不暴露身份。

结论：**PASS**。

### 4.2 PDF metadata

PDF metadata：

- Title：空；
- Author：空；
- Subject：空；
- Keywords：空；
- Creator：`TeX`；
- Producer：`pdfTeX-1.40.29`；
- 无 XMP metadata；
- 无嵌入文件。

未发现作者身份泄露。创建时间存在，但不包含个人信息。

结论：**PASS**。

### 4.3 构建日志路径

`paper/main.log` 包含 TeX 字体解析时写入的绝对工作区路径，其中出现 `/mnt/data/users/luzheng/...`。该路径**没有进入 PDF**，也不在 `main.tex`/`main.bbl`/`references.bib` 中。

风险仅在于误将 `main.log` 或其他构建日志打入匿名投稿材料。官方源文件要求并不需要该日志来复现编译。

结论：**Minor packaging/anonymity risk**。最小处理是在投稿压缩包中排除 `.log`、`.fls`、历史 `compile_*.log` 等非必需构建记录。

## 5. 正文排版元素

### 5.1 Title 与 Abstract

- 标题使用 AAAI style 生成，无自定义字号或间距；
- 标题符合 Title Case；
- Abstract 使用模板环境；
- 标题、匿名作者行和 Abstract 均未出现越界或自定义格式。

结论：**PASS**。

### 5.2 Section、Subsection、段落与列表

- section/subsection 标题由官方 style 控制；
- `secnumdepth=1` 为官方允许值；
- 无自定义 `\section`、`\subsection` 或 caption spacing；
- 正文主字号实测约 9.963 pt，使用 Times-like `TeXGyreTermesX`；
- Abstract 和表体等允许的小字号区域实测约 8.966 pt；
- 列表使用标准 `itemize`/`enumerate`；
- 无脚注；脚注格式不适用；
- 无 theorem/definition 环境；该项不适用。

结论：**PASS**。

### 5.3 公式

- 公式编号连续为 (1)–(8)；
- 相关 `\label`、`\ref` 和 `\eqref` 均已解析；
- 未发现公式越栏、侵入 gutter 或页边距；
- `main.log` 无 overfull box；
- 数学字体为嵌入的 Computer Modern/AMS 数学字体；正文文本仍为官方 Times-like 字体。

结论：**PASS**。

## 6. Table 1–3 格式检查

### 6.1 格式合规

| 检查项 | Table 1 | Table 2 | Table 3 |
|---|---|---|---|
| Caption 位于 tabular 下方 | PASS | PASS | PASS |
| `label` 紧跟 caption | PASS | PASS | PASS |
| Caption 实测约 9.963 pt Roman | PASS | PASS | PASS |
| 表体实测约 8.966 pt（约 9 pt） | PASS | PASS | PASS |
| 无 `resizebox`/`scalebox` | PASS | PASS | PASS |
| 无竖线 | PASS | PASS | PASS |
| `booktabs` 风格 | PASS | PASS | PASS |
| 无表格 overfull | PASS | PASS | PASS |
| 宽表使用 `table*` | PASS | PASS | 不适用；单栏可容纳 |
| 表号顺序 | PASS | PASS | PASS |

表格科学内容和数值未作审计或修改。

### 6.2 浮动位置与正文引用

- Table 1 首次正文讨论/引用位于第 5 页，实际位于第 7 页；
- Table 2 所属 Q2 讨论位于第 5 页，实际位于第 7 页；
- Table 2 源码中只有 `\label{tab:q2}`，正文没有显式 `Table~\ref{tab:q2}`；
- Table 3 在第 6 页被引用，实际位于第 7 页，符合“当前页或随后一页”的位置关系；
- PDF 中三张表仍按 Table 1 → Table 2 → Table 3 的顺序出现。

Author Kit 要求 figures/tables 出现在首次讨论的当前页或随后一页，不应集中到更后的页面。Table 1/2 当前延迟两页，且 Table 2 缺少正文显式引用。

结论：**FAIL / Major**。

最小修复是仅通过合规浮动顺序或源码位置，使 Table 1/2 靠近首次讨论，并为 Table 2 增加一次正常正文引用；不得使用负间距、缩放或缩小字号。

## 7. References 与 citation style

### 7.1 Bibliography style

- `paper/aaai2027.bst` 与当前官方文件 SHA 完全一致；
- `main.blg` 明确记录 `The style file: aaai2027.bst`；
- `main.tex` 使用 `\bibliography{references}`，未重复写 `\bibliographystyle`，符合 style 自动设置方式；
- References 位于源码末尾，之后只有 `\end{document}`；
- 参考文献 PDF 字号约 9.963 pt，未低于官方允许的 9 pt；
- PDF 采用 AAAI author-year 引用形式；
- DOI/URL 字段未形成嵌入超链接；
- 特殊字符和长条目未造成 overfull。

结论：**PASS**。

### 7.2 引用完整性

通过 citation inventory 只读检查：

- citation command：20；
- 引用键出现次数：28；
- 唯一被引键：22；
- BibTeX 条目：24；
- 缺失键：0；
- 重复键：0；
- 未识别引用命令：0；
- 未解析 `input`：0；
- 未使用条目：2（`chen2023deeposg`、`wang2026groupactions`）。

未使用条目不会进入 `main.bbl` 或 PDF，不构成当前格式失败；可在最终源文件清理时删除，但属于 Optional。

## 8. PDF 技术检查

### 8.1 字体

- 检出的字体资源均可从 PDF 提取出实际字体程序：**全部嵌入**；
- Type 3 字体：**0**；
- 正文主字体：`TeXGyreTermesX`，符合 Times-like 要求；
- 数学字体：嵌入的 Type 1 Computer Modern/AMS 字体；
- 第 8 页另有两个嵌入的 Type 0 字体：
  - `EEAXJL+DejaVuSans-Bold`，编码 `Identity-H`；
  - `FVKZVP+DejaVuSans`，编码 `Identity-H`。

Author Kit 明确要求需要 CID/Identity-H 支持的字体转换为轮廓或从文档移除，即使字体来自导入图形。当前两个字体虽已嵌入且不是 Type 3，仍不符合该独立规则。

结论：

- 所有字体嵌入：**PASS**
- 无 Type 3：**PASS**
- 无 CID/Identity-H：**FAIL / Major**

### 8.2 PDF 结构与可解析性

- PDF 版本：1.7，满足 ≥1.5；
- 未加密、无需密码；
- 文本复制权限开启；
- 可正常解析全部 9 页；
- 可提取文本约 37,926 字符；
- 页面尺寸统一；
- 无书签；
- 无嵌入链接；
- 无页面 annotation；
- 无嵌入附件；
- 无对象越出页面边界；
- 无自定义页码、页眉或身份性页脚；首页匿名投稿提示由官方 submission style 自动生成。

结论：**PASS**。

### 8.3 LaTeX 日志

`paper/main.log`：

- LaTeX error：0；
- undefined citation：0；
- undefined reference：0；
- multiply-defined label：0；
- overfull hbox：0；
- overfull vbox：0；
- package/LaTeX/pdfTeX warning：0；
- underfull hbox：14；
- underfull vbox：1；
- 输出：9 pages，10,384,099 bytes。

Underfull 未造成越界、裁切或不可读对象，官方硬规则针对的是 overflow/overfull；因此记录为 Optional，不构成失败。

### 8.4 PDF 文件大小

当前 PDF 为 10,384,099 bytes（约 9.90 MiB）。Main Track 官方页面在所查规则中明确了页数，但未给出可据此判定当前 PDF 的独立上传大小上限；Author Kit 的 10 MB 条款明确针对最终 LaTeX source archive，而本轮未提供实际投稿压缩包。

结论：**UNKNOWN / 不凭经验判定**。

## 9. 官方规则逐条映射

| 官方规则 | 官方出处 | 当前实现 | PASS/FAIL/UNKNOWN | 严重度 | 最小修复 |
|---|---|---|---|---|---|
| 使用 AAAI-27 style | Author Kit, Formatting Requirements | `\usepackage[submission]{aaai2027}` | PASS | — | 无 |
| style 不得修改 | Author Kit, Formatting Requirements | 本地与官方 SHA 完全相同 | PASS | — | 无 |
| 使用 `aaai2027.bst` | Author Kit, References | 本地与官方 SHA 相同；BLG 确认使用 | PASS | — | 无 |
| PDFLaTeX 编译 | Author Kit, Formatting Requirements | log 显示 pdfTeX 成功输出 | PASS | — | 无 |
| US Letter | Author Kit, Formatting Requirements | 全部页面 612×792 pt | PASS | — | 无 |
| 双栏 AAAI 布局 | Author Kit, Formatting Requirements | 7in text width、0.375in gutter | PASS | — | 无 |
| 不超出 margin/gutter | Author Kit, LaTeX Overflow | 无 overfull；对象边界均在页面内 | PASS | — | 无 |
| Main content 最多 7 页 | Main Track CFP, Summary | 第 8 页仍有 Figure 3/caption | FAIL | Critical | 所有非参考文献内容必须止于第 7 页 |
| 总长最多 9 页 | Main Track CFP, Summary | PDF 共 9 页 | PASS | — | 无 |
| 第 7 页后仅 references | Main Track CFP, Summary | 第 8 页为 Figure 3 + References 混排 | FAIL | Critical | 第 8–9 页仅保留 references |
| 不修改 geometry/spacing/fonts | Author Kit, Brief/Forbidden Commands | 未发现相关包或命令 | PASS | — | 无 |
| 禁止负间距压页 | Author Kit, Forbidden Commands | 未发现负 `vspace/vskip` | PASS | — | 无 |
| 禁止整体缩放表格 | Author Kit, Tables | 无 `resizebox/scalebox` | PASS | — | 无 |
| 标题使用 Title Case | Author Kit, Brief | 当前标题符合 | PASS | — | 无 |
| 正文使用 Times-like 字体 | Author Kit, Brief | `TeXGyreTermesX` | PASS | — | 无 |
| 匿名作者/机构 | Author Kit, Anonymous Submission | Anonymous；affiliation 空 | PASS | — | 无 |
| PDF metadata 不泄露身份 | Author Kit, Anonymous Submission | Title/Author 等为空 | PASS | — | 无 |
| 自引不得破坏双盲 | Author Kit, Anonymous Submission | 无身份式自引措辞 | PASS | — | 无 |
| PDF 无身份路径 | Author Kit, Anonymous Submission | PDF 未检出用户名/绝对路径 | PASS | — | 无 |
| 所有字体嵌入 | Author Kit, Brief | 全部字体资源已嵌入 | PASS | — | 无 |
| 禁止 Type 3 字体 | Author Kit, Brief | Type 3 = 0 | PASS | — | 无 |
| 禁止 CID/Identity-H 字体 | Author Kit, Brief | 两个 DejaVu Type 0 Identity-H 资源 | FAIL | Major | 最终图形阶段将字体转轮廓或使用合规字体编码 |
| PDF ≥1.5 | Author Kit, Brief | PDF 1.7 | PASS | — | 无 |
| 不加密/无密码 | Author Kit, Brief | 未加密 | PASS | — | 无 |
| 无 embedded links/bookmarks | Author Kit, Brief | links=0，bookmarks=0 | PASS | — | 无 |
| 无自定义页码/页眉/页脚 | Author Kit, Brief | 无自定义项；仅官方匿名提示 | PASS | — | 无 |
| 单一正文 `.tex`，不拆 section input | Author Kit, What Files to Submit | `main.tex` 无 `input/include` 正文 | PASS | — | 无 |
| Source 与 PDF 匹配 | Author Kit, Brief | PDF/log 晚于 source；抽取文本、标签和表格一致 | PASS | — | 无 |
| Table caption 位于表下 | Author Kit, Table Captions | Table 1–3 均位于下方 | PASS | — | 无 |
| Table caption 为 10 pt Roman | Author Kit, Table Captions | 实测约 9.963 pt Roman | PASS | — | 无 |
| Table body 10 pt，必要时 9 pt | Author Kit, Tables | 三表约 8.966 pt | PASS | — | 无 |
| 宽表跨双栏 | Author Kit, Tables | Table 1/2 为 `table*` | PASS | — | 无 |
| 表格应在首次讨论页或随后一页 | Author Kit, Illustrations and Tables | Table 1/2 从第 5 页延迟至第 7 页 | FAIL | Major | 合规调整源码/浮动顺序 |
| 表格编号与正文引用 | Author Kit, Illustrations and Tables | 编号连续；Table 2 无显式正文引用 | FAIL | Minor（并入上项修复） | 增加一次 `Table~\ref{tab:q2}` |
| References 位于源码末尾 | Author Kit, Preparing Your Paper/References | bibliography 后仅 `end{document}` | PASS | — | 无 |
| References 不小于 9 pt | Author Kit, References | 实测约 9.963 pt | PASS | — | 无 |
| AAAI author-year citation | Author Kit, References | natbib/AAAI author-year 正常 | PASS | — | 无 |
| 无 unresolved citation/reference | Author Kit, Proofreading | 均为 0 | PASS | — | 无 |
| 无 overfull box | Author Kit, LaTeX Overflow | hbox/vbox 均为 0 | PASS | — | 无 |
| 最终 source archive ≤10 MB | Author Kit, Final Archive | 未提供实际投稿 archive | UNKNOWN | — | 打包后单独核验 |
| 投稿 PDF 上传大小上限 | Main Track/Author Kit | 官方所查页面未给出可判定阈值 | UNKNOWN | — | 以 OpenReview 当前上传提示复核 |
| Figure 视觉与 caption 合规 | 用户明确排除 | 未审计 | UNKNOWN | — | 留至最终 Figure 阶段 |
| Supplement/appendix/checklist | 用户明确排除 | 未审计 | UNKNOWN | — | 独立任务 |

## 10. 问题分级

### Critical（1）

1. **第 8 页包含 Figure 3 及 caption，不是 references-only 页面。**  
   证据：`fig:behavior` 位于第 8 页；References 同页中部开始。  
   官方依据：Main Track CFP 明确要求第 7 页之后专用于 references。  
   风险：直接违反主赛道页数硬规则。

### Major（2）

1. **两个 PDF 字体资源使用 Identity-H 编码。**  
   字体已嵌入且无 Type 3，但仍违反官方对 CID/Identity-H 的独立限制。

2. **Table 1/2 与首次讨论位置间隔超过一页。**  
   两表均从第 5 页的讨论延迟到第 7 页；Table 2 还缺少显式正文引用。

### Minor（1）

1. **`paper/main.log` 暴露本地用户名路径。**  
   PDF 和正文不泄露；风险仅在误上传构建日志。投稿材料中排除非必需日志即可。

### Optional（2）

1. 14 个 underfull hbox 和 1 个 underfull vbox 未造成实际越界，可在最终版面校对时观察，不是硬性错误。
2. `references.bib` 有 2 个未引用条目；它们不进入 PDF，可为源文件洁净度而删除，但不是当前格式失败。

## 11. 最小修复清单

按优先级：

1. **P0：恢复 references-only 边界。** 在不使用负间距、整体缩放或小于许可字号的前提下，确保包括 Figure 3/caption 在内的全部非参考文献内容止于第 7 页；第 8–9 页只能包含 References。
2. **P0：消除 Identity-H 字体。** 在最终 Figure 技术导出阶段，将第 8 页导入对象中的 DejaVuSans/DejaVuSans-Bold 转为轮廓，或改用不会生成 CID/Identity-H 的合规嵌入方式。无需改变 Figure 科学内容。
3. **P1：调整 Table 1/2 浮动位置。** 使其位于首次讨论页或随后一页，并给 Table 2 增加显式正文引用。不得使用负间距、`resizebox`、`scalebox` 或缩小到 9 pt 以下。
4. **P1：清洁匿名投稿包。** 不要把 `main.log`、`main.fls`、历史 `compile_*.log` 等带有绝对工作区路径的非必需文件上传。
5. **P2：打包后复核。** 独立核验最终 source archive 的可编译性、所需图形集合和 ≤10 MB 限制；核对 OpenReview 当前 PDF 上传大小提示。

## 12. 最终结论

模板、匿名 PDF、页面几何、三张表的字号与 caption 基本格式、引用样式、字体嵌入、Type 3、链接、公式和 LaTeX 错误均通过。但是，第 8 页包含非参考文献内容，构成 Main Track 页数硬规则违反；同时还存在 Identity-H 字体和 Table 1/2 浮动距离问题。

# `AAAI27_FORMAT_COMPLIANCE_REVISE`
