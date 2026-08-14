---
title: ObsWorld DGH 字段详细设计与落实思路（最终版）
aliases:
  - DGH 字段终版
  - ObsWorld 条件字段契约
tags:
  - ObsWorld
  - DGH
  - 字段设计
  - Stage2
  - WorldModel
created: 2026-07-13
status: P1 字段设计冻结｜direct 与 rollout 共用
scope: EarthNet2021x NetCDF 主动力学任务
supersedes:
  - "[[27 DGH字段详细设计与落实思路（终版）]]"
related:
  - "[[39_ObsWorld_AAAI叙事前沿文献公开数据与代码独立审查_完整汇总]]"
  - "[[40_ObsWorld_主线技术路线阶段改造与实验设计说明]]"
  - "[[41_ObsWorld_代码行动指南_Stage0至Stage4]]"
---

> [!abstract] 最终结论

> **数据协议更新（2026-07-16）：**DGH 的字段设计继续有效；数据身份、清单、验证集和测试划分以服务器已有 EarthNet2021x NetCDF 和 EarthNet2021 `train/iid/ood/extreme/seasonal` 为唯一口径，详见 [48：统一数据协议](48_ObsWorld_EarthNet2021x统一数据协议与主实验规范_20260716.md)。

> P1 的 DGH 不再是“若干累计特征加一个 h 向量”，而是一个具有明确物理角色和时间对齐方式的条件包：D 由 calendar 加四类逐 5 天外生天气组成，G 只保留经过修复的空间 DEM，H 在 direct 中是目标跨度、在 rollout 中是单步间隔。DGH 服务于状态转移 T；φ、mask、obs_age 属于观测过程，不属于 DGH。

> [!important] 冻结范围
> 本文冻结的是首篇 AAAI 的 P1 字段、单位、时序、可用性、编码入口和消融规则。temperature_max、异常/累计胁迫、土壤属性、经纬度、复杂气候先验均明确降为 P2 或 Stage 4，不得在 P1 临时插入导致实验解释失控。

---

## 目录

