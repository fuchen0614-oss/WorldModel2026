# Table 1. GreenEarthNet 第一数据集标准预测（同协议）

来源：`multiseed_standard_eval_20260910T074115Z/E1_table_delivery/`（已验收）。
指标：官方 GreenEarthNet chopped LC-balanced scorer；history 130 → forecast 20。
C1 为三个训练 seed（27/42/97）；基线为官方发布的三个权重种子同协议重评。

| 方法 | split | n(seed) | R²_LC (mean ± 样本std) | RMSE_LC (mean ± 样本std) |
|---|---|---:|---|---|
| TerraState-C1 | iid_chopped | 3 | 0.5221 ± 0.0001 | 0.1555 ± 0.0000 |
| ConvLSTM 1M | iid_chopped | 3 | 0.5107 ± 0.0015 | 0.1557 ± 0.0011 |
| PredRNN 1M | iid_chopped | 3 | 0.5414 ± 0.0110 | 0.1423 ± 0.0045 |
| SimVP 6M | iid_chopped | 3 | 0.4988 ± 0.0061 | 0.1461 ± 0.0017 |
| Contextformer 6M | iid_chopped | 3 | 0.5333 ± 0.0006 | 0.1484 ± 0.0009 |
| Persistence | iid_chopped | 1 | 0.0000 | 0.2213 |
| TerraState-C1 | ood-t_chopped | 3 | 0.5726 ± 0.0001 | 0.1510 ± 0.0000 |
| ConvLSTM 1M | ood-t_chopped | 3 | 0.5483 ± 0.0070 | 0.1615 ± 0.0018 |
| PredRNN 1M | ood-t_chopped | 3 | 0.5924 ± 0.0015 | 0.1474 ± 0.0021 |
| SimVP 6M | ood-t_chopped | 3 | 0.5616 ± 0.0053 | 0.1492 ± 0.0019 |
| Contextformer 6M | ood-t_chopped | 3 | 0.5877 ± 0.0044 | 0.1431 ± 0.0008 |
| Persistence | ood-t_chopped | 1 | 0.0000 | 0.2157 |
| TerraState-C1 | ood-s_chopped | 3 | 0.4949 ± 0.0000 | 0.1621 ± 0.0000 |
| ConvLSTM 1M | ood-s_chopped | 3 | 0.4761 ± 0.0037 | 0.1622 ± 0.0011 |
| PredRNN 1M | ood-s_chopped | 3 | 0.5087 ± 0.0093 | 0.1494 ± 0.0043 |
| SimVP 6M | ood-s_chopped | 3 | 0.4649 ± 0.0064 | 0.1529 ± 0.0013 |
| Contextformer 6M | ood-s_chopped | 3 | 0.5021 ± 0.0020 | 0.1549 ± 0.0016 |
| Persistence | ood-s_chopped | 1 | 0.0000 | 0.2258 |
| TerraState-C1 | ood-st_chopped | 3 | 0.5407 ± 0.0002 | 0.1542 ± 0.0000 |
| ConvLSTM 1M | ood-st_chopped | 3 | 0.5234 ± 0.0032 | 0.1610 ± 0.0009 |
| PredRNN 1M | ood-st_chopped | 3 | 0.5635 ± 0.0017 | 0.1478 ± 0.0013 |
| SimVP 6M | ood-st_chopped | 3 | 0.5275 ± 0.0021 | 0.1553 ± 0.0020 |
| Contextformer 6M | ood-st_chopped | 3 | 0.5567 ± 0.0013 | 0.1473 ± 0.0010 |
| Persistence | ood-st_chopped | 1 | 0.0000 | 0.2183 |

> 均值 ± **样本标准差（ddof=1，n=3）**，不是置信区间。
> 逐 seed 值见 `metrics/T1_per_seed_values.csv`（原样转录，未改动）。
