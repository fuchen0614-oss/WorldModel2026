
# 24 dgh字段获取方式与数据集速查

> [!abstract] 本文定位
> 本文只提炼 Stage 2 动力学所需的 dgh 字段、获取方式和使用数据集。以 [[22 ObsWorld Stage2+ dgh(外生驱动D-地理先验G-预测跨度h)数据构建完整方案]] 与 [[23 ObsWorld完整方法框架与Stage2动力学算法设计]] 为主，结合 05-10、21 号文档中与 dgh 直接相关的内容。

## 1. 一句话结论

`dgh = D + G + h`，是 `StateDynamicsModule` 的三路条件输入，用来预测 `z_t -> z_{t+h}`。

| 符号 | 含义 | 时间属性 | 作用 |
|---|---|---|---|
| `D` | 外生驱动 External Driver | 随时间变化 | 告诉模型“为什么会变”，如降雨、温度、太阳辐射、季节 |
| `G` | 地理先验 Geographic Prior | 静态或极慢变化 | 告诉模型“怎么变才合理”，如高程、坡度、水流方向、土地覆盖背景 |
| `h` | 预测跨度 Horizon | 标量 | 告诉模型要预测多久以后，如 7 天、30 天、365 天 |

> [!important] 最小启动版本
> Stage 2 不必等 ERA5。先做 `dgh_v1_minimal`：用 SSL4EO 自带 DEM、LULC、时间戳、S2 波段即可构建最小 dgh；ERA5 到货后升级到 `dgh_v2_era5`。

## 2. D 外生驱动字段

| 字段                                             |    层级    | 获取方式                                                | 数据源                    | 备注                          |
| ---------------------------------------------- | :------: | --------------------------------------------------- | ---------------------- | --------------------------- |
| `precipitation`                                |   core   | 下载 ERA5-Land `total_precipitation`，对 `[t,t+h]` 区间求和 | ERA5-Land              | 洪水第一驱动，P0                   |
| `temperature_2m`                               |   core   | 下载 ERA5-Land `2m_temperature`，按区间均值或统计量聚合           | ERA5-Land              | 物候、融雪、蒸散发核心变量，P0            |
| `soil_moisture`                                |   core   | 下载 ERA5-Land `volumetric_soil_water`，取表层土壤湿度        | ERA5-Land              | 产流前提，P1                     |
| `evapotranspiration`                           |   core   | 下载 ERA5-Land `total_evaporation`，按区间聚合              | ERA5-Land              | 水量平衡项，P1                    |
| `solar_radiation`                              |   core   | 下载 ERA5-Land `ssrd`，按区间聚合                           | ERA5-Land              | 光合作用和融雪能量，P1                |
| `ndvi_previous`                                |   core   | 从当前或前一时刻 S2 波段计算 `(B8-B4)/(B8+B4)`                  | SSL4EO / EarthNet / S2 | 自回归植被状态                     |
| `day_of_year`                                  |   core   | 从样本时间戳计算 sin/cos 周期编码                               | 数据集时间戳                 | 季节弱驱动                       |
| `season`                                       |   core   | 复用 phi_v3 的季节字段或由时间戳派生                              | SSL4EO / phi_v3        | 与 phi 有重叠，但在 dgh 中作为弱驱动使用   |
| `sun_elevation`                                | optional | 复用 phi_v3 或 NOAA 公式计算                               | phi_v3 / 时间经纬度         | 更偏成像条件，必要时作为 D/phi 共享字段     |
| `wind_speed` / `snow_depth` / `runoff` / `VPD` | enhance  | 从 ERA5-Land 或其他气象产品扩展                               | ERA5-Land 等            | 有则更好，不阻塞 v1                 |
| `LAI` / `fire_mask`                            | optional | 下载 MODIS/VIIRS 或 NASA Earthdata 产品后对齐               | MODIS / VIIRS          | 植被和火灾任务扩展                   |
| `human_activity_proxy`                         | optional | 夜光、道路密度、人口/GDP、城市增长率等外部产品                           | OSM / 夜光 / 统计数据        | 城市化任务弱驱动，缺失时 `field_mask=0` |

## 3. G 地理先验字段

| 字段                               |    层级    | 获取方式                              | 数据源                                            | 备注                   |
| -------------------------------- | :------: | --------------------------------- | ---------------------------------------------- | -------------------- |
| `elevation`                      |   core   | 直接读取 `zarr['dem']` 或 DEM 栅格       | SSL4EO DEM                                     | 地形基础字段               |
| `slope`                          |   core   | DEM 求梯度，建议 Sobel 或 numpy gradient | DEM 派生                                         | 洪水、侵蚀、城市扩张约束         |
| `aspect`                         |   core   | DEM 梯度方向 `arctan2`，可存 sin/cos     | DEM 派生                                         | 影响受光和蒸散发             |
| `flow_direction`                 |   core   | DEM 填洼后用 D8 算法计算                  | DEM 派生，pysheds/richdem                         | 洪水路径关键字段             |
| `flow_accumulation`              |   core   | 由 `flow_direction` 递归统计上游汇流       | DEM 派生                                         | 识别河网与易涝区             |
| `TWI`                            | enhance  | `ln(flow_acc / tan(slope))`       | DEM + flow_acc                                 | 地形湿度指数               |
| `lulc_static`                    |   core   | 读取 LULC 当前或众数类别                   | SSL4EO LULC / DynamicEarthNet / ESA WorldCover | 土地覆盖背景               |
| `lulc_stability`                 |   core   | LULC 时序 mode 频率                   | LULC 时序                                        | 区分稳定区与易变区            |
| `impervious_fraction`            |   core   | LULC 查找表映射，如 urban 高、forest 低     | LULC 派生                                        | 城市内涝和城市化约束           |
| `water_body_mask`                |   core   | `LULC==水体` 或 `flow_acc` 超阈值       | LULC / DEM 派生 / JRC 水体                         | 永久水体基准               |
| `distance_to_water`              |   core   | 对 `water_body_mask` 做距离变换         | scipy distance_transform_edt                   | 近水风险与河岸环境            |
| `TPI` / `curvature` / `TRI`      | enhance  | DEM 二阶或邻域统计派生                     | DEM 派生                                         | 地形增强字段               |
| `drainage_density`               | enhance  | 河网或 flow accumulation 派生          | DEM / HydroSHEDS                               | 洪水增强字段               |
| `water_distance_fine`            | optional | 下载 HydroSHEDS/OSM 水系，栅格化后距离变换     | HydroSHEDS / OSM                               | 洪水任务需要更精细水系时再做       |
| `road_distance` / `climate_zone` | optional | 批量裁剪 OSM 道路、Koppen/ERA5 气候带       | OSM / Koppen / ERA5                            | 早期方案提到的扩展 G，不是 v1 必需 |

