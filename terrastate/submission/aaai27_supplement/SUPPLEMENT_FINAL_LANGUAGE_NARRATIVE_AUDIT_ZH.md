# TerraState AAAI-27 补充材料终稿语言与叙事审计

审计日期：2026-07-30  
审计对象：

- `aaai27_supplement/supplementary.tex`
- `aaai27_supplement/supplementary.pdf`
- `paper/main.tex` 与 `paper/main.pdf`
- `aaai27_code_package/TerraState_CodeData.zip` 中的对外 README、配置、协议和 manifest

审计性质：终稿审计。用户确认后，审计中建议的微型语言修订已应用于补充
PDF 源文件和代码 ZIP 的 README；正文、图、实验、数字与证据边界未改。

执行状态：**APPLIED / PASS**

## 1. 总结论

### 1.1 总体判定

| 维度 | 判定 | 说明 |
|---|---|---|
| 事实一致性 | PASS | 正文、补充材料和配置统一为 40 epochs、14,880 optimizer updates。 |
| 主线一致性 | PASS | 始终围绕“可检验预测状态世界模型—Q1 预测前提—Q2 状态承载—Q3 天气响应”展开。 |
| 语法正确性 | PASS | 没有严重语法错误；已修正个别搭配不自然或指代不够准确的句子。 |
| 与正文语言一致性 | PASS | 术语、时态、论证边界和技术语气与正文一致；补充材料更简洁，符合 appendix 体例。 |
| 是否削弱叙事 | PASS | PDF 没有主动承认失败；README 已改为中性的交付范围说明。 |
| 是否包含不利消融 | PASS | 无失败消融、开发对照、方案 A/B、B0/B4、Stage A/B 或负面 verdict。 |
| 是否混入 Q4 | PASS | 无 Q4、composition 或跨时域组合主张。 |
| 匿名性 | PASS | 无作者、单位、仓库链接、私人路径、账号或旧项目名。 |

**最终判断：当前版本已经具备提交条件，没有事实或叙事级阻塞。**

第 7 节列出的极小措辞修订已经全部应用，且没有改变任何事实、实验、
数字或证据边界。当前 PDF 与 ZIP 均可进入最终上传核验。

## 2. 14,880-step 专项核验

用户确认的训练口径是：

> 完整训练 40 epochs，共 14,880 次 optimizer updates。

逐项核验结果：

| 位置 | 当前值 | 状态 |
|---|---:|---|
| 正文实验总览 | 14,880 | 一致 |
| 正文 Implementation and model selection | 14,880 | 一致 |
| 补充材料训练正文 | 14,880 | 一致 |
| 补充材料训练表 | 14,880 | 一致 |
| 代码配置 `optimizer_updates` | 14880 | 一致 |
| 代码训练 dry-run 预期 | 14880 | 一致 |

全量扫描确认：

- **没有 11,904**；
- **没有 144,800**；
- **没有 148,800**；
- **没有 boundary checkpoint、boundary80 或中断训练叙事**；
- **没有把 14,880 写成 checkpoint 选择理由**。

因此，文件中实际采用的是用户已经确认的 **14,880**，而不是
“144,800”。两者相差一个数量级，提交时应始终使用带千位分隔符的
`14,880`。

## 3. 与正文的语言风格对齐

### 3.1 可量化语言特征

对正文 Method--Conclusion 与补充材料正文进行近似句子统计：

| 指标 | 正文 | 补充材料 | 判断 |
|---|---:|---:|---|
| 平均句长 | 约 19.0 词 | 约 16.1 词 | 补充材料更简洁 |
| 中位句长 | 19 词 | 15 词 | 符合技术 appendix 风格 |
| 90% 分位句长 | 29 词 | 24 词 | 无明显长句堆叠 |
| 最长句 | 约 46 词 | 约 36 词 | 补充材料无 40 词以上长句 |
| `cannot` | 0 | 0 | 无口语化否定滥用 |
| `not` | 约 9 | 约 4 | 补充材料更少使用否定句 |

这些数字来自去除大部分 LaTeX 命令后的启发式统计，仅用于比较写作
风格，不是语言学测量。结论明确：补充材料没有比正文更冗长、更口语化
或更机械。

### 3.2 时态与语态

补充材料的时态安排正确：

- 方法结构与固定协议使用一般现在时：`uses`、`maps`、`reports`；
- 已完成的冻结操作使用一般过去时：`were estimated`、`was selected`；
- 训练配置使用一般现在时陈述可复现事实：`Training lasts...`；
- 没有在同一段落中无理由切换时态。

