# TerraState Figure 1--3 冻结总纲（2026-07-28）

## 0. 优先级

本文件记录作者截至 2026-07-28 的最新图表决策。若既有正文、旧蓝图、
旧状态文件、旧提示词或旧图稿与本文件冲突，**以本文件为准**。冻结的是每张图的
叙事职责、证据边界和主版式；颜色、字体、间距、图标与局部措辞仍可继续优化。

全文只保留一个方法主线：

> TerraState 是一个可检验的预测状态世界模型。Q1 检验预测是否有用，Q2 检验
> 显式状态路径是否承担预测，Q3 检验共享转移是否利用真实未来天气产生更忠实的
> 端点预测。

不把 Q4/composition、因果天气响应、极端天气特异增强、SOTA 或未完成的复现实验
写入 Figure 1--3 的核心主张。

## 1. Figure 1：问题、观点与证据标准

Figure 1 借鉴 EO-WM Figure 1 的叙事节奏和整体布局，但不复制其具体内容、图形资产
或极端天气主张。Figure 1 回答“为什么固定时域精度不足，以及 TerraState 增加了
什么可检验能力”。

建议采用三块连续布局：

1. **Conventional EO forecasting**：历史 EO 与未来天气得到未来观测；输出精度
   可检验，但内部状态是否承载预测、是否正确利用天气仍未知。
2. **TerraState predictive-state world model**：最小概念链
   `history -> z_t -> T(z_t, weather, geography, h) -> z_{t+h} ->
   state contribution -> forecast`。详细模块留给 Figure 2。
3. **Testable evidence**：Q1 forecast skill、Q2 state contribution、
   Q3 weather-forcing response。

Figure 1 不放具体结果数值、置信区间、训练阶段、checkpoint、Q4、完整损失公式或
详细网络模块。不得声称其他 EO 方法都不是世界模型。

## 2. Figure 2：TerraState 的精确实现

Figure 2 采用作者当前认可的连续四段式架构图作为视觉与内容基准，主体为：

`q_theta -> P_rho -> z_t -> T_psi(z_t,w,g,h) -> z_{t+h} ->
O_omega -> r_h`，并以 `y_hat_{t+h}=b_h+r_h` 闭合预测。

四个大区依次为：

1. Historical context；
2. Predictive-state construction；
3. Weather-conditioned dynamics；
4. Forecast closure。

Q2 与 Q3 只作为小型训练后干预接口：

- Q2：在求和前移除 `r_h`；`T -> I` 只作支持性干预；
- Q3：只替换进入 `T` 的未来天气，比较 actual、matched donor 和 normalized mean。

Figure 2 不承担结果展示，不突出 Q1--Q3 数值，也不画 Q4。若当前接入的
`paper/figures/terrastate_architecture_fig2.pdf` 与作者稍后确认的
`示例/fig2——3.pptx` 页面不同，应等待作者选定页面后再替换；在此之前不得自行
改变 Figure 2 的叙事结构。

## 3. Figure 3：冻结结果的可视化证据

Figure 3 使用冻结实验记录自动绘制，采用三面板：

1. **(a) Q2 State contribution**：Validation 与 OOD-t 上移除状态贡献的配对
   效应与 95% 置信区间；可用较弱视觉样式附带 `T -> I` 支持性结果。
2. **(b) Actual vs. matched-donor weather**：84 个冻结配对的端点损失散点，
   横轴 actual-weather loss、纵轴 matched-donor loss，加入 `y=x`。
3. **(c) Actual vs. normalized-mean weather**：相同样本的 actual-weather loss
   与 normalized-mean loss 散点，加入 `y=x`。

在 (b)(c) 中，位于 `y=x` 上方表示替换真实天气后损失增大，即 actual weather
预测更忠实。Table 2--3 负责精确数值；Figure 3 负责显示效应方向、不确定性和
逐样本分布。因此不再将 Figure 3 制作成另一张结果表或 Q1 排行柱状图。

Figure 3 只能从冻结 JSON/CSV 读取数据，禁止手填点、重新估算置信区间、挑选有利
样本或加入没有 provenance 的定性案例。主图不加入 Q4，也不展示未通过的
extreme-specific interaction。

## 4. 正文位置与互补关系

- Figure 1：Introduction 前部，定义问题与贡献。
- Figure 2：Method 中，在方法计算链首次完整解释处。
- Figure 3：Results 中，在 Q2/Q3 结果解释之后或两节之间的合适浮动位置。

三张图分别回答：

1. **Why**：为什么需要可检验的 EO 世界模型；
2. **How**：TerraState 如何实现这种模型；
3. **Evidence**：冻结结果是否支持 load-bearing 与 weather-responsive 状态。

## 5. 当前执行顺序

1. 图表窗口立即绘制 Figure 3 三面板候选，不修改 Figure 1/2。
2. 证据窗口并行审核 Figure 3 的逐点来源、样本数、坐标方向和置信区间。
3. 正文窗口优先修订摘要，并准备 Figure 1--3 的 caption、引用位置和版面接口；
   Figure 3 在证据审核通过前不作为最终证据接入。
4. 作者审核 Figure 3 预览并最终确认 Figure 2 页面。
5. 正文窗口一次性接入作者批准的 Figure 2/3，编译并做纸面字号与页数检查。

