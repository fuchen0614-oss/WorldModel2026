# TerraState Supplement Fact Freeze

Status: **FROZEN**

## Authority and scope

The formal title is *TerraState: A Testable Predictive-State World Model for
Weather-Driven Land-Surface Forecasting*. The governing evidence is the formal
submission (`TerraState_AAAI27/paper/main.tex` and `main.pdf`), its final
tables, the final evidence ledger, the verified implementation, and the
authoritative author confirmation dated 2026-07-30 UTC.

The author confirmed that all submitted Q1--Q3 results correspond to the
completed 40-epoch, 14,880-update run. Earlier intermediate selection and
release-provenance records are **STALE / EXCLUDED** and are not release
evidence.

## Frozen questions

| Question | Frozen definition | Primary sources |
|---|---|---|
| Q1 | Whether TerraState retains useful predictive performance on the OOD-t evaluation. | `paper/main.tex`, Sec. 4.1 and Table 1; `evidence_workspace/results_ledger.json`, Q1 record |
| Q2 | Whether the explicit predictive-state contribution and shared transition carry the final prediction rather than serving only as architectural decoration. State removal is primary; identity transition is supporting. | `paper/main.tex`, Secs. 3.5 and 4.3, Table 2; `evidence_workspace/RESULTS_LEDGER.md`, Q2 |
| Q3 | Whether actual future weather gives better complete-window conditional fidelity than matched-donor and normalized-mean controls on the frozen heat--drought subset. | `paper/main.tex`, Secs. 3.5 and 4.4, Table 3; `evidence_workspace/RESULTS_LEDGER.md`, Q3 |

## Model and data facts

| Item | Frozen fact | Primary sources |
|---|---|---|
| Input modalities | Cloud-masked Sentinel-2 optical history, past meteorology, static geography, and future meteorology supplied only to the shared transition. | `paper/main.tex`, Secs. 3.2--3.4; `WorldModel2026-planb-v2train/data/en21x_dataset.py` |
| Tensor contract | 30 five-day composites at \(128\times128\): 10 context steps and 20 forecast steps (100 days). Optical input has 5 channels, weather has 24, static input has 5. | `paper/main.tex`, Secs. 3.1 and 4.1; `WorldModel2026-planb-v2train/data/en21x_dataset.py` |
| Context-only forecast | \(q_\theta\) emits \(b_{1:H}\) and final-context tokens using historical observations, past weather, and static inputs; future image and weather inputs are masked or zeroed in this pass. | `paper/main.tex`, Eqs. 1--2 and Sec. 3.3; `WorldModel2026-planb-v2train/models/terrastate_v2.py` |
| Predictive-state construction | A normalized two-layer projector maps final-context patch tokens to \(z_t\); state shape is \([1024,256]\) per minicube. | `paper/main.tex`, Sec. 3.3; `WorldModel2026-planb-v2train/models/terrastate_v2.py` |
| Shared transition | A shared GRU encodes the ordered future-weather prefix; fusion conditions on weather, patch geography, and elapsed horizon; every \(z_{t+h}\) is queried directly from the same \(z_t\). | `paper/main.tex`, Eqs. 3--4 and Sec. 3.3; `WorldModel2026-planb-v2train/models/terrastate_v2.py` |
| State readout | The readout maps each 256-dimensional token to a local \(4\times4\) patch and unpatchifies to the image grid. | `paper/main.tex`, Eq. 5 and Sec. 3.4; `WorldModel2026-planb-v2train/models/terrastate_v2.py` |
| Final prediction | \(\widehat y_{t+h}=b_h+r_h\), with fixed non-learnable state scale \(\alpha=1\). | `paper/main.tex`, Eq. 6; `WorldModel2026-planb-v2train/models/terrastate_v2.py` |
| Parameter count | 7,180,896 trainable model parameters in the public configuration. | `paper/main.tex`, implementation paragraph; verified CPU construction of the staged `models/terrastate.py` |
| Objective | \(\mathcal L=\mathcal L_{\rm GT}+0.5\mathcal L_{\rm KD}+\lambda_s\mathcal L_{\rm FS}\); the future-state term anchors only the terminal advanced state. | `paper/main.tex`, Sec. 3.4; `WorldModel2026-planb-v2train/train/train_terrastate_v2.py` |

## Training facts

| Item | Frozen fact | Primary sources |
|---|---|---|
| Duration | 40 epochs; exactly 14,880 optimizer updates. | `paper/main.tex`, lines 534 and 580; author confirmation, 2026-07-30 |
| Optimizer | AdamW, \(\beta=(0.9,0.999)\), zero weight decay, global gradient-norm clipping at 1.0. | `paper/main.tex`, Sec. 4.1; verified training implementation |
| Learning rates | \(3\times10^{-5}\) for non-history parameters; \(9.9\times10^{-7}\) for the history-operator parameter group. | `paper/main.tex`, Sec. 4.1; verified training implementation |
| LR schedule | Linear warm-up for 300 optimizer updates, followed by cosine decay. | `paper/main.tex`, Sec. 4.1; verified training implementation |
| Batch and precision | Global batch 64: 8 devices \(\times\) 8 samples, no accumulation; FP32. | `paper/main.tex`, Sec. 4.1; verified launch/configuration records |
| Hardware | 8 NVIDIA H200 GPUs. | `paper/main.tex`, Sec. 4.1 |
| Parameter schedule | History operator frozen through 80% of updates; only its final Transformer block is unfrozen for the final 20%. Other TerraState branches train throughout. | `paper/main.tex`, Sec. 3.4; verified training implementation |
| State-loss schedule | \(\lambda_s\) ramps 0 to 0.02 over the first 20%, remains 0.02 through 80%, and is 0.01 for the final 20%. | `paper/main.tex`, Sec. 3.4; verified training implementation |
| Randomness and selection | Seed 42, one completed training run. Selection uses validation forecast performance; Q2, Q3, and OOD-t do not select the model. | `paper/main.tex`, Secs. 4.1--4.2; `ReproducibilityChecklist.tex` |

