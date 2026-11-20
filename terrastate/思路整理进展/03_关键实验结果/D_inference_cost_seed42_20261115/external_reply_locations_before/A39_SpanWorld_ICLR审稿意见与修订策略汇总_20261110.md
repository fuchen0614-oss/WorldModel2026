# SpanWorld｜ICLR 审稿意见与修订策略汇总

> 最新主线：2026-11-15用户已确定D为后续主模型；旧“待B/D选型”状态失效。D最终结果验收仍待逐项完成，详见文末锁定记录。

整理日期：2026-11-10。本文汇总本轮讨论已接受或临时锁定的策略，供后续修改论文、安排补充实验和撰写回复使用；不表示实验已经完成，也不是正式提交的 rebuttal。

2026-11-11 更新：2.3 与 3.1 的 Deep-OSG／LISG 回应采用 A42 专项方案；本次仅更新策略文档，未修改论文正文、代码或实验。该项回应路线已锁定，不代表审稿人的创新性质疑已获得认可或消除。

按本次讨论顺序分类：第一位为 3 分（Weak acceptance），第二位为 2 分（Weak rejection），第三位为 1 分（Clear rejection），与 OpenReview 按时间排序的显示顺序不同。每项保留英文原文、中文翻译、策略总写及一段具体策略；相似问题交叉引用，不重复安排实验。

论文依据为实际提交的 PDF，对应本地 v16 PDF／v23 中英双语稿，不以 v17 为依据。项目继续定位为遥感世界模型。本文采用本轮最后确认的范围；此前讨论过但未接受的额外实验，不自动纳入执行。

## 后续推进主线（2026-11-14用户明确锁定）

当前停靠点：已确认且不依赖新结果的内容完成本轮双语MD落稿；等待用户回来确认最终模型、提供结果或指定下一项。不因等待自行改稿、监测训练或重开已锁定问题。

1. 确认最终模型及结果身份：核对配置、训练预算、种子、checkpoint、评价协议，先不改结论。
2. 核心续预测：验收C1/C0R至少三个配对种子，再更新表1、相关附录及回复，重新核对收益与种子波动。
3. 标准精度与外部比较：验收最终模型四分区结果，再更新标准表、必要正文概述及回复，如实交代与强基线、EO-WM的关系。
4. 补充证据：按已锁定方案验收一致性对照、组件消融、状态分析、推理成本及新版天气评估，再更新各自位置。第2—4项可按结果到达顺序处理，不混用不同模型、配置或预算。
5. 全文与回复审计：核对模型、数值、主张与图表；按每位审稿人审计回复重复，先提供原问/翻译、原回复、具体拟删改和完整新回复，用户确认后执行。
6. 双语稿确认后再合入修订LaTeX；重新核对当年官方规范，编译检查页数、引用、匿名、图表及可关闭蓝色标记。正文9页向10页为目标，以官方规范和必要内容为准，不为凑页扩写。

每项涉及新结果解释或新文案，先提供原问及翻译、已锁定策略、实际证据、判断、具体位置与原文/候选文案、完整回复；用户确认后落稿。已明确批准的内容直接执行；科学主张变化、实现矛盾或新增实验决策必须先讨论。

只改writing/SpanWorld后续审稿修改工作副本，原v16/v23不动；A39维护策略和具体修改，A49维护逐条中英回复。不得因润色重写摘要/引言及无关段落，不重画框架图，不将只回复的问题重新扩成正文，不增加训练任务/接管调度/修改模型代码，不提前声称结果或显著性，不上传OpenReview或提交评论。结果图按既定样本选择规则更新。

临时问题单独讨论，默认不改变主线、不自动落稿；用户明确接受后再更新策略。用户说回归主线时，报告当前步骤、已完成、等待事项及下一具体动作。后续无新结果或明确指令，不擅自继续改论文。

## 2026-11-14 已确认修改落稿对账（以本节及各题最新状态为准）

| 问题 | 已落实位置/处理 | 仍待事项 |
|---|---|---|
| 1.1、1.2、1.3 | 多种子、简单替代、成本方案已锁定；不提前填结果 | 新结果验收及表图/回复 |
| 2.1 | §3.1、附录A.1初始化连接与公式、基础预测称谓、图注已改 | 最终配置和标准表现 |
| 2.2、3.4 | 精度与重训消融路线保留 | 最终模型/消融结果 |
| 2.3 | Deep-OSG相关工作与贡献2已改，公式保留 | 配对结果与最终回复完成态 |
| 2.4、3.1、3.2 | 已锁定独立回复，不额外增加正文用途段或重复论证 | 涉及新实验的结果段 |
| 3.3 | EO-WM相关工作/引用、§4.1指引、附录B说明/结果已落稿 | 新模型客观比较 |
| 3.5、3.6 | §4.1天气来源已改；预处理按回复解释不新增正文 | 最终配置一致性 |
| 3.7 | 状态分析等待验收，不写成完成 | 新证据 |
| 3.8 | §3.1 NDVI定位已落稿 | 最终全文核对 |
| 3.9、3.10 | 回复主体已归档；按决定不新增正文 | 新版天气证据/结果身份与结论核对 |
| 3.11 | §4.2及§4.4两处中英压缩已落稿；原问和中英回复在A49 | 最终稿同步；回复内部去重另行审计 |

本轮不启动训练，不自动更新多种子数字，不向论文增加新的科学承诺。后续先接收用户确认的结果/方案再推进；最终配置变化所需方法核对、统一LaTeX/PDF与回复内部去重仍未完成。

## 一、第一位审稿人：3 分，Weak acceptance

### 1.1 核心结果只有单种子和 IID，缺少稳定性与泛化证据

**问题原文**

> The central claim rests on a single seed and one split. The 11% continued-prediction improvement comes from one training run per model on the IID split. Stability across seeds and generalization to the OOD splits are not shown for this comparison.
>
> Can you report the core continued-prediction comparison (Table 1) over at least three seeds, with variability across seeds?

**中文翻译**

> 核心结论建立在单个随机种子和单个数据划分上。11% 的续预测改进来自两个模型在 IID 上各一次训练，尚未展示种子间稳定性或该比较在 OOD 划分上的泛化表现。
>
> 能否在至少三个随机种子上报告表 1 的核心续预测比较，并展示种子间的变化？

**策略总写：重点补齐表 1 的三个配对种子，复评直接预测与续预测；不把所有实验都扩展成多种子。**

在最终配置一致、原有种子可复用的前提下，为 SpanWorld 和直接终点监督控制模型各补两个种子，即新增四次训练，形成三个种子的配对比较。按相同规则复评表 1，汇总直接预测、续预测及其差异的跨种子均值和变异；使用相同权重补充 OOD 评估，不为 OOD 另行训练。若主模型公共配置已改变，则三个种子的配对结果须基于统一新配置，不能混用新旧模型。核心比较的多种子要求不扩展到后面的单项结构消融。

### 1.2 缺少一致性损失等简单替代方案

**问题原文**

> The control may not isolate the mechanism. The paper does not test simpler alternatives, such as a consistency loss on the same rollout paths or noise injection into intermediate states, that might produce the same effect.
>
> How does the partitioned-path control compare with simpler alternatives, such as training on the same rollout paths with only a consistency loss, or adding noise to intermediate states?

**中文翻译**

> 现有控制可能不足以辨别该机制的必要性。论文没有检验更简单的替代方案，例如在相同展开路径上使用一致性损失，或向中间状态注入噪声；这些方法也可能得到相同效果。
>
> 与这些简单替代方案相比，分段路径训练表现如何？

**策略总写：补一个单种子的一致性训练对照，复用现有路径与实现；不同时铺开噪声注入和多种替代训练。**

保留所有目标日期的直接真实观测监督，将额外的分段终点真实观测损失替换为分段预测与同日期直接预测之间的一致性损失，直接预测作为停止梯度的参考。通俗地说，原方法让分段结果对齐真实图像，替代方法让分段结果对齐直接预测。沿用相同架构、路径和公共训练设置，先做一个种子并按表 1 协议评价，不开展大规模权重搜索。若两者相近，如实说明简单一致性也能改善续预测，不强行声称真实终点监督独有优势。此对照回答简单替代方案问题，不等同于完整复现 Deep-OSG 的 LISG。

**本轮锁定落实：** A49已加入第一位3分审稿人本题独立完整中英回复。沿用已批准正文§4.4与附录I表I1A，不重复改稿。回复报告D、seed42、40轮后三条路径均最低的续预测MSE；15+35路径0.04174650对0.04311991，相对降低3.19%。解释一致性对照直接检验监督目标，明确未加入中间状态噪声对照，不宣称已排除所有替代机制。

### 1.3 缺少直接预测与分段预测的推理成本

**问题原文**

> Can you report inference cost for partitioned versus direct prediction?

**中文翻译**

> 能否报告分段预测与直接预测的推理成本？

**策略总写（用户锁定，已落实）：正文不改；附录H新增推理成本说明和表H2，回复直接指向表格。完整直接/分段过程、已有缓存后的续预测、准备成本分别列示；共享环境下只描述实测成本接近。**

**具体新增原文：**

