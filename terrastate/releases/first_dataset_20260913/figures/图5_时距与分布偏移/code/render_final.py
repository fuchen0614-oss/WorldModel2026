#!/usr/bin/env python3
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG = Path(__file__).resolve().parents[1]
BLUE, ORANGE, GREEN, PURPLE = "#0072B2", "#D55E00", "#009E73", "#CC79A7"

def save(fig, name):
    out = FIG / "selected" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight", pad_inches=.05, facecolor="white")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight", pad_inches=.05, facecolor="white")
    plt.close(fig)

with (FIG / "data" / "F5_window_rmse_3seed.csv").open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.4,"axes.titlesize":9.2,
                     "axes.labelsize":8.6,"axes.spines.top":False,"axes.spines.right":False,
                     "axes.grid":True,"grid.alpha":.30,"grid.color":"#BFC7D1"})
order = ["iid_chopped", "ood-t_chopped", "ood-s_chopped", "ood-st_chopped"]
labels = ["A. IID", "B. OOD-T", "C. OOD-S", "D. OOD-ST"]
colors = [BLUE, ORANGE, GREEN, PURPLE]
fig, axes = plt.subplots(2, 2, figsize=(7.15, 4.45), sharex=True, sharey=True)
for ax, split, title, color in zip(axes.ravel(), order, labels, colors):
    rr = [r for r in rows if r["split"] == split]
    x = np.arange(4)
    y = np.array([float(r["rmse_mean"]) for r in rr])
    sd = np.array([float(r["rmse_sample_std_ddof1"]) for r in rr])
    ax.errorbar(x, y, yerr=sd, color=color, marker="o", ms=4.6, lw=1.55,
                capsize=2.5, elinewidth=1.0)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xticks(x, ["1–5", "6–10", "11–15", "16–20"])
    ax.set_ylim(.075, .191)
    ax.grid(axis="x", visible=False)
axes[0,0].set_ylabel("RMSE (NDVI)")
axes[1,0].set_ylabel("RMSE (NDVI)")
axes[1,0].set_xlabel("forecast-step window")
axes[1,1].set_xlabel("forecast-step window")
fig.subplots_adjust(left=.10, right=.985, top=.97, bottom=.12, hspace=.28, wspace=.18)
save(fig, "图5_时距与分布偏移_最终")
