"""plan-b-pvt · local CPU smoke for B4 = ObsWorldB4 (no data / no GPU / no xarray).

Verifies the load-bearing contracts before we spend a single GPU-hour:
  1. forecast forward runs, shape (B, target, 1, H, W), finite;
  2. STRONG-BASELINE-RECOVERABLE: B4's forecast == a bare ContextFormer (B0) with
     the same weights, byte-for-byte -> the world model does not perturb B0;
  3. lambdas=0  -> contract loss is EXACTLY 0 (recoverable);
  4. lambdas.dyn>0 -> a NON-trivial finite latent-future loss (real dynamics), and
     the returned preds are unchanged (design A: aux never touches the forecast);
  5. PhiRenderer O(s, φ) forward shape + φ FiLM is identity at init;
  6. report params + world-model overhead vs B0.

Run:
  /mnt/data/public_tools/miniconda3/envs/fastwam-vjepa/bin/python scripts/smoke_b4.py
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import PVTContextformerQ, contextformer6m_hparams  # noqa: E402
from models.plan_b_b4 import ObsWorldB4  # noqa: E402


def fake_data(B=1, T=30, H=128, W=128):
    torch.manual_seed(0)
    return {
        "dynamic": [torch.randn(B, T, 5, H, W), torch.randn(B, T, 24)],
        "dynamic_mask": [(torch.rand(B, T, 1, H, W) < 0.05).float()],
        "static": [torch.randn(B, 5, H, W)],
    }


def main():
    print("=" * 72)
    print("B4 (ObsWorldB4) local CPU smoke")
    print("=" * 72)
    hp = contextformer6m_hparams(pvt_pretrained=False)
    cl, tl = hp.context_length, hp.target_length
    data = fake_data()

    model = ObsWorldB4(hp, contract_cfg={"state_dim": 256, "n_products": 2}).eval()

    checks = []

    # 1. forecast shape + finite
    with torch.no_grad():
        preds = model(data, pred_start=cl, preds_length=tl)
    ok_shape = tuple(preds.shape) == (1, tl, 1, 128, 128) and torch.isfinite(preds).all().item()
    checks.append(("forecast shape (1,20,1,128,128) + finite", ok_shape, tuple(preds.shape)))

    # 2. strong-baseline-recoverable: == bare ContextFormer (B0) with same weights
    b0 = PVTContextformerQ(hp).eval()
    b0.load_state_dict(model.q.state_dict())
    with torch.no_grad():
        preds_b0 = b0(data, pred_start=cl, preds_length=tl)
    max_abs = (preds - preds_b0).abs().max().item()
    checks.append(("B4 forecast == B0 (max|Δ|<1e-5)", max_abs < 1e-5, f"max|Δ|={max_abs:.2e}"))

    # 3. lambdas=0 -> total loss exactly 0
    with torch.no_grad():
        preds0, aux0 = model(data, pred_start=cl, preds_length=tl, lambdas=SimpleNamespace(dyn=0.0))
    z0 = float(aux0["total"].item())
    checks.append(("lambdas.dyn=0 -> total loss == 0", z0 == 0.0, f"total={z0}"))

    # 4. lambdas.dyn>0 & vic>0 -> non-trivial finite JEPA latent-future + VICReg; preds unchanged
    preds1, aux1 = model(data, pred_start=cl, preds_length=tl, lambdas=SimpleNamespace(dyn=1.0, vic=1.0))
    lf = float(aux1["logs"]["latent_future"].item())
    ok_dyn = torch.isfinite(aux1["total"]).item() and lf > 0.0
    checks.append(("dyn=1 -> JEPA latent_future>0 & finite", ok_dyn, f"latent_future={lf:.4e}"))
    vv, vc = float(aux1["logs"]["vic_var"].item()), float(aux1["logs"]["vic_cov"].item())
    ok_vic = vv >= 0.0 and vc >= 0.0 and vv < 1e3 and vc < 1e3
    checks.append(("vic=1 -> VICReg var+cov finite (anti-collapse)", ok_vic, f"var={vv:.3f} cov={vc:.3f}"))
    with torch.no_grad():
        same_preds = torch.allclose(preds, preds1, atol=1e-6)
    checks.append(("aux does NOT change forecast (design A)", same_preds, f"allclose={same_preds}"))
    # gradient actually flows into the transition (JEPA) AND the projector (VICReg). NB: the
    # transition's last layer is zero-init (identity start), which blocks grad to earlier
    # layers on step 0 — so check the WHOLE module, not net[0].
    aux1["total"].backward()
    tg = [p.grad for p in model.transition.parameters() if p.grad is not None]
    pg = [p.grad for p in model.projector.parameters() if p.grad is not None]
    tsum = sum(g.abs().sum().item() for g in tg)
    psum = sum(g.abs().sum().item() for g in pg)
    ok_grad = (len(tg) > 0 and tsum > 0 and all(torch.isfinite(g).all() for g in tg)
               and len(pg) > 0 and psum > 0 and all(torch.isfinite(g).all() for g in pg))
    checks.append(("grad -> transition (JEPA) & projector (VICReg)", ok_grad,
                   f"|g|transition={tsum:.2e} projector={psum:.2e}"))

    # 5. renderer shape + φ identity at init
    s = torch.randn(4, 256)
    with torch.no_grad():
        o0 = model.renderer(s, torch.zeros(4, dtype=torch.long))
        o1 = model.renderer(s, torch.ones(4, dtype=torch.long))
    ok_render = tuple(o0.shape) == (4, 4) and torch.allclose(o0, o1)  # φ FiLM zero-init -> identical
    checks.append(("renderer shape (4,4) + φ identity at init", ok_render, f"shape={tuple(o0.shape)}"))

    # 6. params + overhead
    p_b0 = sum(p.numel() for p in model.q.parameters())
    p_b4 = model.num_params()
    print("-" * 72)
    print(f"params: B0 backbone={p_b0/1e6:.2f}M | B4 total={p_b4/1e6:.2f}M | "
          f"world-model overhead=+{(p_b4-p_b0)/1e6:.2f}M")
    print("-" * 72)
    allok = True
    for name, ok, detail in checks:
        allok &= bool(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {name:<44} {detail}")
    print("-" * 72)
    print(f"RESULT: {'ALL PASS' if allok else 'FAIL'}")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
