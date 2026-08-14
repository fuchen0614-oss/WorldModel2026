---
title: "ObsWorld Stage2 与 AAAI 主实验决策审查"
created: 2026-07-07
scope: "基于 output 全目录笔记 + 前沿论文调研"
status: "建议作为 30 号总纲的修订依据"
---

# ObsWorld Stage2 与 AAAI 主实验决策审查

> **数据协议更新（2026-07-16）：**本文保留为历史审查。当前执行数据为服务器已有的 EarthNet2021x NetCDF，且只采用 EarthNet2021 `train/iid/ood/extreme/seasonal`；请以 [48：统一数据协议](48_ObsWorld_EarthNet2021x统一数据协议与主实验规范_20260716.md) 为准。

## 0. 总结结论

我的最终判断是：

**主实验应以 EarthNet2021 为核心，Stage2 第一版应优先训练 EarthNet-only 版本；EarthNet+SSL4EO 联合训练应作为泛化增强/扩展实验，而不是第一张 SOTA 对比表的唯一模型。**

原因很直接：

1. EarthNet2021 是当前最适合你叙事的公开标准任务：它原生就是“给定历史遥感观测 + DEM + 目标期气象 forcing，预测未来 Sentinel-2 地表观测/植被状态”。
2. 你的主线虽然不是“为了预测而预测”，但必须通过预测来检验状态动力学。预测是观测界面，不是论文哲学终点。
3. 如果主实验直接用 EarthNet+SSL4EO 联训模型去和 EarthNet-only 方法比，审稿人会很容易质疑公平性；即便效果差，也会让你难以解释到底是方法弱、数据冲突、还是多数据集负迁移。
4. Stage1 用 SSL4EO 预训练、Stage2 用 EarthNet 训练不是问题，这是标准 pretrain-finetune 范式。需要做的是明确标注并做消融，而不是把它当成“精度竞赛吃亏”。
5. `h` 不应该因为 EarthNet 时间间隔稳定就只设一个。EarthNet 的 5-day cadence 很稳定，但预测 5 天、30 天、100 天的动力学难度完全不同。`h` 至少应作为 lead time / horizon embedding 或 per-frame temporal token 存在。

## 1. 对 output 现有方案的总体审查

### 1.1 已经走对的地方

现有材料最有价值的收束是：你已经从“未来影像生成”“主动观测”“遥感世界模型大而全”逐步收束到：

```text
像素观测 X_t
  -> 成像解耦状态 z_t
  -> Dynamics(z_t, D, G, h)
  -> z_{t+h}
  -> 可选观测解码 X_{t+h}
```

这条线是成立的。它能避开“只是视频预测”的风险，因为你不是只看像素相似度，而是强调外生驱动响应、地理约束、多跨度、不确定性和可解释评估。

### 1.2 仍然不稳的地方

当前最需要修正的有五点。

| 问题               | 当前表现                                 | 建议                                    |
| ---------------- | ------------------------------------ | ------------------------------------- |
| 主实验和叙事有轻微错位      | 文档说“不追求预测”，但 §5.1 又以 EarthNet 预测为主实验 | 改成“预测是检验动力学的标准观测协议”，不是论文终点            |
| Stage2 数据策略自相矛盾  | 30 号文档一处说联合训练最优，风险章节又说第一轮单 EarthNet  | 明确分成 `ObsWorld-E` 与 `ObsWorld-G` 两个版本 |
| ENS 方向写反         | 多处写 `ENS↓`                           | EarthNetScore 是 `ENS↑`，越高越好           |
| ERA5 泄露判断过硬      | 26/24.2 把目标期真实 weather 一概视为泄露        | 情景条件预测中合法；真实部署预测中不合法                  |
| Stage1.5 解耦主张需降调 | probe 仍可预测 orbit/satellite 到 67%-71% | 说“线性泄漏被抑制、跨模态对齐增强”，不要声称完全成像无关         |

## 2. 一个必须立刻修正的硬错误：ENS 是越高越好

EarthNet2021 原文定义 EarthNetScore 范围为 0 到 1，1 是完美预测，并由 MAD、OLS、EMD、SSIM 四个分量组合而成。原文还在表格中将 ENS 作为模型性能分数报告。因此你文档里的 `ENS↓` 应全部改成 `ENS↑`。

这不是格式问题，会直接影响你对 EO-WM / Earthformer / baseline 的解读。

建议修正：

```text
EarthNetScore / ENS: ↑
MAD / MAE / RMSE / NDVI-MAE: ↓
R² / DHR / PDC / SSIM: ↑
DRR: 越接近 1 越好
Spread-skill ratio: 越接近 1 越好
90% coverage: 越接近 0.9 越好
```

