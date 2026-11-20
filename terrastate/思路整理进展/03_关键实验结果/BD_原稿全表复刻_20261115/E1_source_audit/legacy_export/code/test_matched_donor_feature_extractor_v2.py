#!/usr/bin/env python3
"""Regression tests for the isolated matched-donor mask contract."""
from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

import numpy as np
import xarray as xr


def write_case(path: Path, *, both: bool = True, dlmask: np.ndarray | None = None, s2mask: np.ndarray | None = None, bad_ndvi: bool = False, unavailable: bool = False) -> None:
    t, y, x = 10, 2, 2
    b8a = np.ones((t, y, x), dtype=np.float32) * 0.7
    b04 = np.ones((t, y, x), dtype=np.float32) * 0.3
    if bad_ndvi:
        b8a.fill(0.0); b04.fill(0.0)
    include_dlmask = both or dlmask is not None
    if include_dlmask and dlmask is None:
        dlmask = np.zeros((t, y, x), dtype=np.float32)
    if s2mask is None:
        s2mask = np.zeros((t, y, x), dtype=np.float32)
    avail = np.zeros(t, dtype=np.float32) if unavailable else np.ones(t, dtype=np.float32)
    variables = {
        "s2_B8A": (("time", "y", "x"), b8a),
        "s2_B04": (("time", "y", "x"), b04),
        "s2_avail": (("time",), avail),
        "esawc_lc": (("y", "x"), np.ones((y, x), dtype=np.float32) * 10),
    }
    if include_dlmask:
        variables["s2_dlmask"] = (("time", "y", "x"), dlmask)
    if both or s2mask is not None:
        variables["s2_mask"] = (("time", "y", "x"), s2mask)
    xr.Dataset(variables, coords={"time": np.arange(t), "y": np.arange(y), "x": np.arange(x)}).to_netcdf(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-dir", type=Path, required=True)
    ap.add_argument("--work-dir", type=Path, required=True)
    args = ap.parse_args()
    import sys
    sys.path.insert(0, str(args.code_dir))
    from matched_donor_feature_extractor_v2 import load_record

    args.work_dir.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="mask_regression_", dir=args.work_dir))
    try:
        both = root / "both.nc"
        bad_legacy = np.ones((10, 2, 2), dtype=np.float32)
        write_case(both, both=True, s2mask=bad_legacy)
        rec = load_record(both)
        assert rec["mask_source"] == "s2_dlmask", rec

        only_legacy = root / "only_s2_mask.nc"
        write_case(only_legacy, both=False, dlmask=None, s2mask=np.zeros((10, 2, 2), dtype=np.float32))
        assert load_record(only_legacy)["mask_source"] == "s2_mask"

        no_clear = root / "no_clear.nc"
        write_case(no_clear, dlmask=np.ones((10, 2, 2), dtype=np.float32))
        try: load_record(no_clear)
        except ValueError: pass
        else: raise AssertionError("no-clear-observation case did not fail")

        bad_ndvi = root / "bad_ndvi.nc"
        write_case(bad_ndvi, bad_ndvi=True)
        try: load_record(bad_ndvi)
        except ValueError: pass
        else: raise AssertionError("nonfinite NDVI case did not fail")

        unavailable = root / "unavailable.nc"
        write_case(unavailable, unavailable=True)
        try: load_record(unavailable)
        except ValueError: pass
        else: raise AssertionError("availability case did not fail")
        print("PASS mask_selection_cases=5")
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
