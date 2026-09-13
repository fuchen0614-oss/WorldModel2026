#!/usr/bin/env python3
"""FREEZE the prediction-gallery candidates BEFORE any model result is read.

Selection uses DATA ATTRIBUTES ONLY, computed from the ground-truth cube and the official
validity mask:
    valid_fraction       mean fraction of valid (cloud-free, vegetated, finite) pixels over the
                         20 target steps
    target_std           spread of the true NDVI inside the target window
    ctx_endpoint_change  |mean NDVI at the last context step - mean NDVI at the endpoint|
    abs_trend            |slope| of the spatial-mean valid NDVI trajectory over the target window
    turn                 largest |second difference| of that same trajectory (a turning point)
    c1_pred_exists       whether the frozen E1 C1 prediction file exists (AVAILABILITY, not outcome)

C1 accuracy is never consulted. C1 availability is used only to avoid freezing a candidate that
cannot be shown at all; how many were skipped for that reason is recorded.

Per split the quota is fixed at 8: high_change x2, seasonal_trend x2, turn_point x1,
low_validity x1, typical x2. Ties break on (season, cube) so the result is exactly reproducible.
Cubes with valid_fraction < MIN_VALID_FRACTION are excluded up front and counted as exclusions.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_showcase as L  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

QUOTA = [("high_change", 2), ("seasonal_trend", 2), ("turn_point", 1),
         ("low_validity", 1), ("typical", 2)]
_LCCFG = {}


def _init(lc_min, lc_max):
    _LCCFG["min"], _LCCFG["max"] = lc_min, lc_max


def metrics_one(args):
    split, rel = args
    try:
        p = L.repaired_gt_path(split, rel)
        d = L.read_ndvi_mask_lc(p)
        veg = L.veg_mask(d["landcover"], _LCCFG["min"], _LCCFG["max"])
        ndvi, mask = d["ndvi"], d["mask"]
        cl, tl = L.CONTEXT_STEPS, L.TARGET_STEPS
        v = L.validity(ndvi, mask, veg)
        vt = v[cl:cl + tl]                      # validity on the target window
        yt = ndvi[cl:cl + tl]
        frac = float(vt.mean())
        vals = yt[vt > 0]
        tstd = float(np.std(vals)) if vals.size else float("nan")
        tmean = float(np.mean(vals)) if vals.size else float("nan")
        # spatial-mean valid trajectory over the target window
        traj = np.array([float(yt[h][vt[h] > 0].mean()) if (vt[h] > 0).any() else np.nan
                         for h in range(tl)])
        ok = np.isfinite(traj)
        if ok.sum() >= 3:
            xs = np.arange(tl)[ok]
            trend = float(np.polyfit(xs, traj[ok], 1)[0])
            d2 = np.diff(traj[ok], n=2)
            turn = float(np.max(np.abs(d2))) if d2.size else 0.0
        else:
            trend, turn = float("nan"), float("nan")
        # Context anchor = the most recent context step that has any valid pixel, then the endpoint
        # step. Anchoring on a single fixed step leaves the metric undefined for most cubes
        # (cloud cover), so the most-recent-valid rule is used; it stays deterministic and
        # independent of any model result.
        ctx_anchor = None
        for j in range(cl - 1, -1, -1):
            if (v[j] > 0).any():
                ctx_anchor = float(ndvi[j][v[j] > 0].mean())
                break
        ep_vals = yt[tl - 1][vt[tl - 1] > 0]
        change = (abs(float(ep_vals.mean()) - ctx_anchor)
                  if ctx_anchor is not None and ep_vals.size else float("nan"))
        return {
            "split": split, "rel": rel, "season": rel.split("/")[0], "cube": Path(rel).stem,
            "valid_fraction": frac, "target_std": tstd, "target_mean": tmean,
            "ctx_endpoint_change": change, "trend": trend, "abs_trend": abs(trend),
            "turn": turn, "n_valid_endpoint": int((vt[tl - 1] > 0).sum()),
            "traj": [None if not np.isfinite(x) else round(x, 6) for x in traj],
            "c1_pred_exists": L.c1_pred_path(split, rel).exists(),
            "error": "",
        }
    except Exception as e:  # noqa: BLE001
        return {"split": split, "rel": rel, "season": rel.split("/")[0],
                "cube": Path(rel).stem, "error": f"{type(e).__name__}: {e}"}


def pick(rows, keep, exclude, n, key, reverse=True):
    """Deterministic top-n under a fixed sort key; already-used cubes are skipped."""
    cand = [r for r in rows if r["cube"] not in exclude and keep(r) and np.isfinite(key(r))]
    cand.sort(key=lambda r: ((-key(r)) if reverse else key(r), r["season"], r["cube"]))
    out = []
    for r in cand:
        if len(out) >= n:
            break
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0, help="smoke test: first N cubes per split")
    args = ap.parse_args()
    out: Path = args.out
    (out / "manifests").mkdir(parents=True, exist_ok=True)
    (out / "logs").mkdir(parents=True, exist_ok=True)

    cfg = L.load_contract_cfg()
    lc_min, lc_max = float(cfg["lc_min"]), float(cfg["lc_max"])
    print(f"contract_cfg: state_dim={cfg['state_dim']} lc_min={lc_min} lc_max={lc_max}")

    all_rows, exclusions = [], []
    for split in L.SPLIT_ORDER:
        rels = L.list_cubes(split)
        if args.limit:
            rels = rels[:args.limit]
        print(f"\n=== {split}: {len(rels)} cubes -> metrics with {args.workers} workers ===")
        with ProcessPoolExecutor(max_workers=args.workers, initializer=_init,
                                 initargs=(lc_min, lc_max)) as ex:
            rows = list(ex.map(metrics_one, [(split, r) for r in rels], chunksize=16))
        err = [r for r in rows if r["error"]]
        print(f"    errors: {len(err)}")
        for r in err[:5]:
            print("      ", r["rel"], r["error"])

        # pre-registered exclusion rule
        low = [r for r in rows if not r["error"] and r["valid_fraction"] < L.MIN_VALID_FRACTION]
        for r in low:
            exclusions.append({"split": split, "season": r["season"], "cube": r["cube"],
                               "reason": "valid_fraction_below_minimum",
                               "valid_fraction": round(r["valid_fraction"], 6),
                               "minimum": L.MIN_VALID_FRACTION})
        usable = [r for r in rows if not r["error"] and r["valid_fraction"] >= L.MIN_VALID_FRACTION]
        usable = [r for r in usable if r["c1_pred_exists"]]
        for r in rows:
            if not r["error"] and r["valid_fraction"] >= L.MIN_VALID_FRACTION and not r["c1_pred_exists"]:
                exclusions.append({"split": split, "season": r["season"], "cube": r["cube"],
                                   "reason": "c1_prediction_not_available",
                                   "valid_fraction": round(r["valid_fraction"], 6), "minimum": ""})
        print(f"    usable={len(usable)}  excluded(low-valid)={len(low)}  "
              f"excluded(no C1 pred)={sum(1 for e in exclusions if e['split']==split and e['reason']=='c1_prediction_not_available')}")

        # NOTE: np.median returns NaN if ANY input is NaN, so the median is taken over finite
        # values only. Cubes whose context/endpoint means are undefined (fully clouded) simply
        # cannot be "typical" and are excluded from that category by the isfinite requirement.
        _chg = [r["ctx_endpoint_change"] for r in usable if np.isfinite(r["ctx_endpoint_change"])]
        med = float(np.median(_chg)) if _chg else 0.0
        print(f"    ctx_endpoint_change finite in {len(_chg)}/{len(usable)} cubes")
        # Coverage bars are DATA-RELATIVE (a fixed quantile of the split's usable cubes) rather
        # than an absolute number, so the same rule applies to every split. The chosen values are
        # written into the manifest so the rule is auditable.
        fr = np.array([r["valid_fraction"] for r in usable]) if usable else np.array([1.0])
        well = float(np.quantile(fr, 0.40))
        good = float(np.quantile(fr, 0.50))
        print(f"    coverage bars: well_covered(q40)={well:.4f}  typical_bar(q50)={good:.4f}  "
              f"median_change={med:.4f}")
        for r in usable:
            r["_well"] = r["valid_fraction"] >= well
            r["_good"] = r["valid_fraction"] >= good
        used, picked = set(), []
        for cat, n in QUOTA:
            if cat == "high_change":
                sel = pick(usable, lambda r: r["_well"], used, n,
                           lambda r: r["ctx_endpoint_change"])
            elif cat == "seasonal_trend":
                sel = pick(usable, lambda r: r["_well"], used, n,
                           lambda r: r["abs_trend"])
            elif cat == "turn_point":
                sel = pick(usable, lambda r: r["_well"], used, n,
                           lambda r: r["turn"])
            elif cat == "low_validity":
                sel = pick(usable, lambda r: True, used, n, lambda r: r["valid_fraction"],
                           reverse=False)
            else:  # typical: good coverage AND the most ordinary context->endpoint change
                sel = pick(usable, lambda r: r["_good"], used, n,
                           lambda r: abs(r["ctx_endpoint_change"] - med), reverse=False)
            for r in sel:
                r["category"] = cat
                r["coverage_bar_q40" if cat != "typical" else "coverage_bar_q50"] = (
                    well if cat != "typical" else good)
                picked.append(r)
                used.add(r["cube"])
            print(f"    {cat:<16} n={len(sel)}/{n}")
        all_rows.extend(picked)

    for i, r in enumerate(sorted(all_rows, key=lambda r: (L.SPLIT_ORDER.index(r["split"]),
                                                          r["category"], r["season"], r["cube"])), 1):
        r["candidate_id"] = f"P{i:02d}"
    all_rows.sort(key=lambda r: r["candidate_id"])

    fields = ["candidate_id", "split", "category", "season", "cube", "rel", "valid_fraction",
              "coverage_bar_q40", "coverage_bar_q50",
              "target_std", "target_mean", "ctx_endpoint_change", "trend", "abs_trend", "turn",
              "n_valid_endpoint", "c1_pred_exists", "traj"]
    man = out / "manifests/PREDICTION_CANDIDATES.csv"
    with open(man, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in all_rows:
            d = dict(r)
            d["traj"] = json.dumps(d["traj"])
            for k in ("valid_fraction", "coverage_bar_q40", "coverage_bar_q50", "target_std",
                      "target_mean", "ctx_endpoint_change", "trend", "abs_trend", "turn"):
                v = d.get(k)
                d[k] = "" if v is None or not np.isfinite(v) else f"{v:.6f}"
            w.writerow(d)
    with open(out / "manifests/PREDICTION_CANDIDATE_EXCLUSIONS.csv", "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["split", "season", "cube", "reason",
                                           "valid_fraction", "minimum"])
        w.writeheader()
        w.writerows(exclusions)

    cnt = {}
    for r in all_rows:
        cnt[r["split"]] = cnt.get(r["split"], 0) + 1
    print(f"\nfrozen {len(all_rows)} candidates -> {man}")
    print("  per split:", cnt)
    print("  per category:", {c: sum(1 for r in all_rows if r['category'] == c) for c, _ in QUOTA})


if __name__ == "__main__":
    main()
