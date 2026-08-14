---
title: "ObsWorld AAAI 最终叙事与实验闭环"
created: 2026-07-08
purpose: "把 ObsWorld 的核心叙事、实验定位、可接受结果与 AAAI 投稿标准统一到一条闭环"
status: "集中版建议稿：后续可作为论文实验与写作总依据"
---

# ObsWorld AAAI 最终叙事与实验闭环

> **数据协议更新（2026-07-16）：**本文的世界模型主线仍有效；数据、验证和评测则统一以服务器已有的 EarthNet2021x NetCDF 与 EarthNet2021 `train/iid/ood/extreme/seasonal` 为准，详见 [48：统一数据协议](48_ObsWorld_EarthNet2021x统一数据协议与主实验规范_20260716.md)。

## 0. 先给结论

我的判断是：**当前 ObsWorld 方向可以支撑 AAAI 级别叙事，但不能按“EarthNet2021 精度刷榜模型”来写。**

最稳的定位是：

> **ObsWorld 是一个成像解耦的地表状态动力学世界模型。它把遥感影像看作地表状态在特定成像条件下的观测，而不是世界本身；模型从观测中估计状态，并显式学习该状态在外生驱动 D、地理先验 G 和预测跨度 h 条件下如何演化。**

这篇文章的主张不是：

> 我们是 EarthNet2021 上像素指标最强的预测器。

而是：

> 标准未来观测预测只能说明模型会外推未来图像；要证明遥感世界模型能力，必须进一步检验模型是否学习到外生驱动下可诊断、可解释、可校准的地表状态转移。

所以实验闭环必须是：

```text
EarthNet 标准预测
  -> 证明方法在公开标准任务上可比

DGH 消融
  -> 证明 D/G/h 不是概念包装，而是有效机制

Weather-response 诊断
  -> 证明模型真的响应外生驱动，而不是记忆季节均值

Uncertainty / G consistency
  -> 证明模型知道哪里难预测，并且地理背景不是无意义通道

Downstream / transfer
  -> 证明 z 不只是 EarthNet 特化特征，而是有迁移价值的地表状态表示
```

只做第一项，会被困在 EO-WM / Earthformer / Contextformer 的赛道里。五项合起来，才是 ObsWorld 的赛道。

## 1. 我们真正想要什么

ObsWorld 的目标不是“预测一张未来遥感图像”这么窄。

我们真正想要的是：

1. **从有偏观测中估计地表状态**  
   遥感影像包含地表、云、太阳角、传感器、轨道、季节等混合因素。我们希望模型得到的 `z` 更接近“地表是什么”，而不是“这张图看起来怎样”。

2. **建模状态如何随外生条件演化**  
   地表变化不是凭空发生的。植被返青、干旱退化、水分胁迫、热浪影响都与外生驱动有关。因此 Stage2 的核心是：

   ```text
   z_t + D + G + h -> z_{t+h}
   ```

3. **用可观测预测检验内部动力学**  
   未来状态 `z_{t+h}` 本身不能直接由人类观察，所以需要通过 decoder 或观测指标投影到未来 S2 / NDVI / vegetation response 上评估。

4. **证明模型不是只会拟合平均未来**  
   如果模型只靠季节均值、地理位置或历史惯性预测，它也可能在像素指标上不错。因此必须用 DGH 消融和 response 诊断检查模型是否真的用了 D/G/h。

5. **知道自己何时不确定**  
   世界模型不应只给单点预测。遥感未来受云、极端天气、土地响应滞后和观测缺失影响，模型应能输出不确定性，并且高不确定区域应更容易出错。

## 2. 主线一句话

建议最终论文主线固定为：

> **Future Earth-observation forecasting should be evaluated as land-surface state dynamics under exogenous forcing, rather than merely as future-pixel reconstruction.**

中文表达：

> **未来遥感预测不应只评价未来像素是否相似，而应检验模型是否学到了外生驱动下物理有意义的地表状态转移。**

ObsWorld 对应的定义：

> **ObsWorld learns an imaging-decoupled land-surface state and predicts its transition under external drivers, geographic priors, and forecast horizons.**

中文：

> **ObsWorld 学习成像解耦的地表状态，并在外生驱动、地理先验和预测跨度条件下预测其状态转移。**

## 3. 方法叙事怎么写才“完美”

