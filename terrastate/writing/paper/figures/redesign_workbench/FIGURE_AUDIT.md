# TerraState Figure Redesign Audit — Phase 2 Final Integration

## 0. Audit status and boundary

- Audit stage: approved two-figure hierarchy, colour/vector refinement, formal
  integration, and page-scale PDF inspection.
- Formal source now references the approved Figure 1 and Figure 2.
- Current v3 source and PDF left untouched.
- No title, abstract, manuscript claim, experiment code, checkpoint, training
  artifact, or result was modified.
- No external skill repository was downloaded or executed. The local TikZ
  workflow and already archived AAAI anchors were sufficient for this phase.

The Phase-1 hashes below remain the rollback baseline:

| Frozen file | SHA-256 |
|---|---|
| `paper/main.tex` | `b9e2800f0e6ef16f65d5fe264412d75459a749909708d2b5d994eb0937528582` |
| `paper/figures/terrastate_overview_v3.tex` | `3ae86a81dcc5ec431ed618b5a3a4ba977bba9f85d4262a68e9685db1cad52cee` |
| `paper/figures/terrastate_overview_v3.pdf` | `30de8d969308f48c1e395baedf8b3cc13acde138d7ed145ebf775c1b68433760` |

## 1. Recommendation

Recommend the two-figure layout:

1. Figure 1 is a full-width method hero: inference closure first, with one
   subordinate training-only band.
2. Figure 2 is a shallow same-checkpoint evidence map: Q1–Q3 are core and Q4 is
   visibly optional.

This division makes the first impression a weather-driven predictive-state
world model rather than a benchmark or an audit dashboard. It also lets Figure
2 explain interventions without surrounding the method chain with test cards.

The compact Figure 1 is a valid page-pressure fallback. Its verification strip
occupies \(43/414=10.4\%\) of source height, below the requested 15% ceiling.
It is not the preferred narrative because even a narrow strip slightly competes
with the method closure.

## 2. Ten-second test

| Question | Recommended Figure 1 | Figure 2 | Compact fallback |
|---|---|---|---|
| Can the innovation be read in ten seconds? | **Pass.** A single solid path exposes \(q_\theta\rightarrow P_\rho\rightarrow z_t\rightarrow T_\psi\rightarrow z_{t+h}\rightarrow O_\omega\rightarrow+\). | **Pass as a second-layer map.** It reads from one checkpoint to Q1–Q3, with Q4 downgraded. | **Pass, with mild competition** from the bottom index. |
| Is \(q\rightarrow T\rightarrow O\) visually central? | **Pass.** \(T_\psi\), spatial states, and the explicit addition node dominate the upper field. | Not applicable; the diagram intentionally references interventions rather than redrawing the model. | **Pass.** |
| Does it look like a method paper? | **Pass.** No ranking, result bar, or large verification card appears. | **Pass if presented after the method.** It is an evidence map, not a hero figure. | **Pass, but weaker than the two-figure layout.** |

## 3. Semantic trace audit

### Figure 1 inference

| Frozen requirement | Visual trace | Status |
|---|---|---|
| Cloud-masked EO history, past meteorology, and static geography enter the history-only operator | EO history, `past met.`, and `static \(g\)` converge on \(q_\theta\) | Pass |
| \(q_\theta\) and \(P_\rho\) remain distinguishable | Separate `history-only \(q_\theta\)` and \(P_\rho\) nodes | Pass |
| The context-only prior is formed before future weather | \(b_h\) branches directly from \(q_\theta\); there is no future-weather edge into the branch | Pass |
| The exposed state is spatial | \(z_t\) and \(z_{t+h}\) share an explicit grid glyph | Pass |
| Full24 weather, static \(g\), and horizon \(h\) enter only shared \(T_\psi\) | Three top chips terminate at \(T_\psi\) only | Pass |
| The future state participates in forecast closure | \(z_{t+h}\rightarrow O_\omega\rightarrow r_h\rightarrow+\) | Pass |
| The prediction combines state contribution and context prior | Both \(O_\omega\) and \(b_h\) reach the explicit addition node | Pass |

### Figure 1 training only

| Frozen requirement | Visual trace | Status |
|---|---|---|
| Only \(\mathcal L_{\rm GT}+0.5\mathcal L_{\rm KD}+\lambda_s\mathcal L_{\rm future\text{-}state}\) is nonzero | Exactly three loss nodes appear | Pass |
| GT and KD supervise the forecast | Dashed prediction branches reach \(\mathcal L_{\rm GT}\) and \(0.5\mathcal L_{\rm KD}\) | Pass |
| Future EO supplies a frozen target state only during training | `observed future EO → frozen \(q+P\) → \(z^\star_{t+20}\)` lies wholly in the dashed training band | Pass |
| Future-state anchoring is limited to \(h=20\) | Both \(z^\star_{t+20}\) and `\(h=20\) only` are explicit | Pass |
| Teacher and future observation do not enter inference | No solid edge leaves either training source | Pass |

### Figure 2

| Evidence requirement | Visual trace | Status |
|---|---|---|
| All tests use one checkpoint without retraining | A single top query bus is labelled `same frozen checkpoint` and `post-training; no retraining` | Pass |
| Q1 uses a paired local reference; reported literature stays separate | TerraState and matched backbone meet at paired local metrics; `Reported rows: Table 1` is outside the comparison arrows | Pass |
| Closure cut is the primary Q2 intervention | `closure cut \(r_h=0\)` has a solid border | Pass |
| \(T\rightarrow I\) is supporting evidence | It is explicitly labelled `support` and uses a lighter dashed border | Pass |
| Q3 changes only future weather into \(T_\psi\) | `future weather \(\rightarrow T_\psi\) only` sits above actual/mean/donor arms | Pass |
| State, output, and score are all tracked | One common readout names all three | Pass |
| Hot-dry is a stratum, not a fourth model input | It appears in a separate dashed bottom strip as `hot-dry vs matched-normal` | Pass |
| Q4 is optional | Smallest panel, grey text/fill, dashed border | Pass |
| No test is depicted as already passed | No numbers, check marks, winner badges, or directional result arrows appear | Pass |

