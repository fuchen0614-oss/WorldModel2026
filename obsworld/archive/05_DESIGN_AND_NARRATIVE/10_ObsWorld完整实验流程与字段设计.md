# 10 ObsWorld 完整实验流程与字段设计

本文用于统一 ObsWorld 后续实验与工程实现思路。重点不是写代码，而是说明完整技术路线、每个阶段训练什么、使用什么数据集、需要哪些字段、哪些模块自己训练、哪些模块借用现有基础模型，以及 FSDP 在训练落地中的位置。

## 1. 当前统一结论

ObsWorld 的核心路线是：

```text
历史遥感观测 X + 当前成像条件 phi
    -> Observation Encoder（观测编码器）
    -> Land-Surface State（地表状态）z_t / S_t
    -> State Dynamics Module（状态动力学模块）
       输入 external driver D（外生驱动）和 geographic prior G（地理先验）
    -> Future Land-Surface State（未来地表状态）z_{t+h} / S_{t+h}
    -> Observation Decoder（观测解码器）
       输入 future imaging condition phi_{t+h}（未来成像条件）
    -> Future Observation（未来像素观测）X_hat_{t+h}
```

这条路线不能写成普通的“下一帧预测”。更准确的说法是：

> ObsWorld 先预测未来地表状态，再把未来状态解码成指定成像条件下的未来遥感观测。

因此，未来像素观测是重要输出，但不是唯一目标。主目标是：

```text
未来地表状态是否正确
状态转移是否合理
外生驱动响应是否可信
成像条件替换是否可控
未来像素是否尊重预测状态
```

## 2. 训练方式总原则

代码框架应该一次性按完整 ObsWorld 设计，但训练不要一次性全训。

推荐路线是：

```text
先搭完整框架骨架
每次只激活一部分模块和 loss
一个阶段训练完成后保存 checkpoint
下一阶段加载上一个 checkpoint 继续训练
最后再做小学习率联合微调
```

也就是：

```text
stage1_ssl4eo_encoder.ckpt
    -> stage1_5_state_aware_encoder.ckpt
    -> stage2_state_dynamics.ckpt
    -> stage3_observation_decoder.ckpt
    -> stage4_task_finetune.ckpt
    -> final_obsworld.ckpt
```

不要一开始把 SSL4EO、EarthNet、DynamicEarthNet、洪水数据、建筑变化数据全部混在一起训练。正确方式是：

```text
统一 sample schema（统一样本字段）
不同数据集返回相似 batch key
不同字段通过 field_mask（字段有效性掩码）控制
不同阶段激活不同 loss
不同数据集服务不同科学问题
```

## 3. 核心英文术语对照

| 英文                  | 中文        | 在本文中的意思                                |
| ------------------- | --------- | -------------------------------------- |
| Observation         | 观测        | 遥感影像本身，是地表在某种成像条件下被看到的结果               |
| Imaging Condition   | 成像条件      | 传感器、模态、波段、季节、云、分辨率、观测角度等影响影像外观的因素      |
| Observation Encoder | 观测编码器     | 把遥感影像编码成特征或初始状态的模型模块                   |
| Land-Surface State  | 地表状态      | 水体、植被、建筑、土地覆盖、灾害状态等更接近地表真实情况的表示        |
| Latent State        | 潜在状态      | 模型内部的连续向量或特征图，记作 z_t                   |
| Semantic State      | 语义状态      | 可解释的状态图或类别图，记作 S_t                     |
| State Dynamics      | 状态动力学     | 当前状态如何随时间、外生驱动和地理先验变化                  |
| External Driver     | 外生驱动      | 降雨、洪水事件、季节、温度、灾害冲击、人类活动等导致状态变化的外部因素    |
| Geographic Prior    | 地理先验      | DEM、坡度、河流距离、土地覆盖背景等影响变化是否合理的空间条件       |
| Observation Decoder | 观测解码器     | 把未来状态变成未来像素观测的模块                       |
| Task Head           | 任务头       | 洪水、土地覆盖、变化检测等具体任务输出层                   |
| field_mask          | 字段有效性掩码   | 标记某个字段是否真实存在，防止缺失字段参与 loss             |
| Checkpoint          | 权重检查点     | 某一阶段训练后保存的模型权重文件                       |
| FSDP                | 全参数分片数据并行 | PyTorch 多 GPU 大模型训练框架，用于降低显存占用         |
| Shard               | 数据分片      | WebDataset 或大规模数据中按文件切分的数据包，常见为 tar 文件 |
| Split               | 数据划分      | train / val / test 等训练、验证、测试划分         |

