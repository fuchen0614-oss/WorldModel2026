# REVIEW_START_HERE · E1 表格交付

交付目录：`/data/zs/multiseed_standard_eval_20260910T074115Z/E1_table_delivery`

## 交付文件

- `/data/zs/multiseed_standard_eval_20260910T074115Z/E1_table_delivery/E1_TABLE_DELIVERY.md`：按四个 split 分表的 E1 主表，含 C1 seed 27/42/97 明细、n=3 均值±样本标准差、A08 同协议基线及实际差距。
- `/data/zs/multiseed_standard_eval_20260910T074115Z/E1_table_delivery/E1_per_seed_values.csv`：逐 seed 可编辑数值及来源。
- `/data/zs/multiseed_standard_eval_20260910T074115Z/E1_table_delivery/E1_summary_values.csv`：均值、ddof=1 样本标准差及来源。
- `/data/zs/multiseed_standard_eval_20260910T074115Z/E1_table_delivery/E1_table_sources.csv`：来源和排除项。

## 验收

- 标准评测：seed27/42/97 × iid_chopped、ood-t_chopped、ood-s_chopped、ood-st_chopped 共 12/12 COMPLETE。每项实际预测文件数等于 manifest 预期数，缺失和多余均为 0；正式聚合指标有限，checkpoint_unchanged=true。
- C1 合并：四个 split 均为 n=3，均值与样本标准差由逐 seed 数值重算；标准差不是置信区间。
- 协议：官方 GreenEarthNet chopped LC-balanced scorer 的 q1_full 标准预测；未用 pooled 指标、共同后缀或文献数字替代。
- 基线：仅接入 A08 同协议实测的 ConvLSTM、PredRNN、SimVP、Contextformer、Persistence；Climatology/Previous year 与 Earthformer 留空/排除并说明。

## 范围外文件

本会话已停止 horizon_parallel 主 PID 3711186 及子 PID 3711251、3711252、3711253、3711254、3711255、3711256、3711257、3711258；停止后 horizon 匹配为空，正式评测匹配为空。此前 v2/v3/v4 PID 均已退出。保留但不纳入本次交付的逐时距文件位置：`/data/zs/multiseed_standard_eval_20260910T074115Z/horizon_parts/`、`/data/zs/multiseed_standard_eval_20260910T074115Z/per_cube_horizon_metrics.csv`、`/data/zs/multiseed_standard_eval_20260910T074115Z/per_seed_horizon_metrics.csv`，以及相关 `horizon_parallel*.log`。这些文件可能是旧版或未完成派生结果，不可视为最终结果。
