# A49｜SpanWorld ICLR逐项审稿回复：中英锁定稿

> 最新主线：2026-11-15用户已确定D为后续主模型；旧“待B/D选型”状态失效。D最终结果验收仍待逐项完成，详见文末锁定记录。

> 当前状态：2026-11-15用户最终批准，消融A/B已落双语MD及本文件T9JT原第5问中英回复。精度待B/D确定；下方此前撤回状态为历史，以本条及末尾新节为准。

> 最新状态（2026-11-15，授权纠正）：D配置seed42固定40轮组件比较结果已验收归档；正文、附录及回复文案仍待逐项讨论审核。此前误加入双语工作稿的本轮组件段和附录I已撤回，不再表述为已落稿。历史“B区待补”应区分为数据已齐、文案未定。既有锁定回复主体不变。


2026-11-13建立。本文件是新的逐项问答汇总，仅纳入用户审核的内容；替代A45作为后续回复工作入口。锁定主体不等于完整回复可提交。原稿和工作论文MD未因本次建档改动。

## 全局写作规则

### T9JT跨问题回复组织备忘（2026-11-14锁定组织视角；内部分析，不认定审稿人动机）

逐项回复保持独立；本段仅供最后组织总起使用，不提前宣布所有问题已解决。不能把批评全部归因于误解，也不能推断审稿人不懂领域或有意拒稿。坚定程度来自原文依据、匹配设计与实际结果，不来自态度对抗。

| 可能的理解分歧（待逐题核对） | 对应原问 | 应澄清的事实／研究定位 | 仍需实证回答的部分 |
|---|---|---|---|
| 将条件状态演化研究等同于端到端业务预报验证 | 3.2应用、3.5天气、3.6预处理 | 给定天气、不完整卫星历史、生成状态复用是当前明确设定；标准质量控制不等于输入完美 | 真实预报误差、观测更新、超100天的效果未验证，不能由设定解释替代 |
| 将标准预测排名视为全文唯一评价目标 | 3.2只追平直接、3.4精度 | 直接预测精度与生成状态的后续预测价值是互补评价；续预测需相对自身直接误差及匹配控制解释 | 标准精度仍须如实报告；新模型、核心配对种子待验收 |
| 将世界模型定位理解为必须覆盖所有波段或已得到生态机制 | 3.8 NDVI、3.10生态意义 | 本文以植被动态为观测任务，通过状态演化与后续预测用途论证模型定位 | 不声明完整环境状态、因果生态规律或未验收应用价值；状态分析仍需完成 |
| 混合训练机制对照、测试时干预与结构重训消融 | 3.4消融、3.7状态 | C1/C0R为独立训练对照；干预回答功能依赖；结构删除需匹配重训 | 一致性与组件证据不能靠术语澄清代替，按A47补充 |
| 贡献表述未把已有监督原则与具体研究发现分开 | 3.1 Deep-OSG、3.3外部比较 | 承认先前监督形式，解释不完整观测、天气驱动状态及匹配科学问题 | 外部方法比较、简单替代与结果稳定性属于真实证据需求 |

总起（中文，主体锁定；最终结果验收后补具体发现）：感谢您对方法贡献、实验依据和实际用途提出的具体意见。SpanWorld关注给定天气驱动下的遥感状态演化：从不完整历史观测形成潜在空间状态，并通过其对后续真实卫星观测的预测检验生成状态的价值。围绕这一目标，我们同时考察标准预测表现，以及在全部目标日期均受到直接监督时，训练路径对生成状态后续预测能力的影响。下面结合任务设定、方法设计和实验证据，逐项回应您的问题。

Opening (English; body locked, specific findings pending verification): Thank you for your detailed comments on the methodological contribution, empirical evidence, and practical value. SpanWorld studies weather-driven state evolution in remote sensing: inferring latent spatial states from incomplete observation histories and evaluating generated states through their predictions of subsequent real satellite observations. With this goal, we examine both standard forecasting performance and how training paths affect subsequent prediction from generated states when every target date already receives direct supervision. Below, we address your concerns individually through the task formulation, model design, and empirical evidence.

语气锁定：立场清楚、证据具体、措辞尊重。不对外使用“审稿人误解/不懂”“这不是额外待遇”“应当区分”等纠正式措辞；通过定义、引用和结果自然说明区别。上述五条理解分歧锁定为组织检查线索，不锁定为审稿人的真实意图或事实错误。总起不暗示尚未验收的补充实验完成，不替代逐项回答。

## T9JT天气来源与预报误差 — A39 3.5（2026-11-14主体锁定）

### 原问与翻译

> The weather data seems to be observed rather than forecast, and the paper does not say where it comes from.
>
> Where does the future weather come from? It looks like observed data rather than forecasts. If so, how would performance change with real weather forecasts, or with noise added to the weather?

> 天气似乎来自观测而非预报，且论文没有说明来源。未来天气来自哪里？如果采用真实天气预报，或者向天气输入加入噪声，性能会怎样变化？

### 中文回复

感谢您提出天气来源及其对实际预测影响的问题。我们使用GreenEarthNet提供的E-OBS气象站观测插值数据，包括预测窗口对应的天气。GreenEarthNet原论文在§3.1公式(1)中将历史与未来天气定义为预测输入，并在§3.3说明其观测来源；本文沿用这一天气条件预测设定。

这一设定使我们能够研究给定天气驱动下的植被状态演化：从不完整卫星观测形成的潜在空间状态，在推进后能否继续支持真实后续观测的预测。核心匹配实验使用相同天气、架构与直接目标监督，考察监督经过的状态转移路径是否影响生成状态的后续预测价值。这为理解天气驱动的遥感世界模型如何学习使用自身生成的状态提供了受控证据。

真实天气预报的误差如何影响植被预测，是将这一能力用于预报驱动应用时的重要问题。目前我们尚未直接评价业务天气预报或加噪天气下的性能。已有天气替换分析考察模型对天气条件的依赖，不能据此量化真实预报误差造成的变化。本文的结果因此支持给定天气条件下的状态续预测能力；其在预报误差下的稳健性仍需进一步检验。

### English response

Thank you for asking about the source of the weather inputs and their implications for forecasting in practice. We use the E-OBS interpolated meteorological station observations provided with GreenEarthNet, including weather over the prediction window. The GreenEarthNet paper defines historical and future weather as prediction inputs in Section 3.1, Eq. (1), and describes their observational source in Section 3.3. Our evaluation follows this weather-conditioned forecasting setting.

This setting allows us to study vegetation-state evolution under given weather forcing: whether latent spatial states inferred from incomplete satellite observations remain useful for predicting subsequent real observations after being advanced by the model. Our matched experiments use the same weather inputs, architecture, and direct target supervision to examine whether the state-transition paths through which supervision is applied affect subsequent prediction from generated states. This provides controlled evidence about how weather-driven remote-sensing world models learn to use their own generated states.

How weather forecast errors affect vegetation predictions is an important question for forecast-driven applications of this capability. We have not directly evaluated operational weather forecasts or noise-corrupted weather inputs. The existing weather-replacement analysis examines dependence on weather conditions and does not quantify the effects of real forecast errors. Our findings therefore support state continuation under given weather conditions; robustness to forecast errors requires further evaluation.

### 修改位置与提交状态

2026-11-14已执行：双语论文工作副本§4.1中英各插入E-OBS来源一句，沿用span.revision蓝色标记。反向还原核对仅这两处插入；原v23 SHA256仍为332c9e8c1ce9ded30cc23e129a98a8f6f773e3a1a11329f8a7b46627d00c8cbe。未改摘要/引言/方法，LaTeX/PDF尚未同步。原稿天气替换证据与新版结果分开，最终验收后核对引用是否仍对应；不新增天气噪声/业务预报任务，不将观测天气称为无误差真值。基准证据：https://arxiv.org/html/2303.16198 。最终匹配设置须与验收版本一致。

