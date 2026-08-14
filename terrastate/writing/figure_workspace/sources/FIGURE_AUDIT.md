# TerraState AAAI-27 Figure Audit

## 1. Audit scope and sources

Read-only audit completed for:

- `paper/main.pdf` (current compiled English PDF);
- `paper/main.tex` (current English source);
- `MANUSCRIPT_ZH.md` (Chinese working manuscript);
- current figure PDFs/PNGs and TikZ sources in `paper/figures/`;
- latest narrative and protocol records 84, 87, and 88 in
  `WorldModel2026/思路整理进展/`;
- frozen final Q1–Q3 evidence in
  `WorldModel2026-planb/TERRASTATE_V2_EVIDENCE.md`;
- `示例/ICLR.pptx`, `示例/Pipeline.pptx`, and the accompanying figure images.

No manuscript, bibliography, model/evaluation code, original result file, or
existing paper figure source was modified.

## 2. Important document-state discrepancy

The current compiled `paper/main.pdf` and current `paper/main.tex` are not the
same manuscript state:

- the PDF still shows TBD local rows/tables and the earlier Q4-prominent
  narrative on pages 6–7;
- `main.tex` already contains the frozen Q1–Q3 values, the final Q2/Q3
  interpretation, and a data-driven behavioral figure.

The body-writing session must decide which source state is authoritative before
integration and recompile there. This figure workspace does not resolve the
manuscript discrepancy and does not modify either file.

## 3. Current Figure 1 audit

Current artifact: `paper/figures/terrastate_method_overview.pdf`.

### Reusable elements

- The exact inference contract is represented correctly:
  history-only `q` → `P` → spatial `z_t` → shared weather-conditioned `T` →
  `z_{t+h}` → `O` → explicit state contribution.
- The context-only forecast `b_h` branches before future weather enters.
- Future weather, static geography, and horizon enter the shared transition.
- Training-only teacher/future-observation branches are separated by line type
  and background.
- Spatial grid glyphs correctly communicate that the exposed state is spatial,
  not a single vector.

### Narrative and visual problems

- It is a detailed method/training diagram, not a Figure 1 problem–contribution
  overview. It does not directly answer why endpoint accuracy is insufficient.
- The first visual impression is implementation complexity: `q`, `P`, three
  losses, teacher, target encoder, and multiple long branches compete equally.
- Q2 and Q3 are absent from the method topology, so the key contribution
  (“the internal path can be intervened on”) is not visible in ten seconds.
- The long, shallow aspect ratio makes labels and training branches fragile at
  AAAI paper scale.
- The training band is scientifically correct but too prominent for the first
  conceptual encounter.

### Decision

Reuse its semantic contract, state glyph, color roles, and explicit `b_h + r_h`
closure. Do not reuse its role as the paper’s problem/contribution Figure 1.

## 4. Current Figure 2 audit

Current artifact: `paper/figures/terrastate_operational_verification.pdf`.

### Reusable elements

- One frozen checkpoint feeds all post-training queries.
- Q2 correctly distinguishes the primary closure/state-contribution cut from
  the supporting `T→I` intervention.
- Q3 correctly holds other variables fixed and presents actual, mean, and
  matched-donor weather as parallel arms.
- Q1–Q3 are already color/shape differentiated without displaying result
  numbers.

### Narrative and visual problems

- The verification cards are detached from the actual `q → z_t → T → z_{t+h}
  → O` computation, so a reader cannot see where Q2/Q3 act.
- Q4 occupies a full panel even though composition is not a core validated
  claim.
- The hot-dry stratum is visually prominent despite the frozen evidence
  supporting response fidelity but not extreme-specific enhancement.
- The figure behaves like a protocol dashboard rather than the formal method
  figure requested for Figure 2.

### Decision

Reuse the same-checkpoint, primary/support, and weather-arm distinctions.
Remove Q4 from the core figure and place Q2/Q3 interventions directly on the
method graph.

## 5. Example-material takeaways

The example PPTs and images favor strong left-to-right flow, repeated visual
glyphs for states/features, and explicit panel boundaries. Those devices are
useful. Their dense module inventories, decorative icons, gradients, shadows,
and numerous colors are unsuitable for the AAAI paper figure requirements and
were not copied.

## 6. EO-WM and AAAI layout-reference audit

The following local papers were inspected only as layout references:

- `literature/eo_wm_2606.27277.pdf`;
- `literature/aaai_figure_anchors/aaai26_sparseworld.pdf`;
- `literature/aaai_figure_anchors/aaai25_drive_occworld.pdf`;
- `literature/aaai_figure_anchors/aaai26_knowledge_boundary.pdf`;
- `literature/aaai_figure_anchors/aaai26_worldagen.pdf`.

Reusable layout principles:

- EO-WM uses a strong left-to-right hierarchy from the limitation of endpoint
  prediction, through an explicit world-model mechanism, to behavioral
  evidence. Figure 1 adopts this reading order, but not its artwork, icons, or
  wording.
- SparseWorld compares alternatives using aligned horizontal rows and a common
  endpoint. This supports TerraState's use of aligned Q1/Q2/Q3 evidence cards,
  while avoiding a copied method-comparison composition.
- Drive-OccWorld separates the central model block from its controllable
  inputs and downstream consequences. Figure 2 similarly makes weather enter
  only `T` and keeps the output path explicit, without using its imagery or
  automotive iconography.
- Knowledge Boundary combines a conceptual mechanism with concrete behavioral
  evidence. TerraState retains the distinction between intervention location
  and measured effect, but does not reproduce its ellipse/trajectory motif.
- WorldAgen uses bordered semantic regions and consistent line styles to
  distinguish architecture, training, and evaluation. Figure 2 uses the same
  general information-layering principle, with original geometry and content.

The retained AAAI-compatible choices are compact bordered regions, a single
dominant inference path, and restrained semantic color. No paper-specific
graphic content, raster example, module icon, or distinctive composition was
copied.

## 7. Frozen claim and method consistency

The redesigned figures follow the current English method equations:

`(b_{1:H}, z_t) = q(history)`,
`z_{t+h} = T(z_t, u_{t:t+h}, g, h)`,
`r_h = O(z_{t+h})`,
`y_hat_{t+h} = b_h + r_h`.

They also respect the final evidence boundary:

- Q1: useful temporal-shift forecasting skill is retained; no SOTA claim.
- Q2: the state contribution is load-bearing; `T→I` remains supporting
  evidence because it can create an out-of-distribution readout state.
- Q3: actual weather predicts the observed endpoint better than matched donor
  and normalized mean weather.
- No hot-dry amplification claim.
- No composition claim and no Q4 panel in Figures 1–3.

## 8. Figure 3 data audit

Available and reliable:

- paired Q2 minicube-effect means and their corresponding paired 95% CIs on
  Validation and Temporal shift;
- aggregate Q3 actual-vs-donor and actual-vs-mean loss effects with geographic
  cluster 95% CIs;
- aggregate Q3-subset forecast metrics.

Unavailable:

- a frozen per-cube Q2/Q3 export;
- a provenance-frozen qualitative EO trajectory or spatial case.

The frozen evidence record explicitly says no per-cube dump was produced and
that evaluation must not be rerun. Revision 2 therefore adopts a truthful
two-panel aggregate design: Q2 paired-effect means and Q3 point effects with
their corresponding stored 95% CIs. The figure communicates direction and
uncertainty, while Tables 2–3 retain exact values. No panel (c), qualitative
case, or per-cube distribution is claimed.

## 9. Terminology requiring body-session confirmation

1. `observation decoder`, `state readout`, or `state head` for `O_omega`.
   The figures currently use **state readout**.
2. `context-only forecast` versus `context-only prior` for `b_h`.
   The figures use **context-only forecast** to avoid suggesting a
   probabilistic prior.
3. `matched donor weather` versus `season/geography-matched control`.
   The figures use **matched donor**.
4. `Temporal shift` versus `OOD-t`.
   Figure text uses **Temporal shift**; machine-readable fields may retain
   `ood_t`.
5. `future weather` versus `full24 weather`.
   The figures use the reader-facing **future weather**; the caption can specify
   the 24-channel path if the body session wants that implementation detail.
6. Whether `q` denotes the composite context/state operator or only the
   initialized backbone. Figure 2 keeps `P` explicit, matching the detailed
   method section.

## 10. Audit conclusion

The new hierarchy should be:

1. Figure 1: problem → TerraState state path → Q1/Q2/Q3 evidence.
2. Figure 2: exact method graph with Q2/Q3 intervention locations and compact
   training-only supervision.
3. Figure 3: uncertainty-aware Q2/Q3 aggregate behavioral evidence using the
   frozen estimates and stored confidence intervals.

This resolves the current narrative mismatch without discarding the correct
semantic work already present in the paper figures.
