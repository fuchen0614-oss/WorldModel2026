#!/usr/bin/env python3
"""Compare old and corrected matched-donor calibration artifacts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", type=Path, required=True)
    ap.add_argument("--new", type=Path, required=True)
    ap.add_argument("--new-per-file", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-md", type=Path, required=True)
    args = ap.parse_args()
    old = json.loads(args.old.read_text(encoding="utf-8"))
    new = json.loads(args.new.read_text(encoding="utf-8"))
    reason_counts = {}
    mask_counts = {}
    with args.new_per_file.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("valid") != "True":
                reason = row.get("reason", "unknown")
                if reason.startswith("non-finite scalar feature"):
                    reason = "non_finite_scalar_feature"
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            else:
                mask = row.get("mask_source", "unknown")
                mask_counts[mask] = mask_counts.get(mask, 0) + 1
    med_delta = [b - a for a, b in zip(old["median"], new["median"])]
    iqr_delta = [b - a for a, b in zip(old["iqr"], new["iqr"])]
    result = {
        "schema": "matched_donor_calibration_comparison_v1",
        "old": {"path": str(args.old), "sha256": sha256(args.old), "n_files": old["n_files"], "n_valid": old["n_valid"], "median": old["median"], "iqr": old["iqr"]},
        "new": {"path": str(args.new), "sha256": sha256(args.new), "n_files": new["n_files"], "n_valid": new["n_valid"], "n_invalid": new["n_invalid"], "median": new["median"], "iqr": new["iqr"], "mask_source_counts_valid": mask_counts, "invalid_reason_counts": reason_counts},
        "delta": {"valid_count": new["n_valid"] - old["n_valid"], "median": med_delta, "iqr": iqr_delta},
        "interpretation": "Corrected extractor prefers s2_dlmask when present; the new calibration was recomputed over all files and must not be treated as old calibration plus 573 rows.",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Matched-donor calibration old/new comparison",
        "",
        f"Old calibration: `{args.old}` (sha256 `{result['old']['sha256']}`)",
        f"Corrected calibration: `{args.new}` (sha256 `{result['new']['sha256']}`)",
        "",
        f"Files: {old['n_files']} total in both runs; valid changed from {old['n_valid']} to {new['n_valid']} (delta {new['n_valid'] - old['n_valid']}).",
        "",
        "| feature | old median | new median | delta | old IQR | new IQR | delta |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for i, (om, nm, dm, oi, ni, di) in enumerate(zip(old["median"], new["median"], med_delta, old["iqr"], new["iqr"], iqr_delta)):
        lines.append(f"| {i} | {om} | {nm} | {dm} | {oi} | {ni} | {di} |")
    lines += [
        "",
        "Corrected valid mask sources: " + json.dumps(mask_counts, ensure_ascii=False),
        "Corrected invalid reasons: " + json.dumps(reason_counts, ensure_ascii=False),
        "",
        "The corrected output is an independent calibration artifact. Existing manifests and evidence remain attributed to their original calibration until rebuilt and revalidated.",
    ]
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "old_valid": old["n_valid"], "new_valid": new["n_valid"], "delta_valid": new["n_valid"] - old["n_valid"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
