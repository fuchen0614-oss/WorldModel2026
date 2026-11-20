#!/usr/bin/env python3
"""Record the calibration provenance of the existing IID donor mapping."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quality-report", type=Path, required=True)
    ap.add_argument("--generator", type=Path, required=True)
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    quality = json.loads(args.quality_report.read_text(encoding="utf-8"))
    source = args.generator.read_text(encoding="utf-8")
    protocol = args.protocol.read_text(encoding="utf-8")
    has_fit = bool(re.search(r"nanmedian|nanpercentile", source))
    has_external_calibration = "--calibration" in source or "calibration_path" in source
    protocol_requires_pool = bool(re.search(r"pool.*held fixed|fixed.*evaluation split", protocol, re.I | re.S))

    report = {
        "schema": "iid_matched_donor_calibration_audit_v1",
        "status": "MISMATCH_REQUIRES_REBUILD_FOR_UNIFIED_FORMAL_LABEL",
        "scope": {
            "quality_report_requested": quality.get("requested"),
            "matched": quality.get("matched"),
            "invalid": quality.get("invalid"),
            "report_scope": quality.get("scope"),
        },
        "evidence": {
            "quality_report": str(args.quality_report),
            "quality_report_sha256": sha256(args.quality_report),
            "generator": str(args.generator),
            "generator_sha256": sha256(args.generator),
            "protocol": str(args.protocol),
            "protocol_sha256": sha256(args.protocol),
            "generator_fits_median_iqr_on_loaded_records": has_fit,
            "generator_accepts_external_calibration_artifact": has_external_calibration,
            "protocol_requires_training_pool_parameters_held_fixed": protocol_requires_pool,
        },
        "conclusion": {
            "rule_compatibility": "Feature schema, exact year-month candidate key, 0.5 Hellinger land-cover term, deterministic path tie-break and reuse cap are present.",
            "calibration_provenance": "The existing generator fits median/IQR from the records loaded for this invocation; the source has no external calibration input. For the existing IID quality report, those records are the IID formal manifest.",
            "scientific_label": "Retain existing intervention and quality outputs, but label them IID-self-calibrated matched-donor, not unified training-pool-calibrated formal evidence.",
            "required_followup": "After the training-pool calibration artifact completes, rebuild the IID manifest with that fixed artifact, compare pair identity/coverage/distance, and rerun only affected donor-state branches if mappings change.",
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "out": str(args.out)}))


if __name__ == "__main__":
    main()
