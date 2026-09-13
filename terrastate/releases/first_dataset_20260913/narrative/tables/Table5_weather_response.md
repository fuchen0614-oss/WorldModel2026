# Table 5. 天气条件作用（Q3 冻结热旱子集）

来源：`/data/zs/WorldModel2026/terrastate/evaluations/candidate_c_q1q2q3_20260830T072737Z/q3/extreme_state_audit.json`
（kind=`extreme_hotdry_state_audit`，evidence_role=`final`，协议 sha `{'hotdry_manifes…`）。
冻结范围：热旱 **84** 个样本；匹配正常唯一对照 **45** 个；配对 **84** 对；bootstrap n=**10000**。
模型：`exclusive`（C1 体系）**单臂**；`weather_in_base=False`；`diagnostic_only=False`。

## 5.0 本表统一的实际时间窗口（已按源码核实，全表一致）

本表**所有** ΔLoss 与精度数字都是**完整 20 步目标窗口**（history 10 → forecast 20，均为五日步）上按有效像素求掩码 MSE 的结果，
**不是**第 20 步单帧误差。核实依据：`eval/extreme_state_audit.py` 的函数 `_endpoint_masked_mse(pred, data, model, mask)` 使用 `cl, tl = model.context_len, model.target_len`。
历史字段名 `endpoint_fidelity` / `loss_e_*` 是**旧命名**，与它实际计算的窗口不一致；引用时按本节的窗口表述。

## 5.1 该子集内的端点精度（actual / donor / mean）

| 条件 | R² | RMSE | NSE |
|---|---:|---:|---:|
| actual | 0.6345 | 0.1473 | 0.0130 |
| donor | 0.5884 | 0.1561 | -0.1025 |
| mean | 0.5578 | 0.1924 | -0.6158 |

> 规范要求：endpoint fidelity requires R2(actual) > R2(donor) AND R2(actual) > R2(mean).
> → `R²(actual)=0.6345` 同时高于 donor (0.5884) 与 mean (0.5578)，该判据成立。

## 5.2 真实损失收益：ΔLoss（**完整 20 步窗口**，control − actual；正值＝实际天气使误差更低）

| 比较 | ΔLoss | paired 95% CI | geo-cluster 95% CI (n组) | reused-control 95% CI (n组) | n | paired 显著>0 |
|---|---:|---|---|---|---:|---|
| actual vs donor（替换为匹配 donor 天气） | 0.002053 | [0.000793, 0.003352] | [0.000761, 0.003452] (31) | [0.000715, 0.003361] (45) | 84 | 是 |
| actual vs mean（替换为归一化均值天气） | 0.010140 | [0.006782, 0.013770] | [0.004839, 0.015558] (31) | [0.004760, 0.015883] (45) | 84 | 是 |

区间解释：`paired` 为样本级配对 bootstrap，`geo_cluster` 为空间组整簇重采样，
`reused_control` 为匹配对照簇重采样；**三者给出的符号结论一致**，但它们是不同的重采样单位。

## 5.3 响应幅度（**不是**损失收益——只说明预测被天气替换推动了多远）

`response_magnitude` 是**预测变化幅度**，与误差是否下降无关；它**不能**当作“天气替换带来了收益”的证据。

| 比较 | 响应幅度 | n |
|---|---:|---:|
| 热旱集 actual vs donor | 0.034663 | 84 |
| 热旱集 actual vs mean | 0.079716 | 84 |
| 匹配正常集 actual vs donor | 0.033858 | 84 |
| 匹配正常集 actual vs mean | 0.062234 | 84 |

## 5.4 热旱−正常交互：按“响应幅度”与“真实损失收益”**分开**报告

两个量纲的单位都是损失（归一化 NDVI 的 MSE 尺度），但含义不同，必须分开读：
**响应幅度**侧的交互可以显著，**损失收益**侧的交互可以不显著——二者不矛盾。

### 5.4a 响应幅度侧的交互（hot-dry − normal）

| 量 | 点估计 | paired 95% CI | geo-cluster 95% CI (n组) | reused-control 95% CI (n组) | paired 显著>0 |
|---|---:|---|---|---|---|
| resp_donor（donor 替换下的响应幅度差） | 0.000806 | [-0.001428, 0.003121] | [-0.001679, 0.002984] (31) | [-0.002437, 0.003683] (45) | 否 |
| resp_mean（mean 替换下的响应幅度差） | 0.017482 | [0.009628, 0.025337] | [0.006463, 0.027492] (31) | [0.007023, 0.027779] (45) | 是 |

### 5.4b 真实损失收益侧的交互（hot-dry − normal）

| 量 | 点估计 | paired 95% CI | geo-cluster 95% CI (n组) | reused-control 95% CI (n组) | paired 显著>0 |
|---|---:|---|---|---|---|
| dloss_donor（donor 替换的损失收益差） | -0.000302 | [-0.002321, 0.001759] | [-0.002841, 0.002582] (31) | [-0.003153, 0.002443] (45) | 否 |
| dloss_mean（mean 替换的损失收益差） | 0.007838 | [0.004395, 0.011532] | [0.003225, 0.011961] (31) | [0.002767, 0.013311] (45) | 是 |

