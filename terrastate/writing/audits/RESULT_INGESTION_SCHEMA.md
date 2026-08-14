# TerraState AAAI-27 结果接入规范

> 目的：把唯一冻结 checkpoint 的真实 JSON/CSV 结果安全接入 `paper/main.tex` 的表 1–3 与结果句。  
> 本规范是写作接口，不是新 benchmark，也不授权修改训练或评测代码。  
> 状态更新（2026-07-27）：Q1–Q3 已依据
> `../WorldModel2026-planb/TERRASTATE_V2_EVIDENCE.md` 的冻结记录接入正文。
> 当前正文表 1、表 2、表 3 分别对应 Q1、Q2、Q3；Q4 不进入正文表格。
> 本文件以下字段继续作为投稿前 Release 原始 JSON/CSV 的 fail-closed 复核接口，
> 不是当前正文仍含 `TBD` 的含义。由于工作区快照中未见记录所指 checkpoint 和
> 原始结果 JSON，仍需在 Release 到位后逐字段复核 SHA、serialized config、
> selection、manifest、scorer、mask/aggregation 与 Q3 donor/normalizer/threshold。

## 1. 全局身份与 fail-closed 规则

Q1–Q4 必须共享：

```json
{
  "schema_version": "terrastate_result_ingestion_v3",
  "model_id": "TerraState",
  "inference_contract_id": "history_q__full24_static_h_T__context_prior_plus_state_v2",
  "driver_protocol": "full24",
  "training_objective_id": "gt_1__kd_0p5__future_state_scheduled",
  "checkpoint_sha256": "HEX",
  "serialized_config_sha256": "HEX",
  "data_manifest_sha256": "HEX",
  "evaluator_commit": "HEX_OR_ARCHIVE_SHA",
  "mask_protocol_id": "STRING",
  "aggregation_protocol_id": "STRING",
  "selection_record_sha256": "HEX",
  "test_lock_id": "STRING"
}
```

以下任一情况发生时停止回填，正文保留 `TBD`：

1. Q 文件间 `checkpoint_sha256`、serialized config、data manifest 或 evaluator 身份不一致；
2. checkpoint 不是验证集规则选择的唯一模型；
3. OOD-t 被用于选模、early stopping、性能判定阈值或样例选择；Q3 只允许按下文声明的方式，在模型评分前使用输入侧时间/位置/未来天气确定 donor，不得使用目标、预测或误差；
4. 正式 evaluator 状态不是 `COMPLETE`，或含 `NaN/Inf/null` 的必填字段；
5. Q3 缺 donor/normalizer/threshold manifest，或 context prior 跨臂不变性失败；
6. 可选 Q4 缺 guard/evaluation-partition manifest，或评测分段与写作表不一致；
7. 只存在中间训练结果、聊天记录或手工抄写数值；
8. 公开论文数字被误放入本地配对比较。
9. TerraState 专用预测导出器、严格 schema adapter 或跨文件身份检查尚未通过；现有旧模型组表脚本不能替代这些前置门。

## 2. 推荐结果包

```text
final_result_package/
├── manifest.json
├── artifact_registry.json
├── validation_selection.json
├── q1_forecast.csv
├── q1_paired.csv
├── q2_load_bearing.csv
├── q3_driver.csv
├── q4_composition.csv
├── q4_state_summary.csv
├── ablations.csv
├── matched_b4_fairness.json
├── q2_q3_thresholds.json
├── q4_guard_and_retention.json
├── q4_broken_path_manifest.json
├── qualitative_manifest.json
└── raw/
    ├── state_contract_exclusive.json
    ├── commands.txt
    └── environment.txt
```

`raw/state_contract_exclusive.json` 是当前 contract evaluator 的原始输出；CSV 是只读 adapter 生成的论文接口。不得为了迁就此 schema 修改 checkpoint。

## 3. Artifact registry 与来源脚本

### 3.1 每个 artifact 的必填字段

| 字段 | 含义 |
|---|---|
| `artifact_id` | 稳定唯一 ID |
| `relative_path` | 相对 final result package 的路径 |
| `sha256` | 文件哈希 |
| `created_utc` | 生成时间 |
| `source_script_path` | 运行脚本或 adapter 路径 |
| `source_script_sha256` | 该脚本内容哈希 |
| `source_repo_commit` | 只读代码版本 |
| `command` | 完整命令，敏感路径可在匿名副本中规范化 |
| `input_artifact_ids` | 所有输入 checkpoint/manifest/JSON |
| `status` | `COMPLETE` 或 `FAIL_CLOSED` |

