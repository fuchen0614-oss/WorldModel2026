"""Evaluate a Stage2 checkpoint on an EarthNet split with ObsWorld losses."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
import yaml
from torch.utils.data import DataLoader

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import EarthNet2021Config, EarthNet2021Dataset, collate_earthnet2021
from eval.earthnet_standard_metrics import EarthNetScoreAccumulator
from eval.forecast_metrics import ForecastMetricAccumulator
from models.losses.earthnet_forecasting import EarthNetForecastLoss
from train.train_stage2_earthnet import (
    create_stage2_model,
    load_config,
    load_stage2_model_state,
    move_batch_to_device,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--split", default="val")
    parser.add_argument("--data-root", type=str)
    parser.add_argument("--external-driver-root", type=str)
    parser.add_argument("--dgh-stats-path", type=str)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--output", default=None)
    parser.add_argument("--official-score", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.data_root is not None:
        config["data"]["root"] = args.data_root
    if args.external_driver_root is not None:
        config["data"]["external_driver_root"] = args.external_driver_root
    if args.dgh_stats_path is not None:
        config["data"]["dgh_stats_path"] = args.dgh_stats_path
    config["data"]["split"] = args.split

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data_cfg = EarthNet2021Config.from_config(config["data"], split=args.split)
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

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    # The Stage2 checkpoint is self-contained; do not require the original
    # Stage1.5 checkpoint path to still exist during evaluation.
    config["model"]["encoder"]["from_checkpoint"] = None
    model = create_stage2_model(config, device)
    state = checkpoint.get("model_state_dict", checkpoint)
    load_stage2_model_state(model, state, strict=True)
    model.eval()

    loss_fn = EarthNetForecastLoss.from_config(
        config["loss"],
        red_index=data_cfg.band_spec.red_index,
        nir_index=data_cfg.band_spec.nir_index,
    ).to(device)

    sums = {}
    count = 0
    official = EarthNetScoreAccumulator(data_cfg.eval_img_size) if args.official_score else None
    forecast_metrics = ForecastMetricAccumulator(
        red_index=data_cfg.band_spec.red_index,
        nir_index=data_cfg.band_spec.nir_index,
    )
    with torch.no_grad():
        for batch in tqdm(loader, desc=f"eval {args.split}"):
            batch = move_batch_to_device(batch, device)
            out = model(batch)
            losses = loss_fn(
                out["pred"],
                batch["x_target"],
                batch.get("target_mask"),
                z_pred=out.get("z_pred"),
                z_target=out.get("z_target"),
                z_context=out.get("z_context"),
                z_target_mask=out.get("z_target_mask"),
                horizons=batch.get("h"),
            )
            bs = batch["x_target"].shape[0]
            count += bs
            for key, value in losses.items():
                sums[key] = sums.get(key, 0.0) + float(value.detach().cpu()) * bs
            forecast_metrics.update(
                out["pred"],
                batch["x_target"],
                batch["target_mask"],
                batch["h"],
                batch["x_context"],
                batch["context_mask"],
            )
            if official is not None:
                official.update(
                    out["pred"],
                    batch["x_target"],
                    batch["target_mask"],
                    [item["sample_id"] for item in batch["meta"]],
                )

    metrics = {key: value / max(count, 1) for key, value in sums.items()}
    metrics["num_samples"] = count
    metrics.update(forecast_metrics.compute())
    if official is not None:
        metrics.update(official.compute())
    print(json.dumps(metrics, indent=2, ensure_ascii=False))

    if args.output is not None:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
