# Research Proposal: ObsWorld — An Observation-Correctable World Model for Sparse Earth Observation Forecasting

## Problem Anchor

- **Bottom-line problem**: 将稀疏、云遮 Earth observation forecasting 建模为 belief-state world modeling：模型既要在外生 forcing 下长期推演 EO-observable Earth-surface evolution，也要在新的局部卫星观测到达后校正内部世界 belief，而不是只回归一个未来视频 cuboid。
- **Must-solve bottleneck**: 当前框架和主流 forecaster 没有同时证明一个 history-dependent belief 能够可靠 open-loop rollout、解码未来观测，并由空间不完整的新 EO evidence 安全修正。
- **Non-goals**: 不恢复不可识别的绝对真实物理状态；不声称首个 EO world model、因果反事实、完整地球模拟、业务天气预报或通用 EO foundation model；当前不实现大规模概率生成。
- **Constraints**: 现有 Stage1/1.5 ViT 与 EarthNet/GreenEarthNet 代码可复用；当前本地只有 Stage1 EuroSAT probe，无 Stage1.5/Stage2 结果；主目标是 AAAI 级、7 页内可闭环的工作；本轮不改代码。
- **Success condition**: 在 GreenEarthNet 官方 OOD 协议上，shared-step latent model 与强 direct control 至少统计持平，并在中间状态组合、观测条件稳健或再观测校正中给出 direct/pixel-autoregressive 模型不具备的稳定收益；天气控制证明收益不是纯 calendar shortcut。

## Central Thesis and Scope

> **We cast sparse Earth observation forecasting as belief-state world modeling: ObsWorld rolls a history-dependent predictive belief forward under supplied forcing, decodes future satellite observations, and corrects that belief from visibility-aligned observation residuals. We hypothesize that this correction improves subsequent rollouts without sacrificing open-loop forecast accuracy.**

ObsWorld 的系统身份是 **observation-correctable Earth observation world model**；唯一机制假设是：对空间局部可见的 EO observation，在相同 visibility operator 与 observation feature space 中显式计算“真实观测 − prior 预测”的 residual，并以可见支持安全更新 predictive belief，应比 unrestricted learned fusion 或 pixel-recurrent online assimilation 形成更有用的 posterior。

这里的“模拟世界”严格指 **simulating EO-observable Earth-surface evolution under supplied meteorological, calendar, and geographic forcing**。ObsWorld 不是新 Bayesian filter，也不是首个 EO world model；不声称跨传感器可识别分解、天气因果性、物理真实隐状态、完整 Earth simulator、radiative-transfer sensor simulator 或通用 foundation model。Stage1.5 仅是可删除的 initialization row；re-observation correction 是 world-model contract 的核心能力实验，而不是无关 downstream。

## World-Model Contract

```text
Predict:  b_t-     = F_5(b_{t-1}+, u_t)
Observe:  x_t-     = H(b_t-)
Update:   b_t+     = U(b_t-, x_t, x_t-, m_obs_t)
Imagine:  b_{t+k}- = F_5^k(b_t+, u_{t+1:t+k})
```

- `b_t`：由完整历史形成的 predictive world belief，不是真实 physical state；
- `F_5`：在 weather、DOY、geography forcing 下的共享时间推进；
- `H`：固定 S2 product 的 learned observation model/decoder，不是物理 sensor renderer；
- `U`：局部新观测对 belief 的 visibility-safe update；
- future `a_t=0`：open-loop imagination；reveal `a_t=1`：posterior correction。

当前是 deterministic, forcing-conditioned EO world model；没有 stochastic uncertainty、agent planning 或 causal intervention，不因此失去 world-model 身份，但不能声称多模态未来、概率校准或数字孪生。

## Technical Gap

Contextformer 已覆盖 GreenEarthNet direct forecast；PredRNN 与 UniTS v2 已覆盖 recurrent/autoregressive forecast；EO-WM 已覆盖 weather-driven partially observed EO generation；RSSM/Kalman-style learned filters 已覆盖 prior/posterior 一般范式。因此，world-model 是问题定义和系统身份，而不能单独作为首创新颖性；recurrence、weather conditioning 或 generic filtering 也不是本稿的新意。

与最近邻 EO-WM 的中心差异必须始终一致：EO-WM 重点是 weather-driven EO generation 与 driver-response diagnostics；ObsWorld 重点是局部新观测如何以 observation-aligned innovation 安全校正 history-dependent belief，并改善之后的 rollout。只有能统一数据、输入和 evaluator 时才做数字比较，不能混用跨协议结果。

