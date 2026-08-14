# TerraState Section 4.3 修订记录

**日期：** 2026-07-28  
**状态：** `READY_FOR_4_3_AUDIT`  
**依据：** `SECTION4_4_3_AAAI_AUDIT_20260728.md`  
**范围：** Section 4.3 英文正文、Table 2 caption、完整中文镜像，以及两个
简版 Markdown 的 4.3 与 Table 2 镜像

## 1. 修改范围

修改文件：

- `paper/main.tex`；
- `MANUSCRIPT_ZH_FULL.md`；
- `MANUSCRIPT.md`；
- `MANUSCRIPT_ZH.md`；
- `SECTION4_4_3_REVISION_LOG_20260728.md`。

未修改：

- Section 3；
- Section 4.1、4.2、4.4；
- Table 2 的表体、数值、行列、指标和 CI；
- Figure 1–3；
- Abstract、Introduction、Conclusion；
- 证据 JSON、ledger、代码、checkpoint 或实验文件。

## 2. 修改前后结构

### 修改前

1. 重新提出 Q2；
2. 说明 state removal 为 primary、\(T\to I\) 为 supporting；
3. Table 2；
4. 先报告 dataset-level official \(\Delta R^2\)；
5. 再报告 paired mean 与 CI；
6. 给出 load-bearing 结论；
7. 限定 \(T\to I\) 的证据地位。

### 修改后

1. **结论先行：** 显式 state-mediated contribution 在 Validation 和 OOD-t
   上均为 load-bearing，state removal 是 primary intervention；
2. **Table 2：** 保留完整六列结果；
3. **Primary paired evidence：** 先报告两个 split 的 paired mean、95% CI
   和 \(n\)，并说明两个区间均排除零；
4. **Dataset-level scale：** 另句报告 official full-minus-removal
   \(\Delta R^2\)；
5. **有限科学解释：** 显式状态路径承载可测量预测增量，但不意味着全部预测信息
   都经过该路径；
6. **Supporting diagnostic：** \(T\to I\) 的同方向退化只支持 learned
   transition involvement，并保留 readout 输入分布变化的限制。

## 3. 长度与段落职责

- 修改前 prose-only：约 116 个英文词（前置审计口径）；
- 修改后 prose-only：135 个英文词；
- 结构：Table 2 前 1 句结论；Table 2 后 5 句解释；
- 未拆分 Validation 和 OOD-t 为重复段落；
- 未逐格朗读 Table 2。

## 4. 证据层级

### Primary state-removal evidence

- Validation：paired mean \(\Delta R^2=0.01616\)，95% CI
  \([0.00643,0.02590]\)，\(n=589\)；
- OOD-t：paired mean \(\Delta R^2=0.02200\)，95% CI
  \([0.01422,0.03018]\)，\(n=1{,}019\)；
- 两个 paired-bootstrap 区间均排除零。

### Dataset-level effect size

- Validation official full-minus-removal \(\Delta R^2=0.01121\)；
- OOD-t official full-minus-removal \(\Delta R^2=0.01997\)。

正文将 paired mean/CI 与 official dataset-level effect 分句报告，没有把 paired
CI 写成 official \(\Delta R^2\) 的置信区间。

### Supporting transition diagnostic

- \(T_\psi=\mathrm{Id}\) 的退化方向一致；
- 只解释为 learned-transition involvement；
- identity substitution 可能使 readout 接收训练分布外状态，因此不支持
  transition necessity。

## 5. Table 2 caption

caption 保持在表格下方，并新增：

> The paired samples contain \(n=589\) minicubes for Validation and
> \(n=1{,}019\) for OOD-t.

没有新增列，也没有修改表体。

Table 2 `tabular` 修改前后 SHA-256 均为：

`a372f2ae9fa3ce9d80298fee89453e1565e0eeabc269e671537baad42ebb069b`

因此 Table 2 的所有数值、行、列、RMSE、official effect 和 paired effect/CI
均保持不变。

