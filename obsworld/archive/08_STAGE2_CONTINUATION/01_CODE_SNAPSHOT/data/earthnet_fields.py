"""Field specs and small utilities for ObsWorld Stage 2 on EarthNet2021.

The module is intentionally conservative: all dataset-specific assumptions
are explicit in config-like dataclasses so that server-side inspection can
correct band order or weather channel mappings without rewriting the trainer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import torch


STAGE15_S2_BANDS = [
    "B01", "B02", "B03", "B04", "B05", "B06",
    "B07", "B08", "B8A", "B09", "B11", "B12",
]


@dataclass
class BandSpec:
    """Band bookkeeping for bridging EarthNet bands and Stage1.5 S2 bands."""

    input_bands: List[str] = field(default_factory=lambda: ["blue", "green", "red", "nir"])
    target_bands: List[str] = field(default_factory=lambda: ["blue", "green", "red", "nir"])
    canonical_s2_bands: List[str] = field(default_factory=lambda: list(STAGE15_S2_BANDS))
    red_band: str = "red"
    nir_band: str = "nir"
    scale_factor: float = 10000.0
    auto_scale: bool = True
    reflectance_min: float = 0.0
    reflectance_max: float = 1.0

    @classmethod
    def from_config(cls, config: Optional[dict]) -> "BandSpec":
        if not config:
            return cls()
        return cls(
            input_bands=list(config.get("input_bands", ["blue", "green", "red", "nir"])),
            target_bands=list(config.get("target_bands", config.get("input_bands", ["blue", "green", "red", "nir"]))),
            canonical_s2_bands=list(config.get("canonical_s2_bands", STAGE15_S2_BANDS)),
            red_band=str(config.get("red_band", "red")),
            nir_band=str(config.get("nir_band", "nir")),
            scale_factor=float(config.get("scale_factor", 10000.0)),
            auto_scale=bool(config.get("auto_scale", True)),
            reflectance_min=float(config.get("reflectance_min", 0.0)),
            reflectance_max=float(config.get("reflectance_max", 1.0)),
        )

    @property
    def in_channels(self) -> int:
        return len(self.input_bands)

    @property
    def out_channels(self) -> int:
        return len(self.target_bands)

    @property
    def red_index(self) -> int:
        return self.target_bands.index(self.red_band)

    @property
    def nir_index(self) -> int:
        return self.target_bands.index(self.nir_band)

    def as_dict(self) -> dict:
        return {
            "input_bands": self.input_bands,
            "target_bands": self.target_bands,
            "canonical_s2_bands": self.canonical_s2_bands,
            "red_band": self.red_band,
            "nir_band": self.nir_band,
            "scale_factor": self.scale_factor,
            "auto_scale": self.auto_scale,
        }


@dataclass
class DriverSpec:
    """D-feature layout used by the Stage2 dynamics module.

    The default feature vector is fixed-size and robust to missing channels:
    missing variables are zero-filled and accompanied by a driver mask in the
    dataset batch. DriverEncoder consumes both values and masks, so an absent
    variable is distinguishable from a physically meaningful zero.
    """

    feature_names: List[str] = field(default_factory=lambda: [
        "target_doy_sin",
        "target_doy_cos",
        "precip_sum",
        "precip_mean",
        "temp_mean",
        "vpd_mean",
        "vpd_max",
        "srad_sum",
        "srad_mean",
    ])
    channel_map: Dict[str, Optional[int]] = field(default_factory=lambda: {
        # EarthNet2021 commonly exposes precipitation and temperature-like E-OBS
        # channels. VPD / solar radiation may be absent; keep them masked.
        "precipitation": 0,
        "temperature": 2,
        "vpd": None,
        "solar_radiation": None,
    })

    @classmethod
    def from_config(cls, config: Optional[dict]) -> "DriverSpec":
        spec = cls()
        if not config:
            return spec
        if "feature_names" in config:
            spec.feature_names = list(config["feature_names"])
        if "channel_map" in config:
            spec.channel_map.update(config["channel_map"])
        return spec

    @property
    def dim(self) -> int:
        return len(self.feature_names)


def make_neutral_s2_phi(batch_size: int, device: torch.device) -> Dict[str, torch.Tensor]:
    """Neutral acquisition-condition dict accepted by PureImagingConditionEncoder.

    Stage2 dynamics never consumes phi. This neutral phi is only used when
    EarthNet does not provide compatible acquisition metadata for the Stage1.5
    observation encoder / optional decoder conditioning.
    """

    return {
        "modality": torch.zeros(batch_size, dtype=torch.long, device=device),
        "time_valid": torch.zeros(batch_size, dtype=torch.float32, device=device),
        "sun_elevation": torch.full((batch_size,), float("nan"), dtype=torch.float32, device=device),
    }


def compute_ndvi(x: torch.Tensor, red_index: int, nir_index: int, eps: float = 1e-6) -> torch.Tensor:
    """Compute NDVI from reflectance-space tensors.

    Args:
        x: [..., C, H, W] reflectance tensor.
    """

    red = x[..., red_index, :, :]
    nir = x[..., nir_index, :, :]
    return (nir - red) / (nir + red + eps)
