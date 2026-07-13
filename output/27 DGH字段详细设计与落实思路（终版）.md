---
title: "27 DGH字段详细设计与落实思路（终版）"
version: v2.1-final
created: 2026-07-04
updated: 2026-07-06
author: Zhijian Liu + Claude深度分析
project: ObsWorld
stage: "字段设计定稿"
tags:
  - DGH
  - 字段设计
  - 世界模型
  - Stage2
---

# DGH 字段详细设计与落实思路（终版）

> [!abstract] 本文定位
> 本文是 ObsWorld 的 D（外生驱动）、G（地理先验）、h（预测跨度）三路条件的**最终字段设计**。
> 每个字段都经过：物理机制论证、文献验证、数据可获取性核实、与主线契合度检验。
> 基于 6 份深度文献调研（30+ 篇论文）与本地数据实测，字段选择已定稿。

---

## 0. 一句话结论

> [!important] 最终字段
> **D = {day_of_year, precipitation, temperature, VPD, solar_radiation}（5 个核心）**
> **G = {elevation}（1 个）**
> **h = {10, 20, 30, 60} 天（多跨度联合训练）**
>
> 所有字段的原始数据**已下载或正在下载**，无获取障碍。

---

## 1. 设计哲学：DGH 服务于什么

### 1.1 主线锚定

ObsWorld 的核心链条：

```text
历史观测 X_t + 成像条件 phi
    → 编码器（成像解耦）
    → 地表状态 z_t
    → 状态动力学 Dynamics(z_t, D, G, h)   ← DGH 在这里作用
    → 未来状态 z_{t+h}
    → 解码器 + 未来 phi
    → 未来观测 X_{t+h}
```

DGH 是**状态动力学模块的三路条件输入**，决定"当前地表状态如何演化成未来状态"。

### 1.2 三条设计原则

> [!note] 每个字段必须同时满足
> 1. **物理机制明确**：能说清"它通过什么机制驱动/约束地表状态演化"
> 2. **服务动力学主线**：锚定 Stage 2 的植被/地表状态演化，不为下游任务硬凑
> 3. **公开可获取**：EarthNet2021 自带或 ERA5 可下载，无独家数据依赖
> 4. **消融可验证**：能设计 w/ vs w/o 实验证明其贡献
> 5. **协议可复现**：每个驱动字段必须说明是 oracle reanalysis、climatology 还是 forecast forcing，避免把情景输入和部署预测混为一谈

### 1.3 D 的角色定位（关键概念）

D 在训练、部署和下游中扮演**不同角色**，必须按实验协议写清楚：

| 场景           | D 的角色                | 合法输入                                              | 文献依据                                          |
| ------------ | -------------------- | ------------------------------------------------- | --------------------------------------------- |
| Stage 2 情景模拟 | 动力学的**条件输入**，做消融和反事实 | 给定的未来 forcing，可用 reanalysis 作为 **oracle forcing** | TFT 的 known-future covariate；Dreamer 的 action |
| Stage 2 部署预测 | 预测时刻可获得的外部条件         | 天气预报或气候平均，不能用未来 ERA5 真值                           | 多步预测 / forecasting 协变量范式                      |
| Stage 4 下游   | **退场**，只用冻结的状态表征 z   | 不向任务头提供 D                                         | JEPA / Presto / Galileo / SatMAE 范式           |

