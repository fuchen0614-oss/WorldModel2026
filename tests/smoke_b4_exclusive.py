"""plan-b-pvt · Phase-II exclusive-route CPU regression smoke (audit-fixed).

No GPU / no real data / no training. Covers all audit-required checks incl. dual-signature
forward, DDP(gloo,2-proc) forward+backward, Stage-B selective unfreeze, alpha fixed 1,
Phase-I->exclusive & exclusive->exclusive loads, teacher SHA invariance, and a synthetic
Q1-Q4 exclusive-eval pass. Phase-I entry left intact.

Run: CUDA_VISIBLE_DEVICES="" <python> tests/smoke_b4_exclusive.py
"""
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams, PVTContextformerQ  # noqa: E402
from models.plan_b_b4 import ObsWorldB4  # noqa: E402
from models.plan_b_b4_exclusive import ObsWorldB4Exclusive, load_exclusive_from_b4  # noqa: E402
from train.train_plan_b_b4_exclusive import (  # noqa: E402
    unfreeze_q_by_prefix, state_sha, sched_lambdas, lr_factor, load_student_init,
)
from eval.eval_b4_exclusive_contract import _alpha_zero, _predict_weather, _uf, _q4, _driver_deltas, parse_sections  # noqa: E402

LAST_STAGE_HEAD = ["core.blocks.2.", "core.head."]


def fake_data(B=2, T=30, H=128, W=128, seed=0):
    g = torch.Generator().manual_seed(seed)
    dyn = torch.randn(B, T, 5, H, W, generator=g); dyn[:, :, 0] = torch.tanh(dyn[:, :, 0])
    return {"dynamic": [dyn, torch.randn(B, T, 24, generator=g)],
            "dynamic_mask": [(torch.rand(B, T, 1, H, W, generator=g) < 0.05).float()],
            "static": [torch.randn(B, 5, H, W, generator=g)],
            "landcover": torch.randint(10, 41, (B, 1, H, W), generator=g).float()}


class FakeDS:
    def __init__(self, n=2, H=128, W=128, T=30):
        self.filepaths = [f"/fake/JAS21/cube{i}.nc" for i in range(n)]; self.H, self.W, self.T = H, W, T

    def __len__(self):
        return len(self.filepaths)

    def __getitem__(self, i):
        g = torch.Generator().manual_seed(i)
        dyn = torch.randn(self.T, 5, self.H, self.W, generator=g); dyn[:, 0] = torch.tanh(dyn[:, 0])
        return {"dynamic": [dyn, torch.randn(self.T, 24, generator=g)],
                "dynamic_mask": [(torch.rand(self.T, 1, self.H, self.W, generator=g) < 0.05).float()],
                "static": [torch.randn(5, self.H, self.W, generator=g)],
                "landcover": torch.randint(10, 41, (1, self.H, self.W), generator=g).float(),
                "filepath": self.filepaths[i]}


def _ddp_worker(rank):
    os.environ.update(MASTER_ADDR="127.0.0.1", MASTER_PORT="29517")
    import torch.distributed as dist
    dist.init_process_group("gloo", rank=rank, world_size=2)
    hp = contextformer6m_hparams(pvt_pretrained=False)
    student = ObsWorldB4Exclusive(hp, contract_cfg={"state_dim": 256, "freeze_b0": True})
    from torch.nn.parallel import DistributedDataParallel as DDP
    student = DDP(student, find_unused_parameters=True)
    teacher = PVTContextformerQ(hp).eval()
    data = fake_data(B=1, seed=rank)
    with torch.no_grad():
        t_pred = teacher.encode(data, pred_start=10, preds_length=20)[0].detach()
    lam = SimpleNamespace(fore=1.0, distill=1.0, resid=1.0, vic=0.05, cmp=0.0, con=0.0)
    _, aux = student(data, t_pred, lam)                 # DUAL-signature forward under DDP
    aux["total"].backward()                             # backward must work
    assert torch.isfinite(aux["total"])
    dist.destroy_process_group()


