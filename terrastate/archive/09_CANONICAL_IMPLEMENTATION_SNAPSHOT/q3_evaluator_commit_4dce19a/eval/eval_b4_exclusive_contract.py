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
from eval.b4_donor_schema import validate_donor_manifest_exclusive  # noqa: E402  (Q3 donor v2 checks)


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


def parse_sections(s):
    """Which contract sections to run. 'all' -> q1,q2,q3,q4. Q2 implies Q1 (needs `full`).
    q1q2-only mode skips the expensive Q3 driver + Q4 composition and does NOT require a
    donor manifest or a frozen guard."""
    if not s or s.strip().lower() == "all":
        return {"q1", "q2", "q3", "q4"}
    out = {x.strip().lower() for x in s.replace("q1q2", "q1,q2").split(",") if x.strip()}
    if "q2" in out:
        out.add("q1")
    return out


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


def _hash_tensor(t) -> str:
    import hashlib
    return hashlib.sha256(t.detach().cpu().to(torch.float32).numpy().tobytes()).hexdigest()


Q2_DR2_FLOOR = 0.005   # spec 七: qualifier effect-size floor (reviewer-facing convention, NOT derived; see provenance)


def _state_dict_hash(m) -> str:
    import hashlib
    h = hashlib.sha256()
    sd = m.state_dict()
    for k in sorted(sd):
        h.update(k.encode()); h.update(sd[k].detach().cpu().to(torch.float32).numpy().tobytes())
    return h.hexdigest()


def _load_q3_threshold(path):
    """Frozen, sha-pinned Q3 practical-effect floor (三.8): pre-registered from Phase-I noise
    BEFORE Stage-B. Fail-closed on null/missing fields."""
    cfg = json.loads(Path(path).read_text())
    for k in ("min_output_abs_delta", "min_matched_minus_arm_dr2"):
        v = cfg.get(k)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise SystemExit(f"REFUSED: q3-threshold-config missing/non-numeric '{k}' (fail-closed).")
    return cfg, _sha(path)


def _q2_invariants(model, ds, idx_of, targets, dev):
    """In-memory Q2 invariants (spec 七.1-3): alpha0-forecast==context_prior byte/allclose;
    T-identity makes transition output==input state; live weights restored after interventions."""
    data = next(iter(_batch_iter(ds, targets[:1], idx_of, dev, 1, 0)))
    h0 = _state_dict_hash(model)
    with torch.no_grad():
        prior, z_t = model._prior_state(data); geo, uf = model._geo_weather(data)
        with _alpha_zero(model):
            pa0 = model.forecast(data)
        alpha0_eq_prior = bool(torch.allclose(pa0, prior, atol=1e-6))
        h_a0 = _state_dict_hash(model)
        with _t_identity(model):
            zid_ok = all(bool(torch.allclose(model.direct_state(z_t, uf, geo, h), z_t, atol=1e-6)) for h in (5, 10, 20))
        h_ti = _state_dict_hash(model)
    return {"alpha0_pred_equals_context_prior": alpha0_eq_prior,
            "T_identity_is_state_identity": zid_ok,
            "live_weights_restored": bool(h_a0 == h0 and h_ti == h0)}


