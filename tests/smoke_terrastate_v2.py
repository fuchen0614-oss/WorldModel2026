#!/usr/bin/env python
"""TerraState-V2 smoke (doc 88 §F) — CPU-only, tiny fixtures. Verifies the 13 required
checks WITHOUT any full training and WITHOUT touching the B-session evaluator/protocol.

Run (from the v2train worktree):
  CUDA_VISIBLE_DEVICES="" <WorldModel-python> tests/smoke_terrastate_v2.py \
      --data-root runs/smoke_v2 --official-ckpt checkpoints/contextformer_official/contextformer6M/seed42.ckpt
"""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
from models.encoders.pvt_contextformer_q import contextformer6m_hparams, load_official_ckpt
from models.terrastate_v2 import TerraStateV2, warm_start_terrastate_v2
from train.terrastate_future_state_cache import FrozenFutureStateEncoder, FutureStateCache, build_cache
from train.terrastate_v2_common import (
    FULL24_FIELD_ORDER, atomic_torch_save, collate_with_ids, module_pair_sha256, to_device_with_ids,
)
from train.train_terrastate_v2 import (
    apply_stage, build_argparser, build_optimizer, lambda_state_at, lambda_state_values,
    lr_factor, run_training,
)

FORBIDDEN = [
    "tools/hotdry_selector.py", "scripts/build_extreme_audit_protocol.py",
    "scripts/materialize_manifest_view.py", "eval/audit_adapters.py",
    "eval/extreme_state_audit.py", "tests/smoke_extreme_audit.py",
    "artifacts/protocols/extreme_audit_oodt_v1",
]

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""), flush=True)