多脚本流水线用 `source_steps[]` 按执行顺序登记，禁止只记录最后一个 adapter。

### 3.2 当前已核验的 V2 源文件

当前正式 run1 的只读代码身份为
`52578ca4b1c0b434b10707cf052a623f0c4e4a99`。

| 职责 | 只读源文件 |
|---|---|
| TerraState-V2 模型、共享 T 与 O | `WorldModel2026-planb-v2train/models/terrastate_v2.py` |
| context-only q 与输入抑制 | `WorldModel2026-planb-v2train/models/plan_b_b4.py` |
| q/PVT/Contextformer 包装与输入嵌入 | `WorldModel2026-planb-v2train/models/encoders/pvt_contextformer_q.py`, `WorldModel2026-planb-v2train/models/encoders/contextformer_official.py` |
| 正式训练入口 | `WorldModel2026-planb-v2train/train/train_terrastate_v2.py` |
| V2 目标、调度与共享训练逻辑 | `WorldModel2026-planb-v2train/train/terrastate_v2_common.py` |
| future-state cache 读取与身份校验 | `WorldModel2026-planb-v2train/train/terrastate_future_state_cache.py` |
| future-state cache builder | `WorldModel2026-planb-v2train/scripts/build_future_state_cache.py` |
| GreenEarthNet 协议参考 | `WorldModel2026-planb-v2train/eval/greenearthnet_protocol.py` |
| Q1–Q4 V2 exporter/evaluator/adapter | `TBD`：commit `52578ca` 尚无可直接满足本 schema 的 paper-ready V2 结果链 |

最终结果包必须登记实际生成结果的 V2 exporter、evaluator、adapter 及其
`source_repo_commit`；如果它们在后续提交中加入，不能沿用 run1 commit
代替真实来源。上述内部文件名只进入 provenance，不进入投稿正文。

### 3.3 当前执行链缺口（必须 fail closed）

- commit `52578ca` 中的 Q1 assembler 仍以旧方法 ID 作为核心行，不能证明 `TerraState + matched_b4` 已齐全；
- 同一 commit 中的旧预测导出器不能严格加载 TerraState-V2；
- 当前尚无把 raw contract JSON 转成本文五个 CSV、同时执行跨文件 identity/finite checks 的正式 adapter；
- raw evaluator 使用宽松载入并包含若干旧说明，不能仅凭其综合 `verdict` 判定论文 PASS。

因此，上表脚本只是**已核验的输入来源**，不是“paper-ready”证明。正式接入必须先具备并哈希：

1. exclusive checkpoint 专用导出器；
2. 只接受最终 V2 serialized arch/route、`driver_protocol=full24`、固定非学习
   `alpha=1`、三项目标合同且关键 missing/unexpected keys 为空的载入审计；
3. 生成本规范 CSV 的严格 adapter；
4. 要求 TerraState 与 Matched B4 两行同时存在的 Table-1 readiness gate；
5. 校验 `driver_protocol=full24`、三项唯一训练目标以及 future-target cache provenance 的 V2 合同门。

## 4. `manifest.json`

### 4.1 必填身份

| 字段 | 约束 |
|---|---|
| `model_id` | 固定 `TerraState` |
| `arch` | 必须与最终 V2 serialized config 和 checkpoint 一致；不得沿用聊天代号 |
| `inference_contract_id` | 固定 `history_q__full24_static_h_T__context_prior_plus_state_v2` |
| `driver_protocol` | 固定 `full24` |
| `driver_fields` | 固定 8 变量 × mean/min/max 的有序 24 通道及字段 SHA |
| `alpha_value/trainable` | 固定 `1.0/false` |
| `checkpoint_sha256` | Q1–Q4 完全相同 |
| `serialized_config_sha256` | 包含 state dims、freeze schedule、full24/static/h 与三项目标 |
| `student_init_sha256` | 与 checkpoint 元数据一致 |
| `kd_teacher_sha256` | 单一 KD provenance；教师不得出现在推理 state dict |
| `future_target_q_projector_sha256` | 训练开始时冻结副本 |
| `future_target_cache_manifest_sha256` | h=20、future-weather-zero、mask/path/target SHA |
| `training_objective_id` | 固定 `gt_1__kd_0p5__future_state_scheduled` |
| `nonzero_objectives` | 恰为 `GT`, `KD`, `future_state` |
| `lambda_state_schedule` | 恰为 0→.02 / .02 / .01 的 20%/80% 分段 |
| `selected_seed` | 与 checkpoint 元数据一致 |
| `selection_record_sha256` | validation-only 选择记录 |

