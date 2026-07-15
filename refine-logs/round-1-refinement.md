# Round 1 Refinement

## Problem Anchor

- **Bottom-line problem**: 在稀疏、受云和 acquisition 条件影响的 Earth observations 中，学习一个能支持可靠长期预测的状态表示及其动力学，而不是只把未来卫星图像当作一个独立视频 cuboid 回归目标。
- **Must-solve bottleneck**: 当前框架和主流方法没有证明 latent 中哪些变化属于地表过程、哪些属于观测形成，也没有证明同一个短步状态转移能够组合到长期、解释中间观测并在新观测到来时被修正。
- **Non-goals**: 不恢复不可识别的绝对真实物理状态；不声称首个 EO world model、因果反事实、完整地球模拟、业务天气预报或通用 EO foundation model；当前不实现大规模概率生成。
- **Constraints**: 现有 Stage1/1.5 ViT 与 EarthNet/GreenEarthNet 代码可复用；当前本地只有 Stage1 EuroSAT probe，无 Stage1.5/Stage2 结果；主目标是 AAAI 级、7 页内可闭环的工作；本轮不改代码。
- **Success condition**: 在 GreenEarthNet 官方 OOD 协议上，shared-step latent model 与强 direct control 至少统计持平，并在中间状态组合、观测条件稳健或再观测校正中给出 direct/pixel-autoregressive 模型不具备的稳定收益；天气控制证明收益不是纯 calendar shortcut。

## Anchor Check

- **Original bottleneck**: 不是单纯提高未来帧精度，而是让预测状态既能保存历史中的不可见记忆，又能在新卫星观测到来时进行局部、可靠的校正。
- **Why the revised method still addresses it**: 将 belief 与单帧 observation embedding 明确分开；用 prior transition 保存并推进历史，用 mask-aware posterior update 吸收新证据。再观测后的未来预测直接检验“校正是否进入了有用的状态”，而非只看像素重建。
- **Reviewer suggestions rejected as drift**: 不引入 LLM、diffusion 或额外下游来追求“现代感”；它们没有解决当前接口错误。也不把 EO-WM 的极端天气响应复制为并列主贡献。

## Simplicity Check

- **Dominant contribution after revision**: 面向稀疏、云遮和空间局部可见 EO 的 innovation-aware masked posterior update，与统一受控 prior transition 组成可校正预测状态。
- **Components removed or merged**: 删除独立 context aggregator `A`，用同一 `F/U` 顺序过滤全部 context；删除 whole-belief latent target、EMA target、`L_range`、generic smoothness、semigroup claim；将 `phi` 因子化、foundation model、EO-WM matched-pair、无关下游移出核心。
- **Reviewer suggestions rejected as unnecessary complexity**: 不新增 stochastic RSSM、diffusion decoder、显式 uncertainty head 或多套 transition expert。当前确定性 filtering 已是检验核心假设的最小版本。
- **Why the remaining mechanism is still the smallest adequate route**: 新增训练部件只有 shared prior `F` 和 posterior update `U`；encoder、decoder、数据和官方任务均复用。若删除 `U`，论文退化为普通 recurrent forecaster；若删除 `F`，无法形成预测先验或评估校正后的持续影响。

## Changes Made

### 1. 修复 belief–observation 语义冲突

- **Reviewer said**: 历史 belief 不能强行对齐单帧 `E(o_t)`，否则会抹掉历史不可见信息。
- **Action**: 使用 `b_t^- = F(b_{t-1}^+, d_t, ...)` 与 `b_t^+ = U(b_t^-, E(o_t,m_t), m_t)`；删除完整状态 latent matching。
- **Reasoning**: observation embedding 是证据，belief 是证据与历史的汇总，两者不应具有同一训练目标。
- **Impact on core method**: “状态”不再只是 encoder latent 的别名，re-observation 也不再是 hard replacement。

### 2. 将 observation correction 升为唯一主机制