def _driver_deltas(model, ds, idx_of, targets, dev, mode, donor_uf=None, bs=1, workers=0, horizons=(5, 10, 20)):
    """Per-cube weather-driver response at MULTIPLE horizons (spec 三.6). Top-level keys keep
    the endpoint (h=target_len) values for back-compat; per_h[h] adds {5,10,20}. `prior_sha`
    lists the weather-free context-prior hash per batch, so the caller can assert it is
    byte-identical across weather arms — any output change must then come only from T (三.7d)."""
    import numpy as np
    cl, tl = model.context_len, model.target_len
    hs = tuple(sorted({int(h) for h in horizons} | {tl}))
    acc = {h: {"state": [], "abs": [], "signed": []} for h in hs}
    prior_sha = []
    for data in _batch_iter(ds, targets, idx_of, dev, bs, workers):
        with torch.no_grad():
            prior, z_t = model._prior_state(data); geo, uf_m = model._geo_weather(data)
            B, H, W = data["dynamic"][0].shape[0], data["dynamic"][0].shape[-2], data["dynamic"][0].shape[-1]
            uf_x = uf_m if mode == "matched" else (torch.zeros_like(uf_m) if mode == "mean" else donor_uf(data))
            Np = z_t.shape[0] // B
            res_m = model._direct_residual(z_t, uf_m, geo, B, H, W)
            res_x = model._direct_residual(z_t, uf_x, geo, B, H, W)
            lc = data["landcover"]; veg = ((lc >= model.lc_min) & (lc <= model.lc_max)).float()
            prior_sha.append(_hash_tensor(prior))
            for h in hs:
                zh_m = model.direct_state(z_t, uf_m, geo, h).view(B, Np, -1)
                zh_x = model.direct_state(z_t, uf_x, geo, h).view(B, Np, -1)
                y_m = (prior + model.alpha * res_m)[:, h - 1, 0:1]
                y_x = (prior + model.alpha * res_x)[:, h - 1, 0:1]
                cloud = (data["dynamic_mask"][0][:, cl + h - 1] < 1.0).float(); valid = veg * cloud
                for n in range(B):
                    vn = valid[n:n + 1]; den = vn.sum() + 1e-8; diff = y_x[n:n + 1] - y_m[n:n + 1]
                    acc[h]["state"].append((zh_x[n] - zh_m[n]).abs().mean().item())
                    acc[h]["abs"].append(((diff.abs() * vn).sum() / den).item())
                    acc[h]["signed"].append(((diff * vn).sum() / den).item())
    def _mean(x):
        return float(np.mean(x)) if x else 0.0
    per_h = {h: {"mean_state_delta": _mean(acc[h]["state"]), "mean_out_abs_delta": _mean(acc[h]["abs"]),
                 "mean_out_signed_delta": _mean(acc[h]["signed"]), "per_cube": acc[h]} for h in hs}
    end = per_h[tl]
    return {"mean_state_delta": end["mean_state_delta"], "mean_out_abs_delta": end["mean_out_abs_delta"],
            "mean_out_signed_delta": end["mean_out_signed_delta"], "per_cube": acc[tl],
            "per_h": per_h, "prior_sha": prior_sha, "horizons": list(hs)}


def _q3_arm(model, ds, idx_of, targets, dev, mode, m_arm, r_arm, r_full, m_full, donor_uf=None, bs=1, workers=0):
    """SIGN CONVENTION (spec 三.1): matched_minus_arm = per-cube R2_matched - R2_arm; positive
    => matched more predictive. CI_low>0 <=> matched significantly better (三.2)."""
    import numpy as np
    dd = _driver_deltas(model, ds, idx_of, targets, dev, mode, donor_uf, bs=bs, workers=workers)
    pc = dd["per_cube"]
    per_h = {f"h={h}": {"state_delta_mean": v["mean_state_delta"], "output_abs_delta_mean": v["mean_out_abs_delta"],
                        "output_abs_delta_bootstrap95": _bootstrap_ci(v["per_cube"]["abs"])}
             for h, v in dd["per_h"].items()}
    return {"metrics": m_arm,
            "matched_minus_arm_R2_overall": m_full.get("R2", float("nan")) - m_arm.get("R2", float("nan")),
            "matched_minus_arm_percube_bootstrap95": _bootstrap_ci(_paired_deltas(r_full, r_arm)),
            "matched_minus_arm_win_tie_loss": _paired_diff(r_full, r_arm),
            "state_delta": {"mean": dd["mean_state_delta"], "bootstrap95": _bootstrap_ci(pc["state"])},
            "output_abs_delta": {"mean": dd["mean_out_abs_delta"], "bootstrap95": _bootstrap_ci(pc["abs"])},
            "output_signed_delta": {"mean": dd["mean_out_signed_delta"], "bootstrap95": _bootstrap_ci(pc["signed"]),
                                    "direction_frac_negative_DIAGNOSTIC_ONLY": float(np.mean([x < 0 for x in pc["signed"]]))},
            "per_horizon": per_h,
            "_prior_sha": dd["prior_sha"]}


