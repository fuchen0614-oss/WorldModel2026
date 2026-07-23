#!/usr/bin/env bash
# ObsWorld Stage2 EarthNet: safe shared-NAS -> local-/tmp staging launcher.
#
# Only the copy below LOCAL_STAGE_ROOT is temporary.  Checkpoints, TensorBoard
# events, provenance and logs remain in the shared project directory.  The
# default ``LOCAL_STAGE_CLEANUP=auto`` removes the local copy after success,
# failure, or a normal interruption.  ``manual`` is an explicit debugging
# cache mode: a fully verified copy is retained and may be reused by the next
# launcher invocation with the same source/manifests.

set -Eeuo pipefail

MARKER_NAME=".obsworld_stage2_local_stage_v1"
MARKER_SCHEMA="schema=obsworld-stage2-local-stage-v1"
STAGE_METADATA_NAME=".obsworld_stage2_local_stage_metadata.env"
STAGE_METADATA_SCHEMA="schema=obsworld-stage2-local-stage-metadata-v1"
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

count_file_list_entries() {
  "${PYTHON_BIN}" - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).read_bytes().count(b"\0"))
PY
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
STAGE_METADATA_PATH="${LOCAL_STAGE_ROOT}/${STAGE_METADATA_NAME}"
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
MIN_LOCAL_FREE_GB="${MIN_LOCAL_FREE_GB:-250}"
LOCAL_STAGE_CLEANUP="${LOCAL_STAGE_CLEANUP:-auto}"
LOCAL_STAGE_DATA_SCOPE="${LOCAL_STAGE_DATA_SCOPE:-all}"
REQUIRE_EMPTY_GPUS="${REQUIRE_EMPTY_GPUS:-0}"
PYTHON_BIN="${PYTHON_BIN:-python}"
# Exactly one Stage2 initializer is required downstream: a frozen Stage1.5 state
# bridge (fresh A') OR an A' weights-only warm-start checkpoint (rescue A').
STAGE15_CHECKPOINT="${STAGE15_CHECKPOINT:-}"
INIT_FROM_CHECKPOINT="${INIT_FROM_CHECKPOINT:-}"

CHECKPOINT_DIR="${CHECKPOINT_DIR:-${PROJECT_ROOT}/checkpoints/${RUN_ID}}"
LOG_DIR="${LOG_DIR:-${PROJECT_ROOT}/logs/${RUN_ID}}"
TRAIN_LOG="${TRAIN_LOG:-${LOG_DIR}/train_200epoch.log}"
LIFECYCLE_LOG="${LOG_DIR}/local_stage_lifecycle.log"
LIFECYCLE_RECORD="${LOG_DIR}/local_stage_run.env"
PREFLIGHT_OUTPUT="${PREFLIGHT_OUTPUT:-${LOG_DIR}/preflight_local_stage.json}"
STAGE2_RUNNER="${STAGE2_RUNNER:-${PROJECT_ROOT}/run_stage2_earthnet.sh}"
RSYNC_BIN="${RSYNC_BIN:-rsync}"
STAGE_FILE_LIST="${LOG_DIR}/local_stage_files.nul"
STAGE_PLAN_SUMMARY="${LOG_DIR}/local_stage_plan.json"

mkdir -p "${CHECKPOINT_DIR}" "${LOG_DIR}"

log() {
  printf '[stage2-local] %s %s\n' "$(date '+%F %T')" "$*" | tee -a "${LIFECYCLE_LOG}"
}

# Write a visible heartbeat before any source-side metadata scan.  On a shared
# NAS that scan can take noticeable time, and users should not have to infer
# whether the nohup launcher actually started.
log "launcher initialized: run_id=${RUN_ID}; source=${SOURCE_DATA_ROOT}; local_stage=${LOCAL_STAGE_ROOT}"
log "local stage policy: cleanup=${LOCAL_STAGE_CLEANUP}; data_scope=${LOCAL_STAGE_DATA_SCOPE}"
log "GPU availability policy: require_empty_gpus=${REQUIRE_EMPTY_GPUS}"

require_file() {
  local label="$1"
  local path="$2"
  [[ -s "${path}" ]] || die "${label} is missing or empty: ${path}"
}

