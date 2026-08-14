# Figure 1 真实素材包使用说明

## 1. 最快使用方式

如果只想立刻开始排版，优先打开：

```text
copy_ready_primary/
```

该目录已经从三个候选中选出视觉最清楚的 **sample 01**，并按 Figure 1 用途重新命名。
可以直接复制 PNG 到 PPT，但仍应在 PPT 中用独立文本框添加标题和标签，不要把说明文字
压进图片。

快速总览：

```text
qa/FIG1_REAL_ASSET_CONTACT_SHEET.png
```

推荐使用顺序：

1. 主选：`sample_01_JAS21_minicube_197_34SEJ_39.50_21.71`
2. 备选：`sample_02_MJJ22_minicube_1_29SND_39.34_-8.53`
3. 备选：`sample_03_JAS22_minicube_22_30STJ_38.85_-5.31`

sample 01 含有清晰的耕地、道路和建成区纹理，历史—未来视觉关系也最容易辨认，最适合
Figure 1 的小尺寸图槽。

---

## 2. `copy_ready_primary/` 与 Figure 1 的对应关系

| Figure 1 位置 | 建议直接使用的文件 | 它是什么 | 使用限制 |
|---|---|---|---|
| Panel (a) EO 历史观测 | `copy_ready_primary/panel_a_eo/historical_observation.png` | sample 01 第 10 个历史 EO token 的真实 RGB | 可标为 historical observation |
| Panel (a) EO 未来观测示意 | `copy_ready_primary/panel_a_eo/future_observation.png` | 同一 AOI 第 20 个未来 token 的真实 RGB target | 只能标为 future observation/target，不能标为 forecast |
| Panel (b) Historical context | `copy_ready_primary/panel_b_historical_context/history_rgb_strip.png` | 同一 minicube 的历史 step 1/5/10 | 推荐作为 B1 主视觉 |
| Panel (b) 最近历史 RGB | `copy_ready_primary/panel_b_historical_context/history_rgb_latest.png` | 历史 step 10 | 图槽很小时使用 |
| Panel (b) 最近历史 NDVI | `copy_ready_primary/panel_b_historical_context/history_ndvi_latest.png` | 由 B8A/B04 计算的真实历史 NDVI | 可与 RGB 二选一 |
| Panel (b) 有效像素说明 | `copy_ready_primary/panel_b_historical_context/history_clear_mask.png` | 云/有效像素掩膜 | 只在需要解释 mask 时使用 |
| Panel (b) Q3 actual | `copy_ready_primary/panel_b_weather_intervention/actual_weather_strip.png` | 冻结 extreme minicube 的标准化 full24 未来天气 | 可直接放进 actual weather 小槽 |
| Panel (b) Q3 donor | `copy_ready_primary/panel_b_weather_intervention/matched_donor_weather_strip.png` | 冻结配对 donor 的标准化 full24 未来天气 | 可直接放进 matched-donor 小槽 |
| Panel (b) Q3 mean | `copy_ready_primary/panel_b_weather_intervention/normalized_mean_weather_strip.png` | 冻结协议中的全零 normalized-mean 控制 | 空白/白色是正确数据含义，不是导出失败 |
| Panel (b) Q3 三臂说明 | `copy_ready_primary/panel_b_weather_intervention/weather_three_arm_reference.png` | actual/donor/mean 的带标签参考图 | 用于理解或大图；Figure 1 小槽优先用三个独立 strip |
| Panel (b) 天气曲线备选 | `copy_ready_primary/panel_b_weather_intervention/actual_vs_donor_raw_curves.png` | 未来 100 天真实物理量曲线 | 适合解释，不建议整张塞入 Figure 1 |
| Panel (b) Observed future | `copy_ready_primary/panel_b_observed_future/observed_future_rgb_step20.png` | 同 AOI 的真实未来 RGB target | 可标为 observed future/target |
| Panel (b) Observed future NDVI | `copy_ready_primary/panel_b_observed_future/observed_future_ndvi_step20.png` | 同 AOI 的真实未来 NDVI target | 推荐作为目标/观测对照 |
| Panel (b) 未来序列 | `copy_ready_primary/panel_b_observed_future/observed_future_rgb_strip.png` | 未来 step 1/10/20 RGB | 空间允许时使用 |
| Panel (b) 未来 NDVI 序列 | `copy_ready_primary/panel_b_observed_future/observed_future_ndvi_strip.png` | 未来 step 1/10/20 NDVI | 适合表达 EO trajectory，但不是预测 |
| 可选 static：DEM | `copy_ready_primary/optional_static/dem_elevation.png` | Copernicus DEM | 图内空间不足时优先删除 |
| 可选 static：地形阴影 | `copy_ready_primary/optional_static/dem_hillshade.png` | DEM 派生 hillshade | 作为图标式 static geography |
| 可选 static：land cover | `copy_ready_primary/optional_static/landcover_esa_worldcover.png` | ESA WorldCover 分类 | 可标为 land cover |
| NDVI 色条 | `copy_ready_primary/legends/ndvi_colorbar.png` | 固定范围 −0.1–0.9 | 只有图中需要读数时才放 |
| land-cover 图例 | `copy_ready_primary/legends/landcover_legend.png` | ESA WorldCover 类别颜色 | Figure 1 通常不放，供作者核对 |

---

## 3. 最重要的边界：这些不是 TerraState forecast

本素材包当前只包含：

