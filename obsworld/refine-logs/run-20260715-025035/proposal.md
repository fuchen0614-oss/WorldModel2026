# ObsWorld refined proposal — round 0

Date: 2026-07-15

## 1. Decision in one sentence

ObsWorld should be presented as an **observation-grounded predictive-state model for sparse Earth observations**: it infers an acquisition-robust predictive state from heterogeneous observations, advances that state with one shared five-day transition under observed weather forcing, and decodes or corrects it when new observations become available.

The paper must not claim the first EO world model, a recovered physical ground-truth state, causal counterfactual simulation, or operational forecasting.

## 2. Problem and gap

The strongest recent competitors already cover the obvious claims:

- Contextformer provides a strong weather-conditioned GreenEarthNet forecaster and an official vegetation evaluation protocol.
- UniTS performs autoregressive raw-reflectance forecasting and unifies forecasting with reconstruction/cloud removal/change detection.
- EO-WM explicitly formulates EO forecasting as a partially observed, weather-driven world-model problem and adds weather-response diagnostics.

The remaining defensible gap is not merely weather conditioning or autoregression. Existing methods generally optimize future observations as frames or cuboids. They do not jointly establish that:

1. acquisition factors belong to an observation process rather than the evolving land-surface process;
2. one latent short-step transition composes over horizons and explains withheld intermediate observations;
3. the predicted state can be corrected by a later observation and then rolled forward again.

This gap is of broader AI interest because it asks what empirical evidence is required before a latent video forecaster should be called a world model under partial observation.

## 3. Operational formulation

For observation `o_t`, acquisition condition `phi_t`, calendar `c_t`, exogenous driver interval `d_t`, and static geography `g`:

```text
e_t       = E(o_t, phi_t, mask_t)
b_0       = A({e_i, timestamp_i, mask_i}_{i in context})
b_{k+1}^- = b_k + F_theta(b_k, d_k, c_{k+1}, g, delta_t)
o_hat     = H(b_{k+1}^-, phi_{k+1})
b_{k+1}^+ = U(b_{k+1}^-, E(o_{k+1}, phi_{k+1}), mask_{k+1})   [optional]
```

`b_t` is a learned predictive state or belief state. It is defined by predictive sufficiency and observation consistency, not identified with the true biophysical state.

Variable roles must remain disjoint:

- `phi`: sensor/product/view geometry and acquisition quality known at inference;
- `c`: day-of-year/season;
- `d`: weather over the current five-day transition interval;
- `g`: static DEM in the primary model;
- `delta_t`: elapsed time;
- horizon `h`: used only by the direct multi-horizon control, not by the shared five-day transition.

Latitude/longitude are excluded from the primary model to reduce geographic shortcut learning. Land-cover labels are used for stratified evaluation, not as inputs.

## 4. Stage 1.5 gate

The repaired state-bridge checkpoint is a prerequisite. The older 60k checkpoint in the current Stage2 config was trained before reconstruction was forced through the state projector and therefore is not adequate evidence for a state bottleneck.

The S1/S2 objective should be described as learning a cross-sensor predictive common representation, not strict acquisition invariance: SAR and optical observations contain complementary physical information. If a strict observation-factorization claim is retained, it needs same-acquisition product pairs such as S2 L1C/L2A. Otherwise, use a shared/private representation or soften the claim.

Stage 1.5 passes only if, on held-out geography:

- state-bridge reconstruction is competitive with the bypass control;
- future-NDVI/predictive probes improve over Stage1 and scratch;
- acquisition probes use disjoint train/validation/test data, actual conditioned encoder paths, multiple seeds, balanced metrics, and calendar/geography controls;
- correct `phi` beats missing/swapped/wrong `phi` in reconstruction while the state does not trivially encode it.

Failure of this gate does not kill Stage2; it changes Stage1.5 from a core contribution to an initialization ablation.

## 5. Stage2-D: controlled direct baseline

Keep a repaired version of the current direct model as a control:

```text
b_hat_h = F_direct(b_0, aggregate(d_1:h), c_h, g, h)
```

It predicts each horizon independently. Its purpose is factual forecast competitiveness and a matched comparison against compositional rollout. It must not be called rollout or a learned step-wise world model.

Repairs required before using this control:

- load the state-bridge checkpoint rather than the legacy 60k checkpoint;
- separate calendar features from weather features;
- use actual timestamps/time gaps in context aggregation;
- use an EMA or frozen target encoder for latent supervision;
- select checkpoints with the official GreenEarthNet validation evaluator, not generic MAE alone;
- remove or ablate the generic temporal smoothness term.

## 6. Stage2-R: proposed shared-step model

### 6.1 Driver construction

Each transition receives weather only for its own five-day interval. Recommended initial features are precipitation sum, mean temperature, mean/max VPD, and solar-radiation sum, with missingness masks. DOY sine/cosine are routed separately as calendar features.

The current cumulative-from-context features remain only in Stage2-D. Feeding them to every recurrent step double-counts past forcing and prevents clean compositional interpretation.

### 6.2 Objectives

Use two training branches sharing the same transition:

1. one-step anchored branch: predict the next encoded observation state from an encoded valid current observation;
2. free-rollout branch: initialize from the ten-frame context and recurrently apply the transition for a randomly selected rollout length.

At clear target pixels/patches, supervise:

- masked four-band Charbonnier or Huber observation loss;
- masked NDVI loss;
- token-level cosine plus smooth-L1 loss to a stop-gradient EMA target encoder;
- a small valid-range penalty.

Do not introduce a KL term unless a genuine stochastic latent distribution is implemented. Do not describe weather sweeps as causal counterfactuals.

A starting loss, to be calibrated by gradient norms on the training split, is:

```text
L = 1.0 L_reflectance + 0.5 L_NDVI + 0.25 L_latent
  + 0.5 L_one-step + 0.01 L_range
```

### 6.3 Curriculum

- R0, 0–5k updates: freeze the image encoder/state projector; train adapters, context aggregator, transition, and decoder with one-step and rollout lengths 1/2/4.
- R1, 5k–40k: train lengths 1/2/4/8/12 with free-rollout weight ramped upward; keep the EMA target encoder frozen from gradients.
- R2, 40k–60k: include length 20; unfreeze the last two encoder blocks and state projector at 0.1x backbone learning rate; retain a one-step auxiliary term.

This is an initial schedule, not a claimed optimum. Early stopping and hyperparameter selection must use an internal geographically disjoint validation split. Official OOD tracks remain locked until the design is fixed.

## 7. Claims and falsification tests

### C1 — observation-grounded state

Claim: the state/observation split improves acquisition robustness without erasing predictive surface information.

Evidence: correct/missing/swapped `phi`; cross-product reconstruction; acquisition, semantic, and future-prediction probes on held-out geography; state-bridge versus bypass.

Falsifier: acquisition leakage falls only because land-surface/phenology information is also erased, or Stage1.5 gives no forecasting benefit.

### C2 — compositional transition

Claim: a shared short-step latent transition maintains competitive endpoint forecasts and better intermediate-state consistency than an independently parameter-matched direct horizon model.

Evidence: direct versus rollout with the same encoder, decoder, parameters, data, and compute; error by 5/25/50/75/100-day horizon; free versus teacher-anchored rollouts; withheld intermediate observations; semigroup/composition consistency.

Falsifier: rollout is worse at endpoints and intermediate horizons without compensating consistency, robustness, efficiency, or assimilation benefit.

### C3 — driver-response fidelity

Claim: the transition uses weather trajectories beyond calendar/geographic correlations.

Evidence: true weather, no weather, calendar only, within-season shuffled weather, and wrong-year same-location weather; natural matched-pair response metrics.

Falsifier: shuffled/wrong-year weather performs equivalently, or sensitivity changes without agreement with observed response direction/magnitude.

### C4 — correction by re-observation (stretch)

Claim: a later valid observation can reduce state error and improve subsequent forecasts.

Evidence: open-loop versus one observation inserted at day 25 or 50, then a continued rollout; compare against a naive latent replacement control.

This is the best world-model-style downstream capability, but it should be moved to the appendix if implementation risks the core paper.

## 8. Experiment hierarchy

### Primary benchmark: GreenEarthNet

Train on its official training data, tune on a geographically disjoint training holdout, then report the official OOD-t, OOD-s, and OOD-st tracks separately. The main headline is OOD-t because it matches the Contextformer paper; spatial and spatiotemporal OOD provide generalization evidence.

