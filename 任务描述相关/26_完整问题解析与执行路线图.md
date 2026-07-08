---
title: "26 ObsWorld DGH问题深度解析与6周执行路线图（完整版）"
version: v1.0
created: 2026-07-04
author: Zhijian Liu + Claude分析
project: ObsWorld
stage: "问题审核与决策"
tags: [ObsWorld, dgh, 问题解析, 决策, 路线图, 完整版]
---

# ObsWorld DGH 问题深度解析与6周执行路线图

> [!abstract] 文档定位
> 本文档是**唯一的完整文档**，整合了所有DGH构建问题的深度分析、文献证据、决策建议和6周执行计划。
> 所有问题在本文档内分节讨论，方便聚焦但不分散。

---

# 目录结构

```
第0部分：核心决策速查（先看这个！）
第1部分：数据规模与立意核实
第2部分：问题1 - 字段归类混乱
第3部分：问题2 - ERA5数据泄露
第4部分：问题3 - DEM边界偏差
第5部分：问题4 - 监督信号设计
第6部分：问题5 - 累积误差问题
第7部分：G字段合理性分析
第8部分：因果图与数据流图
第9部分：6周冲刺执行计划
第10部分：风险评估与FAQ
```

---

# 第0部分：核心决策速查 🎯

> [!tip] 如果时间紧急，只看这部分！

## 快速决策表

| 决策点 | 最终方案 | 理由 |
|--------|---------|------|
| **DEM处理** | ✅ 方案A：只用原始DEM | SSL4EO样本约128×128像素≈2.5km，坡度有意义但flow需要流域级别，你的主任务是植被不是洪水 |
| **主监督** | ✅ 方案A：观测空间 | 不影响"Imaging-Decoupled Dynamics"立意，文献主流，实现简单 |
| **G字段** | ✅ 只保留elevation | 植被任务地形次要，消融后如果没用诚实报告即可 |
| **时间线** | ✅ 6周冲刺（无缓冲版） | 每周有验证点，风险可控 |

## 最终dgh设计

```python
# 直接可用的配置
dgh_final = {
    'D': {
        'day_of_year_sin': sin(2π × doy / 365),
        'day_of_year_cos': cos(2π × doy / 365),
        'precipitation': ERA5气候平均,  # 避免时间泄露
        'temperature_2m': ERA5气候平均,
    },
    'G': {
        'elevation': SSL4EO的DEM,  # 单字段
    },
    'h': [1, 10, 30, 90],  # 多跨度联合训练
}

# 移除的字段：
# ❌ ndvi_previous（循环依赖）→ 改为辅助loss
# ❌ sun_elevation from D（属于phi）
# ❌ slope/aspect/flow（植被任务不敏感+边界问题）
```

## 立意核实结果

**你的论文立意**："Imaging-Decoupled Land-Surface State Dynamics"

**核心贡献**：
1. ✅ 成像解耦（Stage 1.5的phi+FiLM）
2. ✅ 外生驱动条件化（Stage 2的D+FiLM）
3. ✅ 多时间尺度（h设计）
4. ✅ 不确定性量化（VAE）

**观测空间监督不影响立意**：
- 成像解耦：编码器训练时已实现
- 动力学建模：D、G、h仍在起作用
- 监督方式只是"怎么评估好坏"，不是"怎么建模"

**结论**：✅ 用观测空间监督，立意完全不受影响

---

# 第1部分：数据规模与立意核实

## 1.1 数据规模验证

**你的实际数据**：
- SSL4EO-S12：243,968个样本
- 样本尺寸：约128×128像素（从文档推断，10米分辨率）
- 覆盖面积：约1.28km × 1.28km ≈ **1.64平方公里**

**EarthNet2021**：
- 样本尺寸：128×128像素，20米分辨率
- 覆盖面积：约2.56km × 2.56km ≈ **6.55平方公里**

## 1.2 尺度对G字段的影响

```
你的样本尺寸：1.3-2.6km

在这个尺度下：
✅ elevation（高程）：有明显变化
   平原100m vs 丘陵300m vs 山区1000m
   
✅ slope（坡度）：有局部意义
   平地0° vs 缓坡5° vs 陡坡30°
   影响：水流速度、植被类型
   
⚠️ aspect（坡向）：作用不明显
   除非高纬度雪融化任务
   
❌ flow_direction（水流方向）：边界问题严重
   真实流域可能几十公里
   
❌ flow_accumulation（汇流累积）：完全不可行
   需要完整上游信息
```

## 1.3 下游应用分析

**从22号文档看你的下游任务**：
1. 植被物候预测（主要）
2. 土地覆盖变化（主要）
3. 洪水检测（可选，22号文档提到但不是重点）

