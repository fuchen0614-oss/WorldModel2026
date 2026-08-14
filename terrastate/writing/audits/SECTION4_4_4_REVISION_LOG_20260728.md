# Section 4.4 Revision Log

**Date:** 2026-07-28  
**Scope:** Section 4.4 only, plus its authorized Markdown mirrors and the Q3-related compact Conclusion sentence  
**Final state:** `READY_FOR_4_4_AUDIT`

## 1. Modified Files

- `paper/main.tex`
- `MANUSCRIPT_ZH_FULL.md`
- `MANUSCRIPT.md`
- `MANUSCRIPT_ZH.md`
- `SECTION4_4_4_REVISION_LOG_20260728.md`

No Figure file, evidence file, experiment artifact, checkpoint, or model/evaluation
code was modified.

## 2. Structure Before and After

### Before

The pre-revision Section 4.4 used nine sentences (approximately 160 words):

1. restated Q3 as a question;
2. described the matched subset and controls;
3. navigated to the figure and tables;
4. stated output changes without naming or quantifying the response statistic;
5. reported forecast-window fidelity;
6. ended with a bounded interpretation.

### After

The revised Section 4.4 uses seven sentences and 179 words under a conservative
LaTeX-stripped count:

1. directly answers Q3;
2. defines the 84-pair frozen matched setting and fixed quantities;
3. compresses the two control definitions;
4. separates Figure 3's per-pair role from Table 3's aggregate role;
5. reports the forecast-output response statistic;
6. reports complete-window fidelity and geographic-cluster intervals;
7. gives the bounded Q2+Q3 predictive-state interpretation.

The final source structure remains:

> short conclusion/protocol paragraph → Figure 3 → Table 3 → result paragraph

## 3. Forecast-Output Response

The response statistic is named as the **per-minicube masked mean absolute
forecast difference over the common forecast mask**.

- Actual vs. matched-donor weather: `0.03592`
- Actual vs. normalized-mean weather: `0.08137`
- Finite positive pairwise values: `84/84` for both substitutions

These values are rounded from the frozen fields:

- `models.exclusive.q3_donor_fidelity.response_magnitude.extreme_actual_vs_donor.mean`
  = `0.035918147763281706`
- `models.exclusive.q3_donor_fidelity.response_magnitude.extreme_actual_vs_mean.mean`
  = `0.08136940104443402`

Frozen source:
`evidence_workspace/raw/release/q3_extreme_state_audit.json`  
SHA-256:
`9dae43b9a8a4fcdf0a73ef91daa58c189a88e769541ce295046cd0e938497041`

The text does not add a detectability threshold or significance claim. These
values establish forecast-output change only.

## 4. Forecast-Window Fidelity Regression

The scientific estimand remains the masked MSE over the complete 20-step
forecast window:

- Matched donor: control-minus-actual
  `DeltaLoss = 0.00257`, geographic-cluster 95% CI
  `[0.00112, 0.00399]`
- Normalized mean: control-minus-actual
  `DeltaLoss = 0.01126`, geographic-cluster 95% CI
  `[0.00547, 0.01708]`

Positive values continue to mean that actual weather has lower loss. Both
intervals exclude zero. The interpretation remains restricted to the frozen
84-pair matched protocol. No causal, counterfactual, physical-fidelity, or
extreme-specific-enhancement claim was added.

## 5. Mirror Synchronization

### `MANUSCRIPT_ZH_FULL.md`

- synchronized the conclusion-first 4.4 structure;
- added `0.03592` and `0.08137`;
- retained complete 20-step forecast-window semantics;
- retained the same evidence boundary as the English text.

### `MANUSCRIPT.md` and `MANUSCRIPT_ZH.md`

- synchronized the current 4.4 result chain;
- replaced the historical Table 3 with the authoritative five-column table;
- restored the current three-panel Figure 3 and its current caption;
- removed the obsolete “Figure 3 not integrated / future insertion” status;
- updated the Q3-related Conclusion sentence to complete 20-step
  forecast-window fidelity.

Endpoint wording that remains elsewhere in the compact mirrors lies outside the
authorized 4.4/Conclusion scope and was not edited in this revision.

The historical file `evidence_workspace/tables/table3_q3.tex` is
**SUPERSEDED** and was not modified.

## 6. Table 3 Content and Float Position

Table 3's environment, body, values, columns, caption, label, font size, and
scientific definition are unchanged:

- Table 3 environment SHA-256:
  `f2f9dd7ec9f212ce132d7e597d2be04085b54d9979327783d81eaacc552dc55d`
- Table 3 tabular SHA-256:
  `c33059fe7767b658cc70d193e83567ce34053f9d153e815dcd84122b48c8d991`

Float trial:

- Before revision: Table 3 on PDF page 8, above References.
- Trial: changed `[t]` to `[!t]`.
- Result: Table 3 remained on page 8.
- Final action: reverted to the original `[t]` because the stronger placement
  hint produced no benefit.
- After revision: Table 3 remains on page 8, above References.

The table occupies the left column without clipping or overlap; References
begin below it with a visible gap. Moving it further would require a later
whole-paper layout decision. This remains a **layout gate**, not a scientific
or compilation blocker.

## 7. Figure 3 Regression