当前可追加的完成句（中文）：我们已在双语修订工作稿§4.1中明确注明天气数据的来源。

Current revision statement: We have explicitly identified the source of the weather inputs in Section 4.1 of the bilingual revision working draft.

正式提交时须核对LaTeX/PDF实际完成后，再将工作稿称谓改为修订论文；不提前宣称PDF完成。

总起不能替代逐问回答，不将EO-WM比较说成解决所有外部多步方法比较，不将给定天气下匹配有效性外推为预报噪声下仍有效。最终仅按实际完成证据写“已补充”。天气题可用基准原文§3.1公式(1)与§3.3作为具体依据：https://arxiv.org/html/2303.16198 。前者明确历史及未来天气为输入，后者说明E-OBS观测插值来源；遵循基准不是豁免鲁棒性问题的理由。

正文和回复不使用“SpanWorld采用／基于Contextformer的预测骨干”及同义表达；方法直接描述结构，比较直接回答区别；保留必要来源引用与事实披露。逐题回答，不主动混入其他问题。界面讨论先给中文，归档同时保留英文。完成态仅在实际修改/验收后使用。

## 主线状态

2026-11-14用户已锁定后续推进顺序与操作边界，完整规则见A39的后续推进主线。当前等待用户确认最终模型、提供结果或指定下一项；本轮不再改稿。先验收结果，再逐项更新双语稿/回复，最后统一审计与LaTeX/PDF同步。

最新主线（2026-11-14）：已确认且不依赖新结果的正文修改已完成本轮对账；3.3外部方法的附录说明/结果与§4.1指引已补齐，3.11两处局部压缩已完成。明细见A39落稿对账。多种子、最终精度、消融、状态分析、成本及新版天气证据仍待验收，后续按用户确认的结果推进。LaTeX/PDF与回复内部去重未完成。以下旧日期进度为历史记录，以本段为准。

最终去重路线已接受：先完成各题回复和已验收结果，再按每位审稿人连续阅读审计。总起文案可选，没有总起每条也须读懂。跨审稿人允许必要重复；同一审稿人保留必要短句和从不同角度解释同一证据，压缩重复背景、完整科学问题及贡献总结。只局部优化已认可版本，不全面重写。每批先提供原问/翻译、当前完整回复、具体拟删改及理由、修改后完整回复；用户审核后才修改。当前不启动全篇去重。论文正文的重复审计与回复去重分别验收，不能混称完成。

## T9JT写作重复与清晰度 — A39 3.11（2026-11-14主体锁定；双语MD已落实）

### 原问及翻译

> The writing is repetitive and hard to follow.

> 写作重复，难以理解。

### 中文回复（最终稿同步后使用）

感谢指出这一表达问题。我们对方法说明与实验论证进行了针对性修订，以减少重复并使各项设计与证据之间的关系更加清楚。第3.1节明确了初始状态、天气驱动转移、状态读出与基础预测之间的连接，并统一了相应术语和图注。§4.2合并了重复的结果解释，集中说明在目标日期均已接受直接监督、额外监督影像相同的条件下，监督路径如何影响生成状态的后续预测表现。我们保留了§4.3对端点预测与续预测的区分，并精简了实验末尾的总结，明确核心对照、未见时间划分和状态／天气干预各自提供的证据。上述修改使实验部分逐步推进论证，而不反复重述同一贡献；详细实现与补充设置仍保留在附录。

### English response (for use after synchronization of the final manuscript)

Thank you for pointing out this issue with the presentation. We have made targeted revisions to the method description and experimental discussion to reduce repetition and clarify the connections between the design choices and their supporting evidence. Section 3.1 clarifies how the initial state, weather-driven transition, state readout, and baseline prediction connect, with consistent terminology and corresponding clarification in the figure caption. In Section 4.2, we have consolidated repetitive interpretations of the results to focus on how supervision paths affect subsequent prediction from generated states when all target dates already receive direct supervision and the same endpoint images provide additional supervision. We have retained the distinction between endpoint prediction and continued prediction in Section 4.3 and shortened the closing experimental summary to clarify the evidence provided by the controlled comparison, unseen temporal partitions, and state/weather interventions. These revisions allow the experimental discussion to advance the argument progressively rather than repeatedly restating the same contribution; detailed implementation and supplementary settings remain in the appendix.

### 完成范围与提交条件

本次仅在双语论文工作副本替换§4.2结果解释后半段、§4.4末尾总结，中英共四处，沿用蓝色span.revision；具体修改前后全文见A39 3.11。§3.1、术语与图注为此前已落实的共用修改。本次保留摘要、引言、§4.3、结论、图像、数值及其他正文，不新增实验。原始v23与LaTeX/PDF不动；以上回复的完成时态在最终稿同步并核验后才可用于提交。新结果可能要求更新相关结果解释，但不能提前声称已验收。论文局部重复已按本次批准范围处理，不等于全篇或回复内部去重审计完成；后者继续遵循既定逐审稿人审核流程。

## T9JT生态学意义 — A39 3.10（主体锁定；最终结果待核对）

### 原问及翻译

> The paper offers no ecological insight as a physical-sciences paper.

> 作为一篇物理科学领域的论文，本文没有提供生态学见解。

### 中文回复

感谢您提出生态学意义方面的问题。本文关注植被动态建模中的一个具体问题：从不完整卫星观测形成的状态，在天气驱动下经过模型自身推进后，能否继续保留预测后续植被变化所需的信息。对于需要接续演化的模型，这关系到已有演化结果能否继续用于后续预测。

原稿的匹配实验提供了一个具体认识：两种训练方式的直接预测误差接近，但生成状态被再次用于预测时，其表现存在差异。比较保持架构、直接监督日期和额外端点观测一致；在这一受测设置下，全日期直接监督并未使两种训练方式获得相近的续预测表现，监督经过的状态路径仍然影响生成状态的后续预测价值。

对植被动态建模而言，这提示我们，除了评价从历史观测出发的预测精度，还需要通过后续真实观测检验模型生成状态的用途。原稿的状态替换与天气替换分析进一步考察了样本相关状态和对应天气的预测作用。本文由此提供了面向天气驱动植被模型的状态训练与评价依据；这些发现属于植被动态建模的方法性认识，尚不构成对具体生态机制的识别。

### English response

Thank you for raising the question of ecological insight. Our study addresses a specific question in vegetation dynamics modeling: whether states inferred from incomplete satellite observations retain information useful for predicting subsequent vegetation changes after being advanced by the model under weather forcing. For models intended for continued evolution, this concerns whether the results of earlier evolution remain useful for subsequent prediction.

The matched experiments in the original submission provide a concrete finding: the two training approaches have similar direct-prediction errors, but differ when their generated states are reused for subsequent prediction. The comparison holds the architecture, directly supervised dates, and additional endpoint observations fixed. In this evaluated setting, direct supervision at all dates did not produce similar continuation performance across the two approaches; the supervision path still affected the subsequent predictive usefulness of generated states.

For vegetation dynamics modeling, this suggests evaluating not only forecasting accuracy from historical observations but also the usefulness of model-generated states against subsequent real observations. State-replacement and weather-replacement analyses in the original submission further examine the predictive roles of sample-specific states and corresponding weather. Our study thus provides evidence informing state training and evaluation in weather-driven vegetation models. These are methodological findings for vegetation dynamics modeling, rather than identification of specific ecological mechanisms.

### 完成范围

当前仅锁定回复主体，不新增正文或实验；不声称发现生态规律、生态记忆或因果机制。最终按验收结果核对匹配条件、数值及原稿/新版身份。开头可能与其他回复重复，留到完整回复形成后的逐审稿人审计，先给用户修改前后全文，不能现在自行删减。最终结论部分是否需局部调整另行审计，不自动落稿。

