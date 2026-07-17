#!/usr/bin/env bash
# Safely remove an ObsWorld Stage2 EarthNet local staging copy.
#
# This script deliberately accepts only a marked directory below /tmp.  It
# never removes the shared EarthNet source under /csy-mix02.  The Stage2 local
# launcher calls it automatically in LOCAL_STAGE_CLEANUP=auto mode; this is
# also the explicit cleanup command for a LOCAL_STAGE_CLEANUP=manual cache or
# after an untrappable event such as `kill -9` or a node restart.

set -euo pipefail

MARKER_NAME=".obsworld_stage2_local_stage_v1"
MARKER_SCHEMA="schema=obsworld-stage2-local-stage-v1"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/cleanup_stage2_earthnet_local_staged.sh \
    --stage-root /tmp/<user>_obsworld_stage2_earthnet2021x --force

Only a directory below /tmp that contains the ObsWorld Stage2 marker can be
removed.  Without --force, the script asks for an explicit yes/no confirmation.
EOF
}

die() {
  echo "[stage2-local-cleanup] ERROR: $*" >&2
  exit 2
}

canonical_path() {
  realpath -m -- "$1"
}

STAGE_ROOT="${LOCAL_STAGE_ROOT:-}"
FORCE=0
LOCK_HELD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stage-root)
      [[ $# -ge 2 ]] || die "--stage-root requires a path"
      STAGE_ROOT="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    # Internal use by the launcher, which already holds the per-stage flock.
    --lock-held)
      LOCK_HELD=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "${STAGE_ROOT}" ]] || die "provide --stage-root (or LOCAL_STAGE_ROOT)"
STAGE_ROOT="$(canonical_path "${STAGE_ROOT}")"

case "${STAGE_ROOT}" in
  /tmp/*)
    ;;
  *)
    die "refusing to delete a path outside /tmp: ${STAGE_ROOT}"
    ;;
esac

[[ "${STAGE_ROOT}" != "/tmp" ]] || die "refusing to delete /tmp itself"

MARKER_PATH="${STAGE_ROOT}/${MARKER_NAME}"
LOCK_PATH="${STAGE_ROOT}.lock"

if [[ ! -e "${STAGE_ROOT}" ]]; then
  echo "[stage2-local-cleanup] no staging directory remains: ${STAGE_ROOT}"
  exit 0
fi
[[ -d "${STAGE_ROOT}" ]] || die "stage root is not a directory: ${STAGE_ROOT}"
[[ -f "${MARKER_PATH}" ]] || die "marker missing; refusing to delete: ${STAGE_ROOT}"
grep -Fqx "${MARKER_SCHEMA}" "${MARKER_PATH}" \
  || die "marker schema mismatch; refusing to delete: ${STAGE_ROOT}"

if [[ "${LOCK_HELD}" == "0" ]]; then
  command -v flock >/dev/null 2>&1 || die "flock is required for safe cleanup"
  exec 9>"${LOCK_PATH}"
  flock -n 9 || die "a Stage2 local staging launcher is still active; do not delete its data"
fi

SIZE="$(du -sh "${STAGE_ROOT}" 2>/dev/null | awk '{print $1}' || true)"
echo "============================================================"
echo "ObsWorld Stage2 EarthNet local staging cleanup"
echo "Will delete only temporary local data: ${STAGE_ROOT} (${SIZE:-unknown})"
echo "Will NOT delete the shared source dataset."
echo "============================================================"

if [[ "${FORCE}" == "0" ]]; then
  read -r -p "Type yes to delete this marked temporary copy: " answer
  [[ "${answer}" == "yes" ]] || {
    echo "[stage2-local-cleanup] cancelled; nothing was deleted"
    exit 0
  }
fi

# --one-file-system adds one more guard if an unexpected mount appears below
# the temporary staging directory.
rm -rf --one-file-system -- "${STAGE_ROOT}"
[[ ! -e "${STAGE_ROOT}" ]] || die "removal did not finish: ${STAGE_ROOT}"

if [[ "${LOCK_HELD}" == "0" ]]; then
  rm -f -- "${LOCK_PATH}"
fi

echo "[stage2-local-cleanup] SUCCESS: local temporary data was removed"