- **Reviewer said**: 最独特的 `U` 被当成 stretch，claim 与 evidence 不一致。
- **Action**: 训练时显式采样空观测/单次/两次未来再观测日程；Block B 把 learned update、hard replacement、no update 和 restart 作为正文比较。
- **Reasoning**: 只有后续预测的改善才能证明观测真正校正了预测状态。
- **Impact on core method**: correction 不再是“可选 downstream”，而是论文最关键的 capability test。

### 3. 删除伪 composition/semigroup 论证

- **Reviewer said**: 固定 `F_5` 重复调用是定义，不是 semigroup 证据；系统又受时间变化天气控制。
- **Action**: 不再声称 semigroup；改测 5–100 天退化、训练长度外外推、free/anchored gap 和 day-25/day-50 correction gain。
- **Reasoning**: 这些量可证伪，并直接对应长期 predictive-state 可靠性。
- **Impact on core method**: 主张从抽象术语转为可观察行为。

### 4. 统一 direct 与 recurrent control

- **Reviewer said**: 累计天气摘要与逐步天气不是公平机制比较。
- **Action**: 两者使用相同逐日/逐五日 weather trajectory、相同 target horizons、相同 supervision 密度和相同 encoder/decoder；同时报告参数、FLOPs 与更新数。
- **Reasoning**: 唯一被隔离的变量应是 endpoint mapping 与 shared state transition/update。
- **Impact on core method**: 若最终优势消失，必须承认机制未获支持。

### 5. Stage1.5 与天气响应降级为受 gate 控制的支持证据

- **Reviewer said**: GreenEarthNet 主任务固定 S2、neutral phi，严格 observation factorization 没有端到端生效；S1/S2 也非纯 nuisance pair。
- **Action**: 主任务只称“固定 S2 产品预测”；Stage1.5 只作 initialization ablation，先通过 predictive/semantic/no-collapse gate。Block C 在 Stage1.5 与 weather anti-shortcut 中预先二选一。
- **Reasoning**: 不让尚未验证的预训练叙事绑架主方法，也不复制 EO-WM 的独立 claim。
- **Impact on core method**: 即使 Stage1.5 失败，`F/U` 主线仍可被独立证伪。

## Revised Proposal

# Research Proposal: ObsWorld — Observation-Correctable Predictive States for Sparse Earth Observation

## Problem Anchor

- **Bottom-line problem**: 在稀疏、受云和 acquisition 条件影响的 Earth observations 中，学习一个能支持可靠长期预测的状态表示及其动力学，而不是只把未来卫星图像当作一个独立视频 cuboid 回归目标。
- **Must-solve bottleneck**: 当前框架和主流方法没有证明 latent 中哪些变化属于地表过程、哪些属于观测形成，也没有证明同一个短步状态转移能够组合到长期、解释中间观测并在新观测到来时被修正。
- **Non-goals**: 不恢复不可识别的绝对真实物理状态；不声称首个 EO world model、因果反事实、完整地球模拟、业务天气预报或通用 EO foundation model；当前不实现大规模概率生成。
- **Constraints**: 现有 Stage1/1.5 ViT 与 EarthNet/GreenEarthNet 代码可复用；当前本地只有 Stage1 EuroSAT probe，无 Stage1.5/Stage2 结果；主目标是 AAAI 级、7 页内可闭环的工作；本轮不改代码。
- **Success condition**: 在 GreenEarthNet 官方 OOD 协议上，shared-step latent model 与强 direct control 至少统计持平，并在中间状态组合、观测条件稳健或再观测校正中给出 direct/pixel-autoregressive 模型不具备的稳定收益；天气控制证明收益不是纯 calendar shortcut。

## Technical Gap

Contextformer 已建立 GreenEarthNet 的强 direct weather-conditioned forecast；PredRNN 和 UniTS v2 已覆盖 autoregressive forecasting；EO-WM 已覆盖 partial-observation/world-model framing 与天气响应 benchmark；RSSM/PSR/PlaNet 已建立 prior/posterior belief 的一般理论。因此，本工作不能以“使用世界模型”“五日递归”或“加入天气”作为新颖性。

