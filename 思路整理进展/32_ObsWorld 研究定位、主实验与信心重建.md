---
title: "ObsWorld 研究定位、主实验与信心重建"
created: 2026-07-08
scope: "回应 Stage2 / 主实验 / EO-WM / 大模型对比 / 下游任务的关键疑问"
status: "建议与 31 号文档配套阅读"
---

# ObsWorld 研究定位、主实验与信心重建

## 0. 一句话结论

ObsWorld 的创新不在“使用 SSL4EO 预训练再在 EarthNet 微调”这个训练范式本身，而在：

> **把遥感 future forecasting 从“预测未来像素”重构为“成像解耦状态在外生驱动、地理先验和预测跨度条件下的可诊断动力学”。**

所以主实验不能只是“EarthNet2021 精度表”，而应是：

> **EarthNet2021 标准预测 + DGH-response 诊断 + 泛化/迁移验证。**

EarthNet2021 是主实验平台，不是论文全部赛道；EO-WM 是强参照，不是叙事中心。

## 1. pretrain-finetune 是否没有新意

### 1.1 训练范式本身没有新意，这是正常的

`pretrain -> finetune` 是遥感基础模型和视觉模型的常规范式。SatMAE、SkySense、Prithvi-EO-2.0、Galileo、TerraMind 都是先大规模预训练，再在任务/benchmark 上评估或微调。

因此，论文不能把“我预训练了再微调”当贡献。

### 1.2 真正的新意在“预训练后的结构化动力学”

你要强调的不是：

```text
我们也做了 SSL4EO pretraining。
```

而是：

```text
我们把预训练 encoder 的表征组织成一个可被检验的地表状态空间，
并在这个状态空间里显式建模 D/G/h 条件下的状态转移。
```

创新点应写成三层：

1. **状态-观测分离**：影像不是世界本身，z 是地表状态，phi 是成像条件。
2. **DGH 条件动力学**：外生驱动 D、地理先验 G、预测跨度 h 进入动力学模块，而不是被混成普通输入通道。
3. **诊断式评估协议**：不仅报像素预测分数，还检验 weather-response、horizon response、D/G 消融、uncertainty calibration。

### 1.3 AAAI 是否接受这种叙事

可以支撑，但前提是你不要把它写成“又一个 backbone + fine-tune”。AAAI 更容易接受的是：

```text
一个问题形式化 + 一个机制化模型 + 一组能证伪该机制的实验协议。
```

换句话说，AAAI 的故事不是“我模型大、精度高”，而是“我定义并验证了遥感世界模型中哪些变量应该进入状态、观测和动力学”。

## 2. 我们的观点与主实验究竟是什么

### 2.1 文章核心观点

建议固定成这句话：

> **Future EO forecasting should evaluate whether a model learns physically meaningful land-surface transitions under exogenous forcing, rather than only whether it reconstructs future pixels.**

中文：

> **未来遥感预测不应只评价未来像素是否相似，而应检验模型是否学到了外生驱动下物理有意义的地表状态转移。**

### 2.2 主实验不是“下游任务”，而是“标准预测平台上的动力学验证”

主实验应是：

```text
EarthNet2021 weather-conditioned forecasting
```

但论文解释应写成：

```text
我们用 EarthNet2021 作为标准观测协议，检验模型能否在给定 weather forcing、DEM 和历史观测的情况下，预测未来地表状态的观测投影。
```

也就是：

```text
预测 = 检验动力学的标准接口
不是论文的最终哲学目标
```

### 2.3 文章特点怎么体现

不要只靠 Table 1 精度表体现。应靠四个实验共同体现：

| 实验                  | 支撑什么观点                    |
| ------------------- | ------------------------- |
| EarthNet 标准预测       | 方法不是空概念，能在标准任务成立          |
| DGH 消融              | D/G/h 确实贡献动力学，而不是摆设       |
| Weather-response 诊断 | 模型真的响应驱动，而不是记忆季节均值        |
| 下游/泛化任务             | z 不是任务特化像素特征，而是有迁移价值的状态表示 |

如果只有第一项，你会被困在 EO-WM / Earthformer 的赛道里；四项一起，才是 ObsWorld 的赛道。

## 3. 28M 参数怎么和 387M EO-WM 比

### 3.1 不要假装这是公平参数对比

EO-WM 的 diffusion backbone 是 387M。你的当前模型不到 28M，直接比像素生成质量确实不公平。

所以主表必须报告：

```text
Params, training data, inference cost, standard metrics, response metrics
```

不要只报 ENS/MAE。

### 3.2 小模型的可防守位置

你可以把 ObsWorld 定位成：

```text
compact mechanistic world model
```

重点比较：

1. **参数效率**：在远小于 diffusion backbone 的条件下接近标准预测性能。
2. **响应 fidelity**：在 DHR/PDC/NDVI-response 等指标上有竞争力。
3. **机制透明度**：D/G/h 可消融、可替换、可做 scenario sweep。
4. **可插拔性**：Dynamics/Conditioning 可以接到更强 encoder/backbone。

