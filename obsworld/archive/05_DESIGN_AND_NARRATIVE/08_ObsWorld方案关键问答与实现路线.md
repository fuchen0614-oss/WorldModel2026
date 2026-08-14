# 08 ObsWorld 方案关键问答与实现路线

## 0. 英文术语速查

后文保留英文术语，是为了和论文写作、代码目录、模型命名保持一致；括号里的中文是实际含义。

| 英文术语 | 中文意思 | 一句话解释 |
|---|---|---|
| Observation Encoder | 观测编码器 | 把历史遥感影像编码成地表状态证据 |
| Imaging Condition Encoder | 成像条件编码器 | 编码传感器、云、季节、太阳角等“怎么拍”的信息 |
| Land-Surface State Space | 地表状态空间 | 表示土地覆盖、水体、植被、建筑、灾害等地表状态 |
| State Dynamics Module | 状态动力学模块 | 预测地表状态如何在外生驱动和地理先验下变化 |
| Observation Decoder | 观测解码器 / 观测模型 | 把状态按指定成像条件生成像素观测 |
| Task Heads | 任务头 | 用同一个状态空间服务洪水、土地覆盖、建筑变化等任务 |
| field_mask | 字段有效性掩码 | 标记字段是否真实存在，避免缺失字段参与 loss |
| driver sensitivity | 驱动敏感性 | 检查模型是否真的响应降雨、洪水、灾害等驱动 |
| imaging condition swap | 成像条件替换 | 固定地表状态，替换传感器/云/季节等条件，看观测输出是否合理变化 |
| physical consistency | 物理一致性 | 检查预测是否符合坡度、水系、道路、土地覆盖等地理约束 |

## 1. 总览问题

### Q1. 这个方案一句话是什么？

ObsWorld 是一个**成像条件解耦的地表状态动力学遥感世界模型**。它先从多源、有偏的遥感像素观测中估计成像无关地表状态，再在外生驱动和地理先验条件下预测未来地表状态，最后用未来成像条件生成未来像素观测。

建议复述为：

```text
我们不把遥感图像当作世界本身，而把它当作地表状态在特定成像条件下的有偏观测。
ObsWorld 建模地表状态、状态如何演化、状态如何被观测。
```

### Q2. 它为什么叫遥感 world model？

因为它具备 world model 的核心结构：从观测中形成内部状态，学习状态随时间和条件变化的规律，并能进行未来 rollout。遥感里的条件不是机器人 action，而是外生驱动、地理先验和成像条件。

本文的“世界”定义为地表状态场，而不是图像流。像素只是观察这个世界的方式。

### Q3. 它和普通遥感时序预测有什么区别？

普通时序预测通常学习：

```text
过去影像 -> 未来影像
```

ObsWorld 学习：

```text
过去影像 + 成像条件 -> 当前地表状态
当前地表状态 + 外生驱动 + 地理先验 -> 未来地表状态
未来地表状态 + 未来成像条件 -> 未来影像
```


```
输入：
过去 S1/S2 影像
过去成像条件
降雨/洪水事件
DEM、坡度、距河流
未来传感器和云条件

输出：
未来洪水状态图
非水体 -> 洪水的转移图
指定传感器下的未来观测图    1
不确定性图
```

区别在于：ObsWorld 把“地表真的变了”和“拍摄条件变了”分开，并且评估不只看像素相似度，还看状态转移、驱动响应、物理一致性和不确定性。

### Q4. 它和像素生成模型有什么区别？

像素生成模型的中心目标是生成更真实、更清晰的图像。ObsWorld 的中心目标是预测地表状态如何演化。

未来像素在 ObsWorld 中有三个作用：

1. 作为观测模型输出；
2. 作为和 EarthNet、生成模型、未来预测模型对比的接口；
3. 作为可视化证据。

不要说“我们生成未来像素，所以是 world model”。要说“我们预测未来状态，并能在指定成像条件下生成未来观测”。

### Q5. 它和 WorldRS 的关系是什么？

WorldRS 的外生驱动状态转移思想被吸收到 ObsWorld 的 State Dynamics Module（状态动力学模块）中。

最准确的关系是：

```text
ObsWorld = 状态估计 + 状态动力学 + 观测模型
WorldRS = ObsWorld 中状态动力学和驱动响应实验的核心来源
```

所以 WorldRS 不再是并列主线，而是 ObsWorld 的动力学心脏。

### Q6. 它和 output/06 的关系是什么？

`output/06_最新主线方案与实验设计.md` 已经完成了方向选择：采用 ObsWorld-B+，即 ObsWorld 三柱结构为主线，WorldRS 外生驱动为关键能力验证。

