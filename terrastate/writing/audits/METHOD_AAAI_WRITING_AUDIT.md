# TerraState Method：AAAI 写作范式与修订审计

> 日期：2026-07-27  
> 范围：Problem Formulation、Method、Training Objective 与干预定义  
> 约束：只调整论文表达和信息层级，不改变代码事实、方法合同、结果或冻结主线。

## 1. 本节开始前的一手调研

本轮先检查项目内最相近 EO 工作，再补充 AAAI 正式论文。PDF 保存在
`literature/` 与 `literature/method_writing_anchors/`。外部检索只用于建立
写作与结构锚点；没有因为“文献更新”机械扩充正文引用。

| 锚点 | 一手来源 | 方法节的组织方式 | 对 TerraState 的可借鉴点 |
|---|---|---|---|
| SparseWorld (AAAI 2026) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/37347) | 先用公式区分两类预测范式，再给四组件总览；每个核心模块按缺口、机制、效果展开；训练策略最后出现 | 先锁定 \(q\!\to\!P\!\to\!T\!\to\!O\) 闭环，再写模块；不要把课程和优化器混进状态定义 |
| WorldAgen (AAAI 2026) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/38925) | Task Formulation 先定义轨迹单元，随后分别解释 world modeling、action prediction 和 test-time adaptation | Problem Formulation 应只定义对象与目标；训练期支路必须与推理链分开 |
| Modeling Latent Non-Linear Dynamical System over Time Series (AAAI 2025) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/33269) | 先区分 latent state 与 observable，再写状态方程和观测方程，最后给出待求问题 | 先定义 \(z_t\)、\(T_\psi\) 和 \(O_\omega\) 的角色，再称其为 predictive state，避免先给名称后补条件 |
| Learning Hybrid Dynamics Models with Simulator-Informed Latent States (AAAI 2024) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/29075) | Problem Setting 与 Method 分开；显式写出 additive observation model，并说明 additive 结构允许控制其中一条贡献路径 | \(b_h+r_h\) 的价值应写成“可移除且匹配的状态贡献”，同时明确它不表示全部预测都经过状态 |
| Unlocking Efficient Vehicle Dynamics Modeling via Analytic World Models (AAAI 2026) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/39629) | Method 开头先列 notation 与 strategy，随后每个任务写清输入、预测量和监督量 | 训练教师、future-state target 与推理输入必须逐项标明身份，不能只靠图示暗示 |
| Pre-Trained Video Generative Models as World Simulators (AAAI 2026) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/42465) | Preliminaries 定义世界模拟任务；Method 先给三个模块的路线图，各子节从需求进入机制 | 每个 TerraState 子节固定使用“目的 → 机制 → 可检验性质”，不从层数或超参数起笔 |
| EO-WM (2026 preprint) | [arXiv](https://arxiv.org/abs/2606.27277) | Problem Formulation 明确部分可观测 EO、外生天气和预测目标；随后按 architecture 与物理条件模块展开 | 保留天气作为外生驱动和部分可观测设定，但不要复制其概率生成或 benchmark 叙事 |
| VegSim (2026 preprint) | [arXiv](https://arxiv.org/abs/2606.21961) | 先区分 forecasting 与 scenario simulation，再按历史状态、未来条件、递归动力学和 decoder 展开 | 必须说明 TerraState 与其相近结构的实质差异：状态进入可移除的预测闭环，并接受匹配干预 |
| LatentTSF (ICML 2026) | [PMLR](https://proceedings.mlr.press/v306/yang26a.html) | 先写 observation-space 与 latent-space 两种任务，再依次解释 state construction、latent forecasting 和 objective | Future-state anchor 的方法意义是为 transitioned state 提供未来观测表征目标，而不是自动证明状态有预测作用 |

### 2026-07-27 增量检索

- AAAI 2026 的 *Decoupled Spatiotemporal Forecasting from Extreme Sparse
  Observations via Quantized Latent Space* 采用“空间重建—潜空间时间外推”的
  两阶段写法，支持“先定义表示，再定义动力学”的结构原则，但其 VQ 稀疏观测问题
  与 TerraState 不够接近，因此不加入正文引用。
- *Earth-o1* 和最新 cloud-aware EO world model 分别聚焦观测原生大气预测与
  acquisition observability；它们有助于确认世界模型术语正在扩展，但不改变
  TerraState 的问题定义，也不应被硬塞入 Method。

## 2. 从锚点归纳出的 Method 写作规则

1. **Problem Formulation 只回答“给定什么、预测什么、状态如何进入”。**
   数据尺寸、优化器、训练卡数和诊断判定不在这里展开。
2. **总公式必须与图完全同构。** 对 TerraState，应显式分开
   \(q_\theta\)、\(P_\rho\)、\(T_\psi\)、\(O_\omega\)，不再用
   \(q_{\theta,\rho}\) 模糊编码器与投影器。
3. **名称跟在性质之后。** 先说明状态来自历史、受未来天气推进并进入预测闭环，
   再解释为何称为 predictive state。
4. **每个方法小节采用“目的 → 机制 → 可验证性质”。** 首段首句写目的；中间
   给最低限度结构与公式；末句说明该结构允许什么检验，但不宣告检验已通过。
5. **训练与推理解耦。** Teacher 和 future-observation target 只能出现在训练
   目标小节，且必须明确推理时删除。
6. **训练方法与经验验证解耦。** Future-state alignment 是学习信号，Q2
   state-contribution ablation 才检验状态是否承载预测。
7. **核心机制留正文，运行日志下沉。** 状态形状、必要结构和总损失属于 Method；
   optimizer、GPU batch、精确更新数与参数统计属于 Experimental Setup /
   Reproducibility。
8. **干预在 Method 中只定义语义。** 样本配对、bootstrap、control 构造与判定
   逻辑放 Experiments；避免方法看起来像评测协议集合。

## 3. 当前稿的逐项问题

| 严重度 | 当前问题 | 风险 | 修订动作 |
|---|---|---|---|
| MAJOR | 总公式写成复合 \(q_{\theta,\rho}\)，后文又拆成 \(q_\theta\) 与 \(P_\rho\) | 与 Figure 1 及标题主链不完全同构，读者难判断状态究竟由谁产生 | 总式显式写 \((b_{1:H},h_t)=q_\theta(\widetilde{\mathcal C}_t)\)、\(z_t=P_\rho(h_t)\) |
| MAJOR | Problem Formulation 同时承担泄漏防护、方法解释和 Q2/Q3 预告 | 形式化目标被内部审计语言打断 | 保留输入隔离的科学含义，用一段定义、一条闭环公式和一段 predictive-state 条件完成 |
| MAJOR | Method 内优化器、GPU、update 数、参数组细节过长 | 核心创新被工程日志遮蔽 | Method 只保留三阶段课程的功能；精确配置移至 Experiments 的 Implementation |
| MAJOR | 干预小节包含较多评测判定语句 | 方法论文第一印象可能偏 protocol paper | Method 定义 intervention；统计量、paired design 和正面判据放 Evaluation Protocol |
| MINOR | `[1024B,256]`、missing-to-zero、三个 elevation products 等实现细节与核心公式混排 | 阅读节奏不稳定 | 状态维度保留，batch flatten 与标准化细节下沉 |
| MINOR | “only nonzero objective”“no second backbone”等防御式表达重复 | 像审计记录而非成熟方法稿 | 正面陈述实际组成，只在可能误解处保留一次边界 |
| MINOR | 课程分段被称作 phase 3，但正文没有前两 phase 的自然定义 | 内部工程命名残留 | 用 early / middle / final training intervals 描述，不出现研发阶段名 |

## 4. TerraState 的修订结构

### 4.1 Problem Formulation

1. 定义部分可观测历史、过去天气、未来天气、静态地理和未来目标。
2. 明确历史上下文 \(\widetilde{\mathcal C}_t\) 不含未来 EO 和未来天气。
3. 用一组同构方程依次写：
   \[
   (b_{1:H},h_t)=q_\theta(\widetilde{\mathcal C}_t),\quad
   z_t=P_\rho(h_t),\quad
   z_{t+h}=T_\psi(z_t,u_{t:t+h},g,h),\quad
   \widehat y_{t+h}=b_h+O_\omega(z_{t+h}).
   \]
4. 用三项操作性条件解释 predictive state：history-derived、
   forcing-advanced、forecast-contributing。

### 4.2 Historical Context and Spatial Predictive State

- **目的：** 从同一历史前向获得 context forecast 与空间状态。
- **机制：** PVT v2/Contextformer history encoder + projector。
- **可验证性质：** 状态贡献可以在保留同一历史上下文时被移除。

### 4.3 Shared Weather-Conditioned Transition

- **目的：** 让未来气象显式决定状态推进，而不是隐藏在 horizon-specific head。
- **机制：** ordered weather encoding + geography + elapsed-time conditioning +
  shared residual transition。
- **可验证性质：** 固定 encoder/readout 时可以只替换天气输入。

### 4.4 Forecast Closure

- **目的：** 让未来状态实际影响最终预测。
- **机制：** state readout 产生 \(r_h\)，与 \(b_h\) 显式相加。
- **可验证性质：** \(s=0\) 精确恢复同模型的 context-only forecast。

### 4.5 Learning a Future-Anchored Predictive State

- 先解释 GT、KD、future-state alignment 各自解决什么；
- 再给三项总损失与 future-state target 公式；
- 最后用一段概括课程，不在 Method 重复所有 optimizer 参数。

### 4.6 Operational Interventions

- 用两个短段定义 state-path intervention 与 weather intervention；
- \(T\!\to\!I\) 明确是辅助干预；
- Q4 仅用一句 optional post-training extension；
- 样本、置信区间与判定逻辑留给 Experiments。

## 5. Claim–evidence 约束

| 方法句 | 类型 | 可写强度 |
|---|---|---|
| 状态来自历史且未来天气只进入 \(T_\psi\) | METHOD FACT | 确定式 |
| \(b_h+r_h\) 允许精确移除状态贡献 | METHOD FACT | 确定式 |
| Future-state target 锚定 transitioned state | METHOD FACT | 确定式 |
| 状态因此已经 load-bearing | RESULT CLAIM | Method 不写通过，Results 用 Q2 证明 |
| 天气替换会改变状态/预测 | TESTABLE PROPERTY | Method 写“allows us to test”；Results 再报告方向与区间 |
| Composition consistency / non-degeneracy | UNSUPPORTED CORE CLAIM | 不写；只保留 optional analysis |

## 6. 退出条件

- 总公式、Figure 1 和正文术语完全一致；
- 每个小节符合“目的 → 机制 → 可验证性质”；
- Method 不重复完整实验协议或工程运行日志；
- 英中稿公式、符号、数字和主张强度一致；
- 编译无 error、overfull、undefined citation/reference；
- 方法节页面连贯，Figure 1 与公式首次出现距离合理。
