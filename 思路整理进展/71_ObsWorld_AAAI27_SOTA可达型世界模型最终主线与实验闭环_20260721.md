---
title: ObsWorld AAAI-27 SOTA可达型世界模型最终主线与实验闭环
aliases:
  - ObsWorld SOTA-Reachable World Model Decision
  - ObsWorld 世界模型与SOTA主线冻结
tags:
  - ObsWorld
  - AAAI27
  - WorldModel
  - GreenEarthNet
  - SSL4EO
  - PredictiveState
  - MainTable
created: 2026-07-21
updated: 2026-07-21
status: 战略冻结稿；已核对现有结果与关键代码路径；新主线实验尚未执行
evidence_scope:
  - GreenEarthNet OOD-t Direct-P4与Rollout-P4修正后结果
  - EarthNet2021 IID/OOD官方ENS本地评测
  - Stage1 EuroSAT线性探针与Stage1.5训练/探针审计
  - Stage2 neutral-phi、S2-only与Stage1.5初始化代码路径
  - Contextformer公开协议、结果、代码和权重通道
decision_scope:
  - 在“必须争取可达SOTA并保留世界模型定位”的硬约束下重定论文
  - 不采用U、隐藏区域传输或多任务大拼盘作为最低生存路线
---

# 71. ObsWorld AAAI-27：SOTA 可达型世界模型最终主线与实验闭环

> [!important] 本文件回答什么
> 本文件专门回答一个新的硬约束问题：**如果论文必须保留 world model 定位，同时主表必须有现实机会达到 GreenEarthNet SOTA，那么 ObsWorld 应该保留什么、删除什么、重建什么，以及 Stage1/1.5、SSL4EO、S1、`phi`、Stage2、下游任务和大模型分别承担什么证据责任。**
>
> 本文档不是对 [[69_ObsWorld_AAAI27破局终版_复访自适应世界模型叙事实验与工程总纲_20260721]] 或 [[70_ObsWorld_AAAI27中心叙事与主表最终冻结决策_20260721]] 的延伸，也不采用其中更激进的 Rollout-R+、SIT-U、隐藏区域传输或 continual correction 主线。在本文件的硬约束下，旧 `70` 的证据审计仍可引用，但主方法决策由本文件替代。

> [!warning] 最先说清楚的边界
> 没有任何实验设计能够预先保证 SOTA。本文给出的是**目前成功概率最高、归因最干净、即使最终只达到强竞争水平也不需要改变摘要主线**的方案。只有在同协议正式结果超过公开和本地强基线后，才能在摘要与正文写 `state of the art`。

---

# 0. 一页最终决策

## 0.1 唯一推荐路线

> **以官方 Contextformer 为预测精度底座，把 ObsWorld 重构为一个 observation-aware predictive-state world model：从配对观测中学习产品条件不变的地表预测状态，在天气等外生驱动下推进该状态，再由观测条件将状态渲染为未来观测，并证明同一个预测状态可以支持未来植被事件判断。**

这条路线由两个锚点组成：

| 锚点 | 作用 | 最低证据 |
|---|---|---|
| **精度锚点** | 让主表真正够得到 SOTA | 官方 Contextformer 本地复现 + 同初始化、同预算的 ObsWorld 扩展 + 3 seeds |
| **世界模型锚点** | 防止论文退化成单数据集预测器 | 状态-观测因子化 + 外生驱动转移 + 多步状态一致性 + 冻结状态复用 |

最终组件决策如下：

| 现有内容 | 最终处理 | 原因 |
|---|---|---|
| 当前 Direct-P4 / Rollout-P4 | 保留为失败诊断与历史对照，不继续作为 SOTA 主骨架 | 与 Contextformer 差距过大，继续小修成功率低 |
| Contextformer | 作为强预测骨架和本地精度下限 | 已公开达到 `R²=0.62 / RMSE=0.14`，代码和权重可得 |
| Stage1 / Stage1.5 | 在论文中合并为“观测因子化预训练”，按目标骨架重做最小版本 | 现有两阶段名称是工程历史，当前证据无法支撑两个独立贡献 |
| SSL4EO | 保留，但只用于 S2 配对产品的观测因子化 | 它拥有 GreenEarthNet 缺少的配对观测监督 |
| S1 | 从主方法删除 | Stage2 不使用 S1，且缺少同预算下游收益及严格时间配对证据 |
| `phi` | 保留并收缩为“观测产品/处理条件” | 必须在配对 L1C/L2A 交叉渲染中真实使用；GreenEarthNet 中因目标协议固定而取常量 |
| `07` 的多下游任务 | 不恢复任务动物园；只恢复一个同域状态复用任务 | 一个状态的正交复用比多个互不相干的数据集更能证明世界模型 |
| 大模型 + ours | 作为可选 `2x2` 容量归因实验 | 不能用“更大模型”替代方法证据 |
| U / 隐藏区域传输 | 不进入标题、摘要、主表或最低闭环 | 与本次 SOTA + observation-aware world model 主线正交，风险过高 |

## 0.2 推荐标题与中心句

推荐标题：

> **ObsWorld: An Observation-Aware Predictive-State World Model for Land-Surface Forecasting**

中文：

> **ObsWorld：面向地表预测的观测感知预测状态世界模型**

中心句：

> **Earth-observation forecasting should model how the land surface evolves separately from how that state is observed. ObsWorld learns an observation-aware predictive state, evolves it under exogenous drivers, and renders or reuses the same state for future observation and environmental-event prediction.**

## 0.3 为什么这条主线能够长期不变

这条主线不把论文全部押在一个小数点胜负上。最终结果可以在以下范围内变化，而问题和方法不需要变化：

- 若正式超过 Contextformer：写“达到新的 GreenEarthNet SOTA，并同时获得观测因子化和状态复用能力”。
- 若与 Contextformer 统计持平：写“保持强 SOTA 级预测能力，同时加入普通预测器不具备的状态-观测分解与复用”。
- 若略低于 Contextformer但显著超过当前模型：不能写 SOTA，但仍可写“强竞争预测 + 世界模型机制”；是否投稿取决于世界模型实验强度。
- 若既没有强预测，也没有状态因子化或复用收益：论文不成立，应止损，而不是再次改摘要主线。

---

# 1. 当前证据的冷静审计

## 1.1 当前主模型不是 SOTA 的近邻

GreenEarthNet OOD-t 修正后、同一本地 manifest 上的结果为：

| 方法 | R² ↑ | RMSE ↓ | NSE ↑ | 绝对Bias ↓ | RMSE25 ↓ | 证据状态 |
|---|---:|---:|---:|---:|---:|---|
| Published Contextformer | **0.62** | **0.14** | **0.09** | **0.09** | **0.08** | CVPR 2024公开值 |
| Direct-P4 | 0.524 | 0.178 | -0.415 | 0.126 | 0.126 | 本地单seed provisional |
| Rollout-P4 | 0.504 | 0.184 | -0.476 | 0.131 | 0.128 | 本地单seed provisional |

直接结论：

