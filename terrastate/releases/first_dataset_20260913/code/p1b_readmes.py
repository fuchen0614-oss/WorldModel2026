#!/usr/bin/env python3
"""Part 1b: rewrite the two code/README.md files in the release package."""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REL = Path("/data/zs/WorldModel2026/terrastate/releases/first_dataset_20260913")

FIG3 = """# 图3 绘制与复现

## 一键重绘（当前正式入口）

在本图目录执行：

```bash
/data/zs/WorldModel2026/.venv-worldmodel/bin/python code/render_final.py
```

`render_final.py` 绘制**正式版本**的图3A / 图3B，共七个模型行：

Ground truth、Persistence、**ConvLSTM 1M、SimVP 6M、PredRNN 1M、Contextformer 6M**、TerraState-C1。

四个官方基线来自**匹配的 GreenEarthNet 官方 seed-42 checkpoint**（协议、commit 与权重校验见
`data/OFFICIAL_BASELINE_WEIGHT_AUDIT.md` 与 `reproduction/P42_provenance.json`）。图中已无空行。

## 输入位置（两种包结构都会自动适配）

`render_final.py` 按顺序查找，找到即用：

| 输入 | 完整源终稿包 | 精简发布包（本包） |
|---|---|---|
| P42 数组 | `图3_标准空间预测/data/_arrays/P42/arrays.npz` | `reproduction/P42_arrays/arrays.npz` |
| P42 元数据 | `图3_标准空间预测/data/_arrays/P42/metadata.json` | `reproduction/P42_arrays/metadata.json` |
| 四个官方基线预测 | `图3_标准空间预测/data/baseline_predictions/P42.npz` | `reproduction/P42_official_baselines.npz` |

精简包只在 `reproduction/` 保留一份数组，因此不在图目录内重复约 13 MiB。

## 重新执行官方基线推理

`run_official_greenearthnet_p42.py` 是**官方基线的推理入口**，需要原始数据、官方模型配置与
checkpoint。它产出的预测就是上表的 `P42_official_baselines.npz` / `baseline_predictions/P42.npz`。

## 历史脚本（不是当前事实来源）

以下脚本属于**官方基线推理之前**的候选导出流程。它们文件头中"官方基线预测不可用"
一类的描述**只对当时成立、现已过时**，请勿据此判断当前状态：

| 脚本 | 当时的用途 |
|---|---|
| `export_arrays.py` | 早期候选数组导出；其 `missing_baselines` 字段记录的是**导出当时**的可用性 |
| `build_candidates.py`、`make_contact_sheets*.py` | 60 个预测候选的冻结与缩略图 |
| `render_prediction.py` | 早期候选浏览/详细图渲染（已被 `render_final.py` 取代） |
| `lib_showcase.py`、`verify_showcase.py` | 上述流程的公共库与验收脚本 |

**当前正式入口只有两个**：`render_final.py`（重绘正式图）与
`run_official_greenearthnet_p42.py`（官方基线推理）。
"""

FIG8 = """# 图8 一键重绘

在本图目录执行：

```bash
/data/zs/WorldModel2026/.venv-worldmodel/bin/python code/render_final.py
```

脚本重绘**紧凑总体天气响应图**（A：总体效应；B：W02 天气输入）与 **W02 空间/轨迹详图**：
总体 B 使用指定的单一两行图例，详图的色带与对应空间图组水平对齐，并同时输出 PNG 与 PDF。

## 输入位置（两种包结构都会自动适配）

| 输入 | 完整源终稿包 | 精简发布包（本包） |
|---|---|---|
| 总体效应表 | `图8_天气条件响应/data/Table5_weather_response.csv` | 同左（已随包） |
| W02 数组 | `图8_天气条件响应/data/_arrays/W02/arrays.npz` | `reproduction/W02_arrays/arrays.npz` |
| W02 元数据 | `图8_天气条件响应/data/_arrays/W02/metadata.json` | `reproduction/W02_arrays/metadata.json` |

脚本按顺序查找，找到即用；精简包只在 `reproduction/` 保留一份 W02 数组。

## 读图口径

`donor` 与 `mean` 是**反事实天气情景**，没有观测真值；图中差异只说明**模型响应**，
不是已知的反事实误差。只有 `actual` 有对应的真实观测。样本范围是冻结的 84 对热旱配对。
"""

for rel, text in (("figures/图3_标准空间预测/code/README.md", FIG3),
                  ("figures/图8_天气条件响应/code/README.md", FIG8)):
    p = REL / rel
    old = p.stat().st_size
    p.write_text(text, encoding="utf-8")
    print(f"rewrote {rel}  {old:,} -> {p.stat().st_size:,} B")
