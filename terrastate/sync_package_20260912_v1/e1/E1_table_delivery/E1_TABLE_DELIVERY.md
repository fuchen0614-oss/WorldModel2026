# E1_TABLE_DELIVERY · TerraState 第一数据集标准预测

本表只包含 E1 `q1_full` 标准预测：GreenEarthNet chopped、官方 LC-balanced scorer、20 个五日预测网格；不含共同后缀、donor、状态替换、FSR、Q2/Q3/Q4 或第二数据集。C1 为正式 checkpoint 的 3-seed 结果（seed 27/42/97），均值±样本标准差使用 ddof=1，明确 n=3；该标准差不是置信区间。

表中基线来自 A08 的同协议实测结果；文献数字、未完成/不可核实基线不混入。

## IID (`iid_chopped`)

| Method | seed/summary | R²↑ | RMSE↓ | NSE↑ | \|Bias\|↓ | RMSE25↓ | source |
|---|---|---:|---:|---:|---:|---:|---|
| TerraState-C1 | 27 | 0.5221 | 0.1555 | -0.1371 | 0.0997 | 0.0911 | this eval |
| TerraState-C1 | 42 | 0.5220 | 0.1555 | -0.1370 | 0.0996 | 0.0912 | this eval |
| TerraState-C1 | 97 | 0.5221 | 0.1555 | -0.1370 | 0.0997 | 0.0911 | this eval |
| **TerraState-C1** | **mean ± sample std (n=3)** | **0.5221 ± 0.0001** | **0.1555 ± 0.0000** | **-0.1370 ± 0.0001** | **0.0997 ± 0.0000** | **0.0912 ± 0.0000** | summary |
| ConvLSTM 1M | 27 | 0.5108 | 0.1546 | -0.0915 | 0.0965 | 0.0994 | A08 same-protocol |
| ConvLSTM 1M | 42 | 0.5121 | 0.1568 | -0.1130 | 0.0989 | 0.1024 | A08 same-protocol |
| ConvLSTM 1M | 97 | 0.5091 | 0.1557 | -0.1092 | 0.0980 | 0.0996 | A08 same-protocol |
| **ConvLSTM 1M** | **mean ± sample std (n=3)** | **0.5107 ± 0.0015** | **0.1557 ± 0.0011** | **-0.1046 ± 0.0115** | **0.0978 ± 0.0012** | **0.1005 ± 0.0017** | summary |
| PredRNN 1M | 27 | 0.5541 | 0.1371 | 0.0982 | 0.0827 | 0.0869 | A08 same-protocol |
| PredRNN 1M | 42 | 0.5345 | 0.1449 | 0.0130 | 0.0895 | 0.0917 | A08 same-protocol |
| PredRNN 1M | 97 | 0.5357 | 0.1449 | 0.0168 | 0.0884 | 0.0879 | A08 same-protocol |
| **PredRNN 1M** | **mean ± sample std (n=3)** | **0.5414 ± 0.0110** | **0.1423 ± 0.0045** | **0.0427 ± 0.0481** | **0.0869 ± 0.0037** | **0.0888 ± 0.0025** | summary |
| SimVP 6M | 27 | 0.5003 | 0.1443 | -0.0003 | 0.0854 | 0.1012 | A08 same-protocol |
| SimVP 6M | 42 | 0.5040 | 0.1463 | -0.0127 | 0.0883 | 0.0980 | A08 same-protocol |
| SimVP 6M | 97 | 0.4921 | 0.1477 | -0.0444 | 0.0875 | 0.1034 | A08 same-protocol |
| **SimVP 6M** | **mean ± sample std (n=3)** | **0.4988 ± 0.0061** | **0.1461 ± 0.0017** | **-0.0191 ± 0.0227** | **0.0871 ± 0.0015** | **0.1009 ± 0.0027** | summary |
| Contextformer 6M | 27 | 0.5332 | 0.1485 | -0.0357 | 0.0941 | 0.0897 | A08 same-protocol |
| Contextformer 6M | 42 | 0.5340 | 0.1493 | -0.0531 | 0.0950 | 0.0894 | A08 same-protocol |
| Contextformer 6M | 97 | 0.5328 | 0.1475 | -0.0274 | 0.0933 | 0.0888 | A08 same-protocol |
| **Contextformer 6M** | **mean ± sample std (n=3)** | **0.5333 ± 0.0006** | **0.1484 ± 0.0009** | **-0.0387 ± 0.0131** | **0.0941 ± 0.0009** | **0.0893 ± 0.0005** | summary |
| Persistence | deterministic | 0.0000 | 0.2213 | -1.1716 | 0.1610 | 0.1028 | A08 same-protocol |

## OOD-t (`ood-t_chopped`)

