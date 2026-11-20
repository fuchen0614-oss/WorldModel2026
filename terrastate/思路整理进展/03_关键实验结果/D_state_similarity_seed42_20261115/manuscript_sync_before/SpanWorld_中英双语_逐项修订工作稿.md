> 最新落稿状态（2026-11-15）：用户审核后授权，§4.4及附录I表I1A/B已汇入D固定40轮消融。精度回复待B/D确定与验收；其他旧结果仍待统一。LaTeX/PDF未同步。

> 本轮落稿状态（2026-11-14，不进入投稿）：已补§4.1附录指引、附录B外部方法说明、EO-WM四分区结果及VegeDiff独立适配结果；原有SpanWorld/控制与其他分析仍为待更新的旧结果，不代表最终新模型验收。多种子、消融、状态分析、成本及新版天气结果待验收后再替换。

> 修订工作说明（2026-11-13，不进入投稿）：2.1已在§3.1与附录A.1中英对应落稿，初始化公式同步更新。新增文字统一使用 `span.revision` 蓝色标记，公式使用 `\color{blue}`；最终可统一移除标记以关闭着色。此为新版full-base方法的局部修订，原有实验数字及其余配置仍待新版结果验收后同步，不代表整稿已完成版本一致性验收。原v23与v16保持不动，LaTeX尚未同步。

# SpanWorld: A Variable-Span World Model for Vegetation Forecasting

中文标题：SpanWorld：面向植被预测的变跨度世界模型

> 编辑说明（2026-09-25，v23，不进入投稿正文）：从完整双语v22复制，同步绘图会话最新交付的图2拼写修正版及PDF v16入口。图2红框中的segment已修正；图1、正文、图注、AI使用声明、参考文献与附录内容保持不变。
>
> 对应排版：完整英文PDF v16（未随本版归档：`ICLR2027完整稿_v16_图2拼写修正版替换_20260925/spanworld_iclr2027.pdf`）。前一版：完整双语v22（未随本版归档：`SpanWorld_全文完整稿_中英双语_v22_图1图2修正版替换_20260925.md`）。PDF正文9页、全文25页。所有旧版本完整保留。

