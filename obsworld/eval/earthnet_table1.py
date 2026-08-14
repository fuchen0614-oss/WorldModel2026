"""Shared, provenance-bound helpers for the raw EarthNet2021x Table 1 path.

This module intentionally keeps the two metric families separate:

* ``EarthNetScore`` consumes target/prediction NPZ files with RGBN plus a
  cloud-invalid channel.
* The repository's GreenEarthNet-style NDVI evaluator consumes raw NetCDF and
  NDVI prediction NetCDFs.

Both may be useful for the frozen Table 1, but the raw-NetCDF-to-EarthNetScore
adapter is not automatically equivalent to an independently released official
target tree.  Callers must record that parity status explicitly; this module
never upgrades it on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import xarray as xr

from data.earthnet_manifest import records_digest, write_json_atomic


RGBN_VARIABLES: tuple[str, ...] = ("s2_B02", "s2_B03", "s2_B04", "s2_B8A")
CONTEXT_STEPS = 10
TARGET_STEPS = 20
S2_OFFSET_DAYS = 4
S2_STRIDE_DAYS = 5
TABLE1_SCHEMA_VERSION = 1
_CUBENAME_DATE = re.compile(r"(?<!\d)(\d{4})[_-](\d{1,2})[_-](\d{1,2})(?!\d)")


@dataclass(frozen=True)
class RawCube:
    """One 30-token RGBN sequence under the frozen Stage2 temporal contract."""

    rgbn: np.ndarray  # [30, 4, H, W], reflectance in [0, 1]
    clear: np.ndarray  # [30, H, W], True iff input semantics marks a pixel clear
    dates: tuple[date, ...]  # one date per RGBN token

    def __post_init__(self) -> None:
        if self.rgbn.ndim != 4 or self.rgbn.shape[0] != CONTEXT_STEPS + TARGET_STEPS:
            raise ValueError(f"rgbn must be [30,4,H,W], got {self.rgbn.shape}")
        if self.rgbn.shape[1] != len(RGBN_VARIABLES):
            raise ValueError(f"rgbn must contain RGBN, got {self.rgbn.shape}")
        if self.clear.shape != (self.rgbn.shape[0], *self.rgbn.shape[-2:]):
            raise ValueError(
                "clear mask must match RGBN time/spatial axes, got "
                f"{self.clear.shape} for {self.rgbn.shape}"
            )
        if len(self.dates) != self.rgbn.shape[0]:
            raise ValueError("dates must contain exactly one value per sampled frame")

    @property
    def context_rgbn(self) -> np.ndarray:
        return self.rgbn[:CONTEXT_STEPS]

    @property
    def future_rgbn(self) -> np.ndarray:
        return self.rgbn[CONTEXT_STEPS:]

    @property
    def future_dates(self) -> tuple[date, ...]:
        return self.dates[CONTEXT_STEPS:]


@dataclass(frozen=True)
class DoyClimatology:
    """Training-only global RGBN climatology indexed by calendar day-of-year."""

    means: np.ndarray  # [366, 4]
    counts: np.ndarray  # [366, 4]
    global_means: np.ndarray  # [4]

    def __post_init__(self) -> None:
        if self.means.shape != (366, len(RGBN_VARIABLES)):
            raise ValueError(f"means must be [366,4], got {self.means.shape}")
        if self.counts.shape != self.means.shape:
            raise ValueError("counts must match means")
        if self.global_means.shape != (len(RGBN_VARIABLES),):
            raise ValueError("global_means must be RGBN-shaped")

    def predict(self, dates: Sequence[date], height: int, width: int) -> np.ndarray:
        if height <= 0 or width <= 0:
            raise ValueError("height/width must be positive")
        values = np.stack([self.means[_doy_index(value)] for value in dates], axis=0)
        return np.broadcast_to(
            values[:, :, None, None],
            (len(dates), len(RGBN_VARIABLES), height, width),
        ).astype(np.float32, copy=True)


def source_sample_indices(
    *,
    context_steps: int = CONTEXT_STEPS,
    target_steps: int = TARGET_STEPS,
    offset_days: int = S2_OFFSET_DAYS,
    stride_days: int = S2_STRIDE_DAYS,
) -> np.ndarray:
    """Return raw daily indices for the 10-context + 20-future Stage2 sequence."""

    if min(context_steps, target_steps, stride_days) <= 0 or offset_days < 0:
        raise ValueError("invalid raw EarthNet temporal contract")
    return offset_days + stride_days * np.arange(context_steps + target_steps, dtype=int)


def tile_for_sample_id(sample_id: str) -> str:
    """Map an official EarthNet cubename to its five-character tile directory."""

    value = str(sample_id)
    tile = value[:5]
    if not re.fullmatch(r"\d{2}[A-Z]{3}", tile):
        raise ValueError(f"Cannot derive an EarthNet tile from sample_id={sample_id!r}")
    return tile


def raw_cube_from_netcdf(path: str | Path) -> RawCube:
    """Read RGBN and clear masks using the exact Stage2-v2 raw semantics.

    The dataset loader samples raw indices 4,9,...,149, normalizes reflectance
    with the configured auto-scale=10000 rule, and treats ``s2_mask <= 0`` plus
    finite RGBN as clear.  The target adapter and deterministic baselines must
    use precisely that same input contract; otherwise an apparent Table 1 gain
    could come from a different cloud convention rather than the model.
    """

    source = Path(path)
    with xr.open_dataset(source, decode_times=True, cache=False) as cube:
        missing = [name for name in (*RGBN_VARIABLES, "s2_mask") if name not in cube]
        if missing:
            raise KeyError(f"{source}: missing required raw EarthNet variables {missing}")
        indices = source_sample_indices()
        if "time" not in cube.sizes or int(cube.sizes["time"]) <= int(indices[-1]):
            raise ValueError(
                f"{source}: raw time length={cube.sizes.get('time')} cannot supply "
                f"the frozen index {int(indices[-1])}"
            )
        raw_bands = np.stack(
            [_to_thw(cube[name], name)[indices] for name in RGBN_VARIABLES],
            axis=1,
        ).astype(np.float32, copy=False)
        raw_mask = _to_thw(cube["s2_mask"], "s2_mask")[indices]
        dates = _sample_dates(cube, source, indices)

    finite_rgbn = np.all(np.isfinite(raw_bands), axis=1)
    clear = np.isfinite(raw_mask) & (raw_mask <= 0) & finite_rgbn
    rgbn = _normalize_reflectance(raw_bands)
    return RawCube(rgbn=rgbn, clear=clear.astype(bool, copy=False), dates=dates)


def earthnet_target_highresdynamic(raw: RawCube) -> np.ndarray:
    """Build official-toolkit target layout ``[H,W,5,20]`` from raw NetCDF.

    The first four channels are B02/B03/B04/B8A in normalized RGBN order.  The
    fifth is the cloud/invalid indicator expected by ``EarthNetScore``: 1 means
    ignore that target pixel and 0 means score it.  Future values are retained
    under invalid pixels because the official scorer masks them before use.
    """

    invalid = (~raw.clear[CONTEXT_STEPS:]).astype(np.float32, copy=False)
    highres = np.concatenate(
        [raw.future_rgbn, invalid[:, None]],
        axis=1,
    )
    return np.transpose(highres, (2, 3, 1, 0)).astype(np.float32, copy=False)


def persistence_rgbn(raw: RawCube) -> np.ndarray:
    """Repeat the last *clear* context RGBN value per pixel for all 20 targets.

    This is deliberately stronger and less arbitrary than copying a single
    possibly-cloudy last frame.  It only reads the 10 allowed context frames.
    Pixels never observed in context receive 0 reflectance, matching the
    Stage2 input path's zero-unobserved convention; this explicit fallback is
    stored in baseline provenance.
    """

    _, channels, height, width = raw.context_rgbn.shape
    last = np.zeros((channels, height, width), dtype=np.float32)
    for step in range(CONTEXT_STEPS):
        visible = raw.clear[step]
        last[:, visible] = raw.context_rgbn[step, :, visible]
    return np.broadcast_to(last[None], (TARGET_STEPS, channels, height, width)).copy()


def fit_doy_climatology(paths: Iterable[str | Path]) -> DoyClimatology:
    """Fit a global RGBN day-of-year climatology from *training files only*.

    All valid sampled RGBN pixels in the supplied manifest contribute.  This
    has no IID/OOD target leakage provided callers pass the frozen role=train
    manifest.  A day with no observations falls back to the global training
    RGBN mean, which keeps every prediction finite and is recorded in the
    cache sidecar.
    """

    sums = np.zeros((366, len(RGBN_VARIABLES)), dtype=np.float64)
    counts = np.zeros_like(sums, dtype=np.int64)
    observed_any = False
    for value in paths:
        raw = raw_cube_from_netcdf(value)
        for step, frame_date in enumerate(raw.dates):
            index = _doy_index(frame_date)
            visible = raw.clear[step]
            if not np.any(visible):
                continue
            observed_any = True
            pixels = raw.rgbn[step, :, visible]
            sums[index] += pixels.sum(axis=1, dtype=np.float64)
            counts[index] += int(visible.sum())
    if not observed_any:
        raise ValueError("Training manifest contains no finite clear RGBN pixels")
    global_counts = counts.sum(axis=0)
    global_sums = sums.sum(axis=0)
    if np.any(global_counts <= 0):
        raise ValueError("At least one RGBN channel has no training observations")
    global_means = global_sums / global_counts
    means = np.divide(
        sums,
        counts,
        out=np.broadcast_to(global_means, sums.shape).copy(),
        where=counts > 0,
    )
    return DoyClimatology(
        means=means.astype(np.float32),
        counts=counts,
        global_means=global_means.astype(np.float32),
    )


def save_climatology_cache(
    path: str | Path,
    climatology: DoyClimatology,
    *,
    training_manifest: Mapping[str, Any],
    training_dataset_root: str | Path,
) -> Path:
    """Atomically save a training-only climatology plus immutable sidecar."""

    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.stem}.{os.getpid()}.tmp.npz")
    with temporary.open("wb") as handle:
        np.savez_compressed(
            handle,
            means=climatology.means,
            counts=climatology.counts,
            global_means=climatology.global_means,
        )
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output)
    cache_identity = file_identity(output, required=True)
    sidecar = {
        "schema_version": TABLE1_SCHEMA_VERSION,
        "kind": "earthnet_table1_doy_climatology",
        "cache": cache_identity,
        "training_manifest": dict(training_manifest),
        "training_dataset_root": str(Path(training_dataset_root).expanduser().resolve()),
        "temporal_contract": temporal_contract(),
        "rgbn_variables": list(RGBN_VARIABLES),
        "missing_day_fallback": "global_training_rgbn_mean",
        "days_with_direct_observations": int(np.any(climatology.counts > 0, axis=1).sum()),
    }
    write_json_atomic(sidecar, climatology_sidecar_path(output))
    return output


def load_climatology_cache(
    path: str | Path,
    *,
    expected_training_manifest: Mapping[str, Any],
    expected_training_dataset_root: str | Path,
) -> DoyClimatology:
    """Load only a cache proven to derive from the requested frozen train set."""

    source = Path(path).expanduser().resolve()
    sidecar_path = climatology_sidecar_path(source)
    if not source.is_file() or not sidecar_path.is_file():
        raise FileNotFoundError(
            "Climatology cache and sidecar are both required; use --fit-climatology "
            f"to create them: cache={source}, sidecar={sidecar_path}"
        )
    sidecar = load_json_object(sidecar_path)
    if sidecar.get("kind") != "earthnet_table1_doy_climatology":
        raise ValueError(f"Unexpected climatology sidecar kind: {sidecar.get('kind')!r}")
    if sidecar.get("training_manifest") != dict(expected_training_manifest):
        raise ValueError(
            "Climatology cache was fitted from a different training manifest; "
            "refusing test-time leakage or protocol mixing."
        )
    expected_root = str(Path(expected_training_dataset_root).expanduser().resolve())
    if sidecar.get("training_dataset_root") != expected_root:
        raise ValueError("Climatology cache uses a different training dataset root")
    expected_cache = sidecar.get("cache")
    current_cache = file_identity(source, required=True)
    if not isinstance(expected_cache, Mapping) or expected_cache.get("sha256") != current_cache["sha256"]:
        raise ValueError("Climatology cache content no longer matches its sidecar")
    with np.load(source) as payload:
        return DoyClimatology(
            means=np.asarray(payload["means"], dtype=np.float32),
            counts=np.asarray(payload["counts"], dtype=np.int64),
            global_means=np.asarray(payload["global_means"], dtype=np.float32),
        )


def climatology_sidecar_path(cache_path: str | Path) -> Path:
    path = Path(cache_path)
    return path.with_name(f"{path.stem}.json")


def target_relative_path(sample_id: str) -> str:
    return f"{tile_for_sample_id(sample_id)}/{sample_id}.npz"


def greenearthnet_relative_path(source_path: str | Path) -> str:
    path = Path(source_path)
    return f"{path.parent.name}/{path.name}"


def atomic_save_npz(path: str | Path, **arrays: np.ndarray) -> None:
    """Atomically persist one NPZ artifact with fsync before replacement."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.stem}.{os.getpid()}.tmp.npz")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output)


