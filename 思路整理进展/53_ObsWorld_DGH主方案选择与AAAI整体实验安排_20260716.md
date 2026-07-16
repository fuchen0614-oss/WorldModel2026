---
title: ObsWorld DGH 主方案选择与 AAAI 整体实验安排
aliases:
  - 原物理 DGH 与 full24 决议
  - ObsWorld DGH A-C 双方案安排
tags:
  - ObsWorld
  - DGH
  - Stage2
  - AAAI27
  - 实验决议
created: 2026-07-16
status: A 为优先主方案｜C 为现有可运行对照｜最终由 val_dev 闸门确认
related:
  - "[[42_ObsWorld_DGH字段详细设计与落实思路_最终版]]"
  - "[[47_ObsWorld_Stage2正式代码技术指导与实现规范_20260716]]"
  - "[[51_ObsWorld_DGH字段构造与使用规范_20260716]]"
  - "[[52_ObsWorld_AAAI27中心叙事训练实验与写作总纲_20260716]]"
  - "[[54_ObsWorld_原物理DGH接入Stage2的代码改造规范_20260716]]"
---

# 53. ObsWorld DGH 主方案选择与 AAAI 整体实验安排

> [!abstract] 最终决议
> 本文不建立一条独立的“DGH 选择研究线”，也不把 A/C 写成两个并列方法。全文始终只有一个 ObsWorld 世界模型。**A（原物理 DGH 的现代化版本）是优先主方案，C（当前 full24）是已经实现、先运行的完整字段对照。**最终主文只指定其中一个作为 final model（最终模型），另一个最多占紧凑消融表的一行。

> [!important] 为什么可以同时保留 A 和 C
> AAAI 正文不是只能出现一种输入配置；它要求的是“主方法身份唯一、结论清楚”。一个主配置加一个字段消融是标准实验结构。我们不需要为 A/C 增加新任务、新数据集、新基线家族或一整套额外实验。

---

## 1. 一句话回答当前选择

```text
方法与叙事优先项：A = physical4 + C2 + cop_dem + Δt
当前先跑的工程基线：C = full24 + C2 + cop_dem + Δt
暂不优先：B = core12（只有 A/C 难以解释时再启用）
```

选择 A 不是出于情感保留，而是因为它更符合 ObsWorld 的中心叙事：状态转移由水分、热量、大气干燥程度和辐射能量驱动；C 与 G 分别提供季节和地形背景。C 的意义是检验“增加全部原生天气字段和极值统计，是否真的比这个物理核心更有价值”。

---

## 2. A：原物理 DGH 的正式现代化定义

原 42 号文档把两个日历字段和四个天气字段共同称为 6-D D。为适配当前世界模型和严格消融，科学内容不变，但代码边界调整为：

```text
D_physical [30,4]：四类逐五日天气驱动
C_path     [30,2]：季节位置
G          [1,128,128]：Copernicus DEM
Δt_path    [30]：每步五日
```

因此论文仍可以通俗地称它为“六维动态条件”，但技术表和代码必须说明：**4-D weather driver（天气驱动）与 2-D calendar（季节条件）分开编码。**

### 2.1 四个天气字段

固定顺序为：

```text
[
  precip_sum_5d,
  temp_mean_5d,
  vpd_mean_5d,
  srad_sum_5d
]
```

| 字段 | 原始 E-OBS | 五日构造 | 物理角色 | 正式变换 |
|---|---|---|---|---|
| `precip_sum_5d` | `rr` | 五日降水求和 | 水分供给 | `log1p` 后使用 train-only 均值/标准差 |
| `temp_mean_5d` | `tg` | 五日日均温均值 | 热环境与物候 | 使用 train-only 均值/标准差 |
| `vpd_mean_5d` | `tg + hu` | 逐日计算 VPD，再取五日均值 | 大气干燥和蒸腾需求 | 按 train-only 99.5% 分位裁剪，再标准化 |
| `srad_sum_5d` | `qq` | 统一单位后五日辐射求和 | 能量与光合条件 | `log1p` 后使用 train-only 均值/标准差 |

