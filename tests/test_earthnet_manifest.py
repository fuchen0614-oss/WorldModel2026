from __future__ import annotations

import json

import pytest

from data.earthnet_manifest import (
    build_manifest,
    load_manifest_files,
    write_manifest,
)


def _touch(path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def test_manifest_is_relocatable_and_ood_track_isolated(tmp_path):
    root = tmp_path / "EarthNet2021" / "earthnet2021x"
    train = root / "train" / "32ABC" / "train_cube.nc"
    ood_t = root / "ood" / "ood-t_chopped" / "region_t" / "t_cube.nc"
    ood_s = root / "ood" / "ood-s_chopped" / "region_s" / "s_cube.nc"
    _touch(train, b"train")
    _touch(ood_t, b"temporal")
    _touch(ood_s, b"spatial")

    manifest = build_manifest(tmp_path / "EarthNet2021", "ood-t")
    assert manifest["num_files"] == 1
    assert manifest["files"][0]["path"].endswith("t_cube.nc")
    assert "s_cube.nc" not in json.dumps(manifest)

    path = write_manifest(manifest, tmp_path / "manifests" / "ood-t.json")
    loaded = load_manifest_files(
        path,
        tmp_path / "EarthNet2021",
        expected_split="ood-t",
        verify_sizes=True,
    )
    assert loaded == [ood_t.resolve()]


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