最新：3.9回复主体已锁定，状态为“待补充／最终核对”，基于原稿84样本证据。不修改正文，不承诺新增评估；时间允许且结果验收后再更新。最终模型变化时核对旧分析保留方式与模型身份，不能混用新旧结果。

## T9JT天气样本与极端条件收益 — A39 3.9（主体锁定；待补充／最终核对）

### 原问及翻译

> The weather analysis uses only 84 samples, and the paper’s own test shows no extra benefit under hot-dry conditions.

> 天气分析仅使用84个样本，而且论文自身的测试未显示炎热干旱条件下的额外收益。

### 中文回复（基于原稿证据）

感谢您指出天气分析的样本规模及极端条件下的结果。原稿中的84个样本依据附录F.1所述的高温干旱阈值和天气有效性条件筛选得到，用于考察这一特定条件下模型对天气输入的依赖。我们认同，这一样本规模限制了结论对其他极端天气条件的推广。

对于天气驱动的遥感世界模型，一个重要的实证问题是：模型使用的天气是否有助于预测与之对应的真实植被变化。为检验这一点，我们保持模型、历史观测和评价目标不变，将实际天气替换为匹配供体天气或均值天气。两种替换均增加了受测热旱子集的预测误差，表明在这一子集上，与样本对应的天气提供了有用的预测信息。

至于这一作用是否在热旱条件下更强，供体天气替换分析未显示热旱与匹配正常样本之间有明确的效应差异，因此我们不据此主张热旱条件下存在更大的额外优势。本文由这些实验支持的发现是：天气条件对后续预测具有实际作用；结合生成状态的续预测与状态干预分析，我们分别检验外部驱动和生成状态对预测真实后续观测的价值。

### English response (based on the original submission)

Thank you for highlighting the sample size and the findings under extreme conditions. The 84 samples in the original submission were selected using the hot-dry thresholds and weather-validity criteria described in Appendix F.1 to examine the model's dependence on weather inputs under these specific conditions. We agree that this sample size limits generalization to other extreme-weather conditions.

An important empirical question for weather-driven remote-sensing world models is whether the supplied weather helps predict the corresponding real vegetation changes. To examine this, we held the model, historical observations, and evaluation targets fixed, replacing actual weather with either matched donor weather or mean-weather conditions. Both replacements increased prediction error on the evaluated hot-dry subset, indicating that sample-specific weather provided useful predictive information on this subset.

Regarding whether this effect is stronger under hot-dry conditions, the donor-weather replacement analysis did not show a clear difference between the hot-dry and matched normal samples. We therefore do not claim a larger additional benefit under hot-dry conditions on this basis. These experiments support the predictive role of weather conditions; together with continuation and state-intervention analyses, they examine the respective predictive value of external forcing and generated states against subsequent real observations.

### 待补充清单与使用条件

- 2026-11-14用户锁定主体，标记待补充；不修改正文、不追加训练或评估承诺，不写“已扩大样本/已补实验”。
- 时间允许且新天气结果验收后，可更新：模型与checkpoint身份、样本范围及筛选、天气替换效应及不确定性、热旱与正常条件的效应差、准确图表位置。补总体样本不能代替极端子集证据。
- 若不补评估，保留基于原稿的回复，但提交前必须确认该分析在最终论文中的保留方式并清楚标注模型身份；不能将旧模型结果表述为新模型结果。未解决前不可标为可提交终稿。
- 未显示明确差异不等于证明无效应，也不能无依据归因于样本量不足。天气替换支持预测信息作用，不证明生态因果机制，也不证明分段路径训练在极端天气下更有效。
- 原稿依据为附录F.1/F.2、表F1及相关图；不存在新增实验完成状态。最终全稿仍需同步实际表号与中英文。

2026-11-14继续推进：3.8中英回复已锁定，双语论文副本§3.1的NDVI选择说明已落实并标蓝；原稿未动，LaTeX/PDF未同步。下一项3.9天气样本/极端优势，先核对既定策略，最终数值待新版评估。

## T9JT为何只预测NDVI — A39 3.8（2026-11-14锁定并落实正文MD）

### 原问及翻译

> The world-model framing seems too broad. It predicts only NDVI, not the full image, and it’s not clear why only NDVI.
>
> Why focus only on NDVI? Since the paper frames SpanWorld as a remote-sensing world model, have you tried predicting the full multispectral image?

> 世界模型的表述似乎过宽。只预测NDVI而非完整影像，原因不清楚。为何选择NDVI？既然定位为遥感世界模型，是否尝试过完整多光谱预测？

### 中文回复

感谢您提出观测输出与世界模型定位之间的关系。本文聚焦天气驱动的植被动态，因此选择空间NDVI图像作为预测输出，并采用GreenEarthNet的植被预测协议进行评价。模型的历史输入包含多光谱观测，而预测目标是未来植被状况的空间变化。这使我们能够通过后续真实卫星观测，检验模型生成状态是否持续保留与植被预测相关的信息。

SpanWorld的世界模型定位体现在天气驱动的潜在状态演化及其后续使用：模型从不完整历史观测形成空间状态，将生成状态继续输入共享转移，并预测更晚的观测。本文进一步通过匹配实验，检验在所有目标日期均已受到直接监督时，监督路径是否仍影响生成状态的续预测表现。这里，NDVI是用于训练和检验状态预测价值的观测输出；仅凭NDVI预测准确性本身，并不足以确立上述状态能力。

本轮尚未验证完整多光谱影像预测。我们认同，扩展到多光谱输出能够进一步检验所学状态对其他遥感观测的预测价值。当前结论集中于植被动态及其状态续预测，不将潜在状态解释为环境全部属性的完整表示。

我们已在双语修订工作稿§3.1说明NDVI输出与植被动态研究目标的对应关系。

### English response

Thank you for asking about the relationship between the observation output and the world-model framing. Our study focuses on weather-driven vegetation dynamics, so we use spatial NDVI images as the prediction output and evaluate them under the GreenEarthNet vegetation forecasting protocol. Historical inputs include multispectral observations, while the prediction target is the spatial evolution of vegetation conditions. This allows us to test, against subsequent real satellite observations, whether model-generated states retain information useful for vegetation prediction.

SpanWorld's world-model formulation centers on weather-driven latent-state evolution and subsequent state use: the model infers spatial states from incomplete observation histories, feeds generated states back into a shared transition, and predicts later observations. Matched experiments further examine whether supervision paths affect continued prediction from generated states when all target dates already receive direct supervision. NDVI is the observation output used to train and evaluate this predictive value; NDVI forecasting accuracy alone does not establish the state capability described above.

We have not evaluated full multispectral image prediction in this study. We agree that extending the output to multiple spectral bands would further test the predictive value of the learned states for other remote-sensing observations. Our current conclusions concern vegetation dynamics and state continuation; we do not interpret the latent state as a complete representation of all environmental properties.

In Section 3.1 of the bilingual revision working draft, we have explained how the NDVI output relates to our focus on vegetation dynamics.

### 完成状态与边界

正文§3.1定义输出后，中英各插入一句（span.revision蓝色）；原句及其他方法内容不变。中文：“本文聚焦植被动态，选择空间NDVI图像作为观测输出，以后续真实卫星观测检验潜在状态的预测价值。”英文：“We focus on vegetation dynamics and use spatial NDVI images as the observation output, evaluating the predictive value of latent states against subsequent real satellite observations.” 已反向还原验证仅两处插入，原v23 SHA256仍为332c9e8c1ce9ded30cc23e129a98a8f6f773e3a1a11329f8a7b46627d00c8cbe。LaTeX/PDF未同步，正式回复的完成句须在PDF实际修改后调整。无多光谱新实验承诺，期刊计划不写入对外回复。最终匹配结果仍待验收。

