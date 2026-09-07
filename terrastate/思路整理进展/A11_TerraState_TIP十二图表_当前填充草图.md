# A11 · TerraState TIP 八图七表：当前填充草图

> 数据快照：commit `8b616b4`，2026-09-04。  
> `--`：待补；`n.a.`：不适用；`[图像待导出]`：已有模型/数据但尚未生成论文图片。  
> 当前规划：**8 Figures（图）+ 7 Tables（表）= 15 项主文图表**。15 项不是数量指标，而是当前最合理、最少重复的完整证据链。

---

## 0. 全文主线与图表分工

### 0.1 图表必须共同支撑的唯一主旨

> **TerraState 是一个面向高分辨率地球观测的天气驱动世界模型。它从稀疏且部分可观测的历史影像中学习显式空间预测状态，并通过共享的变跨度状态转移持续模拟地表未来。不同于仅生成固定长度未来序列的预测方法，TerraState 要求中间状态能够继续承担后续预测，并使同一天气路径下的直接推进与分段推进保持近似一致。**

核心科学问题是：

> **在部分可观测、天气驱动的高分辨率地球观测场景中，能否构建一个遥感世界模型，学习真正面向未来的空间预测状态，使不同时间跨度的状态转移能够组合，并使中间状态继续承担后续预测？**

真正的方法贡献是：

> **通过 recursive factual supervision（递归事实监督），把“中间状态能够继续代表模型所理解的当前世界”写进真实预测监督路径，而不是训练完成后再临时检查一个 hidden state（隐藏状态）。**

### 0.2 图与表不是同一证据的两种装饰

> **表格负责给出可复核的总体数值，图负责展示这些数值背后的时间过程、空间现象和样本分布。图与表服务于同一科学主张，但不得把相同的汇总数字换一种形式重复呈现。**

| 主张 | 图回答“现象如何发生” | 表回答“总体数值是否成立” |
|---|---|---|
| Q1 预测能力 | Fig. 3-4 展示真实空间预测；Fig. 5 展示随时距退化 | Table 1-2 给两数据集总体指标与统计排名 |
| Q2 状态承载 | Fig. 6 展示时距、样本分布和空间贡献 | Table 4 给 split/seed、精确效应、CI 与判定 |
| Q3 天气响应 | Fig. 7 展示天气输入、NDVI 轨迹和空间分支 | Table 5 给 actual/control 的精确差值、CI 与边界结论 |
| Q4 持续推进 | Fig. 8 展示分段过程、量级趋势、状态/输出差距与地图 | Table 6 给 endpoint/partition/seed、精确退化、CI 与 gate |

### 0.3 当前进度总览

| 编号 | 一句话目的 | 当前可填程度 |
|---|---|---|
| Fig. 1 | 说明为什么固定窗口预测不等于世界模型，并提出可证伪的状态运行契约 | 科学问题已冻结，可立即绘制 |
| Fig. 2 | 展示 C1 架构及递归事实监督为何训练出可续推状态 | 代码已实现，待矢量重画与 API demo |
| Fig. 3 | 检查 GreenEarthNet 上实际空间预测质量和失败模式 | 权重/数据已有，待导图 |
| Fig. 4 | 检查独立数据集上的空间预测与失败边界 | 第二数据集尚未训练 |
| Fig. 5 | 展示两数据集随时距和 OOD 条件的性能变化 | GreenEarthNet 部分可导出；Africa 待补 |
| Fig. 6 | 展示显式状态何时、在哪些样本和区域承担预测 | Q2 数值完成，待导出分布/地图 |
| Fig. 7 | 展示不同天气路径如何产生不同预测轨迹与空间终点 | Q3 数值完成，待导出轨迹/地图 |
| Fig. 8 | 展示 C1/C0R 的直接/分段推进量级差及空间行为 | Q4 核心数值完成，待绘图与多种子确认 |
| Table 1 | 给出 GreenEarthNet 同协议预测竞争力 | E1 基线完成；C1 待补两种子 |
| Table 2 | 给出独立数据集重新训练后的预测能力 | 全部待补 |
| Table 3 | 隔离贡献来自 C1 训练机制而非参数或底座 | C1/功能控制部分完成；C0R Q1-Q3 待补 |
| Table 4 | 精确验证 Q2 状态承载 | 单种子四 split 完成 |
| Table 5 | 精确验证 Q3 条件天气响应 | C1 主结果完成；对照模型/第二数据集待补 |
| Table 6 | 精确验证 Q4 持续推进与组合一致性 | 单种子锁定结果完成；确认实验待补 |
| Table 7 | 报告参数、速度、状态存储和恢复代价 | 参数量已有，其余待测 |

