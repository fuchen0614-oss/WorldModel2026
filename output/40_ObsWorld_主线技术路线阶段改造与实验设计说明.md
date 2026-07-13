---
title: ObsWorld 主线、技术路线、阶段改造与实验设计说明
aliases:
  - ObsWorld 路线图 40
  - ObsWorld Stage 改造说明
tags:
  - ObsWorld
  - 遥感世界模型
  - AAAI
  - 实验设计
  - 技术路线
created: 2026-07-13
status: 讨论稿｜后续代码修改与论文写作的主参考
project_root: D:\Mine Program\codexwork\CVPRAAAI投稿
code_root: D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026
---

> [!abstract] 一句话结论
> 不要放弃“模拟真实世界发生什么”的立意。需要放弃的只是当前公开数据和当前实现无法证明的强断言：绝对真实状态、严格因果反事实、任意长期的完整地球模拟。最优路线是把 ObsWorld 写成一个观测扎根的地表过程世界模型：从稀疏遥感观测估计可预测状态，在真实外生驱动下逐步推进，并生成可与真实未来观测核验的结果。

> [!important] 本文档的作用
> 本文档不修改代码。它回答 DGH 与 T、训练阶段、z 的状态证明、direct 与 rollout、RQ1–RQ4、下游和基础模型比较等问题；同时将后续任务分解为 Stage 0 到 Stage 4，作为后续修改的参考。39 保留为独立审查档案，本文件是对其主线和实验组织的正式修订。

---

## 目录

