#!/usr/bin/env python
"""Score a Table 1 EarthNet NPZ export against an exact frozen target set.

This is the strict Table 1 entry point. It reuses the official
EarthNetScore.get_ENS implementation, but first verifies the prediction and
target manifests as identical, hashed NPZ path sets. This closes a gap in the
toolkit API: it can otherwise score only the overlap of two trees without
making an incomplete pairing obvious in the aggregate number.

The raw-NetCDF target adapter is deliberately not promoted to official parity
here. Its manifest carries adapter_parity_status and the table assembler only
upgrades that status after an explicit reference-target report.
"""

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
from train.stage2_provenance import file_identity, git_identity


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Strictly score one manifest-pinned Table 1 EarthNet prediction tree."
    )
    parser.add_argument("--prediction-dir", required=True)
    parser.add_argument("--prediction-manifest", required=True)
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--workers", type=int, default=-1)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--allow-untracked-predictions",
        action="store_true",
        help="Legacy escape hatch; formal Table 1 invocations must not use this.",
    )
    parser.add_argument(
        "--allow-untracked-targets",
        action="store_true",
        help="Legacy escape hatch; formal Table 1 invocations must not use this.",
    )
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


def _safe_relative(value: str, *, label: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe {label} manifest path: {value!r}")
    return path.as_posix()


def validate_manifest_tree(
    root: str | Path,
    manifest_path: str | Path,
    *,
    artifact: str,
    allow_untracked: bool = False,
    allow_extra: bool = False,
) -> dict[str, Any]:
    """Hash-verify an NPZ tree against its own exported manifest.

    The helper is public so the NPZ-to-GreenEarthNet converter can consume the
    same guarantee before changing only the file container and coordinates.
    """

    output_root = Path(root).expanduser().resolve()
    sidecar = Path(manifest_path).expanduser().resolve()
    actual = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*.npz")
        if path.is_file()
    }
    if not sidecar.is_file():
        if not allow_untracked:
            raise FileNotFoundError(
                f"Formal {artifact} validation requires a manifest: {sidecar}"
            )
        return {
            "tracked": False,
            "artifact": artifact,
            "directory": str(output_root),
            "num_npz_files": len(actual),
        }

    manifest = _load_json_object(sidecar, label=f"{artifact} manifest")
    files = manifest.get("files")
    hash_mode = manifest.get("hash_mode")
    if not isinstance(files, list) or hash_mode not in {"none", "sha256"}:
        raise ValueError(f"{artifact} manifest has no valid files/hash_mode contract")
    expected: set[str] = set()
    observed_records: list[dict[str, Any]] = []
    for record in files:
        if not isinstance(record, Mapping) or not isinstance(record.get("path"), str):
            raise ValueError(f"{artifact} manifest contains an invalid output record")
        relative = _safe_relative(str(record["path"]), label=artifact)
        if relative in expected:
            raise ValueError(f"{artifact} manifest lists duplicate output {relative!r}")
        expected.add(relative)
        observed = output_file_record(
            output_root / relative,
            root=output_root,
            hash_mode=hash_mode,
        )
        for key in ("size_bytes", "sha256"):
            if key in record and observed.get(key) != record.get(key):
                raise ValueError(
                    f"{artifact} content no longer matches manifest: {relative}"
                )
        if "sample_id" in record:
            observed["sample_id"] = record["sample_id"]
        observed_records.append(observed)

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or (extra and not allow_extra):
        details: list[str] = []
        if missing:
            details.append(f"missing={missing[:5]}")
        if extra:
            details.append(f"extra={extra[:5]}")
        raise ValueError(
            f"{artifact} directory does not match its frozen manifest "
            "(" + "; ".join(details) + ")"
        )
    observed_digest = prediction_records_digest(observed_records)
    if manifest.get("files_sha256") != observed_digest:
        raise ValueError(f"{artifact} manifest files_sha256 does not match current files")
    return {
        "tracked": True,
        "artifact": artifact,
        "manifest": file_identity(sidecar, required=True),
        "kind": manifest.get("kind"),
        "format": manifest.get("format"),
        "split": manifest.get("split"),
        "num_files": len(expected),
        "files_sha256": observed_digest,
        "paths": sorted(expected),
        "adapter_parity_status": manifest.get("adapter_parity_status"),
        "extra_files_allowed": bool(extra and allow_extra),
    }


def _validate_pairing(
    prediction_validation: Mapping[str, Any],
    target_validation: Mapping[str, Any],
) -> None:
    if not prediction_validation.get("tracked") or not target_validation.get("tracked"):
        return
    prediction_paths = prediction_validation.get("paths")
    target_paths = target_validation.get("paths")
    if not isinstance(prediction_paths, list) or not isinstance(target_paths, list):
        raise ValueError("Tracked manifests must expose their sorted output paths")
    if prediction_paths != target_paths:
        expected = set(target_paths)
        observed = set(prediction_paths)
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        details: list[str] = []
        if missing:
            details.append(f"prediction_missing={missing[:5]}")
        if extra:
            details.append(f"prediction_extra={extra[:5]}")
        raise ValueError(
            "Prediction and target manifests select different cubes "
            "(" + "; ".join(details) + ")"
        )


def main() -> int:
    args = parse_args()
    prediction_root = Path(args.prediction_dir).expanduser().resolve()
    target_root = Path(args.target_dir).expanduser().resolve()
    prediction_validation = validate_manifest_tree(
        prediction_root,
        args.prediction_manifest,
        artifact="prediction",
        allow_untracked=args.allow_untracked_predictions,
        allow_extra=args.allow_extra_predictions,
    )
    target_validation = validate_manifest_tree(
        target_root,
        args.target_manifest,
        artifact="target",
        allow_untracked=args.allow_untracked_targets,
        allow_extra=False,
    )
    _validate_pairing(prediction_validation, target_validation)
    if not prediction_validation.get("tracked") or not target_validation.get("tracked"):
        raise ValueError(
            "Table 1 scores require both prediction and target manifests. "
            "Use the legacy scorer for explicitly untracked diagnostics."
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
    result = _load_json_object(ens_path, label="EarthNetScore output")
    provenance = {
        "schema_version": 1,
        "kind": "table1_official_earthnet_score",
        "evaluator": "earthnet.parallel_score.EarthNetScore.get_ENS",
        "workers": int(args.workers),
        "prediction_validation": prediction_validation,
        "target_validation": target_validation,
        "pairing_verified": True,
        "adapter_parity_status": target_validation.get("adapter_parity_status"),
        "score_outputs": {
            "individual_scores": file_identity(data_path, required=True),
            "earthnet_score": file_identity(ens_path, required=True),
        },
        "git": git_identity(),
    }
    write_evaluation_sidecar(output / "score_provenance.json", provenance)
    print(json.dumps(json_safe(result), indent=2, ensure_ascii=False, allow_nan=False))
    print(f"score_provenance={output / 'score_provenance.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
