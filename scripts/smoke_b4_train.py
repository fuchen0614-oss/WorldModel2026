"""plan-b-pvt · local GPU TRAINING smoke for ObsWorldB4 (GPU 4-7 only, synthetic).

Verifies B4 actually TRAINS on the local Blackwell (sm_120) cards before we ship a
full run to the server: forward+backward+optimizer step run, the JEPA+VICReg aux is
wired into the loss and flows gradients, nothing goes NaN, and the surrogate loss
moves. Uses a surrogate forecast loss (MSE) — the real MaskedL2NDVILoss is unchanged
from B0 (already validated) and needs real data, so it runs on the server.

MUST be launched pinned to GPU 4-7 (plan-B's local test cards):
  CUDA_VISIBLE_DEVICES=4,5,6,7 <fastwam-vjepa python> scripts/smoke_b4_train.py
Local = test only; full training goes to the server 8×H200.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from models.plan_b_b4 import ObsWorldB4  # noqa: E402


def fake_batch(dev, B=2, T=30, H=128, W=128):
    return {
        "dynamic": [torch.randn(B, T, 5, H, W, device=dev), torch.randn(B, T, 24, device=dev)],
        "dynamic_mask": [(torch.rand(B, T, 1, H, W, device=dev) < 0.05).float()],
        "static": [torch.randn(B, 5, H, W, device=dev)],
    }


def main():
    if not torch.cuda.is_available():
        print("no CUDA visible — this smoke must run on GPU 4-7"); sys.exit(1)
    dev = torch.device("cuda", 0)  # physical GPU 4 under CUDA_VISIBLE_DEVICES=4,5,6,7
    print("=" * 72)
    print(f"B4 local GPU training smoke on: {torch.cuda.get_device_name(0)}")
    print("=" * 72)

    hp = contextformer6m_hparams(pvt_pretrained=False)
    model = ObsWorldB4(hp, contract_cfg={"state_dim": 256, "n_products": 2}).to(dev).train()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    lambdas = SimpleNamespace(dyn=1.0, vic=1.0)
    data = fake_batch(dev)

    # snapshot backbone weights to confirm the forecast backbone actually updates
    w0 = model.q.core.blocks[-1].mlp.fc2.weight.detach().clone()

    losses = []
    for step in range(6):
        opt.zero_grad(set_to_none=True)
        preds, aux = model(data, lambdas=lambdas)          # (B,30,1,H,W) full-seq + aux
        target = torch.zeros_like(preds)                    # surrogate forecast target
        floss = F.mse_loss(preds, target)
        loss = floss + aux["total"]
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        lg = aux["logs"]
        print(f"[step {step}] loss={loss.item():.5f} forecast={floss.item():.5f} "
              f"latent_future={float(lg['latent_future']):.5f} "
              f"vic_var={float(lg['vic_var']):.4f} vic_cov={float(lg['vic_cov']):.4f}")
        losses.append(loss.item())

    # checks
    finite = all(torch.isfinite(torch.tensor(l)) for l in losses)
    moved = abs(losses[-1] - losses[0]) > 1e-6
    backbone_updated = (model.q.core.blocks[-1].mlp.fc2.weight.detach() - w0).abs().sum().item() > 0

    # recoverable training step: dyn=vic=0 -> aux total exactly 0
    _, aux0 = model(data, lambdas=SimpleNamespace(dyn=0.0, vic=0.0))
    aux0_zero = float(aux0["total"].item()) == 0.0

    print("-" * 72)
    for name, ok in [
        ("6 steps ran, all losses finite", finite),
        ("loss moved (training has effect)", moved),
        ("forecast backbone weights updated", backbone_updated),
        ("lambdas=0 -> aux total == 0 (recoverable)", aux0_zero),
    ]:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    allok = finite and moved and backbone_updated and aux0_zero
    print("-" * 72)
    print(f"RESULT: {'ALL PASS' if allok else 'FAIL'}")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
