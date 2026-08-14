# Figure 3 v2 — Current Exact Audit

Audit time (UTC): `2026-07-28T14:22:30Z`  
Verdict: `CURRENT_EXACT_FIG3_V2: PASS`

This audit uses the files currently present on disk. It does not rerun model
evaluation, replace any figure export, or modify the manuscript.

## Current SHA-256

| Role | File | SHA-256 |
|---|---|---|
| Frozen authority | `figure_workspace/FIGURE_1_3_FROZEN_PLAN_20260728.md` | `ef7f745bf10d557dc635e8051daa1effb77dbf806d6bccec621bc67800b827a1` |
| Panel (a), Validation | `evidence_workspace/raw/release/val_q2_state_contract_exclusive.json` | `33b40d3e6bf6e0190c9415a9e0421e9809063356dcba2350890defeeed35f2d9` |
| Panel (a), OOD-t | `evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json` | `7ebc0569d705a9991ac8b8d17c42113c9da052b2bec73f7c28d021e28a65a051` |
| Panels (b,c) | `evidence_workspace/raw/release/q3_extreme_state_audit.json` | `9dae43b9a8a4fcdf0a73ef91daa58c189a88e769541ce295046cd0e938497041` |
| Frozen ledger | `evidence_workspace/results_ledger.json` | `d1f8ec7d7a51fae87afc8ba9dbc27905c6816434dc5554980d2e7c2eb472c4b2` |
| Drawing script | `figure_workspace/source/fig3_behavior_v2.py` | `e87324c5c59a30394868e4233278307a728b190cc9cd371de83afc8de9078c61` |
| Editable vector | `figure_workspace/source/fig3_behavior_v2.svg` | `57707cec564fc046fed04b21c6b7ae3008c049acd104071f869c3b780b6a6ba2` |
| Paper vector | `figure_workspace/export/fig3_behavior_v2.pdf` | `bbf0444dd18c5c910e2bd3d3dcadeccb57e28d3b2bfeee930e004545b351c990` |
| 300-dpi preview | `figure_workspace/export/fig3_behavior_v2.png` | `07521d9d718e1e9a2f45b5e9cd96d08855dde27c2677b25c355784f6da3b9152` |
| Grayscale QA | `figure_workspace/qa/fig3_behavior_v2_grayscale.png` | `5f397a46eb07b6054a57d38e6410ef75f6e75bb17140d34e2128e782d80416fc` |
| Paper-scale QA | `figure_workspace/qa/fig3_behavior_v2_paperscale.png` | `7fb2791dad0613841e9fe9b54a7150385216e073fe7d083c21ecc2cd147466be` |

The three raw JSON hashes match their entries in the current frozen results
ledger.

## Panel data audit

### (a) Q2 State contribution

- Validation source:
  `Q2_load_bearing.closure_cut_alpha0.bootstrap95` and
  `Q2_load_bearing.transition_identity.bootstrap95`.
- OOD-t source: the same fields in the OOD-t frozen JSON.
- State removal, Validation: paired mean `0.01616252595360122`,
  95% CI `[0.006432408120151691, 0.02590229577842624]`, `n=589`.
- State removal, OOD-t: paired mean `0.021997768589881533`,
  95% CI `[0.014219898623411737, 0.03017606928017251]`, `n=1019`.
- Supporting `T→I`, Validation: paired mean `0.017417428921451206`,
  95% CI `[0.007824839508750908, 0.026960749441100905]`, `n=589`.
- Supporting `T→I`, OOD-t: paired mean `0.024015932710944276`,
  95% CI `[0.016086752271438905, 0.032169788967835664]`, `n=1019`.
- Direction is
  `ΔR² = R²_full − R²_intervention`; farther right means more forecast skill
  is lost after intervention.
- The current SVG marker and CI coordinates reproduce these frozen values to
  within `5.9e-7 pt`.

### (b) Actual vs. matched-donor weather

- Source rows: `models.exclusive.q3_donor_rows`.
- Coordinates: `x=loss_e_actual`, `y=loss_e_donor`.
- These coordinates are per-minicube masked MSE values over the complete
  20-step target/forecast window, not \(h=20\)-only endpoint errors.
- Completeness: top-level `n_pairs=84`, protocol `n_pairs=84`, fidelity
  `n_pairs=84`, row count `84`, unique extreme keys `84`, unique pair tuples
  `84`.
- The 45 unique control keys reflect declared donor reuse and do not remove or
  duplicate an extreme-weather pair.
- Missing/non-finite coordinate values: `0`; all `uf_differs=true`.
- Mean `loss_e_donor − loss_e_actual`:
  `0.002565468112672014`.
- Above/equal/below `y=x`: `56/0/28`.
- Current SVG point count: `84`; maximum coordinate error against the current
  frozen rows: `5.8e-7 pt`.

### (c) Actual vs. normalized-mean weather

- Source rows: the same complete `q3_donor_rows`.
- Coordinates: `x=loss_e_actual`, `y=loss_e_mean`.
- The same full-window masked-MSE definition applies. The frozen JSON key
  `endpoint_fidelity` is retained as a legacy internal field name only.
- Mean `loss_e_mean − loss_e_actual`:
  `0.011261332329706334`.
- Above/equal/below `y=x`: `69/0/15`.
- Current SVG point count: `84`; maximum coordinate error against the current
  frozen rows: `8.0e-7 pt`.
- Panels (b,c) both use `[0,0.12]` on both axes. All values are within this
  range; observed maxima are actual `0.08406330645084381`, donor
  `0.05999298021197319`, and normalized mean `0.10805400460958481`.

## Scope and claim-boundary audit

- State removal is visually primary; `T→I` is explicitly supporting evidence.
- Above `y=x` means the control-weather full-window MSE is higher than the
  actual-weather full-window MSE.
- The `56/84` and `69/84` annotations are descriptive counts calculated from
  all frozen rows, not additional significance tests.
- No Q4/composition, causal or counterfactual claim, extreme-specific
  enhancement, SOTA claim, manual point selection, or model reevaluation is
  included.
- The figure supports load-bearing state contribution and conditional
  full-window weather-response fidelity on the declared frozen subsets only.