1. Direct 相对 Contextformer 的 R² 差约 `0.096`，RMSE 高约 `0.038`。
2. Rollout 在 GreenEarthNet 指标上进一步退化，且误差劣势随预测时距扩大。
3. 当前模型参数约 28M，而公开 Contextformer 约 6.1M；更大参数量没有换来更强精度。
4. 这不是换一个 loss、加一个小模块或延长少量训练就能高概率抹平的差距。
5. 如果 SOTA 是硬要求，继续把当前 Stage2 当主骨架属于低成功概率决策。

## 1.2 EarthNetScore 也没有提供可转移的 SOTA 证据

当前本地正式可解释的 IID/OOD ENS 为：

| 模型 | IID ENS ↑ | OOD ENS ↑ |
|---|---:|---:|
| Direct-P4 | 0.1410 | 0.1157 |
| Rollout-P4 | **0.1500** | **0.1231** |
| Published Persistence参考 | 0.2625 | 0.2587 |

这里必须保持协议纪律：EarthNet2021 ENS 与 GreenEarthNet 的 R²/RMSE 不能混表。Extreme/Seasonal 的本地代码采用 `10 -> 20` 截断，而官方轨道分别为 `20 -> 40` 与 `70 -> 140`，因此不能作为官方轨道结果。详见 [[69_ObsWorld_官方EarthNetScore对标_published_vs_ours_20260722]] 的勘误部分。

ENS 上 Rollout 略高于 Direct，只能说明两种预测在某些结构分量上的排序不同，不能弥补绝对值远低于公开 Persistence 的事实，也不能支撑“Rollout 是 SOTA 世界模型”。

## 1.3 Stage1/1.5 与 Stage2 的真实连接状态

当前链条不是完全没有连接，但**功能性连接不足**：

| 问题 | 已核对事实 | 论文含义 |
|---|---|---|
| Stage1质量 | 95k ViT-S EuroSAT frozen linear probe 为 `76.15%`，公开 MAE ViT-S 参考为 `94.1%` | 不能声称强 foundation representation |
| Stage1.5训练 | alignment和重建训练指标改善 | 只能证明训练目标下降，不能单独证明解耦 |
| 历史`phi`探针 | 后续审计发现 `phi` 路径、state projector、token处理和空间切分问题 | 旧探针不能作为正式论文证据 |
| 权重传递 | Stage2-v2 配置要求并加载 Stage1.5 的 encoder、`phi_encoder`、state projector | 不能说 Stage1.5 权重完全没用 |
| Stage2中的`phi` | `data/earthnet_fields.py` 构造 neutral S2 `phi`；注释明确 dynamics 不消费真实`phi` | 不能声称 Stage2 acquisition-aware |
| Stage2中的S1 | `models/dynamics/obsworld_core.py` 冻结 S1 patch projection 和 S1 modality embedding；前向只走`"S2"` | 不能声称 Stage2 使用多模态 S1/S2 |
| 下游归因 | 没有 scratch、Stage1-init、Stage1.5-init 的同预算 Stage2 消融 | 无法证明现有预训练对预测精度的贡献 |

最准确的表述是：

> 当前 Stage2 **加载了** Stage1.5 的共享编码器相关权重，但只在 S2 + neutral `phi` 条件下使用；S1 专属分支和真实成像条件功能没有进入下游，且缺少匹配初始化消融。因此存在参数继承，但尚不存在足以支撑论文主张的功能闭环。

## 1.4 “没有从头训练”不是核心错误

审稿人通常不会因为模型使用公开预训练而否定端到端方法。Contextformer 自身也使用 ImageNet 预训练的 PVT-v2。真正需要回答的是：

1. 预训练为什么与论文问题有关？
2. 预训练权重是否实际进入最终模型？
3. 最终任务是否对全部有效模块做端到端优化？
4. 额外数据和额外训练是否对基线公平？
5. 匹配消融能否证明收益来自方法，而不是更多数据或更多训练？

因此最终方案允许 SSL4EO 预训练，但 GreenEarthNet 阶段必须对所有有效模块进行全量端到端微调，并让 baseline 与 ours 获得相同初始化和额外训练预算。

---

# 2. 为什么只剩一个跑分会削弱 world model，但恢复所有 `07` 任务也不正确

## 2.1 单一平均指标的问题

只在 GreenEarthNet 报一个 R²/RMSE 表，可以证明模型会预测植被，但不能自动证明以下性质：

- latent 是对未来充分的状态，而不是普通隐藏特征；
- 状态在天气驱动下具有可组合的演化规律；
- 状态与产品/处理造成的观测差异被分开；
- 同一个状态能被另一个任务头复用；
- 模型能支持条件替换、干预或多步模拟。

所以把 `07` 的广泛设计全部砍成单数据集单跑分，确实削弱了 world model 叙事。但问题不在“数据集数量少”，而在“世界模型的关键契约没有被独立检验”。

## 2.2 多任务大拼盘的问题

恢复洪水、建筑变化、灾害损伤、土地覆盖、作物和多模态生成的整套 `07` 方案，会带来四个风险：

1. 每个数据集的时间、空间、模态和标签协议不同，七页正文无法讲清。
2. 每个任务都需要专门数据处理和强专家基线，工程成本远超剩余时间。
3. 多个微弱结果不会合成为一个强贡献，反而容易被认为是任务拼盘。
4. 任务专用微调可能证明模型容量，而不是证明同一个世界状态可复用。

最优折中不是“一项跑分”和“全部任务”二选一，而是三类证据各做一个最小闭环：

| 证据类别 | 数据 | 回答的问题 |
|---|---|---|
| 标准预测SOTA | GreenEarthNet | 这个方法是否至少是强预测器？ |
| 观测因子化 | SSL4EO-S2 L1C/L2A配对 | 模型是否把状态与产品观测过程分开？ |
| 状态复用 | GreenEarthNet派生的未来植被衰退事件 | 同一状态是否支持像素误差之外的任务？ |

这已经足以形成一篇聚焦的 AAAI 论文；外部洪水或建筑数据可作为后续扩展，而不是当前摘要承诺。

---

# 3. 最终科学问题与世界模型定义

## 3.1 问题定义

遥感影像不是地表状态本身。相同地表状态在不同产品级别、传感器处理、时间和有效观测条件下可以产生不同像素；反过来，相同像素差异也可能来自真实地表变化或观测过程变化。

论文只回答一个问题：

> **能否学习一个对未来预测充分、对观测产品变化稳定的地表状态，使它在天气等外生驱动下演化，并通过指定的观测条件生成未来观测或支持任务读出？**

## 3.2 最小生成与预测结构

设历史观测为 `X_<=t`，观测条件为 `phi_<=t`，质量掩膜为 `M_<=t`，未来外生驱动为 `D_t:t+h`，静态地理条件为 `G`：

```text
State inference:
z_t = q(X_<=t, phi_<=t, M_<=t)

Controlled evolution:
z_{t+h} = T(z_t, D_t:t+h, G, h)

Observation formation:
X_hat_{t+h} = O(z_{t+h}, phi_{t+h})

State utility:
y_hat_{t+h} = H(z_{t+h})
```

对应概率分解：

```text
p(X_{t+h} | X_<=t, D, G, phi_{t+h})
= integral p_O(X_{t+h} | z_{t+h}, phi_{t+h})
           p_T(z_{t+h} | z_t, D, G, h)
           q(z_t | X_<=t, phi_<=t, M_<=t) dz
```

