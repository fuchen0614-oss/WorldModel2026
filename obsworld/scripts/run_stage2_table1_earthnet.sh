#!/usr/bin/env bash
# Run the reproducible no-training raw EarthNet2021x diagnostic closure.
#
# This path evaluates raw IID/OOD manifests plus the legacy ENS bridge. It is
# useful for internal diagnostics/supplementary analysis, but it is not the
# formal GreenEarthNet CVPR-2024 ood-t_chopped Table 1 runner.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

require_var() {
    local name="$1"
    if [[ -z "${!name:-}" ]]; then
        echo "Missing required environment variable: $name" >&2
        exit 2
    fi
}

require_var DATA_ROOT
require_var TRAIN_MANIFEST
require_var IID_MANIFEST
require_var OOD_MANIFEST
require_var EVAL_ROOT

PYTHON_BIN="${PYTHON_BIN:-python}"
HASH_MODE="${HASH_MODE:-sha256}"
SCORE_WORKERS="${SCORE_WORKERS:-8}"
MODEL_BATCH_SIZE="${MODEL_BATCH_SIZE:-16}"
MODEL_NUM_WORKERS="${MODEL_NUM_WORKERS:-8}"
RUN_BASELINES="${RUN_BASELINES:-1}"
RUN_MODEL="${RUN_MODEL:-1}"
ASSEMBLE_OVERWRITE_ROW="${ASSEMBLE_OVERWRITE_ROW:-0}"
TABLE_ROOT="${TABLE_ROOT:-$EVAL_ROOT/table1}"
CLIMATOLOGY_CACHE="${CLIMATOLOGY_CACHE:-$EVAL_ROOT/cache/train_rgbn_doy_climatology.npz}"

if [[ "$RUN_BASELINES" != 0 && "$RUN_BASELINES" != 1 ]]; then
    echo "RUN_BASELINES must be 0 or 1" >&2
    exit 2
fi
if [[ "$RUN_MODEL" != 0 && "$RUN_MODEL" != 1 ]]; then
    echo "RUN_MODEL must be 0 or 1" >&2
    exit 2
fi
if [[ "$RUN_BASELINES" == 0 && "$RUN_MODEL" == 0 ]]; then
    echo "At least one of RUN_BASELINES/RUN_MODEL must be 1" >&2
    exit 2
fi

mkdir -p "$EVAL_ROOT" "$TABLE_ROOT"

score_targets() {
    local split="$1"
    local manifest="$2"
    local target_dir="$EVAL_ROOT/ens_targets/$split"
    "$PYTHON_BIN" eval/export_earthnet_score_targets.py \
        --dataset-root "$DATA_ROOT" \
        --manifest "$manifest" \
        --split "$split" \
        --output-dir "$target_dir" \
        --hash-mode "$HASH_MODE"
}

score_ens() {
    local prediction_dir="$1"
    local prediction_manifest="$2"
    local split="$3"
    local output_dir="$4"
    "$PYTHON_BIN" eval/score_table1_earthnet.py \
        --prediction-dir "$prediction_dir" \
        --prediction-manifest "$prediction_manifest" \
        --target-dir "$EVAL_ROOT/ens_targets/$split" \
        --target-manifest "$EVAL_ROOT/ens_targets/$split/target_manifest.json" \
        --workers "$SCORE_WORKERS" \
        --output-dir "$output_dir"
}

convert_ndvi() {
    local prediction_dir="$1"
    local prediction_manifest="$2"
    local split="$3"
    local manifest="$4"
    local output_dir="$5"
    "$PYTHON_BIN" eval/export_earthnet_npz_to_greenearthnet.py \
        --prediction-dir "$prediction_dir" \
        --prediction-manifest "$prediction_manifest" \
        --dataset-root "$DATA_ROOT" \
        --manifest "$manifest" \
        --split "$split" \
        --output-dir "$output_dir" \
        --hash-mode "$HASH_MODE"
}

score_ndvi() {
    local prediction_dir="$1"
    local prediction_manifest="$2"
    local split="$3"
    local manifest="$4"
    local output_dir="$5"
    local comparison_score_dir="${6:-}"
    local comparison_args=()
    if [[ -n "$comparison_score_dir" ]]; then
        comparison_args=(--comparison-score-dir "$comparison_score_dir")
    fi
    "$PYTHON_BIN" eval/score_table1_greenearthnet.py \
        --prediction-dir "$prediction_dir" \
        --prediction-manifest "$prediction_manifest" \
        --dataset-root "$DATA_ROOT" \
        --manifest "$manifest" \
        --split "$split" \
        --workers "$SCORE_WORKERS" \
        --output-dir "$output_dir" \
        "${comparison_args[@]}"
}