真正未闭合的问题是：新 EO 图像的有效区域受云遮而空间不完整。普通 learned posterior 可以任意融合 hidden state 与 observation embedding，却没有显式比较“prior 在该可见区域预期看到什么”与“实际看到什么”，也不保证没有证据的 patch 完全保留历史 state。需要一个 observation-aligned residual，并且它的价值必须体现在 reveal 之后的未来，而不是当前帧重建。

## Contribution Focus

1. **System/formulation**: ObsWorld 将 forcing-conditioned open-loop rollout 与 online belief correction 统一为一个 partial-observation EO world-model state machine；不声称 first。
2. **唯一方法级新意**: observation-aligned, visibility-safe residual correction；同 visibility operator/feature space 比较真实与预测观测，保证 exact no-evidence identity，并只由后续预测收益训练。
3. **Evidence**: 同时验证 world model 的两项定义性能力——GreenEarthNet OOD 的 100-day open-loop rollout，以及相对 matched generic filtering / pixel-recurrent assimilation 的 paired post-observation rollout gain。

`F` recurrence、RSSM/filtering 理论、weather、Stage1.5、phi disentanglement、FM、downstream 与 diffusion 都不是并列贡献。

## Components

- `E`: existing S2 observation encoder，初期冻结；
- `P`: 真实/预测 observation branches 完全共享的 feature projector；
- `H`: current Stage2 RGBN decoder architecture；本地无训练好的 Stage2 decoder，因此同初始化并在 Direct/Vanilla/ObsWorld 中联合训练；
- `F_5`: shared five-day controlled transition，输入 step weather、DOY、DEM 与 staleness；
- `U`: lightweight observation-aligned residual update。

没有自由 `Q`、mask token、posterior reconstruction、whole-state latent target、EMA target、smoothness/KL、uncertainty、diffusion、LLM/VLM 或额外任务 head。

## Exact Availability and Mask Contract

三个 mask 的语义与代码路径不得互换：

```text
a_t            [B,1,1,1]  observation availability in {0,1}
m_clear_t      [B,1,H,W]  当前 observation 的 clear/valid optical pixels
m_obs_t        = a_t * m_clear_t
q_obs_t        [B,N,1] = AvgPool(NearestResize(m_obs_t))
m_rgb_sup_t    RGBN loss only 的 clear/finite target mask
m_ndvi_sup_t   official clear × SCL × vegetation/dynamic mask for NDVI loss/eval
```

严格规则：

- 只有 `m_obs/q_obs` 可进入 residual branches、`U` 与 staleness；
- `m_rgb_sup/m_ndvi_sup` 只能进入 loss/evaluation，绝不能进入 `E/F/U`；
- context observation：`a_t=1`；
- future open-loop：所有 future steps 的 `a_t=0`；
- single reveal：仅 reveal step `a_r=1`；
- categorical mask 先 nearest-neighbor resize，再 average-pool 得到连续 clear fraction；
- 用于评分的 future cloud mask 不得影响未 reveal 状态。

必须有 invariance test：固定 context、weather、weights 与 reveal schedule，任意置换/替换所有 unrevealed future supervision masks，所有 open-loop beliefs、staleness 与 predictions 必须保持数值等价。

## State, Staleness and Transition

```text
b_t-, b_t+  [B,N,d]  prior/posterior predictive belief
s_t-, s_t+  [B,N,1]  evidence-weighted staleness in [0,1]
delta = 5/100

s_t- = min(s_{t-1}+ + delta, 1)
b_t- = F_5(b_{t-1}+, w_t, DOY_t, G, s_t-)
s_t+ = (1-q_obs_t) * s_t-
```

`s` 是 visibility-weighted staleness，而非精确 pixel-level time-since-last-observation。`a=0` 时 `q_obs=0`，未 reveal future masks 无法改变它。

全部十个 context observations 用同一 `F/U` 顺序处理，不再使用独立 context aggregator。官方 future inference 全部设置 `a=0`。

## Observation-Aligned Residual

当 observation available 时：

```text
x_pred = H(b_t-)
z_obs  = P(E(x_t    * m_obs_t))
z_pred = P(E(x_pred * m_obs_t))
r_t    = z_obs - stopgrad(z_pred)
```

真实与预测 branches 使用相同 RGBN normalization、visibility mask、`E/P` 权重与 token grid，所以 `r_t` 明确表示“可见区域的真实观测与 prior 预测在 observation feature space 中的 mismatch”。`stopgrad(z_pred)` 防止 correction path 通过修改当前 decoder prediction 人为缩小 residual；`F/H` 仍由普通 forecast loss 训练。