## 3.3 为什么它可以叫 world model

本文不使用强化学习式 action，但地球系统由天气等外生 forcing 推进。一个合格的外生驱动 EO world model 至少需要四个可检验接口：

| 接口 | 必须成立的性质 | 对应实验 |
|---|---|---|
| `q` 状态推断 | 配对观测产生相近状态，状态保留地表语义 | L1C/L2A state consistency、语义probe |
| `T` 受控动力学 | 状态能够多步推进并响应真实驱动 | latent future consistency、null/wrong weather |
| `O` 观测形成 | 固定状态、更换`phi`可生成指定产品 | 四向cross-rendering、no-`phi`消融 |
| `H` 状态复用 | 冻结状态可支持未来事件读出 | vegetation-decline onset/severity probe |

只有预测分数而没有后三项，最多是 forecaster；只有重建和分类而没有 `T`，最多是 representation model。四项共同成立时，world model 定位才完整。

## 3.4 理论支持应写到什么程度

理论部分应建立**预测状态形式化与可检验推论**，不应伪造不可证明的“恢复真实物理状态”定理。

建议采用三条假设：

1. **预测充分性**：给定 `z_t`、未来驱动和未来观测条件后，未来观测与更早历史条件独立。
2. **受控 Markov 性**：给定 `z_t` 和未来驱动后，未来状态不再依赖完整历史。
3. **观测形成条件性**：产品差异由 `phi` 进入 `O`，而不需要写入状态动力学。

由此得到三个实验推论：

1. 同一地表的配对产品经 `q` 后应比原始像素更接近。
2. `O(q(X^a), phi_b)` 应能重建配对产品 `X^b`。
3. `T(z_t,D)` 应接近真实未来观测编码得到的 `q(X_{t+h})`。

必须同时声明识别边界：paired reconstruction 和 latent consistency 只能说明存在一个满足预测与观测契约的表示，**不能证明它等于唯一、完整的真实物理状态**；`z` 最安全的名称是 `predictive land-surface state`。

---

# 4. 最终方法架构：在强基线上增加可归因的世界状态

## 4.1 为什么从 Contextformer 出发

Contextformer 已经包含主任务需要的强归纳偏置：

- 云与有效观测处理；
- 空间上下文建模；
- 气象条件输入；
- 从最后一个无云 NDVI 做 delta prediction；
- 在 GreenEarthNet 上完整端到端训练；
- 约 6.1M 参数即可达到公开 `R²=0.62 / RMSE=0.14`。

公开更大版本并未带来相应 R² 改善，因此“单纯扩大模型”不是最优突破口。ObsWorld 应保留上述强预测结构，只改造 latent 的训练契约和可复用接口。

官方资源：

- 代码：<https://github.com/vitusbenson/greenearthnet>
- 权重：<https://zenodo.org/records/10793870/files/model_weights.zip>
- 论文：<https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html>

## 4.2 强基线可恢复原则

新架构必须满足：当新增 loss 权重为零、附加状态头关闭时，模型退化为本地复现的 Contextformer。这样做有三个作用：

1. 防止新 bottleneck 直接破坏强预测能力。
2. 所有增益都能通过逐项消融归因。
3. 即使新机制训练早期不稳定，也保留公开强基线作为回退点。

不建议把当前 256维 Stage2 状态瓶颈生硬插到 Contextformer 主路径并完全替换其输出。更稳的做法是把 Contextformer 的时空特征显式定义为 `z`，增加状态投影、latent transition consistency 和观测条件 renderer，同时保留原有 NDVI residual head。

## 4.3 两个观测出口

最终模型允许同一状态有两个严格分工的出口：

| 出口 | 数据与目标 | 作用 |
|---|---|---|
| `O_product(z, phi)` | SSL4EO 的 S2 L1C/L2A 四个公共波段 | 验证状态-观测产品因子化 |
| `O_ndvi(z, phi_GEN)` | GreenEarthNet 的标准未来植被目标 | 参加官方预测主表 |

在 GreenEarthNet 中，目标产品和处理协议固定，因此 `phi_GEN` 是固定条件，不需要伪造不存在的逐帧 acquisition metadata。`phi` 的价值由 SSL4EO 配对观测实验验证，而不是期待它在固定产品 benchmark 中自行产生变化。

## 4.4 训练目标

建议总目标为：

```text
L_total = L_GEN
        + lambda_dyn   * L_latent_future
        + lambda_pair  * L_paired_state
        + lambda_cross * L_cross_render
        + lambda_reg   * L_state_regularization
```

各项含义：

```text
L_GEN:
    官方 GreenEarthNet 预测损失，保持 Contextformer 的强精度目标。

L_latent_future:
    distance(T(z_t, D, G, h), stopgrad(q(X_{t+h}, phi_{t+h})))
    直接把 latent transition 与真实未来状态编码对齐。

L_paired_state:
    distance(q(X_L1C, phi_L1C), q(X_L2A, phi_L2A))
    约束同一地表的配对产品共享状态。

L_cross_render:
    O(q(X_a, phi_a), phi_b) -> X_b, a,b in {L1C,L2A}
    验证目标产品由 phi 控制，而不是由 z 偷带产品标签。

L_state_regularization:
    防止状态坍塌并保持空间/语义信息，可使用variance-covariance或轻量语义辅助。
```

`L_latent_future` 是把“隐藏特征”升级为“预测状态”的关键；`L_cross_render` 是把 `phi` 从装饰变量升级为“观测形成条件”的关键。

## 4.5 三个训练阶段，但论文只讲两个概念阶段

工程上可以有三次训练，论文叙事只保留 observation pretraining 和 dynamics learning 两个概念：

| 工程阶段 | 训练内容 | 论文名称 | 权重去向 |
|---|---|---|---|
| A | SSL4EO-S2 L1C/L2A配对因子化 | Observation-factorized pretraining | `q`和`O_product`进入下一阶段 |
| B | GreenEarthNet全量端到端预测与latent consistency | Controlled predictive-state learning | 形成主模型checkpoint |
| C | 冻结`q/T`，训练浅层事件头 | Frozen state readout evaluation | 只用于证明状态复用，不改主模型 |

现有 Stage1 和 Stage1.5 在论文中不再分别编号。它们是历史上从 MAE 到条件化训练的工程演进，不是两个需要审稿人分别接受的科学贡献。

## 4.6 当前 Stage1 权重如何处理

现有 Stage1/1.5 是 12波段 ViT-S/FILM 路径，Contextformer 使用 PVT-v2 类骨架，不能为了“保住已做工作”而强行拼接不兼容权重。优先选择是：

1. 用最终目标骨架的 encoder，在 SSL4EO 的 `B02/B03/B04/B8A` 四个公共波段上重做最小配对预训练。
2. 输入波段、归一化、空间尺寸和 Stage B 保持一致，保证 checkpoint 可直接加载。
3. 现有 Stage1/1.5 checkpoint 作为历史对照或可选初始化消融，不作为最终方法必须依赖。
4. 如果时间不足以重做兼容预训练，宁可从主方法删除 SSL4EO，也不能让不兼容或无收益的旧 checkpoint 成为叙事承重墙。

---

