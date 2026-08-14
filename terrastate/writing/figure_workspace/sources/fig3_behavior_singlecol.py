#!/usr/bin/env python3
"""Generate a single-column re-layout of the audited TerraState Figure 3 v2.

Only the panel geometry changes:
  * panel (a) spans the full 3.3-inch column width;
  * panels (b) and (c) share the lower row;
  * frozen data, intervals, samples, axes, colors, and markers are unchanged.

The audited v2 source and exports are imported but never overwritten.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


HERE = Path(__file__).resolve()
FIGURE_WORKSPACE = HERE.parents[1]
V2_SOURCE = HERE.with_name("fig3_behavior_v2.py")

SVG_OUTPUT = HERE.with_name("fig3_behavior_singlecol.svg")
PDF_OUTPUT = FIGURE_WORKSPACE / "export/fig3_behavior_singlecol.pdf"
PNG_OUTPUT = FIGURE_WORKSPACE / "export/fig3_behavior_singlecol.png"
GRAY_OUTPUT = FIGURE_WORKSPACE / "qa/fig3_behavior_singlecol_grayscale.png"
PAPERSCALE_OUTPUT = FIGURE_WORKSPACE / "qa/fig3_behavior_singlecol_paperscale.png"
QA_OUTPUT = FIGURE_WORKSPACE / "qa/fig3_behavior_singlecol_qa.json"

FIGURE_WIDTH_IN = 3.3
FIGURE_HEIGHT_IN = 3.50


def load_v2_module() -> Any:
    spec = importlib.util.spec_from_file_location("terrastate_fig3_v2", V2_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import audited v2 source: {V2_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_frozen_sources_portable(base: Any, ledger: dict[str, Any]) -> None:
    """Verify frozen inputs even when /mnt/data is mounted as /mnt/workspace."""
    expected_by_name: dict[str, str] = {}
    for record in ledger.get("records", []):
        raw_path = record.get("raw_json_absolute_path")
        raw_hash = record.get("raw_json_sha256")
        if not raw_path or not raw_hash:
            continue
        name = Path(raw_path).name
        previous = expected_by_name.get(name)
        if previous is not None and previous != str(raw_hash):
            raise ValueError(f"conflicting ledger hashes for {name}")
        expected_by_name[name] = str(raw_hash)

    for path in (base.VAL_Q2, base.OODT_Q2, base.Q3_RECORD):
        expected = expected_by_name.get(path.name)
        if expected is None:
            raise ValueError(f"source is absent from frozen results ledger: {path.name}")
        observed = base.sha256(path)
        if observed != expected:
            raise ValueError(
                f"frozen source hash mismatch for {path.name}: "
                f"ledger={expected}, observed={observed}"
            )


def draw_scatter_singlecol(
    base: Any,
    ax: plt.Axes,
    x: np.ndarray,
    y: np.ndarray,
    limit: float,
    color: str,
    title: str,
    ylabel: str,
    above: int,
    *,
    right_axis: bool,
) -> None:
    """Draw the same v2 scatter semantics in a narrow native-size panel."""
    ax.plot(
        [0.0, limit],
        [0.0, limit],
        color=base.ZERO,
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
    tick_labels = [f"{tick:.2f}" for tick in ticks]
    # The adjacent inner endpoints encode the same shared range. Suppressing
    # one duplicate label on each panel prevents a 0.12/0.00 collision while
    # retaining both endpoints across the paired lower row.
    if right_axis:
        tick_labels[0] = ""
    else:
        tick_labels[-1] = ""
    ax.set_xticklabels(tick_labels)
    ax.set_ylabel(ylabel, labelpad=3.2)
    ax.set_title(
        title,
        loc="left",
        fontweight="bold",
        fontsize=8.0,
        pad=4,
        linespacing=0.92,
    )
    ax.set_aspect("equal", adjustable="box")
    ax.grid(
        color=base.GRID,
        linewidth=0.45,
        linestyle=(0, (2, 2)),
        zorder=0,
    )
    ax.text(
        0.04,
        0.94,
        f"{above}/{len(x)}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.5,
        color=base.INK,
        bbox={
            "facecolor": "white",
            "edgecolor": "none",
            "pad": 0.8,
            "alpha": 0.88,
        },
    )
    ax.text(
        0.76,
        0.79,
        "y=x",
        transform=ax.transAxes,
        rotation=45,
        fontsize=7.5,
        color=base.ZERO,
        ha="center",
        va="center",
    )
    if right_axis:
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.spines["left"].set_visible(False)
        ax.spines["right"].set_visible(True)
    else:
        ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.tick_params(direction="out", length=2.7, width=0.7, colors=base.INK)
    ax.xaxis.label.set_color(base.INK)
    ax.yaxis.label.set_color(base.INK)
    ax.title.set_color(base.INK)


def save_outputs(fig: plt.Figure) -> None:
    for path in (
        SVG_OUTPUT,
        PDF_OUTPUT,
        PNG_OUTPUT,
        GRAY_OUTPUT,
        PAPERSCALE_OUTPUT,
        QA_OUTPUT,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SVG_OUTPUT, format="svg")
    fig.savefig(PDF_OUTPUT, format="pdf")
    fig.savefig(PNG_OUTPUT, format="png", dpi=300)
    with Image.open(PNG_OUTPUT) as image:
        image.convert("L").convert("RGB").save(
            GRAY_OUTPUT,
            dpi=(300, 300),
            optimize=True,
        )
        page_dpi = 200
        page = Image.new(
            "RGB",
            (round(8.5 * page_dpi), round(11 * page_dpi)),
            "white",
        )
        final_width = round(FIGURE_WIDTH_IN * page_dpi)
        final_height = round(image.height * final_width / image.width)
        scaled = image.convert("RGB").resize(
            (final_width, final_height),
            Image.Resampling.LANCZOS,
        )
        page.paste(scaled, (round(0.75 * page_dpi), round(0.8 * page_dpi)))
        page.save(PAPERSCALE_OUTPUT, dpi=(page_dpi, page_dpi), optimize=True)


def main() -> None:
    base = load_v2_module()
    ledger = base.read_json(base.RESULTS_LEDGER)
    verify_frozen_sources_portable(base, ledger)
    q2_rows = [
        base.extract_q2(base.read_json(base.VAL_Q2), "Validation"),
        base.extract_q2(base.read_json(base.OODT_Q2), "OOD-t"),
    ]
    q3 = base.extract_q3(base.read_json(base.Q3_RECORD))

    base.configure_style()
    fig = plt.figure(figsize=(FIGURE_WIDTH_IN, FIGURE_HEIGHT_IN))
    # Native single-column geometry. Separate axes rectangles allow the
    # full-width Q2 panel and the narrow scatter panels to have independent
    # outer margins without reducing their physical font sizes.
    ax_q2 = fig.add_axes([0.205, 0.600, 0.755, 0.267])
    ax_donor = fig.add_axes([0.160, 0.140, 0.300, 0.264])
    ax_mean = fig.add_axes([0.540, 0.140, 0.300, 0.264])

    base.draw_q2(ax_q2, q2_rows)
    shared_max = max(
        float(np.max(q3["loss_e_actual"])),
        float(np.max(q3["loss_e_donor"])),
        float(np.max(q3["loss_e_mean"])),
    )
    shared_limit = math.ceil(shared_max / 0.02) * 0.02
    draw_scatter_singlecol(
        base,
        ax_donor,
        q3["loss_e_actual"],
        q3["loss_e_donor"],
        shared_limit,
        base.DONOR,
        "(b) Actual vs.\nmatched donor",
        "Matched-donor window MSE",
        q3["donor_above"],
        right_axis=False,
    )
    draw_scatter_singlecol(
        base,
        ax_mean,
        q3["loss_e_actual"],
        q3["loss_e_mean"],
        shared_limit,
        base.MEAN,
        "(c) Actual vs.\nnormalized mean",
        "Normalized-mean window MSE",
        q3["mean_above"],
        right_axis=True,
    )
    ax_q2.spines["top"].set_visible(False)
    ax_q2.spines["right"].set_visible(False)
    ax_q2.tick_params(direction="out", length=2.7, width=0.7, colors=base.INK)
    ax_q2.xaxis.label.set_color(base.INK)
    ax_q2.yaxis.label.set_color(base.INK)
    ax_q2.title.set_color(base.INK)
    ax_donor.set_xlabel("")
    ax_mean.set_xlabel("")
    fig.text(
        0.5,
        0.035,
        "Actual-weather window MSE",
        ha="center",
        va="bottom",
        fontsize=8.0,
        color=base.INK,
    )

    save_outputs(fig)
    plt.close(fig)

    qa = {
        "layout_only_change": True,
        "figure_size_inches": [FIGURE_WIDTH_IN, FIGURE_HEIGHT_IN],
        "q2": q2_rows,
        "q3_n": q3["n"],
        "q3_unique_extreme_keys": q3["unique_extreme_keys"],
        "missing_or_nonfinite_values": 0,
        "donor_mean_delta": q3["donor_delta"],
        "mean_weather_mean_delta": q3["mean_delta"],
        "donor_above_diagonal": q3["donor_above"],
        "mean_weather_above_diagonal": q3["mean_above"],
        "donor_equal_diagonal": q3["donor_equal"],
        "mean_weather_equal_diagonal": q3["mean_equal"],
        "shared_scatter_limit": shared_limit,
        "source_hashes": {
            str(path): base.sha256(path)
            for path in (
                base.VAL_Q2,
                base.OODT_Q2,
                base.Q3_RECORD,
                base.RESULTS_LEDGER,
                V2_SOURCE,
            )
        },
        "output_hashes": {
            str(path): base.sha256(path)
            for path in (
                SVG_OUTPUT,
                PDF_OUTPUT,
                PNG_OUTPUT,
                GRAY_OUTPUT,
                PAPERSCALE_OUTPUT,
            )
        },
    }
    QA_OUTPUT.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