## 4. 完整实验阶段

### 阶段 0：数据巡检与统一 schema

目标：

```text
确认数据能读
建立统一字段
建立 field_mask
避免后续多数据集训练混乱
```

对应数据集：

```text
SSL4EO-S12-v1.1
后续扩展到 EarthNet、DynamicEarthNet、洪水数据等
```

主要产物：

```text
shard-level manifest（数据分片级清单）
sample schema（统一样本字段定义）
field_mask 规则
数据统计信息
dataloader smoke test 结果
```

这个阶段不追求训练效果，只追求“能稳定读数据、字段解释清楚、缺失字段不造假”。

### 阶段 1：SSL4EO 观测编码器预训练

当前已经确定第一轮使用：

```text
数据集：SSL4EO-S12-v1.1
模态：S2L2A
训练目标：MAE-style masked reconstruction
模型：tiny / ViT-small
训练框架：PyTorch FSDP1
硬件：8 * H100
```

这一阶段训练：

```text
Observation Encoder（观测编码器）
轻量 decoder（只用于重建训练）
可选 phi encoder（成像条件编码器的最小版本）
```

输入：

```text
S2L2A image（Sentinel-2 L2A 影像）
modality / sensor / product_level
season_index 或 time_index
valid_mask
field_mask
```

输出：

```text
masked patch reconstruction（被遮挡 patch 的重建）
initial latent state z_t（初始潜在状态）
stage1_ssl4eo_encoder.ckpt
```

为什么这样做：

```text
SSL4EO 没有强事件驱动标签，但非常适合学习遥感观测表征
masked reconstruction 不需要人工标签
S2L2A 是正式遥感训练中更有意义的多光谱表面反射率产品
```

这一阶段不证明完整 world model，只证明：

```text
模型会读 SSL4EO
模型会编码遥感影像
模型能形成可迁移的遥感观测表征
```

### 阶段 1.5：状态感知辅助预训练

目标：

```text
让 encoder 的 latent 不只是图像纹理，而更接近地表状态
```

可使用 SSL4EO 中的：

```text
NDVI：归一化植被指数
LULC：土地利用 / 土地覆盖
DEM：数字高程模型
S1GRD：Sentinel-1 雷达模态
```

可做任务：

```text
S2L2A -> NDVI 预测
S2L2A -> 弱 LULC 预测
S2L2A -> DEM 辅助预测
S2L2A <-> S1GRD 跨模态对齐或预测
```

注意：这些任务是辅助任务，不是最终论文主任务。它们的作用是让状态空间更像“地表状态”，而不是只重建像素。

### 阶段 2：未来状态与状态动力学训练

目标：

```text
训练 State Dynamics Module（状态动力学模块）
学习当前地表状态如何变成未来地表状态
```

对应数据集：

```text
EarthNet2021：未来观测和植被变化
DynamicEarthNet：土地覆盖状态转移
洪水数据：外生驱动和灾害状态转移
```

主要训练模块：

```text
State Head（状态头）
State Dynamics Module（状态动力学模块）
D/G Encoder（外生驱动 / 地理先验编码器）
```

输入：

```text
z_t / S_t：当前潜在状态或语义状态
D：外生驱动
G：地理先验
h：预测时间间隔
```

输出：

```text
z_{t+h}：未来潜在状态
S_{t+h}：未来语义状态
Delta S：状态转移
U：不确定性
```

重点实验：

```text
w/o D：去掉外生驱动
w/o G：去掉地理先验
wrong D：输入错误驱动
null D：输入空驱动
held-out event：留出事件泛化
held-out region：留出区域泛化
```

这一阶段是 ObsWorld 的论文心脏。

### 阶段 3：条件观测解码训练

目标：

```text
把未来状态解码成指定未来成像条件下的未来像素观测
```

输入：

```text
z_{t+h} / S_{t+h}
phi_{t+h}：未来成像条件
```

输出：

```text
X_hat_{t+h}：未来像素观测
```

对应数据集：

```text
EarthNet2021
SSL4EO 多模态样本
C2S-MS / SEN12-FLOOD 等可选数据
```

关键实验：

```text
固定未来状态，替换 phi_future，看生成观测是否合理变化
生成像素后再用分割器估计状态，与预测状态比较
跨模态观测预测，例如 S2 -> S1 或 S1 -> S2
```

