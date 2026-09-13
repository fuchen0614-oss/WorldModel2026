# reproduction — 复现数组

本目录只放**终稿实际使用**的样本数组，用于重画图或复核数字。

| 文件 | 大小 | 内容 |
|---|---:|---|
| `P42_arrays/arrays.npz` | 3,974,392 B | 选定预测样本 P42 的 GT / TerraState-C1 / Persistence / 掩码 / 上下文 |
| `P42_official_baselines.npz` | 4,456,770 B | P42 上**四个官方基线**的预测（ConvLSTM / PredRNN / SimVP / Contextformer；原文件名 P42.npz，为可读性改名） |
| `W02_arrays/arrays.npz` | 4,450,220 B | 选定天气案例 W02 的 actual / donor / mean 三种情景预测 |

## 两种数组的形状

`P42_arrays/arrays.npz`（预测）：

```
gt            (20, 128, 128)  真实 NDVI，官方 20 个五日步
c1            (20, 128, 128)  TerraState-C1 预测
persistence   (20, 128, 128)  持续性基线（复现，非推理）
valid         (20, 128, 128)  有效像素掩码（云 / 非植被 / 缺测为 0）
context       (10, 128, 128)  上下文 NDVI
context_valid (10, 128, 128)  上下文掩码
landcover     (128, 128)      esawc 地类
```

`P42_official_baselines.npz`：`convlstm / predrnn / simvp / contextformer`，各 `(20, 128, 128)`，来自匹配的 GreenEarthNet 官方 seed-42 checkpoint；
上游来源与协议见 `P42_provenance.json`（`official_release` 指向权重归档）。

`W02_arrays/arrays.npz`（天气）：`gt / valid / pred_actual / pred_donor / pred_mean /
weather_actual / weather_donor / weather_mean`。

> `donor` 与 `mean` 是**反事实情景**：没有观测真值，只能说明模型会预测什么。

## 候选清单（不在此目录的数组）

`PREDICTION_CANDIDATES_60.csv`（60 个预测候选）、`PREDICTION_CANDIDATE_METRICS_60.csv`、
`MECHANISM_CANDIDATES_16.csv`（16 个机制候选）、`WEATHER_CANDIDATES_12.csv`（12 个天气候选）
只给出**清单与指标**；对应的逐样本数组保留在运行目录
`first_dataset_figures_final_20260913T052645Z/图*/data/_arrays/`（约 273 MiB），
如需重画其它候选，从那里取。

