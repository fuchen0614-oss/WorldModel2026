# TerraState citation and BibTeX audit

Audit date: 2026-07-28 UTC. Audit mode: read-only. No `.tex` or `.bib` source
was modified.

## Current inventory

Frozen inputs:

- `paper/main.tex`:
  `66d43adf18f42ed64880130176d64d8cf40ff226c295f7995dd88ce92825f131`
- `paper/references.bib`:
  `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659`

Submission inventory:

- LaTeX files traversed: 1.
- Citation commands: 25.
- Citation-key occurrences: 34.
- Unique cited keys: 24.
- BibTeX entries: 24.
- Missing / duplicate / unused entries: **0 / 0 / 0**.
- Unknown citation commands: 0.
- Unresolved `\input`/`\include`: 0.
- Existing compile log: no undefined- or multiply-defined-citation warning.

## Automated checks and manual adjudication

### WisPaper True Cite

Current report: `audit/final_20260728/true-cite.json`.

- Eligible entries: 19; checked: 19.
- Raw result: 0 pass labels, 19 warnings, 0 failures, 0 API errors.
- Every checked record returned `verified=true` and `titleMatch=true`.
- Warnings arise from `Surname, Given` versus `Given Surname`, TeX
  diacritics, and full versus abbreviated venue names. They are not 19
  confirmed bibliographic errors.
- Five `@misc` entries were skipped: `luo2026eowm`, `iele2026vegsim`,
  `albughdadi2026observability`, `wang2026groupactions`, and
  `ha2018worldmodels`. These were manually checked against official arXiv
  records.

The service is an observed web interface, not a documented stable API, and it
does not establish citation-to-claim support. All warning decisions below use
primary-source adjudication.

### Bib-Check

A fresh online-only Bib-Check run was started with all fix/write options
disabled. Its external check stage produced no result within the audit window
and was interrupted; setup logs are retained under
`audit/final_20260728/bibcheck/`. This is a **tool-level unable-to-complete**,
not a bibliographic failure. The inventory, primary-source adjudication, and
True Cite run above are independent of it.

## Version and metadata audit of all 24 keys

| Status | Keys | Adjudication |
|---|---|---|
| Formal metadata coherent | `shi2015convlstm`, `wang2017predrnn`, `gao2022earthformer`, `voleti2022mcvd`, `zhao2024vegediff`, `yang2026latenttsf`, `chen2023deeposg`, `hafner2019planet`, `hafner2020dreamer`, `littman2001predictive`, `bardes2024vjepa`, `saanum2024simplifying`, `wang2022pvtv2` | Author, title, venue/journal, year and present volume/pages/DOI were checked. LatentTSF is now the formal ICML/PMLR 306 version; V-JEPA is the formal TMLR/OpenReview version. |
| Formal metadata coherent; DOI addition optional | `requenamesa2021earthnet`, `benson2024multimodal`, `gao2022simvp`, `shinohara2025vitkoop`, `diaconu2022weather`, `assran2023ijepa` | Core metadata are correct. Missing DOI is a completeness issue, not a citation error. |
| Current arXiv citation appropriate at audit date | `luo2026eowm`, `iele2026vegsim`, `albughdadi2026observability`, `wang2026groupactions`, `ha2018worldmodels` | Title, author, year and arXiv identifier are coherent. Recheck the four 2026 records immediately before submission. |

The stable key `zhao2024vegediff` contains “2024” while the formal article is
2025; the entry itself correctly says 2025. A BibTeX key is an internal
identifier, so renaming it is unnecessary.

### Optional DOI additions

| Key | DOI |
|---|---|
| `requenamesa2021earthnet` | `10.1109/CVPRW53098.2021.00124` |
| `benson2024multimodal` | `10.1109/CVPR52733.2024.02625` |
| `gao2022simvp` | `10.1109/CVPR52688.2022.00317` |
| `shinohara2025vitkoop` | `10.1109/ICCVW69036.2025.00296` |
| `diaconu2022weather` | `10.1109/CVPRW56347.2022.00142` |
| `assran2023ijepa` | `10.1109/CVPR52729.2023.01499` |

Do not invent missing pagination. LatentTSF page numbers were **unable to
verify** from the inspected official artifact. The V-JEPA TMLR/OpenReview
record used here does not establish pagination or a DOI.

## Citation-to-claim audit

