# 78b · ObsWorld AAAI-27 摘要（提交即用 · 150–200 词严格版）

> 日期：2026-07-22　用途：**直接粘贴进 AAAI 提交系统的摘要框**。由 [[78_ObsWorld_AAAI27初稿_标题双语摘要与正文骨架_20260722]] §2.1 压缩而来。
> 词数：**≈196 词**（AAAI 常规区间 150–200）。8 句范式与新颖性锚点（观测轴）保持不变；骨架不点名，方案A(ViT-S)/B(PVT-Contextformer) 通用。
> 结果句为**默认档 B（统计持平+机制强）**；换档只替换加粗的倒数第二句（三档见文末）。**G2 SOTA 门未过前禁写 `state of the art`。**

---

## EN — 提交即用（≈196 词）

Most Earth-observation forecasters map past images and weather directly to future pixels, entangling how the land surface **evolves** with how it is **observed** under specific product and acquisition conditions. Concurrent EO world models capture the first—weather-driven vegetation dynamics—but operate on derived products and leave observation formation implicit. We introduce **ObsWorld**, an **observation-aware predictive-state world model** that separates state inference, exogenous-driver dynamics, and conditional observation formation. ObsWorld infers a shared land-surface state, evolves it under future weather and geography through one short-horizon transition applied both **directly and compositionally**, renders observations under an explicit condition, and reads future events from the same **frozen** state. We make the state observation-aware with **paired Sentinel-2 products (L1C/L2A)**, so product-dependent appearance is explained by the rendering condition rather than absorbed into the state. Trained end to end on a strong vegetation-forecasting backbone, the same state is evaluated across GreenEarthNet forecasting, cross-product rendering, latent-future consistency, and frozen event readout. **On GreenEarthNet, ObsWorld matches a strong baseline while adding cross-product observation control, better latent consistency, and reusable future-state readouts that pixel forecasters lack.** These results establish observation-aware predictive states as a practical interface between accurate Earth-surface forecasting and reusable EO world models.

---

## 中文对照（同步压缩版，如需双语提交）

多数地球观测预测器把历史影像与天气直接映射到未来像素，将地表如何**演化**与其在特定产品/采集条件下如何**被观测**纠缠在一起。同期地球观测世界模型刻画了前者——天气驱动的植被动力学——但都工作在派生产品上、把观测形成留作隐式。我们提出 **ObsWorld**，一个**观测感知的预测状态世界模型**，分离状态推断、外生驱动动力学与条件化观测形成。ObsWorld 从观测推断共享地表状态，在未来天气与地理下用同一个短步转移（**direct 与 composed 两路**）推进它，在显式观测条件下渲染观测，并从同一个**冻结**状态读出未来事件。我们用**配对 Sentinel-2 产品（L1C/L2A）**使状态观测感知，让产品相关外观由渲染条件解释、而非混入状态。在强植被预测骨架上端到端训练，同一状态通过 GreenEarthNet 预测、跨产品渲染、latent-future 一致性与冻结事件读出共同评价。**在 GreenEarthNet 上，ObsWorld 与强基线持平，同时提供纯像素预测器不具备的跨产品观测控制、更优 latent 一致性与可复用未来状态读出。** 这些结果把观测感知预测状态确立为准确地表预测与可复用地球观测世界模型之间的实用接口。

---

## 结果句三档（只替换 EN 加粗那句 / 中文对应句）

- **档 A（SOTA 通过，G2 门过后才可写）**：*On the official GreenEarthNet protocol, ObsWorld establishes a new state of the art, improving a matched strong baseline from [x] to [y] in R² and from [x] to [y] in RMSE across three seeds, while cross-product and state-utility experiments confirm the observation factorization.*
- **档 B（默认，统计持平+机制强）**：见上 EN 正文加粗句。
- **档 C（有竞争力但未过强基线，不写 SOTA）**：*On GreenEarthNet, ObsWorld substantially improves our predictive-state backbone and remains competitive; its primary gains lie in observation factorization and reusable future states.*

---

## 相较 §2.1 长版的压缩点（可追溯）
1. **删背景铺垫句**（原 S1 "Satellite image time series are the primary record…"）→ 直接从"直接映射的问题"起句。
2. **S1 并句**："treating the image as the surface" 融入 "entangling …"，省 product/processing/acquisition 三联为 "product and acquisition"。
3. **S6 评测句**由 "Built on … and optimized end to end, the same predictive state is evaluated through standard GreenEarthNet forecasting, cross-product rendering, multi-step latent consistency, and a frozen future-event readout." 压为 "Trained end to end on … evaluated across …"。
4. 方法四接口句(S4)、观测监督句(S5)、结果句、回扣句**未压缩**——它们承载新颖性与识别边界，保原样。