---

# 第一部分：八张主图草图

## Fig. 1 · 从固定时距预测到可复用状态世界建模

**目的**：在第一页说明“为什么已有遥感预测器还不够”、本文科学问题为何成立，以及世界模型主张将被哪些行为检验。

```text
(a) Partial observation（部分可观测）

 Hidden land state（不可完全观测的地表状态）:  w_t ─── w_{t+1} ─── ... ─── w_{t+H}
                                                    │          │                    │
 Sparse/cloudy EO（稀疏/云遮挡遥感）:          x_t       [missing]              x_{t+H}
 Dense weather forcing（密集天气驱动）:        u_t ───── u_{t+1} ───── ... ─── u_{t+H}

(b) Fixed-horizon predictor（固定时距预测器）

 history x + weather u[0:H] ───────────────> y_hat_H
                 accurate output may exist（输出可能准确）
                 reusable intermediate state is not required（但不要求中间状态可复用）

(c) Reusable-state EO world model（可复用状态遥感世界模型）

 history ── initialize ──> s_0 ── T[u_0:k] ──> s_k ── T[u_k:H] ──> s_H ──> y_hat_H
                              │                    │
                              │                    ├─ save / resume（保存/恢复）
                              │                    └─ branch u_A / u_B（天气条件分支）
                              └──── T[u_0:H] ───────────────────────────────> s'_H
                                                       requirement: s_H ≈ s'_H

(d) Falsifiable contract（可证伪运行契约）

 Q1 Prediction（预测）      Q2 Load-bearing（承载）
 Q3 Forcing response（驱动响应）   Q4 Continuation/composition（持续/组合一致）
```

| Panel（面板） | 必须表达的结论 | 当前状态 |
|---|---|---|
| (a) | 遥感序列是部分可观测且受天气驱动的动态系统 | 可绘制 |
| (b) | 固定窗口预测准确并不自动证明存在可续推状态 | 可绘制 |
| (c) | TerraState 的研究对象是可保存、续推和分支的空间预测世界状态 | 可绘制 |
| (d) | “世界模型”称谓由 Q1-Q4 的可证伪证据支撑 | 可绘制 |

推荐图注核心句：

> Accurate fixed-horizon forecasts do not necessarily imply a reusable predictive state. TerraState learns weather-driven spatial state transitions and tests whether the learned state remains load-bearing, forcing-responsive, and continuation-consistent across temporal partitions.

中文释义：**准确的固定时距预测并不必然意味着模型拥有可复用预测状态；TerraState 检验状态在不同时间分段下是否持续承担预测、响应天气并保持推进一致。**

---

## Fig. 2 · TerraState-C1 架构与递归事实监督

**目的**：回答“具体提出了什么模型与训练机制”，并把 C0R/C1 的单变量差异画清楚。

```text
(a-c) Model and runtime state（模型与运行时状态）

 Historical EO x_{1:t}     Past weather     Geography
          │                     │                │
          └─────────────────────┴────────────────┘
                                │
            PVT-v2 / Contextformer context backbone（上下文骨干，非创新点）
                    ┌───────────┴───────────┐
                    │                       │
       Context prior P_h（上下文先验）  State projector（状态投影）
                                            │
                                           z_0
                                            │
 Future weather u[a:b] ──> Shared variable-span T（共享变跨度转移）
                                            │
                                           z_b ──> State readout O（状态读出）
                                            │
                           y_hat_b = P_h + alpha O(z_b)

 runtime_state（运行时状态） = {P, z, geography, current_offset}
 initialize(history) -> advance(state, weather_segment) -> decode(state)
                                          └──────────────> branch(state, weather_A/B)

(d) The unique C0R/C1 difference（C0R/C1 唯一核心差分）

 C0R direct factual path（直接事实路径）:
 z_0 ───────────── T[u_0:H] ────────────> z_H ──> y_hat_H ── L(y_hat_H, y_H)

 C1 recursive factual path（递归事实路径）:
 z_0 ─ T[u_0:k] ─> z_k ─ T[u_k:H] ───> z'_H ──> y_hat'_H ── L(y_hat'_H, y_H)

 Same parameters / RNG / endpoints / budget / explicit consistency lambda = 0
（参数、随机数、端点、预算相同；显式一致性损失权重为 0）

(e) Temporal partitions（时间分段）
 train partitions（训练分段） ∩ held-out Q4 partitions（Q4 留出分段） = ∅
```