2026-11-14最新：3.6预处理问题回复已锁定，不新增正文。尚未逐题定稿：3.7内部状态分析（待结果）、3.8 NDVI范围（可现在讨论）、3.9天气样本/极端优势（待更新评估）、3.10生态意义（可先定边界，结果解释待验收）、3.11重复写作（最终局部审计）。此前1.1/1.2/1.3、2.2/3.4及其他回复内数值仍待验收；外部比较论文落稿、最终LaTeX/PDF同步也未完成。当前不是全部问题结束或只剩等待。

## T9JT预处理与实际应用 — A39 3.6（2026-11-14锁定）

### 原问及翻译

> Inputs and targets both come from the preprocessed benchmark. This raises concerns about real-world impact, since real-time forecasting would face noisy satellite imagery.

> 输入与目标都来自预处理后的基准数据，这使实际应用意义受到质疑，因为实时预测会面对带有噪声的卫星影像。

### 中文回复

感谢您关注预处理条件下的结果如何对应实际遥感应用。本文采用GreenEarthNet的标准质量控制流程，以区分可用的植被观测与受云等因素影响的观测。历史输入仍存在缺测，模型需要结合观测掩膜，从不完整的卫星观测历史中形成用于预测的表示；目标侧的有效性掩膜则用于使监督和评分反映植被变化，而非云污染等观测干扰。相应的输入处理、监督和评价规则分别见附录A.1、A.2和B.1。

这一设置保留了本文关注的实际建模问题：在历史观测不完整、预测期间没有新增卫星观测的条件下，如何利用天气驱动推进潜在空间状态，并使生成状态继续支持后续预测。后续真实卫星观测用于监督和检验预测，而不作为预测时的影像输入。因此，基准中的质量控制为检验生成状态的后续预测价值提供了可比较的观测依据。

当前结果支持标准质量控制条件下的状态演化与续预测能力；对于不同的观测质量、掩膜误差或额外影像噪声，其影响仍需专门评价。

### English response

Thank you for asking how results obtained with preprocessed data relate to practical remote-sensing applications. We follow GreenEarthNet's standard quality-control procedures to distinguish usable vegetation observations from observations affected by clouds and other factors. Historical inputs still contain missing observations, and the model uses observation masks to form predictive representations from incomplete satellite histories. On the target side, validity masks allow supervision and scoring to reflect vegetation change rather than cloud contamination and other observation artifacts. The input-processing, supervision, and evaluation rules are described in Appendices A.1, A.2, and B.1, respectively.

This setting retains the practical modeling problem addressed in our study: how to advance latent spatial states under weather forcing and preserve their usefulness for subsequent prediction when historical observations are incomplete and no new satellite observations arrive during prediction. Subsequent real satellite observations provide supervision and evaluation targets, rather than image inputs at prediction time. Benchmark quality control thus provides a comparable observational basis for evaluating the subsequent predictive usefulness of generated states.

The current results support state evolution and continuation under these standard quality-control conditions. The effects of different observation quality, mask errors, or additional image noise require dedicated evaluation.

### 修改措施与验收边界

用户接受仅回复，不新增正文/附录段落；引用已有§4.1、附录A.1、A.2、B.1。未新增原始影像或噪声实验。缺测处理不等于对所有影像噪声鲁棒；有效性掩膜不等于完美标签；后续预测价值不等于完整生态状态或因果机制。最终模型验收后复核缺测与掩膜实现、附录描述及位置一致，现有回复不宣称新结果已完成。原稿与论文工作副本本轮均未修改。

2026-11-14：3.3外部比较问答中英主体与具体落稿方案已锁定（见文件末节及A39 3.3），最终模型比较、表号与论文落稿待补；不追加VegeDiff训练/深度排查。

1.1多种子/OOD待验收；1.2一致性替代待结果，噪声本轮不做；1.3成本待实测。2.1主体锁定、§3.1及A.1已落双语MD，最终配置及性能待补；2.2已确认暂缓，当前转2.3。

## tFYa（2分）—A39 2.1

### 原问与中文翻译

**问题原文**

> The writing is overly abstract, while key architectural details and comparisons with baselines are deferred to the appendix, making the main text insufficiently informative. These should be summarized in the main text to clarify the method and its performance.
>
> What distinguishes SpanWorld as a world model from a conventional vegetation forecasting model? Beyond this terminology, could you clarify the specific architectural and training contributions introduced over Contextformer?

**中文翻译**

> 写作过于抽象，关键架构细节和基线比较被放到附录，正文不足以清楚说明方法与性能，应在正文进行概括。
>
> SpanWorld 作为世界模型与传统植被预测模型有什么区别？除了术语，能否说明相对于 Contextformer 的具体架构和训练贡献？

### 回复主体：中文（锁定）

感谢您指出正文中架构与性能说明不够具体的问题。SpanWorld与Contextformer的关键区别，在于模型不仅从历史输入获得目标日期的预测，还显式构建并推进一个能够继续参与后续预测的空间状态。历史观测形成初始状态，给定区间的天气驱动共享变跨度转移，生成状态随后可以再次进入同一转移，继续预测更晚的观测。状态读出与基础预测共同形成完整输出。

这一区别对应引言中的核心科学问题：当训练已经监督模型从同一初始状态直接预测全部未来目标日期时，这是否足以使分段推进形成的状态继续支持准确的后续预测？换言之，在目标日期均已受到直接监督时，监督所经过的状态转移路径是否仍然影响续预测表现？我们不仅评价从历史直接预测的准确性，还让模型沿不同分段路径形成中间状态，再通过对后续真实卫星观测的预测检验该状态是否仍然有用。这也是本文“世界模型”定位所对应的具体建模与评价内容。

为此，分段路径训练保留所有目标日期的直接监督，并使真实终点影像的预测误差沿生成状态及其后续转移传播。匹配的直接终点控制使用相同架构、初始化、公共训练设置和额外监督端点，将比较集中在监督路径的选择上。这一设计区分了“目标日期受到过监督”与“到达该日期所经过的生成状态受到过后续使用的训练”。

### Response body: English (locked)

Thank you for pointing out that the main text does not make the architecture and performance sufficiently concrete. A key distinction between SpanWorld and Contextformer is that SpanWorld explicitly constructs and advances a spatial state that can be reused for subsequent prediction, in addition to producing forecasts at target dates from historical inputs. Historical observations establish the initial state; weather over the specified interval drives a shared variable-span transition; and the generated state can then enter the same transition again to predict later observations. The state readout and the baseline forecast jointly form the complete output.

This distinction motivates the central question stated in the Introduction: when training already supervises direct predictions from the same initial state at every future target date, is this sufficient for states generated through partitioned rollout to support accurate subsequent prediction? Equivalently, with direct supervision at all target dates, does the state-transition path through which supervision is applied still affect continued prediction? We therefore evaluate both direct forecasting accuracy and the predictive usefulness of intermediate states formed through different partitions, using subsequent real satellite observations as targets. This explicit modeling and evaluation of state evolution and reuse underlies our world-model framing.

Partitioned-path training retains direct supervision at every forecast date and propagates observed endpoint-image errors through generated states and their subsequent transitions. The matched direct-endpoint control uses the same architecture, initialization, common training settings, and additional supervision endpoints, focusing the comparison on the supervision path. This design distinguishes supervision of a target date from training the generated states along a path through their subsequent predictive use.

### 待完成后补入，以下不是可提交声明

- 实际修改后：中文说明§3.1补清计算连接、附录A.1同步实现，并给真实位置；英文 corresponding revision-location statement。不得在落稿前写“We have revised”。
- 结果验收后：中英两版同时加入标准精度与匹配续预测的关键结果及表格位置。不得沿用旧11%冒充新版。
- 表述中的匹配条件须由最终配置/权重/训练回执核对；尚未宣称新实验完成。

### 修改措施及依据