### 3.1 不要这样写

不要把贡献写成：

```text
我们用 SSL4EO 预训练，再在 EarthNet 上微调。
我们加入 D/G/h，所以精度提高。
```

这会显得像普通工程组合。

### 3.2 应该这样写

更稳的写法是：

```text
Existing EO forecasting methods optimize future visual similarity, but this does not reveal whether they learn a meaningful transition of land-surface states. ObsWorld reformulates EO forecasting as imaging-decoupled state dynamics. It separates observation conditions from land-surface states, conditions state transitions on exogenous weather forcing, geographic priors, and forecast horizons, and evaluates the resulting model through standard forecasting, DGH ablations, driver-response diagnostics, uncertainty calibration, and representation transfer.
```

中文逻辑：

1. 现有未来遥感预测大多直接预测未来观测。
2. 但遥感观测不是世界本身，而是地表状态在成像条件下的投影。
3. 如果只看未来像素相似度，无法判断模型是否真的理解地表状态如何响应天气和地理背景。
4. 因此我们提出 ObsWorld：先估计成像解耦状态，再学习 D/G/h 条件下的状态动力学。
5. 我们不仅在 EarthNet2021 标准预测上对比，还用消融、响应诊断、不确定性和下游迁移来验证世界模型能力。

### 3.3 Contribution 建议

贡献建议写三条，不要写太多：

1. **Problem/Formulation**  
   提出面向遥感的成像解耦地表状态动力学形式化，明确区分 state、observation、imaging condition、external driver、geographic prior 和 horizon。

2. **Method**  
   提出 ObsWorld 框架：Stage1/1.5 估计成像解耦状态，Stage2 通过 DGH 条件化动力学预测未来状态，Stage3 将未来状态投影回观测空间并输出不确定性。

3. **Evaluation Protocol**  
   设计一套超越未来像素相似度的评估协议，包括 DGH 消融、weather-response 诊断、uncertainty calibration、geographic consistency 和 transfer evaluation。

## 4. 实验设计的总逻辑

实验不是随机堆叠，而是逐层回答审稿人的问题。

| 审稿人问题 | 对应实验 | 你要证明的点 |
|---|---|---|
| 你不是只讲概念吗？ | EarthNet 标准预测 | 方法在公开 benchmark 上能工作 |
| D/G/h 是不是包装？ | DGH 消融 | 每个条件变量有可测贡献 |
| 你是不是只记住季节平均？ | Weather-response 诊断 | 模型会随天气 forcing 改变预测 |
| 你说 world model，是否知道哪里不确定？ | Uncertainty | 高不确定区域对应高误差 |
| G 只有 elevation，别人认吗？ | G consistency / stratified eval | G 是地理背景，不是硬物理定律 |
| z 真的是状态，不只是特征？ | Downstream / transfer | z 对其他任务有迁移价值 |
| 小模型怎么和大模型比？ | Params/efficiency + plug-in optional | 我们强调机制、效率和可插拔性 |

这就是完整闭环。

## 5. 实验一：EarthNet 标准预测

### 5.1 定位

这是论文的主实验平台，但不是全部叙事。

它的作用是：

> 证明 ObsWorld 在标准 future EO forecasting benchmark 上具有可比性。

不是：

> 证明 ObsWorld 是所有 EarthNet 指标上的绝对第一名。

### 5.2 表格建议

**Table 1: EarthNet2021 Standard Forecasting**

| Method | Type | Params | External Pretrain | ENS↑ | MAD/MAE↓ | SSIM↑ | NDVI-MAE↓ | DHR↑ | Cost |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| Persistence | naive | - | no | | | | | | |
| ConvLSTM | temporal prediction | | no | | | | | | |
| SimVP / PredRNN | video prediction | | no | | | | | | |
| Earthformer | spatiotemporal transformer | | no | | | | | | |
| Contextformer / EarthNet2021x | weather-guided vegetation forecasting | | no / task data | | | | | | |
| EO-WM | diffusion world model | 387M | task data | | | | | | high |
| ObsWorld-S | state dynamics | ViT-S + DGH | SSL4EO | | | | | | lower |

注意：

1. `ENS` 是越高越好。
2. 必须报告参数量，否则小模型和 387M diffusion 的对比会显得不公平。
3. 必须报告至少一个 response 指标，例如 DHR，否则你的特点无法从第一张表体现。

