# Supplement QA

Overall status: **PASS**

## Scope and provenance

The supplement is a compact technical appendix to the anonymous AAAI-27
submission. It adds implementation and protocol details that do not fit in the
main paper. Q1--Q3 numerical results remain in the main paper and are not
reproduced as supplementary result tables.

Author confirmation identifies the submitted model as the completed
40-epoch, 14,880-update run. Earlier intermediate records are excluded from
the supplementary release. No training, evaluation, or result generation was
performed while preparing this appendix.

## Round 1: reverse outline

| Section | Core goal | Additional material retained | Status |
|---|---|---|---|
| Opening navigation | State the appendix path and evidence boundary. | A--D map; explicit non-duplication of main-paper results. | PASS |
| A. Additional Implementation Details | Make the inference and target-construction graph reproducible without repeating the main equations. | Context isolation; tensor dimensions; direct shared transition; readout cut point; stopped teacher and future-state target. | PASS |
| B. Training and Evaluation Protocol | Freeze optimization, preprocessing, split roles, and scorer details. | One training-configuration table; update schedule; masks; tensor export and official scorer. | PASS |
| C. Q2 Intervention and Statistical Protocol | Define the state-removal and identity-transition estimands and safeguards. | Matched arms; official versus paired aggregation; 10,000 paired bootstraps; implementation invariants. | PASS |
| D. Q3 Heat--Drought Subset and Weather-Control Protocol | Define the frozen extreme-weather selection, matched controls, and evidential boundary. | Q80 training-climatology thresholds; weather coverage; excluded selection signals; exact-season standardized-RMS matching; caliper and reuse cap; 84 pairs, 45 donors, 31 clusters; cluster bootstrap; non-causal scope. | PASS |

Every retained paragraph supplies implementation or protocol information that
is additional to the main paper. The former repeated equations, Q1--Q3 result
tables, temporal/land-cover breakdown appendix, and conclusion-style recap
were removed.

## Round 2: claim--evidence audit

- No new scientific claim or experiment was introduced.
- Q2 distinguishes official dataset-level score differences from the mean
  paired-minicube difference and its bootstrap interval.
- State removal is the primary Q2 intervention; identity transition remains a
  supporting diagnostic.
- The Q3 subset is the 84-pair extreme heat--drought selection used for the
  weather intervention. Thresholds come from the training climatology and are
  frozen before model evaluation.
- Future NDVI, model predictions, forecast errors, and checkpoint outputs do
  not enter Q3 subset construction.
- Q3 donors are selected by deterministic nearest-neighbor matching within
  meteorological season using the frozen standardized-RMS distance, 1.5
  caliper, and reuse cap of five.
- Q3 uses actual, matched-donor, and normalized-mean future weather while
  keeping history, state, geography, horizon, readout, targets, and masks
  fixed.
- Q3 is described as conditional response fidelity, not causal identification
  or verified counterfactual prediction.
- Unsupported claims listed in `CLAIM_EVIDENCE_MAP.md` remain absent.

Status: **PASS**.

## Round 3: reviewer-facing completeness

| Reviewer view | Question checked | Where resolved | Status |
|---|---|---|---|
| World-model method | Is the state structurally isolated, advanced by a shared transition, and exposed at a removable forecast path? | Appendix A and the main-paper method. | PASS |
| Earth-observation experiment | Are split roles, masks, temporal grid, preprocessing, and official scoring clear? | Appendix B. | PASS |
| Q2 validity | Are arms matched, estimands separated, and implementation invariants stated? | Appendix C. | PASS |
| Q3 validity | Is the extreme-weather subset frozen independently of outcomes, is the matching distance specified, and are donor dependence and scope handled? | Appendix D. | PASS |
| Reproducibility | Are the verified optimizer, schedule, batching, hardware, selection rule, and intervention protocols recoverable? | Appendices B--D and the separate code ZIP. | PASS |

## Round 4: language and terminology

Grammar, agreement, articles, tense, conjunctions, sentence length, paragraph
topic sentences, and terminology were checked section by section. The text
consistently uses “context-only forecast,” “predictive state,” “shared
transition,” “state contribution,” “state removal,” “identity transition,”
“matched donor,” and “conditional response fidelity.” It does not introduce
Q4, composition claims, failed ablations, seed commentary, or training-run
limitations.

Status: **PASS**.

## Round 5: number audit

The compact PDF contains only configuration, dataset, and protocol counts
needed for reproduction:

| Item | Value retained | Evidence source | Status |
|---|---|---|---|
| Training duration | 40 epochs; 14,880 updates | main paper and author confirmation | PASS |
| Optimizer schedule | AdamW; verified rates, warm-up, cosine decay, clipping, and 20/60/20% stages | training configuration | PASS |
| Batch and hardware | global batch 64; 8 devices x 8 samples; 8 H200 GPUs | training configuration | PASS |
| Context and horizon | 10 context plus 20 forecast composites from 30 five-day composites | method/data configuration | PASS |
| State and patches | 256-dimensional state; 4x4 patches; 1,024 tokens | model configuration | PASS |
| OOD-t and Q2 sample counts | 1,904 OOD-t minicubes; 952 validation targets; 589 eligible paired units | frozen evaluation manifests | PASS |
| Q2 uncertainty | 10,000 paired bootstrap resamples | frozen Q2 protocol | PASS |
| Q3 subset definition | training-climatology Q80 hot/dry thresholds; at least 80% future-weather coverage | frozen Q3 protocol | PASS |
| Q3 matching rule | exact meteorological season; RMS standardized nearest-neighbor distance over eight frozen features; caliper 1.5; reuse cap 5 | frozen Q3 selector | PASS |
| Q3 matching counts | 84 matched pairs; 45 unique donors; 31 geographic clusters | frozen Q3 manifest | PASS |
| Q3 uncertainty | 10,000 geographic-cluster bootstrap replicates | frozen Q3 protocol | PASS |

No Q1--Q3 performance value, repeated result table, horizon breakdown, or
land-cover breakdown remains in the supplement.

## Round 6: LaTeX, visual, and anonymity audit

- `latexmk` completes with pdfTeX and no LaTeX error, undefined reference,
  missing citation, or overfull box.
- Output is a three-page, letter-size, two-column AAAI-27 PDF.
- All pages were rendered and visually checked for readable type, table rules,
  column flow, and whitespace. The short final page reflects the end of the
  compact technical appendix and introduces no formatting violation.
- The document uses the requested A--D technical-appendix structure.
- Exactly one `booktabs` table remains, with its informative multi-line
  caption below the table and aligned with the caption treatment in the main
  paper; the table uses no vertical rules.
- The PDF contains no duplicated main-paper equation block or result table.
- PDF metadata and visible author information are anonymous.
- Text scans find no author identity, private path, old project name,
  intermediate checkpoint label, excluded ablation, or unsupported fourth
  question.

Status: **PASS**.

## PDF--code consistency

| Item | Supplement | Code/config interface | Status |
|---|---|---|---|
| Public model name | TerraState | class and package name `TerraState` | PASS |
| Context / horizon | 10 / 20 five-day steps | configuration and model constants | PASS |
| State / patch | 256 dimensions; 4x4 output patches | configuration and model | PASS |
| Forecast path | context-only forecast plus removable state contribution | `models/terrastate.py` | PASS |
| Training duration | 40 epochs; 14,880 updates | `configs/terrastate.yaml` | PASS |
| Objective | ground truth + 0.5 knowledge-distillation (KD) term + scheduled future-state term | training entry point | PASS |
| Q2 | full, state removal, identity transition; paired bootstrap | Q2 evaluation entry point | PASS |
| Q3 | frozen 84-pair subset; actual, matched-donor, normalized-mean weather; cluster bootstrap | Q3 evaluation entry point and manifest | PASS |
| Results | Numerical results remain in main Tables 1--3 and reference JSON files | `results/*.json` | PASS |

## Protected-input integrity

This revision writes only inside `aaai27_supplement/`. It does not modify the
main paper, figures, original training repositories, weights, datasets,
existing experiment results, or code-package files. The code ZIP remains
unchanged.

## Final directed-revision audit

- The 84 groups are correctly described as the frozen extreme heat--drought
  evaluation samples together with their matched normal-weather donors.
- The donor metric now records the exact-season standardized-RMS nearest-
  neighbor rule, its eight features, the 1.5 caliper, and reuse cap of five.
- Duplicate method equations and Q1--Q3 numerical result tables were removed.
- The former extra temporal/land-cover appendix was removed.
- No failed ablation, Q4/composition result, new experiment, seed statement,
  or “single run/single dataset” limitation was added.
- The English PDF and Chinese review version share the same compact A--D
  structure and evidence boundary.
- The Chinese review version uses renderer-independent Markdown with inline
  code and Unicode symbols instead of MathJax-dependent LaTeX delimiters.
- The Chinese review version mirrors the English training table and its
  caption in native Markdown, including all ten frozen configuration rows.
