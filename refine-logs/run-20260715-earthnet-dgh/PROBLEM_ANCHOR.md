# ObsWorld Problem Anchor：EarthNet 家族、DGH 与观测条件分解

> **状态说明：本文件保留问题锚点；成功条件与术语强度已由 [`FINAL_PROPOSAL.md`](FINAL_PROPOSAL.md) 和 [`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) 进一步收紧。**

日期：2026-07-15  
状态：本轮重审锚点；不修改训练代码

## 1. Bottom-line problem

遥感像素不是地表状态本身。它同时包含两类因素：

1. 地表在气象、地理背景和时间作用下真正发生的演化；
2. 传感器、产品、观测几何、太阳条件和有效性等决定“如何看到”的观测过程。

现有 Earth-surface forecasting 方法通常把历史像素、天气、地理信息和时间直接混入同一个预测器，容易把“世界如何变化”和“世界如何被观测”混为一谈。ObsWorld 要解决的核心问题是：**能否学习一个对未来预测足够的地表状态，使观测条件 `phi` 只负责状态推断和观测生成，而 `D/G/h` 只负责状态演化，并让这一状态能够进行可组合、可核验的未来推演。**

## 2. Must-solve bottlenecks

1. `D/G/h` 不能只是条件拼接；必须形成共享、按时间区间推进的受控状态转移。
2. Stage1.5 不能仅凭训练 loss 或旧 probe 宣称“成像解耦”；必须有严格 held-out 的跨观测一致性、正确条件渲染和未来预测效用证据。
3. GreenEarthNet 是固定 Sentinel-2 主任务，不能单独证明任意未来传感器条件的可控渲染；强 `phi` 主张需要单独的配对观测实验。
4. 主实验必须使用 EarthNet 家族的官方划分、掩码和评估器，不能用训练 holdout 或旧 ENS 路径替代。

## 3. Non-goals

- 不声称隐状态是唯一真实物理状态；
- 不声称数学上可识别的完全 disentanglement；
- 不声称完整地球模拟、数字孪生或因果反事实；
- 不把天气输入、DEM、递归或 world model 名称本身当作首创新意；
- 不把未来云真值、目标掩码或事后才知道的产品信息输入模型；
- 首篇不做概率扩散、LLM 或无关分类下游来掩盖核心机制不足。

## 4. Constraints

- 保留 Stage1、Stage1.5、DGH 和 EarthNet 数据管线的已有投入；
- Stage2 及以后允许修改模型和训练策略；
- 当前 Stage2 是 direct endpoint predictor，并非最终 shared rollout；
- 当前 GreenEarthNet Stage2 使用 neutral `phi`，decoder 也不接收 `phi`；
- AAAI-27 正文只有 7 页，关键证据必须进入正文；
- 当前任务只整理思路，不修改训练代码。

## 5. Success condition

以下四项同时成立，才能支撑完整的 ObsWorld 主张：

1. 在 GreenEarthNet/EarthNet2021x 官方 OOD-t 上，ObsWorld 的 100 天预测至少不显著弱于 matched Direct 和 Contextformer，并给出完整 horizon 曲线；
2. shared transition 使用逐区间 D、空间 G 和 `delta_t`，其组合推演相对 direct endpoint 具有竞争力，且 composition consistency 不能靠牺牲真实预测误差获得；
3. 严格配对的观测实验表明：同一状态在正确 `phi` 下比 shuffled/wrong `phi` 更好地生成目标观测，且状态对跨观测预测和 Stage2 未来预测有用；
4. true/no/shuffled/wrong-time D 与 true/shuffled G 的控制排除 calendar、地理记忆和条件忽略等捷径。

若第 3 项无法成立，论文仍可收缩为“acquisition-aware controlled predictive-state world model”，但不得继续强称任意成像条件解耦与 renderer。若第 2 项无法成立，则只能退回强 direct forecaster，世界模型贡献显著减弱。
