#!/usr/bin/env python
"""Export formal GreenEarthNet Table 1 deterministic baselines.

This is intentionally separate from the raw EarthNet2021x RGBN baseline
utility.  It follows the public GreenEarthNet repository's persistence and
pixel-wise climatology definitions, consumes an explicit frozen chopped-track
manifest, and writes the same hash-verified ``ndvi_pred`` NetCDF layout as a
learned Stage2 export.

For climatology, the public OOD-t protocol uses a matching *full* minicube
from the ``iidx`` tree (flat ``<full-cube-root>/<cubename>.nc`` layout).  The
chopped target itself supplies the context for Persistence.  No recursive
fallback or raw-IID/OOD alias is permitted.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import xarray as xr

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - cosmetic only
    def tqdm(iterable, *args, **kwargs):
        return iterable

from data.earthnet_manifest import (
    GREENEARTHNET_CHOPPED_PROTOCOL_ID,
    load_manifest_files,
    manifest_protocol_spec,
    resolve_manifest_root,
    write_json_atomic,
)
from eval.earthnet_table1 import (
    TABLE1_SCHEMA_VERSION,
    collect_output_records,
    greenearthnet_relative_path,
    source_manifest_identity,
    validate_existing_output,
)
from eval.greenearthnet_protocol import (
    OFFICIAL_EVALUATOR_COMMIT,
    OFFICIAL_REPOSITORY,
    PREDICTION_GRID_CLIMATOLOGY_DAILY,
    PREDICTION_GRID_FIVE_DAILY_20,
    PREDICTION_VARIABLE,
    expected_prediction_times,
    expected_prediction_times_for_grid,
    official_clear_mask,
    target_ndvi,
)
from eval.stage2_evaluation_provenance import prediction_records_digest


OFFICIAL_BASELINE_MODULES = {
    "persistence": "model_pixelwise/persistence.py",
    "climatology": "model_pixelwise/climatology.py",
}
BASELINE_PREDICTION_GRIDS = {
    "persistence": PREDICTION_GRID_FIVE_DAILY_20,
    # This deliberately mirrors the public implementation's
    # ``targ.time.isel(time=slice(50, None))`` rather than resampling it.
    "climatology": PREDICTION_GRID_CLIMATOLOGY_DAILY,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export exact GreenEarthNet-style Persistence/Climatology Table 1 predictions."
    )
    parser.add_argument("--baseline", required=True, choices=sorted(OFFICIAL_BASELINE_MODULES))
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--manifest-protocol",
        default=GREENEARTHNET_CHOPPED_PROTOCOL_ID,
        help="Must be greenearthnet_cvpr2024_chopped_v1 for this formal exporter.",
    )
    parser.add_argument("--split", required=True, help="Exact chopped track, e.g. ood-t_chopped.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prediction-manifest", default=None)
    parser.add_argument("--hash-mode", choices=("none", "sha256"), default="sha256")
    parser.add_argument("--verify-manifest-sizes", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--full-cube-root",
        help=(
            "Required only for climatology: flat directory containing matching full "
            "minicubes named <cubename>.nc (official OOD-t mapping: .../iidx)."
        ),
    )
    return parser.parse_args()


def _prediction_dataset(
    values: xr.DataArray,
    target: xr.Dataset,
    *,
    prediction_grid: str,
) -> xr.Dataset:
    """Return a prediction on one explicitly declared public time grid."""

    times = expected_prediction_times_for_grid(target, prediction_grid)
    selected = values.sel(time=times)
    array = np.asarray(selected.values, dtype=np.float32)
    expected_shape = (times.size, int(target.sizes["lat"]), int(target.sizes["lon"]))
    if array.shape != expected_shape:
        raise ValueError(
            f"Baseline NDVI shape={array.shape}, expected common model grid={expected_shape}"
        )
    return xr.Dataset(
        {
            PREDICTION_VARIABLE: xr.DataArray(
                array,
                coords={"time": times, "lat": target.lat, "lon": target.lon},
                dims=("time", "lat", "lon"),
            )
        }
    )


def official_persistence_prediction(target: xr.Dataset) -> xr.Dataset:
    """Replicate the public persistence baseline on the common 20-step grid.

    The official script samples exactly days 4,9,...,49, forward-fills each
    pixel over that ten-frame context, fills spatial gaps by nearest neighbour,
    clips NDVI, and uses 0.5 only where a value remains unavailable.
    """

    context = (
        target_ndvi(target)
        .where(official_clear_mask(target))
        .isel(time=slice(4, None, 5))
        .isel(time=slice(None, 10))
    )
    if int(context.sizes.get("time", 0)) != 10:
        raise ValueError("Official persistence requires ten five-daily context frames")
    last = (
        context.ffill(dim="time")
        .isel(time=-1)
        .interpolate_na(dim="lat", use_coordinate=False, method="nearest")
        .interpolate_na(dim="lon", use_coordinate=False, method="nearest")
        .clip(-1, 1)
        .fillna(0.5)
    )
    times = expected_prediction_times(target)
    values = np.broadcast_to(
        np.asarray(last.values, dtype=np.float32)[None, ...],
        (int(times.size), int(target.sizes["lat"]), int(target.sizes["lon"])),
    ).copy()
    repeated = xr.DataArray(
        values,
        coords={"time": times, "lat": target.lat, "lon": target.lon},
        dims=("time", "lat", "lon"),
    )
    return _prediction_dataset(
        repeated,
        target,
        prediction_grid=BASELINE_PREDICTION_GRIDS["persistence"],
    )


# Kept as a narrow compatibility alias for the existing unit tests and callers.
# Its semantics are the public GreenEarthNet persistence implementation above,
# not the older raw-EarthNet RGBN diagnostic baseline.
def persistence_ndvi(target: xr.Dataset) -> xr.Dataset:
    return official_persistence_prediction(target)


def _official_climatology_field(full_cube: xr.Dataset, target: xr.Dataset) -> xr.DataArray:
    """Reproduce the public leave-target-year-out pixelwise NDVI climatology."""

    if "time" not in full_cube.coords or "time" not in target.coords:
        raise ValueError("Official climatology requires decoded time coordinates")
    target_year = int(target.isel(time=0).time.dt.year.item())
    masked = target_ndvi(full_cube).where(official_clear_mask(full_cube))
    retained = masked.where(full_cube["time.year"] != target_year, drop=True)
    if int(retained.sizes.get("time", 0)) == 0:
        raise ValueError("Full climatology cube has no observations outside the target year")
    climatology = (
        retained.interpolate_na("time", method="linear")
        .groupby("time.dayofyear")
        .mean()
        .pad(dayofyear=30, mode="wrap")
        .rolling(dayofyear=30, min_periods=1)
        .mean()
        .isel(dayofyear=slice(30, -30))
    )
    return climatology.sel(dayofyear=target.time.dt.dayofyear, method="nearest")


def official_climatology_prediction(full_cube: xr.Dataset, target: xr.Dataset) -> xr.Dataset:
    """Exact public pixelwise climatology on its daily day-50-plus grid."""

    daily = _official_climatology_field(full_cube, target)
    daily = xr.DataArray(
        daily.values,
        coords={"time": target.time, "lat": target.lat, "lon": target.lon},
        dims=("time", "lat", "lon"),
    )
    return _prediction_dataset(
        daily,
        target,
        prediction_grid=BASELINE_PREDICTION_GRIDS["climatology"],
    )


def _atomic_write_netcdf(path: Path, cube: xr.Dataset) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{os.getpid()}.tmp.nc")
    try:
        cube.to_netcdf(temporary, encoding={PREDICTION_VARIABLE: {"dtype": "float32"}})
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _full_cube_path(root: Path, target_path: Path) -> Path:
    candidate = root / target_path.name
    if not candidate.is_file():
        raise FileNotFoundError(
            "Official climatology requires the matching full minicube at "
            f"<full-cube-root>/<cubename>.nc; missing {candidate} for target {target_path}"
        )
    return candidate


def _full_cube_record(path: Path, *, root: Path, hash_mode: str) -> dict[str, Any]:
    from eval.stage2_evaluation_provenance import output_file_record

    return output_file_record(path, root=root, hash_mode=hash_mode)


def _identity(args: argparse.Namespace, source_manifest: Mapping[str, Any]) -> dict[str, Any]:
    full_root = (
        str(Path(args.full_cube_root).expanduser().resolve()) if args.full_cube_root else None
    )
    prediction_grid = BASELINE_PREDICTION_GRIDS[args.baseline]
    return {
        "kind": "greenearthnet_official_baseline_prediction",
        "baseline": args.baseline,
        "split": args.split,
        "manifest_protocol": args.manifest_protocol,
        "source_manifest": dict(source_manifest),
        "full_cube_root": full_root,
        "prediction_grid": prediction_grid,
        "prediction_grid_description": (
            "20 five-daily timestamps: raw indices 54,59,...,149"
            if prediction_grid == PREDICTION_GRID_FIVE_DAILY_20
            else "all target timestamps from raw positional index 50 onward"
        ),
        "official_reference": {
            "repository": OFFICIAL_REPOSITORY,
            "commit": OFFICIAL_EVALUATOR_COMMIT,
            "module": OFFICIAL_BASELINE_MODULES[args.baseline],
        },
    }


def main() -> int:
    args = parse_args()
    manifest_protocol_spec(args.manifest_protocol)
    if args.manifest_protocol != GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        raise ValueError(
            "This exporter is for the formal GreenEarthNet chopped protocol only; "
            "use eval/export_earthnet_table1_baseline.py for raw internal diagnostics."
        )
    if args.baseline == "climatology" and not args.full_cube_root:
        raise ValueError("--baseline climatology requires --full-cube-root")

    dataset_root = resolve_manifest_root(args.dataset_root, protocol=args.manifest_protocol)
    sources = load_manifest_files(
        args.manifest,
        dataset_root,
        expected_protocol=args.manifest_protocol,
        expected_split=args.split,
        verify_exists=True,
        verify_sizes=args.verify_manifest_sizes,
    )
    source_manifest = source_manifest_identity(args.manifest)
    output_root = Path(args.output_dir).expanduser().resolve()
    prediction_manifest = (
        Path(args.prediction_manifest).expanduser().resolve()
        if args.prediction_manifest
        else output_root / "prediction_manifest.json"
    )
    identity = _identity(args, source_manifest)
    validate_existing_output(
        output_root,
        prediction_manifest,
        expected_identity=identity,
        suffix=".nc",
        overwrite=args.overwrite,
    )

    full_root = Path(args.full_cube_root).expanduser().resolve() if args.full_cube_root else None
    expected: dict[str, str] = {}
    full_records: list[dict[str, Any]] = []
    written = 0
    for target_path in tqdm(sources, desc=f"official {args.baseline} {args.split}"):
        relative = greenearthnet_relative_path(target_path)
        if relative in expected:
            raise ValueError(f"Duplicate baseline output path: {relative}")
        expected[relative] = target_path.stem
        output_path = output_root / relative
        if output_path.is_file() and not args.overwrite:
            continue
        with xr.open_dataset(target_path, decode_times=True, cache=False) as target:
            if args.baseline == "persistence":
                prediction = official_persistence_prediction(target).load()
            else:
                assert full_root is not None
                full_path = _full_cube_path(full_root, target_path)
                full_records.append(_full_cube_record(full_path, root=full_root, hash_mode=args.hash_mode))
                with xr.open_dataset(full_path, decode_times=True, cache=False) as full_cube:
                    prediction = official_climatology_prediction(full_cube, target).load()
        _atomic_write_netcdf(output_path, prediction)
        written += 1

    if args.baseline == "climatology":
        assert full_root is not None
        # Recheck/record every source even if outputs were reused, so the output
        # provenance remains complete and a missing full cube cannot hide behind
        # an old prediction directory.
        full_records = [
            _full_cube_record(_full_cube_path(full_root, target), root=full_root, hash_mode=args.hash_mode)
            for target in sources
        ]
    records = collect_output_records(
        output_root,
        expected,
        suffix=".nc",
        hash_mode=args.hash_mode,
    )
    payload = {
        "schema_version": TABLE1_SCHEMA_VERSION,
        "kind": "greenearthnet_official_baseline_prediction_manifest",
        "format": "greenearthnet_ndvi_netcdf",
        "output_dir": str(output_root),
        "split": args.split,
        "manifest_protocol": args.manifest_protocol,
        "source_manifest": source_manifest,
        "baseline": args.baseline,
        "prediction_grid": BASELINE_PREDICTION_GRIDS[args.baseline],
        "prediction_steps_policy": (
            "fixed_20_five_daily"
            if args.baseline == "persistence"
            else "target_time_from_positional_index_50"
        ),
        "hash_mode": args.hash_mode,
        "num_predictions": len(records),
        "files": records,
        "files_sha256": prediction_records_digest(records),
        "identity": identity,
        "baseline_reference": identity["official_reference"],
        "full_cube_records": full_records,
        "full_cube_records_sha256": prediction_records_digest(full_records) if full_records else None,
        "written": written,
    }
    write_json_atomic(payload, prediction_manifest)
    print(f"predictions={output_root}")
    print(f"num_cubes={len(records)}")
    print(f"prediction_manifest={prediction_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
