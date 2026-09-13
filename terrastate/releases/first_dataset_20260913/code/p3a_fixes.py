#!/usr/bin/env python3
"""Part 3a: repair the six verification failures."""
from __future__ import annotations

import io
import re
import shutil
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
OUT = Path("/data/zs/WorldModel2026/terrastate/releases/first_dataset_20260913")
R = Path("/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z")
ND = R / "first_dataset_narrative_dual_20260913T082412Z"
TF = R / "first_dataset_tables_figures_20260910T080000Z"

# ---------------------------------------------------------------- 1 supply the cited references
print("=== 1) copy the Chinese reference documents that figures/references/*.md cite ===")
WANT = {
    "A13_TerraState_科学主线与图表证据总纲.md": ND / "references/A13_TerraState_科学主线与图表证据总纲.md",
    "A14_训练端执行总纲与监督契约.md": ND / "references/A14_训练端执行总纲与监督契约.md",
    "A14B_第一数据集实验实现与验收细则.md": ND / "references/A14B_第一数据集实验实现与验收细则.md",
    "A13B_第二数据集候选调研与延后决策.md": TF / "sources/A13B_第二数据集候选调研与延后决策.md",
}
dst_dir = OUT / "figures/references"
for name, src in WANT.items():
    if not src.exists():
        print(f"  SOURCE MISSING: {src}")
        continue
    shutil.copyfile(src, dst_dir / name)
    print(f"  copied {name}  ({src.stat().st_size:,} B)")

# ------------------------------------------- 2 the master draft: unlink images not in the package
print("\n=== 2) master draft: convert its unresolved image links to plain text ===")
M = OUT / "figures/references/OVERVIEW_母稿_20260912T112243Z.md"
t = M.read_text(encoding="utf-8")
IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def fix(m):
    alt, tgt = m.group(1), m.group(2).strip()
    if tgt.startswith(("http://", "https://")):
        return m.group(0)
    if (M.parent / tgt.split("#")[0]).exists():
        return m.group(0)
    return f"{alt}（历史草稿用图 `{Path(tgt).name}`，未随精简发布包收录）"


n_before = len(IMG.findall(t))
t2 = IMG.sub(fix, t)
n_after_links = len(IMG.findall(t2))
M.write_text(t2, encoding="utf-8")
print(f"  image links before: {n_before}  still links after: {n_after_links}  "
      f"converted: {n_before - n_after_links}")

# also note it in the banner
anchor = "> 文中所有**数值与科学结论未改动**。\n"
if anchor in t2:
    t2 = t2.replace(anchor, anchor +
                    "> 本文件原引用的历史草稿图片未随精简发布包收录，因此其图片链接已改为纯文本标注；\n"
                    "> 需要的图片请到运行目录的对应包中查找。\n", 1)
    M.write_text(t2, encoding="utf-8")
    print("  banner updated with the image note")

# ---------------------------------------------------------------- 3 图3 docs name the four baselines
print("\n=== 3) 图3 analysis / README: name the four official baselines ===")
FOUR_ZH = "（ConvLSTM 1M、PredRNN 1M、SimVP 6M、Contextformer 6M）"
A = OUT / "figures/图3_标准空间预测/ANALYSIS_ZH.md"
a = A.read_text(encoding="utf-8")
old = "四个官方基线均来自匹配的GreenEarthNet官方seed-42 checkpoint"
if old in a:
    a = a.replace(old, f"四个官方基线{FOUR_ZH}均来自匹配的GreenEarthNet官方seed-42 checkpoint", 1)
    A.write_text(a, encoding="utf-8")
    print("  ANALYSIS_ZH.md updated")
else:
    print("  ANALYSIS_ZH.md: anchor not found")
Rd = OUT / "figures/图3_标准空间预测/README.md"
r = Rd.read_text(encoding="utf-8")
old = "与四个官方基线的空间预测和逐像素绝对误差。"
if old in r:
    r = r.replace(old, f"与四个官方基线{FOUR_ZH}的空间预测和逐像素绝对误差。", 1)
    Rd.write_text(r, encoding="utf-8")
    print("  README.md updated")
else:
    print("  README.md: anchor not found")

print("\n=== 4) confirm every markdown link now resolves ===")
EXT = (".md", ".png", ".pdf", ".csv", ".json", ".sh", ".py", ".txt")
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def looks(x):
    if x.startswith(("http://", "https://", "#", "mailto:", "<")):
        return False
    x = x.split("#")[0].strip()
    return bool(x) and x.endswith(EXT) and not any(c in x for c in "^$`{} \\")


bad = []
checked = 0
for md in sorted(OUT.rglob("*.md")):
    for m in LINK.finditer(md.read_text(encoding="utf-8", errors="replace")):
        raw = m.group(1).strip()
        if not looks(raw):
            continue
        checked += 1
        if not (md.parent / raw.split("#")[0].strip()).exists():
            bad.append(f"{md.relative_to(OUT)} -> {raw}")
print(f"  checked {checked}, broken {len(bad)}")
for b in bad[:10]:
    print("   ", b)
