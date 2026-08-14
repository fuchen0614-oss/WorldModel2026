# TerraState AAAI-27 最终证据审计

审计日期：2026-07-28 UTC  
审计状态：**DONE（证据核验完成；正文仍有明确整合事项）**  
工作模式：只读核验。未运行模型、未训练、未复现公开方法、未创造指标；未修改
正文、图稿、CSV、BibTeX、原始 JSON 或实验结果。

## 1. 范围与冻结输入

本轮只读取 `TerraState_AAAI27/`，只更新本报告、`CITATION_AUDIT.md` 和
`STATUS.md`。关键输入的 SHA-256 为：

| 输入 | SHA-256 |
|---|---|
| `paper/main.tex` | `66d43adf18f42ed64880130176d64d8cf40ff226c295f7995dd88ce92825f131` |
| `paper/references.bib` | `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659` |
| `MANUSCRIPT.md` | `92cac5e9fc06ce2bdf4734b467f0202d12f900c970240ad0db96a1c5c3acf1fa` |
| `MANUSCRIPT_ZH.md` | `a9024847e71357c73978f8d5ca99bcb01e0911eee89b1c6d596117ddbff4f82d` |
| `MANUSCRIPT_ZH_FULL.md` | `e0b5d72d1cd68e4dc24999feece3197c61f54f083ca5e40b68fc35a861674e6d` |
| `paper/ReproducibilityChecklist.tex` | `06a3459158089bf1c64b738986118f1d1566e816da4b710c6397561e33c3d5e6` |
| `evidence_workspace/tables/table1_q1.tex` | `d9dd632a77ee62fdbff14129d957a25766752443e0735b4607a8327ef6e67557` |
| `evidence_workspace/tables/table2_q2.tex` | `e7bfd989f6741473161ba0a232f57b329d84726b980d2064758843039fe22ff2` |
| `evidence_workspace/tables/table3_q3.tex` | `f1d39658ded807d697229ca31a447a56a28b98eef57089373df52483ad9a8104` |
| `figure_workspace/data/fig3_aggregate_effects.csv` | `9df66ec44181006fa95d076e15603654c1a775d20c7b6bfe059ba6594f3bc9ee` |

## 2. Q1--Q3 数字审计

### 2.1 Q1

冻结源：
`evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json`
（SHA-256 `7ebc0569d705a9991ac8b8d17c42113c9da052b2bec73f7c28d021e28a65a051`）。

| 项目 | 精确值 | JSON 字段 | n |
|---|---:|---|---:|
| OOD-t \(R^2\) | 0.5693493611664086 | `Q1_forecast.full.R2` | 1904 targets |
| OOD-t RMSE | 0.1505941190915099 | `Q1_forecast.full.rmse` | 1904 targets |

`main.tex`、Table 1、`MANUSCRIPT.md`、`MANUSCRIPT_ZH.md` 和
`MANUSCRIPT_ZH_FULL.md` 中的 `0.569/0.151`、`0.56935/0.15059` 均为上述
精确值的正确舍入。**PASS**。

### 2.2 Q2

Validation 冻结源：
`evidence_workspace/raw/release/val_q2_state_contract_exclusive.json`
（SHA-256 `33b40d3e6bf6e0190c9415a9e0421e9809063356dcba2350890defeeed35f2d9`）。

OOD-t 冻结源：
`evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json`
（SHA-256 `7ebc0569d705a9991ac8b8d17c42113c9da052b2bec73f7c28d021e28a65a051`）。

