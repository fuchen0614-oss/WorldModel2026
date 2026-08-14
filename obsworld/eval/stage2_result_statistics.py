"""Result statistics for the Stage2 EarthNet main experiment (no-U).

Additive layer on top of ``eval/greenearthnet_protocol.py`` (the commit-pinned
official scorer, left untouched). Provides the two artifacts the frozen draft
requires but the scorer does not emit:

1. ``per_horizon_ndvi_metrics`` — a fine 5-day-granularity per-horizon
   (day 5,10,...,100) NDVI RMSE and *spatial* R2 curve for Figure 2. It returns
   pooled sufficient statistics (Σ squared error, pixel count, Σ true, Σ true²)
   so that curves from many cubes can be aggregated into a correct population
   estimate by pooling.

2. ``tile_cluster_paired_bootstrap`` — the paragraph-4.6-mandated PAIRED,
   tile-clustered bootstrap 95% CI for the central Rollout-P4 vs Direct-P4
   claim (resample whole EarthNet tiles with replacement so spatially
   correlated minicubes are not treated as independent).

Design decisions (flagged for review, see 66_... work note):
- ``r2_spatial(t)`` is the SPATIAL explained variance across eligible pixels at
  lead time t: ``1 - SS_res(t)/SS_tot(t)`` with ``SS_tot`` the variance of the
  *true NDVI field* at t. This is DISTINCT from the headline table R2 in
  greenearthnet_protocol, which is a land-cover-balanced mean of the squared
  *temporal* Pearson correlation. They are different quantities; do not conflate
  them. Cross-cube aggregation pools sufficient stats and re-centers SS_tot on
  the pooled global mean (a true population estimate).
- Recommendation: use RMSE (stable) as the headline paired-CI metric; spatial R2
  can be volatile at near-homogeneous horizons and is best shown as a curve only.
- Eligibility reuses the official GreenEarthNet HQ subset criteria
  (landcover<41, min_ndvi>0, n_obs>=10, (n_obs_full-n_obs)>=3, sigma_targ>0.1).
- The bootstrap cluster is the EarthNet tile (first 5 chars of the cube id);
  it is CUBE-weighted (each cube equal), whereas the Figure-2 curve is
  PIXEL-weighted (larger cubes contribute more) — the two artifacts therefore
  weight "the same experiment" differently, by design. A plain percentile
  interval is used; with many tiles its O(1/K) ratio bias is negligible.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

from eval.greenearthnet_protocol import (
    PREDICTION_VARIABLE,
    official_clear_mask,
    target_ndvi,
    validate_prediction_dataset,
)

STRIDE_DAYS = 5


def tile_of(cube_id: str) -> str:
    """EarthNet tile (bootstrap cluster) = the leading 5-char tile code."""

    return str(cube_id)[:5]


def _hq_pixel_eligibility(target: xr.Dataset, prediction: xr.Dataset) -> tuple:
    """Return (ndvi_true[T,H,W] masked, ndvi_pred[T,H,W], clear[T,H,W], eligible[H,W])."""

    validate_prediction_dataset(target, prediction)
    if "esawc_lc" not in target:
        raise KeyError("Target is missing eligibility variable 'esawc_lc'")
    times = prediction.time
    mask_full = official_clear_mask(target)
    ndvi_all = target_ndvi(target).where(mask_full)
    clear = mask_full.sel(time=times)
    ndvi_true = ndvi_all.sel(time=times)
    ndvi_pred = prediction[PREDICTION_VARIABLE].clip(-1, 1).fillna(0.5)

    n_obs_full = mask_full.sum("time")
    n_obs = clear.sum("time")
    sigma_targ = ndvi_true.std("time")
    min_ndvi_targ = ndvi_all.min("time")
    eligible = (
        (target.esawc_lc < 41)
        & (min_ndvi_targ > 0.0)
        & (n_obs >= 10)
        & ((n_obs_full - n_obs) >= 3)
        & (sigma_targ > 0.1)
    )
    return ndvi_true, ndvi_pred, clear, eligible


def per_horizon_ndvi_metrics(
    target: xr.Dataset,
    prediction: xr.Dataset,
    *,
    cube_id: str | None = None,
) -> pd.DataFrame:
    """Per-horizon NDVI sufficient statistics for one minicube.

    Columns: ``horizon_day, n, sum_sq_err, sum_true, sum_true_sq, rmse,
    r2_spatial`` (one row per of the 20 five-daily target steps). ``rmse`` /
    ``r2_spatial`` are the per-cube values; aggregate across cubes with
    :func:`aggregate_horizon_curves` (correct population pooling).
    """

    ndvi_true, ndvi_pred, clear, eligible = _hq_pixel_eligibility(target, prediction)
    rows: list[dict[str, Any]] = []
    n_steps = ndvi_true.sizes["time"]
    for i in range(n_steps):
        true_t = ndvi_true.isel(time=i)
        pred_t = ndvi_pred.isel(time=i)
        # Count n from the actually-usable (eligible, clear, non-NaN) pixels so
        # rmse = sqrt(sum_sq_err / n) divides by exactly the summed population.
        valid = clear.isel(time=i) & eligible & true_t.notnull() & pred_t.notnull()
        n = int(valid.sum())
        tv = true_t.where(valid)
        pv = pred_t.where(valid)
        sum_sq_err = float(((tv - pv) ** 2).sum())
        sum_true = float(tv.sum())
        sum_true_sq = float((tv ** 2).sum())
        if n > 0:
            ss_tot = sum_true_sq - sum_true ** 2 / n
            rmse = float(np.sqrt(sum_sq_err / n))
            r2 = float(1.0 - sum_sq_err / ss_tot) if ss_tot > 0 else float("nan")
        else:
            rmse, r2 = float("nan"), float("nan")
        rows.append(
            {
                "horizon_day": int((i + 1) * STRIDE_DAYS),
                "n": n,
                "sum_sq_err": sum_sq_err,
                "sum_true": sum_true,
                "sum_true_sq": sum_true_sq,
                "rmse": rmse,
                "r2_spatial": r2,
            }
        )
    frame = pd.DataFrame(rows)
    if cube_id is not None:
        frame.insert(0, "id", str(cube_id))
    return frame


def aggregate_horizon_curves(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Pool per-cube per-horizon sufficient statistics into one population curve.

    ``rmse(t) = sqrt(Σsse / Σn)`` (pixel-weighted population RMSE);
    ``r2_spatial(t) = 1 - Σsse / SS_tot`` with ``SS_tot`` re-centred on the
    pooled global mean ``SS_tot = Σtrue² - (Σtrue)²/Σn`` (a true population R2,
    not a within-cube one).
    """

    if not frames:
        raise ValueError("aggregate_horizon_curves received no frames")
    pooled = (
        pd.concat(frames, ignore_index=True)
        .groupby("horizon_day", as_index=False)[
            ["n", "sum_sq_err", "sum_true", "sum_true_sq"]
        ]
        .sum()
    )
    n = pooled["n"].to_numpy(dtype=float)
    sse = pooled["sum_sq_err"].to_numpy(dtype=float)
    st = pooled["sum_true"].to_numpy(dtype=float)
    sts = pooled["sum_true_sq"].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        rmse = np.where(n > 0, np.sqrt(sse / n), np.nan)
        ss_tot = sts - np.where(n > 0, st ** 2 / n, np.nan)
        r2 = np.where(ss_tot > 0, 1.0 - sse / ss_tot, np.nan)
    pooled["rmse"] = rmse
    pooled["r2_spatial"] = r2
    return pooled.sort_values("horizon_day").reset_index(drop=True)


