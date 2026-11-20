#!/usr/bin/env python3
"""Isolated matched-donor feature extractor with the EarthNet2021x mask fix."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import xarray as xr


def load_record(path: Path) -> dict:
    with xr.open_dataset(path, engine="netcdf4", cache=False) as ds:
        b8a = np.asarray(ds["s2_B8A"].isel(time=slice(0, 10)).values, dtype=float)
        b04 = np.asarray(ds["s2_B04"].isel(time=slice(0, 10)).values, dtype=float)
        # EarthNet2021x exposes s2_dlmask alongside the legacy s2_mask.  The
        # former is the dataset cloud mask: 0 is clear, nonzero is unusable.
        if "s2_dlmask" in ds:
            mask_name = "s2_dlmask"
        elif "s2_mask" in ds:
            mask_name = "s2_mask"
        else:
            raise ValueError(f"missing clear-observation mask: {path}")
        clear = np.asarray(ds[mask_name].isel(time=slice(0, 10)).values == 0)
        avail = np.asarray(ds["s2_avail"].isel(time=slice(0, 10)).values, dtype=float)
        lc = np.asarray(ds["esawc_lc"].values, dtype=float)
        times = np.asarray(ds["time"].values[:10])

    denom = b8a + b04
    ndvi = np.divide(b8a - b04, denom, out=np.full_like(denom, np.nan), where=np.abs(denom) > 1e-8)
    valid = np.isfinite(ndvi) & clear
    if avail.size:
        valid &= np.isfinite(avail)[:, None, None] & (avail[:, None, None] > 0)
    frame_means = np.array([
        float(np.nanmean(ndvi[t][valid[t]])) if np.any(valid[t]) else np.nan
        for t in range(ndvi.shape[0])
    ])
    finite = np.isfinite(frame_means)
    last = float(frame_means[np.flatnonzero(finite)[-1]]) if np.any(finite) else np.nan
    scalar = np.array([
        float(np.nanmean(frame_means)) if np.any(finite) else np.nan,
        float(np.nanstd(frame_means)) if np.any(finite) else np.nan,
        last,
        float(np.mean(finite)),
    ], dtype=float)

    lc = lc[np.isfinite(lc)]
    lc = np.rint(lc).astype(int) if lc.size else np.array([], dtype=int)
    hist = np.zeros(256, dtype=float)
    if lc.size:
        for value, count in Counter(lc.tolist()).items():
            if 0 <= value < hist.size:
                hist[value] = count
        hist /= hist.sum()

    if not np.all(np.isfinite(scalar)):
        raise ValueError(f"non-finite scalar feature: {path}")
    if not np.any(hist):
        raise ValueError(f"missing land-cover feature: {path}")
    return {
        "path": str(path),
        "season": str(times[0])[:7],
        "scalar": scalar,
        "lc": hist,
        "mask_source": mask_name,
        "finite_history_frames": int(finite.sum()),
        "available_frames": int(np.sum(np.isfinite(avail) & (avail > 0))),
        "clear_frames": int(np.sum(np.any(clear, axis=(1, 2)))),
    }