| Split / intervention | Full \(R^2\) | Intervened \(R^2\) | Official \(\Delta R^2\) | Paired mean \(\Delta R^2\) [paired bootstrap 95% CI] | n |
|---|---:|---:|---:|---:|---:|
| Val / state removal | .4973219642 | .4861075400 | .0112144242 | .0161625260 [.0064324081, .0259022958] | 589 |
| Val / \(T=I\) | .4973219642 | .4854160744 | .0119058898 | .0174174289 [.0078248395, .0269607494] | 589 |
| OOD-t / state removal | .5693493612 | .5493773509 | .0199720103 | .0219977686 [.0142198986, .0301760693] | 1019 |
| OOD-t / \(T=I\) | .5693493612 | .5476642387 | .0216851224 | .0240159327 [.0160867523, .0321697890] | 1019 |

字段：

- full/intervened：`Q2_load_bearing.{full,alpha0,T_identity}.R2`；
- official：`Q2_load_bearing.official_R2_full_minus_{alpha0,Tid}`；
- paired mean：`Q2_load_bearing.{closure_cut_alpha0,transition_identity}.paired.mean_delta_R2`；
- CI：同一对象的 `bootstrap95.{ci_low,ci_high}`；
- n：同一对象的 `paired.n`/`bootstrap95.n`。

验证结论：

1. **paired mean 只能搭配 paired bootstrap CI：PASS。** 当前 Table 2、正文和
   Figure 3 活跃 CSV 均遵守。
2. **official \(\Delta R^2\) 只能作为 Table 2 独立统计量：PASS。** 当前 Table 2
   将其与 paired mean/CI 分开；不得把 official delta 画进带 paired CI 的
   Figure 3。
3. state removal 是 Q2 的定义性主检验。两个 split 的 paired CI 均排除 0，
   支持 `load-bearing`。
4. `T=I` 只支持 transition involvement。冻结 JSON 明示
   `transition_margin_clean=false`，因为 identity state 对 readout 可能是分布外
   输入；不得写成定义性核心证据或“transition 必要”的干净因果证明。

所有检查版本中的显示值均为上述值的正确舍入。**PASS**。

### 2.3 Q3

冻结源：`evidence_workspace/raw/release/q3_extreme_state_audit.json`
（SHA-256 `9dae43b9a8a4fcdf0a73ef91daa58c189a88e769541ce295046cd0e938497041`）。

| Future weather | \(R^2\) | RMSE | Control loss − actual loss [geo-cluster 95% CI] | n / clusters |
|---|---:|---:|---:|---:|
| Actual | .6253516463 | .1491516260 | reference | 84 / 31 |
| Matched donor | .5893404938 | .1584189321 | .0025654681 [.0011187122, .0039874911] | 84 / 31 |
| Normalized mean | .5430064799 | .1970936896 | .0112613323 [.0054656245, .0170799321] | 84 / 31 |

性能字段：`models.exclusive.q3_aggregate_extreme.{actual,donor,mean}.{R2,rmse}`。
差值和主 CI 字段：
`models.exclusive.q3_donor_fidelity.endpoint_fidelity.extreme_actual_vs_{donor,mean}`
的 `delta_loss_mean` 与 `geo_cluster_bootstrap.{ci_low,ci_high,n,n_clusters}`。

**符号合同已确认：**

\[
\Delta\mathrm{Loss}=\mathrm{Loss(control)}-\mathrm{Loss(actual)}.
\]

正值表示 actual weather 的 endpoint loss 更低、预测更好。当前 Table 3、正文和
活跃 Figure 3 CSV 均正确。不得将它写成 “actual minus control”。

探索性 hot--dry interaction 为 `0.0004360788783136134`，geo-cluster 95% CI
`[-0.0021624635347345066, 0.003199765110504583]`，判据未通过，冻结状态为
`hotdry_enhancement_status=FAIL`。正文正确写成“不支持 extreme-specific
enhancement”。**PASS**。

### 2.4 跨文档一致性