### 4.2 协议身份

| 字段 | 约束 |
|---|---|
| `train_manifest_sha256` | 训练数据冻结身份 |
| `validation_manifest_sha256` | 验证数据冻结身份 |
| `oodt_manifest_sha256` | 一次性测试身份 |
| `mask_protocol_id` | Q1–Q4 同一有效像素定义 |
| `aggregation_protocol_id` | Q1–Q4 同一聚合单位 |
| `scorer_sha256` | Q1–Q4 同一评分代码 |
| `donor_manifest_sha256` | Q3 必需 |
| `weather_normalizer_sha256` | Q3 必需 |
| `q3_threshold_config_sha256` | 正式 Q3 必需 |
| `guard_config_sha256` | Q4 必需 |
| `q4_evaluation_partitions_sha256` | 可选 Q4 必需；不得出现 training composition partitions |
| `evaluator_commit` | 正式 evaluator 的 commit/archive hash |

### 4.3 一次性测试锁

```json
{
  "selection_uses_oodt": false,
  "performance_thresholds_use_oodt": false,
  "donor_rule_uses_oodt": false,
  "donor_assignment_uses_oodt_input_covariates": true,
  "donor_construction_uses_oodt_scores": false,
  "donor_construction_uses_oodt_targets_or_errors": false,
  "donor_floor_source": "per-track input-weather divergence quantile under a validation-frozen quantile level",
  "qualitative_selection_uses_oodt_errors": false,
  "oodt_run_count": 1,
  "checkpoint_frozen_before_oodt": true,
  "data_manifest_frozen_before_oodt": true,
  "donor_manifest_frozen_before_model_scoring": true
}
```

这是一项显式的 transductive control construction：正式实现当前会读取待评测
minicube 的**已声明模型输入**（未来天气、时间、地理）来计算同轨 divergence
floor 和确定配对。它不读取 NDVI target、预测或误差，也不能改变 checkpoint、
判定阈值或结果措辞。若作者决定不接受这种输入侧 transduction，则必须先修改
评测实现为 validation-calibrated absolute floor；在两者之一冻结前，Q3 保持
`TBD`。

## 5. 表 1：Q1 公共预测能力

### 5.1 `q1_forecast.csv`

| 字段 | 表格位置 | 规则 |
|---|---|---|
| `method_id` | Method | 稳定 ID |
| `display_name` | Method | 论文显示名 |
| `source_type` | Source | 固定 `local_exact` |
| `protocol_id` | Local panel | 两行必须完全相同 |
| `n_minicubes` | caption/result | 统计单位是 minicube |
| `r2` | \(R^2\) | 全精度值保留于 CSV |
| `rmse` | RMSE | 同一 mask/aggregation |
| `nse` | NSE | 同上 |
| `abs_bias` | \(|Bias|\) | 同上 |
| `rmse25` | RMSE25 | 同上 |
| `outperformance` | Outperf. | 同上 |
| `checkpoint_sha256` | provenance | TerraState 行等于全局身份 |

表 1 面板规则：

- Published Panel A 已在正文中逐项引用
  \citet{benson2024multimodal} 的 Table 2 数值，标记 `Reported`；它不从最终
  本地结果包回填；
- Local Panel B 恰好只接受 `method_id ∈ {matched_b4, TerraState}`，且两行
  共享 manifest/scorer/mask/aggregation；
- 不要求本地复现 ConvLSTM、PredRNN、SimVP、Earthformer 或 Contextformer；
- 不加粗跨协议“最佳”，不支持 published-vs-local paired superiority；
- TerraState 的表 1 行必须与 Q2–Q3 及可选 Q4 的 checkpoint 相同。

### 5.2 `q1_paired.csv`

TerraState 相对 Matched B4 至少包含：

