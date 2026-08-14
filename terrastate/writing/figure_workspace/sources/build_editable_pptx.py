#!/usr/bin/env python3
"""Build fully native, grouped PowerPoint sources for TerraState Figures 1–2.

The deck is written as DrawingML/PresentationML directly because python-pptx is
not available in this runtime. No figure bitmap is embedded: text, cards,
state grids, lines, arrows, and cut marks are independent native objects.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT.parent / "示例" / "Pipeline.pptx"
SOURCE = ROOT / "source"

EMU_PER_UNIT = 3048  # 2100 source units == 7 inches.
FONT = "Arial"

INK = "202833"
GRAY = "66717C"
LIGHT = "C4CAD0"
BLUE = "0072B2"
BLUE_FILL = "EAF3F8"
GREEN = "008B6B"
GREEN_FILL = "E9F5F0"
PURPLE = "6F5AA8"
PURPLE_FILL = "F1EFF9"
ORANGE = "D55E00"
ORANGE_FILL = "FFF3E8"
BROWN = "A65C1B"
TRAIN_FILL = "FFFAF3"
WHITE = "FFFFFF"


def emu(value: float) -> int:
    return int(round(value * EMU_PER_UNIT))


def color_xml(hex_color: str) -> str:
    return f'<a:solidFill><a:srgbClr val="{hex_color}"/></a:solidFill>'


@dataclass
class Canvas:
    width: float
    height: float
    counter: int = 1

    def next_id(self) -> int:
        self.counter += 1
        return self.counter

    def rect(
        self,
        name: str,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str = WHITE,
        stroke: str = INK,
        stroke_width: float = 3,
        rounded: bool = True,
        dash: str | None = None,
    ) -> str:
        shape_id = self.next_id()
        geom = "roundRect" if rounded else "rect"
        dash_xml = f'<a:prstDash val="{dash}"/>' if dash else ""
        return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
    <a:prstGeom val="{geom}"><a:avLst/></a:prstGeom>
    {color_xml(fill)}
    <a:ln w="{emu(stroke_width)}">{color_xml(stroke)}{dash_xml}<a:headEnd type="none"/><a:tailEnd type="none"/></a:ln>
  </p:spPr>
</p:sp>"""

    def ellipse(
        self,
        name: str,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str = WHITE,
        stroke: str = INK,
        stroke_width: float = 3,
    ) -> str:
        shape_id = self.next_id()
        return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
    <a:prstGeom val="ellipse"><a:avLst/></a:prstGeom>
    {color_xml(fill)}
    <a:ln w="{emu(stroke_width)}">{color_xml(stroke)}</a:ln>
  </p:spPr>
</p:sp>"""

    def text(
        self,
        name: str,
        x: float,
        y: float,
        w: float,
        h: float,
        text: str,
        size_units: float = 36,
        color: str = INK,
        bold: bool = False,
        align: str = "ctr",
        valign: str = "ctr",
    ) -> str:
        shape_id = self.next_id()
        font_size = max(size_units, 33)
        paragraphs: list[str] = []
        for line in text.split("\n"):
            paragraphs.append(
                f'<a:p><a:pPr algn="{align}"/>'
                f'<a:r><a:rPr lang="en-US" sz="{int(round(font_size / 300 * 7200))}" '
                f'b="{1 if bold else 0}" dirty="0"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
                f'<a:latin typeface="{FONT}"/><a:ea typeface="{FONT}"/><a:cs typeface="{FONT}"/>'
                f'</a:rPr><a:t>{escape(line)}</a:t></a:r><a:endParaRPr lang="en-US"/></a:p>'
            )
        return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
    <a:prstGeom val="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr wrap="none" anchor="{valign}" lIns="0" rIns="0" tIns="0" bIns="0"><a:noAutofit/></a:bodyPr>
  <a:lstStyle/>{''.join(paragraphs)}</p:txBody>
</p:sp>"""

    def rich_text(
        self,
        name: str,
        x: float,
        y: float,
        w: float,
        h: float,
        runs: list[tuple[str, float, bool, int]],
        color: str = INK,
        align: str = "l",
    ) -> str:
        """Create one editable text line with optional DrawingML baselines."""
        shape_id = self.next_id()
        run_xml: list[str] = []
        for value, size_units, bold, baseline in runs:
            font_size = max(size_units, 33)
            baseline_xml = f' baseline="{baseline}"' if baseline else ""
            run_xml.append(
                f'<a:r><a:rPr lang="en-US" sz="{int(round(font_size / 300 * 7200))}" '
                f'b="{1 if bold else 0}" dirty="0"{baseline_xml}>'
                f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
                f'<a:latin typeface="{FONT}"/><a:ea typeface="{FONT}"/><a:cs typeface="{FONT}"/>'
                f'</a:rPr><a:t>{escape(value)}</a:t></a:r>'
            )
        return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
    <a:prstGeom val="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr wrap="none" anchor="ctr" lIns="0" rIns="0" tIns="0" bIns="0"><a:noAutofit/></a:bodyPr>
  <a:lstStyle/><a:p><a:pPr algn="{align}"/>{''.join(run_xml)}<a:endParaRPr lang="en-US"/></a:p></p:txBody>