| Panel | 当前可填内容 | 空缺 |
|---|---|---|
| (a) Context initialization（上下文初始化） | PVT-v2/Contextformer、prior、projector 已实现 | 最终矢量图 |
| (b) Shared T（共享转移） | 变跨度、多次共享调用已实现 | 标清天气窗口与 offset |
| (c) Runtime state/API（运行状态/接口） | 机制具备 | 统一 save/load 薄接口与 demo |
| (d) C0R/C1 factual path（事实路径） | 代码差分已确认 | 与方法公式逐项核对 |
| (e) Held-out partitions（留出分段） | 训练/评测分段隔离已实现 | 列出最终冻结集合 |

---

## Fig. 3 · GreenEarthNet 多时距定性预测

**目的**：让审稿人直接检查主数据集上的像素级预测、长时退化和失败模式，而不只看到平均 R²/RMSE。

| Split / sample（划分/样例） | Last context（历史末帧） | GT h=5/10/20 | Persistence | PredRNN | Contextformer | **C1** | Absolute-error maps（绝对误差图） |
|---|---|---|---|---|---|---|---|
| IID / frozen P25 | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] |
| OOD-t / frozen P50 | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] |
| OOD-s / frozen P75 | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] |
| OOD-st / high dynamic | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] |
| Frozen failure case（冻结失败案例） | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] |

执行约束：所有方法使用同一样例、mask、时间点和色标；样例按 C1 per-cube RMSE 的固定分位与动态幅度在排版前冻结；完整随机样例网格和全序列放补充材料。

---

## Fig. 4 · EarthNet2023-Africa 独立数据集定性预测

**目的**：给出跨地区、跨生态与跨协议的空间外部有效性，并主动展示典型结果和失败边界。

| Sample | Last context | GT short/mid/long | Persistence_A | Strong baseline_A | Contextformer_A | **C1_A** | Error map |
|---|---|---|---|---|---|---|---|
| Typical 1 | -- | -- | -- | -- | -- | -- | -- |
| Typical 2 | -- | -- | -- | -- | -- | -- | -- |
| High dynamic | -- | -- | -- | -- | -- | -- | -- |
| Failure case | -- | -- | -- | -- | -- | -- | -- |

`C1_A` 表示在 EarthNet2023-Africa 上重新训练/合法适配的同一 TerraState-C1 原理，不是把 GreenEarthNet 的 `C1_G` 权重直接拿来预测。若额外研究 `C1_G -> Africa`，应作为 transfer/zero-shot（迁移/零样本）实验单列，不能替代本图。

---

## Fig. 5 · 两数据集预测时距与 OOD 退化曲线

**目的**：展示预测误差随真实未来时距如何累积，说明 C1 的竞争力和代价在何时出现；不重复 Table 1-2 的总体平均数。

```text
(a) GreenEarthNet R²↑                        (b) GreenEarthNet RMSE↓
 0.7 |  PredRNN / Contextformer / C1          0.24 |
     |  four split small multiples                 |  IID / OOD-t / OOD-s / OOD-st
 0.6 |  with 95% CI                          0.20 |  with 95% CI
 0.5 |                                       0.16 |
 0.4 |_______________________________        0.12 |_______________________________
       day 5  day 10  day 15  day 20                 day 5  day 10  day 15  day 20
       [逐时距与多种子结果待导出]                    [逐时距与多种子结果待导出]

(c) Africa native metric（原生指标）          (d) Africa common NDVI metric（共同指标）
  -- |                                       -- |
     | [待训练与导出]                           | [待训练与导出]
  -- |________________________________       -- |________________________________
       actual forecast days（真实预测天数）          actual forecast days（真实预测天数）
```

GreenEarthNet 使用 `2x2` 小多图覆盖四 split；两数据集时间分辨率不同则分别标真实天数。相同方法跨面板保持同色，置信带来自多种子/聚类 bootstrap，不能用单种子曲线伪装统计稳定性。

---

## Fig. 6 · Q2 显式状态承载

**目的**：展示状态贡献在什么时距、什么样本和什么空间区域出现；Table 4 负责精确总体效应和判定。