如果像素指标输给 EO-WM，这是预期内；只要 response/ablation/efficiency 赢或持平，叙事仍成立。

### 3.3 必须补一个中等规模版本

如果资源允许，建议至少做一个 `ObsWorld-S`：

```text
encoder: ViT-S/16 约 22M
dynamics + decoder: 10-30M
total: 40-60M
```

这不一定要追到 387M，但比 28M 更像顶会实验规模。

## 4. 单数据集下 h 是否需要改

需要。

EarthNet 的时间间隔稳定，但 horizon 难度不固定。单数据集下 h 反而更容易定义清楚。

建议两种路线二选一：

### 4.1 如果按 EarthNet 标准输出 20 帧

```text
h = {5, 10, 15, ..., 100} days
```

每个 target frame 都有 lead-time embedding。这样最贴合 EarthNet 标准协议。

### 4.2 如果先做轻量 Stage2

采样少数 horizon：

```text
h = {5, 10, 20, 30, 60, 100}
```

训练时随机抽 h，预测对应未来帧。正文做 `w/o h` 或 `fixed h` 消融。

### 4.3 不建议只设一个 h

如果只设一个 h，DGH 里的 H 就变成装饰项，论文贡献会少一块。

## 5. 是否太看重 EO-WM

是的，31 号文档为了回答 EarthNet 主实验问题，EO-WM 权重略高。更合理的对标矩阵应是三类。

### 5.1 A 类：时空预测/植被预测模型

这是 EarthNet 主表里的主要对手：

- Persistence / climatology
- ConvLSTM / PredRNN / SimVP
- Earthformer
- Contextformer / GreenEarthNet-style
- EO-WM

### 5.2 B 类：遥感基础模型

这类不一定做 EarthNet 未来预测，但必须在下游/表征实验里对标：

- SatMAE
- SkySense
- Prithvi-EO-2.0
- Galileo
- TerraMind
- DOFA / CROMA / Clay 视可用性选择

### 5.3 C 类：世界模型/机制模型

这是叙事参照，不一定都能直接跑：

- Dreamer / JEPA / V-JEPA
- EO-WM
- RS-WorldModel
- Remote Sensing-Oriented World Model

### 5.4 EO-WM 应该如何出现

EO-WM 不是“我们唯一要打败的人”。它在论文里应该是：

```text
最接近的 weather-driven EO world model 参照
```

但不是：

```text
全文唯一中心对手
```

你可以明确说：EO-WM 的长处是 diffusion video forecasting 和 weather-response diagnostic；ObsWorld 的长处是状态-观测分离、D/G/h 模块化、轻量机制和可插拔动力学。

## 6. 主实验为什么仍然用 EarthNet2021

因为你需要一个公开、标准、可复现的平台来支撑第一张表。EarthNet2021 正好提供：

1. 历史 Sentinel-2。
2. 未来 Sentinel-2。
3. weather forcing。
4. DEM。
5. 标准 intercomparison。

这几乎天然对应你的：

```text
X_t + D + G + h -> X_{t+h}
```

但要避免被困住，正文必须这样组织：

```text
§5.1 EarthNet standard forecasting: sanity + comparability
§5.2 DGH response diagnostics: our real main claim
§5.3 ablations: mechanism verification
§5.4 transfer/generalization: world-model-like representation
```

这样 EarthNet 是入口，不是牢笼。

## 7. 下游任务怎么选

下游任务要服务你的主线，不能越多越好。

### 7.1 推荐最小组合

正文做 1 个，附录再做 1 个。

| 优先级 | 数据集 | 任务 | 为什么适合 |
|---|---|---|---|
| P0 | CropHarvest | 作物分类 / crop type prediction | 全球、时序、与气象/物候强相关，最贴近 DGH |
| P1 | Sen1Floods11 | 洪水/水体分割 | 检验 z 是否编码水体和灾害状态，但与当前植被主线略远 |
| P2 | PASTIS-R / PASTIS | 作物/地块时序分割 | 时序性强，但接入工程略重 |
| P3 | BigEarthNet / EuroSAT | 地类分类 | 简单 sanity check，但太静态，不足以支撑动力学 |

### 7.2 下游训练协议

建议统一成：

```text
freeze encoder -> extract z -> train lightweight task head
```

然后加一个少量微调设置：

```text
linear probe / frozen head
small-lr finetune
```

不要把下游做成大型工程。它的作用是证明 `z` 有迁移价值，不是抢主实验。

### 7.3 CropHarvest 具体做法

```text
input: Sentinel time series (+ optional weather if dataset已有)
encoder: ObsWorld encoder 提取 z
head: temporal pooling + MLP / small Transformer
metric: F1, accuracy, macro-F1
comparison: SatMAE/Prithvi/Galileo/Presto 可引用或复现可用模型
```