| Method | seed/summary | R²↑ | RMSE↓ | NSE↑ | \|Bias\|↓ | RMSE25↓ | source |
|---|---|---:|---:|---:|---:|---:|---|
| TerraState-C1 | 27 | 0.5725 | 0.1510 | -0.1073 | 0.1014 | 0.0824 | this eval |
| TerraState-C1 | 42 | 0.5726 | 0.1509 | -0.1065 | 0.1013 | 0.0824 | this eval |
| TerraState-C1 | 97 | 0.5727 | 0.1509 | -0.1066 | 0.1013 | 0.0824 | this eval |
| **TerraState-C1** | **mean ± sample std (n=3)** | **0.5726 ± 0.0001** | **0.1510 ± 0.0000** | **-0.1068 ± 0.0004** | **0.1014 ± 0.0000** | **0.0824 ± 0.0000** | summary |
| ConvLSTM 1M | 27 | 0.5466 | 0.1603 | -0.1750 | 0.1093 | 0.1004 | A08 same-protocol |
| ConvLSTM 1M | 42 | 0.5560 | 0.1636 | -0.1989 | 0.1122 | 0.1053 | A08 same-protocol |
| ConvLSTM 1M | 97 | 0.5424 | 0.1606 | -0.1957 | 0.1077 | 0.1008 | A08 same-protocol |
| **ConvLSTM 1M** | **mean ± sample std (n=3)** | **0.5483 ± 0.0070** | **0.1615 ± 0.0018** | **-0.1899 ± 0.0130** | **0.1097 ± 0.0023** | **0.1022 ± 0.0027** | summary |
| PredRNN 1M | 27 | 0.5942 | 0.1498 | -0.0675 | 0.1026 | 0.1015 | A08 same-protocol |
| PredRNN 1M | 42 | 0.5915 | 0.1466 | -0.0165 | 0.0960 | 0.1001 | A08 same-protocol |
| PredRNN 1M | 97 | 0.5916 | 0.1458 | -0.0286 | 0.0935 | 0.1039 | A08 same-protocol |
| **PredRNN 1M** | **mean ± sample std (n=3)** | **0.5924 ± 0.0015** | **0.1474 ± 0.0021** | **-0.0375 ± 0.0266** | **0.0974 ± 0.0047** | **0.1018 ± 0.0019** | summary |
| SimVP 6M | 27 | 0.5555 | 0.1510 | -0.0819 | 0.1000 | 0.1055 | A08 same-protocol |
| SimVP 6M | 42 | 0.5650 | 0.1472 | -0.0489 | 0.0964 | 0.1025 | A08 same-protocol |
| SimVP 6M | 97 | 0.5644 | 0.1495 | -0.0671 | 0.0966 | 0.1050 | A08 same-protocol |
| **SimVP 6M** | **mean ± sample std (n=3)** | **0.5616 ± 0.0053** | **0.1492 ± 0.0019** | **-0.0660 ± 0.0165** | **0.0977 ± 0.0020** | **0.1043 ± 0.0016** | summary |
| Contextformer 6M | 27 | 0.5897 | 0.1438 | -0.0086 | 0.0941 | 0.0849 | A08 same-protocol |
| Contextformer 6M | 42 | 0.5827 | 0.1433 | 0.0001 | 0.0937 | 0.0786 | A08 same-protocol |
| Contextformer 6M | 97 | 0.5907 | 0.1422 | 0.0238 | 0.0931 | 0.0820 | A08 same-protocol |
| **Contextformer 6M** | **mean ± sample std (n=3)** | **0.5877 ± 0.0044** | **0.1431 ± 0.0008** | **0.0051 ± 0.0168** | **0.0936 ± 0.0005** | **0.0818 ± 0.0032** | summary |
| Persistence | deterministic | 0.0000 | 0.2157 | -1.2248 | 0.1583 | 0.0850 | A08 same-protocol |

## OOD-s (`ood-s_chopped`)

