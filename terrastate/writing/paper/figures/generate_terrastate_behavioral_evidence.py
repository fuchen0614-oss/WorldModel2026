#!/usr/bin/env python3
"""Generate an editable TikZ Figure 3 from the frozen evidence CSV.

This script uses only the Python standard library. It performs no evaluation,
bootstrap, or statistical recomputation; it only maps recorded values to
coordinates in a standalone TikZ source.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "terrastate_behavioral_evidence.csv"
OUT_TEX = ROOT / "terrastate_behavioral_evidence.tex"

BLUE = "356787"
ORANGE = "A95B14"
PURPLE = "635694"
GRAY = "66717C"
LIGHT = "C8CDD2"
INK = "202833"


def read_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with DATA.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            parsed: dict[str, object] = dict(row)
            for key in ("estimate", "ci_low", "ci_high"):
                parsed[key] = float(row[key]) if row[key] else None
            rows.append(parsed)
    return rows


def sx(value: float, low: float, high: float, x0: float, x1: float) -> float:
    return x0 + (value - low) / (high - low) * (x1 - x0)


def interval(x: float, lo: float, hi: float, y: float, color: str, filled: bool) -> str:
    fill = f"c{color}" if filled else "white"
    return (
        rf"\draw[draw=c{color},line width=1.6pt] ({lo:.2f},{y:.2f}) -- ({hi:.2f},{y:.2f});"
        "\n"
        rf"\draw[draw=c{color},line width=1.2pt] ({lo:.2f},{y-4:.2f}) -- ({lo:.2f},{y+4:.2f});"
        "\n"
        rf"\draw[draw=c{color},line width=1.2pt] ({hi:.2f},{y-4:.2f}) -- ({hi:.2f},{y+4:.2f});"
        "\n"
        rf"\filldraw[draw=c{color},fill={fill},line width=1.3pt] ({x:.2f},{y:.2f}) circle (3.8pt);"
    )


def axis(x0: float, x1: float, y: float, ticks: list[tuple[float, str]], label: str) -> str:
    lines = [rf"\draw[draw=c{INK},line width=1.0pt] ({x0},{y}) -- ({x1},{y});"]
    for x, text in ticks:
        lines.append(rf"\draw[draw=c{INK},line width=0.8pt] ({x:.2f},{y-3}) -- ({x:.2f},{y+3});")
        lines.append(
            rf"\node[anchor=north,font=\fontsize{{15}}{{17}}\selectfont,text=c{INK}] "
            rf"at ({x:.2f},{y-5}) {{{text}}};"
        )
    lines.append(
        rf"\node[anchor=north,font=\fontsize{{17}}{{19}}\selectfont,text=c{INK}] "
        rf"at ({(x0+x1)/2:.2f},{y-27}) {{{label}}};"
    )
    return "\n".join(lines)


def main() -> None:
    rows = read_rows()
    q2 = [row for row in rows if row["panel"] == "q2"]
    q3_effect = [row for row in rows if row["panel"] == "q3_effect"]
    q3_skill = [row for row in rows if row["panel"] == "q3_skill"]

    body: list[str] = []

    # Panel backgrounds and labels.
    panels = [(18, 342), (350, 654), (662, 982)]
    for left, right in panels:
        body.append(
            rf"\draw[rounded corners=8pt,draw=c{LIGHT},line width=1.0pt,fill=white] "
            rf"({left},18) rectangle ({right},242);"
        )
    for letter, x in zip(("a", "b", "c"), (28, 360, 672)):
        body.append(
            rf"\node[anchor=north west,font=\bfseries\fontsize{{20}}{{23}}\selectfont,text=c{INK}] "
            rf"at ({x},232) {{({letter})}};"
        )

    # Panel (a): Q2 forest plot.
    x0a, x1a, low_a, high_a = 105.0, 326.0, -0.001, 0.035
    zero_a = sx(0.0, low_a, high_a, x0a, x1a)
    body.append(rf"\draw[draw=c{LIGHT},line width=1.0pt] ({zero_a:.2f},61) -- ({zero_a:.2f},216);")
    y_base = {"Validation": 174.0, "Temporal shift": 102.0}
    for split, y in y_base.items():
        body.append(
            rf"\node[anchor=east,font=\fontsize{{17}}{{19}}\selectfont,text=c{INK}] "
            rf"at (99,{y}) {{{split}}};"
        )
    for row in q2:
        primary = row["intervention"] == "State contribution ablation"
        y = y_base[str(row["split_or_control"])] + (8.0 if primary else -8.0)
        color = BLUE if primary else GRAY
        body.append(
            interval(
                sx(float(row["estimate"]), low_a, high_a, x0a, x1a),
                sx(float(row["ci_low"]), low_a, high_a, x0a, x1a),
                sx(float(row["ci_high"]), low_a, high_a, x0a, x1a),
                y,
                color,
                primary,
            )
        )
    ticks_a = [
        (sx(v, low_a, high_a, x0a, x1a), f"{v:.2f}") for v in (0.00, 0.01, 0.02, 0.03)
    ]
    body.append(axis(x0a, x1a, 55, ticks_a, r"forecast skill removed ($\Delta R^2$)"))
    body.append(
        rf"\filldraw[draw=c{BLUE},fill=c{BLUE}] (112,213) circle (3.5pt);"
        rf"\node[anchor=west,font=\fontsize{{15}}{{17}}\selectfont] at (121,213) {{state ablation}};"
    )
    body.append(
        rf"\filldraw[draw=c{GRAY},fill=white,line width=1.2pt] (234,213) circle (3.5pt);"
        rf"\node[anchor=west,font=\fontsize{{15}}{{17}}\selectfont] at (243,213) {{$T\!\rightarrow I$}};"
    )

    # Panel (b): Q3 loss effect forest plot.
    x0b, x1b, low_b, high_b = 445.0, 638.0, -0.0007, 0.0185
    zero_b = sx(0.0, low_b, high_b, x0b, x1b)
    body.append(rf"\draw[draw=c{LIGHT},line width=1.0pt] ({zero_b:.2f},61) -- ({zero_b:.2f},216);")
    y_effect = {"Matched control": 174.0, "Normalized mean": 102.0}
    for name, y in y_effect.items():
        body.append(
            rf"\node[anchor=east,font=\fontsize{{17}}{{19}}\selectfont,text=c{INK}] "
            rf"at (439,{y}) {{{name}}};"
        )
    for row in q3_effect:
        y = y_effect[str(row["split_or_control"])]
        body.append(
            interval(
                sx(float(row["estimate"]), low_b, high_b, x0b, x1b),
                sx(float(row["ci_low"]), low_b, high_b, x0b, x1b),
                sx(float(row["ci_high"]), low_b, high_b, x0b, x1b),
                y,
                PURPLE,
                True,
            )
        )
    ticks_b = [
        (sx(v, low_b, high_b, x0b, x1b), f"{v:.3f}") for v in (0.000, 0.005, 0.010, 0.015)
    ]
    body.append(axis(x0b, x1b, 55, ticks_b, "loss increase under control weather"))

    # Panel (c): separate R2 and RMSE strips for the Q3 subset.
    order = ["Actual weather", "Matched control", "Normalized mean"]
    colors = {"Actual weather": PURPLE, "Matched control": GRAY, "Normalized mean": LIGHT}
    r2 = {str(r["split_or_control"]): float(r["estimate"]) for r in q3_skill if r["metric"] == "r2"}
    rmse = {str(r["split_or_control"]): float(r["estimate"]) for r in q3_skill if r["metric"] == "rmse"}
    x0c, x1c = 700.0, 960.0

    ticks_r2 = [(sx(v, 0.52, 0.65, x0c, x1c), f"{v:.2f}") for v in (0.54, 0.58, 0.62)]
    body.append(axis(x0c, x1c, 151, ticks_r2, r"$R^2$ on Q3 subset"))
    ticks_rmse = [(sx(v, 0.14, 0.205, x0c, x1c), f"{v:.2f}") for v in (0.15, 0.17, 0.19)]
    body.append(axis(x0c, x1c, 58, ticks_rmse, "RMSE on Q3 subset"))

    legend_items = [
        ("Actual", PURPLE, 704),
        ("Matched", GRAY, 792),
        ("Mean", LIGHT, 891),
    ]
    for label, color, x in legend_items:
        edge = INK if label == "Mean" else color
        body.append(
            rf"\filldraw[draw=c{edge},fill=c{color},line width=1.0pt] ({x},216) circle (3.7pt);"
            rf"\node[anchor=west,font=\fontsize{{14}}{{16}}\selectfont,text=c{INK}] "
            rf"at ({x+8},216) {{{label}}};"
        )
    for name in order:
        color = colors[name]
        xr2 = sx(r2[name], 0.52, 0.65, x0c, x1c)
        xrmse = sx(rmse[name], 0.14, 0.205, x0c, x1c)
        edge = INK if name == "Normalized mean" else color
        body.append(
            rf"\filldraw[draw=c{edge},fill=c{color},line width=1.0pt] ({xr2:.2f},174) circle (4pt);"
        )
        body.append(
            rf"\filldraw[draw=c{edge},fill=c{color},line width=1.0pt] "
            rf"({xrmse:.2f},81) rectangle ++(7pt,7pt);"
        )

    tex = rf"""\documentclass{{minimal}}
