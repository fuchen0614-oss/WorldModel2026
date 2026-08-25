# TerraState 当前状态

> 本文件由 `terrastate/ops/candidate_c_nightly/20260820T155316Z/regen_status.py` 从 E0 v3 工件机械生成，零手打数值。生成时间 2026-08-20T21:07:15.740677+00:00。

## 1. E0 v3 封账状态

| 项 | 值 |
|---|---|
| 验收结论 | **ACCEPTED** |
| gate 数 | 6 |
| check 数 | 732 |
| 失败数 | 0 |
| fail-closed | 是 |
| 历史复现 | 57/57 （bit-exact 57） |
| closeout 审计 | ACCEPTED（732 checks / 0 failed） |
| 独立完整性审计 | PASS（18 checks / 0 不一致） |
| 复现范围 | 仅 11,904 侧复现历史参考；14,880 侧无历史参考可比 |

## 2. 固定检查点

| 键 | logical_id | step | file SHA-256 |
|---|---|---|---|
| 11904 | `terrastate/v2/legacy-boundary11904@v1` | 11904 | `644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd` |
| 14880 | `terrastate/v2/verified-resume14880@v1` | 14880 | `a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f` |

## 3. 头条指标（11,904 → 14,880）

| selector | 11,904 | 14,880 | 来源路径 |
|---|---|---|---|
| `Q1.val.overall.R2` | 0.49732196418835595 | 0.49709355615470024 | `Q1_forecast.full.R2` |
| `Q1.val.overall.rmse` | 0.1572881669325748 | 0.15733399506089182 | `Q1_forecast.full.rmse` |
| `Q1.val.overall.nse` | -0.15475482758989223 | -0.1559974291116175 | `Q1_forecast.full.nse` |
| `Q1.val.overall.biasabs` | 0.0997195960230769 | 0.09972860331501403 | `Q1_forecast.full.biasabs` |
| `Q1.oodt.overall.R2` | 0.5693493611664086 | 0.5692781483135535 | `Q1_forecast.full.R2` |
| `Q1.oodt.overall.rmse` | 0.1505941190915099 | 0.15062711918297353 | `Q1_forecast.full.rmse` |
| `Q1.oodt.overall.nse` | -0.09865601980139305 | -0.09975306029983821 | `Q1_forecast.full.nse` |
| `Q1.oodt.overall.biasabs` | 0.10082906836242285 | 0.10080980043117554 | `Q1_forecast.full.biasabs` |
| `Q2.oodt.arms.full.R2` | 0.5693493611664086 | 0.5692781483135535 | `Q2_load_bearing.full.R2` |
| `Q2.oodt.arms.alpha0.R2` | 0.5493773508945857 | 0.5489462969661727 | `Q2_load_bearing.alpha0.R2` |
| `Q2.oodt.arms.T_identity.R2` | 0.5476642387248465 | 0.5473352458096724 | `Q2_load_bearing.T_identity.R2` |
| `Q2.oodt.official_deltas.official_R2_full_minus_alpha0` | 0.019972010271822827 | 0.020331851347380803 | `Q2_load_bearing.official_R2_full_minus_alpha0` |
| `Q2.oodt.official_deltas.official_R2_full_minus_Tid` | 0.021685122441562066 | 0.02194290250388109 | `Q2_load_bearing.official_R2_full_minus_Tid` |
| `Q2.oodt.bootstrap_families.closure_cut_alpha0.bootstrap95.mean` | 0.021997768589881533 | 0.02224764814218487 | `Q2_load_bearing.closure_cut_alpha0.bootstrap95.mean` |
| `Q2.oodt.bootstrap_families.closure_cut_alpha0.bootstrap95.ci_low` | 0.014219898623411737 | 0.014365401181430417 | `Q2_load_bearing.closure_cut_alpha0.bootstrap95.ci_low` |
| `Q2.oodt.bootstrap_families.closure_cut_alpha0.bootstrap95.ci_high` | 0.03017606928017251 | 0.03049188689730075 | `Q2_load_bearing.closure_cut_alpha0.bootstrap95.ci_high` |
| `Q2.oodt.gates.verdict` | LOAD_BEARING | LOAD_BEARING | `Q2_load_bearing.verdict` |

