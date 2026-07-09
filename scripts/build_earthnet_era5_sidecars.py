#!/usr/bin/env python
"""Build per-cube EarthNet D sidecars from gridded ERA5-Land files.

The script supports standard ERA5-Land hourly files, where precipitation and
solar radiation are cumulative from 00 UTC, and de-accumulated time-series
files, where hourly values must be summed. Temperature and dewpoint are used
to derive hourly VPD before daily averaging.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import (
    EarthNet2021Config,
    _canonical_cubename,
    _discover_npz_files,
    _parse_start_date,
)


VARIABLE_ALIASES = {
    "temperature": ("t2m", "2t", "2m_temperature", "temperature_2m", "tg"),
    "dewpoint": (
        "d2m",
        "2d",
        "2m_dewpoint_temperature",
        "dewpoint_temperature_2m",
        "dew",
    ),
    "precipitation": ("tp", "total_precipitation", "rr"),
    "solar_radiation": (
        "ssrd",
        "surface_solar_radiation_downwards",
        "surface_solar_radiation",
        "qq",
    ),
}
COORDINATE_ALIASES = {
    "time": ("time", "valid_time", "date"),
    "latitude": ("latitude", "lat", "y"),
    "longitude": ("longitude", "lon", "x"),
}


def vapor_pressure_deficit_kpa(
    temperature_c: np.ndarray,
    dewpoint_c: np.ndarray,
) -> np.ndarray:
    """Derive VPD from air temperature and dewpoint using Tetens' equation."""

    temperature_c = np.asarray(temperature_c, dtype=np.float64)
    dewpoint_c = np.asarray(dewpoint_c, dtype=np.float64)
    saturation = 0.6108 * np.exp(
        17.27 * temperature_c / (temperature_c + 237.3)
    )
    actual = 0.6108 * np.exp(
        17.27 * dewpoint_c / (dewpoint_c + 237.3)
    )
    return np.maximum(saturation - actual, 0.0).astype(np.float32)


def _temperature_to_celsius(values: np.ndarray, units: str) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    normalized_units = units.lower().replace(" ", "")
    finite = values[np.isfinite(values)]
    looks_kelvin = (
        normalized_units in {"k", "kelvin", "degrees_k"}
        or "kelvin" in normalized_units
        or (finite.size > 0 and float(np.nanmedian(finite)) > 150.0)
    )
    return (values - 273.15 if looks_kelvin else values).astype(np.float32)


def _precipitation_to_mm(values: np.ndarray, units: str) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    normalized_units = units.lower().replace(" ", "")
    is_meter = normalized_units in {
        "m",
        "meter",
        "metre",
        "mofwaterequivalent",
    } or normalized_units.startswith("mofwater")
    is_millimeter = (
        normalized_units in {"mm", "millimeter", "millimetre", "kgm-2"}
        or normalized_units.startswith("mm")
    )
    if not is_meter and not is_millimeter:
        raise ValueError(
            f"Unsupported precipitation units {units!r}; expected m or mm"
        )
    return (values * 1000.0 if is_meter else values).astype(np.float32)


def _radiation_to_mj(values: np.ndarray, units: str) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    normalized_units = units.lower().replace(" ", "")
    is_joule = (
        normalized_units.startswith("j")
        or "joule" in normalized_units
        or "jm" in normalized_units
    )
    is_megajoule = normalized_units.startswith("mj") or "megajoule" in normalized_units
    if not is_joule and not is_megajoule:
        raise ValueError(
            f"Unsupported solar-radiation units {units!r}; expected J/m2 or MJ/m2"
        )
    return (values / 1e6 if is_joule else values).astype(np.float32)


def _find_name(container: Iterable[str], aliases: Sequence[str], kind: str) -> str:
    lookup = {str(name).lower(): str(name) for name in container}
    for alias in aliases:
        if alias.lower() in lookup:
            return lookup[alias.lower()]
    raise KeyError(f"Could not find {kind}; tried aliases={list(aliases)}")


def _resolve_variable(dataset, requested: Optional[str], canonical: str) -> str:
    if requested:
        if requested not in dataset.data_vars:
            raise KeyError(
                f"Requested {canonical} variable {requested!r} is absent; "
                f"available={list(dataset.data_vars)}"
            )
        return requested
    return _find_name(dataset.data_vars, VARIABLE_ALIASES[canonical], canonical)


