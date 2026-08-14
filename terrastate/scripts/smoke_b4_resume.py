"""plan-b-pvt · minimal RESUME smoke (CPU synthetic). A freeze_b0=true Phase-I checkpoint,
resumed with a CLI override --freeze-b0 0, must:
  * actually UNFREEZE q (all q params trainable);
  * keep predictions byte-identical (weights unchanged; freeze only affects the grad path);
  * use differential LR (q/backbone = branch_lr*0.1, branch = branch_lr) — same grouping as
    train_plan_b_b4.py;
  * after one backward, give BOTH q and T/O finite non-zero gradients.

Run: CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
       <fastwam-vjepa python> scripts/smoke_b4_resume.py
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


def fake_data(B=2, T=30, H=128, W=128, seed=0):
    g = torch.Generator().manual_seed(seed)
    dyn = torch.randn(B, T, 5, H, W, generator=g); dyn[:, :, 0] = torch.tanh(dyn[:, :, 0])
    return {"dynamic": [dyn, torch.randn(B, T, 24, generator=g)],
            "dynamic_mask": [(torch.rand(B, T, 1, H, W, generator=g) < 0.05).float()],
            "static": [torch.randn(B, 5, H, W, generator=g)],
            "landcover": torch.randint(10, 41, (B, 1, H, W), generator=g).float()}


def make_opt(model, branch_lr):
    """SAME module-identity grouping as train_plan_b_b4.py."""
    q_params = [p for p in model.q.parameters() if p.requires_grad]
    branch_params = [p for n, p in model.named_parameters() if not n.startswith("q.") and p.requires_grad]
    groups = []
    if branch_params:
        groups.append({"params": branch_params, "lr": branch_lr, "name": "branch"})
    if q_params:
        groups.append({"params": q_params, "lr": branch_lr * 0.1, "name": "q_backbone"})
    return torch.optim.AdamW(groups, betas=(0.9, 0.999)), groups


def gn(mod):
    gs = [p.grad for p in mod.parameters() if p.grad is not None]
    return (sum(g.abs().sum().item() for g in gs), all(torch.isfinite(g).all() for g in gs)) if gs else (0.0, False)


def main():
    hp = contextformer6m_hparams(pvt_pretrained=False)
    data = fake_data()
    branch_lr = 1e-4
    m1 = ObsWorldB4(hp, contract_cfg={"state_dim": 256, "freeze_b0": True}).eval()  # Phase I (frozen B0)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "phase1.pt"
        torch.save({"b4_state_dict": m1.state_dict(), "contract_cfg": m1.config(), "step": 42}, p)
        ck = torch.load(p, map_location="cpu", weights_only=False)
        cfg = dict(ck["contract_cfg"]); cfg["freeze_b0"] = False                    # CLI override
        m2 = ObsWorldB4(hp, contract_cfg=cfg)
        m2.load_state_dict(ck["b4_state_dict"], strict=True)

    checks = []
    n_q_tr, n_q_tot = sum(p.requires_grad for p in m2.q.parameters()), sum(1 for _ in m2.q.parameters())
    checks.append((f"resume+freeze_b0=0 -> q trainable {n_q_tr}/{n_q_tot}", n_q_tr == n_q_tot))

    opt, groups = make_opt(m2, branch_lr)
    lrs = {g["name"]: g["lr"] for g in groups}
    qn = sum(pp.numel() for g in groups if g["name"] == "q_backbone" for pp in g["params"])
    print(f"opt groups: {[(g['name'], len(g['params']), g['lr']) for g in groups]}  q-group params={qn/1e6:.3f}M")
    checks.append((f"q group lr == branch_lr*0.1 ({lrs.get('q_backbone')})",
                   abs(lrs.get("q_backbone", 0) - branch_lr * 0.1) < 1e-12))
    checks.append((f"branch group lr == branch_lr ({lrs.get('branch')})",
                   abs(lrs.get("branch", 0) - branch_lr) < 1e-12))

    with torch.no_grad():
        m1.eval(); m2.eval()
        d = (m1.forecast(data) - m2.forecast(data)).abs().max().item()
    checks.append((f"resumed forecast == Phase-I forecast (max|Δ|={d:.2e})", d == 0.0))

    m2.train()
    opt.zero_grad(set_to_none=True)
    _, aux = m2(data, lambdas=SimpleNamespace(fore=1.0, resid=1.0, cmp=0.0, con=0.0, vic=0.05))
    aux["total"].backward()
    (gq, fq), (gt, ft), (go, fo) = gn(m2.q), gn(m2.transition), gn(m2.o_delta)
    checks.append((f"q finite non-zero grad (|g|={gq:.2e})", gq > 0 and fq))
    checks.append((f"T finite non-zero grad (|g|={gt:.2e})", gt > 0 and ft))
    checks.append((f"O_delta finite non-zero grad (|g|={go:.2e})", go > 0 and fo))

    print("-" * 74)
    allok = True
    for nm, ok in checks:
        allok &= bool(ok); print(f"[{'PASS' if ok else 'FAIL'}] {nm}")
    print("-" * 74); print(f"RESULT: {'ALL PASS' if allok else 'FAIL'}")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
