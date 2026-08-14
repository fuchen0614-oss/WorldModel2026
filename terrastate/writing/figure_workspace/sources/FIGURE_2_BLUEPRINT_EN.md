# Figure 2 Construction Blueprint: Continuous TerraState Architecture

> Status: this document supersedes the previous Figure 2 blueprint. Earlier rendered figures are archival drafts and are no longer construction references.

## 1. Purpose

Figure 2 answers one technical question:

> **How does TerraState construct an explicit predictive state from multimodal history, evolve it with future weather through shared dynamics, and close the state contribution into the final vegetation forecast?**

Its role is distinct from the other main figures:

```text
Figure 1: why a testable EO world model is needed and what evidence is required
Figure 2: how TerraState implements that model
Figure 3: whether the frozen experimental results support the claims
```

Figure 2 must therefore be one continuous left-to-right method diagram, not a collection of engineering stages or disconnected training schematics.

## 2. Visual design language

Adopt the useful design principles of the supplied weather-model figures and EO-WM Figure 2:

- a continuous stage ribbon;
- real input imagery on the left;
- expanded visual modules in the center;
- real forecast imagery on the right;
- one block feeding the next;
- one continuous inference path with no training rail;
- short labels instead of explanatory paragraphs.

Use the colored partitioning of the supplied graph-memory figure only as a secondary reference. Avoid hand-drawn borders, decorative icons, dense formulas, and branded model logos.

## 3. Canvas and geometry

- Full AAAI double-column width.
- Recommended size: `7.0 × 3.25 in`.
- Acceptable height: `3.15–3.35 in`.
- No title inside the artwork; use the LaTeX caption.
- English text only in the final artwork.

### Horizontal regions

| Region | Header | Width |
|---|---|---:|
| (a) | Multimodal context | 19% |
| (b) | History encoding & state construction | 25% |
| (c) | Weather-conditioned shared dynamics | 31% |
| (d) | State readout & forecast | 25% |

Keep the regions adjacent. Separate them with light background tones or thin dividers while preserving one continuous inference arrow.

### Vertical allocation

| Band | Height |
|---|---:|
| Continuous stage ribbon | 9% |
| Main inference architecture | 84% |
| Legend and whitespace | 7% |

Figure 2 has no lower training rail. The frozen teacher, future-state target, losses, and stage schedule belong in the method text or appendix.

### 3.1 Explicit hierarchy: four major regions and their sub-blocks

Figure 2 contains exactly **four major regions**. Draw the four large background containers first, then place the following sub-blocks inside them:

```text
Figure 2
├── Region A: Multimodal context
│   ├── A1 historical-EO image group
│   ├── A2 historical-environment image group
│   ├── A3 static-geography image group
│   └── A4 future-weather strip
├── Region B: History encoding & state construction
│   ├── B1 history encoder q
│   ├── B2 state branch: context features → P → z_t
│   └── B3 context-forecast branch: b_h
├── Region C: Weather-conditioned shared dynamics
│   ├── C1 conditioning inputs: u_{t:t+h}, g, h
│   ├── C2 shared transition T
│   ├── C3 evolved state z_{t+h}
│   └── C4 small weather-intervention port
└── Region D: State readout & forecast
    ├── D1 readout branch: O → r_h
    ├── D2 forecast fusion: b_h + r_h
    ├── D3 final forecast-image group
    └── D4 small state-path intervention port
```

The distinction is strict:

- major region = large tinted background with a top header;
- sub-block = rounded white box, image group, or network module inside a region;
- visual element = image, tensor glyph, curve, or icon inside a sub-block;
- intervention = a tiny port attached to an arrow, never a separate major module;

For example, the DEM is one image inside A3, temperature/precipitation/radiation are three visual channels inside A4, and \(h=5,10,20\) are three images inside D3.

## 4. Global wireframe