阅读导航（编辑区）：[正文](#main-text) · [AI使用声明](#ai-use-statement) · [参考文献](#references) · [全部附录](#appendices)

<a id="main-text"></a>

## 中文摘要

世界模型通过学习环境的内部表示及其演化，为推演未来环境变化提供了建模途径。这些模型需要在推进过程中保持内部表征的预测价值。评价这一能力，需要同时考察从生成状态出发的继续预测，以及从历史出发的直接预测。为此，我们提出遥感世界模型SpanWorld，从卫星观测中学习植被动态，并通过天气条件下的状态转移推进模型自身的潜在空间状态。模型以给定未来天气为外部驱动，并以真实遥感影像检验后续预测。模型将不完整历史观测形成的基准预测与动态空间状态结合，通过共享变跨度转移，在有限预测窗口内支持直接预测与分段推进。我们进一步设计分段路径学习机制：保留模型从同一初始状态直接预测各未来目标日期的监督，同时采样不同的时间分段，以目标日期的真实影像监督经中间状态继续推进所得的预测。在GreenEarthNet的100天密集归一化差异植被指数（NDVI）图像预测任务上，我们设置采用相同模型架构的对照。两种模型均接受全时距直接预测监督。我们进一步使用相同端点影像，分别监督SpanWorld的分段推进预测和对照的直接预测。在IID评测中，两种方案经一种训练未见的时间分段推进至第50天，再从各自形成的中间状态分别预测第55—100天各目标日期的NDVI影像。对这些后续预测，分段路径学习使均方误差（MSE）较对照降低约11%，而两者直接预测同一时段的误差接近。

## English Abstract

World models learn internal representations of environments and their evolution, providing a way to forecast future environmental change. These models need to preserve the predictive value of their internal representations as rollouts progress. Evaluating this capability requires examining continued predictions from generated states alongside direct forecasts from history. To this end, we propose SpanWorld, a remote-sensing world model that learns vegetation dynamics from satellite observations and advances its latent spatial state through weather-conditioned transitions. The model uses given future weather as an external driver, and its subsequent predictions are evaluated against real remote-sensing imagery. SpanWorld combines baseline predictions derived from incomplete historical observations with a dynamic spatial state updated by a shared variable-span transition, supporting direct prediction and partitioned rollout within a finite forecast window. We further introduce a partitioned-path learning mechanism that retains supervision of predictions made directly from the same initial state at every future target date. It also samples temporal partitions and uses observed target images to supervise predictions made by continuing from model-generated intermediate states. On GreenEarthNet's 100-day dense normalized difference vegetation index (NDVI) image forecasting task, we compare SpanWorld with a control using the same architecture. Both models receive supervision of direct predictions at all forecast horizons. Using the same endpoint images, we additionally supervise predictions from partitioned rollouts in SpanWorld and direct predictions in the control. On the IID split, both models roll out to day 50 using one temporal partition unseen during training, then predict the image at each target date from day 55 to day 100 separately from their respective day-50 states. For these subsequent predictions, partitioned-path learning reduces mean squared error (MSE) by approximately 11% relative to the control, while direct-prediction errors over the same period remain similar.

## 中文引言

世界模型通过对环境演化进行内部推演，为未来预测、规划与决策提供了重要基础。对未来变化的推演能够帮助判断环境可能如何发展，并为后续行动的选择提供依据。世界模型从已有观测中学习环境的内部表示及其演化关系，使这些推演能够在模型内部进行。

已有研究利用学习得到的潜在状态动力学模型生成未来轨迹，支持行为学习与规划（[Hafner等，2020](https://arxiv.org/abs/1912.01603)；[Hansen等，2024](https://arxiv.org/abs/2310.16828)）。在通过状态转移持续推演的模型中，生成状态会再次参与后续转移，用于预测更远的未来（[Hafner等，2021](https://arxiv.org/html/2010.02193v4#S2)）。状态的预测作用涉及两个相互联系的层面：到达某个日期时产生的预测，以及从该日期的生成状态继续推进后产生的预测。前者反映模型对当前目标的预测表现，后者进一步检验生成状态能否继续承载后续预测所需的信息。因此，训练如何约束生成状态的使用，以及这种约束如何影响其后续预测能力，值得进一步考察。

天气驱动的植被变化为考察这种状态作用提供了具体场景。已有研究结合遥感观测、气象信息与空间条件预测未来植被变化，并进一步通过天气条件下的潜在状态递归推进开展动态模拟（[Benson等，2024](https://arxiv.org/abs/2303.16198)；[Iele等，2026](https://arxiv.org/html/2606.21961v2)）。这一场景具有相互关联的观测与驱动条件：遥感影像记录植被的空间分布及其变化，但可用历史往往不完整，需要从有限观测中形成预测所需的表示；随时间变化的天气为后续演化提供外部驱动；后续真实影像则为检验预测提供依据。在给定未来天气、预测期间不接收新增遥感影像的条件下，这些特点使模型生成状态的后续预测能力能够通过真实植被变化得到考察。

对于本文考虑的共享变跨度转移，模型可以跨越不同时间间隔接续预测，使同一目标日期既可以从初始状态直接到达，也可以经由中间状态分段到达。在这一设定下，本文关注的核心问题是：**当训练已经监督模型从同一初始状态直接预测全部未来目标日期时，这是否足以使分段推进形成的状态继续支持准确的后续预测？** 这种监督作用于从初始状态出发的预测。我们通过利用模型生成的状态预测后续观测，检验这种监督是否足以支持继续预测。监督覆盖哪些日期，与监督经过怎样的状态推进路径，需要被分别考察（图1）。

围绕这一问题，我们提出面向植被预测的遥感世界模型SpanWorld，通过天气条件下的共享变跨度转移，在有限预测窗口内支持植被图像的直接预测与分段推进。为使生成状态受到后续预测质量的约束，我们进一步设计分段路径学习机制：在保留全时距直接预测监督的同时，以真实端点影像监督从模型生成状态继续推进所产生的预测。在模型架构和监督所用端点影像相同的受控比较中，该机制在直接预测误差接近的情况下，减轻了模型推进后的继续预测退化。

## English Introduction

World models provide a foundation for prediction, planning, and decision-making by simulating environmental dynamics. These simulations help anticipate how an environment may evolve and inform subsequent actions. By learning internal representations and their dynamics from observations, world models enable possible future changes to be explored within the model.

Existing approaches use learned latent dynamics models to generate future trajectories for behavior learning and planning ([Hafner et al., 2020](https://arxiv.org/abs/1912.01603); [Hansen et al., 2024](https://arxiv.org/abs/2310.16828)). In models that perform continued rollout through state transitions, generated states serve as inputs to subsequent transitions to predict further into the future ([Hafner et al., 2021](https://arxiv.org/html/2010.02193v4#S2)). This distinguishes prediction at a target time from continued prediction using the state reached at that time. The former assesses the model’s output at the current target, while the latter examines whether the generated state retains information useful for subsequent prediction. It is therefore worth examining how training constrains the use of generated states and how these constraints affect subsequent prediction.

Weather-driven vegetation change provides a concrete setting for examining the predictive role of generated states. Previous studies combine remote-sensing observations, meteorological inputs, and spatial information to forecast vegetation change, with more recent work using weather-conditioned recurrent latent dynamics to simulate its evolution ([Benson et al., 2024](https://arxiv.org/abs/2303.16198); [Iele et al., 2026](https://arxiv.org/html/2606.21961v2)). This setting brings together complementary observations and external drivers. Remote-sensing imagery records the spatial distribution of vegetation and its changes over time, but historical observations are often incomplete, requiring predictive representations to be formed from limited observations. Time-varying weather provides an external driver of subsequent evolution, while later imagery provides observations against which predictions can be evaluated. With future weather given and no additional remote-sensing imagery supplied during prediction, these conditions allow the predictive value of model-generated states to be examined against observed vegetation change.

With the shared variable-span transition considered here, a model can continue forecasting over intervals of different lengths. The same target date can therefore be reached either directly from the initial state or through intermediate states along a partitioned rollout. Our central question in this setting is: **When training already supervises direct predictions from the same initial state at every future target date, is this sufficient for states generated through partitioned rollout to support accurate subsequent prediction?** This supervision is applied to predictions made from the initial state. We test whether this supervision is sufficient for continued prediction by using model-generated states to predict later observations. The dates covered by supervision and the state-transition paths along which it is applied therefore need to be examined separately (Figure 1).

To address this question, we introduce SpanWorld, a remote-sensing world model for vegetation forecasting. SpanWorld uses a shared, weather-conditioned variable-span transition to support direct prediction of vegetation imagery and partitioned rollout within a finite forecast window. We further introduce a partitioned-path learning mechanism that uses subsequent prediction quality to guide state learning. This mechanism retains supervision of direct predictions and uses observed endpoint imagery to supervise predictions made by continuing from model-generated states. Controlled comparisons using the same architecture and endpoint images for supervision show that this mechanism reduces degradation in continued prediction after rollout while direct-prediction errors remain similar.

## 中文贡献

本文的主要贡献如下：

1. **提出面向植被预测的遥感世界模型SpanWorld。** 通过天气条件下的共享变跨度转移更新动态空间状态，在有限预测窗口内支持密集植被图像的直接预测与分段推进。

2. <span class="revision" style="color:blue">我们提出分段路径学习，通过生成空间状态的后续预测用途训练天气驱动的状态演化。该方法在保留全部目标日期直接监督的同时，使真实终点影像误差沿采样分段路径传播，联合训练中间状态的形成及其后续使用。</span>

3. **揭示SpanWorld中监督路径对继续预测能力的影响。** 两种方案采用相同架构和全时距直接预测监督，并使用相同端点影像提供额外监督；区别在于额外监督作用于直接预测还是分段预测。在所测条件下，分段路径监督改善了SpanWorld从生成状态出发的继续预测表现，而两种训练方案的直接预测误差仍然接近。

## English Contributions

Our main contributions are as follows:

1. **We introduce SpanWorld, a remote-sensing world model for vegetation forecasting.** Its shared weather-conditioned variable-span transition updates a dynamic spatial state, supporting direct prediction of dense vegetation imagery and partitioned rollout within a finite forecast window.

2. <span class="revision" style="color:blue">We introduce partitioned-path learning to train weather-driven state evolution through the subsequent predictive use of generated spatial states. While retaining direct supervision at every target date, the method propagates observed endpoint-image errors through sampled partitioned paths, jointly training the formation and subsequent use of intermediate states.</span>

3. **We reveal how the choice of supervision path affects continued prediction in SpanWorld.** The controlled comparison holds the architecture and supervision of direct predictions at all forecast horizons fixed. Both schemes use the same endpoint images for additional supervision, applied to either direct or partitioned predictions. Under the evaluated conditions, partitioned-path supervision improves SpanWorld's continued prediction from generated states, while direct-prediction errors remain similar between the two training schemes.

## 中文相关工作

世界模型从已有观测学习环境表示与动力学，为未来预测、规划和行为学习提供基础。在模型驱动的控制与策略学习中，Dyna、PETS和MBPO分别体现了模型辅助规划、概率动力学与模型生成轨迹的作用（Sutton, 1991；Chua et al., 2018；Janner et al., 2019）。在视觉环境中，E2C、World Models、SimPLe、PlaNet及Dreamer系列通过像素或潜在状态预测支持控制、规划和行为学习（Watter et al., 2015；Ha and Schmidhuber, 2018；Kaiser et al., 2020；Hafner et al., 2019, 2020, 2021, 2023）；DeepMDP、MuZero与TD-MPC系列则围绕任务相关信息组织状态表示与动力学学习（Gelada et al., 2019；Schrittwieser et al., 2020；Hansen et al., 2022, 2024）。在序列建模方面，IRIS、TWM与STORM发展Transformer动力学，DIAMOND引入扩散生成，TWISTER采用多步对比预测（Micheli et al., 2023；Robine et al., 2023；Zhang et al., 2023；Alonso et al., 2024；Burchi and Timofte, 2025）。视觉表示学习也扩展至无需图像重建的目标和预训练特征上的动力学预测：DreamerPro采用原型表征学习，DINO-WM与V-JEPA 2-AC则基于预训练视觉表示学习动力学并支持规划（Deng et al., 2022；Zhou et al., 2025；Assran et al., 2025）。这一研究脉络强调，内部表示既服务于预测或决策，也为后续动力学推演提供信息基础。从观测出发的预测精度与模型推进后表示的后续预测价值，因此是相互关联而需要区分的问题。

天气条件下的地球观测预测将学习动力学与真实环境演化联系起来。循环记忆、结构分解、卷积预测、条件扩散与时空注意力等方法，为视频及地球系统预测提供了方法基础（Shi et al., 2015；Wang et al., 2017, 2018；Le Guen and Thome, 2020；Gao et al., 2022a, 2022b；Voleti et al., 2022）。EarthNet2021建立了由未来天气引导的卫星影像预测任务，后续研究进一步考察天气信息的预测作用与条件模拟价值（Requena-Mesa et al., 2021；Diaconu et al., 2022）。GreenEarthNet及Contextformer结合历史影像、气象与空间条件进行密集NDVI预测（Benson et al., 2024）；VegeDiff通过潜在扩散模型刻画植被变化的不确定性，生成未来植被影像（Zhao et al., 2025）；<span class="revision" style="color:blue">EO-WM采用天气条件潜在视频扩散模型，预测未来多光谱遥感观测（Luo et al., 2026）；</span>VegSim进一步构建天气情景条件下的植被世界模型，通过递归潜在动力学生成概率性NDVI轨迹（Iele et al., 2026）。这些进展将地球观测预测的研究范围，从未来影像估计拓展到天气条件下的动力学模拟。面对不完整历史、时变天气与空间异质性，本文在这一基础上进一步关注：在给定天气且没有新增遥感影像时，模型自身推进形成的表示能否继续支持真实后续植被变化的预测。

多步预测与动力学学习从训练目标和运行过程两个方面，研究如何保留面向未来的有效信息。Scheduled Sampling通过在真实输入与模型生成输入之间采样，处理训练与生成过程之间的差异；Professor Forcing则对齐教师强制与自由运行时的循环动力学（Bengio et al., 2015；Lamb et al., 2016）。CPC、SPR与TWISTER通过未来表征预测构建学习目标，PlaNet的latent overshooting与EfficientZero的表征一致性约束进一步提供多步推演的学习信号（van den Oord et al., 2018；Schwarzer et al., 2021；Burchi and Timofte, 2025；Hafner et al., 2019；Ye et al., 2021）。在物理模拟与神经方程求解中，训练状态扰动、面向模型生成状态的训练及预测细化，也被用于改善连续推进的稳定性与预测质量（Sanchez-Gonzalez et al., 2020；Brandstetter et al., 2022；Lippe et al., 2023）。在时间与演化算子建模方面，Neural ODE和Latent ODE描述连续时间状态演化，DeepONet与Fourier Neural Operator学习函数空间中的映射（Chen et al., 2018；Rubanova et al., 2019；Lu et al., 2021；Li et al., 2021）。<span class="revision" style="color:blue">Deep-OSG研究自治动力系统的变时间步长演化算子及其直接与组合演化的一致性，并包含利用真实终点状态监督两类预测的训练形式（Chen and Wu, 2023）。SpanWorld则面向不完整观测下、由天气驱动的潜在空间状态演化，将生成状态的后续预测能力作为训练与评价的中心：共享可变跨度转移使用各区间对应的天气推进状态，分段路径学习通过真实终点影像监督其后续使用。我们进一步在全日期直接监督和额外终点观测均受控的条件下，检验监督路径是否仍然影响生成状态的续预测表现。</span>

## English Related Work

World models learn representations and dynamics of environments from existing observations, providing a foundation for future prediction, planning, and behavior learning. In model-based control and policy learning, Dyna, PETS, and MBPO respectively demonstrate the roles of model-assisted planning, probabilistic dynamics, and model-generated trajectories (Sutton, 1991; Chua et al., 2018; Janner et al., 2019). In visual environments, E2C, World Models, SimPLe, PlaNet, and the Dreamer series support control, planning, and behavior learning through pixel or latent-state prediction (Watter et al., 2015; Ha and Schmidhuber, 2018; Kaiser et al., 2020; Hafner et al., 2019, 2020, 2021, 2023), while DeepMDP, MuZero, and the TD-MPC series organize state representation and dynamics learning around task-relevant information (Gelada et al., 2019; Schrittwieser et al., 2020; Hansen et al., 2022, 2024). For sequence modeling, IRIS, TWM, and STORM use Transformers to model temporal dynamics, DIAMOND introduces diffusion-based generation, and TWISTER adopts multi-step contrastive prediction (Micheli et al., 2023; Robine et al., 2023; Zhang et al., 2023; Alonso et al., 2024; Burchi and Timofte, 2025). Visual representation learning has also expanded toward reconstruction-free objectives and dynamics prediction over pretrained features: DreamerPro uses prototypical representation learning, whereas DINO-WM and V-JEPA 2-AC learn dynamics over pretrained visual representations and support planning (Deng et al., 2022; Zhou et al., 2025; Assran et al., 2025). Across these approaches, internal representations support prediction or decision making while carrying information needed for further rollout. Prediction accuracy from observations and the ability of model-generated representations to support subsequent prediction are therefore related but distinct questions.

Weather-conditioned Earth observation forecasting connects learned dynamics with the evolution of real environments. Methods based on recurrent memory, structured decomposition, convolutional prediction, conditional diffusion, and spatiotemporal attention have provided methodological foundations for video and Earth-system forecasting (Shi et al., 2015; Wang et al., 2017, 2018; Le Guen and Thome, 2020; Gao et al., 2022a, 2022b; Voleti et al., 2022). EarthNet2021 established satellite-image forecasting guided by future weather, and subsequent work further examined the predictive role of weather information and its value for conditional simulation (Requena-Mesa et al., 2021; Diaconu et al., 2022). GreenEarthNet and Contextformer combine historical imagery, meteorology, and spatial conditions for dense NDVI forecasting (Benson et al., 2024); VegeDiff models uncertainty in vegetation change with latent diffusion to generate future vegetation imagery (Zhao et al., 2025); <span class="revision" style="color:blue">EO-WM predicts future multispectral Earth observations using weather-conditioned latent video diffusion (Luo et al., 2026);</span> and VegSim further develops a vegetation world model conditioned on weather scenarios, using recurrent latent dynamics to generate probabilistic NDVI trajectories (Iele et al., 2026). Together, these advances extend the scope of Earth observation forecasting from future-image estimation to weather-conditioned dynamics simulation. Incomplete observation histories, time-varying weather, and spatial heterogeneity make vegetation forecasting a setting that calls for both representation learning and conditional dynamics modeling. Building on this foundation, we examine whether representations formed through a model's own rollout can support subsequent vegetation forecasting under given future weather, without additional remote-sensing observations.

Multi-step prediction and dynamics learning study how training objectives and rollout processes can preserve information useful for the future. Scheduled Sampling addresses the mismatch between training and generation by sampling between observed and model-generated inputs, while Professor Forcing aligns recurrent dynamics under teacher forcing and free running (Bengio et al., 2015; Lamb et al., 2016). CPC, SPR, and TWISTER construct learning objectives around predicting future representations, while latent overshooting in PlaNet and representation-consistency constraints in EfficientZero further provide learning signals for multi-step rollout (van den Oord et al., 2018; Schwarzer et al., 2021; Burchi and Timofte, 2025; Hafner et al., 2019; Ye et al., 2021). In learned physical simulation and neural PDE solving, perturbing states during training, training on model-generated states, and refining predictions have also been used to improve rollout stability and prediction quality (Sanchez-Gonzalez et al., 2020; Brandstetter et al., 2022; Lippe et al., 2023). For temporal and evolution-operator modeling, Neural ODE and Latent ODE describe continuous-time state evolution, while DeepONet and the Fourier Neural Operator learn mappings in function spaces (Chen et al., 2018; Rubanova et al., 2019; Lu et al., 2021; Li et al., 2021). <span class="revision" style="color:blue">Deep-OSG studies variable-time-step evolution operators for autonomous dynamical systems and consistency between direct and composed evolution, including a training formulation that supervises both predictions using observed endpoint states (Chen and Wu, 2023). SpanWorld focuses on weather-driven latent spatial-state evolution under incomplete observations, placing the subsequent predictive usefulness of generated states at the center of training and evaluation: a shared variable-span transition advances states using the weather for each interval, and partitioned-path learning supervises their subsequent use through observed endpoint imagery. With direct supervision at all target dates and additional endpoint observations controlled, we further examine whether the supervision path still affects continued prediction from generated states.</span>

## 中文方法

### 3 方法

SpanWorld旨在使模型自身推进形成的状态继续支持准确的后续预测。全时距直接预测监督训练模型从初始状态预测各个未来日期。为支持从生成状态继续预测，我们联合设计状态转移及其监督机制。天气条件下的共享变跨度转移用于推进初始状态及生成状态。我们提出分段路径学习，以真实端点影像监督从生成状态继续预测，并通过后续预测误差约束中间状态的形成。模型结构与学习机制分别见图2(a)和图2(b)。

#### 3.1 天气条件下的变跨度状态转移

为支持不同时间区间上的继续预测，SpanWorld以空间网格上的图像块特征表示动态状态。共享转移以各区间的天气与跨度为条件，复用此前推进形成的状态预测后续变化。

以历史窗口末端为时刻0，记历史上下文为 $\mathcal H$，其中包含不完整遥感影像、观测有效性及历史气象信息；静态地理条件记为 $G$。给定未来天气序列 $W_{1:n}$，模型预测随后 $n$ 个时间步的密集NDVI图像 $Y_{1:n}$，每步对应5天，期间不接收新增遥感影像。<span class="revision" style="color:blue">本文聚焦植被动态，选择空间NDVI图像作为观测输出，以后续真实卫星观测检验潜在状态的预测价值。</span><span class="revision" style="color:blue">模型使用PVT空间编码器和时间Transformer，在各自的输入条件下计算基础预测与用于状态初始化的历史特征：</span>

$$
\color{blue}{B_{1:n}=F_\phi(\mathcal H,G,W_{1:n},\mathcal C),\qquad S_0=P_\psi\!\left[H_\phi(\mathcal H,G,\mathcal C)_{\mathrm{last}}\right].}
$$

<span class="revision" style="color:blue">其中，$\mathcal C$ 表示已知日期特征；$F_\phi$ 和 $H_\phi$ 分别表示共享编码器的预测输出和特征输出，$P_\psi$ 为状态投影。基础预测使用历史观测与给定的未来天气。初始空间状态则由屏蔽未来影像和未来天气、保留日期特征的计算得到，将最后一个历史时刻的特征投影为 $S_0$。</span>

为处理不同长度的推进区间，我们以本次调用的起止时刻定义转移。设输入状态 $S_a$ 对应时刻 $a$，本次调用将其推进至时刻 $b$，生成状态 $S_b$，则

$$
S_b
=
T_\theta
\left(
S_a;\,W_{a+1:b},G,\Delta
\right),
\qquad
\Delta=b-a,\quad 0\leq a<b\leq n.
$$

这里，$T_\theta$ 是参数共享的状态转移，$\theta$ 表示其可学习参数，$\Delta$ 为本次推进的局部跨度，$W_{a+1:b}$ 为该区间内按时间排列的天气序列，$G$ 为静态地理条件。输入 $S_a$ 可以是历史初始化状态，也可以是此前推进生成的状态。

具体而言，共享GRU从零隐藏状态顺序编码本次天气区间，并取末端输出形成区间表示。天气表示与跨度嵌入广播至空间网格，与各位置的地理编码拼接融合；融合条件再与归一化的当前状态拼接，经多层感知机生成状态增量，再与原状态相加。该更新网络在空间位置和推进区间之间共享参数，使各次调用根据自身区间的条件更新状态，并通过动态状态传递前续推进形成的信息。

对于目标时刻 $t$，直接路径从 $S_0$ 调用一次共享转移，得到 $S_t^D$。分段路径沿时间划分 $0=\tau_0<\tau_1<\cdots<\tau_m=t$ 推进，其中 $m\geq2$，所得状态以上标 $P$ 标记：

$$
\begin{aligned}
S_t^D
&=
T_\theta(S_0;\,W_{1:t},G,t),\\
S_{\tau_0}^P
&=S_0,\\
S_{\tau_j}^P
&=
T_\theta
\left(
S_{\tau_{j-1}}^P;\,
W_{\tau_{j-1}+1:\tau_j},
G,
\tau_j-\tau_{j-1}
\right),
\qquad j=1,\ldots,m.
\end{aligned}
$$

分段状态对应当前选定的时间划分，最终状态为 $S_t^P=S_{\tau_m}^P$。两类路径连接相同的起止日期，并使用同一有序天气过程。完成首个推进区间后，后续转移以前一区间生成的状态为输入，通过共享动力学的重复调用支持继续预测。

共享读出算子 $O_\delta$ 将各位置的状态特征映射为图像块，重组后形成图像空间修正量 $C_t^r$（下称状态修正），再与同一目标日期的<span class="revision" style="color:blue">基础预测</span> $B_t$ 相加：

$$
C_t^r=O_\delta(S_t^r),
\qquad
\hat Y_t^r=B_t+C_t^r,
\qquad
r\in\{D,P\}.
$$

其中，$\delta$ 表示读出算子的参数，$\hat Y_t^r$ 为完整预测。直接与分段路径共享<span class="revision" style="color:blue">基础预测</span>、转移参数及读出算子，因此路径对预测的影响通过各自形成的动态状态体现。编码骨干及其来源、状态初始化、转移和读出细节见附录A.1。

时刻 $k$ 形成的状态 $S_k$ 可用于预测多个后续日期。对于每个目标日期 $t>k$，模型独立地从同一个 $S_k$ 出发，以区间天气 $W_{k+1:t}$、地理条件 $G$ 和跨度 $t-k$ 调用共享转移。所得状态的读出与目标日期的<span class="revision" style="color:blue">基础预测</span> $B_t$ 相加，使继续预测保留历史预测信息。

#### 3.2 分段路径学习

为将生成状态的后续预测价值纳入学习，SpanWorld在全时距直接预测监督之外，引入对从生成状态继续推进所得预测的分段端点监督。直接预测目标首先约束整个未来窗口的预测：

$$
\mathcal L_{\mathrm{dir}}
=
\ell_{\mathrm{seq}}
\left(
\hat Y_{1:n}^{D},Y_{1:n}
\right).
$$

其中，$\hat Y_{1:n}^{D}$ 为从初始状态 $S_0$ 分别预测各未来日期得到的图像序列，$Y_{1:n}$ 为对应真实影像，$\ell_{\mathrm{seq}}$ 为考虑有效观测与植被掩膜的序列均方误差。

我们进一步以真实端点影像监督分段路径上的预测，训练共享转移使用模型自身生成的状态。对于预设端点集合 $\mathcal E$，每个端点分别对应一个多段时间划分候选集合；每条候选路径的各段跨度均为正整数，总和等于该端点的时间索引。每次更新均从各端点的候选集合中独立、均匀采样一条路径，同时确定该路径的段数与切分位置。具体端点及候选集合见附录A.3。

模型从同一初始状态 $S_0$ 出发，沿各条采样路径重复调用共享转移，形成端点状态 $S_e^P$ 及完整预测 $\hat Y_e^P=B_e+O_\delta(S_e^P)$。分段路径损失定义为

$$
\mathcal L_{\mathrm{path}}
=
\frac{1}{|\mathcal E|}
\sum_{e\in\mathcal E}
\ell_{\mathrm{img}}
\left(
\hat Y_e^P,Y_e
\right).
$$

其中，$Y_e$ 为端点 $e$ 的真实影像，仅作为损失目标；$\ell_{\mathrm{img}}$ 为有效植被像素上的掩膜均方误差。路径上的状态均由模型生成。不同时间划分使共享转移在训练中利用不同前续区间形成的状态，预测真实的后续变化。

分段路径学习将中间状态置于后续预测的计算链中。训练不截断分段之间的梯度，端点误差通过后续转移回传至中间状态的形成过程，使这些状态在学习中承担支持后续演化及图像预测的任务。

联合学习目标为

$$
\mathcal L_{\mathrm{SpanWorld}}
=
\mathcal L_{\mathrm{dir}}
+
\lambda_{\mathrm{path}}
\mathcal L_{\mathrm{path}},
$$

其中，$\lambda_{\mathrm{path}}$ 控制分段路径监督的相对权重。两项损失均监督完整图像预测，分别覆盖从初始状态出发的直接预测，以及从生成状态出发的后续预测。具体掩膜、归一化及训练配置分别见附录A.2和A.4。

## English Method

### 3 Method

SpanWorld is designed to support accurate subsequent prediction from states generated during its own rollout. Direct supervision across the forecast window trains the model to predict each future date from the initial state. We jointly design the state transition and its supervision to support continued prediction from generated states. A shared, weather-conditioned variable-span transition advances both initial and generated states. We introduce partitioned-path learning, using observed endpoint images to supervise continued predictions from generated states and guide intermediate state formation through subsequent prediction errors. Figure 2 shows the architecture (a) and learning mechanism (b).

#### 3.1 Weather-Conditioned Variable-Span Transition

To support continued prediction over different time intervals, SpanWorld represents the dynamic state as a spatial grid of image-patch features. A shared transition conditioned on each interval's weather and length reuses states formed by earlier transitions to predict subsequent changes.

 Let time 0 denote the end of the history window. The historical context $\mathcal H$ comprises incomplete remote-sensing imagery, observation validity masks, and historical weather; $G$ denotes static geographic conditions. Given future weather $W_{1:n}$, the model predicts dense NDVI images $Y_{1:n}$ over the next $n$ five-day steps, without new remote-sensing imagery. <span class="revision" style="color:blue">We focus on vegetation dynamics and use spatial NDVI images as the observation output, evaluating the predictive value of latent states against subsequent real satellite observations.</span> <span class="revision" style="color:blue">The model uses a PVT spatial encoder and a temporal Transformer to compute the baseline forecast and the historical features for state initialization under their respective input conditions:</span>

$$
\color{blue}{B_{1:n}=F_\phi(\mathcal H,G,W_{1:n},\mathcal C),\qquad S_0=P_\psi\!\left[H_\phi(\mathcal H,G,\mathcal C)_{\mathrm{last}}\right].}
$$

<span class="revision" style="color:blue">Here, $\mathcal C$ denotes known calendar features; $F_\phi$ and $H_\phi$ denote the prediction and feature outputs of the shared encoder, respectively, and $P_\psi$ is the state projection. The baseline forecast uses historical observations and the supplied future weather. For state initialization, future imagery and future weather are masked out while calendar features are retained, and features at the final historical step are projected into $S_0$.</span>

To handle intervals of different lengths, we define each transition by its start and end times. Given an input state $S_a$ at time $a$, the transition produces a state $S_b$ at time $b$:

$$
S_b
=
T_\theta
\left(
S_a;\,W_{a+1:b},G,\Delta
\right),
\qquad
\Delta=b-a,\quad 0\leq a<b\leq n.
$$

Here, $T_\theta$ is the shared state transition with learnable parameters $\theta$, $\Delta$ is the length of the current interval, $W_{a+1:b}$ is the weather sequence over that interval in chronological order, and $G$ denotes static geographic conditions. The input $S_a$ can be either the state initialized from history or a state generated by an earlier transition.

A shared GRU encodes the current interval's weather chronologically from a zero hidden state. Its final output and the span embedding are broadcast over the spatial grid, concatenated with geographic features at each location, and fused. These features are concatenated with the normalized current state and passed through a multilayer perceptron (MLP), whose output is added to the input state. The network is shared across spatial locations and intervals. Each transition thus uses its own interval's conditions, while the dynamic state carries information from preceding transitions.

For target time $t$, the direct path applies the shared transition once to obtain $S_t^D$ from $S_0$. The partitioned path follows a temporal partition $0=\tau_0<\tau_1<\cdots<\tau_m=t$, with $m\geq2$, and its states carry superscript $P$:

$$
\begin{aligned}
S_t^D
&=
T_\theta(S_0;\,W_{1:t},G,t),\\
S_{\tau_0}^P
&=S_0,\\
S_{\tau_j}^P
&=
T_\theta
\left(
S_{\tau_{j-1}}^P;\,
W_{\tau_{j-1}+1:\tau_j},
G,
\tau_j-\tau_{j-1}
\right),
\qquad j=1,\ldots,m.
\end{aligned}
$$

The resulting states depend on the chosen partition, with endpoint state $S_t^P=S_{\tau_m}^P$. Both paths connect the same start and end dates under the same ordered weather sequence. After the initial transition, subsequent transitions take the preceding interval's generated state as input, supporting continued prediction through repeated application of the shared dynamics.

A shared readout $O_\delta$ maps each location's state features to an image patch. Assembling these patches yields an image-space correction $C_t^r$, added to the <span class="revision" style="color:blue">baseline</span> $B_t$ for the same target date:

$$
C_t^r=O_\delta(S_t^r),
\qquad
\hat Y_t^r=B_t+C_t^r,
\qquad
r\in\{D,P\}.
$$

Here, $\delta$ denotes the readout parameters, and $\hat Y_t^r$ is the complete prediction. Direct and partitioned paths share the baselines, transition parameters, and readout. The rollout path therefore affects the prediction through the dynamic state it produces. Appendix A.1 details the encoder backbone and its source, state initialization, transition, and readout.

A state $S_k$ formed at time $k$ can support predictions at multiple later dates. For each target date $t>k$, the model independently advances the same $S_k$ using the shared transition with weather $W_{k+1:t}$, geographic conditions $G$, and span $t-k$. The resulting state's readout is added to the target date's baseline $B_t$, retaining predictive information from history during continued prediction. 

#### 3.2 Partitioned-Path Learning

To learn states that support subsequent prediction, SpanWorld supplements supervision of direct predictions with endpoint supervision along partitioned paths. The direct objective constrains predictions over the entire forecast window:

$$
\mathcal L_{\mathrm{dir}}
=
\ell_{\mathrm{seq}}
\left(
\hat Y_{1:n}^{D},Y_{1:n}
\right).
$$

Here, $\hat Y_{1:n}^{D}$ is the image sequence obtained by making a separate prediction for each future date from the initial state $S_0$, and $Y_{1:n}$ contains the corresponding observed images. The sequence mean squared error $\ell_{\mathrm{seq}}$ accounts for observation validity and vegetation masks.

We additionally supervise predictions along partitioned paths using observed endpoint images, training the shared transition to operate on model-generated states. Each endpoint in a predefined set $\mathcal E$ is associated with a candidate set of temporal partitions with multiple segments. Each candidate consists of positive integer spans that sum to the endpoint's time index. At each training update, we independently sample one path uniformly from each endpoint's candidate set, thereby selecting its segment count and boundaries. The endpoints and candidate sets are listed in Appendix A.3.

From the same initial state $S_0$, the model repeatedly applies the shared transition along each sampled path, producing endpoint state $S_e^P$ and complete prediction $\hat Y_e^P=B_e+O_\delta(S_e^P)$. The partitioned-path loss is

$$
\mathcal L_{\mathrm{path}}
=
\frac{1}{|\mathcal E|}
\sum_{e\in\mathcal E}
\ell_{\mathrm{img}}
\left(
\hat Y_e^P,Y_e
\right).
$$

Here, $Y_e$ is the observed image at endpoint $e$, used only as a loss target, and $\ell_{\mathrm{img}}$ is the masked mean squared error over valid vegetation pixels. All states along the path are model-generated. Sampling different temporal partitions trains the shared transition to predict subsequent observations from states formed over different preceding intervals.

Partitioned-path learning places intermediate states in the computational path of subsequent predictions. Gradients propagate through every segment without truncation, allowing endpoint prediction errors to guide the formation of intermediate states through the subsequent transitions. These states are therefore learned to support later state evolution and image prediction.

The joint objective is

$$
\mathcal L_{\mathrm{SpanWorld}}
=
\mathcal L_{\mathrm{dir}}
+
\lambda_{\mathrm{path}}
\mathcal L_{\mathrm{path}},
$$

where $\lambda_{\mathrm{path}}$ controls the relative weight of partitioned-path supervision. Both losses supervise complete image predictions, covering direct predictions from the initial state and subsequent predictions from generated states. Appendix A.2 details masking and normalization, while Appendix A.4 provides the training configuration.

## 中文实验

### 4 实验

本节检验分段路径学习能否在直接监督已经覆盖全部未来目标日期的条件下，改善模型生成状态的继续预测能力。我们通过同架构受控比较考察监督路径的作用，通过训练未见时间划分检验共享转移的端点预测，并结合组件与输入干预分析动态状态及天气对预测的贡献。

#### 4.1 评测设置

我们在GreenEarthNet（Benson等，2024）的同分布（IID）、时间分布外（OOD-T）、空间分布外（OOD-S）及时间与空间联合分布外（OOD-ST）划分上评估SpanWorld。给定包含不完整遥感观测的50天历史上下文及预测窗口内的天气，模型以五天为间隔预测随后100天的NDVI影像，预测期间不接收新增遥感观测。<span class="revision" style="color:blue">天气驱动采用GreenEarthNet配套的E-OBS气象站观测插值数据（Benson et al., 2024）。</span>标准预测采用官方土地覆盖类别平衡的R²与均方根误差（RMSE）；继续预测采用样本等权平均的均方误差（MSE），在相同目标日期、样本和有效观测范围内进行比较。<span class="revision" style="color:blue">标准预测结果见附录B，涵盖既有预测基线及天气条件多光谱预测方法EO-WM。下文通过同架构匹配比较，进一步检验监督路径对生成状态后续预测价值的影响。</span>

#### 4.2 生成状态的继续预测能力

为检验监督路径的作用，我们将SpanWorld与将额外端点监督施加于直接预测的方案进行比较，称其为直接端点监督对照。两者采用相同架构和共同初始化，以相同更新次数训练，均接受全时距直接预测监督，并使用相同端点影像提供额外监督。区别在于额外监督作用于分段推进还是直接推进产生的预测。评测时，每个模型分别通过50天单段、25＋25天或15＋35天三条路径形成第50天状态，其中15＋35天为训练未见划分。随后，每个模型从各自固定的第50天状态出发，独立预测第55—100天各目标日期的NDVI影像，使用对应区间天气、地理条件及<span class="revision" style="color:blue">基础预测</span>。所有比较均使用相同的2,837个IID样本与后续目标窗口。

两种监督方式的直接预测误差接近，但生成状态被再次使用时，预测表现出现明显差异（表1）。从初始状态直接预测第55—100天目标时，对照与SpanWorld的MSE分别为0.041480和0.041285。在三条受测推进路径上，对照的继续预测误差均有所增加，而SpanWorld保持在接近自身直接预测误差的水平。对于训练未见的15＋35天划分，SpanWorld的继续预测MSE为0.041448，较对照的0.046550降低10.96%。<span class="revision" style="color:blue">在全部目标日期均已接受直接监督、额外监督影像相同的条件下，这一比较表明，监督所经过的状态推进路径仍会影响生成状态的后续预测能力。分段路径学习通过真实端点误差约束中间状态的形成及其后续使用，减轻了受测路径上的继续预测退化。</span>

**表1：共同后续时窗上的直接与继续预测。** 在相同的2,837个IID样本上评价第55—100天的预测。预测起点为初始状态或所示路径形成的各模型固定第50天状态。MSE按样本等权平均，差值为SpanWorld减对照。差值的95%区间来自固定模型下的配对地理组自助重采样。差值及相对改善幅度使用未舍入数值。15＋35天为训练未见划分。计算细则见附录C。

| 预测起点 | 直接端点监督对照 | SpanWorld | Δ MSE | 95% CI |
|:---:|:---:|:---:|:---:|:---:|
| 初始状态 | 0.041480 | **0.041285** | -0.000195 | [-0.000382, -0.000015] |
| 50天推进后 | 0.043713 | **0.041688** | -0.002025 | [-0.002680, -0.001300] |
| 25＋25天推进后 | 0.046488 | **0.041536** | -0.004952 | [-0.005948, -0.003868] |
| 15＋35天推进后 | 0.046550 | **0.041448** | -0.005101 | [-0.006107, -0.004009] |

<p align="center">* 每行较低的MSE加粗。</p>

这一差异也体现在预测的空间分布中（图3）。在所示案例中，两种方案的直接预测较为接近。经15＋35天推进后继续预测第100天，对照出现较大范围的NDVI偏高及绝对误差增加，而SpanWorld的预测分布和误差水平变化较小。该案例依据推进后退化差异从已有导出案例中选取（附录G），用于说明改善的空间表现。表1提供共同样本集合上的总体证据。

#### 4.3 未见时间划分下的端点预测

共享转移的分段使用还要求模型能够适应训练候选之外的时间组合。我们因此考察，改变推进段数与各段长度后，端点预测能否保持有效。我们将SpanWorld在九种训练未见时间划分下的预测（附录D），与第50、75、100天同端点的直接预测进行比较（图4a）。IID样本资格依据各端点的有效观测确定，MSE按有效像素汇总。九种划分下，分段与直接预测的MSE比值为0.992—1.023，说明端点精度接近直接预测。这一结果表明，共享转移的预测能力能够延伸至训练候选之外的受测时间组合。结合继续预测比较，两项评测分别考察分段推进的两个阶段：在到达的端点产生准确影像，以及利用形成的状态预测后续观测。前者检验变跨度转移的组合使用，后者评价这些转移所生成状态的后续用途。

#### 4.4 状态推进与天气信息的作用

为考察<span class="revision" style="color:blue">基础预测</span>之外的动态预测贡献，我们固定已训练模型，分别仅保留<span class="revision" style="color:blue">基础预测</span>，或将共享转移替换为恒等映射，使状态保持为初始状态。两种干预在四种划分上均提高了RMSE（表2）。以IID为例，完整模型的RMSE为0.1555，仅保留<span class="revision" style="color:blue">基础预测</span>时增至0.1708，采用恒等转移时增至0.2150。两种干预考察动态分支的互补作用：仅保留基准时，移除了由状态读出的图像修正；恒等转移则保留初始状态的读出，但省略了状态在对应区间天气下的演化。这些结果表明，状态修正及其动态更新均对完整模型的预测表现具有实际贡献，动态分支在<span class="revision" style="color:blue">基础预测</span>之外提供了有效的预测信息。

**表2：状态修正与动态转移的预测贡献。** 报告在同一已训练模型上进行推理干预后、完整100天预测窗口上的官方RMSE。完整指标与干预细节见附录E。

| 设置 | IID | OOD-T | OOD-S | OOD-ST |
|:---|:---:|:---:|:---:|:---:|
| 完整模型 | **0.1555** | **0.1509** | **0.1621** | **0.1542** |
| 仅<span class="revision" style="color:blue">基础预测</span> | <u>0.1708</u> | <u>0.1627</u> | <u>0.1755</u> | <u>0.1650</u> |
| 恒等转移 | 0.2150 | 0.2150 | 0.2196 | 0.2164 |

<span class="revision" style="color:blue">为检验简单训练目标能否替代分段真实端点监督，我们在匹配的公共训练设置下，对各组模型训练40轮后的表现进行比较。在seed42下，完整方案在三条受测路径上均取得最低的续预测MSE，其中训练未见的15＋35天路径较一致性替代降低3.19%。在此基础上，我们进一步通过移除动态状态分支并重新训练，考察该分支对标准预测表现的影响：完整模型在四个测试划分上的R²均更高，两组RMSE数值接近。两部分的完整设置与结果见附录I表I1。</span>

<p align="center">* 最佳结果加粗，次佳结果加下划线。</p>

继续预测同时使用生成状态和<span class="revision" style="color:blue">基础预测</span>。我们因此检验，在保留<span class="revision" style="color:blue">基础预测</span>时，生成状态是否仍提供有效的预测信息，以及这一作用是否依赖状态与当前样本的匹配。保持原样本的<span class="revision" style="color:blue">基础预测</span>、地理条件及后续天气不变，将其生成状态替换为另一个历史NDVI特征与土地覆盖组成相近样本的状态，并评估第55—100天的预测（图4b）。状态替换在四种划分上均增加了平均MSE，增量的95%置信区间均高于零。因此，即使<span class="revision" style="color:blue">基础预测</span>保持不变，替换状态仍提高了后续预测误差，说明原样本自身生成的状态对继续预测具有实际贡献。

天气替换进一步检验，使用各样本实际未来天气是否有助于预测。我们在84个OOD-T高温干旱样本上（附录F），保持模型、历史观测和评价目标不变，将实际天气替换为匹配正常天气样本的天气序列或归一化均值天气，并评估完整100天预测窗口（图4c）。两种替换均增加了平均MSE，其中均值天气造成的增幅更大。在受测子集上，使用与各样本对应的实际天气能够降低预测误差，说明天气条件提供了有效的预测信息。替换改变了共享转移接收的外部驱动，同时保留相同的真实观测目标。由此产生的误差增量将天气条件与真实未来植被变化的预测联系起来，补充了生成状态本身具有后续预测价值的证据。

<span class="revision" style="color:blue">这些评测从互补角度检验了SpanWorld：核心对照考察监督路径对续预测的影响，未见时间划分检验共享转移的组合使用，组件干预和输入替换则分析状态与天气对预测的贡献。</span>

## English Experiments

### 4 Experiments

We test whether partitioned-path learning improves continued prediction from model-generated states when direct supervision already covers all future target dates. Controlled comparisons within the same architecture examine the effect of supervision paths. Evaluations under unseen temporal partitions test the shared transition's endpoint predictions, while component and input interventions examine the contributions of dynamic states and weather.

#### 4.1 Evaluation Setup

We evaluate SpanWorld on the in-distribution (IID), temporal out-of-distribution (OOD-T), spatial out-of-distribution (OOD-S), and joint temporal-spatial out-of-distribution (OOD-ST) splits of GreenEarthNet (Benson et al., 2024). Given a 50-day historical context containing incomplete remote-sensing observations, together with weather for the forecast window, the model predicts NDVI images for the next 100 days at five-day intervals, without additional remote-sensing observations during prediction. <span class="revision" style="color:blue">Weather forcing is taken from the E-OBS interpolated meteorological station observations provided with GreenEarthNet (Benson et al., 2024).</span> We evaluate standard forecasting using the official land-cover-balanced R² and root mean squared error (RMSE). For continued prediction, we use mean squared error (MSE) averaged equally across samples, comparing predictions over the same target dates, samples, and valid observations. <span class="revision" style="color:blue">Standard forecasting results are provided in Appendix B, covering existing forecasting baselines and EO-WM, a weather-conditioned multispectral forecasting method. We next use an architecture-matched comparison to examine how supervision paths affect the subsequent predictive usefulness of generated states.</span>

#### 4.2 Continued Prediction from Generated States

To examine the effect of the supervision path, we compare SpanWorld with a control that applies the additional endpoint supervision to direct predictions (the direct-endpoint control). Both models use the same architecture and initialization, are trained for the same number of updates, receive supervision of direct predictions at all forecast horizons, and use the same endpoint images for additional supervision. The difference is whether this additional supervision is applied to predictions obtained through partitioned or direct rollouts. At evaluation, each model reaches day 50 through one of three paths: a single 50-day segment, 25+25 days, or 15+35 days. The 15+35-day partition is unseen during training. Each model then predicts the NDVI image at each target date from day 55 to day 100 independently from its own fixed day-50 state, using weather over the corresponding interval, geographic conditions, and the <span class="revision" style="color:blue">baseline</span> prediction. All comparisons use the same 2,837 IID samples and subsequent target window.

The two supervision schemes yield similar direct prediction errors, but their performance differs markedly when generated states are reused (Table 1). When predicting the day-55–100 targets directly from the initial state, the control and SpanWorld achieve MSEs of 0.041480 and 0.041285, respectively. Across all three rollout paths, the control's continued prediction error increases, whereas SpanWorld's error remains close to its own direct prediction error. For the 15+35-day partition, unseen during training, SpanWorld achieves an MSE of 0.041448, a 10.96% reduction from the control's 0.046550. <span class="revision" style="color:blue">With all target dates already directly supervised and the same endpoint images used for additional supervision, this comparison shows that the state-transition paths along which supervision is applied still affect subsequent prediction from generated states. Partitioned-path learning uses observed endpoint errors to constrain both the formation and subsequent use of intermediate states, reducing degradation in continued prediction along the evaluated paths.</span>

**Table 1: Direct and continued prediction over a shared subsequent window.** Predictions are evaluated on the same 2,837 IID samples for days 55–100. Predictions start from the initial state or each model's fixed day-50 state reached along the indicated path. MSE is averaged equally across samples. Differences are SpanWorld minus control. Their 95% intervals are computed by paired geographic-cluster bootstrap resampling with trained models held fixed. Differences and relative improvements use unrounded values. The 15+35-day partition is unseen during training. Calculation details are in Appendix C.

| Starting state | Control | SpanWorld | Δ MSE | 95% CI |
|:---:|:---:|:---:|:---:|:---:|
| Initial state | 0.041480 | **0.041285** | -0.000195 | [-0.000382, -0.000015] |
| After 50 days | 0.043713 | **0.041688** | -0.002025 | [-0.002680, -0.001300] |
| After 25+25 days | 0.046488 | **0.041536** | -0.004952 | [-0.005948, -0.003868] |
| After 15+35 days | 0.046550 | **0.041448** | -0.005101 | [-0.006107, -0.004009] |

<p align="center">* Within each row, the lower MSE is bolded.</p>

The spatial predictions illustrate this difference (Figure 3). In the example shown, the two schemes produce similar direct predictions. When predicting day 100 after a 15+35-day rollout, the control overpredicts NDVI over a substantial area and exhibits increased absolute error, whereas SpanWorld's prediction pattern and error level change less. This case was selected from the available visualizations based on the difference in degradation after rollout (Appendix G). It illustrates how the improvement appears spatially. Table 1 provides aggregate evidence over the shared sample set.

#### 4.3 Endpoint Prediction under Unseen Temporal Partitions

Using the shared transition in partitioned rollouts also requires it to accommodate temporal partitions unseen during training. We therefore examine whether endpoint predictions remain accurate when the number and lengths of rollout segments change. We compare SpanWorld's predictions under nine temporal partitions unseen during training (Appendix D) with direct predictions at the same endpoints: days 50, 75, and 100 (Figure 4(a)). IID sample eligibility is determined by valid observations at each endpoint, and MSE is pooled over valid pixels. Across these partitions, the ratio of partitioned to direct prediction MSE ranges from 0.992 to 1.023, indicating endpoint accuracy close to direct prediction. This result shows that the shared transition's predictive capability extends to the evaluated temporal partitions unseen during training. Together with the continued-prediction comparison, it addresses two stages of partitioned rollout: producing an accurate image at the reached endpoint and using the resulting state to predict later observations. The former examines the composition of variable-span transitions, while the latter evaluates the subsequent use of the states they generate.

#### 4.4 Contributions of State Evolution and Weather

To examine the dynamic contribution beyond the <span class="revision" style="color:blue">baseline</span>, we hold the trained model fixed and either retain only the baseline prediction or replace the shared transition with an identity mapping, keeping the state at its initial value. Both interventions increase RMSE on all four splits (Table 2). On IID, RMSE rises from 0.1555 for the full model to 0.1708 with only the <span class="revision" style="color:blue">baseline</span> and to 0.2150 with the identity transition. The two interventions examine complementary aspects of the dynamic branch. Retaining only the baseline removes the state-derived image correction, whereas the identity transition preserves the readout of the initial state but omits its evolution under the interval's weather. These results show that both the state correction and its dynamic update contribute to the full model's predictions, with the dynamic branch providing useful predictive information beyond the <span class="revision" style="color:blue">baseline</span>.

**Table 2: Predictive contributions of state correction and dynamic transition.** Official RMSE over the full 100-day forecast window under inference-time interventions on the same trained model. Full metrics and intervention details are provided in Appendix E.

| Setting | IID | OOD-T | OOD-S | OOD-ST |
|:---|:---:|:---:|:---:|:---:|
| Full model | **0.1555** | **0.1509** | **0.1621** | **0.1542** |
| History baseline only | <u>0.1708</u> | <u>0.1627</u> | <u>0.1755</u> | <u>0.1650</u> |
| Identity transition | 0.2150 | 0.2150 | 0.2196 | 0.2164 |

<span class="revision" style="color:blue">To test whether a simpler training objective can replace observed-endpoint supervision along partitioned paths, we compare the models after 40 epochs of training under matched common training settings. With seed 42, the full model achieves the lowest continuation MSE on all three evaluated paths, reducing MSE by 3.19% relative to the consistency alternative on the training-unseen 15+35-day path. We further remove the dynamic state branch and retrain the model to examine its contribution to standard forecasting: the full model has higher R² on all four test splits, with numerically close RMSE values between the two models. Full settings and results for both comparisons are reported in Appendix I, Table I1.</span>

<p align="center">* Best results are bolded, and second-best results are underlined.</p>

Continued prediction uses both a generated state and a <span class="revision" style="color:blue">baseline</span> prediction. We therefore examine whether the generated state provides useful predictive information in the presence of that baseline, and whether this contribution depends on matching the state to the current sample. We replace each sample's generated state with one from another sample matched on historical NDVI features and land-cover composition, while retaining the original sample's <span class="revision" style="color:blue">baseline</span> prediction, geographic conditions, and subsequent weather. We evaluate predictions for days 55–100 (Figure 4(b)). State replacement increases mean MSE on all four splits, with the 95% confidence intervals for these increases lying entirely above zero. Thus, even with the baseline prediction unchanged, replacing the state raises subsequent prediction error, indicating that the sample's own generated state contributes to continued prediction.

Weather replacement further tests whether using each sample's actual future weather improves prediction. On 84 hot-dry samples from the OOD-T split (Appendix F), we hold the model, historical observations, and evaluation targets fixed and replace actual weather with either the weather sequence of a matched sample with normal weather or normalized-mean weather. We evaluate the full 100-day prediction window (Figure 4(c)). Both replacements increase mean MSE, with a larger increase under mean-weather conditions. On this evaluated subset, using the actual weather associated with each sample lowers prediction error, indicating that weather conditioning provides useful predictive information. The replacement changes the forcing supplied to the shared transition while retaining the same observed targets. The resulting error increase links weather conditioning to the prediction of actual future vegetation, complementing the evidence that generated states themselves remain useful.

<span class="revision" style="color:blue">These evaluations examine complementary aspects of SpanWorld: the controlled comparison tests how supervision paths affect continued prediction, unseen temporal partitions test the compositional use of the shared transition, and component interventions and input replacements examine the contributions of states and weather.</span>

## 中文结论

### 5 结论

本文提出变跨度世界模型SpanWorld，在不完整遥感观测和给定未来天气条件下，通过共享状态转移支持植被变化的直接预测与分段推进。分段路径监督在保留全时距直接预测监督的同时，利用真实端点观测监督模型从自身生成的中间状态继续推进所产生的预测。在模型架构、初始化和监督所用端点影像相同的受控比较中，该机制在直接预测误差接近的情况下，减轻了受测路径上的继续预测退化。

这一比较表明，即使直接预测监督已经覆盖全部未来目标日期，监督所经过的推进路径仍会影响模型生成状态的后续预测能力。对于需要持续推进的世界模型，学习与评价应同时关注从观测出发的预测精度，以及模型自身生成的表征能否继续支持对真实未来的预测。

## English Conclusion

### 5 Conclusion

We present SpanWorld, a variable-span world model that forecasts vegetation change from incomplete remote-sensing observations given future weather. Its shared state transition supports direct prediction and partitioned rollout. Alongside supervision of direct predictions at all forecast horizons, partitioned-path learning uses observed endpoint images to supervise subsequent predictions from model-generated intermediate states. In controlled comparisons with the architecture, initialization, and endpoint images used for supervision held fixed, partitioned-path supervision reduces degradation in continued prediction across the evaluated paths, while the two training approaches yield similar direct-prediction errors.

These findings show that, even when supervision of direct predictions covers all future target dates, the rollout path along which supervision is applied affects subsequent prediction from model-generated states. For world models intended for continued rollout, learning and evaluation should consider both prediction accuracy from observations and the ability of model-generated representations to support further prediction of actual future change.

<a id="ai-use-statement"></a>

## AI使用声明 / AI Use Statement

### 中文

我们使用生成式AI工具辅助方法与评测代码的实现和中译英，并就研究方法、实验及作者对实验结果的解读提供反馈。其他用途包括论文起草与语言编辑、文献检索与梳理，以及图表和LaTeX文件的准备。研究假设及其修订思路由作者提出。作者已审核全部AI辅助工作，包括代码、参考文献、实验结果和论文文稿，并对论文的最终内容负责。

### English

We used generative AI tools to assist with the implementation of methods and evaluation code and with Chinese-to-English translation, and to provide feedback on methodology, experiments, and the authors' interpretation of experimental results. Additional uses included manuscript drafting and language editing, literature search and synthesis, and preparation of figures, tables, and LaTeX files. The research hypotheses and the ideas guiding their revision originated with the authors. The authors reviewed all AI-assisted work, including the code, references, experimental results, and manuscript, and take responsibility for the final content of this paper.

## 图注归档（编辑区，不构成新增正文节）

> 图 1–4 的中英图注共用同一组图号；正式排版时置于各自图片下方，不保留本编辑区标题。以下图注已按当前资产与附录协议核对。这里只登记已有资产，不生成、覆盖或重排图片。
>
> 图1沿用2.6版高清PNG；图2已替换为用户最新导出的2.6版拼写修正版。两图保持原始比例与正文宽度，图2红框中的segment已修正。Figure 2 uses the corrected export; manuscript text and captions remain unchanged.

### 图 1 / Figure 1

资产：研究问题示意图（历史路径：`D:/Mine Program/codexwork/CVPRAAAI投稿/WorldModel2026v2/terrastate/writing/SpanWorld后续写作/ICLR2027完整稿_v16_图2拼写修正版替换_20260925/figures/figure1_motivation.png`）。位置：引言的科学问题之后。

**图内文字定稿 / Final in-figure text（编辑记录，已替换2.6版图片）**

图1(b)顶部标题 / Panel (b) heading：

中文：**继续预测能力需要单独评价**

English: **Continued Prediction Requires Separate Evaluation**

英文建议分为两行，保留分面编号“(b)”：

Continued Prediction  
Requires Separate Evaluation

此标题强调继续预测需要单独检验，与下方直接预测和生成状态继续预测的对照相衔接。当前链接的PNG已替换为2.6版；以下图注保持不变。

**中文图注：世界模型场景与继续预测问题。**（a）动作条件视觉预测与天气条件植被预测。（b）即使直接预测准确，仍需单独评估从生成状态出发的继续预测。（c）SpanWorld 利用共享动力学、有序天气与保留的历史上下文进行直接预测及继续预测，期间不接收新增遥感影像。

**English caption: World-model setting and the continuation question.** (a) Action-conditioned visual prediction and weather-conditioned vegetation forecasting. (b) Even with accurate direct predictions, continued prediction from generated states requires separate evaluation. (c) SpanWorld uses shared dynamics, ordered weather, and retained historical context for direct and continued prediction without new remote-sensing imagery.

### 图 2 / Figure 2

资产：架构及学习机制图（2.6版拼写修正版）（历史路径：`D:/Mine Program/codexwork/CVPRAAAI投稿/WorldModel2026v2/terrastate/writing/SpanWorld后续写作/ICLR2027完整稿_v16_图2拼写修正版替换_20260925/figures/figure2_architecture.png`）。位置：方法概览，正文图 2a 对应架构、图 2b 对应学习机制。

**图内文字定稿 / Final in-figure text（编辑记录，已替换2.6版拼写修正版图片）**

图2(a)基准预测序列标签 / Panel (a) baseline-sequence label：

中文：**基准预测 \(B_{1:n}\)**

English: **Base Forecasts \(B_{1:n}\)**

其中，\(n\) 表示整个预测窗口的末端，与正文及图中列出的 \(B_1,B_2,B_3,\ldots,B_n\) 一致。图2(b)中的训练端点 \(e\in\{10,15,20\}\)，以及 \(S_e\)、\(\hat Y_e^P\)、\(Y_e\) 保留。

图2(b)红色虚线框说明 / Panel (b) red dashed-box text：

中文：每次调用 \(T_\theta\) 时，均使用对应区间的天气、地理条件 \(G\) 和时间跨度 \(\Delta\)。

English: Each call to \(T_\theta\) uses the corresponding weather segment, \(G\), and \(\Delta\).

英文建议分为四行：

Each call to \(T_\theta\) uses  
the corresponding  
weather segment,  
\(G\), and \(\Delta\).

\(G\) 为共享的静态地理条件，\(\Delta\) 为本次调用的推进跨度。当前链接的PNG已替换为2.6版拼写修正版，红框中的segment已正确显示。上述中英文与图中文字一致，正文图注保持不变。

**中文图注：SpanWorld 架构与分段路径学习。**（a）直接（D）与分段（P）推进共享天气条件动力学和读出模块；由状态读出的图像修正与<span class="revision" style="color:blue">基于历史观测及给定未来天气的基础预测</span>相加。（b）全时距直接预测监督与采样分段推进后的端点监督共同训练模型。未来目标影像仅作为预测的监督目标。

**English caption: SpanWorld architecture and partitioned-path learning.** (a) Direct (D) and partitioned (P) routes share weather-conditioned dynamics and a readout module; state-derived image corrections are added to <span class="revision" style="color:blue">baseline predictions conditioned on historical observations and the supplied future weather</span>. (b) Training combines supervision of direct predictions at all forecast horizons with endpoint supervision after sampled partitioned rollouts. Future target images serve only as supervision targets for predictions.

### 图 3 / Figure 3

资产：直接与继续预测案例（历史路径：`D:/Mine Program/codexwork/CVPRAAAI投稿/WorldModel2026v2/terrastate/writing/SpanWorld后续写作/ICLR2027完整稿_v16_图2拼写修正版替换_20260925/figures/figure3_prediction_routes.png`）。位置：4.2 的定性结果之后；案例与显示协议见附录 G。

**中文图注：一个改善明显的IID样本在第100天的直接与继续预测。** 继续预测使用各模型经15＋35天推进形成的状态。NDVI面板共用一套色标，绝对误差面板共用另一套色标。所有面板使用相同掩膜，灰色表示无效观测。超过0.45的误差仅在显示时饱和。

**English caption: Direct and continued day-100 predictions for a high-improvement IID example.** Continued predictions use each model's state after a 15+35-day rollout. NDVI panels share one color scale, and absolute-error panels share another. A common mask applies throughout, with invalid observations in gray. Errors above 0.45 saturate for display only.

### 图 4 / Figure 4

资产：未见划分及输入替换（历史路径：`D:/Mine Program/codexwork/CVPRAAAI投稿/WorldModel2026v2/terrastate/writing/SpanWorld后续写作/ICLR2027完整稿_v16_图2拼写修正版替换_20260925/figures/figure4_partition_interventions.png`）。位置：4.3–4.4；完整协议与结果分别见附录 D、E、F。

**中文图注：未见时间划分与输入替换。**（a）分段预测相对同端点直接预测的像素汇总MSE百分比变化。方括号表示各段天数，各组从上至下到达第50、75、100天。（b）状态替换引起的第55—100天样本等权MSE增量。（c）84个OOD-T高温干旱样本在完整100天窗口内的天气替换MSE增量。T/S/ST表示时间、空间及联合分布偏移，Mean weather表示归一化均值天气。（b,c）正值表示原状态或实际天气的误差较低，误差条为配对地理组bootstrap的95%置信区间。

**English caption: Unseen temporal partitions and input replacements.** (a) Percentage change in pooled endpoint MSE versus direct prediction at the same endpoint. Brackets show segment lengths (days). Groups reach days 50/75/100, top to bottom. (b) State-replacement increase in sample-averaged MSE for days 55–100. (c) Weather-replacement MSE increase over the full 100-day window on 84 hot-dry OOD-T samples. T/S/ST denote temporal, spatial, and joint distribution shifts. Mean weather denotes normalized-mean weather. In (b,c), positive values favor the original state or actual weather, and error bars show paired geographic-cluster bootstrap 95% confidence intervals.

<a id="references"></a>

## References

1. Eloi Alonso et al. *Diffusion for World Modeling: Visual Details Matter in Atari.* NeurIPS, 2024. [Paper](https://papers.nips.cc/paper_files/paper/2024/hash/6bdde0373d53d4a501249547084bed43-Abstract-Conference.html)
2. Mido Assran et al. *V-JEPA 2: Self-Supervised Video Models Enable Understanding, Prediction and Planning.* arXiv preprint arXiv:2506.09985, 2025. [Paper](https://arxiv.org/abs/2506.09985)
3. Samy Bengio et al. *Scheduled Sampling for Sequence Prediction with Recurrent Neural Networks.* NeurIPS, 2015. [Paper](https://proceedings.neurips.cc/paper/2015/hash/e995f98d56967d946471af29d7bf99f1-Abstract.html)
4. Vitus Benson et al. *Multi-Modal Learning for Geospatial Vegetation Forecasting.* CVPR, 2024. [Paper](https://arxiv.org/abs/2303.16198)
5. Johannes Brandstetter, Daniel E. Worrall, and Max Welling. *Message Passing Neural PDE Solvers.* ICLR, 2022. [Paper](https://openreview.net/forum?id=vSix3HPYKSU)
6. Maxime Burchi and Radu Timofte. *Learning Transformer-Based World Models with Contrastive Predictive Coding.* ICLR, 2025. [Paper](https://proceedings.iclr.cc/paper_files/paper/2025/hash/148c0aeea1c5da82f4fa86a09d4190da-Abstract-Conference.html)
7. Junfeng Chen and Kailiang Wu. *Deep-OSG: Deep Learning of Operators in Semigroup.* Journal of Computational Physics, 493:112498, 2023. [Published paper](https://doi.org/10.1016/j.jcp.2023.112498) · [Preprint](https://arxiv.org/abs/2302.03358)
8. Ricky T. Q. Chen, Yulia Rubanova, Jesse Bettencourt, and David Duvenaud. *Neural Ordinary Differential Equations.* NeurIPS, 2018. [Paper](https://proceedings.neurips.cc/paper/2018/hash/69386f6bb1dfed68692a24c8686939b9-Abstract.html)
9. Kurtland Chua, Roberto Calandra, Rowan McAllister, and Sergey Levine. *Deep Reinforcement Learning in a Handful of Trials using Probabilistic Dynamics Models.* NeurIPS, 2018. [Paper](https://papers.nips.cc/paper_files/paper/2018/hash/3de568f8597b94bda53149c7d7f5958c-Abstract.html)
10. Fei Deng, Ingook Jang, and Sungjin Ahn. *DreamerPro: Reconstruction-Free Model-Based Reinforcement Learning with Prototypical Representations.* ICML, 2022. [Paper](https://proceedings.mlr.press/v162/deng22a.html)
11. Codruț-Andrei Diaconu, Sudipan Saha, Stephan Günnemann, and Xiao Xiang Zhu. *Understanding the Role of Weather Data for Earth Surface Forecasting Using a ConvLSTM-Based Model.* CVPR EarthVision Workshop, 2022. [Paper](https://openaccess.thecvf.com/content/CVPR2022W/EarthVision/html/Diaconu_Understanding_the_Role_of_Weather_Data_for_Earth_Surface_Forecasting_CVPRW_2022_paper.html)
12. Zhangyang Gao et al. *SimVP: Simpler Yet Better Video Prediction.* CVPR, 2022a. [Paper](https://openaccess.thecvf.com/content/CVPR2022/html/Gao_SimVP_Simpler_Yet_Better_Video_Prediction_CVPR_2022_paper.html)
13. Zhihan Gao et al. *Earthformer: Exploring Space-Time Transformers for Earth System Forecasting.* NeurIPS, 2022b. [Paper](https://arxiv.org/abs/2207.05833)
14. Carles Gelada et al. *DeepMDP: Learning Continuous Latent Space Models for Representation Learning.* ICML, 2019. [Paper](https://proceedings.mlr.press/v97/gelada19a.html)
15. David Ha and Jürgen Schmidhuber. *World Models.* arXiv preprint arXiv:1803.10122, 2018. [Paper](https://arxiv.org/abs/1803.10122)
16. Danijar Hafner et al. *Learning Latent Dynamics for Planning from Pixels.* ICML, 2019. [Paper](https://arxiv.org/abs/1811.04551)
17. Danijar Hafner, Timothy Lillicrap, Jimmy Ba, and Mohammad Norouzi. *Dream to Control: Learning Behaviors by Latent Imagination.* ICLR, 2020. [Paper](https://arxiv.org/abs/1912.01603)
18. Danijar Hafner et al. *Mastering Atari with Discrete World Models.* ICLR, 2021. [Paper](https://openreview.net/forum?id=0oabwyZbOu)
19. Danijar Hafner, Jurgis Pasukonis, Jimmy Ba, and Timothy Lillicrap. *Mastering Diverse Domains through World Models.* arXiv preprint arXiv:2301.04104, 2023. [Paper](https://arxiv.org/abs/2301.04104)
20. Nicklas Hansen, Xiaolong Wang, and Hao Su. *Temporal Difference Learning for Model Predictive Control.* ICML, 2022. [Paper](https://proceedings.mlr.press/v162/hansen22a.html)
21. Nicklas Hansen, Hao Su, and Xiaolong Wang. *TD-MPC2: Scalable, Robust World Models for Continuous Control.* ICLR, 2024. [Paper](https://arxiv.org/abs/2310.16828)
22. Irene Iele, Elena Mulero Ayllón, Paolo Soda, and Matteo Tortora. *VegSim: A Geospatial World Model for Scenario-Conditioned Vegetation Simulation.* arXiv preprint arXiv:2606.21961, 2026. [Paper](https://arxiv.org/abs/2606.21961)
23. Michael Janner, Justin Fu, Marvin Zhang, and Sergey Levine. *When to Trust Your Model: Model-Based Policy Optimization.* NeurIPS, 2019. [Paper](https://papers.nips.cc/paper/2019/hash/5faf461eff3099671ad63c6f3f094f7f-Abstract.html)
24. Łukasz Kaiser et al. *Model-Based Reinforcement Learning for Atari.* ICLR, 2020. [Paper](https://arxiv.org/abs/1903.00374)
25. Alex M. Lamb et al. *Professor Forcing: A New Algorithm for Training Recurrent Networks.* NeurIPS, 2016. [Paper](https://proceedings.neurips.cc/paper/2016/hash/16026d60ff9b54410b3435b403afd226-Abstract.html)
26. Vincent Le Guen and Nicolas Thome. *Disentangling Physical Dynamics from Unknown Factors for Unsupervised Video Prediction.* CVPR, 2020. [Paper](https://openaccess.thecvf.com/content_CVPR_2020/html/Le_Guen_Disentangling_Physical_Dynamics_From_Unknown_Factors_for_Unsupervised_Video_Prediction_CVPR_2020_paper.html)
27. Zongyi Li et al. *Fourier Neural Operator for Parametric Partial Differential Equations.* ICLR, 2021. [Paper](https://openreview.net/forum?id=c8P9NQVtmnO)
28. Phillip Lippe, Bastiaan S. Veeling, Paris Perdikaris, Richard E. Turner, and Johannes Brandstetter. *PDE-Refiner: Achieving Accurate Long Rollouts with Neural PDE Solvers.* NeurIPS, 2023. [Paper](https://papers.neurips.cc/paper_files/paper/2023/hash/d529b943af3dba734f8a7d49efcb6d09-Abstract-Conference.html)
29. Lu Lu, Pengzhan Jin, Guofei Pang, Zhongqiang Zhang, and George Em Karniadakis. *Learning Nonlinear Operators via DeepONet Based on the Universal Approximation Theorem of Operators.* Nature Machine Intelligence, 2021. [Paper](https://doi.org/10.1038/s42256-021-00302-5)
30. Vincent Micheli, Eloi Alonso, and François Fleuret. *Transformers are Sample-Efficient World Models.* ICLR, 2023. [Paper](https://openreview.net/forum?id=vhFu1Acb0xb)
31. Christian Requena-Mesa et al. *EarthNet2021: A Large-Scale Dataset and Challenge for Earth Surface Forecasting as a Guided Video Prediction Task.* CVPR EarthVision Workshop, 2021. [Paper](https://arxiv.org/abs/2104.10066)
32. Jan Robine, Marc Höftmann, Tobias Uelwer, and Stefan Harmeling. *Transformer-Based World Models Are Happy With 100k Interactions.* ICLR, 2023. [Paper](https://openreview.net/forum?id=TdBaDGCpjly)
33. Yulia Rubanova, Ricky T. Q. Chen, and David Duvenaud. *Latent Ordinary Differential Equations for Irregularly-Sampled Time Series.* NeurIPS, 2019. [Paper](https://proceedings.neurips.cc/paper/2019/hash/42a6845a557bef704ad8ac9cb4461d43-Abstract.html)
34. Alvaro Sanchez-Gonzalez et al. *Learning to Simulate Complex Physics with Graph Networks.* ICML, 2020. [Paper](https://proceedings.mlr.press/v119/sanchez-gonzalez20a.html)
35. Julian Schrittwieser et al. *Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model.* Nature, 2020. [Paper](https://www.nature.com/articles/s41586-020-03051-4)
36. Max Schwarzer et al. *Data-Efficient Reinforcement Learning with Self-Predictive Representations.* ICLR, 2021. [Paper](https://openreview.net/forum?id=uCQfPZwRaUu)
37. Xingjian Shi et al. *Convolutional LSTM Network: A Machine Learning Approach for Precipitation Nowcasting.* NeurIPS, 2015. [Paper](https://proceedings.neurips.cc/paper/2015/hash/07563a3fe3bbe7e3ba84431ad9d055af-Abstract.html)
38. Richard S. Sutton. *Dyna, an Integrated Architecture for Learning, Planning, and Reacting.* ACM SIGART Bulletin, 1991. [Paper](https://dl.acm.org/doi/10.1145/122344.122377)
39. Aaron van den Oord, Yazhe Li, and Oriol Vinyals. *Representation Learning with Contrastive Predictive Coding.* arXiv preprint arXiv:1807.03748, 2018. [Paper](https://arxiv.org/abs/1807.03748)
40. Vikram Voleti, Alexia Jolicoeur-Martineau, and Christopher Pal. *MCVD: Masked Conditional Video Diffusion for Prediction, Generation, and Interpolation.* NeurIPS, 2022. [Paper](https://proceedings.neurips.cc/paper_files/paper/2022/hash/944618542d80a63bbec16dfbd2bd689a-Abstract-Conference.html)
41. Yunbo Wang et al. *PredRNN: Recurrent Neural Networks for Predictive Learning Using Spatiotemporal LSTMs.* NeurIPS, 2017. [Paper](https://proceedings.neurips.cc/paper/2017/hash/e5f6ad6ce374177eef023bf5d0c018b6-Abstract.html)
42. Yunbo Wang et al. *PredRNN++: Towards a Resolution of the Deep-in-Time Dilemma in Spatiotemporal Predictive Learning.* ICML, 2018. [Paper](https://proceedings.mlr.press/v80/wang18b.html)
43. Manuel Watter, Jost Springenberg, Joschka Boedecker, and Martin Riedmiller. *Embed to Control: A Locally Linear Latent Dynamics Model for Control from Raw Images.* NeurIPS, 2015. [Paper](https://proceedings.neurips.cc/paper/2015/hash/a1afc58c6ca9540d057299ec3016d726-Abstract.html)
44. Weirui Ye, Shaohuai Liu, Thanard Kurutach, Pieter Abbeel, and Yang Gao. *Mastering Atari Games with Limited Data.* NeurIPS, 2021. [Paper](https://proceedings.neurips.cc/paper_files/paper/2021/hash/d5eca8dc3820cad9fe56a3bafda65ca1-Abstract.html)
45. Weipu Zhang, Gang Wang, Jian Sun, Yetian Yuan, and Gao Huang. *STORM: Efficient Stochastic Transformer Based World Models for Reinforcement Learning.* NeurIPS, 2023. [Paper](https://papers.neurips.cc/paper_files/paper/2023/hash/5647763d4245b23e6a1cb0a8947b38c9-Abstract-Conference.html)
46. Sijie Zhao et al. *VegeDiff: Latent Diffusion Model for Geospatial Vegetation Forecasting.* IEEE Transactions on Geoscience and Remote Sensing, 2025. [Preprint](https://arxiv.org/abs/2407.12592) · [Official publication citation](https://github.com/NJU-LHRS/Official_VegeDiff#citation)
47. Gaoyue Zhou, Hengkai Pan, Yann LeCun, and Lerrel Pinto. *DINO-WM: World Models on Pre-Trained Visual Features Enable Zero-Shot Planning.* ICML, 2025. [Paper](https://proceedings.mlr.press/v267/zhou25t.html)
48. <span class="revision" style="color:blue">Junwei Luo, Shuai Yuan, Zhenya Yang, Yansheng Li, Zhe Liu, and Hengshuang Zhao. *EO-WM: A Physically Informed World Model for Probabilistic Earth Observation Forecasting.* arXiv:2606.27277, 2026. [Preprint](https://arxiv.org/abs/2606.27277) · [Official repository](https://github.com/hku-sail/EO-WM)</span>

---

<a id="appendices"></a>

## 附录 / Appendices

<a id="appendix-a"></a>

## A. 方法与实现细节 / Method and Implementation Details

### 中文稿

#### A.1 输入与网络实现

模型使用 10 个历史时间步预测未来 20 步，每步对应 5 天，空间尺寸为 \(128\times128\)。遥感输入为 NDVI、B02、B03、B04 和 B8A，取各五天区间末日对应的观测；输出为 NDVI。预处理沿用 Contextformer 的数据适配规则（`earthnet-models-pytorch v0.1.0`）：八个气象变量按 `fg、hu、pp、qq、rr、tg、tn、tx` 排列，先用固定统计量标准化，再依次拼接五天均值、最小值和最大值，形成 24 维天气输入。地理输入为 NASA、ALOS 和 Copernicus 三个 DEM 通道，各除以 500；土地覆盖仅用于监督掩膜。输入缺失数值填零；观测掩膜结合云掩膜与场景分类构造，缺失掩膜按无效处理。

历史编码采用 Contextformer 6M 配置（Benson et al., 2024）。<span class="revision" style="color:blue">基础预测在给定未来天气的条件下计算。初态特征由同一编码器在屏蔽未来影像和未来天气的条件下计算，保留已知日期特征。每次状态转移另行接收对应区间的天气。</span>历史图像块内存在正掩膜值时，其图像嵌入被掩蔽。最后一个历史时刻的末层 Transformer 特征经投影得到 \(S_0\)。读出将每个状态向量映射为 \(4\times4\) 图像块并拼接为图像空间中的状态修正，再与绝对目标日期对应的 \(B_t\) 相加，修正系数固定为 1。 <span class="revision" style="color:blue">年度正弦／余弦季节特征经线性投影加入token表示。</span>

区间天气编码由零隐藏状态开始，顺序处理 \(W_{a+1:b}\) 并取末端输出；跨度编码使用局部长度 \(b-a\)。<span class="revision" style="color:blue">天气与跨度表示广播至空间网格，与逐位置地理编码及终点季节特征融合，再与经融合条件调制的归一化状态拼接，共同输入多层感知机，生成加回原状态的增量。</span>转移逐空间位置应用共享网络，不额外引入跨位置的空间混合层；各时距与分段共享参数。

对于全时距直接预测，一次遍历 \(W_{1:n}\) 的GRU计算即可生成各天气前缀的表示，等价于分别从零隐藏状态编码每个前缀。各目标日期的动态状态随后从同一个 \(S_0\) 独立计算，并以批量方式实现。在分段推进中，天气GRU在每个分段均从零隐藏状态开始编码，动态状态则在相邻分段之间传递。

**表 A1：输入与网络规格。形状省略批次维；MLP 数字表示层宽，中间隐藏层使用 GELU。**

| 项目 | 配置 |
|---|---|
| 历史影像；有效性掩膜 | \(10\times5\times128\times128\)；\(10\times1\times128\times128\) |
| 历史天气；未来天气 | \(10\times24\)；\(20\times24\) |
| 地理输入；预测输出 | \(3\times128\times128\)；\(20\times1\times128\times128\) |
| 历史骨干 | Contextformer 6M，PVT 空间编码；时序 Transformer 深度 3、宽度 256、8 个注意力头、MLP 扩展比 4 |
| 状态网格 | \(32\times32\times256\)，对应 \(4\times4\) 图像块；实现中展平批次与空间位置维 |
| 状态投影 | LayerNorm → Linear \(256\to512\) → GELU → Linear \(512\to256\) → LayerNorm |
| 天气编码 | 单层 GRU，输入 24，隐藏维度 128 |
| 地理编码 | \(4\times4\) 平均池化；MLP \(3\to64\to64\) |
| 跨度编码 | 64 维固定正弦／余弦编码，输入为五天时间步数 |
| 条件融合 | <span class="revision" style="color:blue">拼接 \(128+64+64\) 维条件；MLP \(256\to256\to256\)，融合2维季节特征的线性投影</span> |
| 状态残差更新 | <span class="revision" style="color:blue">拼接经条件AdaLN调制的状态与融合条件</span>；MLP \(512\to512\to512\to256\)，输出加回状态 |
| 预测修正读出 | Linear \(256\to16\)，恢复为空间图像 |

#### A.2 损失计算

令 \(i,t,p\) 分别表示样本、预测时间步和像素；\(c_{itp}\) 在观测掩膜值小于 1 时取 1，\(v_{ip}\) 在土地覆盖类别属于 \([10,40]\) 时取 1。取 \(\epsilon=10^{-8}\)。直接预测沿用序列损失，先按每像素的有效日期归一化，再聚合空间与批次；令 \(q_{ip}=\max_t\mathbf{1}[\widehat Y^D_{itp}\ne-1]\)，其中 \(-1\) 为沿用的预测无效标记；<span class="revision" style="color:blue">对于整个预测窗口内无有效目标观测的像素，将 \(q_{ip}\) 置为0。</span>

\[
\ell_{\mathrm{seq}}=
\frac{
\displaystyle\sum_{i,p}v_{ip}q_{ip}
\frac{\sum_{t=1}^{n}c_{itp}(\widehat Y^D_{itp}-Y_{itp})^2}
{\sum_{t=1}^{n}c_{itp}+\epsilon}
}{\displaystyle\sum_{i,p}v_{ip}q_{ip}+\epsilon}.
\]

端点图像损失直接在该日期的有效植被像素上聚合：

\[
\ell_{\mathrm{img}}(\widehat Y_e,Y_e)=
\frac{\displaystyle\sum_{i,p}v_{ip}c_{iep}(\widehat Y_{iep}-Y_{iep})^2}
{\displaystyle\sum_{i,p}v_{ip}c_{iep}+\epsilon}.
\]

分段监督对三个端点的图像损失等权平均；与直接预测监督的权重均为 1，即 \(\lambda_{\mathrm{path}}=1\)。两类损失均监督 \(B_t\) 与状态修正相加后的完整预测。<span class="revision" style="color:blue">上述损失使用跨设备汇总的有效监督计数进行归一化。</span>不使用目标标准差缩放或重加权。<span class="revision" style="color:blue">整个预测窗口内无有效目标观测的像素不参与序列损失平均；</span>无有效监督像素的端点损失为零，仍保留在三端点平均中。

#### A.3 分段采样与训练流程

训练端点集合为 \(\mathcal E=\{10,15,20\}\)，分别对应第 50、75、100 天。每次更新在各端点的多段候选集合中独立、均匀抽取一条路径；计划由训练种子和更新编号确定，同次更新的样本、微批次和设备共用该计划。每个候选划分均表示为以五天为单位的分段长度序列，各段长度之和等于该端点的时间索引。只从表中候选抽样，未见评测划分另列于 D。

**表 A2：分段监督的训练候选。**

| 端点 | 预测天数 | 候选分段长度 |
|---|---:|---|
| 10 | 50 天 | \((5,5)\)、\((5,3,2)\) |
| 15 | 75 天 | \((7,8)\)、\((7,4,4)\) |
| 20 | 100 天 | \((10,10)\)、\((10,5,5)\)、\((5,5,5,5)\) |

一次历史编码后，从同一 \(S_0\) 分别计算全时距直接预测和三个分段端点预测。每条分段路径仅在最终端点读出图像；在当前训练阶段，真实目标影像仅用于计算损失，损失梯度沿每条采样路径的全部分段反向传播。直接端点监督对照保留模型、端点、损失及优化配置，执行相同的随机抽样后将所选路径替换为单段，使额外端点监督作用于从 \(S_0\) 出发的一次直接转移。

继续预测评测将同一生成状态 \(S_k\) 固定为各后续日期的预测起点，分别使用 \(W_{k+1:t}\)、局部跨度 \(t-k\)、原样本地理条件和保留的 \(B_t\)。针对每个目标日期，模型分别从同一个固定状态 \(S_k\) 调用共享转移，再将所得状态的读出与保留的基准预测 \(B_t\) 相加，生成该日期的预测。在分段路径训练中，每个监督端点均沿各自从 \(S_0\) 出发的采样路径到达。具体评测日期与统计协议见 C。

#### A.4 初始化与优化设置

> A.4编辑核验说明（2026-11-15，不进入投稿）：以下按用户批准的D最终稿方案更新。三种子运行完成状态、跨运行全局batch/更新预算/设备布局、未见分段及干预的权重绑定仍需最终验收；此处列明种子不表示三种子结果已全部完成。初始化历史段本轮保留，D各配对运行的共同父检查点及其前序训练叙述待核对。若各运行物理设备布局不同，按已批准方案仅保留全局batch与梯度累积。

模型与直接端点监督对照继承同一完整检查点。其直接前序阶段从已有预测模型出发，进行了 14,880 次更新，使用真实 NDVI 监督、冻结天气条件教师的预测蒸馏，以及冻结编码器从真实未来观测构造的终点状态监督。前两项权重为 1 和 0.5；状态监督采用层归一化后的余弦距离，权重在前 20% 更新内由 0 线性升至 0.02，保持至 80%，最后 20% 为 0.01。该阶段前 80% 冻结历史骨干，最后 20% 解冻其末个时序 Transformer 块。

当前阶段重新建立优化器与调度，仅使用 A.2 的两类图像监督，不再使用蒸馏或未来状态目标。<span class="revision" style="color:blue">历史骨干最后两个时序 Transformer 块参与微调</span>，状态投影、条件编码、融合、转移和读出模块均训练。历史编码前向采用评估模式以停用随机时间掩膜，同时保留解冻参数的梯度。

**表 A3：当前阶段的优化配置。**

| 配置项 | 取值 |
|---|---|
| 优化器 | AdamW，\(\beta_1=0.9,\ \beta_2=0.999\) |
| 状态及条件建模模块学习率 | \(3\times10^{-5}\) |
| 历史骨干解冻块学习率 | <span class="revision" style="color:blue">\(1\times10^{-5}\)，缩放系数 \(1/3\)</span> |
| 权重衰减 | 0 |
| 学习率调度 | <span class="revision" style="color:blue">600 次更新线性预热，随后余弦衰减至峰值学习率的 0.1 倍</span> |
| 批次与梯度累积 | <span class="revision" style="color:blue">全局 32；4 设备 × 每设备 8；梯度累积 1</span> |
| 梯度范数裁剪上限 | 1 |
| 训练长度 | <span class="revision" style="color:blue">主实验 100 个 epoch，74,500 次更新</span> |
| 随机种子 | <span class="revision" style="color:blue">核心监督路径比较：27、42、97；补充消融：42</span> |

<span class="revision" style="color:blue">主实验依据验证集表现选择检查点，核心监督路径比较采用配对随机种子27、42和97。未见划分及干预评估采用seed42的相应验证选优检查点。补充消融统一使用seed42的固定第40轮检查点，详见附录I。</span>

### English manuscript

#### A.1 Inputs and Network Implementation

The model uses 10 historical steps to forecast the next 20 steps at five-day intervals and a spatial size of \(128\times128\) pixels. Remote-sensing inputs comprise NDVI, B02, B03, B04, and B8A sampled at the end of each five-day interval; the output is NDVI. Preprocessing follows the Contextformer data adapter (`earthnet-models-pytorch v0.1.0`). Eight weather variables, ordered as `fg, hu, pp, qq, rr, tg, tn, tx`, are standardized using fixed statistics. Their five-day means, minima, and maxima are concatenated in this order to form 24-dimensional weather inputs. Geographic inputs comprise NASA, ALOS, and Copernicus DEM channels, each divided by 500; land cover is used only for supervision masks. Missing input values are filled with zero. Observation masks combine cloud masks and scene classifications, with missing mask values treated as invalid.

The history encoder follows the Contextformer 6M configuration (Benson et al., 2024). <span class="revision" style="color:blue">The baseline forecast is computed with the supplied future weather. Features for state initialization are computed using the same encoder with future imagery and future weather masked out, while retaining known calendar features. Each state transition separately receives the weather for its corresponding interval.</span> A historical image-patch embedding is masked if any pixel in the patch has a positive mask value. Features at the last historical step from the final Transformer block are projected to obtain \(S_0\). The readout maps each state vector to a \(4\times4\) image patch, assembles them into an image-space correction, and adds it to \(B_t\) at the absolute target date, with a fixed correction coefficient of 1. <span class="revision" style="color:blue">Annual sine/cosine seasonal features are linearly projected and added to the token representations.</span>

Each weather interval \(W_{a+1:b}\) is encoded in temporal order from a zero GRU hidden state, using the final output as its representation. The span encoding uses the local interval length \(b-a\). <span class="revision" style="color:blue">Weather and span representations are broadcast over the spatial grid and fused with location-specific geographic features and endpoint seasonal features. The normalized state, modulated by the fused condition, is concatenated with that condition and passed to an MLP that predicts an increment to be added to the input state.</span> The transition applies a shared network at each spatial location without an additional cross-location mixing layer; parameters are shared across forecast horizons and partitions.

For all-horizon direct prediction, a single GRU pass over \(W_{1:n}\) produces weather representations for every prefix, equivalent to encoding each prefix from a zero hidden state. The horizon-specific dynamic states are then computed independently from the same \(S_0\) in a batch. In partitioned rollout, the weather GRU starts from a zero hidden state for each segment, while the dynamic state is passed between successive segments.

**Table A1: Input and network specifications. Shapes omit the batch dimension. MLP widths are listed in order, with GELU after intermediate hidden layers.**

| Component | Configuration |
|---|---|
| Historical imagery; validity mask | \(10\times5\times128\times128\); \(10\times1\times128\times128\) |
| Historical weather; future weather | \(10\times24\); \(20\times24\) |
| Geographic inputs; forecast output | \(3\times128\times128\); \(20\times1\times128\times128\) |
| History backbone | Contextformer 6M with PVT spatial encoding; temporal Transformer depth 3, width 256, 8 attention heads, MLP expansion ratio 4 |
| State grid | \(32\times32\times256\), corresponding to \(4\times4\) image patches; batch and spatial dimensions are flattened in the implementation |
| State projection | LayerNorm → Linear \(256\to512\) → GELU → Linear \(512\to256\) → LayerNorm |
| Weather encoder | Single-layer GRU; input dimension 24, hidden dimension 128 |
| Geographic encoder | \(4\times4\) average pooling; MLP \(3\to64\to64\) |
| Span encoding | Fixed 64-dimensional sine/cosine encoding of the span in five-day steps |
| Condition fusion | <span class="revision" style="color:blue">Concatenate \(128+64+64\) condition dimensions; MLP \(256\to256\to256\), incorporating a linear projection of the two-dimensional seasonal features</span> |
| Residual state update | <span class="revision" style="color:blue">Concatenate the conditionally AdaLN-modulated state and fused condition</span>; MLP \(512\to512\to512\to256\), added to the input state |
| Prediction correction readout | Linear \(256\to16\), followed by spatial reassembly |

#### A.2 Loss Computation

Let \(i,t,p\) index samples, forecast steps, and pixels. The observation indicator \(c_{itp}\) equals 1 when the observation-mask value is below 1, and the vegetation indicator \(v_{ip}\) equals 1 for land-cover codes in \([10,40]\). We use \(\epsilon=10^{-8}\). Direct predictions use the inherited sequence loss, which first averages over valid dates at each pixel and then aggregates across pixels and samples. Let \(q_{ip}=\max_t\mathbf{1}[\widehat Y^D_{itp}\ne-1]\), where \(-1\) is the inherited invalid-prediction marker. <span class="revision" style="color:blue">For pixels with no valid target observations throughout the forecast window, \(q_{ip}\) is set to zero.</span>

\[
\ell_{\mathrm{seq}}=
\frac{
\displaystyle\sum_{i,p}v_{ip}q_{ip}
\frac{\sum_{t=1}^{n}c_{itp}(\widehat Y^D_{itp}-Y_{itp})^2}
{\sum_{t=1}^{n}c_{itp}+\epsilon}
}{\displaystyle\sum_{i,p}v_{ip}q_{ip}+\epsilon}.
\]

The endpoint image loss instead aggregates directly over valid vegetation pixels at the target date:

\[
\ell_{\mathrm{img}}(\widehat Y_e,Y_e)=
\frac{\displaystyle\sum_{i,p}v_{ip}c_{iep}(\widehat Y_{iep}-Y_{iep})^2}
{\displaystyle\sum_{i,p}v_{ip}c_{iep}+\epsilon}.
\]

Partitioned-path supervision averages the image losses equally over three endpoints. Both supervision terms have unit weight, giving \(\lambda_{\mathrm{path}}=1\), and supervise the full prediction obtained by adding the state correction to \(B_t\). <span class="revision" style="color:blue">These losses are normalized using valid-supervision counts aggregated across devices.</span> No target-standard-deviation scaling or reweighting is applied. <span class="revision" style="color:blue">Pixels with no valid target observations throughout the forecast window are excluded from the sequence-loss average.</span> An endpoint with no valid supervision pixels contributes zero loss and remains in the three-endpoint average.

#### A.3 Partition Sampling and Training Procedure

The training endpoint set is \(\mathcal E=\{10,15,20\}\), corresponding to days 50, 75, and 100. Each update independently samples one multi-segment path uniformly from each endpoint's candidate set. The plan is determined by the training seed and update index and shared across samples, microbatches, and devices within that update. Each candidate partition is written as a sequence of segment lengths in five-day steps. The lengths sum to its endpoint index. Sampling is restricted to these candidates. Unseen evaluation partitions are listed separately in D.

**Table A2: Training candidates for partitioned-path supervision.**

| Endpoint | Forecast lead time | Candidate segment lengths |
|---|---:|---|
| 10 | 50 days | \((5,5)\), \((5,3,2)\) |
| 15 | 75 days | \((7,8)\), \((7,4,4)\) |
| 20 | 100 days | \((10,10)\), \((10,5,5)\), \((5,5,5,5)\) |

After one history-encoding pass, all-horizon direct predictions and the three partitioned endpoint predictions are computed from the same \(S_0\). Each partitioned path decodes an image only at its final endpoint. In the current training stage, observed target imagery enters only the loss, whose gradients propagate through all segments of each sampled path. The direct-endpoint control retains the model, endpoints, losses, and optimization settings. It performs the same random draws, then replaces each sampled path with a single direct transition from \(S_0\) for the additional endpoint supervision.

Continuation evaluation fixes the same generated state \(S_k\) as the starting point for each subsequent target date, using \(W_{k+1:t}\), the local span \(t-k\), the original sample's geography, and the retained \(B_t\). For each target date, a separate call to the shared transition advances the same fixed state \(S_k\). The prediction combines the resulting state's readout with the retained baseline \(B_t\). For partitioned-path training, each supervised endpoint is reached along its own sampled path from \(S_0\). Evaluation dates and statistics are specified in C.

#### A.4 Initialization and Optimization

The model and direct-endpoint control inherit the same full checkpoint. Its immediate preceding training stage started from an existing forecasting model and ran for 14,880 updates, using observed NDVI supervision, prediction distillation from a frozen weather-conditioned teacher, and terminal-state supervision with targets encoded from observed future imagery by a frozen encoder. The first two terms had weights of 1 and 0.5. State supervision used cosine distance after LayerNorm, with its weight increasing linearly from 0 to 0.02 during the first 20% of updates, remaining at 0.02 until 80%, and changing to 0.01 for the final 20%. The history backbone was frozen for the first 80%, after which its final temporal Transformer block was unfrozen.

The current stage starts with a new optimizer and schedule and uses only the two image-supervision terms in A.2, without distillation or future-state targets. <span class="revision" style="color:blue">The final two temporal Transformer blocks of the history backbone are finetuned</span>; the state projection, condition encoders, fusion, transition, and readout modules are trained. History encoding runs in evaluation mode to disable random temporal masking while retaining gradients for unfrozen parameters.

**Table A3: Optimization settings for the current training stage.**

| Setting | Value |
|---|---|
| Optimizer | AdamW, \(\beta_1=0.9,\ \beta_2=0.999\) |
| Learning rate for state and condition modules | \(3\times10^{-5}\) |
| Learning rate for the unfrozen history-backbone block | <span class="revision" style="color:blue">\(1\times10^{-5}\), scaling factor \(1/3\)</span> |
| Weight decay | 0 |
| Learning-rate schedule | <span class="revision" style="color:blue">Linear warmup for 600 updates, followed by cosine decay to 0.1 times the peak learning rate</span> |
| Batch size and gradient accumulation | <span class="revision" style="color:blue">Global batch 32; 4 devices × 8 samples; accumulation 1</span> |
| Gradient-norm clipping threshold | 1 |
| Training duration | <span class="revision" style="color:blue">Main experiments: 100 epochs, 74,500 updates</span> |
| Random seed | <span class="revision" style="color:blue">Core supervision-path comparison: 27, 42, 97; supplementary ablations: 42</span> |

<span class="revision" style="color:blue">Checkpoints for the main experiments are selected by validation performance. The core supervision-path comparison uses paired seeds 27, 42, and 97. Unseen-partition and intervention evaluations use the corresponding validation-selected checkpoint for seed 42. Supplementary ablations consistently use the fixed epoch-40 checkpoints for seed 42 (Appendix I).</span>

<a id="appendix-b"></a>

## B. 标准预测的完整设置与结果 / Standard Forecasting: Setup and Full Results

### 中文稿

#### B.1 数据与评测协议

采用 GreenEarthNet 的四个 chopped 划分（Benson et al., 2024），清单样本数见表 B1。输入预处理见 A.1；全部评测使用 10 个历史五日步和 20 个未来五日步。未来遥感图像及其有效性掩膜仅用于评分，不输入模型。

官方评分先在像素时间序列上计算指标，再依次在立方体内的土地覆盖类别、同类立方体以及土地覆盖类别之间聚合。有效像素须满足云/场景掩膜、土地覆盖编码小于 41、最小有效 NDVI 大于 0、未来窗口至少 10 次有效观测、其余时间至少 3 次有效观测及目标时间标准差大于 0.1。这里的 \(R^2_{\mathrm{LC}}\) 是相关系数平方的类别平衡均值，不是 \(1-\mathrm{SSE}/\mathrm{SST}\)；RMSE 在平方根之后聚合。NSE 按官方实现先转为 normalized NSE、聚合后再逆变换。\(|\mathrm{Bias}|\) 为绝对偏差；RMSE25表示预测窗口前25天的RMSE。因此，标准指标与 C 中的样本等权 MSE 不直接互换。

表 B2 中，<span class="revision" style="color:blue">除使用公开权重评价的EO-WM外，学习方法均使用 seeds 27/42/97；</span>四个公开学习基线采用 GreenEarthNet 作者发布的 [Zenodo 权重（record 10793870）](https://zenodo.org/records/10793870)，并在共同清单、输入版本、掩膜与评分实现上重评。Weather-conditioned ConvGRU 为本研究实现，每个种子在四个划分上使用同一权重。Persistence 是确定性基线。表 B2 的 ± 表示三个种子结果的样本标准差（分母为 \(3-1\)）。各方法在统一评测协议下比较，训练预算和初始化按各自方案设置。

**表 B1 / Table B1：标准预测清单范围 / Standard forecasting manifests.**

| 划分 / Split | 清单 / Manifest | 样本数 / Samples |
|---|---|---:|
| IID | iid_chopped | 2,856 |
| OOD-T | ood-t_chopped | 1,904 |
| OOD-S | ood-s_chopped | 10,536 |
| OOD-ST | ood-st_chopped | 7,024 |

表中数量为各评测清单的样本数；不同端点的有效样本数在对应实验中给出。OOD-S 使用正式标准评测采用的修复覆盖数据，ConvGRU 沿用相同清单及输入版本。

天气条件ConvGRU为本研究实现的递归基线。两层64通道卷积编码历史五波段影像、有效性掩膜和三个DEM通道。96通道ConvGRU在128×128空间网格上运行，结合24维天气与地理特征，每次推进一个五日步。预测时反馈前一步NDVI，读出为 \(\operatorname{sigmoid}(\operatorname{Conv}_{1\times1}(h_t)+\widehat Y_{t-1})\)。前一步NDVI在sigmoid之前与卷积输出相加，两项共同经过非线性读出。预测期间不接收未来遥感影像。

<span class="revision" style="color:blue">我们使用EO-WM公开权重及配套EO-VAE，在统一的GreenEarthNet四分区与NDVI评分协议下进行适配评价。其EarthNet数据体系与GreenEarthNet在卫星观测、气象驱动和任务设计上密切相关。每例采用30步Euler采样生成5个预测成员，对预测反射率取均值后计算NDVI；波段、地形与天气输入按数据接口作相应适配。这里报告公开权重的适配表现，训练条件与本文模型不同。</span>

<span class="revision" style="color:blue">对于VegeDiff，我们依据官方代码训练适配模型。在所核查的官方发布资源中，未找到可直接使用的自编码器权重，因此采用公开的EarthNet微调EO-VAE，并进一步在GreenEarthNet训练数据上适配。扩散预测模型训练100 epoch（seed 97），按验证集选择checkpoint。当前实现训练时未执行条件随机丢弃，而评价使用CFG scale=2；这一训练与采样设置的匹配问题及替代潜空间的影响尚未排除。我们单列其适配结果，不据此判断原始VegeDiff的性能或声称优于该方法。</span>

<span class="revision" style="color:blue">VegSim与本文在天气驱动的潜在植被状态演化方面相关，但其公开任务预测minicube级NDVI序列及分位数，与本文的逐像素空间预测粒度不同，因此不将其原文指标直接纳入同一精度排名。</span>

#### B.2 完整指标与种子结果

**表 B2 / Table B2：四划分完整标准指标 / Full standard forecasting metrics on four splits.** <span class="revision" style="color:blue">各方法的训练种子数见表中标注。多种子结果报告均值±样本标准差；EO-WM报告公开权重的适配评价结果。确定性结果只报告点估计。/ The number of training seeds is indicated for each method. Multi-seed results are reported as mean ± sample standard deviation; EO-WM reports adapted evaluation results using released weights. Deterministic results are point estimates.</span> 

**IID**

| 方法 / Method | 种子数 / Seeds | R² ↑ | RMSE ↓ | NSE ↑ | \|Bias\| ↓ | RMSE25 ↓ |
|---|---|---|---|---|---|---|
| SpanWorld | 3 | 0.5221 ± 6.49e−5 | 0.1555 ± 1.42e−6 | -0.1370 ± 9.51e−5 | 0.0997 ± 4.00e−6 | 0.0912 ± 1.75e−5 |
| Weather-conditioned ConvGRU | 3 | 0.5195 ± 0.0023 | 0.1568 ± 0.0021 | -0.1498 ± 0.0217 | 0.0989 ± 0.0028 | 0.0937 ± 6.91e-5 |
| Persistence | — | 0.0000 | 0.2213 | -1.1716 | 0.1610 | 0.1028 |
| ConvLSTM 1M | 3 | 0.5107 ± 0.00150 | 0.1557 ± 0.00110 | -0.1046 ± 0.0115 | 0.0978 ± 0.00121 | 0.1005 ± 0.00168 |
| PredRNN 1M | 3 | **0.5414** ± 0.0110 | **0.1423** ± 0.00450 | **0.0427** ± 0.0481 | **0.0869** ± 0.00365 | **0.0888** ± 0.00253 |
| SimVP 6M | 3 | 0.4988 ± 0.00609 | <u>0.1461</u> ± 0.00171 | <u>-0.0191</u> ± 0.0227 | <u>0.0871</u> ± 0.00150 | 0.1009 ± 0.00272 |
| Contextformer 6M | 3 | <u>0.5333</u> ± 6.11e−4 | 0.1484 ± 9.02e−4 | -0.0387 ± 0.0131 | 0.0941 ± 8.50e−4 | <u>0.0893</u> ± 4.58e−4 |
| <span class="revision" style="color:blue">EO-WM</span> | <span class="revision" style="color:blue">公开权重 / Released weights</span> | <span class="revision" style="color:blue">0.4643</span> | <span class="revision" style="color:blue">0.1578</span> | <span class="revision" style="color:blue">-0.1553</span> | <span class="revision" style="color:blue">0.0989</span> | <span class="revision" style="color:blue">0.0991</span> |

**OOD-T**

| 方法 / Method | 种子数 / Seeds | R² ↑ | RMSE ↓ | NSE ↑ | \|Bias\| ↓ | RMSE25 ↓ |
|---|---|---|---|---|---|---|
| SpanWorld | 3 | 0.5726 ± 1.08e−4 | 0.1510 ± 2.74e−5 | -0.1068 ± 4.31e−4 | 0.1014 ± 3.21e−5 | <u>0.0824</u> ± 2.03e−5 |
| Weather-conditioned ConvGRU | 3 | 0.5683 ± 0.0012 | 0.1532 ± 0.0011 | -0.1326 ± 0.0091 | 0.1014 ± 0.0010 | 0.0872 ± 0.0017 |
| Persistence | — | 0.0000 | 0.2157 | -1.2248 | 0.1583 | 0.0850 |
| ConvLSTM 1M | 3 | 0.5483 ± 0.00696 | 0.1615 ± 0.00182 | -0.1899 ± 0.0130 | 0.1097 ± 0.00228 | 0.1022 ± 0.00272 |
| PredRNN 1M | 3 | **0.5924** ± 0.00153 | <u>0.1474</u> ± 0.00212 | <u>-0.0375</u> ± 0.0266 | <u>0.0974</u> ± 0.00470 | 0.1018 ± 0.00192 |
| SimVP 6M | 3 | 0.5616 ± 0.00532 | 0.1492 ± 0.00191 | -0.0660 ± 0.0165 | 0.0977 ± 0.00202 | 0.1043 ± 0.00161 |
| Contextformer 6M | 3 | <u>0.5877</u> ± 0.00436 | **0.1431** ± 8.19e−4 | **0.0051** ± 0.0168 | **0.0936** ± 5.03e−4 | **0.0818** ± 0.00315 |
| <span class="revision" style="color:blue">EO-WM</span> | <span class="revision" style="color:blue">公开权重 / Released weights</span> | <span class="revision" style="color:blue">0.5331</span> | <span class="revision" style="color:blue">0.1571</span> | <span class="revision" style="color:blue">-0.1824</span> | <span class="revision" style="color:blue">0.1052</span> | <span class="revision" style="color:blue">0.1070</span> |

**OOD-S**

| 方法 / Method | 种子数 / Seeds | R² ↑ | RMSE ↓ | NSE ↑ | \|Bias\| ↓ | RMSE25 ↓ |
|---|---|---|---|---|---|---|
| SpanWorld | 3 | 0.4949 ± 2.88e−5 | 0.1621 ± 9.59e−6 | -0.1763 ± 1.26e−4 | 0.1018 ± 1.37e−5 | 0.0970 ± 1.55e−5 |
| Weather-conditioned ConvGRU | 3 | 0.4830 ± 0.0015 | 0.1617 ± 0.0023 | -0.1695 ± 0.0302 | 0.0991 ± 0.0031 | 0.0998 ± 0.0007 |
| Persistence | — | 0.0000 | 0.2258 | -1.1336 | 0.1625 | 0.1127 |
| ConvLSTM 1M | 3 | 0.4761 ± 0.00373 | 0.1622 ± 0.00105 | -0.1540 ± 0.0113 | 0.0998 ± 0.00105 | 0.1038 ± 0.00176 |
| PredRNN 1M | 3 | **0.5087** ± 0.00926 | **0.1494** ± 0.00429 | **-0.0103** ± 0.0500 | <u>0.0888</u> ± 0.00435 | **0.0935** ± 0.00337 |
| SimVP 6M | 3 | 0.4649 ± 0.00635 | <u>0.1529</u> ± 0.00125 | <u>-0.0703</u> ± 0.0184 | **0.0882** ± 0.00164 | 0.1069 ± 0.00351 |
| Contextformer 6M | 3 | <u>0.5021</u> ± 0.00197 | 0.1549 ± 0.00160 | -0.0790 ± 0.0221 | 0.0960 ± 0.00166 | <u>0.0948</u> ± 6.56e−4 |
| <span class="revision" style="color:blue">EO-WM</span> | <span class="revision" style="color:blue">公开权重 / Released weights</span> | <span class="revision" style="color:blue">0.4322</span> | <span class="revision" style="color:blue">0.1679</span> | <span class="revision" style="color:blue">-0.2439</span> | <span class="revision" style="color:blue">0.1044</span> | <span class="revision" style="color:blue">0.1051</span> |

**OOD-ST**

| 方法 / Method | 种子数 / Seeds | R² ↑ | RMSE ↓ | NSE ↑ | \|Bias\| ↓ | RMSE25 ↓ |
|---|---|---|---|---|---|---|
| SpanWorld | 3 | 0.5407 ± 1.88e−4 | 0.1542 ± 2.51e−5 | -0.1551 ± 4.30e−4 | 0.1016 ± 1.86e−5 | <u>0.0871</u> ± 2.38e−5 |
| Weather-conditioned ConvGRU | 3 | 0.5415 ± 0.0033 | 0.1553 ± 0.0021 | -0.1710 ± 0.0226 | 0.1008 ± 0.0018 | 0.0924 ± 0.0008 |
| Persistence | — | 0.0000 | 0.2183 | -1.2401 | 0.1607 | 0.0966 |
| ConvLSTM 1M | 3 | 0.5234 ± 0.00321 | 0.1610 ± 9.24e−4 | -0.2261 ± 0.0113 | 0.1059 ± 0.00176 | 0.1047 ± 0.00204 |
| PredRNN 1M | 3 | **0.5635** ± 0.00166 | <u>0.1478</u> ± 0.00133 | <u>-0.0708</u> ± 0.0104 | **0.0943** ± 0.00333 | 0.1045 ± 0.00250 |
| SimVP 6M | 3 | 0.5275 ± 0.00211 | 0.1553 ± 0.00201 | -0.1552 ± 0.0205 | 0.0999 ± 9.50e−4 | 0.1082 ± 0.00189 |
| Contextformer 6M | 3 | <u>0.5567</u> ± 0.00130 | **0.1473** ± 0.00104 | **-0.0578** ± 0.0154 | <u>0.0958</u> ± 0.00137 | **0.0860** ± 0.00236 |
| <span class="revision" style="color:blue">EO-WM</span> | <span class="revision" style="color:blue">公开权重 / Released weights</span> | <span class="revision" style="color:blue">0.5014</span> | <span class="revision" style="color:blue">0.1624</span> | <span class="revision" style="color:blue">-0.2641</span> | <span class="revision" style="color:blue">0.1068</span> | <span class="revision" style="color:blue">0.1086</span> |

<p align="center">* 每个划分、每项指标的最佳均值加粗，次佳均值加下划线。 / Within each split and metric, best means are bolded and second-best means are underlined.</p>

<span class="revision" style="color:blue">VegeDiff适配结果（单种子；独立报告） / Adapted VegeDiff results (one seed; reported separately)</span>

| 方法 / Method | IID RMSE | OOD-T RMSE | OOD-S RMSE | OOD-ST RMSE |
|---|---:|---:|---:|---:|
| <span class="revision" style="color:blue">VegeDiff（适配 / adapted）</span> | <span class="revision" style="color:blue">0.4043</span> | <span class="revision" style="color:blue">0.3882</span> | <span class="revision" style="color:blue">0.4031</span> | <span class="revision" style="color:blue">0.4030</span> |

<span class="revision" style="color:blue">这些数值来自上述适配实现，不纳入最佳值标记或正式优越性排名。 / These values come from the adaptation described above and are excluded from best-value highlighting and formal superiority claims.</span>

SpanWorld 的 \(R^2_{\mathrm{LC}}\) 在四个划分上均低于 PredRNN 和 Contextformer。与 ConvGRU 相比，SpanWorld 在 IID 和 OOD-T 上的 \(R^2_{\mathrm{LC}}\) 较高且 RMSE 较低；在 OOD-S 上的 \(R^2_{\mathrm{LC}}\) 较高，但 RMSE 略大；在 OOD-ST 上的 \(R^2_{\mathrm{LC}}\) 略低，而 RMSE 较低。

**表 B3 / Table B3：全部三种子方法的逐运行主指标 / Per-run primary metrics for all three-seed methods.** 每格为 R²_LC / RMSE_LC；同一 seed 的四划分使用同一权重。公开基线的逐运行源记录保留四位小数，其均值与标准差由该记录计算。/ Each cell gives R²_LC / RMSE_LC. Each seed uses one checkpoint across all splits. Released-baseline run records retain four decimals; their means and standard deviations are computed from those records.

| 划分 / Split | 方法 / Method | Seed 27 | Seed 42 | Seed 97 |
|---|---|---|---|---|
| IID | SpanWorld | 0.522123 / 0.155531 | 0.522020 / 0.155529 | 0.522139 / 0.155532 |
| IID | Weather-conditioned ConvGRU | 0.516884 / 0.159180 | 0.521159 / 0.155214 | 0.520592 / 0.156141 |
| IID | ConvLSTM 1M | 0.5108 / 0.1546 | 0.5121 / 0.1568 | 0.5091 / 0.1557 |
| IID | PredRNN 1M | **0.5541** / **0.1371** | **0.5345** / **0.1449** | **0.5357** / **0.1449** |
| IID | SimVP 6M | 0.5003 / <u>0.1443</u> | 0.5040 / <u>0.1463</u> | 0.4921 / 0.1477 |
| IID | Contextformer 6M | <u>0.5332</u> / 0.1485 | <u>0.5340</u> / 0.1493 | <u>0.5328</u> / <u>0.1475</u> |
| OOD-T | SpanWorld | 0.572471 / 0.150988 | 0.572600 / 0.150940 | 0.572686 / 0.150942 |
| OOD-T | Weather-conditioned ConvGRU | 0.568206 / 0.154415 | 0.567111 / 0.152880 | 0.569438 / 0.152356 |
| OOD-T | ConvLSTM 1M | 0.5466 / 0.1603 | 0.5560 / 0.1636 | 0.5424 / 0.1606 |
| OOD-T | PredRNN 1M | **0.5942** / <u>0.1498</u> | **0.5915** / <u>0.1466</u> | **0.5916** / <u>0.1458</u> |
| OOD-T | SimVP 6M | 0.5555 / 0.1510 | 0.5650 / 0.1472 | 0.5644 / 0.1495 |
| OOD-T | Contextformer 6M | <u>0.5897</u> / **0.1438** | <u>0.5827</u> / **0.1433** | <u>0.5907</u> / **0.1422** |
| OOD-S | SpanWorld | 0.494926 / 0.162140 | 0.494875 / 0.162130 | 0.494923 / 0.162149 |
| OOD-S | Weather-conditioned ConvGRU | 0.481694 / 0.164263 | 0.482702 / 0.159806 | 0.484653 / 0.161030 |
| OOD-S | ConvLSTM 1M | 0.4787 / 0.1611 | 0.4777 / 0.1632 | 0.4718 / 0.1622 |
| OOD-S | PredRNN 1M | **0.5187** / **0.1445** | **0.5071** / **0.1526** | **0.5004** / **0.1510** |
| OOD-S | SimVP 6M | 0.4631 / <u>0.1517</u> | 0.4720 / <u>0.1529</u> | 0.4597 / 0.1542 |
| OOD-S | Contextformer 6M | <u>0.5039</u> / 0.1548 | <u>0.5024</u> / 0.1566 | <u>0.5000</u> / <u>0.1534</u> |
| OOD-ST | SpanWorld | 0.540543 / 0.154206 | 0.540760 / 0.154161 | 0.540918 / 0.154164 |
| OOD-ST | Weather-conditioned ConvGRU | 0.538476 / 0.157648 | 0.541003 / 0.154569 | 0.545051 / 0.153632 |
| OOD-ST | ConvLSTM 1M | 0.5203 / 0.1605 | 0.5267 / 0.1621 | 0.5231 / 0.1605 |
| OOD-ST | PredRNN 1M | **0.5647** / <u>0.1485</u> | **0.5616** / <u>0.1487</u> | **0.5642** / **0.1463** |
| OOD-ST | SimVP 6M | 0.5272 / 0.1547 | 0.5255 / 0.1536 | 0.5297 / 0.1575 |
| OOD-ST | Contextformer 6M | <u>0.5575</u> / **0.1467** | <u>0.5574</u> / **0.1485** | <u>0.5552</u> / <u>0.1467</u> |

<p align="center">* 每个划分、种子及指标内，最佳结果加粗，次佳结果加下划线。 / Within each split, seed, and metric, best results are bolded and second-best results are underlined.</p>

**表 B4 / Table B4：ConvGRU 的分时窗 RMSE / ConvGRU RMSE by forecast window.** Seeds 27/42/97 的均值 ± 样本标准差；沿用官方类别平衡聚合，各列分别覆盖五个预测日期。/ Means ± sample standard deviations over seeds 27/42/97; official land-cover-balanced aggregation; each column covers five forecast dates.

| 划分 / Split | 第 5–25 天 / Days 5–25 | 第 30–50 天 / Days 30–50 | 第 55–75 天 / Days 55–75 | 第 80–100 天 / Days 80–100 |
|---|---|---|---|---|
| IID | 0.0937 ± 6.91e-5 | 0.1330 ± 0.0014 | 0.1629 ± 0.0028 | 0.1772 ± 0.0025 |
| OOD-T | 0.0872 ± 0.0017 | 0.1285 ± 0.0030 | 0.1608 ± 0.0019 | 0.1752 ± 0.0038 |
| OOD-S | 0.0998 ± 0.0007 | 0.1371 ± 0.0010 | 0.1653 ± 0.0031 | 0.1810 ± 0.0031 |
| OOD-ST | 0.0924 ± 0.0008 | 0.1320 ± 0.0011 | 0.1600 ± 0.0031 | 0.1757 ± 0.0040 |

### English manuscript

#### B.1 Data and Evaluation Protocol

We use the four chopped GreenEarthNet splits (Benson et al., 2024), with manifest sizes listed in Table B1. Preprocessing follows Appendix A.1. All evaluations use 10 historical and 20 future five-day steps. Future remote-sensing images and their validity masks are used only for evaluation.

The official scorer computes temporal pixel metrics and aggregates them within cube–land-cover groups, across cubes within each class, and then across land-cover classes. Eligibility requires the cloud/scene mask, a land-cover code below 41, positive minimum valid NDVI, at least 10 valid future observations and three outside the forecast window, and target temporal standard deviation above 0.1. \(R^2_{\mathrm{LC}}\) averages squared correlations rather than \(1-\mathrm{SSE}/\mathrm{SST}\); RMSE is aggregated after taking square roots. NSE is transformed to normalized NSE before aggregation and inverted afterward. \(|\mathrm{Bias}|\) is absolute bias, and RMSE25 is the RMSE over the first 25 forecast days. These metrics are distinct from the sample-averaged MSE in Appendix C.

<span class="revision" style="color:blue">Except for EO-WM, which is evaluated using released weights, learned methods use seeds 27/42/97.</span> The four published learning baselines use the GreenEarthNet authors' [released checkpoints (Zenodo record 10793870)](https://zenodo.org/records/10793870), re-evaluated with shared manifests, input versions, masks, and scoring code. Our weather-conditioned ConvGRU uses one checkpoint per seed across all four splits. Persistence is deterministic. In Table B2, ± denotes the sample standard deviation across three seeds. All methods share the evaluation protocol, with training budgets and initialization set according to their respective procedures. Table B1 gives manifest sample counts; endpoint-eligible counts are reported for each experiment. OOD-S uses the repaired data version from the formal standard evaluation.

The weather-conditioned ConvGRU is our recurrent baseline implementation. Two 64-channel convolutional layers encode historical five-band imagery, validity masks, and three DEM channels. A 96-channel ConvGRU operates on a \(128\times128\) grid with 24-dimensional weather and geography, advancing one five-day step per call. Forecasting feeds back the previous NDVI prediction, with readout \(\operatorname{sigmoid}(\operatorname{Conv}_{1\times1}(h_t)+\widehat Y_{t-1})\). The previous NDVI prediction is added to the convolutional output before the sigmoid, so both terms pass through the nonlinear readout. Inference proceeds without future remote-sensing observations.

<span class="revision" style="color:blue">We evaluate released EO-WM weights and the accompanying EO-VAE under the shared GreenEarthNet four-split and NDVI scoring protocol. Its EarthNet setting is closely related to GreenEarthNet in satellite observations, meteorological drivers, and task design. For each sample, we generate five prediction members using 30 Euler sampling steps and average predicted reflectances before computing NDVI; band, terrain, and weather inputs are adapted to the data interface. These results characterize the adapted released weights, whose training conditions differ from those of our model.</span>

<span class="revision" style="color:blue">For VegeDiff, we train an adaptation based on the official code. We did not find directly usable autoencoder weights in the official resources inspected, so we use the publicly released EarthNet-finetuned EO-VAE and further adapt it on the GreenEarthNet training data. The diffusion predictor is trained for 100 epochs (seed 97), with checkpoint selection based on validation performance. The current implementation does not randomly drop conditioning during training, whereas evaluation uses CFG scale=2; the effects of this training–sampling mismatch and the substituted latent space remain unresolved. We report the adapted results separately and do not use them to characterize the original VegeDiff method or claim superiority over it.</span>

<span class="revision" style="color:blue">VegSim is related to our work in weather-driven latent vegetation-state evolution, but its released task predicts minicube-level NDVI sequences and quantiles rather than pixel-level spatial forecasts. We therefore do not rank its published metrics alongside results from our pixel-level task.</span>

#### B.2 Full Metrics and Seed Results

<span class="revision" style="color:blue">Table B2 includes the adapted EO-WM evaluation; the adapted VegeDiff results are reported separately below it. Tables B3–B4 retain per-seed primary scores for the six three-seed methods and three-seed ConvGRU forecast-window RMSE.</span> Released-baseline run records retain four decimals, from which their means and sample standard deviations are calculated. Each SpanWorld seed uses one checkpoint across all splits. Its \(R^2_{\mathrm{LC}}\) is below PredRNN and Contextformer on every split. Relative to ConvGRU, SpanWorld has higher \(R^2_{\mathrm{LC}}\) and lower RMSE on IID and OOD-T; on OOD-S, it has higher \(R^2_{\mathrm{LC}}\) but slightly higher RMSE; on OOD-ST, it has slightly lower \(R^2_{\mathrm{LC}}\) and lower RMSE.

<a id="appendix-c"></a>

## C. 核心继续预测实验 / Matched Continuation: Protocol and Full Results

### 中文稿

#### C.1 比较条件与预测路径

SpanWorld 与直接端点监督对照使用相同架构、共同初始化、全时距直接预测监督及更新次数，并使用相同端点影像提供额外监督；额外监督分别作用于分段或直接推进产生的预测。训练配置及候选分段见 A.3—A.4。训练按更新次数对齐，转移调用次数和计算开销则由各自的推进路径决定。

直接预测分别从 \(S_0\) 查询第 55—100 天；继续预测先经 50 天、25＋25 天或 15＋35 天推进得到 \(S_{10}\)，再从该固定状态独立查询同一组日期。后续查询使用相应区间天气、接收样本的地理信息及<span class="revision" style="color:blue">基础预测</span> \(B_t\)，没有新增遥感观测，也不反馈预测图像。15＋35 天不在训练候选中。下文步数均为五日步，第 10 步对应第 50 天。

#### C.2 样本、估计量与不确定性

接收样本（receiver）指清单中的一个样本，由其历史上下文和预测窗口界定。完整后缀要求十个目标时距记录齐全，且有效像素总数大于零；2,856 个 IID 清单样本中有 2,837 个满足要求，另外 19 个无后缀有效像素。有效区域使用观测掩膜小于 1 且土地覆盖编码在 \([10,40]\) 内的像素，在模型和路径之间保持一致。

令 \(e_{ik}\) 和 \(v_{ik}\) 为样本 \(i\) 在后续时距 \(k\) 的平方误差和及有效像素数。主指标为
\[
L_i=\frac{\sum_{k=1}^{10}e_{ik}}{\sum_{k=1}^{10}v_{ik}},
\qquad
\overline L=\frac1N\sum_{i=1}^{N}L_i .
\]
它不是所有样本像素一次合并的 \(\sum e/\sum v\)。空间不确定性通过 80 个 Sentinel-2 地理组的配对 bootstrap 计算：有放回抽组、保留组内全部样本及其模型/路径配对，再计算相同的样本等权均值。使用 2,000 次重抽样、随机种子 20260914 和百分位 95% 区间；这些边际区间反映固定已训练模型条件下的地理组抽样变异。单独评估第 100 天时，按该日期的有效像素重新判定资格，得到 1,670 个接收样本，不能沿用 2,837 的分母。

#### C.3 完整后缀、退化与单终点结果

**表 C1 / Table C1：共同后缀的绝对误差与模型间差值 / Absolute errors and between-model differences on the common suffix.** 第 55–100 天，N=2,837；差值为 SpanWorld 减直接端点监督对照，负值有利于 SpanWorld。括号为 95% 区间。/ Days 55–100, N=2,837. Differences are SpanWorld minus the direct-endpoint control; negative values favor SpanWorld. Brackets give 95% intervals.

| 预测起点 / Prediction starting point (days) | 对照 MSE [95% CI] / Control | SpanWorld MSE [95% CI] | ΔMSE [95% CI] |
|---|---|---|---|
| 初态直接 / Initial-state direct | 0.041480 [0.035780, 0.047559] | **0.041285** [0.035709, 0.047239] | -0.000195 [-0.000382, -0.000015] |
| 50 | 0.043713 [0.038079, 0.049802] | **0.041688** [0.036009, 0.047699] | -0.002025 [-0.002680, -0.001300] |
| 25+25 | 0.046488 [0.040882, 0.052690] | **0.041536** [0.035868, 0.047549] | -0.004952 [-0.005948, -0.003868] |
| 15+35 | 0.046550 [0.040938, 0.052730] | **0.041448** [0.035763, 0.047426] | -0.005101 [-0.006107, -0.004009] |

<p align="center">* 每行两个模型中较低的MSE加粗。 / Within each row, the lower model MSE is bolded.</p>

15+35 天路径下的相对降低为 10.96%，由未舍入均值计算：100×(对照−SpanWorld)/对照。/ The relative reduction after 15+35 days is 10.96%, computed from unrounded means as 100×(control−SpanWorld)/control.

**表 C2 / Table C2：各模型相对自身直接预测的后续误差变化 / Change in subsequent error relative to each model's direct prediction.** 与正文表1 使用同一后缀、资格集和空间重抽样；正值表示误差增加。/ Same window, eligibility set, and spatial resampling as Table 1; positive values indicate increased error.

| 模型 / Model | 到第 50 天的路径 / Route to day 50 | 相对自身直接预测的 ΔMSE / ΔMSE vs own direct | 95% CI |
|---|---|---|---|
| Direct-endpoint control | 50 | 0.002234 | [0.001448, 0.002960] |
| Direct-endpoint control | 25+25 | 0.005008 | [0.003895, 0.006040] |
| Direct-endpoint control | 15+35 | 0.005070 | [0.003952, 0.006097] |
| SpanWorld | 50 | **0.000403** | [0.000231, 0.000582] |
| SpanWorld | 25+25 | **0.000251** | [0.000078, 0.000440] |
| SpanWorld | 15+35 | **0.000163** | [-0.000010, 0.000345] |

<p align="center">* 每条路径上较低的MSE增量加粗。 / For each path, the lower increase in MSE is bolded.</p>

SpanWorld 在三条路径上的误差增幅均小于对照，其中 15＋35 天路径的增幅最小，其区间跨零。

**表 C3 / Table C3：模型间的退化差 / Between-model differences in degradation.** 差值为 (SpanWorld 继续−自身直接)−(对照继续−自身直接)；N=2,837，区间按相同配对重抽样计算。/ Differences equal (SpanWorld continued−own direct)−(control continued−own direct), with N=2,837 and the same paired resampling.

| 到第 50 天的路径 / Route to day 50 | 退化差 / Difference in degradation | 95% CI |
|---|---:|---|
| 50 | -0.001831 | [-0.002500, -0.001076] |
| 25+25 | -0.004757 | [-0.005780, -0.003649] |
| 15+35 | -0.004906 | [-0.005929, -0.003788] |

**表 C4 / Table C4：第 100 天独立资格集上的模型间差值 / Between-model differences on the separately eligible day-100 set.** 差值为 SpanWorld 减直接端点监督对照；\(N=1,670\)，80 个地理组。/ Differences are SpanWorld minus the direct-endpoint control; \(N=1,670\), with 80 geographic groups.

| 预测起点 / Prediction starting point | 第 100 天 ΔMSE / Day-100 ΔMSE | 95% CI |
|---|---|---|
| Initial state / 初态 | 0.000126 | [-0.000065, 0.000317] |
| 50-day state / 单段 | -0.001360 | [-0.002508, -0.000191] |
| 25+25-day state / 均分 | -0.004292 | [-0.005976, -0.002617] |
| 15+35-day state / 未见分段 | -0.004723 | [-0.006394, -0.003044] |

单终点的直接预测差值为正且区间跨零，而三条继续预测路径的差值均为负。这一结果进一步区分了直接预测表现与推进后的继续预测表现。

### English manuscript

#### C.1 Comparison Conditions and Prediction Routes

SpanWorld and the direct-endpoint control use the same architecture, initialization, supervision of direct predictions at all forecast horizons, and number of updates. Both use the same endpoint images for additional supervision, applied to partitioned and direct predictions, respectively. Appendices A.3–A.4 specify training. Training is matched by update count, with transition-call counts and computational costs determined by the respective rollout paths.

Direct predictions query each date from days 55–100 from \(S_0\). Continued predictions first form \(S_{10}\) through 50, 25+25, or 15+35 days of rollout, then query each target independently from that fixed state. Queries use the corresponding interval weather, receiver geography, and retained baseline \(B_t\), without new remote-sensing observations or predicted-image feedback. The 15+35-day partition is absent from the training candidates. An index step spans five days.

#### C.2 Samples, Estimands, and Uncertainty

A receiver denotes one manifest sample, defined by its historical context and forecast window. Full-suffix eligibility requires all ten horizon records and a positive total valid-pixel count. This yields 2,837 of the 2,856 IID samples; the remaining 19 have no valid suffix pixels. Validity requires an observation-mask value below 1 and land-cover codes in \([10,40]\), held fixed across models and routes.

For each receiver, \(L_i\) divides the sum of squared errors over the ten horizons by their total valid-pixel count; \(\overline L\) then averages receivers equally, as defined above. This differs from pooling all receivers' pixels. Paired bootstrap resampling draws 80 Sentinel-2 geographic groups with replacement, retains all within-group receivers and model/route pairings, and recomputes the same sample-averaged statistic. We use 2,000 resamples, random seed 20260914, and percentile 95% intervals. These marginal intervals describe geographic sampling variability with the trained models held fixed. Day-100-only evaluation uses its own validity criterion and 1,670 eligible receivers.

#### C.3 Full-Suffix, Degradation, and Single-Endpoint Results

Table C1 reports absolute errors and between-model differences for the full suffix; the relative reduction after 15+35 days is 10.96% using unrounded means. Table C2 reports error increases relative to each model's own direct prediction. SpanWorld has smaller error increases along all three paths; its smallest increase occurs after 15+35 days, with an interval spanning zero. Table C3 reports paired between-model differences in degradation, all negative. Table C4 reports between-model differences at day 100. The direct-prediction difference is positive with an interval crossing zero, whereas all three continued-prediction differences are negative. These results distinguish direct accuracy from post-rollout prediction.

<a id="appendix-d"></a>

## D. 训练未见时间分段 / Evaluation on Unseen Temporal Partitions

### 中文稿

#### D.1 分段与评价定义

使用冻结的 SpanWorld 权重，在 2,856 个 IID 清单样本上评估九种未包含于 A.3 训练候选的时间划分；三个目标日期均接受直接预测监督。因此，这里的“未见”具体指时间划分。此处直接比较同一目标日期的直接预测与分段预测，不从该端点继续查询后续日期。对每个端点的共同有效像素累加平方误差与像素数，得到 pooled MSE；第 50、75、100 天分别有 1,615、1,568、1,617 个样本具有有效像素。因此，本表与 C 的后续时窗样本等权 MSE 具有不同的估计对象。

#### D.2 完整端点结果

**表 D1 / Table D1：九种训练未见分段的完整端点结果 / Endpoint results for nine training-unseen partitions.** 比值为分段预测 MSE 除以同日期直接预测 MSE；分段长度均以天为单位。图 4a 使用 100×(比值−1)，由未舍入源值计算。/ Ratios divide partitioned MSE by direct MSE at the same date; segment lengths are in days. Figure 4a uses 100×(ratio−1), computed from unrounded source values.

| 目标天数 / Target day | 分段长度（天） / Segment lengths (days) | N | 直接 MSE / Direct | 分段 MSE / Partitioned | 比值 / Ratio | 相对变化 / Change (%) |
|---|---|---:|---:|---:|---:|---:|
| 50 | 15+35 | 1615 | **0.027289** | 0.027750 | 1.016875 | 1.687 |
| 50 | 30+20 | 1615 | **0.027289** | 0.027772 | 1.017694 | 1.769 |
| 50 | 10+15+25 | 1615 | **0.027289** | 0.027929 | 1.023419 | 2.342 |
| 75 | 20+55 | 1568 | **0.035779** | 0.036384 | 1.016923 | 1.692 |
| 75 | 15+25+35 | 1568 | **0.035779** | 0.036561 | 1.021870 | 2.187 |
| 100 | 40+60 | 1617 | 0.037691 | **0.037401** | 0.992329 | -0.767 |
| 100 | 10+90 | 1617 | **0.037691** | 0.037893 | 1.005365 | 0.536 |
| 100 | 10+30+60 | 1617 | 0.037691 | **0.037591** | 0.997369 | -0.263 |
| 100 | 5+20+30+45 | 1617 | 0.037691 | **0.037478** | 0.994352 | -0.565 |

<p align="center">* 每行直接预测与分段预测中较低的MSE加粗。 / Within each row, the lower direct or partitioned MSE is bolded.</p>

比值范围为 0.992329—1.023419，即相对直接预测约 −0.77% 至 +2.34%。误差既有增加，也有降低。这说明在所测划分下，端点精度接近直接预测。

### English manuscript

#### D.1 Partitions and Evaluation Definitions

We evaluate nine temporal partitions absent from the training candidates in Appendix A.3 using the frozen SpanWorld checkpoint on the 2,856-sample IID manifest; all three endpoint dates receive supervision of direct predictions. Thus, unseen refers specifically to the temporal partition. This experiment compares direct and partitioned predictions at the same endpoint, without subsequent queries from that endpoint. Pooled MSE divides the total squared error by the total number of jointly valid pixels. There are 1,615, 1,568, and 1,617 eligible samples at days 50, 75, and 100, respectively. This estimand differs from the sample-averaged subsequent-window MSE in Appendix C.

#### D.2 Full Endpoint Results

Table D1 lists all nine partitions. The partitioned-to-direct MSE ratios range from 0.992329 to 1.023419, corresponding to changes of approximately −0.77% to +2.34%. Errors both increase and decrease. Endpoint accuracy remains close to direct prediction over the evaluated partitions.

<a id="appendix-e"></a>

## E. 模型生成状态的作用 / Contributions of Model-Generated States

### 中文稿

#### E.1 干预与固定条件

使用固定的SpanWorld权重，通过一次 50 天转移形成中间状态，随后将其替换为匹配供体在相同时刻形成的状态。接收样本的<span class="revision" style="color:blue">基础预测</span>、地理信息、后续天气和目标日期保持不变。供体限定为同一划分、相同观测起始年月，排除接收样本自身。历史前十步提供四个摘要：带掩膜的 NDVI 帧均值、帧标准差、最后有效帧均值及有效帧比例；各特征按训练校准池的中位数/IQR 标准化（零或非有限 IQR 置为 1）。距离为该四维向量的欧氏距离，加 0.5 倍归一化 256-bin 地类直方图的 Hellinger 距离。按样本相对路径依次进行最近邻匹配，平局按供体路径排序，每个供体最多使用一次；特征缺失或未匹配样本从两种预测中共同排除。匹配仅依据上述历史观测统计量、土地覆盖组成、样本资格条件和确定性分配规则。

后续第 55—100 天的有效区域使用接收样本自身的观测掩膜，并在原状态与替换状态之间保持一致。每个带上下文及预测窗口的清单条目作为一个接收样本。报告替换状态减原状态的 MSE 差，正值表示替换使预测变差。表 E1 分开列出完整后续时窗与第 100 天各自的资格集。主指标为样本等权；地理组等权与像素 pooled 仅改变聚合权重。各点估计均配套相同估计对象的 2,000 次配对空间重抽样 95% 区间，重抽样种子为 20260910，区间以固定的供体匹配与已训练模型为条件。

#### E.2 完整替换结果

**表 E1 / Table E1：状态替换的 MSE 差及 95% 区间 / State-replacement MSE differences and 95% intervals.** 每格为点估计 [下界, 上界]；三种聚合口径不互相替代。/ Each cell is an estimate [lower, upper]; the three weighting schemes are distinct.

| 窗口 / Window | 划分 / Split | N | 地理组 / Groups | 样本等权 / Sample-equal | 地理组等权 / Group-equal | 像素合并 / Pixel-pooled |
|---|---|---|---|---|---|---|
| 55–100 天 / days | IID | 2066 | 80 | 0.003192 [0.002537, 0.003848] | 0.003168 [0.002420, 0.003897] | 0.003399 [0.002657, 0.004120] |
| 55–100 天 / days | OOD-T | 1605 | 80 | 0.002192 [0.001660, 0.002708] | 0.002246 [0.001697, 0.002795] | 0.002368 [0.001784, 0.002967] |
| 55–100 天 / days | OOD-S | 6965 | 878 | 0.003345 [0.002975, 0.003719] | 0.003419 [0.003054, 0.003793] | 0.002617 [0.002200, 0.003028] |
| 55–100 天 / days | OOD-ST | 5437 | 878 | 0.001558 [0.001247, 0.001867] | 0.001558 [0.001237, 0.001878] | 0.001284 [0.000941, 0.001633] |
| 100 天 / day | IID | 1214 | 80 | 0.004109 [0.002808, 0.005303] | 0.003677 [0.002313, 0.004965] | 0.004336 [0.003215, 0.005373] |
| 100 天 / day | OOD-T | 884 | 80 | 0.003140 [0.002143, 0.004180] | 0.003228 [0.001965, 0.004465] | 0.002431 [0.001708, 0.003112] |
| 100 天 / day | OOD-S | 3549 | 852 | 0.003431 [0.002734, 0.004111] | 0.002767 [0.001892, 0.003610] | 0.002982 [0.002344, 0.003539] |
| 100 天 / day | OOD-ST | 2731 | 854 | 0.001004 [0.000364, 0.001668] | 0.000533 [-0.000222, 0.001314] | 0.000794 [0.000186, 0.001406] |

第55—100天后续时窗的四划分主指标均为正，区间均高于零；第 100 天的 OOD-ST 地理组等权区间跨零。完整后续时窗的结果表明，在保留<span class="revision" style="color:blue">基础预测</span>、地理条件与后续天气时，原样本自身生成的状态有助于继续预测。

补充的冻结模型干预将状态修正系数置零（\(\widehat Y_t=B_t\)），或将共享转移置为恒等映射（保留 \(S_0\) 的状态修正）。两者均保留历史信息，不重新训练。表E2报告完整100天预测窗口上的标准预测指标，正文表2列出其中的RMSE结果。

**表 E2 / Table E2：去状态修正与恒等转移 / Removing the state correction or using an identity transition.** 完整100天预测窗口；官方R²_LC与RMSE_LC。/ Full 100-day forecast window; official R²_LC and RMSE_LC.

| Split | Full R² | No correction R² | Identity transition R² | Full RMSE | No correction RMSE | Identity transition RMSE |
|---|---:|---:|---:|---:|---:|---:|
| IID | **0.5220** | <u>0.4883</u> | 0.4877 | **0.1555** | <u>0.1708</u> | 0.2150 |
| OOD-T | **0.5726** | <u>0.5555</u> | 0.5549 | **0.1509** | <u>0.1627</u> | 0.2150 |
| OOD-S | **0.4949** | <u>0.4614</u> | 0.4605 | **0.1621** | <u>0.1755</u> | 0.2196 |
| OOD-ST | **0.5408** | <u>0.5237</u> | 0.5232 | **0.1542** | <u>0.1650</u> | 0.2164 |

<p align="center">* 每个划分、每项指标内，最佳结果加粗，次佳结果加下划线。 / Within each split and metric, best results are bolded and second-best results are underlined.</p>

### English manuscript

#### E.1 Intervention and Fixed Conditions

Using the fixed SpanWorld checkpoint, we form the intermediate state with a single 50-day transition and replace it with a matched donor's state at the same time. The receiver's <span class="revision" style="color:blue">baseline</span>, geography, subsequent weather, and target dates remain fixed. Donors share the split and observation-start year/month, with self-matches excluded. Four summaries use the first ten observations: masked NDVI frame mean, frame standard deviation, last valid-frame mean, and valid-frame fraction. Features are standardized by training-calibration medians and IQRs, replacing zero or nonfinite IQRs with one. Distance combines Euclidean distance in this four-dimensional space with 0.5 times the Hellinger distance between normalized 256-bin land-cover histograms. Receivers are processed in relative-path order; nearest-neighbor ties are resolved by donor path, with at most one use per donor. Samples with missing features or no match are excluded from both conditions. Matching uses only the historical summaries, land-cover composition, eligibility criteria, and deterministic assignment rules described above.

We evaluate days 55–100 using each receiver’s observation mask, shared between original-state and donor-state predictions. Each manifest entry with its context and forecast window defines a receiver. Positive donor-minus-original MSE differences indicate harm from replacement. Table E1 separates the full subsequent window from the day-100 eligibility set. Sample-equal weighting is primary; group-equal and pixel-pooled results assess weighting sensitivity. Each estimate has a corresponding paired geographic-bootstrap 95% interval from 2,000 resamples with seed 20260910, conditional on the fixed matching and trained model.

#### E.2 Full Replacement Results

Primary differences over days 55–100 are positive on all four splits, with intervals above zero; the group-equal interval for day 100 on OOD-ST spans zero. The subsequent-window results show that the original sample's generated state contributes to continued prediction when its <span class="revision" style="color:blue">baseline</span>, geography, and subsequent weather are retained.

Additional frozen-model interventions set the state-correction coefficient to zero (\(\widehat Y_t=B_t\)) or replace the shared transition with the identity map (retaining the correction from \(S_0\)). Both preserve historical information, without retraining. Table E2 reports standard forecasting metrics over the full 100-day forecast window. Main-text Table 2 presents its RMSE results.

<a id="appendix-f"></a>

## F. 天气输入与预测响应 / Weather Inputs and Forecast Responses

### 中文稿

#### F.1 天气条件与配对协议

在冻结的 OOD-T 高温干旱子集上评估同一SpanWorld权重。筛选使用未来 100 天的日均温度均值与日降水均值；高温异常为温度的标准化偏差，干旱异常为降水的反向标准化偏差。训练气候统计按预测起始月与 3° 经纬网格计算，样本不足 30 或方差无效时依次回退至月份×6°纬度带及月份。预定的第 80 百分位方案要求高温异常≥0.845641、干旱异常≥0.820556，且未来温度与降水同时有效的日数比例≥0.80，得到 84 个样本。该覆盖率条件针对未来气温与降水记录的共同有效性。

正常天气供体的两项异常绝对值均≤0.75，并与接收样本处于相同气象季节（DJF/MAM/JJA/SON）。匹配采用年内日期、纬度、经度、植被比例、历史云比例、历史观测有效率、历史 NDVI 均值及未来天气有效率八项特征，在极端与正常候选组成的池上按均值/标准差标准化；标准化距离的均方根须≤1.5。按样本标识确定性匹配，每个供体最多复用五次，84 个配对使用 45 个唯一供体。匹配不使用未来 NDVI 或预测误差。

保留接收样本的历史、地理信息与权重，将完整 20 步未来天气替换为供体的有序天气序列，或将归一化天气张量置零。后者构成归一化均值天气条件。所有损失均在完整 100 天预测窗口的有效植被像素上计算，先求样本 MSE，再对样本等权平均。差值为替换天气损失减实际天气损失。区间使用 10,000 次重抽样，分别按 84 个配对、31 个地理组和 45 个复用供体组计算；图 4c 采用地理组区间。

#### F.2 预测响应与事实误差

**表 F1 / Table F1：天气替换的损失差与队列差异 / Loss differences under weather replacement and cohort interactions.** 前两行是热旱子集的替换减实际天气 MSE；后两行是该效应在热旱与匹配正常样本之间的差。/ The first two rows report replacement-minus-actual MSE on the hot-dry subset; the last two report hot-dry-minus-matched-normal differences in this effect.

| 比较 / Comparison | ΔMSE | 配对 95% CI / Paired | 地理组 95% CI / Geographic | 供体组 95% CI / Donor-group |
|---|---:|---|---|---|
| 供体−实际 / Donor−actual | 0.002053 | [0.000793, 0.003352] | [0.000761, 0.003452] | [0.000715, 0.003361] |
| 均值−实际 / Mean−actual | 0.010140 | [0.006782, 0.013770] | [0.004839, 0.015558] | [0.004760, 0.015883] |
| 供体替换：热旱−正常 / Donor effect: hot-dry−normal | -0.000302 | [-0.002321, 0.001759] | [-0.002841, 0.002582] | [-0.003153, 0.002443] |
| 均值替换：热旱−正常 / Mean effect: hot-dry−normal | 0.007838 | [0.004395, 0.011532] | [0.003225, 0.011961] | [0.002767, 0.013311] |

供体与均值替换均提高热旱子集的预测误差，均值替换增幅更大。对应的平均绝对预测变化分别为 0.034663 和 0.079716；该量为替换天气前后两份预测之间的平均绝对差。供体替换在热旱与正常样本之间的损失效应差区间跨零，未显示热旱子集具有更大的误差增幅。所有误差均以实际天气下的真实观测为评价目标。

### English manuscript

#### F.1 Weather Conditions and Pairing Protocol

We evaluate the same SpanWorld checkpoint on a frozen OOD-T hot-dry subset. Selection uses the means of daily temperature and precipitation over the next 100 days. Heat is a standardized temperature anomaly; dryness is the sign-reversed standardized precipitation anomaly. Training climatology is stratified by forecast-start month and 3° latitude–longitude cells, falling back to month×6° latitude bands and then month when fewer than 30 records or invalid variance prevent calibration. The predefined 80th-percentile tier requires heat≥0.845641, dryness≥0.820556, and jointly valid future temperature and precipitation on at least 80% of days, yielding 84 samples. This coverage criterion applies to the joint validity of future temperature and precipitation records.

Normal-weather donors have absolute heat and dryness anomalies ≤0.75 and share the receiver's meteorological season (DJF/MAM/JJA/SON). Eight matching features are day of year, latitude, longitude, vegetation fraction, historical cloud fraction, historical observation-validity fraction, historical mean NDVI, and future weather-validity fraction. Features are standardized by means and standard deviations of the combined extreme/normal candidate pool; root-mean-square standardized distance must be ≤1.5. Deterministic sample-ID ordering and a maximum of five uses per donor yield 84 pairs with 45 unique donors. Matching uses neither future NDVI nor prediction errors.

We retain each receiver's history, geography, and model weights while replacing all 20 future weather steps with the donor's ordered sequence or zeros in normalized weather space. The latter gives normalized-mean weather conditions. Losses cover valid vegetation pixels over the full 100-day window and are averaged equally across samples. Differences are replacement-minus-actual MSE. We use 10,000 bootstrap resamples, separately resampling the 84 pairs, 31 geographic groups, or 45 reused-donor groups; Figure 4c uses geographic-group intervals.

#### F.2 Prediction Responses and Factual Errors

Both replacements increase hot-dry forecasting error, with a larger increase under mean weather (Table F1). Mean absolute changes between predictions are 0.034663 for donor and 0.079716 for mean weather; these measure mean absolute differences between predictions before and after weather replacement. The hot-dry-minus-normal loss interaction under donor replacement has an interval crossing zero, with no clear evidence of a larger error increase on the hot-dry subset. All errors are evaluated against observations under the actual weather.

<a id="appendix-g"></a>

## G. 定性预测案例 / Qualitative Forecast Cases

### G.1 案例选择与显示协议 / Case Selection and Display Protocol

正文图 3 使用 IID 样本 P42（清单索引 2055，\(\texttt{MJJ19/minicube\_23\_30STJ\_39.19\_-5.73.nc}\)）在第 100 天（2019-08-05）的预测。两方案分别经 15+35 天形成第 50 天状态，再预测第 100 天；直接预测从初态到达同一日期，过程中不接收新影像。

案例候选池从 2,837 个共同后续时窗样本中，以后缀有效覆盖率≥0.40 得到 1,340 个候选，按“对照减 SpanWorld 的后缀 MSE”选取五个固定分位案例（10%、25%、50%、75%、90%），另纳入预先保留的 P42。图 3 的选择范围为上述六个案例中覆盖率≥0.40 的 41 个案例与后续日期组合，选择依据为两方案的单日退化差异。P42 是该有限候选集中的改善明显示例。

所有方案与路径共用观测和有效掩膜；NDVI 面板共用一套色带，绝对误差面板共用另一套。灰色表示无效或未评分像素，误差图显示预测与真实观测的绝对差。NDVI 显示范围为 [-0.6, 0.9]，绝对误差为 [0, 0.45]。MSE使用显示裁剪前的预测值计算。图 3 共评分 16,147/16,384 个像素，单帧直接/继续 MSE 分别为 SpanWorld 的 0.005882/0.004518 和对照的 0.005390/0.042048。总体结果由正文表1 及附录 C 给出。

Main-text Figure 3 uses IID sample P42 (manifest index 2055, \(\texttt{MJJ19/minicube\_23\_30STJ\_39.19\_-5.73.nc}\)) at day 100 (2019-08-05). Each model first forms its day-50 state through 15+35 days of rollout and then predicts day 100; direct forecasts query the same date from the initial state, without new imagery.

The candidate pool retained 1,340 of the 2,837 common-window samples with suffix coverage≥0.40. It included cases at five fixed quantiles (10%, 25%, 50%, 75%, 90%) of control-minus-SpanWorld suffix MSE, plus the preselected P42. Figure 3 was selected from 41 case–target-date combinations with coverage≥0.40 across these six cases, based on the between-model difference in single-date degradation. P42 illustrates a marked improvement within this restricted pool.

All models and routes share observations and validity masks. NDVI panels share one color scale, and absolute-error panels share another. Gray denotes invalid or unscored pixels; error maps show absolute differences between predictions and observations. NDVI and absolute-error display ranges are [-0.6, 0.9] and [0, 0.45]. MSE is computed from predictions before display clipping. Figure 3 scores 16,147 of 16,384 pixels. Direct/continued frame MSEs are 0.005882/0.004518 for SpanWorld and 0.005390/0.042048 for the control. Aggregate results appear in Table 1 and Appendix C.

### G.2 补充案例 / Additional Cases

图 G1 使用同一 P42 的第 25 与 75 天，日期在出图前固定，不按单帧误差择优。图 G2 使用第 10 百分位案例 Q10（清单索引 2132，\(\texttt{MJJ19/minicube\_91\_31UGS\_50.56\_5.89.nc}\)）；第70天（2019-07-05）仅依据有效像素覆盖率选取，该日期在后续预测窗口内的覆盖率最高，为0.9682。两图沿用 G.1 的显示与评分规则。

Figure G1 uses P42 at days 25 and 75, fixed before rendering rather than selected by frame error. Figure G2 uses the tenth-percentile case Q10 (manifest index 2132, \(\texttt{MJJ19/minicube\_91\_31UGS\_50.56\_5.89.nc}\)). Day 70 (2019-07-05) is selected solely for its maximum valid-pixel coverage (0.9682) within the subsequent window. Both figures follow the display and scoring rules in G.1.

![G1 标准预测案例](附录/图版/H1_标准预测案例.png)

**图 G1 / Figure G1：标准预测补充案例 / Additional standard forecasts.** P42 第 25/75 天的观测、SpanWorld 与官方 PredRNN 1M 预测及绝对误差。SpanWorld/PredRNN 单帧 MSE 分别为 0.005089/0.002808、0.005728/0.003597；该例中 PredRNN 误差较低。/ Observations, SpanWorld and official PredRNN 1M predictions, and absolute errors at days 25/75 for P42. Frame MSEs for SpanWorld/PredRNN are 0.005089/0.002808 and 0.005728/0.003597; PredRNN has lower error in this example.

![G2 继续预测退化案例](附录/图版/H2_续推不利案例.png)

**图 G2 / Figure G2：继续预测退化案例 / Degradation in continued prediction.** Q10 经 15+35 天形成第 50 天状态后预测第 70 天。上行为 SpanWorld，下行为直接端点监督对照；Direct 从初态预测，Continued 从生成状态预测。直接/继续 MSE 分别为 0.024007/0.030284、0.025428/0.024308，展示总体改善之外的个例退化。/ Q10 at day 70 after a 15+35-day rollout to day 50. SpanWorld is shown above the direct-endpoint control; Direct starts from the initial state and Continued from the generated state. Direct/continued MSEs are 0.024007/0.030284 and 0.025428/0.024308, illustrating a case of degradation despite the aggregate improvement.

<a id="appendix-h"></a>

## H. 资源、权重身份与适用范围 / Resources, Checkpoints, and Scope

### 中文稿

表 H1 汇总核心结果权重对应的正式训练阶段资源。SpanWorld 与同架构直接端点监督对照从同一已训练父权重开始；设备、更新次数及实测计算成本列于表中。

证据范围为给定天气、有限预测窗口及五日步整数倍跨度；预测期间没有新增遥感观测或在线同化。

### English manuscript

Table H1 summarizes resources for the formal training stages that produced the checkpoints used in the core comparison. SpanWorld and its same-architecture direct-endpoint control start from the same trained parent weights; the table lists devices, update counts, and measured compute.

The evidence concerns given weather and a finite forecast window, with variable spans in integer multiples of five-day steps. No new remote-sensing observation or online assimilation enters during prediction.

### H 节共用数值表 / Numeric Table for Section H

**表 H1 / Table H1.** 核心结果权重所对应的当前正式阶段。Allocated GPU-hours = 4 × elapsed wall-hours；不含共同父模型的更早训练。/ Current formal stages mapped to the core-result checkpoints. Allocated GPU-hours = 4 × elapsed wall-hours; earlier shared-parent training is excluded.

| Training scheme | Parameters | Devices × batch/device × accumulation | Global batch | Updates | Wall-hours | Allocated GPU-hours |
|---|---:|---|---:|---:|---:|---:|
| SpanWorld partitioned-path learning | 7,180,896 | 4 × 8 × 2 | 64 | 14,880 | 5.901 | 23.606 |
| Direct-endpoint supervision control | 7,180,896 | 4 × 8 × 2 | 64 | 14,880 | 5.665 | 22.661 |


## I. 训练目标与动态状态分支消融 / Training-Objective and Dynamic-State-Branch Ablations

> 编辑说明（不进入投稿）：当前结果属于D配置、seed42、固定第40轮；不能改标为B配置。最终主模型确定后核对归属。原始结果及选模敏感性证据保留，本节不代表核心三配对种子结果。

<span class="revision" style="color:blue">我们在匹配的公共训练设置下，对各组模型训练40轮后的表现进行消融比较，均采用seed42。</span>

<span class="revision" style="color:blue">We compare the models after 40 epochs of training under matched common training settings, using seed 42 throughout.</span>

### 表I1：补充消融结果 / Table I1: Supplementary ablation results

#### A. 训练目标比较 / Training-objective comparison

<span class="revision" style="color:blue">训练目标比较包括完整方案、直接终点对照和一致性替代。各组保留全部目标日期的直接观测监督；一致性替代采用相同分段路径，将额外真实端点监督替换为对同日期停止梯度的直接预测的匹配。表I1A报告共同后缀的直接预测MSE和三条路径的续预测MSE。</span>

<span class="revision" style="color:blue">The training-objective comparison includes the full model, the direct-endpoint control, and the consistency alternative. All retain direct observed-image supervision at every target date. The consistency alternative uses the same partitioned paths and replaces additional observed-endpoint supervision with agreement to stop-gradient direct predictions at the same dates. Table I1A reports direct and continued prediction MSE on the common suffix for the three paths.</span>

| 模型 / Model | 直接 / Direct MSE | 50天 / days | 25+25天 / days | 15+35天 / days |
|---|---:|---:|---:|---:|
| <span class="revision" style="color:blue">完整方案 / Full</span> | <span class="revision" style="color:blue">0.04121391</span> | <span class="revision" style="color:blue">0.04143541</span> | <span class="revision" style="color:blue">0.04183792</span> | <span class="revision" style="color:blue">0.04174650</span> |
| <span class="revision" style="color:blue">直接终点对照 / Direct-endpoint control</span> | <span class="revision" style="color:blue">0.04361874</span> | <span class="revision" style="color:blue">0.04399701</span> | <span class="revision" style="color:blue">0.04965237</span> | <span class="revision" style="color:blue">0.04869256</span> |
| <span class="revision" style="color:blue">一致性替代 / Consistency</span> | <span class="revision" style="color:blue">0.04284155</span> | <span class="revision" style="color:blue">0.04299178</span> | <span class="revision" style="color:blue">0.04317601</span> | <span class="revision" style="color:blue">0.04311991</span> |

<span class="revision" style="color:blue">完整方案在三条受测路径上均取得最低的续预测MSE，其中训练未见的15＋35天路径较一致性替代降低3.19%。</span>

<span class="revision" style="color:blue">The full model achieves the lowest continuation MSE on all three evaluated paths, reducing MSE by 3.19% relative to the consistency alternative on the training-unseen 15+35-day path.</span>

#### B. 动态状态分支重训比较 / Dynamic-state-branch retraining comparison

<span class="revision" style="color:blue">在上述公共训练设置下，我们移除动态状态分支及其读出，重新训练仅保留基础预测的模型，并将相应的额外端点监督施加于基础预测。表I1B报告完整模型与该重训模型在四个测试划分上的标准预测RMSE与R²。完整模型在四个划分上均取得更高的R²；两组RMSE数值接近，其中完整模型在OOD-S上更低，在其余划分上略高。</span>

<span class="revision" style="color:blue">Under the same common training settings, we remove the dynamic state branch and its readout and retrain the baseline-only model, applying the corresponding additional endpoint supervision to the baseline forecast. Table I1B reports standard forecasting RMSE and R² for the full and retrained models on all four test splits. The full model has higher R² on all four splits; RMSE values are numerically close, with lower RMSE on OOD-S and slightly higher RMSE on the other splits.</span>

| 划分 / Split | 完整 RMSE↓ / Full | 移除分支 RMSE↓ / Without branch | 完整 R²↑ / Full | 移除分支 R²↑ / Without branch |
|---|---:|---:|---:|---:|
| IID | <span class="revision" style="color:blue">0.149114</span> | <span class="revision" style="color:blue">0.149090</span> | <span class="revision" style="color:blue">0.530113</span> | <span class="revision" style="color:blue">0.528091</span> |
| OOD-T | <span class="revision" style="color:blue">0.145669</span> | <span class="revision" style="color:blue">0.145483</span> | <span class="revision" style="color:blue">0.578613</span> | <span class="revision" style="color:blue">0.575506</span> |
| OOD-S | <span class="revision" style="color:blue">0.156579</span> | <span class="revision" style="color:blue">0.156827</span> | <span class="revision" style="color:blue">0.496896</span> | <span class="revision" style="color:blue">0.494428</span> |
| OOD-ST | <span class="revision" style="color:blue">0.150780</span> | <span class="revision" style="color:blue">0.150481</span> | <span class="revision" style="color:blue">0.546021</span> | <span class="revision" style="color:blue">0.544087</span> |
