#!/usr/bin/env bash
# Drain E1 configs with a real slot pool: as soon as one job finishes another
# starts, so a config sitting in its CPU scoring phase does not hold a GPU idle.
#
# The earlier version launched N jobs and waited for all N. Measured on the
# Contextformer rows that left GPUs 4-7 near 0% for most of each ~25 min round,
# because the official scorer is xarray/dask on CPU with no GPU path at all --
# the bottleneck is scoring and NetCDF I/O, not GPU compute. Overlapping the two
# phases is what helps here; adding more GPUs would not.
#
# Usage: run_e1_queue.sh <slots> <gpu-list-comma-sep> <configs-file>
# configs-file lines:  <model> <ckpt|NONE> <split>
set -u
cd "$(dirname "$0")"

SLOTS="$1"; IFS=',' read -ra GPUS <<< "$2"; CFG="$3"
mapfile -t JOBS < <(grep -vE '^\s*(#|$)' "$CFG")
mkdir -p logs_e1

i=0
for job in "${JOBS[@]}"; do
  while [ "$(jobs -rp | wc -l)" -ge "$SLOTS" ]; do sleep 5; done
  read -r m c s <<< "$job"
  g="${GPUS[$((i % ${#GPUS[@]}))]}"
  ( bash run_e1_one.sh "$m" "$c" "$s" "$g" >> "logs_e1/${m}__${s}.log" 2>&1 ) &
  echo "[launch $((i + 1))/${#JOBS[@]}] gpu=$g  $m  $s"
  i=$((i + 1))
done
wait
echo "ALL DONE $(date -u +%H:%M:%SZ)"