```text
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ (a) Multimodal context │ (b) History encoding & state │ (c) Weather-conditioned │ (d) Readout │
│                        │         construction          │     shared dynamics      │   & forecast │
│                        │                               │                          │              │
│ Past EO sequence ─────▶│ q ──┬──▶ context features ─▶ P ─▶ z_t ─▶ shared T ─▶ z_t+h ─▶ O ─▶ r_h ─┐
│ mask / past context ──▶│     │                              ▲                                   │
│ static geography ─────▶│     └──────── context forecast b_h ┼───────────────────────────────────┼─▶ ⊕ ─▶ ŷ
│                        │                                    │                                   │
│ Future weather strip ──────────────────────────────────────┘                                   │
│ geography + horizon h ─────────────────────────────────────┘                                   │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

The only primary reading order is:

```text
inputs → history encoding → current state → weather-driven transition
       → evolved state → state readout → forecast closure
```

### 4.1 Bilingual construction annotations for the illustrator

Use the following convention while drawing:

```text
English label retained in the final paper figure
中文施工说明（推荐插入的图片或视觉元素）
```

The Chinese line is an illustrator note and must be removed from the final paper artwork.

For the fully expanded bilingual wireframe set, use Sections 4.2–4.8 of `FIGURE_2_BLUEPRINT_ZH.md`: Section 4.3 gives the cross-region layout and Sections 4.4–4.7 expand Regions A–D.

| Final English label | 中文施工说明与插图建议 |
|---|---|
| `Historical Earth observations` | 历史地球观测（同一地块3–4帧 Sentinel-2 RGB/NDVI，按 \(t-3,\ldots,t\) 叠放） |
| `Historical environmental context` | 历史环境上下文（云/有效像素 mask + 简短历史天气条带） |
| `Static geographic attributes` | 静态地理属性（土地覆盖图 + DEM地形图；没有真实DEM时用简洁等高线） |
| `Future meteorological forcing` | 未来气象驱动（温度曲线 + 降水柱 + 辐射色带） |
| `History encoder q` | 历史编码器（3–4层紧凑网络块或 patch-to-token 示意） |
| `Context features` | 上下文特征（薄型彩色 token 方块墙） |
| `State projector P` | 状态投影器（梯形漏斗或两层小型MLP） |
| `History-only predictive state z_t` | 仅由历史形成的状态（4×4/6×6抽象张量格 + 小时钟，不画成地图） |
| `Context-only forecasts b_{1:H}` | 上下文预测（浅蓝预测缩略图序列或薄输出带） |
| `Geographic context g` | 地理上下文（土地覆盖/DEM小图标） |
| `Forecast horizon h` | 预测时距（小时钟或 \(h=1,\ldots,H\) 刻度） |
| `Shared transition T` | 共享转移（状态token与天气token交互的简化注意力/门控网格） |
| `Evolved predictive state z_{t+h}` | 演化后状态（与 \(z_t\) 同形，内部颜色轻微变化） |
| `Weather intervention` | 天气干预接口（`actual / matched donor / normalized mean` 三选一端口） |
| `State readout O` | 状态读出器（窄型解码器或漏斗网络） |
| `State contribution r_h` | 状态贡献（真实零中心发散色贡献图；没有时保留空图槽） |
| `Forecast fusion` | 预测融合（圆形加号 + \(\widehat y_{t+h}=b_h+r_h\)） |
| `Vegetation forecast` | 植被预测（同一地块 \(h=5,10,20\) 的真实NDVI预测图） |
| `State-path intervention` | 状态路径干预（位于 \(r_h\rightarrow\oplus\) 上的可断开小开关） |

## 5. Computational contract

The artwork must encode the implemented computation:

\[
z_t=P(q(\mathrm{history})), \qquad
b_h=q_{\mathrm{forecast}}(\mathrm{history}),
\]

\[
z_{t+h}=T(z_t,u_{t:t+h},g,h), \qquad
r_h=O(z_{t+h}),
\]

\[
\widehat y_{t+h}=b_h+r_h.
\]

The structural constraints are:

1. \(z_t\) reads historical information only.
2. \(b_h\) is a context-only forecast.
3. Future weather reaches the forecast only through \(T\).
4. \(T\) is shared across queried forecast horizons.
5. \(O\) maps the evolved state to a forecast contribution.
6. The final prediction is the sum of context and state contributions.

Do not depict recurrent rollout or temporal composition. The implemented transition is a shared horizon-conditioned query, not a demonstrated composition operator.

## 6. Region (a): Multimodal context

### Visual contents

Arrange three compact input groups vertically:

1. **Historical Earth observations**: three or four overlapping real EO/NDVI frames marked \(t-3,\ldots,t\).
2. **Historical environmental context**: a real valid/cloud mask and a short past-weather strip.
3. **Static geographic attributes**: land-cover and terrain/geography thumbnails.

Place **Future meteorological forcing** on a separate lower strip. It must bypass \(q\), \(P\), and \(z_t\), and terminate only at \(T\).

### Copy-ready labels

- `(a) Multimodal context`
- `Historical Earth observations`
- `Historical environmental context`
- `Static geographic attributes`
- `Future meteorological forcing`
- `past EO`
- `valid / cloud mask`
- `past weather`
- `land cover`
- `terrain`
- `u_{t:t+h}`

## 7. Region (b): History encoding & state construction

### Main structure

```text
historical inputs
       ↓
