# Round 2 Refinement

## Problem Anchor

- **Bottom-line problem**: 在稀疏、受云和 acquisition 条件影响的 Earth observations 中，学习一个能支持可靠长期预测的状态表示及其动力学，而不是只把未来卫星图像当作一个独立视频 cuboid 回归目标。
- **Must-solve bottleneck**: 当前框架和主流方法没有证明 latent 中哪些变化属于地表过程、哪些属于观测形成，也没有证明同一个短步状态转移能够组合到长期、解释中间观测并在新观测到来时被修正。
- **Non-goals**: 不恢复不可识别的绝对真实物理状态；不声称首个 EO world model、因果反事实、完整地球模拟、业务天气预报或通用 EO foundation model；当前不实现大规模概率生成。
- **Constraints**: 现有 Stage1/1.5 ViT 与 EarthNet/GreenEarthNet 代码可复用；当前本地只有 Stage1 EuroSAT probe，无 Stage1.5/Stage2 结果；主目标是 AAAI 级、7 页内可闭环的工作；本轮不改代码。
- **Success condition**: 在 GreenEarthNet 官方 OOD 协议上，shared-step latent model 与强 direct control 至少统计持平，并在中间状态组合、观测条件稳健或再观测校正中给出 direct/pixel-autoregressive 模型不具备的稳定收益；天气控制证明收益不是纯 calendar shortcut。

## Anchor Check

- **Original bottleneck**: 学到能保存历史、开放推进并被局部新观测纠正的 EO predictive state，而不是只回归一个 future cube。
- **Why the revised method still addresses it**: `b^-` 与 `e` 继续分离；`U` 对不可见 token 严格 identity；它是否有用只由 reveal 之后的 future skill 判断。全体 cube 的固定再观测协议直接对应稀疏/云遮问题。
- **Reviewer suggestions rejected as drift**: 没有添加 diffusion、FM 或额外 downstream。VanillaFilter 与 PredRNN-online 是隔离机制增量所需的强对照，不成为新模块或新贡献。

## Simplicity Check

- **Dominant contribution after revision**: Cloud- and age-gated innovation update，使局部 EO evidence 只在可信位置修正历史 predictive belief，并通过后续预测端到端学习。
- **Components removed or merged**: Stage1.5 不再是 Claim 2；weather 不再是论文级 response claim；删除 posterior-current reconstruction loss、train-length extrapolation、复杂 direct assimilation、hard/restart 正文双对照。
- **Reviewer suggestions rejected as unnecessary complexity**: 不给 `E` 新增完整 mask encoder；在 state token 接口用连续 `q` 与单一 learned mask token 即可。`H` 从共同初始化联合训练，不再构造额外预训练 decoder。
- **Why the remaining mechanism is smallest adequate**: 主方法仍只有 `F` 与 `U` 两个新 trainable units；掩码契约、训练 schedule 和强 baseline 是证据设计，不是系统堆叠。

## Changes Made

### 1. 加入真正强的过滤与在线递归对照

- **Reviewer said**: no update/hard replace 不足以证明 innovation update 的增量。
- **Action**: Block B 固定 no-update、parameter-matched VanillaFilter、PredRNN-online、proposed U；hard replacement 只留一个附录行。
- **Reasoning**: 只有优于 generic posterior 与成熟 pixel recurrent assimilation，才能把收益归因于 innovation/clear-fraction/age 结构。
- **Impact**: 新颖性被置于可证伪的最强比较，而非弱消融。

### 2. 修复 decoder 初始化与训练矛盾

- **Reviewer said**: 当前四波段 Stage2 decoder 没有训练权重，不能冻结。
- **Action**: 所有 proposed/direct/vanilla variants 使用相同随机种子初始化的 `H` 并共同训练；`E` 先冻结，必要时统一解冻最后 blocks。
- **Reasoning**: 不依赖并不存在的 checkpoint，同时保证公平性。
- **Impact**: 方案与当前代码资源一致。

### 3. 固定 mask/evidence/age 张量契约

- **Reviewer said**: proposal 的 mask token 不是现有 encoder 接口，`q/age` 未精确定义。
- **Action**: pixel mask 平均池化为连续 `q`；无效像素归零，encoder state 与单一 learned mask token 按 `q` 混合；`q=0` 时 `U` 严格 identity；effective age 按固定公式递推。
- **Reasoning**: 这是现有 E 上最小且可单测的适配，不需要重写 encoder。
- **Impact**: partial/full missing patch 行为无歧义。

### 4. 去除 correction 的晴朗样本选择偏差

