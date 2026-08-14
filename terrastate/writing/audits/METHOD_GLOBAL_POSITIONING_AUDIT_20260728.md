# TerraState Section 3 整体定位与说服力审计

**审计日期：** 2026-07-28  
**审计性质：** 只读定位审计；未修改正文、中文稿、PDF、图片、代码或实验结果。  
**唯一写入：** 本报告。  
**审计视角：** AAAI 审稿人 + 论文编辑。  
**事实边界：** 3.1–3.4 的方法事实、公式、训练身份、信息边界、接口定义和 Q1–Q3 证据全部硬冻结。

## 0. 输入与审计边界

本轮完整核对了：

- `paper/main.tex` 的标题、摘要、Introduction、Related Work、Section 3、Section 4、Limitations、Conclusion 和 Figure 1–3 captions；
- `MANUSCRIPT_ZH_FULL.md`；
- `METHOD_3_2_FINAL_AUDIT_20260728.md`；
- `METHOD_3_3_FINAL_AUDIT_20260728.md`；
- `METHOD_3_4_FINAL_AUDIT_20260728.md`；
- 当前冻结的 3.1 正文。项目中没有单独命名的 3.1 final-audit 文件，因此以已冻结正文及其既有编译审阅记录为准；
- `METHOD_AAAI_WRITING_AUDIT.md`；
- `METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md`；
- `AUTHOR_NOTES.md`、claim–evidence audits 与 `evidence_workspace/results_ledger.json`；
- `WorldModel2026/思路整理进展/84_...md` 中的单模型方法论文主线；
- 既有 AAAI 写作锚点总结。外部论文只用于段落功能和审稿人阅读顺序，不作为 TerraState 技术证据。

本报告不重新审计公式，也不建议改变任何硬冻结内容。

## 1. 总体结论

## POSITIONING_NEEDS_MINOR_LIFT

TerraState 当前已经具备清楚、可信且证据安全的方法论文定位。审稿人读完标题、摘要和 Introduction 后，能够回答：

1. **缺口是什么：** 固定时域像素精度不能判定内部状态是否真正参与预测，也不能判定未来天气是否通过所声明路径影响预测。
2. **为什么重要：** 一个准确预测器仍可能绕过声明状态或弱用天气，因此输出精度不足以支持预测状态世界模型的内部主张。
3. **方法新意是什么：** TerraState 显式构建历史预测状态，用共享天气条件转移推进状态，再把状态读出作为可移除贡献纳入最终预测；训练期用未来观测表示锚定推进状态。
4. **为什么属于世界模型：** 方法从部分历史推断状态，在外生天气驱动下推进状态，并把推进状态解码回未来可观测量；Q2/Q3 进一步检验状态使用和天气响应。

Section 3 已形成明确闭环：

> predictive-state formulation → inference architecture → future-state learning → post-training interfaces。

读者不需要自行拼接技术逻辑。当前需要提升的不是事实完整度，而是三点编辑性问题：

- 少数 gap 句过于普遍，容易被审稿人攻击为低估已有天气响应或世界模型工作；
- 3.3 与 3.4 的开场偏训练身份/否定式说明，future-state anchoring 与干预接口组成的 method–evidence loop 尚未被最有力地说出来；
- 因果、物理状态、extreme-specific enhancement 和 composition 的限制在多个章节重复，导致结尾力度略被削弱。

这些问题可以通过段首、段尾和过渡句的最小调整解决，无需重写 Section 3，也不需要改变任何公式、方法事实或证据边界。

### 优先级计数

- **P0：0**
- **P1：7**
- **P2：6**

没有 P0，说明当前主线已经清楚；P1/P2 只用于增强第一印象和减少自我削弱。

## 2. 当前最清晰的一句话核心贡献

### English

> **TerraState is a predictive-state world model that exposes a history-derived, weather-transitioned state as an explicit forecast contribution, making state use and weather response directly testable in the same frozen model.**

### 中文

> **TerraState 是一个预测状态世界模型：它将由历史构建、经天气条件转移推进的状态作为显式贡献纳入最终预测，从而能在同一冻结模型上直接检验状态是否参与预测以及是否响应天气。**

这句话同时覆盖：

- world-model 身份；
- history → state → weather transition → forecast 的方法链；
- 显式 state-mediated contribution；
- same-model post-training testability；
- Q2 与 Q3；

且没有暗示 SOTA、因果性、完整物理状态、composition、non-collapse 或极端天气额外增强。

## 3. 第一印象审计

| 审稿人问题 | 当前是否能回答 | 当前答案出现位置 | 判断 |
|---|---|---|---|
| TerraState 解决什么缺口？ | 能 | Abstract lines 32–38；Introduction lines 89–110 | **清楚**。但 “selected almost entirely” 稍显普遍化 |
| 为什么普通像素指标不够？ | 能 | Introduction lines 89–96 | **清楚且有结构性问题句** |
| 方法新意是什么？ | 能 | Abstract lines 38–45；Introduction lines 112–123；贡献 1–2 | **清楚**。`augments a backbone` 略有“预测器加插件”的第一印象 |
| 为什么是世界模型？ | 能 | Introduction lines 57–64；3.1 lines 204–217 | **清楚**。状态、外生 forcing、transition、readout 均到位 |
| 为什么不是普通预测器加消融？ | 基本能 | 3.1 显式 state path；3.2 additive route；3.3 future anchor；3.4 matched interfaces | **已回答，但 method–evidence loop 还可更显性** |
| 为什么不是 benchmark/protocol 论文？ | 能 | Introduction 以方法为中心；Method 先于实验；Related Work 与贡献列表 | **通过**。Q1–Q3 是同一模型的证据而非新尺子 |

