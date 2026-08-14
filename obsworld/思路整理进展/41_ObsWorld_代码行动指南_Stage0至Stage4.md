---
title: ObsWorld 代码行动指南｜Stage 0 至 Stage 4
aliases:
  - ObsWorld 代码路线图 41
  - ObsWorld 实施清单
tags:
  - ObsWorld
  - 代码行动指南
  - Stage0
  - Stage2
  - AAAI
created: 2026-07-13
status: 设计冻结前行动指南｜不含实际代码修改
project_root: D:\Mine Program\codexwork\CVPRAAAI投稿
code_root: D:\Mine Program\codexwork\CVPRAAAI投稿\WorldModel2026
related:
  - "[[39_ObsWorld_AAAI叙事前沿文献公开数据与代码独立审查_完整汇总]]"
  - "[[40_ObsWorld_主线技术路线阶段改造与实验设计说明]]"
---

> [!abstract] 执行总原则

> **数据协议更新（2026-07-16）：**本篇是历史代码路线图。当前唯一数据/评测口径为服务器已有的 EarthNet2021x NetCDF 与 EarthNet2021 `train/iid/ood/extreme/seasonal`；冻结清单和正式接口以 [48：统一数据协议](48_ObsWorld_EarthNet2021x统一数据协议与主实验规范_20260716.md) 及 47 为准。

> 先证明每个字段和评测都可信，再重建不可旁路的状态接口；随后将 direct 和 rollout 作为两套严格配对的 Stage 2 运行进行比较；根据预先写定的门槛选择最终模型，而不是先将二者混合并从中挑最好数字。第一篇的必达终点是 RQ1–RQ4，不是同时实现同化、不确定性、精确几何和大模型。

> [!warning] 本文档不授权直接重写
> 下文是代码修改的顺序、文件地图、接口约束、测试与验收条件。修改前仍应先阅读对应文件、确认当前工作树中用户正在进行的实验，不覆盖现有运行产物。

---

## 目录

