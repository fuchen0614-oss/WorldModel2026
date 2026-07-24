#!/usr/bin/env bash
# Formal GreenEarthNet CVPR-2024 OOD-t chopped Table 1 closure.
#
# Evaluation-only: this script loads an existing checkpoint and writes below
# EVAL_ROOT. It never launches training and never deletes local staged data.
# Raw EarthNet2021x/ENS diagnostics intentionally use a different runner.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

require_var() {
    local name="$1"
    if [[ -z "${!name:-}" ]]; then
        echo "Missing required environment variable: $name" >&2
        exit 2
    fi
}

require_bool() {
    local name="$1"
    local value="$2"
    case "$value" in
        0|1) ;;
        *) echo "$name must be 0 or 1 (got: $value)" >&2; exit 2 ;;
    esac
}

require_var GREEN_EVAL_ROOT
require_var OODT_MANIFEST
require_var EVAL_ROOT
require_var METHOD_ID
require_var METHOD_LABEL
require_var METHOD_KIND

PYTHON_BIN="${PYTHON_BIN:-python}"
HASH_MODE="${HASH_MODE:-sha256}"
MODEL_BATCH_SIZE="${MODEL_BATCH_SIZE:-8}"
MODEL_NUM_WORKERS="${MODEL_NUM_WORKERS:-8}"
SCORE_WORKERS="${SCORE_WORKERS:-8}"
RUN_PREFLIGHT="${RUN_PREFLIGHT:-1}"
RUN_BASELINES="${RUN_BASELINES:-1}"
RUN_MODEL="${RUN_MODEL:-1}"
RUN_ASSEMBLE="${RUN_ASSEMBLE:-1}"
VERIFY_MANIFEST_SIZES="${VERIFY_MANIFEST_SIZES:-0}"
ASSEMBLE_OVERWRITE_ROW="${ASSEMBLE_OVERWRITE_ROW:-0}"

TRACK="ood-t_chopped"
PROTOCOL="greenearthnet_cvpr2024_chopped_v1"
TABLE_ROOT="${TABLE_ROOT:-$EVAL_ROOT/table1_oodt_chopped}"
BASELINE_ROOT="${BASELINE_ROOT:-$EVAL_ROOT/baselines_oodt_chopped}"
METHOD_ROOT="${METHOD_ROOT:-$EVAL_ROOT/$METHOD_ID/oodt_chopped}"
CLIMATOLOGY_FULL_CUBE_ROOT="${CLIMATOLOGY_FULL_CUBE_ROOT:-$GREEN_EVAL_ROOT/iidx}"
METHOD_PARAMS_MILLIONS="${METHOD_PARAMS_MILLIONS:-28.17}"
METHOD_SEED="${METHOD_SEED:-42}"

require_bool RUN_PREFLIGHT "$RUN_PREFLIGHT"
require_bool RUN_BASELINES "$RUN_BASELINES"
require_bool RUN_MODEL "$RUN_MODEL"
require_bool RUN_ASSEMBLE "$RUN_ASSEMBLE"
require_bool VERIFY_MANIFEST_SIZES "$VERIFY_MANIFEST_SIZES"
require_bool ASSEMBLE_OVERWRITE_ROW "$ASSEMBLE_OVERWRITE_ROW"

if [[ "$RUN_MODEL" == 1 ]]; then
    require_var CONFIG
    require_var CHECKPOINT
    require_var CONDITIONING_STATS_PATH
    require_var NDVI_SOURCE
    case "$NDVI_SOURCE" in
        head|rgbn) ;;
        *) echo "NDVI_SOURCE must be 'head' or 'rgbn' (got: $NDVI_SOURCE)" >&2; exit 2 ;;
    esac
    test -f "$CHECKPOINT"
    test -f "$CONDITIONING_STATS_PATH"
fi

test -f "$OODT_MANIFEST"
mkdir -p "$EVAL_ROOT" "$TABLE_ROOT" "$BASELINE_ROOT" "$METHOD_ROOT"

manifest_size_args=()
if [[ "$VERIFY_MANIFEST_SIZES" == 1 ]]; then
    manifest_size_args=(--verify-manifest-sizes)
fi

overwrite_row_args=()
if [[ "$ASSEMBLE_OVERWRITE_ROW" == 1 ]]; then
    overwrite_row_args=(--overwrite-row)
fi