仍未被这些工作直接闭合、且与 EO 数据特性一致的缺口是：未来新观测往往只在部分空间可信，其到达受云和 acquisition 稀疏性制约。现有 endpoint 或 pixel-AR forecaster 没有一个被明确训练和检验的接口，用于在保留历史隐状态的同时，只让可信的新观测局部修正预测 belief，并验证这种修正是否改善之后的长时预测。

## Method Thesis

- **One-sentence thesis**: ObsWorld 用一个 weather-controlled shared prior transition 推进预测 belief，并用一个由观测 innovation、空间 clear fraction 与 observation age 调制的 masked posterior update 吸收稀疏新 EO 证据，从而让同一状态同时支持开放循环预测和再观测后的持续校正。
- **Why this is the smallest adequate intervention**: `F` 解决“没有未来观测时如何推进”，`U` 解决“局部可信观测到来时如何更新”；两者之外不新增生成器、教师模型或任务 head。
- **Why timely**: 最近 EO world-model 工作已经说明“能生成未来”不等于“状态接口可信”。本方案把可校正性变成训练目标和主实验，而不是继续扩大生成模型。

## Contribution Focus

- **Dominant contribution**: 一个面向空间局部缺测 EO 的 observation-correctable predictive-state interface：shared controlled prior `F` + innovation-aware masked update `U`，以及使校正影响后续预测的训练日程。
- **Conditional supporting contribution**: repaired EO pretraining 是否改善状态初始化；只有预注册 gate 通过才保留为正文支持项。
- **Explicit non-contributions**: 不声称 prior/posterior filtering 的一般理论首创；不声称首个 EO world model；不把五日递归、天气敏感性、phi disentanglement、foundation model 或下游分类作为平行贡献。

## Proposed Method

### Complexity Budget

- **Frozen/reused backbone**: 现有 S2 observation encoder `E`、S2 decoder `H`、GreenEarthNet 数据与官方 evaluator；先冻结 encoder/decoder，pilot 后只允许最后少量 block 低学习率微调。
- **New trainable components**: (1) shared five-day controlled transition `F`；(2) masked innovation update `U`。`U` 内的 projection/gate 属于同一更新单元，不另计模块。
- **Tempting additions intentionally not used**: diffusion/stochastic decoder、LLM、VLM teacher、foundation-model 2×2、uncertainty head、多传感器 Stage2、额外 downstream、transition experts。

### State and Inputs

- `b_t^- ∈ R^{N×d}`: 在时刻 `t` 观测到来前的 spatial predictive prior；包含从历史保留的不可见记忆。
- `b_t^+ ∈ R^{N×d}`: 吸收时刻 `t` 可用观测后的 posterior belief。
- `e_t = E(o_t, m_t)`: 当前 S2 RGBN 与显式云/有效像素 mask 的 observation evidence；遮挡区域使用 mask token 和 mask feature，而非仅乘零。
- `D_t`: 与官方协议一致的历史/未来 weather trajectory；每个五日 transition 内保留逐日顺序，不压成只与 horizon 相关的累计摘要。
- `C_t`: 绝对日期/DOY；`G`: DEM/static；`a_t`: 每个 patch 距离最近可信观测的 age；`q_t∈[0,1]^N`: patch clear fraction。
- GreenEarthNet 主任务为固定 S2 product，因此主模型不使用虚构的 neutral `phi`，也不作 acquisition-factorization claim。

### System Overview

```text
learned b_init
    |
    |  context frame 1: U(b_init, E(o1,m1), q1, age1)
    v
   b1+
    |
    |  for every later context frame:
    |  bt- = F(b{t-1}+, Dt, Ct, G, age)
    |  bt+ = U(bt-, E(ot,mt), qt, age)
    v
context posterior b0+
    |
    |  future step k:
    |  bk- = F(b{k-1}+, Dk, Ck, G, age)
    |  prediction = H(bk-)
    |  if no observation: bk+ = bk-
    |  if observation arrives: bk+ = U(bk-, E(ok,mk), qk, age)
    v
open-loop or observation-corrected future rollout
```

同一 `F/U` 过滤 context 与 future，删除独立 context aggregator，避免 context state 和 rollout state 来自不同接口。若第一帧之前没有可用状态，`b_init` 是一个小的 learned spatial token，第一帧由 `U` 建立 posterior。

