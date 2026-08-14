# Round 4 Refinement

## Problem Anchor

- **Bottom-line problem**: 在稀疏、受云和 acquisition 条件影响的 Earth observations 中，学习一个能支持可靠长期预测的状态表示及其动力学，而不是只把未来卫星图像当作一个独立视频 cuboid 回归目标。
- **Must-solve bottleneck**: 当前框架和主流方法没有证明 latent 中哪些变化属于地表过程、哪些属于观测形成，也没有证明同一个短步状态转移能够组合到长期、解释中间观测并在新观测到来时被修正。
- **Non-goals**: 不恢复不可识别的绝对真实物理状态；不声称首个 EO world model、因果反事实、完整地球模拟、业务天气预报或通用 EO foundation model；当前不实现大规模概率生成。
- **Constraints**: 现有 Stage1/1.5 ViT 与 EarthNet/GreenEarthNet 代码可复用；当前本地只有 Stage1 EuroSAT probe，无 Stage1.5/Stage2 结果；主目标是 AAAI 级、7 页内可闭环的工作；本轮不改代码。
- **Success condition**: 在 GreenEarthNet 官方 OOD 协议上，shared-step latent model 与强 direct control 至少统计持平，并在中间状态组合、观测条件稳健或再观测校正中给出 direct/pixel-autoregressive 模型不具备的稳定收益；天气控制证明收益不是纯 calendar shortcut。

## Anchor Check

- **Original bottleneck**: 稀疏/局部 EO 观测怎样安全、持续地校正 history-dependent predictive state。
- **Why the revised method still addresses it**: 模型结构不变；本轮只把“哪些 mask 可进入模型”与“什么统计量决定 claim”写死，消除 future cloud leakage 与选择性报告。
- **Reviewer suggestions rejected as drift**: 无需加入任何新模型、任务或数据集。第二数据集、下游和 FM 仍不属于本稿必要证据。

## Simplicity Check

- **Dominant contribution after revision**: observation-aligned residual correction；没有新增组件。
- **Components removed or merged**: 统计主终点压成一个 gain-AUC estimand；clear strata/RGBN/RMSE 变为 secondary；weather 只保留 true/no sanity。
- **Reviewer suggestions rejected as unnecessary complexity**: 不增加 masked normalization 或低-q专用模块；用共同 baseline contract 和 strata 判断即可。
- **Why the remaining mechanism is smallest adequate**: 本轮只新增布尔 availability 作为数据 contract，不是 trainable module。

## Changes Made

### 1. 严格拆分 observation 与 supervision masks

- **Reviewer said**: 未 reveal 的 future cloud mask 若进入 staleness，会泄漏未来云量。
- **Action**: 新增 `a_t`；只用 `m_obs=a*m_clear`/`q_obs` 更新 `U/s`，`m_sup` 永远只进 loss/evaluation；固定 nearest resize 和 unrevealed-mask invariance test。
- **Impact**: no-reveal computation graph 对全部 future target masks 完全不变。

### 2. 预注册 correction primary estimand 和层级统计

- **Reviewer said**: day25/50、多个误差和 strata 会产生选择空间。
- **Action**: 主终点固定为 day25/day50 平均的 cube-level NDVI-MAE paired gain AUC；primary comparisons 是 Ours-Vanilla 与 Ours-PredRNN-online，Holm correction；tile cluster paired bootstrap。
- **Impact**: reviewer 不需要猜结果是从哪一列挑出的。

### 3. 预声明 open-loop non-inferiority

- **Reviewer said**: “strong baseline level”过于模糊。
- **Action**: Block A primary 为官方 NDVI RMSE；对 matched Direct-Seq 的 non-inferiority margin 固定为 0.01，使用 paired tile-bootstrap one-sided upper 95% CI；OOD 前锁定。
- **Impact**: open-loop 是否保住被转为二元、可复核 gate。

## Revised Proposal

# Research Proposal: ObsWorld — Observation-Aligned Residual Correction for Sparse EO Predictive States

## Problem Anchor

