# TerraState AAAI-27 逐节收敛路线

> 状态：ACTIVE  
> 英文唯一事实源：`paper/main.tex`  
> 建立日期：2026-07-27  
> 目的：避免无边界的整篇重写，以可复核、可回退的方式逐节完成 AAAI 投稿稿。

## 1. 不可越过的边界

1. 不修改标题、TerraState 单模型定位和
   \(q\rightarrow z_t\rightarrow T_\psi\rightarrow z_{t+h}
   \rightarrow O_\omega\) 主线。
2. 不修改训练、评测代码、checkpoint、实验输出或历史记录。
3. 不推测或美化实验数字；所有结果必须来自冻结证据。
4. Q1 是预测能力，Q2 是状态贡献，Q3 是天气响应；三者不能相互替代。
5. Q4/composition 只作为可选训练后分析，不进入核心贡献。
6. 论文是一个可检验预测状态的世界模型，不是 benchmark 或模型审计工具。
7. 英文修改以 `paper/main.tex` 为准，并同步
   `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md` 和完整中文审阅稿。
8. Figure 1--3 必须有明确的正文插入位置，但未批准或数据不足的图不以
   TBD/空框形式出现在 PDF 中。

## 2. 固定的逐节闭环

每次只收敛一个章节，并依次完成以下八步。

### Step 1：建立本节事实基线

- 提取当前英文、中文和历史版本；
- 标出冻结句、证据支持句、越界句和仅属实现记录的句子；
- 核对本节引用的公式、表格、图和实验字段。

### Step 2：调研一手写作锚点

- 至少核验 4 篇相关 AAAI 正式论文；
- 优先选择方法类型和章节任务相近的论文；
- 只总结信息顺序、段落角色和主张粒度，不模仿具体措辞；
- 记录论文、官方链接、对应章节和可借鉴原则。

这是每一章节的强制前置门槛，而不是全稿开始时只做一次的通用调研。摘要、引言、
相关工作、方法、实验、局限与结论均须分别建立对应的文献写作记录；未完成本节
调研和“外部规律 → TerraState 写法”映射时，不允许进入本节正文修改。

### Step 3：冻结本节职责

回答三个问题：

1. 本节必须让审稿人知道什么？
2. 哪些信息应由前一节或后一节承担？
3. 本节结束时审稿人应自然产生什么下一个问题？

### Step 4：建立 claim--evidence 映射

每个主要句子标记为：

- `SUPPORTED`：有当前冻结证据；
- `QUALIFIED`：有证据但必须附带范围；
- `BACKGROUND`：由已核验文献支持；
- `METHOD FACT`：由代码/配置事实支持；
- `UNSUPPORTED`：删除或降级；
- `AUTHOR DECISION`：需要作者确认。

### Step 5：先设计信息槽，再写句子

- 每段只承担一个核心信息；
- 首句说明本段功能；
- 句子按“已知事实 → 缺口/机制 → 对 TerraState 的意义”推进；
- 不先做同义词润色，不使用空泛的 superior、novel、significant。

### Step 6：英文修订与中文同步

- 英文先进入权威稿；
- 中文使用自然解释，但保持章节顺序、符号、数字和主张强度；
- Markdown 镜像不得形成第二套事实源；
- 统一 predictive state、state readout、context-only forecast、
  weather-conditioned transition 等术语。

### Step 7：双重复审

第一轮检查本节自身：

- 信息是否完整；
- 方法身份是否清楚；
- 证据是否越界；
- 是否存在工程日志语言或 AI 式空话。

第二轮检查跨节关系：

- 是否重复前文；
- 是否提前泄露后文职责；
- 与标题、摘要及前面已冻结章节是否像同一篇论文；
- 图表首次引用是否在合理位置。

### Step 8：编译与状态记录

- 使用项目内 TeX Live 编译；
- 检查 citation/reference、overfull/underfull、页数和浮动体；
- 更新本文件的阶段状态；
- 只有本节闭环通过后才进入下一节。

## 3. 各章节职责

