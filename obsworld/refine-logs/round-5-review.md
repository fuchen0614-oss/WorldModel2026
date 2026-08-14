# Round 5 Review

<details>
<summary>Full raw reviewer response</summary>

## Round 5 final raw review

### 最终结论

**Overall：9.2 / 10**

**Verdict：READY**

这里的 READY 含义是：

> proposal 的问题、方法、训练、对照、mask contract 和统计验证已经闭环，可以冻结设计并进入实现与实验阶段。

它不意味着论文已经被结果支持，也不意味着必然达到 AAAI 接收水平。后续若未通过预注册门槛，应按照 stop rules 收缩或放弃 claim，而不是继续添加模块补救。

## 核心审查结果

### 1. Problem–method fidelity：PASS

最终方法直接对应原始瓶颈：

- predictive belief 由历史决定；
- `F_5` 负责无观测时的状态推进；
- 新观测到来时，模型比较 prior prediction 与真实观测；
- 只有可见证据能够改变相应 belief；
- correction 的价值由后续预测验证，而不是当前帧重建；
- open-loop 与 online correction 由同一模型完成。

同时，proposal 已主动放弃无法在当前工作中证明的内容：

- 不宣称物理真实状态；
- 不宣称因果天气作用；
- 不宣称新通用 Bayesian filter；
- 不扩张到 foundation model、LLM、diffusion 或无关 downstream；
- Stage1.5 只是可删除初始化变量。

问题范围和实际证据之间已基本一致。

### 2. Innovation 语义：PASS

最终 residual：

\[
z_t^{obs}=P(E(x_t\odot m_t^{obs})),
\]

\[
z_t^{pred}=P(E(H(b_t^-)\odot m_t^{obs})),
\]

\[
r_t=z_t^{obs}-\operatorname{sg}(z_t^{pred})
\]

具有明确语义：

- 同一可见区域；
- 同一 RGBN 归一化；
- 同一 `E/P`；
- 同一 token grid；
- 真实观测与 prior decoded prediction 直接比较。

自由 `Q` 已删除，因此不存在 `Q/R/gate` 共同重参数化、使所谓 innovation 退化为任意 hidden transform 的问题。

`stopgrad(z_pred)` 也具有清晰作用：correction loss 不能通过 residual 分支直接修改当前 decoder prediction 来缩小残差，而 `F/H` 仍通过普通 forecast loss 和后续 dynamics 得到训练。

该机制仍然属于 learned filtering/data assimilation 范畴，但现在可以准确称为：

> observation-aligned residual correction

而不是泛化成“新的 filtering theory”。

### 3. 梯度路径：PASS

最终 proposal 已正确区分：

- reveal-time `U` invocation 只由 `L_post` 监督；
- context 中共享的 `U` invocation 通过所有 downstream forecast consequences 训练。

在 reveal 时：

1. 先生成并监督 prior prediction；
2. 再读取观测并更新；
3. 当前帧没有 posterior reconstruction；
4. update 只能通过之后的预测证明价值。

segment-normalized loss：

\[
L=0.5L_{pre}+0.5L_{post}
\]

避免了早 reveal 仅因剩余 horizon 更多而获得更大的总监督权重。single reveal 也避免了多个 correction event 相互覆盖导致的归因混乱。

梯度设计已经足够清晰，不需要再增加 latent alignment、EMA target 或 posterior decoder。

### 4. Availability 与 mask contract：PASS

这一轮补充的 `a_t` 是必要且充分的。

现在严格区分：

- `m_obs/q_obs`：只用于 observation assimilation；
- `m_rgb_sup/m_ndvi_sup`：只用于监督和评估；
- unrevealed future：`a_t=0`，因此 `q_obs=0`；
- future target cloud mask 即使存在于 batch 中，也不能进入 `E/F/U/staleness`。

因此：

\[
s_t^+=(1-q_t^{obs})s_t^-
\]

不会泄漏未来云量。

以下约束已经形成完整防线：

- categorical mask nearest-neighbor resize；
- q 在 token grid 上 average-pool；
- `a=0` 时不调用 update；
- `q=0` 时 state exact identity；
- unrevealed-mask permutation invariance test；
- supervision masks 与 model-input masks 使用不同变量和路径。

这是一个可直接转化成代码单元测试的完整 contract。

### 5. VanillaFilter 公平性：PASS

