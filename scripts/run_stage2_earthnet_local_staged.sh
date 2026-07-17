#!/usr/bin/env bash
# ObsWorld Stage2 EarthNet: safe shared-NAS -> local-/tmp staging launcher.
#
# Only the copy below LOCAL_STAGE_ROOT is temporary.  Checkpoints, TensorBoard
# events, provenance and logs remain in the shared project directory.  The
# EXIT/INT/TERM/HUP traps remove the local copy after success, failure, or a
# normal user interruption.  See the Stage2 guide for the one manual recovery
# command needed after an untrappable kill -9 or a node reboot.

set -Eeuo pipefail

MARKER_NAME=".obsworld_stage2_local_stage_v1"
MARKER_SCHEMA="schema=obsworld-stage2-local-stage-v1"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

die() {
  echo "[stage2-local] ERROR: $*" >&2
  exit 2
}

canonical_path() {
  realpath -m -- "$1"
}

resolve_earthnet_dataset_root() {
  local candidate
  candidate="$(canonical_path "$1")"
  if [[ "$(basename "${candidate}")" == "earthnet2021x" ]]; then
    printf '%s\n' "${candidate}"
  elif [[ -d "${candidate}/earthnet2021x" ]]; then
    printf '%s\n' "${candidate}/earthnet2021x"
  else
    die "could not find earthnet2021x below source root: ${candidate}"
  fi
}

count_netcdf_files() {
  find "$1" -type f -name '*.nc' -printf '.' | wc -c | tr -d '[:space:]'
}

RUN_ID="${RUN_ID:-stage2_physical4_8gpu_b64_200ep_local_$(date +%Y%m%d_%H%M%S)}"
SOURCE_DATA_ROOT="${SOURCE_DATA_ROOT:-/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021}"
LOCAL_STAGE_ROOT="${LOCAL_STAGE_ROOT:-/tmp/${USER:-unknown}_obsworld_stage2_earthnet2021x}"
LOCAL_STAGE_ROOT="$(canonical_path "${LOCAL_STAGE_ROOT}")"

case "${LOCAL_STAGE_ROOT}" in
  /tmp/*)
    ;;
  *)
    die "LOCAL_STAGE_ROOT must be below /tmp, got: ${LOCAL_STAGE_ROOT}"
    ;;
esac
[[ "${LOCAL_STAGE_ROOT}" != "/tmp" ]] || die "LOCAL_STAGE_ROOT cannot be /tmp itself"

LOCAL_DATA_ROOT="${LOCAL_STAGE_ROOT}/EarthNet2021"
LOCAL_DATASET_ROOT="${LOCAL_DATA_ROOT}/earthnet2021x"
MARKER_PATH="${LOCAL_STAGE_ROOT}/${MARKER_NAME}"
LOCK_PATH="${LOCAL_STAGE_ROOT}.lock"

CONFIG="${CONFIG:-configs/train/stage2_earthnet_v2_direct_physical4.yaml}"
MAX_STEPS="${MAX_STEPS:-8800}"
BATCH_SIZE="${BATCH_SIZE:-64}"
NUM_WORKERS="${NUM_WORKERS:-8}"
PREFETCH_FACTOR="${PREFETCH_FACTOR:-1}"
PERSISTENT_WORKERS="${PERSISTENT_WORKERS:-1}"
LOG_INTERVAL="${LOG_INTERVAL:-50}"
GPUS="${GPUS:-8}"
PREFLIGHT="${PREFLIGHT:-1}"
PREFLIGHT_MAX_FILES="${PREFLIGHT_MAX_FILES:-16}"
PREFLIGHT_CHECK_MODEL="${PREFLIGHT_CHECK_MODEL:-1}"
REQUIRE_MANIFEST="${REQUIRE_MANIFEST:-1}"
RUN_TRAIN="${RUN_TRAIN:-1}"
MIN_LOCAL_FREE_GB="${MIN_LOCAL_FREE_GB:-140}"

CHECKPOINT_DIR="${CHECKPOINT_DIR:-${PROJECT_ROOT}/checkpoints/${RUN_ID}}"
LOG_DIR="${LOG_DIR:-${PROJECT_ROOT}/logs/${RUN_ID}}"
TRAIN_LOG="${TRAIN_LOG:-${LOG_DIR}/train_200epoch.log}"
LIFECYCLE_LOG="${LOG_DIR}/local_stage_lifecycle.log"
LIFECYCLE_RECORD="${LOG_DIR}/local_stage_run.env"
PREFLIGHT_OUTPUT="${PREFLIGHT_OUTPUT:-${LOG_DIR}/preflight_local_stage.json}"
STAGE2_RUNNER="${STAGE2_RUNNER:-${PROJECT_ROOT}/run_stage2_earthnet.sh}"
RSYNC_BIN="${RSYNC_BIN:-rsync}"

mkdir -p "${CHECKPOINT_DIR}" "${LOG_DIR}"

log() {
  printf '[stage2-local] %s %s\n' "$(date '+%F %T')" "$*" | tee -a "${LIFECYCLE_LOG}"
}

# Write a visible heartbeat before any source-side metadata scan.  On a shared
# NAS that scan can take noticeable time, and users should not have to infer
# whether the nohup launcher actually started.
log "launcher initialized: run_id=${RUN_ID}; source=${SOURCE_DATA_ROOT}; local_stage=${LOCAL_STAGE_ROOT}"

require_file() {
  local label="$1"
  local path="$2"
  [[ -s "${path}" ]] || die "${label} is missing or empty: ${path}"
}

for command in flock setsid realpath; do
  command -v "${command}" >/dev/null 2>&1 || die "required command is unavailable: ${command}"
done
if [[ "${RSYNC_BIN}" == */* ]]; then
  [[ -x "${RSYNC_BIN}" ]] || die "rsync executable is unavailable: ${RSYNC_BIN}"
