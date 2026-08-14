# TerraState Figure 2 视觉修订与可直接替换素材蓝图

更新时间：2026-07-28 UTC  
状态：施工指导与素材包；**不是最终 Figure 2 图稿**  
适用正文：当前 `paper/main.tex` 的 Sections 3.1–3.4 方法定义  
配套临时包：

```text
TerraState_AAAI27/figure_workspace/
TEMP_FIG2_REVISION_BUNDLE_20260728/
```

本文件不会修改当前 Figure 2、`main.tex`、模型、训练代码或实验记录。当前正式图保留为
历史草案。

---

## 0. 先用一分钟重新理解 Figure 2

Figure 2 只回答一个问题：

> **TerraState 在一次正常推理中，如何从历史信息构造显式预测状态，让未来天气只通过
> 共享转移推进该状态，再把状态读出为可切断的空间预测贡献？**

它不是：

- Figure 1 的“为什么要做、贡献是什么”；
- Figure 3 的“干预后数值发生了什么”；
- 完整训练流水线；
- teacher、future-state cache、KD 与训练阶段的总览；
- 对世界模型性质的结果证明。

读者在 5–10 秒内应该看到下面这条主链：

```text
历史EO + 过去天气 + 静态地理
        │
        ▼
qθ History encoder
        ├──────────────► context-only forecast b_h ───────────┐
        │                                                     │
        ▼                                                     │
Pρ State projector                                           │
        │                                                     │
        ▼                                                     │
predictive state z_t                                         │
        │                                                     │
        ▼                                                     │
shared weather-conditioned residual transition Tψ            │
        │                                                     │
        ▼                                                     │
evolved state z_{t+h}                                        │
        │                                                     │
        ▼                                                     │
Oω State readout → spatial contribution r_h ───► (+) ◄────────┘
                                                    │
                                                    ▼
                                  land-surface forecast ŷ_{t+h}
```

另有两条**测试时接口**：

```text
Q3：actual / matched donor / normalized mean
    只替换 Tψ 上游的 future-weather input

Q2 primary：在 r_h → (+) 之间切断，remove r_h (α=0)
Q2 support：把 Tψ 替换为 identity，T→I
```

这就是整张图的全部逻辑。其余视觉元素只服务于让这条逻辑更容易读。

---

## 1. 当前 Figure 2 是什么

当前论文实际引用的是：

```text
TerraState_AAAI27/paper/figures/
terrastate_architecture_fig2_author_slide1.pdf
```

可编辑源与预览：

```text
TerraState_AAAI27/paper/figures/
terrastate_architecture_fig2_author_slide1.pptx
terrastate_architecture_fig2_author_slide1.png
```

临时包内提供了只读副本：

```text
current/terrastate_architecture_fig2_author_slide1.pptx
current/terrastate_architecture_fig2_author_slide1.pdf
current/terrastate_architecture_fig2_author_slide1.png
current/current_fig2_annotated_issues.png
```

当前图的基本布局是：

```text
┌────────────────────┬─────────────────────────────────────┐
│ (a) context        │ (b) history encoding/state          │
│                    │                                     │
├────────────────────┼─────────────────────────────────────┤
│ (d) readout/output │ (c) weather-conditioned dynamics    │
└────────────────────┴─────────────────────────────────────┘
```

方法路径按顺时针 `a→b→c→d` 绕行，但页面自然阅读顺序是
`a→b→d→c`。这使主链需要靠长回折箭头维持，缩到 AAAI 双栏后不容易一次看懂。

---

## 2. 当前图必须修复的事实问题

这些不是个人审美，而是当前图与冻结实现/正文不一致的地方。

### 2.1 Future weather 不能位于 historical context 内

当前：

```text
Future meteorological forcing
```

与历史 EO、历史天气、静态地理一起装在 `(a) Multimodal context` 中，并由总箭头进入
history encoder。视觉上会被理解为未来天气进入 `qθ`。

正确：