## 3. 第二个关键修正：未来 weather forcing 不一定是泄露

EarthNet2021 的标准任务是 guided video prediction。原文明确说模型可以使用 context frames、static DEM，以及包含目标时间步的 mesoscale climatic variables。也就是说，在 EarthNet2021 标准 benchmark 中，使用目标期 weather forcing 是协议的一部分。

但这只在下面这个定义中合法：

```text
scenario-conditioned forecasting / impact simulation:
给定未来 weather forcing，检验模型是否能把 forcing 转化为合理地表响应。
```

如果你把任务定义成真实部署预测：

```text
deployment forecasting:
在 t 时刻预测未来，未来真实 ERA5 reanalysis 不可用。
```

那就必须换成天气预报、气候平均或历史统计。

所以建议论文里写成双协议：

| 协议 | D 输入 | 是否用于主实验 | 目的 |
|---|---|---:|---|
| Oracle/scenario forcing | EarthNet/E-OBS/ERA5 目标期 forcing | 是 | 与 EarthNet/EO-WM 公平对比，验证驱动响应 |
| Climatology forcing | 历史气候平均 | 可做消融 | 测模型离开真实 forcing 后的退化 |
| Forecast forcing | 真实天气预报产品 | 可作为未来工作 | 部署预测 |

这样既不被“泄露”打倒，也不夸大部署能力。

## 4. Stage2 到底用一个数据集还是两个数据集

### 4.1 我的建议

Stage2 训练安排应分成两个版本：

```text
ObsWorld-E:
  Stage1/1.5: SSL4EO 预训练
  Stage2: EarthNet2021 train only
  用途: 主实验公平对比、DGH 消融、方法站稳

ObsWorld-G:
  Stage1/1.5: SSL4EO 预训练
  Stage2: EarthNet2021 + SSL4EO seasonal pairs / held-out climate
  用途: 跨气候泛化、generalist world model 叙事增强
```

第一张主表只放 `ObsWorld-E`。第二张表或附录再放 `ObsWorld-G`，说明多数据集是否带来跨气候收益。

### 4.2 为什么不建议一上来只做双数据集

双数据集训练不是错，但会带来三个论文风险：

1. **公平性风险**：别人通常在 EarthNet train split 上训练，你用了额外时序/季节对数据，主表需要标注 external data。
2. **解释风险**：如果 EarthNet 指标下降，你很难说清楚是模型弱还是多数据集泛化牺牲。
3. **工程风险**：SSL4EO 只有 4 季节快照，不是严格连续时序。强行当 Stage2 时序监督，会让 h 和 D 的含义变软。

因此，EarthNet-only 是主实验锚点，联合训练是扩展能力。

### 4.3 Stage1 用 SSL4EO、Stage2 用 EarthNet 是否算不公平

不算不公平，但要标注。

这属于遥感 foundation model 的常见范式：大规模自监督预训练，再在目标数据集上训练/微调。SatMAE、Prithvi-EO、Presto、Galileo 等工作都不是只在最终 benchmark 的训练集上从零开始。

你需要做的不是回避，而是设计消融：

| 消融 | 目的 |
|---|---|
| EarthNet from scratch | 证明 Stage1 预训练是否有用 |
| Stage1 baseline encoder vs Stage1.5 encoder | 证明成像解耦/跨模态对齐是否有用 |
| frozen encoder vs small-lr finetune | 证明是否破坏状态空间 |
| EarthNet-only vs EarthNet+SSL4EO | 证明联合训练是否真的提升泛化 |

## 5. 如果 Stage2 只用 EarthNet2021，主实验是什么

主实验不是“单纯预测像素”，而是：

> **Weather-conditioned land-surface state forecasting on EarthNet2021.**

中文可写成：

> **基于外生气象 forcing 的地表状态动力学预测。**

形式上你仍输出未来 20 帧 Sentinel-2 或 NDVI/latent state，因为这是可观测的评价界面。但论文解释时要说：像素是状态动力学的观测投影，标准预测指标只是第一层验证。

### 5.1 主表

建议主表如下：

| Method                              | External pretrain | Params | ENS↑ | MAD↓ | OLS↑ | EMD↑ | SSIM↑ | NDVI-MAE↓ | DHR↑ |
| ----------------------------------- | ----------------: | -----: | ---: | ---: | ---: | ---: | ----: | --------: | ---: |
| Persistence                         |                 否 |      - |      |      |      |      |       |           |      |
| ConvLSTM / PredRNN / SimVP          |                 否 |        |      |      |      |      |       |           |      |
| Earthformer                         |                 否 |        |      |      |      |      |       |           |      |
| Contextformer-style |               否/是 |        |      |      |      |      |       |           |      |
| EO-WM                               |                 否 |   387M |      |      |      |      |       |           |      |
| ObsWorld-E                          |            SSL4EO |        |      |      |      |      |       |           |      |