### Shared Controlled Prior `F`

`F` 复用现有 latent dynamics blocks，输入上一 posterior、五日内逐日天气 encoding、绝对日历、DEM 和 observation age：

```text
b_t^- = F_5(b_{t-1}^+, EncD(D_{t-4:t}), C_t, G, a_t)
```

`F_5` 在所有 context/future steps 共享参数。共享本身不是贡献；其作用是给 `U` 提供一个在无观测时可持续推进、在有观测时可被修正的 prior。论文使用“controlled recurrence/open-loop propagation”，不使用 semigroup 首创语言。

### Innovation-Aware Masked Posterior Update `U`

`U` 不把 belief 替换为单帧 encoder latent。对每个 spatial token：

```text
e_t   = E(o_t, m_t)
r_t   = e_t - Q(b_t^-)
K_t   = q_t · sigmoid(MLP([b_t^-, e_t, r_t, q_t, a_t]))
b_t^+ = b_t^- + K_t ⊙ R(r_t)
```

其中 `Q/R/MLP` 是一个轻量 residual update 单元；`q_t=0` 时严格保持 `b_t^+=b_t^-`。`r_t` 只作为 update 输入，不把整个 belief 训练成单帧 observation latent。`age` 让模型区分刚观测与长期未观测区域，`q_t` 避免当前代码中“5% clear 即整 token 有效”的过松规则。

该形式受到 learned filtering/Kalman gain 启发，但不声称通用 filtering 理论创新；EO 特异点是 patch-level cloud validity、稀疏 arrival schedule 与后续遥感预测的联合训练和评测。

### Observation Decoder

`H(b_t^-)` 输出固定 S2 RGBN；官方主指标由输出与 mask 计算 NDVI。若再观测发生，先记录 prior prediction，再形成 `b_t^+` 供后续时刻使用。decoder 已经 sigmoid 到 `[0,1]`，故不再设置 `L_range`。

### Training Plan

每个样本包含官方 context 与 20 个五日 future frames。训练采用两种 mini-batch 日程，而不是同时复制两条昂贵计算图：

1. **Open-loop batch**: future observation schedule 为空，所有 future steps 只用 `F` 推进。
2. **Correction batch**: 在 future 中随机选 1–2 个有足够 clear support 的时刻暴露观测，先预测再用 `U` 更新，继续预测后续帧；同时对观测 mask 做额外 dropout，模拟更稀疏/局部到达。

初始建议按 1:1 混合，最终比例只由 Val pilot 决定。所有二十个 future horizons 在各模型中具有相同 target exposure；若采样 rollout length，使用 inverse-frequency weighting，避免短 horizon 被过度监督。

训练损失只保留与可观察主张直接相关的三类：

```text
L = λ_prior · L_masked_RGBN/NDVI(H(b_t^-), o_t)
  + λ_post  · L_masked_RGBN/NDVI(H(b_t^+), o_t)       # 仅 reveal 时刻
  + λ_after · L_future_after_update                    # reveal 之后的未来
```

- `L_prior` 覆盖 open-loop batch 及每次 update 前的预测；
- `L_post` 防止 update 忽略观测，但不是主要成功证据；
- `L_after` 是关键，使 update 必须改善后续预测而非只复制当前观测；
- 删除 whole-state latent cosine/Huber target、EMA target adapter、generic temporal smoothness、KL 和 range loss；
- `λ` 不预设为“最优”，先用 500–1000 update pilot 的 loss/gradient scale 与 Val 曲线锁定，再不看 OOD test。

训练顺序：protocol sanity → 冻结 `E/H` 的短序列 pilot → rollout length 1/2/4/8/12/20 curriculum → 只在必要时低学习率解冻最后 encoder blocks。BPTT 若超显存，按 state carry 的固定 chunks 做 gradient checkpointing，但不截断前向状态。

### Inference

