#!/usr/bin/env python
"""Inspect a local EarthNet2021 mirror before Stage2 training.

Run this on the server and paste the JSON summary back if the loader needs
dataset-specific mapping fixes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import EarthNet2021Config, EarthNet2021Dataset, inspect_earthnet_root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="EarthNet2021 root directory")
    parser.add_argument("--config", default="configs/train/stage2_earthnet_main.yaml")
    parser.add_argument("--split", default="train")
    parser.add_argument("--max-files", type=int, default=3)
    parser.add_argument("--external-driver-root")
    parser.add_argument("--dgh-stats-path")
    parser.add_argument("--try-loader", action="store_true", help="Also instantiate the Stage2 dataset and print one sample shape")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as handle:
        full_config = yaml.safe_load(handle)
    data_config = dict(full_config["data"])
    report = inspect_earthnet_root(
        args.root,
        split=args.split,
        max_files=args.max_files,
        data_format=str(data_config.get("data_format", "auto")),
        file_glob=data_config.get("file_glob"),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.try_loader:
        data_config["root"] = args.root
        data_config["split"] = args.split
        data_config["max_files"] = args.max_files
        if args.external_driver_root:
            data_config["external_driver_root"] = args.external_driver_root
        if args.dgh_stats_path:
            data_config["dgh_stats_path"] = args.dgh_stats_path
        cfg = EarthNet2021Config.from_config(data_config, split=args.split)
        ds = EarthNet2021Dataset(cfg)
        sample = ds[0]
        shape_report = {
            key: list(value.shape)
            for key, value in sample.items()
            if hasattr(value, "shape")
        }
        print("\n[loader_sample_shapes]")
        print(json.dumps(shape_report, indent=2, ensure_ascii=False))
        print("\n[meta]")
        print(json.dumps(sample.get("meta", {}), indent=2, ensure_ascii=False))
        feature_names = cfg.driver_spec.feature_names
        valid_rate = sample["D_mask"].float().mean(dim=0).tolist()
        print("\n[driver_valid_rate]")
        print(json.dumps(dict(zip(feature_names, valid_rate)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