| 检查对象 | Q1 | Q2 | Q3 | 结论 |
|---|---|---|---|---|
| `paper/main.tex` | 精确舍入一致 | official 与 paired 分开，数值一致 | 性能、差值、CI、符号一致 | PASS |
| `evidence_workspace/tables/table1_q1.tex` | 一致 | — | — | PASS |
| `evidence_workspace/tables/table2_q2.tex` | — | 一致 | — | PASS |
| `evidence_workspace/tables/table3_q3.tex` | — | — | 一致 | PASS |
| `MANUSCRIPT.md` | 一致 | 一致 | 一致 | PASS |
| `MANUSCRIPT_ZH.md` | 一致 | 一致 | 一致 | PASS |
| `MANUSCRIPT_ZH_FULL.md` | 一致 | 一致 | 一致 | **数字 PASS；状态文字需更新** |

`MANUSCRIPT_ZH_FULL.md` 仍称 Figure 3 在等待 provenance-complete evidence；
这与本轮已闭合的聚合 CSV 不一致。它不是数字错误，但正文整合会话应更新状态文字。

## 3. Figure 3 CSV 逐行审计

活跃且唯一认可的数据源：
`figure_workspace/data/fig3_aggregate_effects.csv`。CSV 内路径以仓库父目录为
基准；解析后的绝对源均位于本项目 `evidence_workspace/raw/release/`。

| CSV 行 | Panel / intervention | Estimand | Estimate / CI | n | 源及 SHA 核验 | Direction | 结果 |
|---:|---|---|---|---:|---|---|---|
| 2 | Q2 Val / state removal | paired mean \(\Delta R^2\) | .016162526 [.006432408, .025902296] | 589 | val Q2 JSON / `33b40d3e...f2d9`，匹配 | full − intervention | PASS |
| 3 | Q2 Val / \(T=I\) | paired mean \(\Delta R^2\) | .017417429 [.007824840, .026960749] | 589 | val Q2 JSON / `33b40d3e...f2d9`，匹配 | full − intervention | PASS |
| 4 | Q2 OOD-t / state removal | paired mean \(\Delta R^2\) | .021997769 [.014219899, .030176069] | 1019 | OOD JSON / `7ebc0569...a051`，匹配 | full − intervention | PASS |
| 5 | Q2 OOD-t / \(T=I\) | paired mean \(\Delta R^2\) | .024015933 [.016086752, .032169789] | 1019 | OOD JSON / `7ebc0569...a051`，匹配 | full − intervention | PASS |
| 6 | Q3 matched donor | control − actual endpoint loss | .002565468 [.001118712, .003987491] | 84 | Q3 JSON / `9dae43b9...7041`，匹配 | positive favors actual | PASS |
| 7 | Q3 normalized mean | control − actual endpoint loss | .011261332 [.005465625, .017079932] | 84 | Q3 JSON / `9dae43b9...7041`，匹配 | positive favors actual | PASS |

生成器 `figure_workspace/source/fig3_behavior.py` 对字段名、源 SHA、estimand、
CI unit 和方向执行校验；本轮未运行生成器。现有
`figure_workspace/export/fig3_behavior.{pdf,png}` 经目视核验与 CSV 一致。

### 必须隔离的旧文件

`paper/figures/data/terrastate_behavioral_evidence.csv`
（SHA-256 `c9d3477d2912e17c2e9619f5638a1f125fe6f0d5aaeced894fea1784ac9aeb6f`）
为 **FAIL / 禁止作为正文来源**：

- Q2 将 dataset-level official \(\Delta R^2\) 与 paired bootstrap CI 错配；
- Q3 将正值错误标成 “Actual minus control”；
- 所记源 SHA 不能对应当前冻结 JSON。

任何由它生成的旧 behavioral figure 只能视为归档，不得插入正文。

## 4. Caption 与过度主张审计

检查了 `main.tex` 当前 Figure 1/2、Table 1--3 caption，以及
`figure_workspace/LATEX_INCLUDES.tex`、`FIGURE_SPEC.md`、
`FIGURE_TEXT_COPY.md` 中计划 caption。