注意：如果你引入 EO-WM 的 DHR/PDC 风格指标，必须清楚说明是复现其 diagnostic benchmark，还是你自己构造的 EarthNet-DGH diagnostic。

### 5.2 主实验的公平性

最公平的设置是：

1. 所有对比方法都使用 EarthNet train split。
2. 所有方法拿到相同 context frames、DEM、目标期 weather forcing。
3. 你的 SSL4EO 预训练标注为 external unlabeled pretraining。
4. 如果审稿人担心外部预训练，附一行 `ObsWorld-E w/o SSL4EO pretrain`。

这样你既能正面对标，也不会被“外部数据作弊”击穿。

## 6. H 是否只需要一个时间跨度

不建议。

EarthNet 的采样间隔确实稳定：context 通常是 10 帧，目标是未来 20 帧，每 5 天一帧。但这只说明时间网格稳定，不说明动力学难度固定。预测 `t+5` 和 `t+100` 是完全不同的任务。

建议有两种实现：

### 6.1 序列预测实现

模型一次输出未来 20 帧：

```text
input: X_{t-45:t}, D_{t:t+100}, G
output: X_{t+5:t+100}
```

这时 `h` 可以作为每个 target frame 的 temporal/lead-time embedding：

```text
h = {5, 10, 15, ..., 100} days
```

### 6.2 多跨度直接预测实现

训练时采样多个 horizon：

```text
h in {5, 10, 20, 30, 60, 100}
```

每个 h 预测对应未来帧或未来 latent。

如果你要把 H 作为 DGH 的贡献点，必须做 `w/o h` 或 `single fixed h` 的消融。否则 H 只是一个工程 token，不是论文贡献。

## 7. 前沿工作的主实验规律

### 7.1 EarthNet2021

EarthNet2021 的主实验是标准 train/test split 上的 future satellite forecasting。它有 IID、OOD、Extreme Summer、Seasonal Cycle 等 tracks；模型输入历史影像、DEM 和气象变量，输出未来 20 帧 Sentinel-2，并用 EarthNetScore 及分量指标评价。

### 7.2 Contextformer（CVPR 2024）

Contextformer 是一个相关的气象条件植被预测基线；它的条件注入方式与消融设计可供借鉴，但其论文的数据划分不是本项目的执行协议。本项目只在服务器已有的 EarthNet2021x NetCDF 文件上，按 EarthNet2021 的 IID/OOD/Extreme/Seasonal 轨道组织实验。

### 7.3 EO-WM

EO-WM 直接把 EarthNet2021 扩展为 weather-driven world modeling：主实验仍是 EarthNet2021 10 context / 20 target forecasting，但增加 Extreme Summer 和 Seasonal Matched-Pair diagnostic，评价模型是否按 weather forcing 正确响应。它还报告 DHR、PDC、DRR 等非纯像素指标。

这对你非常重要：**最新前沿已经在做“标准预测 + 驱动响应诊断”的组合，而不是只报一个生成质量指标。**

### 7.4 遥感基础模型

SkySense、Prithvi-EO-2.0、TerraMind、Galileo、Presto、SatMAE 等工作的主实验通常是：

```text
大规模预训练
  -> 多个公开下游 benchmark
  -> 与同类 foundation models / specialist models 比
  -> 消融预训练目标、输入模态、模型规模或条件字段
```

它们不是通常拿“另一个完全无关数据集”做唯一主实验，而是把目标 benchmark 的 test split 作为主表，再用跨域/下游任务证明泛化。

## 8. ObsWorld 最合理的 AAAI 实验安排

8 页正文建议这样安排。

### 8.1 主实验：EarthNet2021 标准预测

目的：证明你的动力学模型不是只会讲概念，能在标准 benchmark 上成立。

报告：

```text
ENS↑, MAD↓, OLS↑, EMD↑, SSIM↑, NDVI-MAE↓, R²↑
```

同时加入一个 response 指标：

```text
DHR↑ 或 PDC↑
```

### 8.2 世界模型诊断：DGH-response benchmark

目的：证明它真的使用 D/G/h，而不是普通时序外推。

建议三类：

1. Extreme weather subset：热浪/干旱样本，测 NDVI decline amplitude。
2. Seasonal matched pairs：同地不同年 weather forcing 差异，测响应方向和大小。
3. Counterfactual forcing sweep：固定 z 和 G，改变 precipitation/VPD/radiation，画响应曲线。

第三类没有真实反事实真值，所以只能作为“模型行为诊断”，不要写成强因果结论。

