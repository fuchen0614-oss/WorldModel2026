# VALIDATION_REPORT

本报告只记录**可机械核对的检查**；不做主观质量判断。

| 检查 | 结果 | 细节 |
|---|---|---|
| T4B/iid/full_suffix receiver-equal point estimate reproduces v8 | PASS | got=0.00319203 expected=0.00319203393815653 |
| T4B/ood_t/full_suffix receiver-equal point estimate reproduces v8 | PASS | got=0.00219172 expected=0.0021917210571023612 |
| T4B/ood_s/full_suffix receiver-equal point estimate reproduces v8 | PASS | got=0.00334457 expected=0.003344566880082621 |
| T4B/ood_st/full_suffix receiver-equal point estimate reproduces v8 | PASS | got=0.00155839 expected=0.0015583897001574352 |
| T4B/iid receiver count == v8 n_cubes | PASS | got=2066 expected=2066 |
| T4B/ood_t receiver count == v8 n_cubes | PASS | got=1605 expected=1605 |
| T4B/ood_s receiver count == v8 n_cubes | PASS | got=6965 expected=6965 |
| T4B/ood_st receiver count == v8 n_cubes | PASS | got=5437 expected=5437 |
| T1 summary transcribed without modification | PASS | Table1 generated directly from E1_summary_values.csv (no manual edits) |
| C0R pairing identity (parent sha + raw diff) | PASS | parent_value_sha16=aa98fbd2fa302727 max_abs_diff=0.0 |
| T7 reuse vs re-encode produce identical outputs | PASS | max_abs_diff=0.0 |
| C0R standard-prediction coverage | PASS | 4/4 splits: ['iid_chopped', 'ood-s_chopped_repaired_v2', 'ood-st_chopped', 'ood-t_chopped'] |
| RUN_LEDGER.csv field alignment (csv parse AND naive comma split) | PASS | header=9 fields; field-count set=[9]; raw-comma set=[8] |
| RUN_LEDGER.csv carries no stale/running status | PASS | statuses=['done'] |
| Per-record pairing check (id/season/coords/landcover/n_obs) | PASS | 4/4 splits checked; overall=PASS |
| T4B declares receiver-equal as MAIN and the other two as SENSITIVITY | PASS | roles={'receiver_equal': {'main'}, 'geo_equal': {'sensitivity'}, 'pixel_pooled': {'sensitivity'}} |
| T4B OOD-st endpoint: receiver-equal above 0 while geo-equal CI crosses 0 | PASS | receiver_equal ci_above_zero=True, geo_equal ci_above_zero=False |
| paired bootstrap docstring matches the implemented grouping rule | PASS | docstring documents tile-first + 0.1-degree fallback and the 0.5-degree sensitivity run |
| paired bootstrap reports primary + 0.5-deg sensitivity groupings | PASS | keys=['B', 'contract_note', 'grouping_rule_primary', 'grouping_rule_sensitivity', 'primary_grouping', 'seed', 'sensitivity_grouping_0.5deg', 'statistic'] |
| T7 records each runtime phase separately | PASS | missing=[] |
| T7 verifies ALL four query outputs (adapter vs pure compute) | PASS | 4/4 queries identical; max_abs_diff=0.0 |
| T7 reports no single headline speedup for reuse | PASS | a B-dependent cost model is reported instead of one ratio |
| no external pointer file or temp helper script dependency (active code only) | PASS | leftovers=[] |
| retention record present and deleted prediction dirs absent | PASS | 4 pred/ dirs recorded, all absent=True |

## 复用与重跑说明（本轮增量执行）

整体整理阶段只改动**文字、CSV 字段、展示方案与打包**，未改动统计公式、测量协议或评分输入，因此按“代码与输入未变”的理由复用以下结果，**而不是**沿用旧结论：

**复用（未重跑）**：逐评分记录配对核对、配对空间组 bootstrap、T4B 三口径统计、C1 运行时阶段测量、全部表格数值与图件数据。
**重跑**：`code/gen_reports.py`（报告 / CSV 字段 / 展示方案）、`code/finalize_package.py`（哈希与账本刷新），以及末尾新增的一致性门 `code/verify_consistency.py`。

上述计算脚本在本轮的哈希（用于核对复用依据）：

- `gen_tables.py` = `9d8040757a7e7f17…`；`gen_t5.py` = `d7e2d7c10193c7b3…`；`gen_tables2.py` = `e78d1bde058a491c…`；`gen_figures.py` = `6a9d2dd3192abe06…`；`paired_c0r_c1.py` = `48df05d3d6a4ca99…`；`measure_runtime_c1.py` = `6f3bbd6b7452c911…`；`verify_pairing.py` = `068ab69f69c49593…`

> 旧版的“通过”记录**不**直接充当新版验收：本报告表中的全部检查项均在本次运行中重新执行，上表即本次结果。


## 本轮修正项的自检（对应交付要求一~五）

| 修正项 | 自检 | 位置 |
|---|---|---|
| 一 固定统计口径 | T4B 声明 receiver 等权为**主口径**、另两口径为敏感性；OOD-st 单终点“receiver 等权 CI 下界>0 而地理组等权 CI 跨 0”在数据中可见；claims 不再出现“不劣于” | `tables/Table4B_*`、`reports/CLAIM_EVIDENCE_MATRIX.csv` |
| 二 修复天气表 | Table 5 全部为数值单元格、无 JSON 转储；响应幅度与真实损失收益分节；统一时间窗口在 5.0 声明并按源码核实 | `tables/Table5_weather_response.md` |
| 三 补一次效率测量 | 分阶段成本、四条**完全相同**查询、纯计算身份校验副本、CPU/GPU 恢复与传输均已单独记录；未设也未维持 1.80× | `metrics/T7_c1_runtime.json`、`tables/Table7_*` |
| 四 正式验收 | 逐评分记录配对核对（id/season/坐标/地类/n_obs）；空间分组定义矛盾已核对并说明 | `reports/PAIRING_CHECK.md` |
| 五 修复交付 | `run_all.sh` 语法与自足性；账本字段数与状态；预测影像删除与保留统计量记录 | `code/run_all.sh`、`reports/RUN_LEDGER.csv`、`provenance/RETENTION_AND_DELETION.md` |

## 覆盖与唯一性

- T4B 以 **receiver=`dataset_index`** 为样本单位（`cube` 只是文件名，被多个 receiver 共用）；
  按 receiver 聚合后的数量与 v8 原表 `n_cubes` 完全一致（2066/1605/6965/5437）。
- T6A 保留原九个留出分段全集，未按结果筛选。
- T1 逐 seed 值原样转录，未做任何修改。

## 有限值与公式

- T4B 三口径公式：receiver 等权 = mean_receiver(donor/n − A/n)；地理组等权 = mean_group(group mean)；
  pooled = (Σdonor_sse − ΣA_sse)/Σn_valid。CI 由 B=2000、seed=20260910 的重采样给出，
  同一重采样同时作用于两侧（配对）。
- 所有 bootstrap 分位数取 2.5%/97.5%。

## 统计对象一致性

- T4B 的**每一条**点估计与其 CI 使用同一估计对象（本轮的修正重点）。
- T4A 的点估计与 CI 均来自 `closure_cut_alpha0.paired` / `bootstrap95` 同一配对集合。

## 来源

- 每个表的来源路径见 `EVIDENCE_INVENTORY.csv`；复用图件的来源见 `provenance/FIGURES_REUSED.csv`。