# 5. SSL4EO、Stage1/1.5、S1 与 `phi` 的最终答辩口径

## 5.1 为什么 Stage1/1.5 使用 SSL4EO？

最好的回答不是“SSL4EO 数据大”或“遥感预训练通常都用它”，而是：

> **GreenEarthNet 主要提供固定产品协议下的时间演化监督，难以单独区分真实状态变化与观测产品变化。SSL4EO 提供同地点、相匹配的 S2 L1C/L2A 观测，使我们能够学习共享状态与产品条件化观测模型。因此 SSL4EO 解决 observation identifiability 问题，GreenEarthNet 解决 dynamics learning 问题，两者监督互补而非随意拼接。**

这个回答成立需要三个前提：

1. 使用严格配对的 S2 L1C/L2A 样本，并在 manifest 中记录 acquisition/time pairing。
2. Stage A 与 Stage B 使用兼容的 encoder 和公共波段，预训练权重真实进入最终模型。
3. 用 `scratch vs paired-pretrain` 的同预算消融证明这一步至少改善因子化、鲁棒性或最终预测中的一项。

如果做不到这三点，SSL4EO 就只是额外数据，审稿人的质疑成立。

## 5.2 Stage1 和 Stage1.5 在文章中是什么地位？

最终文章不再使用“Stage1 是通用基础模型、Stage1.5 是完全去耦模型”的说法。统一改写为：

> **Before learning dynamics, we pretrain the observation interface on paired Sentinel-2 products so that a shared predictive state can be rendered under an explicit product condition.**

也就是说：

- Stage1 的 MAE 是初始化手段，不是贡献。
- Stage1.5 的条件化思想被吸收到 observation-factorized pretraining 中。
- 现有训练内 reconstruction/alignment 下降是开发证据，不进入主要结果。
- 历史无效 `phi` probe 不进入正文、附录或 rebuttal。
- 论文不需要向审稿人解释“为什么有 1.5”，因为 1.5 是工程版本号，不是科学阶段。

## 5.3 `phi` 到底是什么，为什么 Stage2 看不到变化？

最终将 `phi` 收缩定义为：

> **描述目标观测如何形成的已知条件，最低版本只包含 S2 product level，即 L1C 或 L2A；只有经过有效性审计的太阳角、时间或质量字段才可继续加入。**

`phi` 不属于地表状态，也不应成为动力学输入。它只进入状态反演和观测 renderer：

```text
z = q(X, phi)              # 利用phi反演共享状态
X_target = O(z, phi_target) # 利用目标phi生成指定产品
z_future = T(z, weather)    # dynamics不消费产品标签
```

GreenEarthNet 的目标产品协议固定，所以 `phi_GEN` 固定是合理的，类似一个 decoder domain token。这里不能声称模型在 GreenEarthNet 中动态利用太阳角或 SAR 几何。`phi` 的必要性必须由 SSL4EO 上的 `w/o phi` 和 cross-rendering 结果体现。

## 5.4 S1 为什么加入过，现在为什么建议删除？

历史上加入 S1 有合理动机：SAR 在云下可用，并可能提供结构和水分信息；S1/S2 共享 transformer 也可能改善表示。但是动机不等于当前论文证据。

当前删除 S1 的原因是：

1. Stage2 的正式前向只调用 S2，S1 patch projection 和 modality embedding 被显式冻结。
2. 没有 `S2-only pretraining vs S1+S2 pretraining` 的同预算 GreenEarthNet 下游消融。
3. SSL4EO 中 S1/S2 常有时间差，直接约束相同 latent 可能把真实时间变化误当模态差异。
4. Stage1 EuroSAT 精度没有显示双模态预训练已经形成强表征优势。
5. 在截止前新增 S1 稳健性轨道会分散 SOTA 主表资源。

审稿人问“为什么 Stage1/1.5 有 S1，后面没有”时，最诚实的最终回答应是：

> **S1 was explored during representation development but is not part of the final method because the target benchmark provides only the optical stream and our controlled ablation did not establish a downstream benefit. We therefore remove the S1-specific branch from all paper-facing claims.**

如果坚持保留 S1，最低实验成本是：

| 对照 | 必须匹配的条件 | 可接受的证据 |
|---|---|---|
| S2-only pretraining | 相同 encoder、总 steps、样本数、增强与Stage B预算 | GreenEarthNet三seed提升或严格缺云/遮挡鲁棒性提升 |
| S1+S2 pretraining | 显式建模时间差，不把非同期样本当瞬时同状态 | 提升稳定且不是额外训练量造成 |

在该结果出现前，S1 不进入摘要、方法图和贡献列表。

## 5.5 `phi` 没有直接出现在跑分中，是否等于没有用？

不等于。`phi` 的功能不是作为最终预测标签，而是控制观测形成。它应由专门实验衡量：

- 固定 `z`，改变 `phi_target`，输出能否切换到对应产品；
- 不提供 `phi` 时，跨产品重建是否显著变差；
- `z` 上产品类别可预测性是否下降；
- `z` 的地表语义可预测性是否保留；
- 配对预训练是否提高固定 GreenEarthNet 产品下的鲁棒性或初始化质量。

如果这些实验没有正向结果，`phi` 就不应留在最终方法中。不能仅凭架构图中存在 `phi_encoder` 声称成像解耦。

---

# 6. 与现有前沿的本质差异

## 6.1 不应该争夺的主张

以下位置已经拥挤或被已有工作覆盖：

- “第一个使用天气的 EO 预测模型”；
- “第一个天气驱动 EO world model”；
- “第一个递归 latent vegetation model”；
- “第一个遥感 world model”；
- “第一个多模态 S1/S2 foundation encoder”；
- “模型更大，所以更接近真实世界”。

## 6.2 可建立的差异点

| 相关方向 | 已有工作核心 | ObsWorld应证明的补充差异 |
|---|---|---|
| Contextformer | 强 GreenEarthNet 植被预测、天气条件、空间上下文 | 在不牺牲强精度的前提下，把 latent 变为可检验、可渲染、可复用的预测状态 |
| EO-WM | 天气驱动的概率多光谱未来与极端场景 | 显式分离状态动力学与产品条件化观测形成；避免声称首次天气世界模型 |
| VegSim类递归状态模型 | 气象驱动的植被 latent 与情景模拟 | 高分辨率观测产品因子化和标准 GreenEarthNet SOTA 级精度 |
| SSL4EO/CROMA等预训练 | 多源遥感表示与下游迁移 | 配对产品不是终点，而是最终 dynamics model 的 observation interface |
| 普通多任务模型 | 一个 backbone 接多个任务头 | 使用同一冻结的未来状态，检验预测充分性而非任务联合训练容量 |

最安全的 related-work 定位句：

> **Existing EO forecasters primarily optimize a direct mapping from a fixed observation history and weather to future vegetation, while recent EO world models focus on scenario-conditioned or probabilistic future generation. ObsWorld studies a complementary axis: whether a strong forecasting representation can serve as an observation-aware predictive state whose evolution is separated from product-dependent rendering and whose future state remains useful beyond pixel regression.**

## 6.3 创造性在哪里

创造性不在某一个新 transformer block，而在一个完整、可证伪的接口契约：

