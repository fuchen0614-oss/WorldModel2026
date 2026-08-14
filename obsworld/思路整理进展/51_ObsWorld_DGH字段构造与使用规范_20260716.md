---
title: ObsWorld DGH 字段构造与使用规范
aliases:
  - ObsWorld 当前 DGH 终版
  - Stage2-v2 条件字段说明
tags:
  - ObsWorld
  - DGH
  - EarthNet2021x
  - Stage2
  - 字段设计
created: 2026-07-16
status: 正式 24-D 路径协议已写入代码｜真实完整统计量待生成
supersedes:
  - "[[42_ObsWorld_DGH字段详细设计与落实思路_最终版]]"
related:
  - "[[47_ObsWorld_Stage2正式代码技术指导与实现规范_20260716]]"
  - "[[48_ObsWorld_EarthNet2021x统一数据协议与主实验规范_20260716]]"
  - "[[50_ObsWorld整体框架与Stage2完成度审计_20260716]]"
---

# 51. ObsWorld DGH 字段构造与使用规范

> [!abstract] 一句话结论
> DGH 没有被放弃，而是从“给每个终点准备一个累计条件向量”升级为“驱动共享状态转移的一条时间路径”。当前正式协议是：`D_path [30,24]` 表示 30 个连续五日天气区间，`C_path [30,2]` 单独表示季节位置，`G` 固定为 Copernicus DEM 空间图，`H/Δt` 表示 direct 的累计预测跨度或 rollout 的单步推进长度。

> [!important] 2026-07-16 论文配置决议
> 本文仍是**当前已实现 full24（方案 C）的准确技术说明**，但 full24 不再被预先指定为唯一论文主配置。最新决议是：原物理 `physical4 + C2`（方案 A）作为优先主模型候选，full24 先运行并作为完整字段对照，最终只用 `val_dev` 锁定一个配置。详见 [[53_ObsWorld_DGH主方案选择与AAAI整体实验安排_20260716]] 和 [[54_ObsWorld_原物理DGH接入Stage2的代码改造规范_20260716]]。

> [!warning] 与 42 号文档的关系
> 42 中“DOY + 降水 + 温度 + VPD + 辐射”的 6-D 设计保留了重要的生态物理直觉。当前已经实现的路径依据 raw EarthNet2021x 的 8 个 E-OBS 字段形成 **24-D**，并把 DOY 从 D 中拆成独立的 **C**；后续将以新增协议接入 42 的物理字段，不覆盖本路径。旧 9-D 累计版本继续只作为 legacy（历史）基线。

---

## 目录