本文件把 06 里的方案改成问答式执行手册。遇到“到底做什么、怎么实现、先做哪个数据集、怎么回答审稿人”这类问题，优先查 08。

## 2. 叙事问题

### Q7. 整体论文叙事应该怎么讲？

建议按六段讲。

1. 现有遥感模型主要理解或生成观测，但遥感观测不是世界本身。
2. 遥感像素变化同时来自地表真实变化和成像条件变化。
3. 遥感 world model 应把地表状态、状态动力学和观测模型分开。
4. ObsWorld 从有偏观测估计成像无关状态，在外生驱动和地理先验下预测未来状态。
5. 未来像素由未来状态和未来成像条件生成，作为观测出口。
6. 通过状态转移、驱动敏感性、成像条件替换、物理一致性和校准实验验证 world model 能力。

### Q8. 审稿人最可能认可的创新点是什么？

最可能被认可的是“遥感 world model 的结构性切分”：

- 世界是地表状态，不是图像流；
- 成像条件解释观测偏置；
- 外生驱动进入状态动力学；
- 像素预测变成观测模型而不是唯一目标；
- 用可证伪实验验证驱动响应和物理一致性。

这比单说“我们训练了一个遥感世界模型”更稳。

### Q9. 审稿人最可能质疑什么？

最可能质疑五点。

1. 这是不是普通视频预测？
2. 这是不是 RS-WorldModel / TerraMind 的变体？
3. 成像无关状态如何证明？
4. 外生驱动字段是否真的有效？
5. 多数据集训练是不是工程拼盘？

对应应对是：状态转移主指标、驱动替换实验、成像条件替换实验、`field_mask` schema、每个数据集只服务一个能力。

### Q10. 如何避免被认为只是换壳的视频预测？

必须在任务定义、模型结构和实验指标三处一起切开。

任务定义上，不写“预测未来帧”，而写“预测未来地表状态及其观测投影”。模型结构上，显式写出 `Observation Encoder（观测编码器） -> State Space（状态空间） -> Dynamics（动力学） -> Observation Decoder（观测解码器）`。实验上，不只报 SSIM/PSNR，还要报状态转移 F1、驱动响应 KL、物理一致性违规率、ECE/AUSE。

一句话回答：

```text
普通视频预测直接预测未来画面；ObsWorld 先预测地表状态如何变，再解释在某个未来成像条件下会看到什么。
```

## 3. 输入输出问题

### Q11. 模型输入到底是什么？

最完整输入是：

```text
X_{t-k:t}: 历史遥感影像
phi_{t-k:t}: 历史成像条件
D: 外生驱动
G: 地理先验
h: 预测跨度
phi_{t+h}: 未来成像条件
field_mask: 字段有效性掩码，表示字段是否真实存在
```

第一版不要求每个样本都有所有字段，但 dataloader 必须告诉模型哪些字段真实存在。

### Q12. 模型输出到底是什么？

主输出是：

```text
S_{t+h}: 未来地表状态
Delta S: 状态转移
U: 不确定性
```

辅助但重要的输出是：

```text
X_hat_{t+h}: 未来像素观测
R: 物理一致性或结构化解释
```

像素输出不要删，但不要让它变成唯一主输出。

### Q13. 什么是成像条件？

成像条件是影响“同一地表状态会被拍成什么样”的因素。

包括：

- 传感器类型；
- 光学/SAR 模态；
- 波段；
- 空间分辨率；
- 观测时间；
- 季节；
- 云量和云掩膜；
- 太阳高度角；
- 视角；
- SAR 极化和入射角；
- 产品级别。

第一版最低限度也要有 `sensor + timestamp/season + cloud/valid mask + bands`。

### Q14. 什么是地表状态？

地表状态是比像素更接近“地表真实情况”的表示。

它可以包括：

- 土地覆盖；
- 植被状态；
- 水体/洪水状态；
- 建筑存在和变化；
- 灾害损伤等级；
- 作物类型或物候；
- 连续潜状态，例如湿度、绿度、扰动强度。

建议用“双层状态”：

```text
显式语义状态 S_t + 连续潜状态 z_t
```

这样既能评估，又能保留像素细节。

### Q15. 什么是外生驱动？

外生驱动是影响地表状态演化、但不是模型或智能体自己产生的外部过程。

例子：

- 降雨；
- 温度；
- 洪水事件；
- 灾害类型；
- 极端天气；
- 时间跨度；
- 季节转换；
- 城市扩张强度；
- 人类活动 proxy。

