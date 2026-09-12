# REVIEW_START_HERE

## Bottom line

The first-dataset evidence can now be reviewed from this directory without
re-running experiments. E1 standard prediction is accepted for 3 seeds x 4
splits. Corrected-mask matched-donor evidence is accepted for the four split
packages, with full-suffix and endpoint scopes kept separate. Dev476 and
IID2856 leaveout reports are accepted only for their stated scopes. FSR is a
completed fixed five-day recursive control with documented caveats.

The new derived C1/FSR common-suffix path comparison shows a positive
FSR-minus-C1 A/B output mismatch in all four splits. The geo-cluster bootstrap
intervals are positive in this derived statistic, but this does not replace
target-error evaluation, prove general equivalence, or establish a universal
method advantage. The FSR control also has a 1.1243 transition-compute ratio
relative to the C1 expectation, so claims of compute-matched superiority are
not supported.

## Accepted and reusable evidence

| Area | Status | Coverage | Entry |
|---|---|---:|---|
| E1 standard prediction | accepted | 3 seeds x 4 splits; exact manifests | `EVIDENCE_INDEX.csv` row E1 |
| Corrected-mask donor | accepted | IID 2078, OOD-t 1632, OOD-st 5577, OOD-s 7065 receiver pairs | `mechanism_summary.csv` and DONOR_V8 |
| Dev leaveout | accepted diagnostic | 476 samples, 9 combinations | LEAVEOUT_DEV |
| IID leaveout | accepted tested scope | 2856 samples, 9 combinations | LEAVEOUT_IID |
| FSR control | accepted with caveats | seed42, fixed five-day endpoints | FSR and FSR_QA |
| C1/FSR path CI | derived | 4 splits, existing common-suffix rows only | `statistics/paired_statistics.csv` |

Corrected-mask donor full-suffix usable counts are IID 2066, OOD-t 1605,
OOD-st 5437, and OOD-s 6965. Endpoint usable counts are IID 1214, OOD-t 884,
OOD-st 2731, and OOD-s 3549. The endpoint sets are not interchangeable with
the full-suffix sets.

## Main interpretation

The existing C0R/C1 comparison supports the narrower claim that recursive
multi-segment supervision differs from direct-only endpoint training and can
improve tested composition stability. It does not by itself prove superiority
over ordinary fixed-step recursion. FSR is the relevant completed control and
must be presented with its compute asymmetry and its single-seed scope.

The corrected donor results show that replacing the learned intermediate state
with the protocol-selected donor state generally increases target error in the
reported full-suffix comparisons. OOD-st endpoint uncertainty crosses zero.
These results support an association between the learned state and the tested
continuation behavior; they do not prove that the state is a complete physical
state or that the model supports arbitrary continuous-time or causal
counterfactual claims.

## Table and figure sources

- Corrected Table 4B, Table 6B, and Fig.7: `evidence_v8_corrected_mask_20260910T074500Z/`.
- F3, F5, and F8: `first_dataset_tables_figures_20260910T080000Z/` and its
  recorded prediction_v3 sources. F3's typical t+20 blank error panel is a
  valid-mask limitation, not zero error. F5 retains full prediction-horizon
  semantics and is not a suffix curve.
- E1 standard table: `/data/zs/multiseed_standard_eval_20260910T074115Z/E1_table_delivery/`.
- FSR control report and QA: `fixedstep_r_20260910T110000Z/reports/`.

## Known gaps

### Completed by existing evidence or this postprocessing

- Four-split corrected-mask donor summaries and source-indexed table/figure
  references.
- Existing E1 three-seed acceptance.
- Existing dev/IID leaveout summaries kept separate.
- C1/FSR A/B output path paired statistics and detailed row data.

### Missing or not substituted

- No completed direct-prediction plus explicit consistency-regularizer control
  was found in the reviewed artifacts.
- No formal compute-matched efficiency benchmark was found.
- FSR report early provenance/evaluation tables still contain placeholders;
  this is a documentation gap even though the final run/checkpoint facts are
  recorded.
- The requested local statistical-review file was unavailable in the current
  workspace.
- Second dataset work is outside this package.

## Reproduction

This package's only derived computation can be rerun with:

```bash
python3 /data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/evidence_closure_final/statistics/build_ab_path_paired_ci.py \
  --root /data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z \
  --out /data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/evidence_closure_final/statistics
```

The script reads existing CSVs only. Its output is paired by receiver and
horizon, records exclusions, and uses the fixed bootstrap seed in
`STATISTICS_PROTOCOL.md`.

## Final classification

This is a reviewable evidence closure package, not a claim that every proposed
control exists. Results are separated into standard prediction, mechanism
intervention, fixed-step control, and leaveout scopes. PASS labels in source
reports are retained as protocol outcomes and are not rewritten as equivalence
or universal guarantees.

The next action is paper-level review of the FSR caveats and the two known
control gaps; no additional experiment is started by this package.
