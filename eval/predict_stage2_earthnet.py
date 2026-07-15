#!/usr/bin/env python
"""Export ObsWorld predictions in the official EarthNet2021 NPZ layout."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
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
from train.train_stage2_earthnet import (
    create_stage2_model,
    forward_stage2_model,
    load_config,
    load_stage2_model_state,
    move_batch_to_device,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument(
        "--split",
        default="iid",
        choices=["train", "val", "iid", "ood", "extreme", "seasonal", "test"],
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--external-driver-root")
    parser.add_argument("--dgh-stats-path")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--output-size", type=int, default=128)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    config["data"]["root"] = args.data_root
    config["data"]["split"] = args.split
    # Official test context cubes contain 10 optical frames and no targets.
    config["data"]["strict"] = False
    if args.external_driver_root:
        config["data"]["external_driver_root"] = args.external_driver_root
    if args.dgh_stats_path:
        config["data"]["dgh_stats_path"] = args.dgh_stats_path
    config["model"]["encoder"]["from_checkpoint"] = None
    config["model"]["compute_latent_targets"] = False

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

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    model = create_stage2_model(config, device)
    load_stage2_model_state(
        model,
        checkpoint.get("model_state_dict", checkpoint),
        strict=True,
    )
    model.eval()

    output_root = Path(args.output_dir)
    with torch.no_grad():
        for batch in tqdm(loader, desc=f"predict EarthNet {args.split}"):
            batch = move_batch_to_device(batch, device)
            pred = forward_stage2_model(model, batch)["pred"].float().clamp(0, 1)
            pred = _resize_predictions(pred, args.output_size).cpu().numpy()
            for index, meta in enumerate(batch["meta"]):
                cubename = meta["sample_id"]
                tile = cubename[:5]
                path = output_root / tile / f"{cubename}.npz"
                if path.exists() and not args.overwrite:
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                highresdynamic = np.transpose(
                    pred[index],
                    (2, 3, 1, 0),
                ).astype(np.float32)
                np.savez_compressed(path, highresdynamic=highresdynamic)

    print(f"predictions={output_root}")
    print(f"num_cubes={len(dataset)}")


def _resize_predictions(pred: torch.Tensor, size: int) -> torch.Tensor:
    b, t, c, h, w = pred.shape
    if (h, w) == (size, size):
        return pred
    resized = F.interpolate(
        pred.reshape(b * t, c, h, w),
        size=(size, size),
        mode="bilinear",
        align_corners=False,
    )
    return resized.reshape(b, t, c, size, size)


if __name__ == "__main__":
    main()
