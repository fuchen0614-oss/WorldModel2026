# Figure 2 图内英文文案清单

以下文本与当前候选 SVG/PPTX 一致。正式画布仅使用英文。

## Panel headers

- `A  Historical Context`
- `B  Predictive-State Construction`
- `C  Shared Weather-Conditioned Transition`
- `D  State Readout and Forecast Closure`

## A — Historical Context

- `Historical EO`
- `Recorded mask`
- `Static geography`
- `Past weather`
- `History-encoder inputs`
- `EO + recorded mask + past weather + geography`

## B — Predictive-State Construction

- `History encoder qθ`
- `history only`
- `eₜ tokens`
- `Pρ`
- `zₜ`
- `history-only predictive state`
- `bₕ`
- `Context-only forecast bₕ`
- `independent bypass`
- `context-only bypass bₕ`

## C — Shared Weather-Conditioned Transition

- `Q3 future-weather input`
- `actual`
- `season-, geography-, and quality-matched donor`
- `normalized mean`
- `Shared weather-prefix encoder Eᵤ`
- `dₕ`
- `Patch-wise geography E_g(g)ᵢ`
- `Horizon Eₕ(h)`
- `Condition fusion F → cₕ,ᵢ`
- `LN(zₜ)`
- `Shared transition Tψ`
- `Δψ([LN(zₜ); cₕ,ᵢ])`
- `zₜ₊ₕ = zₜ + Δψ([LN(zₜ); cₕ,ᵢ])`
- `one direct query per horizon`
- `Q2: T→I`

## D — State Readout and Forecast Closure

- `zₜ₊ₕ`
- `State readout Oω`
- `rₕ`
- `spatial raster contribution`
- `Q2 primary`
- `remove rₕ (α=0)`
- `bₕ + αrₕ`
- `ŷₜ₊ₕ`
- `NDVI forecast`

## 禁止恢复的旧文案

- `D3 Vegetation forecast`
- `TRAINING ONLYL`
- `future weather` 作为 `qθ` 输入
- weather/state 乘号
- Stage A/B、full24、smoke 或其他工程内部名称
- causal、counterfactual、composition、Q4

