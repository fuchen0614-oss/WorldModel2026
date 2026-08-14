# TerraState AAAI-27 Results Integration Audit

Date: 2026-07-27

## Scope and evidence boundary

This audit covers the result-integrated manuscript, its bilingual reading mirrors, Tables 1--3,
and Figure 3. No training or evaluation code was modified or executed. The numerical source is
the frozen project record `WorldModel2026-planb/TERRASTATE_V2_EVIDENCE.md`.

The record identifies the selected model by checkpoint path, file SHA256, weight fingerprint,
code commits, validation-only selection procedure, evaluation manifests, and Q3 protocol hashes.
The raw checkpoint and underlying Q1--Q3 JSON/CSV releases are not present in the currently
visible workspace. Consequently, this revision verifies consistency against the frozen record but
does not independently recompute hashes, confidence intervals, or metrics. The release package
must be re-audited before submission.

## Claim--evidence decisions

| Question | Evidence integrated | Verdict | Strongest supported claim | Excluded claim |
|---|---|---|---|---|
| Q1 | OOD-t \(R^2=0.56935\), RMSE \(=0.15059\); matched backbone \(R^2=0.58252\), RMSE \(=0.14342\) | Useful, not superior | TerraState preserves useful out-of-distribution forecasting skill | SOTA, best-performing, or superiority over the matched backbone |
| Q2 | State-path intervention: Val \(+0.01121\), 95% CI \([0.00643,0.02590]\); OOD-t \(+0.01997\), 95% CI \([0.01422,0.03018]\). Transition-to-identity effects are positive auxiliary evidence. | PASS | The predictive-state path is load-bearing for the final forecast | All predictive information flows only through the state, or the loss alone proves load-bearingness |
| Q3 | Actual weather improves loss over matched donor by \(0.00257\), 95% CI \([0.00112,0.00399]\), and over normalized mean weather by \(0.01126\), 95% CI \([0.00547,0.01708]\) | PASS for weather response | Forecast behavior depends on the supplied future weather, and actual weather outperforms the two controls under the frozen protocol | Causality, physical simulation, or universal correctness of the response |
| Q3 hot--dry | Interaction \(0.00044\), 95% CI \([-0.00216,0.00320]\) | FAIL | No supported extreme-specific enhancement | Successful hot--dry enhancement |
| Q4 | No final result integrated | Not claimed | Optional post-training extension only | Composition-consistent or non-degenerate state as an established result |

The detailed section-level mapping is maintained in `RESULTS_CLAIM_EVIDENCE_AUDIT.md`.

## Figure and table responsibilities

- Figure 1: model mechanism and the \(q\rightarrow T\rightarrow O\) forecast closure.
- Figure 2: same-model interventions used for Q1--Q3; Q4 is visually subordinate and optional.
- Table 1: exact Q1 forecast metrics, with reported literature results separated from local results.
- Table 2: exact Q2 absolute scores, paired effects, and confidence intervals.
- Table 3: exact Q3 actual/control scores, effects, and confidence intervals.
- Figure 3: behavioral interpretation rather than a second copy of all table cells:
  - panel (a): Q2 state-path and transition effects with confidence intervals on Val and OOD-t;
  - panel (b): Q3 actual-versus-control loss effects with confidence intervals;
  - panel (c): Q3 endpoint \(R^2\) and RMSE for actual, matched-donor, and mean-weather conditions.

Figure 3 is generated from `paper/figures/data/terrastate_behavioral_evidence.csv`. No
qualitative tile or per-cube distribution is shown because no frozen per-sample array is available.

## Final layout and build

- PDF: 9 US-Letter pages.
- Figure 1: page 2.
- Figure 2: page 5.
- Tables 1--3: page 6.
- Figure 3: page 7. The column-width version is used because the full-width candidate produced
  substantially poorer final-page column balance under the nine-page layout.
- Main text ends on page 7; pages 8--9 contain references only.
- The current build has no LaTeX errors, unresolved citations/references, overfull boxes, or
  Type-3/unembedded fonts.
- The manuscript is anonymous.

## Remaining release-side inputs

1. The checkpoint file and an independently recomputed SHA256.
2. Serialized architecture/config and environment identity.
3. The validation-only selection ledger.
4. Frozen manifests, masks, horizon, scorer, aggregation, donor mapping, normalizer, and threshold.
5. Raw Q1--Q3 JSON/CSV outputs, including paired unit identifiers and bootstrap metadata.
6. Optional frozen per-cube arrays and sample-selection records if a distributional or qualitative
   evidence panel is later desired.
7. Optional Q4 result package; a weak or absent Q4 result must remain outside the core claims.
