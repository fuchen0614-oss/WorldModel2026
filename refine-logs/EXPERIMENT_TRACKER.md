# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics / Gate | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R001 | M0 | split audit | explicit official manifests | all | unique path/year/tile counts; missing split hard fail | MUST | TODO | 禁止 fallback root scan |
| R002 | M0 | evaluator parity | official climatology/persistence artifacts | ood-t | reproduced official metrics | MUST | TODO | GreenEarthNet evaluator, not ENS |
| R003 | M0 | export parity | template `ndvi_pred` NetCDF | Val | dims/time/lat/lon/file naming | MUST | TODO | 替换旧 NPZ export |
| R004 | M0 | input parity | obs/supervision masks + 24ch weather audit | Train/Val | official SCL/dlmask/landcover; separate variable paths; coverage/stats | MUST | TODO | 包含 context weather |
| R005 | M0 | state unit tests | q/staleness/U identity | synthetic | q=0 exact identity; q=1 reset; partial-q recursion | MUST | TODO | nearest resize then average-pool |
| R006 | M0 | reveal leakage test | all online systems | synthetic | predict-before-update; only `m_obs` consumed; swapping unrevealed target masks changes nothing | MUST | TODO | bitwise/equivalent invariance |
| R010 | M1 | tiny overfit | ObsWorld | 8 Train cubes | loss decreases; output finite/aligned | MUST | TODO | jointly train H |
| R011 | M1 | baseline parity | Contextformer official | Val/ood-t | paper/repo score parity | MUST | TODO | use official weights if available |
| R012 | M1 | recurrent baseline | PredRNN | Val | official metrics, throughput | MUST | TODO | full weather/20 targets |
| R013 | M1 | matched direct | Direct-Seq | Val | official metrics, Params/FLOPs | MUST | TODO | shared weather MLP + 1-layer GRU |
| R014 | M1 | open-loop pilot | ObsWorld no reveal | Val | strong-baseline range; horizon curve | MUST | TODO | stop if factual collapse |
| R020 | M2 | generic filter | VanillaFilter seed 42 | Val | paired gain-AUC day25/50 | MUST | TODO | same z_obs/z_pred; params/FLOPs within 5% |
| R021 | M2 | proposed update | aligned residual U seed 42 | Val | paired gain-AUC + absolute MAE/strata | MUST | TODO | same single-reveal schedule |
| R022 | M2 | pixel online control | PredRNN-online seed 42 | Val | post-reveal aggregate/strata | MUST | TODO | masked RGBN+mask at reveal |
| R023 | M2 | no-reveal counterfactual | same trained online models | Val | correction gain vs own no-reveal | MUST | TODO | inference only |
| R030 | M3 | staleness deletion | residual U w/o staleness | Val | paired gain-AUC delta | MUST | TODO | delete if equivalent |
| R031 | M3 | q deletion | binary q vs continuous q | Val | strata + aggregate | MUST | TODO | choose simpler if equivalent |
| R032 | M3 | hard replace diagnostic | hard replacement | Val | post-reveal aggregate | NICE | TODO | appendix only |
| R033 | M3 | initialization gate | Stage1 vs repaired Stage1.5 | Val | predictive/semantic + Stage2 skill | NICE | TODO | no second claim |
| R034 | M3 | weather sanity | true/no/wrong-year | Val | official correctness | NICE | TODO | no causal language |
| R040 | M4 | final open-loop seeds | final ObsWorld seeds 42/27/97 | ood-t | official metrics + cluster CI | MUST | TODO | config locked |
| R041 | M4 | final vanilla seeds | VanillaFilter seeds 42/27/97 | ood-t | day25/50 post-reveal | MUST | TODO | config locked |
| R042 | M4 | final online recurrent seeds | PredRNN-online seeds 42/27/97 | ood-t | day25/50 post-reveal | MUST | TODO | config locked |
| R043 | M4 | final direct seeds | Direct-Seq seeds 42/27/97 | ood-t | official metrics | MUST | TODO | if pilot competitive |
| R044 | M4 | final correction inference | all trained online systems | ood-t | all-cube/strata/counts/curves | MUST | TODO | fixed day25/day50 |
| R050 | M5 | spatial OOD | final systems | ood-s/ood-st | compact official metrics | NICE | TODO | no retuning |
| R051 | M5 | land-cover/season failure | final model | ood-t | subgroup metrics and examples | NICE | TODO | report counts |
| R052 | M5 | efficiency | final + matched controls | Val | Params/FLOPs/latency/memory | NICE | TODO | same hardware |

Statuses: `TODO`, `RUNNING`, `DONE`, `FAILED`, `SKIPPED_BY_GATE`.