当前有效措施以A39第2.1节为准：必要公共架构连接；新版基础预测/初态天气依赖与初始化公式；附录A.1旧句；结果验收后正文性能概述。不改框架图、不扩展实现报告、不在本题讨论LISG。用户本轮授权后，§3.1文字、初始化公式及A.1已落实到双语工作MD并标蓝，日期条件使用 $\mathcal C$。LaTeX与最终配置/结果尚未同步。

### 科学问题一致性审计

原引言问“全日期直接监督是否足以支持分段生成状态的后续预测”；回复的“监督路径是否仍影响续预测”是对应的受控实验问题，含义一致而非逐字相同。回复先使用原引言问题，再解释路径比较，避免让读者误认为另提科学问题。不因统一问法擅改原引言。


编辑记录：A39第2.1已补中英文原句/拟替换句、公式候选、保留内容与待验收位置。本轮具体文案与公式已应用于双语论文工作MD；仅报告这一完成范围，不宣称PDF已修订。

当前顺序：先独立处理tFYa原第4问（A39 2.3）；锁定本题后再临时加入T9JT第1问，按其独立问法组织回复，不合并回复。

## tFYa原第4问 — A39 2.3（主体锁定，结果待补）

### 原问

> How does partitioned-path learning differ from Deep-OSG’s training formulation that supervises both direct and composed predictions using observed endpoint states?

> 分段路径学习与Deep-OSG中使用真实终点状态同时监督直接预测和组合预测的训练形式有何区别？

对应Weakness要求：说明方法贡献不能只停留在天气条件植被预测的应用迁移。

### 中文回复主体

感谢您提出这一关键比较。Deep-OSG研究自治动力系统的演化算子，并包含利用真实终点状态监督直接与组合预测的训练形式。SpanWorld的方法区别在于：它从不完整卫星观测历史推断潜在空间状态，以各时间区间的有序天气驱动共享可变跨度转移，并通过影像预测训练生成状态的后续使用。这里受监督的是状态读出与基础预测共同形成的完整影像，而潜在中间状态通过后续转移接收终点影像误差的梯度。

分段路径学习将这一状态使用方式纳入训练：在保留全部目标日期直接监督的同时，采样具有不同段数和边界的路径，使共享转移学习使用先前生成的状态。这一设计对应本文的核心问题：当所有目标日期都已接受直接监督时，这是否足以使分段生成的状态继续支持准确预测？

为检验这一问题，我们采用匹配的直接终点对照，控制架构、初始化、训练更新次数、全日期直接监督及额外终点影像，比较额外监督施加于直接路径和分段路径的效果。该实验区分了目标日期覆盖与生成状态后续使用的训练，检验监督路径在本文模型中的作用。

我们已在双语修订工作稿的相关工作中明确Deep-OSG与本文的关系，并将贡献列表第二项具体表述为通过生成状态的后续预测用途训练天气驱动的状态演化。

### English response body

Thank you for raising this comparison. Deep-OSG studies evolution operators for autonomous dynamical systems and includes a formulation that supervises direct and composed predictions using observed endpoint states. SpanWorld differs in its state formulation: it infers latent spatial states from incomplete satellite observation histories, drives a shared variable-span transition with the ordered weather for each interval, and trains the subsequent use of generated states through image prediction. Supervision is applied to the complete image prediction combining the state readout and baseline forecast, while latent intermediate states receive gradients from endpoint-image errors through subsequent transitions.

Partitioned-path learning incorporates this use of states into training. It retains direct supervision at every target date and samples paths with different segment counts and boundaries, training the shared transition to use previously generated states. This design addresses our central question: when all target dates already receive direct supervision, is that sufficient for states generated through partitioned rollout to support accurate subsequent prediction?

We test this question with a matched direct-endpoint control, holding architecture, initialization, training update count, all-date direct supervision, and additional endpoint images fixed, while applying the additional supervision to direct versus partitioned paths. This comparison separates target-date coverage from training generated states through their subsequent use, testing the role of the supervision path within our model.

In the bilingual revision working draft, we have clarified the relationship to Deep-OSG in Related Work and made the second contribution explicit: training weather-driven state evolution through the subsequent predictive use of generated states.

### 证据与提交状态

- 待补：最终模型配对续预测结果、相对自身直接预测的退化、种子与统计范围、实际表号。以上匹配条件须复核最终训练回执。
- 已完成：仅双语MD的Related Work末段与贡献第二项，标蓝；LaTeX/PDF未同步。正式提交时按真实完成版本修改最后一段，不能将工作MD完成等同于PDF完成。
- 不声称提出全新通用直接/组合监督原则，不声称C0R结果证明优于Deep-OSG；方法区别与受控发现共同支撑贡献。
- §3.2已有梯度解释完整，路径公式和解释暂不改。T9JT第1问下一步单独讨论，未处理。

## T9JT原第1问 — A39 3.1（两版结构已接受，结果待验收）

### 原问及翻译

> How does partitioned-path learning differ from Deep-OSG? A comparison with Deep-OSG, or with other multi-step training methods like scheduled sampling or latent overshooting, would help to see what is new here.

> 分段路径学习与Deep-OSG有何不同？与Deep-OSG，或scheduled sampling、latent overshooting等其他多步训练方法比较，有助于判断新意。

同时回应其“多步训练改善链式预测属于预期”的批评。本题独立回复，不直接复制tFYa。

### 版本A：不依赖一致性结果（中文）

感谢您指出方法比较与实证解释方面的问题。Deep-OSG包含使用真实终点监督直接与组合预测的训练形式。SpanWorld具体研究从不完整卫星观测形成的潜在空间状态，如何在对应区间天气驱动下持续支持后续影像预测。分段路径学习将这一状态使用方式纳入训练，使终点影像误差通过生成状态及其后续转移传播，同时保留全部目标日期的直接监督。

多步训练有助于多步预测提供了合理动机。本文进一步考察：当全部目标日期已经接受直接监督、额外终点观测也相同时，监督经过的状态路径是否仍影响续预测。匹配比较控制架构、初始化、训练更新次数、直接监督日期及额外终点影像，将额外监督分别施加于直接路径和分段路径。相对各模型自身直接预测误差的退化分析，进一步区分直接预测能力与生成状态的后续预测价值。

【待补最终C1/C0R结果、种子统计及位置。】当前比较支持本文设置下监督路径的作用，与所列外部多步训练方法的直接比较仍是证据缺口。相关工作与贡献表述已在双语MD修改，最终回复应按真实PDF完成状态给出位置。

### Version A: English

Thank you for highlighting the need for methodological comparison and a clearer interpretation of the evidence. Deep-OSG includes observed-endpoint supervision of direct and composed predictions. SpanWorld studies how latent spatial states inferred from incomplete satellite observations can support subsequent image prediction under interval-specific weather. Partitioned-path learning trains this use of states by propagating endpoint-image errors through generated states and subsequent transitions, while retaining direct supervision at every target date.

The expectation that multi-step training can benefit multi-step prediction provides a reasonable motivation. Our comparison further asks whether the supervision path still matters when all target dates already receive direct supervision and the additional endpoint observations are held fixed. The matched comparison controls architecture, initialization, training update count, directly supervised dates, and additional endpoint images, applying the additional supervision to direct or partitioned paths. Degradation relative to each model's own direct-prediction error further separates direct forecasting ability from the subsequent predictive usefulness of generated states.

[Pending: verified C1/C0R results, seed variability, and locations.] This comparison supports the role of the supervision path in our setting; direct comparison with the listed external multi-step methods remains an evidence gap. Related Work and the contribution statement have been revised in the bilingual MD; the final response must cite the actually revised PDF.

### 版本B：一致性验收后加入A版的段落（中文）

