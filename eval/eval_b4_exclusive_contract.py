#!/usr/bin/env python
"""plan-b-pvt · Phase-II EXCLUSIVE-route state-contract evaluator (Q1–Q4).

Separate from the Phase-I evaluator (eval/eval_b4_state_contract.py is untouched). Reuses its
PURE helpers (scoring, bootstrap, manifest, donor, guard, batched loader) but drives the
EXCLUSIVE model:
  * Q2 closure = alpha=0 (NOT a gate); transition = T→identity.
  * Q3 weather intervention changes ONLY T's future weather; the context_prior is fixed
    (it never reads future weather), so any output change is attributable to T.
  * Q4 composed = exclusive composed (prior + alpha·O(composed state)); the negative control
    is ASYMMETRIC — it misaligns ONLY the composed leg-2 weather window (direct untouched),
    not the old "shuffle both paths" control.

FP32; checkpoint asserted byte-unchanged. Refuses the parent's gate-based methods.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from models.plan_b_b4_exclusive import ObsWorldB4Exclusive, load_exclusive_from_b4  # noqa: E402
from eval.eval_b4_state_contract import (  # noqa: E402  (PURE reuse; Phase-I file unchanged)
    _sha, _bootstrap_ci, _paired_diff, _paired_deltas, _t_identity, _load_guard_config,
    _evaluator_commit, _export, _score, _per_cube_r2, _batch_iter, _targets,
    validate_donor_manifest, _donor_rel, _Q4_CALIBER,
)


def load_exclusive(ckpt_path, device):
    ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    if not (isinstance(ck, dict) and "b4_state_dict" in ck):
        raise ValueError(f"{ckpt_path} has no b4_state_dict")
    arch = (ck.get("contract_cfg", {}) or {}).get("arch") or ck.get("arch")
    hp = contextformer6m_hparams(pvt_pretrained=False)
    model = ObsWorldB4Exclusive(hp, contract_cfg=ck.get("contract_cfg", {"state_dim": 256}))
    if arch == "ObsWorldB4Exclusive":
        model.load_state_dict(ck["b4_state_dict"], strict=False)
    else:                                                              # allow evaluating a Phase-I warm-start too
        load_exclusive_from_b4(model, ck["b4_state_dict"])
    print(f"[excl] loaded {ckpt_path} arch={arch} alpha={float(model.alpha):.3f} route={model.ROUTE_VERSION}")
    return model.to(device).eval()


@contextlib.contextmanager
def _alpha_zero(model):
    a = model.alpha.clone(); model.alpha.zero_()
    try:
        yield
    finally:
        model.alpha.copy_(a)


def _predict_weather(model, data, uf_x):
    """context_prior FIXED (never sees future weather); ONLY T sees the intervened weather."""
    prior, z_t = model._prior_state(data)
    hr = data["dynamic"][0]; B, H, W = hr.shape[0], hr.shape[-2], hr.shape[-1]
    geo, _ = model._geo_weather(data)
    resid = model._direct_residual(z_t, uf_x, geo, B, H, W)
    return prior + model.alpha * resid


def _uf(model, data):
    cl, tl = model.context_len, model.target_len
    return data["dynamic"][1][:, cl:cl + tl]


def _composed_broken(model, prior, z_t, uf, geo, h1, h2, B, H, W):
    """ASYMMETRIC control: leg-1 correct, leg-2 gets the WRONG weather window (uf[:, :h2] from t,
    not uf[:, h1:h1+h2] from t+h1) -> breaks ONLY the composed path's weather/time correspondence.
    Direct path is never touched."""
    bp = z_t.shape[0]
    d1 = model._to_patch(model.weather_enc.window(uf[:, :h1]), bp)
    he1 = model.time_emb(torch.full((bp,), h1, device=z_t.device, dtype=torch.long))
    z_mid = model.transition(z_t, model._cond(d1, geo, he1))
    d2 = model._to_patch(model.weather_enc.window(uf[:, :h2]), bp)      # WRONG window (misaligned)
    he2 = model.time_emb(torch.full((bp,), h2, device=z_t.device, dtype=torch.long))
    z_cmp = model.transition(z_mid, model._cond(d2, geo, he2))
    return prior[:, h1 + h2 - 1] + model.alpha * model._decode_state(z_cmp, B, H, W)


def _driver_deltas(model, ds, idx_of, targets, dev, mode, donor_uf=None, bs=1, workers=0):
    import numpy as np
    cl, tl = model.context_len, model.target_len
    sd, oa, osg = [], [], []
    for data in _batch_iter(ds, targets, idx_of, dev, bs, workers):
        with torch.no_grad():
            prior, z_t = model._prior_state(data); geo, uf_m = model._geo_weather(data)
            B, H, W = data["dynamic"][0].shape[0], data["dynamic"][0].shape[-2], data["dynamic"][0].shape[-1]
            uf_x = uf_m if mode == "matched" else (torch.zeros_like(uf_m) if mode == "mean" else donor_uf(data))
            Np = z_t.shape[0] // B
            zh_m = model.direct_state(z_t, uf_m, geo, tl).view(B, Np, -1)
            zh_x = model.direct_state(z_t, uf_x, geo, tl).view(B, Np, -1)
            y_m = (prior + model.alpha * model._direct_residual(z_t, uf_m, geo, B, H, W))[:, tl - 1, 0:1]
            y_x = (prior + model.alpha * model._direct_residual(z_t, uf_x, geo, B, H, W))[:, tl - 1, 0:1]
            lc = data["landcover"]; veg = ((lc >= model.lc_min) & (lc <= model.lc_max)).float()
            cloud = (data["dynamic_mask"][0][:, cl + tl - 1] < 1.0).float(); valid = veg * cloud
            for n in range(B):
                vn = valid[n:n + 1]; den = vn.sum() + 1e-8; diff = y_x[n:n + 1] - y_m[n:n + 1]
                sd.append((zh_x[n] - zh_m[n]).abs().mean().item())
                oa.append(((diff.abs() * vn).sum() / den).item()); osg.append(((diff * vn).sum() / den).item())
    return {"mean_state_delta": float(np.mean(sd)), "mean_out_abs_delta": float(np.mean(oa)),
            "mean_out_signed_delta": float(np.mean(osg)), "per_cube": {"state": sd, "abs": oa, "signed": osg}}


def _q3_arm(model, ds, idx_of, targets, dev, mode, m_arm, r_arm, r_full, m_full, donor_uf=None, bs=1, workers=0):
    import numpy as np
    dd = _driver_deltas(model, ds, idx_of, targets, dev, mode, donor_uf, bs=bs, workers=workers)
    pc = dd["per_cube"]
    return {"metrics": m_arm,
            "metric_diff_vs_matched_R2_overall": m_arm.get("R2", float("nan")) - m_full.get("R2", float("nan")),
            "metric_diff_percube_bootstrap95": _bootstrap_ci(_paired_deltas(r_arm, r_full)),
            "state_delta": {"mean": dd["mean_state_delta"], "bootstrap95": _bootstrap_ci(pc["state"])},
            "output_abs_delta": {"mean": dd["mean_out_abs_delta"], "bootstrap95": _bootstrap_ci(pc["abs"])},
            "output_signed_delta": {"mean": dd["mean_out_signed_delta"], "bootstrap95": _bootstrap_ci(pc["signed"]),
                                    "direction_frac_negative": float(np.mean([x < 0 for x in pc["signed"]]))}}


def _q4(model, ds, idx_of, targets, dev, guard_max, guard_sha, official_R2, bs=1, workers=0):
    import numpy as np
    cl, tl = model.context_len, model.target_len
    parts = {"train": model.partitions, "heldout": model.heldout_partitions}
    acc = {"train": {}, "heldout": {}}
    st = {h: {"std": [], "eff_rank": [], "movement": []} for h in (1, 5, 10, 20)}
    for data in _batch_iter(ds, targets, idx_of, dev, bs, workers):
        with torch.no_grad():
            prior, z_t = model._prior_state(data); geo, uf = model._geo_weather(data)
            B, H, W = data["dynamic"][0].shape[0], data["dynamic"][0].shape[-2], data["dynamic"][0].shape[-1]
            Np = z_t.shape[0] // B; z_bn = z_t.view(B, Np, -1)
            lc = data["landcover"]; lcm = ((lc >= model.lc_min) & (lc <= model.lc_max)).float()
            targ = data["dynamic"][0][:, cl:cl + tl, 0:1]; cloud = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).float()
            for h in (1, 5, 10, 20):
                zh = model.direct_state(z_t, uf, geo, h).view(B, Np, -1)
                for n in range(B):
                    st[h]["std"].append(model.state_std(zh[n])); st[h]["eff_rank"].append(model.effective_rank(zh[n]))
                    st[h]["movement"].append((zh[n] - z_bn[n]).abs().mean().item())
            for split, plist in parts.items():
                for (h1, h2) in plist:
                    h = h1 + h2
                    z_dir = model.direct_state(z_t, uf, geo, h).view(B, Np, -1)
                    z_cmp = model.composed_state(z_t, uf, geo, h1, h2).view(B, Np, -1)
                    y_dir = prior[:, h - 1] + model.alpha * model._decode_state(model.direct_state(z_t, uf, geo, h), B, H, W)
                    y_cmp = model._composed_pred(prior, z_t, uf, geo, h1, h2, B, H, W)
                    y_cmp_bk = _composed_broken(model, prior, z_t, uf, geo, h1, h2, B, H, W)   # ASYMMETRIC control
                    key = f"{h1}+{h2}"
                    a = acc[split].setdefault(key, {"dir": [], "cmp": [], "gap": [], "sgap": [], "gap_bk": []})
                    for n in range(B):
                        th, ch, lm = targ[n:n + 1, h - 1], cloud[n:n + 1, h - 1], lcm[n:n + 1]
                        a["dir"].append(model._masked_mse1(y_dir[n:n + 1], th, ch, lm).item())
                        a["cmp"].append(model._masked_mse1(y_cmp[n:n + 1], th, ch, lm).item())
                        a["gap"].append(model._masked_mse1(y_cmp[n:n + 1], y_dir[n:n + 1], ch, lm).item())
                        a["sgap"].append((z_cmp[n] - z_dir[n]).abs().mean().item())
                        a["gap_bk"].append(model._masked_mse1(y_cmp_bk[n:n + 1], y_dir[n:n + 1], ch, lm).item())
    out = {"caliber": _Q4_CALIBER, "official_overall_R2_reference": official_R2,
           "guard_endpoint_max": guard_max, "guard_config_sha256": guard_sha,
           "guard_status": "UNSET_FAIL_CLOSED" if guard_max is None else "SET_FROZEN",
           "control_note": "asymmetric: broken control misaligns ONLY the composed leg-2 weather window "
                           "(direct untouched). composed-vs-direct gap << broken gap => real weather-time composition.",
           "state": {f"h={h}": {"std": float(np.mean(v["std"])), "eff_rank": float(np.mean(v["eff_rank"])),
                                "movement": float(np.mean(v["movement"]))} for h, v in st.items()}}
    for split in ("train", "heldout"):
        out[split] = {}
        for p, v in acc[split].items():
            ed, ec, gp, gbk = (float(np.mean(v[k])) for k in ("dir", "cmp", "gap", "gap_bk"))
            verdict = "UNSET_FAIL_CLOSED" if guard_max is None else ("PASS" if (ed <= guard_max and ec <= guard_max) else "FAIL")
            out[split][p] = {"diagnostic_endpoint_dir_mse_modelspace": ed, "diagnostic_endpoint_cmp_mse_modelspace": ec,
                             "guard_verdict": verdict,
                             "diagnostic_path_gap_mse_modelspace": {"mean": gp, "bootstrap95": _bootstrap_ci(v["gap"])},
                             "diagnostic_state_path_gap": {"mean": float(np.mean(v["sgap"])), "bootstrap95": _bootstrap_ci(v["sgap"])},
                             "control_broken_composed_leg2_gap": gbk,
                             "composition_ratio_real_over_broken": gp / (gbk + 1e-12)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True); ap.add_argument("--val-dir", required=True)
    ap.add_argument("--data-manifest", default=""); ap.add_argument("--dataset-root", default="")
    ap.add_argument("--split", default="val"); ap.add_argument("--output-dir", required=True)
    ap.add_argument("--donor-manifest", default=""); ap.add_argument("--guard-config", default="")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=1); ap.add_argument("--num-data-workers", type=int, default=4)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    formal = not args.limit
    if formal and not (args.data_manifest and args.dataset_root):
        raise SystemExit("REFUSED: FORMAL exclusive contract needs --data-manifest + --dataset-root.")
    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
    dev = torch.device(args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu")
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    root = Path(args.dataset_root or args.val_dir)
    ckpt_sha0 = _sha(args.ckpt)
    model = load_exclusive(args.ckpt, dev)
    ds = GreenEarthNetContextformerDataset(args.val_dir, dl_cloudmask=True)
    idx_of = {str(Path(p)): i for i, p in enumerate(ds.filepaths)}
    targets = _targets(args, ds, root)
    data_hash = _sha(args.data_manifest) if args.data_manifest else f"SMOKE_LIMIT_{args.limit}"
    guard_max, guard_sha = (None, None)
    if args.guard_config:
        guard_max, guard_sha, _ = _load_guard_config(args.guard_config)
    prov = {"checkpoint_sha256": ckpt_sha0, "data_manifest_sha256": data_hash,
            "donor_manifest_sha256": _sha(args.donor_manifest) if args.donor_manifest else None,
            "guard_config_sha256": guard_sha, "evaluator_commit": _evaluator_commit(),
            "route_version": model.ROUTE_VERSION, "split": args.split, "formal": formal, "n_targets": len(targets)}
    R = {"checkpoint": str(Path(args.ckpt).resolve()), "provenance": prov, "command": " ".join(sys.argv),
         "status": "COMPLETE", "incomplete_reasons": []}
    bw = dict(bs=args.batch_size, workers=args.num_data_workers)

    def _run(arm, ctx, predict):
        pdir, sdir = out / f"{arm}/pred", out / f"{arm}/score"; tag = {**prov, "arm": arm}
        with ctx:
            status = _export(model, ds, idx_of, targets, pdir, predict, dev, tag, **bw)
        if status == "written" and sdir.exists():
            shutil.rmtree(sdir)
        return _score(targets, pdir, sdir, args.workers), _per_cube_r2(sdir)

    # ---- Q1 + Q2 (alpha=0 & T-identity) ----
    m_full, r_full = _run("q1_full", contextlib.nullcontext(), lambda m, d: m.forecast(d))
    m_a0, r_a0 = _run("q2_alpha0", _alpha_zero(model), lambda m, d: m.forecast(d))
    m_ti, r_ti = _run("q2_Tid", _t_identity(model), lambda m, d: m.forecast(d))
    ci_a0, ci_ti = _bootstrap_ci(_paired_deltas(r_full, r_a0)), _bootstrap_ci(_paired_deltas(r_full, r_ti))
    R["Q1_forecast"] = {"full": m_full}
    R["Q2_load_bearing"] = {"full": m_full, "alpha0": m_a0, "T_identity": m_ti,
                            "official_R2_full_minus_alpha0": m_full.get("R2", float("nan")) - m_a0.get("R2", float("nan")),
                            "official_R2_full_minus_Tid": m_full.get("R2", float("nan")) - m_ti.get("R2", float("nan")),
                            "closure_cut_alpha0": {"paired": _paired_diff(r_full, r_a0), "bootstrap95": ci_a0},
                            "transition_identity": {"paired": _paired_diff(r_full, r_ti), "bootstrap95": ci_ti},
                            "verdict": ("LOAD_BEARING" if (ci_a0.get("significant_gt0") and ci_ti.get("significant_gt0"))
                                        else "NOT_LOAD_BEARING (CI crosses 0 on alpha0 and/or T-identity)")}

    # ---- Q3 (T-only weather) ----
    m_mean, r_mean = _run("q3_mean", contextlib.nullcontext(),
                          lambda m, d: _predict_weather(m, d, torch.zeros_like(_uf(m, d))))
    noise = _driver_deltas(model, ds, idx_of, targets, dev, "matched", **bw)
    q3 = {"matched": m_full, "noise_floor_matched": {"state": noise["mean_state_delta"], "abs": noise["mean_out_abs_delta"]},
          "mean": _q3_arm(model, ds, idx_of, targets, dev, "mean", m_mean, r_mean, r_full, m_full, **bw)}
    if args.donor_manifest:
        donors = json.loads(Path(args.donor_manifest).read_text())
        errs = validate_donor_manifest(donors, targets, root)
        if errs:
            R["status"] = "INCOMPLETE_FAIL_CLOSED"; R["incomplete_reasons"].append({"donor": errs[:20]})
            q3["donor"] = {"status": "FAIL_CLOSED", "errors": errs[:20]}
        else:
            pairs = donors.get("pairs", {})
            def donor_uf(data):
                cl, tl = model.context_len, model.target_len; ws = []
                for fp in data["filepath"]:
                    dr = _donor_rel(pairs[str(Path(fp).relative_to(root))]); di = idx_of[str(root / dr)]
                    ws.append(ds[di]["dynamic"][1][cl:cl + tl])
                return torch.stack(ws).to(dev)
            m_don, r_don = _run("q3_donor", contextlib.nullcontext(), lambda m, d: _predict_weather(m, d, donor_uf(d)))
            q3["donor"] = {"donor_schema": donors.get("donor_schema"),
                           **_q3_arm(model, ds, idx_of, targets, dev, "donor", m_don, r_don, r_full, m_full, donor_uf=donor_uf, **bw)}
    else:
        q3["donor"] = {"status": "FAIL_CLOSED", "reason": "no --donor-manifest"}
        if formal:
            R["status"] = "INCOMPLETE_FAIL_CLOSED"; R["incomplete_reasons"].append("Q3 donor missing")
    R["Q3_driver"] = q3

    # ---- Q4 (exclusive composed + asymmetric broken control) ----
    R["Q4_composition"] = _q4(model, ds, idx_of, targets, dev, guard_max, guard_sha, m_full.get("R2"), **bw)
    if guard_max is None and formal:
        R["status"] = "INCOMPLETE_FAIL_CLOSED"; R["incomplete_reasons"].append("Q4 guard UNSET")

    R["checkpoint_unchanged"] = (_sha(args.ckpt) == ckpt_sha0)
    assert R["checkpoint_unchanged"], "checkpoint changed!"
    (out / "state_contract_exclusive.json").write_text(json.dumps(R, indent=2, allow_nan=True))
    print(f"[excl-contract] status={R['status']} Q2={R['Q2_load_bearing']['verdict']} out={out}")
    return 0 if R["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