case "${LOCAL_STAGE_CLEANUP}" in
  auto|manual)
    ;;
  *)
    die "LOCAL_STAGE_CLEANUP must be auto or manual, got: ${LOCAL_STAGE_CLEANUP}"
    ;;
esac
case "${LOCAL_STAGE_DATA_SCOPE}" in
  all|train_val)
    ;;
  *)
    die "LOCAL_STAGE_DATA_SCOPE must be all or train_val, got: ${LOCAL_STAGE_DATA_SCOPE}"
    ;;
esac
case "${REQUIRE_EMPTY_GPUS}" in
  0|1)
    ;;
  *)
    die "REQUIRE_EMPTY_GPUS must be 0 or 1, got: ${REQUIRE_EMPTY_GPUS}"
    ;;
esac

for command in flock setsid realpath sha256sum sort "${PYTHON_BIN}"; do
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
if [[ "${LOCAL_STAGE_DATA_SCOPE}" == "all" ]]; then
  for split in train iid ood extreme seasonal; do
    [[ -d "${SOURCE_DATASET_ROOT}/${split}" ]] \
      || die "shared EarthNet source lacks required split directory: ${split}"
  done
fi

require_file "conditioning stats" "${CONDITIONING_STATS_PATH:-}"
require_file "train manifest" "${MANIFEST_PATH:-}"
require_file "validation manifest" "${VALIDATION_MANIFEST_PATH:-}"
# Exactly one Stage2 initializer must be provided, and only one. The rescue
# config (plan_a_prime_from_s1a_stage2.yaml, require_stage15_checkpoint=false)
# supplies INIT_FROM_CHECKPOINT and must NOT be forced to name a Stage1.5
# checkpoint; the fresh config supplies STAGE15_CHECKPOINT.
if [[ -n "${STAGE15_CHECKPOINT}" && -n "${INIT_FROM_CHECKPOINT}" ]]; then
  die "STAGE15_CHECKPOINT and INIT_FROM_CHECKPOINT are mutually exclusive; provide exactly one"
elif [[ -n "${INIT_FROM_CHECKPOINT}" ]]; then
  require_file "A' warm-start checkpoint (INIT_FROM_CHECKPOINT)" "${INIT_FROM_CHECKPOINT}"
elif [[ -n "${STAGE15_CHECKPOINT}" ]]; then
  require_file "Stage1.5 checkpoint (STAGE15_CHECKPOINT)" "${STAGE15_CHECKPOINT}"
else
  die "no Stage2 initializer: set STAGE15_CHECKPOINT (fresh) or INIT_FROM_CHECKPOINT (A' warm-start)"
fi
[[ -f "${PROJECT_ROOT}/${CONFIG}" ]] || die "config not found under project: ${CONFIG}"
[[ -f "${STAGE2_RUNNER}" ]] || die "Stage2 runner not found: ${STAGE2_RUNNER}"

if [[ "${RUN_TRAIN}" != "1" ]]; then
  die "RUN_TRAIN must remain 1 in this lifecycle launcher; use run_stage2_earthnet.sh for preflight-only work"
fi

exec 9>"${LOCK_PATH}"
flock -n 9 || die "another Stage2 local staging launcher already owns: ${LOCAL_STAGE_ROOT}"

STAGE_CREATED=0
STAGE_REUSED=0
STAGING_PID=""
TRAIN_PID=""
PLANNED_NC_FILES=""
STAGE_FILE_LIST_SHA256=""
TRAIN_MANIFEST_SHA256=""
VALIDATION_MANIFEST_SHA256=""

ensure_local_free_space() {
  local available_kb required_kb
  available_kb="$(df -Pk "$(dirname "${LOCAL_STAGE_ROOT}")" | awk 'NR == 2 {print $4}')"
  required_kb=$((MIN_LOCAL_FREE_GB * 1024 * 1024))
  [[ "${available_kb}" =~ ^[0-9]+$ ]] || die "could not determine free space for ${LOCAL_STAGE_ROOT}"
  if (( available_kb < required_kb )); then
    die "local disk has only $((available_kb / 1024 / 1024))G free; need at least ${MIN_LOCAL_FREE_GB}G"
  fi
}

