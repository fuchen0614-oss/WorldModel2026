"""EarthNet2021 and EarthNet2021x dataset utilities for ObsWorld Stage 2.

Both the legacy ``.npz`` layout and the current EarthNet2021x ``.nc`` layout
are supported. Dataset-specific assumptions stay explicit so server-side
inspection can validate them before a long run.
"""

from __future__ import annotations

import math
import json
import hashlib
import re
from datetime import date, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

from data.earthnet_conditioning import (
    ConditioningStatsV2,
    EOBS_NETCDF_VARIABLES,
    EOBS_VARIABLES,
    aggregate_eobs_path,
    build_calendar_path,
    build_delta_t_path,
    is_known_stage2_protocol,
    is_stage2_v2_protocol,
    load_conditioning_stats_v2,
    normalize_cop_dem,
)
from data.earthnet_fields import BandSpec, DriverSpec
from data.earthnet_manifest import load_manifest_files


HIGHRES_KEYS = ("highresdynamic", "highres_dynamic", "dynamic", "s2", "images", "x", "data")
MESO_KEYS = ("mesodynamic", "meso_dynamic", "weather", "meteorology", "meteo")
STATIC_KEYS = ("highresstatic", "mesostatic", "static", "dem", "topography")
MASK_KEYS = ("highresmask", "dynamic_mask", "mask", "cloudmask", "cloud_mask")
DATE_KEYS = ("dates", "time", "times", "timestamps")


@dataclass
class EarthNet2021Config:
    root: str
    split: str = "train"
    split_subdirs: Dict[str, List[str]] = field(default_factory=lambda: {
        "train": ["train", "earthnet2021x/train", "iid/train", "earthnet2021/train"],
        "val": ["val", "valid", "validation", "iid/val"],
        "test": ["test", "iid_test_split/context"],
        "iid": ["iid", "earthnet2021x/iid", "iid_test_split/context", "iid_test/context"],
        "ood": ["ood", "earthnet2021x/ood", "ood_test_split/context", "ood_test/context"],
        "extreme": ["extreme", "earthnet2021x/extreme", "extreme_test_split/context", "extreme_test/context"],
        "seasonal": ["seasonal", "earthnet2021x/seasonal", "seasonal_test_split/context", "seasonal_test/context"],
    })
    data_format: str = "auto"
    # ``legacy_direct9`` is intentionally the default so existing Direct-DGH
    # jobs remain byte-for-byte compatible. Formal world-model development
    # explicitly chooses ``earthnet2021x_path_v2``.
    stage2_protocol: str = "legacy_direct9"
    file_glob: str = "**/*.npz"
    context_frames: int = 10
    target_frames: int = 20
    frame_interval_days: int = 5
    model_img_size: int = 256
    eval_img_size: int = 128
    # The old path uses ``model_img_size`` everywhere.  V2 separates the
    # Stage1.5-compatible context size from native EarthNet target/DEM sizes.
    context_img_size: Optional[int] = None
    target_img_size: Optional[int] = None
    geo_img_size: Optional[int] = None
    image_channels: int = 4
    target_channels: int = 4
    cloud_mask_channel: int = 6
    cloud_mask_is_invalid: bool = True
    meso_steps_per_image: int = 5
    meso_crop_size: int = 2
    elevation_channel: int = 0
    elevation_scale: float = 2000.0
    netcdf_s2_offset_days: int = 4
    netcdf_dem_variables: List[str] = field(
        default_factory=lambda: ["nasa_dem", "alos_dem", "cop_dem"]
    )
    formal_dem_variable: str = "cop_dem"
    netcdf_solar_scale: float = 0.0864
    validation_fraction: float = 0.1
    validation_group: str = "tile"
    split_seed: int = 42
    use_train_holdout: bool = True
    manifest_path: Optional[str] = None
    require_manifest: bool = False
    verify_manifest_exists: bool = True
    verify_manifest_sizes: bool = False
    verify_manifest_hashes: bool = False
    driver_mean: Optional[List[float]] = None
    driver_std: Optional[List[float]] = None
    conditioning_stats_path: Optional[str] = None
    conditioning_stats: Optional[ConditioningStatsV2] = None
    require_conditioning_stats: bool = False
    external_driver_root: Optional[str] = None
    external_driver_required: bool = False
    disabled_driver_features: List[str] = field(default_factory=list)
    max_files: Optional[int] = None
    band_spec: BandSpec = field(default_factory=BandSpec)
    driver_spec: DriverSpec = field(default_factory=DriverSpec)
    normalize: bool = True
    strict: bool = False

    @classmethod
    def from_config(cls, config: dict, split: Optional[str] = None) -> "EarthNet2021Config":
        data_cfg = dict(config)
        requested_split = split or str(data_cfg.get("split", "train"))
        band_spec = BandSpec.from_config(data_cfg.get("band_spec"))
        driver_spec = DriverSpec.from_config(data_cfg.get("driver_spec"))
        stage2_protocol = str(data_cfg.get("stage2_protocol", "legacy_direct9")).lower()
        if not is_known_stage2_protocol(stage2_protocol):
            raise ValueError(
                "Unknown data.stage2_protocol="
                f"{stage2_protocol!r}; use legacy_direct9 or earthnet2021x_path_v2"
            )
        require_conditioning_stats = bool(
            data_cfg.get(
                "require_conditioning_stats",
                is_stage2_v2_protocol(stage2_protocol)
                and bool(data_cfg.get("strict", False)),
            )
        )
        if is_stage2_v2_protocol(stage2_protocol):
            if data_cfg.get("dgh_stats_path"):
                raise ValueError(
                    "earthnet2021x_path_v2 cannot use legacy dgh_stats_path; "
                    "provide conditioning_stats_path built from the frozen train manifest"
                )
            if data_cfg.get("disabled_driver_features"):
                raise ValueError(
                    "earthnet2021x_path_v2 does not support legacy disabled_driver_features; "
                    "use the explicit full24/core12 model choice in Commit B"
                )
            stats = {}
            conditioning_stats = load_conditioning_stats_v2(
                data_cfg.get("conditioning_stats_path"),
                require=require_conditioning_stats,
            )
        else:
            stats = _load_stats(
                data_cfg.get("dgh_stats_path"),
                expected_feature_names=driver_spec.feature_names,
            )
            conditioning_stats = None
        split_subdirs = data_cfg.get("split_subdirs")
        manifest_path = data_cfg.get("manifest_path")
        manifest_paths = data_cfg.get("manifest_paths") or {}
        if manifest_paths:
            if not isinstance(manifest_paths, dict):
                raise TypeError("data.manifest_paths must be a mapping from split to path")
            # An explicit null is meaningful: formal configs use it to say
            # that no role-specific manifest has been frozen yet.  In
            # particular, val must never fall back to the train manifest.
            if requested_split in manifest_paths:
                manifest_path = manifest_paths[requested_split]
        return cls(
            root=str(data_cfg["root"]),
            split=requested_split,
            split_subdirs=split_subdirs if split_subdirs is not None else cls.__dataclass_fields__["split_subdirs"].default_factory(),
            data_format=str(data_cfg.get("data_format", "auto")).lower(),
            stage2_protocol=stage2_protocol,
            file_glob=str(data_cfg.get("file_glob", "**/*.npz")),
            context_frames=int(data_cfg.get("context_frames", 10)),
            target_frames=int(data_cfg.get("target_frames", 20)),
            frame_interval_days=int(data_cfg.get("frame_interval_days", 5)),
            model_img_size=int(data_cfg.get("model_img_size", 256)),
            eval_img_size=int(data_cfg.get("eval_img_size", 128)),
            context_img_size=(
                int(data_cfg["context_img_size"])
                if data_cfg.get("context_img_size") is not None
                else None
            ),
            target_img_size=(
                int(data_cfg["target_img_size"])
                if data_cfg.get("target_img_size") is not None
                else None
            ),
            geo_img_size=(
                int(data_cfg["geo_img_size"])
                if data_cfg.get("geo_img_size") is not None
                else None
            ),
            image_channels=int(data_cfg.get("image_channels", band_spec.in_channels)),
            target_channels=int(data_cfg.get("target_channels", band_spec.out_channels)),
            cloud_mask_channel=int(data_cfg.get("cloud_mask_channel", 6)),
            cloud_mask_is_invalid=bool(data_cfg.get("cloud_mask_is_invalid", True)),
            meso_steps_per_image=int(data_cfg.get("meso_steps_per_image", 5)),
            meso_crop_size=int(data_cfg.get("meso_crop_size", 2)),
            elevation_channel=int(data_cfg.get("elevation_channel", 0)),
            elevation_scale=float(data_cfg.get("elevation_scale", 2000.0)),
            netcdf_s2_offset_days=int(data_cfg.get("netcdf_s2_offset_days", 4)),
            netcdf_dem_variables=list(
                data_cfg.get(
                    "netcdf_dem_variables",
                    ["nasa_dem", "alos_dem", "cop_dem"],
                )
            ),
            formal_dem_variable=str(data_cfg.get("formal_dem_variable", "cop_dem")),
            netcdf_solar_scale=float(data_cfg.get("netcdf_solar_scale", 0.0864)),
            validation_fraction=float(data_cfg.get("validation_fraction", 0.1)),
            validation_group=str(data_cfg.get("validation_group", "tile")),
            split_seed=int(data_cfg.get("split_seed", 42)),
            use_train_holdout=bool(data_cfg.get("use_train_holdout", True)),
            manifest_path=str(manifest_path) if manifest_path else None,
            require_manifest=bool(data_cfg.get("require_manifest", False)),
            verify_manifest_exists=bool(data_cfg.get("verify_manifest_exists", True)),
            verify_manifest_sizes=bool(data_cfg.get("verify_manifest_sizes", False)),
            verify_manifest_hashes=bool(data_cfg.get("verify_manifest_hashes", False)),
            driver_mean=stats.get("driver_mean"),
            driver_std=stats.get("driver_std"),
            conditioning_stats_path=(
                str(data_cfg["conditioning_stats_path"])
                if data_cfg.get("conditioning_stats_path")
                else None
            ),
            conditioning_stats=conditioning_stats,
            require_conditioning_stats=require_conditioning_stats,
            external_driver_root=data_cfg.get("external_driver_root"),
            external_driver_required=bool(data_cfg.get("external_driver_required", False)),
            disabled_driver_features=list(data_cfg.get("disabled_driver_features", [])),
            max_files=data_cfg.get("max_files"),
            band_spec=band_spec,
            driver_spec=driver_spec,
            normalize=bool(data_cfg.get("normalize", True)),
            strict=bool(data_cfg.get("strict", False)),
        )


