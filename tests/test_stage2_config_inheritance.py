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
    assert rollout["model"]["decoder"] == direct["model"]["decoder"]
    assert rollout["training"]["rollout_curriculum"][-1]["length"] == 20


def test_config_inheritance_rejects_cycles(tmp_path):
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text("_base_: second.yaml\nvalue: 1\n", encoding="utf-8")
    second.write_text("_base_: first.yaml\nvalue: 2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Cyclic"):
        load_config(first)
