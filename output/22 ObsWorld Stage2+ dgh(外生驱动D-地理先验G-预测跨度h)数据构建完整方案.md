---
title: 22 ObsWorld Stage2+ dgh(外生驱动D/地理先验G/预测跨度h)数据构建完整方案
version: v1.0
created: 2026-07-01
project: ObsWorld
stage: 2 数据准备
tags:
  - ObsWorld
  - dgh
  - external-driver
  - geographic-prior
  - horizon
  - dataset
  - stage2
---

# 22 ObsWorld Stage2+ dgh 数据构建完整方案

> [!abstract] 本文定位
> 本文回答一个问题：**进入 Stage 2(状态动力学)之前,外生驱动 D、地理先验 G、预测跨度 h 这三路条件数据,到底怎么造、用什么数据集、哪些能直接算、哪些要下载、多个数据集怎么协同、权重怎么继承。**
> 本文是可执行的数据准备说明书,不是概念讨论。读完你应该能直接开工。

---

## 0. 文档导读

> [!info] 本文回答的六个问题
> 1. **dgh 到底是什么?** 和已有的 phi(成像条件)有什么区别?(见 §1)
> 2. **只用 SSL4EO 够吗?为什么要引入别的数据集?**(见 §2)
> 3. **先用 SSL4EO 之后,怎么加入其他数据集?权重是保留还是重训?**(见 §3,最关键)
> 4. **每个字段具体怎么来?哪些直接算、哪些要下载?**(见 §4、§7)
> 5. **不同数据集字段缺失、格式不一,怎么统一?**(见 §5、§6)
> 6. **现在具体该做什么?按什么顺序?**(见 §8)

### 与其他文档的关系

| 文档 | 角色 | 与本文关系 |
|------|------|-----------|
| [[10ObsWorld 完整实验流程与字段设计]] | 总纲:5+1 阶段路线 | 本文是「阶段 2 数据准备」的执行细节 |
| [[21_phi_v3与geo字段说明文档]] | phi 与 geo(DEM)字段说明 | 本文的 G 地理先验继承并扩展其 geo 部分 |
| [[13_项目进度汇报与phi数据集结构及FiLM设计约束]] | phi 数据集结构 | 本文的 D/G 复用其 parquet + sample_key join 范式 |
| **22(本文)** | **dgh 数据构建说明书** | 承接以上,聚焦 D/G/h 三路条件的构建与多数据集编排 |
| [[23ObsWorld完整方法框架与Stage2动力学算法设计]] | Stage 2 算法设计 | 本文准备的 dgh 数据服务于 23 的动力学模块 |

---

## 1. dgh 是什么(概念界定)

### 1.1 主线回顾

ObsWorld 的核心链条:

```text
历史遥感观测 X + 成像条件 phi
    → Observation Encoder(观测编码器)
    → Land-Surface State(地表状态)z_t
    → State Dynamics Module(状态动力学模块)      ← 阶段 2,dgh 在这里进入
       输入 external driver D + geographic prior G + horizon h
    → Future Land-Surface State(未来地表状态)z_{t+h}
    → Observation Decoder(观测解码器)+ 未来成像条件 phi_{t+h}
    → Future Observation(未来观测)X_hat_{t+h}
```

**dgh 是状态动力学模块的三路条件输入**,决定「当前地表状态 z_t 如何演化成未来状态 z_{t+h}」。

### 1.2 D — External Driver(外生驱动)

**定义**:随时间变化的、来自系统外部的驱动因素,它们「推动」地表状态发生变化。

**特征**:随时间变(time-varying)、未来时刻的值在预测时通常已知或可估计(如未来天气预报)。

**例子**:降雨、气温、土壤湿度、太阳辐射、蒸散发。降雨增多会推动洪水;气温回升会推动植被返青。

### 1.3 G — Geographic Prior(地理先验)

**定义**:静态或极缓变的空间背景条件,它们「约束」地表状态变化的合理性。

**特征**:不随时间变(static)、每个地点固定、对每个样本只需算一次。

**例子**:高程(DEM)、坡度、水流方向、土地覆盖背景、到水体距离。水只会往低处流(高程约束);陡坡不容易积水(坡度约束);城市扩张倾向于平地(坡度约束)。

### 1.4 h — Horizon(预测跨度)

**定义**:从当前时刻 t 到预测目标时刻 t+h 之间的时间间隔。

**特征**:一个标量(单位:天或月)。它告诉模型「你要预测的是多久以后」。

**例子**:h=7 天(短期洪水)、h=30 天(月度植被)、h=365 天(年度土地覆盖变化)。

### 1.5 dgh 与 phi 的区别(重要,不要混淆)

> [!important] phi 和 D/G 是两类完全不同的条件
> - **phi(成像条件)**:描述「这张图是怎么拍的」——传感器、太阳角、云、季节。它影响**观测的外观**,但不影响地表本身。作用在编码器/解码器。
> - **D/G(驱动/先验)**:描述「地表为什么会变、怎么变才合理」——降雨、地形。它影响**地表状态的演化**。作用在动力学模块。
>
> 一句话:**phi 管「看起来怎样」,D/G 管「实际怎么变」。** 二者在不同模块、服务不同目的,不要合并。

---

## 2. 数据集策略:为什么要用多个数据集

### 2.1 SSL4EO-S12 的能力与局限

**能力**:

- 大规模(24.4 万地点)、多模态(S2/S1/DEM/LULC/NDVI)、多季节(4 时间片)
- 已有成熟 pipeline(zarr 读取、phi parquet、多卡 FSDP)
- 自带 DEM 和 LULC → G 地理先验的现成来源

**局限**:

| 局限 | 后果 | 需要谁补 |
|------|------|---------|
| 只有 4 个季节快照,非连续时序 | 长时程动力学、规整 h 无法训 | DynamicEarthNet(月度)、EarthNet2021(5日) |
| 无事件标注(洪水/火灾) | 洪水任务无监督 | Sen1Floods11 |
| 无未来天气预报字段 | 强驱动 D 缺失 | EarthNet2021 自带 / ERA5 外接 |
| LULC 是弱标签(产品级,非人工标注) | 状态转移监督弱 | DynamicEarthNet 月度真值 |