**地形敏感度分析**：

| 任务 | elevation | slope | flow | 结论 |
|------|-----------|-------|------|------|
| 植被物候 | ⭐ 次要 | ⭐ 次要 | ❌ 不需要 | 降雨气温是主导 |
| 土地覆盖 | ⭐⭐ 中等 | ⭐ 次要 | ❌ 不需要 | 平地易城市化 |
| 洪水检测 | ⭐⭐⭐ 关键 | ⭐⭐ 重要 | ⭐⭐⭐ 关键 | 必须有flow |

**结论**：
- 你的主任务（植被+土地覆盖）：**elevation够了**
- 如果要做洪水：需要下载HydroSHEDS全球flow产品

## 1.4 最终DEM方案决策

**方案A（推荐）**：只用原始elevation
```python
G = {'elevation': DEM}
```
✅ 适合你的主任务
✅ 避免边界问题
✅ 时间紧迫，直接可用

**方案B（如果G消融效果不好）**：加slope
```python
G = {
    'elevation': DEM,
    'slope': 从DEM局部算（3×3窗口）
}
```
⚠️ 只有G消融后发现不够才考虑

---

# 第2部分：问题1 - 字段归类混乱详解

## 2.1 问题描述

**核心困惑**：NDVI、season、sun_elevation到底属于D还是phi？

**当前22号文档的混乱**：
- `ndvi_previous` 在D里
- `sun_elevation` 同时在D和phi
- `season` 同时在D和phi

## 2.2 为什么这是问题

### 问题A：信息循环依赖

```python
# 错误流程
z_t = Encoder(X_t, phi_t)  # z_t已编码植被
ndvi = decode_ndvi(z_t)    # 从z_t解码NDVI
D = {'ndvi_previous': ndvi}  # 再作为D喂回
z_pred = Dynamics(z_t, D, G, h)  # z_t信息重复用了

→ 循环依赖，梯度混乱
```

### 问题B：phi和D边界模糊

同一个量（如season）同时在phi和D，模型"看到"两次，不清楚哪个在起作用。

## 2.3 正确分类判据

**文献判据**（Causal Inference with EO Data, 2023）：
> 当变量X能从影像M推断时，X=f(M)，不该作为独立外生输入

**可操作的检查清单**：

```
判断字段X应归为什么：

Step 1: X能从当前影像X_t直接计算吗？
  YES → 进Step 2
  NO → 归D（外生驱动）或G（地理先验）

Step 2: X影响什么过程？
  只影响"观测外观" → phi
  只影响"状态演化" → 需拆分或不放D
  两者都影响 → 拆分成两个字段
```

## 2.4 正确分类表

| 字段 | 能从影像算 | 影响什么 | 正确归类 | 理由 |
|------|-----------|---------|---------|------|
| **NDVI** | ✅ | 状态变量 | 从z解码，不放D | (B8-B4)/(B8+B4) |
| **sun_elevation** | ✅ | 观测外观 | 只放phi | 从时间+经纬度算 |
| **cloud_cover** | ✅ | 观测外观 | 只放phi | 从掩码统计 |
| **season** | ✅ | 双重 | **拆分** | 见下方 |
| **precipitation** | ❌ | 状态演化 | D | 需ERA5 |
| **temperature** | ❌ | 状态演化 | D | 需ERA5 |
| **elevation** | ❌ | 空间约束 | G | 需DEM |

## 2.5 季节的拆分方案

季节有双重角色：

```python
# 角色1：成像时间（phi）
phi = {
    'season_index': 2,  # 秋季，0/1/2/3
    'month': 10,
}
作用：告诉编码器"这张图是秋天拍的"
影响：叶子颜色、光照、大气条件
位置：编码器/解码器的FiLM调制

# 角色2：物候驱动（D）
D = {
    'day_of_year_sin': sin(2π × 280/365),
    'day_of_year_cos': cos(2π × 280/365),
}
作用：告诉动力学"现在是生长季哪个阶段"
影响：植被生长速度、物候节律
位置：动力学模块的FiLM调制
```

**为什么要拆分**：
- 编码方式不同（离散 vs 连续）
- 作用机制不同（成像外观 vs 动力学规律）
- 避免信息重复

## 2.6 NDVI的三种正确用法

### 用法1：只做评估指标（最简单）

```python
# 训练时不用NDVI
# 测试时计算NDVI预测误差

X_pred = Decoder(z_pred, phi_future)
ndvi_pred = (X_pred[B8] - X_pred[B4]) / (X_pred[B8] + X_pred[B4])
ndvi_real = (X_real[B8] - X_real[B4]) / (X_real[B8] + X_real[B4])

RMSE_ndvi = sqrt(mean((ndvi_pred - ndvi_real)²))
```