| 字段 | 用途 |
|---|---|
| `metric` | 主/辅指标名 |
| `delta_definition` | 明确方向，例如 `TerraState - matched` |
| `mean_delta` | 结果句 |
| `ci_low`, `ci_high` | paired CI |
| `wins`, `ties`, `losses` | 结果句 |
| `n_pairs` | 完整性 |
| `bootstrap_unit` | 必须是 minicube |
| `bootstrap_repetitions`, `bootstrap_seed` | provenance |
| `noninferiority_margin` | 没有冻结则为 null |

### 5.3 Q1 三档结果句

**PASS**

> On [N] test minicubes, TerraState obtains [METRICS] and improves over Matched B4 by [DELTA, CI] under the identical local protocol. The same checkpoint is used in Q2–Q3 and optional Q4.

**PARTIAL**

> TerraState obtains [METRICS]. Its paired difference from Matched B4 is [DELTA, CI]. [It meets the validation-frozen non-inferiority margin / No non-inferiority claim is made because no margin was frozen.] The same checkpoint is used below.

**FAIL**

> TerraState obtains [METRICS] and trails Matched B4 by [DELTA, CI]. We therefore treat the state analyses below as mechanism diagnostics rather than evidence of a competitive forecasting method.

## 6. 表 2：Q2 load-bearing

### 6.1 `q2_load_bearing.csv`

固定三行：

```text
full
closure_cut
transition_identity
```

| 字段 | 表 2 单元/结果句 | 当前原始 JSON |
|---|---|---|
| `r2`, `rmse` | 绝对指标 | `Q2_load_bearing.full/alpha0/T_identity.*` |
| `delta_r2_vs_full` | \(\Delta R^2\) | full 与 arm 计算 |
| `delta_rmse_vs_full` | \(\Delta RMSE\) | full 与 arm 计算 |
| `paired_metric_delta_mean` | 发现句 | `closure_cut_alpha0.paired` / `transition_identity.paired` |
| `paired_ci_low/high` | 发现句 | 对应 `bootstrap95` |
| `output_abs_delta` | Output \(\Delta\) | arm 输出与 full 的同样本绝对变化 |
| `state_abs_delta` | State \(\Delta\) | closure 为 `NA`；T→I 必填 |
| `context_prior_r2/rmse` | exact-closure identity audit | `alpha0.*` |
| `alpha0_pred_equals_context_prior` | invariant | `invariants.*` |
| `T_identity_is_state_identity` | invariant | `invariants.*` |

当前 raw evaluator 不直接给出论文表所需的 `output_abs_delta` 与
`state_abs_delta`，正式 adapter 必须从同样本预测/状态数组计算并登记来源。
closure cut 精确等于 context-only prior，因此所谓
`gain_removed_fraction=(full-closure)/(full-prior)` 在代数上恒为 1，只能作为
identity audit，不能作为经验发现或结果句。Q2 报告绝对的 paired
full-versus-prior 效应；Q1 Matched B4 不是这个 prior。

### 6.2 Q2 判定优先级

1. closure cut 是 load-bearing 主证据；
2. \(T\rightarrow I\) 是辅助机制证据，并在正文声明 OOD-state 混杂；
3. evaluator 内部 `dr2_floor` 是项目冻结规则，不表述成领域通用阈值；
4. Q2 FAIL 时，最终整体 predictive-state 结论必须降级，Q3/Q4 不能覆盖。

### 6.3 Q2 三档结果句

**PASS**

> The exact closure cut reduces [PRIMARY METRIC] by [DELTA, CI] relative to the full checkpoint; \(T\!\rightarrow I\) also changes the endpoint by [VALUE, CI]. This supports a load-bearing state-mediated contribution.

**PARTIAL**

> The closure cut changes [PRIMARY METRIC] by [DELTA, CI], whereas \(T\!\rightarrow I\) [does/does not] show a consistent additional effect. We therefore support only [the state-carried increment / no transition-local claim].

**FAIL**

> The closure cut does not remove a stable forecasting contribution ([DELTA, CI]). TerraState therefore does not support the forecast-bearing-state subclaim on this checkpoint.

## 7. 表 2：Q3 driver sensitivity

### 7.1 `q3_driver.csv`

固定三行：

```text
matched
normalized_mean
season_geo_donor
```

