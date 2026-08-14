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
from eval.eval_b4_exclusive_contract import (  # noqa: E402
    _alpha_zero, _predict_weather, _uf, _q4, _driver_deltas, parse_sections,
    _cube_clustered_bootstrap, _q2_invariants,
)
from eval.b4_donor_schema import (  # noqa: E402
    weather_divergence, doy_diff_circular, build_pairs_divergent,
)
from models.plan_b_b4_exclusive import EXCL_TRAIN_PARTITIONS, EXCL_HELDOUT_PARTITIONS  # noqa: E402

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

    # synthetic Q3/Q4 exclusive eval: driver deltas (multi-h) + Q4 with A_comp + composite verdict
    ds = FakeDS(4); idx = {str(Path(p)): i for i, p in enumerate(ds.filepaths)}; tg = [Path(p) for p in ds.filepaths]
    model.eval()
    with torch.no_grad():
        y_match = _predict_weather(model, data, _uf(model, data))
        y_mean = _predict_weather(model, data, torch.zeros_like(_uf(model, data)))
    dd = _driver_deltas(model, ds, idx, tg, torch.device("cpu"), "mean", bs=1, workers=0)
    q4 = _q4(model, ds, idx, tg, torch.device("cpu"), 0.5, "x", 0.5, bs=1, workers=0, ni_margin=0.05, q2_pass=True)
    part = next(iter(q4["heldout"].values()))
    C.append(("Q3/Q4 synthetic: matched!=mean; per-h {5,10,20}; Q4 A_comp+non-inf+verdict+cube-clustered present",
              (y_match - y_mean).abs().max() > 1e-6 and len(dd["per_cube"]["signed"]) == len(tg)
              and set(dd["per_h"].keys()) >= {5, 10, 20}
              and "broken_minus_real_advantage_A_comp" in part and "endpoint_composed_minus_direct" in part
              and "state_path_gap" in part and q4.get("verdict") in ("Q4_PASS", "Q4_FAIL")
              and "heldout_pooled_A_comp_cube_clustered" in q4))

    # (三.4) matched-vs-matched Q3 noise floor is deterministically ~0
    dd_m = _driver_deltas(model, ds, idx, tg, torch.device("cpu"), "matched", bs=1, workers=0)
    C.append(("Q3 matched-vs-matched noise floor == 0 (deterministic; not a stochastic estimate)",
              max(abs(x) for x in dd_m["per_cube"]["abs"]) < 1e-9 and dd_m["mean_state_delta"] < 1e-9))

    # (五.2) composition ramp: 0 before start, mid in (0,λ), full at/after start+ramp
    base = SimpleNamespace(fore=1, distill=1, resid=1, vic=0.05, cmp=0.2, con=0.1, state_con=0.3, vic_future=0.05)
    r0 = sched_lambdas(base, 100, 1000, 0.25, 0.5, cmp_start_frac=0.5, cmp_ramp_frac=0.25)
    rmid = sched_lambdas(base, 625, 1000, 0.25, 0.5, cmp_start_frac=0.5, cmp_ramp_frac=0.25)
    rfull = sched_lambdas(base, 800, 1000, 0.25, 0.5, cmp_start_frac=0.5, cmp_ramp_frac=0.25)
    C.append(("composition ramp: start=0, mid in (0,λ), full=λ (cmp/con/state_con/vic_future)",
              r0.cmp == 0 and r0.state_con == 0 and 0 < rmid.cmp < 0.2 and 0 < rmid.state_con < 0.3
              and abs(rfull.cmp - 0.2) < 1e-9 and abs(rfull.vic_future - 0.05) < 1e-9))

    # (五.3-4) EXCL train/heldout partitions disjoint + horizon coverage
    tr = set(map(tuple, model.partitions)); ho = set(map(tuple, model.heldout_partitions))
    tot = lambda S: {a + b for a, b in S}
    C.append(("EXCL partitions disjoint + coverage (train totals ⊇{10,15,20}; heldout has 10 and 20)",
              tr.isdisjoint(ho) and {10, 15, 20} <= tot(tr) and 10 in tot(ho) and 20 in tot(ho)
              and set(EXCL_TRAIN_PARTITIONS) == tr and set(EXCL_HELDOUT_PARTITIONS) == ho))

    # (五.5-6) Stage-B state_con + vic_future produce gradients on the transition; terms present
    model.freeze_b0 = False; model.train(); model.zero_grad(set_to_none=True)
    for p in model.q.parameters():
        p.requires_grad_(True)
    lam_sb = SimpleNamespace(fore=1.0, distill=0.0, resid=0.0, vic=0.0, cmp=1.0, con=1.0, state_con=1.0, vic_future=0.05)
    _, aux_sb = model(data, t_pred, lam_sb); aux_sb["total"].backward()
    tgrad = any(p.grad is not None and p.grad.abs().sum() > 0 for p in model.transition.parameters())
    C.append(("Stage-B cmp/con/state_con/vic_future backward -> transition grads; all terms present",
              tgrad and {"cmp", "con", "state_con", "vic_future"} <= set(aux_sb["terms"])))

    # (五.7) never-alone assert fires when state_con>0 without fore + (cmp|con)
    threw = False
    try:
        model(data, t_pred, SimpleNamespace(fore=0.0, distill=0, resid=0, vic=0, cmp=0, con=0, state_con=1.0, vic_future=0))
    except AssertionError:
        threw = True
    C.append(("state_con never-alone assert fires (fore=0, cmp=0, con=0)", threw))

    # (Stage-A golden) new default-OFF machinery is INERT: total identical to the pre-audit lambda shape
    model.eval(); model.freeze_b0 = True
    for p in model.q.parameters():
        p.requires_grad_(False)
    lam_new = SimpleNamespace(fore=1.0, distill=1.0, resid=1.0, vic=0.05, cmp=0.0, con=0.0, state_con=0.0, vic_future=0.0)
    lam_old = SimpleNamespace(fore=1.0, distill=1.0, resid=1.0, vic=0.05, cmp=0.0, con=0.0)   # pre-audit shape (no new keys)
    with torch.no_grad():
        _, a_new = model(data, t_pred, lam_new)
        _, a_old = model(data, t_pred, lam_old)
        p_inf = model.forecast(data)
    C.append(("Stage-A golden: default-OFF machinery INERT (total == pre-audit shape) + finite forecast",
              torch.equal(a_new["total"], a_old["total"]) and torch.isfinite(p_inf).all()))

    # (七) Q2 invariants: alpha0==context_prior, T-identity==state-identity, weights restored
    inv = _q2_invariants(model, ds, idx, tg[:1], torch.device("cpu"))
    C.append(("Q2 invariants: alpha0==prior, T-identity==state, live weights restored",
              inv["alpha0_pred_equals_context_prior"] and inv["T_identity_is_state_identity"] and inv["live_weights_restored"]))

    # (六.9) cube-clustered bootstrap direction: positive blocks significant, zero blocks not
    posb = _cube_clustered_bootstrap([[1.0, 1.0], [1.0], [1.0, 1.0, 1.0]])
    zerob = _cube_clustered_bootstrap([[0.0], [0.0], [0.0]])
    C.append(("cube-clustered bootstrap: positive blocks CI>0, zero blocks not; n_cubes correct",
              posb["significant_gt0"] and not zerob["significant_gt0"] and posb["n_cubes"] == 3))

    # (二) donor v2 pure helpers: circular DOY, normalized-space divergence, prefer-divergent + reuse cap
    import numpy as _np
    recs = {f"c{i}": {"tile": "31TDJ", "season": "JJA", "centroid": [45.0, 5.0 + 0.01 * i], "doy": 180 + i, "year": 2018}
            for i in range(4)}
    ufs = {f"c{i}": _np.full((20, 24), float(i)) for i in range(4)}      # c3 is most divergent from c0
    pairs_v2, floor_abs, unp = build_pairs_divergent(recs, ufs, max_geo_km=500, doy_window=15, reuse_cap=1, floor_quantile=0.0)
    C.append(("donor v2: circular DOY + normalized divergence + prefer-divergent + reuse cap",
              doy_diff_circular(1, 364) == 2 and weather_divergence([[0]], [[3]]) == 3.0
              and pairs_v2["c0"]["donor"] == "c3" and all(e["donor_reuse_count"] <= 1 for e in pairs_v2.values())))

    # (四) intervention-distillation: gated term + gradient when an arm batch is passed; ABSENT when None
    m_iv = ObsWorldB4Exclusive(hp, contract_cfg={"state_dim": 256, "freeze_b0": True})
    load_exclusive_from_b4(m_iv, b4_sd); unfreeze_q_by_prefix(m_iv, ["core.blocks.2.", "core.head."]); m_iv.train()
    tch = PVTContextformerQ(hp)
    tch.load_state_dict({k[2:]: v for k, v in b4_sd.items() if k.startswith("q.")}, strict=False); tch.eval()
    ad = fake_data(seed=9); ad["dynamic"][0][:, :cl] = data["dynamic"][0][:, :cl]; ad["dynamic"][1][:, cl:] = 0.0
    with torch.no_grad():
        tp2 = tch.encode(data, pred_start=cl, preds_length=tl)[0].detach()
        ta = tch.encode(ad, pred_start=cl, preds_length=tl)[0].detach()
    lam_iv = SimpleNamespace(fore=1.0, distill=0.0, resid=0.0, vic=0.0, cmp=0.0, con=0.0, state_con=0.0, vic_future=0.0, intervention=0.2)
    m_iv.zero_grad(set_to_none=True)
    _, aux_iv = m_iv(data, tp2, lam_iv, {"arm_data": ad, "teacher_arm_pred": ta, "arm": "zero"}); aux_iv["total"].backward()
    ig = any(p.grad is not None and p.grad.abs().sum() > 0 for p in m_iv.transition.parameters())
    with torch.no_grad():
        _, aux_off = m_iv(data, tp2, lam_iv, None)                                     # no arm batch => term must NOT fire
        _, aux_fo = m_iv(data, tp2, SimpleNamespace(fore=1.0, distill=0, resid=0, vic=0, cmp=0, con=0,
                                                    state_con=0, vic_future=0, intervention=0), None)
    C.append(("intervention: gated term+grad w/ arm; ABSENT w/o arm; never replaces L_fore",
              "intervention" in aux_iv["terms"] and ig and "intervention" not in aux_off["terms"]
              and torch.equal(aux_off["total"], aux_fo["total"])))

    # Stage-B MAIN/SAFE full-lambda ONE-BATCH train: fwd+bwd+opt.step+checkpoint save/reload runs
    import tempfile as _tf
    def _one_step(lam, with_interv):
        mm = ObsWorldB4Exclusive(hp, contract_cfg={"state_dim": 256, "freeze_b0": True})
        load_exclusive_from_b4(mm, b4_sd); unfreeze_q_by_prefix(mm, ["core.blocks.2.", "core.head."]); mm.train()
        iv = {"arm_data": ad, "teacher_arm_pred": ta, "arm": "zero"} if with_interv else None
        opt2 = torch.optim.AdamW([p for p in mm.parameters() if p.requires_grad], lr=1e-5)
        opt2.zero_grad(set_to_none=True)
        _, a = mm(data, tp2, lam, iv); a["total"].backward()
        torch.nn.utils.clip_grad_norm_(mm.parameters(), 1.0); opt2.step()
        ok = bool(torch.isfinite(a["total"]))
        with _tf.TemporaryDirectory() as td:
            pth = Path(td) / "sb.pt"
            torch.save({"b4_state_dict": mm.state_dict(), "contract_cfg": mm.config(), "arch": mm.ARCH,
                        "route_version": mm.ROUTE_VERSION, "stage": "B"}, pth)
            m2 = ObsWorldB4Exclusive(hp, contract_cfg={"state_dim": 256, "freeze_b0": True})
            _, _, src = load_student_init(m2, torch.load(pth, map_location="cpu", weights_only=False))
        return ok and src == "exclusive"
    lam_main = SimpleNamespace(fore=1.0, distill=0.5, resid=0.5, vic=0.05, cmp=0.5, con=0.5, state_con=0.25, vic_future=0.05, intervention=0.1)
    lam_safe = SimpleNamespace(fore=1.0, distill=1.0, resid=1.0, vic=0.05, cmp=0.25, con=0.5, state_con=0.1, vic_future=0.05, intervention=0.0)
    C.append(("Stage-B MAIN one-batch: full loss fwd+bwd+opt.step+ckpt save/reload (with intervention arm)", _one_step(lam_main, True)))
    C.append(("Stage-B SAFE one-batch: full loss fwd+bwd+opt.step+ckpt save/reload (no intervention)", _one_step(lam_safe, False)))

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