## Proposed Residual Update

```text
g_t   = sigmoid(MLP([LN(b_t-), r_t, q_obs_t, s_t-]))
delta = R(r_t)
b_t+  = b_t- + q_obs_t * g_t * delta
```

`q_obs` 只在 update 外乘一次，并作为 gate reliability input。`a=0` 时不调用 update；`q_obs=0` 时由结构保证 exact identity。

reveal-time 的 `U` invocation 仅由 post-reveal losses 监督；context 中共享的 `U` invocation 通过所有 downstream forecast consequences 训练。

## Strong Controls

### VanillaFilter

使用同一个 `F/E/P/H`、额外 encoder forward、availability/mask contract、staleness、reveal schedule、decoder initialization 与 forecast loss：

```text
u_t  = MLP_v([LN(b_t-), z_obs, stopgrad(z_pred), q_obs_t, s_t-])
b_t+ = b_t- + q_obs_t * u_t
```

它能隐式学习 subtraction。update-cell Params/FLOPs 与 proposed 相差不超过 5%；同时报告 cell/full model Params/FLOPs、reveal wall-time 与平均训练 overhead。

### PredRNN-online

使用官方强 recurrent configuration、相同 weather/targets/reveal distribution。仅在 reveal 时输入 masked RGBN 与 `m_obs`，随后继续 autoregressive rollout。必须同时报告 reveal 后绝对误差与相对同 checkpoint 禁用 reveal 的 self-gain。

### Direct-Seq

matched factual control，使用相同 `E/H` initialization、全部 20 targets 与 raw weather。所有模型使用官方 24 个五日 weather features及 historical weather；Direct 用一层 GRU 聚合 shared step embeddings，recurrent models逐步消费。Weather 是 benchmark forcing，不是因果 claim。

## Training

- 50% no-reveal batches；
- 50% exactly-one-reveal batches；`r` 从 future steps 2–15 均匀采样且与 cloud fraction 独立；
- 所有 online systems 使用同一 sampled schedule；
- reveal 时先输出/监督 prior，再消费 observation；
- 无 current-frame posterior reconstruction；
- 全部 20 future targets supervised；
- `H` 同初始化联合训练；`E/P` freeze/unfreeze policy matched。

设 `ell_t = L_RGBN(m_rgb_sup) + lambda * L_NDVI(m_ndvi_sup)`：

```text
no reveal:
    L = mean_{1:T} ell_t

one reveal at r:
    L_pre  = mean_{1:r} ell_t
    L_post = mean_{r+1:T} ell_t
    L = 0.5 * L_pre + 0.5 * L_post
```

这样不同 reveal 位置获得等量 post-segment supervision。curriculum 只把 rollout length 从 1/2/4/8/12 推到 20；不声称 train-length extrapolation。删除 whole-belief latent target、EMA target、range、smoothness、KL 与 posterior reconstruction。

## RQ1 / Evaluation Block A: Open-Loop Earth-Observation World Rollout

在 locked `ood-t_chopped` 上使用 unmodified GreenEarthNet full-20 evaluator；OOD-s/st 为 secondary tracks。主表：persistence/climatology、Contextformer、PredRNN、matched Direct-Seq、final ObsWorld。UniTS 只有按同一 evaluator 重跑时才进入数字表。

Primary official endpoint 是 NDVI RMSE。OOD 前锁定：

```text
Delta_open = RMSE_ObsWorld - RMSE_Direct
delta_NI = 0.01 NDVI RMSE
```

paired geographic-tile bootstrap 的 one-sided upper 95% CI 必须 `<0.01`。R²、NSE、|bias|、climatology outperformance、RMSE25 为 secondary official endpoints。正文报告 horizon-wise degradation curve 作为 rollout stability 的行为证据。Val 锁定后 OOD-t 只评一次；bootstrap replicate 必须在重采样 tiles 上重新计算 official aggregate metric。

## RQ2 / Evaluation Block B: Partial-Observation Belief Correction

每个 cube、每个 checkpoint 都独立运行 no reveal、day25 reveal、day50 reveal；不按 clear fraction 筛 cube。所有方法使用相同、只依赖 ground truth 的 validity set；这些不称作截断版“官方指标”。

令 `e_{m,s,c,r,h}` 为 common valid pixels 上的 cube-level post-reveal NDVI MAE：

```text
g_{m,s,c,r,h} = e_no-reveal_{m,s,c,r,h} - e_reveal_{m,s,c,r,h}
G_{m,s,c,r}   = mean_{h>r} g_{m,s,c,r,h}
Gbar_{m,s,c}  = 0.5 * (G_day25 + G_day50)

D_{b,s,c} = Gbar_{Ours,s,c} - Gbar_{b,s,c}
b in {VanillaFilter, PredRNN-online}
```

