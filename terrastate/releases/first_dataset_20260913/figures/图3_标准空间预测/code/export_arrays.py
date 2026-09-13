#!/usr/bin/env python3
"""Export the per-candidate arrays used by the gallery figures.

Reads only artefacts that already exist:
  * ground truth, cloud/land-cover mask  -> the validation cubes (official dataset formulas)
  * TerraState-C1 prediction             -> the frozen E1 evaluation NetCDF (NEVER re-inferred)
  * Persistence                          -> reproduced from the context (deterministic)
No model is loaded and no GPU is used, so this step cannot change any reported number.

Baseline spatial predictions (Contextformer / PredRNN / ConvLSTM / SimVP) are NOT available on
this server: `evaluations/e1_main_table/*` kept only `scores/`, and no official baseline
checkpoint exists under /data/zs. They are therefore absent from the figures and are recorded as a
missing baseline rather than filled with a substitute model.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_showcase as L  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

EARLY, MID, LATE = 4, 9, 19     # fixed display horizons (0-based) for every candidate and model


def fs(x):
    """Format a float for CSV output; None/NaN become an EMPTY cell, never 0."""
    return "" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{float(x):.6f}"


def export_one(out: Path, man: dict, cfg: dict, seed: int) -> dict:
    split, rel = man["split"], man["rel"]
    d = L.read_ndvi_mask_lc(L.repaired_gt_path(split, rel))
    ndvi, mask, lc = d["ndvi"], d["mask"], d["landcover"]
    cl, tl = L.CONTEXT_STEPS, L.TARGET_STEPS
    veg = L.veg_mask(lc, float(cfg["lc_min"]), float(cfg["lc_max"]))
    valid = L.validity(ndvi, mask, veg)
    gt = ndvi[cl:cl + tl]
    vmask = valid[cl:cl + tl]
    ctx = ndvi[:cl]
    cvalid = valid[:cl]

    c1 = L.read_c1_pred(split, rel, seed)
    if c1 is None:
        return {"candidate_id": man["candidate_id"], "status": "missing_c1_prediction"}
    if c1.shape != gt.shape:
        return {"candidate_id": man["candidate_id"],
                "status": f"shape_mismatch gt={gt.shape} c1={c1.shape}"}

    # timestamps: prefer the prediction NetCDF's own axis, then verify it against the GT axis
    ptimes = L.read_c1_pred_times(split, rel, seed)
    gtimes = L.read_gt_times(split, rel)
    sub = [gtimes[L.OFFSET_DAYS::L.STRIDE_DAYS][cl + h] for h in range(tl)]
    time_match = (ptimes == sub)

    pers = L.persistence_from_context(ndvi, valid, cl, tl)

    cid = man["candidate_id"]
    vf_step = vmask.mean(axis=(1, 2))                 # valid fraction per target step
    # DISPLAY-STEP RULE (pre-registered, applied identically to every model and every candidate):
    # the browse / thumbnail step is the step with the LARGEST valid fraction (ties -> later step).
    # This exists because heavy cloud can leave individual steps with zero valid pixels, and a
    # fully grey panel is unusable for choosing figures. The DETAIL figure keeps the fixed
    # t+5 / t+10 / t+20 steps and shows the per-step coverage, so the gap stays visible.
    display_step = int(np.argmax(vf_step[::-1][::-1])) if vf_step.max() > 0 else LATE
    order = np.argsort(-vf_step, kind="stable")
    top3 = sorted(int(i) for i in order[:3])

    dest = out / "gallery/_arrays" / cid
    dest.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        dest / "arrays.npz",
        gt=gt.astype(np.float32), c1=c1.astype(np.float32),
        persistence=pers.astype(np.float32),
        valid=vmask.astype(np.uint8), context=ctx.astype(np.float32),
        context_valid=cvalid.astype(np.uint8), landcover=np.asarray(lc, dtype=np.float32),
    )
    meta = {
        "candidate_id": cid, "split": split, "category": man["category"],
        "season": man["season"], "cube": man["cube"], "rel": rel,
        "dataset_index": man.get("dataset_index", ""),
        "context_steps": cl, "target_steps": tl,
        "offset_days": L.OFFSET_DAYS, "stride_days": L.STRIDE_DAYS,
        "target_dates": ptimes, "target_dates_match_dataset": bool(time_match),
        "gt_path": str(L.repaired_gt_path(split, rel)),
        "c1_pred_path": str(L.c1_pred_path(split, rel, seed)),
        "c1_checkpoint": str(L.C1_CKPT),
        "valid_fraction": float(vmask.mean()),
        "n_valid_target": int(vmask.sum()),
        "lc_min": float(cfg["lc_min"]), "lc_max": float(cfg["lc_max"]),
        "valid_scl_classes": list(L.VALID_SCL_CLASSES),
        "display_horizons_0based": [EARLY, MID, LATE],
        "display_step_1based": display_step + 1,
        "display_steps_top3_1based": [i + 1 for i in top3],
        "display_step_rule": ("browse/thumbnail use the step with the largest valid fraction "
                              "(ties -> later step); the detail figure keeps the fixed "
                              "t+5 / t+10 / t+20 steps"),
        "valid_fraction_per_step": [round(float(x), 6) for x in vf_step],
        "n_empty_steps": int((vf_step == 0).sum()),
        "missing_baselines": ["Contextformer 6M", "PredRNN 1M", "ConvLSTM 1M", "SimVP 6M"],
        "missing_baselines_reason": ("no official baseline checkpoint and no exported baseline "
                                     "prediction on this server"),
    }
    (dest / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                        encoding="utf-8")

    def rmse(pred):
        return L.rmse_on(pred, gt, vmask)

    def per_h(pred):
        out_h = []
        for h in range(tl):
            m = vmask[h] > 0
            if not m.any():
                out_h.append(None)          # a step with no valid pixel has no defined error
                continue
            d = pred[h][m] - gt[h][m]
            out_h.append(float(np.sqrt(np.mean(d ** 2))))
        return out_h

    return {"candidate_id": cid, "status": "ok", "split": split, "category": man["category"],
            "season": man["season"], "cube": man["cube"], "rel": rel,
            "valid_fraction": round(float(vmask.mean()), 6),
            "n_valid_target": int(vmask.sum()),
            "display_step": display_step + 1, "n_empty_steps": int((vf_step == 0).sum()),
            "rmse_c1": rmse(c1), "rmse_persistence": rmse(pers),
            "rmse_c1_h": per_h(c1), "rmse_persistence_h": per_h(pers),
            "gt_endpoint_mean": float(gt[LATE][vmask[LATE] > 0].mean()) if (vmask[LATE] > 0).any() else None,
            "ctx_last_mean": float(ctx[cl - 1][cvalid[cl - 1] > 0].mean()) if (cvalid[cl - 1] > 0).any() else None,
            "target_dates": ptimes, "time_match": bool(time_match)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    out = args.out
    man = list(csv.DictReader(open(out / "manifests/PREDICTION_CANDIDATES.csv", newline="",
                                   encoding="utf-8")))
    if args.limit:
        man = man[:args.limit]
    cfg = L.load_contract_cfg()
    rows = []
    for m in man:
        r = export_one(out, m, cfg, args.seed)
        rows.append(r)
        flag = "ok  " if r["status"] == "ok" else "FAIL"
        extra = (f"valid={r['valid_fraction']:.3f} rmse_c1={r['rmse_c1']:.4f} "
                 f"rmse_pers={r['rmse_persistence']:.4f}" if r["status"] == "ok" else r["status"])
        print(f"  {flag} {r['candidate_id']} {r.get('split',''):<28} {extra}")

    (out / "metrics").mkdir(parents=True, exist_ok=True)
    ok = [r for r in rows if r["status"] == "ok"]
    with open(out / "metrics/PREDICTION_CANDIDATE_METRICS.csv", "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["candidate_id", "split", "category", "season", "cube", "rel",
                    "status", "valid_fraction", "n_valid_target",
                    "rmse_c1", "rmse_persistence",
                    "rmse_c1_early", "rmse_c1_mid", "rmse_c1_late",
                    "rmse_persistence_early", "rmse_persistence_mid", "rmse_persistence_late",
                    "rmse_c1_h20", "rmse_persistence_h20",
                    "display_step", "n_empty_steps",
                    "target_dates_match_dataset"])
        for r in rows:
            if r["status"] != "ok":
                w.writerow([r["candidate_id"], "", "", "", "", "", r["status"]] + [""] * 15)
                continue
            w.writerow([r["candidate_id"], r["split"], r["category"], r["season"], r["cube"],
                        r["rel"], "ok", r["valid_fraction"], r["n_valid_target"],
                        fs(r["rmse_c1"]), fs(r["rmse_persistence"]),
                        fs(r["rmse_c1_h"][EARLY]), fs(r["rmse_c1_h"][MID]),
                        fs(r["rmse_c1_h"][LATE]),
                        fs(r["rmse_persistence_h"][EARLY]),
                        fs(r["rmse_persistence_h"][MID]),
                        fs(r["rmse_persistence_h"][LATE]),
                        json.dumps(r["rmse_c1_h"]), json.dumps(r["rmse_persistence_h"]),
                        r["display_step"], r["n_empty_steps"],
                        r["time_match"]])
    print(f"\nexported {len(ok)}/{len(rows)} candidates -> gallery/_arrays/")
    bad = [r for r in rows if r["status"] != "ok"]
    if bad:
        print("not exported:", [(r["candidate_id"], r["status"]) for r in bad])
    times_ok = all(r.get("time_match") for r in ok)
    print(f"target timestamps agree with the dataset axis for every candidate: {times_ok}")
    print(f"mean masked RMSE over candidates: C1={np.mean([r['rmse_c1'] for r in ok]):.4f}  "
          f"Persistence={np.mean([r['rmse_persistence'] for r in ok]):.4f}")


if __name__ == "__main__":
    main()