- **Reviewer said**: 只选 clear cube 会让任务变容易。
- **Action**: 所有 cube 固定 day 25 和 50，真实 mask 原样输入，`q=0` 自动 no-op；报告总体、clear-fraction strata 和样本量。
- **Reasoning**: 能把负例也纳入主统计，符合实际 acquisition。
- **Impact**: correction gain 可复现且不依赖 eligibility filter。

### 5. 具体化天气公平性并进一步降级支持项

- **Reviewer said**: Direct weather aggregator 未定义，weather claim 与 Block C 冲突，Stage1.5 仍过重。
- **Action**: 所有模型共享 24-channel five-day weather MLP，Direct 用一层 GRU 聚合 trajectory；weather 仅是 benchmark forcing，附录保留 true/no/wrong-year 三行 sanity；Stage1.5 永远只是 initialization ablation。
- **Reasoning**: 保留 Anchor 所需 anti-shortcut 检查，但不复制 EO-WM 或制造第二贡献。
- **Impact**: 一篇论文只剩一个 dominant claim。

## Revised Proposal

# Research Proposal: ObsWorld — Cloud-Gated Predictive-State Correction for Sparse Earth Observation

## Problem Anchor

- **Bottom-line problem**: 在稀疏、受云和 acquisition 条件影响的 Earth observations 中，学习一个能支持可靠长期预测的状态表示及其动力学，而不是只把未来卫星图像当作一个独立视频 cuboid 回归目标。
- **Must-solve bottleneck**: 当前框架和主流方法没有证明 latent 中哪些变化属于地表过程、哪些属于观测形成，也没有证明同一个短步状态转移能够组合到长期、解释中间观测并在新观测到来时被修正。
- **Non-goals**: 不恢复不可识别的绝对真实物理状态；不声称首个 EO world model、因果反事实、完整地球模拟、业务天气预报或通用 EO foundation model；当前不实现大规模概率生成。
- **Constraints**: 现有 Stage1/1.5 ViT 与 EarthNet/GreenEarthNet 代码可复用；当前本地只有 Stage1 EuroSAT probe，无 Stage1.5/Stage2 结果；主目标是 AAAI 级、7 页内可闭环的工作；本轮不改代码。
- **Success condition**: 在 GreenEarthNet 官方 OOD 协议上，shared-step latent model 与强 direct control 至少统计持平，并在中间状态组合、观测条件稳健或再观测校正中给出 direct/pixel-autoregressive 模型不具备的稳定收益；天气控制证明收益不是纯 calendar shortcut。

## Technical Gap

Contextformer 已覆盖 GreenEarthNet 强 direct forecasting；PredRNN 与 UniTS v2 已覆盖 recurrent/autoregressive prediction；EO-WM 已覆盖 weather-driven partially observed EO generation；RSSM、predictive-state 和 Kalman-style learned filter 已覆盖一般 prior/posterior 结构。因此本工作不把这些概念本身写成新颖性。

剩余的具体 EO 问题是：一张新卫星影像通常仅在部分 patch 可信。普通 recurrent assimilation 会让整帧 observation embedding 更新整个 hidden state，generic learned posterior 也不保证完全不可见位置保持历史 belief。需要一个可单测的局部更新接口：由 prediction–observation innovation 决定“往哪里改”，由 clear fraction 决定“多少证据可用”，由 time-since-observation 决定“先验已陈旧多久”，并且只靠该更新对之后预测的影响学习。

## Method Thesis

- **One-sentence thesis**: ObsWorld 以共享 prior transition 推进 spatial predictive belief，并用一个对 `q=0` 严格保持 identity 的 cloud/age-gated innovation update 吸收局部 EO evidence；更新器不重建当前观测，而是由 reveal 后的未来预测误差端到端训练。
- **Smallest adequate intervention**: `F` 提供无观测时的 prior，`U` 提供局部可信证据到达时的 posterior；一个连续 mask contract 即可复用现有 encoder，不增加生成器或任务头。
- **Timeliness**: 当前前沿已能生成长期 EO 序列，但“新观测能否在不破坏遮挡区域记忆的情况下持续改善未来”仍不是标准主证据。

## Contribution Focus

- **Only paper-level contribution**: 面向空间局部缺测 EO 的 cloud/age-gated innovation correction，与 open-loop/correction 混合训练协议；其机制增量由 parameter-matched generic filter 和 PredRNN-online 隔离。
- **Supporting engineering choices, not contributions**: shared five-day prior、EO encoder initialization、benchmark weather forcing、official GreenEarthNet protocol。
- **Explicit non-contributions**: 不声称 filtering/RSSM/recurrence/world-model framing 首创；不声称跨传感器 observation factorization；不声称天气因果响应；不把 Stage1.5、FM、downstream 或 diffusion 列作贡献。

