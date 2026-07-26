# OOD-t hot-dry predictive-state audit protocol (FROZEN)

- git_commit: `0ca675032439d87e6925618a9e80ed70d4cde374` (dirty=True)
- frozen_utc: 2026-07-26T00:00:00Z
- primary tier: **broad**  (strict=36, broad=84, primary=84, control_unique=45)

## What this is
Forcing-only extreme hot-dry subset of `ood-t_chopped` (INTERNAL state stress test) plus a
season/location/quality matched-normal control. Selection used ONLY future-weather forcing and
observed pre-forcing context -- never future NDVI, model output, prediction error, or a checkpoint.
Thresholds were frozen from the TRAIN climatology before any OOD-t scoring.

## Training-end usage (no re-selection; existing data only)
1. Verify: `sha256sum -c MANIFEST.SHA256` and check `num_files` / `files_sha256` in each manifest.
2. The evaluator reads the manifests directly and resolves root-relative paths via `--dataset-root`
   (or materialize a symlink view with `scripts/materialize_manifest_view.py`). No NetCDF is copied.

## NOT this
The EarthNet2021 extreme-2018 EO-WM external protocol (raw NPZ+CSV) is a SEPARATE track; no strict
same-table reproduction is claimed until its window mapping is verified.
