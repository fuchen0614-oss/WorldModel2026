from __future__ import annotations

from pathlib import Path

import pytest

from eval.stage2_evaluation_provenance import (
    json_safe,
    output_file_record,
    prediction_records_digest,
    verify_checkpoint_contract,
)


def _config(*, forecast_mode: str = "direct_path_24d") -> dict:
    return {
        "protocol": {"schema_version": 2},
        "data": {
            "root": "/relocated/EarthNet2021",
            "split": "iid",
            "dataset_protocol": "earthnet2021_standard_v1",
            "evaluation_protocol": "earthnet2021_standard_v1",
            "stage2_protocol": "earthnet2021x_path_v2",
            "context_frames": 10,
            "target_frames": 20,
            "frame_interval_days": 5,
            "netcdf_s2_offset_days": 4,
            "context_img_size": 256,
            "target_img_size": 128,
            "eval_img_size": 128,
            "geo_img_size": 128,
            "formal_dem_variable": "cop_dem",
            "band_spec": {"input_bands": ["blue", "green", "red", "nir"]},
        },
        "model": {
            "family": "obsworld_stage2_v2",
            "forecast_mode": forecast_mode,
            "driver_protocol": "full24",
            "future_start_index": 10,
            "target_steps": 20,
            "encoder": {
                "from_checkpoint": "/old/stage15.pt",
                "freeze": True,
                "embed_dim": 384,
            },
            "dynamics": {"latent_dim": 128},
        },
        "loss": {"weights": {"obs": 1.0, "ndvi": 0.5}},
    }


def test_contract_allows_relocated_root_split_and_stage15_path():
    checkpoint_config = _config()
    runtime = _config()
    runtime["data"]["root"] = "/new-mount/EarthNet2021"
    runtime["data"]["split"] = "ood"
    runtime["model"]["encoder"]["from_checkpoint"] = None
    runtime["model"]["encoder"]["freeze"] = False

    verification = verify_checkpoint_contract(
        {"config": checkpoint_config},
        runtime,
    )
    assert verification["checked"]
    assert verification["matches"]


def test_contract_rejects_changed_forecast_mode_without_explicit_override():
    with pytest.raises(ValueError, match="forecast_mode"):
        verify_checkpoint_contract(
            {"config": _config(forecast_mode="direct_path_24d")},
            _config(forecast_mode="obsworld_partition_24d"),
        )

    overridden = verify_checkpoint_contract(
        {"config": _config(forecast_mode="direct_path_24d")},
        _config(forecast_mode="obsworld_partition_24d"),
        allow_mismatch=True,
    )
    assert overridden["override_used"]
    assert not overridden["matches"]


def test_prediction_record_digest_is_stable_and_tracks_content(tmp_path):
    root = tmp_path / "predictions"
    first = root / "34TDP" / "a.npz"
    second = root / "34TDP" / "b.npz"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    record_a = output_file_record(first, root=root, hash_mode="sha256")
    record_b = output_file_record(second, root=root, hash_mode="sha256")
    assert prediction_records_digest([record_a, record_b]) == prediction_records_digest(
        [record_b, record_a]
    )
    second.write_bytes(b"changed")
    changed_b = output_file_record(second, root=root, hash_mode="sha256")
    assert prediction_records_digest([record_a, record_b]) != prediction_records_digest(
        [record_a, changed_b]
    )


def test_json_safe_preserves_integers_and_converts_nonfinite_metrics_to_null():
    assert json_safe({"count": 3, "metric": float("nan")}) == {
        "count": 3,
        "metric": None,
    }