## 4. h 预测跨度字段

| 字段 | 获取方式 | 典型范围 | 编码方式 |
|---|---|---|---|
| `time_delta` / `horizon` | `(t_future - t_current).days` | 按任务决定 | 连续标量，单位天 |
| `log_h` | `log(h)` 或 `log1p(h)` | 同上 | 与状态特征拼接后过 MLP |
| `h_bucket` | 将 h 离散成短/中/长跨度 | 洪水 1-7 天；植被 7-180 天；土地覆盖 90-730 天 | 可选，用于课程学习或采样分层 |

## 5. 数据集分工

| 数据集 / 数据源                               | 主要用途                     | 给 dgh 提供什么                                        |  优先级  |
| --------------------------------------- | ------------------------ | ------------------------------------------------- | :---: |
| SSL4EO-S12 v1.1                         | Stage 1 预训练；Stage 2 骨架验证 | DEM、LULC、NDVI、时间戳、季节对；可构建 `dgh_v1_minimal`        |  P0   |
| DynamicEarthNet                         | Stage 2 状态转移主数据          | 月度 LULC 真值，构造 `S_t -> S_{t+h}` / `z_t -> z_{t+h}` |  P0   |
| EarthNet2021                            | 未来像素预测与短期动力学             | 5 日一帧、未来 S2、天气 forcing、地形                         |  P0   |
| ERA5-Land                               | 通用外生驱动来源                 | 降雨、气温、土壤湿度、蒸散发、太阳辐射等 D 字段                         | P0/P1 |
| Sen1Floods11                            | 洪水下游评估                   | 洪水 mask、永久水/洪水区分；D/G 需外接                          |  P1   |
| SEN12-FLOOD / C2S-MS Floods             | 洪水和多模态扩展                 | S1/S2 洪水场景、事件响应、云/水体标签                            |  P1   |
| HydroSHEDS / OSM                        | 精细水系和道路先验                | 河流距离、道路距离、排水网络增强 G                                |  P2   |
| MODIS / VIIRS / NASA Earthdata          | 任务扩展驱动                   | LAI、火灾、夜光等可选 D 字段                                 |  P2   |
| ESA WorldCover / Dynamic World / JRC 水体 | 弱状态或水体先验                 | LULC、永久水体、弱标签补充                                   |  P2   |

> [!note] 数据集不要物理缝合
> 各数据集通过 adapter 输出统一 sample dict：`image, phi, D, G, h, labels, field_mask, dataset_id, task_id`。缺字段用 `field_mask=0` 和缺失嵌入处理，不伪造数值。

## 6. 获取与存储流程

1. 构建 `dgh_v1_minimal`：从 SSL4EO 读取 DEM、LULC、时间戳、S2 波段；离线派生 G、弱 D 和 h。
2. DEM 派生：`elevation -> slope/aspect -> flow_direction -> flow_accumulation -> TWI`。
3. LULC 派生：`lulc_static -> lulc_stability -> impervious_fraction -> water_body_mask -> distance_to_water`。
4. ERA5 下载：注册 Copernicus CDS，下载指定 bbox 和时间范围内的 ERA5-Land 变量，保存为 zarr/netCDF。
5. ERA5 对齐：空间上按样本 `center_lat/lon` 双线性插值；时间上匹配最近时刻或聚合 `[t,t+h]` 区间。
6. 可选 HydroSHEDS：下载水系矢量，栅格化到影像网格，再做距离变换。
7. 写出 parquet：沿用 phi_v3 范式，离线抽取，训练时按 `sample_key` join。

## 7. 版本路线

| 版本 | 字段范围 | 外部数据 | 用途 |
|---|---|---|---|
| `dgh_v1_minimal` | DEM、slope、aspect、flow、LULC、水体、season、NDVI、h | 无 | Stage 2 骨架训练和架构验证 |
| `dgh_v2_era5` | v1 + precipitation、temperature、soil_moisture、evapotranspiration、solar_radiation | ERA5-Land | 完整驱动训练、洪水/植被消融 |
| `dgh_v3_hydro` | v2 + 精细水系距离、排水网络增强字段 | HydroSHEDS / OSM | 洪水任务和空间先验消融 |

## 8. 最小实施顺序

1. 先做 `dgh_v1_minimal`，数小时级批处理即可启动 Stage 2。
2. 同步申请 Copernicus CDS 并排队下载 ERA5-Land。
3. 训练侧先让 dataloader 返回 `D/G/h + field_mask`，不要等所有字段齐全。
4. ERA5 到货后构建 `dgh_v2_era5`，继续训练并做 `w/ D` vs `w/o D` 消融。
5. 如果洪水任务需要更强地理约束，再做 `dgh_v3_hydro`。

## 9. 参考来源
