# ObsWorld 中心叙事定稿：不要放弃世界模型，要放弃不可验证的强宣称

**Date**: 2026-07-15  
**Status**: framing revision after method proposal READY

## Bottom Line

上一版为了规避 `first EO world model`、完整地球模拟、物理真实状态和因果天气响应等 overclaim，把论文整体压缩成 observation-aligned correction。这保护了方法严谨性，却把 **系统问题** 和 **方法创新** 错误地合并了。

最终层级应是：

1. **领域母叙事**：Earth observation 是对持续演化地表世界的稀疏、局部、受云影响的观测；任务是 partial-observation world modeling。
2. **系统身份**：ObsWorld 是 observation-correctable EO world model。
3. **方法级唯一新意**：observation-aligned, visibility-safe residual correction。
4. **证据闭环**：同一个 belief-state model 同时通过 open-loop world rollout 与 partial-observation belief correction。
5. **claim boundary**：模拟 EO-observable Earth-surface evolution，而非完整真实地球或因果数字孪生。

因此：**world model 回到标题、摘要、引言和实验组织中；aligned residual 仍是唯一可归因的方法创新。**

## Recommended Title and Thesis

Title:

> **ObsWorld: An Observation-Correctable World Model for Sparse Earth Observation Forecasting**

Proposal-stage thesis:

> **We cast sparse Earth observation forecasting as belief-state world modeling: ObsWorld rolls a history-dependent predictive belief forward under supplied forcing, decodes future satellite observations, and corrects that belief from visibility-aligned observation residuals. We hypothesize that this correction improves subsequent rollouts without sacrificing open-loop forecast accuracy.**

Result-stage thesis（仅在实验成立后）：

> **We cast sparse Earth observation forecasting as belief-state world modeling: ObsWorld rolls a history-dependent predictive belief forward under supplied forcing, decodes future satellite observations, and corrects that belief from visibility-aligned observation residuals, improving subsequent rollouts without sacrificing open-loop forecast accuracy.**

## Why This Is a World Model

```text
Predict:  b_t-     = F_5(b_{t-1}+, u_t)
Observe:  x_t-     = H(b_t-)
Update:   b_t+     = U(b_t-, x_t, x_t-, m_obs_t)
Imagine:  b_{t+k}- = F_5^k(b_t+, u_{t+1:t+k})
```

| Contract | ObsWorld | Evidence |
|---|---|---|
| history-dependent belief | `b_t` 汇总全部可用历史，不绑定单帧 latent | sequential filtering / state ablations |
| temporal dynamics | shared five-day `F_5` | 100-day open-loop horizon curve |
| exogenous conditioning | weather + DOY + static geography | true/no-weather + correct/shuffled-time forcing |
| observation model | learned `H: b -> RGBN`；NDVI 由 Red/NIR 确定性计算 | official forecast fidelity + qualitative trajectories |
| partial-observation update | `U(b^-, aligned residual, q, staleness)` | day25/day50 all-cube paired correction |
| open-loop imagination | future `a=0`，repeated `F_5/H` | locked GreenEarthNet OOD rollout |

EO world model 不要求机器人 action；这里的 `u_t` 是外生环境 forcing。它也不要求 latent 等于唯一物理状态；`b_t` 是对未来 EO observation 足够的 predictive belief。

## What “Simulating the Real World” Means Here

Allowed:

> **simulating EO-observable Earth-surface evolution under supplied meteorological, calendar, and geographic forcing**

Not allowed:

- simulating the complete real Earth；
- recovering the unique physical land-surface state；
- causal/counterfactual weather simulation；
- operational forecasting when future reanalysis/oracle forcing is supplied；
- calling `H` a physical sensor/radiative-transfer simulator；
- claiming stochastic or calibrated multimodal futures from a deterministic model。

这个边界不会削弱 world-model 叙事，反而把“世界”具体化为论文确实能观测和验证的 EO-observable dynamics。

## Introduction Logic

1. **Reality**: 地表连续演化，而 satellite observations 稀疏、云遮且只局部揭示世界。
2. **Limitation**: 预测未来 image cuboid 不足以形成可持续的 world belief；现实中会有新观测到达，模型必须把它与自己预期看到的内容对齐并修正。
3. **World-model requirement**: EO world model 应维护 belief、在 forcing 下推进、解码观测、吸收新证据。
4. **Method gap**: generic fusion 没有显式比较同一可见区域中的 real observation 与 prior prediction，也不保证 no-evidence state identity。
5. **ObsWorld**: visibility-aligned residual + exact no-evidence identity + future-only correction supervision。
6. **Evidence**: official open-loop rollout + paired post-observation rollout improvement。

与 EO-WM 的一句差异：

> **EO-WM emphasizes weather-driven EO generation and driver-response diagnostics, whereas ObsWorld studies how partial new observations can safely correct a history-dependent world belief and improve subsequent rollouts.**

## Contribution Bullets

1. **System/formulation**: a partial-observation EO world model unifying forcing-conditioned open-loop rollout and online belief correction in one transition–observation–update state machine；不声称 first。
2. **Method**: a visibility-safe observation-aligned residual update using the same visibility operator and feature space, exact no-evidence identity, and future-only supervision。
3. **Evidence**: official 100-day open-loop OOD rollout plus paired all-cube correction against capacity-matched VanillaFilter and PredRNN-online。

Recurrence、weather、Stage1.5、phi、FM、downstream 与 diffusion 不列为平行贡献。

## Experiment Storyline

### RQ1: Open-Loop Earth-Observation World Rollout

- GreenEarthNet official full-20 / 100-day OOD-t；
- persistence、climatology、Contextformer、PredRNN、matched Direct-Seq、ObsWorld；
- official NDVI RMSE non-inferiority + horizon-wise degradation curve；
- 证明 world model 能推演，不要求单靠 aggregate metric 宣称全局 SOTA。

### RQ2: Partial-Observation Belief Correction

- all cubes；固定 day25/day50 reveal；
- same-checkpoint no update、VanillaFilter、PredRNN-online、aligned residual；
- paired gain-AUC + absolute post-reveal error + clear-fraction strata；
- 证明 belief 能被真实局部证据校正，而不是只生成一次未来 cube。

### RQ3: World-Model Contract and Mechanism Ablations

- explicit residual vs generic fusion；
- exact `q=0` identity / unrevealed-mask invariance；
- continuous q / staleness deletion；
- independently trained true-weather/no-weather，作为 driver utility 的辅助证据；
- same-checkpoint correct-time/time-shuffled-or-wrong-year forcing，correct-time 更优是 time-alignment 的关键证据。

Forcing checks 只证明模型使用 time-aligned driver。若失败，删除 forcing-conditioned 强调；不得升级成因果干预 claim。

## Downstream and Foundation Models

当前不需要 unrelated downstream。re-observation correction 本身就是最接近 world-model claim 的 capability test；普通分类或分割不能证明 belief update 改善未来 rollout。

Foundation-model encoder 的 2×2 只回答 scale interaction：

```text
small encoder + Direct
small encoder + ObsWorld
FM encoder    + Direct
FM encoder    + ObsWorld
```

它应在核心机制通过后作为 Appendix 或后续扩展。只有未来把 claim 扩大为 transferable/general EO world model 时，多数据集 downstream 与 FM 才成为必要证据。

## Final Decision

不再使用“论文不围绕世界模型”这类措辞。统一使用：

> **World model is the system-level problem and identity; observation-aligned residual correction is the method-level novelty.**

需要拒绝的不是 world model，而是无法由当前任务和实验验证的物理、因果、首创与完整地球宣称。