- [[#0. 决策总览：不放弃什么，收紧什么]]
- [[#1. T 是什么：为什么 DGH 之外出现了 T]]
- [[#2. 训练阶段没有被推翻：哪些保留，哪些重训]]
- [[#3. z 怎样才算地表状态：不以向量相似为标准]]
- [[#4. 观测角度问题：不应以 45 度或 7.5 度作为标准]]
- [[#5. direct 加 rollout：含义、训练和严谨性]]
- [[#6. RQ1–RQ4、下游任务与 Foundation Model 的位置]]
- [[#7. 对 39 的正式修订：最终 AAAI 主线]]
- [[#8. 现有实现问题总表]]
- [[#9. Stage 0 到 Stage 4 的技术路线]]
- [[#10. 最终实验闭环、正文表格与成功线]]
- [[#11. 公开数据能与不能证明什么]]
- [[#12. 代码修改前的决策清单]]
- [[#13. 术语与本地文件索引]]

---

# 0. 决策总览：不放弃什么，收紧什么

## 0.1 原始愿景是正确的

“模拟真实世界发生了什么”比“预测下一张遥感图像”更有研究价值，也更符合世界模型的原始含义。遥感观测天然是部分可观测的：地表过程通过传感器、云、处理级别、太阳几何和不规则重访，才成为我们见到的影像。

真正需要收紧的不是愿景，而是可证据化的范围。首篇论文最合理的世界定义是：

> 在植被主导、气象驱动、约 100 天的地表过程窗口中，模型从稀疏且受采集过程影响的观测中形成预测性内部状态，在真实天气轨迹下逐步重演地表变化，并由后续卫星观测核验。

| 可以主张 | 当前不能严谨主张 |
|---|---|
| 对真实已发生序列的事实重演或回放 | 唯一、完整、绝对真实的地球状态 |
| 给定真实天气的事实预测 | 交换天气后的严格因果反事实 |
| 给定合理驱动路径的条件情景推演 | 覆盖城市、洪涝、农业决策等一切过程的完整地球模拟器 |
| 稀疏观测之间的短中期过程演化 | 任意长时间的无误差自由推演 |

> [!warning] 关键边界
> 换一条天气输入后，预测发生变化，只能证明条件敏感性或事实响应一致性；不能证明因果干预。公开卫星数据中仍有未观测土壤水分、灌溉、植被类型等因素。EO-WM 也将 EO 预测定义为部分可观测、受天气驱动且具有未观测状态不确定性的任务。([EO-WM](https://arxiv.org/html/2606.27277))

## 0.2 旧主线、33–35、39 的正确分工

| 内容 | 最值得保留 | 不能直接作为最终论文的原因 | 正确角色 |
|---|---|---|---|
| idea 中 v5 主线 | 状态、动力学、观测三分法；世界不等于影像 | 尚缺逐项实验证据 | 为什么做，Why |
| WorldRS 外生驱动思路 | 外生驱动决定地表演化 | 过度统一植被、洪涝、建筑等异质过程 | 未来扩展 |
| 33–35 DGH 方案 | 工程上可运行的未来预测框架 | 直接预测不能单独证明连续模拟 | direct 性能基线 |
| 39 独立审查 | 代码问题、风险边界、证据链 | 若照搬为摘要会过于表征学习化 | 怎样证明，How to prove |
| 本文件方案 | 状态、短步转移、观测与事实验证闭环 | 需要阶段性代码重构 | 最终 AAAI 路线 |

最终总叙建议固定为：

> ObsWorld 是一个观测扎根的地表过程世界模型。它从稀疏、异构、受采集过程影响的地球观测中推断持续存在的预测状态；在给定真实外生驱动轨迹下逐步推进该状态；并在指定的已知观测条件下生成可被后续卫星观测验证的结果。

英文可写为：

> ObsWorld is an observation-grounded land-surface process world model. It infers a persistent predictive state from sparse and acquisition-affected Earth observations, rolls the state forward under prescribed exogenous driver trajectories, and renders verifiable observations under target acquisition conditions.

---

# 1. T 是什么：为什么 DGH 之外出现了 T

## 1.1 T 不是新条件，而是把原来隐含的机制写清楚

原有流程近似为：

历史观测 → z_context  
z_context + D + G + h → z_future  
z_future → 未来影像

第二个箭头本来必然有一个神经网络。现在把它明确叫作 T，也就是 transition，状态转移函数。T 不是第四个与 D、G、h 并列的输入，而是“在 D、G 和时间尺度条件下，z 如何演化”的机制。

| 符号 | 中文 | 任务中的角色 |
|---|---|---|
| z_t | 潜在预测状态 | 当前对地表过程的内部估计，是被推进的对象 |
| D | 外生驱动 | 天气等随时间变化的外部强迫 |
| G | 静态地理背景 | 高程、地理环境等决定区域反应背景的变量 |
| h | 预测跨度 | 离当前多远；是时间索引，不是物理驱动 |
| T | 状态转移函数 | 让状态在一小段时间内发生演化的共享机制 |
| O | 观测模型或解码器 | 将状态映射为某种卫星可见观测 |
| φ | 观测条件 | 产品、传感器、已知几何等观测过程信息 |

最清楚的数学关系是：

$$
z_{t+\delta}=T_\theta(z_t,D_{t:t+\delta},G,c_t,\delta)
$$

$$
\hat{x}_{t+\delta}=O_\psi(z_{t+\delta},\phi^{known}_{t+\delta})
$$

其中 c_t 是日历或季节信息，δ 是单步长度，例如 5 天。

这条式子的核心逻辑是：

1. D 是天气输入；
2. G 是背景条件；
3. h 或 δ 是时间尺度；
4. T 才是模型学习的演化规律；
5. O 解释为什么同样的地表状态在不同传感器或产品条件下可呈现不同观测。

如果不单列 T，D+G+h 到未来影像很容易被评审理解为普通条件回归。把 T 显式化后，才可以提出严格问题：同一个短步 T 重复调用时，是否仍能重演真正发生的过程？

## 1.2 DGH 不废弃，但必须重新分工

DGH 的问题不在于使用 D、G、h，而在于当前三者角色混杂。

| 旧项 | 是否保留 | 推荐改法 |
|---|---:|---|
| D，天气 | 保留并强化 | 使用逐日或逐 5 天天气路径，而非只提供从起点到终点的累计量 |
| G，地理背景 | 保留但不作为主贡献 | 先修 DEM，再加入来源清楚、跨时不变的静态变量 |
| h，跨度 | 保留但改职责 | direct 模型可使用 h；rollout 模型使用步长 δ 和步数 K=h/δ |
| calendar，日历 | 单列新增 | 与天气分开，以便区分天气效应和季节规律 |
| φ，观测条件 | 单列新增 | 只放推理时已知的观测过程变量；未来真实云量不可作为输入 |
| T，转移 | 显式新增 | 同一个短步模块被重复调用，构成可检验的演化机制 |

推荐的三侧结构是：

观测侧：x_t、mask_t、φ_t → encoder 或 update → z_t  
演化侧：z_t、D、G、calendar、δ → T → z_t+δ  
渲染侧：z_t+δ、已知 φ → O → 预测观测

> [!tip] 与 EO-WM 的关系
> EO-WM 也将天气视为外生条件，并区分气候基线、天气异常和累积胁迫。([EO-WM，第 3.3–3.4 节](https://arxiv.org/html/2606.27277)) 这不是我们要复制它的扩散视频模型；我们的差异应落在显式持续状态、共享短步转移、观测分工和可选更新机制。

## 1.3 Stage 2 是否要改

需要，但不是推倒重来。当前 Stage 2 实际数据流为：

q(history) → z_context  
z_context + D + G + h → F_direct → z_future  
z_future → decoder → image_future

当前实现属于 direct multi-horizon predictor，直接多跨度预测器。它是合理模型，能够作为：

1. 高性能预测基线；
2. 早期可行性验证；
3. rollout 模型的初始化或辅助端点监督；
4. 论文中代表“只做端点预测”的公平对照。

但它不能单独称为连续模拟器，因为每个未来跨度由同一 context 直接输出，而不是让前一步预测状态继续进入同一机制。

因此 Stage 2 未来分成两个清楚的分支：

| 分支 | 内容 | 在论文中的职责 |
|---|---|---|
| Stage 2-D | F_direct 一次跳到 h 天后的状态 | 主表强基线和性能护栏 |
| Stage 2-R | 共享短步 T_δ 重复推进 K 次 | 世界模型最关键的模拟证据 |

它们的感知 encoder、观测 decoder、训练数据和评测协议应一致或明确匹配。差异应只在于端点直接预测与短步连续转移，而不是某一边偷偷使用更强 encoder。

---

# 2. 训练阶段没有被推翻：哪些保留，哪些重训

## 2.1 新路线是全技术路线，不只是 Stage 1 之后的补丁

此前的 Stage 1 → Stage 1.5 → Stage 2 骨架仍然正确。新路线的变化是把训练、验证与论文主张对应起来，并在前面增加数据协议阶段，在后面增加机制评测阶段。

| 阶段 | 原意 | 是否保留 | 修订后的明确职责 |
|---|---|---:|---|
| Stage 0 | 原来没有单列 | 新增 | 波段、mask、DEM、指标、消融配置、数据泄漏的工程验收 |
| Stage 1 | 通用遥感预训练 | 保留 | 感知基础；不承担世界模型主张 |
| Stage 1.5 | 状态 z 与观测条件 φ 分离 | 保留但重构 | 构造真实不可旁路的状态接口 |
| Stage 2-D | DGH 未来预测 | 保留并修复 | direct 性能基线 |
| Stage 2-R | 过去只在文字中隐含 | 新增 | 共享短步转移和 free rollout |
| Stage 3 | 过去混在训练后评测中 | 独立化 | RQ1–RQ4 的固定 checkpoint 证据 |
| Stage 4 | 不确定性、同化、基础模型 | 可选 | 提高上限，不阻塞首篇 |

所以答案是：这是一条从 Stage 0 到 Stage 4 的完整路线，其中 Stage 1 后最重要的新内容是 Stage 2-R；不是把 Stage 1 全部推倒后另建项目。

## 2.2 是否说明 Stage 1 之后全部错误

不是。必须区分“有价值”“不能证明原声称”“存在确定 bug”。

| 内容 | 当前判断 | 是否最终需要重训 |
|---|---|---:|
| Stage 1 通用预训练 | 有价值，可保留，前提是输入波段和尺度语义正确 | 不因引入 T 而重训 |
| Stage 1.5 当前重建 | 不能证明 z 承担重建状态，因为存在旁路 | 若保留状态主张，必须重训 |
| Stage 1.5 旧 φ probe | 当前数字不可进论文，因脚本评测错误 | 修后重新评测 |
| 当前 Stage 2-D | 合法预测原型和强基线 | 最终版应在 P0 修复后重训 |
| 当前 Stage 2-D 曲线和图 | 仍有诊断价值，可看数据和损失是否跑通 | 不需要丢弃 |
| Stage 2-R | 目前尚未真实存在 | 必须新训练 |

准确说法应是：

> Stage 1 后的工作不是全部错误；但 Stage 1.5 的旧训练和 probe 不能再承担“已证明状态分离”的结论，当前 Stage 2-D 不能独自承担“逐步世界模拟”的结论。最终论文模型需要在修复后重新训练。

## 2.3 最少重训与推荐重训方案

### 最少可投稿闭环

1. 完成 Stage 0 的 P0 修复与官方评测；
2. 暂时保留 Stage 1 权重；
3. 重训 Stage 1.5，使重建强制经过 z；
4. 修复并重训 Stage 2-D，得到可靠 direct 基线；
5. 训练轻量 Stage 2-R，先完成短中期 rollout；
6. 用最终 checkpoint 重跑全部状态实验。

### 最稳妥方案，推荐

1. 审计 Stage 1 输入波段、归一化、mask 和时间定义；只有发现其本身语义错误才重训；
2. Stage 1.5 学习共享状态子空间加模态私有残差，不强迫 S1 与 S2 向量完全相同；
3. Stage 2-D 与 Stage 2-R 都从同一经过验证的 encoder 和 decoder 初始化；
4. target state 使用 frozen 或 EMA teacher，避免移动监督；
5. 用 3 个随机种子和置信区间决定措辞，而非只选最佳 checkpoint。

> [!note] 为什么不要求 S1 和 S2 的 z 完全相同
> S1 SAR 与 S2 光学观察的物理量不同，公开数据还可能不严格共时。严谨命题是它们对共享预测状态子空间提供互补后验估计，而不是要求两个向量逐元素相等。可使用 z_shared 与小容量 z_private。

---

# 3. z 怎样才算地表状态：不以向量相似为标准

## 3.1 状态是功能定义，不是向量外观

只计算 z 的余弦相似度、L2 距离或跨模态一致性，不能证明它是地表状态：

- 相似的 z 可能共同编码云、日期或位置；
- 不相似的 z 可能只是坐标变换不同；
- 强制两种传感器完全相同，可能扔掉有用物理信息。

本项目中的正确定义是：

> 若一个表示在控制观测条件后仍保留地表语义和未来演化信息，并且可通过状态转移重演真实后续观测，而不是只利用当前图像外观，它就是预测性地表过程状态。

因此必须由多组功能性证据共同判断：

| 要检验的问题 | 正确实验 | 能证明什么 |
|---|---|---|
| z 是否保留地表内容 | 冻结 z，预测 NDVI、植被变化、土地覆盖等 | 没有通过丢掉一切来伪装鲁棒 |
| z 是否对未来有用 | 从 z 预测未来影像、NDVI 曲线、变化方向 | 它具有预测充分性 |
| z 是否少含产品表象 | 严格匹配的 held-out φ probe，与 metadata baseline 比 | 观测条件额外泄漏下降 |
| z 能否演化 | T(z,D) 解码后与真实隐藏或未来帧比较 | 状态转移具有现实对应 |
| 新观测能否修正 z | rollout 后加入真实中间帧，观察余下预测改善 | 支持部分可观测的更新能力 |

> [!warning] 合理但不能越界的名字
> 在没有地面真值直接标注土壤水分、生物量等情况下，z 应称为 latent predictive state，潜在预测状态，或 estimated land-surface process state，估计的地表过程状态。不能称为已经恢复的真实物理状态。

## 3.2 状态与观测条件分工的最小证明

对于首篇，最有力的 RQ2 组合是：

1. SSL4EO 上用同地点同时间 L1C 与 L2A 做产品级交叉重建；
2. 证明 z 对地表语义和未来变化仍有信息；
3. 在控制地点、日期等混杂因素后，证明 z 对产品/观测条件的额外可预测性降低；
4. 在最终 Stage 2 checkpoint 重做，而不是只在 Stage 1.5 做。

SSL4EO-S12 数据卡说明 L1C 与 L2A 可为同一 S2 时刻的两种产品，而 S1 与 S2 并非严格同一时刻；因此前者更适合产品条件分工，后者更适合互补多模态表征，而不是绝对同状态证明。([SSL4EO-S12](https://huggingface.co/datasets/embed2scale/SSL4EO-S12-v1.1))

---

# 4. 观测角度问题：不应以 45 度或 7.5 度作为标准

## 4.1 先回答结论

当前最小投稿路线不需要把“从 z 反推观测角度”作为核心任务，因此没有必要把精力放在 45 度、7.5 度或终端观测角度中位数上。

若将来真的做角度泄漏 probe，正确问题也不是“模型应猜到多少度”，而是：

> 在 z 没有观测角度信息时，一个回归器所能达到的无信息误差是否只等于训练数据的统计基线；加入 z 后是否有显著增量预测能力？

## 4.2 正确统计基线

若以 MSE 回归角度：

- 没有任何信息时，最优常数是训练集均值；
- 不是理论区间 0 到 90 的中点 45 度。

若以 MAE 回归角度：

- 没有任何信息时，最优常数是训练集中位数；
- 这可能是 7.5 度，也可能不是，取决于真实数据分布。

最规范的指标不是某个“正确固定角度”，而是：

$$
\Delta R^2 = R^2(metadata+z \rightarrow \phi)-R^2(metadata \rightarrow \phi)
$$

若 ΔR² 近于零，说明 z 没有提供 metadata 之外额外的观测条件信息。metadata 至少应包含位置、日期、轨道或传感器等，因为它们本身与角度和地表类型有关；否则 probe 会误把地理相关性当成 z 泄漏。

对于 azimuth，方位角，需预测 sin 和 cos 或使用圆周误差，不能把 359 度和 1 度当成相差 358 度。

## 4.3 Sentinel-1 与 Sentinel-2 不能把所有角度混在一起

| 角度 | 0 度含义 | Sentinel-2 | Sentinel-1 IW | 能否直接混合 |
|---|---|---|---|---|
| view zenith 或 off-nadir，观测天顶角/离轴角 | 正下视 | 通常较小；Sen2Cor LUT 采用 0 到 10 度传感器视角 | 非同一量 | 否 |
| solar zenith，太阳天顶角 | 太阳在头顶 | 0 到 70 度可用 | SAR 不依赖太阳照明 | 否 |
| incidence angle，SAR 入射角 | 雷达波与地表法线夹角 | 不适用 | Sentinel-1 IW 约 29.1 到 46.0 度 | 否 |

Sentinel-2 的反射率确实会受太阳天顶角、传感器视角和相对方位角影响；Sen2Cor 文档中传感器视角查找表是 0 到 10 度，太阳天顶角是 0 到 70 度。([Sen2Cor Manual](https://step.esa.int/thirdparties/sen2cor/2.12.0/docs/OMPC.TPZ.SUM.002%20-%20i1r1%20-%20Sen2Cor%202.12.03%20Configuration%20and%20User%20Manual.pdf)) Sentinel-1 IW 的 29.1 到 46.0 度是 SAR 入射角，不能同 S2 的 view zenith 合成一个标签。([Sentinel-1 Observation Scenario](https://sentinel.esa.int/web/sentinel/missions/sentinel-1/observation-scenario))

## 4.4 为什么首篇不做角度反推或几何观测算子

1. 当前 GreenEarthNet 主训练接口没有经过统一验证的逐帧完整几何元数据；
2. S1/S2 不严格共时，不能拿来当干净的同状态、不同几何配对；
3. 云是缺失和质量机制，不是普通、可自由替换的 φ；
4. 如果 decoder 没有真实受控的 φ 输入，做几何声称只会扩大不可检验的风险。

未来若有可靠配对，可固定 z、给定已知 φ，检验 O(z,φ) 是否正确重现对应产品或几何观测。评价目标仍不是“角度应为 7.5 度”，而是更换已知 φ 后能否产生对应观测。

---

# 5. direct 加 rollout：含义、训练和严谨性

## 5.1 最直白的解释

- direct path，直接路径：从当前状态一次跳到第 h 天未来；
- rollout path，连续推演路径：用同一个短步 T 走多次，每次从上一步预测状态继续向前。

两者都应和真实未来影像或真实 NDVI 比较。rollout 不能只证明自己的 latent 向量与 direct 向量接近。

## 5.2 direct 是否放在主实验

是。direct 不应被删除：

- 它通常是强、稳定的事实预测基线；
- 它告诉读者新的机制没有因为世界模型叙事而放弃实际预测性能；
- 若 rollout 的远期性能略弱，direct 可以承担主预测任务，rollout 在中短期和隐藏帧重演上展示机制价值；
- 它是防止评审说“只是模型更复杂”的必要对照。

但不能让 direct 单独作为连续模拟的证据。主实验中应有 direct 的主表成绩，也应有 rollout 的隐藏帧和自由推演成绩。

## 5.3 代码如何体现

当前代码已有 direct 的原型。未来最简单的实现不是两套 encoder，而是两套匹配的训练配置：

| 组件 | direct | rollout | 设计原则 |
|---|---|---|---|
| encoder / state interface | 同一 Stage 1.5 初始化 | 同一初始化 | 排除感知差异 |
| observation decoder | 同一架构、相同损失 | 同一架构、相同损失 | 两者均对真实观测负责 |
| dynamics | F_direct 一次跳跃 | T_δ 重复 K 次 | 差异只在是否可组合 |
| 参数量 | 匹配或明确报告 | 匹配或明确报告 | 防止容量解释 |
| 训练运行 | 一次独立训练 | 一次独立训练 | 独立训练是严谨的 |

rollout 的最小式子为：

$$
\hat{z}_{t+(k+1)\delta}=T_\theta(\hat{z}_{t+k\delta},D_{k:k+1},G,c_{t+k\delta},\delta)
$$

训练顺序：

1. 先训练单步；
2. 再用 teacher forcing，教师强制，训练 2 到 4 步；
3. 再逐渐加入 scheduled sampling，计划采样；
4. 最终以模型自己的前一步连续前推，即 free rollout，自由推演；
5. 每一步均解码并对真实可见像素计算损失；
6. 汇报真实终点与真实隐藏中间帧误差。

## 5.4 两条路径是否需要单独训练

可以，而且推荐初版分开训练。它们不需要不同 encoder；用同一 Stage 1.5 权重初始化、相同数据切分和近似参数量的独立运行，反而最公平。

之后可以尝试 hybrid：以 rollout 为主，再加一个 direct terminal loss 作为辅助。但论文必须报告纯 free rollout 的真实效果，不能只报告辅助的 direct 端点。

## 5.5 这是否严谨，文献中有无类似思想

严谨。世界模型通常要检验内部状态能否在条件或动作下连续推进，而非只预测一个终点。AAAI 的 Drive-OccWorld 将未来状态预测、条件化未来和规划收益形成链条，不只报告单帧生成。([Drive-OccWorld, AAAI-25](https://ojs.aaai.org/index.php/AAAI/article/view/33010))

EO-WM 也将稀疏、云污染卫星序列视为部分可观测、天气驱动的世界建模问题，并在确定性比较方法中处理预测 rollout。([EO-WM](https://arxiv.org/html/2606.27277)) 我们的创新不应是“也做 rollout”，而应是显式共享状态、可重用 T 和隐藏帧重演证据。

> [!danger] 必须避免的伪证明
> 如果 direct 与 rollout 的 z 很相似，但二者都偏离真实未来，只能说明它们一致地错。组合差只是诊断指标；真实中间帧和终点误差才是核心。

---

# 6. RQ1–RQ4、下游任务与 Foundation Model 的位置

## 6.1 RQ1–RQ4 是正文的最小最终实验设计

39 中将实验拆得较多。最终正文应收敛为四个必须回答的问题，其他作为增强或补充材料：

| RQ | 问题 | 核心证据 | 论文主张 |
|---|---|---|---|
| RQ1 | 能否预测真实发生的未来 | 官方 IID/OOD 主表和 horizon 曲线 | 基本事实能力 |
| RQ2 | z 是否为观测条件之外、有语义且预测充分的状态 | 产品交叉重建、probe、最终 checkpoint 验证 | 状态和观测分工 |
| RQ3 | 共享短步 T 是否能重演中间过程并自由推演 | 隐藏帧、direct 对 rollout、误差随步数 | 可组合过程模拟 |
| RQ4 | 天气与新观测更新是否真实有效 | true/no/shuffled/wrong-year D；可选同化 | 驱动有效性和部分可观测更新 |

同化、不确定性、极端事件、Foundation Model 2×2 都很有价值，但不应使 RQ1–RQ4 失焦。

## 6.2 下游任务是否必须

不是必须。论文的主任务本身就是地表过程的事实预测和重演；如果 RQ1–RQ4 完成，已有完整任务、机制、验证闭环。

推荐一个轻量 state usefulness probe，状态可用性探针：

- 冻结 z；
- 线性层或小 MLP 预测 NDVI、NDVI 变化、植被变化等级或公开土地覆盖标签；
- 和 raw image feature、普通时序 encoder、Foundation Model feature 比；
- 它只证明 z 没有丢掉有用地表信息，不能取代世界模型主证据。

若做真正下游，优先选择与主线一致的任务：

1. 预测 NDVI 轨迹上的植被衰退或干旱响应；
2. 缺失观测重演后对变化检测的收益；
3. 新观测同化后，余下窗口预测的提升。

不建议为凑下游做建筑分割、城市变化或洪水制图；其时间尺度和物理过程会使首篇的世界定义失焦。

## 6.3 大模型加 ours 是否必要

不是 P0 或 P1 的必要条件，但有 8 张 H200 时很值得做。正确分工是：

> Foundation Model 负责强感知或生成先验；ObsWorld 负责状态接口、转移和更新机制。

最有说服力的是 2×2，不是只比较某个大模型加 ours：

| 感知骨干 | 动力学头 | 回答的问题 |
|---|---|---|
| 轻量 encoder | direct | 普通预测基线 |
| 轻量 encoder | ObsWorld rollout | 机制本身有效吗 |
| Foundation Model encoder | direct | 强感知带来多少提升 |
| Foundation Model encoder | ObsWorld rollout | 强感知下机制是否仍有效 |

必须保持数据、输入、decoder、切分和评测一致。这样才能排除“提升只来自更大 backbone”的解释。

## 6.4 各实验使用什么对照

| 实验 | 必须对照 | 有条件再加 |
|---|---|---|
| RQ1 | persistence、climatology、Earthformer/Contextformer、Stage 2-D、Stage 2-R | EO-WM 协议兼容结果、Foundation 2×2 |
| RQ2 | Stage 1、修复 Stage 1.5、最终 Stage 2、no-φ/no-bottleneck | 遥感基础模型冻结特征 |
| RQ3 | 容量匹配 direct、teacher-forced rollout、free rollout | no composition、不同 rollout 长度 |
| RQ4 | true D、no D、calendar-only、within-season shuffle、wrong-year D | EO-WM 的 Extreme 和 Matched-Pair 诊断 |
| 同化增强 | no update、gated update、完整历史重新编码 | 不同缺失时间长度 |

---

# 7. 对 39 的正式修订：最终 AAAI 主线

39 的“采集稳健和可组合状态转移”是正确的证据方向，但若作为摘要中心，读者可能将文章看成表征学习或领域泛化工作，失去“模拟发生了什么”的原始强度。

最终应改为：

> 主线是观测扎根的地表过程模拟。状态与观测条件分工，是为了不把传感器表象误当世界；可组合转移，是为了重演观测之间发生的过程；驱动负对照，是为了检验天气是否提供了季节之外的事实预测信息。

## 7.1 39 中需要修正的地方

| 39 中的表述或倾向 | 修订后的判断 |
|---|---|
| B8A 映射使全部 NDVI/loss 失效 | 更准确：首先是预训练 encoder 的通道语义错位；目标张量的 NDVI 次序未必失效。必须修复和做对照，但不夸大 |
| ENS 只是 legacy，不能用 | 原 EarthNet2021 仍应按官方 ENS 协议；GreenEarthNet 使用自身官方指标。问题是不能混用 |
| direct 与 composed 接近即可证明组合性 | 不成立。二者均须对真实未来准确 |
| 强制 z_S1 等于 z_S2 | 不推荐。共享子空间和私有残差更符合不同传感器物理含义 |
| 所有 φ 都应被去除 | 不成立。日期、地形、部分几何与世界状态相关；应清楚定义纯观测变量并控制混杂 |
| 把不确定性列为主贡献 | 当前未实现可靠不确定性，降为 Stage 4 |

## 7.2 最终写作边界

不要写：

- 恢复真实世界的完整状态；
- 交换天气得到因果反事实；
- 第一个天气驱动 EO 世界模型；
- 当前 FiLM decoder 是半物理观测模型；
- 用多个 h 头证明连续 rollout；
- 使用未来云真值作为 future φ。

可以写：

- estimated predictive state，估计的预测性状态；
- driver-conditioned transition，外生驱动条件下的转移；
- factual forecasting 或 factual replay，事实预测或事实重演；
- scenario rollout under prescribed drivers，给定驱动的条件情景推演；
- observation-conditioned rendering，观测条件渲染；
- does not establish causal intervention，不构成因果干预。

---

# 8. 现有实现问题总表

## P0：正式结论前必须处理

| 问题 | 证据位置 | 后果 | 推荐处理 | 影响阶段 |
|---|---|---|---|---|
| DEM 单通道 LayerNorm 归一为常数 | models/adapters/geo_tokenizer.py 28–33 | G 中 elevation 无效 | 改为显式标准化加卷积或合适空间归一化 | Stage 0、Stage 2 |
| Stage 1.5 重建旁路 z | train/train_stage1_5_dual_conditioned.py 208–218 | 重建好不证明 z 是状态 | decoder 必须真正从 z 与 φ 重建；私有残差限容量 | Stage 1.5 |
| Stage 2 φ 实际未进入 decoder | dynamics/obsworld_stage2.py 87–92；decoders/earthnet_observation_decoder.py | 不可称观测条件渲染 | 传入推理时已知 φ；没有可靠 φ 就收紧主张 | Stage 1.5、2 |
| 旧 φ probe 无效 | eval/eval_phi_leakage_probe_fixed.py | 旧数值不可入论文 | 正确池化、最终权重、严格 train/test/location/time split | Stage 3 |
| D 与 h/calendar 混杂 | data/datasets/earthnet2021.py 822–856 | 天气消融不等于天气效果 | 提供逐步 D，calendar 单列，做负对照 | Stage 2、3 |
| 多 h 直接输出而非 rollout | obsworld_stage2.py 121–133 | 不能证明连续模拟 | 新建 Stage 2-R 的共享短步 T | Stage 2-R |
| 云置零及 token 末次有效时刻混合 | obsworld_stage2.py 81–94；context_state_aggregator.py 93–95 | 一个 z 可能是不同日期空间拼贴 | 输入 mask、clear fraction、last-observed age；最终用 update 机制 | Stage 0、2 |
| 数据集与指标协议易混 | eval/earthnet_standard_metrics.py 等 | 数字不可比 | 每张表明确数据、split、官方指标脚本 | Stage 0、3 |
| 消融 yaml 会被 require_all_driver_features 阻止 | scripts/generate_stage2_ablation_configs.py；train/train_stage2_earthnet.py | no-VPD 等实验跑不出 | 配置同步覆盖检查，做小样本预跑 | Stage 0 |

## P1：不阻塞原型，但会影响最终说服力

| 问题 | 判断 | 推荐处理 |
|---|---|---|
| B8A 映射到 canonical B08 | 预训练 adapter 通道语义风险 | 修映射或做 B08/B8A 适配对照 |
| target encoder 可训练 | 移动监督与潜在 collapse 风险 | frozen 或 EMA teacher |
| Stage 2 后期 unfreeze encoder | 可能毁掉 Stage 1.5 性质 | 最终 checkpoint 重跑全部 RQ2 |
| Stage 1.5/2 decoder 不统一 | 削弱统一观测模型 | 接口、初始化或损失尽量统一 |
| 无 logvar/概率输出 | 当前不能主张不确定性 | Stage 4 后再加入 |
| 时间编码只有序数 | 固定 5 天可暂用，不支持不规则采样叙事 | 输入真实 Δt 后再宣称 |

---

# 9. Stage 0 到 Stage 4 的技术路线

## Stage 0：数据和评测可信性

目标：在训练前确保任何结果都可解释。

- 审计 Stage 1 canonical band 和 EarthNet B8A 的 adapter 映射；
- 修复 DEM 单通道归一化；
- 将 cloud mask、有效比例、每 token 最后观测年龄明确输入，而不是将云简单置零；
- 为 x、mask、φ、D、G、calendar、Δt 建立字段契约，注明预测时是否可知；
- 固定 GreenEarthNet 与 EarthNet2021 各自官方 split 和 metric；
- 对每个消融配置做最小预跑。

验收：

- 高程 token 不为常数；
- no-D/no-feature yaml 可以开始训练；
- persistence 和 climatology 的官方结果可复现；
- 随机抽样可人工核对波段、mask、NDVI 和日期。

## Stage 1：感知预训练

目标：获得可靠 encoder，不把其本身包装成世界模型创新。

推荐：

- 若 Stage 1 的数据语义正确，保留已有权重；
- 先 frozen 使用，作为所有后续方法共同初始化；
- 如需 EarthNet B8A，训练明确定义的 adapter，而不是隐式把 B8A 当 B08；
- 记录数据、尺度、波段和许可证。

结论：仅因加入 T 不需要重训 Stage 1。

## Stage 1.5：真正建立状态接口

目标：确保 z 不能被 reconstruction 绕过。

推荐结构：

$$
(z_{shared},r_{private})=E(x,\phi), \qquad \hat{x}=O(z_{shared},r_{private},\phi)
$$

原则：

1. 预测和转移只使用 z_shared；
2. r_private 是小容量残差，不得成为无限制 encoder bypass；
3. 对齐只作用于共享子空间，并考虑 S1/S2 时间差；
4. 先做产品级 L1C/L2A 分工，不把复杂角度作为首要 φ；
5. 训练后执行严格 held-out probe；
6. Stage 2 完成后再在最终 checkpoint 重跑。

## Stage 2-D：direct 性能护栏

目标：保留原 DGH 路线的优势，得到可靠主表基线。

模型：

$$
\hat{z}_{t+H}=F_{direct}(z_t,D_{t:t+H},G,c_t,H)
$$

必须修改：

- D 使用清晰天气路径，calendar 单列；
- 修 DEM、B8A、mask、消融、目标 encoder；
- 未来未知云不可进入主输入；
- 若 encoder 解冻，重跑 RQ2。

这条分支可以直接承担预测主表，但不承担 rollout 主张。

## Stage 2-R：共享短步状态转移

目标：完成最核心的世界模型机制。

模型：

$$
\hat{z}_{t+(k+1)\delta}=T_\theta(\hat{z}_{t+k\delta},D_{k:k+1},G,c_{t+k\delta},\delta)
$$

推荐实现：

- 从 5 天单步开始；
- 输入为空间状态 token、该时间块天气、DEM/静态 token、calendar、真实 Δt；
- 输出状态残差，即下一状态等于当前状态加变化量；
- 使用门控残差 Transformer 或条件 SSM，先不追求复杂 Neural ODE；
- 初期单步，再 2 到 4 步 teacher forcing，再 scheduled sampling，最后 free rollout；
- 每步解码都对真实观测做 mask-aware loss；
- 与 direct 使用匹配容量和同一初始化。

## Stage 3：固定 checkpoint 的论文证据

目标：将“模型跑出来”与“主张被验证”分开。

- RQ1 官方预测主表与 horizon 曲线；
- RQ2 产品分工、语义和未来 probe；
- RQ3 隐藏中间帧重演、teacher forcing 与 free rollout；
- RQ4 true/no/calendar/shuffled/wrong-year D；
- 3 seeds、地点级 bootstrap、成功与失败案例；
- 保存所有实验配置和结果索引。

## Stage 4：上限增强，非首篇阻塞

| 项目 | 价值 | 何时做 |
|---|---|---|
| assimilation，同化更新 | 最强部分可观测世界模型证据之一 | RQ1–3 稳定后 |
| Foundation Model 2×2 | 证明机制可迁移至强感知 backbone | direct/rollout 已完成后 |
| EO-WM Extreme/Matched-Pair | 正面对标最近邻天气响应 | 协议兼容后 |
| 不确定性 | 处理多解未来与可靠性 | 有可靠概率输出后 |
| 半物理几何观测模型 | 增强物理性 | 有真实几何配对和独立验证后 |
| 主动采集 | 新颖但属于另一篇的决策问题 | 有可验证 decision environment 后 |

---

# 10. 最终实验闭环、正文表格与成功线

## RQ1：能否预测真实发生的未来

设计：

- 数据：GreenEarthNet earthnet2021x 的 IID、OOD-t、OOD-s、OOD-st；原 EarthNet2021 比较时完全遵循其 ENS 协议；
- 模型：persistence、climatology、Earthformer/Contextformer、Stage 2-D、Stage 2-R；
- 指标：数据集官方 R2、RMSE、NSE、bias、climatology outperformance，外加 horizon 曲线；
- 统计：3 seeds、地点级 bootstrap CI、同一切分。

证明：模型锚定真实未来，而不是只具有内部自洽。

可接受：rollout 最远端略弱于 direct，但中短期好且高于 persistence/climatology。  
不可接受：无法稳定超过简单基线，或协议混用。

## RQ2：z 是否为有用且较少依赖观测外观的状态

设计：

1. SSL4EO 同地点同时间 L1C/L2A 的产品交叉重建；
2. no-φ、no-bottleneck、bypass 对照；
3. 冻结 z 预测 NDVI、未来变化、植被语义；
4. metadata 到 φ 与 metadata 加 z 到 φ 的增量 probe；
5. 所有结果在 final Stage 2 checkpoint 重跑。

证明：z 保留地表内容和未来信息，并较少依赖产品外观。  
不证明：z 已经是可直接解释的真实土壤水分或生物量。

## RQ3：共享短步 T 是否重演观测之间真正发生的过程

设计：

1. 从真实序列中遮掉清晰中间帧，不只遮最后一帧；
2. 输入遮挡前历史和真实天气路径；
3. 解码被遮掉的中间日期与终点，并和真实帧比较；
4. 比较 direct、teacher-forced rollout、free rollout；
5. 画误差随步数或跨度增长曲线；
6. 报告 direct 与 rollout 的差距，但只作为诊断。

唯一关键判据不是两个 latent 是否接近，而是：

$$
error(\hat{x}^{rollout}_{t+H},x_{t+H})
$$

以及中间真实帧的误差是否合理。

证明：模型可由一个重复使用的短步机制跨越未观测区间重演真实地表过程。这是保住“模拟真实世界发生什么”立意的最重要实验。

## RQ4：天气和新观测是否真的贡献

天气必须做以下负对照：

| 条件 | 回答的问题 |
|---|---|
| true D | 真实天气下的事实预测 |
| no D | 不提供天气时是否退化 |
| calendar-only | 排除只是知道季节 |
| within-season 或 location shuffle D | 排除月份或地点代理 |
| wrong-year D | 使用同地点同季节不同年份天气，检验预测变化是否与真实差异方向一致 |

评测可用真实 NDVI 方向、衰退强度和极端窗口。EO-WM 的 Extreme Summer 与 Seasonal Matched-Pair 可以作为对标诊断，但它们验证的是事实响应一致性，而不是因果识别。([EO-WM benchmark](https://arxiv.org/html/2606.27277))

同化为推荐增强：

1. 先从早期观测 free rollout；
2. 在中间时刻揭示一张真实新观测；
3. 比较 no update、gated update、重编码完整历史；
4. 评价之后窗口的预测改善。

## 10.1 正文表格与图

| 位置 | 内容 | RQ |
|---|---|---|
| Table 1 | 官方预测 IID/OOD 主表，含 direct 和 rollout | RQ1 |
| Figure 1 | 状态估计、转移、观测框架图 | 总叙 |
| Table 2 | 状态、观测分工、语义与未来 probe | RQ2 |
| Figure 2 | 隐藏帧重演案例与 rollout error curve | RQ3 |
| Table 3 | direct、teacher forcing、free rollout、不同长度 | RQ3 |
| Table 4 | true/no/calendar/shuffle/wrong-year D | RQ4 |
| Figure 3 | NDVI 驱动响应，包含失败案例 | RQ4 |
| Supplement | 同化、Foundation 2×2、极端事件、完整 seeds | 增强 |

四者共同的论文句子：

> RQ1 证明模型对真实未来负责；RQ2 证明内部表示不是简单产品外观或无信息压缩；RQ3 证明同一短步机制可以跨越未观测区间重演过程；RQ4 证明天气提供了季节之外的事实预测信息，并可选地证明新观测可修正内部状态。它们共同支持观测扎根的地表过程世界模型，而不是普通未来图像回归。

## 10.2 成功线与允许的不理想结果

| 维度 | 最低成功线 | 允许的不理想结果 | 会危及主线的结果 |
|---|---|---|---|
| RQ1 | 稳定优于 persistence 与 climatology，且主表具竞争力 | 不一定所有像素指标均第一 | 无法超简单基线 |
| RQ2 | 语义和未来信息保留，产品条件增量泄漏下降 | 不能要求完全随机或完全不可预测 | z 无语义、无未来信息，或靠 bypass 重建 |
| RQ3 | free rollout 对真实中间和终点有效，误差随步数有可解释增长 | 远期略弱于 direct | direct/rollout 都对真实未来差，只在 latent 一致 |
| RQ4 | true D 优于 no D 或合理负对照 | 某单独天气通道作用弱 | calendar-only 与 true D 无区别，或 shuffle 更好且无法解释 |

---

# 11. 公开数据能与不能证明什么

| 数据 | 最适合承担 | 不应承担 |
|---|---|---|
| GreenEarthNet 或 earthnet2021x | 植被预测、时间/空间 OOD、隐藏帧重演、天气消融 | 精确几何算子、因果反事实 |
| 原 EarthNet2021 | 历史方法和 EO-WM 协议兼容对比 | 与 GreenEarthNet 指标混用 |
| SSL4EO-S12 | L1C/L2A 产品分工、预训练 | S1/S2 严格同状态证明 |
| DeepExtremeCubes | 极端或更强 OOD 补充 | 当前主过程的一致时间网格 |
| DynamicEarthNet/CropHarvest | 轻量语义 probe | 替代事实预测主任务 |

> [!important] 公开数据并不是根本瓶颈
> 它足以支持事实重演、预测、驱动有效性、跨产品表征和 OOD 的世界模型证据；它不支持无干预条件下的严格因果，或对地下未观测状态的绝对解释。把边界写清楚会增强而非削弱论文。

---

# 12. 代码修改前的决策清单

## 必须确定的五件事

- [ ] 首篇世界范围固定为植被主导、气象驱动、约 100 天窗口的地表过程。
- [ ] 正式使用“观测扎根的地表过程世界模型”作为总定位。
- [ ] 现有 Stage 2 定义为 Stage 2-D direct baseline，不再承担 rollout 主张。
- [ ] 接受 Stage 1.5 必须重训，旧 φ probe 数字不进入论文。
- [ ] 同化、不确定性、精确几何、Foundation 2×2 放入 Stage 4，不阻塞 P0–P1。

## 推荐执行顺序

1. 写字段契约：每个字段属于 x、mask、φ、D、G、calendar、Δt 的哪一类，预测时是否可知；
2. Stage 0 修复与最小预跑；
3. 先将 Stage 2-D 跑成严谨、可复现的预测 baseline；
4. 重训 Stage 1.5；
5. 实现 Stage 2-R 的单步到多步 rollout；
6. 固化 RQ1–RQ4；
7. 最后用 8 张 H200 并行运行 seeds、2×2、OOD、mask 与驱动消融。

> [!tip] 算力使用原则
> 8 张 H200 的最大价值不是把一个未经验证的模型放大，而是并行做 3–5 seeds、direct/rollout 消融、OOD 切分、天气负对照和 2×2，从而提高证据可信度。

---

# 13. 术语与本地文件索引

## 术语

| 英文 | 中文 | 本项目精确定义 |
|---|---|---|
| World model | 世界模型 | 有状态、转移、观测接口的模型，不是只生成未来图片 |
| Predictive state | 预测性状态 | 对未来充分、可随驱动演化的内部状态 |
| Transition T | 状态转移 | 在短时间步内将状态按 D、G、calendar 推进的共享模块 |
| Direct prediction | 直接预测 | 从 z_t 一次跳到 z_t+h |
| Rollout | 连续推演 | 重复调用同一个 T_δ，以前一步预测为下一步输入 |
| Teacher forcing | 教师强制 | 训练时用真实或 teacher 状态做上一步输入 |
| Scheduled sampling | 计划采样 | 训练时逐渐混入模型自己预测的状态 |
| Observation model O | 观测模型 | 在已知采集条件下从状态生成卫星观测 |
| Exogenous driver D | 外生驱动 | 天气等模型外产生、影响地表变化的输入 |
| Assimilation | 同化或更新 | 新观测出现后修正已经推演的状态 |

## 本地文件

| 用途 | 文件 |
|---|---|
| 原始状态、动力学、观测主线 | D:\Mine Program\codexwork\CVPRAAAI投稿\idea\20260608——ObsWorld_主线定稿_v5.md |
| 旧主线融合总结 | D:\Mine Program\codexwork\CVPRAAAI投稿\output\05_ObsWorld新主线总结与可行性审查.md |
| 当前 33–35 叙事 | D:\Mine Program\codexwork\CVPRAAAI投稿\output\33_ObsWorld AAAI最终叙事与实验闭环.md |
| 独立审查档案 | [[39_ObsWorld_AAAI叙事前沿文献公开数据与代码独立审查_完整汇总]] |
| 当前 Stage 2 模型 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\dynamics\obsworld_stage2.py |
| 当前转移模块 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\models\dynamics\state_dynamics_module.py |
| Stage 1.5 训练 | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\train\train_stage1_5_dual_conditioned.py |
| φ probe | D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026\eval\eval_phi_leakage_probe_fixed.py |

> [!summary] 最终建议
> 最高成功率路线不是退回普通预测，也不是马上制造无法验证的强模拟器，而是：先修复可证伪的工程问题；保留 direct 作为性能护栏；重建不可旁路的状态接口；训练共享短步 T；用真实隐藏帧和 free rollout 证明重演；用天气负对照证明驱动增益。这样既保住“模拟真实世界发生什么”的原始野心，也让每一个主张都有公开数据能够支撑的证据。