History encoder q
   ┌───┴─────────────────────┐
   │                         │
   ▼                         ▼
context forecasts b_1:H   context features
                             │
                             ▼
                      State projector P
                             │
                             ▼
             History-only predictive state z_t
```

This is the only major branch in the figure. Use a thin upper path for \(b_{1:H}\) and a thick central path through \(P\) and \(z_t\).

### Visual encoding

- Draw \(q\) as a compact stack of encoder/token blocks, not a layer-by-layer PVT diagram.
- Draw context features as a thin token wall.
- Draw \(P\) as a small trapezoid or narrow MLP.
- Draw \(z_t\) as a colored 4×4 or 6×6 tensor glyph with a small history-clock marker.
- Draw \(b_{1:H}\) as a pale forecast strip that continues directly to the final addition node.

### Copy-ready labels

- `(b) History encoding & state construction`
- `History encoder q`
- `Context features`
- `State projector P`
- `History-only predictive state z_t`
- `Context-only forecasts b_{1:H}`
- `encode`
- `project`
- `context branch`

## 8. Region (c): Weather-conditioned shared dynamics

### Main structure

```text
Future meteorological forcing u_t:t+h
                         │
Geographic context g ────┼──▶ Shared transition T
Forecast horizon h ──────┤              │
Current state z_t ───────┘              ▼
                               Evolved state z_t+h
```

This is the visual center of the figure.

### Transition module

Render \(T\) as one large rounded module with three visual levels:

1. weather tokens entering from above or below;
2. a simplified state–forcing interaction pattern;
3. updated state tokens leaving on the right.

The module may resemble a compact attention/gating block, but it must not be labeled MMDiT, physics solver, or physically constrained model.

Use one module labeled `shared across forecast horizons`; do not add a circular rollout arrow.

### Optional intervention port

At the weather entrance, add a small port labeled:

- `Weather intervention`
- `actual / matched donor / normalized mean`

This port indicates where Q3 acts; it does not contain results.

### Copy-ready labels

- `(c) Weather-conditioned shared dynamics`
- `Future meteorological forcing u_{t:t+h}`
- `Geographic context g`
- `Forecast horizon h`
- `Shared transition T`
- `state–forcing interaction`
- `shared across forecast horizons`
- `Current predictive state z_t`
- `Evolved predictive state z_{t+h}`
- `Weather intervention`
- `actual / matched donor / normalized mean`

## 9. Region (d): State readout & forecast

### Main structure

```text
z_t+h → State readout O → State contribution r_h ─┐
                                                  ▼
