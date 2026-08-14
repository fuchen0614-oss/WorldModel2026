# TerraState AAAI-27 作者控制台

> 更新日期：2026-07-27  
> 英文唯一事实源：`paper/main.tex`  
> 中文同步稿：`MANUSCRIPT_ZH.md`  
> 写作区之外的模型、训练、评测、checkpoint、结果与记录均只读。

## 1. 当前论文状态

- 论文只介绍一个方法：**TerraState**。
- 标题、单模型定位与 \(q\rightarrow z_t\rightarrow T_\psi\rightarrow z_{t+h}\rightarrow O_\omega\) 主线保持不变。
- 按作者本轮明确要求，摘要已从结果无关版本更新为由最终 Q1–Q3 证据支持的版本；旧的“摘要仍待结果兑现”说明已失效。
- Q1、Q2、Q3 已接入正文。Q4 仅保留为探索性训练后扩展，正文不报告 Q4 结果，也不主张 composition consistency 或 non-degeneracy。
- 论文不是 benchmark；Q1–Q3 是对同一选定 TerraState 模型的预测能力、状态贡献和天气响应证据。
- 不声称 SOTA、因果识别、完整物理状态、极端天气特异增强或训练稳定性。

## 2. 权威结果来源与身份记录

本轮结果的权威本地来源是只读冻结记录：

`../WorldModel2026-planb/TERRASTATE_V2_EVIDENCE.md`

冻结记录给出的模型身份如下：

| 字段 | 冻结值 |
|---|---|
| checkpoint 路径（内部记录） | `runs/terrastate_v2/run1/checkpoint_boundary80.pt` |
| checkpoint step | 11,904 |
| 文件 SHA-256 | `644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd` |
| weight SHA-256 前缀 | `aba100c138119bc0…` |
| serialized architecture | `TerraStateV2`（论文统一称 TerraState） |
| 训练代码 commit | `52578ca` |
| evaluator commit | `4dce19a` |
| 选模候选 | 预注册候选集合；重复权重去重 |
| 选择规则 | 内部 Q1 qualifier 未通过时，按预声明 fallback 选择验证集 Q1 最优候选 |
| Q2/Q3/OOD-t 是否参与选择 | 否 |
| OOD-t 样本 | `ood-t_chopped`，1,904 minicubes |
| OOD-t manifest | `evaluations/greenearthnet_oodt_20260719_214234/greenearthnet_oodt_chopped_manifest.json` |
| OOD-t data manifest SHA 前缀 | `58c8d648…` |
| Q3 协议 | `extreme_audit_oodt_v1`，84 个匹配样本对 |
| Q3 protocol SHA 前缀 | `570a0c36…` |
| Q3 hot-dry / matched-normal manifest SHA 前缀 | `f8db1ccb…` / `84a09421…` |
| Q3 threshold SHA 前缀 | `1c20cd71…` |

当前工作区能读取上述冻结证据记录和 manifest，但冻结记录所指的 checkpoint 文件与三个原始结果 JSON 不在本地可见路径中。因此本轮没有重新计算 SHA，也没有从原始数组重新统计；正文数字逐项誊录自冻结证据记录。Figure 3 的 CSV 同样记录这一来源。若投稿前取得 Release 原始 JSON，应再次执行逐字段 provenance 对照；在此之前不得自行“修补”缺失字段。

## 3. 已核验的方法与训练事实

### 推理结构

\[
(b_{1:H},z_t)=q_{\theta,\rho}(\widetilde{\mathcal C}_t),\qquad
z_{t+h}=T_\psi(z_t,u_{t:t+h},g,h),\qquad
\widehat y_{t+h}=b_h+O_\omega(z_{t+h}).
\]

- \(\widetilde{\mathcal C}_t\) 包含云掩膜 EO 历史、过去气象和静态地理，不含未来 EO 或未来天气。
- \(b_h\) 与 \(z_t\) 来自同一次历史前向。
- 未来气象序列、静态地理与时距进入共享 \(T_\psi\)。
- \(O_\omega(z_{t+h})=r_h\) 是状态介导的预测贡献；正常推理为 \(b_h+r_h\)。
- 状态贡献切除令 \(r_h=0\)，精确恢复 \(b_h\)。
- 正文只主张状态分支承载可测预测增量，不主张全部预测能力都经过状态。