### 用法2：作为辅助监督（推荐）

```python
# 训练时加辅助loss
z_pred = Dynamics(z_t, D, G, h)

# 主loss（观测空间）
X_pred = Decoder(z_pred, phi_future)
loss_main = ||X_pred - X_future||²

# NDVI辅助loss
ndvi_pred = NDVIHead(z_pred)  # 轻量级MLP
ndvi_real = compute_ndvi(X_future)
loss_ndvi = ||ndvi_pred - ndvi_real||²

loss_total = loss_main + 0.1 * loss_ndvi
```

### 用法3：状态反馈（高级，可选）

```python
# 如果一定要让动力学"知道当前植被"
ndvi_current = NDVIHead(z_t)

# 作为独立输入（不是D！）
z_pred = Dynamics(z_t, D, G, h, state_feedback={'ndvi': ndvi_current})
```

**我的建议**：先用用法1或2，只有不够时才考虑3

## 2.7 修正后的字段设计

```python
# 最终版本
D_clean = {
    'day_of_year_sin': sin(2π × doy/365),  # 物候驱动
    'day_of_year_cos': cos(2π × doy/365),
    'precipitation': ERA5,
    'temperature_2m': ERA5,
}

phi_clean = {
    'season_index': 0/1/2/3,  # 成像时间
    'sun_elevation': 太阳高度角,
    'cloud_mask': 云掩码,
    'sensor': 传感器类型,
}

G_clean = {
    'elevation': DEM,
}

# 彻底移除：
# ❌ ndvi_previous from D
# ❌ sun_elevation from D
# ❌ season from D（改为day_of_year）
```

---

# 第3部分：问题2 - ERA5数据泄露详解

## 3.1 泄露类型A：时间泄露

### 问题场景

```
任务：t=0时刻，预测t=7天后的植被

错误做法：
时间轴：  t=0        t=7天
         今天       未来
          ↓          ↓
训练时：  X_t  →  预测  →  X_future
         +
      ERA5[t=0到t=7的真实降雨] ← ❌ 作弊！

问题：真实应用时，在t=0无法知道未来7天真实降雨
```

### 正确做法（三种策略）

#### 策略1：只用当前时刻（弱驱动）
```python
D = load_era5(time=t_current)  # 只用t=0
```
优点：简单、无泄露
缺点：信息弱

#### 策略2：用气候平均（推荐）
```python
D = get_climate_average(
    location=(lat, lon),
    day_of_year=t_future.day_of_year
)
```
✅ 无泄露、提供季节性先验

#### 策略3：用天气预报
```python
D = load_forecast(issued_time=t_current, horizon=7)
```
最接近实际，但需额外数据

**我的建议**：主实验用策略2

## 3.2 泄露类型B：空间自相关泄露（隐蔽！）

### 问题原理

```
ERA5格点：0.1° ≈ 9km
你的样本：1.3-2.6km

多个相邻样本共享同一个ERA5格点！

     格点A      格点B
       ●          ●
     9km        9km

     □□□  □□   ← 你的样本
   样本1-6 样本7-10
    ↑同一格点A↑  ↑格点B↑
```

**泄露发生**：
```
如果随机切分：
训练集：样本1、2、3（格点A）
测试集：样本4、5、6（格点A）

问题：测试集用的ERA5格点A，训练时"见过"！
```

### 正确切分方法

```python
# 按ERA5格点分组
def get_era5_grid_id(lat, lon):
    grid_lat = round(lat / 0.1) * 0.1
    grid_lon = round(lon / 0.1) * 0.1
    return (grid_lat, grid_lon)

# 分组
from collections import defaultdict
grid_groups = defaultdict(list)
for sample in all_samples:
    grid = get_era5_grid_id(sample.lat, sample.lon)
    grid_groups[grid].append(sample)

# 按格点切分（不是按样本！）
unique_grids = list(grid_groups.keys())
train_grids, test_grids = train_test_split(unique_grids, test_size=0.2)

# 组装样本
train_samples = []
for grid in train_grids:
    train_samples.extend(grid_groups[grid])
```

### 检查脚本（必须运行）

```python
# 检查重叠率
train_grids = {get_era5_grid_id(s.lat, s.lon) for s in train_samples}
test_grids = {get_era5_grid_id(s.lat, s.lon) for s in test_samples}

overlap = train_grids & test_grids
overlap_rate = len(overlap) / len(test_grids) * 100

print(f"重叠率: {overlap_rate:.1f}%")

# ✅ 理想：0%
# ⚠️ 可接受：< 5%
# ❌ 需修正：> 10%
```