VanillaFilter 获得与 proposed 相同的：

- `F/E/P/H`；
- `z_obs`；
- `stopgrad(z_pred)`；
- availability、q 和 staleness；
- reveal schedule；
- forecast supervision；
- 额外 encoder forward；
- decoder initialization；
- freeze/unfreeze policy。

它具有足够表达能力隐式学习：

\[
z_{obs}-z_{pred}.
\]

因此 proposed 与 Vanilla 的差异被压缩为：

> 是否显式施加 aligned residual inductive bias。

参数/FLOPs 控制在 5%，并报告 full-model、cell-level 和 wall-time，使信息量、容量与计算量混杂均得到处理。

PredRNN-online 则承担第二层证伪：测试成熟 pixel recurrent model 是否已经能从相同 reveal 获得同等 future benefit。

这一 falsifier chain 已达到论文级要求。

### 6. Correction statistics：PASS

primary estimand 已锁定为：

\[
G_{m,s,c,r}
=
\operatorname{mean}_{h>r}
\left(
e^{no-reveal}_{m,s,c,r,h}
-
e^{reveal}_{m,s,c,r,h}
\right),
\]

\[
\bar G_{m,s,c}
=
\frac{G_{day25}+G_{day50}}{2},
\]

\[
D_{b,s,c}
=
\bar G_{\mathrm{Ours},s,c}
-
\bar G_{b,s,c}.
\]

它具有几个重要优点：

- 相同 checkpoint 自身配对；
- day25/day50 等权，而非由后续 horizon 数量决定权重；
- 先形成 same-seed/same-cube difference；
- 再在 cube 内平均 seeds；
- 按 geographic tile 聚合；
- bootstrap tile 而不是 pixel；
- 直接 bootstrap Ours-baseline difference；
- 两个 co-primary comparison 使用 Holm 控制 family-wise error；
- clear strata 被明确定位为 effect-modification，而不是额外显著性检验。

同时要求 absolute post-reveal NDVI MAE 不更差，排除了“因为自己的 no-reveal 起点很差，所以 self-gain 看起来很大”的假改善。

统计设计已经足以支撑中心 claim。

### 7. Open-loop non-inferiority：PASS

Block A 已明确：

- primary endpoint：official NDVI RMSE；
- matched control：Direct-Seq；
- estimand：
  \[
  \Delta_{open}
  =
  RMSE_{\mathrm{ObsWorld}}
  -
  RMSE_{\mathrm{Direct}};
  \]
- non-inferiority margin：
  \[
  \delta_{NI}=0.01;
  \]
- 判定：paired tile-bootstrap one-sided upper 95% CI 小于 0.01；
- OOD-t 在 Val 锁定后只评估一次。

这使“保持竞争性 open-loop skill”从模糊描述变成了可复核 gate。

论文中仍应简短解释 0.01 margin 的领域意义或 Val-scale依据，但这属于报告要求，不再是设计 blocker。

## 是否还需要下游、第二数据集或大模型组合

当前 proposal 不需要这些内容才能成立。

理由是中心 claim 已经由最近的能力测试直接验证：

> 给模型一帧空间不完整的新 EO observation，它能否比 generic filter 和 pixel recurrence 更有效地改善之后的预测？

这比分类、分割等远距离 downstream 更直接。

第二数据集会提高外部有效性，但 GreenEarthNet 已包含：

- official OOD-t；
- OOD-s/st secondary tracks；
- day25/day50 correction；
- 全 cube；
- clear-fraction effect analysis。

对于一篇七页、单一机制 claim 的论文，这可以形成足够完整的证据链。

AnySat/TerraMind 或“FM + ours”只有在轻量机制已经成功后，才适合作为后续扩展；现在加入会削弱归因并扩大工程风险。

## 剩余风险：不是设计 blocker

### 1. 贡献仍然偏窄

该方法不是全新 filtering 理论，而是 EO partial-observation 场景下的结构化 residual update。能否达到 AAAI 水平将高度依赖：

- 对 Vanilla 的稳定优势；
- 对 PredRNN-online 的稳定优势；
- 低/中 clear-fraction 下仍有收益；
- open-loop 不退化；
- effect size 不只是统计显著而且具有实际意义。

若优势很小或只出现在最高-clear strata，不能靠增加下游任务挽救原 claim。

### 2. Direct 必须真的是强 baseline

