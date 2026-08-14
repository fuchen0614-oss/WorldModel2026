"""GreenEarthNet NetCDF adapter for TerraState."""

import json
from pathlib import Path
from typing import Union

import numpy as np
import torch
import xarray as xr
from torch.utils.data import Dataset


class GreenEarthNetDataset(Dataset):
    """Read chopped NetCDF minicubes and return TerraState tensors."""

    def __init__(
        self,
        folder: Union[Path, str],
        fp16: bool = False,
        s2_bands=("ndvi", "B" + "02", "B" + "03", "B" + "04", "B8A"),
        eobs_vars=("fg", "hu", "pp", "qq", "rr", "tg", "tn", "tx"),
        eobs_agg=("mean", "min", "max"),
        static_vars=("nasa_dem", "alos_dem", "cop_dem", "esawc_lc", "geom_cls"),
        start_month_extreme=None,
        dl_cloudmask: bool = True,
        manifest: Union[Path, str, None] = None,
    ):
        folder = Path(folder)
        if manifest is None:
            self.filepaths = sorted(folder.glob("**/*.nc"))
        else:
            payload = json.loads(Path(manifest).read_text(encoding="utf-8"))
            self.filepaths = [folder / item["path"] for item in payload["files"]]
            missing = [str(path) for path in self.filepaths if not path.is_file()]
            if missing:
                raise FileNotFoundError(
                    f"Manifest files are missing under DATA_ROOT: {missing[:3]}"
                )
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

        nir = minicube["s2_" + "B8A"]
        red = minicube["s2_" + "B" + "04"]
        ndvi = (nir - red) / (nir + red + 1e-8)
        minicube["s2_ndvi"] = ndvi
        clear_full = (minicube.s2_dlmask < 1) & minicube.s2_SCL.isin(
            [1, 2, 4, 5, 6, 7]
        )

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
        ).transpose("time", "variable")

        eobsarr = []
        if "mean" in self.eobs_agg:
            eobsarr.append(eobs.coarsen(time=5, coord_func="max").mean())
        if "min" in self.eobs_agg:
            eobsarr.append(eobs.coarsen(time=5, coord_func="max").min())
        if "max" in self.eobs_agg:
            eobsarr.append(eobs.coarsen(time=5, coord_func="max").max())
        if "std" in self.eobs_agg:
            eobsarr.append(eobs.coarsen(time=5, coord_func="max").std())
        eobsarr = np.concatenate(eobsarr, axis=1)
        eobsarr[np.isnan(eobsarr)] = 0.0

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
        clear_target = (
            clear_full.isel(time=slice(4, None, 5))
            .isel(time=slice(10, 30))
            .transpose("time", "lat", "lon")
            .values
        )
        target_ndvi = (
            ndvi.isel(time=slice(4, None, 5))
            .isel(time=slice(10, 30))
            .where(
                clear_full.isel(time=slice(4, None, 5)).isel(
                    time=slice(10, 30)
                )
            )
        )
        eligible = (
            (minicube.esawc_lc < 41)
            & (ndvi.where(clear_full).min("time") > 0.0)
            & (clear_target.sum(0) >= 10)
            & ((clear_full.sum("time").values - clear_target.sum(0)) >= 3)
            & (target_ndvi.std("time").values > 0.1)
        )

        return {
            "dynamic": [
                torch.from_numpy(sen2arr.astype(self.type)),
                torch.from_numpy(eobsarr.astype(self.type)),
            ],
            "dynamic_mask": [torch.from_numpy(sen2mask.astype(self.type))],
            "static": [torch.from_numpy(staticarr.astype(self.type))],
            "static_mask": [],
            "landcover": torch.from_numpy(lc.astype(self.type)),
            "evaluation_clear": torch.from_numpy(clear_target.astype(bool)),
            "evaluation_eligible": torch.from_numpy(
                np.asarray(eligible).astype(bool)
            ),
            "filepath": str(filepath),
            "cubename": filepath.stem,
        }
