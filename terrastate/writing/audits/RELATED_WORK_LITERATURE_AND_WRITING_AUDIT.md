# TerraState Related Work：文献版图与 AAAI 写作审计

> 状态：RESEARCH COMPLETE / REVISION BASIS  
> 日期：2026-07-27  
> 范围：天气驱动 EO 预测、EO world models、predictive states/latent dynamics

## 1. AAAI Related Work 写作锚点

### ReconVLA（AAAI-26）

- 官方链接：https://ojs.aaai.org/index.php/AAAI/article/view/38921
- 组织方式：按“action-centric VLA”和“generative manipulation”两个与方法组件
  直接相关的主题分组。
- 每组写法：共同范式 → 代表工作 → 仍缺少的机制 → 本文区别。
- 对 TerraState 的启示：分类轴应由论文的核心机制决定，而不是按所有可能沾边的
  技术建立小节。

### LLM2CLIP（AAAI-26）

- 官方链接：https://ojs.aaai.org/index.php/AAAI/article/view/37427
- 组织方式：`CLIP meets Stronger Language Models` 与
  `CLIP meets Longer Captions`，分别对应引言中提出的两个挑战。
- 每段结尾明确指出已有工作没有识别或解决的具体问题。
- 对 TerraState 的启示：Related Work 应与引言中的“预测能力不等于内部预测状态”
  缺口一致，不能突然扩展到无关的 EO 表示学习综述。

### WorldAgen（AAAI-26）

- 官方链接：https://ojs.aaai.org/index.php/AAAI/article/view/38925
- 组织方式：VLA、World Models、Test-Time Training 三个直接支撑方法身份的主题。
- 每段只解释一个研究社区以及 WorldAgen 相对它的缺口。
- 对 TerraState 的启示：world model 必须成为 Related Work 的一级边界，而不是
  只在普通 forecasting 段落末尾出现。

### SparseWorld（AAAI-26）

- 官方论文：
  https://ojs.aaai.org/index.php/AAAI/article/view/37347
  （本地审阅文件为 `literature/aaai_figure_anchors/aaai26_sparseworld.pdf`；
  正式题名为 *SparseWorld: A Flexible, Adaptive, and Efficient 4D Occupancy
  World Model Powered by Sparse and Dynamic Queries*。）
- 组织方式：3D occupancy prediction → 4D occupancy world models →
  end-to-end planning。
- 优点：先给类别差异，再把最近方法放入类别，避免逐篇摘要。
- 风险：个别段落只列工作而缺少明确的 `ours differs because` 句。
- 对 TerraState 的启示：保留每段最后一句的明确边界判断。

### Drive-OccWorld（AAAI-25）

- 官方论文：
  https://ojs.aaai.org/index.php/AAAI/article/view/33010
- 组织方式：按输出状态类型区分 2D image world models 与 3D volume world
  models，最后说明本文如何把生成能力接入 planning。
- 对 TerraState 的启示：最有效的分类不是“用了哪种 backbone”，而是“状态如何
  表示、如何转移、如何进入下游闭环”。

## 2. 本地最相关论文

| 工作 | 身份 | 核心方法 | 与 TerraState 的关系 | 必须保持的区别 |
|---|---|---|---|---|
| GreenEarthNet / Contextformer | CVPR 2024 | 多模态高分辨率植被预测 | 任务、数据和历史编码器基础 | 主要建立输出预测；不验证暴露状态是否承载预测 |
| EO-WM | 2026 preprint | 视频扩散、气候态/异常/累积胁迫条件、响应 benchmark | 最近的 EO forcing-response 工作 | 主要在输出层评价天气响应；TerraState 主张显式状态贡献 |
| VegSim | 2026 preprint | NDVI latent state、未来天气递归 rollout、情景模拟 | 最近的 latent vegetation world model | 面向可控情景；TerraState 检验状态是否进入实际预测闭环 |
| Cloud-aware observability WM | 2026 preprint | 预测下一次可用观测及恢复时间 | 同为 EO latent world model | 目标是可观测性，不是地表状态预测 |
| LatentTSF | ICML 2026 | 从 observation regression 转向 latent-state forecasting | 支持“准确输出不保证有序潜状态”的缺口 | 不研究 EO 外生天气，也没有 TerraState 的状态切除与天气对照 |
| World Models / PlaNet / Dreamer | foundational | latent dynamics for prediction/control | world-model 概念基础 | 动作条件控制不同于观测到的外生天气 |
| I-JEPA / V-JEPA | CVPR 2023 / TMLR | 预测未来或遮挡表示 | future-state anchor 的概念背景 | 表示预测本身不能证明状态对最终 forecast load-bearing |
| PLSM | NeurIPS 2024 | 约束控制对潜状态的作用 | driver-conditioned latent dynamics 邻近工作 | 强化学习动作与 EO 天气驱动不同 |

