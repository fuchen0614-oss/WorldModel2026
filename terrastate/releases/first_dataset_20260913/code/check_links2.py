#!/usr/bin/env python3
"""Refine the link check and repair the one genuinely missing reference.

The naive regex matched LaTeX-ish fragments inside `$...$` (`z_b^direct = T_[0,b](z0)`) and local
editor paths (`<D:/.../file.py:123>`). A reference is only checked when it looks like a real file
reference: it ends with a known extension and contains no code/math characters.
"""
from __future__ import annotations

import io
import re
import shutil
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
OUT = Path("/data/zs/WorldModel2026/terrastate/releases/first_dataset_20260913")
NAR = OUT / "narrative"
A13B_SRC = Path("/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/"
                "first_dataset_tables_figures_20260910T080000Z/sources/"
                "A13B_第二数据集候选调研与延后决策.md")

print("=== 1) supply the reference A13 actually cites ===")
if A13B_SRC.exists():
    dst = NAR / "references" / A13B_SRC.name
    shutil.copyfile(A13B_SRC, dst)
    print(f"  copied {A13B_SRC.name} -> narrative/references/")
else:
    print(f"  SOURCE MISSING: {A13B_SRC}")

EXT = (".md", ".png", ".pdf", ".csv", ".json", ".sh", ".py", ".txt", ".yml", ".yaml")
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def looks_like_path(t: str) -> bool:
    if t.startswith(("http://", "https://", "#", "mailto:", "<")):
        return False
    t = t.split("#")[0].strip()
    if not t or not t.endswith(EXT):
        return False
    # exclude math / code fragments
    return not any(ch in t for ch in "^$`{} \\")


print()
print("=== 2) resolve every real file reference in every narrative markdown ===")
bad, checked = [], 0
for md in sorted(NAR.rglob("*.md")):
    t = md.read_text(encoding="utf-8")
    for m in LINK.finditer(t):
        tgt = m.group(1).strip()
        if not looks_like_path(tgt):
            continue
        checked += 1
        rel = tgt.split("#")[0].strip()
        if not (md.parent / rel).exists():
            bad.append(f"{md.relative_to(OUT)} -> {rel}")
print(f"  references checked: {checked}")
print(f"  unresolved        : {len(bad)}")
for b in bad:
    print("   ", b)

print()
print("=== 3) figure links specifically (the ones that were dead) ===")
fig_links = []
for md in sorted(NAR.rglob("*.md")):
    t = md.read_text(encoding="utf-8")
    for m in LINK.finditer(t):
        if m.group(1).strip().startswith("../figures/"):
            fig_links.append((md.relative_to(OUT), m.group(1).strip()))
miss = [(a, b) for a, b in fig_links if not (NAR / a).parent.joinpath(b).exists()]
print(f"  figure links: {len(fig_links)}   unresolved: {len(miss)}")
for a, b in miss[:8]:
    print("   ", a, "->", b)

print()
print("=== 4) no symlinks, no weight-like files anywhere in the release ===")
sl = [str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_symlink()]
wt = [str(p.relative_to(OUT)) for p in OUT.rglob("*")
      if p.is_file() and p.suffix in (".pt", ".pth", ".ckpt", ".safetensors", ".bin", ".onnx")]
print(f"  symlinks: {len(sl)} {sl[:5]}")
print(f"  weights : {len(wt)} {wt[:5]}")

print()
print(f"release files: {sum(1 for p in OUT.rglob('*') if p.is_file())}")
print(f"release size : {sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()) / 1048576:.1f} MiB")
sys.exit(1 if (bad or sl or wt) else 0)