### Primary correction estimand

- co-primary paired differences：`D_Vanilla` 与 `D_PredRNN-online`；
- family-wise alpha 0.05，Holm correction；
- 先在 same-seed/same-cube/reveal 内形成 paired quantities；保留三种子 point estimates；再在 cube 内平均 seeds，并在 geographic tile 内聚合 cubes/windows；
- 10,000 paired cluster-bootstrap replicates，重采 geographic tiles，绝不把 pixels 当独立样本；
- 直接 bootstrap `Ours-baseline` differences，而非比较两条独立 CI。

### Required supporting endpoint

Ours 的 absolute post-reveal NDVI MAE 还必须不劣于/低于两个 baseline；若 self-gain 仅因自身 no-reveal 起点更差而显得大，主张不成立。

### Secondary endpoints

NDVI RMSE、RGBN MAE、horizon error/gain curves、day25/day50 separate gain-AUC，以及预注册 clear-fraction strata 和 support counts。Strata 只作 effect-modification/stability analysis，不做一组新的显著性检验。

## RQ3 / Evaluation Block C: World-Model Contract and Mechanism Ablations

- no explicit residual（Vanilla）；
- no staleness；
- continuous `q` → binary q。

只有 Val 显示有益的部件才保留。Stage1 vs repaired Stage1.5 initialization 是 decision-gated Appendix row。Hard replacement、multi-reveal、EO-WM benchmark、额外数据集、downstream 与 FM 全部 cut。

Forcing-alignment 是 world-model contract 的 required supporting evidence，而不是新贡献：

- independently trained true-weather vs no-weather，作为 driver predictive utility 的辅助证据；
- same-checkpoint correct-time vs time-shuffled/wrong-year weather；correct-time 更优是 time-alignment 的关键证据。

两类检查都运行。若 correct-time 不优于 shuffled/wrong-year，删除 thesis 中 forcing-conditioned 的强调；若有差异，也只声称模型使用 time-aligned forcing，不声称 causal response。

## Success and Stop Rules

中心 claim 仅在全部条件成立时获得支持：

1. Block A 通过 official NDVI RMSE non-inferiority；
2. Holm-adjusted `D_Vanilla>0`；
3. Holm-adjusted `D_PredRNN-online>0`；
4. absolute post-reveal NDVI MAE 不劣于两个 online baselines；
5. 效果不只来自 highest-clear stratum；
6. mask invariance、q identity、evaluator parity、baseline parity 全部通过；
7. no-staleness 或 binary q 若等效，则按预注册规则删除相应组件。
8. forcing-alignment supporting checks 至少证明模型不完全忽略 time-aligned driver；否则收缩 forcing claim。

失败于 Vanilla 表示 explicit residual 不必要；失败于 PredRNN-online 表示没有 latent-assimilation advantage；open-loop collapse 表示统一 predictive-state paper 不成立。不得通过追加大模型、无关 downstream 或更多模块来救失败 claim。

## Implementation and Protocol Gates

1. explicit official split manifests，missing split hard fail；
2. official NetCDF `ndvi_pred` export，preserve time/lat/lon；
3. full-20 evaluator 与 official mask parity；
4. complete historical/future 24-channel weather；
5. observation/supervision mask separation 与 unrevealed-mask invariance；
6. q=0 identity、q=1 reset、partial-q staleness、predict-before-update、reveal-only-clear-pixel tests；
7. eight-cube overfit 与 Contextformer/PredRNN official parity；
8. one-seed proposed vs Vanilla/PredRNN-online gate 后才跑三种子。

## Downstream, Second Dataset and Large Models

当前不需要无关 downstream。固定 all-cube re-observation 是距离中心 claim 最近的能力测试。GreenEarthNet 已含 OOD-t/s/st，第二数据集能增强外部有效性但不是七页单一主张的必要条件。

AnySat/TerraMind initialization 或 FM 2×2 只有轻量机制成功后才适合后续扩展；现在加入会削弱归因并扩大风险。LLM 在本方法中没有角色。

## Compute and Timeline

先测 500–1000 updates 吞吐再报价 GPU-hours。residual 只在一半训练样本的一次 reveal 额外调用一次 `E/P`。gate-driven 预算约 8–12 full-run equivalents、正常约六周。以 2026-07-15 的本地状态（无 Stage2 artifacts）看，2026-07-28 AAAI-27 full-paper deadline 不是可信的 from-scratch 目标。
