# Round 3 Refinement

## Problem Anchor

- **Bottom-line problem**: 在稀疏、受云和 acquisition 条件影响的 Earth observations 中，学习一个能支持可靠长期预测的状态表示及其动力学，而不是只把未来卫星图像当作一个独立视频 cuboid 回归目标。
- **Must-solve bottleneck**: 当前框架和主流方法没有证明 latent 中哪些变化属于地表过程、哪些属于观测形成，也没有证明同一个短步状态转移能够组合到长期、解释中间观测并在新观测到来时被修正。
- **Non-goals**: 不恢复不可识别的绝对真实物理状态；不声称首个 EO world model、因果反事实、完整地球模拟、业务天气预报或通用 EO foundation model；当前不实现大规模概率生成。
- **Constraints**: 现有 Stage1/1.5 ViT 与 EarthNet/GreenEarthNet 代码可复用；当前本地只有 Stage1 EuroSAT probe，无 Stage1.5/Stage2 结果；主目标是 AAAI 级、7 页内可闭环的工作；本轮不改代码。
- **Success condition**: 在 GreenEarthNet 官方 OOD 协议上，shared-step latent model 与强 direct control 至少统计持平，并在中间状态组合、观测条件稳健或再观测校正中给出 direct/pixel-autoregressive 模型不具备的稳定收益；天气控制证明收益不是纯 calendar shortcut。

## Anchor Check

- **Original bottleneck**: 让 history-dependent predictive belief 在空间局部观测到来时被可信地纠正，并让纠正影响后续长期预测。
- **Why the revised method still addresses it**: innovation 现在由“同 mask 下真实观测特征 − prior 解码预测特征”确定，不再是自由 `Q` 的命名；不可见 patch 仍严格 identity；主训练和评测均只看 reveal 后的预测价值。
- **Reviewer suggestions rejected as drift**: 没有添加新任务或新模型家族。额外的 predicted-image encoder forward 仅在 reveal 时计算，用于固定 observation-aligned residual 的语义。

## Simplicity Check

- **Dominant contribution after revision**: observation-aligned residual correction，由共享 observation encoder、continuous clear support 与 evidence-weighted staleness 构成。
- **Components removed or merged**: 删除自由 `Q`、`e_mask`、double-q、two-reveal main training、post-reveal “official metrics”语言、wrong-year 必做项。
- **Reviewer suggestions rejected as unnecessary complexity**: 不加入 alignment loss，因为 shared masked re-encoding 已使 residual 语义成立；不加入 second posterior/reconstruction head。
- **Why the remaining mechanism is smallest adequate**: `F` 与一个 residual `U` 仍是仅有新单元；predicted/observed features 复用相同 `E/P/H`，没有新增独立 observation projector。

## Changes Made

### 1. 将 innovation 改成确定的 observation-aligned residual

- **Reviewer said**: 自由 `Q` 可与 gate 任意重参数化，不能保证预测观测语义。
- **Action**: reveal 时对真实 masked observation 与 prior decoded prediction 使用同一个 frozen/shared `E/P`，直接相减；预测分支 stop-gradient，删除 `Q`。
- **Reasoning**: 两项在相同 observation feature space、相同可见像素上比较，残差意义由计算图而不是损失名称保证。
- **Impact**: 贡献可被准确称为 observation-aligned residual correction。

### 2. 删除 mask token 与 q 双重衰减

- **Reviewer said**: `qz+(1-q)e_mask` 后再乘 q 会弱化低-clear evidence并污染 residual。
- **Action**: `z_obs=P(E(x*m))` 原样进入 residual；`q` 只在 final residual correction 外乘一次，同时作为 gate reliability input。
- **Reasoning**: q=0 identity 仍由结构保证，部分清晰 patch 不再遭 q² 衰减。
- **Impact**: 低-clear strata 与主动机一致。

### 3. 分离官方 factual metrics 与 correction-specific metrics

- **Reviewer said**: 截断 10/15 steps 后不能沿用完整 GreenEarthNet official R²/NSE/outperformance定义。
- **Action**: Block A 仅 full-20 open-loop 用官方 evaluator；Block B 用固定共同 mask 的 post-reveal NDVI/RGBN MAE/RMSE、paired gain、horizon curve/AUC。
- **Reasoning**: 避免改变资格条件后仍叫官方指标。
- **Impact**: 两类实验的统计单位与结论边界清楚。

