#!/usr/bin/env python
"""Compare raw-NetCDF-adapted ENS targets with an independently supplied target tree.

A successful report is the only supported way to upgrade a Table 1 row from
raw_adapter_unverified to parity_verified. The command deliberately does not
rewrite target manifests: the report remains separate, hash-bound evidence that
can be inspected before an assembler uses it.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np

from data.earthnet_manifest import write_json_atomic
from eval.score_table1_earthnet import validate_manifest_tree
from train.stage2_provenance import file_identity


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify generated EarthNetScore targets against an independent target tree."
    )
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--reference-target-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--atol", type=float, default=0.0)
    parser.add_argument("--rtol", type=float, default=0.0)
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Debug-only cap. A partial comparison can never certify parity.",
    )
    return parser.parse_args()


def _manifest_records(path: Path) -> list[dict[str, Any]]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    files = payload.get("files")
    if not isinstance(files, list):
        raise ValueError(f"Target manifest has no files list: {path}")
    records: list[dict[str, Any]] = []
    for value in files:
        if not isinstance(value, dict) or not isinstance(value.get("path"), str):
            raise ValueError("Target manifest contains an invalid output record")
        records.append(value)
    return sorted(records, key=lambda item: str(item["path"]))


def _reference_path(root: Path, relative: str) -> Path:
    candidates = (root / relative, root / "target" / relative)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _highres(path: Path) -> np.ndarray:
    with np.load(path, allow_pickle=False) as payload:
        if "highresdynamic" not in payload:
            raise KeyError(f"{path} has no highresdynamic array")
        return np.asarray(payload["highresdynamic"])


def _compare_arrays(
    generated: np.ndarray,
    reference: np.ndarray,
    *,
    atol: float,
    rtol: float,
) -> dict[str, object]:
    if generated.shape != reference.shape:
        return {
            "equal": False,
            "shape_generated": list(generated.shape),
            "shape_reference": list(reference.shape),
            "num_mismatched": None,
            "max_abs_diff": None,
        }
    equal = np.isclose(
        generated,
        reference,
        rtol=rtol,
        atol=atol,
        equal_nan=True,
    )
    finite_diff = np.abs(
        np.nan_to_num(generated.astype(np.float64), nan=0.0)
        - np.nan_to_num(reference.astype(np.float64), nan=0.0)
    )
    return {
        "equal": bool(np.all(equal)),
        "shape_generated": list(generated.shape),
        "shape_reference": list(reference.shape),
        "num_mismatched": int(equal.size - int(equal.sum())),
        "max_abs_diff": float(finite_diff.max(initial=0.0)),
        "mean_abs_diff": float(finite_diff.mean()) if finite_diff.size else 0.0,
    }


def main() -> int:
    args = parse_args()
    if args.atol < 0 or args.rtol < 0:
        raise ValueError("--atol and --rtol must be non-negative")
    if args.max_files < 0:
        raise ValueError("--max-files must be non-negative")

    target_root = Path(args.target_dir).expanduser().resolve()
    manifest_path = Path(args.target_manifest).expanduser().resolve()
    reference_root = Path(args.reference_target_dir).expanduser().resolve()
    target_validation = validate_manifest_tree(
        target_root,
        manifest_path,
        artifact="generated target",
    )
    records = _manifest_records(manifest_path)
    selected = records if args.max_files == 0 else records[: args.max_files]
    mismatches: list[dict[str, object]] = []
    missing_reference: list[str] = []
    checked = 0
    for record in selected:
        relative = str(record["path"])
        generated = target_root / relative
        reference = _reference_path(reference_root, relative)
        if not reference.is_file():
            missing_reference.append(relative)
            continue
        comparison = _compare_arrays(
            _highres(generated),
            _highres(reference),
            atol=args.atol,
            rtol=args.rtol,
        )
        checked += 1
        if not comparison["equal"] and len(mismatches) < 20:
            mismatches.append(
                {
                    "path": relative,
                    "generated": str(generated),
                    "reference": str(reference),
                    **comparison,
                }
            )

    complete = len(selected) == len(records)
    passed = (
        complete
        and checked == len(records)
        and not missing_reference
        and not mismatches
    )
    report = {
        "schema_version": 1,
        "kind": "earthnet_score_target_adapter_parity_report",
        "status": "parity_verified" if passed else (
            "partial_not_verifiable" if not complete else "parity_failed"
        ),
        "passed": passed,
        "complete": complete,
        "tolerances": {"atol": float(args.atol), "rtol": float(args.rtol)},
        "generated_target_manifest": file_identity(manifest_path, required=True),
        "generated_target_validation": target_validation,
        "reference_target_dir": str(reference_root),
        "num_manifest_files": len(records),
        "num_checked": checked,
        "num_missing_reference": len(missing_reference),
        "missing_reference_preview": missing_reference[:20],
        "num_mismatched": len(mismatches),
        "mismatch_preview": mismatches,
    }
    output = Path(args.output).expanduser().resolve()
    write_json_atomic(report, output)
    print(f"parity_status={report['status']}")
    print(f"parity_report={output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