| 章节 | 必须完成的任务 | 不应承担的任务 |
|---|---|---|
| Abstract | 背景、缺口、世界模型身份、核心机制、单句证据总结 | 连续结果句、详细统计协议、局限清单 |
| Introduction | 应用价值、结构性缺口、操作性世界模型定义、TerraState 解法、简短证据和贡献 | 置信区间细节、完整结果复述 |
| Related Work | 建立研究边界，解释与最近工作的机制差异 | 文献名单、实现细节、结果宣告 |
| Problem Definition | 定义输入、预测目标、状态和可检验问题 | 训练课程和结果 |
| Method | 解释 \(q\)、\(T\)、\(O\)、预测闭合、训练目标及可验证性质 | 声称 Q1--Q3 已通过 |
| Experiments | 数据、比较口径、选模、指标和 Q1--Q3 协议 | 重复引言动机 |
| Results | 按 Q1--Q3 回答问题，严格区分统计量 | 新方法、新评价目标 |
| Limitations | 说明证据边界和外推限制 | 否定已经支持的核心结果 |
| Conclusion | 回答研究问题并总结已支持结论 | 新数字、新实验或更强主张 |

## 4. 世界模型的操作性定义

全文采用同一逻辑：

> TerraState is a world model in the operational sense that it infers a
> predictive state from partial observation histories, advances that state
> under exogenous future weather with a shared transition, and maps the
> advanced state back to an observable forecast. Its state and transition
> remain on the prediction path and can therefore be tested by matched
> interventions on the same model.

中文解释：

> TerraState 的世界模型身份来自一个完整的“观测—状态—动力学—可观测预测”
> 闭环：它从部分历史观测推断预测状态，在外生未来天气的条件下用共享转移推进
> 状态，再把未来状态映射回地表预测。状态与转移真实位于预测路径中，因此可以在
> 同一个模型上通过匹配干预检验。

该定义不等同于完整物理状态、因果模拟器或数字孪生。

## 5. Figure 1--3 的正文接口

- **Figure 1：问题/方法总览。** 位于 Introduction 首次给出 TerraState 解法后，
  Method 之前或开头。
- **Figure 2：模型结构与干预位置。** 位于 Method 的 state/weather intervention
  定义附近，或 Experiments 的 Questions and Protocol 之后。
- **Figure 3：行为证据。** 位于 Q2/Q3 Results 附近，只在真实数据和统计口径
  完全对齐时接入。

若图稿未批准，只在 LaTeX 源中保留注释式插入点，不显示空白框、不产生未定义引用。

## 6. 阶段状态

| 阶段 | 状态 | 退出条件 |
|---|---|---|
| 权威版本与冻结项基线 | COMPLETE | 当前稿、提交稿、证据和状态文件已定位；图稿状态冲突已记录待后续处理 |
| Abstract | AUDIT COMPLETE / AUTHOR GATE | 作者批准建议摘要后同步权威稿 |
| Introduction | COMPLETE | 世界模型定义前置、结果粒度合理；双语同步并通过编译 |
| Related Work | COMPLETE | 已按“EO 预测 → EO 世界模型 → 预测状态/潜变量动力学”建立边界；双语同步、引用零冗余并通过编译 |
| Problem Definition + Method | COMPLETE | 总公式与图同构；模块按“目的—机制—可验证性质”展开；实现细节下沉且双语编译通过 |
| Experiments + Results | COMPLETE | 实验问题、实际主指标与统计单位分层；Q1--Q3 数值和 estimand 与证据工作区一致 |
| Limitations + Conclusion | COMPLETE | Q1--Q3 强度、hot-dry null、一次训练与外推边界均已对齐 |
| Figure 1--3 正文接口 | COMPLETE | 正式稿只显示已批准 Figure 1；Figure 2/3 具有不可见、无悬空引用的合法插入点，旧 Revision 2 不再被误标为待接入 |
| 全稿复审与编译 | COMPLETE WITH GATES | 双语、引用、格式、版面已通过；只剩摘要作者门、真实图源/图稿批准与 checklist |

## 7. 摘要专用作者门

摘要关系到已上传 registration 文本，采用额外保护：

1. 先保存“提交版—当前版—建议版—修改原因”；
2. 建议版最多一个结果句；
3. 优先保留提交版的背景、缺口和方法句；
4. 只删除已被最终合同否定的旧主张；
5. 未经作者确认，不覆盖 `paper/main.tex` 中的摘要。
