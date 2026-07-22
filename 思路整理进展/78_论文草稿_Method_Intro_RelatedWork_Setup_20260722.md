# 78 · 论文草稿：Abstract / Intro / Related Work / Method / Setup（英文正文 + 中文旁注）

> 写于 2026-07-22。**用途**：这是可直接粘进 LaTeX 的正文草稿。方法细节全部取自已核实的代码（file:line 见旁注）。**叙事严格遵循 76 号冻结版**，不越识别边界。Results/Tables 为占位，受"结果句门禁"（G2）约束——**SOTA 门未过前正文任何处不得出现 "state of the art"**。
> 中文旁注用 〔注：…〕 标出，正式提交时删。

---

## Title
**ObsWorld: An Observation-Aware Predictive-State World Model for Land-Surface Forecasting**

## Abstract
〔注：与 76 号冻结摘要一致，`【RESULT】` 是唯一可换句，按 76 §4 的 A/B/C 三档随实测替换。〕

Earth-observation forecasting is commonly cast as a direct mapping from past satellite images and weather to future vegetation. This entangles two distinct processes: how the land surface evolves, and how a given state is observed under specific product, processing, and acquisition conditions. We introduce **ObsWorld**, an observation-aware predictive-state world model that separates state inference, exogenous-driver dynamics, and conditional observation formation. ObsWorld infers a shared land-surface state from observations, evolves it under future weather and geographic context through a shared short-horizon transition applied both **directly and compositionally**, and renders future observations under an explicit observation condition. To make the state observation-aware, we learn it from **paired Sentinel-2 products (L1C/L2A)** so that product-dependent appearance is explained by the rendering condition rather than absorbed into the state. Built on a strong vegetation-forecasting backbone and optimized end to end, the same predictive state is evaluated through standard GreenEarthNet forecasting, cross-product rendering, multi-step latent consistency, and a frozen future-state event readout. **【RESULT】** These results position observation-aware predictive states as a practical interface between accurate Earth-surface forecasting and reusable Earth-observation world models.

---

## 1. Introduction
〔注：三段式——问题纠缠 → 我们的重构（四接口）→ 贡献。禁止越 76 §2 识别边界。〕

Forecasting the future state of the land surface from satellite image time series is a core Earth-observation (EO) task with direct relevance to drought monitoring, vegetation dynamics, and climate impact assessment. The dominant formulation learns a direct map from a context window of past optical frames and associated weather variables to a horizon of future frames, and is evaluated by how closely the predicted frames match held-out satellite observations. Strong recent models in this family — recurrent, convolutional, and transformer video predictors — have steadily improved this pixel-space forecasting accuracy.

This direct formulation, however, conflates two physically distinct processes. The first is **how the land surface evolves** under exogenous forcing such as weather and terrain. The second is **how a given surface state is observed**: a satellite frame is not the surface itself but a biased measurement of it under a specific product level, atmospheric-correction pipeline, and acquisition geometry. Because a fixed benchmark holds the observation protocol constant, a model trained only to match future frames is free to absorb product- and processing-dependent appearance into the very representation it uses to roll the state forward. The learned representation is then accurate on the fixed protocol but is neither identifiable as a surface state nor reusable under a changed observation condition — precisely the properties a *world model* is expected to provide.

We argue that EO forecasting should instead **separate state evolution from observation formation**, and we operationalize this as an **observation-aware predictive state**. Concretely, ObsWorld learns four testable interfaces (Fig. 1): a state-inference operator `q` that maps observations and an observation condition to a shared land-surface state; a controlled dynamics operator `T` that advances the state under future weather, geographic context, and elapsed time; an observation operator `O` that renders a state into a future observation under an explicit condition; and a readout `H` that consumes the frozen state for a downstream environmental event. Crucially, our claim that the representation is a world-model *state* rests not on the name but on **falsifiable behaviour of these interfaces**: the same short-horizon transition is applied both **directly** (one 10-day step) and **compositionally** (two 5-day steps) over the identical control path and is trained to agree, so the state is a compositional sufficient statistic; product-dependent appearance is pushed into `O` by learning from **paired Sentinel-2 L1C/L2A products**, so a fixed state can be re-rendered across conditions; and the **frozen** state supports a future vegetation-event readout it was never trained for.

We deliberately bound our claims (§3.5): the state is called a *predictive land-surface state* — sufficient for the future, stable across product conditions, controllably advanced, and reusable — and we do **not** claim to recover a unique or complete physical state, causal structure, a digital twin, real-time acquisition invariance, or a first weather-driven world model.