```text
qθ输入：
historical EO + past meteorological observations + static geography

future weather：
独立放置，只进入 future-weather encoder / Tψ
```

### 2.2 删除 weather tokens × state tokens 的乘号

实际实现不是逐元素乘法、attention product 或 gate。正确结构为：

```text
d_h = weather-prefix encoder(u_{t+1:t+h})
E_g(g)_i = patch-wise geography
E_h(h) = horizon code

c_{h,i} = condition fusion([d_h; E_g(g)_i; E_h(h)])

z_{t+h,i}
= z_{t,i} + Δψ([LN(z_{t,i}); c_{h,i}])
```

视觉上使用：

```text
weather prefix ┐
patch-wise geo ├→ concat / condition fusion → c_{h,i}
horizon code   ┘

z_t + residual update → z_{t+h}
```

### 2.3 必须画出 residual skip

当前 shared transition 近似黑盒替换。正确图必须看见：

```text
z_t ───────────────────────┐
 │                         ▼
 └→ LN + condition → Δψ → (+) → z_{t+h}
```

### 2.4 不要画递归 rollout

每个时距 `h` 都从同一个 `z_t` 做一次 direct query：

```text
z_t ──T(u_{t+1:t+1})──► z_{t+1}
z_t ──T(u_{t+1:t+5})──► z_{t+5}
z_t ──T(u_{t+1:t+20})─► z_{t+20}
```

图中不画：

```text
z_t → z_{t+1} → z_{t+2} → … → z_{t+h}
```

只需在 `Tψ` 下方写：

```text
one direct query per horizon
```

### 2.5 `Oω` 后必须是空间 raster contribution

当前 `State contribution` 仍是 token cube。实际：

```text
z_{t+h} tokens
→ Oω local 4×4 patch readout
→ unpatchify
→ spatial forecast contribution r_h
```

因此：

- `z_t`、`z_{t+h}` 可以使用抽象 token grid；
- `r_h` 必须画成空间栅格或明确的 patch-unpatchified raster；
- 不要把 `r_h` 再画成 latent token。

### 2.6 Q2 主切点必须精确

主要干预：

```text
r_h ──X──► (+)
remove r_h (α=0)
```

支持性干预：

```text
T→I
```

不要让 `T→I` 和 state removal 看起来同等重要。

### 2.7 Q3 替换发生在 transition 上游

三路：

```text
actual future weather
matched-donor weather
normalized-mean weather
```

汇入**同一个** future-weather encoder 与 shared transition。替换时历史 EO、`b_h`、
`z_t`、静态地理、horizon、readout 和 ground truth 都保持固定。

图中可以写：

```text
Q3 weather intervention
actual / matched donor / normalized mean
```

不要写：

```text
causal intervention
counterfactual correctness
extreme-specific response
```

### 2.8 删除 `D3 Vegetation forecast`

`D3` 不是论文方法术语。改成：

```text
Land-surface forecast ŷ_{t+h}
```

若正文最终明确只强调 NDVI，可写：

```text
NDVI forecast ŷ_{t+h}
```

当前最稳妥的是 `Land-surface forecast`。

---

## 3. 推荐的新布局：四个竖向阶段，严格从左到右

配套线框：

```text
target_blueprint/fig2_target_wireframe.png
target_blueprint/fig2_target_wireframe.svg
```

建议成图尺寸：

```text
7.0 in × 3.15–3.30 in
AAAI双栏通栏
```

四个大块相对宽度：

```text
A Historical context      18%
B Predictive state        25%
C Shared transition       32%
D Readout & closure       25%
```

建议坐标，以 7.0 × 3.25 英寸画布为参考：

```text
A：x = 0.00–1.28 in
B：x = 1.28–3.06 in
C：x = 3.06–5.31 in
D：x = 5.31–7.00 in
```

不再使用 2×2 顺时针回路。原因不是“横排更时尚”，而是 Figure 2 的唯一任务是让读者
跟随一次推理主链，严格左到右最可靠。

---

