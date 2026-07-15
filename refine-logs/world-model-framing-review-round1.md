# World-Model Framing Review — Round 1

**Date**: 2026-07-15  
**Reviewer verdict**: viable and preferable to correction-only framing  
**Overall**: 8.9 / 10 before requested revisions

## Core Verdict

The proposed rewrite is viable. The prior documents retreated too far from world modeling while avoiding overclaim, compressing the system-level research problem into a local update module and weakening significance. The recommended hierarchy is:

- mother narrative / system identity: observation-correctable Earth observation world model for sparse, cloudy observations;
- sole method novelty: observation-aligned residual correction;
- evidence: one belief-state model supports both open-loop rollout and partial-observation correction;
- boundary: EO-observable Earth-surface dynamics under supplied forcing, not complete geophysics or a causal digital twin.

Do not abandon world modeling; abandon first-claim, physical-state equivalence, complete-Earth simulation, causal weather response, and recurrence-as-novelty.

## Recommended Title and Thesis

> **ObsWorld: An Observation-Correctable World Model for Sparse Earth Observation Forecasting**

> **We cast sparse Earth observation forecasting as belief-state world modeling: ObsWorld rolls a history-dependent predictive belief forward under supplied forcing, decodes future satellite observations, and corrects that belief from visibility-aligned observation residuals, improving subsequent rollouts without sacrificing open-loop forecast accuracy.**

At proposal stage, use “we hypothesize” before results exist.

## Contract Audit

| Requirement | Mapping | Verdict |
|---|---|---|
| history-dependent predictive state | sequential `b_t` from all context via shared `F/U` | satisfied; call belief, not physical state |
| temporal dynamics | shared `F_5` | satisfied; recurrence is not novelty |
| exogenous conditioning | weather, DOY, DEM/geography | structurally satisfied; forcing-use evidence required |
| observation model | `H(b_t)` to RGBN/NDVI | minimum condition satisfied; call learned decoder/model, not physical renderer |
| partial-observation inference | `U(b_t^-,r_t,q_t,s_t)` | satisfied and distinctive |
| open-loop imagination | future `a=0`, repeated `F_5/H` | satisfied; official 100-day forecast is evidence |
| belief correction | aligned innovation then future rollout | satisfied; primary novelty and experiment |
| stochastic uncertainty | absent | acceptable for deterministic WM; no multimodal/calibration claim |
| actions/planning | no action, supplied forcing only | acceptable for EO; say forcing-conditioned predictive WM |
| physical/causal state | unidentifiable | not required, but enforce boundary |

## Experiment Revision Requested

1. Rename Block A to **Open-Loop Earth-Observation World Rollout**; retain official full-20 results and add horizon-wise degradation.
2. Rename Block B to **Partial-Observation Belief Correction**; interpret it as a defining world-model behavior.
3. Rename Block C to **World-Model Contract and Mechanism Ablations**; retain residual/fusion, identity, mask invariance, q/staleness checks.
4. Promote minimal forcing-alignment evidence to required support: independently trained true/no-weather and same-checkpoint correct-time vs time-shuffled/wrong-year. It can show driver use, not causality.
5. Keep unrelated downstream and FM out until the core mechanism succeeds.

## Claim Boundaries

- not first EO world model;
- not a unique physical-state recovery;
- not complete Earth/climate/ecosystem digital twin;
- not causal/counterfactual weather response;
- not operational forecast with future oracle/reanalysis forcing;
- `H` is learned product-specific observation model, not radiative transfer;
- deterministic rollout, no calibrated or multimodal uncertainty claim;
- no cross-sensor acquisition-invariant claim;
- world model is system identity; aligned residual is the method novelty.

## Scores

| Dimension | Score |
|---|---:|
| Novelty | 8.5 |
| Technical Soundness | 9.1 |
| Feasibility | 9.2 |
| Clarity | 8.6 |
| Impact | 9.1 |
| Reproducibility | 9.5 |
| Overall | 8.9 |

Reviewer expected 9.2 after: restoring the two-level hierarchy, consistently naming observation-correctable EO WM, downgrading `H` to learned observation model, organizing experiments as three RQs, requiring minimal forcing alignment, limiting real-world simulation to EO-observable dynamics, and distinguishing ObsWorld from EO-WM.