### 第一印象结论

当前第一印象已经是“方法型 predictive-state world model”，不是 benchmark。最容易被怀疑的地方不是标题或 3.1，而是：

1. Abstract 的 `augments a forecasting backbone` 容易把方法读成 backbone + residual branch；
2. 3.3 第一段先讲三种训练身份，方法洞见出现得稍晚；
3. 3.4 以 “alignment does not by itself...” 开场，正确但偏防御；
4. Conclusion 以四项开放问题结束，最后落点弱于实际支持的联合结论。

## 4. Section 3 整体推进审计

目标逻辑及当前显性程度如下：

| 目标逻辑 | 当前承载位置 | 显性程度 | 审计判断 |
|---|---|---:|---|
| 1. 世界模型主张不能只由架构名称成立 | Abstract lines 42–45；Introduction lines 89–110 | 5/5 | 已显性呈现 |
| 2. TerraState 将主张落实为历史构建、天气推进、显式读出的状态 | 3.1 总式；3.2 三模块 | 5/5 | 已显性呈现 |
| 3. Future-state learning 塑造推进状态 | 3.3 Future-State Representation Target | 4/5 | 技术清楚，但方法意义可以更早出现 |
| 4. Post-training interfaces 检验状态使用与天气响应 | 3.3 末句 + 3.4 | 4/5 | 已显性呈现，但过渡可以更主动 |
| 5. 方法机制与 Q1–Q3 形成同一模型上的证据闭环 | Introduction lines 112–145；3.4；Section 4 | 4/5 | 逻辑成立；可用一句桥接强化 |

### 核心判断

Section 3 的因果逻辑已经成立，不需要重构。最小提升点位于：

- 3.3 第一段第一句：先说 future-state learning 解决什么，再区分三个身份；
- 3.3 最后一段与 3.4 开头：将“alignment 不能证明”改成更主动的“alignment 塑造什么、interfaces 检验什么”；
- 3.2 readout 段末：突出 additive design 的方法价值，而不是先强调 context-only branch 仍可保留信息。

## 5. 核心定位句安全等级

| 候选定位句 | 等级 | 审计理由 | 推荐安全版本 |
|---|---|---|---|
| TerraState turns the world-state claim from an architectural assertion into an empirically testable question. | **SAFE_WITH_QUALIFIER** | 机制与 Q2/Q3 支持 testability，但 “the world-state claim” 容易被理解为对所有世界模型作普遍裁决 | **For weather-driven EO forecasting, TerraState turns the predictive-state claim from an architectural assertion into an empirically testable question.** |
| TerraState exposes rather than merely names a predictive state. | **SAFE_WITH_QUALIFIER** | “exposes”由显式 \(r_h\) 路径支持；“merely names”可能把现有工作稻草人化 | **TerraState exposes an explicit predictive-state path rather than relying on an implicit latent-state label.** |
| The explicit state-mediated path makes state use and weather response separately testable. | **SAFE** | Q2 在 `r_h` 切点；Q3 只替换 `T_\psi` 的天气输入，两者结构上可分 | 可直接使用 |
| Future-state anchoring and post-training interventions form a method–evidence loop. | **SAFE_WITH_QUALIFIER** | Alignment 塑造状态，interventions 检验状态；但 anchoring 本身不证明 Q2/Q3 | **Future-state anchoring shapes the transitioned state, while post-training interventions test whether that state carries forecast information and responds to supplied weather.** |
| TerraState provides a falsifiable predictive-state formulation for weather-driven EO forecasting. | **SAFE_WITH_QUALIFIER** | “falsifiable”需落实到冻结接口和任务范围，不能泛化为完整世界模型判准 | **TerraState provides an operationally falsifiable predictive-state formulation for weather-driven EO forecasting under a frozen intervention protocol.** |

五个候选中没有 `UNSUPPORTED`。风险主要来自范围过宽或对已有工作的隐含贬低，而不是 TerraState 自身证据不足。

## 6. 世界模型身份审计

### 6.1 当前兑现链

`world model` 在全文不是空标签，而由以下结构逐级兑现：

1. **Partial observability：** 历史 EO 稀疏且受云遮挡；
2. **Predictive state：** \(q_\theta\) 与 \(P_\rho\) 从历史构建空间状态；
3. **Exogenous forcing：** future weather 只经共享 \(T_\psi\) 进入；
4. **State dynamics：** 对每个 horizon 从同一 \(z_t\) 执行直接状态转移；
5. **Observation mapping：** \(O_\omega\) 把推进状态读出为栅格贡献；
6. **Forecast participation：** \(r_h\) 显式进入最终预测；
7. **Empirical testability：** Q2/Q3 在同一冻结模型上测试 state use 与 weather response。