def paired_per_cube_frame(
    metric_a: pd.DataFrame,
    metric_b: pd.DataFrame,
    *,
    value_col: str,
    id_col: str = "id",
) -> pd.DataFrame:
    """Align two per-cube metric tables on cube id and form the paired diff.

    Returns ``id, tile, a, b, diff`` where ``diff = a - b``. Rows with a NaN in
    either metric are dropped so the point estimate and the bootstrap CI operate
    on exactly the same sample. (Convention: for a lower-is-better metric pass
    metric_a=baseline, metric_b=model so diff>0 means model better; for a
    higher-is-better metric pass metric_a=model, metric_b=baseline.)
    """

    a = metric_a[[id_col, value_col]].rename(columns={value_col: "a"})
    b = metric_b[[id_col, value_col]].rename(columns={value_col: "b"})
    merged = a.merge(b, on=id_col, how="inner").dropna(subset=["a", "b"])
    if merged.empty:
        raise ValueError("No common non-NaN cube ids between the two metric tables")
    merged["diff"] = merged["a"] - merged["b"]
    merged["tile"] = merged[id_col].map(tile_of)
    return merged.rename(columns={id_col: "id"})[["id", "tile", "a", "b", "diff"]]


def tile_cluster_paired_bootstrap(
    paired: pd.DataFrame,
    *,
    value_col: str = "diff",
    cluster_col: str = "tile",
    n_boot: int = 2000,
    ci: float = 0.95,
    seed: int = 20260718,
) -> dict[str, float]:
    """Tile-clustered paired bootstrap CI for the mean of ``value_col``.

    Resamples whole clusters (tiles) with replacement ``n_boot`` times; within a
    drawn cluster all its cube-level paired values are kept, so spatial
    correlation inside a tile does not inflate significance. Requires >=2
    clusters (between-cluster variance is otherwise unidentifiable).
    """

    if paired.empty:
        raise ValueError("tile_cluster_paired_bootstrap received an empty frame")
    if not 0.0 < ci < 1.0:
        raise ValueError(f"ci must be in (0,1), got {ci}")
    clean = paired.dropna(subset=[value_col])
    if clean.empty:
        raise ValueError(f"All {value_col} values are NaN")
    values_by_cluster = {
        key: np.asarray(sub[value_col].to_numpy(dtype=float))
        for key, sub in clean.groupby(cluster_col)
    }
    clusters = list(values_by_cluster)
    n_clusters = len(clusters)
    if n_clusters < 2:
        raise ValueError(
            f"tile-cluster bootstrap needs >=2 clusters, got {n_clusters}; "
            "a CI from a single tile would be degenerate/spuriously significant"
        )
    rng = np.random.default_rng(seed)
    point = float(np.mean(np.concatenate(list(values_by_cluster.values()))))
    boot = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        drawn = rng.integers(0, n_clusters, size=n_clusters)
        pooled = np.concatenate([values_by_cluster[clusters[j]] for j in drawn])
        boot[b] = pooled.mean()
    alpha = (1.0 - ci) / 2.0
    lo = float(np.quantile(boot, alpha))
    hi = float(np.quantile(boot, 1.0 - alpha))
    if point > 0:
        p_one_sided = float(np.mean(boot <= 0.0))
    elif point < 0:
        p_one_sided = float(np.mean(boot >= 0.0))
    else:
        p_one_sided = float("nan")
    return {
        "estimate": point,
        "ci_low": lo,
        "ci_high": hi,
        "ci_level": ci,
        "n_boot": int(n_boot),
        "n_clusters": int(n_clusters),
        "n_samples": int(len(clean)),
        # One-sided bootstrap tail fraction on the far side of 0 from the
        # estimate's sign (NaN when the estimate is exactly 0).
        "p_one_sided": p_one_sided,
        "significant": bool(lo > 0.0 or hi < 0.0),
    }


def write_per_sample_records(frame: pd.DataFrame, path: str | Path) -> Path:
    """Persist per-sample records to Parquet (frozen evidence for re-analysis)."""

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out, index=False)
    return out
