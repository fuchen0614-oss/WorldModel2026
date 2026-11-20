"""plan-b-pvt · faithful GreenEarthNet -> Contextformer input adapter.

Vendored from earthnet-models-pytorch @ v0.1.0
  earthnet_models_pytorch/data/en21x_data.py :: EarthNet2021XDataset
(only the Dataset; the LightningDataModule and the `pytorch_lightning` /
`str2bool` imports are dropped so this runs on our torch-2.x stack).

The original variable normalization and five-day mean/min/max layout are retained.
V2 adds calendar features, strict daily alignment, explicit missing-day counts and
Inf rejection. All-NaN normalized statistics use the original zero fallback; this
is a compatibility rule, not an observed weather value or temporal interpolation.

Output per cube (the exact dict ContextFormer.forward expects):
  data["dynamic"][0]   sen2arr   (T=30, 5, H, W)   [ndvi,B02,B03,B04,B8A], NaN->0
  data["dynamic"][1]   eobsarr   (T=30, 24)        weather, normalized+coarsened
  data["dynamic_mask"] [sen2mask (T=30, 1, H, W)]  cloud mask (dlmask/SCL), NaN->4
  data["static"][0]    staticarr (5, H, W)         only [:3] (3 DEMs) are used
  data["landcover"]    esawc_lc  (1, H, W)         for land-cover-balanced scoring
"""

from pathlib import Path
from typing import Union

import numpy as np
import torch
import xarray as xr
from torch.utils.data import Dataset


