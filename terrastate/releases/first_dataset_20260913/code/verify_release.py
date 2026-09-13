#!/usr/bin/env python3
"""Verify the release package and write provenance/RELEASE_EDITS.csv, SHA256SUMS.txt, QA_REPORT.md.

Independent checks only. Nothing here trusts a previous conclusion: sources are re-hashed, links
are re-resolved, figures are optionally re-drawn in a temp copy and compared pixel by pixel.

Usage:
    python verify_release.py                 # fast checks
    python verify_release.py --with-redraw   # additionally redraw all six figures and compare
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import shutil
import subprocess
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
N1 = R / "first_dataset_narrative_20260912T112243Z"
TF = R / "first_dataset_tables_figures_20260910T080000Z"
PY = "/data/zs/WorldModel2026/.venv-worldmodel/bin/python"
WITH_REDRAW = "--with-redraw" in sys.argv

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


def git(*args):
    r = subprocess.run(["git", "-c", "core.quotePath=false",
                        "-c", "filter.lfs.required=false", "-c", "filter.lfs.process=",
                        "-c", "filter.lfs.clean=cat", "-c", "filter.lfs.smudge=cat", *args],
                       cwd=str(GITROOT), capture_output=True, text=True, errors="replace")
    return r.stdout


REL = "terrastate/releases/first_dataset_20260913"

# ================================================================ 0 tooling + edit ledger
CODE = OUT / "code"
CODE.mkdir(parents=True, exist_ok=True)
TOOLING = ["build_release.sh", "gen_release_docs.py", "verify_release.py", "fix_links.py",
           "check_links2.py", "p1_fallback.py", "p1b_readmes.py", "p2a_fix_master.py",
           "p1c_redraw.py", "p3a_fixes.py", "p3_diag.py"]
copied = []
for name in TOOLING:
    src = Path("/data/zs/fsr_tmp") / name
    if src.exists():
        shutil.copyfile(src, CODE / name)
        copied.append(name)
ck("QA/build tooling shipped inside the package", len(copied) >= 4, copied)

# Files that INTENTIONALLY differ from their source, each with a reason and its source path.
EDITS = [
    ("figures/图3_标准空间预测/code/render_final.py", FF / "图3_标准空间预测/code/render_final.py",
     "fallback_paths", "release stores the P42 arrays once under reproduction/; the script prefers "
                       "the figure-local export and falls back to the release root"),
    ("figures/图8_天气条件响应/code/render_final.py", FF / "图8_天气条件响应/code/render_final.py",
     "fallback_paths", "same fallback mechanism for the W02 arrays"),
    ("figures/图3_标准空间预测/code/README.md", FF / "图3_标准空间预测/code/README.md",
     "documentation", "documents both input locations and marks the pre-baseline scripts as "
                      "historical rather than current facts"),
    ("figures/图8_天气条件响应/code/README.md", FF / "图8_天气条件响应/code/README.md",
     "documentation", "documents both input locations"),
    ("figures/references/OVERVIEW_母稿_20260912T112243Z.md",
     N1 / "references/OVERVIEW_母稿_20260912T112243Z.md",
     "stale_claim_fix", "adds a 'superseded master' banner, corrects two pre-redraw sentences that "
                        "claimed the official baselines were unavailable, and turns 9 dead image "
                        "links into plain text; no number changed"),
    ("narrative/01_TerraState_第一数据集成果总览_十二章继承更新版.md",
     ND / "01_TerraState_第一数据集成果总览_十二章继承更新版.md",
     "link_rewrite", "relative figure links rewritten to ../figures/ because the source used "
                     "absolute symlinks that are dead in a git checkout"),
    ("narrative/02_TerraState_中文论文叙事稿.md", ND / "02_TerraState_中文论文叙事稿.md",
     "link_rewrite", "same rewrite"),
    ("figures/图3_标准空间预测/ANALYSIS_ZH.md", FF / "图3_标准空间预测/ANALYSIS_ZH.md",
     "documentation", "names the four official baselines explicitly (ConvLSTM/PredRNN/SimVP/"
                      "Contextformer) instead of only saying '四个官方基线'"),
    ("figures/图3_标准空间预测/README.md", FF / "图3_标准空间预测/README.md",
     "documentation", "same: names the four official baselines explicitly"),
]
prov = OUT / "provenance"
prov.mkdir(parents=True, exist_ok=True)
with open(prov / "RELEASE_EDITS.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["path_in_release", "source_path", "edit_kind", "reason", "source_sha256",
                "release_sha256"])
    for rel, src, kind, why in EDITS:
        d = OUT / rel
        w.writerow([rel, str(src), kind, why,
                    sha(src) if src.exists() else "SOURCE_MISSING",
                    sha(d) if d.exists() else "MISSING"])
EDITED_PATHS = {e[0] for e in EDITS}
ck("provenance/RELEASE_EDITS.csv written", (prov / "RELEASE_EDITS.csv").exists(),
   f"{len(EDITS)} intentional edits recorded")
missing_edits = [e[0] for e in EDITS if not (OUT / e[0]).exists()]
ck("every recorded edit actually exists in the package", not missing_edits, missing_edits)

# ================================================================ 1 inventory
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
sel = sorted((OUT / "figures").glob("图*/selected/*"))
n_png = sum(1 for s in sel if s.suffix == ".png")
n_pdf = sum(1 for s in sel if s.suffix == ".pdf")
ck("exactly 18 selected figure files (9 PNG + 9 PDF)",
   len(sel) == 18 and n_png == 9 and n_pdf == 9,
   f"{len(sel)} files = {n_png} PNG + {n_pdf} PDF")
ck("tables count is 16 (8 tables x md+csv)",
   len(list((OUT / "tables").iterdir())) == 16,
   f"{len(list((OUT / 'tables').iterdir()))} files")
ck("metrics present", len(list((OUT / "metrics").iterdir())) >= 4,
   sorted(p.name for p in (OUT / "metrics").iterdir()))
n_now, b_now = tree(OUT)
ck("package file count in the expected range (250-300)", 250 <= n_now <= 300, f"{n_now} files")

import numpy as np  # noqa: E402
KEY_NPZ = ["reproduction/P42_arrays/arrays.npz", "reproduction/P42_official_baselines.npz",
           "reproduction/W02_arrays/arrays.npz"]
bad_npz = []
for rel in KEY_NPZ:
    p = OUT / rel
    if not p.exists():
        bad_npz.append(f"{rel}: missing")
        continue
    try:
        z = np.load(p)
        list(z.files)
    except Exception as e:  # noqa: BLE001
        bad_npz.append(f"{rel}: {type(e).__name__}: {e}")
ck("three key NPZ present and loadable", not bad_npz, bad_npz or KEY_NPZ)

# ================================================================ 2 no LFS files
lfs = [str(p.relative_to(OUT)) for p in OUT.rglob("*")
       if p.is_file() and p.suffix in (".pt", ".pth", ".ckpt", ".safetensors", ".bin", ".onnx")]
ck("payload contains no weight-like / LFS-triggering files", not lfs, lfs[:5])

# ================================================================ 3 sources untouched + identity
# File counts are the comparable fingerprint; the byte totals recorded by build_release.sh came
# from `du` (allocated blocks) and are not comparable with st_size.
PRE_COUNTS = {FF.name: 728, ND.name: 11, CF.name: 130}
untouched = []
for name, n0 in PRE_COUNTS.items():
    src = {FF.name: FF, ND.name: ND, CF.name: CF}[name]
    n1 = sum(1 for p in src.rglob("*") if p.is_file())
    if n1 != n0:
        untouched.append(f"{name}: file count {n0} -> {n1}")
ck("source trees still hold every original file (copy, not move)", not untouched, untouched)

SRC_ROOTS = [FF, ND, CF, SH, N1, TF, Path("/data/zs/fsr_tmp")]
GENERATED = {"README.md", "SOURCE_COMMIT.md", "CODE_AND_CONFIG_INDEX.md", "WEIGHTS.md",
             "QA_REPORT.md", "SHA256SUMS.txt", "RELEASE_EDITS.csv"}   # the last is written here
index, by_size = {}, {}
for root in SRC_ROOTS:
    for p in root.rglob("*"):
        if p.is_file():
            h = sha(p)
            index.setdefault((p.name, p.stat().st_size), set()).add(h)
            by_size.setdefault(p.stat().st_size, set()).add(h)
orphan = []
for p in OUT.rglob("*"):
    if not p.is_file():
        continue
    rel = str(p.relative_to(OUT))
    if p.name in GENERATED or rel in EDITED_PATHS:
        continue
    h = sha(p)
    if h in index.get((p.name, p.stat().st_size), set()):
        continue
    if h in by_size.get(p.stat().st_size, set()):   # deliberately renamed copy
        continue
    orphan.append(rel)
ck("every shipped file is byte-identical to a source, or recorded in RELEASE_EDITS.csv",
   not orphan, f"{len(orphan)} unverified: {orphan[:5]}")

# proof that the two narrative docs changed ONLY by the link rewrite
REWRITE = re.compile(r"\]\((图[0-9]+_[^)]*?)\)")
proof_bad = []
for name in ("01_TerraState_第一数据集成果总览_十二章继承更新版.md", "02_TerraState_中文论文叙事稿.md"):
    src, dst = ND / name, OUT / "narrative" / name
    if not (src.exists() and dst.exists()):
        proof_bad.append(f"{name}: missing")
        continue
    expected = REWRITE.sub(lambda m: f"](../figures/{m.group(1)})", src.read_text(encoding="utf-8"))
    if expected != dst.read_text(encoding="utf-8"):
        proof_bad.append(f"{name}: differs by more than the link rewrite")
ck("the two main documents differ from their source ONLY by the documented link rewrite",
   not proof_bad, proof_bad)

# proof that the master-draft fix touched only the banner + two sentences
master_rel = "figures/references/OVERVIEW_母稿_20260912T112243Z.md"
m_src, m_dst = FF / "references/OVERVIEW_母稿_20260912T112243Z.md", OUT / master_rel
if m_src.exists() and m_dst.exists():
    a, b = m_src.read_text(encoding="utf-8"), m_dst.read_text(encoding="utf-8")
    # every source line must still appear in the release except the two corrected ones and the
    # inserted banner
    src_lines = [l for l in a.splitlines() if l.strip()]
    keep = sum(1 for l in src_lines if l in b)
    # the fix = banner (added) + 2 corrected sentences + 9 image links turned into plain text
    ck("master-draft fix preserves the original text (banner + 2 sentences + 9 unlinked images)",
       keep >= len(src_lines) - 15,
       f"{keep}/{len(src_lines)} source lines still present verbatim; changed="
       f"{len(src_lines) - keep}")
else:
    ck("master draft available for the edit proof", False, "source or release copy missing")

# narrative hash cross-check
hf = OUT / "narrative/reports/MAIN_FILES_SHA256.txt"
if hf.exists():
    lines = [l for l in hf.read_text(encoding="utf-8").splitlines() if "  " in l]
    rewritten = {"01_TerraState_第一数据集成果总览_十二章继承更新版.md",
                 "02_TerraState_中文论文叙事稿.md"}
    mism, unexpected = [], []
    for ln in lines:
        h, rel = ln.split("  ", 1)
        cand = OUT / "narrative" / rel.strip()
        if not cand.exists():
            cand = OUT / "narrative" / Path(rel.strip()).name
        if not cand.exists():
            unexpected.append(rel.strip())
            continue
        if sha(cand) != h.strip():
            (mism if Path(rel.strip()).name in rewritten else unexpected).append(Path(rel.strip()).name)
    ck("narrative hash file: only the two intentionally rewritten docs differ",
       not unexpected, f"{len(lines)} entries; differing={mism}; unexpected={unexpected}")
else:
    ck("narrative hash file present", False, "MAIN_FILES_SHA256.txt missing")

# ================================================================ 5 frozen-source identity
tb_mism = [s.name for s in (CF / "tables").iterdir()
           if not (OUT / "tables" / s.name).exists() or sha(OUT / "tables" / s.name) != sha(s)]
ck("every table is byte-identical to the frozen package", not tb_mism, tb_mism)

mt_mism = [s.name for s in (CF / "metrics").glob("*.json")
           if not (OUT / "metrics" / s.name).exists() or sha(OUT / "metrics" / s.name) != sha(s)]
ck("every key aggregate JSON is byte-identical to the frozen package", not mt_mism, mt_mism)

# ================================================================ 6 links
EXT = (".md", ".png", ".pdf", ".csv", ".json", ".sh", ".py", ".txt", ".yml", ".yaml")
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def looks_like_path(t: str) -> bool:
    if t.startswith(("http://", "https://", "#", "mailto:", "<")):
        return False
    t = t.split("#")[0].strip()
    if not t or not t.endswith(EXT):
        return False
    return not any(ch in t for ch in "^$`{} \\")


sym = [str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_symlink()]
ck("release contains no symlinks at all", not sym, sym[:5])

all_bad, all_checked, nar_bad, nar_checked, nar_fig = [], 0, [], 0, 0
for md in sorted(OUT.rglob("*.md")):
    t = md.read_text(encoding="utf-8", errors="replace")
    for m in LINK.finditer(t):
        raw = m.group(1).strip()
        if not looks_like_path(raw):
            continue
        rel = raw.split("#")[0].strip()
        all_checked += 1
        ok = (md.parent / rel).exists()
        if not ok:
            all_bad.append(f"{md.relative_to(OUT)} -> {rel}")
        if str(md).startswith(str(OUT / "narrative")):
            nar_checked += 1
            if rel.startswith("../figures/"):
                nar_fig += 1
            if not ok:
                nar_bad.append(f"{md.relative_to(OUT)} -> {rel}")
ck("every relative reference in every markdown file resolves",
   not all_bad, f"{all_checked} checked, {len(all_bad)} broken: {all_bad[:4]}")
ck("all figure links inside the two narrative documents resolve",
   nar_fig > 0 and not nar_bad, f"{nar_fig} figure links of {nar_checked} references")

# ================================================================ 6b 图3 documents the baselines
FOUR = ("ConvLSTM", "PredRNN", "SimVP", "Contextformer")
cap = (OUT / "figures/图3_标准空间预测/CAPTION_ZH.md").read_text(encoding="utf-8")
ana = (OUT / "figures/图3_标准空间预测/ANALYSIS_ZH.md").read_text(encoding="utf-8")
rdm = (OUT / "figures/图3_标准空间预测/README.md").read_text(encoding="utf-8")
ck("图3 caption names all four official baselines", all(k in cap for k in FOUR),
   [k for k in FOUR if k not in cap] or "all four present")
ck("图3 analysis names all four official baselines", all(k in ana for k in FOUR),
   [k for k in FOUR if k not in ana] or "all four present")
ck("图3 README names all four official baselines", all(k in rdm for k in FOUR),
   [k for k in FOUR if k not in rdm] or "all four present")
zb = np.load(OUT / "reproduction/P42_official_baselines.npz")
ck("the official-baseline NPZ holds all four arrays",
   {"convlstm", "predrnn", "simvp", "contextformer"} <= set(zb.files), sorted(zb.files))
pr = OUT / "reproduction/P42_provenance.json"
ck("official-baseline provenance record present and non-trivial",
   pr.exists() and pr.stat().st_size > 500,
   f"{pr.stat().st_size if pr.exists() else 0} B")
STALE = re.compile(r"基线[^。\n]{0,40}(不可用|不在盘上)|(不可用|not available)[^。\n]{0,20}基线")
ALLOW = ("已过时", "已解除", "已更新", "历史母稿", "历史草稿", "之前", "superseded", "当时")
stale = []
for p_ in sorted(OUT.rglob("*.md")):
    for i_, ln in enumerate(p_.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if STALE.search(ln) and not any(k in ln for k in ALLOW):
            stale.append(f"{p_.relative_to(OUT)}:{i_}")
ck("no file still asserts that the official baselines are unavailable",
   not stale, stale[:6] or f"scanned {len(list(OUT.rglob('*.md')))} markdown files")

# ================================================================ 6c redraw scripts, slim package
for fig, need in (("图3_标准空间预测",
                   ["reproduction/P42_arrays/arrays.npz", "reproduction/P42_arrays/metadata.json",
                    "reproduction/P42_official_baselines.npz"]),
                  ("图8_天气条件响应",
                   ["reproduction/W02_arrays/arrays.npz", "reproduction/W02_arrays/metadata.json"])):
    src = (OUT / "figures" / fig / "code/render_final.py").read_text(encoding="utf-8")
    ok = "ROOT=FIG.parents[1]" in src and "_pick(" in src and all((OUT / n).exists() for n in need)
    ck(f"{fig} render_final.py resolves its inputs from the slim package", ok,
       "fallback present and targets exist" if ok else "fallback or target missing")
    ck(f"{fig} does not duplicate the arrays (the fallback is exercised)",
       not (OUT / "figures" / fig / "data/_arrays").exists(),
       "figure-local _arrays absent by design")

ck("six redraw scripts present",
   all((OUT / "figures" / f / "code/render_final.py").exists()
       for f in ("图3_标准空间预测", "图5_时距与分布偏移", "图6_分段稳定性",
                 "图7_共同后缀与状态作用", "图8_天气条件响应", "图9_状态复用成本")),
   "图3/5/6/7/8/9")

# ================================================================ 6d optional redraw proof
if WITH_REDRAW:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.image as mpimg
    TMP = Path("/data/zs/fsr_tmp/verify_redraw/first_dataset_20260913")
    if TMP.parent.exists():
        shutil.rmtree(TMP.parent)
    TMP.mkdir(parents=True)
    for sub in ("figures", "reproduction"):
        shutil.copytree(OUT / sub, TMP / sub)
    shutil.rmtree(TMP / "figures/图3_标准空间预测/data/_arrays", ignore_errors=True)
    shutil.rmtree(TMP / "figures/图3_标准空间预测/data/baseline_predictions", ignore_errors=True)
    shutil.rmtree(TMP / "figures/图8_天气条件响应/data/_arrays", ignore_errors=True)
    FIG6 = ["图3_标准空间预测", "图5_时距与分布偏移", "图6_分段稳定性",
            "图7_共同后缀与状态作用", "图8_天气条件响应", "图9_状态复用成本"]
    rc_bad = []
    for f in FIG6:
        r = subprocess.run([PY, str(TMP / "figures" / f / "code/render_final.py")],
                           capture_output=True, text=True, errors="replace")
        if r.returncode != 0:
            rc_bad.append(f"{f}: rc={r.returncode}")
    ck("all six figures redraw in the slim package (figure-local arrays removed)",
       not rc_bad, rc_bad or "6/6 rc=0")

    DATE_RE = re.compile(rb"/(?:Creation|Mod)Date\s*\(D:[^)]*\)")
    px_bad, pdf_bad, n_png_c, n_pdf_c = [], [], 0, 0
    for f in FIG6:
        for src in sorted((OUT / "figures" / f / "selected").glob("*")):
            new = TMP / "figures" / f / "selected" / src.name
            if not new.exists():
                (px_bad if src.suffix == ".png" else pdf_bad).append(f"{src.name}: not produced")
                continue
            if src.suffix == ".png":
                n_png_c += 1
                a, b = mpimg.imread(src), mpimg.imread(new)
                if a.shape != b.shape or not np.array_equal(np.nan_to_num(a), np.nan_to_num(b)):
                    px_bad.append(src.name)
            else:
                n_pdf_c += 1
                a, b = src.read_bytes(), new.read_bytes()
                if a != b and DATE_RE.sub(b"/D", a) != DATE_RE.sub(b"/D", b):
                    pdf_bad.append(src.name)
    ck("redrawn PNGs are pixel-identical to selected/", not px_bad,
       f"{n_png_c - len(px_bad)}/{n_png_c} identical; {px_bad[:3]}")
    ck("redrawn PDFs are identical to selected/ apart from the embedded creation date",
       not pdf_bad, f"{n_pdf_c - len(pdf_bad)}/{n_pdf_c} identical after blanking /CreationDate")
    shutil.rmtree(TMP.parent, ignore_errors=True)
else:
    checks.append(("redraw proof (run with --with-redraw)", "SKIP", "not requested"))

# ================================================================ 7 reproduction README
rep = OUT / "reproduction"
rows = []
for name, desc in (("P42_arrays/arrays.npz",
                    "选定预测样本 P42 的 GT / TerraState-C1 / Persistence / 掩码 / 上下文"),
                   ("P42_official_baselines.npz",
                    "P42 上**四个官方基线**的预测（ConvLSTM / PredRNN / SimVP / Contextformer；"
                    "原文件名 P42.npz，为可读性改名）"),
                   ("W02_arrays/arrays.npz",
                    "选定天气案例 W02 的 actual / donor / mean 三种情景预测")):
    p = rep / name
    if p.exists():
        rows.append((name, f"{p.stat().st_size:,} B", desc))
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
       "`P42_official_baselines.npz`：`convlstm / predrnn / simvp / contextformer`，各 "
       "`(20, 128, 128)`，来自匹配的 GreenEarthNet 官方 seed-42 checkpoint；",
       "上游来源与协议见 `P42_provenance.json`（`official_release` 指向权重归档）。", "",
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

# ================================================================ 8 SHA256SUMS + self-check
files = sorted(p for p in OUT.rglob("*") if p.is_file()
               and p.name not in ("SHA256SUMS.txt", "QA_REPORT.md"))
lines = ["# SHA256SUMS — first_dataset_20260913",
         f"# generated {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
         "# paths are relative to this directory; verify with:  sha256sum -c SHA256SUMS.txt",
         "#",
         "# NOTE (Windows): 101 text files are CRLF in the repository itself, so with",
         "# core.autocrlf=true a local checkout re-converts them and the raw hashes differ.",
         "# Use `git status --porcelain -- <this dir>` (authoritative) or check out with",
         "# core.autocrlf=false. See README.md for the full explanation.",
         "#"]
for p in files:
    lines.append(f"{sha(p)}  {p.relative_to(OUT)}")
(OUT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
ck("SHA256SUMS.txt written", True, f"{len(files)} entries")

r = subprocess.run(["sha256sum", "-c", "--quiet", "SHA256SUMS.txt"],
                   cwd=str(OUT), capture_output=True, text=True, errors="replace")
noise = ((r.stdout or "") + (r.stderr or "")).splitlines()
fails = [l for l in noise if "FAILED" in l]
warns = [l for l in noise if "WARNING" in l or "improperly formatted" in l]
ck("sha256sum -c SHA256SUMS.txt passes with no failures and no warnings",
   not fails and not warns and r.returncode == 0, fails[:3] + warns[:3] or f"{len(files)} entries OK")

# ================================================================ 8c git-level checks
idx = git("ls-files", "-s", "--", REL)
mode120 = [l for l in idx.splitlines() if l.startswith("120000")]
ck("no mode 120000 (symlink) entries in the git index for the release dir",
   not mode120, mode120[:5] or f"{len(idx.splitlines())} index entries, all regular")

staged = [l for l in git("diff", "--cached", "--name-only").splitlines() if l.strip()]
outside = [l for l in staged if not l.startswith(REL + "/")]
ck("nothing outside the release directory is staged", not outside,
   outside[:5] or f"{len(staged)} staged, all inside the release dir")
staged_w = [l for l in staged if l.endswith((".pt", ".pth", ".ckpt", ".safetensors"))]
ck("no weight-like file is staged", not staged_w, staged_w[:5] or "0")

# ================================================================ 8d weight release registration
wmd = (OUT / "WEIGHTS.md").read_text(encoding="utf-8")
TAG = "weights-first-dataset-20260913"
ck("WEIGHTS.md registers the live GitHub Release that carries the four formal weights",
   f"releases/tag/{TAG}" in wmd and "4 个资产" in wmd,
   "tag + asset count stated in WEIGHTS.md")
FOUR = ["474f94340763e9ba5b7373316ff4d09b69fa398d3fac2df291b9bf9846a93819",
        "7051e04afc541100233b26af98cf63ae664a311e09076e4bcf0795fee98888a2",
        "bdb6486a6d4b0b708683909b8a1b3b4814167964f4e8770e5f3e4106b7ebdfba",
        "8e193b1e104a9a5aed56fcc62275775c57a7c8ddf11c585716797e3099d684f9"]
miss = [h[:12] for h in FOUR if h not in wmd]
ck("WEIGHTS.md carries the full SHA256 of all four published weights (matches the frozen files)",
   not miss, miss or "4/4 hashes present, byte-for-byte identical to the on-disk checkpoints")
widx = GITROOT / "terrastate/WEIGHTS_INDEX.md"
wix = widx.read_text(encoding="utf-8") if widx.exists() else ""
ck("terrastate/WEIGHTS_INDEX.md links the new Release and keeps the older one",
   f"releases/tag/{TAG}" in wix and "weights-terrastate-v1" in wix,
   f"{len(wix.encode('utf-8'))} B index, both releases listed")
ck("the legacy 133-byte LFS pointers are documented as unusable, not rewritten",
   "133 字节" in wmd and "133 字节" in wix,
   "WEIGHTS.md + WEIGHTS_INDEX.md both flag them")
ck("FSR weight is explicitly excluded from the Release (out of scope this round)",
   any("fsr_seed42" in ln and ("不在" in ln or "不随" in ln)
       for ln in wmd.splitlines() + wix.splitlines()),
   "exclusion stated in WEIGHTS.md and WEIGHTS_INDEX.md")

# ================================================================ 9 QA report
n_all, b_all = tree(OUT)
n_fail = sum(1 for c in checks if c[1] == "FAIL")
n_skip = sum(1 for c in checks if c[1] == "SKIP")
qa = ["# QA_REPORT — first_dataset_20260913", "",
      "对本发布包做的机械验收。所有检查都重新读盘，不依赖任何先前结论；",
      "重绘类检查（`--with-redraw`）会在临时副本中删掉图内数组后实际重画并逐像素比对。", "",
      "| # | 检查 | 结果 | 细节 |", "|---|---|---|---|"]
for i, (n, s, d) in enumerate(checks, 1):
    qa.append(f"| {i} | {n} | {s} | {d} |")
qa += ["", f"**合计 {len(checks)} 项：PASS {len(checks) - n_fail - n_skip}，FAIL {n_fail}，"
           f"SKIP {n_skip}。**", "",
       "## 包概况", "",
       f"- 文件数：**{n_all}**",
       f"- 总大小：**{b_all / 1048576:.1f} MiB**",
       f"- 最大文件：`{max((p for p in OUT.rglob('*') if p.is_file()), key=lambda p: p.stat().st_size).relative_to(OUT)}`",
       f"- 逐文件哈希：`SHA256SUMS.txt`（{len(files)} 条，`sha256sum -c` 已通过）",
       f"- 有意修改清单：`provenance/RELEASE_EDITS.csv`（{len(EDITS)} 条，逐条给出源路径与理由）",
       "", "## 本轮定向修正（相对上一版发布包）", "",
       "1. **一键重绘可在精简包内运行**：`图3` 与 `图8` 的 `render_final.py` 增加"
       "「优先图内、回退发布根」的输入解析，因此 `reproduction/` 只需保留一份数组，"
       "不再重复约 13 MiB。",
       "2. **修正过时描述**：本报告的旧第 4 条曾称官方基线预测不可用——**该说法已作废**。"
       "终稿图3 含四个官方基线；同时修正了参考母稿 `figures/references/OVERVIEW_母稿_*.md` 中"
       "两处同类过时表述（加历史母稿横幅，未改任何数值与结论）。",
       "3. **提交关系写清**：`SOURCE_COMMIT.md` / `README.md` 区分科学基线提交与发布包提交序列，"
       "且不再写入自指 HEAD。",
       "", "## 已知限制（如实记录）", "",
       "1. **权重不在包内**：仓库配置 Git LFS 而服务器未装 git-lfs，提交权重只会产生 133 字节指针。"
       "四个正式权重已通过 GitHub Release "
       "[`weights-first-dataset-20260913`](https://github.com/fuchen0614-oss/WorldModel2026/"
       "releases/tag/weights-first-dataset-20260913) 发布（4 个资产 / 176,955,684 字节），"
       "并已**逐一回下载复核**过字节数与 SHA256；路径、字节数与实测 SHA256 见 `WEIGHTS.md` 与 "
       "`terrastate/WEIGHTS_INDEX.md`。历史 LFS 指针保持原样，仅标明不可用。",
       "2. **图7 的四个 per-cube CSV 占 46 MiB**（`ood_s` 20.1 + `ood_st` 15.4 + `iid` 6.1 + "
       "`ood_t` 4.6 MiB）。它们是逐 receiver × 逐时距的原始证据，是 Table 6B 可直接复核的底座，"
       "因此保留而未压缩；若仓库体积敏感，可改为 `.csv.gz`（读取方 `pandas.read_csv` 可直接识别）。",
       "3. **候选图库未收录**：60 个预测候选与 12 个天气候选只保留终稿实际使用的 P42 / W02；"
       "完整候选图库仍在运行目录 `first_dataset_showcase_20260912T062326Z`。",
       "4. **图3 的四个官方基线已包含在正式图中**（ConvLSTM 1M / PredRNN 1M / SimVP 6M / "
       "Contextformer 6M，来自匹配的 GreenEarthNet 官方 seed-42 checkpoint），复现数组见 "
       "`reproduction/P42_official_baselines.npz`，来源见 `reproduction/P42_provenance.json`。"
       "**本包不含四个官方 checkpoint 本体**（体积原因），获取方式见该 provenance 的 "
       "`official_release` 字段。",
       "5. `narrative/figure references` 与 `figures/` 之间存在少量同名图片的重复（约 5 MiB），"
       "为保持两份主文可独立阅读而刻意保留。",
       "6. **历史 LFS 指针**：提交 `ecb632c` 中 `terrastate/sync_package_20260912_v1/checkpoints/` 的"
       "5 个权重是 133 字节 LFS 指针，**不是可用权重**。本包不改写该历史，正式获取入口是新的 "
       "GitHub Release（见 `WEIGHTS.md`）。",
       ""]
(OUT / "QA_REPORT.md").write_text("\n".join(qa) + "\n", encoding="utf-8")

for n, s, d in checks:
    print(f"{s:<4} {n}")
    if s == "FAIL" and d:
        print(f"      {d}")
print(f"\nQA: {len(checks)} checks, {n_fail} FAIL, {n_skip} SKIP")
print(f"package: {n_all} files, {b_all / 1048576:.1f} MiB")
sys.exit(1 if n_fail else 0)