### 唯一训练目标

\[
\mathcal L
=\mathcal L_{\mathrm{GT}}
+0.5\mathcal L_{\mathrm{KD}}
+\lambda_s\mathcal L_{\mathrm{future\text{-}state}}.
\]

- 没有非零 composition、output consistency、VICReg、driver distillation 或其他 refinement objective。
- Future-state target 由冻结的初始化编码器/投影器从真实未来 EO 产生，只用于 \(h=20\) 的训练锚定。
- 冻结预测教师只提供 KD；教师与 target encoder 均不进入推理。
- Q2/Q3/Q4 全是训练后干预，不接收梯度。

### 训练配置

- 40 epochs，14,880 optimizer updates。
- AdamW，\(\beta=(0.9,0.999)\)，weight decay 0，gradient clipping 1.0。
- 8 GPUs × 每卡 batch 8，global batch 64，无梯度累积。
- 非 \(q\) 分支基础学习率 \(3\times10^{-5}\)。
- \(q\) 参数组学习率 \(9.9\times10^{-7}\)，只在最后 20% 更新。
- 前 300 steps 线性 warmup，随后 cosine decay。
- 前 80% 冻结 \(q\)；最后 20% 只解冻其最后一个 Transformer block。
- \(\lambda_s\)：0–20% 从 0 线性升到 0.02；20–80% 为 0.02；80–100% 为 0.01。

### 状态与参数量

- 每个 \(128\times128\) minicube 产生 \(32^2=1024\) 个 patch state。
- 单样本状态形状为 `[1024,256]`；运行时为 `[1024B,256]`。
- 推理模型共有 7,180,896 个唯一 `nn.Parameter` 标量。
- 前 80% 可训练参数为 1,120,336；最后 20% 为 1,910,096。
- 参数量计入推理模型中的冻结 \(q\)，排除 buffers、冻结 KD teacher、离线 future-target encoder/projector 与缓存 tensor。

## 4. Q1–Q4 verdict 与允许措辞

| 问题 | 结果 | Verdict | 正文允许的最强措辞 | 禁止措辞 |
|---|---|---|---|---|
| Q1 OOD-t | \(R^2=0.56935\)，RMSE \(=0.15059\) | useful skill | preserves useful temporal-shift forecasting skill | SOTA；优于匹配骨干 |
| Q1 matched backbone | \(R^2=0.58252\)，RMSE \(=0.14342\) | TerraState 较低 | matched backbone remains more accurate | non-inferior；accuracy gain |
| Q2 Val | state ablation \(\Delta R^2=0.01121\)，CI \([0.00643,0.02590]\) | PASS / LOAD-BEARING | state-mediated path is load-bearing on validation | future-state loss proves Q2 |
| Q2 OOD-t | state ablation \(\Delta R^2=0.01997\)，CI \([0.01422,0.03018]\) | PASS / LOAD-BEARING | remains load-bearing under temporal shift | effect is significantly stronger than Val |
| Q2 \(T\to I\) | Val \(0.01191\)，OOD-t \(0.02169\)，CI 均高于 0 | supporting | supporting intervention has the same direction | 用它替代主 state ablation |
| Q3 actual vs matched control | \(\Delta\)Loss \(=0.00257\)，CI \([0.00112,0.00399]\) | PASS | actual weather predicts the endpoint more faithfully | causal/counterfactual correctness |
| Q3 actual vs mean | \(\Delta\)Loss \(=0.01126\)，CI \([0.00547,0.01708]\) | PASS | actual weather outperforms normalized-mean control | generic domain threshold |
| hot-dry interaction | \(0.00044\)，CI \([-0.00216,0.00320]\) | FAIL | no evidence of extreme-specific enhancement | hot-dry enhancement succeeds |
| Q4 | 未接入 | exploratory only | optional post-training analysis | composition-consistent；non-degenerate |

内部的 0.502、0.156 与 0.005 仅是项目内冻结规则，不能写成领域公认阈值。Q3 子集 \(R^2=0.6254\) 只属于 84 对样本，不能代替完整 OOD-t 的 \(R^2=0.56935\)。