通过相对弱的 Direct 的 non-inferiority 不足以支持“competitive official skill”。因此结果表中还应确保：

- Direct 本身经过充分调优；
- Contextformer/PredRNN reproduction 与官方量级一致；
- ObsWorld 没有明显落后于所有外部 skill anchors。

这属于未来结果门槛，不要求现在改变方法。

### 3. NI margin 需要说明依据

`0.01 NDVI RMSE` 已在 OOD 前锁定，这是正确的。最终论文应说明它来自：

- domain-relevant tolerance；
- Val variation；
- 或基准中有意义的效果量。

不能在看到 OOD 结果后修改。

### 4. Bootstrap 实现要保持 official metric 定义

对于 Block A，若 official NDVI RMSE 是非线性全局聚合量，bootstrap 每个 replicate 时应在重采样 tile 上重新计算指标，而不是简单平均预先计算的 tile RMSE。

Block B 已明确使用 cube-level MAE，因此其聚合单位没有这一歧义。

### 5. 低 \(q\) 更新可能过弱

masked feature residual 本身可能随 clear support 下降，外层再乘 \(q\) 后，极低-clear observation 的 correction 可能很弱。

当前不应提前增加 normalization 模块。clear strata 和 binary/continuous q ablation 已足以判断：

- 若低 \(q\) 仍有效，现有设计成立；
- 若只在高 \(q\) 有效，应收缩 sparse-observation claim；
- 若 binary q 等效，则删除 continuous q；
- 若 staleness 无贡献，则删除 staleness。

### 6. 工程与时间风险仍高

当前没有 Stage2 结果，且需要先完成：

- official split/evaluator parity；
- weather loader；
- NetCDF export；
- strong baseline reproduction；
- mask invariance tests；
- decoder与训练稳定性检查。

因此 proposal READY 不等于 AAAI-27 当前 deadline 可行。文档对这一点的判断是诚实的。

## Result gates

未来只有同时满足以下条件，中心 claim 才成立：

1. ObsWorld 通过 official NDVI RMSE non-inferiority。
2. Holm-adjusted `D_Vanilla` 显著大于零。
3. Holm-adjusted `D_PredRNN-online` 显著大于零。
4. absolute post-reveal NDVI MAE 不劣于两个在线 baseline。
5. 收益不是只由最高-clear strata 驱动。
6. mask invariance、q identity、evaluator parity 和 baseline parity 全部通过。
7. no-staleness 或 binary q 若等效，按预注册规则删除相应组件。

如果任一核心 gate 失败，应收缩或放弃对应 claim，而不是增加大模型、下游任务或更多模块。

## Drift

**Drift warning：NONE。**

最终 proposal 仍围绕原始 predictive-state 问题，没有被 Stage1.5、天气、FM、下游任务或概率生成方向带偏。新增内容全部是对原有机制的定义、对照和验证闭环。

## Scores

| 维度 | 权重 | 分数 | 评语 |
|---|---:|---:|---|
| Problem Fidelity | 15% | 9.5 | 问题、边界、机制和证据完全对应 |
| Method Specificity | 25% | 9.4 | 状态、mask、梯度、更新、训练和推理 contract 均已明确 |
| Contribution Quality | 25% | 8.7 | 窄但清楚、可证伪；主要风险是贡献增量性而非设计混乱 |
| Frontier Leverage | 15% | 9.2 | generic filter、PredRNN-online、Direct 和 official anchors 构成合理前沿对照 |
| Feasibility | 10% | 9.1 | 方法本身轻量可实现；剩余风险主要是 benchmark 工程和训练稳定性 |
| Validation Focus | 5% | 9.5 | primary estimand、Holm、paired cluster bootstrap、NI gate 均已锁定 |
| Venue Readiness | 5% | 8.9 | proposal 已达到投稿级设计完整性，最终取决于 effect size 和结果一致性 |

加权总分：

\[
0.15(9.5)+0.25(9.4)+0.25(8.7)+0.15(9.2)
+0.10(9.1)+0.05(9.5)+0.05(8.9)
=9.16
\]

**Weighted overall：9.2 / 10**

**Final verdict：READY**

**Remaining design blockers：NONE。**

下一阶段应冻结 proposal，建立协议测试和 baseline parity，然后按既定 gate 跑最小一轮 one-seed 验证；不建议继续进行方法层面的扩张或第五种叙事重构。

</details>