**Contributions.**
1. **Problem and formulation.** We recast EO world modeling as learning an *observation-aware predictive state*, explicitly separating state inference, exogenous-driver dynamics, and product-conditioned observation formation.
2. **Method.** We introduce the ObsWorld *state contract* — paired-state consistency, latent-future consistency, direct/composed compositional transitions, and a conditional observation renderer — compatible with a strong forecasting backbone and trained end to end.
3. **Empirics.** On standard GreenEarthNet forecasting, L1C/L2A factorization, and a frozen future-state readout, we jointly evaluate accuracy, controllable observation, and state utility.
〔注：贡献严格 = 76 §5，不含"统一所有任务/首个天气驱动/通用基础模型/S1-S2 全模态"。〕

---

## 2. Related Work
〔注：三块。数字/引用待补（我不杜撰具体分数与文献锚点；占位 [CITE]）。〕

**Earth-observation and vegetation forecasting.** A large body of work predicts future satellite frames or vegetation indices from past frames and meteorological drivers, spanning convolutional recurrent models, pure convolutional predictors, and spatiotemporal transformers [CITE]. On the EarthNet2021/GreenEarthNet benchmark family, context-conditioned transformers that fuse a static context encoding with per-pixel weather are the current strong points of comparison [CITE]. These methods target pixel-space forecasting accuracy under a fixed product protocol and do not model the observation process separately from surface evolution — the gap ObsWorld addresses.

**World models and predictive states.** Latent-dynamics world models learn a compact state that is inferred from observations, advanced by a transition under actions/controls, and decoded back to observations, with latent-consistency or latent-overshooting objectives encouraging the state to be a sufficient statistic for prediction [CITE]. Joint-embedding predictive architectures similarly emphasize predicting in a learned state space rather than pixel space [CITE]. ObsWorld adapts this view to EO, where the "action" is exogenous weather/terrain forcing and the observation model is a physically meaningful product/processing condition rather than a nuisance decoder.

**Self-supervision and product factorization in remote sensing.** Remote-sensing self-supervised corpora provide large multi-sensor, multi-product image collections, including paired Sentinel-2 L1C (top-of-atmosphere) and L2A (surface reflectance) products [CITE]. Prior use is primarily representation pretraining. We instead use L1C/L2A pairing as *supervision for the observation operator*: the same surface state must render to two products under two conditions, which is what makes product-dependent appearance explainable by the condition rather than absorbed into the state.

---

## 3. Method
〔注：架构细节全部已核实，file:line 见旁注。图 1 = 四接口 q/T/O/H。〕

### 3.1 Overview and notation
Let a context window of `T_c = 10` past optical frames `X_{1:T_c}` (RGB+NIR, 128×128, 5-day cadence) with per-pixel clear-sky masks be given, together with an observation condition `φ`, exogenous weather drivers `D`, static geographic context `G` (elevation), and elapsed times. ObsWorld predicts the next `T_f = 20` frames `X̂_{T_c+1:T_c+T_f}`. Internally it maintains a spatial **predictive state** `z ∈ R^{N×d}` with `N = 256` tokens on a 16×16 grid and `d = 256` channels. 〔注：token 数/维来自 `state_projector`(state_dim=256) 与 dynamics.latent_dim=256；grid 16×16 来自 256 patch。〕

The four interfaces are:
- **State inference** `q`:  `z_0 = q(X_{1:T_c}, φ)` .
- **Controlled dynamics** `T`:  `z_{t+h} = T(z_t, D_{t:t+h}, G, h)` .
- **Observation formation** `O`:  `X̂ = O(z, φ_target)` .
- **State readout** `H`:  `ŷ = H(z)` (frozen `z`).

### 3.2 Observation-aware state inference `q`
Each context frame is band-adapted from the 4-band EarthNet layout to the 12-band Sentinel-2 canonical layout 〔注：`EarthNetInputAdapter`, source_to_canonical=[1,2,3,8]〕 and encoded by a **FiLM-conditioned multi-modal ViT** (patch 16, 256² input, embed dim 384, depth 12) 〔注：`MultiModalViTEncoderFiLM`, base config 38–58 行〕. The observation condition `φ` is embedded by a dedicated encoder and injected via FiLM into the encoder's later blocks, so appearance that depends on the product/processing condition is routed through `φ` rather than the surface tokens 〔注：`PureImagingConditionEncoder`; film_start_layer=8〕. Per-frame token states are pooled into a single context state by a **coverage-aware aggregator** that weights each token by its clear-sky fraction and zeroes never-observed tokens 〔注：`ContextStateAggregator`, min_token_clear_fraction=0.25, coverage from `pixel_mask_to_token_coverage`〕. On GreenEarthNet the product protocol is fixed, so `φ` is a constant neutral reference at forecasting time; its necessity is established separately on paired data (§3.6, §4). 〔注：如实披露 φ 在主基准为常量，不假装动态采集元数据——76 §2。〕