### 8.3 DGH 消融

必须做。

建议不要一次做过多组合，正文保留 6-8 个：

| Config | D | G | h | Stage1.5 | 目的 |
|---|---:|---:|---:|---:|---|
| AR baseline | 否 | 否 | 否 | 是 | 只有 z_t 惯性外推 |
| +D | 是 | 否 | 否/固定 | 是 | 气象 forcing 贡献 |
| +G | 否 | 是 | 否/固定 | 是 | 地理先验贡献 |
| +h | 否 | 否 | 是 | 是 | 多跨度贡献 |
| +D+h | 是 | 否 | 是 | 是 | 你最核心的组合 |
| full DGH | 是 | 是 | 是 | 是 | 完整模型 |
| full w/o Stage1.5 | 是 | 是 | 是 | 否 | 解耦/对齐是否有用 |

如果篇幅不够，`+G` 可以放附录，因为植被任务里 elevation 可能贡献有限。

### 8.4 泛化实验

这里放 `ObsWorld-G`，而不是让它抢主表。

可选设置：

1. EarthNet2021 OOD track。
2. EarthNet2021 IID/Extreme/Seasonal 补充轨道。
3. SSL4EO held-out climate/region seasonal-pair prediction。

建议优先级：

```text
EarthNet2021 IID/OOD > EarthNet2021 Extreme/Seasonal > SSL4EO seasonal pairs
```

因为前两者更接近标准 benchmark；SSL4EO seasonal pairs 更像自建泛化诊断。

### 8.5 下游任务

下游任务不是主实验，不要喧宾夺主。

最低限度做 1 个，推荐：

1. **CropHarvest / crop mapping**：最贴近 vegetation dynamics 和 weather/DEM 条件。
2. **Sen1Floods11**：如果你想证明 z 对水体/灾害也有迁移能力。

正文最多放一张小表，更多放 appendix。

## 9. 论文叙事建议

建议摘要和 introduction 把主线改成：

```text
Existing EO forecasting models can predict future pixels, but standard metrics do not reveal whether a model has learned a physically meaningful land-surface transition. We propose ObsWorld, an imaging-decoupled land-surface dynamics model that estimates a state from biased satellite observations and predicts its transition under exogenous weather forcing, geographic priors, and forecast horizon. We evaluate ObsWorld on EarthNet2021 not only by reconstruction metrics, but also by driver-response diagnostics and DGH ablations.
```

中文逻辑：

1. 遥感影像不是世界本身，而是地表状态在成像条件下的观测。
2. EarthNet/EO-WM 类任务已经证明 future EO forecasting 重要，但标准像素指标不足以证明模型理解了驱动响应。
3. ObsWorld 的贡献是把状态、成像条件、外生驱动、地理先验和预测跨度显式分开。
4. 主实验在 EarthNet2021 上公平对比，能力实验检验 DGH 响应、极端事件、matched-pair 和不确定性。

## 10. 推荐的立即执行清单

1. 修改所有实验表：`ENS↓` 改为 `ENS↑`。
2. 把“未来 ERA5 泄露”改成“双协议”：scenario forcing 合法，deployment forecasting 不合法。
3. Stage2 先做 `ObsWorld-E`：EarthNet-only，打通标准主表。
4. 同时保留 `ObsWorld-G` 配置，但只作为泛化/附录，不作为第一主实验唯一模型。
5. `h` 改为 EarthNet lead-time embedding：至少 `{5,10,15,...,100}` 或抽样 `{5,10,20,30,60,100}`。
6. Stage1.5 论文说法降调：不要声称完全解耦，改成“线性泄漏抑制 + 跨模态对齐 + probe 透明报告”。
7. DGH 消融优先跑 `D` 和 `h`，`G` 若效果弱则诚实报告为任务相关发现。

## 11. 参考来源

- EarthNet2021: https://arxiv.org/abs/2104.10066
- EarthNet2021 CVPRW paper PDF: https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf
- Contextformer, CVPR 2024: https://arxiv.org/abs/2303.16198
- EO-WM, 2026: https://arxiv.org/abs/2606.27277
- RS-WorldModel, 2026: https://arxiv.org/abs/2603.14941
- Remote Sensing-Oriented World Model, 2025: https://arxiv.org/abs/2509.17808
- SatMAE, NeurIPS 2022: https://arxiv.org/abs/2207.08051
- Presto: https://arxiv.org/html/2304.14065
- Galileo, ICML 2025: https://proceedings.mlr.press/v267/tseng25a.html
- Prithvi-EO-2.0: https://arxiv.org/abs/2412.02732
- TerraMind, ICCV 2025: https://arxiv.org/abs/2504.11171
