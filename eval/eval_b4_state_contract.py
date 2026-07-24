#!/usr/bin/env python
"""plan-b-pvt · B4 real-data STATE-CONTRACT evaluator (priority 2, formal-hardened).

Same checkpoint, same samples, same OFFICIAL evaluator. In-memory interventions only;
the checkpoint file is asserted byte-unchanged. FORMAL runs need a FROZEN data manifest
(+dataset-root+split); --limit is a NON-formal smoke. Any formal arm that cannot be run
(missing/invalid donor manifest, unset endpoint guard) is reported INCOMPLETE and the
process exits non-zero — it never prints "contract complete".

  Q2 load-bearing : full vs gate=0 vs T→identity → official metrics + per-cube paired diff.
  Q3 driver       : matched / normalized-mean / season-geo DONOR. B0 is held FIXED (real
                    weather); ONLY the TerraState transition sees the intervened future
                    weather. Reports transitioned-state Δ, endpoint-output Δ, AND the
                    official prediction-metric diff. No donor manifest ⇒ FAIL CLOSED.
  Q4 composition  : direct/composed endpoint DIAGNOSTIC error (model normalized-NDVI
                    space, training cloud+veg mask — NOT the official caliber; the
                    official overall R2 is carried in Q2) + path gap; guard verdict
                    pass/fail ONLY under a PRE-REGISTERED, hashed --guard-config, else
                    UNSET_FAIL_CLOSED (gaps are NOT positive evidence).

Reuses eval/export_contextformer_predictions.make_ndvi_prediction_dataset and the
official eval/eval_greenearthnet_official scorer + data/earthnet_manifest.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import shutil
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.export_b4_predictions import load_b4  # noqa: E402


def _sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


GUARD_CONFIG_REQUIRED = ("threshold", "caliber", "rationale", "frozen_utc")


def _load_guard_config(path):
    """Read a PRE-REGISTERED, hashed guard config (Fix 6). The threshold must be
    frozen in a file (not chosen post-hoc on the CLI). Returns (threshold, sha, cfg)
    or raises SystemExit. The file must declare threshold + caliber + rationale +
    frozen_utc so the guarded quantity and its pre-registration are auditable."""
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"REFUSED: --guard-config {p} does not exist (guard stays UNSET_FAIL_CLOSED).")
    cfg = json.loads(p.read_text())
    missing = [k for k in GUARD_CONFIG_REQUIRED if k not in cfg]
    if missing:
        raise SystemExit(f"REFUSED: guard-config missing keys {missing}; will not invent a threshold.")
    thr = cfg["threshold"]
    if not isinstance(thr, (int, float)) or isinstance(thr, bool) or thr != thr:
        raise SystemExit(f"REFUSED: guard-config threshold must be a finite number, got {thr!r}.")
    return float(thr), _sha(p), cfg


def _evaluator_commit() -> str:
    import subprocess
    from eval.greenearthnet_protocol import OFFICIAL_EVALUATOR_COMMIT
    git = "nogit"
    try:
        git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip() or "nogit"
    except Exception:
        pass
    return f"repo:{git}+official:{OFFICIAL_EVALUATOR_COMMIT}"


@contextlib.contextmanager
def _gate_zero(model):
    g = model.gate.data.clone(); model.gate.data.zero_()
    try:
        yield
    finally:
        model.gate.data.copy_(g)


@contextlib.contextmanager
def _t_identity(model):
    w = model.transition.net[-1].weight.data.clone(); b = model.transition.net[-1].bias.data.clone()
    model.transition.net[-1].weight.data.zero_(); model.transition.net[-1].bias.data.zero_()
    try:
        yield
    finally:
        model.transition.net[-1].weight.data.copy_(w); model.transition.net[-1].bias.data.copy_(b)


def _paired_diff(a: dict, b: dict):
    import statistics
    keys = sorted(set(a) & set(b))
    d = [a[k] - b[k] for k in keys]
    if not d:
        return {"n": 0}
    wins = sum(x > 0 for x in d); losses = sum(x < 0 for x in d)
    return {"n": len(d), "mean_delta_R2": statistics.fmean(d), "median_delta_R2": statistics.median(d),
            "win": wins, "tie": len(d) - wins - losses, "loss": losses}


def _predict_donor(model, data, donor_uf):
    """B0 from the REAL data (unchanged); ONLY the transition sees donor future weather."""
    preds_b0, z_t = model._b0_and_state(data)
    hr = data["dynamic"][0]; B, H, W = hr.shape[0], hr.shape[-2], hr.shape[-1]
    geo, _ = model._geo_weather(data)
    resid = model._direct_residual(z_t, donor_uf, geo, B, H, W)
    return preds_b0 + model.gate * resid


def validate_donor_manifest(manifest, targets, root):
    """Thin re-export of the pure season+geo validator (see eval/b4_donor_schema.py)."""
    from eval.b4_donor_schema import validate_donor_manifest as _v
    return _v(manifest, targets, Path(root))


def _donor_rel(entry):
    from eval.b4_donor_schema import donor_rel
    return donor_rel(entry)


def _targets(args, ds, root: Path):
    if args.limit:                                              # NON-formal smoke
        return [Path(p) for p in ds.filepaths[:args.limit]]
    from data.earthnet_manifest import load_manifest_files      # FORMAL: frozen manifest, no discovery
    return [Path(p) for p in load_manifest_files(args.data_manifest, str(root),
                                                 expected_split=args.split, verify_exists=True)]


def _data(ds, idx, dev):
    s = ds[idx]
    return {"dynamic": [s["dynamic"][0].unsqueeze(0).to(dev), s["dynamic"][1].unsqueeze(0).to(dev)],
            "dynamic_mask": [s["dynamic_mask"][0].unsqueeze(0).to(dev)],
            "static": [s["static"][0].unsqueeze(0).to(dev)],
            "landcover": s["landcover"].unsqueeze(0).to(dev), "filepath": s["filepath"]}


def _export(model, ds, idx_of, targets, out_dir: Path, predict, dev, tag: dict):
    """Write NDVI NetCDFs for the EXACT target set; skip ONLY if the FULL provenance
    tag matches (Fix 8/9: a different arm / ckpt / data / evaluator never reuses a
    stale prediction). Returns 'reused' or 'written'."""
    import xarray as xr
    from eval.export_contextformer_predictions import make_ndvi_prediction_dataset
    prov = out_dir / "provenance.json"
    if prov.is_file() and json.loads(prov.read_text()) == tag:
        return "reused"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for t in targets:
        data = _data(ds, idx_of[str(Path(t))], dev)
        with torch.no_grad():
            ndvi = predict(model, data)[:, :, 0].float().cpu().numpy()
        fp = Path(data["filepath"]); op = out_dir / fp.parent.name / fp.name
        op.parent.mkdir(parents=True, exist_ok=True)
        with xr.open_dataset(fp) as tgt:
            make_ndvi_prediction_dataset(tgt, ndvi[0]).to_netcdf(op, encoding={"ndvi_pred": {"dtype": "float32"}})
    prov.write_text(json.dumps(tag, sort_keys=True))
    return "written"


def _score(targets, pred_dir: Path, score_dir: Path, workers):
    from eval.eval_greenearthnet_official import score_directory, summarize_score_parquets
    from eval.greenearthnet_protocol import PREDICTION_GRID_FIVE_DAILY_20
    score_directory([Path(t) for t in targets], pred_dir, score_dir, workers=workers,
                    prediction_grid=PREDICTION_GRID_FIVE_DAILY_20)
    return summarize_score_parquets(score_dir)


def _per_cube_r2(score_dir: Path, lc_balanced: bool = True):
    """Per-cube R2 for paired win/tie/loss.

    lc_balanced=True (default, Fix 5): within each (season,id) average r² per
    landcover then over landcovers — the official LC-balanced caliber at cube
    granularity. lc_balanced=False is a simple pixel-r² mean (diagnostic only).
    The paper HEADLINE remains the official overall LC-balanced R2 in the arm
    metrics; this per-cube series only colours the paired comparison.
    """
    import pandas as pd
    fr = [pd.read_parquet(p) for p in sorted(Path(score_dir).glob("scores_en21x_*.parquet"))]
    if not fr:
        return {}
    df = pd.concat(fr, ignore_index=True).assign(R2=lambda x: x.r ** 2)
    if lc_balanced:
        per_lc = df.groupby(["season", "id", "landcover"])["R2"].mean()
        cube = per_lc.groupby(level=["season", "id"]).mean()
        return {f"{s}/{i}": float(v) for (s, i), v in cube.items()}
    return {f"{s}/{i}": float(v) for (s, i), v in df.groupby(["season", "id"])["R2"].mean().items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--val-dir", required=True)
    ap.add_argument("--data-manifest", default=""); ap.add_argument("--dataset-root", default="")
    ap.add_argument("--split", default="val")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--donor-manifest", default="")
    ap.add_argument("--guard-config", default="",
                    help="PRE-REGISTERED, hashed guard config JSON {threshold,caliber,rationale,frozen_utc}. "
                         "Formal runs MUST use this so the threshold is frozen, not picked post-hoc.")
    ap.add_argument("--guard-endpoint-max", type=float, default=None,
                    help="SMOKE-ONLY inline threshold; ignored in FORMAL mode (use --guard-config).")
    ap.add_argument("--limit", type=int, default=0, help="NON-formal smoke on first N cubes")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    formal = not args.limit
    if formal and not (args.data_manifest and args.dataset_root):
        raise SystemExit("REFUSED: FORMAL contract eval needs --data-manifest + --dataset-root.")
    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
    dev = args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu"
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    root = Path(args.dataset_root or args.val_dir)
    ckpt_sha_before = _sha(args.ckpt)
    model = load_b4(args.ckpt, dev)
    ds = GreenEarthNetContextformerDataset(args.val_dir, dl_cloudmask=True)
    idx_of = {str(Path(p)): i for i, p in enumerate(ds.filepaths)}
    targets = _targets(args, ds, root)
    data_hash = _sha(args.data_manifest) if args.data_manifest else f"SMOKE_LIMIT_{args.limit}"
    donor_hash = _sha(args.donor_manifest) if args.donor_manifest else None
    evaluator_commit = _evaluator_commit()

    # ---- resolve the FROZEN guard (Fix 6) -----------------------------------
    guard_max, guard_sha, guard_cfg = None, None, None
    if args.guard_config:
        guard_max, guard_sha, guard_cfg = _load_guard_config(args.guard_config)
    elif args.guard_endpoint_max is not None and not formal:
        guard_max, guard_sha = args.guard_endpoint_max, "SMOKE_INLINE_NOT_FROZEN"

    # ---- FULL provenance recorded on every output (Fix 7) -------------------
    prov_base = {"checkpoint_sha256": ckpt_sha_before, "data_manifest_sha256": data_hash,
                 "donor_manifest_sha256": donor_hash, "guard_config_sha256": guard_sha,
                 "evaluator_commit": evaluator_commit, "split": args.split, "formal": formal,
                 "n_targets": len(targets)}
    R = {"checkpoint": str(Path(args.ckpt).resolve()), "provenance": prov_base,
         "command": " ".join(sys.argv), "guard_config": guard_cfg,
         "status": "COMPLETE", "incomplete_reasons": []}

    # ---- Q2 load-bearing -----------------------------------------------------
    def _run(arm, ctx, predict):
        pdir, sdir = out / f"{arm}/pred", out / f"{arm}/score"
        tag = {**prov_base, "arm": arm}
        with ctx:
            status = _export(model, ds, idx_of, targets, pdir, predict, dev, tag)
        if status == "written" and sdir.exists():   # Fix 8: never summarize a prior provenance's parquet
            shutil.rmtree(sdir)
        return _score(targets, pdir, sdir, args.workers), _per_cube_r2(sdir)
    m_full, r_full = _run("q2_full", contextlib.nullcontext(), lambda m, d: m.forecast(d))
    m_g0, r_g0 = _run("q2_gate0", _gate_zero(model), lambda m, d: m.forecast(d))
    m_ti, r_ti = _run("q2_Tid", _t_identity(model), lambda m, d: m.forecast(d))
    _pc_caliber = "per-cube LC-balanced R2 (official aggregation at cube granularity); win/tie/loss only"
    R["Q2_load_bearing"] = {
        "caliber_note": "full/gate0/T_identity metrics are the OFFICIAL LC-balanced GreenEarthNet aggregation.",
        "full": m_full, "gate0": m_g0, "T_identity": m_ti,
        "official_overall_R2_full_minus_gate0": m_full.get("R2", float("nan")) - m_g0.get("R2", float("nan")),
        "official_overall_R2_full_minus_Tidentity": m_full.get("R2", float("nan")) - m_ti.get("R2", float("nan")),
        "paired_percube_full_minus_gate0": {**_paired_diff(r_full, r_g0), "caliber": _pc_caliber},
        "paired_percube_full_minus_Tidentity": {**_paired_diff(r_full, r_ti), "caliber": _pc_caliber}}

    # ---- Q3 driver (B0 FIXED; state Δ + output Δ + metric diff) ---------------
    # matched == q2_full (SAME arm, SAME provenance, SAME process) -> safe reuse (Fix 9).
    m_mean, _ = _run("q3_mean", contextlib.nullcontext(), lambda m, d: m.forecast_weather(d, "mean")[1])
    q3 = {"matched": m_full, "matched_reuse_note": "identical to q2_full arm under the same full provenance",
          "mean": {"metrics": m_mean,
                   "metric_diff_vs_matched_R2": (m_mean.get("R2", float("nan")) - m_full.get("R2", float("nan")))}}
    q3["mean"].update(_driver_deltas(model, ds, idx_of, targets, dev, "mean"))
    if args.donor_manifest:
        donors = json.loads(Path(args.donor_manifest).read_text())
        errs = validate_donor_manifest(donors, targets, root)
        if errs:
            R["status"] = "INCOMPLETE_FAIL_CLOSED"; R["incomplete_reasons"].append({"donor_manifest": errs[:20]})
            q3["donor"] = {"status": "FAIL_CLOSED", "errors": errs[:20]}
        else:
            pairs = donors.get("pairs", {})
            def donor_uf(d):
                donor_rel = _donor_rel(pairs[str(Path(d["filepath"]).relative_to(root))])
                di = idx_of[str(root / donor_rel)]
                return ds[di]["dynamic"][1].unsqueeze(0).to(dev)[:, model.context_len:model.context_len + model.target_len]
            m_don, _ = _run("q3_donor", contextlib.nullcontext(),
                            lambda m, d: _predict_donor(m, d, donor_uf(d)))
            q3["donor"] = {"metrics": m_don, "donor_schema": donors.get("donor_schema"),
                           "metric_diff_vs_matched_R2": (m_don.get("R2", float("nan")) - m_full.get("R2", float("nan")))}
            q3["donor"].update(_driver_deltas(model, ds, idx_of, targets, dev, "donor", donor_uf))
    else:
        q3["donor"] = {"status": "FAIL_CLOSED", "reason": "no --donor-manifest; batch-roll is NOT a valid donor"}
        if formal:
            R["status"] = "INCOMPLETE_FAIL_CLOSED"; R["incomplete_reasons"].append("Q3 donor missing")
    R["Q3_driver"] = q3

    # ---- Q4 composition + guard ----------------------------------------------
    R["Q4_composition"] = _q4(model, ds, idx_of, targets, dev, guard_max, guard_sha,
                              official_overall_R2=m_full.get("R2"))
    if guard_max is None and formal:
        R["status"] = "INCOMPLETE_FAIL_CLOSED"; R["incomplete_reasons"].append("Q4 endpoint guard UNSET (no frozen --guard-config)")

    R["checkpoint_unchanged"] = (_sha(args.ckpt) == ckpt_sha_before)
    assert R["checkpoint_unchanged"], "checkpoint changed during eval!"
    (out / "state_contract.json").write_text(json.dumps(R, indent=2, allow_nan=True))
    print(f"[contract] status={R['status']}  ckpt_unchanged={R['checkpoint_unchanged']}  out={out}")
    if R["status"] != "COMPLETE":
        print(f"[contract] INCOMPLETE — reasons: {R['incomplete_reasons']}  (NOT 'contract complete')")
        return 2
    print("[contract] complete")
    return 0


def _driver_deltas(model, ds, idx_of, targets, dev, mode, donor_uf=None):
    """Per-cube transitioned-state Δ and endpoint-output Δ (mode vs matched), at h=target_len."""
    import numpy as np
    sd, od = [], []
    for t in targets:
        d = _data(ds, idx_of[str(Path(t))], dev)
        with torch.no_grad():
            pb0, z_t = model._b0_and_state(d); geo, uf_m = model._geo_weather(d)
            B, H, W = d["dynamic"][0].shape[0], d["dynamic"][0].shape[-2], d["dynamic"][0].shape[-1]
            uf_x = torch.zeros_like(uf_m) if mode == "mean" else donor_uf(d)
            zh_m = model.direct_state(z_t, uf_m, geo, model.target_len)
            zh_x = model.direct_state(z_t, uf_x, geo, model.target_len)
            y_m = pb0 + model.gate * model._direct_residual(z_t, uf_m, geo, B, H, W)
            y_x = pb0 + model.gate * model._direct_residual(z_t, uf_x, geo, B, H, W)
            sd.append((zh_x - zh_m).abs().mean().item()); od.append((y_x - y_m).abs().max().item())
    return {"mean_transitioned_state_delta": float(np.mean(sd)),
            "mean_endpoint_output_delta": float(np.mean(od))}


_Q4_CALIBER = ("DIAGNOSTIC, model normalized-NDVI space on the TRAINING cloud "
               "(dl_cloudmask<1) + vegetation-landcover mask, simple masked MSE at the "
               "model step index. This is NOT the official GreenEarthNet caliber "
               "(official = s2_B8A/B04 NDVI, SCL clear-mask, 20×5-daily grid, "
               "land-cover-balanced aggregation). Official overall R2 is carried "
               "separately in Q2 full / q3 arms. The composition guard therefore "
               "bounds a DIAGNOSTIC non-collapse quantity, not an official metric.")


def _q4(model, ds, idx_of, targets, dev, guard_max, guard_sha=None, official_overall_R2=None):
    import numpy as np
    cl, tl = model.context_len, model.target_len
    parts = {"train": model.partitions, "heldout": model.heldout_partitions}
    acc = {"train": {}, "heldout": {}}
    state_h = {h: {"std": [], "eff_rank": [], "movement": []} for h in (1, 5, 10, 20)}
    for t in targets:
        d = _data(ds, idx_of[str(Path(t))], dev)
        with torch.no_grad():
            pb0, z_t = model._b0_and_state(d); geo, uf = model._geo_weather(d)
            B, H, W = d["dynamic"][0].shape[0], d["dynamic"][0].shape[-2], d["dynamic"][0].shape[-1]
            lc = d["landcover"]; lcm = ((lc >= model.lc_min) & (lc <= model.lc_max)).float()
            targ = d["dynamic"][0][:, cl:cl + tl, 0:1]; cloud = (d["dynamic_mask"][0][:, cl:cl + tl] < 1.0).float()
            for h in (1, 5, 10, 20):
                zh = model.direct_state(z_t, uf, geo, h)
                state_h[h]["std"].append(model.state_std(zh)); state_h[h]["eff_rank"].append(model.effective_rank(zh))
                state_h[h]["movement"].append((zh - z_t).abs().mean().item())
            for split, plist in parts.items():
                for (h1, h2) in plist:
                    h = h1 + h2
                    y_dir = pb0[:, h - 1] + model.gate * model._decode_state(model.direct_state(z_t, uf, geo, h), B, H, W)
                    y_cmp = model.composed_prediction(pb0, z_t, uf, geo, h1, h2, B, H, W)
                    th, ch = targ[:, h - 1], cloud[:, h - 1]
                    key = f"{h1}+{h2}"
                    acc[split].setdefault(key, {"dir": [], "cmp": [], "gap": []})
                    acc[split][key]["dir"].append(model._masked_mse1(y_dir, th, ch, lcm).item())
                    acc[split][key]["cmp"].append(model._masked_mse1(y_cmp, th, ch, lcm).item())
                    acc[split][key]["gap"].append(model._masked_mse1(y_cmp, y_dir, ch, lcm).item())
    out = {"caliber": _Q4_CALIBER,
           "official_overall_R2_reference": official_overall_R2,
           "guard_endpoint_max": guard_max, "guard_config_sha256": guard_sha,
           "guard_status": "UNSET_FAIL_CLOSED" if guard_max is None else "SET_FROZEN",
           "state": {f"h={h}": {"std": float(np.mean(v["std"])), "eff_rank": float(np.mean(v["eff_rank"])),
                                "movement": float(np.mean(v["movement"]))} for h, v in state_h.items()}}
    for split in ("train", "heldout"):
        out[split] = {}
        for p, v in acc[split].items():
            ed, ec, gp = float(np.mean(v["dir"])), float(np.mean(v["cmp"])), float(np.mean(v["gap"]))
            if guard_max is None:
                verdict = "UNSET_FAIL_CLOSED"; gap_report = "withheld (guard unset; gap is NOT positive evidence)"
            else:
                passed = ed <= guard_max and ec <= guard_max
                verdict = "PASS" if passed else "FAIL"; gap_report = gp if passed else "withheld (endpoints not qualified)"
            out[split][p] = {"diagnostic_endpoint_dir_mse_modelspace": ed,
                             "diagnostic_endpoint_cmp_mse_modelspace": ec,
                             "guard_verdict": verdict,
                             "diagnostic_path_gap_mse_modelspace": gap_report}
    return out


if __name__ == "__main__":
    raise SystemExit(main())
