from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_baseline_reference_report_binds_public_persistence_metrics(tmp_path):
    manifest = tmp_path / "oodt.json"
    _write(
        manifest,
        {
            "schema_version": 2,
            "dataset": "greenearthnet_chopped",
            "protocol": "greenearthnet_cvpr2024_chopped_v1",
            "split": "ood-t_chopped",
            "role": "ood-t_chopped",
            "source_splits": ["ood-t_chopped"],
            "hash_mode": "sha256",
            "num_files": 1,
            "files": [],
            "files_sha256": "frozen-files",
        },
    )
    metrics = {"R2": 0.5, "rmse": 0.1, "nse": 0.4, "biasabs": 0.02, "rmse25": 0.11}
    local = tmp_path / "local.json"
    reference = tmp_path / "public_persistence.json"
    _write(local, {"metrics": metrics})
    _write(reference, {"metrics": metrics})
    output = tmp_path / "baseline_reference.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "eval" / "verify_greenearthnet_baseline_reference.py"),
            "--baseline", "persistence",
            "--local-score", str(local),
            "--reference-score", str(reference),
            "--manifest", str(manifest),
            "--reference-command", "python model_pixelwise/persistence.py && python eval.py",
            "--output", str(output),
        ],
        cwd=ROOT,
        check=True,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["passed"]
    assert report["baseline"] == "persistence"
    assert report["metrics"]["rmse"]["absolute_error"] == 0.0
