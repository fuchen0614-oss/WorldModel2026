from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_parity_report_binds_equal_metrics_to_oodt_manifest(tmp_path):
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
    reference = tmp_path / "official.json"
    _write(local, {"metrics": metrics})
    _write(reference, {"metrics": metrics})
    output = tmp_path / "parity.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "eval" / "verify_greenearthnet_evaluator_parity.py"),
            "--local-score", str(local),
            "--reference-score", str(reference),
            "--manifest", str(manifest),
            "--output", str(output),
        ],
        cwd=ROOT,
        check=True,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["passed"]
    assert report["evaluation_track"] == "ood-t_chopped"
    assert report["metrics"]["rmse"]["absolute_error"] == 0.0