| 字段 | 表 2/结果句 | 当前原始 JSON |
|---|---|---|
| `r2`, `rmse` | 绝对指标 | `Q3_driver.matched/normalized_zero_reference/donor.*` |
| `delta_r2_vs_matched` | \(\Delta R^2\) | arm 与 matched |
| `delta_rmse_vs_matched` | \(\Delta RMSE\) | arm 与 matched |
| `matched_minus_arm_mean` | 发现句 | `matched_minus_arm_*` |
| `paired_ci_low/high` | 发现句 | `matched_minus_arm_percube_bootstrap95` |
| `state_abs_delta` | State \(\Delta\) | `state_abs_delta` |
| `output_abs_delta` | Output \(\Delta\) | `output_abs_delta` |
| `per_horizon_state/output_delta` | 支持材料 | `per_h` |
| `context_prior_invariant` | fail-closed | `verdict_conditions.context_prior_invariant_across_arms` |
| `practical_floor_pass` | 正式判定 | zero/donor floor |
| `donor_schema` | provenance | donor block |

normalized mean 的含义固定为：

> 在全局按变量标准化后的天气空间中置零，即各变量训练集全局均值；不是逐日/逐地气候态。

donor 必须由冻结 manifest 证明地理、季节/DOY、差异量级与复用约束。规则与
quantile level 在 validation 阶段冻结；当前实现的绝对 divergence floor 与具体
assignment 由该评测轨的输入侧天气/地理/时间确定，并必须在模型评分前哈希。
不得使用 target、prediction 或 error。正文不使用简单 batch shuffle。

### 7.2 Q3 三档结果句

**PASS**

> Matched weather outperforms normalized-mean and season/geography-matched donor forcing by [DELTA/CI] and [DELTA/CI], respectively, while the context-only prior remains invariant; transitioned-state and output changes are [SUMMARY].

**PARTIAL**

> Matched weather differs from [CONTROL] but not [CONTROL] under the frozen practical-effect rule. We therefore report conditional sensitivity to [SUPPORTED CONTROL] without claiming robust driver sensitivity.

**FAIL**

> Matched weather does not outperform the frozen controls, or the prior-invariance check fails. This checkpoint does not support the driver-sensitive-state subclaim.

## 8. 可选表 3：训练后 Q4 composition 与 anti-collapse

### 8.1 冻结 evaluation partitions

```json
{
  "q4_evaluation": [[3, 7], [6, 4], [4, 11], [8, 12], [2, 18]],
  "used_for_training": false,
  "used_for_model_selection": false
}
```

Q4 只在唯一 checkpoint 选择并冻结后运行；分段必须与冻结 evaluator manifest
完全一致，不要求也不得声明 checkpoint 中存在 training composition partitions。

### 8.2 `q4_composition.csv`

每个 partition 一行：

| 字段 | 表 3 列 | 当前原始 JSON |
|---|---|---|
| `h1`, `h2`, `h_total` | Partition | adapter 从 Q4 evaluation block 读取 |
| `endpoint_direct_mse` | \(E^{dir}\) | `endpoint_direct_mse` |
| `endpoint_composed_mse` | \(E^{cmp}\) | `endpoint_composed_mse` |
| `abs_endpoint_guard_pass` | Joint guard 的第一部分 | `abs_endpoint_guard_pass` |
| `noninferiority_rel_pass` | Joint guard 的第二部分 | `noninferiority_rel_pass` |
| `joint_guard_pass` | Joint guard | adapter 必须取二者 AND |
| `state_path_gap` | \(\delta_z\) | `state_path_gap.mean`；mean absolute token gap |
| `output_path_gap` | \(\delta_y\) | `output_path_gap.mean`；valid-pixel MSE |
| `broken_control_gap` | \(\delta_y^{broken}\) | `broken_control_gap` |
| `a_comp_mean` | \(A_{\rm comp}\) | `broken_minus_real_advantage_A_comp.mean` |
| `a_comp_ci_low/high` | 结果句 | 对应 `bootstrap95` |
| `real_over_broken_ratio` | 辅助 | `composition_ratio_real_over_broken_AUX` |

关键约束：

- `joint_guard_pass = abs_endpoint_guard_pass AND noninferiority_rel_pass`；
- 不得只复制 evaluator 的综合 `verdict`；
- real leg-2 使用半开窗口 `u[:, h1:h1+h2]`；broken leg-2 用等长前缀
  `u[:, :h2]` 替换；leg-1、direct、geo、elapsed-time \(h_2\)、prior、closure
  与 target 均不变；
- `q4_broken_path_manifest.json` 必须记录上述 slice 规则、实现 hash 与每个
  partition，不能只依赖自然语言 caption；
