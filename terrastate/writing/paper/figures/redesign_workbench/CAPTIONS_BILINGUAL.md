# TerraState Figure Captions and Chinese Reading Notes — Formal Phase 2

> These captions match the approved figures now referenced by
> `paper/main.tex`. The Chinese text is a logic-preserving reading aid.

## Figure 1 — TerraState Method Overview

### English caption

**TerraState inference and training supervision.** Cloud-masked EO history,
retained past meteorology, and static geography enter the history-only context
operator \(q_\theta\), which emits a context-only prior \(b_h\) and, through
\(P_\rho\), a spatial predictive state \(z_t\). Full24 future weather, static
geography, and horizon \(h\) condition the shared transition \(T_\psi\);
\(O_\omega\) decodes \(z_{t+h}\) into a contribution \(r_h\) that is added
explicitly to \(b_h\). Solid arrows denote inference. Orange dashed branches are
training only: ground-truth forecasting, distillation from a frozen
full-weather teacher, and an \(h=20\) future-state anchor produced from observed
future EO by a frozen target encoder. Neither teacher nor future observation is
used at inference.

### 中文解释

**TerraState 的推理闭环与训练监督。** 云掩膜 EO 历史、保留的过去气象和静态地理进入
history-only 上下文算子 \(q_\theta\)。该算子一方面产生不使用未来天气的 context-only
先验 \(b_h\)，另一方面经 \(P_\rho\) 形成空间预测状态 \(z_t\)。Full24 未来天气、静态
地理与预测时距 \(h\) 只条件化共享转移 \(T_\psi\)；状态头 \(O_\omega\) 将
\(z_{t+h}\) 解码成状态贡献 \(r_h\)，再与 \(b_h\) 显式相加形成预测。实线是推理路径；
虚线只在训练期存在，分别表示真实目标监督、冻结 full-weather teacher 蒸馏，以及由
真实未来 EO 的冻结目标编码器提供的 \(h=20\) 状态锚定。Teacher 和未来观测都不参与
推理。

## Figure 2 — Same-Checkpoint Operational Verification

### English caption

**Same-checkpoint operational verification.** The selected TerraState
checkpoint is evaluated without retraining; the Q1 matched backbone is a
separately trained, frozen reference under the same local protocol. Q1 reports
their paired forecast comparison. Q2 compares the
full model with the exact closure cut \(r_h=0\) and the supporting
\(T\!\rightarrow I\) intervention. Q3 changes only the future-weather input to
\(T_\psi\), comparing actual, normalized-mean, and matched-donor forcing while
tracking state, output, and score changes; the pre-registered hot-dry analysis
compares intervention effects with matched-normal conditions rather than
supplying an additional model input. Q4 is an optional post-training
direct/composed query guarded by endpoint accuracy and non-collapse checks.
The diagram specifies queries, not outcomes or a new benchmark.

### 中文解释

**同一检查点的可操作验证。** 选定的 TerraState 检查点不经重训练接受全部检验；Q1
中的匹配骨干是同一本地协议下独立训练并冻结的参考，而不是该检查点的一个输出。Q1
报告二者的严格配对预测比较。Q2 比较完整模型、精确闭环
切除 \(r_h=0\) 和作为辅证的 \(T\!\rightarrow I\)。Q3 只替换 \(T_\psi\) 的未来
天气输入，比较 actual、归一化均值和匹配供体，同时追踪状态、输出和得分变化。预注册
hot-dry 分析比较其干预效应与 matched-normal 的差异，它不是新增模型输入或第四个天气
分支。Q4 仅为训练后的可选 direct/composed 查询，并受端点精度与防坍塌条件约束。
整张图描述的是查询逻辑，不是已经产生的结果，也不是新 benchmark。

## Compact fallback caption suffix

If the compact Figure 1 is used, append:

> The narrow bottom strip is a space-constrained index of same-checkpoint
> verification; it does not depict an additional model component.

中文含义：底部窄条只是在页面空间受限时索引同一检查点的验证问题，不是额外模型组件，
也不表示 Q1–Q4 已经通过。
