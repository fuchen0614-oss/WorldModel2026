#!/usr/bin/env python
"""Gate-0 A2: export reproduced-Contextformer NDVI forecasts to GreenEarthNet
`ndvi_pred` NetCDFs, scoreable by eval/eval_greenearthnet_official.py.

Lean by design — this produces a parity NUMBER, so it skips the heavy
provenance/manifest machinery of the formal ObsWorld exporter. It uses the
faithful data adapter + the reproduced Contextformer (official weights) and
writes predictions on the exact official 20 five-daily grid
(`eval.greenearthnet_protocol.expected_prediction_times`).

Usage (server, GPU):
  python eval/export_contextformer_predictions.py \
    --track-dir $DATA_GEN/ood-t_chopped \
    --ckpt checkpoints/contextformer_official/contextformer6M/seed42.ckpt \
    --output-dir evaluations/plan_b_ctx_a2/ood-t_chopped/pred \
    --device cuda --batch-size 8 [--limit 64]
Then score:
  python eval/eval_greenearthnet_official.py --target-dir $DATA_GEN/ood-t_chopped \
    --prediction-dir <output-dir> --output-dir <scores> ...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import xarray as xr
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.greenearthnet_contextformer_dataset import (  # noqa: E402
    GreenEarthNetContextformerDataset,
)
from eval.greenearthnet_protocol import (  # noqa: E402
    PREDICTION_VARIABLE,
    expected_prediction_times,
)
from models.encoders.pvt_contextformer_q import PVTContextformerQ  # noqa: E402

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(it, *a, **k):
        return it


def make_ndvi_prediction_dataset(target: xr.Dataset, ndvi: np.ndarray) -> xr.Dataset:
    """Build the ndvi_pred cube on the official 20 five-daily target times."""
    times = expected_prediction_times(target)
    ndvi = np.clip(np.asarray(ndvi, dtype=np.float32), -1.0, 1.0)
    expected = (times.size, target.sizes["lat"], target.sizes["lon"])
    if ndvi.shape != expected:
        raise ValueError(f"ndvi shape {ndvi.shape} != expected {expected}")
    return xr.Dataset(
        {
            PREDICTION_VARIABLE: xr.DataArray(
                ndvi,
                coords={"time": times, "lat": target.lat, "lon": target.lon},
                dims=("time", "lat", "lon"),
            )
        }
    )


def collate(samples):
    return {
        "dynamic": [
            torch.stack([s["dynamic"][0] for s in samples]),
            torch.stack([s["dynamic"][1] for s in samples]),
        ],
        "dynamic_mask": [torch.stack([s["dynamic_mask"][0] for s in samples])],
        "static": [torch.stack([s["static"][0] for s in samples])],
        "filepath": [s["filepath"] for s in samples],
        "cubename": [s["cubename"] for s in samples],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track-dir", required=True, help="e.g. $DATA_GEN/ood-t_chopped")
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0, help="only first N cubes (0=all)")
    ap.add_argument("--bf16", action="store_true", help="autocast bf16 on cuda")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    dev = args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu"
    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    dataset = GreenEarthNetContextformerDataset(args.track_dir, dl_cloudmask=True)
    n_total = len(dataset)
    if args.limit and args.limit < n_total:
        dataset.filepaths = dataset.filepaths[: args.limit]
    print(f"[data] track={args.track_dir}  cubes={len(dataset)} (of {n_total})")

    loader = DataLoader(
        dataset, batch_size=args.batch_size, shuffle=False,
        num_workers=args.num_workers, collate_fn=collate, pin_memory=(dev == "cuda"),
    )

    model = PVTContextformerQ.from_checkpoint(args.ckpt, strict=True).to(dev).eval()
    print(f"[model] loaded {args.ckpt}  params={model.num_params()/1e6:.2f}M  device={dev}")

    written = skipped = 0
    with torch.no_grad():
        for batch in tqdm(loader, desc="ctx export"):
            data = {
                "dynamic": [batch["dynamic"][0].to(dev), batch["dynamic"][1].to(dev)],
                "dynamic_mask": [batch["dynamic_mask"][0].to(dev)],
                "static": [batch["static"][0].to(dev)],
            }
            if args.bf16 and dev == "cuda":
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    preds = model(data, pred_start=10, preds_length=20)
            else:
                preds = model(data, pred_start=10, preds_length=20)
            ndvi = preds[:, :, 0].float().cpu().numpy()  # (B, 20, H, W)

            for i, fp in enumerate(batch["filepath"]):
                fp = Path(fp)
                out_path = out_root / fp.parent.name / fp.name
                if out_path.exists() and not args.overwrite:
                    skipped += 1
                    continue
                with xr.open_dataset(fp) as target:
                    cube = make_ndvi_prediction_dataset(target, ndvi[i]).load()
                out_path.parent.mkdir(parents=True, exist_ok=True)
                cube.to_netcdf(out_path, encoding={PREDICTION_VARIABLE: {"dtype": "float32"}})
                written += 1

    print(f"[done] written={written} skipped={skipped} out={out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
