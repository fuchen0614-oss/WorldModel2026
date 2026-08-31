#!/usr/bin/env python3
"""Export NDVI predictions from the official GreenEarthNet baselines (ConvLSTM,
PredRNN, SimVP) on our frozen chopped tracks, in the same layout the official
scorer expects.

Why this exists: the published weights ship as PyTorch-Lightning checkpoints from
earthnet-models-pytorch v0.1.0, which pins torch 1.13.1 and will not run on this
box. The nn.Modules themselves are plain torch and import fine on torch 2.x once
`segmentation-models-pytorch` is present, so we point sys.path at the upstream
checkout, build the module from the official YAML, and strip the Lightning
`model.` prefix off the state dict. No model code is reimplemented.

Mirrors eval/export_contextformer_predictions.py -- same dataset, same collate,
same output cubes -- so both paths feed the official scorer identically.
"""
import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
import xarray as xr
import yaml
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset  # noqa: E402
from eval.export_contextformer_predictions import collate, make_ndvi_prediction_dataset  # noqa: E402
from eval.greenearthnet_protocol import PREDICTION_VARIABLE  # noqa: E402

try:
    from tqdm import tqdm
except ImportError:                                            # pragma: no cover
    def tqdm(it, *a, **k):
        return it

ARCH = {                       # official `Architecture:` value -> (module, class)
    "convlstm_ae": ("convlstm_ae", "ConvLSTMAE"),
    "predrnn": ("predrnn", "PredRNN"),
    "simvp": ("simvp", "SimVP"),
}


def build_model(cfg_path: str, ckpt_path: str, emp_root: str):
    """Instantiate the upstream nn.Module from its official YAML and weights."""
    sys.path.insert(0, emp_root)
    cfg = yaml.safe_load(Path(cfg_path).read_text())
    arch = cfg["Architecture"]
    if arch not in ARCH:
        raise SystemExit(f"unsupported Architecture {arch!r}; known: {list(ARCH)}")
    mod_name, cls_name = ARCH[arch]
    mod = __import__(f"earthnet_models_pytorch.model.{mod_name}", fromlist=["x"])
    cls = getattr(mod, cls_name)

    # The module reads plain attributes off an argparse-style namespace. Task-level
    # fields (context/target length, land-cover bounds) live in the Task section.
    hp = dict(cfg.get("Model", {}))
    task = cfg.get("Task", {}) or {}
    for k, default in (("context_length", 10), ("target_length", 20),
                       ("min_lc", 10), ("max_lc", 40), ("setting", "en21x"),
                       ("lc_min", 10), ("lc_max", 40), ("method", ""),
                       ("spatial_shuffle", False), ("use_weather", True)):
        hp.setdefault(k, task.get(k, default))
    model = cls(SimpleNamespace(**hp))

    ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    sd = {k[len("model."):]: v for k, v in ck["state_dict"].items() if k.startswith("model.")}
    missing, unexpected = model.load_state_dict(sd, strict=True)
    if missing or unexpected:
        raise SystemExit(f"{ckpt_path}: load NOT clean "
                         f"missing={list(missing)} unexpected={list(unexpected)}")
    n = sum(p.numel() for p in model.parameters())
    print(f"[model] {arch} from {Path(ckpt_path).name}  params={n/1e6:.2f}M  strict=True OK")
    return model


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track-dir", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--config", required=True, help="official model_configs/*/seed=42.yaml")
    ap.add_argument("--emp-root", required=True, help="earthnet-models-pytorch checkout")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    dev = args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu"
    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    dataset = GreenEarthNetContextformerDataset(args.track_dir, dl_cloudmask=True)
    n_total = len(dataset)
    if args.limit and args.limit < n_total:
        dataset.filepaths = dataset.filepaths[: args.limit]
    print(f"[data] track={args.track_dir}  cubes={len(dataset)} (of {n_total})")

    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False,
                        num_workers=args.num_workers, collate_fn=collate,
                        pin_memory=(dev == "cuda"))
    model = build_model(args.config, args.ckpt, args.emp_root).to(dev).eval()

    written = skipped = 0
    with torch.no_grad():
        for batch in tqdm(loader, desc="baseline export"):
            data = {
                "dynamic": [batch["dynamic"][0].to(dev), batch["dynamic"][1].to(dev)],
                "dynamic_mask": [batch["dynamic_mask"][0].to(dev)],
                "static": [batch["static"][0].to(dev)],
                # ConvLSTM anneals teacher forcing by global_step; a large value
                # drives the decay to 0, i.e. pure autoregression -- the correct
                # inference behaviour. Unused by the other architectures.
                "global_step": torch.tensor(1e9, device=dev),
            }
            preds = model(data, pred_start=10, preds_length=20)
            if isinstance(preds, (tuple, list)):
                preds = preds[0]
            ndvi = preds[:, :, 0].float().cpu().numpy()             # (B, 20, H, W)

            for i, fp in enumerate(batch["filepath"]):
                fp = Path(fp)
                out_path = out_root / fp.parent.name / fp.name
                if out_path.exists() and not args.overwrite:
                    skipped += 1
                    continue
                with xr.open_dataset(fp) as target:
                    cube = make_ndvi_prediction_dataset(target, ndvi[i]).load()
                out_path.parent.mkdir(parents=True, exist_ok=True)
                cube.to_netcdf(out_path, encoding={PREDICTION_VARIABLE: {"dtype": "float32"}})
                written += 1

    print(f"[done] written={written} skipped={skipped} out={out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
