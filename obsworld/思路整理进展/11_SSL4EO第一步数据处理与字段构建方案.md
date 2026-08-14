# 11 SSL4EO 第一步数据处理与字段构建方案

本文专门描述 ObsWorld 第一阶段的数据处理方案。当前目标不是完整训练 ObsWorld，而是在远程服务器上先把 SSL4EO-S12-v1.1 的数据可读性、字段构建、dataloader smoke test 和 Stage 1 训练入口跑通。

## 1. 当前已知信息

服务器工作目录：

```text
/csy-mix02/cog8/zjliu17/Agent/WorldModel2026
```

数据集目录：

```text
/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1
```

下载方式：

```text
从 Hugging Face mirror 的 embed2scale/SSL4EO-S12-v1.1 仓库原样下载文件
下载脚本会生成 .manifest.json
```

因此，数据格式应以仓库实际文件为准。下载脚本不会改变数据格式，只会把远程文件复制到本地。官方 Hugging Face 页面说明该仓库主要用于 WebDataset，因此大概率是一批 tar shard。

当前第一轮固定选择：

```text
模态：S2L2A
数据范围：先小 shard 子集做 smoke test，再切 train split 正式训练
训练目标：MAE-style masked reconstruction
模型：tiny / ViT-small
训练框架：PyTorch FSDP1
硬件：8 * H100
```

## 2. 第一步总目标

第一步不是“开始正式大规模训练”，而是完成：

```text
确认数据存在
确认数据格式
确认 S2L2A 可读
确认 batch 可进入模型
确认单卡训练 10 step 可跑
确认 FSDP1 8 卡训练 10 step 可跑
确认 checkpoint 可保存和加载
```

第一步成功后，才进入正式 train split 训练。

## 3. 官方字段核实后的字段解决方案

根据 SSL4EO-S12-v1.1 的官方 GitHub、Hugging Face 数据集页和技术报告，字段问题不需要从零猜。该数据集已经提供了较多原生元数据，第一步应该采用：

```text
先读取官方原生字段
再派生少量必要字段
最后用 field_mask 标记缺失字段
```

不要自己凭空补字段，也不要为了让 schema 看起来完整而伪造字段。

### 3.1 官方数据组织

官方资料显示，SSL4EO-S12-v1.1 包含：

```text
246,144 个地点
每个地点 4 个时间戳
模态包括：
S2L1C
S2L2A
S2RGB
S1GRD
NDVI
LULC
DEM
```

当前 Hugging Face 仓库是 WebDataset 版本：

```text
外层：tar shard
内部：Zarr Zip 样本
读取：官方提供 build_ssl4eos12_dataset
```

因此，第一步不要假设数据是普通 tif 文件，也不要全量解压。应优先：

```text
读取 .manifest.json
检查 tar shard
使用官方 dataloader 或按 WebDataset + Zarr Zip 读取
```

### 3.2 官方 metadata 中已经有的字段

官方 Hugging Face 页面说明提供：

```text
train_metadata.parquet
val_metadata.parquet
```

这些 metadata 文件中包含的关键字段包括：

| 官方字段                              | 中文意思             | 在 ObsWorld 中的用途                |
| --------------------------------- | ---------------- | ------------------------------ |
| `tar`                             | 所在 tar 分片        | 对应 `shard_path`                |
| `zarr`                            | 样本 Zarr Zip 名称   | 对应 `sample_key` 或样本文件名         |
| `sample_id`                       | 样本编号 / 地点编号      | 对应 `sample_id` / `location_id` |
| `split`                           | 数据划分             | train / val                    |
| `center_lon`                      | 中心经度             | 空间元数据                          |
| `center_lat`                      | 中心纬度             | 空间元数据                          |
| `crs`                             | 坐标参考系统           | 空间对齐                           |
| `bounds`                          | 空间范围             | patch 地理范围                     |
| `geometry`                        | 空间多边形            | 可用于 GIS 检查                     |
| `S2_time_0` 到 `S2_time_3`         | Sentinel-2 四个时间戳 | S2L2A 的时间字段                    |
| `S1_time_0` 到 `S1_time_3`         | Sentinel-1 四个时间戳 | S1GRD 的时间字段                    |
| `cloud_cover_0` 到 `cloud_cover_3` | 四个时间片的云量比例       | 成像条件 / 质量控制                    |