## 4. 四个大块内部如何放置小块

## 4.1 A — Historical context

标题：

```text
(a) Historical context
（a）历史上下文
```

内部按照下列层级放置：

```text
┌──────────────────────┐
│ Historical EO        │  高度约42%
│ [三帧真实RGB strip]   │
├──────────┬───────────┤
│ Past     │ Static    │  高度约24%
│ weather  │ geography │
├──────────┴───────────┤
│ Valid / clear mask   │  高度约18%
└──────────────────────┘
```

可直接放入：

```text
copy_ready/panel_a_historical_context/history_rgb_strip.png
copy_ready/panel_a_historical_context/past_weather_context.png
copy_ready/panel_a_historical_context/dem_hillshade.png
copy_ready/panel_a_historical_context/landcover_esa_worldcover.png
copy_ready/panel_a_historical_context/history_clear_mask.png
```

建议用法：

- `history_rgb_strip.png`：占 A 区最上方 45%，保持 3:1 横向条带；
- `past_weather_context.png`：左下，裁掉不必要白边，不改变曲线；
- `dem_hillshade.png` 与 `landcover_esa_worldcover.png`：二选一即可；同时放会拥挤；
- `history_clear_mask.png`：只需 0.18–0.25 英寸小图，旁边写 `valid / clear mask`；
- 不需要另外从网上下载 EO 输入，这些已经来自本项目的真实 minicube。

必须删除：

```text
Future meteorological forcing
```

它必须移到 C 区。

直接可复制英文：

```text
Historical EO
Past weather
Static geography
Valid / clear mask
History-only inputs
```

中文施工提示：

```text
历史EO
过去天气
静态地理
有效/晴空掩膜
仅历史输入
```

---

## 4.2 B — Predictive-state construction

标题：

```text
(b) Predictive state
（b）预测状态
```

内部层级：

```text
Historical context
       │
       ▼
qθ History encoder
       ├──────────────► Context-only forecast b_h
       │
       ▼
Pρ State projector
       │
       ▼
Predictive state z_t
```

推荐在 B 区内让 `z_t` 比 `qθ/Pρ` 更醒目，因为本文特色不是 backbone，而是显式可操作
状态。

可直接放入：

```text
copy_ready/panel_b_state_construction/
history_encoder_state_split.svg
history_encoder_state_split.png

copy_ready/panel_b_state_construction/
zt_predictive_state.svg
zt_predictive_state.png
```

如果需要 context-only forecast 的图像符号，可使用：

```text
copy_ready/panel_b_state_construction/
context_forecast_bh_SCHEMATIC.svg
context_forecast_bh_SCHEMATIC.png
```

注意：这个 `b_h` 文件是明确标记的抽象示意，不是模型输出。正式图中若没有可追溯
`b_h` 数组，最好继续用抽象栅格，而不是把 observed future 冒充成 `b_h`。

直接可复制英文：

```text
History encoder qθ
State projector Pρ
Predictive state z_t
Context-only forecast b_h
```

不建议继续用：

```text
Tokenization
Context features
State-construction branch
```

这些词不是错误，但会分散读者对 `qθ→Pρ→z_t` 和 `b_h` 分叉的注意。

---

## 4.3 C — Shared weather-conditioned transition

标题：

```text
(c) Shared weather-conditioned transition
（c）共享天气条件转移
```

这个区块是整张图的信息中心，应是四块中最宽的。

内部按照四层放：

```text
第一层：Q3 future-weather selector
actual / matched donor / normalized mean
                 │
                 ▼
第二层：weather-prefix encoder d_h

第三层：
weather prefix d_h ┐
patch-wise E_g(g)_i├→ condition fusion → c_{h,i}
horizon E_h(h)     ┘

第四层：
z_t ─────────────────────────────┐
 │                               ▼
 └→ LN(z_t) + c_{h,i} → Δψ → (+) → z_{t+h}
```

可直接放入的真实天气图：

