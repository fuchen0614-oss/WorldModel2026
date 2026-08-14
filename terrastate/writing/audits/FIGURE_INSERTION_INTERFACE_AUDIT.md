# TerraState Figure 1--3 正文接入口审计

更新时间：2026-07-27 UTC

> **历史状态说明（2026-07-28）：** 本文档记录 Figure 2 接入前的接口审计。
> 作者随后批准以 `示例/fig2——2.pptx` 第 1 页为视觉母版重构 Figure 2；
> provenance 安全的原创矢量版已接入 `paper/main.tex`，标签为
> `fig:architecture`。当前状态以 `paper/WRITING_STATUS.md` 的 0G 节和
> `figure_workspace/STATUS.md` 为准。

## 1. 当前正式事实

- `paper/main.tex` 与 `paper/main.pdf` 当前只接入 Figure 1：
  `paper/figures/terrastate_method_overview.pdf`。
- `figure_workspace/STATUS.md` 已明确：Revision 2 的 Figure 1--3 导出稿被总控否决，
  只能作为历史草案，不能继续被描述为“等待批准的当前候选”。
- 新版 Figure 1/2 目前是施工蓝图。真实 EO 历史、未来 EO、TerraState 示例预测，
  以及 Figure 2 所需的 \(b_h/r_h/\widehat y\) 同案例分解尚未形成完整
  provenance。
- 聚合结果足以支持 Table 2/3 和未来的统计行为图，但不能替代真实遥感案例。

## 2. 接入口决策

### Figure 1

当前正式 Figure 1 保持不变。它已在 Introduction 后部、第二页顶部附近出现，
承担现有方法总览职责。在作者批准新版 Figure 1 且素材完整前，不替换当前引用。

### Figure 2

`main.tex` 在 `Evaluation Questions and Protocol` 的共同协议说明之后保留不可见
插入点。未来图的职责限于：

- 展示 TerraState 连续方法架构；
- 标出 Q2 状态贡献干预与 Q3 天气替换发生的位置；
- 不展示结果数值、排行榜、通过标志或 benchmark 卡片。

预定标签为 `fig:architecture`。只有图稿正式存在时才增加 `\ref`，因此当前编译
不会产生悬空引用。

### Figure 3

`main.tex` 在 Q3 结果之后、Limitations 之前保留不可见插入点。未来图必须满足：

- Q2 使用 per-minicube paired effect mean 与其 paired 95% CI；
- 不把 dataset-level official \(\Delta R^2\) 与 paired CI 混画；
- Q3 使用 endpoint-loss increase 与 geographic-cluster interval；
- 若使用定性面板，必须锁定同一真实 EO 案例、provenance 和统一色标。

预定标签为 `fig:behavior`。当前没有可见空框、TBD 或悬空引用。

## 3. 为什么现在不接入旧图

旧 Figure 2 含 provenance 不完整的 matched-backbone 比较。旧 Figure 3 混合了
不同 estimand。Revision 2 虽修正部分统计口径，但已经被新的三图信息层级和施工
蓝图取代。把任何一个旧导出稿接入会造成“图稿状态”与总控记录冲突。

## 4. 版面预留

当前正文第 6 页存在可用纵向空间，可容纳未来紧凑 Figure 3。Figure 2 的最终高度
尚不确定，因此只冻结语义位置，不提前通过负间距、缩小字体或移动表格强行留白。
待批准图稿到位后，再根据实际 bounding box 执行浮动体调度。

## 5. 验收条件

在任何图稿进入正式 PDF 前，必须同时满足：

1. 语义与 `main.tex` 的 \(q_\theta\rightarrow P_\rho\rightarrow z_t
   \rightarrow T_\psi\rightarrow z_{t+h}\rightarrow O_\omega\) 及
   \(b_h+r_h\) 完全一致；
2. 推理、训练专用监督与训练后干预视觉分离；
3. 所有真实影像、预测和数值具有来源记录；
4. 论文实际缩放下文字可读，灰度可辨；
5. 图与表互补，不重复构造排行榜；
6. 接入后重新编译并检查页数、浮动位置、引用、字体和匿名性。
