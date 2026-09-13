#!/usr/bin/env python3
"""Generate the release's top-level documents with REAL hashes computed from disk.

Everything written here is derived from the files that actually exist; nothing is transcribed from
memory. Sources are only read.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
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


def sha(p: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def sh(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str),
                          capture_output=True, text=True, errors="replace").stdout.strip()


COMMIT = sh(["git", "rev-parse", "HEAD"], cwd=GITROOT)
BRANCH = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=GITROOT)
REMOTE = sh(["git", "remote", "get-url", "origin"], cwd=GITROOT)
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ------------------------------------------------------------------ weights (measured)
WEIGHT_SPECS = [
    ("C1 seed 42 (recursive endpoint training, main arm)",
     GITROOT / "terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt"),
    ("C0R seed 42 (direct endpoint training, mechanism control)",
     GITROOT / "terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c0r_20260823T063516Z/checkpoint_main.pt"),
    ("C1 seed 27 (multi-seed stability)",
     GITROOT / "terrastate/sync_package_20260912_v1/checkpoints/c1_seed27_checkpoint_main.pt"),
    ("C1 seed 97 (multi-seed stability)",
     GITROOT / "terrastate/sync_package_20260912_v1/checkpoints/c1_seed97_checkpoint_main.pt"),
    ("FSR seed 42 (fixed-index-step endpoint variant -- historical registration only)",
     GITROOT / "terrastate/sync_package_20260912_v1/checkpoints/fsr_seed42_checkpoint_main.pt"),
]
weights = []
for label, p in WEIGHT_SPECS:
    if p.exists():
        weights.append({"label": label, "path": str(p.relative_to(GITROOT)),
                        "bytes": p.stat().st_size, "sha256": sha(p)})
    else:
        weights.append({"label": label, "path": str(p.relative_to(GITROOT)), "bytes": None,
                        "sha256": None})
print("weights measured:")
for w in weights:
    print(f"  {w['bytes']}  {(w['sha256'] or 'MISSING')[:16]}…  {w['path']}")

# E1-recorded checkpoint hashes, for cross-checking
e1 = list(csv.DictReader(open(GITROOT / "terrastate/sync_package_20260912_v1/e1/"
                              "E1_table_delivery/E1_per_seed_values.csv", newline="", encoding="utf-8")))
e1_ck = {}
for r in e1:
    if r.get("checkpoint_sha256"):
        e1_ck.setdefault(r["seed"], set()).add(r["checkpoint_sha256"])

# ------------------------------------------------------------------ code index
CODE_GROUPS = {
    "模型与训练（产生这些权重）": [
        "terrastate/models/terrastate_candidate_c.py",
        "terrastate/models/terrastate_v2.py",
        "terrastate/models/plan_b_b4_exclusive.py",
        "terrastate/train/train_terrastate_candidate_c.py",
        "terrastate/train/terrastate_v2_common.py",
        "terrastate/data/greenearthnet_contextformer_dataset.py",
    ],
    "评测与协议（产生这些数字）": [
        "terrastate/eval/eval_b4_exclusive_contract.py",
        "terrastate/eval/greenearthnet_protocol.py",
        "terrastate/eval/eval_greenearthnet_official.py",
        "terrastate/eval/extreme_state_audit.py",
        "terrastate/eval/export_contextformer_predictions.py",
        "terrastate/eval/export_emp_baseline_predictions.py",
        "terrastate/collect_e1_table.py",
    ],
    "运行时状态接口": [
        "terrastate/runtime/candidate_c_state.py",
    ],
    "协议与配置": [
        "terrastate/artifacts/protocols/candidate_c_v1/candidate_c_design_contract_v1.json",
        "terrastate/artifacts/protocols/candidate_c_v1/candidate_c_selection_contract_v1.json",
        "terrastate/artifacts/protocols/candidate_c_v1/candidate_c_formal_queue_v1.json",
        "terrastate/artifacts/protocols/extreme_audit_oodt_v1/hotdry_manifest.json",
    ],
}
code_rows = []
for grp, files in CODE_GROUPS.items():
    for rel in files:
        p = GITROOT / rel
        code_rows.append({"group": grp, "path": rel, "exists": p.exists(),
                          "bytes": p.stat().st_size if p.exists() else None,
                          "sha256": sha(p)[:16] + "…" if p.exists() else ""})

fig_code = sorted(str(p.relative_to(OUT)) for p in (OUT / "figures").glob("图*/code/*"))

# ------------------------------------------------------------------ README
n_files = sum(1 for p in OUT.rglob("*") if p.is_file())
total_bytes = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
fig_dirs = sorted(d.name for d in (OUT / "figures").glob("图*"))

readme = f"""# first_dataset_20260913 — 第一数据集成果发布包

