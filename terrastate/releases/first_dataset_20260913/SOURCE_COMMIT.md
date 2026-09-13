# SOURCE_COMMIT — 来源与基线提交

## 基线

| 项 | 值 |
|---|---|
| Git 仓库 | `git@github.com:fuchen0614-oss/WorldModel2026.git` |
| 分支 | `q4-eval-percube-eligibility` |
| 提交 | `dc743eb75616a52c8bea6c2188c35a3c9ee8e61d` |
| 打包时间（UTC） | 2026-09-13T09:10:26Z |

本发布包中的每一项材料都**复制**自下列来源；来源目录**未被修改、未被移动、未被删除**。

| 用途 | 包内位置 | 来源（只读） | 文件数 | 大小 |
|---|---|---|---|---|
| 叙事两稿 + 参考 | `narrative/` | `/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_narrative_dual_20260913T082412Z` | 11 | 0.22 MiB |
| 终稿图与图注 | `figures/` | `/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_figures_final_20260913T052645Z` | 728 | 449.88 MiB |
| 8 张表 | `tables/` | `/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_closure_fix_20260911T081702Z/tables` | 16 | 0.06 MiB |
| 关键聚合指标 | `metrics/` | `/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_closure_fix_20260911T081702Z/metrics` | 50 | 1429.43 MiB |
| 验收与缺口 | `reports/` | `/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_closure_fix_20260911T081702Z/reports` | 13 | 0.05 MiB |
| 验收与缺口 | `reports/` | `/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_showcase_20260912T062326Z/reports` | 11 | 0.05 MiB |
| 验收与缺口 | `reports/` | `/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_showcase_20260912T062326Z/manifests` | 3 | 0.33 MiB |
| 复现数组 | `reproduction/` | `/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_figures_final_20260913T052645Z/图3_标准空间预测/data` | 129 | 221.43 MiB |
| 复现数组 | `reproduction/` | `/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_figures_final_20260913T052645Z/图8_天气条件响应/data` | 28 | 51.88 MiB |

## 与本包相邻的既存同步包

仓库在提交 `ecb632c`（"Add curated TerraState evidence sync package"）中已包含
`terrastate/sync_package_20260912_v1/`：E1 主表交付、evidence v8 的四划分表格与 Fig7、
leaveout JSON、FSR 文档，以及 5 个权重（**以 Git LFS 指针形式**，见 `WEIGHTS.md`）。
本包**不重复**这些内容，只补齐其未覆盖的部分：终稿图、两份主文、修正版表格
（Table 3/4A/4B/5/6A/6B/7）、配对统计、验收记录与复现数组。

## 复现命令（只读，不改动任何来源）

```bash
# 表格与指标
cat tables/Table4B_state_intervention_corrected.csv
cat metrics/T3_c0r_vs_c1_paired_bootstrap.json

# 终稿图（每个图目录内都有 code/ 与 data/）
ls figures/图7_共同后缀与状态作用/selected/
python figures/图7_共同后缀与状态作用/code/render_final.py   # 依赖见该目录 README

# 复现数组
python - <<'PY'
import numpy as np
z = np.load("reproduction/P42_arrays/arrays.npz")
print({k: z[k].shape for k in z.files})
PY
```