```text
copy_ready/panel_c_transition/
actual_future_weather_full24.png
matched_donor_weather_full24.png
normalized_mean_weather_full24.png
q3_three_weather_arms_real.png
```

推荐：

- 空间足够时使用 `q3_three_weather_arms_real.png`；
- 空间不足时使用三个 `*_full24.png` 作为三条薄 strip；
- 三条图必须保持相同宽度和色标，不单独拉伸；
- `normalized mean` 在标准化 full24 空间为零，因此图像接近中性色是正确的。

可直接放入的可编辑机制模块：

```text
copy_ready/panel_c_transition/condition_fusion_chi.svg
copy_ready/panel_c_transition/residual_direct_transition.svg
copy_ready/panel_c_transition/zth_evolved_state.svg
copy_ready/panel_c_transition/q3_weather_selector_schematic.svg
copy_ready/panel_c_transition/q2_support_T_to_identity.svg
```

所有 SVG 都保留文字和独立矢量对象；对应目录内同时有 300 dpi PNG，可直接拖进 PPT。

直接可复制英文：

```text
Actual future weather
Matched-donor weather
Normalized-mean weather
Weather-prefix encoder
Patch-wise geography
Horizon code
Condition fusion
Shared residual transition Tψ
Evolved predictive state z_{t+h}
One direct query per horizon
Q3 weather intervention
```

唯一建议保留的局部公式：

```text
z_{t+h,i} = z_{t,i}
            + Δψ([LN(z_{t,i}); c_{h,i}])
```

若最终图过密，可以只写：

```text
residual update
one direct query per horizon
```

不要同时塞入完整公式和长解释。

---

## 4.4 D — State readout and forecast closure

标题：

```text
(d) Readout & closure
（d）状态读出与预测闭合
```

内部结构：

```text
z_{t+h}
   │
   ▼
Oω State readout
   │
   ▼
spatial contribution r_h ──X──┐
                              ▼
context-only forecast b_h ───►(+)──► forecast ŷ_{t+h}
```

Q2 切点放在：

```text
r_h → (+)
```

可直接放入：

```text
copy_ready/panel_d_readout_closure/
readout_additive_closure.svg
readout_additive_closure.png

copy_ready/panel_d_readout_closure/
q2_remove_rh_cut.svg
q2_remove_rh_cut.png
```

抽象栅格：

```text
copy_ready/panel_d_readout_closure/
state_contribution_rh_SCHEMATIC.svg
state_contribution_rh_SCHEMATIC.png

copy_ready/panel_d_readout_closure/
land_surface_forecast_yhat_SCHEMATIC.svg
land_surface_forecast_yhat_SCHEMATIC.png
```

这些成品可以直接替换当前 token cube 和 D3 预测栈，但必须知道：

- 它们是原创抽象栅格；
- 它们不是冻结模型输出；
- 文件中保留了 `SCHEMATIC` 小标识，防止被误认为定性结果；
- 如果作者以后取得真实 `r_h` 和 `ŷ`，应按相同尺寸直接替换。

直接可复制英文：

```text
State readout Oω
Spatial state contribution r_h
Context-only forecast b_h
Land-surface forecast ŷ_{t+h}
Q2 primary: remove r_h (α=0)
Q2 supporting: T→I
```

闭合公式：

```text
ŷ_{t+h} = b_h + r_h
```

---

## 5. 每条箭头具体从哪里到哪里

正常推理使用实线：

```text
A historical context → B qθ
qθ → Pρ
Pρ → z_t
qθ → b_h
z_t → Tψ residual transition
future-weather encoder → condition fusion
patch-wise geography → condition fusion
horizon code → condition fusion
condition fusion c_{h,i} → Tψ
Tψ → z_{t+h}
z_{t+h} → Oω
Oω → spatial r_h
r_h → addition
b_h → addition
addition → ŷ_{t+h}
```

Q3 使用紫色虚线：

```text
actual / matched donor / normalized mean
→ 同一个 future-weather encoder
→ 同一个 Tψ
```