else
  command -v "${RSYNC_BIN}" >/dev/null 2>&1 || die "rsync executable is unavailable: ${RSYNC_BIN}"
fi

SOURCE_DATASET_ROOT="$(resolve_earthnet_dataset_root "${SOURCE_DATA_ROOT}")"
log "validating shared source, frozen artifacts and local disk before staging"
[[ -d "${SOURCE_DATASET_ROOT}" ]] || die "shared EarthNet source not found: ${SOURCE_DATASET_ROOT}"
for split in train iid ood extreme seasonal; do
  [[ -d "${SOURCE_DATASET_ROOT}/${split}" ]] \
    || die "shared EarthNet source lacks required split directory: ${split}"
done

require_file "conditioning stats" "${CONDITIONING_STATS_PATH:-}"
require_file "train manifest" "${MANIFEST_PATH:-}"
require_file "validation manifest" "${VALIDATION_MANIFEST_PATH:-}"
require_file "Stage1.5 checkpoint" "${STAGE15_CHECKPOINT:-}"
[[ -f "${PROJECT_ROOT}/${CONFIG}" ]] || die "config not found under project: ${CONFIG}"
[[ -f "${STAGE2_RUNNER}" ]] || die "Stage2 runner not found: ${STAGE2_RUNNER}"

if [[ "${RUN_TRAIN}" != "1" ]]; then
  die "RUN_TRAIN must remain 1 in this lifecycle launcher; use run_stage2_earthnet.sh for preflight-only work"
fi

available_kb="$(df -Pk "$(dirname "${LOCAL_STAGE_ROOT}")" | awk 'NR == 2 {print $4}')"
required_kb=$((MIN_LOCAL_FREE_GB * 1024 * 1024))
[[ "${available_kb}" =~ ^[0-9]+$ ]] || die "could not determine free space for ${LOCAL_STAGE_ROOT}"
if (( available_kb < required_kb )); then
  die "local disk has only $((available_kb / 1024 / 1024))G free; need at least ${MIN_LOCAL_FREE_GB}G"
fi

exec 9>"${LOCK_PATH}"
flock -n 9 || die "another Stage2 local staging launcher already owns: ${LOCAL_STAGE_ROOT}"

