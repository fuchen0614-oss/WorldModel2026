# TerraState Q1–Q3 Claim–Evidence Audit

> Date: 2026-07-27  
> Authority for paper wording: `paper/main.tex`  
> Frozen numerical source: `../WorldModel2026-planb/TERRASTATE_V2_EVIDENCE.md`

## Verdict summary

| Question | Verdict | Evidence-supported interpretation |
|---|---|---|
| Q1 forecast skill | PASS for useful OOD-t skill; not an accuracy win | \(R^2=0.56935\), RMSE \(=0.15059\); matched backbone is more accurate |
| Q2 load-bearing state | PASS | State-contribution ablation reduces \(R^2\) on Val and OOD-t; both primary CIs exclude zero |
| Q3 weather response | PARTIAL overall | Endpoint fidelity passes for matched and mean controls; hot-dry-specific enhancement fails |
| Q4 composition/non-collapse | Not evaluated as a core claim | Exploratory only; no positive main-paper claim |

## Abstract

| Claim | Evidence | Status / allowed strength |
|---|---|---|
| TerraState infers, transitions, and decodes an explicit predictive state | Verified method structure and code-aligned manuscript | Supported as a method description |
| Future-observation target is training-only | Training contract and method implementation record | Supported |
| TerraState preserves useful temporal-shift skill | OOD-t \(R^2=0.56935\), RMSE \(=0.15059\) | Supported; do not say SOTA or accuracy improvement |
| State contribution is load-bearing | Val \(\Delta R^2=0.01121\), CI \([0.00643,0.02590]\); OOD-t \(0.01997\), CI \([0.01422,0.03018]\) | Supported |
| Forecast behavior depends on supplied weather | Actual vs matched \(\Delta\)Loss \(0.00257\), CI \([0.00112,0.00399]\); actual vs mean \(0.01126\), CI \([0.00547,0.01708]\) | Supported as response fidelity, not causality |

The abstract does **not** claim composition consistency, non-degeneracy, SOTA, or hot-dry-specific enhancement.

## Introduction

| Paragraph role | Main claim | Evidence mapping | Audit result |
|---|---|---|---|
| Task context | EO prediction uses cloud-obscured history, meteorology, and geography | EarthNet2021 / GreenEarthNet citations | Supported |
| Gap | Pixel accuracy alone does not verify a forecast-bearing, driver-responsive state | Conceptual motivation plus LatentTSF citation | Properly framed as a gap, not an empirical result |
| Definition | Predictive state must contribute to forecast and use declared forcing | Q2 and Q3 operational definitions | Supported |
| Method | TerraState implements history state, shared weather transition, and explicit closure | Method equations and implementation audit | Supported |
| Evidence preview | Q1 useful; Q2 CIs exclude zero; Q3 controls worsen loss; hot-dry null | Tables 1–3 and frozen record | Supported and appropriately qualified |
| Contributions | Model, future-state anchor, matched evidence | Method plus Q2/Q3 | Supported |

Removed or rejected from the Introduction:

- SOTA or superiority language;
- a positive composition/non-degeneracy claim;
- hot-dry-specific enhancement;
- any suggestion that Q3 can substitute for Q2.

## Method

| Method statement | Evidence basis | Boundary |
|---|---|---|
| \(b_h\) and \(z_t\) come from the same historical-context pass | Serialized architecture/code audit recorded in `AUTHOR_NOTES.md` | Future weather must not enter \(b_h\) |
| Shared \(T_\psi\) receives ordered 24-channel weather, geography, and horizon | Code/config audit | “24-channel future meteorological sequence” is a data description, not a method name |
| \(\widehat y=b_h+O_\omega(z_{t+h})\) | Serialized architecture/code audit | Does not imply all forecast skill passes through state |
| Only \(\mathcal L_{\rm GT}+0.5\mathcal L_{\rm KD}+\lambda_s\mathcal L_{\rm future-state}\) is optimized | Frozen training contract | No composition/VICReg/driver-distillation objective |
| Future target exists only at \(h=20\) | Frozen training contract | Does not imply transition only supports \(h=20\) |
| State ablation is primary; \(T\to I\) is supporting | Intervention semantics | \(T\to I\) may be distribution-confounded |
| Actual weather must improve endpoint prediction | Q3 criterion | Latent movement alone is insufficient |

## Results

### Q1

- **Raw result:** TerraState \(R^2=0.56935\), RMSE \(=0.15059\); matched backbone \(R^2=0.58252\), RMSE \(=0.14342\).
- **Strongest supported statement:** TerraState preserves useful temporal-shift forecasting skill.
- **Unsupported:** TerraState improves accuracy, is non-inferior, or is state of the art.

### Q2

- **Val:** state ablation \(\Delta R^2=0.01121\), CI \([0.00643,0.02590]\); \(T\to I\) \(\Delta R^2=0.01191\), CI \([0.00782,0.02696]\).
- **OOD-t:** state ablation \(\Delta R^2=0.01997\), CI \([0.01422,0.03018]\); \(T\to I\) \(\Delta R^2=0.02169\), CI \([0.01609,0.03217]\).
- **Strongest supported statement:** the state-mediated path is load-bearing on both splits.
- **Unsupported:** OOD-t makes the effect significantly stronger; future-state loss proves state use; \(T\to I\) alone establishes load-bearing state use.

### Q3

- **Actual vs season/geography-matched control:** \(\Delta\)Loss \(=0.00257\), geo-cluster CI \([0.00112,0.00399]\).
- **Actual vs normalized mean:** \(\Delta\)Loss \(=0.01126\), geo-cluster CI \([0.00547,0.01708]\).
- **Q3 subset scores:** \(R^2\) actual \(0.6254\), matched \(0.5893\), mean \(0.5430\); RMSE actual \(0.1492\), matched \(0.1584\), mean \(0.1971\).
- **Strongest supported statement:** actual weather predicts observed endpoints more faithfully than the two frozen controls.
- **Unsupported:** causal or counterfactual correctness; full OOD-t \(R^2=0.6254\); hot-dry-specific enhancement.
- **Negative result:** hot-dry interaction \(0.00044\), CI \([-0.00216,0.00320]\), so the enhancement claim is rejected.

## Limitations and Conclusion

| Claim | Evidence | Final treatment |
|---|---|---|
| One training run | Frozen record | Explicit limitation |
| One temporal-shift track | Local result scope | Explicit limitation |
| Matched backbone remains more accurate | Q1 local panel | Explicit limitation |
| No extreme-specific enhancement | Hot-dry null | Explicit limitation |
| No causal interpretation | Q3 design | Explicit limitation |
| No core composition claim | No final Q4 evidence | Explicit limitation |
| Load-bearing and weather-responsive predictive state | Q2 PASS + Q3 endpoint-fidelity PASS | Final positive conclusion |

## Identity caveat

The frozen Markdown record provides the checkpoint path, SHA, selection record, manifests, protocol hashes, and numerical summaries. The checkpoint and raw result JSON files referenced there are not currently visible in this workspace snapshot, so this writing pass did not recompute hashes or statistics. Before submission, a Release-level raw-artifact audit remains advisable. No claim in the current manuscript depends on an unavailable per-cube dump.