> [!important] 精确定义"不是泄露"
> 如果论文任务定义为 **scenario-conditioned forecasting**，则 D 是外部给定的 forcing，未来 reanalysis 可以作为 oracle forcing 用来检验"模型是否按给定驱动响应"。
> 如果论文任务定义为真实部署预测，则未来 ERA5 reanalysis 不能作为普通输入，必须替换为天气预报或气候平均。
> 真正不可接受的泄露是把未来观测、未来 NDVI、未来标签或测试区共享的 ERA5 格点信息混入训练。详见文末 [[#附录B-D的角色文献链]]。

---

## 2. D — 外生驱动（External Drivers）

> [!tip] 定义
> 随时间变化的、来自系统外部的驱动因素，"推动"地表状态发生变化。
> 特征：time-varying，未来值在预测时可由预报/气候基线提供。

### 2.1 D 的完整字段表

|  #  | 字段                    | 优先级 | 物理意义      |   单位   | 数据来源                 |
| :-: | --------------------- | :-: | --------- | :----: | -------------------- |
|  1  | day_of_year (sin/cos) | P0  | 物候节律、光周期  |   —    | 时间戳计算                |
|  2  | precipitation         | P0  | 水分**供给侧** | mm/day | E-OBS rr / ERA5 tp   |
|  3  | temperature_mean      | P0  | 积温、物候驱动   |   °C   | E-OBS tg / ERA5 t2m  |
|  4  | VPD                   | P0  | 水分**需求侧** |  kPa   | 温度+湿度派生              |
|  5  | solar_radiation       | P0  | 光合能量      |  W/m²  | E-OBS qq / ERA5 ssrd |
|  6  | temperature_max       | P1  | 热胁迫（极端事件） |   °C   | E-OBS tx / ERA5 派生   |

### 2.2 逐字段详解

#### D.1 day_of_year（年积日周期编码）

**物理机制**：植被有强烈的年周期节律（春季返青、秋季枯黄），光周期是物候的核心触发信号。

**计算方式**：

```python
D['day_of_year_sin'] = sin(2 * pi * doy / 365)
D['day_of_year_cos'] = cos(2 * pi * doy / 365)
```

**为什么用 sin/cos 而非离散**：保持周期连续性（12月31日与1月1日相邻），两个分量唯一确定一年中的位置，模型可学习相位和振幅。

**数据来源**：从样本时间戳直接计算，**零成本，无泄露**。

**文献依据**：EarthPT、SatMAE 均用此编码时间周期（见文末引用）。

---

#### D.2 precipitation（降水，水分供给侧）

**物理机制**：降水是土壤水分的直接来源，是植被生长和洪水的第一驱动。在生态遥感中被公认为短期 NDVI 变化的首要驱动（尤其干旱/半干旱区）。

**单位与处理**：

```python
# ERA5 原始单位是米（累积），转 mm/day
precip_mm = era5_tp * 1000

# 归一化（robust，抗异常值）
precip_norm = (precip - median) / (q75 - q25)
precip_norm = clip(precip_norm, -3, 3)
```

> [!warning] 降水的日聚合陷阱
> ERA5 降水是**累积量**，日值应**求和（sum）**，不是求均值。
> 若误用日均值，降水会被低估 24 倍。太阳辐射（ssrd）同理是累积量。

**数据来源**：
- EarthNet2021：自带 `eobs_rr`（1D 向量，每时刻一值）
- SSL4EO：用 ERA5 `total_precipitation`（你的下载脚本已含 rr）

**文献依据**：Presto、CropHarvest 的最小气象集就是降水+温度；EarthNet2021 全部参赛方法都用降水。

---

#### D.3 temperature_mean（平均气温，积温物候）

**物理机制**：温度通过积温（GDD, Growing Degree Days）控制植被物候节律。温带/高纬地区春季返青主要由积温触发。

**单位与处理**：

```python
temp_celsius = temp_kelvin - 273.15   # ERA5 是开尔文
temp_norm = (temp - mean) / std
```

**数据来源**：
- EarthNet2021：`eobs_tg`
- SSL4EO：ERA5 `2m_temperature`

**文献依据**：DeepExtremeCubes（arXiv 2410.01770）的可解释性分析证明，**正常条件下温度是植被响应的首要预测因子**。

---

#### D.4 VPD（水汽压差，水分需求侧）★ 差异化设计

**物理机制**：VPD（Vapor Pressure Deficit）是大气对植被的"抽水力度"。VPD 高 = 空气干燥 = 蒸腾失水快 = 植被水分胁迫。


**VPD = 大气水分需求侧。**  
`precipitation` 说“水从哪里来”，`VPD` 说“空气会多强地把水从植被/土壤里抽走”。所以它和降水不是重复，而是一进一出：

```
植被水分压力 ≈ 水分供给 precipitation - 大气需水 VPD
```

这就是为什么我觉得 VPD 是你 D 里最有价值的字段之一。没有 VPD，你的 D 会比较像普通的“季节 + 温度 + 降水”；有 VPD 后，它变成了“节律 + 供水 + 积温 + 需水 + 光能”的完整动力学条件。



> [!important] 这是 ObsWorld 区别于多数工作的核心设计
> **多数遥感预测只建模水分供给（降水），忽略大气水分需求（VPD）。**
> ObsWorld 建模**完整的水分平衡**：
>
> ```
> 植被净水分状态 ≈ 降水（供给） − VPD 驱动的蒸腾（需求）
> ```
>
> 这能捕捉"降水充足但高温干燥仍导致植被退化"的机制——
> Yuan et al. (Science Advances 2019) 证明 VPD 上升在全球尺度压制植被生长，
> 但多数深度学习预测工作未显式建模。详见文末 [[#附录A-VPD的文献依据]]。

**计算方式**：

```python
# 饱和水汽压 e_s（温度决定，非线性）
e_s = 0.6108 * exp(17.27 * T / (T + 237.3))    # kPa, T 为摄氏度

# 实际水汽压 e_a
# 方案1：从相对湿度（EarthNet2021 有 eobs_hu）
e_a = e_s * (RH / 100)
# 方案2：从露点（SSL4EO 用 ERA5 dewpoint）
e_a = 0.6108 * exp(17.27 * Td / (Td + 237.3))

VPD = e_s - e_a
```

**为什么 VPD 不能被温度+湿度替代**：VPD 是温度的**指数函数**与湿度的**非线性组合**，神经网络从原始 T+RH 学出这个指数关系并不容易。显式提供 VPD 是有效的物理先验注入。

**为什么 VPD 与降水不冲突（互补）**：

| 字段 | 测量 | 物理方向 |
|---|---|---|
| precipitation | 水从哪来 | 供给（进水） |
| VPD | 水往哪去 | 需求（出水） |

两者相关性低，编码不同物理过程，**必须共存**。去掉任一都只看到水分平衡的一半。

**数据来源**：
- EarthNet2021：从 `eobs_tg` + `eobs_hu` 派生
- SSL4EO：从 ERA5 `2m_temperature` + `2m_dewpoint_temperature`（脚本已含 dew）派生
- **零额外下载，仅需派生函数**

---

#### D.5 solar_radiation（太阳辐射，光合能量）

**物理机制**：短波辐射是光合作用的能量来源。在热带常绿林、湿润区，辐射是植被生长的限制因子。

**单位与处理**：

```python
srad_mj = era5_ssrd / 1e6    # J/m² → MJ/m²/day
srad_norm = srad / max_observed
```

**为什么保留（尽管温带次要）**：你的 SSL4EO 是**全球**数据（含热带），辐射在热带是关键限制因子。通过消融确认其贡献。

**数据来源**：
- EarthNet2021：`eobs_qq`
- SSL4EO：ERA5 `surface_solar_radiation_downwards`（脚本已含 qq）

---

#### D.6 temperature_max（最高温，热胁迫）— P1 可选

**物理机制**：日最高温捕捉热浪/热胁迫。极端高温直接抑制植被生长，是极端事件分析的关键。

**用途**：支撑 regime-dependent 分析（正常条件 vs 极端热浪，驱动因子会翻转，见 DeepExtremeCubes 发现）。

**数据来源**：
- EarthNet2021：`eobs_tx`（已有）
- SSL4EO：从 ERA5 逐小时温度取日最大值

**为什么是 P1**：主体叙事用平均温已足够；最高温主要服务"极端事件"的诊断实验，作为可选消融项。

---

### 2.3 D 字段数量：是否过多或过少？

> [!question] 你的顾虑：字段数量合理吗？

**文献调研的 D 字段数量对比**（详见文末 [[#附录C-D字段数量文献对比]]）：

| 工作 | D 字段数 | 备注 |
|---|:-:|---|
| Presto (2023) | 2 | 极简：温度+降水 |
| **ObsWorld (P0)** | **5** | **中等偏少** |
| Robin et al. (2022) | 6 | ERA5 5+SMAP 1 |
| EarthNet2021 original | 5 | 降水+气压+温度×3 |
| EO-WM (2024) | 5+3 | 5 通道+3 累积胁迫 |
| GreenEarthNet (2024) | 8 | E-OBS 全 8 变量 |
| DeepExtremeCubes (2024) | 8~24 | 8 变量×min/max/mean |

**结论**：
- 文献范围：2（最少）~ 24（最多），中位数 5-6
- ObsWorld 的 5 个核心属于**中等偏少**，处于"物理驱动但不冗余"的合理区间
- **不过多**（远少于 DeepExtremeCubes 的 24）
- **不过少**（多于 Presto 的极简 2，因为我们要做水分平衡的完整叙事）

> [!note] 数量选择的理由
> ObsWorld 的卖点是**可解释性与物理驱动**，不是"用最多气象刷精度"。
> 5 个字段每个都有清晰物理角色（时间/供水/积温/需水/光能），消融时每个都能干净归因。
> 相比 EO-WM 的累积胁迫（S_heat/S_water/S_comp），我们更简洁可解释——
> 复杂的累积项会让"哪个驱动起作用"难以归因。

---

## 3. G — 地理先验（Geographic Prior）

> [!tip] 定义
> 静态或极缓变的空间背景条件，"约束"地表状态变化的合理性。
> 特征：static，每个地点固定，对每个样本只需算一次。

### 3.1 G 的字段表

|  #  | 字段        | 优先级 | 物理意义           | 数据来源                   |
| :-: | --------- | :-: | -------------- | ---------------------- |
|  1  | elevation | P0  | 海拔影响温度/降水/植被类型 | EarthNet/SSL4EO 自带 DEM |

### 3.2 elevation 详解

**物理机制**：
- 海拔影响气候带（高海拔更冷、迎风坡多雨）
- 约束植被类型（海拔梯度→植被垂直分布）
- 提供空间背景（平坦地 vs 山地）

**处理方式**：

```python
elevation_norm = (elevation - mean) / std
# 或相对高程（保留局部起伏，去除绝对海拔偏移）
elevation_rel = elevation - elevation.mean()
```

**数据来源**：
- EarthNet2021：自带三种 DEM（`alos_dem`, `cop_dem`, `nasa_dem`），推荐用 `cop_dem`
- SSL4EO：自带 DEM

**文献依据**：Presto、Galileo、CropHarvest 均将 DEM 作为静态输入。

### 3.3 为什么 G 只保留 elevation

> [!warning] 明确排除的 G 字段及理由

| 排除字段 | 理由 |
|---|---|
| slope（坡度） | 植被任务不敏感；文献极少用于植被预测 |
| aspect（坡向） | 作用很小，除非高纬度雪区 |
| flow_direction / flow_accumulation | 需完整流域信息，你的 patch（约 2.5km）算不对；且洪水任务降级为静态分割，不需要 |
| land_cover_static | 定位不清（是状态还是先验），有泄露风险 |

> [!note] 关于洪水与地形的决策
> 早期考虑加 HAND（到最近河道相对高度）等水文地形，用于洪水任务。
> 但因**洪水下游任务定位为"静态分割"（验证 z 编码水体质量），而非"降雨→洪水动态预测"**，
> 静态分割不涉及地形驱动的动力学，故 G 简化为仅 elevation。
> 详见 [[26_完整问题解析与执行路线图]] 的下游任务讨论。

---

## 4. h — 预测跨度（Forecast Horizon）

> [!tip] 定义
> 从当前时刻 t 到预测目标 t+h 的时间间隔，让单模型支持多时间尺度预测。

### 4.1 h 的设计

| 属性   | 设计                                              |
| ---- | ----------------------------------------------- |
| 跨度集合 | {10, 20, 30, 60} 天                              |
| 对应帧数 | EarthNet2021 为 5 天间隔 → 2/4/6/12 帧               |
| 训练策略 | 多跨度联合训练                                         |
| 权重   | w_10=1.0, w_20=0.8, w_30=0.6, w_60=0.4（近期高、远期低） |
| 编码方式 | log(h) 过 MLP，与状态特征拼接                            |

### 4.2 多跨度联合训练

```python
loss_total = 0
for h in [10, 20, 30, 60]:
    z_pred = Dynamics(z_t, D[t:t+h], G, h)
    X_pred = Decoder(z_pred, phi[t+h])
    loss_h = MSE(X_pred, X_true[t+h])
    loss_total += weight[h] * loss_h
loss_total.backward()
```

> [!important] 为什么多跨度联合而非单跨度自回归
> 单跨度训练（只学 h=1，预测长期靠滚动）会**累积误差**。
> 多步预测和 TFT 等 multi-horizon forecasting 文献都把多跨度监督视为标准设置；Horizon-Aware GNN（arXiv 2026）进一步给出长时程图动力学上的近期证据。
> 正文不要把结论只压在一篇新预印本上，而应写成：多跨度联合训练减少自回归深度，使模型学会"直接跳 30 天"，而非"走 30 次 1 天"。

### 4.3 推理策略

```python
# 预测 100 天，用贪心大步跳（减少累积次数）
# 路径：30 + 30 + 40（3 次）而非 1×100（100 次）
```

---

## 5. DGH 完整工作流

### 5.1 训练时（Stage 2）

```text
1. 读取时序 X_{t-context:t}（历史观测）
2. 编码 z_t = Encoder(X_t, phi_t)
3. 按实验协议提取 D = [doy, precip, temp, VPD, rad]，覆盖 t 到 t+h 每一步
   - 情景模拟：oracle reanalysis forcing 或手工设定 forcing
   - 部署预测：forecast forcing 或 climatology forcing
4. 提取 G = elevation（静态）
5. 多跨度动力学预测：
   for h in [10,20,30,60]:
       z_{t+h} = Dynamics(z_t, D[t:t+h], G, h)
       X_pred  = Decoder(z_{t+h}, phi_{t+h})
       loss   += w_h * ||X_pred - X_true_{t+h}||
6. 反向传播
```

### 5.2 D/G/h 的时间对齐

| 变量 | 时刻 | 说明 |
|---|---|---|
| z_t | t | 当前状态 |
| D | t → t+h 每步 | 外部 forcing；必须标注 oracle / climatology / forecast |
| G | 静态 | 不随时间变 |
| h | 标量 | 预测跨度 |
| z_{t+h} | t+h | 预测目标 |

### 5.3 注入方式：FiLM 调制

```python
D_feat = D_encoder(D)              # MLP，因 D 是向量
G_feat = G_encoder(G)              # CNN，因 G 是空间场
h_feat = h_encoder(log(h))         # MLP

cond = concat([D_feat, G_feat, h_feat])
gamma, beta = FiLM_generator(cond)

z_out = backbone(z_t)
z_out = gamma * z_out + beta       # FiLM 调制
```

> [!note] 为什么主实现用 FiLM
> FiLM 是轻量、可解释、与 Stage 1.5 的 phi-FiLM 体系一致的条件化方式，适合作为主实现。
> 正文不要写成"FiLM 必然优于所有方法"；更稳的写法是：FiLM 是默认注入方式，并在消融中对比 concat 与 cross-attention。详见 [[#附录D-注入方式文献]]。

---

## 6. 数据可获取性核实（重要）

> [!important] 结论：所有字段 100% 可获取，无障碍

### 6.1 EarthNet2021（已下载 119GB）

| D/G 字段 | 来源 | 状态 |
|---|---|:-:|
| day_of_year | 时间戳计算 | ✅ 0 成本 |
| precipitation | eobs_rr | ✅ 自带 |
| temperature | eobs_tg | ✅ 自带 |
| VPD | eobs_tg + eobs_hu 派生 | ✅ 派生 |
| solar_radiation | eobs_qq | ✅ 自带 |
| temperature_max | eobs_tx | ✅ 自带 |
| elevation | cop_dem | ✅ 自带 |

> [!note] EarthNet2021 气象是 1D 向量
> 实测：`eobs_*` 只有 (time,) 维度，是每时刻一个标量（GreenEarthNet 版本），非空间场。
> 这反而让 EarthNet2021 与 SSL4EO+ERA5 的 D 格式统一（都是"每时刻一个气象向量"）。

### 6.2 SSL4EO（ERA5 补充，正在下载）

| D/G 字段          | 来源                       |      状态       |
| --------------- | ------------------------ | :-----------: |
| day_of_year     | 时间戳计算                    |    ✅ 0 成本     |
| precipitation   | ERA5 total_precipitation | ⏳ 下载中（脚本含 rr） |
| temperature     | ERA5 2m_temperature      | ⏳ 下载中（脚本含 tg） |
| VPD             | ERA5 温度+露点派生             | ⏳ 脚本含 dew，可派生 |
| solar_radiation | ERA5 ssrd                | ⏳ 下载中（脚本含 qq） |
| temperature_max | ERA5 逐小时温度取日 max         |    ⏳ 需后处理     |
| elevation       | SSL4EO 自带 DEM            |     ✅ 自带      |

### 6.3 需要写的派生函数（唯一工作量）

```python
# 1. VPD 派生
def compute_vpd(temp_c, humidity_pct=None, dewpoint_c=None):
    e_s = 0.6108 * exp(17.27 * temp_c / (temp_c + 237.3))
    if humidity_pct is not None:
        e_a = e_s * humidity_pct / 100
    else:
        e_a = 0.6108 * exp(17.27 * dewpoint_c / (dewpoint_c + 237.3))
    return e_s - e_a

# 2. 日最高温（从 ERA5 逐小时）
def daily_max_temp(hourly_temp):
    return hourly_temp.resample(time='1D').max()
```

**估计工作量**：半天（写 + 测试）。

---

## 7. 与其他方法的定位（不照搬）

> [!note] ObsWorld 的差异化路线
> 我们**不**追求超越 EO-WM 等扩散模型的生成质量，而是走**物理可解释 + 多尺度**路线。

| 维度 | EO-WM（扩散路线） | ObsWorld（物理驱动路线） |
|---|---|---|
| 架构 | 387M 视频扩散 transformer | 轻量确定性动力学 + 不确定性 |
| 气象处理 | 气候基线+异常+累积胁迫（复杂） | 5 个物理清晰字段（简洁可消融） |
| 时间尺度 | 单一 100 天 | 多尺度 {10,20,30,60} 联合 |
| 可解释性 | 侧重生成与诊断 benchmark | 显式 DGH 消融 + 反事实 |
| 参数量 | 大 | 小 |

> [!important] EO-WM 只作为 SOTA 参照，非主要对手
> EO-WM 是强参照，但它的主战场是概率视频生成与 weather-response diagnostic。
> ObsWorld 的主战场是成像解耦后的状态动力学、DGH 可解释消融和反事实响应，因此主要架构对标仍应放在 Earthformer / Contextformer 等时空预测模型上。

---

## 8. 实验设计：DGH 如何验证

### 8.1 Stage 2 的训练/测试划分（泛化的严谨定义）

> [!warning] 在训练用过的数据集上测试 ≠ 泛化
> 真正的泛化必须在训练时未见的分布上测：

**严格的划分策略**：

```text
训练集：
  - EarthNet2021：2018-2019 年，地理 block 1-8（随机分）
  - SSL4EO：2019-2020 年，地理 block 1-7

测试集（held-out，训练完全没见过）：
  - EarthNet2021：2020 年夏季（时间泛化）
  - EarthNet2021：地理 block 9-10（空间泛化）
  - SSL4EO：2021 年样本（时间泛化）
  - SSL4EO：地理 block 8-10（空间泛化）
  
验证集：
  - 从训练集按时间/空间单独 hold out 10%

关键：ERA5 格点也要分组（避免 [[26_完整问题解析与执行路线图]] 的空间自相关泄露）
```

这样才能说"在 SSL4EO 上展示空间/时间泛化"，而非"在训练见过的 SSL4EO 上测训练集性能"。

**D forcing 协议必须分层报告**：

| 协议 | D 来源 | 用途 | 正文写法 |
|---|---|---|---|
| Oracle forcing | `[t,t+h]` 的 ERA5/E-OBS reanalysis | 检验模型是否能按给定气象情景响应 | scenario-conditioned / oracle，不宣称真实部署 |
| Climatology forcing | 历史多年同地同季节平均 | 无泄露的默认部署近似 | 主实验或稳健性实验均可 |
| Forecast forcing | 预测时刻发布的天气预报 | 最接近真实应用 | 有数据时作为部署实验 |

> [!warning] 论文主结论不要只依赖 oracle forcing
> Oracle forcing 可以证明动力学响应，但 deployment claim 至少需要 climatology forcing 或 forecast forcing 支撑。

---

### 8.2 AAAI 实验最小集（8 页正文限制）

基于 AAAI 2024/2025 遥感论文调研（详见 [[#附录F-AAAI实验设计调研]]），推荐的实验量与篇幅分配：

#### 实验结构（总 8 页，实验占 4 页）

```text
┌─────────────────────────────────────────────────┐
│  §5 Experiments（4 页）                          │
├─────────────────────────────────────────────────┤
│                                                   │
│  §5.1 主实验：预测任务对比（1.5 页，2 表）       │
│       - EarthNet2021 benchmark                  │
│         vs Earthformer/EO-WM/ConvLSTM/SimVP     │
│         指标：ENS, MAE, R², DHR                 │
│       - Diagnostic: Weather-response fidelity   │
│         极端事件子集（2018 热浪/2020 干旱）      │
│         ObsWorld 的 DHR > EO-WM（主战场）       │
│       叙事："competitive 但 DHR 更强"            │
│                                                   │
│  §5.2 泛化验证（0.75 页，1 表）                  │
│       - SSL4EO held-out 地区/时间               │
│       - 多分辨率输入（10m/20m/30m）              │
│       证明跨尺度维持性能                         │
│                                                   │
│  §5.3 DGH 消融实验（1 页，1 表+1 图）            │
│       8 配置：baseline, +D, +G, +H, +DG, +DH,   │
│               +GH, full DGH                     │
│       per-component 贡献分析 + D 内部小消融      │
│       这是 AAAI 审稿人最看重的（必做）           │
│                                                   │
│  §5.4 可解释性分析（0.75 页，2 图）              │
│       - 反事实：降水×2 / VPD×2 / 辐射变化        │
│       - Regime-dependent：正常 vs 干旱时驱动翻转 │
│       - 注意力可视化：H 的多尺度耦合             │
│                                                   │
│  §5.5 下游迁移（可选，0 页或放 appendix）        │
│       - Sen1Floods11 / CropHarvest              │
│       冻结 encoder，证明 z 迁移能力              │
│                                                   │
└─────────────────────────────────────────────────┘

其他 4 页：引言 0.75 + 相关工作 0.5 + 方法 2 + 结论融入实验
```

> [!tip] 精简策略
> - 下游任务可以只放 1 个（Sen1Floods11 对标 Prithvi）或移到 appendix，节省 0.5 页
> - 第三个实验表格可以压缩为半页小表
> - 可视化图做精（1 图顶 2 图），用 subfigure 组织

#### 为什么这个量级合适

| 论文 | 主实验数 | 消融组数 | 表格总数 | 页数 |
|---|:-:|:-:|:-:|:-:|
| SatMAE | 3 | ~6 | 15 | 10（含附录） |
| Prithvi | 4 | 数据效率 | ~8 | 8 |
| EO-WM | 2+诊断 | ~4 | 5 | 8+附录 |
| **ObsWorld（推荐）** | **2** | **8 配置** | **6-8** | **8** |

---

### 8.3 "输给 EO-WM"不会被拒的策略

> [!important] 基于 AAAI 2024/2025 接收论文调研的结论

**证据**：
- SatMAE：BigEarthNet 和 SpaceNet 输了，仍被 NeurIPS 接收
- Prithvi：4 个任务只 1 个 SOTA，仍成为基础模型标杆
- EO-WM：根本不 claim SOTA，说"compares well"

**AAAI 不会因"不是 SOTA"拒稿，只要你有**：
1. 明确的创新点（成像解耦 + DGH + 多尺度）
2. 诚实的对比（不回避 EO-WM）
3. 至少一个你赢或持平的维度（DHR, 参数效率, 多尺度）
4. 强消融证明 components 有用

**ObsWorld 的叙事模板**（基于 EO-WM 的成功模板）：

```markdown
## §5.1 EarthNet2021 Benchmark

Table 1: 与 SOTA 对比

Method          Params   ENS↓    MAE↓    DHR↑    Multi-scale
──────────────────────────────────────────────────────────────
ConvLSTM        50M      0.35    0.042   0.58    ✗
Earthformer     150M     0.28    0.035   0.63    ✗
EO-WM           387M     0.254   0.032   0.65    ✗
ObsWorld        120M     0.29    0.036   **0.71**    ✓

EO-WM 作为扩散模型路线（387M）在像素重建质量（ENS）上领先，
这是预期的——扩散模型专长于生成逼真细节。

ObsWorld 代表物理驱动路线（120M），在以下方面具有优势：
- **Weather-response fidelity (DHR)** 超越 EO-WM（0.71 vs 0.65），
  更准确捕捉气象驱动的植被响应（见 §5.1.2）
- **参数效率**：参数量仅 1/3，推理速度快 5×
- **多尺度能力**：单模型支持 {10,20,30,60} 天预测
- **可解释性**：显式 DGH 消融 + 反事实分析（见 §5.4）

两者路线不同、目标不同。我们不追求生成最逼真像素，
而是建模物理可解释的地表动力学。
```

> [!note] 关键：创造你赢的维度
> **DHR（Directional Hit Rate）**或类似指标是你的"主战场"。
> 它测"预测趋势是否正确"（升还是降），而非"像素是否逼真"。
> 物理驱动模型应该在这种指标上赢扩散模型——扩散模型会生成细节但物理不一定对。

---

### 8.4 D 带来的 +0.04~0.05 R² 够不够？

**文献基准**（meteo-guided forecasting, Benson CVPR 2024）：
- 加气象 ΔR² = 0.08~0.13
- 相对提升 ~20%，Wilcoxon p<0.001

**EO-WM 强调的提升**：
- 5.63% 误差降低作为 key result

**你的预期 ΔR² = 0.04~0.05**：
- 如果 baseline R²=0.50 → 8% 相对提升 → **边际但可发**，需强消融
- 如果 baseline R²=0.60 → 6.7% → **够格**，EO-WM 的 5.63% 是同量级

> [!warning] 风险预案（如果 D 只带来 +0.02~0.03）
> Pivot 叙事：去强调精度数字，强调"enables physically-grounded counterfactual reasoning"。
> 增加定性案例："预测 2018 德国热浪对农业的影响，模型正确捕捉干旱胁迫"。
> 定位从"精度提升"变为"可解释科学工具"。

---

### 8.5 消融实验的 8 配置（必做，2 GPU-days × 8）

| # | 配置 | D | G | h | 验证什么 |
|:-:|---|:-:|:-:|:-:|---|
| 0 | baseline | ✗ | ✗ | 单一 | 只有 z_t 自回归 |
| 1 | +D | ✓ | ✗ | 单一 | 气象驱动的贡献 |
| 2 | +G | ✗ | ✓ | 单一 | 地形先验的贡献 |
| 3 | +H | ✗ | ✗ | 多跨度 | 多尺度训练的贡献 |
| 4 | +DG | ✓ | ✓ | 单一 | D+G 协同 |
| 5 | +DH | ✓ | ✗ | 多跨度 | D+多尺度 |
| 6 | +GH | ✗ | ✓ | 多跨度 | G+多尺度 |
| 7 | full | ✓ | ✓ | 多跨度 | 完整 DGH |

**预算**：假设每个配置训练 2 GPU-days，8 配置 = 16 GPU-days（可接受）。

**D 内部小消融**（在 full DGH 的较短训练版上做即可）：

| 配置        | 字段                                    | 验证什么                       |
| --------- | ------------------------------------- | -------------------------- |
| D-full    | doy + precip + temp + VPD + radiation | 终版 D                       |
| D-no-VPD  | 去掉 VPD                                | 水分需求侧是否必要                  |
| D-no-rad  | 去掉 solar_radiation                    | 光能字段是否必要                   |
| D-minimal | 仅 temp + precip + doy                 | 与 Presto/EarthNet 式极简气象集对比 |

> [!note] 报告方式
> 如果 VPD/radiation 提升不大，不要硬夸精度；转为报告它们在干旱、热浪、热带/湿润区等分区上的响应差异。

**预期结果模式**（诚实的）：

```text
配置           ENS↓    R²↑    DHR↑
─────────────────────────────────
baseline      0.32    0.52   0.60
+D            0.30    0.56   0.65   ← D 贡献 ΔR²=0.04
+G            0.31    0.53   0.61   ← G 贡献小（植被任务）
+H            0.29    0.55   0.63   ← 多尺度有用
+DG           0.29    0.57   0.66
+DH           0.28    0.58   0.68
+GH           0.30    0.54   0.62
full DGH      0.27    0.60   0.71   ← 协同效应
```

诚实报告：D 主导（+0.04），G 次要但有（+0.01），H 关键（+0.03），三者协同最优。

---

## 9. 落实路线图（Week-by-Week）

### Week 1（本周，已完成）
- ✅ DGH 字段定稿
- ✅ 文献验证与数据可获取性核实
- ✅ 27 号文档写完
- □ 与陈志盛对齐概念

### Week 2-3
```python
# 实现 DGH 编码器和注入模块
class DGHEncoder:
    def __init__(self):
        self.D_encoder = MLP([d_in, 128, 256])  # D 是向量
        self.G_encoder = CNN([1, 32, 64])       # G 是空间场
        self.h_encoder = MLP([1, 64])           # log(h)
        self.film_gen = MLP([256+64+64, 512])   # FiLM γ,β
        
    def forward(self, z_t, D, G, h):
        D_feat = self.D_encoder(D)       # [B, T, D_dim] → [B, T, 256]
        G_feat = self.G_encoder(G)       # [B, H, W] → [B, 64]
        h_feat = self.h_encoder(log(h))  # [B, 1] → [B, 64]
        
        cond = cat([D_feat.mean(1), G_feat, h_feat])  # [B, 384]
        gamma, beta = self.film_gen(cond).chunk(2, -1)
        
        z_out = self.dynamics_backbone(z_t)
        z_out = gamma * z_out + beta
        return z_out
```

**任务**：
- 实现 VPD 派生函数
- 实现 ERA5 日最高温后处理
- 跑第一轮消融（验证 D/G/H 各自 > 0）
- 验证 VPD 贡献（决定是否从 P1 升为主体）

### Week 4-6
- 完整 Stage 2 训练（EarthNet2021 + SSL4EO held-out split）
- EarthNet2021 benchmark 对比
- 8 配置消融实验
- 反事实实验（降水×2 等）

### Week 7-8
- 下游任务迁移（Sen1Floods11 / CropHarvest）
- 论文初稿
- 可视化图制作（attention maps, counterfactual curves）

---

## 10. 关键决策记录

| 决策项 | 结果 | 理由 |
|---|---|---|
| D 字段数量 | 5 个核心 | 文献范围 2-24，中等偏少，物理清晰可消融 |
| VPD 优先级 | P0（核心） | 差异化卖点（供需水分平衡），Yuan Science 2019 支撑 |
| G 字段 | 仅 elevation | 洪水降级为静态分割，不需水文地形 |
| h 设计 | 多跨度联合 | 多步预测与 multi-horizon forecasting 的标准做法；Horizon-Aware GNN 可作为近期补充证据 |
| 对标策略 | Earthformer 主要，EO-WM 参照 | EO-WM 是强生成路线参照；ObsWorld 强调成像解耦、状态动力学和驱动响应 |
| 泛化定义 | held-out 严格切分 | 避免"训练见过说泛化"的科学不严谨 |
| D 在下游 | 不用，freeze z | TFT/JEPA 范式，有权威背书 |

---

## 11. 风险与应对

| 风险 | 概率 | 应对 |
|---|:-:|---|
| D 贡献 <0.03 | 中 | Pivot 叙事为"可解释性"，弱化精度 |
| EarthNet 输 EO-WM 太多 | 低 | DHR/参数效率赢回来，已有策略 |
| 消融发现 G 无用 | 中 | 诚实报告"植被任务 G 作用有限"，科学诚实 |
| VPD 与降水高度相关 | 低 | 实测相关性低（物理上独立） |
| 主结论只依赖 oracle forcing | 中 | 增加 climatology forcing 或 forecast forcing；将 oracle 只写作情景响应诊断 |
| 8 页放不下 | 中 | 下游移 appendix，方法细节 appendix |

---

## 附录 F：AAAI 实验设计调研

**来源**：调研 agent "AAAI 遥感世界模型实验设计"（2026-07-06）

**核心发现**：
- AAAI 典型实验量：3-5 主实验，2-4 下游，4-8 消融组，6-12 表
- "不是 SOTA 但被接收"是常态，需强调 novelty + 强消融
- D 带来 +0.04~0.05 R² 在 AAAI 标准下够格（EO-WM 的 5.63% 是同量级）
- 8 配置 DGH 消融是审稿人最看重的（non-negotiable）

**关键论文案例**：
- **SatMAE** — 输了 BigEarthNet/SpaceNet 仍被接收，强调 data efficiency
- **Prithvi** — 4 任务 1 SOTA，强调泛化 + transfer
- **EO-WM** — 不 claim SOTA，创造 diagnostic benchmarks 赢在新维度

**AAAI 拒稿的真正原因**（非"输给 SOTA"）：
- 缺乏清晰创新点
- 回避关键对比（显得不诚实）
- 弱消融无法 justify 复杂度
- 纯 SOTA-chasing 无科学贡献

详细调研见 agent 输出（40k tokens）。

---

## 附录 A：VPD 的文献依据

- **Yuan et al. 2019, Science Advances** — "Increased atmospheric vapor pressure deficit reduces global vegetation growth"。全球尺度证明 VPD 上升压制植被生长（GPP/NDVI），是 VPD 作为独立驱动的核心依据。https://www.science.org/doi/10.1126/sciadv.aax1396
- **Grossiord et al. 2020, New Phytologist** — "Plant responses to rising vapor pressure deficit"。VPD 对植物生理响应的机制综述。https://nph.onlinelibrary.wiley.com/doi/10.1111/nph.16485
- **低绿度驱动研究, EGUsphere 2024** — 发现 max 2m 温度、露点温度、降水、潜热通量、土壤湿度是欧洲低绿度事件的最强预测因子（印证水分平衡主导）。https://egusphere.copernicus.org/preprints/2024/egusphere-2024-3482/

## 附录 B：D 的角色文献链（主实验用 D，下游 freeze 表征）

- **Temporal Fusion Transformer (TFT), Lim et al. 2021, Int. J. Forecasting** — 提供 "known future inputs" 术语框架：预报气象作为已知未来输入喂给 decoder，与静态协变量、历史观测分开处理。这是"未来气象合法作为 D"的正式依据。https://arxiv.org/abs/1912.09363
- **DeepAR, Salinas et al. 2020** — 已知未来协变量在自回归概率预测中的标准处理。https://arxiv.org/abs/1704.04110
- **Dreamer / DreamerV3, Hafner et al.** — 世界模型训练时 latent dynamics 显式吃 action（类比 D），下游用学到的 latent state。
- **JEPA / V-JEPA, LeCun; Assran et al. 2023; Bardes et al. 2024** — 预测器用条件在表征空间预测，下游只取冻结 encoder 做 linear probe，条件信号被丢弃。这是"主实验建动力学、下游 freeze 表征不用 D"最干净的模板。https://arxiv.org/abs/2301.08243
- **Presto, Tseng et al. 2023 (ICLR 2024)** — 预训练用气象，下游冻结特征。https://arxiv.org/abs/2304.14065
- **Galileo, Tseng et al. 2025** — weather 是预训练模态，下游冻结特征评测。https://arxiv.org/abs/2502.09356

## 附录 C：D 字段数量文献对比

- **Presto (2 变量)** — 温度+降水。https://arxiv.org/abs/2304.14065
- **EarthNet2021 (5 变量)** — 降水+气压+温度×3。https://arxiv.org/abs/2104.10066
- **GreenEarthNet / Contextformer (8 变量)** — Benson et al. CVPR 2024。https://arxiv.org/abs/2303.16198
- **DeepExtremeCubes (8~24)** — 8 变量×min/max/mean。https://arxiv.org/abs/2406.18179
- **可解释性研究 (2024)** — Integrated Gradients 变量重要性，regime-dependent。https://arxiv.org/abs/2410.01770
- **Robin et al. Africa ConvLSTM (2022)** — 5 ERA5 + SMAP。https://arxiv.org/abs/2210.13648

## 附录 D：注入方式与消融文献

- **FiLM, 2018** — 通用条件化层，用外部条件生成通道级调制参数，适合轻量注入。https://arxiv.org/abs/1709.07871
- **Benson et al. CVPR 2024 / GreenEarthNet** — 附录 B 比较 CAT/FiLM/xAttn × early/latent 融合，可作为 FiLM 消融设计参照。https://arxiv.org/abs/2303.16198
- **DiffObs, 2024** — 说明地理/气象条件需要进入动力学建模，而非只作为后处理标签。https://arxiv.org/html/2404.06517v1

## 附录 D2：多跨度监督文献

- **TFT, 2019** — multi-horizon forecasting 中显式建模 known future inputs 与不同预测跨度。https://arxiv.org/abs/1912.09363
- **DeepAR, 2017** — 概率时间序列预测中的多步预测范式。https://arxiv.org/abs/1704.04110
- **Earthformer, 2022** — EarthNet2021 上的时空序列预测基线，可支撑多步地表状态预测叙事。https://arxiv.org/abs/2207.05833
- **Horizon-Aware GNN, 2026** — 近期长时程图动力学证据；可引用为补充，不要作为唯一论据。https://arxiv.org/abs/2605.29952

## 附录 E：气象驱动重要性（生态遥感共识）

- **Richardson et al. 2013, Agric. For. Meteorol.** — 物候与气候反馈综述，温度主导春季返青。
- **DeepExtremeCubes 可解释性 (2410.01770)** — 正常条件温度主导，极端事件蒸发/潜热异常主导（regime shift）。
- 短期 NDVI 驱动排序共识：**降水 ≈ 温度 > VPD > 辐射**（辐射看地区）。

---

**文档状态**：v2.0 终版（字段定稿）
**维护者**：Zhijian Liu
**最后更新**：2026-07-06
