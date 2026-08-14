# TerraState Figure 1：AAAI 视觉锚点与方案审计

审计日期：2026-07-27  
范围：只比较视觉组织原则，不把锚点论文加入 TerraState 的正文引用，也不复刻其构图、配色、图标或文字。所有锚点均来自 AAAI Proceedings 官方页面与官方 PDF；下载副本及所审页面位于 `literature/aaai_figure_anchors/`。

## 1. 结论

推荐 **方案 B：方法闭环主导、训练监督分层、同检查点验证压缩为次级条带**。据此生成的 `terrastate_overview_v3` 明显优于 v2，已经接入 `main.tex`，但 v1/v2 源文件均保留，可随时回退。

v3 第一视觉层是一个天气驱动的预测状态世界模型：历史上下文经 \(q_\theta\) 与 \(P_\rho\) 得到 \(z_t\)，full24 天气、地理与预测时距进入共享 \(T_\psi\)，\(O_\omega(z_{t+h})\) 与 context-only prior \(b_h\) 显式相加形成预测。三项训练信号位于独立橙色区域；Q1–Q3 与可选 Q4 被压缩到底部训练后验证条带。它因此不会像 v2 那样让“方法”和“验证协议”在视觉上平分 Figure 1。

## 2. AAAI 主会锚点

### 2.1 Drive-OccWorld，AAAI 2025

