# ObsWorld：可由观测校正的遥感世界模型——整体框架、Stage2 训练与 AAAI 实验定稿

> **2026-07-15 后续决策说明：**本文的代码审计、协议风险和 overclaim 检查仍然有效；但其“稀疏/局部观测 + `U` 校正”为中心的定调对 EO-WM 反应过度，弱化了初版 ObsWorld 的 `phi`、DGH 与“状态推断—状态演化—观测生成”三柱。有关 EarthNet/GreenEarthNet 关系、DGH 保留、新中心叙事、Stage2 variable-step transition 与 AAAI 实验的当前规范性方案，以 [`44_ObsWorld_EarthNet_DGH主线重整_20260715.md`](44_ObsWorld_EarthNet_DGH主线重整_20260715.md) 为准。本文保留为上一轮审计记录，不再作为唯一方法定稿。

> 日期：2026-07-15  
> 状态：**历史审计版本；其中关于“9.2/10、9.3/10”的评分属于本版本当时的内部复审记录，不代表方法已被实验验证，也已被后续更严格复审重新打开。正式实验结果尚不存在。**  
> 本文定位：保留为 01–42 之后的代码、协议与 overclaim 审计记录；当前规范性决策文档是 44。  
> 本轮只整理理论、方法、实验和代码风险；**没有修改训练代码。**  
> 本次文字优化说明：本版优先提升中文可读性，没有把现有 Stage2 和实验设计视为不可修改；下一轮仍可依据前沿研究、AAAI 篇幅和代码可行性进行实质性重审与大改。

---

## 阅读指南：先用中文快速理解，再保留英文用于论文写作

本文采用“**中文含义在前，英文术语在后**”的写法。模型名、变量名、指标缩写和投稿时需要使用的标准术语仍保留英文，但第一次出现时给出中文解释。阅读时可先看中文；真正写论文或对照代码时，再看括号中的英文。

### 核心术语速查

| 英文或缩写 | 本文统一中文含义 | 在 ObsWorld 中具体指什么 |
|---|---|---|
| EO / Earth Observation | 对地观测、遥感观测 | 以卫星 RGBN/NDVI 为主的地表观测 |
| world model | 世界模型 | 维护内部状态、推演未来、生成观测并吸收新证据的模型 |
| partial observation | 部分可观测 | 云遮、时间稀疏和传感器限制使卫星无法看到完整地表状态 |
| predictive belief / belief | 预测信念状态 | 由全部历史信息形成、用于预测未来的内部状态 `b_t`；不等于真实物理状态 |
| prior / posterior | 更新前状态 / 更新后状态 | 新观测进入前的 `b_t-` 与吸收新观测后的 `b_t+` |
| observation evidence | 观测证据 | 当前卫星图像在晴空有效区域提供的信息 |
| forcing | 外生驱动 | 气象、日历和静态地理等推动地表变化、但不由模型内部产生的条件 |
| observation model / decoder | 观测模型 / 解码器 | 将内部 belief 解码为 RGBN；NDVI 由 Red/NIR 确定性计算 |
| open-loop rollout | 开放循环推演 | 未来没有新卫星观测时，仅依靠内部状态与外生驱动连续预测 |
| update / correction | 状态更新 / 校正 | 新观测到达后修正内部 belief |
| aligned residual / innovation | 对齐残差 / 创新量 | 同一可见区域、同一特征空间中“真实观测减去预测观测”的差异 |
| visibility-safe | 可见性安全 | 只有存在有效观测证据的位置可以更新；无证据位置保持不变 |
| reveal | 揭示新观测 | 在训练或评估的指定未来时刻向模型提供一帧真实局部观测 |
| Direct-Seq | 直接多步预测对照 | 从同一个 context 状态分别查询各预测时刻，不递归传递未来状态 |
| matched control/baseline | 匹配对照 / 基线 | 尽量保证输入、参数量、监督和计算量相同，只比较目标机制 |
| ablation / deletion | 消融 / 删除实验 | 删除或替换某个组件，判断它是否真正必要 |
| OOD | 分布外测试 | 测试时间、空间或时空组合超出训练分布 |
| locked test | 锁定测试集 | 完成验证集选型后只评一次，避免根据测试结果反复调参 |
| non-inferiority | 非劣效性 | 证明 ObsWorld 的开放循环预测没有显著差于强 Direct 对照 |
| paired bootstrap | 配对自助法 | 在同一地理单元和样本上比较方法，并通过重复重采样估计置信区间 |
| downstream task | 下游任务 | 分类、分割等用于检验表示迁移能力的额外任务 |
| foundation model / FM | 基础模型 / 大模型 | AnySat、TerraMind 等大规模预训练遥感模型 |
| claim | 论文主张 | 论文希望实验支持的明确结论 |
| gate / stop rule | 阶段门槛 / 止损规则 | 只有前一阶段证据通过才继续投入后续训练 |

### 一张文字流程图读懂全文

```text
连续演化的地表世界
        ↓ 只能被卫星稀疏、局部地观测
历史观测 → predictive belief b_t（预测信念状态）
        ↓ F_5 + forcing（状态转移 + 外生驱动）
未来 belief → H → 未来 RGBN → Red/NIR → NDVI
        ↑
局部新观测 → aligned residual（对齐残差）→ U（状态校正）
```

全文最重要的区分是：**“世界模型”说明我们在解决什么系统问题；“对齐残差校正”说明我们提出了什么具体新方法。**

---

## 0. 最终结论先行

### 0.1 旧主线中最值得保留与必须放弃的部分

值得保留：

1. EO 是**部分可观测问题（partial observation problem）**，而不仅是视频外推；
2. 需要区分**依赖历史的预测信念状态（history-dependent predictive belief）**与**单帧观测证据（observation evidence）**；
3. 未来气象（future weather）、日历信息（calendar）和静态地理条件（static geography）的角色必须分开；
4. 一个模型应同时支持无新观测时的**开放循环推演（open-loop rollout）**与新观测到来后的**状态更新（update）**；
5. 世界模型叙事必须由可观察的模型行为支撑，不能只靠隐状态（latent）、`D/G/h` 或模块命名。

必须放弃或降级：

1. **“首个 EO 世界模型（first EO world model）”**：EO-WM 已直接采用“部分可观测、气象驱动的 EO 世界模型”叙事；
2. **“五日递归本身就是创新或半群性质（semigroup）”**：PredRNN、UniTS 等早已使用自回归；重复调用固定的 `F_5` 只是架构定义；
3. **“Stage1.5 已分离真实状态与观测条件”**：当前 S1/S2 近时配对并非只改变干扰因素的纯配对（nuisance pair），GreenEarthNet 主任务也没有端到端使用 `phi`；
4. **“天气敏感性就是响应正确或因果”**：未来 E-OBS 属于基准中预先给定的外生驱动或再分析数据（benchmark forcing/reanalysis）；人工缩放输入后输出发生变化，只能证明模型对输入敏感，不能证明响应在因果意义上正确；
5. **“必须增加下游与大模型才像 AAAI”**：对本稿的动力学与校正主张（dynamics/correction claim），它们反而会削弱因果归因；
6. **“当前直接预测版 Stage2 已经是递归推演（rollout）”**：当前代码从同一个 `z_context` 独立查询各预测跨度（horizon），本质上是直接多时距预测器（direct multi-horizon predictor）。

这里必须纠正上一版的措辞：上述边界意味着放弃 **“首个、完整、物理因果的地球模拟器”**，不意味着放弃世界模型。把系统级问题也一起降成一个局部校正模块（correction module），是矫枉过正。

### 0.2 最终中心叙述：世界模型是母叙事，对齐残差是方法创新

