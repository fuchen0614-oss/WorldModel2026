# TerraState figure workspace

This directory is an isolated, non-destructive handoff for Figures 1–3.

## Regenerate Figures 1–2

```bash
python source/build_editable_pptx.py
python source/export_figures.py
```

## Regenerate Figure 3

```bash
python source/fig3_behavior.py
python source/export_figures.py
```

Figure 3 reads only `data/fig3_aggregate_effects.csv`. It does not require
per-cube data and does not run evaluation. See `data/FIG3_DATA_STATUS.md`.

## Source of truth

- Edit SVG masters in `source/`.
- Edit native PowerPoint masters in `source/*.pptx`; all text, cards, grids,
  arrows, and cut marks are native objects grouped by semantic region.
- Use vector PDFs in `export/` for LaTeX.
- Use 300 dpi PNGs in `export/` for review.
- Use `FIGURE_CONTACT_SHEET.png` for a one-screen style comparison.
- Use `qa/*_grayscale.png` to inspect non-color differentiation.
- Verify hashes and dimensions in `EXPORT_MANIFEST.json`.
- Verify native PowerPoint object counts in `PPTX_EDITABILITY_REPORT.json`.
- See `QA_REPORT.md` for paper-size, vector, live-text, and fail-closed checks.

No file outside this workspace is written by the generation scripts.