```text
(a) Intervention（干预）
 Same model/input ──> full:       y_hat = P + 1 * O(z)
                  └─> prior-only: y_hat = P + 0 * O(z)

(b) Horizon dependence（随时距变化）
 ΔR² / ΔRMSE
   ↑       IID / OOD-t / OOD-s / OOD-st
   |      [逐时距曲线待导出]
 0 +--------------------------------------> forecast days

(c) Sample distribution（样本分布）
 per-cube/per-tile ΔRMSE ECDF or violin（经验累积分布/小提琴图）
 [四 split、零效应线、cluster-bootstrap CI 待导出]

(d) Spatial mechanism evidence（空间机制证据）
```

| Frozen contribution level | GT | Full C1 | Prior-only | Error full | Error prior-only | State contribution map（状态贡献图） |
|---|---|---|---|---|---|---|
| High | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] |
| Median | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] |
| Low | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] |

当前总体效应仅作为绘图校验锚点，不把四行 Table 4 再画成柱状图：

```text
Paired mean ΔR² = R²(full) - R²(prior-only)

IID     0.031381  CI [0.025315, 0.037247]
OOD-s   0.028741  CI [0.024551, 0.032919]
OOD-st  0.021049  CI [0.015030, 0.027153]
OOD-t   0.018935  CI [0.010882, 0.026923]
```

Fig. 6 的 `(a)-(d)` 全部制作并组成一张综合图，不是四选一；若版面不足，完整四 split 分布放补充材料，主文仍保留时距、分布摘要和空间案例。

---

## Fig. 7 · Q3 天气响应与条件分支

**目的**：从“天气输入如何改变”一路展示到“NDVI 轨迹和空间终点如何改变”，证明模型使用了所提供的未来天气；Table 5 负责精确效应、CI 与负结果。

```text
(a) Weather trajectories（天气轨迹）
 Same runtime state z_k
    ├─ actual weather（真实天气）:  temperature / precipitation / ...
    ├─ donor weather（匹配错配天气）
    └─ mean weather（均值天气）

(b) Predicted NDVI trajectories（NDVI 预测轨迹）
 NDVI
   ↑        GT ─────────────
   |        actual ─────────
   |        donor  - - - - -
   |        mean   · · · · ·
   +--------------------------------> forecast days

(c) Endpoint maps（终点地图）
 GT | Actual | Donor | Mean

(d) Difference/error maps（差异/误差图）
 Actual-Donor | Actual-Mean | Error(actual)-Error(donor/mean)
```

| 当前统计锚点 | Value | 95% geo-cluster CI | 结论 |
|---|---:|---|---|
| Actual vs donor ΔLoss | **0.002053** | **[0.000761, 0.003452]** | PASS |
| Actual vs mean ΔLoss | **0.010140** | **[0.004839, 0.015558]** | PASS |
| Hot-dry interaction（热旱交互） | **-0.000302** | **[-0.002841, 0.002582]** | FAIL，不主张热旱特异增强 |

| Extreme subset（极端子集） | R²↑ | RMSE↓ | Spatial endpoint |
|---|---:|---:|---|
| **Actual** | **0.634493** | **0.147289** | [图像待导出] |
| Donor | 0.588372 | 0.156135 | [图像待导出] |
| Mean | 0.557833 | 0.192398 | [图像待导出] |

Fig. 7 的 `(a)-(d)` 全部制作并组成一张综合图，不是从“天气、轨迹、地图、差异图”中任选一个。图中统一写 conditional branch/response（条件分支/响应），不得写 causal counterfactual（因果反事实）。

---

## Fig. 8 · Q4 直接推进与分段推进一致性

**目的**：这是 TIP 新主线的定义性结果图；它要证明中间状态可以继续代表模型所理解的当前世界，并证明该性质来自 C1 的递归事实监督，而非参数增加。

```text
(a) Protocol（协议）
 Direct（直接）:       z_0 ───────── T[u_0:H] ─────────────> z_H
 Segmented（分段）:    z_0 ─ T[u_0:k] ─> z_k ─ T[u_k:H] ─> z'_H
 Same state/forcing/T, different computation graphs（同状态、天气和 T，不同计算图）

(b) Degradation vs horizon/segments（随时距与分段数退化）

 Worst segmented degradation↓
 h=10  C1  | #               0.8%      C0R | #########       9.2%
 h=15  C1  | #               1.0%      C0R | #########       9.1%
 h=20  C1  | #               1.2%      C0R | ############### 14.7%

 [终稿改为带 CI 的折线/点线图；当前条形仅作数值草图]

(c) State/output gap distribution（状态/输出差距分布）
 C1 direct-segmented:  [待导出 per-cube/per-tile 分布]
 C0R direct-segmented: [待导出 per-cube/per-tile 分布]

(d) Spatial endpoints（空间终点）
```