注意：不要把任务标签偷偷塞进驱动。`driver_type=flood` 可以表示事件类型，但不能直接告诉模型哪个像素被淹。

### Q16. 什么是地理先验？

地理先验是影响状态变化是否合理的空间背景。

例子：

- DEM；
- 坡度；
- 永久水体；
- 距河流距离；
- 距道路距离；
- 距已有建筑距离；
- 气候带；
- 土地覆盖先验；
- 城市区域 mask。

地理先验可以作为输入，也可以作为独立评估器。第一版不要把它写成绝对物理定律，应写成软约束。

### Q17. 哪些字段是必须字段，哪些是可选字段？

必须字段：

```text
sample_id
dataset_name
timestamp 或相对时间顺序
sensor
bands
X
valid_mask
field_mask（字段有效性掩码）
h
```

强建议字段：

```text
phi
season
cloud_mask
lat/lon
state_label 或 weak state
dem
slope
land_cover_prior
```

任务相关字段：

```text
precipitation
temperature
extreme_event_flag
disaster_type
distance_to_water
distance_to_urban
human_activity_proxy
```

缺失字段用 `field_mask=0`，不要用零值冒充真实值。

## 4. 数据集问题

### Q18. 推荐优先使用哪些数据集？

第一版优先：

1. SSL4EO-S12 v1.1；
2. EarthNet2021；
3. DynamicEarthNet；
4. Sen1Floods11 / SEN12-FLOOD / C2S-MS Floods 至少一个。

第二阶段再加：

1. SpaceNet7 或 xBD 二选一；
2. PASTIS；
3. BigEarthNet / SEN12MS。

不要因为数据集名字多就全加。每个数据集必须对应一个能力。

### Q19. 每个数据集放在哪个训练阶段？

| 阶段 | 数据集 |
|---|---|
| 阶段 1 观测编码预训练 | SSL4EO-S12 v1.1、BigEarthNet、SEN12MS、PASTIS |
| 阶段 2 状态动力学 | EarthNet2021、DynamicEarthNet、PASTIS、SpaceNet7 |
| 阶段 3 观测模型 | EarthNet2021、DynamicEarthNet、SSL4EO、C2S-MS Floods |
| 阶段 4 任务评估 | Sen1Floods11、SEN12-FLOOD、C2S-MS、DynamicEarthNet、SpaceNet7、xBD |

第一版可以合并阶段 2 和阶段 3 的部分训练，但文档和代码配置里要分清目标。

### Q20. SSL4EO-S12 v1.1 怎么用？

用作观测编码和成像解耦预训练主数据。

它适合学：

- Sentinel-1 / Sentinel-2 多模态；
- 多季节观测；
- DEM / LULC / NDVI 弱辅助；
- masked reconstruction；
- 跨模态状态一致性。

它不适合单独证明外生驱动状态动力学，因为它没有强事件驱动。