论文应明确围绕 **可由新观测校正的对地观测世界模型（observation-correctable Earth observation world model）**。卫星图像不是连续世界本身，而是对持续演化地表过程的稀疏、局部且受云影响的观测。因此，遥感世界模型不应只把历史图像序列块（image cube）映射成未来序列块，而应：

1. 维护由完整历史形成的预测信念状态（predictive belief）`b_t`；
2. 在给定气象、日历和静态地理外生驱动（forcing）时，用 `F_5` 推演 belief；
3. 用学习得到的观测模型（learned observation model）`H` 将 belief 解码为未来 RGBN 观测；NDVI 由红光与近红外波段（Red/NIR）确定性计算，用于监督与评估；
4. 当新的局部可见观测到达时，用更新模块 `U` 校正 belief；
5. 在此后没有新观测时继续进行开放循环推演（open-loop rollout）。

系统级中心命题：

> **Satellite forecasting is world modeling under partial observation: a useful EO world model must not only roll a predictive belief forward and decode future observations, but also correct that belief when sparse, cloud-free evidence arrives.**

中文速读：

> **卫星遥感预测本质上是部分可观测条件下的世界建模：一个有效的 EO 世界模型不仅要向前推演预测信念状态并生成未来观测，还要在稀疏的晴空证据到来时校正该状态。**

方法级唯一新意仍然是一个范围明确、可被实验否定的机制：

> **ObsWorld learns an observation-correctable predictive state for sparse Earth observation. When a partial new image arrives, the model compares the real observation with its prior decoded prediction under the same visibility mask and observation encoder, then uses this aligned residual to update only supported state regions; the update is trained solely through improvements in subsequent forecasts.**

中文速读：

> **ObsWorld 学习一种可由稀疏 EO 新观测校正的预测状态。新观测到达时，模型在相同可见区域和相同观测编码器中比较真实图像与更新前预测，形成对齐残差；只有存在证据的位置可以更新 belief，而这次更新是否有效，只由后续预测能否改善来判断。**

这不是新的贝叶斯滤波理论（Bayesian filtering theory），而是 **EO 局部云遮条件下的观测对齐残差校正（observation-aligned residual correction）**。因此两层叙事并不冲突：**世界模型定义论文在解决什么系统问题；对齐残差定义我们具体提出了什么新方法。**

“模拟真实世界”的合法边界是：

> **simulating EO-observable Earth-surface evolution under supplied meteorological, calendar, and geographic forcing**

中文速读：

> **在给定气象、日历和地理外生驱动的条件下，模拟未来能够被遥感系统观测到的地表演化。**

即模拟给定外生条件下未来可被卫星产品观测到的地表演化，而不是声称模拟完整地球物理、恢复唯一真实状态、建立因果数字孪生或进行业务天气预报。

推荐标题：

> **ObsWorld: An Observation-Correctable World Model for Sparse Earth Observation Forecasting**

中文含义：

> **ObsWorld：面向稀疏对地观测预测、可由观测校正的世界模型**

### 0.3 对用户四个问题的直接回答

1. **整体思路是否有问题？**  
   有。主要问题不是模块无法实现，而是早期贡献过多：belief 被错误绑定到单帧隐表示（latent），`phi` 与主任务脱节，直接预测（direct prediction）被误写成递归推演（rollout），天气相关主张与 EO-WM 重叠，而且主实验没有先锁定官方协议。修订后只保留一个世界模型母叙事和一个主导机制（dominant mechanism），不能再把它们拆成多项平行创新。

2. **Stage2 应该长什么样？**  
   不再把 `z_context + D + G + h -> 每个终点时刻（endpoint）` 作为唯一主模型。最终 Stage2 使用同一组 `F_5/U` 按时间顺序处理十帧上下文观测；未来没有新观测时用 `F_5` 开放循环推演；训练中有一半样本随机揭示一帧未来观测，再使用对齐残差通过 `U` 更新状态并继续预测。Direct-Seq 保留为输入和训练条件匹配的对照（matched control）。

3. **主实验应该在训练数据、另一个数据集，还是 EarthNet2021？**  
   主实验应采用 **GreenEarthNet 官方训练集、验证集和锁定的时间分布外测试协议（Train/Val/locked OOD-t protocol）**，而不是在训练集上报告精度，也不必为了形式强行跨数据集。空间分布外与时空分布外测试（OOD-s/OOD-st）是次级泛化轨道。只有重新提出天气响应正确性（weather-response）主张时，才必须在原始 EarthNet2021 上复现 EO-WM 的匹配样本协议（matched-pair protocol）；当前它不是主实验。

4. **AAAI 主实验、下游和其他实验怎样排？**  
   三块足够：RQ1 验证官方 20 个未来时刻的开放循环世界推演；RQ2 在全部样本上验证第 25/50 天的新观测校正，并与 VanillaFilter、PredRNN-online 比较；RQ3 检查世界模型行为契约与最小消融。当前不做无关下游或基础模型 2×2 组合。AAAI 是会议，不是“AAAI 期刊”；在尚无 Stage2 结果的情况下，不应把 2026-07-28 的 AAAI-27 正文截止日期当作可信的从零投稿目标。

---

## 1. 全部 MD 演进审查，而非只看前几个

本轮完整读取了目录内 **49 个 Markdown 文件，约 30,831 行、1.13 MB**，并按演进阶段理解，而不是只采纳前几份“定稿”。

### 1.1 01–08：问题意识正确，但贡献边界过宽

早期文档正确区分了观测模型（observation model）、潜在状态（latent state）与动力学（dynamics），也意识到 EO 观测并不等于完整世界状态。但它们同时把状态—观测分离、世界模型、天气响应、反事实分析和下游迁移都写成并列贡献，导致任何一条证据不足都可能拖垮整篇论文。

最终保留“部分可观测 + 预测状态（partial observation + predictive state）”这一核心问题，删除“大而全”的贡献清单。

### 1.2 09–21：实现开始具体，但“字段/模块存在”不等于理论成立

这些文件的重要价值是把 SSL4EO、phi、FiLM、Stage1/1.5、S1 geometry、DEM 和训练流程真正落到代码字段上。需要修正的推理是：

- 编码器（encoder）接收 `phi`，不等于潜在表示已经去除采集条件干扰（acquisition nuisance）；
- 解码器（decoder）接收 `phi`，不等于状态与观测已经可以被唯一识别或分离；
- S1/S2 七日内配对不等于“真实状态完全相同、只有观测算子不同”；合成孔径雷达（SAR）与光学观测包含互补物理信息；
- 对池化特征做线性去相关或探针实验（pooled linear decorrelation/probe），不能证明每个 token 都相互独立。

### 1.3 22–30：D/G/h 让 Stage2 可实现，但时间角色被混在一起

这些文件正确引入：

- `D`：外生驱动（forcing）；
- `G`：静态地理条件（static geography）；
- `h`：预测跨度。

最终必须再拆出：

- `C_t`：绝对日历时间或年内日序（calendar/DOY）；
- `w_t`：逐步气象驱动（stepwise weather），表示每个五日区间的 forcing；
- `h`：只提供给 Direct 的终点查询（endpoint query）；共享 `F_5` 不需要额外的预测跨度身份（horizon identity）；
- `s_t`：按观测证据加权的陈旧度（evidence-weighted staleness）；
- `a_t`：当前时刻是否有观测（observation availability）。

否则，累计气象摘要（cumulative weather）、年内日序（DOY）和预测跨度（horizon）很容易相互替代，实验将无法说明模型真正利用了哪类信息。

### 1.4 31–37：GreenEarthNet 主任务选对，但直接预测被错误写成递归推演