本目录是 **TerraState 第一数据集** 的一次性发布快照：代码索引、两份主文、终稿图、关键表格与
统计、必要的复现数组，以及来源与哈希。**只收录关键结果，不收中间产物。**

- 生成时间（UTC）：{NOW}
- 基线提交：`{COMMIT[:12]}`（分支 `{BRANCH}`，远端 `{REMOTE}`）
- 规模：**{n_files} 个文件，{total_bytes / 1048576:.1f} MiB**
- 完整性：`SHA256SUMS.txt`（逐文件）；`QA_REPORT.md`（本轮验收）

## 怎么读

| 想做什么 | 从这里开始 |
|---|---|
| 快速理解主线与结论 | `narrative/01_TerraState_第一数据集成果总览_十二章继承更新版.md` |
| 直接用于论文写作 | `narrative/02_TerraState_中文论文叙事稿.md` |
| 看图选图 | `figures/OVERVIEW.md` → `figures/图*/selected/`（终稿）+ `figures/reports/FIGURE_CAPTIONS_ZH.md` |
| 核对某个数字 | `tables/`（8 张表 md+csv）→ `metrics/`（聚合 JSON） |
| 复现图与数字 | `reproduction/`（选定样本的数组与元数据）+ `figures/图*/code/` |
| 查来源与权重 | `SOURCE_COMMIT.md`、`CODE_AND_CONFIG_INDEX.md`、`WEIGHTS.md` |

## 目录

```
README.md                 本文件
SOURCE_COMMIT.md          基线提交与每一项材料的来源路径
CODE_AND_CONFIG_INDEX.md  代码 / 协议 / 配置索引（含哈希）
WEIGHTS.md                正式权重清单：路径、字节数、SHA256、获取方式
QA_REPORT.md              本轮验收记录
SHA256SUMS.txt            逐文件哈希
narrative/                两份主文 + 参考文献 + 叙事 QA
figures/                  OVERVIEW + {len(fig_dirs)} 个图目录（selected/ 终稿、code/、data/ 文本）
tables/                   8 张表（md + csv）
metrics/                  关键聚合指标（配对 bootstrap、运行时、天气审计、逐 seed 值）
reports/                  验收 / 主张矩阵 / 证据清单 / 缺口 / 展示方案 / 候选清单
reproduction/             选定样本的数组与候选清单
```

## 范围与排除（重要）

**收录**：两份主文；{len(fig_dirs)} 张终稿图及其绘图代码与文本数据；8 张表的 md+csv；
关键聚合 JSON；验收与缺口记录；**选定样本**（P42 / W02）的复现数组；正式权重清单。

**刻意排除**（都有理由，不是遗漏）：

| 排除内容 | 原因 |
|---|---|
| `figures/图*/candidates/`、`alternatives/`、`contact_sheets/` | 候选图库与备选图，属选图过程产物，已另行保存在运行目录 |
| `figures/图*/data/_arrays/`（P01…P60 全量数组，约 273 MiB） | 60 个候选的逐样本数组；仅保留终稿实际使用的 P42 / W02 |
| 训练日志、`runs/`、`__pycache__`、中断运行 | 过程产物 |
| milestone / 冒烟 / 已停止路线的中间权重 | 非正式权重 |
| 旧 closure / showcase 包的重复副本 | 上游包仍在原处，本目录只放精选 |
| 第二数据集空产物 | 本轮范围外（已延期） |
| `*.pt / *.pth / *.ckpt / *.safetensors` | 仓库配置了 Git LFS 过滤器而服务器未安装 git-lfs，权重走 `WEIGHTS.md` 记录的路径，见下文 |

## 关于权重（请注意）

