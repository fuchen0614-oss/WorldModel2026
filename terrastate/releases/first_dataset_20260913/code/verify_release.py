#!/usr/bin/env python3
"""Verify the release package and write SHA256SUMS.txt + QA_REPORT.md.

Independent checks only: source trees must be unchanged, the payload must contain no
LFS-triggering files, the narrative copies must match the narrative package's own hash file, and
the figures/tables must be the expected ones.
"""
from __future__ import annotations

import hashlib
import io
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GITROOT = Path("/data/zs/WorldModel2026")
OUT = GITROOT / "terrastate/releases/first_dataset_20260913"
R = Path("/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z")
FF = R / "first_dataset_figures_final_20260913T052645Z"
ND = R / "first_dataset_narrative_dual_20260913T082412Z"
CF = R / "first_dataset_closure_fix_20260911T081702Z"
SH = R / "first_dataset_showcase_20260912T062326Z"

# fingerprints recorded BEFORE the copy (see build_release.sh output)
PRE = {FF.name: (728, 472240958), ND.name: (11, 249228), CF.name: (130, 1511302222)}

checks = []


def ck(name, ok, detail=""):
    checks.append((name, "PASS" if ok else "FAIL", str(detail)))
    return ok


def sha(p: Path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def tree(d: Path):
    fs = [p for p in d.rglob("*") if p.is_file()]
    return len(fs), sum(p.stat().st_size for p in fs)


# ---------------------------------------------------------------- 0 ship the QA tooling
CODE = OUT / "code"
CODE.mkdir(parents=True, exist_ok=True)
TOOLING = ["build_release.sh", "gen_release_docs.py", "verify_release.py", "fix_links.py",
           "check_links2.py"]
copied = []
for name in TOOLING:
    src = Path("/data/zs/fsr_tmp") / name
    if src.exists():
        import shutil as _sh
        _sh.copyfile(src, CODE / name)
        copied.append(name)
ck("QA/build tooling shipped inside the package", len(copied) >= 3, copied)

# ---------------------------------------------------------------- 1 required files
REQ = ["README.md", "SOURCE_COMMIT.md", "CODE_AND_CONFIG_INDEX.md", "WEIGHTS.md",
       "QA_REPORT.md", "SHA256SUMS.txt"]
missing = [f for f in REQ if not (OUT / f).exists()]
ck("all top-level documents present", not missing, missing)
ck("narrative carries both main documents",
   (OUT / "narrative/01_TerraState_第一数据集成果总览_十二章继承更新版.md").exists()
   and (OUT / "narrative/02_TerraState_中文论文叙事稿.md").exists(),
   "01 十二章继承更新版 + 02 中文论文叙事稿")
figs = sorted(d.name for d in (OUT / "figures").glob("图*"))
ck("nine figure directories present", len(figs) == 9, figs)
sel = sorted(p.name for p in (OUT / "figures").glob("图*/selected/*"))
ck("selected figures present", len(sel) >= 18, f"{len(sel)} files")
ck("tables count is 16 (8 tables x md+csv)",
   len(list((OUT / "tables").iterdir())) == 16,
   f"{len(list((OUT / 'tables').iterdir()))} files")
ck("metrics present", len(list((OUT / "metrics").iterdir())) >= 4,
   sorted(p.name for p in (OUT / "metrics").iterdir()))
ck("reproduction arrays present",
   (OUT / "reproduction/P42_arrays/arrays.npz").exists()
   and (OUT / "reproduction/P42_official_baselines.npz").exists()
   and (OUT / "reproduction/W02_arrays/arrays.npz").exists(),
   "P42 arrays + P42 official baselines + W02 arrays")

# ---------------------------------------------------------------- 2 no LFS files
lfs = [str(p.relative_to(OUT)) for p in OUT.rglob("*")
       if p.is_file() and p.suffix in (".pt", ".pth", ".ckpt", ".safetensors")]
ck("payload contains no LFS-triggering weights", not lfs, lfs[:5])

# ---------------------------------------------------------------- 3 sources untouched
# NOTE: the pre-copy fingerprint recorded by build_release.sh came from `du` (allocated blocks),
# while this script sums st_size (apparent size); the two differ by block rounding, so the byte
# totals are NOT comparable. File counts are. The real invariant -- "every shipped file is a
# byte-identical copy of a source file" -- is checked separately below.
PRE_COUNTS = {FF.name: 728, ND.name: 11, CF.name: 130}
untouched = []
for name, n0 in PRE_COUNTS.items():
    src = {FF.name: FF, ND.name: ND, CF.name: CF}[name]
    n1 = sum(1 for p in src.rglob("*") if p.is_file())
    if n1 != n0:
        untouched.append(f"{name}: file count {n0} -> {n1}")
ck("source trees still hold every original file", not untouched, untouched)

# every release file must exist byte-identical somewhere in the source roots (copy, not move,
# and not edited after copying)
SRC_ROOTS = [FF, ND, CF, SH,
             R / "first_dataset_narrative_20260912T112243Z",     # metrics_derived / provenance / ...
             R / "first_dataset_tables_figures_20260910T080000Z",  # A13B reference doc
             Path("/data/zs/fsr_tmp")]                            # the QA/build tooling
# covered by the stronger rewrite-proof check above, so excluded from the byte-identity sweep
REWRITTEN = {f"narrative/{n}" for n in
             ("01_TerraState_第一数据集成果总览_十二章继承更新版.md", "02_TerraState_中文论文叙事稿.md")}
GENERATED = {"README.md", "SOURCE_COMMIT.md", "CODE_AND_CONFIG_INDEX.md", "WEIGHTS.md",
             "QA_REPORT.md", "SHA256SUMS.txt"}
index, by_size = {}, {}
for root in SRC_ROOTS:
    for p in root.rglob("*"):
        if p.is_file():
            h = sha(p)
            index.setdefault((p.name, p.stat().st_size), set()).add(h)
            by_size.setdefault(p.stat().st_size, set()).add(h)
orphan = []
for p in OUT.rglob("*"):
    if not p.is_file() or p.name in GENERATED or str(p.relative_to(OUT)) in REWRITTEN:
        continue
    h = sha(p)
    if h in index.get((p.name, p.stat().st_size), set()):
        continue
    # a deliberately renamed copy (e.g. P42.npz -> P42_official_baselines.npz) still has to match
    # some source file byte for byte
    if h in by_size.get(p.stat().st_size, set()):
        continue
    orphan.append(str(p.relative_to(OUT)))
ck("every shipped file is a byte-identical copy of a source file", not orphan,
   f"{len(orphan)} unverified: {orphan[:5]}")

# The two main documents were INTENTIONALLY edited in the release copy: their relative figure
# links were rewritten from `图N_x/...` to `../figures/图N_x/...` so they resolve in a git
# checkout (the source package used absolute symlinks, which are dead on GitHub and on Windows).
# Proof that nothing else changed: applying the same rewrite to the source must reproduce the
# release copy byte for byte.
REWRITE = re.compile(r"\]\((图[0-9]+_[^)]*?)\)")
proof_bad = []
for name in ("01_TerraState_第一数据集成果总览_十二章继承更新版.md", "02_TerraState_中文论文叙事稿.md"):
    src = ND / name
    dst = OUT / "narrative" / name
    if not (src.exists() and dst.exists()):
        proof_bad.append(f"{name}: missing")
        continue
    expected = REWRITE.sub(lambda m: f"](../figures/{m.group(1)})",
                           src.read_text(encoding="utf-8"))
    if expected != dst.read_text(encoding="utf-8"):
        proof_bad.append(f"{name}: differs by more than the link rewrite")
ck("the two main documents differ from their source ONLY by the documented link rewrite",
   not proof_bad, proof_bad)

# narrative hash cross-check, allowing exactly those two rewritten documents
hf = OUT / "narrative/reports/MAIN_FILES_SHA256.txt"
if hf.exists():
    lines = [l for l in hf.read_text(encoding="utf-8").splitlines() if "  " in l]
    rewritten = {"01_TerraState_第一数据集成果总览_十二章继承更新版.md",
                 "02_TerraState_中文论文叙事稿.md"}
    mism, unexpected = [], []
    for ln in lines:
        h, rel = ln.split("  ", 1)
        rel = rel.strip()
        cand = OUT / "narrative" / rel
        if not cand.exists():
            cand = OUT / "narrative" / Path(rel).name
        if not cand.exists():
            unexpected.append(rel)
            continue
        if sha(cand) != h.strip():
            (mism if Path(rel).name in rewritten else unexpected).append(Path(rel).name)
    ck("narrative hash file: the only entries that differ are the two intentionally rewritten docs",
       not unexpected, f"{len(lines)} entries; differing={mism}; unexpected={unexpected}")
else:
    ck("narrative hash file present", False, "MAIN_FILES_SHA256.txt missing")

# ---------------------------------------------------------------- 5 tables match the frozen package
tb_mism = []
for src in (CF / "tables").iterdir():
    dst = OUT / "tables" / src.name
    if not dst.exists() or sha(dst) != sha(src):
        tb_mism.append(src.name)
ck("every table is byte-identical to the frozen package", not tb_mism, tb_mism)

# ---------------------------------------------------------------- 6 link integrity
EXT = (".md", ".png", ".pdf", ".csv", ".json", ".sh", ".py", ".txt", ".yml", ".yaml")
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def looks_like_path(t: str) -> bool:
    if t.startswith(("http://", "https://", "#", "mailto:", "<")):
        return False
    t = t.split("#")[0].strip()
    if not t or not t.endswith(EXT):
        return False
    return not any(ch in t for ch in "^$`{} \\")


ck("release contains no symlinks at all",
   not any(p.is_symlink() for p in OUT.rglob("*")),
   [str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_symlink()][:5])

NAR = OUT / "narrative"
bad_links, n_checked, n_fig = [], 0, 0
for md in sorted(NAR.rglob("*.md")):
    t = md.read_text(encoding="utf-8")
    for m in LINK.finditer(t):
        raw = m.group(1).strip()
        if not looks_like_path(raw):
            continue
        n_checked += 1
        rel = raw.split("#")[0].strip()
        if rel.startswith("../figures/"):
            n_fig += 1
        if not (md.parent / rel).exists():
            bad_links.append(f"{md.relative_to(OUT)} -> {rel}")
ck("every relative reference in the narrative documents resolves",
   not bad_links, f"{n_checked} checked, {len(bad_links)} broken: {bad_links[:4]}")
ck("the figure links inside the narrative documents resolve (they were dead before the fix)",
   n_fig > 0 and not [b for b in bad_links if "figures" in b],
   f"{n_fig} figure links checked")

# ---------------------------------------------------------------- 7 reproduction README
rep = OUT / "reproduction"
if rep.exists():
    import numpy as np
    rows = []
    for name, desc in (("P42_arrays/arrays.npz",
                        "选定预测样本 P42 的 GT / TerraState-C1 / Persistence / 掩码 / 上下文"),
                       ("P42_official_baselines.npz",
                        "P42 上官方 GreenEarthNet 基线的预测（原文件名 P42.npz，为可读性改名）"),
                       ("W02_arrays/W02", "选定天气案例 W02 的 actual / donor / mean 三种情景预测")):
        p = rep / name
        if p.exists():
            rows.append((name, f"{p.stat().st_size:,} B", desc))
        elif p.is_dir() or (rep / (name + "/arrays.npz")).exists():
            q = rep / (name + "/arrays.npz")
            rows.append((name + "/arrays.npz", f"{q.stat().st_size:,} B", desc))
    md = ["# reproduction — 复现数组", "",
          "本目录只放**终稿实际使用**的样本数组，用于重画图或复核数字。", "",
          "| 文件 | 大小 | 内容 |", "|---|---:|---|"]
    for a, b, c in rows:
        md.append(f"| `{a}` | {b} | {c} |")
    md += ["", "## 两种数组的形状", "",
           "`P42_arrays/arrays.npz`（预测）：", "", "```",
           "gt            (20, 128, 128)  真实 NDVI，官方 20 个五日步",
           "c1            (20, 128, 128)  TerraState-C1 预测",
           "persistence   (20, 128, 128)  持续性基线（复现，非推理）",
           "valid         (20, 128, 128)  有效像素掩码（云 / 非植被 / 缺测为 0）",
           "context       (10, 128, 128)  上下文 NDVI",
           "context_valid (10, 128, 128)  上下文掩码",
           "landcover     (128, 128)      esawc 地类",
           "```", "",
           "`W02_arrays/arrays.npz`（天气）：`gt / valid / pred_actual / pred_donor / pred_mean /",
           "weather_actual / weather_donor / weather_mean`。", "",
           "> `donor` 与 `mean` 是**反事实情景**：没有观测真值，只能说明模型会预测什么。",
           "", "## 候选清单（不在此目录的数组）", "",
           "`PREDICTION_CANDIDATES_60.csv`（60 个预测候选）、`PREDICTION_CANDIDATE_METRICS_60.csv`、",
           "`MECHANISM_CANDIDATES_16.csv`（16 个机制候选）、`WEATHER_CANDIDATES_12.csv`（12 个天气候选）",
           "只给出**清单与指标**；对应的逐样本数组保留在运行目录", 
           "`first_dataset_figures_final_20260913T052645Z/图*/data/_arrays/`（约 273 MiB），",
           "如需重画其它候选，从那里取。", ""]
    (rep / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("wrote reproduction/README.md")

# ---------------------------------------------------------------- 7 write SHA256SUMS
files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"
               and p.name != "QA_REPORT.md")
lines = ["# SHA256SUMS — first_dataset_20260913",
         f"# generated {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
         "# paths are relative to this directory; verify with:  sha256sum -c SHA256SUMS.txt",
         "#"]
for p in files:
    lines.append(f"{sha(p)}  {p.relative_to(OUT)}")
(OUT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
ck("SHA256SUMS.txt written", True, f"{len(files)} entries")

# ---------------------------------------------------------------- 7 QA report
n_all, b_all = tree(OUT)
n_fail = sum(1 for c in checks if c[1] == "FAIL")
qa = ["# QA_REPORT — first_dataset_20260913", "",
      "对本发布包做的机械验收。所有检查都重新读盘，不依赖任何先前结论。", "",
      "| 检查 | 结果 | 细节 |", "|---|---|---|"]
for n, s, d in checks:
    qa.append(f"| {n} | {s} | {d} |")
qa += ["", f"**合计 {len(checks)} 项，FAIL {n_fail} 项。**", "",
       "## 包概况", "",
       f"- 文件数：**{n_all}**",
       f"- 总大小：**{b_all / 1048576:.1f} MiB**",
       f"- 最大文件：{max((p for p in OUT.rglob('*') if p.is_file()), key=lambda p: p.stat().st_size).relative_to(OUT)}",
       "", "## 已知限制（如实记录）", "",
       "1. **权重不在包内**：仓库配置 Git LFS 而服务器未装 git-lfs，"
       "提交权重只会产生 133 字节指针。四个正式权重的路径、字节数与实测 SHA256 见 `WEIGHTS.md`。",
       "2. **图7 的四个 per-cube CSV 占 46 MiB**（`ood_s` 20.1 + `ood_st` 15.4 + `iid` 6.1 + `ood_t` 4.6 MiB）。"
       "它们是逐 receiver × 逐时距的原始证据，是 Table 6B 可直接复核的底座，因此保留而未压缩；"
       "若仓库体积敏感，可改为 `.csv.gz`（读取方 `pandas.read_csv` 可直接识别）。",
       "3. **候选图库未收录**：60 个预测候选与 12 个天气候选只保留终稿实际使用的 P42 / W02；"
       "完整候选图库仍在运行目录 `first_dataset_showcase_20260912T062326Z`。",
       "4. **基线的空间预测文件在本服务器不可用**（官方权重与导出的预测都不在盘上），"
       "因此图件中的对比模型只有 Ground truth / Persistence / TerraState-C1；基线数值仍在 Table 1。",
       "5. `narrative/figure references` 与 `figures/` 之间存在少量同名图片的重复（约 5 MiB），"
       "为保持两份主文可独立阅读而刻意保留。", ""]
(OUT / "QA_REPORT.md").write_text("\n".join(qa) + "\n", encoding="utf-8")

for n, s, d in checks:
    print(f"{s}  {n}")
    if s == "FAIL" and d:
        print(f"      {d}")
print(f"\nQA: {len(checks)} checks, {n_fail} FAIL")
print(f"package: {n_all} files, {b_all / 1048576:.1f} MiB")
sys.exit(1 if n_fail else 0)
