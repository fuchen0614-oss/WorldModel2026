# Figure 2 临时施工包 QA

检查日期：2026-07-28 UTC

## 结论

PASS，适合作为作者手工修改 Figure 2 的施工素材包。

本结论不表示推荐线框已经是最终论文美术稿，也不表示抽象 `SCHEMATIC` 栅格是模型输出。

## 完整性

- 当前图历史副本：PPTX / PDF / PNG 完整；
- 推荐线框：SVG / 300 dpi PNG 完整；
- 可编辑机制素材：SVG / 300 dpi PNG 成对存在；
- 真实 EO / mask / DEM / land-cover / weather PNG 完整；
- 中文施工蓝图、README、provenance 与 SHA 清单完整。

## 分辨率

- 最小 PNG 为图标，`360 × 360 px @ 300 dpi`；
- 单帧真实 EO/地理图为 `512 × 512 px @ 300 dpi`；
- 单路天气条带为 `960 × 245 px @ 300 dpi`；
- 历史 EO strip 与组合天气图均高于单栏小图使用所需分辨率；
- 机制图优先提供 SVG，可无损缩放。

## SVG

- 18 个 SVG 均通过 XML 解析；
- 机制 SVG 中的文字保留为 `<text>`，未转路径；
- 纯图标 SVG 不含文字是预期行为；
- 三个 `SCHEMATIC` raster SVG 内含一个本地生成的小型 raster 图层，文件名与图面均明确标识；
- 其余机制 SVG 不嵌入 raster。

## 来源与数据边界

- 历史 EO、mask、DEM、land cover 与天气来自
  `primary_sample_provenance.json` 记录的 EarthNet2021x minicube；
- actual / matched donor / normalized mean 来自冻结 Q3 配对及既有 full24 导出；
- 未加载模型、未重新评估、未改实验记录；
- observed future 只放在 `reference_only_not_model_output/`；
- 当前正式 Figure 2 的 PPTX/PDF/PNG 与临时包副本 SHA 完全一致，说明未改正式文件。

## 作者仍需人工确认

1. 最终输出标签采用 `Land-surface forecast` 还是更窄的 `NDVI forecast`；
2. 最终图是否保留抽象 `b_h/r_h/ŷ`，或以后换成可追溯的冻结模型输出；
3. 作者是否采用推荐四列布局，或只在当前 2×2 PPT 上做最小修复；
4. 图内是否保留局部 residual 公式；若纸面过密，建议只保留
   `residual update` 与 `one direct query per horizon`；
5. 正式接入前重新检查 7.0 英寸纸面字号与 raster provenance。