export_baseline() {
    local baseline="$1"
    local manifest="$2"
    local split="$3"
    local output_dir="$4"
    local args=(
        --dataset-root "$DATA_ROOT"
        --manifest "$manifest"
        --split "$split"
        --baseline "$baseline"
        --format earthnet_npz
        --output-dir "$output_dir"
        --hash-mode "$HASH_MODE"
    )
    if [[ "$baseline" == "climatology" ]]; then
        args+=(
            --climatology-cache "$CLIMATOLOGY_CACHE"
            --climatology-train-manifest "$TRAIN_MANIFEST"
            --climatology-train-dataset-root "$DATA_ROOT"
            --fit-climatology
        )
    fi
    "$PYTHON_BIN" eval/export_earthnet_table1_baseline.py "${args[@]}"
}

assemble_row() {
    local method_id="$1"
    local method_label="$2"
    local method_kind="$3"
    local seed="$4"
    local params="$5"
    local checkpoint="${6:-}"
    local extra=()
    if [[ -n "$seed" ]]; then
        extra+=(--seed "$seed")
    fi
    if [[ -n "$checkpoint" ]]; then
        extra+=(--checkpoint "$checkpoint")
    fi
    if [[ -n "${IID_TARGET_PARITY_REPORT:-}" ]]; then
        extra+=(--iid-target-parity-report "$IID_TARGET_PARITY_REPORT")
    fi
    if [[ -n "${OOD_TARGET_PARITY_REPORT:-}" ]]; then
        extra+=(--ood-target-parity-report "$OOD_TARGET_PARITY_REPORT")
    fi
    if [[ "$ASSEMBLE_OVERWRITE_ROW" == 1 ]]; then
        extra+=(--overwrite-row)
    fi
    "$PYTHON_BIN" eval/assemble_stage2_table1.py \
        --table-root "$TABLE_ROOT" \
        --method-id "$method_id" \
        --method-label "$method_label" \
        --method-kind "$method_kind" \
        --params-millions "$params" \
        --iid-ens-score "$EVAL_ROOT/ens_scores/$method_id/iid/earthnet_score.json" \
        --iid-ens-provenance "$EVAL_ROOT/ens_scores/$method_id/iid/score_provenance.json" \
        --iid-ndvi-score "$EVAL_ROOT/ndvi_scores/$method_id/iid/metrics_en21x.json" \
        --iid-ndvi-provenance "$EVAL_ROOT/ndvi_scores/$method_id/iid/score_provenance.json" \
        --iid-target-manifest "$EVAL_ROOT/ens_targets/iid/target_manifest.json" \
        --ood-ens-score "$EVAL_ROOT/ens_scores/$method_id/ood/earthnet_score.json" \
        --ood-ens-provenance "$EVAL_ROOT/ens_scores/$method_id/ood/score_provenance.json" \
        --ood-ndvi-score "$EVAL_ROOT/ndvi_scores/$method_id/ood/metrics_en21x.json" \
        --ood-ndvi-provenance "$EVAL_ROOT/ndvi_scores/$method_id/ood/score_provenance.json" \
        --ood-target-manifest "$EVAL_ROOT/ens_targets/ood/target_manifest.json" \
        "${extra[@]}"
}

for split in iid ood; do
    if [[ "$split" == iid ]]; then
        manifest="$IID_MANIFEST"
    else
        manifest="$OOD_MANIFEST"
    fi
    score_targets "$split" "$manifest"
done

