"""plan-b-pvt · TerraState (B4) synthetic TRAINING smoke on the CURRENT protocol.

Validates one training step of the NEW model/trainer API (masked fore/resid/cmp/con/vic
losses, landcover, context-only state, multi-partition composition) WITHOUT real data.
Device-agnostic: uses CPU when no GPU is visible — run this round with
CUDA_VISIBLE_DEVICES="" so it stays CPU-only.

  CUDA_VISIBLE_DEVICES="" <fastwam-vjepa python> scripts/smoke_b4_train.py
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from models.plan_b_b4 import ObsWorldB4  # noqa: E402


def fake_batch(dev, B=2, T=30, H=128, W=128, seed=0):
    g = torch.Generator().manual_seed(seed)
    dyn = torch.randn(B, T, 5, H, W, generator=g); dyn[:, :, 0] = torch.tanh(dyn[:, :, 0])
    return {
        "dynamic": [dyn.to(dev), torch.randn(B, T, 24, generator=g).to(dev)],
        "dynamic_mask": [(torch.rand(B, T, 1, H, W, generator=g) < 0.05).float().to(dev)],
        "static": [torch.randn(B, 5, H, W, generator=g).to(dev)],
        "landcover": torch.randint(10, 41, (B, 1, H, W), generator=g).float().to(dev),
    }


def main():
    dev = torch.device("cuda", 0) if torch.cuda.is_available() else torch.device("cpu")
    name = torch.cuda.get_device_name(0) if dev.type == "cuda" else "CPU"
    print("=" * 74); print(f"B4 TerraState training smoke on: {name}"); print("=" * 74)

    hp = contextformer6m_hparams(pvt_pretrained=False)
    model = ObsWorldB4(hp, contract_cfg={"state_dim": 256, "freeze_b0": True,
                                         "partitions": [(3, 7), (4, 6), (5, 5), (10, 10)]}).to(dev).train()
    opt = torch.optim.AdamW(model.trainable_parameters(), lr=1e-3)
    lam = SimpleNamespace(fore=1.0, resid=1.0, cmp=1.0, con=1.0, vic=0.05)  # vic 0.05: audit-balanced
    data = fake_batch(dev)

    w0 = model.o_delta.weight.detach().clone()
    q0 = next(iter(model.q.parameters())).detach().clone()
    losses = []
    for step in range(6):
        opt.zero_grad(set_to_none=True)
        preds, aux = model(data, lambdas=lam)
        loss = aux["total"]; loss.backward()
        torch.nn.utils.clip_grad_norm_(model.trainable_parameters(), 1.0)
        opt.step()
        lg = aux["logs"]
        gn = lambda m: sum(p.grad.norm().item() ** 2 for p in m.parameters() if p.grad is not None) ** 0.5
        print(f"[step {step}] loss={loss.item():.5f} fore={float(lg['fore']):.4f} resid={float(lg['resid']):.4f} "
              f"cmp={float(lg.get('cmp_ep', 0)):.4f} vic={float(lg['vic_var']):.3f} gate={float(lg['gate']):.2e} "
              f"| grad we={gn(model.weather_enc):.1e} T={gn(model.transition):.1e} Oδ={gn(model.o_delta):.1e}")
        losses.append(loss.item())

    finite = all(torch.isfinite(torch.tensor(l)) for l in losses)
    moved = abs(losses[-1] - losses[0]) > 1e-6
    branch_updated = (model.o_delta.weight.detach() - w0).abs().sum().item() > 0
    b0_frozen = (next(iter(model.q.parameters())).detach() - q0).abs().sum().item() == 0
    _, aux0 = model(data, lambdas=SimpleNamespace(fore=0., resid=0., cmp=0., con=0., vic=0.))
    recoverable = float(aux0["total"].item()) == 0.0

    print("-" * 74)
    checks = [("6 steps finite", finite), ("loss moved", moved),
              ("branch (O_δ) updated", branch_updated), ("B0 frozen (unchanged)", b0_frozen),
              ("lambdas=0 -> aux total==0 (recoverable)", recoverable),
              ("CPU-only this round", dev.type == "cpu")]
    for nm, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {nm}")
    allok = all(ok for _, ok in checks[:5])   # device line is informational
    print("-" * 74); print(f"RESULT: {'ALL PASS' if allok else 'FAIL'}  (device={dev.type})")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
