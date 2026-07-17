#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

CONFIG="${CONFIG:-configs/train/stage2_earthnet_main.yaml}"
DATA_ROOT="${DATA_ROOT:-/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021}"
MAX_STEPS="${MAX_STEPS:-50000}"
BATCH_SIZE="${BATCH_SIZE:-2}"
NUM_WORKERS="${NUM_WORKERS:-4}"
PREFETCH_FACTOR="${PREFETCH_FACTOR:-1}"
PERSISTENT_WORKERS="${PERSISTENT_WORKERS:-1}"
LOG_INTERVAL="${LOG_INTERVAL:-50}"
GPUS="${GPUS:-1}"
DGH_STATS_PATH="${DGH_STATS_PATH:-}"
CONDITIONING_STATS_PATH="${CONDITIONING_STATS_PATH:-}"
MANIFEST_PATH="${MANIFEST_PATH:-}"
VALIDATION_MANIFEST_PATH="${VALIDATION_MANIFEST_PATH:-}"
REQUIRE_MANIFEST="${REQUIRE_MANIFEST:-0}"
EXTERNAL_DRIVER_ROOT="${EXTERNAL_DRIVER_ROOT:-}"
STAGE15_CHECKPOINT="${STAGE15_CHECKPOINT:-}"
RESUME_FROM="${RESUME_FROM:-}"
CHECKPOINT_DIR="${CHECKPOINT_DIR:-}"
LOG_DIR="${LOG_DIR:-}"
PREFLIGHT="${PREFLIGHT:-1}"
PREFLIGHT_MAX_FILES="${PREFLIGHT_MAX_FILES:-64}"
PREFLIGHT_SPLIT="${PREFLIGHT_SPLIT:-train}"
PREFLIGHT_OUTPUT="${PREFLIGHT_OUTPUT:-}"
PREFLIGHT_CHECK_MODEL="${PREFLIGHT_CHECK_MODEL:-1}"
RUN_TRAIN="${RUN_TRAIN:-1}"
PYTHON_BIN="${PYTHON_BIN:-python}"
TORCHRUN_BIN="${TORCHRUN_BIN:-torchrun}"

for FLAG_NAME in PREFLIGHT REQUIRE_MANIFEST PREFLIGHT_CHECK_MODEL RUN_TRAIN PERSISTENT_WORKERS; do
  FLAG_VALUE="${!FLAG_NAME}"
  if [[ "${FLAG_VALUE}" != "0" && "${FLAG_VALUE}" != "1" ]]; then
    echo "${FLAG_NAME} must be 0 or 1, got ${FLAG_VALUE}" >&2
    exit 2
  fi
done
if [[ "${NUM_WORKERS}" -lt 0 ]]; then
  echo "NUM_WORKERS must be non-negative, got ${NUM_WORKERS}" >&2
  exit 2
fi
if [[ "${PREFETCH_FACTOR}" -le 0 ]]; then
  echo "PREFETCH_FACTOR must be positive, got ${PREFETCH_FACTOR}" >&2
  exit 2
fi
if [[ "${LOG_INTERVAL}" -le 0 ]]; then
  echo "LOG_INTERVAL must be positive, got ${LOG_INTERVAL}" >&2
  exit 2
fi

echo "=== ObsWorld Stage2 EarthNet Training ==="
echo "CONFIG=${CONFIG}"
echo "DATA_ROOT=${DATA_ROOT}"
echo "MAX_STEPS=${MAX_STEPS}"
echo "BATCH_SIZE=${BATCH_SIZE}"
echo "NUM_WORKERS=${NUM_WORKERS}"
echo "PREFETCH_FACTOR=${PREFETCH_FACTOR}"
echo "PERSISTENT_WORKERS=${PERSISTENT_WORKERS}"
echo "LOG_INTERVAL=${LOG_INTERVAL}"
echo "GPUS=${GPUS}"
echo "DGH_STATS_PATH=${DGH_STATS_PATH:-<config>}"
echo "CONDITIONING_STATS_PATH=${CONDITIONING_STATS_PATH:-<config>}"
echo "MANIFEST_PATH=${MANIFEST_PATH:-<config>}"
echo "VALIDATION_MANIFEST_PATH=${VALIDATION_MANIFEST_PATH:-<config>}"
echo "REQUIRE_MANIFEST=${REQUIRE_MANIFEST}"
echo "PREFLIGHT_CHECK_MODEL=${PREFLIGHT_CHECK_MODEL}"
echo "RUN_TRAIN=${RUN_TRAIN}"
echo "EXTERNAL_DRIVER_ROOT=${EXTERNAL_DRIVER_ROOT:-<config>}"
echo "STAGE15_CHECKPOINT=${STAGE15_CHECKPOINT:-<config>}"
echo "RESUME_FROM=${RESUME_FROM:-<none>}"
echo "CHECKPOINT_DIR=${CHECKPOINT_DIR:-<config>}"
echo "LOG_DIR=${LOG_DIR:-<config>}"

EXTRA_ARGS=()
if [[ -n "${DGH_STATS_PATH}" ]]; then
  EXTRA_ARGS+=(--dgh-stats-path "${DGH_STATS_PATH}")
fi
if [[ -n "${CONDITIONING_STATS_PATH}" ]]; then
  EXTRA_ARGS+=(--conditioning-stats-path "${CONDITIONING_STATS_PATH}")
