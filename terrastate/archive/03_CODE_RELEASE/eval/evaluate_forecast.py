#!/usr/bin/env python
"""Evaluate TerraState forecasting on a GreenEarthNet split."""

import argparse
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.common import (  # noqa: E402
    build_loader,
    build_model,
    move,
    official_cube_rows,
    read_config,
    summarize_official_rows,
    write_json,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument(
        "--manifest", default="manifests/q1_files.json"
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def main():
    args = parse_args()
    config = read_config(args.config)
    device = torch.device(args.device)
    model = build_model(config, args.checkpoint, device)
    rows = []
    with torch.no_grad():
        for batch in build_loader(
            args.data_root, config, manifest=args.manifest
        ):
            batch = move(batch, device)
            prediction = model(batch)
            rows.extend(official_cube_rows(batch, prediction))
    metrics = summarize_official_rows(rows)
    metrics["protocol"] = "Q1 land-cover-balanced forecast evaluation"
    write_json(args.output, metrics)


if __name__ == "__main__":
    main()