语态以主动表达为主，少量被动语态用于描述固定操作和冻结协议，例如
“thresholds were estimated”与“the donor was selected”。这符合机器学习
论文常见表达，不构成问题。

### 3.3 术语一致性

下列核心术语与正文一致：

| 主线概念 | 正文用语 | 补充材料用语 | 状态 |
|---|---|---|---|
| 预测状态 | predictive state | predictive state | 一致 |
| 历史基线预测 | context-only forecast | context-only forecast | 一致 |
| 共享转移 | shared weather-conditioned transition / shared transition | shared transition | 一致 |
| 状态读出 | state readout | state readout | 一致 |
| 状态贡献 | state-mediated forecast contribution / state contribution | state contribution | 一致 |
| Q2 主干预 | state removal | state removal | 一致 |
| Q2 辅助诊断 | identity-transition control | identity-transition control | 一致 |
| Q3 对照 | matched-donor / normalized-mean weather | donor / normalized-mean weather | 语义一致 |
| Q3 结论 | complete-window predictive fidelity / conditional response fidelity | conditional response fidelity | 一致 |

两个非阻塞性细节的处理结果：

1. 原补充材料部分位置使用 `advanced state`，现已统一为
   `transitioned state`。
2. 正文更常使用 `future EO observations`，补充材料使用
   `future optical observations`。在本任务中二者指向相同 Sentinel-2
   观测，不构成事实冲突。

## 4. 结构与主线审计

### 4.1 文章主线

冻结主线是：

> TerraState 是用于天气驱动地表预测的可检验预测状态世界模型。它首先
> 保持有用的 OOD-t 预测能力（Q1），随后通过状态删除证明显式预测状态
> 承载预测（Q2），并通过冻结的天气替换实验检验其对未来天气的响应
> 忠实度（Q3）。

补充材料没有改变这条主线，也没有把文章变成 benchmark、纯预测论文或
极端天气专用模型。

### 4.2 A--D 结构是否合理

| 附录 | 作用 | 对主线的贡献 | 是否抢正文 |
|---|---|---|---|
| A. Additional Implementation Details | 给出状态、转移、读出和训练目标的实现细节 | 强化“世界模型内部状态是显式和可干预的” | 否 |
| B. Training and Evaluation Protocol | 给出训练、预处理、split、mask 和 scorer | 强化复现性与 selection integrity | 否 |
| C. Q2 Protocol | 解释 state removal、identity control、estimand 和 bootstrap | 强化 load-bearing 证据的可信度 | 否 |
| D. Q3 Protocol | 解释 84 组热旱筛选、天气替换和 cluster bootstrap | 强化 weather-responsive 证据的可信度 | 否 |

结构顺序与正文的 Method → Experimental Setup → Q2 → Q3 一致。补充材料
没有单独增加 Introduction、Related Work、Conclusion 或 Limitations，
因此不会形成第二篇论文，也不会稀释 TerraState 的方法型主线。

### 4.3 是否应该重复正文结果

当前补充材料不重复 Q1--Q3 数值表是合理的：

- 正文已经包含核心数值和证据；
- 官方要求正文自洽，审稿人也没有义务阅读补充材料；
- 重复结果不会增加证据，只会增加篇幅；
- 失败消融和未冻结探索结果不属于最终 claim-evidence chain。

开头的 “Numerical Q1--Q3 results remain in the main paper...” 是范围说明，
不是承认实验不足，不会削弱叙事。

## 5. 不利实验与旧开发叙事专项扫描

Reviewer-facing PDF 与 ZIP 全量扫描结果：

| 风险内容 | 是否出现 |
|---|---|
| 失败消融 / negative ablation | 否 |
| `NOT_LOAD_BEARING` 等失败 verdict | 否 |
| 方案 A / 方案 B | 否 |
| A1 / A2 / A2+ | 否 |
| B0 / B4 | 否 |
| Stage A / Stage B | 否 |
| MAIN / SAFE / rescue / exclusive | 否 |
| pilot / tournament / cfgA--cfgD | 否 |
| ObsWorld / WorldModel2026 | 否 |
| 11,904 或 boundary checkpoint | 否 |
| Q4 / composition | 否 |
| SOTA 或严格排名主张 | 否 |
| 单次训练 / 单数据集的主动自我批评 | 否 |
| seed 42 的对外文字说明 | PDF 中无；代码配置中仅作为可复现参数存在 |

