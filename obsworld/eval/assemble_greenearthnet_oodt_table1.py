#!/usr/bin/env python
"""Assemble formal GreenEarthNet CVPR-2024 OOD-t Table 1 rows.

This command is deliberately separate from ``assemble_stage2_table1.py``.
The latter retains the raw EarthNet2021x IID/OOD diagnostic/ENS path; this
assembler accepts only the explicit public ``ood-t_chopped`` track and the
GreenEarthNet metrics used by the paper-facing Table 1.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import (  # noqa: E402
    GREENEARTHNET_CHOPPED_DATASET_ID,
    GREENEARTHNET_CHOPPED_PROTOCOL_ID,
    write_json_atomic,
)
from eval.table1_artifact_contract import (  # noqa: E402
    PREDICTION_GRID_CLIMATOLOGY_DAILY,
    PREDICTION_GRID_FIVE_DAILY_20,
    TABLE1_SCHEMA_VERSION,
    VALID_PREDICTION_GRIDS,
    source_manifest_identity,
)
from eval.greenearthnet_published_table2 import published_table2_rows  # noqa: E402


CORE_METHOD_IDS = ("persistence", "climatology", "direct-p4", "rollout-p4")
BASELINE_METHOD_IDS = ("persistence", "climatology")
METHOD_ORDER = {
    "persistence": 0,
    "previous-year": 1,
    "climatology": 1,
    "earthformer": 4,
    "predrnn": 5,
    "simvp": 6,
    "contextformer": 7,
    "direct-p4": 10,
    "rollout-p4": 11,
}
METRIC_KEYS = ("R2", "rmse", "nse", "biasabs", "outperformance", "rmse25")
RMSE25_TIME_GRID_NOTE = (
    "`rmse25` serializes the public evaluator's `rmse_0_5`: for the 20-step "
    "five-daily grid it covers the first 25 days, while public Climatology's "
    "daily day-50-plus grid covers its first five daily points. Keep the source "
    "grid visible and do not rank those two RMSE25 cells as an equal-horizon claim."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register one provenance-bound OOD-t chopped Table 1 row."
    )
    parser.add_argument("--table-root", required=True)
    parser.add_argument("--method-id", required=True)
    parser.add_argument("--method-label", required=True)
    parser.add_argument("--method-kind", required=True)
    parser.add_argument("--score", required=True, help="metrics_en21x.json")
    parser.add_argument("--score-provenance", required=True, help="score_provenance.json")
    parser.add_argument("--target-manifest", required=True, help="Frozen ood-t_chopped manifest")
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--seed", default=None)
    parser.add_argument("--params-millions", type=float, default=0.0)
    parser.add_argument(
        "--evaluator-parity-report",
        default=None,
        help="Optional passed report from eval/verify_greenearthnet_evaluator_parity.py.",
    )
    parser.add_argument(
        "--baseline-reference-parity-report",
        default=None,
        help=(
            "Optional report from eval/verify_greenearthnet_baseline_reference.py; "
            "required for a paper-ready Persistence/Climatology row."
        ),
    )
    parser.add_argument("--overwrite-row", action="store_true")
    return parser.parse_args()


def _load_json(path: str | Path, *, label: str) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Missing {label}: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {label} JSON: {source}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must be a JSON object: {source}")
    return payload


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


def _finite(value: object, *, name: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return float(value)


def _target_context(path: str | Path) -> dict[str, Any]:
    payload = _load_json(path, label="frozen target manifest")
    if payload.get("dataset") != GREENEARTHNET_CHOPPED_DATASET_ID:
        raise ValueError("Formal Table 1 target manifest is not a GreenEarthNet chopped manifest")
    if payload.get("protocol") != GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        raise ValueError("Formal Table 1 target manifest has the wrong protocol")
    if payload.get("role") != "ood-t_chopped" or payload.get("split") != "ood-t_chopped":
        raise ValueError("Formal Table 1 target manifest must be exactly ood-t_chopped")
    sources = payload.get("source_splits")
    if sources != ["ood-t_chopped"]:
        raise ValueError("Formal Table 1 target manifest must have source_splits=[ood-t_chopped]")
    if not isinstance(payload.get("num_files"), int) or int(payload["num_files"]) <= 0:
        raise ValueError("Formal Table 1 target manifest has no positive num_files")
    if not isinstance(payload.get("files_sha256"), str) or not payload["files_sha256"]:
        raise ValueError("Formal Table 1 target manifest has no files_sha256")
    source_manifest = source_manifest_identity(path)
    return {
        "source_manifest": source_manifest,
        "num_files": int(payload["num_files"]),
        "files_sha256": str(payload["files_sha256"]),
    }


def _parity_context(
    report_path: str | Path | None,
    *,
    target: Mapping[str, Any],
    score_identity: Mapping[str, Any],
) -> dict[str, Any]:
    if report_path is None:
        return {"status": "pending", "report": None}
    payload = _load_json(report_path, label="evaluator parity report")
    if payload.get("kind") != "greenearthnet_evaluator_parity_report":
        raise ValueError("Unexpected evaluator parity report kind")
    if payload.get("source_manifest") != target["source_manifest"]:
        raise ValueError("Evaluator parity report belongs to a different frozen target manifest")
    if payload.get("source_manifest_protocol") != GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        raise ValueError("Evaluator parity report uses a different protocol")
    if payload.get("evaluation_track") != "ood-t_chopped":
        raise ValueError("Evaluator parity report uses a different track")
    if payload.get("local_score") != dict(score_identity):
        raise ValueError(
            "Evaluator parity report was made from a different local score artifact"
        )
    return {
        "status": "passed" if payload.get("passed") is True else "failed",
        "report": _identity(report_path),
    }


def _baseline_reference_parity_context(
    report_path: str | Path | None,
    *,
    method_id: str,
    target: Mapping[str, Any],
    score_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind deterministic baseline construction to an independent public run."""

    if method_id not in BASELINE_METHOD_IDS:
        if report_path is not None:
            raise ValueError(
                "--baseline-reference-parity-report is valid only for Persistence "
                "or Climatology rows"
            )
        return {"status": "not_applicable", "report": None}
    if report_path is None:
        return {"status": "pending", "report": None}

    payload = _load_json(report_path, label="baseline-reference parity report")
    if payload.get("kind") != "greenearthnet_baseline_reference_parity_report":
        raise ValueError("Unexpected baseline-reference parity report kind")
    if payload.get("baseline") != method_id:
        raise ValueError("Baseline-reference parity report belongs to a different baseline")
    if payload.get("source_manifest") != target["source_manifest"]:
        raise ValueError(
            "Baseline-reference parity report belongs to a different frozen target manifest"
        )
    if payload.get("source_manifest_protocol") != GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        raise ValueError("Baseline-reference parity report uses a different protocol")
    if payload.get("evaluation_track") != "ood-t_chopped":
        raise ValueError("Baseline-reference parity report uses a different track")
    if payload.get("local_score") != dict(score_identity):
        raise ValueError(
            "Baseline-reference parity report was made from a different local score artifact"
        )
    return {
        "status": "passed" if payload.get("passed") is True else "failed",
        "report": _identity(report_path),
    }


