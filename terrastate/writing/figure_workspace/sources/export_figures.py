#!/usr/bin/env python3
"""Export editable TerraState SVG sources to vector PDF and 300 dpi PNG.

PyMuPDF's SVG parser does not apply embedded CSS classes consistently, so this
exporter materializes the small shared class vocabulary as presentation
attributes in a temporary SVG before conversion. The source SVGs remain the
editable masters.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
EXPORT = ROOT / "export"
QA = ROOT / "qa"

CLASS_STYLE = {
    "text": {
        "font-family": "Arial, Helvetica, sans-serif",
        "fill": "#202833",
    },
    "label": {"font-size": "40px", "font-weight": "700"},
    "heading": {
        "font-family": "Arial, Helvetica, sans-serif",
        "fill": "#202833",
        "font-size": "40px",
        "font-weight": "700",
    },
    "body": {"font-size": "36px"},
    "small": {
        "font-family": "Arial, Helvetica, sans-serif",
        "fill": "#202833",
        "font-size": "33px",
    },
    "micro": {"font-size": "33px"},
    "tick": {
        "font-family": "Arial, Helvetica, sans-serif",
        "fill": "#202833",
        "font-size": "33px",
    },
    "panel": {
        "fill": "#ffffff",
        "stroke": "#9aa3ad",
        "stroke-width": "4",
        "rx": "24",
    },
    "node": {
        "fill": "#ffffff",
        "stroke": "#34424f",
        "stroke-width": "4",
        "rx": "18",
    },
    "history": {
        "fill": "#eaf3f8",
        "stroke": "#0072b2",
        "stroke-width": "5",
    },
    "state": {
        "fill": "#e9f5f0",
        "stroke": "#008b6b",
        "stroke-width": "5",
    },
    "weather": {
        "fill": "#f1eff9",
        "stroke": "#6f5aa8",
        "stroke-width": "5",
    },
    "output": {
        "fill": "#fff3e8",
        "stroke": "#d55e00",
        "stroke-width": "5",
    },
    "train": {
        "fill": "#fffaf3",
        "stroke": "#a65c1b",
        "stroke-width": "4",
        "stroke-dasharray": "13 9",
    },
    "solid": {
        "fill": "none",
        "stroke": "#202833",
        "stroke-width": "6",
        "marker-end": "url(#arrow)",
    },
    "thin": {
        "fill": "none",
        "stroke": "#66717c",
        "stroke-width": "4",
        "marker-end": "url(#arrowGray)",
    },
    "intervene": {
        "fill": "none",
        "stroke": "#d55e00",
        "stroke-width": "6",
        "stroke-dasharray": "15 10",
        "marker-end": "url(#arrowOrange)",
    },
    "weatherDash": {
        "fill": "none",
        "stroke": "#6f5aa8",
        "stroke-width": "6",
        "stroke-dasharray": "15 10",
        "marker-end": "url(#arrowPurple)",
    },
    "q2": {
        "fill": "none",
        "stroke": "#d55e00",
        "stroke-width": "6",
        "stroke-dasharray": "15 10",
        "marker-end": "url(#arrowOrange)",
    },
    "q3": {
        "fill": "none",
        "stroke": "#6f5aa8",
        "stroke-width": "6",
        "stroke-dasharray": "15 10",
        "marker-end": "url(#arrowPurple)",
    },
    "training": {
        "fill": "none",
        "stroke": "#a65c1b",
        "stroke-width": "5",
        "stroke-dasharray": "5 9",
        "marker-end": "url(#arrowBrown)",
    },
}


def parse_inline_style(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for declaration in value.split(";"):
        if ":" not in declaration:
            continue
        key, val = declaration.split(":", 1)
        result[key.strip()] = val.strip()
    return result


def materialize_css(source: Path, destination: Path) -> None:
    tree = ET.parse(source)
    root = tree.getroot()
    for element in root.iter():
        attrs: dict[str, str] = {}
        for class_name in element.attrib.get("class", "").split():
            attrs.update(CLASS_STYLE.get(class_name, {}))
        attrs.update(parse_inline_style(element.attrib.get("style", "")))
        for key, value in attrs.items():
            element.set(key, value)
        element.attrib.pop("class", None)
        element.attrib.pop("style", None)
    tree.write(destination, encoding="utf-8", xml_declaration=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_one(stem: str) -> dict[str, object]:
    source = SOURCE / f"{stem}.svg"
    pdf_path = EXPORT / f"{stem}.pdf"
    png_path = EXPORT / f"{stem}.png"
    gray_path = QA / f"{stem}_grayscale.png"

    with tempfile.TemporaryDirectory(prefix="terrastate_svg_") as temp_dir:
        inline_svg = Path(temp_dir) / source.name
        materialize_css(source, inline_svg)
        svg_doc = fitz.open(inline_svg)
        pdf_bytes = svg_doc.convert_to_pdf()

    pdf_doc = fitz.open("pdf", pdf_bytes)
    pdf_doc.save(pdf_path, garbage=4, deflate=True)
    page = pdf_doc[0]
    color = page.get_pixmap(dpi=300, alpha=False)
    color.save(png_path)
    gray = fitz.Pixmap(fitz.csGRAY, color)
    gray.save(gray_path)

    return {
        "source": str(source.relative_to(ROOT)),
        "source_sha256": sha256(source),
        "pdf": str(pdf_path.relative_to(ROOT)),
        "pdf_sha256": sha256(pdf_path),
        "png": str(png_path.relative_to(ROOT)),
        "png_sha256": sha256(png_path),
        "pdf_width_pt": round(page.rect.width, 3),
        "pdf_height_pt": round(page.rect.height, 3),
        "png_width_px": color.width,
        "png_height_px": color.height,
        "png_dpi": 300,
    }


def make_paper_scale_preview(stems: list[str]) -> dict[str, object]:
    preview_pdf = QA / "paperscale_preview.pdf"
    preview_png = QA / "paperscale_preview.png"
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((54, 48), "TerraState figures at 7.0-inch AAAI full width", fontsize=9)
    top = 70.0
    for stem in stems:
        source = fitz.open(EXPORT / f"{stem}.pdf")
        source_page = source[0]
        rect = fitz.Rect(54, top, 558, top + source_page.rect.height)
        page.show_pdf_page(rect, source, 0)
        top = rect.y1 + 52
    document.save(preview_pdf, garbage=4, deflate=True)
    raster = page.get_pixmap(dpi=150, alpha=False)
    raster.save(preview_png)
    return {
        "pdf": str(preview_pdf.relative_to(ROOT)),
        "png": str(preview_png.relative_to(ROOT)),
        "page_width_pt": 612,
        "page_height_pt": 792,
        "render_dpi": 150,
    }


def make_contact_sheet() -> dict[str, object]:
    contact_pdf = QA / "figure_contact_sheet.pdf"
    contact_png = ROOT / "FIGURE_CONTACT_SHEET.png"
    document = fitz.open()
    page = document.new_page(width=1200, height=1430)
    page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
    page.insert_text((40, 38), "TerraState Figures 1–3 · contact sheet", fontsize=16)

    def place(stem: str, label: str, rect: fitz.Rect) -> None:
        page.insert_text((rect.x0, rect.y0 - 10), label, fontsize=11)
        source = fitz.open(EXPORT / f"{stem}.pdf")
        page.show_pdf_page(rect, source, 0, keep_proportion=True)
        page.draw_rect(rect, color=(0.75, 0.78, 0.81), width=0.8)

    place("fig1_overview", "Figure 1 · problem and contribution overview", fitz.Rect(40, 72, 1160, 424))
    place("fig2_method", "Figure 2 · method and intervention map", fitz.Rect(40, 484, 1160, 980))
    place("fig3_behavior", "Figure 3 · behavioral evidence", fitz.Rect(40, 1040, 1160, 1376))
    status_text = "All three panels shown at a common thumbnail width."

    document.save(contact_pdf, garbage=4, deflate=True)
    raster = page.get_pixmap(dpi=144, alpha=False)
    raster.save(contact_png)
    return {
        "png": str(contact_png.relative_to(ROOT)),
        "pdf": str(contact_pdf.relative_to(ROOT)),
        "render_dpi": 144,
        "status": status_text,
    }


def main() -> None:
    EXPORT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    stems = ["fig1_overview", "fig2_method", "fig3_behavior"]
    missing = [stem for stem in stems if not (SOURCE / f"{stem}.svg").exists()]
    if missing:
        raise FileNotFoundError(f"Required editable SVG source missing: {missing}")
    figures = [export_one(stem) for stem in stems]
    paper_scale = make_paper_scale_preview(stems)
    contact_sheet = make_contact_sheet()
    manifest = {
        "format_version": 1,
        "revision": "2.1-final",
        "figures": figures,
        "paper_scale_qa": paper_scale,
        "contact_sheet": contact_sheet,
        "note": "Revision 2.1 final. PDFs are vector exports; PNGs are 300 dpi paper previews.",
    }
    (ROOT / "EXPORT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    for item in figures:
        print(
            f"{item['pdf']} ({item['pdf_width_pt']}x{item['pdf_height_pt']} pt), "
            f"{item['png']} ({item['png_width_px']}x{item['png_height_px']} px)"
        )


if __name__ == "__main__":
    main()
