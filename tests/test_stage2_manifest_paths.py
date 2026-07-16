from __future__ import annotations

import json

import pytest

from data.datasets.earthnet2021 import EarthNet2021Config, _discover_npz_files
from data.earthnet_manifest import records_digest


def test_split_specific_manifest_does_not_silently_fallback_to_train():
    config = {
        "root": "/data/EarthNet2021",
        "split": "train",
        "stage2_protocol": "earthnet2021x_path_v2",
        "manifest_path": "/manifests/train_cli_override.json",
        "manifest_paths": {"train": None, "val": None},
        "require_manifest": True,
        "conditioning_stats_path": None,
        "require_conditioning_stats": False,
    }

    train = EarthNet2021Config.from_config(config, split="train")
    val = EarthNet2021Config.from_config(config, split="val")

    # A formal validation run must receive its own role=val manifest.  It may
    # not quietly reuse a generic/train path merely because it was supplied
    # elsewhere in the config.
    assert train.manifest_path is None
    assert val.manifest_path is None


def test_split_specific_manifest_overrides_direct_path_when_present():
    config = {
        "root": "/data/EarthNet2021",
        "stage2_protocol": "earthnet2021x_path_v2",
        "manifest_path": "/manifests/fallback.json",
        "manifest_paths": {
            "train": "/manifests/train_dev.json",
            "val": "/manifests/val_dev.json",
        },
        "conditioning_stats_path": None,
        "require_conditioning_stats": False,
    }

    assert EarthNet2021Config.from_config(config, split="train").manifest_path == "/manifests/train_dev.json"
    assert EarthNet2021Config.from_config(config, split="val").manifest_path == "/manifests/val_dev.json"


def test_manifest_exists_verification_can_be_disabled_for_preflight(tmp_path):
    records = [
        {
            "path": "train/34TDP/missing.nc",
            "size_bytes": 123,
            "sample_id": "missing",
        }
    ]
    manifest = {
        "schema_version": 2,
        "dataset": "earthnet2021x",
        "protocol": "earthnet2021_standard_v1",
        "split": "train-dev",
        "role": "train",
        "source_splits": ["train"],
        "hash_mode": "none",
        "num_files": len(records),
        "files": records,
        "files_sha256": records_digest(records),
    }
    manifest_path = tmp_path / "train_dev.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    base = {
        "root": str(tmp_path / "earthnet2021x"),
        "split": "train",
        "stage2_protocol": "earthnet2021x_path_v2",
        "data_format": "netcdf",
        "manifest_path": str(manifest_path),
        "require_manifest": True,
        "conditioning_stats_path": None,
        "require_conditioning_stats": False,
        "use_train_holdout": False,
    }

    strict_cfg = EarthNet2021Config.from_config(base, split="train")
    with pytest.raises(FileNotFoundError):
        _discover_npz_files(strict_cfg)

    fast_cfg = EarthNet2021Config.from_config(
        {**base, "verify_manifest_exists": False},
        split="train",
    )

    assert _discover_npz_files(fast_cfg) == [
        tmp_path / "earthnet2021x" / "train" / "34TDP" / "missing.nc"
    ]