这些文件的重要进步，是把主任务从泛化的 EarthNet 想法收缩到可复现的基准（benchmark）。然而，当前 Stage2 代码会为每个预测跨度复制相同的上下文状态（context state），再用 `D/G/h` 独立预测，并不存在 `b_5 -> b_10 -> ...` 的未来状态传递。因此，它只能称为 Direct-Seq，即直接多步预测模型。

修订结论：**不删除直接预测分支（direct）；应把它做强，并作为检验递归世界模型是否真正必要的机制对照。**

### 1.5 38–42：已接近正确问题，但需要吸收 2026 前沿与接口审查

这些文件已经提出“由真实观测约束的预测状态（observation-grounded predictive state）”、RQ1–RQ4、GreenEarthNet 主任务和可选下游，方向明显改善。仍需修正：

- 共享递归推演（shared rollout）本身不足以构成新颖性；
- 将完整 belief 对齐到单帧隐表示（single-frame latent），会抹掉历史记忆；
- 再观测更新模块 `U` 不能继续只作为远期扩展（stretch goal）；
- 天气响应（weather response）与 EO-WM 已有工作重叠；
- `phi` 未在 GreenEarthNet 端到端流程中真正生效；
- 状态校正实验与事实预测实验（factual forecast）必须使用各自合适的指标，不能混在一起。

### 1.6 周报、未命名、简要改动、精度对标与问题汇总同样重要

44–49 并非可忽略的杂项。它们提供了：

- 真实训练/代码完成度，而非概念稿中的假定完成度；
- EuroSAT 探针实验（probe）数值与模型检查点（checkpoint）状态；
- 状态桥接模块（state bridge）、`D/G/h`、掩码（mask）与 Stage2 的具体改动；
- 未解决问题的集中列表。

它们直接推翻了“Stage1.5/Stage2 已经具备论文证据”的假设：本地目前只有 Stage1 探针结果，没有 Stage1.5/Stage2 的正式实验结果（formal results）。

---

## 2. 理论定位：部分可观测、受外生驱动的 EO 世界模型

### 2.1 可辩护的世界模型定义

首先定义历史信息集合（history）：

```text
H_t = {available observations, masks, weather, calendar, static geography}_{<=t}
```

belief `b_t` 的目标不是恢复唯一的真实地表物理状态，而是成为对未来观测和任务足够的预测状态（predictive state）：

```text
p(o_{t+1:t+K} | H_t, future forcing)
≈ p(o_{t+1:t+K} | b_t, future forcing)
```

这一定位与预测状态表示（predictive-state representation）以及 PlaNet/RSSM 中的部分可观测建模思想一致，但本稿不声称理论首创。

### 2.2 更新前状态、观测证据与更新后状态不能混为同一个隐表示

错误接口：

```text
b_t- ≈ E(o_t)
```

`b_t-` 是更新前状态（prior），应保存历史中当前图像不可见的信息；`E(o_t)` 只是当前单帧提供的观测证据（evidence）。强迫二者整体相等，会使 belief 丢失历史记忆。

正确接口：

```text
b_t- = F(b_{t-1}+, controls)
e_t  = observation evidence
b_t+ = U(b_t-, e_t, visibility)
```

因此，最终 Stage2 删除以下设计：以单帧定义完整状态的隐空间目标（whole-state latent target）、指数滑动平均目标适配器（EMA target adapter），以及锚定到单帧的隐表示匹配（one-frame anchored latent matching）。

### 2.3 本稿可以与不可以声称什么

可以：

- 可由新观测校正的 EO 世界模型（observation-correctable EO world model）；
- 在给定外生驱动下，对“EO 可观测地表演化”进行数据驱动模拟（data-grounded simulation）；
- 观测对齐残差校正（observation-aligned residual correction）；
- 可见性安全的预测状态更新（visibility-safe predictive state update）；
- 受外生驱动约束的开放循环推演与在线校正（forcing-conditioned open-loop and online correction）；
- 面向固定 Sentinel-2 产品的基准预测（fixed-product S2 benchmark prediction）。

不可以：

- 声称隐状态（latent）等于真实物理状态（physical state）；
- 声称完成了可识别的状态—观测分解（identifiable decomposition）；
- 声称对所有传感器和产品都具有采集条件不变性（acquisition invariance）；
- 声称得到了因果正确的天气响应（causal weather response）；
- 声称可以进行业务天气预报（operational weather forecast）；
- 声称提出了新的通用滤波理论；
- 声称这是首个 EO 世界模型。

### 2.4 世界模型行为契约（world-model contract）与当前框架的对应关系

```text
Predict:  b_t-   = F_5(b_{t-1}+, u_t)
Observe:  x_t-   = H(b_t-)
Update:   b_t+   = U(b_t-, x_t, x_t-, m_obs_t)
Imagine:  b_{t+k}- = F_5^k(b_t+, u_{t+1:t+k})
```

其中，`u_t` 表示气象、日历和地理外生驱动，不是智能体动作（agent action）。EO 世界模型不必像机器人世界模型那样拥有动作输入，但必须明确区分外生条件、内部状态推进、观测生成和新证据更新。

| 世界模型必要能力 | ObsWorld 实现 | 必须提供的证据 | 主张边界 |
|---|---|---|---|
| 历史依赖的预测状态 | 全部上下文观测经共享 `F/U` 顺序形成 `b_t` | 顺序上下文（sequential-context）与匹配的直接/递归对照 | `b_t` 是 predictive belief，不是真实物理状态 |
| 时间状态转移 | 共享五日转移 `F_5` | 100 天开放循环误差随时距变化曲线与官方指标 | 递归（recurrence）本身不是创新 |
| 外生条件建模 | 气象、DOY、DEM/静态地理 | true/no-weather 训练对照，以及正确/错时气象检查 | 只证明使用了时间对齐的 forcing，不证明因果 |
| 学习式观测模型 | `H(b_t)` 输出 RGBN；NDVI 由 Red/NIR 确定性计算 | 预测准确性与定性推演样例 | `H` 不是辐射传输或物理传感器模拟器 |
| 部分观测推断 | 可见性安全的更新模块 `U` | 第 25/50 天、覆盖全部样本的配对校正实验 | 对齐残差才是方法创新 |
| 开放循环想象/推演 | 未来 `a_t=0`，重复调用 `F_5/H` | 锁定 OOD 上完整 20 步推演 | 当前是确定性模型，不能声称多模态未来或校准不确定性 |

因此，本稿能否称为世界模型，并不取决于“latent 是否就是真实世界”或“是否存在 agent action”，而取决于是否具备可检查的**状态转移—观测生成—证据更新状态机（transition–observation–update state machine）**，以及是否提供相应的行为证据。

---

## 3. 最终整体框架

### 3.1 阶段角色

#### Stage 1：通用 EO 观测表示学习

保留现有 S1/S2 掩码重建预训练（masked reconstruction/pretraining）。这一阶段只提供编码器初始化（encoder initialization），不承担地表动力学相关主张。

#### Stage 1.5：可选的初始化改进

修复后的状态桥接模块（repaired state bridge）可以继续训练和验证，但它始终只是初始化消融（initialization ablation）：

- `Stage1/S2-only`：只使用 Stage1 的 S2 分支；
- `old bypass`：旧版旁路连接；
- `repaired Stage1.5 state bridge`：修复后的 Stage1.5 状态桥接。

只有当预测效用、语义效用和 Stage2 验证集性能都不退化时，Stage1.5 才值得在实验表中保留一行。没有严格的跨产品配对（product pair）时，只能称为**跨传感器预测预训练（cross-sensor predictive pretraining）**，不能称为状态—观测解耦（state/observation disentanglement）。

#### Stage 2：论文主方法

