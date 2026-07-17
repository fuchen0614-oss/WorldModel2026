from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
CLEANUP = ROOT / "scripts" / "cleanup_stage2_earthnet_local_staged.sh"
LAUNCHER = ROOT / "scripts" / "run_stage2_earthnet_local_staged.sh"
MARKER_NAME = ".obsworld_stage2_local_stage_v1"
MARKER_SCHEMA = "schema=obsworld-stage2-local-stage-v1\n"


def _marked_stage_root(tmp_path: Path) -> Path:
    # The cleanup contract intentionally accepts only /tmp paths.  pytest's
    # tmp_path may live elsewhere, so make a unique, private temporary root.
    root = Path("/tmp") / f"obsworld_stage2_cleanup_test_{tmp_path.name}"
    root.mkdir(parents=True, exist_ok=False)
    (root / MARKER_NAME).write_text(MARKER_SCHEMA, encoding="utf-8")
    (root / "payload.txt").write_text("temporary EarthNet data", encoding="utf-8")
    return root


def test_stage2_local_staging_scripts_have_valid_bash_syntax():
    for script in (CLEANUP, LAUNCHER):
        subprocess.run(["bash", "-n", str(script)], check=True)


def test_cleanup_removes_only_a_marked_tmp_stage_root(tmp_path):
    stage_root = _marked_stage_root(tmp_path)
    completed = subprocess.run(
        ["bash", str(CLEANUP), "--stage-root", str(stage_root), "--force"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert "SUCCESS" in completed.stdout
    assert not stage_root.exists()


def test_cleanup_refuses_an_unmarked_tmp_directory(tmp_path):
    stage_root = Path("/tmp") / f"obsworld_stage2_unmarked_test_{tmp_path.name}"
    stage_root.mkdir(parents=True, exist_ok=False)
    (stage_root / "must_survive.txt").write_text("not a staging root", encoding="utf-8")
    try:
        completed = subprocess.run(
            ["bash", str(CLEANUP), "--stage-root", str(stage_root), "--force"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert completed.returncode != 0
        assert (stage_root / "must_survive.txt").exists()
    finally:
        subprocess.run(["rm", "-rf", "--", str(stage_root)], check=True)


def test_launcher_exposes_lifecycle_cleanup_guards():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "trap on_exit EXIT" in text
    assert "trap 'on_signal INT 130' INT" in text
    assert "trap 'on_signal TERM 143' TERM" in text
    assert "trap 'on_signal HUP 129' HUP" in text
    assert "cleanup_stage2_earthnet_local_staged.sh" in text
    assert "LOCAL_STAGE_ROOT must be below /tmp" in text
    assert "launcher initialized" in text


def _fake_earthnet_source(tmp_path: Path) -> Path:
    source_parent = tmp_path / "shared" / "EarthNet2021"
    dataset = source_parent / "earthnet2021x"
    for split in ("train", "iid", "ood", "extreme", "seasonal"):
        cube = dataset / split / "tile"
        cube.mkdir(parents=True, exist_ok=True)
        (cube / f"{split}.nc").write_bytes(b"test NetCDF payload")
    return source_parent


def _fake_runner(tmp_path: Path) -> Path:
    runner = tmp_path / "fake_stage2_runner.sh"
    runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "test -d \"${DATA_ROOT}/earthnet2021x/train\"\n"
        "printf '%s\\n' \"${DATA_ROOT}\" > \"${CAPTURE_FILE}\"\n"
        "touch \"${RUNNER_STARTED}\"\n"
        "sleep \"${FAKE_SLEEP_SECONDS:-0}\"\n",
        encoding="utf-8",
    )
    runner.chmod(0o755)
    return runner


def _fake_rsync(tmp_path: Path) -> Path:
    rsync = tmp_path / "fake_rsync.sh"
    rsync.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "touch \"${STAGING_STARTED}\"\n"
        "sleep 30\n",
        encoding="utf-8",
    )
    rsync.chmod(0o755)
    return rsync


def _launcher_environment(tmp_path: Path, stage_root: Path, runner: Path) -> dict[str, str]:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    stats = artifacts / "stats.json"
    train_manifest = artifacts / "train.json"
    val_manifest = artifacts / "val.json"
    checkpoint = artifacts / "stage15.pt"
    for path in (stats, train_manifest, val_manifest, checkpoint):
        path.write_text("non-empty", encoding="utf-8")

    environment = os.environ.copy()
    environment.update(
        {
            "SOURCE_DATA_ROOT": str(_fake_earthnet_source(tmp_path)),
            "LOCAL_STAGE_ROOT": str(stage_root),
            "CONDITIONING_STATS_PATH": str(stats),
            "MANIFEST_PATH": str(train_manifest),
            "VALIDATION_MANIFEST_PATH": str(val_manifest),
            "STAGE15_CHECKPOINT": str(checkpoint),
            "CHECKPOINT_DIR": str(tmp_path / "checkpoints"),
            "LOG_DIR": str(tmp_path / "logs"),
            "STAGE2_RUNNER": str(runner),
            "CAPTURE_FILE": str(tmp_path / "captured_data_root.txt"),
            "RUNNER_STARTED": str(tmp_path / "runner_started"),
            "MIN_LOCAL_FREE_GB": "1",
            "RUN_ID": "pytest-local-stage",
        }
    )
    return environment


def test_launcher_stages_uses_local_data_and_cleans_after_success(tmp_path):
    stage_root = Path("/tmp") / f"obsworld_stage2_launcher_test_{tmp_path.name}"
    runner = _fake_runner(tmp_path)
    environment = _launcher_environment(tmp_path, stage_root, runner)
    try:
        subprocess.run(
            ["bash", str(LAUNCHER)],
            cwd=ROOT,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        assert (tmp_path / "captured_data_root.txt").read_text(encoding="utf-8").strip() == str(
            stage_root / "EarthNet2021"
        )
        assert not stage_root.exists()
        lifecycle = (tmp_path / "logs" / "local_stage_lifecycle.log").read_text(
            encoding="utf-8"
        )
        assert "cleanup SUCCESS" in lifecycle
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)
        Path(f"{stage_root}.lock").unlink(missing_ok=True)


def test_launcher_cleans_after_term_signal(tmp_path):
    stage_root = Path("/tmp") / f"obsworld_stage2_term_test_{tmp_path.name}"
    runner = _fake_runner(tmp_path)
    environment = _launcher_environment(tmp_path, stage_root, runner)
    environment["FAKE_SLEEP_SECONDS"] = "30"
    process = subprocess.Popen(
        ["bash", str(LAUNCHER)],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        started = Path(environment["RUNNER_STARTED"])
        deadline = time.monotonic() + 20
        while not started.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert started.exists(), process.communicate(timeout=5)

        active_cleanup = subprocess.run(
            ["bash", str(CLEANUP), "--stage-root", str(stage_root), "--force"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert active_cleanup.returncode != 0
        assert stage_root.exists()

        process.terminate()
        process.communicate(timeout=20)
        assert process.returncode == 143
        assert not stage_root.exists()
        lifecycle = (tmp_path / "logs" / "local_stage_lifecycle.log").read_text(
            encoding="utf-8"
        )
        assert "received TERM" in lifecycle
        assert "cleanup SUCCESS" in lifecycle
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)
        shutil.rmtree(stage_root, ignore_errors=True)
        Path(f"{stage_root}.lock").unlink(missing_ok=True)


def test_launcher_cleans_after_term_during_rsync_staging(tmp_path):
    stage_root = Path("/tmp") / f"obsworld_stage2_rsync_term_test_{tmp_path.name}"
    runner = _fake_runner(tmp_path)
    environment = _launcher_environment(tmp_path, stage_root, runner)
    environment["RSYNC_BIN"] = str(_fake_rsync(tmp_path))
    environment["STAGING_STARTED"] = str(tmp_path / "staging_started")
    process = subprocess.Popen(
        ["bash", str(LAUNCHER)],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        started = Path(environment["STAGING_STARTED"])
        deadline = time.monotonic() + 20
        while not started.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert started.exists(), process.communicate(timeout=5)

        process.terminate()
        process.communicate(timeout=20)
        assert process.returncode == 143
        assert not stage_root.exists()
        lifecycle = (tmp_path / "logs" / "local_stage_lifecycle.log").read_text(
            encoding="utf-8"
        )
        assert "rsync staging process group" in lifecycle
        assert "cleanup SUCCESS" in lifecycle
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)
        shutil.rmtree(stage_root, ignore_errors=True)
        Path(f"{stage_root}.lock").unlink(missing_ok=True)