### 2.2 候选数据集分工表（纠正版）

> [!note] 核心思想:每个数据集服务一个能力,不是简单堆在一起
> 关键纠正:**Stage 2 的目标是学习状态动力学(z_t → z_{t+h}),不是训练洪水检测等应用任务。** 洪水检测是 Stage 4 下游评估任务。

| 数据集                 |  阶段   | 主要角色     | 训练目标          | 监督信号                  | 时序性质      |
| ------------------- | :---: | -------- | ------------- | --------------------- | --------- |
| **SSL4EO-S12**      | 1/1.5 | 观测编码预训练  | 学习 Enc: X → z | 重建 loss(MAE)          | 4 季快照     |
|                     |   2   | dgh 架构验证 | 学习季节尺度动力学     | X_{t+90d} 或 z_{t+90d} | 季节对(90天)  |
| **DynamicEarthNet** |   2   | 状态转移主数据  | 学习月度演化        | LULC_{t+30d} 代理       | 月度密集(24月) |
| **EarthNet2021**    |   2   | 像素预测主数据  | 学习短期观测重建      | X_{t+5d}(像素级)         | 5日一帧 + 天气 |
| **Sen1Floods11**    |   4   | 下游评估     | 验证 z 编码水体信息   | 洪水 mask 标注            | 事件前后      |
| **作物/建筑数据**         |   4   | 下游评估     | 验证 z 迁移能力     | 任务标注                  | -         |
| **ERA5-Land**       |   2   | 外生驱动来源   | 为动力学提供 D      | **不是标注,是输入**          | 逐日/逐时     |

**关键澄清**:

- ✅ Stage 2 监督信号是 **X_{t+h} 本身**(未来观测)或从 X_{t+h} 编码的 **z_{t+h}**(未来状态)
- ✅ ERA5 提供的是 **D(外生驱动输入)**,不是监督标注
- ❌ 洪水标注 **不参与** Stage 2 动力学训练,只在 Stage 4 评估时使用
- ❌ Stage 2 不直接优化"洪水 IoU"或"作物 F1",而是优化"预测未来状态/观测"

### 2.3 顶会先例:SOTA 工作都是多数据集协同

| 工作 | 预训练数据 | 下游/微调数据 |
|------|-----------|--------------|
| Prithvi(NASA/IBM) | HLS | Sen1Floods11、作物分割 |
| SatMAE | fMoW-Sentinel | EuroSAT、BigEarthNet |
| PRESTO | SSL4EO-S12 + WorldStrat | EuroCrops 等 |
| ClimaX | ERA5 | 多个气候下游任务 |

**没有任何顶会工作只用单一数据集从头到尾。** 预训练用大数据、下游/动力学用带标注的专门数据,是标准范式。

### 2.4 结论

> [!important] 数据集策略结论(纠正版)
> **SSL4EO 是起点不是全部。Stage 2 动力学训练的核心是学习「状态如何演化」,不是学习「洪水在哪」。**
>
> 正确做法:
> - **Stage 1/1.5**: SSL4EO 预训练编码器 + 成像解耦
> - **Stage 2**: 多数据集联合训练动力学(DynamicEarthNet + EarthNet2021 + SSL4EO 季节对),监督信号是未来观测/状态本身,ERA5 提供 D 输入
> - **Stage 4**: 用 Sen1Floods11 等有标注数据评估下游任务,验证 z 的有用性
>
> 起点选 SSL4EO 的理由:基础设施已成熟、编码器权重可继承、先在熟悉数据上验证架构再扩展,是控制风险的工程选择。

---

## 2.5 各阶段定位与产出(新增)

> [!tip] 本节澄清各阶段到底在做什么、需要什么数据、产出什么能力

### Stage 1: 观测编码预训练

**定位**: 学习从遥感观测 X 提取地表状态表征 z 的编码器

**数据集**: SSL4EO-S12

**监督信号**: 重建 loss(MAE)

**产出**: encoder.ckpt，能力 Enc: X → z

### Stage 1.5: 成像解耦

**定位**: 让 z 不受成像条件(云、太阳角、季节)影响

**数据集**: SSL4EO-S12(多季节、多云量)

**监督信号**: 重建 loss + 对比 loss

**产出**: encoder_v1.5.ckpt，能力 Enc_phi: (X, phi) → z(成像无关)

### Stage 2: 状态动力学(dgh 作用阶段)

**定位**: 学习地表状态如何随时间演化，加入外生驱动和地理约束

**数据集**:

- DynamicEarthNet(月度时序)
- EarthNet2021(5日密集 + 天气)
- SSL4EO-S12(季节对)
- ERA5-Land(提供 D 输入)

**监督信号**:

- 状态 loss: ||z_pred - z_real||²(从 X_{t+h} 编码得到)
- 观测 loss: ||X_pred - X_{t+h}||²(如果联合训解码器)
- 代理 loss: ||NDVI_pred - NDVI_{t+h}||²(辅助)

**产出**: dynamics.ckpt，能力 Dynamics: (z_t, D, G, h) → p(z_{t+h})，带不确定性

### Stage 3: 观测解码

**定位**: 从状态 z 生成遥感观测 X

**数据集**: SSL4EO-S12 / EarthNet2021

**监督信号**: 重建 loss

**产出**: decoder.ckpt，能力 Dec: (z, phi) → X

### Stage 4: 下游任务微调

**定位**: 验证 z 是否编码了有用的地表信息

**数据集**: Sen1Floods11(洪水)、作物数据集、建筑数据集等

**监督信号**: 任务特定标注(洪水 mask、作物类别等)

**产出**: 证明 z 的迁移能力，提供应用出口

### Stage 5: 世界模型能力实验

**定位**: 验证模型是否学到了物理规律

