#!/usr/bin/env python
"""plan-b-pvt · Stage1.8 factorization eval (Table 2 + Fig 3, the world-model evidence).

Loads a trained Stage18Factorizer and, on held-out paired L1C/L2A samples, measures:
  * 4-way cross-render (L1C->L1C, L1C->L2A, L2A->L1C, L2A->L2A): reflectance MAE/RMSE,
    SAM (spectral angle), SSIM  -> Table 2.
  * paired latent distance ||q(L1C) - q(L2A)|| (shared, product-invariant state).
  * control no-phi (identity FiLM): cross-render must get WORSE without phi -> phi is
    load-bearing, not decoration.
  * Fig 3: fix z, render with L1C-phi vs L2A-phi -> RGB pngs showing phi controls the
    product a pure forecaster cannot switch.

Usage:
  python eval/eval_stage1_8_factorize.py --ckpt checkpoints/plan_b_stage1_8/checkpoint_last.pt \
    --cache-dir /tmp/zjliu17_l1c_l2a_cache --output evaluations/plan_b_stage1_8 --fig3 8
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.ssl4eo_l1c_l2a_paired import SSL4EOL1CL2APairedDataset  # noqa: E402
from models.stage1_8_factorizer import Stage18Factorizer, L1C, L2A  # noqa: E402


def sam(pred, targ, eps=1e-8):
    """Spectral angle (rad), mean over pixels. pred/targ: (B,C,H,W)."""
    dot = (pred * targ).sum(1)
    n = pred.norm(dim=1) * targ.norm(dim=1) + eps
    return torch.arccos((dot / n).clamp(-1 + 1e-6, 1 - 1e-6)).mean().item()


def ssim(pred, targ):
    try:
        from skimage.metrics import structural_similarity as sk_ssim
    except Exception:
        return float("nan")
    p = pred.detach().cpu().numpy(); t = targ.detach().cpu().numpy()
    vals = []
    for b in range(p.shape[0]):
        for c in range(p.shape[1]):
            vals.append(sk_ssim(t[b, c], p[b, c], data_range=1.0))
    return float(np.mean(vals))


@torch.no_grad()
def render_no_phi(model, z):
    """FiLM bypass (identity): decode z without any product conditioning."""
    return model.decoder(z)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--max-samples", type=int, default=512)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--fig3", type=int, default=8, help="#samples for the Fig-3 phi-swap panel")
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    dev = args.device if torch.cuda.is_available() else "cpu"
    model = Stage18Factorizer(in_ch=4, state_dim=256, pvt_pretrained=False).to(dev).eval()
    ck = torch.load(args.ckpt, map_location="cpu", weights_only=False)
    model.load_state_dict(ck["model_state_dict"], strict=True)

    ds = SSL4EOL1CL2APairedDataset(args.cache_dir)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False, num_workers=4)

    combos = [("L1C->L1C", "l1c", L1C), ("L1C->L2A", "l1c", L2A),
              ("L2A->L1C", "l2a", L1C), ("L2A->L2A", "l2a", L2A)]
    acc = {c[0]: {"mae": [], "rmse": [], "sam": [], "ssim": []} for c in combos}
    nophi = {"L1C": [], "L2A": []}
    paired_dist, n = [], 0

    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    with torch.no_grad():
        for batch in loader:
            l1c, l2a = batch["l1c"].to(dev), batch["l2a"].to(dev)
            z = {"l1c": model.encode(l1c), "l2a": model.encode(l2a)}
            tgt = {"l1c": l1c, "l2a": l2a}
            paired_dist.append((z["l1c"] - z["l2a"]).pow(2).mean().item())
            for name, src, pid in combos:
                target = tgt["l2a" if pid == L2A else "l1c"]
                pred = model.render(z[src], torch.full((l1c.shape[0],), pid, device=dev, dtype=torch.long))
                acc[name]["mae"].append((pred - target).abs().mean().item())
                acc[name]["rmse"].append((pred - target).pow(2).mean().sqrt().item())
                acc[name]["sam"].append(sam(pred, target))
                acc[name]["ssim"].append(ssim(pred, target))
            # no-phi control: decode z_l1c without product token, compare to both products
            npred = render_no_phi(model, z["l1c"])
            nophi["L1C"].append((npred - l1c).abs().mean().item())
            nophi["L2A"].append((npred - l2a).abs().mean().item())
            n += l1c.shape[0]
            if n >= args.max_samples:
                break

    table2 = {name: {k: float(np.mean(v)) for k, v in m.items()} for name, m in acc.items()}
    result = {
        "n_samples": n,
        "table2_cross_render": table2,
        "paired_latent_mse": float(np.mean(paired_dist)),
        "control_no_phi_mae": {k: float(np.mean(v)) for k, v in nophi.items()},
        "note": "cross-render (L1C->L2A / L2A->L1C) low + no-phi worse => phi controls the "
                "product; paired_latent_mse low => shared product-invariant state.",
    }
    (out / "table2_factorization.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

    # --- Fig 3: fix z(L1C), render with L1C-phi vs L2A-phi (RGB from B04,B03,B02) ---
    if args.fig3 > 0:
        try:
            import imageio.v2 as imageio
            fig_dir = out / "fig3_phi_swap"; fig_dir.mkdir(exist_ok=True)
            b = next(iter(loader))
            l1c = b["l1c"][: args.fig3].to(dev)
            z = model.encode(l1c)
            r_l1c = model.render(z, torch.full((l1c.shape[0],), L1C, device=dev, dtype=torch.long))
            r_l2a = model.render(z, torch.full((l1c.shape[0],), L2A, device=dev, dtype=torch.long))

            def rgb(x):  # (B,4,H,W) bands [B02,B03,B04,B8A] -> RGB [B04,B03,B02]
                im = x[:, [2, 1, 0]].clamp(0, 1).permute(0, 2, 3, 1).detach().cpu().numpy()
                return (im / max(im.max(), 1e-6) * 255).astype("uint8")
            gt, a, c = rgb(l1c), rgb(r_l1c), rgb(r_l2a)
            for i in range(l1c.shape[0]):
                panel = np.concatenate([gt[i], a[i], c[i]], axis=1)  # [GT | phi=L1C | phi=L2A]
                imageio.imwrite(fig_dir / f"sample_{i}.png", panel)
            print(f"[fig3] wrote {l1c.shape[0]} phi-swap panels -> {fig_dir}")
        except Exception as e:
            print(f"[fig3] skipped ({e})")


if __name__ == "__main__":
    main()
