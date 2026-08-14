# Round 4 Review

<details>
<summary>Full raw reviewer response</summary>

## Round 4 raw review

### 结论

本轮已经解决上一轮四个主要方法 blocker：

- innovation 现在确实由同 mask、同 encoder/projector 下的真实观测与 prior prediction 之差定义；
- `Q`、`e_mask` 和显式 double-\(q\) 已删除；
- VanillaFilter 获得相同输入和额外 encoder forward；
- official open-loop 与 correction-specific evaluation 已分离；
- single-reveal、segment-normalized training 和 paired self-gain 已闭环。

我不再认为需要修改核心方法结构。但 proposal 里仍有两个必须在实现前写死的协议问题：未 reveal 时的 mask/staleness 防泄漏 contract，以及 primary estimand/cluster inference 的精确定义。

因此本轮仍是 **REVISE**，但已经属于“小范围协议修订”，不再需要新模块或重新设计 Stage2。

# 五项重点判断

## 1. Innovation 语义：PASS

当前定义：

\[
z_t^{obs}=P(E(x_t\odot m_t)),
\]

\[
z_t^{pred}=P(E(H(b_t^-)\odot m_t)),
\]

\[
r_t=z_t^{obs}-\operatorname{sg}(z_t^{pred})
\]

已经使 residual 的含义由计算图固定：

- 两侧使用同一个 `E/P`；
- 输入波段、归一化、token grid 和 visibility operator 一致；
- 比较的是 prior 在同一可见区域的预测与真实观测；
- 不再依赖自由 `Q` 是否学成 observation predictor。

即使 `E/P` 是学习的表示空间，这仍然是有效的 observation-aligned residual，而不是任意命名的 subtraction head。

`stopgrad(z_pred)` 也合理：它阻止 correction loss 通过 residual 支路直接修改 decoder、把残差人为压小；`F/H` 仍会通过 reveal 时刻的 prior loss 和后续 forecast loss正常训练。

这一项不再是 blocker。

## 2. 梯度路径：基本 PASS

对于 future reveal at \(r\)：

- \(\ell_r\) 评估的是 update 前 prior prediction；
- reveal-time `U` 只通过 \(t>r\) 的 `L_post` 得到梯度；
- `L_post` 同时可通过 skip connection 和后续 `F/H` 更新 reveal 前状态；
- 不存在 current-frame posterior reconstruction shortcut；
- 不存在通过 `z_pred` 支路修改当前 prior、伪造小 residual 的路径。

有一处表述需要修正：

> “`U` receives gradient only through `L_post`”

对整个共享 `U` 参数并不严格成立，因为十个 context observations 也调用同一个 `U`，这些 context update 会从所有后续预测损失获得梯度。

应改成：

> The reveal-time invocation of `U` receives supervision only through `L_post`; context invocations of the shared cell are trained through their downstream forecast consequences.

这是措辞问题，不需要改变算法。

## 3. VanillaFilter 公平性：PASS

VanillaFilter 当前获得：

\[
[b_t^-,z_t^{obs},\operatorname{sg}(z_t^{pred}),q_t,s_t^-]
\]

并且：

- 使用相同的额外 encoder forward；
- 具有相同 outer-\(q\) identity contract；
- 能隐式学习 \(z_{obs}-z_{pred}\)；
- update cell 的参数量和 FLOPs 控制在 5%；
- 使用相同 reveal schedule、decoder initialization 和训练目标。

因此如果 proposed 优于 Vanilla，可以较可信地归因于 explicit residual inductive bias，而不是信息、参数或计算量不平等。

最终实现应同时报告：

- update-cell Params/FLOPs；
- full-model Params/FLOPs；
- reveal 时 wall-time；
- 训练平均 overhead。

但这只是实施报告要求，不是方法 blocker。

## 4. Mask contract：仍有一个真实 blocker

proposal 定义了 `m_t` 和 `q_t`，但还没有形式化区分：

- observation-availability mask；
- target supervision/evaluation mask。