Use the unchanged official evaluator and report R², RMSE, NSE, absolute bias, climatology outperformance, and RMSE25, macro-averaged as specified. Generic full-image MAE/PSNR/SSIM can be secondary raw-reflectance metrics, not replacements.

Main baselines:

- persistence, previous year, climatology;
- ConvLSTM, PredRNN, SimVP, Earthformer, Contextformer;
- current repaired direct ObsWorld;
- shared-step ObsWorld;
- UniTS when executable code/checkpoints permit a same-protocol run. Its paper-only PSNR/SSIM numbers are not directly comparable to official GreenEarthNet metrics.

### Secondary diagnostic benchmark: original EarthNet2021

If resources allow, retrain the direct and rollout variants on EarthNet2021 and run the public EO-WM Extreme Summer and Seasonal Matched-Pair CSV protocols. This creates a same-protocol comparison with the closest 2026 competitor and is more valuable than an unrelated classification downstream task.

Do not transfer headline numbers between EarthNet2021 and GreenEarthNet.

### Mechanism dataset

Use SSL4EO-S12 or a controlled S2 product-pair subset only for the observation-factorization tests. This is a mechanism experiment, not a claim that the forecast model cross-dataset generalizes.

## 9. Main paper tables/figures

1. Main forecast table: GreenEarthNet OOD-t official metrics, parameters, FLOPs, and inference time.
2. OOD table: OOD-t/OOD-s/OOD-st, compact primary metrics.
3. Composition figure/table: error curves by horizon; direct, one-step teacher anchored, and free rollout.
4. State/observation mechanism table: state bridge, `phi` interventions, semantic/acquisition/predictive probes.
5. Driver-response table: true/no/calendar/shuffle/wrong-year, plus matched-pair diagnostics if EarthNet2021 is included.
6. Compact ablation table: pretraining, state bridge, per-step drivers, EMA target, rollout curriculum, and loss terms.

For the core model and matched direct control, use at least three seeds. Report mean and standard deviation, cube-level paired bootstrap 95% intervals, and a paired test on per-cube errors. Do not treat millions of pixels as independent samples.

## 10. Downstream and foundation-model decision

A downstream task is not mandatory for a task-specific forecasting/world-model paper. Contextformer and EO-WM establish their claims without an unrelated downstream classification suite. Broad downstream transfer becomes mandatory only if the claim is a general-purpose foundation representation, as in AnySat/TerraMind-style work.

If one application is added, choose predicted vegetation-decline onset/severity or re-observation assimilation because it tests the dynamics claim. CropHarvest and Sen1Floods11 should not enter the main paper unless the paper pivots to a general representation claim.

The “large model + ours” idea is not useless, but it is a Stage4 control, not a contribution. Use a 2x2 design:

```text
light encoder + direct      light encoder + rollout
FM encoder    + direct      FM encoder    + rollout
```

This tests whether gains come from the transition design or merely a stronger backbone. Run it only after the light-model claim closes; AnySat or TerraMind is preferable to an LLM because the inputs are EO observations.

## 11. Submission decision

AAAI is a conference, not a journal. AAAI-27 abstracts are due 2026-07-21 and full papers 2026-07-28. With no local Stage2 result artifacts, this proposal is not presently evidence-ready for AAAI-27. A submission should proceed only if remote experiments already provide a clean direct baseline, repaired Stage1.5 checkpoint, and enough time for shared-step and official evaluation runs. Otherwise, target the next suitable cycle rather than locking weak claims around incomplete results.

## 12. Go/no-go gates

- G0 data/protocol: exact split manifests, official evaluator parity, no silent root fallback or mixed OOD tracks.
- G1 state: repaired state-bridge checkpoint and valid probes.
- G2 forecast: direct baseline reproduces a credible official score.
- G3 method: rollout supports C2 on at least two independent dimensions.
- G4 behavior: weather controls support C3.
- G5 scope: optional EarthNet2021 diagnostics, assimilation, and foundation-model 2x2 only after G0–G4.

The paper proceeds with the full ObsWorld narrative only if G1–G4 pass. Otherwise the narrative must shrink to exactly what the experiments support.
