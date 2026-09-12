#!/usr/bin/env python3
"""Postprocess existing C1/FSR common-suffix CSVs; no inference or scoring."""

import argparse
import csv
import math
import random
from collections import defaultdict
from pathlib import Path


SPLITS = {
    "iid": {
        "c1": "formal_suffix_v3_iid_full_20260908T100000Z/tables/formal_common_suffix_per_cube_horizon_with_geo.csv",
        "fsr": "fixedstep_r_20260910T110000Z/eval/suffix/iid_chopped/plot_data/formal_common_suffix_per_cube_horizon.csv",
    },
    "ood_t": {
        "c1": "formal_suffix_v3_ood-t_chopped_v4_20260908T113000Z/tables/formal_common_suffix_per_cube_horizon_with_geo.csv",
        "fsr": "fixedstep_r_20260910T110000Z/eval/suffix/ood-t_chopped/plot_data/formal_common_suffix_per_cube_horizon.csv",
    },
    "ood_st": {
        "c1": "formal_suffix_v3_ood-st_chopped_v4_20260908T113000Z/tables/formal_common_suffix_per_cube_horizon_with_geo.csv",
        "fsr": "fixedstep_r_20260910T110000Z/eval/suffix/ood-st_chopped/plot_data/formal_common_suffix_per_cube_horizon.csv",
    },
    "ood_s": {
        "c1": "formal_suffix_v3_ood-s_chopped_repaired_v4_20260909T021700Z/plot_data/formal_common_suffix_per_cube_horizon.csv",
        "fsr": "fixedstep_r_20260910T110000Z/eval/suffix/ood-s_chopped/plot_data/formal_common_suffix_per_cube_horizon.csv",
    },
}

KEYS = ("dataset_index", "cube", "season", "suffix_horizon")


def finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def geo_group(cube):
    """Match the audited evidence builder's spatial grouping rule."""
    fields = Path(str(cube)).name.split("_")
    if fields[0] == "minicube" and len(fields) >= 5:
        return fields[2]
    if fields[0] == "minicube" and len(fields) >= 4:
        return f"lat={fields[2]}_lon={fields[3]}"
    return fields[0]


def read_unique(path):
    rows = {}
    duplicates = 0
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            key = tuple(row[k] for k in KEYS)
            if key in rows:
                duplicates += 1
            rows[key] = row
    return rows, duplicates


def close_enough(a, b):
    if not finite(a) or not finite(b):
        return False
    a = float(a)
    b = float(b)
    return math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-5)


def bootstrap(values_by_geo, draws=2000, seed=20260910):
    groups = sorted(values_by_geo)
    rng = random.Random(seed)
    estimates = []
    for _ in range(draws):
        sampled = [groups[rng.randrange(len(groups))] for _ in groups]
        estimates.append(sum(values_by_geo[g] for g in sampled) / len(sampled))
    estimates.sort()
    return estimates[int(0.025 * draws)], estimates[int(0.975 * draws) - 1]


