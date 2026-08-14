from __future__ import annotations

import json

import pytest

from eval.predict_stage2_earthnet import _validate_existing_output_directory
from eval.score_earthnet_prediction_dir import _validate_prediction_manifest
from eval.stage2_evaluation_provenance import (
    output_file_record,
    prediction_records_digest,
)
from train.stage2_provenance import sha256_file


def _write_manifest(root, checkpoint, *, split="iid"):
    output = root / "34TDP" / "cube.npz"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"prediction")
    record = output_file_record(output, root=root, hash_mode="sha256")
    record["sample_id"] = "34TDP_cube"
    manifest = {
        "schema_version": 1,
        "kind": "stage2_prediction_manifest",
        "split": split,
        "hash_mode": "sha256",
        "num_predictions": 1,
        "files": [record],
        "files_sha256": prediction_records_digest([record]),
        "provenance": {
            "checkpoint": {"sha256": sha256_file(checkpoint)},
            "contract_verification": {"runtime_contract_sha256": "same-contract"},
        },
    }
    path = root / "prediction_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_scorer_rejects_extra_npz_not_listed_in_prediction_manifest(tmp_path):
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"checkpoint")
    root = tmp_path / "predictions"
    manifest = _write_manifest(root, checkpoint)

    validated = _validate_prediction_manifest(
        root,
        manifest,
        allow_untracked=False,
        allow_extra=False,
    )
    assert validated["tracked"]

    extra = root / "34TDP" / "stale.npz"
    extra.write_bytes(b"stale")
    with pytest.raises(ValueError, match="mixed/incomplete"):
        _validate_prediction_manifest(
            root,
            manifest,
            allow_untracked=False,
            allow_extra=False,
        )


def test_export_refuses_untracked_existing_prediction_files(tmp_path):
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"checkpoint")
    root = tmp_path / "predictions"
    stale = root / "34TDP" / "stale.npz"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale")

    with pytest.raises(FileExistsError, match="no prediction_manifest"):
        _validate_existing_output_directory(
            root,
            root / "prediction_manifest.json",
            checkpoint_path=str(checkpoint),
            split="iid",
            dataset_size=1,
            hash_mode="sha256",
            runtime_contract_sha256="same-contract",
            overwrite=False,
        )


def test_export_reuses_only_matching_complete_prediction_manifest(tmp_path):
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"checkpoint")
    root = tmp_path / "predictions"
    manifest = _write_manifest(root, checkpoint)

    _validate_existing_output_directory(
        root,
        manifest,
        checkpoint_path=str(checkpoint),
        split="iid",
        dataset_size=1,
        hash_mode="sha256",
        runtime_contract_sha256="same-contract",
        overwrite=False,
    )
    (root / "34TDP" / "cube.npz").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="does not match its manifest"):
        _validate_existing_output_directory(
            root,
            manifest,
            checkpoint_path=str(checkpoint),
            split="iid",
            dataset_size=1,
            hash_mode="sha256",
            runtime_contract_sha256="same-contract",
            overwrite=False,
        )