这些字段应作为第一步字段构建的主要来源。

### 3.3 官方 dataloader 可返回的字段

官方说明中，使用：

```text
return_metadata=True
```

时，dataloader 可以返回：

```text
center_lon
center_lat
cloud_mask
time_S2L2A
time_S1GRD
```

这些字段非常重要，因为它们直接对应我们方案里的：

```text
空间位置
时间戳
云掩码
成像条件 phi
样本质量控制
```

因此，第一步 dataloader smoke test 不应只打印 `image`，还应尝试打开 `return_metadata=True`，确认这些字段是否能正常返回。

### 3.4 S2L2A 的实际字段形式

官方示例显示，S2L2A 被加载为 xarray dataset 时大致是：

```text
time: 4
band: 12
y: 264
x: 264
```

也就是模型中常见的张量形式：

```text
S2L2A: [time, channel, height, width]
S2L2A: [4, 12, 264, 264]
```

其中 `band` 包括 Sentinel-2 的多光谱波段，例如：

```text
B01
B02
B03
B04
B05
B06
B07
B08
B8A
B09
B11
B12
```

官方示例还显示 S2L2A 中有：

```text
center_lat
center_lon
cloud_mask
crs
file_id
sample_id
time
```

所以第一阶段 S2L2A 的字段构建可以直接围绕这些字段展开。

### 3.5 S1GRD 的实际字段形式

官方示例显示，S1GRD 被加载后是：

```text
time: 4
band: 2
y: 264
x: 264
```

也就是：

```text
S1GRD: [4, 2, 264, 264]
```

两个 band 是：

```text
vv
vh
```

中文解释：

| band | 中文意思 |
|---|---|
| `vv` | 垂直发射、垂直接收极化 |
| `vh` | 垂直发射、水平接收极化 |

这说明 SSL4EO 中的 S1GRD 不是需要自己处理的复数 SLC 文件，而是已经处理好的实数 GRD 后向散射特征。后续使用 S1GRD 时，应按 2 通道实数 SAR 输入处理，不要按 RGB 图像处理，也不要假设需要读取复数相位。

### 3.6 默认时间顺序与季节顺序

官方说明中有一个重要细节：

```text
SSL4EO-S12-v1.1 默认按日期排序
每个 timestep 不一定固定对应春夏秋冬
```

如果希望按固定季节顺序读取，需要使用官方参数：

```text
reindex_seasonal=True
```

含义是：

```text
按 yearly quartal / 季节重新排序
```

因此，字段构建时要区分：

| 字段 | 中文 | 使用条件 |
|---|---|---|
| `timestamp` | 精确时间戳 | 从 S2_time / S1_time 直接读取 |
| `time_index` | 时间序号 | 默认可用，表示日期排序后的 0/1/2/3 |
| `season_index` | 季节序号 | 只有使用 `reindex_seasonal=True` 或能确认季节顺序时才稳定使用 |

不要默认把 `time_index=0/1/2/3` 直接解释为春夏秋冬。

### 3.7 字段解决策略

字段应分为三类处理。

第一类：官方原生字段，直接读取。

```text
sample_id
split
tar
zarr
center_lon
center_lat
crs
bounds
geometry
S2_time_0 到 S2_time_3
S1_time_0 到 S1_time_3
cloud_cover_0 到 cloud_cover_3
cloud_mask
file_id
```

第二类：由原生字段可靠派生。

```text
dataset_name = SSL4EO-S12-v1.1
modality = S2L2A / S1GRD / NDVI / LULC / DEM
sensor = Sentinel-2 / Sentinel-1
product_level = L2A / GRD
time_index = 0 / 1 / 2 / 3
valid_mask = image 是否 finite 且不为 nodata
valid_ratio = valid_mask 的有效像素比例
cloud_ratio = cloud_mask 或 cloud_cover 的统计
```