**推理成本。** 我们比较直接与分段模式预测第55—100天目标的计算成本。分段模式先经15＋35天形成第50天状态，再从该固定状态查询后续目标。两种完整过程均包含历史状态、基础预测和天气条件的计算，并复用天气前缀编码、批量处理目标日期。已有状态及基础预测缓存后的续预测与相应准备成本分别报告。

**表H2：直接与分段预测的推理成本。** 使用SpanWorld的seed42验证集选定权重，在同一张共享RTX 4090上测试8个128×128的IID样本，批量大小为1，采用FP32。每个样本、每种模式预热3次并测量10次。报告耗时中位数［第25、75百分位数］和测量中的最大进程峰值已分配显存；不计磁盘读取及主机到GPU的数据传输。

|模式|中位数［P25，P75］，ms|峰值显存，MiB|
|---|---:|---:|
| 直接预测完整过程 / Direct, end-to-end | 122.44［86.84，124.73］ | 595.85 |
| 分段预测完整过程 / Partitioned, end-to-end | 122.15［87.62，124.85］ | 595.85 |
| 已有第50天状态及基础预测缓存后的续预测 / Continuation from an existing day-50 state and cached baseline predictions | 5.21［5.17，5.23］ | 174.73 |
| 第50天状态及缓存准备 / Day-50 state and cache preparation | 117.38［80.62，119.50］ | 595.85 |

在本次测量中，两种完整过程的耗时和峰值显存接近。缓存后续预测的耗时不包含准备成本，显存包含驻留缓存。

**状态：** 中英工作MD附录H与A49完整双语回复已同步；原稿、正文、表H1、LaTeX/PDF未改。恢复验收证据：`03_关键实验结果/D_inference_cost_seed42_20261115/recovered_data_acceptance.json`。原worker退出1与数据恢复验收区分，不能冒称原业务正常退出。

## 二、第二位审稿人：2 分，Weak rejection

### 2.1 正文抽象，架构与性能说明不足；世界模型及相对骨干的贡献不清楚

图注最新执行：用户批准后已将图2(a)中英图注的基础预测短语分别改为“基于历史观测及给定未来天气的基础预测”及“baseline predictions conditioned on historical observations and the supplied future weather”，标蓝；仅这两处短语，(b)及监督说明不变，原图不改。不另加“见§3.1”补丁句。此状态覆盖下文此前图注待审状态，LaTeX/PDF待同步。

2026-11-14命名一致性落实：用户批准将方法及后续实验、图注、附录中的“历史基准预测/历史基准”称谓改为“基础预测”，history-derived/historical baseline改为baseline，局部词组标蓝；摘要/引言保持，公式和数值未变。仅名称调整，不改干预归因。实际只读查看v16 figure2_architecture.png：图内使用Base Forecasts / Base Forecast，无历史限定；未画出未来天气进入基础预测分支的连接，概览存在输入省略，不能称图已经完整展示新版依赖。原图不改；图注已按后续批准版本局部改为“基于历史观测及给定未来天气的基础预测”，英文对应明确同一依赖，不另加§3.1指引。图片、LaTeX/PDF未修改。天气替换是否同时改变基础预测分支继续待最终评估协议核对，不凭名称调整宣称解决。

**问题原文**

> The writing is overly abstract, while key architectural details and comparisons with baselines are deferred to the appendix, making the main text insufficiently informative. These should be summarized in the main text to clarify the method and its performance.
>
> What distinguishes SpanWorld as a world model from a conventional vegetation forecasting model? Beyond this terminology, could you clarify the specific architectural and training contributions introduced over Contextformer?

**中文翻译**

> 写作过于抽象，关键架构细节和基线比较被放到附录，正文不足以清楚说明方法与性能，应在正文进行概括。
>
> SpanWorld 作为世界模型与传统植被预测模型有什么区别？除了术语，能否说明相对于 Contextformer 的具体架构和训练贡献？

**策略总写（2026-11-13更新）：以“具体状态复用能力—科学问题—训练路径—受控验证”回答2.1；正文只做必要连接与新版事实纠正，不写答辩式骨干比较段。**

**表达约束：**正文与回复不使用“SpanWorld采用／基于Contextformer的预测骨干”及同义措辞。必要时直接说明PVT空间编码、时间Transformer等结构，回复采用“与Contextformer的区别在于……”的直接比较。现有真实来源引用和必要的附录来源/权重说明保留，不隐瞒实际复用关系；不将复用模块说成原创。该约束不改写审稿人原话。

**回复主线：**SpanWorld显式形成可反复参与共享天气条件变跨度转移的空间状态，以后续真实卫星观测检验生成状态的预测价值；完整输出仍包含基础预测。科学问题沿用引言原句：当训练已监督从同一初始状态直接预测全部未来日期时，这是否足以使分段形成的状态支持准确后续预测？“全日期已监督，监督路径是否仍影响续预测”是同一问题的实验化表述，不修改研究目标。以全日期直接监督、分段端点监督、匹配C0R解释训练与验证，重点突出故事与受控证据。

**具体措施：**§3.1仅在必要处补空间/时间处理与初态来源的连接；纠正新版基础预测使用给定未来天气、初态计算屏蔽未来天气/未来影像而保留已知日期特征的输入边界，并同步初始化公式；附录A.1修正“单次前向同时产生二者、二者均不用未来天气”的旧说明。原本清楚的GRU、状态传递、读出相加不重复修改；不新增骨干比较正文段，不重写方法开头或贡献列表，不改框架图。AdaLN不是本项正文重点，最终实际采用时只作必要实现说明，不能保留不符合计算过程的旧句。具体公式符号与最终英文落稿另行确认，不把实现变化全部称为文字澄清。

**性能部分：**新结果验收后正文简述标准表现与续预测表现，完整标准表保留附录；现在不填数字，不使用完成态。基线精度和续预测价值分别回答，不能以一个替代另一个。

**问题边界与状态：**不在2.1回复引入Deep-OSG／LISG争议，也不主动加入独立完整环境状态等额外辩护；这些由对应问题负责。架构/科学问题回复主体已锁定，正文修改完成说明和性能结论待补，2.1尚未全部关闭。正式问答汇总见[A49](<A49_SpanWorld_ICLR逐项审稿回复_中英锁定稿_20261113.md>)，不使用此前未认可的A45批量草稿。

#### 2.1 正文与附录具体修改单（2026-11-13；修改1—3已落双语MD）

此处保存可操作的原文对照，而非只列原则。后续各问题均按“位置—原文—替换/增补—理由—状态”维护；思路改变时直接改本节，不累积相互冲突的候选。原v16/v23永不改，先改双语工作MD，最终再合入LaTeX副本。以下保留已审核的具体对照；修改1—3及公式已按本节完成状态落稿，修改4—5继续等待最终配置与结果。

**修改1｜§3.1式(1)引导句及式后初始化段：区分基础预测与初始状态。**

原文定位：从“The history encoder $E_\phi$ maps ...”至式(1)后“The shared transition uses future weather ...”。该段之前的任务定义、历史输入定义保留；之后的转移段保留。

原文关键句：
> The history encoder $E_\phi$ maps $\mathcal H$ and $G$ to future baseline predictions $B_{1:n}$ and an initial dynamic state $S_0$:
>
> Here, $\phi$ denotes the encoder parameters, and $S_0$ is obtained by projecting features at the end of the history window. Both the baseline predictions $B_{1:n}$ and the initial state $S_0$ are formed without future weather. The baselines retain predictive information from past observations. The shared transition uses future weather to update the dynamic state, whose readout then contributes to the prediction.

建议引导句（中文）：模型采用PVT空间编码器和时间Transformer，分别计算基础预测与用于初始状态构建的历史特征。

建议引导句（英文）：The model uses a PVT spatial encoder and a temporal Transformer to compute the baseline forecast and the historical features for state initialization under their respective input conditions.

建议式后替换（中文）：基础预测使用历史观测与给定的未来天气。初始空间状态则通过屏蔽未来影像和未来天气的计算路径获得：将最后一个历史时刻的特征投影为$S_0$，同时保留已知日期特征。两条计算路径共享骨干参数。

建议式后替换（英文）：The baseline forecast uses historical observations and the supplied future weather. The initial spatial state is obtained through a computation with future imagery and future weather masked out: features at the final historical step are projected into $S_0$, while known calendar features are retained. The two computations share backbone parameters.

理由：旧版“基础预测与初态都不使用未来天气”不适用于当前full-base公共路线；这属于版本事实纠正。正文不展开两次调用/缓存/运行优化。读出相加已有专段，不在这里重复；必要来源引用沿用已有位置。

**修改2｜式(1)：同步修改依赖关系，保持编号，具体符号待确认。**

原式：$(B_{1:n},S_0)=E_\phi(\mathcal H,G)$。

候选表达（未单独锁定）：
$$
B_{1:n}=F_\phi(\mathcal H,G,W_{1:n},C),\qquad
S_0=P_\psi\!\left[H_\phi(\mathcal H,G,C)_{\mathrm{last}}\right].
$$

$C$为已知日期特征；$F_\phi$与$H_\phi$分别表示共享骨干在不同输入条件下的预测输出和特征输出，不是两套独立骨干；$P_\psi$为已有投影。采用前核对符号冲突和后续引用，不能将等价记号整理称为新机制。最终也可采用更简洁且正确的记号，但必须明确$B$读取未来天气、$S_0$不读取未来天气。

