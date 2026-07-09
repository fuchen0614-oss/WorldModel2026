#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

DATA_ROOT="${DATA_ROOT:-/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021}"
WORKERS="${WORKERS:-8}"
MANIFEST_WORKERS="${MANIFEST_WORKERS:-4}"
REPORT_DIR="${REPORT_DIR:-logs/earthnet2021x_sync}"
SPLITS="${SPLITS:-iid ood extreme seasonal}"
PYTHON_BIN="${PYTHON_BIN:-python}"

mkdir -p "${REPORT_DIR}"

echo "=== EarthNet2021x remaining split synchronization ==="
echo "DATA_ROOT=${DATA_ROOT}"
echo "SPLITS=${SPLITS}"
echo "WORKERS=${WORKERS}"
echo "MANIFEST_WORKERS=${MANIFEST_WORKERS}"
echo "REPORT_DIR=${REPORT_DIR}"

for split in ${SPLITS}; do
  echo
  echo "=== Syncing ${split} ==="
  "${PYTHON_BIN}" scripts/sync_earthnet2021x.py \
    --root "${DATA_ROOT}" \
    --split "${split}" \
    --workers "${WORKERS}" \
    --manifest-workers "${MANIFEST_WORKERS}" \
    --report "${REPORT_DIR}/${split}_sync.json"

  echo "=== Verifying ${split} ==="
  "${PYTHON_BIN}" scripts/sync_earthnet2021x.py \
    --root "${DATA_ROOT}" \
    --split "${split}" \
    --dry-run \
    --report "${REPORT_DIR}/${split}_final_check.json"
done

echo
echo "=== All requested EarthNet2021x splits are complete ==="
