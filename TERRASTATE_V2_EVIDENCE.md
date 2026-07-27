# TerraState-V2 — boundary80 Evidence (Q1 / Q2 / Q3)

Frozen final checkpoint of the doc-88 unique training line. All numbers below are from formal,
frozen-protocol evaluations on the same checkpoint. Provenance is recorded per section.

## Model & frozen checkpoint
- **Model**: `TerraStateV2` — history → q → context-only state `z_t` (reads NO future weather);
  `y = prior + alpha · O( T(z_t, full24_weather, geo, h) )`, `alpha = 1` (fixed). Future weather can
  reach the output **only** through the shared transition `T`; the prior is structurally weather-free.
- **Checkpoint**: `runs/terrastate_v2/run1/checkpoint_boundary80.pt` (step 11904, stage 2).
  - `file_sha256 = 644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd`
  - `weight_sha256 = aba100c138119bc0…` · `arch = TerraStateV2` (loaded on the exclusive T-only route).
- **Commits**: V2 code `52578ca` (branch `plan-b-v2-train`); evaluator `4dce19a` (branch `plan-b-pvt`).
- **Selection (frozen, before viewing Q2)**: pre-registered candidates `{boundary80, fsval_best, last}`
  (`last` == `fsval_best` by weight SHA → deduped). Neither passed the internal Q1 qualifier →
  **fallback: pick the best-Q1 pre-registered candidate = `boundary80`** (NOT chosen by any Q2 margin).

## Q1 — public usability (official LC-balanced R2, `val_chopped`, bs=1)
| metric | value | gate | result |
|---|---|---|---|
| R2 | **0.49732** | ≥ 0.502 | short by 0.0047 |
| RMSE | **0.15729** | ≤ 0.156 | over by 0.0013 |

→ **Q1 = SHORT** (usable but below the accuracy qualifier). Accuracy anchor = full-weather Phase-I B4 ≈ 0.512.

## Q2 — load-bearing core hard gate (`val_chopped`, bs=1, evaluator 0ca6750)
- full R2 `0.49732` · alpha0 (== frozen weather-free prior) R2 `0.48610754` · T_identity R2 `0.48542`.
- **closure** (full − alpha0) ΔR2 = **+0.01121**, paired bootstrap 95% CI **[+0.00643, +0.02590]** sig>0, ≥ floor 0.005.
- transition (full − T_identity) ΔR2 = +0.01191, CI [+0.00782, +0.02696] sig>0.
- invariants all pass (alpha0 == prior; T_identity == state-identity; live-weights restored). `clean=False`
  is only the OOD-confounded transition arm — the **closure** cut (the honest test) passes on its own.
- **VERDICT = LOAD_BEARING ✅** — the weather-driven state materially and significantly improves the
  forecast over the weather-free prior.

## Q3 — weather response fidelity (frozen `extreme_audit_oodt_v1`, `--evidence-role final`, evaluator 4dce19a, n_pairs=84)
Frozen protocol SHA: hotdry `f8db1ccb…`, matched_normal `84a09421…`, protocol `570a0c36…`, thresholds `1c20cd71…`.

- **endpoint fidelity (geo-cluster PRIMARY; paired also shown)**:
  | arm | ΔLoss | geo-cluster 95% CI | paired 95% CI |
  |---|---|---|---|
  | actual vs **donor** (season/geo-matched wrong weather) | +0.00257 | [+0.00112, +0.00399] sig | [+0.00120, +0.00398] sig |
  | actual vs **mean** (climatology) | +0.01126 | [+0.00547, +0.01708] sig | [+0.00753, +0.01530] sig |
  → **endpoint_fidelity_status = PASS**.
- **forecast score (extreme stratum)**: actual R2 **0.6254** > donor 0.5893 > mean 0.5430; RMSE 0.1492 < 0.1584 < 0.1971.
- **state / output response (stratum means)**: hot-dry `state_move 0.499 / output|Δvs.mean| 0.081 / contrib_state 0.062`
  vs matched-normal `0.493 / 0.055 / 0.046` (raw response larger under hot-dry — descriptive only).