## 3.3 检查清单

**在训练前必须确认**：
- [ ] D的时间来源明确（气候平均）
- [ ] 运行了ERA5格点重叠检查
- [ ] 重叠率 < 10%
- [ ] 如果>10%，按格点重新切分

---

# 第4部分：问题3 - DEM边界偏差（已决策：方案A）

## 4.1 问题快速总结

**陈志盛的担忧**：小patch内计算水文特征（坡度、水流方向）会有边界误差

**结论**：✅ 你的主任务（植被+土地覆盖）不需要复杂水文特征，**直接用elevation即可**

## 4.2 为什么不需要算水文特征

| 特征 | 需要的尺度 | 你的尺度 | 结论 |
|------|-----------|---------|------|
| slope（坡度） | 局部3×3即可 | 1.3-2.6km | 可以算，但植被任务不敏感 |
| flow_direction | 需要邻域信息 | 1.3-2.6km | 边界问题中等 |
| flow_accumulation | 需要完整流域（几十km） | 1.3-2.6km | **完全不可行** |

**核心原因**：
1. 你的主任务是植被物候和土地覆盖，**降雨和气温是主导因素**
2. 地形影响是次要的（除非做洪水预测）
3. 文献（DiffObs、COP-GEN）都是直接喂原始DEM

## 4.3 最终方案

```python
G = {'elevation': DEM}  # 单字段，直接从SSL4EO获取
```

**优点**：
- ✅ 避免边界问题
- ✅ 简单直接
- ✅ 符合文献主流
- ✅ 时间紧迫，不需要额外计算

**如果G消融后效果不好才考虑**：
```python
G = {
    'elevation': DEM,
    'slope': 从DEM局部算（3×3窗口）  # 不需要大范围
}
```

---

# 第5部分：问题4 - 监督信号设计

## 5.1 核心决策

**✅ 用观测空间监督（方案A）**

```python
# 主loss
X_pred = Decoder(Dynamics(z_t, D, G, h), phi_future)
loss_main = MSE(X_pred, X_future)

# 可选辅助loss
ndvi_pred = NDVIHead(z_pred)
loss_ndvi = MSE(ndvi_pred, ndvi_real)

loss_total = loss_main + 0.1 * loss_ndvi
```

## 5.2 为什么不影响立意

**你的论文立意**："Imaging-Decoupled Land-Surface State Dynamics"

**三大支柱**：
1. **Imaging-Decoupled**（成像解耦）
   - 在Stage 1.5的编码器训练时实现
   - phi通过FiLM调制编码器
   - ✅ 与监督方式无关

2. **State Dynamics**（状态动力学）
   - 在Stage 2的动力学模块实现
   - D、G、h通过FiLM注入
   - ✅ 与监督方式无关

3. **Land-Surface**（地表预测）
   - 最终目标是预测未来地表状况
   - 观测空间loss直接优化这个目标
   - ✅ 更直接

**监督方式的角色**：只是"怎么评判预测好坏"，不是"怎么建模动力学"

**类比**：
```
你的创新 = 炒菜的新方法（成像解耦+动力学驱动）
监督方式 = 判断菜好坏的标准（尝味道 vs 看颜色）

用观测空间 = 直接尝味道
→ 不影响你炒菜方法的创新性
```

## 5.3 状态空间的问题

```python
# 状态空间监督的问题
z_pred = Dynamics(z_t, D, G, h)
z_real = Encoder(X_future, phi_future)  # ← 问题在这
loss = MSE(z_pred, z_real)

问题1：z_real来自编码器，本身有误差
问题2：如果编码器在Stage 2继续更新，z_real会变（moving target）
问题3：需要决策编码器要不要冻结，增加复杂度
```

## 5.4 主目标 vs 副目标

**主目标**：学习状态动力学（预测未来）
```python
loss_main = MSE(X_pred, X_future)  # 权重1.0
```

**副目标**：辅助约束（帮助学习）
```python
loss_ndvi = MSE(NDVI_pred, NDVI_real)  # 权重0.1
loss_lulc = CrossEntropy(LULC_pred, LULC_real)  # 权重0.1
```

**关系**：副目标权重远小于主目标，确保模型聚焦核心任务

---

# 第6部分：问题5 - 累积误差与多跨度训练

## 6.1 核心问题

**你的预测跨度**：5天、30天、90天

**如果用自回归**：
```
预测90天 = 预测1天 × 90次
每次误差ε，累积后误差爆炸
```

## 6.2 文献证据

