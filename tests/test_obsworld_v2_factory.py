from __future__ import annotations

import pytest


torch = pytest.importorskip("torch")

from data.stage2_contract import model_input_view
from models.dynamics.obsworld_factory import create_obsworld_v2_model
from models.dynamics.partition_consistency import PartitionConsistencyLoss
from models.losses.earthnet_forecasting import EarthNetForecastLoss


def _tiny_config() -> dict:
    return {
        "data": {"stage2_protocol": "earthnet2021x_path_v2"},
        "model": {
            "family": "obsworld_stage2_v2",
            "forecast_mode": "direct_path_24d",
            "driver_protocol": "full24",
            "future_start_index": 10,
            "target_steps": 20,
            "require_stage15_checkpoint": False,
            "use_phi_encoder": True,
            "conditions": {"use_D": True, "use_G": True, "use_h": True},
            "encoder": {
                "type": "MultiModalViTEncoderFiLM",
                "from_checkpoint": None,
                "freeze": False,
                "img_size": 32,
                "s1_channels": 2,
                "s2_channels": 12,
                "patch_size": 16,
                "embed_dim": 32,
                "depth": 1,
                "num_heads": 4,
                "mlp_ratio": 2.0,
                "dropout": 0.0,
                "phi_dim": 32,
                "use_film": True,
                "use_cross_attention": False,
                "film_start_layer": 0,
            },
            "phi_encoder": {
                "type": "PureImagingConditionEncoder",
                "embed_dim": 32,
                "sun_dim": 8,
                "sar_geom_dim": 8,
                "dropout": 0.0,
                "condition_dropout": 0.0,
                "use_sar_geometry": True,
            },
            "state_projector": {
                "type": "SpatialStateProjector",
                "in_dim": 32,
                "state_dim": 16,
                "hidden_dim": 32,
            },
            "band_adapter": {
                "type": "EarthNetInputAdapter",
                "in_channels": 4,
                "out_channels": 12,
                "hidden_channels": 16,
                "mode": "linear",
                "source_to_canonical": [1, 2, 3, 8],
            },
            "context_aggregator": {
                "type": "ContextStateAggregator",
                "state_dim": 16,
                "hidden_dim": 32,
                "dropout": 0.0,
                "max_context_frames": 10,
                "min_token_clear_fraction": 0.25,
                "zero_unobserved_tokens": True,
            },
            "interval_driver_encoder": {
                "type": "IntervalDriverEncoder",
                "input_dim": 24,
                "calendar_dim": 2,
                "token_dim": 16,
                "hidden_dim": 32,
                "out_dim": 8,
                "num_layers": 1,
                "num_heads": 4,
                "dropout": 0.0,
                "max_segment_length": 20,
            },
            "horizon_encoder": {
                "type": "HorizonEncoder",
                "out_dim": 8,
                "hidden_dim": 16,
                "max_h_days": 100.0,
            },
            "geo_tokenizer": {
                "type": "GeoTokenizer",
                "in_channels": 1,
                "geo_dim": 4,
                "img_size": 16,
                "patch_size": 8,
            },
            "dynamics": {
                "type": "StateDynamicsModule",
                "latent_dim": 16,
                "dynamics_type": "mlp",
                "driver_dim": 8,
                "geo_dim": 4,
                "time_dim": 8,
                "hidden_dim": 32,
                "num_layers": 1,
                "num_heads": 4,
                "dropout": 0.0,
            },
            "decoder": {
                "type": "EarthNetObservationDecoder",
                "in_dim": 16,
                "out_channels": 4,
                "img_size": 16,
                "patch_size": 8,
                "depth": 1,
                "num_heads": 4,
                "decoder_embed_dim": 32,
                "mlp_ratio": 2.0,
                "dropout": 0.0,
                "decoder_mode": "transformer",
                "predict_logvar": False,
                "output_activation": "sigmoid",
            },
        },
    }


