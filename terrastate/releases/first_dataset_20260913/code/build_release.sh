#!/usr/bin/env bash
# Build terrastate/releases/first_dataset_20260913/ by COPYING curated materials.
#
# HARD RULES (per the user's requirement):
#   * copy only -- `cp -a`, never `mv`, never delete; every source stays untouched
#   * no .pt/.pth/.ckpt/.safetensors in the payload (the repo LFS filter would break on them)
#   * nothing outside the new release directory is staged, committed or modified
set -uo pipefail
GITROOT=/data/zs/WorldModel2026
R=/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z
FF=$R/first_dataset_figures_final_20260913T052645Z
ND=$R/first_dataset_narrative_dual_20260913T082412Z
CF=$R/first_dataset_closure_fix_20260911T081702Z
SH=$R/first_dataset_showcase_20260912T062326Z
OUT=$GITROOT/terrastate/releases/first_dataset_20260913

echo "=== source presence check (all must exist before we start) ==="
for d in "$FF" "$ND" "$CF" "$SH"; do
  [ -d "$d" ] && echo "  OK   $d" || { echo "  MISSING $d"; exit 1; }
done
[ -e "$OUT" ] && { echo "  REFUSING: $OUT already exists"; exit 1; } || echo "  release dir is new: $OUT"

echo
echo "=== recording source fingerprints BEFORE copying ==="
for d in "$FF" "$ND" "$CF"; do
  printf '  %-70s files=%-6s bytes=%s\n' "$(basename "$d")" \
    "$(find "$d" -type f | wc -l)" "$(du -sb "$d" | cut -f1)"
done

mkdir -p "$OUT"/{narrative,figures,tables,metrics,reports,reproduction}

echo
echo "=== 1) narrative (copy whole package) ==="
cp -a "$ND"/. "$OUT/narrative"/
find "$OUT/narrative" -type f | wc -l

echo
echo "=== 2) figures: per-figure selected + docs + code + text data ==="
cp -a "$FF/OVERVIEW.md" "$FF/README.md" "$OUT/figures/" 2>/dev/null
for sub in reports references; do cp -a "$FF/$sub" "$OUT/figures/" 2>/dev/null; done
for d in "$FF"/图*; do
  name=$(basename "$d")
  dst="$OUT/figures/$name"
  mkdir -p "$dst"
  for item in selected code; do [ -d "$d/$item" ] && cp -a "$d/$item" "$dst/"; done
  # per-figure docs
  find "$d" -maxdepth 1 -type f \( -name '*.md' -o -name '*.csv' -o -name '*.json' \) -exec cp -a {} "$dst/" \;
  # text data only: skip _arrays/, candidates/, alternatives/, contact_sheets/, baseline_predictions/
  if [ -d "$d/data" ]; then
    mkdir -p "$dst/data"
    find "$d/data" -maxdepth 1 -type f -exec cp -a {} "$dst/data/" \;
    for sub in $(find "$d/data" -maxdepth 1 -type d ! -path "$d/data" | sort); do
      b=$(basename "$sub")
      case "$b" in _arrays|baseline_predictions) echo "    [skip arrays] $name/data/$b";; 
        *) cp -a "$sub" "$dst/data/";; esac
    done
  fi
  printf '  %-28s %s files  %s\n' "$name" "$(find "$dst" -type f | wc -l)" "$(du -sh "$dst" | cut -f1)"
done

echo
echo "=== 3) tables (16 files from the frozen corrected package) ==="
cp -a "$CF/tables/." "$OUT/tables"/ && ls "$OUT/tables" | wc -l

