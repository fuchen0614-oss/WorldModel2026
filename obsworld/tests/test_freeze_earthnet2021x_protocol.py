from __future__ import annotations

import json

import pytest

from data.earthnet_manifest import load_manifest_files, write_json_atomic
from scripts.freeze_earthnet2021x_protocol import freeze_protocol


def _touch_cube(root, split: str, tile: str, start: str, end: str) -> None:
    path = root / split / tile / f"{tile}_{start}_{end}_0_1_0_1_0_1_0_1.nc"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"netcdf-placeholder")


def test_freeze_protocol_creates_explicit_development_and_test_manifests(tmp_path):
    root = tmp_path / "EarthNet2021" / "earthnet2021x"
    for tile in ("31AAA", "32BBB", "33CCC"):
        _touch_cube(root, "train", tile, "2018-05-01", "2018-09-27")
        _touch_cube(root, "train", tile, "2019-05-01", "2019-09-27")
    _touch_cube(root, "iid", "31AAA", "2019-05-01", "2019-09-27")
    _touch_cube(root, "ood", "34DDD", "2019-05-01", "2019-09-27")
    _touch_cube(root, "extreme", "35EEE", "2018-01-31", "2018-11-26")
    _touch_cube(root, "seasonal", "34DDD", "2017-05-28", "2020-04-11")

    output = tmp_path / "frozen"
    result = freeze_protocol(root, output, val_tile_count=1, seed=7)

    protocol = json.loads((output / "protocol.json").read_text())
    assert protocol["protocol"] == "earthnet2021_standard_v1"
    assert protocol["primary_test_tracks"] == ["iid", "ood"]
    assert protocol["supplementary_test_tracks"] == ["extreme", "seasonal"]
    assert "ood-t" not in json.dumps(protocol)
    assert result["validation_tiles"] == protocol["development"]["validation_tiles"]

    train_files = set(
        load_manifest_files(output / "train_dev.json", root, expected_split="train")
    )
    val_files = set(
        load_manifest_files(output / "val_dev.json", root, expected_split="val")
    )
    all_files = set(
        load_manifest_files(output / "train_all.json", root, expected_split="train")
    )
    assert train_files
    assert val_files
    assert not train_files.intersection(val_files)
    assert train_files.union(val_files) == all_files
    assert not list(output.parent.glob(f".{output.name}.staging-*"))


def test_parallel_freeze_is_byte_identical_to_single_worker(tmp_path):
    root = tmp_path / "earthnet2021x"
    for tile in ("31AAA", "32BBB", "33CCC"):
        for year in ("2018", "2019", "2020"):
            _touch_cube(root, "train", tile, f"{year}-05-01", f"{year}-09-27")
    _touch_cube(root, "iid", "31AAA", "2019-05-01", "2019-09-27")
    _touch_cube(root, "ood", "34DDD", "2019-05-01", "2019-09-27")
    _touch_cube(root, "extreme", "35EEE", "2018-01-31", "2018-11-26")
    _touch_cube(root, "seasonal", "34DDD", "2017-05-28", "2020-04-11")

    serial_output = tmp_path / "serial"
    parallel_output = tmp_path / "parallel"
    freeze_protocol(
        root,
        serial_output,
        val_tile_count=1,
        seed=7,
        workers=1,
        progress_every=0,
    )
    freeze_protocol(
        root,
        parallel_output,
        val_tile_count=1,
        seed=7,
        workers=2,
        progress_every=0,
    )

    serial_files = sorted(path.name for path in serial_output.glob("*.json"))
    parallel_files = sorted(path.name for path in parallel_output.glob("*.json"))
    assert parallel_files == serial_files
    for filename in serial_files:
        assert (parallel_output / filename).read_bytes() == (serial_output / filename).read_bytes()


def test_freeze_protocol_never_overwrites_an_existing_evidence_directory(tmp_path):
    root = tmp_path / "earthnet2021x"
    for tile in ("31AAA", "32BBB"):
        _touch_cube(root, "train", tile, "2018-05-01", "2018-09-27")
    _touch_cube(root, "iid", "31AAA", "2019-05-01", "2019-09-27")
    _touch_cube(root, "ood", "34DDD", "2019-05-01", "2019-09-27")
    _touch_cube(root, "extreme", "35EEE", "2018-01-31", "2018-11-26")
    _touch_cube(root, "seasonal", "34DDD", "2017-05-28", "2020-04-11")

    output = tmp_path / "frozen"
    freeze_protocol(root, output, val_tile_count=1, seed=7)
    before = (output / "protocol.json").read_bytes()

    with pytest.raises(FileExistsError, match="immutable evidence"):
        freeze_protocol(root, output, val_tile_count=1, seed=8)

    assert (output / "protocol.json").read_bytes() == before
    assert not list(output.parent.glob(f".{output.name}.staging-*"))


def test_freeze_protocol_rejects_an_unknown_hash_mode_before_writing(tmp_path):
    root = tmp_path / "earthnet2021x"
    root.mkdir()
    output = tmp_path / "frozen"

    with pytest.raises(ValueError, match="hash_mode"):
        freeze_protocol(root, output, hash_mode="invalid")

    assert not output.exists()
    assert not list(output.parent.glob(f".{output.name}.staging-*"))


def test_atomic_json_writer_leaves_no_temporary_file(tmp_path):
    output = tmp_path / "manifest.json"
    write_json_atomic({"schema_version": 1, "value": "完整"}, output)

    assert json.loads(output.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "value": "完整",
    }
    assert not list(tmp_path.glob(".manifest.json.*.tmp"))