Stage2 的核心是让同一组 `F_5/U` 同时承担以下过程：

1. 按时间顺序融合全部上下文帧（chronological filtering）；
2. 在未来没有新观测时进行开放循环状态转移；
3. 在指定未来时刻接收一帧新观测并进行可选校正；
4. 解码器生成 RGBN，官方任务使用由 Red/NIR 计算得到的 NDVI。

### 3.2 变量契约

```text
x_t        RGBN 遥感观测
a_t        当前时刻是否有观测（0/1）
m_clear    当前观测中的晴空/有效像素
m_obs      a_t * m_clear；只有它可以进入状态更新
q_obs      patch 级连续晴空比例
m_rgb_sup  仅用于 RGBN 损失的监督掩码
m_ndvi_sup 仅用于官方 NDVI 损失和评估的监督掩码
w_t        五日气象驱动嵌入
C_t        绝对日历时间/年内日序（DOY）
G          DEM 与静态地理条件
s_t        按观测证据加权的状态陈旧度
b_t-/b_t+  更新前/更新后的预测信念状态（prior/posterior belief）
```

必须严格遵守：即使未来目标掩码已经被数据加载器读入并用于计算损失，只要 `a=0` 表示该时刻没有向模型揭示观测，这些目标掩码就绝不能影响模型状态。

### 3.3 顺序处理上下文并形成更新前状态（prior）

模型从学习得到的初始状态 `b_init` 出发，十个上下文帧都使用同一个状态转移与更新接口：

```text
s_t- = min(s_{t-1}+ + 5/100, 1)
b_t- = F_5(b_{t-1}+, w_t, C_t, G, s_t-)

if a_t = 1:
    b_t+ = U(b_t-, observation_t)
else:
    b_t+ = b_t-
```

中文解释：每经过五天，`F_5` 先根据上一状态、气象、日历、地理信息和陈旧度形成新的更新前状态 `b_t-`。若当前有观测，则调用 `U` 得到更新后状态 `b_t+`；若没有观测，更新后状态直接等于更新前状态。

删除独立上下文聚合器（context aggregator）的核心理论角色。这样，上下文状态与未来状态不再由两套语义不同的模块产生，整条时间轴都服从同一个世界模型状态机。

### 3.4 观测对齐残差（observation-aligned residual）

当当前时刻存在可用观测时，先由更新前状态生成模型原本预期看到的观测（prior prediction）：

```text
x_pred = H(b_t-)
z_obs  = P(E(x_t    * m_obs_t))
z_pred = P(E(x_pred * m_obs_t))
r_t    = z_obs - stopgrad(z_pred)
```

中文解释：`x_pred` 是 belief 解码出的预测图像；`z_obs` 是真实可见观测的特征；`z_pred` 是同一可见区域内预测图像的特征；`r_t` 是二者之差。`stopgrad` 表示残差分支不能通过反向传播去“篡改”当前预测，使残差看起来更小。

真实与预测两条分支使用相同掩码、RGBN 归一化、编码器/投影器和 token 网格，从而保证 `r_t` 表示**观测空间中的真实不一致（observation-space mismatch）**，而不是由自由模块 `Q` 学出的任意减法。

### 3.5 可见性安全的状态更新（visibility-safe update）

```text
g_t    = sigmoid(MLP([LN(b_t-), r_t, q_obs_t, s_t-]))
delta  = R(r_t)
b_t+   = b_t- + q_obs_t * g_t * delta
s_t+   = (1-q_obs_t) * s_t-
```

中文解释：`g_t` 决定每个位置应更新多少，`delta` 给出更新方向，`q_obs_t` 根据实际晴空证据限制更新幅度。晴空证据越少，更新越弱；完全没有证据时，belief 必须严格保持不变。

性质：

- `a=0`：没有新观测，不调用更新模块；
- `q_obs=0`：没有晴空证据，belief 满足严格恒等性（exact identity）；
- `q` 只在更新量外乘一次，避免旧写法造成 `q²` 级别的过度衰减；
- `s` 是连续的软陈旧度（soft staleness），不夸大为精确的逐像素观测年龄。

### 3.6 为什么删除隐状态目标、EMA 与时间平滑正则

- 完整 belief 不能由单帧目标（single-frame target）定义，因为它还应保存当前帧看不到的历史信息；
- 解码器的 sigmoid 已限制输出范围，因此范围损失 `L_range` 冗余；
- 通用时间平滑正则（temporal smoothness）会错误压低极端或快速变化；
- KL 正则或随机状态（stochastic state）不是验证当前机制假设所需的最小设计；
- 对齐残差已经提供语义更明确的状态更新信号（update signal）。

---

## 4. Stage2 最终训练定义

### 4.1 气象、日历、地理信息与预测跨度

GreenEarthNet/Contextformer 的官方气象输入使用八个 E-OBS 变量（`fg, hu, pp, qq, rr, tg, tn, tx`），分别计算每五日的均值、最小值和最大值，共得到 24 维特征。最终主比较必须使用同等信息，不能继续使用当前只有四个字段的简化输入（shortcut）。

- 使用共享的两层多层感知机（two-layer MLP）得到每个五日区间的气象表示 `w_k`；
- ObsWorld、VanillaFilter 和 PredRNN 按时间顺序消费 `w_k`；
- Direct 使用一层门控循环单元（GRU）聚合同一段 `w_1...w_h`；
- 上下文历史气象也必须输入，不能只提供未来气象；
- `DOY` 单独作为日历变量 `C_t`，不混入累计气象摘要；
- `G` 使用 DEM 和静态地理信息；
- `h` 只用于 Direct 的终点查询；`F_5` 本身始终表示固定五日状态转移。

未来 E-OBS 属于预先给定的真值式或再分析外生驱动（oracle/reanalysis forcing）。因此，论文只能称其为**受外生驱动约束的历史回算或情景预测（forcing-conditioned hindcast/scenario forecast）**，不能称为业务实时预报（operational forecast）。

### 4.2 编码器与解码器的训练状态

- `E/P` 初期冻结；如果验证集性能进入平台期（Val plateau），各匹配隐状态模型可在相同步数和学习率下解冻相同的末端网络块；
- 当前四波段 `H` 没有本地训练好的检查点，**不能冻结一个随机初始化的 `H`**；
- 对每个随机种子（seed），Direct、VanillaFilter 和 ObsWorld 使用完全相同的 `E/P/H` 初始化；
- `H` 与 Stage2 联合训练；所有模型使用相同的 20 个未来目标进行监督。

### 4.3 新观测揭示计划（reveal schedule）

所有在线递归系统（online recurrent systems）使用同一训练分布：

- 50% 的批次不揭示任何未来观测；
- 50% 的批次恰好揭示一帧未来观测；
- 揭示时刻从第 2–15 个未来步中均匀采样，并且不根据晴空比例（cloud fraction）挑选；
- 在揭示时刻先输出当前更新前预测，再读取真实观测，避免信息泄漏；
- 多次揭示（multi-reveal）不进入正文主训练。

训练时不按晴空证据量筛选样本；当 `q=0` 时，更新结构自然退化为无操作（no-op）。

### 4.4 训练损失（loss）

设：

```text
ell_t = L_masked_RGBN(m_rgb_sup) + lambda_NDVI * L_masked_NDVI(m_ndvi_sup)
```

不揭示未来观测时：

```text
L = mean_{t=1..20} ell_t
```

在第 `r` 步揭示一帧观测时：

```text
L_pre  = mean_{t=1..r} ell_t
L_post = mean_{t=r+1..20} ell_t
L = 0.5 * L_pre + 0.5 * L_post
```

