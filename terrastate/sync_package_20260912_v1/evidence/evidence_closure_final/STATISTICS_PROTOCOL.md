# TerraState First-Dataset Evidence Closure: Statistics Protocol

## Scope

This package is postprocessing only. It does not train, run inference, rescore
predictions, or alter existing evidence packages. Standard prediction, common
suffix, single endpoint, development leaveout, IID leaveout, and OOD leaveout
are separate scopes.

## Evidence families

1. E1 uses the delivered three-seed standard prediction table: seeds 27, 42,
   and 97, four splits, 20 forecast steps, the official GreenEarthNet chopped
   LC-balanced scorer, and mean plus sample standard deviation (`ddof=1`).
   Seed dispersion is not a confidence interval.
2. Corrected-mask donor evidence reuses evidence_v8 and its four per-split
   paired row files. Full suffix and endpoint use their own valid sets. The
   donor is an intermediate-state replacement, not donor weather.
3. FixedStep-R (FSR) is retained as the fixed five-index-step endpoint-training
   variant. It is a method control, not a new dataset or a new scoring rule.

## Paired C1/FSR path statistic

The derived path statistic uses only existing common-suffix CSV rows. C1 and
FSR rows are joined on `dataset_index`, `cube`, `season`, and
`suffix_horizon`. A row is eligible only when both sides have the same
`n_valid`, matching `target_sum` and `target_sum_sq` within the recorded
numeric tolerance, and finite `A_B_output_mae`. Rows with no valid pixels are
excluded and counted; they are not silently treated as zero.

For each receiver `(dataset_index, cube, season)`, the statistic is the mean
of the horizon-level `FSR A_B_output_mae - C1 A_B_output_mae`. The point estimate
`delta_fsr_minus_c1_mean_cube_horizon` remains the pair-weighted mean over
eligible receiver-horizon rows. The geo-equal point estimate and bootstrap use
one value per receiver, then equal-weight audited spatial groups. This avoids
overweighting a receiver merely because it has more valid horizons.

The 95% interval is a 2,000-draw equal-group bootstrap with seed 20260910.
Positive delta means FSR has a larger A/B output mismatch than C1. This is a
path-consistency/output-compatibility statistic, not a target-error CI, a raw
state-distance CI, an official LC-balanced score, or a proof of equivalence.
The geo group is derived with the audited grouping rule because some older
plot CSVs carry stale full-cube labels.

## Donor statistics

The donor rows are reused from corrected evidence_v8. Their reported point
estimate is donor minus A delta MSE, with the accompanying spatial bootstrap
CI, sample scope, and group count from the accepted source. A CI crossing zero
is retained as uncertainty and is not translated into equivalence.

## Non-combinable quantities

Do not subtract metrics across different sample IDs, forecast horizons,
masks, weather paths, or protocols. Do not use pooled RMSE intervals to infer
significance of the official LC-balanced metric. Do not use seed standard
deviation as a confidence interval. Do not combine dev476 with IID2856 or
OOD scopes.

## Limitations

The local statistical-review reference requested for this task was not present
in the current workspace. The FSR report contains unresolved placeholders in
some early provenance/evaluation sections, although its final training and
evaluation sections provide the retained control facts. A direct-plus-
consistency-regularizer control and a formal compute-matched efficiency
benchmark were not found in the reviewed artifacts. These are gaps, not
results to be filled by substitution.