| 风险 | 当前/权威 caption | 结论 |
|---|---|---|
| SOTA 或严格排名暗示 | Table 1 明示协议未严格对齐、不作跨 panel 排名 | PASS |
| 因果或 counterfactual correctness | 正文限制明确称 Q3 是 conditional predictive fidelity，不是因果识别或 counterfactual correctness | PASS |
| extreme-specific enhancement | Table 3/正文不宣称；失败结果明确披露 | PASS |
| composition/Q4 | 无主图或主表，正文明确未作为核心经验主张 | PASS |
| 把 \(T\to I\) 写成定义性核心证据 | Figure 2、Table 2 均称 supporting evidence，并披露分布外 caveat | PASS |

两个文字工作台警告：

1. `FIGURE_TEXT_COPY.md` 的术语备忘含 “counterfactual weather” 禁用词提示；
   不得将该词复制进 caption。
2. 同文件的一个旧 Figure 2 caption 说图像 tiles 必须来自冻结 query，与当前
   `main.tex` 和权威 `LATEX_INCLUDES.tex` 的“schematic tiles”合同冲突。以当前
   `main.tex`/`LATEX_INCLUDES.tex` 为准，旧文案不得使用。

## 5. Figure 1--3 验收

| Figure | 与方法合同一致 | 与证据边界一致 | 无无来源图像/数字 | 与正文不冲突 | 总结 |
|---|---|---|---|---|---|
| Figure 1 | PASS：训练/推理路径及 training-only 分支一致 | PASS：无结果性外推 | PASS：全为原创示意元素，无实验数字/真实 EO 样本 | PASS | **PASS** |
| Figure 2 | PASS：history/state/transition/readout 与干预口一致 | PASS：state removal 为主、\(T\to I\) 为辅、Q3 仅换 future weather | PASS：schematic tiles 明示非定性结果 | PASS | **PASS** |
| Figure 3 export | PASS：Q2/Q3 estimand 与干预一致 | PASS：只画 paired Q2 和 cluster Q3；不画 Q4/hot-dry 成功 | PASS：6 个点和 CI 全可回溯 | **FAIL：尚未插入 `main.tex`，正文仍只有注释接口** | **FAIL（整合未完成，图件本身 PASS）** |

Figure 3 的最终整合只能使用
`figure_workspace/export/fig3_behavior.pdf` 和活跃聚合 CSV；不得使用
`paper/figures/data/terrastate_behavioral_evidence.csv` 或其旧图。

## 6. 公开 baseline、24 条参考文献、匿名性与种子表述

### 6.1 引用清点

- `paper/main.tex`：25 个 citation commands，34 个 key occurrences，24 个
  unique keys。
- `paper/references.bib`：24 个条目。
- missing / duplicate / unused：**0 / 0 / 0**。
- 未解析 `\input`/`\include`：0。
- 当前编译日志未见 undefined/multiply-defined citation。

24 条的作者、题目、会议/期刊、年份、现有页码、DOI/arXiv 和版本状态已逐条复核；
详细结论见 `CITATION_AUDIT.md`。没有确认的错误需要阻塞提交。自动 True Cite 对
19 个可处理条目全部返回 `verified=true`、`titleMatch=true`，但因作者格式和会场
简称产生 19 个 warning；5 个 `@misc` 由工具跳过，已人工按官方来源核验。自动
warning 不能解释为 19 个书目错误。

额外的 Bib-Check online-only 重跑在外部检查阶段无输出挂起，已中止且未修改
任何源；这是工具级 `unable to complete`，不是书目失败。当前结论由引用清点、
官方原文人工核验和成功返回的 True Cite 结果共同支持。

仍有以下非阻塞警告：

- 6 个正式条目可选补 DOI（EarthNet2021、GreenEarthNet、SimVP、ViT-Koop、
  weather-role paper、I-JEPA）；当前核心元数据正确。