def atomic_write_netcdf(path: str | Path, dataset: xr.Dataset) -> None:
    """Write a prediction NetCDF atomically, never exposing a partial cube."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.stem}.{os.getpid()}.tmp.nc")
    dataset.to_netcdf(temporary, encoding={"ndvi_pred": {"dtype": "float32"}})
    os.replace(temporary, output)


def collect_output_records(
    output_root: str | Path,
    expected: Mapping[str, str],
    *,
    suffix: str,
    hash_mode: str,
) -> list[dict[str, Any]]:
    """Ensure one output tree contains exactly the frozen expected sample set."""

    root = Path(output_root).expanduser().resolve()
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob(f"*{suffix}")
        if path.is_file()
    }
    expected_paths = set(expected)
    missing = sorted(expected_paths - actual)
    extra = sorted(actual - expected_paths)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing[:5]}")
        if extra:
            details.append(f"extra={extra[:5]}")
        raise RuntimeError(
            "Output directory does not exactly match its frozen manifest "
            "(" + "; ".join(details) + ")"
        )
    records: list[dict[str, Any]] = []
    for relative in sorted(expected):
        record = output_file_record(root / relative, root=root, hash_mode=hash_mode)
        record["sample_id"] = expected[relative]
        records.append(record)
    return records


def validate_existing_output(
    output_root: str | Path,
    manifest_path: str | Path,
    *,
    expected_identity: Mapping[str, Any],
    suffix: str,
    overwrite: bool,
) -> None:
    """Reject reuse of a target/baseline directory from another frozen run."""

    root = Path(output_root).expanduser().resolve()
    manifest = Path(manifest_path).expanduser().resolve()
    existing = list(root.rglob(f"*{suffix}")) if root.is_dir() else []
    if not existing and not manifest.exists():
        return
    if overwrite:
        return
    if not manifest.is_file():
        raise FileExistsError(
            f"{root} contains existing {suffix} files but no manifest; use a fresh "
            "directory instead of mixing untracked Table 1 outputs."
        )
    payload = load_json_object(manifest)
    if payload.get("identity") != dict(expected_identity):
        raise ValueError(
            "Existing Table 1 output belongs to a different frozen input/baseline "
            "contract; use a separate directory."
        )
    files = payload.get("files")
    hash_mode = payload.get("hash_mode")
    if not isinstance(files, list) or hash_mode not in {"none", "sha256"}:
        raise ValueError("Existing Table 1 output manifest has no valid file contract")
    for record in files:
        if not isinstance(record, Mapping) or not isinstance(record.get("path"), str):
            raise ValueError("Existing Table 1 output manifest contains an invalid file record")
        observed = output_file_record(root / str(record["path"]), root=root, hash_mode=hash_mode)
        for key in ("size_bytes", "sha256"):
            if key in record and observed.get(key) != record[key]:
                raise ValueError(
                    f"Existing Table 1 output no longer matches its manifest: {record['path']}"
                )


def source_manifest_identity(path: str | Path) -> dict[str, Any]:
    """Minimal manifest identity without importing torch-heavy training code."""

    source = Path(path).expanduser().resolve()
    payload = load_json_object(source)
    files_sha256 = payload.get("files_sha256")
    if not isinstance(files_sha256, str) or not files_sha256:
        raise ValueError(f"Manifest has no files_sha256: {source}")
    return {
        "path": str(source),
        "sha256": sha256_file(source),
        "dataset": payload.get("dataset"),
        "protocol": payload.get("protocol"),
        "split": payload.get("split"),
        "role": payload.get("role"),
        "num_files": payload.get("num_files"),
        "files_sha256": files_sha256,
    }


def output_file_record(path: str | Path, *, root: str | Path, hash_mode: str) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    output_root = Path(root).expanduser().resolve()
    if hash_mode not in {"none", "sha256"}:
        raise ValueError(f"Unknown hash_mode={hash_mode!r}")
    if not source.is_file():
        raise FileNotFoundError(f"Missing output file: {source}")
    result: dict[str, Any] = {
        "path": source.relative_to(output_root).as_posix(),
        "size_bytes": int(source.stat().st_size),
    }
    if hash_mode == "sha256":
        result["sha256"] = sha256_file(source)
    return result


def file_identity(path: str | Path, *, required: bool = False) -> dict[str, Any] | None:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        if required:
            raise FileNotFoundError(source)
        return {"path": str(source), "exists": False}
    return {
        "path": str(source),
        "exists": True,
        "size_bytes": int(source.stat().st_size),
        "sha256": sha256_file(source),
    }


def load_json_object(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON object: {source}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object in {source}")
    return payload


def temporal_contract() -> dict[str, int]:
    return {
        "context_steps": CONTEXT_STEPS,
        "target_steps": TARGET_STEPS,
        "netcdf_s2_offset_days": S2_OFFSET_DAYS,
        "frame_interval_days": S2_STRIDE_DAYS,
    }


def sha256_file(path: str | Path, *, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _normalize_reflectance(values: np.ndarray) -> np.ndarray:
    output = np.asarray(values, dtype=np.float32).copy()
    finite = output[np.isfinite(output)]
    if finite.size and float(finite.max()) > 2.0:
        output /= 10000.0
    output = np.nan_to_num(output, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(output, 0.0, 1.0)


def _to_thw(array: xr.DataArray, name: str) -> np.ndarray:
    required = {"time", "lat", "lon"}
    if not required.issubset(set(array.dims)):
        raise ValueError(f"{name} must have time/lat/lon dimensions, got {array.dims}")
    ordered = array.transpose("time", "lat", "lon")
    return np.asarray(ordered.values)


def _sample_dates(cube: xr.Dataset, source: Path, indices: np.ndarray) -> tuple[date, ...]:
    if "time" in cube.coords:
        values = np.asarray(cube["time"].values)[indices]
        parsed: list[date] = []
        for value in values:
            candidate = _as_date(value)
            if candidate is None:
                parsed = []
                break
            parsed.append(candidate)
        if len(parsed) == len(indices):
            return tuple(parsed)
    start = _date_from_cubename(source.stem)
    if start is None:
        raise ValueError(
            f"{source}: cannot decode time coordinates or derive an ISO start date "
            "from the cubename for training-only climatology"
        )
    return tuple(start + timedelta(days=int(offset)) for offset in indices)


def _as_date(value: Any) -> date | None:
    if isinstance(value, np.datetime64):
        if np.isnat(value):
            return None
        text = np.datetime_as_string(value, unit="D")
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if all(hasattr(value, key) for key in ("year", "month", "day")):
        try:
            return date(int(value.year), int(value.month), int(value.day))
        except (TypeError, ValueError):
            return None
    return None


def _date_from_cubename(stem: str) -> date | None:
    match = _CUBENAME_DATE.search(stem)
    if not match:
        return None
    try:
        return date(*(int(value) for value in match.groups()))
    except ValueError:
        return None


def _doy_index(value: date) -> int:
    return int(value.timetuple().tm_yday) - 1