def _batch() -> dict:
    batch_size = 1
    delta_t = torch.full((batch_size, 30), 5.0)
    return {
        "x_context": torch.rand(batch_size, 10, 4, 32, 32),
        "context_mask": torch.ones(batch_size, 10, 32, 32),
        "D_path": torch.randn(batch_size, 30, 24),
        "D_mask": torch.ones(batch_size, 30, 24),
        "C_path": torch.randn(batch_size, 30, 2),
        "delta_t_path": delta_t,
        "G": torch.rand(batch_size, 1, 16, 16),
        "G_mask": torch.ones(batch_size, 1, 16, 16),
        "h": torch.arange(5, 101, 5).repeat(batch_size, 1).float(),
        "x_target": torch.rand(batch_size, 20, 4, 16, 16),
        "target_mask": torch.ones(batch_size, 20, 16, 16),
    }


def test_factory_direct24_forward_and_backward_uses_v2_target_geometry():
    torch.manual_seed(2)
    model = create_obsworld_v2_model(_tiny_config()).train()
    batch = _batch()
    output = model(model_input_view(batch), selected_steps=[0, 9, 19])

    assert output["pred"].shape == (1, 3, 4, 16, 16)
    assert output["z_pred"].shape == (1, 3, 4, 16)
    assert output["step_indices"].tolist() == [0, 9, 19]
    indices = output["step_indices"]
    target = batch["x_target"].index_select(1, indices)
    mask = batch["target_mask"].index_select(1, indices)
    loss = EarthNetForecastLoss(
        red_index=2,
        nir_index=3,
        w_latent=0.0,
        w_delta=0.0,
        w_smooth=0.0,
    )(output["pred"], target, mask)["total"]
    loss.backward()

    assert torch.isfinite(loss)
    assert model.transition.state_dynamics.output_proj.weight.grad is not None
    assert model.core.decoder.decoder.decoder_pred.weight.grad is not None


def test_factory_rejects_nonformal_direct24_dimensions():
    config = _tiny_config()
    config["model"]["decoder"]["patch_size"] = 4
    with pytest.raises(ValueError, match="token count"):
        create_obsworld_v2_model(config)


def test_factory_builds_shared_open_loop_rollout_wrapper():
    config = _tiny_config()
    config["model"]["forecast_mode"] = "rollout_t5_24d"
    model = create_obsworld_v2_model(config).eval()
    output = model(model_input_view(_batch()), selected_steps=[0, 1], max_rollout_steps=2)

    assert model.forecast_mode == "rollout_t5_24d"
    assert output["z_rollout"].shape == (1, 2, 4, 16)
    assert output["pred"].shape == (1, 2, 4, 16, 16)


def test_factory_builds_partition_wrapper_without_new_dynamics_parameters():
    config = _tiny_config()
    config["model"]["forecast_mode"] = "obsworld_partition_24d"
    model = create_obsworld_v2_model(config).eval()
    output = model(
        model_input_view(_batch()),
        selected_steps=[0, 1],
        max_rollout_steps=2,
        partition_start=0,
    )

    assert model.forecast_mode == "obsworld_partition_24d"
    assert output["partition"]["endpoint_index"].item() == 1
    assert output["partition"]["pred_direct"].shape == (1, 4, 16, 16)
    assert output["partition"]["pred_composed"].shape == (1, 4, 16, 16)


def test_partition_branch_backpropagates_through_shared_transition_and_decoder():
    config = _tiny_config()
    config["model"]["forecast_mode"] = "obsworld_partition_24d"
    model = create_obsworld_v2_model(config).train()
    batch = _batch()
    output = model(
        model_input_view(batch),
        selected_steps=[0, 1],
        max_rollout_steps=2,
        partition_start=0,
    )
    partition = output["partition"]
    loss = PartitionConsistencyLoss(red_index=2, nir_index=3)(
        z_direct=partition["z_direct"],
        z_composed=partition["z_composed"],
        pred_direct=partition["pred_direct"],
        pred_composed=partition["pred_composed"],
        target=batch["x_target"][:, 1],
        target_mask=batch["target_mask"][:, 1],
        state_mask=partition["state_valid_mask"],
    )["total"]
    loss.backward()

    assert torch.isfinite(loss)
    assert model.transition.state_dynamics.output_proj.weight.grad is not None
    assert model.core.decoder.decoder.decoder_pred.weight.grad is not None