Context-only forecast b_h ───────────────────────▶ ⊕ → Vegetation forecast ŷ_t+h
```

### Visual encoding

- Draw \(O\) as a compact decoder/readout funnel.
- Prefer a real signed contribution map for \(r_h\); otherwise retain an explicitly labeled empty asset slot.
- Route \(b_h\) from the upper context branch.
- Place the single equation \(\widehat y_{t+h}=b_h+r_h\) next to the addition node.
- End with three consistent NDVI forecast thumbnails, for example \(h=5,10,20\).
- If an observed future is shown, place it below as a small `reference` image with no solid input arrow.

### State-path intervention

Place a small breakable port between \(r_h\) and the addition node:

- `State-path intervention`
- `remove state contribution`

Do not include the supporting \(T\!\rightarrow I\) arm in the main architecture figure.

### Copy-ready labels

- `(d) State readout & forecast`
- `State readout O`
- `State contribution r_h`
- `Context-only forecast b_h`
- `Forecast fusion`
- `Vegetation forecast ŷ_{t+h}`
- `State-path intervention`
- `remove state contribution`
- `h=5`
- `h=10`
- `h=20`
- `reference`

## 10. Training objectives are not shown

Figure 2 is inference-only. The frozen forecast teacher, future-state target encoder, observed future targets, loss weights, and stage schedule are described in the method text or appendix and do not appear in the artwork.

## 11. Styling

### Color semantics

| Semantic role | Suggested color |
|---|---|
| Historical EO and context | muted blue |
| Predictive states | teal |
| Future weather | warm orange |
| Shared transition | blue-violet |
| State readout/contribution | green or cyan |
| Context-only branch | light blue |
| Final forecast | dark green |
| Intervention ports | small orange-red accents |

Use no more than five primary colors. Avoid rainbow nodes, large gradients, shadows, and 3-D effects.

### Typography and lines

- Sans-serif font consistent with the paper.
- Panel headers: 8.5–9 pt.
- Module labels: 7.5–8 pt.
- Auxiliary labels: 6.5–7 pt.
- Main arrows: 1.2–1.5 pt.
- Context-forecast branch: 0.8–1.0 pt.
- Panel dividers: 0.6–0.8 pt.

## 12. Caption

**Figure 2: TerraState architecture and testable predictive-state pathway.**
Historical Earth observations, environmental context, and static geographic attributes are encoded by \(q\). The same history-conditioned pass produces context-only forecasts \(b_{1:H}\) and, through projector \(P\), a history-only predictive state \(z_t\). Future meteorological forcing, geographic context, and the requested horizon enter only the shared transition \(T\), which evolves the state to \(z_{t+h}\). Readout \(O\) maps the evolved state to a state contribution \(r_h\), and the final vegetation forecast closes as \(\widehat y_{t+h}=b_h+r_h\). Small intervention ports expose the state-contribution and future-weather pathways used by the behavioral tests.

## 13. Exclusions

Do not include:

- `full24`, Stage A/B, Phase I/II, boundary80, MAIN-last;
- caches, checkpoints, SHA values, DDP, GPUs, or batches;
- future weather entering \(q\), \(P\), \(z_t\), \(O\), or \(b_h\);
- future EO or any training target;
- recurrent rollout or temporal-composition claims;
- extreme-specific enhancement claims;
- `physics-informed` or `physically constrained`;
- MMDiT unless the actual model uses MMDiT;
- random latent heatmaps presented as real internal states;
- screenshots from external papers;
- Q2/Q3 result values;
- the teacher, future-state target, or training supervision.

## 14. Acceptance checklist

- [ ] One continuous left-to-right inference path crosses all four regions.
- [ ] \(q\) produces both context forecasts and context features.
- [ ] \(P\) produces history-only \(z_t\).
- [ ] Future weather enters only \(T\).
- [ ] Geography and horizon enter \(T\).
- [ ] \(T\) is shared but is not drawn as a rollout loop.
- [ ] \(O\) reads only \(z_{t+h}\).
- [ ] Forecast closure is \(\widehat y_{t+h}=b_h+r_h\).
- [ ] The state-path intervention sits on \(r_h\rightarrow\oplus\).
- [ ] The weather intervention sits on future weather \(\rightarrow T\).
- [ ] No teacher, future-EO target, or training rail appears.
- [ ] Every real image follows `FIGURE_2_ASSET_CHECKLIST.md`.
- [ ] Every label follows `FIGURE_2_TEXT_COPY.md`.
- [ ] PPTX and SVG remain editable; the PDF remains vector-sharp and legible at paper scale.
