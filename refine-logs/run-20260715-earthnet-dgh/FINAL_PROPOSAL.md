# Final Proposal：EarthNet-first ObsWorld with DGH

日期：2026-07-15  
状态：方法定稿候选；当前只整理思路，不修改训练代码

## 1. 一句话结论

不应放弃 EarthNet2021、DGH、Stage1/1.5，也不应放弃“模拟真实世界”的母叙事。更稳妥的收敛方式是：

> **以 EarthNet2021 benchmark family 为研究主线，以 GreenEarthNet protocol over the EarthNet2021x release 为主实验协议；把 D/G/H 从条件字段升级为受控状态转移的明确接口，并通过“产品轴的跨观测解码”与“时间轴的控制感知分割一致转移”两条约束，支撑一个可由真实卫星产品核验的 EO 世界模型。**

## 2. 推荐中心叙事

中文正式版：

> **ObsWorld 是一个按观测过程与地表动力学进行角色分工的对地观测世界模型。它从多源、受传感器、产品与成像条件 `phi` 影响的遥感观测中，推断对未来预测足够的 EO 可观测地表动力学状态；在区间外生驱动 `D`、静态地理背景 `G`、日历 `C` 与时间跨度 `H/delta_t` 的约束下推演该状态；再通过给定产品条件的观测模型，将未来状态生成成可由真实卫星数据核验的未来观测。**

英文正式版：

> **ObsWorld is a role-separated Earth-observation world model. It infers a predictive state of EO-observable land-surface dynamics from heterogeneous observations affected by sensor, product, and acquisition conditions; advances that state under interval-specific exogenous forcing, static geography, calendar, and elapsed time; and maps the evolved state to future satellite products that can be verified against real observations.**

直觉版：

> **先估计地表现在可能是什么，再模拟它在天气、地形和时间作用下如何变化，最后模拟卫星会如何看见它。**

“模拟真实世界”在本稿中的可检验含义是：维护内部预测状态、在给定外生驱动下连续推演、跨时间分区保持一致，并生成可核验观测；它不等于声称完整地球模拟器、唯一真实物理状态或因果反事实系统。

## 3. 数据集定位

- GreenEarthNet **不是** EarthNet2021 的一个抽样子集。
- 它沿用 EarthNet2021 的训练位置与时空规格，是对 EarthNet2021 的增强版本；论文名为 GreenEarthNet，代码中使用 `earthnet2021x` / `en21x`。
- 因而论文统一写：**EarthNet2021 benchmark family**；主协议写：**GreenEarthNet protocol over the EarthNet2021x data release**。
- 原始 EarthNet2021 的 Extreme/Seasonal 轨道只作为兼容性和过程诊断，不与 GreenEarthNet official OOD splits 混称。

主选择 GreenEarthNet protocol 的原因不是追逐新名字，而是它保留了 EarthNet2021 的任务血统，同时提供更可靠的云掩码、完整 E-OBS、官方 OOD-t/OOD-s/OOD-st 和更适合 DGH 的地理层。

## 4. DGH 的最终身份

DGH 保留，但不能把“有天气、DEM、horizon”本身写成创新。

### D：区间驱动路径

主协议对齐 Contextformer：8 个 E-OBS 变量每 5 日做 mean/min/max，得到 24-D token。主模型与 matched Direct 使用完全相同的 24-D 序列、Train-only normalization 和同构 `E_D`。同一变长 `E_D` 为 5/10/20 日区间分别消化 1/2/4 个 token；不为不同步长设独立 driver head。raw daily encoder 降为附录增强。原有 `rr/tg/hu/qq + VPD` 设计作为 `D-core` 信息删减消融保留。

### G：静态地理响应背景

P1 只使用与强基线匹配的空间 DEM；完整地跨 location 置换 G，而不是随机打乱 DEM 像素。landcover/geomorphon 留到 P2。

### H：可组合时间接口

`H` 不只是终点编号。共享的 variable-step transition 接收 `delta_t in {5,10,20 days}`；100 日主推演由 20 次五日转移组成，并用 control-aware partition consistency 检查同一驱动路径不同时间划分是否给出一致未来。因 `D/C` 随时间变化，不将这个约束误写为普通自治 semigroup。

## 5. 统一方法

### 5.1 观测与状态初始化

```text
e_i = Q(x_i, phi_i, observation_mask_i)
s_0 = I(e_1:10, D_history, C_history, G)
```

- `Q` 是 acquisition-aware per-observation encoder；
- `I` 是冻结定义的轻量 history initializer，不再在“同一 transition”与“另一个 initializer”之间摇摆；
- future cloud truth、目标 SCL/dlmask 和事后产品元数据不得输入。

### 5.2 DGH controlled variable-step transition

```text
s_b = T_theta(s_a, E_D(d_5day[a:b], C[a:b]), C[a:b], G, delta_t=b-a)
x_hat_b = O_psi(s_b, phi_product)
```

同一 `T_theta` 训练 5/10/20 日区间。对相邻区间：

```text
s_direct = T(s, D_1:2, G, 10d)
s_comp   = T(T(s, D_1, G, 5d), D_2, G, 5d)
P(s)     = LayerNorm(s, elementwise_affine=False)
L_part   = distance(P(s_direct), stopgrad(P(s_comp)))
         + observation_distance(O(s_direct), stopgrad(O(s_comp)))
```