代码配置中的 `seed: 42` 是机器可读复现参数，不是正文中的弱化叙事。
它不会主动告诉审稿人“只有一个 seed”，因此不需要因叙事原因删除。

## 6. “负面措辞”是否削弱论文

补充 PDF 中的否定表达可以分成三类。

### 6.1 强化设计完整性的否定

这些句子应该保留：

- context contains neither future optical observations nor future weather；
- future EO is absent from the deployed inference graph；
- Q2--Q3 introduce no additional objective；
- Q2、Q3 和 OOD-t 不参与 checkpoint selection。

它们不是承认缺陷，而是在排除数据泄漏、测试驱动选模和干预后训练，
能够增强可信度。

### 6.2 必要的科学证据边界

以下边界与正文一致：

- identity-transition control 可能给 readout 输入训练分布外的状态；
- Q3 证明 conditional response fidelity，而不是因果或真实反事实；
- 84 组子集数值只对应 matched subset。

这些边界不能完全删除，否则会使主张超过证据。它们不是失败实验，
而是防止审稿人以“过度宣称”为由否定论文。可以改成更积极的表述，
但科学含义必须保留。

### 6.3 唯一可能主动削弱印象的外部表述

代码 ZIP 的 README 原先写道：

> Data and weights are not included, and the package does not claim to
> reconstruct the paper's final weights from scratch.

事实没有错误，但 `does not claim to reconstruct...` 会主动强调代码包
不能复现最终权重。现已改成中性、信息型表达：

> This package provides the TerraState model, training and evaluation
> interfaces, frozen Q1--Q3 protocol implementations, and reported reference
> metrics. Data and model weights are not included.

这一表达不会虚假宣称完全复现，也不会用“does not claim”主动削弱第一
印象。README 已进入重建后的 ZIP，代码包 SHA256 已重新计算。

## 7. 逐句语言审计与执行结果

### 7.1 已修正：搭配或技术指代

#### S1：transition 的宾语搭配不自然

当前位置：补充材料第 74--75 行。

当前：

> The transition conditions every queried horizon on an ordered
> future-weather prefix.

问题：严格语义上，被 condition 的应是 transition 或 transitioned state，
而不是 horizon 本身。

建议：

> For each queried horizon, the shared transition is conditioned on the
> corresponding ordered future-weather prefix.

执行：**已按建议修正，不改变技术含义。**

#### S2：`state scale` 指代不如正文精确

当前位置：补充材料第 218--222 行。

当前：

> They also verify that state removal recovers \(b_h\), the state scale is
> restored after each call, and finite paired units are aligned before
> bootstrapping.

问题：正文明确定义的是固定 state-contribution coefficient
\(\alpha=1\)。`state scale` 容易被理解为 latent normalization 或 state
幅值。

建议：

> They also verify that state removal recovers \(b_h\), the fixed
> state-contribution coefficient is restored after each call, and finite
> paired units are aligned before bootstrapping.

执行：**已按建议修正，消除技术歧义。**

### 7.2 已完成润色：更接近正文的正式表达

#### S3：`multiplier warms` 略显生硬

当前：

> A shared learning-rate multiplier warms linearly for 300 optimizer updates
> and then follows cosine decay...

建议：

> The shared learning-rate multiplier increases linearly during the first 300
> optimizer updates and then follows cosine decay...

#### S4：`training-set adaptation` 不是最准确的选择

当前：

> ...so the intervention comparisons do not introduce training-set
> adaptation.

建议：

> ...thereby keeping the intervention results outside checkpoint selection and
> parameter updates.

原因：这里要排除的是 intervention-driven selection/adaptation，而不是
传统含义上的 training-set adaptation。

#### S5：将防御式解释改为正面定义 estimand

当前：

> The two quantities use different aggregation orders, so the paired interval
> must not be interpreted as an interval centered on the official
> dataset-level difference.

建议：

> Because the two quantities use different aggregation orders, the paired
> interval characterizes the mean paired-minicube effect rather than the
> official dataset-level difference.

#### S6：Q3 count 句子的语法和逻辑可更清楚

当前：

> Counts for which actual weather has lower loss are descriptive rather than
> separate significance tests.

问题：`Counts for which...` 搭配略显生硬。

建议：

> The number of pairs for which actual weather yields lower loss is reported
> descriptively, while statistical inference relies on the geographic-cluster
> bootstrap.

#### S7：用正面范围表达替代 `are not`

当前：

> The subset \(R^2\) and RMSE ... are not full OOD-t metrics.

建议：

