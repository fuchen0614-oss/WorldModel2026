# TerraState 新近文献扫描（2026-07-27）

## 1. 扫描目的

本轮不是为增加引用数量，而是检查 2026 年近期论文是否改变 TerraState 的问题边界：

> 对天气驱动 EO 预测而言，输出准确并不足以说明模型内部形成了一个实际参与预测、
> 且会响应所提供未来天气的预测状态。

检索优先使用 arXiv 论文页、AAAI Proceedings 和 CVF 官方论文页。判断标准是论文
是否同时接近以下至少两项：EO/地表预测、显式潜状态、未来天气驱动、状态进入预测
闭环、对状态或驱动进行匹配干预。

## 2. 直接相关且已经覆盖

### EO-WM

- 论文：*EO-WM: A Physically Informed World Model for Probabilistic Earth
  Observation Forecasting*
- 一手来源：https://arxiv.org/abs/2606.27277
- 关系：同样把 EO 预测界定为部分可观测、天气驱动的世界建模，并评估输出层天气
  响应；它是 TerraState 当前最接近的外部边界之一。
- 决策：已经在 Related Work 中引用。继续把差异限定为“TerraState 进一步检验
  显式状态贡献”，不贬低 EO-WM 的概率预测和天气响应贡献。

### VegSim

- 论文：*VegSim: A Geospatial World Model for Scenario-Conditioned Vegetation
  Simulation*
- 一手来源：https://arxiv.org/abs/2606.21961
- 关系：从稀疏 NDVI 历史、过去气象和静态信息推断潜在植被状态，再在未来天气下
  递归推进并解码 NDVI 分位数。
- 决策：已经引用。TerraState 的边界保持为“状态贡献可被移除、真实天气和匹配
  对照在同一模型上比较”，而不是声称首先使用天气驱动潜状态。

### Cloud-aware observability forecasting

- 论文：*From Surface Forecasting to Observability Forecasting: A Latent World
  Model for Cloud-Aware EO Monitoring*
- 一手来源：https://arxiv.org/abs/2607.13651
- 关系：使用潜世界模型和天气驱动，但预测目标是下一次观测是否可用以及何时恢复，
  并非地表状态。
- 决策：已经以“不同预测目标”在 Related Work 中引用；它不改变 TerraState 的
  novelty 表述。

## 3. 新扫描但不建议加入正文

### OCELOT

- 论文：*OCELOT: Direct Atmospheric Forecasting from Heterogeneous Earth
  Observations Using a Graph-Transformer Hybrid Model*
- 一手来源：https://arxiv.org/abs/2607.14196
- 关系：直接从异构观测预测大气变量，包含共享潜在网格和观测空间输出。
- 不加入原因：研究对象是全球短期大气预测，不检验天气条件下的地表预测状态贡献；
  加入会把 Related Work 从 land-surface EO forecasting 拉向天气预报基础模型。

### Earth-o1

- 论文：*Earth-o1: A Grid-free Observation-native Atmospheric World Model*
- 一手来源：https://arxiv.org/abs/2605.06337
- 关系：强调观测原生、无网格的大气世界模型。
- 不加入原因：它界定的是大气状态演化与跨传感器预测，不承担 TerraState 所研究的
  状态切除或外生天气替换问题。

### AAAI-26 latent/world-model papers

- *MrCoM: A Meta-Regularized World-Model Generalizing Across Multi-Scenarios*：
  https://ojs.aaai.org/index.php/AAAI/article/view/39933
- *Decoupled Spatiotemporal Forecasting from Extreme Sparse Observations via
  Quantized Latent Space*：
  https://ojs.aaai.org/index.php/AAAI/article/view/39897
- 判断：前者服务多场景强化学习世界模型泛化，后者服务稀疏物理场重建与外推。
  二者可作为写作和方法图的层级参考，但不是 TerraState 的最近工作，不应机械加入
  Related Work。

## 4. 对当前正文的影响

- 没有发现需要改变标题、摘要主线、Q1--Q3 证据链或 TerraState 方法定义的新论文。
- 现有三段 Related Work 边界仍合理：
  weather-driven EO forecasting → EO world models and forcing response →
  predictive states and latent dynamics。
- 本轮不新增 BibTeX 条目。当前 24 个条目全部在正文使用，避免 citation dumping。
- 后续定期扫描应优先关注：
  1. GreenEarthNet/EarthNet 上的新 world-model 论文；
  2. 对未来天气进行 matched intervention 的 EO 工作；
  3. 明确检验 latent state 是否进入预测路径的工作；
  4. EO-WM、VegSim 与 observability preprint 的正式录用或元数据更新。