| Horizon | GT | C1 direct | C1 segmented | C1 abs. diff | C0R direct | C0R segmented | C0R abs. diff |
|---:|---|---|---|---|---|---|---|
| 10 | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] |
| 15 | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] |
| 20 | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] | [图像待导出] |

Fig. 8 的 `(a)-(d)` 全部制作并组成一张综合图。Table 6 已负责精确 gate 和 19/19 统计，因此本图不再放大面积 PASS/FAIL 矩阵。必须在图注说明：原 per-cube R² `G_abs` 的 4/19 是聚合规格错误；同批封存统计中的 pooled-RMSE 为 19/19，修正 pooled-R² 后三种资格口径也均为 19/19。不能改写成“原门预注册通过”。

---

# 第二部分：七张主表草图

## Table 1 · GreenEarthNet 同协议预测主表

**目的**：用统一 manifest、mask、scorer 和 forecast horizon 给出 Q1 基础预测竞争力；不把 C1 写成当前未达到的精度 SOTA。

| Method（方法） | Seeds | IID R² / RMSE | OOD-t R² / RMSE | OOD-s R² / RMSE | OOD-st R² / RMSE | Params |
|---|---:|---:|---:|---:|---:|---:|
| Persistence | deterministic | 0.0000 / 0.2213 | 0.0000 / 0.2157 | 0.0000 / 0.2258 | 0.0000 / 0.2183 | 0 |
| Climatology | -- | -- | -- | -- | -- | 0 |
| Previous Year | -- | -- | -- | -- | -- | 0 |
| ConvLSTM | 3 | 0.5107 / 0.1557 | 0.5483 / 0.1615 | 0.4761 / 0.1622 | 0.5234 / 0.1610 | 1.04M |
| PredRNN | 3 | **0.5414 / 0.1423** | **0.5925 / 0.1474** | **0.5087 / 0.1494** | **0.5635 / 0.1479** | 1.43M |
| SimVP | 3 | 0.4988 / 0.1461 | 0.5616 / 0.1492 | 0.4650 / 0.1529 | 0.5275 / 0.1553 | 6.59M |
| Contextformer | 3 | 0.5333 / 0.1484 | 0.5877 / **0.1431** | 0.5021 / 0.1549 | 0.5567 / **0.1473** | 6.06M |
| **TerraState-C1** | **1（待补 2）** | 0.5220 / 0.1555 | 0.5726 / 0.1509 | 0.4949 / 0.1621 | 0.5408 / 0.1542 | 7.18M |
| Earthformer | -- | n.a. | n.a. | n.a. | n.a. | -- |

AAAI 原稿 OOD-t 的 V2 为 `R²=0.569349, RMSE=0.150594`；当前 C1 为 `R²=0.572604, RMSE=0.150941`，即 R² `+0.003255`、RMSE `+0.000347`（略差）。应表述为“增加持续状态能力后预测整体持平”，不能表述为更准。

---

## Table 2 · EarthNet2023-Africa 独立训练预测主表

**目的**：验证 Q1 是否跨独立地区、生态与数据协议成立；同时报告数据集原生指标和共同 NDVI 指标。

| Method（方法） | Seeds | Native val metric↑（原生验证指标） | Native test metric↑（原生测试指标） | NDVI R²↑ | NDVI RMSE↓ | Params |
|---|---:|---:|---:|---:|---:|---:|
| Persistence_A | -- | -- | -- | -- | -- | 0 |
| Climatology_A | -- | -- | -- | -- | -- | 0 |
| Official baseline A | -- | -- | -- | -- | -- | -- |
| Strong video baseline_A | -- | -- | -- | -- | -- | -- |
| Contextformer_A | -- | -- | -- | -- | -- | -- |
| C0R_A | -- | -- | -- | -- | -- | 7.18M* |
| **TerraState-C1_A** | -- | -- | -- | -- | -- | 7.18M* |

`*` 输入维度或输出头适配后需重新统计参数量。Table 2 来自第二数据集上的独立训练流程；同一套 `C0R_A/C1_A` 权重再进入 Table 4-6 的精简 Q2-Q4 复验。

---

## Table 3 · 核心机制与消融总表（GreenEarthNet）

**目的**：区分外部骨干差异、C0R/C1 训练路径差异和功能干预，证明贡献来自递归事实监督与共享状态机制，而不只是参数量。

