# Figure 2 编辑性与纸面 QA

## 可编辑性

- PASS：PPTX 不是整页截图，当前包含 208 个独立可编辑对象，并按 A/B/C/D 组织为 4 个 panel group；跨 panel 长连线保留在顶层。
- PASS：PPTX 包含 8 个独立图片对象；其余模块、格子、线条、箭头、文字和干预标记为原生可编辑对象。
- PASS：所有 PPTX 文本保持可编辑，统一使用 Arial。
- PASS：SVG 文字保留为 `<text>`，没有转路径。
- PASS：SVG 各模块使用有意义的对象/分组名称，如 `B_history_encoder_q`、`C_transition_delta`、`D_q2_primary_cut`。
- PASS：构建脚本可从继承素材完整重建 PPTX、SVG、PDF 和预览。
- PASS：原作者 PPTX 先复制为 `source/fig2_author_source_copy.pptx`，其 SHA 与正式源一致。

## 纸面尺寸

- 画布：7.0 × 4.05 英寸。
- 最小显式字号：7.5 pt。
- 300 dpi PNG：2100 × 1215 px。
- PDF：单页 7.0 × 4.05 英寸；包含可提取文字、174 组矢量 drawing 和 8 张可追溯 raster input。
- `qa/fig2_architecture_candidate_paperscale.png` 在 Letter 页面上按 7.0 英寸宽放置，用于直观看实际双栏大小。
- 中文结构审阅采用 `FIG2_STRUCTURE_REVIEW_ZH.md`；当前运行环境没有可用 CJK 字体，因此没有保留会出现缺字方块的中文栅格预览。

## 视觉审阅

- PASS：A→B→C→D 方向明确，不再存在旧版 2×2 回路。
- PASS：future weather 与 historical context 分离。
- PASS：主路径使用蓝/绿/紫；Q2 primary 使用橙色；Q3 使用紫色虚线；`T→I` 为小号灰色。
- PASS：没有箭头穿过模块正文。
- PASS：没有文字超出画布或被裁切。
- PASS：面板标题、数学符号、箭头和边框风格一致。
- PASS：paper-scale 下 panel 标题、核心模块、Q2/Q3 接口和 donor 三路输入可读。
- PASS：灰度预览中主链、Q2 cut 的交叉符号/虚线、Q3 虚线框和支持性标签仍可区分。

## 自动检查

详见 `qa/automated_qa.json`：

- `pptx_out_of_bounds = []`
- `pptx_min_explicit_font_pt = 7.5`
- `svg_xml_parse = true`
- `forbidden_terms_found = []`

## 已知但可接受的视觉选择

- normalized-mean future-weather strip 近似空白是冻结 control 的真实表示，不是缺图。
- `b_h`、`r_h` 和 `ŷ_{t+h}` 使用抽象格图，避免在没有可追溯定性预测缓存时伪造模型输出。
- 候选图高度为 4.05 英寸；接入正文前应由作者结合最终页流决定是否接受这一高度，不能通过缩小字号或负间距硬压。
