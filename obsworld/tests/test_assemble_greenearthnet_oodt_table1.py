from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _identity(path: Path) -> dict:
    return {
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _manifest(tmp_path: Path) -> tuple[Path, dict]:
    path = tmp_path / "oodt.json"
    payload = {
        "schema_version": 2,
        "dataset": "greenearthnet_chopped",
        "protocol": "greenearthnet_cvpr2024_chopped_v1",
        "split": "ood-t_chopped",
        "role": "ood-t_chopped",
        "source_splits": ["ood-t_chopped"],
        "hash_mode": "sha256",
        "num_files": 2,
        "files": [],
        "files_sha256": "frozen-file-list",
    }
    _write(path, payload)
    source = {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "dataset": payload["dataset"],
        "protocol": payload["protocol"],
        "split": payload["split"],
        "role": payload["role"],
        "num_files": payload["num_files"],
        "files_sha256": payload["files_sha256"],
    }
    return path, source


def _artifacts(tmp_path: Path, source: dict) -> tuple[Path, Path, Path]:
    score = tmp_path / "score" / "metrics_en21x.json"
    provenance = tmp_path / "score" / "score_provenance.json"
    parity = tmp_path / "score" / "parity.json"
    _write(
        score,
        {
            "metrics": {
                "R2": 0.5,
                "rmse": 0.1,
                "nse": 0.4,
                "biasabs": 0.05,
                "outperformance": 0.2,
                "rmse25": 0.11,
            }
        },
    )
    score_identity = _identity(score)
    _write(
        provenance,
        {
            "kind": "table1_greenearthnet_score",
            "source_manifest": source,
            "source_manifest_protocol": "greenearthnet_cvpr2024_chopped_v1",
            "evaluation_track": "ood-t_chopped",
            "num_target_files": 2,
            "prediction_validation": {
                "tracked": True,
                "manifest_protocol": "greenearthnet_cvpr2024_chopped_v1",
                "split": "ood-t_chopped",
                "source_manifest": source,
                "prediction_grid": "official_5day_20",
            },
        },
    )
    _write(
        parity,
        {
            "kind": "greenearthnet_evaluator_parity_report",
            "passed": True,
            "source_manifest": source,
            "source_manifest_protocol": "greenearthnet_cvpr2024_chopped_v1",
            "evaluation_track": "ood-t_chopped",
            "local_score": score_identity,
        },
    )
    return score, provenance, parity


def test_formal_oodt_assembler_keeps_partial_table_provisional(tmp_path):
    manifest, source = _manifest(tmp_path)
    score, provenance, parity = _artifacts(tmp_path, source)
    table = tmp_path / "table"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "eval" / "assemble_greenearthnet_oodt_table1.py"),
            "--table-root", str(table),
            "--method-id", "direct-p4",
            "--method-label", "Direct-P4",
            "--method-kind", "paired-direct",
            "--params-millions", "28.17",
            "--seed", "42",
            "--score", str(score),
            "--score-provenance", str(provenance),
            "--target-manifest", str(manifest),
            "--evaluator-parity-report", str(parity),
        ],
        cwd=ROOT,
        check=True,
    )
    bundle = json.loads((table / "table1_oodt_chopped_bundle.json").read_text(encoding="utf-8"))
    assert bundle["status"]["locally_evaluated_rows_present"] == ["direct-p4"]
    assert "contextformer" in bundle["status"]["published_reference_rows_present"]
    assert bundle["status"]["evaluator_parity_passed_for_all_rows"]
    assert not bundle["status"]["paper_ready"]
    markdown = (table / "table1_oodt_chopped.md").read_text(encoding="utf-8")
    assert "GreenEarthNet CVPR-2024 OOD-t chopped" in markdown
    assert "| Direct-P4 |" in markdown
    assert "| Contextformer | Benson et al., CVPR 2024, Table 2 |" in markdown
    assert "0.6200±0.0000" in markdown
    assert "RMSE25†" in markdown
    assert "rmse_0_5" in markdown



def test_persistence_baseline_reference_report_is_bound_to_the_same_score(tmp_path):
    manifest, source = _manifest(tmp_path)
    score, provenance, parity = _artifacts(tmp_path, source)
    baseline_report = tmp_path / "score" / "persistence_baseline_reference.json"
    _write(
        baseline_report,
        {
            "kind": "greenearthnet_baseline_reference_parity_report",
            "baseline": "persistence",
            "passed": True,
            "source_manifest": source,
            "source_manifest_protocol": "greenearthnet_cvpr2024_chopped_v1",
            "evaluation_track": "ood-t_chopped",
            "local_score": _identity(score),
        },
    )
    table = tmp_path / "table"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "eval" / "assemble_greenearthnet_oodt_table1.py"),
            "--table-root", str(table),
            "--method-id", "persistence",
            "--method-label", "Persistence",
            "--method-kind", "non-learning",
            "--params-millions", "0",
            "--score", str(score),
            "--score-provenance", str(provenance),
            "--target-manifest", str(manifest),
            "--evaluator-parity-report", str(parity),
            "--baseline-reference-parity-report", str(baseline_report),
        ],
        cwd=ROOT,
        check=True,
    )
    bundle = json.loads((table / "table1_oodt_chopped_bundle.json").read_text(encoding="utf-8"))
    assert bundle["rows"][0]["baseline_reference_parity"]["status"] == "passed"
    assert not bundle["status"]["baseline_reference_parity_passed_for_baselines"]
