# Research Proposal: ObsWorld

## Problem Anchor

- **Bottom-line problem**: 在稀疏、受云和 acquisition 条件影响的 Earth observations 中，学习一个能支持可靠长期预测的状态表示及其动力学，而不是只把未来卫星图像当作一个独立视频 cuboid 回归目标。
- **Must-solve bottleneck**: 当前框架和主流方法没有证明 latent 中哪些变化属于地表过程、哪些属于观测形成，也没有证明同一个短步状态转移能够组合到长期、解释中间观测并在新观测到来时被修正。
- **Non-goals**: 不恢复不可识别的绝对真实物理状态；不声称首个 EO world model、因果反事实、完整地球模拟、业务天气预报或通用 EO foundation model；当前不实现大规模概率生成。
- **Constraints**: 现有 Stage1/1.5 ViT 与 EarthNet/GreenEarthNet 代码可复用；当前本地只有 Stage1 EuroSAT probe，无 Stage1.5/Stage2 结果；主目标是 AAAI 级、7 页内可闭环的工作；本轮不改代码。
- **Success condition**: 在 GreenEarthNet 官方 OOD 协议上，shared-step latent model 与强 direct control 至少统计持平，并在中间状态组合、观测条件稳健或再观测校正中给出 direct/pixel-autoregressive 模型不具备的稳定收益；天气控制证明收益不是纯 calendar shortcut。

## Technical Gap

Contextformer 已提供 GreenEarthNet 强 direct forecast；UniTS 已做 autoregressive raw-reflectance forecasting；EO-WM 已提出 partially observed, weather-driven EO world model 和天气响应诊断。因此 weather conditioning 或 autoregression 本身均不是空白。

仍未闭合的是：用 acquisition-aware observation interface 形成 predictive state，以一个 shared short-step latent transition 组合长期未来，并用中间状态与 re-observation 行为验证该结构，而不只是用 endpoint pixels 命名 latent video predictor 为 world model。

## Method Thesis

- **One-sentence thesis**: 将 acquisition-conditioned observation formation 与 land-surface predictive dynamics 分开，并让一个共享五日 latent transition 在逐步天气驱动下反复推进，可得到比独立 endpoint 或 pixel-autoregressive 预测更可组合、可验证和可校正的 EO predictive state。
- **Why smallest adequate**: 复用现有 encoder/decoder，只新增一个 shared transition；observation update 优先采用轻量 gated fusion，而非增加 diffusion、LLM 或多任务系统。
- **Why timely**: 它回答 2026 年 EO world-model 工作之后更严格的问题——什么结构和证据才能区分 world model 与 weather-conditioned video generation。

## Contribution Focus

- **Dominant contribution**: observation-grounded compositional latent transition，在 partial observation 下区分 prior rollout 与 observation-conditioned state update。
- **Supporting contribution**: 一个针对 composition、observation factor 和 driver response 的 claim-driven evaluation；不另立为新 benchmark claim，优先复用官方协议。
- **Explicit non-contributions**: 不以 backbone、foundation model、probabilistic diffusion、下游分类或新天气指标作为平行贡献。

## Proposed Method

### Complexity Budget

- **Frozen/reused**: repaired Stage1.5 encoder/state projector、S2 decoder、GreenEarthNet data/evaluator、Contextformer/OpenSTL baselines。
- **New trainable components**: (1) shared five-day latent transition；(2) 可选的轻量 mask-gated observation update。若 update 仅用确定性插值/attention reuse，则只算一个核心新组件。
- **Intentionally excluded**: latent diffusion、LLM、额外分类下游、大规模 stochastic state、经纬度 shortcut、多套 transition experts。

### System Overview

```text
context observations + phi + masks + timestamps
                  -> observation encoder -> context belief b0

b_k -- shared T(b_k, D_k, C_k, G, dt=5) --> prior b_{k+1}^- --> decoder --> o_hat
                                                |
new observation (training or assimilation) -> update U -> posterior b_{k+1}^+
```