为进一步检验收益是否仅来自训练时使用分段路径，我们增加了同架构、同采样路径的一致性训练对照。该对照保留全部日期的直接观测监督，将额外分段终点损失替换为对同日期停止梯度的直接预测的匹配。在相同的【预算及种子】下，【填写共同后缀直接误差、续预测误差及退化】。这一结果表明【按实际结果解释】。该实验针对监督来源进行比较，不构成Deep-OSG、scheduled sampling或latent overshooting的完整复现。

### Version B: conditional addition to A

To further examine whether the benefit arises merely from training on partitioned paths, we added a consistency control with the same architecture and sampled paths. It retains direct observed-image supervision at every target date and replaces the additional partitioned endpoint loss with agreement to stop-gradient direct predictions at the same dates. Under matched [budget and seed], [report direct and continuation errors on the common suffix and degradation]. These results indicate [interpretation supported by the results]. This comparison targets the source of supervision; it is not a full reproduction of Deep-OSG, scheduled sampling, or latent overshooting.

### 使用条件与实验身份

B段为验收后模板，当前不宣称完成。已完成且有效的实验不能仅因结果不利而省略；相近或不利结果须据实解释。匹配条件须核对回执。四组仍为C1、C0R、一致性、基础框架/去动态分支；一致性是第3组，不是ABCD中的A/B。表格称“训练目标比较区”“组件比较区”，不再简称A/B区。ABCD选型不能替代C1/C0R三配对种子及补充目标对照评估。本题不新增正文重复段，不新增训练任务。

## tFYa原第3问 — A39 2.4（2026-11-14锁定）

### 原问

> In what application scenarios is a model supporting both direct forecasting and continued prediction from generated intermediate states particularly advantageous? How should one choose between these two prediction modes across different scenarios?

> 在哪些应用场景中，同时支持直接预测和从生成中间状态继续预测具有特别的优势？不同场景下应如何选择这两种模式？

### 中文回复

感谢您提出关于应用场景和模式选择的问题。两种模式使SpanWorld能够在同一模型中支持目标日期查询与模拟过程的接续演化。直接预测从历史形成的初始状态获得目标日期的结果；续预测则复用已经生成的中间状态，结合后续区间的天气继续推进。

一个潜在的应用场景是分阶段的天气情景分析：多条轨迹共享历史观测和前期天气过程，随后分别考虑持续干旱或降雨恢复等不同条件。采用直接预测时，各情景从初始状态出发，根据相应的完整天气序列计算目标日期的预测；采用续预测时，则可复用共同前期过程形成的潜在空间状态，再根据不同的后续天气分别推进。这使共同前期演化成为可以接续使用的模拟结果，并将不同天气情景下的后续演化建立在同一个生成状态上。

因此，直接预测适合获取给定条件下的目标日期结果，续预测适合接续已有模拟过程或从共同状态展开后续轨迹。本文通过后续真实卫星观测，检验支撑这种状态复用的预测能力，并通过匹配对照研究分段路径训练对该能力的作用。

### English response

Thank you for asking about application scenarios and mode selection. The two modes allow SpanWorld to support both target-date queries and continuation of a simulated trajectory within the same model. Direct prediction obtains a target-date forecast from the history-initialized state; continued prediction reuses a generated intermediate state and advances it with the weather for the subsequent interval.

One potential application is staged weather-scenario analysis: several trajectories share historical observations and an initial weather sequence, then consider different subsequent conditions, such as persistent drought or rainfall recovery. With direct prediction, each scenario is evaluated from the initial state using its full weather sequence up to the target date. With continued prediction, the latent spatial state formed through the common preceding evolution can be reused and advanced under each subsequent weather sequence. This makes the preceding evolution a reusable simulation result and places subsequent evolution under different weather scenarios on the same generated-state starting point.

Accordingly, direct prediction is appropriate for obtaining target-date outputs under given conditions, whereas continued prediction is appropriate for extending an existing simulation or branching subsequent trajectories from a common state. Our experiments use subsequent real satellite observations to evaluate the predictive ability needed for such state reuse, and matched controls to study how partitioned-path training affects this ability.

### 修改及验收状态（内部，不进入回复）

本题仅完善问答，不新增正文段落；未修改LaTeX/PDF，不使用本题“已修订正文”声明。潜在场景定位保留，删除独立的长限制声明；不声称分支应用已实测、必然更快或更准。新版基础预测也读取天气，状态前期复用不能等同于整模型计算复用；各情景的基础预测仍须正确计算。若加入数值须等待最终模型结果验收。正文既有科学问题和模式定义保留。下一题T9JT原第2问单独处理，不复制本回复。

## T9JT原第2问 — A39 3.2（2026-11-14回复主体锁定）

### 原问与翻译

> In exp. setup, multi-step prediction only matches direct prediction. Is there a case where continuing from a generated state actually helps, for example when a new observation arrives at day 50, or when forecasting beyond day 100?

> 在实验设置中，多步预测仅达到直接预测的水平。是否存在从生成状态继续预测真正有帮助的情形，例如第50天到达新观测，或者预测超过第100天？

### 中文回复

感谢您指出“续预测能够运行”与“续预测带来实际价值”之间的区别。我们理解，仅展示分段预测接近直接预测，还不足以证明新增观测接入或长时域预测等应用收益。

本文已经验证的收益，是在模型必须使用自身生成状态继续预测时，分段路径训练能够减轻预测退化。原稿表1中，两种训练方案均接受全部目标日期的直接监督，并使用相同的额外终点影像。它们从初始状态直接预测的误差接近，但在沿训练未见的15＋35天路径形成第50天状态、再预测第55—100天时，续预测表现出现明显差异。相对各模型自身直接预测误差的退化分析进一步支持这一结果。因此，接近直接预测并非本文收益的全部含义；关键在于，在目标日期和额外观测相同的条件下，模型生成的状态能否在后续使用中保持预测价值。

您提出的第50天接入新观测和超过100天预测，是检验进一步应用价值的具体方向。本文尚未评估这两种设置：当前实验在不接收新增遥感观测的条件下，考察基准100天窗口内的状态续预测。我们选择这一设置，是为了单独检验模型自身演化形成的状态，而不混入新观测带来的信息增益。

这项能力为接续已有模拟过程、从共同中间状态展开后续天气轨迹提供了基础。本文的贡献是建立这一状态演化与训练方式，并通过后续真实卫星观测检验生成状态的可用性；上述扩展应用则需要进一步验证。

### English response

Thank you for highlighting the distinction between being able to continue prediction and demonstrating its practical value. We recognize that showing partitioned predictions close to direct predictions does not by itself establish benefits for applications such as incorporating new observations or forecasting over longer horizons.

The benefit established in our experiments is reduced degradation when the model must reuse its own generated states for subsequent prediction. In Table 1 of the original submission, both training schemes receive direct supervision at every target date and use the same additional endpoint images. Their direct-prediction errors are close, but their continued-prediction performance differs after forming a day-50 state through the training-unseen 15+35-day path and predicting days 55–100. The degradation analysis relative to each model's own direct-prediction error further supports this finding. Thus, matching direct prediction is not the entire interpretation of the result: the key issue is whether generated states retain predictive value when subsequently reused, with target-date coverage and additional observations held fixed.

Incorporating a new observation at day 50 and forecasting beyond day 100 are concrete directions for testing further application value. We have not evaluated these two settings. Our current experiments examine state continuation within the benchmark's 100-day forecast window without additional remote-sensing observations. This setting isolates states formed through the model's own evolution, without introducing information gains from new observations.

This ability provides a basis for extending an existing simulation or developing subsequent weather trajectories from a common intermediate state. Our contribution is to establish this state-evolution and training formulation and evaluate the usefulness of generated states against subsequent real satellite observations; the proposed application extensions require further validation.

### 内部完成与待补状态