- [[#1. DGH 到底是什么]]
- [[#2. 一页字段决议]]
- [[#3. D：24-D 五日天气路径]]
- [[#4. C：为什么日历从 D 中独立出来]]
- [[#5. G：固定 Copernicus DEM]]
- [[#6. H 与 Δt：时间怎样进入模型]]
- [[#7. 三种 D 协议的关系]]
- [[#8. 时间对齐与张量形状]]
- [[#9. Direct、Rollout 与 Partition 怎样公平使用 DGH]]
- [[#10. 缺失值、mask 与统计量]]
- [[#11. DGH 的实验验证]]
- [[#12. 当前实现状态与下一步]]

---

## 1. DGH 到底是什么

DGH 是状态动力学的条件接口：

$$
b_{t+\Delta t}=F_\theta(b_t,D_{t:t+\Delta t},C_{t:t+\Delta t},G,\Delta t).
$$

通俗地说：

- `D`（Driver，外生驱动）回答“这段时间发生了什么天气”；
- `C`（Calendar，日历条件）回答“这段时间处于一年中的什么季节”；
- `G`（Geography，地理背景）回答“这些变化发生在怎样的地形背景”；
- `H/Δt`（Horizon/elapsed time，预测跨度/经过时间）回答“这次向未来推进多远”。

项目名称仍叫 DGH，是为了保留原有概念和已有工作；但实际代码接口应理解为：

```text
D + C + G + H/Δt
```

`phi`、云 mask、观测清晰度、再观测 availability（可用性）不属于 DGH。它们描述观测过程，而不是地表状态为何随时间变化。

---

## 2. 一页字段决议

| 组别 | 当前正式字段 | Shape（单样本） | 数据来源 | 作用 |
|---|---|---|---|---|
| D | 8 个 E-OBS × mean/min/max | `[30,24]` | EarthNet2021x NetCDF | 每五日的天气驱动 |
| D_mask | 24-D 字段有效性 | `[30,24]` | 由逐日有限值计算 | 区分真实 0 与缺失 |
| D_valid_day_count | 每窗每变量有效天数 | `[30,8]` | 由逐日数据计算 | 只用于审计，不进模型 |
| C | `doy_sin/doy_cos` | `[30,2]` | 样本起始日期 | 季节/年周期 |
| G | `cop_dem` | `[1,128,128]` | EarthNet2021x NetCDF | 空间地形背景 |
| G_mask | DEM 有效区域 | `[1,128,128]` | DEM 有限值 | 避免把缺失当零海拔 |
| H-direct | `5,10,...,100` 天 | `[20]` | 固定目标网格 | Direct 的终点查询 |
| Δt-path | 每步 5 天 | `[30]` | 固定协议 | Rollout/partition 的推进长度 |

正式未来预测使用：

```text
D_fut = D_path[10:30]      # 20 个未来五日区间
C_fut = C_path[10:30]
Δt_fut = delta_t_path[10:30]
```

---

## 3. D：24-D 五日天气路径

### 3.1 八个原始 E-OBS 变量

固定顺序为：

```text
[fg, hu, pp, qq, rr, tg, tn, tx]
```

| 缩写 | 中文解释 | 在模型中的直觉角色 |
|---|---|---|
| `fg` | 风速 | 蒸散、热量和水汽交换背景 |
| `hu` | 相对湿度 | 空气湿润程度和水分需求背景 |
| `pp` | 海平面气压 | 大尺度天气形势的辅助信息 |
| `qq` | 全球/太阳辐射 | 地表能量与光合条件 |
| `rr` | 降水 | 水分输入 |
| `tg` | 平均气温 | 一般热环境和物候条件 |
| `tn` | 最低气温 | 低温边界与夜间热条件 |
| `tx` | 最高气温 | 高温边界与热胁迫信息 |

这里不把任何单个变量包装成完整物理机制。它们是数据集提供的外生 forcing（强迫条件），模型是否真正使用它们必须由 no-D、shuffled-D 和 wrong-year D 实验检验。

### 3.2 为什么每个变量取 mean/min/max

每个连续五日窗口，对标准化后的逐日数据计算：

- `mean`：这五天的一般水平；
- `min`：这五天的低值边界；
- `max`：这五天的高值边界。

因此每个时间块维度为：

$$
8\ \text{variables}\times3\ \text{aggregations}=24.
$$

这不是因为“24”本身有特殊意义，而是希望在保持输入规模可控的同时，既保留平均天气，也保留五日内的上下边界。更重要的是，Direct、Rollout 和 Partition 都使用同一 24-D 路径，避免输入信息量不公平。

### 3.3 24 维固定排列

当前代码采用“聚合方式优先”的顺序：

```text
[mean_fg, mean_hu, mean_pp, mean_qq, mean_rr, mean_tg, mean_tn, mean_tx,
 min_fg,  min_hu,  min_pp,  min_qq,  min_rr,  min_tg,  min_tn,  min_tx,
 max_fg,  max_hu,  max_pp,  max_qq,  max_rr,  max_tg,  max_tn,  max_tx]
```

不能改成：

```text
[mean_fg, min_fg, max_fg, mean_hu, min_hu, max_hu, ...]
```

虽然两者都是 24 维，但训练权重、统计量和 checkpoint（检查点）完全不兼容。当前 `data/earthnet_conditioning.py` 是唯一字段顺序来源。

### 3.4 构造顺序

先用训练集逐日统计量标准化，再做五日聚合：

```text
原始逐日 E-OBS [150,8]
        │
        ├── 使用 train manifest 的 daily_mean/daily_std
        ▼
标准化逐日 E-OBS [150,8]
        │
        ├── 每 5 天一个窗口，共 30 窗
        ▼
mean/min/max
        ▼
D_path [30,24]
```

公式为：

$$
z_{d,v}=\frac{x_{d,v}-\mu_v^{train}}{\sigma_v^{train}},
$$

$$
D_k=\mathrm{Concat}
\left(
\mathrm{nanmean}(z_{5k:5k+5}),
\mathrm{nanmin}(z_{5k:5k+5}),
\mathrm{nanmax}(z_{5k:5k+5})
\right).
$$

注意：24-D 聚合后不再做第二轮随意 z-score，否则无法与当前字段契约核对。

### 3.5 缺失值规则

对某个五日窗口和某个变量：

- 至少有 1 天有效：用有效天计算 mean/min/max，对应三个 mask 都是 1；
- 5 天全部缺失：三个值填 0，三个 mask 都是 0；
- 同时记录 `valid_day_count`，但它只用于审计，不作为模型捷径。

这样做比“缺一天就整段作废”更适合 raw E-OBS，同时仍能明确告诉模型某个聚合量是否可信。

---

## 4. C：为什么日历从 D 中独立出来

`C_path[k]` 是第 k 个五日窗口中点日期的年周期编码：

$$
C_k=\left[
\sin\left(2\pi\frac{DOY_k}{365.25}\right),
\cos\left(2\pi\frac{DOY_k}{365.25}\right)
\right].
$$

Shape 为 `[30,2]`。

把 C 从 D 拆开的原因不是否定季节性，而是为了让实验可解释：

- no-D 只删除具体天气，不应同时删除“现在是什么季节”；
- calendar-only 可以测试只靠季节规律能做到什么；
- shuffled-D 只替换天气路径，目标样本自己的季节位置保持不变；
- 防止模型把“夏天”误写成“使用了未来天气”。

因此：

> C 是动态条件，但在代码和实验上必须与天气 D 分组。

---

## 5. G：固定 Copernicus DEM

当前正式 G 只有：

```text
G = cop_dem
```

| 属性 | 当前决定 |
|---|---|
| 数据源 | EarthNet2021x NetCDF 中的 `cop_dem` |
| 表示 | 单通道 128×128 空间栅格 |
| 标准化 | train manifest 上的 `g_mean/g_std` |
| 缺失处理 | 无效处填 0，并保留 `G_mask` |
| 编码 | `GeoTokenizer(img_size=128, patch_size=8)` |
| 输出对齐 | 16×16 geo token，与 256/16 的状态 token 网格一致 |

为什么不再从 `nasa_dem/alos_dem/cop_dem` 中“哪个存在就用哪个”：

- 不同 DEM 产品本身可能存在系统差异；
- 若每个 cube 使用不同来源，模型可能学习 DEM 产品差异而不是地形；
- 固定来源更方便标准化、消融与复现。

当前 P1 不加入经纬度、土地覆盖、土壤类型和气候区。它们可能提高精度，但会让 OOD 解释和数据协议更复杂。

---

## 6. H 与 Δt：时间怎样进入模型

### 6.1 Direct24 的 H

Direct24 从同一个历史状态 `b0` 出发，回答某个终点问题：

$$
\hat b_{t+H}=F_{direct}(b_t,D_{1:K},C_{1:K},G,H),\quad K=H/5.
$$

H 为：

```text
[5,10,15,...,100] days
```

Direct 可以知道累计 H，因为它的任务本身就是“直接预测指定终点”。

### 6.2 Rollout24 的 Δt

Rollout 每次只推进一个五日区间：

$$
b_{k+1}=F_5(b_k,D_k,C_k,G,\Delta t=5).
$$

100 天预测来自 20 次调用，而不是把 `H=100` 塞给每一步。这样才能检验同一个局部转移是否可以持续模拟演化。

### 6.3 Partition24 的可变时间段

Partition 比较：

```text
路径 A：读取连续 2 个 D/C token，一次推进 10 天
路径 B：读取第 1 个 token 推进 5 天，再读取第 2 个 token 推进 5 天
```

两条路径必须读取完全相同的天气与日历片段，并同时接受真实 day-10 终点监督。否则模型可能“两条路径一致地错”。

---

## 7. 三种 D 协议的关系

### 7.1 `full24`：当前主协议

- 8 个 E-OBS 变量；
- mean/min/max；
- 30 个五日 token；
- Direct/Rollout/Partition 主实验统一使用。

### 7.2 `D_core12`：紧凑天气消融

变量固定为：

```text
[rr, tg, hu, qq] × [mean, min, max] = 12-D
```

它保留：

- 同一时间对齐；
- 同一 train-only 逐日标准化；
- 同一缺失值规则；
- 同一模型结构。

它只减少变量，用来回答“风速、气压、最低/最高温是否真的提供额外价值”。若 core12 与 full24 持平，应优先考虑更简单的 core12，而不是强行保留 24-D。

### 7.3 `legacy_cumulative9`：历史 Direct-DGH

旧 9-D 字段为：

```text
target_doy_sin
target_doy_cos
precip_sum
precip_mean
temp_mean
vpd_mean
vpd_max
srad_sum
srad_mean
```

它从最后 context 时刻到各目标终点做累计/均值摘要，适合：

- 复现旧 Direct-DGH；
- 检查历史训练链；
- 展示思想如何从“终点摘要”进化为“时间路径”。

它不适合作为 Rollout24 的公平输入，也不能把 legacy9 vs full24 的差异全部归因于递推结构。

---

## 8. 时间对齐与张量形状

EarthNet2021x 一个普通 cube 有 150 个逐日位置。S2 帧位于：

```text
day index = 4, 9, 14, ..., 149
```

所以：

```text
D_path[0]  = day 0..4，结束于第 1 个 S2 帧
D_path[1]  = day 5..9
...
D_path[9]  = day 45..49，结束于最后 context 帧
D_path[10] = day 50..54，推动 b0 到第 1 个 future 状态
...
D_path[29] = day 145..149，推动到第 20 个 future 状态
```

正式 batch（批次）主要字段为：

| 字段 | Batch shape | 是否进模型 |
|---|---|---:|
| `x_context` | `[B,10,4,256,256]` | 是 |
| `context_mask` | `[B,10,256,256]` | 是 |
| `D_path` | `[B,30,24]` | 是 |
| `D_mask` | `[B,30,24]` | 是 |
| `C_path` | `[B,30,2]` | 是 |
| `delta_t_path` | `[B,30]` | 是 |
| `G` | `[B,1,128,128]` | 是 |
| `G_mask` | `[B,1,128,128]` | 是 |
| `h` | `[B,20]` | 是 |
| `x_target` | `[B,20,4,128,128]` | 仅 loss（损失） |
| `target_mask` | `[B,20,128,128]` | 仅 loss |
| official eval fields | 按评估协议 | 仅评估 |
| `D_valid_day_count` | `[B,30,8]` | 仅审计 |

最关键的断言是：

```text
first future driver == D_path[:,10]
```

如果这里错一位，模型会把历史天气或错误时间段当成未来驱动，所有精度结果都失去解释。

---

## 9. Direct、Rollout 与 Partition 怎样公平使用 DGH

| 内容 | Direct24 | Rollout24 | Partition24 |
|---|---|---|---|
| D 原始变量 | full24 | full24 | full24 |
| C | 同一 C_path | 同一 C_path | 同一 C_path |
| G | 同一 cop_dem | 同一 cop_dem | 同一 cop_dem |
| 状态初始化 | 同一 Stage1/1.5 core | 同一 | 同一 |
| decoder | 同一 RGBN decoder | 同一 | 同一 |
| 时间使用 | 读取目标前缀并直接到终点 | 每次读取 1 个五日 token | 比较 2-token 直达与两次 1-token |
| 目的 | 强公平对照 | 开放循环地基 | 时间可组合性证据 |

因此正式比较必须使用同一 24-D 路径。只有这样，Direct 与 Rollout 的差异才主要来自“直接查询”与“共享递推”本身。

---

## 10. 缺失值、mask 与统计量

### 10.1 为什么必须有 D_mask

标准化后的数值 0 通常表示“等于训练集均值”，不是“缺失”。如果没有 D_mask，模型无法区分：

- 真实天气恰好接近平均值；
- 原数据缺失后被填成 0。

`IntervalDriverEncoder` 同时读取值和 mask，才可以把缺失作为缺失处理。

### 10.2 统计量必须来自训练清单

正式统计文件绑定：

- 数据集身份；
- train manifest SHA-256；
- 文件数；
- 变量顺序；
- 聚合顺序；
- daily mean/std；
- DEM mean/std；
- 有效覆盖率；
- Git commit。

`val_dev/iid/ood/extreme/seasonal` 不得参与统计量拟合。最终若从 `train_dev` 切换到 `train_all` 重训，必须重新计算与 `train_all` manifest 匹配的统计量。

### 10.3 当前并行构造

`scripts/build_earthnet_conditioning_stats.py` 已支持多个 NetCDF reader process（读取进程）。建议共享 NAS 上使用较小 workers（例如 4–8），避免用过高并发拖慢其它训练任务。

---

## 11. DGH 的实验验证

DGH 不能只靠物理解释证明有效，必须通过行为实验验证。

| 实验 | 改什么 | 证明什么 | 理想结果 | 失败后怎么办 |
|---|---|---|---|---|
| full24 vs core12 | 减少 4 个变量 | 全 8 字段是否必要 | full24 稳定更好 | 持平则用 core12 简化 |
| true-D vs no-D | 删除天气，保留 C/G/H | 天气是否提供预测价值 | true-D 更好 | 删除“天气驱动提升”强表述 |
| correct-time vs shuffled-D | 同 checkpoint 错配天气路径 | 模型是否使用时间对齐驱动 | correct-time 更好 | 不能声称模型使用了 D |
| calendar-only | 只保留 C/G/H | 季节捷径能做到什么 | 弱于 full DGH | 若持平，说明天气未起作用 |
| full-G vs no-G | 清零 G 和 G_mask | 地形是否有增益 | full-G 更好或更稳 | 持平则 G 只作条件，不主张增益 |
| G location shuffle | 整地点交换 DEM | G 是否与地点匹配有关 | 原 G 更好 | 若无差异，模型可能忽略 G |
| Direct24 vs Rollout24 | 改预测拓扑，不改 DGH | 递推地基是否成立 | Rollout 长期不崩 | 崩溃则世界模型主线不成立 |
| 10-day vs 5+5 | 改时间分割 | 动力学是否可组合 | 状态/像素 gap 小且精度不降 | 重新调损失或删除强 claim |

这些是 predictive/behavioral evidence（预测/行为证据），不能写成天气因果效应或真实物理定律发现。

---

## 12. 当前实现状态与下一步

### 已经完成

- 8 变量和 24-D 唯一顺序；
- daily normalize → five-day aggregate；
- D_mask 与 valid_day_count；
- `D_path/C_path/delta_t_path`；
- index 10 未来对齐；
- fixed `cop_dem` 与 G mask；
- stats-v2 schema（统计结构）；
- Direct/Rollout/Partition 共享 DGH；
- full24/core12/legacy9 概念隔离；
- 对应单元和合成测试。

### 尚未完成

- 用完整 `train_dev` 生成正式统计文件；
- 真实 DataLoader preflight；
- core12 正式配置与真实消融结果；
- true/no/shuffled D 真实实验；
- no-G/G-shuffle 真实实验；
- DGH 是否改善 IID/OOD 的正式结论。

> [!summary] 最终记忆法
> 当前 DGH 的关键不是“有 24 个天气数字”，而是“同一条时间对齐的 D/C/G/Δt 路径被 Direct、Rollout 和 Partition 公平共享”。只有时间对齐干预和 OOD 结果证明模型真正使用了这条路径，DGH 才能成为世界模型叙事的证据，而不是装饰性条件。
