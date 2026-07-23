"""plan-b-pvt · TerraState (B4) stage-1.5 CPU synthetic smoke — 13 checks.

CPU-only (CUDA_VISIBLE_DEVICES=""), no data, no training. Extends the stage-1
wiring checks with the stage-1.5 corrections: composed PREDICTION (not just latent),
B0-protocol MASKED losses, and a T-only weather-intervention interface.

  1  init full B4 prediction == B0 (gate zero-init, bit-exact);
  2  future satellite truth does NOT change z_t;
  3a future weather does NOT change z_t; 3b but DOES change T's future state;
  4  direct vs composed are two different computation paths;
  5  masked residual/endpoint gradient reaches WeatherEncoder, T, O_δ (anti-starvation);
  6  non-zero gate: cutting T changes the final prediction (load-bearing);
  7  save/load b4_state_dict -> byte-identical predictions;
  8  full24 dims + future time slice correct;
  9  no local GPU used;
  10 composed state DECODES to a real prediction (≠B0 when gate>0) + endpoint supervised;
  11 masked NDVI loss ignores cloudy pixels (same protocol as B0);
  12 T-only intervention: B0 fixed across matched/null/shuffled, output changes;
  13 exporter load_b4 rebuilds from contract_cfg (round-trip) and REFUSES core-only.

Run: CUDA_VISIBLE_DEVICES="" <fastwam-vjepa python> scripts/smoke_b4.py
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import PVTContextformerQ, contextformer6m_hparams  # noqa: E402
from models.plan_b_b4 import ObsWorldB4  # noqa: E402
from eval.export_b4_predictions import load_b4  # noqa: E402


def fake_data(B=2, T=30, H=128, W=128, seed=0):
    g = torch.Generator().manual_seed(seed)
    dyn = torch.randn(B, T, 5, H, W, generator=g)
    dyn[:, :, 0] = torch.tanh(dyn[:, :, 0])                       # NDVI channel 0 in (-1,1)
    return {
        "dynamic": [dyn, torch.randn(B, T, 24, generator=g)],
        "dynamic_mask": [(torch.rand(B, T, 1, H, W, generator=g) < 0.05).float()],
        "static": [torch.randn(B, 5, H, W, generator=g)],
        "landcover": torch.randint(10, 41, (B, 1, H, W), generator=g).float(),
    }


def main():
    hp = contextformer6m_hparams(pvt_pretrained=False)
    cl, tl = hp.context_length, hp.target_length
    model = ObsWorldB4(hp, contract_cfg={"state_dim": 256, "freeze_b0": True}).eval()
    data = fake_data()
    checks = []

    # 1. init B4 == B0
    with torch.no_grad():
        preds = model.forecast(data)
        b0 = PVTContextformerQ(hp).eval(); b0.load_state_dict(model.q.state_dict())
        preds_b0 = b0(data, pred_start=cl, preds_length=tl)
    d1 = (preds - preds_b0).abs().max().item()
    checks.append(("init B4 forecast == B0 (gate=0, bit-exact)", d1 == 0.0, f"max|Δ|={d1:.2e}"))

    # 2. future satellite truth does not change z_t
    with torch.no_grad():
        _, z_t = model._b0_and_state(data)
        d_fut = fake_data(seed=1)
        d_fut["dynamic"][0][:, :cl] = data["dynamic"][0][:, :cl]
        d_fut["dynamic"][1] = data["dynamic"][1]; d_fut["static"] = data["static"]
        d_fut["dynamic_mask"][0][:, :cl] = data["dynamic_mask"][0][:, :cl]
        _, z_t2 = model._b0_and_state(d_fut)
    d2 = (z_t - z_t2).abs().max().item()
    checks.append(("future satellite truth does NOT change z_t", d2 == 0.0, f"max|Δ|={d2:.2e}"))

    # 3. future weather: z_t unchanged, T future state changes
    with torch.no_grad():
        w2 = data["dynamic"][1].clone(); w2[:, cl:] = torch.randn_like(w2[:, cl:])
        d_w = {"dynamic": [data["dynamic"][0], w2], "dynamic_mask": data["dynamic_mask"],
               "static": data["static"], "landcover": data["landcover"]}
        _, z_t_w = model._b0_and_state(d_w)
        geo, uf = model._geo_weather(data); _, uf_w = model._geo_weather(d_w)
        zdir, zdir_w = model.direct_state(z_t, uf, geo, tl), model.direct_state(z_t, uf_w, geo, tl)
    checks.append(("future weather does NOT change z_t", (z_t - z_t_w).abs().max().item() == 0.0,
                   f"max|Δ|={(z_t - z_t_w).abs().max().item():.2e}"))
    checks.append(("future weather DOES change T future state", (zdir - zdir_w).abs().max().item() > 1e-6,
                   f"max|Δ|={(zdir - zdir_w).abs().max().item():.2e}"))

    # 4. direct vs composed different paths
    with torch.no_grad():
        d4 = (model.direct_state(z_t, uf, geo, 10) - model.composed_state(z_t, uf, geo, 4, 6)).abs().max().item()
    checks.append(("direct(10) != composed(4,6) (non-trivial)", d4 > 1e-6, f"max|Δ|={d4:.2e}"))

    # 8. full24 dims + future slice
    ok8 = (data["dynamic"][1].shape[-1] == 24 and model.driver_dim == 24 and tuple(uf.shape) == (2, tl, 24)
           and tuple(model._direct_residual(z_t, uf, geo, 2, 128, 128).shape) == (2, tl, 1, 128, 128))
    checks.append(("full24 dims + future slice (B,20,24)&resid", ok8, f"uf={tuple(uf.shape)}"))

    # 11. masked NDVI loss ignores cloudy pixels (same protocol as B0)
    with torch.no_grad():
        p = torch.randn(2, tl, 1, 128, 128)
        la, _ = model.ndvi_loss(p, data)
        p2 = p.clone(); cloudy = (data["dynamic_mask"][0][:, cl:cl + tl] >= 1.0)
        p2[cloudy] = p2[cloudy] + 5.0
        lb, _ = model.ndvi_loss(p2, data)
    checks.append(("masked loss ignores cloudy pixels (B0 protocol)", abs(la.item() - lb.item()) < 1e-6,
                   f"Δloss={abs(la.item() - lb.item()):.2e}"))

    # 5 + 10. masked losses -> gradient to WeatherEncoder/T/O_δ; composed endpoint supervised
    lam = SimpleNamespace(fore=1.0, resid=1.0, cmp=1.0, con=1.0, vic=1.0)
    _, aux = model(data, lambdas=lam)
    aux["total"].backward()
    def gnorm(mod):
        gs = [p.grad for p in mod.parameters() if p.grad is not None]
        return (sum(g.abs().sum().item() for g in gs), all(torch.isfinite(g).all() for g in gs)) if gs else (0.0, False)
    (gw, fw), (gt, ft), (go, fo) = gnorm(model.weather_enc), gnorm(model.transition), gnorm(model.o_delta)
    checks.append(("masked grad reaches WeatherEncoder & T & O_δ", gw > 0 and gt > 0 and go > 0 and fw and ft and fo,
                   f"|g| we={gw:.2e} T={gt:.2e} Oδ={go:.2e}"))
    ok10a = "cmp_ep" in aux["logs"] and "con" in aux["logs"] and torch.isfinite(aux["logs"]["cmp_ep"])
    with torch.no_grad():
        model.gate.data.fill_(1.0)
        pb0, z_tg = model._b0_and_state(data); geo_g, uf_g = model._geo_weather(data)
        yc = model.composed_prediction(pb0, z_tg, uf_g, geo_g, 10, 10, 2, 128, 128)
        ok10b = (yc - pb0[:, 19]).abs().max().item() > 1e-6      # composed decode contributes (gate>0)
        model.gate.data.fill_(0.0)
    checks.append(("composed DECODES to prediction (≠B0) + endpoint supervised", bool(ok10a and ok10b),
                   f"cmp_ep={float(aux['logs'].get('cmp_ep', -1)):.4f} Δcmp={(yc - pb0[:, 19]).abs().max().item():.2e}"))

    # 6. non-zero gate: cutting T changes the forecast (load-bearing)
    with torch.no_grad():
        model.gate.data.fill_(1.0)
        preds_T = model.forecast(data)
        ws, bs = model.transition.net[-1].weight.data.clone(), model.transition.net[-1].bias.data.clone()
        model.transition.net[-1].weight.data.zero_(); model.transition.net[-1].bias.data.zero_()  # T -> identity
        preds_noT = model.forecast(data)
        model.transition.net[-1].weight.data.copy_(ws); model.transition.net[-1].bias.data.copy_(bs)
        model.gate.data.fill_(0.0)
    d6 = (preds_T - preds_noT).abs().max().item()
    checks.append(("gate>0: cutting T changes forecast (load-bearing)", d6 > 1e-6, f"max|Δ|={d6:.2e}"))

    # 12. T-only weather intervention: B0 fixed, output changes
    with torch.no_grad():
        model.gate.data.fill_(1.0)
        b0m, ym = model.forecast_weather(data, "matched")
        b0n, yn = model.forecast_weather(data, "mean")        # climatological (normalized-zero) forcing
        b0s, ys = model.forecast_weather(data, "shuffled")
        model.gate.data.fill_(0.0)
    b0_fixed = (b0m - b0n).abs().max().item() == 0.0 and (b0m - b0s).abs().max().item() == 0.0
    mean_moved = (ym - yn).abs().max().item() > 1e-6          # climatological forcing moves output
    shuf_moved = (ym - ys).abs().max().item() > 1e-6          # roll -> deterministic non-identity shuffle
    checks.append(("T-only: B0 fixed, mean+shuffled change output", b0_fixed and mean_moved and shuf_moved,
                   f"B0Δ={(b0m - b0n).abs().max().item():.0e} meanΔ={(ym - yn).abs().max().item():.2e} "
                   f"shufΔ={(ym - ys).abs().max().item():.2e}"))

    # 14. parameterizable multi-partition composition interface
    with torch.no_grad():
        model.gate.data.fill_(1.0)
        parts = model.composed_predictions(data, partitions=[(3, 7), (4, 6), (5, 5)])
        ok14 = (set(parts.keys()) == {(3, 7), (4, 6), (5, 5)}
                and all(tuple(v[0].shape) == (2, 1, 128, 128) and tuple(v[1].shape) == (2, 1, 128, 128)
                        for v in parts.values())
                and (parts[(3, 7)][0] - parts[(3, 7)][1]).abs().max().item() > 1e-6)
        model.gate.data.fill_(0.0)
    checks.append(("multi-partition composed_predictions interface", bool(ok14),
                   f"parts={sorted(parts.keys())}"))

    # 7 + 13. checkpoint round-trip via exporter load_b4; refuse core-only
    with torch.no_grad():
        model.gate.data.fill_(0.5)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "b4.pt"
            torch.save({"b4_state_dict": model.state_dict(),
                        "contract_cfg": {"state_dim": 256, "freeze_b0": True}}, p)
            m2 = load_b4(str(p), "cpu")
            d7 = (model.forecast(data) - m2.forecast(data)).abs().max().item()
            core_p = Path(td) / "core.pt"
            torch.save({"core_state_dict": model.q.core.state_dict()}, core_p)
            refused = False
            try:
                load_b4(str(core_p), "cpu")
            except ValueError:
                refused = True
        model.gate.data.fill_(0.0)
    checks.append(("b4 round-trip identical + exporter refuses core-only", d7 == 0.0 and refused,
                   f"max|Δ|={d7:.2e} refused={refused}"))

    # 9. no local GPU
    checks.append(("CPU-only (no local GPU)", (not torch.cuda.is_available())
                   and all(not p.is_cuda for p in model.parameters()), f"cuda={torch.cuda.is_available()}"))

    p_b0, p_b4 = sum(p.numel() for p in model.q.parameters()), model.num_params()
    print("=" * 78)
    print(f"params: B0={p_b0/1e6:.2f}M  B4={p_b4/1e6:.2f}M  branch(+)={(p_b4-p_b0)/1e6:.2f}M  "
          f"trainable={sum(p.numel() for p in model.trainable_parameters())/1e6:.2f}M")
    print("-" * 78)
    allok = True
    for name, ok, detail in checks:
        allok &= bool(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {name:<52} {detail}")
    print("-" * 78)
    print(f"RESULT: {'ALL PASS' if allok else 'FAIL'}  ({sum(c[1] for c in checks)}/{len(checks)})")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
