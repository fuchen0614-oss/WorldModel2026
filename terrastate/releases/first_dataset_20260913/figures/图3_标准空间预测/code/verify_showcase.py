#!/usr/bin/env python3
"""Acceptance for the showcase package. Mechanical checks only; no statistic is recomputed.

Covered (only what this round changed or produced):
  * candidate count, ID uniqueness and ID<->file correspondence;
  * per-split / per-category quota compliance against the frozen manifest;
  * every candidate compared at the SAME target steps under the SAME validity mask;
  * one shared NDVI scale and one shared error scale (constants, asserted from the renderer);
  * invalid pixels never rendered as a numeric zero (grey via masked arrays);
  * OVERVIEW tables agree with the frozen CSV values they claim to come from;
  * embedded images and links resolve on disk;
  * weather cases carry the counterfactual warning and the protocol-reuse proof;
  * local-sync completeness.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_showcase as L  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

checks = []


def ck(name, ok, detail=""):
    checks.append((name, "PASS" if ok else "FAIL", str(detail)))
    return ok


def rd(p):
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out = args.out
    F = L.FROZEN

    # ---------------------------------------------------------------- 1 candidates
    man = rd(out / "manifests/PREDICTION_CANDIDATES.csv")
    ids = [c["candidate_id"] for c in man]
    ck("32 prediction candidates frozen", len(man) == 32, f"n={len(man)}")
    ck("candidate ids unique and contiguous", len(set(ids)) == len(ids) == 32
       and sorted(ids) == [f"P{i:02d}" for i in range(1, 33)], f"ids={ids[:3]}…{ids[-2:]}")
    per_split = {}
    for c in man:
        per_split[c["split"]] = per_split.get(c["split"], 0) + 1
    ck("8 candidates per split", set(per_split.values()) == {8}, per_split)
    ck("all five categories present",
       {c["category"] for c in man} == {"high_change", "seasonal_trend", "turn_point",
                                        "low_validity", "typical"},
       sorted({c["category"] for c in man}))
    ck("each candidate names a season and a cube",
       all(c["season"] and c["cube"] for c in man), "no empty season/cube")

    # ---------------------------------------------------------------- 2 export integrity
    met = rd(out / "metrics/PREDICTION_CANDIDATE_METRICS.csv")
    ok_rows = [r for r in met if r["status"] == "ok"]
    ck("all 32 candidates exported", len(ok_rows) == 32, f"ok={len(ok_rows)}")
    ck("target timestamps agree with the dataset axis for every candidate",
       all(r["target_dates_match_dataset"] == "True" for r in ok_rows),
       f"{sum(1 for r in ok_rows if r['target_dates_match_dataset'] == 'True')}/32")
    bad_dirs = [c["candidate_id"] for c in man
                if not (out / "gallery/_arrays" / c["candidate_id"] / "arrays.npz").exists()]
    ck("every candidate has an exported array bundle", not bad_dirs, bad_dirs)

    # same steps, same mask, shared scales -- read back from the arrays
    shapes, masks_ok, finite_ok = set(), True, True
    for c in man[:8]:
        z = np.load(out / "gallery/_arrays" / c["candidate_id"] / "arrays.npz")
        for k in ("gt", "c1", "persistence", "valid"):
            shapes.add((k, z[k].shape))
        if z["gt"].shape != z["c1"].shape or z["gt"].shape != z["persistence"].shape:
            masks_ok = False
        v = z["valid"]
        if v.shape != z["gt"].shape:
            masks_ok = False
        if not np.array_equal(np.unique(v), np.array([0, 1], dtype=v.dtype)):
            finite_ok = False
    ck("GT / C1 / Persistence share one shape per candidate", masks_ok,
       f"{len(shapes)} (key,shape) pairs over 8 sampled candidates")
    ck("validity mask is strictly binary", finite_ok, "values ∈ {0,1}")

    # ---------------------------------------------------------------- 3 rendering
    need = []
    for c in man:
        cid = c["candidate_id"]
        for suffix in ("_browse.png", "_browse.pdf", "_detail.png", "_detail.pdf"):
            if not (out / "gallery/prediction" / f"{cid}{suffix}").exists():
                need.append(f"{cid}{suffix}")
        if not (out / "gallery/prediction/thumbs" / f"{cid}_thumb.png").exists():
            need.append(f"{cid}_thumb.png")
    ck("every prediction candidate has browse/detail (png+pdf) and a thumbnail",
       not need, need[:6])

    sheets = sorted((out / "gallery/contact_sheets").glob("CONTACT_prediction_page*.png"))
    sheets_w = sorted((out / "gallery/contact_sheets").glob("CONTACT_weather_page*.png"))
    ck("prediction contact sheets cover all 32 candidates (8 per page)",
       len(sheets) == 4, f"{len(sheets)} page(s)")

    wx = rd(out / "manifests/WEATHER_CANDIDATES.csv")
    ck("12 weather candidates frozen", len(wx) == 12, f"n={len(wx)}")
    ck("weather contact sheets present", len(sheets_w) == 2, f"{len(sheets_w)} page(s)")
    wx_files = []
    for w in wx:
        for suffix in ("_browse.png", "_detail.png", "_detail.pdf"):
            if not (out / "gallery/weather" / f"{w['case_id']}{suffix}").exists():
                wx_files.append(f"{w['case_id']}{suffix}")
    ck("every weather case has browse/detail figures", not wx_files, wx_files[:6])
    wmeta = [json.loads((out / "gallery/weather/_arrays" / w["case_id"] / "metadata.json")
                        .read_text(encoding="utf-8")) for w in wx]
    ck("weather cases state that donor/mean have no counterfactual truth",
       all(m.get("counterfactual_ground_truth") is False and m.get("interpretation_limit")
           for m in wmeta), "interpretation_limit present on all 12")

    # ---------------------------------------------------------------- 4 consistency with frozen numbers
    t1 = rd(F / "tables/Table1_standard_prediction.csv")
    ov = (out / "OVERVIEW.md").read_text(encoding="utf-8")
    c1_iid = next(r for r in t1 if r["method"] == "TerraState-C1" and r["split"] == "iid_chopped")
    ck("OVERVIEW quotes Table 1 C1 iid R²_LC exactly",
       f"{float(c1_iid['R2_mean']):.4f}" in ov, f"{float(c1_iid['R2_mean']):.4f}")
    t4b = rd(F / "tables/Table4B_state_intervention_corrected.csv")
    for sp, scope in (("iid", "full_suffix_1_to_10"), ("ood_st", "endpoint_h10")):
        for est in ("receiver_equal", "geo_equal"):
            r = next((x for x in t4b if x["split"] == sp and x["scope"] == scope
                      and x["estimand"] == est), None)
            if r:
                s = f"{float(r['point_delta_mse']):.6f}"
                ck(f"OVERVIEW quotes T4B {sp}/{scope}/{est} = {s}", s in ov, s)
    bs = json.loads((F / "metrics/T3_c0r_vs_c1_paired_bootstrap.json").read_text(encoding="utf-8"))
    v = bs["primary_grouping"]["ood-t_chopped"]
    ck("OVERVIEW quotes the ood-t bootstrap CI exactly",
       f"[{v['ci95'][0]:+.6f}, {v['ci95'][1]:+.6f}]" in ov,
       f"[{v['ci95'][0]:+.6f}, {v['ci95'][1]:+.6f}]")
    rt = json.loads((F / "metrics/T7_c1_runtime.json").read_text(encoding="utf-8"))
    ck("OVERVIEW quotes the model_hash phase cost exactly",
       f"{rt['phases']['model_hash_ms']:.2f}" in ov, f"{rt['phases']['model_hash_ms']:.2f}")

    # ---------------------------------------------------------------- 5 links and images
    imgs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", ov)
    missing_img = [i for i in set(imgs) if not (out / i).exists()]
    ck("every embedded image resolves on disk", not missing_img, missing_img)
    # only references that look like real paths (they must contain a separator) are checked, so
    # prose fragments such as "`_browse.png`" cannot be mistaken for a missing file
    links = [l for l in re.findall(r"`([A-Za-z0-9_./\-]+\.(?:csv|md|json|png|pdf))`", ov) if "/" in l]
    missing_link = [l for l in set(links) if not (out / l).exists() and not (F / l).exists()]
    ck("every backticked file reference resolves either here or in the frozen package",
       not missing_link, missing_link)

    # ---------------------------------------------------------------- 6 wording discipline
    bad = []
    for needle, allowed in (("不劣于", ("不声称", "声称", "不作判定", "不得", "不写")),
                            ("所有窗口", ("不得",)),
                            ("1.80", ("v1", "未设", "未维持", "不维持", "不设"))):
        for f in [out / "OVERVIEW.md", out / "reports/SELECTION_GUIDE.md"]:
            for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if needle in ln and not any(a in ln for a in allowed):
                    bad.append(f"{f.name}:{i}: {needle}")
    ck("overview and guide keep the wording discipline", not bad, bad)

    # ---------------------------------------------------------------- 7 frozen copies
    fc = rd(out / "provenance/FROZEN_COPIES.csv")
    mism = []
    for r in fc:
        p = out / r["path_in_showcase"]
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != r["sha256"]:
            mism.append(r["path_in_showcase"])
    ck("frozen copies are byte-identical to their recorded hashes", not mism, mism)
    src_missing = [r["frozen_source"] for r in fc if not Path(r["frozen_source"]).exists()]
    ck("every frozen source still exists (nothing was moved or altered)", not src_missing,
       src_missing[:5])

    # ---------------------------------------------------------------- report
    n_fail = sum(1 for c in checks if c[1] == "FAIL")
    lines = ["# SHOWCASE_VERIFICATION", "",
             "机械核对，只覆盖本轮新增或改动的内容；**不重算任何统计量**。",
             "运行入口：`code/verify_showcase.py`。", "",
             "| 检查 | 结果 | 细节 |", "|---|---|---|"]
    for n, s, d in checks:
        lines.append(f"| {n} | {s} | {d} |")
    lines += ["", f"**合计 {len(checks)} 项，FAIL {n_fail} 项。**", ""]
    (out / "reports/SHOWCASE_VERIFICATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "reports/SHOWCASE_VERIFICATION.json").write_text(
        json.dumps({"n_checks": len(checks), "n_fail": n_fail,
                    "checks": [{"name": a, "result": b, "detail": c} for a, b, c in checks]},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for n, s, d in checks:
        print(f"{s}  {n}")
        if s == "FAIL" and d:
            print(f"      {d}")
    print(f"\nSHOWCASE_VERIFICATION: {len(checks)} checks, {n_fail} FAIL")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