## 5. Claim–Evidence–Artifact 映射

| ID | 论文主张 | 证据 | 位置 | 状态 |
|---|---|---|---|---|
| C1 | TerraState 保留有效时间偏移预测能力 | OOD-t Q1；同时披露 matched backbone 更准确 | 摘要、引言、表 1、Q1、结论 | supported with limitation |
| C2 | 状态介导路径在验证集与 OOD-t 上承载预测 | state ablation 的两个正 \(\Delta R^2\) 与不跨零 CI | 摘要、贡献、表 2、Q2、图 3a、结论 | supported |
| C3 | 真实未来天气比匹配/均值天气更忠实地预测终点 | 两个正 \(\Delta\)Loss 与 geo-cluster CI | 摘要、贡献、表 3、Q3、图 3b–c、结论 | supported |
| C4 | 极端热旱条件有额外增强 | hot-dry interaction CI 跨零 | Results、Limitations | rejected; explicitly not claimed |
| C5 | composition consistency / non-degeneracy | 无最终主文证据 | Method exploratory note、Limitations | not claimed |
| C6 | Q1–Q3 来自同一选定模型且 OOD-t 未参与选择 | 冻结 evidence provenance 与 selection record | Protocol、表注 | recorded; raw Release recheck pending |
| C7 | 本文不是 benchmark、因果或完整物理模拟 | 范围措辞审计 | Intro、Method、Limitations | satisfied |

更细的摘要—引言—结论对照见 `RESULTS_CLAIM_EVIDENCE_AUDIT.md`。

## 6. 图表职责

- **Figure 1**：方法结构与训练期监督。不能承担结果结论。
- **Figure 2**：同一模型上的干预设计。只说明查询，不显示 PASS、winner 或数值。
- **Figure 3**：真实行为证据。
  - (a) Q2 state ablation 与 \(T\to I\) 的效应量和 CI；
  - (b) Q3 两个天气对照的损失增量和 CI；
  - (c) 同一 84 对 Q3 子集上的 actual/matched/mean \(R^2\) 与 RMSE。
- Figure 3 数据源为 `paper/figures/data/terrastate_behavioral_evidence.csv`；
  全宽审计版由 `paper/figures/generate_terrastate_behavioral_evidence.py`
  生成，正文使用同一数据的单栏可编辑排版
  `paper/figures/terrastate_behavioral_evidence_column.tex`，以避免结论被
  双栏浮动体推到参考文献页；未产生或伪造逐样本数组。
- **Table 1**：Q1；公开 Reported 与本地 Local 分面，不跨协议排名。
- **Table 2**：Q2。
- **Table 3**：Q3。Q4 不再占用正文表格。

## 7. 结果接入后的论文边界

1. 标题保持不变。
2. 摘要已按作者本轮指令用 Q1–Q3 结果校准；没有加入 Q4、SOTA 或 hot-dry 正面主张。
3. 结论只总结 Q1 useful skill、Q2 load-bearing 与 Q3 response fidelity。
4. 一次训练、一个时间偏移轨道、匹配骨干更准确、hot-dry null 与无跨数据集验证均明确进入 Limitations。
5. Q2 的 state ablation 是主证据；\(T\to I\) 只作辅证。
6. Q3 证明条件预测保真度，不证明因果或真实物理响应。

## 8. 投稿前仍需处理

- 若实验 Release 到位，对 checkpoint、serialized config、selection record、manifest、scorer、mask、aggregation、Q3 donor/normalizer/threshold 和三个结果 JSON 做一次逐字段 provenance 复核。
- 若没有 Release 原始 JSON，保留当前“来自冻结证据记录”的作者说明，不能声称重新计算。
- 补充训练种子或其他数据集只能作为新实验，当前正文不依赖它们。
- Q4 只有产生真实、强且通过身份审计的证据后才可进入补充材料；不得因此改写核心结论。
- 投稿前复查 2026 concurrent preprint 的正式出版元数据。
- 最终编译后确认正文页数、图表位置、字体嵌入、匿名性、引用和无占位符。