- **官方 open-loop forecast**: 用全部 context 通过 `F/U` 得到 posterior，未来 100 天不暴露任何目标观测。
- **re-observation forecast**: 在 day 25 或 day 50 提供当日带原始云 mask 的 S2 观测，用 `U` 更新一次，再只评价之后的 horizons。
- **operational boundary**: 未来 EOBS/天气在 benchmark 中是 oracle/reanalysis forcing，因此结果称 forcing-conditioned hindcast/scenario forecast，不称真实业务天气预报。

### Optional Supporting Component: Stage1.5 Initialization Gate

Stage1.5 不进入主方法定义，也不以 S1/S2 近时配对证明严格 nuisance disentanglement。它只作为 `E/H` initialization 候选，先满足：

1. 使用真正 repaired state-bridge checkpoint，而非旧 bypass checkpoint；
2. held-out geography 上 future-NDVI/predictive probe 不低于 S2-only/Stage1；
3. semantic utility 不坍塌；
4. acquisition probe 使用真实 forward path、独立 train/val/test、平衡指标、calendar/geography controls；
5. 最终 Stage2 Val skill 至少不发生实质下降。

若 gate 失败，主模型改用 S2-only/Stage1 initialization，并从正文贡献中删除 Stage1.5；不追加更多 probe 挽救。若没有严格 product-pair 数据，只称 cross-sensor predictive pretraining，不称 state/observation 可识别分解。

### Modern Primitive Usage

- **Used**: 复用预训练 EO encoder，并采用现代 predictive-state/filtering interface。
- **Not used**: LLM/VLM/diffusion/RL，因为它们不会修复 belief–observation 接口，也不为固定 S2 factual forecast 提供更小的机制。
- **Foundation model role if later explored**: 只作为冻结 encoder 的 appendix ceiling，不进入主模型或 2×2 主实验；当前直接删除。

### Fair Direct Control

`Direct-Seq` 与 ObsWorld 必须使用同一 observation encoder/decoder、相同完整 weather sequence、相同 target horizons 与 supervision density：

```text
Direct:   H(F_direct(b0+, EncD(D_1:h), C_h, G, h))
ObsWorld: H(F_5(...F_5(b0+, D_1)..., D_h))
```

比较同时报告 Params、训练 updates、wall-clock/FLOPs。若 direct 训练六个 horizon，ObsWorld 也只能用相同六个；更推荐两者均监督全部 20 个。PredRNN 作为成熟 recurrent baseline，不能只用较弱 Pixel-AR 自制对照。

### Failure Modes and Falsifiers

- **U 只复制当前帧**: `L_post` 好但 reveal 后未来不改善；结论为 correction 失败，不能用 reconstruction 掩盖。
- **U 破坏历史**: learned U 不如 hard/no update，或清晰区域改善但遮挡区域恶化；缩小 gate/加强 `q=0` identity，若仍失败则否定主机制。
- **F 长期漂移**: official endpoint 和 5–100d curve 均显著落后 direct/PredRNN；停止 world-model claim。
- **Stage1.5 有害**: gate 失败即删除支持 claim。
- **天气 shortcut**: true weather 不优于 calendar/no/wrong-year；只称 calendar-conditioned 或删除 weather-response 描述。
- **协议污染**: split 缺失时 hard fail，manifest hash 与官方 evaluator parity 未通过前不跑正式实验。

### Novelty and Elegance Argument

新颖性不在 `F`、`U` 或 filtering 公式的单独存在，而在一个明确针对 EO 局部云遮/稀疏再观测的最小训练与评测闭环：prior 保留历史，mask/age-conditioned innovation 只校正可信区域，校正价值由之后的预测而非当前重建证明。相较 Contextformer 的 endpoint forecast、PredRNN/UniTS 的 autoregression、EO-WM 的 weather-driven generation，本方案把“新观测能否形成有用 posterior”设为中心机制和正文证据。

## Claim-Driven Validation Sketch

### Claim 1（主）: Learned masked posterior update creates a useful observation-correctable predictive state