**读法（仅转述源 JSON 的判定，不新增推断）**：
- `resp_mean` 的 95% CI 不含 0（[0.009628, 0.025337]）→ 热旱集在 mean 替换下**响应幅度更大**；
- `resp_donor` 的 95% CI **跨 0**（[-0.001428, 0.003121]）→ donor 替换下的响应幅度差不显著；
- `dloss_donor` 的 95% CI **跨 0**（[-0.002321, 0.001759]）→ 热旱相对正常的**损失收益**差在 donor 替换下不显著；
- `dloss_mean` 的 95% CI 不含 0（[0.004395, 0.011532]）→ mean 替换下损失收益差为正。
- 因此**不能**用“响应幅度更大”推断“热旱下天气替换收益更大”。

## 5.5 热旱 vs 匹配正常队列：各分量交互（cohort）

单位：响应尺度；`direction` 与 `n_missing_pairs` 原样转录。

| 分量 | 点估计 | paired 95% CI | geo-cluster 95% CI (n组) | paired 显著>0 | direction | 缺失配对 |
|---|---:|---|---|---|---|---:|
| resp_clim | 0.017482 | [0.009628, 0.025337] | [0.006463, 0.027492] (31) | 是 | `hotdry>normal` | 0 |
| resp_flip | -0.004542 | [-0.007711, -0.001511] | [-0.007877, -0.000897] (31) | 否 | `hotdry<=normal` | 0 |
| contrib_state | 0.009349 | [0.003599, 0.015168] | [0.001416, 0.017004] (31) | 是 | `hotdry>normal` | 0 |
| state_move | 0.006534 | [0.002107, 0.010988] | [0.001248, 0.011118] (31) | 是 | `hotdry>normal` | 0 |

## 5.6 分层效应均值（响应尺度，非损失收益）

| stratum | contrib_state | resp_clim | resp_flip | state_move |
|---|---:|---:|---:|---:|
| hotdry | 0.052681 | 0.079716 | 0.023781 | 0.270629 |
| matched_normal | 0.040518 | 0.054879 | 0.029100 | 0.260238 |

> 各分量 n：`{"hotdry": {"resp_clim": 84, "resp_flip": 84, "contrib_state": 84, "state_move": 84}, "matched_normal": {"resp_clim": 45, "resp_flip": 45, "contrib_state": 45, "state_move": 45}}`（热旱 n=84，匹配正常唯一对照 n=45）。

## 5.7 分层精度（按臂）

| stratum | 臂 | R² | RMSE | NSE | biasabs |
|---|---|---:|---:|---:|---:|
| hotdry | full | 0.6345 | 0.1473 | 0.0130 | 0.1038 |
| hotdry | closure_zero_scale | 0.5909 | 0.1742 | -0.3766 | 0.1285 |
| hotdry | t_identity | 0.5899 | 0.2210 | -0.7886 | 0.1805 |
| matched_normal | full | 0.5465 | 0.1597 | -0.2225 | 0.1115 |
| matched_normal | closure_zero_scale | 0.5502 | 0.1755 | -0.5062 | 0.1234 |
| matched_normal | t_identity | 0.5497 | 0.2249 | -1.0442 | 0.1811 |

## 5.8 源 JSON 的判定状态（原样转录）

| 字段 | 值 |
|---|---|
| `endpoint_fidelity_status` | **PASS** |
| `hotdry_enhancement_status` | **FAIL** |
| `primary_criterion` | `geo_cluster_bootstrap_ci_low_gt0` |
| `raw_status` | `Q3_RESPONSE_FIDELITY_ONLY` |
| `overall_status` | `Q3_RESPONSE_FIDELITY_ONLY` |
| `uf_differs_all_pairs` | True |
| `n_pairs`（q3） | 84 |

> `endpoint_fidelity_status=PASS` 指的是 5.1 的 R² 判据；`hotdry_enhancement_status=FAIL` 指的是
> “热旱下天气替换的收益**增强**”这一主张未通过其主判据。**两者同时成立，不冲突。**

## 5.9 口径与范围警告（引用本表时必须一并带上）

1. **窗口**：全部 ΔLoss 是完整 20 步窗口（见 5.0），不是单终点帧误差；字段名是旧命名。
2. **响应幅度 ≠ 损失收益**：5.3 / 5.4a / 5.5 / 5.6 是响应尺度；5.2 / 5.4b 是损失收益尺度。
   前者显著不蕴含后者显著，本表的 `dloss_donor` 就是不显著的反例。
3. **范围**：只覆盖**冻结的热旱子集及其匹配正常对照**，**不是**全体样本的总体天气评测。
4. **未做**：本轮未新增任何抽样天气评测；未做 C0R / Contextformer 的代表模型天气对照；
   未做其他 split 的天气对照。
5. **mean 对照的含义**：是**归一化天气置零**，不是物理意义上的“无天气”。
6. **单臂**：只有 `exclusive`（C1 体系）一个模型，`weather_in_base=False`，没有第二臂可对照。
7. **不新增推断**：本表的全部结论均转述源 JSON 的字段值与其自带 `*_status`，未做新的显著性判断。