**修改3｜附录A.1第二段：仅替换新版不再成立的句子。**

保留该段已有来源说明，保留之后的图像patch掩膜规则及读出实现。拟替换以下三句：
> A single forward pass produces the baseline sequence $B_{1:n}$ and features for state initialization. During this pass, future image positions are masked and future weather is zeroed, so neither $B_{1:n}$ nor $S_0$ receives future weather. The actual future weather enters the subsequent state transitions separately.

中文替换：基础预测在给定未来天气的条件下计算。初态特征由同一骨干在屏蔽未来影像和未来天气的条件下计算，保留已知日期特征。每次状态转移另行接收对应区间的天气。

英文替换：The baseline forecast is computed with the supplied future weather. Features for state initialization are computed using the same backbone with future imagery and future weather masked out, while retaining known calendar features. Each state transition separately receives the weather for its corresponding interval.

理由：不再错误声称一次前向产生两者或二者均不读取天气。其余正确内容不动，不展开工程实现。

**修改4｜转移条件的一致性检查：待最终配置后局部处理，不扩写。**

核对已有“拼接条件与归一化状态进入MLP”的描述与最终选定实现是否一致；季节条件需要准确交代，AdaLN实际采用则在附录原段或规格表必要说明，不另写动机。未选定前不写死细节，不重画框架图。

**修改5｜§4.1标准表现概述：结果未验收，暂缓。**

位置：原句“Standard forecasting comparisons are provided in Appendix B.”附近，将其扩展成简短的实际性能概述并保留附录引用。须含实际比较对象、指标/划分及差异方向，并区分标准精度和匹配续预测。现在不预写胜负、不填旧数字，不用空泛“性能提高”代替验收值。中英具体句子等结果后一并确认。

**明确不改：**原引言科学问题、框架图、已清楚的GRU/分段状态传递/读出相加描述；不因2.1增加正文Contextformer比较段，不因本题重写方法开头或贡献列表。2.3如有独立调整，单独审核，不混入本题。

**完成状态：**用户授权后，修改1—3已写入 `writing/SpanWorld后续审稿修改/SpanWorld_中英双语_逐项修订工作稿.md` 的中英对应位置，新增内容标蓝；式(1)采用上列F/H/P表达，日期特征改用 $\mathcal C$ 以区分影像修正 $C_t^r$，并解释共享参数与投影。原v23哈希核对未变。修改4最终条件/规格表、修改5性能以及全文新版依赖表述仍待验收同步；LaTeX未改，不宣称整稿已完成。

### 2.2 标准预测精度落后于 Contextformer，改动的收益不足以解释精度损失

**问题原文**

> In the metrics reported in Appendix B.2, SpanWorld underperforms Contextformer 6M, whose architecture it adopts for its history encoder, in terms of forecasting metrics across all four splits.
>
> Why does SpanWorld underperform Contextformer 6M, as reported in Appendix B.2? What benefits do the proposed modifications provide that justify this loss in forecasting accuracy?

**中文翻译**

> 附录 B.2 显示，SpanWorld 在全部四个划分的预测指标上都落后于 Contextformer 6M，而它的历史编码器采用了后者的架构。
>
> 为什么会落后？所提出的改动带来了哪些收益，能够解释预测精度的损失？

**策略总写：先在原框架内优化训练与局部实现，并训练至 100 epoch 后统一复评；能缩小或消除差距最好，否则如实解释收益与代价。**

将季节／日期特征、天气统计与时间表示、天气对齐及 mask／缺测规则、原转移内的 AdaLN 天气调制，以及优化器、学习率、调度和损失权重列为候选优化方向，具体方案后续单独确定，不要求全部加入。用验证集选择配置，训练至 100 epoch 并按统一验证规则选取 checkpoint，在四个划分复评；公开权重是否同为 100 epoch 及其其他训练条件先核对，不仅凭 epoch 数声称预算完全公平。主模型与核心同架构对照采用相同公共改动。若仍存在标准精度差距，如实呈现并结合匹配对照说明续预测能力的收益，不把全部差距未经验证地归因于分段训练，也不声称精度提升自动解决方法创新问题。

**当前推进状态（2026-11-13）：用户确认2.2暂缓，等待最终配置与四划分结果验收，再写具体性能解释，不预设原因或结果。**

### 2.3 分段路径学习与 Deep-OSG 的方法重叠

**问题原文**

> Deep-OSG already includes a training formulation that supervises both direct and composed predictions using observed endpoint states. The paper should clarify the methodological novelty of partitioned-path learning beyond adapting this idea to weather-conditioned vegetation forecasting.
>
> How does partitioned-path learning differ from Deep-OSG’s training formulation that supervises both direct and composed predictions using observed endpoint states?

**中文翻译**

> Deep-OSG 已包含利用真实终点状态同时监督直接预测与组合预测的训练形式。论文应说明：除了将该思想应用于天气条件下的植被预测，分段路径学习还有哪些方法创新？
>
> 分段路径学习与这一训练形式具体有什么区别？

**策略总写（2026-11-13锁定）：**Related Work按已有研究→本文状态建模及训练→受控科学问题组织；准确交代Deep-OSG包含真实终点监督，但不写“共享原则”或引申为借鉴来源，不在正文展开LISG。回复直接比较自治系统演化算子与不完整观测下天气驱动潜在空间状态及影像监督，并说明匹配实验回答的问题。独立开展研究不能替代新颖性比较；不以“巧合/非抄袭”作答。

**修改1｜Related Work最后一段，已落双语MD并标蓝。**

原文（中文）：
> Deep-OSG进一步面向自治动力系统学习变时间步长的演化算子，研究直接与组合演化的半群一致性，并包含利用真实端点状态监督直接与组合预测的训练形式（Chen and Wu, 2023）。在此基础上，SpanWorld将天气驱动的共享变跨度状态转移与模型生成状态上的预测学习结合。在保留全时距直接预测监督的同时，分段路径学习进一步以真实目标影像监督模型经自身推进后产生的预测，使同一模型共同学习从历史观测直接预测，以及利用自身形成的中间表示继续预测的能力。

替换中文：
> Deep-OSG研究自治动力系统的变时间步长演化算子及其直接与组合演化的一致性，并包含利用真实终点状态监督两类预测的训练形式（Chen and Wu, 2023）。SpanWorld则面向不完整观测下、由天气驱动的潜在空间状态演化，将生成状态的后续预测能力作为训练与评价的中心：共享可变跨度转移使用各区间对应的天气推进状态，分段路径学习通过真实终点影像监督其后续使用。我们进一步在全日期直接监督和额外终点观测均受控的条件下，检验监督路径是否仍然影响生成状态的续预测表现。

替换英文：
> Deep-OSG studies variable-time-step evolution operators for autonomous dynamical systems and consistency between direct and composed evolution, including a training formulation that supervises both predictions using observed endpoint states (Chen and Wu, 2023). SpanWorld focuses on weather-driven latent spatial-state evolution under incomplete observations, placing the subsequent predictive usefulness of generated states at the center of training and evaluation: a shared variable-span transition advances states using the weather for each interval, and partitioned-path learning supervises their subsequent use through observed endpoint imagery. With direct supervision at all target dates and additional endpoint observations controlled, we further examine whether the supervision path still affects continued prediction from generated states.

理由：保留文献背景，具体说明状态来源、天气驱动、监督空间及受控问题，避免只有任务领域不同或只重复模型简介。

**修改2｜贡献列表第二项，已落双语MD并标蓝。**

原文：
> 2. **提出以真实观测监督分段推进预测的学习机制。** 在保留全时距直接预测监督的同时，以真实端点影像监督模型沿不同时间划分进行分段推进后产生的预测，将生成中间状态的后续预测质量纳入训练。

替换中文：
> 我们提出分段路径学习，通过生成空间状态的后续预测用途训练天气驱动的状态演化。该方法在保留全部目标日期直接监督的同时，使真实终点影像误差沿采样分段路径传播，联合训练中间状态的形成及其后续使用。

替换英文：
> We introduce partitioned-path learning to train weather-driven state evolution through the subsequent predictive use of generated spatial states. While retaining direct supervision at every target date, the method propagates observed endpoint-image errors through sampled partitioned paths, jointly training the formation and subsequent use of intermediate states.

理由：以生成状态的后续用途为训练设计中心，保留提出分段路径学习的贡献力度，不将一般联合监督原则宣称为首次。

**保留内容：**路径损失、联合目标公式及§3.2已有“梯度不截断、终点误差回传至中间状态形成”说明不改。A42第3节等价展开保留为备选，本轮无必要增加符号。摘要/引言其余句子不批量重写，框架图不动。

**证据待补：**新版模型验收后加入配对续预测与自身直接误差退化结果；旧11%与C3区间仅为原投稿证据，不能移植。匹配控制不等于Deep-OSG性能对比。A49已录原问及锁定中英回复主体，结果段和正式PDF修改位置待补。

**状态：**上述两处中英MD已落稿，原v23哈希未变；LaTeX/PDF未修改。本题主体锁定不等于整条回复可提交。T9JT第1问随后独立讨论，不合并回复。专项依据仍见A42（未随本版归档：`A42_SpanWorld回应DeepOSG_LISG_正文公式与回复双语方案_20261111.md`），其旧候选修改范围和回复以本节最新决定为准。