### 5.3 可接受结果

理想情况：

```text
ObsWorld-S 在 ENS / NDVI-MAE / DHR 上接近或超过 Earthformer/Contextformer；
DHR 或 response 指标明显优于普通预测模型；
参数量和推理成本低于 EO-WM。
```

可接受情况：

```text
ObsWorld-S 在像素/ENS 指标略低于 EO-WM；
但明显优于 naive / ConvLSTM / 简单 video baseline；
与 Earthformer/Contextformer 接近；
在 DHR、NDVI response、参数效率或 uncertainty 上更强。
```

危险情况：

```text
连 Persistence / ConvLSTM 都明显打不过；
DHR 也没有优势；
DGH 消融几乎无增益。
```

如果出现危险情况，叙事会撑不住，需要复盘模型和数据。

## 6. 实验二：DGH 消融

### 6.1 定位

这是最关键的机制实验。

它回答：

> D/G/h 到底是不是有用，还是只是把几个字段拼进去包装成世界模型？

### 6.2 表格建议

**Table 2: DGH Mechanism Ablation**

| Config | D | G | h | Stage1.5 | ENS↑ | NDVI-MAE↓ | DHR↑ | Long-horizon Error↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AR baseline | - | - | - | yes | | | | |
| +D | yes | - | - | yes | | | | |
| +G | - | yes | - | yes | | | | |
| +h | - | - | yes | yes | | | | |
| +D+h | yes | - | yes | yes | | | | |
| full DGH | yes | yes | yes | yes | | | | |
| full w/o Stage1.5 | yes | yes | yes | no | | | | |

### 6.3 预期与容错

最理想：

```text
D 贡献最大；
h 显著改善远期预测；
G 小幅提升或在特定地形区域提升；
Stage1.5 对 response 或稳定性有帮助。
```

可接受：

```text
D 和 h 有明确贡献；
G 整体贡献小，但 shuffled-G 或 high-elevation subset 有差异；
Stage1.5 不显著提升主指标，但改善跨模态一致性或降低成像敏感性。
```

不可接受：

```text
D、h、G 全都没有贡献；
full DGH 与 AR baseline 基本一样；
weather-response 诊断也没有改善。
```

如果 D 和 h 不起作用，ObsWorld 的核心会受损。

如果 G 不强，不是致命问题。因为 EarthNet 植被短期预测里，天气和时间跨度天然比 elevation 更强。

## 7. 实验三：Weather-response 诊断

### 7.1 定位

这是区分 ObsWorld 和普通 future-frame predictor 的关键实验。

普通模型可能会输出“看起来合理”的未来图，但不一定真正响应 weather forcing。这个实验就是检查：

> 当天气条件改变时，模型的未来状态是否按合理方向改变？

### 7.2 三种设计

1. **Extreme subset**

   选干旱、热浪、强降水等样本，评估模型是否能预测 NDVI 下降/恢复方向。

2. **Seasonal matched pairs**

   找相似季节、相似地点但天气条件不同的样本，比较模型是否能区分不同 forcing 下的未来变化。

3. **Forcing sweep**

   固定 `z_t, G, h`，人为改变 D：

   ```text
   D_real
   D_precip_down / VPD_up
   D_precip_up / VPD_down
   ```

   看未来 NDVI 或 vegetation response 是否按合理方向变化。

### 7.3 指标与图

可以报告：

```text
DHR: Directional Hit Rate，预测变化方向是否正确
PDC: predicted direction consistency
NDVI response slope
response correlation
```

可视化：

```text
同一地点，三种 D scenario 下的未来 NDVI 曲线
```

### 7.4 可接受结果

理想：

```text
ObsWorld 的 DHR 明显高于不使用 D 的模型；
forcing sweep 中降水/VPD 改变导致合理的 NDVI 响应；
极端天气 subset 上优势更明显。
```

可接受：

```text
标准 ENS 不是第一，但 weather-response 指标更好；
D 消融显示极端事件子集上收益大于普通子集。
```

不可接受：

```text
改变 D 后预测几乎不变；
或 response 方向经常违反常识；
或 +D 与 w/o D 没区别。
```

如果这个实验失败，世界模型叙事会明显变弱。

## 8. 实验四：不确定性

### 8.1 定位

