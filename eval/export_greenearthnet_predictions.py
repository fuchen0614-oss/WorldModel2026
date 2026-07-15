#!/usr/bin/env python
"""Export ObsWorld RGBN forecasts to official GreenEarthNet NetCDF files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
import xarray as xr
from torch.utils.data import DataLoader

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import (  # noqa: E402
    EarthNet2021Config,
    EarthNet2021Dataset,
    collate_earthnet2021,
)
from data.stage2_contract import model_input_view  # noqa: E402
from eval.greenearthnet_protocol import make_prediction_dataset  # noqa: E402
from train.train_stage2_earthnet import (  # noqa: E402
    create_stage2_model,
    load_config,
    load_stage2_model_state,
    move_batch_to_device,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--split", default="ood-t")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dgh-stats-path")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    config["data"].update(
        {
            "root": args.data_root,
            "split": args.split,
            "manifest_path": args.manifest,
            "require_manifest": True,
            "strict": True,
        }
    )
    if args.dgh_stats_path:
        config["data"]["dgh_stats_path"] = args.dgh_stats_path
    config["model"]["encoder"]["from_checkpoint"] = None
    # Formal export never sends future observations/masks through the model.
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
    written = 0
    skipped = 0
    with torch.no_grad():
        for batch in tqdm(loader, desc=f"export GreenEarthNet {args.split}"):
            batch = move_batch_to_device(batch, device)
            prediction = model(model_input_view(batch))["pred"].float().clamp(0, 1)
            for index, metadata in enumerate(batch["meta"]):
                target_path = Path(metadata["path"])
                output_path = output_root / target_path.parent.name / target_path.name
                if output_path.exists() and not args.overwrite:
                    skipped += 1
                    continue
                with xr.open_dataset(target_path) as target:
                    height = int(target.sizes["lat"])
                    width = int(target.sizes["lon"])
                    rgbn = prediction[index]
                    if tuple(rgbn.shape[-2:]) != (height, width):
                        rgbn = F.interpolate(
                            rgbn,
                            size=(height, width),
                            mode="bilinear",
                            align_corners=False,
                        )
                    prediction_cube = make_prediction_dataset(
                        target,
                        rgbn.cpu().numpy(),
                        red_index=data_cfg.band_spec.red_index,
                        nir_index=data_cfg.band_spec.nir_index,
                    ).load()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                prediction_cube.to_netcdf(
                    output_path,
                    encoding={"ndvi_pred": {"dtype": "float32"}},
                )
                written += 1

    summary = {
        "split": args.split,
        "manifest": str(Path(args.manifest).resolve()),
        "num_dataset_files": len(dataset),
        "written": written,
        "skipped_existing": skipped,
        "output_dir": str(output_root.resolve()),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "export_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
