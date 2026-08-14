# Figure 3 v2 — Frozen Data Trace

Status: `FIG3_V2_READY_FOR_EVIDENCE_AUDIT`

Generated: 2026-07-28 UTC  
Frozen authority: `FIGURE_1_3_FROZEN_PLAN_20260728.md`

## 1. Generation rule

`source/fig3_behavior_v2.py` reads the frozen JSON records directly. It does not rerun a
checkpoint, reconstruct confidence intervals, hand-enter points, remove samples, or read values
from the old Figure 3 aggregate CSV.

Before drawing, the script verifies the three raw JSON SHA-256 values against
`evidence_workspace/results_ledger.json`. Generation fails on a hash mismatch, an unexpected
sample count, a missing/non-finite value, or a Q3 row mean inconsistent with the frozen summary.

## 2. Panel (a): Q2 State contribution

### Validation

- Data:
  `TerraState_AAAI27/evidence_workspace/raw/release/val_q2_state_contract_exclusive.json`
- State removal estimate:
  `$.Q2_load_bearing.closure_cut_alpha0.bootstrap95.mean`
- State removal 95% CI:
  `$.Q2_load_bearing.closure_cut_alpha0.bootstrap95.[ci_low,ci_high]`
- Paired units: `n = 589`
- Paired mean \(\Delta R^2\): `0.01616252595360122`
- 95% CI: `[0.006432408120151691, 0.02590229577842624]`
- Supporting \(T\to I\) estimate:
  `$.Q2_load_bearing.transition_identity.bootstrap95.mean`
- Supporting \(T\to I\) 95% CI:
  `$.Q2_load_bearing.transition_identity.bootstrap95.[ci_low,ci_high]`
- \(T\to I\) paired mean \(\Delta R^2\): `0.017417428921451206`
- \(T\to I\) 95% CI: `[0.007824839508750908, 0.026960749441100905]`

### OOD-t

- Data:
  `TerraState_AAAI27/evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json`
- State removal estimate:
  `$.Q2_load_bearing.closure_cut_alpha0.bootstrap95.mean`
- State removal 95% CI:
  `$.Q2_load_bearing.closure_cut_alpha0.bootstrap95.[ci_low,ci_high]`
- Paired units: `n = 1019`
- Paired mean \(\Delta R^2\): `0.021997768589881533`
- 95% CI: `[0.014219898623411737, 0.03017606928017251]`
- Supporting \(T\to I\) estimate:
  `$.Q2_load_bearing.transition_identity.bootstrap95.mean`
- Supporting \(T\to I\) 95% CI:
  `$.Q2_load_bearing.transition_identity.bootstrap95.[ci_low,ci_high]`
- \(T\to I\) paired mean \(\Delta R^2\): `0.024015932710944276`
- \(T\to I\) 95% CI: `[0.016086752271438905, 0.032169788967835664]`

Direction used in the plot:

> \(\Delta R^2 = R^2_{\mathrm{full}} - R^2_{\mathrm{intervention}}\).

Therefore, farther right means a larger forecast-skill loss after intervention. State removal is
the filled primary marker; \(T\to I\) is the smaller open supporting marker.

## 3. Panel (b): Actual vs. matched-donor weather

### Q3 loss semantics

The frozen Q3 fields `loss_e_actual`, `loss_e_donor`, and `loss_e_mean` are
**per-minicube masked MSE values over the complete 20-step target/forecast
window**. They compare each weather arm with the observed future NDVI across
the full target window; they are **not** an error evaluated only at the single
\(h=20\) endpoint.

The frozen JSON container name `endpoint_fidelity` is a legacy internal field
name. It is retained unchanged for provenance and backward compatibility; it
does not redefine the underlying full-window MSE as an \(h=20\)-only error.

- Data:
  `TerraState_AAAI27/evidence_workspace/raw/release/q3_extreme_state_audit.json`
- Rows:
  `$.models.exclusive.q3_donor_rows`
- x field: `loss_e_actual`
- y field: `loss_e_donor`
- Frozen pairs: `n_pairs = 84`
- Rows read: `84`
- Unique `e_key`: `84`
- Missing/non-finite x values: `0`
- Missing/non-finite y values: `0`
- Mean of `loss_e_donor - loss_e_actual`:
  `0.002565468112672014`
- Frozen summary value:
  `$.models.exclusive.q3_donor_fidelity.endpoint_fidelity.extreme_actual_vs_donor.delta_loss_mean`
  = `0.002565468112672014`
- Difference between row mean and frozen summary: `0`
- Above \(y=x\): `56/84`
- Equal to \(y=x\): `0/84`
- Below \(y=x\): `28/84`

## 4. Panel (c): Actual vs. normalized-mean weather

- Data:
  `TerraState_AAAI27/evidence_workspace/raw/release/q3_extreme_state_audit.json`
- Rows:
  `$.models.exclusive.q3_donor_rows`
