#!/usr/bin/env bash
# Reap orphaned E1 workers whose parent driver was stopped. Kept in a file so the
# match patterns do not appear in the invoking shell's own command line -- doing
# this inline kept killing the caller.
set -u
n=0
for pat in export_emp_baseline_predictions export_contextformer_predictions \
           eval_greenearthnet_official run_e1_one; do
  for p in $(ps -eo pid,args --no-headers | grep -F "$pat" | grep -v grep | awk '{print $1}'); do
    [ "$p" = "$$" ] && continue
    kill "$p" 2>/dev/null && n=$((n + 1))
  done
done
sleep 4
for pat in export_emp_baseline_predictions export_contextformer_predictions \
           eval_greenearthnet_official run_e1_one; do
  for p in $(ps -eo pid,args --no-headers | grep -F "$pat" | grep -v grep | awk '{print $1}'); do
    [ "$p" = "$$" ] && continue
    kill -9 "$p" 2>/dev/null
  done
done
echo "reaped $n"