**Horizon-Aware GNN (2026)**：多跨度联合训练，长期预测误差降低**63%**

## 6.3 解决方案（必须实现）

```python
# 联合训练多个跨度
horizons = [1, 10, 30, 90]
weights = {1: 1.0, 10: 0.8, 30: 0.5, 90: 0.3}

for h in horizons:
    z_pred = Dynamics(z_t, D, G, h)
    X_pred = Decoder(z_pred, phi_future)
    loss_h = MSE(X_pred, X_{t+h})
    loss_total += weights[h] * loss_h
```

**为什么有效**：
- 模型学会"直接跳30天"，而不是"走30次1天"
- 减少自回归深度，降低累积误差

## 6.4 推理策略

**错误**：预测90天，用1天步长滚90次
**正确**：用训练过的最大步长贪心跳跃
```python
# 路径：30+30+30 = 90（3次累积）
# vs 1+1+...+1 = 90（90次累积）
```

---

# 第7部分：G字段合理性分析

## 7.1 G的三个候选字段分析

### elevation（高程）

**物理意义**：
- 影响气候带（高海拔更冷）
- 影响降雨分布（迎风坡多雨）
- 约束植被类型（高海拔针叶林）

**数据可得性**：✅ SSL4EO自带DEM

**对植被任务的作用**：⭐⭐ 中等（次要于降雨气温）

**结论**：✅ **保留**（唯一保留的G字段）

---

### slope（坡度）

**物理意义**：
- 影响水流速度
- 影响土壤侵蚀
- 平坦地易农业/城市化

**数据可得性**：✅ 可从DEM计算（3×3窗口）

**对植被任务的作用**：⭐ 较小

**边界问题**：⚠️ 边界像素需要外围信息，但影响范围小（只有边界一圈）

**结论**：⚠️ **暂不保留**，只有G消融后发现elevation不够才考虑

---

### aspect（坡向）

**物理意义**：
- 南坡vs北坡受光不同
- 影响雪融化速度
- 影响植被类型

**数据可得性**：✅ 可从DEM计算

**对植被任务的作用**：⭐ 很小（除非高纬度）

**你的数据**：全球分布，不集中在高纬度雪区

**结论**：❌ **不保留**

---

### flow_direction / flow_accumulation

**物理意义**：
- 水往哪流、有多少上游水
- 洪水预测的核心

**数据可得性**：❌ 需要大尺度计算或下载HydroSHEDS

**对植被任务的作用**：❌ 几乎无关

**边界问题**：❌❌ 严重（需要完整流域信息）

**你的主任务**：植被+土地覆盖，不是洪水

**结论**：❌ **不保留**

---

## 7.2 最终G设计

```python
G_final = {
    'elevation': SSL4EO的DEM  # 单字段
}

# 不包含：
# ❌ slope（植被任务不敏感+时间紧）
# ❌ aspect（作用很小）
# ❌ flow_direction/accumulation（不适用+边界严重）
```

## 7.3 如果G没用怎么办

**消融实验**：
```markdown
| 配置 | 90天RMSE |
|------|----------|
| Baseline (D+h) | 0.28 |
| +G (elevation) | 0.27 |
| 改进 | 3.6% |
```

**如果改进<5%**，论文中诚实报告：

```markdown
我们尝试引入地理先验G（DEM高程），但在植被物候预测任务中，
G提升有限（<5%）。推测原因：
1. 2.5km尺度下地形影响较小
2. 降雨和气温已足够解释植被变化
3. 编码器可能从多时相影像隐式学到地形信息

G在不同任务中作用差异大（洪水预测可能更需要），
我们的发现提示地理先验需根据具体任务验证，而非想当然有用。
```

**这样写完全不影响发表**，反而显得实验严谨

---

# 第8部分：因果图与数据流图

## 8.1 核心因果关系图