def nested_tensor_equal(a, b):
    if torch.is_tensor(a):
        return torch.equal(a, b)
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(nested_tensor_equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(nested_tensor_equal(x, y) for x, y in zip(a, b))
    return a == b


def one_batch(data_dir, n=2):
    ds = GreenEarthNetContextformerDataset(data_dir, dl_cloudmask=True)
    samples = [ds[i] for i in range(min(n, len(ds)))]
    return to_device_with_ids(collate_with_ids(samples), torch.device("cpu"))


def make_student_init(official_ckpt, out_path, state_dim=256):
    hp = contextformer6m_hparams(pvt_pretrained=False)
    model = TerraStateV2(hp, contract_cfg={"state_dim": state_dim, "freeze_b0": True})
    if official_ckpt and Path(official_ckpt).exists():
        miss, unexp = load_official_ckpt(model.q.core, official_ckpt, strict=False)
        print(f"student-init q from official ckpt: missing={len(miss)} unexpected={len(unexp)}")
    else:
        print("student-init: random q (official ckpt absent) — machinery smoke only")
    atomic_torch_save({"b4_state_dict": model.state_dict(), "contract_cfg": model.config(),
                       "arch": model.ARCH}, out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="runs/smoke_v2")
    ap.add_argument("--official-ckpt", default="checkpoints/contextformer_official/contextformer6M/seed42.ckpt")
    args = ap.parse_args()
    torch.manual_seed(0)
    dev = torch.device("cpu")
    root = Path(args.data_root)
    train_dir, val_dir = str(root / "data/train"), str(root / "data/val")
    cache_dir = root / "cache"; out_dir = root / "out"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # ---- 0. isolation: B-session files absent in this worktree ----------------------
    present = [f for f in FORBIDDEN if (ROOT / f).exists()]
    check("13/iso: B-session evaluator/protocol files untouched (absent here)", not present,
          f"present={present}" if present else "none present")

    # ---- student-init + frozen target encoder + tiny caches -------------------------
    init_path = make_student_init(args.official_ckpt, cache_dir / "student_init.pt")
    init_ck = torch.load(init_path, map_location="cpu", weights_only=False)
    hp = contextformer6m_hparams(pvt_pretrained=False)
    model = TerraStateV2(hp, contract_cfg={"state_dim": 256, "freeze_b0": True})
    warm_start_terrastate_v2(model, init_ck)
    model.eval()

    enc = FrozenFutureStateEncoder(model.q, model.projector, model.context_len, model.target_len,
                                   model.patch_size, lc_min=model.lc_min, lc_max=model.lc_max)
    q_proj_sha = module_pair_sha256(model.q, model.projector)

    tr_ds = GreenEarthNetContextformerDataset(train_dir, dl_cloudmask=True)
    va_ds = GreenEarthNetContextformerDataset(val_dir, dl_cloudmask=True)
    tr_blob = build_cache(tr_ds, enc, dev, root=train_dir, split="train",
                          student_init_path=str(init_path), student_init_sha256="smoke", per_gpu_batch=2)
    va_blob = build_cache(va_ds, enc, dev, root=val_dir, split="val",
                          student_init_path=str(init_path), student_init_sha256="smoke", per_gpu_batch=2)
    atomic_torch_save(tr_blob, cache_dir / "train_future_state_cache.pt")
    atomic_torch_save(va_blob, cache_dir / "val_future_state_cache.pt")

    # ---- 1. cache generate / read / SHA verify --------------------------------------
    tr_cache = FutureStateCache(cache_dir / "train_future_state_cache.pt", train_dir)
    va_cache = FutureStateCache(cache_dir / "val_future_state_cache.pt", val_dir)
    sha_ok = True
    try:
        tr_cache.verify(q_projector_sha256=q_proj_sha, field_order=FULL24_FIELD_ORDER, horizon_h=model.target_len)
        va_cache.verify(q_projector_sha256=q_proj_sha, field_order=FULL24_FIELD_ORDER, horizon_h=model.target_len)
    except AssertionError as e:
        sha_ok = False; print("verify err:", e)
    check("1: tiny cache generate + read + SHA verify",
          sha_ok and len(tr_cache) == len(tr_ds) and len(va_cache) == len(va_ds),
          f"train={len(tr_cache)} val={len(va_cache)} "
          f"cov train={tr_blob['provenance']['coverage']:.4f} val={va_blob['provenance']['coverage']:.4f} "
          f"mask_sha={tr_blob['provenance']['mask_sha256'][:12]} "
          f"eff_rank={tr_blob['sanity']['effective_rank']:.2f} n_nan={tr_blob['sanity']['n_nan']} "
          f"zero_var={tr_blob['sanity']['n_zero_var_dims']} move_cos={tr_blob['sanity']['movement_cos_from_context']:.3f}")

    # ---- 1b. CF-consistent mask: injecting ONE cloud pixel excludes the whole patch --
    dci = one_batch(train_dir, n=min(4, len(tr_ds)))
    pm0 = enc.patch_mask(dci)                                        # (B*P,)
    ps, term = enc.patch_size, enc.context_len + enc.target_len - 1
    B = dci["dynamic_mask"][0].shape[0]
    wp = dci["dynamic_mask"][0].shape[-1] // ps
    P = pm0.numel() // B
    valid_idx = torch.nonzero(pm0).flatten()
    if len(valid_idx) > 0:
        f = int(valid_idx[0]); b, lp = f // P, f % P; i, j = lp // wp, lp % wp
        dci["dynamic_mask"][0][b, term, 0, i * ps, j * ps] = 4.0     # single cloud pixel in that patch
        pm1 = enc.patch_mask(dci)
        ci_ok = bool(pm0[f]) and (not bool(pm1[f])) and int((pm0 & ~pm1).sum()) == 1
        detail = f"flat {f} (cube {b}) valid->excluded; #flipped={int((pm0 & ~pm1).sum())}"
    else:
        ci_ok, detail = False, "no valid patch across smoke cubes (terminal-frame coverage 0)"
    check("1b: 1 cloud pixel excludes its 4x4 patch (fully-clear rule)", ci_ok, detail)

    data = one_batch(train_dir, n=2)
    z_star, pmask = tr_cache.gather(data["filepath"], dev)

    # ---- 2. forward/backward no NaN -------------------------------------------------
    model.train()
    _, aux = model(data, teacher_pred=model.forecast(data).detach(), z_star=z_star,
                   patch_mask=pmask, lambda_state=0.02)
    loss = aux["total"]; loss.backward()
    grads_finite = all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
    check("2: forward/backward no NaN", bool(torch.isfinite(loss)) and grads_finite,
          f"loss={float(loss):.5f} terms={ {k: round(float(v),5) for k,v in aux['logs'].items() if k in ('gt','kd','future_state')} }")
    model.zero_grad(set_to_none=True); model.eval()

    # ---- 2a. default scale=1 is an exact regression to the legacy raw-lambda path ---
    # Same fixed model/input/teacher/cache, including one optimizer+scheduler update.
    legacy = copy.deepcopy(model).train()
    scaled = copy.deepcopy(model).train()
    apply_stage(legacy, 1, ["core.blocks.2."])
    apply_stage(scaled, 1, ["core.blocks.2."])
    teacher_fixed = model.forecast(data).detach()
    raw_lam = lambda_state_at(1, 6)
    raw_v, effective_v = lambda_state_values(1, 6, 1.0)
    opt_legacy = build_optimizer(legacy, 3e-5, 0.033, 0.0)
    opt_scaled = build_optimizer(scaled, 3e-5, 0.033, 0.0)
    sch_legacy = torch.optim.lr_scheduler.LambdaLR(
        opt_legacy, lr_lambda=lambda s: lr_factor(s, 1, 6))
    sch_scaled = torch.optim.lr_scheduler.LambdaLR(
        opt_scaled, lr_lambda=lambda s: lr_factor(s, 1, 6))
    _, aux_legacy = legacy(data, teacher_fixed, z_star, pmask, raw_lam)
    _, aux_scaled = scaled(data, teacher_fixed, z_star, pmask, effective_v)
    aux_legacy["total"].backward()
    aux_scaled["total"].backward()
    grad_equal = all(
        (pa.grad is None) == (pb.grad is None)
        and (pa.grad is None or torch.equal(pa.grad, pb.grad))
        for pa, pb in zip(legacy.parameters(), scaled.parameters()))
    components_equal = all(
        torch.equal(aux_legacy["terms"][k], aux_scaled["terms"][k])
        for k in ("gt", "kd", "future_state"))
    opt_legacy.step(); sch_legacy.step()
    opt_scaled.step(); sch_scaled.step()
    state_equal = nested_tensor_equal(legacy.state_dict(), scaled.state_dict())
    opt_equal = nested_tensor_equal(opt_legacy.state_dict(), opt_scaled.state_dict())
    sched_equal = nested_tensor_equal(sch_legacy.state_dict(), sch_scaled.state_dict())
    default_parser_scale = build_argparser().get_default("future_state_scale")
    check("2a: scale=1 exact default regression (rtol=0, atol=0)",
          raw_lam == raw_v == effective_v and default_parser_scale == 1.0
          and torch.equal(aux_legacy["total"], aux_scaled["total"])
          and components_equal and grad_equal and state_equal and opt_equal and sched_equal,
          f"lambda={raw_lam:.6f} loss={float(aux_scaled['total']):.8f} "
          f"grad={grad_equal} model/opt/sched={state_equal}/{opt_equal}/{sched_equal}")

    # ---- 2b. scale=0 has exactly the GT+0.5*KD objective and gradient ---------------
    nofs = copy.deepcopy(model).train()
    gt_kd = copy.deepcopy(model).train()
    apply_stage(nofs, 1, ["core.blocks.2."])
    apply_stage(gt_kd, 1, ["core.blocks.2."])
    _, aux_nofs = nofs(data, teacher_fixed, z_star, pmask, 0.0)
    _, aux_gtkd = gt_kd(data, teacher_fixed, z_star, pmask, 0.0)
    reference_total = aux_gtkd["terms"]["gt"] + 0.5 * aux_gtkd["terms"]["kd"]
    aux_nofs["total"].backward()
    reference_total.backward()
    nofs_grad_equal = all(
        (pa.grad is None) == (pb.grad is None)
        and (pa.grad is None or torch.equal(pa.grad, pb.grad))
        for pa, pb in zip(nofs.parameters(), gt_kd.parameters()))
    check("2b: scale=0 objective/gradient exactly GT + 0.5 KD (rtol=0, atol=0)",
          torch.equal(aux_nofs["total"], reference_total) and nofs_grad_equal
          and all(torch.isfinite(aux_nofs["terms"][k]) for k in ("gt", "kd", "future_state")),
          f"total={float(aux_nofs['total']):.8f} fs={float(aux_nofs['terms']['future_state']):.8f} "
          f"grad={nofs_grad_equal}")

    # ---- 3. full24 path enters T (weather changes forecast) -------------------------
    with torch.no_grad():
        y0 = model.forecast(data)
        y1 = model.forecast(model._shallow_with_weather(data, randomize_future=True))
    check("3: full24 future weather enters T (changes forecast)", not torch.allclose(y0, y1),
          f"max|dy|={float((y0-y1).abs().max()):.4e}")

    # ---- 4. prior ignores future weather --------------------------------------------
    check("4: context-only prior ignores future weather", model.assert_prior_ignores_future_weather(data))

    # ---- 5. target future weather zeroed (target invariant to future weather) -------
    with torch.no_grad():
        zt0 = enc.encode_target(data)
        d_w = model._shallow_with_weather(data, randomize_future=True)
        zt1 = enc.encode_target(d_w)
        d_f = model._shallow_with_frames(data, randomize_future=True)
        zt2 = enc.encode_target(d_f)
    check("5: target future weather zeroed (target invariant to future weather)",
          torch.equal(zt0, zt1) and not torch.allclose(zt0, zt2),
          "target changes with future EO but NOT with future weather")

    # ---- 6. inference reads no future EO / no cache ---------------------------------
    check("6: inference forecast ignores future EO frames (+ takes no cache)",
          model.assert_forecast_ignores_future_eo(data))

    # ---- 7. alpha fixed 1, no grad, not an optimizer param --------------------------
    alpha_ok = ("alpha" in model._buffers and not model.alpha.requires_grad and float(model.alpha) == 1.0)
    check("7: alpha == 1 fixed non-learnable buffer", alpha_ok, f"alpha={float(model.alpha)}")

    # ---- 8. exactly one KD loss (terms == {gt, kd, future_state}) -------------------
    terms = set(aux["terms"].keys())
    check("8: exactly one KD term; loss == {gt, kd, future_state}", terms == {"gt", "kd", "future_state"},
          f"terms={sorted(terms)}")

    # ---- 9. q freeze states across the 3 stages -------------------------------------
    def q_state(m):
        return {n: p.requires_grad for n, p in m.q.named_parameters()}
    apply_stage(model, 1, ["core.blocks.2."]); s1 = q_state(model)
    apply_stage(model, 2, ["core.blocks.2."]); s2 = q_state(model)
    apply_stage(model, 3, ["core.blocks.2."]); s3 = q_state(model)
    st1_frozen = not any(s1.values()); st2_frozen = not any(s2.values())
    st3_ok = all((v == n.startswith("core.blocks.2.")) for n, v in s3.items()) and any(s3.values())
    check("9: q freeze — stage1/2 fully frozen, stage3 only last block", st1_frozen and st2_frozen and st3_ok,
          f"stage3 trainable={sum(s3.values())}")
    apply_stage(model, 1, ["core.blocks.2."])

    # ---- 10/11/2b. tiny 3-stage run: no-NaN, 80% boundary ckpt, stage transitions ---
    def base_args(od, per_gpu=2, gb=2, max_steps=6, max_epochs=40, resume="",
                  deterministic=True, future_state_scale=1.0, stop_after_step=0):
        a = build_argparser().parse_args([
            "--train-dir", train_dir, "--val-dir", val_dir,
            "--train-cache", str(cache_dir / "train_future_state_cache.pt"),
            "--val-cache", str(cache_dir / "val_future_state_cache.pt"),
            "--student-init", str(init_path), "--teacher-b4", str(init_path),
            "--output-dir", od, "--device", "cpu",
            "--per-gpu-batch", str(per_gpu), "--global-batch", str(gb), "--num-workers", "0",
            "--max-steps", str(max_steps), "--max-epochs", str(max_epochs),
            "--future-state-scale", str(future_state_scale),
            "--stop-after-step", str(stop_after_step),
            "--branch-lr", "3e-5", "--q-lr-scale", "0.033",
            "--lr-warmup-steps", "1", "--val-interval", "1000", "--ckpt-interval", "3",
            "--log-interval", "1", "--unfreeze-q-prefixes", "core.blocks.2.",
        ] + (["--resume", resume] if resume else []) + (["--deterministic"] if deterministic else []))
        return a

    ref = run_training(base_args(str(out_dir / "ref"), max_steps=6))
    boundary_ckpt = out_dir / "ref" / "checkpoint_boundary80.pt"
    check("10: 80% boundary checkpoint force-saved", boundary_ckpt.exists(),
          f"boundary80_step={ref['boundary80']}")
    ref_finite = all(torch.isfinite(torch.tensor(r["total"])) for r in ref["loss_log"])
    check("11: 3-stage tiny run finite (no NaN over run)", ref_finite and ref["step"] == 6,
          f"steps={ref['step']} losses={[round(r['total'],4) for r in ref['loss_log']]}")

    # ---- 12. save/resume alignment (params/opt/sched/RNG/next-step loss) -------------
    # ref (total_steps=6) already saved checkpoint_step3.pt at step 3; resume from it and
    # verify the continued losses (steps 4..6) match the uninterrupted reference.
    res = run_training(base_args(str(out_dir / "b"), max_steps=6,
                                 resume=str(out_dir / "ref" / "checkpoint_step3.pt")))
    ref_tail = {r["step"]: r["total"] for r in ref["loss_log"] if r["step"] > 3}
    res_tail = {r["step"]: r["total"] for r in res["loss_log"] if r["step"] > 3}
    aligned = res_tail and all(
        abs(ref_tail.get(s, 1e9) - res_tail[s]) <= 1e-4 * (abs(ref_tail.get(s, 0)) + 1e-3)
        for s in res_tail)
    check("12: save/resume — resumed next-step losses match uninterrupted", aligned,
          f"ref_tail={ {k: round(v,5) for k,v in ref_tail.items()} } res_tail={ {k: round(v,5) for k,v in res_tail.items()} }")

    # ---- 12b. no-FS boundary stop + metadata + exact scale-0 resume -----------------
    wofs_out = out_dir / "wofs"
    wofs = run_training(base_args(str(wofs_out), max_steps=5,
                                  future_state_scale=0.0, stop_after_step=4))
    wofs_ck = torch.load(wofs_out / "checkpoint_boundary80.pt",
                         map_location="cpu", weights_only=False)
    expected_objective = all(
        abs(r["total"] - (r["gt"] + 0.5 * r["kd"])) <= 1e-7
        and r["effective_lambda_state"] == 0.0
        and r["lambda_state_raw"] == lambda_state_at(r["step"] - 1, 5)
        for r in wofs["loss_log"])
    branch_changed = any(
        not k.startswith("q.") and not torch.equal(v, init_ck["b4_state_dict"][k])
        for k, v in wofs_ck["b4_state_dict"].items()
        if k in init_ck["b4_state_dict"] and torch.is_tensor(v))
    wofs_meta = (
        wofs["step"] == 4 and wofs["final_stage"] == 2 and not wofs["q_grad_seen_stage3"]
        and wofs_ck["step"] == 4 and wofs_ck["stage"] == 2
        and wofs_ck["total_steps"] == 5 and wofs_ck["q_freeze"]["trainable_q"] == []
        and wofs_ck["future_state_scale"] == 0.0
        and wofs_ck["args"]["future_state_scale"] == 0.0
        and wofs_ck["lambda_state_raw"] == lambda_state_at(4, 5)
        and wofs_ck["effective_lambda_state"] == 0.0
        and wofs_ck["loss_weights"]["kd"] == 0.5)
    check("12b: no-FS stops at boundary before stage3; loss/checkpoint identity exact",
          expected_objective and wofs_meta and branch_changed,
          f"step/stage={wofs['step']}/{wofs['final_stage']} raw/effective="
          f"{wofs_ck['lambda_state_raw']}/{wofs_ck['effective_lambda_state']} "
          f"branch_updated={branch_changed}")

    wofs_resume_out = out_dir / "wofs_resume"
    wofs_resume = run_training(base_args(
        str(wofs_resume_out), max_steps=5,
        resume=str(wofs_out / "checkpoint_step3.pt"),
        future_state_scale=0.0, stop_after_step=4))
    wofs_step4 = next(r for r in wofs["loss_log"] if r["step"] == 4)
    wofs_resume_step4 = next(r for r in wofs_resume["loss_log"] if r["step"] == 4)
    check("12c: no-FS checkpoint resume preserves scale and next update",
          wofs_resume["step"] == 4 and wofs_resume["final_stage"] == 2
          and wofs_resume_step4["effective_lambda_state"] == 0.0
          and abs(wofs_step4["total"] - wofs_resume_step4["total"])
          <= 1e-4 * (abs(wofs_step4["total"]) + 1e-3),
          f"full/resume step4={wofs_step4['total']:.8f}/{wofs_resume_step4['total']:.8f}")

    mismatch_rejected = False
    try:
        run_training(base_args(str(out_dir / "wofs_bad_resume"), max_steps=5,
                               resume=str(wofs_out / "checkpoint_step3.pt"),
                               future_state_scale=1.0, stop_after_step=4))
    except AssertionError as e:
        mismatch_rejected = "future_state_scale mismatch" in str(e)
    check("12d: resume rejects future-state-scale mismatch", mismatch_rejected)

    # ---- 13. single vs 'DDP' global-batch / effective-update definition -------------
    e_a = run_training(base_args(str(out_dir / "gb_a"), per_gpu=2, gb=4, max_steps=0, max_epochs=2))  # accum=2
    e_b = run_training(base_args(str(out_dir / "gb_b"), per_gpu=4, gb=4, max_steps=0, max_epochs=2))  # accum=1
    check("13: global-batch/effective-updates consistent across factorizations",
          e_a["total_steps"] == e_b["total_steps"] and e_a["global_batch"] == e_b["global_batch"] == 4
          and e_a["accum"] == 2 and e_b["accum"] == 1,
          f"A(accum2)={e_a['total_steps']} B(accum1)={e_b['total_steps']} gb={e_a['global_batch']}")

    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n==== SMOKE {n_pass}/{len(RESULTS)} PASSED ====")
    sys.exit(0 if n_pass == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
