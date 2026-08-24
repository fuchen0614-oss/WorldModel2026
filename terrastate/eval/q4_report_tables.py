#!/usr/bin/env python
"""把 Q4 结果包整理成论文 Panel A / Panel B 可填的数字，并并列打印三种资格口径。

只读：本脚本不重算任何指标，只从 q4_aggregate.json / q4_compare.json 取数。
用法：
  python eval/q4_report_tables.py --run results/q4_eval_<ts>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(p: Path):
    with p.open() as f:
        return json.load(f)


def _fmt(v, nd=4):
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "pass" if v else "FAIL"
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return str(v)


def _ci(b, nd=4):
    """把 {'mean':..,'ci95':[lo,hi]} 打成 mean [lo, hi]。"""
    if not isinstance(b, dict) or "mean" not in b:
        return "n/a"
    lo, hi = (b.get("ci95") or [None, None])[:2]
    return f"{_fmt(b['mean'], nd)} [{_fmt(lo, nd)}, {_fmt(hi, nd)}]"


def panel_a(agg, cmp_):
    """Partition × (E_dir, E_cmp, joint guard, delta_z, delta_y, delta_y_broken, A_comp)。

    E_dir 取同端点 direct 组合的 pooled MSE；E_cmp 取该 partition 自身的 pooled MSE。
    joint guard 用 compare 的 per-combo G_abs 判定（臂间比较那道门）。
    """
    pc = agg["per_combo"]
    direct_mse = {}
    for c, blk in pc.items():
        if blk["meta"]["n_segments"] == 1:
            direct_mse[int(blk["meta"]["endpoint"])] = \
                blk["variants"]["factual"]["pooled_mse"]
    cpc = (cmp_ or {}).get("per_combo", {})
    rows = []
    for c, blk in pc.items():
        m = blk["meta"]
        if m["n_segments"] == 1:
            continue
        ep = int(m["endpoint"])
        p = blk.get("paths") or {}
        rows.append({
            "combo": c,
            "partition": "+".join(str(x) for x in m["partition"]),
            "endpoint": ep,
            "tag": m["tag"],
            "n_eligible": blk.get("n_eligible_cubes"),
            "E_dir": direct_mse.get(ep),
            "E_cmp": blk["variants"]["factual"]["pooled_mse"],
            "guard": cpc.get(c, {}).get("passes"),
            "delta_z": p.get("delta_z"),
            "delta_y": p.get("delta_y"),
            "delta_y_broken": p.get("delta_y_broken"),
            "a_comp": p.get("a_comp_path"),
        })
    rows.sort(key=lambda r: (r["endpoint"], len(r["partition"])))
    return rows


def panel_b(agg):
    """Horizon × (M_h, S_h/S_t, r_eff,h/r_eff,t, 退化检查)。"""
    hs = agg.get("horizon_state_report") or {}
    nc = ((agg.get("gates") or {}).get("state_retention") or {}) \
        .get("noncollapse_gate") or {}
    rows = []
    for h, r in sorted((hs.get("horizons") or {}).items(), key=lambda kv: int(kv[0])):
        if r.get("degenerate"):
            rows.append({"horizon": h, "degenerate": True, "reason": r.get("reason")})
            continue
        rows.append({"horizon": h, "movement": r["movement"],
                     "std_retention": r["std_retention"],
                     "rank_retention": r["effective_rank_retention"],
                     "n_tokens": r["n_tokens"]})
    return rows, hs.get("denominator"), nc.get("verdict")


def degradation(agg):
    """直接 vs 分段的核心对比：每个端点 direct RMSE、最差分段 RMSE、相对退化。"""
    pc = agg["per_combo"]
    out = {}
    for c, blk in pc.items():
        m = blk["meta"]
        ep = int(m["endpoint"])
        rmse = blk["variants"]["factual"]["pooled_rmse"]
        r2 = blk["variants"]["factual"]["pooled_r2"]
        d = out.setdefault(ep, {"direct": None, "direct_r2": None,
                                "worst": None, "worst_combo": None,
                                "worst_r2": None})
        if m["n_segments"] == 1:
            d["direct"], d["direct_r2"] = rmse, r2
        elif d["worst"] is None or rmse > d["worst"]:
            d["worst"], d["worst_combo"], d["worst_r2"] = rmse, c, r2
    for ep, d in out.items():
        if d["direct"] and d["worst"]:
            d["degradation_pct"] = 100.0 * (d["worst"] / d["direct"] - 1.0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="q4_eval_<ts> 目录")
    a = ap.parse_args()
    run = Path(a.run)
    c1 = _load(run / "c1_score" / "q4_aggregate.json")
    c0r = _load(run / "c0r_score" / "q4_aggregate.json")
    cmp_path = run / "compare" / "q4_compare.json"
    cmp_ = _load(cmp_path) if cmp_path.is_file() else None

    print("=" * 78)
    print("资格口径（本次运行的主口径与并列敏感性）")
    er = c1.get("eligibility_rule", {})
    print(f"  主口径: {er.get('axis')} = {er.get('min_valid_pixels')}")
    print(f"  预注册: {er.get('preregistered')}   改变结论: {er.get('changes_conclusion')}")
    print(f"  代价: {er.get('cost')}")

    print("\n" + "=" * 78)
    print("四道门")
    for nm, arm in (("C1 ", c1), ("C0R", c0r)):
        g = arm["gates"]
        print(f"  {nm} verdict={arm['verdict']:>4}  " + "  ".join(
            f"{k}={'P' if v.get('passes') else 'F'}" for k, v in g.items()))

    print("\n" + "=" * 78)
    print("核心对比：直接预测 vs 分段递推（pooled RMSE / R²）")
    d1, d0 = degradation(c1), degradation(c0r)
    print(f"  {'端点':<6}{'臂':<5}{'direct RMSE':>12}{'最差分段':>12}"
          f"{'退化':>9}   {'direct R²':>10}{'分段 R²':>10}  最差组合")
    for ep in sorted(d1):
        for nm, dd in (("C1", d1), ("C0R", d0)):
            r = dd.get(ep, {})
            print(f"  {ep:<6}{nm:<5}{_fmt(r.get('direct')):>12}"
                  f"{_fmt(r.get('worst')):>12}"
                  f"{_fmt(r.get('degradation_pct'), 1) + '%':>9}   "
                  f"{_fmt(r.get('direct_r2'), 3):>10}{_fmt(r.get('worst_r2'), 3):>10}"
                  f"  {r.get('worst_combo')}")

    print("\n" + "=" * 78)
    print("Panel A（C1；E=pooled MSE，guard=臂间 G_abs）")
    for r in panel_a(c1, cmp_):
        print(f"  {r['partition']:<10} ep{r['endpoint']:<3} {r['tag']:<11}"
              f" n={r['n_eligible']:<4}"
              f" E_dir={_fmt(r['E_dir'])} E_cmp={_fmt(r['E_cmp'])}"
              f" guard={_fmt(r['guard'])}")
        print(f"       dz={_ci(r['delta_z'])}  dy={_ci(r['delta_y'])}")
        print(f"       dy_brk={_ci(r['delta_y_broken'])}  A_comp={_ci(r['a_comp'])}")

    print("\n" + "=" * 78)
    print("Panel B（C1；逐 horizon 状态量，仅报告不参与门）")
    rows, den, verdict = panel_b(c1)
    if den:
        print(f"  分母 S_t={_fmt(den['state_std_zt'])} "
              f"r_eff,t={_fmt(den['effective_rank_zt'], 3)} "
              f"n_tokens={den['n_tokens_zt']}")
    for r in rows:
        if r.get("degenerate"):
            print(f"  h={r['horizon']:<4} 退化：{r['reason']}")
        else:
            print(f"  h={r['horizon']:<4} M_h={_fmt(r['movement'], 3):>8}"
                  f"  S_h/S_t={_fmt(r['std_retention']):>8}"
                  f"  r_eff ratio={_fmt(r['rank_retention']):>8}"
                  f"  n_tokens={r['n_tokens']}")
    print(f"  预注册退化检查（noncollapse_gate, ep20|10-10）: {verdict}")

    if cmp_:
        print("\n" + "=" * 78)
        print("臂间比较 C1 vs C0R（geo-clustered bootstrap, B=2000, tile 聚类）")
        g = cmp_["factual_endpoint_gate"]
        print(f"  verdict={cmp_['verdict']}  direct_all_pass={g['direct_all_pass']}"
              f"  composed_all_pass={g['composed_all_pass']}")
        cpc = cmp_["per_combo"]
        npass = sum(1 for v in cpc.values() if v.get("passes"))
        print(f"  通过组合数: {npass}/{len(cpc)}")
        print("  三种资格口径并列（通过数）：")
        for key, lab in (("none", "无门限 sst>0"),
                         ("std_floor_v1", "v1 std>=1e-2")):
            n = sum(1 for v in cpc.values()
                    if (v.get("sensitivity", {}).get(key) or {}).get("passes"))
            print(f"    {lab:<16} {n}/{len(cpc)}")
        print(f"    {'主口径 n_valid>=64':<16} {npass}/{len(cpc)}")
        print("\n  逐组合（主口径）：")
        for c, v in cpc.items():
            el = v.get("eligibility", {})
            print(f"    {c:<16} {'pass' if v.get('passes') else 'FAIL':<5}"
                  f" n={el.get('n_eligible')}/{el.get('n_cubes_total')}"
                  f"  (none={el.get('n_eligible_none')},"
                  f" std_v1={el.get('n_eligible_std_floor_v1')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
