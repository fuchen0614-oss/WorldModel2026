#!/usr/bin/env python
"""plan-b-pvt · export FULL TerraState (B4) NDVI forecasts for scoring.

Unlike eval/export_contextformer_predictions.py (which loads a bare Contextformer
core = B0), this REQUIRES a full `b4_state_dict` and runs the load-bearing
prediction ŷ = B0 + gate·O_δ(direct T). Guards (doc 84 requirement ⑦):
  * refuses a checkpoint that only has `core_state_dict` (that would silently
    score B0 and mislabel it as B4);
  * prints the gate magnitude + residual contribution so a gate≈0 (== B0) run is
    visible, not hidden.

Usage (server, GPU):
  python eval/export_b4_predictions.py --track-dir $DATA_GEN/ood-t_chopped \
    --ckpt checkpoints/plan_b_b4a/checkpoint_best.pt \
    --output-dir evaluations/plan_b_b4a/ood-t_chopped/pred --device cuda --batch-size 8
Then score with eval/eval_greenearthnet_official.py (same frozen evaluator as B0).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Only torch/model imports at module level, so `load_b4` is importable WITHOUT xarray
# (the CPU smoke reuses it). Data/xarray/exporter imports are lazy inside main().
from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from models.plan_b_b4 import ObsWorldB4  # noqa: E402


def load_b4(ckpt_path: str, device: str) -> ObsWorldB4:
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    if not (isinstance(ckpt, dict) and "b4_state_dict" in ckpt):
        raise ValueError(
            f"{ckpt_path} has no 'b4_state_dict'. Refusing to score it as B4 — a "
            "core_state_dict-only checkpoint is B0, not TerraState. Use "
            "eval/export_contextformer_predictions.py for a B0/core checkpoint."
        )
    hp = contextformer6m_hparams(pvt_pretrained=False)
    contract_cfg = ckpt.get("contract_cfg", {"state_dim": 256})
    model = ObsWorldB4(hp, contract_cfg=contract_cfg)
    missing, unexpected = model.load_state_dict(ckpt["b4_state_dict"], strict=True)
    gate = float(model.gate.detach().abs().mean().item())
    print(f"[model] loaded b4_state_dict  params={model.num_params()/1e6:.2f}M  "
          f"missing={len(missing)} unexpected={len(unexpected)}  |gate|={gate:.4e}")
    if gate == 0.0:
        print("[warn] gate==0 -> this B4 forecast is byte-identical to B0 (nothing learned yet).")
    return model.to(device).eval()


def main() -> int:
    import xarray as xr
    from torch.utils.data import DataLoader
    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
    from eval.export_contextformer_predictions import collate, make_ndvi_prediction_dataset
    from eval.greenearthnet_protocol import PREDICTION_VARIABLE
    try:
        from tqdm import tqdm
    except ImportError:
        def tqdm(it, *a, **k):
            return it

    ap = argparse.ArgumentParser()
    ap.add_argument("--track-dir", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    dev = args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu"
    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    dataset = GreenEarthNetContextformerDataset(args.track_dir, dl_cloudmask=True)
    if args.limit and args.limit < len(dataset):
        dataset.filepaths = dataset.filepaths[: args.limit]
    print(f"[data] track={args.track_dir}  cubes={len(dataset)}")
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False,
                        num_workers=args.num_workers, collate_fn=collate, pin_memory=(dev == "cuda"))

    model = load_b4(args.ckpt, dev)

    written = skipped = 0
    resid_frac = []
    with torch.no_grad():
        for batch in tqdm(loader, desc="b4 export"):
            data = {
                "dynamic": [batch["dynamic"][0].to(dev), batch["dynamic"][1].to(dev)],
                "dynamic_mask": [batch["dynamic_mask"][0].to(dev)],
                "static": [batch["static"][0].to(dev)],
            }
            preds, preds_b0, residual, *_ = model.forecast(data, want_state=True)
            resid_frac.append((model.gate * residual).abs().mean().item() / (preds.abs().mean().item() + 1e-8))
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

    print(f"[done] written={written} skipped={skipped} "
          f"mean_residual_fraction={np.mean(resid_frac):.4e} out={out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
