# ObsWorld Experiment Tracker

状态：尚未开始实现；本文件用于冻结协议与后续回填，不代表已有结果。

| ID | 阶段 | 实验 | 数据/协议 | Seeds | 关键指标 | Gate | 状态 | 备注 |
|---|---|---|---|---:|---|---|---|---|
| M0-01 | Protocol | official manifest audit | GreenEarthNet | - | file/hash/count | exact | TODO | 禁止 fallback scan |
| M0-02 | Protocol | evaluator parity | OOD-t dev copy | - | six official metrics | parity | TODO | 先复现公开 baseline |
| M0-03 | Data | official 24-D/5-day E-OBS + mask audit | Train/Val | - | 8 vars×mean/min/max; missingness/shape | exact | TODO | Train-only stats; raw daily 仅 appendix |
| M0-04 | Fairness | Direct/rollout/main matching | Train/Val | - | same `E_D`; total params | <=10% params | TODO | 5/10/20d 共享变长 encoder |
| M0-phi | Data | L1C/L2A pair audit | SSL4EO shards | - | key/time/file_id/clear support | exact | TODO | 先 20 shards |
| M1-01 | Stage1.5 | 60k checkpoint re-eval | geographic holdout | 3 | pair/probe/future utility | stable | TODO | 不用旧 probe 数字 |
| M1-02 | Stage1.5 | cross-observation repair | S1/S2 <=7d | 3 | cross decode + Stage2 skill | pass both | TODO | 不称纯 renderer pair |
| M1-03 | Stage1.5 | product-conditioned Gate | exact L1C/L2A | 3 | 4-row ablation; correct vs wrong token | clustered paired CI | TODO | shared decoder; 失败则 fixed S2 |
| M2-01 | Stage2-A | small overfit/direct | GreenEarthNet Train | 1 | RGBN/NDVI | overfit | TODO | protocol smoke test |
| M2-02 | Stage2-A | matched Direct | Val | 1→3 | official metrics | strong range | TODO | official 24-D D; same `E_D` |
| M3-01 | Stage2-B1 | shared T5 rollout | Val | 1 | horizon error | non-collapse | TODO | architecture control |
| M3-P0 | Protocol | freeze partition sampling | Train/Val | - | 5/10/20 and partition ratios; masks; weights | frozen before 2×2/OOD | TODO | default 0.50/0.25/0.25; exact D/C splice |
| M3-02a | 2×2 | base state + variable-step no part | Val | 1→3 | forecast/OOD/gap | factorial baseline | TODO | product−, temporal− |
| M3-02b | 2×2 | cross-observation state + no part | Val | 1→3 | forecast/OOD/gap | product main effect | TODO | product+, temporal− |
| M3-03a | 2×2 | base state + control-aware part | Val | 1→3 | forecast/OOD/gap | temporal main effect | TODO | product−, temporal+ |
| M3-03b | 2×2 | full ObsWorld | Val | 1→3 | forecast/OOD/gap | interaction + formal inequalities | TODO | product+, temporal+; fixed LN |
| M3-03i | 2×2 audit | intervention isolation + interaction | all four cells | - | `Delta_int`; data/update/FLOP parity | CI + parity pass | TODO | only `lambda_crossobs/lambda_part` switch |
| M3-03c | Diagnostic | partition gap predicts long-OOD error | checkpoints/models/regions | - | prereg correlation/CI | stable sign | TODO | no post-hoc subgroup selection |
| M3-04 | Ablation | no/plausible-shuffle D | Val | 3 | paired difference | true wins | TODO | season/climate matched |
| M3-05 | Ablation | no/permuted G | Val | 3 | paired difference | true wins | TODO | full-map permutation |
| M4-01 | Main | locked OOD-t | official | 3 | official six + clustered paired 95% CI | frozen inequalities | TODO | three seeds AND CI; one formal evaluation |
| M4-02 | Secondary | OOD-s/OOD-st | official | 3 | official six | report | TODO | appendix |
| M4-03 | Secondary | original Extreme/Seasonal | EarthNet2021 | 3 | diagnostic | optional | TODO | 不混称 official Green split |

## Frozen decisions to fill before training

- Git commit：`TBD`
- official dataset release/hash：`TBD`
- split manifest hash：`TBD`
- evaluator commit：`TBD`
- train-only normalization file/hash：`TBD`
- plausible D shuffle rule：`TBD`
- G permutation rule：`TBD`
- non-inferiority `delta_NI`, `delta_part` and independent rationale：`TBD` (必须早于 ObsWorld locked-OOD 结果)
- parameter/FLOP matching report：`TBD` (总参数差 <=10%)
- driver encoder signature/hash：`TBD` (三类模型相同)
- partition sampling/anchor/mask/loss-weight spec hash：`TBD` (在主 2×2 和 locked OOD 前冻结)
- 2×2 product-pair counts/update counts/forward-pass parity：`TBD`
- interaction contrast：`Delta_int=L_11-L_10-L_01+L_00`; `synergistic` 需 `upper95CI<0`
- clustered bootstrap unit/code/hash：`TBD` (tile/location)
- locked OOD-t evaluation date：`TBD`
