# ObsWorld：EarthNet2021x、DGH 与世界模型主线重整

> **2026-07-16 最终数据更新。**当前数据、清单和运行命令以 raw EarthNet2021x 的 `train/iid/ood/extreme/seasonal` 协议为准；`iid/ood` 是主评测，`extreme/seasonal` 是压力测试。GreenEarthNet 是独立的后续扩展，不再影响本轮路线。本文件说明为什么现有 EarthNet2021x raw data、DGH 和 ObsWorld 世界模型叙事可以且应该继续保留。

## 1. 当前数据结论

不换训练数据。服务器已有的 EarthNet2021x NetCDF 数据按以下**raw（原始发布）目录**使用：

```text
train      → 训练来源
iid/ood    → 主评测
extreme/seasonal → 压力测试
```

它的价值不是“普通视频预测数据”，而是：历史 Sentinel-2 观测、未来真实 E-OBS 气象驱动、DEM 和多种时间跨度测试共同构成了一个可验证的地表演化问题。

## 2. 不改变的中心叙事

> **ObsWorld 是一个成像条件解耦的地表状态动力学遥感世界模型：它从多源、有偏、带成像条件的遥感像素观测中估计更稳定的地表状态，在外生驱动和地理先验约束下预测未来地表状态，再用固定的未来产品条件把未来状态渲染为可验证的未来像素观测。**

这句话保留了初版立意的绝大部分，但加入两个必要边界：

1. 当前 EarthNet2021x 主实验固定 Sentinel-2 产品，不能声称已经验证任意未来传感器/太阳角控制；
2. “世界模型”必须落实为可检验行为，而不只是 latent（隐变量）名字。

可检验行为是：

- 历史观测变化时，初始化状态对未来预测有用；
- 正确 DGH 驱动优于去掉或错配驱动；
- 十天一步与五天加五天得到相容的状态和观测；
- 递推模型在长时程、极端或季节循环轨道中不退化为单纯复制最后一帧；
- 预测最终回到真实未来 RGBN 观测，并由冻结的 EarthNet2021 standard evaluator 检验；开发验证与四条测试轨道绝不混用。

## 3. DGH 为什么保留、怎样升级

| 字段 | 原有投资 | Stage2 正式含义 | 为什么保留 |
|---|---|---|---|
| `D` | 天气/外生驱动 | 30 个五日 token，每 token 为 8 个 E-OBS 字段的 mean/min/max，即 24-D | 地表状态变化不能只靠图像惯性解释 |
| `G` | DEM/地理先验 | 固定 `cop_dem` 空间图 | 地形提供长期不变、可解释的局地背景 |
| `H` | 预测时距 | 由 `delta_t` 累积的真实时间跨度 | 共享转移模型必须知道走了多远 |

关键变化不是抛弃 DGH，而是把旧的“每个终点一个累计摘要”升级为逐区间路径：

```text
历史观测 → 状态 s0
每五日 D/C/G/Δt → 共享转移 T
s0 → s1 → … → s20
每个未来状态 → 固定 RGBN 解码器 → 真实未来观测
```

这样，模型才可以比较：

```text
T(s0, D[0:2], 10天)

与

T(T(s0, D[0:1], 5天), D[1:2], 5天)
```

这就是时间分割一致性（partition consistency）：同一真实十天，不应因计算路径不同而产生互相矛盾的未来。

## 4. Stage2 的三层对照

| 模型 | 是否共享状态转移 | 是否使用时间分割约束 | 证明什么 |
|---|---|---|---|
| matched Direct-DGH | 否 | 否 | 强精度对照；避免把递归本身误认为优势 |
| shared T5 rollout | 是 | 否 | 单独检验共享五日递推 |
| ObsWorld | 是 | 是 | 检验可组合地表状态动力学 |

三个模型必须共享：训练/验证清单、D/C/G 信息、参数预算、预测跨度和输出 RGBN 头。否则结果无法归因于“世界模型结构”。

## 5. EarthNet2021x 中的 `phi`

Stage1/Stage1.5 已经为 `phi` 做了数据构造、条件重建、S1/S2 对齐和 probe（探针）验证，这些不作废。

但 Stage2 主实验中只有可靠的历史日期、产品身份和有效像素标记；没有完整的未来太阳/观测几何。因此主实验写作：

```text
x_future = O(s_future, phi_fixed_S2)
```

而不是写成任意 `phi_future` 可控渲染。Stage1.5 的价值通过相同 Stage2 初始化的 2×2 实验判断：若它改善长时程、OOD 或时间分割一致性，就保留为主方法初始化；否则降为预训练/附录证据。

## 6. 主实验怎样支撑世界模型叙事

### 主表：由审计冻结的 OOD 轨道

比较 Persistence、简单气候基线、可复现强时空基线、matched Direct-DGH、shared T5 和 ObsWorld。主表固定为 EarthNet2021 standard 的 IID/OOD，Extreme/Seasonal 是补充压力测试；所有指标、mask 和导出都使用同一口径。

- IID：证明在同一任务分布中具有基础预测能力；
- OOD：证明在新空间地点仍有泛化能力；
- ObsWorld 相比 Direct：证明状态递推不以主预测质量为代价；
- ObsWorld 相比 shared T5：证明时间可组合约束的独立价值。

### 补充表：Extreme 与 Seasonal

- Extreme：检验气象异常下的地表响应；
- Seasonal：检验多季节、长时程递推是否稳定。

它们不是额外数据集，而是同一服务器数据中的正式补充轨道，因此尤其适合世界模型叙事。

### 消融与行为图

1. `true-D / no-D / shuffled-D`：证明用了时间对齐的气象驱动；
2. `full-G / no-G`：检验 DEM 是否真的有增益；
3. `full24 / D-core`：检验原 DGH 紧凑设计是否已足够；
4. 10 天与 5+5 天的状态/像素 gap：验证可组合演化；
5. 5–100 天分时距曲线：避免平均分数掩盖后期崩溃。

## 7. 当前最优执行顺序

1. 运行 48 中的冻结脚本，生成 `train_dev/val_dev/train_all/iid/ood/extreme/seasonal` 清单；
2. 继续完成 Stage2 的 Direct、shared rollout、partition 代码；
3. 用 Stage1.5 checkpoint 做小样本 smoke 和开发验证；
4. 先取得 IID/OOD 主结果；
5. 再补 Extreme/Seasonal、基线、消融和可视化。

这条路线不放弃“模拟真实世界”的目标；它把这个目标落在“状态估计、受驱动演化、可组合推演、返回真实观测验证”四个可检查属性上。

## 参考

- [EarthNet2021 原论文](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf)
- [EarthNet Models PyTorch](https://github.com/earthnet2021/earthnet-models-pytorch)
