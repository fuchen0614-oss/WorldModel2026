# Round 3 Review

<details>
<summary>Full raw reviewer response</summary>

## Round 3 严格评审

### 总评

这一轮已经从“包含很多可能方向的系统草案”，收敛成了一个可以被明确证伪的核心假设：

> 对稀疏、云遮挡的遥感时间序列，显式使用可见度与陈旧度控制的观测残差更新，是否优于无更新、一般 learned filter 和在线 PredRNN？

这比前两轮明显更像一篇完整论文。框架主线没有漂移，训练、基线和评估协议也具体了许多。

但我仍然给出 **REVISE，而不是 READY**。最关键的原因是：当前所谓的 `innovation` 在数学上还没有被约束为“预测观测与真实观测之间的残差”；同时，部分可见观测被 `q` 重复衰减，可能直接削弱最核心的云遮挡场景。

## 已经解决的问题

这一轮以下修改是实质性的，而非文字润色：

- 将贡献压缩到一个核心：cloud/age-gated innovation correction。
- `Stage1.5` 和天气错误年份测试退回附录，不再抢主叙事。
- 增加参数匹配的 `VanillaFilter` 和同 reveal schedule 的 `PredRNN-online`。
- 明确 `H` 是新初始化且需联合训练，修复了上一轮“冻结未训练 decoder”的问题。
- 给出了 `q`、age、prior/posterior、context/future 的完整时序定义。
- correction reveal 不再选择容易样本，而是覆盖全 cube、固定 day25/day50、报告 clear-fraction strata。
- posterior 不使用当前帧重建损失，降低“把当前输入复制到当前输出”的风险。
- Direct baseline 的天气轨迹编码不再过弱。
- 删除 train-length extrapolation，避免引入无法支撑的第二条故事。

这些改变使方案从上一轮约 7 分提升到接近 8 分。

# 仍然存在的关键问题

## 1. `Q(b^-)` 没有被约束成“预测观测”，因此 innovation 语义不成立

当前定义为：

\[
r_t=e_t-Q(\mathrm{LN}(b_t^-)).
\]

但 `Q` 完全由远期预测损失端到端训练，没有任何约束要求：

\[
Q(b_t^-)\approx \text{该时刻模型预期看到的观测特征}.
\]

因此，`Q`、`R` 和 gate 可以共同学成任意重参数化。形式上发生了减法，不等于模型真的计算了“预测—观测创新量”。

这会带来一个直接的审稿问题：

> 为什么这是 innovation-aware filtering，而不是一个带减法结构的通用 gated MLP？

而且 `VanillaFilter([b,e,q,a])` 本身具有足够表达能力，它完全可以隐式学习同样的减法。若没有语义约束，你们的贡献只能被描述为优化上的 inductive bias，而不能强称为显式预测误差校正。

### 推荐的最小修复

优先考虑以下两种方案之一，不需要同时采用。

方案 A，更干净：

\[
z_t^{obs}=P(E(x_t\odot m_t)),
\]

\[
z_t^{pred}=P(E(H(b_t^-)\odot m_t)),
\]

\[
r_t=z_t^{obs}-\operatorname{sg}(z_t^{pred}).
\]

即让真实观测和 prior 预测经过同一个 encoder、同一个可见掩码，再直接相减。这样 innovation 的语义是确定的，同时可以删除独立的 `Q`。

它只在 reveal 时多一次 encoder 前向，通常比增加一套复杂模块更容易解释。相同掩码还能部分抵消 zero-filled encoder 带来的偏差。

方案 B，计算更轻：

保留 `Q`，但增加仅作用于 prior observation head 的对齐：

\[
\mathcal L_Q
=
\frac{\sum q_t
\left\|
Q(b_t^-)-\operatorname{sg}(z_t)
\right\|_1}
{\sum q_t+\epsilon}.
\]

它只约束 `Q` 预测观测特征，不对整个 belief 做 latent matching，也不是 posterior reconstruction，因此不会重新引入前几轮所担心的“整状态被单帧绑架”。

在二者之间，我更推荐方案 A：语义更直接，还能删掉 `Q`，论文解释也更短。

## 2. 当前 `q` 对观测产生了双重衰减，且 `e_mask` 会污染部分可见观测

现在是：

\[
e=qz+(1-q)e_{mask},
\]

随后：