| Model/intervention（模型/干预） | Explicit state（显式状态） | Shared T（共享转移） | Weather（天气） | Recursive factual path（递归事实路径） | OOD-t R²↑ | Q2 | Q3 | Q4 |
|---|:---:|:---:|:---:|:---:|---:|---|---|---|
| Contextformer | × | × | ✓ | × | 0.5877 | n.a. | -- | n.a. |
| C0R | ✓ | ✓ | ✓ | × | -- | -- | -- | **FAIL（锁定）** |
| **C1** | ✓ | ✓ | ✓ | ✓ | **0.572604** | **PASS** | **PASS** | **PASS（锁定）** |
| C1 prior-only / `alpha=0` | 状态读出关闭 | 保留 | ✓ | ✓ | 0.555527 | control（对照） | -- | -- |
| C1 identity-T（恒等转移） | ✓ | identity（恒等） | 条件不起正常推进作用 | ✓ | 0.554934 | support（辅助） | -- | -- |
| C1 donor weather（错配天气） | ✓ | ✓ | donor | ✓ | -- | -- | control | -- |
| C1 mean weather（均值天气） | ✓ | ✓ | mean | ✓ | -- | -- | control | -- |
| C1 w/o geo（移除地理） | ✓ | ✓ | ✓ | ✓ | -- | -- | -- | -- |

V2 不作为主表必需行；它是 AAAI 前代模型，最多放补充材料。Contextformer 是外部强基线，不是 TerraState 内部同构消融；C0R 才是证明 C1 机制的关键控制组。

---

## Table 4 · Q2 状态承载定量表

**目的**：精确报告 full（完整模型）相对 prior-only（仅上下文先验）的状态贡献、统计区间和判定；Fig. 6 展示其时间、分布与空间形态。

| Dataset/Split | Model | Seeds | Full R²↑ | Prior-only R²↑ | Official ΔR²↑ | Paired mean ΔR²↑ | 95% CI | Decision |
|---|---|---:|---:|---:|---:|---:|---|---|
| GreenEarthNet / IID | C1_G | 1 | 0.522028 | 0.488350 | **0.033679** | 0.031381 | [0.025315, 0.037247] | **LOAD_BEARING** |
| GreenEarthNet / OOD-t | C1_G | 1 | 0.572604 | 0.555527 | **0.017077** | 0.018935 | [0.010882, 0.026923] | **LOAD_BEARING** |
| GreenEarthNet / OOD-s | C1_G | 1 | 0.494874 | 0.461436 | **0.033439** | 0.028741 | [0.024551, 0.032919] | **LOAD_BEARING** |
| GreenEarthNet / OOD-st | C1_G | 1 | 0.540760 | 0.523713 | **0.017047** | 0.021049 | [0.015030, 0.027153] | **LOAD_BEARING** |
| GreenEarthNet / all splits | C1_G | 3 | -- | -- | -- | -- | [--, --] | -- |
| EarthNet2023-Africa / Test | C1_A | -- | -- | -- | -- | -- | [--, --] | -- |

Table 4 不要求把所有视频预测基线加入，因为普通基线没有与 `alpha=0` 同构的状态支路。第二数据集使用独立训练的 `C1_A` 做精简 full/prior-only 复验。

---

## Table 5 · Q3 条件天气响应定量表

**目的**：精确检验真实天气相对错配/均值天气是否提供更高终点保真，并公开热旱特异性未成立的边界。

| Dataset/Subset | Model | Comparison（比较） | R² actual↑ | R² control↑ | RMSE actual↓ | RMSE control↓ | ΔLoss↑ | 95% geo-cluster CI | Decision |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| GreenEarthNet / Overall | Contextformer | Actual vs donor | -- | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet / Overall | Contextformer | Actual vs mean | -- | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet / Overall | C0R_G | Actual vs donor/mean | -- | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet / Overall | **C1_G** | Actual vs donor | -- | -- | -- | -- | **0.002053** | **[0.000761, 0.003452]** | **PASS** |
| GreenEarthNet / Overall | **C1_G** | Actual vs mean | -- | -- | -- | -- | **0.010140** | **[0.004839, 0.015558]** | **PASS** |
| GreenEarthNet / Extreme | **C1_G** | Actual vs donor | **0.634493** | 0.588372 | **0.147289** | 0.156135 | -- | [--, --] | actual > donor |
| GreenEarthNet / Extreme | **C1_G** | Actual vs mean | **0.634493** | 0.557833 | **0.147289** | 0.192398 | -- | [--, --] | actual > mean |
| GreenEarthNet / Hot-dry | **C1_G** | Interaction | n.a. | n.a. | n.a. | n.a. | **-0.000302** | **[-0.002841, 0.002582]** | **FAIL** |
| EarthNet2023-Africa / Overall | Weather baseline_A | Actual vs control | -- | -- | -- | -- | -- | [--, --] | -- |
| EarthNet2023-Africa / Overall | **C1_A** | Actual vs control | -- | -- | -- | -- | -- | [--, --] | -- |

