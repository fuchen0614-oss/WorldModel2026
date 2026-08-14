from __future__ import annotations

from pathlib import Path

import torch
import yaml

from data.stage2_contract import stage2_field_table, validate_stage2_batch
from models.adapters.earthnet_band_adapter import EarthNetInputAdapter
from models.adapters.geo_tokenizer import GeoTokenizer


def test_earthnet_b8a_maps_to_canonical_b8a_slot():
    adapter = EarthNetInputAdapter(in_channels=4, out_channels=12)
    source = torch.tensor([[[[1.0]], [[2.0]], [[3.0]], [[4.0]]]])
    output = adapter(source)

    expected = torch.zeros_like(output)
    expected[:, 1] = 1.0  # B02
    expected[:, 2] = 2.0  # B03
    expected[:, 3] = 3.0  # B04
    expected[:, 8] = 4.0  # B8A, not B08
    assert torch.equal(output, expected)


def test_geo_tokenizer_preserves_single_channel_signal():
    tokenizer = GeoTokenizer(in_channels=1, geo_dim=4, img_size=8, patch_size=4)
    with torch.no_grad():
        tokenizer.proj[0].weight[:, 0] = torch.tensor([1.0, 2.0, 4.0, 8.0])
        tokenizer.proj[0].bias.copy_(torch.tensor([0.0, -0.1, 0.2, 0.4]))
    low = tokenizer(torch.full((1, 1, 8, 8), 0.2))
    high = tokenizer(torch.full((1, 1, 8, 8), 0.8))
    assert torch.isfinite(low).all() and torch.isfinite(high).all()
    assert not torch.allclose(low, high)


def test_stage2_batch_contract_checks_temporal_alignment():
    batch = {
        "x_context": torch.zeros(2, 3, 4, 8, 8),
        "context_mask": torch.ones(2, 3, 8, 8),
        "D": torch.zeros(2, 5, 9),
        "D_mask": torch.ones(2, 5, 9),
        "G": torch.zeros(2, 1, 8, 8),
        "G_mask": torch.ones(2, 1, 8, 8),
        "h": torch.arange(5).float().view(1, 5).repeat(2, 1),
        "x_target": torch.zeros(2, 5, 4, 8, 8),
        "target_mask": torch.ones(2, 5, 8, 8),
    }
    validate_stage2_batch(batch)
    assert {item["name"] for item in stage2_field_table()} >= {"D", "G", "h", "x_target"}


def test_stage2_configs_use_b8a_mapping():
    root = Path(__file__).resolve().parents[1]
    for name in ("stage2_earthnet_main.yaml", "stage2_earthnet_smoke.yaml"):
        config = yaml.safe_load((root / "configs" / "train" / name).read_text(encoding="utf-8"))
        assert config["model"]["band_adapter"]["source_to_canonical"] == [1, 2, 3, 8]