### 3.3 Controlled compositional dynamics `T`
The transition advances a state over a variable-length control segment. A shared **interval driver encoder** turns an ordered segment of 5-day weather tokens `D`, calendar `C`, and durations `Δt` into a single conditioning summary via a small temporal transformer with availability-aware pooling 〔注：`IntervalDriverEncoder`; 缺测 D 仍保留日历/时长信息，公平 no-D 消融〕; a horizon encoder embeds elapsed days; and a residual state-dynamics transformer proposes the next state, combined through a single LayerScale-style residual gate 〔注：`ControlledTransition.forward` 119 行 `next = state + residual_scale*(proposed-state)`〕. The **same** transition supports two evaluation modes over the identical control path (Fig. 1):
- **Direct**: a single transition consumes the whole future prefix `D_{0:j+1}` to reach endpoint `j`.
- **Composed**: the endpoint is reached by two consecutive 5-day transitions, `z_0 → z_k → z_j`, the second starting from the intermediate state.

Because the transition accepts any intermediate state as input and its horizon embedding is the per-segment elapsed time, composition is well defined; training them to agree makes `z` a **compositional Markov sufficient statistic** rather than a per-horizon lookup. 〔注：composed 由 `ObsWorldPartitionModel._two_step_partition` 实现；一致性由 `PartitionConsistencyLoss`（无可学习参数、对称 stop-grad、含 endpoint 监督防退化）——见 doc 77 §1。〕

Weather drivers `D` use a compact, physically motivated **four-variable** protocol (5-day precipitation sum, mean temperature, mean vapour-pressure deficit, and shortwave radiation sum), derived from E-OBS variables 〔注：physical4: rr/tg/hu/qq → precip/temp/vpd/srad；配置 `stage2_earthnet_v2_direct_physical4.yaml`〕. Static context `G` is elevation tokenized on a grid aligned with the state grid 〔注：`GeoTokenizer`, cop_dem, 128/8→16×16〕. Ablations cleanly remove `D`, `G`, or the horizon while preserving the remaining time/season information.

### 3.4 Conditional observation formation `O`
A lightweight transformer decoder renders a state into a 4-band (RGB+NIR) future frame at 128×128 under output condition `φ_target` 〔注：`EarthNetObservationDecoder`+`LightDecoder`, patch 8, sigmoid〕. To anchor accuracy, `O` can predict a **bounded residual on a per-pixel last-valid-clear baseline**: it decodes a tanh-bounded delta added to the most recent cloud-free reflectance at each pixel, so the forecaster starts near persistence and learns the change 〔注：residual head + `last_valid_pixels`——Plan A 精度杠杆；baseline 只进 renderer，绝不进状态，见 core 125–127 行〕. NDVI is computed from the red and NIR channels for index-space supervision and evaluation.

### 3.5 State readout `H` and identification boundary
A small readout head consumes the **frozen** predictive state to predict a future vegetation-decline event, testing that `z` carries reusable, decision-relevant structure beyond the frame it was decoded to. We call `z` a *predictive land-surface state* — sufficient for the future, stable across product conditions, controllably advanced, and reusable — and explicitly **do not** claim recovery of a unique/complete physical state, causal structure, a digital twin, real-time acquisition invariance, or a first weather-driven world model. 〔注：识别边界=76 §2，锁死。〕

### 3.6 Training objectives
The forecasting objective is a masked Huber reconstruction on clear-sky target pixels plus an NDVI term 〔注：`loss.weights obs=1.0, ndvi=0.5`〕. The world-model state contract adds: a **paired-state consistency** that ties states of the same location under different products through the renderer condition (from L1C/L2A pairs); a **direct/composed consistency** on both latent states and rendered endpoints, with an endpoint-to-target term that prevents degenerate agreement 〔注：`PartitionConsistencyLoss` state/observation/ndvi/endpoint=0.10/0.10/0.05/0.50〕. The model is initialized from a self-supervised encoder and **fine-tuned end to end** 〔注：Stage1.5 initializer, encoder freeze=false〕.

---

## 4. Experimental Setup
〔注：数据/协议/指标/基线/训练。分数占位，绝不杜撰。〕

