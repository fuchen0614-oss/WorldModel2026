# TerraState Limitations and Conclusion Revision Log

Date: 2026-07-28  
Status: `LIMITATIONS_CONCLUSION_REVISION_COMPLETE_READY_FOR_FINAL_AUDIT`

## 1. Scope

This revision changes only:

- `paper/main.tex`: `Limitations and Scope` and `Conclusion`;
- `MANUSCRIPT_ZH_FULL.md`: Sections 5--6;
- `MANUSCRIPT.md`: Sections 5--6;
- `MANUSCRIPT_ZH.md`: Sections 5--6;
- the PDF and routine LaTeX auxiliary files produced by the final compilation.

It does not change the title, abstract, Sections 1--4, equations, tables,
figures, captions, bibliography, experiments, evidence, model, or code.

## 2. File SHA-256

| File | Before | After |
|---|---|---|
| `paper/main.tex` | `0bd80eb824005857fb03930c74a581b153417019559974476d12d94dd3d79d00` | `1fe12204bad54b2b18a8debd5792cab9dff85a1e342cc35ca8df0e9a2d6eaab9` |
| `paper/main.pdf` | `a9892a795aa3f506c844cce184234f82bc507959b4dec8cde219d8386104c7e6` | `5f3931e373643d7aa3674fa3517e2e4f1e58f1632bd279b513d11f28bc021691` |
| `MANUSCRIPT_ZH_FULL.md` | `18c4637b50805c1169a7b5588e58ee9830dbb331ccd8146436e900154ee80815` | `0577238cd6d9561fb9ca7ea9fa4d8275da74a5b5f447e1d0407c4390d66099c6` |
| `MANUSCRIPT.md` | `ea801022bc815b51faeaebb9756138fc7e3caa643d5802dcd5beedd01cb98a07` | `8c8c47c00bc1ebc7337269f268539dfb9869fb73bc9a4feb2cc385a0ac3ebe21` |
| `MANUSCRIPT_ZH.md` | `eda2683e266c9ae37669c0c20741f7bf92879389aed9799305c02714728b7d94` | `d957d421af7efafb73d94ebd4775b3a1c150f01574d927c22197d27ac4c2f4ac` |
| `paper/main.log` | not a source baseline | `630577816ffd7a011c262173dfe0bd339d1753761350de5d17d1e36ac63b4af7` |

## 3. Target-block regression

The hashes below use each `\section{...}` marker and all text up to the next
section marker.

| Target block | Before | After |
|---|---|---|
| `Limitations and Scope` | `02c7944f2122bcad29fc05a2762ab957648f3f050445e8570ea975c9508fe76c` | `e4f1456ff2609d44d8f74ad66474e6e8a831184cd59cdffdd0411f6dba4fa186` |
| `Conclusion` | `8b31a9ac48ee3c6ea1d8e2263d09710513341b198b6dad237a627d42a67ef5bd` | `21f9dadc2155a1d21c48e1c2456cc9fdc05dc088eaa0e9510ee21d244337f5b1` |

The revised English Limitations contains 150 words. The revised English
Conclusion contains 109 words.

## 4. Frozen-block regression

The following local hashes were recorded immediately before the scoped patch
and reproduced after it.

| Frozen block | Before | After | Result |
|---|---|---|---|
| Section 1 Introduction | `ce34d1ca444bf783eb4ccad116bfb1f4a9dde7f67a1d03dddd328eff04bc2b92` | same | PASS |
| Section 2 Related Work | `e6609d90667a20d41e196bca0c1da50e6b928428e707439b6368d155eee4bc94` | same | PASS |
| Section 3 Method | `ac8c836546f41efdddda3be863abf6a22baf2562ce6d92b31405065afc28f6aa` | same | PASS |
| Section 4 Experiments | `85f681270b339a1c4f9e0cb73bb2777dc131d1f1e5585329609c6f778b0452a4` | same | PASS |
| Figure 3 environment | `71f99a264e41bff28bef55ba77a3fe2a26e07da25a53923e119dbc083554ef3a` | same | PASS |

Additional frozen asset hashes after the revision are:

- Figure 1 image:
  `cad4c85d4787babb3eee6f10fb12e86537da2c71ab6534656fd144f1ea587fd0`;
- Figure 2 image:
  `9192e1d0f66253bad3391ac7208a5de91e663586157776fa8c8d30a46aa714f5`;
- Figure 3 PDF:
  `3b9c764152a867b2d1aef1b82b5661eb18bbd613236cb37dc45d58dfac7f0a53`;
- `paper/references.bib`:
  `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659`.

No figure path, label, caption, float, source, or export was changed. In
particular, the Figure 3 path remains
`../figure_workspace/export/fig3_behavior_singlecol.pdf` and its label remains
`fig:behavior`.

## 5. Limitations structure

The three paragraphs now have one responsibility each:

1. **Representation and deployment scope.** TerraState learns a
   future-predictive representation, not a complete physical land-surface
   state. The evaluation uses realized future meteorology. Operational weather
   forecasts contain prediction error and may introduce input-distribution
   shift; these differences may affect state evolution and forecast quality,
   but their magnitude is not quantified here.