fi
if [[ -n "${MANIFEST_PATH}" ]]; then
  EXTRA_ARGS+=(--manifest-path "${MANIFEST_PATH}")
fi
if [[ -n "${VALIDATION_MANIFEST_PATH}" ]]; then
  EXTRA_ARGS+=(--validation-manifest-path "${VALIDATION_MANIFEST_PATH}")
fi
if [[ "${REQUIRE_MANIFEST}" == "1" || -n "${MANIFEST_PATH}" || -n "${VALIDATION_MANIFEST_PATH}" ]]; then
  EXTRA_ARGS+=(--require-manifest)
fi
if [[ -n "${EXTERNAL_DRIVER_ROOT}" ]]; then
  EXTRA_ARGS+=(--external-driver-root "${EXTERNAL_DRIVER_ROOT}")
fi
if [[ -n "${STAGE15_CHECKPOINT}" ]]; then
  EXTRA_ARGS+=(--stage15-checkpoint "${STAGE15_CHECKPOINT}")
fi
if [[ -n "${RESUME_FROM}" ]]; then
  EXTRA_ARGS+=(--resume-from "${RESUME_FROM}")
fi
if [[ -n "${CHECKPOINT_DIR}" ]]; then
  EXTRA_ARGS+=(--checkpoint-dir "${CHECKPOINT_DIR}")
fi
if [[ -n "${LOG_DIR}" ]]; then
  EXTRA_ARGS+=(--log-dir "${LOG_DIR}")
fi

if [[ "${PREFLIGHT}" == "1" ]]; then
  PREFLIGHT_ARGS=(
    --config "${CONFIG}"
    --data-root "${DATA_ROOT}"
    --split "${PREFLIGHT_SPLIT}"
    --max-files "${PREFLIGHT_MAX_FILES}"
  )
  if [[ "${PREFLIGHT_CHECK_MODEL}" == "1" ]]; then
    PREFLIGHT_ARGS+=(--check-model)
  fi
  if [[ -n "${DGH_STATS_PATH}" ]]; then
    PREFLIGHT_ARGS+=(--dgh-stats-path "${DGH_STATS_PATH}")
  fi
  if [[ -n "${CONDITIONING_STATS_PATH}" ]]; then
    PREFLIGHT_ARGS+=(--conditioning-stats-path "${CONDITIONING_STATS_PATH}")
  fi
  if [[ -n "${MANIFEST_PATH}" ]]; then
    PREFLIGHT_ARGS+=(--manifest-path "${MANIFEST_PATH}")
  fi
  if [[ -n "${VALIDATION_MANIFEST_PATH}" ]]; then
    PREFLIGHT_ARGS+=(--validation-manifest-path "${VALIDATION_MANIFEST_PATH}")
  fi
  if [[ "${REQUIRE_MANIFEST}" == "1" || -n "${MANIFEST_PATH}" || -n "${VALIDATION_MANIFEST_PATH}" ]]; then
    PREFLIGHT_ARGS+=(--require-manifest)
  fi
  if [[ -n "${EXTERNAL_DRIVER_ROOT}" ]]; then
    PREFLIGHT_ARGS+=(--external-driver-root "${EXTERNAL_DRIVER_ROOT}")
  fi
  if [[ -n "${STAGE15_CHECKPOINT}" ]]; then
    PREFLIGHT_ARGS+=(--stage15-checkpoint "${STAGE15_CHECKPOINT}")
  fi
  if [[ -n "${RESUME_FROM}" ]]; then
    PREFLIGHT_ARGS+=(--resume-from "${RESUME_FROM}")
  fi
  if [[ -n "${PREFLIGHT_OUTPUT}" ]]; then
    PREFLIGHT_ARGS+=(--output "${PREFLIGHT_OUTPUT}")
  fi
  "${PYTHON_BIN}" scripts/preflight_stage2_earthnet.py "${PREFLIGHT_ARGS[@]}"
fi

if [[ "${RUN_TRAIN}" == "0" ]]; then
  echo "Preflight-only mode complete; training was not launched."
  exit 0
fi

if [[ "${GPUS}" -gt 1 ]]; then
  "${TORCHRUN_BIN}" --nproc_per_node="${GPUS}" train/train_stage2_earthnet.py \
    --config "${CONFIG}" \
    --data-root "${DATA_ROOT}" \
    --max-steps "${MAX_STEPS}" \
    --batch-size "${BATCH_SIZE}" \
    --num-workers "${NUM_WORKERS}" \
    --prefetch-factor "${PREFETCH_FACTOR}" \
    --persistent-workers "${PERSISTENT_WORKERS}" \
    --log-interval "${LOG_INTERVAL}" \
    "${EXTRA_ARGS[@]}"
else
  "${PYTHON_BIN}" train/train_stage2_earthnet.py \
    --config "${CONFIG}" \
    --data-root "${DATA_ROOT}" \
    --max-steps "${MAX_STEPS}" \
    --batch-size "${BATCH_SIZE}" \
    --num-workers "${NUM_WORKERS}" \
    --prefetch-factor "${PREFETCH_FACTOR}" \
    --persistent-workers "${PERSISTENT_WORKERS}" \
    --log-interval "${LOG_INTERVAL}" \
    "${EXTRA_ARGS[@]}"
fi
