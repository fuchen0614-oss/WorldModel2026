#!/usr/bin/env python
"""plan-b-pvt · Table 3 dynamics measurements on a trained B0 (no new training).

Two measurements on the frozen forecaster (evidence that its z is a controllable
predictive state, not just a hidden feature):

  (A) latent-future consistency: cosine( z_student[future], z_teacher[future] ),
      where student = normal forecast (future masked) and teacher = all-frames-
      visible (sees the real future). High cosine => the predicted state is
      consistent with the real future-informed state.

  (B) weather sensitivity: NDVI prediction change when the future weather driver
      is (i) zeroed (null) or (ii) shuffled across the batch (wrong). A non-trivial
      change => the state responds to the exogenous driver, not ignores it.

Usage:
  python eval/eval_table3_dynamics.py --ckpt checkpoints/plan_b_b0/checkpoint_best.pt \
    --data-root $DATA_GEN/ood-t_chopped --output evaluations/plan_b_b0_table3 --max-cubes 256
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*Grad strides do not match.*")

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset  # noqa: E402
from models.encoders.pvt_contextformer_q import PVTContextformerQ  # noqa: E402
from train.train_plan_b_contextformer import collate, to_device  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--data-root", required=True, help="a GreenEarthNet track dir of .nc cubes")
    ap.add_argument("--output", required=True)
    ap.add_argument("--max-cubes", type=int, default=256)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()
    dev = args.device if torch.cuda.is_available() else "cpu"

    model = PVTContextformerQ.from_checkpoint(args.ckpt, strict=True).to(dev).eval()
    ds = GreenEarthNetContextformerDataset(args.data_root, dl_cloudmask=True)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False,
                        num_workers=4, collate_fn=collate)

    cons, sens_null, sens_wrong, n = [], [], [], 0
    cl, tl = model.hparams.context_length, model.hparams.target_length
    with torch.no_grad():
        for batch in loader:
            data = to_device(batch, dev)
            # (A) latent-future consistency: student (future masked) vs teacher (all visible)
            model.core(data, pred_start=cl, preds_length=tl); z_s = model._z
            model.core(data, pred_start=cl + tl, preds_length=0); z_t = model._z
            fut = slice(cl, cl + tl)
            cons.append(F.cosine_similarity(z_s[:, fut], z_t[:, fut], dim=-1).mean().item())

            # (B) weather sensitivity: real vs null vs shuffled future weather
            preds = model(data, pred_start=cl, preds_length=tl)             # real
            w = data["dynamic"][1]
            data_null = {**data, "dynamic": [data["dynamic"][0], torch.zeros_like(w)]}
            preds_null = model(data_null, pred_start=cl, preds_length=tl)
            perm = torch.randperm(w.shape[0], device=w.device)
            data_wrong = {**data, "dynamic": [data["dynamic"][0], w[perm]]}
            preds_wrong = model(data_wrong, pred_start=cl, preds_length=tl)
            sens_null.append((preds - preds_null).abs().mean().item())
            sens_wrong.append((preds - preds_wrong).abs().mean().item())

            n += batch["dynamic"][0].shape[0]
            if n >= args.max_cubes:
                break

    result = {
        "n_cubes": n,
        "latent_future_consistency_cos": float(np.mean(cons)),
        "weather_sensitivity_null_ndvi_mae": float(np.mean(sens_null)),
        "weather_sensitivity_wrong_ndvi_mae": float(np.mean(sens_wrong)),
        "note": "high consistency_cos => predicted state ~= future-informed state; "
                "non-zero weather_sensitivity => the state responds to the driver "
                "(null/wrong weather changes the NDVI forecast).",
    }
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    (out / "table3_dynamics.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