- Figure 3 is on PDF page 7.
- Figure 3 and its caption remain within the page bounds.
- No overlap with the Conclusion was detected.
- Figure 3 environment SHA-256:
  `bb50e15a2b30fa1625d7f2981454607a49f2df500937974d9cc35640f398dad6`
- Figure 3 PDF SHA-256:
  `bbf0444dd18c5c910e2bd3d3dcadeccb57e28d3b2bfeee930e004545b351c990`
- Figure 3 PNG SHA-256:
  `07521d9d718e1e9a2f45b5e9cd96d08855dde27c2677b25c355784f6da3b9152`

No Figure 1–3 asset was changed or re-exported.

## 8. Frozen-Block SHA Regression

| Block | Before SHA-256 | After SHA-256 | Result |
|---|---|---|---|
| Abstract | `d067709e98b84830d0c5a3cd78ac1f51904e5a42ac0b70abb993186ab64721ab` | `d067709e98b84830d0c5a3cd78ac1f51904e5a42ac0b70abb993186ab64721ab` | PASS |
| Introduction | `d171277066f1ce281947278340568e3867ad05d1e881eabbe3cb5ef2a54a24c9` | `d171277066f1ce281947278340568e3867ad05d1e881eabbe3cb5ef2a54a24c9` | PASS |
| Section 3 | `b054a42ed0783ad8bfbfa731bef5137cde11b68a58f1048ce12ad14fc4dbdf7d` | `b054a42ed0783ad8bfbfa731bef5137cde11b68a58f1048ce12ad14fc4dbdf7d` | PASS |
| Section 4.1 | `9feea977ba80119b27150811ca2cb50471f7bf0c8380d7e2aad95466cf8b5f45` | `9feea977ba80119b27150811ca2cb50471f7bf0c8380d7e2aad95466cf8b5f45` | PASS |
| Section 4.2 | `1255639a23e12090bece746b81f879ac3adcaa3af789d018adb22c3898666740` | `1255639a23e12090bece746b81f879ac3adcaa3af789d018adb22c3898666740` | PASS |
| Section 4.3 | `393750e4bb4f8e23703ebac4dd0ccd510257e5b62f00b216a32fe15b9a5a9d3a` | `393750e4bb4f8e23703ebac4dd0ccd510257e5b62f00b216a32fe15b9a5a9d3a` | PASS |
| Table 1 body | `e138d52fbfb8c374a48cd6342d8cc5b53a4f95773e228805092b4501dedbdf36` | `e138d52fbfb8c374a48cd6342d8cc5b53a4f95773e228805092b4501dedbdf36` | PASS |
| Table 2 body | `a372f2ae9fa3ce9d80298fee89453e1565e0eeabc269e671537baad42ebb069b` | `a372f2ae9fa3ce9d80298fee89453e1565e0eeabc269e671537baad42ebb069b` | PASS |
| Figure 3 environment | `bb50e15a2b30fa1625d7f2981454607a49f2df500937974d9cc35640f398dad6` | `bb50e15a2b30fa1625d7f2981454607a49f2df500937974d9cc35640f398dad6` | PASS |

Section 4.4 changed from
`017ba3a9643c878a4cd885709d7cddd634859fef759b050059f4ae5964da74b4`
to
`2f9326e7ea63a6622f3e84e3c7d0f1e68133a127843a8ac10ade429a8082bff5`,
as intended.

## 9. Compilation and Layout

Compilation command:

```text
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

using the project-local TeX Live 2026 installation.

| Check | Result |
|---|---:|
| PDF generated | PASS |
| Total pages | 9 |
| Section 4.4 heading | page 5 |
| Output-response/fidelity result paragraph | page 6 |
| Figure 3 | page 7 |
| Table 3 | page 8 |
| References begin | page 8 |
| LaTeX errors | 0 |
| Undefined references | 0 |
| Undefined citations | 0 |
| Multiply-defined labels | 0 |
| Overfull boxes | 0 |
| Underfull diagnostics | 8, non-blocking |
| Figure 3/Table 3 clipping or overlap | none detected |

Output PDF:
`paper/main.pdf`

Final file SHA-256:

- `paper/main.tex`:
  `3fa2fe271fcc77f7e3cd9c77f095408ed9e514106cc952ca62e09e6cb913a51f`
- `MANUSCRIPT_ZH_FULL.md`:
  `ed606a806110d4c85a5d3243a052d3f3f4238d40b34588e6d14c19f9ef906ee8`
- `MANUSCRIPT.md`:
  `3e59a8f05f5e320cfe01f6c48c8bb2f646fb54e74582de918feb9a62548afac6`
- `MANUSCRIPT_ZH.md`:
  `4867fad7c8d4da43be3ce468e2a8e8458a96328cfd74c2d3023baef0ce200e33`
- `paper/main.pdf`:
  `71a9082ec742bb1a4fa9009d5ba73adaff4f04adc310f9bd9b36d622a1e47caa`

## 10. Remaining Blockers

There is no evidence, claim, synchronization, or compilation blocker for the
Section 4.4 revision audit. The only remaining issue is the whole-paper layout
gate for Table 3, which remains on page 8 beside the References after the safe
`[!t]` trial failed to improve placement.

**Status:** `READY_FOR_4_4_AUDIT`