注意：第一版 decoder 用轻量 U-Net / MAE decoder 即可，不建议一开始使用扩散模型。

### 阶段 4：下游任务与 world model 评估

目标：

```text
证明状态空间和状态动力学对真实任务有用
```

必做任务：

```text
未来像素预测
土地覆盖 / 季节状态转移
洪水识别与洪水状态转移
```

强建议任务：

```text
跨模态观测预测
不确定性校准
```

可选任务：

```text
建筑变化
灾害损毁
作物 / 物候
```

核心评估不是只看 PSNR / SSIM，而是同时看：

```text
像素质量
状态准确性
状态转移
驱动敏感性
成像条件可控性
物理一致性
不确定性校准
长程 rollout 稳定性
```

### 阶段 5：基础模型增强与对比

目标：

```text
证明 ObsWorld 的提升不是因为 encoder 更大，而是因为状态-动力学-观测结构更合理
```

可接入的 foundation encoder：

```text
Prithvi-EO-2.0
SatMAE
CROMA
Scale-MAE
TerraMind encoder
```

对比方式：

```text
基础模型 encoder + 普通任务头
基础模型 encoder + 直接未来像素预测头
基础模型 encoder + ObsWorld state/dynamics/decoder
自训 tiny/ViT-small ObsWorld
```

理想结论：

```text
ObsWorld 框架能把遥感基础模型的当前图像理解能力，转化为未来地表状态预测能力。
```

## 5. 数据集分工

| 数据集                                 | 中文作用              | 对应阶段       | 证明什么             |
| ----------------------------------- | ----------------- | ---------- | ---------------- |
| SSL4EO-S12-v1.1                     | 多模态、多季节遥感预训练数据    | 阶段 1 / 1.5 | 观测编码、跨模态、弱状态表征   |
| EarthNet2021                        | 未来观测预测数据          | 阶段 2 / 3   | 未来像素、植被变化、观测解码   |
| DynamicEarthNet                     | 土地覆盖时间序列          | 阶段 2 / 4   | 土地覆盖状态转移         |
| Sen1Floods11 / SEN12-FLOOD / C2S-MS | 洪水数据              | 阶段 2 / 4   | 外生驱动、地理先验、洪水状态转移 |
| SpaceNet7                           | 建筑 footprint 时间序列 | 完整版可选      | 慢变量城市变化          |
| xBD                                 | 灾害损毁数据            | 完整版可选      | 单次冲击事件响应         |
| PASTIS                              | 作物 / 物候时序         | 完整版可选      | 农业季节动力学          |
| BigEarthNet / SEN12MS               | 大规模语义辅助预训练        | 可选增强       | 语义辅助、跨模态表征       |

第一版最小闭环仍然推荐：

```text
SSL4EO-S12-v1.1
+ EarthNet2021
+ 一个洪水数据集
```

不要第一版同时铺开所有数据集。

## 6. 统一字段总表

### 6.1 样本身份字段

| 字段 | 中文 | 作用 | 是否必须 |
|---|---|---|---|
| `sample_id` | 样本编号 | 唯一标识一个样本 | 必须 |
| `dataset_name` | 数据集名称 | 标记样本来自哪个数据集 | 必须 |
| `split` | 数据划分 | train / val / test | 必须 |
| `shard_path` | 数据分片路径 | WebDataset tar 或其他 shard 文件位置 | SSL4EO 必须 |
| `sample_key` | 分片内样本键 | tar 内部样本前缀或样本名 | SSL4EO 必须 |
| `location_id` | 地点编号 | 同一地点多时相 / 多模态对齐 | 强建议 |
| `aoi_id` | 区域编号 | 区域划分和跨区域泛化 | 可选 |

### 6.2 时间字段

| 字段 | 中文 | 作用 | 可行性说明 |
|---|---|---|---|
| `timestamp` | 时间戳 | 真实拍摄时间 | 有则用，没有不要伪造 |
| `time_index` | 时间序号 | 第几个时间片，例如 0/1/2/3 | SSL4EO 第一版可用 |
| `season_index` | 季节序号 | 春夏秋冬或四季编号 | SSL4EO 第一版可用 |
| `season` | 季节 | spring / summer / autumn / winter | 若官方顺序明确再填 |
| `time_delta` | 时间间隔 | 当前到未来相隔多久 | 动力学阶段必须 |
| `horizon` | 预测步长 | 预测 t+h | 动力学阶段必须 |

