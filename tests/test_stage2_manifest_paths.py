from __future__ import annotations

from data.datasets.earthnet2021 import EarthNet2021Config


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
