#!/bin/bash
WD=/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_narrative_20260912T112243Z
cd "$WD" || exit 1
echo "=== referenced paths resolve (from narrative dir) ==="
miss=0
grep -o '](\(figures\|gallery\)/[^)]*)' OVERVIEW.md | sed 's/](//; s/)$//' | sort -u > /tmp/imgpaths.txt
while read -r p; do
  if [ -f "$p" ]; then echo "OK   $p"; else echo "MISS $p"; miss=1; fi
done < /tmp/imgpaths.txt

grep -o '`\(tables\|metrics\|manifests\|metrics_derived\|references\)/[A-Za-z0-9_./-]*`' OVERVIEW.md \
  | tr -d '`' | sort -u > /tmp/refpaths.txt
while read -r p; do
  if [ -e "$p" ]; then echo "OK   $p"; else echo "MISS $p"; miss=1; fi
done < /tmp/refpaths.txt

echo "=== absolute paths referenced ==="
for p in /data/zs/multiseed_standard_eval_20260910T074115Z/E1_table_delivery/E1_per_seed_values.csv \
         /data/zs/multiseed_standard_eval_20260910T074115Z/E1_table_delivery/E1_summary_values.csv \
         /data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_closure_fix_20260911T081702Z \
         /data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_showcase_20260912T062326Z \
         /data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_narrative_20260912T112243Z/OVERVIEW.md; do
  [ -e "$p" ] && echo "OK   $p" || { echo "MISS $p"; miss=1; }
done

echo "=== write-bound check: every realpath under /data/zs ==="
out=0
for p in "$WD"/*; do
  rp=$(realpath "$p")
  case "$rp" in
    /data/zs/*) : ;;
    *) echo "OUT  $p -> $rp"; out=1 ;;
  esac
done
[ "$out" -eq 0 ] && echo "OK   all entries resolve inside /data/zs"

echo "=== result ==="
if [ "$miss" -eq 0 ] && [ "$out" -eq 0 ]; then echo "ACCEPTANCE: ALL REFERENCES RESOLVE"; else echo "ACCEPTANCE: PROBLEMS FOUND"; fi