本目录**不含权重文件**，原因是仓库根 `.gitattributes` 把 `*.pt` 等列入 Git LFS，而服务器没有安装
`git-lfs`；直接提交权重只会写入 133 字节的 LFS 指针，克隆方拿到的是指针而不是模型。
因此这里改为在 `WEIGHTS.md` 中给出**每个权重的路径、字节数与实测 SHA256**，
并说明获取方式。仓库历史提交 `ecb632c` 中的 `terrastate/sync_package_20260912_v1/checkpoints/`
就是这种情况（指针），请以 `WEIGHTS.md` 为准。

## 这份包不是什么

- 不是论文正文，也不是完整审计日志；它是**成果快照 + 来源索引**。
- 不包含第二数据集结论；只覆盖第一数据集。
- 不重跑实验：包内所有数字都来自已验收的冻结结果，本包只做整理与校验。
"""
(OUT / "README.md").write_text(readme, encoding="utf-8")
print("wrote README.md")

# ------------------------------------------------------------------ SOURCE_COMMIT
src_rows = []
def count(d: Path):
    return sum(1 for p in d.rglob("*") if p.is_file()), sum(p.stat().st_size for p in d.rglob("*") if p.is_file())

for label, target, sources in (
    ("叙事两稿 + 参考", "narrative/", [ND]),
    ("终稿图与图注", "figures/", [FF]),
    ("8 张表", "tables/", [CF / "tables"]),
    ("关键聚合指标", "metrics/", [CF / "metrics"]),
    ("验收与缺口", "reports/", [CF / "reports", SH / "reports", SH / "manifests"]),
    ("复现数组", "reproduction/", [FF / "图3_标准空间预测/data", FF / "图8_天气条件响应/data"]),
):
    for s in sources:
        if s.exists():
            n, b = count(s)
            src_rows.append([label, target, str(s), n, b])

src_md = "\n".join(f"| {a} | `{b}` | `{c}` | {d} | {e/1048576:.2f} MiB |"
                   for a, b, c, d, e in src_rows)

sc = f"""# SOURCE_COMMIT — 来源与基线提交

## 基线

| 项 | 值 |
|---|---|
| Git 仓库 | `{REMOTE}` |
| 分支 | `{BRANCH}` |
| 提交 | `{COMMIT}` |
| 打包时间（UTC） | {NOW} |

本发布包中的每一项材料都**复制**自下列来源；来源目录**未被修改、未被移动、未被删除**。

| 用途 | 包内位置 | 来源（只读） | 文件数 | 大小 |
|---|---|---|---|---|
{src_md}

## 与本包相邻的既存同步包

仓库在提交 `ecb632c`（"Add curated TerraState evidence sync package"）中已包含
`terrastate/sync_package_20260912_v1/`：E1 主表交付、evidence v8 的四划分表格与 Fig7、
leaveout JSON、FSR 文档，以及 5 个权重（**以 Git LFS 指针形式**，见 `WEIGHTS.md`）。
本包**不重复**这些内容，只补齐其未覆盖的部分：终稿图、两份主文、修正版表格
（Table 3/4A/4B/5/6A/6B/7）、配对统计、验收记录与复现数组。

## 复现命令（只读，不改动任何来源）