Q2 primary 使用橙红切断符号：

```text
r_h ──X──► addition
```

Q2 support 使用灰色小标：

```text
T→I support
```

不要：

- 让 future weather 的箭头接触 `qθ` 外框；
- 让 Q3 虚线从 `z_{t+h}` 或 `Oω` 下游进入；
- 用箭头穿过模块文字；
- 从 `b_h` 连到 `Tψ`；
- 把 observed future 连入推理路径。

---

## 6. 当前 PPTX 的“最小修改路线”

如果不从空白画布重排，打开：

```text
current/terrastate_architecture_fig2_author_slide1.pptx
```

按下面顺序修改最省返工：

1. 在 `(a)` 中删掉 `Future meteorological forcing` 的两张图片与标签；
2. 把 `(a)` 标题改为 `Historical context`；
3. 将 `(c)` 和 `(d)` 的位置交换，形成自然的 `a,b,c,d` 阅读顺序；
4. 把 C 区三路天气放到 transition 上游；
5. 删除 weather/state 中间的乘号；
6. 插入 `condition_fusion_chi.svg`；
7. 插入 `residual_direct_transition.svg`，代替当前 shared-transition 内部；
8. 把当前 `State contribution` token cube 替换成
   `state_contribution_rh_SCHEMATIC.png` 或真实 `r_h`；
9. 把 Q2 切点移动到 `r_h→(+)`；
10. 将 `D3 Vegetation forecast` 改为 `Land-surface forecast ŷ_{t+h}`；
11. 删除外圈长回折箭头，改成局部短箭头；
12. 最后把字体统一成 Arial、Helvetica 或 Aptos，正文不小于最终纸面 7.5–8 pt。

这条路线能修复事实，但仍会保留 2×2 结构。若作者愿意移动大区，推荐直接采用第 3 节
四列布局，阅读成本更低。

---

## 7. 哪些图片是真实数据，哪些只是抽象符号

### 7.1 已经是真实项目数据，可直接用

```text
Historical RGB strip
Historical NDVI
Valid / clear mask
Past precipitation/temperature curves
DEM elevation / hillshade
ESA WorldCover land cover
Actual future-weather full24 strip
Matched-donor future-weather full24 strip
Normalized-mean future-weather full24 strip
```

这些来自同一个已经选择并记录 provenance 的 OOD-t minicube，或其冻结 matched donor。

### 7.2 可以抽象画，不需要模型输出

```text
qθ encoder
Pρ projector
z_t token tensor
condition fusion c_{h,i}
residual transition
z_{t+h} token tensor
Oω readout
addition node
Q2 cut
Q3 selector
horizon / geography / weather icons
```

### 7.3 目前没有可追溯真实模型输出

```text
b_h context-only forecast
r_h state contribution
ŷ_{t+h} TerraState forecast
```

临时包提供的同名 `SCHEMATIC` 文件只是为了让你能直接放置视觉成品，不等于冻结模型
定性案例。

### 7.4 绝对不能冒充模型输出

目录：

```text
copy_ready/reference_only_not_model_output/
```

其中：

```text
observed_future_rgb_step20_REFERENCE_ONLY.png
observed_future_ndvi_step20_REFERENCE_ONLY.png
```

是真实未来观测 target，不是 `b_h`、`r_h` 或 `ŷ`。除非图中明确标注
`Observed future (reference)` 并且不连接推理箭头，否则不要放入 Figure 2。

---

## 8. 不手搓素材的优先获取路线

### 第一优先：直接用本临时包

先看：

```text
qa/FIG2_ASSET_CONTACT_SHEET.png
```

找到需要的成图后，从 `copy_ready/` 对应子目录复制 PNG 或 SVG。

### 第二优先：从本项目的同一 minicube 导出

如果需要换案例，必须保持：

```text
同一AOI
同一裁剪范围
同一历史/未来时间定义
历史输入与天气输入可追溯
```

建议资产类别：

