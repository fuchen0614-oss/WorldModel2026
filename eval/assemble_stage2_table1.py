#!/usr/bin/env python
"""Assemble raw EarthNet2021x IID/OOD diagnostic single-seed rows.

This legacy/raw path never recomputes a metric. It reads strict scorer
artifacts and records the raw-NPZ ENS bridge separately from the local NDVI
scorer. It is **not** the formal GreenEarthNet CVPR-2024 ``ood-t_chopped``
Table 1; use ``eval/assemble_greenearthnet_oodt_table1.py`` for that path.
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

from data.earthnet_manifest import write_json_atomic
from eval.table1_artifact_contract import TABLE1_SCHEMA_VERSION


REQUIRED_METHOD_IDS = ("persistence", "climatology", "direct-p4", "rollout-p4")
METHOD_ORDER = {
    "persistence": 0,
    "climatology": 1,
    "direct-p4": 10,
    "rollout-p4": 11,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add one verified row to the internal raw EarthNet2021x IID/OOD diagnostic bundle."
    )
    parser.add_argument("--table-root", required=True)
    parser.add_argument("--method-id", required=True)
    parser.add_argument("--method-label", required=True)
    parser.add_argument("--method-kind", required=True)
    parser.add_argument("--seed", default=None)
    parser.add_argument("--params-millions", type=float, default=0.0)
    parser.add_argument("--checkpoint")
    parser.add_argument("--iid-ens-score", required=True)
    parser.add_argument("--iid-ens-provenance", required=True)
    parser.add_argument("--iid-ndvi-score", required=True)
    parser.add_argument("--iid-ndvi-provenance", required=True)
    parser.add_argument("--iid-target-manifest", required=True)
    parser.add_argument("--iid-target-parity-report")
    parser.add_argument("--ood-ens-score", required=True)
    parser.add_argument("--ood-ens-provenance", required=True)
    parser.add_argument("--ood-ndvi-score", required=True)
    parser.add_argument("--ood-ndvi-provenance", required=True)
    parser.add_argument("--ood-target-manifest", required=True)
    parser.add_argument("--ood-target-parity-report")
    parser.add_argument("--overwrite-row", action="store_true")
    return parser.parse_args()


def _load_json(path: str | Path, *, label: str) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {label} JSON: {source}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must be a JSON object: {source}")
    return payload


def _file_identity(path: str | Path) -> dict[str, Any]:
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


def _finite(value: object, *, label: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be finite, got {value!r}")
    return float(value)


def _target_context(
    target_manifest: str | Path,
    parity_report: str | Path | None,
) -> dict[str, Any]:
    path = Path(target_manifest).expanduser().resolve()
    payload = _load_json(path, label="target manifest")
    if payload.get("kind") != "earthnet2021_score_target_manifest":
        raise ValueError(
            f"Unexpected target manifest kind={payload.get('kind')!r}; expected "
            "'earthnet2021_score_target_manifest'"
        )
    identity = payload.get("identity")
    if not isinstance(identity, Mapping):
        raise ValueError("Target manifest has no immutable source identity")
    source_manifest = identity.get("source_manifest")
    if not isinstance(source_manifest, Mapping):
        raise ValueError("Target manifest has no source manifest identity")
    num_targets = payload.get("num_targets")
    files_sha256 = payload.get("files_sha256")
    if not isinstance(num_targets, int) or num_targets <= 0 or not isinstance(files_sha256, str):
        raise ValueError("Target manifest has no valid num_targets/files_sha256 contract")

    parity = {
        "status": "raw_adapter_unverified",
        "report": None,
    }
    if parity_report:
        report_path = Path(parity_report).expanduser().resolve()
        report = _load_json(report_path, label="target parity report")
        report_target = report.get("generated_target_manifest")
        if not isinstance(report_target, Mapping):
            raise ValueError("Target parity report has no generated target manifest identity")
        if report_target.get("sha256") != _file_identity(path)["sha256"]:
            raise ValueError(
                "Target parity report belongs to a different generated target manifest"
            )
        if report.get("passed") is True and report.get("complete") is True:
            parity = {
                "status": "parity_verified",
                "report": _file_identity(report_path),
            }
        else:
            parity = {
                "status": str(report.get("status", "parity_failed")),
                "report": _file_identity(report_path),
            }

    return {
        "manifest": _file_identity(path),
        "split": payload.get("split"),
        "num_targets": num_targets,
        "files_sha256": files_sha256,
        "source_manifest": dict(source_manifest),
        "adapter_parity": parity,
    }


def _load_ens(
    score_path: str | Path,
    provenance_path: str | Path,
    *,
    target: Mapping[str, Any],
) -> dict[str, Any]:
    score_file = Path(score_path).expanduser().resolve()
    payload = _load_json(score_file, label="ENS score")
    score = _finite(payload.get("EarthNetScore"), label="EarthNetScore")
    provenance_file = Path(provenance_path).expanduser().resolve()
    provenance = _load_json(provenance_file, label="ENS score provenance")
    if provenance.get("kind") != "table1_official_earthnet_score":
        raise ValueError(
            "ENS artifact was not produced by eval/score_table1_earthnet.py; "
            "formal Table 1 rows require strict pairing provenance."
        )
    if provenance.get("pairing_verified") is not True:
        raise ValueError("ENS score provenance does not confirm target/prediction pairing")
    target_validation = provenance.get("target_validation")
    if not isinstance(target_validation, Mapping) or not target_validation.get("tracked"):
        raise ValueError("ENS score provenance has no tracked target validation")
    target_manifest = target_validation.get("manifest")
    if not isinstance(target_manifest, Mapping):
        raise ValueError("ENS score provenance has no target manifest identity")
    if target_manifest.get("sha256") != target["manifest"]["sha256"]:
        raise ValueError("ENS score and supplied target manifest do not match")
    if target_validation.get("files_sha256") != target["files_sha256"]:
        raise ValueError("ENS score target set differs from the supplied target manifest")
    components = {
        key: _finite(value, label=key)
        for key, value in payload.items()
        if key != "EarthNetScore" and isinstance(value, (int, float))
    }
    return {
        "score": score,
        "components": components,
        "score_file": _file_identity(score_file),
        "provenance_file": _file_identity(provenance_file),
    }


def _load_ndvi(
    score_path: str | Path,
    provenance_path: str | Path,
    *,
    target: Mapping[str, Any],
) -> dict[str, Any]:
    score_file = Path(score_path).expanduser().resolve()
    payload = _load_json(score_file, label="NDVI score")
    metrics = payload.get("metrics")
    if not isinstance(metrics, Mapping):
        raise ValueError("NDVI score has no metrics mapping")
    result = {
        "r2": _finite(metrics.get("R2"), label="GreenEarthNet R2"),
        "rmse": _finite(metrics.get("rmse"), label="GreenEarthNet rmse"),
        "outperformance": (
            _finite(metrics["outperformance"], label="GreenEarthNet outperformance")
            if "outperformance" in metrics
            else None
        ),
        "metrics": dict(metrics),
        "score_file": _file_identity(score_file),
    }
    provenance_file = Path(provenance_path).expanduser().resolve()
    provenance = _load_json(provenance_file, label="NDVI score provenance")
    if provenance.get("kind") != "table1_greenearthnet_score":
        raise ValueError(
            "NDVI artifact was not produced by eval/score_table1_greenearthnet.py; "
            "formal Table 1 rows require manifest-bound scoring."
        )
    if provenance.get("source_manifest") != target["source_manifest"]:
        raise ValueError("NDVI score source manifest differs from the ENS target manifest")
    if provenance.get("num_target_files") != target["num_targets"]:
        raise ValueError("NDVI score target count differs from the ENS target manifest")
    result["provenance_file"] = _file_identity(provenance_file)
    return result


def _row_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.method_id):
        raise ValueError("--method-id must be a safe stable identifier")
    if args.params_millions < 0:
        raise ValueError("--params-millions must be non-negative")
    splits: dict[str, dict[str, Any]] = {}
    for name in ("iid", "ood"):
        target = _target_context(
            getattr(args, f"{name}_target_manifest"),
            getattr(args, f"{name}_target_parity_report"),
        )
        ens = _load_ens(
            getattr(args, f"{name}_ens_score"),
            getattr(args, f"{name}_ens_provenance"),
            target=target,
        )
        ndvi = _load_ndvi(
            getattr(args, f"{name}_ndvi_score"),
            getattr(args, f"{name}_ndvi_provenance"),
            target=target,
        )
        splits[name] = {
            "target": target,
            "earthnetscore": ens,
            "greenearthnet": ndvi,
        }
    checkpoint = _file_identity(args.checkpoint) if args.checkpoint else None
    adapter_status = {
        split: splits[split]["target"]["adapter_parity"]["status"]
        for split in sorted(splits)
    }
    return {
        "schema_version": TABLE1_SCHEMA_VERSION,
        "kind": "stage2_table1_row",
        "method": {
            "id": args.method_id,
            "label": args.method_label,
            "kind": args.method_kind,
            "seed": args.seed,
            "params_millions": float(args.params_millions),
            "checkpoint": checkpoint,
        },
        "splits": splits,
        "formal_status": {
            "seed_status": "single_seed" if args.seed is not None else "deterministic_or_unspecified",
            "ens_adapter_status": adapter_status,
            "ens_ready_for_frozen_column": all(
                status == "parity_verified" for status in adapter_status.values()
            ),
            "ndvi_protocol": "manifest-bound GreenEarthNet-style scorer",
        },
    }


def _context_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    splits = row["splits"]
    return {
        "schema_version": TABLE1_SCHEMA_VERSION,
        "kind": "stage2_table1_context",
        "splits": {
            name: {
                "target_manifest": split["target"]["manifest"],
                "target_files_sha256": split["target"]["files_sha256"],
                "source_manifest": split["target"]["source_manifest"],
            }
            for name, split in sorted(splits.items())
        },
        "metric_families": {
            "ens": "EarthNetScore over strict paired RGBN NPZ exports",
            "ndvi": "manifest-bound GreenEarthNet-style R2/RMSE/Outperformance",
        },
    }


def _write_row_and_context(
    root: Path,
    row: Mapping[str, Any],
    *,
    overwrite: bool,
) -> None:
    context_path = root / "table1_context.json"
    context = _context_from_row(row)
    if context_path.is_file():
        existing = _load_json(context_path, label="Table 1 context")
        if existing != context:
            raise ValueError(
                "This Table 1 root already contains a different IID/OOD manifest "
                "context; use a separate table root instead of mixing protocols."
            )
    else:
        write_json_atomic(context, context_path)

    row_path = root / "rows" / f"{row['method']['id']}.json"
    if row_path.is_file() and not overwrite:
        raise FileExistsError(
            f"Table 1 row already exists: {row_path}. Pass --overwrite-row only "
            "after deliberately replacing the exact evaluation artifacts."
        )
    write_json_atomic(row, row_path)


def _load_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "rows").glob("*.json")):
        row = _load_json(path, label="Table 1 row")
        if row.get("kind") != "stage2_table1_row":
            raise ValueError(f"Unexpected Table 1 row kind: {path}")
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            METHOD_ORDER.get(str(row["method"]["id"]), 100),
            str(row["method"]["label"]),
        ),
    )


def _format_metric(value: object, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def _format_outperformance(value: object) -> str:
    if value is None:
        return "—"
    return f"{100.0 * float(value):.1f}%"


def _format_params(value: object) -> str:
    numeric = float(value)
    return "0" if numeric == 0 else f"{numeric:.1f}M"


def _render(root: Path, rows: list[dict[str, Any]]) -> None:
    table_rows: list[dict[str, Any]] = []
    for row in rows:
        method = row["method"]
        iid = row["splits"]["iid"]
        ood = row["splits"]["ood"]
        table_rows.append(
            {
                "method_id": method["id"],
                "method": method["label"],
                "type": method["kind"],
                "seed": method["seed"],
                "params_millions": method["params_millions"],
                "iid_r2": iid["greenearthnet"]["r2"],
                "iid_rmse": iid["greenearthnet"]["rmse"],
                "iid_outperformance": iid["greenearthnet"]["outperformance"],
                "iid_ens": iid["earthnetscore"]["score"],
                "ood_r2": ood["greenearthnet"]["r2"],
                "ood_rmse": ood["greenearthnet"]["rmse"],
                "ood_outperformance": ood["greenearthnet"]["outperformance"],
                "ood_ens": ood["earthnetscore"]["score"],
                "iid_ens_adapter_status": iid["target"]["adapter_parity"]["status"],
                "ood_ens_adapter_status": ood["target"]["adapter_parity"]["status"],
                "ens_ready_for_frozen_column": row["formal_status"]["ens_ready_for_frozen_column"],
            }
        )

    present = {item["method_id"] for item in table_rows}
    missing = [method for method in REQUIRED_METHOD_IDS if method not in present]
    fully_verified = bool(table_rows) and all(
        item["ens_ready_for_frozen_column"] for item in table_rows
    )
    status = {
        "rows_present": [item["method_id"] for item in table_rows],
        "required_rows_missing": missing,
        "complete_core_rows": not missing,
        "ens_adapter_parity_verified_for_all_rows": fully_verified,
        "paper_ready": bool(not missing and fully_verified),
        "warning": (
            None
            if fully_verified
            else (
                "ENS values are retained in the artifact but are provisional: "
                "the raw-NetCDF target adapter has not yet passed an independent "
                "official-target parity report. Do not paste the ENS column into "
                "the frozen manuscript until this becomes true."
            )
        ),
    }

    write_json_atomic(
        {
            "schema_version": TABLE1_SCHEMA_VERSION,
            "kind": "stage2_table1_bundle",
            "status": status,
            "rows": rows,
        },
        root / "table1_bundle.json",
    )
    _write_csv(root / "table1_single_seed.csv", table_rows)
    _write_markdown(root / "table1_single_seed.md", table_rows, status)


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    columns = [
        "method_id", "method", "type", "seed", "params_millions",
        "iid_r2", "iid_rmse", "iid_outperformance", "iid_ens",
        "ood_r2", "ood_rmse", "ood_outperformance", "ood_ens",
        "iid_ens_adapter_status", "ood_ens_adapter_status",
        "ens_ready_for_frozen_column",
    ]
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def _write_markdown(
    path: Path,
    rows: list[Mapping[str, Any]],
    status: Mapping[str, Any],
) -> None:
    lines = [
        "# Internal raw EarthNet2021x IID/OOD diagnostic bundle",
        "",
        f"Status: {'paper-ready' if status['paper_ready'] else 'partial/provisional'}.",
        "This is not the formal GreenEarthNet CVPR-2024 OOD-t chopped Table 1.",
        "",
    ]
    if status["warning"]:
        lines.extend([f"> Warning: {status['warning']}", ""])
    if status["required_rows_missing"]:
        lines.extend([
            "Missing core rows: " + ", ".join(status["required_rows_missing"]),
            "",
        ])
    lines.extend(
        [
            "| Method | Type | IID R² ↑ | IID RMSE ↓ | IID Outperf ↑ | OOD R² ↑ | OOD RMSE ↓ | ENS (IID) ↑ | Params |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        seed_mark = f" †seed={row['seed']}" if row["seed"] is not None else ""
        lines.append(
            "| {method}{seed} | {kind} | {iid_r2} | {iid_rmse} | {iid_out} | "
            "{ood_r2} | {ood_rmse} | {iid_ens} | {params} |".format(
                method=row["method"],
                seed=seed_mark,
                kind=row["type"],
                iid_r2=_format_metric(row["iid_r2"]),
                iid_rmse=_format_metric(row["iid_rmse"]),
                iid_out=_format_outperformance(row["iid_outperformance"]),
                ood_r2=_format_metric(row["ood_r2"]),
                ood_rmse=_format_metric(row["ood_rmse"]),
                iid_ens=_format_metric(row["iid_ens"], digits=4),
                params=_format_params(row["params_millions"]),
            )
        )
    lines.extend(
        [
            "",
            "OOD ENS is retained in table1_single_seed.csv and table1_bundle.json; the frozen manuscript layout has one ENS column, displayed here as IID ENS.",
            "R²/RMSE/Outperformance use the repository's manifest-bound GreenEarthNet-style scorer. ENS uses the strict EarthNetScore wrapper and must remain out of the manuscript until target-adapter parity is verified.",
            "",
        ]
    )
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    args = parse_args()
    root = Path(args.table_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    row = _row_from_args(args)
    _write_row_and_context(root, row, overwrite=args.overwrite_row)
    _render(root, _load_rows(root))
    print(f"table_root={root}")
    print(f"row={root / 'rows' / (args.method_id + '.json')}")
    print(f"table_markdown={root / 'table1_single_seed.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
