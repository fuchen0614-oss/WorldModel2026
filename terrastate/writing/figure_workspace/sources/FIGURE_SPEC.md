# TerraState Figures 1–3 Specification

## Shared visual system

- Intended width: full AAAI two-column width, `7.0 in`.
- Editable masters: SVG with named semantic groups and live text, plus native
  DrawingML PPTX sources with editable text, independent shapes/connectors, and
  no embedded slide image.
- Paper exports: vector PDF.
- Review exports: 300 dpi PNG.
- Typeface: Arial/Helvetica-compatible sans serif across all three figures.
- Minimum intended final text size: approximately 8–9 pt at 7.0 in width.
- Normal inference: dark solid arrow.
- Q2 intervention: orange long-dashed path/cut.
- Q3 weather replacement: purple long-dashed path.
- Training only: brown dotted/dashed band.
- Color is never the only encoding; border weight, glyph, and line pattern also
  distinguish semantic roles.

Color palette:

| Role | Hex | Non-color encoding |
|---|---|---|
| history / Q1 | `#0072B2` | solid blue-gray box |
| predictive state | `#008B6B` | spatial grid glyph |
| weather / Q3 | `#6F5AA8` | purple box + dashed replacement paths |
| closure / Q2 | `#D55E00` | orange cut/cross + long dash |
| training only | `#A65C1B` | dotted/dashed enclosing band |
| neutral ink | `#202833` | heavy solid inference |

No figure contains a paper-style title, result winner badge, gradient, shadow,
3D element, or decorative icon.

## Figure 1 — Problem and contribution overview

### Question answered

Why does prediction accuracy alone not establish state-based world modeling,
and what additional evidence does TerraState provide?

### Reading order

1. Left: an endpoint forecaster is verifiable only at its output.
2. Center: TerraState exposes a predictive state and advances it through a
   shared weather-driven transition. Detailed decoding is deferred to Figure 2.
3. Right: Q1 tests retained forecast skill, Q2 intervenes on the state path,
   and Q3 replaces only the weather input to `T`.
4. Bottom-right conclusion: an internally testable EO world model.

### Deliberate omissions

- No training history or internal checkpoint names.
- No result values.
- No Q4/composition.
- No claim that existing forecasters are not world models.
- No detailed module inventory or loss schedule.

### English caption

**Why endpoint accuracy is not enough.** An EO forecaster may use both
observations and weather, yet output accuracy alone does not establish that an
internal state carries the forecast or evolves with the declared driver.
TerraState exposes a forecast-bearing predictive-state path with a shared
weather-driven transition. The selected model is therefore tested in three
complementary ways: Q1 measures retained forecast skill, Q2 cuts or bypasses
the state path, and Q3 replaces its future-weather driver.

### 中文解释

**为什么端点精度还不够。** 常规 EO 预测器即使同时使用观测和天气，输出精度仍不能
证明内部状态是否真正承担预测，也不能证明状态是否随声明的驱动而演化。TerraState
暴露一条承载预测的显式状态路径，并通过共享的天气驱动转移推进状态。因而，同一个
选定模型接受三项互补验证：Q1 检验保留的预测能力，Q2 切断或绕过状态路径，Q3 替换
未来天气驱动。

## Figure 2 — Formal method and intervention map

### Question answered

How does TerraState run internally, and exactly where are Q2/Q3 interventions
applied?

### Normal inference contract

1. Cloud-masked EO history, past weather, and static geography enter `q`.
2. `q` emits a context-only forecast `b_h` and exposes context features.
3. `P` projects those features into explicit state `z_t`.
4. `T(z_t,w,g,h)` is the shared weather-conditioned transition.
5. The future state `z_{t+h}` is decoded by `O` into `r_h`.
6. The final prediction is `y_hat_{t+h}=b_h+r_h`.

### Q2 placement

- Primary: cut the `r_h` edge before the addition node, equivalent to `s=0`.
- Supporting: bypass learned transition dynamics with `T→I`.
- The two interventions are visually distinct and are not presented as equally
  reliable evidence.

### Q3 placement

- Actual, matched donor, and normalized mean weather meet at a selector whose
  only downstream connection is the weather input to `T`.