因此，3.2–3.4 不需要机械重复 `world model`。继续通过 state、transition、forcing、readout 和 interventions 表达身份，比每段重复标签更成熟。

### 6.2 是否被降格为普通 forecaster

没有发生整体降格，但三处措辞会轻微触发该印象：

- Abstract：`augments a forecasting backbone with...`；
- 3.2 readout 段：先写 context-only branch 仍可保留信息，再写 state contribution；
- 3.4：接口术语密集，若脱离 3.1/3.2 阅读，容易被看作 ablation protocol。

解决方式不是夸大状态充分性，而是主动说明：

> 状态贡献是标准预测的一部分，并且其显式结构让“是否使用状态”和“是否响应天气”成为两个可以分别检验的问题。

## 7. 与现有工作的差异审计

### 7.1 当前稳健对比尺度

最稳健、最有力的差异不是：

- “现有方法都不是世界模型”；
- “现有方法完全不检验天气”；
- “TerraState 首次提出预测状态”；
- “TerraState 比所有预测器更准确”。

而是：

> **Prior EO forecasting work principally validates predicted observations, while TerraState additionally exposes a state-mediated forecast path and tests whether that path both contributes to prediction and responds faithfully to supplied weather.**

中文：

> **已有 EO 预测工作主要验证未来观测的预测质量；TerraState 进一步暴露一条状态介导的预测路径，并检验该路径是否实际贡献于预测、是否忠实响应所提供的天气。**

该比较：

- 承认 EO-WM、Diaconu 等工作已研究天气响应；
- 不否认 VegSim 等模型的世界模型身份；
- 将差异落在“内部状态是否在预测闭环中并可被匹配干预”；
- 与 Q2/Q3 的真实证据同构。

### 7.2 各章节分工

| 章节 | 应承担的差异强度 | 当前状态 | 判断 |
|---|---|---|---|
| Introduction | 提出结构性缺口并给一句最接近工作差异 | 已做到 | 略需限定普遍化语句 |
| Related Work | 承认现有天气响应/latent dynamics，并指出 TerraState 的 state-path testability | 已做到 | composition 段尾会分散当前主线 |
| Method | 展示差异如何由结构实现，不重复批评他人 | 已做到 | 3.2–3.4 边界成熟 |
| Experiments | 用 Q1/Q2/Q3 兑现，不建立新 benchmark | 已做到 | Section 4 待独立审计 |

## 8. 过度防御与重复限制清单

| 位置 | 当前限制 | 是否必须原地保留 | 建议 |
|---|---|---:|---|
| Introduction lines 105–106 | “narrower than a complete physical state or a causal simulator” | 否 | 压缩或移至该段末尾；Introduction 先完成方法定位 |
| Related Work lines 176–180 | 不替代 probabilistic forecasting/scenario simulation | 是，简短保留 | 这是最接近工作的范围差异，不算无效防御 |
| Related Work lines 195–198 | composition 仅探索 | 否 | 当前无 Q4 主张，可从 Related Work 删除或只在 Limitations 出现一次 |
| 3.1 lines 247–249 | 不声称完整物理状态或因果模拟器 | 是 | 保留一次，作为操作性 world-model 定义边界 |
| 3.2 lines 311–314 | context-only branch 可能保留预测信息 | 是，但可正向改写 | 保留“不要求全部信息经状态”的事实，突出 additive isolation |
| 3.3 lines 400–404 | FS alignment 不能证明 load-bearing | 是 | 改成 “alignment shapes; interfaces test”，减少否定式开头 |
| 3.4 lines 424–427 | T→I 的 readout OOD 限制 | 是 | 必须与 supporting diagnostic 原地绑定 |
| 3.4 lines 462–464 | 非因果、非反事实、非 extreme enhancement | 部分 | causal/counterfactual 原地保留；extreme-specific enhancement 移至 Results/Limitations |
| Figure 2 caption | 不检验 composition/causal effects | 否 | caption 只需说明接口，不必再次列出未主张事项 |
| Q3 Results lines 702–704 | hot-dry null | 是 | 必须与真实负结果原地报告 |
| Limitations lines 708–727 | 物理、因果、极端、单次训练、泛化、composition | 是 | 这是完整限制的主要归宿 |
| Conclusion lines 737–739 | 再列 causal/extreme/composition/generalization | 否 | 用受限但积极的联合结论收尾；完整限制已在上一节 |

### 重复限制的推荐归宿

- **完整物理状态：** 3.1 一次 + Limitations；
- **因果/反事实：** 3.4 接口边界一次 + Limitations；
- **extreme-specific enhancement：** Q3 Results + Limitations；
- **composition：** Limitations 一次；
- **训练稳定性和跨数据集泛化：** Limitations；
- **不同协议不可严格排名：** Table 1 caption / Q1 setup。

## 9. 主动表达与动词审计

