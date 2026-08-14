# TerraState AAAI-27 全稿收敛审计

更新时间：2026-07-27 UTC

## 1. 总体结论

当前稿件已经形成一致的方法型论文闭环：

> 部分观测的天气驱动 EO 预测 → 显式预测状态 → 共享天气条件转移 →
> 状态读出进入预测闭环 → 同一模型上的 Q1 预测能力、Q2 状态贡献和 Q3 天气响应。

除摘要作者门与新版 Figure 1/2 的真实素材外，当前可由写作端独立完成的主文内容
已经基本收敛。稿件不会给人“新 benchmark”或纯诊断工具的主印象；主要卖点是一个
把预测状态放入预测闭环、从而能够接受匹配干预的方法。

## 2. 严重度审计

### CRITICAL：仍需作者决定

**摘要信息重心。** 当前摘要共约 198 词，前五句承担背景、缺口、方法、训练锚定和
评测设计，但最后连续四句分别展开 Q1、Q2、Q3 与总括结论。实际第一页中，摘要的
数字密度明显压过方法身份，也比 2026-07-22 上传摘要改动更大。

建议摘要已经保存在 `ABSTRACT_AUDIT_AND_REVISION_PROPOSAL.md`：

- 恢复提交版的背景—缺口—世界模型—机制顺序；
- 删除 composition、matched-backbone 等已失效承诺；
- 只用最后一句概括 Q1--Q3；
- 不用多组小数主导摘要。

根据既定作者门，本轮没有覆盖 `main.tex` 的摘要。

### MAJOR：本轮已修复

1. 英文和中文阅读稿仍把被否决的 Revision 2 图写成“待批准候选”。现已与
   `figure_workspace/STATUS.md` 对齐，并为 Figure 2/3 建立不可见插入口。
2. `operational`、`manifest/evaluator equivalence`、缓存读取等工程审计措辞过多。
   已改为 testable model property、data-subset/scoring equivalence、fixed targets
   throughout training 等方法论文表达。
3. `\clearpage` 人为把参考文献推迟并造成第 6 页大面积留白，违反 AAAI Author
   Kit 不使用页面断点命令控制版面的要求。现已删除，参考文献自然接续正文。

### MINOR：保留观察

- 第 5 页集中放置 Table 1--3，视觉密度较高，但字号、列宽和 caption 仍可读。
  Figure 3 到位后需要重新调度浮动体，当前不应为尚不存在的图提前压缩表格。
- 编译日志有 6 条 `Underfull \hbox`，均未造成可见溢出、裁切或格式违规。

## 3. 逐节职责与成熟度

| 部分 | 当前职责 | 结论 |
|---|---|---|
| Abstract | 背景、缺口、world-model 身份、核心机制、一个证据总结句 | AUTHOR GATE |
| Introduction | 应用问题、世界模型定义、结构缺口、TerraState 解法、定性证据与贡献 | PASS |
| Related Work | EO 预测、EO 世界模型、预测状态/潜动力学三条边界 | PASS |
| Problem Formulation | 输入隔离、\(q\)-\(P\)-\(T\)-\(O\) 闭环及预测状态定义 | PASS |
| Method | 状态推断、共享转移、显式状态贡献、三项训练信号、Q2/Q3 干预语义 | PASS |
| Experiments | validation-only selection、Q1--Q3 指标与统计单位、同一模型 | PASS |
| Results | Q1 useful skill、Q2 两类 estimand 分开、Q3 endpoint fidelity | PASS |
| Limitations | 一次训练、协议非等价、非因果、hot-dry null、Q4 非核心 | PASS |
| Conclusion | 回答 Q1--Q3，不引入新数字或更强主张 | PASS |

## 4. Claim--evidence 核心映射

| 主张 | 证据 | 允许措辞 |
|---|---|---|
| TerraState 保留预测能力 | OOD-t \(R^2=0.56935\)，RMSE \(=0.15059\) | useful predictive skill |
| 状态路径承载预测 | Val/OOD-t state removal official \(\Delta R^2\)；另报 paired mean/CI | load-bearing on both splits |
| 转移参与预测 | \(T\rightarrow I\) 同方向，但 readout 输入分布改变 | supporting evidence only |
| 预测依赖所给未来天气 | 84 对样本中 actual weather 的 endpoint loss 低于 donor/mean controls | weather-response fidelity |
| 极端热旱特异增强 | 交互区间跨零 | 不支持；只报告 null |
| composition/non-degeneracy | 无核心最终证据 | optional/exploratory only |

## 5. 图稿接口

- Figure 1：正式 PDF 当前唯一可见图，位于第 2 页。
- Figure 2：`main.tex` 在共同评测协议之后保留不可见插入口；旧 Revision 2
  不得接入，新蓝图需要 provenance 完整的 EO/预测素材。
- Figure 3：在 Q3 之后保留不可见插入口。Q2 必须画 paired mean + paired CI，
  Q3 必须画 endpoint-loss increase + geo-cluster interval；不得混用 estimand。
- 当前 PDF 没有空白框、TBD 或未定义图引用。

详见 `FIGURE_INSERTION_INTERFACE_AUDIT.md`。

## 6. 新近文献复核

本轮重新扫描 EO-WM、VegSim、cloud-aware observability、OCELOT、Earth-o1 和
AAAI-26 相关 latent/world-model 工作。没有发现需要改变当前主线的新论文，也没有
为了数量新增引用。具体判断见 `NEW_LITERATURE_SCAN_20260727.md`。

## 7. 编译、格式与版面

- 权威源：`paper/main.tex`
- PDF：`paper/main.pdf`
- 页数：7 页，US Letter（612×792 pt）
- Figure 1：第 2 页
- Table 1--3：第 5 页
- Limitations：第 5--6 页
- Conclusion：第 6 页
- References：第 6 页开始，第 7 页结束
- 匿名性：`Anonymous Submission`，空 affiliations，无 acknowledgments
- 字体：全部字体对象嵌入；Type 3 为 0
- BibTeX：24 个条目，24 个正文使用；缺失键、unused、重复键均为 0
- LaTeX：无 error、overfull、undefined citation/reference
- 警告：6 条非阻塞 `Underfull \hbox`
- 页面渲染：`paper/build_review_full_convergence_20260727/`

## 8. 尚未由写作端解决的事项

1. 作者决定是否采用 `ABSTRACT_AUDIT_AND_REVISION_PROPOSAL.md` 的单结果句摘要。
2. 新 Figure 1/2 所需真实、可追溯 EO/预测素材与最终作者批准。
3. 若制作 Figure 3，补齐对应统计图数据或固定定性案例；不得用聚合 CSV 伪造影像。
4. 按投稿系统要求单独填写并上传 reproducibility checklist。
5. 投稿前复核 EO-WM、VegSim、observability 等同期预印本的最新元数据。

## 9. 定时复审状态

当前 Goal 尚未结束：摘要和图稿仍有作者/素材门，因此尚未创建与进行中工作重叠的
定时任务。待上述门槛解除或作者明确冻结当前版本后，再建立“新论文扫描 → novelty
影响判断 → 引用元数据检查 → PDF 全稿复审”的周期任务。

