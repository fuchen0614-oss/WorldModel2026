#!/usr/bin/env python
"""plan-b-pvt · Phase-II teacher intervention-distillation PREFLIGHT (spec 四). NO TRAINING.

Feeds the FROZEN full-weather teacher (the Phase-I B4 q) three future-weather arms with the
history / static / cloud-mask held FIXED, changing ONLY the future 20xV weather:
  * matched           — the cube's own REAL future weather
  * normalized_zero   — future weather = 0 in the z-scored space (per-variable global mean; NOT climatology)
  * donor             — a season+geo+DOY-matched, weather-DIVERGENT donor's future weather (v2 manifest)
Each arm's NDVI is scored with the OFFICIAL GreenEarthNet scorer; we report matched-minus-arm
official metrics + per-cube paired bootstrap CI, and the teacher output response vs weather divergence.

GATE (四): a low-prob intervention-distillation loss may be enabled in Stage-B ONLY if matched has a
directionally-correct + reliable (per-cube paired CI_low>0) advantage over BOTH controls, with the
donor arm treated as the PRIMARY defensible control (real in-distribution weather). If the gate FAILS,
do NOT enable the loss — the teacher is not a reliable weather driver and distilling it would fabricate Q3.

Server only (needs xarray + real data + official scorer). Reuses Phase-I PURE helpers; touches nothing.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import PVTContextformerQ, contextformer6m_hparams  # noqa: E402
from eval.eval_b4_state_contract import (  # noqa: E402  (PURE reuse; Phase-I file unchanged)
    _sha, _bootstrap_ci, _paired_diff, _paired_deltas, _export, _score, _per_cube_r2, _batch_iter, _targets,
    _donor_rel,
)
from eval.b4_donor_schema import validate_donor_manifest_exclusive  # noqa: E402


def _build_teacher(ckpt, dev):
    """SEPARATE frozen full-weather teacher = Phase-I B4 q (identical to trainer.build_teacher)."""
    ck = torch.load(ckpt, map_location="cpu", weights_only=False)
    hp = contextformer6m_hparams(pvt_pretrained=False)
    teacher = PVTContextformerQ(hp)
    q_sd = {k[len("q."):]: v for k, v in ck["b4_state_dict"].items() if k.startswith("q.")}
    teacher.load_state_dict(q_sd, strict=False)
    teacher.to(dev).eval()
    for p in teacher.parameters():
        p.requires_grad_(False)
    return teacher, hp.context_length, hp.target_length


def _arm_data(data, cl, tl, mode, donor_uf=None):
    """Clone data with ONLY the future weather replaced (history/static/mask fixed)."""
    d = dict(data)
    d["dynamic"] = [data["dynamic"][0], data["dynamic"][1].clone()]
    if mode == "zero":
        d["dynamic"][1][:, cl:cl + tl] = 0.0
    elif mode == "donor":
        d["dynamic"][1][:, cl:cl + tl] = donor_uf(data)
    return d                                                    # 'matched' => unchanged


def _teacher_predict(teacher, cl, tl, mode, donor_uf=None):
    def f(_model, data):
        d = _arm_data(data, cl, tl, mode, donor_uf)
        return teacher.encode(d, pred_start=cl, preds_length=tl)[0]   # (B,tl,n_out,H,W) full-weather NDVI
    return f


def main() -> int:
    import numpy as np
    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset

    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher-b4", required=True, help="Phase-I B4 checkpoint (frozen teacher source)")
    ap.add_argument("--val-dir", required=True); ap.add_argument("--dataset-root", default="")
    ap.add_argument("--data-manifest", default=""); ap.add_argument("--donor-manifest", required=True)
    ap.add_argument("--split", default="val"); ap.add_argument("--output-dir", required=True)
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=1); ap.add_argument("--num-data-workers", type=int, default=4)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    dev = torch.device(args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu")
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    root = Path(args.dataset_root or args.val_dir)
    teacher, cl, tl = _build_teacher(args.teacher_b4, dev)
    ds = GreenEarthNetContextformerDataset(args.val_dir, dl_cloudmask=True)
    idx_of = {str(Path(p)): i for i, p in enumerate(ds.filepaths)}
    targets = _targets(args, ds, root)

    donors = json.loads(Path(args.donor_manifest).read_text())
    derrs = validate_donor_manifest_exclusive(donors, targets, root)
    if derrs:
        (out / "teacher_preflight.json").write_text(json.dumps(
            {"status": "INCOMPLETE_FAIL_CLOSED", "donor_errors": derrs[:30]}, indent=2))
        print(f"[preflight] donor manifest invalid ({len(derrs)} errs) — fail closed."); return 2
    pairs = donors.get("pairs", {})

    def donor_uf(data):
        ws = []
        for fp in data["filepath"]:
            dr = _donor_rel(pairs[str(Path(fp).relative_to(root))]); di = idx_of[str(root / dr)]
            ws.append(ds[di]["dynamic"][1][cl:cl + tl])
        return torch.stack(ws).to(dev)

    prov = {"teacher_sha256": _sha(args.teacher_b4), "n_targets": len(targets), "kind": "teacher_intervention_preflight"}

    def _run(arm, predict):
        pdir, sdir = out / f"{arm}/pred", out / f"{arm}/score"
        _export(teacher, ds, idx_of, targets, pdir, predict, dev, {**prov, "arm": arm},
                bs=args.batch_size, workers=args.num_data_workers)
        return _score(targets, pdir, sdir, args.workers), _per_cube_r2(sdir)

    m_match, r_match = _run("matched", _teacher_predict(teacher, cl, tl, "matched"))
    m_zero, r_zero = _run("normalized_zero", _teacher_predict(teacher, cl, tl, "zero"))
    m_don, r_don = _run("donor", _teacher_predict(teacher, cl, tl, "donor", donor_uf))

    def _arm_block(m_arm, r_arm):
        ci = _bootstrap_ci(_paired_deltas(r_match, r_arm))            # matched - arm per cube
        return {"metrics": m_arm,
                "matched_minus_arm_R2_overall": m_match.get("R2", float("nan")) - m_arm.get("R2", float("nan")),
                "matched_minus_arm_percube_bootstrap95": ci,
                "matched_minus_arm_win_tie_loss": _paired_diff(r_match, r_arm),
                "CI_low_gt0": bool(ci.get("significant_gt0"))}

    zero_blk, don_blk = _arm_block(m_zero, r_zero), _arm_block(m_don, r_don)

    # teacher output RESPONSE vs weather divergence (donor arm): per-cube masked |matched - donor| NDVI
    resp, divg = [], []
    for data in _batch_iter(ds, targets, idx_of, dev, args.batch_size, args.num_data_workers):
        with torch.no_grad():
            y_m = teacher.encode(_arm_data(data, cl, tl, "matched"), pred_start=cl, preds_length=tl)[0][:, :, 0:1]
            y_d = teacher.encode(_arm_data(data, cl, tl, "donor", donor_uf), pred_start=cl, preds_length=tl)[0][:, :, 0:1]
            lc = data["landcover"]; veg = ((lc >= 10) & (lc <= 40)).float()
            cloud = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).float()
            valid = (veg.unsqueeze(1) * cloud)
            B = y_m.shape[0]
            for n in range(B):
                vn = valid[n:n + 1]; den = vn.sum() + 1e-8
                resp.append((((y_m[n:n + 1] - y_d[n:n + 1]).abs() * vn).sum() / den).item())
                rel = str(Path(data["filepath"][n]).relative_to(root))
                divg.append(float(pairs[rel]["weather_divergence"]))
    corr = float(np.corrcoef(divg, resp)[0, 1]) if len(resp) > 2 and np.std(divg) > 0 and np.std(resp) > 0 else float("nan")

    gate = bool(zero_blk["CI_low_gt0"] and don_blk["CI_low_gt0"])
    res = {"status": "COMPLETE", "provenance": prov,
           "matched_R2": m_match.get("R2"), "arms": {"normalized_zero": zero_blk, "donor": don_blk},
           "teacher_response_vs_divergence": {"pearson_corr": corr, "mean_output_response": float(np.mean(resp)) if resp else 0.0,
                                              "note": "donor arm; positive corr = teacher output moves with weather divergence."},
           "GATE_pass": gate,
           "gate_rule": "matched beats BOTH controls with per-cube paired CI_low>0 (donor = primary defensible control).",
           "decision": ("ENABLE_INTERVENTION_DISTILLATION_ALLOWED" if gate
                        else "DO_NOT_ENABLE — teacher not a reliable weather driver; distilling it would fabricate Q3."),
           "science_note": "If the ContextFormer-6M teacher barely uses masked future weather, matched-minus-control is "
                           "small and the gate fails HONESTLY — do not lower it to force Q3."}
    (out / "teacher_preflight.json").write_text(json.dumps(res, indent=2, allow_nan=True))
    print(f"[preflight] matched_R2={m_match.get('R2'):.5f} zero_dR2={zero_blk['matched_minus_arm_R2_overall']:+.5f}(CI>0={zero_blk['CI_low_gt0']}) "
          f"donor_dR2={don_blk['matched_minus_arm_R2_overall']:+.5f}(CI>0={don_blk['CI_low_gt0']}) GATE={gate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
