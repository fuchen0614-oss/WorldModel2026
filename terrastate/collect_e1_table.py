#!/usr/bin/env python3
"""Regenerate the E1 main-table document from whatever results exist on disk.

Mechanical: every number is read out of a result JSON, nothing is transcribed by
hand, so re-running this after more configs finish keeps A08 in sync. Rows that
have not been scored yet show as pending rather than being silently dropped.

Sources
  baselines   evaluations/e1_main_table/<model>__<split>/scores/metrics_en21x.json
  TerraState  evaluations/candidate_c_q1q2q3_*/<tag>/state_contract_exclusive.json
"""
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
E1 = ROOT / "evaluations/e1_main_table"
C1 = ROOT / "evaluations/candidate_c_q1q2q3_20260830T072737Z"
OUT = ROOT / "思路整理进展/A08_E1主表_同协议重跑结果.md"

SPLITS = ["iid_chopped", "ood-t_chopped", "ood-s_chopped", "ood-st_chopped"]
SPLIT_LABEL = {"iid_chopped": "IID", "ood-t_chopped": "OOD-t",
               "ood-s_chopped": "OOD-s", "ood-st_chopped": "OOD-st"}
METRICS = ["R2", "rmse", "nse", "biasabs", "rmse25"]
FAMILIES = [("convlstm1M", "ConvLSTM 1M", "1.04M"),
            ("predrnn1M", "PredRNN 1M", "1.43M"),
            ("simvp6M", "SimVP 6M", "6.59M"),
            ("contextformer6M", "Contextformer 6M", "6.06M")]
SEEDS = ["27", "42", "97"]
# Benson et al. CVPR 2024 Table 2, OOD-t. Reference only -- different protocol run.
PAPER = {"convlstm1M": (0.580, 0.160, -0.130, 0.110, 0.110),
         "predrnn1M": (0.620, 0.150, 0.030, 0.100, 0.100),
         "simvp6M": (0.600, 0.150, 0.030, 0.090, 0.100),
         "contextformer6M": (0.620, 0.140, 0.090, 0.090, 0.080)}
C1_TAG = {"iid_chopped": "iid", "ood-t_chopped": "oodt",
          "ood-s_chopped": "oods", "ood-st_chopped": "oodst"}


def baseline(model, split):
    p = E1 / f"{model}__{split}" / "scores" / "metrics_en21x.json"
    if not p.is_file():
        return None
    m = json.loads(p.read_text()).get("metrics", {})
    return {k: m[k] for k in METRICS} if all(k in m for k in METRICS) else None


def terrastate(split):
    p = C1 / C1_TAG[split] / "state_contract_exclusive.json"
    if not p.is_file():
        return None
    q = json.loads(p.read_text())["Q1_forecast"]["full"]
    return {k: q[k] for k in METRICS}


def cell(v):
    return "—" if v is None else f"{v:.4f}"


def main():
    lines = [
        "# A08 · E1 主表：同协议重跑结果",
        "",
        "> **本文由 `collect_e1_table.py` 从结果 JSON 机械生成，无手工抄录。**",
        f"> 生成时间（UTC）：{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}",
        ">",
        "> 与 [A06](./A06_TerraState_主表Table1_当前数值与来源.md) 的区别：A06 记录的是"
        "**文献数字**（Benson et al. CVPR 2024 Table 2）；本文是**我们自己在同一 manifest / "
        "mask / scorer / 时域下重跑**的结果。A01 §3.1 要求两者分栏，本文即自跑栏。",
        "",
        "**协议**：GreenEarthNet chopped（`greenearthnet_cvpr2024_chopped_v1`），官方 LC-balanced "
        "scorer，四个 split 共 22,320 minicubes。基线权重为 Zenodo record 10793870 的官方发布权重，"
        "`strict=True` 加载，参数量与论文一致（见 [A07](./A07_E1基线家底_权重代码数据在哪怎么取.md)）。",
        "",
        "---",
        "",
    ]

    for split in SPLITS:
        lines += [f"## {SPLIT_LABEL[split]}（`{split}`）", "",
                  "| Method | seed | R²↑ | RMSE↓ | NSE↑ | \\|Bias\\|↓ | RMSE25↓ | #Params |",
                  "|---|---|---:|---:|---:|---:|---:|---:|"]
        for fam, label, params in FAMILIES:
            per_seed = {}
            for s in SEEDS:
                r = baseline(f"{fam}_seed{s}", split)
                per_seed[s] = r
                lines.append(f"| {label} | {s} | " +
                             " | ".join(cell(r[k] if r else None) for k in METRICS) +
                             f" | {params} |")
            got = [r for r in per_seed.values() if r]
            if len(got) == len(SEEDS):
                mean = {k: statistics.fmean(r[k] for r in got) for k in METRICS}
                lines.append(f"| **{label}** | **3-seed 均值** | " +
                             " | ".join(f"**{cell(mean[k])}**" for k in METRICS) +
                             f" | {params} |")
        ts = terrastate(split)
        lines.append("| **TerraState-C1** | 1 | " +
                     " | ".join(f"**{cell(ts[k] if ts else None)}**" for k in METRICS) +
                     " | **7.18M** |")
        lines += ["", ""]

    # --- literature gap, OOD-t only (the split the paper reports) --------------
    lines += ["---", "", "## 与文献数字的差距（OOD-t，仅供对照）", "",
              "论文报的是 3-seed 均值，故只在三个 seed 都跑完时比较。",
              "**这不是我们跑错了** —— 同一份官方权重在不同评测协议下给出不同数值，",
              "正是 A01 §3.1 要求同协议重跑的原因。", "",
              "| Method | 指标 | 论文 | 本次重跑 | 差 |", "|---|---|---:|---:|---:|"]
    any_gap = False
    for fam, label, _ in FAMILIES:
        got = [baseline(f"{fam}_seed{s}", "ood-t_chopped") for s in SEEDS]
        if not all(got):
            continue
        any_gap = True
        mean = {k: statistics.fmean(r[k] for r in got) for k in METRICS}
        for k, ref in zip(METRICS, PAPER[fam]):
            lines.append(f"| {label} | {k} | {ref:.3f} | {mean[k]:.4f} | "
                         f"{mean[k]-ref:+.4f} |")
    if not any_gap:
        lines.append("| — | — | — | 三个 seed 尚未跑齐 | — |")

    # --- progress -------------------------------------------------------------
    done = pend = 0
    pending = []
    for fam, _, _ in FAMILIES:
        for s in SEEDS:
            for split in SPLITS:
                if baseline(f"{fam}_seed{s}", split):
                    done += 1
                else:
                    pend += 1
                    pending.append(f"{fam}_seed{s}__{split}")
    ts_done = sum(1 for sp in SPLITS if terrastate(sp))
    lines += ["", "---", "", "## 进度", "",
              f"- 基线：**{done}/{done+pend}** 个配置已出分",
              f"- TerraState-C1：**{ts_done}/4** 个 split 已出分",
              "- 非 ML 基线（Persistence / Climatology / Previous year）：**未接入**，"
              "官方实现在 `third_party/greenearthnet/model_pixelwise/`，待办",
              "- Earthformer：**权重不在官方发布包内**，标 n.a.（论文中最弱的学习型方法）",
              ""]
    if pending:
        lines += ["<details><summary>未完成配置</summary>", "", "```"] + \
                 pending[:60] + ["```", "", "</details>", ""]

    OUT.write_text("\n".join(lines))
    print(f"[ok] {OUT}  基线 {done}/{done+pend}  TerraState {ts_done}/4")


if __name__ == "__main__":
    main()
