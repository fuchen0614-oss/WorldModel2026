#!/usr/bin/env python3
"""Generate Revision-2 Figure 3 from the frozen aggregate-effect CSV.

The script reads all experimental values from data/fig3_aggregate_effects.csv.
It does not run evaluation, reconstruct per-cube observations, or contain
hard-coded final estimates.
"""

from __future__ import annotations

import csv
import hashlib
import math
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1].resolve()
INPUT = ROOT / "data" / "fig3_aggregate_effects.csv"
OUTPUT = ROOT / "source" / "fig3_behavior.svg"

INK = "#202833"
GRAY = "#66717c"
LIGHT = "#c4cad0"
ORANGE = "#d55e00"
PURPLE = "#6f5aa8"
ORANGE_FILL = "#fff3e8"
PURPLE_FILL = "#f1eff9"

REQUIRED = {
    "panel",
    "split_or_control",
    "intervention",
    "metric",
    "estimate",
    "ci_low",
    "ci_high",
    "ci_unit",
    "n",
    "source_record",
    "source_record_sha256",
}


def read_and_validate() -> list[dict[str, str]]:
    with INPUT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("aggregate-effect CSV contains no rows")
    missing = REQUIRED - set(rows[0])
    if missing:
        raise ValueError(f"missing aggregate fields: {sorted(missing)}")
    for row in rows:
        values = [float(row[key]) for key in ("estimate", "ci_low", "ci_high")]
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"non-finite estimate or CI in {row}")
        estimate, low, high = values
        if low > estimate or estimate > high:
            raise ValueError(f"estimate outside CI in {row}")
        if int(row["n"]) <= 0:
            raise ValueError(f"non-positive sample count in {row}")
    verified_sources: dict[str, str] = {}
    for row in rows:
        source_record = row["source_record"]
        expected_hash = row["source_record_sha256"]
        if source_record in verified_sources:
            if verified_sources[source_record] != expected_hash:
                raise ValueError(f"conflicting hashes for {source_record}")
            continue
        source_path = (WORKSPACE / source_record).resolve()
        if not source_path.is_relative_to(WORKSPACE):
            raise ValueError(f"frozen source path leaves allowed workspace: {source_path}")
        if not source_path.is_file():
            raise ValueError(f"frozen source record is absent: {source_path}")
        observed_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if observed_hash != expected_hash:
            raise ValueError(
                f"frozen source hash mismatch for {source_record}: "
                f"expected {expected_hash}, observed {observed_hash}"
            )
        verified_sources[source_record] = expected_hash

    q2 = [row for row in rows if row["panel"] == "q2"]
    q3 = [row for row in rows if row["panel"] == "q3"]
    if len(q2) != 4 or len(q3) != 2:
        raise ValueError(f"expected four Q2 and two Q3 rows, found {len(q2)} and {len(q3)}")
    if {row["metric"] for row in q2} != {"paired_mean_delta_r2"}:
        raise ValueError("Q2 rows must use paired_mean_delta_r2")
    if {row["metric"] for row in q3} != {"control_minus_actual_delta_loss"}:
        raise ValueError("Q3 rows must use control_minus_actual_delta_loss")
    if {row["intervention"] for row in q3} != {"Control loss minus actual loss"}:
        raise ValueError("Q3 effect direction must be control loss minus actual loss")
    return rows


def scale(value: float, low: float, high: float, x0: float, x1: float) -> float:
    return x0 + (value - low) / (high - low) * (x1 - x0)


def tick_label(value: float) -> str:
    if value == 0:
        return "0"
    return f"{value:.3f}".rstrip("0")