def _cube_clustered_bootstrap(per_cube_blocks, n_boot=10000, seed=0, alpha=0.05):
    """Cube-CLUSTERED bootstrap (spec 六.9): resample CUBES (not partition-values); each cube
    contributes ALL its partition values as a block. Grand mean = Σvals/Σcount over sampled cubes."""
    import numpy as np
    blocks = [b for b in per_cube_blocks]
    ncube = len(blocks)
    if ncube == 0:
        return {"mean": None, "ci_low": None, "ci_high": None, "significant_gt0": False, "n_cubes": 0}
    sums = np.array([float(np.sum(b)) if len(b) else 0.0 for b in blocks])
    cnts = np.array([float(len(b)) for b in blocks])
    grand = float(sums.sum() / max(cnts.sum(), 1.0))
    rng = np.random.default_rng(seed)
    take = rng.integers(0, ncube, size=(n_boot, ncube))
    bsum = sums[take].sum(1); bcnt = cnts[take].sum(1)
    boots = np.where(bcnt > 0, bsum / np.maximum(bcnt, 1.0), 0.0)
    lo, hi = (float(x) for x in np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)]))
    return {"mean": grand, "ci_low": lo, "ci_high": hi, "significant_gt0": bool(lo > 0), "n_cubes": ncube}