**Data.** GreenEarthNet / EarthNet2021x: 10 context + 20 target frames at 5-day cadence, 128×128, 4 bands (RGB+NIR), with per-pixel cloud masks; E-OBS meteorology and Copernicus DEM as `G`; paired Sentinel-2 L1C/L2A products for observation-operator supervision. 〔注：L1C/L2A 数据是否就位——侦察子代理复核中，回来补。〕

**Protocol and metrics.** We evaluate on the GreenEarthNet **ood-t** (out-of-domain temporal, chopped) track and report per-pixel NDVI **R², RMSE, NSE, and RMSE25** against held-out clear-sky targets, following the GreenEarthNet scorer 〔注：`eval/score_table1_greenearthnet.py`；主表 Table 1。诚实：本机可达的 chopped 只有 ood-t（1904 minicubes/8 regions）；val/iid/ood-s/ood-st chopped 缺，故只报 ood-t track，不称"完整官方协议"——doc 80 §4。〕 Separately, as a diagnostic on the raw EarthNet2021x iid/ood splits, we report the official **EarthNetScore (ENS)** — the harmonic mean of MAD/OLS/EMD/SSIM subscores 〔注：ENS 与 GreenEarthNet R²/RMSE 是两套互斥协议，**永不同表**（doc 74:36 / doc 80 §0）。ENS 的 SSIM 子分有 ~x^10.3 缩放，模型 ENS 甚至输给静态 persistence（doc 69/80）——故 ENS 只作诊断，主表用 R²/RMSE。〕 World-model interfaces are evaluated by: rendering error with vs. without the observation condition `φ`; direct-vs-composed latent consistency (state gap) and endpoint accuracy; and frozen-state event-readout skill against a raw-history baseline.

**Baselines.** A matched strong vegetation-forecasting backbone (our Direct model) and published EO forecasters on the same protocol 〔注：Contextformer/PredRNN/SimVP 等，数字取官方，doc 69〕. World-model claims are additionally checked against internal ablations (no-`φ`, no-`D`, no composition, non-frozen readout).

**Training.** End-to-end fine-tuning from a self-supervised initializer; AdamW (lr 1e-4, backbone 1e-5, weight decay 0.05); DeepSpeed ZeRO-1; 8×H200; bf16; 200 EarthNet epochs. 〔注：来自 `stage2_earthnet_v2_direct24.yaml` optimizer + train_zero1。〕

---

## 5. Experiments (plan; results TBD, gated)
〔注：三柱，与 76 §7 / doc 77 对应。结果句 A/B/C 档由 Table 1 的 G2 门决定。〕

- **Table 1 — Accuracy (S1a, Direct).** GreenEarthNet ood-t NDVI R²/RMSE/NSE vs. matched backbone and published forecasters. **[TBD — S1a 训练中；epoch100 val 首个门禁。参照锚点：matched Direct-P4 ood-t R²=0.5243 / RMSE=0.1778（doc 80 §1）；G2 门=3-seed R²>0.62 & RMSE<0.14。评测命令见 doc 80 §2。]**
- **Table 2 — Observation factorization.** Rendering with vs. without observation condition `φ`; does `φ` explain product/acquisition appearance? **[BLOCKED/需决策 — 真·L1C/L2A 数据+代码双缺（doc 79，已核实）；备选是用可得的采集条件 φ 做可运行版因子化。摘要"L1C/L2A"一句待你授权软化。]**
- **Table 3 — World-model state (S1b + frozen readout).** Direct-vs-composed latent gap + endpoint accuracy; frozen future-state event readout vs. raw-history. **[TBD — S1b config 就绪，门禁 gated，见 doc 77]**

**Honesty guards (锁死):**
- SOTA 门（G2：3-seed R²>0.62 & RMSE<0.14）未过前，正文与摘要不得写 "state of the art"；走 76 §4 的 B/C 档。
- S1b 的递归 rollout 头条精度**不得**作为方法精度上报；Table 1 = S1a Direct（doc 77 §2）。
- 官方分数只取官方来源、同 track/同 split；ENS 与 R² 不混用（doc 69 勘误）。

---

## 附：写作待办（醒来续）
1. Related Work 的 [CITE] 补文献锚点 + doc 69 的官方数字进 Table 1 对照列。
2. Fig.1 四接口示意图（q/T/O/H + direct/composed 两路）——先手绘草图。
3. Method 3.6 的 paired-state consistency 在 v2 代码中的确切实现路径（L1C/L2A 分支）——依赖 Stage1.8 侦察结论。
4. 结果句按 S1a epoch100 → 完成的 val 决定 A/B/C 档。