### 2.4 为什么需要分段续预测，以及何时选择两种模式

**问题原文**

> In what application scenarios is a model supporting both direct forecasting and continued prediction from generated intermediate states particularly advantageous? How should one choose between these two prediction modes across different scenarios?

**中文翻译**

> 在哪些应用场景中，同时支持直接预测和从生成中间状态继续预测具有特别的优势？不同场景下应如何选择两种模式？

**策略总写（2026-11-14锁定）：仅完善本题回复，正文不新增用途段落。**

回复顺序：两种模式对应目标日期查询与接续模拟；以潜在的分阶段天气情景分析给出具体对比；直接预测从初始状态分别处理各完整情景，续预测复用共同前期生成状态，再根据后续天气分支；最后明确模式选择，并落到论文已有的状态续预测能力及匹配验证。保留“潜在应用场景”的准确定位，不另写一整段防御性限制声明。完整中英问答已入A49。

**正文具体措施：**此前拟在§3.1新增模式选择段落的方案取消；现有路径定义与引言科学问题保留，不改公式和框架图。本题不宣称正文已新增说明。最终如引用数值，等新版验收后填入。

**内部审计：**共同前期复用仅指潜在状态演化；新版基础预测读取天气，各分支仍需匹配的基础预测，不能扩大为整个模型免重算或已证明效率优势。多日期不必然需要分段。接近直接精度不等于状态功能完全相同。不新增同化、超100天或分支应用训练。T9JT相关问题单独处理。

## 三、第三位审稿人：1 分，Clear rejection

### 3.1 与已有多步方法重叠，续预测改善似乎属于预期结果

**问题原文**

> The technique is not new, as Deep-OSG already supervises both direct and composed predictions.
>
> The empirical result is somewhat expected, since a model never trained on its own outputs will degrade when chained.
>
> How does partitioned-path learning differ from Deep-OSG? A comparison with Deep-OSG, or with other multi-step training methods like scheduled sampling or latent overshooting, would help to see what is new here.

**中文翻译**

> 该技术并不新，Deep-OSG 已经同时监督直接与组合预测。
>
> 实验结果在一定程度上可以预期，因为未在自身输出上训练的模型在链式使用时会退化。
>
> 分段路径学习与 Deep-OSG 有何不同？与它或 scheduled sampling、latent overshooting 等多步训练方法比较，有助于说明新意。

**最新锁定并落实：** A49本题已整合为完整中英回复，不再并列原A/B候选。方法定位首段保留；核心对照检验监督路径，一致性消融检验相同路径下的监督目标。填入已验收D/seed42/固定40轮表I1A：完整方案三条路径续预测MSE均最低，15+35路径0.04174650对0.04311991，降低3.19%。不将一致性对照等同于Deep-OSG、scheduled sampling或latent overshooting完整复现。

**正文具体措施：** 本次无新增修改；继续复用2.3已落稿的Related Work及贡献第二项，以及既有§4.4和附录I表I1A，不另增重复段落，不改公式。

**未关闭项：** 最终C1/C0R三个配对种子的核心续预测结果、相对各自直接预测的退化、种子变化、最终表号及匹配条件核对。A49中英保留对应待补占位；只补已验收消融，不预写三种子结论。最终LaTeX/PDF仍待同步。

### 3.2 固定窗口内分段仅追平直接预测，缺少实际使用场景

**问题原文**

> In simple terms, the task is finite-horizon forecasting: a fixed 100-day window where every date is directly supervised.
>
> Multi-step prediction only matches direct prediction and never improves on it.
>
> No real use case is tested: no new observations mid-forecast, and no forecasting beyond day 100.
>
> In exp. setup, multi-step prediction only matches direct prediction. Is there a case where continuing from a generated state actually helps, for example when a new observation arrives at day 50, or when forecasting beyond day 100?

**中文翻译**

> 任务本质上是固定 100 天窗口的预测，每个日期都受到直接监督；多步预测只是达到直接预测的水平，没有超过它。
>
> 没有验证实际用例：既没有预测中途的新观测，也没有超过第 100 天的预测。
>
> 是否存在从生成状态继续预测真正有帮助的情形，例如第 50 天接入新观测，或者预测超过第 100 天？

**策略总写（2026-11-14锁定）：直接回复，不新增应用实验或正文段落。**

回应“能运行≠实际价值”；以表1与自身直接误差退化说明已验证收益是相对匹配直接终点对照的状态复用可靠性，而非超过直接预测。明确未评估第50天观测更新或超100天；说明不接入新观测可单独检验模型生成状态，不混入新增信息收益。以接续模拟能力收束，不承诺应用优势或未来实验。完整原问及中英回复已入A49。

**正文措施：**无新增修改；保留既有科学问题、表1及退化分析。本题不启动同化、超时域或天气分支实验；只使用原有已验收证据及既定新版评估产出。最终以新版配对结果、退化、种子统计及实际表号替换原稿结果段，不能混用新旧模型。

**数据与实验边界：**当前使用50天历史、100天预测窗口；无超100天评价目标不等于断言原始数据绝对不存在更长序列。真实第50天观测进入模型与仅作评价标签不同，状态替换干预不是观测同化。当前主体锁定，数字验收待补。

### 3.3 缺少外部方法比较

**问题原文**

> The empirical validation rests on one in-house control, with no other multi-step methods or VegeDiff/VegSim for comparison.

**中文翻译**

> 实证验证主要依赖一个内部控制模型，缺少其他多步方法或 VegeDiff／VegSim 的比较。

**策略总写（2026-11-14更新锁定）：EO-WM提供正式外部预测参照；VegeDiff透明单列适配结果，不用于优越性结论；VegSim说明minicube级输出与逐像素任务的差异。本题不追加训练或深入诊断。**

**2026-11-14已落实：以下为当前执行状态，替代此前“待入表/待落稿”记录。**

相关工作EO-WM定位与引用此前已完成；本轮在双语工作稿补齐§4.1附录指引、附录B.1外部方法说明及B.2结果。原稿和LaTeX/PDF不动。EO-WM数据直接来自`03_关键实验结果/EO_WM公开权重重评_20261113/最终分数与验收证据.json`；VegeDiff数值与适配边界依据A08及已锁定A49。以下均以蓝色span.revision落稿。

**§4.1：替换原“标准预测比较见附录B”及后续引导句。**

> 标准预测结果见附录B，涵盖既有预测基线及天气条件多光谱预测方法EO-WM。下文通过同架构匹配比较，进一步检验监督路径对生成状态后续预测价值的影响。

> Standard forecasting results are provided in Appendix B, covering existing forecasting baselines and EO-WM, a weather-conditioned multispectral forecasting method. We next use an architecture-matched comparison to examine how supervision paths affect the subsequent predictive usefulness of generated states.

**附录B.1：新增外部方法短说明（中英全文）。**

> 我们使用EO-WM公开权重及配套EO-VAE，在统一的GreenEarthNet四分区与NDVI评分协议下进行适配评价。其EarthNet数据体系与GreenEarthNet在卫星观测、气象驱动和任务设计上密切相关。每例采用30步Euler采样生成5个预测成员，对预测反射率取均值后计算NDVI；波段、地形与天气输入按数据接口作相应适配。这里报告公开权重的适配表现，训练条件与本文模型不同。

> We evaluate released EO-WM weights and the accompanying EO-VAE under the shared GreenEarthNet four-split and NDVI scoring protocol. Its EarthNet setting is closely related to GreenEarthNet in satellite observations, meteorological drivers, and task design. For each sample, we generate five prediction members using 30 Euler sampling steps and average predicted reflectances before computing NDVI; band, terrain, and weather inputs are adapted to the data interface. These results characterize the adapted released weights, whose training conditions differ from those of our model.

> 对于VegeDiff，我们依据官方代码训练适配模型。在所核查的官方发布资源中，未找到可直接使用的自编码器权重，因此采用公开的EarthNet微调EO-VAE，并进一步在GreenEarthNet训练数据上适配。扩散预测模型训练100 epoch（seed 97），按验证集选择checkpoint。当前实现训练时未执行条件随机丢弃，而评价使用CFG scale=2；这一训练与采样设置的匹配问题及替代潜空间的影响尚未排除。我们单列其适配结果，不据此判断原始VegeDiff的性能或声称优于该方法。

> For VegeDiff, we train an adaptation based on the official code. We did not find directly usable autoencoder weights in the official resources inspected, so we use the publicly released EarthNet-finetuned EO-VAE and further adapt it on the GreenEarthNet training data. The diffusion predictor is trained for 100 epochs (seed 97), with checkpoint selection based on validation performance. The current implementation does not randomly drop conditioning during training, whereas evaluation uses CFG scale=2; the effects of this training–sampling mismatch and the substituted latent space remain unresolved. We report the adapted results separately and do not use them to characterize the original VegeDiff method or claim superiority over it.

> VegSim与本文在天气驱动的潜在植被状态演化方面相关，但其公开任务预测minicube级NDVI序列及分位数，与本文的逐像素空间预测粒度不同，因此不将其原文指标直接纳入同一精度排名。