1. 用配对产品把“世界发生了什么”和“产品如何呈现它”拆开。
2. 用 latent future consistency 直接训练状态演化，而不仅监督最终像素。
3. 用强 SOTA forecaster 保证世界状态不是以牺牲任务性能换来的抽象概念。
4. 用同一冻结未来状态做事件读出，验证状态具有任务接口价值。

这是一条适合 AAAI 的方法与评估贡献：问题清楚、结构可检验、失败条件明确，并且不依赖规模叙事。

---

# 7. 主实验设计

## 7.1 Table 1：标准 GreenEarthNet SOTA 主表

Table 1 必须采用 Contextformer 官方 GreenEarthNet 协议，不再把 EarthNet2021 ENS 与其混列。

建议行：

| 分组 | 方法 | 作用 |
|---|---|---|
| Published | Persistence、Previous year、Climatology、Earthformer、PredRNN、SimVP、Contextformer | 公开参考 |
| Reproduced | Local Contextformer | evaluator与训练底座 |
| Ours ablation | Local Contextformer + state interface | 排除仅增加接口参数的影响 |
| Ours ablation | + latent future consistency | 验证预测状态训练 |
| Ours full | + paired observation pretraining + `phi` renderer | 完整 ObsWorld |

必须报告：

| 指标 | 方向 | 原因 |
|---|---:|---|
| R² | ↑ | 主预测解释能力 |
| RMSE | ↓ | 绝对植被误差 |
| NSE | ↑ | 相对基准表现 |
| Absolute bias | ↓ | 系统偏差 |
| Outperformance | ↑ | 相对气候态逐样本胜率 |
| RMSE25 | ↓ | 近期预测能力 |

正式协议要求：

1. 使用官方 split、cloud mask、target 和 evaluator。
2. 先直接加载官方权重验证本地 evaluator parity。
3. Local Contextformer 与 ObsWorld 使用同一初始化、相同数据、相同额外训练步数和选模规则。
4. 最终至少 3 seeds，报告 mean ± std。
5. 对每个 minicube 或 location/tile 做 paired bootstrap，避免只看两位小数。
6. 公开参数量、训练时长、预训练数据与额外计算。
7. 不把当前 EarthNet2021x 内部 val_dev 数字与 GreenEarthNet OOD-t 公开值混用。

## 7.2 Table 2：状态-观测因子化

采用严格配对的 SSL4EO S2 L1C/L2A 样本，使用相同四个公共波段：

| 输入状态来源 | 目标`phi` | 目标观测 | 试验简称 |
|---|---|---|---|
| L1C | L1C | L1C | L1C -> L1C |
| L1C | L2A | L2A | L1C -> L2A |
| L2A | L1C | L1C | L2A -> L1C |
| L2A | L2A | L2A | L2A -> L2A |

指标与解释：

| 指标 | 目标 | 证明点 |
|---|---|---|
| Reflectance MAE / RMSE | ↓ | renderer能否生成正确产品 |
| SAM | ↓ | 光谱形状是否保持 |
| SSIM | ↑ | 空间结构是否保持 |
| Paired latent distance | ↓ | 配对产品状态是否一致 |
| Product probe accuracy on `z` | 接近控制下限 | 产品信息是否仍泄漏到状态 |
| Land-cover/semantic probe | ↑或保持 | 状态是否避免坍塌和语义丢失 |

必须包含的控制：

| 控制 | 目的 |
|---|---|
| no-`phi` | 证明目标产品条件必要 |
| no shared-state constraint | 证明不是两个独立autoencoder |
| no bottleneck / direct translation | 排除仅靠大decoder完成图像翻译 |
| shuffled target `phi` | 检查renderer是否真正读取条件 |
| unpaired samples | 证明严格配对监督的价值 |

不能只报告 cross-reconstruction 好看。若 product probe 很高，说明 `z` 仍携带产品身份；若 semantic probe 崩溃，说明低 product probe 可能只是状态坍塌。

## 7.3 Table 3：世界模型行为与状态复用

最低版本可做成两面板，不额外引入大型外部数据集。

Panel A：受控状态演化

| 实验 | 对照 | 指标 |
|---|---|---|
| Future-state consistency | `T(z_t,D)` 对真实未来 `q(X_t+h)` | cosine/L2、按时距曲线 |
| Real/null/wrong weather | 固定历史，替换未来天气 | 预测差异、误差变化、事件响应方向 |
| Direct vs repeated transition | 同一状态接口、相同天气前缀 | R²/RMSE与latent drift曲线 |

Panel B：冻结状态复用

定义一个与 GreenEarthNet 同域、可从未来 NDVI 客观派生的任务，例如：

```text
event = future window内NDVI相对历史/季节基线下降超过delta
onset = 首次越过阈值的预测日
severity = future window内最大或累计负异常
```

训练和评价约束：

1. `delta`、基线窗口和事件定义只能在 train/val 冻结，不能看 test 调整。
2. 冻结主模型的 `q/T`，只训练线性层或两层 MLP。
3. 比较历史状态 `z_t`、预测未来状态 `z_t+h`、Contextformer feature 和 raw-history head。
4. 报告 AUROC、AUPRC、F1、onset MAE、severity MAE 和 calibration。
5. 明确这证明的是 state utility，不是假装成为独立外部任务泛化。

若之后资源允许，再增加真实外部植被压力或灾害标签；它属于增强实验，不是最低摘要承诺。

## 7.4 最小核心消融矩阵

| 编号 | 强骨架 | Predictive state interface | Latent future loss | SSL4EO pair | `phi` renderer | 作用 |
|---|:---:|:---:|:---:|:---:|:---:|---|
| B0 | ✓ | | | | | Local Contextformer |
| B1 | ✓ | ✓ | | | | 排除仅增参数效应 |
| B2 | ✓ | ✓ | ✓ | | | 预测状态贡献 |
| B3 | ✓ | ✓ | ✓ | ✓ | | 额外数据但无显式观测条件 |
| B4 | ✓ | ✓ | ✓ | ✓ | ✓ | 完整 ObsWorld |

只有 B4 同时在 Table 1 不退化、Table 2 因子化成立、Table 3 状态复用成立，完整叙事才闭环。

## 7.5 “大模型 + ours”应该怎样做

它只能是以下 `2x2`：

| 骨架 | Direct objective | + ObsWorld state contract |
|---|---:|---:|
| 轻量/原始Contextformer | A | B |
| 更强foundation encoder | C | D |

应该比较：

- `B-A`：机制在轻量骨架上的收益；
- `D-C`：机制在大骨架上的收益；
- `(D-C) - (B-A)`：机制是否随容量变化。

只报告“当前弱模型”对“大模型 + ours”没有归因价值，因为容量、初始化、数据和方法同时变化。若时间不足，整张 `2x2` 放弃，不影响中心主线。

---

# 8. SOTA 生存门与止损条件

## Gate 0：官方复现与 evaluator parity

必须先完成：

1. 官方 Contextformer checkpoint 在本地 GreenEarthNet evaluator 上得到与公开量级一致的结果。
2. 本地训练/微调版至少达到约 `R² >= 0.60`、`RMSE <= 0.145`。
3. 数据 split、mask、target、聚合和 checkpoint 选择全部记录 provenance。

