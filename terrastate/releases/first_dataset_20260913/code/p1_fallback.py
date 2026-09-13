#!/usr/bin/env python3
"""Part 1: add a release-package fallback to the two redraw scripts.

The release ships the arrays ONCE under `reproduction/` instead of duplicating them inside each
figure directory. Each script now prefers its original figure-local input and falls back to the
release root, so the slim package can still redraw without a ~13 MiB duplicate.

Only the RELEASE copies are edited; the frozen source packages are untouched.
"""
from __future__ import annotations

import hashlib
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REL = Path("/data/zs/WorldModel2026/terrastate/releases/first_dataset_20260913")

RESOLVER = '''
# ---------------------------------------------------------------------------------------------
# Input resolution. The curated release package stores these arrays ONCE under
# `reproduction/` instead of duplicating them inside every figure directory. Prefer the original
# figure-local export when it is present (full source package), otherwise fall back to the
# release root (slim package). Nothing else about the drawing depends on which one is used.
ROOT=FIG.parents[1]                      # .../first_dataset_20260913

def _pick(*cands):
    for c in cands:
        if c.exists():
            return c
    raise SystemExit("input not found; tried:\\n  " + "\\n  ".join(str(c) for c in cands))

'''

PATCHES = {
    "figures/图3_标准空间预测/code/render_final.py": [
        ('z=np.load(FIG/"data"/"_arrays"/"P42"/"arrays.npz")\n'
         'b=np.load(FIG/"data"/"baseline_predictions"/"P42.npz")\n'
         'meta=json.loads((FIG/"data"/"_arrays"/"P42"/"metadata.json").read_text(encoding="utf-8"))\n',
         RESOLVER +
         '_ARRAYS=_pick(FIG/"data"/"_arrays"/"P42"/"arrays.npz",\n'
         '              ROOT/"reproduction"/"P42_arrays"/"arrays.npz")\n'
         '_META=_pick(FIG/"data"/"_arrays"/"P42"/"metadata.json",\n'
         '            ROOT/"reproduction"/"P42_arrays"/"metadata.json")\n'
         '_BASELINE=_pick(FIG/"data"/"baseline_predictions"/"P42.npz",\n'
         '                ROOT/"reproduction"/"P42_official_baselines.npz")\n'
         'z=np.load(_ARRAYS)\n'
         'b=np.load(_BASELINE)\n'
         'meta=json.loads(_META.read_text(encoding="utf-8"))\n'),
    ],
    "figures/图8_天气条件响应/code/render_final.py": [
        ('z=np.load(FIG/"data"/"_arrays"/"W02"/"arrays.npz")\n'
         'meta=json.loads((FIG/"data"/"_arrays"/"W02"/"metadata.json").read_text(encoding="utf-8"))\n',
         RESOLVER +
         '_ARRAYS=_pick(FIG/"data"/"_arrays"/"W02"/"arrays.npz",\n'
         '              ROOT/"reproduction"/"W02_arrays"/"arrays.npz")\n'
         '_META=_pick(FIG/"data"/"_arrays"/"W02"/"metadata.json",\n'
         '            ROOT/"reproduction"/"W02_arrays"/"metadata.json")\n'
         'z=np.load(_ARRAYS)\n'
         'meta=json.loads(_META.read_text(encoding="utf-8"))\n'),
    ],
}

for rel, pairs in PATCHES.items():
    p = REL / rel
    t = p.read_text(encoding="utf-8")
    before = hashlib.sha256(t.encode()).hexdigest()[:16]
    for old, new in pairs:
        if old not in t:
            sys.exit(f"FAILED: anchor not found in {rel}")
        t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    after = hashlib.sha256(t.encode()).hexdigest()[:16]
    print(f"patched {rel}\n   {before} -> {after}  ({len(t):,} B)")

# syntax check
import ast
for rel in PATCHES:
    ast.parse((REL / rel).read_text(encoding="utf-8"))
print("both scripts parse OK")