| 位置 | 当前表达 | 推荐动词/结构 | 为什么不扩大主张 |
|---|---|---|---|
| Abstract lines 39–42 | “augments a forecasting backbone” | **structures forecasting around / integrates** | 描述既有 \(q\to P\to T\to O\) 与加法路径，不宣称性能提升 |
| Introduction lines 98–110 | “addresses this gap” | **turns / formulates / exposes** | 只强化问题到方法的动作，不改变证据 |
| 3.1 lines 244–247 | “supports separate tests” | **isolates two testable questions** | Q2/Q3 切点确实分离 |
| 3.2 lines 298–299 | “keeps their roles explicit” | **isolates future forcing within state evolution** | future weather 唯一进入 \(T_\psi\)，为实现事实 |
| 3.2 lines 312–314 | “can be evaluated independently” | **exposes ... for direct evaluation** | 显式加法与 `alpha=0` 支持该描述 |
| 3.3 line 360 | “anchors” | **保留 anchors** | 是最准确的方法动词，不需要换成 `enhances` |
| 3.3 lines 400–404 | “cannot by itself establish” | **shapes ..., while interfaces test ...** | 仍保留证据边界，但先说正面方法功能 |
| 3.4 lines 408–412 | “we therefore define” | **we expose / apply two post-training interfaces** | 接口在同一模型上确实可用，不宣告结果 |
| Figure 2 caption | “organizes” | **traces / shows** | 仅改善视觉叙述动作 |
| Conclusion lines 731–739 | “supports” | **保留 supports** | 联合结论有证据但仍受单模型、冻结协议限制，不宜用 `demonstrates` 作无条件结论 |

不推荐在核心联合结论中使用 `demonstrates`。它可以用于局部、严格结果句，例如 “Table 2 demonstrates a positive paired effect under the specified intervention”，但全文结论应继续用 `supports`。

## 10. Claim–Evidence 映射

| 内容 | 当前最强允许主张 | 方法/结果证据 | 当前表达强度 | 推荐强度 |
|---|---|---|---|---|
| 论文定位 | TerraState 是天气驱动 EO 预测中的 task-specific testable predictive-state world model | partial history → state → forcing-conditioned transition → readout；predictive-state literature | **刚好** | 保持；避免完整环境模拟含义 |
| 方法贡献 | TerraState 让空间 predictive state 作为显式、可移除贡献进入预测，并暴露独立 weather path | Equations (1)–(4)；Q2/Q3 interfaces | **略显不足**于 3.3/3.4 过渡 | 更主动表达 explicit path + separate testability |
| Future-state learning | Frozen future representation anchors terminal transitioned state without entering inference | Equation (6)、三种训练身份与信息边界 | **技术充分，定位略弱** | 强调 future evidence shapes state，不声称 load-bearing |
| Q1 | TerraState retains useful OOD-t forecast skill | \(R^2=0.56935\)，RMSE \(=0.15059\) | **刚好** | 保持 `useful`，不使用 SOTA/competitive ranking |
| Q2 | State-mediated contribution is load-bearing on validation and OOD-t under the frozen intervention | official deltas + paired CIs above zero | **刚好** | 保持；T→I 继续 supporting |
| Q3 | Predictive-state path is weather-responsive under the frozen matched protocol | actual/control output response + both geo-cluster fidelity CIs above zero | **部分位置略宽** | 在联合结论中补 `under the frozen protocol/in this setting` |
| 世界模型联合结论 | 一个保留有用预测能力的 TerraState 模型暴露出承载预测且响应所供天气的 predictive state | Q1 + Q2 + Q3，同一选定模型 | **基本刚好** | 用 `supports`，不升级为物理、因果、可组合状态 |

## 11. Section 3 逐段力度审计