这在 future open-loop 中很重要。即使图像本身没有 reveal，训练 batch 中仍然必须加载 target cloud mask 来计算 \(\ell_t\)。如果代码不慎用该 mask 更新：

\[
s_t^+=(1-q_t)s_t^-,
\]

那么模型虽然没有看到 target RGBN，却通过 staleness 获得了未来云量信息。

proposal 的自然意图显然是不泄漏，但当前公式没有完全排除这一实现。

### 必须加入的精确 contract

定义 observation availability：

\[
a_t\in\{0,1\}.
\]

然后区分：

\[
m_t^{obs}=a_t\,m_t^{clear},
\qquad
q_t^{obs}=\operatorname{AvgPool}(m_t^{obs}),
\]

\[
m_t^{sup}=m_t^{clear}\odot m_t^{SCL/landcover}.
\]

其中：

- `m_obs/q_obs` 只能进入 `U` 和 staleness；
- `m_sup` 只能进入 loss/evaluation；
- context observation：\(a_t=1\)；
- future no-reveal：所有步 \(a_t=0\)；
- single-reveal：仅 \(t=r\) 时 \(a_t=1\)。

staleness 应写成：

\[
s_t^+=(1-a_tq_t^{clear})s_t^-.
\]

或者显式分支：

\[
s_t^+=
\begin{cases}
(1-q_t^{clear})s_t^-, & a_t=1,\\
s_t^-, & a_t=0.
\end{cases}
\]

同时增加单元测试：

> 在 RGBN、weather、context 完全相同的情况下，任意替换 unrevealed future target masks，不得改变 open-loop belief、staleness 或 prediction。

mask resize 也应固定为 nearest-neighbor，随后再 average-pool，避免对类别 mask 做双线性插值。

这是当前唯一仍涉及模型计算图的 blocker。

## 5. Evaluation statistics：设计方向正确，但 estimand 尚未完全锁定

“共同 GT-only validity mask + same-checkpoint paired gain + tile/location cluster bootstrap”是正确方向，但还需要写清三个统计细节。

### 5.1 预注册一个 primary correction endpoint

当前同时有：

- day25/day50；
- MAE/RMSE；
- absolute error/self-gain；
- horizon curve/AUC；
- 两个主要 baseline；
- 多个 clear strata。

如果没有 primary estimand，结果容易被质疑为从大量指标中选择最有利结论。

建议预注册一个主统计量，例如：

\[
G_{m,r,c,s}
=
\operatorname{AUC}
\left(
E^{no-reveal}_{m,r,c,s}
-
E^{reveal}_{m,r,c,s}
\right),
\]

再以 day25/day50 的平均 NDVI-MAE gain AUC 作为 primary self-gain endpoint。

同时预注册 proposed 与 baseline 的差：

\[
D_{b,c,s}=G_{\text{Ours},c,s}-G_{b,c,s},
\quad
b\in\{\text{Vanilla},\text{PredRNN-online}\}.
\]

Absolute post-reveal NDVI MAE 可以作为共同的 co-primary 或必要 supporting endpoint；其他 RGBN、RMSE、单 horizon 和 strata 作为 secondary。

### 5.2 明确 bootstrap 的独立单位

不能把 seed × cube × pixel 展平后当独立样本。

建议：

1. 在每个 `seed × cube × reveal` 内，先在共同有效像素与 horizon 上计算 cube-level metric；
2. 在相同 seed/cube 上形成 proposed-baseline paired difference；
3. 先对三个 seeds 求平均，保留 seed-wise point estimates；
4. 按 location/tile bootstrap，而不是按像素或 cube 随机 bootstrap；
5. 对 self-gain 比较，bootstrap 的对象应是：
   \[
   G_{\text{Ours}}-G_{\text{baseline}},
   \]
   而不是分别计算两条 CI 后观察是否重叠。

若希望对多个 co-primary comparison 做显著性判断，应预声明 Holm correction；clear strata 更适合作为效应稳定性分析，而不是大量独立显著性检验。

### 5.3 “open-loop statistically tied”需要预声明 non-inferiority 标准

