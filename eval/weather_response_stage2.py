#!/usr/bin/env python
"""Measure how a Stage2 checkpoint responds to controlled weather changes."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import torch
from torch.utils.data import DataLoader

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import (
    EarthNet2021Config,
    EarthNet2021Dataset,
    collate_earthnet2021,
)
from data.earthnet_fields import compute_ndvi
from train.train_stage2_earthnet import (
    create_stage2_model,
    load_config,
    move_batch_to_device,
)


SCENARIOS = {
    "precip_x0.5": ("multiply", ["precip_sum", "precip_mean"], 0.5),
    "precip_x2.0": ("multiply", ["precip_sum", "precip_mean"], 2.0),
    "temp_minus5C": ("add", ["temp_mean"], -5.0),
    "temp_plus5C": ("add", ["temp_mean"], 5.0),
    "vpd_x0.5": ("multiply", ["vpd_mean", "vpd_max"], 0.5),
    "vpd_x1.5": ("multiply", ["vpd_mean", "vpd_max"], 1.5),
    "srad_x0.5": ("multiply", ["srad_sum", "srad_mean"], 0.5),
    "srad_x1.5": ("multiply", ["srad_sum", "srad_mean"], 1.5),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--split", default="val")
    parser.add_argument("--external-driver-root", required=True)
    parser.add_argument("--dgh-stats-path", required=True)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--max-batches", type=int, default=100)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    config["data"]["root"] = args.data_root
    config["data"]["split"] = args.split
    config["data"]["external_driver_root"] = args.external_driver_root
    config["data"]["dgh_stats_path"] = args.dgh_stats_path
    config["model"]["encoder"]["from_checkpoint"] = None
    config["model"]["compute_latent_targets"] = False

    data_cfg = EarthNet2021Config.from_config(config["data"], split=args.split)
    if data_cfg.driver_mean is None or data_cfg.driver_std is None:
        raise RuntimeError("Weather-response requires train-only D mean/std.")
    dataset = EarthNet2021Dataset(data_cfg)
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True,
        drop_last=False,
        collate_fn=collate_earthnet2021,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    model = create_stage2_model(config, device)
    model.load_state_dict(
        checkpoint.get("model_state_dict", checkpoint),
        strict=True,
    )
    model.eval()

    sums = defaultdict(float)
    counts = defaultdict(float)
    with torch.no_grad():
        for batch_index, batch in enumerate(tqdm(loader, desc="weather response")):
            if batch_index >= args.max_batches:
                break
            batch = move_batch_to_device(batch, device)
            base_pred = model(batch)["pred"]
            for name, scenario in SCENARIOS.items():
                changed = dict(batch)
                changed["D"] = _apply_scenario(
                    batch["D"],
                    batch["D_mask"],
                    data_cfg,
                    scenario,
                )
                scenario_pred = model(changed)["pred"]
                _accumulate_response(
                    sums,
                    counts,
                    name,
                    base_pred,
                    scenario_pred,
                    batch["target_mask"],
                    batch["h"],
                    data_cfg,
                )

    report = {
        name: sums[name] / max(counts[name], 1.0)
        for name in sorted(sums)
    }
    report["num_samples"] = min(
        len(dataset),
        args.max_batches * args.batch_size,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


def _apply_scenario(
    normalized: torch.Tensor,
    valid_mask: torch.Tensor,
    data_cfg: EarthNet2021Config,
    scenario,
) -> torch.Tensor:
    operation, feature_names, value = scenario
    mean = normalized.new_tensor(data_cfg.driver_mean).view(1, 1, -1)
    std = normalized.new_tensor(data_cfg.driver_std).view(1, 1, -1).clamp_min(1e-6)
    raw = normalized * std + mean
    changed = raw.clone()
    for feature_name in feature_names:
        index = data_cfg.driver_spec.feature_names.index(feature_name)
        if operation == "multiply":
            changed[..., index] = changed[..., index] * value
        elif operation == "add":
            changed[..., index] = changed[..., index] + value
        else:
            raise ValueError(f"Unknown weather scenario operation: {operation}")
    renormalized = (changed - mean) / std
    return torch.where(valid_mask.gt(0), renormalized, normalized)


def _accumulate_response(
    sums,
    counts,
    name: str,
    base_pred: torch.Tensor,
    scenario_pred: torch.Tensor,
    clear_mask: torch.Tensor,
    horizons: torch.Tensor,
    data_cfg: EarthNet2021Config,
) -> None:
    mask = clear_mask.float()
    ndvi_base = compute_ndvi(
        base_pred.float(),
        data_cfg.band_spec.red_index,
        data_cfg.band_spec.nir_index,
    ).clamp(-1, 1)
    ndvi_changed = compute_ndvi(
        scenario_pred.float(),
        data_cfg.band_spec.red_index,
        data_cfg.band_spec.nir_index,
    ).clamp(-1, 1)
    ndvi_delta = ndvi_changed - ndvi_base
    pixel_delta = (scenario_pred.float() - base_pred.float()).abs().mean(dim=2)

    valid = mask.sum()
    sums[f"{name}/mean_ndvi_delta"] += float((ndvi_delta * mask).sum().cpu())
    counts[f"{name}/mean_ndvi_delta"] += float(valid.cpu())
    sums[f"{name}/mean_abs_pixel_delta"] += float((pixel_delta * mask).sum().cpu())
    counts[f"{name}/mean_abs_pixel_delta"] += float(valid.cpu())

    for horizon in torch.unique(horizons).tolist():
        h_mask = mask * horizons.eq(horizon).float()[:, :, None, None]
        key = f"{name}/ndvi_delta_h{int(round(horizon))}"
        sums[key] += float((ndvi_delta * h_mask).sum().cpu())
        counts[key] += float(h_mask.sum().cpu())


if __name__ == "__main__":
    main()
