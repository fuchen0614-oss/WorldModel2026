# TerraState AAAI-27 Section 1 Revision Log

**Date:** 2026-07-28  
**Scope:** Section 1 `Introduction` only  
**Status:** `SECTION1_REVISION_COMPLETE_READY_FOR_FINAL_AUDIT`

## 1. Revision scope and authority

The English authority is `paper/main.tex`; `MANUSCRIPT_ZH_FULL.md` is the
complete Chinese mirror. `MANUSCRIPT.md` and `MANUSCRIPT_ZH.md` were updated
only in their Introduction sections. The revision did not modify the abstract,
Section 2, Section 3, Section 4, Limitations, Conclusion, tables, figure
environments, figure assets, bibliography, title, or author information.

The revised Introduction contains **511 English words**, excluding the
unchanged Figure 1 caption. The pre-revision audit counted approximately
574 words under the same scope.

## 2. SHA-256 regression

### 2.1 Files before and after

| File | Before | After |
|---|---|---|
| `paper/main.tex` | `3fa2fe271fcc77f7e3cd9c77f095408ed9e514106cc952ca62e09e6cb913a51f` | `8191d0ba1de07711a5969dcb3822fe1aecd3669e5711c8d7ec58b10a540a8200` |
| `MANUSCRIPT_ZH_FULL.md` | `ed606a806110d4c85a5d3243a052d3f3f4238d40b34588e6d14c19f9ef906ee8` | `1d26cdc8d3037116b79d3741a7be0fdeac3aae19794453a6cf23fabfd0bd2510` |
| `MANUSCRIPT.md` | `3e59a8f05f5e320cfe01f6c48c8bb2f646fb54e74582de918feb9a62548afac6` | `08481eb5c5bb529429978a60d600d87b51118a02a1425736e333a6b94f0c66a7` |
| `MANUSCRIPT_ZH.md` | `4867fad7c8d4da43be3ce468e2a8e8458a96328cfd74c2d3023baef0ce200e33` | `614d94e59df4882b1fc45294567ef12ec99db75cc489d763b336f4530bec635b` |
| `paper/main.pdf` | `e27142265a6cc5944e7da086d37e72dfeebc8c6ee335445758422ee806ef33d0` | `b35c21365f3f93545ce758a48fc1cd6cfcf7eba554ff9b6bf8605ad07b6ae306` |

The authoritative Introduction block changed from
`d171277066f1ce281947278340568e3867ad05d1e881eabbe3cb5ef2a54a24c9`
to
`ce34d1ca444bf783eb4ccad116bfb1f4a9dde7f67a1d03dddd328eff04bc2b92`.

### 2.2 Frozen-block regression

| Frozen block | Current SHA-256 | Regression result |
|---|---|---|
| Abstract environment | `d067709e98b84830d0c5a3cd78ac1f51904e5a42ac0b70abb993186ab64721ab` | Unchanged from frozen baseline |
| Figure 1 environment | `a977039948dafba50f4c6117fb41827c284d497c4ad3a80f2d1b0635fe7439ee` | Unchanged from frozen baseline |
| Section 2 | `6ebf7a733cae749c2eb5ea17a163f4d652e2a3834b24b249194f7505abc50d34` | Not edited |
| Section 3 | `b054a42ed0783ad8bfbfa731bef5137cde11b68a58f1048ce12ad14fc4dbdf7d` | Unchanged from frozen baseline |
| Section 4.1 | `9feea977ba80119b27150811ca2cb50471f7bf0c8380d7e2aad95466cf8b5f45` | Unchanged from frozen baseline |
| Section 4.2 | `1255639a23e12090bece746b81f879ac3adcaa3af789d018adb22c3898666740` | Unchanged from frozen baseline |
| Section 4.3 | `393750e4bb4f8e23703ebac4dd0ccd510257e5b62f00b216a32fe15b9a5a9d3a` | Unchanged from frozen baseline |
| Section 4.4 | `2f9326e7ea63a6622f3e84e3c7d0f1e68133a127843a8ac10ade429a8082bff5` | Unchanged from frozen baseline |
| Limitations | `02c7944f2122bcad29fc05a2762ab957648f3f050445e8570ea975c9508fe76c` | Not edited |
| Conclusion | `8b31a9ac48ee3c6ea1d8e2263d09710513341b198b6dad237a627d42a67ef5bd` | Not edited |