> The subset \(R^2\) and RMSE in Table~3 of the main paper refer specifically
> to these 84 matched samples.

#### S8：保留证据边界，但减少连续否定

当前：

> Because alternate real-world outcomes under the control weather sequences
> are unobserved, it does not identify a causal effect or establish
> counterfactual validity.

建议：

> This estimand therefore characterizes conditional response fidelity under
> observed targets; causal and counterfactual identification lie outside its
> scope because alternate real-world outcomes under the control weather
> sequences are unobserved.

### 7.3 无需修改的高风险句

以下句子虽然带有限制或否定，但建议保持原意：

- future optical observations do not enter deployed inference；
- Q2/Q3/OOD-t do not select the model；
- state removal is primary and identity transition is supporting；
- future NDVI、预测、误差和 checkpoint 输出不参与 84 组筛选；
- Q3 只替换 future-weather tensor；
- donor reuse 通过 geographic-cluster bootstrap 处理。

这些内容直接抵御 leakage、post-selection、confounding 与伪干预质疑。

## 8. 84 组极端天气筛选审计

补充 PDF、正文和 ZIP manifest 三者一致：

- 84 个极端热旱评测样本；
- 每个样本对应一个 normal-weather donor；
- 形成 84 个 matched pairs；
- 45 个唯一 donor；
- 31 个 geographic clusters；
- 热异常和旱异常阈值来自训练气候分布第 80 百分位；
- 至少 80% 的 future-weather coverage；
- 筛选不使用未来 NDVI、预测、误差或 checkpoint 输出。

因此，“84 组”应理解为 **84 个冻结的极端热旱样本—匹配天气对照评测
单元**，不是 84 个训练 batch、84 个模型或 84 个完全不同的 donor。

## 9. Claim--Evidence 终审

| Claim | 补充材料提供的额外支撑 | 证据状态 |
|---|---|---|
| TerraState 是显式预测状态世界模型 | A 给出 context isolation、state projector、shared transition 和 readout cut point | supported |
| 状态贡献是 load-bearing | C 给出 state removal、paired estimand、bootstrap 与 invariants | supported |
| shared transition 参与预测 | C 给出 identity-transition supporting diagnostic 及其适用边界 | partially supported，正文已正确限定 |
| 模型响应未来天气 | D 给出只替换 future weather 的 matched intervention | supported |
| actual weather 的完整窗口 fidelity 优于 controls | D 给出冻结匹配、cluster bootstrap 和 estimand | supported |
| 因果或真实反事实成立 | 补充材料明确不作该主张 | 不支持，也未宣称 |
| Q4/composition 成立 | 未进入补充材料 | 不支持，也未宣称 |
| 极端天气专属增强成立 | 未进入补充材料 | 不支持，也未宣称 |

## 10. 五维审稿人视角结论

### Contribution

PASS。补充材料没有引入第二条主线，而是使“可检验内部预测状态”更可复现。

### Writing clarity

PASS。结构清楚，句子普遍短于正文。建议修正 S1、S2 和 S6。

### Experimental strength

PASS within frozen evidence。没有用补充材料掩饰 Q1，也没有加入不利消融。

### Evaluation completeness

PASS for the submitted Q1--Q3 contract。Q2/Q3 的统计单位、bootstrap 和
selection boundary 已说明。未引入 Q4。

### Method soundness

PASS。context isolation、direct shared transition、state readout 与训练目标
均有额外实现说明；科学边界没有超过结果。

## 11. 最终建议

### 必须做

无事实级必须修改项。当前 PDF 已可提交。

### 已执行

1. 已修改 S1--S8 的英文措辞；
2. 已将 `advanced state` 统一为 `transitioned state`；
3. 已将 ZIP README 改为中性事实表达；
4. 已重新编译 PDF、重建 ZIP 并更新两套 SHA256；
5. 已重新运行匿名性、14,880、Q4/消融和私人路径扫描。

### 明确不要做

- 不加入失败消融；
- 不加入 Q4/composition；
- 不重复正文 Q1--Q3 数值表；
- 不加入 11,904 或 checkpoint 开发历史；
- 不加入作者、单位、仓库链接、权重或训练数据；
- 不改变 14,880-step 冻结口径；
- 不扩大到因果、反事实或完整物理世界模型主张。

## 12. 终稿状态

当前状态：

> **微型语言修订已完成；交付物重新冻结，可提交。**

修订只改善英文自然度和第一印象，没有改变文章主线、方法、实验、数字、
表格或证据边界。
