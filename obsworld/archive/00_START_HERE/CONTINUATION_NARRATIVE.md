# 可继续发展的初始研究叙事

## 值得保留的核心问题

遥感观测同时包含地表状态和成像条件。仅用重建训练得到的 latent token 可能混合两者，因而不宜直接把普通 observation feature 命名为 world state。

Stage 1 → 1.5 的最有价值主线是：

> 先学习能读取多模态遥感观测的空间表示，再显式给出成像条件，使模型通过一个受约束的状态瓶颈解释观测；随后检验该状态保留了什么、排除了什么，以及它是否对后续动力学预测有用。

## 当前方法故事

1. Stage 1 用 S1/S2 masked reconstruction 学习观测结构。
2. Stage 1.5 将 acquisition condition \(\phi\) 作为观测形成因素显式输入。
3. 近同期 S1/S2 alignment 鼓励同一地表在两种传感器下形成一致状态。
4. state projector 与 reconstruction bridge 强制重建经过显式状态瓶颈。
5. nonlinear probe 检查模型是否仍把成像因素编码进 state。

## 当前证据允许的表述

Stage 1.5 改善跨模态一致性并保持重建能力，但只抑制了所采用正则能看见的线性泄漏；非线性成像信息仍然存在。因此，更准确的身份是“受 acquisition conditioning 与跨模态约束的候选地表状态”，而不是“已经完全成像不变的物理状态”。

## 后续可验证方向

这些是研究计划，不是已完成主张：

- 用 adversarial nuisance predictor 或更直接的条件独立目标处理非线性泄漏；
- 把 probe 设为训练外固定评估，而不是仅监控训练内 nuisance loss；
- 分别验证状态的重建充分性、跨模态一致性、成像条件泄漏和下游动力学价值；
- 用 state-path removal 检验状态是否真正参与后续预测；
- 比较“更强解耦”是否真的改善动态预测，避免把解耦本身当成最终目标。

## 不应恢复的旧叙事

- 仅凭架构命名就宣称 world state；
- 仅凭低 cross-covariance 就宣称完整 disentanglement；
- 把更多训练步数等同于更少非线性泄漏；
- 把 Stage 1.5 的负 probe 结果隐藏掉；
- 在没有干预证据时声称状态是 load-bearing。

