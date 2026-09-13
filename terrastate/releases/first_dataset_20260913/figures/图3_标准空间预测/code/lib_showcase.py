#!/usr/bin/env python3
"""Shared helpers for the first-dataset showcase package.

Everything here mirrors the VERIFIED code paths rather than re-deriving them:
  * NDVI and the cloud/land-cover mask come from the project's own dataset class
    (`data/greenearthnet_contextformer_dataset.py`, s2_bands[0] == "ndvi");
  * the official target timestamps come from `eval/greenearthnet_protocol.expected_prediction_times`
    (context_steps=10, target_steps=20, offset_days=4, stride_days=5);
  * TerraState-C1 predictions are READ from the frozen E1 evaluation NetCDFs, never re-inferred.

Nothing in this module writes to the shared repository.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

# ----------------------------------------------------------------- frozen sources (read-only)
REPO = Path("/data/zs/WorldModel2026/terrastate")
VAL_ROOT = Path("/data/zs/TrainData/EarthNet2021/earthnet2021x")
OOD_S_REPAIR = Path("/data/zs/earthnet_ood_s_repair_20260908T140000Z")
E1 = Path("/data/zs/multiseed_standard_eval_20260910T074115Z")
FROZEN = Path("/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/"
              "first_dataset_closure_fix_20260911T081702Z")
E1_MAIN_TABLE = REPO / "evaluations/e1_main_table"
C1_CKPT = REPO / "ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt"

# E1 directory name -> validation-data root
SPLITS = {
    "iid_chopped": {"val": VAL_ROOT / "iid_chopped", "e1": "iid_chopped",
                    "contract": "iid_chopped"},
    "ood-t_chopped": {"val": VAL_ROOT / "ood-t_chopped", "e1": "ood-t_chopped",
                      "contract": "ood-t_chopped"},
    "ood-st_chopped": {"val": VAL_ROOT / "ood-st_chopped", "e1": "ood-st_chopped",
                       "contract": "ood-st_chopped"},
    "ood-s_chopped": {"val": VAL_ROOT / "ood-s_chopped", "e1": "ood-s_chopped_repaired_v2",
                      "contract": "ood-s_chopped_repaired_v2"},
}
SPLIT_ORDER = ["iid_chopped", "ood-t_chopped", "ood-s_chopped", "ood-st_chopped"]

# model / scorer constants, taken from the verified code
CONTEXT_STEPS = 10
TARGET_STEPS = 20
OFFSET_DAYS = 4
STRIDE_DAYS = 5
VALID_SCL_CLASSES = (1, 2, 4, 5, 6, 7)
# per-step substitution value used for the official cloud mask
MASK_FILL = 4.0


def out_root() -> Path:
    """This package's root, resolved from the script location (self-contained)."""
    return Path(__file__).resolve().parents[1]


# ----------------------------------------------------------------- data access
def repaired_gt_path(split: str, rel: str) -> Path:
    """GT path actually used by the frozen evaluation.

    The ood-s split needed a readability repair: accepted repaired files live under a separate
    output root and take precedence over the original download. For every other split the
    original validation root is used.
    """
    if split == "ood-s_chopped":
        rp = OOD_S_REPAIR / rel
        if rp.exists():
            return rp
    return SPLITS[split]["val"] / rel


def list_cubes(split: str) -> list[str]:
    """Deterministic, sorted list of `<season>/<cube>.nc` relative paths."""
    root = SPLITS[split]["val"]
    return sorted(str(p.relative_to(root)) for p in root.rglob("*.nc"))


def read_rgb_like(path: Path, bands=("s2_B8A", "s2_B04", "s2_B03")) -> np.ndarray:
    import xarray as xr
    with xr.open_dataset(path) as d:
        arr = np.stack([d[b].isel(time=slice(OFFSET_DAYS, None, STRIDE_DAYS)).values
                        for b in bands], axis=0)
    return arr


def read_ndvi_mask_lc(path: Path) -> dict:
    """NDVI, validity mask and land cover on the official 30-step five-daily grid.

    Mirrors `GreenEarthNetContextformerDataset.__getitem__` exactly:
      ndvi   = (B8A - B04) / (B8A + B04 + 1e-8)
      mask   = s2_dlmask where > 0 else 4 * ~s2_SCL.isin(VALID_SCL_CLASSES); NaN -> 4
      sample = isel(time=slice(4, None, 5))
    """
    import xarray as xr
    # Slice BEFORE .values so only the 30 needed time slabs are read from disk: the cube carries
    # 150 daily steps and reading all of them costs ~5x more I/O for no benefit.
    sl = slice(OFFSET_DAYS, None, STRIDE_DAYS)
    with xr.open_dataset(path) as d:
        nir = d["s2_B8A"].isel(time=sl).values
        red = d["s2_B04"].isel(time=sl).values
        dlmask = d["s2_dlmask"].isel(time=sl).values
        scl = d["s2_SCL"].isel(time=sl).values
        lc = d["esawc_lc"].values
    ndvi = (nir - red) / (nir + red + 1e-8)
    scl_ok = np.isin(scl, VALID_SCL_CLASSES)
    mask = np.where(dlmask > 0, dlmask, MASK_FILL * (~scl_ok))
    mask = np.nan_to_num(mask, nan=MASK_FILL)
    return {"ndvi": ndvi.astype(np.float64), "mask": mask.astype(np.float64),
            "landcover": np.asarray(lc, dtype=np.float64)}


