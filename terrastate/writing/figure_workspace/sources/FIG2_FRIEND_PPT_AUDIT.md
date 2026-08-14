# `示例/fig2——2.pptx` 第 1 页审核与 Figure 2 落地记录

更新时间：2026-07-28 UTC

## 1. 结论

第 1 页适合作为 TerraState Figure 2 的**视觉母版**，但不适合原样进入论文。
最终采用其“四段阶段条、连续左到右主链、少量真实视觉锚点”的组织原则，重新构建
了一个完全可编辑、结果无关、来源可审计的 Figure 2。

## 2. 原页可借鉴之处

- 四个连续阶段与 TerraState 的方法层级高度一致：
  `Historical context → predictive-state construction →
  weather-conditioned dynamics → forecast closure`。
- 历史输入、状态张量、天气序列、共享转移与输出被视觉化，而不是全部写成普通方框。
- context-forecast branch 与 state-construction branch 分开，适合表达
  $b_h+r_h$ 的闭合。
- 使用蓝、绿、紫、橙区分历史、状态、天气动力学和预测输出，颜色较克制。

## 3. 原页不能直接使用的原因

### 3.1 版面与可读性

- 原 PPTX 画布为 13.33 × 7.5 英寸，但第 1 页对象实际延伸至约 16 英寸；
  `(d) Readout & forecast` 区超出幻灯片右边界。
- 原页正文最小字号为 8 pt。若把约 16 英寸宽的内容缩到 AAAI 7 英寸通栏，
  等效字号约 3.5 pt。
- 大量纵向空白没有服务论文图，直接导出会浪费版面。

### 3.2 方法语义

- `Future meteorological forcing` 同时出现在输入区和动力学区，容易让读者误以为
  未来天气进入 history encoder 或 context-only forecast。
- 原页没有足够清楚地表达
  `q_\theta → P_\rho → z_t → T_\psi → z_{t+h} → O_\omega → r_h`
  以及 $\widehat y_{t+h}=b_h+r_h$。
- `D3 Vegetation forecast`、`PState projector` 等施工文字尚未论文术语化。
- Q2 的主干预“remove $r_h$”没有得到足够清楚的图形位置。

### 3.3 素材 provenance

原 PPTX 含多张无法由当前 TerraState 证据包确认来源的栅格素材，例如其他区域遥感图、
欧洲土地覆盖图、火星地形图、天气网页截图和外部曲线图。它们不能被包装成 TerraState
的真实输入、输出或实验结果，也不应在来源与许可未确认时直接复用。

## 4. 已落地的修订

新版 Figure 2：

- 使用 7.0 × 3.18 英寸原生画布，在论文通栏尺寸下不再二次大幅缩小；
- 只保留历史信息进入 $q_\theta$，未来天气只进入共享转移 $T_\psi$；
- 明确显示 $P_\rho$、$z_t$、$z_{t+h}$、$O_\omega$、$r_h$ 和
  context-only forecast $b_h$；
- 用加法节点闭合最终预测；
- 将 Q3 weather replacement、Q2 remove $r_h$ 与辅助 $T\rightarrow I$
  放在对应路径旁，而不是绘制成 benchmark 卡片；
- 所有遥感/状态/天气缩略图均为原创矢量示意，不表示真实定性结果；
- 不展示训练阶段、cache、checkpoint、Q4 或任何虚构实验数字。

## 5. 输出与可编辑性

- PPTX：`source/fig2_friend_adapted.pptx`
- SVG：`source/fig2_friend_adapted.svg`
- PDF：`export/fig2_friend_adapted.pdf`
- PNG：`export/fig2_friend_adapted.png`
- 灰度预览：`qa/fig2_friend_adapted_grayscale.png`
- 论文尺寸预览：`qa/fig2_friend_adapted_paperscale.png`
- 构建脚本：`source/build_fig2_friend_adaptation.py`
- 清单：`FIG2_FRIEND_ADAPTATION_MANIFEST.json`

PPTX 只有 1 页，共 137 个原生可编辑对象：85 个形状、44 条线和 8 个文本框；
没有嵌入图片。正式 PDF 为矢量输出，字体程序已嵌入。

## 6. 与其他图的分工

- Figure 1：当前仍承担推理路径与训练监督总览；后续若按已冻结蓝图改成问题—贡献图，
  Figure 2 将自然成为唯一的详细方法图。
- Figure 2：详细方法结构与 Q2/Q3 干预位置。
- Figure 3：只在真实行为结果图源完整后展示 Q2/Q3 的定量证据。

因此，Figure 2 本身不含结果、不承担排行榜，也不会把论文改写成 benchmark。