**方法**: D/G 消融、反事实推理、物理一致性检查

**产出**: 论文核心卖点，证明模型用上了 dgh

---

## 3. 训练编排:权重怎么继承、数据集怎么加入(最关键)

这一节回答「先用 SSL4EO 之后,怎么加入其他数据集?是保留权重还是重训?」

### 3.1 核心原则:只从零训一次,之后全部继承

> [!important] 一句话原则
> 整个 ObsWorld 从头到尾,**只有 Stage 1 是从零训练**。之后每个阶段都是「加载上一阶段权重 + 新增模块 + 继续训练」。**不存在「拿新数据集从头重训」这回事。**

编码器在 Stage 1 学到的是「看懂遥感影像」的通用能力,这个能力跨数据集通用。丢掉重训既浪费算力,又会让模型忘掉已学会的表征。

### 3.2 分阶段 checkpoint 继承链

```text
Stage 1   : SSL4EO MAE 预训练               → encoder.ckpt        (唯一一次从零)
Stage 1.5 : 载入 encoder.ckpt + phi/FiLM     → encoder_v1.5.ckpt   (继承,成像解耦)
Stage 2   : 载入 encoder_v1.5.ckpt
            + 新增 StateDynamicsModule
            + 新增 D/G/h 编码器              → dynamics.ckpt       (继承)
Stage 3   : 载入 Stage2 + 新增观测解码器      → decoder.ckpt        (继承)
Stage 4   : 载入 Stage3,下游任务微调          → task.ckpt           (继承)
```

每一步的动作固定为:**装上前一步权重 → 新增几个模块 → 只把新模块从零训 → 老模块冻结或小学习率微调。**

### 3.3 编码器冻结还是微调(一个可调旋钮)

标准做法分两步:

1. **先冻结编码器**:只训新增的动力学模块。省显存、训练稳定、快速验证架构是否正确。
2. **再解冻**:用远小于主学习率的值(如主 lr 的 1/10)对整体联合微调,榨取最后性能。

> [!tip] 为什么先冻结
> 新模块初始是随机的,若一开始就联合训,随机模块产生的大梯度会破坏已经训好的编码器(称为「表征坍塌」)。先冻结让新模块先学到合理状态,再解冻联合,是安全做法。

### 3.4 多数据集:联合训练,不是顺序替换

> [!danger] 不要顺序训练
> 「先在 DynamicEarthNet 训完,再拿去 EarthNet 训」会导致**灾难性遗忘(catastrophic forgetting)**——模型学了后面的忘了前面的。这是错误做法。

**正确做法:联合训练**。多个数据集用统一 schema,在训练时通过采样器混合,同一个模型同时见到所有数据集:

- 每个 step 从不同数据集轮流取 batch
- 用 `field_mask` 控制各样本激活哪些字段
- 用 `task_id` 控制各样本参与哪个任务头的 loss

### 3.5 推荐的 Stage 2 内部编排

```text
Stage 2a  单数据集跑通架构
   数据:先用一个数据集(建议 DynamicEarthNet,月度时序规整,或 SSL4EO 季节对)
   目标:验证 StateDynamicsModule + D/G/h 编码器不崩、loss 收敛、状态转移合理
   编码器:冻结
Stage 2b  多数据集联合训练
   数据:DynamicEarthNet + EarthNet2021 + Sen1Floods11(统一 schema + 轮换采样)
   目标:各激活各的任务头,学习不同能力
   编码器:仍冻结或极低 lr
Stage 2c  联合微调
   解冻编码器,全局低学习率微调
```

### 3.6 先例

- **Prithvi / SatMAE**:预训练一次,每个下游任务都从同一预训练权重 fine-tune,从不重训预训练。
- **世界模型(DreamerV3 等)**:编码器与动力学联合训练;分阶段场景下,冻结感知模块先训动力学是常见控制手段。
- **多任务/多数据集训练**:联合采样 + 任务门控(task gating)是标准,顺序训练因遗忘问题被普遍规避。

---

## 4. 字段总清单:哪些直接算、哪些要下载

> [!info] 两大类字段
> - **A 类:直接可算** —— 不需下载任何外部数据,从 SSL4EO 现有数据(或时间戳/波段)派生。批处理脚本即可。
> - **B 类:需下载外部数据** —— 必须先下载 ERA5 等外部数据集,再做空间/时间对齐才能得到。

### 4.1 A 类:直接可算(无需外部数据)

| 字段 | 属于 | 来源 / 计算方式 |
|------|:---:|---------------|
| elevation(高程) | G | SSL4EO zarr['dem'] 直接读 |
| slope(坡度) | G | 从 DEM 求梯度(scipy Sobel) |
| aspect(坡向) | G | 从 DEM 梯度方向 arctan2 |
| flow_direction(水流方向) | G | 从 DEM 用 D8 算法(pysheds/richdem) |
| flow_accumulation(汇流累积) | G | 从 flow_direction 递归上游计数 |
| TWI(地形湿度指数) | G | ln(flow_acc / tan(slope)) |
| lulc_static(土地覆盖背景) | G | SSL4EO zarr['lulc'] 直接读 |
| lulc_stability(稳定度) | G | LULC 时序 mode 频率 |
| impervious_fraction(不透水比例) | G | LULC 查找表映射 |
| water_body_mask(永久水体) | G | LULC==水体 或 flow_acc>阈值 |
| distance_to_water(到水体距离) | G | 距离变换(scipy distance_transform_edt) |
| day_of_year(年积日) | D | 时间戳 → sin/cos 编码 |
| season(季节) | D | 已在 phi_v3 中 |
| sun_elevation(太阳高度角) | D/phi | NOAA 公式(已在 phi_v3 中) |
| ndvi_previous(历史 NDVI) | D | 从 S2 波段算 (B8-B4)/(B8+B4) |
| time_delta / h(预测跨度) | h | (t_future − t_current).days |

> [!note] A 类约 15+ 个字段,全部一次批处理脚本、数小时内可完成,零下载成本。

