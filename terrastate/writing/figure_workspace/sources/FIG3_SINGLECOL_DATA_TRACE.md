# Figure 3 Single-Column Layout — Final Data and QA Trace

Status: `FIG3_SINGLECOL_LAYOUT_FROZEN`

This is the final single-column adaptation of the evidence-audited Figure 3
v2. It changes panel geometry and paper integration only. The frozen data,
estimands, confidence intervals, sample membership, evidence direction, and
Q2 primary/supporting hierarchy are unchanged.

## Final layout and paper integration

- LaTeX float: standard `figure[t]`, not `figure*`, `minipage`, or
  `captionof`.
- Included width: `\columnwidth`.
- Figure size: `3.3 × 3.5 in`; PDF media box: `237.6 × 252.0 pt`.
- Panel (a): full column width at the top.
- Panels (b) and (c): side by side below panel (a).
- Configured text sizes: `7.5–8.5 pt`.
- Panels (b) and (c) retain the common `[0, 0.12]` range on both axes.
- Panel (c) uses right-side y ticks; duplicated inner x-axis endpoints are
  suppressed only typographically. Coordinates and data are unchanged.
- Final paper: 9 pages; Figure 3 is Figure 3 on PDF page 8, fully contained in
  the left column. References begin below it and continue in the right column.
- Page 7 remains filled by Results, Tables 1–3, Limitations, and Conclusion;
  the former large blank region is absent.

## Frozen data checks

The single-column script imports the v2 extraction and verification functions
from `source/fig3_behavior_v2.py`. It reads the same frozen JSON files and
hard-fails if their SHA-256 values differ from
`evidence_workspace/results_ledger.json`. The path resolver accepts the
workspace's equivalent `/mnt/data/...` and `/mnt/workspace/...` mount roots;
the accepted filenames and required hashes remain exact.

### Q2

- Validation state removal: mean `0.01616252595360122`,
  95% CI `[0.006432408120151691, 0.02590229577842624]`, `n=589`.
- Validation \(T\to I\): mean `0.017417428921451206`,
  95% CI `[0.007824839508750908, 0.026960749441100905]`, `n=589`.
- OOD-t state removal: mean `0.021997768589881533`,
  95% CI `[0.014219898623411737, 0.03017606928017251]`, `n=1019`.
- OOD-t \(T\to I\): mean `0.024015932710944276`,
  95% CI `[0.016086752271438905, 0.032169788967835664]`, `n=1019`.

### Q3

- Rows read: `84`.
- Unique matched-pair keys: `84`.
- Missing/non-finite values: `0`.
- Rows filtered or selected: `0`.
- Donor-minus-actual mean loss: `0.002565468112672014`.
- Normalized-mean-minus-actual mean loss: `0.011261332329706334`.
- Matched donor above \(y=x\): `56/84`.
- Normalized mean above \(y=x\): `69/84`.
- Points equal to \(y=x\): `0`.
- The losses remain per-minicube masked MSE over the complete 20-step
  forecast window, not an \(h=20\)-only endpoint error.

## Frozen-source SHA-256

| File | SHA-256 |
|---|---|
| `evidence_workspace/raw/release/val_q2_state_contract_exclusive.json` | `33b40d3e6bf6e0190c9415a9e0421e9809063356dcba2350890defeeed35f2d9` |
| `evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json` | `7ebc0569d705a9991ac8b8d17c42113c9da052b2bec73f7c28d021e28a65a051` |
| `evidence_workspace/raw/release/q3_extreme_state_audit.json` | `9dae43b9a8a4fcdf0a73ef91daa58c189a88e769541ce295046cd0e938497041` |
| `evidence_workspace/results_ledger.json` | `d1f8ec7d7a51fae87afc8ba9dbc27905c6816434dc5554980d2e7c2eb472c4b2` |
| `figure_workspace/source/fig3_behavior_v2.py` | `e87324c5c59a30394868e4233278307a728b190cc9cd371de83afc8de9078c61` |

## Final single-column output SHA-256

| File | SHA-256 |
|---|---|
| `figure_workspace/source/fig3_behavior_singlecol.py` | `4bbe7d71613c5358352688dac93dc417598d42728074af86890dd955d5ad31d0` |
| `figure_workspace/source/fig3_behavior_singlecol.svg` | `399ebcd4335aabc4ea0dcbd46a279a6789b5af14a5ea237ebe9bd3ea88cca503` |
| `figure_workspace/export/fig3_behavior_singlecol.pdf` | `3b9c764152a867b2d1aef1b82b5661eb18bbd613236cb37dc45d58dfac7f0a53` |
| `figure_workspace/export/fig3_behavior_singlecol.png` | `9299c97fe61bf123dcdfa761e92cf056c4dbfaebefe5bcc662975049840919ed` |
| `figure_workspace/qa/fig3_behavior_singlecol_grayscale.png` | `f5191df49c0e5258eed5f143642486f10722363121f6a86580ea29b2b45a61e1` |
| `figure_workspace/qa/fig3_behavior_singlecol_paperscale.png` | `af55372e7ecc64572b4a42f588b14f539ab5a047a2e7f830711e756a27fecd46` |
| `figure_workspace/qa/fig3_behavior_singlecol_inpaper.png` | `8a1610c05b6fce239e1b8474e9b2d5a4e461ad7789b2b8e25e2512b60ea8b3e4` |
| `figure_workspace/qa/fig3_behavior_singlecol_qa.json` | `e5405316086836c0d6583b2abde0fcfe1dc8b3e76caa9165e041bd9e97ea43cf` |

## Paper integration SHA-256

| File | SHA-256 |
|---|---|
| `paper/main.tex` | `0bd80eb824005857fb03930c74a581b153417019559974476d12d94dd3d79d00` |
| `paper/main.pdf` | `a9892a795aa3f506c844cce184234f82bc507959b4dec8cde219d8386104c7e6` |
| `paper/main.log` | `d74f82c46a4c42a971b14ecdee1bb95246bf85d19c5ab2cb40180bf902eb951c` |

## Format and compilation QA

- PDF raster image objects: `0`; the Figure 3 PDF remains vector.
- SVG: `35` editable text nodes and `0` embedded image nodes.
- PNG and grayscale preview: 300 dpi.
- Color is not the sole encoding: state removal is filled, \(T\to I\) is
  open/smaller, and the weather controls occupy separately labeled panels.
- Paper-scale and grayscale previews: visually checked, no clipping or
  overlap.
- In-paper preview: visually checked at final column width, with readable
  labels, markers, CIs, scatter points, diagonal counts, and caption.
- LaTeX errors: `0`.
- Undefined citations/references: `0`.
- Overfull hbox: `0`.
- Overfull vbox: `0`.
- Figure labels: architecture = Figure 2 on page 6; behavior = Figure 3 on
  page 8.

## Scope

- Model evaluation rerun: `NO`.
- Frozen JSON, ledger, experiments, or models modified: `NO`.
- Figure 1 or Figure 2 modified: `NO`.
- Tables 1–3 or Results claims modified: `NO`.
- Q4/composition included: `NO`.
- Causal or counterfactual claim added: `NO`.
- Extreme-specific enhancement added: `NO`.
- Superseded trial page previews were removed; the retained final in-paper
  preview is `qa/fig3_behavior_singlecol_inpaper.png`.
