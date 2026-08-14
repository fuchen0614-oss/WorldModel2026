# 当前有效事实与主张

## 方法身份

TerraState 是用于天气驱动地表预测的可检验预测状态世界模型。其公开推理链为：

\[
(b_{1:H},e_t)=q_\theta(\widetilde{\mathcal C}_t),\quad
z_t=P_\rho(e_t),\quad
z_{t+h}=T_\psi(z_t,u_{t+1:t+h},g,h),
\]

\[
r_h=O_\omega(z_{t+h}),\qquad
\widehat y_{t+h}=b_h+r_h.
\]

- 历史编码器只读取历史 EO、历史 mask、过去天气和静态地理。
- 未来天气只通过共享天气条件转移进入状态贡献路径。
- 每个 horizon 从同一个 \(z_t\) 做一次直接查询，不是递归 rollout。
- 最终预测显式相加 context-only forecast \(b_h\) 与 state-mediated contribution \(r_h\)。
- teacher 和 future-state target encoder 只用于训练，不进入推理。

## Q1：预测前提

- GreenEarthNet OOD-t：1,904 minicubes。
- \(R^2=0.56935\)，RMSE \(=0.15059\)，NSE \(=-0.099\)，\(|Bias|=0.101\)，RMSE25 \(=0.082\)。
- 最强安全表述：TerraState 在 temporal shift 下保留有效预测能力。
- 不支持 SOTA、严格排名或所有指标统一领先。

## Q2：状态贡献

主证据是移除 \(r_h\)，不是 \(T\to I\)。

- Validation：official \(\Delta R^2=0.01121\)；paired mean \(=0.01616\)，95% CI \([0.00643,0.02590]\)，\(n=589\)。
- OOD-t：official \(\Delta R^2=0.01997\)；paired mean \(=0.02200\)，95% CI \([0.01422,0.03018]\)，\(n=1,019\)。
- 最强安全表述：显式状态路径在两个 split 上承载可测量的预测增量。
- \(T\to I\) 仅支持 learned-transition involvement；它可能使 readout 接收训练分布外状态。

## Q3：天气响应

- 冻结的 84 个 matched pairs，31 个 geographic clusters。
- Actual vs matched donor：mean absolute forecast difference \(=0.03592\)；\(\Delta Loss=0.00257\)，95% CI \([0.00112,0.00399]\)。
- Actual vs normalized mean：mean absolute forecast difference \(=0.08137\)；\(\Delta Loss=0.01126\)，95% CI \([0.00547,0.01708]\)。
- \(\Delta Loss=Loss(control)-Loss(actual)\)，使用完整 20-step forecast-window masked MSE。
- 最强安全表述：未来天气替换改变预测输出，真实天气相对两条冻结对照具有更高预测窗口保真度。
- 不支持因果天气效应、反事实正确性或极端天气特异增强。

## 联合结论

在保持有用预测能力的前提下，Q2 与 Q3 支持 TerraState 暴露一个承载预测且响应所提供天气条件的可检验预测状态。该结论不等于完整物理状态，也不要求全部预测信息都经过状态路径。

