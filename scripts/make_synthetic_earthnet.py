#!/usr/bin/env python
"""Create a tiny EarthNet-shaped dataset for server-side Stage2 smoke tests."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    root = Path(args.output_root)
    cube_dir = root / "train" / "32UMC"
    driver_dir = root / "drivers"
    cube_dir.mkdir(parents=True, exist_ok=True)
    driver_dir.mkdir(parents=True, exist_ok=True)

    name = (
        "32UMC_2017_01_01_2017_05_31_"
        "100_228_100_228_10_90_10_90.npz"
    )
    rng = np.random.default_rng(7)
    high = rng.uniform(0.05, 0.8, size=(128, 128, 7, 30)).astype(np.float32)
    high[:, :, 6, :] = 0.0
    mask = np.zeros((128, 128, 30), dtype=np.uint8)
    mask[:64, :64, 12] = 1
    meso = rng.normal(size=(80, 80, 5, 150)).astype(np.float32)
    meso[:, :, 0, :] = np.abs(meso[:, :, 0, :])
    np.savez_compressed(
        cube_dir / name,
        highresdynamic=high,
        highresmask=mask,
        mesodynamic=meso,
        highresstatic=np.full((128, 128, 1), 500.0, dtype=np.float32),
        mesostatic=np.zeros((80, 80, 1), dtype=np.float32),
    )
    days = np.arange(150, dtype=np.float32)
    np.savez_compressed(
        driver_dir / name,
        vpd=0.5 + days * 0.001,
        solar_radiation=10.0 + days * 0.01,
    )
    print(f"cube_root={root}")
    print(f"external_driver_root={driver_dir}")


if __name__ == "__main__":
    main()