| Method | seed/summary | R²↑ | RMSE↓ | NSE↑ | \|Bias\|↓ | RMSE25↓ | source |
|---|---|---:|---:|---:|---:|---:|---|
| TerraState-C1 | 27 | 0.4949 | 0.1621 | -0.1764 | 0.1018 | 0.0970 | this eval |
| TerraState-C1 | 42 | 0.4949 | 0.1621 | -0.1762 | 0.1018 | 0.0970 | this eval |
| TerraState-C1 | 97 | 0.4949 | 0.1621 | -0.1764 | 0.1018 | 0.0970 | this eval |
| **TerraState-C1** | **mean ± sample std (n=3)** | **0.4949 ± 0.0000** | **0.1621 ± 0.0000** | **-0.1763 ± 0.0001** | **0.1018 ± 0.0000** | **0.0970 ± 0.0000** | summary |
| ConvLSTM 1M | 27 | 0.4787 | 0.1611 | -0.1413 | 0.0988 | 0.1024 | A08 same-protocol |
| ConvLSTM 1M | 42 | 0.4777 | 0.1632 | -0.1630 | 0.1009 | 0.1058 | A08 same-protocol |
| ConvLSTM 1M | 97 | 0.4718 | 0.1622 | -0.1576 | 0.0997 | 0.1033 | A08 same-protocol |
| **ConvLSTM 1M** | **mean ± sample std (n=3)** | **0.4761 ± 0.0037** | **0.1622 ± 0.0011** | **-0.1540 ± 0.0113** | **0.0998 ± 0.0011** | **0.1038 ± 0.0018** | summary |
| PredRNN 1M | 27 | 0.5187 | 0.1445 | 0.0464 | 0.0841 | 0.0912 | A08 same-protocol |
| PredRNN 1M | 42 | 0.5071 | 0.1526 | -0.0484 | 0.0927 | 0.0974 | A08 same-protocol |
| PredRNN 1M | 97 | 0.5004 | 0.1510 | -0.0288 | 0.0895 | 0.0920 | A08 same-protocol |
| **PredRNN 1M** | **mean ± sample std (n=3)** | **0.5087 ± 0.0093** | **0.1494 ± 0.0043** | **-0.0103 ± 0.0500** | **0.0888 ± 0.0043** | **0.0935 ± 0.0034** | summary |
| SimVP 6M | 27 | 0.4631 | 0.1517 | -0.0549 | 0.0864 | 0.1077 | A08 same-protocol |
| SimVP 6M | 42 | 0.4720 | 0.1529 | -0.0654 | 0.0896 | 0.1031 | A08 same-protocol |
| SimVP 6M | 97 | 0.4597 | 0.1542 | -0.0907 | 0.0886 | 0.1100 | A08 same-protocol |
| **SimVP 6M** | **mean ± sample std (n=3)** | **0.4649 ± 0.0064** | **0.1529 ± 0.0013** | **-0.0703 ± 0.0184** | **0.0882 ± 0.0016** | **0.1069 ± 0.0035** | summary |
| Contextformer 6M | 27 | 0.5039 | 0.1548 | -0.0770 | 0.0958 | 0.0949 | A08 same-protocol |
| Contextformer 6M | 42 | 0.5024 | 0.1566 | -0.1021 | 0.0978 | 0.0954 | A08 same-protocol |
| Contextformer 6M | 97 | 0.5000 | 0.1534 | -0.0580 | 0.0945 | 0.0941 | A08 same-protocol |
| **Contextformer 6M** | **mean ± sample std (n=3)** | **0.5021 ± 0.0020** | **0.1549 ± 0.0016** | **-0.0790 ± 0.0221** | **0.0960 ± 0.0017** | **0.0948 ± 0.0007** | summary |
| Persistence | deterministic | 0.0000 | 0.2258 | -1.1336 | 0.1625 | 0.1127 | A08 same-protocol |

## OOD-st (`ood-st_chopped`)