第三类：SSL4EO 第一阶段没有的字段，不强补。

```text
precipitation
temperature
event_type
future_state
driver D
river_distance
damage_label
```

这些字段留给后续 EarthNet、洪水数据、DynamicEarthNet、SpaceNet7/xBD 等数据集。

### 3.8 第一阶段 field_mask 推荐值

第一阶段只用 S2L2A 做 masked reconstruction 时，推荐：

```text
field_mask.image = 1
field_mask.sample_id = 1
field_mask.split = 1
field_mask.shard_path = 1
field_mask.sample_key = 1
field_mask.modality = 1
field_mask.sensor = 1
field_mask.product_level = 1
field_mask.timestamp = 1
field_mask.time_index = 1
field_mask.center_lon = 1
field_mask.center_lat = 1
field_mask.crs = 1
field_mask.bounds = 1
field_mask.cloud_mask = 1
field_mask.cloud_cover = 1
field_mask.valid_mask = 1
```

如果没有加载 DEM、NDVI、LULC，则：

```text
field_mask.dem = 0
field_mask.ndvi = 0
field_mask.lulc = 0
```

如果加载了对应模态，则设为：

```text
field_mask.dem = 1
field_mask.ndvi = 1
field_mask.lulc = 1
```

第一阶段不使用外生驱动和未来状态，因此：

```text
field_mask.driver = 0
field_mask.precipitation = 0
field_mask.temperature = 0
field_mask.event_type = 0
field_mask.future_image = 0
field_mask.future_state = 0
field_mask.state_delta = 0
```

### 3.9 对文章结构的影响

这次官方字段核实后，可以更明确地写：

```text
SSL4EO 阶段不是靠人工补字段，而是利用官方提供的时间、空间、云、模态和多源观测元数据，训练 Observation Encoder 和初始 Imaging Condition Encoder。
```

对应文章中的模块关系：

```text
S2L2A / S1GRD / NDVI / LULC / DEM
    -> Observation Encoder（观测编码器）

sensor / modality / product_level / timestamp / cloud_mask / cloud_cover
    -> Imaging Condition Encoder（成像条件编码器）

NDVI / LULC / DEM
    -> 状态感知辅助任务或地理先验辅助，不必第一轮启用
```

第一轮仍然建议只做：

```text
S2L2A + masked reconstruction
```

第二轮再加入：

```text
NDVI
LULC
DEM
S1GRD
```

这样不会把数据处理做得过重，同时又保留了 ObsWorld 后续扩展所需的字段基础。

## 3. 为什么先用小 shard 子集

SSL4EO-S12-v1.1 数据量约 2.3TB。如果一开始直接读取完整 train split，问题会很难定位。

常见问题包括：

```text
路径不对
tar shard 读不了
tar 内部 key 不符合预期
样本无法按 image / label 分组
S2L2A 的 shape 不一致
dtype 或数值范围异常
NaN / Inf
多卡重复读取同一批 shard
loss 变 NaN
checkpoint 保存失败
```

所以第一步采用：

```text
1-5 个小 shard
少量 batch
10 step smoke test
```

这一步不看精度，只看训练管线能不能跑通。

## 4. 数据巡检顺序

建议按以下顺序做数据处理。

### 4.1 路径存在性检查

检查：

```text
数据根目录是否存在
.manifest.json 是否存在
目录下是否有 tar / json / csv / parquet / zarr 等文件
总文件数
总大小
主要文件后缀
```

如果 `.manifest.json` 存在，优先读 `.manifest.json`。不要重新全量扫描 2.3TB 数据。

### 4.2 shard-level manifest

先建立“数据分片级清单”，而不是“样本级全量清单”。

`shard-level manifest` 中文可理解为：

```text
每个 tar / shard 文件一行的清单
```

建议字段：