def _q4(model, ds, idx_of, targets, dev, guard_max, guard_sha, official_R2, bs=1, workers=0, ni_margin=0.05, q2_pass=None):
    import numpy as np
    cl, tl = model.context_len, model.target_len
    parts = {"train": model.partitions, "heldout": model.heldout_partitions}
    acc = {"train": {}, "heldout": {}}
    HS = (1, 5, 10, 20)
    st = {h: {"std": [], "eff_rank": [], "movement": [], "std_ratio": [], "eff_rank_ratio": []} for h in HS}
    zt_std, zt_eff = [], []
    for data in _batch_iter(ds, targets, idx_of, dev, bs, workers):
        with torch.no_grad():
            prior, z_t = model._prior_state(data); geo, uf = model._geo_weather(data)
            B, H, W = data["dynamic"][0].shape[0], data["dynamic"][0].shape[-2], data["dynamic"][0].shape[-1]
            Np = z_t.shape[0] // B; z_bn = z_t.view(B, Np, -1)
            lc = data["landcover"]; lcm = ((lc >= model.lc_min) & (lc <= model.lc_max)).float()
            targ = data["dynamic"][0][:, cl:cl + tl, 0:1]; cloud = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).float()
            zts = [model.state_std(z_bn[n]) for n in range(B)]
            zte = [model.effective_rank(z_bn[n]) for n in range(B)]
            zt_std.extend(zts); zt_eff.extend(zte)
            for h in HS:
                zh = model.direct_state(z_t, uf, geo, h).view(B, Np, -1)
                for n in range(B):
                    s_h = model.state_std(zh[n]); e_h = model.effective_rank(zh[n])
                    st[h]["std"].append(s_h); st[h]["eff_rank"].append(e_h)
                    st[h]["movement"].append((zh[n] - z_bn[n]).abs().mean().item())
                    st[h]["std_ratio"].append(s_h / (zts[n] + 1e-8)); st[h]["eff_rank_ratio"].append(e_h / (zte[n] + 1e-8))
            for split, plist in parts.items():
                for (h1, h2) in plist:
                    h = h1 + h2
                    z_dir = model.direct_state(z_t, uf, geo, h).view(B, Np, -1)
                    z_cmp = model.composed_state(z_t, uf, geo, h1, h2).view(B, Np, -1)
                    y_dir = prior[:, h - 1] + model.alpha * model._decode_state(model.direct_state(z_t, uf, geo, h), B, H, W)
                    y_cmp = model._composed_pred(prior, z_t, uf, geo, h1, h2, B, H, W)
                    y_cmp_bk = _composed_broken(model, prior, z_t, uf, geo, h1, h2, B, H, W)   # ASYMMETRIC control
                    key = f"{h1}+{h2}"
                    a = acc[split].setdefault(key, {"dir": [], "cmp": [], "gap": [], "sgap": [], "gap_bk": [], "A": [], "nid": []})
                    for n in range(B):
                        th, ch, lm = targ[n:n + 1, h - 1], cloud[n:n + 1, h - 1], lcm[n:n + 1]
                        ed_i = model._masked_mse1(y_dir[n:n + 1], th, ch, lm).item()
                        ec_i = model._masked_mse1(y_cmp[n:n + 1], th, ch, lm).item()
                        gp_i = model._masked_mse1(y_cmp[n:n + 1], y_dir[n:n + 1], ch, lm).item()
                        gbk_i = model._masked_mse1(y_cmp_bk[n:n + 1], y_dir[n:n + 1], ch, lm).item()
                        a["dir"].append(ed_i); a["cmp"].append(ec_i); a["gap"].append(gp_i)
                        a["sgap"].append((z_cmp[n] - z_dir[n]).abs().mean().item())
                        a["gap_bk"].append(gbk_i); a["A"].append(gbk_i - gp_i); a["nid"].append(ec_i - ed_i)

    def npmean(x):
        return float(np.mean(x)) if len(x) else 0.0
    state_block = {f"h={h}": {"std": npmean(v["std"]), "eff_rank": npmean(v["eff_rank"]), "movement": npmean(v["movement"]),
                              "std_ratio": npmean(v["std_ratio"]), "eff_rank_ratio": npmean(v["eff_rank_ratio"]),
                              "across_cube_movement_var": float(np.var(v["movement"])) if v["movement"] else 0.0}
                   for h, v in st.items()}
    out = {"caliber": _Q4_CALIBER, "official_overall_R2_reference": official_R2,
           "noninferiority_rel_margin": ni_margin, "abs_endpoint_guard_max": guard_max, "guard_config_sha256": guard_sha,
           "guard_status": "UNSET_FAIL_CLOSED" if guard_max is None else "SET_FROZEN",
           "control_note": "asymmetric broken control misaligns ONLY the composed leg-2 weather window (direct untouched). "
                           "A_comp = gap_broken - gap_real (cube-paired); positive => real composition holds. "
                           "This certifies a LEARNED weather-controlled composition/cocycle consistency on the frozen splits, "
                           "NOT a strict semigroup/flow theorem.",
           "state_zt": {"std": npmean(zt_std), "eff_rank": npmean(zt_eff)}, "state": state_block}
    for split in ("train", "heldout"):
        out[split] = {}
        for p, v in acc[split].items():
            ed, ec, gp, gbk = (npmean(v[k]) for k in ("dir", "cmp", "gap", "gap_bk"))
            ni_ci = _bootstrap_ci(v["nid"]); a_ci = _bootstrap_ci(v["A"])
            ni_pass = bool(ec <= ed * (1.0 + ni_margin)) if guard_max is not None else None
            abs_guard = None if guard_max is None else bool(ed <= guard_max and ec <= guard_max)
            out[split][p] = {"endpoint_direct_mse": ed, "endpoint_composed_mse": ec,
                             "endpoint_composed_minus_direct": {"mean": ec - ed, "bootstrap95": ni_ci},
                             "noninferiority_rel_pass": ni_pass, "abs_endpoint_guard_pass": abs_guard,
                             "output_path_gap": {"mean": gp, "bootstrap95": _bootstrap_ci(v["gap"])},
                             "state_path_gap": {"mean": npmean(v["sgap"]), "bootstrap95": _bootstrap_ci(v["sgap"])},
                             "broken_control_gap": gbk,
                             "broken_minus_real_advantage_A_comp": {"mean": npmean(v["A"]), "bootstrap95": a_ci,
                                                                    "significant_gt0": bool(a_ci.get("significant_gt0"))},
                             "composition_ratio_real_over_broken_AUX": gp / (gbk + 1e-12)}
    # ---- pooled held-out cube-clustered A_comp + composite Q4 verdict (spec 六.8-9) ----
    ho = acc["heldout"]; ho_keys = list(ho.keys())
    ncube = len(next(iter(ho.values()))["A"]) if ho else 0
    blocks = [[ho[k]["A"][n] for k in ho_keys] for n in range(ncube)] if ncube else []
    pooled = _cube_clustered_bootstrap(blocks)
    ratios = {k: (npmean(ho[k]["gap"]) / (npmean(ho[k]["gap_bk"]) + 1e-12)) for k in ho_keys}
    n_ratio_lt1 = sum(1 for r in ratios.values() if r < 1.0)
    ho_ni_all = (guard_max is not None) and all(out["heldout"][k]["noninferiority_rel_pass"] for k in ho_keys)
    ret_floor = 0.5
    ret_pass = bool(state_block.get("h=20", {}).get("std_ratio", 0.0) >= ret_floor
                    and state_block.get("h=20", {}).get("eff_rank_ratio", 0.0) >= ret_floor)
    out["heldout_pooled_A_comp_cube_clustered"] = pooled
    out["heldout_ratio_real_over_broken"] = ratios
    need_ratio = max(1, len(ho_keys) // 2)
    conds = {"heldout_noninferiority_all_pass": bool(ho_ni_all),
             "pooled_heldout_A_comp_CI_low_gt0": bool(pooled.get("significant_gt0")),
             "n_heldout_ratio_lt1": n_ratio_lt1, "need_ratio_lt1_ge": need_ratio,
             "retention_pass": ret_pass, "retention_floor": ret_floor, "Q2_load_bearing_pass": bool(q2_pass)}
    if guard_max is None:
        out["verdict"] = "UNSET_FAIL_CLOSED"
    else:
        out["verdict"] = ("Q4_PASS" if (ho_ni_all and pooled.get("significant_gt0") and n_ratio_lt1 >= need_ratio
                                        and ret_pass and bool(q2_pass)) else "Q4_FAIL")
    out["verdict_conditions"] = conds
    out["heldout_note_h20"] = ("(10,10)->h=20 composition is NEVER trained (cmp/con reach h<=10); it is EXTRAPOLATION, "
                               "reported as diagnostic-only evidence, not a trained guarantee.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True); ap.add_argument("--val-dir", required=True)
    ap.add_argument("--data-manifest", default=""); ap.add_argument("--dataset-root", default="")
    ap.add_argument("--split", default="val"); ap.add_argument("--output-dir", required=True)
    ap.add_argument("--donor-manifest", default=""); ap.add_argument("--guard-config", default="")
    ap.add_argument("--q3-threshold-config", default="", help="FROZEN sha-pinned Q3 practical-effect floor (Phase-I-noise-derived); FORMAL fail-closed if absent")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=1); ap.add_argument("--num-data-workers", type=int, default=4)
    ap.add_argument("--sections", default="all", help="'all' or subset of q1,q2,q3,q4 (or 'q1q2'). q1q2 skips Q3/Q4 and needs no donor/guard.")
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()
    sections = parse_sections(args.sections)

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
    guard_max, guard_sha, ni_margin = (None, None, 0.05)
    if args.guard_config:
        guard_max, guard_sha, guard_cfg = _load_guard_config(args.guard_config)
        if isinstance(guard_cfg, dict):
            ni_margin = float(guard_cfg.get("noninferiority_rel_margin", 0.05))
    _ck = torch.load(args.ckpt, map_location="cpu", weights_only=False)          # stage/freeze_b0 for provenance
    ck_stage = _ck.get("stage")
    ck_freeze_b0 = (_ck.get("contract_cfg", {}) or {}).get("freeze_b0", getattr(model, "freeze_b0", None))
    q3_floor, q3_floor_sha = _load_q3_threshold(args.q3_threshold_config) if args.q3_threshold_config else (None, None)
    prov = {"checkpoint_sha256": ckpt_sha0, "data_manifest_sha256": data_hash,
            "donor_manifest_sha256": _sha(args.donor_manifest) if args.donor_manifest else None,
            "guard_config_sha256": guard_sha, "q3_threshold_config_sha256": q3_floor_sha,
            "evaluator_commit": _evaluator_commit(), "checkpoint_stage": ck_stage, "checkpoint_freeze_b0": ck_freeze_b0,
            "route_version": model.ROUTE_VERSION, "split": args.split, "formal": formal, "n_targets": len(targets)}
    R = {"checkpoint": str(Path(args.ckpt).resolve()), "provenance": {**prov, "sections": sorted(sections)},
         "command": " ".join(sys.argv), "status": "COMPLETE", "incomplete_reasons": []}
    bw = dict(bs=args.batch_size, workers=args.num_data_workers)

    def _run(arm, ctx, predict):
        pdir, sdir = out / f"{arm}/pred", out / f"{arm}/score"; tag = {**prov, "arm": arm}
        with ctx:
            status = _export(model, ds, idx_of, targets, pdir, predict, dev, tag, **bw)
        if status == "written" and sdir.exists():
            shutil.rmtree(sdir)
        return _score(targets, pdir, sdir, args.workers), _per_cube_r2(sdir)

    # ---- Q1 (full) — always (Q2/Q3/Q4 all reference it) ----
    m_full, r_full = _run("q1_full", contextlib.nullcontext(), lambda m, d: m.forecast(d))
    R["Q1_forecast"] = {"full": m_full}

    # ---- Q2 (alpha=0 & T-identity) + effect-size floor + invariants (spec 七) ----
    if "q2" in sections:
        m_a0, r_a0 = _run("q2_alpha0", _alpha_zero(model), lambda m, d: m.forecast(d))
        m_ti, r_ti = _run("q2_Tid", _t_identity(model), lambda m, d: m.forecast(d))
        ci_a0, ci_ti = _bootstrap_ci(_paired_deltas(r_full, r_a0)), _bootstrap_ci(_paired_deltas(r_full, r_ti))
        dR2_a0 = m_full.get("R2", float("nan")) - m_a0.get("R2", float("nan"))
        dR2_ti = m_full.get("R2", float("nan")) - m_ti.get("R2", float("nan"))
        inv = _q2_invariants(model, ds, idx_of, targets, dev)
        sig = bool(ci_a0.get("significant_gt0") and ci_ti.get("significant_gt0"))
        floor_ok = bool(dR2_a0 >= Q2_DR2_FLOOR and dR2_ti >= Q2_DR2_FLOOR)
        clean = bool(m_ti.get("R2", 0.0) >= m_a0.get("R2", 0.0) - 1e-6)   # T-margin not below closure-off baseline (七.4)
        verdict = ("LOAD_BEARING" if (sig and floor_ok)
                   else f"NOT_LOAD_BEARING (significant={sig}, dR2>={Q2_DR2_FLOOR}:{floor_ok})")
        stage_note = None
        if ck_stage == "B" or ck_freeze_b0 is False:
            stage_note = ("Stage-B: alpha0 baseline == context_prior recomputed from the UNFROZEN q; it is NO LONGER "
                          "the frozen-B0 Q1 accuracy anchor. Re-anchored + re-checked empirically THIS run (七.5).")
        R["Q2_load_bearing"] = {"full": m_full, "alpha0": m_a0, "T_identity": m_ti,
                                "official_R2_full_minus_alpha0": dR2_a0, "official_R2_full_minus_Tid": dR2_ti,
                                "dr2_floor": Q2_DR2_FLOOR, "dr2_floor_pass": floor_ok, "significant": sig,
                                "closure_cut_alpha0": {"paired": _paired_diff(r_full, r_a0), "bootstrap95": ci_a0},
                                "transition_identity": {"paired": _paired_diff(r_full, r_ti), "bootstrap95": ci_ti},
                                "transition_margin_clean": clean,
                                "transition_margin_confound_note": ("T-identity feeds O a FROZEN z_t (OOD for O trained on "
                                                                    "evolved states); a perfectly clean transition-only ablation "
                                                                    "is not achievable on this route — margin partly reflects OOD."),
                                "invariants": inv, "stage_note": stage_note, "verdict": verdict}

    # ---- Q3 (weather driver, T-only) — matched_minus_arm sign, multi-h, total verdict (spec 三) ----
    if "q3" in sections:
        m_z, r_z = _run("q3_normalized_zero", contextlib.nullcontext(),
                        lambda m, d: _predict_weather(m, d, torch.zeros_like(_uf(m, d))))
        zero_arm = _q3_arm(model, ds, idx_of, targets, dev, "mean", m_z, r_z, r_full, m_full, **bw)
        q3 = {"matched": m_full,
              "normalized_zero_reference": {
                  "note": "future weather set to 0 in the GLOBALLY z-scored space = per-variable global training mean "
                          "(24-D mean/min/max all zeroed); NOT day-of-year/location climatology.",
                  **zero_arm},
              "direction_note": "direction_frac_negative is DIAGNOSTIC ONLY; NDVI has no unified weather sign (三.5)."}
        donor_arm = None
        if args.donor_manifest:
            donors = json.loads(Path(args.donor_manifest).read_text())
            errs = validate_donor_manifest_exclusive(donors, targets, root)   # v2: geo+season+DOY+divergence+reuse
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
                donor_arm = _q3_arm(model, ds, idx_of, targets, dev, "donor", m_don, r_don, r_full, m_full, donor_uf=donor_uf, **bw)
                q3["donor"] = {"donor_schema": donors.get("donor_schema"), **donor_arm}
        else:
            q3["donor"] = {"status": "FAIL_CLOSED", "reason": "no --donor-manifest"}
            if formal:
                R["status"] = "INCOMPLETE_FAIL_CLOSED"; R["incomplete_reasons"].append("Q3 donor missing")

        # ---- Q3 TOTAL verdict (三.7): both controls' matched-minus-arm CI_low>0, prior invariant, floors ----
        prior_invariant = (donor_arm is None or
                           list(zero_arm.get("_prior_sha", [])) == list(donor_arm.get("_prior_sha", [])))

        def _floor_ok(arm):
            if q3_floor is None or arm is None:
                return None
            outd_low = arm["output_abs_delta"]["bootstrap95"].get("ci_low")
            outd_low = outd_low if outd_low is not None else float("-inf")
            return bool(outd_low >= q3_floor["min_output_abs_delta"]
                        and arm["matched_minus_arm_R2_overall"] >= q3_floor["min_matched_minus_arm_dr2"])
        zero_pass = bool(zero_arm["matched_minus_arm_percube_bootstrap95"].get("significant_gt0"))
        donor_pass = bool(donor_arm is not None and donor_arm["matched_minus_arm_percube_bootstrap95"].get("significant_gt0"))
        conds = {"matched_minus_zero_CI_low_gt0": zero_pass, "matched_minus_donor_CI_low_gt0": donor_pass,
                 "context_prior_invariant_across_arms": prior_invariant,
                 "zero_practical_floor": _floor_ok(zero_arm), "donor_practical_floor": _floor_ok(donor_arm)}
        base_ok = zero_pass and donor_pass and prior_invariant
        if q3_floor is not None:
            q3["verdict"] = ("WEATHER_DRIVER_PASS" if (base_ok and conds["zero_practical_floor"] and conds["donor_practical_floor"])
                             else "WEATHER_DRIVER_FAIL")
        else:
            q3["verdict"] = ("INCOMPLETE_NO_FROZEN_FLOOR" if formal
                             else ("SIGNIFICANT_UNGATED" if base_ok else "NOT_SIGNIFICANT_UNGATED"))
            if formal:
                R["status"] = "INCOMPLETE_FAIL_CLOSED"; R["incomplete_reasons"].append("Q3 practical-effect floor UNSET")
        q3["verdict_conditions"] = conds
        for a in ("normalized_zero_reference", "donor"):   # drop long internal prior-sha lists before serialize
            if isinstance(q3.get(a), dict):
                q3[a].pop("_prior_sha", None)
        R["Q3_driver"] = q3

    # ---- Q4 (exclusive composed + asymmetric broken control) ----
    if "q4" in sections:
        q2_pass = R.get("Q2_load_bearing", {}).get("verdict") == "LOAD_BEARING"
        R["Q4_composition"] = _q4(model, ds, idx_of, targets, dev, guard_max, guard_sha, m_full.get("R2"),
                                  ni_margin=ni_margin, q2_pass=q2_pass, **bw)
        if guard_max is None and formal:
            R["status"] = "INCOMPLETE_FAIL_CLOSED"; R["incomplete_reasons"].append("Q4 guard UNSET")

    R["checkpoint_unchanged"] = (_sha(args.ckpt) == ckpt_sha0)
    assert R["checkpoint_unchanged"], "checkpoint changed!"
    (out / "state_contract_exclusive.json").write_text(json.dumps(R, indent=2, allow_nan=True))
    q2v = R.get("Q2_load_bearing", {}).get("verdict", "n/a")
    q3v = R.get("Q3_driver", {}).get("verdict", "n/a")
    q4v = R.get("Q4_composition", {}).get("verdict", "n/a")
    print(f"[excl-contract] status={R['status']} sections={sorted(sections)} Q2={q2v} Q3={q3v} Q4={q4v} out={out}")
    return 0 if R["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
