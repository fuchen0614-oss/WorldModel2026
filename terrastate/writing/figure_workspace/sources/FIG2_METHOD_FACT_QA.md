# Figure 2 方法事实 QA

核对依据：

- `METHOD_3_2_FINAL_AUDIT_20260728.md`
- `METHOD_3_4_FINAL_AUDIT_20260728.md`
- 当前冻结 `paper/main.tex` Section 3.1–3.4
- `FIGURE_2_VISUAL_ASSET_BLUEPRINT_ZH.md`

## 逐项结果

- PASS：`qθ` 的输入只包含历史 EO、recorded mask、past weather 和 static geography。
- PASS：future weather 完全移出 historical context；不存在 future-weather→`qθ` 箭头。
- PASS：`qθ` 同时产生空间 context tokens `e_t` 和 context-only forecast `b_h`。
- PASS：`Pρ(e_t)→z_t`，且 `z_t` 明确标为 history-only predictive state。
- PASS：`b_h` 有独立旁路进入最终加法节点，不被画成 observed future。
- PASS：Q3 三路未来天气位于 transition 上游，并进入同一个 weather-prefix encoder。
- PASS：首次完整使用 `season-, geography-, and quality-matched donor`。
- PASS：`d_h`、patch-wise `E_g(g)_i` 和 `E_h(h)` 经过 condition fusion 得到 `c_{h,i}`。
- PASS：没有旧版 weather/state 乘号。
- PASS：`z_t` 明确进入 `LN/Δψ`，同时保留 residual skip。
- PASS：显式写出 `z_{t+h}=z_t+Δψ([LN(z_t);c_{h,i}])`。
- PASS：标注 `one direct query per horizon`，未画递归 rollout。
- PASS：Q3 只切换 future-weather input，不放在 transition 下游。
- PASS：`Oω` 把 `z_{t+h}` 读出为空间 raster contribution `r_h`；`r_h` 不是 latent-token wall。
- PASS：`b_h` 和 `r_h` 进入显式加法节点，图中显示 `b_h+αr_h`。
- PASS：Q2 primary 切点位于 `r_h` 进入加法节点之前，标为 `remove r_h (α=0)`。
- PASS：`T→I` 在 transition 附近以灰色小标签表示，属于 supporting intervention。
- PASS：没有 teacher、future-state cache、KD、训练阶段或工程损失。
- PASS：没有 Q4、composition、causal、counterfactual、extreme-specific enhancement 或 SOTA 主张。
- PASS：observed-future reference 没有进入候选图。

## 输出名称判断

候选图采用 `NDVI forecast ŷ_{t+h}`。这是基于正文主要实验 target、`r_h` 的单通道输出及 Q1–Q3 的 NDVI 评测作出的统一选择。若作者更强调通用 land-surface modeling，可在接入前统一改名；这属于表述粒度选择，不是方法事实冲突。