assert_gpus_are_empty() {
  [[ "${REQUIRE_EMPTY_GPUS}" == "1" ]] || return 0
  command -v nvidia-smi >/dev/null 2>&1 || die "REQUIRE_EMPTY_GPUS=1 requires nvidia-smi"
  local active_processes
  active_processes="$(nvidia-smi --query-compute-apps=pid,used_memory \
    --format=csv,noheader,nounits 2>/dev/null || true)"
  if [[ -n "${active_processes//[[:space:]]/}" ]]; then
    echo "${active_processes}" >&2
    die "GPU compute processes already exist; refusing to start. Wait for clean GPUs or set REQUIRE_EMPTY_GPUS=0 explicitly"
  fi
  log "GPU availability check passed: no compute processes detected"
}

build_stage_file_plan() {
  rm -f -- "${STAGE_FILE_LIST}" "${STAGE_PLAN_SUMMARY}"
  if [[ "${LOCAL_STAGE_DATA_SCOPE}" == "all" ]]; then
    log "building complete NetCDF staging list from the shared source"
    find "${SOURCE_DATASET_ROOT}" -type f -name '*.nc' -printf '%P\0' \
      | LC_ALL=C sort -z -u > "${STAGE_FILE_LIST}"
  else
    log "building train+val manifest-only staging list"
    "${PYTHON_BIN}" "${PROJECT_ROOT}/scripts/build_stage2_local_stage_file_list.py" \
      --dataset-root "${SOURCE_DATASET_ROOT}" \
      --train-manifest "${MANIFEST_PATH}" \
      --validation-manifest "${VALIDATION_MANIFEST_PATH}" \
      --output "${STAGE_FILE_LIST}" \
      --summary "${STAGE_PLAN_SUMMARY}"
  fi
  PLANNED_NC_FILES="$(count_file_list_entries "${STAGE_FILE_LIST}")"
  [[ "${PLANNED_NC_FILES}" =~ ^[0-9]+$ && "${PLANNED_NC_FILES}" -gt 0 ]] \
    || die "local staging plan contains no NetCDF files"
  STAGE_FILE_LIST_SHA256="$(sha256sum "${STAGE_FILE_LIST}" | awk '{print $1}')"
  TRAIN_MANIFEST_SHA256="$(sha256sum "${MANIFEST_PATH}" | awk '{print $1}')"
  VALIDATION_MANIFEST_SHA256="$(sha256sum "${VALIDATION_MANIFEST_PATH}" | awk '{print $1}')"
  log "staging plan ready: scope=${LOCAL_STAGE_DATA_SCOPE}; planned_nc_files=${PLANNED_NC_FILES}; file_list_sha256=${STAGE_FILE_LIST_SHA256}"
}

verify_local_stage_files() {
  local local_count relative
  [[ -d "${LOCAL_DATASET_ROOT}" ]] || return 1
  local_count="$(count_netcdf_files "${LOCAL_DATASET_ROOT}")"
  if [[ "${local_count}" != "${PLANNED_NC_FILES}" ]]; then
    log "local stage file-count mismatch: expected=${PLANNED_NC_FILES}; actual=${local_count}"
    return 1
  fi
  while IFS= read -r -d '' relative; do
    if [[ ! -f "${LOCAL_DATASET_ROOT}/${relative}" ]]; then
      log "local stage is missing planned NetCDF file: ${relative}"
      return 1
    fi
  done < "${STAGE_FILE_LIST}"
  return 0
}

write_stage_metadata() {
  {
    printf '%s\n' "${STAGE_METADATA_SCHEMA}"
    printf 'source_dataset_root=%s\n' "${SOURCE_DATASET_ROOT}"
    printf 'local_stage_data_scope=%s\n' "${LOCAL_STAGE_DATA_SCOPE}"
    printf 'planned_netcdf_files=%s\n' "${PLANNED_NC_FILES}"
    printf 'file_list_sha256=%s\n' "${STAGE_FILE_LIST_SHA256}"
    printf 'train_manifest_sha256=%s\n' "${TRAIN_MANIFEST_SHA256}"
    printf 'validation_manifest_sha256=%s\n' "${VALIDATION_MANIFEST_SHA256}"
  } > "${STAGE_METADATA_PATH}"
}