- x field: `loss_e_actual`
- y field: `loss_e_mean`
- Frozen pairs: `n_pairs = 84`
- Rows read: `84`
- Unique `e_key`: `84`
- Missing/non-finite x values: `0`
- Missing/non-finite y values: `0`
- Mean of `loss_e_mean - loss_e_actual`:
  `0.011261332329706334`
- Frozen summary value:
  `$.models.exclusive.q3_donor_fidelity.endpoint_fidelity.extreme_actual_vs_mean.delta_loss_mean`
  = `0.011261332329706334`
- Difference between row mean and frozen summary: `0`
- Above \(y=x\): `69/84`
- Equal to \(y=x\): `0/84`
- Below \(y=x\): `15/84`

Panels (b) and (c) use the same `[0, 0.12]` range on both axes. No row is omitted.

## 5. Missing-value and scope audit

- Q2 required estimates, CI endpoints, and sample counts: no missing/non-finite values.
- Q3 `loss_e_actual`, `loss_e_donor`, and `loss_e_mean`: no missing/non-finite values.
- Q3 points filtered or selected after inspection: `0`.
- Model evaluation rerun: `NO`.
- Q4/composition included: `NO`.
- Extreme-specific interaction included: `NO`.
- Failed hot-dry enhancement claim included: `NO`.
- Q3 use is limited to full-window predictive fidelity on the frozen evaluated
  subset. The corresponding frozen summary remains stored under the legacy
  internal key `endpoint_fidelity`.

## 6. SHA-256 inventory

### Frozen authority and evidence

| File | SHA-256 |
|---|---|
| `figure_workspace/FIGURE_1_3_FROZEN_PLAN_20260728.md` | `ef7f745bf10d557dc635e8051daa1effb77dbf806d6bccec621bc67800b827a1` |
| `evidence_workspace/raw/release/val_q2_state_contract_exclusive.json` | `33b40d3e6bf6e0190c9415a9e0421e9809063356dcba2350890defeeed35f2d9` |
| `evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json` | `7ebc0569d705a9991ac8b8d17c42113c9da052b2bec73f7c28d021e28a65a051` |
| `evidence_workspace/raw/release/q3_extreme_state_audit.json` | `9dae43b9a8a4fcdf0a73ef91daa58c189a88e769541ce295046cd0e938497041` |
| `evidence_workspace/results_ledger.json` | `d1f8ec7d7a51fae87afc8ba9dbc27905c6816434dc5554980d2e7c2eb472c4b2` |

The three raw-record hashes match their entries in the frozen results ledger.

### Candidate outputs

| File | SHA-256 |
|---|---|
| `source/fig3_behavior_v2.py` | `e87324c5c59a30394868e4233278307a728b190cc9cd371de83afc8de9078c61` |
| `source/fig3_behavior_v2.svg` | `57707cec564fc046fed04b21c6b7ae3008c049acd104071f869c3b780b6a6ba2` |
| `export/fig3_behavior_v2.pdf` | `bbf0444dd18c5c910e2bd3d3dcadeccb57e28d3b2bfeee930e004545b351c990` |
| `export/fig3_behavior_v2.png` | `07521d9d718e1e9a2f45b5e9cd96d08855dde27c2677b25c355784f6da3b9152` |
| `qa/fig3_behavior_v2_grayscale.png` | `5f397a46eb07b6054a57d38e6410ef75f6e75bb17140d34e2128e782d80416fc` |
| `qa/fig3_behavior_v2_paperscale.png` | `7fb2791dad0613841e9fe9b54a7150385216e073fe7d083c21ecc2cd147466be` |

## 7. Format and paper-scale checks

- Figure size: `7.0 × 2.55 in`.
- SVG size: `504 × 183.6 pt`; text remains SVG text (`svg.fonttype = none`).
- PDF: vector Matplotlib objects with embedded DejaVu Sans fonts; no raster image object was
  detected in the PDF stream.
- PNG: `2100 × 765 px`, 300 dpi.
- Grayscale preview: `2100 × 765 px`, 300 dpi.
- Paper-scale preview: US Letter canvas at 150 dpi with the figure placed at exactly 7.0 inches.
- Minimum configured text size: `7.5 pt`.
- Color is not the only encoding: state removal is filled, \(T\to I\) is open/smaller, and the
  two weather comparisons occupy separate labeled panels.

## 8. Frozen-plan compliance

`PASS`

- Three required panels are present.
- Q2 uses paired \(\Delta R^2\) and frozen 95% intervals.
- Positive/rightward Q2 values mean larger intervention-induced skill loss.
- Q3 uses all 84 frozen paired rows and code-computed above-diagonal counts.
- Panels (b) and (c) share coordinate limits.
- No Q4, extreme-specific interaction, manual point, or rerun result is present.
- Candidate names do not overwrite the existing formal Figure 3 files.