- [[#1. 最终要实现的最小系统]]
- [[#2. direct 与 rollout 的明确实施决策]]
- [[#3. Stage 0：先修数据、mask、评测与配置]]
- [[#4. Stage 1：保留并审计感知预训练]]
- [[#5. Stage 1.5：构造不可旁路的状态接口]]
- [[#6. Stage 2-D：可靠的 direct 基线]]
- [[#7. Stage 2-R：共享短步 T 的 rollout 模型]]
- [[#8. Stage 3：评测、选择最终模型与论文产物]]
- [[#9. Stage 4：Foundation Model 2×2 与其他增强]]
- [[#10. 代码文件地图、测试与产物规范]]
- [[#11. 依赖关系、停止条件与执行顺序]]

---

# 1. 最终要实现的最小系统

## 1.1 最小接口契约

所有后续实现都必须服从同一个字段契约。先写成 Python dataclass 或 batch schema，再改模型。

| 字段 | 含义 | 预测时能否知道 | 允许进入哪里 |
|---|---|---:|---|
| x_t | 遥感观测 | 已知历史，未来为标签 | encoder、loss |
| valid_mask_t | 可用像素或云质量 | 历史已知；未来仅作标签 mask | encoder、loss；不能把未来真值伪装成条件 |
| obs_age_t | 每 token 最近一次有效观测距当前时间 | 可由历史计算 | context/update |
| φ_t | 传感器、产品级别、推理时已知的几何 | 仅已知部分可用 | encoder、decoder |
| D_t:t+δ | 逐日或逐时间块天气路径 | 事实预测时可用 | transition |
| G | 静态地理背景，例如 DEM | 可用 | transition |
| calendar_t | 年内日序、月份、周期编码 | 可用 | transition |
| Δt | 真实时间间隔 | 可用 | transition |
| h | 目标跨度 | 可用 | direct 的输出索引；rollout 的步数派生量 |

> [!danger] 未来信息规则
> 未来未知云量、未来质量标记、未来目标影像和未来从影像计算出的变量，绝不进入事实预测主模型。它们只能用于监督、评分，或在明确标注为 oracle 的附加实验中使用。

## 1.2 目标架构

最小系统包含三个不可混淆的部分：

1. E：从历史观测、已知 φ 与 mask 形成 z_t；
2. T：给定 D、G、calendar 和 Δt 推进 z_t；
3. O：从未来状态和已知未来 φ 解码成预测观测。

概念上：

$$
z_t=E(x_{\le t},valid\_mask_{\le t},\phi_{\le t},obs\_age_{\le t})
$$

$$
z_{t+\delta}=T(z_t,D_{t:t+\delta},G,calendar_t,\delta)
$$

$$
\hat{x}_{t+\delta}=O(z_{t+\delta},\phi^{known}_{t+\delta})
$$

首篇不要求复杂 Kalman Filter 或 Neural ODE。关键是 T 为共享短步函数，且输出必须由真实观测检验。

---

# 2. direct 与 rollout 的明确实施决策

## 2.1 结论：P1 先做两套配对方案，不做一个混合方案

第一轮正式机制比较选择两套独立的 Stage 2 运行：

| 方案 | 动力学定义 | 角色 |
|---|---|---|
| Stage 2-D，direct | F_direct(z_t,D_t:t+H,G,calendar_t,H) 一次输出终点 | 强预测基线 |
| Stage 2-R，rollout | 同一个 T_δ 从 z_t 连续调用 K 次 | 过程模拟候选主模型 |

它们不是两个不同项目，也不使用两套 encoder。它们是同一状态接口下的受控动力学比较。

不建议在 P1 一开始实现 direct 加 rollout 混合头，原因是混合模型可以通过 direct shortcut 获得好端点，而掩盖短步 T 是否真正有效。Hybrid 仅在 P2 或 Stage 4、且独立 direct/rollout 结论成立后才探索。

## 2.2 必须控制的变量

两套运行必须固定以下全部项目：

- 同一训练/验证/测试地点与时间切分；
- 同一 Stage 1.5 encoder checkpoint；
- 同一输入波段、归一化、mask 逻辑、D、G、calendar、Δt 定义；
- 同一 observation decoder 架构、相同初始权重；
- 尽量匹配的动力学参数量、优化器、学习率日程、batch、训练步数和计算预算；
- 同一随机种子集合，例如 seed 1、2、3；
- 同一事实预测损失、相同 cloud-aware 评分；
- 同一 horizon 评测点和同一 OOD protocol。

唯一应变化的是：

| 组件 | Stage 2-D | Stage 2-R |
|---|---|---|
| 输入时间 | 直接获得完整 D 路径与 H | 每次只获得一个 D 时间块与 δ |
| 动力学调用 | 一次 | K 次、权重共享 |
| 中间状态 | 可不显式输出 | 每一步必须可被解码和评测 |
| 关键评测 | 端点事实预测 | 中间帧、free rollout、端点事实预测 |

## 2.3 encoder 与 decoder 如何控制

推荐采用两层控制，而不是含糊地说“共享 encoder”：

### 机制控制运行，必须

- E 固定为同一 Stage 1.5 checkpoint，Stage 2 不解冻；
- O 使用同一初始化、同一架构和同一训练日程；
- 各运行独立优化其 dynamics 与 decoder；
- 另做一个小规模诊断：将 E 和 O 都冻结，仅训练 F_direct 或 T_δ。

这个小规模诊断最能隔离“变化是否来自 dynamics”。即使它不是最终最高成绩，也应保留在补充材料。

### 最终性能运行，必须

- E 在 P1 仍建议冻结，避免 Stage 2 破坏 Stage 1.5 状态性质；
- O 可以在两组中以相同初始化、相同步数独立训练；
- 若后续确需解冻 E，则 direct 与 rollout 采用相同解冻时点和学习率，并且最终 checkpoint 必须重跑全部 RQ2。

这比“两个方案共享一套不断被彼此更新的 encoder 权重”更干净。后者会引入训练互相污染和实现复杂度。

## 2.4 最终模型如何选择

在代码开始前，写入实验配置的选择门槛：

| 结果 | 论文最终模型 | 处理方式 |
|---|---|---|
| rollout 在隐藏帧和 free rollout 明确有效，RQ1 与 direct 竞争或仅小幅差距 | rollout | 将 ObsWorld 定义为 rollout 世界模型，direct 为对照 |
| rollout 在 RQ3/RQ4 强，但最远端像素略弱 | 双任务分工，但不混淆 | direct 报端点预测；rollout 报过程重演；论文坦诚边界 |
| rollout 不能重演真实中间和终点 | 不选择 rollout | 不用 hybrid 掩盖；降级叙事为 direct 条件预测或继续改进 T |

推荐用统计而非绝对硬阈值：看 3 seeds 的均值、置信区间、相对简单基线的改善、以及误差随步数是否合理增长。不要预先规定“必须高 5%”之类没有统计依据的数字。

---

# 3. Stage 0：先修数据、mask、评测与配置

## 3.1 目标

让所有训练和消融在开始前具备可信输入、可信输出和可复现配置。Stage 0 不应消耗大规模训练算力。

## 3.2 必改文件与任务

| 文件 | 当前问题 | 计划修改 | 单元验收 |
|---|---|---|---|
| models/adapters/geo_tokenizer.py | 单通道高程经过 LayerNorm 可能成为常数 | 改为明确输入标准化加空间卷积，或不会在单通道末维归一化的实现 | 高低程输入产生不同 token；no-G/G 都可运行 |
| data/datasets/earthnet2021.py | D 是累计量且混入 h/日期；context token 的有效时间不统一 | 返回 weather_path、calendar、delta_t、valid_mask、obs_age 等独立字段 | 打印单样本能逐项核对时间窗口和字段可用性 |
| configs/train/stage2_earthnet_main.yaml | B8A 与 canonical band 映射、D feature 校验等有风险 | 写清 band mapping；将 require_all_driver_features 与消融配置解耦 | no-VPD/no-SRAD/no-precip 最小预跑成功 |
| scripts/generate_stage2_ablation_configs.py | 生成配置会触发主配置的 feature 完整性检查 | 为消融同步修改检查规则，保存实际覆盖值 | 每个生成 yaml 可被训练脚本加载 |
| eval/earthnet_standard_metrics.py 及评测入口 | EarthNet2021 与 EarthNet2021x 协议可能混用 | 按数据集拆开入口和结果目录 | persistence 与 climatology 的官方指标可复现 |
| 新增 tests 目录 | 目前缺少合同测试 | 加数据、mask、band、config、metric smoke tests | CI 或本地单命令小样本全通过 |

## 3.3 Stage 0 必做测试

- [ ] 高程 token 测试：两个不同 DEM 常数图输入后 token 不应完全相同。
- [ ] 波段测试：EarthNet 四通道顺序、NDVI 用红与 B8A、adapter slot 与预训练 canonical band 的关系都可打印核对。
- [ ] 时间测试：每个 target 的 D 路径、calendar、h、Δt 不相互替代。
- [ ] mask 测试：全云、部分云、零反射率三种输入不会被模型误当成同一种情况。
- [ ] 未来泄漏测试：batch 中未来 quality/cloud 字段不被传入事实预测 forward。
- [ ] 消融配置测试：所有 no-feature yaml 都能通过 preflight。
- [ ] 指标测试：同一预测不能同时被错误送入 EarthNet2021 ENS 和 EarthNet2021x 新协议。

## 3.4 Stage 0 完成定义

只有当所有 smoke test 通过、baseline 指标可复现、随机可视化样本的人为检查没有波段/时间错误时，才允许启动 Stage 1.5 或 Stage 2 的正式多卡训练。

---

# 4. Stage 1：保留并审计感知预训练

## 4.1 决策

Stage 1 不因本路线而被判定错误。若 Stage 1 使用的波段、归一化、空间尺度和预训练样本定义正确，直接保留其 checkpoint。

## 4.2 必做审计

- [ ] 写出 canonical band 顺序、各数据集 band 顺序、所用 adapter 索引。
- [ ] 确认 EarthNet 的 B8A 不是被静默映射成预训练 B08。
- [ ] 记录 Stage 1 的预训练数据、许可证、输入尺度和 mask 行为。
- [ ] 固定一个可复现的 Stage 1 checkpoint 作为 direct 与 rollout 的共同起点。

## 4.3 何时需要重训 Stage 1

只有出现下列事实时才重训：

1. 输入波段语义在预训练中已大面积错误；
2. normalization 与下游完全不兼容且 adapter 无法补偿；
3. 权重或数据定义不可追溯。

否则，优先把算力投入 Stage 1.5 和 Stage 2-R。

---

# 5. Stage 1.5：构造不可旁路的状态接口

## 5.1 当前问题

当前训练文件为 train/train_stage1_5_dual_conditioned.py。重建路径直接使用 encoder latent，state projector 的 z 主要只参与对齐和泄漏约束。因此重建成功不能证明 z 是状态。

## 5.2 最小重构目标

主重建必须以共享状态为瓶颈：

$$
(z_{shared},r_{private})=E(x,\phi)
$$

$$
\hat{x}=O(z_{shared},r_{private},\phi)
$$

其中：

- z_shared 是 Stage 2 唯一可使用的状态；
- r_private 为可选、小容量的产品/模态私有残差；
- 禁止将原始 encoder latent 无限制直通 decoder；
- 如果当前没有可信 φ，则先不做细粒度几何控制，不强行构造伪 φ。

## 5.3 建议文件拆分

| 新或修改文件 | 职责 |
|---|---|
| models/state/shared_state_projector.py | 从 encoder token 得到 z_shared 和可选 r_private |
| models/decoders/earthnet_observation_decoder.py | 统一状态观测 decoder；接口接受 z 与可选已知 φ |
| train/train_stage1_5_dual_conditioned.py | 改为所有主重建都必须经过 z_shared |
| eval/eval_phi_leakage_probe_fixed.py | 正确 token 池化、加载训练权重、严格切分 |
| 新增 eval/eval_state_usefulness.py | 冻结 z 的 NDVI、未来变化、语义 probe |

文件名可根据现有仓库风格调整；关键是职责不能再混在训练脚本内。

## 5.4 Stage 1.5 验收

- [ ] no-bottleneck 或 bypass 应显著优于/不同于真正 z 模型，证明实验对旁路敏感。
- [ ] z 保留 NDVI、未来变化等信息。
- [ ] 加 z 对纯产品/观测条件的增量可预测性降低，且 probe 有独立 train/val/test。
- [ ] 重建与产品交叉重建均不依赖未来信息。
- [ ] 保存固定 checkpoint，供 Stage 2-D 与 Stage 2-R 完全相同地初始化。

---

# 6. Stage 2-D：可靠的 direct 基线

## 6.1 目标

把当前 Stage 2 从“可跑原型”变成“可被正式比较的条件预测基线”。这不是退路，而是所有世界模型结果的性能护栏。

## 6.2 推荐接口

$$
\hat{z}_{t+H}=F_{direct}(z_t,D_{t:t+H},G,calendar_t,H)
$$

$$
\hat{x}_{t+H}=O(\hat{z}_{t+H},\phi^{known}_{t+H})
$$

## 6.3 修改清单

| 文件 | 修改方向 |
|---|---|
| models/dynamics/obsworld_stage2.py | 明确 direct 分支输入与输出；不再把它写成 rollout |
| models/dynamics/state_dynamics_module.py | 保持为 direct dynamics 或更名以避免误解 |
| data/datasets/earthnet2021.py | 接收分离后的 D path、G、calendar、h、mask、obs_age |
| models/decoders/earthnet_observation_decoder.py | 与 Stage 1.5 保持同一状态接口；只接收已知 φ |
| train/train_stage2_earthnet.py | 固定 encoder、EMA/frozen target、保存字段契约和配置快照 |
| configs/train/stage2_direct_*.yaml | 新建，不覆盖用户现有 main yaml |

## 6.4 验收

- [ ] 在官方协议上复现 persistence 与 climatology。
- [ ] direct 明显优于简单基线，且曲线没有异常时间泄漏。
- [ ] no-D、calendar-only 等消融可以真实运行。
- [ ] 训练结束的 encoder checkpoint 可被 RQ2 probe 正确加载。

---

# 7. Stage 2-R：共享短步 T 的 rollout 模型

## 7.1 目标

让状态真正通过一个共享短步机制连续演化，并在中间和终点均由真实观测核验。

## 7.2 推荐最小实现

新增而不是在当前 direct 模型中塞入复杂分支：

| 新文件建议 | 职责 |
|---|---|
| models/dynamics/stepwise_state_transition.py | 实现共享 T_δ，输入当前状态与一个天气时间块 |
| models/dynamics/obsworld_stage2_rollout.py | 管理 K 次状态推进、每步 decoder、teacher forcing 和 free rollout |
| train/train_stage2_rollout.py | 单步到多步课程训练入口 |
| configs/train/stage2_rollout_*.yaml | 固定 δ、K、teacher forcing 和 scheduled sampling 配置 |
| eval/eval_hidden_frame_replay.py | 遮挡中间清晰帧后评估重演 |
| eval/eval_rollout_diagnostics.py | horizon curve、direct/composed gap、失败案例 |

## 7.3 训练课程

1. 单步：预测 t+δ；
2. 两步到四步 teacher forcing；
3. scheduled sampling：逐渐以预测状态代替 teacher 状态；
4. free rollout：全程使用自身预测；
5. 逐步扩大从短窗口到 100 天窗口。

每一步都计算 masked observation loss。可增加 latent teacher loss，但不能只在 latent 中自洽；最终必须由影像/NDVI 的真实误差决定。

## 7.4 必须记录的运行字段

- rollout_step δ；
- rollout_steps K；
- teacher_forcing_probability；
- scheduled_sampling schedule；
- 是否冻结 E、是否训练 O；
- 每一步有效像素比例；
- 每步 image loss、NDVI loss、latent teacher loss；
- direct 与 rollout 的参数量、训练步数、wall-clock 预算；
- free rollout 与 teacher-forced 两组分开保存。

## 7.5 Stage 2-R 验收

- [ ] 一步预测稳定；
- [ ] 被遮掉的真实中间帧可被重演；
- [ ] free rollout 不发生 NaN、常量状态或快速 collapse；
- [ ] 终点事实预测与 direct 和简单基线比较；
- [ ] direct/composed 接近时，两者也必须对真实未来准确；
- [ ] 误差随步数增长可解释，而不是第一步即失效。

---

# 8. Stage 3：评测、选择最终模型与论文产物

## 8.1 RQ1 到 RQ4 的脚本化产物

| RQ | 应有评测入口 | 应有结果文件 |
|---|---|---|
| RQ1 | `eval/eval_stage2_earthnet.py` | IID/OOD 主表，Extreme/Seasonal 补充表和 horizon CSV |
| RQ2 | eval/eval_state_usefulness.py；eval_phi_leakage_probe_fixed.py | 产品交叉重建、probe、最终 checkpoint 报告 |
| RQ3 | eval/eval_hidden_frame_replay.py；eval_rollout_diagnostics.py | 中间帧与终点误差、轨迹图、失败案例 |
| RQ4 | eval/eval_driver_counterfactual_controls.py | true/no/calendar/shuffle/wrong-year D 表和 NDVI 曲线 |
| 应用增强 | eval/eval_ndvi_decline_events.py | 衰退 onset、severity、事件检测结果 |

应用增强不需要另训世界模型：从预测和真实 NDVI 曲线派生是否衰退、何时衰退、衰退多少即可。这是提高应用说服力的最低成本方法。

## 8.2 结果目录规范

每次正式运行应保存：

1. 完整 yaml；
2. git commit 或代码 hash；若目录不是 git 仓库则保存文件哈希和修改日期；
3. checkpoint；
4. 数据版本、split 清单、随机种子；
5. metrics.csv；
6. sample visualization；
7. stdout/stderr；
8. 实际参数量、训练步数和耗时。

建议目录形式：

output/runs/2026xxxx_stage2_direct_seed1  
output/runs/2026xxxx_stage2_rollout_seed1  
output/runs/2026xxxx_stage4_fm_rollout_seed1

## 8.3 论文模型选择会议需要的最小材料

- [ ] direct 与 rollout 的 3 seed 汇总；
- [ ] RQ1 主表；
- [ ] RQ3 隐藏帧及 free rollout 曲线；
- [ ] RQ4 天气负对照；
- [ ] RQ2 最终 checkpoint probe；
- [ ] 至少两个成功、两个失败的可视化案例；
- [ ] 选用最终模型的决策记录。

---

# 9. Stage 4：Foundation Model 2×2 与其他增强

## 9.1 2×2 的固定设计

| encoder | dynamics | 简称 |
|---|---|---|
| 轻量或当前 Stage 1 encoder | direct | Light-D |
| 轻量或当前 Stage 1 encoder | rollout | Light-R |
| Foundation Model encoder 加 adapter | direct | FM-D |
| Foundation Model encoder 加 adapter | rollout | FM-R |

为了公平：

- 四组使用同一 EarthNet2021x 数据、同一 split、同一 band preprocessing；
- Foundation encoder 的输出经统一 adapter 映射到相同 z 维度；
- direct/rollout 的输入字段、decoder、训练预算匹配；
- 报告可训练参数、总参数和是否冻结 Foundation encoder；
- 先 freeze Foundation encoder，确认机制信号后再考虑 LoRA 或小规模适配。

## 9.2 理想效果长什么样

令 A=Light-D，B=Light-R，C=FM-D，D=FM-R。

| 比较 | 理想观察 | 说明 |
|---|---|---|
| C 对 A | C 在 RQ1 更好 | Foundation 感知确实有价值 |
| B 对 A | B 在 RQ3/RQ4 更好，RQ1 竞争 | rollout 机制本身有价值 |
| D 对 C | D 在 RQ3/RQ4 更好，RQ1 竞争 | 强 encoder 下机制仍有增益 |
| D 对 B | D 进一步提高事实预测 | Foundation 与机制可叠加 |

最理想：FM-R 在 RQ3/RQ4 最强，并在 RQ1 也为最佳或与 FM-D 无显著差异。

可以接受：FM-D 的最远期像素分数最高，但 FM-R 在隐藏帧、free rollout、驱动响应、同化上最强，并且 RQ1 差距有限且透明报告。

不理想：FM-D 在所有项目都大幅更好，FM-R 没有任何机制优势。此时不能宣称 T 带来价值，应检查 transition、adapter 或缩小主张。

## 9.3 下游任务与拒稿风险的处理

没有独立下游任务不等于缺乏说服力。AAAI 方法论文可以以预测任务、机制消融、可控性或决策相关评测构成闭环；关键是主张和评测必须一一对应。Drive-OccWorld 使用预测到规划收益的链条，而 EO-WM 则用标准预测加天气响应诊断来证明 EO 世界建模能力。([Drive-OccWorld](https://ojs.aaai.org/index.php/AAAI/article/view/33010)) ([EO-WM](https://arxiv.org/html/2606.27277))

本项目最稳妥的做法不是硬加外部下游，而是增加同源、可解释的应用评测：

- 预测 NDVI 是否跌破衰退阈值；
- 预测衰退 onset 的时间误差；
- 预测衰退幅度或严重度误差；
- 在极端天气窗口中对早期预警或严重度分级的收益。

这会把 RQ1/RQ4 的结果转为实际监测意义，几乎不增加数据和模型风险。

---

# 10. 代码文件地图、测试与产物规范

## 10.1 当前重要文件

| 类别 | 文件 |
|---|---|
| 数据集 | WorldModel2026/data/datasets/earthnet2021.py |
| 地理 tokenizer | WorldModel2026/models/adapters/geo_tokenizer.py |
| Stage 2 总模型 | WorldModel2026/models/dynamics/obsworld_stage2.py |
| 当前 dynamics | WorldModel2026/models/dynamics/state_dynamics_module.py |
| observation decoder | WorldModel2026/models/decoders/earthnet_observation_decoder.py |
| context 聚合 | WorldModel2026/models/dynamics/context_state_aggregator.py |
| Stage 1.5 训练 | WorldModel2026/train/train_stage1_5_dual_conditioned.py |
| Stage 2 训练 | WorldModel2026/train/train_stage2_earthnet.py |
| φ probe | WorldModel2026/eval/eval_phi_leakage_probe_fixed.py |
| Stage 2 主配置 | WorldModel2026/configs/train/stage2_earthnet_main.yaml |
| 消融生成器 | WorldModel2026/scripts/generate_stage2_ablation_configs.py |

## 10.2 推荐新增测试

| 测试 | 目的 |
|---|---|
| tests/test_geo_tokenizer.py | 单通道 DEM 不是常数 |
| tests/test_earthnet_band_contract.py | B8A、NDVI、adapter slot 一致 |
| tests/test_temporal_field_contract.py | D、calendar、h、Δt 分离且无未来泄漏 |
| tests/test_mask_and_obs_age.py | 云、有效像素、最近观测时间正确传递 |
| tests/test_stage15_bottleneck.py | decoder 不可从原始 latent 旁路 |
| tests/test_rollout_shapes.py | K 步 T 的形状、时间和梯度正确 |
| tests/test_ablation_config_smoke.py | 所有 yaml 都能被训练入口加载 |
| tests/test_metric_protocol.py | 数据集只能进入对应官方 metric |

## 10.3 每次代码修改的最低验收流程

1. 静态导入和格式检查；
2. 单元测试；
3. 单 batch forward/backward；
4. 100 到 500 iteration 的 smoke train；
5. 一个小验证集评测；
6. 人工看 4 个样本，包括云、无云、不同高程、不同季节；
7. 才启动多卡正式训练。

---

# 11. 依赖关系、停止条件与执行顺序

## 11.1 依赖图

Stage 0 → Stage 1 审计 → Stage 1.5 → Stage 2-D 与 Stage 2-R 配对运行 → Stage 3 RQ1–RQ4 → Stage 4 增强

其中 Stage 2-R 依赖于：

- 正确的逐步 D 路径；
- mask 和 obs_age 处理；
- 不可旁路的 z；
- 统一或清楚匹配的 decoder；
- 能提供中间帧监督的序列数据。

## 11.2 停止并重新审计的条件

- Stage 0 基线或波段检查失败；
- Stage 1.5 的 z 无法保留未来和语义信息；
- rollout 第一两步就 collapse 或对真实中间帧明显弱于 persistence；
- weather shuffle 比 true D 更好且无法从泄漏/实现解释；
- decoder 仍能从 bypass 而不通过 z 重建；
- 最终 Stage 2 后 RQ2 性质全部消失。

发生这些情况时，先诊断数据契约和实现，不应用更大模型或更多算力掩盖。

## 11.3 最终 P0/P1 待办清单

- [ ] 完成 Stage 0 的所有 contract 与 smoke test。
- [ ] 冻结一个经 band 审计的 Stage 1 checkpoint。
- [ ] 重构并重训 Stage 1.5。
- [ ] 建立 Stage 2-D 独立 config、结果目录和官方评测。
- [ ] 实现 Stage 2-R 单步版本。
- [ ] 推进到多步 teacher forcing 与 free rollout。
- [ ] 完成 direct/rollout 三 seed 的 RQ1、RQ3 初表。
- [ ] 完成 RQ2 最终 checkpoint 重验和 RQ4 天气负对照。
- [ ] 决定 rollout 是否通过门槛成为最终 ObsWorld。

> [!summary] 最终行动顺序
> 先让现有 direct 变成可靠基线，再让状态接口真实成立，最后用配对 rollout 检验“模拟”是否成立。Foundation Model、同化和复杂下游只在这个闭环稳定后加入。这样每一次大规模训练都有明确要回答的问题，也能在 rollout 不成功时及时止损，而不是把整个项目拖入不可解释的复杂系统。