- **hot-dry × matched-normal interaction** (dloss_donor): geo-cluster CI [−0.00216, +0.00320] sig=False,
  paired mean +0.00044 [−0.00172, +0.00263] sig=False → **hotdry_enhancement_status = FAIL**.
- invariants: `uf_differs_all_pairs = True` (donor really changes the full24 future weather); `weather_in_base = False` (T-only).
- **overall = `Q3_RESPONSE_FIDELITY_ONLY` → PARTIAL** (fidelity established; no extreme-specific enhancement).

## Three-gate summary (same frozen boundary80)
| Gate | Result | Verdict |
|---|---|---|
| Q1 (public usability) | R2 0.497 < 0.502, RMSE 0.157 > 0.156 | **SHORT** |
| Q2 (load-bearing core hard gate) | closure +0.0112, sig, ≥ floor; invariants pass | **LOAD_BEARING ✅** |
| Q3 (weather response) | endpoint fidelity PASS; hot-dry enhancement FAIL | **RESPONSE_FIDELITY / PARTIAL ✅** |

## Interpretation
- The model has a **genuinely load-bearing, internally-testable predictive state** (Q2) that responds to
  weather **faithfully and in the correct direction** (Q3 endpoint): feeding the *actual* future weather
  through `T` predicts the real NDVI **significantly better than a real-but-wrong donor weather and than
  climatology** — this is *fidelity*, not mere sensitivity.
- The response is **general, not extreme-specific** (no significant hot-dry enhancement).
- **Faithfulness–accuracy tradeoff**: routing all weather through a single testable transition on a
  weather-free prior yields a verifiable, load-bearing, correctly-responding state, at a small accuracy
  cost (Q1 short by ~0.005). The accuracy anchor remains the full-weather B4 (~0.512).

## OOD-t (temporal-OOD robustness) — frozen boundary80, `ood-t_chopped` (1904), bs=1, `--sections q1q2`
Manifest `evaluations/greenearthnet_oodt_20260719_214234/greenearthnet_oodt_chopped_manifest.json`
(role/protocol `ood-t_chopped` / greenearthnet chopped). Loaded `arch=TerraStateV2` on the exclusive T-only route.

| metric | OOD-t | val (ref) | gate | OOD-t result |
|---|---|---|---|---|
| Q1 R2 | **0.56935** | 0.49732 | ≥ 0.502 | **PASS** |
| Q1 RMSE | **0.15059** | 0.15729 | ≤ 0.156 | **PASS** |
| Q2 closure ΔR2 | **+0.01997** | +0.01121 | ≥ 0.005 | pass |
| Q2 closure CI | [+0.01422,+0.03018] sig | [+0.00643,+0.02590] sig | > 0 | pass |
| Q2 verdict | **LOAD_BEARING** | LOAD_BEARING | — | ✅ |

- On the temporal-OOD split boundary80 **clears both Q1 gates** (the val shortfall does not generalize) and is
  close to the full-weather B4 anchor (OOD-t ≈ **0.583 / 0.143**; R2 gap −0.014, same as the val gap).
- The load-bearing state is **robust and stronger on OOD-t** (closure +0.020 vs val +0.011).
- → Q2 LOAD_BEARING on **both** val and OOD-t; Q1 usable on OOD-t; combined with the Q3 response fidelity,
  the internally-testable weather-driven state is a robust, generalizing property of the model.

### OOD-t detailed metrics (from raw `state_contract_exclusive.json`; no NaN/Inf; ckpt sha `644deaac…` unchanged)
- **Q1 full**: NSE −0.09866 · |bias| 0.10083 · RMSE25 (rmse_0_5) 0.08205.
- **Q1 per land-cover** (R2 / RMSE): forest 0.5521 / 0.1473 · shrub 0.5562 / 0.1478 · grass 0.5845 / 0.1451 · crop 0.5847 / 0.1622.
- **Q2 arms** (R2 / RMSE): full 0.56935 / 0.15059 · alpha0 (frozen prior) 0.54938 / 0.16519 · T_identity 0.54766 / 0.25832.
- **Q2 CIs**: closure ΔR2 +0.01997, CI [+0.01422, +0.03018] sig; transition ΔR2 +0.02169, CI [+0.01609, +0.03217] sig; floor_pass=True, significant=True; invariants all pass; `clean=False` (T_identity OOD-confounded — closure remains the honest test). VERDICT LOAD_BEARING.
- Provenance: evaluator commit repo `78073db` + official scorer `a0329636…`; manifest role `ood-t_chopped`, n=1904, data_manifest_sha256 `58c8d648…`.