### 4. 单 reveal 与事件归一化

- **Reviewer said**: 早 reveal 获得更多后续梯度，两次 reveal 混合贡献。
- **Action**: 50% no reveal、50% single reveal；correction batch 分别平均 pre/post segments，使每个 reveal event 的 post loss 与剩余长度无关。
- **Reasoning**: 让 update 的监督量不由 reveal 位置决定，并简化归因。
- **Impact**: 多次 assimilation 降为未来附录，不进入主方法。

### 5. 精确区分绝对预测与自身 correction gain

- **Reviewer said**: 不同模型 open-loop floor 不同，只比 reveal 后绝对误差不公平。
- **Action**: 对每个 checkpoint 同时运行 reveal/no-reveal；同时报告 absolute post-reveal error 与 within-model paired gain。
- **Reasoning**: 分开回答“最终谁最好”和“谁最会吸收观测”。
- **Impact**: PredRNN-online 是公平且有解释力的强 baseline。

## Revised Proposal

# Research Proposal: ObsWorld — Observation-Aligned Residual Correction for Sparse EO Predictive States

## Problem Anchor

- **Bottom-line problem**: 在稀疏、受云和 acquisition 条件影响的 Earth observations 中，学习一个能支持可靠长期预测的状态表示及其动力学，而不是只把未来卫星图像当作一个独立视频 cuboid 回归目标。
- **Must-solve bottleneck**: 当前框架和主流方法没有证明 latent 中哪些变化属于地表过程、哪些属于观测形成，也没有证明同一个短步状态转移能够组合到长期、解释中间观测并在新观测到来时被修正。
- **Non-goals**: 不恢复不可识别的绝对真实物理状态；不声称首个 EO world model、因果反事实、完整地球模拟、业务天气预报或通用 EO foundation model；当前不实现大规模概率生成。
- **Constraints**: 现有 Stage1/1.5 ViT 与 EarthNet/GreenEarthNet 代码可复用；当前本地只有 Stage1 EuroSAT probe，无 Stage1.5/Stage2 结果；主目标是 AAAI 级、7 页内可闭环的工作；本轮不改代码。
- **Success condition**: 在 GreenEarthNet 官方 OOD 协议上，shared-step latent model 与强 direct control 至少统计持平，并在中间状态组合、观测条件稳健或再观测校正中给出 direct/pixel-autoregressive 模型不具备的稳定收益；天气控制证明收益不是纯 calendar shortcut。

## Technical Gap

Contextformer 已覆盖 GreenEarthNet direct forecast；PredRNN/UniTS 已覆盖 recurrent/autoregressive forecast；EO-WM 已覆盖 weather-driven partially observed EO generation；RSSM/Kalman-style learned filters 已覆盖 prior/posterior 的一般范式。因此，本工作不以 world-model、recurrence、weather 或 generic filtering 为创新。

具体未闭合的问题是：新 EO 图像的有效区域受云遮而空间不完整。普通 learned posterior 可以任意融合 hidden state 和 observation embedding，却没有显式比较“prior 本来预期看到什么”与“当前实际看到什么”，也不保证无有效证据的 patch 完全保留历史 state。需要一个 observation-aligned residual：同一可见区域、同一 observation encoder 下，直接比较真实观测与 prior 解码预测，再按可见支持和软陈旧度局部更新 belief；其价值必须体现在 reveal 之后的未来，而非当前帧重建。

## Method Thesis

- **One-sentence thesis**: ObsWorld 在新观测到来时，将真实 masked observation 与 prior decoded prediction 经过同一 observation encoder，形成语义确定的 residual；一个只受 continuous clear support 与 evidence-weighted staleness 调制的 update 用该 residual 校正 spatial predictive belief，并仅从之后的 future loss 学习。
- **Smallest adequate intervention**: 复用 `E/P/H` 同掩码重编码，无需自由 observation head、alignment loss、mask token 或 posterior reconstruction。
- **Timeliness**: 重点不再是能否生成未来，而是部分观测是否能形成有长期预测价值、且对无证据区域安全的 posterior。