### 4.2 B 类:需下载外部数据

| 字段 | 属于 | 外部数据源 | 获取方式 | 优先级 |
|------|:---:|-----------|---------|:---:|
| precipitation(降雨) | D | ERA5-Land total_precipitation | Copernicus CDS API(免费,需注册) | P0 必需 |
| temperature_2m(气温) | D | ERA5-Land 2m_temperature | 同上 | P0 必需 |
| soil_moisture(土壤湿度) | D | ERA5-Land volumetric_soil_water | 同上 | P1 |
| evapotranspiration(蒸散发) | D | ERA5-Land total_evaporation | 同上 | P1 |
| solar_radiation(太阳辐射) | D | ERA5-Land ssrd | 同上 | P1 |
| water_distance(精细水系距离) | G | HydroSHEDS / OSM | 手动下载 + 栅格化 | P2 可选 |
| LAI / 火灾 | D | MODIS/VIIRS | NASA Earthdata | P2 可选 |

> [!note] B 类约 5-8 个字段,核心是 ERA5 气象。下载 + 空间时间对齐脚本另需时间(见 §7.4)。

### 4.3 D(外生驱动)完整字段设计

> [!tip] 说明:elevation/slope 等虽在动力学中调制 D 的效果,但本质是静态的,归入 G。此处 D 只列「随时间变化」的字段。

**核心字段(core)**:

| 字段                 | 物理意义        | 数据源             | 为什么需要                     |
| ------------------ | ----------- | --------------- | ------------------------- |
| precipitation      | 累积降水量(mm)   | ERA5-Land 0.1°  | 洪水第一驱动;植被水分限制;是最强外生驱动     |
| temperature_2m     | 2 米气温(°C)   | ERA5-Land       | 植被物候(积温)、融雪、蒸散发核心参数       |
| soil_moisture      | 表层土壤含水量     | ERA5-Land 0-7cm | 产流前提(饱和土→产流);比降雨更直接反映可用水分 |
| evapotranspiration | 实际蒸散发(mm)   | ERA5-Land       | 闭合水量平衡 ΔS=P−ET−R;植被活力指标   |
| solar_radiation    | 地表短波辐射      | ERA5-Land       | 光合作用能量源;融雪速率              |
| ndvi_previous      | 前一时刻植被指数    | S2 波段计算         | 植被状态历史反馈(自回归基线)           |
| day_of_year        | 年积日 sin/cos | 时间戳             | 编码季节周期,物候节律               |

**增强字段(enhancement,有则更好)**:wind_speed(风速)、snow_depth(雪深)、runoff(径流)、vapor_pressure_deficit(水汽压差)、LAI(叶面积指数)、fire_mask(火灾)。

**可选字段(optional,未来扩展)**:human_activity_proxy(夜光/道路密度)、irrigation(灌溉)、soil_texture(土壤质地)。

**驱动字段的物理耦合**(供动力学模块参考):

- 水量平衡:precipitation − evapotranspiration ± soil_moisture ≈ 产流
- 能量-水分:temperature + solar_radiation → evapotranspiration
- 植被响应:ndvi_previous × (precipitation, temperature, radiation) → 未来 NDVI

### 4.4 G(地理先验)完整字段设计

**核心字段(core)**:

| 字段 | 物理意义 | 来源 | 为什么需要 |
|------|---------|------|-----------|
| elevation | 高程(m) | SSL4EO DEM | 所有地形派生的基础;洪水低洼优先淹没 |
| slope | 坡度(°) | DEM 派生 | 产流速度、侵蚀、约束洪水传播 |
| aspect | 坡向(°) | DEM 派生 | 影响太阳辐射、蒸散发、融雪时序 |
| flow_direction | 水流方向(D8) | DEM 派生 | 定义水流拓扑,预测洪水路径必需 |
| flow_accumulation | 汇流累积面积 | flow_direction 派生 | 识别河网与汇流区(高值=易涝) |
| lulc_static | 土地覆盖背景 | SSL4EO LULC | 参考态;不同地类物理参数不同 |
| lulc_stability | 稳定度(0-1) | LULC 时序 | 区分稳定区 vs 易变区 |
| impervious_fraction | 不透水比例 | LULC 映射 | 高不透水→快速产流→城市内涝 |
| water_body_mask | 永久水体掩码 | LULC/flow_acc | 洪水检测的基准水体 |
| distance_to_water | 到水体距离(m) | 距离变换 | 近水风险高;影响河岸植被、土壤湿度 |

**增强字段(enhancement)**:TWI(地形湿度指数)、TPI(地形位置指数)、curvature(曲率)、TRI(地形粗糙度)、drainage_density(排水密度)、solar_radiation_potential(潜在太阳辐射)、vegetation_potential_index(植被潜力指数)。

> [!warning] 关于 G 的一个重要经验
> 文献中有案例:朴素地把 DEM 当一个额外输入通道,反而使洪水分割精度下降(IoU 0.672→0.661);需要专用编码路径 + 注意力/门控才稳定获益(升到 0.695)。**因此 G 必须做 w/o G 消融验证其真实贡献,不能想当然认为「加了就有用」。**

### 4.5 h(预测跨度)设计

| 维度 | 设计 |
|------|------|
| 表示方式 | 连续标量,单位:天(continuous scalar days) |
| 各任务典型范围 | 洪水 1-7 天;植被 7-180 天;作物 30-270 天;土地覆盖 90-730 天 |
| 编码方式 | log(h) 与状态特征拼接,再过 MLP(diminishing information over time) |
| 是否多尺度 | 是,单模型支持多个 h |
| 训练采样 | log-uniform 采样 h + 时间距离加权 loss;课程式从短到长 |

---

## 5. 缺失字段处理:不同数据集缺不同字段怎么办

> [!important] 前提认知
> 缺失是遥感多数据集训练的**常态,不是意外**。SSL4EO 无洪水标签、EarthNet 无 S1、Sen1Floods11 无长时序——这是必然的。整套机制就是为了让缺失「优雅降级」而不是「崩溃或造假」。