echo
echo "=== 4) metrics (key aggregates) ==="
cp -a "$CF/metrics"/*.json "$OUT/metrics"/ 2>/dev/null
cp -a "$CF/metrics/T1_per_seed_values.csv" "$OUT/metrics"/ 2>/dev/null
cp -a "$CF/metrics/PREDICTION_CANDIDATE_METRICS.csv" "$OUT/metrics"/ 2>/dev/null
cp -a "$CF/metrics/WEATHER_CANDIDATE_METRICS.csv" "$OUT/metrics"/ 2>/dev/null
ls -la "$OUT/metrics"

echo
echo "=== 5) reports (acceptance / claims / inventory / gaps) ==="
for f in VALIDATION_REPORT.md PAIRING_CHECK.md PAIRING_CHECK.csv PAIRING_CHECK.json \
         CONSISTENCY_CHECK.md CONSISTENCY_CHECK.json CLAIM_EVIDENCE_MATRIX.csv \
         EVIDENCE_INVENTORY.csv GAPS_AND_EXCLUSIONS.md PRESENTATION_PLAN.md \
         QUESTIONS_AND_DECISIONS.md RUN_LEDGER.csv; do
  [ -f "$CF/reports/$f" ] && cp -a "$CF/reports/$f" "$OUT/reports/"
done
# showcase-level acceptance is also relevant evidence
[ -f "$SH/reports/SHOWCASE_VERIFICATION.md" ] && cp -a "$SH/reports/SHOWCASE_VERIFICATION.md" "$OUT/reports/"
[ -f "$SH/reports/SELECTION_GUIDE.md" ] && cp -a "$SH/reports/SELECTION_GUIDE.md" "$OUT/reports/"
[ -f "$SH/manifests/PREDICTION_CANDIDATES.csv" ] && cp -a "$SH/manifests/PREDICTION_CANDIDATES.csv" "$OUT/reports/"
[ -f "$SH/manifests/WEATHER_CANDIDATES.csv" ] && cp -a "$SH/manifests/WEATHER_CANDIDATES.csv" "$OUT/reports/"
ls "$OUT/reports" | wc -l

echo
echo "=== 6) reproduction: the arrays the selected figures actually consume ==="
cp -a "$FF/图3_标准空间预测/data/_arrays/P42" "$OUT/reproduction/P42_arrays"
cp -a "$FF/图3_标准空间预测/data/baseline_predictions/P42.npz" "$OUT/reproduction/P42_official_baselines.npz"
cp -a "$FF/图3_标准空间预测/data/baseline_predictions/P42_provenance.json" "$OUT/reproduction/" 2>/dev/null
cp -a "$FF/图8_天气条件响应/data/_arrays/W02" "$OUT/reproduction/W02_arrays"
cp -a "$FF/图3_标准空间预测/data/PREDICTION_CANDIDATES_60.csv" "$OUT/reproduction/" 2>/dev/null
cp -a "$FF/图3_标准空间预测/data/PREDICTION_CANDIDATE_METRICS_60.csv" "$OUT/reproduction/" 2>/dev/null
cp -a "$FF/图7_共同后缀与状态作用/data/MECHANISM_CANDIDATES_16.csv" "$OUT/reproduction/" 2>/dev/null
cp -a "$FF/图8_天气条件响应/data/WEATHER_CANDIDATES_12.csv" "$OUT/reproduction/" 2>/dev/null
find "$OUT/reproduction" -type f | sed "s|$OUT/||"

echo
echo "=== 7) safety assertions ==="
bad=$(find "$OUT" -type f \( -name '*.pt' -o -name '*.pth' -o -name '*.ckpt' -o -name '*.safetensors' \) | wc -l)
echo "  LFS-triggering files in payload: $bad (must be 0)"
[ "$bad" -ne 0 ] && exit 1
echo "  total files: $(find "$OUT" -type f | wc -l)"
echo "  total size : $(du -sh "$OUT" | cut -f1)"
echo "  largest 5  :"
find "$OUT" -type f -printf '%s\t%p\n' | sort -rn | head -5 | awk -F'\t' '{printf "    %8.2f MB  %s\n", $1/1048576, $2}' | sed "s|$OUT/||"

echo
echo "=== 8) sources still intact (copy, not move) ==="
for d in "$FF" "$ND" "$CF"; do
  printf '  %-70s files=%-6s bytes=%s\n' "$(basename "$d")" \
    "$(find "$d" -type f | wc -l)" "$(du -sb "$d" | cut -f1)"
done
echo "BUILD DONE (nothing staged/committed yet)"