\[
b^+=b^-+q\cdot g\cdot R(r).
\]

这意味着观测相关信息可能被近似衰减为 \(q^2\)。例如 `q=0.1` 时：

- `e` 已经有 90% 是 `e_mask`；
- 最终 correction 又整体乘以 0.1；
- residual 中还包含 `e_mask-Q(b)`，它不再是纯粹的有效观测残差。

这与“充分利用稀疏但真实的可见像素”这一中心动机相冲突。

### 建议

直接删除 `e_mask`：

\[
z=P(E(x\odot m)),
\]

\[
b^+=b^-+q\cdot g([b^-,r,q,a])\cdot R(r).
\]

因为：

- `q=0` 时，外部乘法已经保证严格 identity；
- `q` 本身已经作为输入告诉 update 模块观测可靠度；
- 不再需要额外的 missing token；
- 避免了对部分观测的两次门控。

若采用上面的同掩码预测残差方案，真实图像和预测图像都经过 `m`，会进一步减轻 frozen nonlinear encoder 对零填充输入的系统偏差。

这是本轮第二个核心 blocker。若不修复，最重要的低 clear-fraction strata 可能恰好是方法最难受益的部分。

## 3. 截断后的 correction 评估不能直接称为“官方 GreenEarthNet metrics”

GreenEarthNet 官方评估的有效像素筛选、观测数要求、时间方差条件、climatology comparison 等，是围绕完整 target window 定义的。

在 day50 reveal 后严格只评估 10 个 future steps 时：

- 有效像素资格会变化；
- `n_obs ≥ 10` 等条件处于临界边界；
- NSE、R²、outperformance 等指标的统计意义和完整 20-step 官方评估不同；
- RMSE25 等指标也未必能直接按原协议截断。

因此不宜把 correction 表称为“post-reveal official metrics”。

### 更稳妥的协议

- Block A：完整 20-step open-loop，严格使用 GreenEarthNet 官方指标。
- Block B：定义 correction-specific paired metrics：
  - post-reveal NDVI MAE / RMSE；
  - RGBN MAE；
  - 相对于同一 checkpoint、同一 cube、无 reveal 情况的 paired gain；
  - horizon-wise gain curve；
  - post-reveal error 或 gain 的 AUC。
- 所有方法使用完全相同的有效像素集合。
- 有效像素集合只能依赖真实 mask 和预注册规则，不能依赖方法输出。
- bootstrap 继续以 tile/location 为 cluster。

这不会削弱论文，反而会让 correction claim 更容易解释。

## 4. reveal 位置不同会产生不等量的 update 梯度

虽然所有 20 个预测 horizon 等权，但 reveal 越早，`U` 能通过越多后续预测得到梯度；越晚则监督链更短。

因此“horizon loss 等权”不等于“不同 correction event 等权”。

如果保留随机 reveal，需要至少对每段 reveal 后的损失按剩余步数归一化。例如：

\[
\mathcal L_{\text{post}}
=
\frac{1}{T-r}
\sum_{t=r+1}^{T}\ell_t.
\]

两次 reveal 还会造成第一更新和第二更新的贡献混合，增加解释难度。

### 推荐简化

主训练只保留：

- 50% no reveal；
- 50% one reveal，均匀采样 step 2–15。

day25 和 day50 分别作为两个独立评估设置即可。多次 assimilation 可以作为附录实验，而不必进入主训练和核心论证。

这样既减少训练分支，也让一次 correction 的因果归因更清楚。

## 5. PredRNN-online 的比较必须同时报告绝对精度和自身 correction gain

若 ObsWorld 与 PredRNN 的 open-loop 基础精度不同，仅比较 reveal 后绝对误差，无法单独说明谁的 assimilation mechanism 更好。

Block B 应同时报告：

\[
\Delta_{\text{method}}
=
\mathrm{Error}_{\text{no reveal}}
-
\mathrm{Error}_{\text{reveal}}.
\]

需要同时回答：

1. reveal 后谁的绝对预测最好？
2. 相对于自身无 reveal 基线，谁从观测中获得的提升最大？

对于 “no-update ObsWorld”，最好明确它是同一个 proposed checkpoint 在推理时禁用 reveal，而不是单独训练的另一个模型。这样 paired gain 才最干净。

## 6. age 的名称和解释需要更精确

当前：

