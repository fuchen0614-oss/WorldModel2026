# E1 Acceptance Review

Review date: 2026-09-11

## Verdict

**ACCEPTED FOR E1 TABLE USE, WITH DOCUMENTATION CAVEATS.**

The formal delivery exists and passes the checks that affect the numerical E1
table: 3 seeds (27, 42, 97) x 4 splits = 12 completed evaluations; every
evaluation has exact manifest coverage, no missing or unexpected prediction
files, unchanged checkpoint status, and finite official aggregate metrics.
The five C1 summary metrics were independently recomputed from the per-seed
CSV using sample standard deviation (`ddof=1`) and match the delivered summary.

This review accepts the table as a standard-prediction E1 delivery. It does
not accept common-suffix, donor/state-replacement, FSR, Q2/Q3/Q4, horizon, or
second-dataset results because they are explicitly outside this delivery.

## Verified facts

| Check | Result |
|---|---|
| Seeds | 27, 42, 97; all four splits present |
| Splits | `iid_chopped`, `ood-t_chopped`, `ood-s_chopped`, `ood-st_chopped` |
| Requested/actual/unique samples | Exact equality for all 12 rows |
| Expected samples per split | IID 2,856; OOD-t 1,904; OOD-s 10,536; OOD-st 7,024 |
| Missing/unexpected predictions | 0 / 0 in every row |
| Acceptance/status | 12/12 `COMPLETE` |
| Official aggregate metrics | No non-finite official metric recorded |
| Checkpoint unchanged | `True` for all 12 rows |
| Checkpoint hashes | Three checkpoint SHA256 files independently pass `sha256sum -c` |
| Protocol | GreenEarthNet chopped, official LC-balanced scorer, `q1_full` standard forecast |
| Summary statistics | Mean and sample SD (`ddof=1`) recomputed for R2, RMSE, NSE, biasabs, RMSE25; 20/20 checks pass |

## Accepted scope

The E1 table is a standard 20-step forecast result. It uses the frozen C1
configuration, history length 130, forecast length 20, and the protocol in
`protocol_freeze.json`. C1 values come from `per_seed_metrics.csv`; baselines
come from the A08 same-protocol measured table. Literature values and blocked
or unavailable baselines are not substituted.

The OOD-s rows use the accepted repair overlay materialized under the
independent multiseed output root. The delivery records the 10,536-sample
manifest and the repair source separately; this is acceptable for this table,
but should remain explicit in the paper and source index.

## Numerical reading

C1 is extremely stable across seeds: the reported seed dispersion is small in
all four splits. This is dispersion across three trained/evaluated seeds, not
a confidence interval. Against the A08 baselines, C1 is not the best method
on every metric: for example, PredRNN and/or Contextformer have lower RMSE or
higher R2 in several splits. The table must therefore be presented as a
multi-metric comparison, not as a universal C1 win.

## Caveats and non-blocking issues

1. `SHA256SUMS.txt` contains paths relative to the multiseed root, not the
   `E1_table_delivery` directory. Running `sha256sum -c` from the delivery
   directory reports missing files; running it from
   `/data/zs/multiseed_standard_eval_20260910T074115Z` passes all five files.
   This is a reproducibility usability issue, not a checksum failure.
2. `checkpoint_inventory.tsv` has a malformed header/order: the data rows are
   `seed, path, status`, while the header says `checkpoint, seed, status,
   path`. The independent `checkpoint_sha256.txt`, per-seed source paths, and
   actual checkpoint hashes resolve the provenance for this table, so this is
   recorded as a documentation issue rather than a numerical block.
3. `nonfinite_score_values` is nonzero in the status CSV. The postprocessor
   documents these as per-pixel values emitted for insufficient observations;
   it retains the count for audit and accepts only when the official aggregate
   metrics are finite. This should remain documented and must not be described
   as every raw score pixel being finite.
4. A08 baselines are accepted here because the source explicitly labels them
   same-protocol measured and lists seeds 27/42/97. This review did not rerun
   those baseline models.

## Not part of this acceptance

- No confidence intervals across seeds were calculated; the requested table
  uses mean plus sample standard deviation.
- No new inference, image scan, horizon-statistic generation, or scoring was
  performed in this review.
- The old horizon-derived files are explicitly excluded by the delivery
  review and are not evidence for E1.

## Source files

See `SOURCE_INDEX.csv` in this directory for the exact source paths and the
role of each file.