- 数据集中的历史 Sentinel-2 EO；
- 数据集中的未来真实观测 target；
- 数据集中的实际/匹配 donor 天气；
- 由冻结训练统计得到的标准化 full24 天气；
- normalized-mean 的全零控制；
- DEM、land cover 和 mask。

本素材包**不包含**：

```text
TerraState forecast
context-only forecast b_h
state contribution r_h
z_t / z_{t+h} 的真实内部张量
actual/donor/mean 三臂下的模型预测图
```

因此：

- `observed_future_*.png` 不能改名为 `forecast.png`；
- target 不能放入标有 “TerraState prediction” 的槽；
- Panel (b) 的 Forecast 模块在没有模型缓存时，应继续使用抽象小图框或明确写
  `Forecast`，不要塞入 target 冒充预测；
- `copy_ready_primary/model_outputs_NOT_AVAILABLE/` 专门用于提醒这一点。

---

## 4. 三个样本为什么被选中

三个样本均来自冻结 Q3 的 84 个 extreme–donor 配对。筛选只使用：

1. 固定历史/未来时点的有效像素比例；
2. NDVI 空间纹理；
3. tile 与时期多样性。

没有使用：

- 模型误差；
- donor/mean 相对 actual 的效果；
- Q2/Q3 干预效应；
- 人工挑选“模型表现最好”的样本。

| 样本 | 主要地表类型 | 六个固定帧平均有效比例 | 最低有效比例 | 用途建议 |
|---|---|---:|---:|---|
| sample 01 | Cropland | 0.9978 | 0.9869 | 主选；纹理和城镇边界最清楚 |
| sample 02 | Cropland | 0.9812 | 0.9385 | 河流/灌溉地块备选 |
| sample 03 | Grassland | 1.0000 | 1.0000 | 视觉更简洁的备选 |

完整排名和所有 84 个候选的质量字段：

```text
data/selection_record.json
```

三个最终样本摘要：

```text
data/selection_summary.csv
```

---

## 5. 每个 sample 子目录包含什么

```text
samples/<sample_name>/
├── historical_eo/
│   ├── history_rgb_step01.png
│   ├── history_rgb_step05.png
│   ├── history_rgb_step10.png
│   ├── history_rgb_strip.png
│   ├── history_ndvi_step10.png
│   └── history_clear_mask_step10.png
├── future_target/
│   ├── target_rgb_step01.png
│   ├── target_rgb_step10.png
│   ├── target_rgb_step20.png
│   ├── target_rgb_strip.png
│   ├── target_ndvi_step01.png
│   ├── target_ndvi_step10.png
│   ├── target_ndvi_step20.png
│   ├── target_ndvi_strip.png
│   └── target_clear_mask_step20.png
├── weather/
│   ├── actual_weather_full24_strip.png
│   ├── matched_donor_weather_full24_strip.png
│   ├── normalized_mean_weather_full24_strip.png
│   ├── weather_three_arm_reference.png
│   ├── actual_vs_matched_donor_raw_curves.png
│   └── 三份对应 full24 CSV
├── static_context/
│   ├── dem_elevation.png
│   ├── dem_hillshade.png
│   └── landcover_esa_worldcover.png
└── provenance/
    └── ASSET_PROVENANCE.json
```

每个 `ASSET_PROVENANCE.json` 记录：

- extreme `e_key` 与 donor `c_key`；
- 两个原始 `.nc` 的绝对路径与 SHA256；
- Q3 冻结 JSON 与 SHA256；
- conditioning statistics 与 SHA256；
- 时间步、波段、NDVI、mask 和 full24 构造；
- RGB/NDVI 显示变换；
- 是否包含模型输出。

---

## 6. 天气图片怎样理解

### 独立 full24 strip

三个 strip 都是 `20 × 24` 的标准化未来天气 token：

- 横向：future token 1–20；
- 纵向：24 个 mean/min/max E-OBS 特征；
- 红色：高于训练集均值；
- 蓝色：低于训练集均值；
- 白色：接近标准化零值。

`normalized_mean_weather_strip.png` 为白色是预期结果，因为冻结 Q3 协议使用
`zeros_like(future_weather)` 表示 normalized mean。

### 原始天气曲线

`actual_vs_matched_donor_raw_curves.png` 展示未来 100 天：

- rainfall；
- mean temperature；
- relative humidity；
- solar radiation。

蓝色实线为 actual，橙色虚线为 matched donor。部分变量的断线来自原始 E-OBS
缺失值，没有进行虚构插值。

---

## 7. 显示变换，不是数据篡改

- RGB 使用六个导出时点共享的 2%–98% percentile stretch 和 gamma 0.85；
- 所有 RGB 仍保持相同 AOI、像素网格和裁剪；
- NDVI 固定显示范围为 −0.1–0.9；
- 无效像素显示为浅灰；
- 128×128 原始空间网格用 nearest-neighbor 放大 4 倍，便于 PPT 裁切；
- 放大没有生成新的遥感细节。

---

## 8. 复现与完整性

导出脚本：

```text
source/export_fig1_real_assets.py
```

运行环境：

```text
/mnt/data/users/luzheng/workspace/iclr/czj/WorldModel2026/.conda/envs/WorldModel/bin/python
```

全部文件校验：

```text
SHA256SUMS.txt
```

本次过程没有加载 checkpoint、没有运行推理、没有重新评估模型，也没有修改冻结 JSON
或原始 NetCDF。

