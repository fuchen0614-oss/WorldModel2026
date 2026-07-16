from __future__ import annotations

import json

from data.earthnet_manifest import load_manifest_files
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