| 字段                 | 中文    | 说明                                       |
| ------------------ | ----- | ---------------------------------------- |
| `shard_id`         | 分片编号  | 给每个 shard 一个唯一编号                         |
| `rel_path`         | 相对路径  | shard 相对数据根目录的位置                         |
| `abs_path`         | 绝对路径  | shard 在服务器上的完整路径                         |
| `file_type`        | 文件类型  | tar / zarr / json / csv 等                |
| `size_bytes`       | 文件大小  | 用于校验下载完整性                                |
| `split`            | 数据划分  | train / val / test，若路径无法判断则 unknown      |
| `modality`         | 模态    | S2L2A / S1GRD / S2RGB 等，若路径无法判断则 unknown |
| `verified`         | 是否验证过 | 是否已经打开检查                                 |
| `sample_count_est` | 样本数估计 | 可选，第一步不强制全量统计                            |
| `notes`            | 备注    | 记录异常或不确定信息                               |

第一步不要为了统计所有样本数而打开全部 tar。可以先抽样打开少量 shard。

### 4.3 识别 split 和 modality

需要从文件路径或文件名中尝试识别：

```text
split：train / val / test
modality：S2L2A / S2L1C / S2RGB / S1GRD / NDVI / LULC / DEM
```

如果路径不能明确识别，不要乱填。可以写：

```text
split = unknown
modality = unknown
field_mask.split = 0
```

然后通过 tar 内部 key 或官方数据读取脚本进一步确认。

## 5. tar shard 内部样本检查

如果数据是 WebDataset tar shard，第一步应该随机选 1-5 个 tar 文件打开检查。

检查内容：

```text
tar 内部文件名
是否存在成组样本
样本 key 怎么命名
S2L2A 数据对应什么后缀
是否有 json / metadata
是否有多个 time_index
是否有 NDVI / LULC / DEM 对齐文件
```

WebDataset 常见结构是：

```text
sample_key.ext
sample_key.json
sample_key.npy
sample_key.tif
```

但不能假设一定如此，必须以实际 tar 内容为准。

检查结果需要回答：

```text
一个样本由哪些文件组成？
哪个文件是 S2L2A 图像？
S2L2A 是 tif、npy、npz、zarr 还是其他格式？
是否能拿到四个时间片？
是否能拿到 location_id？
是否能拿到 timestamp？
```

## 6. 第一轮 S2L2A 字段设计

第一轮只做 S2L2A masked reconstruction，因此字段不要贪多。

### 6.1 必须字段

| 字段              | 中文      | 来源            | 说明                                         |
| --------------- | ------- | ------------- | ------------------------------------------ |
| `sample_id`     | 样本编号    | 生成            | 全局唯一，例如 dataset + shard + key + time_index |
| `dataset_name`  | 数据集名称   | 固定            | SSL4EO-S12-v1.1                            |
| `split`         | 数据划分    | 路径 / manifest | train / val / test / unknown               |
| `shard_path`    | 分片路径    | manifest      | 当前样本来自哪个 tar                               |
| `sample_key`    | 样本键     | tar 内部文件名     | 用于样本分组                                     |
| `modality`      | 模态      | 路径 / key / 固定 | 当前第一轮固定为 S2L2A                             |
| `sensor`        | 传感器     | 固定            | Sentinel-2                                 |
| `product_level` | 产品级别    | 固定            | L2A，表示大气校正后的表面反射率产品                        |
| `image`         | 图像张量    | tar 内部数据      | 模型输入                                       |
| `bands`         | 波段列表    | 数据说明 / 读取结果   | 不要硬编码，以实际读取为准                              |
| `valid_mask`    | 有效像素掩码  | image 派生      | 非 NaN、非 Inf、非 nodata                       |
| `field_mask`    | 字段有效性掩码 | 生成            | 标记每个字段是否真实存在                               |

### 6.2 强建议字段