若 Gate 0 不通过，任何“ours 超过本地 baseline”都不能称为 SOTA；首先修协议，不改模型。

## Gate 1：新增状态契约不得破坏强基线

先跑 B0/B1/B2 单 seed pilot：

- B1 应与 B0 基本等价，证明接口本身没有破坏预测。
- B2 至少在主要验证指标上稳定改善或不退化，同时 latent future error 明显降低。
- 若 B1 已显著变差，说明插入位置或 bottleneck 错误，应修架构而不是增加更多 loss。

## Gate 2：SOTA 声明门

正式写 SOTA 至少要求：

1. 同协议 `R² > 0.62` 且 `RMSE < 0.14`，不能只赢一个次要指标。
2. 优先目标为约 `R² >= 0.63`、`RMSE <= 0.135`，给四舍五入和方差留出空间。
3. 3 seeds 均值超过本地 matched Contextformer，paired bootstrap 或置信区间支持提升。
4. Outperformance、NSE和bias不能出现明显反向退化。
5. 若只在第二位小数打平，写 `competitive` 或 `on par`，不写 SOTA。

## Gate 3：world model 声明门

至少同时通过：

- cross-product rendering 显著优于 no-`phi`；
- paired latent consistency 改善且 semantic retention 不坍塌；
- future latent consistency 随训练改善；
- frozen future state 在事件读出上优于历史状态或匹配直接特征；
- null/wrong driver 对照表明模型不是完全忽略天气。

若只通过 Table 1，论文应叫 strong forecaster，不应叫 world model。

## Gate 4：Stage A保留门

SSL4EO 配对预训练只有在以下至少一项稳定成立时才进入最终方法：

- 改善 GreenEarthNet 三seed主指标；
- 在观测产品变化或人为产品扰动下显著提高鲁棒性；
- 明显改善 Table 2 因子化，同时 Table 1 不退化。

如果 Stage A 对任何正式指标都无益，应从最终模型删除；“已经训练过”不是保留理由。

## Gate 5：S1恢复门

S1 只有在同计算量的 `S2-only vs S1+S2` 下游消融中稳定获益，并解决时间错配后，才能进入附录；要进入摘要，还需要它成为核心增益来源。当前默认不做。

---

# 9. 审稿人问答模板

## Q1：为什么不直接在 GreenEarthNet 上从头端到端训练？

**回答：** 最终 GreenEarthNet 阶段会对有效模块做全量端到端训练或微调；“端到端”不等于“必须随机初始化”。配对观测预训练解决 GreenEarthNet 单一产品协议无法监督的状态-观测分解问题。我们同时报告随机/标准初始化与 paired-pretraining 的同预算消融，并公开额外数据和计算。

## Q2：使用 SSL4EO 是否只是靠更多数据提高精度？

**回答：** baseline 与 ours 必须获得相同的额外训练预算；B3 与 B4 区分“用了额外数据”和“使用显式 `phi` 因子化”。SSL4EO 的主要评价也不是 GreenEarthNet 分数，而是预先定义的配对状态一致性和交叉产品渲染。如果普通无条件预训练同样有效，就不能把收益归因于 observation factorization。

## Q3：Stage1 的 EuroSAT 只有 76.15%，为什么还相信它？

**回答：** 我们不把现有 Stage1 写成强 foundation model，也不以 EuroSAT 作为核心证据。最终 observation pretraining 使用与强预测骨架兼容的四波段 encoder，并由配对产品因子化和 GreenEarthNet 下游消融直接评价。旧 76.15% 只作为研发历史，不能证明最终方法。

## Q4：为什么早期使用 S1，最终模型却没有 S1？

**回答：** S1 是预训练探索，不是最终组件。目标 benchmark 仅提供光学历史，现有受控实验也没有证明 S1 预训练的下游收益，而且非同期 S1/S2 会引入状态错配。我们因此删除 S1 专属分支及其相关主张，避免把未验证动机写成贡献。

## Q5：GreenEarthNet 中 `phi` 是常量，它有什么用？

**回答：** `phi` 描述观测形成，而 GreenEarthNet 的目标观测协议固定，所以常量是任务事实，不是模型缺陷。它的功能通过 SSL4EO L1C/L2A 配对产品的 cross-rendering 和 no-`phi` 对照验证。我们不声称 GreenEarthNet 阶段使用了不存在的逐帧 acquisition metadata。

## Q6：这是否只是 Contextformer 加几个辅助 loss？

**回答：** 强骨架是实现载体，不是创新声明。方法贡献是一个可复用的 predictive-state contract，包括配对观测状态一致性、受控 latent transition、条件化观测 renderer 和冻结状态读出。每个接口都有独立实验和失败条件。若这些接口不能产生超越普通辅助正则的结果，这个质疑成立，论文不应过度包装。

## Q7：如何证明 `z` 是真实地表状态？

**回答：** 本文不声称恢复唯一真实物理状态。我们声称它是 predictive land-surface state：对未来观测充分、对配对产品条件稳定、能够在外生驱动下推进，并能支持未来事件读出。所有主张限定在这些可测性质内。

## Q8：为什么只有一个主要动态数据集也能叫 world model？

**回答：** 数据集数量不是 world model 定义。GreenEarthNet 检验动力学和标准预测，SSL4EO 检验观测形成，同域事件读出检验状态复用。三个数据角色覆盖 `q/T/O/H` 四个接口，比多个任务各自训练一套网络更能检验统一状态。

## Q9：植被衰退标签来自 NDVI，不还是同一个任务吗？

**回答：** 它不是外部泛化证据，因此我们只称 state utility。关键控制是冻结 `q/T`、使用浅层头并比较历史状态、预测状态和普通 backbone feature。它检验未来状态是否形成决策相关的可读结构，而不是宣称新领域迁移。若需要更强的通用性结论，必须增加独立真实标签数据集。

## Q10：没有 action 为什么叫 world model？

**回答：** 本文不是 agent world model。地球表面由天气等观测到的外生 forcing 驱动，`T(z,D,G,h)` 是受控动力学。文章始终使用 `exogenous-driver predictive-state world model` 这一限定，不把天气称为可执行 action。

## Q11：与 EO-WM 的本质区别是什么？

**回答：** 不争夺“天气驱动世界模型”或“概率未来生成”。本文聚焦状态演化与产品观测形成的显式分离，并要求同一 latent 通过配对产品渲染、未来状态一致性和冻结读出接受检验。正式 related work 仍需逐条核对 EO-WM 最新版本，避免夸大对方未覆盖的范围。

## Q12：SOTA 是否只是因为换成了 Contextformer？

**回答：** Table 1 同时报告本地 Contextformer、只增加状态接口、增加 latent loss、增加普通 SSL4EO 预训练和完整 ObsWorld。所有行共享初始化、数据和训练预算。只有完整模型相对 matched Contextformer 的增量才归因于 ObsWorld；相对当前 Direct-P4 的大幅提升不能算方法贡献。

## Q13：为什么不继续修当前 28M Stage2？

**回答：** 当前 Direct 与强基线有明显差距，Rollout 还存在累积漂移；参数量更大却精度更低。摘要与全文时间有限时，从已验证强预测结构出发比继续修复弱骨架有更高成功概率。旧模型仍作为结构诊断与负面证据保留。