### Q3（极端状态审计，机械筛选）

| selector | 11,904 | 14,880 |
|---|---|---|
| `Q3.counts.n_control_unique` | 45 | 45 |
| `Q3.counts.n_geo_clusters` | 31 | 31 |
| `Q3.counts.n_pairs` | 84 | 84 |
| `Q3.counts.n_reused_control_clusters` | 45 | 45 |
| `Q3.counts.protocol_n_pairs` | 84 | 84 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.delta_loss_mean` | 0.002565468112672014 | 0.0025695093652410876 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.geo_cluster_bootstrap.ci_high` | 0.003987491067301663 | 0.003986807599386983 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.geo_cluster_bootstrap.ci_low` | 0.0011187122087714869 | 0.0011268149171079383 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.geo_cluster_bootstrap.mean` | 0.002565468112672014 | 0.0025695093652410876 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.geo_cluster_bootstrap.n` | 84 | 84 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.geo_cluster_bootstrap.n_clusters` | 31 | 31 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.geo_cluster_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.paired_bootstrap.ci_high` | 0.003982677219236003 | 0.003987763251158564 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.paired_bootstrap.ci_low` | 0.0011953603675855058 | 0.0011951253688104251 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.paired_bootstrap.frac_pos` | 0.6666666666666666 | 0.6547619047619048 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.paired_bootstrap.mean` | 0.002565468112672014 | 0.0025695093652410876 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.paired_bootstrap.n` | 84 | 84 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.paired_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.reused_control_cluster_bootstrap.ci_high` | 0.004140386835031964 | 0.004141273665947641 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.reused_control_cluster_bootstrap.ci_low` | 0.0010028157455885883 | 0.0009959744667960482 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.reused_control_cluster_bootstrap.mean` | 0.002565468112672014 | 0.0025695093652410876 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.reused_control_cluster_bootstrap.n` | 84 | 84 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.reused_control_cluster_bootstrap.n_clusters` | 45 | 45 |
| `Q3.endpoint_fidelity.extreme_actual_vs_donor.reused_control_cluster_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.delta_loss_mean` | 0.011261332329706334 | 0.011389337176556833 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.geo_cluster_bootstrap.ci_high` | 0.0170799320898515 | 0.017265939159405365 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.geo_cluster_bootstrap.ci_low` | 0.005465624536528642 | 0.005548044197817492 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.geo_cluster_bootstrap.mean` | 0.011261332329706334 | 0.011389337176556833 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.geo_cluster_bootstrap.n` | 84 | 84 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.geo_cluster_bootstrap.n_clusters` | 31 | 31 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.geo_cluster_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.paired_bootstrap.ci_high` | 0.015303447515283812 | 0.015450009475136452 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.paired_bootstrap.ci_low` | 0.007529678631856639 | 0.0076451200372719625 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.paired_bootstrap.frac_pos` | 0.8214285714285714 | 0.8095238095238095 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.paired_bootstrap.mean` | 0.011261332329706334 | 0.011389337176556833 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.paired_bootstrap.n` | 84 | 84 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.paired_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.reused_control_cluster_bootstrap.ci_high` | 0.017714386102466874 | 0.017873479602548904 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.reused_control_cluster_bootstrap.ci_low` | 0.005212267390684386 | 0.005319221199795531 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.reused_control_cluster_bootstrap.mean` | 0.011261332329706334 | 0.011389337176556833 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.reused_control_cluster_bootstrap.n` | 84 | 84 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.reused_control_cluster_bootstrap.n_clusters` | 45 | 45 |
| `Q3.endpoint_fidelity.extreme_actual_vs_mean.reused_control_cluster_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.hotdry_interaction.dloss_donor.geo_cluster_bootstrap.ci_high` | 0.003199765110504583 | 0.003174650861834188 |
| `Q3.hotdry_interaction.dloss_donor.geo_cluster_bootstrap.ci_low` | -0.0021624635347345066 | -0.002173025324078599 |
| `Q3.hotdry_interaction.dloss_donor.geo_cluster_bootstrap.mean` | 0.0004360788783136134 | 0.0004270670927196209 |
| `Q3.hotdry_interaction.dloss_donor.geo_cluster_bootstrap.significant_gt0` | 否 | 否 |
| `Q3.hotdry_interaction.dloss_donor.paired_bootstrap.ci_high` | 0.0026285071957231373 | 0.0026113461588725575 |
| `Q3.hotdry_interaction.dloss_donor.paired_bootstrap.ci_low` | -0.0017186705140505051 | -0.0017291863943336508 |
| `Q3.hotdry_interaction.dloss_donor.paired_bootstrap.mean` | 0.0004360788783136134 | 0.0004270670927196209 |
| `Q3.hotdry_interaction.dloss_donor.paired_bootstrap.significant_gt0` | 否 | 否 |
| `Q3.hotdry_interaction.dloss_donor.reused_control_cluster_bootstrap.ci_high` | 0.003306087406565355 | 0.00328862719393429 |
| `Q3.hotdry_interaction.dloss_donor.reused_control_cluster_bootstrap.ci_low` | -0.0025273992025991085 | -0.0025244989895738938 |
| `Q3.hotdry_interaction.dloss_donor.reused_control_cluster_bootstrap.mean` | 0.0004360788783136134 | 0.0004270670927196209 |
| `Q3.hotdry_interaction.dloss_donor.reused_control_cluster_bootstrap.significant_gt0` | 否 | 否 |
| `Q3.hotdry_interaction.dloss_mean.geo_cluster_bootstrap.ci_high` | 0.012358345135340317 | 0.012447570046917296 |
| `Q3.hotdry_interaction.dloss_mean.geo_cluster_bootstrap.ci_low` | 0.0031729625584255277 | 0.003225588979210075 |
| `Q3.hotdry_interaction.dloss_mean.geo_cluster_bootstrap.mean` | 0.00802125371618396 | 0.008093610512635982 |
| `Q3.hotdry_interaction.dloss_mean.geo_cluster_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.hotdry_interaction.dloss_mean.paired_bootstrap.ci_high` | 0.011935417796658361 | 0.012020002959754838 |
| `Q3.hotdry_interaction.dloss_mean.paired_bootstrap.ci_low` | 0.004334346223168679 | 0.00440371591376745 |
| `Q3.hotdry_interaction.dloss_mean.paired_bootstrap.mean` | 0.00802125371618396 | 0.008093610512635982 |
| `Q3.hotdry_interaction.dloss_mean.paired_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.hotdry_interaction.dloss_mean.reused_control_cluster_bootstrap.ci_high` | 0.01382225962412352 | 0.013931050306537554 |
| `Q3.hotdry_interaction.dloss_mean.reused_control_cluster_bootstrap.ci_low` | 0.0026928806540965594 | 0.0027428779675134816 |
| `Q3.hotdry_interaction.dloss_mean.reused_control_cluster_bootstrap.mean` | 0.00802125371618396 | 0.008093610512635982 |
| `Q3.hotdry_interaction.dloss_mean.reused_control_cluster_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.hotdry_interaction.resp_donor.geo_cluster_bootstrap.ci_high` | 0.0032603159652614664 | 0.003244291723021102 |
| `Q3.hotdry_interaction.resp_donor.geo_cluster_bootstrap.ci_low` | -0.0010011238753920052 | -0.001020716008749687 |
| `Q3.hotdry_interaction.resp_donor.geo_cluster_bootstrap.mean` | 0.0011792403945167149 | 0.0011653741045544546 |
| `Q3.hotdry_interaction.resp_donor.geo_cluster_bootstrap.significant_gt0` | 否 | 否 |
| `Q3.hotdry_interaction.resp_donor.paired_bootstrap.ci_high` | 0.0033779126713939355 | 0.003378164990378233 |
| `Q3.hotdry_interaction.resp_donor.paired_bootstrap.ci_low` | -0.0009148788772844931 | -0.000923393915789867 |
| `Q3.hotdry_interaction.resp_donor.paired_bootstrap.mean` | 0.0011792403945167149 | 0.0011653741045544546 |
| `Q3.hotdry_interaction.resp_donor.paired_bootstrap.significant_gt0` | 否 | 否 |
| `Q3.hotdry_interaction.resp_donor.reused_control_cluster_bootstrap.ci_high` | 0.003562037448020082 | 0.003556125734819483 |
| `Q3.hotdry_interaction.resp_donor.reused_control_cluster_bootstrap.ci_low` | -0.00137876071040453 | -0.001393701037500549 |
| `Q3.hotdry_interaction.resp_donor.reused_control_cluster_bootstrap.mean` | 0.0011792403945167149 | 0.0011653741045544546 |
| `Q3.hotdry_interaction.resp_donor.reused_control_cluster_bootstrap.significant_gt0` | 否 | 否 |
| `Q3.hotdry_interaction.resp_mean.geo_cluster_bootstrap.ci_high` | 0.029642608798552995 | 0.029484414692757782 |
| `Q3.hotdry_interaction.resp_mean.geo_cluster_bootstrap.ci_low` | 0.005525818686391359 | 0.0054002115688343575 |
| `Q3.hotdry_interaction.resp_mean.geo_cluster_bootstrap.mean` | 0.01818380479346074 | 0.01804787790890606 |
| `Q3.hotdry_interaction.resp_mean.geo_cluster_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.hotdry_interaction.resp_mean.paired_bootstrap.ci_high` | 0.02646898071342591 | 0.026368260342306233 |
| `Q3.hotdry_interaction.resp_mean.paired_bootstrap.ci_low` | 0.0099607620984205 | 0.009794352874935915 |
| `Q3.hotdry_interaction.resp_mean.paired_bootstrap.mean` | 0.01818380479346074 | 0.01804787790890606 |
| `Q3.hotdry_interaction.resp_mean.paired_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.hotdry_interaction.resp_mean.reused_control_cluster_bootstrap.ci_high` | 0.029346815281599135 | 0.029195754066882944 |
| `Q3.hotdry_interaction.resp_mean.reused_control_cluster_bootstrap.ci_low` | 0.006873613738220764 | 0.006795395113695041 |
| `Q3.hotdry_interaction.resp_mean.reused_control_cluster_bootstrap.mean` | 0.01818380479346074 | 0.01804787790890606 |
| `Q3.hotdry_interaction.resp_mean.reused_control_cluster_bootstrap.significant_gt0` | 是 | 是 |
| `Q3.strata.hotdry.closure_zero_scale.R2` | 0.575077887189188 | 0.5753749249026148 |
| `Q3.strata.hotdry.closure_zero_scale.rmse` | 0.18439795641134255 | 0.18421010213044875 |
| `Q3.strata.hotdry.full.R2` | 0.6253516462782711 | 0.6268869270900711 |
| `Q3.strata.hotdry.full.rmse` | 0.14915162604727777 | 0.14896837663176288 |
| `Q3.strata.hotdry.t_identity.R2` | 0.57525591605909 | 0.5755082456687665 |
| `Q3.strata.hotdry.t_identity.rmse` | 0.25392880359543024 | 0.25408833731241665 |
| `Q3.strata.hotdry.weather_in_base.R2` | None | None |
| `Q3.strata.hotdry.weather_in_base.rmse` | None | None |
| `Q3.verdicts.endpoint_fidelity_status` | PASS | PASS |
| `Q3.verdicts.hotdry_enhancement_status` | FAIL | FAIL |
| `Q3.verdicts.overall_status` | Q3_RESPONSE_FIDELITY_ONLY | Q3_RESPONSE_FIDELITY_ONLY |

> 收割到的 headline metric leaf 总数：262（全部存入 `state.json.headline_metrics_all`，表内仅展示子集）。

> `|ΔR²| < 0.01` 是**描述性对齐标准**，不是统计显著性检验，也不是成功门或 checkpoint 选择门；它没有被废除。

## 4. 文档一致性

| 文档 | live SHA-256 | sidecar | 匹配 |
|---|---|---|---|
| A03 | `59b5851b7d0ebace2934306bb37128a61353bdaa7d40bf8c6348eb3a66b603d5` | `59b5851b7d0ebace2934306bb37128a61353bdaa7d40bf8c6348eb3a66b603d5` | 是 |
| A01 | `f2a054981157e8f729d2f0655d8cc32e00262cbce0ab6e2c91e3e00c5591182d` | `—` | — |
| A02 | `8502db07e3ffc95ad20502b6d681d61abbec091dab29672e904658d04643a3b5` | `—` | — |

## 5. v3 canonical 工件

| 文件 | 字节 | SHA-256 |
|---|---|---|
| `attempt_manifest_v3.json` | 9675 | `41cee90e3d60dcd110b040eeaa896bc485d90f2cd63eaa7f02039b13b092602a` |
| `closeout_audit_v3.json` | 5058 | `00337d15e846cfdf7aa2ee8c5808bdf9097ae8c44c5bfec9c37d376abec2c008` |
| `e0_acceptance_report_v3.json` | 166619 | `f53232870def9ff219093052fd2bacfd035769443ab399fca49051bbf5363f57` |
| `e0_artifact_index_v3.json` | 42046 | `59365d48c9c2be6c49da872e23c72efa3971a91f04eae9d25fa159e489a69855` |
| `e0_comparison_11904_vs_14880_v3.json` | 240571 | `2e1529ca4e24b3ef8f3498f35f9de2a5912f817aa6ffe0bfc87274df8e2cde4a` |
| `e0_launch_record_v3.json` | 8827 | `9e07243ed156c0850249f0352d97c17fffafb67454ebe2cd4e3a18a0780c222d` |
| `e0_metric_inventory_v3.json` | 82211 | `e1b1c8c902d004267847197ea87970a0e7dd4993908ad01e80f218bed07e5a2e` |
| `e0_provenance_v3.json` | 37491 | `719975c53699fa6a7a513e167e11136e34e58f95c9ad316a6dd7ec3abe18c1c6` |
| `experiment_integrity_audit_v3.json` | 2288 | `b2b64acf20038ba65d9914a46c1c3370e6076687392ca4a478dc1674503386fc` |
| `final_gates_v3.json` | 726 | `a999ea84aa8b79a26bb9f12b9404f57e95f3909f34b96e550b2818efdb64f611` |

## 6. Candidate C 当前阶段

- 工作目录：`terrastate/ops/candidate_c_nightly/20260820T155316Z`
- **当前状态：`BLOCKED_SMOKE_ATTEMPT_BUDGET_EXHAUSTED`**（状态机第 10 次转移，2026-08-20T21:05:11.324882Z）
- 阶段范围：T3 实现 / CPU 测试 / GPU smoke / C1-C0R 预注册队列
- GPU smoke attempt 用量：**2/2**（预算已用尽）
  - `smoke/run_20260820T195259Z`：checkpoint 0 个（目录保留）
  - `smoke/run_20260820T202342Z`：checkpoint 0 个（目录保留）
- 状态原因：mandate 规定 ≤2 次全新 GPU smoke attempt；2/2 已用尽。两次失败均为我的配置缺陷（attempt1: smoke λ_pair=0.5 撞 trainer L280 无条件闸门；attempt2: 冻结配置沿用 trainer argparse 默认 selector 'splits.val_dev.ids'，冻结 manifest 无 splits 顶层键）。两次均被 fail-closed 拦住：0 checkpoint、0 训练 step、GPU 占用合计约 33s、未影响他人。两处根因已在生成器源头修复并在 CPU 上复验全绿。这是显式数值硬门，不自行超出，也不把 smoke 改名为 pilot 绕过（预算洗白）。
- 下一步：需要授权再做 1 次 GPU smoke attempt。授权后可直接执行 launch_gpu_run.py --kind smoke（8 卡，--stop-after-step 32，total_steps 仍为 2976），随后 pilot(~128 updates) → FORMAL_READY → 正式 C1 → 机械完成门 → C0R。
- warm-start 父节点别名：`terrastate/v2/default-training-anchor`
- fork 语义：weights-only Phase-II fork（新 optimizer/scheduler/RNG，phase_step 从 0 开始），不是 exact resume
- 本轮允许臂：C1, C0R
- 本轮禁止臂：C0S, C2, C3, C4, C5
- simulator 状态：`BLOCKED_SIMULATOR_LIBRARY_AND_FORMAL_SCENARIO_MANIFEST`

仓库 HEAD `c9503030e498e8ec86fffe9105998c3a2a540d68`，分支 `main`。
