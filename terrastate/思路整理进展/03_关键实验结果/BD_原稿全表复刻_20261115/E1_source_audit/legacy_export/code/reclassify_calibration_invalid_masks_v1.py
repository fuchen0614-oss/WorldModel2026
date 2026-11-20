#!/usr/bin/env python3
"""Audit existing calibration failures for the s2_mask/s2_dlmask branch."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import xarray as xr


def finite_frames(ds: xr.Dataset, mask_name: str) -> int:
    b8a = np.asarray(ds["s2_B8A"].isel(time=slice(0, 10)).values, dtype=float)
    b04 = np.asarray(ds["s2_B04"].isel(time=slice(0, 10)).values, dtype=float)
    mask = np.asarray(ds[mask_name].isel(time=slice(0, 10)).values == 0)
    avail = np.asarray(ds["s2_avail"].isel(time=slice(0, 10)).values, dtype=float)
    denom = b8a + b04
    ndvi = np.divide(b8a - b04, denom, out=np.full_like(denom, np.nan), where=np.abs(denom) > 1e-8)
    valid = np.isfinite(ndvi) & mask & (np.isfinite(avail) & (avail > 0))[:, None, None]
    return int(np.sum([np.any(valid[t]) for t in range(valid.shape[0])]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--train-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    source = json.loads(args.audit.read_text(encoding="utf-8"))
    rows = []
    categories = Counter()
    for original in source["invalid_rows"]:
        path = args.train_root / original["relative_path"]
        row = {"relative_path": original["relative_path"], "original_category": original["category"], "original_error": original["error_message"]}
        try:
            with xr.open_dataset(path, engine="netcdf4", cache=False) as ds:
                has_old = "s2_mask" in ds
                has_dl = "s2_dlmask" in ds
                old_frames = finite_frames(ds, "s2_mask") if has_old else None
                dl_frames = finite_frames(ds, "s2_dlmask") if has_dl else None
                if has_old and has_dl and old_frames == 0 and dl_frames > 0:
                    category = "loader_mask_branch_false_invalid"
                elif (old_frames or 0) > 0:
                    category = "s2_mask_history_usable_but_other_issue"
                elif (dl_frames or 0) > 0:
                    category = "dlmask_history_usable_without_s2_mask_branch"
                else:
                    category = "no_finite_history_under_available_masks"
                row.update({
                    "has_s2_mask": has_old,
                    "has_s2_dlmask": has_dl,
                    "s2_mask_finite_frames": old_frames,
                    "s2_dlmask_finite_frames": dl_frames,
                    "s2_mask_zero_count": int(np.sum(np.asarray(ds["s2_mask"].isel(time=slice(0, 10)).values == 0))) if has_old else None,
                    "s2_dlmask_zero_count": int(np.sum(np.asarray(ds["s2_dlmask"].isel(time=slice(0, 10)).values == 0))) if has_dl else None,
                })
        except Exception as exc:
            category = "diagnostic_read_failure"
            row["diagnostic_error"] = f"{type(exc).__name__}: {exc}"
        row["reclassified_category"] = category
        categories[category] += 1
        rows.append(row)
    out = {
        "schema": "matched_donor_calibration_invalid_mask_reclassification_v1",
        "source_audit": str(args.audit),
        "n_source_invalid": len(rows),
        "category_counts": dict(sorted(categories.items())),
        "interpretation": "loader_mask_branch_false_invalid means s2_mask has no clear frame but s2_dlmask has at least one; matched_donor_smoke_v1 chooses s2_mask whenever present.",
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"n_source_invalid": len(rows), "category_counts": dict(sorted(categories.items()))}))


if __name__ == "__main__":
    main()