## 3. 2026-07-27 新论文扫描

### 直接相关，当前已覆盖

1. **EO-WM: A Physically Informed World Model for Probabilistic Earth
   Observation Forecasting**（arXiv:2606.27277，2026-06-25）
   - 一手来源：https://arxiv.org/abs/2606.27277
   - 继续作为最接近的 output-level forcing-response 工作。

2. **VegSim: A Geospatial World Model for Scenario-Conditioned Vegetation
   Simulation**（arXiv:2606.21961，2026-06-20）
   - 一手来源：https://arxiv.org/abs/2606.21961
   - 继续作为最接近的 latent vegetation rollout 工作。

3. **From Surface Forecasting to Observability Forecasting: A Latent World
   Model for Cloud-Aware EO Monitoring**（arXiv:2607.13651，2026-07-15）
   - 一手来源：https://arxiv.org/abs/2607.13651
   - 当前参考文献已覆盖；正文只需一句说明任务不同。

### 已审阅但不建议加入正文

1. **Earth-o1: A Grid-free Observation-native Atmospheric World Model**
   （arXiv:2605.06337）
   - 研究大气状态、无网格观测和全球天气预报，不是卫星地表/植被状态预测。
2. **DAWP: Data Assimilation and Weather Prediction in Satellite Observation
   Space**（NeurIPS 2025）
   - 重点是从卫星观测进行全球大气预报，不能帮助界定 TerraState 的内部地表状态
     检验。
3. **Adapting World Models with Latent-State Dynamics Residuals**
   （L4DC 2026）
   - 重点是 simulation-to-real RL 与低数据适应；与外生天气下的地表预测距离较远。

不加入这些论文不是遗漏，而是避免 citation dumping。后续定时扫描只有在新工作直接
改变以下任一边界时才建议进入正文：

- GreenEarthNet 上的显式状态世界模型；
- 同一预测模型中的 state-path ablation；
- 对实际天气和匹配天气控制的 endpoint fidelity；
- 与 TerraState 相同的 history-state-transition-readout 闭环。

## 4. 当前 Related Work 的问题

### MAJOR-1：四个主题的权重不合理

`EO representation learning` 与本文主要 claim 没有一一对应关系，却与
`EO world models and forcing response` 占用同一级标题。它会让读者误以为论文
还主张新的 EO encoder 或 pretraining method。

**决定：删除独立 EO representation learning 段。** 实际历史编码器初始化由
Method 中的 PVT v2/Contextformer 引用说明即可。

### MAJOR-2：第一段仍像模型清单

ConvLSTM、PredRNN、SimVP、Earthformer、MCVD、VegeDiff 和 ViT-Koop 连续出现，
但没有先解释它们为何属于不同范式。

**决定：** 先用 deterministic/multimodal、probabilistic、latent-state transition
三种输出机制组织，再列代表工作。

### MAJOR-3：与 EO-WM/VegSim 的差异需要更精确

当前措辞容易形成“它们只看 output，我们看 state”的过度简化。VegSim 确实有 latent
state，EO-WM 也确实将任务定义为 world modeling。

**决定：**

- 不否定它们的 world-model 身份；
- EO-WM：区别是 physically structured forcing + output response evaluation
  versus explicit state contribution inside the forecast path；
- VegSim：区别是 scenario-conditioned latent rollout versus matched removal of
  the state contribution used by the observed-weather forecast；
- TerraState 只主张补充证据维度，不宣称替代上述工作。

### MINOR-1：Q4 文献权重过高

Deep-OSG 和 group actions 与可逆/代数动作有关，而天气通常有序且不可逆。Q4 已非
核心结果。

**决定：** 只保留一句范围说明，不把 composition 发展成独立主题。

## 5. 推荐的三段结构

### Paragraph 1：Weather-driven EO forecasting

任务来源 → deterministic/multimodal forecasting → probabilistic forecasting →
latent transition → TerraState 对输出精度范式的补充。

### Paragraph 2：EO world models and forcing response

EO-WM → VegSim → observability world model → 三者与 TerraState 的精确差异。
这是最重要的一段。

### Paragraph 3：Predictive states and latent dynamics

PSR/world models → joint-embedding future representations → LatentTSF/PLSM →
TerraState 的 state anchor + forecast-path test → 一句说明 composition 非核心。

## 6. 写作纪律

1. 每段第一句定义研究主题，最后一句给出 TerraState 的差异。
2. 不把预印本写成已录用工作。
3. 不把相邻工作描述成没有 state 或不是 world model。
4. 不把 Q2/Q3 写成新 benchmark。
5. 不因“引用数量”保留与主张无关的 EO pretraining 清单。
6. Related Work 只建立边界；具体损失、结构与实验结果留在后文。
