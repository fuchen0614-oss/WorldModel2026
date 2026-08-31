#!/usr/bin/env bash
# Drain a list of E1 configs across the free GPUs, one job per GPU at a time.
# Usage: run_e1_queue.sh <gpu-list-comma-sep> <configs-file>
# configs-file lines:  <model> <ckpt|NONE> <split>
set -u
cd "$(dirname "$0")"
IFS=',' read -ra GPUS <<< "$1"; CFG="$2"
mapfile -t JOBS < <(grep -vE '^\s*(#|$)' "$CFG")
i=0
while [ $i -lt ${#JOBS[@]} ]; do
  for g in "${GPUS[@]}"; do
    [ $i -ge ${#JOBS[@]} ] && break
    read -r m c s <<< "${JOBS[$i]}"
    ( bash run_e1_one.sh "$m" "$c" "$s" "$g" >> "logs_e1/${m}__${s}.log" 2>&1 ) &
    echo "[launch] gpu=$g  $m  $s"
    i=$((i+1))
  done
  wait
done
echo "ALL DONE $(date -u +%H:%M:%SZ)"
