"""plan-b-pvt · current-code B4 AUDIT (CPU, synthetic) with HARD gates + state diagnostics.

Reports (raw, not just PASS/FAIL): fore/resid/cmp/con/25·vic_var+vic_cov raw+weighted
shares, per-module gradients, gate, state residual fraction, T-cut output delta, and
z_t / z_{t+h} anti-collapse diagnostics. AUDIT OK only if ALL hard gates pass — a zero
gradient, T-cut Δ=0, or VICReg dominating prediction losses now FAILS the audit.

NOTE: manually setting gate=1 here only proves the T→output WIRING is live; it does NOT
prove the TRAINED state is load-bearing (that needs real training + a delete-T ablation
showing an R² drop). Overwrites nothing.

Run: CUDA_VISIBLE_DEVICES="" <fastwam-vjepa python> scripts/audit_b4.py
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from models.plan_b_b4 import ObsWorldB4  # noqa: E402
from eval.export_b4_predictions import load_b4  # noqa: E402


def fake_data(B=2, T=30, H=128, W=128, seed=0):
    g = torch.Generator().manual_seed(seed)
    dyn = torch.randn(B, T, 5, H, W, generator=g); dyn[:, :, 0] = torch.tanh(dyn[:, :, 0])
    return {"dynamic": [dyn, torch.randn(B, T, 24, generator=g)],
            "dynamic_mask": [(torch.rand(B, T, 1, H, W, generator=g) < 0.05).float()],
            "static": [torch.randn(B, 5, H, W, generator=g)],
            "landcover": torch.randint(10, 41, (B, 1, H, W), generator=g).float()}


def gnorm(mod):
    gs = [p.grad for p in mod.parameters() if p.grad is not None]
    return (sum(g.norm().item() ** 2 for g in gs) ** 0.5, all(torch.isfinite(g).all() for g in gs)) if gs else (0.0, False)


def loss_shares(model, data, lam):
    _, aux = model(data, lambdas=lam); lg = aux["logs"]
    r = {k: float(lg.get(k, 0.0)) for k in ("fore", "resid", "cmp_ep", "dir_ep", "con", "vic_var", "vic_cov")}
    w = {"fore": lam.fore * r["fore"], "resid": lam.resid * r["resid"],
         "cmp": lam.cmp * (r["cmp_ep"] + r["dir_ep"]), "con": lam.con * r["con"],
         "vic": lam.vic * (25.0 * r["vic_var"] + r["vic_cov"])}
    return r, w, float(aux["total"]), aux


def main():
    hp = contextformer6m_hparams(pvt_pretrained=False)
    model = ObsWorldB4(hp, contract_cfg={"state_dim": 256, "freeze_b0": True}).train()
    data = fake_data()
    hard = {}
    print("=" * 86)
    print(f"B4 AUDIT  B0={sum(p.numel() for p in model.q.parameters())/1e6:.2f}M B4={model.num_params()/1e6:.2f}M "
          f"trainable={sum(p.numel() for p in model.trainable_parameters())/1e6:.2f}M")
    print(f"          train_partitions={model.partitions}  heldout={model.heldout_partitions}")

    # --- loss balance: all-on λ_vic=1 (shows the pathology) vs recommended Phase-I ---
    finite_all = True
    for tag, lam in [("all-on λ_vic=1.0", SimpleNamespace(fore=1., resid=1., cmp=1., con=1., vic=1.0)),
                     ("PHASE-I fore/resid, vic=0.05", SimpleNamespace(fore=1., resid=1., cmp=0., con=0., vic=0.05))]:
        model.zero_grad(set_to_none=True)
        r, w, total, aux = loss_shares(model, data, lam)
        finite_all &= all(torch.isfinite(torch.tensor(v)) for v in list(r.values()) + [total])
        pred = w["fore"] + w["resid"] + w["cmp"] + w["con"]
        aux["total"].backward()
        print("-" * 86)
        print(f"[{tag}]")
        print(f"  RAW      fore={r['fore']:.4f} resid={r['resid']:.4f} cmp_ep={r['cmp_ep']:.4f} "
              f"dir_ep={r['dir_ep']:.4f} con={r['con']:.4f} vic_var={r['vic_var']:.4f} vic_cov={r['vic_cov']:.4f}")
        print(f"  WEIGHTED fore={w['fore']:.3f} resid={w['resid']:.3f} cmp={w['cmp']:.3f} con={w['con']:.3f} "
              f"vic={w['vic']:.3f}  TOTAL={total:.3f}  vic/pred={w['vic']/max(pred,1e-9):.2f}x")
        (gw, fw), (gt, ft), (go, fo), (gp, fp) = (gnorm(model.weather_enc), gnorm(model.transition),
                                                  gnorm(model.o_delta), gnorm(model.projector))
        print(f"  grad     weather={gw:.2e} T={gt:.2e} Oδ={go:.2e} proj={gp:.2e} "
              f"fuse={gnorm(model.fuse)[0]:.2e} geo={gnorm(model.geo_enc)[0]:.2e} "
              f"gate={model.gate.grad.abs().item() if model.gate.grad is not None else 0:.2e}")
        if tag.startswith("PHASE"):
            hard["grads_nonzero_finite"] = min(gw, gt, go, gp) > 0 and fw and ft and fo and fp
            hard["vic_not_dominate_predictions"] = w["vic"] < pred
    hard["all_losses_finite"] = finite_all

    # --- gate / residual fraction / T-cut (gate=1: WIRING evidence only) ---
    with torch.no_grad():
        model.gate.data.fill_(1.0)
        preds, preds_b0, residual, *_ = model.forecast(data, want_state=True)
        resid_frac = (model.gate * residual).abs().mean().item() / (preds.abs().mean().item() + 1e-9)
        preds_T = model.forecast(data)
        ws, bs = model.transition.net[-1].weight.data.clone(), model.transition.net[-1].bias.data.clone()
        model.transition.net[-1].weight.data.zero_(); model.transition.net[-1].bias.data.zero_()
        tcut = (preds_T - model.forecast(data)).abs().max().item()
        model.transition.net[-1].weight.data.copy_(ws); model.transition.net[-1].bias.data.copy_(bs)
    print("-" * 86)
    print(f"[gate=1 WIRING]  residual fraction ‖gate·resid‖/‖ŷ‖={resid_frac:.4e}  T-cut Δ={tcut:.4e}  "
          f"(wiring only; trained load-bearing needs a real delete-T R² drop)")
    hard["residual_fraction_nonzero"] = resid_frac > 0
    hard["tcut_above_tol"] = tcut > 1e-6

    # --- z_t / z_{t+h} anti-collapse diagnostics (gate=1) ---
    with torch.no_grad():
        _, z_t = model._b0_and_state(data)
        geo, u_future = model._geo_weather(data)
        print("-" * 86)
        print(f"[state diag]  z_t  std={model.state_std(z_t):.4f} eff_rank={model.effective_rank(z_t):.1f}/256")
        for h in (1, 5, 10, 20):
            zd = model.direct_state(z_t, u_future, geo, h)
            print(f"  direct z_{h:>2}  std={model.state_std(zd):.4f} eff_rank={model.effective_rank(zd):.1f} "
                  f"Δ(z_h−z_t)={ (zd - z_t).abs().mean().item():.4f}")
        z_c = model.composed_state(z_t, u_future, geo, 5, 5)
        z_d10 = model.direct_state(z_t, u_future, geo, 10)
        print(f"  composed(5,5)→10  std={model.state_std(z_c):.4f} eff_rank={model.effective_rank(z_c):.1f} "
              f"consistency Δ(dir−cmp)={(z_d10 - z_c).abs().mean().item():.4f}")
        # weather sensitivity of state & output (matched/mean/shuffled)
        zm = model.direct_state(z_t, model._intervene(u_future, "mean"), geo, 10)
        zs = model.direct_state(z_t, model._intervene(u_future, "shuffled"), geo, 10)
        model.gate.data.fill_(1.0)
        _, y_ma = model.forecast_weather(data, "matched")
        _, y_me = model.forecast_weather(data, "mean")
        _, y_sh = model.forecast_weather(data, "shuffled")
        model.gate.data.fill_(0.0)
        print(f"  weather-sens  stateΔ mean={ (z_d10 - zm).abs().mean().item():.4f} "
              f"shuffled={(z_d10 - zs).abs().mean().item():.4f} | outputΔ mean={(y_ma - y_me).abs().max().item():.2e} "
              f"shuffled={(y_ma - y_sh).abs().max().item():.2e}")
        print("  (diagnose first; add a z_h VICReg loss ONLY if z_h collapses — do not over-regularize)")

    # --- checkpoint save/load/export round-trip + refuse core-only ---
    with torch.no_grad():
        model.gate.data.fill_(0.37)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "b4.pt"
            torch.save({"b4_state_dict": model.state_dict(), "contract_cfg": model.config()}, p)
            m2 = load_b4(str(p), "cpu")
            rt = (model.forecast(data) - m2.forecast(data)).abs().max().item()
            cp = Path(td) / "core.pt"; torch.save({"core_state_dict": model.q.core.state_dict()}, cp)
            refused = False
            try:
                load_b4(str(cp), "cpu")
            except ValueError:
                refused = True
        model.gate.data.fill_(0.0)
    print("-" * 86)
    print(f"[ckpt]  round-trip max|Δ|={rt:.2e}  refuse-core-only={refused}  contract_cfg keys={sorted(model.config())}")
    hard["ckpt_roundtrip_exact"] = rt == 0.0
    hard["core_only_refused"] = refused

    # --- HARD GATES ---
    print("=" * 86)
    allok = True
    for k, v in hard.items():
        allok &= bool(v)
        print(f"[{'PASS' if v else 'FAIL'}] hard gate: {k}")
    print("-" * 86)
    print(f"AUDIT {'OK' if allok else 'FAIL'}")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
