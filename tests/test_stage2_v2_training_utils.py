from __future__ import annotations

import pytest


torch = pytest.importorskip("torch")

from data.datasets.earthnet2021 import EarthNet2021Config
from train.train_stage2_earthnet import (
    Stage2PerformanceWindow,
    format_stage2_training_progress,
    move_batch_to_device,
    partition_supervision_for_output,
    prepare_stage2_batch_for_model,
    select_v2_horizon_indices,
    stage2_supervision_for_output,
)


def test_move_batch_to_device_recurses_through_nested_values():
    nested = {
        "top": torch.ones(1),
        "phi": {"nested": torch.ones(2)},
        "items": [torch.ones(3), {"still_nested": torch.ones(4)}],
        "meta": ["keep-this-string"],
    }
    moved = move_batch_to_device(nested, torch.device("cpu"))
    assert moved["top"].device.type == "cpu"
    assert moved["phi"]["nested"].device.type == "cpu"
    assert moved["items"][1]["still_nested"].device.type == "cpu"
    assert moved["meta"] == ["keep-this-string"]


def test_v2_horizon_selection_is_sorted_unique_and_keeps_long_range():
    torch.manual_seed(7)
    steps = select_v2_horizon_indices(20, 6, device=torch.device("cpu"))
    assert steps is not None
    assert steps.shape == (6,)
    assert steps.tolist() == sorted(set(steps.tolist()))
    assert any(value < 7 for value in steps.tolist())
    assert any(value >= 13 for value in steps.tolist())


def test_v2_supervision_is_sliced_only_after_model_output():
    batch = {
        "x_target": torch.arange(20).view(1, 20, 1, 1, 1).float(),
        "target_mask": torch.ones(1, 20, 1, 1),
        "h": torch.arange(5, 101, 5).view(1, 20).float(),
    }
    output = {
        "pred": torch.zeros(1, 3, 1, 1, 1),
        "step_indices": torch.tensor([0, 7, 19]),
    }
    supervision = stage2_supervision_for_output(batch, output)
    assert supervision["target"].flatten().tolist() == [0.0, 7.0, 19.0]
    assert supervision["horizons"].flatten().tolist() == [5.0, 40.0, 100.0]


def test_partition_terminal_supervision_stays_outside_model_output():
    batch = {
        "x_target": torch.arange(20).view(1, 20, 1, 1, 1).float(),
        "target_mask": torch.ones(1, 20, 1, 1),
    }
    terminal = partition_supervision_for_output(
        batch,
        {"endpoint_index": torch.tensor(11)},
    )

    assert terminal["endpoint_index"].tolist() == [11]
    assert terminal["target"].flatten().tolist() == [11.0]


def test_stage2_progress_line_reports_losses_and_pipeline_timing():
    window = Stage2PerformanceWindow(data_wait_s=1.0, local_sample_count=16, optimizer_updates=2)
    performance = window.summarize(device=torch.device("cpu"), world_size=1)
    line = format_stage2_training_progress(
        step=20,
        max_steps=100,
        epoch=3,
        losses={"total": 1.25, "obs": 1.0, "ndvi": 0.5},
        learning_rates=[1e-4],
        performance=performance,
    )

    assert "train step=20/100 epoch=4" in line
    assert "loss=1.25000" in line
    assert "data=0.500s" in line
    assert "throughput=" in line


def test_trainer_prepares_deferred_context_at_model_geometry():
    data_cfg = EarthNet2021Config(
        root=".",
        stage2_protocol="earthnet2021x_path_v2",
        model_img_size=16,
        context_img_size=16,
        defer_context_resize_to_device=True,
    )
    raw_batch = {
        "x_context": torch.ones(2, 10, 4, 8, 8),
        "context_mask": torch.ones(2, 10, 8, 8),
    }

    prepared = prepare_stage2_batch_for_model(raw_batch, data_cfg)

    assert tuple(prepared["x_context"].shape) == (2, 10, 4, 16, 16)
    assert tuple(prepared["context_mask"].shape) == (2, 10, 16, 16)
    assert tuple(raw_batch["x_context"].shape) == (2, 10, 4, 8, 8)
