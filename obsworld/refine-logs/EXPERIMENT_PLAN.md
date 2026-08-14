# Experiment Plan

> **2026-07-16 final protocol.** This plan uses only the already audited raw
> `EarthNet2021/earthnet2021x` release. `train_dev → val_dev` is the only
> development/selection route; locked results use IID/OOD as the main table and
> Extreme/Seasonal as supplementary stress tracks. EarthNetScore (ENS) is the
> official endpoint. GreenEarthNet and `*_chopped` tracks are a separate future
> extension and must never be mixed into this plan's data, metrics or tables.

**Problem**: 将稀疏、云遮 Earth observation forecasting 建模为 observation-correctable world modeling：同一个 history-dependent belief 既能在给定外生 forcing 下开放循环推演 EO-observable Earth-surface evolution，也能在局部新观测到来后被可靠校正。  
**Method Thesis**: shared prior transition 推进 world belief；learned observation model 解码未来 RGBN，NDVI 由 Red/NIR 确定性计算；真实 reveal 与 prior decoded prediction 经相同 observation mask/encoder 后形成 aligned residual，再由 visibility-safe update 校正 belief；reveal-time update 只由之后的 rollout loss 监督。  
**Date**: 2026-07-15

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|---|---|---|---|
| C0（系统身份/能力前提，不是首创 claim）ObsWorld 是 forcing-conditioned、observation-correctable EO world model | world-model 母叙事必须由 transition–observation–update 与 open-loop 行为支撑，不能只靠命名 | official 100-day open-loop rollout 对 strong direct 非劣；horizon degradation 可控；time-aligned forcing 被使用；新观测可改变后续 rollout | B1, B2, B3 |
| C1（唯一方法新意）observation-aligned residual correction 形成更有用的 predictive posterior | 这是相对 generic RSSM/filtering 与 online recurrence 唯一需要成立的机制增量 | 固定 day-25/day-50 all-cube protocol 的 paired gain-AUC 同时优于 capacity-matched VanillaFilter 与 PredRNN-online；absolute post-reveal MAE 不更差；收益不来自参数、监督、晴朗筛样或 mask 泄漏 | B2, B3 |

**Anti-claims to rule out**:

- 收益只来自在线看到了未来观测，而不是 update 结构；
- 收益只来自参数更多、target exposure 更多或天气输入更完整；
- 只选择了晴朗/容易 cube，或只在高 clear-fraction 层有效；
- update 只是复制当前 reveal frame，没有改善后续预测；
- latent filter 并不优于标准 PredRNN hidden-state assimilation；
- 结果来自 split 混入、旧 EarthNet evaluator、错误 mask 或输出格式；
- Stage1.5 或天气响应被不必要地包装成第二贡献。
- “模拟世界”被误写成恢复完整真实地球、物理 sensor simulation 或因果数字孪生。

## Paper Storyline

- **Main paper must prove**: RQ1 的 open-loop world rollout 地基成立；RQ2 证明局部新观测能校正 belief 并改善后续 rollout；RQ3 在强 online baselines 下隔离 innovation correction，并证明 `q/age` 必要或应被删除。
- **Required support**: 两类检查都运行；true-weather/no-weather 是 driver utility 辅助证据，correct-time 优于 time-shuffled/wrong-year 是 time-alignment 关键证据；只作能力证据，不作新贡献或因果 claim。
- **Appendix can support**: Extreme/Seasonal 紧凑表、clear strata 全表、hard replacement、Stage1/Stage1.5 initialization、land-cover/season failure panels、RGBN diagnostics、Params/FLOPs。
- **Experiments intentionally cut**: CropHarvest/Sen1Floods11 等无关下游、Foundation Model 2×2、LLM/VLM、diffusion/uncertainty、完整 EO-WM matched-pair benchmark、多传感器 Stage2、额外 benchmark。UniTS 只有能按同一 raw EarthNet2021x manifest、NPZ 导出和 EarthNetScore 重跑时才进数字表。

## Experiment Blocks

### RQ1 / Block 1: Open-Loop Earth-Observation World Rollout

