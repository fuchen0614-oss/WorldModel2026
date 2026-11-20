"""Render two landscape appendix panels from frozen forecast arrays only.

No model inference, training, or cherry-picked per-frame selection is performed.
The script writes audit JSON alongside each image.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "源数组"
OUT = ROOT

NDVI_MIN, NDVI_MAX = -0.6, 0.9
ERROR_MIN, ERROR_MAX = 0.0, 0.45


def common_style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 9,
        "pdf.fonttype": 42,
    })


def new_canvas():
    fig = plt.figure(figsize=(7.8, 3.8), facecolor="white")
    gs = fig.add_gridspec(
        2, 5, left=0.095, right=0.985, top=0.90, bottom=0.205,
        wspace=0.045, hspace=0.12
    )
    ndvi = plt.get_cmap("viridis").copy()
    error = plt.get_cmap("magma").copy()
    ndvi.set_bad("#b7bfc5")
    error.set_bad("#b7bfc5")
    return fig, gs, ndvi, error


def image_cell(fig, gs, row, col, values, valid, cmap, low, high, title, row_label):
    ax = fig.add_subplot(gs[row, col])
    ax.imshow(np.ma.masked_where(~valid, values), cmap=cmap, vmin=low, vmax=high,
              interpolation="nearest", origin="upper")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    if row == 0:
        ax.set_title(title, pad=5)
    if col == 0:
        ax.text(-0.105, 0.5, row_label, transform=ax.transAxes,
                rotation=90, ha="center", va="center", fontsize=9, fontweight="bold")


def legends(fig, ndvi, error):
    bar1 = fig.add_axes([0.15, 0.095, 0.29, 0.022])
    bar2 = fig.add_axes([0.57, 0.095, 0.29, 0.022])
    cb1 = fig.colorbar(ScalarMappable(Normalize(NDVI_MIN, NDVI_MAX), ndvi),
                       cax=bar1, orientation="horizontal", extend="both")
    cb2 = fig.colorbar(ScalarMappable(Normalize(ERROR_MIN, ERROR_MAX), error),
                       cax=bar2, orientation="horizontal", extend="max")
    cb1.set_label("NDVI", fontsize=8, labelpad=2)
    cb2.set_label("Absolute NDVI error", fontsize=8, labelpad=2)
    cb1.set_ticks([-0.6, -0.3, 0.0, 0.3, 0.6, 0.9])
    cb2.set_ticks([0.0, 0.15, 0.30, 0.45])
    for cb in (cb1, cb2):
        cb.ax.tick_params(labelsize=7, length=2, pad=2)
    fig.legend(handles=[Patch(facecolor="#b7bfc5", edgecolor="none", label="Invalid / unscored")],
               loc="lower center", bbox_to_anchor=(0.5, -0.001), frameon=False,
               fontsize=7.5)


def mse(pred, obs, valid):
    return float(np.mean((pred[valid] - obs[valid]) ** 2))


def render_h1():
    with np.load(SOURCES / "P42_arrays.npz") as z:
        gt, c1, valid = (z[k].copy() for k in ("gt", "c1", "valid"))
    with np.load(SOURCES / "P42_official_baselines.npz") as z:
        predrnn = z["predrnn"].copy()
    meta = json.loads((SOURCES / "P42_metadata.json").read_text(encoding="utf-8"))
    assert gt.shape == c1.shape == valid.shape == predrnn.shape
    steps = [4, 14]  # one-based future steps 5 and 15: days 25 and 75
    fig, gs, ndvi, error = new_canvas()
    columns = ["Observed", "SpanWorld", "PredRNN 1M",
               "SpanWorld |error|", "PredRNN |error|"]
    records = []
    for row, i in enumerate(steps):
        mask = valid[i].astype(bool) & np.isfinite(gt[i]) & np.isfinite(c1[i]) & np.isfinite(predrnn[i])
        assert mask.any()
        values = [gt[i], c1[i], predrnn[i], np.abs(c1[i]-gt[i]), np.abs(predrnn[i]-gt[i])]
        for col, value in enumerate(values):
            image_cell(fig, gs, row, col, value, mask, ndvi if col < 3 else error,
                       NDVI_MIN if col < 3 else ERROR_MIN,
                       NDVI_MAX if col < 3 else ERROR_MAX,
                       columns[col], f"Day {(i+1)*5}")
        records.append({
            "step_1based": i+1,
            "date": meta["target_dates"][i],
            "valid_pixels": int(mask.sum()),
            "coverage": float(mask.mean()),
            "spanworld_mse_unclipped": mse(c1[i], gt[i], mask),
            "predrnn_mse_unclipped": mse(predrnn[i], gt[i], mask),
        })
    legends(fig, ndvi, error)
    fig.savefig(OUT / "H1_标准预测案例.png", dpi=350, facecolor="white")
    fig.savefig(OUT / "H1_标准预测案例.pdf", facecolor="white")
    plt.close(fig)
    audit = {
        "source_arrays": str(SOURCES / "P42_arrays.npz"),
        "source_baselines": str(SOURCES / "P42_official_baselines.npz"),
        "case": "P42 IID; same case family as main-text example, different dates",
        "selection": "steps 5 and 15 fixed before rendering; not selected by per-frame error",
        "ndvi_display": [NDVI_MIN, NDVI_MAX],
        "absolute_error_display": [ERROR_MIN, ERROR_MAX],
        "display_clipping_only": True,
        "same_valid_mask_within_each_row": True,
        "records": records,
    }
    (OUT / "H1_数值核验.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")


def render_h2():
    with np.load(SOURCES / "frames.npz") as z:
        arrays = {key: z[key].copy() for key in z.files}
    meta = json.loads((SOURCES / "metadata.json").read_text(encoding="utf-8"))
    i = 19  # one-based step 14: day 70, highest suffix coverage
    j = i - 10  # continued arrays cover absolute forecast steps 11..20
    fig, gs, ndvi, error = new_canvas()
    columns = ["Observed", "Direct", "Continued",
               "Direct |error|", "Continued |error|"]
    rows = [("SpanWorld", "C1"), ("Control", "C0R")]
    records = []
    for row, (label, key) in enumerate(rows):
        obs = arrays["gt"]
        direct = arrays[f"{key}_direct"]
        continued = arrays[f"{key}_continued"]
        mask = arrays["valid"].astype(bool) & np.isfinite(obs) & np.isfinite(direct) & np.isfinite(continued)
        assert mask.any()
        values = [obs, direct, continued, np.abs(direct-obs), np.abs(continued-obs)]
        for col, value in enumerate(values):
            image_cell(fig, gs, row, col, value, mask, ndvi if col < 3 else error,
                       NDVI_MIN if col < 3 else ERROR_MIN,
                       NDVI_MAX if col < 3 else ERROR_MAX,
                       columns[col], label)
        records.append({
            "scheme": "SpanWorld" if key == "C1" else "Direct-endpoint control",
            "step_1based": i+1,
            "date": meta["dates"][i],
            "valid_pixels": int(mask.sum()),
            "coverage": float(mask.mean()),
            "direct_mse_unclipped": mse(direct, obs, mask),
            "continued_mse_unclipped": mse(continued, obs, mask),
        })
    legends(fig, ndvi, error)
    fig.savefig(OUT / "H2_续推不利案例.png", dpi=350, facecolor="white")
    fig.savefig(OUT / "H2_续推不利案例.pdf", facecolor="white")
    plt.close(fig)
    audit = {
        "source_arrays": str(SOURCES / "frames.npz"),
        "source_metadata": str(SOURCES / "metadata.json"),
        "case": meta["id"] + " IID",
        "selection": meta["selection"],
        "suffix_benefit_C0R_minus_C1": meta["benefit"],
        "date_selection": "day100 fixed in prior candidate export; all >=40% coverage cases with C1 continued MSE > own direct MSE retained",
        "selected_step_coverage_from_metadata": meta["coverage_by_step"][i],
        "ndvi_display": [NDVI_MIN, NDVI_MAX],
        "absolute_error_display": [ERROR_MIN, ERROR_MAX],
        "display_clipping_only": True,
        "same_valid_mask_within_each_row": True,
        "records": records,
    }
    (OUT / "H2_数值核验.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    common_style()
    OUT.mkdir(exist_ok=True)
    render_h1()
    render_h2()
