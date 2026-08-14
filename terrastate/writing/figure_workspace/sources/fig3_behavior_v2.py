#!/usr/bin/env python3
"""Generate TerraState Figure 3 v2 from frozen Q2/Q3 JSON records.

This script:
  * reads paired Q2 estimates and frozen bootstrap intervals directly;
  * reads all 84 Q3 paired rows directly;
  * never reruns evaluation, filters samples, or hard-codes plotted values;
  * validates the current source files against the frozen results ledger;
  * writes SVG, vector PDF, 300-dpi PNG, grayscale, and paper-scale previews.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/terrastate_fig3_mplconfig")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from PIL import Image


FIGURE_WORKSPACE = Path(__file__).resolve().parents[1]
PROJECT_ROOT = FIGURE_WORKSPACE.parents[1]

VAL_Q2 = (
    PROJECT_ROOT
    / "TerraState_AAAI27/evidence_workspace/raw/release/"
    / "val_q2_state_contract_exclusive.json"
)
OODT_Q2 = (
    PROJECT_ROOT
    / "TerraState_AAAI27/evidence_workspace/raw/release/"
    / "oodt_q1q2_state_contract_exclusive.json"
)
Q3_RECORD = (
    PROJECT_ROOT
    / "TerraState_AAAI27/evidence_workspace/raw/release/"
    / "q3_extreme_state_audit.json"
)
RESULTS_LEDGER = (
    PROJECT_ROOT / "TerraState_AAAI27/evidence_workspace/results_ledger.json"
)

SVG_OUTPUT = FIGURE_WORKSPACE / "source/fig3_behavior_v2.svg"
PDF_OUTPUT = FIGURE_WORKSPACE / "export/fig3_behavior_v2.pdf"
PNG_OUTPUT = FIGURE_WORKSPACE / "export/fig3_behavior_v2.png"
GRAY_OUTPUT = FIGURE_WORKSPACE / "qa/fig3_behavior_v2_grayscale.png"
PAPERSCALE_OUTPUT = FIGURE_WORKSPACE / "qa/fig3_behavior_v2_paperscale.png"

EXPECTED_Q3_PAIRS = 84
EXPECTED_DONOR_DELTA = 0.002565468112672014
EXPECTED_MEAN_DELTA = 0.011261332329706334

INK = "#202124"
GRID = "#D5D9DE"
ZERO = "#7B8087"
STATE = "#D55E00"  # Okabe-Ito vermillion
SUPPORT = "#6C757D"
DONOR = "#0072B2"  # Okabe-Ito blue
MEAN = "#009E73"  # Okabe-Ito bluish green


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_finite(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} is missing or non-finite: {value!r}")
    return float(value)


def ledger_hashes(ledger: dict[str, Any]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for record in ledger.get("records", []):
        raw_path = record.get("raw_json_absolute_path")
        raw_hash = record.get("raw_json_sha256")
        if raw_path and raw_hash:
            hashes[str(Path(raw_path).resolve())] = str(raw_hash)
    return hashes


def verify_frozen_sources(ledger: dict[str, Any]) -> None:
    expected = ledger_hashes(ledger)
    for path in (VAL_Q2, OODT_Q2, Q3_RECORD):
        resolved = str(path.resolve())
        if resolved not in expected:
            raise ValueError(f"source is absent from frozen results ledger: {path}")
        observed = sha256(path)
        if observed != expected[resolved]:
            raise ValueError(
                f"frozen source hash mismatch for {path}: "
                f"ledger={expected[resolved]}, observed={observed}"
            )


def extract_q2(record: dict[str, Any], split: str) -> dict[str, Any]:
    if record.get("status") != "COMPLETE":
        raise ValueError(f"{split}: Q2 record is not COMPLETE")
    q2 = record["Q2_load_bearing"]
    definitions = {
        "state_removal": q2["closure_cut_alpha0"]["bootstrap95"],
        "transition_identity": q2["transition_identity"]["bootstrap95"],
    }
    extracted: dict[str, Any] = {"split": split}
    for key, block in definitions.items():
        mean = require_finite(block.get("mean"), f"{split}.{key}.mean")
        low = require_finite(block.get("ci_low"), f"{split}.{key}.ci_low")
        high = require_finite(block.get("ci_high"), f"{split}.{key}.ci_high")
        n = int(block.get("n", 0))
        if not (low <= mean <= high):
            raise ValueError(f"{split}.{key}: estimate is outside its CI")
        if n <= 0:
            raise ValueError(f"{split}.{key}: invalid paired sample count {n}")
        extracted[key] = {"mean": mean, "low": low, "high": high, "n": n}
    return extracted


def extract_q3(record: dict[str, Any]) -> dict[str, Any]:
    rows = record["models"]["exclusive"]["q3_donor_rows"]
    if int(record.get("n_pairs", -1)) != EXPECTED_Q3_PAIRS:
        raise ValueError(f"top-level n_pairs is not {EXPECTED_Q3_PAIRS}")
    if len(rows) != EXPECTED_Q3_PAIRS:
        raise ValueError(f"q3_donor_rows has {len(rows)} rows, expected 84")

    fields = ("loss_e_actual", "loss_e_donor", "loss_e_mean")
    arrays: dict[str, np.ndarray] = {}
    for field in fields:
        values = [
            require_finite(row.get(field), f"q3_donor_rows[{i}].{field}")
            for i, row in enumerate(rows)
        ]
        arrays[field] = np.asarray(values, dtype=float)

    donor_delta = float(np.mean(arrays["loss_e_donor"] - arrays["loss_e_actual"]))
    mean_delta = float(np.mean(arrays["loss_e_mean"] - arrays["loss_e_actual"]))
    fidelity = record["models"]["exclusive"]["q3_donor_fidelity"]["endpoint_fidelity"]
    frozen_donor = require_finite(
        fidelity["extreme_actual_vs_donor"]["delta_loss_mean"],
        "frozen donor delta",
    )
    frozen_mean = require_finite(
        fidelity["extreme_actual_vs_mean"]["delta_loss_mean"],
        "frozen normalized-mean delta",
    )
    for name, observed, frozen, expected in (
        ("donor", donor_delta, frozen_donor, EXPECTED_DONOR_DELTA),
        ("normalized mean", mean_delta, frozen_mean, EXPECTED_MEAN_DELTA),
    ):
        if not math.isclose(observed, frozen, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"{name} row mean {observed} != frozen mean {frozen}")
        if not math.isclose(observed, expected, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"{name} row mean {observed} != expected frozen value {expected}")

    return {
        **arrays,
        "n": len(rows),
        "donor_delta": donor_delta,
        "mean_delta": mean_delta,
        "donor_above": int(
            np.sum(arrays["loss_e_donor"] > arrays["loss_e_actual"])
        ),
        "mean_above": int(np.sum(arrays["loss_e_mean"] > arrays["loss_e_actual"])),
        "donor_equal": int(
            np.sum(arrays["loss_e_donor"] == arrays["loss_e_actual"])
        ),
        "mean_equal": int(np.sum(arrays["loss_e_mean"] == arrays["loss_e_actual"])),
        "unique_extreme_keys": len({row["e_key"] for row in rows}),
    }


def configure_style() -> None:
    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "axes.titlesize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.5,
            "axes.linewidth": 0.75,
            "lines.linewidth": 0.9,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.facecolor": "white",
            "savefig.edgecolor": "white",
        }
    )


def draw_q2(ax: plt.Axes, q2_rows: list[dict[str, Any]]) -> None:
    y_base = np.asarray([1.0, 0.0])
    offset = 0.105

    state_mean = np.asarray([row["state_removal"]["mean"] for row in q2_rows])
    state_low = np.asarray([row["state_removal"]["low"] for row in q2_rows])
    state_high = np.asarray([row["state_removal"]["high"] for row in q2_rows])
    tid_mean = np.asarray([row["transition_identity"]["mean"] for row in q2_rows])
    tid_low = np.asarray([row["transition_identity"]["low"] for row in q2_rows])
    tid_high = np.asarray([row["transition_identity"]["high"] for row in q2_rows])

    ax.axvline(0.0, color=ZERO, linestyle=(0, (2, 2)), linewidth=0.8, zorder=0)
    ax.errorbar(
        state_mean,
        y_base + offset,
        xerr=np.vstack((state_mean - state_low, state_high - state_mean)),
        fmt="o",
        markersize=5.6,
        markerfacecolor=STATE,
        markeredgecolor=STATE,
        ecolor=STATE,
        elinewidth=1.25,
        capsize=2.3,
        capthick=1.0,
        zorder=3,
    )
    ax.errorbar(
        tid_mean,
        y_base - offset,
        xerr=np.vstack((tid_mean - tid_low, tid_high - tid_mean)),
        fmt="D",
        markersize=4.0,
        markerfacecolor="white",
        markeredgecolor=SUPPORT,
        markeredgewidth=0.9,
        ecolor=SUPPORT,
        elinewidth=0.85,
        capsize=1.9,
        capthick=0.75,
        alpha=0.78,
        zorder=2,
    )

    ax.set_yticks(y_base, ["Validation", "OOD-t"])
    ax.set_ylim(-0.55, 1.55)
    ax.set_xlim(-0.001, 0.035)
    ax.set_xticks([0.0, 0.01, 0.02, 0.03])
    ax.set_xlabel("Mean paired per-minicube R² loss")
    ax.set_title("(a) Q2 · State contribution", loc="left", fontweight="bold", pad=23)
    ax.grid(axis="x", color=GRID, linewidth=0.55, linestyle=(0, (2, 2)), zorder=0)

    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            color=STATE,
            markerfacecolor=STATE,
            markersize=5.2,
            label="State removal",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            linestyle="none",
            color=SUPPORT,
            markerfacecolor="white",
            markersize=4.0,
            label="T→I (support)",
        ),
    ]
    ax.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.0, 1.07),
        frameon=False,
        ncol=2,
        handletextpad=0.35,
        columnspacing=0.75,
        borderaxespad=0.0,
    )


def draw_scatter(
    ax: plt.Axes,
    x: np.ndarray,
    y: np.ndarray,
    limit: float,
    color: str,
    title: str,
    ylabel: str,
    above: int,
) -> None:
    ax.plot(
        [0.0, limit],
        [0.0, limit],
        color=ZERO,
        linestyle=(0, (3, 2)),
        linewidth=0.85,
        zorder=1,
    )
    ax.scatter(
        x,
        y,
        s=15,
        c=color,
        alpha=0.68,
        edgecolors="white",
        linewidths=0.28,
        zorder=2,
    )
    ax.set_xlim(0.0, limit)
    ax.set_ylim(0.0, limit)
    ticks = np.linspace(0.0, limit, 4)
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xlabel("Actual-weather window MSE")
    ax.set_ylabel(ylabel)
    ax.set_title(
        title,
        loc="left",
        fontweight="bold",
        fontsize=8.0,
        pad=4,
        linespacing=0.92,
    )
    ax.set_aspect("equal", adjustable="box")
    ax.grid(color=GRID, linewidth=0.45, linestyle=(0, (2, 2)), zorder=0)
    ax.text(
        0.04,
        0.94,
        f"{above}/{len(x)} above y=x",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.5,
        color=INK,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0, "alpha": 0.88},
    )
    ax.text(
        0.78,
        0.82,
        "y=x",
        transform=ax.transAxes,
        rotation=45,
        fontsize=7.5,
        color=ZERO,
        ha="center",
        va="center",
    )


def paper_scale_preview(png_path: Path, output: Path) -> None:
    page_dpi = 150
    page = Image.new("RGB", (int(8.5 * page_dpi), int(11 * page_dpi)), "white")
    with Image.open(png_path) as image:
        image = image.convert("RGB")
        final_width = int(7.0 * page_dpi)
        final_height = round(image.height * final_width / image.width)
        image = image.resize((final_width, final_height), Image.Resampling.LANCZOS)
        x = round((page.width - final_width) / 2)
        y = int(0.8 * page_dpi)
        page.paste(image, (x, y))
    page.save(output, dpi=(page_dpi, page_dpi), optimize=True)


def save_outputs(fig: plt.Figure) -> None:
    SVG_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PDF_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    GRAY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SVG_OUTPUT, format="svg")
    fig.savefig(PDF_OUTPUT, format="pdf")
    fig.savefig(PNG_OUTPUT, format="png", dpi=300)
    with Image.open(PNG_OUTPUT) as image:
        gray = image.convert("L").convert("RGB")
        gray.save(GRAY_OUTPUT, dpi=(300, 300), optimize=True)
    paper_scale_preview(PNG_OUTPUT, PAPERSCALE_OUTPUT)


def main() -> None:
    ledger = read_json(RESULTS_LEDGER)
    verify_frozen_sources(ledger)
    q2_rows = [
        extract_q2(read_json(VAL_Q2), "Validation"),
        extract_q2(read_json(OODT_Q2), "OOD-t"),
    ]
    q3 = extract_q3(read_json(Q3_RECORD))

    configure_style()
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(7.0, 2.55),
        gridspec_kw={"width_ratios": [1.12, 1.0, 1.0]},
    )
    fig.subplots_adjust(
        left=0.085,
        right=0.985,
        bottom=0.245,
        top=0.825,
        wspace=0.39,
    )

    draw_q2(axes[0], q2_rows)
    shared_max = max(
        float(np.max(q3["loss_e_actual"])),
        float(np.max(q3["loss_e_donor"])),
        float(np.max(q3["loss_e_mean"])),
    )
    shared_limit = math.ceil(shared_max / 0.02) * 0.02
    draw_scatter(
        axes[1],
        q3["loss_e_actual"],
        q3["loss_e_donor"],
        shared_limit,
        DONOR,
        "(b) Actual vs.\nmatched-donor\nweather",
        "Matched-donor window MSE",
        q3["donor_above"],
    )
    draw_scatter(
        axes[2],
        q3["loss_e_actual"],
        q3["loss_e_mean"],
        shared_limit,
        MEAN,
        "(c) Actual vs.\nnormalized-mean\nweather",
        "Normalized-mean window MSE",
        q3["mean_above"],
    )
    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(direction="out", length=2.7, width=0.7, colors=INK)
        ax.xaxis.label.set_color(INK)
        ax.yaxis.label.set_color(INK)
        ax.title.set_color(INK)

    save_outputs(fig)
    plt.close(fig)

    summary = {
        "q2": q2_rows,
        "q3_n": q3["n"],
        "q3_unique_extreme_keys": q3["unique_extreme_keys"],
        "donor_mean_delta": q3["donor_delta"],
        "mean_weather_mean_delta": q3["mean_delta"],
        "donor_above_diagonal": q3["donor_above"],
        "mean_weather_above_diagonal": q3["mean_above"],
        "donor_equal_diagonal": q3["donor_equal"],
        "mean_weather_equal_diagonal": q3["mean_equal"],
        "shared_scatter_limit": shared_limit,
        "outputs": [
            str(SVG_OUTPUT),
            str(PDF_OUTPUT),
            str(PNG_OUTPUT),
            str(GRAY_OUTPUT),
            str(PAPERSCALE_OUTPUT),
        ],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