STAGE_CREATED=0
STAGING_PID=""
TRAIN_PID=""

cleanup_staging() {
  if [[ "${STAGE_CREATED}" != "1" || ! -e "${LOCAL_STAGE_ROOT}" ]]; then
    return 0
  fi
  log "cleanup begins: ${LOCAL_STAGE_ROOT}"
  if bash "${PROJECT_ROOT}/scripts/cleanup_stage2_earthnet_local_staged.sh" \
    --stage-root "${LOCAL_STAGE_ROOT}" --force --lock-held; then
    log "cleanup SUCCESS: local EarthNet copy removed"
    return 0
  fi
  local cleanup_rc=$?
  log "cleanup FAILED (rc=${cleanup_rc}). Manual recovery command: bash ${PROJECT_ROOT}/scripts/cleanup_stage2_earthnet_local_staged.sh --stage-root ${LOCAL_STAGE_ROOT} --force"
  return "${cleanup_rc}"
}

terminate_process_group() {
  local pid="$1"
  local label="$2"
  [[ -n "${pid}" ]] || return 0
  kill -0 "${pid}" 2>/dev/null || return 0

  log "sending TERM to ${label} process group ${pid} before cleanup"
  kill -TERM -- "-${pid}" 2>/dev/null || kill -TERM "${pid}" 2>/dev/null || true
  local deadline=$((SECONDS + 90))
  while kill -0 "${pid}" 2>/dev/null && (( SECONDS < deadline )); do
    sleep 1
  done
  if kill -0 "${pid}" 2>/dev/null; then
    log "${label} process group did not exit in 90s; sending KILL"
    kill -KILL -- "-${pid}" 2>/dev/null || kill -KILL "${pid}" 2>/dev/null || true
  fi
  wait "${pid}" 2>/dev/null || true
}

terminate_staging_group() {
  local pid="${STAGING_PID:-}"
  terminate_process_group "${pid}" "rsync staging"
  STAGING_PID=""
}

terminate_training_group() {
  local pid="${TRAIN_PID:-}"
  terminate_process_group "${pid}" "Stage2 training"
  TRAIN_PID=""
}

on_signal() {
  local signal_name="$1"
  local exit_code="$2"
  log "received ${signal_name}; stopping training and cleaning local data"
  terminate_training_group
  terminate_staging_group
  exit "${exit_code}"
}

on_exit() {
  local run_rc=$?
  local cleanup_rc=0
  trap - EXIT
  terminate_training_group
  terminate_staging_group
  cleanup_staging || cleanup_rc=$?
  rm -f -- "${LOCK_PATH}"
  if (( run_rc == 0 && cleanup_rc != 0 )); then
    exit "${cleanup_rc}"
  fi
  exit "${run_rc}"
}

trap on_exit EXIT
trap 'on_signal INT 130' INT
trap 'on_signal TERM 143' TERM
trap 'on_signal HUP 129' HUP

if [[ -e "${LOCAL_STAGE_ROOT}" ]]; then
  if [[ -f "${MARKER_PATH}" ]] && grep -Fqx "${MARKER_SCHEMA}" "${MARKER_PATH}"; then
    log "removing a stale marked local staging copy before this run"
    bash "${PROJECT_ROOT}/scripts/cleanup_stage2_earthnet_local_staged.sh" \
      --stage-root "${LOCAL_STAGE_ROOT}" --force --lock-held
  else
    die "existing LOCAL_STAGE_ROOT is unmarked; refusing to overwrite it: ${LOCAL_STAGE_ROOT}"
  fi
fi

mkdir -p "${LOCAL_STAGE_ROOT}" "${LOCAL_DATA_ROOT}"
{
  printf '%s\n' "${MARKER_SCHEMA}"
  printf 'run_id=%s\n' "${RUN_ID}"
  printf 'created_at=%s\n' "$(date --iso-8601=seconds)"
  printf 'source_dataset_root=%s\n' "${SOURCE_DATASET_ROOT}"
  printf 'local_dataset_root=%s\n' "${LOCAL_DATASET_ROOT}"
  printf 'automatic_cleanup=on_exit_int_term_hup\n'
} > "${MARKER_PATH}"
STAGE_CREATED=1