## Dataset and Q1 protocol

| Item | Frozen fact | Primary sources |
|---|---|---|
| Splits | GreenEarthNet training, validation, and OOD-t partitions; OOD-t is held out from selection. | `paper/main.tex`, Secs. 4.1--4.2; `ReproducibilityChecklist.tex` |
| Preprocessing | Five-day optical composites; NDVI from near-infrared and red; missing optical values zero-filled after mask construction; learned cloud mask combined with valid scene classes; normalized weather aggregated by mean/min/max; elevation divided by 500. | `paper/main.tex`, Sec. 4.1; `WorldModel2026-planb-v2train/data/en21x_dataset.py` |
| Valid pixels | Official clear-target rule and declared vegetation land-cover range. | `paper/main.tex`, Secs. 4.1--4.2; verified scorer code |
| Q1 scorer | Pixel-time-series quantities balanced over minicubes and vegetation land-cover classes. Higher is better for \(R^2\) and NSE; lower is better for RMSE, absolute bias, and \(\mathrm{RMSE}_{25}\). | `paper/main.tex`, Sec. 4.2 and Table 1; verified scorer code |
| Q1 output | 20 NDVI prediction frames on target timestamps with source latitude/longitude coordinates; package CLI writes `q1_metrics.json`. | verified evaluation implementation; staged `eval/evaluate_forecast.py` |

## Frozen results allowed in the Supplementary PDF

### Q1: OOD-t forecast

| Metric | Exact frozen value |
|---|---:|
| Number of targets | 1,904 |
| \(R^2\) | 0.5693493611664086 |
| RMSE | 0.1505941190915099 |
| NSE | -0.098656 |
| Absolute bias | 0.100829 |
| \(\mathrm{RMSE}_{25}\) | 0.0820498 |

Sources: `paper/main.tex`, Table 1; `evidence_workspace/results_ledger.json`,
Q1; final paper tables.

Verified OOD-t horizon-block RMSE values are 0.0820498, 0.1293617,
0.1602056, and 0.1679543. Forest, shrub, grass, and crop \(R^2\) values are
0.552058, 0.556196, 0.584470, and 0.584673; corresponding RMSE values are
0.147263, 0.147816, 0.145102, and 0.162196. Sources:
`evidence_workspace/results_ledger.json` and the final evidence tables.

### Q2: load-bearing state

| Split | Arm | \(R^2\) | RMSE | Official \(\Delta R^2\) | Paired mean \(\Delta R^2\) [95% CI] |
|---|---|---:|---:|---:|---:|
| Validation | Full | 0.49732 | 0.15729 | reference | -- |
| Validation | State removed | 0.48611 | 0.17101 | 0.01121 | 0.01616 [0.00643, 0.02590] |
| Validation | Identity transition | 0.48542 | 0.26102 | 0.01191 | 0.01742 [0.00782, 0.02696] |
| OOD-t | Full | 0.56935 | 0.15059 | reference | -- |
| OOD-t | State removed | 0.54938 | 0.16519 | 0.01997 | 0.02200 [0.01422, 0.03018] |
| OOD-t | Identity transition | 0.54766 | 0.25832 | 0.02169 | 0.02402 [0.01609, 0.03217] |

The paired bootstrap uses 10,000 replicates. Validation has 952 targets and
589 paired metric units; OOD-t has 1,904 targets and 1,019 paired units.
Sources: `paper/main.tex`, Table 2 and Sec. 4.3;
`evidence_workspace/RESULTS_LEDGER.md`, Q2.

### Q3: weather-response fidelity

The frozen subset has 84 matched pairs, 45 unique donors, and 31 geographic
clusters. The intervention keeps history, initial state, geography, targets,
masks, readout, and parameters fixed, while replacing only future weather
with actual, season/geography/quality-matched donor, or normalized-mean
weather. Complete-window masked MSE is primary. The geographic-cluster
bootstrap uses 10,000 replicates.

| Future weather | \(R^2\) | RMSE | Control-minus-actual loss [95% CI] | Actual-lower count |
|---|---:|---:|---:|---:|
| Actual | 0.6254 | 0.1492 | reference | -- |
| Matched donor | 0.5893 | 0.1584 | 0.00257 [0.00112, 0.00399] | 56 / 84 |
| Normalized mean | 0.5430 | 0.1971 | 0.01126 [0.00547, 0.01708] | 69 / 84 |

Mean absolute forecast differences are 0.03592 for actual versus donor and
0.08137 for actual versus normalized mean. Sources: `paper/main.tex`, Table 3
and Sec. 4.4; `evidence_workspace/RESULTS_LEDGER.md`, Q3; final table files.

## Evidence boundaries

- Q2 supports that the exposed state contribution is load-bearing and that
  the shared transition is involved in the current model. It does not establish
  a complete physical state or component-wise optimality.
- Q3 is a controlled conditional-response and conditional-fidelity test. It is
  not causal identification or proof of a valid real-world counterfactual.
- No Q4, composition claim, new dataset, new ablation, state-of-the-art claim,
  or heat--drought-specific enhancement is admitted.
- Unverified implementation details and untraceable numbers are excluded.