## 4. Nonexistent-path and forbidden-content audit

No candidate TikZ source contains Stage A/B, B4, V2, cache construction,
checkpoint migration, VICReg, composition loss, output consistency, driver
distillation, residual-carrier training, benchmark rankings, or result values.

No edge sends:

- future weather into \(q_\theta\), \(b_h\), or the final addition directly;
- future EO or the frozen teacher into inference;
- Q1–Q4 back into training;
- hot-dry labels into the model.

The optional direct/composed query appears only in Figure 2 and is visually
subordinate. It is not represented as a training loss or established result.

## 5. Grayscale, font, and paper-scale audit

- Standalone canvases:
  - Figure 1: approximately \(996.3\times358.7\) PDF points;
  - compact Figure 1: approximately \(996.3\times412.5\) points;
  - Figure 2: approximately \(996.3\times229.1\) points.
- AAAI `aaai2027.sty` sets `\textwidth` to 7.0 in. At
  `0.98\textwidth`, a 1000-pt source canvas is scaled by approximately 0.50.
- Minimum source font is 18 pt, yielding approximately 9 pt at final paper
  scale. The main chain, loss labels, and intervention labels remain readable in
  the rendered page previews.
- Inference uses heavy solid arrows; training uses dashed arrows with a white
  under-stroke; post-training queries use fine dotted arrows. Panels and states
  also differ by fill, border weight, and glyph, so colour is not required.
- The generated grayscale previews retain all three path types and Q4 remains
  lower contrast.
- No overfull box is emitted by any standalone wireframe compile.

Minor refinement reserved for the colour phase:

1. tune the exact vertical position of the \(r_h\) label after the final palette
   and line weights are selected;
2. reduce the visual prominence of training-source boxes with colour rather
   than smaller text;
3. decide whether abstract EO/grid glyphs remain or are replaced by real,
   provenance-frozen thumbnails.

## 6. Actual AAAI-copy compilation

The candidates were inserted only into independent copies of `main.tex` inside
this workbench.

| Preview | Figure placement | Pages | Compile state |
|---|---|---:|---|
| current v3 baseline copy | Figure 1 on p.2 | 9 | clean citations/references; no overfull |
| recommended two-figure copy | Figure 1 on p.2; Figure 2 on p.6 | 9 | clean citations/references; no overfull |
| compact fallback copy | compact Figure 1 on p.2; no separate Figure 2 | 9 | clean citations/references; no overfull |

The recommended copy reports one underfull vertical box on page 7; both
candidate copies retain two pre-existing underfull prose boxes corresponding to
the same manuscript lines. These are not figure overflows. There are no
undefined citations, undefined references, or LaTeX errors.

This feasibility preview does not pre-commit the final float position: real
result values, confidence intervals, and qualitative arrays may change the
later page balance.

## 7. Image slots

Figure 1 deliberately reserves replaceable vector slots for:

1. cloud-masked EO history;
2. the final forecast;
3. observed future EO in the training-only branch.

The Phase-1 files use abstract grids only. Real imagery must not be inserted
until sample identity, timestamps, mask, colour scale, array provenance, and
selection rule are frozen. The spatial-state grids are conceptual glyphs and
must not be mistaken for measured output.

## 8. Independent visual review and corrections

An independent paper-scale review found no critical semantic error. It
recommended both figures after one major ambiguity was corrected: the matched
backbone in Q1 is now visibly separate from the frozen TerraState checkpoint
rather than appearing to be another output of it. The same review requested
non-colour emphasis for the actual-weather arm and explicit wording that the
panels are queries rather than outcomes; both corrections are present.

Final Figure 1 keeps the training band subordinate while retaining all three
and only three losses. Final Figure 2 uses a heavy outline for the
actual-weather reference, a heavy orange outline for the primary closure cut,
and a grey dashed Q4 panel. Its rightmost label was shortened to avoid edge
crowding at paper scale.

## 9. Formal-PDF audit

| Check | Final state |
|---|---|
| Figure 1 placement | page 2, full width |
| Figure 2 placement | page 6, full width |
| Main-text endpoint | Conclusion ends on page 7 |
| References | pages 8–9 only |
| PDF page size | US Letter, 612×792 pt |
| Fonts | all 32 referenced fonts embedded |
| Undefined citation/reference | none |
| Overfull box | none |
| Underfull warnings | one page vbox and two bibliography hboxes; no figure overflow |
| Minimum source font | 18 pt, approximately 9 pt after full-width scaling |

The first formal integration placed three empty result tables on page 7 and
pushed Limitations/Conclusion onto page 8. Because Q4 is optional and has no
real result package, its complete Table 3 source was moved, reversibly, to
`paper/supplementary_q4_table.tex`. This restores pages 8–9 to references
without shrinking fonts, changing margins, or altering any claim.

## 10. Final decision

The approved two-figure hierarchy is now the formal layout. Figure 1 remains
the method hero; Figure 2 remains a secondary evidence map. The compact
single-figure fallback and v3 are preserved but not used. Figure 3 remains
uninstantiated until real evidence exists.