if [[ "$RUN_BASELINES" == 1 ]]; then
    # Fit Climate first; Persistence Outperformance is evaluated against it.
    for split in iid ood; do
        if [[ "$split" == iid ]]; then
            manifest="$IID_MANIFEST"
        else
            manifest="$OOD_MANIFEST"
        fi
        rgbn_dir="$EVAL_ROOT/rgbn_predictions/climatology/$split"
        export_baseline climatology "$manifest" "$split" "$rgbn_dir"
        score_ens "$rgbn_dir" "$rgbn_dir/prediction_manifest.json" "$split" \
            "$EVAL_ROOT/ens_scores/climatology/$split"
        ndvi_dir="$EVAL_ROOT/ndvi_predictions/climatology/$split"
        convert_ndvi "$rgbn_dir" "$rgbn_dir/prediction_manifest.json" "$split" "$manifest" "$ndvi_dir"
        score_ndvi "$ndvi_dir" "$ndvi_dir/prediction_manifest.json" "$split" "$manifest" \
            "$EVAL_ROOT/ndvi_scores/climatology/$split"
    done
    assemble_row climatology Climatology non-learning "" 0

    for split in iid ood; do
        if [[ "$split" == iid ]]; then
            manifest="$IID_MANIFEST"
        else
            manifest="$OOD_MANIFEST"
        fi
        rgbn_dir="$EVAL_ROOT/rgbn_predictions/persistence/$split"
        export_baseline persistence "$manifest" "$split" "$rgbn_dir"
        score_ens "$rgbn_dir" "$rgbn_dir/prediction_manifest.json" "$split" \
            "$EVAL_ROOT/ens_scores/persistence/$split"
        ndvi_dir="$EVAL_ROOT/ndvi_predictions/persistence/$split"
        convert_ndvi "$rgbn_dir" "$rgbn_dir/prediction_manifest.json" "$split" "$manifest" "$ndvi_dir"
        score_ndvi "$ndvi_dir" "$ndvi_dir/prediction_manifest.json" "$split" "$manifest" \
            "$EVAL_ROOT/ndvi_scores/persistence/$split" \
            "$EVAL_ROOT/ndvi_scores/climatology/$split"
    done
    assemble_row persistence Persistence non-learning "" 0
fi

if [[ "$RUN_MODEL" == 1 ]]; then
    require_var METHOD_ID
    require_var METHOD_LABEL
    require_var METHOD_KIND
    require_var CONFIG
    require_var CHECKPOINT
    require_var CONDITIONING_STATS_PATH
    require_var SEED
    PARAMS_MILLIONS="${PARAMS_MILLIONS:-28.17}"

    model_extra=()
    if [[ -n "${EXTERNAL_DRIVER_ROOT:-}" ]]; then
        model_extra+=(--external-driver-root "$EXTERNAL_DRIVER_ROOT")
    fi
    for split in iid ood; do
        if [[ "$split" == iid ]]; then
            manifest="$IID_MANIFEST"
        else
            manifest="$OOD_MANIFEST"
        fi
        rgbn_dir="$EVAL_ROOT/rgbn_predictions/$METHOD_ID/$split"
        "$PYTHON_BIN" eval/predict_stage2_earthnet.py \
            --config "$CONFIG" \
            --checkpoint "$CHECKPOINT" \
            --data-root "$DATA_ROOT" \
            --split "$split" \
            --output-dir "$rgbn_dir" \
            --conditioning-stats-path "$CONDITIONING_STATS_PATH" \
            --manifest-path "$manifest" \
            --batch-size "$MODEL_BATCH_SIZE" \
            --num-workers "$MODEL_NUM_WORKERS" \
            --hash-mode "$HASH_MODE" \
            "${model_extra[@]}"
        score_ens "$rgbn_dir" "$rgbn_dir/prediction_manifest.json" "$split" \
            "$EVAL_ROOT/ens_scores/$METHOD_ID/$split"
        ndvi_dir="$EVAL_ROOT/ndvi_predictions/$METHOD_ID/$split"
        convert_ndvi "$rgbn_dir" "$rgbn_dir/prediction_manifest.json" "$split" "$manifest" "$ndvi_dir"
        score_ndvi "$ndvi_dir" "$ndvi_dir/prediction_manifest.json" "$split" "$manifest" \
            "$EVAL_ROOT/ndvi_scores/$METHOD_ID/$split" \
            "$EVAL_ROOT/ndvi_scores/climatology/$split"
    done
    assemble_row "$METHOD_ID" "$METHOD_LABEL" "$METHOD_KIND" "$SEED" "$PARAMS_MILLIONS" "$CHECKPOINT"
fi

echo
echo "WARNING: this is the raw EarthNet2021x diagnostic path, not the formal OOD-t chopped paper table."
echo "Table 1 artifacts:"
echo "  $TABLE_ROOT/table1_single_seed.md"
echo "  $TABLE_ROOT/table1_single_seed.csv"
echo "  $TABLE_ROOT/table1_bundle.json"
