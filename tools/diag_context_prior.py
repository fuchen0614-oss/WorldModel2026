#!/usr/bin/env python
"""plan-b-pvt · Phase-II context-prior diagnostic (server, GPU).

The exclusive route's accuracy depends on how good the context-only PRIOR is versus the
full-weather TEACHER (that gap is what T must reconstruct). This tool MEASURES it on a
fixed val subset (never assumes it):
  * exports TEACHER (full-weather B0) NDVI and PRIOR (context-only) NDVI to two dirs;
  * scores BOTH with the official GreenEarthNet scorer -> R2/RMSE/... for each;
  * reports masked (teacher - prior) RMSE + energy (the reconstruction target scale for T).

Usage (GPU):
  CUDA_VISIBLE_DEVICES=2 python tools/diag_context_prior.py \
    --ckpt checkpoints/plan_b_b4a/checkpoint_best.pt --val-dir $DATA/val_chopped \
    --data-manifest artifacts/protocols/b4_eval/val_chopped.manifest.json \
    --dataset-root $DATA --split val --n-cubes 128 --out $OUT/context_prior_diag.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import PVTContextformerQ, contextformer6m_hparams  # noqa: E402
from models.plan_b_b4_exclusive import ObsWorldB4Exclusive, load_exclusive_from_b4  # noqa: E402
from eval.eval_b4_state_contract import _sha  # noqa: E402


def _targets(args, ds):
    if args.data_manifest:
        from data.earthnet_manifest import load_manifest_files
        man = json.loads(Path(args.data_manifest).read_text())
        root = args.dataset_root or args.val_dir
        allt = load_manifest_files(args.data_manifest, root,
                                   expected_split=man.get("role") or man.get("split") or args.split,
                                   expected_protocol=man.get("protocol", "earthnet2021_standard_v1"),
                                   verify_exists=True)
    else:
        allt = [Path(p) for p in ds.filepaths]
    return [Path(t) for t in allt[:args.n_cubes]]


def main() -> int:
    import xarray as xr
    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
    from eval.export_contextformer_predictions import make_ndvi_prediction_dataset
    from eval.eval_greenearthnet_official import score_directory, summarize_score_parquets
    from eval.greenearthnet_protocol import PREDICTION_GRID_FIVE_DAILY_20

    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True); ap.add_argument("--val-dir", required=True)
    ap.add_argument("--data-manifest", default=""); ap.add_argument("--dataset-root", default="")
    ap.add_argument("--split", default="val"); ap.add_argument("--n-cubes", type=int, default=128)
    ap.add_argument("--workers", type=int, default=8); ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    dev = torch.device(args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu")
    ck = torch.load(args.ckpt, map_location="cpu", weights_only=False)
    hp = contextformer6m_hparams(pvt_pretrained=False)
    student = ObsWorldB4Exclusive(hp, contract_cfg=ck.get("contract_cfg", {"state_dim": 256})).to(dev).eval()
    load_exclusive_from_b4(student, ck["b4_state_dict"])
    teacher = PVTContextformerQ(hp)
    teacher.load_state_dict({k[2:]: v for k, v in ck["b4_state_dict"].items() if k.startswith("q.")}, strict=False)
    teacher.to(dev).eval()
    cl, tl = student.context_len, student.target_len

    ds = GreenEarthNetContextformerDataset(args.val_dir, dl_cloudmask=True)
    idx_of = {str(Path(p)): i for i, p in enumerate(ds.filepaths)}
    targets = _targets(args, ds)
    base = Path(args.out).parent if args.out else Path("evaluations/context_prior_diag")
    tdir, pdir = base / "teacher/pred", base / "prior/pred"
    ckpt_sha = _sha(args.ckpt)
    prov = {"ckpt_sha256": ckpt_sha, "n_cubes": len(targets), "kind": "context_prior_diag"}
    prov_path = base / "diag_provenance.json"
    # refuse silent mix/overwrite: a prior run with a DIFFERENT ckpt/subset must not be reused
    if prov_path.is_file() and json.loads(prov_path.read_text()) != prov:
        if not args.overwrite:
            raise SystemExit(f"REFUSED: {base} holds a different diag ({prov_path}); pass --overwrite to wipe.")
        shutil.rmtree(base, ignore_errors=True)
    tdir.mkdir(parents=True, exist_ok=True); pdir.mkdir(parents=True, exist_ok=True)
    prov_path.parent.mkdir(parents=True, exist_ok=True); prov_path.write_text(json.dumps(prov, indent=2))

    rmse_tp, energy = [], []
    for t in targets:
        s = ds[idx_of[str(Path(t))]]
        data = {"dynamic": [s["dynamic"][0].unsqueeze(0).to(dev), s["dynamic"][1].unsqueeze(0).to(dev)],
                "dynamic_mask": [s["dynamic_mask"][0].unsqueeze(0).to(dev)],
                "static": [s["static"][0].unsqueeze(0).to(dev)],
                "landcover": s["landcover"].unsqueeze(0).to(dev), "filepath": s["filepath"]}
        with torch.no_grad():
            prior, _ = student._prior_state(data)                       # context-only forecast
            teach = teacher.encode(data, pred_start=cl, preds_length=tl)[0]   # full-weather
        pri_ndvi = prior[:, :, 0].float().cpu().numpy()[0]
        tea_ndvi = teach[:, :, 0].float().cpu().numpy()[0]
        lc = data["landcover"]; veg = ((lc >= student.lc_min) & (lc <= student.lc_max)).float()
        cloud = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).float()[:, :, 0]     # (1,tl,H,W)
        valid = (veg * cloud).cpu().numpy()[0]                          # (tl,H,W)
        d = (tea_ndvi - pri_ndvi); den = valid.sum() + 1e-8
        rmse_tp.append(float(np.sqrt(((d ** 2) * valid).sum() / den)))
        energy.append(float(((d ** 2) * valid).sum() / den))
        fp = Path(s["filepath"])
        for ndvi, root in ((tea_ndvi, tdir), (pri_ndvi, pdir)):
            op = root / fp.parent.name / fp.name; op.parent.mkdir(parents=True, exist_ok=True)
            with xr.open_dataset(fp) as tgt:
                make_ndvi_prediction_dataset(tgt, np.clip(ndvi, -1, 1)).to_netcdf(op, encoding={"ndvi_pred": {"dtype": "float32"}})

    def score(pred_dir):
        sd = pred_dir.parent / "score"
        score_directory([Path(x) for x in targets], pred_dir, sd, workers=args.workers,
                        prediction_grid=PREDICTION_GRID_FIVE_DAILY_20)
        return summarize_score_parquets(sd)
    m_teacher, m_prior = score(tdir), score(pdir)
    res = {"ckpt_sha256": _sha(args.ckpt), "n_cubes": len(targets),
           "teacher_full_weather_metrics": m_teacher, "context_prior_metrics": m_prior,
           "teacher_minus_prior": {"masked_rmse_mean": float(np.mean(rmse_tp)),
                                   "masked_energy_mean": float(np.mean(energy))},
           "gap_R2": m_teacher.get("R2", float("nan")) - m_prior.get("R2", float("nan")),
           "gap_RMSE": m_prior.get("rmse", float("nan")) - m_teacher.get("rmse", float("nan"))}
    print(json.dumps({k: v for k, v in res.items() if k != "teacher_full_weather_metrics"}, indent=2))
    print(f"[diag] teacher R2={m_teacher.get('R2'):.5f} RMSE={m_teacher.get('rmse'):.5f} | "
          f"prior R2={m_prior.get('R2'):.5f} RMSE={m_prior.get('rmse'):.5f} | "
          f"teacher-prior masked RMSE={np.mean(rmse_tp):.5f}")
    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=2)); print(f"[diag] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
