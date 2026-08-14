#!/usr/bin/env bash
# plan-b-pvt · B4 post-training evidence pipeline (Q1–Q4), FORMAL by default.
# Order (freeze-then-test): FULL-val selection (frozen data manifest, NO discovery) ->
# freeze ONE checkpoint -> state contract (Q2 gate/T · Q3 weather/donor · Q4 composition
# +anti-collapse under a PRE-REGISTERED, hashed guard-config). OOD-t is PRINTED ONLY, run
# ONCE after freeze, never for selection. A missing donor manifest or an unset/unfrozen
# guard makes the contract INCOMPLETE (non-zero) — it is NOT reported as complete.
#
#   Formal: DATA_MANIFEST=<val.json> DATASET_ROOT=$DATA GUARD_CONFIG=<guard.json> \
#           DONOR_MANIFEST=<donors.json> bash scripts/run_b4_posttrain.sh
#   Smoke : LIMIT=8 bash scripts/run_b4_posttrain.sh        (NON-formal; no freeze)
#   Plan  : DRY=1 ... bash scripts/run_b4_posttrain.sh
#
# Strict prep (Fix 10): errexit is ON for every preparation step; it is disabled ONLY
# around the contract call so its non-zero INCOMPLETE rc can be captured and surfaced.
set -euo pipefail

REPO="${REPO:-/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb}"
DATA="${DATA:-/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet}"
PHASE1_OUT="${PHASE1_OUT:-$REPO/checkpoints/plan_b_b4a}"
EVAL_ROOT="${EVAL_ROOT:-$REPO/evaluations/plan_b_b4a_post}"
DATA_MANIFEST="${DATA_MANIFEST:-}"; DATASET_ROOT="${DATASET_ROOT:-$DATA}"; SPLIT="${SPLIT:-val}"
DONOR_MANIFEST="${DONOR_MANIFEST:-}"; GUARD_CONFIG="${GUARD_CONFIG:-}"
LIMIT="${LIMIT:-0}"; WORKERS="${WORKERS:-8}"; DRY="${DRY:-0}"

# conda activation trips `set -u` (unbound _CONDA_* vars); relax only around it.
set +u; source /csy-opt/cog8/zjliu17/miniconda3/etc/profile.d/conda.sh; conda activate WorldModel; set -u
cd "$REPO"
VAL="$DATA/val_chopped"; OODT="$DATA/ood-t_chopped"
SELECT_OUT="$EVAL_ROOT/select"; CONTRACT_OUT="$EVAL_ROOT/contract"
smoke=(); [ "$LIMIT" != "0" ] && smoke=(--limit "$LIMIT")
fdata=(); [ "$LIMIT" = "0" ] && fdata=(--data-manifest "$DATA_MANIFEST" --dataset-root "$DATASET_ROOT" --split "$SPLIT")

if [ "$LIMIT" = "0" ] && [ -z "$DATA_MANIFEST" ]; then
  echo "REFUSED: formal run needs DATA_MANIFEST (or LIMIT=N for a non-formal smoke)"; exit 1; fi

echo "=== 1) checkpoint selection  (formal=$([ "$LIMIT" = "0" ] && echo yes || echo NO/smoke)) ==="
if [ "$DRY" = "1" ]; then
  python eval/select_b4_checkpoint.py --ckpt-dir "$PHASE1_OUT" --val-dir "$VAL" \
    --output-dir "$SELECT_OUT" --dry-run "${smoke[@]}" "${fdata[@]}"; echo "DRY done"; exit 0; fi
python eval/select_b4_checkpoint.py --ckpt-dir "$PHASE1_OUT" --val-dir "$VAL" \
  --output-dir "$SELECT_OUT" --workers "$WORKERS" "${smoke[@]}" "${fdata[@]}"

if [ "$LIMIT" != "0" ]; then echo "SMOKE done (no freeze / no formal contract)"; exit 0; fi
SELECTED=$(python -c "import json;print(json.load(open('$SELECT_OUT/selection.json'))['selected_checkpoint'])")
echo "=== 2) frozen checkpoint = $SELECTED ==="

echo "=== 3) state contract (Q2/Q3/Q4) ==="
donor=(); [ -n "$DONOR_MANIFEST" ] && donor=(--donor-manifest "$DONOR_MANIFEST")
guard=(); [ -n "$GUARD_CONFIG" ] && guard=(--guard-config "$GUARD_CONFIG")
# Capture the contract rc without aborting the script: errexit off ONLY here.
set +e
python eval/eval_b4_state_contract.py --ckpt "$SELECTED" --val-dir "$VAL" \
  --data-manifest "$DATA_MANIFEST" --dataset-root "$DATASET_ROOT" --split "$SPLIT" \
  --output-dir "$CONTRACT_OUT" --workers "$WORKERS" "${donor[@]}" "${guard[@]}"
rc=$?
set -e
if [ "$rc" != "0" ]; then echo "=== contract INCOMPLETE (rc=$rc) — NOT complete; fix donor/guard before claims ==="; fi

echo "=== 4) OOD-t — COMMAND ONLY (run ONCE after review; never for selection) ==="
cat <<CMD
python eval/export_b4_predictions.py --track-dir "$OODT" --ckpt "$SELECTED" --output-dir "$EVAL_ROOT/oodt/pred"
python eval/eval_greenearthnet_official.py --target-dir "$OODT" --prediction-dir "$EVAL_ROOT/oodt/pred" \
  --output-dir "$EVAL_ROOT/oodt/score" --manifest <FROZEN_OODT_MANIFEST> --dataset-root "$DATASET_ROOT" --split ood-t --workers $WORKERS
CMD
exit $rc
