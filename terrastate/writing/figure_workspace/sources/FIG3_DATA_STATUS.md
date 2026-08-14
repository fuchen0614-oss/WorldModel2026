# Figure 3 data status — Revision 2

## Active source

Figure 3 is generated only from `fig3_aggregate_effects.csv`. The CSV contains:

- four frozen Q2 effect estimates: state-contribution ablation and `T→I` on
  Validation and Temporal shift/OOD-t;
- two frozen Q3 effect estimates: matched-donor and normalized-mean weather
  relative to actual weather;
- the stored 95% confidence-interval limits, resampling unit, sample count,
  source-record path, and source-record SHA-256.

The values were transcribed from three frozen release JSON records:

- `TerraState_AAAI27/evidence_workspace/raw/release/val_q2_state_contract_exclusive.json`;
- `TerraState_AAAI27/evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json`;
- `TerraState_AAAI27/evidence_workspace/raw/release/q3_extreme_state_audit.json`.

Each CSV row stores its own source path and SHA-256. The plotting script reads
every estimate and interval from the CSV; it contains no final experimental
number.

## Revision-2 decision

The active Figure 3 has two panels:

1. Q2 effects on Validation and OOD-t with paired bootstrap 95% CIs;
2. Q3 endpoint-loss increases with geographic-cluster bootstrap 95% CIs.

A third per-cube distribution or qualitative trajectory is no longer required.
This avoids re-running evaluation and avoids inventing unavailable per-cube
records. Tables remain responsible for exact numeric reporting; the figure
emphasizes effect direction, uncertainty, and the primary/supporting
distinction.

## Validation performed by the plotting script

`source/fig3_behavior.py` fails before writing the SVG if:

- required aggregate fields are missing;
- any estimate or CI limit is non-finite;
- an estimate lies outside its stored interval;
- sample counts are non-positive;
- a row's source path is outside the allowed workspace, its source file is
  missing, or its stored SHA-256 does not match that local frozen JSON;
- the CSV does not contain exactly four Q2 rows and two Q3 rows;
- Q2 metric identities are not `paired_mean_delta_r2`;
- Q3 metric identities are not `control_minus_actual_delta_loss`, or the
  intervention direction is not `Control loss minus actual loss`.

The Q2 points are the paired minicube-effect means stored with the same paired
bootstrap intervals. They are intentionally not the separately reported
dataset-level `ΔR²` point estimates in Table 2. The Q3 sign is
`control loss − actual-weather loss`, so positive values mean that weather
replacement worsens the endpoint prediction.

## Inactive future schema

`fig3_per_cube_effects.schema.csv` is retained only as an inactive provenance
specification should an authorized frozen export become available later. It is
not read by Revision-2 Figure 3 and is not required for any current output.

No script in this workspace runs the model, recomputes a prediction, or
reconstructs a confidence interval.