这种写法使较早和较晚揭示情况下，揭示后监督（post-reveal supervision）的总权重保持一致。揭示时调用的 `U` 只从后续损失 `L_post` 获得监督；上下文阶段调用的 `U` 则通过后续预测获得梯度。当前揭示帧不设置“更新后立即重建该帧”的捷径（posterior reconstruction shortcut）。

权重 `lambda` 先通过 500–1000 次更新的小规模试验，检查损失与梯度量级，并结合验证集试跑（Val pilot）锁定；不能把任意初始值直接写成最优设置。

### 4.5 训练课程（curriculum）

1. 先在 8 个数据块上过拟合（eight-cube overfit），验证实现是否正确；
2. 依次训练 1/2/4/8/12 步推演；
3. 扩展到完整 20 步推演；
4. 加入 50% 不揭示、50% 单次揭示的混合训练；
5. 只有确有必要时，才对所有匹配模型同步解冻编码器最后若干网络块。

若时间反向传播（BPTT）超过显存，可使用梯度检查点（gradient checkpointing）；但不能因此改变前向状态的连续传递。本文不声称具有超出训练长度的外推能力（train-length extrapolation）。

### 4.6 强对照

#### Direct-Seq

它与 ObsWorld 使用相同的 `E/H`、气象输入、20 个监督目标、训练样本和调参预算，只比较“直接查询各终点（endpoint mapping）”与“递归传递状态（recurrent state transition）”的差异。

#### VanillaFilter

VanillaFilter 是通用隐式融合滤波器。它获得完全相同的 `z_obs`、`z_pred`、`q`、`s`，并拥有相同的一次额外编码器前向计算：

```text
u_t  = MLP_v([LN(b_t-), z_obs, stopgrad(z_pred), q_obs, s_t-])
b_t+ = b_t- + q_obs * u_t
```

它可以隐式学习“观测减预测”的操作，但不显式构造对齐残差。其更新模块参数量和浮点运算量（FLOPs）与 ObsWorld 的差异不得超过 5%。

#### PredRNN-online

PredRNN-online 使用官方较强的递归配置。揭示新观测时，它接收被掩码的 RGBN 与观测掩码，然后继续预测。该对照用于检验：成熟的像素级递归模型（pixel recurrence）是否已经足以完成在线观测吸收，而无需我们的隐状态对齐残差机制。

---

## 5. 前沿研究告诉我们的主实验规则

### 5.1 “主实验必须另一个数据集”是错误规则

实验形态应由论文主张（claim）决定：

| 主张类型 | 合理的实验形态 |
|---|---|
| 面向特定任务的预测方法 | 在训练集训练、验证集选型，并在同一基准的锁定测试集/OOD 上报告主结果；跨数据集不是必要条件 |
| 基础模型或通用表示 | 多数据集、多任务和下游评估才是必要证据 |
| 新的响应或鲁棒性能力 | 同一基准上严格设计的干预/能力测试协议，可以作为主证据 |

Contextformer 与 EO-WM 都以各自基准中未参与训练的测试划分或分布外划分（held-out/OOD splits）为主，并不要求“在 EarthNet 上训练，再到另一个无关数据集做主测试”。AnySat、TerraMind、ST-ReP 使用多数据集，是因为它们声称具有通用表示或基础模型能力。

### 5.2 Contextformer / GreenEarthNet 是主实验锚点

