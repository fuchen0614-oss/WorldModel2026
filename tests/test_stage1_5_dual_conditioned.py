"""CPU tests for the canonical Stage1.5 dual-conditioned path."""

import torch

from data.datasets.ssl4eo_dual import collate_dual_conditioned_pair_fn
from models.decoders.dual_head_decoder import DualHeadDecoder
from models.encoders.multimodal_vit_encoder import MultiModalViTEncoder
from models.encoders.multimodal_vit_encoder_film import MultiModalViTEncoderFiLM
from models.encoders.pure_imaging_condition_encoder import PureImagingConditionEncoder
from models.encoders.state_projection import SpatialStateProjector
from models.losses.stage1_5_state import CrossModalVICRegLoss, PhiCrossCovarianceLoss
from train.train_stage1_5_dual_conditioned import train_micro_step


def make_phi(batch=4, modality=0, with_sar=False):
    phi = {
        "center_lat": torch.linspace(-30, 30, batch),
        "center_lon": torch.linspace(0, 60, batch),
        "modality": torch.full((batch,), modality, dtype=torch.long),
        "time": torch.arange(batch, dtype=torch.long) * 86_400_000_000_000,
        "time_valid": torch.ones(batch, dtype=torch.long),
        "season": torch.arange(batch, dtype=torch.long) % 4,
        "day_of_year": torch.arange(batch, dtype=torch.long) + 10,
        "sun_elevation": torch.linspace(20, 60, batch),
        "cloud_cover": torch.zeros(batch),
        "cloud_shadow": torch.zeros(batch),
        "valid_ratio": torch.ones(batch),
    }
    if with_sar:
        phi.update({
            "s1_orbit_direction": torch.arange(batch) % 2,
            "s1_relative_orbit": torch.arange(batch) + 1,
            "s1_satellite": torch.arange(batch) % 2,
            "s1_incidence_angle": torch.full((batch,), float("nan")),
            "s1_incidence_valid": torch.zeros(batch, dtype=torch.long),
        })
    return phi


def test_pure_phi_ignores_semantic_shortcuts():
    encoder = PureImagingConditionEncoder(embed_dim=64, condition_dropout=0.0).eval()
    phi = make_phi()
    changed = {k: v.clone() for k, v in phi.items()}
    changed["center_lat"] += 80
    changed["center_lon"] -= 120
    changed["season"] = (changed["season"] + 2) % 4
    changed["day_of_year"] += 180
    changed["cloud_cover"][:] = 0.9
    with torch.no_grad():
        first = encoder(phi)
        second = encoder(changed)
    assert torch.equal(first, second)


def test_late_film_and_state_shape():
    encoder = MultiModalViTEncoderFiLM(
        img_size=32, patch_size=8, embed_dim=64, depth=4, num_heads=4,
        phi_dim=64, use_film=True, use_cross_attention=False, film_start_layer=2)
    assert not hasattr(encoder.blocks[0], "film")
    assert not hasattr(encoder.blocks[1], "film")
    assert hasattr(encoder.blocks[2], "film") and hasattr(encoder.blocks[3], "film")
    projector = SpatialStateProjector(in_dim=64, state_dim=32, hidden_dim=64)
    tokens = encoder(torch.randn(2, 12, 32, 32), "S2", 0.0, torch.randn(2, 64))[0]
    assert projector(tokens).shape == (2, 16, 32)


def test_time_pair_collate():
    ns_day = 86_400_000_000_000
    rows = []
    for i, delta in enumerate((3, 9)):
        common = {
            "sample_id": str(i), "sample_key": f"k{i}", "season_idx": 0,
            "s1_image": torch.zeros(2, 16, 16), "s2_image": torch.zeros(12, 16, 16),
            "cloud_mask": torch.zeros(16, 16),
        }
        def raw(modality, time):
            out = {"modality": modality, "center_lat": 0.0, "center_lon": 0.0}
            for t in range(4):
                out.update({f"time_{t}": time, f"time_valid_{t}": 1,
                            f"season_{t}": t, f"day_of_year_{t}": t + 1,
                            f"sun_elevation_{t}": 30.0, f"cloud_cover_{t}": 0.0,
                            f"cloud_shadow_{t}": 0.0, f"valid_ratio_{t}": 1.0})
            return out
        common["phi_s1"] = raw("S1GRD", 0)
        common["phi_s2"] = raw("S2L2A", delta * ns_day)
        rows.append(common)
    batch = collate_dual_conditioned_pair_fn(rows)
    assert torch.allclose(batch["time_delta_days"], torch.tensor([3.0, 9.0]))


def test_losses_finite_and_backward():
    z1 = torch.randn(8, 32, requires_grad=True)
    z2 = torch.randn(8, 32, requires_grad=True)
    out = CrossModalVICRegLoss()(z1, z2, torch.ones(8, dtype=torch.bool))
    nuisance = PhiCrossCovarianceLoss()(z1, make_phi(8), "S2")
    (out["total"] + nuisance).backward()
    assert torch.isfinite(z1.grad).all() and torch.isfinite(z2.grad).all()


def test_end_to_end_micro_step():
    torch.manual_seed(0)
    b, size = 4, 32
    encoder = MultiModalViTEncoderFiLM(
        img_size=size, patch_size=8, embed_dim=64, depth=4, num_heads=4,
        phi_dim=64, use_film=True, use_cross_attention=False, film_start_layer=2)
    phi_encoder = PureImagingConditionEncoder(embed_dim=64, condition_dropout=0.0)
    decoder = DualHeadDecoder(
        in_dim=64, decoder_embed_dim=32, depth=2, num_heads=4,
        patch_size=8, img_size=size, phi_dim=64)
    projector = SpatialStateProjector(in_dim=64, state_dim=32, hidden_dim=64)
    teacher = MultiModalViTEncoder(
        img_size=size, patch_size=8, embed_dim=64, depth=4, num_heads=4)
    teacher.load_state_dict({k: v for k, v in encoder.state_dict().items() if ".film." not in k}, strict=True)
    teacher.requires_grad_(False).eval()
    batch = {
        "s1_image": torch.randn(b, 2, size, size),
        "s2_image": torch.randn(b, 12, size, size),
        "s1_phi": make_phi(b, 1, True), "s2_phi": make_phi(b, 0, False),
        "cloud_mask": torch.zeros(b, size, size),
        "time_delta_days": torch.tensor([1.0, 2.0, 8.0, 3.0]),
        "time_pair_valid": torch.ones(b, dtype=torch.bool),
    }
    config = {
        "data": {"pair_max_days": 7.0},
        "training": {
            "mask_ratio": 0.75, "recon_loss": "l1",
            "loss_weights": {"mae": 1.0, "alignment_start": 0.01,
                             "alignment_end": 0.02, "nuisance_start": 0.0,
                             "nuisance_end": 0.01, "anchor": 0.1,
                             "ramp_end_step": 10},
        },
    }
    losses = {"alignment": CrossModalVICRegLoss(),
              "nuisance": PhiCrossCovarianceLoss(),
              "anchor": __import__("models.losses.stage1_5_state", fromlist=["FeatureAnchorLoss"]).FeatureAnchorLoss()}
    total, logs = train_micro_step(batch, torch.device("cpu"), encoder, phi_encoder,
                                   decoder, projector, teacher, losses, config, 0)
    total.backward()
    assert torch.isfinite(total)
    assert logs["pair_valid_rate"] == 0.75
    assert any(p.grad is not None for p in phi_encoder.parameters())
