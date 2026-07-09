#!/usr/bin/env python
"""Generate Stage2 D/G/h ablation configs from the main config."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import yaml


ABLATIONS = {
    "no_D": {
        "conditions": {"use_D": False, "use_G": True, "use_h": True},
    },
    "no_G": {
        "conditions": {"use_D": True, "use_G": False, "use_h": True},
    },
    "no_h": {
        "conditions": {"use_D": True, "use_G": True, "use_h": False},
    },
    "z_only": {
        "conditions": {"use_D": False, "use_G": False, "use_h": False},
    },
    "no_vpd": {
        "conditions": {"use_D": True, "use_G": True, "use_h": True},
        "disabled_driver_features": ["vpd_mean", "vpd_max"],
    },
    "no_srad": {
        "conditions": {"use_D": True, "use_G": True, "use_h": True},
        "disabled_driver_features": ["srad_sum", "srad_mean"],
    },
    "no_precip": {
        "conditions": {"use_D": True, "use_G": True, "use_h": True},
        "disabled_driver_features": ["precip_sum", "precip_mean"],
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="configs/train/stage2_earthnet_main.yaml")
    parser.add_argument("--out-dir", default="configs/train/stage2_ablation")
    args = parser.parse_args()

    base_path = Path(args.base)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with base_path.open("r", encoding="utf-8") as handle:
        base = yaml.safe_load(handle)

    for name, changes in ABLATIONS.items():
        cfg = copy.deepcopy(base)
        cfg["model"]["conditions"] = changes["conditions"]
        cfg["data"]["disabled_driver_features"] = changes.get(
            "disabled_driver_features", []
        )
        cfg["checkpoint_dir"] = str(Path(cfg["checkpoint_dir"]).with_name(f"stage2_earthnet_{name}"))
        cfg["log_dir"] = str(Path(cfg["log_dir"]).with_name(f"stage2_earthnet_{name}"))
        out_path = out_dir / f"stage2_earthnet_{name}.yaml"
        with out_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(cfg, handle, sort_keys=False, allow_unicode=True)
        print(out_path)


if __name__ == "__main__":
    main()
