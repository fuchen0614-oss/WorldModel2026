#!/usr/bin/env python
"""Build the doc-88 future-state target cache for train & val (deliverable B / §6.1.3).

Copies the student's q/projector at training start (from --student-init), freezes them,
and caches the terminal (h=20) future-observation target state z*_{t+20} per cube — with
REAL future EO and future weather ZEROED — keyed by relative cube path, in FP16, with full
provenance (q/projector SHA, data-manifest SHA, field order, h, config SHA) + a sanity
report. Train and val caches are written SEPARATELY. The cache is never read by inference.

  python scripts/build_future_state_cache.py \
    --student-init <phase1_b4_or_exclusive.pt> \
    --train-dir <.../train> --val-dir <.../val_chopped> \
    --out-dir <cache_dir> [--limit N] [--per-gpu-batch 4] [--device cuda|cpu]

Use --limit for the tiny local smoke (2-4 cubes); build the FULL cache on the 8xH200 box.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from models.terrastate_v2 import TerraStateV2, warm_start_terrastate_v2  # noqa: E402
from train.terrastate_future_state_cache import (  # noqa: E402
    FrozenFutureStateEncoder, build_cache, sidecar,
)
from train.terrastate_v2_common import atomic_torch_save, state_sha  # noqa: E402


def _build_one(dataset, encoder, device, *, root, split, student_init_path,
               student_init_sha256, out_path, args):
    blob = build_cache(
        dataset, encoder, device, root=root, split=split,
        student_init_path=student_init_path, student_init_sha256=student_init_sha256,
        per_gpu_batch=args.per_gpu_batch, num_workers=args.num_workers,
        limit=args.limit, sanity_cap=args.sanity_cap, min_coverage=args.min_coverage,
    )
    atomic_torch_save(blob, out_path)
    sc = sidecar(blob)
    Path(str(out_path) + ".json").write_text(json.dumps(sc, indent=2, default=str))
    print(f"[{split}] cached {blob['provenance']['n_cubes']} cubes -> {out_path}")
    print(f"[{split}] coverage={blob['provenance']['coverage']:.4f} "
          f"({blob['provenance']['valid_patches']}/{blob['provenance']['total_patches']} valid patches) "
          f"mask_sha={blob['provenance']['mask_sha256'][:16]}")
    print(f"[{split}] sanity: {json.dumps(blob['sanity'], default=str)}")
    print(f"[{split}] q/projector SHA={blob['provenance']['q_projector_sha256'][:16]} "
          f"data_manifest SHA={blob['provenance']['data_manifest_sha256'][:16]} "
          f"config SHA={blob['provenance']['config_sha256'][:16]} dup={len(blob['dup'])}")
    return blob


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--student-init", required=True,
                    help="Phase-I b4 OR exclusive checkpoint; its q/projector define the frozen target encoder")
    ap.add_argument("--train-dir", required=True)
    ap.add_argument("--val-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--state-dim", type=int, default=256)
    ap.add_argument("--per-gpu-batch", type=int, default=4)
    ap.add_argument("--num-workers", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help=">0 caps #cubes per split (tiny smoke)")
    ap.add_argument("--sanity-cap", type=int, default=20000, help="max patches kept for the sanity report")
    ap.add_argument("--min-coverage", type=float, default=0.0,
                    help="fail-closed: RAISE if valid-patch coverage < this (do NOT relax the mask rule)")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--dl-cloudmask", type=int, default=1)
    args = ap.parse_args()

    # lazy (xarray) import so the module stays light
    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset

    dev = torch.device(args.device)
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)

    hp = contextformer6m_hparams(pvt_pretrained=False)
    init_ck = torch.load(args.student_init, map_location="cpu", weights_only=False)
    student_init_sha = state_sha(init_ck["b4_state_dict"])
    model = TerraStateV2(hp, contract_cfg={"state_dim": args.state_dim, "freeze_b0": True})
    miss, unexp, src = warm_start_terrastate_v2(model, init_ck)
    print(f"student-init warm-start ({src}): missing={len(miss)} unexpected={len(unexp)} "
          f"sha={student_init_sha[:16]}")

    encoder = FrozenFutureStateEncoder(
        model.q, model.projector, model.context_len, model.target_len, model.patch_size,
        lc_min=model.lc_min, lc_max=model.lc_max, deepcopy=True,
    ).to(dev)
    print(f"frozen target encoder q/projector SHA = {encoder.sha256()[:16]} (h={model.target_len})")

    train_ds = GreenEarthNetContextformerDataset(args.train_dir, dl_cloudmask=bool(args.dl_cloudmask))
    _build_one(train_ds, encoder, dev, root=args.train_dir, split="train",
               student_init_path=args.student_init, student_init_sha256=student_init_sha,
               out_path=out / "train_future_state_cache.pt", args=args)

    val_ds = GreenEarthNetContextformerDataset(args.val_dir, dl_cloudmask=bool(args.dl_cloudmask))
    _build_one(val_ds, encoder, dev, root=args.val_dir, split="val",
               student_init_path=args.student_init, student_init_sha256=student_init_sha,
               out_path=out / "val_future_state_cache.pt", args=args)

    print("done: train+val future-state caches written (separate).")


if __name__ == "__main__":
    main()
