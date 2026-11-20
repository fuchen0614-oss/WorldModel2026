#!/usr/bin/env python3
"""Freeze corrected matched-donor calibration and per-file audit artifacts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-dir", type=Path, required=True)
    ap.add_argument("--train-root", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--progress-every", type=int, default=500)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    sys.path.insert(0, str(args.code_dir))
    from matched_donor_feature_extractor_v2 import load_record

    files = sorted(args.train_root.glob("*/*.nc"))
    if args.limit > 0:
        files = files[: args.limit]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    scalars = []
    lcs = []
    valid_rels = []
    class_seen = set()
    reason_counts = Counter()
    mask_counts = Counter()
    start = time.time()
    for index, path in enumerate(files, 1):
        rel = str(path.relative_to(args.train_root)).replace("\\", "/")
        row = {"relative_path": rel, "valid": False, "reason": None, "error_type": None, "mask_source": None}
        try:
            rec = load_record(path)
            row.update({
                "valid": True,
                "season": rec["season"],
                "mask_source": rec["mask_source"],
                "finite_history_frames": rec["finite_history_frames"],
                "available_frames": rec["available_frames"],
                "clear_frames": rec["clear_frames"],
                "scalar_0": float(rec["scalar"][0]),
                "scalar_1": float(rec["scalar"][1]),
                "scalar_2": float(rec["scalar"][2]),
                "scalar_3": float(rec["scalar"][3]),
                "landcover_finite": True,
            })
            scalars.append(rec["scalar"])
            lcs.append(rec["lc"])
            valid_rels.append(rel)
            class_seen.update(np.flatnonzero(rec["lc"] > 0).tolist())
            mask_counts[rec["mask_source"]] += 1
        except Exception as exc:
            row.update({"reason": str(exc), "error_type": type(exc).__name__})
            reason_counts[f"{type(exc).__name__}:{str(exc).split(':', 1)[0]}"] += 1
        rows.append(row)
        if index == 1 or index % args.progress_every == 0:
            print(f"processed {index}/{len(files)} valid={len(scalars)} invalid={index-len(scalars)} elapsed={time.time()-start:.1f}s", flush=True)

    matrix = np.stack(scalars) if scalars else np.empty((0, 4), dtype=float)
    median = np.nanmedian(matrix, axis=0) if len(matrix) else np.full(4, np.nan)
    iqr = np.nanpercentile(matrix, 75, axis=0) - np.nanpercentile(matrix, 25, axis=0) if len(matrix) else np.full(4, np.nan)
    iqr[~np.isfinite(iqr) | (iqr == 0)] = 1.0
    rels = [str(p.relative_to(args.train_root)).replace("\\", "/") for p in files]
    file_list_sha = hashlib.sha256("\n".join(rels).encode()).hexdigest()
    csv_path = args.out_dir / "per_file_features.csv"
    fields = ["relative_path", "valid", "reason", "error_type", "season", "mask_source", "finite_history_frames", "available_frames", "clear_frames", "scalar_0", "scalar_1", "scalar_2", "scalar_3", "landcover_finite"]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    np.savez_compressed(args.out_dir / "valid_features.npz", relative_path=np.asarray(valid_rels), scalar=matrix, lc=np.asarray(lcs))
    out = {
        "schema": "matched_donor_calibration_v2_corrected_mask",
        "status": "COMPLETE" if len(rows) == len(files) else "INCOMPLETE",
        "train_root": str(args.train_root),
        "n_files": len(files),
        "n_valid": len(scalars),
        "n_invalid": len(files) - len(scalars),
        "invalid_reason_counts": dict(sorted(reason_counts.items())),
        "mask_source_counts_valid": dict(sorted(mask_counts.items())),
        "file_list_sha256": file_list_sha,
        "feature_schema": ["history_ndvi_mean", "history_ndvi_std", "history_last_mean", "history_valid_frame_fraction"],
        "history_window": "time[0:10] only; s2_B04/s2_B8A, selected clear mask, s2_avail; no future target/weather",
        "mask_selection_contract": "prefer s2_dlmask when present (EarthNet2021x: 0=clear); fallback to s2_mask only when s2_dlmask is absent",
        "median": median.tolist(),
        "iqr": iqr.tolist(),
        "zero_or_nonfinite_iqr_replaced_by": 1.0,
        "landcover_vocabulary": sorted(int(x) for x in class_seen),
        "per_file_features_csv": str(csv_path),
        "valid_features_npz": str(args.out_dir / "valid_features.npz"),
        "elapsed_seconds": time.time() - start,
    }
    (args.out_dir / "calibration.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("status", "n_files", "n_valid", "n_invalid", "invalid_reason_counts", "mask_source_counts_valid")}))


if __name__ == "__main__":
    main()