def _resolve_coordinate(dataset, requested: Optional[str], canonical: str) -> str:
    if requested:
        if requested not in dataset.coords and requested not in dataset.dims:
            raise KeyError(
                f"Requested {canonical} coordinate {requested!r} is absent"
            )
        return requested
    names = list(dataset.coords) + list(dataset.dims)
    return _find_name(names, COORDINATE_ALIASES[canonical], canonical)


def _open_era5(paths: Sequence[str]):
    try:
        import xarray as xr
    except ImportError as exc:
        raise ImportError(
            "ERA5 sidecar construction requires xarray and netCDF4. "
            "Install the project requirements first."
        ) from exc

    expanded: List[Path] = []
    for item in paths:
        path = Path(item)
        if any(char in item for char in "*?[]"):
            expanded.extend(sorted(path.parent.glob(path.name)))
        elif path.is_dir():
            expanded.extend(sorted(path.glob("*.nc")))
            expanded.extend(sorted(path.glob("*.grib")))
            expanded.extend(sorted(path.glob("*.grib2")))
        elif path.exists():
            expanded.append(path)
    expanded = sorted(dict.fromkeys(p.resolve() for p in expanded))
    if not expanded:
        raise FileNotFoundError(f"No ERA5 files matched: {list(paths)}")

    if len(expanded) == 1:
        dataset = xr.open_dataset(expanded[0])
    else:
        dataset = xr.open_mfdataset(
            [str(path) for path in expanded],
            combine="by_coords",
            parallel=False,
        )
    return dataset, expanded


def _cube_center(cubename: str) -> Tuple[float, float]:
    try:
        import earthnet as en
    except ImportError as exc:
        raise ImportError(
            "Coordinate lookup requires earthnet==0.3.9"
        ) from exc
    bounds = en.get_coords_from_cube(cubename, ignore_warning=True)
    lon_min, lat_min, lon_max, lat_max = [float(value) for value in bounds[:4]]
    return 0.5 * (lat_min + lat_max), 0.5 * (lon_min + lon_max)


def _normalize_longitude(longitude: float, coordinate_values: np.ndarray) -> float:
    finite = np.asarray(coordinate_values)[np.isfinite(coordinate_values)]
    if finite.size and float(np.nanmin(finite)) >= 0.0 and longitude < 0.0:
        return longitude % 360.0
    return longitude


def _point_variables(
    dataset,
    variables: Dict[str, str],
    latitude_name: str,
    longitude_name: str,
    time_name: str,
    latitude: float,
    longitude: float,
    start_date: date,
    num_days: int,
) -> Tuple[Dict[str, Tuple[np.ndarray, np.ndarray, str]], float, float]:
    longitude = _normalize_longitude(
        longitude,
        np.asarray(dataset[longitude_name].values),
    )
    point = dataset[list(variables.values())].sel(
        {
            latitude_name: latitude,
            longitude_name: longitude,
        },
        method="nearest",
    )
    end_date = start_date + timedelta(days=num_days)
    point = point.sel(
        {time_name: slice(np.datetime64(start_date), np.datetime64(end_date))}
    ).load()
    selected_lat = float(point[latitude_name].values)
    selected_lon = float(point[longitude_name].values)

    extracted = {}
    for canonical, variable in variables.items():
        data = point[variable]
        extra_dims = [dim for dim in data.dims if dim != time_name]
        for dim in extra_dims:
            if data.sizes[dim] != 1:
                raise ValueError(
                    f"{variable} retains unsupported dimension "
                    f"{dim}={data.sizes[dim]}"
                )
            data = data.isel({dim: 0})
        times = np.asarray(data[time_name].values).astype("datetime64[ns]")
        values = np.asarray(data.values, dtype=np.float64).reshape(-1)
        if times.shape[0] != values.shape[0]:
            raise ValueError(
                f"{variable} time/value length mismatch: "
                f"{times.shape} vs {values.shape}"
            )
        extracted[canonical] = (
            times,
            values,
            str(data.attrs.get("units", "")),
        )
    return extracted, selected_lat, selected_lon


def _daily_mean(
    times: np.ndarray,
    values: np.ndarray,
    start_date: date,
    num_days: int,
) -> np.ndarray:
    day_index = times.astype("datetime64[D]")
    out = np.full(num_days, np.nan, dtype=np.float32)
    for offset in range(num_days):
        day = np.datetime64(start_date + timedelta(days=offset))
        selected = values[day_index == day]
        if selected.size:
            out[offset] = float(np.nanmean(selected))
    return out