class EarthNet2021Dataset(Dataset):
    """Map-style EarthNet2021 loader returning Stage2-ready batches."""

    def __init__(self, config: EarthNet2021Config):
        self.config = config
        if not is_known_stage2_protocol(config.stage2_protocol):
            raise ValueError(
                "Unknown stage2_protocol="
                f"{config.stage2_protocol!r}; use legacy_direct9 or earthnet2021x_path_v2"
            )
        self.files = _discover_npz_files(config)
        if not self.files:
            raise FileNotFoundError(
                f"No EarthNet files matching {config.file_glob!r} found under "
                f"root={config.root!r}, split={config.split!r}. "
                "Run scripts/inspect_earthnet2021.py to verify the dataset layout."
            )
        if config.max_files is not None:
            self.files = self.files[: int(config.max_files)]

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, index: int) -> Dict[str, Any]:
        path = self.files[index]
        data_format = _infer_data_format(path, self.config.data_format)
        if data_format == "netcdf":
            sample = parse_earthnet_netcdf(path, self.config)
        else:
            if is_stage2_v2_protocol(self.config.stage2_protocol):
                raise ValueError(
                    "earthnet2021x_path_v2 is defined only for EarthNet2021x "
                    "NetCDF minicubes; use legacy_direct9 for .npz data."
                )
            with np.load(path, allow_pickle=True) as cube:
                arrays = {k: cube[k] for k in cube.files}
            external_drivers, external_channel_map = _load_external_drivers(path, self.config)
            sample = parse_earthnet_npz(
                arrays,
                self.config,
                sample_name=path.name,
                external_drivers=external_drivers,
                external_channel_map=external_channel_map,
            )
        sample["meta"] = {
            "path": str(path),
            "sample_id": _canonical_cubename(path.name),
            "split": self.config.split,
            "stage2_protocol": self.config.stage2_protocol,
        }
        if is_stage2_v2_protocol(self.config.stage2_protocol):
            stats = self.config.conditioning_stats or ConditioningStatsV2.identity()
            sample["meta"]["conditioning_stats_source"] = stats.source
            sample["meta"]["conditioning_manifest_sha256"] = stats.manifest_sha256
        return sample


def create_earthnet2021_loader(
    config: EarthNet2021Config,
    batch_size: int,
    num_workers: int = 4,
    shuffle: bool = True,
    drop_last: bool = True,
    sampler=None,
) -> DataLoader:
    dataset = EarthNet2021Dataset(config)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=(shuffle and sampler is None),
        sampler=sampler,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=drop_last,
        collate_fn=collate_earthnet2021,
    )


