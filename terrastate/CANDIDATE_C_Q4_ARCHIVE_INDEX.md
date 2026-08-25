# Candidate C / Q4 Archive Index

Last updated: 2026-08-25 Asia/Shanghai.

This file is the entry point for the TerraState Candidate C recursive-vs-direct
Q4 package. It records what is canonical, what is supplementary, and what should
not be interpreted as a stronger claim than the evidence supports.

## Current Verdict

- State: `Q4_LOCKED_COMPLETE_QUALIFIED_FAIL_NO_RERUN`.
- Locked run: `results/q4_eval_locked_4gpu_20260824T101119Z/`.
- Main result: C1 recursive passes all single-arm Q4 gates; C0R direct fails
  `composed_vs_direct` and `state_retention`.
- Cross-arm endpoint guard: `G_abs = 4/19`, overall `FAIL`.
- Supported claim: C1 shows a strong qualified compositional-stability signal
  on the fixed 4-GPU pair and locked split.
- Unsupported claim: Q4 overall PASS, endpoint non-inferiority, complete proof
  of compositional predictive state, composition-loss effectiveness, simulator
  calibration, or causal counterfactual response.

## Canonical Code

- Model: `models/terrastate_candidate_c.py`
- Training: `train/train_terrastate_candidate_c.py`
- Launcher: `train/launch_candidate_c.py`
- Q4 evaluator: `eval/eval_terrastate_candidate_c_q4.py`
- Q4 table extractor: `eval/q4_report_tables.py`
- Run wrapper: `scripts/run_q4_eval.sh`
- Tests: `tests/test_candidate_c_*.py`, `tests/test_resume_boundary11904.py`,
  `tests/test_q4_paths_and_floor.py`, `tests/test_q4_percube_eligibility.py`

## Canonical Locked Results

- Result root: `results/q4_eval_locked_4gpu_20260824T101119Z/`
- C1 aggregate: `results/q4_eval_locked_4gpu_20260824T101119Z/c1_score/q4_aggregate.json`
- C0R aggregate: `results/q4_eval_locked_4gpu_20260824T101119Z/c0r_score/q4_aggregate.json`
- Cross-arm compare: `results/q4_eval_locked_4gpu_20260824T101119Z/compare/q4_compare.json`
- Human-readable report:
  `ops/candidate_c_nightly/20260820T155316Z/Q4_LOCKED_EVAL_RESULT_REPORT_20260824.md`

The locked split has already been accessed once and sealed. Do not rerun,
change thresholds, swap checkpoints, or use locked metrics to tune future
losses.

## Main Numbers

| endpoint | C1 direct RMSE / R2 | C1 worst composed degradation | C0R direct RMSE / R2 | C0R worst composed degradation | G_abs pass |
|---:|---:|---:|---:|---:|---:|
| 10 | 0.1377 / 0.630 | 0.8% | 0.1369 / 0.634 | 9.2% | 2/6 |
| 15 | 0.1596 / 0.493 | 1.0% | 0.1600 / 0.491 | 9.1% | 0/5 |
| 20 | 0.1617 / 0.531 | 1.2% | 0.1628 / 0.525 | 14.7% | 2/8 |

Eligibility sensitivity is not optional: none=`1/19`, std-v1=`5/19`,
primary `n_valid>=64`=`4/19`. All fail the cross-arm endpoint guard.

## Key Weights

The selected final checkpoints are tracked with Git LFS. Their hashes are in
`KEY_WEIGHT_SHA256SUMS.txt`.

- Canonical 4-GPU C1:
  `ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt`
- Canonical 4-GPU C0R:
  `ops/candidate_c_nightly/20260820T155316Z/formal/run_c0r_20260823T063516Z/checkpoint_main.pt`
- Historical 14,880 anchor:
  `runs/resume11904_to14880/20260818_112933/checkpoint_fsval_best.pt`
- 8-GPU replicas are recorded for provenance but are not the Q4 locked evidence.

Intermediate milestone checkpoints such as `checkpoint_step*.pt` and
`checkpoint_milestone*.pt` are local training history. They are intentionally
not part of the minimal canonical package unless a future audit specifically
requires them.

## Documentation Map

- Candidate C execution ledger:
  `思路整理进展/A04_TerraState_CandidateC_实现训练与实验总账.md`
- Main project handbook:
  `思路整理进展/A05_TerraState_项目主线全景手册_原理证据进度与路线图.md`
- Q4 result report:
  `ops/candidate_c_nightly/20260820T155316Z/Q4_LOCKED_EVAL_RESULT_REPORT_20260824.md`
- Optional paper table:
  `writing/paper/supplementary_q4_table.tex`

## Suggested Next Work

Do not try to repair the locked Q4 verdict. The next experiment should be a new
pre-frozen development-only protocol, for example an Extreme Summer / Seasonal
Matched-Pair weather-response extension. It should be positioned as application
evidence linked to Q2/Q3/Q4, not as a retroactive reinterpretation of this
locked Q4 run.