| 段落 | 当前唯一信息 | 对主线作用 | 力度 1–5 | 过度技术化 | 过度防御 | 是否需回扣 | 推荐最小英文 | 推荐最小中文 |
|---|---|---|---:|---|---|---|---|---|
| 3.1 P1 | 将天气驱动 EO world modeling 表述为历史状态、forcing 推进和未来解码 | 建立世界模型任务身份 | 5 | 否 | 否 | 否 | 保持 | 保持 |
| 3.1 P2 | TerraState 将 state contribution 显式放入最终预测 | 方法身份与普通预测器差异 | 5 | 否 | 否 | 否 | 保持 | 保持 |
| 3.1 P3 | 定义输入、符号及 \(q\to P\to T\to O\) 总式 | 给全文技术地图 | 4 | 必要技术 | 否 | 否 | 保持 | 保持 |
| 3.1 P4 | 定义信息边界与可检验性质，并限制物理/因果含义 | 将世界模型身份落到可验证结构 | 4 | 否 | 轻微 | 可正向收束 | “This information boundary isolates state use from weather response, while treating \(z_t\) as a predictive—not complete physical—state.” | “这一信息边界把状态使用与天气响应分开检验，同时只把 \(z_t\) 视为预测状态，而非完整物理状态。” |
| 3.2 opening | 给出 inference architecture 三模块 | 从总式进入模块 | 4 | 否 | 否 | 否 | 保持 | 保持 |
| 3.2 History | 同一历史前向产生 context forecast 与 spatial state | 建立共享历史基础和空间状态 | 4 | 适度 | 否 | 否 | 保持 | 保持 |
| 3.2 Transition | weather prefix、patch geo、horizon 经共享 residual transition 推进状态 | 兑现 weather-driven dynamics | 4 | 适度 | 否 | 建议一句 | “This separation isolates future meteorological forcing within state evolution.” | “这种分离把未来气象驱动明确限定在状态演化路径中。” |
| 3.2 Readout | state token 读出 raster \(r_h\)，与 \(b_h\) 相加 | 兑现 forecast-bearing state | 4 | 否 | 轻微 | 建议正向改写 | “The additive design isolates a distinct state-mediated forecast contribution for direct evaluation.” | “加性结构隔离出一项独立的状态介导预测贡献，可对其进行直接评估。” |
| 3.3 Identities | 区分 student、KD teacher、target encoder | 保证训练身份和推理边界 | 3 | 偏技术身份表 | 否 | **需要** | “To align the transitioned state with observed future evidence without exposing future EO at inference, training separates the deployable student from two frozen reference branches.” | “为利用真实未来观测约束推进状态、同时避免未来 EO 进入推理，训练过程将可部署学生模型与两条冻结参考分支分开。” |
| 3.3 Forecast objectives | GT 保持真实预测，KD 约束到强教师，且聚合不同 | 保护 forecast usefulness | 4 | 必要技术 | 否 | 否 | 保持 | 保持 |
| 3.3 Future target | 未来 EO 冻结表示锚定 terminal transitioned state | 核心状态学习洞见 | 5 | 适度 | 否 | 否 | 保持 | 保持 |
| 3.3 Total/boundary | 汇总唯一目标，删除训练支路，并把 load-bearing 交给干预 | 从学习机制转向证据 | 3 | 否 | 偏否定式 | **需要** | “Future-state alignment shapes what the transitioned state represents; the following interfaces test whether that state affects forecasts and responds to supplied weather.” | “未来状态对齐塑造推进状态所表达的内容；后续接口再检验该状态是否影响预测并响应所提供的天气。” |
| 3.4 opening | 说明为什么需要两个训练后接口 | 建立 method–evidence loop | 3 | 否 | 偏否定式 | **需要** | “To test whether the learned state is used by the forecast and responds to supplied weather, we expose two post-training interfaces on the same frozen TerraState model.” | “为检验学习到的状态是否真正用于预测并响应所提供的天气，我们在同一冻结 TerraState 模型上暴露两个训练后接口。” |
| 3.4 Q2 | `alpha=0` 精确恢复 \(b_h\)，定义 load-bearing；T→I 辅助 | 使 state-use claim 可证伪 | 4 | 统计边界略密 | 必要 | 否 | 保持；后续只可压缩固定量列表 | 保持 |
| 3.4 Q3 | 只替换 \(T\) 的天气输入，定义 response/fidelity/weather-responsive | 使 driver claim 可证伪 | 4 | 较技术 | 末句防御较长 | 可压缩 | 保留 causal/counterfactual 限定；将 extreme-specific enhancement 留给 Results/Limitations | 同步处理 |

## 12. 全篇术语一致性

| 术语 | 当前一致性 | 发现的问题 | 推荐统一方式 |
|---|---|---|---|
| testable predictive-state world model | 高 | Abstract 因断句分为两句，但语义一致 | 保持为核心身份 |
| predictive state | 高 | `world state` 偶尔用于问题表述 | 描述 TerraState 时优先 `predictive state`；`world-state claim`仅作上位问题 |
| context-only forecast | 高 | Figure 2/中文偶有 “context forecast” | 首次 `context-only forecast \(b_h\)`，后文不换名 |
| state-mediated contribution | 中高 | Abstract/Figure captions 常简写 `state contribution` | 首次完整定义，后文允许 `state contribution` |
| shared weather-conditioned transition | 中 | Figure 2 caption 用 `weather-conditioned shared dynamics`；其他位置用 `shared transition` | 正式模块统一为 `shared weather-conditioned transition` |
| future-state anchoring/alignment | 中 | `anchor`、`anchoring`、`alignment`交替 | 机制称 `future-state anchoring`；损失/优化过程称 `future-state alignment` |
| state-contribution intervention | 中高 | Experiments 用 `state removal`、caption 用 `state-contribution removal` | 首次 `state-contribution intervention (state removal)`，后文用 `state removal` |
| load-bearing | 高 | 无实质冲突 | 保持 |
| controlled weather-path substitution | 中 | Experiments 多用 `weather intervention/replacement` | Method 首次定义正式名；Results 可用 `weather substitution` |
| forecast-window response fidelity | 中 | Figure 3 用 `weather-response fidelity`；Q3 标题用 `Weather-Forcing Response` | 层级固定：operation = weather-path substitution；observable = forecast response；criterion = forecast-window response fidelity |
| weather-responsive predictive state | 高 | Conclusion 缺 frozen-protocol qualifier | 联合结论补范围限定 |
| matched-donor weather | 中高 | Figure 2 caption 首次展开漏掉 quality | 首次写 `season-, geography-, and quality-matched donor weather`，后文简称 matched-donor weather |

## 13. AAAI 审稿人模拟

### 13.1 支持型审稿人

- **最可能认可：** 一个模型同时提供 useful forecast skill、load-bearing state path 和 controlled weather response；方法与证据同构。
- **最可能追问：** future-state anchor 相比普通表示对齐的具体方法价值是什么。
- **当前正文是否回答：** 技术上回答充分，定位上略晚。
- **最小安全句：**  
  *“Future-state anchoring shapes the representation advanced by \(T_\psi\), while the post-training interfaces independently test whether that representation matters to prediction.”*