- **Bottom-line problem**: 在稀疏、受云和 acquisition 条件影响的 Earth observations 中，学习一个能支持可靠长期预测的状态表示及其动力学，而不是只把未来卫星图像当作一个独立视频 cuboid 回归目标。
- **Must-solve bottleneck**: 当前框架和主流方法没有证明 latent 中哪些变化属于地表过程、哪些属于观测形成，也没有证明同一个短步状态转移能够组合到长期、解释中间观测并在新观测到来时被修正。
- **Non-goals**: 不恢复不可识别的绝对真实物理状态；不声称首个 EO world model、因果反事实、完整地球模拟、业务天气预报或通用 EO foundation model；当前不实现大规模概率生成。
- **Constraints**: 现有 Stage1/1.5 ViT 与 EarthNet/GreenEarthNet 代码可复用；当前本地只有 Stage1 EuroSAT probe，无 Stage1.5/Stage2 结果；主目标是 AAAI 级、7 页内可闭环的工作；本轮不改代码。
- **Success condition**: 在 GreenEarthNet 官方 OOD 协议上，shared-step latent model 与强 direct control 至少统计持平，并在中间状态组合、观测条件稳健或再观测校正中给出 direct/pixel-autoregressive 模型不具备的稳定收益；天气控制证明收益不是纯 calendar shortcut。

## Central Thesis and Scope

ObsWorld 不是新 Bayesian filter，也不是首个 EO world model。其唯一机制假设是：对空间局部可见的 EO observation，在相同 visibility operator 与 observation feature space 中显式计算“真实观测 − prior 预测”的 residual，并以可见支持安全更新 predictive belief，应比 unrestricted learned fusion 或 pixel-recurrent online assimilation 形成更有用的 posterior。

不声称跨传感器可识别分解、天气因果性、物理真实隐状态或通用 foundation model。Stage1.5 永远只是可删除的 initialization row；re-observation correction 是能力实验而非无关 downstream。

## Components

- `E`: existing S2 observation encoder，initially frozen；
- `P`: shared observation-feature projector，真实/预测分支完全共享；
- `H`: current Stage2 RGBN decoder architecture，同初始化并在 Direct/Vanilla/ObsWorld 中联合训练；
- `F_5`: shared five-day transition，输入 step weather、DOY、DEM、staleness；
- `U`: lightweight observation-aligned residual update。

没有自由 `Q`、mask token、posterior reconstruction、whole-state latent target、EMA target、smoothness/KL、uncertainty、diffusion、LLM/VLM 或额外任务 head。

## Exact Availability and Mask Contract

Define three non-interchangeable masks:

```text
a_t            [B,1,1,1]  observation availability in {0,1}
m_clear_t      [B,1,H,W]  clear/valid optical pixels from the observation
m_obs_t        = a_t * m_clear_t
q_obs_t        [B,N,1] = AvgPool(NearestResize(m_obs_t))
m_rgb_sup_t    clear/finite target mask for RGBN loss only
m_ndvi_sup_t   official clear × SCL × vegetation/dynamic validity for NDVI loss/eval only
```

The contracts are strict:

- only `m_obs/q_obs` may enter `E` residual branches, `U` and staleness；
- `m_rgb_sup/m_ndvi_sup` may enter loss/evaluation only and are never passed to `F/U/E` as model inputs；
- all context observations have `a_t=1`；
- future open-loop has `a_t=0` at every step；
- single-reveal training/evaluation has `a_r=1` at the chosen reveal and zero elsewhere；
- categorical masks are resized with nearest-neighbor before clear fraction average-pooling；
- a future target mask loaded to score a frame has no path to prediction state unless that frame is explicitly revealed。

Mandatory invariance test:

> Hold context RGBN/masks, future weather, model weights and reveal schedule fixed. Arbitrarily permuting or replacing every unrevealed future supervision mask must leave all open-loop beliefs, staleness values and predictions bitwise/equivalently unchanged.

## State, Staleness and Transition

```text
b_t-, b_t+  [B,N,d]  prior/posterior predictive belief
s_t-, s_t+  [B,N,1]  evidence-weighted staleness in [0,1]
δ = 5/100

s_t- = min(s_{t-1}+ + δ, 1)
b_t- = F_5(b_{t-1}+, w_t, DOY_t, G, s_t-)
```

Only observation availability changes staleness:

```text
s_t+ = (1-q_obs_t) * s_t-
```

Since `q_obs=0` whenever `a=0`, unrevealed future cloud masks cannot affect it. This is visibility-weighted staleness, not literal pixel-level last-observation age.

