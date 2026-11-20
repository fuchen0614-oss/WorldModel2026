#!/usr/bin/env python3
"""Record immutable hashes for the frozen donor-calibration artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--feature-code", type=Path, required=True)
    ap.add_argument("--calibration-code", type=Path, required=True)
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    result = {
        "schema": "matched_donor_calibration_provenance_v1",
        "status": calibration.get("status"),
        "calibration": {
            "path": str(args.calibration),
            "sha256": sha256(args.calibration),
            "n_files": calibration.get("n_files"),
            "n_valid": calibration.get("n_valid"),
            "invalid_counts": calibration.get("invalid_counts"),
            "file_list_sha256": calibration.get("file_list_sha256"),
            "feature_schema": calibration.get("feature_schema"),
            "history_window": calibration.get("history_window"),
        },
        "code": {
            "feature_extractor": {"path": str(args.feature_code), "sha256": sha256(args.feature_code)},
            "calibration_driver": {"path": str(args.calibration_code), "sha256": sha256(args.calibration_code)},
        },
        "log": {"path": str(args.log), "sha256": sha256(args.log)},
        "fixed_for_evaluation": True,
        "use_boundary": "This artifact must be loaded unchanged for every evaluation split; no split-specific refit.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
