#!/usr/bin/env python3
import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path


CONDS = ("D20", "A", "B", "donor")
PAIR_NAMES = {
    "A-D20": ("A", "D20"),
    "B-D20": ("B", "D20"),
    "B-A": ("B", "A"),
    "donor-A": ("donor", "A"),
}


def geo_group(cube):
    fields = Path(str(cube)).name.split("_")
    if fields[0] == "minicube" and len(fields) >= 5:
        # Tile-style ids: minicube_<index>_<Sentinel tile>_<lat>_<lon>.
        return fields[2]
    if fields[0] == "minicube" and len(fields) >= 4:
        # OOD-st spatial ids: minicube_<index>_<lat>_<lon>.
        return f"lat={fields[2]}_lon={fields[3]}"
    return fields[0]


def num(row, key):
    value = row.get(key, "")
    return float(value) if value not in ("", "nan", "NaN") else float("nan")


def mean(values):
    return sum(values) / len(values) if values else float("nan")


def geo_bootstrap(values_by_group, reps=2000, seed=20260908):
    groups = list(values_by_group.values())
    if len(groups) < 2:
        return float("nan"), float("nan"), len(groups)
    rng = random.Random(seed)
    estimates = []
    group_means = [mean(x) for x in groups]
    for _ in range(reps):
        sample = [group_means[rng.randrange(len(group_means))] for _ in group_means]
        estimates.append(mean(sample))
    estimates.sort()
    lo = estimates[int(0.025 * (len(estimates) - 1))]
    hi = estimates[int(0.975 * (len(estimates) - 1))]
    return lo, hi, len(groups)