- 4 个 2026 新预印本（EO-WM、VegSim、observability、group actions）应在正式
  投稿前再查一次 venue 状态。
- LatentTSF 的正式 ICML/PMLR 元数据已更新，但页码在当前官方材料中
  `unable to verify`，不得编造。
- V-JEPA 已使用正式 TMLR/OpenReview 版本；无可核验页码/DOI。

### 6.2 公开 baseline

Table 1 的 Climatology、ConvLSTM、PredRNN、Contextformer 数值逐项匹配
GreenEarthNet 论文 Table 2。公开均值未被降低，仅按表注省略不确定性。

- GreenEarthNet Table 2 内部：同一论文协议下可比较，但种子数不同。
- TerraState 与公开方法：**不构成严格可比排行榜**；当前分 panel 和 caption
  已诚实披露。
- ConvLSTM、PredRNN、Contextformer 是 3-seed mean；Climatology 是确定性
  baseline。不能称公开数字都是单种子。
- TerraState 来自一个 selected training run。正文已披露 one-run 限制，但 Table 1
  caption 最好再加入简短种子说明，避免读者只看表时误会。

EO-WM 的“世界模型”定位、物理 forcing 和 output/response diagnostics 由原文
支持；但不能据一篇论文推广成“所有/大多数 EO 世界模型只依赖输出精度”。安全
写法应归因于 EO-WM 的动机或写成“common output-level benchmarks do not by
themselves establish internal-state behavior”。

### 6.3 匿名性

- `main.tex` 为 `Anonymous Submission`，affiliation 为空。
- 活跃正文、manuscript mirrors、Figure 3 CSV、主图中未检出个人名、用户绝对路径、
  私有仓库 URL 或项目作者身份。
- 当前 PDF metadata 未见 author/creator 身份字段。

匿名性：**PASS**。证据 JSON 内部的历史集群路径不进入论文或图稿；不得复制到
submission source。

## 7. 主张边界

| 主张 | 状态 | 允许表述 | 禁止表述 |
|---|---|---|---|
| TerraState 是可干预预测状态的 EO world model | supported | “a testable predictive-state EO world model” | 完整物理地表状态、因果世界模型 |
| Q1 保留有效未来预测能力 | supported | useful OOD-t forecast skill | SOTA、严格优于公开方法 |
| predictive state 是 load-bearing | supported | state removal causes positive paired effect on Val/OOD-t | 所有预测信息都必须经过 state |
| transition 参与预测 | partially supported | identity intervention points in same direction | \(T\) 的纯净必要性/因果必要性 |
| weather input 影响预测行为并提高 endpoint fidelity | supported | actual weather predicts endpoint better than donor/mean controls | causal effect、counterfactual correctness |
| competitive performance | partially supported | public values provide historical context; performance remains useful | strict competitive ranking、best/SOTA |
| composition/Q4 | unsupported as core empirical claim | unexplored/optional extension | composition law 已验证 |
| extreme hot-dry enhancement | unsupported | CI crosses zero; no claim | enhancement 成功、极端响应被证明 |
| SOTA | unsupported | 不使用 | SOTA/state of the art |

## 8. Reproducibility checklist 逐项底稿

`paper/ReproducibilityChecklist.tex` 当前所有答案仍为空，且未被 `main.tex`
引用。以下是审计底稿，不替代作者最终选择：