def process(split, root, out_dir):
    c1, c1_duplicates = read_unique(root / SPLITS[split]["c1"])
    fsr, fsr_duplicates = read_unique(root / SPLITS[split]["fsr"])
    keys = sorted(set(c1) & set(fsr))
    excluded = defaultdict(int)
    details = []

    for key in keys:
        a = c1[key]
        b = fsr[key]
        # Some older plot CSVs carry a stale full-cube geo_group column. Use
        # the audited deterministic grouping rule from build_matched_donor_evidence_v1.py.
        derived_geo = geo_group(key[1])
        if int(a["n_valid"]) <= 0:
            excluded["no_valid_pixels"] += 1
            continue
        if a.get("n_valid") != b.get("n_valid") or not close_enough(a.get("target_sum"), b.get("target_sum")) or not close_enough(a.get("target_sum_sq"), b.get("target_sum_sq")):
            excluded["mask_or_target_mismatch"] += 1
            continue
        if not finite(a.get("A_B_output_mae")) or not finite(b.get("A_B_output_mae")):
            excluded["nonfinite_path_metric"] += 1
            continue
        delta = float(b["A_B_output_mae"]) - float(a["A_B_output_mae"])
        record = {
            "split": split,
            "dataset_index": key[0],
            "cube": key[1],
            "season": key[2],
            "suffix_horizon": key[3],
            "geo_group": derived_geo,
            "n_valid": a["n_valid"],
            "c1_A_B_output_mae": a["A_B_output_mae"],
            "fsr_A_B_output_mae": b["A_B_output_mae"],
            "delta_fsr_minus_c1": f"{delta:.17g}",
        }
        details.append(record)

    cube_means = {}
    by_cube = defaultdict(list)
    for row in details:
        by_cube[(row["dataset_index"], row["cube"], row["season"])].append(float(row["delta_fsr_minus_c1"]))
    for cube, values in by_cube.items():
        cube_means[cube] = sum(values) / len(values)

    # Aggregate once per receiver (dataset_index, cube, season), not once per
    # horizon; otherwise receivers with more valid horizons are overweighted.
    receiver_geo = {}
    for row in details:
        receiver_key = (row["dataset_index"], row["cube"], row["season"])
        receiver_geo[receiver_key] = row["geo_group"]
    geo_cube_means = defaultdict(list)
    for receiver_key, value in cube_means.items():
        geo_cube_means[receiver_geo[receiver_key]].append(value)
    geo_means = {g: sum(v) / len(v) for g, v in geo_cube_means.items()}
    ci_low, ci_high = bootstrap(geo_means) if geo_means else (float("nan"), float("nan"))

    c1_mean = sum(float(r["c1_A_B_output_mae"]) for r in details) / len(details) if details else float("nan")
    fsr_mean = sum(float(r["fsr_A_B_output_mae"]) for r in details) / len(details) if details else float("nan")
    delta_mean = fsr_mean - c1_mean if details else float("nan")
    summary = {
        "split": split,
        "c1_path_mae_mean_cube_horizon": f"{c1_mean:.17g}",
        "fsr_path_mae_mean_cube_horizon": f"{fsr_mean:.17g}",
        "delta_fsr_minus_c1_mean_cube_horizon": f"{delta_mean:.17g}",
        "delta_fsr_minus_c1_geo_equal_point": f"{(sum(geo_means.values()) / len(geo_means)) if geo_means else float('nan'):.17g}",
        "delta_fsr_minus_c1_geo_bootstrap_ci95_low": f"{ci_low:.17g}",
        "delta_fsr_minus_c1_geo_bootstrap_ci95_high": f"{ci_high:.17g}",
        "n_cube_horizon_pairs": len(details),
        "n_cubes": len(cube_means),
        "n_geo_groups": len(geo_means),
        "c1_input_rows": len(c1),
        "fsr_input_rows": len(fsr),
        "c1_duplicate_keys": c1_duplicates,
        "fsr_duplicate_keys": fsr_duplicates,
        "excluded_total": sum(excluded.values()),
        "excluded_reasons": ";".join(f"{k}={v}" for k, v in sorted(excluded.items())) or "none",
        "bootstrap_draws": 2000,
        "bootstrap_seed": 20260910,
        "interpretation": "delta=FSR-C1; positive means larger FSR A/B output mismatch, negative means smaller FSR mismatch",
    }
    return summary, details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    summaries = []
    detail_path = args.out / "paired_path_differences.csv"
    detail_fields = ["split", "dataset_index", "cube", "season", "suffix_horizon", "geo_group", "n_valid", "c1_A_B_output_mae", "fsr_A_B_output_mae", "delta_fsr_minus_c1"]
    with detail_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=detail_fields)
        writer.writeheader()
        for split in SPLITS:
            summary, details = process(split, args.root, args.out)
            summaries.append(summary)
            writer.writerows(details)
    with (args.out / "paired_statistics.csv").open("w", newline="") as handle:
        fields = list(summaries[0])
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)


if __name__ == "__main__":
    main()
