# 关键权重与最终结果索引

本页只回答两个问题：哪些权重真正保留了，以及当前论文使用哪些最终数值。

## 权重

| 身份 | 本地文件 | step | SHA-256 | 可做什么 |
|---|---|---:|---|---|
| Phase-I B4 教师/精度锚点 | `07_WEIGHTS_AND_PROVENANCE/phase1_b4_teacher/checkpoint_best.pt` | 13,000 | `2c5d084236716d84d1ed11289248a501a7cb906675a32ccb8fd73e1f2a26881c` | 可严格加载为 `ObsWorldB4`；用于 V2 KD teacher 与 B4 精度复验，不是最终 TerraState 权重 |
| 历史 boundary80 正式候选 | `07_WEIGHTS_AND_PROVENANCE/historical_boundary80_release/checkpoint_boundary80.pt` | 11,904 | `644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd` | 可在 commit `52578ca` 严格加载并复验历史 Q1–Q3 evidence |
| 作者确认的最终模型 | 二进制尚未恢复 | 14,880 | 候选台账记录 weight SHA `aa98fbd2fa302727bc3375dff17e1c414c652c19d0919c4fbcdcd05a0a5d28aa` | 当前正文口径；取得二进制后仍需重新验证文件 SHA 与 Q1–Q3 绑定 |

不得把 boundary80 文件重命名成最终权重，也不得使用 `runs/smoke_*` 下的权重
填补缺口。权重的详细身份冲突见 `PROVENANCE_AND_WEIGHT_STATUS.md`。

## 当前论文关键结果

当前报告数值统一保存在 `04_RESULTS_EVIDENCE/current/release_metrics/`：

### Q1：预测效用（OOD-t，1,904 minicubes）

| R² | RMSE | NSE | \|bias\| | RMSE25 |
|---:|---:|---:|---:|---:|
| 0.56935 | 0.15059 | -0.099 | 0.101 | 0.082 |

### Q2：承载预测的状态

| split | Full R² | 移除状态 R² | ΔR² | 恒等转移 R² | ΔR² |
|---|---:|---:|---:|---:|---:|
| validation | 0.49732 | 0.48611 | 0.01121 | 0.48542 | 0.01191 |
| OOD-t | 0.56935 | 0.54938 | 0.01997 | 0.54766 | 0.02169 |

两组 paired bootstrap 95% CI 均在 0 以上；完整区间见 `q2_metrics.json`。

### Q3：天气响应保真度（冻结 heat-drought 子集）

| 条件 | R² | RMSE | control − actual loss |
|---|---:|---:|---:|
| Actual weather | 0.6254 | 0.1492 | — |
| Matched donor | 0.5893 | 0.1584 | 0.00257 |
| Normalized mean | 0.5430 | 0.1971 | 0.01126 |

样本为 84 对、31 个 geographic clusters、10,000 次 bootstrap。这里的 R²/RMSE
是 Q3 冻结子集结果，不能替代 Q1 的完整 OOD-t 主表指标。

## 中间结果排除规则

本归档不再纳入训练周期 checkpoint、smoke 权重、临时选择表、失败版图、预测
缓存或重复评分副本。具有科学意义的历史 release 证据单独放在
`04_RESULTS_EVIDENCE/historical_release_provenance/`，不会混入当前最终结果。
