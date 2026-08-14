"""Local smoke for the B0 training core (no DDP, no real data).

Builds synthetic cubes, then checks: train-mode forward (mtm masking) + masked
L2 NDVI loss + backward produce finite grads, and eval-mode forward
(pred_start=10) + loss are finite. Validates the training math before the
8-GPU run on the server.
"""
import os
import sys
import tempfile

import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from data.greenearthnet_contextformer_dataset import (  # noqa: E402
    GreenEarthNetContextformerDataset,
)
from models.encoders.pvt_contextformer_q import (  # noqa: E402
    PVTContextformerQ,
    contextformer6m_hparams,
)
from models.losses.masked_l2_ndvi import MaskedL2NDVILoss  # noqa: E402
from train.train_plan_b_contextformer import collate  # noqa: E402
from scripts.smoke_greenearthnet_adapter import make_fake_cube  # noqa: E402


def main():
    print("=" * 70)
    print("B0 training-core smoke")
    print("=" * 70)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    with tempfile.TemporaryDirectory() as d:
        for i in range(2):
            make_fake_cube(os.path.join(d, f"cube_{i}.nc"), seed=i)
        ds = GreenEarthNetContextformerDataset(d, dl_cloudmask=True)
        batch = collate([ds[0], ds[1]])
        data = {
            "dynamic": [batch["dynamic"][0].to(dev), batch["dynamic"][1].to(dev)],
            "dynamic_mask": [batch["dynamic_mask"][0].to(dev)],
            "static": [batch["static"][0].to(dev)],
            "landcover": batch["landcover"].to(dev),
        }

        model = PVTContextformerQ(contextformer6m_hparams(pvt_pretrained=False)).to(dev)
        loss_fn = MaskedL2NDVILoss(
            lc_min=10, lc_max=40, context_length=10, target_length=20,
            ndvi_pred_idx=0, ndvi_targ_idx=0, pred_mask_value=-1,
        )

        # --- train step ---
        model.train()
        preds = model(data)  # train mode -> c_l=10, mtm masking, full 30 frames
        loss, logs = loss_fn(preds, data)
        loss.backward()
        gnorm = sum(p.grad.norm().item() for p in model.parameters() if p.grad is not None)
        print(f"[train] preds={tuple(preds.shape)} loss={loss.item():.5f} "
              f"finite={torch.isfinite(loss).item()} grad_norm={gnorm:.3f}")

        # --- eval step ---
        model.eval()
        with torch.no_grad():
            vpreds = model(data, pred_start=10, preds_length=20)
            vloss, _ = loss_fn(vpreds, data)
        print(f"[eval ] preds={tuple(vpreds.shape)} loss={vloss.item():.5f} "
              f"finite={torch.isfinite(vloss).item()}")

        ok = (
            preds.shape[1] == 30 and tuple(vpreds.shape) == (2, 20, 1, 128, 128)
            and torch.isfinite(loss).item() and torch.isfinite(vloss).item()
            and gnorm > 0
        )
    print("-" * 70)
    print(f"RESULT: {'PASS' if ok else 'FAIL'}  (device={dev})")
    print("=" * 70)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
