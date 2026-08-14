# TerraState Experiments / Results：AAAI 写作范式与证据审计

> 日期：2026-07-27  
> 范围：Experimental Setup、Q1–Q3 Results、Limitations、Conclusion  
> 原则：只重排已冻结证据，不改变数值、统计量、结果 verdict 或研究主线。

## 1. 本节开始前的一手调研

本轮检查了 AAAI 2024–2026 方法论文的实验节，并把新增 PDF 保存在
`literature/experiment_writing_anchors/`。只提炼实验叙事和结果解释方法，不把
这些论文作为 TerraState 科学主张的引用。

| 锚点 | 一手来源 | 实验节写法 | 对 TerraState 的启示 |
|---|---|---|---|
| ReconVLA (AAAI 2026) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/38921) | Experiments 开头列出待回答问题；每一实验先给 setting，再按结果—机制解释组织 | 保留 Q1–Q3 问题列表，但问题后应立即给统一协议，不重复引言动机 |
| CADYT (AAAI 2026) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/40999) | Setup 统一说明数据、基线、指标、重复次数；Results 按每个研究问题依次回答，并区分 sanity check 与主结论 | Q1/Q2/Q3 的统计单位和区间方法应在 setup 一次定义；正文结果只解释对应问题 |
| LLM2CLIP (AAAI 2026) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/37427) | 主结果之外明确报告性能下降与 trade-off，并把未经验证的原因标为 hypothesis | Hot-dry null、一次训练和跨协议限制要保留；不能用 Q2/Q3 掩盖 Q1 |
| SparseWorld (AAAI 2026) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/37347) | Dataset/Metrics、Implementation、Main Results 分层；每段围绕一张表回答一个任务 | 实现细节应集中，Q1–Q3 各段只承担一个结论；Table 1–3 紧邻首次解释 |
| WorldAgen (AAAI 2026) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/38925) | 先给 dataset 与 implementation，随后按 benchmark 报告结果；核心机制另设 ablation | TerraState 不应把 Q2/Q3称为普通重训练 ablation；它们是同一模型的匹配干预 |
| Drive-OccWorld (AAAI 2025) | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/33010) | 世界模型结果与下游任务分开，图表分别承担量化与行为解释 | Table 负责精确数字，未来 Figure 3 应展示效应与行为，不重复表格排行榜 |
| Contextformer / GreenEarthNet | [CVF Open Access](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-Modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html) | 数据、掩膜、指标和 OOD 划分在 Methods/Experiments 明确，Table 2 给公开对照 | Published 与 Local 面板必须隔离；公开均值只作历史背景，不作严格排名 |

## 2. 归纳出的写作规则

1. **Experiments 开头先给问题，再给共同协议。** 问题列表可保留，但不重复
   Introduction 的“为什么重要”。
2. **只定义后文实际使用的主指标。** Q1 用 \(R^2\)/RMSE；Q2 必须同时定义
   dataset-level official \(\Delta R^2\) 与 per-minicube paired effect；Q3 用
   endpoint-loss increase 与 geographic-cluster CI。
3. **表格负责精确数值，正文负责回答问题。** 结果段采用
   “结论 → 最少必要数字 → 解释 → 边界”，不逐格朗读表格。
4. **不同 estimand 永不共用一套区间。** Official delta 和 paired effect 必须
   继续分列、分句。
5. **主证据与辅证据分层。** State removal 是 Q2 主证据；\(T\to I\) 只支持
   transition involvement。
6. **负结果是论文成熟度的一部分。** Hot-dry interaction 跨零时明确写
   “no evidence”，不藏入附录，也不把原因写成已证实机制。
7. **协议边界写一次即可。** Manifest、fallback、checkpoint、SHA 等应留在
   provenance / reproducibility 文件；主文只保留 validation-only selection、
   same selected model、one run 与 non-equivalent public/local protocols。
8. **Conclusion 只回答研究问题。** 不引入新数字、方法或组合主张。

