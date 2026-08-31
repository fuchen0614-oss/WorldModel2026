#!/usr/bin/env python
"""eval/extreme_state_audit.py -- FROZEN-protocol extreme hot-dry predictive-state audit (Q1 + state).

Runs the SAME audit on BOTH world-model architectures via eval/audit_adapters.py, stratified into the
hot-dry extreme subset vs its season/location/quality matched-normal control, and reports the CORE test
(correction 6): interaction = effect_hotdry - effect_matched_normal, with a paired and a geo-clustered
bootstrap (mean, 95% CI, n, direction). It never emits a bare PASS/FAIL and never drops a frozen metric.

Semantics (corrections 8/9): B4's base B0 still reads real future weather, so its T-identity / zero-scale
arms only isolate the ADDITIONAL state-branch contribution -- every arm carries `weather_in_base`, and B4
and exclusive numbers are reported side by side for DIAGNOSIS, never merged into one claim. Shared PRIMARY
arms are the semantically-consistent ones (full, zero-scale closure, T-identity, state-shuffle, weather
intervention); the architecture-specific broken control is not part of this tool.

Reads the frozen manifests directly (root-relative paths resolved via --dataset-root). Does NOT modify the
Phase-I / exclusive evaluators; it only imports their pure primitives.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import (  # noqa: E402
    GREENEARTHNET_CHOPPED_PROTOCOL_ID, load_manifest_files, resolve_manifest_root,
)
from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from eval.eval_b4_state_contract import _batch_iter, _export, _score, _per_cube_r2, _sha  # noqa: E402
import eval.audit_adapters as A  # noqa: E402

_TILE_RE = re.compile(r"_(\d{2}[A-Z]{3})_")


def _key(path) -> str:
    """Stable cube key = last two path components (season/cube.nc); identical under a view or the root."""
    p = Path(path)
    return f"{p.parent.name}/{p.name}"


def _tile(path) -> str:
    m = _TILE_RE.search(Path(path).name)
    return m.group(1) if m else Path(path).parent.name


def load_model(ckpt_path, device, arch_hint=None):
    """Load ObsWorldB4 / ObsWorldB4Exclusive / TerraStateV2 from a checkpoint; fresh (random) if None.

    TerraStateV2 subclasses ObsWorldB4Exclusive and reuses the exclusive T-only inference VERBATIM,
    so it is loaded into an ObsWorldB4Exclusive shell via the SAME path the Q2 evaluator uses
    (load_exclusive_from_b4), with a fail-closed exact-key check."""
    from models.plan_b_b4 import ObsWorldB4
    from models.plan_b_b4_exclusive import ObsWorldB4Exclusive, load_exclusive_from_b4
    hp = contextformer6m_hparams(pvt_pretrained=False)
    if ckpt_path is None:
        cfg = {"state_dim": 256}
        model = (ObsWorldB4Exclusive if arch_hint == "exclusive" else ObsWorldB4)(hp, contract_cfg=cfg)
        return model.to(device).eval(), {"arch": arch_hint or "b4", "ckpt": None, "sha256": None}
    ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    if not (isinstance(ck, dict) and "b4_state_dict" in ck):
        raise ValueError(f"{ckpt_path} has no b4_state_dict")
    arch = (ck.get("contract_cfg", {}) or {}).get("arch") or ck.get("arch")
    cfg = ck.get("contract_cfg", {"state_dim": 256})
    if arch == "TerraStateCandidateC":
        # Candidate C's shared segment transition would be silently dropped by the exclusive
        # shell, so build the real class and demand an exact key match.
        from models.terrastate_candidate_c import TerraStateCandidateC
        model = TerraStateCandidateC(hp, contract_cfg=cfg)
        miss, unexp = model.load_state_dict(ck["b4_state_dict"], strict=True)
        if miss or unexp:
            raise ValueError(f"{ckpt_path}: Candidate C load NOT clean: "
                             f"missing={list(miss)} unexpected={list(unexp)}")
    elif arch in ("ObsWorldB4Exclusive", "TerraStateV2"):
        model = ObsWorldB4Exclusive(hp, contract_cfg=cfg)
        miss, unexp = load_exclusive_from_b4(model, ck["b4_state_dict"])
        if miss or unexp:
            raise ValueError(f"{ckpt_path}: exclusive load NOT clean (arch={arch}): "
                             f"missing={list(miss)} unexpected={list(unexp)}")
    else:
        model = ObsWorldB4(hp, contract_cfg=cfg)
        try:
            model.load_state_dict(ck["b4_state_dict"], strict=False)
        except Exception:
            load_exclusive_from_b4(model, ck["b4_state_dict"])
    prov = {"arch": arch or "b4", "ckpt": str(Path(ckpt_path).resolve()), "sha256": _sha(ckpt_path)}
    return model.to(device).eval(), prov


def _veg_cloud_mask(data, model, ref):
    cl, tl = model.context_len, model.target_len
    lc = data["landcover"]
    lcm = ((lc >= model.lc_min) & (lc <= model.lc_max)).type_as(ref)          # (B,1,H,W)
    cloud = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).type_as(ref)        # (B,tl,1,H,W)
    return cloud * lcm.unsqueeze(1)


def _per_cube_masked_mean(delta, mask):
    num = (delta.abs() * mask).flatten(1).sum(1)
    den = mask.flatten(1).sum(1).clamp_min(1e-8)
    return (num / den).detach().cpu().numpy()


def compute_effects(model, ds, idx_of, targets, dev, bs, workers):
    """Per-cube forcing-response / state-contribution / state-movement effects, keyed by cube key."""
    out = {}
    arch = A.arch_of(model)
    wib = A.weather_in_base(model)
    for data in _batch_iter(ds, targets, idx_of, dev, bs, workers):
        with torch.no_grad():
            pred_full = A.predict(model, data)
            uf = A.future_weather(model, data)
            pred_clim = A.predict_with_weather(model, data, torch.zeros_like(uf))     # climatological-mean forcing
            pred_flip = A.predict_with_weather(model, data, torch.flip(uf, dims=[1]))  # seasonal-shuffle forcing
            with A.zero_scale_ctx(model):
                pred_closure = A.predict(model, data)
            z_t, z_h = A.extract_states(model, data, model.target_len)
        m = _veg_cloud_mask(data, model, pred_full)
        resp_clim = _per_cube_masked_mean(pred_full - pred_clim, m)
        resp_flip = _per_cube_masked_mean(pred_full - pred_flip, m)
        contrib = _per_cube_masked_mean(pred_full - pred_closure, m)
        Bn = pred_full.shape[0]                                   # z_t is (B*patches, dim) -> reshape per cube
        zt = z_t.reshape(Bn, -1); zh = z_h.reshape(Bn, -1)
        move = (torch.linalg.vector_norm(zh - zt, dim=1) /
                torch.linalg.vector_norm(zt, dim=1).clamp_min(1e-8)).detach().cpu().numpy()
        for i, fp in enumerate(data["filepath"]):
            out[_key(fp)] = dict(resp_clim=float(resp_clim[i]), resp_flip=float(resp_flip[i]),
                                 contrib_state=float(contrib[i]), state_move=float(move[i]),
                                 tile=_tile(fp), arch=arch, weather_in_base=wib)
    return out


def _arm_predict(arm):
    if arm == "full":
        return lambda m, d: A.predict(m, d)
    if arm == "closure_zero_scale":
        def f(m, d):
            with A.zero_scale_ctx(m):
                return A.predict(m, d)
        return f
    if arm == "t_identity":
        def f(m, d):
            with A.t_identity_ctx(m):
                return A.predict(m, d)
        return f
    raise ValueError(arm)


def stratum_accuracy(model, ds, idx_of, targets, dev, out_dir: Path, prov_tag: dict, bs, workers):
    """Official LC-balanced R2/RMSE per arm on ONE stratum (reuses _export + _score)."""
    res = {}
    for arm in ("full", "closure_zero_scale", "t_identity"):
        pdir = out_dir / arm / "pred"; sdir = out_dir / arm / "score"
        _export(model, ds, idx_of, targets, pdir, _arm_predict(arm), dev, {**prov_tag, "arm": arm}, bs=bs, workers=workers)
        summ = _score(targets, pdir, sdir, workers)
        res[arm] = {"R2": summ.get("R2"), "rmse": summ.get("rmse"), "nse": summ.get("nse"),
                    "biasabs": summ.get("biasabs")}
    res["weather_in_base"] = A.weather_in_base(model)
    return res


def _boot(vals, n_boot, seed, alpha=0.05):
    a = np.asarray(vals, float); a = a[np.isfinite(a)]
    if a.size == 0:
        return dict(n=0, mean=float("nan"), ci_low=float("nan"), ci_high=float("nan"),
                    frac_pos=float("nan"), significant_gt0=False)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, a.size, size=(n_boot, a.size))
    boots = a[idx].mean(axis=1)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return dict(n=int(a.size), mean=float(a.mean()), ci_low=float(lo), ci_high=float(hi),
                frac_pos=float((a > 0).mean()), significant_gt0=bool(lo > 0))


def _cluster_boot(vals, clusters, n_boot, seed, alpha=0.05):
    a = np.asarray(vals, float); c = np.asarray(clusters)
    ok = np.isfinite(a); a, c = a[ok], c[ok]
    if a.size == 0:
        return dict(n=0, n_clusters=0, mean=float("nan"), ci_low=float("nan"), ci_high=float("nan"),
                    significant_gt0=False)
    uniq = np.unique(c); rng = np.random.default_rng(seed)
    groups = {t: a[c == t] for t in uniq}
    boots = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.choice(uniq, size=uniq.size, replace=True)
        boots[b] = np.concatenate([groups[t] for t in pick]).mean()
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return dict(n=int(a.size), n_clusters=int(uniq.size), mean=float(a.mean()),
                ci_low=float(lo), ci_high=float(hi), significant_gt0=bool(lo > 0))


def interaction(effects, pairs, n_boot, seed):
    """CORE test: effect_hotdry - effect_matched_normal over matched pairs (paired + geo-clustered bootstrap)."""
    out = {}
    for eff in ("resp_clim", "resp_flip", "contrib_state", "state_move"):
        deltas, clusters, n_missing = [], [], 0
        for e_key, c_key in pairs:
            if e_key in effects and c_key in effects:
                deltas.append(effects[e_key][eff] - effects[c_key][eff])
                clusters.append(effects[e_key]["tile"])
            else:
                n_missing += 1
        out[eff] = {
            "paired_bootstrap": _boot(deltas, n_boot, seed),
            "geo_cluster_bootstrap": _cluster_boot(deltas, clusters, n_boot, seed),
            "n_missing_pairs": n_missing,
            "direction": ("hotdry>normal" if np.nanmean(deltas or [np.nan]) > 0 else "hotdry<=normal"),
        }
    return out


# ----------------------------------------------------------------------------- Q3 donor-weather fidelity
def _endpoint_masked_mse(pred, data, model, mask):
    """Per-cube masked MSE of a prediction vs the REAL future NDVI over the target window."""
    cl, tl = model.context_len, model.target_len
    target = data["dynamic"][0][:, cl:cl + tl, 0:1]
    err = (((pred - target) ** 2) * mask).flatten(1).sum(1) / mask.flatten(1).sum(1).clamp_min(1e-8)
    return err.detach().cpu().numpy()


def _parts(model, data):
    """base, z_t, geo, real-uf, (B,H,W) -- cached so an arm only re-decodes the residual (no re-encode)."""
    base, z_t = A.base_and_state(model, data)
    geo, uf = model._geo_weather(data)
    B, H, W = A._bhw(data)
    return base, z_t, geo, uf, (B, H, W)


def _decode(model, base, z_t, geo, uf, bhw):
    B, H, W = bhw
    return base + A.scale(model) * model._direct_residual(z_t, uf, geo, B, H, W)


def _data_of(ds, idx_of, path, dev):
    from eval.eval_b4_state_contract import _data
    return _data(ds, idx_of[str(Path(path))], dev)


def donor_pairs(model, ds, idx_of, pair_paths, dev):
    """PER-PAIR matched-donor intervention: swap ONLY the full24 future weather between the paired
    extreme and control cube; history / static geography / horizon / checkpoint stay fixed. The base +
    state (z_t) are computed once per cube and reused, so donor/mean arms only re-decode the residual
    with a different forcing tensor. Four arms per pair (spec 2)."""
    rows = []
    for e_path, c_path in pair_paths:
        E = _data_of(ds, idx_of, e_path, dev)
        C = _data_of(ds, idx_of, c_path, dev)
        with torch.no_grad():
            bE, zE, gE, ufE, shE = _parts(model, E)
            bC, zC, gC, ufC, shC = _parts(model, C)
            pE_act = _decode(model, bE, zE, gE, ufE, shE)
            pE_don = _decode(model, bE, zE, gE, ufC, shE)                  # extreme ctx + normal DONOR weather
            pE_mean = _decode(model, bE, zE, gE, torch.zeros_like(ufE), shE)
            pC_act = _decode(model, bC, zC, gC, ufC, shC)
            pC_don = _decode(model, bC, zC, gC, ufE, shC)                  # normal ctx + extreme DONOR weather
            pC_mean = _decode(model, bC, zC, gC, torch.zeros_like(ufC), shC)
        mE = _veg_cloud_mask(E, model, pE_act); mC = _veg_cloud_mask(C, model, pC_act)
        r = dict(
            e_key=_key(e_path), c_key=_key(c_path), tile=_tile(e_path), control_id=_key(c_path),
            uf_differs=bool((ufE - ufC).abs().max().item() > 0),
            loss_e_actual=float(_endpoint_masked_mse(pE_act, E, model, mE)[0]),
            loss_e_donor=float(_endpoint_masked_mse(pE_don, E, model, mE)[0]),
            loss_e_mean=float(_endpoint_masked_mse(pE_mean, E, model, mE)[0]),
            loss_c_actual=float(_endpoint_masked_mse(pC_act, C, model, mC)[0]),
            loss_c_donor=float(_endpoint_masked_mse(pC_don, C, model, mC)[0]),
            loss_c_mean=float(_endpoint_masked_mse(pC_mean, C, model, mC)[0]),
            resp_e_donor=float(_per_cube_masked_mean(pE_act - pE_don, mE)[0]),
            resp_e_mean=float(_per_cube_masked_mean(pE_act - pE_mean, mE)[0]),
            resp_c_donor=float(_per_cube_masked_mean(pC_act - pC_don, mC)[0]),
            resp_c_mean=float(_per_cube_masked_mean(pC_act - pC_mean, mC)[0]),
        )
        r["dloss_e_donor"] = r["loss_e_donor"] - r["loss_e_actual"]        # >0 => actual weather predicts better
        r["dloss_e_mean"] = r["loss_e_mean"] - r["loss_e_actual"]
        r["dloss_c_donor"] = r["loss_c_donor"] - r["loss_c_actual"]
        r["dloss_c_mean"] = r["loss_c_mean"] - r["loss_c_actual"]
        rows.append(r)
    return rows


def _summ(vals):
    a = np.asarray(vals, float); a = a[np.isfinite(a)]
    return {"mean": float(a.mean()) if a.size else float("nan"), "n": int(a.size)}


def _q3_statuses(ep_donor_geo, ep_mean_geo, enh_donor_geo, weather_in_base, evidence_role):
    """Frozen Q3 decision (geo-cluster CI is PRIMARY; paired/reused-control are reported but do not decide).
      endpoint_fidelity: actual-vs-donor AND actual-vs-mean geo-cluster CI lower bound > 0
      hotdry_enhancement: interaction dloss_donor geo-cluster CI lower bound > 0
    evidence_role/weather_in_base gate the emitted overall_status so a diagnostic run can NEVER print a
    formal strong Q3 verdict."""
    endpoint = bool(ep_donor_geo and ep_mean_geo)
    enhancement = bool(enh_donor_geo)
    if endpoint and enhancement:
        raw = "Q3_STRONG_RESPONSE_FIDELITY_AND_HOTDRY_ENHANCEMENT"
    elif endpoint:
        raw = "Q3_RESPONSE_FIDELITY_ONLY"
    else:
        raw = "Q3_SENSITIVITY_PARTIAL"
    if weather_in_base:                                   # B4 base reads real weather -> always diagnostic
        overall = "DIAGNOSTIC_ONLY"
    elif evidence_role == "final":                        # formal verdict only for the frozen V2 final run
        overall = raw
    else:                                                 # diagnostic role: never a formal strong verdict
        overall = "DIAGNOSTIC_ONLY"
    return {
        "endpoint_fidelity_status": "PASS" if endpoint else "FAIL",
        "hotdry_enhancement_status": "PASS" if enhancement else "FAIL",
        "primary_criterion": "geo_cluster_bootstrap_ci_low_gt0",
        "raw_status": raw, "evidence_role": evidence_role, "overall_status": overall,
    }


def q3_donor_report(model, rows, n_boot, seed, evidence_role="diagnostic"):
    """Q3 response FIDELITY (spec 3): response magnitude + actual-vs-mean + actual-vs-donor +
    endpoint Delta-loss + hotdry-minus-normal interaction, each with paired / geo-cluster / reused-control
    cluster bootstraps. Fidelity is claimed ONLY when actual endpoint error is significantly below the
    donor AND the mean arms; otherwise it is labelled SENSITIVITY_PARTIAL."""
    tiles = [r["tile"] for r in rows]; controls = [r["control_id"] for r in rows]
    out = {
        "weather_in_base": A.weather_in_base(model), "n_pairs": len(rows),
        "uf_differs_all_pairs": bool(rows) and all(r["uf_differs"] for r in rows),
        "response_magnitude": {
            "extreme_actual_vs_mean": _summ([r["resp_e_mean"] for r in rows]),
            "extreme_actual_vs_donor": _summ([r["resp_e_donor"] for r in rows]),
            "normal_actual_vs_mean": _summ([r["resp_c_mean"] for r in rows]),
            "normal_actual_vs_donor": _summ([r["resp_c_donor"] for r in rows]),
        },
        "endpoint_fidelity": {},
        "interaction_hotdry_minus_normal": {},
    }
    for tag, key in (("extreme_actual_vs_donor", "dloss_e_donor"), ("extreme_actual_vs_mean", "dloss_e_mean")):
        d = [r[key] for r in rows]
        out["endpoint_fidelity"][tag] = {
            "delta_loss_mean": _summ(d)["mean"],
            "paired_bootstrap": _boot(d, n_boot, seed),
            "geo_cluster_bootstrap": _cluster_boot(d, tiles, n_boot, seed),
            "reused_control_cluster_bootstrap": _cluster_boot(d, controls, n_boot, seed),
        }
    for tag, ek, ck in (("resp_donor", "resp_e_donor", "resp_c_donor"),
                        ("resp_mean", "resp_e_mean", "resp_c_mean"),
                        ("dloss_donor", "dloss_e_donor", "dloss_c_donor"),
                        ("dloss_mean", "dloss_e_mean", "dloss_c_mean")):
        inter = [r[ek] - r[ck] for r in rows]
        out["interaction_hotdry_minus_normal"][tag] = {
            "paired_bootstrap": _boot(inter, n_boot, seed),
            "geo_cluster_bootstrap": _cluster_boot(inter, tiles, n_boot, seed),
            "reused_control_cluster_bootstrap": _cluster_boot(inter, controls, n_boot, seed),
        }
    # Frozen Q3 decision: geo-cluster CI is PRIMARY (paired + reused-control are reported but do not decide).
    ep_donor_geo = out["endpoint_fidelity"]["extreme_actual_vs_donor"]["geo_cluster_bootstrap"]["significant_gt0"]
    ep_mean_geo = out["endpoint_fidelity"]["extreme_actual_vs_mean"]["geo_cluster_bootstrap"]["significant_gt0"]
    enh_donor_geo = out["interaction_hotdry_minus_normal"]["dloss_donor"]["geo_cluster_bootstrap"]["significant_gt0"]
    out.update(_q3_statuses(ep_donor_geo, ep_mean_geo, enh_donor_geo, A.weather_in_base(model), evidence_role))
    return out


def _stratum_means(effects, keys):
    sub = [effects[k] for k in keys if k in effects]
    res = {}
    for eff in ("resp_clim", "resp_flip", "contrib_state", "state_move"):
        vals = np.array([s[eff] for s in sub], float)
        res[eff] = {"mean": float(np.nanmean(vals)) if vals.size else float("nan"), "n": int(vals.size)}
    return res


def _build_donor_uf(model, ds, idx_of, pair_paths, dev):
    """{extreme_key: matched-control future-weather tensor}. Control ufs cached (reuse-safe, no re-read)."""
    cache, out = {}, {}
    for e_path, c_path in pair_paths:
        ck = _key(c_path)
        if ck not in cache:
            cache[ck] = A.future_weather(model, _data_of(ds, idx_of, c_path, dev)).detach()
        out[_key(e_path)] = cache[ck]
    return out


def donor_endpoint_accuracy(model, ds, idx_of, targets, donor_uf, dev, out_dir, prov, bs, workers):
    """Aggregate official R2/RMSE on the (unique) extreme stratum under actual / mean / donor future weather.
    Unique extremes only -> no double counting. R2(actual) should exceed R2(donor) and R2(mean) for fidelity."""
    def pf_actual(m, d):
        return A.predict(m, d)

    def pf_mean(m, d):
        return A.predict_with_weather(m, d, torch.zeros_like(A.future_weather(m, d)))

    def pf_donor(m, d):
        keys = [_key(fp) for fp in d["filepath"]]
        duf = torch.cat([donor_uf[k].to(dev) for k in keys], dim=0)
        base, z_t = A.base_and_state(m, d)
        geo, _ = m._geo_weather(d)
        B, H, W = A._bhw(d)
        return base + A.scale(m) * m._direct_residual(z_t, duf, geo, B, H, W)

    res = {}
    for arm, pf in (("actual", pf_actual), ("mean", pf_mean), ("donor", pf_donor)):
        pdir = out_dir / arm / "pred"; sdir = out_dir / arm / "score"
        _export(model, ds, idx_of, targets, pdir, pf, dev, {**prov, "arm": f"q3_{arm}"}, bs=bs, workers=workers)
        s = _score(targets, pdir, sdir, workers)
        res[arm] = {"R2": s.get("R2"), "rmse": s.get("rmse"), "nse": s.get("nse")}
    res["weather_in_base"] = A.weather_in_base(model)
    res["fidelity_note"] = "endpoint fidelity requires R2(actual) > R2(donor) AND R2(actual) > R2(mean)."
    return res


def audit_model(name, model, ds, idx_of, ext_keys, ctl_keys, ext_paths, ctl_paths, pairs, pair_paths, out, args):
    dev = next(model.parameters()).device
    bw = dict(bs=args.batch_size, workers=args.num_data_workers)
    prov = {"model": name, "ckpt_sha": args._ckpt_sha.get(name)}
    all_targets = ext_paths + ctl_paths
    effects = compute_effects(model, ds, idx_of, all_targets, dev, **bw)
    result = {
        "arch": A.arch_of(model), "weather_in_base": A.weather_in_base(model),
        "diagnostic_only": A.weather_in_base(model),
        "n_extreme": len(ext_keys), "n_control": len(ctl_keys),
        "stratum_effect_means": {"hotdry": _stratum_means(effects, ext_keys),
                                 "matched_normal": _stratum_means(effects, ctl_keys)},
        "interaction_hotdry_minus_normal_cohort": interaction(effects, pairs, args.n_boot, args.seed),
    }
    # Q3 matched-DONOR fidelity (spec 1-4): true weather intervention (swap ONLY full24 future weather),
    # per-pair endpoint Delta-loss + interaction with paired / geo-cluster / reused-control bootstraps.
    donor_rows = donor_pairs(model, ds, idx_of, pair_paths, dev)
    result["q3_donor_fidelity"] = q3_donor_report(model, donor_rows, args.n_boot, args.seed,
                                                  evidence_role=args.evidence_role)
    if args.dump_per_cube:
        result["q3_donor_rows"] = donor_rows
    if not args.no_accuracy:
        result["stratum_accuracy"] = {
            "hotdry": stratum_accuracy(model, ds, idx_of, ext_paths, dev, out / name / "hotdry", prov, **bw),
            "matched_normal": stratum_accuracy(model, ds, idx_of, ctl_paths, dev, out / name / "normal", prov, **bw),
        }
        donor_uf = _build_donor_uf(model, ds, idx_of, pair_paths, dev)
        result["q3_aggregate_extreme"] = donor_endpoint_accuracy(
            model, ds, idx_of, ext_paths, donor_uf, dev, out / name / "q3donor", prov, **bw)
    result["per_cube_effects"] = effects if args.dump_per_cube else None
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocol-dir", required=True, help="dir with hotdry_manifest.json + matched_normal_manifest.json")
    ap.add_argument("--dataset-root", required=True)
    ap.add_argument("--data-dir", default=None, help="dir the loader globs (view or ood-t_chopped); default: root/ood-t_chopped")
    ap.add_argument("--ckpt-b4", default=None)
    ap.add_argument("--ckpt-exclusive", default=None)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--num-data-workers", type=int, default=2)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0,
                    help="smoke: run only the first N FROZEN pairs (complete pairs; strata derived from them, "
                         "never truncate-then-intersect the manifests)")
    ap.add_argument("--evidence-role", choices=("diagnostic", "final"), default="diagnostic",
                    help="diagnostic (default): never emit a formal strong Q3 verdict (this B4 + old-exclusive "
                         "audit). final: only for the frozen V2 checkpoint's official Q3 evidence.")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--no-accuracy", action="store_true", help="skip the official-scorer arms (effects/interaction only)")
    ap.add_argument("--dump-per-cube", action="store_true")
    ap.add_argument("--smoke-fresh", action="store_true", help="construct random models if no ckpt (code-path smoke)")
    args = ap.parse_args()

    dev = torch.device(args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu")
    root = resolve_manifest_root(args.dataset_root, protocol=GREENEARTHNET_CHOPPED_PROTOCOL_ID)
    pdir = Path(args.protocol_dir)
    hot_man = pdir / "hotdry_manifest.json"; nrm_man = pdir / "matched_normal_manifest.json"
    hot_abs = load_manifest_files(hot_man, args.dataset_root, expected_split="ood-t_chopped",
                                  expected_protocol=GREENEARTHNET_CHOPPED_PROTOCOL_ID, verify_exists=True)
    nrm_abs = load_manifest_files(nrm_man, args.dataset_root, expected_split="ood-t_chopped",
                                  expected_protocol=GREENEARTHNET_CHOPPED_PROTOCOL_ID, verify_exists=True)
    key2abs = {_key(p): p for p in list(hot_abs) + list(nrm_abs)}

    # FROZEN pairs drive everything. --limit takes the first N COMPLETE pairs (deterministic order); the
    # extreme/control strata are DERIVED from those pairs -- we never truncate the two manifests separately
    # and intersect (which could yield 0..N unstable pairs).
    nrm_audit = json.loads(nrm_man.read_text(encoding="utf-8"))["audit"]
    protocol_n_pairs = int(nrm_audit.get("n_pairs", len(nrm_audit["pairs_extreme_to_control"])))
    pairs_rel = [(e, v["control_path"]) for e, v in sorted(nrm_audit["pairs_extreme_to_control"].items())]
    if args.limit:
        pairs_rel = pairs_rel[:args.limit]
    if not pairs_rel:
        raise SystemExit("REFUSED: empty pairing (0 pairs) -- nothing to audit")
    n_pairs = len(pairs_rel)
    if args.limit:
        assert n_pairs == min(args.limit, protocol_n_pairs), \
            f"limit pairs {n_pairs} != min(limit={args.limit}, protocol={protocol_n_pairs})"
    else:
        assert n_pairs == protocol_n_pairs, f"n_pairs {n_pairs} != frozen protocol n_pairs {protocol_n_pairs}"
    pairs = [(_key(root / e), _key(root / c)) for e, c in pairs_rel]
    ext_keys = list(dict.fromkeys(k for k, _ in pairs))           # unique extremes IN the selected pairs
    ctl_keys = list(dict.fromkeys(k for _, k in pairs))           # unique controls IN the selected pairs
    for k in ext_keys + ctl_keys:
        if k not in key2abs:
            raise SystemExit(f"pair cube {k} not present in the frozen manifests")
    ext_paths = [key2abs[k] for k in ext_keys]
    ctl_paths = [key2abs[k] for k in ctl_keys]

    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
    data_dir = args.data_dir or str(root / "ood-t_chopped")
    ds = GreenEarthNetContextformerDataset(data_dir, dl_cloudmask=True)
    idx_of = {str(Path(p)): i for i, p in enumerate(ds.filepaths)}
    # remap manifest-resolved absolute paths to whatever the dataset globbed (view vs root)
    def _remap(paths):
        out = []
        for p in paths:
            k = _key(p)
            hit = next((fp for fp in ds.filepaths if _key(fp) == k), None)
            if hit is None:
                raise FileNotFoundError(f"cube {k} not found under data-dir {data_dir}")
            out.append(Path(hit))
        return out
    ext_paths, ctl_paths = _remap(ext_paths), _remap(ctl_paths)

    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    args._ckpt_sha = {}
    models = {}
    if args.ckpt_b4 or args.smoke_fresh:
        models["b4"], pb = load_model(args.ckpt_b4, dev, arch_hint="b4"); args._ckpt_sha["b4"] = pb["sha256"]
    if args.ckpt_exclusive or args.smoke_fresh:
        models["exclusive"], pe = load_model(args.ckpt_exclusive, dev, arch_hint="exclusive"); args._ckpt_sha["exclusive"] = pe["sha256"]
    if not models:
        raise SystemExit("provide --ckpt-b4 and/or --ckpt-exclusive (or --smoke-fresh)")

    report = {
        "kind": "extreme_hotdry_state_audit", "protocol_dir": str(pdir.resolve()),
        "protocol_sha": {f: _sha(pdir / f) for f in ("hotdry_manifest.json", "matched_normal_manifest.json",
                                                     "protocol.json", "thresholds.json", "provenance.json")
                         if (pdir / f).is_file()},
        "n_extreme": len(ext_keys), "n_control_unique": len(ctl_keys),
        "n_pairs": n_pairs, "protocol_n_pairs": protocol_n_pairs, "evidence_role": args.evidence_role,
        "limit": args.limit or None,
        "device": str(dev), "batch_size": args.batch_size, "n_boot": args.n_boot,
        "note": "B4 and exclusive numbers are DIAGNOSTIC and are NOT merged into one claim (weather_in_base differs).",
        "models": {},
    }
    key2path = {_key(p): p for p in list(ext_paths) + list(ctl_paths)}
    pair_paths = [(key2path[e], key2path[c]) for e, c in pairs if e in key2path and c in key2path]

    for name, model in models.items():
        report["models"][name] = audit_model(name, model, ds, idx_of, ext_keys, ctl_keys,
                                              ext_paths, ctl_paths, pairs, pair_paths, out, args)
        r = report["models"][name]; q3 = r["q3_donor_fidelity"]
        print(f"[audit] {name}: arch={A.arch_of(model)} weather_in_base={A.weather_in_base(model)} "
              f"n_extreme={len(ext_keys)} n_control_unique={len(ctl_keys)} n_pairs={n_pairs} role={args.evidence_role}")
        ed = q3["endpoint_fidelity"]["extreme_actual_vs_donor"]["geo_cluster_bootstrap"]
        print(f"[audit] {name}: Q3 endpoint(donor) geo-cluster CI=[{ed['ci_low']:.6f},{ed['ci_high']:.6f}] "
              f"sig>0={ed['significant_gt0']} | uf_differs_all={q3['uf_differs_all_pairs']}")
        print(f"[audit] {name}: Q3 endpoint={q3['endpoint_fidelity_status']} enhancement={q3['hotdry_enhancement_status']} "
              f"raw={q3['raw_status']} -> overall={q3['overall_status']}")
    (out / "extreme_state_audit.json").write_text(json.dumps(report, indent=2, allow_nan=True), encoding="utf-8")
    print(f"[audit] wrote {out / 'extreme_state_audit.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