| 字段 | 中文 | 来源 | 说明 |
|---|---|---|---|
| `location_id` | 地点编号 | sample_key / metadata | 同一地点多时相和多模态对齐的关键 |
| `time_index` | 时间序号 | key / metadata | SSL4EO 有四个季节时间片时可用 0/1/2/3 |
| `season_index` | 季节序号 | time_index 派生 | 官方顺序明确时再映射成具体季节 |
| `spatial_resolution` | 空间分辨率 | metadata / 数据说明 | 如果没有精确字段，用数据集默认并标记来源 |
| `valid_ratio` | 有效像素比例 | valid_mask 统计 | 判断样本质量 |
| `image_minmax` | 数值范围统计 | image 统计 | 用于发现异常值 |

### 6.3 可选字段

| 字段           | 中文          | 来源                   | 可行性                  |
| ------------ | ----------- | -------------------- | -------------------- |
| `timestamp`  | 精确时间戳       | metadata             | 有则用，没有不要伪造           |
| `season`     | 季节          | timestamp / 官方顺序     | 不确定时只保留 season_index |
| `ndvi`       | 归一化植被指数     | SSL4EO NDVI 模态或由波段派生 | 第二轮辅助任务使用            |
| `lulc`       | 土地利用 / 土地覆盖 | SSL4EO LULC 模态       | 弱状态标签                |
| `dem`        | 数字高程模型      | SSL4EO DEM 模态        | 地理先验                 |
| `cloud_mask` | 云掩码         | QA 或 metadata        | 若没有，不要硬补             |
| `crs`        | 坐标参考系统      | metadata             | 有则记录                 |
| `bounds`     | 地理范围        | metadata             | 有则记录                 |

### 6.4 不建议第一轮强补的字段

第一轮不要强行补：

```text
precipitation：降雨
temperature：温度
sun_angle：太阳角
view_angle：观测角
event_type：事件类型
future_image：未来图像监督
future_state：未来状态监督
```

原因：

```text
SSL4EO 第一轮主要是观测编码预训练
这些字段如果没有真实来源，会引入假监督
```

## 7. field_mask 规则

`field_mask` 的中文是“字段有效性掩码”。

它不是图像 mask，而是告诉训练系统：

```text
这个字段是否真实存在？
对应 loss 是否可以启用？
```

第一轮 S2L2A 样本可能是：

```text
field_mask.image = 1
field_mask.modality = 1
field_mask.sensor = 1
field_mask.product_level = 1
field_mask.time_index = 1 或 0
field_mask.timestamp = 0 或 1
field_mask.ndvi = 0 或 1
field_mask.lulc = 0 或 1
field_mask.dem = 0 或 1
field_mask.cloud_mask = 0
field_mask.future_image = 0
field_mask.future_state = 0
field_mask.precipitation = 0
```

原则：

```text
缺字段不伪造
缺字段不参与对应 loss
缺字段可以用 missing embedding 表示
0 不是“没有发生”，而是“未知 / 缺失”
```

例子：

```text
precipitation = 0 且 field_mask.precipitation = 0
```

含义是“没有降雨字段”，不是“降雨为 0”。

## 8. S2L2A 图像处理原则

### 8.1 band 处理

S2L2A 是 Sentinel-2 L2A 表面反射率产品。常见情况是多光谱波段，但具体通道数量必须以实际读取结果为准。

不要硬编码：

```text
一定是 12 通道
一定是 13 通道
一定已经重采样到同一分辨率
```

应该先检查：

```text
image shape
band count
每个 band 的 dtype
每个 band 的 min / max
是否存在 nodata
```

### 8.2 数值归一化

第一步不要假设数值范围。

需要先统计：

```text
原始 dtype：uint16 / float32 / 其他
最小值 / 最大值
均值 / 标准差
异常值比例
NaN / Inf 比例
```

再决定：

```text
是否除以 10000
是否 clip 到合理范围
是否做 per-band mean/std normalization
```

正式训练前应从一部分 shard 统计 per-band mean/std。第一轮 smoke test 可以先使用简单归一化，但必须记录假设。

### 8.3 valid_mask 构建

`valid_mask` 中文是“有效像素掩码”。

可由以下规则构建：