[Contextformer (CVPR 2024)](https://openaccess.thecvf.com/content/CVPR2024/papers/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.pdf) 的关键结构：

- Train：2017–2020；
- Val：相邻地理位置（location）的 2020 年数据；
- OOD-t：相同位置的 2021–2022 年数据，是论文的主要时间分布外测试；
- OOD-s：外部区域（region）的 2017–2019 年数据，是空间分布外测试；
- OOD-st：外部区域的 2021–2022 年数据，是时空联合分布外测试；
- 官方指标：决定系数 R²、均方根误差 RMSE、纳什效率系数 NSE、绝对偏差 `|bias|`、优于气候平均基线的比例，以及前 25 天 RMSE；
- 强基线包括持续性预测（persistence）、气候平均（climatology）、ConvLSTM、PredRNN、SimVP 和 Earthformer 等；
- 支撑实验包括有/无气象、空间打乱（spatial shuffle）、土地覆盖和季节分组等；
- 最终论文没有为了形式而增加与中心主张无关的下游任务。

[GreenEarthNet 官方代码与评估器](https://github.com/vitusbenson/greenearthnet) 要求输出 NetCDF 格式的 `ndvi_pred`，其目标坐标和时间必须严格对齐；评估掩码由 `s2_dlmask + SCL + vegetation/dynamic` 等规则共同确定。

### 5.3 UniTS v2 表明“自回归”本身不再具有新颖性

[UniTS v2](https://arxiv.org/html/2512.04461) 已经在 GreenEarthNet 上进行自回归多帧 RGBN 预测（autoregressive multi-frame forecasting）。因此，论文不能声称“现有方法都只一次性预测整个序列块，而我们首次使用递归”。它目前公开的主要结果是 PSNR、SSIM、RMSE、MAE 和 SAM；同时，其[代码仓库](https://github.com/YuxiangZhang-BIT/UniTS)在本轮核查时尚不能直接按 GreenEarthNet 官方协议复跑。因此，不能把跨协议、不可比的数字混入官方主表。

### 5.4 EO-WM 否定“世界模型首创”，但不否定世界模型母叙事

[EO-WM](https://arxiv.org/html/2606.27277) 已明确提出“部分可观测、气象驱动的 EO 世界模型”，并给出极端夏季（Extreme Summer）和季节匹配样本（Seasonal Matched-Pair）响应诊断。因此，本稿不能声称首个 EO 世界模型，也不能把通用的气象条件输入（generic weather conditioning）当作新意；但这不妨碍 ObsWorld 用世界模型定义系统问题。二者的中心差异应统一写成：**EO-WM 重点验证气象驱动的遥感生成，ObsWorld 重点研究局部新观测如何安全校正历史依赖的预测信念状态，并改善后续推演。**

若本稿声称“模型对外生驱动的响应是正确的”（driver-response fidelity），就必须在原始 EarthNet2021 上按同一协议比较 [EO-WM 代码](https://github.com/Luo-Z13/EO-WM)。当前只保留较弱但必要的**外生驱动对齐证据（forcing-alignment evidence）**：分别训练真实气象与无气象模型，并在同一个检查点上比较正确时间气象、错时气象和错误年份气象。它们只能证明模型使用了时间对齐的驱动，不能证明因果响应正确。

### 5.5 为什么基础模型论文需要下游任务，而本稿当前不需要

[AnySat (CVPR 2025)](https://openaccess.thecvf.com/content/CVPR2025/papers/Astruc_AnySat_One_Earth_Observation_Model_for_Many_Resolutions_Scales_and_CVPR_2025_paper.pdf)、[TerraMind (ICCV 2025)](https://openaccess.thecvf.com/content/ICCV2025/html/Jakubik_TerraMind_Large-Scale_Generative_Multimodality_for_Earth_Observation_ICCV_2025_paper.html) 和 [ST-ReP (AAAI 2025)](https://ojs.aaai.org/index.php/AAAI/article/view/33465) 需要多个任务和数据集，是因为它们的中心主张是通用表示学习。ObsWorld 当前研究的是特定任务中的预测状态机制（task-specific predictive-state mechanism），不能机械复制基础模型论文的实验形式。

[DriveWorld (CVPR 2024)](https://openaccess.thecvf.com/content/CVPR2024/papers/Min_DriveWorld_4D_Pre-trained_Scene_Understanding_via_World_Models_for_Autonomous_CVPR_2024_paper.pdf) 的下游实验有意义，是因为它声称具有预训练场景理解能力。对我们而言，再观测校正（re-observation correction）已经是最贴近自身主张的能力测试（capability test）。

---

## 6. 最优主实验：验证 EO 世界模型的三项行为契约

### RQ1 / 实验块 A：开放循环遥感世界推演（主表 1）

数据集与协议（dataset/protocol）：

- 使用 GreenEarthNet 训练集训练；
- 使用官方验证集调参和早停（early stopping）；
- 锁定的 `ood-t_chopped` 是主要测试集；
- OOD-s/OOD-st 作为次级泛化结果，以紧凑列或附录形式报告；
- 模型配置锁定后，OOD-t 只评估一次。

主表行（比较方法）：

1. 持续性预测（persistence）；
2. 气候平均预测（climatology）；
3. Contextformer；
4. PredRNN；
5. 完全匹配的 Direct-Seq；
6. 最终 ObsWorld；
7. UniTS 只有在同一官方评估器上成功复跑时才加入数字表。

主表列（评价指标）：

- 主要指标：官方 NDVI RMSE；
- 次要指标：R²、NSE、`|bias|`、优于气候平均基线的比例、前 25 天 RMSE；
- 参数量、浮点运算量和推理延迟（Params/FLOPs/latency）可放在附录。

预先注册非劣效性标准（non-inferiority）：

```text
Delta_open = RMSE_ObsWorld - RMSE_Direct
delta_NI = 0.01
```

中文解释：`Delta_open` 是 ObsWorld 与 Direct 的 RMSE 差；小于 0 表示 ObsWorld 更好，大于 0 表示更差。我们允许的最大非劣界值 `delta_NI` 为 0.01。

使用按地理瓦片配对的自助法（paired geographic-tile bootstrap）时，单侧 95% 置信区间上界必须小于 0.01。每次重采样后都要在重新抽取的瓦片上完整重算官方聚合指标，不能简单平均每块瓦片的 RMSE。

正文同时保留“误差随预测时距变化曲线”（horizon-wise degradation curve）。它不是装饰性图，而是直接回答：共享 belief 在 100 天无观测推演中是否稳定。主表 1 证明最终结果质量，这条曲线证明世界模型的逐步推演行为。

### RQ2 / 实验块 B：部分观测下的预测信念状态校正（主表 2 + 主图 2）

每个数据块（cube）都运行以下三种条件：

- 不揭示未来观测；
- 第 25 天揭示一帧真实观测；
- 第 50 天揭示一帧真实观测。

不按晴朗程度筛选样本，直接使用真实 `m_obs`。实验块 B 的指标不称为“官方指标”，因为只评估揭示后的截断时间窗，会改变官方 R²、NSE 和 outperformance 的样本资格与统计含义。

主表比较方法：

1. 同一检查点、不揭示新观测；
2. VanillaFilter；
3. PredRNN-online；
4. 本文提出的对齐残差更新 `U`。

主要统计量（primary estimand）：

```text
g_{m,s,c,r,h} = NDVI_MAE_no-reveal - NDVI_MAE_reveal
G_{m,s,c,r}   = mean_{h>r} g
Gbar          = 0.5 * (G_day25 + G_day50)
D_b           = Gbar_ours - Gbar_baseline
```

中文解释：`g` 表示同一模型在获得新观测后减少了多少误差；`G` 是揭示后全部未来时刻的平均收益；`Gbar` 对第 25 天和第 50 天两种揭示位置等权平均；`D_b` 再比较 ObsWorld 与基线的校正收益差。只有 `D_b>0`，才说明 ObsWorld 从同一帧新观测中获得了比基线更大的长期收益。

- 两个共同主要比较（co-primary）是 `D_Vanilla` 和 `D_PredRNN-online`；
- 使用 Holm 方法控制两个主要比较的整体第一类错误率；
- 先在相同随机种子和相同数据块内形成配对差值；
- 数据块和时间窗先按地理瓦片（geographic tile）聚合；
- 进行 10,000 次配对的瓦片聚类自助采样（paired tile-cluster bootstrap）；
- 必要支撑条件：ObsWorld 揭示后的绝对 NDVI MAE 也不能差于两个基线，避免“起点更差所以看起来提升更大”；
- 次要指标包括 NDVI RMSE、RGBN MAE、随时距变化的收益曲线及其曲线下面积（AUC）；
- 按晴空比例分层时只报告效果和样本量，不进行多重显著性“捞结果”。

这一实验不是普通下游任务，而是世界模型的第二项定义性能力：新世界证据到达后，内部 belief 能否被校正，并使之后的想象/推演（imagination/rollout）更准确。

### RQ3 / 实验块 C：世界模型行为契约与机制消融（紧凑消融表/附录）

正文最多保留：

1. 删除显式残差，即退化为 VanillaFilter；
2. 删除状态陈旧度 `s`；
3. 将连续晴空比例 `q` 替换为二值可见标记。

只有在验证集上确实有益的部件才进入最终模型。附录可放：

- Stage1/S2-only 与修复后的 Stage1.5 初始化对比；
- 用新观测直接硬替换状态（hard replacement）；
- OOD-s/OOD-st 的完整分项结果；
- 土地覆盖、季节和失败案例。

外生驱动对齐检查（forcing alignment）不再是完全可选项。最低限度必须完成：

1. 分别训练真实气象模型与无气象模型，作为气象驱动预测效用的辅助证据；
2. 在同一检查点下比较正确时间、错时和错误年份气象；正确时间气象更优，才是时间对齐有效的关键证据。

两类检查都必须运行。若正确时间气象不优于错时或错误年份气象，就必须从中心命题中删除“受外生驱动约束”的强调；即使存在差异，也只能声称模型使用了时间对齐的驱动，不能升级为因果响应主张。

明确不做或推迟：

- 与主张无关的下游任务；
- 基础模型 2×2 组合实验；
- 大语言模型（LLM）；
- 概率扩散生成；
- 多次揭示的正文主训练；
- EO-WM 的完整响应基准；
- 额外数据集，除非核心实验全部完成且仍有资源。

### 6.4 论文页面预算

AAAI 七页内容建议：

1. 图 1：世界 belief 推进 → 观测解码 → 对齐创新量 → 更新后推演；
2. 表 1：开放循环遥感世界推演主结果；
3. 图 2：第 25/50 天新观测后的配对收益曲线与晴空比例分层；
4. 表 2：VanillaFilter、PredRNN-online、本文方法与最小消融；
5. 附录：协议一致性、全部指标、效率、Stage1.5/气象/OOD 分项结果。

不要挤入六张平行主表。

---

## 7. 下游任务与“大模型 + ObsWorld”最终取舍

### 7.1 本稿不需要无关下游

CropHarvest、Sen1Floods11、EuroSAT 分类等任务不能直接证明：

- belief 能被部分观测安全更新；
- 状态更新能够改善后续预测；
- 对齐残差优于通用滤波器。

再观测校正本身就是最直接的能力评估（capability evaluation）。它不是“可选小实验”，而是主证据。

### 7.2 什么时候才需要下游

只有当论文主张变成：

- 通用 EO 表示；
- 基础模型；
- 可迁移预训练；
- 广义场景理解；

才必须增加多数据集和下游任务。当前不应为了增加实验而反向扩大论文主张。

### 7.3 大模型并非永远无用，但现在不是解法

AnySat/TerraMind 编码器可以在核心方法成功后，作为附录中的性能上限探索（appendix ceiling）或后续工作：

```text
小型编码器 + Direct
小型编码器 + ObsWorld
基础模型编码器 + Direct
基础模型编码器 + ObsWorld
```

但这一实验回答的是模型规模与方法的交互（scale interaction），不能修复掩码泄漏、belief—evidence 接口或校正语义问题。因此当前先不运行；大语言模型对本任务也没有自然角色。

---

## 8. 当前代码与最终方案的一致性审计

本轮最初只做静态代码审查；随后已在项目内复现 Python 3.11.15 / PyTorch 2.12.0+cu130 环境，在 H200 上完成 CUDA 冒烟测试（smoke test），并通过 `tests/` 下 26 项正式测试。全仓运行 pytest 时，仍会被 `scripts/test_dual_dataloader.py` 中旧 `/csy-mix02/...` 数据路径阻断。下面关于 Stage2 接口的判断主要来自静态审计，不能误写成“最终 Stage2 已通过运行验证”。

### 8.1 已经正确/值得复用

- B8A/近红外波段映射（NIR band mapping）已按 RGBN 顺序纠正；
- `GeoTokenizer` 已存在，静态 DEM 数据路径可复用；
- 修复后的 Stage1.5 状态重建桥接模块已经存在；
- Stage1.5 已移除部分错误的 `phi` 打乱和跨季节配对逻辑；
- `PureImagingConditionEncoder` 已更接近“只编码采集条件（acquisition-only）”的角色；
- EarthNet2021x 的 NetCDF 加载器已能读取 S2 RGBN、E-OBS 子集和 DEM。

### 8.2 P0：阻塞性协议问题，正式训练前必须修复

| 问题 | 当前证据 | 风险/最终要求 |
|---|---|---|
| 数据划分名称与回退逻辑 | `data/datasets/earthnet2021.py:38-46, 522-540` 只有通用 train/val/iid/ood；找不到时回退到根目录 | 可能在无提示时混入错误划分；必须使用显式 `val_chopped/ood-t/s/st` 清单，缺失时直接报错 |
| 评估器不是 GreenEarthNet 官方版本 | `eval/earthnet_standard_metrics.py` 仍是原 EarthNet ENS 路径 | 切换为 GreenEarthNet 官方完整 20 步评估器 |
| 预测输出格式错误 | `eval/predict_stage2_earthnet.py:97-107` 输出 `highresdynamic` NPZ | 输出保留 time/lat/lon 坐标的 NetCDF `ndvi_pred` |
| 观测掩码与评估掩码不一致 | loader `earthnet2021.py:273-277` 使用 `s2_mask<=0`；官方评估器结合 dlmask/SCL/landcover | 将观测掩码与监督/评估掩码显式分路，并与官方规则对齐 |
| 气象变量不完整 | `earthnet2021.py:250-251` 只取 rr/tg/hu/qq；`_format_stage2_sample:364-376` 只构造未来驱动 | 使用官方 8 个变量 × mean/min/max = 24 维，并加入上下文历史气象 |
| 检查点版本过旧 | `configs/train/stage2_earthnet_main.yaml:14` 指向旧的 non-state-bridge 60k 检查点 | 先核对检查点；Stage1.5 只作为通过门槛后才采用的初始化候选 |

### 8.3 P0：当前模型还不是最终 Stage2

- `models/dynamics/obsworld_stage2.py:121-134` 把同一个 `z_context` 复制到每个预测跨度，属于直接预测，不是递归推演；
- `:142-157` 使用单个目标帧的编码器隐表示作为完整状态目标，最终应删除；
- `:146` 每次前向传播都把在线波段适配器复制给目标适配器，这不是指数滑动平均（EMA），最终也不再需要；
- `:52-55, 87-90` 在 GreenEarthNet 上使用中性常量 `phi`，不能支持端到端观测算子主张；
- `:81-82` 只是把掩码逐像素乘到输入上；最终必须明确区分 `a/m_obs/m_sup` 三条路径；
- `:176` 的 token 掩码只要求晴空比例 `>0.05`，条件过松；最终使用连续 `q`；
- `models/dynamics/context_state_aggregator.py:26-29,85` 只有序号时间嵌入，没有真实日历、历史气象或陈旧度；最终用顺序 `F/U` 取代其核心角色；
- `H` 是 Stage2 新增的解码器，本地没有训练结果，不能冻结随机权重。

### 8.4 P1：公平性与可解释性

- 当前配置 `horizons_per_sample: 6`；如果递归模型监督 20 个时刻而 Direct 只监督 6 个时刻，比较不公平，因此二者都必须使用 20 个目标；
- 当前流程把 128 分辨率输入上采样到 256，再降采样评估；必须报告或消除插值对精度和效率的影响；
- Direct 与递归模型必须使用相同的逐步气象序列，不能比较“累计气象简化输入”和“完整逐步轨迹”；
- 未来目标掩码即使可用于损失计算，也不得改变状态陈旧度；必须加入“未揭示未来掩码不变性测试”（unrevealed-mask invariance test）；
- `m_obs` 与 `m_sup` 需要不同变量/代码路径，避免误用。

### 8.5 当前 `phi` 探针实验不能作为论文证据

`eval/eval_phi_leakage_probe_fixed.py` 的问题包括：

- `:76-77` 没有走真实的条件化 `phi` 路径；
- `:81-83` 删除一个不存在或未经确认的 CLS token 后再做池化；
- `:250-252` 对 Stage1 使用随机初始化的 `SpatialStateProjector`，并不是恒等映射；
- `:275-294` 在同一个数据加载器上训练和评估探针，存在数据复用问题；
- 随机基线固定写成 50%，没有核对类别不平衡；
- 缺少独立的地理/日历控制变量和多随机种子。

因此，现有“`phi` 信息泄漏下降”不能写进论文主结论。若 Stage1.5 只作为初始化对照行，应优先修复预测/语义效用门槛，不再用大量探针实验挽救叙事。

### 8.6 当前结果能说明什么

本地 JSON：

- Stage1 双模态 50k：EuroSAT 总体准确率（OA）约 69.57%；
- 分阶段训练 95k：OA 约 76.15%；
- 仅 S2 的 50k：OA 约 70.43%；
- 文件中记录的 94.1% 基线尚未证明评估协议和骨干网络公平可比。

这些结果只能说明 Stage1 表示包含一定语义信息，不能证明 Stage1.5 已完成因素分解、Stage2 预测有效、观测校正成立，或论文已经具备 AAAI 证据。当前没有本地 Stage1.5/Stage2 的正式结果或检查点产物。

---

## 9. 执行顺序与止损条件

### 阶段门槛 0（Gate 0）：官方协议

必须全部通过：

1. 使用显式数据划分清单，并审计哈希、数量、年份和地理瓦片；
2. 用气候平均和持续性基线检查官方评估器是否复现一致；
3. 检查 NetCDF `ndvi_pred` 的坐标与时间是否完全对齐；
4. 检查官方评估掩码是否一致；
5. 补齐 24 维气象变量和上下文历史气象；
6. 严格分离 `a/m_obs/m_sup`；
7. 通过未揭示掩码不变性、`q=0` 恒等性和“先预测后揭示”的顺序测试。

未通过，不跑正式训练。

### 阶段门槛 1（Gate 1）：强基线与小样本过拟合测试

1. 在 8 个数据块上过拟合，验证训练链路；
2. 使用 Contextformer 官方权重或复现结果检查协议一致性；
3. 建立较强的 PredRNN 基线；
4. 建立完整匹配、监督全部 20 个未来时刻的 Direct-Seq；
5. 测量 500–1000 次更新的吞吐和显存占用。

### 阶段门槛 2（Gate 2）：单随机种子的主机制试验

只跑：

- 不揭示未来观测的开放循环模型；
- VanillaFilter；
- PredRNN-online；
- 对齐残差更新 `U`。

若 `U` 在验证集配对收益上不优于 VanillaFilter 和 PredRNN-online，同时开放循环预测也不合格，则立即停止，不再运行三随机种子正式实验。

### 阶段门槛 3（Gate 3）：删除无效组件并简化模型

在验证集上测试：

- 删除状态陈旧度；
- 将连续 `q` 改为二值 `q`。

如果性能等效，就删除更复杂的组件。只有核心门槛已经通过时，才继续测试 Stage1.5 初始化。

### 阶段门槛 4（Gate 4）：三随机种子与一次锁定 OOD 测试

只有 Gate 2/3 通过后，才运行 3 个随机种子、OOD-t 和聚类自助法统计。之后才可补充 OOD-s/OOD-st 和失败案例附录。

### 论文主张成立的全部条件

1. 相比匹配的 Direct，官方 NDVI RMSE 通过 0.01 非劣效性门槛；
2. Holm 校正后的 `D_Vanilla>0`；
3. Holm 校正后的 `D_PredRNN-online>0`；
4. 揭示后的绝对 MAE 不差于两个在线基线；
5. 收益不能只出现在晴空比例最高的一层；
6. 协议、基线和掩码测试全部通过；
7. 无效的 staleness 或 `q` 组件按预设规则删除。

任何核心门槛失败，都必须缩小或放弃对应主张；**不能通过追加大模型、无关下游或更多模块来挽救叙事。**

### 正常时间/算力判断

当前环境已经具备 PyTorch 和 8 张 H200，但尚未测量最终 Stage2 的每步耗时、显存和评估开销，因此仍不能给出可信的 GPU 小时数。预算公式为：

```text
GPU-hours = sec_per_update × planned_updates × seeds / 3600 + evaluator/checkpoint overhead
```

中文解释：总 GPU 小时约等于“每次更新耗时 × 计划更新次数 × 随机种子数”，再加上评估和保存检查点的额外开销。

按阶段门槛推进，预计需要约 8–12 次完整训练等价量（full-run equivalents），正常约六周：

1. 协议、数据和评估器修复：1–2 周；
2. 强基线与单随机种子试验：1–2 周；
3. 模型简化、三随机种子与统计：约 2 周；
4. 论文图表与失败分析：约 1 周。

---

## 10. AAAI 定位、时间与写法

[AAAI-27 主技术轨征稿说明](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/)当前给出的时间为：摘要截止 2026-07-21，正文截止 2026-07-28，补充材料/代码截止 2026-07-31，均按地球任意时区截止（AoE）。投稿需要填写可复现性检查表；正文内容限 7 页，额外页面只能用于参考文献，总页数最多 9 页。

以 2026-07-15 的实际状态：

- 没有 Stage2 正式结果；
- 官方评估流水线尚未对齐；
- 最终方法尚未实现；
- 强基线的一致性复现尚未完成；

因此，从当前状态出发在 AAAI-27 截止前完成从零投稿并不可信。若远程机器已有未同步结果，应先按 Gate 0–2 盘点；否则应把当前设计作为下一正常投稿周期或其他顶会的严谨路线。

AAAI 相关性不应写成“遥感应用重要”，而应写：

1. 部分可观测性；
2. 受外生驱动约束、通过学习获得的世界预测信念状态；
3. 状态转移—观测生成—证据更新的世界模型行为契约；
4. 观测对齐校正；
5. 受控的顺序推断；
6. 能够真正否定主张的强基线，以及可复现的实验协议。

建议最终贡献点（contribution bullets）只写两类：

1. 一个方法贡献：具有严格无证据恒等性的对齐残差校正；
2. 一个证据贡献：覆盖全部数据块的配对校正协议，并与匹配的通用滤波器和像素递归吸收方法比较；不声称提出了新基准。

---

## 11. 最终问答

### Q1：EarthNet2021 还做不做？

主任务使用 GreenEarthNet/EarthNet2021x 官方 OOD 测试轨道。原始 EarthNet2021 的 ENS 指标或 EO-WM 的极端/匹配样本实验不进入核心；只有未来重新提出天气响应主张时才必须补做。

### Q2：是否一定要跨数据集？

不需要。当前主张是面向特定任务的状态校正机制；官方 OOD-t/OOD-s/OOD-st 加校正协议，已经可以形成主证据。第二数据集只能增强外部有效性，不是设计成立的必要条件。

### Q3：是否需要下游？

不需要与主张无关的下游任务。再观测校正就是距离中心主张最近的能力测试。

### Q4：大模型 + ObsWorld 是否无用？

不是永远无用，但目前无助于隔离主机制的真实贡献。核心机制通过阶段门槛后，可以作为附录或后续工作；当前不做。

### Q5：Stage1.5 是否废掉？

不删除代码，但将其降级为初始化候选。它不再决定主论文是否成立；若门槛失败，就使用 Stage1/S2-only 初始化。

### Q6：主结果只要精度第一吗？

不是。首先要证明官方开放循环预测相对 Direct 满足非劣效性，然后还要在配对校正收益上击败 VanillaFilter 和 PredRNN-online。若只提高终点预测精度却没有校正证据，它只是一个更强的预测模型；若校正很强但开放循环世界推演崩溃，也不能支持“统一的、可由观测校正的世界模型”主张。

### Q7：最终一句话是什么？

> **ObsWorld 是一个面向稀疏遥感、可由观测校正的世界模型：它在给定外生驱动下维护并推演地表预测信念状态，解码未来卫星观测，并利用可见区域对齐残差吸收局部新证据；论文通过开放循环世界推演和新观测到达后的状态校正两项行为共同验证它。**

### Q8：为什么仍然可以叫“世界模型”？

因为命名依据不是隐状态是否等于真实物理世界，而是模型是否形成由历史支持、可以持续维护的预测信念状态，是否具有受外生条件控制的状态转移和观测模型，是否能在无新观测时继续推演，以及能否在新观测到来时形成更新后状态（posterior）。当前框架覆盖这四项；需要收缩的是物理真实性和因果性的主张强度，而不是世界模型身份。

---

## 12. 主要公开来源

- [AAAI-27 Main Technical Track Call](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/)
- [Benson et al., Multi-modal Learning for Geospatial Vegetation Forecasting, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.pdf)
- [GreenEarthNet official repository and evaluator](https://github.com/vitusbenson/greenearthnet)
- [Requena-Mesa et al., EarthNet2021, CVPR EarthVision 2021](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf)
- [Zhang et al., UniTS v2](https://arxiv.org/html/2512.04461)
- [UniTS repository](https://github.com/YuxiangZhang-BIT/UniTS)
- [Luo et al., EO-WM](https://arxiv.org/html/2606.27277)
- [EO-WM repository](https://github.com/Luo-Z13/EO-WM)
- [Astruc et al., AnySat, CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Astruc_AnySat_One_Earth_Observation_Model_for_Many_Resolutions_Scales_and_CVPR_2025_paper.pdf)
- [Jakubik et al., TerraMind, ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Jakubik_TerraMind_Large-Scale_Generative_Multimodality_for_Earth_Observation_ICCV_2025_paper.html)
- [Min et al., DriveWorld, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Min_DriveWorld_4D_Pre-trained_Scene_Understanding_via_World_Models_for_Autonomous_CVPR_2024_paper.pdf)
- [Zheng et al., ST-ReP, AAAI 2025](https://ojs.aaai.org/index.php/AAAI/article/view/33465)
- [Hafner et al., PlaNet, ICML 2019](https://proceedings.mlr.press/v97/hafner19a.html)
- [Littman, Sutton, Singh, Predictive Representations of State, NeurIPS 2001](https://papers.nips.cc/paper_files/paper/2001/hash/1e4d36177d71bbb3558e43af9577d70e-Abstract.html)