Q3 需要代表性 weather-aware baseline（天气感知基线），因为“是否使用天气”不是 TerraState 独有接口；无天气输入模型记为 `n.a.`，不能硬做不公平干预。

---

## Table 6 · Q4 持续推进与分段一致性定量表

**目的**：精确报告 C1/C0R 在不同终点和分段方式下的直接/分段准确性、相对退化、CI 与 gate；Fig. 8 展示过程、分布和空间现象。

### (a) 已完成的锁定评测

| Dataset | Model | Horizon | Direct RMSE↓ / R²↑ | Worst segmented degradation↓ | Q4 gates | Status |
|---|---|---:|---:|---:|---|---|
| GreenEarthNet locked | **C1** | 10 | 0.1377 / 0.630 | **0.8%** | 4/4 PASS | **PASS** |
| GreenEarthNet locked | **C1** | 15 | 0.1596 / 0.493 | **1.0%** | 4/4 PASS | **PASS** |
| GreenEarthNet locked | **C1** | 20 | 0.1617 / 0.531 | **1.2%** | 4/4 PASS | **PASS** |
| GreenEarthNet locked | C0R | 10 | 0.1369 / 0.634 | 9.2% | 2/4 PASS | **FAIL** |
| GreenEarthNet locked | C0R | 15 | 0.1600 / 0.491 | 9.1% | 2/4 PASS | **FAIL** |
| GreenEarthNet locked | C0R | 20 | 0.1628 / 0.525 | 14.7% | 2/4 PASS | **FAIL** |

### (b) 待补的确认评测

| Dataset | Model | Seeds | Horizon | Partition | Direct RMSE↓ | Segmented RMSE↓ | Relative degradation↓ | Pooled R²↑ | 95% CI | Gate |
|---|---|---:|---:|---|---:|---:|---:|---:|---|---|
| GreenEarthNet confirm | C0R_G | -- | 10/15/20 | 2/3/4 segments | -- | -- | -- | -- | [--, --] | -- |
| GreenEarthNet confirm | **C1_G** | -- | 10/15/20 | 2/3/4 segments | -- | -- | -- | -- | [--, --] | -- |
| EarthNet2023-Africa | C0R_A | -- | -- | -- | -- | -- | -- | -- | [--, --] | -- |
| EarthNet2023-Africa | **C1_A** | -- | -- | -- | -- | -- | -- | -- | [--, --] | -- |

锁定结果的正确写法：C1 单臂四门通过，C0R 失败关键门；原 per-cube R² `G_abs` 腿产生的 4/19 属于聚合规格错误，不再作为负面结论。同批封存统计量中 pooled-RMSE 腿 19/19 通过，修正为 pooled-R² 后三种资格口径也均为 19/19，因此有效结论是“修正后的事实端点非劣审计 19/19 通过”；不能改写成“原 per-cube 门预注册通过”。

---

## Table 7 · 参数量、计算量与状态接口成本

**目的**：说明可续推状态的计算、显存、状态序列化和恢复代价是否可接受，并避免只比较参数量。

| Method | Params↓ | FLOPs/sample↓ | Peak VRAM↓ | Train time/epoch↓ | Direct inference↓ | Segmented inference↓ | Runtime state size↓ | Save/load time↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PredRNN | **1.43M** | -- | -- | -- | -- | n.a. | n.a. | n.a. |
| Contextformer | **6.06M** | -- | -- | -- | -- | n.a. | n.a. | n.a. |
| C0R | **7.18M** | -- | -- | -- | -- | -- | -- | -- |
| **TerraState-C1** | **7.18M** | -- | -- | -- | -- | -- | -- | -- |

---

# 第三部分：模型与数据集覆盖规则

