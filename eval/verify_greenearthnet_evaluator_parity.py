#!/usr/bin/env python
"""Compare local Table 1 metrics with an independently run official evaluator.

The public GreenEarthNet evaluator is intentionally kept in a separate checkout
when doing the final paper verification.  This utility does not rerun it; it
pins both metric files to a frozen OOD-t manifest and records numerical parity
in a machine-readable report consumed by the Table 1 assembler.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import (  # noqa: E402
    GREENEARTHNET_CHOPPED_PROTOCOL_ID,
    manifest_protocol_spec,
    write_json_atomic,
)
from eval.table1_artifact_contract import source_manifest_identity  # noqa: E402

OFFICIAL_REPOSITORY = "https://github.com/vitusbenson/greenearthnet"
OFFICIAL_EVALUATOR_COMMIT = "a0329636631371a4aaa9a95c75ed0a37d27b8c4f"


REQUIRED_METRICS = ("R2", "rmse", "nse", "biasabs", "rmse25")
_ALIASES = {
    "R2": ("R2", "r2"),
    "rmse": ("rmse", "RMSE"),
    "nse": ("nse", "NSE"),
    "biasabs": ("biasabs", "bias_abs", "absolute_bias"),
    "rmse25": ("rmse25", "rmse_0_5", "RMSE25"),
    "outperformance": ("outperformance", "gain_outperform", "Outperformance"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record metric parity between a local score and an official evaluator score."
    )
    parser.add_argument("--local-score", required=True)
    parser.add_argument("--reference-score", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--manifest-protocol",
        default=GREENEARTHNET_CHOPPED_PROTOCOL_ID,
    )
    parser.add_argument("--split", default="ood-t_chopped")
    parser.add_argument("--reference-command", default=None)
    parser.add_argument("--atol", type=float, default=1e-8)
    parser.add_argument("--rtol", type=float, default=1e-6)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(8 * 1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _identity(path: str | Path) -> dict[str, Any]:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return {
        "path": str(resolved),
        "size_bytes": int(resolved.stat().st_size),
        "sha256": _sha256(resolved),
    }


def _load_metrics(path: str | Path) -> dict[str, float]:
    source = Path(path).expanduser().resolve()
    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows or not {"metric", "value"}.issubset(rows[0]):
            raise ValueError("CSV score must have metric,value columns")
        raw: Mapping[str, Any] = {str(row["metric"]): row["value"] for row in rows}
    else:
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("JSON score must be an object")
        candidate = payload.get("metrics", payload)
        if not isinstance(candidate, Mapping):
            raise ValueError("JSON score has no metrics object")
        raw = candidate

    metrics: dict[str, float] = {}
    for canonical, aliases in _ALIASES.items():
        for key in aliases:
            value = raw.get(key)
            if value is None:
                continue
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Metric {key!r} is not numeric in {source}") from exc
            if not math.isfinite(number):
                raise ValueError(f"Metric {key!r} is not finite in {source}")
            metrics[canonical] = number
            break
    missing = [name for name in REQUIRED_METRICS if name not in metrics]
    if missing:
        raise ValueError(f"Score {source} is missing required Table 1 metrics: {missing}")
    return metrics


def main() -> int:
    args = parse_args()
    if args.atol < 0 or args.rtol < 0:
        raise ValueError("--atol and --rtol must be non-negative")
    manifest_protocol_spec(args.manifest_protocol)
    if args.manifest_protocol != GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        raise ValueError("Evaluator parity is only defined here for the chopped GreenEarthNet protocol")
    if args.split != "ood-t_chopped":
        raise ValueError("Formal Table 1 evaluator parity requires --split ood-t_chopped")

    local = _load_metrics(args.local_score)
    reference = _load_metrics(args.reference_score)
    comparisons: dict[str, dict[str, Any]] = {}
    passed = True
    for name in REQUIRED_METRICS:
        local_value = local[name]
        reference_value = reference[name]
        tolerance = args.atol + args.rtol * abs(reference_value)
        absolute_error = abs(local_value - reference_value)
        metric_passed = absolute_error <= tolerance
        comparisons[name] = {
            "local": local_value,
            "reference": reference_value,
            "absolute_error": absolute_error,
            "tolerance": tolerance,
            "passed": metric_passed,
        }
        passed = passed and metric_passed

    report = {
        "kind": "greenearthnet_evaluator_parity_report",
        "passed": passed,
        "source_manifest": source_manifest_identity(args.manifest),
        "source_manifest_protocol": args.manifest_protocol,
        "evaluation_track": args.split,
        "local_score": _identity(args.local_score),
        "reference_score": _identity(args.reference_score),
        "reference": {
            "repository": OFFICIAL_REPOSITORY,
            "commit": OFFICIAL_EVALUATOR_COMMIT,
            "command": args.reference_command,
        },
        "atol": args.atol,
        "rtol": args.rtol,
        "metrics": comparisons,
        "notes": [
            "The reference score must be produced by an independently checked-out official evaluator on the exact same frozen manifest and prediction tree.",
            "This report records numerical equality; it does not make an unlabeled result from another split comparable.",
        ],
    }
    output = write_json_atomic(report, args.output)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"parity_report={output}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