## 3. 当前稿的主要问题

| 严重度 | 当前问题 | 风险 | 修订动作 |
|---|---|---|---|
| MAJOR | Targets and metrics 罗列 NSE、bias、outperformance、RMSE25、ENS，但核心表格与结果不使用 | 实验节像结果接入口或内部评测清单，读者不清楚主判据 | 直接定义 Q1、Q2、Q3 实际采用的 estimand 与区间单位 |
| MAJOR | Data and selection 解释 internal qualifier、fallback 和本地 bundle | 工程 provenance 抢占科学叙事 | 主文收敛为 validation-only selection、OOD-t 未参与、1,904 样本；细节留控制文件 |
| MAJOR | Q1 表注的 “nominal ... test family” 和 “frozen local evaluation” 偏内部语言 | 削弱投稿成熟度 | 改为 published context / local TerraState evaluation，并保留非严格比较限定 |
| MINOR | Q3 结果句 “does not merely change its state” 容易被读成已经验证完整内部机制 | 实际证据是 endpoint fidelity，不是因果或状态正确性 | 改为“结果满足预先要求的 endpoint criterion；latent movement alone 不足” |
| MINOR | Conclusion 首句 “turns ... into a property” 抽象 | 世界模型身份不够直接 | 改为“makes the predictive state of an EO world model directly testable within the forecast path” |
| MINOR | Figure 2/3 的注释插入口与 Results 关系尚未收敛 | 后续接图可能造成重复或浮动拥堵 | 保留不可见注释接口；Figure 3 只在真实效应图批准后进入 |

## 4. TerraState 的结果叙事模板

### Q1

- **结论：** retains useful predictive skill under OOD-t；
- **数字：** \(R^2=0.56935\)，RMSE \(=0.15059\)，1,904 minicubes；
- **边界：** 不宣称 SOTA，不跨 Published/Local 面板排名。

### Q2

- **结论：** state-mediated contribution is load-bearing on validation and
  OOD-t；
- **主证据：** state removal；
- **统计：** official \(\Delta R^2\) 与 paired mean/CI 分开；
- **辅证据：** \(T\to I\) 同方向，但受 readout 输入分布变化影响；
- **禁止：** 不宣称 OOD-t 效应显著更强，不用 future-state loss 代替 Q2。

### Q3

- **结论：** actual future weather yields better endpoint fidelity than
  matched-donor and normalized-mean controls；
- **统计：** 84 对、loss increase、geo-cluster CI；
- **边界：** 不宣称因果、反事实正确性或 hot-dry 特异增强；
- **负结果：** hot-dry interaction CI 跨零，明确记录为未支持。

## 5. Claim–evidence 检查

| 主张 | 证据 | 允许强度 |
|---|---|---|
| useful OOD-t forecast skill | Q1 local \(R^2\)/RMSE | SUPPORTED / qualified |
| load-bearing state path | state removal paired effects, intervals exclude zero | SUPPORTED |
| transition involvement | \(T\to I\) same-direction degradation | PARTIAL / supporting only |
| weather-response fidelity | actual beats both controls on endpoint loss | SUPPORTED / conditional |
| hot-dry enhancement | interaction CI crosses zero | UNSUPPORTED; state null explicitly |
| causal or counterfactual correctness | no counterfactual ground truth | UNSUPPORTED |
| strict ranking / SOTA | protocols not equivalent | UNSUPPORTED |
| composition consistency | no core Q4 result | UNSUPPORTED |

## 6. 退出条件

- Setup 只包含实际使用的指标、统计单位和选择规则；
- Q1–Q3 各自回答一个问题，统计量不混写；
- Table 1–3 的数字与证据工作区逐项一致；
- negative result 与限制可见但不喧宾夺主；
- 英中稿数字、术语与主张强度一致；
- PDF 无表格溢出、overfull、undefined citation/reference；
- Figure 2/3 没有可见 TBD 或空框。
