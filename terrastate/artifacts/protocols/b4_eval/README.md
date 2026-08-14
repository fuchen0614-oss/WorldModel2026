# B4 (TerraState) post-training evaluation — protocol & server commands

Same **one frozen checkpoint** proves Q1 forecast skill, Q2 load-bearing, Q3 driver
sensitivity, Q4 composition/non-collapse. B0 is never a contribution — the contribution
is the context-only predictive state + shared weather/geo/time transition + a measurable
load-bearing residual. **Freeze-then-test**: select on FULL `val_chopped` only → freeze
ONE checkpoint → run the contract + OOD-t ONCE. No B5, no separate benchmark.

All artifacts here are **generators / schema / templates only** — no manifest is
fabricated locally (this machine has no readable GreenEarthNet data; the server root
`/csy-mix02/.../TrainData/GreenEarthNet` is absent here). Build the real manifests on the
server with the commands below.

## 0) Freeze the data manifests (reuse existing freezer — do NOT re-invent)
```bash
# val_chopped (formal selection + contract target set)
python scripts/freeze_greenearthnet_chopped_protocol.py \
  --eval-root $DATA --track val_chopped --hash-mode sha256 \
  --output artifacts/protocols/b4_eval/val_chopped.manifest.json
# ood-t_chopped (VALIDATE / freeze ONLY — never scored during selection or contract)
python scripts/freeze_greenearthnet_chopped_protocol.py \
  --eval-root $DATA --track ood-t_chopped --hash-mode sha256 \
  --output artifacts/protocols/b4_eval/ood-t_chopped.manifest.json
```
`load_manifest_files(..., expected_protocol=greenearthnet_cvpr2024_chopped_v1)` re-verifies
dataset/protocol/role/source/digest on read; a stale or mislabelled manifest is rejected.

## 1) Build the Q3 donor manifest (season+geo matched, NetCDF-verified)
```bash
python scripts/build_b4_donor_manifest.py \
  --data-manifest artifacts/protocols/b4_eval/val_chopped.manifest.json \
  --dataset-root $DATA --split val \
  --out evaluations/plan_b_b4a_post/donors.json --max-geo-km 150
```
Writes `donors.json` (`{donor_schema, pairs}`) + `donors.audit.json`. Exits non-zero and
marks INCOMPLETE if any target lacks an eligible same-season/geo-near donor. The contract's
pure validator re-checks every pair (tile vs filename, season validity+equality+filename
cross-check, haversine recomputed from centroids vs recorded, ≤ max_geo_km) and fails closed
on any unproven claim.

## 2) Freeze the endpoint guard (USER pre-registers the threshold)
Copy `guard_config.TEMPLATE.json` → `guard_config.json`, set `threshold` **before** seeing
final numbers, fill `rationale` + `frozen_utc`. Threshold null / file absent ⇒
`UNSET_FAIL_CLOSED` and the contract exits non-zero. The threshold bounds a **diagnostic**
model-space endpoint MSE, not an official metric.

## 3) Dry-run the pipeline (no export/score)
```bash
DRY=1 DATA_MANIFEST=artifacts/protocols/b4_eval/val_chopped.manifest.json \
  bash scripts/run_b4_posttrain.sh
```

## 4) Small NON-FORMAL smoke (1–2 cubes, no freeze, no selection.json)
```bash
LIMIT=2 bash scripts/run_b4_posttrain.sh
```
Smoke scores EXACTLY the N exported cubes (mirror of the prediction tree), so
target-set == prediction-set == N. It never writes `selection.json`.

## 5) FULL-val selection (formal, no discovery) + contract
```bash
DATA_MANIFEST=artifacts/protocols/b4_eval/val_chopped.manifest.json \
DATASET_ROOT=$DATA SPLIT=val \
GUARD_CONFIG=artifacts/protocols/b4_eval/guard_config.json \
DONOR_MANIFEST=evaluations/plan_b_b4a_post/donors.json \
  bash scripts/run_b4_posttrain.sh
```
Selection → freeze ONE checkpoint → Q2/Q3/Q4 contract. Missing donor or unfrozen guard ⇒
contract INCOMPLETE (non-zero), never "complete".

## 6) One-shot OOD-t (run ONCE, after the frozen checkpoint is chosen; never for selection)
The launcher PRINTS this; run it manually with the frozen ood-t manifest:
```bash
python eval/export_b4_predictions.py --track-dir $DATA/ood-t_chopped \
  --ckpt <FROZEN_CKPT> --output-dir evaluations/plan_b_b4a_post/oodt/pred
python eval/eval_greenearthnet_official.py --target-dir $DATA/ood-t_chopped \
  --prediction-dir evaluations/plan_b_b4a_post/oodt/pred \
  --output-dir evaluations/plan_b_b4a_post/oodt/score \
  --manifest artifacts/protocols/b4_eval/ood-t_chopped.manifest.json \
  --dataset-root $DATA --split ood-t --workers 8
```

## Caliber note
Q2 full/gate0/T_identity and every Q3 arm report the **official** LC-balanced GreenEarthNet
R2/RMSE/NSE (official scorer, SCL clear-mask, B8A/B04 NDVI, 20×5-daily grid). Q4 endpoint
MSE / path gap and the per-cube paired win/tie/loss are **diagnostics** in model
normalized-NDVI space and are labelled as such; they never stand in for an official metric.