用户明确接受：本题直接回复，不新增观测更新、超100天或天气分支应用实验，不增加正文段落。暂以上述原投稿证据组织回复；最终用验收后的C1/C0R配对结果、退化及种子变异更新第二段并给准确表号，不将旧结果冒充新版。当前100天评价协议未覆盖更晚目标，不断言原始数据绝对没有更长序列。新观测用于推理更新不同于目标影像用于监督/打分；跨样本状态替换也不是观测同化。无新增训练任务、无正文完成声明。
## T9JT外部比较不足 — A39 3.3（2026-11-14锁定，落稿及最终结果待补）

### 原问及翻译

> The empirical validation rests on one in-house control, with no other multi-step methods or VegeDiff/VegSim for comparison.

> 实证验证主要依赖一个内部控制模型，缺少其他多步方法或VegeDiff／VegSim的比较。

### 中文回复主体（工作版；位置与最终模型结论待补）

感谢审稿人指出外部比较不足。我们认同，内部匹配控制能够检验分段路径训练的作用，但不能替代与近期外部方法的比较。本文关注天气驱动的遥感世界模型：从不完整历史观测形成潜在空间状态，并使生成状态继续参与后续预测。因此，评价需要同时回答两个问题：模型的标准预测表现如何，以及在所有目标日期均已受到直接监督时，监督经过的转移路径是否仍然影响生成状态的后续预测价值。

为补充外部预测参照，我们使用EO-WM的公开权重，在本文的GreenEarthNet测试分区和像素级评价协议下完成了评价。EO-WM同样研究天气条件下的多光谱遥感预测，其EarthNet数据体系与GreenEarthNet在卫星观测、气象驱动和数据设计上密切相关。其IID、OOD-T、OOD-S和OOD-ST RMSE分别为0.1578、0.1571、0.1679和0.1624。〔待补：最终SpanWorld相同协议下的对应结果、种子统计及一句客观比较；标准表实际位置。〕完整结果已纳入双语修订工作稿附录B，并说明公开权重来源、必要输入适配和训练条件差异。

对于审稿人提出的VegeDiff，我们依据官方代码开展了复现。在所核查的官方发布资源中，我们未找到可直接使用的自编码器权重，因此采用公开的EarthNet微调EO-VAE，并进一步在GreenEarthNet训练数据上适配。随后训练扩散预测模型100 epoch，按照验证集选择checkpoint。当前适配实现的IID、OOD-T、OOD-S和OOD-ST RMSE分别为0.4043、0.3882、0.4031和0.4030。我们已在双语修订工作稿附录B单独报告这些结果和适配设置。由于自编码器及潜空间发生变化，且训练—采样配置存在尚未排除的匹配问题，这些结果尚不足以代表原始VegeDiff的性能，因此不将其作为优于VegeDiff的证据。

我们也核查了VegSim。它与本文在天气驱动的潜在植被状态演化方面密切相关，但其公开任务采用minicube级NDVI序列和分位数预测，而本文评价逐像素空间预测。直接并列其原文指标不能形成同一任务下的比较。因此，我们已在双语修订工作稿附录B说明这一方法关联及输出粒度差异，而不把不同任务的数值放入同一精度排名。

这些补充使评价同时包含近期外部预测参照和针对训练路径的匹配检验。外部比较用于说明SpanWorld的预测表现所处的位置；内部控制则保持架构和直接目标监督一致，检验分段路径训练是否改善生成状态的后续预测价值。本文围绕这一状态能力提出具体问题，并通过真实后续卫星观测加以检验。〔待补：最终C1/C0R三个配对种子的续预测发现、波动范围及准确表号；不使用旧版约11%替代新版。〕

### English response (working draft; final results and locations pending)

Thank you for pointing out the lack of external comparisons. We agree that an internally matched control can test the effect of partitioned-path training but cannot replace comparisons with recent external methods. SpanWorld studies weather-driven remote-sensing world modeling: inferring a latent spatial state from incomplete observation histories and reusing generated states for subsequent prediction. Evaluation therefore needs to address both standard forecasting performance and whether the transition paths through which supervision is applied affect the subsequent predictive usefulness of generated states when every target date already receives direct supervision.

To provide an external forecasting reference, we evaluated publicly released EO-WM weights on our GreenEarthNet test splits using the same pixel-level evaluation protocol. EO-WM also studies weather-conditioned multispectral forecasting, and its EarthNet data setting is closely related to GreenEarthNet in satellite observations, meteorological drivers, and dataset design. Its RMSE is 0.1578, 0.1571, 0.1679, and 0.1624 on IID, OOD-T, OOD-S, and OOD-ST, respectively. [Pending: corresponding final SpanWorld results and seed statistics, a factual comparison, and the actual table location.] The full results are included in Appendix B of the bilingual revision working draft, with weight provenance, required input adaptations, and differences in training conditions.

For VegeDiff, we implemented and trained an adaptation based on the official code. We did not find directly usable autoencoder weights in the official resources we inspected, so we used the publicly released EarthNet-finetuned EO-VAE and further adapted it on the GreenEarthNet training data. We trained the diffusion predictor for 100 epochs and selected the checkpoint using the validation set. The current adapted implementation obtains RMSE values of 0.4043, 0.3882, 0.4031, and 0.4030 on IID, OOD-T, OOD-S, and OOD-ST, respectively. We report these results and adaptation settings separately in Appendix B of the bilingual revision working draft. Because the autoencoder and latent representation were changed, and a training–sampling configuration mismatch remains unresolved, these results are not sufficient to characterize the original VegeDiff method's performance. We therefore do not use them as evidence of superiority over VegeDiff.

We also examined VegSim. It is closely related to our work in weather-driven latent vegetation dynamics, but its released task predicts minicube-level NDVI sequences and quantiles, whereas our evaluation measures pixel-level spatial forecasts. Directly juxtaposing its published metrics would not constitute a comparison on the same task. We explain this methodological relationship and difference in output granularity in Appendix B of the bilingual revision working draft rather than rank metrics from different tasks together.

These additions provide both an external forecasting reference and matched tests of the supervision path. External comparisons establish the forecasting context for SpanWorld, while internal controls hold the architecture and direct target supervision fixed to test whether partitioned-path training improves the subsequent predictive usefulness of generated states. Our study poses a concrete question about this state capability and evaluates it against subsequent real satellite observations. [Pending: verified continuation findings and variability across three paired C1/C0R seeds, with the actual table reference; do not substitute the original approximately 11% result for the revised model.]

### 锁定措施、提交门槛与证据

2026-11-14最新呈现锁定：§4.1优先采用简短附录指引版，不在正文展开EO-WM数据相关性和选择理由；相关工作在VegeDiff与VegSim之间补一句EO-WM定位，中英具体文案见A39 3.3。正文性能概述留待结果验收后决定是否补一句，论文中不插入结果占位；最终仍需审计2.1正文性能说明是否得到回应。此调整不取消回复中的EO-WM数值和最终SpanWorld客观比较，也不取消完整附录结果。最新执行：上述不依赖新结果的内容已落双语工作稿；3.4精度与重训消融继续待验收，安排按A47。

