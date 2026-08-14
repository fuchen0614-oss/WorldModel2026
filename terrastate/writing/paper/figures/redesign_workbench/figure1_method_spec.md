# Figure 1 Specification — TerraState Method Overview

## 1. 单句信息

TerraState 从历史观测推断空间预测状态，用唯一共享且由未来天气/地理/时距条件化的 \(T_\psi\) 推进该状态，再把 state head 的贡献与 context-only prior 显式相加形成最终预测。

## 2. 读图顺序

读者应在十秒内沿一条左到右实线完成：

```text
cloud-masked EO history
  → history-only q_theta
  → P_rho
  → spatial z_t
  → shared T_psi
  → spatial z_{t+h}
  → O_omega
  → state contribution r_h
  → (+ b_h)
  → forecast y_hat_{t+h}
```

第二眼才读取下方 training-only 虚线支路。

## 3. 精确计算图

### 3.1 推理实线

1. \(\mathcal H_t\)、retained past meteorology、static geography \(g\) 进入 \(q_\theta\)。
2. 同一次 history-only forward：
   - 产生 horizon-indexed context-only prior \(b_h\)；
   - 暴露 context token，经 \(P_\rho\) 得到 \(z_t\)。
3. full24 future weather \(u_{t:t+h}\)、static \(g\) 和 horizon \(h\) 只进入共享 \(T_\psi\)。
4. \(T_\psi\) 产生 \(z_{t+h}\)。
5. \(O_\omega(z_{t+h})=r_h\)。
6. 显式加法节点计算 \(\widehat y_{t+h}=b_h+r_h\)。

必须让 \(b_h\) 在 future weather 进入之前分出。图中不得出现 future weather 到 \(q_\theta\)、\(b_h\) 或加法节点的直连。

### 3.2 Training-only 虚线

唯一非零训练目标：

\[
\mathcal L
=
\mathcal L_{\rm GT}
+0.5\mathcal L_{\rm KD}
+\lambda_s\mathcal L_{\rm future\text{-}state}.
\]

三条监督关系分别为：

1. observed future target \(y_{t+h}\) 与 \(\widehat y_{t+h}\) 形成 \(\mathcal L_{\rm GT}\)；
2. frozen full-weather forecasting teacher 的预测与 \(\widehat y_{t+h}\) 形成 \(0.5\mathcal L_{\rm KD}\)；
3. observed future EO 经 frozen \(q+P\) 得到 \(z^\star_{t+20}\)，只与 student 的 \(z_{t+20}\) 形成 \(\lambda_s\mathcal L_{\rm future\text{-}state}\)。

teacher、observed future EO、frozen target encoder 与 target state 均不得连接到实线推理路径。

## 4. 空间布局

- 画布：约 `1000 pt × 360 pt`，双栏通栏。
- 主推理区域：约占图高 65%–70%。
- training-only 区域：约占图高 25%–30%，使用独立浅底/虚线边界。
- 不设置图内总标题。
- 左侧输入约 14%；\(q_\theta/P_\rho/z_t\) 约 30%；共享 \(T_\psi\) 及条件约 24%；closure/output 约 24%；其余为留白与箭头。
- \(T_\psi\) 和两个空间状态 glyph 是视觉中心；context prior 是清晰但次级的旁路。

## 5. 视觉语法

| 语义 | 最终颜色建议 | 非颜色编码 |
|---|---|---|
| 历史/context | 冷蓝灰 | 实边框 |
| predictive state | 低饱和绿 | 网格/token glyph |
| shared transition | 低饱和紫 | 较粗边框、居中 |
| closure/output | 低饱和橙 | 显式 \(+\) 节点 |
| training-only | 橙褐 | 长虚线、独立底带 |

第一阶段全部为黑白线框：实线表示推理，长虚线表示 training-only。颜色不得成为唯一编码。

## 6. 图像与状态 glyph

- 历史输入保留 3 个可替换 EO 缩略槽，并叠加云掩膜线纹。
- \(z_t\) 与 \(z_{t+h}\) 使用同形的 \(4\times4\) 小网格，强调“空间状态”而非普通向量。
- 预测输出保留一个小型空间网格槽。
- observed future EO 的训练支路使用更小的缩略槽，且被 training-only 边界包围。
- 未有冻结真实数组时，所有槽都保持抽象矢量 glyph。

## 7. 图内英文标签

优先使用：

- `cloud-masked EO`
- `past met.`
- `static \(g\)`
- `history-only \(q_\theta\)`
- `projector \(P_\rho\)`
- `spatial state \(z_t\)`
- `full24 weather`
- `horizon \(h\)`
- `shared \(T_\psi\)`
- `future state \(z_{t+h}\)`
- `state head \(O_\omega\)`
- `context prior \(b_h\)`
- `state contribution \(r_h\)`
- `forecast \(\widehat y_{t+h}\)`
- `TRAINING ONLY`
- `frozen teacher`
- `observed future EO`
- `frozen \(q+P\)`
- `\(h=20\) only`

不使用长句，不出现研发名或大标题。

## 8. 尺寸验收

- 以 `0.98\textwidth` 放入 AAAI 双栏页面时，最小成品文字目标为 9 pt，任何标签不得低于约 8.5 pt。
- 最细成品线宽目标不低于 0.5 pt。
- 主链箭头与 training-only 虚线在灰度打印中必须清楚区分。
- 预测加法、future-weather 入口与 \(h=20\) 限定必须在 paper-scale preview 中可直接辨认。

## 9. 英文 caption 草案

**TerraState inference and training supervision.** Cloud-masked EO history, retained past meteorology, and static geography enter the history-only context operator \(q_\theta\), which emits a context-only prior \(b_h\) and, through \(P_\rho\), a spatial predictive state \(z_t\). Full24 future weather, static geography, and horizon \(h\) condition the shared transition \(T_\psi\); the state head \(O_\omega\) decodes \(z_{t+h}\) into a contribution \(r_h\) that is added explicitly to \(b_h\). Solid arrows denote inference. Dashed branches are training only: ground-truth forecasting, distillation from a frozen full-weather teacher, and an \(h=20\) future-state anchor produced from observed future EO by a frozen target encoder. Neither teacher nor future observation is used at inference.

## 10. 中文解释草案

**TerraState 的推理闭环与训练监督。** 云掩膜 EO 历史、保留的过去气象和静态地理进入 history-only 上下文算子 \(q_\theta\)；它一路产生 context-only 先验 \(b_h\)，另一路经 \(P_\rho\) 得到空间预测状态 \(z_t\)。Full24 未来天气、静态地理与预测时距 \(h\) 条件化同一个共享转移 \(T_\psi\)，状态头 \(O_\omega\) 将 \(z_{t+h}\) 解码为状态贡献 \(r_h\)，再与 \(b_h\) 显式相加。实线表示推理；虚线只表示训练监督，包括真实目标、冻结 full-weather teacher 的蒸馏，以及由真实未来 EO 的冻结目标编码器提供的 \(h=20\) 状态锚定。teacher 与未来观测均不参与推理。
