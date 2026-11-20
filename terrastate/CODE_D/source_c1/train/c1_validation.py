"""GreenEarthNet eval.py RMSE projection (HQ filter, pixel -> cube/LC -> LC)."""
import math
from collections import defaultdict


def cube_scores(target, prediction):
    import numpy as np

    full = (target.s2_dlmask < 1) & target.s2_SCL.isin([1, 2, 4, 5, 6, 7])
    nir, red = target.s2_B8A, target.s2_B04
    ndvi = ((nir - red) / (nir + red + 1e-8)).where(full).clip(-1, 1)
    selected = ndvi.sel(time=prediction.time)
    count = full.sel(time=prediction.time).sum("time")
    rmse = (((selected - prediction.clip(-1, 1).fillna(0.5)) ** 2).mean("time")) ** 0.5
    keep = (
        (target.esawc_lc < 41) & (ndvi.min("time") > 0) & (count >= 10)
        & (full.sum("time") - count >= 3) & (selected.std("time") > 0.1)
    )
    classes = target.esawc_lc.broadcast_like(rmse).values
    values = rmse.where(keep).values
    return {
        float(lc): float(values[(classes == lc) & np.isfinite(values)].mean(dtype=np.float64))
        for lc in np.unique(classes[np.isfinite(values)])
    }


def score_file(path, prediction, context_len):
    import xarray as xr

    with xr.open_dataset(path) as target:
        dates = target.time.isel(time=slice(4, None, 5))[context_len:]
        pred = xr.DataArray(prediction, dims=("time", "lat", "lon"),
                            coords={"time": dates, "lat": target.lat, "lon": target.lon})
        return cube_scores(target, pred)


def aggregate(expected, partitions):
    cubes = {}
    for partition in partitions:
        for cube, values in partition:
            if cube in cubes:
                if cubes[cube] != values:
                    return None, "inconsistent_duplicate"
            else:
                cubes[cube] = values
    if set(cubes) != set(expected) or len(set(expected)) != len(expected):
        return None, "incomplete"
    groups = defaultdict(list)
    for cube in sorted(cubes):
        for landcover, value in cubes[cube].items():
            if not math.isfinite(value):
                return None, "nonfinite"
            groups[landcover].append(value)
    if not groups:
        return None, "empty"
    return math.fsum(math.fsum(v) / len(v) for v in groups.values()) / len(groups), "ok"


def improved(best, score, epoch, step):
    if score is not None and math.isfinite(score) and (best is None or score < best["score"]):
        return {"score": score, "epoch": epoch, "step": step}
    return best