2. **Intervention evidence boundary.** Matched-control response is conditional
   predictive fidelity, not causal identification or counterfactual
   correctness. The hot-dry interval does not support extreme-specific
   enhancement. State removal supports a measurable increment through the
   explicit state path, not the claim that all output information must pass
   through that state.
3. **External validity.** Evidence is limited to GreenEarthNet temporal shift;
   cross-dataset generality is not established. Cloud screening and unobserved
   soil moisture, irrigation, and vegetation type remain possible limitations.

The former sentence
`Temporal composition remains unexplored as a core empirical claim.` was
deleted without replacement. Q4, composition, non-collapse, group actions, and
temporal compositionality are not reintroduced.

## 6. Conclusion structure

The revised single paragraph follows:

1. **Problem:** accurate EO forecasts alone do not establish formation and use
   of an internal world state.
2. **Method:** TerraState combines a history-derived spatial predictive state,
   shared weather-conditioned transition, explicit state-mediated forecast
   contribution, future-state anchoring, and post-training state/weather
   interventions.
3. **Evidence:** the model retains useful OOD-t skill; state removal causes
   measurable degradation; actual weather has greater complete-window fidelity
   than frozen controls.
4. **Broader significance:** TerraState turns an internal predictive-state
   claim in weather-driven EO world modeling from an architectural assertion
   into an empirically testable and falsifiable question.

This strengthens the world-modeling takeaway without adding SOTA, ranking,
causal, counterfactual, complete-physical-state, extreme-specific, or
composition claims.

## 7. Pre-audit issue closure

| Pre-audit issue | Resolution |
|---|---|
| Major M1: Limitations reopens Q4/composition | Deleted the composition sentence and kept the third paragraph focused on external validity. |
| Major M2: Conclusion lacks method recap and broader takeaway | Rebuilt the paragraph as problem → method → evidence → significance without adding results or claims. |
| Major M3: compact mirrors disagree with the authority | Synchronized only Sections 5--6 and removed stale single-run, public/local-ranking, and composition-open language there. |
| Minor m1: operational-weather sentence is ambiguous | Distinguished realized meteorology from operational forecast error and distribution shift, and stated that the deployment gap is not quantified. |
| Minor m2: `state-mediated contribution is positive` is indirect | Replaced it with the intervention-grounded statement that removing the contribution causes measurable degradation. |

## 8. English--Chinese synchronization

`MANUSCRIPT_ZH_FULL.md` follows the same three Limitations responsibilities and
the same four-step Conclusion. Both compact mirrors use the same scope,
evidence strength, and conclusion structure. The Chinese text uses
“可能影响” and “尚未量化” for operational-weather deployment, “支持” rather
than “证明” for evidence, and “可以接受经验检验和否证” for the broader
takeaway.

The compact mirrors' Sections 5--6 no longer contain:

- single-run or one-run limitations;
- Published/Local or public-versus-local ranking language;
- composition-open or Q4 language;
- endpoint-only Q3 language;
- 11,904/boundary80 language.

Stale wording outside Sections 5--6 was not changed because it lies outside
this task's authorized scope.

## 9. Figure 3 gate

`FIG3_SINGLECOL_LAYOUT_FINAL_AUDIT_20260728.md` exists and contains:

`FIG3_SINGLECOL_LAYOUT_FROZEN`

The gate reports a single-column `figure[t]`, the frozen Figure 3 asset on page
8, and no overfull boxes. The present revision preserved the Figure 3
environment and asset hashes exactly.

## 10. Compilation and layout

Compilation was run from `paper/` with the project-local TeX Live 2026:

```text
PATH=/mnt/data/users/luzheng/workspace/iclr/czj/.tools/texlive-2026/bin/x86_64-linux:$PATH \
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

| Check | Result |
|---|---:|
| PDF generated and parsed | PASS |
| Total pages | 9 |
| LaTeX errors | 0 |
| Undefined citations | 0 |
| Undefined references | 0 |
| Multiply-defined labels | 0 |
| Overfull hboxes | 0 |
| Overfull vboxes | 0 |
| Underfull hboxes | 14 |
| Underfull vboxes | 1 |

The underfull diagnostics are ordinary line/page balancing warnings and do not
produce clipping or overlap. Visual inspection of pages 7--9 confirms:

- Limitations and Conclusion remain readable in normal two-column order;
- Conclusion begins on page 7 and completes before References;
- Figure 3 remains intact in the left column of page 8;
- References begin below Figure 3 on page 8 and continue on page 9;
- no abnormal crop, overlap, cross-column intrusion, or float regression is
  visible.

## 11. Unmodified content

This revision did not modify:

- title, author/anonymity block, or abstract;
- Sections 1--4 or Equations (1)--(8);
- Figures 1--3, their paths, labels, captions, source files, or exports;
- Tables 1--3;
- `paper/references.bib`;
- any Q1--Q3 number, statistical unit, evidence file, model, checkpoint, code,
  or data file.

The missing `SECTION2_FINAL_AUDIT_20260728.md` was not treated as authority;
the current Section 2 text, its revision-log hash, and the Figure 3 frozen
audit regression hash were preserved unchanged.

## 12. Handoff

The text revision, mirror synchronization, gated compilation, and regression
checks are complete. This task does not perform the independent final audit
and does not declare the two sections frozen.

`LIMITATIONS_CONCLUSION_REVISION_COMPLETE_READY_FOR_FINAL_AUDIT`