def _score_context(
    score_path: str | Path,
    provenance_path: str | Path,
    *,
    target: Mapping[str, Any],
) -> dict[str, Any]:
    score = _load_json(score_path, label="GreenEarthNet score")
    metrics_raw = score.get("metrics")
    if not isinstance(metrics_raw, Mapping):
        raise ValueError("GreenEarthNet score has no metrics object")
    metrics: dict[str, float | None] = {}
    for key in METRIC_KEYS:
        if key == "outperformance" and key not in metrics_raw:
            metrics[key] = None
        else:
            metrics[key] = _finite(metrics_raw.get(key), name=f"score metric {key}")

    provenance = _load_json(provenance_path, label="GreenEarthNet score provenance")
    if provenance.get("kind") != "table1_greenearthnet_score":
        raise ValueError("Score was not emitted by eval/score_table1_greenearthnet.py")
    if provenance.get("source_manifest") != target["source_manifest"]:
        raise ValueError("Score provenance belongs to a different frozen target manifest")
    if provenance.get("source_manifest_protocol") != GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        raise ValueError("Score provenance uses a different protocol")
    if provenance.get("evaluation_track") != "ood-t_chopped":
        raise ValueError("Score provenance uses a different evaluation track")
    if provenance.get("num_target_files") != target["num_files"]:
        raise ValueError("Score provenance target count differs from frozen manifest")
    prediction = provenance.get("prediction_validation")
    if not isinstance(prediction, Mapping) or prediction.get("tracked") is not True:
        raise ValueError("Score provenance has no tracked prediction validation")
    if prediction.get("manifest_protocol") != GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        raise ValueError("Prediction export uses a different protocol")
    if prediction.get("split") != "ood-t_chopped":
        raise ValueError("Prediction export uses a different track")
    if prediction.get("source_manifest") != target["source_manifest"]:
        raise ValueError("Prediction export belongs to a different frozen target manifest")
    prediction_grid = prediction.get("prediction_grid")
    if prediction_grid not in VALID_PREDICTION_GRIDS:
        raise ValueError(
            "Score provenance has no supported declared prediction_grid; "
            "re-score from a current formal prediction manifest."
        )
    return {
        "metrics": metrics,
        "score": _identity(score_path),
        "provenance": _identity(provenance_path),
        "prediction_grid": str(prediction_grid),
    }