- 准确标题：*Driving in the Occupancy World: Vision-Centric 4D Occupancy Forecasting and Planning via World Models for Autonomous Driving*
- 官方来源：[AAAI Proceedings 文章页](https://ojs.aaai.org/index.php/AAAI/article/view/33010)；[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/33010/35165)
- 图与页码：Figure 1，PDF 第 2 页；完整方法图 Figure 2，PDF 第 3 页。
- 与 TerraState 的相关性：同样需要把“历史观测 → 状态表示 → 世界模型推进 → 未来输出”作为第一层叙事，并同时解释条件输入和下游预测。
- 组织方式：Figure 1 先用真实占据序列建立任务直觉；Figure 2 再以双栏通栏方式展示 history encoder、memory、world decoder、动作条件和预测/规划输出。
- 视觉特征：分区底色明确；主箭头连续；真实输入/输出缩略图帮助读者把抽象模块映射回任务；caption 较长但能独立说明各区作用。模块与嵌套细节较密，局部文字在论文尺度下偏小。
- 可借鉴：方法主链应占主要面积；输入/输出可保留“真实数据槽位”；不同功能区使用浅底色而不是大量高饱和颜色。
- 不应照搬：自动驾驶图标、三维方块、规划器支路和高度嵌套的 decoder 细节不属于 TerraState；真实图像在固定样本与统一色标产生前不能进入正文。

### 2.2 GLAM，AAAI 2025

- 准确标题：*GLAM: Global-Local Variation Awareness in Mamba-based World Model*
- 官方来源：[AAAI Proceedings 文章页](https://ojs.aaai.org/index.php/AAAI/article/view/33880)；[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/33880/36035)
- 图与页码：Figure 1，PDF 第 1 页；方法总览 Figure 2，PDF 第 3 页。
- 与 TerraState 的相关性：Figure 2 以输入、编码、两条动力学分支、融合和输出构成完整推理路径，训练/验证信息没有与主架构争夺视觉中心。
- 组织方式：上半部画端到端主链；下半部只展开两个必要机制和符号图例。
- 视觉特征：双栏通栏；两种主色对应两条机制；箭头方向稳定；模块标签大于公式标签；caption 先给总览再解释分支。
- 可借鉴：主链优先、机制细节次级；只为真正不同的语义使用不同颜色；图例集中。
- 不应照搬：GLAM 的内部单元展开和大量圆形符号对 TerraState 没有必要；TerraState 不应把 GRU 细节画成第二个视觉中心。

### 2.3 SparseWorld，AAAI 2026

- 准确标题：*SparseWorld: A Flexible, Adaptive, and Efficient 4D Occupancy World Model Powered by Sparse and Dynamic Queries*
- 官方来源：[AAAI Proceedings 文章页](https://ojs.aaai.org/index.php/AAAI/article/view/37347)；[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/37347/41309)
- 图与页码：Figure 1，PDF 第 1 页；方法总览 Figure 2，PDF 第 3 页。
- 与 TerraState 的相关性：清楚区分感知、状态条件动力学和并行输出头，并用真实输入/输出样例强化方法论文的第一印象。
- 组织方式：双栏通栏，由左到右分四区；主架构和必要模块展开处于同一水平带；caption 逐区解释。
- 视觉特征：虚线大区框、浅色机制框、统一方向的主箭头；实物图像和抽象 token 并存。信息密度较高，但层级仍可追踪。
- 可借鉴：分区标题直接对应论文小节；状态转移必须处于主链中央；输出缩略图应服务于语义，而非装饰。
- 不应照搬：多级 decoder 内部结构、点云/占据图像和橙色循环支路会让 TerraState 过度工程化。

### 2.4 STICA，AAAI 2026

- 准确标题：*Object-Centric World Models for Causality-Aware Reinforcement Learning*
- 官方来源：[AAAI Proceedings 文章页](https://ojs.aaai.org/index.php/AAAI/article/view/39642)；[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/39642/43603)
- 图与页码：Figure 1，PDF 第 2 页。
- 与 TerraState 的相关性：同一通栏图同时容纳世界模型、对象级表示样例和策略/价值网络，说明方法与语义证据可以共存，但必须有强层级。
- 组织方式：架构、重建可视化、下游决策三个面板并列；caption 明确按 (a)–(c) 解释。
- 视觉特征：模块与样例图丰富、箭头关系完整；但面板多、注释密，缩放后局部文本较吃力。
- 可借鉴：若未来加入真实定性结果，应作为清楚标号的独立子图，而不是混入推理箭头。
- 不应照搬：Figure 1 同时承担架构、表示质量和下游机制会提高理解成本；TerraState 当前不应把 Q1–Q4 扩成同等大小的四个面板。

### 2.5 Knowledge Boundary，AAAI 2026

- 准确标题：*Perceiving the Knowledge Boundary: Uncertainty-Guided Exploration and Imagination for World Models*
- 官方来源：[AAAI Proceedings 文章页](https://ojs.aaai.org/index.php/AAAI/article/view/39576)；[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/39576/43537)
- 图与页码：Figure 1，PDF 第 2 页；架构 Figure 2，PDF 第 4 页。
- 与 TerraState 的相关性：Figure 1 先以简洁概念图和真实 rollout 建立问题直觉，把完整技术架构留给后续图。
- 组织方式：概念与现象优先，方法细节后置；双栏宽度保持充分留白。
- 视觉特征：箭头少、字体大、真实序列占据重要面积、caption 自解释；审稿人第一眼负担低。
- 可借鉴：Figure 1 不必承载所有工程细节；状态语义和输入/输出任务应先于细粒度实现。
- 不应照搬：TerraState 目前没有可诚实展示的固定真实样本数组，也不值得额外付出 Figure 2 的版面成本。

### 2.6 WorldAgen，AAAI 2026

- 准确标题：*WorldAgen: Unified State-Action Prediction with Test-Time World Model Training*
- 官方来源：[AAAI Proceedings 文章页](https://ojs.aaai.org/index.php/AAAI/article/view/38925)；[官方 PDF](https://ojs.aaai.org/index.php/AAAI/article/download/38925/42887)
- 图与页码：Figure 1，PDF 第 2 页；Figure 2，PDF 第 4 页。
- 与 TerraState 的相关性：同一图同时展示方法架构、训练流程和一个小型性能面板，接近 TerraState “方法 + 训练信号 + 验证”的组织难题。
- 组织方式：方法架构占上半部，训练流程与性能图占下半部；以 (a)–(c) 明确层级。
- 视觉特征：双栏、浅色虚线边界、实物缩略图和 token 结合；信息完整但几乎占满整页，caption 很长。
- 可借鉴：方法必须拥有最大的单一区域；训练过程与结果需要视觉降级。
- 不应照搬：把性能图放入方法总览会让 TerraState 的 Q1–Q4 反客为主，也会增加当前 9 页稿件的版面压力。

## 3. 从锚点提取的共同原则

1. AAAI 并不存在一种固定“流程图模板”；真正稳定的共同点是**单一阅读方向、明显的语义分区、方法主链最大、caption 能独立解释**。
2. 方法型 world-model 论文通常让 representation/state/dynamics/output 成为第一层；训练细节或验证结果只能作为第二层或另图。
3. 真实输入/输出小图能提高任务直觉，但只有在样本选择、色标和数据 provenance 固定后才应进入投稿图。
4. 双栏通栏很常见，但通栏不是容纳无限信息的许可。局部机制展开、训练流程、结果图若同时出现，字体会迅速跌破可读尺度。
5. 颜色主要用于区分语义区域；箭头样式比颜色更可靠。黑白打印时仍需靠实线、虚线、点线和边框形态维持含义。

## 4. v2 语义与视觉审计

### 优点

- TikZ 矢量、双栏通栏，推理、训练监督、训练后干预已有线型区分。
- \(q\!\rightarrow z_t\!\rightarrow T\!\rightarrow z_{t+h}\!\rightarrow O\) 与 \(b_h\) 加法闭环基本准确。
- Q2/Q3 的干预位置清楚；Q4 已使用灰色虚线降级。
- 版面高度较低，接入稳定。

### 主要问题

- 右侧 Q1–Q4 约占三分之一且与方法区同高，第一眼容易把论文理解为 diagnostic/benchmark paper。
- \(q_\theta\) 与 \(P_\rho\) 合并为 \(q_{\theta,\rho}\)，弱化了“上下文预测骨干”与“状态投影器”的区别。
- 只突出 future-state alignment，没有同时展示唯一三项训练信号
  \(\mathcal L_{\mathrm{GT}}+0.5\mathcal L_{\mathrm{KD}}+\lambda_s\mathcal L_{\mathrm{future-state}}\)。
- 冻结 full-weather KD teacher 缺失；observed future EO 支路虽用橙色标记，仍可能被误读为推理输入。
- 没有给任务输入/输出留下直观图像槽位，抽象模块多于地表预测语义。

## 5. 三种方案比较

评分范围 1–5，越高越好；“抗 benchmark 误判”表示越不容易被误读为主要提出评测协议。

| 指标 | A：保留左右双区 | B：方法主导 + 验证条带 | C：方法 Figure 1 + 验证 Figure 2 |
|---|---:|---:|---:|
| 方法型论文第一印象 | 3.5 | **5.0** | 5.0 |
| world-model 主线清晰度 | 4.0 | **5.0** | 5.0 |
| 与正文公式一致性 | 5.0 | **5.0** | 5.0 |
| 抗 benchmark 误判 | 3.0 | **5.0** | 5.0 |
| AAAI 双栏可读性 | 4.0 | **4.5** | 4.5 |
| 页面成本 | **5.0** | **5.0** | 2.5 |
| 黑白/色盲可辨识性 | 4.0 | **4.5** | 4.5 |
| caption 自解释程度 | 4.5 | **5.0** | 4.5 |
| 合计 / 40 | 33.0 | **39.0** | 36.0 |

### 方案 A

改动最小，能够补齐三项 loss 和 KD teacher，但 verification 仍与方法视觉并列，不能彻底解除“论文主要贡献是一套验证协议”的风险。

### 方案 B

把推理闭环放在最大区域；训练监督放在独立色带；Q1–Q3 与 optional Q4 压成同检查点验证条带。它与论文“一个 TerraState，证据链验证同一模型”的层级最一致，且不增加浮动体。

### 方案 C

方法叙事最纯，但需要新增 Figure 2。当前结果仍为 TBD，第二张图只能再次画协议，既增加页数成本，也会加重后部 Table 1–3 的浮动体拥挤。若未来获得高质量、固定样本的定性结果，Figure 2 才值得重新评估。

## 6. v3 验收

- 文件：`paper/figures/terrastate_overview_v3.tex/pdf/png`。
- 论文尺度预览：`paper/figures/terrastate_overview_v3_paperscale.pdf/png`。
- 对比：`paper/figures/terrastate_overview_v2_v3_paperscale_comparison.pdf/png`。
- 主链约占图高的一半以上且横向贯通；验证条带只占底部约八分之一。
- 明确分开 \(q_\theta\) 与 \(P_\rho\)，并画出 \(b_h\) 与 \(O_\omega(z_{t+h})\) 的显式加法。
- full24 future weather 只进入共享 \(T_\psi\)；past meteorology 与 static \(g\) 进入 history-only context operator；future weather 不进入 \(b_h\)。
- 橙色训练区完整写出唯一三项损失，包含 frozen full-weather teacher 与仅用于 \(h=20\) 的 future-state anchor。
- teacher 与 observed future EO 均未连接到实线推理路径。
- Q1–Q3 为实边框，Q4 为灰色虚线；实线、橙色虚线、灰色点线即使在灰度预览中仍可区分。
- 输入/输出使用明确标注为示意性的矢量缩略槽，不冒充真实结果；真实定性数组仍等待固定样本和统一色标。
- v3 使用 Times-like 矢量字形；最小源字号 19pt，在 `0.98\textwidth` 的实际缩放下约为 9.4pt，满足 Author Kit 的 9pt 下限。
- 最细源线宽 1.1pt，按同一缩放后约为 0.55pt；颜色之外还使用实线、虚线、点线和边框形态编码语义。
- v3 在 AAAI 实际宽度下比 v2 高约 30pt，但仍位于 PDF 第 2 页顶部，未引入 overfull box 或额外页数。

## 7. 保留事项

- 三阶段训练 curriculum 继续留在正文，不挤入 Figure 1；它是优化过程，不是推理图的第一层语义。
- 在真实样本、固定选择规则、统一色标和 provenance 可用前，不把卫星影像或预测热图替换进 Figure 1。
- 若最终 Q4 证据弱或未执行，底部灰色 Q4 卡片可在最终结果接入时移除；这一调整不会改变主图结构。