“at strong baseline level”仍稍模糊。应在 Val 上锁定：

- Block A primary official metric；
- non-inferiority margin；
- OOD-t 只进行一次锁定评估。

这不是要求现在提供结果，而是要求结果出来前明确什么算“open-loop 没有因 correction 机制而显著退化”。

这是评估协议 blocker，不是需要增加实验的理由。

# 非 blocker 的风险判断

## 低 \(q\) residual 的尺度

即使删除显式 double-\(q\)，masked encoder 本身也可能让 residual norm 随可见面积变化，外层再乘 \(q\) 后可能对极低-clear patch 更新很弱。

但由于 ViT/LayerNorm 下残差尺度未必线性随 \(q\) 缩放，而且 Vanilla 采用完全相同 contract，这更适合作为 clear-strata 实证问题，而不是继续增加 masked normalization 模块。

当前不建议再改方法。若结果显示收益只出现在最高 clear stratum，已有 stop rule 足以处理。

## 创新幅度

方法仍然接近 learned Kalman/data-assimilation 思路，理论上不是全新 filter。但目前的贡献边界已经足够诚实：

- 不声称新 Bayesian filter；
- 强调 patchy EO visibility operator；
- 显式比较 aligned observed/predicted features；
- exact no-evidence identity；
- 用 Vanilla 和 PredRNN-online 直接证伪。

只要 proposed 在绝对误差和 paired self-gain 上稳定优于两个强控制，这种窄而清楚的贡献可以支撑 AAAI。无需为“看起来更大”再加入下游任务、大模型组合或第二套机制。

## 单数据集

GreenEarthNet 的 OOD-t/s/st，加上全 cube correction protocol，能够形成较丰富的分布外证据。第二数据集会增强泛化性，但在当前 7 页、单一 claim 和工程状态下不是方法成立的必要条件。

下游任务和“FM + ours”仍然不需要进入本稿。

# Drift

**Drift warning：NONE。**

Round 4 保持了原始 anchor：

- predictive belief 而非单纯 cuboid regression；
- 观测形成与状态更新的区分；
- shared transition；
- 新观测到来后的局部、安全 correction；
- 不扩张到因果物理状态、通用 foundation model 或下游应用合集。

# Scores

| 维度 | 权重 | 分数 | 评语 |
|---|---:|---:|---|
| Problem Fidelity | 15% | 9.3 | 问题、non-goals、成功条件和实验已高度一致 |
| Method Specificity | 25% | 8.8 | innovation 和训练路径具体；availability/supervision mask 仍需形式化分离 |
| Contribution Quality | 25% | 8.5 | 单一且可证伪，但属于强控制下的窄 data-assimilation 创新 |
| Frontier Leverage | 15% | 9.0 | 已正确面对 generic filter、PredRNN-online 和 Direct/Contextformer |
| Feasibility | 10% | 8.8 | 无额外大模块，额外计算有界；主要风险转为协议实现 |
| Validation Focus | 5% | 8.4 | paired design 很好，但 primary estimand 和层级 bootstrap 尚未写死 |
| Venue Readiness | 5% | 8.3 | 已接近可执行 AAAI proposal，剩余是防泄漏和统计预注册 |

加权总分：

\[
0.15(9.3)+0.25(8.8)+0.25(8.5)+0.15(9.0)
+0.10(8.8)+0.05(8.4)+0.05(8.3)
=8.785
\]

**Overall：8.8 / 10**

**Verdict：REVISE**

# Remaining actions

只需再完成三项，不建议继续扩张方法：

1. 引入显式 availability \(a_t\)，严格分离 `m_obs/q_obs` 与 `m_sup`，增加 unrevealed-mask invariance test。
2. 锁定 correction primary estimand、paired difference 和 tile-level bootstrap 单位。
3. 在 Val 上预声明 open-loop non-inferiority metric/margin，并修正“U only receives L_post gradient”的表述范围。

完成后，proposal 层面可以进入 READY；之后的决定因素应是实际结果是否跨过预声明门槛，而不是继续添加模块、下游任务或大模型组合。

</details>