</p:sp>"""

    def line(
        self,
        name: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: str = INK,
        width: float = 4,
        dash: str = "solid",
        arrow: bool = False,
    ) -> str:
        shape_id = self.next_id()
        x = min(x1, x2)
        y = min(y1, y2)
        w = max(abs(x2 - x1), 0.01)
        h = max(abs(y2 - y1), 0.01)
        flip_h = ' flipH="1"' if x2 < x1 else ""
        flip_v = ' flipV="1"' if y2 < y1 else ""
        tail = '<a:tailEnd type="triangle" w="med" len="med"/>' if arrow else '<a:tailEnd type="none"/>'
        dash_xml = "" if dash == "solid" else f'<a:prstDash val="{dash}"/>'
        return f"""
<p:cxnSp>
  <p:nvCxnSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>
  <p:spPr>
    <a:xfrm{flip_h}{flip_v}><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
    <a:prstGeom val="line"><a:avLst/></a:prstGeom>
    <a:ln w="{emu(width)}">{color_xml(color)}{dash_xml}<a:headEnd type="none"/>{tail}</a:ln>
  </p:spPr>
</p:cxnSp>"""

    def group(self, name: str, x: float, y: float, w: float, h: float, children: list[str]) -> str:
        shape_id = self.next_id()
        return f"""
<p:grpSp>
  <p:nvGrpSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
  <p:grpSpPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/>
  <a:chOff x="0" y="0"/><a:chExt cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm></p:grpSpPr>
  {''.join(children)}