## Proposed Method

### Complexity Budget

- **Reused**: existing S2-capable encoder `E`、state projector、EarthNet RGBN decoder architecture `H`、latent dynamics blocks、GreenEarthNet data/evaluator。
- **Trainable main units**: shared controlled transition `F`；cloud/age-gated innovation update `U`。
- **Training status**: `E` initially frozen；`H` is not pretrained and must be trained from the same initialization in all Direct/Vanilla/ObsWorld variants；only if Val plateaus may all variants unfreeze the same last encoder blocks at the same step/LR。
- **Excluded**: stochastic state/diffusion、LLM/VLM、uncertainty head、multisensor Stage2、extra downstream、foundation-model grid、transition experts。

### Exact Tensor Contract

For `B` samples, `N` spatial patches and state width `d`:

```text
x_t : [B, 4, H, W] normalized RGBN
m_t : [B, 1, H, W] official clear-pixel mask in {0,1}
q_t : [B, N, 1] = average-pool(m_t) to the encoder patch grid
z_t : [B, N, d] = Project(E(x_t * m_t))
e_mask : [1,1,d] one learned missing-evidence token
e_t : [B,N,d] = q_t * z_t + (1-q_t) * e_mask
a_t : [B,N,1] effective observation age normalized to [0,1]
b_t-, b_t+ : [B,N,d] prior/posterior predictive belief
```

`q` is never thresholded at 5%. Partially clear patches contribute proportionally. `e_mask` is the only mask token and lives after the frozen encoder/state projector, so current `E` need not be rewritten. Its value cannot update the state when `q=0`, because the final update is multiplied by `q`.

Age recursion for step length `Δ=5/A_max`, with `A_max=100 days` in the main task:

```text
a_t- = min(a_{t-1}+ + Δ, 1)
a_t+ = (1-q_t) * a_t-
```

Thus a fully clear patch resets age, a missing patch retains its increased age, and a partially clear patch reduces age continuously. At `q=0`, the state update must pass an exact numerical identity test; age remains `a_t-`.

### Sequential Context and Future State

There is no separate context aggregator. Starting from learned spatial `b_init` and age `1`, all ten context frames are filtered in chronological order:

```text
b_t- = F(b_{t-1}+, w_t, c_t, G, a_t-)
b_t+ = U(b_t-, e_t, q_t, a_t-)
```

For the first context frame, `F(b_init, ...)` is still called, so the same state interface is used everywhere. Future open-loop sets `b_t+=b_t-`; a revealed observation calls `U` after recording the prior prediction.

### Shared Five-Day Weather Interface

To match the official Contextformer input rather than the current four-feature shortcut, each five-day interval uses the 24 features formed by mean/min/max of eight E-OBS variables (`fg, hu, pp, qq, rr, tg, tn, tx`). A shared two-layer MLP produces `w_k` for every model.

- ObsWorld/VanillaFilter: consume one `w_k` per transition.
- PredRNN: receive the same `w_k` through its published conditioning path.
- Direct-Seq: a one-layer GRU aggregates `[w_1,...,w_h]` for each queried horizon, then the direct dynamics head predicts that endpoint.

This does not require identical parameter counts, but requires identical raw inputs, targets, target density, training samples and search budget; Params, update count, FLOPs and wall time are reported. Weather is benchmark forcing, not an independent causal claim.

### Prior Transition `F`

```text
b_t- = F_5(b_{t-1}+, w_t, DOY_t, G, a_t-)
```

`F_5` reuses the existing latent dynamics block and is shared across all steps. Its recurrence is not claimed as novel or as a semigroup. Its only role is to produce a history-carrying prior that may remain open-loop or be locally corrected.

### Proposed Update `U_innov`

```text
r_t   = e_t - Q(LN(b_t-))
g_t   = sigmoid(MLP([LN(b_t-), r_t, q_t, a_t-]))
delta = R(r_t)
b_t+  = b_t- + q_t * g_t * delta
```

`Q`, `R` and the gate MLP form one residual update cell. `q` is broadcast over channels. The exact identity `U(b,e,0,a)=b` follows by construction. Innovation is explicit: evidence only changes the belief relative to what the prior already predicts in the observation-aligned feature space.

### Parameter-Matched Vanilla Filter

