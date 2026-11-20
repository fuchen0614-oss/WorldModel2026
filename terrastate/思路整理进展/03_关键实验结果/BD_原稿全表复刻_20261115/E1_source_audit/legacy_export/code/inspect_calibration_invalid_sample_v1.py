#!/usr/bin/env python3
"""Inspect one audit sample to distinguish mask semantics from true extraction errors."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr


def scalar_for(ds: xr.Dataset, mask_name: str) -> tuple[np.ndarray, int, int]:
    b8a = np.asarray(ds["s2_B8A"].isel(time=slice(0, 10)).values, dtype=float)
    b04 = np.asarray(ds["s2_B04"].isel(time=slice(0, 10)).values, dtype=float)
    mask = np.asarray(ds[mask_name].isel(time=slice(0, 10)).values == 0)
    avail = np.asarray(ds["s2_avail"].isel(time=slice(0, 10)).values, dtype=float)
    denom = b8a + b04
    ndvi = np.divide(b8a - b04, denom, out=np.full_like(denom, np.nan), where=np.abs(denom) > 1e-8)
    valid = np.isfinite(ndvi) & mask & (np.isfinite(avail) & (avail > 0))[:, None, None]
    frame_means = np.array([
        float(np.nanmean(ndvi[t][valid[t]])) if np.any(valid[t]) else np.nan
        for t in range(ndvi.shape[0])
    ])
    finite = np.isfinite(frame_means)
    last = float(frame_means[np.flatnonzero(finite)[-1]]) if np.any(finite) else np.nan
    scalar = np.array([np.nanmean(frame_means), np.nanstd(frame_means), last, np.mean(finite)])
    return scalar, int(finite.sum()), int(np.any(valid, axis=(1, 2)).sum())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--train-root", type=Path, required=True)
    ap.add_argument("--code-dir", type=Path, required=True)
    args = ap.parse_args()
    sys.path.insert(0, str(args.code_dir))
    from matched_donor_smoke_v1 import load_record

    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    row = next(r for r in audit["invalid_rows"] if r["category"] == "feature_extraction_or_normalization_problem")
    path = args.train_root / row["relative_path"]
    with xr.open_dataset(path, engine="netcdf4", cache=False) as ds:
        print(json.dumps({
            "relative_path": row["relative_path"],
            "variables": sorted(ds.variables),
            "has_s2_mask": "s2_mask" in ds,
            "has_s2_dlmask": "s2_dlmask" in ds,
            "s2_mask_unique_first10": np.unique(ds["s2_mask"].isel(time=slice(0, 10)).values).tolist() if "s2_mask" in ds else None,
            "s2_dlmask_unique_first10": np.unique(ds["s2_dlmask"].isel(time=slice(0, 10)).values).tolist() if "s2_dlmask" in ds else None,
            "load_record_error": row["error_message"],
            "s2_mask_scalar": scalar_for(ds, "s2_mask")[0].tolist() if "s2_mask" in ds else None,
            "s2_mask_finite_frames": scalar_for(ds, "s2_mask")[1] if "s2_mask" in ds else None,
            "s2_dlmask_scalar": scalar_for(ds, "s2_dlmask")[0].tolist() if "s2_dlmask" in ds else None,
            "s2_dlmask_finite_frames": scalar_for(ds, "s2_dlmask")[1] if "s2_dlmask" in ds else None,
        }, ensure_ascii=False, indent=2))
    try:
        load_record(path)
    except Exception as exc:
        print(f"load_record_reproduced={type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