## Contribution Focus

- **Only paper-level contribution**: observation-aligned residual correction for patchily observed EO predictive states，加上 exact no-evidence identity 与 single-reveal future-only training。
- **Strong falsifiers**: parameter-matched generic filter（也获得 observed/predicted features）与 PredRNN-online。
- **Not contributions**: `F` recurrence、RSSM/filtering 理论、weather、Stage1.5、phi disentanglement、FM、downstream、diffusion。

## Proposed Method

### Reused and Trainable Components

- `E`: existing S2-capable observation encoder；initially frozen。
- `P`: existing state projector applied identically to real and predicted masked observations；not an independently trained observation head。
- `H`: current four-band EarthNet decoder architecture；Stage2 has no trained local checkpoint, so it is jointly trained from matched initialization in Direct/Vanilla/ObsWorld variants。
- `F`: shared five-day controlled transition；trainable。
- `U`: one lightweight residual gate/cell；trainable。
- If Val requires encoder adaptation, all matched latent variants unfreeze the same final blocks at the same step and LR。

There is no `Q`, mask token, posterior reconstruction head, uncertainty model, LLM/VLM, diffusion, extra downstream or multisensor Stage2.

### Inputs and Patch Contracts

```text
x_t        [B,4,H,W]    normalized RGBN
m_t        [B,1,H,W]    official clear-pixel mask
q_t        [B,N,1]      average-pool(m_t) on encoder token grid, continuous [0,1]
b_t-,b_t+  [B,N,d]      prior/posterior predictive belief
s_t        [B,N,1]      evidence-weighted staleness in [0,1]
```

No `q>0.05` threshold is used. Invalid pixels are set to zero only to define a common masked observation function. Clear support influences the update exactly once through the outer `q` multiplier and is also available to the gate as a reliability feature.

Staleness with `δ=5/100` per step:

```text
s_t- = min(s_{t-1}+ + δ, 1)
s_t+ = (1-q_t) * s_t-
```

This is explicitly called evidence-weighted/visibility-weighted staleness, not literal pixel-level time since last observation. It is a patch approximation; `q=0` leaves current increased staleness unchanged and `q=1` resets it.

### Sequential Filtering

Starting from learned `b_init`, all ten context observations use the same interface:

```text
b_t- = F_5(b_{t-1}+, w_t, DOY_t, G, s_t-)
x_t_pred = H(b_t-)
if observation is available:
    b_t+ = U(b_t-, x_t, x_t_pred, m_t, q_t, s_t-)
else:
    b_t+ = b_t-
```

Future official open-loop never exposes target observations. A correction run reveals exactly one future observation after the prior prediction at that time is recorded.

### Observation-Aligned Residual

At a reveal time:

```text
z_obs  = P(E(x_t       * m_t))
z_pred = P(E(x_t_pred  * m_t))
r_t    = z_obs - stopgrad(z_pred)
```

Both branches use identical `E/P`, the same RGBN bands, normalization, spatial mask and token grid. Hence `r_t` has a fixed interpretation: mismatch between the available real observation and what the prior predicted in the observation feature space. `stopgrad` prevents the residual target from being made artificially small by changing the prior/decoder through this path; `F/H` remain trained by ordinary forecast loss.

This adds one encoder forward only for samples/times with a reveal. Since main training uses at most one reveal and half of samples have none, average overhead is bounded and reported.

### Proposed Residual Update

```text
g_t   = sigmoid(MLP([LN(b_t-), r_t, q_t, s_t-]))
delta = R(r_t)
b_t+  = b_t- + q_t * g_t * delta
```

`q` appears only once as the outer evidence mass multiplier. By construction, `U(b,r,q=0,s)=b` exactly. Gate and residual map are spatial-token-wise with the same lightweight mixing budget used by the generic baseline.

### Strong Generic Filter Baseline

To ensure improvement is not just access to the predicted feature or extra compute, VanillaFilter also receives both aligned features and performs the same extra encoder forward:

```text
u_t  = MLP_v([LN(b_t-), z_obs, stopgrad(z_pred), q_t, s_t-])
b_t+ = b_t- + q_t * u_t
```

