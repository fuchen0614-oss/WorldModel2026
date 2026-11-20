"""Build the two paper-width experimental figures from frozen A24 sources.

No model execution, training, interpolation, or manipulation of prediction pixels.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sources"
INK = "#23313a"
MUTED = "#617078"
BLUE = "#287793"
ORANGE = "#b87549"
GRID = "#d3dadc"
INVALID = "#c4c9cb"
NDVI_LIMITS = (-0.6, 0.9)
ERROR_LIMITS = (0.0, 0.45)

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 7.1,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK,
        "xtick.color": MUTED,
        "ytick.color": INK,
    }
)


def save(fig: plt.Figure, folder: str, stem: str) -> None:
    out = ROOT / folder
    out.mkdir(exist_ok=True)
    fig.savefig(out / f"{stem}.png", dpi=420)
    fig.savefig(out / f"{stem}.pdf")
    plt.close(fig)


def image(ax: plt.Axes, pixels: np.ndarray, mask: np.ndarray, cmap, vmin, vmax) -> None:
    ax.imshow(
        np.ma.array(pixels, mask=~mask),
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        interpolation="nearest",
        origin="upper",
        aspect="equal",
    )
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def figure3() -> None:
    with np.load(SRC / "frames.npz") as z:
        data = {key: z[key].copy() for key in z.files}
    meta = json.loads((SRC / "original_metadata.json").read_text(encoding="utf-8"))
    target_index = 19  # zero-based future step 20, day 100
    continued_index = target_index - 10  # exported suffix steps 11-20
    assert len(meta["dates"]) == 20
    assert data["gt"].ndim == 2
    assert data["C0R_continued"].ndim == 2
    assert data["C1_continued"].ndim == 2
    mask = data["valid"].astype(bool)
    observed = data["gt"]
    assert mask.any()
    routes = [
        (
            "SpanWorld",
            data["C1_direct"],
            data["C1_continued"],
        ),
        (
            "Direct-endpoint\ncontrol",
            data["C0R_direct"],
            data["C0R_continued"],
        ),
    ]
    ndvi = plt.get_cmap("viridis").copy()
    ndvi.set_bad(INVALID)
    error = plt.get_cmap("magma").copy()
    error.set_bad(INVALID)
    heads = [
        "Observed",
        "Direct\nprediction",
        "Continued\nprediction",
        "Direct\nabsolute error",
        "Continued\nabsolute error",
    ]

    fig = plt.figure(figsize=(5.5, 2.55))
    xpos = [0.132, 0.307, 0.482, 0.657, 0.832]
    width = 0.155
    yrow = [0.540, 0.185]
    height = width * 5.5 / 2.55
    for x, head in zip(xpos, heads):
        fig.text(x + width / 2, 0.930, head, ha="center", va="center", fontsize=7.35, color=INK)
    metrics = []
    for row, (name, direct, continued) in enumerate(routes):
        fig.text(
            0.100,
            yrow[row] + height / 2,
            name,
            rotation=90,
            va="center",
            ha="center",
            fontsize=7.5,
            weight="bold",
            color=BLUE if row == 0 else ORANGE,
        )
        cards = [
            (observed, ndvi, *NDVI_LIMITS),
            (direct, ndvi, *NDVI_LIMITS),
            (continued, ndvi, *NDVI_LIMITS),
            (np.abs(direct - observed), error, *ERROR_LIMITS),
            (np.abs(continued - observed), error, *ERROR_LIMITS),
        ]
        for x, (pixels, cmap, lo, hi) in zip(xpos, cards):
            ax = fig.add_axes([x, yrow[row], width, height])
            image(ax, pixels, mask, cmap, lo, hi)
        metrics.append(
            {
                "model": name.replace("\n", " "),
                "direct_mse": float(np.mean((direct[mask] - observed[mask]) ** 2)),
                "continued_mse": float(np.mean((continued[mask] - observed[mask]) ** 2)),
                "direct_error_display_saturation_fraction": float(
                    np.mean(np.abs(direct[mask] - observed[mask]) > ERROR_LIMITS[1])
                ),
                "continued_error_display_saturation_fraction": float(
                    np.mean(np.abs(continued[mask] - observed[mask]) > ERROR_LIMITS[1])
                ),
            }
        )

    # Shared scales make all predictions and all errors mutually comparable.
    bar_ndvi = fig.add_axes([0.252, 0.092, 0.240, 0.023])
    bar_error = fig.add_axes([0.700, 0.092, 0.240, 0.023])
    fig.colorbar(
        ScalarMappable(norm=Normalize(*NDVI_LIMITS), cmap=ndvi),
        cax=bar_ndvi,
        orientation="horizontal",
        ticks=[-0.6, 0, 0.5, 0.9],
    )
    fig.colorbar(
        ScalarMappable(norm=Normalize(*ERROR_LIMITS), cmap=error),
        cax=bar_error,
        orientation="horizontal",
        ticks=[0, 0.15, 0.30, 0.45],
        extend="max",
        extendfrac=0.045,
    )
    for bar in (bar_ndvi, bar_error):
        bar.tick_params(labelsize=7.0, length=1.6, pad=1)
    fig.text(0.370, 0.143, "NDVI", fontsize=7.2, ha="center", color=INK)
    fig.text(0.820, 0.143, "Absolute NDVI error", fontsize=7.2, ha="center", color=INK)
    swatch = fig.add_axes([0.132, 0.092, 0.016, 0.023])
    swatch.set_facecolor(INVALID)
    swatch.set_xticks([])
    swatch.set_yticks([])
    for spine in swatch.spines.values():
        spine.set_visible(False)
    fig.text(0.153, 0.098, "Invalid", fontsize=7.0, va="center", color=MUTED)
    save(fig, "fig3", "fig3_prediction_routes_compact")

    audit = {
        "case_id_internal": meta["id"],
        "case_selection_internal": meta["selection"],
        "target_step": target_index + 1,
        "target_day": (target_index + 1) * 5,
        "target_date": meta["dates"][target_index],
        "continuation_from_day": 50,
        "pre_continuation_partition_days": [15, 35],
        "valid_pixels": int(mask.sum()),
        "total_pixels": int(mask.size),
        "coverage": float(mask.mean()),
        "ndvi_display_limits": NDVI_LIMITS,
        "absolute_error_display_limits": ERROR_LIMITS,
        "ndvi_display_saturation_fraction": {
            name: float(np.mean(data[name][mask] < NDVI_LIMITS[0]))
            + float(np.mean(data[name][mask] > NDVI_LIMITS[1]))
            for name, index in [
                ("gt", target_index),
                ("C1_direct", target_index),
                ("C1_continued", continued_index),
                ("C0R_direct", target_index),
                ("C0R_continued", continued_index),
            ]
        },
        "metrics": metrics,
        "metric_note": "Single target date; mean squared error over the identical valid-observation pixels. Display clipping never changes MSE.",
    }
    (ROOT / "fig3" / "fig3_case_metrics.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def figure4_data():
    with (SRC / "leaveout_q4_formal_iid2856_v1.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        held = {row["combo"]: row for row in csv.DictReader(handle)}
    order = [
        ("ep10|3-7", "15+35"),
        ("ep10|6-4", "30+20"),
        ("ep10|2-3-5", "10+15+25"),
        ("ep15|4-11", "20+55"),
        ("ep15|3-5-7", "15+25+35"),
        ("ep20|8-12", "40+60"),
        ("ep20|2-18", "10+90"),
        ("ep20|2-6-12", "10+30+60"),
        ("ep20|1-4-6-9", "5+20+30+45"),
    ]
    endpoints = [50] * 3 + [75] * 2 + [100] * 4
    top = []
    for (key, label), day in zip(order, endpoints):
        row = held[key]
        assert int(row["endpoint"]) * 5 == day
        top.append(
            {
                "combo": key,
                "partition_days": label,
                "endpoint_day": day,
                "n_eligible": int(row["n_eligible_cubes"]),
                "relative_change_pct": (float(row["composed_over_direct_ratio"]) - 1) * 100,
                "direct_pooled_mse": float(row["direct_pooled_mse"]),
                "partitioned_pooled_mse": float(row["composed_pooled_mse"]),
            }
        )
    assert [top[i]["n_eligible"] for i in [0, 3, 5]] == [1615, 1568, 1617]

    text = (SRC / "Table4B_state_intervention_corrected.md").read_text(encoding="utf-8")
    section = text.split("## 完整后缀 11–20", 1)[1].split("## 单终点 h10", 1)[0]
    states = []
    for line in section.splitlines():
        if not line.startswith("| ") or "主口径" not in line:
            continue
        fields = [item.strip() for item in line.strip().strip("|").split("|")]
        lo, hi = [float(value) for value in re.findall(r"-?\d+\.\d+", fields[4])]
        states.append(
            {
                "split": fields[0],
                "delta_mse": float(fields[3]),
                "ci_low": lo,
                "ci_high": hi,
                "n_receivers": int(fields[6]),
                "n_geo_groups": int(fields[7]),
            }
        )
    assert [row["split"] for row in states] == ["iid", "ood_t", "ood_s", "ood_st"]
    source = json.loads((SRC / "q3_extreme_state_audit.json").read_text(encoding="utf-8"))
    q3 = source["models"]["exclusive"]["q3_donor_fidelity"]["endpoint_fidelity"]
    weather = []
    for label, key in [
        ("Matched donor", "extreme_actual_vs_donor"),
        ("Normalized mean", "extreme_actual_vs_mean"),
    ]:
        value = q3[key]["geo_cluster_bootstrap"]
        weather.append(
            {
                "condition": label,
                "delta_mse": float(value["mean"]),
                "ci_low": float(value["ci_low"]),
                "ci_high": float(value["ci_high"]),
                "n_samples": int(value["n"]),
                "n_geo_groups": int(value["n_clusters"]),
            }
        )
    assert all(row["n_samples"] == 84 for row in weather)
    return top, states, weather


def figure4() -> None:
    top, states, weather = figure4_data()
    fig = plt.figure(figsize=(5.5, 2.65))
    a = fig.add_axes([0.225, 0.215, 0.230, 0.610])
    b = fig.add_axes([0.530, 0.270, 0.170, 0.530])
    c = fig.add_axes([0.775, 0.270, 0.210, 0.530])

    # Nine labeled rows preserve day-valued partitions without narrow x labels.
    yy = np.arange(8, -1, -1)
    partition_labels = [
        "[15,35]", "[30,20]", "[10,15,25]", "[20,55]", "[15,25,35]",
        "[40,60]", "[10,90]", "[10,30,60]", "[5,20,30,45]",
    ]
    values = np.array([row["relative_change_pct"] for row in top])
    a.scatter(values, yy, s=17, color=BLUE, zorder=3)
    a.axvline(0, color=MUTED, lw=0.8, zorder=1)
    a.axhline(5.5, color=GRID, lw=0.7)
    a.axhline(3.5, color=GRID, lw=0.7)
    a.set_xlim(-1.25, 2.9)
    a.set_ylim(-0.5, 8.5)
    a.set_xticks([-1, 0, 1, 2])
    a.set_yticks(yy, partition_labels)
    a.tick_params(axis="x", labelsize=7.0, length=2, pad=2)
    a.tick_params(axis="y", labelsize=7.0, length=0, pad=3)
    a.grid(axis="x", color=GRID, lw=0.45, zorder=0)
    a.spines[["top", "right", "left"]].set_visible(False)
    a.set_xlabel("Change vs direct (%)", fontsize=7.1, labelpad=2)
    fig.text(0.030, 0.965, "(a) Unseen partitions", fontsize=8.2, weight="bold", color=INK, va="top")
    for center, label in [(7, "50d"), (4.5, "75d"), (1.5, "100d")]:
        yfig = 0.215 + 0.610 * (center + 0.5) / 9
        fig.text(0.042, yfig, label, va="center", fontsize=7.0, weight="bold", color=MUTED)

    for ax in (b, c):
        ax.spines[["top", "right"]].set_visible(False)
        ax.axhline(0, color=MUTED, lw=0.8, zorder=1)
        ax.grid(axis="y", color=GRID, lw=0.45, zorder=0)
        ax.tick_params(axis="y", labelsize=7.0, length=2, pad=2)
        ax.tick_params(axis="x", labelsize=7.0, length=0, pad=2)
        ax.set_ylabel("ΔMSE", fontsize=7.0, labelpad=1)

    b.set_ylim(-0.0003, 0.00435)
    b.set_xlim(-0.5, 3.5)
    b.set_yticks([0, 0.002, 0.004], ["0", ".002", ".004"])
    b.set_xticks(range(4), ["IID", "OOD-T", "OOD-S", "OOD-ST"])
    plt.setp(b.get_xticklabels(), rotation=65, ha="right", rotation_mode="anchor")
    for index, row in enumerate(states):
        mean = row["delta_mse"]
        b.errorbar(
            index, mean,
            yerr=[[mean - row["ci_low"]], [row["ci_high"] - mean]],
            fmt="o", color=BLUE, capsize=2.1, elinewidth=1.0,
            markersize=4.0, zorder=3,
        )
    fig.text(0.500, 0.965, "(b) State\nreplacement", fontsize=8.1, weight="bold", color=INK, va="top")

    c.set_ylim(-0.001, 0.017)
    c.set_xlim(-0.5, 1.5)
    c.set_yticks([0, 0.005, 0.010, 0.015], ["0", ".005", ".010", ".015"])
    c.set_xticks([0, 1], ["Matched\ndonor", "Mean\nweather"])
    for index, row in enumerate(weather):
        mean = row["delta_mse"]
        c.errorbar(
            index, mean,
            yerr=[[mean - row["ci_low"]], [row["ci_high"] - mean]],
            fmt="s", color=ORANGE, capsize=2.1, elinewidth=1.0,
            markersize=4.0, zorder=3,
        )
    fig.text(0.745, 0.965, "(c) Weather\nreplacement", fontsize=8.1, weight="bold", color=INK, va="top")

    save(fig, "fig4", "fig4_partition_and_interventions_compact")
    (ROOT / "fig4" / "fig4_plot_values.json").write_text(
        json.dumps({"heldout_partitions": top, "state_replacement": states, "weather_replacement": weather}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    figure3()
    figure4()