preflight() {
    local args=(scripts/preflight_greenearthnet_oodt_table1.py --dataset-root "$GREEN_EVAL_ROOT" --manifest "$OODT_MANIFEST" --manifest-protocol "$PROTOCOL" --split "$TRACK" --output "$EVAL_ROOT/preflight_oodt_chopped.json" --strict "${manifest_size_args[@]}")
    # A model-only rerun can reuse scored baselines. Require/check full iidx
    # cubes only when generating baselines or when they are already present.
    if [[ "$RUN_BASELINES" == 1 || -d "$CLIMATOLOGY_FULL_CUBE_ROOT" ]]; then
        args+=(--full-cube-root "$CLIMATOLOGY_FULL_CUBE_ROOT")
    fi
    "$PYTHON_BIN" "${args[@]}"
}

export_baseline() {
    local baseline="$1"
    local output_root="$BASELINE_ROOT/$baseline"
    local extra=()
    if [[ "$baseline" == climatology ]]; then
        extra=(--full-cube-root "$CLIMATOLOGY_FULL_CUBE_ROOT")
    fi
    local args=(eval/generate_baseline_predictions.py --baseline "$baseline" --dataset-root "$GREEN_EVAL_ROOT" --manifest "$OODT_MANIFEST" --manifest-protocol "$PROTOCOL" --split "$TRACK" --output-dir "$output_root/predictions" --prediction-manifest "$output_root/predictions/prediction_manifest.json" --hash-mode "$HASH_MODE" "${manifest_size_args[@]}" "${extra[@]}")
    "$PYTHON_BIN" "${args[@]}"
}

score_ndvi() {
    local prediction_dir="$1"
    local prediction_manifest="$2"
    local output_dir="$3"
    local comparison_score_dir="${4:-}"
    local comparison_args=()
    if [[ -n "$comparison_score_dir" ]]; then
        comparison_args=(--comparison-score-dir "$comparison_score_dir")
    fi
    local args=(eval/score_table1_greenearthnet.py --prediction-dir "$prediction_dir" --prediction-manifest "$prediction_manifest" --dataset-root "$GREEN_EVAL_ROOT" --manifest "$OODT_MANIFEST" --manifest-protocol "$PROTOCOL" --split "$TRACK" --workers "$SCORE_WORKERS" --output-dir "$output_dir" "${manifest_size_args[@]}" "${comparison_args[@]}")
    "$PYTHON_BIN" "${args[@]}"
}

register_row() {
    local method_id="$1"
    local label="$2"
    local kind="$3"
    local params="$4"
    local score="$5"
    local provenance="$6"
    local checkpoint="${7:-}"
    local seed="${8:-}"
    local parity_report="${9:-}"
    local baseline_reference_report="${10:-}"
    local args=(eval/assemble_greenearthnet_oodt_table1.py --table-root "$TABLE_ROOT" --method-id "$method_id" --method-label "$label" --method-kind "$kind" --params-millions "$params" --score "$score" --score-provenance "$provenance" --target-manifest "$OODT_MANIFEST" "${overwrite_row_args[@]}")
    if [[ -n "$checkpoint" ]]; then args+=(--checkpoint "$checkpoint"); fi
    if [[ -n "$seed" ]]; then args+=(--seed "$seed"); fi
    if [[ -n "$parity_report" ]]; then args+=(--evaluator-parity-report "$parity_report"); fi
    if [[ -n "$baseline_reference_report" ]]; then args+=(--baseline-reference-parity-report "$baseline_reference_report"); fi
    "$PYTHON_BIN" "${args[@]}"
}

if [[ "$RUN_PREFLIGHT" == 1 ]]; then
    preflight
fi

if [[ "$RUN_BASELINES" == 1 ]]; then
    # All non-climatology Outperformance values are relative to this score.
    export_baseline climatology
    score_ndvi "$BASELINE_ROOT/climatology/predictions" "$BASELINE_ROOT/climatology/predictions/prediction_manifest.json" "$BASELINE_ROOT/climatology/score"

    export_baseline persistence
    score_ndvi "$BASELINE_ROOT/persistence/predictions" "$BASELINE_ROOT/persistence/predictions/prediction_manifest.json" "$BASELINE_ROOT/persistence/score" "$BASELINE_ROOT/climatology/score"
fi