```text
historical RGB / NDVI
valid or clear mask
DEM
ESA WorldCover land cover
past weather
actual future weather
matched-donor future weather
normalized-mean future weather
```

### 第三优先：只为“非模型视觉说明”找官方素材

外部图只能用于通用 EO 场景、图标或公开地理底图，不得替代 TerraState 输入或输出。

推荐官方入口：

- Copernicus Browser：<https://dataspace.copernicus.eu/browser/>
- Copernicus Browser 使用说明：
  <https://documentation.dataspace.copernicus.eu/Applications/Browser.html>
- Sentinel-2 官方介绍：
  <https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2/>
- ESA WorldCover 数据：
  <https://esa-worldcover.org/en/data-access>
- Copernicus DEM：
  <https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM>
- Material Symbols SVG/PNG：
  <https://developers.google.com/fonts/docs/material_symbols>

推荐搜索词：

```text
Sentinel-2 L2A agricultural fields cloud mask
Sentinel-2 NDVI cropland time series
Copernicus DEM hillshade agriculture
ESA WorldCover cropland 10 m
weather forcing time-series icon SVG
state transition residual block diagram
patch token grid SVG
```

中文搜索：

```text
哨兵二号 农田 真彩色 时间序列
遥感 云掩膜 示例
DEM 山体阴影 农业区
ESA WorldCover 耕地
天气时间序列 矢量图标
残差状态转移 示意图
```

搜索后不要直接截图论文图形内容。优先下载官方数据或自行在官方 Browser 导出目标区域。
记录 URL、许可、日期与 AOI。

---

## 9. 文献与 AAAI 图应该借鉴什么

### 9.1 EO-WM

本地：

```text
TerraState_AAAI27/literature/eo_wm_2606.27277.pdf
```

在线：

<https://arxiv.org/abs/2606.27277>

可以借鉴：

- 真实 EO 输入、天气条件、核心机制与输出交替出现；
- 大图先给完整输入—机制—输出，再在局部展示关键条件路径；
- 图片承担场景身份，模块承担方法逻辑；
- 不把所有实现细节塞进一个网络盒子。

不照搬：

- EO-WM 的 climatology / anomaly / cumulative stress 分解；
- diffusion/VAE/DiT 模块；
- 它的行为 benchmark 布局；
- 任何原图中的图块、符号、颜色组合或具体箭头。

TerraState 必须额外突出：

```text
history-only z_t
future weather exclusive route through Tψ
explicit spatial state contribution r_h
Q2 r_h cut
Q3 weather replacement
```

### 9.2 本地 AAAI anchors

推荐只看布局：

```text
literature/aaai_figure_anchors/aaai25_drive_occworld_page_03.png
literature/aaai_figure_anchors/aaai26_sparseworld_page_03.png
literature/aaai_figure_anchors/aaai25_glam_page_03.png
```

重点观察：

- 输入图片组如何控制在 15–25% 宽度；
- 核心机制如何占据最大宽度；
- 输出图片如何闭合主路径；
- stage header、短箭头和分支如何避免穿字。

不要裁取 anchors 中任何图片或网络图形。

---

## 10. `示例/ICLR.pptx` 具体哪些对象可复用

源文件：

```text
TerraState_AAAI27/示例/ICLR.pptx
```

该文件的科学内容是 EEG，不能直接作为 TerraState 图像素材；可以复制其原生 PPT 图片框、
对齐、分组和短箭头。

### 第 1 页

可复制的三帧图片框：

```text
Raw EEG Data
x ≈ 0.65 in
y ≈ 0.57 / 1.56 / 2.52 in
每张约 1.42 × 0.83 in
```

用法：

```text
复制框与分组
删除 EEG 波形
替换成 history_rgb_strip.png 的三帧
压缩为 A 区顶端的历史EO组
```

可复制的第二组三行框：

```text
Augmentation
x ≈ 2.64 in
y ≈ 0.61 / 1.60 / 2.55 in
每张约 1.42 × 0.79 in
```