> VegSim is related to our work in weather-driven latent vegetation-state evolution, but its released task predicts minicube-level NDVI sequences and quantiles rather than pixel-level spatial forecasts. We therefore do not rank its published metrics alongside results from our pixel-level task.

**附录B.2：表格与统计说明。**

表B2四分区各增加EO-WM一行，五项指标R²/RMSE/NSE/绝对偏差/RMSE25按验收JSON保留四位小数；种子列标“公开权重 / Released weights”，五个生成成员不视为训练种子。B.1“所有学习方法三种子”句同步排除公开权重EO-WM；表注改为逐方法标明种子，多种子报告均值±样本标准差，公开权重报告适配评价，确定性方法为点估计。B3/B4保留原三种子方法的逐种子数据，不为EO-WM编造种子。

表B2后独立披露VegeDiff适配结果，IID/OOD-T/OOD-S/OOD-ST RMSE为0.4043/0.3882/0.4031/0.4030，不纳入最佳值标记或优越性排名。没有隐藏低分，也没有认定低分原因已被验证。EO-WM四分区RMSE为0.1578/0.1571/0.1679/0.1624。旧SpanWorld及其他结果未替换，新旧模型不可混作最终结果。

**正文与故事边界：**本题不修改摘要、引言、方法；正文简短指向附录，数据相关性和适配放附录与回复。外部预测比较与内部路径控制互补，不把EO-WM评价说成外部多步训练方法的完整比较。最终性能概述待验收，不能用附录指引替代审稿人对标准精度的全部关切。不追加VegeDiff训练或诊断。

**状态：**本题不依赖新模型结果的已确认写作内容已落双语MD；A49同步为工作稿已落实。待补最终模型身份/配置、标准精度及与EO-WM和强基线的客观关系、核心配对种子发现、LaTeX/PDF同步与最终表格强调标记审计。工作稿顶端已明确旧结果仍待替换；提交前清除所有内部占位及编辑说明。

### 3.4 标准精度落后及缺少训练阶段的组件消融

**问题原文**

> It scores below Contextformer and PredRNN on the official metrics, even though Contextformer is its own backbone.
>
> There is no real ablation study, only test-time changes to one trained model.
>
> Why does SpanWorld score below Contextformer on the official metrics when Contextformer is its own backbone? Retraining without individual components would also help clarify which parts of the design matter.

**中文翻译**

> 尽管 Contextformer 是其骨干，SpanWorld 的官方指标仍落后于 Contextformer 和 PredRNN。
>
> 没有真正的消融研究，只有对一个已训练模型进行测试时修改。
>
> 为什么精度落后？移除组件后重新训练，也有助于说明哪些设计确实重要。

**策略总写：精度问题按 2.2 处理；保留已有训练机制对照，补充一项关键组件的单种子重训消融，不开展多种子或全面组件组合实验。**

当前具体实验以A47第1、4、5、8、11节后续锁定为准，覆盖早期“优先移除天气条件”的候选。C1/C0R为独立训练的监督机制对照，状态替换、恒等转移归为测试时干预。补充训练目标比较采用匹配40epoch的C1/C0R/一致性设置；组件比较采用完整模型与仅基础预测框架，严格核验公共设置。时间不足时允许已有自训基础模型作为参照，但不匹配就不能称严格组件重训消融。附录一张组合表分“训练目标比较区”和“组件比较区”；前者重点共同后缀续预测MSE及相对自身直接预测的退化，后者标准RMSE/R²，无状态接口时续预测标不适用。正文只概括实际发现并指向附录。核心C1/C0R三配对种子100epoch计划保持。当前结果未验收，下一轮先讨论回复，不新增训练、不宣称完成。

### 3.5 未来天气来源及真实天气预报误差

**问题原文**

> The weather data seems to be observed rather than forecast, and the paper does not say where it comes from.
>
> Where does the future weather come from? It looks like observed data rather than forecasts. If so, how would performance change with real weather forecasts, or with noise added to the weather?

**中文翻译**

> 天气数据似乎来自观测而非预报，论文也没有说明来源。
>
> 未来天气来自哪里？若使用真实天气预报，或向天气输入加入噪声，性能会如何变化？

**策略总写：补清天气来源与条件预测设定，不接入真实天气预报；轻量天气扰动实验作为可选补充。**

**执行状态更新（2026-11-14，覆盖下文此前“待落稿”状态）：**用户批准后，已在双语论文工作副本§4.1预测窗口说明后插入下列中英来源句，均用span.revision标蓝；核对仅两处插入，原v23哈希不变。A49完成句已同步。LaTeX/PDF未修改；本题不新增实验。后续3.6先讨论，未授权新段落落稿。

最新锁定：A49已存本题原问、温和且立场明确的中英回复主体及T9JT总起。组织顺序为来源与基准依据→受控科学问题→预报误差问题的实际证据边界；不以纠正或质疑审稿人的语气表述，不新增实验承诺。跨问题理解分歧仅作内部检查线索。此前“加强版回复待审核”状态由本次主体锁定覆盖；正文来源句仍待实际落稿，不能提前声明已修订。

2026-11-14最新边界：用户接受正文最小来源说明，不在正文展开业务预报答辩。§4.1数据介绍拟加：“天气驱动采用GreenEarthNet配套的E-OBS气象站观测插值数据（Benson et al., 2024）。” / “Weather forcing is taken from the E-OBS interpolated meteorological station observations provided with GreenEarthNet (Benson et al., 2024).” 尚未应用到论文MD。回复强化可核查依据：基准原文§3.1公式(1)明确历史与未来天气输入，§3.3明确观测插值来源；这是基准定义的条件预测，不是SpanWorld独有的额外输入待遇。匹配研究检验给定共同天气下监督路径的作用，不能外推为预报误差不影响结论。业务天气/加噪性能尚无直接结果，简洁回答而不承诺新增工作。已有天气替换不是预报噪声验证。跨问题理解分歧备忘已入A49，仅作内部组织线索，非指责审稿人动机；加强版回复待用户审核。

正文说明天气来自 GreenEarthNet 配套的 E-OBS 气象站观测插值数据，本文研究给定天气驱动下的植被预测与状态续预测能力。匹配对照使用相同天气输入，用于检验监督路径的作用；真实天气预报误差对效果的影响尚未验证。扰动评估只作为可选补充，不自动增加实验任务，也不提前承诺结果；若开展，应与 3.9 统筹。天气扰动不能等同于真实业务预报验证。

### 3.6 输入与目标经过预处理，实际应用意义受到质疑

**问题原文**

> Inputs and targets both come from the preprocessed benchmark. This raises concerns about real-world impact, since real-time forecasting would face noisy satellite imagery.

**中文翻译**

> 输入与目标都来自预处理后的基准数据，这使实际应用意义受到质疑，因为实时预测会面对带有噪声的卫星影像。

**策略总写：说明标准预处理的合理性，引用已有云与缺测处理说明；明确部署边界，不新增原始影像或噪声实验。**

**2026-11-14锁定：**用户接受A49中英完整回复；本题不新增正文或附录文字，覆盖下文“必要时补一两句”的候选。引用现有§4.1不完整观测设定及附录A.1输入掩膜、A.2监督、B.1评价规则。回复先解释质量控制与缺测，再连接天气驱动状态续预测的科学问题，末句交代其他噪声条件尚未评价。最终按新模型核对实现与上述位置，不将处理缺测等同于噪声稳健性。无新实验、无论文改动。后续仍有3.7—3.11待逐项处理，不是只剩等待结果。

指出本文沿用公开基准的数据质量控制与评价流程，标准预处理使训练和评价建立在有效遥感观测之上，本身不能推出研究缺乏实际意义。引用正文已有的不完整历史观测说明、附录 A.1 的有效性掩膜及 A.2 的损失掩膜规则，必要时仅在正文补一两句，不重写完整预处理流程。说明模型输入并非因此完整、无噪声；其他观测质量或预处理误差变化下的部署效果仍需进一步验证，但不接受“使用预处理数据便削弱现有受控实验有效性”的推论。本轮不新增原始影像流程或影像噪声实验。

### 3.7 缺少内部表征的直接分析

**问题原文**

> The internal representations highlighted in the motivation are never analyzed directly, either quantitatively or qualitatively.
>
> The paper motivates the work through internal representations, but I couldn’t find any direct analysis of them. Could you show how close the states reached in steps are to those reached directly, for both SpanWorld and the control?

**中文翻译**

> 动机中强调的内部表征没有得到直接的定量或定性分析。
>
> 能否分别展示 SpanWorld 和控制模型通过分段路径与直接路径到达的状态有多接近？

**策略总写（2026-11-15用户锁定并落实）：仅新增附录E.3及表E3，正文不增加概述；以同模型内部直接/分段状态余弦相似度回答原问，结合已有续预测评价解释。**

**具体稿件修改：** 在附录E中文和英文部分各新增E.3；共用表E3，不改变原E.1/E.2及表E1/E2。中文实际新增内容如下，英文对应已同步双语工作稿。

我们比较直接与分段路径到达第50天的潜在状态。使用核心续预测评价中的2,837个IID样本，分别计算每个模型的25＋25天、15＋35天分段状态与其自身直接路径状态的余弦相似度。SpanWorld与直接端点监督对照均使用seed42的验证集选定权重。

