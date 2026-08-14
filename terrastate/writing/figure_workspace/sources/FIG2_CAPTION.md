# Figure 2 caption 建议

## English

**TerraState architecture and intervention interfaces.** Historical EO with its recorded mask, past weather, and static geography is encoded by \(q_\theta\) into a context-only forecast \(b_h\) and spatial tokens \(e_t\), which \(P_\rho\) projects to the history-only predictive state \(z_t\). For each horizon, actual, season-, geography-, and quality-matched donor, or normalized-mean future weather is encoded and fused with patch-wise geography and horizon before the shared residual transition \(T_\psi\). The readout \(O_\omega\) maps \(z_{t+h}\) to a raster contribution \(r_h\), closing the forecast as \(\hat y_{t+h}=b_h+\alpha r_h\). Q2 removes \(r_h\) (\(\alpha=0\), primary) or sets \(T\!\rightarrow\!I\) (supporting); Q3 changes only the future-weather input.

## 中文对照

**TerraState 架构与干预接口。** 带记录掩膜的历史 EO、过去天气和静态地理由 \(q_\theta\) 编码为 context-only forecast \(b_h\) 与空间 token \(e_t\)，后者经 \(P_\rho\) 投影成仅由历史构造的预测状态 \(z_t\)。对每个预测跨度，真实、按季节—地理—质量匹配的 donor 或 normalized-mean 未来天气经过同一个编码器，并与逐 patch 地理及 horizon 融合后驱动共享残差转移 \(T_\psi\)。读出 \(O_\omega\) 将 \(z_{t+h}\) 映射为空间栅格贡献 \(r_h\)，最终以 \(\hat y_{t+h}=b_h+\alpha r_h\) 闭合。Q2 的主要干预移除 \(r_h\)（\(\alpha=0\)），\(T\!\rightarrow\!I\) 仅为支持性干预；Q3 只替换未来天气输入。

## 接入前提醒

当前图内终点写作 `NDVI forecast`。如果正文最终采用更泛化的 `land-surface forecast`，caption 中的 forecast 含义与图内标签必须同步修改；不要只改其中一处。