- 正面 path gap 解释只针对 `joint_guard_pass=true`；
- Q4 pooled \(A_{\rm comp}\) 使用 minicube-clustered bootstrap；
- Q2 未通过时，Q4 不能获得整体 predictive-state 正面结论。

### 8.3 `q4_state_summary.csv`

固定四行 `horizon ∈ {1,5,10,20}`，与当前 evaluator 完全一致：

| 字段 | 表 3/结果句 | 当前原始 JSON |
|---|---|---|
| `horizon` | 关联行/补充材料 | `Q4_composition.state.h=*` |
| `movement_mean_abs` | M | `movement` |
| `state_std` | S 原值 | `std` |
| `state_std_ratio_to_context` | S retention | `std_ratio` |
| `effective_rank` | R 原值 | `eff_rank` |
| `effective_rank_ratio_to_context` | R retention | `eff_rank_ratio` |
| `across_cube_movement_var` | 退化审计 | 同名字段 |
| `context_state_std` | denominator | `state_zt.std` |
| `context_effective_rank` | denominator | `state_zt.eff_rank` |
| `degeneracy_check` | 表 3 Panel B 最后一列 | adapter 对 validation-frozen movement/std/rank 规则的联合判定 |

计算轴固定为：每个 minicube 内跨 patch tokens 计算 channel std 与中心化
covariance/effective rank；movement 对 patch 与 channel 取 mean absolute；最后跨
minicube 平均。不得把所有 cube/token 无声明地池化成另一种统计。

### 8.4 当前 evaluator 的已知接入注意

1. 原始 JSON 允许序列化 `NaN`；adapter 必须拒绝所有必填非有限值；
2. 原始综合 Q4 verdict 未明确 AND 每行 absolute guard；论文 adapter 使用更严格的 `joint_guard_pass`；
3. 原始 `heldout_note_h20` 与旧 training-composition 逻辑均已过时；禁止把这些 note 接入论文；
4. 当前 evaluator 输出 raw state path gap，而不是旧稿中的 cross-sample shuffled-state normalization；表 3 已按真实字段设计；
5. raw evaluator 的 retention floor 当前硬编码且不包含 movement floor；正式
   `q4_guard_and_retention.json` 必须在 OOD-t 评分前冻结 absolute/NI、
   \(A_{\rm comp}\) practical floor、movement 与 std/rank retention 规则及计算轴；
6. 任何阈值都必须有 validation-frozen config hash，不表述成通用科学标准；
7. 在严格 adapter 与上述 config 尚不存在时，Q4 保持 `TBD`，不得复制 raw verdict。

### 8.5 Q4 三档结果句

**PASS**

> All predeclared Q4 paths satisfy the absolute and non-inferiority endpoint guards. The pooled \(A_{\rm comp}\) is [VALUE, CI], and state movement/std/effective-rank retention exclude the declared identity and collapse controls.

**PARTIAL**

> [N/TOTAL] Q4 partitions satisfy both endpoint guards, and [SUBSET] also outperform the broken-path control. We therefore report partition-limited consistency rather than general path reuse.

**FAIL**

> The Q4 paths fail [ENDPOINT / BROKEN-CONTROL / STATE-RETENTION] conditions. This checkpoint does not support the composition-consistent, non-degenerate-state subclaim.

## 9. `ablations.csv` 与 Matched B4 公平性

### 9.1 消融接口

正文承诺的候选行只在最终配置可执行且真实运行时出现：

```text
projector
shared_transition
driver_encoder
geography
elapsed_time
kd_objective
future_state_objective
```

| 字段 | 规则 |
|---|---|
| `ablation_id`, `display_name` | 稳定 ID 与投稿名 |
| `ablation_type` | `component` / `objective` / `inference_cut` |
| `reference_model_id` | 固定 `TerraState` |
| `checkpoint_sha256` | 另训消融必须记录自身 checkpoint；同 checkpoint cut 则等于全局 |
| `exact_change` | 唯一改变的模块/非零权重 |
| `unchanged_fields_sha256` | 数据、初始化、budget、selection、scorer 的联合 hash |
| `seed_set`, `training_updates` | 公平性 |
| `r2`, `rmse`, `paired_delta`, `ci_low/high` | 真实结果 |
| `source_artifact_ids` | 预测、评分、config、checkpoint |
| `status` | `COMPLETE` / `NOT_RUN` / `FAIL_CLOSED` |