```
外部世界
    ↓
┌───────────┐       ┌───────────┐
│ 外生驱动D │       │ 地理先验G │
│ - 降雨    │       │ - 高程    │
│ - 气温    │       │           │
│ - 日期    │       │           │
└─────┬─────┘       └─────┬─────┘
      │                   │
      │ 驱动状态演化       │ 约束合理性
      ↓                   ↓
┌──────────────────────────────┐
│   真实地表状态 S               │
│   S_{t+h} = f(S_t, D, G, h)  │
└──────────┬───────────────────┘
           │
           │ 成像过程
           ↓
     ┌─────────┐
     │ 观测X_t │ ←─── 成像条件phi
     └────┬────┘      - 太阳角
          │           - 云掩码
          │           - 季节
          ↓
     ┌─────────┐
     │编码器Enc│
     │+ phi调制│
     └────┬────┘
          │
          ↓
     ┌─────────┐
     │ 状态z_t │ （成像解耦的表征）
     └────┬────┘
          │
          ├─────────────┬─────────────┐
          │             │             │
          ↓             ↓             ↓
    ┌─────────┐   ┌─────────┐   ┌─────────┐
    │动力学   │   │辅助任务 │   │评估指标 │
    │+D+G+h   │   │NDVI/LULC│   │NDVI预测 │
    └────┬────┘   └─────────┘   └─────────┘
         │
         ↓
    ┌─────────┐
    │ z_{t+h} │
    └────┬────┘
         │
         ↓
    ┌─────────┐
    │解码器Dec│ ←─── phi_{future}
    │+ phi调制│
    └────┬────┘
         │
         ↓
    ┌─────────┐
    │ X_{t+h} │ 预测的未来观测
    └────┬────┘
         │
         ↓ 主监督
    ┌─────────┐
    │X_future │ 真实未来观测
    └─────────┘
```

## 8.2 phi vs D 的关键区别

```
┌─────────────────────────────────┐
│ phi（成像条件）vs D（外生驱动）  │
└─────────────────────────────────┘

phi的问题：图是怎么拍的？
D的问题：地表怎么变化？

phi的影响：观测外观（同一地表，不同外观）
D的影响：状态演化（地表本身变化）

phi的位置：编码器/解码器
D的位置：动力学模块

phi的时变性：每次成像都可能不同
D的时变性：每个时间步都可能不同

phi的例子：太阳角、云、季节外观
D的例子：降雨、气温、日期（物候）
```

## 8.3 NDVI的三个正确位置

```
❌ 错误：D（外生驱动）
z_t → decode_ndvi → D['ndvi'] → Dynamics
      ↑______循环依赖______↑

✅ 正确1：评估指标
X_pred → 计算NDVI → 对比ndvi_real → 评估RMSE

✅ 正确2：辅助监督
z_pred → NDVIHead → ndvi_pred
                      ↓ loss
                   ndvi_real
                      ↓
         loss_total = loss_main + 0.1*loss_ndvi

✅ 正确3：状态反馈（可选）
z_t → decode_ndvi → state_feedback
                         ↓
      Dynamics(z_t, D, G, h, state_feedback)
```

---

# 第9部分：6周冲刺执行计划

## 9.1 总体时间线

```
Week 1 (7月5-11): 概念对齐 + 数据检查 + dgh_v0验证
Week 2 (7月12-18): ERA5集成 + 多跨度训练
Week 3 (7月19-25): 完整训练 + 多尺度验证
Week 4 (7月26-8月1): 消融实验（D/G/h）
Week 5 (8月2-8): 可视化 + 论文初稿
Week 6 (8月9-15): 论文完稿 + 最终检查
```

## 9.2 Week 1 详细计划（7月5-11日）

### Day 1 (7月5日 周六)

**上午：概念对齐**
- [ ] 打印本文档的"因果图与数据流图"部分
- [ ] 与陈志盛面对面过一遍phi/D/G边界
- [ ] 确认DEM方案（只用elevation）
- [ ] 确认监督信号（观测空间）

**下午：数据检查**
```python
# 检查ERA5格点重叠
from collections import defaultdict

def get_era5_grid(lat, lon):
    return (round(lat/0.1)*0.1, round(lon/0.1)*0.1)

grid_groups = defaultdict(list)
for sample in ssl4eo_samples:
    grid = get_era5_grid(sample.lat, sample.lon)
    grid_groups[grid].append(sample.id)

# 检查当前train/val的重叠率
train_grids = {get_era5_grid(s.lat, s.lon) for s in train_samples}
val_grids = {get_era5_grid(s.lat, s.lon) for s in val_samples}
overlap = train_grids & val_grids
print(f"重叠率: {len(overlap)/len(val_grids)*100:.1f}%")
```

**输出**：
- [ ] 概念对齐完成（陈志盛签字确认）
- [ ] 重叠率报告（如果>10%需要重新切分）

---

### Day 2-3 (7月6-7日)

**任务：实现dgh_v0_minimal**