- **Claim tested**: C0 的必要前提——final belief-state model 首先是可信的 100-day open-loop world forecaster。
- **Why this block exists**: correction 不能弥补 open-loop 任务本身失败；官方协议对齐也是所有机制实验的地基。
- **Dataset / split / task**: raw EarthNet2021x `train_dev` 训练；`val_dev` 选择配置/早停；锁定后 IID 与 OOD 为主测试；Extreme 与 Seasonal 仅作紧凑压力测试列。
- **Compared systems**:
  - reference: persistence、climatology；
  - strong direct: Direct24 matched control；Contextformer 仅在相同 raw manifest/ENS 协议可复现时加入；
  - strong recurrent: final ObsWorld open-loop；PredRNN 仅在相同协议可复现时加入；
  - UniTS 仅在代码发布且能生成匹配的 EarthNet `highresdynamic` NPZ 时加入。
- **Metrics**:
  - decisive: official EarthNetScore（ENS，越高越好）及 MAD/OLS/EMD/SSIM 分量；
  - secondary: horizon-wise RGBN/NDVI MAE、Params、FLOPs、wall time；这些解释指标不混入 official rank。
- **Setup details**:
  - context 10、future 20、五日步长；全部模型使用相同官方 supervision masks 和 24-channel five-day weather；
  - Direct 与 ObsWorld 相同 encoder/decoder initialization、20 targets、target density、data samples 和 tuning budget；
  - `H` 必须共同训练，不能冻结随机 decoder；`E` 初期冻结，若解冻则 matched variants 在相同步数/LR 解冻；
  - 3 seeds；只用 `val_dev` 锁配置；IID/OOD 各只测试一次；按 tile/location cluster bootstrap，不把像素当独立样本。
- **Success criterion**: 预注册 `Delta_open = ENS_Direct - ENS_ObsWorld`、`delta_NI=0.01 ENS`；OOD 上 paired tile-cluster bootstrap 的 one-sided upper 95% CI 必须 `<0.01`，IID 不得发生事实性崩溃。外部方法如进入主表，必须在相同协议达到合理量级，避免 matched Direct 自身过弱。
- **Failure interpretation**: 若稳定落后强基线且 protocol 无误，C0 的 unified world-model paper 不成立；可保留 direct task baseline，但不能靠 correction 或追加任务掩盖 open-loop collapse。
- **Table / figure target**: Main Table 1（IID/OOD ENS）+ horizon-wise degradation curve；Extreme/Seasonal 与完整效率列放 Appendix。
- **Priority**: MUST-RUN

### RQ2 / Block 2: Partial-Observation Belief Correction

- **Claim tested**: C1 的主体——explicit innovation + continuous clear support + age 是否比 generic filtering 和 pixel recurrent assimilation 更有用。
- **Why this block exists**: no-update/hard replacement 是弱对照；只有击败强 generic/online baselines，才能把结果归因于所提机制。
- **Dataset / split / task**: 同一 raw EarthNet2021x `train_dev` cubes；`val_dev` 固定 protocol 开发；锁定后在 IID/OOD 的所有 cubes 评估。
- **Compared systems**:
  - final ObsWorld with reveal disabled（同一模型的 no-update trajectory）；
  - capacity-matched VanillaFilter：获得同一个 `z_obs/z_pred/q/staleness` 与额外 encoder forward，但隐式融合；与 residual update 参数/FLOPs差 ≤5%；
  - PredRNN-online：reveal 时输入 masked true RGBN + mask，更新 recurrent state 后继续；
  - proposed `U_innov`；
  - hard replacement 只留 Appendix 单行。
- **Metrics**:
  - primary: day25/day50 等权的 cube-level NDVI-MAE paired gain-AUC，形成 `D_Vanilla` 与 `D_PredRNN-online` 两个 co-primary differences；
  - required support: absolute post-reveal NDVI MAE 不劣于两个 baseline；
  - secondary: NDVI RMSE、RGBN MAE、horizon error/gain curves；clear-fraction strata `[0,.1), [.1,.3), [.3,.6), [.6,1]` 及每层 cube/pixel support。
- **Setup details**:
  - strict mask separation: `m_obs/q_obs` 只进 model/staleness；`m_rgb_sup/m_ndvi_sup` 只进 loss/eval；future no-reveal `a=0`；
  - evaluation 对所有 cube 固定 day 25 和 day 50，不设置 eligibility/clear threshold；`q_obs=0` 严格 no-op；使用所有方法共同、只由 GT 定义的 validity set；
  - train schedule 完全相同：50% no reveal、50% exactly one reveal；step 2–15 均匀采样且与 clear fraction 独立；pre/post segments 各自按长度平均；
  - reveal step 先预测、再消费观测；当前 reveal 帧无 posterior reconstruction；reveal-time invocation 只由后续 loss监督；
  - 3 seeds；same-seed/same-cube 先配对，seeds/cubes在 geographic tile 内聚合，10,000 paired tile-cluster bootstrap；两个 co-primary 用 Holm 控制 family-wise alpha 0.05。