`paper/references.bib` and all Figure 1--3 files were read-only during this
revision.

## 3. New Introduction reverse outline

| Unit | Unique role | Resulting narrative action |
|---|---|---|
| P1 | Task and real-world setting | Defines sparse/cloud-obscured EO histories, past meteorology, geography, future weather, and task value; introduces predictive-state world modeling explicitly as this paper's perspective rather than a universal definition of EO forecasting. |
| P2 | Progress and evidence gap | Acknowledges improved observation prediction, then explains why fixed-window pixel accuracy cannot establish state use or weather-driven state advancement. |
| P3 | Scientific question and method identity | Grounds predictive state in future observables, poses one falsifiable question, introduces TerraState as a testable predictive-state world model, and gives the physical/causal/generative scope boundary once. |
| P4 | Mechanism overview | Follows history \(\rightarrow\) spatial state \(\rightarrow\) shared weather-conditioned transition \(\rightarrow\) explicit state contribution \(\rightarrow\) forecast; adds future-state anchoring and the two post-training interfaces without Q-number or estimator detail. |
| P5 | Evidence preview | Reports one OOD-t forecasting result and summarizes the Q2/Q3 evidence at the strongest supported qualitative level. |
| P6 | Contributions | Separates the scientific viewpoint, the TerraState method, and the evidence on the same trained model. |

The transition order is now:

> task → progress → evidence gap → scientific question → TerraState →
> mechanism → evidence → contributions

## 4. Resolution of the pre-audit Major issues

| Pre-audit Major | Resolution |
|---|---|
| P1 treated EO forecasting as inherently a world-modeling problem | Replaced the universal formulation with “We study this task from a predictive-state world-modeling perspective.” The task is introduced first; the world-model identity is then presented as the paper's scientific view. |
| P3 risked defining TerraState's exact intervention criteria as universal qualifications for a meaningful predictive state | Replaced the protocol-style definition with the general predictive-state basis, a concrete scientific question, and TerraState's method identity. Detailed Q2/Q3 estimands and frozen-control criteria no longer define the concept in the Introduction. |
| P4 read like a Q1/Q2/Q3 audit contract | Reorganized it around the actual computational mechanism and two high-level test interfaces. Removed Q numbering, \(\alpha\), identity-transition, teacher-encoder, and loss-estimator detail from the overview. |

The pre-audit Minor issues were also addressed:

- the result preview now reports \(R^2=0.56935\) and
  \(\mathrm{RMSE}=0.15059\) once;
- the contributions now have distinct viewpoint, method, and evidence roles;
- `declared state`, `same selected model`, endpoint-only Q3 language, and
  Q4/composition language were removed from the revised Introduction mirrors.

## 5. Information retained, removed, moved, and compressed

### Retained

- The real EO task, cloud obstruction, past meteorology, static geography, and
  supplied future weather.
- EarthNet2021 and GreenEarthNet as task-setting references.
- LatentTSF as evidence that accurate outputs need not imply ordered latent
  structure.
- Predictive-state representations as the conceptual anchor.
- TerraState's spatial state, shared transition, state readout, future-state
  anchor, state-removal interface, and weather-substitution interface.
- The supported Q1, Q2, and Q3 evidence chain.

### Removed from the Introduction

- The claim that the forecasting task is *therefore* necessarily a partially
  observed world-modeling problem.
- Protocol-heavy language such as `declared state`, `frozen controls`, and Q
  numbering in the method overview.
- Detailed success criteria and the complete loss definition from the
  conceptual paragraph.
- Repeated comparison with EO-WM and VegSim; those closest-work comparisons
  remain in Section 2, which was not edited.

### Compressed or deferred

- Q2/Q3 implementation and statistical detail remain in Sections 3.4 and 4.
- The one-time scope limitation replaces repeated defensive qualifications.
- Figure 1 retains its existing caption and role; no visual or caption change
  was made.

## 6. AAAI writing anchors

The revision followed structural actions documented in
`SECTION1_2_AAAI_WRITING_CALIBRATION_AND_PREAUDIT_20260728.md`; no wording or
technical claim was copied.

| Anchor | Structural action used |
|---|---|
| Drive-OccWorld | Establish task value and structural gap before naming the world model; preview evidence after the mechanism. |
| Simulator-Informed Latent States | Make a latent state's role concrete through its computational use rather than through terminology alone. |
| SparseWorld | Tie the gap to a specific representation/pathway limitation and let method components answer that limitation. |
| iTrendRNN | Acknowledge forecasting progress before introducing an internal-transparency/evidence gap. |
| Modeling Latent Non-Linear Dynamical System over Time Series (LaNoLem) | Use one explicit research question to bridge the gap and the method identity. |