VPD（vapor pressure deficit，水汽压亏缺）采用固定、可审计的公式；单位和公式必须写入统计文件与 checkpoint（检查点）来源信息，禁止不同机器暗中使用不同实现。

### 2.2 C、G 与 H/Δt

| 条件 | 选择 | 是否相对原思想变化 |
|---|---|---|
| C | 每个五日区间中点的 `doy_sin/doy_cos` | 物理含义不变，只从 D 中独立出来 |
| G | `cop_dem` 单通道空间海拔图 | 仍是海拔；只把数据产品固定为一种 |
| H-direct | 5、10、…、100 天累计预测跨度 | 不变 |
| Δt-rollout | 每次只输入局部 5 天 | 不变并进一步严格化 |

为保证 A/C 只改变天气表示，A 使用当前统一的“五日区间中点”计算 C，而不恢复 42 号文档中的“五日结束日”。二者只相差两天，但混用会让 A/C 比较同时改变日历对齐。该调整不改变原 DGH 的季节周期思想。

### 2.3 原方案中保留与不保留的部分

保留：

- 降水、均温、VPD、辐射的生态物理核心；
- 五日逐步路径；
- DEM 地理背景；
- Direct 终点跨度与 Rollout 局部步长的区别；
- 字段级 mask（有效性标记）和 train-only 统计量。

不恢复：

- 旧累计到终点的 9-D Direct 表示；
- 把日历、天气和最终 horizon（预测跨度）揉成不可分的一个向量；
- `nasa_dem/alos_dem/cop_dem` 中自动选择第一个可用产品；
- Direct 与 Rollout 使用不同天气信息；
- 允许不同字段协议共用 checkpoint 或统计文件。

---

## 3. C：full24 在本文中的准确角色

C 使用当前已经实现的：

```text
[fg, hu, pp, qq, rr, tg, tn, tx] × [mean, min, max] = 24-D
```

它不是被废弃的错误方案，而承担三个明确作用：

1. **现在可以先运行**：尽快验证 Stage2 真实数据、优化、预测导出和精度量级；
2. **信息完整对照**：检验物理精简 A 是否因为删去风速、气压、最低/最高温而损失性能；
3. **风险兜底**：如果 A 在相同协议下明显且可重复地落后，最终模型可以切换为 C。

C 不应成为第二条文章主线，也不单独承担新的贡献。它只回答一个支持性问题：

> 一个物理精简的驱动集合是否足够，还是完整 E-OBS 条件确实提供了必要的预测信息？

---

## 4. A/C 如何放进 AAAI 全文

### 4.1 主方法章节

主方法章节只描述最终锁定的 DGH 配置，不同时介绍两套完整模型。如果 A 通过选择闸门，则方法正文写 A；C 仅在实验设置中用一句话说明为 information-rich driver variant（信息更丰富的驱动版本）。

### 4.2 主实验和消融

A/C 不新增独立表格，只进入现有 DGH/forcing 紧凑消融中的一行：

| World model | Driver | Open-loop ENS | 50–100d 指标 | shuffled-D 变化 |
|---|---|---:|---:|---:|
| ObsWorld | A: physical4 + C2 | 待实验 | 待实验 | 待实验 |
| ObsWorld | C: full24 + C2 | 待实验 | 待实验 | 待实验 |

这两行仍使用同一个：

- EarthNet2021x `train_dev → val_dev`；
- Stage1.5 初始化；
- Direct/Rollout 模型宽度；
- G、C、Δt；
- 训练步数、损失与随机种子；
- evaluator（评估器）。

只有天气字段表示不同。A 的输入投影从 24 维变为 4 维，因此第一层会自然减少少量参数；不应为了“参数完全相等”而填充无意义通道。论文报告总 Params/FLOPs（参数量/计算量），并说明主体状态维度、转移和解码器宽度完全一致。

### 4.3 不增加的实验

不会因为 A/C 增加：

- 新数据集；
- 新下游任务；
- 新的大模型组合；
- 新基线家族；
- A/C 各自完整三随机种子的所有消融；
- 另一套论文叙事。