### 5.1 先分清两种缺失(处理方式完全不同)

| 缺失类型 | 例子 | 处理方式 |
|---------|------|---------|
| **输入字段缺失**(喂给模型的) | precipitation、DEM、temperature | field_mask=0 + 缺失嵌入,模型照常前向 |
| **监督标签缺失**(算 loss 用的) | flood_mask、LULC 真值 | 任务头门控,不激活对应 loss |

### 5.2 输入字段缺失:field_mask + 缺失嵌入

> [!danger] 错误做法:缺失字段填 0
> 若 precipitation 缺失填 0,模型会以为「这里真的没下雨」,学到错误因果。**0 是一个真实数值,不等于「未知」。**

**正确做法**:

1. `field_mask[precipitation] = 0` 标记该字段不存在
2. 用一个**可学习的缺失嵌入(learnable missing embedding)** 替代该字段的编码,等价于告诉模型「此项未知,不要当真」
3. 模型据 field_mask 知道这路信息不可信,自动降低其权重

这套机制你的项目已有基础——phi_v3 的 S1 无云字段就是这样处理的(见 [[phi-parquet-nan-int-fields]] 与 14 号文档的 NaN 修复)。

### 5.3 监督标签缺失:任务头门控(task_id)

- Sen1Floods11 有洪水标签 → 激活洪水任务头,计算洪水 loss
- SSL4EO 无洪水标签 → 洪水任务头对它关闭,不计算该 loss
- 用 `task_id` 字段标记「本样本参与哪些任务的训练」,loss 按 task_id 门控

### 5.4 训练时模态随机丢弃(提升鲁棒性)

为让模型天生适应缺失,训练时故意以一定概率(如 10%)随机丢弃本来存在的字段,逼模型学会「缺某项也能预测」。部署到真实缺字段的数据集时性能不会骤降。Prithvi 对 metadata 就用了这种随机 drop。

### 5.5 先例

| 方法 | 缺失处理 |
|------|---------|
| PRESTO | 任意模态/波段可缺,用 masking |
| Galileo(2024) | 多种遥感模态,缺失模态直接 mask |
| DOFA(2024) | 动态生成权重,适配不同波段数 |
| OmniSat(ECCV 2024) | 每模态独立编码,缺失不参与 |
| Prithvi | metadata 随机 drop 提升鲁棒 |

---

## 6. 多数据集如何统一:不缝合,用统一 schema + 适配器

这一节回答「多个数据集是缝合成一个新数据集,还是各自读取后统一进模型」。

### 6.1 结论先行

> [!important] 不物理缝合,用逻辑统一
> 顶会主流做法是**「统一 schema + 每个数据集一个适配器 + 采样器混合」**,而**不是**把数据集重采样对齐后拼成一个巨大新文件。你的 07/10 号文档也已选了这条路(「不要拼成一个大锅」)。

### 6.2 为什么不物理缝合

| 问题 | 说明 |
|------|------|
| 分辨率/坐标系不同 | SSL4EO 10m、EarthNet 20m、Planet 3m,物理上无法直接拼 |
| 波段数不同 | S2 12 波段、Planet 4 波段,拼不到一起 |
| 存储爆炸 | 重复存储,数据量翻数倍 |
| 失去溯源 | 出问题不知是哪个数据集导致 |
| 无法灵活增减 | 想加/删一个数据集要重新缝合全部 |

### 6.3 统一 schema + 适配器架构

```text
DatasetA 读取器(适配器)─┐
DatasetB 读取器(适配器)─┼→ 统一样本字典 ─→ collate ─→ 模型
DatasetC 读取器(适配器)─┘   {image, phi, D, G, h,
                              labels, field_mask,
                              dataset_id, task_id}
```

- 每个数据集写一个**适配器**,把各自原始格式翻译成**统一样本字典**(相同的 key)
- 所有数据集输出的字典结构一致,只是 field_mask 标记各自缺什么
- 加 `dataset_id`(来源)和 `task_id`(参与哪个任务)两个字段
- 模型和 loss 根据这两个字段决定如何处理

### 6.4 batch 如何组织、如何采样

| 策略 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| **同质 batch**(推荐) | 每个 batch 只来自一个数据集,step 间轮换 | 不同 shape 不冲突,简单 | 梯度按数据集波动 |
| 混合 batch | 一个 batch 混多数据集 | 梯度更稳 | 不同分辨率/波段需 padding+mask,复杂 |

**对本项目(各数据集分辨率、波段差异大),推荐同质 batch + 数据集轮换**——这也是 Stage 1 已用的 WebDataset 分片轮换思路的延伸。采样比例可加权(大数据集或重要任务多采,类似多语言温度采样)。

### 6.5 先例

| 系统 | 做法 |
|------|------|
| TorchGeo(遥感标准库) | 每数据集一个类,统一 DataLoader,UnionDataset 逻辑合并非物理合并 |
| TerraTorch / Prithvi | 数据集模块化,各自适配器 → 统一接口 |
| ClimaX | 变量 tokenization,不同数据集变量不同也能统一进模型 |
| PRESTO | 统一像素时序格式,各来源映射进来,缺失 mask |
| PyTorch 通用 | ConcatDataset/interleave 是 DataLoader 层逻辑合并,不动原始文件 |

---

## 7. 数据获取与处理流程

> [!note] 统一范式
> 所有 dgh 字段都沿用 phi_v3 的范式:**离线抽取 → 存成 parquet → 训练时按 sample_key join**。不在训练时在线计算,便于复现和验证。

### 7.1 SSL4EO 已有字段(直接读)

- DEM:zarr['dem'],已对齐,直接读
- LULC:zarr['lulc'],直接读
- 时间戳:zarr['time'](纳秒单位),用于算 h
- phi_v3(季节、太阳角、云、经纬度):已在 phi_processed_v3/

### 7.2 从 DEM 派生(流程)