- 2026-11-14已完成双语工作稿相关工作/引用、§4.1指引、附录B说明、EO-WM结果与VegeDiff独立披露，具体文案见A39；LaTeX/PDF未同步。当前回复明确称“工作稿”，正式提交前同步最终稿后再调整称谓。
- EO-WM回复报告四分区RMSE，最终加SpanWorld对应数值/均值±标准差及客观关系。排名不是必需；仅在最终全表、指标和统计口径确定后才可给特定指标/分区排名。不写笼统SOTA，不把公开预训练权重评价描述为同训练预算比较。
- 附录B2加入EO-WM行，修正“学习方法均三种子”的笼统图注，逐行标注独立训练种子、公开checkpoint及采样设置；生成样本数不等于独立训练种子数。
- VegeDiff在附录B单独说明和一行四分区结果，不进入正式优越性排名。必须简述实际CFG疑点：当前训练未执行条件随机丢弃，验证/测试使用零条件分支和CFG scale=2；尚无实验证明其造成的影响。不能写“尝试无果后确定原因为……”。
- 本题不追加VegeDiff训练或深入诊断。未做的CFG验证不能宣称已做；不依据其低分证明本方法更强。
- VegSim解释输出粒度；不声称它与本文不相关、不具备演化能力。外部标准预测比较不等于完整复现外部多步训练方法；一致性对照仍按A47、A49 3.1另行验收。
- 实验结果入口：执行交接/统一管理/scores_and_curves_20261113_2345.json；A08为结果总表，本文档不覆盖其结果管理职责。
- 官方依据：https://github.com/hku-sail/EO-WM ；https://github.com/NJU-LHRS/Official_VegeDiff ；https://arxiv.org/html/2606.21961v2 ；https://pure.mpg.de/rest/items/item_3620750_11/component/file_3621584/content 。
- 待补清单：最终模型身份/配置一致性；EO-WM与最终模型的同协议数值关系；核心配对种子结论；最终表号核对；LaTeX/PDF同步与核对。附录适配说明与蓝色落稿已完成，提交前清除全部占位。


## 2026-11-14消融预算表述锁定（用户确认）

正文、附录及回复统一表述：我们在匹配的公共训练设置下，对各组模型训练40轮后的表现进行消融比较。

English: We compare the models after 40 epochs of training under matched common training settings.

具体已接受正文文案及边界见A39同名小节。本次仅锁定措辞，不将40轮说成唯一实际训练总预算或事前预注册；原始证据与敏感性记录保留。正文/回复主体不展开总训练轮数。完整附录与问答仍按逐项审核后落稿，B区待补。


## T9JT原第5问 — A39 3.4（主体锁定并落稿；待补充，未关闭）

### 原问

> Why does SpanWorld score below Contextformer on the official metrics when Contextformer is its own backbone? Retraining without individual components would also help clarify which parts of the design matter.

中文：为什么SpanWorld在官方指标上低于Contextformer，尽管Contextformer是其骨干？移除不同组件并重新训练，也有助于说明设计中的哪些部分发挥了作用。

同时回应弱点：There is no real ablation study, only test-time changes to one trained model.（没有真正的消融研究，只有对同一个已训练模型进行测试时修改。）

### 中文回复

感谢您指出标准预测精度与组件贡献这两个相互关联的问题。针对精度方面的关切，我们在原有状态演化框架与分段路径监督原则下，进一步完善了训练配置及季节与天气条件的表达，并在相同测试划分和评分协议下重新评价。这些公共调整同步用于完整模型和直接终点对照，使更新后的比较仍能检验监督路径对生成状态后续预测的作用。

〔待补：D最终三种子结果验收后，补入四个划分的标准预测结果、相对Contextformer及PredRNN的客观比较，以及准确表号。说明实际改善和仍存在的差距，不将差距归因于未经验证的机制。〕

为进一步检验动态分支与标准预测表现的关系，我们补充了移除动态状态分支及其读出后重新训练基础预测模型的对照。在匹配的公共训练设置下比较训练40轮后的表现，完整模型在四个测试划分上均取得更高的R²，两组RMSE数值接近。完整设置与结果见附录I表I1B。这项实验补充了原有测试时干预：重训对照考察删除分支后模型重新学习的表现，测试时干预则检验已训练模型对状态及其动态更新的依赖。

我们同时在附录I表I1A报告训练目标比较，进一步检验简单一致性训练能否替代分段真实端点监督。两部分分别回答“移除动态分支后预测表现如何”和“如何训练生成状态的后续使用”，并与核心匹配续预测实验共同说明设计的作用。我们已在正文§4.4概括这些发现，并在附录集中呈现完整设置与结果。

### English response

Thank you for raising these related questions about standard forecasting accuracy and component contributions. To address the accuracy concern, we refine the training configuration and the representation of seasonal and weather conditions within the original state-evolution framework and partitioned-path supervision principle, and re-evaluate on the same test splits with the same scoring protocol. These common changes are applied to both the full model and the direct-endpoint control, so that the updated comparison continues to test how supervision paths affect subsequent prediction from generated states.

[Pending: after verification of the final three-seed D results, insert results on all four splits, an objective comparison with Contextformer and PredRNN, and the exact table reference. Describe improvements and remaining gaps without attributing them to unverified mechanisms.]

To further examine the relationship between the dynamic branch and standard forecasting performance, we add a control that removes the dynamic state branch and its readout and retrains the baseline-only model. After 40 epochs of training under matched common training settings, the full model has higher R² on all four test splits, with numerically close RMSE values between the models. Full settings and results appear in Appendix I, Table I1B. This experiment complements the original test-time interventions: retraining examines performance after relearning without the branch, whereas test-time interventions examine the trained model’s reliance on states and their dynamic updates.

We also report a training-objective comparison in Appendix I, Table I1A, testing whether simple consistency training can replace observed-endpoint supervision along partitioned paths. The two comparisons address performance after removing the dynamic branch and how to train the subsequent use of generated states, respectively. Together with the core matched continuation experiment, they clarify the roles of the design choices. We summarize these findings in Section 4.4 and present the full settings and results in the appendix.

### 提交条件

上述完成态目前仅对应双语MD；正式回复须待LaTeX/PDF同步核查。主模型已锁定D；精度结果及对应配置核验待补，整题未关闭。A区沿用此前锁定，不改其他题的回复。现有消融按D固定40轮解释，不与最终主表权重混用。


## 2026-11-15 用户锁定：后续以D为主模型

用户明确接受D的选择，后续写作、结果核对与审稿回复围绕D推进，覆盖此前“待B/D选型”的状态。B保留为选型与研究证据，不删除，不混入D主结果。

- 选型已定不等于结果全部验收；标准主结果与核心C1/C0R配对三种子继续按D的最终验收资料完成。回复中的精度占位改为等待D最终结果，不再等待B/D决策。
- 消融A/B继续使用已锁定D、seed42、固定第40轮口径；正文§4.4和附录I表I1A/B的已确认组织保持。
- 验证选优核心结果与固定40轮消融分开：当前8.76%与14.27%属于不同权重口径，不互相替换；最终数字以对应验收为准。
- 标准精度改善、绝对续预测误差变化、相对C0R收益分别报告，不写成全面提升，不把联合优化收益全部归于路径训练。已有不利结果与选模敏感性记录保留。
- 下一步先核对D的模型配置、标准结果、核心配对结果及现有状态/成本/天气证据，再按原问展示具体修改候选；用户审核后更新双语MD，最后统一LaTeX/PDF。主模型选择不授权新增训练或停止其他执行器。
- 本次仅同步决策与推进状态，不批量替换正文结果、原稿或回复主体。


### 2026-11-15 配套稿件状态更新（内部，不进入回复）

用户批准的A.4中英最小配置修订已落双语工作稿，具体前后对照见A39。2.1配置一致性及3.4精度段仍待D最终三种子、跨运行配置和共同初始化核验；未改已锁定回复主体，不将本次落稿视为整题关闭。


### 2026-11-15 A.1配套落稿状态（内部记录）

用户批准的季节输入与条件AdaLN精简说明已落实双语工作稿A.1及表A1，具体原文/改文见A39。对应2.1与3.4的方法描述依据得到补充；不改已锁定回复主体。最终精度、三种子及LaTeX/PDF仍待补充。


### 2026-11-15 A.2配套核验完成（内部记录）

用户批准的A.2文字修订已落双语稿：保留损失公式，通过文字补充q置零条件，修正跨设备有效计数与无监督像素处理。具体修改及归档来源见A39；不新增问答、不改已锁定回复主体。2.1/3.4仍按最终结果与其他待验收项管理，未关闭。
