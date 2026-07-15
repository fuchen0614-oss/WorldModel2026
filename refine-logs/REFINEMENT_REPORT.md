# Refinement Report

**Problem**: 稀疏/云遮 EO 的长期 predictive state 与再观测校正。  
**Initial approach**: acquisition-aware representation、shared rollout、weather response与多套实验并行。  
**Date**: 2026-07-15  
**Rounds**: 5 / 5  
**Final score**: 9.2 / 10  
**Final verdict**: READY

## Output Files

- Clean final proposal: `refine-logs/FINAL_PROPOSAL.md`
- Review summary: `refine-logs/REVIEW_SUMMARY.md`
- Experiment roadmap: `refine-logs/EXPERIMENT_PLAN.md`
- Execution tracker: `refine-logs/EXPERIMENT_TRACKER.md`
- Full score history: `refine-logs/score-history.md`
- Raw reviews: `refine-logs/round-1-review.md` through `round-5-review.md`
- World-model framing decision: `refine-logs/WORLD_MODEL_FRAMING.md`
- Framing audit: `refine-logs/world-model-framing-review-round1.md` and `world-model-framing-review-round2.md`

## Score Evolution

| Round | Problem Fidelity | Method Specificity | Contribution Quality | Frontier Leverage | Feasibility | Validation Focus | Venue Readiness | Overall | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 8.0 | 6.0 | 4.0 | 6.0 | 5.0 | 4.0 | 4.0 | 5.5 | RETHINK |
| 2 | 8.5 | 7.0 | 6.5 | 7.5 | 6.0 | 7.5 | 6.0 | 7.1 | REVISE |
| 3 | 9.0 | 8.0 | 7.0 | 8.5 | 7.5 | 8.5 | 6.5 | 7.9 | REVISE |
| 4 | 9.3 | 8.8 | 8.5 | 9.0 | 8.8 | 8.4 | 8.3 | 8.8 | REVISE |
| 5 | 9.5 | 9.4 | 8.7 | 9.2 | 9.1 | 9.5 | 8.9 | 9.2 | READY |

## Final Proposal Snapshot

- system identity is an observation-correctable EO world model；aligned residual is the sole method novelty；
- shared `F_5` sequentially filters context and advances future predictive belief；
- real observation and prior decoded prediction are masked identically and encoded by the same `E/P`；
- their residual enters a q/staleness-gated update with exact no-evidence identity；
- reveal-time update is trained only through later forecast consequences；
- official open-loop and correction-specific paired evaluation are strictly separated；
- forcing alignment is required supporting evidence but not a parallel contribution；Stage1.5, FM and downstream remain optional/cut。

## Post-READY Framing Audit

The user correctly challenged the correction-only presentation. A two-round audit restored world modeling as the mother narrative while preserving all claim boundaries. Framing score improved from 8.9 to 9.3 (READY). The frozen hierarchy is:

1. world model = system-level problem and identity；
2. aligned residual = method-level novelty；
3. open-loop rollout + partial-observation correction + contract checks = empirical evidence；
4. simulated target = EO-observable Earth-surface evolution under supplied forcing, not complete physical Earth。

## Key Pushback / Drift Decisions

| Reviewer pressure or tempting route | Decision | Outcome |
|---|---|---|
| Add FM/LLM/diffusion for modernity | rejected as unrelated to belief-observation interface | focus improved |
| Keep Stage1.5 factorization as co-primary claim | rejected; fixed-product GreenEarthNet does not exercise phi end-to-end | moved to optional init row |
| Call five-day recurrence semigroup/composition novelty | rejected; recurrence is architecture definition | replaced by measurable forecast/correction behavior |
| Use full EarthNet/EO-WM weather benchmark | rejected unless weather response remains a claim | weather becomes benchmark forcing/sanity only |
| Add unrelated downstream | rejected | re-observation becomes the direct capability test |

## Remaining Weaknesses

- No Stage1.5 or Stage2 result currently exists locally；READY is proposal readiness, not evidence readiness。
- Innovation is a narrow EO data-assimilation contribution, not new general filtering theory。
- Actual paper claim fails if open-loop is inferior, Vanilla/PredRNN-online match correction, or gains appear only in high-clear cases。
- Protocol/evaluator/weather/export engineering must be corrected before any formal training。

## Next Steps

Freeze the method and the restored world-model narrative. Implement only the protocol gates and one-seed core systems in the order specified by `EXPERIMENT_PLAN.md`; run three seeds only after the one-seed claim gate passes.