1. 读取 DEM
2. 求梯度 → slope、aspect(scipy Sobel)
3. 填洼(fill sinks)→ D8 算法 → flow_direction(pysheds/richdem)
4. flow_direction → 递归上游计数 → flow_accumulation
5. flow_accumulation + slope → TWI = ln(flow_acc/tan(slope))
6. 高值字段(flow_acc)做 log 变换压缩动态范围

### 7.3 从 LULC 派生(流程)

1. 读取 LULC 时序
2. mode 频率 → lulc_stability
3. 查找表映射(urban=0.85, forest=0.05...)→ impervious_fraction
4. LULC==水体 或 flow_acc>阈值 → water_body_mask
5. water_body_mask 距离变换 → distance_to_water

### 7.4 ERA5-Land 下载(详细流程)

> [!important] 这是唯一需要「先申请、再下载」的外部数据,建议今天就开始申请(排队慢)。

**步骤**:

1. **注册 Copernicus CDS 账号**:访问 cds.climate.copernicus.eu,注册,获取 API key(免费)
2. **配置本地**:安装 cdsapi 库,把 API key 写入 ~/.cdsapirc
3. **确定下载范围**:从 SSL4EO 所有样本的 center_lat/lon 求 min/max,得到覆盖的经纬度边界框 + 时间范围(样本时间戳的最早到最晚)
4. **提交下载请求**:请求 ERA5-Land 的 total_precipitation、2m_temperature 等变量,按边界框和时间范围下载,存为 zarr/netCDF
5. **等待**:CDS 有排队,大范围请求可能等 1-7 天

**空间/时间对齐(join)**:

- 空间:ERA5 是 0.1°(~9km)格点,遥感是 10m。对每个样本的 center_lat/lon,从 ERA5 格点**双线性插值**取值
- 时间:样本时间戳匹配到最近的 ERA5 时刻;对 [t, t+h] 区间做聚合(降雨求和、温度取均值/极值)
- 边界处理:时间戳超出 ERA5 覆盖 → field_mask=0,用季节气候平均兜底或标缺失

> [!warning] 分辨率不匹配是已知事实,论文要写明
> ERA5(~9km)远粗于 Sentinel(10m),它提供的是「区域气象」而非「逐像素气象」。这是外生驱动 D 的固有局限,应作为**弱驱动**处理,做敏感性分析而非强因果断言。

### 7.5 HydroSHEDS(可选,P2)

若需要比「从 LULC 派生」更精确的水系距离:手动下载 HydroSHEDS 水系矢量 → 栅格化 → 距离变换。数据量约 10GB。洪水任务精度不够时再考虑。

### 7.6 存储:parquet + sample_key + 版本管理

- **格式**:parquet(与 phi_v3 一致)
- **目录**:TrainData/SSL4EO-S12-v1.1/dgh_processed/{version}/{split}/
- **主键**:sample_key(= tar __key__,与 phi 对齐)
- **粒度**:每(modality, split)一个 parquet
- **版本**:

| 版本 | 字段 | 外部数据 | 用途 |
|------|------|---------|------|
| dgh_v1_minimal | DEM/slope/aspect/flow/lulc/water/season/h | 无 | Stage2 骨架训练,验证架构 |
| dgh_v2_era5 | v1 + 降雨/温度/土壤湿度等 | ERA5-Land | 完整驱动消融、洪水任务 |
| dgh_v3_hydro | v2 + 精细水系距离 | HydroSHEDS | 空间先验消融、论文完整性 |

> [!note] 版本演进原则:只加列不删列。旧版本永远可用;新增字段用 field_mask 标记,缺失优雅降级。

---

## 8. 实施路线图

> [!important] 核心判断:Stage 2 训练不必等 ERA5。dgh_v1(全部 A 类字段)就足够启动骨架训练验证架构。ERA5 到货后再升级到 v2。

### 8.1 三条并行准备线

**A 线(立即可做,不依赖外部)**:

1. 构建 dgh_v1_minimal(全部 A 类字段)→ parquet
2. 改造数据加载器(新增时序 dataset,join dgh parquet)
3. 实现 StateDynamicsModule(z_t + D + G + h → z_{t+h})

**B 线(今天启动,后台排队)**:

4. 申请 Copernicus CDS 账号(5 分钟)
5. 配置并提交 ERA5-Land 下载请求(排队 1-7 天)

**C 线(ERA5 到货后)**:

6. 构建 dgh_v2_era5(空间/时间 join)

### 8.2 分阶段执行

| 阶段 | 内容 | 依赖 | 预计工作量 |
|------|------|------|-----------|
| Stage 0 | 盘点 SSL4EO 现有字段 + phi_v3 覆盖,验证 sample_key join 一致 | 无 | 1 天 |
| Stage 1a | 写 build_dgh_v1.py,算全部 A 类字段,输出 parquet | 无 | 2-3 天 |
| Stage 1b | 质量验证(range/NaN/join 覆盖率),smoke test | Stage1a | 1 天 |
| Stage 2a | 下载 ERA5-Land 降雨/温度(申请今天就做) | CDS 账号 | 下载 1-7 天(排队) |
| Stage 2b | 写 join_era5_to_dgh.py,空间时间对齐,输出 dgh_v2 | Stage2a | 2-3 天 |
| Stage 3 | (可选)HydroSHEDS 水系距离 → dgh_v3 | — | 3-4 天 |
| Stage 4 | 集成进 StateDynamicsModule,dataloader 返回 D/G 字典 | dgh_v1 | 2-3 天 |
| Stage 5 | 验证 + field_mask 生效 + w/ vs w/o 消融 | Stage4 | 1-2 天 |

### 8.3 现在的最优行动路径

```text
今天    : 申请 CDS 账号 + 开始写 build_dgh_v1.py
本周    : dgh_v1 就绪 → 改数据加载器 → 写 StateDynamicsModule
下周    : 用 dgh_v1 训练 Stage 2 骨架(验证架构),同时等 ERA5
第 2-3 周: ERA5 到货 → 构建 dgh_v2 → 完整驱动消融训练
```

