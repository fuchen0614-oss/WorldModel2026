#!/usr/bin/env python
"""plan-b-pvt · quantify how much of the 0.583-vs-0.62 gap is aggregation convention.

Benson's own code is internally inconsistent about the land-cover R2 aggregation:
  * eval.py (the canonical evaluator)  -> TWO-level:  groupby(id, landcover)
    mean per cube, THEN groupby(landcover) mean, then mean over the 4 classes.
  * model_pixelwise/persistence.py     -> ONE-level:  groupby(landcover) over
    ALL pixels directly (pixel-count weighted).

They give different numbers. This script reads the per-pixel score parquets that
eval/eval_greenearthnet_official.py already wrote (scores_en21x_*.parquet) and
reports R2/RMSE/NSE under BOTH conventions, plus a pixel-weighted global r2, so
we can attribute the reproduction gap to convention vs. model vs. data.

No re-inference, no GPU: pure pandas over existing parquets (seconds).

Usage:
  python eval/diagnose_aggregation_gap.py <score_dir> [<score_dir> ...]
where each <score_dir> holds scores_en21x_*.parquet (e.g. the dir passed as
--output-dir to eval_greenearthnet_official.py for the B0 run).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

LC = (("forest", 10), ("shrub", 20), ("grass", 30), ("crop", 40))


def _load(score_dir: Path) -> pd.DataFrame:
    paths = sorted(score_dir.glob("scores_en21x_*.parquet"))
    if not paths:
        raise FileNotFoundError(f"no scores_en21x_*.parquet under {score_dir}")
    frame = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
    frame = frame.assign(R2=frame.r ** 2, biasabs=frame.bias.abs())
    return frame


def two_level(frame: pd.DataFrame) -> dict[str, float]:
    """Canonical eval.py order: per (season,id,landcover) mean, then per LC, then mean."""
    per_cube = frame.groupby(["season", "id", "landcover"], as_index=False)[
        ["R2", "rmse", "nnse", "biasabs"]
    ].mean()
    by_lc = per_cube.groupby("landcover").mean(numeric_only=True)
    out = {
        "R2": float(by_lc.R2.reindex([c for _, c in LC]).mean()),
        "rmse": float(by_lc.rmse.reindex([c for _, c in LC]).mean()),
        "nse": float(2.0 - 1.0 / by_lc.nnse.reindex([c for _, c in LC]).mean()),
    }
    for name, code in LC:
        if code in by_lc.index:
            out[f"R2_{name}"] = float(by_lc.R2.loc[code])
    return out


def one_level(frame: pd.DataFrame) -> dict[str, float]:
    """persistence.py order: per landcover over ALL pixels directly, then mean over LC."""
    by_lc = frame.groupby("landcover")[["R2", "rmse", "nnse", "biasabs"]].mean()
    out = {
        "R2": float(by_lc.R2.reindex([c for _, c in LC]).mean()),
        "rmse": float(by_lc.rmse.reindex([c for _, c in LC]).mean()),
        "nse": float(2.0 - 1.0 / by_lc.nnse.reindex([c for _, c in LC]).mean()),
    }
    for name, code in LC:
        if code in by_lc.index:
            out[f"R2_{name}"] = float(by_lc.R2.loc[code])
    return out


def global_pixel(frame: pd.DataFrame) -> dict[str, float]:
    """No land-cover balancing at all: mean r2 over every eligible pixel."""
    return {"R2": float(frame.R2.mean()), "rmse": float(frame.rmse.mean())}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for arg in sys.argv[1:]:
        score_dir = Path(arg)
        frame = _load(score_dir)
        two, one, glob = two_level(frame), one_level(frame), global_pixel(frame)
        print("=" * 72)
        print(f"score_dir      : {score_dir}")
        print(f"eligible pixels: {len(frame):,}")
        print("-" * 72)
        print(f"{'convention':<28}{'R2':>10}{'RMSE':>10}{'NSE':>10}")
        print(f"{'TWO-level (eval.py canon)':<28}{two['R2']:>10.4f}"
              f"{two['rmse']:>10.4f}{two['nse']:>10.4f}")
        print(f"{'ONE-level (persistence.py)':<28}{one['R2']:>10.4f}"
              f"{one['rmse']:>10.4f}{one['nse']:>10.4f}")
        print(f"{'global pixel (no LC bal.)':<28}{glob['R2']:>10.4f}"
              f"{glob['rmse']:>10.4f}{'':>10}")
        print("-" * 72)
        print(f"R2 gap ONE-minus-TWO : {one['R2'] - two['R2']:+.4f}")
        print("per-LC R2 (two-level):",
              {k[3:]: round(v, 4) for k, v in two.items() if k.startswith("R2_")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