### 6.3 观测字段

| 字段 | 中文 | 作用 | 可行性说明 |
|---|---|---|---|
| `image` / `observation` | 当前观测影像 | 模型输入 | 必须 |
| `future_image` | 未来观测影像 | 像素预测监督 | EarthNet / 动态数据必需 |
| `modality` | 模态 | S2L2A、S1GRD、S2RGB 等 | 必须 |
| `sensor` | 传感器 | Sentinel-1 / Sentinel-2 等 | 必须 |
| `product_level` | 产品级别 | L1C / L2A / GRD 等 | 强建议 |
| `bands` | 波段列表 | 说明 image 的通道含义 | 必须 |
| `spatial_resolution` | 空间分辨率 | 米 / 像素 | 强建议 |
| `crs` | 坐标参考系统 | 地理投影信息 | 有则记录 |
| `valid_mask` | 有效像素掩码 | 排除无效值、nodata、NaN | 必须 |
| `cloud_mask` | 云掩码 | 排除云污染像素 | 有则用，没有 mask=0 |

### 6.4 成像条件字段

`phi` 表示当前成像条件，`phi_future` 表示未来成像条件。

| 字段 | 中文 | 作用 |
|---|---|---|
| `phi.sensor` | 传感器条件 | S1 / S2 等 |
| `phi.modality` | 模态条件 | 光学、多光谱、SAR 等 |
| `phi.product_level` | 产品级别条件 | L1C / L2A / GRD |
| `phi.bands` | 波段条件 | 不同通道组合 |
| `phi.resolution` | 分辨率条件 | 不同空间尺度 |
| `phi.time_index` | 时间序号条件 | 多时相输入 |
| `phi.season` | 季节条件 | 季节外观差异 |
| `phi.cloud_ratio` | 云量比例 | 如果能从 mask 统计 |
| `phi.valid_ratio` | 有效像素比例 | 从 valid_mask 统计 |

第一版不要强行使用太阳角、观测角、精确云量。如果数据里没有，使用 `field_mask=0`。

### 6.5 地表状态字段

| 字段 | 中文 | 作用 |
|---|---|---|
| `latent_state` / `z_t` | 当前潜在状态 | 模型内部连续状态 |
| `state` / `S_t` | 当前语义状态 | 水体、LULC、洪水等显式状态 |
| `future_state` / `S_{t+h}` | 未来语义状态 | 状态预测监督 |
| `state_delta` / `Delta S` | 状态转移 | 当前到未来发生什么变化 |
| `state_uncertainty` | 状态不确定性 | 预测可信度 |

SSL4EO 第一阶段通常只有弱状态，例如 NDVI / LULC / DEM。真正强状态转移需要 EarthNet、DynamicEarthNet、洪水数据等。

### 6.6 外生驱动字段

| 字段 | 中文 | 作用 | 第一版可行性 |
|---|---|---|---|
| `driver` / `D` | 外生驱动总字段 | 影响状态变化的外部条件 | 动力学阶段使用 |
| `precipitation` | 降雨 | 洪水和植被变化驱动 | 洪水数据可选增强 |
| `temperature` | 温度 | 植被、农业、季节变化 | 可选 |
| `event_type` | 事件类型 | flood、storm、wildfire 等 | 洪水 / 灾害数据可用 |
| `event_time` | 事件时间 | 灾害发生时间 | 有则用 |
| `season_driver` | 季节驱动 | 季节性变化 | 可从时间字段派生 |

没有真实驱动时不要伪造因果。缺失字段必须 `field_mask=0`。

### 6.7 地理先验字段

| 字段 | 中文 | 作用 | 可行性 |
|---|---|---|---|
| `geo` / `G` | 地理先验总字段 | 影响状态变化是否合理 | 动力学阶段使用 |
| `dem` | 数字高程模型 | 地形高度 | SSL4EO 有，洪水任务重要 |
| `slope` | 坡度 | 水流和地表变化约束 | 可由 DEM 派生 |
| `aspect` | 坡向 | 可选地形属性 | 可由 DEM 派生 |
| `water_distance` | 距水体 / 河流距离 | 洪水先验 | 需要水体或河网数据 |
| `permanent_water` | 永久水体 | 洪水和水体变化背景 | 可选 |
| `lulc_prior` | 土地覆盖先验 | 状态变化背景 | SSL4EO / DynamicEarthNet 可用 |