不确定性不是装饰，而是 world model 的自然属性。

遥感未来不是完全确定的：

```text
云和缺测导致观测不确定；
极端天气导致响应不确定；
远期 h 更难预测；
不同地表类型对天气响应不同。
```

因此模型应该不仅输出预测，还输出：

```text
我对这个预测有多确定。
```

### 8.2 怎么做

Stage2 Dynamics 从 deterministic 输出改为：

```text
Dynamics(z_t, D, G, h) -> mu, log_sigma
```

其中：

```text
mu：预测的未来状态均值
sigma：预测不确定性
```

### 8.3 实验指标

| 指标 | 中文解释 | 希望结果 |
|---|---|---|
| uncertainty-error correlation | 模型越不确定的地方是否越容易错 | 正相关，越高越好 |
| coverage | 90% 置信区间是否真的覆盖约 90% 真值 | 接近 0.9 |
| sharpness | 区间是否太宽 | 越窄越好，但不能牺牲 coverage |
| horizon uncertainty | 远期预测是否更不确定 | h 越大，sigma 合理增大 |

### 8.4 可视化

展示三张图：

```text
预测误差图
不确定性图
二者重合区域
```

如果高误差区域和高不确定区域重合，就很有说服力。

### 8.5 可接受结果

理想：

```text
uncertainty-error correlation 明显为正；
远期 h 不确定性更高；
极端天气 subset 不确定性更高；
coverage 接近目标水平。
```

可接受：

```text
不确定性不完美校准，但高不确定区域与高误差区域有明显相关；
可作为可信预测分析。
```

不可接受：

```text
sigma 与 error 无关；
或 sigma 坍塌为常数；
或所有地方都给很大不确定性。
```

不确定性失败不会彻底毁掉主线，但会削弱 world model 的可信度。

## 9. 实验五：G consistency / 地理先验分析

### 9.1 为什么 G 只有 elevation 也能做

G 的地位不是“完整物理法则”，而是：

> 静态地理背景条件。

在当前任务中，`elevation` 足以作为第一版 G，因为它影响气候带、植被类型、温度背景、降水分布和地表响应。

不要把 G 写成：

```text
模型显式知道全部地理物理规律。
```

要写成：

```text
G provides static geographic context for state transitions.
```

中文：

> G 为状态转移提供静态地理背景。

### 9.2 实验设计

| 实验 | 做法 | 意义 |
|---|---|---|
| w/o G | 不输入 elevation | 测 G 总体贡献 |
| shuffled G | batch 内打乱 elevation | 检查模型是否真的依赖正确地理背景 |
| elevation-stratified eval | 按低/中/高海拔分组 | 检查 G 是否在特定地形条件下更有价值 |

### 9.3 可接受结果

理想：

```text
full DGH > w/o G；
shuffled G 明显下降；
高海拔或复杂地形区域 G 收益更大。
```

可接受：

```text
整体 G 收益较小；
但 shuffled G 或 stratified eval 显示 G 在部分区域有用。
```

也可以诚实写：

> 地理先验在短期植被预测中贡献小于 weather forcing，但其任务相关性本身是一个有价值发现。

不可接受：

```text
w/o G、shuffled G、full G 完全一样；
且没有任何分组差异。
```

如果这样，G 不应作为核心贡献，只能作为完整形式化的一部分放轻。

## 10. 实验六：Downstream / Transfer

### 10.1 定位

下游任务不是为了抢主实验，而是证明：

> ObsWorld 学到的 z 不是 EarthNet 特化特征，而是可迁移的地表状态表示。

### 10.2 推荐数据集

优先级：

| 优先级 | 数据集 | 任务 | 理由 |
|---|---|---|---|
| P0 | CropHarvest | 作物分类 / crop type prediction | 与物候、气象、地表状态最一致 |
| P1 | Sen1Floods11 | 洪水/水体分割 | 检验 z 对水体/灾害状态的表示能力 |
| P2 | PASTIS | 作物/地块时序分割 | 时序性强，但工程量更大 |
| P3 | EuroSAT/BigEarthNet | 静态地类分类 | 可做 sanity check，但叙事支撑弱 |

第一篇 AAAI 正文建议只放一个下游任务，优先 CropHarvest。

### 10.3 表格建议

**Table 4: Representation Transfer**