| 项 | 建议状态 | 审计依据 / 必须补充 |
|---|---|---|
| 1.1 conceptual outline | Yes | 方法、方程和架构图完整 |
| 1.2 claims/limitations | Yes | Q1--Q3 与限制分开；Q4/hot-dry 被限制 |
| 1.3 related work | Yes | 24 条引用且 claim 支持已审计 |
| 2.1 theoretical results | No | 无理论结果主张 |
| 2.2--2.8 theory details | N/A | 无定理/证明 |
| 3.1 dataset statistics | Yes | minicube、时空设置、样本数已写 |
| 3.2 train/val/test splits | Yes | selection 与 OOD-t 分离已写 |
| 3.3 new dataset | N/A | 未发布新数据集 |
| 3.4 data consent/PII | N/A | 遥感公开基准，无人类受试信息 |
| 3.5 dataset citation | Yes | EarthNet2021/GreenEarthNet 已引 |
| 3.6 public accessibility | Partial | 基准公开；本地 OOD 子集/manifest 与官方完整协议不完全等同 |
| 3.7 data license | N/A/author confirm | 本文未发布新数据；仍应由作者按 checklist 原文确认 |
| 4.1 model/method description | Yes | 方程、结构、训练阶段充分 |
| 4.2 experimental settings | Partial | 最终设置充分，开发搜索范围/全部选择过程未完整披露 |
| 4.3 preprocessing code | No | appendix 未提供 |
| 4.4 experiment source code | No | submission appendix 未提供 |
| 4.5 code/data release | Author decision | 审计不能替作者承诺未来发布 |
| 4.6 code documentation | Unable to verify | 本任务禁止审计/运行训练评测代码 |
| 4.7 random seeds | Partial | one-run 已披露；seed 42 未在正文写出 |
| 4.8 compute environment | No | GPU/CPU/OS/framework version 未写 |
| 4.9 metrics/statistics definition | Partial | Q2/Q3 estimand 与 CI 已定义；指标公式/选择理由可更完整 |
| 4.10 number of runs | Yes | 明示一个 selected training run |
| 4.11 uncertainty | Yes for Q2/Q3 | paired 与 geo-cluster CI 已报告；Q1 无跨种子不确定性 |
| 4.12 significance/testing | Partial | Q2/Q3 gate 清楚；没有多种子或多重比较论证 |
| 4.13 hyperparameters | Partial | 核心优化参数已写，不是可执行完整 config |

## 9. 逆向检查与最终判定

- Table 1 的每个公开数字回到 GreenEarthNet 原论文 Table 2；TerraState 数字回到
  冻结 OOD JSON。
- Table 2 的每个 full/intervened/official/paired/CI/n 回到同一个 split 的冻结
  Q2 JSON；不同 estimand 未混配。
- Table 3 的 actual/donor/mean、差值、CI、n 回到冻结 Q3 JSON；符号正确。
- Figure 3 活跃 CSV 的每一行都通过路径、SHA、字段、估计量、CI、n 和方向检查。

**最终证据审计：DONE。**  
**提交整合尚未完成：Figure 3 未进入 `main.tex`，checklist 仍为空；这些是正文整合
会话的工作，不是证据核验阻塞。**

## 10. 正文整合会话必须处理

1. 只使用 `figure_workspace/export/fig3_behavior.pdf` 及其活跃 CSV 插入
   Figure 3；禁止使用旧 `paper/figures/data/terrastate_behavioral_evidence.csv`。
2. Figure 3 caption 必须明确 Q2 为 paired means + paired bootstrap CI，Q3 为
   control loss − actual loss + geographic-cluster CI；正值 favor actual。
3. 保持 official \(\Delta R^2\) 只在 Table 2 独立列中，不能与 paired CI 配对。
4. 保持 state removal 为 Q2 主检验，\(T\to I\) 只作 supporting evidence。
5. 更新 `MANUSCRIPT_ZH_FULL.md` 中“Figure 3 仍待 provenance”这一过时状态。
6. Table 1 caption 建议补充：公开 learned baselines 为三种子均值、Climatology
   deterministic、TerraState 为 one-run；仍不得作严格跨 panel 排名。
7. 按第 8 节填写最终 checklist；尤其必须由作者决定 code release，并补
   seed/compute environment 或诚实回答 No/Partial。
8. 不得加入 SOTA、因果/counterfactual correctness、extreme enhancement、
   composition/Q4 已验证或 transition 纯净必要性等表述。