## 7. Claim–evidence alignment

| Claim in the revised Introduction | Evidence basis | Boundary |
|---|---|---|
| TerraState retains useful OOD-t forecasting skill | Full OOD-t: \(R^2=0.56935\), RMSE \(=0.15059\), 1,904 minicubes | No SOTA, strict ranking, equivalence, or uniform leadership claim |
| The state-mediated contribution is load-bearing | State removal degrades Validation and OOD-t performance; both primary paired confidence intervals exclude zero | Does not imply that all predictive information passes through the state |
| Actual weather has higher complete-window fidelity than two controls | Positive control-minus-actual masked-loss effects with geographic-cluster intervals excluding zero on the frozen matched subset | No causal, counterfactual, physical-state, or extreme-specific claim |
| TerraState exposes a load-bearing, weather-responsive predictive state | Joint Q1 prerequisite + Q2 state contribution + Q3 response/fidelity evidence | Limited to the evaluated protocol and model |

No Q4, composition, non-collapse, hot-dry enhancement, 11,904/boundary80,
endpoint-only Q3, Published/Local, seed/run, \(\pm\), SOTA, or strict-ranking
claim was introduced into the revised Introduction.

## 8. English–Chinese synchronization

- `paper/main.tex` and `MANUSCRIPT.md` carry the same final English
  Introduction narrative.
- `MANUSCRIPT_ZH_FULL.md` and `MANUSCRIPT_ZH.md` carry a natural Chinese
  rendering with the same paragraph roles, numbers, qualifiers, and claim
  strength.
- Inline mathematics in the Markdown mirrors uses `$...$` for reliable
  rendering.
- The compact mirrors' stale endpoint/Q4/composition wording was removed from
  their Introduction sections. Their frozen Section 2 and later sections were
  not touched in this task.

## 9. Compilation and visual regression

Compilation command:

```text
PATH=/mnt/data/users/luzheng/workspace/iclr/czj/.tools/texlive-2026/bin/x86_64-linux:$PATH \
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Run from `TerraState_AAAI27/paper/`.

| Check | Result |
|---|---:|
| PDF generated | PASS |
| Total pages | 9, unchanged |
| LaTeX errors | 0 |
| Undefined citations | 0 |
| Undefined references | 0 |
| Multiply-defined labels | 0 |
| Overfull boxes | 0 |
| Underfull hboxes | 7 |
| Underfull vboxes | 2 |

The underfull diagnostics are non-blocking. One hbox diagnostic occurs in the
revised contribution list; visual inspection shows no clipping, overlap, or
misordered text. The remaining diagnostics occur in existing Method/reference
material or ordinary page balancing.

Visual/page regression:

- Introduction starts on page 1 and continues naturally below Figure 1 on
  page 2.
- Figure 1 remains at the top of page 2.
- Section 2 begins on page 2 after the contribution list.
- Figure 2 remains on page 6.
- Tables 1--2 and Figure 3 remain on page 7.
- Table 3 and References begin on page 8; References continue through page 9.
- No visible clipping, overlap, or float-order regression was found.

Output PDF:

`paper/main.pdf`

## 10. Frozen content not modified

- Abstract, title, anonymous author information, and copyright notice;
- Section 2 Related Work;
- frozen Section 3 and Equations (1)--(8);
- frozen Section 4, Tables 1--3, all Q1--Q3 numbers, and training identity;
- Limitations and Conclusion;
- Figure 1--3 environments, captions, paths, and image assets;
- `references.bib`;
- all experiment, model, checkpoint, and evidence files.

## 11. Section 2 TODOs recorded without modification

1. The opening Related Work paragraph remains somewhat list-like and can later
   be synthesized more explicitly by forecasting paradigm.
2. The structured-operator/group-action tail should be reconsidered because
   composition is no longer part of the Q1--Q3 main claim.
3. The compact mirrors contain historical endpoint/Q4 wording outside the
   Introduction in frozen Section 2/3 material. Any cleanup must occur in the
   dedicated Section 2 or mirror-wide synchronization task, not by reopening
   this Section 1 revision.

These TODOs do not block the independent final audit of Section 1.