- **禁止夸大：** 不写 anchoring 已经证明 load-bearing/non-collapse。

### 13.2 怀疑“只是预测器加消融”的审稿人

- **最可能认可：** `r_h` 是标准 forward 的组成，不是只在分析时附加的 probe；`alpha=0` 精确恢复 matched context-only forecast。
- **最可能攻击：** context-only branch 已经预测大部分输出，新增状态路径只是小 residual。
- **当前正文是否回答：** 3.2 与 Q2 已回答，但 Abstract 的 `augments a backbone` 加重了该印象。
- **最小安全句：**  
  *“The state branch is part of the standard forecast, and its additive form provides a matched intervention that removes only the state-mediated contribution.”*
- **禁止夸大：** 不写全部预测信息必须经过状态，不用“小 residual 也等于完整世界状态”式辩护。

### 13.3 怀疑“world model 定义自创”的审稿人

- **最可能认可：** predictive-state literature 本来就以未来可观测量定义状态；TerraState 给出 task-specific 操作化。
- **最可能攻击：** 作者用自己设计的 Q2/Q3 决定什么模型有资格叫 world model。
- **当前正文是否回答：** Introduction 和 Related Work 已强调不做真假裁判，但预测状态文献锚点主要在 Related Work，Introduction 定义段可更紧地承接。
- **最小安全句：**  
  *“Following the predictive-state view of defining state through future observables, we adopt task-specific tests of forecast contribution and forcing response rather than a universal criterion for world models.”*
- **禁止夸大：** 不写 `first`、`only valid world model`、`all prior methods merely name states`。

### 13.4 关注实验精度不够强的审稿人

- **最可能认可：** Q1 没被隐藏；公开与本地 panel 分开；论文不声称 SOTA。
- **最可能攻击：** TerraState 的公开精度没有明显优势，机制贡献是否值得复杂度。
- **当前正文是否回答：** Q1 诚实，Q2/Q3 提供正交机制证据；Section 4 仍需单独审查完整性。
- **最小安全句：**  
  *“We use forecast skill as a qualification for interpreting the state evidence, not as a claim of cross-protocol accuracy superiority.”*
- **禁止夸大：** 不写 competitive with SOTA、non-inferior、outperforms 或把不同协议数值当严格排名。

## 14. 建议增强位置清单

## 14.1 P0：必须增强，否则主线不清

**数量：0。**

当前没有会让主线无法成立的定位缺口。

## 14.2 P1：显著改善说服力

### P1-1 — Abstract/Introduction 的 gap 范围

- **当前句：**  
  “Yet such models are selected almost entirely by fixed-horizon pixel accuracy...”
- **推荐英文：**  
  “Yet such models are typically evaluated primarily by fixed-horizon pixel accuracy, which cannot establish whether an internal representation functions as a forecast-bearing, weather-responsive predictive state.”
- **推荐中文：**  
  “然而，这类模型通常主要通过固定时域像素精度进行评价，而该指标无法判定内部表示是否真正构成承载预测、响应天气的预测状态。”
- **安全性：** 将过度普遍化改为稳健范围，同时保留核心缺口。
- **篇幅：** 基本不增加。

### P1-2 — Abstract 的方法身份

- **当前句：**  
  “TerraState augments a forecasting backbone with a spatial state...”
- **推荐英文：**  
  “TerraState structures forecasting around a spatial predictive state inferred from cloud-masked histories, advanced by a shared transition conditioned on future weather, geography, and elapsed time, and read out as an explicit contribution to the final forecast.”
- **推荐中文：**  
  “TerraState 围绕一个空间预测状态组织预测过程：该状态由云掩膜历史推断，在未来天气、地理和经过时间条件下由共享转移推进，并被读出为最终预测中的显式贡献。”
- **安全性：** 只是重述真实 forward，减少“backbone 加插件”印象。
- **篇幅：** 可与后一句合并，净篇幅接近不变。

### P1-3 — Introduction 的 predictive-state 文献锚点

- **当前句：**  
  “TerraState addresses this gap by turning the world-state claim into a testable model property. We call a representation...”
- **推荐英文：**  
  “Following the predictive-state view of defining state through future observables, TerraState turns the world-state claim into a testable model property: the state is inferred from partial history, advanced under future forcing, and decoded into an observable forecast.”
- **推荐中文：**  
  “沿用通过未来可观测量定义状态的预测状态视角，TerraState 将世界状态主张转化为可检验的模型性质：该状态由部分历史推断，在未来驱动下推进，并被解码为可观测预测。”
- **安全性：** 使用已有 `littman2001predictive` 文献锚点，表明这是 task-specific 落地而非自创通用资格标准。
- **篇幅：** 增加一个引用，句数可保持。

### P1-4 — Introduction 的 Q3 预告

- **当前句：**  
  “Q3 replaces future weather to test whether the transition uses the supplied forcing in the correct predictive direction.”
- **推荐英文：**  
  “Q3 replaces future weather to test whether the state-mediated path responds to the supplied forcing and achieves greater forecast-window fidelity under actual weather than under frozen controls.”
- **推荐中文：**  
  “Q3 替换未来天气，以检验状态介导路径是否响应所提供的驱动，以及真实天气是否比冻结对照具有更高的预测窗口保真度。”
