#!/usr/bin/env python
"""Strict GreenEarthNet-style scoring for a frozen Table 1 manifest.

The repository already contains the metric implementation. This wrapper adds
the same safeguards used for ENS: the prediction NetCDF tree must be a
hash-verified, exact image of the requested IID/OOD manifest, and a comparison
score (for Outperformance) must be tied to the same target manifest.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

from data.earthnet_manifest import (
    GREENEARTHNET_CHOPPED_PROTOCOL_ID,
    PROTOCOL_ID,
    load_manifest_files,
    manifest_protocol_spec,
    resolve_manifest_root,
    write_json_atomic,
)
from eval.earthnet_table1 import (
    TABLE1_SCHEMA_VERSION,
    greenearthnet_relative_path,
    source_manifest_identity,
)
from eval.eval_greenearthnet_official import score_directory
from eval.greenearthnet_protocol import (
    OFFICIAL_EVALUATOR_COMMIT,
    PREDICTION_GRID_CLIMATOLOGY_DAILY,
    PREDICTION_GRID_FIVE_DAILY_20,
    VALID_PREDICTION_GRIDS,
    summarize_score_parquets,
)
from eval.stage2_evaluation_provenance import (
    output_file_record,
    prediction_records_digest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score a manifest-pinned NDVI NetCDF export for Table 1."
    )
    parser.add_argument("--prediction-dir", required=True)
    parser.add_argument("--prediction-manifest", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--manifest-protocol",
        default=PROTOCOL_ID,
        help="Protocol of --manifest; formal OOD-t uses greenearthnet_cvpr2024_chopped_v1.",
    )
    parser.add_argument(
        "--split",
        required=True,
        help="Exact frozen manifest role (for example ood-t_chopped), never an alias.",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--verify-manifest-sizes", action="store_true")
    parser.add_argument("--comparison-score-dir")
    parser.add_argument(
        "--allow-extra-predictions",
        action="store_true",
        help="Legacy escape hatch; formal Table 1 invocations must not use this.",
    )
    return parser.parse_args()


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {label} JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must be a JSON object: {path}")
    return payload


def _safe_relative(value: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe prediction manifest path: {value!r}")
    return path.as_posix()


def _prediction_grid_contract(manifest: Mapping[str, Any]) -> tuple[str, str | None]:
    """Validate the public output-time grid declared by a prediction manifest."""

    prediction_grid = manifest.get("prediction_grid")
    if prediction_grid not in VALID_PREDICTION_GRIDS:
        raise ValueError(
            "Prediction manifest must declare a supported public prediction_grid; "
            f"got {prediction_grid!r}"
        )
    baseline = manifest.get("baseline")
    identity = manifest.get("identity")
    identity_baseline = identity.get("baseline") if isinstance(identity, Mapping) else None
    if baseline is None:
        baseline = identity_baseline
    elif identity_baseline is not None and baseline != identity_baseline:
        raise ValueError("Prediction manifest baseline and identity.baseline disagree")
    if baseline is not None and not isinstance(baseline, str):
        raise ValueError("Prediction manifest baseline must be a string when present")
    if baseline not in (None, "persistence", "climatology"):
        raise ValueError(f"Unsupported formal deterministic baseline {baseline!r}")
    if baseline == "climatology" and prediction_grid != PREDICTION_GRID_CLIMATOLOGY_DAILY:
        raise ValueError(
            "Public Climatology must declare the exact daily day-50-plus grid; "
            "do not silently resample it to the learned-model grid."
        )
    if (
        prediction_grid == PREDICTION_GRID_CLIMATOLOGY_DAILY
        and baseline != "climatology"
    ):
        raise ValueError(
            "Only the public Climatology baseline may use the daily day-50-plus grid"
        )
    if (
        prediction_grid == PREDICTION_GRID_FIVE_DAILY_20
        and baseline == "climatology"
    ):
        raise ValueError("Public Climatology cannot be registered on the 20-step grid")
    return str(prediction_grid), baseline


def _validate_prediction_tree(
    prediction_root: Path,
    manifest_path: Path,
    *,
    expected: dict[str, str],
    expected_split: str,
    expected_manifest_protocol: str,
    expected_source_manifest: Mapping[str, Any],
    allow_extra: bool,
) -> dict[str, Any]:
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Formal Table 1 GreenEarthNet scoring requires a prediction manifest: "
            f"{manifest_path}"
        )
    manifest = _load_json_object(manifest_path, label="prediction manifest")
    prediction_protocol = str(manifest.get("manifest_protocol", PROTOCOL_ID))
    if prediction_protocol != expected_manifest_protocol:
        raise ValueError(
            "Prediction manifest protocol does not match the frozen target manifest: "
            f"prediction={prediction_protocol!r}, expected={expected_manifest_protocol!r}"
        )
    if manifest.get("split") != expected_split:
        raise ValueError(
            "Prediction manifest split does not match the frozen target manifest: "
            f"prediction={manifest.get('split')!r}, expected={expected_split!r}"
        )
    if manifest.get("source_manifest") != dict(expected_source_manifest):
        raise ValueError(
            "Prediction manifest source_manifest does not match the frozen target "
            "manifest; use a fresh export/registration rather than mixing tracks."
        )
    prediction_grid, baseline = _prediction_grid_contract(manifest)
    files = manifest.get("files")
    hash_mode = manifest.get("hash_mode")
    if not isinstance(files, list) or hash_mode not in {"none", "sha256"}:
        raise ValueError("Prediction manifest has no valid files/hash_mode contract")
    records_by_path: dict[str, Mapping[str, Any]] = {}
    for record in files:
        if not isinstance(record, Mapping) or not isinstance(record.get("path"), str):
            raise ValueError("Prediction manifest contains an invalid output record")
        relative = _safe_relative(str(record["path"]))
        if relative in records_by_path:
            raise ValueError(f"Prediction manifest lists duplicate output {relative!r}")
        records_by_path[relative] = record

    actual = {
        path.relative_to(prediction_root).as_posix()
        for path in prediction_root.rglob("*.nc")
        if path.is_file()
    }
    listed = set(records_by_path)
    required = set(expected)
    missing_manifest = sorted(required - listed)
    extra_manifest = sorted(listed - required)
    missing_files = sorted(required - actual)
    extra_files = sorted(actual - required)
    if (
        missing_manifest
        or extra_manifest
        or missing_files
        or (extra_files and not allow_extra)
    ):
        details: list[str] = []
        if missing_manifest:
            details.append(f"manifest_missing={missing_manifest[:5]}")
        if extra_manifest:
            details.append(f"manifest_extra={extra_manifest[:5]}")
        if missing_files:
            details.append(f"file_missing={missing_files[:5]}")
        if extra_files:
            details.append(f"file_extra={extra_files[:5]}")
        raise ValueError(
            "NDVI prediction directory does not exactly match the frozen manifest "
            "(" + "; ".join(details) + ")"
        )

    observed_records: list[dict[str, Any]] = []
    for relative in sorted(records_by_path):
        record = records_by_path[relative]
        observed = output_file_record(
            prediction_root / relative,
            root=prediction_root,
            hash_mode=hash_mode,
        )
        for key in ("size_bytes", "sha256"):
            if key in record and observed.get(key) != record.get(key):
                raise ValueError(
                    f"NDVI prediction content no longer matches manifest: {relative}"
                )
        if "sample_id" in record:
            observed["sample_id"] = record["sample_id"]
        observed_records.append(observed)
    digest = prediction_records_digest(observed_records)
    if manifest.get("files_sha256") != digest:
        raise ValueError("NDVI prediction manifest files_sha256 does not match outputs")
    return {
        "tracked": True,
        "manifest": {
            "path": str(manifest_path),
            "size_bytes": int(manifest_path.stat().st_size),
            "sha256": _sha256_file(manifest_path),
        },
        "kind": manifest.get("kind"),
        "format": manifest.get("format"),
        "split": manifest.get("split"),
        "manifest_protocol": prediction_protocol,
        "source_manifest": dict(expected_source_manifest),
        "prediction_grid": prediction_grid,
        "baseline": baseline,
        "num_predictions": len(required),
        "files_sha256": digest,
        "extra_predictions_allowed": bool(extra_files and allow_extra),
    }


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(8 * 1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _comparison_provenance(
    score_dir: str | None,
    source_manifest: Mapping[str, Any],
    *,
    manifest_protocol: str,
    split: str,
    prediction_grid: str,
) -> dict[str, Any] | None:
    if not score_dir:
        return None
    root = Path(score_dir).expanduser().resolve()
    provenance_path = root / "score_provenance.json"
    provenance = _load_json_object(provenance_path, label="comparison score provenance")
    comparison_manifest = provenance.get("source_manifest")
    if comparison_manifest != dict(source_manifest):
        raise ValueError(
            "Comparison score uses a different frozen source manifest; refusing "
            "to calculate Table 1 Outperformance across splits."
        )
    if provenance.get("source_manifest_protocol") != manifest_protocol:
        raise ValueError(
            "Comparison score uses a different manifest protocol; refusing "
            "to calculate Table 1 Outperformance across protocols."
        )
    if provenance.get("evaluation_track") != split:
        raise ValueError(
            "Comparison score uses a different evaluation track; refusing "
            "to calculate Table 1 Outperformance across tracks."
        )
    comparison_prediction = provenance.get("prediction_validation")
    if not isinstance(comparison_prediction, Mapping):
        raise ValueError("Comparison score has no validated prediction-grid provenance")
    comparison_grid = comparison_prediction.get("prediction_grid")
    comparison_baseline = comparison_prediction.get("baseline")
    if comparison_grid not in VALID_PREDICTION_GRIDS:
        raise ValueError("Comparison score declares an unsupported prediction grid")
    if comparison_baseline != "climatology":
        raise ValueError(
            "Formal Table 1 Outperformance must use the exact Climatology score "
            "as its comparison, not another learned or deterministic method."
        )
    if (
        prediction_grid != PREDICTION_GRID_FIVE_DAILY_20
        or comparison_grid != PREDICTION_GRID_CLIMATOLOGY_DAILY
    ):
        raise ValueError(
            "Formal Table 1 Outperformance requires a 20-step learned/Persistence "
            "prediction compared with the public daily Climatology baseline."
        )
    return {
        "score_dir": str(root),
        "prediction_grid": comparison_grid,
        "baseline": comparison_baseline,
        "score_provenance": {
            "path": str(provenance_path),
            "size_bytes": int(provenance_path.stat().st_size),
            "sha256": _sha256_file(provenance_path),
        },
    }


def _reject_stale_score_parquets(output: Path, sources: list[Path]) -> None:
    """Fail closed if a reused score directory contains another manifest's regions."""

    expected = {f"scores_en21x_{source.parent.name}.parquet" for source in sources}
    actual = {path.name for path in output.glob("scores_en21x_*.parquet")} if output.is_dir() else set()
    unexpected = sorted(actual - expected)
    if unexpected:
        raise FileExistsError(
            "Score output directory contains stale region Parquets outside the "
            f"frozen manifest: {unexpected[:10]}. Use a fresh --output-dir "
            "instead of mixing score populations."
        )