```text
不是 NaN
不是 Inf
不是 nodata
数值在合理范围内
```

如果没有明确 nodata 值，先只用 finite check：

```text
isfinite(image)
```

后续再根据统计结果加强规则。

## 9. 成像条件 phi 的第一版构造

`phi` 中文是“成像条件”。

第一版 S2L2A 的 `phi` 可以先包含：

| 字段                       | 中文     | 来源             |
| ------------------------ | ------ | -------------- |
| `phi.modality`           | 模态     | S2L2A          |
| `phi.sensor`             | 传感器    | Sentinel-2     |
| `phi.product_level`      | 产品级别   | L2A            |
| `phi.band_count`         | 波段数量   | image shape    |
| `phi.spatial_resolution` | 空间分辨率  | metadata / 默认  |
| `phi.time_index`         | 时间序号   | key / metadata |
| `phi.season_index`       | 季节序号   | key / metadata |
| `phi.valid_ratio`        | 有效像素比例 | valid_mask 统计  |

不要第一版强行加入：

```text
sun_elevation
view_angle
cloud_probability
atmospheric_condition
```

除非数据中真的有。

## 10. 小 shard 子集构建

小 shard 子集用于 smoke test。

建议选择：

```text
1-5 个 S2L2A shard
优先选择文件大小正常、路径看起来属于 train 或 val 的 shard
如果存在 val split，先选 val
如果没有明确 val，就从 train 中选少量 shard
```

小 shard 子集需要记录：

```text
subset_name
selected_shards
selection_reason
created_time
sample_count_est
```

小 shard 子集不是正式训练数据，只用于排错。

## 11. 数据处理产物

第一步应产出以下非代码产物或缓存：

```text
outputs/data_inspection/ssl4eo_file_summary.json
outputs/data_inspection/ssl4eo_shard_manifest.csv
outputs/data_inspection/ssl4eo_sample_preview.json
outputs/data_inspection/ssl4eo_s2l2a_stats.json
outputs/data_inspection/ssl4eo_smoke_subset.txt
```

含义：

| 文件 | 中文 | 用途 |
|---|---|---|
| `ssl4eo_file_summary.json` | 文件概览 | 总文件数、总大小、后缀分布 |
| `ssl4eo_shard_manifest.csv` | 分片清单 | 每个 shard 的路径、大小、模态、split |
| `ssl4eo_sample_preview.json` | 样本预览 | 少量样本 key、shape、dtype |
| `ssl4eo_s2l2a_stats.json` | S2L2A 统计 | min/max/mean/std/NaN 比例 |
| `ssl4eo_smoke_subset.txt` | 小 shard 列表 | smoke test 使用哪些 shard |

注意：不要把大图像复制到 cache 里。缓存只保存清单、统计和小预览。

## 12. dataloader 输出样本格式

第一轮 dataloader 应该统一输出类似含义的 batch。

不是代码，只说明字段逻辑：

```text
image：S2L2A 图像张量
phi：成像条件字段
valid_mask：有效像素掩码
field_mask：字段有效性掩码
meta：样本编号、shard、key、split 等元信息
```

如果已有字段可读，也可以包含：

```text
ndvi
lulc
dem
```

但第一轮训练 loss 只需要：

```text
masked reconstruction loss
```

不要因为 batch 中有 LULC / DEM 就立刻启用所有任务。先确认主通路稳定。

## 13. Stage 1 训练目标

第一轮采用 MAE-style masked reconstruction。

中文解释：

```text
把 S2L2A 图像切成很多 patch
随机遮住一部分 patch
模型只能看到未遮住的 patch
模型需要恢复被遮住的 patch
通过恢复误差训练 encoder
```

这适合 SSL4EO，因为：

```text
不需要人工标签
能训练遥感图像结构理解
和 SatMAE / MAE 类方法一致
后续 encoder 可以接到 ObsWorld 状态空间
```

第一轮 checkpoint：

```text
checkpoints/stage1_ssl4eo_s2l2a_mae_encoder.ckpt
```

