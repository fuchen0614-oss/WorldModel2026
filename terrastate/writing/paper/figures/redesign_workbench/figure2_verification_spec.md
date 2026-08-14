# Figure 2 Specification — Operational State Verification

## 1. 单句信息

同一个最终冻结 checkpoint 接受三项核心检验：预测是否可用（Q1）、状态支路是否承载预测（Q2）、未来天气是否通过共享转移产生正确的状态与端点响应（Q3）；composition（Q4）仅为视觉降级的可选扩展。

## 2. 总体布局

- 推荐为双栏通栏、浅而宽的 evidence map，目标画布约 `1000 pt × 225 pt`。
- 最左是唯一 `same frozen checkpoint` 节点。
- 右侧依次为：
  - A / Q1 Forecast skill；
  - B / Q2 Load-bearing；
  - C / Q3 Driver response；
  - D / Q4 Optional。
- Q1–Q3 使用实边框；Q4 使用灰色虚线边框、较窄宽度和较弱文字层级。
- 不画排行榜、柱状图或已经通过的勾号。

## 3. A / Q1 Forecast skill

表达：

- frozen TerraState checkpoint 在固定本地协议上产生预测；
- 与 local matched backbone 作严格配对；
- published numbers 仍由 Table 1 单独标记为 Reported，不进入此图的比较箭头；
- 图中只显示 `forecast metrics / paired local comparison`，不显示 TBD 数字。

该面板证明“结果可用”，不单独证明世界状态。

## 4. B / Q2 Load-bearing

从同一 checkpoint 和同一批样本分出三臂：

1. `full`；
2. `closure cut: r_h=0`，精确恢复 \(b_h\)，是主证据；
3. `support: T→I`，是共享转移依赖的辅证。

三臂最终都到 endpoint forecast / paired score。图中不得把 \(T\rightarrow I\) 画成与 closure cut 同等无条件可靠的证据；可通过 `primary` / `support` 小标签或线型区分。

## 5. C / Q3 Driver response

固定 history、static geography、prior、checkpoint、sample population 与 mask，只替换 \(T_\psi\) 的 future-weather 输入：

1. `actual weather`；
2. `normalized mean`；
3. `matched donor`。

对每个 arm 同时观察：

- transitioned-state change；
- endpoint-output change；
- forecast-score change。

### Hot-dry 的准确位置

hot-dry 不是第四种天气 arm，也不是模型输入。它作为 Q3 下方的预注册压力分层：

```text
effect under hot-dry
       vs
effect under matched-normal
```

只有直接检验两组效应差及其区间，才允许解释为 amplification。线框图只表达“进行该比较”，不得用上升箭头、勾号或文字暗示已经增强。

## 6. D / Optional Q4

只显示：

- `direct`
- `composed`
- `endpoint guard`
- `non-collapse guard`

使用灰色、虚线和 `optional` 标签。不得显示 composition loss、训练 partition 或“已验证 compositional dynamics”。若最终不进入正文，该面板可整体移到附录或删除，不影响 Q1–Q3。

## 7. 视觉语法

- checkpoint 到各面板：点线或细实线，表示训练后查询，而非模型推理。
- 面板内部的干预分叉使用一致箭头方向。
- Q2 的 closure cut 采用实边框；\(T\rightarrow I\) 采用较浅或虚线辅助边框。
- Q3 的三个 weather arm 平行排列；hot-dry/matched-normal 使用横向括号或独立底条。
- Q4 使用最低对比度和最小面积。
- 所有面板使用问句/测试名，不用性能结论。

## 8. 图内英文标签

- `same frozen checkpoint`
- `Q1 forecast skill`
- `paired local reference`
- `Q2 load-bearing`
- `full`
- `closure cut \(r_h=0\)`
- `support: \(T\to I\)`
- `Q3 driver response`
- `actual`
- `mean`
- `matched donor`
- `state · output · score`
- `pre-registered stratum`
- `hot-dry vs matched-normal`
- `Q4 optional`
- `direct · composed`
- `endpoint + non-collapse guards`

## 9. 英文 caption 草案

**Same-checkpoint operational verification.** The selected TerraState checkpoint is evaluated without retraining. Q1 reports forecast skill under the fixed local protocol and its paired matched-backbone reference. Q2 compares the full model with the exact closure cut \(r_h=0\) and the supporting \(T\!\rightarrow I\) intervention. Q3 changes only the future-weather input to \(T_\psi\), comparing actual, normalized-mean, and matched-donor forcing while tracking state, output, and score changes; the pre-registered hot-dry analysis compares intervention effects with matched-normal conditions rather than supplying an additional model input. Q4 is an optional post-training direct/composed query guarded by endpoint accuracy and non-collapse checks.

## 10. 中文解释草案

**同一检查点的可操作验证。** 选定的 TerraState 检查点不经重训练接受所有检验。Q1 在固定本地协议上报告预测能力，并只与匹配骨干作严格配对。Q2 比较完整模型、精确闭环切除 \(r_h=0\) 和作为辅证的 \(T\!\rightarrow I\)。Q3 只替换 \(T_\psi\) 的未来天气，比较 actual、归一化均值与匹配供体，同时追踪状态、输出和得分；预注册 hot-dry 分析比较其干预效应与 matched-normal 的差异，而不是给模型增加输入。Q4 仅是训练后的可选 direct/composed 查询，并受端点精度和防坍塌条件约束。
