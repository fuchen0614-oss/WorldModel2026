#!/usr/bin/env python
"""Evaluate actual, matched-donor, and normalized-mean future weather."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.dataset import GreenEarthNetDataset  # noqa: E402
from eval.common import (  # noqa: E402
    build_model,
    cluster_interval,
    flattened,
    move,
    official_cube_rows,
    read_config,
    summarize_official_rows,
    target_and_mask,
    window_loss,
    write_json,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def collate_one(sample):
    output = {}
    for key, value in sample.items():
        if torch.is_tensor(value):
            output[key] = value.unsqueeze(0)
        elif isinstance(value, list):
            output[key] = [
                item.unsqueeze(0) if torch.is_tensor(item) else item
                for item in value
            ]
        else:
            output[key] = [value]
    return output


def main():
    args = parse_args()
    config = read_config(args.config)
    device = torch.device(args.device)
    model = build_model(config, args.checkpoint, device)
    dataset = GreenEarthNetDataset(args.data_root)
    lookup = {
        str(path.relative_to(Path(args.data_root))).replace("\\", "/"): index
        for index, path in enumerate(dataset.filepaths)
    }
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    names = ("actual", "matched_donor", "normalized_mean")
    rows = {name: [] for name in names}
    donor_deltas, mean_deltas, clusters = [], [], []
    donor_responses, mean_responses = [], []
    actual_lower = {"matched_donor": 0, "normalized_mean": 0}
    with torch.no_grad():
        for pair in manifest["pairs"]:
            current = move(collate_one(dataset[lookup[pair["sample"]]]), device)
            donor = move(collate_one(dataset[lookup[pair["donor"]]]), device)
            start = int(config["model"]["context_steps"])
            steps = int(config["model"]["forecast_steps"])
            actual_weather = current["dynamic"][1][:, start : start + steps]
            donor_weather = donor["dynamic"][1][:, start : start + steps]
            mean_weather = torch.zeros_like(actual_weather)
            predictions = {
                "actual": model.forecast(current, future_weather=actual_weather),
                "matched_donor": model.forecast(
                    current, future_weather=donor_weather
                ),
                "normalized_mean": model.forecast(
                    current, future_weather=mean_weather
                ),
            }
            target, valid = target_and_mask(
                current, predictions["actual"], config
            )
            losses = {}
            for name, prediction in predictions.items():
                rows[name].extend(official_cube_rows(current, prediction))
                losses[name] = window_loss(prediction, target, valid)
            donor_delta = losses["matched_donor"] - losses["actual"]
            mean_delta = losses["normalized_mean"] - losses["actual"]
            donor_deltas.append(donor_delta)
            mean_deltas.append(mean_delta)
            clusters.append(pair["cluster"])
            donor_responses.append(
                float(
                    (predictions["actual"] - predictions["matched_donor"])
                    .abs()[valid]
                    .mean()
                    .cpu()
                )
            )
            mean_responses.append(
                float(
                    (predictions["actual"] - predictions["normalized_mean"])
                    .abs()[valid]
                    .mean()
                    .cpu()
                )
            )
            actual_lower["matched_donor"] += int(donor_delta > 0)
            actual_lower["normalized_mean"] += int(mean_delta > 0)
    metrics = {name: summarize_official_rows(rows[name]) for name in names}
    repetitions = int(config["evaluation"]["bootstrap_replicates"])
    seed = int(config["evaluation"]["seed"])
    metrics["matched_donor"]["control_minus_actual_loss"] = float(
        np.mean(donor_deltas)
    )
    metrics["matched_donor"]["geographic_cluster_95"] = cluster_interval(
        donor_deltas, clusters, repetitions, seed
    )
    metrics["matched_donor"]["actual_lower_count"] = actual_lower["matched_donor"]
    metrics["normalized_mean"]["control_minus_actual_loss"] = float(
        np.mean(mean_deltas)
    )
    metrics["normalized_mean"]["geographic_cluster_95"] = cluster_interval(
        mean_deltas, clusters, repetitions, seed
    )
    metrics["normalized_mean"]["actual_lower_count"] = actual_lower["normalized_mean"]
    metrics["n_pairs"] = len(manifest["pairs"])
    metrics["mean_absolute_forecast_difference"] = {
        "actual_vs_matched_donor": float(np.mean(donor_responses)),
        "actual_vs_normalized_mean": float(np.mean(mean_responses)),
    }
    metrics["protocol"] = "Q3 complete-window response fidelity"
    write_json(args.output, metrics)


if __name__ == "__main__":
    main()