Hidden width is chosen so its parameters and FLOPs are within 5% of proposed `U`. It can learn a subtraction implicitly; proposed `U` only contributes the explicit residual inductive bias.

PredRNN-online is the second strong control: it gets the same reveal schedule, masked RGBN, mask and weather, updates its hidden state and continues autoregressively.

### Weather and Direct Fairness

Weather is benchmark forcing, not a causal claim. All models use the official 24 five-day features (mean/min/max of eight E-OBS variables) and historical context weather. One shared MLP creates step embeddings. Direct-Seq uses a one-layer GRU over the same step sequence for each horizon; `F`/PredRNN consume step embeddings sequentially. All models see the same raw weather, targets, training samples and target density; Params/FLOPs/wall time are reported.

A tiny true-weather/no-weather check remains Appendix only to satisfy the anti-calendar shortcut boundary. Wrong-year testing is optional and not required for the paper.

### Decoder and Optimization Fairness

`H` is trainable, not frozen. For each seed, matched Direct/Vanilla/ObsWorld start from the same `E/P/H` state. All 20 future targets are supervised. Search spaces and update budgets are predeclared and comparable. Contextformer and PredRNN use official strong configurations rather than intentionally weak reimplementations.

### Main Training Schedule

For every recurrent online system:

- 50% batches: no future reveal, 20-step open-loop;
- 50% batches: exactly one reveal `r` uniformly sampled from future steps 2–15, independently of cloud fraction；
- reveal uses the real target mask for every cube, without clear eligibility filtering；
- at `r`, first emit the prior prediction, then update；
- no posterior/current-frame reconstruction loss；
- multi-reveal is excluded from the main method。

Let `ℓ_t = L_RGBN + λ_NDVI L_NDVI` under the target clear mask. Losses are segment-normalized:

```text
no reveal: L = mean_{t=1..T} ℓ_t

one reveal at r:
L_pre  = mean_{t=1..r} ℓ_t
L_post = mean_{t=r+1..T} ℓ_t
L = 0.5 * L_pre + 0.5 * L_post
```

Thus each correction event receives one normalized post segment regardless of how early it occurs. `U` receives gradient only through `L_post`. λ is selected on Train/Val scale and locked before OOD. No whole-belief latent target, EMA target, range, smoothness, KL or current posterior reconstruction is used.

Curriculum only changes rollout length 1/2/4/8/12/20 before the full mixed schedule. There is no train-length extrapolation claim.

### Inference and Evaluation

#### Block A: official open-loop

Filter ten context frames, then predict all twenty future steps without target observations. Export official `ndvi_pred` NetCDF with unchanged coordinates/time. Use the unmodified GreenEarthNet evaluator for R², RMSE, NSE, |bias|, climatology outperformance and RMSE25.

#### Block B: correction-specific paired protocol

For every cube, independently evaluate:

- no reveal from a given checkpoint；
- one reveal at day 25；
- one reveal at day 50。

Never filter cubes by clear fraction. Use the actual mask; q=0 becomes exact no-op. Score only horizons after reveal with a predeclared common validity mask that depends only on ground-truth cloud/SCL/land-cover rules, never on model output.

These are not called official GreenEarthNet metrics. Report:

- absolute post-reveal NDVI MAE and RMSE；
- RGBN MAE as secondary；
- within-checkpoint paired gain `Error_no-reveal - Error_reveal`；
- horizon-wise absolute error and gain curves；
- post-reveal error/gain AUC；
- clear-fraction strata `[0,.1), [.1,.3), [.3,.6), [.6,1]` with cube/pixel support counts；
- paired tile/location cluster-bootstrap CI across three seeds。

For PredRNN-online and VanillaFilter, both absolute post-reveal error and their own paired gain are reported. “No update ObsWorld” always means the same trained checkpoint with reveal disabled, never a separately trained easier model.

### Protocol and Implementation Gates

Before any claim run:

