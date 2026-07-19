#!/usr/bin/env python
"""Verify a local formal baseline against an independently run public baseline.

Evaluator parity only proves that this repository and the public evaluator score
the *same* prediction tree equally.  This companion check proves that the
locally generated deterministic Persistence or Climatology baseline also
matches a score produced by the public baseline implementation on the same
frozen OOD-t chopped targets.
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

from data.earthnet_manifest import GREENEARTHNET_CHOPPED_PROTOCOL_ID, manifest_protocol_spec, write_json_atomic  # noqa: E402
from eval.table1_artifact_contract import source_manifest_identity  # noqa: E402

OFFICIAL_REPOSITORY = "https://github.com/vitusbenson/greenearthnet"
OFFICIAL_EVALUATOR_COMMIT = "a0329636631371a4aaa9a95c75ed0a37d27b8c4f"
REQUIRED_METRICS = ("R2", "rmse", "nse", "biasabs", "rmse25")
ALIASES = {
    "R2": ("R2", "r2"),
    "rmse": ("rmse", "RMSE"),
    "nse": ("nse", "NSE"),
    "biasabs": ("biasabs", "bias_abs", "absolute_bias"),
    "rmse25": ("rmse25", "rmse_0_5", "RMSE25"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record local deterministic-baseline parity against an independent public reference."
    )
    parser.add_argument("--baseline", required=True, choices=("persistence", "climatology"))
    parser.add_argument("--local-score", required=True)
    parser.add_argument("--reference-score", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-protocol", default=GREENEARTHNET_CHOPPED_PROTOCOL_ID)
    parser.add_argument("--split", default="ood-t_chopped")
    parser.add_argument("--reference-command", required=True)
    parser.add_argument("--atol", type=float, default=1e-8)
    parser.add_argument("--rtol", type=float, default=1e-6)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _identity(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        while True:
            block = handle.read(8 * 1024 * 1024)
            if not block:
                break
            digest.update(block)
    return {
        "path": str(source),
        "size_bytes": int(source.stat().st_size),
        "sha256": digest.hexdigest(),
    }


def _load_metrics(path: str | Path) -> dict[str, float]:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
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
        raw = payload.get("metrics", payload)
        if not isinstance(raw, Mapping):
            raise ValueError("JSON score has no metrics object")

    metrics: dict[str, float] = {}
    for canonical, aliases in ALIASES.items():
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
        raise ValueError(f"Score {source} is missing required baseline metrics: {missing}")
    return metrics


def main() -> int:
    args = parse_args()
    if args.atol < 0 or args.rtol < 0:
        raise ValueError("--atol and --rtol must be non-negative")
    manifest_protocol_spec(args.manifest_protocol)
    if args.manifest_protocol != GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        raise ValueError("Baseline-reference parity is only defined for the chopped protocol")
    if args.split != "ood-t_chopped":
        raise ValueError("Formal Table 1 baseline-reference parity requires --split ood-t_chopped")

    local = _load_metrics(args.local_score)
    reference = _load_metrics(args.reference_score)
    metrics: dict[str, dict[str, Any]] = {}
    passed = True
    for name in REQUIRED_METRICS:
        local_value = local[name]
        reference_value = reference[name]
        tolerance = args.atol + args.rtol * abs(reference_value)
        absolute_error = abs(local_value - reference_value)
        metric_passed = absolute_error <= tolerance
        metrics[name] = {
            "local": local_value,
            "reference": reference_value,
            "absolute_error": absolute_error,
            "tolerance": tolerance,
            "passed": metric_passed,
        }
        passed = passed and metric_passed

    report = {
        "kind": "greenearthnet_baseline_reference_parity_report",
        "baseline": args.baseline,
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
        "metrics": metrics,
        "notes": [
            "The reference score must be produced by the public baseline implementation and public evaluator on the exact same frozen OOD-t chopped population.",
            "This check is separate from evaluator parity: it validates baseline construction, not only metric computation.",
        ],
    }
    output = write_json_atomic(report, args.output)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"baseline_reference_parity={output}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