CLIMATOLOGY_SCORE_DIR="${CLIMATOLOGY_SCORE_DIR:-$BASELINE_ROOT/climatology/score}"
CLIMATOLOGY_SCORE="${CLIMATOLOGY_SCORE:-$CLIMATOLOGY_SCORE_DIR/metrics_en21x.json}"
CLIMATOLOGY_SCORE_PROVENANCE="${CLIMATOLOGY_SCORE_PROVENANCE:-$CLIMATOLOGY_SCORE_DIR/score_provenance.json}"
PERSISTENCE_SCORE_DIR="${PERSISTENCE_SCORE_DIR:-$BASELINE_ROOT/persistence/score}"
PERSISTENCE_SCORE="${PERSISTENCE_SCORE:-$PERSISTENCE_SCORE_DIR/metrics_en21x.json}"
PERSISTENCE_SCORE_PROVENANCE="${PERSISTENCE_SCORE_PROVENANCE:-$PERSISTENCE_SCORE_DIR/score_provenance.json}"

if [[ "$RUN_MODEL" == 1 ]]; then
    model_args=(eval/export_greenearthnet_predictions.py --config "$CONFIG" --checkpoint "$CHECKPOINT" --data-root "$GREEN_EVAL_ROOT" --manifest "$OODT_MANIFEST" --manifest-protocol "$PROTOCOL" --split "$TRACK" --output-dir "$METHOD_ROOT/predictions" --prediction-manifest "$METHOD_ROOT/predictions/prediction_manifest.json" --conditioning-stats-path "$CONDITIONING_STATS_PATH" --ndvi-source "$NDVI_SOURCE" --batch-size "$MODEL_BATCH_SIZE" --num-workers "$MODEL_NUM_WORKERS" --hash-mode "$HASH_MODE" "${manifest_size_args[@]}")
    echo "  NDVI_SOURCE (scored closure): $NDVI_SOURCE"
    if [[ -n "${DGH_STATS_PATH:-}" ]]; then model_args+=(--dgh-stats-path "$DGH_STATS_PATH"); fi
    "$PYTHON_BIN" "${model_args[@]}"
    score_ndvi "$METHOD_ROOT/predictions" "$METHOD_ROOT/predictions/prediction_manifest.json" "$METHOD_ROOT/score" "$CLIMATOLOGY_SCORE_DIR"
fi

METHOD_SCORE_DIR="${METHOD_SCORE_DIR:-$METHOD_ROOT/score}"
METHOD_SCORE="${METHOD_SCORE:-$METHOD_SCORE_DIR/metrics_en21x.json}"
METHOD_SCORE_PROVENANCE="${METHOD_SCORE_PROVENANCE:-$METHOD_SCORE_DIR/score_provenance.json}"

if [[ "$RUN_ASSEMBLE" == 1 ]]; then
    test -f "$CLIMATOLOGY_SCORE"
    test -f "$CLIMATOLOGY_SCORE_PROVENANCE"
    test -f "$PERSISTENCE_SCORE"
    test -f "$PERSISTENCE_SCORE_PROVENANCE"
    test -f "$METHOD_SCORE"
    test -f "$METHOD_SCORE_PROVENANCE"

    register_row climatology "Climatology" non-learning 0 "$CLIMATOLOGY_SCORE" "$CLIMATOLOGY_SCORE_PROVENANCE" "" "" "${CLIMATOLOGY_PARITY_REPORT:-}" "${CLIMATOLOGY_BASELINE_REFERENCE_REPORT:-}"
    register_row persistence "Persistence" non-learning 0 "$PERSISTENCE_SCORE" "$PERSISTENCE_SCORE_PROVENANCE" "" "" "${PERSISTENCE_PARITY_REPORT:-}" "${PERSISTENCE_BASELINE_REFERENCE_REPORT:-}"
    register_row "$METHOD_ID" "$METHOD_LABEL" "$METHOD_KIND" "$METHOD_PARAMS_MILLIONS" "$METHOD_SCORE" "$METHOD_SCORE_PROVENANCE" "${CHECKPOINT:-}" "$METHOD_SEED" "${METHOD_PARITY_REPORT:-}" ""
fi

echo "Formal GreenEarthNet OOD-t Table 1 outputs:"
echo "  evaluation root: $EVAL_ROOT"
echo "  table root:      $TABLE_ROOT"
echo "  table markdown:  $TABLE_ROOT/table1_oodt_chopped.md"
echo "  cache policy:    no local data/cache deletion is performed by this script"