The decisive generic alternative uses the same `F/E/H`, `q`, age and reveal schedule, but no explicit innovation:

```text
u_t   = MLP_v([LN(b_t-), e_t, q_t, a_t-])
b_t+  = b_t- + q_t * u_t
```

Hidden width is adjusted so `U_vanilla` and `U_innov` are within 5% parameters and comparable FLOPs. Therefore a difference cannot be explained by mask availability, online training or update capacity alone.

### Decoder `H`

`H` maps belief tokens to four S2 bands with sigmoid output. It is Stage2-new and jointly trained. For each seed, Direct-Seq, VanillaFilter and ObsWorld start from the identical `H` state; baseline-specific training then proceeds independently. Official reporting uses predicted NDVI; RGBN loss remains a training signal and secondary diagnostic.

### Training Schedule and Loss

All recurrent correction systems use the same reveal schedule distribution:

- 50% of training samples: no future observation, pure 20-step open loop;
- 25%: one reveal time uniformly sampled from future steps 2–15;
- 25%: two distinct reveal times uniformly sampled from future steps 2–15;
- reveal times are sampled independently of cloud/clear fraction; the real target mask is used without eligibility filtering;
- PredRNN-online receives the same revealed masked observation and mask; Vanilla/ObsWorld receive the same `e,q,a`.

Every system is supervised on all 20 targets with equal horizon weight. At each reveal, the model first emits `H(b_t-)`; only then is the observation consumed for later steps. There is no loss on `H(b_t+)` at the reveal frame. The only loss is future prediction:

```text
L = mean_t [ L_masked_RGBN(H(b_t-), x_t)
           + λ_ndvi L_masked_NDVI(H(b_t-), x_t) ]
```

Consequently `U` receives gradients only through horizons after the update and cannot win by copying the revealed frame. `λ_ndvi` is locked using training-scale/Val pilots. No whole-state latent target, EMA target, posterior reconstruction, range loss, smoothness or KL is used.

Curriculum: short overfit and one-step sanity → rollout lengths 1/2/4/8/12/20 → full mixed reveal schedule. If all-20 supervision is used, Direct-Seq is also supervised on all 20. Encoder unfreezing, if needed, is identical across compared latent variants.

### Inference Protocols

#### Official open-loop

Filter all context frames, then perform 20 future transitions with no target observation. This produces the official GreenEarthNet 100-day output.

#### Fixed all-cube correction

Run two predeclared settings on every cube:

1. reveal the observation at day 25;
2. reveal the observation at day 50.

Use the actual official mask; never exclude a cube for insufficient clear pixels. If all patches have `q=0`, update is identity. Score only horizons strictly after the reveal. Report:

- all-cube post-reveal official metrics/correction gain;
- clear-fraction strata fixed before evaluation, e.g. `[0,.1), [.1,.3), [.3,.6), [.6,1]`;
- cube count in every stratum;
- time-since-reveal error curves and cluster-bootstrap CI by location/tile.

No selection of “usable” or “clear” cubes is allowed after seeing outcomes.

### PredRNN-Online Control

PredRNN is trained with the same no/one/two-reveal schedule. Without reveal it feeds its previous prediction as usual; at reveal it consumes the masked true RGBN plus an explicit mask channel, updates its recurrent state, and continues autoregressively. It receives identical weather trajectory and target exposure. This tests whether a standard pixel recurrent hidden state already provides all claimed correction behavior.

### Minimal Weather and Initialization Checks

- **Weather sanity, appendix**: final model true weather vs separately trained no-weather, plus same-location wrong-year weather at inference. This only checks that results are not pure calendar persistence; artificial response sensitivity is not called causal correctness.
- **Stage1.5 initialization, appendix**: Stage1/S2-only vs repaired Stage1.5 using the same final architecture. Stage1.5 is retained only if predictive/semantic utility and Stage2 Val do not regress. It is never elevated to a paper claim and S1/S2 pairs are not described as pure nuisance pairs.

### Failure Modes and Stop Rules

- **`U_innov` ≤ VanillaFilter**: explicit innovation contribution unsupported; either report generic filtering result with weaker novelty or stop AAAI method claim.
- **`U_innov` ≤ PredRNN-online**: latent correction has no demonstrated advantage over mature recurrent assimilation; stop world-model claim.
- **Open-loop far below Direct/Contextformer/PredRNN**: correction cannot rescue an invalid factual forecaster; stop.
- **Gain only in high-clear stratum**: limit claim to adequate observation support; no blanket sparse-observation robustness claim.
- **q=0 changes belief**: implementation bug; no experiment is valid until identity unit test passes.
- **Stage1.5 gate fails**: use Stage1/S2-only and remove the row from main discussion.
- **True/no/wrong-year weather indistinguishable**: remove any driver-use interpretation; retain weather only because benchmark supplies it.

