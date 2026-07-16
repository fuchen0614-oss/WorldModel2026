from __future__ import annotations

import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "run_stage2_earthnet.sh"


def _fake_python(tmp_path: Path) -> Path:
    executable = tmp_path / "fake_python.sh"
    executable.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "count_file=\"${CAPTURE_FILE}.count\"\n"
        "count=0\n"
        "if [[ -f \"${count_file}\" ]]; then count=$(cat \"${count_file}\"); fi\n"
        "count=$((count + 1))\n"
        "printf '%s' \"${count}\" > \"${count_file}\"\n"
        "printf '%s\\n' \"$@\" > \"${CAPTURE_FILE}.${count}\"\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def _captured_args(capture: Path, index: int) -> list[str]:
    return (capture.with_name(f"{capture.name}.{index}")).read_text(
        encoding="utf-8"
    ).splitlines()


def test_launcher_propagates_formal_v2_artifacts_to_preflight_and_training(tmp_path):
    capture = tmp_path / "captured"
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHON_BIN": str(_fake_python(tmp_path)),
            "CAPTURE_FILE": str(capture),
            "CONFIG": "configs/train/stage2_earthnet_v2_direct24.yaml",
            "DATA_ROOT": "/data/EarthNet2021",
            "MAX_STEPS": "7",
            "BATCH_SIZE": "3",
            "NUM_WORKERS": "0",
            "GPUS": "1",
            "PREFLIGHT": "1",
            "PREFLIGHT_MAX_FILES": "11",
            "PREFLIGHT_SPLIT": "train",
            "PREFLIGHT_OUTPUT": "/artifacts/preflight.json",
            "CONDITIONING_STATS_PATH": "/artifacts/conditioning_stats.json",
            "MANIFEST_PATH": "/artifacts/train_dev.json",
            "VALIDATION_MANIFEST_PATH": "/artifacts/val_dev.json",
            "STAGE15_CHECKPOINT": "/checkpoints/state_bridge.pt",
            "RESUME_FROM": "/checkpoints/resume.pt",
            "CHECKPOINT_DIR": "/runs/checkpoints",
            "LOG_DIR": "/runs/logs",
        }
    )

    subprocess.run(
        ["bash", str(LAUNCHER)],
        cwd=ROOT,
        env=environment,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    preflight = _captured_args(capture, 1)
    training = _captured_args(capture, 2)

    assert preflight[0] == "scripts/preflight_stage2_earthnet.py"
    for flag, value in (
        ("--data-root", "/data/EarthNet2021"),
        ("--conditioning-stats-path", "/artifacts/conditioning_stats.json"),
        ("--manifest-path", "/artifacts/train_dev.json"),
        ("--validation-manifest-path", "/artifacts/val_dev.json"),
        ("--stage15-checkpoint", "/checkpoints/state_bridge.pt"),
        ("--resume-from", "/checkpoints/resume.pt"),
        ("--output", "/artifacts/preflight.json"),
    ):
        assert preflight[preflight.index(flag) + 1] == value
    assert "--require-manifest" in preflight

    assert training[0] == "train/train_stage2_earthnet.py"
    for flag, value in (
        ("--data-root", "/data/EarthNet2021"),
        ("--conditioning-stats-path", "/artifacts/conditioning_stats.json"),
        ("--manifest-path", "/artifacts/train_dev.json"),
        ("--validation-manifest-path", "/artifacts/val_dev.json"),
        ("--stage15-checkpoint", "/checkpoints/state_bridge.pt"),
        ("--resume-from", "/checkpoints/resume.pt"),
        ("--checkpoint-dir", "/runs/checkpoints"),
        ("--log-dir", "/runs/logs"),
    ):
        assert training[training.index(flag) + 1] == value
    assert "--require-manifest" in training


def test_launcher_supports_data_only_preflight_without_launching_training(tmp_path):
    capture = tmp_path / "captured"
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHON_BIN": str(_fake_python(tmp_path)),
            "CAPTURE_FILE": str(capture),
            "CONFIG": "configs/train/stage2_earthnet_v2_direct24.yaml",
            "DATA_ROOT": "/data/EarthNet2021",
            "GPUS": "1",
            "PREFLIGHT": "1",
            "PREFLIGHT_CHECK_MODEL": "0",
            "RUN_TRAIN": "0",
            "CONDITIONING_STATS_PATH": "/artifacts/conditioning_stats.json",
            "MANIFEST_PATH": "/artifacts/train_dev.json",
            "VALIDATION_MANIFEST_PATH": "/artifacts/val_dev.json",
        }
    )

    completed = subprocess.run(
        ["bash", str(LAUNCHER)],
        cwd=ROOT,
        env=environment,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert "Preflight-only mode complete" in completed.stdout
    assert _captured_args(capture, 1)[0] == "scripts/preflight_stage2_earthnet.py"
    assert not (capture.with_name(f"{capture.name}.2")).exists()