1. explicit `train/val_chopped/ood-t_chopped/ood-s_chopped/ood-st_chopped` manifests; missing split hard fail；
2. official mask/evaluator parity and `ndvi_pred` NetCDF with time/lat/lon preservation；
3. full official weather including context；
4. unit tests: q pooling, q=0 exact state identity, q=1 staleness reset, partial-q recursion, predict-before-update, only revealed clear pixels enter both residual branches；
5. eight-cube overfit and official Contextformer/PredRNN parity；
6. no Stage2 claim based on the current local EuroSAT probes alone。

### Stage1.5 and Other Scope Decisions

Stage1.5 is only an initialization row if repaired state-bridge checkpoint passes predictive/semantic and Stage2 Val gates. It is not Claim 2, and S1/S2 near-time pairs are not called pure nuisance pairs. No unrelated downstream is required; the correction protocol is the closest capability test. No foundation-model 2×2 is run before the lightweight mechanism succeeds. An LLM has no role.

### Failure and Stop Rules

- official open-loop materially below Contextformer/PredRNN/Direct after protocol parity → stop predictive-state paper；
- proposed residual update not above parameter-matched Vanilla on absolute error and paired gain → explicit residual contribution unsupported；
- not above PredRNN-online, or improvement is only a lower open-loop floor artifact → no latent-assimilation advantage；
- gain restricted to the highest-clear stratum → restrict or reject sparse-observation claim；
- no-staleness equivalent on Val → delete staleness from final method；
- binary q equivalent → choose simpler mask contract；
- q=0 changes belief or validity set differs by method → invalidate run；
- Stage1.5 gate fails → use Stage1/S2-only and omit it；
- true/no-weather indistinguishable → remove any driver-use interpretation。

## Novelty and Elegance Argument

The method is not presented as a new Bayesian filter. Its narrow hypothesis is that patchily observed EO requires an observation-aligned residual rather than unrestricted hidden-state fusion: real and predicted observations are compared under the identical visibility operator and observation encoder; only visible evidence can modify the corresponding predictive state; and the update is trained only by its consequences for later forecasts. A capacity/compute-matched filter sees the same two features but must learn the comparison implicitly, while PredRNN-online tests whether pixel recurrence already suffices. This is one mechanism, one strong falsifier chain and no parallel contribution.

## Single Claim and Minimum Evidence

**Claim**: Under spatially partial, intermittently arriving EO observations, observation-aligned residual correction creates a more useful predictive posterior than unrestricted learned fusion or pixel-recurrent online assimilation, while retaining competitive official open-loop skill.

Minimum evidence:

1. full-20 official OOD-t factual forecast is at strong baseline level；
2. on all-cube fixed day25/day50 evaluation, proposed has lower absolute post-reveal error and larger paired self-gain than VanillaFilter and PredRNN-online；
3. three seeds/tile-cluster CI support the aggregate effect；
4. effect is not solely from high-clear strata；
5. matched inputs, reveal schedule, target density, decoder initialization, parameters/FLOPs and validity masks rule out confounds。

## Three Experiment Blocks

### A. Official factual forecast

Persistence/climatology, Contextformer, PredRNN, matched Direct-Seq, final ObsWorld；full official metrics on locked OOD-t, compact OOD-s/st, three seeds where stochastic training applies。

### B. Correction mechanism

Same-checkpoint no reveal, VanillaFilter, PredRNN-online, proposed residual U；all cubes fixed day25/day50；correction-specific absolute errors, paired gain, curves/AUC, clear strata/counts。

### C. Minimal deletions and boundaries

No explicit residual（Vanilla）, no staleness, continuous-to-binary q；Stage1.5 initialization and true/no-weather only as decision-gated appendix rows。Hard replacement, multi-reveal, extra datasets, downstream, FM and EO-WM benchmark remain cut。

## Compute and Timeline

Measure 500–1000 update throughput before quoting GPU-hours. Main extra cost is at most one additional `E/P` pass on half of training samples and one reveal at evaluation. Run order: protocol parity → baseline/overfit → one-seed proposed vs Vanilla/PredRNN-online → simplification on Val → only surviving systems get three seeds/one locked OOD evaluation. Target remains roughly 8–12 full-run equivalents and six weeks; with no local Stage2 artifacts on 2026-07-15, the 2026-07-28 AAAI-27 full-paper deadline is not a credible from-scratch target.
