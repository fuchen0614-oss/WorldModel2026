#!/usr/bin/env python
"""CPU smoke test for model construction, interventions, and serialization."""

import argparse
import sys
import tempfile
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.terrastate import TerraState, load_checkpoint  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-size", type=int, default=32)
    parser.add_argument("--architecture-only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    torch.manual_seed(7)
    model = TerraState(history_pretrained=False).cpu().eval()
    if args.architecture_only:
        print(f"TerraState parameters={model.parameter_count()}")
        return
    size = args.image_size
    batch = {
        "dynamic": [
            torch.randn(1, 30, 5, size, size),
            torch.randn(1, 30, 24),
        ],
        "dynamic_mask": [torch.zeros(1, 30, 1, size, size)],
        "static": [torch.randn(1, 5, size, size)],
        "landcover": torch.full((1, 1, size, size), 30.0),
    }
    with torch.no_grad():
        full = model.forecast(batch)
        removed = model.forecast(batch, state_scale=0.0)
        identity = model.forecast(batch, identity_transition=True)
        mean_weather = torch.zeros(1, 20, 24)
        mean = model.forecast(batch, future_weather=mean_weather)
    expected = (1, 20, 1, size, size)
    assert full.shape == removed.shape == identity.shape == mean.shape == expected
    assert torch.isfinite(full).all()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "checkpoint.pt"
        torch.save({"model_state_dict": model.state_dict()}, path)
        restored = TerraState(history_pretrained=False)
        report = load_checkpoint(restored, str(path), strict=True)
        assert report == {"missing": [], "unexpected": []}
    print("CPU_SMOKE_PASS")


if __name__ == "__main__":
    main()
