#!/usr/bin/env python3
"""Build an index-aligned matched-donor manifest from frozen quality output."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--formal-manifest", type=Path, required=True)
    ap.add_argument("--quality-report", type=Path, required=True)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    with args.formal_manifest.open(newline="", encoding="utf-8") as fh:
        base = list(csv.DictReader(fh))
    by_path = {str((args.data_root / r["relative_path"]).resolve()): r for r in base}
    by_index = {int(r["dataset_index"]): r for r in base}
    quality = json.loads(args.quality_report.read_text(encoding="utf-8"))
    rows = []
    seen_receiver = set()
    seen_donor = Counter()
    for pair in quality["rows"]:
        receiver = str(Path(pair["receiver"]).resolve())
        donor = str(Path(pair["donor"]).resolve())
        if receiver not in by_path or donor not in by_path:
            raise SystemExit(f"pair path absent from formal manifest: {receiver} -> {donor}")
        rr = by_path[receiver]
        dr = by_path[donor]
        rid = int(rr["dataset_index"])
        did = int(dr["dataset_index"])
        if rid in seen_receiver:
            raise SystemExit(f"duplicate receiver index: {rid}")
        if rid == did:
            raise SystemExit(f"self match: {rid}")
        seen_receiver.add(rid)
        seen_donor[did] += 1
        rows.append({
            "dataset_index": rid,
            "cube": rr["cube"],
            "relative_path": rr["relative_path"],
            "season": pair["season"],
            "donor_index": did,
            "donor_cube": dr["cube"],
            "donor_relative_path": dr["relative_path"],
            "match_distance": pair["distance"],
        })
    rows.sort(key=lambda r: int(r["dataset_index"]))
    fields = list(rows[0]) if rows else []
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    summary = {
        "status": "PASS",
        "formal_manifest_rows": len(base),
        "matched_rows": len(rows),
        "unique_receivers": len(seen_receiver),
        "unique_donors": len(seen_donor),
        "self_matches": 0,
        "reuse_max": max(seen_donor.values(), default=0),
        "reuse_histogram": dict(sorted(Counter(seen_donor.values()).items())),
        "quality_report": str(args.quality_report),
        "data_root": str(args.data_root),
    }
    summary_path = args.out.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