**表E3：到达第50天的直接与分段状态相似度。** 对每个空间token的通道向量计算余弦相似度，再在样本内及样本间取平均。15＋35天为训练未见划分。

| 分段路径 | SpanWorld | 直接端点监督对照 |
|---|---:|---:|
| 25＋25天 | **0.9270** | 0.6889 |
| 15＋35天 | **0.9094** | 0.6990 |

在两条受测路径上，SpanWorld的分段状态与其自身直接路径状态的平均余弦相似度均高于对照。该分析从内部表征层面补充了生成状态的续预测评价。

**回复思路与状态：** A49已新增T9JT原第4问的原问、中译及完整双语回复，明确指向附录E.3、表E3。附录简洁报告设置和观察，回复解释与续预测证据的互补关系；不重复总研究动机，不将状态相似度等同于预测质量或物理自洽。取消此前“在正文概述”的候选措施。

**证据与提交门槛：** `03_关键实验结果/D_state_similarity_seed42_20261115/`；2837个IID样本、11348行、真实exit0，样本清单/SHA/聚合重算PASS。D-C1/C0R seed42的既有验证best，与核心六表权重一致；仅单种子内部状态分析。状态RMSE保留原始记录，论文小表只列余弦。双语MD已落稿；LaTeX/PDF及最终引用待统一同步。

### 3.8 为什么只预测 NDVI，而不是完整多光谱影像

**问题原文**

> The world-model framing seems too broad. It predicts only NDVI, not the full image, and it’s not clear why only NDVI.
>
> Why focus only on NDVI? Since the paper frames SpanWorld as a remote-sensing world model, have you tried predicting the full multispectral image?

**中文翻译**

> 世界模型的表述似乎过宽，模型只预测 NDVI 而非完整影像，也没有解释为什么只关注 NDVI。
>
> 为什么选择 NDVI？既然定位为遥感世界模型，是否尝试过完整多光谱预测？

**策略总写：本轮解释 NDVI 的研究范围；完整多光谱预测留待后续期刊工作，不列入本轮实验承诺。**

**2026-11-14已落实：**A49本题原问和中英回复主体锁定。双语论文工作副本§3.1首次定义NDVI输出后各加一句并标蓝：中文“本文聚焦植被动态，选择空间NDVI图像作为观测输出，以后续真实卫星观测检验潜在状态的预测价值。”英文“We focus on vegetation dynamics and use spatial NDVI images as the observation output, evaluating the predictive value of latent states against subsequent real satellite observations.” 不改摘要/贡献/结论或输出公式；核对仅两处插入，原稿哈希不变，LaTeX/PDF待同步。回复顺序为植被研究目标→NDVI观测与评价依据→状态演化及匹配科学问题→完整多光谱未验证。期刊安排仅内部保留，不用未来计划代替原问答案。

正文说明本文聚焦植被动态，沿用 GreenEarthNet 的 NDVI 预测任务评价天气驱动下的状态演化与续预测能力。明确 NDVI 是本文选择的观测输出，潜在状态通过其后续预测作用接受检验，不把模型描述为已经完整重建所有遥感波段或生态过程。如实说明完整多光谱预测尚未在本轮验证，留待期刊扩展；不以波段数量作为世界模型身份的唯一判断，也不以名称替代能力边界说明。

### 3.9 天气分析样本较少，极端天气下没有额外优势

**问题原文**

> The weather analysis uses only 84 samples, and the paper’s own test shows no extra benefit under hot-dry conditions.

**中文翻译**

> 天气分析仅使用 84 个样本，而且论文自身的测试未显示炎热干旱条件下的额外收益。

**策略总写（最新锁定）：先按原稿证据回复，不修改正文、不承诺新增评估；中英文主体已入A49，状态为待补充／最终核对。是否补充天气评估取决于时间及实际验收。**

说明84个样本由附录F.1的热旱阈值与天气有效性条件筛选，承认推广范围有限。实际天气替换为匹配供体/均值天气均提高受测子集误差，支持天气的预测信息作用；供体替换效应在热旱与正常样本之间未显示明确差异，不声称热旱额外优势。将天气驱动与生成状态的预测用途联系起来，不作生态因果推断。时间允许且新结果验收后再补模型身份、样本范围、效应与不确定性、子集差异及图表位置；扩大总体样本不能替代极端子集证据。不补时也须核对旧模型分析在终稿的保留方式，不冒充新模型结果。此前扩大评估属于候选，不再作为本题对外承诺；无新训练/调度授权。

### 3.10 缺少生态学见解

**问题原文**

> The paper offers no ecological insight as a physical-sciences paper.

**中文翻译**

> 作为一篇物理科学应用领域的论文，本文没有提供生态学方面的见解。

**策略总写：明确论文的方法贡献定位，基于已有结果补充生态应用意义；植被类型分组分析改为可选，不新增强制实验。**

2026-11-14最新锁定：A49已归档本题原问及中英文回复主体，标记最终结果待核对。当前不新增正文，不新增实验。突出受测设置下直接精度相近但续预测表现不同的具体认识及其对植被状态训练/评价的意义，不称为生态机制发现。最终用验收结果核对原稿与新版身份。回复去重留至所有回复与结果整合后，拟删改须先向用户展示原问、修改前后完整回复；总起可选，不作为理解单题回复的前提。

说明本文旨在改善天气驱动下植被状态的续预测能力，并不以发现新的生态规律为目标。结合已有状态和天气分析，解释样本相关状态与天气条件对植被动态预测的意义，区分预测证据与生态机制解释；不能仅以“属于应用领域”推定必须提出新生态定律，也不能用“超出范围”完全回避领域价值。优化训练后，如已有结果便于按植被类型分组，可作补充；本轮不承诺新增生态发现，不将误差或天气响应解释成已验证的干旱记忆、物候或因果机制。

### 3.11 写作重复且难以理解

**问题原文**

> The writing is repetitive and hard to follow.

**中文翻译**

> 写作重复，难以理解。

**锁定策略（2026-11-14）：保留故事与章节结构，以两处局部压缩回应重复问题；方法流程澄清沿用2.1已落实修改。**

摘要、引言、§4.3及结论保留。§4.2集中解释匹配条件下监督路径的作用；§4.4末尾概括实验的互补职能，避免再次完整重述核心结论。完整实现与补充设置留附录，不新增实验、不重画框架图，不扩大为无关语言润色。

**已执行的正文修改：双语工作稿两处中英共四段，统一蓝色span.revision标记。以下保留修改前后全文供审计。**

**§4.2中文修改前**

> 在目标日期覆盖与额外监督影像相同的条件下，分段路径学习减轻了继续预测退化。额外监督所用端点影像的日期已经包含在直接监督覆盖的范围内。因此，改善来自这些观测对状态推进路径施加约束的方式：端点误差同时评价了复用生成中间状态后的预测。这一比较表明，将生成状态的后续使用纳入监督，有助于保留模型推进后的预测能力。

**修改后**

> 在全部目标日期均已接受直接监督、额外监督影像相同的条件下，这一比较表明，监督所经过的状态推进路径仍会影响生成状态的后续预测能力。分段路径学习通过真实端点误差约束中间状态的形成及其后续使用，减轻了受测路径上的继续预测退化。

**§4.2 English修改前**

> With the same target-date coverage and endpoint images for additional supervision, partitioned-path learning reduces degradation in continued prediction. The additional endpoint images already fall within the dates covered by direct supervision. The improvement therefore concerns how those observations constrain the state-transition path: the endpoint error also evaluates predictions that reuse a generated intermediate state. This comparison shows that supervising the subsequent use of generated states helps preserve predictive capability after rollout.

**修改后**

> With all target dates already directly supervised and the same endpoint images used for additional supervision, this comparison shows that the state-transition paths along which supervision is applied still affect subsequent prediction from generated states. Partitioned-path learning uses observed endpoint errors to constrain both the formation and subsequent use of intermediate states, reducing degradation in continued prediction along the evaluated paths.

**§4.4中文修改前**

> 这些结果共同表明，即使直接预测误差接近，监督路径仍会影响生成状态的继续预测表现。分段路径学习以真实观测监督生成状态被再次使用后的预测，减轻了受测路径上的继续预测退化。未见划分、组件干预和输入替换进一步说明了共享转移的使用范围，以及动态状态和天气对预测的贡献。

**修改后**

> 这些评测从互补角度检验了SpanWorld：核心对照考察监督路径对续预测的影响，未见时间划分检验共享转移的组合使用，组件干预和输入替换则分析状态与天气对预测的贡献。

**§4.4 English修改前**

> Together, these results show that supervision paths affect continued prediction from generated states even when direct-prediction errors are similar. Partitioned-path learning applies observation-based supervision to predictions made after generated states are reused, reducing degradation across the evaluated paths. Unseen partitions, component interventions, and input replacements further characterize the use of the shared transition and the contributions of dynamic states and weather.

**修改后**

> These evaluations examine complementary aspects of SpanWorld: the controlled comparison tests how supervision paths affect continued prediction, unseen temporal partitions test the compositional use of the shared transition, and component interventions and input replacements examine the contributions of states and weather.

**问题→位置→依据→状态**