def axis(
    x0: float,
    x1: float,
    y: float,
    low: float,
    high: float,
    ticks: list[float],
    label: str,
) -> str:
    parts = [f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{INK}" stroke-width="4"/>']
    for value in ticks:
        xx = scale(value, low, high, x0, x1)
        parts.append(f'<line x1="{xx:.2f}" y1="{y}" x2="{xx:.2f}" y2="{y+12}" stroke="{INK}" stroke-width="3"/>')
        parts.append(
            f'<text class="tick" text-anchor="middle" x="{xx:.2f}" y="{y+42}">{tick_label(value)}</text>'
        )
    parts.append(f'<text class="small" text-anchor="middle" x="{(x0+x1)/2}" y="{y+86}">{escape(label)}</text>')
    return "".join(parts)


def interval(
    row: dict[str, str],
    y: float,
    low: float,
    high: float,
    x0: float,
    x1: float,
    color: str,
    filled: bool,
    shape: str,
) -> str:
    estimate = scale(float(row["estimate"]), low, high, x0, x1)
    ci_low = scale(float(row["ci_low"]), low, high, x0, x1)
    ci_high = scale(float(row["ci_high"]), low, high, x0, x1)
    fill = color if filled else "#ffffff"
    point = (
        f'<circle cx="{estimate:.2f}" cy="{y}" r="11" fill="{fill}" stroke="{color}" stroke-width="5"/>'
        if shape == "circle"
        else f'<rect x="{estimate-11:.2f}" y="{y-11:.2f}" width="22" height="22" '
        f'fill="{fill}" stroke="{color}" stroke-width="5"/>'
    )
    return (
        f'<line x1="{ci_low:.2f}" y1="{y}" x2="{ci_high:.2f}" y2="{y}" stroke="{color}" stroke-width="7"/>'
        f'<line x1="{ci_low:.2f}" y1="{y-12}" x2="{ci_low:.2f}" y2="{y+12}" stroke="{color}" stroke-width="4"/>'
        f'<line x1="{ci_high:.2f}" y1="{y-12}" x2="{ci_high:.2f}" y2="{y+12}" stroke="{color}" stroke-width="4"/>'
        + point
    )


def q2_panel(rows: list[dict[str, str]]) -> str:
    order = [
        ("Validation", "State contribution ablation", "Validation · state ablation", True),
        ("Validation", "Transition to identity", "Validation · T → I", False),
        ("Temporal shift", "State contribution ablation", "OOD-t · state ablation", True),
        ("Temporal shift", "Transition to identity", "OOD-t · T → I", False),
    ]
    indexed = {(row["split_or_control"], row["intervention"]): row for row in rows}
    x, y, width, height = 20, 20, 1010, 590
    x0, x1 = x + 400, x + width - 45
    low, high = 0.0, 0.035
    ys = [y + 155, y + 245, y + 355, y + 445]
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="22" fill="#fff" stroke="{LIGHT}" stroke-width="4"/>',
        f'<text class="heading" x="{x+28}" y="{y+58}">(a) Q2 · state-path interventions</text>',
        f'<text class="small" x="{x+28}" y="{y+102}">paired 95% bootstrap confidence intervals</text>',
    ]
    for (split, intervention, label, filled), yy in zip(order, ys):
        row = indexed[(split, intervention)]
        parts.append(f'<text class="small" text-anchor="end" x="{x0-24}" y="{yy+11}">{escape(label)}</text>')
        parts.append(interval(row, yy, low, high, x0, x1, ORANGE, filled, "circle"))
    parts.append(
        axis(
            x0,
            x1,
            y + 485,
            low,
            high,
            [0.0, 0.01, 0.02, 0.03],
            "paired mean forecast-skill loss (ΔR²)",
        )
    )
    return "".join(parts)


def q3_panel(rows: list[dict[str, str]]) -> str:
    order = [
        ("Matched donor", "matched donor", True),
        ("Normalized mean", "normalized mean", False),
    ]
    indexed = {row["split_or_control"]: row for row in rows}
    x, y, width, height = 1050, 20, 1030, 590
    x0, x1 = x + 345, x + width - 45
    low, high = 0.0, 0.02
    ys = [y + 215, y + 355]
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="22" fill="#fff" stroke="{LIGHT}" stroke-width="4"/>',
        f'<text class="heading" x="{x+28}" y="{y+58}">(b) Q3 · weather replacements</text>',
        f'<text class="small" x="{x+28}" y="{y+102}">geographic-cluster 95% confidence intervals</text>',
        f'<text class="small" x="{x+28}" y="{y+145}">reference: actual future weather</text>',
    ]
    for (control, label, filled), yy in zip(order, ys):
        row = indexed[control]
        parts.append(f'<text class="small" text-anchor="end" x="{x0-24}" y="{yy+11}">{escape(label)}</text>')
        parts.append(interval(row, yy, low, high, x0, x1, PURPLE, filled, "square"))
    parts.append(axis(x0, x1, y + 445, low, high, [0.0, 0.005, 0.01, 0.015, 0.02], "endpoint-loss increase vs actual"))
    return "".join(parts)


def main() -> None:
    rows = read_and_validate()
    q2 = [row for row in rows if row["panel"] == "q2"]
    q3 = [row for row in rows if row["panel"] == "q3"]
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="7in" height="2.10in" viewBox="0 0 2100 630">
  <style>
    .heading {{ font-family: Arial, Helvetica, sans-serif; font-size: 38px; font-weight: 700; fill: {INK}; }}
    .small {{ font-family: Arial, Helvetica, sans-serif; font-size: 33px; fill: {INK}; }}
    .tick {{ font-family: Arial, Helvetica, sans-serif; font-size: 33px; fill: {INK}; }}
  </style>
  <rect width="2100" height="630" fill="#fff"/>
  <g id="q2_aggregate_effects">{q2_panel(q2)}</g>
  <g id="q3_aggregate_effects">{q3_panel(q3)}</g>
</svg>
"""
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} from {INPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
