#!/usr/bin/env python3
"""R02-A2: freeze the audited spatial grouping and finish the A1 statistics.

Read-only postprocessing of the R02-A1 sufficient statistics
(``PER_RECEIVER_HORIZON.csv``). No inference, no rescoring, no A1 file edits.

What this script does
---------------------
1. Verifies the A1 key coverage (receiver x model x path x k) and rebuilds the
   receiver-equal-weight full-suffix MSE point estimates from sufficient
   statistics alone, then compares them with the delivered A1 summaries.
2. Derives ``receiver_id -> group_id`` with the *audited* spatial grouping rule
   taken verbatim from
   ``/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/code/build_matched_donor_evidence_v1.py:20-28``
   (identical to ``evidence_closure_final/statistics/build_ab_path_paired_ci.py``).
   The A1 adapter carried its own simplified, self-declared non-authoritative
   copy of that rule, so the column in the A1 CSV is cross-checked, not trusted.
3. Runs a paired spatial-group bootstrap (2000 draws, seed 20260914) that
   resamples groups with replacement and *retains every receiver inside a drawn
   group together with its model/path pairings*, recomputing the
   receiver-equal-weight estimate on the pooled multiset. This is deliberately
   NOT "average group means, then equal-weight groups".

Estimator contract
------------------
* receiver full-suffix MSE = sum(sse over k=1..10) / sum(n_valid over k=1..10),
  defined only when all ten horizons are present and the total valid count > 0.
* point estimate = unweighted mean over receivers (receiver-equal weight).
* bootstrap replicate = the same receiver-equal mean over the pooled multiset of
  receivers contributed by the drawn groups (count-weighted, so a group drawn
  twice contributes its receivers twice).
* interval = percentile interval, index rule int(0.025*(B-1)) / int(0.975*(B-1)),
  matching the audited ``geo_bootstrap`` convention in the same repository.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

MODELS = ("C0R", "C1")
PATHS = ("D20", "A", "B", "C")
PATH_LABEL = {"D20": "D_direct_11_20"}
HORIZONS = tuple(range(1, 11))
DRAWS = 2000
SEED = 20260914

GROUP_RULE_SOURCE = (
    "/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/"
    "code/build_matched_donor_evidence_v1.py:20-28"
)


def geo_group(cube: str) -> str:
    """The audited spatial grouping rule (verbatim semantics, no extensions)."""
    fields = Path(str(cube)).name.split("_")
    if fields[0] == "minicube" and len(fields) >= 5:
        # Tile-style ids: minicube_<index>_<Sentinel tile>_<lat>_<lon>.
        return fields[2]
    if fields[0] == "minicube" and len(fields) >= 4:
        # OOD-st spatial ids: minicube_<index>_<lat>_<lon>.
        return f"lat={fields[2]}_lon={fields[3]}"
    return fields[0]


def a1_adapter_group(cube: str) -> str:
    """A1's own simplified rule, kept only to detect disagreements."""
    fields = Path(str(cube)).name.split("_")
    return fields[2] if len(fields) >= 3 and fields[0] == "minicube" else "UNCONFIRMED"


def percentile_interval(estimates, alpha=0.025):
    estimates = sorted(estimates)
    n = len(estimates)
    lo = estimates[int(alpha * (n - 1))]
    hi = estimates[int((1.0 - alpha) * (n - 1))]
    return lo, hi


class Target:
    """One bootstrap target: a fixed receiver set and per-receiver values."""

    __slots__ = ("name", "receivers", "values")

    def __init__(self, name, receivers, values):
        self.name = name
        self.receivers = receivers
        self.values = values

    def group_tables(self, receiver_group):
        """Return (group_ids, sum_of_values, n_receivers, per_group_arrays)."""
        agg = defaultdict(lambda: [0.0, 0])
        arrays = defaultdict(list)
        for r, v in zip(self.receivers, self.values):
            g = receiver_group[r]
            agg[g][0] += v
            agg[g][1] += 1
            arrays[g].append((r, v))
        groups = sorted(agg)
        return groups, agg, arrays