All ten context observations are processed sequentially using the same `F/U`; there is no separate context aggregator. Future official inference sets all `a=0`.

## Observation-Aligned Residual and Update

At an available observation:

```text
x_pred = H(b_t-)
z_obs  = P(E(x_t    * m_obs_t))
z_pred = P(E(x_pred * m_obs_t))
r_t    = z_obs - stopgrad(z_pred)

g_t    = sigmoid(MLP([LN(b_t-), r_t, q_obs_t, s_t-]))
delta  = R(r_t)
b_t+   = b_t- + q_obs_t * g_t * delta
```

At `a=0` the update is not invoked and `b_t+=b_t-`; at `q_obs=0`, the formula is exact identity. Real and predicted branches use identical RGBN normalization, masks, `E/P` weights and token grid. `stopgrad` prevents the correction path from shrinking residual by changing the current prior/decoder; `F/H` are still trained by forecast losses.

The reveal-time invocation of `U` receives supervision only through post-reveal losses. Context invocations of the same shared cell receive gradients through all downstream forecast consequences.

## Strong Controls

### VanillaFilter

Uses the same `F/E/P/H`, extra encoder forward, availability/mask contract, staleness, reveal schedule and forecast loss:

```text
u_t  = MLP_v([LN(b_t-), z_obs, stopgrad(z_pred), q_obs_t, s_t-])
b_t+ = b_t- + q_obs_t * u_t
```

It can learn subtraction implicitly. Update-cell Params/FLOPs are within 5%; report cell/full model Params/FLOPs, reveal wall-time and average train overhead.

### PredRNN-online

Uses the official strong recurrent configuration, same weather/targets/reveal distribution. At reveal only, it receives masked RGBN plus `m_obs`; otherwise it receives no future observation. It reports both absolute post-reveal error and gain relative to the same checkpoint with reveal disabled.

### Direct-Seq

Matched factual control with the same `E/H`, targets and raw weather. All methods use the official 24 five-day features and historical weather. Direct uses a one-layer GRU over shared step embeddings; recurrent systems consume them stepwise. Weather is benchmark forcing, not a paper claim.

## Training

- 50% no-reveal batches；
- 50% exactly-one-reveal batches, `r` uniform over future steps 2–15 and independent of cloud fraction；
- every recurrent online system uses the same sampled schedule；
- at reveal, predict prior first and update second；
- no current-frame posterior reconstruction；
- all 20 future targets supervised；
- `H` jointly trained from matched initialization；`E/P` freeze/unfreeze policy matched。

For prediction loss `ell_t = L_RGBN(m_rgb_sup) + λ L_NDVI(m_ndvi_sup)`:

```text
no reveal:
    L = mean_{1:T} ell_t

one reveal at r:
    L_pre  = mean_{1:r} ell_t
    L_post = mean_{r+1:T} ell_t
    L = 0.5 L_pre + 0.5 L_post
```

Thus reveal-time `U` is supervised only through a length-normalized post segment. Context uses the same update cell and is trained through downstream forecasts. Curriculum 1/2/4/8/12/20 only manages optimization；there is no train-length extrapolation claim。

## Evaluation Block A: Official Open-Loop

Use the unmodified GreenEarthNet full-20 evaluator on locked `ood-t_chopped`; OOD-s/st are compact secondary tracks. Rows: persistence/climatology, Contextformer, PredRNN, matched Direct-Seq, final ObsWorld. UniTS only if rerun under the same evaluator.

Primary official endpoint is NDVI RMSE. Before any OOD-t evaluation, lock the non-inferiority test against matched Direct-Seq:

```text
Delta_open = RMSE_ObsWorld - RMSE_Direct
non-inferiority margin δ_NI = 0.01 NDVI RMSE
```

Using paired tile-cluster bootstrap, the one-sided upper 95% CI of `Delta_open` must be below `0.01`. R²/NSE/|bias|/outperformance/RMSE25 are secondary official endpoints. OOD-t is evaluated once after Val locking. Contextformer/PredRNN remain external skill anchors, not selectively chosen after test.

## Evaluation Block B: Correction-Specific Paired Protocol

For every cube and each checkpoint, run no reveal, day25 reveal and day50 reveal. Never filter by clear fraction. All methods use a common ground-truth-only validity set; it cannot depend on model output.