### 7.4 Sen1Floods11 具体做法

```text
input: S1/S2 image
encoder: ObsWorld encoder
head: lightweight U-Net / segmentation head
metric: IoU, F1
comparison: Prithvi / CROMA / DOFA / random init / SSL4EO MAE baseline
```

如果只能做一个，我更推荐 CropHarvest，因为它和“外生驱动的地表状态”更一致。

## 8. 参数低是否没信心

低参数不是死刑，但需要改叙事。

不应说：

```text
我们是最强遥感大模型。
```

应说：

```text
我们提出一个机制化、可诊断、可插拔的遥感状态动力学框架，并在小规模模型上验证它。
```

顶会可以接受“小模型验证机制”，但实验必须让机制清楚：

1. 加 D 明显改善 response。
2. 加 h 改善多跨度。
3. Stage1.5 比普通 MAE 更适合作为 dynamics state。
4. 小模型在参数效率上合理。
5. 框架可插到更强 backbone 上。

如果这五条成立，信心是够的。

## 9. 是否要“加入到别人家的大模型”

建议作为 **附加实验 / 可插拔性实验**，不要作为主实验主线。

### 9.1 为什么不作为主线

如果主线变成：

```text
Prithvi + our module
SkySense + our module
Galileo + our module
```

工程量会暴涨，而且文章会从“ObsWorld 方法”变成“插件 benchmark”。第一篇不建议这么写。

### 9.2 但应该做一个最小可插拔实验

选一个容易接入的公开 backbone，例如：

```text
SatMAE / SSL4EO-MAE / Prithvi-EO-2.0-300M
```

实验设计：

```text
Frozen backbone features z_t
  + ObsWorld-Dynamics(D,G,h)
  -> future z / future NDVI
```

对比：

```text
backbone feature + MLP horizon head
backbone feature + generic Transformer head
backbone feature + ObsWorld DGH Dynamics
```

如果 `ObsWorld DGH Dynamics` 赢，就说明你的贡献不是某个小 encoder，而是“动力学机制”。

### 9.3 终版模型怎么定义

建议论文里定义三版：

| 名称 | 含义 | 用途 |
|---|---|---|
| ObsWorld-S | 你自己的小/中等模型端到端 | 主方法、主实验 |
| ObsWorld-DGH plug-in | 把 DGH dynamics 接到外部 backbone | 可插拔性实验 |
| ObsWorld-G | 多数据集训练版 | 泛化/附录 |

正文主角仍是 `ObsWorld-S`，插件实验只证明机制通用。

## 10. 最终实验蓝图

### 主文实验

1. **EarthNet2021 standard forecasting**
   - 对比 Earthformer / Contextformer / EO-WM / ConvLSTM / SimVP。
   - 指标：ENS、MAD、OLS、EMD、SSIM、NDVI-MAE、DHR。

2. **DGH mechanism ablation**
   - `AR baseline`, `+D`, `+h`, `+D+h`, `full DGH`, `w/o Stage1.5`。

3. **Weather-response diagnostic**
   - Extreme summer / drought / seasonal matched pair / forcing sweep。

4. **Downstream transfer**
   - 首选 CropHarvest；备选 Sen1Floods11。

### 附录实验

1. EarthNet+SSL4EO 联合训练泛化。
2. 更多下游任务。
3. plug-in 到 Prithvi/SatMAE/Galileo 特征。
4. D 内部变量消融：precip/temp/VPD/radiation。

## 11. 你现在应该怎么重建信心

你担心的是对的：如果目标是“28M 模型在 EarthNet 像素指标上打败 387M diffusion”，那确实危险。

但这不是唯一、也不是最合理的目标。

更合理的目标是：

```text
用一个 compact model 证明：
1. 显式区分 state / observation / forcing 是有意义的；
2. D/G/h 条件能带来可诊断的动力学响应；
3. 这些响应不是普通 future-frame predictor 自动保证的；
4. 该机制可以迁移或插入更大遥感 backbone。
```

这个目标比“刷 EarthNet 第一名”更像 AAAI。

## 12. 参考来源

- EarthNet2021: https://arxiv.org/abs/2104.10066
- EarthNet2021 CVPRW paper: https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf
- EO-WM: https://arxiv.org/abs/2606.27277
- GreenEarthNet / Contextformer: https://arxiv.org/abs/2303.16198
- Earthformer: https://arxiv.org/abs/2207.05833
- SkySense: https://arxiv.org/abs/2312.10115
- Prithvi-EO-2.0: https://arxiv.org/abs/2412.02732
- Galileo: https://arxiv.org/abs/2502.09356
- SatMAE: https://proceedings.neurips.cc/paper_files/paper/2022/hash/01c561df365429f33fcd7a7faa44c985-Abstract-Conference.html
- TerraMind: https://arxiv.org/abs/2504.11171
