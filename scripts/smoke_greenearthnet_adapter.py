"""Local smoke for the GreenEarthNet -> Contextformer data adapter.

Builds a synthetic minicube matching the GreenEarthNet schema, runs the adapter,
checks the produced tensor shapes, then feeds them through the reproduced
Contextformer end-to-end. No real data / GPU needed. This validates the data
path shape-contract locally; the real numeric parity runs on the server.
"""

import os
import sys
import tempfile

import numpy as np
import torch
import xarray as xr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from data.greenearthnet_contextformer_dataset import (  # noqa: E402
    GreenEarthNetContextformerDataset,
)
from models.encoders.pvt_contextformer_q import (  # noqa: E402
    PVTContextformerQ,
    contextformer6m_hparams,
)


def make_fake_cube(path, T=150, H=128, W=128, seed=0):
    rng = np.random.default_rng(seed)
    tvu = lambda: (("time", "lat", "lon"), rng.random((T, H, W)).astype("float32"))
    tv = lambda: (("time",), rng.random((T,)).astype("float32"))
    hw = lambda: (("lat", "lon"), rng.random((H, W)).astype("float32"))
    ds = xr.Dataset(
        {
            "s2_B02": tvu(), "s2_B03": tvu(), "s2_B04": tvu(), "s2_B8A": tvu(),
            "s2_dlmask": (("time", "lat", "lon"),
                          rng.integers(0, 2, (T, H, W)).astype("float32")),
            "s2_SCL": (("time", "lat", "lon"),
                       rng.integers(0, 12, (T, H, W)).astype("float32")),
            "eobs_fg": tv(), "eobs_hu": tv(), "eobs_pp": tv(), "eobs_qq": tv(),
            "eobs_rr": tv(), "eobs_tg": tv(), "eobs_tn": tv(), "eobs_tx": tv(),
            "nasa_dem": hw(), "alos_dem": hw(), "cop_dem": hw(),
            "esawc_lc": hw(), "geom_cls": hw(),
        },
        coords={"time": np.arange(T), "lat": np.arange(H), "lon": np.arange(W)},
    )
    ds.to_netcdf(path)


def batch(sample):
    return {
        "dynamic": [sample["dynamic"][0].unsqueeze(0), sample["dynamic"][1].unsqueeze(0)],
        "dynamic_mask": [sample["dynamic_mask"][0].unsqueeze(0)],
        "static": [sample["static"][0].unsqueeze(0)],
    }


def main():
    print("=" * 70)
    print("Adapter smoke: synthetic GreenEarthNet cube -> Contextformer")
    print("=" * 70)
    with tempfile.TemporaryDirectory() as d:
        make_fake_cube(os.path.join(d, "minicube_fake.nc"))
        adapter = GreenEarthNetContextformerDataset(d, dl_cloudmask=True)
        print(f"[adapter] cubes found: {len(adapter)}")
        s = adapter[0]
        shapes = {
            "sen2arr": tuple(s["dynamic"][0].shape),
            "eobsarr": tuple(s["dynamic"][1].shape),
            "sen2mask": tuple(s["dynamic_mask"][0].shape),
            "staticarr": tuple(s["static"][0].shape),
            "landcover": tuple(s["landcover"].shape),
        }
        for k, v in shapes.items():
            print(f"[adapter] {k:10s}: {v}")
        assert shapes["sen2arr"] == (30, 5, 128, 128), shapes["sen2arr"]
        assert shapes["eobsarr"] == (30, 24), shapes["eobsarr"]
        assert shapes["sen2mask"] == (30, 1, 128, 128), shapes["sen2mask"]
        assert shapes["staticarr"] == (5, 128, 128), shapes["staticarr"]

        model = PVTContextformerQ(contextformer6m_hparams(pvt_pretrained=False)).eval()
        with torch.no_grad():
            preds, z = model.encode(batch(s), pred_start=10, preds_length=20)
        print(f"[model  ] preds: {tuple(preds.shape)} (expect (1,20,1,128,128)), "
              f"finite={torch.isfinite(preds).all().item()}")
        print(f"[model  ] z    : {tuple(z.shape)} (expect (1024,30,256))")
        ok = tuple(preds.shape) == (1, 20, 1, 128, 128) and torch.isfinite(preds).all().item()
    print("-" * 70)
    print(f"RESULT: {'PASS' if ok else 'FAIL'}")
    print("=" * 70)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