def bootstrap_target(target, receiver_group, draws=DRAWS, seed=SEED, verify_draws=50):
    """Paired spatial-group bootstrap of a receiver-equal-weight mean.

    Groups are drawn with replacement; every receiver of a drawn group enters
    the pooled multiset with its own value, so the replicate is the
    receiver-equal mean over the pooled receivers (never a mean of group means).
    """
    groups, agg, arrays = target.group_tables(receiver_group)
    if len(groups) < 2:
        return {
            "n_groups": len(groups),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "estimates": [],
            "degenerate": True,
        }
    rng = random.Random(seed)
    gidx = range(len(groups))
    estimates = []
    for _ in range(draws):
        num = 0.0
        den = 0
        for _ in gidx:
            g = groups[rng.randrange(len(groups))]
            s, n = agg[g]
            num += s
            den += n
        estimates.append(num / den if den else float("nan"))

    # Self-check: the count-weighted shortcut must equal an explicit
    # concatenation of receivers for the same draws.
    rng_check = random.Random(seed)
    for i in range(min(verify_draws, draws)):
        pooled = []
        for _ in gidx:
            g = groups[rng_check.randrange(len(groups))]
            pooled.extend(v for _r, v in arrays[g])
        explicit = sum(pooled) / len(pooled)
        if not math.isclose(explicit, estimates[i], rel_tol=1e-12, abs_tol=1e-15):
            raise RuntimeError(f"bootstrap_replicate_mismatch:{target.name}:{i}")
    lo, hi = percentile_interval(estimates)
    below = sum(1 for e in estimates if e < 0.0)
    return {
        "n_groups": len(groups),
        "ci_low": lo,
        "ci_high": hi,
        "frac_draws_below_zero": below / len(estimates),
        "estimates": estimates,
        "degenerate": False,
    }


