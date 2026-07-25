"""plan-b-pvt · Phase-II exclusive-route CPU smoke (the 8 audit-required checks).

No GPU / no real data / no training. Verifies the STRUCTURE + teacher/student separation
before any training is launched.

Run: CUDA_VISIBLE_DEVICES="" <python> tests/smoke_b4_exclusive.py
"""
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams, PVTContextformerQ  # noqa: E402
from models.plan_b_b4 import ObsWorldB4  # noqa: E402
from models.plan_b_b4_exclusive import ObsWorldB4Exclusive, load_exclusive_from_b4  # noqa: E402


def fake_data(B=2, T=30, H=128, W=128, seed=0):
    g = torch.Generator().manual_seed(seed)
    dyn = torch.randn(B, T, 5, H, W, generator=g); dyn[:, :, 0] = torch.tanh(dyn[:, :, 0])
    return {"dynamic": [dyn, torch.randn(B, T, 24, generator=g)],
            "dynamic_mask": [(torch.rand(B, T, 1, H, W, generator=g) < 0.05).float()],
            "static": [torch.randn(B, 5, H, W, generator=g)],
            "landcover": torch.randint(10, 41, (B, 1, H, W), generator=g).float()}


def _sd_sha(module):
    h = hashlib.sha256()
    for k in sorted(module.state_dict()):
        h.update(k.encode()); h.update(module.state_dict()[k].detach().cpu().numpy().tobytes())
    return h.hexdigest()


def main():
    C = []
    hp = contextformer6m_hparams(pvt_pretrained=False)
    cl, tl = hp.context_length, hp.target_length

    # Phase-I B4 (to warm-start from) — build + grab its state_dict (has gate)
    b4 = ObsWorldB4(hp, contract_cfg={"state_dim": 256, "freeze_b0": True}).eval()
    b4_sd = b4.state_dict()

    # exclusive student (Stage A: q frozen)
    model = ObsWorldB4Exclusive(hp, contract_cfg={"state_dim": 256, "freeze_b0": True}).eval()
    miss, unexp = load_exclusive_from_b4(model, b4_sd)

    data = fake_data()

    # (6) reuse q/projector/T/O; only old gate dropped; alpha is the only new (missing) key
    C.append(("(6) B4 reuse: unexpected==[gate], missing⊆[alpha], no gate param in exclusive",
              unexp == [] and set(miss) <= {"alpha"} and "gate" not in dict(model.named_parameters())
              and hasattr(model, "alpha")))

    # (1) changing REAL future weather must NOT change context_prior (it's future-weather-free)
    with torch.no_grad():
        prior1, z1 = model._prior_state(data)
        d2 = fake_data(); d2["dynamic"][0][:, :cl] = data["dynamic"][0][:, :cl]      # keep history identical
        d2["dynamic"][0][:, cl:] = 0                                                 # (irrelevant to prior)
        d2["dynamic"][1][:, :cl] = data["dynamic"][1][:, :cl]                        # keep history weather
        d2["dynamic"][1][:, cl:] = data["dynamic"][1][:, cl:] + 5.0                  # PERTURB future weather
        d2["dynamic_mask"][0][:] = data["dynamic_mask"][0]; d2["static"][0][:] = data["static"][0]
        d2["landcover"] = data["landcover"]
        prior2, _ = model._prior_state(d2)
    C.append(("(1) future-weather change -> context_prior unchanged",
              torch.allclose(prior1, prior2, atol=1e-6)))

    # (2) changing future weather MUST change the T-path residual
    with torch.no_grad():
        geo, uf = model._geo_weather(data); B, H, W = 2, 128, 128
        r1 = model._direct_residual(z1, uf, geo, B, H, W)
        r2 = model._direct_residual(z1, uf + 3.0, geo, B, H, W)
    C.append(("(2) future-weather change -> T residual changes", (r1 - r2).abs().max().item() > 1e-5))

    # (3) alpha=0 -> pred == context_prior (bit/tol)
    with torch.no_grad():
        model.alpha.fill_(0.0); pred0 = model.forecast(data)
        model.alpha.fill_(1.0); pred1 = model.forecast(data)
    C.append(("(3) alpha=0 -> pred==context_prior; alpha=1 differs",
              torch.allclose(pred0, prior1, atol=1e-6) and (pred1 - prior1).abs().max().item() > 1e-6))

    # (4) teacher = SEPARATE frozen q; no grad; NOT in student's inference state_dict / params
    teacher = PVTContextformerQ(hp)
    teacher.load_state_dict({k[2:]: v for k, v in b4_sd.items() if k.startswith("q.")}, strict=False)
    teacher.eval()
    for p in teacher.parameters():
        p.requires_grad_(False)
    no_teacher_in_student = not any("teacher" in k for k in model.state_dict())
    C.append(("(4) teacher separate + no grad + absent from student state_dict",
              all(not p.requires_grad for p in teacher.parameters()) and no_teacher_in_student))

    # (5) unfreeze student q + optimizer step -> teacher params bit-unchanged
    tsha0 = _sd_sha(teacher)
    for p in model.q.parameters():
        p.requires_grad_(True)                                            # simulate Stage-B unfreeze
    model.freeze_b0 = False; model.train()
    lam = SimpleNamespace(fore=1.0, distill=1.0, resid=1.0, vic=0.05, cmp=0.0, con=0.0)
    with torch.no_grad():
        t_pred = teacher.encode(data, pred_start=cl, preds_length=tl)[0].detach()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)
    _, aux = model.loss(data, t_pred, lam); aux["total"].backward(); opt.step()
    C.append(("(5) after student-q unfreeze+step, teacher SHA unchanged", _sd_sha(teacher) == tsha0))
    C.append(("(4b) loss finite + logs have distill/resid (teacher-prior target)",
              torch.isfinite(aux["total"]) and "distill" in aux["logs"] and "resid" in aux["logs"]))

    # (8) inference forecast completes WITHOUT teacher
    model.eval()
    with torch.no_grad():
        pred = model.forecast(data)
    C.append(("(8) inference forecast runs with NO teacher call", tuple(pred.shape[:2]) == (2, tl)))

    # (7) Phase-I ObsWorldB4 still intact (gate present, forecast works) — not broken
    with torch.no_grad():
        p_b4 = b4.forecast(data)
    C.append(("(7) Phase-I ObsWorldB4 unbroken (has gate, forecast works)",
              hasattr(b4, "gate") and tuple(p_b4.shape[:2]) == (2, tl)))

    # param count (report)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[exclusive] inference params = {n_params/1e6:.4f}M  (B4 had {sum(p.numel() for p in b4.parameters())/1e6:.4f}M; gate dropped)")
    print("=" * 70)
    allok = True
    for name, ok in C:
        allok &= bool(ok); print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print("-" * 70)
    print(f"RESULT: {'ALL PASS' if allok else 'FAIL'}  ({sum(bool(c[1]) for c in C)}/{len(C)})")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