---

# 10. 摘要与贡献冻结模板

## 10.1 稳定英文摘要

下列摘要在结果出来前不填性能形容词，方法主线可以现在冻结：

> **Earth-observation forecasting is commonly formulated as a direct mapping from image and weather histories to future vegetation, which can entangle land-surface evolution with product-dependent observation effects. We introduce ObsWorld, an observation-aware predictive-state world model that separates state inference, exogenous-driver dynamics, and conditional observation formation. ObsWorld learns a shared state from paired Sentinel-2 products, evolves that state under future weather and geographic context, and renders future observations under an explicit product condition. Built upon a strong GreenEarthNet forecaster and optimized end to end, the same predictive state is evaluated through standard vegetation forecasting, cross-product rendering, multi-step latent consistency, and a frozen future-event readout. On GreenEarthNet, ObsWorld achieves [R2/RMSE/Outperformance with uncertainty], while paired-product and state-utility experiments show [verified mechanism results]. These results establish observation-aware predictive states as a practical interface between accurate Earth-surface forecasting and reusable EO world models.**

在 SOTA 门未通过前，最后两句只能写可验证任务范围，不能提前写 `state-of-the-art`。

## 10.2 结果句三种合法版本

SOTA 通过：

> **ObsWorld establishes a new state of the art on the official GreenEarthNet protocol, improving the matched Contextformer baseline from [x] to [y] in R² and from [x] to [y] in RMSE across three seeds.**

统计持平但机制强：

> **ObsWorld matches the strong Contextformer forecasting baseline while adding cross-product observation control, improved latent future consistency, and reusable future-state readouts.**

只超过当前模型但未过强基线：

> **ObsWorld substantially improves our original predictive-state backbone and remains competitive on GreenEarthNet; its primary gains lie in observation factorization and state reuse.**

第三种不能写 SOTA。若摘要系统要求现在提交，优先使用不含未知结果强度的稳定摘要，而不是写一个可能被正式结果推翻的性能结论。

## 10.3 三条贡献

1. **问题与形式化贡献**：将 EO world modeling 表述为观测感知预测状态问题，显式分离状态推断、外生驱动演化和产品条件化观测形成。
2. **方法贡献**：提出与强预测骨架兼容的 ObsWorld state contract，通过配对状态一致性、latent future consistency 和 cross-product rendering 训练可组合状态。
3. **实证贡献**：在标准 GreenEarthNet 强基线、配对产品因子化和冻结未来状态读出三个维度联合评价准确性、可控观测和状态效用。

贡献列表不包含“统一所有遥感任务”“首次天气驱动”“强通用基础模型”或“S1/S2 全模态世界模型”。

---

# 11. 七页 AAAI 正文结构

| 部分 | 建议篇幅 | 必须回答的问题 |
|---|---:|---|
| 1. Introduction | 0.9页 | 为什么直接预测混淆状态演化与观测形成；本文三项贡献 |
| 2. Related Work | 0.6页 | EO forecasting、EO world models、EO SSL、predictive state；准确限定差异 |
| 3. Problem Formulation | 0.6页 | `q/T/O/H`、预测充分性、受控Markov和识别边界 |
| 4. Method | 1.6页 | 强骨架、paired pretraining、latent future loss、两个观测出口 |
| 5. Experimental Setup | 0.7页 | 两数据角色、官方协议、matched budget、三seed与事件定义 |
| 6. Results | 1.8页 | Table 1 SOTA、Table 2因子化、Table 3状态行为 |
| 7. Analysis & Limitations | 0.5页 | 消融、失败案例、非物理真值、外部任务边界 |
| 8. Conclusion | 0.3页 | 准确收束，不扩大主张 |

正文只需一张方法图和三张紧凑表。完整指标、更多可视化、训练细节、配对manifest审计和额外probe放补充材料，但决定中心主张的结果必须在正文。

---

# 12. 实际执行顺序

## P0：先建立强基线，不写新模块

1. 获取官方 Contextformer 代码与约 2.3GB 权重。
2. 冻结 commit、权重 hash、依赖和 GreenEarthNet manifest。
3. 用官方 checkpoint 跑本地 evaluator parity。
4. 跑一个 matched fine-tune baseline，确定额外训练本身不会制造不公平增益。
5. Gate 0 通过后才进入 P1。

## P1：最小 predictive-state 改造

1. 明确 Contextformer 哪一层作为空间状态 `z`。
2. 增加不阻断原预测头的 state projection。
3. 加入未来观测 encoder target 和 `L_latent_future`。
4. 完成 B0/B1/B2 单seed pilot。
5. 只有 B2 保持强精度且 latent 指标改善，才继续。

## P2：重做兼容的 observation pretraining

1. 从 SSL4EO 构造 S2 L1C/L2A 同 acquisition 配对 manifest。
2. 只使用 GreenEarthNet 兼容的四个公共波段和相同预处理。
3. 为 `phi` 增加明确的 L1C/L2A product token，而不是复用旧 S1/S2 modality code。
4. 训练共享 `q` 与 `O_product`，完成四向渲染。
5. 跑 no-`phi`、no-shared-state、direct-translation 和 product/semantic probes。
6. 将相同 encoder checkpoint 加载到 Stage B，跑 B3/B4。

## P3：正式主表

1. 固定所有超参数和 checkpoint 选择规则。
2. 跑 B0、B2、B4 三个最关键配置的 3 seeds；资源允许再补 B1/B3 三seed。
3. 用同一 evaluator 生成全部六个 GreenEarthNet 指标。
4. 做 location/tile clustered paired bootstrap。
5. 只在 Gate 2 通过后把 SOTA 写入摘要。

## P4：世界模型闭环

1. 生成 latent error 随时距曲线。
2. 跑 real/null/wrong weather 对照，不做无真值的强因果结论。
3. 在 train/val 冻结 vegetation-decline 事件定义。
4. 冻结主 checkpoint，训练浅层状态读出头。
5. 汇总 Table 2、Table 3 和失败案例。

## P5：可选增强，只有主表完成后才启动

- Foundation encoder `2x2`；
- S1 privileged-pretraining 消融；
- 外部真实植被压力或灾害任务；
- 更长时间、多区域和更多观测产品；
- U、在线校正或隐藏区域传输。

这些任务都不应抢占 P0-P4 的 GPU、工程时间和论文篇幅。

---

# 13. 主张白名单与禁区

## 13.1 当前已经可以写

- 遥感预测需要区分地表状态演化和观测形成。
- 当前模型在 GreenEarthNet 上明显低于 Contextformer，Rollout 存在累积误差。
- 当前 Stage2 加载 Stage1.5 权重，但只使用 S2 + neutral `phi`，缺少功能性闭环。
- 本文提出以配对产品、受控 latent transition 和状态复用共同检验 predictive state。
- 公开强骨架是提高 SOTA 可达性的合理工程与科学选择。

## 13.2 只有正式结果通过后才能写

- ObsWorld 达到 GreenEarthNet SOTA。
- 配对预训练改善标准预测或观测域鲁棒性。
- `phi` 实现产品条件化观测形成。
- `z` 对产品条件稳定且保留地表语义。
- 未来状态支持植被衰退发生、严重度和提前量预测。
- ObsWorld 的增益跨骨架成立。