log "counting shared-source NetCDF files before rsync; this one-time metadata scan may take a short while"
source_count="$(count_netcdf_files "${SOURCE_DATASET_ROOT}")"
[[ "${source_count}" =~ ^[0-9]+$ && "${source_count}" -gt 0 ]] \
  || die "shared EarthNet source contains no NetCDF files: ${SOURCE_DATASET_ROOT}"

log "local staging starts: source=${SOURCE_DATASET_ROOT}; target=${LOCAL_DATASET_ROOT}; source_nc_files=${source_count}"
log "rsync is resumable only while this launcher remains alive; any normal interruption removes the temporary copy by design"
setsid "${RSYNC_BIN}" -aH --partial --append-verify --info=progress2 -- \
  "${SOURCE_DATASET_ROOT}/" "${LOCAL_DATASET_ROOT}/" &
STAGING_PID="$!"
log "rsync staging process-group leader PID=${STAGING_PID}"
if wait "${STAGING_PID}"; then
  STAGING_PID=""
else
  staging_rc=$?
  STAGING_PID=""
  die "rsync staging failed with rc=${staging_rc}"
fi

local_count="$(count_netcdf_files "${LOCAL_DATASET_ROOT}")"
if [[ "${local_count}" != "${source_count}" ]]; then
  die "NetCDF file-count mismatch after staging: source=${source_count}, local=${local_count}"
fi
for split in train iid ood extreme seasonal; do
  [[ -d "${LOCAL_DATASET_ROOT}/${split}" ]] \
    || die "local staging is missing split directory after rsync: ${split}"
done

cat > "${LIFECYCLE_RECORD}" <<EOF
schema=obsworld-stage2-local-stage-run-v1
run_id=${RUN_ID}
source_dataset_root=${SOURCE_DATASET_ROOT}
local_stage_root=${LOCAL_STAGE_ROOT}
local_data_root=${LOCAL_DATA_ROOT}
local_dataset_root=${LOCAL_DATASET_ROOT}
source_nc_files=${source_count}
local_nc_files=${local_count}
automatic_cleanup=EXIT,INT,TERM,HUP
manual_recovery_cleanup=bash ${PROJECT_ROOT}/scripts/cleanup_stage2_earthnet_local_staged.sh --stage-root ${LOCAL_STAGE_ROOT} --force
EOF

log "local staging verified: ${local_count} NetCDF files; formal preflight/training will now use DATA_ROOT=${LOCAL_DATA_ROOT}"

export DATA_ROOT="${LOCAL_DATA_ROOT}"
export CONFIG MAX_STEPS BATCH_SIZE NUM_WORKERS PREFETCH_FACTOR PERSISTENT_WORKERS LOG_INTERVAL GPUS
export PREFLIGHT PREFLIGHT_MAX_FILES PREFLIGHT_CHECK_MODEL REQUIRE_MANIFEST RUN_TRAIN
export CHECKPOINT_DIR LOG_DIR PREFLIGHT_OUTPUT
export HDF5_USE_FILE_LOCKING="${HDF5_USE_FILE_LOCKING:-FALSE}"
export TORCH_NCCL_ASYNC_ERROR_HANDLING="${TORCH_NCCL_ASYNC_ERROR_HANDLING:-1}"

cd "${PROJECT_ROOT}"
log "training starts in a dedicated process group; training log=${TRAIN_LOG}"
setsid bash "${STAGE2_RUNNER}" > "${TRAIN_LOG}" 2>&1 &
TRAIN_PID="$!"
log "training process-group leader PID=${TRAIN_PID}"

if wait "${TRAIN_PID}"; then
  TRAIN_PID=""
  log "training finished successfully; automatic cleanup follows"
else
  train_rc=$?
  TRAIN_PID=""
  log "training exited with rc=${train_rc}; automatic cleanup follows"
  exit "${train_rc}"
fi
