"""GreenEarthNet CVPR 2024 evaluation protocol.

The formulas and aggregation order follow the authors' public ``eval.py`` at
commit ``a0329636631371a4aaa9a95c75ed0a37d27b8c4f``.  Keeping this evaluator
separate from the legacy EarthNet ENS scorer prevents the two protocols from
being accidentally mixed in a paper table.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr


OFFICIAL_REPOSITORY = "https://github.com/vitusbenson/greenearthnet"
OFFICIAL_EVALUATOR_COMMIT = "a0329636631371a4aaa9a95c75ed0a37d27b8c4f"
PREDICTION_VARIABLE = "ndvi_pred"
VALID_SCL_CLASSES = (1, 2, 4, 5, 6, 7)
OUTPERFORMANCE_THRESHOLDS = {
    "rmse": 0.01,
    "nnse": 0.05,
    "R2": 0.05,
    "biasabs": 0.01,
}


def expected_prediction_times(
    target: xr.Dataset,
    *,
    context_steps: int = 10,
    target_steps: int = 20,
    offset_days: int = 4,
    stride_days: int = 5,
) -> xr.DataArray:
    """Return the official 20 five-daily target timestamps."""

    if "time" not in target.coords:
        raise ValueError("GreenEarthNet target has no time coordinate")
    sampled = target.time.isel(time=slice(offset_days, None, stride_days))
    required = context_steps + target_steps
    if sampled.size < required:
        raise ValueError(
            f"GreenEarthNet target has only {sampled.size} five-daily steps; "
            f"expected at least {required}"
        )
    return sampled.isel(time=slice(context_steps, required))


def validate_prediction_dataset(
    target: xr.Dataset,
    prediction: xr.Dataset,
    *,
    prediction_name: str = PREDICTION_VARIABLE,
) -> None:
    """Reject malformed or temporally misaligned prediction files."""

    if prediction_name not in prediction:
        raise KeyError(f"Prediction is missing variable {prediction_name!r}")
    array = prediction[prediction_name]
    if tuple(array.dims) != ("time", "lat", "lon"):
        raise ValueError(
            f"{prediction_name} must use dims ('time','lat','lon'), got {array.dims}"
        )
    expected = expected_prediction_times(target)
    if array.sizes.get("time") != expected.size:
        raise ValueError(
            f"Prediction has {array.sizes.get('time')} target steps; "
            f"expected {expected.size}"
        )
    if not np.array_equal(array.time.values, expected.values):
        raise ValueError("Prediction timestamps do not match the official target times")
    for coordinate in ("lat", "lon"):
        if coordinate not in target.coords:
            raise ValueError(f"Target is missing coordinate {coordinate!r}")
        if not np.array_equal(array[coordinate].values, target[coordinate].values):
            raise ValueError(f"Prediction {coordinate} coordinate does not match target")
    values = np.asarray(array.values)
    if np.isinf(values).any():
        raise ValueError("Prediction contains infinite values")


def official_clear_mask(target: xr.Dataset) -> xr.DataArray:
    """Evaluation-only clear-pixel mask from DL mask and Sentinel-2 SCL."""

    required = ("s2_dlmask", "s2_SCL")
    missing = [name for name in required if name not in target]
    if missing:
        raise KeyError(f"Target is missing official mask variables: {missing}")
    return (target.s2_dlmask < 1) & target.s2_SCL.isin(VALID_SCL_CLASSES)


def target_ndvi(target: xr.Dataset) -> xr.DataArray:
    missing = [name for name in ("s2_B8A", "s2_B04") if name not in target]
    if missing:
        raise KeyError(f"Target is missing NDVI bands: {missing}")
    return ((target.s2_B8A - target.s2_B04) / (
        target.s2_B8A + target.s2_B04 + 1e-8
    )).clip(-1, 1)


def compute_pixel_metrics(
    target: xr.Dataset,
    prediction: xr.Dataset,
    *,
    prediction_name: str = PREDICTION_VARIABLE,
    subset_hq: bool = True,
    validate: bool = True,
) -> pd.DataFrame:
    """Compute official per-pixel metrics for one minicube."""

    if validate:
        validate_prediction_dataset(target, prediction, prediction_name=prediction_name)
    for name in ("esawc_lc", "geom_cls", "cop_dem"):
        if name not in target:
            raise KeyError(f"Target is missing official evaluator variable {name!r}")

    mask_full = official_clear_mask(target)
    mask = mask_full.sel(time=prediction.time)
    ndvi_full = target_ndvi(target).where(mask_full)
    ndvi_true = ndvi_full.sel(time=prediction.time)
    ndvi_pred = prediction[prediction_name].clip(-1, 1).fillna(0.5)

    squared_error = (ndvi_true - ndvi_pred) ** 2
    mse = squared_error.mean("time")
    target_mean = ndvi_true.mean("time")
    target_variation = ((ndvi_true - target_mean) ** 2).sum("time")
    nse = 1.0 - squared_error.sum("time") / target_variation

    metrics: dict[str, xr.DataArray] = {
        # The official implementation stores normalized NSE per pixel, then
        # reverses the transform only after land-cover-balanced aggregation.
        "nnse": 1.0 / (2.0 - nse),
        "n_obs_full": mask_full.sum("time"),
        "n_obs": mask.sum("time"),
        "sigma_targ": ndvi_true.std("time"),
        "sigma_pred": ndvi_pred.where(mask).std("time"),
        "bias": ndvi_true.mean("time") - ndvi_pred.where(mask).mean("time"),
        "min_ndvi_targ": ndvi_full.min("time"),
        "rmse": mse ** 0.5,
        "r": xr.corr(ndvi_true, ndvi_pred, dim="time"),
        "landcover": target.esawc_lc,
        "geom": target.geom_cls,
        "cop_dem": target.cop_dem,
    }
    for start in (0, 5, 10, 15):
        metrics[f"rmse_{start}_{start + 5}"] = (
            squared_error.isel(time=slice(start, start + 5)).mean("time") ** 0.5
        )

    frame = (
        xr.Dataset(metrics)
        .to_dataframe()
        .drop(columns="sentinel:product_id", errors="ignore")
    )
    if subset_hq:
        frame = frame[
            (frame.landcover < 41)
            & (frame.min_ndvi_targ > 0.0)
            & (frame.n_obs >= 10)
            & ((frame.n_obs_full - frame.n_obs) >= 3)
            & (frame.sigma_targ > 0.1)
        ]
    return frame


def score_cube_paths(
    target_path: str | Path,
    prediction_path: str | Path,
    *,
    prediction_name: str = PREDICTION_VARIABLE,
) -> pd.DataFrame:
    target_path = Path(target_path)
    prediction_path = Path(prediction_path)
    with xr.open_dataset(target_path) as target, xr.open_dataset(prediction_path) as prediction:
        frame = compute_pixel_metrics(
            target,
            prediction,
            prediction_name=prediction_name,
        ).reset_index()
    frame["id"] = target_path.stem
    frame["season"] = target_path.parent.stem
    return frame


def summarize_scores(
    frame: pd.DataFrame,
    comparison: pd.DataFrame | None = None,
) -> dict[str, float]:
    """Apply the official cube/land-cover-balanced aggregation order."""

    if frame.empty:
        raise ValueError("No eligible GreenEarthNet pixels were scored")
    required = {
        "id", "landcover", "nnse", "rmse", "r", "bias",
        "rmse_0_5", "rmse_5_10", "rmse_10_15", "rmse_15_20",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"Score frame is missing columns: {missing}")

    nnse_lc = _landcover_balanced(frame, "nnse")
    rmse_lc = _landcover_balanced(frame, "rmse")
    r2_lc = _landcover_balanced(frame.assign(R2=frame.r ** 2), "R2")
    biasabs_lc = _landcover_balanced(frame.assign(biasabs=frame.bias.abs()), "biasabs")
    result: dict[str, float] = {
        "nse": float(2.0 - 1.0 / nnse_lc.mean()),
        "rmse": float(rmse_lc.mean()),
        "R2": float(r2_lc.mean()),
        "biasabs": float(biasabs_lc.mean()),
    }

    for label, code in (("forest", 10), ("shrub", 20), ("grass", 30), ("crop", 40)):
        if code in nnse_lc.index:
            result[f"nse_{label}"] = float(2.0 - 1.0 / nnse_lc.loc[code])
            result[f"rmse_{label}"] = float(rmse_lc.loc[code])
            result[f"R2_{label}"] = float(r2_lc.loc[code])
            result[f"biasabs_{label}"] = float(biasabs_lc.loc[code])

    for start in (0, 5, 10, 15):
        key = f"rmse_{start}_{start + 5}"
        result[key] = float(_landcover_balanced(frame, key).mean())

    if comparison is not None:
        result.update(_outperformance_metrics(frame, comparison))
        result["outperformance"] = result["gain_outperform"]
    result["rmse25"] = result["rmse_0_5"]
    return result


def summarize_score_parquets(
    score_dir: str | Path,
    comparison_score_dir: str | Path | None = None,
) -> dict[str, float]:
    """Memory-bounded official aggregation over per-region Parquet files."""

    score_paths = sorted(Path(score_dir).glob("scores_en21x_*.parquet"))
    if not score_paths:
        raise FileNotFoundError(f"No GreenEarthNet score Parquets under {score_dir}")

    cube_landcover_frames = []
    for path in score_paths:
        frame = pd.read_parquet(path)
        frame = frame.assign(R2=frame.r ** 2, biasabs=frame.bias.abs())
        columns = [
            "nnse", "rmse", "R2", "biasabs",
            "rmse_0_5", "rmse_5_10", "rmse_10_15", "rmse_15_20",
        ]
        cube_landcover_frames.append(
            frame.groupby(["id", "landcover"], as_index=False)[columns].mean()
        )
    cube_landcover = pd.concat(cube_landcover_frames, ignore_index=True)
    # IDs are official minicube IDs and should be globally unique.  Fail rather
    # than silently reweight if a malformed tree repeats one across regions.
    if cube_landcover.duplicated(["id", "landcover"]).any():
        raise ValueError("Duplicate id/landcover groups across score Parquets")

    by_landcover = cube_landcover.groupby("landcover").mean(numeric_only=True)
    result: dict[str, float] = {
        "nse": float(2.0 - 1.0 / by_landcover.nnse.mean()),
        "rmse": float(by_landcover.rmse.mean()),
        "R2": float(by_landcover.R2.mean()),
        "biasabs": float(by_landcover.biasabs.mean()),
    }
    for label, code in (("forest", 10), ("shrub", 20), ("grass", 30), ("crop", 40)):
        if code in by_landcover.index:
            row = by_landcover.loc[code]
            result[f"nse_{label}"] = float(2.0 - 1.0 / row.nnse)
            result[f"rmse_{label}"] = float(row.rmse)
            result[f"R2_{label}"] = float(row.R2)
            result[f"biasabs_{label}"] = float(row.biasabs)
    for start in (0, 5, 10, 15):
        key = f"rmse_{start}_{start + 5}"
        result[key] = float(by_landcover[key].mean())

    if comparison_score_dir is not None:
        gain_frames = []
        comparison_root = Path(comparison_score_dir)
        for model_path in score_paths:
            baseline_path = comparison_root / model_path.name
            if not baseline_path.is_file():
                raise FileNotFoundError(
                    f"Missing comparison score Parquet: {baseline_path}"
                )
            model = pd.read_parquet(model_path)
            baseline = pd.read_parquet(baseline_path)
            index = ["lon", "lat", "id", "season", "landcover"]
            model = model.set_index(index).sort_index()
            baseline = baseline.set_index(index).sort_index()
            if not model.index.equals(baseline.index):
                raise ValueError(
                    f"Model/baseline eligible pixels differ for {model_path.name}"
                )
            gains = pd.DataFrame(
                {
                    "nnse": -1.0 / model.nnse + 1.0 / baseline.nnse,
                    "R2": model.r ** 2 - baseline.r ** 2,
                    "rmse": baseline.rmse - model.rmse,
                    "biasabs": baseline.bias.abs() - model.bias.abs(),
                }
            ).reset_index()
            gain_frames.append(
                gains.groupby(["id", "landcover"], as_index=False)[
                    ["nnse", "R2", "rmse", "biasabs"]
                ].mean()
            )
        gain_frame = pd.concat(gain_frames, ignore_index=True)
        if gain_frame.duplicated(["id", "landcover"]).any():
            raise ValueError("Duplicate gain groups across comparison Parquets")
        gain_lc = gain_frame.groupby("landcover").mean(numeric_only=True)
        for name in ("nnse", "R2", "rmse", "biasabs"):
            result[f"gain_{name}_mean"] = float(gain_lc[name].mean())
        wins = sum(
            (gain_frame[name] > threshold).astype(float)
            for name, threshold in OUTPERFORMANCE_THRESHOLDS.items()
        )
        result["gain_outperform"] = float((wins > 2).mean())
        result["outperformance"] = result["gain_outperform"]

    result["rmse25"] = result["rmse_0_5"]
    return result


def _landcover_balanced(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame.groupby(["id", "landcover"])[column].mean().groupby("landcover").mean()


def _outperformance_metrics(
    frame: pd.DataFrame,
    comparison: pd.DataFrame,
) -> dict[str, float]:
    index = ["lon", "lat", "id", "season", "landcover"]
    required = set(index) | {"nnse", "r", "rmse", "bias"}
    for name, candidate in (("model", frame), ("comparison", comparison)):
        missing = sorted(required - set(candidate.columns))
        if missing:
            raise KeyError(f"{name} score frame is missing columns: {missing}")

    model = frame.set_index(index).sort_index()
    baseline = comparison.set_index(index).sort_index()
    common = model.index.intersection(baseline.index)
    if common.empty:
        raise ValueError("Model and comparison scores have no aligned pixels")
    model = model.loc[common]
    baseline = baseline.loc[common]
    gains = {
        "nnse": -1.0 / model.nnse + 1.0 / baseline.nnse,
        "R2": model.r ** 2 - baseline.r ** 2,
        "rmse": baseline.rmse - model.rmse,
        "biasabs": baseline.bias.abs() - model.bias.abs(),
    }
    output: dict[str, float] = {}
    grouped_gains = {}
    for name, values in gains.items():
        grouped = values.groupby(["id", "landcover"]).mean()
        grouped_gains[name] = grouped
        output[f"gain_{name}_mean"] = float(grouped.groupby("landcover").mean().mean())

    wins = sum(
        (grouped_gains[name] > threshold).astype(float)
        for name, threshold in OUTPERFORMANCE_THRESHOLDS.items()
    )
    output["gain_outperform"] = float((wins > 2).mean())
    return output


def rgbn_to_ndvi(
    prediction: np.ndarray,
    *,
    red_index: int = 2,
    nir_index: int = 3,
) -> np.ndarray:
    """Convert ``[T,C,H,W]`` RGBN reflectance to clipped NDVI."""

    array = np.asarray(prediction, dtype=np.float32)
    if array.ndim != 4:
        raise ValueError(f"Expected prediction [T,C,H,W], got {array.shape}")
    if max(red_index, nir_index) >= array.shape[1]:
        raise ValueError("Red/NIR index is outside the prediction channel dimension")
    red = array[:, red_index]
    nir = array[:, nir_index]
    ndvi = (nir - red) / (nir + red + 1e-8)
    return np.clip(ndvi, -1.0, 1.0).astype(np.float32)


def make_prediction_dataset(
    target: xr.Dataset,
    prediction_rgbn: np.ndarray,
    *,
    red_index: int = 2,
    nir_index: int = 3,
) -> xr.Dataset:
    ndvi = rgbn_to_ndvi(
        prediction_rgbn,
        red_index=red_index,
        nir_index=nir_index,
    )
    times = expected_prediction_times(target)
    expected_shape = (times.size, target.sizes["lat"], target.sizes["lon"])
    if ndvi.shape != expected_shape:
        raise ValueError(f"NDVI prediction shape={ndvi.shape}, expected={expected_shape}")
    return xr.Dataset(
        {
            PREDICTION_VARIABLE: xr.DataArray(
                ndvi,
                coords={"time": times, "lat": target.lat, "lon": target.lon},
                dims=("time", "lat", "lon"),
            )
        }
    )
