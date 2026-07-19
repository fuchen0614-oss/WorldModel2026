from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _identity(path: Path) -> dict:
    return {
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _target_manifest(root: Path, split: str) -> tuple[Path, dict]:
    source_manifest = {
        "path": f"/frozen/{split}.json",
        "sha256": f"{split}-source-sha",
        "dataset": "earthnet2021x",
        "protocol": "earthnet2021_standard_v1",
        "split": split,
        "role": split,
        "num_files": 2,
        "files_sha256": f"{split}-source-files",
    }
    path = root / "targets" / split / "target_manifest.json"
    payload = {
        "kind": "earthnet2021_score_target_manifest",
        "split": split,
        "num_targets": 2,
        "files_sha256": f"{split}-target-files",
        "identity": {"source_manifest": source_manifest},
    }
    _write_json(path, payload)
    return path, source_manifest


def _method_artifacts(
    root: Path,
    method_id: str,
    split: str,
    target_manifest: Path,
    source_manifest: dict,
    *,
    score: float,
    r2: float,
    rmse: float,
    outperformance: float | None,
) -> tuple[Path, Path, Path, Path]:
    target_identity = _identity(target_manifest)
    ens_score = root / "ens" / method_id / split / "earthnet_score.json"
    ens_provenance = root / "ens" / method_id / split / "score_provenance.json"
    ndvi_score = root / "ndvi" / method_id / split / "metrics_en21x.json"
    ndvi_provenance = root / "ndvi" / method_id / split / "score_provenance.json"
    _write_json(
        ens_score,
        {
            "EarthNetScore": score,
            "Value (MAD)": score + 0.1,
            "Trend (OLS)": score + 0.2,
        },
    )
    _write_json(
        ens_provenance,
        {
            "kind": "table1_official_earthnet_score",
            "pairing_verified": True,
            "target_validation": {
                "tracked": True,
                "manifest": target_identity,
                "files_sha256": f"{split}-target-files",
            },
        },
    )
    metrics = {"R2": r2, "rmse": rmse}
    if outperformance is not None:
        metrics["outperformance"] = outperformance
    _write_json(ndvi_score, {"metrics": metrics})
    _write_json(
        ndvi_provenance,
        {
            "kind": "table1_greenearthnet_score",
            "source_manifest": source_manifest,
            "num_target_files": 2,
        },
    )
    return ens_score, ens_provenance, ndvi_score, ndvi_provenance


def _run_row(
    tmp_path: Path,
    table_root: Path,
    method_id: str,
    label: str,
    kind: str,
    seed: str | None,
    *,
    outperformance: float | None,
) -> None:
    artifacts: dict[str, tuple[Path, Path, Path, Path]] = {}
    targets: dict[str, Path] = {}
    for split, score in (("iid", 0.31), ("ood", 0.22)):
        target, source = _target_manifest(tmp_path, split)
        targets[split] = target
        artifacts[split] = _method_artifacts(
            tmp_path,
            method_id,
            split,
            target,
            source,
            score=score,
            r2=0.6 if split == "iid" else 0.5,
            rmse=0.12 if split == "iid" else 0.15,
            outperformance=outperformance,
        )

    args = [
        sys.executable,
        str(ROOT / "eval" / "assemble_stage2_table1.py"),
        "--table-root", str(table_root),
        "--method-id", method_id,
        "--method-label", label,
        "--method-kind", kind,
        "--params-millions", "28.17" if method_id == "direct-p4" else "0",
    ]
    if seed is not None:
        args.extend(["--seed", seed])
    for split in ("iid", "ood"):
        ens_score, ens_provenance, ndvi_score, ndvi_provenance = artifacts[split]
        args.extend(
            [
                f"--{split}-ens-score", str(ens_score),
                f"--{split}-ens-provenance", str(ens_provenance),
                f"--{split}-ndvi-score", str(ndvi_score),
                f"--{split}-ndvi-provenance", str(ndvi_provenance),
                f"--{split}-target-manifest", str(targets[split]),
            ]
        )
    subprocess.run(args, cwd=ROOT, check=True)


def test_assembler_renders_provisional_partial_table_without_cross_manifest_mix(tmp_path):
    table_root = tmp_path / "table"
    _run_row(
        tmp_path,
        table_root,
        "climatology",
        "Climatology",
        "non-learning",
        None,
        outperformance=None,
    )
    _run_row(
        tmp_path,
        table_root,
        "direct-p4",
        "Direct-P4",
        "paired-direct",
        "42",
        outperformance=0.19,
    )

    markdown = (table_root / "table1_single_seed.md").read_text(encoding="utf-8")
    assert "partial/provisional" in markdown
    assert "raw-NetCDF target adapter" in markdown
    assert "| Climatology |" in markdown
    assert "| Direct-P4 †seed=42 |" in markdown

    with (table_root / "table1_single_seed.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["method_id"] for row in rows] == ["climatology", "direct-p4"]
    assert rows[1]["iid_ens"] == "0.31"
    assert rows[1]["ood_ens"] == "0.22"
    assert rows[0]["iid_outperformance"] == ""