\usepackage[T1]{{fontenc}}
\usepackage{{newtxtext}}
\usepackage{{newtxmath}}
\usepackage{{xcolor}}
\usepackage{{tikz}}
\pdfpagewidth=1000pt
\pdfpageheight=260pt
\setlength{{\paperwidth}}{{1000pt}}
\setlength{{\paperheight}}{{260pt}}
\setlength{{\textwidth}}{{1000pt}}
\setlength{{\textheight}}{{260pt}}
\setlength{{\oddsidemargin}}{{-72pt}}
\setlength{{\topmargin}}{{-72pt}}
\setlength{{\headheight}}{{0pt}}
\setlength{{\headsep}}{{0pt}}
\setlength{{\footskip}}{{0pt}}
\pagestyle{{empty}}
\definecolor{{c{BLUE}}}{{HTML}}{{{BLUE}}}
\definecolor{{c{ORANGE}}}{{HTML}}{{{ORANGE}}}
\definecolor{{c{PURPLE}}}{{HTML}}{{{PURPLE}}}
\definecolor{{c{GRAY}}}{{HTML}}{{{GRAY}}}
\definecolor{{c{LIGHT}}}{{HTML}}{{{LIGHT}}}
\definecolor{{c{INK}}}{{HTML}}{{{INK}}}
\begin{{document}}
\begin{{tikzpicture}}[x=1pt,y=1pt,line cap=round,line join=round]
\useasboundingbox (0,0) rectangle (1000,260);
\fill[white] (0,0) rectangle (1000,260);
{chr(10).join(body)}
\end{{tikzpicture}}
\end{{document}}
"""
    OUT_TEX.write_text(tex, encoding="utf-8")


if __name__ == "__main__":
    main()
