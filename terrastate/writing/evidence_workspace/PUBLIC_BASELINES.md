# Public baseline source audit

## Primary source

- Vitus Benson et al., “Multi-modal Learning for Geospatial Vegetation
  Forecasting,” CVPR 2024, pp. 27788–27799.
- Official CVF paper:
  <https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html>
- Local frozen paper SHA-256:
  `6162538030e6d13b849a051017a6d25e649ec7c7edb792988a4fa9cd30eb1114`.
- Local frozen supplement SHA-256:
  `886e020279ee68f523b5135af2d919945f489452227f6a4e986545b240f40200`.
- Result location: main paper, Table 2; protocol discussion in Sections 3.4,
  3.5, 4.1 and the supplement.

The publication evaluates vegetation forecasting across Europe in 2021–2022
on its temporal out-of-distribution test and reports \(R^2\), RMSE, NSE,
absolute bias, climatology outperformance, and first-25-day RMSE. The learned
GreenEarthNet models use weather conditioning as described in the paper.

## Original Table 2 means

The values below are copied without changing the means. Uncertainty is omitted
only for compactness.

| Publication group | Method | \(R^2\) | RMSE | NSE | \(|bias|\) | Outperform climatology | RMSE 25 days | Seed reporting |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Non-ML | Persistence | 0.00 | 0.23 | -1.28 | 0.17 | 21.8% | 0.09 | deterministic |
| Non-ML | Previous year | 0.56 | 0.20 | -0.40 | 0.14 | 19.3% | 0.18 | deterministic |
| Non-ML | Climatology | 0.58 | 0.18 | -0.34 | 0.13 | n.a. | 0.16 | deterministic |
| This study | ConvLSTM | 0.58 | 0.16 | -0.13 | 0.11 | 53.1% | 0.11 | mean of 3 seeds |
| This study | Earthformer | 0.52 | 0.16 | -0.13 | 0.10 | 56.5% | 0.09 | 1 seed |
| This study | PredRNN | 0.62 | 0.15 | 0.03 | 0.10 | 64.7% | 0.10 | mean of 3 seeds |
| This study | SimVP | 0.60 | 0.15 | 0.03 | 0.09 | 64.1% | 0.10 | mean of 3 seeds |
| This study | Contextformer | 0.62 | 0.14 | 0.09 | 0.09 | 66.8% | 0.08 | mean of 3 seeds |

The Table 2 caption says mean ± standard deviation is computed from three
random seeds, while the adjacent text explicitly states that Earthformer has
one seed. Thus neither “all public values are single-seed” nor “all public
values are three-seed means” is correct.

Recommended compact note:

> For compactness, we report mean performance from the original publications
> and omit uncertainty estimates.

Add the seed clarification when space permits.

## Selection for Table 1

Table 1 uses Climatology, ConvLSTM, PredRNN, and Contextformer:

- Climatology anchors the seasonal-cycle baseline.
- ConvLSTM is a recurrent weather-conditioned baseline.
- PredRNN is the strongest selected video-prediction adaptation by published
  \(R^2\).
- Contextformer is the task-specific public reference.

Earthformer and SimVP remain verified in this audit but are omitted from the
compact table. No public value was lowered, rounded selectively, or converted
from a local reproduction.

## Comparability adjudication

| Comparison | Status | Reason |
|---|---|---|
| Published methods with one another in GreenEarthNet Table 2 | Strict within the publication | Same publication table and stated evaluation protocol; seed counts differ and are disclosed. |
| TerraState with its own Q2/Q3 interventions | Strict within checkpoint/protocol | Same frozen checkpoint and paired evaluation, subject to each intervention's stated caveats. |
| TerraState vs published GreenEarthNet methods | **Not proven strict** | Same benchmark and nominal OOD-t family, but the publication does not expose TerraState's exact manifest SHA or evaluator revision; TerraState is one frozen run. |
| TerraState vs local matched-backbone reproduction | Nominally same local family, but not ledger-verifiable here | The exact local matched-backbone numbers occur in narrative summaries, but no release-level raw JSON with field paths was found. It is excluded from Table 1. |
| Q3 vs EO-WM extreme diagnostics | Not comparable | TerraState Q3 is an internal 84-pair stress test with its own matching protocol, not the EO-WM external diagnostic benchmark. |

Table 1 therefore uses separate panels and must not be described as a strict
leaderboard.
