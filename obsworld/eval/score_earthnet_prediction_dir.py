#!/usr/bin/env python
"""Score an exported EarthNet2021 prediction directory with the official toolkit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.earthnet_standard_metrics import ensure_earthnet_ssim_compat
from eval.stage2_evaluation_provenance import (
    json_safe,
    output_file_record,
    prediction_records_digest,
    write_evaluation_sidecar,
)
from train.stage2_provenance import (
    canonical_json_sha256,
    file_identity,
    git_identity,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prediction-dir", required=True)
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--workers", type=int, default=-1)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--prediction-manifest",
        default=None,
        help="Defaults to <prediction-dir>/prediction_manifest.json.",
    )
    parser.add_argument(
        "--allow-untracked-predictions",
        action="store_true",
        help="Allow legacy predictions without a manifest; provenance will say untracked.",
    )
    parser.add_argument(
        "--allow-extra-predictions",
        action="store_true",
        help="Allow NPZ files not listed in the prediction manifest (not for formal scores).",
    )
    args = parser.parse_args()

    prediction_root = Path(args.prediction_dir).expanduser().resolve()
    target_root = Path(args.target_dir).expanduser().resolve()
    manifest_path = (
        Path(args.prediction_manifest).expanduser().resolve()
        if args.prediction_manifest
        else prediction_root / "prediction_manifest.json"
    )
    prediction_validation = _validate_prediction_manifest(
        prediction_root,
        manifest_path,
        allow_untracked=args.allow_untracked_predictions,
        allow_extra=args.allow_extra_predictions,
    )

    try:
        import earthnet as en
        from earthnet.parallel_score import EarthNetScore
    except ImportError as exc:
        raise ImportError(
            "Install the official scorer first: pip install earthnet==0.3.9"
        ) from exc
    ensure_earthnet_ssim_compat(en)

    output = Path(args.output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    data_path = output / "individual_scores.json"
    ens_path = output / "earthnet_score.json"
    EarthNetScore.get_ENS(
        str(prediction_root),
        str(target_root),
        n_workers=args.workers,
        data_output_file=str(data_path),
        ens_output_file=str(ens_path),
    )
    with ens_path.open("r", encoding="utf-8") as handle:
        result = json.load(handle)
    provenance = {
        "schema_version": 1,
        "kind": "stage2_official_earthnet_score",
        "evaluator": "earthnet.parallel_score.EarthNetScore.get_ENS",
        "workers": int(args.workers),
        "prediction_validation": prediction_validation,
        "target_directory": _directory_inventory(target_root),
        "score_outputs": {
            "individual_scores": file_identity(data_path, required=True),
            "earthnet_score": file_identity(ens_path, required=True),
        },
        "git": git_identity(),
    }
    write_evaluation_sidecar(output / "score_provenance.json", provenance)
    print(json.dumps(json_safe(result), indent=2, ensure_ascii=False, allow_nan=False))
    print(f"score_provenance={output / 'score_provenance.json'}")


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid prediction manifest JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"Prediction manifest must be a JSON object: {path}")
    return payload


def _validate_prediction_manifest(
    prediction_root: Path,
    manifest_path: Path,
    *,
    allow_untracked: bool,
    allow_extra: bool,
) -> dict[str, Any]:
    """Verify that EarthNetScore sees exactly one checkpoint's prediction set."""

    actual = {
        path.relative_to(prediction_root).as_posix()
        for path in prediction_root.rglob("*.npz")
        if path.is_file()
    }
    if not manifest_path.is_file():
        if not allow_untracked:
            raise FileNotFoundError(
                f"Formal scoring requires prediction_manifest.json, missing: {manifest_path}. "
                "Pass --allow-untracked-predictions only for a clearly labeled legacy score."
            )
        return {
            "tracked": False,
            "prediction_dir": str(prediction_root),
            "num_npz_files": len(actual),
        }

    manifest = _load_json_object(manifest_path)
    files = manifest.get("files")
    hash_mode = manifest.get("hash_mode")
    if not isinstance(files, list) or hash_mode not in {"none", "sha256"}:
        raise ValueError("Prediction manifest has no valid files/hash_mode contract")
    expected: set[str] = set()
    records: list[Mapping[str, Any]] = []
    for record in files:
        if not isinstance(record, Mapping) or not isinstance(record.get("path"), str):
            raise ValueError("Prediction manifest contains an invalid output record")
        relative = str(record["path"])
        if relative in expected:
            raise ValueError(f"Prediction manifest lists duplicate output {relative!r}")
        expected.add(relative)
        records.append(record)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or (extra and not allow_extra):
        details = []
        if missing:
            details.append(f"missing={missing[:5]}")
        if extra:
            details.append(f"extra={extra[:5]}")
        raise ValueError(
            "Prediction directory does not match its frozen manifest; refusing "
            "to score a mixed/incomplete export (" + "; ".join(details) + ")"
        )
    observed_records: list[dict[str, Any]] = []
    for record in records:
        source = prediction_root / str(record["path"])
        observed = output_file_record(source, root=prediction_root, hash_mode=hash_mode)
        for key in ("size_bytes", "sha256"):
            if key in record and observed.get(key) != record.get(key):
                raise ValueError(
                    f"Prediction content no longer matches manifest: {record['path']}"
                )
        observed["sample_id"] = record.get("sample_id")
        observed_records.append(observed)
    observed_digest = prediction_records_digest(observed_records)
    if manifest.get("files_sha256") != observed_digest:
        raise ValueError("Prediction manifest files_sha256 does not match current outputs")
    provenance = manifest.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValueError("Prediction manifest has no valid provenance object")
    return {
        "tracked": True,
        "manifest": file_identity(manifest_path, required=True),
        "split": manifest.get("split"),
        "num_predictions": len(records),
        "files_sha256": observed_digest,
        "extra_predictions_allowed": bool(extra and allow_extra),
        "checkpoint": provenance.get("checkpoint"),
        "contract_verification": provenance.get("contract_verification"),
    }


def _directory_inventory(root: Path) -> dict[str, Any]:
    """Record target layout without hashing every large reference cube."""

    files = sorted(path for path in root.rglob("*") if path.is_file())
    records = [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": int(path.stat().st_size),
        }
        for path in files
    ]
    return {
        "root": str(root),
        "num_files": len(records),
        "files_sha256": canonical_json_sha256(records),
    }


if __name__ == "__main__":
    main()