- **安全性：** 与实际 Q3 estimand 和结论一致，避免 `correct direction` 被理解为物理或因果正确。
- **篇幅：** 小幅增加。

### P1-5 — 3.3 的方法目的

- **当前句：**  
  “Training separates the deployable TerraState student from two frozen reference branches.”
- **推荐英文：**  
  “To align the transitioned state with observed future evidence without exposing future EO at inference, training separates the deployable TerraState student from two frozen reference branches.”
- **推荐中文：**  
  “为利用真实未来观测约束推进状态、同时避免未来 EO 进入推理，训练过程将可部署的 TerraState 学生模型与两条冻结参考分支分开。”
- **安全性：** 只提前说明已有训练设计的目的，不声称 alignment 已证明 Q2。
- **篇幅：** 增加约 11 个英文词。

### P1-6 — 3.4 的 method–evidence bridge

- **当前句：**  
  “Future-state alignment shapes the learned representation, but it does not by itself show...”
- **推荐英文：**  
  “To test whether the learned state is used by the forecast and responds to supplied weather, we expose two post-training interfaces on the same frozen TerraState model. Future-state alignment shapes the representation; these interfaces evaluate its predictive role.”
- **推荐中文：**  
  “为检验学习到的状态是否真正用于预测并响应所提供的天气，我们在同一冻结 TerraState 模型上暴露两个训练后接口。未来状态对齐用于塑造表示，这些接口则评估其预测作用。”
- **安全性：** 保留 learning signal 与 empirical evidence 的严格分工，先给正面目的。
- **篇幅：** 与当前三句接近。

### P1-7 — Conclusion 的最终落点

- **当前句：**  
  “Together, these results support a load-bearing, weather-responsive predictive state while leaving causal interpretation, extreme-specific enhancement, temporal composition, and broader generalization open.”
- **推荐英文：**  
  “Together, under the frozen protocol, these results support TerraState's core claim: a useful forecaster can expose a predictive state that carries forecast information and responds faithfully to supplied weather.”
- **推荐中文：**  
  “综合来看，在冻结协议下，这些结果支持 TerraState 的核心主张：一个具备有效预测能力的模型可以暴露出承载预测信息、并忠实响应所提供天气的预测状态。”
- **安全性：** 加入 protocol qualifier；所有完整限制已在前一节，不需要结论再次逐项枚举。
- **篇幅：** 略缩短。

## 14.3 P2：可选文风提升

### P2-1 — Related Work 的稳健比较

- **当前句：**  
  “These works primarily establish the quality of predicted observations. TerraState adds a different requirement...”
- **推荐英文：**  
  “Across these forecasting paradigms, the principal evidence concerns the quality of predicted observations. TerraState additionally exposes a state-mediated forecast path and tests both its predictive role and its response to supplied weather.”
- **推荐中文：**  
  “在这些预测范式中，主要证据集中于未来观测的预测质量。TerraState 进一步暴露状态介导的预测路径，并检验其预测作用及其对所提供天气的响应。”
- **安全性：** 避免声称既有工作没有天气分析，同时明确 TerraState 的增量。
- **篇幅：** 基本不变。

### P2-2 — 3.2 Transition 的结构价值

- **当前句：**  
  “Separating historical state construction from future forcing keeps their roles explicit.”
- **推荐英文：**  
  “Separating historical state construction from future forcing isolates future meteorological forcing within state evolution.”
- **推荐中文：**  
  “将历史状态构建与未来驱动分开，使未来气象驱动被明确限定在状态演化路径中。”
- **安全性：** 直接来自 future weather 唯一进入 \(T_\psi\) 的硬事实。
- **篇幅：** 不增加。

### P2-3 — 3.2 Readout 的正向收束

- **当前句：**  
  “The context-only branch may retain predictive information; the additive design instead exposes...”
- **推荐英文：**  
  “The additive design isolates a distinct state-mediated forecast contribution for direct evaluation, while retaining the context-only forecast as its matched reference.”
- **推荐中文：**  
  “加性结构隔离出一项可直接评估的状态介导预测贡献，同时保留仅上下文预测作为匹配参照。”
- **安全性：** 不要求全部预测经过 state，也不提前宣告 Q2 通过。
- **篇幅：** 略缩短。

### P2-4 — 3.3→3.4 的段尾连接

- **当前句：**  
  “Future-state alignment shapes the transitioned state, but it cannot by itself establish that the state is load-bearing...”
- **推荐英文：**  
  “Future-state alignment shapes what the transitioned state represents; the following interfaces test whether that state affects forecasts and responds to supplied weather.”
- **推荐中文：**  
  “未来状态对齐塑造推进状态所表达的内容；后续接口再检验该状态是否影响预测并响应所提供的天气。”
- **安全性：** 不把 alignment 写成结果证据，且自然进入 3.4。
- **篇幅：** 接近不变。

### P2-5 — 移除 composition 对当前主线的干扰

- **当前句：**  
  Related Work lines 195–198 介绍 structured operators 后说明 composition 为 exploratory extension；Conclusion 再次列出 temporal composition。
- **推荐英文：**  
  主文当前不需要补充句；若保留文献，只写相关 latent-dynamics 背景，不将 composition 设为本文待验证能力。完整边界留在 Limitations。
