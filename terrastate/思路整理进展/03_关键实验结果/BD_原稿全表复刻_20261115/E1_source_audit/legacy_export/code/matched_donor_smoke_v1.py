#!/usr/bin/env python3
"""Small, outcome-blind smoke test for the A14B matched-state donor rule.

This validates feature extraction, same-season candidate filtering, deterministic
tie breaking, and reuse accounting. It is not a formal intervention evaluation.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import xarray as xr


def load_record(path: Path) -> dict:
    with xr.open_dataset(path, engine="netcdf4") as ds:
        b8a = np.asarray(ds["s2_B8A"].isel(time=slice(0, 10)).values, dtype=float)
        b04 = np.asarray(ds["s2_B04"].isel(time=slice(0, 10)).values, dtype=float)
        if "s2_mask" in ds:
            # Legacy EarthNet files use 0 for clear observations.
            clear = np.asarray(ds["s2_mask"].isel(time=slice(0, 10)).values == 0)
        else:
            # EarthNet2021x chopped files expose the equivalent DL cloud mask:
            # 0=clear, 1/2/3=cloud or shadow.
            clear = np.asarray(ds["s2_dlmask"].isel(time=slice(0, 10)).values == 0)
        avail = np.asarray(ds["s2_avail"].isel(time=slice(0, 10)).values, dtype=float)
        lc = np.asarray(ds["esawc_lc"].values, dtype=float)
        times = np.asarray(ds["time"].values[:10])

    denom = b8a + b04
    ndvi = np.divide(b8a - b04, denom, out=np.full_like(denom, np.nan), where=np.abs(denom) > 1e-8)
    valid = np.isfinite(ndvi) & clear
    if avail.size:
        valid &= np.isfinite(avail)[:, None, None] & (avail[:, None, None] > 0)
    frame_means = np.array([
        float(np.nanmean(ndvi[t][valid[t]])) if np.any(valid[t]) else np.nan
        for t in range(ndvi.shape[0])
    ])
    finite = np.isfinite(frame_means)
    last = float(frame_means[np.flatnonzero(finite)[-1]]) if np.any(finite) else np.nan
    scalar = np.array([
        float(np.nanmean(frame_means)) if np.any(finite) else np.nan,
        float(np.nanstd(frame_means)) if np.any(finite) else np.nan,
        last,
        float(np.mean(finite)),
    ], dtype=float)

    lc = lc[np.isfinite(lc)]
    lc = np.rint(lc).astype(int) if lc.size else np.array([], dtype=int)
    hist = np.zeros(256, dtype=float)
    if lc.size:
        for value, count in Counter(lc.tolist()).items():
            if 0 <= value < hist.size:
                hist[value] = count
        hist /= hist.sum()

    if not np.all(np.isfinite(scalar)):
        raise ValueError(f"non-finite scalar feature: {path}")
    if not np.any(hist):
        raise ValueError(f"missing land-cover feature: {path}")

    # Exact year-month from the observed context, available before prediction.
    season = str(times[0])[:7]
    return {"path": str(path), "season": season, "scalar": scalar, "lc": hist}


def hellinger(p: np.ndarray, q: np.ndarray) -> float:
    return float(np.linalg.norm(np.sqrt(p) - np.sqrt(q)) / math.sqrt(2.0))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--manifest", type=Path, default=None)
    args = ap.parse_args()

    if args.manifest:
        with args.manifest.open(newline="", encoding="utf-8") as fh:
            rels = [row["relative_path"] for row in csv.DictReader(fh)]
        all_files = [args.data_root / rel for rel in rels]
    else:
        all_files = sorted(args.data_root.glob("*/*.nc"))
    files = all_files if args.n <= 0 else all_files[: args.n]
    if len(files) < 2:
        raise SystemExit(f"need at least 2 files, found {len(files)}")
    invalid = []
    records = []
    for path in files:
        try:
            records.append(load_record(path))
        except (ValueError, OSError) as exc:
            invalid.append({"path": str(path), "reason": str(exc)})
    if len(records) < 2:
        raise SystemExit(f"need at least 2 valid files, found {len(records)}; invalid={invalid}")
    scalar_matrix = np.stack([r["scalar"] for r in records], axis=0)
    med = np.nanmedian(scalar_matrix, axis=0)
    iqr = np.atleast_1d(np.nanpercentile(scalar_matrix, 75, axis=0) - np.nanpercentile(scalar_matrix, 25, axis=0)).astype(float)
    iqr[~np.isfinite(iqr) | (iqr == 0)] = 1.0
    for r in records:
        r["zscalar"] = (r["scalar"] - med) / iqr

    rows = []
    reuse = Counter()
    unmatched = []
    assigned = set()
    for receiver in sorted(records, key=lambda r: r["path"]):
        candidates = [r for r in records if r["season"] == receiver["season"] and r["path"] != receiver["path"] and r["path"] not in assigned]
        if not candidates:
            unmatched.append(receiver["path"])
            continue
        ranked = []
        for donor in candidates:
            distance = float(np.linalg.norm(receiver["zscalar"] - donor["zscalar"]) + 0.5 * hellinger(receiver["lc"], donor["lc"]))
            ranked.append((distance, donor["path"], donor))
        distance, _, donor = min(ranked, key=lambda x: (x[0], x[1]))
        reuse[donor["path"]] += 1
        assigned.add(donor["path"])
        rows.append({"receiver": receiver["path"], "donor": donor["path"], "season": receiver["season"], "distance": distance})

    args.out.parent.mkdir(parents=True, exist_ok=True)
    distances = np.array([r["distance"] for r in rows], dtype=float)
    season_counts = Counter(r["season"] for r in records)
    matched_season_counts = Counter(r["season"] for r in rows)
    args.out.write_text(json.dumps({
        "status": "PASS",
        "scope": "smoke_only_not_formal_evaluation",
        "requested": len(files),
        "manifest": str(args.manifest) if args.manifest else None,
        "invalid": len(invalid),
        "matched": len(rows),
        "unmatched": len(unmatched),
        "self_matches": sum(r["receiver"] == r["donor"] for r in rows),
        "reuse_max": max(reuse.values(), default=0),
        "distance_quantiles": {str(q): float(np.quantile(distances, q)) for q in (0.0, 0.25, 0.5, 0.75, 1.0)} if distances.size else {},
        "season_counts": dict(sorted(season_counts.items())),
        "matched_season_counts": dict(sorted(matched_season_counts.items())),
        "season_groups": len({r["season"] for r in records}),
        "feature_dimension": int(records[0]["scalar"].size),
        "landcover_dimension": int(records[0]["lc"].size),
        "rows": rows,
        "unmatched_paths": unmatched,
        "invalid_records": invalid,
        "rule": "same exact year-month; standardized initial 10-frame NDVI summaries plus 0.5*Hellinger ESA WorldCover histogram; deterministic path tie-break",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "requested": len(files), "matched": len(rows), "unmatched": len(unmatched), "reuse_max": max(reuse.values(), default=0)}))


if __name__ == "__main__":
    main()