| Method | seed/summary | R²↑ | RMSE↓ | NSE↑ | \|Bias\|↓ | RMSE25↓ | source |
|---|---|---:|---:|---:|---:|---:|---|
| TerraState-C1 | 27 | 0.5405 | 0.1542 | -0.1556 | 0.1017 | 0.0871 | this eval |
| TerraState-C1 | 42 | 0.5408 | 0.1542 | -0.1547 | 0.1016 | 0.0871 | this eval |
| TerraState-C1 | 97 | 0.5409 | 0.1542 | -0.1549 | 0.1016 | 0.0871 | this eval |
| **TerraState-C1** | **mean ± sample std (n=3)** | **0.5407 ± 0.0002** | **0.1542 ± 0.0000** | **-0.1551 ± 0.0004** | **0.1016 ± 0.0000** | **0.0871 ± 0.0000** | summary |
| ConvLSTM 1M | 27 | 0.5203 | 0.1605 | -0.2135 | 0.1054 | 0.1024 | A08 same-protocol |
| ConvLSTM 1M | 42 | 0.5267 | 0.1621 | -0.2295 | 0.1079 | 0.1063 | A08 same-protocol |
| ConvLSTM 1M | 97 | 0.5231 | 0.1605 | -0.2353 | 0.1045 | 0.1054 | A08 same-protocol |
| **ConvLSTM 1M** | **mean ± sample std (n=3)** | **0.5234 ± 0.0032** | **0.1610 ± 0.0009** | **-0.2261 ± 0.0113** | **0.1059 ± 0.0018** | **0.1047 ± 0.0020** | summary |
| PredRNN 1M | 27 | 0.5647 | 0.1485 | -0.0806 | 0.0971 | 0.1034 | A08 same-protocol |
| PredRNN 1M | 42 | 0.5616 | 0.1487 | -0.0720 | 0.0951 | 0.1028 | A08 same-protocol |
| PredRNN 1M | 97 | 0.5642 | 0.1463 | -0.0599 | 0.0906 | 0.1074 | A08 same-protocol |
| **PredRNN 1M** | **mean ± sample std (n=3)** | **0.5635 ± 0.0017** | **0.1478 ± 0.0013** | **-0.0708 ± 0.0104** | **0.0943 ± 0.0033** | **0.1045 ± 0.0025** | summary |
| SimVP 6M | 27 | 0.5272 | 0.1547 | -0.1476 | 0.0999 | 0.1075 | A08 same-protocol |
| SimVP 6M | 42 | 0.5255 | 0.1536 | -0.1396 | 0.0989 | 0.1067 | A08 same-protocol |
| SimVP 6M | 97 | 0.5297 | 0.1575 | -0.1785 | 0.1008 | 0.1103 | A08 same-protocol |
| **SimVP 6M** | **mean ± sample std (n=3)** | **0.5275 ± 0.0021** | **0.1553 ± 0.0020** | **-0.1552 ± 0.0205** | **0.0999 ± 0.0010** | **0.1082 ± 0.0019** | summary |
| Contextformer 6M | 27 | 0.5575 | 0.1467 | -0.0524 | 0.0946 | 0.0882 | A08 same-protocol |
| Contextformer 6M | 42 | 0.5574 | 0.1485 | -0.0752 | 0.0973 | 0.0835 | A08 same-protocol |
| Contextformer 6M | 97 | 0.5552 | 0.1467 | -0.0459 | 0.0956 | 0.0862 | A08 same-protocol |
| **Contextformer 6M** | **mean ± sample std (n=3)** | **0.5567 ± 0.0013** | **0.1473 ± 0.0010** | **-0.0578 ± 0.0154** | **0.0958 ± 0.0014** | **0.0860 ± 0.0024** | summary |
| Persistence | deterministic | 0.0000 | 0.2183 | -1.2401 | 0.1607 | 0.0966 | A08 same-protocol |

## C1 相对主要同协议基线的实际差距

- `iid_chopped`：C1 相对 Contextformer 6M 的 Δ(R², RMSE, NSE, |Bias|, RMSE25) = (-0.0112, +0.0071, -0.0983, +0.0055, +0.0019)；相对 PredRNN 1M = (-0.0193, +0.0132, -0.1797, +0.0128, +0.0023)。差值按 C1−基线计算，方向优劣按表头箭头解释，不预设 C1 优于基线。
- `ood-t_chopped`：C1 相对 Contextformer 6M 的 Δ(R², RMSE, NSE, |Bias|, RMSE25) = (-0.0151, +0.0079, -0.1119, +0.0077, +0.0006)；相对 PredRNN 1M = (-0.0198, +0.0036, -0.0692, +0.0040, -0.0194)。差值按 C1−基线计算，方向优劣按表头箭头解释，不预设 C1 优于基线。
- `ood-s_chopped`：C1 相对 Contextformer 6M 的 Δ(R², RMSE, NSE, |Bias|, RMSE25) = (-0.0072, +0.0072, -0.0973, +0.0058, +0.0022)；相对 PredRNN 1M = (-0.0138, +0.0128, -0.1661, +0.0130, +0.0035)。差值按 C1−基线计算，方向优劣按表头箭头解释，不预设 C1 优于基线。
- `ood-st_chopped`：C1 相对 Contextformer 6M 的 Δ(R², RMSE, NSE, |Bias|, RMSE25) = (-0.0160, +0.0069, -0.0972, +0.0058, +0.0011)；相对 PredRNN 1M = (-0.0228, +0.0063, -0.0842, +0.0074, -0.0174)。差值按 C1−基线计算，方向优劣按表头箭头解释，不预设 C1 优于基线。

## 限制与缺失标记

- Climatology / Previous year：A08 标为阻塞，未纳入表格；Earthformer：权重不可得，未纳入表格。
- OOD-s 使用已验收 repair overlay 的独立 materialized 只读副本，manifest 样本集合保持 10,536；与其他 split 的数据来源不同，已在状态 CSV 中标明。
- A08 基线为已有同协议实测结果；不含文献表格数字。
- 逐时距派生文件和未完成/旧版逐时距文件不属于本次 E1 表格交付，不能视为最终结果。

可编辑数据：`E1_per_seed_values.csv`、`E1_summary_values.csv`、`E1_table_sources.csv`。