可用链接：[SSL4EO-S12 v1.1 GitHub](https://github.com/DLR-MF-DAS/SSL4EO-S12-v1.1)。

### Q21. EarthNet2021 怎么用？

用作未来像素观测预测主数据。

它适合证明：

- Observation Decoder（观测解码器）能输出未来观测；
- 未来天气/地形可作为条件；
- 像素预测能和现有 Earth surface forecasting 方法比较。

但 EarthNet 的状态标签较弱，所以要补 NDVI、粗 LULC 或状态伪标签。不要把 EarthNet 单独当成完整 world model 证据。

链接：[EarthNet](https://www.earthnet.tech/)，[arXiv](https://arxiv.org/abs/2104.10066)。

### Q22. DynamicEarthNet 怎么用？

用作土地覆盖/季节状态转移主数据。

它适合构造：

```text
S_t -> S_{t+h}
Delta S
source month -> target month
```

它能证明状态动力学，不只是像素预测。主要风险是 Planet 数据许可和数据获取成本，需要早确认。

链接：[DynamicEarthNet arXiv](https://arxiv.org/abs/2203.12560)，[代码](https://github.com/aysim/dynnet)。

### Q23. 洪水数据集怎么用？

洪水数据是外生驱动实验的第一主战场。

推荐用途：

- Sen1Floods11：SAR 洪水识别和事件级测试；
- SEN12-FLOOD：S1/S2 多模态洪水序列；
- C2S-MS Floods：近同期 S1/S2、水体标签、S2 云/阴影 mask。

需要补：

- DEM；
- slope；
- permanent water；
- distance_to_water；
- event metadata；
- 可选降雨。

重点实验：

```text
真实洪水驱动 vs 空驱动 vs 错误驱动
有 DEM/slope/water prior vs 无 G
光学/SAR 条件替换
```

链接：[Sen1Floods11](https://openaccess.thecvf.com/content_CVPRW_2020/html/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.html)，[SEN12-FLOOD](https://cmr.earthdata.nasa.gov/search/concepts/C2781412140-MLHUB.html)，[C2S-MS Floods](https://source.coop/c2sms/c2smsfloods)。

### Q24. SpaceNet7、xBD、PASTIS、BigEarthNet、SEN12MS 分别适合做什么？

| 数据集 | 适合用途 |
|---|---|
| SpaceNet7 | 城市扩张、建筑 footprint 时间序列、慢变量状态变化 |
| xBD | 灾前/灾后建筑损毁，单步冲击响应 |
| PASTIS / PASTIS-R | 作物、物候、农业语义状态，S1/S2 时序 |
| BigEarthNet | 大规模 S1/S2 多标签预训练或语义辅助 |
| SEN12MS | S1/S2/MODIS LULC 多模态预训练 |

第一版不要同时做 SpaceNet7 和 xBD。建议二选一：如果想强调慢变量动力学，选 SpaceNet7；如果想强调灾害冲击响应，选 xBD。

### Q25. 为什么不把所有数据集直接拼起来？

因为它们的监督目标、时间结构、空间分辨率、许可、标签本体和驱动字段都不一样。

直接拼会导致三个问题：

1. 模型收到冲突监督；
2. 论文像工程合集；
3. 审稿人看不清每个数据集证明什么。

正确做法是统一 schema，但不统一所有 loss。每个样本用 `field_mask` 激活自己有真值的字段。

### Q26. 每个数据集需要补哪些字段？

简化版如下：

| 数据集 | 最需要补 |
|---|---|
| SSL4EO | `phi`、季节、云/valid mask、弱状态 |
| EarthNet | 粗状态、未来 `phi`、NDVI/LULC 辅助 |
| DynamicEarthNet | DEM、气候带、季节、天气 proxy |
| 洪水数据 | DEM、坡度、永久水体、距河流、事件/降雨 |
| SpaceNet7 | 道路、已有建筑距离、增长率 |
| xBD | 灾害类型、强度 proxy、建筑先验、DEM |
| PASTIS | 天气、物候阶段、地块先验 |
| BigEarthNet / SEN12MS | `phi`、季节、弱语义状态 |

### Q27. 字段怎么获取、对齐和缓存？

推荐流程：

```text
1. 下载原始数据
2. 生成 manifest
3. 解析 timestamp/sensor/bands
4. 构建 phi
5. 裁剪外部地理图层
6. 派生 slope/distance/state/Delta S
7. 重投影和重采样
8. 写入 cache
9. 生成 field_mask
10. dataloader 仅读缓存
```

训练时不要在线调用外部服务。公开时也不要重分发受限影像，发布索引、脚本、schema 和评估协议即可。

## 5. 训练阶段问题

### Q28. 整体训练分几个阶段？

建议四阶段：

1. 观测编码与成像解耦预训练；
2. 状态动力学训练；
3. 观测模型训练；
4. 任务微调与世界模型评估。

第一版可以工程上合并部分阶段，但论文描述和配置文件要保持四阶段逻辑。

### Q29. 第一阶段训练什么？

训练 Observation Encoder（观测编码器）、Imaging Condition Encoder（成像条件编码器）和初始 State Space（状态空间）。

输入：

```text
多模态影像 + 成像条件 + mask + 弱标签
```

输出：

```text
token / z_t / 初始状态 / 重建观测
```

主要 loss：

```text
masked reconstruction
cross-modal consistency
contrastive loss
semantic auxiliary loss
phi decorrelation / condition reconstruction
```

### Q30. 第二阶段训练什么？

训练 State Dynamics Module（状态动力学模块）。

输入：

```text
s_t 或历史状态序列
D
G
h
```

输出：

```text
s_{t+h}
S_{t+h}
Delta S
U
```

主要 loss：

```text
state CE/Focal/Dice
state latent L1/L2
transition loss
driver sensitivity loss（驱动敏感性损失）
geo consistency loss（地理先验一致性损失）
```

### Q31. 第三阶段训练什么？

训练 Observation Decoder（观测解码器 / 观测模型）。

输入：

```text
s_{t+h}
phi_{t+h}
target sensor/bands
valid_mask
```

输出：

```text
X_hat_{t+h}
observation uncertainty
```

主要 loss：

```text
L1 / L2 / Charbonnier
SSIM
spectral angle
masked pixel loss
feature loss
condition consistency
```

第一版用轻量 decoder，不要一开始上扩散。

### Q32. 第四阶段训练什么？

第四阶段主要是任务微调和评估。

任务包括：

- 洪水；
- LULC；
- 未来状态；
- 建筑变化；
- 灾害损毁；
- 未来像素；
- 跨成像条件泛化。

这一阶段的重点不是多训几个 head，而是固定协议、跑对比、跑消融、做可视化。

### Q33. 每阶段输入、输出和损失是什么？

| 阶段 | 输入 | 输出 | 损失 |
|---|---|---|---|
| 1 | `X, phi, mask, weak label` | `z_t, s_t, X_rec` | MAE、对齐、对比、语义辅助 |
| 2 | `s_t, D, G, h` | `s_{t+h}, S_{t+h}, Delta S` | CE/Focal/Dice、driver、geo |
| 3 | `s_{t+h}, phi_future` | `X_hat_future` | L1/L2、SSIM、SAM、masked pixel |
| 4 | 任务输入 | 任务输出、指标 | 任务 loss、校准、评估协议 |

### Q34. 每阶段结束后应该得到什么产物？

阶段 1：

```text
可复用 encoder
phi encoder
初始状态表示
预训练 checkpoint
```

阶段 2：

```text
dynamics checkpoint
state transition head
driver/geo 消融结果
```

阶段 3：

```text
observation decoder
未来像素预测结果
成像条件替换可视化
```

阶段 4：

```text
主实验表
消融表
世界模型能力实验
失败案例
最终论文图表
```

## 6. 模型与代码问题

### Q35. 代码层大概怎么安排？

代码分成八层：

```text
configs
data
field_builders
models
losses
tasks
eval
scripts
```

其中最关键的是 `field_builders`、`models/dynamics` 和 `eval/protocols`。这三块决定论文是不是 ObsWorld，而不是普通多任务训练。

### Q36. 推荐使用什么深度学习框架？

推荐：

- PyTorch；
- PyTorch Lightning 或 Lightning Fabric；
- timm；
- Hugging Face Transformers；
- einops；
- segmentation_models_pytorch；
- torchgeo；
- rasterio / xarray / geopandas。

如果团队熟悉裸 PyTorch，也可以不用 Lightning，但必须保证配置、日志、checkpoint 和多阶段训练可复现。

### Q37. 推荐使用哪些现成模型或代码库？

推荐复用：

- [Prithvi-EO-2.0](https://github.com/NASA-IMPACT/Prithvi-EO-2.0)；
- [TerraMind](https://github.com/ibm/terramind) 作为相关工作和生成对比参考；
- [SatMAE](https://sustainlab-group.github.io/SatMAE/)；
- CROMA、DOFA、Scale-MAE；
- ConvLSTM / Earthformer / EarthNet baseline；
- U-Net / UPerNet / DeepLab；
- torchgeo datasets 和 transforms 思路。

第一版可以先不用 foundation model 权重，只用中等规模 ViT/MAE 跑通。大模型编码器作为机制验证放第二轮。

### Q38. 哪些模块要自己写？

必须自己写：

```text
manifest/schema
field_mask（字段有效性掩码）
phi encoder
D/G encoder
state space interface
dynamics module
observation decoder 接线
driver sensitivity protocol（驱动敏感性评估协议）
imaging condition swap protocol（成像条件替换评估协议）
physical consistency protocol（物理一致性评估协议）
```

这些是论文贡献所在。编码器 backbone 和 segmentation head 可以复用。

### Q39. 哪些模块可以先用简单版本？

可以先简单化：

- Observation Encoder（观测编码器）：ViT-S/B 或 U-Net encoder；
- Dynamics（动力学模块）：ConvLSTM 或 small Temporal Transformer；
- Observation Decoder（观测解码器）：U-Net decoder；
- Uncertainty：MC dropout 或 small ensemble；
- Geo prior：DEM/slope/water distance 三项即可；
- Driver：事件类型 + 时间跨度 + 季节即可。

不要第一版就追求完整物理模拟、扩散生成、全数据集统一大模型。

### Q40. 最小代码闭环是什么？

最小闭环是：

```text
1. 读取一个样本：X, phi, D, G, field_mask（字段有效性掩码）
2. encoder 得到 s_t
3. dynamics 得到 s_{t+h}
4. state head 输出 S_{t+h}/Delta S
5. decoder 用 phi_future 输出 X_hat
6. loss 根据 field_mask（字段有效性掩码）激活
7. eval 跑有/无 D、G、phi 的消融
```

建议先用 EarthNet + 洪水数据跑通，不要等所有数据集整理完。

### Q41. 推荐的项目目录结构是什么？

```text
configs/
data/
  datasets/
  transforms/
  field_builders/
  datamodules/
models/
  encoders/
  condition_encoders/
  state_space/
  dynamics/
  decoders/
  heads/
losses/
tasks/
eval/
  metrics/
  protocols/
scripts/
notebooks/
```

每个目录必须有清楚边界。不要把字段构建散落在 dataset 里面，也不要把评估协议写在 notebook 里。

### Q42. 数据加载器应该如何设计？

Dataset 返回统一字典：

```python
{
    "image": ...,
    "future_image": ...,
    "phi": ...,
    "phi_future": ...,
    "driver": ...,
    "geo": ...,
    "state": ...,
    "future_state": ...,
    "task_label": ...,
    "field_mask": ...,
    "meta": ...
}
```

不同数据集可以字段缺失，但 key 尽量一致。collate_fn 要能处理变长时间序列和缺字段。

### Q43. 字段 mask 和缺失字段怎么处理？

原则：

```text
缺字段不伪造真值。
缺字段不参与对应 loss。
缺字段可以用 learnable missing embedding 表示。
所有 loss 都读 field_mask（字段有效性掩码）。
```

例如没有降雨：

```text
driver.precipitation = 0
field_mask.precipitation = 0  # 该字段缺失，不参与降雨相关 loss
```

模型知道这个 0 不是“无降雨”，而是“未知”。

### Q44. 训练配置文件应该如何组织？

建议分层配置：

```text
configs/data/ssl4eo.yaml
configs/data/earthnet.yaml
configs/model/obsworld_vit_small.yaml
configs/train/stage1_pretrain.yaml
configs/train/stage2_dynamics.yaml
configs/train/stage3_observation.yaml
configs/eval/driver_sensitivity.yaml
```

每个配置至少写：

- 数据集；
- 字段；
- batch 采样比例；
- loss 权重；
- optimizer；
- checkpoint；
- 输出目录；
- eval protocol（评估协议）。

不要把关键超参藏在脚本里。

## 7. 实验问题

### Q45. 对比模型有哪些？

必须覆盖五类：

1. 遥感基础模型：SkySense、Prithvi-EO-2.0、CROMA、DOFA、SatMAE、Scale-MAE；
2. 未来预测模型：Persistence、ConvLSTM、PredRNN、Earthformer、EarthNet baseline；
3. 遥感生成/world model：RS-WorldModel、RemoteBAGEL、TerraMind；
4. 任务专家模型：洪水、LULC、建筑变化、损毁；
5. 自身消融：w/o state、w/o D、w/o G、w/o phi。

无法复现的模型要明确说明，只在可比子任务或公开结果上比较。

### Q46. 下游任务有哪些？

必做：

- 未来像素预测；
- 土地覆盖/季节状态转移；
- 洪水识别与洪水状态转移。

强建议：

- 跨模态观测预测；
- 不确定性校准。

可选：

- SpaceNet7 建筑变化；
- xBD 灾害损伤；
- PASTIS 作物/物候。

### Q47. 世界模型能力实验有哪些？

核心实验：

```text
真实/空/错误驱动替换
未来成像条件替换
状态一致性
物理一致性
不确定性校准
跨模态泛化
跨区域/事件/季节泛化
```

这些实验比普通主表更重要，因为它们证明“模型像一个世界模型那样响应条件”。

### Q48. 消融实验怎么设计？

消融要对应论文 claim。

| Claim | 消融 |
|---|---|
| 成像条件解耦有用 | w/o `phi`，`phi` 普通拼接 vs 条件注入 |
| 状态空间必要 | direct pixel prediction |
| 外生驱动有用 | w/o `D`，空/错 `D` |
| 地理先验有用 | w/o `G` |
| 观测模型可控 | w/o `phi_future` |
| 不确定性有用 | w/o uncertainty head |
| 统一 schema 有用 | single-task vs schema multi-task |

每个消融都要有对应指标，不要只给一张大表。

### Q49. 评价指标用哪些？

像素：

```text
MAE, RMSE, PSNR, SSIM, LPIPS, EarthNetScore, spectral angle
```

状态：

```text
mIoU, F1, OA, object F1, transition F1
```

驱动：

```text
KL, real-null probability gap, mismatch transition decay
```

物理：

```text
slope/water/road consistency, violation rate
```

不确定性：

```text
ECE, NLL, Brier, AUSE, risk-coverage curve
```

泛化：

```text
held-out AOI/event/season drop
```

### Q50. 可视化应该展示什么？

必须展示：

1. 历史影像、真实未来、预测未来；
2. 当前状态、预测未来状态、真实未来状态；
3. 状态转移图；
4. 真实/空/错误驱动的预测差异；
5. 固定状态、替换未来成像条件后的多版本输出；
6. 有/无地理先验的物理一致性；
7. 不确定性热图和错误区域；
8. 失败案例。

每张图都要服务一个 claim，不要只放好看的图。

## 8. 投稿与风险问题

### Q51. 更适合 CVPR 还是 AAAI？

当前主线更自然地适合 AAAI，也可以冲 CVPR。

AAAI 更看重：

- world model 定义；
- 状态空间；
- 条件动力学；
- 不确定性；
- 可证伪评估。

CVPR 更看重：

- 视觉结果；
- 像素预测；
- 强 baseline；
- 可视化；
- 方法模块清晰。

如果像素预测和可视化强，CVPR 竞争力上升；如果像素一般但状态/驱动/物理一致性强，AAAI 更稳。

### Q52. 最小可投稿版本是什么？

最小可投稿版本：

```text
数据：SSL4EO + EarthNet + 洪水数据
模型：中等规模 encoder + state head + dynamics + observation decoder
实验：像素预测 + 洪水状态转移 + 驱动/先验/成像条件消融
```

必须有：

- `field_mask`（字段有效性掩码）schema；
- 状态—动力学—观测流程；
- 有/无 `D`；
- 真实/空/错误驱动；
- 有/无 `G`；
- 有/无 `phi`；
- 状态一致性或物理一致性。

没有这些，world model 叙事不稳。

### Q53. 完整顶会版本是什么？

完整版本：

```text
SSL4EO + EarthNet + DynamicEarthNet + 洪水 + SpaceNet7/xBD + PASTIS/BigEarthNet/SEN12MS
```

模型上：

- 多模态编码器；
- 成像条件解耦状态；
- 条件状态动力学；
- 条件观测模型；
- 多任务 heads；
- 不确定性。

实验上：

- 常规主表；
- world model 能力实验；
- 大模型编码器 + ObsWorld；
- 强消融；
- 跨区域/事件/季节泛化；
- 可视化和失败案例。

### Q54. 最大风险是什么？

最大风险是被读成“多任务遥感时序预测工程”。

触发这个风险的情况：

- 数据集很多但每个作用不清；
- 主指标只有像素质量；
- `D/G/phi` 消融不明显；
- 状态空间不可解释；
- 没有驱动替换和物理一致性实验。

解决办法是先做最小可证伪实验。不要等全系统完成才发现 `D` 没用。

### Q55. 如果实验效果一般，如何保住论文贡献？

如果常规指标一般，但专属指标强，可以保住。

可强调：

- 状态一致性更好；
- 驱动响应更合理；
- 成像条件替换更可控；
- 不确定性更可信；
- 跨模态/跨区域更稳。

如果所有指标都一般，要退一步，把论文从“大模型性能”改为“统一 schema + 可证伪评估协议 + 中等规模方法验证”。

### Q56. 如果时间不足，应该砍掉什么？

优先砍：

1. SpaceNet7 和 xBD 中砍一个；
2. PASTIS；
3. BigEarthNet / SEN12MS 辅助预训练；
4. 大模型编码器增强；
5. 复杂 diffusion decoder；
6. 主动获取；
7. 自然语言问答。

不能砍：

- `field_mask`（字段有效性掩码）；
- `phi/D/G`；
- 状态 head；
- dynamics；
- 至少一个像素出口；
- 至少一个驱动敏感性实验。

## 9. 最终执行清单

### Q57. 现在第一步应该做什么？

第一步不是写大模型，而是做数据字段和最小闭环。

立刻做：

```text
1. 固定 unified sample schema
2. 写 manifest 格式
3. 选 EarthNet + 洪水数据做 pilot
4. 构建 phi/D/G/field_mask（字段有效性掩码）
5. 训练一个小模型跑通 X -> s -> s_future -> X_future
6. 跑 w/o D、w/o G、w/o phi
```

最小 pilot 证明不了驱动和先验有用，就不要急着扩数据。

### Q58. 两周内应该完成什么？

两周目标：

```text
第 1-3 天：schema + manifest + field_mask（字段有效性掩码）
第 4-7 天：EarthNet dataloader + baseline pixel prediction
第 8-10 天：洪水数据 dataloader + DEM/slope/water prior
第 11-14 天：小模型闭环 + 第一组消融
```

两周结束时至少要有：

- dataloader 输出样例；
- 可视化一个 batch 的字段；
- baseline 训练日志；
- 有/无 `D/G/phi` 的初步对比。

### Q59. 一个月内应该完成什么？

一个月目标：

```text
1. 阶段 1 预训练最小版
2. 阶段 2 动力学最小版
3. 阶段 3 观测 decoder 最小版
4. 洪水驱动敏感性实验
5. EarthNet 像素预测主表雏形
6. 第一版可视化图组
```

一个月后应能判断：

- 状态瓶颈是否有用；
- `D` 是否被模型使用；
- `G` 是否改善物理一致性；
- `phi` 是否改善跨成像条件输出；
- 是否值得扩到 DynamicEarthNet 和 SpaceNet7/xBD。

### Q60. 最终论文应该如何组织？

建议论文结构：

```text
1. Introduction
2. Related Work
3. Problem Definition
4. Method
   4.1 Observation Encoder（观测编码器）
   4.2 Imaging Condition Encoder（成像条件编码器）
   4.3 Land-Surface State Space（地表状态空间）
   4.4 State Dynamics Module（状态动力学模块）
   4.5 Observation Decoder（观测解码器 / 观测模型）
   4.6 Training Objectives
5. Unified Data Schema and Tasks
6. Experiments
   6.1 Main Results
   6.2 World Model Capability Tests
   6.3 Ablations
   6.4 Visualization and Failure Cases
7. Discussion and Limitations
8. Conclusion
```

Introduction 不要写太散。全篇只围绕一句话展开：

```text
遥感图像不是世界本身；ObsWorld 建模地表状态、状态动力学和条件观测过程。
```

## 附录 A. 外部核查链接速查

本轮写作使用的主要外部链接包括：

| 类别 | 链接 |
|---|---|
| SSL4EO-S12 v1.1 | https://github.com/DLR-MF-DAS/SSL4EO-S12-v1.1 |
| EarthNet2021 | https://www.earthnet.tech/ |
| DynamicEarthNet | https://arxiv.org/abs/2203.12560 |
| C2S-MS Floods | https://source.coop/c2sms/c2smsfloods |
| SpaceNet7 | https://arxiv.org/abs/2102.11958 |
| PASTIS | https://github.com/VSainteuf/pastis-benchmark |
| BigEarthNet | https://bigearth.net/ |
| RS-WorldModel | https://arxiv.org/abs/2603.14941 |
| Remote Sensing-Oriented World Model | https://arxiv.org/abs/2509.17808 |
| Earth-o1 | https://arxiv.org/abs/2605.06337 |
| Prithvi-EO-2.0 | https://github.com/NASA-IMPACT/Prithvi-EO-2.0 |
| TerraMind | https://github.com/ibm/terramind |

## 附录 B. 三轮逻辑自检

### 第一轮：主线一致性检查

| 检查项 | 结果 |
|---|---|
| 是否始终围绕 ObsWorld | 通过。所有问答围绕成像条件解耦、状态动力学和观测模型。 |
| 是否把 WorldRS 吸收到动力学中 | 通过。Q5 明确 WorldRS 是动力学心脏。 |
| 是否避免单纯像素预测 | 通过。Q3、Q4、Q10、Q52 多次限定像素位置。 |
| 是否明确状态、动力学、观测模型关系 | 通过。Q1、Q11、Q12、Q28-34 已明确。 |

### 第二轮：数据与训练闭环检查

| 检查项 | 结果 |
|---|---|
| 每阶段是否有明确数据 | 通过。Q19、Q28-34 已列出。 |
| 每数据集是否有明确用途 | 通过。Q20-24 已分工。 |
| 是否处理字段缺失 | 通过。Q17、Q27、Q43 说明 `field_mask`（字段有效性掩码）。 |
| 是否避免无脑拼接 | 通过。Q25 明确禁止。 |
| 是否给出执行时间表 | 通过。Q57-59 给出第一步、两周、一个月计划。 |

### 第三轮：代码落地检查

| 检查项      | 结果                 |
| -------- | ------------------ |
| 是否说明复用框架 | 通过。Q36、Q37 已列出。    |
| 是否说明自写模块 | 通过。Q38 已列出。        |
| 是否有最小闭环  | 通过。Q40、Q52 已列出。    |
| 是否有完整版本  | 通过。Q53 已列出。        |
| 是否避免工程过重 | 通过。Q39、Q56 明确可砍内容。 |

最终自检结论：08 已经把方案中的关键概念、执行选择和审稿问答固定下来。后续真正的第一步应是字段 schema 和最小实验闭环，而不是继续扩展概念。
