#!/usr/bin/env python3
"""Explain formal matched-donor exclusions without reading future targets."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import xarray as xr


def inspect(path: Path) -> dict:
    with xr.open_dataset(path, engine="netcdf4", cache=False) as ds:
        b8a = np.asarray(ds["s2_B8A"].isel(time=slice(0, 10)).values, dtype=float)
        b04 = np.asarray(ds["s2_B04"].isel(time=slice(0, 10)).values, dtype=float)
        dlmask = np.asarray(ds["s2_dlmask"].isel(time=slice(0, 10)).values, dtype=float)
        avail = np.asarray(ds["s2_avail"].isel(time=slice(0, 10)).values, dtype=float)
        lc = np.asarray(ds["esawc_lc"].values, dtype=float)
        first10 = np.asarray(ds["time"].values[:10])
        lat = np.asarray(ds["lat"].values, dtype=float)
        lon = np.asarray(ds["lon"].values, dtype=float)

    denom = b8a + b04
    ndvi = np.divide(b8a - b04, denom, out=np.full_like(denom, np.nan), where=np.abs(denom) > 1e-8)
    clear = np.isfinite(dlmask) & (dlmask == 0)
    avail_ok = np.isfinite(avail) & (avail > 0)
    valid = np.isfinite(ndvi) & clear & avail_ok[:, None, None]
    frame_valid = np.sum(valid, axis=(1, 2))
    avail_frames = np.isfinite(avail) & (avail > 0)
    frame_mask = avail_frames[:, None, None]
    raw_band_any = bool(np.any(np.isfinite(b8a) & np.isfinite(b04) & frame_mask))
    clear_any = bool(np.any(clear & frame_mask))
    valid_any = bool(np.any(valid))
    lc_ok = bool(np.any(np.isfinite(lc)))

    # NaN in s2_avail means that a Sentinel-2 observation is unavailable at
    # that timestamp; it is expected in this dataset.  Exclude only when the
    # first ten-frame history has no usable timestamp at all.
    if not np.any(avail_ok):
        category = "missing_or_unavailable_s2_avail"
    elif not raw_band_any:
        category = "raw_history_bands_nonfinite"
    elif not clear_any:
        category = "no_clear_observation_in_first10"
    elif not valid_any:
        category = "no_valid_ndvi_after_clear_and_availability_mask"
    elif not lc_ok:
        category = "missing_landcover"
    else:
        category = "feature_valid"
    return {
        "season": str(first10[0])[:7],
        "history_start": str(first10[0]),
        "history_end": str(first10[-1]),
        "valid_pixel_counts_by_frame": frame_valid.astype(int).tolist(),
        "raw_band_any": raw_band_any,
        "clear_any": clear_any,
        "valid_ndvi_any": valid_any,
        "landcover_finite": lc_ok,
        "landcover_mode": int(np.bincount(np.rint(lc[np.isfinite(lc)]).astype(int)).argmax()) if lc_ok else None,
        "lat_mean": float(np.nanmean(lat)),
        "lon_mean": float(np.nanmean(lon)),
        "category": category,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--mapping", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    with args.manifest.open(newline="", encoding="utf-8") as fh:
        paths = [r["relative_path"] for r in csv.DictReader(fh)]
    mapping = json.loads(args.mapping.read_text())
    matched = {str(Path(r["receiver"]).relative_to(args.data_root)) for r in mapping.get("rows", [])}
    rows = []
    errors = []
    for rel in paths:
        try:
            rec = inspect(args.data_root / rel)
            rec["relative_path"] = rel
            rec["matched"] = rel in matched
            rows.append(rec)
        except Exception as exc:
            errors.append({"relative_path": rel, "error_type": type(exc).__name__, "error": str(exc)})

    by_category = Counter(r["category"] for r in rows)
    by_season = defaultdict(lambda: Counter())
    by_mode = defaultdict(lambda: Counter())
    for r in rows:
        by_season[r["season"]]["total"] += 1
        by_season[r["season"]]["matched"] += int(r["matched"])
        by_season[r["season"]]["excluded"] += int(not r["matched"])
        by_mode[str(r["landcover_mode"])]["total"] += 1
        by_mode[str(r["landcover_mode"])]["matched"] += int(r["matched"])
        by_mode[str(r["landcover_mode"])]["excluded"] += int(not r["matched"])

    matched_rows = [r for r in rows if r["matched"]]
    excluded_rows = [r for r in rows if not r["matched"]]
    def spatial_summary(items):
        return {
            "n": len(items),
            "lat_mean": float(np.mean([r["lat_mean"] for r in items])) if items else None,
            "lon_mean": float(np.mean([r["lon_mean"] for r in items])) if items else None,
            "lat_min": float(min(r["lat_mean"] for r in items)) if items else None,
            "lat_max": float(max(r["lat_mean"] for r in items)) if items else None,
            "lon_min": float(min(r["lon_mean"] for r in items)) if items else None,
            "lon_max": float(max(r["lon_mean"] for r in items)) if items else None,
        }

    out = {
        "status": "PASS" if not errors and len(rows) == len(paths) else "FAIL",
        "requested": len(paths),
        "inspected": len(rows),
        "matched": len(matched_rows),
        "excluded": len(excluded_rows),
        "errors": errors,
        "category_counts": dict(by_category),
        "season_counts": {k: dict(v) for k, v in sorted(by_season.items())},
        "landcover_mode_counts": {k: dict(v) for k, v in sorted(by_mode.items())},
        "spatial_summary_matched": spatial_summary(matched_rows),
        "spatial_summary_excluded": spatial_summary(excluded_rows),
        "history_window": "only time[0:10] and s2_B04/s2_B8A/s2_dlmask/s2_avail; no future target or future weather read",
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("status", "requested", "inspected", "matched", "excluded", "category_counts")}))


if __name__ == "__main__":
    main()