这个 checkpoint 后续用于：

```text
初始化 ObsWorld Observation Encoder
接 state head
接 dynamics
接 observation decoder
与 foundation encoder 做对比
```

## 14. FSDP1 数据侧注意事项

FSDP1 多卡训练时，数据处理必须注意：

```text
每个 rank 读取不同 shard 或不同样本
不要 8 张卡重复读取同一批数据
worker 数不要过大，避免文件句柄和 I/O 压力
WebDataset shard shuffle 要可复现
小 shard smoke test 可以允许重复，但正式训练不能重复严重
```

建议顺序：

```text
1. 单进程读取一个 batch
2. 单卡训练 10 step
3. 8 卡 FSDP1 训练 10 step
4. 检查每张卡是否真的参与训练
5. 检查 checkpoint 是否能加载
6. 再切正式 train split
```

H100 建议：

```text
bf16 优先
不使用 CPU offload
第一轮不开 activation checkpointing
第一轮保存 full checkpoint
```

## 15. 第一阶段成功标准

数据可读性成功：

```text
能打开 tar shard
能识别 S2L2A 样本
能得到 image tensor
shape / dtype / min / max 合理
NaN / Inf 比例可接受
valid_mask 可构建
```

dataloader 成功：

```text
能读出 batch
batch 内样本维度一致
field_mask 正确
meta 信息可追踪回 shard 和 sample_key
```

训练 smoke test 成功：

```text
forward 正常
loss 是有限值
backward 正常
optimizer step 正常
单卡 10 step 正常
FSDP1 8 卡 10 step 正常
checkpoint 保存正常
checkpoint 重新加载正常
```

如果这些成功，再进入正式 train split。

## 16. 常见风险与处理原则

| 风险 | 中文解释 | 处理原则 |
|---|---|---|
| 全量解压太慢 | 2.3TB 数据不适合先全部解压 | 使用 WebDataset 流式读取 |
| manifest 太细 | 样本级全量 manifest 会非常慢 | 先做 shard-level manifest |
| split 不明确 | 路径看不出 train / val | 标记 unknown，不要乱填 |
| modality 不明确 | 文件名看不出 S2L2A | 打开 tar 内部检查 |
| band 数不确定 | 不同产品通道可能不同 | 以实际 shape 为准 |
| 数值范围不明 | 可能是 uint16 或 float | 先统计，再归一化 |
| 多卡重复读 | 8 张卡读同样数据 | 分布式 shard 切分 |
| checkpoint 不兼容 | FSDP 保存方式影响后续加载 | 第一轮优先 full checkpoint |
| 字段造假 | 缺失字段填 0 被当真 | 使用 field_mask |

## 17. 第一轮之后如何扩展

第一轮完成后，按以下顺序扩展：

```text
S2L2A masked reconstruction 跑通
    -> 加 NDVI / LULC / DEM 辅助任务
    -> 加 S1GRD / S2L2A 跨模态对齐
    -> 接 EarthNet 做未来观测预测
    -> 接洪水数据做外生驱动状态转移
    -> 接 observation decoder 做未来状态到未来像素
```

也就是说，SSL4EO 第一步只负责搭好 ObsWorld 的“眼睛”：

```text
Observation Encoder（观测编码器）
```

后续才逐步接：

```text
State Space（地表状态空间）
State Dynamics（状态动力学）
Observation Decoder（观测解码器）
```

## 18. 最终建议

当前最合理的第一步是：

```text
用 .manifest.json 建立 shard-level manifest
抽取 1-5 个 S2L2A shard 做 smoke subset
检查 tar 内部样本结构
构建 S2L2A 的最小字段 schema
构建 field_mask
统计 shape / dtype / min / max / NaN
跑 dataloader smoke test
跑单卡 10 step
跑 FSDP1 8 卡 10 step
确认 checkpoint 可保存和加载
再切换到 train split 正式训练
```

这一步完成后，项目就不再停留在概念层面，而是有了可以继续扩展的遥感观测编码训练地基。
