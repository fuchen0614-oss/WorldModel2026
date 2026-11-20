#!/usr/bin/env python3
"""Recover per-file reasons for the existing training-pool ValueErrors.

The original calibration pass only retained an exception-type counter.  This
audit repeats feature loading for the same files, records only invalid rows,
and never recomputes calibration statistics or model inference.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import xarray as xr


def classify_failure(path: Path, message: str) -> dict:
    """Read only the feature inputs needed to explain a failed load."""
    required = ["s2_B8A", "s2_B04", "s2_dlmask", "s2_avail", "esawc_lc", "time"]
    try:
        with xr.open_dataset(path, engine="netcdf4", cache=False) as ds:
            present = set(ds.variables)
            missing = [name for name in required if name not in present]
            if missing:
                return {
                    "category": "field_or_format_problem",
                    "missing_variables": missing,
                    "detail": "required feature variable is absent",
                }
            b8a = np.asarray(ds["s2_B8A"].isel(time=slice(0, 10)).values, dtype=float)
            b04 = np.asarray(ds["s2_B04"].isel(time=slice(0, 10)).values, dtype=float)
            dlmask = np.asarray(ds["s2_dlmask"].isel(time=slice(0, 10)).values, dtype=float)
            avail = np.asarray(ds["s2_avail"].isel(time=slice(0, 10)).values, dtype=float)
            lc = np.asarray(ds["esawc_lc"].values, dtype=float)
            times = np.asarray(ds["time"].values[:10])
    except Exception as exc:
        return {
            "category": "file_read_problem",
            "detail": f"diagnostic read failed: {type(exc).__name__}: {exc}",
        }

    denom = b8a + b04
    ndvi = np.divide(b8a - b04, denom, out=np.full_like(denom, np.nan), where=np.abs(denom) > 1e-8)
    clear = np.isfinite(dlmask) & (dlmask == 0)
    avail_ok = np.isfinite(avail) & (avail > 0)
    valid = np.isfinite(ndvi) & clear
    if avail.size:
        valid &= avail_ok[:, None, None]
    frame_means = np.array([
        float(np.nanmean(ndvi[t][valid[t]])) if np.any(valid[t]) else np.nan
        for t in range(min(10, ndvi.shape[0]))
    ])
    finite_frames = int(np.isfinite(frame_means).sum())
    lc_finite = int(np.isfinite(lc).sum())
    if finite_frames == 0:
        category = "reasonable_missing_history"
        detail = "no finite clear and available NDVI frame in time[0:10]"
    elif lc_finite == 0:
        category = "reasonable_missing_landcover"
        detail = "history feature is usable but esawc_lc has no finite value"
    else:
        category = "feature_extraction_or_normalization_problem"
        detail = "required arrays are readable and contain finite history/landcover"
    return {
        "category": category,
        "detail": detail,
        "history_start": str(times[0]) if len(times) else None,
        "history_end": str(times[-1]) if len(times) else None,
        "finite_history_frames": finite_frames,
        "available_frames": int(avail_ok.sum()),
        "clear_frames": int(np.any(clear, axis=(1, 2)).sum()),
        "landcover_finite_values": lc_finite,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-dir", type=Path, required=True)
    ap.add_argument("--train-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--progress-every", type=int, default=500)
    args = ap.parse_args()
    sys.path.insert(0, str(args.code_dir))
    from matched_donor_smoke_v1 import load_record

    files = sorted(args.train_root.glob("*/*.nc"))
    invalid = []
    errors_by_type = Counter()
    start = time.time()
    for index, path in enumerate(files, 1):
        try:
            load_record(path)
        except Exception as exc:
            errors_by_type[type(exc).__name__] += 1
            detail = classify_failure(path, str(exc))
            detail.update({
                "relative_path": str(path.relative_to(args.train_root)).replace("\\", "/"),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            })
            invalid.append(detail)
        if index == 1 or index % args.progress_every == 0:
            print(
                f"processed {index}/{len(files)} invalid={len(invalid)} "
                f"elapsed={time.time() - start:.1f}s",
                flush=True,
            )

    categories = Counter(row["category"] for row in invalid)
    out = {
        "schema": "matched_donor_calibration_train_invalid_audit_v1",
        "status": "PASS" if len(files) and len(invalid) == 1602 else "REVIEW",
        "train_root": str(args.train_root),
        "n_files": len(files),
        "n_invalid": len(invalid),
        "n_valid": len(files) - len(invalid),
        "original_calibration_invalid_counts": {"ValueError": 1602},
        "observed_error_types": dict(errors_by_type),
        "category_counts": dict(sorted(categories.items())),
        "history_window": "time[0:10] only; feature variables only; no future target/weather",
        "does_not_recompute_calibration": True,
        "elapsed_seconds": time.time() - start,
        "invalid_rows": invalid,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("status", "n_files", "n_valid", "n_invalid", "category_counts")}))


if __name__ == "__main__":
    main()