def _row(args: argparse.Namespace) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.method_id):
        raise ValueError("--method-id must be a safe stable identifier")
    if args.params_millions < 0:
        raise ValueError("--params-millions must be non-negative")
    target = _target_context(args.target_manifest)
    score = _score_context(args.score, args.score_provenance, target=target)
    expected_prediction_grid = (
        PREDICTION_GRID_CLIMATOLOGY_DAILY
        if args.method_id == "climatology"
        else PREDICTION_GRID_FIVE_DAILY_20
    )
    if score["prediction_grid"] != expected_prediction_grid:
        raise ValueError(
            f"Table 1 row {args.method_id!r} declares prediction_grid="
            f"{score['prediction_grid']!r}, expected {expected_prediction_grid!r}."
        )
    if args.method_id != "climatology" and score["metrics"]["outperformance"] is None:
        raise ValueError(
            "Every learned/Persistence row must be scored against the exact Climatology "
            "score directory so Table 1 Outperformance is defined."
        )
    parity = _parity_context(
        args.evaluator_parity_report,
        target=target,
        score_identity=score["score"],
    )
    baseline_reference_parity = _baseline_reference_parity_context(
        args.baseline_reference_parity_report,
        method_id=args.method_id,
        target=target,
        score_identity=score["score"],
    )
    checkpoint = _identity(args.checkpoint) if args.checkpoint else None
    return {
        "schema_version": TABLE1_SCHEMA_VERSION,
        "kind": "greenearthnet_oodt_table1_row",
        "protocol": GREENEARTHNET_CHOPPED_PROTOCOL_ID,
        "evaluation_track": "ood-t_chopped",
        "method": {
            "id": args.method_id,
            "label": args.method_label,
            "kind": args.method_kind,
            "seed": args.seed,
            "params_millions": float(args.params_millions),
            "checkpoint": checkpoint,
        },
        "target": target,
        "score": score,
        "evaluator_parity": parity,
        "baseline_reference_parity": baseline_reference_parity,
    }


def _context_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    target = row["target"]
    return {
        "schema_version": TABLE1_SCHEMA_VERSION,
        "kind": "greenearthnet_oodt_table1_context",
        "protocol": GREENEARTHNET_CHOPPED_PROTOCOL_ID,
        "evaluation_track": "ood-t_chopped",
        "target_manifest": target["source_manifest"],
        "target_num_files": target["num_files"],
        "target_files_sha256": target["files_sha256"],
        "metric_columns": list(METRIC_KEYS),
    }


def _write_row(root: Path, row: Mapping[str, Any], *, overwrite: bool) -> None:
    root.mkdir(parents=True, exist_ok=True)
    context_path = root / "table1_oodt_chopped_context.json"
    context = _context_from_row(row)
    if context_path.is_file():
        if _load_json(context_path, label="Table 1 context") != context:
            raise ValueError("Table root already binds a different formal OOD-t target manifest")
    else:
        write_json_atomic(context, context_path)
    row_path = root / "rows" / f"{row['method']['id']}.json"
    if row_path.is_file() and not overwrite:
        raise FileExistsError(f"Row already exists: {row_path}; pass --overwrite-row to replace it")
    write_json_atomic(row, row_path)