def write_csv(path: Path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_a1_csv(path: Path):
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a1-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    a1 = args.a1_dir
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- load
    rows = []
    with (a1 / "PER_RECEIVER_HORIZON.csv").open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append(
                {
                    "dataset_index": int(r["dataset_index"]),
                    "cube": r["cube"],
                    "a1_geo_group": r["geo_group"],
                    "model": r["model"],
                    "path": r["path"],
                    "k": int(r["k"]),
                    "absolute_h": int(r["absolute_h"]),
                    "n_valid": int(r["n_valid"]),
                    "sse": float(r["sse"]),
                    "exclude_reason": r.get("exclude_reason", ""),
                }
            )

    gates = {}
    keys = [(r["dataset_index"], r["model"], r["path"], r["k"]) for r in rows]
    gates["rows"] = len(rows)
    gates["unique_keys"] = len(set(keys))
    gates["duplicate_keys"] = len(keys) - len(set(keys))
    nonzero_exclude = sum(1 for r in rows if r["exclude_reason"])
    gates["rows_with_exclude_reason"] = nonzero_exclude
    bad = [
        r
        for r in rows
        if r["n_valid"] > 0 and not (math.isfinite(r["sse"]) and r["sse"] >= 0.0)
    ]
    gates["nonfinite_or_negative_sse_with_valid_pixels"] = len(bad)
    bad_abs = [
        r
        for r in rows
        if r["absolute_h"] != 10 + r["k"]
    ]
    gates["absolute_h_not_10_plus_k"] = len(bad_abs)
    gates["gate_pass"] = (
        gates["duplicate_keys"] == 0
        and gates["nonfinite_or_negative_sse_with_valid_pixels"] == 0
        and gates["absolute_h_not_10_plus_k"] == 0
    )

    # ------------------------------------------------- receiver -> group map
    receiver_cube = {}
    cube_conflicts = 0
    for r in rows:
        d, c = r["dataset_index"], r["cube"]
        if d in receiver_cube and receiver_cube[d] != c:
            cube_conflicts += 1
        receiver_cube[d] = c
    receiver_group = {d: geo_group(c) for d, c in receiver_cube.items()}

    map_rows = []
    for d in sorted(receiver_cube):
        c = receiver_cube[d]
        audited = geo_group(c)
        adapter = a1_adapter_group(c)
        map_rows.append(
            {
                "receiver_id": d,
                "dataset_index": d,
                "cube": c,
                "group_id": audited,
                "group_rule_source": GROUP_RULE_SOURCE,
                "a1_csv_geo_group": "",
                "a1_csv_geo_group_matches_audited": "",
                "a1_adapter_rule_agrees": str(adapter == audited),
            }
        )
    a1_group_by_receiver = {}
    a1_group_conflict = 0
    for r in rows:
        d = r["dataset_index"]
        prev = a1_group_by_receiver.setdefault(d, r["a1_geo_group"])
        if prev != r["a1_geo_group"]:
            a1_group_conflict += 1
    for row in map_rows:
        d = row["dataset_index"]
        row["a1_csv_geo_group"] = a1_group_by_receiver.get(d, "")
        row["a1_csv_geo_group_matches_audited"] = str(
            a1_group_by_receiver.get(d, "") == row["group_id"]
        )
    write_csv(
        out / "RECEIVER_GROUP_MAP.csv",
        [
            "receiver_id",
            "dataset_index",
            "cube",
            "group_id",
            "group_rule_source",
            "a1_csv_geo_group",
            "a1_csv_geo_group_matches_audited",
            "a1_adapter_rule_agrees",
        ],
        map_rows,
    )

    group_members = defaultdict(list)
    for d, g in receiver_group.items():
        group_members[g].append(d)
    sizes = sorted((len(v) for v in group_members.values()), reverse=True)

    def quantile(sorted_desc, q):
        if not sorted_desc:
            return 0
        idx = min(len(sorted_desc) - 1, int((1.0 - q) * len(sorted_desc)))
        return sorted_desc[idx]

    size_rows = [
        {
            "group_id": g,
            "n_receivers": len(v),
            "receiver_dataset_indices": ";".join(str(x) for x in sorted(v)),
        }
        for g, v in sorted(group_members.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ]
    write_csv(out / "GROUP_SIZE_DISTRIBUTION.csv", list(size_rows[0]), size_rows)

    cubes_per_receiver = defaultdict(set)
    for d, c in receiver_cube.items():
        cubes_per_receiver[c].add(d)
    shared_cubes = sum(1 for c, s in cubes_per_receiver.items() if len(s) > 1)
    n_cubes = len(cubes_per_receiver)

    # ------------------------------------------------- point estimates
    full = {}
    ks_seen = defaultdict(set)
    for r in rows:
        key = (r["dataset_index"], r["model"], r["path"])
        a = full.setdefault(key, {"sse": 0.0, "n": 0})
        ks_seen[key].add(r["k"])
        if r["n_valid"]:
            a["sse"] += r["sse"]
            a["n"] += r["n_valid"]
    qualified = {
        k: v["sse"] / v["n"]
        for k, v in full.items()
        if len(ks_seen[k]) == 10 and v["n"] > 0
    }

    # k=10 independent qualification set
    k10 = {}
    for r in rows:
        if r["k"] == 10 and r["n_valid"] > 0:
            k10[(r["dataset_index"], r["model"], r["path"])] = r["sse"] / r["n_valid"]

    # ------------------------------------------------- A1 recheck
    recheck = []
    a1_summary = read_a1_csv(a1 / "SUMMARY_CORRECTED.csv")
    if a1_summary:
        for row in a1_summary:
            m, p = row["model"], row["path"]
            vals = [v for (d, mm, pp), v in qualified.items() if mm == m and pp == p]
            mine = sum(vals) / len(vals) if vals else float("nan")
            recheck.append(
                {
                    "quantity": "mean_receiver_full_mse",
                    "model": m,
                    "path": p,
                    "a1_reported": row["mean_receiver_full_mse"],
                    "recomputed": f"{mine:.17g}",
                    "abs_diff": f"{abs(mine - float(row['mean_receiver_full_mse'])):.3e}",
                    "a1_n_receivers": row["n_receivers"],
                    "recomputed_n": len(vals),
                }
            )
    a1_delta = read_a1_csv(a1 / "MAIN_DELTA.csv")
    paired_sets = {}
    if a1_delta:
        for row in a1_delta:
            p = row["path"]
            common = sorted(
                {d for (d, m, pp) in qualified if pp == p and m == "C0R"}
                & {d for (d, m, pp) in qualified if pp == p and m == "C1"}
            )
            paired_sets[p] = common
            vals = [qualified[(d, "C1", p)] - qualified[(d, "C0R", p)] for d in common]
            mine = sum(vals) / len(vals) if vals else float("nan")
            recheck.append(
                {
                    "quantity": "mean_delta_c1_minus_c0r",
                    "model": "C1-C0R",
                    "path": p,
                    "a1_reported": row["mean_delta_c1_minus_c0r"],
                    "recomputed": f"{mine:.17g}",
                    "abs_diff": f"{abs(mine - float(row['mean_delta_c1_minus_c0r'])):.3e}",
                    "a1_n_receivers": row["n_paired_receivers"],
                    "recomputed_n": len(vals),
                }
            )
    a1_deg = read_a1_csv(a1 / "DEGRADATION_VS_DIRECT.csv")
    deg_sets = {}
    if a1_deg:
        for row in a1_deg:
            m, p = row["model"], row["path"]
            common = sorted(
                {d for (d, mm, pp) in qualified if mm == m and pp == p}
                & {d for (d, mm, pp) in qualified if mm == m and pp == "D20"}
            )
            deg_sets[(m, p)] = common
            vals = [qualified[(d, m, p)] - qualified[(d, m, "D20")] for d in common]
            mine = sum(vals) / len(vals) if vals else float("nan")
            recheck.append(
                {
                    "quantity": "mean_change_vs_D20",
                    "model": m,
                    "path": p,
                    "a1_reported": row["mean_change_vs_D20"],
                    "recomputed": f"{mine:.17g}",
                    "abs_diff": f"{abs(mine - float(row['mean_change_vs_D20'])):.3e}",
                    "a1_n_receivers": row["n_paired_receivers"],
                    "recomputed_n": len(vals),
                }
            )
    a1_k10 = read_a1_csv(a1 / "ENDPOINT_K10.csv")
    k10_sets = {}
    if a1_k10:
        for row in a1_k10:
            m, p = row["model"], row["path"]
            sel = sorted(d for (d, mm, pp) in k10 if mm == m and pp == p)
            k10_sets[(m, p)] = sel
            vals = [k10[(d, m, p)] for d in sel]
            mine = sum(vals) / len(vals) if vals else float("nan")
            recheck.append(
                {
                    "quantity": "mean_receiver_mse_k10",
                    "model": m,
                    "path": p,
                    "a1_reported": row["mean_receiver_mse_k10"],
                    "recomputed": f"{mine:.17g}",
                    "abs_diff": f"{abs(mine - float(row['mean_receiver_mse_k10'])):.3e}",
                    "a1_n_receivers": row["n_receivers_k10"],
                    "recomputed_n": len(vals),
                }
            )
    write_csv(
        out / "A2_POINT_ESTIMATES_RECHECK.csv",
        ["quantity", "model", "path", "a1_reported", "recomputed", "abs_diff", "a1_n_receivers", "recomputed_n"],
        recheck,
    )
    max_abs_diff = max((float(r["abs_diff"]) for r in recheck), default=float("nan"))
    count_mismatch = sum(
        1 for r in recheck if str(r["a1_n_receivers"]) != str(r["recomputed_n"])
    )

    # ------------------------------------------------- bootstrap targets
    targets = []

    # (1) per model/path receiver-equal full-suffix MSE
    mse_meta = {}
    for m in MODELS:
        for p in PATHS:
            sel = sorted(d for (d, mm, pp) in qualified if mm == m and pp == p)
            mse_meta[(m, p)] = sel
            targets.append(
                Target(f"mse|{m}|{p}", sel, [qualified[(d, m, p)] for d in sel])
            )

    # (2) paired C1-C0R per path
    for p in PATHS:
        sel = paired_sets.get(p, [])
        targets.append(
            Target(
                f"delta_c1_minus_c0r|{p}",
                sel,
                [qualified[(d, "C1", p)] - qualified[(d, "C0R", p)] for d in sel],
            )
        )

    # (3) degradation vs own D20, per model/path
    for m in MODELS:
        for p in ("A", "B", "C"):
            sel = deg_sets.get((m, p), [])
            targets.append(
                Target(
                    f"degradation_vs_D20|{m}|{p}",
                    sel,
                    [qualified[(d, m, p)] - qualified[(d, m, "D20")] for d in sel],
                )
            )

    # (4) difference in degradation between models (C1 minus C0R)
    degdiff_sets = {}
    for p in ("A", "B", "C"):
        sel = sorted(set(deg_sets.get(("C1", p), [])) & set(deg_sets.get(("C0R", p), [])))
        degdiff_sets[p] = sel
        targets.append(
            Target(
                f"degradation_model_diff|{p}",
                sel,
                [
                    (qualified[(d, "C1", p)] - qualified[(d, "C1", "D20")])
                    - (qualified[(d, "C0R", p)] - qualified[(d, "C0R", "D20")])
                    for d in sel
                ],
            )
        )

    # (5) k=10 endpoint, independent qualification set
    for m in MODELS:
        for p in PATHS:
            sel = k10_sets.get((m, p), [])
            targets.append(Target(f"mse_k10|{m}|{p}", sel, [k10[(d, m, p)] for d in sel]))
    for p in PATHS:
        sel = sorted(
            set(k10_sets.get(("C0R", p), [])) & set(k10_sets.get(("C1", p), []))
        )
        targets.append(
            Target(
                f"delta_k10_c1_minus_c0r|{p}",
                sel,
                [k10[(d, "C1", p)] - k10[(d, "C0R", p)] for d in sel],
            )
        )

    results = {}
    for t in targets:
        results[t.name] = bootstrap_target(t, receiver_group)
    results["_point"] = {}

    # ------------------------------------------------- result tables
    def point(sel, value_fn):
        vals = [value_fn(d) for d in sel]
        return sum(vals) / len(vals) if vals else float("nan")

    mse_rows = []
    for m in MODELS:
        for p in PATHS:
            sel = mse_meta[(m, p)]
            r = results[f"mse|{m}|{p}"]
            mse_rows.append(
                {
                    "model": m,
                    "path": p,
                    "n_receivers": len(sel),
                    "n_groups": r["n_groups"],
                    "mean_receiver_full_mse": f"{point(sel, lambda d: qualified[(d, m, p)]):.17g}",
                    "ci95_low": f"{r['ci_low']:.17g}",
                    "ci95_high": f"{r['ci_high']:.17g}",
                }
            )
    write_csv(
        out / "A2_MSE_CI.csv",
        ["model", "path", "n_receivers", "n_groups", "mean_receiver_full_mse", "ci95_low", "ci95_high"],
        mse_rows,
    )

    delta_rows = []
    for p in PATHS:
        sel = paired_sets.get(p, [])
        r = results[f"delta_c1_minus_c0r|{p}"]
        delta_rows.append(
            {
                "path": p,
                "prefix": PATH_LABEL.get(p, p),
                "n_paired_receivers": len(sel),
                "n_groups": r["n_groups"],
                "mean_c0r": f"{point(sel, lambda d: qualified[(d, 'C0R', p)]):.17g}",
                "mean_c1": f"{point(sel, lambda d: qualified[(d, 'C1', p)]):.17g}",
                "mean_delta_c1_minus_c0r": f"{point(sel, lambda d: qualified[(d, 'C1', p)] - qualified[(d, 'C0R', p)]):.17g}",
                "ci95_low": f"{r['ci_low']:.17g}",
                "ci95_high": f"{r['ci_high']:.17g}",
                "ci_crosses_zero": str(r["ci_low"] <= 0.0 <= r["ci_high"]),
            }
        )
    write_csv(
        out / "A2_MAIN_DELTA_CI.csv",
        ["path", "prefix", "n_paired_receivers", "n_groups", "mean_c0r", "mean_c1", "mean_delta_c1_minus_c0r", "ci95_low", "ci95_high", "ci_crosses_zero"],
        delta_rows,
    )

    deg_rows = []
    for m in MODELS:
        for p in ("A", "B", "C"):
            sel = deg_sets.get((m, p), [])
            r = results[f"degradation_vs_D20|{m}|{p}"]
            deg_rows.append(
                {
                    "model": m,
                    "path": p,
                    "n_paired_receivers": len(sel),
                    "n_groups": r["n_groups"],
                    "mean_change_vs_D20": f"{point(sel, lambda d: qualified[(d, m, p)] - qualified[(d, m, 'D20')]):.17g}",
                    "ci95_low": f"{r['ci_low']:.17g}",
                    "ci95_high": f"{r['ci_high']:.17g}",
                    "ci_crosses_zero": str(r["ci_low"] <= 0.0 <= r["ci_high"]),
                }
            )
    write_csv(
        out / "A2_DEGRADATION_CI.csv",
        ["model", "path", "n_paired_receivers", "n_groups", "mean_change_vs_D20", "ci95_low", "ci95_high", "ci_crosses_zero"],
        deg_rows,
    )

    degdiff_rows = []
    for p in ("A", "B", "C"):
        sel = degdiff_sets[p]
        r = results[f"degradation_model_diff|{p}"]
        degdiff_rows.append(
            {
                "path": p,
                "n_paired_receivers": len(sel),
                "n_groups": r["n_groups"],
                "degradation_c0r": f"{point(sel, lambda d: qualified[(d, 'C0R', p)] - qualified[(d, 'C0R', 'D20')]):.17g}",
                "degradation_c1": f"{point(sel, lambda d: qualified[(d, 'C1', p)] - qualified[(d, 'C1', 'D20')]):.17g}",
                "degradation_diff_c1_minus_c0r": f"{point(sel, lambda d: (qualified[(d, 'C1', p)] - qualified[(d, 'C1', 'D20')]) - (qualified[(d, 'C0R', p)] - qualified[(d, 'C0R', 'D20')])):.17g}",
                "ci95_low": f"{r['ci_low']:.17g}",
                "ci95_high": f"{r['ci_high']:.17g}",
                "ci_crosses_zero": str(r["ci_low"] <= 0.0 <= r["ci_high"]),
            }
        )
    write_csv(
        out / "A2_DEGRADATION_MODEL_DIFF_CI.csv",
        ["path", "n_paired_receivers", "n_groups", "degradation_c0r", "degradation_c1", "degradation_diff_c1_minus_c0r", "ci95_low", "ci95_high", "ci_crosses_zero"],
        degdiff_rows,
    )

    k10_rows = []
    for m in MODELS:
        for p in PATHS:
            sel = k10_sets[(m, p)]
            r = results[f"mse_k10|{m}|{p}"]
            k10_rows.append(
                {
                    "model": m,
                    "path": p,
                    "n_receivers_k10": len(sel),
                    "n_groups": r["n_groups"],
                    "mean_receiver_mse_k10": f"{point(sel, lambda d: k10[(d, m, p)]):.17g}",
                    "ci95_low": f"{r['ci_low']:.17g}",
                    "ci95_high": f"{r['ci_high']:.17g}",
                }
            )
    write_csv(
        out / "A2_ENDPOINT_K10_CI.csv",
        ["model", "path", "n_receivers_k10", "n_groups", "mean_receiver_mse_k10", "ci95_low", "ci95_high"],
        k10_rows,
    )

    k10_delta_rows = []
    for p in PATHS:
        sel = sorted(set(k10_sets[("C0R", p)]) & set(k10_sets[("C1", p)]))
        r = results[f"delta_k10_c1_minus_c0r|{p}"]
        k10_delta_rows.append(
            {
                "path": p,
                "n_paired_receivers_k10": len(sel),
                "n_groups": r["n_groups"],
                "mean_delta_c1_minus_c0r_k10": f"{point(sel, lambda d: k10[(d, 'C1', p)] - k10[(d, 'C0R', p)]):.17g}",
                "ci95_low": f"{r['ci_low']:.17g}",
                "ci95_high": f"{r['ci_high']:.17g}",
                "ci_crosses_zero": str(r["ci_low"] <= 0.0 <= r["ci_high"]),
            }
        )
    write_csv(
        out / "A2_ENDPOINT_K10_DELTA_CI.csv",
        ["path", "n_paired_receivers_k10", "n_groups", "mean_delta_c1_minus_c0r_k10", "ci95_low", "ci95_high", "ci_crosses_zero"],
        k10_delta_rows,
    )

    meta = {
        "run": "R02-A2 spatial-group statistics closure",
        "inputs": {
            "a1_per_receiver_horizon": str(a1 / "PER_RECEIVER_HORIZON.csv"),
            "a1_dir": str(a1),
            "a1_files_modified": False,
        },
        "grouping": {
            "rule_source": GROUP_RULE_SOURCE,
            "rule": "minicube_<index>_<MgrsTile>_<lat>_<lon> -> fields[2]; minicube_<index>_<lat>_<lon> -> lat=.._lon=..; else fields[0]",
            "group_semantics": "Sentinel-2 MGRS tile id for IID chopped receivers (traceable, from the cube name already present in every A1 row)",
            "n_receivers": len(receiver_cube),
            "n_cubes": n_cubes,
            "cubes_shared_by_multiple_receivers": shared_cubes,
            "n_groups": len(group_members),
            "group_size_min": min(sizes) if sizes else 0,
            "group_size_median_desc_index": quantile(sizes, 0.5),
            "group_size_max": max(sizes) if sizes else 0,
            "receiver_cube_conflicts": cube_conflicts,
            "a1_csv_geo_group_conflicts_within_receiver": a1_group_conflict,
            "a1_csv_geo_group_mismatch_vs_audited": sum(
                1 for r in map_rows if r["a1_csv_geo_group_matches_audited"] == "False"
            ),
            "a1_adapter_rule_mismatch_vs_audited": sum(
                1 for r in map_rows if r["a1_adapter_rule_agrees"] == "False"
            ),
        },
        "estimator": {
            "receiver_full_suffix_mse": "sum(sse k=1..10)/sum(n_valid k=1..10), requires all 10 horizons and n>0",
            "weighting": "receiver equal weight",
            "bootstrap": "paired spatial-group bootstrap, groups drawn with replacement, all receivers of a drawn group retained with their model/path pairings; replicate is the receiver-equal mean over the pooled multiset",
            "not_used": "group-mean-then-equal-weight-groups; independent-pixel bootstrap",
            "draws": DRAWS,
            "seed": SEED,
            "interval": "percentile, index int(0.025*(B-1)) and int(0.975*(B-1))",
        },
        "gates": gates,
        "a1_recheck": {
            "max_abs_diff": max_abs_diff,
            "count_mismatches": count_mismatch,
            "rows_compared": len(recheck),
        },
        "notes": [
            "Marginal 95% intervals are not simultaneous; paths are not selected by significance.",
            "An interval crossing zero is uncertainty, not equivalence.",
            "The interval reflects receiver/group sampling only; it does not cover training randomness.",
        ],
    }
    (out / "A2_RUN_METADATA.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("A2_GATES", json.dumps(gates, ensure_ascii=False))
    print(
        "A2_RECHECK max_abs_diff",
        max_abs_diff,
        "count_mismatches",
        count_mismatch,
        "rows",
        len(recheck),
    )
    print(
        "A2_GROUPS receivers",
        len(receiver_cube),
        "cubes",
        n_cubes,
        "groups",
        len(group_members),
        "min",
        min(sizes) if sizes else 0,
        "max",
        max(sizes) if sizes else 0,
    )
    print(
        "A2_GROUP_COLUMN a1_mismatch",
        meta["grouping"]["a1_csv_geo_group_mismatch_vs_audited"],
        "adapter_mismatch",
        meta["grouping"]["a1_adapter_rule_mismatch_vs_audited"],
    )
    for row in delta_rows:
        print(
            "A2_DELTA",
            row["path"],
            row["mean_delta_c1_minus_c0r"],
            "[",
            row["ci95_low"],
            row["ci95_high"],
            "]",
            "n",
            row["n_paired_receivers"],
            "groups",
            row["n_groups"],
        )
    for row in degdiff_rows:
        print(
            "A2_DEGDIFF",
            row["path"],
            row["degradation_diff_c1_minus_c0r"],
            "[",
            row["ci95_low"],
            row["ci95_high"],
            "]",
        )
    for row in k10_delta_rows:
        print(
            "A2_K10DELTA",
            row["path"],
            row["mean_delta_c1_minus_c0r_k10"],
            "[",
            row["ci95_low"],
            row["ci95_high"],
            "]",
        )


if __name__ == "__main__":
    main()