| 证据 | GreenEarthNet | EarthNet2023-Africa | 是否需要所有外部基线 |
|---|---|---|---|
| Table 1/2、Fig. 3-5：Q1 | 各模型按同协议训练/评测 | 各模型在 Africa 上重新训练/合法适配 | 需要 Persistence、Contextformer、代表性视频/官方强基线 |
| Table 3：机制消融 | **完整消融只在主数据集做** | 只保留 C0R_A/C1_A 核心确认 | 不需要把所有外部基线变成内部消融 |
| Table 4、Fig. 6：Q2 | C1 三种子 × 四 split 完整报告 | 独立训练 `C1_A` 做精简 full/prior-only | 不需要；普通基线没有同构状态读出 |
| Table 5、Fig. 7：Q3 | C1 必做，C0R/Contextformer 提供行为对照 | `C1_A` 必做，并选天气感知强基线 | 只需要代表性 weather-aware baseline |
| Table 6、Fig. 8：Q4 | C0R/C1 多终点、多分段、多种子 | `C0R_A/C1_A` 做精简确认 | 不需要；无可恢复状态接口者无法公平评测 |

第二数据集的角色不是更换 PVT 编码器或直接使用 GreenEarthNet 权重，而是**保持同一 TerraState-C1 原理，在独立数据上重新训练并用该数据集原生指标与共同 NDVI 指标评价**。完整消融集中在 GreenEarthNet，可以避免把计算预算浪费在重复证明每个部件；Africa 只复验主模型和 C0R/C1 核心机制。

---

# 第四部分：完成优先级

| 优先级 | 必须完成的实验/产物 | 直接封住的审稿风险 | 对应图表 | 最低完成判定 |
|---|---|---|---|---|
| P0-1 | 冻结 C1/C0R 配置、事实路径、Q4 pooled 协议 | 主模型与机制定义漂移 | Fig. 2、Table 3/6 | 配置、manifest、公式、代码路径一致 |
| P0-2 | C1 补齐 3 seeds × 4 splits | C1 与三种子基线统计不公平 | Table 1、Fig. 5、Table 4/6 | mean±std/CI 可报告，结论方向稳定 |
| P0-3 | C0R/C1 同 seed/预算补齐 Q1、Q2、Q4 | Q4 可能来自参数、数据或运气 | Fig. 8、Table 3/6 | C1 优势跨种子保持且 Q1 不坍塌 |
| P0-4 | 用已有结果生成 GreenEarthNet 五张结果图草稿 | 只有标量，没有空间/过程证据 | Fig. 3、5-8 | 样例冻结，曲线/分布/地图均可追溯 |
| P0-5 | 实现并验证 state save/load/resume 薄接口 | “暂停/恢复”可能只是图示包装 | Fig. 2、Table 7 | 不重编码历史即可恢复，数值与内存连续推进一致 |
| P0-6 | 补直接同行协议级比较或清晰协议矩阵 | 仅与旧视频基线比较，未回应 EO 世界模型同行 | Table 1-3 / Related Work | 可比结果已跑；不可比项明确说明差异 |
| P1-1 | EarthNet2023-Africa 数据、任务、许可、时间步审计 | 第二数据集不独立或指标不合法 | Fig. 4-5、Table 2 | 输入/目标/mask/native metric 冻结 |
| P1-2 | Africa 强基线与 C0R_A/C1_A 独立训练 | 单数据集现象 | Fig. 4-5、Table 2 | 同协议主表与定性图完成 |
| P1-3 | Africa 精简 Q2-Q4 复验 | 状态性质只在 GreenEarthNet 成立 | Table 4-6，必要时 Fig. 6-8 小面板 | Q2/Q3/C1-vs-C0R Q4 方向一致或诚实收窄主张 |
| P1-4 | FLOPs、显存、速度、state size、save/load time | 新能力代价不透明 | Table 7 | 同硬件、同 batch、预热后统一测量 |
| P1-5 | 全文按新主线重写 | 结果新增但论文仍像 AAAI 加长版 | Fig. 1-2 与全文 | 标题/摘要/引言/方法/实验均以 C1 与 Q4 为中心 |

当前已经完成的核心事实是：E1 基线 `48/48`、C1 Q1 单种子、Q2 四 split、Q3 主响应、Q4 锁定核心证据。当前最先应补的是 **C1 多种子、C0R/C1 严格确认、已有结果的 Fig. 3/5/6/7/8 草图**；随后再进入第二独立数据集。做到 P0 全部完成并且 P1-1 至 P1-3 成立，才形成 TIP 主线的最低可信闭环。