def _load_rows(root: Path) -> list[dict[str, Any]]:
    context_path = root / "table1_oodt_chopped_context.json"
    context = _load_json(context_path, label="Table 1 context")
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "rows").glob("*.json")):
        row = _load_json(path, label="Table 1 row")
        if row.get("kind") != "greenearthnet_oodt_table1_row":
            raise ValueError(f"Unexpected row kind in {path}")
        method_id = str(row.get("method", {}).get("id", ""))
        if "baseline_reference_parity" not in row:
            # Table roots created before this gate remain readable, but cannot
            # become paper-ready until their baseline rows are re-registered.
            row["baseline_reference_parity"] = {
                "status": "pending" if method_id in BASELINE_METHOD_IDS else "not_applicable",
                "report": None,
            }
        score = row.get("score")
        if not isinstance(score, Mapping) or score.get("prediction_grid") not in VALID_PREDICTION_GRIDS:
            raise ValueError(
                f"Row {path} has no declared prediction grid; re-register it with current formal scoring."
            )
        expected_prediction_grid = (
            PREDICTION_GRID_CLIMATOLOGY_DAILY
            if method_id == "climatology"
            else PREDICTION_GRID_FIVE_DAILY_20
        )
        if score["prediction_grid"] != expected_prediction_grid:
            raise ValueError(
                f"Row {path} uses incompatible prediction_grid={score['prediction_grid']!r}."
            )
        if _context_from_row(row) != context:
            raise ValueError(f"Row {path} is bound to a different formal OOD-t context")
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (METHOD_ORDER.get(str(row["method"]["id"]), 100), str(row["method"]["label"])),
    )


def _format(value: object, digits: int = 4) -> str:
    return "—" if value is None else f"{float(value):.{digits}f}"


def _format_outperformance(value: object) -> str:
    return "—" if value is None else f"{100.0 * float(value):.1f}%"


def _format_with_std(
    value: object,
    std: object,
    *,
    digits: int = 4,
    percent: bool = False,
) -> str:
    if value is None:
        return "—"
    scale = 100.0 if percent else 1.0
    suffix = "%" if percent else ""
    mean_text = f"{scale * float(value):.{1 if percent else digits}f}"
    if std is None:
        return mean_text + suffix
    std_text = f"{scale * float(std):.{1 if percent else digits}f}"
    return f"{mean_text}±{std_text}{suffix}"


