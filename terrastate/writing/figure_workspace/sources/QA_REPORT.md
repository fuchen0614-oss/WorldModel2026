# Revision-2.1 final figure export and editability QA

## Paper-size and raster checks

| Artifact | Final size | PNG preview | Result |
|---|---:|---:|---|
| Figure 1 | 7.0 × 2.20 in | 2100 × 660 px, 300 dpi | pass |
| Figure 2 | 7.0 × 3.10 in | 2100 × 930 px, 300 dpi | pass |
| Figure 3 | 7.0 × 2.10 in | 2100 × 630 px, 300 dpi | pass |

`qa/paperscale_preview.png` places all three exports at 7.0-inch AAAI full
width. Manual review found the primary hierarchy, intervention labels, axes,
and confidence intervals readable at that size.

## PDF and boundary checks

- All three PDFs have a 504 pt page width, corresponding to exactly 7.0 inches.
- All three PDFs contain vector drawing objects and zero raster image objects.
- Text remains selectable.
- No extracted text block extends beyond a PDF page boundary.
- The PNG previews carry 300 × 300 dpi metadata.

## SVG checks

- Visible labels remain SVG `<text>`/`<tspan>` nodes; text is not converted to
  paths.
- Figure 1 uses named groups for the endpoint-only forecaster, explicit state
  path, Q1–Q3 verification tests, and conclusion.
- Figure 2 uses named groups for normal inference, inputs/encoder, Q3 weather
  switch, state/readout path, context forecast, Q2 interventions, and
  training-only supervision.
- Figure 3 uses named Q2 and Q3 aggregate-effect groups.
- None of the three SVGs contains an `<image>` element.

## Native PPTX checks

Figure 1 and Figure 2 are native DrawingML reconstructions rather than
flattened slide images:

| Artifact | Groups | Editable text bodies | Native connectors | Pictures |
|---|---:|---:|---:|---:|
| Figure 1 | 4 | 27 | 24 | 0 |
| Figure 2 | 2 | 41 | 33 | 0 |

All package XML parts parse successfully, ZIP integrity passes, all text bodies
use no-wrap/no-autofit, and neither package contains `ppt/media` content.
Arial is the requested font. The detailed structural summary is in
`PPTX_EDITABILITY_REPORT.json`.

The minimum native PPTX run size is 7.92 pt in both files, matching the
approximately 8 pt minimum used by the editable SVG masters at 7.0-inch
width.

Figure 3 is delivered as an editable, grouped SVG plus the complete CSV-driven
plotting script. It does not require a PPTX to remain reproducible and editable.

This runtime has no PowerPoint or LibreOffice renderer. The PPTX packages were
validated structurally against the matching SVG layouts, not by a native Office
render. They should be opened once on the target PowerPoint system to confirm
platform-specific font metrics.

## Grayscale and non-color encoding

Grayscale previews exist for all three figures:

- `qa/fig1_overview_grayscale.png`;
- `qa/fig2_method_grayscale.png`;
- `qa/fig3_behavior_grayscale.png`.

Normal inference uses heavy solid arrows; Q2 retains a cut/cross, labels, and
filled/open points; Q3 retains its selector, labels, square points, and
filled/open distinction; training is isolated in a separate bordered band.
Meaning therefore does not rely on hue alone.

`FIGURE_CONTACT_SHEET.png` shows all three figures at one common thumbnail
width; `qa/paperscale_preview.png` shows all three at the intended 7.0-inch
paper width.

## Figure 3 provenance checks

`source/fig3_behavior.py` reads every estimate and stored interval from
`data/fig3_aggregate_effects.csv`. It validates required fields, finite values,
CI ordering, positive sample counts, every row's frozen source path and
on-disk SHA-256, expected row counts, metric identities, and the Q3 effect
direction before writing the SVG. Q2 points are paired minicube-effect means
with their corresponding paired bootstrap intervals. It does not read or
fabricate per-cube data and does not run model evaluation.

## Revision-2.1 visual separation

- Figure 1 contains no `q/P/O`, closure equation, training loss, or detailed
  intervention arms.
- Figure 2 contains the formal inference path, exact Q2/Q3 locations, and three
  compact training supervision items.
- Figure 3 contains only behavioral effect directions and 95% confidence
  intervals; exact values remain in Tables 2–3.

## Revision-2.1 final checks

- Figure 1 uses “shared transition” and “weather-conditioned”; the original
  three-line `shared T / driven by w / transition` wording is absent.
- Figure 2 uses the natural-language training summary “Training objectives:
  forecasting + distillation + future-state alignment”; no loss formula is
  embedded in the diagram.
- Figure 2 uses `state readout`, `context-only forecast`, `actual`,
  `matched donor`, `normalized mean`, `remove r_h (s=0)`, and `T→I`.
- Figure 3 retains `paired mean forecast-skill loss (ΔR²)` and the frozen
  paired-effect means/CIs. Its CSV SHA-256 is unchanged from Revision 2:
  `9df66ec44181006fa95d076e15603654c1a775d20c7b6bfe059ba6594f3bc9ee`.
- An independent read-only review found no overlap, clipping, spelling error,
  data mixing, or print-scale readability blocker.
