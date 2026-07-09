import sys
from pathlib import Path

import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.adapters.earthnet_band_adapter import EarthNetInputAdapter
from models.adapters.geo_tokenizer import GeoTokenizer
from models.decoders.earthnet_observation_decoder import EarthNetObservationDecoder
from models.dynamics.context_state_aggregator import ContextStateAggregator
from models.dynamics.condition_encoders import DriverEncoder, HorizonEncoder
from models.dynamics.obsworld_stage2 import ObsWorldStage2Model
from models.dynamics.state_dynamics_module import StateDynamicsModule
from models.encoders.multimodal_vit_encoder_film import MultiModalViTEncoderFiLM
from models.encoders.pure_imaging_condition_encoder import PureImagingConditionEncoder
from models.encoders.state_projection import SpatialStateProjector
from models.losses.earthnet_forecasting import EarthNetForecastLoss
from train.train_stage2_earthnet import build_scheduler


def test_stage2_forward_and_backward():
    torch.manual_seed(0)
    encoder = MultiModalViTEncoderFiLM(
        img_size=32, s1_channels=2, s2_channels=12, patch_size=16,
        embed_dim=32, depth=1, num_heads=4, phi_dim=32, film_start_layer=0,
    )
    model = ObsWorldStage2Model(
        band_adapter=EarthNetInputAdapter(in_channels=4, out_channels=12),
        encoder=encoder,
        phi_encoder=PureImagingConditionEncoder(embed_dim=32, sun_dim=8, sar_geom_dim=8),
        state_projector=SpatialStateProjector(in_dim=32, state_dim=16, hidden_dim=32),
        context_aggregator=ContextStateAggregator(state_dim=16, hidden_dim=32),
        driver_encoder=DriverEncoder(in_dim=9, hidden_dim=16, out_dim=8),
        horizon_encoder=HorizonEncoder(out_dim=8, hidden_dim=16, max_h_days=15),
        geo_tokenizer=GeoTokenizer(in_channels=1, geo_dim=4, img_size=32, patch_size=16),
        dynamics=StateDynamicsModule(latent_dim=16, dynamics_type="mlp", driver_dim=8, geo_dim=4, time_dim=8, hidden_dim=32),
        decoder=EarthNetObservationDecoder(in_dim=16, out_channels=4, patch_size=16, img_size=32, depth=1, num_heads=4, decoder_embed_dim=32),
        max_h_days=15,
    )
    batch = {
        "x_context": torch.rand(2, 2, 4, 32, 32),
        "x_target": torch.rand(2, 3, 4, 32, 32),
        "context_mask": torch.ones(2, 2, 32, 32),
        "target_mask": torch.ones(2, 3, 32, 32),
        "D": torch.randn(2, 3, 9),
        "D_mask": torch.ones(2, 3, 9),
        "G": torch.randn(2, 1, 32, 32),
        "G_mask": torch.ones(2, 1, 32, 32),
        "h": torch.tensor([[5.0, 10.0, 15.0], [5.0, 10.0, 15.0]]),
    }
    out = model(batch)
    assert out["pred"].shape == (2, 3, 4, 32, 32)
    assert out["z_pred"].shape[:3] == (2, 3, 4)
    loss_fn = EarthNetForecastLoss(red_index=2, nir_index=3)
    assert out["z_target_mask"].shape == (2, 3, 4)
    losses = loss_fn(
        out["pred"],
        batch["x_target"],
        batch["target_mask"],
        out["z_pred"],
        out["z_target"],
        out["z_context"],
        out["z_target_mask"],
        batch["h"],
    )
    losses["total"].backward()
    assert torch.isfinite(losses["total"])
    unused = [
        name
        for name, parameter in model.named_parameters()
        if parameter.requires_grad and parameter.grad is None
    ]
    assert not unused, f"Trainable parameters unused by Stage2 forward: {unused}"


def test_scheduler_respects_each_parameter_group_minimum():
    first = nn.Parameter(torch.zeros(()))
    second = nn.Parameter(torch.zeros(()))
    optimizer = torch.optim.AdamW([
        {"params": [first], "lr": 1e-4},
        {"params": [second], "lr": 1e-5},
    ])
    config = {
        "training": {"max_steps": 10, "warmup_steps": 0},
        "optimizer": {
            "lr": 1e-4,
            "backbone_lr": 1e-5,
            "min_lr": 1e-6,
            "backbone_min_lr": 1e-6,
        },
    }
    scheduler = build_scheduler(optimizer, config)
    for _ in range(10):
        optimizer.step()
        scheduler.step()
    assert abs(optimizer.param_groups[0]["lr"] - 1e-6) < 1e-12
    assert abs(optimizer.param_groups[1]["lr"] - 1e-6) < 1e-12


if __name__ == "__main__":
    test_stage2_forward_and_backward()
    print("Stage2 component smoke test passed.")