Let `e_{m,s,c,r,h}` be cube-level NDVI MAE on common valid pixels at post-reveal horizon `h`, for method `m`, seed `s`, cube `c`, reveal `r`. Define:

```text
g_{m,s,c,r,h} = e_no-reveal_{m,s,c,r,h} - e_reveal_{m,s,c,r,h}
G_{m,s,c,r}   = mean_{h>r} g_{m,s,c,r,h}          # normalized gain AUC
Gbar_{m,s,c}  = 0.5 * (G_day25 + G_day50)

D_{b,s,c} = Gbar_{Ours,s,c} - Gbar_{b,s,c}
b in {VanillaFilter, PredRNN-online}
```

Positive `D` means Ours extracts more future value from the same revealed observation than the baseline.

### Primary correction estimand

- two co-primary paired differences: `D_Vanilla` and `D_PredRNN-online`；
- family-wise alpha 0.05 with Holm correction；
- three seeds are reported individually；for inference, first form same-seed/same-cube paired differences, average the three seed estimates within cube, then average all cubes/windows within geographic tile；
- resample geographic tiles with replacement for 10,000 paired cluster-bootstrap replicates；never resample pixels as independent data；
- bootstrap `Ours-baseline` differences directly, not overlapping separate CIs。

### Required supporting endpoint

Ours must also have non-worse/lower absolute post-reveal NDVI MAE than each baseline; a large self-gain caused only by a worse no-reveal starting point does not support the claim.

### Secondary endpoints

Post-reveal NDVI RMSE, RGBN MAE, horizon error/gain curves, gain AUC by day25/day50 separately, and predeclared clear-fraction strata with cube/pixel support counts. Strata are stability/effect-modification analyses, not a family of significance tests.

## Evaluation Block C: Minimal Deletions

- no explicit residual（Vanilla）；
- no staleness；
- continuous `q` → binary q。

Only features with Val benefit remain in the final model. Stage1 vs repaired Stage1.5 initialization and true/no-weather are optional appendix rows, never new claims. Hard replacement, multi-reveal, EO-WM benchmark, extra datasets, downstream and FM remain cut.

## Success and Stop Rules

The proposal claim is supported only if all hold:

1. Block A passes RMSE non-inferiority vs matched Direct；
2. both Holm-adjusted co-primary `D_b` comparisons favor Ours；
3. absolute post-reveal NDVI MAE is not worse than both strong online baselines；
4. effect is not exclusively driven by the highest-clear stratum；
5. all leakage/fairness/protocol tests pass。

Failure against Vanilla rejects explicit residual as necessary；failure against PredRNN-online rejects a latent correction advantage；factual collapse rejects the unified predictive-state paper。No extra downstream/module is added to rescue a failed claim。

## Implementation and Protocol Gates

1. explicit official split manifests and missing-split hard fail；
2. official NetCDF `ndvi_pred` export preserving time/lat/lon；
3. official full-20 evaluator and mask parity；
4. complete historical/future 24-channel weather；
5. mask availability/supervision separation and unrevealed-mask invariance；
6. q=0 identity、q=1 reset、partial-q staleness、predict-before-update and reveal-only-clear-pixel tests；
7. 8-cube overfit and official Contextformer/PredRNN parity；
8. one-seed U vs Vanilla/PredRNN-online gate before three seeds。

## Novelty, Downstream and Large Models

The novelty is deliberately narrow: an observation-aligned, visibility-safe residual correction rule for patchily observed EO predictive states, proven against a generic filter with identical information/compute and a mature pixel recurrent online model. It is not a new generic filter theory or physical-state identification.

No unrelated downstream is needed; fixed all-cube re-observation is the most direct capability test. A second dataset is beneficial but not required for this single-claim seven-page paper. AnySat/TerraMind initialization or FM 2×2 is deferred until after the lightweight claim succeeds; an LLM has no use here.

## Compute and Timeline

Measure 500–1000-update throughput before quoting GPU-hours. The proposed residual adds one `E/P` forward only on half the training samples and one evaluation reveal. Gate-driven budget remains approximately 8–12 full-run equivalents over roughly six weeks. With no local Stage2 artifacts on 2026-07-15, AAAI-27's 2026-07-28 full-paper deadline is not a credible from-scratch target.
