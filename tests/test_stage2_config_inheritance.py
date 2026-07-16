from __future__ import annotations

from pathlib import Path

import pytest


pytest.importorskip("torch")

from train.train_stage2_earthnet import load_config


def test_rollout_config_inherits_matched_direct24_contract():
    root = Path(__file__).resolve().parents[1]
    direct = load_config(root / "configs/train/stage2_earthnet_v2_direct24.yaml")
    rollout = load_config(root / "configs/train/stage2_earthnet_v2_rollout24.yaml")

    assert rollout["model"]["forecast_mode"] == "rollout_t5_24d"
    assert rollout["data"] == direct["data"]
    assert rollout["data"]["evaluation_protocol"] == "earthnet2021_standard_v1"
    assert rollout["model"]["decoder"] == direct["model"]["decoder"]
    assert rollout["training"]["rollout_curriculum"][-1]["length"] == 20


def test_partition_config_inherits_the_identical_rollout_contract():
    root = Path(__file__).resolve().parents[1]
    rollout = load_config(root / "configs/train/stage2_earthnet_v2_rollout24.yaml")
    partition = load_config(root / "configs/train/stage2_earthnet_v2_partition24.yaml")

    assert partition["model"]["forecast_mode"] == "obsworld_partition_24d"
    assert partition["data"] == rollout["data"]
    assert partition["model"]["decoder"] == rollout["model"]["decoder"]
    assert partition["training"]["rollout_curriculum"] == rollout["training"]["rollout_curriculum"]
    assert partition["training"]["partition"]["enabled"] is True


def test_config_inheritance_rejects_cycles(tmp_path):
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text("_base_: second.yaml\nvalue: 1\n", encoding="utf-8")
    second.write_text("_base_: first.yaml\nvalue: 2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Cyclic"):
        load_config(first)
