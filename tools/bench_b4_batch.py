#!/usr/bin/env python
"""plan-b-pvt · Q2–Q4 batch benchmark + numerical-equivalence gate (server, GPU).

On a FIXED set of N cubes (default 64, manifest order): run the batched Q4+driver
inner-loops at batch=1 (REFERENCE) then at each candidate batch (default 64,32,16,8),
auto-downgrading on CUDA OOM. For every batch it records peak VRAM, cubes/s and wall
time, and VERIFIES numerical equivalence to batch=1:
  * per-cube driver arrays (state_delta/out_abs/out_signed)   |Δ| <= --tol (1e-5)
  * per-cube Q4 endpoint/gap/state-gap/shuffled + state stats |Δ| <= --tol
  * Q4 PASS/FAIL guard verdicts identical
It then recommends the FASTEST batch that PASSED equivalence.

This does NOT export/score (no official metrics, no NetCDF writes) — it only exercises
the batched forward + per-cube statistics, which is exactly where a cross-cube-mixing
bug would show up. FP32 only; no autocast. Checkpoint asserted byte-unchanged.

Usage (GPU, real data):
  CUDA_VISIBLE_DEVICES=6 python tools/bench_b4_batch.py \
    --ckpt checkpoints/plan_b_b4a/checkpoint_best.pt \
    --val-dir $DATA/val_chopped \
    --data-manifest artifacts/protocols/b4_eval/val_chopped.manifest.json \
    --dataset-root $DATA --split val --n-cubes 64 --batches 64 32 16 8
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.export_b4_predictions import load_b4  # noqa: E402
from eval.eval_b4_state_contract import _sha, _driver_deltas, _q4, _batch_iter  # noqa: E402


def _flat_q4(q):
    v = []
    for sp in ("train", "heldout"):
        for _, p in q[sp].items():
            v += [p["diagnostic_endpoint_dir_mse_modelspace"], p["diagnostic_endpoint_cmp_mse_modelspace"],
                  p["diagnostic_path_gap_mse_modelspace"]["mean"], p["diagnostic_state_path_gap"]["mean"],
                  p["control_path_gap_shuffled_weather"]]
    for _, s in q["state"].items():
        v += [s["std"], s["eff_rank"], s["movement"]]
    return v


def _verdicts(q):
    return [q[sp][k]["guard_verdict"] for sp in ("train", "heldout") for k in sorted(q[sp])]


def _run_once(model, ds, idx_of, targets, dev, bs, workers, guard):
    """Return (preds, driver_percube_dict, q4_flat, q4_verdicts, seconds, peak_gib).
    Times the EXPORT-path forecast (predictions) + driver + Q4 — representative of the
    real contract GPU cost, and yields per-cube predictions for max-abs equivalence."""
    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev); torch.cuda.synchronize(dev)
    t0 = time.time()
    preds = []
    for data in _batch_iter(ds, targets, idx_of, dev, bs, workers):
        with torch.no_grad():
            preds.append(model.forecast(data)[:, :, 0].float().cpu())    # (B, target_len, H, W)
    preds = torch.cat(preds, 0)
    dd = _driver_deltas(model, ds, idx_of, targets, dev, "mean", bs=bs, workers=workers)
    q4 = _q4(model, ds, idx_of, targets, dev, guard, "bench", official_overall_R2=0.0, bs=bs, workers=workers)
    if dev.type == "cuda":
        torch.cuda.synchronize(dev)
    secs = time.time() - t0
    peak = (torch.cuda.max_memory_allocated(dev) / 1024**3) if dev.type == "cuda" else 0.0
    return preds, dd["per_cube"], _flat_q4(q4), _verdicts(q4), secs, peak


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--val-dir", required=True)
    ap.add_argument("--data-manifest", default=""); ap.add_argument("--dataset-root", default="")
    ap.add_argument("--split", default="val")
    ap.add_argument("--n-cubes", type=int, default=64)
    ap.add_argument("--batches", type=int, nargs="+", default=[64, 32, 16, 8])
    ap.add_argument("--num-data-workers", type=int, default=4)
    ap.add_argument("--guard", type=float, default=0.05)
    ap.add_argument("--tol", type=float, default=1e-5)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    dev = torch.device(args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu")
    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
    ckpt_sha0 = _sha(args.ckpt)
    model = load_b4(args.ckpt, str(dev))
    ds = GreenEarthNetContextformerDataset(args.val_dir, dl_cloudmask=True)
    idx_of = {str(Path(p)): i for i, p in enumerate(ds.filepaths)}
    # fixed N cubes in manifest order (formal) or first-N (fallback)
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
    targets = [Path(t) for t in allt[:args.n_cubes]]
    print(f"[bench] cubes={len(targets)} device={dev} tol={args.tol} guard={args.guard}")

    # REFERENCE: batch=1
    ref_p, ref_dd, ref_q4, ref_vd, s1, p1 = _run_once(model, ds, idx_of, targets, dev, 1, args.num_data_workers, args.guard)
    cps1 = len(targets) / s1
    print(f"[bench] bs=  1  time={s1:6.1f}s  cubes/s={cps1:5.2f}  peakVRAM={p1:5.2f}GiB  (REFERENCE)")

    rows = [{"batch": 1, "time_s": s1, "cubes_s": cps1, "peak_gib": p1, "equiv": True, "speedup": 1.0}]
    for bs in args.batches:
        if bs <= 1:
            continue
        try:
            p, dd, q4, vd, s, pk = _run_once(model, ds, idx_of, targets, dev, bs, args.num_data_workers, args.guard)
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                if dev.type == "cuda":
                    torch.cuda.empty_cache()
                print(f"[bench] bs={bs:3d}  OOM -> auto-downgrade (skip)")
                rows.append({"batch": bs, "oom": True, "equiv": False}); continue
            raise
        # equivalence vs batch=1: predictions + per-cube driver + Q4 stats + guard verdicts
        pred_max = (p - ref_p).abs().max().item()
        drv_max = max((abs(a - b) for k in ("state_delta", "out_abs", "out_signed")
                       for a, b in zip(ref_dd[k], dd[k])), default=0.0)
        q4_max = max((abs(a - b) for a, b in zip(ref_q4, q4)), default=0.0)
        vd_ok = (vd == ref_vd)
        equiv = (pred_max <= args.tol and drv_max <= args.tol and q4_max <= args.tol and vd_ok)
        cps = len(targets) / s
        print(f"[bench] bs={bs:3d}  time={s:6.1f}s  cubes/s={cps:5.2f}  peakVRAM={pk:5.2f}GiB  "
              f"speedup={cps/cps1:4.2f}x  predΔ={pred_max:.2e} drvΔ={drv_max:.2e} q4Δ={q4_max:.2e} "
              f"verdict_ok={vd_ok}  EQUIV={'PASS' if equiv else 'FAIL'}")
        rows.append({"batch": bs, "time_s": s, "cubes_s": cps, "peak_gib": pk,
                     "pred_max_abs": pred_max, "drv_max_abs": drv_max, "q4_max_abs": q4_max,
                     "verdicts_match": vd_ok, "equiv": equiv, "speedup": cps / cps1})

    assert _sha(args.ckpt) == ckpt_sha0, "checkpoint changed during benchmark!"
    passed = [r for r in rows if r.get("equiv") and r.get("batch", 1) > 1]
    rec = max(passed, key=lambda r: r["cubes_s"]) if passed else {"batch": 1, "cubes_s": cps1, "speedup": 1.0}
    print("\n[bench] ==== RECOMMENDATION ====")
    print(f"[bench] fastest EQUIVALENCE-PASS batch = {rec['batch']}  "
          f"(cubes/s={rec['cubes_s']:.2f}, speedup={rec.get('speedup',1.0):.2f}x vs bs=1)")
    if not passed:
        print("[bench] WARNING: no batch>1 passed equivalence — investigate cross-cube aggregation before formal run.")
    result = {"ckpt_sha256": ckpt_sha0, "n_cubes": len(targets), "tol": args.tol,
              "rows": rows, "recommended_batch": rec["batch"], "any_equiv_pass": bool(passed)}
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2))
        print(f"[bench] wrote {args.out}")
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
