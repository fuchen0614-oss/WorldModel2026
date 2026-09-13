#!/usr/bin/env python3
"""Part 1c: redraw every final figure in a TEMP copy and compare against the released selected/.

The temp copy deliberately has the figure-local arrays removed, so this simultaneously proves
(a) the new release-root fallback works and (b) the redraw is reproducible.

Nothing in the release package is modified.
"""
from __future__ import annotations

import hashlib
import io
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REL = Path("/data/zs/WorldModel2026/terrastate/releases/first_dataset_20260913")
TMP = Path("/data/zs/fsr_tmp/redraw_test/first_dataset_20260913")
PY = "/data/zs/WorldModel2026/.venv-worldmodel/bin/python"

print("=== build the temp slim copy (figures + reproduction only) ===")
if TMP.parent.exists():
    shutil.rmtree(TMP.parent)
TMP.mkdir(parents=True)
for sub in ("figures", "reproduction"):
    shutil.copytree(REL / sub, TMP / sub)
print(f"  copied to {TMP}")

print("\n=== remove the figure-local arrays to force the fallback path ===")
removed = []
for d in ("figures/图3_标准空间预测/data/_arrays",
          "figures/图3_标准空间预测/data/baseline_predictions",
          "figures/图8_天气条件响应/data/_arrays"):
    p = TMP / d
    if p.exists():
        shutil.rmtree(p)
        removed.append(d)
for r in removed:
    print(f"  removed {r}")
print(f"  fallback targets present: "
      f"{(TMP/'reproduction/P42_arrays/arrays.npz').exists()}, "
      f"{(TMP/'reproduction/P42_official_baselines.npz').exists()}, "
      f"{(TMP/'reproduction/W02_arrays/arrays.npz').exists()}")

FIGS = ["图3_标准空间预测", "图5_时距与分布偏移", "图6_分段稳定性",
        "图7_共同后缀与状态作用", "图8_天气条件响应", "图9_状态复用成本"]

print("\n=== run each render_final.py in the temp copy ===")
ran = {}
for f in FIGS:
    script = TMP / "figures" / f / "code/render_final.py"
    r = subprocess.run([PY, str(script)], capture_output=True, text=True, errors="replace")
    ok = r.returncode == 0
    ran[f] = ok
    print(f"  {f:<28} rc={r.returncode}")
    if not ok:
        for ln in ((r.stdout or "") + (r.stderr or "")).splitlines()[-6:]:
            print("      ", ln)

print("\n=== compare redrawn output against the released selected/ ===")
rows = []
for f in FIGS:
    src_dir = REL / "figures" / f / "selected"
    new_dir = TMP / "figures" / f / "selected"
    for src in sorted(src_dir.glob("*")):
        new = new_dir / src.name
        if not new.exists():
            rows.append((f, src.name, "MISSING", ""))
            continue
        a = src.read_bytes()
        b = new.read_bytes()
        if src.suffix.lower() == ".png":
            ia, ib = mpimg.imread(src), mpimg.imread(new)
            same = ia.shape == ib.shape and np.array_equal(np.nan_to_num(ia), np.nan_to_num(ib))
            if same:
                rows.append((f, src.name, "PIXEL-IDENTICAL",
                             f"{ia.shape[0]}x{ia.shape[1]}"))
            else:
                maxd = (float(np.nanmax(np.abs(np.nan_to_num(ia) - np.nan_to_num(ib))))
                        if ia.shape == ib.shape else float("nan"))
                rows.append((f, src.name, "PIXEL-DIFF", f"max|diff|={maxd:.3e}"))
        else:
            ha, hb = hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()
            if ha == hb:
                rows.append((f, src.name, "BYTE-IDENTICAL", f"{len(a):,} B"))
            else:
                # PDFs embed a creation timestamp; compare size as a sanity signal
                rows.append((f, src.name, "BYTE-DIFF",
                             f"{len(a):,} vs {len(b):,} B (sha differs)"))

w = max(len(r[1]) for r in rows)
n_png_ok = sum(1 for r in rows if r[2] == "PIXEL-IDENTICAL")
n_png = sum(1 for r in rows if r[1].endswith(".png"))
n_pdf_ok = sum(1 for r in rows if r[2] == "BYTE-IDENTICAL")
n_pdf = sum(1 for r in rows if r[1].endswith(".pdf"))
for r in rows:
    print(f"  {r[0]:<22} {r[1]:<{w}}  {r[2]:<16} {r[3]}")

print(f"\n  PNG pixel-identical: {n_png_ok}/{n_png}")
print(f"  PDF byte-identical : {n_pdf_ok}/{n_pdf}")
allran = all(ran.values())
print(f"  all six scripts ran: {allran}")
print(f"\n  RESULT: {'PASS' if (allran and n_png_ok == n_png and n_png == 18) else 'REVIEW'}")
