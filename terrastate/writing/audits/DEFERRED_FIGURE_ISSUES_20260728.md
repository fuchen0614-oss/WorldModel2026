# TerraState AAAI-27 延期 Figure 问题清单

**日期：** 2026-07-28  
**性质：** 只登记、不修改、不重绘  
**延期条目：** 10（Figure 1：1；Figure 2：9；Figure 3：0）

## Figure 1

### 当前状态

- 正式投稿图：
  `paper/figures/terrastate_concept_overview_author_20260728.png`
- SHA-256：
  `cad4c85d4787babb3eee6f10fb12e86537da2c71ab6534656fd144f1ea587fd0`
- `main.tex` caption 与当前主线一致：输出评分缺口、history-only state、shared
  transition、Q1–Q3 evidence。

### Deferred F1-1：Markdown 辅助说明仍指向旧训练监督图

- **位置：** 三份 Markdown 镜像中 Introduction 后的 Figure 1 标题、路径与说明；
  `MANUSCRIPT_ZH_FULL.md` 仍链接 `terrastate_method_overview.*`。
- **问题：** 辅助说明把 Figure 1 描述成“推理路径与训练监督”，并展开 frozen teacher
  与 \(h=20\) target；当前正式 Figure 1 是概念性 testable world-model overview。
- **科学影响：** 不影响 `main.tex/main.pdf`，但作者只看 Markdown 时可能误认当前正式
  图的职责。
- **最终图阶段最小方向：** 只同步 Markdown 的图名、路径和概念性说明；不改 Figure 1
  图像、caption、正文或方法事实。

## Figure 2

### 当前状态

- 正式投稿图：
  `paper/figures/terrastate_architecture_fig2_author_noborder_20260728.png`
- SHA-256：
  `9192e1d0f66253bad3391ac7208a5de91e663586157776fa8c8d30a46aa714f5`
- `main.tex` caption 已正确说明 history context、future weather through transition、
  explicit contribution、Q2/Q3 和非因果/非 composition 边界。
- 下列问题属于图片本体，不属于已经通过的 Section 3 正文或 Equations (1)–(8)。

### Deferred F2-1：future weather 被放入 multimodal history context

- **问题：** `Future meteorological forcing` 视觉上位于 panel (a)
  `Multimodal context`，总箭头指向 history encoder。
- **科学影响：** 容易误读为 \(q_\theta\) 可读取 future weather，违反正式信息边界。
- **最小方向：** 将 future weather 从 history-context 边界移出，只连接
  \(T_\psi\) 的 weather path。

### Deferred F2-2：transition 被画成 token multiplication

- **问题：** weather tokens 与 state tokens 通过乘号式节点结合。
- **科学影响：** 实现不是乘法、attention gate 或 element-wise modulation。
- **最小方向：** 删除乘号语义，使用 condition-fusion → residual transition 节点。

### Deferred F2-3：没有表达 condition fusion

- **问题：** 图中未明确表示
  \([E_u(u_{t+1:t+h});E_g(g)_i;E_h(h)]\to F(\cdot)\)。
- **科学影响：** 无法看出 weather prefix、patch-wise geography 和 horizon 如何共同
  条件化 transition。
- **最小方向：** 在 transition 前增加简洁 condition-fusion 模块及三条输入。

### Deferred F2-4：没有表达 residual update

- **问题：** 未显示 \(z_{t+h}=z_t+\Delta_\psi(\cdot)\) 的 skip/add。
- **科学影响：** 读者无法恢复真实 transition operator。
- **最小方向：** 为 \(z_t\) 添加 residual skip 和显式加法节点。

### Deferred F2-5：没有表达 same-\(z_t\) direct-per-horizon

- **问题：** 当前图容易被读成 recursive rollout 或跨 horizon token chaining。
- **科学影响：** TerraState 正式推理是每个 \(h\) 从同一 \(z_t\) 直接查询，不支持
  recurrent composition。
- **最小方向：** 标注 “direct query from the same \(z_t\) for each horizon” 或等价
  短标签；不要画 \(z_t\to z_{t+1}\to\cdots\)。

### Deferred F2-6：readout 输出未明确为 raster contribution \(r_h\)

- **问题：** readout 后仍显示 token grid。
- **科学影响：** 容易把 \(r_h\) 误认为 latent state，而不是可与 \(b_h\) 相加的
  horizon-specific raster。
- **最小方向：** 把 readout 输出画成栅格，并标注 \(r_h\)。

### Deferred F2-7：未明确 \(b_h+r_h=\widehat y_{t+h}\)

- **问题：** 虽有视觉加法节点，但 `context-only forecast`、raster \(r_h\) 和最终
  \(\widehat y\) 的标签关系不完整。
- **科学影响：** 削弱 Q2 为什么能在精确切点移除 state contribution 的可理解性。
- **最小方向：** 给加法节点两条清楚输入，并标注
  \(\widehat y_{t+h}=b_h+r_h\)。

### Deferred F2-8：Q2/Q3 干预切点不准确

- **问题：** Q2 未明确位于 `r_h → +` 前的 \(\alpha=0\) 切点；Q3 selector 与
  transition weather entrance 的对应关系不够明确。
- **科学影响：** 读者可能误以为 Q2 删除整个 state computation，或 Q3 替换 history、
  geography/ground truth，而不仅是 future weather。
- **最小方向：** Q2 标在 \(r_h\) 进入加法前；Q3 标在 \(T_\psi\) 的 weather input
  前，并写 actual / matched donor / normalized mean。

### Deferred F2-9：保留内部 `D3` 标签

- **问题：** 最终输出写成 `D3 Vegetation forecast`。
- **科学影响：** `D3` 是无法由论文定义恢复的内部工程标签，削弱投稿图的自包含性。
- **最小方向：** 删除 `D3`，仅保留 `land-surface forecast` 或
  \(\widehat y_{t+h}\)。

## Figure 3

### 当前状态

- 正式投稿图：
  `figure_workspace/export/fig3_behavior_singlecol.pdf`
- PDF SHA-256：
  `3b9c764152a867b2d1aef1b82b5661eb18bbd613236cb37dc45d58dfac7f0a53`
- PNG SHA-256：
  `9299c97fe61bf123dcdfa761e92cf056c4dbfaebefe5bcc662975049840919ed`
- 状态：`FIG3_SINGLECOL_LAYOUT_FROZEN`

### 待办

无。

Figure 3 当前正确区分：

- state removal primary 与 \(T\to I\) supporting；
- Validation 与 OOD-t；
- paired mean 与 paired-bootstrap CI；
- actual-weather x 轴与 donor/mean control y 轴；
- \(y>x\) 表示 control MSE 更高、actual weather 更优；
- 84 对完整样本和描述性 56/84、69/84；
- 无 SOTA、因果、Q4 或 extreme-specific enhancement。

## 不修改声明

本清单没有修改 Figure 1–3、caption、正文、PDF、PPTX、SVG、PNG、CSV、脚本或冻结
结果。所有条目仅供全文文本收敛后的最终 Figure 阶段处理；它们不进入
`FULL_TEXT_GLOBAL_CONSISTENCY_AUDIT_20260728.md` 的正文 Critical/Major 计数。