| Encoder | Pretraining | Frozen | Task | Metric |
|---|---|---:|---|---:|
| Random ViT-S | none | yes | CropHarvest | |
| SSL4EO MAE | SSL4EO | yes | CropHarvest | |
| Stage1 encoder | SSL4EO dual MAE | yes | CropHarvest | |
| Stage1.5 encoder | SSL4EO + phi/alignment | yes | CropHarvest | |
| ObsWorld-S | SSL4EO + EarthNet DGH | yes | CropHarvest | |

如果时间允许，再加入 Prithvi / Galileo / SatMAE。否则不要让这些基础模型成为主线依赖。

### 10.4 可接受结果

理想：

```text
Stage1.5 > Stage1；
ObsWorld-S > Stage1.5；
至少在 CropHarvest 上表现优于普通 SSL4EO MAE baseline。
```

可接受：

```text
ObsWorld-S 在下游上不显著提升，但不退化；
主贡献仍由 DGH 和 response 诊断支撑。
```

危险：

```text
DGH 训练后 z 下游性能明显退化；
说明 Stage2 破坏了通用状态表示。
```

如果出现退化，应在 Stage2 冻结 encoder，只训练 dynamics，不让 encoder 被破坏。

## 11. 可视化体系

可视化必须服务实验，不要只放漂亮图。

### 11.1 Fig. 1：方法图

展示：

```text
X_t + phi_t -> Encoder -> z_t
z_t + D + G + h -> Dynamics -> z_{t+h}
z_{t+h} + phi_{t+h} -> Decoder -> X_{t+h}
```

这是全篇核心图。

### 11.2 Fig. 2：标准预测可视化

展示：

```text
历史观测
真实未来
ObsWorld 预测
baseline 预测
误差图
NDVI 变化图
```

对应 Table 1。

### 11.3 Fig. 3：Weather-response 可视化

固定 `z_t, G, h`，改变 D：

```text
真实天气
干旱情景
湿润情景
```

展示未来 NDVI 曲线或 vegetation response map。

对应 Table 3 / response diagnostic。

### 11.4 Fig. 4：Uncertainty 可视化

展示：

```text
预测误差图
不确定性图
二者重合区域
```

对应 uncertainty-error correlation。

### 11.5 Fig. 5：G / horizon 可视化

可选：

```text
h=5, 20, 60, 100 天的预测序列
或低/高海拔区域 response 对比
```

对应 H 和 G 的解释。

## 12. 实验之间的关系

这些实验不是并列散点，而是递进关系。

```text
Step 1: EarthNet 标准预测
  证明方法可运行、可比较。

Step 2: DGH 消融
  证明方法结构不是装饰。

Step 3: Weather-response 诊断
  证明 D 真的改变状态转移。

Step 4: Uncertainty / G analysis
  证明模型不只输出点预测，还具备可信性和地理上下文意识。

Step 5: Downstream transfer
  证明 z 不是单数据集特化特征。
```

如果用一句话概括：

> **Table 1 证明 ObsWorld 能预测；Table 2 证明 ObsWorld 为什么能预测；Table 3 证明 ObsWorld 按外生驱动预测；Table 4/Fig. 4 证明 ObsWorld 知道哪里不确定；下游实验证明 ObsWorld 学到的是可迁移状态。**

## 13. AAAI 篇幅安排

正文 8 页可以这样安排：

| 部分 | 篇幅 |
|---|---:|
| Introduction | 0.75 页 |
| Related Work | 0.5 页 |
| Method | 2 页 |
| Experiments | 4 页 |
| Conclusion / Limitation | 融入实验末尾 |

实验 4 页内部：

| 小节 | 内容 | 篇幅 |
|---|---|---:|
| 5.1 | EarthNet 标准预测：Table 1 + 一组可视化 | 1.1 页 |
| 5.2 | DGH 消融：Table 2 | 0.9 页 |
| 5.3 | Weather-response：Table 3 + Fig. 3 | 0.9 页 |
| 5.4 | Uncertainty + G consistency：小表 + Fig. 4 | 0.6 页 |
| 5.5 | Downstream transfer：小表 | 0.5 页 |

如果篇幅不够，删减顺序：

```text
先删 plug-in 大模型实验；
再删第二个下游任务；
再把 G consistency 放 appendix；
保留 EarthNet + DGH + response + uncertainty。
```