## val_chopped ↔ OOD-t side-by-side (same frozen boundary80)
| gate | val_chopped | OOD-t | note |
|---|---|---|---|
| Q1 R2 | 0.49732 (< 0.502) | **0.56935 (≥ 0.502)** | usable on OOD-t; short on val |
| Q1 RMSE | 0.15729 (> 0.156) | **0.15059 (≤ 0.156)** | usable on OOD-t; short on val |
| Q2 closure ΔR2 | +0.01121 | +0.01997 | both above the 0.005 floor |
| Q2 closure 95% CI | [+0.00643,+0.02590] sig | [+0.01422,+0.03018] sig | both exclude 0 |
| Q2 verdict | LOAD_BEARING | LOAD_BEARING | robust across splits |

## Same-caliber OOD-t vs Phase-I B4 (full-weather accuracy anchor)
| metric | TerraState boundary80 | Phase-I B4 (full-weather) | Δ (TerraState − B4) |
|---|---|---|---|
| OOD-t R2 | **0.56935** | 0.58252 | **−0.01317** |
| OOD-t RMSE | **0.15059** | 0.14342 | **+0.00717** |

TerraState is slightly behind B4 on OOD-t accuracy but **does not collapse**; the full-weather B4 remains the
accuracy anchor. The state's material contribution (Q2) carries from val into the temporal-OOD split.

## Final evidence table (frozen boundary80, all contracts)
| contract | split | key metric | verdict |
|---|---|---|---|
| Q1 usability | val_chopped | R2 0.49732 / RMSE 0.15729 | SHORT (internal gate 0.502 / 0.156) |
| Q1 usability | OOD-t | R2 0.56935 / RMSE 0.15059 | PASS |
| Q2 load-bearing | val_chopped | closure +0.01121, CI [+0.0064,+0.0259], sig | LOAD_BEARING |
| Q2 load-bearing | OOD-t | closure +0.01997, CI [+0.0142,+0.0302], sig | LOAD_BEARING |
| Q3 response fidelity | extreme (ood-t subset, 84 pairs) | endpoint PASS; enhancement FAIL | RESPONSE_FIDELITY_ONLY / PARTIAL |

## Paper-usable statement (中文 / English)
- **中文**：TerraState 在保持实质性时间-OOD 预测能力的同时，形成了在验证集和时间-OOD 条件下都显著服务最终预测的内部状态，并能更忠实地利用真实未来天气（真实天气显著优于季节/地理匹配的错误 donor 天气与气候均值天气）。
- **English**: TerraState forms an internal predictive state that significantly serves the final forecast on
  both the validation and the temporal-OOD splits, and that uses the actual future weather more faithfully
  (real weather significantly outperforms a season/geography-matched wrong-donor weather and a
  climatology-mean weather), while retaining substantial temporal-OOD predictive skill.

## Forbidden / unsupported claims (do NOT write)
- Q3's extreme-stratum forecast **R2 = 0.6254 is NOT the full OOD-t Table-1 score**. TerraState's full OOD-t
  score is **R2 = 0.56935, RMSE = 0.15059**.
- **0.502 is an INTERNAL frozen gate, not a domain-recognized threshold.**
- Q3 supports **weather-response fidelity only — NOT hot-dry-specific enhancement**.
- Do **NOT** claim SOTA, extreme-specific enhancement, or temporal composition.
- The **"accuracy–verifiability tradeoff" is an observed phenomenon, not a proven causal claim.**
- OOD-t Q2 (+0.020) is numerically higher than val Q2 (+0.011), but **without a cross-split significance test,
  do NOT claim that the temporal-OOD condition *causes* a stronger state contribution.**
