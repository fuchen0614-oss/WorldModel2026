#!/usr/bin/env python
"""Evaluate state removal and identity-transition controls."""

import argparse
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.common import (  # noqa: E402
    build_loader,
    build_model,
    cube_r2,
    move,
    official_cube_rows,
    percentile_interval,
    read_config,
    summarize_official_rows,
    write_json,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def main():
    args = parse_args()
    config = read_config(args.config)
    device = torch.device(args.device)
    model = build_model(config, args.checkpoint, device)
    names = ("full", "state_removed", "identity_transition")
    rows = {name: [] for name in names}
    paired = {"state_removed": [], "identity_transition": []}
    with torch.no_grad():
        for batch in build_loader(args.data_root, config):
            batch = move(batch, device)
            outputs = {
                "full": model.forecast(batch),
                "state_removed": model.forecast(batch, state_scale=0.0),
                "identity_transition": model.forecast(
                    batch, identity_transition=True
                ),
            }
            cube_rows = {
                name: official_cube_rows(batch, prediction)
                for name, prediction in outputs.items()
            }
            full_r2 = cube_r2(cube_rows["full"])
            for name, prediction in outputs.items():
                rows[name].extend(cube_rows[name])
                if name != "full":
                    paired[name].append(
                        full_r2 - cube_r2(cube_rows[name])
                    )
    metrics = {name: summarize_official_rows(rows[name]) for name in names}
    repetitions = int(config["evaluation"]["bootstrap_replicates"])
    seed = int(config["evaluation"]["seed"])
    for name in paired:
        metrics[name]["paired_mean_delta_R2"] = float(
            torch.tensor(paired[name]).nanmean().item()
        )
        metrics[name]["paired_bootstrap_95"] = percentile_interval(
            paired[name], repetitions, seed
        )
        metrics[name]["official_delta_R2"] = (
            metrics["full"]["R2"] - metrics[name]["R2"]
        )
    metrics["protocol"] = "Q2 frozen-forward interventions"
    write_json(args.output, metrics)


if __name__ == "__main__":
    main()
