# TerraState Figure 3 单栏布局最终审计

最终状态：`FIG3_SINGLECOL_LAYOUT_FROZEN`

审计日期：2026-07-28  
审计范围：Figure 3 单栏图源、导出、LaTeX 浮动体、最终论文页面、数据
trace 与 QA。未重新评估模型，未修改冻结数据或 Figure 3 之外的论文内容。

## 1. 最终布局

- Figure 3 使用 AAAI 双栏论文中的标准单栏 `figure[t]`，宽度为
  `\columnwidth`。
- 图面为 `3.3 × 3.5 in`：
  - (a) Q2 横向占满上方；
  - (b) matched-donor 与 (c) normalized-mean 在下方并排。
- 最终 PDF 中 Figure 3 为第 3 号图，位于第 8 页左栏；整图、图注均在
  单栏边界内。References 从图注下方开始，并在右栏继续。
- 第 7 页由 Results、Table 1–3、Limitations 和 Conclusion 连续填充，
  不再出现原先由不可分页结构造成的大面积空白。

## 2. LaTeX 修改前后

### 问题版本

问题版本使用 `center + minipage + captionof` 将图和长图注绑成一个不可分页
整体，曾产生约 121 pt 的 overfull vbox，并引发挤压和分页副作用。

### 最终版本

```latex
\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{../figure_workspace/export/fig3_behavior_singlecol.pdf}
\caption{State and weather interventions. (a) Paired per-minicube
$\Delta R^2$ after state removal (filled, primary) or $T\!\rightarrow I$
(open, supporting); lines show paired-bootstrap 95\% CIs. (b,c) Complete
20-step-window masked MSE under actual weather versus matched-donor and
normalized-mean controls for 84 frozen pairs. Points above the diagonal favor
actual weather; 56/84 and 69/84 are descriptive counts.}
\label{fig:behavior}
\end{figure}
```

正文中的 `Figure~\ref{fig:behavior}(b,c)` 引用保持不变。

## 3. Caption 调整与语义一致性

原图注为较长的自包含版本；最终图注压缩为约 56 个英文词，删除重复解释，
但保留全部科学语义：

1. (a) 是逐 minicube 配对 \(\Delta R^2\)；
2. state removal 为 filled/primary；
3. \(T\!\rightarrow I\) 为 open/supporting；
4. 横线为 paired-bootstrap 95% CI；
5. (b,c) 为 84 个冻结配对上的完整 20 步预测窗口 masked MSE；
6. 对角线上方表示 actual weather 更优；
7. `56/84` 与 `69/84` 仅为描述性计数。

图注没有引入 causal、counterfactual、composition/Q4 或
extreme-specific enhancement 主张。

## 4. 冻结数据回归

| 项目 | 最终验证值 | 结论 |
|---|---:|---|
| Validation state removal | `0.01616252595360122`, CI `[0.006432408120151691, 0.02590229577842624]`, `n=589` | PASS |
| Validation \(T\to I\) | `0.017417428921451206`, CI `[0.007824839508750908, 0.026960749441100905]` | PASS |
| OOD-t state removal | `0.021997768589881533`, CI `[0.014219898623411737, 0.03017606928017251]`, `n=1019` | PASS |
| OOD-t \(T\to I\) | `0.024015932710944276`, CI `[0.016086752271438905, 0.032169788967835664]` | PASS |
| Q3 配对数 | `84`；unique `84`；missing/non-finite `0` | PASS |
| donor-minus-actual | `0.002565468112672014` | PASS |
| mean-minus-actual | `0.011261332329706334` | PASS |
| 对角线上方计数 | donor `56/84`；mean `69/84` | PASS |
| 误差窗口 | complete 20-step forecast window，不是仅 \(h=20\) | PASS |

没有手填、筛选或重算数据点；所有数值由冻结 JSON 经 v2 数据读取与校验逻辑
获得。

## 5. 图形与纸面 QA

- Figure 3 PDF media box：`237.6 × 252.0 pt`。
- Figure 3 PDF 中 raster image object：`0`，保持矢量。
- SVG：`35` 个文本节点、`0` 个嵌入图片节点，文字保持可编辑。
- 最终字号配置：`7.5–8.5 pt`。
- paper-scale：PASS，无坐标、CI、标签、点或计数裁切。
- grayscale：PASS；filled/open marker 和分面结构使颜色不是唯一编码。
- in-paper：PASS；不侵入右栏，不与 Table 3、正文或 References 重叠，
  图与图注未分离。

最终预览：

- `figure_workspace/qa/fig3_behavior_singlecol_paperscale.png`
- `figure_workspace/qa/fig3_behavior_singlecol_grayscale.png`
- `figure_workspace/qa/fig3_behavior_singlecol_inpaper.png`