class GreenEarthNetContextformerDataset(Dataset):
    """Reads GreenEarthNet chopped NetCDF cubes and yields the Contextformer
    `data` dict (faithful copy of the official EarthNet2021XDataset)."""

    def __init__(
        self,
        folder: Union[Path, str],
        fp16: bool = False,
        s2_bands=("ndvi", "B02", "B03", "B04", "B8A"),
        eobs_vars=("fg", "hu", "pp", "qq", "rr", "tg", "tn", "tx"),
        eobs_agg=("mean", "min", "max"),
        static_vars=("nasa_dem", "alos_dem", "cop_dem", "esawc_lc", "geom_cls"),
        start_month_extreme=None,
        dl_cloudmask: bool = True,
    ):
        folder = Path(folder)
        self.filepaths = sorted(list(folder.glob("**/*.nc")))
        self.type = np.float16 if fp16 else np.float32

        self.s2_bands = list(s2_bands)
        self.eobs_vars = list(eobs_vars)
        self.eobs_agg = list(eobs_agg)
        self.static_vars = list(static_vars)
        self.start_month_extreme = start_month_extreme
        self.dl_cloudmask = dl_cloudmask

        # E-OBS normalization constants (verbatim from en21x_data.py)
        self.eobs_mean = xr.DataArray(
            data=[
                8.90661030749754, 2.732927619847993, 77.54440854529798,
                1014.330962704611, 126.47924227500346, 1.7713217310829938,
                4.770701430461286, 13.567999825718509,
            ],
            coords={"variable": [
                "eobs_tg", "eobs_fg", "eobs_hu", "eobs_pp",
                "eobs_qq", "eobs_rr", "eobs_tn", "eobs_tx",
            ]},
        )
        self.eobs_std = xr.DataArray(
            data=[
                9.75620252236597, 1.4870108944469236, 13.511387994026359,
                10.262645403460999, 97.05522895011327, 4.147967261223076,
                9.044987677752898, 11.08198777356161,
            ],
            coords={"variable": [
                "eobs_tg", "eobs_fg", "eobs_hu", "eobs_pp",
                "eobs_qq", "eobs_rr", "eobs_tn", "eobs_tx",
            ]},
        )
        self.static_mean = xr.DataArray(
            data=[0.0, 0.0, 0.0, 0.0, 0.0],
            coords={"variable": list(static_vars)},
        )
        self.static_std = xr.DataArray(
            data=[500.0, 500.0, 500.0, 1.0, 1.0],
            coords={"variable": list(static_vars)},
        )

    def __len__(self) -> int:
        return len(self.filepaths)

    def __getitem__(self, idx: int) -> dict:
        filepath = self.filepaths[idx]
        minicube = xr.open_dataset(filepath)

        if self.start_month_extreme:
            start_idx = {"march": 10, "april": 15, "may": 20, "june": 25, "july": 30}[
                self.start_month_extreme
            ]
            minicube = minicube.isel(time=slice(5 * start_idx, 5 * (start_idx + 30)))

        nir = minicube.s2_B8A
        red = minicube.s2_B04
        ndvi = (nir - red) / (nir + red + 1e-8)
        minicube["s2_ndvi"] = ndvi

        sen2arr = (
            minicube[[f"s2_{b}" for b in self.s2_bands]]
            .to_array("band")
            .isel(time=slice(4, None, 5))
            .transpose("time", "band", "lat", "lon")
            .values
        )
        sen2arr[np.isnan(sen2arr)] = 0.0

        if self.dl_cloudmask:
            sen2mask = (
                minicube.s2_dlmask.where(
                    minicube.s2_dlmask > 0,
                    4 * (~minicube.s2_SCL.isin([1, 2, 4, 5, 6, 7])),
                )
                .isel(time=slice(4, None, 5))
                .transpose("time", "lat", "lon")
                .values[:, None, ...]
            )
            sen2mask[np.isnan(sen2mask)] = 4.0
        else:
            sen2mask = (
                minicube[["s2_mask"]]
                .to_array("band")
                .isel(time=slice(4, None, 5))
                .transpose("time", "band", "lat", "lon")
                .values
            )
            sen2mask[np.isnan(sen2mask)] = 4.0

        eobs = (
            (
                minicube[[f"eobs_{v}" for v in self.eobs_vars]].to_array("variable")
                - self.eobs_mean
            )
            / self.eobs_std
        ).sel(variable=[f"eobs_{v}" for v in self.eobs_vars]).transpose("time", "variable")

        from data.weather_contract import aggregate_weather
        try:
            weather_values, weather_counts, weather_end_dates = aggregate_weather(
                minicube.time.values, eobs.values.tolist(), self.eobs_agg)
        except ValueError as exc:
            raise ValueError(f"{filepath}: {exc}") from exc
        image_end_dates = [str(d)[:10] for d in minicube.time.isel(time=slice(4, None, 5)).values]
        if weather_end_dates != image_end_dates:
            raise ValueError(f"{filepath}: weather/image endpoint mismatch")
        eobsarr = np.asarray(weather_values, dtype=self.type)

        staticarr = (
            (
                (minicube[self.static_vars].to_array("variable") - self.static_mean)
                / self.static_std
            )
            .transpose("variable", "lat", "lon")
            .values
        )
        staticarr[np.isnan(staticarr)] = 0.0

        lc = (
            minicube[["esawc_lc"]]
            .to_array("variable")
            .transpose("variable", "lat", "lon")
            .values
        )

        from data.calendar_features import annual_encoding
        dates = minicube.time.isel(time=slice(4, None, 5)).values
        season = torch.tensor([annual_encoding(d) for d in dates], dtype=torch.float32)
        if len(season) != len(sen2arr):
            raise ValueError("calendar/image length mismatch")
        return {
            "season": season,
            "weather_valid_days": torch.tensor(weather_counts, dtype=torch.int16),
            "dynamic": [
                torch.from_numpy(sen2arr.astype(self.type)),
                torch.from_numpy(eobsarr.astype(self.type)),
            ],
            "dynamic_mask": [torch.from_numpy(sen2mask.astype(self.type))],
            "static": [torch.from_numpy(staticarr.astype(self.type))],
            "static_mask": [],
            "landcover": torch.from_numpy(lc.astype(self.type)),
            "filepath": str(filepath),
            "cubename": filepath.stem,
        }
