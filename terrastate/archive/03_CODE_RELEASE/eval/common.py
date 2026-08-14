"""Shared evaluation utilities."""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader

from data.dataset import GreenEarthNetDataset
from models.terrastate import TerraState, load_checkpoint


def read_config(path):
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_model(config, checkpoint, device):
    model = TerraState(
        state_dim=config["model"]["state_dim"],
        weather_dim=config["model"]["weather_dim"],
        geography_dim=config["model"]["geography_dim"],
        horizon_dim=config["model"]["horizon_dim"],
        condition_dim=config["model"]["condition_dim"],
        history_pretrained=False,
    )
    load_checkpoint(model, checkpoint, strict=True)
    return model.to(device).eval()


def build_loader(data_root, config, batch_size=1, manifest=None):
    dataset = GreenEarthNetDataset(data_root, manifest=manifest)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=min(2, int(config["data"]["workers"])),
    )


def move(value, device):
    if torch.is_tensor(value):
        return value.to(device)
    if isinstance(value, list):
        return [move(item, device) for item in value]
    if isinstance(value, dict):
        return {key: move(item, device) for key, item in value.items()}
    return value


def target_and_mask(batch, prediction, config):
    start = int(config["model"]["context_steps"])
    steps = int(config["model"]["forecast_steps"])
    target = batch["dynamic"][0][:, start : start + steps, :1]
    clear = batch["dynamic_mask"][0][:, start : start + steps] < 1
    landcover = batch["landcover"]
    low = int(config["evaluation"]["vegetation_landcover_min"])
    high = int(config["evaluation"]["vegetation_landcover_max"])
    vegetation = (landcover >= low) & (landcover <= high)
    valid = clear & vegetation.unsqueeze(1) & torch.isfinite(prediction)
    return target, valid


def flattened(prediction, target, valid):
    return (
        prediction[valid].detach().cpu().double().numpy(),
        target[valid].detach().cpu().double().numpy(),
    )


def aggregate_metrics(prediction, target):
    if prediction.size == 0:
        raise ValueError("No valid pixels")
    error = prediction - target
    rmse = float(np.sqrt(np.mean(error**2)))
    bias = float(abs(np.mean(error)))
    if prediction.size < 2 or np.std(prediction) == 0 or np.std(target) == 0:
        r2 = float("nan")
    else:
        r2 = float(np.corrcoef(prediction, target)[0, 1] ** 2)
    return {"R2": r2, "RMSE": rmse, "absolute_bias": bias}


def official_cube_rows(batch, prediction):
    """Compute official per-cube, per-land-cover metric rows."""

    prediction = prediction.detach().cpu().double().numpy()
    target = batch["dynamic"][0][:, 10:30, :1].detach().cpu().double().numpy()
    clear = batch["evaluation_clear"].detach().cpu().numpy()[:, :, None]
    eligible = batch["evaluation_eligible"].detach().cpu().numpy()
    landcover = batch["landcover"].detach().cpu().numpy()[:, 0]
    cube_names = batch["cubename"]
    rows = []
    for index in range(prediction.shape[0]):
        pred = np.clip(prediction[index, :, 0], -1.0, 1.0)
        pred = np.where(np.isfinite(pred), pred, 0.5)
        truth = np.where(clear[index, :, 0], target[index, :, 0], np.nan)
        pred_masked = np.where(clear[index, :, 0], pred, np.nan)
        error = truth - pred_masked
        rmse = np.sqrt(np.nanmean(error**2, axis=0))
        bias = np.nanmean(error, axis=0)
        truth_mean = np.nanmean(truth, axis=0)
        pred_mean = np.nanmean(pred_masked, axis=0)
        truth_dev = truth - truth_mean
        pred_dev = pred_masked - pred_mean
        truth_ss = np.nansum(truth_dev**2, axis=0)
        pred_ss = np.nansum(pred_dev**2, axis=0)
        error_ss = np.nansum(error**2, axis=0)
        nse = 1.0 - error_ss / np.maximum(truth_ss, 1e-12)
        nnse = 1.0 / (2.0 - nse)
        correlation = np.nansum(truth_dev * pred_dev, axis=0) / np.sqrt(
            np.maximum(truth_ss * pred_ss, 1e-12)
        )
        blocks = {
            f"rmse_{start}_{start + 5}": np.sqrt(
                np.nanmean(error[start : start + 5] ** 2, axis=0)
            )
            for start in (0, 5, 10, 15)
        }
        valid_pixel = eligible[index]
        for code in sorted(np.unique(landcover[index][valid_pixel])):
            selected = valid_pixel & (landcover[index] == code)
            if not np.any(selected):
                continue
            row = {
                "cube": str(cube_names[index]),
                "landcover": int(code),
                "nnse": float(np.nanmean(nnse[selected])),
                "rmse": float(np.nanmean(rmse[selected])),
                "R2": float(np.nanmean(correlation[selected] ** 2)),
                "biasabs": float(np.nanmean(np.abs(bias[selected]))),
            }
            for key, values in blocks.items():
                row[key] = float(np.nanmean(values[selected]))
            rows.append(row)
    return rows


def summarize_official_rows(rows):
    """Apply minicube then land-cover balancing to official metric rows."""

    if not rows:
        raise ValueError("No eligible GreenEarthNet metric rows")
    keys = (
        "nnse",
        "rmse",
        "R2",
        "biasabs",
        "rmse_0_5",
        "rmse_5_10",
        "rmse_10_15",
        "rmse_15_20",
    )
    by_landcover = {}
    for row in rows:
        by_landcover.setdefault(row["landcover"], []).append(row)
    balanced = {
        key: float(
            np.mean(
                [
                    np.nanmean([row[key] for row in group])
                    for group in by_landcover.values()
                ]
            )
        )
        for key in keys
    }
    return {
        "R2": balanced["R2"],
        "RMSE": balanced["rmse"],
        "NSE": float(2.0 - 1.0 / balanced["nnse"]),
        "absolute_bias": balanced["biasabs"],
        "RMSE25": balanced["rmse_0_5"],
        "RMSE_5_10": balanced["rmse_5_10"],
        "RMSE_10_15": balanced["rmse_10_15"],
        "RMSE_15_20": balanced["rmse_15_20"],
    }


def cube_r2(rows):
    if not rows:
        return float("nan")
    return float(np.nanmean([row["R2"] for row in rows]))


def window_loss(prediction, target, valid):
    values = (prediction - target).square()[valid]
    return float(values.mean().detach().cpu()) if values.numel() else float("nan")


def percentile_interval(values, replicates, seed):
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    rng = np.random.default_rng(seed)
    draws = rng.choice(values, size=(replicates, values.size), replace=True).mean(1)
    return [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))]


def cluster_interval(values, clusters, replicates, seed):
    groups = {}
    for value, cluster in zip(values, clusters):
        groups.setdefault(str(cluster), []).append(float(value))
    keys = sorted(groups)
    rng = random.Random(seed)
    draws = []
    for _ in range(replicates):
        sampled = [groups[rng.choice(keys)] for _ in keys]
        draws.append(float(np.mean([item for group in sampled for item in group])))
    return [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))]


def write_json(path, payload):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