- [[#0. 为什么需要替换 27 的终版定位]]
- [[#1. 一页字段决议]]
- [[#2. D、G、H 的精确定义与边界]]
- [[#3. D：逐步动态条件的最终字段]]
- [[#4. G：静态地理背景的最终字段]]
- [[#5. H：direct 与 rollout 中的时间字段]]
- [[#6. DGH 之外但必须存在的观测字段]]
- [[#7. 时间对齐、张量形状、归一化和可用性]]
- [[#8. direct 与 rollout 如何使用同一 DGH]]
- [[#9. 推荐编码与注入方式]]
- [[#10. 消融、负对照与验收]]
- [[#11. 明确排除及 P2 增强字段]]
- [[#12. 实现映射与冻结清单]]

---

# 0. 为什么需要替换 27 的终版定位

原 [[27 DGH字段详细设计与落实思路（终版）]] 的物理选择是有价值的：年周期、降水、均温、VPD、短波辐射和 DEM 构成了一个简洁、公开可得、可消融的生态遥感条件集。

但原文服务的是“直接按 h 预测未来”的方案。当前主线已经明确需要同时比较：

1. Stage 2-D：direct multi-horizon prediction，直接多跨度预测；
2. Stage 2-R：shared-step rollout，共享短步推演。

这带来三个必须修订的地方：

| 原 27 的写法 | 为什么不足 | 本文最终修订 |
|---|---|---|
| 天气被压缩为从当前到每个 target 的累计统计 | rollout 不知道每一步到底经历了什么天气 | D 的基本单位改为逐 5 天时间块 |
| day_of_year 混在 D 中但未和天气消融严格区分 | 无法判断模型利用天气还是季节 | calendar 仍属于 D，但固定为独立子组并单独消融 |
| h 对所有动力学统一输入 | rollout 会知道总终点，可能偷学终点回归 | h 仅用于 direct；rollout 只看 Δt 和当前 calendar |

> [!summary] 本文与 27 的关系
> 字段的生态物理逻辑没有推翻；变化的是时间组织、字段边界、direct/rollout 的使用方式和实验控制。本文是 P1 的唯一字段设计依据。

---

# 1. 一页字段决议

## 1.1 最终 DGH 条件包

$$
\mathrm{DGH}=
\left\{
D_{\mathrm{calendar}},
D_{\mathrm{weather\ path}},
G_{\mathrm{elevation}},
H_{\mathrm{time}}
\right\}.
$$

| 组别 | 最终字段 | 数量 | P1 是否必须 | 物理角色 |
|---|---|---:|---:|---|
| D-calendar | doy_sin，doy_cos | 2 | 是 | 年周期、物候背景、光周期代理 |
| D-weather | precip_sum_5d | 1 | 是 | 水分供给 |
| D-weather | temp_mean_5d | 1 | 是 | 积温、物候与热条件 |
| D-weather | vpd_mean_5d | 1 | 是 | 大气水分需求、蒸腾胁迫 |
| D-weather | srad_sum_5d | 1 | 是 | 光合能量供给 |
| G | elevation_m | 1 个空间图 | 是 | 地形约束、局地气候和植被背景 |
| H-direct | h_days | 1 | 是，仅 direct | 目标跨度 |
| H-rollout | delta_days | 1 | 是，仅 rollout | 共享转移的单步时间尺度 |

因此：

- 每个 5 天动态时间块的 D 向量是 6 维；
- G 是一张 1 通道空间 DEM；
- H 不是一个固定的全局向量，而是依赖 direct 或 rollout 的时间接口；
- 其他字段不得在 P1 暗中混入 DGH。

## 1.2 最终状态转移写法

### rollout

$$
s_{t+(k+1)\Delta}=
T_\theta
\left(
s_{t+k\Delta},
d^{\mathrm{weather}}_k,
d^{\mathrm{calendar}}_k,
G_{\mathrm{elevation}},
\Delta
\right).
$$

### direct

$$
\hat{s}_{t+H}=
F_{\mathrm{direct}}
\left(
s_t,
\{d^{\mathrm{weather}}_1,\ldots,d^{\mathrm{weather}}_K\},
\{d^{\mathrm{calendar}}_1,\ldots,d^{\mathrm{calendar}}_K\},
G_{\mathrm{elevation}},
H
\right),
\quad K=H/\Delta.
$$

这两条式子使用相同字段语义；区别仅在于 direct 一次读完整路径，rollout 每次读一个时间块并重复调用同一个 T。

---

# 2. D、G、H 的精确定义与边界

## 2.1 D：动态已知条件

D 的正式定义为：

> 在模型外部产生、随时间变化、会影响地表过程演化、且在事实预测协议下可提供的动态条件。

本项目中 D 由两部分组成：

1. D-calendar：由时间戳确定的周期背景；
2. D-weather：降水、温度、VPD、短波辐射组成的外生天气路径。

calendar 放入 D 是合理的，因为它随时间变化且在预测时已知；但它必须保持独立字段组，原因是“天气是否有效”不能被 DOY 偷换。

## 2.2 G：静态地理背景

G 的正式定义为：

> 在一个样本窗口内不随时间变化，但会改变同一外生驱动下状态转移规律的空间背景。

P1 中 G 仅包含 DEM。DEM 是空间图，不是一个区域标量；这样模型可利用局地起伏、坡地背景和高程差异。

## 2.3 H：时间查询，而非物理天气

H 的正式定义为：

> 指明模型应在何种时间尺度上推进状态的时间查询变量。

H 不属于天气，也不属于静态地理。它的职责是告诉 direct 模型“预测终点距离多远”，或告诉 rollout 模型“这一小步跨度多长”。

---

# 3. D：逐步动态条件的最终字段

## 3.1 D-calendar：两个字段

| 字段 | 公式 | 范围 | 数据源 | 为什么保留 |
|---|---|---|---|---|
| doy_sin | sin(2π DOY / 365.25) | [-1, 1] | 样本时间戳 | 周期连续，避免 12 月和 1 月距离很远 |
| doy_cos | cos(2π DOY / 365.25) | [-1, 1] | 样本时间戳 | 与 sin 共同唯一表示年内日期 |

规则：

- 使用每个未来 5 天块结束日的 DOY；
- 不做 z-score，不做缺失填补；
- 对 rollout，第 k 步使用该步目标日期的 DOY；
- 对 direct，输入长度 K 的 calendar 序列，而不是只给终点 DOY；
- calendar-only 是 RQ4 的必要负对照。

> [!warning] calendar 的边界
> calendar 是已知的季节背景，不是纯观测条件 φ，也不应被称为天气驱动。它在代码里可以归入 D 字典，但在模型和消融中必须以独立子组存在。

## 3.2 D-weather.1：precip_sum_5d

| 属性 | 最终决定 |
|---|---|
| 字段名 | precip_sum_5d |
| 物理意义 | 该 5 天块内进入地表系统的水分供给 |
| 原始数据 | 日降水量，EarthNet2021x 的 E-OBS rr；其他数据协议使用对应 ERA5 或公开再分析 |
| 聚合 | 5 天求和 |
| 单位 | mm / 5 days |
| 变换 | log1p 后按训练集统计量标准化 |
| 缺失 | 全部 5 天均存在才有效；否则该字段 mask 为 0 |

只保留 sum，不保留 mean。因为单步长度固定为 5 天时 mean 与 sum 完全线性相关，两个同时输入只会制造冗余。

## 3.3 D-weather.2：temp_mean_5d

| 属性 | 最终决定 |
|---|---|
| 字段名 | temp_mean_5d |
| 物理意义 | 积温、物候节律和热环境 |
| 原始数据 | 日均温，EarthNet2021x 的 E-OBS tg |
| 聚合 | 5 天均值 |
| 单位 | °C |
| 变换 | 按训练集均值/标准差标准化；训练集外不重估 |
| 缺失 | 全部 5 天均存在才有效 |

仅使用均温。temperature_max 与均温、VPD 强相关，作为极端事件 P2 增强，而非 P1 主字段。

## 3.4 D-weather.3：vpd_mean_5d

| 属性 | 最终决定 |
|---|---|
| 字段名 | vpd_mean_5d |
| 物理意义 | 大气干燥程度、蒸腾需求和水分胁迫 |
| 原始数据 | 日均温加相对湿度；EarthNet2021x 的 E-OBS tg 与 hu |
| 派生 | 由饱和水汽压和实际水汽压之差计算 |
| 聚合 | 5 天均值 |
| 单位 | kPa |
| 变换 | clip 到训练集 99.5 分位后，按训练集统计量标准化 |
| 缺失 | 温度或湿度任一天缺失，则该 5 天字段无效 |

VPD 不与 humidity 共同作为 P1 输入。humidity 是 VPD 的组成部分；同时输入会使“水分需求侧”解释变得重复。

## 3.5 D-weather.4：srad_sum_5d

| 属性 | 最终决定 |
|---|---|
| 字段名 | srad_sum_5d |
| 物理意义 | 该时间块可用于光合作用的辐射能量 |
| 原始数据 | E-OBS qq；或 ERA5 surface solar radiation downwards |
| 聚合 | 先统一到 MJ/m²/day，再 5 天求和 |
| 单位 | MJ/m² / 5 days |
| 变换 | log1p 后按训练集统计量标准化 |
| 缺失 | 全部 5 天均存在才有效 |

只保留 sum，不保留 mean；理由与降水相同。

## 3.6 P1 D 向量的固定顺序

每一步的原始 D 向量固定为：

$$
d_k=
[
doy\_sin_k,
doy\_cos_k,
precip\_sum\_5d_k,
temp\_mean\_5d_k,
vpd\_mean\_5d_k,
srad\_sum\_5d_k
].
$$

该顺序必须同时写入：

1. 数据集返回的 feature_names；
2. 训练 yaml；
3. 归一化统计 JSON；
4. checkpoint metadata；
5. 评测脚本；
6. 论文附录字段表。

任何统计文件的字段顺序不一致都应直接报错，不能自动猜测。

---

# 4. G：静态地理背景的最终字段

## 4.1 P1 仅保留 elevation_m

| 属性 | 最终决定 |
|---|---|
| 字段名 | elevation_m |
| 表示 | 单通道空间图，不做全图均值池化 |
| 来源 | EarthNet2021x NetCDF 中可用的 nasa_dem、alos_dem、cop_dem；按统一优先级选一个 |
| 单位 | metres |
| 变换 | 使用训练集 global robust normalization，例如 median/IQR；不在单通道最后维使用 LayerNorm |
| 缺失 | 无 DEM 的样本显式 G_mask=0，不以零海拔代替 |
| 注入 | GeoTokenizer 产生空间 token，进入 T |

当前 GeoTokenizer 的单通道 LayerNorm 会消去 DEM 信息，因此本字段的“设计冻结”以修复该 P0 bug 为前提。修复前不得报告 no-G 或 G 有效性的结论。

## 4.2 P1 明确不加入的 G 字段

| 字段 | 是否加入 | 理由 |
|---|---:|---|
| 经纬度 | 否 | 容易成为空间记忆，在 OOD 中产生伪泛化 |
| 土壤类型、土地覆盖 | 否 | 增加外部数据、类别先验和缺失处理；首篇没有必要 |
| 坡度、坡向 | 否 | 可由空间 DEM 在 GeoTokenizer 中学习局部导数；暂不手工堆派生量 |
| 气候区标签 | 否 | 与 calendar 和天气强相关，解释困难 |
| 未来静态地图或任务标签 | 否 | 存在信息泄漏或任务投机风险 |

---

# 5. H：direct 与 rollout 中的时间字段

## 5.1 共同时间网格

EarthNet2021x 当前主配置为：

- 10 个 context frames；
- 20 个 target frames；
- frame_interval_days = 5；
- 最大预测窗口 100 天。

因此 P1 统一定义：

$$
\Delta=5 \text{ days}, \qquad
\mathcal{H}=\{5,10,15,\ldots,100\} \text{ days}.
$$

这比原 27 的 {10,20,30,60} 更完整：它和数据真实 target 网格一致，也支持隐藏中间帧和全 horizon 曲线。

## 5.2 H-direct

direct 的时间字段只有：

| 字段 | 定义 | 编码 |
|---|---|---|
| h_days | 目标 target 相对 nominal context end 的天数，取 H 集合 | h/100 加 Fourier 或小 MLP 时间 embedding |

训练时不是每个 batch 预测全部 20 个 target。为控制显存，建议从六个区间各采样一个 horizon：

| 层级 | 可采样 h 天数 |
|---|---|
| short-1 | 5，10 |
| short-2 | 15，20，25 |
| medium-1 | 30，35，40 |
| medium-2 | 45，50，55，60 |
| long-1 | 65，70，75，80 |
| long-2 | 85，90，95，100 |

这样一个样本约训练 6 个 horizon，同时长期覆盖全部 20 个 target。评测必须输出完整 5 到 100 天曲线。

## 5.3 H-rollout

rollout 的共享 T 不接收全局 h_days。它只接收：

| 字段 | 值 | 作用 |
|---|---|---|
| delta_days | 5 | 告诉 T 本次推进一个 5 天时间块 |
| calendar_k | 当前第 k 步的 doy_sin/cos | 告诉 T 本步季节位置 |

总跨度由调用次数决定：

$$
h=K \times \Delta.
$$

禁止把最终 h=100 作为每一个 rollout step 的输入；否则模型可能学习“我最终要到 100 天”而非真正的一步演化。

---

# 6. DGH 之外但必须存在的观测字段

以下字段不可塞进 DGH，因为它们描述“卫星如何看到状态”，而不是“地表为何变化”：

| 字段 | 位置 | 用途 | 是否未来真值可输入 |
|---|---|---|---:|
| x_context | observation encoder | 历史遥感观测 | 仅历史 |
| valid_mask | encoder 与 loss | 云/无效像素的观测质量 | 未来只能做 loss mask |
| obs_age | state inference 或 update | 每个 token 距上次有效观测的时间 | 可由历史计算 |
| φ_product/sensor | encoder 与 O decoder | 已知产品或传感器差异 | 仅推理时已知 |
| future cloud mask | 仅 loss/evaluation | 遮掉不可评分目标像素 | 否 |

这条边界非常重要：未来云不是地表过程驱动，不能作为 D；产品和传感器也不是天气，不能作为 G。

---

# 7. 时间对齐、张量形状、归一化和可用性

## 7.1 统一时间锚点

所有 D 和 H 相对统一 nominal context end，记为 t0。

即使 context 内不同像素最后有效观测时间不同，状态推断器也必须通过 obs_age 知道这一点；但动力学时间轴仍从共同 t0 开始。不能让每个 token 用自己的天气起点，否则样本没有统一物理时间。

第 k 个时间块定义为：

$$
(t_0+(k-1)\Delta,\;t_0+k\Delta].
$$

其 D 向量为 d_k，目标影像为 x_{t0+kΔ}。

## 7.2 最终张量契约

| 张量 | shape | 说明 |
|---|---|---|
| D_path | B × 20 × 6 | 20 个连续 5 天块，每块 6 个 D 字段 |
| D_mask | B × 20 × 6 | 字段级可用性，不以零值替代缺失 |
| G_elevation | B × 1 × H × W | DEM 空间图 |
| G_mask | B × 1 × H × W 或 B × 1 | DEM 可用性 |
| h_days | B × Hf | direct 抽样 horizon |
| delta_days | B 或 scalar | rollout 单步，P1 固定为 5 |
| calendar_path | 已含于 D_path 前两维 | 不另复制成未对齐的字段 |
| obs_age | B × Tcontext × N 或适配的空间形式 | 不属于 DGH |

## 7.3 归一化契约

| 字段 | 变换 | 统计来源 |
|---|---|---|
| doy_sin/cos | 不变 | 无 |
| precip_sum_5d | log1p 后 z-score | 仅 train split |
| temp_mean_5d | z-score | 仅 train split |
| vpd_mean_5d | 训练集 99.5 分位 clip 后 z-score | 仅 train split |
| srad_sum_5d | log1p 后 z-score | 仅 train split |
| elevation_m | robust normalization | 仅 train split |
| h_days | 除以 100，之后时间 embedding | 固定常数 |
| delta_days | 除以 5，之后时间 embedding | 固定常数 |

任何 validation/test 的统计量不得参与归一化统计。跨数据集时必须重建或明确复用训练集统计，不能静默混用。

## 7.4 D 的事实预测协议

P1 的 RQ1/RQ3/RQ4 主实验使用已发生时期的再分析或观测天气，因此属于：

> oracle forcing factual replay，已知真实天气强迫下的事实重演。

这在科学上合法，但论文必须明确：它检验“给定真实驱动时能否重演真实地表变化”，不等同于部署时提前获知未来天气。

真正 forecast forcing，即未来气象预报输入，属于 P2 部署实验；不要在 P1 混淆。

---

# 8. direct 与 rollout 如何使用同一 DGH

## 8.1 direct 的条件流

direct 从 D_path 的前 K 块取完整未来天气和 calendar 序列：

$$
e_D^{direct}=E_{path}(d_1,\ldots,d_K).
$$

再与 G 和 h_days 融合：

$$
\hat{s}_{t+H}=
F_{direct}(s_t,e_D^{direct},E_G(G),E_H(H)).
$$

direct 可以知道 H，因为它的任务就是直接回答指定 horizon 的状态。

## 8.2 rollout 的条件流

rollout 每次只读取一个步骤：

$$
e_{D,k}=E_{step}(d_k).
$$

$$
\hat{s}_{k+1}=T(\hat{s}_k,e_{D,k},E_G(G),E_\Delta(\Delta)).
$$

同一 T 参数在 k=1 到 K 重复使用。它不知道终点总跨度，只知道此刻天气、季节、地理和本步时间长度。

## 8.3 公平控制

| 内容 | direct | rollout |
|---|---|---|
| D 字段和归一化 | 完全相同 | 完全相同 |
| G 字段和 GeoTokenizer | 完全相同 | 完全相同 |
| encoder / decoder 初始化 | 完全相同 | 完全相同 |
| 时间网格 | 5 到 100 天 | 5 天 × 1 到 20 步 |
| 唯一机制差异 | 路径一次聚合后跳到终点 | 共享短步 T 连续调用 |

这保证比较回答的是“拓扑是否有机制价值”，而非“某一路多了天气字段或更强感知骨干”。

---

# 9. 推荐编码与注入方式

## 9.1 P1 默认实现

| 条件子组 | 编码器 | 输出形式 | 注入位置 |
|---|---|---|---|
| D-calendar | 2 层 MLP | 全局 condition embedding | T 的 FiLM/gated residual |
| D-weather step | 小型 MLP | 每步 weather embedding | T 的 FiLM/gated residual |
| D-weather path，direct 专用 | causal GRU 或轻量 temporal Transformer | 终点 path embedding | F_direct 的 FiLM/gated residual |
| G-elevation | 修复后的 GeoTokenizer | 空间 geo tokens | 与 state token cross-attention 或 token-wise gating |
| H-direct | HorizonEncoder | 时间 query embedding | F_direct |
| H-rollout | DeltaEncoder | 单步时间 embedding | T |

推荐默认融合：

$$
\Delta s=
Gate(s,e_D,e_C,e_H)
\odot
f(s,E_G(G)).
$$

这里 Gate 可实现为 FiLM 或 gated residual。P1 不把“注入方式创新”作为论文贡献；只需固定一个稳定默认实现，并在较小规模附录比较 concat、FiLM、cross-attention。

## 9.2 为什么不为每个天气字段建一个复杂模块

四类天气字段的物理角色不同，但 P1 的科学目标是先证明“分组条件是否真的有效”，而不是同时声称四个独立的气候机理网络。

P1 中：

- calendar、weather、geo、time 四组有独立 encoder；
- 降水、温度、VPD、辐射在 weather encoder 内作为不同通道；
- 通过字段消融判断其贡献。

P2 中若证据显示有效，再加入 anomaly/stress 专用路径或 feature-wise gating。

---

# 10. 消融、负对照与验收

## 10.1 DGH 主消融

| 配置 | calendar | weather 四字段 | G | H | 回答 |
|---|---:|---:|---:|---:|---|
| A：image-only | 否 | 否 | 否 | 否 | 纯观测预测基线 |
| B：plus-H | 否 | 否 | 否 | 是 | 仅多跨度查询的贡献 |
| C：calendar-only | 是 | 否 | 否 | 是 | 纯季节规律能做到什么 |
| D：weather-only | 否 | 是 | 否 | 是 | 天气不借 DOY 的价值 |
| E：calendar+weather | 是 | 是 | 否 | 是 | 动态 D 的完整作用 |
| F：full-DGH | 是 | 是 | 是 | 是 | 完整条件包 |

P1 中不再使用原先将 h、calendar、累计天气混在一起的 +D/+G/+H 消融命名；上述名称直接对应物理问题。

## 10.2 RQ4 的天气负对照

在 full-DGH 基础上：

| 对照 | 操作 | 预期解释 |
|---|---|---|
| no-weather | 保留 calendar/G/H，去掉四类天气 | 天气相对季节的增益 |
| within-season shuffle | 同季节内替换天气路径 | 破坏实际天气对应关系 |
| wrong-year weather | 同地点/同季节换另一年天气 | 检验预测是否随真实差异方向变化 |
| no-calendar | 保留天气，去掉 DOY sin/cos | 检验天气是否只靠季节代理 |
| no-G | 去掉 DEM | 评估地理背景是否有独立价值 |

任何天气有效性结论都至少需要 true-weather 对 no-weather、calendar-only、within-season shuffle 三项比较。

## 10.3 D 内部字段消融

在 full-DGH 的较短训练或固定 checkpoint 下做：

| 配置 | 去掉字段 | 目的 |
|---|---|---|
| no-precip | precip_sum_5d | 水分供给是否必要 |
| no-temp | temp_mean_5d | 积温/热条件是否必要 |
| no-vpd | vpd_mean_5d | 大气需求侧是否提供额外信息 |
| no-srad | srad_sum_5d | 光能条件是否必要 |

字段消融的价值在于解释，而不是要求每个字段都带来显著大提升。若某字段无效，应报告并考虑在 P2 删除，而不是人为保留。

## 10.4 字段验收条件

- [ ] D_path 真实为连续 20 个 5 天时间块，而非每个 h 的累计统计。
- [ ] D_mask 对任何缺失字段有效，零降水不被误认为缺失。
- [ ] calendar-only 与 weather-only 都可以运行。
- [ ] direct 的 h 和 rollout 的 delta 不会同时错误输入全局终点。
- [ ] DEM token 对不同高程输入不同。
- [ ] 训练集统计文件有固定 feature_names 和版本。
- [ ] 所有消融配置通过最小训练 smoke test。

---

# 11. 明确排除及 P2 增强字段

## 11.1 P1 明确排除

| 字段 | 原因 |
|---|---|
| precip_mean_5d | 与 sum 冗余 |
| srad_mean_5d | 与 sum 冗余 |
| vpd_max_5d | 与均值高度相关，先不增加共线性 |
| temperature_max_5d | 先保留给极端事件扩展 |
| humidity | 已用于派生 VPD，避免重复 |
| 经纬度 | 空间记忆风险 |
| soil / landcover / climate zone | 额外数据与解释负担，不是 P1 必需 |
| future cloud / quality | 未来信息泄漏 |
| sun/view angle | 当前主数据接口与观测模型尚不支持干净验证 |

## 11.2 P2 或 Stage 4 可加

| 字段/机制 | 触发条件 | 用途 |
|---|---|---|
| temperature_max_5d | 极端热浪诊断确有收益 | 热胁迫 |
| climatology/anomaly | P1 已证明天气有效 | 将季节基线与异常天气区分 |
| cumulative heat/water stress | rollout 稳定且想对标 EO-WM | 持续异常效应 |
| soil/static attributes | G 无效或 OOD 是瓶颈 | 异质地表背景 |
| location encoding | 严格空间 OOD 设计完成 | 全球迁移 |
| forecast weather forcing | 完成事实 replay 后 | 部署可行性 |

---

# 12. 实现映射与冻结清单

## 12.1 当前代码到最终契约的变化

| 当前位置 | 当前行为 | 最终目标 |
|---|---|---|
| data/datasets/earthnet2021.py | 每个 target 从 nominal context end 累计天气，输出压缩特征 | 输出 D_path 20×6，每个元素为独立 5 天块 |
| _add_weather_values | 生成 sum、mean、max 等多个统计 | P1 固定为 precip_sum、temp_mean、vpd_mean、srad_sum |
| target_doy_sin/cos | 已生成但混入 driver 向量 | 保留为 D-calendar 前两维，独立消融开关 |
| configs/train/stage2_earthnet_main.yaml | driver channel map 是四个原始天气通道 | 增加最终 feature_names、D_path 配置、字段组消融 |
| models/adapters/geo_tokenizer.py | 单通道 LayerNorm 有失效风险 | 修复 DEM tokenization，使用 elevation_m 空间图 |
| models/dynamics/obsworld_stage2.py | 一个 driver embedding 加一个 horizon embedding | 分离 direct 条件路径；不再把它称作 rollout |
| 新增 rollout 模型 | 当前不存在 | 逐步读取 d_k 和 delta_days 的共享 T |

## 12.2 P1 配置应冻结的常量

| 名称 | 值 |
|---|---|
| step_days | 5 |
| max_horizon_days | 100 |
| d_feature_names | doy_sin, doy_cos, precip_sum_5d, temp_mean_5d, vpd_mean_5d, srad_sum_5d |
| g_feature_names | elevation_m |
| direct h grid | 5 到 100 天，步长 5 |
| direct horizons per sample | 6，分层采样 |
| rollout delta_days | 5 |
| rollout max steps | 20 |
| weather protocol P1 | oracle reanalysis factual replay |
| D statistics | train split only |

## 12.3 论文中可直接使用的字段说明

> At each five-day transition, ObsWorld conditions its state dynamics on a six-dimensional dynamic driver vector comprising cyclic day-of-year encoding, accumulated precipitation, mean temperature, mean vapor-pressure deficit, and accumulated shortwave radiation. A spatial elevation map provides static geographic context. Direct forecasting is queried by the target horizon, whereas rollout uses only the local five-day interval and does not observe the final horizon.

对应中文：

> ObsWorld 在每个 5 天状态转移中使用 6 维动态条件：年积日周期编码、累计降水、平均气温、平均水汽压差和累计短波辐射；空间 DEM 提供静态地理背景。直接预测由目标跨度查询，而连续推演只观察当前 5 天间隔，不输入最终预测终点。

> [!summary] 最终冻结结论
> P1 DGH 已确定为 D 的 6 个逐步字段、G 的空间 DEM、以及 direct/rollout 分别使用的 H 时间接口。字段应保持这一最小且物理清晰的集合，优先证明状态转移与天气路径有效；不要在尚未完成基础闭环前加入温度极值、土壤、坐标、复杂胁迫或几何观测变量。
