#!/usr/bin/env python3
"""Fix the dead-link defect in the release package.

Problem: the narrative source package used ABSOLUTE symlinks into /data/zs/. A git checkout
(and the GitHub web UI) cannot resolve them, so 24 relative image/link references inside the two
main documents were broken.

Fix, applied to the RELEASE COPY ONLY (sources untouched):
  1. delete the 14 symlinks;
  2. copy the small real directories they pointed at (metrics_derived, provenance, manifests,
     metrics) so nothing is lost, never shipping *.pt;
  3. rewrite relative link targets `图N_x/...` -> `../figures/图N_x/...` so they resolve against the
     single copy of the figures (no 50 MB duplication);
  4. verify every relative link/image in every narrative markdown file resolves on disk.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OUT = Path("/data/zs/WorldModel2026/terrastate/releases/first_dataset_20260913")
NAR = OUT / "narrative"
N1 = Path("/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/"
          "first_dataset_narrative_20260912T112243Z")

print("=== 1) symlinks found in the release (all removed) ===")
links = sorted(p for p in OUT.rglob("*") if p.is_symlink())
for l in links:
    print(f"  {l.relative_to(OUT)}  ->  {os.readlink(l)}")
    l.unlink()
print(f"  removed {len(links)};  remaining symlinks: {sum(1 for _ in OUT.rglob('*') if _.is_symlink())}")

print()
print("=== 2) copy the small real directories those links pointed at ===")
for d in ("metrics_derived", "provenance", "manifests", "metrics", "tables"):
    src = N1 / d
    if not src.exists():
        print(f"  {d}: source missing, skipped")
        continue
    n_files = sum(1 for _ in src.rglob("*") if _.is_file())
    if n_files == 0:
        print(f"  {d}: empty at source, skipped")
        continue
    dst = NAR / d
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.rglob("*"):
        if p.is_file():
            # realpath so a symlinked source is followed; enforce the name in the destination
            shutil.copyfile(p, dst / p.name)
    print(f"  {d}: copied {n_files} file(s)")

pt = sorted(NAR.rglob("*.pt")) + sorted(NAR.rglob("*.pth")) + sorted(NAR.rglob("*.ckpt"))
for p in pt:
    print(f"  removing weight file that must never ship: {p.relative_to(OUT)}")
    p.unlink()
print(f"  weight-like files under narrative/: {len(list(NAR.rglob('*.pt')))} (must be 0)")

print()
print("=== 3) rewrite figure-relative link targets to ../figures/ ===")
pat = re.compile(r"\]\((图[0-9]+_[^)]*?)\)")
total = 0
for md in sorted(NAR.rglob("*.md")):
    t = md.read_text(encoding="utf-8")
    new, n = pat.subn(lambda m: f"](../figures/{m.group(1)})", t)
    if n:
        md.write_text(new, encoding="utf-8")
        print(f"  {md.relative_to(OUT)}: {n} link target(s) rewritten")
        total += n
print(f"  total rewritten: {total}")

print()
print("=== 4) verify every relative link/image in every narrative markdown resolves ===")
bad = []
for md in sorted(NAR.rglob("*.md")):
    t = md.read_text(encoding="utf-8")
    for m in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", t):
        tgt = m.group(1).strip()
        if tgt.startswith(("http://", "https://", "#", "mailto:")):
            continue
        tgt = tgt.split("#")[0]
        if not tgt:
            continue
        if not (md.parent / tgt).exists():
            bad.append(f"{md.relative_to(OUT)} -> {tgt}")
print(f"  unresolved references: {len(bad)}")
for b in bad[:15]:
    print("   ", b)

print()
print("=== 5) overview of the fixed narrative directory ===")
for p in sorted(NAR.iterdir()):
    if p.is_dir():
        print(f"  {p.name}/  {sum(1 for _ in p.rglob('*') if _.is_file())} files")
    else:
        print(f"  {p.name}  {p.stat().st_size:,} B")
print()
print(f"release files: {sum(1 for p in OUT.rglob('*') if p.is_file())}")
print(f"release size : {sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()) / 1048576:.1f} MiB")
sys.exit(1 if bad else 0)