### 8.4 Stage 2 就绪判据

> [!tip] 什么程度的 dgh 就能开始 Stage 2
> **dgh_v1_minimal 即可启动。** 动力学模块需要地理约束(DEM/slope/lulc)和时间信息(h)来学习合理转移,降雨是「驱动增强」不是「启动阻塞」。
>
> 决策规则:若 dgh_v1 在 DynamicEarthNet 上产生合理状态转移(森林留在山上、水在谷底),再升级 v2;若转移随机,先修动力学模块,不急着加数据。

### 8.5 风险与兜底

- **ERA5 下载卡住(CDS 排队 >1 周)**:直接用 dgh_v1 开训,以 season_index 作代理弱驱动;模型已预留驱动编码器槽位,ERA5 事后集成即可。
- **每个版本向后兼容**:v2 构建失败,v1 仍可用;field_mask 保证缺字段优雅降级而非崩溃。

---

## 9. 三个具体实例(展示最终数据结构)

> [!note] 以下数值为示意,展示 D/G/h 字段的组织形式与合理取值范围。

### 9.1 洪水场景:强降雨驱动快速积水

```yaml
scenario: 洪水预测 - 季风暴雨
h: 12 小时(短跨度)
预期状态变化: 从正常态转为淹没态,水位上升 1.5-3.2m,淹没范围扩大 240%
D(外生驱动,随时间变):
  precipitation_cumulative: 287.3 mm    # 区间累积降雨(强)
  precipitation_intensity: 23.9 mm/h
  soil_moisture: 82.5%                   # 土壤已近饱和(产流前提)
  temperature: 28.3 °C
G(地理先验,静态):
  elevation: 12.3 m                      # 低洼
  slope: 0.7°                            # 平坦易积水
  flow_accumulation: 高                  # 汇流区
  distance_to_water: 340 m               # 近河高风险
  impervious_fraction: 0.18
  TWI: 8.7                               # 高地形湿度指数
field_mask: precipitation/soil_moisture/elevation/slope 均有效
```

### 9.2 植被场景:季节转换驱动返青

```yaml
scenario: 植被物候 - 干季转湿季
h: 30 天
预期状态变化: NDVI 0.68 → 0.82,冠层从旱季末转早湿季
D(外生驱动):
  precipitation_cumulative: 142.5 mm
  temperature_mean: 26.8 °C
  solar_radiation: 18.3 MJ/m²/day        # 光合能量
  growing_degree_days: 234.5             # 积温
  ndvi_previous: 0.68                    # 历史状态反馈
G(地理先验):
  elevation: 287 m
  aspect: 210°                           # 坡向影响受光
  lulc_static: 常绿阔叶林
  distance_to_water: 850 m
  vegetation_potential_index: 高          # 约束 NDVI 上限
field_mask: 气象字段有效;火灾字段无效(field_mask=0)
```

### 9.3 土地覆盖变化场景:城市化

```yaml
scenario: 土地覆盖变化 - 城市扩张
h: 90 天
预期状态变化: 农田 → 建成区,不透水面 0.08 → 0.72
D(外生驱动 / 人类活动代理):
  # 注意:城市化驱动多为社会经济量,属弱驱动,数据难获取
  season/time_delta: 有效
  precipitation/temperature: 有效(弱相关)
  population_growth 等社会经济量: 多数 field_mask=0(公开数据难获取)
G(地理先验):
  slope: 2.1°                            # 平坦可建
  distance_to_urban: 近                  # 城市扩张前沿
  surrounding_urban_fraction: 0.34
  lulc_stability: 低                     # 易变区
  lulc_static: 农田
field_mask: 地形/邻域字段有效;社会经济驱动多数无效
```

> [!warning] 城市化场景的诚实声明
> 城市扩张的真正驱动(人口、GDP、政策)是社会经济量,公开遥感数据拿不到。这类样本的 D 大量 field_mask=0,只能靠 G(地形可建性、邻近已有城市)和弱驱动。论文中应明确:城市化是**弱驱动任务**,不做强因果声明。这与 07 号文档「诚实区分强/弱驱动」一致。

---

## 附录 A:FAQ 知识点问答

> [!note] 本附录以问答形式覆盖零散但重要的知识点,供随时查阅。

**Q1:为什么不直接用 EarthNet2021 作主数据?它自带天气 forcing 不是更省事?**

EarthNet2021 确实自带 E-OBS 天气 forcing 和 EU-DEM,是 D/G 现成打包的好数据。但起点选 SSL4EO 是因为:(1)Stage 1 编码器已在 SSL4EO 上训练,权重可无缝继承;(2)SSL4EO 基础设施(zarr 读取、phi、FSDP)已成熟;(3)EarthNet 只覆盖欧洲、只有 RGB+NIR、20m 分辨率,泛化性不如 SSL4EO 全球多模态。**正确定位:SSL4EO 打基础和验证架构,EarthNet 作为像素预测和驱动主数据在 Stage 2b 引入。**

**Q2:ERA5 是 ~9km 的气象数据,能对齐到 10m 的遥感影像吗?**

能对齐(双线性插值到样本中心点),但要认清这是「区域气象」不是「逐像素气象」。同一个 ERA5 格点覆盖约 900 个 Sentinel 像素,它们共享同一个降雨值。**因此 ERA5 驱动应作为弱驱动**,做敏感性分析(降雨多→洪水概率上升)而非逐像素强因果。论文中必须写明这个分辨率不匹配的固有局限。

**Q3:如果 CDS 下载太慢(排队一周)怎么办?**

不阻塞。dgh_v1(全部 A 类字段,不含 ERA5)就能启动 Stage 2 骨架训练。用 season_index 作代理弱驱动先跑通架构。模型已预留驱动编码器槽位,ERA5 到货后升级到 dgh_v2 即可,无需改架构。

**Q4:dgh_v1 能训多久?什么时候切到 v2?**