用法：

```text
改成 actual / matched donor / normalized mean
放入 C 区 Q3 selector
每个框替换成对应 full24 weather strip
```

可复制的 token 小方块：

```text
x ≈ 4.6–7.9 in
y ≈ 0.9–5.9 in
```

用法：

```text
只保留4×4或5×6网格分组方式
分别改成 z_t 与 z_{t+h}
删除 Q/K/V、FFN、Time2Freq、Res 等 EEG 字段
```

### 第 6 页

三张 sibling cards：

```text
x ≈ 2.33 / 3.51 / 4.68 in
y ≈ 3.36 in
每张约 1.14–1.16 × 0.58 in
```

用法：

```text
改成 Historical EO / Past weather / Static geography
用于 A 区输入小卡
```

### 不使用 ICLR.pptx 内的媒体

```text
EEG波形
雷达图
模型比较图例
灯泡、对话框、checklist位图
```

本包 `copy_ready/icons/` 已提供更干净的原创 SVG/PNG 图标。

---

## 11. `示例/fig2——2.pptx` 与当前图如何使用

```text
TerraState_AAAI27/示例/fig2——2.pptx
```

它适合作为对象来源，而不适合作为方法事实来源。

可复用：

- 历史 EO 图片组的框与裁剪；
- panel 外框；
- 状态 token 的独立小方块；
- 短箭头、加号和简单模块框；
- current author-slide PPT 中已经整理好的图片。

需要删除或替换：

- 来历不清的 EO、地形、天气截图；
- future weather 位于历史输入边界的关系；
- multiplication；
- token-form `r_h`；
- D3 标签；
- 长回折箭头。

为了方便编辑，本包已把当前 PPTX 原样复制到：

```text
current/terrastate_architecture_fig2_author_slide1.pptx
```

应在副本上修改，不覆盖论文当前文件，直到作者正式批准。

---

## 12. 图片尺寸、裁剪与分辨率

### 真实遥感与地图图块

推荐：

```text
单帧：至少 512 × 512 px
三帧strip：至少 1500 × 500 px
论文中显示宽度：0.7–1.2 in
裁剪：同一AOI、同一比例、最近邻或无额外重采样
```

不要：

- 使用 AI 超分；
- 每帧单独改变 RGB 拉伸；
- 为了“更漂亮”改变空间范围；
- 把 target 当 forecast。

### 天气条带

推荐：

```text
单条：至少 900 × 240 px
三路组合：至少 1800 × 600 px
论文中每条高度：0.10–0.18 in
```

实际提供的 PNG 均按 300 dpi 导出；像素尺寸写在：

```text
provenance/ASSET_MANIFEST.json
```

### 抽象模块

优先使用 SVG。需要在 PowerPoint 里快速替换时使用同名 PNG。SVG：

- 文字未转路径；
- 模块保留矢量对象；
- 放大不会模糊；
- 可在 Illustrator、Inkscape 或支持 SVG 的 PowerPoint 中编辑。

---

## 13. 图内最终中英文短文案

### Panel A

```text
(a) Historical context
（a）历史上下文

Historical EO
历史EO

Past weather
过去天气

Static geography
静态地理

Valid / clear mask
有效/晴空掩膜
```

### Panel B

```text
(b) Predictive state
（b）预测状态

History encoder qθ
历史编码器 qθ

State projector Pρ
状态投影器 Pρ

Predictive state z_t
预测状态 z_t

Context-only forecast b_h
仅上下文预测 b_h
```

### Panel C

```text
(c) Shared weather-conditioned transition
（c）共享天气条件转移

Actual future weather
真实未来天气

Matched-donor weather
匹配供体天气

Normalized-mean weather
归一化均值天气

Weather-prefix encoder
天气前缀编码器

Patch-wise geography
逐patch地理条件

Horizon code
时距编码

Condition fusion c_{h,i}
条件融合 c_{h,i}

Shared residual transition Tψ
共享残差转移 Tψ

Evolved predictive state z_{t+h}
演化后的预测状态 z_{t+h}

One direct query per horizon
每个时距一次直接查询
```