唯一 objective set 固定为 GT + 0.5 KD + scheduled future-state；目标消融只允许
在保留 GT 时分别移除 KD 或 future-state。commit `52578ca` 的正式 V2 训练入口
并未提供或核验上述全部重训练消融开关，因此本 schema 只预留写作接口，不把
文字承诺伪装成已实现实验；没有严格配置与运行时，该行标 `NOT_RUN` 并从
Results 删除。Q4
composition 与 non-collapse 量不是训练目标，不能列为 objective ablation。

### 9.2 `matched_b4_fairness.json`

必须逐项记录 TerraState 与 Matched B4 是否共享：

- context-backbone 初始化与数据 manifests；
- 单一 KD teacher access/distillation policy；TerraState 的 future-target
  supervision 作为明确方法差异单独登记；
- training updates、batching、validation cadence 与 early stopping；
- optimizer/LR search budget、seed set 与选择规则；
- target、mask、scorer、aggregation；
- 参数量、FLOPs/推理成本的计算脚本。

任何 `false` 或 `unknown` 都必须进入正文限制，不能仍称 `matched-budget`。

## 10. 正文发现句的字段依赖

| 正文槽 | 必需字段 |
|---|---|
| Q1 `[N]` | `q1_forecast.n_minicubes` |
| Q1 `[METRICS]` | TerraState row exact local metrics |
| Q1 `[DELTA, CI]` | `q1_paired.mean_delta/ci_low/ci_high` |
| Q1 `[W/T/L]` | `q1_paired.wins/ties/losses` |
| Q2 `[ABSOLUTE DELTA, CI]` | closure-cut paired fields |
| Q2 T→I `[VALUE, CI]` | transition identity output/metric delta |
| Q3 two `[DELTA, CI]` | normalized mean 与 donor 两臂 |
| Q3 `[SUMMARY]` | two controls 的 state/output changes |
| Q4 `[NUMBER]/[TOTAL]` | predeclared evaluation `joint_guard_pass` |
| Q4 pooled `[VALUE, CI]` | cube-clustered Q4 \(A_{\rm comp}\) |
| Q4 ratio count | `real_over_broken_ratio < 1` |
| Q4 anti-collapse phrase | movement/std-ratio/effective-rank-ratio + frozen rules |

缺一个字段就删除相应从句，不能凭文字补全。

## 11. 自动与人工接入检查表

- [ ] `model_id=TerraState` 且只有一个 checkpoint；
- [ ] `driver_protocol=full24`，static/horizon 字段与顺序哈希一致；
- [ ] 非零目标恰为 GT + 0.5 KD + scheduled future-state；
- [ ] future-target q/projector/cache 的 h=20、weather-zero、mask/path/SHA 合同完整；
- [ ] Q1–Q4 identity/provenance 完全一致；
- [ ] final checkpoint 由 validation-only 记录选择；
- [ ] OOD-t 运行次数与 test lock 完整；
- [ ] 表 1 Published 数值与 Benson et al. Table 2 一致，Local 仅 Matched B4 + TerraState，且没有跨面板排名；
- [ ] Q1 paired unit 是 minicube；
- [ ] Q2 closure cut 精确等于 context-only prior；
- [ ] Q2 只报告 paired full-versus-prior 绝对效应，不把恒等 gain fraction 当发现；
- [ ] Q3 只改变 T weather，prior invariant 通过；
- [ ] Q3 donor/normalizer/floor 均有冻结 hash；
- [ ] 可选 Q4 evaluation partitions 与 evaluator manifest 一致，且未进入训练或选模；
- [ ] Q4 direct/composed endpoints 分别报告；
- [ ] Q4 joint guard 显式包含 absolute AND non-inferiority；
- [ ] Q4 real/broken control、movement/std/rank 全部存在；
- [ ] strict exclusive exporter、schema adapter 与 Table-1 readiness gate 均通过；
- [ ] Matched B4 fairness 字段完整，所有差异已披露；
- [ ] 正文实际保留的 ablation 行均有可执行配置与真实 artifact；
- [ ] 每张表恰好选择 PASS/PARTIAL/FAIL 一种结果句；
- [ ] 所有 `TBD` 只由机器结果字段替换；
- [ ] Results 与 Conclusion 强度经过最终人工复审；
- [ ] 冻结标题与摘要逐字未改。