stage_metadata_matches_plan() {
  [[ -f "${MARKER_PATH}" && -f "${STAGE_METADATA_PATH}" ]] || return 1
  grep -Fqx "${MARKER_SCHEMA}" "${MARKER_PATH}" \
    && grep -Fqx "${STAGE_METADATA_SCHEMA}" "${STAGE_METADATA_PATH}" \
    && grep -Fqx "source_dataset_root=${SOURCE_DATASET_ROOT}" "${STAGE_METADATA_PATH}" \
    && grep -Fqx "local_stage_data_scope=${LOCAL_STAGE_DATA_SCOPE}" "${STAGE_METADATA_PATH}" \
    && grep -Fqx "planned_netcdf_files=${PLANNED_NC_FILES}" "${STAGE_METADATA_PATH}" \
    && grep -Fqx "file_list_sha256=${STAGE_FILE_LIST_SHA256}" "${STAGE_METADATA_PATH}" \
    && grep -Fqx "train_manifest_sha256=${TRAIN_MANIFEST_SHA256}" "${STAGE_METADATA_PATH}" \
    && grep -Fqx "validation_manifest_sha256=${VALIDATION_MANIFEST_SHA256}" "${STAGE_METADATA_PATH}"
}

cleanup_staging() {
  if [[ "${STAGE_CREATED}" != "1" || ! -e "${LOCAL_STAGE_ROOT}" ]]; then
    return 0
  fi
  if [[ "${LOCAL_STAGE_CLEANUP}" == "manual" ]]; then
    log "LOCAL_STAGE_CLEANUP=manual; retaining local staging data: ${LOCAL_STAGE_ROOT}"
    log "manual cleanup command: bash ${PROJECT_ROOT}/scripts/cleanup_stage2_earthnet_local_staged.sh --stage-root ${LOCAL_STAGE_ROOT} --force"
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
  if [[ "${LOCAL_STAGE_CLEANUP}" == "manual" ]]; then
    log "received ${signal_name}; stopping processes and retaining local data by explicit manual policy"
  else
    log "received ${signal_name}; stopping training and cleaning local data"
  fi
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

build_stage_file_plan
assert_gpus_are_empty

if [[ -e "${LOCAL_STAGE_ROOT}" ]]; then
  if [[ ! -f "${MARKER_PATH}" ]] || ! grep -Fqx "${MARKER_SCHEMA}" "${MARKER_PATH}"; then
    die "existing LOCAL_STAGE_ROOT is unmarked; refusing to overwrite it: ${LOCAL_STAGE_ROOT}"
  fi
  if stage_metadata_matches_plan && verify_local_stage_files; then
    STAGE_CREATED=1
    STAGE_REUSED=1
    log "reusing verified local staging copy: ${LOCAL_STAGE_ROOT}; planned_nc_files=${PLANNED_NC_FILES}"
  else
    log "existing local staging copy is not reusable for this verified plan; removing it before staging"
    bash "${PROJECT_ROOT}/scripts/cleanup_stage2_earthnet_local_staged.sh" \
      --stage-root "${LOCAL_STAGE_ROOT}" --force --lock-held
  fi
fi

if [[ "${STAGE_REUSED}" != "1" ]]; then
  ensure_local_free_space
  mkdir -p "${LOCAL_STAGE_ROOT}" "${LOCAL_DATA_ROOT}"
  {
    printf '%s\n' "${MARKER_SCHEMA}"
    printf 'run_id=%s\n' "${RUN_ID}"
    printf 'created_at=%s\n' "$(date --iso-8601=seconds)"
    printf 'source_dataset_root=%s\n' "${SOURCE_DATASET_ROOT}"
    printf 'local_dataset_root=%s\n' "${LOCAL_DATASET_ROOT}"
    printf 'local_stage_cleanup=%s\n' "${LOCAL_STAGE_CLEANUP}"
    printf 'local_stage_data_scope=%s\n' "${LOCAL_STAGE_DATA_SCOPE}"
  } > "${MARKER_PATH}"
  STAGE_CREATED=1

  log "local staging starts: source=${SOURCE_DATASET_ROOT}; target=${LOCAL_DATASET_ROOT}; planned_nc_files=${PLANNED_NC_FILES}"
  if [[ "${LOCAL_STAGE_CLEANUP}" == "manual" ]]; then
    log "manual cache mode: a fully verified copy remains after this run for an explicit retry"
  else
    log "auto cleanup mode: any normal interruption removes the temporary copy by design"
  fi
  setsid "${RSYNC_BIN}" -aH --partial --append-verify --info=progress2 --from0 \
    --files-from="${STAGE_FILE_LIST}" -- \
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

  verify_local_stage_files \
    || die "local staging verification failed for ${PLANNED_NC_FILES} planned NetCDF files"
  write_stage_metadata
fi

cat > "${LIFECYCLE_RECORD}" <<EOF
schema=obsworld-stage2-local-stage-run-v1
run_id=${RUN_ID}
source_dataset_root=${SOURCE_DATASET_ROOT}
local_stage_root=${LOCAL_STAGE_ROOT}
local_data_root=${LOCAL_DATA_ROOT}
local_dataset_root=${LOCAL_DATASET_ROOT}
local_stage_cleanup=${LOCAL_STAGE_CLEANUP}
local_stage_data_scope=${LOCAL_STAGE_DATA_SCOPE}
stage_reused=${STAGE_REUSED}
planned_netcdf_files=${PLANNED_NC_FILES}
file_list_sha256=${STAGE_FILE_LIST_SHA256}
automatic_cleanup=$([[ "${LOCAL_STAGE_CLEANUP}" == "auto" ]] && printf 'EXIT,INT,TERM,HUP' || printf 'disabled_manual_mode')
manual_recovery_cleanup=bash ${PROJECT_ROOT}/scripts/cleanup_stage2_earthnet_local_staged.sh --stage-root ${LOCAL_STAGE_ROOT} --force
EOF

log "local staging verified: ${PLANNED_NC_FILES} planned NetCDF files; formal preflight/training will now use DATA_ROOT=${LOCAL_DATA_ROOT}"

export DATA_ROOT="${LOCAL_DATA_ROOT}"
export CONFIG MAX_STEPS BATCH_SIZE NUM_WORKERS PREFETCH_FACTOR PERSISTENT_WORKERS LOG_INTERVAL GPUS
export PREFLIGHT PREFLIGHT_MAX_FILES PREFLIGHT_CHECK_MODEL REQUIRE_MANIFEST RUN_TRAIN
export CHECKPOINT_DIR LOG_DIR PREFLIGHT_OUTPUT
# Forward the initializer + frozen-artifact paths to the Stage2 runner so the
# choice (fresh Stage1.5 vs A' warm-start) is explicit and independent of shell
# export inheritance. Empty vars stay empty and are ignored by the runner.
export STAGE15_CHECKPOINT INIT_FROM_CHECKPOINT
export CONDITIONING_STATS_PATH MANIFEST_PATH VALIDATION_MANIFEST_PATH
export HDF5_USE_FILE_LOCKING="${HDF5_USE_FILE_LOCKING:-FALSE}"
export TORCH_NCCL_ASYNC_ERROR_HANDLING="${TORCH_NCCL_ASYNC_ERROR_HANDLING:-1}"

cd "${PROJECT_ROOT}"
assert_gpus_are_empty
log "training starts in a dedicated process group; training log=${TRAIN_LOG}"
setsid bash "${STAGE2_RUNNER}" > "${TRAIN_LOG}" 2>&1 &
TRAIN_PID="$!"
log "training process-group leader PID=${TRAIN_PID}"

if wait "${TRAIN_PID}"; then
  TRAIN_PID=""
  if [[ "${LOCAL_STAGE_CLEANUP}" == "manual" ]]; then
    log "training finished successfully; local data retained by explicit manual policy"
  else
    log "training finished successfully; automatic cleanup follows"
  fi
else
  train_rc=$?
  TRAIN_PID=""
  if [[ "${LOCAL_STAGE_CLEANUP}" == "manual" ]]; then
    log "training exited with rc=${train_rc}; local data retained by explicit manual policy"
  else
    log "training exited with rc=${train_rc}; automatic cleanup follows"
  fi
  exit "${train_rc}"
fi