| 原问 | 修改位置 | 依据与作用 | 状态 |
|---|---|---|---|
| 写作重复 | §4.2结果解释后半段 | 保留目标日期与额外影像匹配条件，合并重复解释；实验数值不改 | 双语MD已完成 |
| 重复、难以理解 | §4.4末尾 | 区分核心对照、未见分段与状态/天气干预的证据职能；§4.3必要区分保留 | 双语MD已完成 |
| 方法难以理解（与2.1共用） | §3.1及图注 | 沿用已有的方法连接、基础预测术语与图注澄清 | 双语MD此前已落实 |

完整中英回复见A49 3.11。原始v23与LaTeX/PDF未修改；正式回复完成时态仅在同步并核查最终稿后使用。新结果未验收，本轮不改变旧数值及统计主张。回复内部去重待各题与结果齐备后逐审稿人审计，不将本次局部正文修订称为全篇或回复去重完成。

## 附录：本轮可能改动的内容与相对风险

本附录只记录已讨论的候选范围，不是具体实现方案，也不表示候选改动已经采用。以下为相对审稿论证与验证工作量的判断，不是会议对具体改动的预先许可；多个局部改动叠加后需按整体影响重新判断。本轮暂不更换主模型基座／基础框架，不整体改成扩散模型。

| 顺序：风险由低到高 | 可能改动的内容 | 本轮暂定边界 |
|---|---|---|
| 1．较低 | 正文澄清、引用与贡献表述、已有结果整理、状态诊断与推理成本 | 优先回应已有意见，避免新增未经验证的能力声明。 |
| 2．较低至中等 | 优化器、学习率、调度、训练轮数、损失权重，以及实现错误修正 | 可作为精度优化候选；记录变更，按实际影响重训或重评。修正代码少不等于结果影响小。 |
| 3．中等 | 天气的日／五日统计与序列表示、时间对齐、天气 mask／缺测规则，以及简单季节／日期特征 | 维持预测时可用的信息条件；借鉴他人实现前核对具体逻辑与来源。若目标或评价掩膜改变，相关方法按统一口径重评。 |
| 4．中等偏高 | 在现有状态转移内使用 AdaLN 天气调制，调整局部条件融合 | 属于局部结构改动；说明替代了什么，保持主模型与直接终点控制的公共结构一致，补齐必要证据。 |
| 5．较高、暂不锁定 | 针对 Deep-OSG 重叠部分的新训练机制，专门物候、气候异常响应或长期记忆模块，以及多项核心机制联合修改 | 先确认具体问题和实质增量，方案另行讨论；不为了制造表面差异而增加机制，不自动进入本轮执行。 |
| 6．本轮不做 | 更换主模型基座或整体基础框架；改为扩散模型及其训练采样体系 | 用户已明确暂不采用。外部方法选择 VegeDiff／VegSim 之一，不等于更换 SpanWorld 主模型框架。 |

公共改动进入主模型后，核心配对对照采用同样的季节、天气、mask 和优化配置；用验证集选择方案，保留原配置与结果来源。更新后的相对收益以实际复评为准，不能沿用原配置约 11% 的数字，也不能把联合优化收益全部归于单个机制。单项组件消融仍限定为一个匹配种子，不因附录列出候选方向而自动增加多项消融。采用的改动同步写入方法、实验与对应回复；按需要在最终 PDF 中标注修改。

## 依据与原稿定位

