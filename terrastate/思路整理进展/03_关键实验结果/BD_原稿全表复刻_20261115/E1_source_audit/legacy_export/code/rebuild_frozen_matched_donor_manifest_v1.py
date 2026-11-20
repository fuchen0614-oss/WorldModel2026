#!/usr/bin/env python3
"""Rebuild a donor manifest with fixed training-pool calibration."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def hellinger(p: np.ndarray, q: np.ndarray) -> float:
    return float(np.linalg.norm(np.sqrt(p) - np.sqrt(q)) / np.sqrt(2.0))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-dir", type=Path, required=True)
    ap.add_argument("--formal-manifest", type=Path, required=True)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--old-manifest", type=Path, default=None)
    ap.add_argument("--out-manifest", type=Path, required=True)
    ap.add_argument("--out-report", type=Path, required=True)
    args = ap.parse_args()
    sys.path.insert(0, str(args.code_dir))
    from matched_donor_smoke_v1 import load_record

    base = list(csv.DictReader(args.formal_manifest.open(newline="", encoding="utf-8")))
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    med = np.asarray(calibration["median"], dtype=float)
    iqr = np.asarray(calibration["iqr"], dtype=float)
    if med.shape != iqr.shape or med.ndim != 1 or not np.all(np.isfinite(med)) or not np.all(np.isfinite(iqr)):
        raise SystemExit("invalid calibration vectors")

    records = []
    invalid = []
    for row in base:
        path = args.data_root / row["relative_path"]
        try:
            rec = load_record(path)
            rec["dataset_index"] = int(row["dataset_index"])
            rec["cube"] = row["cube"]
            rec["relative_path"] = row["relative_path"]
            rec["zscalar"] = (rec["scalar"] - med) / iqr
            records.append(rec)
        except Exception as exc:
            invalid.append({"dataset_index": int(row["dataset_index"]), "relative_path": row["relative_path"], "reason": str(exc)})

    rows = []
    assigned = set()
    for receiver in sorted(records, key=lambda r: r["path"]):
        candidates = [
            donor for donor in records
            if donor["season"] == receiver["season"]
            and donor["path"] != receiver["path"]
            and donor["path"] not in assigned
        ]
        if not candidates:
            continue
        ranked = []
        for donor in candidates:
            distance = float(np.linalg.norm(receiver["zscalar"] - donor["zscalar"]) + 0.5 * hellinger(receiver["lc"], donor["lc"]))
            ranked.append((distance, donor["path"], donor))
        distance, _, donor = min(ranked, key=lambda x: (x[0], x[1]))
        assigned.add(donor["path"])
        rows.append({
            "dataset_index": receiver["dataset_index"],
            "cube": receiver["cube"],
            "relative_path": receiver["relative_path"],
            "season": receiver["season"],
            "donor_index": donor["dataset_index"],
            "donor_cube": donor["cube"],
            "donor_relative_path": donor["relative_path"],
            "match_distance": distance,
        })
    rows.sort(key=lambda r: r["dataset_index"])
    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.out_manifest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    old = list(csv.DictReader(args.old_manifest.open(newline="", encoding="utf-8"))) if args.old_manifest and args.old_manifest.exists() else []
    old_pairs = {int(r["dataset_index"]): int(r["donor_index"]) for r in old}
    new_pairs = {int(r["dataset_index"]): int(r["donor_index"]) for r in rows}
    common = sorted(set(old_pairs) & set(new_pairs))
    changed = [i for i in common if old_pairs[i] != new_pairs[i]]
    reuse = Counter(r["donor_index"] for r in rows)
    distances = np.asarray([float(r["match_distance"]) for r in rows], dtype=float)
    report = {
        "schema": "frozen_matched_donor_manifest_rebuild_v1",
        "status": "PASS_WITH_EXPLICIT_INVALID_EVAL_RECORDS" if invalid else "PASS",
        "calibration": {"path": str(args.calibration), "sha256": sha256(args.calibration), "file_list_sha256": calibration.get("file_list_sha256")},
        "formal_manifest": {"path": str(args.formal_manifest), "rows": len(base), "sha256": sha256(args.formal_manifest)},
        "feature_code": {"path": str(args.code_dir / "matched_donor_smoke_v1.py"), "sha256": sha256(args.code_dir / "matched_donor_smoke_v1.py")},
        "result": {
            "requested": len(base), "valid_records": len(records), "invalid_records": len(invalid),
            "matched": len(rows), "unmatched_valid": len(records) - len(rows), "self_matches": sum(int(r["dataset_index"]) == int(r["donor_index"]) for r in rows),
            "reuse_max": max(reuse.values(), default=0), "distance_quantiles": {str(q): float(np.quantile(distances, q)) for q in (0, .25, .5, .75, 1)} if len(distances) else {},
        },
        "comparison_to_old_iid_manifest": {
            "old_path": str(args.old_manifest) if args.old_manifest else None,
            "old_sha256": sha256(args.old_manifest) if args.old_manifest and args.old_manifest.exists() else None,
            "old_rows": len(old),
            "common_receivers": len(common), "pair_changed": len(changed), "pair_changed_fraction": (len(changed) / len(common)) if common else None,
            "old_only_receivers": sorted(set(old_pairs) - set(new_pairs)), "new_only_receivers": sorted(set(new_pairs) - set(old_pairs)),
        },
        "invalid_records": invalid,
        "rule": "Fixed training-pool median/IQR; exact YYYY-MM candidate key; 0.5 Hellinger ESA WorldCover; deterministic path tie-break; donor reuse cap 1; no future target/weather.",
        "formal_status": "comparison_only_manifest_pending_quality_acceptance_and_intervention_rerun",
    }
    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "requested": len(base), "valid": len(records), "invalid": len(invalid), "matched": len(rows), "pair_changed": len(changed), "reuse_max": max(reuse.values(), default=0)}))


if __name__ == "__main__":
    main()
