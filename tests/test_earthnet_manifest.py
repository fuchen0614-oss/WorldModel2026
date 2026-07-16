from __future__ import annotations

import json

import pytest

from data.earthnet_manifest import (
    DATASET_ID,
    PROTOCOL_ID,
    build_manifest,
    build_manifest_from_paths,
    load_manifest_files,
    write_manifest,
)


def _touch(path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def test_manifest_is_relocatable_and_physical_ood_is_isolated(tmp_path):
    root = tmp_path / "EarthNet2021" / "earthnet2021x"
    train = root / "train" / "32ABC" / "train_cube.nc"
    ood = root / "ood" / "32DEF" / "ood_cube.nc"
    _touch(train, b"train")
    _touch(ood, b"ood")

    manifest = build_manifest(tmp_path / "EarthNet2021", "ood")
    assert manifest["num_files"] == 1
    assert manifest["dataset"] == DATASET_ID
    assert manifest["protocol"] == PROTOCOL_ID
    assert manifest["role"] == "ood"
    assert manifest["files"][0]["path"].endswith("ood_cube.nc")
    assert "train_cube.nc" not in json.dumps(manifest)

    path = write_manifest(manifest, tmp_path / "manifests" / "ood.json")
    loaded = load_manifest_files(
        path,
        tmp_path / "EarthNet2021",
        expected_split="ood",
        verify_sizes=True,
    )
    assert loaded == [ood.resolve()]

    with pytest.raises(ValueError, match="Unknown EarthNet split"):
        build_manifest(tmp_path / "EarthNet2021", "ood-t")

    with pytest.raises(ValueError, match="Unsupported EarthNet2021 manifest role"):
        build_manifest_from_paths(
            tmp_path / "EarthNet2021",
            "old-subtrack",
            [ood],
            role="ood-t",
            source_splits=("ood",),
        )


def test_manifest_rejects_path_traversal(tmp_path):
    root = tmp_path / "earthnet2021x"
    _touch(root / "train" / "cube.nc", b"cube")
    manifest = build_manifest(root, "train")
    manifest["files"][0]["path"] = "../outside.nc"
    # Keep the original digest deliberately: tampering must be detected before
    # an unsafe path is ever opened.
    path = write_manifest(manifest, tmp_path / "bad.json")
    with pytest.raises(ValueError, match="digest"):
        load_manifest_files(path, root, expected_split="train")
