#!/usr/bin/env python3
"""Thumbnails and multi-page contact sheets.

Each case gets one compact thumbnail next to its ID; the contact sheets stack 8 prediction cases
(or 6 weather cases) per page so that IDs, categories and splits stay legible after scaling.
IDs on the sheets match the detail-figure filenames exactly.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_showcase as L  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
plt = L.setup_matplotlib()
from matplotlib.gridspec import GridSpec  # noqa: E402

LATE = 19
PER_PAGE_PRED = 5
PER_PAGE_WX = 6


def _cm(name, bad="0.80"):
    cm = L.plt_get_cmap(name).copy()
    cm.set_bad(bad)
    return cm


def display_step(arrdir: Path) -> int:
    """Pre-registered display step: the step with the largest valid fraction (ties -> later).
    Recorded in the candidate metadata; identical for every model of that sample.
    `arrdir` is the candidate's own array directory (prediction and weather live in different
    parents, so the caller passes it rather than reconstructing the path)."""
    m = json.loads((Path(arrdir) / "metadata.json").read_text(encoding="utf-8"))
    if "display_step_1based" in m:
        return int(m["display_step_1based"]) - 1
    v = np.load(Path(arrdir) / "arrays.npz")["valid"]
    vf = v.mean(axis=(1, 2))
    return len(vf) - 1 - int(np.argmax(vf[::-1])) if vf.max() > 0 else v.shape[0] - 1


def small(ax, arr, valid, cmap=None, vmin=None, vmax=None):
    ax.imshow(np.where(valid > 0, arr, np.nan), cmap=cmap or _cm(L.NDVI_CMAP),
              vmin=L.NDVI_VMIN if vmin is None else vmin,
              vmax=L.NDVI_VMAX if vmax is None else vmax)
    ax.set_xticks([]); ax.set_yticks([])


def pred_thumb(out: Path, cid: str, arr, arrdir: Path) -> Path:
    gt, c1, v = arr["gt"], arr["c1"], arr["valid"]
    h = display_step(arrdir)
    d = out / "gallery/prediction/thumbs"
    d.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(3.6, 1.45))
    small(axes[0], gt[h], v[h]); axes[0].set_title("truth", fontsize=6.5, pad=1.5)
    small(axes[1], c1[h], v[h]); axes[1].set_title("C1", fontsize=6.5, pad=1.5)
    small(axes[2], np.abs(c1[h] - gt[h]), v[h], cmap=_cm(L.ERR_CMAP),
          vmin=L.ERR_VMIN, vmax=L.ERR_VMAX)
    axes[2].set_title("|err|", fontsize=6.5, pad=1.5)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.86, bottom=0.01, wspace=0.04)
    p = d / f"{cid}_thumb.png"
    fig.savefig(p, dpi=110); plt.close(fig)
    return p


def wx_thumb(out: Path, cid: str, arr, arrdir: Path) -> Path:
    gt, pa, pd_, pm, v = (arr["gt"], arr["pred_actual"], arr["pred_donor"],
                          arr["pred_mean"], arr["valid"])
    h = display_step(arrdir)
    d = out / "gallery/weather/thumbs"
    d.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 4, figsize=(4.8, 1.45))
    small(axes[0], gt[h], v[h]); axes[0].set_title("truth", fontsize=6.5, pad=1.5)
    small(axes[1], pa[h], v[h]); axes[1].set_title("actual", fontsize=6.5, pad=1.5)
    small(axes[2], pd_[h] - pa[h], v[h], cmap=_cm("coolwarm"), vmin=-0.4, vmax=0.4)
    axes[2].set_title("donor-actual", fontsize=6.5, pad=1.5)
    small(axes[3], pm[h] - pa[h], v[h], cmap=_cm("coolwarm"), vmin=-0.4, vmax=0.4)
    axes[3].set_title("mean-actual", fontsize=6.5, pad=1.5)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.86, bottom=0.01, wspace=0.04)
    p = d / f"{cid}_thumb.png"
    fig.savefig(p, dpi=110); plt.close(fig)
    return p


def sheet_pred(out: Path, cases: list[dict], page: int, n_pages: int):
    n = len(cases)
    fig = plt.figure(figsize=(9.6, 1.62 * n + 1.0))
    gs = GridSpec(n, 6, figure=fig, hspace=0.30, wspace=0.06,
                  left=0.035, right=0.985, top=1 - 0.62 / (1.62 * n + 1.0),
                  bottom=0.40 / (1.62 * n + 1.0))
    for i, c in enumerate(cases):
        z = np.load(c["_arr"] / "arrays.npz")
        gt, c1, v = z["gt"], z["c1"], z["valid"]
        h = display_step(c["_arr"])
        axl = fig.add_subplot(gs[i, 0])
        axl.axis("off")
        axl.text(0.0, 0.5, f"{c['candidate_id']}\n{c['split'].replace('_chopped','')}\n"
                           f"{c['category']}\nt+{h + 1}",
                 fontsize=7.4, va="center", ha="left", linespacing=1.5)
        a_gt = fig.add_subplot(gs[i, 1:3]); small(a_gt, gt[h], v[h])
        a_c1 = fig.add_subplot(gs[i, 3:5]); small(a_c1, c1[h], v[h])
        a_er = fig.add_subplot(gs[i, 5])
        small(a_er, np.abs(c1[h] - gt[h]), v[h], cmap=_cm(L.ERR_CMAP),
              vmin=L.ERR_VMIN, vmax=L.ERR_VMAX)
        if i == 0:
            a_gt.set_title("Ground truth", fontsize=8.5, pad=4)
            a_c1.set_title("TerraState-C1 prediction", fontsize=8.5, pad=4)
            a_er.set_title("|error|", fontsize=8.5, pad=4)
    fig.suptitle(f"Prediction candidates — contact sheet {page}/{n_pages}   "
                 f"(IDs match the detail figures in gallery/prediction/; the step shown is each "
                 f"candidate's best-covered step)",
                 fontsize=10.5, y=0.995)
    d = out / "gallery/contact_sheets"
    d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / f"CONTACT_prediction_page{page:02d}.png", dpi=120)
    fig.savefig(d / f"CONTACT_prediction_page{page:02d}.pdf")
    plt.close(fig)


def sheet_wx(out: Path, cases: list[dict], page: int, n_pages: int):
    n = len(cases)
    fig = plt.figure(figsize=(10.0, 1.62 * n + 1.0))
    gs = GridSpec(n, 6, figure=fig, hspace=0.30, wspace=0.06,
                  left=0.035, right=0.985, top=1 - 0.62 / (1.62 * n + 1.0),
                  bottom=0.40 / (1.62 * n + 1.0))
    for i, c in enumerate(cases):
        z = np.load(c["_arr"] / "arrays.npz")
        gt, pa, pd_, pm, v = (z["gt"], z["pred_actual"], z["pred_donor"], z["pred_mean"],
                              z["valid"])
        h = display_step(c["_arr"])
        axl = fig.add_subplot(gs[i, 0]); axl.axis("off")
        axl.text(0.0, 0.5, f"{c['case_id']}\nq3 #{c['q3_source_index']}\n"
                           f"tile {c.get('tile','')}\nt+{h + 1}",
                 fontsize=7.4, va="center", ha="left", linespacing=1.5)
        a_gt = fig.add_subplot(gs[i, 1]); small(a_gt, gt[h], v[h])
        a_ac = fig.add_subplot(gs[i, 2]); small(a_ac, pa[h], v[h])
        a_dn = fig.add_subplot(gs[i, 3])
        small(a_dn, pd_[h] - pa[h], v[h], cmap=_cm("coolwarm"), vmin=-0.4, vmax=0.4)
        a_mn = fig.add_subplot(gs[i, 4])
        small(a_mn, pm[h] - pa[h], v[h], cmap=_cm("coolwarm"), vmin=-0.4, vmax=0.4)
        a_vd = fig.add_subplot(gs[i, 5])
        small(a_vd, v[h].astype(float), v[h], cmap=_cm("Greys", bad="white"),
              vmin=0, vmax=1)
        if i == 0:
            for ax_, t in ((a_gt, "truth"), (a_ac, "actual"), (a_dn, "donor − actual"),
                           (a_mn, "mean − actual"), (a_vd, "valid")):
                ax_.set_title(t, fontsize=8.5, pad=4)
    fig.suptitle(f"Weather-response candidates — contact sheet {page}/{n_pages}   "
                 f"(donor/mean are counterfactual: no observed truth)", fontsize=11, y=0.995)
    d = out / "gallery/contact_sheets"
    d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / f"CONTACT_weather_page{page:02d}.png", dpi=120)
    fig.savefig(d / f"CONTACT_weather_page{page:02d}.pdf")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out = args.out

    preds = []
    for d in sorted((out / "gallery/_arrays").glob("P*")):
        m = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
        m["_arr"] = d
        preds.append(m)
    preds.sort(key=lambda m: m["candidate_id"])
    for m in preds:
        z = np.load(m["_arr"] / "arrays.npz")
        pred_thumb(out, m["candidate_id"], {k: z[k] for k in z.files}, m["_arr"])
    npg = max(1, math.ceil(len(preds) / PER_PAGE_PRED))
    if preds:
        for p in range(npg):
            sheet_pred(out, preds[p * PER_PAGE_PRED:(p + 1) * PER_PAGE_PRED], p + 1, npg)
    print(f"prediction: {len(preds)} thumbs, {npg if preds else 0} contact sheet page(s)")

    wx = []
    for d in sorted((out / "gallery/weather/_arrays").glob("W*")):
        m = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
        m["_arr"] = d
        wx.append(m)
    wx.sort(key=lambda m: m["case_id"])
    for m in wx:
        z = np.load(m["_arr"] / "arrays.npz")
        wx_thumb(out, m["case_id"], {k: z[k] for k in z.files}, m["_arr"])
    npg2 = max(1, math.ceil(len(wx) / PER_PAGE_WX))
    if wx:
        for p in range(npg2):
            sheet_wx(out, wx[p * PER_PAGE_WX:(p + 1) * PER_PAGE_WX], p + 1, npg2)
    print(f"weather: {len(wx)} thumbs, {npg2 if wx else 0} contact sheet page(s)")


if __name__ == "__main__":
    main()
