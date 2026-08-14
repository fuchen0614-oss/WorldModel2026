# Figure 3 data provenance

`terrastate_behavioral_evidence.csv` is a writing-side transcription of the
frozen evidence record:

`WorldModel2026-planb/TERRASTATE_V2_EVIDENCE.md`

The source SHA-256 is:

`dcb5f9c0143a1d58e19d1732a9348215392278f266d2348c0ef87988e0ca86da`

No model, training, evaluation, bootstrap, or per-sample computation is run by
the figure script. The CSV contains only values already present in the frozen
record. The record states that no per-cube export was produced, so Figure 3
uses stored aggregate effects and confidence intervals rather than a fabricated
sample distribution or qualitative panel.
