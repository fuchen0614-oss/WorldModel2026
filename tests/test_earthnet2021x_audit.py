from __future__ import annotations

import numpy as np
import pytest

xr = pytest.importorskip("xarray")

from scripts.audit_earthnet2021x import (
    GREENEARTHNET_REQUIRED_VARIABLES,
    audit_netcdf,
)


def _write_cube(path, *, omit: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dynamic = np.zeros((150, 2, 3), dtype=np.float32)
    static = np.zeros((2, 3), dtype=np.float32)
    variables = {}
    for name in GREENEARTHNET_REQUIRED_VARIABLES:
        if name == omit:
            continue
        if name.startswith("eobs_"):
            variables[name] = (("time",), np.zeros(150, dtype=np.float32))
        elif name in {"esawc_lc", "geom_cls", "cop_dem"}:
            variables[name] = (("lat", "lon"), static)
        else:
            variables[name] = (("time", "lat", "lon"), dynamic)
    xr.Dataset(
        variables,
        coords={"time": np.arange(150), "lat": np.arange(2), "lon": np.arange(3)},
    ).to_netcdf(path)


def test_greenearthnet_audit_requires_all_eight_eobs_and_eval_fields(tmp_path):
    complete = tmp_path / "complete.nc"
    _write_cube(complete)
    report = audit_netcdf(
        complete,
        read_arrays=False,
        required_variables=GREENEARTHNET_REQUIRED_VARIABLES,
    )
    assert report["ok"]
    assert len(report["eobs_variables"]) == 8

    incomplete = tmp_path / "incomplete.nc"
    _write_cube(incomplete, omit="eobs_fg")
    report = audit_netcdf(
        incomplete,
        read_arrays=False,
        required_variables=GREENEARTHNET_REQUIRED_VARIABLES,
    )
    assert not report["ok"]
    assert report["missing_variables"] == ["eobs_fg"]