## 14. 是否满足 AAAI 标准

### 14.1 满足的条件

这套叙事满足 AAAI 的关键条件：

1. **问题不是纯工程刷榜**  
   你提出的是遥感世界模型应该如何形式化和验证。

2. **方法和问题一致**  
   state / phi / D / G / h 都在模型结构中有明确位置。

3. **实验能证伪主张**  
   如果 DGH 没用、response 不变、不确定性无关，实验会暴露出来。这是科学性。

4. **即使不是所有指标 SOTA，也有可发表空间**  
   只要标准预测合理，DGH 和 response 证据强，就不是单纯输赢表。

5. **与现有工作有清晰切割**  
   EO-WM 偏 diffusion future video + weather response；SkySense/Prithvi/Galileo 偏 foundation representation；ObsWorld 主打成像解耦状态动力学和 DGH 可诊断机制。

### 14.2 不满足的情况

如果出现下面情况，就不建议强投 AAAI 主会：

```text
EarthNet 标准预测明显弱于简单 baseline；
DGH 消融无增益；
改变 D 后预测不变；
uncertainty 与 error 无关；
Stage2 破坏 z 的下游迁移。
```

这种情况下需要复盘 Stage2，而不是靠叙事硬撑。

### 14.3 可容错情况

下面情况仍可接受：

```text
像素指标低于 EO-WM；
G 整体贡献较小；
Stage1.5 非线性 phi 泄漏仍存在；
下游只做一个任务；
大模型 plug-in 没时间做。
```

但前提是：

```text
D 和 h 有明确贡献；
weather-response 诊断有优势；
标准预测不崩；
论文诚实报告限制。
```

## 15. 最终写作模板

### 15.1 Abstract 逻辑

```text
Remote sensing forecasting is often evaluated by future-pixel similarity, yet future pixels are only observations of underlying land-surface states under specific acquisition conditions. We argue that an Earth-observation world model should instead learn how land-surface states transition under exogenous drivers, geographic priors, and forecast horizons. We introduce ObsWorld, an imaging-decoupled land-surface state dynamics model. ObsWorld estimates a state from biased satellite observations, predicts its future transition conditioned on D/G/h, and decodes the predicted state into future observations with uncertainty. On EarthNet2021, ObsWorld achieves competitive standard forecasting performance while providing stronger driver-response fidelity, interpretable DGH ablations, calibrated uncertainty, and transferable state representations.
```

### 15.2 Introduction 末段

```text
Our goal is not merely to synthesize visually plausible future satellite images. Instead, we use future observation prediction as a standard protocol to test whether the model has learned physically meaningful land-surface transitions. This distinction motivates both our architecture and our evaluation: beyond standard EarthNet metrics, we evaluate DGH ablations, weather-response diagnostics, uncertainty-error alignment, and representation transfer.
```

### 15.3 实验章节开头

```text
We organize experiments around the claims of ObsWorld. First, we evaluate standard future-observation forecasting on EarthNet2021 for comparability. Second, we ablate D/G/h to test whether the proposed conditioning variables contribute to state dynamics. Third, we evaluate weather-response diagnostics to determine whether predictions change consistently under different external forcing. Fourth, we analyze uncertainty and geographic consistency. Finally, we test whether the learned state representation transfers to downstream land-surface tasks.
```

中文解释：

> 我们的实验不是为了堆指标，而是逐条验证 ObsWorld 的定义：能预测、用了 DGH、会响应驱动、知道不确定性、状态可迁移。

## 16. 最终判断

这套方案可以支撑 AAAI 叙事。

但它的成功条件不是“EarthNet 所有指标第一”，而是：

1. EarthNet 标准预测具有竞争力；
2. D 和 h 的机制贡献明确；
3. weather-response 诊断能显示 ObsWorld 比普通预测器更会响应外生驱动；
4. uncertainty 至少与误差正相关；
5. z 的迁移不退化，最好提升；
6. 论文诚实说明 G 和 Stage1.5 解耦的边界。

如果这些条件基本满足，即使 EO-WM 在像素生成质量上更强，ObsWorld 仍然有清晰的 AAAI 价值：

> **它提供的不是另一个更大的未来帧生成器，而是一套可诊断、可解释、可迁移的遥感地表状态动力学建模框架。**