def _daily_accumulation(
    times: np.ndarray,
    values: np.ndarray,
    start_date: date,
    num_days: int,
    mode: str,
) -> np.ndarray:
    out = np.full(num_days, np.nan, dtype=np.float32)
    if mode == "cumulative":
        hours = (times.astype("datetime64[h]") - times.astype("datetime64[D]")).astype(int)
        midnight_times = times[hours == 0]
        midnight_values = values[hours == 0]
        represented_days = midnight_times.astype("datetime64[D]") - np.timedelta64(1, "D")
        for offset in range(num_days):
            day = np.datetime64(start_date + timedelta(days=offset))
            selected = midnight_values[represented_days == day]
            if selected.size:
                out[offset] = float(selected[-1])
        return out
    if mode == "incremental":
        represented_days = (
            times.astype("datetime64[ns]") - np.timedelta64(1, "ns")
        ).astype("datetime64[D]")
        for offset in range(num_days):
            day = np.datetime64(start_date + timedelta(days=offset))
            selected = values[represented_days == day]
            if selected.size:
                out[offset] = float(np.nansum(selected))
        return out
    raise ValueError(f"Unknown accumulation mode: {mode}")


def _validate_daily(name: str, values: np.ndarray, num_days: int) -> None:
    if values.shape != (num_days,):
        raise ValueError(f"{name} has shape={values.shape}, expected {(num_days,)}")
    if not np.isfinite(values).all():
        missing = int((~np.isfinite(values)).sum())
        raise ValueError(f"{name} is missing {missing}/{num_days} daily values")


