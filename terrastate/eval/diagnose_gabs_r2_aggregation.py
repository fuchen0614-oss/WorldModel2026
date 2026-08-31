#!/usr/bin/env python3
"""DIAGNOSTIC ONLY — re-aggregate the sealed Q4 G_abs statistics under a corrected R2.

This does NOT re-score `val_locked`: no model is loaded, no forward pass is run, no
sealed artifact is modified. It reads the per-cube sufficient statistics (n, sse, sy,
sy2) that the sealed run already wrote, and asks one question:

    the frozen G_abs R2 leg averages PER-CUBE R2, which is unbounded below when a
    cube's target variance approaches zero. What does the same sealed data say if
    that leg uses POOLED R2 instead -- the same aggregation the RMSE leg already uses?

Everything else is imported verbatim from the evaluator: geo-clustered bootstrap
(B=2000, tile clusters, same seed), eligibility, percentile CI, EPS_R2 / EPS_RMSE.
Step 1 reproduces the frozen 4/19 as a self-check; if that fails, nothing below it
is trustworthy and the script says so.

The frozen verdict Q4_LOCKED_COMPLETE_QUALIFIED_FAIL_NO_RERUN stands regardless of
what this prints. Output is limitation/diagnosis evidence, not a new verdict.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.eval_terrastate_candidate_c_q4 import (  # noqa: E402
    COMPARE_BOOTSTRAP_B, CONTROL_SEED, EPS_R2, EPS_RMSE, MIN_VALID_PIXELS,
    SENSITIVITY_STD_FLOOR, ci_from_draws, geo_cluster_weights, load_score_dir,
    per_cube_metrics, wmean, wpooled, _align, _key,
)

SEALED = Path("results/q4_eval_locked_4gpu_20260824T101119Z")
OUT = Path("results/q4_gabs_r2_diagnostic")


def block(W, sa, sb, elig, *, r2_mode):
    """G_abs for one combo. `r2_mode` selects ONLY how the R2 leg aggregates."""
    if r2_mode == "per_cube":                       # frozen definition
        _m, ra, _s, _e = per_cube_metrics(sa)
        _m, rb, _s, _e = per_cube_metrics(sb)
        d_r2 = wmean(W, ra - rb, elig)
        point = float(np.nanmean(np.where(elig, ra - rb, np.nan)))
    elif r2_mode == "pooled":                       # corrected: match the RMSE leg
        _msea, r2a = wpooled(W, sa, elig)
        _mseb, r2b = wpooled(W, sb, elig)
        d_r2 = r2a - r2b
        point = float(np.nanmedian(d_r2))
    else:
        raise ValueError(r2_mode)

    lo_r2, hi_r2 = ci_from_draws(d_r2)
    pa, _ = wpooled(W, sa, elig)
    pb, _ = wpooled(W, sb, elig)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.sqrt(pa) / np.sqrt(np.maximum(pb, 1e-300))
    lo_rt, hi_rt = ci_from_draws(ratio)
    return {
        "n_paired_cubes": int(elig.sum()),
        "delta_r2_point": point, "delta_r2_ci95": [lo_r2, hi_r2], "delta_r2_lcb": lo_r2,
        "lcb_ge_neg_eps": bool(lo_r2 >= -EPS_R2),
        "rmse_ratio_ucb": hi_rt, "ucb_le_1_plus_eps": bool(hi_rt <= 1.0 + EPS_RMSE),
        "passes": bool(lo_r2 >= -EPS_R2 and hi_rt <= 1.0 + EPS_RMSE),
    }


def main():
    agg_a, sa_all, ids_a = load_score_dir(str(SEALED / "c1_score"))
    agg_b, sb_all, ids_b = load_score_dir(str(SEALED / "c0r_score"))
    combos = {c["combo"]: c for c in agg_a.get("combos", [])}

    rows, Wcache = [], {}
    for combo, meta in combos.items():
        al = _align(sa_all, ids_a, sb_all, ids_b, _key(combo, "factual"))
        if al is None:
            continue
        sa, sb, elig, ids = al
        ck = (len(ids), hash(tuple(ids)))
        if ck not in Wcache:
            Wcache[ck] = geo_cluster_weights(ids, B=COMPARE_BOOTSTRAP_B, seed=CONTROL_SEED)
        W, tiles = Wcache[ck]

        # sensitivity axes, identical to the sealed run
        e_none = (per_cube_metrics(sa, min_valid=1, std_floor=0.0)[3]
                  & per_cube_metrics(sb, min_valid=1, std_floor=0.0)[3])
        e_std = (per_cube_metrics(sa, min_valid=1, std_floor=SENSITIVITY_STD_FLOOR)[3]
                 & per_cube_metrics(sb, min_valid=1, std_floor=SENSITIVITY_STD_FLOOR)[3])

        row = {"combo": combo, "n_segments": meta["n_segments"], "n_tiles": len(tiles)}
        for mode in ("per_cube", "pooled"):
            row[mode] = block(W, sa, sb, elig, r2_mode=mode)
            row[f"{mode}_none"] = block(W, sa, sb, e_none, r2_mode=mode)
            row[f"{mode}_std_v1"] = block(W, sa, sb, e_std, r2_mode=mode)
        rows.append(row)

    def tally(mode, suffix=""):
        k = mode + suffix
        return sum(r[k]["passes"] for r in rows)

    repro = tally("per_cube")
    print(f"\n[自检] 用冻结定义复现 G_abs: {repro}/{len(rows)} 通过 "
          f"(封存报告记录为 4/19)  -> {'一致 ✅' if repro == 4 and len(rows) == 19 else '不一致 ❌'}")
    if not (repro == 4 and len(rows) == 19):
        print("       复现失败，下面的修正结果不可信。")
        return 1

    print(f"\n{'combo':<15}{'seg':>4} | {'冻结 per-cube R²':^30} | {'修正 pooled R²':^30}")
    print(f"{'':<15}{'':>4} | {'ΔR²':>10}{'LCB':>10}{'过?':>8} | {'ΔR²':>10}{'LCB':>10}{'过?':>8}")
    print("-" * 88)
    for r in rows:
        p, q = r["per_cube"], r["pooled"]
        print(f"{r['combo']:<15}{r['n_segments']:>4} | {p['delta_r2_point']:>10.3f}"
              f"{p['delta_r2_lcb']:>10.3f}{('PASS' if p['passes'] else 'FAIL'):>8} | "
              f"{q['delta_r2_point']:>10.4f}{q['delta_r2_lcb']:>10.4f}"
              f"{('PASS' if q['passes'] else 'FAIL'):>8}")

    print(f"\n{'口径':<22}{'冻结 per-cube R²':>20}{'修正 pooled R²':>20}")
    for suffix, name in (("_none", "none (sst>0)"), ("_std_v1", "std_floor v1"),
                         ("", f"primary (n_valid>={MIN_VALID_PIXELS})")):
        print(f"  {name:<20}{tally('per_cube', suffix):>16}/{len(rows)}"
              f"{tally('pooled', suffix):>16}/{len(rows)}")

    direct = [r for r in rows if r["n_segments"] == 1]
    comp = [r for r in rows if r["n_segments"] > 1]
    for mode in ("per_cube", "pooled"):
        d = sum(r[mode]["passes"] for r in direct)
        c = sum(r[mode]["passes"] for r in comp)
        print(f"\n  {mode:<10} direct {d}/{len(direct)}  composed {c}/{len(comp)}  "
              f"总门={'PASS' if d == len(direct) and c == len(comp) else 'FAIL'}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gabs_r2_diagnostic.json").write_text(json.dumps({
        "schema": "gabs_r2_diagnostic_v1",
        "IS_DIAGNOSTIC_NOT_A_VERDICT": True,
        "frozen_verdict_unchanged": "Q4_LOCKED_COMPLETE_QUALIFIED_FAIL_NO_RERUN",
        "source_sealed_run": str(SEALED),
        "reproduced_frozen_gabs": f"{repro}/{len(rows)}",
        "per_combo": rows,
    }, indent=2, default=float))
    print(f"\n写出: {OUT/'gabs_r2_diagnostic.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