def load_contract_cfg() -> dict:
    import torch
    ck = torch.load(C1_CKPT, map_location="cpu", weights_only=False)
    cfg = dict(ck.get("contract_cfg") or {})
    cfg.setdefault("state_dim", 256)
    return cfg


def veg_mask(landcover: np.ndarray, lc_min: float, lc_max: float) -> np.ndarray:
    lc = np.asarray(landcover).reshape(-1)[0] if np.asarray(landcover).ndim == 3 else landcover
    return ((lc >= lc_min) & (lc <= lc_max)).astype(np.float64)


def validity(ndvi: np.ndarray, mask: np.ndarray, veg: np.ndarray) -> np.ndarray:
    """valid = (cloud mask < 1) AND vegetation land cover AND finite NDVI, on (T,H,W)."""
    return ((mask < 1.0) & np.isfinite(ndvi) & (veg[None, :, :] > 0)).astype(np.float64)


# ----------------------------------------------------------------- C1 predictions (read-only)
def c1_pred_path(split: str, rel: str, seed: int = 42) -> Path:
    return E1 / f"eval/seed{seed}/{SPLITS[split]['e1']}/q1_full/pred" / rel


def read_c1_pred(split: str, rel: str, seed: int = 42) -> np.ndarray | None:
    import xarray as xr
    p = c1_pred_path(split, rel, seed)
    if not p.exists():
        return None
    with xr.open_dataset(p) as d:
        return np.asarray(d["ndvi_pred"].values, dtype=np.float64)


def read_c1_pred_times(split: str, rel: str, seed: int = 42) -> list[str]:
    import xarray as xr
    p = c1_pred_path(split, rel, seed)
    with xr.open_dataset(p) as d:
        return [str(x)[:10] for x in d["time"].values]


def read_gt_times(split: str, rel: str) -> list[str]:
    import xarray as xr
    with xr.open_dataset(repaired_gt_path(split, rel)) as d:
        return [str(x)[:10] for x in d["time"].values]


# ----------------------------------------------------------------- persistence
def persistence_from_context(ndvi: np.ndarray, valid: np.ndarray, cl: int = CONTEXT_STEPS,
                             tl: int = TARGET_STEPS) -> np.ndarray:
    """Official persistence: repeat each pixel's LAST VALID context observation.

    Deterministic given the cube, so it is reproduced rather than read.
    """
    ctx = ndvi[:cl]
    ctx_valid = valid[:cl] > 0
    idx = np.where(ctx_valid.any(axis=0), ctx_valid.shape[0] - 1 - np.argmax(ctx_valid[::-1], axis=0), -1)
    last = np.zeros(ctx.shape[1:], dtype=np.float64)
    for h in range(ctx.shape[1]):
        for w in range(ctx.shape[2]):
            j = idx[h, w]
            if j >= 0:
                last[h, w] = ctx[j, h, w]
    return np.repeat(last[None, :, :], tl, axis=0)


# ----------------------------------------------------------------- styling (unified across panels)
NDVI_CMAP = "viridis"
NDVI_VMIN, NDVI_VMAX = 0.0, 1.0
ERR_CMAP = "magma"
ERR_VMIN, ERR_VMAX = 0.0, 0.4          # errors above ERR_VMAX are clipped, and the caption says so
MIN_VALID_FRACTION = 0.15              # below this a candidate is not interpretable -> excluded


def setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.dpi": 130, "savefig.dpi": 130, "savefig.bbox": "tight",
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "axes.grid": False, "image.interpolation": "nearest",
    })
    return plt


def masked_panel(ax, arr, cmap=NDVI_CMAP, vmin=NDVI_VMIN, vmax=NDVI_VMAX, valid=None,
                 title=None, invalid_color="0.75"):
    """Show an NDVI panel; invalid pixels are drawn in a flat grey, never as a zero value."""
    a = np.array(arr, dtype=np.float64, copy=True)
    if valid is not None:
        a = np.where(valid > 0, a, np.nan)
    cm = plt_get_cmap(cmap).copy()
    cm.set_bad(invalid_color)
    im = ax.imshow(a, cmap=cm, vmin=vmin, vmax=vmax)
    if title:
        ax.set_title(title, fontsize=9)
    ax.set_xticks([]); ax.set_yticks([])
    return im


def plt_get_cmap(name):
    import matplotlib
    import matplotlib.pyplot as plt
    try:
        return matplotlib.colormaps[name]
    except Exception:  # noqa: BLE001
        return plt.get_cmap(name)


def masked_error_panel(ax, err, valid, cmap=ERR_CMAP, vmin=ERR_VMIN, vmax=ERR_VMAX,
                       title=None):
    a = np.where(valid > 0, err, np.nan)
    cm = plt_get_cmap(cmap).copy()
    cm.set_bad("0.75")
    im = ax.imshow(a, cmap=cm, vmin=vmin, vmax=vmax)
    if title:
        ax.set_title(title, fontsize=9)
    ax.set_xticks([]); ax.set_yticks([])
    return im


def rmse_on(pred, target, valid):
    """Masked RMSE over the whole 20-step window (same definition as the official scorer)."""
    m = (valid > 0) & np.isfinite(pred) & np.isfinite(target)
    if m.sum() == 0:
        return float("nan")
    return float(np.sqrt(np.mean((pred[m] - target[m]) ** 2)))