def _build_one_sidecar(
    dataset,
    cube_path: Path,
    output_root: Path,
    names: Dict[str, str],
    coords: Dict[str, str],
    num_days: int,
    accumulation_mode: str,
    include_precip_temp: bool,
    overwrite: bool,
) -> dict:
    cubename = _canonical_cubename(cube_path.name)
    output = output_root / f"{cubename}.npz"
    if output.exists() and not overwrite:
        return {"status": "skipped", "output": str(output)}
    start_date = _parse_start_date(cubename)
    if start_date is None:
        raise ValueError(f"Cannot parse start date from {cubename}")
    latitude, longitude = _cube_center(cubename)

    extracted, grid_lat, grid_lon = _point_variables(
        dataset,
        names,
        coords["latitude"],
        coords["longitude"],
        coords["time"],
        latitude,
        longitude,
        start_date,
        num_days,
    )
    metadata = {}
    for canonical, variable in names.items():
        _, _, units = extracted[canonical]
        metadata[canonical] = {
            "variable": variable,
            "units": units,
            "grid_latitude": grid_lat,
            "grid_longitude": grid_lon,
        }

    t_times, t_values, t_units = extracted["temperature"]
    d_times, d_values, d_units = extracted["dewpoint"]
    if not np.array_equal(t_times, d_times):
        raise ValueError("temperature and dewpoint timestamps are not aligned")
    temperature_c = _temperature_to_celsius(t_values, t_units)
    dewpoint_c = _temperature_to_celsius(d_values, d_units)
    daily_vpd = _daily_mean(
        t_times,
        vapor_pressure_deficit_kpa(temperature_c, dewpoint_c),
        start_date,
        num_days,
    )
    _validate_daily("vpd", daily_vpd, num_days)

    s_times, s_values, s_units = extracted["solar_radiation"]
    daily_srad = _daily_accumulation(
        s_times,
        _radiation_to_mj(s_values, s_units),
        start_date,
        num_days,
        accumulation_mode,
    )
    _validate_daily("solar_radiation", daily_srad, num_days)

    arrays = {
        "vpd": daily_vpd.astype(np.float32),
        "solar_radiation": daily_srad.astype(np.float32),
        "start_date": np.asarray(start_date.isoformat()),
        "source_center_latitude": np.float32(latitude),
        "source_center_longitude": np.float32(longitude),
        "metadata_json": np.asarray(json.dumps(metadata, ensure_ascii=False)),
    }
    if include_precip_temp:
        p_times, p_values, p_units = extracted["precipitation"]
        daily_precip = _daily_accumulation(
            p_times,
            _precipitation_to_mm(p_values, p_units),
            start_date,
            num_days,
            accumulation_mode,
        )
        daily_temp = _daily_mean(
            t_times,
            temperature_c,
            start_date,
            num_days,
        )
        _validate_daily("precipitation", daily_precip, num_days)
        _validate_daily("temperature", daily_temp, num_days)
        arrays["precipitation"] = daily_precip.astype(np.float32)
        arrays["temperature"] = daily_temp.astype(np.float32)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".npz.tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    temporary.replace(output)
    return {"status": "written", "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/train/stage2_earthnet_main.yaml")
    parser.add_argument("--data-root", required=True)
    parser.add_argument(
        "--era5",
        nargs="+",
        required=True,
        help="ERA5-Land NetCDF/GRIB files, directories, or glob patterns.",
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--split", default="train")
    parser.add_argument("--max-files", type=int)
    parser.add_argument(
        "--accumulation-mode",
        choices=["cumulative", "incremental"],
        required=True,
        help=(
            "Use cumulative for standard reanalysis-era5-land hourly files; "
            "use incremental for de-accumulated ERA5-Land time-series files."
        ),
    )
    parser.add_argument(
        "--include-era5-precip-temp",
        action="store_true",
        help="Also replace EarthNet E-OBS precipitation/temperature with ERA5.",
    )
    parser.add_argument("--temperature-variable")
    parser.add_argument("--dewpoint-variable")
    parser.add_argument("--precipitation-variable")
    parser.add_argument("--solar-variable")
    parser.add_argument("--time-coordinate")
    parser.add_argument("--latitude-coordinate")
    parser.add_argument("--longitude-coordinate")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["data"]["root"] = args.data_root
    config["data"]["split"] = args.split
    config["data"]["dgh_stats_path"] = None
    # Sidecars are reusable preprocessing artifacts, so construct them for the
    # complete raw split instead of only the train portion of a held-out split.
    config["data"]["use_train_holdout"] = False
    data_cfg = EarthNet2021Config.from_config(config["data"], split=args.split)
    files = _discover_npz_files(data_cfg)
    if args.max_files:
        files = files[: args.max_files]
    if not files:
        raise FileNotFoundError(
            f"No EarthNet cubes found under {args.data_root} for split={args.split}"
        )

    dataset, era5_files = _open_era5(args.era5)
    names = {
        "temperature": _resolve_variable(
            dataset, args.temperature_variable, "temperature"
        ),
        "dewpoint": _resolve_variable(dataset, args.dewpoint_variable, "dewpoint"),
        "solar_radiation": _resolve_variable(
            dataset, args.solar_variable, "solar_radiation"
        ),
    }
    if args.include_era5_precip_temp:
        names["precipitation"] = _resolve_variable(
            dataset, args.precipitation_variable, "precipitation"
        )
    coords = {
        "time": _resolve_coordinate(dataset, args.time_coordinate, "time"),
        "latitude": _resolve_coordinate(
            dataset, args.latitude_coordinate, "latitude"
        ),
        "longitude": _resolve_coordinate(
            dataset, args.longitude_coordinate, "longitude"
        ),
    }
    num_days = (
        data_cfg.context_frames + data_cfg.target_frames
    ) * data_cfg.frame_interval_days
    output_root = Path(args.output_root)
    written = 0
    skipped = 0
    failure_count = 0
    failures = []
    for index, path in enumerate(files, start=1):
        try:
            result = _build_one_sidecar(
                dataset=dataset,
                cube_path=path,
                output_root=output_root,
                names=names,
                coords=coords,
                num_days=num_days,
                accumulation_mode=args.accumulation_mode,
                include_precip_temp=args.include_era5_precip_temp,
                overwrite=args.overwrite,
            )
            written += int(result["status"] == "written")
            skipped += int(result["status"] == "skipped")
        except Exception as exc:
            failure_count += 1
            if len(failures) < 100:
                failures.append(
                    {
                        "cube": str(path),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
        if index % 100 == 0:
            print(
                f"ERA5 sidecars {index}/{len(files)} "
                f"written={written} failed={failure_count}",
                flush=True,
            )

    report = {
        "earthnet_files": len(files),
        "era5_files": [str(path) for path in era5_files],
        "variables": names,
        "coordinates": coords,
        "accumulation_mode": args.accumulation_mode,
        "num_days_per_cube": num_days,
        "written": written,
        "skipped": skipped,
        "failed": failure_count,
        "failure_examples": failures,
        "output_root": str(output_root.resolve()),
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(text + "\n", encoding="utf-8")
    if failure_count:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