本轮生成的试排页面预览已删除，避免后续误用。

## 6. 编译门禁

- `paper/main.pdf`：9 页。
- LaTeX errors：`0`。
- undefined citations/references：`0`。
- overfull hbox：`0`。
- overfull vbox：`0`。
- 普通 underfull 提示不造成裁切或阅读顺序问题。
- Figure 2 仍为第 2 号图（第 6 页），Figure 3 为第 3 号图（第 8 页）。
- Table 1–3、Section 1、Section 2、Method、Limitations、Conclusion 和
  References 阅读顺序正常。

## 7. 输出与哈希

### Figure 3 单栏文件

| 文件 | SHA-256 |
|---|---|
| `figure_workspace/source/fig3_behavior_singlecol.py` | `4bbe7d71613c5358352688dac93dc417598d42728074af86890dd955d5ad31d0` |
| `figure_workspace/source/fig3_behavior_singlecol.svg` | `399ebcd4335aabc4ea0dcbd46a279a6789b5af14a5ea237ebe9bd3ea88cca503` |
| `figure_workspace/export/fig3_behavior_singlecol.pdf` | `3b9c764152a867b2d1aef1b82b5661eb18bbd613236cb37dc45d58dfac7f0a53` |
| `figure_workspace/export/fig3_behavior_singlecol.png` | `9299c97fe61bf123dcdfa761e92cf056c4dbfaebefe5bcc662975049840919ed` |
| `figure_workspace/qa/fig3_behavior_singlecol_grayscale.png` | `f5191df49c0e5258eed5f143642486f10722363121f6a86580ea29b2b45a61e1` |
| `figure_workspace/qa/fig3_behavior_singlecol_paperscale.png` | `af55372e7ecc64572b4a42f588b14f539ab5a047a2e7f830711e756a27fecd46` |
| `figure_workspace/qa/fig3_behavior_singlecol_inpaper.png` | `8a1610c05b6fce239e1b8474e9b2d5a4e461ad7789b2b8e25e2512b60ea8b3e4` |
| `figure_workspace/qa/fig3_behavior_singlecol_qa.json` | `e5405316086836c0d6583b2abde0fcfe1dc8b3e76caa9165e041bd9e97ea43cf` |

### 正文编译文件

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `0bd80eb824005857fb03930c74a581b153417019559974476d12d94dd3d79d00` |
| `paper/main.pdf` | `a9892a795aa3f506c844cce184234f82bc507959b4dec8cde219d8386104c7e6` |
| `paper/main.log` | `d74f82c46a4c42a971b14ecdee1bb95246bf85d19c5ab2cb40180bf902eb951c` |

完整 frozen-source 与 output trace 见
`figure_workspace/FIG3_SINGLECOL_DATA_TRACE.md`。

## 8. Figure 3 之外的内容保护

本轮对 `main.tex` 的可归因修改仅为 Figure 3 浮动体。以下冻结局部哈希保持
现有审计值：

| 对象 | 当前 SHA-256 | 冻结核对 |
|---|---|---|
| Abstract 环境 | `d067709e98b84830d0c5a3cd78ac1f51904e5a42ac0b70abb993186ab64721ab` | 与 Section 1/2 审计一致 |
| Introduction 区块 | `ce34d1ca444bf783eb4ccad116bfb1f4a9dde7f67a1d03dddd328eff04bc2b92` | 与 Section 1/2 审计一致 |
| Related Work 区块 | `e6609d90667a20d41e196bca0c1da50e6b928428e707439b6368d155eee4bc94` | 与 Section 2 修订日志一致 |
| Table 1 完整环境 | `ec5b1dd99126d54306894f5263c9f1dad6247ae2c805899fc00e0d75c2f3cfce` | 与 Section 4.2 审计一致 |
| Table 1 tabular | `e138d52fbfb8c374a48cd6342d8cc5b53a4f95773e228805092b4501dedbdf36` | 与 Section 4.2 审计一致 |
| Table 2 完整环境 | `5281b09bbfaff9f57ed1ef17f243b161d2588ea571c7aca393ce0b62fadb1197` | 与 Section 4.3 审计一致 |
| Table 2 tabular | `a372f2ae9fa3ce9d80298fee89453e1565e0eeabc269e671537baad42ebb069b` | 与 Section 4.3 审计一致 |
| Table 3 tabular | `c33059fe7767b658cc70d193e83567ce34053f9d153e815dcd84122b48c8d991` | 与 Section 4.4 审计一致 |

未修改任何 MANUSCRIPT 文件、references.bib、Figure 1、Figure 2、表格、
冻结 JSON、ledger、实验或模型文件。