用 dgh_v1 训 5-10k 步,验证:动力学模块不崩、loss 收敛、状态转移合理(森林留在山上、水在谷底)。若合理,集成 dgh_v2 继续训并做「有降雨 vs 无降雨」消融;若转移随机,先修动力学模块,不急着加数据。

**Q5:引入其他数据集后,字段清单要重新设计吗?**

不用。字段清单(schema)是一次性设计的超集,加数据集主要是「填空」(不同数据集填不同子集,缺的标 field_mask=0),偶尔「加列」(引入全新字段类型,如洪水事件标注)。已有字段的定义几乎不动。

**Q6:多个数据集缺不同字段,会不会导致 batch 里字段对不齐?**

不会。所有数据集通过适配器输出**相同结构的样本字典**(相同 key),缺的字段用缺失嵌入占位 + field_mask=0 标记。batch 内结构一致,只是 mask 不同。

**Q7:输入字段缺失和标签缺失处理一样吗?**

不一样。输入字段缺失(如没降雨数据)→ field_mask=0 + 缺失嵌入,模型照常前向;监督标签缺失(如没洪水标签)→ 任务头门控(task_id),不激活该 loss。

**Q8:多数据集是缝成一个大文件吗?**

不是。用「统一 schema + 每数据集一个适配器 + 采样器轮换」的逻辑统一,不物理缝合。原因:分辨率/波段/坐标系不同无法物理拼、存储爆炸、失去溯源、无法灵活增减。

**Q9:一个 batch 里要混多个数据集吗?**

不必。推荐「同质 batch + 数据集轮换」——每个 step 从一个数据集取 batch,step 间轮换。避免不同分辨率/波段的 padding 复杂性。采样比例可加权。

**Q10:加入新数据集时,已训好的权重要丢掉重训吗?**

不要。整个 ObsWorld 只有 Stage 1 从零训,之后全部「加载上一阶段权重 + 新增模块 + 继续训练」。编码器学到的通用表征跨数据集有效,重训是浪费且会遗忘。

**Q11:多个数据集是一个个顺序训练吗?**

不是。顺序训练会灾难性遗忘(学了后面忘了前面)。用联合训练:多数据集统一 schema + 采样器混合,同一模型同时见到所有数据集,用 field_mask 和 task_id 门控。

**Q12:编码器在 Stage 2 要冻结还是微调?**

分两步:先冻结,只训新增动力学模块(稳定、省显存、验证架构);再解冻,用小学习率(约主 lr 的 1/10)联合微调。

**Q13:D 和 G 有重叠字段(如 elevation、slope 两边都提到),矛盾吗?**

不矛盾,是分类视角不同。elevation/slope 本质是**静态的**,归入 G;但它们会**调制 D 的效果**(如陡坡让降雨更快产流),所以在讨论驱动机制时会一起出现。存储上归 G(静态,每样本算一次),不要在 D 里重复存。

**Q14:h(预测跨度)为什么要显式告诉模型?**

因为同样的 z_t 和驱动,预测 7 天后和 30 天后的结果完全不同。h 让单个模型支持多时间尺度预测。编码方式:log(h) 与状态特征拼接过 MLP。

**Q15:为什么 G 要做 w/o G 消融,不能默认「加了就有用」?**

文献中有反例:朴素把 DEM 当额外通道反而使洪水分割精度下降(IoU 0.672→0.661),需专用编码路径 + 门控才获益。所以必须用「有 G vs 无 G」消融证明 G 的真实贡献,这也是世界模型能力实验的一部分(证明模型真在用地理先验)。

**Q16:ndvi_previous 算 D 还是状态?它有点像既是输入又是状态。**

它是「状态的历史反馈」,介于输入和状态之间。实践上作为 D 的一个字段喂入(自回归基线),帮助模型锚定植被当前水平。若编码器已能从 z_t 解出植被信息,它可作为辅助/冗余信号。

**Q17:phi 和 D/G 会不会功能重叠?比如 season 两边都有。**

season 在 phi 里是「成像条件」(不同季节拍出来外观不同),在 D 里是「弱驱动」(季节推动物候变化)。同一个物理量在不同模块服务不同目的,这是合理的,不算冗余。关键是 phi 作用在编码器/解码器,D 作用在动力学模块。

**Q18:整个 dgh 数据准备,最少需要做什么就能开始 Stage 2?**

三件事:(1)构建 dgh_v1_minimal(全 A 类字段,数小时批处理);(2)改数据加载器 join dgh;(3)实现 StateDynamicsModule。ERA5 可并行等待,不阻塞启动。

---

## 附录 B:字段速查表

### D 外生驱动(随时间变)

| 字段 | 层级 | 来源类型 |
|------|:---:|:---:|
| precipitation | core | B 类(ERA5) |
| temperature_2m | core | B 类(ERA5) |
| soil_moisture | core | B 类(ERA5) |
| evapotranspiration | core | B 类(ERA5) |
| solar_radiation | core | B 类(ERA5) |
| ndvi_previous | core | A 类(S2 波段) |
| day_of_year / season | core | A 类(时间戳) |
| wind / snow / VPD / LAI / fire | enhance | B 类 |

### G 地理先验(静态)

| 字段 | 层级 | 来源类型 |
|------|:---:|:---:|
| elevation | core | A 类(SSL4EO DEM) |
| slope / aspect | core | A 类(DEM 派生) |
| flow_direction / flow_accumulation | core | A 类(DEM 派生) |
| lulc_static / lulc_stability | core | A 类(SSL4EO LULC) |
| impervious_fraction | core | A 类(LULC 派生) |
| water_body_mask / distance_to_water | core | A 类(LULC 派生) |
| TWI / TPI / curvature / TRI | enhance | A 类(DEM 派生) |
| 精细水系距离 | enhance | B 类(HydroSHEDS) |

### h 预测跨度

| 字段 | 来源类型 |
|------|:---:|
| time_delta / horizon | A 类(时间戳差) |

> [!info] A 类 = 直接可算(无需下载);B 类 = 需下载外部数据。core = 核心必需;enhance = 增强可选。