最终只有获选配置进入三随机种子 IID/OOD 主结果。未获选配置通常只保留一个固定随机种子的 `val_dev` 紧凑行；若预算允许，再在附录报告第二个随机种子确认方向。

---

## 5. 与 AAAI 主张的关系

ObsWorld 的两个核心问题仍然是：

1. 能否进行可信的 100 天 open-loop rollout（开放循环推演）；
2. 新的部分观测能否安全校正 belief（预测信念状态）并改善后续未来。

A/C 不是第三个核心主张。它只帮助回答：

> ObsWorld 的外生驱动是否具有清楚、必要且不过度复杂的表示？

无论最后选 A 还是 C，世界模型的 `I-F-H-U` 结构、再观测校正创新和主实验协议完全不变。

---

## 6. 后续执行顺序

### M0：先保持当前代码不动，运行 C/full24

当前 full24 是 operational default（当前可操作默认配置）。完成正式 manifest、train-only conditioning stats、preflight 和 Stage1.5 checkpoint 绑定后，依次运行：

1. Direct24 的 32-cube 过拟合；
2. Rollout24 的 32-cube 过拟合；
3. 扩展到 128 cube；
4. 一个固定随机种子的 Direct24/Rollout24 `val_dev` pilot（试跑）。

这些结果首先回答训练链是否正常，并提供 full24 的精度参考；它们不是最终论文结论。

### M1：以新增配置方式接入 A

不得覆盖 C 的数据构造、统计文件、yaml、输出目录和 checkpoint。A 以 `physical4_v1` 独立命名接入，但复用同一 Stage2 模型拓扑、数据清单、G/C/Δt、训练器、损失和评估器。

### M2：让 A 走同一条既有主线

A 依次完成相同的 32/128 cube sanity（健全性测试）和 one-seed `val_dev`。这不是新建实验，而是把预定主模型输入接入已经必须运行的 Stage2 主线。

### M3：一次紧凑决策

只用 `val_dev` 比较 A/C，关注：

- ENS 或开发阶段对应主指标；
- 50–100 天长期曲线；
- 训练稳定性；
- correct-time 与 shuffled-D 的差值；
- 主体模型宽度一致，并记录输入层带来的少量 Params/FLOPs 差异。

禁止用最终 IID/OOD 测试集选择 A 或 C。

### M4：锁定一个最终 DGH

选择完成后：

- 获选配置进入 correction（观测校正）、强基线和三随机种子主实验；
- 未获选配置停止扩展，只作为一行字段消融；
- 论文所有主结论只围绕获选配置书写。

---

## 7. 选择规则

优先级不是“谁偶然高一点就选谁”，而是：

1. 如果 A 与 C 的差距小于训练随机波动或结论不稳定，选择 A；
2. 如果 A 长期预测更稳、驱动打乱后退化更明确，即使平均分接近，也选择 A；
3. 只有 C 在相同预算下取得清楚、可重复且不只来自短时距的提升，才把 C 升为最终主配置；
4. 若一个随机种子差距很小，只对 A/C 各追加一个确认种子，不展开新的实验矩阵；
5. B/core12 默认不运行；只有 A/C 结果矛盾且确实无法解释时才作为诊断项。

这种规则既保留原 DGH 的科学价值，也避免为了保留旧设计而忽视明确的负结果。

---

## 8. 最终论文口径

若 A 获选，推荐写法为：

> ObsWorld conditions each five-day state transition on accumulated precipitation, mean temperature, mean vapor-pressure deficit, and accumulated solar radiation, while cyclic calendar features and a spatial elevation map provide seasonal and geographic context.
>
> 中文：ObsWorld 在每个五日状态转移中使用累计降水、平均温度、平均水汽压亏缺和累计太阳辐射；周期日历特征与空间海拔图分别提供季节和地理背景。

full24 的结果只用于补充：使用全部八个 E-OBS 变量是否带来额外收益。

> [!summary] 最终记忆法
> 我们不是在 A 与 C 之间写两篇论文，而是在同一 ObsWorld 中先运行现有 C 获取真实 Stage2 反馈，再把更符合中心叙事的 A 接入同一训练链。最终正文只有一个主配置，另一个是一行必要而紧凑的字段证据。