## 6. 主张边界

修订后支持：

- state removal reduces forecast quality on both splits；
- the explicit state path carries a measurable forecast increment；
- the state-mediated contribution is load-bearing on both splits；
- \(T\to I\) supports learned-transition involvement。

修订后没有声称：

- 整个预测完全依赖状态；
- 所有预测信息都必须经过状态；
- necessary-and-sufficient 或完整物理状态；
- causal contribution 或 counterfactual correctness；
- transition necessity；
- OOD-t 效应显著强于 Validation；
- non-collapse、composition/Q4；
- 内部 0.005 floor 是论文判据。

## 7. 中英文与简版镜像

四份文本已同步：

| 文件 | 4.3 prose | Table 2 |
|---|---|---|
| `paper/main.tex` | 英文权威版本 | 六列权威表；caption 加 paired \(n\) |
| `MANUSCRIPT_ZH_FULL.md` | 完整中文镜像 | 六列镜像；表注加 paired \(n\) |
| `MANUSCRIPT.md` | 英文阅读镜像 | 旧八列结构同步为当前六列结构 |
| `MANUSCRIPT_ZH.md` | 中文阅读镜像 | 旧八列结构同步为当前六列结构 |

中文使用“承载可测量的预测增量”，没有翻译成“整个预测完全依赖状态”。

## 8. 冻结回归

以下区间 SHA-256 与修改前一致：

- Section 3：  
  `b054a42ed0783ad8bfbfa731bef5137cde11b68a58f1048ce12ad14fc4dbdf7d`
- Section 4.1：  
  `9feea977ba80119b27150811ca2cb50471f7bf0c8380d7e2aad95466cf8b5f45`
- Section 4.2：  
  `1255639a23e12090bece746b81f879ac3adcaa3af789d018adb22c3898666740`
- Section 4.4：  
  `017ba3a9643c878a4cd885709d7cddd634859fef759b050059f4ae5964da74b4`

4.3 中没有恢复 11,904、boundary80、Published/Local/Source、single seed 或
single run 叙事。

## 9. 编译与排版检查

编译命令：

`latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`

结果：

- PDF：`paper/main.pdf`；
- 编译成功：是；
- LaTeX errors：0；
- undefined citations：0；
- undefined references：0；
- multiply-defined labels：0；
- overfull boxes：0；
- underfull hboxes：7；
- underfull vboxes：0；
- Table 2 caption 位于 `tabular` 之后，`\label{tab:q2}` 紧跟 caption；
- Table 2 没有裁切或严重溢出。

普通 underfull 不构成本轮阻塞，未据此改动其他章节或整体版面。

## 10. 修改后 SHA-256

- `paper/main.tex`：  
  `7e2e5f33a6584a0d1558041e27cf31fd4c4124c9aa1cfcd33b642874a28e11c2`
- `MANUSCRIPT_ZH_FULL.md`：  
  `7c987ff0a581efa70fcad56ae5eecf24ebf107794b5f29c7694b5222ad828469`
- `MANUSCRIPT.md`：  
  `91b1de611e21c0d6f283e68e90af374804834dead982e1dce9b53c01943270db`
- `MANUSCRIPT_ZH.md`：  
  `b3d88f0d5a07e8984b0c102ec56522dbb38b8e8e0b3f2e68dd5abd0ee9303354`
- `paper/main.pdf`：  
  `4238bcdbde2785f8a135f27165f4340e50af1de358501a97cfebecb36d8cbcd6`
- Section 4.3（含 Table 2）：  
  `393750e4bb4f8e23703ebac4dd0ccd510257e5b62f00b216a32fe15b9a5a9d3a`

## 11. 阻塞状态

未发现事实、证据、交叉引用或编译阻塞。本轮没有继续修改 Section 4.4 或启动
全篇审计。

## 12. 最终状态

`READY_FOR_4_3_AUDIT`