- 审稿原文：[OpenReview 讨论页](https://openreview.net/forum?id=ezBYm2cIpd)；本次逐句整理依据用户提供的 OpenReview 文本（历史路径：`C:/Users/32084/.codex/attachments/2345ac0f-f9eb-48dc-a081-5368c65a3c6d/已粘贴的文本.txt`）。
- 实际投稿：下载的投稿 PDF（历史路径：`D:/datato/Chrome/17467_SpanWorld_A_Variable_Spa.pdf`）。对应 v16 PDF（未随本版归档：`E:/MineProgram/codexwork/CVPRAAAI投稿/WorldModel2026v2/terrastate/writing/SpanWorld后续写作/ICLR2027完整稿_v16_图2拼写修正版替换_20260925/spanworld_iclr2027.pdf`） 与 v23 中英双语稿（未随本版归档：`E:/MineProgram/codexwork/CVPRAAAI投稿/WorldModel2026v2/terrastate/writing/SpanWorld后续写作/SpanWorld_全文完整稿_中英双语_v23_图2拼写修正版替换_20260925.md`）。
- 已有实验定位：表 1 为三种路径到达第 50 天后的续预测；图 4(a) 为九种未见分段的终点精度；图 4(b) 为状态替换；附录 A.1／A.2 为输入与掩膜说明；标准预测比较在附录 B，不将 v17 后增的正文标准表当作原稿已有内容。
- Deep-OSG 方法关系核对：[第 3.2 节及 LISG 训练目标](https://arxiv.org/html/2302.03358#S3.SS2)。真实终点联合监督已有先例；当前回应采用 2.3 所链接的 A42，新增机制仍需另行研究与确认。
- GreenEarthNet 来源核对：[基准原论文](https://arxiv.org/html/2303.16198)。第 3.3 节说明 E-OBS 气象站观测插值数据，第 3.1 节说明任务与有效像元掩膜。
- 本文将最后确认的范围收拢在同一文档中；A38 等旧材料保留，不据其较宽候选列表自动增加本轮任务。研究长期规划与本轮 rebuttal 的执行范围分开处理。

## 2026-11-14消融预算表述锁定（用户确认）

正文、附录及回复统一使用：

> 我们在匹配的公共训练设置下，对各组模型训练40轮后的表现进行消融比较。

> We compare the models after 40 epochs of training under matched common training settings.

该句描述实际评价的训练阶段，不声称所有模型仅训练40轮，也不声称40轮为事前预注册预算。正文和回复主体不展开总训练轮数或权重截取过程；原始结果和此前选模敏感性记录保留。避免笼统声称全部配置相同或计算资源完全相同：实验组的监督路径/目标本来不同。

已接受的正文中文表述（与附录I实际就绪后一并落入论文，当前不提前插入无对应附录的引用）：

> 为检验简单训练目标能否替代分段真实端点监督，我们在匹配的公共训练设置下，对各组模型训练40轮后的表现进行比较。在seed42下，完整方案在三条受测路径上均取得最低的续预测MSE，其中训练未见的15＋35天路径较一致性替代降低3.19%（完整结果见附录I）。

当前仅锁定此措辞与正文候选；完整附录布局和问答继续按逐项审核流程确认后再落稿。表A精确CSV已归档，展示保留直接MSE和续预测MSE，不单列误差增量；原CSV诊断列不删除。B区仍待结果验收与文案讨论。本次不改训练、不改原始证据、不同步LaTeX/PDF。

## 2026-11-15 授权范围纠正：结果归档完成，论文落稿待审核

用户澄清：接受汇入的是结果记录文档，正文/附录及回复仍须先讨论具体位置与文案，再经审核落稿。此前误加入双语工作稿的§4.4中英文段落、新附录I及页首完成说明已撤回；本文件此前相应“已落稿”记录及未经确认的审计方案也已撤回。D配置seed42固定第40轮组件比较四划分结果与验收记录保留（见A08、统一索引及`03_关键实验结果/D_seed42_fixed40_20261114/B_standard_fixed40.csv`），结果已验收不等于文案已获批准。接下来按原问→锁定策略→当前分析→具体正文/附录与回复候选→用户审核的主线推进。原v23、LaTeX/PDF未动。


## 2026-11-15 用户最终授权：A沿用、B接入，双语MD与回复已落实

覆盖此前“撤回/待落稿”的当前状态，历史记录保留。A的比较与已锁定结论不变，B接在A后；正文§4.4表2后统一引导，附录I为“训练目标与动态状态分支消融”，表I1A训练目标、I1B组件重训。原v23、LaTeX/PDF不动。

### 正文确切新增内容

为检验简单训练目标能否替代分段真实端点监督，我们在匹配的公共训练设置下，对各组模型训练40轮后的表现进行比较。在seed42下，完整方案在三条受测路径上均取得最低的续预测MSE，其中训练未见的15＋35天路径较一致性替代降低3.19%。在此基础上，我们进一步通过移除动态状态分支并重新训练，考察该分支对标准预测表现的影响：完整模型在四个测试划分上的R²均更高，两组RMSE数值接近。两部分的完整设置与结果见附录I表I1。

To test whether a simpler training objective can replace observed-endpoint supervision along partitioned paths, we compare the models after 40 epochs of training under matched common training settings. With seed 42, the full model achieves the lowest continuation MSE on all three evaluated paths, reducing MSE by 3.19% relative to the consistency alternative on the training-unseen 15+35-day path. We further remove the dynamic state branch and retrain the model to examine its contribution to standard forecasting: the full model has higher R² on all four test splits, with numerically close RMSE values between the two models. Full settings and results for both comparisons are reported in Appendix I, Table I1.

### 附录与回复对账

A区保留直接/续预测MSE，不单列退化；B区保留四划分RMSE/R²。附录具体双语设置及数值见工作稿附录I；B设置为：

在上述公共训练设置下，我们移除动态状态分支及其读出，重新训练仅保留基础预测的模型，并将相应的额外端点监督施加于基础预测。表I1B报告完整模型与该重训模型在四个测试划分上的标准预测RMSE与R²。完整模型在四个划分上均取得更高的R²；两组RMSE数值接近，其中完整模型在OOD-S上更低，在其余划分上略高。

Under the same common training settings, we remove the dynamic state branch and its readout and retrain the baseline-only model, applying the corresponding additional endpoint supervision to the baseline forecast. Table I1B reports standard forecasting RMSE and R² for the full and retrained models on all four test splits. The full model has higher R² on all four splits; RMSE values are numerically close, with lower RMSE on OOD-S and slightly higher RMSE on the other splits.

原问为第三位审稿人T9JT原第5问，A39 3.4。完整中英回复已入A49对应小节，精度段待B/D确定和验收后补；整题未关闭。证据为`03_关键实验结果/D_seed42_fixed40_20261114/suffix_tables/A_suffix.csv`及`B_standard_fixed40.csv`。现有结果属于D，不得改标B。选模敏感性原始证据保留。正式PDF同步及旧结果统一尚未完成。


## 2026-11-15 用户锁定：后续以D为主模型

用户明确接受D的选择，后续写作、结果核对与审稿回复围绕D推进，覆盖此前“待B/D选型”的状态。B保留为选型与研究证据，不删除，不混入D主结果。

- 选型已定不等于结果全部验收；标准主结果与核心C1/C0R配对三种子继续按D的最终验收资料完成。回复中的精度占位改为等待D最终结果，不再等待B/D决策。
- 消融A/B继续使用已锁定D、seed42、固定第40轮口径；正文§4.4和附录I表I1A/B的已确认组织保持。
- 验证选优核心结果与固定40轮消融分开：当前8.76%与14.27%属于不同权重口径，不互相替换；最终数字以对应验收为准。
- 标准精度改善、绝对续预测误差变化、相对C0R收益分别报告，不写成全面提升，不把联合优化收益全部归于路径训练。已有不利结果与选模敏感性记录保留。
- 下一步先核对D的模型配置、标准结果、核心配对结果及现有状态/成本/天气证据，再按原问展示具体修改候选；用户审核后更新双语MD，最后统一LaTeX/PDF。主模型选择不授权新增训练或停止其他执行器。
- 本次仅同步决策与推进状态，不批量替换正文结果、原稿或回复主体。


### 2026-11-15 T9JT原第5问回复局部微调锁定

用户逐项确认：①接受组件段衔接修改；②保留原总结句；③末句增加“设置与”。已同步A49本题中英对应句，不修改论文正文、A区内容或实验数值。精度结果仍待补，整题未关闭。

修改前：对于组件贡献，我们补充了移除动态状态分支及其读出后重新训练基础预测模型的对照。

修改后：为进一步检验动态分支与标准预测表现的关系，我们补充了移除动态状态分支及其读出后重新训练基础预测模型的对照。

修改前：我们已在正文§4.4概括这些发现，并在附录集中呈现完整结果。

修改后：我们已在正文§4.4概括这些发现，并在附录集中呈现完整设置与结果。

②保留原文：两部分分别回答“移除动态分支后预测表现如何”和“如何训练生成状态的后续使用”，并与核心匹配续预测实验共同说明设计的作用。


### 2026-11-15 3.4完整回复同步：待补充，未关闭

A49本题已合入用户认可的精度说明开头及对应英文；保留已锁定消融段和原总结句，采用已批准的衔接及“完整设置与结果”。精度占位由等待B/D选择改为等待D最终三种子验收。

完整回复开头：感谢您指出标准预测精度与组件贡献这两个相互关联的问题。针对精度方面的关切，我们在原有状态演化框架与分段路径监督原则下，进一步完善了训练配置及季节与天气条件的表达，并在相同测试划分和评分协议下重新评价。这些公共调整同步用于完整模型和直接终点对照，使更新后的比较仍能检验监督路径对生成状态后续预测的作用。

论文§4.1保持现有附录指引，不新增精度评价句；本次未改论文。下一项按已接受主线核对D方法/附录配置与实际实现，先列原文与候选供用户审核。核心最终数值、公共配置匹配核对、LaTeX/PDF同步仍待完成，不使用单种子阶段结果填满最终结论。


### 2026-11-15 附录A.4最小修改经用户批准落稿

对应2.1方法配置准确性及3.4精度回复依据。中英工作稿A.4已更新微调范围、表A3变化单元格、主实验/消融选权重规则，统一蓝色。初始化历史段不改。

| 项目 | 原文 | 已落稿 |
|---|---|---|
| 配置/描述 | 历史骨干仅末个时序 Transformer 块参与微调 | 历史骨干最后两个时序 Transformer 块参与微调 |
| 配置/描述 | \(9.9\times10^{-7}\)，缩放系数 0.033 | \(1\times10^{-5}\)，缩放系数 \(1/3\) |
| 配置/描述 | 300 次更新线性预热，随后余弦衰减至 0 | 600 次更新线性预热，随后余弦衰减至峰值学习率的 0.1 倍 |
| 配置/描述 | 全局 64；4 设备 × 每设备 8；梯度累积 2 | 全局 32；4 设备 × 每设备 8；梯度累积 1 |
| 配置/描述 | 40 个 epoch，14,880 次更新 | 主实验 100 个 epoch，74,500 次更新 |
| 配置/描述 | 报告使用预先指定的第 14,880 次更新检查点，不以验证集最优检查点替代。核心监督路径比较中的每种模型均训练一次，使用随机种子42。未见划分及干预评估使用相应的固定检查点。 | 主实验依据验证集表现选择检查点，核心监督路径比较采用配对随机种子27、42和97。未见划分及干预评估采用seed42的相应验证选优检查点。补充消融统一使用seed42的固定第40轮检查点，详见附录I。 |

表A3种子列更新为核心配对27/42/97、补充消融42。三种子完成及跨运行设置、共同父检查点仍待验收；已在工作稿增加非投稿编辑说明，不能将方案落稿等同于全部训练完成。不改正文其他章节、原稿、LaTeX/PDF。


### 2026-11-15 A.1季节与条件调制最小修订（用户批准，已落双语MD）

对应2.1架构准确性及3.4精度回复中的条件表达更新。仅在A.1补一句token季节输入、局部替换转移描述、更新表A1两行。不新增季节表格行，不改正文公式/框架图，不把局部调整列为新贡献。新增中英文字统一标蓝。

新增句：年度正弦／余弦季节特征经线性投影加入token表示。

原文：天气与跨度表示广播至空间网格，与逐位置地理编码融合，再与归一化状态共同输入多层感知机，生成加回原状态的增量。

修改：天气与跨度表示广播至空间网格，与逐位置地理编码及终点季节特征融合，再与经融合条件调制的归一化状态拼接，共同输入多层感知机，生成加回原状态的增量。

原文：拼接 \(128+64+64\) 维条件；MLP \(256\to256\to256\)

修改：拼接 \(128+64+64\) 维条件；MLP \(256\to256\to256\)，融合2维季节特征的线性投影

原文：拼接 LayerNorm 后的状态与融合条件

修改：拼接经条件AdaLN调制的状态与融合条件

证据：D配置use_adaln=True、annual_sincos_v1、tokens_and_transition；releases/spanworld_v2/dev/models/plan_b_b4.py与D归档源码SHA一致（9728a6ad8102041c75b1278a1ad01f4961ceabadd5315ecb7e9011119ee05032）。代码保留条件拼接和残差路径，季节投影融入条件，AdaLN调制归一化状态；未扩张原MLP拼接维度。token季节路径由归档编码器核对。LaTeX/PDF未同步，其他待验收事项保持。


### 2026-11-15 A.2损失口径最小修订（用户批准，已落双语MD）

对应2.1/3.4配套事实核验，不新增审稿问题或重写回复。用户要求保留公式：显示公式与编号不动，仅文字补充无有效目标像素的q置零规则，并修正跨设备计数归一化及排除无监督像素两句。

原文：其中 \(-1\) 为沿用的预测无效标记：

修改：其中 \(-1\) 为沿用的预测无效标记；对于整个预测窗口内无有效目标观测的像素，将 \(q_{ip}\) 置为0。

原文：上述归一化在各设备的每个微批次内计算；损失按梯度累积次数缩放，梯度跨设备平均。

修改：上述损失使用跨设备汇总的有效监督计数进行归一化。

原文：若像素在整个窗口无有效观测，其序列误差为零，但满足外层掩膜时仍计入分母；

修改：整个预测窗口内无有效目标观测的像素不参与序列损失平均；

来源核验：D配置supervision_v2=True；模型调用明确exclude_unsupervised_pixels开关。此前损失文件来源缺项已在D_seed42_ablation60_20261114/fairness_audit的evidence/shared_code/models/losses/masked_l2_ndvi.py找到归档原件，SHA256为b97e43a65fd814d37847e52d01a21ca643b8b036552002ebe03aa02f62671cdb，与查阅实现一致；关联download_receipt.json、training_evidence/C1/plan.json及C0R/source_manifest.json。全局计数辅助文件SHA与D记录一致。端点零监督说明、损失权重和公式主体保持不动；不据此归因精度收益。原稿和LaTeX/PDF未改。
