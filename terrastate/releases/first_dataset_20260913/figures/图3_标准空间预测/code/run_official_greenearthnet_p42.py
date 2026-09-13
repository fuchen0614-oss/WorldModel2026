#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import torch


MODELS_TO_RUN = {
    "convlstm": ("convlstm/convlstm1M", "ConvLSTM 1M"),
    "predrnn": ("predrnn/predrnn1M", "PredRNN 1M"),
    "simvp": ("simvp/simvp6M", "SimVP 6M"),
    "contextformer": ("contextformer/contextformer6M", "Contextformer 6M"),
}


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def model_namespace(model_cls, values):
    parser = argparse.ArgumentParser(add_help=False)
    parser = model_cls.add_model_specific_args(parser)
    args = [f"--{key}={value}" for key, value in values.items()]
    return parser.parse_args(args)


def add_batch_and_device(value, device):
    if torch.is_tensor(value):
        return value.unsqueeze(0).to(device)
    if isinstance(value, list):
        return [add_batch_and_device(v, device) for v in value]
    if isinstance(value, dict):
        return {k: add_batch_and_device(v, device) for k, v in value.items()}
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--model-code", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--cube", type=Path, required=True)
    parser.add_argument("--figure-arrays", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--gpu", type=int, default=3)
    args = parser.parse_args()

    import sys
    sys.path.insert(0, str(args.model_code))
    from earthnet_models_pytorch.data.en21x_data import EarthNet2021XDataset
    from earthnet_models_pytorch.model import MODELS
    from earthnet_models_pytorch.utils import parse_setting

    device = torch.device(f"cuda:{args.gpu}" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(42)
    if device.type == "cuda":
        torch.cuda.set_device(device)

    dataset = EarthNet2021XDataset(args.cube.parent, dl_cloudmask=True, allow_fastaccess=False)
    matches = [i for i, p in enumerate(dataset.filepaths) if p.resolve() == args.cube.resolve()]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one dataset match for {args.cube}, found {len(matches)}")
    raw_item = dataset[matches[0]]
    data = add_batch_and_device(raw_item, device)
    data["global_step"] = torch.tensor(0.0, device=device)

    fig = np.load(args.figure_arrays)
    gt = fig["gt"]
    valid = fig["valid"].astype(bool)
    predictions = {}
    provenance = {
        "dataset_cube": str(args.cube),
        "model_code": str(args.model_code),
        "model_code_commit": subprocess.check_output(["git", "-C", str(args.model_code), "rev-parse", "HEAD"], text=True).strip(),
        "greenearthnet_repo": str(args.repo),
        "greenearthnet_commit": subprocess.check_output(["git", "-C", str(args.repo), "rev-parse", "HEAD"], text=True).strip(),
        "official_release": "https://zenodo.org/records/10793870",
        "official_archive_md5": "d9f531a7e6e3e1d497af30760ca6fcf9",
        "seed": 42,
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(device) if device.type == "cuda" else "CPU",
        "context_steps": 10,
        "target_steps": 20,
        "protocol": "official GreenEarthNet configuration and v0.1.0 earthnet-models-pytorch code; inference only",
        "models": {},
    }
    metric_rows = []

    for key, (subdir, display_name) in MODELS_TO_RUN.items():
        config = args.repo / "model_configs" / subdir / "seed=42.yaml"
        checkpoint = args.weights / subdir / "seed=42.ckpt"
        setting = parse_setting(config, track="iid_chopped")
        model_cls = MODELS[setting["Architecture"]]
        if key == "contextformer":
            # The constructor asks timm for a generic pretrained PVT initialization.
            # The released checkpoint contains the full PVT state, so prevent that
            # unnecessary network request before loading the official state strictly.
            import timm
            original_create_model = timm.create_model
            def offline_create_model(name, *positional, **keywords):
                keywords["pretrained"] = False
                return original_create_model(name, *positional, **keywords)
            timm.create_model = offline_create_model
            try:
                model = model_cls(model_namespace(model_cls, setting["Model"]))
            finally:
                timm.create_model = original_create_model
        else:
            model = model_cls(model_namespace(model_cls, setting["Model"]))
        ckpt = torch.load(checkpoint, map_location="cpu", weights_only=False)
        state = {name[len("model."):]: tensor for name, tensor in ckpt["state_dict"].items() if name.startswith("model.")}
        load_result = model.load_state_dict(state, strict=True)
        model.to(device).eval()
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)
            torch.cuda.synchronize(device)
        start = time.perf_counter()
        with torch.inference_mode():
            pred, _ = model(data, pred_start=10, preds_length=20)
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        elapsed = time.perf_counter() - start
        arr = pred[0, :, 0].detach().float().cpu().numpy()
        if arr.shape != (20, 128, 128) or not np.isfinite(arr).all():
            raise RuntimeError(f"Invalid {key} prediction: shape={arr.shape}, finite={np.isfinite(arr).all()}")
        predictions[key] = arr.astype(np.float32)
        sse = float(np.square(arr[valid] - gt[valid]).sum())
        n = int(valid.sum())
        provenance["models"][key] = {
            "display_name": display_name,
            "architecture": setting["Architecture"],
            "config": str(config),
            "config_sha256": sha256(config),
            "checkpoint": str(checkpoint),
            "checkpoint_sha256": sha256(checkpoint),
            "checkpoint_epoch": ckpt.get("epoch"),
            "checkpoint_global_step": ckpt.get("global_step"),
            "checkpoint_lightning_version": ckpt.get("pytorch-lightning_version"),
            "strict_load_missing": list(load_result.missing_keys),
            "strict_load_unexpected": list(load_result.unexpected_keys),
            "prediction_shape": list(arr.shape),
            "prediction_min": float(arr.min()),
            "prediction_max": float(arr.max()),
            "elapsed_seconds_single_cube": elapsed,
            "peak_gpu_bytes": int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else 0,
            "p42_pooled_rmse": float(np.sqrt(sse / n)),
            "p42_valid_values": n,
        }
        metric_rows.append({
            "model": display_name,
            "seed": 42,
            "candidate": "P42",
            "pooled_rmse": float(np.sqrt(sse / n)),
            "valid_values": n,
            "prediction_min": float(arr.min()),
            "prediction_max": float(arr.max()),
            "elapsed_seconds_single_cube": elapsed,
        })
        del model, ckpt, pred
        if device.type == "cuda":
            torch.cuda.empty_cache()

    args.out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out / "P42.npz", **predictions)
    (args.out / "P42_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    with (args.out / "P42_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metric_rows[0]))
        writer.writeheader()
        writer.writerows(metric_rows)
    print(json.dumps({k: v["p42_pooled_rmse"] for k, v in provenance["models"].items()}, indent=2))


if __name__ == "__main__":
    main()
