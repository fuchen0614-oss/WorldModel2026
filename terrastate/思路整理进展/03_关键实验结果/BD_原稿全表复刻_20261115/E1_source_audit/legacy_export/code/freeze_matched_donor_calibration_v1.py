#!/usr/bin/env python3
"""Freeze matched-donor feature calibration from the full training pool."""
from __future__ import annotations

import argparse
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
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--progress-every", type=int, default=500)
    args = ap.parse_args()
    sys.path.insert(0, str(args.code_dir))
    from matched_donor_smoke_v1 import load_record

    files = sorted(args.train_root.glob("*/*.nc"))
    scalars = []
    class_seen = set()
    invalid = Counter()
    start = time.time()
    for i, path in enumerate(files, 1):
        try:
            rec = load_record(path)
            scalars.append(rec["scalar"])
            class_seen.update(np.flatnonzero(rec["lc"] > 0).tolist())
        except Exception as exc:
            invalid[type(exc).__name__] += 1
        if i == 1 or i % args.progress_every == 0:
            print(f"processed {i}/{len(files)} valid={len(scalars)} elapsed={time.time()-start:.1f}s", flush=True)
    if not scalars:
        raise SystemExit("no valid training calibration records")
    matrix = np.stack(scalars)
    median = np.nanmedian(matrix, axis=0)
    iqr = np.nanpercentile(matrix, 75, axis=0) - np.nanpercentile(matrix, 25, axis=0)
    iqr[~np.isfinite(iqr) | (iqr == 0)] = 1.0
    rels = [str(p.relative_to(args.train_root)).replace("\\", "/") for p in files]
    digest = hashlib.sha256("\n".join(rels).encode()).hexdigest()
    out = {
        "status": "PASS" if not invalid else "PASS_WITH_EXPLICIT_INVALID_TRAIN_RECORDS",
        "pool": "full sorted EarthNet2021x train tree",
        "train_root": str(args.train_root),
        "n_files": len(files), "n_valid": len(scalars), "invalid_counts": dict(invalid),
        "file_list_sha256": digest,
        "feature_schema": ["history_ndvi_mean", "history_ndvi_std", "history_last_mean", "history_valid_frame_fraction"],
        "history_window": "time[0:10] only; s2_B04, s2_B8A, s2_dlmask, s2_avail; no future target/weather",
        "median": median.tolist(), "iqr": iqr.tolist(),
        "zero_or_nonfinite_iqr_replaced_by": 1.0,
        "landcover_vocabulary": sorted(int(x) for x in class_seen),
        "frozen_before_ood_matching": True,
        "elapsed_seconds": time.time() - start,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("status", "n_files", "n_valid", "invalid_counts", "file_list_sha256")}))


if __name__ == "__main__":
    main()