def main() -> int:
    args = parse_args()
    manifest_protocol_spec(args.manifest_protocol)
    if args.workers == 0 or args.workers < -1:
        raise ValueError("--workers must be -1 or a positive integer")
    workers = max(1, os.cpu_count() or 1) if args.workers == -1 else args.workers
    dataset_root = resolve_manifest_root(
        args.dataset_root,
        protocol=args.manifest_protocol,
    )
    sources = load_manifest_files(
        args.manifest,
        dataset_root,
        expected_split=args.split,
        expected_protocol=args.manifest_protocol,
        verify_exists=True,
        verify_sizes=args.verify_manifest_sizes,
    )
    expected: dict[str, str] = {}
    for source in sources:
        relative = greenearthnet_relative_path(source)
        if relative in expected:
            raise ValueError(f"Duplicate target-relative prediction path: {relative}")
        expected[relative] = source.stem

    source_manifest = source_manifest_identity(args.manifest)
    prediction_root = Path(args.prediction_dir).expanduser().resolve()
    prediction_manifest = Path(args.prediction_manifest).expanduser().resolve()
    prediction_validation = _validate_prediction_tree(
        prediction_root,
        prediction_manifest,
        expected=expected,
        expected_split=args.split,
        expected_manifest_protocol=args.manifest_protocol,
        expected_source_manifest=source_manifest,
        allow_extra=args.allow_extra_predictions,
    )
    comparison = _comparison_provenance(
        args.comparison_score_dir,
        source_manifest,
        manifest_protocol=args.manifest_protocol,
        split=args.split,
        prediction_grid=str(prediction_validation["prediction_grid"]),
    )

    output = Path(args.output_dir).expanduser().resolve()
    _reject_stale_score_parquets(output, sources)
    score_summary = score_directory(
        sources,
        prediction_root,
        output,
        workers=workers,
        prediction_grid=str(prediction_validation["prediction_grid"]),
    )
    metrics = summarize_score_parquets(
        output,
        args.comparison_score_dir,
    )
    if not all(_is_finite_number(value) for value in metrics.values()):
        raise ValueError("GreenEarthNet metrics contain non-finite values")
    protocol_label = (
        "GreenEarthNet CVPR 2024 OOD-t chopped"
        if (
            args.manifest_protocol == GREENEARTHNET_CHOPPED_PROTOCOL_ID
            and args.split == "ood-t_chopped"
        )
        else "GreenEarthNet-style internal diagnostic"
    )
    result = {
        "protocol": protocol_label,
        "official_evaluator_commit": OFFICIAL_EVALUATOR_COMMIT,
        "source_manifest_protocol": args.manifest_protocol,
        "evaluation_track": args.split,
        "prediction_grid": prediction_validation["prediction_grid"],
        "num_target_files": len(sources),
        "num_eligible_pixels": score_summary["num_eligible_pixels"],
        "metrics": metrics,
    }
    metrics_json = output / "metrics_en21x.json"
    metrics_csv = output / "metrics_en21x.csv"
    write_json_atomic(result, metrics_json)
    _write_metrics_csv(metrics, metrics_csv)
    provenance = {
        "schema_version": TABLE1_SCHEMA_VERSION,
        "kind": "table1_greenearthnet_score",
        "source_manifest": source_manifest,
        "source_manifest_protocol": args.manifest_protocol,
        "evaluation_track": args.split,
        "prediction_validation": prediction_validation,
        "comparison": comparison,
        "workers": int(workers),
        "num_target_files": len(sources),
        "num_eligible_pixels": score_summary["num_eligible_pixels"],
        "metric_output": {
            "path": str(metrics_json),
            "size_bytes": int(metrics_json.stat().st_size),
            "sha256": _sha256_file(metrics_json),
        },
    }
    write_json_atomic(provenance, output / "score_provenance.json")
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    print(f"score_provenance={output / 'score_provenance.json'}")
    return 0


def _is_finite_number(value: object) -> bool:
    import math

    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _write_metrics_csv(metrics: Mapping[str, float], path: Path) -> None:
    import csv

    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        for key in sorted(metrics):
            writer.writerow([key, metrics[key]])
    temporary.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
