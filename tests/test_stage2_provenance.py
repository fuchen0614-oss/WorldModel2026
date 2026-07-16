from __future__ import annotations

import json

import pytest


torch = pytest.importorskip("torch")

from train.stage2_provenance import (
    atomic_torch_save,
    build_stage2_run_provenance,
    canonical_json_sha256,
    sha256_file,
    write_json_atomic,
)


def _formal_config() -> dict:
    return {
        "protocol": {"schema_version": 2},
        "data": {
            "root": "/data/EarthNet2021",
            "dataset_protocol": "earthnet2021_standard_v1",
            "stage2_protocol": "earthnet2021x_path_v2",
            "evaluation_protocol": "earthnet2021_standard_v1",
            "require_manifest": True,
            "batch_size": 2,
        },
        "model": {
            "forecast_mode": "obsworld_partition_24d",
            "driver_protocol": "full24",
            "require_stage15_checkpoint": True,
        },
        "training": {
            "seed": 42,
            "max_steps": 10,
            "gradient_accumulation_steps": 1,
            "horizons_per_sample": 6,
            "require_conditioning_stats": True,
            "require_full_conditioning_stats": True,
        },
    }


def test_provenance_binds_config_manifests_stats_and_initializer_bytes(tmp_path):
    train = tmp_path / "train.json"
    val = tmp_path / "val.json"
    stats = tmp_path / "stats.json"
    initializer = tmp_path / "stage15.pt"
    train.write_text(
        json.dumps(
            {
                "dataset": "earthnet2021x",
                "protocol": "earthnet2021_standard_v1",
                "split": "train-dev",
                "role": "train",
                "num_files": 3,
                "files_sha256": "train-record-digest",
            }
        ),
        encoding="utf-8",
    )
    val.write_text(
        json.dumps(
            {
                "dataset": "earthnet2021x",
                "protocol": "earthnet2021_standard_v1",
                "split": "val-dev",
                "role": "val",
                "num_files": 1,
                "files_sha256": "val-record-digest",
            }
        ),
        encoding="utf-8",
    )
    stats.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "manifest_sha256": "train-record-digest",
                "num_files": 3,
                "is_full_train": True,
                "g_variable": "cop_dem",
            }
        ),
        encoding="utf-8",
    )
    initializer.write_bytes(b"frozen-stage15")

    config = _formal_config()
    provenance = build_stage2_run_provenance(
        config,
        train_manifest_path=train,
        validation_manifest_path=val,
        conditioning_stats_path=stats,
        stage15_checkpoint_path=initializer,
        resume_checkpoint_path=None,
        parent_provenance=None,
        device=torch.device("cpu"),
        world_size=1,
        repo_root=tmp_path,
    )

    assert provenance["resolved_config_sha256"] == canonical_json_sha256(config)
    assert provenance["train_manifest"]["files_sha256"] == "train-record-digest"
    assert provenance["validation_manifest"]["role"] == "val"
    assert provenance["conditioning_stats"]["manifest_sha256"] == "train-record-digest"
    assert provenance["stage15_initializer"]["sha256"] == sha256_file(initializer)
    assert provenance["git"]["commit"] is None


def test_atomic_json_and_torch_writes_leave_no_partial_destination(tmp_path):
    json_path = tmp_path / "nested" / "run_provenance.json"
    checkpoint_path = tmp_path / "nested" / "checkpoint.pt"
    write_json_atomic(json_path, {"b": 2, "a": 1})
    atomic_torch_save({"tensor": torch.tensor([3])}, checkpoint_path)

    assert json.loads(json_path.read_text(encoding="utf-8")) == {"a": 1, "b": 2}
    assert torch.load(checkpoint_path, weights_only=False)["tensor"].tolist() == [3]
    assert not list((tmp_path / "nested").glob(".*.tmp"))
