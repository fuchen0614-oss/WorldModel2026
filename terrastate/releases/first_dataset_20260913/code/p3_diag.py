#!/usr/bin/env python3
"""Diagnose the 6 failures precisely."""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
OUT = Path("/data/zs/WorldModel2026/terrastate/releases/first_dataset_20260913")
R = Path("/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z")
FF = R / "first_dataset_figures_final_20260913T052645Z"
ND = R / "first_dataset_narrative_dual_20260913T082412Z"
N1 = R / "first_dataset_narrative_20260912T112243Z"

print("=== 1) where does the master draft really come from? ===")
for cand in (N1 / "references/OVERVIEW_母稿_20260912T112243Z.md",
             FF / "references/OVERVIEW_母稿_20260912T112243Z.md"):
    print(f"  {cand.exists()}  {cand}")

print("\n=== 2) the 15 broken markdown links (file -> target) ===")
EXT = (".md", ".png", ".pdf", ".csv", ".json", ".sh", ".py", ".txt")
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def looks(t):
    if t.startswith(("http://", "https://", "#", "mailto:", "<")):
        return False
    t = t.split("#")[0].strip()
    return bool(t) and t.endswith(EXT) and not any(c in t for c in "^$`{} \\")


broken = {}
for md in sorted(OUT.rglob("*.md")):
    for m in LINK.finditer(md.read_text(encoding="utf-8", errors="replace")):
        raw = m.group(1).strip()
        if not looks(raw):
            continue
        rel = raw.split("#")[0].strip()
        if not (md.parent / rel).exists():
            broken.setdefault(str(md.relative_to(OUT)), []).append(rel)
missing_targets = {}
for f, targets in broken.items():
    for t in targets:
        missing_targets.setdefault(Path(t).name, []).append(f)
for name, files in sorted(missing_targets.items()):
    print(f"  missing target: {name}")
    for f in files:
        print(f"      referenced by {f}")

print("\n=== 3) do those targets exist anywhere we can copy from? ===")
for name in sorted(missing_targets):
    hits = [str(p) for root in (ND, N1, FF, R / "first_dataset_tables_figures_20260910T080000Z")
            for p in root.rglob(name)]
    print(f"  {name}: {hits[:3] if hits else 'NOT FOUND'}")

print("\n=== 4) lines still claiming baselines are unavailable ===")
PAT = re.compile(r"基线[^。\n]{0,40}(不可用|不在盘上)|(不可用|not available)[^。\n]{0,20}基线")
for p in sorted(OUT.rglob("*.md")):
    for i, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if PAT.search(ln) and not any(k in ln for k in ("已过时", "已解除", "已更新", "历史母稿", "superseded")):
            print(f"  {p.relative_to(OUT)}:{i}")
            print(f"      {ln.strip()[:180]}")

print("\n=== 5) 图3 ANALYSIS / README exact baseline wording ===")
for f in ("ANALYSIS_ZH.md", "README.md", "CAPTION_ZH.md"):
    t = (OUT / "figures/图3_标准空间预测" / f).read_text(encoding="utf-8")
    hits = [ln.strip() for ln in t.splitlines() if "基线" in ln]
    print(f"  --- {f} ---")
    for ln in hits[:3]:
        print(f"      {ln[:170]}")

print("\n=== 6) figures/references inventory vs narrative/references ===")
print("  figures/references:", sorted(p.name for p in (OUT / "figures/references").iterdir()))
print("  narrative/references:", sorted(p.name for p in (OUT / "narrative/references").iterdir()))