## Novelty and Elegance Argument

The proposal does not claim a new state-space theory. Its focused mechanism hypothesis is narrower and falsifiable: in patchily observed EO, a generic posterior update is insufficient because it neither represents prediction–observation disagreement explicitly nor guarantees local no-evidence identity; an innovation residual modulated by continuous clear support and effective observation age should form a better predictive posterior. The training objective cannot reward current-frame copying, and the main evidence requires improvement over both parameter-matched generic filtering and PredRNN-online. This is the smallest version in which EO-specific correction is an actual algorithmic claim rather than a relabeled recurrent forecast.

## Claim-Driven Validation

### Single Primary Claim

**Claim**: Under spatially partial and intermittently arriving EO observations, the cloud/age-gated innovation update forms a more useful predictive posterior than no update, a capacity-matched generic learned posterior, or standard pixel-recurrent online assimilation, while retaining competitive official open-loop skill.

- **Minimum evidence**: official OOD-t open-loop at strong-baseline level; `U_innov > U_vanilla` and `U_innov > PredRNN-online` on all-cube post-reveal metrics with three seeds/cluster CI; gains not confined to one cherry-picked cloud stratum.
- **Anti-claims ruled out**: more parameters; access to clearer observations; extra target supervision; current-frame copying; different weather sequence; split/evaluator mismatch.
- **Falsifier**: failure against either strong correction baseline, or factual open-loop collapse.

## Three Compact Experiment Blocks

### Block A — Official factual forecasting (main paper)

- Dataset: GreenEarthNet Train/Val; locked `ood-t_chopped` main, OOD-s/OOD-st compact generalization.
- Rows: persistence/climatology reference; Contextformer; PredRNN; Direct-Seq; final ObsWorld. UniTS appears only if rerun with the same official evaluator—never import incomparable PSNR/SSIM numbers.
- Columns: official R², RMSE, NSE, |bias|, climatology outperformance, RMSE25; Params/FLOPs/latency secondary; three seeds and tile/location cluster bootstrap.

### Block B — Correction mechanism isolation (main paper)

- Rows: no-update ObsWorld; VanillaFilter; PredRNN-online; proposed innovation U. Hard replacement is one appendix diagnostic only.
- Settings: all cubes, fixed day-25 and day-50 reveal, real masks; post-reveal metrics, time curve, clear strata/counts.
- Same reveal training distribution, weather, targets and evaluation for every online system.

### Block C — Compact dependency/failure checks (appendix or one small ablation table)

- `U` without age, without explicit innovation, and binary-mask replacement for the continuous `q` contract;
- Stage1/S2-only vs repaired Stage1.5 initialization only if pre-gate passes;
- true/no/wrong-year weather sanity.

This block does not create new claims. Unrelated downstream, FM 2×2, EO-WM matched-pair benchmark, probabilistic generation and additional datasets remain cut.

## Experiment Handoff Inputs

- **P0 protocol**: explicit official split manifests and hard fail; official NetCDF `ndvi_pred` export preserving time/lat/lon; official `s2_dlmask + SCL + vegetation/dynamic` evaluation; official/full 24-channel weather with historical context.
- **P0 unit tests**: q pooling; `q=0` exact belief identity; `q=1` age reset; partial-q age; reveal is applied only after current prediction; no target pixels leak outside revealed mask.
- **Core baselines**: Contextformer, PredRNN, Direct-Seq, VanillaFilter, PredRNN-online.
- **Statistical unit**: location/tile, not pixel; three training seeds; paired cluster bootstrap and effect-size CI.
- **Decision order**: protocol parity → shared decoder/encoder sanity → strong baseline reproduction → one-seed U vs Vanilla/PredRNN-online → only positive pilots receive three seeds.

## Compute & Timeline

- Measure 500–1000-update throughput before budgeting. Formula: `sec/update × updates × seeds / 3600`, plus evaluator overhead.
- Gate-driven target: 1 sanity/overfit; 2 strong baseline pilots; 3 online one-seed pilots; only the surviving 3–4 systems receive three seeds. Approximate 8–12 full-equivalent runs, stopped early if Vanilla/PredRNN-online falsify the claim.
- Normal route remains about six weeks. With no Stage2 artifacts on 2026-07-15, AAAI-27's 2026-07-28 full-paper deadline is not a credible from-scratch target.