地理先验是软约束，不是绝对规则。

### 6.8 标签与任务字段

| 字段 | 中文 | 作用 |
|---|---|---|
| `task_id` | 任务编号 | 指明当前样本服务什么任务 |
| `task_label` | 任务标签 | 分割、分类、变化检测标签 |
| `flood_mask` | 洪水掩码 | 洪水任务监督 |
| `lulc_label` | 土地覆盖标签 | 土地覆盖状态监督 |
| `change_mask` | 变化掩码 | 建筑、灾害或土地覆盖变化 |
| `damage_label` | 损毁标签 | 灾害损毁评估 |

### 6.9 字段有效性掩码

`field_mask` 是全项目最重要的工程字段之一。

作用：

```text
告诉模型哪些字段真实存在
告诉 loss 哪些监督可以激活
防止缺失字段被当成真实 0
支持多数据集统一 batch
```

示例含义：

```text
field_mask.image = 1
field_mask.future_image = 0
field_mask.state = 0
field_mask.ndvi = 1
field_mask.dem = 1
field_mask.precipitation = 0
field_mask.cloud_mask = 0
```

这表示当前样本有图像、NDVI、DEM，但没有未来图像、强状态标签、降雨和云掩码。

## 7. 训练配置逻辑

每个训练阶段单独配置：

```text
configs/train/stage1_ssl4eo_fsdp.yaml
configs/train/stage1_5_state_aux.yaml
configs/train/stage2_dynamics.yaml
configs/train/stage3_decoder.yaml
configs/train/stage4_task_eval.yaml
```

每个配置要明确：

```text
使用哪些数据集
启用哪些字段
训练哪些模块
冻结哪些模块
启用哪些 loss
batch size
学习率
precision
checkpoint 路径
FSDP 设置
```

训练不是“所有模块一次全部配好一起训”，而是：

```text
同一个项目框架
不同阶段配置
不同模块 trainable / frozen
不同 loss 权重
不同 checkpoint 输入输出
```

## 8. FSDP1 落地关系

FSDP1 是训练工程框架，不是论文方法创新。它和 ObsWorld 的关系是：

```text
ObsWorld：模型方法和实验范式
FSDP1：多 GPU 训练实现方式
```

8 张 H100 推荐：

```text
PyTorch FSDP1
bf16 mixed precision
不使用 CPU offload
先不开 activation checkpointing
先保存 full state dict checkpoint
正式大模型再考虑 sharded checkpoint
```

关键注意事项：

```text
WebDataset shard 必须按 rank / worker 切分，避免 8 张卡读重复样本
先小 shard smoke test，再 train split 正式训练
每个 rank 的随机种子要可控
rank 0 负责主要日志
checkpoint 要能被下一阶段非 FSDP 或 FSDP 训练正常加载
FSDP 包装后 optimizer 的创建和 checkpoint 保存要保持一致
```

## 9. 当前第一轮固定选择

当前第一轮建议固定为：

```text
数据：SSL4EO-S12-v1.1
模态：S2L2A
数据范围：先小 shard 子集 smoke test，再切 train split
模型：tiny / ViT-small
训练目标：MAE-style masked reconstruction
分布式：FSDP1
硬件：8 * H100
精度：bf16 优先
checkpoint：先保存 stage1_ssl4eo_encoder.ckpt
```

第一轮成功标准：

```text
能读取 S2L2A batch
batch shape / dtype / 数值范围合理
单卡 10 step 正常
FSDP1 8 卡 10 step 正常
loss 是有限值，没有 NaN / Inf
checkpoint 能保存和重新加载
```

## 10. 后续需要避免的误区

1. 不要把 2.3TB 数据全部解压后再训练。
2. 不要第一步就做完整 ObsWorld。
3. 不要缺字段时用 0 冒充真实值。
4. 不要把所有数据集等权混合。
5. 不要把 FSDP 写成方法创新。
6. 不要让像素预测统治论文。
7. 不要只做大模型 encoder 加普通预测头，否则会变成普通迁移学习。

最终主线应保持：

```text
SSL4EO 训练遥感观测编码能力
EarthNet / DynamicEarthNet / 洪水数据训练未来状态和动力学
条件观测 decoder 负责把未来状态变成未来观测
FSDP1 负责让训练在 8 * H100 上稳定运行
```