</p:grpSp>"""


def card(
    c: Canvas,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    lines: list[tuple[str, float, bool]],
    fill: str,
    stroke: str,
    dash: str | None = None,
) -> list[str]:
    parts = [c.rect(f"{name}_box", x, y, w, h, fill, stroke, 4, True, dash)]
    total = sum(size * 1.25 for _, size, _ in lines)
    cursor = y + (h - total) / 2
    for index, (value, size, bold) in enumerate(lines):
        line_h = size * 1.25
        parts.append(c.text(f"{name}_text_{index+1}", x + 8, cursor, w - 16, line_h, value, size, INK, bold))
        cursor += line_h
    return parts


def state_card(c: Canvas, name: str, x: float, y: float, label: str, subtitle: str = "") -> list[str]:
    parts = [c.rect(f"{name}_box", x, y, 166, 144, GREEN_FILL, GREEN, 4)]
    parts.append(c.rect(f"{name}_grid_border", x + 41, y + 20, 84, 64, WHITE, GREEN, 2, False))
    for index in range(1, 4):
        parts.append(c.line(f"{name}_grid_v{index}", x + 41 + index * 21, y + 20, x + 41 + index * 21, y + 84, GREEN, 1.5))
        parts.append(c.line(f"{name}_grid_h{index}", x + 41, y + 20 + index * 16, x + 125, y + 20 + index * 16, GREEN, 1.5))
    parts.append(c.text(f"{name}_label", x + 8, y + 87, 150, 34, label, 36, INK, True))
    if subtitle:
        parts.append(c.text(f"{name}_subtitle", x + 8, y + 117, 150, 24, subtitle, 29))
    return parts


def history_glyph(c: Canvas, prefix: str, x: float, y: float, scale: float = 1.0, color: str = BLUE) -> list[str]:
    parts: list[str] = []
    for index, offset in enumerate((0, 12, 24), start=1):
        parts.append(c.rect(f"{prefix}_frame_{index}", x + offset * scale, y + offset * scale, 58 * scale, 48 * scale, WHITE, color, 2, False))
    parts.append(c.line(f"{prefix}_mask", x + 26 * scale, y + 28 * scale, x + 78 * scale, y + 70 * scale, color, 2, "dash"))
    return parts


def fig1_slide() -> tuple[Canvas, list[str]]:
    c = Canvas(2100, 660)
    root: list[str] = [c.rect("white_background", 0, 0, 2100, 660, WHITE, WHITE, 0, False)]

    left: list[str] = [c.rect("accuracy_panel_border", 0, 0, 500, 520, WHITE, "9AA3AD", 4)]
    left += [
        c.text("accuracy_heading", 30, 14, 440, 48, "Output prediction", 40, INK, True, "l"),
        c.text("accuracy_subheading", 30, 62, 440, 40, "what accuracy can verify", 36, INK, False, "l"),
    ]
    left += card(c, "weather_input", 34, 126, 142, 58, [("weather", 32, False)], PURPLE_FILL, PURPLE)
    left += card(c, "observations", 34, 214, 154, 112, [], BLUE_FILL, BLUE)
    left += history_glyph(c, "observations", 55, 233)
    left.append(c.text("observations_label", 20, 330, 182, 38, "observations", 32))
    left += card(c, "endpoint_forecaster", 268, 181, 184, 128, [("endpoint", 35, False), ("forecaster", 35, False)], WHITE, INK)
    left.append(c.line("weather_to_forecaster", 176, 155, 268, 205, INK, 4, "solid", True))
    left.append(c.line("observations_to_forecaster", 188, 270, 268, 270, INK, 5, "solid", True))
    left += card(c, "future_output", 246, 354, 154, 88, [], ORANGE_FILL, ORANGE)
    left.append(c.rect("future_grid", 273, 371, 100, 52, WHITE, ORANGE, 2, False))
    for index in range(1, 3):
        left.append(c.line(f"future_grid_h{index}", 273, 371 + index * 17, 373, 371 + index * 17, ORANGE, 1.5))
        left.append(c.line(f"future_grid_v{index}", 273 + index * 33, 371, 273 + index * 33, 423, ORANGE, 1.5))
    left.append(c.line("forecaster_to_output", 360, 309, 360, 354, INK, 5, "solid", True))
    left.append(c.text("accuracy_note_1", 30, 449, 440, 34, "Accuracy checks the endpoint.", 32, INK, False, "l"))
    left.append(c.text("accuracy_note_2", 30, 482, 445, 34, "Internal mechanism: untested.", 32, INK, False, "l"))
    root.append(c.group("Figure1_Accuracy_Only_Forecaster", 24, 24, 500, 520, left))

    center: list[str] = [c.rect("explicit_path_panel_border", 0, 0, 910, 520, WHITE, "9AA3AD", 4)]
    center.append(c.text("explicit_path_heading", 30, 14, 850, 48, "TerraState exposes an explicit state path", 40, INK, True, "l"))
    center += card(c, "past_context", 38, 211, 148, 104, [("past", 35, False), ("context", 35, False)], BLUE_FILL, BLUE)
    center += state_card(c, "predictive_state_t", 232, 184, "zₜ")
    center.append(c.rect("shared_transition_box", 427, 184, 310, 158, PURPLE_FILL, PURPLE, 4))
    center.append(c.text("shared_transition_title", 435, 210, 294, 40, "shared transition", 33, INK, True))
    center.append(c.text("shared_transition_condition", 435, 264, 294, 40, "weather-conditioned", 33))
    center += card(c, "future_weather", 482, 96, 200, 54, [("future weather", 31, False)], PURPLE_FILL, PURPLE)
    center += state_card(c, "predictive_state_future", 747, 184, "zₜ₊ₕ")
    center.append(c.line("weather_to_T", 582, 150, 582, 184, PURPLE, 5, "dash", True))
    center.append(c.line("context_to_state", 186, 263, 232, 263, INK, 5, "solid", True))
    center.append(c.line("state_to_T", 398, 263, 427, 263, INK, 5, "solid", True))
    center.append(c.line("T_to_future_state", 737, 263, 747, 263, INK, 5, "solid", True))
    center.append(c.text("predictive_state_label", 205, 350, 220, 40, "predictive state", 32))
    center.append(c.text("future_state_label", 720, 350, 220, 40, "future state", 32))
    center.append(c.text("intervenable_path_note", 90, 420, 730, 46, "forecast-bearing path that can be intervened on", 35))
    root.append(c.group("Figure1_Explicit_Predictive_State_Path", 548, 24, 910, 520, center))

    right: list[str] = [c.rect("verification_tests_panel_border", 0, 0, 594, 520, WHITE, "9AA3AD", 4)]
    right.append(c.text("verification_tests_heading", 30, 14, 535, 48, "Three verification tests", 38, INK, True, "l"))
    right += card(c, "q1_forecast_test", 32, 96, 530, 104, [("Q1   Forecast skill", 36, True), ("useful prediction?", 32, False)], BLUE_FILL, BLUE)
    right += card(c, "q2_state_test", 32, 226, 530, 104, [("Q2   State intervention", 36, True), ("cut or bypass the path", 32, False)], ORANGE_FILL, ORANGE)
    right += card(c, "q3_weather_test", 32, 356, 530, 104, [("Q3   Weather intervention", 36, True), ("replace the future driver", 32, False)], PURPLE_FILL, PURPLE)
    root.append(c.group("Figure1_Three_Verification_Tests", 1482, 24, 594, 520, right))

    outcome: list[str] = [
        c.rect("outcome_border", 0, 0, 1528, 70, GREEN_FILL, GREEN, 5),
        c.text(
            "outcome_text",
            26,
            10,
            1476,
            50,
            "Explicit state path + targeted tests → internally testable EO world model",
            36,
            INK,
        ),
    ]
    root.append(c.group("Figure1_Internally_Testable_Outcome", 548, 566, 1528, 70, outcome))
    return c, root


def fig2_slide() -> tuple[Canvas, list[str]]:
    c = Canvas(2100, 930)
    root: list[str] = [c.rect("white_background", 0, 0, 2100, 930, WHITE, WHITE, 0, False)]
    normal: list[str] = [c.rect("normal_inference_border", 0, 0, 2038, 585, WHITE, LIGHT, 4)]
    normal.append(c.text("normal_inference_label", 28, 10, 380, 40, "NORMAL INFERENCE", 32, INK, False, "l"))
    normal.append(c.line("normal_header_rule", 365, 33, 1974, 33, LIGHT, 2))
    normal += card(c, "eo_history", 24, 208, 230, 176, [], BLUE_FILL, BLUE)
    normal += history_glyph(c, "eo_history", 56, 233, 1.2)
    normal.append(c.text("eo_history_label", 42, 322, 194, 42, "EO history", 34))
    normal.append(c.text("cloud_masked_label", 24, 388, 230, 38, "cloud-masked", 30))
    normal += card(c, "q_encoder", 304, 191, 230, 210, [("q", 40, True), ("history", 31, False), ("encoder", 31, False)], BLUE_FILL, BLUE)
    normal += card(c, "past_weather_static", 279, 80, 280, 74, [("past weather", 30, False), ("static geography g", 30, False)], BLUE_FILL, BLUE)
    normal.append(c.line("past_conditions_to_q", 419, 154, 419, 191, INK, 4, "solid", True))
    normal += card(c, "projector", 586, 232, 142, 128, [("P", 40, True), ("projector", 29, False)], BLUE_FILL, BLUE)
    normal += state_card(c, "state_t", 778, 201, "zₜ", "predictive")
    normal += card(c, "transition", 1056, 201, 320, 190, [("shared T", 40, True), ("T(zₜ, w, g, h)", 34, False), ("weather-conditioned", 30, False)], PURPLE_FILL, PURPLE)
    normal += state_card(c, "state_future", 1426, 201, "zₜ₊ₕ", "future state")
    normal += card(c, "readout", 1664, 222, 154, 148, [("O", 40, True), ("state", 29, False), ("readout", 29, False)], ORANGE_FILL, ORANGE)
    normal.append(c.ellipse("sum_node", 1836, 254, 80, 80, WHITE, ORANGE, 5))
    normal.append(c.text("sum_plus", 1836, 254, 80, 80, "+", 40, INK, True))
    normal += card(c, "future_ndvi", 1936, 219, 116, 154, [("future", 31, False), ("NDVI", 31, False), ("ŷₜ₊ₕ", 31, False)], ORANGE_FILL, ORANGE)
    for name, x1, x2 in [
        ("history_to_q", 254, 304),
        ("q_to_P", 534, 586),
        ("P_to_state", 728, 778),
        ("state_to_T", 944, 1056),
        ("T_to_future_state", 1376, 1426),
        ("future_state_to_O", 1592, 1664),
        ("O_to_sum", 1818, 1836),
        ("sum_to_output", 1916, 1936),
    ]:
        normal.append(c.line(name, x1, 296, x2, 296, INK, 5, "solid", True))
    normal.append(c.rect("q3_switch_box", 896, 58, 640, 114, "F8F7FC", PURPLE, 4))
    normal.append(c.text("q3_switch_label", 912, 64, 608, 36, "Q3 · switch w only (g,h fixed)", 29))
    normal += card(c, "q3_actual", 916, 108, 100, 45, [("actual", 29, False)], PURPLE_FILL, PURPLE)
    normal += card(c, "q3_donor", 1026, 108, 220, 45, [("matched donor", 29, False)], WHITE, PURPLE, "dash")
    normal += card(c, "q3_mean", 1256, 108, 260, 45, [("normalized mean", 29, False)], WHITE, PURPLE, "dash")
    normal.append(c.line("actual_to_T", 966, 153, 1136, 201, INK, 4, "solid", True))
    normal.append(c.line("donor_to_T", 1136, 153, 1216, 201, PURPLE, 4, "dash", True))
    normal.append(c.line("mean_to_T", 1386, 153, 1296, 201, PURPLE, 4, "dash", True))
    normal.append(c.line("context_prior_down", 419, 401, 419, 524, GRAY, 3))
    normal.append(c.line("context_prior_horizontal", 419, 524, 1810, 524, GRAY, 3))
    normal.append(c.line("context_prior_to_sum", 1810, 524, 1876, 334, GRAY, 3, "solid", True))
    normal += card(c, "context_prior_label", 556, 487, 500, 72, [("context-only forecast bₕ", 31, False)], BLUE_FILL, BLUE)
    normal.append(c.line("q2_identity_bypass", 944, 427, 1426, 427, ORANGE, 5, "dash", True))
    normal += card(c, "q2_identity_label", 1036, 404, 360, 62, [("Q2 support · T→I", 31, False)], ORANGE_FILL, ORANGE, "dash")
    normal.append(c.line("q2_primary_pointer", 1636, 413, 1852, 330, ORANGE, 5, "dash", True))
    normal += card(c, "q2_primary_label", 1466, 413, 340, 84, [("Q2 primary", 31, False), ("remove rₕ (s=0)", 31, False)], ORANGE_FILL, ORANGE)
    normal.append(c.line("closure_cut_1", 1827, 267, 1857, 325, ORANGE, 7))
    normal.append(c.line("closure_cut_2", 1857, 267, 1827, 325, ORANGE, 7))
    root.append(c.group("Figure2_Normal_Inference_and_Interventions", 24, 25, 2038, 585, normal))

    training: list[str] = [c.rect("training_band_border", 0, 0, 2038, 266, TRAIN_FILL, BROWN, 4)]
    training.append(c.text("training_only_label", 28, 10, 250, 46, "TRAINING ONLY", 32, BROWN, False, "l"))
    training.append(
        c.text(
            "training_objectives",
            306,
            10,
            1050,
            46,
            "Training objectives: forecasting + distillation + future-state alignment",
            33,
            INK,
            False,
            "l",
        )
    )
    training.append(c.text("inference_absence_note", 1190, 10, 800, 46, "teacher + future EO absent at inference", 29, INK, False, "r"))
    training += card(c, "gt_loss", 31, 92, 430, 108, [("Forecast supervision", 33, False), ("ground-truth future", 29, False)], TRAIN_FILL, BROWN)
    training += card(c, "kd_loss", 501, 92, 430, 108, [("Distillation", 33, False), ("frozen teacher", 29, False)], TRAIN_FILL, BROWN)
    training += card(c, "state_loss", 971, 92, 1007, 108, [("Future-state supervision", 33, False), ("terminal h = 20 target from frozen q + P on future EO", 28, False)], TRAIN_FILL, BROWN)
    root.append(c.group("Figure2_Training_Only_Supervision", 24, 638, 2038, 266, training))
    return c, root


def slide_xml(c: Canvas, shapes: list[str], name: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 showMasterSp="0">
 <p:cSld name="{escape(name)}">
  <p:spTree>
   <p:nvGrpSpPr><p:cNvPr id="1" name="Root"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
   <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{emu(c.width)}" cy="{emu(c.height)}"/>
   <a:chOff x="0" y="0"/><a:chExt cx="{emu(c.width)}" cy="{emu(c.height)}"/></a:xfrm></p:grpSpPr>
   {''.join(shapes)}
  </p:spTree>
 </p:cSld>
 <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def build_pptx(output: Path, c: Canvas, shapes: list[str], title: str) -> None:
    slide = slide_xml(c, shapes, title)
    slide_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"
 Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>"""
    with zipfile.ZipFile(TEMPLATE) as source_zip, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as out_zip:
        for item in source_zip.infolist():
            name = item.filename
            if name.startswith("ppt/media/") or name == "docProps/thumbnail.jpeg":
                continue
            if name in {"ppt/slides/slide1.xml", "ppt/slides/_rels/slide1.xml.rels"}:
                continue
            data = source_zip.read(name)
            if name == "ppt/presentation.xml":
                text = data.decode("utf-8")
                text = re.sub(r'<p:sldSz cx="\d+" cy="\d+"/?>', f'<p:sldSz cx="{emu(c.width)}" cy="{emu(c.height)}"/>', text)
                data = text.encode("utf-8")
            out_zip.writestr(name, data)
        out_zip.writestr("ppt/slides/slide1.xml", slide.encode("utf-8"))
        out_zip.writestr("ppt/slides/_rels/slide1.xml.rels", slide_rels.encode("utf-8"))


def main() -> None:
    SOURCE.mkdir(parents=True, exist_ok=True)
    for stem, builder, title in [
        ("fig1_overview", fig1_slide, "TerraState Figure 1 Overview"),
        ("fig2_method", fig2_slide, "TerraState Figure 2 Method"),
    ]:
        canvas, shapes = builder()
        output = SOURCE / f"{stem}.pptx"
        build_pptx(output, canvas, shapes, title)
        print(f"wrote {output.relative_to(ROOT)} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
