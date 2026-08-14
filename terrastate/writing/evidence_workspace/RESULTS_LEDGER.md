# TerraState Q1–Q3 results ledger

Audit freeze: 2026-07-27 UTC. This document is the human-readable index to
`results_ledger.json`, which contains the exact machine-readable field paths,
hashes, sample counts, evaluator versions, and limitations.

## Frozen model identity

- Public display name: **TerraState**.
- Internal traceability name: `boundary80`; preregistered candidate tag
  `stage2_end_boundary80`, step 11,904, stage 2.
- Checkpoint file SHA-256:
  `644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd`.
- Weight SHA-256:
  `aba100c138119bc0fc4412082412596dcf31090410643aa0736b5705b04feaa7`.
- Training-code commit:
  `52578ca4b1c0b434b10707cf052a623f0c4e4a99`.
- Frozen public release:
  `terrastate-v2-boundary80-evidence-v1`, commit
  `c63a333a4fc0ad31d68159b090d06c80bf13f21f`.
- Selection was made before viewing Q2. No preregistered candidate passed the
  internal Q1 qualifier; the best Q1 candidate in the preregistered set was
  selected. This is one run (seed 42, `deterministic=false`).

The engineering names above exist only for traceability. The paper tables use
“TerraState”.

## Q1: frozen temporal-shift prediction

| Split | Metric | Exact value | Raw JSON field |
|---|---:|---:|---|
| `ood-t_chopped` | \(R^2\) | 0.5693493611664086 | `$.Q1_forecast.full.R2` |
| `ood-t_chopped` | RMSE | 0.1505941190915099 | `$.Q1_forecast.full.rmse` |

- Raw JSON:
  `/mnt/data/users/luzheng/workspace/iclr/czj/TerraState_AAAI27/evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json`
  (SHA-256 `7ebc0569...a65a051`).
- Manifest:
  `/mnt/data/users/luzheng/workspace/iclr/czj/WorldModel2026-planb/evaluations/greenearthnet_oodt_20260719_214234/greenearthnet_oodt_chopped_manifest.json`
  (locally rehashed SHA-256 `58c8d648...8e1e49`).
- Protocol/evaluator: `exclusive_v1`,
  `repo:78073db+official:a0329636631371a4aaa9a95c75ed0a37d27b8c4f`.
- Sample size: 1,904 targets.
- Permitted claim: useful future-prediction skill persists under the frozen
  temporal shift.
- Not permitted: SOTA, strict superiority to published baselines, or
  multi-seed robustness.

## Q2: state-path load bearing

### Exact metrics

| Split | Full \(R^2\) | Full RMSE | \(\alpha=0\) \(R^2\) | \(T=\mathrm{Id}\) \(R^2\) | Official \(\Delta R^2\), state path | Official \(\Delta R^2\), identity \(T\) |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 0.49732196418835595 | 0.1572881669325748 | 0.48610753997662814 | 0.48541607437960566 | 0.011214424211727803 | 0.011905889808750292 |
| Temporal shift | 0.5693493611664086 | 0.1505941190915099 | 0.5493773508945857 | 0.5476642387248465 | 0.019972010271822827 | 0.021685122441562066 |

| Split/intervention | Paired mean \(\Delta R^2\) | Paired bootstrap 95% CI | Paired \(n\) | Verdict |
|---|---:|---:|---:|---|
| Validation, state-path removal | 0.01616252595360122 | [0.006432408120151691, 0.02590229577842624] | 589 | `LOAD_BEARING` |
| Validation, identity transition | 0.017417428921451206 | [0.007824839508750908, 0.026960749441100905] | 589 | supporting |
| Temporal shift, state-path removal | 0.021997768589881533 | [0.014219898623411737, 0.03017606928017251] | 1,019 | `LOAD_BEARING` |
| Temporal shift, identity transition | 0.024015932710944276 | [0.016086752271438905, 0.032169788967835664] | 1,019 | supporting |

Raw field families:

- `$.Q2_load_bearing.full`, `.alpha0`, `.T_identity`;
- `$.Q2_load_bearing.official_R2_full_minus_alpha0`;
- `$.Q2_load_bearing.official_R2_full_minus_Tid`;
- `$.Q2_load_bearing.closure_cut_alpha0.bootstrap95`;
- `$.Q2_load_bearing.transition_identity.bootstrap95`;
- `$.Q2_load_bearing.verdict`.

Validation uses 952 targets and 589 paired metric units; temporal shift uses
1,904 targets and 1,019 paired units. The official dataset-level delta and the
paired-bootstrap mean/interval are different estimands. They must be labeled
separately, not written as if the interval were centered on the official delta.

State-path removal is the clean primary intervention. The evaluator explicitly
sets `transition_margin_clean=false`: \(T=\mathrm{Id}\) sends an unevolved state
to a readout trained on evolved states. It supports transition involvement but
does not by itself prove clean transition necessity.

The validation manifest SHA is recorded consistently as
`d9bd91d6...52bf8e`, but the manifest file is absent locally and could not be
independently rehashed. The temporal-shift manifest was locally rehashed.

## Q3: weather intervention

The final protocol is `extreme_audit_oodt_v1`, broad primary track, with 84
extreme pairs, 45 unique controls, 31 geographic clusters, and 10,000 bootstrap
replicates.

| Future weather | \(R^2\) | RMSE | Loss increase vs actual | Primary geo-cluster 95% CI |
|---|---:|---:|---:|---:|
| Actual | 0.6253516462782711 | 0.14915162604727777 | 0 | — |
| Matched donor | 0.5893404938146756 | 0.15841893205313404 | 0.002565468112672014 | [0.0011187122087714869, 0.003987491067301663] |
| Mean weather | 0.5430064798749749 | 0.19709368956822035 | 0.011261332329706334 | [0.005465624536528642, 0.0170799320898515] |

Core raw paths:

- scores:
  `$.models.exclusive.q3_aggregate_extreme.{actual,donor,mean}.{R2,rmse}`;
- donor endpoint:
  `$.models.exclusive.q3_donor_fidelity.endpoint_fidelity.extreme_actual_vs_donor`;
- mean-weather endpoint:
  `$.models.exclusive.q3_donor_fidelity.endpoint_fidelity.extreme_actual_vs_mean`;
- primary criterion:
  `$.models.exclusive.q3_donor_fidelity.primary_criterion`;
- endpoint verdict:
  `$.models.exclusive.q3_donor_fidelity.endpoint_fidelity_status`.

Endpoint response fidelity passes: actual future weather is better than both
matched donor and mean weather, with the primary cluster-bootstrap lower bounds
above zero.

The hot–dry enhancement guard **fails**:

- interaction mean \(=0.0004360788783136134\);
- geo-cluster 95% CI
  \([-0.0021624635347345066,\ 0.003199765110504583]\);
- raw field:
  `$.models.exclusive.q3_donor_fidelity.interaction_hotdry_minus_normal.dloss_donor.geo_cluster_bootstrap`;
- verdict:
  `$.models.exclusive.q3_donor_fidelity.hotdry_enhancement_status = "FAIL"`.

Therefore Q3 supports weather-sensitive endpoint behavior only. It does not
support extreme-specific enhancement, causal counterfactual validity, or an
external EO-WM extreme-benchmark claim.

Q3 provenance limitation: the raw Q3 JSON does not embed the checkpoint SHA or
evaluator commit. Same-checkpoint linkage is supplied by the frozen release
bundle, `EVIDENCE.md`, and `q3.run.log`; protocol-builder and repository
commits are separately recorded. This is a provenance gap to preserve in any
camera-ready archive.

## Reverse-trace result

Every number in the three draft tables maps to a raw JSON field or to
GreenEarthNet Table 2. No local matched-backbone/B0/B4 number was admitted to
Table 1 because a release-level raw result record supporting that row was not
found. See `TABLE_NOTES.md` and `PUBLIC_BASELINES.md`.