| Manuscript statement | Primary source support | Status / safe boundary |
|---|---|---|
| EarthNet2021 is a guided Earth-surface/video-prediction task with EO and weather inputs | EarthNet2021 official CVPRW paper | **supported** |
| GreenEarthNet uses 30 five-day composites, 10 context / 20 target, 128×128 at 20 m, weather and quality masks, and temporal OOD evaluation | GreenEarthNet official CVPR paper and supplement | **supported** |
| ConvLSTM, PredRNN, SimVP, Earthformer, MCVD and VegeDiff instantiate the named recurrent, video, transformer or diffusion families | Original method papers | **supported**; do not imply all share TerraState's exact protocol |
| Weather conditioning changes Earth-surface forecast behavior | Diaconu et al. and GreenEarthNet | **supported** as predictive behavior, not causal identification |
| EO-WM is a physically informed probabilistic EO world model and evaluates output/response behavior under forcing | EO-WM official arXiv paper | **supported** |
| VegSim is a scenario-conditioned vegetation world model with weather-conditioned latent rollout | VegSim official arXiv paper | **supported** |
| Observability forecasting targets cloud-aware EO monitoring | Official arXiv record | **supported** |
| Accurate output does not by itself establish orderly/useful latent state | LatentTSF directly studies latent disorder; predictive-state/world-model papers motivate state tests | **supported** when scoped; a universal claim about all EO world models is not supported |
| Predictive representations, PlaNet/Dreamer, I-JEPA/V-JEPA, softly invariant world models and operator/group-action work motivate explicit state/dynamics | Original papers | **supported** for the named technical characterizations |
| TerraState's initialization and exact implementation use the claimed local backbone | External citations support the architectures, not the internal implementation fact | **partially external**; rely on local provenance for the TerraState-specific fact |
| Public Table 1 values | GreenEarthNet Table 2 | **supported**; seed counts must be described accurately |

## Public baseline source audit

Primary source: Vitus Benson et al., “Multi-modal Learning for Geospatial
Vegetation Forecasting,” CVPR 2024, Table 2.

Local frozen sources:

- main paper SHA-256:
  `6162538030e6d13b849a051017a6d25e649ec7c7edb792988a4fa9cd30eb1114`
- supplement SHA-256:
  `886e020279ee68f523b5135af2d919945f489452227f6a4e986545b240f40200`

Values used in TerraState Table 1:

| Method | Published \(R^2\) mean | Published RMSE mean | Seed statement |
|---|---:|---:|---|
| Climatology | 0.58 | 0.18 | deterministic |
| ConvLSTM | 0.58 | 0.16 | mean of 3 seeds |
| PredRNN | 0.62 | 0.15 | mean of 3 seeds |
| Contextformer | 0.62 | 0.14 | mean of 3 seeds |

All means are copied without lowering or selective conversion. Omitting
uncertainty is legitimate with the existing note:

> For compactness, we report mean performance from the original publications
> and omit uncertainty estimates.

The publication reports three seeds for the selected learned methods; its
Earthformer result, not used in the compact TerraState table, is one seed.
Therefore neither “all public values are single-seed” nor “all public values
are three-seed” is valid as a universal statement.

Comparability:

| Comparison | Status |
|---|---|
| Methods within GreenEarthNet Table 2 | Comparable under the publication's table protocol, with disclosed seed differences |
| TerraState Q2/Q3 interventions within the frozen local protocol | Strict within checkpoint/protocol, subject to stated intervention caveats |
| TerraState versus published GreenEarthNet methods | **Not proven strictly comparable**; use separate panels and no rank |
| Q3 versus EO-WM/VegSim diagnostics | Not comparable; different tasks and intervention protocols |

## Anonymity audit

- `main.tex` uses `Anonymous Submission` and has no affiliation.
- No personal name, local user path, private-repository URL, or author identity
  was found in the active manuscript mirrors, Figure 3 CSV, or submission
  figures.
- PDF metadata inspection found no author/creator identity.
- Bibliography author names are external cited authors and are not an
  anonymity leak.

Status: **PASS**. Internal source paths appearing only in evidence JSON must
not be copied into submission files.

## Confirmed errors, warnings, and unable-to-verify items

### Confirmed errors

- **None in the current 24-entry bibliography.**
- The earlier arXiv-only LatentTSF and V-JEPA records have already been
  corrected in the current bibliography.

### Warnings

1. Six DOI additions above are optional metadata-completeness improvements.
2. Four 2026 preprints should receive a final venue-status check at submission
   time.
3. Table 1 should ideally state the public seed context and TerraState's
   one-run status directly in the caption, although the main text already
   discloses one run.
4. “Existing EO world models mainly rely on output accuracy” is too broad.
   Attribute the concern to EO-WM/common output-level benchmarks instead.

### Unable to verify

1. Strict public-method versus TerraState protocol equivalence.
2. LatentTSF formal page range.
3. V-JEPA TMLR pagination or DOI.
4. Cross-seed TerraState stability, because only one selected training run is
   reported.
5. A current Bib-Check result, because the external check stage did not
   complete; no source was changed.

No current substantive cited statement was found to be directly contradicted
by its cited primary source.
