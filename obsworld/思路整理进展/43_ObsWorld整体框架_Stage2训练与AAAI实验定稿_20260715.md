# ObsWorld 整体框架、Stage2 训练与 AAAI 实验定稿

> **2026-07-16 最终数据更新。**当前论文与代码主线固定使用已审计通过的 raw EarthNet2021x：`train` 训练、`iid/ood` 主评测、`extreme/seasonal` 压力测试，统一采用 EarthNet2021 standard evaluator（官方评估器）口径。GreenEarthNet 目录不进入本轮训练、主表或自动数据合并；49 仅保留其历史审计解释。DGH 与实验层次以 44、45、46、47 为补充。

## 1. 最终中心叙事

ObsWorld 不是只预测下一段卫星像素的普通视频模型，而是一个面向地表过程的遥感世界模型。

> **它从带成像条件和缺失的历史遥感观测中估计预测性地表状态，在气象驱动、地理先验和真实时间跨度控制下递推未来状态，再解码为可与真实未来卫星观测直接核验的 RGBN 图像。**

“世界模型”在本文中不是泛泛的宣传词，而必须落在四项行为：

1. `state estimation`（状态估计）：历史图像不是直接复制，而是形成对未来有用的状态；
2. `controlled dynamics`（受控动力学）：未来变化要随 DGH 改变；
3. `compositional rollout`（可组合递推）：十天一步与五天加五天保持一致；
4. `observable verification`（可观测核验）：最终预测回到未来 RGBN，并由冻结的 EarthNet2021 官方评估器检验；训练、验证与测试清单不可混用。

## 2. 三段式方法框架

```text
历史 S1/S2 或 S2 观测 + 历史 mask/phi
                  │
                  ▼
Stage1/Stage1.5 encoder + state initializer I
                  │
                  ▼
           预测性地表状态 s0
                  │
        D path + C path + G + Δt
                  ▼
      共享状态转移 T（递推 20 个五日步）
                  │
                  ▼
            未来状态 s1 ... s20
                  │
            固定 Sentinel-2 解码器 O
                  ▼
        未来 RGBN 观测 + 冻结的官方评估器核验
```

### 2.1 Stage1 / Stage1.5：状态初始化

Stage1.5 不是“已经证明完全解耦”的最终结论，而是一个更好的初始化候选：

- 它保留 Stage1 的 EO 表征能力；
- 它额外学习 S1/S2 近时对齐、条件重建和 state bridge；
- 它的价值由后续相同 Stage2 初始化对比决定。

因此论文不应仅因 probe（探针）结果就声称 `phi` 已完全被移除；应报告 Stage1 与 Stage1.5 在同一 Stage2 下的未来预测、长时程误差和时间分割一致性。

### 2.2 Stage2：DGH 控制的状态演化

| 符号 | 中文 | 正式实现 |
|---|---|---|
| `D` | 外生驱动 | 八个 E-OBS 气象字段，每五日 mean/min/max，得到 24 维 token |
| `C` | 日历/季节条件 | 与天气分开编码，避免气象被日历捷径替代 |
| `G` | 地理先验 | 固定 `cop_dem`，保持空间图而非随意打平 |
| `Δt` | 时间跨度 | 5/10/20 日的共享转移跨度 |

旧版 Direct-DGH 仍保留为必要对照，但它只是“从同一初始状态查询各未来时刻”的预测器；只有 shared rollout 和 partition consistency（时间分割一致性）共同通过，才支撑世界模型主张。

### 2.3 Stage3：固定产品下的观测核验

当前主实验输出固定 Sentinel-2 RGBN 产品：

```text
x_hat_future = O(s_future, phi_fixed_S2)
```

这足以验证“状态是否能演化并产生未来观测”，但不夸大为任意未来传感器、太阳角或产品的可控渲染。更强的 `phi` 控制属于后续 Gate，不阻塞当前主实验。

## 3. 数据与实验协议

本项目的**训练原始数据**使用服务器已有的 EarthNet2021x NetCDF release（发布版本）：

```text
train      开发训练与最终重训来源
iid/ood/extreme/seasonal  raw 发布中的物理目录
```

在 49 的审计完成前，不能把这四个 raw 目录自动写成论文的最终测试轨道：

- 当前固定 EarthNet2021 standard：`iid/ood` 是主表，`extreme/seasonal` 是补充压力测试；
- `val_dev` 仅用于 checkpoint 选择，绝不从 `iid/ood/extreme/seasonal` 选择模型；
- 所有表格使用同一套 raw manifest、mask、预测导出与官方评分规则。

开发期仍可从 `train` 中确定性划分 `train_dev` 与 `val_dev`：

- `train_dev`：模型训练、统计量计算；
- `val_dev`：选 checkpoint、调学习率、冻结训练步数；
- `iid/ood/extreme/seasonal`：任何情况下都不用于调参。

主表不是“训练集上比精度”，而是在审计后锁定的未参与调参轨道上、由对应官方评估器得到的分数。无论最终协议哪一支，长期/域外测试都是支撑“受驱动长期地表演化”的补充证据，不是可有可无的附属实验。

## 4. Stage2 训练目标

基础损失：

```text
L_obs  = valid-mask RGBN reconstruction / forecast loss
L_state = optional latent target consistency
L_part = direct-vs-composed state and observation consistency
L_DGH  = D/G intervention diagnostics (evaluation, not always a training loss)

L_total = L_obs + λ_state L_state + λ_part L_part
```

训练安排：

1. 小样本 overfit，确认 mask、D path、梯度与解码器正确；
2. 短 rollout，先令 `λ_part=0`；
3. 逐渐增加 rollout 长度，并提高 `λ_part`；
4. 验证永远做完整 20 个未来五日步；
5. 任何主结果之前，先比较 matched Direct、shared T5 和 ObsWorld。

## 5. AAAI 主实验闭环

| 证据 | 回答的问题 | 合格现象 |
|---|---|---|
| IID / OOD ENS | 模型是否具有基础预测与空间泛化能力 | 优于 Persistence，且对 Direct 非劣 |
| Direct / shared rollout / ObsWorld | 收益来自哪里 | 可组合递推在长期不伤主预测 |
| 10 天 vs 5+5 天 gap | 是否有一致的状态演化 | gap 降低，真实预测不恶化 |
| true-D / no-D / shuffled-D | 是否真的使用外生驱动 | 正确 D 最好 |
| full-G / no-G | DEM 是否有效 | 有益则保留，无益则降级为解释先验 |
| Extreme / Seasonal | 极端与长时程是否稳定 | 后期不崩溃，行为结论可复现 |
| Stage1 vs Stage1.5 × partition | 前期投入是否真实有用 | 至少一条行为/预测证据改善 |

下游任务、大模型组合和第二数据集不是当前主稿必要条件。只有在主预测、递推行为和 DGH 干预均成立后，才考虑作为附录扩展。

## 6. 当前执行优先级

1. 冻结 EarthNet2021x 协议与 manifest；
2. 完成 Stage2 Direct/shared/partition 的最小训练路径；
3. 用完成后的 Stage1.5 checkpoint 做 smoke 与 `val_dev` Gate；
4. 先取得 IID/OOD 主结果；
5. 最后补 Strong baselines、Extreme/Seasonal、消融与图表。

这条路线保留了“模拟真实世界”的核心，但避免了无法由当前数据证明的过强说法。

## 参考

- [EarthNet2021 原论文](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf)
- [EarthNet Models PyTorch](https://github.com/earthnet2021/earthnet-models-pytorch)
