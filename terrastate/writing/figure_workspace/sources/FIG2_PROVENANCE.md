# Figure 2 素材 provenance

## 1. 冻结样本

实际使用的历史 EO、mask、地理和未来天气素材继承自已通过 QA 的施工包：

`figure_workspace/TEMP_FIG2_REVISION_BUNDLE_20260728/`

主样本：

- EarthNet2021x OOD-t
- `JAS21/minicube_197_34SEJ_39.50_21.71.nc`
- dominant land cover: Cropland
- actual minicube SHA-256：`99525401b1d8ce0e6edeb3a641e72a27e43478bbbde17ed629756b4ee7082ec9`

matched donor：

- `JAS21/minicube_151_33TWE_40.62_16.18.nc`
- donor minicube SHA-256：`5f7bf6fb6856bbc41048937e97c5c841f09d74b1fa3fb6ec8c9f889d3a89ac4c`

冻结 Q3 记录：

- `evidence_workspace/raw/release/q3_extreme_state_audit.json`
- SHA-256：`9dae43b9a8a4fcdf0a73ef91daa58c189a88e769541ce295046cd0e938497041`

本候选稿没有运行模型推理，也没有重新挑选样本。

## 2. 当前实际嵌入的八张素材

### 真实项目输入

- `assets/real_project/history_rgb_strip.png`
  - 同一 minicube 的三帧历史 RGB。
  - 输入波段为 B04/B03/B02；共享 2–98 percentile stretch，gamma 0.85。
- `assets/real_project/history_clear_mask.png`
  - recorded clear mask。
- `assets/real_project/dem_hillshade.png`
  - 同一 AOI 的 Copernicus DEM hillshade。
- `assets/real_project/landcover_esa_worldcover.png`
  - 同一 AOI 的 ESA WorldCover。

### 由真实项目数值本地渲染

- `assets/real_project/past_weather_context.png`
  - 从 actual minicube 的前 50 天 `eobs_rr/eobs_tn/eobs_tg/eobs_tx` 直接绘制。
  - 这是输入数值的可视化，不是实验结果，也不是手填曲线。

### 冻结 Q3 future-weather input

- `assets/real_project/actual_future_weather_full24.png`
- `assets/real_project/matched_donor_weather_full24.png`
- `assets/real_project/normalized_mean_weather_full24.png`

三者均是 train-standardized daily E-OBS full24 的 20 个未来 token。normalized-mean control 在 normalized full24 space 中是全零 tensor，因此对应条带接近中性色，不应人为增加纹理。

所有候选包内素材的 SHA 和字节数记录在 `qa/automated_qa.json` 与 `EXPORT_MANIFEST.json`。

## 3. 不是模型输出的示意对象

以下均由 PPTX/SVG 原生矢量对象构成：

- `e_t` token grid
- `z_t` 与 `z_{t+h}` state grid
- context-only forecast `b_h`
- state raster contribution `r_h`
- NDVI forecast `ŷ_{t+h}`
- encoder、projection、condition fusion、transition、readout、加法节点和箭头

这些格子仅用于表达 tensor/raster 类型和路径，不携带某个样本的真实预测数值。

## 4. 明确未使用

施工包中的以下文件没有进入候选画布：

- `observed_future_ndvi_step20_REFERENCE_ONLY.png`
- `observed_future_rgb_step20_REFERENCE_ONLY.png`

因此不存在把 observed future 冒充 forecast 的问题。候选图也没有使用任何网络下载图片、他人论文图形或不可追踪装饰性位图。