def _render(root: Path, rows: list[dict[str, Any]]) -> None:
    table_rows: list[dict[str, Any]] = []
    for row in rows:
        method = row["method"]
        metrics = row["score"]["metrics"]
        table_rows.append(
            {
                "method_id": method["id"],
                "method": method["label"],
                "type": method["kind"],
                "seed": method["seed"] or "",
                "params_millions": method["params_millions"],
                "R2": metrics["R2"],
                "rmse": metrics["rmse"],
                "nse": metrics["nse"],
                "biasabs": metrics["biasabs"],
                "outperformance": metrics["outperformance"],
                "rmse25": metrics["rmse25"],
                "prediction_grid": row["score"]["prediction_grid"],
                "evaluator_parity": row["evaluator_parity"]["status"],
                "baseline_reference_parity": row["baseline_reference_parity"]["status"],
                "metric_std": {},
                "result_source": "local_evaluation",
                "citation": None,
            }
        )
    local_table_rows = list(table_rows)
    local_method_ids = {str(item["method_id"]) for item in local_table_rows}
    published_rows = [
        row for row in published_table2_rows()
        if str(row["method_id"]) not in local_method_ids
    ]
    table_rows.extend(published_rows)
    table_rows.sort(
        key=lambda item: (
            METHOD_ORDER.get(str(item["method_id"]), 100),
            str(item["method"]),
        )
    )
    present = local_method_ids
    missing = [identifier for identifier in CORE_METHOD_IDS if identifier not in present]
    all_parity_passed = bool(local_table_rows) and all(
        item["evaluator_parity"] == "passed" for item in local_table_rows
    )
    all_non_climate_have_outperformance = all(
        item["method_id"] == "climatology" or item["outperformance"] is not None
        for item in local_table_rows
    )
    all_baseline_reference_passed = all(
        any(
            item["method_id"] == baseline_id
            and item["baseline_reference_parity"] == "passed"
            for item in local_table_rows
        )
        for baseline_id in BASELINE_METHOD_IDS
    )
    status = {
        "rows_present": [str(item["method_id"]) for item in table_rows],
        "locally_evaluated_rows_present": sorted(local_method_ids),
        "published_reference_rows_present": [
            str(item["method_id"])
            for item in table_rows
            if item["result_source"] == "published_reference"
        ],
        "required_rows_missing": missing,
        "complete_core_rows": not missing,
        "evaluator_parity_passed_for_all_rows": all_parity_passed,
        "baseline_reference_parity_passed_for_baselines": all_baseline_reference_passed,
        "outperformance_defined_for_non_climatology_rows": all_non_climate_have_outperformance,
        "prediction_grid_by_method": {
            str(item["method_id"]): str(item["prediction_grid"])
            for item in table_rows
        },
        "rmse25_time_grid_note": RMSE25_TIME_GRID_NOTE,
        "paper_ready": bool(
            not missing
            and all_parity_passed
            and all_baseline_reference_passed
            and all_non_climate_have_outperformance
        ),
        "warning": (
            None
            if (
                not missing
                and all_parity_passed
                and all_baseline_reference_passed
                and all_non_climate_have_outperformance
            )
            else "This is a partial/provisional formal OOD-t Table 1 bundle. Do not paste it as a final paper table until all core rows, official-evaluator parity reports, and deterministic-baseline reference-parity reports are present."
        ),
    }
    bundle = {
        "schema_version": TABLE1_SCHEMA_VERSION,
        "kind": "greenearthnet_oodt_table1_bundle",
        "status": status,
        "rows": rows,
        "published_reference_rows": published_rows,
    }
    write_json_atomic(bundle, root / "table1_oodt_chopped_bundle.json")
    columns = [
        "method_id", "method", "type", "seed", "params_millions", "R2", "rmse",
        "nse", "biasabs", "outperformance", "rmse25", "prediction_grid",
        "evaluator_parity", "baseline_reference_parity", "result_source", "citation",
    ]
    csv_path = root / "table1_oodt_chopped.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for item in table_rows:
            csv_item = dict(item)
            csv_item.pop("metric_std", None)
            citation = csv_item.get("citation")
            csv_item["citation"] = "" if citation is None else citation["url"]
            writer.writerow(csv_item)
    markdown = [
        "# GreenEarthNet CVPR-2024 OOD-t chopped — Table 1",
        "",
        "This file is generated only from frozen-manifest, hash-verified score artifacts.",
        "",
        "| Method | Source | Seed | Params | R² ↑ | RMSE ↓ | NSE ↑ | |Bias| ↓ | Outperformance ↑ | RMSE25† ↓ |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in table_rows:
        params = "0" if float(item["params_millions"]) == 0 else f"{float(item['params_millions']):.2f}M"
        markdown.append(
            "| {method} | {source} | {seed} | {params} | {r2} | {rmse} | {nse} | {bias} | {out} | {rmse25} |".format(
                method=item["method"],
                source=("local" if item["result_source"] == "local_evaluation" else "Benson et al., CVPR 2024, Table 2"),
                seed=item["seed"] or "—", params=params,
                r2=_format_with_std(item["R2"], item["metric_std"].get("R2")),
                rmse=_format_with_std(item["rmse"], item["metric_std"].get("rmse")),
                nse=_format_with_std(item["nse"], item["metric_std"].get("nse")),
                bias=_format_with_std(item["biasabs"], item["metric_std"].get("biasabs")),
                out=_format_with_std(item["outperformance"], item["metric_std"].get("outperformance"), percent=True),
                rmse25=_format_with_std(item["rmse25"], item["metric_std"].get("rmse25")),
            )
        )
    markdown.extend(
        [
            "",
            f"> † {RMSE25_TIME_GRID_NOTE}",
            "",
            "> Published-reference rows are copied from Benson et al., CVPR 2024, Table 2; they are not presented as local reruns. A same-ID local Persistence/Climatology row replaces the corresponding published row in this rendered table.",
            "",
            "> Source: https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html",
            "",
            "## Bundle status",
            "",
            "```json",
            json.dumps(status, indent=2),
            "```",
            "",
        ]
    )
    (root / "table1_oodt_chopped.md").write_text("\n".join(markdown), encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path(args.table_root).expanduser().resolve()
    row = _row(args)
    _write_row(root, row, overwrite=args.overwrite_row)
    _render(root, _load_rows(root))
    print(f"table_root={root}")
    print(f"row={root / 'rows' / (args.method_id + '.json')}")
    print(f"table={root / 'table1_oodt_chopped.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