- History, geography, `q`, `P`, `O`, `b_h`, samples, and masks remain fixed.

### Training-only band

The band uses the natural-language summary “Training objectives: forecasting +
distillation + future-state alignment.” It identifies ground-truth
forecasting, the frozen teacher, and the `h=20` future-observation state target.
It contains no full loss formula, curriculum/stage names, or test-time
intervention loss.

### English caption

**TerraState inference, supervision, and post-training interventions.**
Cloud-masked EO history, past meteorology, and static geography enter the
history encoder `q`; its context features are projected by `P` into the
predictive state `z_t`, while the same history-only pass produces the
context-only forecast `b_h`. Future weather, geography, and horizon condition
the shared transition `T`, and the state readout `O` decodes `z_{t+h}` into
`r_h`, yielding `y_hat_{t+h}=b_h+r_h`. Q2 either removes `r_h` (primary) or
replaces `T` by the identity (supporting). Q3 changes only the future-weather
input to `T`, comparing actual, matched-donor, and normalized-mean forcing.
The lower band shows training-only ground-truth, teacher-distillation, and
terminal future-state supervision; these sources are absent at inference.

### 中文解释

**TerraState 的推理、监督与训练后干预。** 云掩膜 EO 历史、过去气象和静态地理
进入历史编码器 `q`；同一次 history-only 前向一方面产生 context-only 预测 `b_h`，
另一方面由 `P` 将上下文特征投影为空间预测状态 `z_t`。未来天气、地理与预测时距
条件化共享转移 `T`，状态读出 `O` 将 `z_{t+h}` 解码为 `r_h`，最终得到
`y_hat_{t+h}=b_h+r_h`。Q2 的主检验移除 `r_h`，辅检验将 `T` 替换为恒等映射；Q3
只替换进入 `T` 的未来天气，比较真实天气、匹配供体和归一化均值天气。下方仅展示
训练期的真实目标、教师蒸馏和终端未来状态监督；这些来源在推理时均不存在。

## Figure 3 — Behavioral evidence

### Adopted design

- (a) Q2 forest plot: primary state-contribution cut and supporting `T→I` on
  Validation and OOD-t, with stored paired 95% CIs.
- (b) Q3 forest plot: endpoint-loss increase under matched-donor and
  normalized-mean weather, with stored geographic-cluster 95% CIs.

The two panels emphasize effect direction, uncertainty, and the
primary/supporting distinction. Tables 2–3 remain the source for exact numeric
reporting, so the roles are complementary rather than a second tabulation.

### Current data status

The frozen aggregate CSV is complete and sufficient for the active two-panel
design. `fig3_behavior.py` reads all estimates and stored interval limits from
that CSV and generates SVG/PDF/PNG without evaluating the model. No per-cube
record, qualitative case, or placeholder number is used.

### English caption

**Behavioral effects of state and weather interventions.** (a) Paired mean loss
of forecast skill after removing the state contribution (filled) or replacing
the shared transition by the identity (open) on Validation and OOD-t; lines
show paired 95% bootstrap confidence intervals. (b) Increase in endpoint loss
after replacing actual future weather with matched-donor or normalized-mean
weather; lines show geographic-cluster 95% confidence intervals. Rightward
effects mean that removing the state path or replacing actual weather degrades
prediction.

### 中文解释

**状态与天气干预的行为效应。** (a) 在验证集和时间偏移划分上，逐 minicube
配对计算移除状态贡献（实心）或将共享转移替换为恒等映射（空心）所造成的预测能力
损失，并绘制其均值；横线为配对 bootstrap 95% 置信区间。(b) 将真实未来天气替换
为匹配供体或归一化均值天气后，端点损失的增量；横线为地理簇 bootstrap 95%
置信区间。效应越向右，表示切断状态路径或替换真实天气后预测退化越明显。

## Export and integration

`source/export_figures.py` materializes the editable SVG styles, writes vector
PDFs, generates 300 dpi PNGs, and records hashes/dimensions in
`EXPORT_MANIFEST.json`.

The main manuscript is intentionally not modified. See `LATEX_INCLUDES.tex` for
copy-paste snippets.