- **Success criterion**: Holm-adjusted `D_Vanilla>0` 与 `D_PredRNN-online>0` 同时成立；absolute post-reveal NDVI MAE 不更差；总体收益不能只由最高-clear stratum贡献。
- **Failure interpretation**:
  - `U_innov ≤ VanillaFilter`: explicit innovation 不成立，最多是 generic EO filtering paper；
  - `U_innov ≤ PredRNN-online`: latent correction 没有相对成熟 recurrent assimilation 的证据，停止强 claim；
  - 只在高-clear 层有效: 把 claim 限制到 adequate observation support；
  - reveal 当下好、后续无增益: update 只复制观测，主张失败。
- **Table / figure target**: Main Table 2 + Main Fig. 2（post-reveal curves/strata）。
- **Priority**: MUST-RUN

### RQ3 / Block 3: World-Model Contract and Mechanism Ablations

- **Claim tested**: C1 的最小机制是否确实需要 innovation、continuous `q` 和 age；同时检查结论不依赖未经证实的 Stage1.5 或 calendar shortcut。
- **Why this block exists**: 既隔离组件必要性，也允许在证据不足时删除无用部件，保持方法简洁。
- **Dataset / split / task**: 首先在 `train_dev/val_dev` 做 one-seed decision pilots；只把 `val_dev` 锁定后的 final deletion rows 在 IID/OOD 评估。Stage1.5 行默认 Appendix；forcing-alignment 是 required supporting evidence。
- **Compared systems**:
  - residual update full；w/o explicit residual（即 VanillaFilter）；w/o evidence-weighted staleness；binary token mask 替代 continuous `q`；
  - initialization appendix: Stage1/S2-only vs repaired Stage1.5，使用同一 Stage2；
  - forcing contract: independently trained true-weather/no-weather；同一 checkpoint correct-time/time-shuffled-or-wrong-year weather，后者必须支持 correct-time 更优。
- **Metrics**: official/post-reveal metrics；q=0 identity/age 单元测试；predictive/semantic Stage1.5 gate；weather sanity 只看 forecast correctness，不把 output sensitivity 称因果。
- **Setup details**:
  - 如果 w/o-age 在 `val_dev` 与 full 等价，最终方法删除 age；如果 binary-q 等价，优先更简单版本；此选择在 IID/OOD 前完成；
  - Stage1.5 只有 predictive/semantic utility 与 Stage2 `val_dev` 都不降才显示，且永不升级为第二 claim；
  - forcing sanity 不扩展成 EO-WM 式因果响应矩阵，也不称 counterfactual realism。
- **Success criterion**: 至少 explicit innovation 相对 matched Vanilla 必须成立；age/q 只有有稳定增益才保留。至少一个严谨 forcing comparison 证明模型使用 time-aligned driver，否则删去 forcing-conditioned 强调。Stage1.5 负结果不影响主 claim。
- **Failure interpretation**: deletion 不降即删组件；Stage1.5 gate 失败即用 Stage1/S2-only；天气不可区分即删除 driver-use 解释。
- **Table / figure target**: 一个 compact ablation table；其余 Appendix。
- **Priority**: MUST-RUN for innovation row；forcing contract 为 MUST-RUN supporting；age/q/Stage1.5 为 NICE-TO-HAVE/decision-gated

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|---|---|---|---|---|---|
| M0 Protocol | 锁死 split、mask、weather、export、evaluator | R001–R006 | explicit manifests；missing split hard fail；EarthNet NPZ/ENS/provenance 小样本闭环；availability/supervision 分路；unrevealed-mask invariance 与 q/staleness/reveal tests 全过 | CPU/data work + <0.1 run | 静默混 split、错误 ENS 输入、future mask 泄漏 |
| M1 Sanity/Baselines | 证明训练链与 matched controls 可信 | R010–R014 | 32–128 cube overfit；Direct/Rollout/Partition 收敛与导出闭环；外部 baseline 仅在同协议可复现时加入 | 2–3 pilots | decoder/driver/input parity 错误 |
| M2 Mechanism Pilot | 单 seed 检验 C1 是否值得继续 | R020–R023 | U 必须优于 Vanilla 与 PredRNN-online 的 `val_dev` aggregate；open-loop 不崩 | 3–4 pilots | innovation 无增量、BPTT 显存 |
| M3 Simplify | 删除无用 age/q/Stage1.5 部件 | R030–R034 | 用 `val_dev` 选最小 final method并锁定；不看 IID/OOD | 2–4 short/partial runs | scope creep、按 test 选模型 |
| M4 Confirm | 最终 systems 三种子与一次 OOD | R040–R049 | C1 CI 支持；否则按 stop rule 降级/停止 | 约 6–9 full runs，依 M2 gate | 方差大、效果只在晴朗层 |
| M5 Polish | 紧凑 OOD/failure/appendix | R050–R054 | 只做不改变主结论的诊断 | 主要 inference + ≤2 trains | 为救叙事无限追加 |