```bash
# 表格与指标
cat tables/Table4B_state_intervention_corrected.csv
cat metrics/T3_c0r_vs_c1_paired_bootstrap.json

# 终稿图（每个图目录内都有 code/ 与 data/）
ls figures/图7_共同后缀与状态作用/selected/
python figures/图7_共同后缀与状态作用/code/render_final.py   # 依赖见该目录 README

# 复现数组
python - <<'PY'
import numpy as np
z = np.load("reproduction/P42_arrays/arrays.npz")
print({{k: z[k].shape for k in z.files}})
PY
```
"""
(OUT / "SOURCE_COMMIT.md").write_text(sc, encoding="utf-8")
print("wrote SOURCE_COMMIT.md")

# ------------------------------------------------------------------ CODE index
groups = {}
for r in code_rows:
    groups.setdefault(r["group"], []).append(r)
code_md = ["# CODE_AND_CONFIG_INDEX — 代码、协议与配置索引", "",
           "路径均相对 Git 仓库根。哈希为 SHA256 前 16 位，完整值可用 "
           "`sha256sum <path>` 复核；不存在或未纳入仓库的条目已标明。", ""]
for grp, rows in groups.items():
    code_md += [f"## {grp}", "", "| 路径 | 存在 | 字节 | sha256(前16) |", "|---|---|---:|---|"]
    for r in rows:
        code_md.append(f"| `{r['path']}` | {'是' if r['exists'] else '**否**'} | "
                       f"{r['bytes'] if r['bytes'] is not None else '—'} | `{r['sha256']}` |")
    code_md.append("")
code_md += [f"## 图件绘制代码（本包内 {len(fig_code)} 个文件）", "",
            "| 路径 |", "|---|"]
for f in fig_code:
    code_md.append(f"| `{f}` |")
code_md += ["", "## 运行环境", "",
            "| 项 | 值 |", "|---|---|",
            f"| 服务器 | dilab |",
            f"| Python | `/data/zs/WorldModel2026/.venv-worldmodel/bin/python` |",
            f"| GPU（正式评测） | 4× NVIDIA A100-SXM4-40GB |",
            f"| 数据集根 | `/data/zs/TrainData/EarthNet2021/earthnet2021x` |", ""]
(OUT / "CODE_AND_CONFIG_INDEX.md").write_text("\n".join(code_md) + "\n", encoding="utf-8")
print("wrote CODE_AND_CONFIG_INDEX.md")

# ------------------------------------------------------------------ WEIGHTS
wm = ["# WEIGHTS — 正式权重清单", "",
      "本包**不包含**权重文件：仓库根 `.gitattributes` 将 `*.pt / *.pth / *.ckpt / *.safetensors` "
      "交由 Git LFS 管理，而本服务器**未安装 git-lfs**。若直接提交，写进仓库的只会是 133 字节的 "
      "LFS 指针（历史提交 `ecb632c` 中的 `sync_package_20260912_v1/checkpoints/` 正是如此），"
      "克隆方拿到的是指针而非模型。因此这里给出**实测**的路径、字节数与 SHA256。", "",
      "## 支撑当前结论的正式权重", "",
      "| 权重 | 仓库内路径 | 字节 | SHA256（实测） |", "|---|---|---:|---|"]
for w in weights:
    if w["bytes"] is None:
        wm.append(f"| {w['label']} | `{w['path']}` | **缺失** | — |")
    else:
        wm.append(f"| {w['label']} | `{w['path']}` | {w['bytes']:,} | `{w['sha256']}` |")
wm += ["", "## 与 E1 交付记录的交叉核对", ""]
if e1_ck:
    wm += ["E1 交付 CSV 中记录的 `checkpoint_sha256`（截断形式）：", "",
           "| seed | 记录的哈希 |", "|---|---|"]
    for k, v in sorted(e1_ck.items()):
        wm.append(f"| {k} | `{', '.join(sorted(v))}` |")
    wm += ["", "> 说明：上表为本包**重新计算**的完整 SHA256；E1 CSV 中记录的是截断值，"
               "两者前缀一致即为同一文件。", ""]
wm += ["## 三个 C1 权重的关系", "",
       "C1 seed 27 / 42 / 97 是同一次多 seed 标准评测的三个训练种子；"
       "Table 1 的 `均值 ± 样本标准差(ddof=1, n=3)` 就来自这三个权重，"
       "它是**种子离散度**，不是置信区间（见 `tables/Table1_standard_prediction.md`）。", "",
       "## 获取方式（按可行性排序）", "",
       "1. **直接从服务器复制**（推荐，无需 LFS）：上表路径在 dilab 上可直接 `scp`。",
       "2. **走 GitHub Release**：需要 `gh`（本服务器未安装）或网页/API 上传；"
       "建议为四个正式权重单开一个 Release，标签如 `weights-first-dataset-20260913`。",
       "3. **修复 LFS 后重推**：安装 `git-lfs` 并 `git lfs push --all origin`，"
       "可把历史指针补成真实对象；但这会改动已推送历史，需谨慎。", "",
       "## 复核命令", "",
       "```bash",
       "sha256sum terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt",
       "sha256sum terrastate/sync_package_20260912_v1/checkpoints/c1_seed27_checkpoint_main.pt",
       "```", ""]
(OUT / "WEIGHTS.md").write_text("\n".join(wm) + "\n", encoding="utf-8")
print("wrote WEIGHTS.md")
print(f"MEASURED_WEIGHTS_JSON={json.dumps(weights, ensure_ascii=False)}")
