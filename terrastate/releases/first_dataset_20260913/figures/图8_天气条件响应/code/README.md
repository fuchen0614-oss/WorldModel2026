# 图8 一键重绘

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
