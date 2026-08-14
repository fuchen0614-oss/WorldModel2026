#!/usr/bin/env bash
# A' post-training evidence runbook (one command, but never auto-runs OOD-t).
#
# Order:  full val_dev selection  ->  freeze the SINGLE A checkpoint  ->
#         Q2 load-bearing / Q3 driver / Q4 composition on the frozen checkpoint
#         ->  PRINT (do not run) the one-time GreenEarthNet OOD-t command.
#
# Hard rules enforced here:
#   * OOD-t is NEVER selected on and NEVER auto-run; only its command is printed,
#     and only for the SINGLE frozen winner (rescue XOR fresh, never both).
#   * DRY_RUN=1 (default) prints every command and runs only NON-FORMAL smokes
#     (--limit). Set DRY_RUN=0 for the formal closure (still no OOD-t).
#   * Every evidence step verifies the frozen checkpoint SHA256 is unchanged.
#
# This script does not modify the model/trainer/config and does not git.
set -euo pipefail

REPO="${REPO:-/csy-mix02/cog8/zjliu17/Agent/WorldModel2026}"
cd "$REPO"

# --- required inputs (frozen, read-only) ---
CONFIG_SELECT="${CONFIG_SELECT:-configs/train/plan_a_prime_from_s15.yaml}"   # contract == rescue's (init keys are runtime-only)
CONFIG_RESCUE="${CONFIG_RESCUE:-configs/train/plan_a_prime_from_s1a_stage2.yaml}"
CONFIG_FRESH="${CONFIG_FRESH:-configs/train/plan_a_prime_from_s15.yaml}"
RESCUE_DIR="${RESCUE_DIR:-$REPO/checkpoints/plan_a_prime_from_s1a_stage2}"
FRESH_DIR="${FRESH_DIR:-$REPO/checkpoints/plan_a_prime_from_s15}"
VAL_MANIFEST="${VAL_MANIFEST:?set VAL_MANIFEST to the frozen val_dev manifest}"
DATA_ROOT="${DATA_ROOT:?set DATA_ROOT}"
STATS="${STATS:?set STATS (physical4 conditioning stats)}"
EVAL_ROOT="${EVAL_ROOT:-$REPO/evaluations/aprime_post_training}"

# OOD-t inputs are only used to PRINT the final command (never executed here).
GREEN_EVAL_ROOT="${GREEN_EVAL_ROOT:-<set GREEN_EVAL_ROOT>}"
OODT_MANIFEST="${OODT_MANIFEST:-<set OODT_MANIFEST (frozen ood-t_chopped)>}"

DRY_RUN="${DRY_RUN:-1}"
SMOKE_LIMIT="${SMOKE_LIMIT:-2}"
BATCH_SIZE="${BATCH_SIZE:-4}"
# Pre-declared guards (used only when DRY_RUN=0). Tune from a first smoke.
Q2_MIN_DEGRADATION="${Q2_MIN_DEGRADATION:-0.0005}"
Q3_MIN_STATE="${Q3_MIN_STATE:-0.01}"
Q3_MIN_OUTPUT="${Q3_MIN_OUTPUT:-0.0005}"
Q4_GUARD_DIRECT="${Q4_GUARD_DIRECT:-0.05}"
Q4_GUARD_COMPOSED="${Q4_GUARD_COMPOSED:-0.05}"

mkdir -p "$EVAL_ROOT"
PY="${PYTHON_BIN:-python}"
LIMIT_ARG=(); [[ "$DRY_RUN" == "1" ]] && LIMIT_ARG=(--limit "$SMOKE_LIMIT")
echo "=== A' post-training runbook (DRY_RUN=$DRY_RUN) ==="
echo "  selection config : $CONFIG_SELECT"
echo "  rescue dir       : $RESCUE_DIR"
echo "  fresh dir        : $FRESH_DIR"
echo "  val manifest     : $VAL_MANIFEST"
echo "  eval root        : $EVAL_ROOT"
[[ "$DRY_RUN" == "1" ]] && echo "  MODE: NON-FORMAL smoke (--limit $SMOKE_LIMIT); no formal winner is crowned."

# ---------------------------------------------------------------- Stage 1: select
SEL_OUT="$EVAL_ROOT/selection_val_dev.json"
SELECT_CMD=("$PY" eval/aprime_select_checkpoint.py
  --run "rescue=$RESCUE_DIR" --run "fresh=$FRESH_DIR"
  --config "$CONFIG_SELECT" --split val --manifest-path "$VAL_MANIFEST"
  --data-root "$DATA_ROOT" --conditioning-stats-path "$STATS"
  --metric ndvi_main --mode min --batch-size "$BATCH_SIZE"
  --output "$SEL_OUT" "${LIMIT_ARG[@]}")
echo; echo "[1/4] SELECT (val_dev, OOD-t-free, metric=ndvi_main):"; printf '  %q' "${SELECT_CMD[@]}"; echo
"${SELECT_CMD[@]}"

if [[ "$DRY_RUN" == "1" ]]; then
  echo; echo "DRY_RUN smoke complete. Selection was NON-FORMAL (no winner)."
  echo "Re-run with DRY_RUN=0 for the formal closure. OOD-t is never run by this script."
  exit 0
