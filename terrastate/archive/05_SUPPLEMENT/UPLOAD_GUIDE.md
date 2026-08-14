# AAAI-27 Supplementary Submission — Final Upload Guide

Status: **FINAL**

## 1. Official requirements applied

AAAI-27 permits three independent supplementary uploads:

1. **Supplementary Document (PDF):** additional proofs, derivations,
   implementation or experimental details, dataset descriptions, examples, or
   extended results;
2. **Supplementary Media Archive (ZIP):** images, audio, video, animations, or
   similar media;
3. **Supplementary Code and Data Package (ZIP):** source code, scripts, data,
   and instructions that help reviewers assess reproducibility.

The submission is optional, reviewers are not required to read it, and the
main paper must remain self-contained. Every supplementary file must preserve
double-blind anonymity. The official guide prohibits links or pointers to
web-hosted supplementary material, including anonymous GitHub or Hugging Face
repositories.

The deadline is **July 31, 2026, 11:59 PM UTC-12 (Anywhere on Earth)**. This is
**August 1, 2026, 11:59 UTC** and **August 1, 2026, 7:59 PM China Standard
Time**.

Official pages:

- https://aaai.org/conference/aaai/aaai-27/supplementary-material/
- https://aaai.org/conference/aaai/aaai-27/submission-instructions/
- https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/

## 2. Final upload set

### Supplementary Document

Upload:

`aaai27_supplement/supplementary.pdf`

Final properties:

- 3 pages, US Letter, two-column AAAI-27 style;
- title exactly matches the submitted paper;
- visible author is `Anonymous submission`;
- PDF metadata author is empty;
- compact A--D appendix structure;
- one training-configuration table;
- no duplicated Q1--Q3 performance table;
- no Q4/composition claim, failed ablation, private path, old project name, or
  intermediate-checkpoint narrative.

Its content is deliberately limited to material genuinely additional to the
main paper:

- **A — Additional Implementation Details:** context isolation, predictive
  state construction, direct shared transition, state readout, and stopped
  training targets;
- **B — Training and Evaluation Protocol:** optimizer and schedule, split
  roles, preprocessing, masks, exports, and official scoring;
- **C — Q2 Protocol:** state removal, identity-transition control, global and
  paired estimands, bootstrap, and implementation invariants;
- **D — Q3 Protocol:** frozen extreme heat--drought selection, 84 matched
  pairs, 45 unique donors, 31 geographic clusters, weather controls, cluster
  bootstrap, and the non-causal evidence boundary.

Do not upload the TeX source, Chinese review version, fact-freeze files, QA
files, audit files, or this guide.

### Supplementary Code and Data Package

Upload:

`aaai27_code_package/TerraState_CodeData.zip`

Final properties:

- anonymous relative paths only;
- TerraState model and training/evaluation entry points;
- frozen Q1--Q3 manifests and reference metric JSON files;
- configuration, dependency list, dataset adapter, and brief instructions;
- no old project name, author identity, private path, private URL, token,
  credential, weights, training cache, or dataset copy.

Under the frozen no-weight policy, the ZIP supports implementation and
protocol inspection but does not provide push-button reconstruction of the
final checkpoint. The README states this boundary explicitly.

### Supplementary Media

Do not upload a media archive. The paper's figures are already embedded in the
main PDF, and no additional media are necessary for the claims.

### Reproducibility Checklist

The checklist was already uploaded separately in the designated OpenReview
field with the main-paper submission:

`paper/ReproducibilityChecklist.pdf`

Do not append it to the supplementary PDF and do not upload a second copy as
supplementary material.

## 3. Upload procedure

1. Open submission **25624** in OpenReview and choose **Edit**.
2. Upload `supplementary.pdf` to **Supplementary Document**.
3. Upload `TerraState_CodeData.zip` to **Supplementary Code and Data
   Package**.
4. Leave **Supplementary Media Archive** empty.
5. Save the revision before the supplementary deadline.
6. Reopen the submission page and verify that both uploaded filenames are
   visible.
7. Download both files from OpenReview rather than trusting the local upload
   dialog.
8. Open the downloaded PDF and extract the downloaded ZIP in a clean
   directory.
9. Confirm the downloaded files match the local file sizes and SHA256 values.

## 4. Final local identities

- `supplementary.pdf`: 233,381 bytes.
- `TerraState_CodeData.zip`: 67,410 bytes (filesystem display may round to
  66 KB).

Use the checksum files:

- `aaai27_supplement/SHA256SUMS.txt`
- `aaai27_code_package/SHA256SUMS.txt`

Run:

```bash
cd /mnt/data/users/luzheng/workspace/iclr/czj/TerraState_AAAI27/aaai27_supplement
sha256sum -c SHA256SUMS.txt

cd /mnt/data/users/luzheng/workspace/iclr/czj/TerraState_AAAI27/aaai27_code_package
sha256sum -c SHA256SUMS.txt
```

## 5. Frozen final decision

The following are intentionally excluded and should not be added during the
last upload:

- repeated main-paper equations or Q1--Q3 result tables;
- failed or exploratory ablations;
- Q4/composition evidence;
- new claims, new experiments, or post-selection analysis;
- author names, affiliations, acknowledgements, repository links, or private
  paths;
- initial, teacher, or final checkpoints;
- the complete GreenEarthNet dataset;
- Chinese notes, internal evidence ledgers, or QA reports.

The final reviewer-facing submission therefore consists of exactly:

1. the already submitted anonymous main paper;
2. the already submitted separate reproducibility checklist;
3. `supplementary.pdf`;
4. `TerraState_CodeData.zip`.