def parse_earthnet_npz(
    arrays: Dict[str, np.ndarray],
    config: EarthNet2021Config,
    sample_name: Optional[str] = None,
    external_drivers: Optional[np.ndarray] = None,
    external_channel_map: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    if is_stage2_v2_protocol(config.stage2_protocol):
        raise ValueError(
            "earthnet2021x_path_v2 requires NetCDF E-OBS fields and does not "
            "silently reinterpret legacy .npz mesodynamic arrays."
        )
    high = _select_required_array(arrays, HIGHRES_KEYS, ndim=4)
    high_tchw = _to_tchw(high, prefer_spatial=True).astype(np.float32)
    if high_tchw.shape[1] < config.image_channels:
        raise ValueError(
            f"High-res dynamic has only {high_tchw.shape[1]} channels, "
            f"but image_channels={config.image_channels}."
        )

    image = high_tchw[:, : config.image_channels]
    clear_mask = _extract_clear_mask(arrays, high_tchw, config)
    meso = _extract_meso_features(arrays, crop_size=config.meso_crop_size)
    start_date = _parse_start_date(sample_name)
    elevation, geo_mask = _extract_elevation(
        arrays,
        image_hw=image.shape[-2:],
        channel=config.elevation_channel,
        scale=config.elevation_scale,
    )
    return _format_stage2_sample(
        image=image,
        clear_mask=clear_mask,
        meso=meso,
        elevation=elevation,
        geo_mask=geo_mask,
        config=config,
        start_date=start_date,
        external_drivers=external_drivers,
        external_channel_map=external_channel_map,
    )


def parse_earthnet_netcdf(
    path: Path,
    config: EarthNet2021Config,
) -> Dict[str, Any]:
    """Parse one EarthNet2021x minicube into the shared Stage2 contract."""

    try:
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError(
            "EarthNet2021x .nc loading requires xarray and netCDF4."
        ) from exc

    s2_variables = ("s2_B02", "s2_B03", "s2_B04", "s2_B8A")
    weather_variables = ("eobs_rr", "eobs_tg", "eobs_hu", "eobs_qq")
    with xr.open_dataset(path, cache=False) as cube:
        if is_stage2_v2_protocol(config.stage2_protocol):
            return _parse_earthnet_netcdf_v2_cube(
                cube=cube,
                path=path,
                config=config,
                s2_variables=s2_variables,
            )
        missing = [
            name
            for name in (*s2_variables, "s2_mask", *weather_variables)
            if name not in cube.variables
        ]
        if missing:
            raise KeyError(f"{path}: missing EarthNet2021x variables {missing}")

        indices = slice(
            config.netcdf_s2_offset_days,
            None,
            config.frame_interval_days,
        )
        image = np.stack(
            [
                _xarray_to_thw(cube[name], name)[indices]
                for name in s2_variables
            ],
            axis=1,
        ).astype(np.float32)
        raw_mask = _xarray_to_thw(cube["s2_mask"], "s2_mask")[indices]
        clear_mask = (
            np.isfinite(raw_mask) & (raw_mask <= 0)
            & np.all(np.isfinite(image), axis=1)
        ).astype(np.float32)

        meso = _extract_netcdf_weather(cube, config)

        dem_name = next(
            (name for name in config.netcdf_dem_variables if name in cube.variables),
            None,
        )
        if dem_name is None:
            if config.strict:
                raise KeyError(
                    f"{path}: no DEM found; expected one of "
                    f"{config.netcdf_dem_variables}"
                )
            elevation = np.zeros((1, image.shape[-2], image.shape[-1]), dtype=np.float32)
            geo_mask = np.zeros_like(elevation)
        else:
            elevation_2d = _xarray_to_hw(cube[dem_name], dem_name)
            elevation = elevation_2d[None].astype(np.float32)
            geo_mask = np.isfinite(elevation).astype(np.float32)
            elevation = np.nan_to_num(elevation, nan=0.0)
            if config.elevation_scale > 0:
                elevation = elevation / float(config.elevation_scale)

        start_date = _xarray_start_date(cube) or _parse_start_date(path.name)

    netcdf_driver_spec = _earthnet2021x_driver_spec(config)
    return _format_stage2_sample(
        image=image,
        clear_mask=clear_mask,
        meso=meso,
        elevation=elevation,
        geo_mask=geo_mask,
        config=config,
        start_date=start_date,
        driver_spec=netcdf_driver_spec,
        driver_time_offset_days=config.netcdf_s2_offset_days,
    )


def _parse_earthnet_netcdf_v2_cube(
    cube: Any,
    path: Path,
    config: EarthNet2021Config,
    s2_variables: Sequence[str],
) -> Dict[str, Any]:
    """Parse one NetCDF cube under the frozen formal v2 protocol.

    This function is deliberately separate from the legacy NetCDF branch.
    Sharing the old four-field weather extraction or first-available DEM logic
    would make a v2 run look valid while violating its published data contract.
    """

    _validate_v2_temporal_config(config)
    if config.formal_dem_variable != "cop_dem":
        raise ValueError(
            "earthnet2021x_path_v2 freezes G to formal_dem_variable='cop_dem'; "
            f"got {config.formal_dem_variable!r}"
        )
    required = (*s2_variables, "s2_mask", *EOBS_NETCDF_VARIABLES, "cop_dem")
    missing = [name for name in required if name not in cube.variables]
    if missing:
        raise KeyError(f"{path}: v2 protocol requires EarthNet2021x variables {missing}")

    indices = slice(
        config.netcdf_s2_offset_days,
        None,
        config.frame_interval_days,
    )
    image = np.stack(
        [_xarray_to_thw(cube[name], name)[indices] for name in s2_variables],
        axis=1,
    ).astype(np.float32)
    raw_mask = _xarray_to_thw(cube["s2_mask"], "s2_mask")[indices]
    clear_mask = (
        np.isfinite(raw_mask)
        & (raw_mask <= 0)
        & np.all(np.isfinite(image), axis=1)
    ).astype(np.float32)

    daily_raw = np.stack(
        [
            _xarray_to_time(cube[f"eobs_{variable}"], f"eobs_{variable}")
            for variable in EOBS_VARIABLES
        ],
        axis=1,
    ).astype(np.float32)
    stats = config.conditioning_stats or load_conditioning_stats_v2(
        config.conditioning_stats_path,
        require=(config.require_conditioning_stats or config.strict),
    )
    conditioning = aggregate_eobs_path(daily_raw, stats)

    raw_dem = _xarray_to_hw(cube["cop_dem"], "cop_dem")[None].astype(np.float32)
    elevation, geo_mask = normalize_cop_dem(raw_dem, stats)
    start_date = _xarray_start_date(cube) or _parse_start_date(path.name)
    if config.strict and start_date is None:
        raise ValueError(f"{path}: formal v2 requires a parseable first observation date")

    return _format_stage2_v2_sample(
        image=image,
        clear_mask=clear_mask,
        conditioning=conditioning,
        elevation=elevation,
        geo_mask=geo_mask,
        config=config,
        start_date=start_date,
    )


def _validate_v2_temporal_config(config: EarthNet2021Config) -> None:
    expected = {
        "context_frames": 10,
        "target_frames": 20,
        "frame_interval_days": 5,
        "netcdf_s2_offset_days": 4,
    }
    mismatches = [
        f"{name}={getattr(config, name)!r} (expected {value})"
        for name, value in expected.items()
        if getattr(config, name) != value
    ]
    if mismatches:
        raise ValueError(
            "earthnet2021x_path_v2 uses a frozen 150-day/30-token protocol; "
            + "; ".join(mismatches)
        )


def _format_stage2_v2_sample(
    image: np.ndarray,
    clear_mask: np.ndarray,
    conditioning: Any,
    elevation: np.ndarray,
    geo_mask: np.ndarray,
    config: EarthNet2021Config,
    start_date: Optional[date],
) -> Dict[str, Any]:
    """Format image/condition tensors whose different spatial sizes are valid."""

    if config.normalize:
        image = _normalize_reflectance(image, config.band_spec)
    total_steps = config.context_frames + config.target_frames
    original_frames = image.shape[0]
    if original_frames < total_steps:
        if config.strict:
            raise ValueError(
                f"Formal v2 needs {total_steps} S2 frames, found {original_frames}"
            )
        image = np.concatenate(
            [image, np.repeat(image[-1:], total_steps - original_frames, axis=0)],
            axis=0,
        )
        clear_mask = np.concatenate(
            [
                clear_mask,
                np.zeros(
                    (total_steps - original_frames, *clear_mask.shape[-2:]),
                    dtype=np.float32,
                ),
            ],
            axis=0,
        )
    elif original_frames > total_steps:
        image = image[:total_steps]
        clear_mask = clear_mask[:total_steps]

    x_context = image[: config.context_frames]
    x_target = image[
        config.context_frames:total_steps,
        : config.target_channels,
    ]
    context_mask = clear_mask[: config.context_frames].copy()
    target_mask = clear_mask[config.context_frames:total_steps].copy()
    if original_frames < config.context_frames:
        context_mask[original_frames:] = 0.0
    if original_frames < total_steps:
        target_mask[max(0, original_frames - config.context_frames):] = 0.0

    context_img_size = config.context_img_size or config.model_img_size
    target_img_size = config.target_img_size or config.eval_img_size
    geo_img_size = config.geo_img_size or config.eval_img_size
    if min(context_img_size, target_img_size, geo_img_size) <= 0:
        raise ValueError("Stage2-v2 image sizes must all be positive")

    h = (
        np.arange(1, config.target_frames + 1, dtype=np.float32)
        * float(config.frame_interval_days)
    )
    calendar_path = build_calendar_path(
        start_date,
        num_steps=total_steps,
        days_per_step=config.frame_interval_days,
    )
    delta_t_path = build_delta_t_path(
        num_steps=total_steps,
        days_per_step=config.frame_interval_days,
    )

    return {
        "x_context": _resize_tchw(
            torch.from_numpy(x_context), context_img_size, mode="bilinear"
        ).float(),
        "x_target": _resize_tchw(
            torch.from_numpy(x_target), target_img_size, mode="bilinear"
        ).float(),
        "context_mask": _resize_thw(
            torch.from_numpy(context_mask), context_img_size, mode="nearest"
        ).float(),
        "target_mask": _resize_thw(
            torch.from_numpy(target_mask), target_img_size, mode="nearest"
        ).float(),
        "D_path": torch.from_numpy(conditioning.values).float(),
        "D_mask": torch.from_numpy(conditioning.mask).float(),
        # This is an audit field, not a model input.  It enables preflight and
        # experiment provenance to distinguish partial from total loss of data.
        "D_valid_day_count": torch.from_numpy(conditioning.valid_day_count).long(),
        "C_path": torch.from_numpy(calendar_path).float(),
        "delta_t_path": torch.from_numpy(delta_t_path).float(),
        "G": _resize_chw(
            torch.from_numpy(elevation), geo_img_size, mode="bilinear"
        ).float(),
        "G_mask": _resize_chw(
            torch.from_numpy(geo_mask), geo_img_size, mode="nearest"
        ).float(),
        "h": torch.from_numpy(h).float(),
        "start_date": start_date.isoformat() if start_date is not None else None,
    }


def _format_stage2_sample(
    image: np.ndarray,
    clear_mask: np.ndarray,
    meso: Optional[np.ndarray],
    elevation: np.ndarray,
    geo_mask: np.ndarray,
    config: EarthNet2021Config,
    start_date: Optional[date],
    external_drivers: Optional[np.ndarray] = None,
    external_channel_map: Optional[Dict[str, int]] = None,
    driver_spec: Optional[DriverSpec] = None,
    driver_time_offset_days: int = 0,
) -> Dict[str, Any]:
    if config.normalize:
        image = _normalize_reflectance(image, config.band_spec)
    total_needed = config.context_frames + config.target_frames
    original_frames = image.shape[0]
    if original_frames < total_needed:
        if config.strict:
            raise ValueError(f"Need {total_needed} frames, found {original_frames}")
        image = np.concatenate(
            [image, np.repeat(image[-1:], total_needed - original_frames, axis=0)],
            axis=0,
        )
        clear_mask = np.concatenate(
            [
                clear_mask,
                np.zeros(
                    (total_needed - original_frames, *clear_mask.shape[-2:]),
                    dtype=np.float32,
                ),
            ],
            axis=0,
        )

    x_context = image[: config.context_frames]
    x_target = image[
        config.context_frames:total_needed,
        : config.target_channels,
    ]
    context_mask = clear_mask[: config.context_frames].copy()
    target_mask = clear_mask[config.context_frames:total_needed].copy()
    if original_frames < config.context_frames:
        context_mask[original_frames:] = 0.0
    if original_frames < total_needed:
        target_mask[max(0, original_frames - config.context_frames):] = 0.0

    active_driver_spec = driver_spec or config.driver_spec
    drivers, driver_mask = _build_driver_features(
        meso=meso,
        num_targets=config.target_frames,
        context_frames=config.context_frames,
        frame_interval_days=config.frame_interval_days,
        meso_steps_per_image=config.meso_steps_per_image,
        driver_spec=active_driver_spec,
        start_date=start_date,
        external_drivers=external_drivers,
        external_channel_map=external_channel_map,
        time_offset_days=driver_time_offset_days,
    )
    for feature_name in config.disabled_driver_features:
        if feature_name not in active_driver_spec.feature_names:
            raise ValueError(f"Unknown disabled D feature: {feature_name}")
        feature_index = active_driver_spec.feature_names.index(feature_name)
        drivers[:, feature_index] = 0.0
        driver_mask[:, feature_index] = 0.0
    drivers = _normalize_driver_features(
        drivers,
        driver_mask,
        config.driver_mean,
        config.driver_std,
    )
    h = (
        np.arange(1, config.target_frames + 1, dtype=np.float32)
        * float(config.frame_interval_days)
    )

    x_context_t = _resize_tchw(torch.from_numpy(x_context), config.model_img_size, mode="bilinear")
    x_target_t = _resize_tchw(torch.from_numpy(x_target), config.model_img_size, mode="bilinear")
    context_mask_t = _resize_thw(torch.from_numpy(context_mask), config.model_img_size, mode="nearest")
    target_mask_t = _resize_thw(torch.from_numpy(target_mask), config.model_img_size, mode="nearest")
    elevation_t = _resize_chw(torch.from_numpy(elevation), config.model_img_size, mode="bilinear")
    geo_mask_t = _resize_chw(torch.from_numpy(geo_mask), config.model_img_size, mode="nearest")

    return {
        "x_context": x_context_t.float(),
        "x_target": x_target_t.float(),
        "context_mask": context_mask_t.float(),
        "target_mask": target_mask_t.float(),
        "D": torch.from_numpy(drivers).float(),
        "D_mask": torch.from_numpy(driver_mask).float(),
        "G": elevation_t.float(),
        "G_mask": geo_mask_t.float(),
        "h": torch.from_numpy(h).float(),
        "start_date": start_date.isoformat() if start_date is not None else None,
    }


def collate_earthnet2021(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not batch:
        raise ValueError("Cannot collate an empty EarthNet batch")
    tensor_keys = [key for key, value in batch[0].items() if torch.is_tensor(value)]
    for index, sample in enumerate(batch[1:], start=1):
        actual = [key for key, value in sample.items() if torch.is_tensor(value)]
        if actual != tensor_keys:
            raise ValueError(
                "EarthNet batch mixes tensor contracts: "
                f"sample 0 keys={tensor_keys}, sample {index} keys={actual}"
            )
    out = {
        key: torch.stack([sample[key] for sample in batch], dim=0)
        for key in tensor_keys
    }
    out["meta"] = [sample.get("meta", {}) for sample in batch]
    out["start_date"] = [sample.get("start_date") for sample in batch]
    return out


def inspect_npz_file(path: Path) -> Dict[str, Any]:
    """Return JSON-friendly key/shape/dtype/range metadata for one minicube."""

    info: Dict[str, Any] = {"path": str(path), "keys": {}}
    with np.load(path, allow_pickle=True) as cube:
        for key in cube.files:
            arr = cube[key]
            item = {"shape": list(arr.shape), "dtype": str(arr.dtype)}
            if np.issubdtype(arr.dtype, np.number) and arr.size > 0:
                finite = np.asarray(arr[np.isfinite(arr)]) if np.issubdtype(arr.dtype, np.floating) else arr.reshape(-1)
                if finite.size:
                    item.update({
                        "min": float(np.nanmin(finite)),
                        "max": float(np.nanmax(finite)),
                        "mean": float(np.nanmean(finite)),
                    })
            info["keys"][key] = item
    return info


def inspect_netcdf_file(path: Path) -> Dict[str, Any]:
    try:
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError("NetCDF inspection requires xarray and netCDF4.") from exc
    info: Dict[str, Any] = {"path": str(path), "dimensions": {}, "variables": {}}
    with xr.open_dataset(path, cache=False) as cube:
        info["dimensions"] = {
            name: int(value) for name, value in cube.sizes.items()
        }
        for key in (
            "s2_B02",
            "s2_B03",
            "s2_B04",
            "s2_B8A",
            "s2_mask",
            "eobs_rr",
            "eobs_tg",
            "eobs_hu",
            "eobs_qq",
            "nasa_dem",
            "alos_dem",
            "cop_dem",
        ):
            if key not in cube.variables:
                continue
            array = cube[key]
            item: Dict[str, Any] = {
                "dims": list(array.dims),
                "shape": list(array.shape),
                "dtype": str(array.dtype),
                "units": array.attrs.get("units"),
            }
            values = np.asarray(array.values)
            finite = values[np.isfinite(values)]
            if finite.size:
                item.update(
                    {
                        "min": float(np.min(finite)),
                        "max": float(np.max(finite)),
                        "mean": float(np.mean(finite)),
                    }
                )
            info["variables"][key] = item
    return info


def inspect_earthnet_root(
    root: str,
    split: str = "train",
    max_files: int = 3,
    data_format: str = "auto",
    file_glob: Optional[str] = None,
) -> Dict[str, Any]:
    if file_glob is None:
        file_glob = "**/*.nc" if data_format in {"netcdf", "nc", "earthnet2021x"} else "**/*.npz"
    cfg = EarthNet2021Config(
        root=root,
        split=split,
        max_files=max_files,
        data_format=data_format,
        file_glob=file_glob,
    )
    files = _discover_npz_files(cfg)
    return {
        "root": root,
        "split": split,
        "data_format": data_format,
        "file_glob": file_glob,
        "num_files_found": len(files),
        "files": [
            inspect_netcdf_file(path)
            if _infer_data_format(path, data_format) == "netcdf"
            else inspect_npz_file(path)
            for path in files[:max_files]
        ],
    }


def _discover_npz_files(config: EarthNet2021Config) -> List[Path]:
    root = Path(config.root)
    using_manifest = bool(config.manifest_path)
    if using_manifest:
        files = load_manifest_files(
            config.manifest_path,
            root,
            expected_split=config.split,
            verify_exists=config.verify_manifest_exists,
            verify_sizes=config.verify_manifest_sizes,
            verify_hashes=config.verify_manifest_hashes,
        )
        candidates = []
    else:
        if config.require_manifest:
            raise ValueError(
                f"split={config.split!r} requires an explicit manifest; "
                "root fallback/glob discovery is disabled"
            )
        if (
            is_stage2_v2_protocol(config.stage2_protocol)
            and config.split not in config.split_subdirs
        ):
            raise ValueError(
                "earthnet2021x_path_v2 does not support split="
                f"{config.split!r}; use one of train/iid/ood/extreme/seasonal "
                "or role=val for the deterministic development holdout."
            )
        candidates = []
        for sub in config.split_subdirs.get(config.split, [config.split]):
            p = root / sub
            if p.exists():
                candidates.append(p)
        files = []
    using_train_holdout = using_manifest and config.split == "val"
    if (
        not using_manifest
        and not candidates
        and config.use_train_holdout
        and config.split in {"train", "val"}
    ):
        train_candidates = []
        for sub in config.split_subdirs.get("train", ["train"]):
            p = root / sub
            if p.exists():
                train_candidates.append(p)
        if train_candidates:
            candidates = train_candidates
            using_train_holdout = True
    if not using_manifest and not candidates and root.exists():
        if is_stage2_v2_protocol(config.stage2_protocol):
            raise FileNotFoundError(
                "earthnet2021x_path_v2 found no directory for "
                f"split={config.split!r} under {root}; refusing a root-level "
                "fallback that could mix train and test files."
            )
        candidates = [root]
    for base in candidates:
        files.extend(sorted(base.glob(config.file_glob)))
    # Keep deterministic order and remove duplicates from overlapping candidates.
    files = sorted(dict.fromkeys(files))
    apply_holdout = config.use_train_holdout and (
        config.split == "train" or using_train_holdout
    )
    if apply_holdout:
        group_by_path = {
            path: (
                _canonical_cubename(path.name)[:5]
                if config.validation_group == "tile"
                else path.name
            )
            for path in files
        }
        group_counts: Dict[str, int] = {}
        for group_name in group_by_path.values():
            group_counts[group_name] = group_counts.get(group_name, 0) + 1
        validation_groups = _choose_validation_groups(
            group_counts,
            validation_fraction=config.validation_fraction,
            seed=config.split_seed,
        )
        files = [
            path
            for path in files
            if (
                group_by_path[path] in validation_groups
                if config.split == "val"
                else group_by_path[path] not in validation_groups
            )
        ]
    return files


def _choose_validation_groups(
    group_counts: Dict[str, int],
    validation_fraction: float,
    seed: int,
) -> set[str]:
    """Choose whole groups while matching the requested sample fraction.

    A hash threshold over groups can badly miss the requested sample fraction
    when geographic tiles have very different cube counts. This deterministic
    subset-sum keeps train/validation tiles disjoint and selects the group
    combination closest to the target number of samples.
    """

    if not 0.0 <= validation_fraction <= 1.0:
        raise ValueError(
            f"validation_fraction must be in [0,1], got {validation_fraction}"
        )
    if not group_counts or validation_fraction <= 0.0:
        return set()
    if validation_fraction >= 1.0:
        return set(group_counts)
    if len(group_counts) > 512:
        threshold = int(validation_fraction * 10000)
        return {
            name
            for name in group_counts
            if _stable_bucket(name, seed) < threshold
        }

    total = sum(group_counts.values())
    target = int(round(total * validation_fraction))
    ordered_groups = sorted(
        group_counts,
        key=lambda name: (_stable_bucket(name, seed), name),
    )
    # sum -> (previous sum, group added). Snapshotting keys ensures each group
    # is used at most once.
    parents: Dict[int, Optional[Tuple[int, str]]] = {0: None}
    for group_name in ordered_groups:
        count = group_counts[group_name]
        for previous in sorted(list(parents), reverse=True):
            current = previous + count
            if current not in parents:
                parents[current] = (previous, group_name)

    candidates = [value for value in parents if 0 < value < total]
    if not candidates:
        return {ordered_groups[0]}
    best = min(
        candidates,
        key=lambda value: (
            abs(value - target),
            value > target,
            value,
        ),
    )
    selected = set()
    while best:
        parent = parents[best]
        if parent is None:
            break
        previous, group_name = parent
        selected.add(group_name)
        best = previous
    return selected


def _select_required_array(arrays: Dict[str, np.ndarray], keys: Sequence[str], ndim: Optional[int] = None) -> np.ndarray:
    lower = {k.lower(): k for k in arrays.keys()}
    for key in keys:
        actual = lower.get(key.lower())
        if actual is not None:
            arr = arrays[actual]
            if ndim is None or arr.ndim == ndim:
                return arr
    raise KeyError(
        f"Could not find any of keys={list(keys)} with ndim={ndim}; "
        f"available keys={list(arrays.keys())}"
    )


def _select_optional_array(arrays: Dict[str, np.ndarray], keys: Sequence[str], ndim: Optional[int] = None) -> Optional[np.ndarray]:
    try:
        return _select_required_array(arrays, keys, ndim=ndim)
    except KeyError:
        return None


def _to_tchw(arr: np.ndarray, prefer_spatial: bool = True) -> np.ndarray:
    """Convert common EarthNet 4D layouts to [T,C,H,W]."""

    if arr.ndim != 4:
        raise ValueError(f"Expected 4D array, got shape={arr.shape}")
    s = arr.shape

    # Already [T,C,H,W].
    if s[0] <= 200 and s[1] <= 32 and s[2] >= 32 and s[3] >= 32:
        return arr
    # [H,W,C,T].
    if s[0] >= 32 and s[1] >= 32 and s[2] <= 32 and s[3] <= 300:
        return np.transpose(arr, (3, 2, 0, 1))
    # [H,W,T,C].
    if s[0] >= 32 and s[1] >= 32 and s[2] <= 300 and s[3] <= 32:
        return np.transpose(arr, (2, 3, 0, 1))
    # [T,H,W,C].
    if s[0] <= 300 and s[1] >= 32 and s[2] >= 32 and s[3] <= 32:
        return np.transpose(arr, (0, 3, 1, 2))
    raise ValueError(f"Cannot infer [T,C,H,W] layout from shape={arr.shape}")


def _static_to_chw(arr: np.ndarray) -> np.ndarray:
    if arr.ndim == 2:
        return arr[None].astype(np.float32)
    if arr.ndim == 3:
        if arr.shape[0] <= 32:
            return arr.astype(np.float32)
        if arr.shape[-1] <= 32:
            return np.transpose(arr, (2, 0, 1)).astype(np.float32)
    raise ValueError(f"Cannot infer [C,H,W] static layout from shape={arr.shape}")


def _normalize_reflectance(image: np.ndarray, band_spec: BandSpec) -> np.ndarray:
    out = image.astype(np.float32)
    finite = out[np.isfinite(out)]
    if (
        band_spec.auto_scale
        and finite.size > 0
        and float(np.max(finite)) > 2.0
    ):
        out = out / float(band_spec.scale_factor)
    out = np.nan_to_num(
        out,
        nan=band_spec.reflectance_min,
        posinf=band_spec.reflectance_max,
        neginf=band_spec.reflectance_min,
    )
    return np.clip(out, band_spec.reflectance_min, band_spec.reflectance_max)


def _extract_clear_mask(arrays: Dict[str, np.ndarray], high_tchw: np.ndarray, config: EarthNet2021Config) -> np.ndarray:
    total_needed = config.context_frames + config.target_frames
    mask_arr = _select_optional_array(arrays, MASK_KEYS)
    if mask_arr is not None:
        if mask_arr.ndim == 4:
            mask_tchw = _to_tchw(mask_arr)
            mask = mask_tchw[:, 0]
        elif mask_arr.ndim == 3:
            mask = _to_thw(mask_arr)
        else:
            mask = None
        if mask is not None:
            if mask.shape[0] < total_needed:
                pad = np.repeat(mask[-1:], total_needed - mask.shape[0], axis=0)
                mask = np.concatenate([mask, pad], axis=0)
            return _mask_values_to_clear(
                mask[:total_needed],
                config.cloud_mask_is_invalid,
            )

    # Train cubes have seven channels and use index 6; official context-only
    # test cubes have five channels and place the cloud mask last (index 4).
    if high_tchw.shape[1] >= 5:
        mask_channel = (
            config.cloud_mask_channel
            if high_tchw.shape[1] > config.cloud_mask_channel
            else high_tchw.shape[1] - 1
        )
        mask = high_tchw[:, mask_channel]
        if mask.shape[0] < total_needed:
            pad = np.repeat(mask[-1:], total_needed - mask.shape[0], axis=0)
            mask = np.concatenate([mask, pad], axis=0)
        return _mask_values_to_clear(
            mask[:total_needed],
            config.cloud_mask_is_invalid,
        )

    h, w = high_tchw.shape[-2:]
    return np.ones((total_needed, h, w), dtype=np.float32)


def _mask_values_to_clear(
    mask: np.ndarray,
    mask_is_invalid: bool,
) -> np.ndarray:
    finite = np.isfinite(mask)
    if mask_is_invalid:
        clear = finite & (mask <= 0)
    else:
        clear = finite & (mask > 0)
    return clear.astype(np.float32)


def _to_thw(arr: np.ndarray) -> np.ndarray:
    if arr.ndim != 3:
        raise ValueError(f"Expected 3D array, got {arr.shape}")
    # [T,H,W]
    if arr.shape[0] <= 300 and arr.shape[1] >= 32 and arr.shape[2] >= 32:
        return arr
    # [H,W,T]
    if arr.shape[0] >= 32 and arr.shape[1] >= 32 and arr.shape[2] <= 300:
        return np.transpose(arr, (2, 0, 1))
    raise ValueError(f"Cannot infer [T,H,W] mask layout from shape={arr.shape}")


def _extract_meso_features(
    arrays: Dict[str, np.ndarray],
    crop_size: int = 2,
) -> Optional[np.ndarray]:
    meso = _select_optional_array(arrays, MESO_KEYS)
    if meso is None:
        return None
    if meso.ndim == 4:
        tchw = _to_tchw(meso, prefer_spatial=False)
        if crop_size > 0:
            h, w = tchw.shape[-2:]
            crop_h = min(crop_size, h)
            crop_w = min(crop_size, w)
            h0 = (h - crop_h) // 2
            w0 = (w - crop_w) // 2
            tchw = tchw[:, :, h0:h0 + crop_h, w0:w0 + crop_w]
        return np.nanmean(tchw, axis=(-2, -1)).astype(np.float32)  # [T,C]
    if meso.ndim == 3:
        chw = _static_to_chw(meso)
        return np.nanmean(chw, axis=(-2, -1))[None].astype(np.float32)
    if meso.ndim == 2:
        return meso.astype(np.float32)
    return None


def _build_driver_features(
    meso: Optional[np.ndarray],
    num_targets: int,
    context_frames: int,
    frame_interval_days: int,
    meso_steps_per_image: int,
    driver_spec: DriverSpec,
    start_date: Optional[date],
    external_drivers: Optional[np.ndarray] = None,
    external_channel_map: Optional[Dict[str, int]] = None,
    time_offset_days: int = 0,
) -> Tuple[np.ndarray, np.ndarray]:
    features = np.zeros((num_targets, driver_spec.dim), dtype=np.float32)
    mask = np.zeros_like(features, dtype=np.float32)

    for j in range(num_targets):
        values: Dict[str, float] = {}
        valid: Dict[str, float] = {}
        if start_date is not None:
            target_date = start_date + timedelta(
                days=time_offset_days + (context_frames + j) * frame_interval_days
            )
            target_doy = target_date.timetuple().tm_yday
            values["target_doy_sin"] = math.sin(2.0 * math.pi * target_doy / 365.25)
            values["target_doy_cos"] = math.cos(2.0 * math.pi * target_doy / 365.25)
            valid["target_doy_sin"] = valid["target_doy_cos"] = 1.0

        last_context_day = (
            time_offset_days + (context_frames - 1) * meso_steps_per_image
        )
        target_day = time_offset_days + (context_frames + j) * meso_steps_per_image
        interval = _meso_interval(meso, start=last_context_day + 1, end=target_day + 1)
        _add_weather_values(values, valid, interval, driver_spec.channel_map)
        external_interval = _meso_interval(
            external_drivers,
            start=last_context_day + 1,
            end=target_day + 1,
        )
        if external_interval is not None:
            _add_weather_values(
                values,
                valid,
                external_interval,
                external_channel_map or {},
            )

        for i, name in enumerate(driver_spec.feature_names):
            features[j, i] = float(values.get(name, 0.0))
            mask[j, i] = float(valid.get(name, 0.0))
    return features, mask


def _meso_interval(meso: Optional[np.ndarray], start: int, end: int) -> Optional[np.ndarray]:
    if meso is None or meso.size == 0:
        return None
    t = meso.shape[0]
    if start < 0 or end <= start or end > t:
        return None
    return meso[start:end]


def _add_weather_values(values: Dict[str, float], valid: Dict[str, float], interval: Optional[np.ndarray], channel_map: Dict[str, Optional[int]]) -> None:
    if interval is None:
        return

    def get_channel(name: str) -> Optional[np.ndarray]:
        idx = channel_map.get(name)
        if idx is None:
            return None
        if idx < 0 or idx >= interval.shape[1]:
            return None
        data = interval[:, idx].astype(np.float32)
        # A cumulative forcing window is valid only when every day is present.
        # Partial sums would silently make different horizons incomparable.
        if data.size == 0 or not np.isfinite(data).all():
            return None
        return data

    precip = get_channel("precipitation")
    if precip is not None:
        values["precip_sum"] = float(np.sum(precip))
        values["precip_mean"] = float(np.mean(precip))
        valid["precip_sum"] = valid["precip_mean"] = 1.0

    temp = get_channel("temperature")
    if temp is not None:
        values["temp_mean"] = float(np.mean(temp))
        valid["temp_mean"] = 1.0

    vpd = get_channel("vpd")
    if vpd is not None:
        values["vpd_mean"] = float(np.mean(vpd))
        values["vpd_max"] = float(np.max(vpd))
        valid["vpd_mean"] = valid["vpd_max"] = 1.0

    srad = get_channel("solar_radiation")
    if srad is not None:
        values["srad_sum"] = float(np.sum(srad))
        values["srad_mean"] = float(np.mean(srad))
        valid["srad_sum"] = valid["srad_mean"] = 1.0


def _normalize_driver_features(
    features: np.ndarray,
    mask: np.ndarray,
    mean: Optional[List[float]],
    std: Optional[List[float]],
) -> np.ndarray:
    if mean is None or std is None:
        return features
    mean_arr = np.asarray(mean, dtype=np.float32)
    std_arr = np.asarray(std, dtype=np.float32)
    if mean_arr.shape != (features.shape[-1],) or std_arr.shape != (features.shape[-1],):
        raise ValueError(
            f"DGH stats shape mismatch: expected {(features.shape[-1],)}, "
            f"got mean={mean_arr.shape}, std={std_arr.shape}"
        )
    normalized = (features - mean_arr[None]) / np.maximum(std_arr[None], 1e-6)
    return np.where(mask > 0, normalized, 0.0).astype(np.float32)


def _extract_elevation(
    arrays: Dict[str, np.ndarray],
    image_hw: Tuple[int, int],
    channel: int,
    scale: float,
) -> Tuple[np.ndarray, np.ndarray]:
    static = _select_optional_array(arrays, STATIC_KEYS)
    if static is None:
        h, w = image_hw
        return np.zeros((1, h, w), dtype=np.float32), np.zeros((1, h, w), dtype=np.float32)
    chw = _static_to_chw(static)
    if channel < 0 or channel >= chw.shape[0]:
        raise ValueError(f"elevation_channel={channel} outside static shape={chw.shape}")
    elev = chw[channel:channel + 1].astype(np.float32)
    mask = np.isfinite(elev).astype(np.float32)
    elev = np.nan_to_num(elev, nan=0.0)
    if scale > 0:
        elev = elev / float(scale)
    return elev, mask


def _resize_tchw(x: torch.Tensor, size: int, mode: str) -> torch.Tensor:
    if x.shape[-1] == size and x.shape[-2] == size:
        return x
    return F.interpolate(x, size=(size, size), mode=mode, align_corners=False if mode == "bilinear" else None)


def _resize_thw(x: torch.Tensor, size: int, mode: str) -> torch.Tensor:
    y = x.unsqueeze(1)
    if y.shape[-1] == size and y.shape[-2] == size:
        return x
    kwargs = {"align_corners": False} if mode == "bilinear" else {}
    return F.interpolate(y, size=(size, size), mode=mode, **kwargs).squeeze(1)


def _resize_chw(x: torch.Tensor, size: int, mode: str) -> torch.Tensor:
    y = x.unsqueeze(0)
    if y.shape[-1] == size and y.shape[-2] == size:
        return x
    kwargs = {"align_corners": False} if mode == "bilinear" else {}
    return F.interpolate(y, size=(size, size), mode=mode, **kwargs).squeeze(0)


def _parse_start_date(sample_name: Optional[str]) -> Optional[date]:
    if not sample_name:
        return None
    stem = Path(sample_name).stem
    iso_match = re.search(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", stem)
    if iso_match:
        try:
            return date(*(int(value) for value in iso_match.groups()))
        except ValueError:
            pass
    parts = stem.split("_")
    # Official cubename: tile_YYYY_MM_DD_YYYY_MM_DD_...
    for i in range(max(0, len(parts) - 2)):
        if (
            re.fullmatch(r"\d{4}", parts[i])
            and re.fullmatch(r"\d{1,2}", parts[i + 1])
            and re.fullmatch(r"\d{1,2}", parts[i + 2])
        ):
            try:
                return date(int(parts[i]), int(parts[i + 1]), int(parts[i + 2]))
            except ValueError:
                continue
    return None


def _load_stats(
    path: Optional[str],
    expected_feature_names: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    if not path:
        return {}
    stats_path = Path(path)
    if not stats_path.exists():
        raise FileNotFoundError(f"DGH stats file not found: {stats_path}")
    with stats_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if expected_feature_names is not None and data.get("feature_names") is not None:
        actual = list(data["feature_names"])
        expected = list(expected_feature_names)
        if actual != expected:
            raise ValueError(
                "DGH stats feature order does not match the configured D layout: "
                f"stats={actual}, config={expected}"
            )
    mean = data.get("driver_mean")
    std = data.get("driver_std")
    if (mean is None) != (std is None):
        raise ValueError(
            f"DGH stats {stats_path} must contain both driver_mean and driver_std"
        )
    if mean is not None:
        mean_arr = np.asarray(mean, dtype=np.float64)
        std_arr = np.asarray(std, dtype=np.float64)
        if not np.isfinite(mean_arr).all() or not np.isfinite(std_arr).all():
            raise ValueError(f"DGH stats {stats_path} contain non-finite values")
        if np.any(std_arr <= 0):
            raise ValueError(f"DGH stats {stats_path} contain non-positive std values")
    return {
        "driver_mean": mean,
        "driver_std": std,
    }


def _load_external_drivers(
    sample_path: Path,
    config: EarthNet2021Config,
) -> Tuple[Optional[np.ndarray], Optional[Dict[str, int]]]:
    """Load optional daily D sidecar data for one EarthNet cube.

    Supported ``.npz`` layouts:
    - ``drivers=[T,C]`` plus ``driver_names=[C]``;
    - named 1D arrays: precipitation, temperature, vpd, solar_radiation.

    Day zero must match the first date encoded in the EarthNet cube name.
    """

    if not config.external_driver_root:
        return None, None
    root = Path(config.external_driver_root)
    candidates = [
        root / sample_path.name,
        root / f"{sample_path.stem}.npz",
        root / f"{_canonical_cubename(sample_path.name)}.npz",
    ]
    sidecar = next((path for path in candidates if path.exists()), None)
    if sidecar is None:
        if config.external_driver_required:
            raise FileNotFoundError(
                f"External driver sidecar not found for {sample_path.name} under {root}"
            )
        return None, None

    with np.load(sidecar, allow_pickle=True) as data:
        if "drivers" in data.files:
            drivers = np.asarray(data["drivers"], dtype=np.float32)
            if drivers.ndim != 2:
                raise ValueError(
                    f"{sidecar}: drivers must be [T,C], got {drivers.shape}"
                )
            if "driver_names" not in data.files:
                raise KeyError(f"{sidecar}: drivers requires driver_names")
            names = [
                value.decode("utf-8") if isinstance(value, bytes) else str(value)
                for value in np.asarray(data["driver_names"]).tolist()
            ]
            if len(names) != drivers.shape[1]:
                raise ValueError(
                    f"{sidecar}: {len(names)} driver_names for {drivers.shape[1]} channels"
                )
            return drivers, {name: index for index, name in enumerate(names)}

        canonical = ("precipitation", "temperature", "vpd", "solar_radiation")
        available = [name for name in canonical if name in data.files]
        if not available:
            raise KeyError(
                f"{sidecar}: expected drivers/driver_names or named arrays {canonical}"
            )
        lengths = {np.asarray(data[name]).reshape(-1).shape[0] for name in available}
        if len(lengths) != 1:
            raise ValueError(f"{sidecar}: named driver arrays have unequal lengths")
        drivers = np.stack(
            [np.asarray(data[name], dtype=np.float32).reshape(-1) for name in available],
            axis=1,
        )
        return drivers, {name: index for index, name in enumerate(available)}


def _stable_bucket(name: str, seed: int) -> int:
    digest = hashlib.sha1(f"{seed}:{name}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 10000


def _canonical_cubename(filename: str) -> str:
    """Strip context/target/experiment prefixes from an EarthNet cubename."""

    parts = Path(filename).name.split("_")
    tile_pattern = re.compile(r"\d{2}[A-Z]{3}")
    for index, part in enumerate(parts):
        if tile_pattern.fullmatch(part):
            cubename = "_".join(parts[index:])
            for suffix in (".npz", ".nc"):
                if cubename.endswith(suffix):
                    return cubename[: -len(suffix)]
            return cubename
    return Path(filename).stem


def _infer_data_format(path: Path, configured: str) -> str:
    aliases = {
        "nc": "netcdf",
        "earthnet2021x": "netcdf",
        "npz": "npz",
        "earthnet2021": "npz",
    }
    if configured != "auto":
        resolved = aliases.get(configured, configured)
        if resolved not in {"netcdf", "npz"}:
            raise ValueError(
                f"Unsupported data_format={configured!r}; use auto, netcdf, or npz."
            )
        return resolved
    if path.suffix.lower() == ".nc":
        return "netcdf"
    if path.suffix.lower() == ".npz":
        return "npz"
    raise ValueError(f"Cannot infer EarthNet data format from {path}")


def _xarray_to_thw(array: Any, name: str) -> np.ndarray:
    required = {"time", "lat", "lon"}
    if not required.issubset(array.dims):
        raise ValueError(
            f"{name} must contain dimensions time/lat/lon, got {array.dims}"
        )
    return np.asarray(
        array.transpose("time", "lat", "lon").values,
        dtype=np.float32,
    )


def _xarray_to_time(array: Any, name: str) -> np.ndarray:
    if "time" not in array.dims:
        raise ValueError(f"{name} must contain a time dimension, got {array.dims}")
    other_dims = [dimension for dimension in array.dims if dimension != "time"]
    ordered = array.transpose("time", *other_dims)
    values = np.asarray(ordered.values, dtype=np.float32)
    if values.ndim > 1:
        values = np.nanmean(values, axis=tuple(range(1, values.ndim)))
    return values


def _xarray_to_hw(array: Any, name: str) -> np.ndarray:
    if not {"lat", "lon"}.issubset(array.dims):
        raise ValueError(f"{name} must contain lat/lon dimensions, got {array.dims}")
    selected = array
    for dimension in array.dims:
        if dimension not in {"lat", "lon"}:
            selected = selected.isel({dimension: 0})
    return np.asarray(selected.transpose("lat", "lon").values, dtype=np.float32)


def _extract_netcdf_weather(
    cube: Any,
    config: EarthNet2021Config,
) -> np.ndarray:
    precip = _xarray_to_time(cube["eobs_rr"], "eobs_rr")
    temperature = _temperature_to_celsius(
        _xarray_to_time(cube["eobs_tg"], "eobs_tg")
    )
    humidity = _relative_humidity_percent(
        _xarray_to_time(cube["eobs_hu"], "eobs_hu")
    )
    vpd = _vpd_from_temperature_humidity(temperature, humidity)
    # E-OBS qq is mean irradiance in W/m2. Convert it to daily MJ/m2 so
    # cumulative solar forcing has a physical unit before train-only z-score.
    solar = (
        _xarray_to_time(cube["eobs_qq"], "eobs_qq")
        * float(config.netcdf_solar_scale)
    )
    return np.stack(
        [precip, temperature, vpd, solar],
        axis=1,
    ).astype(np.float32)


def _earthnet2021x_driver_spec(config: EarthNet2021Config) -> DriverSpec:
    return DriverSpec(
        feature_names=list(config.driver_spec.feature_names),
        channel_map={
            "precipitation": 0,
            "temperature": 1,
            "vpd": 2,
            "solar_radiation": 3,
        },
    )


def _xarray_start_date(cube: Any) -> Optional[date]:
    if "time" not in cube.coords or cube.sizes.get("time", 0) == 0:
        return None
    value = cube["time"].values[0]
    try:
        converted = np.datetime64(value, "D").astype(object)
        if isinstance(converted, date):
            return converted
    except (TypeError, ValueError, OverflowError):
        pass
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(value))
    if match:
        try:
            return date(*(int(part) for part in match.groups()))
        except ValueError:
            return None
    return None


def _temperature_to_celsius(values: np.ndarray) -> np.ndarray:
    output = values.astype(np.float32)
    finite = output[np.isfinite(output)]
    if finite.size and float(np.nanmedian(finite)) > 100.0:
        output = output - 273.15
    return output


def _relative_humidity_percent(values: np.ndarray) -> np.ndarray:
    output = values.astype(np.float32)
    finite = output[np.isfinite(output)]
    if finite.size and float(np.nanmax(finite)) <= 1.5:
        output = output * 100.0
    return np.clip(output, 0.0, 100.0)


def _vpd_from_temperature_humidity(
    temperature_c: np.ndarray,
    relative_humidity_percent: np.ndarray,
) -> np.ndarray:
    saturation = 0.6108 * np.exp(
        17.27 * temperature_c / (temperature_c + 237.3)
    )
    return np.maximum(
        saturation * (1.0 - relative_humidity_percent / 100.0),
        0.0,
    ).astype(np.float32)