## Compute and Data Budget

- **Total estimated GPU-hours**: 项目本地 WorldModel 环境已复现，并已通过 106 项单元/合成集成测试；真实训练吞吐仍未知。M1 每个系统先测 500–1000 updates 的 `sec/update`、peak memory、eval time；使用 `sec_per_update × updates × seeds / 3600 + 15% eval/checkpoint`。
- **Full-run budget**: gate-driven 约 8–12 full-equivalent runs；M2 若失败，不运行三种子、Extreme/Seasonal 或 appendix trains。
- **Data preparation needs**: frozen raw EarthNet2021x manifests；完整 8 E-OBS variables 的 mean/min/max 24 features及历史 context weather；official cloud/SCL/land-cover masks；EarthNet `highresdynamic` NPZ prediction template。
- **Human evaluation needs**: 无。qualitative 只做 failure diagnosis。
- **Biggest bottleneck**: Direct24/Rollout24/Partition24、exporter 和 scorer provenance 已实现；仍缺真实 manifest/stats/preflight、真实小样本 overfit、online reveal/update 分支以及最终 Stage1.5 initializer。

## Risks and Mitigations

- **Risk: official protocol 与当前代码不一致**  
  **Mitigation**: M0 是硬 gate；`train_dev/val_dev/iid/ood/extreme/seasonal` manifests、EarthNet NPZ scorer、NetCDF schema、mask/weather parity 未通过前不训练。
- **Risk: proposed U 只是通用 filter 换名**  
  **Mitigation**: capacity-matched Vanilla 与 PredRNN-online 是 must-run；失败即缩 claim/停止。
- **Risk: 极低 q 时 residual/update 仍过弱**  
  **Mitigation**: q-stratified curves、identity tests、continuous-vs-binary pilot；不预先加 normalization 模块，若 continuous q 无益则删。
- **Risk: correction protocol cherry-pick**  
  **Mitigation**: 所有 cubes 固定 day25/day50、真实 mask、全体统计与层样本数。
- **Risk: H 随机冻结导致训练失败**  
  **Mitigation**: H 从共同 initialization 联合训练；E 的 freeze/unfreeze 对 matched systems一致。
- **Risk: 未来 E-OBS 被误称业务预测**  
  **Mitigation**: 明确称 forcing-conditioned hindcast/scenario forecast；不声称 operational weather forecasting。
- **Risk: AAAI 截止日期驱动不可信结论**  
  **Mitigation**: 2026-07-28 不作为无 Stage2 结果的 from-scratch目标；先完成证据 gate。

## Final Checklist

- [ ] Main Table 1 + horizon curve covers open-loop Earth-observation world rollout
- [ ] Main Table 2 / Fig. 2 isolates online correction against VanillaFilter and PredRNN-online with paired gain-AUC
- [ ] availability/supervision masks separated; `q=0` identity, staleness, reveal ordering, unrevealed-mask invariance tests specified
- [ ] Innovation, q, age deletion decisions occur on `val_dev` before IID/OOD
- [ ] Stage1.5 remains optional; forcing alignment is required support but not a parallel contribution
- [ ] Strong baselines use matched weather, targets, supervision and tuning budget
- [ ] Official split/evaluator/export/mask parity is proven before training
- [ ] Primary estimands, Holm correction, three seeds and paired geographic-tile bootstrap are locked
- [ ] Failure/stop rules are enforced
- [ ] Unrelated downstream, FM, LLM, diffusion and incomparable UniTS numbers remain cut