### Core Mechanism

- `phi`: sensor/product/view geometry only；`C`: DOY；`D_k`: current five-day weather；`G`: DEM；`h` only for direct control。
- Free inference repeatedly applies the same transition and never consumes future observations.
- Training uses one-step posterior-anchored prediction plus multi-step prior overshooting/free rollout.
- EMA encoder/posterior targets prevent a moving-target latent loss.

### Training Signal

```text
L = L_masked_reflectance + 0.5 L_NDVI
  + 0.25 L_prior_to_EMA_posterior
  + 0.5 L_one_step + 0.01 L_range
```

Weights are starting priors and must be calibrated on training/Val gradients. Generic temporal smoothness and KL are excluded from P1.

Curriculum: 0–5k one/few-step with image encoder frozen；5–40k rollout lengths 1/2/4/8/12；40–60k add length 20 and unfreeze last encoder blocks/state projector at 0.1× LR.

### Inference

Ten context frames form `b0`; 20 five-day prior transitions produce 100-day RGBN observations. If a later clear image is provided in an assimilation test, `U` forms a posterior and rollout continues. No target image enters open-loop inference.

### Failure Modes and Diagnostics

- State1.5 erases semantics: predictive/semantic probes fall with nuisance probe；fallback is to downgrade it to initialization.
- Rollout drift: endpoint and hidden-step curves degrade；fallback is direct task paper, not relabeling.
- Calendar shortcut: shuffled/wrong-year weather unchanged；fallback is weather-conditioned rather than response-faithful claim.
- S1/S2 false invariance: use L1C/L2A controlled pairs or soften to cross-sensor common predictive subspace.

### Novelty and Elegance

Relative to Contextformer/UniTS/EO-WM, novelty is not a larger generator or a new weather embedding. It is the minimal state-space interface: observation-conditioned posterior, shared short-step prior, and observation decoder, together with direct/pixel-AR matched controls that isolate latent composition.

## Claim-Driven Validation Sketch

### Claim 1: Shared latent step is a genuine compositional predictive mechanism

- **Minimal experiment**: Direct-Seq vs Pixel-AR vs Latent-Step on GreenEarthNet OOD-t plus sparse-supervision hidden frames and horizon curves.
- **Metrics**: official R²/RMSE/NSE/bias/outperformance/RMSE25, hidden-step error, accumulation gap, Params/FLOPs.
- **Expected evidence**: official metrics statistically tied or better, plus clear hidden-step/accumulation or assimilation gain.

### Claim 2: Observation-aware state improves robustness without losing predictive content

- **Minimal experiment**: bypass/Stage1/repaired Stage1.5；correct/missing/swapped phi；acquisition/semantic/future probes on held-out geography。
- **Metrics**: reconstruction, future NDVI, balanced nuisance probe, semantic probe, confidence intervals.
- **Expected evidence**: nuisance accessibility decreases while semantic/future utility and Stage2 skill improve or remain intact.

## Experiment Handoff Inputs

- **Must-prove claims**: composition first；observation robustness second。
- **Must-run ablations**: direct/pixel/latent；state bridge；true/no/shuffled weather；EMA target；rollout curriculum。
- **Critical dataset/metrics**: GreenEarthNet official Val/OOD-t/OOD-s/OOD-st and unchanged official evaluator。
- **Highest-risk assumptions**: repaired Stage1.5 is useful；shared rollout remains competitive；phi evidence transfers to fixed-product GreenEarthNet。

## Compute & Timeline Estimate

- **GPU-hours**: unknown until one 500–1000-update measured pilot; report formula `sec/update × updates × seeds / 3600` rather than fabricate。
- **Data cost**: existing GreenEarthNet/SSL4EO；optional original EarthNet2021 diagnostics only after core gates。
- **Timeline**: approximately six weeks for protocol, baselines, main seeds, mechanisms and one optional strengthening block. AAAI-27 in July 2026 is not evidence-ready unless remote results already exist.