\[
a_t^+=(1-q_t)a_t^-.
\]

它并不是严格意义上的“距上一次可信观测经过了多少时间”。例如 10% 可见会将整个 patch 的 age 缩短 10%，本质上是一个累积的软可信度状态。

建议称为：

> evidence-weighted staleness / visibility-weighted staleness

而不要直接称为 time-since-last-observation。

作为 patch-level approximation 是可以接受的，但论文中应明确它不是像素级真实观测年龄。

# 贡献是否足够锐利

目前的研究假设已经足够锐利，而且可被明确证伪：

- 若 proposed update 不优于 VanillaFilter，说明显式结构没有必要；
- 若不优于 PredRNN-online，说明更强序列模型已能实现同等 assimilation；
- 若收益只存在于高可见率样本，不存在于稀疏/cloud strata，说明核心动机不成立；
- 若 correction 改善但 open-loop 明显下降，说明统一模型的价值不足。

但要达到 AAAI 程度，必须先解决 `Q` 的语义不可识别问题。否则贡献容易被审稿人归类为：

> standard recurrent state-space model with an extra gated residual update.

修复后，更合适的贡献表述是：

> an observation-aligned residual correction rule for sparse EO predictive states

而不是泛称一个新的 world model 或通用 Bayesian filter。

# 建议进一步删减的复杂度

建议从正文核心中删除或降级：

- 删除 `e_mask`。
- 主训练只保留 single reveal。
- Stage1.5 初始化只在确有收益时放附录一行。
- weather sanity 最多保留 `true weather / no weather`；wrong-year 可以在空间足够时再做。
- Block C 核心只保留：
  - no innovation；
  - no staleness；
  - continuous q → binary q。
- 不再增加下游任务、基础大模型组合、更多数据集或更多 correction 模块。

目前最缺的不是实验数量，而是让一个核心机制在数学和评估协议上完全闭环。

# 漂移检查

**Drift warning：NONE。**

当前 proposal 与 anchor 保持一致：

- 仍聚焦稀疏、云遮挡、间歇观测条件下的 EO predictive state；
- 没有重新扩张到通用物理世界模型；
- 没有把 Stage1.5、天气因果性或 foundation model 变成第二主贡献；
- correction 实验能直接支撑 observation-formation 与 latent-state separation 的应用动机。

需要注意的只是：正文不应把 soft patch visibility correction 夸大为完整的 latent physical process identification。

# 评分

| 维度 | 权重 | 评分 | 评语 |
|---|---:|---:|---|
| Problem Fidelity | 15% | 9.0 | 问题、边界与成功标准已经高度一致 |
| Method Specificity | 25% | 8.0 | 时序和训练足够具体，但 innovation 与 partial evidence 仍有定义缺口 |
| Contribution Quality | 25% | 7.0 | 单一贡献清楚，但当前 Q 未被语义约束，仍接近通用 filter 重参数化 |
| Frontier Leverage | 15% | 8.5 | 已正确引入 learned filter、online recurrent assimilation 等关键对照 |
| Feasibility | 10% | 7.5 | 核心可实现；官方评估、数据 mask 和 correction protocol 仍需工程落地 |
| Validation Focus | 5% | 8.5 | 全 cube、固定 reveal、strata、cluster bootstrap 都很好 |
| Venue Readiness | 5% | 6.5 | 已具 AAAI 论文骨架，但核心机制语义和 correction metric 尚未闭环 |

加权总分：

\[
0.15(9.0)+0.25(8.0)+0.25(7.0)+0.15(8.5)
+0.10(7.5)+0.05(8.5)+0.05(6.5)
=7.875
\]

**总分：7.9 / 10**

**结论：REVISE**

## 下一轮只需要优先解决四件事

1. 让 innovation 成为真正的 observation-aligned residual：同掩码预测特征相减，或给 `Q` 增加 prior observation alignment。
2. 删除 `e_mask` 和双重 `q` 衰减。
3. 将 correction evaluation 与官方 open-loop evaluation 分开定义。
4. 简化为 single-reveal 主训练，并对 reveal 后损失按剩余 horizon 归一化。

完成这四点后，方法设计本身可接近 8.8–9.0 分；是否最终达到 AAAI 水平，就主要取决于 GreenEarthNet OOD open-loop、all-cube correction 和强基线结果。

</details>