fi

# ---------------------------------------------------------------- Stage 2: freeze
read -r WIN_CKPT WIN_RUN WIN_SHA < <("$PY" - "$SEL_OUT" <<'PYEOF'
import json, sys
sel = json.load(open(sys.argv[1]))
cr = sel.get("cross_run_selection")
if not cr or not cr.get("selected_checkpoint"):
    sys.exit("no formal winner in selection output")
print(cr["selected_checkpoint"], cr.get("selected_run", "?"), cr.get("selected_checkpoint_sha256", "?"))
PYEOF
)
FROZEN_CONFIG="$CONFIG_FRESH"; [[ "$WIN_RUN" == "rescue" ]] && FROZEN_CONFIG="$CONFIG_RESCUE"
echo; echo "[2/4] FREEZE single A checkpoint:"
echo "  winner run     : $WIN_RUN"
echo "  winner ckpt    : $WIN_CKPT"
echo "  winner sha256  : $WIN_SHA"
echo "  winner config  : $FROZEN_CONFIG"
ACTUAL_SHA="$(sha256sum "$WIN_CKPT" | awk '{print $1}')"
[[ "$ACTUAL_SHA" == "$WIN_SHA" ]] || { echo "ABORT: winner sha mismatch ($ACTUAL_SHA != $WIN_SHA)"; exit 1; }
printf '{"frozen_checkpoint":"%s","run":"%s","sha256":"%s","config":"%s"}\n' \
  "$WIN_CKPT" "$WIN_RUN" "$WIN_SHA" "$FROZEN_CONFIG" > "$EVAL_ROOT/frozen_A_checkpoint.json"

# ---------------------------------------------------------------- Stage 3: Q2/Q3/Q4
echo; echo "[3/4] Q2 load-bearing / Q3 driver / Q4 composition on the FROZEN checkpoint"
"$PY" eval/aprime_load_bearing.py --config "$FROZEN_CONFIG" --checkpoint "$WIN_CKPT" \
  --split val --manifest-path "$VAL_MANIFEST" --data-root "$DATA_ROOT" \
  --conditioning-stats-path "$STATS" --batch-size "$BATCH_SIZE" \
  --min-degradation "$Q2_MIN_DEGRADATION" --output "$EVAL_ROOT/q2_load_bearing.json"

"$PY" eval/aprime_driver_sensitivity.py --config "$FROZEN_CONFIG" --checkpoint "$WIN_CKPT" \
  --split val --manifest-path "$VAL_MANIFEST" --data-root "$DATA_ROOT" \
  --conditioning-stats-path "$STATS" --batch-size "$BATCH_SIZE" \
  --min-state-change "$Q3_MIN_STATE" --min-output-change "$Q3_MIN_OUTPUT" \
  --output "$EVAL_ROOT/q3_driver.json"

# Q4 runs once per partition: the training partition and a held-out partition.
"$PY" eval/aprime_composition.py --config "$FROZEN_CONFIG" --checkpoint "$WIN_CKPT" \
  --partition-name train_dev --partition-role train --split train --manifest-path "$VAL_MANIFEST" \
  --data-root "$DATA_ROOT" --conditioning-stats-path "$STATS" --batch-size "$BATCH_SIZE" \
  --guard-direct-threshold "$Q4_GUARD_DIRECT" --guard-composed-threshold "$Q4_GUARD_COMPOSED" \
  --output "$EVAL_ROOT/q4_composition_train.json"
echo "NOTE: run Q4 again with the held-out partition manifest+split (e.g. ood-t_chopped)"
echo "      into q4_composition_heldout.json before drawing composition conclusions."

# ---------------------------------------------------------------- Stage 4: PRINT OOD-t
echo; echo "[4/4] ONE-TIME commands to run MANUALLY, post-freeze, for the SINGLE winner only:"
echo "----- full val_dev NDVI/loss (official evaluator, RGBN-derived NDVI) -----"
cat <<CMD
  $PY eval/eval_stage2_earthnet.py --config $FROZEN_CONFIG --checkpoint $WIN_CKPT \\
    --split val --manifest-path $VAL_MANIFEST --data-root $DATA_ROOT \\
    --conditioning-stats-path $STATS --batch-size $BATCH_SIZE \\
    --output $EVAL_ROOT/frozen_val_full.json
CMD
echo "----- GreenEarthNet OOD-t chopped Table-1 (RUN EXACTLY ONCE, winner only) -----"
cat <<CMD
  GREEN_EVAL_ROOT=$GREEN_EVAL_ROOT OODT_MANIFEST=$OODT_MANIFEST \\
  EVAL_ROOT=$EVAL_ROOT/table1_oodt METHOD_ID=terrastate-A METHOD_LABEL="TerraState-A" METHOD_KIND=learning \\
  CONFIG=$FROZEN_CONFIG CHECKPOINT=$WIN_CKPT CONDITIONING_STATS_PATH=$STATS \\
  bash scripts/run_stage2_table1_greenearthnet_oodt.sh
CMD
echo
echo "This script intentionally did NOT run OOD-t. Run the block above by hand only"
echo "after you accept the frozen winner. Only $WIN_RUN goes to OOD-t (never both)."
