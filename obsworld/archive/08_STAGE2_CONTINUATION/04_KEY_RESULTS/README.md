# Stage2 最终关键结果

本目录保存与 `03_KEY_WEIGHTS/` 两份 best checkpoint 对应的 GreenEarthNet
OOD-t chopped 正式评分。只保留聚合 metrics、CSV 和 scorer provenance；不保存
逐季 parquet、预测 NetCDF、过程日志或周期 checkpoint。

评测合同：

- protocol：`greenearthnet_cvpr2024_chopped_v1`
- split：`ood-t_chopped`
- target files：1,904
- prediction grid：official 5-day / 20-step
- official evaluator commit：`a0329636631371a4aaa9a95c75ed0a37d27b8c4f`
- manifest SHA-256：`58c8d64897193e9cffff5bc6c8524909707ebae5376b5d4dee68597ef08e1e49`

## 汇总

| 路线 | R² | RMSE | NSE | \|bias\| | RMSE25 |
|---|---:|---:|---:|---:|---:|
| Direct physical4 best | 0.52430 | 0.17776 | -0.41513 | 0.12583 | 0.12552 |
| Rollout physical4 best | 0.50388 | 0.18390 | -0.47572 | 0.13111 | 0.12762 |

这些是值得保留的正式历史结果，但不是后期 TerraState/AAAI 主模型结果，也不应
与另一归档中的 TerraState Q1–Q3 证据混写。它们的主要价值是：提供一个从
Stage1.5 初始化继续开发 Direct 与 rollout 动力学的可加载起点和真实基线。

## 文件对应

- `direct_physical4/metrics_en21x.{json,csv}`：Direct 聚合指标；
- `direct_physical4/score_provenance.json`：Direct scorer 来源链；
- `rollout_physical4/metrics_en21x.{json,csv}`：Rollout 聚合指标；
- `rollout_physical4/score_provenance.json`：Rollout scorer 来源链；
- `protocol/greenearthnet_oodt_chopped_manifest.json`：两者共同使用的文件清单。

