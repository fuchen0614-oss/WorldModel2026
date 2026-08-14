# Table construction and reverse-trace notes

## Status

- `tables/table1_q1.tex`: complete draft; public means verified from the
  original CVPR 2024 Table 2; TerraState values verified from frozen Q1 JSON.
- `tables/table2_q2.tex`: complete draft; both splits and both interventions
  map to frozen Q2 JSON. Official deltas and paired effects are separated.
- `tables/table3_q3.tex`: complete draft; actual, matched donor, mean weather,
  cluster-bootstrap intervals, response-fidelity pass, and failed hot–dry
  guard are explicit.
- None of these files has been inserted into `main.tex`.

## Reverse trace by table

### Table 1

| Cell family | Source |
|---|---|
| TerraState \(R^2\), RMSE | `oodt_q1q2_state_contract_exclusive.json`, `$.Q1_forecast.full.{R2,rmse}` |
| Climatology, ConvLSTM, PredRNN, Contextformer | Benson et al., CVPR 2024, main paper Table 2 |
| Seed/uncertainty note | Benson et al., Table 2 caption and Section 4.1 text |

Table 1 deliberately has no bold best value across panels. Published methods
and TerraState are contextual rather than strictly ranked.

### Table 2

| Cell family | Source |
|---|---|
| Full, alpha0, identity \(R^2\) | `$.Q2_load_bearing.{full,alpha0,T_identity}.R2` |
| Official closure delta | `$.Q2_load_bearing.official_R2_full_minus_alpha0` |
| Official identity delta | `$.Q2_load_bearing.official_R2_full_minus_Tid` |
| Paired closure effect/CI | `$.Q2_load_bearing.closure_cut_alpha0.bootstrap95` |
| Paired identity effect/CI | `$.Q2_load_bearing.transition_identity.bootstrap95` |
| Verdict | `$.Q2_load_bearing.verdict` |

Important wording constraint: the paired interval is not the interval of the
official dataset-level delta. The table labels both estimands.

Important causal constraint: identity-transition evidence is confounded by an
out-of-distribution readout input (`transition_margin_clean=false`). Use
“supporting evidence for transition involvement,” not “clean proof that the
transition is necessary.”

### Table 3

| Cell family | Source |
|---|---|
| Actual/donor/mean \(R^2\), RMSE | `$.models.exclusive.q3_aggregate_extreme` |
| Donor loss increase and CI | `$.models.exclusive.q3_donor_fidelity.endpoint_fidelity.extreme_actual_vs_donor` |
| Mean-weather loss increase and CI | `$.models.exclusive.q3_donor_fidelity.endpoint_fidelity.extreme_actual_vs_mean` |
| Primary criterion and pass | `$.models.exclusive.q3_donor_fidelity.{primary_criterion,endpoint_fidelity_status}` |
| Failed hot–dry enhancement | `$.models.exclusive.q3_donor_fidelity.interaction_hotdry_minus_normal.dloss_donor.geo_cluster_bootstrap` and `.hotdry_enhancement_status` |

The aggregate \(R^2\)/RMSE values are for the selected 84-pair subset. They
must not be confused with the full 1,904-target Q1 result.

## Copy-safe notes for the manuscript session

1. Q1: “TerraState retains useful OOD-t predictive skill
   (\(R^2=0.569\), RMSE \(=0.151\)) on the frozen local manifest.”
2. Q2: “Removing the state-mediated residual reduces performance on both
   validation and temporal-shift splits; the prespecified load-bearing gate
   passes.” Keep identity-transition evidence qualified as confounded.
3. Q3: “Actual future weather yields better endpoint fidelity than matched
   donor or mean weather on the frozen 84-pair stress test.” Do not call this
   causal validity.
4. “The hot–dry enhancement interaction is inconclusive (95% CI crosses
   zero).”
5. “Published GreenEarthNet means are contextual references under the nominal
   same benchmark family, not a strict cross-implementation leaderboard.”
6. Do not use “SOTA”; do not create a core Q4/composition table.
