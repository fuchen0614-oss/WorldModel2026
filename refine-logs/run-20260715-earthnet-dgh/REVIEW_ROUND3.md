# Independent Reverse Review — Round 3

日期：2026-07-15  
原判定：REVISE，8.5/10，接近 GO  
原路线保留度：约 89%

## 独立复审的保留度判断

| 内容 | 保留度 |
|---|---:|
| EarthNet 主线 | 95% |
| DGH | 95% |
| Stage1/1.5 已有投入 | 85% |
| 状态推断—状态演化—观测生成三柱 | 90% |
| EO world model / 模拟真实世界母叙事 | 90% |

## 本轮必须修改的问题

1. L1C/L2A product Gate 需要明确一个 shared decoder 与 target-product token，并预注册 `self only / self+cross / w/o target condition / full` 消融。
2. partition loss 中的 `P` 不能是会自行塌缩的可学习 projector；应使用固定非 affine LayerNorm 或冻结投影。
3. 公开 Contextformer 使用的是每五日 24-D E-OBS（8 variables × mean/min/max）；主表必须对齐，raw daily 可作附录。
4. 自有方法必须同时有三种子和 tile/location-cluster paired CI，不能二选一。
5. non-inferiority margin 和 stop inequalities 需在看到 ObsWorld locked-OOD 结果之前冻结。
6. matched Direct 和 ObsWorld 应使用相同 `E_D` 架构，总参数量差异不超过 10%。
7. 还需要一次针对最接近方法的正式查新，判断“两轴一致性”能否作为安全新意。

## 已落实的修改

- 主 D 接口改为公开协议的 24-D/5-day token，5/10/20 日共享变长 `E_D`；
- `P(s)` 固定为 `LayerNorm(elementwise_affine=False)`；
- product Gate 改为 shared decoder + target-product token，且固定 source state 仅替换 token；
- 三种子 **AND** clustered paired CI 写入 protocol；
- 参数差 <=10%、相同 `E_D`、结果无关 margin 与形式化 stop inequalities 写入计划；
- 将普通 semigroup 描述改为非自治驱动下的 control-aware partition/evolution consistency。

## 审查后的统一表述

> **The predictive state is constrained across observation products by cross-observation decoding and across temporal partitions by control-aware partition-consistent transitions.**

中文：

> **ObsWorld 的预测状态同时受两条轴约束：在产品轴上由跨观测解码约束，在时间轴上由控制感知的分割一致转移约束。**

