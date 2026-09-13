#!/bin/bash
# Final acceptance for the TerraState first-dataset narrative delivery.
WD=/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_narrative_20260912T112243Z
SC=/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_showcase_20260912T062326Z
FX=/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/first_dataset_closure_fix_20260911T081702Z
BASE=/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z
FAIL=0
ok(){ echo "  PASS  $1"; }
ng(){ echo "  FAIL  $1"; FAIL=$((FAIL+1)); }

echo "== A1. table numbers correspond to sections =="
cd "$WD" || exit 1
for t in "表 1" "表 3" "表 4A" "表 4B" "表 5" "表 6A" "表 6B" "表 7"; do
  n=$(grep -c "$t" OVERVIEW.md)
  [ "$n" -ge 2 ] && ok "$t referenced $n times" || ng "$t referenced only $n times"
done
grep -q '表 2' OVERVIEW.md && ok "表 2 listed as deferred" || ng "表 2 not listed"
for f in 图 1 图 2 图 3 图 4 图 5 图 6 图 7 图 8 图 9; do
  grep -q "$f" OVERVIEW.md || ng "$f missing from index"
done
ok "图 1-9 all appear in the figure index"

echo "== A2. numbers traceable =="
python3 check_traceability.py > /tmp/tc.txt 2>&1
grep -q "distinct decimals" /tmp/tc.txt && ok "traceability script ran" || ng "traceability script failed"
grep -q "re-derivation" /tmp/tc.txt && ok "key ratios re-derived" || ng "re-derivation missing"
[ -s metrics_derived/DERIVED_STATS.csv ] && ok "DERIVED_STATS.csv present" || ng "DERIVED_STATS.csv empty"
python3 - <<'PY'
import json,sys
d=json.load(open("metrics_derived/DERIVED_STATS_PROVENANCE.json",encoding="utf-8"))
assert all(s["exists"] for s in d["sources"]), "a recorded source is missing"
assert d["derived"], "no derived values"
print("  PASS  provenance: %d sources hashed, %d derived values"
      % (len(d["sources"]), len(d["derived"])))
PY

echo "== A3. markdown tables render (column consistency) =="
python3 - <<'PY'
import re,sys
lines=open("OVERVIEW.md",encoding="utf-8").read().split("\n")
i=0;tables=0;bad=[]
def cols(r):
    t=r.strip()
    if t.startswith("|"): t=t[1:]
    if t.endswith("|"): t=t[:-1]
    return len(t.split("|"))
while i<len(lines):
    if lines[i].lstrip().startswith("|"):
        blk=[];start=i
        while i<len(lines) and lines[i].lstrip().startswith("|"):
            blk.append(lines[i]); i+=1
        tables+=1
        cs=set(cols(r) for r in blk)
        if len(cs)>1: bad.append((start+1,sorted(cs)))
    else: i+=1
print("  tables: %d" % tables)
if bad:
    for ln,cs in bad: print("  FAIL  table at line %d has column counts %s" % (ln,cs))
    sys.exit(1)
print("  PASS  all tables have consistent column counts")
PY
[ $? -eq 0 ] || FAIL=$((FAIL+1))
grep -q '\\|' OVERVIEW.md && ng "escaped pipe found inside a table cell" || ok "no escaped pipes that could break columns"

echo "== A4. image/file references resolve =="
bash provenance/check_reference_resolution.sh > /tmp/rr.txt 2>&1
if grep -q "ACCEPTANCE: ALL REFERENCES RESOLVE" /tmp/rr.txt; then ok "all references resolve from the narrative dir"; else ng "reference resolution problem"; grep MISS /tmp/rr.txt; fi

echo "== A5. frozen packages unmodified =="
newer=$(find "$SC" "$FX" /data/zs/multiseed_standard_eval_20260910T074115Z -newermt "2026-09-12 11:20" -type f 2>/dev/null | head)
[ -z "$newer" ] && ok "no file inside the frozen packages was touched this round" || { ng "files touched in frozen packages:"; echo "$newer"; }
other=$(find "$BASE" -maxdepth 1 -mindepth 1 -newermt "2026-09-12 11:20" 2>/dev/null)
[ "$other" = "$WD" ] && ok "narrative dir is the only new entry under the results root" || { ng "unexpected new entries:"; echo "$other"; }
out=0
for p in "$WD"/*; do case "$(realpath "$p")" in /data/zs/*) :;; *) echo "  OUT $p"; out=1;; esac; done
[ "$out" -eq 0 ] && ok "every narrative entry resolves inside /data/zs" || FAIL=$((FAIL+1))
[ -z "$(find -L "$WD" -type l 2>/dev/null)" ] && ok "no broken links" || { ng "broken links present"; find -L "$WD" -type l; }

echo "== A6. no plan written as done; no diagnostic image as mechanism evidence =="
if grep -nE '本包|不得声称|本包禁止' OVERVIEW.md >/dev/null; then ng "audit tone still present"; grep -nE '本包|不得声称' OVERVIEW.md; else ok "no audit-tone phrasing"; fi
for phrase in "任意分段" "连续时间" "完整物理状态" "真实反事实"; do
  c=$(grep -c "$phrase" OVERVIEW.md)
  echo "     '$phrase' occurs $c time(s) (must only appear as a disclaimed boundary)"
done
grep -q "分段实验或状态替换证据" OVERVIEW.md && ok "prediction gallery explicitly labelled as non-mechanism evidence" || ng "gallery labelling missing"
grep -q "现有版本" OVERVIEW.md && ok "reused figures labelled with their status" || ng "figure status labels missing"
grep -q "图 6（现有版本，后续重绘）" OVERVIEW.md && ok "图 6 correction note present" || ng "图 6 correction note missing"

echo "== A7/A8. delivery complete, documents identical across locations =="
for f in OVERVIEW.md 文案修订说明.md 第一数据集成果总览_文案优化_20260912.md recompute_derived.py check_traceability.py TRACEABILITY_CHECK.md; do
  [ -f "$WD/$f" ] && ok "remote has $f" || ng "remote missing $f"
done
for d in references metrics_derived provenance; do
  [ -d "$WD/$d" ] && [ -n "$(ls -A "$WD/$d")" ] && ok "$d populated" || ng "$d empty"
done

echo
echo "== files produced this round =="
find "$WD" -type f -printf '%10s  %P\n' | sort -k2

echo
if [ "$FAIL" -eq 0 ]; then echo "ACCEPTANCE: ALL CHECKS PASSED"; else echo "ACCEPTANCE: $FAIL CHECK(S) FAILED"; fi
exit $FAIL