def write_csv(path, rows):
    fields = list(rows[0]) if rows else []
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def markdown_table(path, title, rows, columns):
    with path.open("w") as fh:
        fh.write(f"# {title}\n\n")
        fh.write("| " + " | ".join(columns) + " |\n")
        fh.write("|" + "|".join("---" for _ in columns) + "|\n")
        for row in rows:
            fh.write("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--split", default="iid_matched_donor")
    ap.add_argument("--matched-manifest", type=Path, required=True)
    args = ap.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "tables").mkdir(exist_ok=True); (args.out / "figures").mkdir(exist_ok=True)
    with args.input.open(newline="") as fh:
        source_rows = list(csv.DictReader(fh))
    with args.matched_manifest.open(newline="", encoding="utf-8") as fh:
        matched_rows = list(csv.DictReader(fh))
    cubes = defaultdict(lambda: {"cube": "", "geo_group": "", "rows": {}})
    for row in source_rows:
        key = row["dataset_index"]
        item = cubes[key]; item["cube"] = row["cube"]; item["geo_group"] = geo_group(row["cube"])
        item["rows"][int(row["suffix_horizon"])] = row
    expected_horizons = set(range(1, 11))
    # Validity is evaluated per cube and per scope. A cube with an invalid mask at
    # one horizon must not erase its other valid horizons from the formal table.
    scopes = {"full_suffix_1_to_10": expected_horizons, "endpoint_h10": {10}}
    cube_scope = defaultdict(dict)
    exclusions = defaultdict(int)
    for scope, horizons in scopes.items():
        for key, item in cubes.items():
            valid_horizons = []
            for h in horizons:
                row = item["rows"].get(h)
                if row is None:
                    continue
                try:
                    valid = int(float(row["n_valid"])) > 0 and all(math.isfinite(num(row, f"{c}_sse")) for c in CONDS)
                except (TypeError, ValueError):
                    valid = False
                if valid:
                    valid_horizons.append(h)
            if not valid_horizons:
                exclusions[(scope, "no_common_valid_horizon")] += 1
                continue
            agg = {}
            target_sum = sum(num(item["rows"][h], "target_sum") for h in valid_horizons)
            target_sum_sq = sum(num(item["rows"][h], "target_sum_sq") for h in valid_horizons)
            for c in CONDS:
                sse = sum(num(item["rows"][h], f"{c}_sse") for h in valid_horizons)
                n = sum(int(float(item["rows"][h]["n_valid"])) for h in valid_horizons)
                abs_sum = sum(num(item["rows"][h], f"{c}_sum_abs") for h in valid_horizons)
                agg[c] = {"sse": sse, "n": n, "abs": abs_sum, "rmse": math.sqrt(sse / n), "mae": abs_sum / n,
                          "target_sum": target_sum, "target_sum_sq": target_sum_sq}
            cube_scope[key][scope] = {"agg": agg, "horizons": valid_horizons}
    exclusion_rows = [{"scope": scope, "reason": reason, "count": count} for (scope, reason), count in sorted(exclusions.items())]
    write_csv(args.out / "tables/exclusions.csv", exclusion_rows or [{"scope": "all", "reason": "none", "count": 0}])

    summary = []; paired = []
    scope_items = {}
    for scope, horizons in scopes.items():
        scope_items[scope] = {key: value[scope] for key, value in cube_scope.items() if scope in value}
        for c in CONDS:
            sse = sum(v["agg"][c]["sse"] for v in scope_items[scope].values())
            n = sum(v["agg"][c]["n"] for v in scope_items[scope].values())
            target_sum = sum(v["agg"][c]["target_sum"] for v in scope_items[scope].values())
            target_sum_sq = sum(v["agg"][c]["target_sum_sq"] for v in scope_items[scope].values())
            target_sst = target_sum_sq - (target_sum * target_sum / n)
            rmses = [v["agg"][c]["rmse"] for v in scope_items[scope].values()]
            summary.append({"split": args.split, "scope": scope, "condition": c, "n_cubes": len(rmses),
                            "n_cube_horizon_pairs": sum(len(v["horizons"]) for v in scope_items[scope].values()),
                            "excluded_cubes": len(cubes) - len(rmses), "n_valid": n,
                            "pooled_rmse": math.sqrt(sse / n), "pooled_r2": 1.0 - sse / target_sst if target_sst > 0 else float("nan"),
                            "mean_cube_rmse": mean(rmses),
                            "pooled_mae": sum(v["agg"][c]["abs"] for v in scope_items[scope].values()) / n,
                            "n_geo_groups": len({cubes[key]["geo_group"] for key in scope_items[scope]})})
        for label, (left, right) in PAIR_NAMES.items():
            deltas = [v["agg"][left]["rmse"] - v["agg"][right]["rmse"] for v in scope_items[scope].values()]
            mse_deltas = [(v["agg"][left]["sse"] / v["agg"][left]["n"]) - (v["agg"][right]["sse"] / v["agg"][right]["n"]) for v in scope_items[scope].values()]
            by_geo = defaultdict(list); by_geo_mse = defaultdict(list)
            for key, v in scope_items[scope].items():
                by_geo[cubes[key]["geo_group"]].append(v["agg"][left]["rmse"] - v["agg"][right]["rmse"])
                by_geo_mse[cubes[key]["geo_group"]].append((v["agg"][left]["sse"] / v["agg"][left]["n"]) - (v["agg"][right]["sse"] / v["agg"][right]["n"]))
            lo, hi, groups = geo_bootstrap(by_geo, seed=20260908 + len(paired))
            mse_lo, mse_hi, _ = geo_bootstrap(by_geo_mse, seed=20300908 + len(paired))
            paired.append({"split": args.split, "scope": scope, "comparison": label, "left": left, "right": right,
                           "n_cubes": len(deltas), "excluded_cubes": len(cubes) - len(deltas),
                           "n_cube_horizon_pairs": sum(len(v["horizons"]) for v in scope_items[scope].values()),
                           "mean_cube_rmse_difference": mean(deltas),
                           "median_cube_rmse_difference": sorted(deltas)[len(deltas)//2],
                           "mean_cube_mse_difference": mean(mse_deltas),
                           "median_cube_mse_difference": sorted(mse_deltas)[len(mse_deltas)//2],
                           "geo_groups": groups, "geo_cluster_bootstrap_ci95_low": lo,
                           "geo_cluster_bootstrap_ci95_high": hi,
                           "geo_cluster_mse_ci95_low": mse_lo, "geo_cluster_mse_ci95_high": mse_hi})

    write_csv(args.out / "tables/summary_by_condition.csv", summary)
    write_csv(args.out / "tables/paired_differences.csv", paired)
    markdown_table(args.out / "tables/Table_6B_common_suffix_formal.md", "Table 6B. Formal common-suffix results (matched-donor protocol)",
                   summary, ["scope", "condition", "n_cubes", "n_cube_horizon_pairs", "excluded_cubes", "n_valid", "pooled_rmse", "pooled_r2", "mean_cube_rmse", "pooled_mae", "n_geo_groups"])
    markdown_table(args.out / "tables/Table_4B_state_intervention_formal.md", "Table 4B. Formal intermediate-state intervention (matched-donor protocol)",
                   [r for r in paired if r["comparison"] == "donor-A"],
                   ["scope", "comparison", "n_cubes", "n_cube_horizon_pairs", "excluded_cubes", "mean_cube_mse_difference", "median_cube_mse_difference", "geo_groups", "geo_cluster_mse_ci95_low", "geo_cluster_mse_ci95_high", "mean_cube_rmse_difference"])
    markdown_table(args.out / "tables/paired_differences.md", "Paired differences and geographic bootstrap intervals", paired,
                   ["scope", "comparison", "n_cubes", "n_cube_horizon_pairs", "excluded_cubes", "mean_cube_mse_difference", "median_cube_mse_difference", "geo_groups", "geo_cluster_mse_ci95_low", "geo_cluster_mse_ci95_high", "mean_cube_rmse_difference"])

    # State-distance and process/difference visualization for Fig. 7.
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        horizons = list(range(1, 11))
        curves = {c: [] for c in CONDS}
        for h in horizons:
            for c in CONDS:
                vals = []
                for item in cubes.values():
                    row = item["rows"].get(h)
                    if row is not None and int(float(row["n_valid"])) > 0 and all(math.isfinite(num(row, f"{x}_sse")) for x in CONDS):
                        vals.append(math.sqrt(num(row, f"{c}_sse") / int(float(row["n_valid"]))))
                curves[c].append(mean(vals))
        fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
        ax = axes[0, 0]
        for c, label in (("D20", "D direct"), ("A", "A [10]"), ("B", "B [5,5]"), ("donor", "matched-state donor")):
            ax.plot(horizons, curves[c], marker="o", linewidth=2, label=label)
        ax.set(title="Common-suffix error trajectory", xlabel="Suffix horizon", ylabel="Mean cube RMSE"); ax.grid(alpha=.25); ax.legend()
        ax = axes[0, 1]
        for label, (left, right) in (("A-D", ("A", "D20")), ("B-D", ("B", "D20")), ("B-A", ("B", "A")), ("donor-A", ("donor", "A"))):
            vals = []
            for h in horizons:
                d = []
                for item in cubes.values():
                    row = item["rows"].get(h)
                    if row is not None and int(float(row["n_valid"])) > 0 and all(math.isfinite(num(row, f"{x}_sse")) for x in CONDS):
                        n = int(float(row["n_valid"]))
                        d.append(math.sqrt(num(row, f"{left}_sse") / n) - math.sqrt(num(row, f"{right}_sse") / n))
                vals.append(mean(d))
            ax.plot(horizons, vals, marker="o", label=label)
        ax.axhline(0, color="black", linewidth=1); ax.set(title="Paired RMSE difference by horizon", xlabel="Suffix horizon", ylabel="RMSE difference"); ax.grid(alpha=.25); ax.legend()
        ax = axes[1, 0]
        endpoint_items = scope_items["endpoint_h10"]
        state_ab = [num(cubes[key]["rows"][10], "state_A_B_l1") for key in endpoint_items]
        state_ad = [num(cubes[key]["rows"][10], "state_A_donor_l1") for key in endpoint_items]
        ax.boxplot([state_ab, state_ad], labels=["A vs B state", "A vs donor state"], showfliers=False)
        ax.set(title="Intermediate-state distance", ylabel="Raw state L1"); ax.grid(axis="y", alpha=.25)
        ax = axes[1, 1]
        delta = [v["agg"]["donor"]["rmse"] - v["agg"]["A"]["rmse"] for v in scope_items["full_suffix_1_to_10"].values()]
        ax.hist(delta, bins=40, color="#4c78a8", alpha=.85); ax.axvline(0, color="black", linewidth=1)
        ax.set(title="State-donor minus normal A", xlabel="Full-suffix cube RMSE difference", ylabel="Cubes"); ax.grid(axis="y", alpha=.25)
        fig.suptitle(f"Fig. 7. Formal common suffix and matched-state intervention ({args.split}, n={len(scope_items['full_suffix_1_to_10'])})")
        fig.savefig(args.out / "figures/Fig7_formal_common_suffix_state_intervention.png", dpi=180)
        plt.close(fig)
    except Exception as exc:
        (args.out / "figures/Fig7_generation_error.txt").write_text(f"{type(exc).__name__}: {exc}\n")
        raise
    distances = sorted(float(r["match_distance"]) for r in matched_rows if r.get("match_distance", "") not in ("", "nan", "NaN"))
    distance_quantiles = {}
    if distances:
        for q in (0.0, 0.25, 0.5, 0.75, 1.0):
            pos = min(len(distances) - 1, int(q * (len(distances) - 1)))
            distance_quantiles[str(q)] = distances[pos]
    (args.out / "evidence_manifest.json").write_text(json.dumps({
        "split": args.split, "source_csv": str(args.input), "source_rows": len(source_rows),
        "total_cubes": len(cubes), "usable_cubes_by_scope": {scope: len(items) for scope, items in scope_items.items()},
        "excluded_by_scope": {f"{scope}:{reason}": count for (scope, reason), count in exclusions.items()},
        "scopes": {k: sorted(v) for k, v in scopes.items()},
        "conditions": {"D20": "direct query from initial state", "A": "[10] to step 10 then shared 10->20 suffix", "B": "[5,5] to step 10 then shared 10->20 suffix", "donor": "matched intermediate-state replacement with receiver prior/geo/weather"},
        "donor_rule": "A14B frozen same-year-month matched donor; standardized first-10 observed NDVI summaries plus 0.5*Hellinger ESA WorldCover histogram; deterministic path tie-break; no future target or model outcome used; reuse cap 1",
        "matched_manifest": str(args.matched_manifest), "matched_manifest_rows": len(matched_rows),
        "match_distance_quantiles": distance_quantiles,
        "excluded_reasons": {f"{scope}:{reason}": count for (scope, reason), count in exclusions.items()},
    }, ensure_ascii=False, indent=2) + "\n")
    print(f"built evidence for scopes { {scope: len(items) for scope, items in scope_items.items()} } from {len(cubes)} cubes in {args.out}")


if __name__ == "__main__":
    main()