- **Minimal experiment**: GreenEarthNet open-loop + day-25/day-50 re-observation；比较 no update、restart from observation、hard latent replacement、learned `U`。
- **Baselines/controls**: matched Direct-Seq、PredRNN；同天气、同 targets、同 encoder/decoder、同预算。
- **Metrics**: 官方指标；5–100d horizon curve；只在 update 之后计算的 correction gain/AUC；按 cloud fraction、missingness rate、time-since-observation 分层。
- **Expected evidence**: 官方 open-loop 达到强 baseline 合理量级；learned U 稳定优于 no/hard/restart，并在 long-horizon degradation、missingness robustness、assimilation gain 三项中至少两项优于匹配 direct/PredRNN。否则主 claim 被证伪。

### Claim 2（条件支持）: Repaired EO pretraining improves initialization without erasing predictive content

- **Minimal experiment**: scratch、S2-only/Stage1、old bypass、repaired Stage1.5，先做 gate，随后只对通过者做 Stage2 transfer。
- **Metrics**: held-out future probe、semantic probe、balanced acquisition probe、Stage2 Val/OOD skill；3 seeds/CI。
- **Expected evidence**: predictive/semantic utility 不降且 Stage2 收敛或 skill 改善；否则不保留该 claim。

## Three Core Experiment Blocks

### Block A — Official factual forecast

- GreenEarthNet `ood-t_chopped` 为主表，OOD-s/OOD-st 为紧凑泛化列；官方 R²、RMSE、NSE、|bias|、climatology outperformance、RMSE25。
- Baselines: persistence/climatology、Contextformer、PredRNN、可同协议运行时的 UniTS；Direct-Seq；final ObsWorld。
- 三种子；location/tile cluster bootstrap；Val 锁配置后一次 OOD test。

### Block B — Predictive state and observation correction

- open-loop、observation-anchored、no update、restart、hard replacement、learned U；day 25/50；多种 cloud/missingness。
- 只评价 update 后 future，报告 horizon curve 与 correction gain；这是正文最重要的机制图/表。

### Block C — Pre-registered one-of-two support block

- M0 阶段先跑 Stage1.5 gate；若通过，Block C 只做 initialization/state-bridge ablation。
- 若 gate 失败，Block C 改为 true/no/calendar/wrong-year weather anti-shortcut controls。
- 选择在看 OOD test 前锁定；不会在同一主稿中同时扩张两套证据。

明确删除无关 downstream、Foundation Model 2×2、完整 EO-WM benchmark、概率生成和额外新数据集。re-observation correction 就是最贴合主张的 capability evaluation，不另叫下游任务。

## Experiment Handoff Inputs

- **Must-prove claim**: `U` 不只是当前帧重建，而是形成能改善后续预测的 posterior。
- **Must-run ablations**: no/hard/restart/learned update；Direct-Seq/PredRNN；same-weather/equal-supervision fairness；mask/age deletion。
- **Critical protocol**: explicit `val_chopped/ood-t_chopped/ood-s_chopped/ood-st_chopped` manifests，missing split hard fail，GreenEarthNet NetCDF `ndvi_pred` 官方 evaluator 与官方 masks。
- **P0 implementation prerequisites**: 修复 split fallback、输出格式、mask parity、full historical/future weather、旧 checkpoint path；实现 sequential context `F/U` 和 open-loop/correction schedules。
- **Highest-risk assumptions**: GreenEarthNet future 中存在足够可信 day-25/day-50 observations用于机制评测；`U` 的校正能延续而非短暂复制；Stage1.5 checkpoint 可用。

## Compute & Timeline Estimate

- **GPU-hours**: 先以 500–1000 updates 测量 `sec/update × updates × seeds / 3600`；不在无吞吐证据时编造总时长。
- **Run budget**: protocol/sanity → 1-seed direct/PredRNN/ObsWorld pilots → 只有过 gate 的模型跑 3 seeds；目标约 8–12 full-equivalent runs，而非原计划 12–18+。
- **Timeline**: 官方协议和实现约 1–2 周，pilots/gates 约 1–2 周，主 seeds/统计约 2 周；这是正常六周路线。以 2026-07-15 的状态，没有现成 Stage2 结果时不应把 2026-07-28 AAAI-27 full-paper deadline 当作可信目标。