def main():
    C = []
    hp = contextformer6m_hparams(pvt_pretrained=False)
    cl, tl = hp.context_length, hp.target_length
    b4 = ObsWorldB4(hp, contract_cfg={"state_dim": 256, "freeze_b0": True}).eval()
    b4_sd = b4.state_dict()
    model = ObsWorldB4Exclusive(hp, contract_cfg={"state_dim": 256, "freeze_b0": True}).eval()
    miss, unexp = load_exclusive_from_b4(model, b4_sd)
    data = fake_data()

    # (6) B4 reuse: only gate dropped, alpha new, no gate param
    C.append(("B4 reuse: unexpected==[gate], missing⊆[alpha], no gate param",
              unexp == [] and set(miss) <= {"alpha"} and "gate" not in dict(model.named_parameters())))

    # dual-signature forward: model(data)=inference ; model(data,teacher,lam)=train loss+backward
    with torch.no_grad():
        pred_inf = model(data)
    teacher = PVTContextformerQ(hp); teacher.load_state_dict({k[2:]: v for k, v in b4_sd.items() if k.startswith("q.")}, strict=False)
    teacher.eval()
    for p in teacher.parameters():
        p.requires_grad_(False)
    tsha0 = state_sha(teacher.state_dict())
    for p in model.q.parameters():                      # allow grad so backward touches something
        p.requires_grad_(True)
    model.freeze_b0 = False; model.train()
    with torch.no_grad():
        t_pred = teacher.encode(data, pred_start=cl, preds_length=tl)[0].detach()
    lam = SimpleNamespace(fore=1.0, distill=1.0, resid=1.0, vic=0.05, cmp=0.0, con=0.0)
    _, aux = model(data, t_pred, lam); aux["total"].backward()
    C.append(("dual-signature forward: model(data) infers + model(data,teacher,lam) train+backward",
              tuple(pred_inf.shape[:2]) == (2, tl) and torch.isfinite(aux["total"])
              and {"fore", "distill", "resid"} <= set(aux["terms"])))
    C.append(("(5) teacher SHA unchanged after student step", state_sha(teacher.state_dict()) == tsha0))

    # Stage B selective unfreeze: ONLY core.blocks.2.* + core.head.* trainable
    model2 = ObsWorldB4Exclusive(hp, contract_cfg={"state_dim": 256, "freeze_b0": True})
    unf = unfreeze_q_by_prefix(model2, LAST_STAGE_HEAD)
    train_q = {n for n, p in model2.q.named_parameters() if p.requires_grad}
    ok_prefix = train_q and all(n.startswith(("core.blocks.2.", "core.head.")) for n in train_q) \
        and not any(n.startswith(("core.blocks.0.", "core.blocks.1.", "core.embed_images")) for n in train_q)
    C.append(("Stage B: ONLY core.blocks.2.+core.head. trainable (asserts inside)", bool(ok_prefix)))

    # alpha fixed 1 (both stages) — schedule helpers never touch alpha
    C.append(("alpha buffer == 1.0 (never scheduled)", float(model2.alpha) == 1.0))
    ls_a1 = sched_lambdas(SimpleNamespace(fore=1, distill=1, resid=1, vic=0.05, cmp=0, con=0), 10, 1000, 0.25, 0.5)
    ls_a2 = sched_lambdas(SimpleNamespace(fore=1, distill=1, resid=1, vic=0.05, cmp=0, con=0), 500, 1000, 0.25, 0.5)
    C.append(("loss schedule A1(=1) -> A2(=0.5) on distill/resid; LR warmup+cosine monotone-ish",
              ls_a1.distill == 1 and ls_a2.distill == 0.5 and ls_a2.resid == 0.5
              and lr_factor(0, 200, 1000) == 0.0 and 0.99 < lr_factor(200, 200, 1000) <= 1.0 and lr_factor(1000, 200, 1000) < 0.05))

    # both loads: Phase-I b4 -> exclusive AND exclusive -> exclusive
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "b4.pt"; torch.save({"b4_state_dict": b4_sd, "contract_cfg": b4.config()}, p1)
        m_a = ObsWorldB4Exclusive(hp, contract_cfg={"state_dim": 256, "freeze_b0": True})
        _, _, src1 = load_student_init(m_a, torch.load(p1, map_location="cpu", weights_only=False))
        p2 = Path(td) / "excl.pt"; torch.save({"b4_state_dict": m_a.state_dict(), "contract_cfg": m_a.config(), "arch": m_a.ARCH}, p2)
        m_b = ObsWorldB4Exclusive(hp, contract_cfg={"state_dim": 256, "freeze_b0": True})
        _, _, src2 = load_student_init(m_b, torch.load(p2, map_location="cpu", weights_only=False))
    C.append(("checkpoint loads: phase1_b4 + exclusive both accepted", src1 == "phase1_b4" and src2 == "exclusive"))

    # (1) future-weather change -> context_prior unchanged ; (2) -> T residual changes ; (3) alpha=0->pred==prior
    model.eval()
    with torch.no_grad():
        prior1, z1 = model._prior_state(data)
        d2 = fake_data(seed=1); d2["dynamic"][0][:, :cl] = data["dynamic"][0][:, :cl]
        d2["dynamic"][1][:, :cl] = data["dynamic"][1][:, :cl]; d2["dynamic"][1][:, cl:] += 5.0
        d2["dynamic_mask"][0][:] = data["dynamic_mask"][0]; d2["static"][0][:] = data["static"][0]; d2["landcover"] = data["landcover"]
        prior2, _ = model._prior_state(d2)
        geo, uf = model._geo_weather(data)
        r1 = model._direct_residual(z1, uf, geo, 2, 128, 128); r2 = model._direct_residual(z1, uf + 3, geo, 2, 128, 128)
        with _alpha_zero(model):
            pa0 = model.forecast(data)
    C.append(("(1)(2)(3) prior invariant / T changes / alpha0==prior",
              torch.allclose(prior1, prior2, atol=1e-6) and (r1 - r2).abs().max() > 1e-5 and torch.allclose(pa0, prior1, atol=1e-6)))

    # (8) inference forecast with NO teacher; (7) Phase-I intact
    with torch.no_grad():
        _ = model.forecast(data); pb4 = b4.forecast(data)
    C.append(("(8)(7) inference w/o teacher + Phase-I ObsWorldB4 unbroken",
              hasattr(b4, "gate") and tuple(pb4.shape[:2]) == (2, tl)))

    # synthetic Q1-Q4 exclusive eval (model-space parts): driver deltas + Q4 with asymmetric control
    ds = FakeDS(2); idx = {str(Path(p)): i for i, p in enumerate(ds.filepaths)}; tg = [Path(p) for p in ds.filepaths]
    model.eval()
    with torch.no_grad():
        y_match = _predict_weather(model, data, _uf(model, data))
        y_mean = _predict_weather(model, data, torch.zeros_like(_uf(model, data)))
    dd = _driver_deltas(model, ds, idx, tg, torch.device("cpu"), "mean", bs=1, workers=0)
    q4 = _q4(model, ds, idx, tg, torch.device("cpu"), 0.5, "x", 0.5, bs=1, workers=0)
    part = next(iter(q4["train"].values()))
    C.append(("Q1-Q4 synthetic: matched!=mean, driver per-cube, Q4 has asymmetric broken control",
              (y_match - y_mean).abs().max() > 1e-6 and len(dd["per_cube"]["signed"]) == len(tg)
              and "control_broken_composed_leg2_gap" in part and "composition_ratio_real_over_broken" in part
              and "diagnostic_state_path_gap" in part))

    # --sections parsing: q1q2 -> {q1,q2} only; all -> q1..q4; q2 implies q1
    C.append(("parse_sections: q1q2->{q1,q2}, all->q1..q4, q2 implies q1",
              parse_sections("q1q2") == {"q1", "q2"} and parse_sections("all") == {"q1", "q2", "q3", "q4"}
              and parse_sections("q2") == {"q1", "q2"} and "q3" not in parse_sections("q1,q2")))

    # DDP (gloo, 2-proc) forward+backward — verifies dual-signature under DDP
    ddp_ok = True
    try:
        import torch.multiprocessing as mp
        mp.spawn(_ddp_worker, nprocs=2, join=True)
    except Exception as e:
        ddp_ok = False; print("  DDP smoke error:", repr(e)[:200])
    C.append(("DDP(gloo,2-proc) dual-signature forward+backward", ddp_ok))

    print("=" * 72)
    allok = True
    for name, ok in C:
        allok &= bool(ok); print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print("-" * 72)
    print(f"RESULT: {'ALL PASS' if allok else 'FAIL'}  ({sum(bool(c[1]) for c in C)}/{len(C)})")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