- **推荐中文：**  
  当前主文无需增加组合性说明；若保留相关文献，只用于潜空间动力学背景，组合性未验证的边界统一放入局限性。
- **安全性：** Q4 不属于核心证据，删除重复不会扩大任何主张。
- **篇幅：** 减少。

### P2-6 — Captions 与正文术语统一

- **当前句：**  
  Figure 2 使用 `weather-conditioned shared dynamics` 和不完整的 season/geography donor 定义；Figure 3 使用 `weather-response fidelity`。
- **推荐英文：**  
  统一为 `shared weather-conditioned transition`；首次定义 `season-, geography-, and quality-matched donor weather`；Figure 3 使用 `forecast-window response fidelity`。
- **推荐中文：**  
  统一为“共享天气条件转移”“季节、地理和质量匹配的供体天气”“预测窗口响应保真度”。
- **安全性：** 只做术语校准，不改变图表数据或方法事实。
- **篇幅：** 极小。

## 15. 最小增强补丁计划

在保持方法硬冻结的前提下，建议最多进行以下局部调整：

1. **Abstract：** 两处短改——限定 gap 范围；把 `augments a backbone` 改成 state-centered forward 描述。
2. **Introduction：** 两处短改——用 predictive-state literature 锚定操作性定义；把 `correct predictive direction` 改成 forecast-window fidelity。
3. **Related Work：** 一处短改——软化对既有工作的概括；可删除 composition 分支。
4. **3.2：** 两个段尾句正向化——transition 的 forcing isolation；readout 的 matched additive contribution。
5. **3.3：** 第一段首句加入训练目的；最后一句形成主动桥接。
6. **3.4：** 只改总导入的句序；两个接口正文、Equation (8) 与判据完全不动。
7. **Conclusion：** 最后一句补 frozen-protocol qualifier，并以正面联合结论收尾。
8. **Captions：** 只统一正式术语；Figure 2 图像本体继续由独立视觉任务处理。

明确不做：

- 不重写 Section 3；
- 不改变任何公式；
- 不改变 q/P/T/O、direct transition、加法或训练目标；
- 不修改 Section 4；
- 不修改 Figure 2；
- 不新增结果或文献主张；
- 不使用 `first`、`only`、SOTA 或因果措辞。

## 16. 修改后的回归检查

若作者批准最小表达增强，必须执行：

1. **硬事实回归：** 对照 3.1–3.4 final audits，确认所有公式、输入权限和接口定义未变；
2. **Claim–evidence 回归：** 逐句核对 Abstract、Introduction、Conclusion 是否仍仅由 Q1–Q3 支持；
3. **范围回归：** 搜索 causal、counterfactual、composition、non-collapse、extreme-specific、SOTA、first、only；
4. **术语回归：** 检查 Section 3、captions、Section 4 和中文镜像；
5. **双语回归：** 英文限定词 `under the frozen protocol`、`supports`、`matched` 不得在中文中丢失；
6. **版面回归：** 重新编译并确认页数、浮动体、underfull/overfull、引用和 Figure 3 不回退；
7. **Section 4 审计后回归：** 再判断 Q3 的 detectability statistic、donor 定义和 provenance 说明是否需要全篇统一。

## 17. 最终判断

### 是否可以在保持硬冻结的情况下增强表达？

**可以。** 所有 P1/P2 建议都只调整段首、段尾、过渡或范围限定，不触碰方法设计、公式、结果或证据边界。

### 可以直接加入的句子

可在作者批准后直接使用：

- 本报告第 2 节的一句话核心贡献；
- P1-4 的 Q3 预告；
- P1-5 的 3.3 目的句；
- P1-6 的 3.4 bridge；
- P2-2、P2-3、P2-4 的 Section 3 段尾句。

### 必须等待 Section 4 审计后再定的内容

- detectability statistic 的精确名称与报告尺度；
- Q3 raw JSON provenance 的最终复现说明；
- matched donor 首次定义应放在 Method、caption 还是 Section 4；
- 全篇对 “selected/frozen model” 的复现措辞；
- 图表与表格最终占页后，哪些限制需要压缩。

### 是否存在当前过度主张？

**没有与冻结结果直接冲突的强过度主张，但存在三处轻微范围过宽：**

1. Abstract 的 “selected almost entirely” 对现有工作概括过强；
2. Related Work 的 “These works primarily establish...” 可能低估个别天气响应分析；
3. Conclusion 的联合 world-model 结论未显式加 `under the frozen protocol/in this setting`。

此外，Introduction 的 `correct predictive direction` 容易被误读为物理或因果正确，应改为证据实际支持的 `forecast-window fidelity`。这些均属于 P1/P2 级范围校准，不构成论文主线或证据失效。

## 18. 最终状态

`POSITIONING_NEEDS_MINOR_LIFT`

`METHOD_FACTS_AND_EVIDENCE_BOUNDARIES_REMAIN_FROZEN`

`MINIMAL_EXPRESSION_ENHANCEMENT_IS_SAFE`

当前 Section 3 已经是一个成立的方法闭环。下一步若执行表达增强，应坚持“少量、局部、可回归”，而不是重新寻找主线或重写方法。
