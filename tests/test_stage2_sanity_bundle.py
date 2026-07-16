from __future__ import annotations

import json

import pytest

from data.earthnet_manifest import load_manifest_files
from scripts.build_stage2_sanity_bundle import build_sanity_bundle
from scripts.freeze_earthnet2021x_protocol import freeze_protocol


def _touch_cube(root, split: str, tile: str, index: int) -> None:
    start = f"2018-0{5 + index}-01"
    end = f"2018-{9 + index:02d}-27"
    path = root / split / tile / f"{tile}_{start}_{end}_0_1_0_1_0_1_0_1.nc"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"placeholder-{split}-{tile}-{index}".encode("utf-8"))


def _frozen_protocol(tmp_path):
    root = tmp_path / "EarthNet2021" / "earthnet2021x"
    for tile in ("31AAA", "32BBB", "33CCC", "34DDD"):
        for index in range(3):
            _touch_cube(root, "train", tile, index)
    _touch_cube(root, "iid", "31AAA", 0)
    _touch_cube(root, "ood", "35EEE", 0)
    _touch_cube(root, "extreme", "36FFF", 0)
    _touch_cube(root, "seasonal", "37GGG", 0)
    frozen = tmp_path / "frozen_protocol"
    freeze_protocol(root, frozen, val_tile_count=1, seed=7)
    return root, frozen


def test_sanity_bundle_is_deterministic_spatially_spread_and_explicitly_nonformal(tmp_path):
    root, frozen = _frozen_protocol(tmp_path)
    first = build_sanity_bundle(
        data_root=root,
        train_manifest_path=frozen / "train_dev.json",
        validation_manifest_path=frozen / "val_dev.json",
        output_dir=tmp_path / "sanity_a",
        train_count=5,
        validation_count=2,
        seed=19,
    )
    second = build_sanity_bundle(
        data_root=root,
        train_manifest_path=frozen / "train_dev.json",
        validation_manifest_path=frozen / "val_dev.json",
        output_dir=tmp_path / "sanity_b",
        train_count=5,
        validation_count=2,
        seed=19,
    )

    bundle = json.loads(
        (tmp_path / "sanity_a" / "bundle.json").read_text(encoding="utf-8")
    )
    assert bundle["formal_result_eligible"] is False
    assert bundle["manifests"]["train"]["num_files"] == 5
    assert bundle["manifests"]["val"]["num_files"] == 2
    assert bundle["selector"] == "tile_round_robin_sha256_v1"

    first_train = load_manifest_files(first["train_manifest_path"], root, expected_split="train")
    first_val = load_manifest_files(first["validation_manifest_path"], root, expected_split="val")
    second_train = json.loads((tmp_path / "sanity_b" / "train_sanity.json").read_text(encoding="utf-8"))
    first_train_payload = json.loads((tmp_path / "sanity_a" / "train_sanity.json").read_text(encoding="utf-8"))
    assert len(first_train) == 5
    assert len(first_val) == 2
    assert len({path.stem.split("_", 1)[0] for path in first_train}) >= 2
    assert first_train_payload["files_sha256"] == second_train["files_sha256"]
    assert first_train_payload["selection"]["kind"] == "sanity_subset_not_formal"


def test_sanity_bundle_refuses_to_overwrite_existing_debug_evidence(tmp_path):
    root, frozen = _frozen_protocol(tmp_path)
    output = tmp_path / "sanity"
    kwargs = {
        "data_root": root,
        "train_manifest_path": frozen / "train_dev.json",
        "validation_manifest_path": frozen / "val_dev.json",
        "output_dir": output,
        "train_count": 3,
        "validation_count": 2,
        "seed": 19,
    }
    build_sanity_bundle(**kwargs)
    before = (output / "bundle.json").read_bytes()
    with pytest.raises(FileExistsError, match="debug evidence"):
        build_sanity_bundle(**kwargs)
    assert (output / "bundle.json").read_bytes() == before
    assert not list(output.parent.glob(f".{output.name}.staging-*"))