```python
# 最简版本（验证框架可行性）
dgh_v0 = {
    'D': {
        'day_of_year_sin': sin(2π × doy/365),
        'day_of_year_cos': cos(2π × doy/365),
    },
    'G': {
        'elevation': SSL4EO的DEM,
    },
    'h': horizon_days,
}

class DynamicsV0(nn.Module):
    def __init__(self, z_dim=512):
        self.D_encoder = MLP(2 → 128)
        self.G_encoder = CNN(1 → 128)
        self.h_encoder = MLP(1 → 64)
        self.film_gen = MLP(320 → z_dim*2)
        self.backbone = Transformer(z_dim, 4层)
    
    def forward(self, z_t, D, G, h):
        D_feat = self.D_encoder(cat([D['sin'], D['cos']]))
        G_feat = self.G_encoder(G['elevation']).mean(dim=(2,3))
        h_feat = self.h_encoder(log(h+1e-6))
        
        cond = cat([D_feat, G_feat, h_feat])
        gamma, beta = self.film_gen(cond).chunk(2, dim=1)
        
        z = self.backbone(z_t)
        z = gamma.unsqueeze(-1).unsqueeze(-1) * z + beta.unsqueeze(-1).unsqueeze(-1)
        return z
```

**验证实验**：
```python
# 对比
Baseline: z_t → Transformer → z_pred（不用dgh）
+dgh_v0: z_t + dgh_v0 → Dynamics → z_pred

在SSL4EO训练10 epochs
期望：+dgh_v0比baseline好5-10%
```

**输出**：
- [ ] dgh_v0代码
- [ ] 训练loss曲线对比图
- [ ] 决策：框架是否work

---

### Day 4-5 (7月8-9日)

**任务：申请ERA5下载**

```bash
# 立即申请（后台下载，需要数天）
# Copernicus CDS: https://cds.climate.copernicus.eu/

变量：
- total_precipitation
- 2m_temperature

时空范围：
- Time: 2017-2021（覆盖SSL4EO）
- Space: SSL4EO样本的经纬度范围
- Resolution: 0.1° × 0.1°
```

**输出**：
- [ ] 提交下载请求
- [ ] 写ERA5对齐脚本（准备Week 2用）

---

### Week 1 里程碑检查（7月11日 周五）

**必须完成**：
- [ ] phi/D/G概念对齐（有签字）
- [ ] 数据切分检查完成
- [ ] dgh_v0验证通过（框架work）
- [ ] ERA5下载启动

**风险点**：
- 如果dgh_v0不work → 周末加班诊断
- 如果数据切分重叠严重 → 重新切分

---

## 9.3 Week 2-6 简要计划

### Week 2 (7月12-18)
- ERA5集成到数据pipeline
- 实现多跨度训练
- dgh_v1完整训练

### Week 3 (7月19-25)
- 完整训练到收敛
- 多时间尺度可行性验证
- 如果90天预测RMSE>0.5 → 调整策略

### Week 4 (7月26-8月1)
- D消融（证明D有用）
- G消融（知道G是否有用）
- h多跨度消融
- 开始写论文实验部分

### Week 5 (8月2-8)
- 可视化（预测样例、误差曲线）
- 不确定性校准图
- 论文实验部分初稿

### Week 6 (8月9-15)
- 补充实验
- 论文实验部分定稿
- 与陈志盛最终review

---

# 第10部分：风险评估与FAQ

## 10.1 高风险场景及缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| **ERA5空间泄露未修正** | 高 | 严重 | Week 1立即检查修正 |
| **dgh_v0不work** | 中 | 高 | Week 1诊断，2-3天修复 |
| **90天预测很差** | 中 | 中 | Week 3验证，不行降低期望 |
| **G完全没用** | 中低 | 低 | 诚实报告，不影响发表 |
| **多数据集不兼容** | 低 | 中 | 只用SSL4EO |

## 10.2 常见问题FAQ

### Q1: G没用是不是dgh构造失败了？

**A**: 不是。D（降雨气温）和h（多跨度）仍然是强贡献。G是可选加分项。文献里也有"G没用"的顶会论文（SpatialEpiBench）。

---

### Q2: 论文还能发AAAI/CVPR吗？

**A**: 能。关键是：
- ✅ 实验严谨（数据切分正确、消融完整）
- ✅ 方法创新（成像解耦+外生驱动+多尺度）
- ✅ 分析深入（包括失败的实验）

诚实报告G没用反而显得更可信。

---

### Q3: NDVI是不是完全没用？

**A**: 不是"没用"，而是"换了位置"：
- ❌ 不作为D输入（循环依赖）
- ✅ 作为辅助loss或评估指标

仍然在发挥作用。

---

### Q4: 观测空间监督真的不影响立意吗？

**A**: 确认不影响。你的立意是"如何建模动力学"（成像解耦+驱动条件化），不是"如何监督训练"。监督方式是实现细节，不是核心创新。

文献主流都是观测空间（DiffObs、FengWu、EarthPT）。

---

### Q5: 6周时间够吗？