两条分支同时受真实未来观测监督，避免“两个分支一致地预测错”。`P` 是固定、无可学习参数的归一化，避免一致性 projector 自身塌缩。这样 composition 是同一模型内可计算的性质，而不是把两个不同模型的 latent 强行比较。

### 5.3 跨观测角色约束

现有 Stage1.5 只有 self-reconstruction、近时 S1/S2 alignment 和 nuisance penalty；它尚未训练 target-condition cross-decoding。轻量 repair 增加：

```text
s_a = Q(x_a, phi_a)
L_crossobs = d(O_target(s_a, phi_b), x_b)
```

- 近时 S1/S2 cross-decoding 只支持“多观测共享预测状态”，不支持“二者只差成像条件”的强解释；
- 同次 S2 L1C/L2A 是更干净的 product-conditioned observation experiment。主方法使用同一 decoder `O(s,p_target)`，评估 wrong condition 时只换 product token，固定 source state 和全部权重；只有它通过 geographic holdout、correct/wrong target condition 和 cross-decoding Gate，正文才使用 product-conditioned observation formation；
- 否则 GreenEarthNet 主任务明确使用 fixed-product S2 observation model。

产品轴最小消融固定为 `self only`、`self+cross-observation`、`full w/o target-product condition`、`full`。其中 full 是 Stage1.5 已有 alignment/variance/teacher 约束 + self/cross + shared decoder + product token；`w/o condition` 只从同一 decoder 移除 token，不换 head。四行总参数差限制在 10% 内。两个产品各自的归一化统计只来自 Train，target 监督始终是真实 target-product pixels，不使用 source pixels 伪造交叉目标。

## 6. Stage 路线

1. **Stage1：保留。** S1/S2 masked pretraining，作为初始化。
2. **Stage1.5-A：先验收 60k checkpoint。** 修复 split/probe，检查 paired evidence、future predictive utility 和 matched Stage2 skill。
3. **Stage1.5-B：只做轻量 repair。** 增加 cross-observation loss；优先审计并补少量 L1C matched shards，而非立刻全量重训。
4. **Stage2-A：matched Direct-DGH。** 先打通官方 protocol、full E-OBS、20 targets 和 evaluator；它是强基线，不是假装 rollout。
5. **Stage2-B1：shared 5-day rollout。** 验证递归不崩溃。
6. **Stage2-B2：主方法。** variable-step transition + partition consistency + role-separated inputs。
7. **Stage3：优先强化观测模型证据。** `U` 新观测校正只有在核心通过后再做。
8. **Stage4：过程诊断和可选应用。** original EarthNet Extreme/Seasonal、一个窄 downstream 或一个 FM initializer；都不救核心失败。

## 7. 论文贡献边界

查新后，不声称 Q/T/O 状态空间分工、multi-sensor shared state、L1C/L2A translation 或 variable-step/semigroup consistency 的组件首创。[Earth-o1](https://arxiv.org/abs/2605.06337)已展示观测原生的异构观测统一动力学与 cross-sensor inference；[COP-GEN](https://arxiv.org/abs/2603.03239)已支持 native-resolution any-to-any EO generation；[Intrinsic Differential Consistency](https://arxiv.org/abs/2605.08454)已有 time-conditioned variable-step 与跨时间分区 composition regularization。

正文只保留两个需由实验联合成立的贡献点：

1. **Observation-product-axis constraint for an EO predictive state**：观测条件与动力学条件不仅有接口路由，还用 fixed-source cross-observation decoding 约束，且该约束必须改善 EarthNet future utility。
2. **Control-path-axis constraint for land-surface evolution**：同一 variable-step transition 在逐区间 DGH forcing 下形成长期可组合推演，composition gap 下降时不得伤害真实 forecast，并在 GreenEarthNet official OOD 上与强 Direct/Contextformer 比较。

真正的总贡献是这两轴在 **同一个受非自治 DGH 驱动的 land-surface predictive state** 上联合成立，而不是其中任一组件单独新颖。

因此必须做 product-axis × temporal-axis 2×2：`base/no-part`、`crossobs/no-part`、`base/part`、`crossobs/part`。四行使用同一 EarthNet Stage2、D/C/G、预算与 evaluator。如果 cross-observation state 不改善 EarthNet forecast/OOD，product axis 必须降为 mechanism-only 结果，总贡献收缩为 controlled temporal consistency，不再使用“两轴协同”。

只有 Gate 通过才加入第三个较窄结果：**product-conditioned S2 observation formation**。不声称任意传感器、任意太阳角渲染。

## 8. 失败后的合理收缩

- product `phi` Gate 失败：保留 acquisition-aware inference，decoder 限定 fixed S2；
- Stage1.5 不提升 Stage2：Stage1.5 移到附录，主模型用 Stage1；
- partition consistency 无收益：删除该 loss，论文只剩 shared transition；此时重新做 novelty Gate；
- rollout 显著弱于 Direct：停止 compositional world-model 投稿主线；
- true D 与 plausible-shuffled D 无差：删除 driver-aligned 强主张；
- G 无效：删除 G，不为 DGH 缩写强留字段；
- `U`、downstream 或 FM 失败：不影响已通过的 Stage2 核心。

## 9. 与 43 的关系

43 的代码审计、协议风险和 overclaim 检查继续有效；但其叙事对 EO-WM 反应过度，把“稀疏/局部观测 + U 校正”放得过重，并弱化了 `phi`、DGH 与状态—转移—观测三柱。本提案恢复三柱主线，同时保留 43 中正确的证据边界。
