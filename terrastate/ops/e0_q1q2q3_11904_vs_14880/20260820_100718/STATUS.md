# E0 Evaluation Status

**Status**: ACCEPTED  
**验收时间**: 2026-08-20T08:45:41.468141Z  
**目录**: `20260820_100718`

## 验收结果

- **六项任务**: 6/6 通过
- **历史复现**: 57/57 指标，全部 Δ=0
- **失败项**: 0

## 关键对比 (11,904 vs 14,880)

### Validation Q1
- **11,904**: R²=0.4973, RMSE=0.1573
- **14,880**: R²=0.4971, RMSE=0.1573

### OOD-t Q1
- **11,904**: R²=0.5693, RMSE=0.1506
- **14,880**: R²=0.5693, RMSE=0.1506

### OOD-t Q3
- **11,904**: Q3_RESPONSE_FIDELITY_ONLY (endpoint: PASS, hotdry: FAIL)
- **14,880**: Q3_RESPONSE_FIDELITY_ONLY (endpoint: PASS, hotdry: FAIL)

## 解读

- 0.01 仅为描述性阈值，非选择门
- 14,880 已固定为后续 anchor
- 不根据 OOD 结果回选
- Q3 hot-dry FAIL 是科学结果

## 工件

- `attempt_manifest.json` — 本次尝试清单
- `e0_launch_record.json` — 启动记录
- `e0_acceptance_report.json` — 验收报告
- `e0_comparison_11904_vs_14880.json` — 完整比较
- `e0_provenance.json` — 溯源链
- `e0_artifact_index.json` — 工件索引
- `state.json` — 状态快照

## 排除的部分尝试（审计证据保留）

- `runs/gpu2_v14880_oodt_q1q2`
- `runs/gpu5_v14880_val_q1q2`
- `runs/gpu6_legacy11904_val_q1q2`