**A**: 紧但够用。关键是：
- 聚焦核心（D+h+phi）
- 灵活处理次要（G没用就报告、多数据集来不及就只用SSL4EO）
- 每周有验证点，及时调整

---

### Q6: 如果多时间尺度（5/30/90天）单模型不行怎么办？

**A**: Week 3预验证，如果真不行有三个Plan B：
1. 改成分层模型（短期模型+长期模型）
2. 只做单尺度（比如只做30天）
3. 降低长期期望（90天RMSE允许高一些）

这不是致命问题，是技术选择。

---

## 10.3 文献支持摘要

**核心文献（20+篇顶会）**：

| 论文 | 会议 | 核心发现 | 对你的启示 |
|------|------|---------|-----------|
| DiffObs | 2024 | D简单拼接失败 | 用FiLM，不拼接 |
| Horizon-Aware GNN | 2026 | 多跨度降低误差63% | 必须联合训练 |
| COP-GEN | 2026 | DEM当独立模态 | 不预算水文 |
| SpatialEpiBench | 2026 | 空间先验可能无用 | G需消融验证 |
| Earthformer | NeurIPS 2022 | 时空Transformer | 架构参考 |
| FengWu | 2024 | 观测空间监督 | 主流做法 |

---

## 10.4 检查清单

### 概念对齐
- [ ] phi/D/G边界清晰
- [ ] NDVI位置正确（不在D）
- [ ] season拆分理解

### 数据准备
- [ ] ERA5格点重叠率<10%
- [ ] DEM数据可访问
- [ ] 时间切分有禁运期

### 代码实现
- [ ] dgh_v0验证通过
- [ ] 多跨度训练实现
- [ ] 主loss用观测空间

### 实验设计
- [ ] D消融计划明确
- [ ] G消融计划明确
- [ ] h多跨度消融计划明确

### 论文准备
- [ ] 实验部分框架写好
- [ ] 可视化需求列清单

---

# 总结：你的最终dgh设计

```python
# 最终确定版本（直接可用）

dgh_final = {
    'D': {
        # 核心字段
        'day_of_year_sin': sin(2π × doy / 365),
        'day_of_year_cos': cos(2π × doy / 365),
        'precipitation': ERA5_climate_average(location, doy),
        'temperature_2m': ERA5_climate_average(location, doy),
        
        # 数据来源：ERA5-Land 0.1°格点
        # 时间策略：气候平均（避免泄露）
    },
    
    'G': {
        # 单字段
        'elevation': SSL4EO的DEM,
        
        # 数据来源：SSL4EO自带
        # 不算slope/flow（植被任务不敏感+时间紧）
    },
    
    'h': {
        # 多跨度
        'horizons': [1, 10, 30, 90],  # 天
        'weights': {1: 1.0, 10: 0.8, 30: 0.5, 90: 0.3},
        
        # 训练：联合训练所有h
        # 推理：贪心大步跳
    },
}

# 移除的字段（有理由）：
removed_fields = {
    'ndvi_previous': '循环依赖 → 改为辅助loss',
    'sun_elevation': '属于phi，不是D',
    'season': '拆分成phi_season + day_of_year',
    'slope': '植被任务不敏感',
    'aspect': '作用很小',
    'flow_direction': '边界问题+不适用',
    'flow_accumulation': '完全不可行',
}

# phi字段（对比）：
phi = {
    'season_index': 0/1/2/3,
    'sun_elevation': 太阳高度角,
    'cloud_mask': 云掩码,
    'sensor': 传感器类型,
}

# 监督信号：
loss_main = MSE(X_pred, X_future)  # 观测空间
loss_ndvi = MSE(NDVI_pred, NDVI_real)  # 辅助
loss_total = loss_main + 0.1 * loss_ndvi
```

---

# 核心决策记录

| 决策点 | 选择 | 依据 |
|--------|------|------|
| DEM处理 | 只用elevation | 样本1.3-2.6km，植被任务，时间紧 |
| 主监督 | 观测空间 | 不影响立意，文献主流 |
| G字段 | 只保留elevation | 消融后决定是否加slope |
| D注入 | FiLM调制 | 文献证明拼接失败 |
| 多跨度 | 联合训练 | 降低累积误差63% |
| 时间线 | 6周冲刺 | 每周验证，风险可控 |

---

**文档版本**：v1.0 完整版
**创建日期**：2026-07-04
**维护者**：Zhijian Liu
**审核者**：陈志盛（待对齐）

**下一步行动**：
1. ✅ 阅读本文档
2. 🔴 今晚检查ERA5格点重叠
3. 🔴 明天与陈志盛对齐概念
4. 🔴 周末实现dgh_v0

---

END OF DOCUMENT
