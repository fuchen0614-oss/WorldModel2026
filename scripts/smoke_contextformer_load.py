"""Gate-0 A2 smoke: build our vendored Contextformer, load the OFFICIAL weights,
run a forward on synthetic data. Verifies the modern-stack reproduction loads
the published checkpoint cleanly and runs on this box (no data/GPU needed).

Usage:
  python scripts/smoke_contextformer_load.py [--ckpt /tmp/ctx6m/seed=42.ckpt] [--device cpu]
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import torch  # noqa: E402

from models.encoders.pvt_contextformer_q import (  # noqa: E402
    PVTContextformerQ,
    contextformer6m_hparams,
)


def make_synthetic_batch(B=1, H=128, W=128, context=10, preds=20, device="cpu"):
    """Match ContextFormer.forward's expected `data` dict.

    n_image=8 = 5 dynamic channels + 3 static channels (static[:3]).
    weather has the FULL sequence length T = context + preds = 30, c_m = n_weather = 24.
    Only the context frames are given for dynamic/mask; the model appends zeros
    for the prediction window internally.
    """
    T = context + preds
    data = {
        "dynamic": [
            torch.randn(B, context, 5, H, W, device=device),   # hr_dynamic (NDVI+bands)
            torch.randn(B, T, 24, device=device),               # weather (B, T, 24)
        ],
        "dynamic_mask": [
            (torch.rand(B, context, 1, H, W, device=device) > 0.8).float(),  # cloud mask
        ],
        "static": [
            torch.randn(B, 3, H, W, device=device),             # static (DEM etc.)
        ],
    }
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="/tmp/ctx6m/seed=42.ckpt")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--strict", action="store_true", default=True)
    args = ap.parse_args()

    dev = args.device

    print("=" * 70)
    print("Gate-0 A2 smoke: vendored Contextformer + official weights")
    print("=" * 70)

    if os.path.exists(args.ckpt):
        print(f"[load] official ckpt: {args.ckpt}")
        model = PVTContextformerQ.from_official(args.ckpt, strict=args.strict)
        rep = model._load_report
        print(f"[load] missing keys   : {len(rep['missing'])}  {rep['missing'][:3]}")
        print(f"[load] unexpected keys: {len(rep['unexpected'])}  {rep['unexpected'][:3]}")
        assert not rep["missing"], "missing keys -> arch mismatch"
        assert not rep["unexpected"], "unexpected keys -> arch mismatch"
        loaded = True
    else:
        print(f"[warn] ckpt not found ({args.ckpt}); building random-init instead")
        model = PVTContextformerQ(contextformer6m_hparams(pvt_pretrained=False))
        loaded = False

    model = model.to(dev).eval()
    n = model.num_params()
    print(f"[arch] params: {n/1e6:.2f}M  (expected ~6.06M)")

    data = make_synthetic_batch(device=dev)
    with torch.no_grad():
        preds, z = model.encode(data, pred_start=10, preds_length=20)

    print(f"[fwd ] preds shape: {tuple(preds.shape)}  (expected (1, 20, 1, 128, 128))")
    print(f"[fwd ] z (state)  : {tuple(z.shape)}  (expected (B*32*32, 30, 256))")
    print(f"[fwd ] preds finite: {torch.isfinite(preds).all().item()}  "
          f"range [{preds.min().item():.3f}, {preds.max().item():.3f}]")

    ok = (
        tuple(preds.shape) == (1, 20, 1, 128, 128)
        and torch.isfinite(preds).all().item()
        and z is not None
    )
    print("-" * 70)
    print(f"RESULT: {'PASS' if ok else 'FAIL'}  (weights_loaded={loaded})")
    print("=" * 70)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
