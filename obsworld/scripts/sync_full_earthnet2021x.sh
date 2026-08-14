#!/usr/bin/env bash
# Robust full-dataset synchronizer for EarthNet2021x.
# Runs each split with retries until a --dry-run verification reports COMPLETE.
# Idempotent: safe to re-run after interruption.
set -uo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON_BIN:-/root/nas/users/luzheng/workspace/ssh/czj/WorldModel2026/.conda/envs/WorldModel/bin/python}"
ROOT="${DATA_ROOT:-/root/nas/users/luzheng/workspace/ssh/czj/TrainData/EarthNet2021/earthnet2021x}"
WORKERS="${WORKERS:-64}"
SPLITS="${SPLITS:-iid ood extreme seasonal train}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-8}"
REPORT_DIR="${REPORT_DIR:-logs/earthnet2021x_full_sync}"

mkdir -p "${REPORT_DIR}"

echo "############################################################"
echo "# EarthNet2021x FULL sync"
echo "# root=${ROOT}"
echo "# workers=${WORKERS}  splits='${SPLITS}'  max_attempts=${MAX_ATTEMPTS}"
echo "# started: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "############################################################"

overall_ok=1
for split in ${SPLITS}; do
  echo
  echo "==================== SPLIT: ${split} ===================="
  attempt=1
  split_done=0
  while [ "${attempt}" -le "${MAX_ATTEMPTS}" ]; do
    echo "--- ${split}: sync attempt ${attempt}/${MAX_ATTEMPTS} ($(date -u '+%H:%M:%SZ')) ---"
    "${PY}" scripts/sync_earthnet2021x.py \
      --root "${ROOT}" \
      --split "${split}" \
      --workers "${WORKERS}" \
      --report "${REPORT_DIR}/${split}_sync_attempt${attempt}.json"
    rc=$?
    echo "--- ${split}: sync attempt ${attempt} exit=${rc} ---"

    # Verify with a dry-run: exit 0 means nothing left to download.
    "${PY}" scripts/sync_earthnet2021x.py \
      --root "${ROOT}" \
      --split "${split}" \
      --dry-run \
      --report "${REPORT_DIR}/${split}_verify.json"
    vrc=$?
    if [ "${vrc}" -eq 0 ]; then
      echo "=== ${split}: COMPLETE (verified, attempt ${attempt}) ==="
      split_done=1
      break
    fi
    echo "=== ${split}: still incomplete (verify rc=${vrc}); retrying ==="
    attempt=$((attempt + 1))
    sleep 5
  done

  if [ "${split_done}" -ne 1 ]; then
    echo "!!! ${split}: FAILED to complete after ${MAX_ATTEMPTS} attempts !!!"
    overall_ok=0
  fi
done

echo
echo "############################################################"
if [ "${overall_ok}" -eq 1 ]; then
  echo "# ALL SPLITS COMPLETE"
else
  echo "# FINISHED WITH SOME INCOMPLETE SPLITS (see reports above)"
fi
echo "# finished: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "############################################################"