### Panel D

```text
(d) Readout & closure
（d）读出与闭合

State readout Oω
状态读出 Oω

Spatial state contribution r_h
空间状态贡献 r_h

Land-surface forecast ŷ_{t+h}
地表预测 ŷ_{t+h}

Q2 primary: remove r_h (α=0)
Q2主要干预：移除 r_h（α=0）

Q2 supporting: T→I
Q2支持性干预：T→I
```

---

## 14. Caption 草案

### English

> **TerraState inference architecture and intervention interfaces.** Historical
> EO, past weather, and static geography produce a context-only forecast
> \(b_h\) and history-only predictive state \(z_t\). For each horizon, the same
> state is directly advanced by a shared residual transition conditioned on
> the corresponding future-weather prefix, patch-wise geography, and horizon
> code. The state readout yields a spatial contribution \(r_h\), which closes
> the forecast as \(\widehat y_{t+h}=b_h+r_h\). Q2 removes \(r_h\) (primary) or
> sets \(T\) to the identity (supporting); Q3 replaces only future weather with
> matched-donor or normalized-mean controls.

### 中文

> **TerraState 的推理架构与干预接口。** 历史 EO、过去天气和静态地理共同产生仅上下文
> 预测 \(b_h\) 与仅由历史构造的预测状态 \(z_t\)。对每个预测时距，共享残差转移使用对应
> 的未来天气前缀、逐 patch 地理条件和时距编码，从同一个 \(z_t\) 直接得到
> \(z_{t+h}\)。状态读出生成空间贡献 \(r_h\)，并以
> \(\widehat y_{t+h}=b_h+r_h\) 闭合预测。Q2 的主要干预移除 \(r_h\)，支持性干预将
> \(T\) 替换为恒等映射；Q3 只把未来天气替换为 matched-donor 或 normalized-mean
> 对照。

Caption 不宣称结果，不使用 `causal`、`counterfactual correctness`、Q4、composition、
SOTA 或 extreme-specific enhancement。

---

## 15. 与正文术语的一致性检查

必须保持：

```text
qθ：history operator / history encoder
Pρ：state projector
z_t：history-only predictive state
Tψ：shared weather-conditioned residual transition
z_{t+h}：evolved / advanced predictive state
Oω：state readout
b_h：context-only forecast
r_h：spatial state contribution
ŷ_{t+h}=b_h+r_h：standard inference closure
Q2 primary：remove r_h (α=0)
Q2 support：T→I
Q3：actual / matched donor / normalized mean
```

必须避免：

```text
future weather进入qθ
state/weather multiplication
recursive rollout
r_h仍是latent token
normalized mean = no weather
donor = random donor
state = complete physical state
Q2 proves transition necessity
Q3 causal response
```

训练期 teacher、future-state target 与三项训练目标留在正文 Section 3.3，不进入本版
Figure 2。当前方法审计明确允许 Figure 2 只画 inference path 和 post-training
intervention interfaces。

---

## 16. 最后施工顺序

1. 打开 `qa/FIG2_ASSET_CONTACT_SHEET.png` 选素材；
2. 打开 `target_blueprint/fig2_target_wireframe.png` 看四列关系；
3. 复制 `current/*.pptx` 作为可编辑起点；
4. 先修 future-weather 边界；
5. 再修 condition fusion 与 residual transition；
6. 再把 `r_h` 改成 raster；
7. 最后放 Q2/Q3 接口；
8. 删除长箭头和冗余 stage 装饰；
9. 输出 7.0 英寸宽 PDF 检查 7.5–8 pt 字号；
10. 对照第 15 节逐项审计。

如果只能完成一半，优先级为：

```text
方法事实正确
> future weather exclusive route
> r_h/addition/Q2切点
> condition fusion + residual update
> 真实遥感视觉
> 装饰与配色
```