## 13.3 禁止写

- `first weather-driven EO world model`；
- 恢复了真实、唯一或完整的物理地表状态；
- Stage1 是强或通用遥感 foundation model；
- Stage1.5 已完全 disentangle acquisition nuisance；
- Stage2 使用真实逐帧 `phi`；
- 最终方法使用 S1/S2 多模态动力学；
- 当前 Direct/Rollout 已接近或超过 Contextformer；
- EarthNet2021 ENS 与 GreenEarthNet R²/RMSE 可直接合并排名；
- 本地 Extreme/Seasonal 截断结果是官方 track 结果；
- 只因采用更大/更强 backbone 就证明 ObsWorld 方法有效。

---

# 14. “保留、重做、删除”最终清单

| 项目 | 决策 | 进入摘要 | 进入正文 | 条件 |
|---|---|:---:|:---:|---|
| ObsWorld名称 | 保留 | ✓ | ✓ | 限定为predictive-state world model |
| Contextformer强骨架 | 引入并复现 | 结果句可写 | ✓ | evaluator parity与matched baseline |
| 当前Direct-P4 | 保留为诊断 | | 次要/附录 | 不贬低、不冒充强基线 |
| 当前Rollout-P4 | 保留为漂移证据 | | 次要/附录 | 协议清楚 |
| Stage1/1.5概念 | 合并重写 | | ✓ | 统一称observation-factorized pretraining |
| 现有Stage1/1.5权重 | 非承重、可做对照 | | 可选附录 | 兼容且消融有用才保留 |
| SSL4EO S2 L1C/L2A | 保留并重做最小配对任务 | ✓ | ✓ | 配对审计、四波段兼容 |
| S1 | 删除 | | | 只有严格下游收益才恢复 |
| `phi` | 收缩并真实接线 | ✓ | ✓ | 仅声称已验证的product condition |
| 天气`D` | 保留 | ✓ | ✓ | real/null/wrong对照 |
| 地理先验`G` | 仅保留强骨架真实使用部分 | | ✓ | 不增加无收益复杂度 |
| 植被衰退读出 | 新增一个 | ✓ | ✓ | 冻结状态、预注册事件定义 |
| 洪水/建筑/xBD/PASTIS任务群 | 删除 | | | 后续工作 |
| 大模型+ours | 可选`2x2` | | 可选 | 主表完成后 |
| U/隐藏区域传输 | 删除于本路线 | | | 与最低闭环正交 |

---

# 15. 最终判断

## 15.1 对“是否削弱叙事”的回答

把原 `07` 全部砍成一个 GreenEarthNet 总分，确实把世界模型削弱成了普通预测器；但问题不是没有保留足够多任务，而是没有给状态、动力学和观测模型分别提供证据。本方案恢复的是三个必要接口实验，而不是恢复所有数据集。

## 15.2 对“SSL4EO是否无法自圆其说”的回答

现有表述确实难以自圆其说，因为 Stage2 只用 neutral `phi`，S1 分支不参与正式下游，且没有初始化消融。SSL4EO 只有在被重新定位为“配对产品观测因子化监督”，并让兼容 encoder 真实进入强 GreenEarthNet 主模型后，才有不可替代的理由。

## 15.3 对“Stage1/1.5如何保住”的回答

不保住阶段编号和全部旧实现，只保住其中最有价值的科学思想：**通过条件化观测模型，把观测差异从预测状态中分离。** 现有 checkpoint 可以作为开发资产，但不能要求论文为它们承担超出证据的主张。

## 15.4 对“S1和`phi`怎么办”的回答

- S1 当前删除，因为没有下游闭环。
- `phi` 保留，但改为真实可控的 L1C/L2A product condition。
- GreenEarthNet 中 `phi` 固定，明确披露，不假装它动态发挥作用。
- `phi` 是否最终保留，由 Table 2 的 no-`phi` 和 cross-rendering 决定。

## 15.5 对“怎样最可能够到SOTA”的回答

唯一高概率方向是：**先复现官方 Contextformer，让它成为不可跌破的精度底座，再以可关闭、可消融的方式增加 predictive-state 训练和 observation-factorized pretraining。** 当前弱 Stage2 继续调参、大模型直接替换、增加 S1、增加 U 或恢复多任务，都不是更高概率的 SOTA 路径。

## 15.6 最终论文一句话

> **ObsWorld 不是通过堆叠更多遥感任务来证明“看过更多世界”，而是在一个强预测器中建立可检验的地表预测状态：它把产品相关的观测形成与天气驱动的状态演化分开，在标准 GreenEarthNet 上争取 SOTA，并用配对产品渲染和冻结未来状态读出证明该状态确实具有世界模型接口价值。**

---

# 16. 关联证据与资源

## 16.1 本地文档

- [[07_ObsWorld主线定稿与实验方案]]：原始状态-动力学-观测与多任务愿景。
- [[58_ObsWorld_AAAI27中文论文终稿_主实验冻结版_20260717]]：当前中文论文、GreenEarthNet结果与协议边界。
- [[67_ObsWorld_核心叙事_相关工作差异_Table1数值与下一步_20260719]]：相关工作、协议与主表历史决策。
- [[69_ObsWorld_官方EarthNetScore对标_published_vs_ours_20260722]]：ENS完整结果及官方轨道勘误。
- [[70_ObsWorld_AAAI27中心叙事与主表最终冻结决策_20260721]]：Stage1/1.5证据审计与旧U路线；本文件不继承其U主线。

## 16.2 本地代码证据

- `configs/train/stage2_earthnet_v2_direct24.yaml`：正式Stage2要求Stage1.5 initializer，定义S2输入与world-state路径。
- `models/dynamics/obsworld_factory.py`：加载Stage1.5 encoder、`phi_encoder`与state projector。
- `models/dynamics/obsworld_core.py`：Stage2只走S2，冻结S1专属参数并使用neutral `phi`。
- `data/earthnet_fields.py`：`make_neutral_s2_phi`明确说明Stage2 dynamics不消费真实`phi`。
- `results/linear_probe_eurosat_95k.json`：Stage1 ViT-S EuroSAT OA `0.76148`，参考基线`0.941`。
- `evaluations/greenearthnet_oodt_20260719_214234/`：Direct-P4与Rollout-P4修正后OOD-t评估产物。
- `evaluations/officialENS_run1/`：EarthNet2021官方ENS本地评估产物。

## 16.3 外部资源

- Contextformer论文：<https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html>
- Contextformer代码：<https://github.com/vitusbenson/greenearthnet>
- Contextformer权重：<https://zenodo.org/records/10793870/files/model_weights.zip>
- SSL4EO-S12 v1.1：<https://github.com/DLR-MF-DAS/SSL4EO-S12-v1.1>
- EO-WM代码：<https://github.com/Luo-Z13/EO-WM>

> [!important] 最后执行原则
> 先完成 Gate 0 和 B0/B1/B2，不要同时启动 SSL4EO 重训、S1、foundation `2x2` 和外部下游任务。只要强基线尚未在本地站稳，任何更大的世界模型实验都无法回答“SOTA 是否够得到”。
