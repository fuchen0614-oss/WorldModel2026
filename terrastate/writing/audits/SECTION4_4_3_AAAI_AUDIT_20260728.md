# TerraState AAAI-27 Section 4.3 修改前独立审计

**审计日期：** 2026-07-28  
**审计对象：** Section 4.3 “Load-Bearing Predictive State”、Table 2 及其英文/中文镜像  
**审计性质：** 只读的 AAAI 写作、证据层级、统计口径与格式审计  
**权威正文：** `paper/main.tex`  
**事实优先级：** 作者最新确认事实与冻结 Q2 JSON > 当前实现审计与最终证据审计 >
当前正文 > 中文主镜像 > 简版 Markdown 镜像 > 历史 ledger/audit  

## 1. 最终结论

# READY_FOR_4_3_REVISION

当前 4.3 没有事实、统计或证据边界错误。State removal 已被明确设为 Q2 的
primary intervention，且 load-bearing 结论确实由两个 split 上的逐 minicube
paired effect 及其排除零的 paired-bootstrap 95% CI 支持。\(T_\psi\!\to I\)
也被正确限制为 supporting diagnostic of transition involvement，并明确披露
readout 可能接收训练分布外状态这一解释边界。

本节已经接近成熟的 AAAI 机制结果段。修改重点不是增加实验或重新解释数值，而是：

1. 将 load-bearing 结论移到首句；
2. 让 primary paired evidence 先于 dataset-level official effect size；
3. 可选但建议补充 Validation/OOD-t 的 paired \(n\)，提高 Table 2 的统计
   自包含性；
4. 将两个简版 Markdown 镜像同步到最终 4.3 的结构。

### 问题计数

| 等级 | 数量 | 结论 |
|---|---:|---|
| Critical | **0** | 无事实、数值、统计或证据边界错误 |
| Major | **0** | 无需新增证据或重构章节 |
| Minor | **4** | 结论位置、证据顺序、paired \(n\) 和简版镜像同步 |

当前平均质量评分：**4.3 / 5.0**。

---

## 2. 并行读取与局部 SHA 确认

### 2.1 哈希提取边界

- **Section 4.3 local block：** 从
  `\subsection{Load-Bearing Predictive State}` 开始，至
  `\subsection{Weather-Forcing Response}` 之前，包含 Table 2。
- **Table 2 local block：** 从 `\begin{table*}[t]` 开始，至包含
  `\label{tab:q2}` 的 `\end{table*}` 结束。
- **4.3 prose-only block：** 上述 Section 4.3 local block 去除完整 Table 2
  环境后的文本。

### 2.2 审计开始与成稿前哈希

| 对象 | 开始时 SHA-256 | 成稿前 SHA-256 | 判断 |
|---|---|---|---|
| `paper/main.tex` 全文件 | `f6859f34c0585715bb59d6ebf4bc8fa96640874b3f030c0a931252c9cf4f6aa3` | `f6859f34c0585715bb59d6ebf4bc8fa96640874b3f030c0a931252c9cf4f6aa3` | 未变 |
| Section 4.3（含 Table 2） | `83213677f51c2ea4dab3f0ef0470fafbabf9e9f9e2077b095c6b0ed74abcb229` | `83213677f51c2ea4dab3f0ef0470fafbabf9e9f9e2077b095c6b0ed74abcb229` | 未变 |
| Section 4.3 prose-only | `d9ebdd9fb4e38333a889cd2dfe141b197a729271f54886487253521286394aa5` | `d9ebdd9fb4e38333a889cd2dfe141b197a729271f54886487253521286394aa5` | 未变 |
| Table 2 完整环境 | `6d6299d3c2c6419717696d1b713eaa0931114cac64118b35c2d72733a08c05ed` | `6d6299d3c2c6419717696d1b713eaa0931114cac64118b35c2d72733a08c05ed` | 未变 |
| Table 2 `tabular` | `a372f2ae9fa3ce9d80298fee89453e1565e0eeabc269e671537baad42ebb069b` | 同左 | 未变 |
| Table 2 caption 正文 | `2690aad11f7a8000b79d14fefacbc130a571f92230eac83673952973a93d9d1b` | 同左 | 未变 |

结论：审计期间没有发生 4.3 或 Table 2 并行修改，无需切换审计基线。即使 4.2
窗口并行工作，本报告也没有将正常的 4.2 修改视为阻塞。

---

## 3. 读取范围与权威事实

本轮核对了：

1. `paper/main.tex` 当前 4.1--4.4、Table 2，以及与 Q2 对应的 Section 3.4；
2. `MANUSCRIPT_ZH_FULL.md` 当前 4.3；
3. `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md` 当前 4.3；
4. `SECTION4_AAAI_PRE_REVISION_AUDIT_20260728.md`；
5. `SECTION4_4_1_FINAL_AUDIT_20260728.md`；
6. `SECTION4_4_1_REVISION_LOG_20260728.md`；
7. `SECTION4_FINAL_AAAI_AUDIT_20260728.md`；
8. `EXPERIMENTS_RESULTS_AAAI_WRITING_AUDIT.md`；
9. `METHOD_3_4_AAAI_AUDIT_20260728.md`；
10. `METHOD_3_4_FINAL_AUDIT_20260728.md`；
11. `evidence_workspace/results_ledger.json`；
12. `evidence_workspace/FINAL_EVIDENCE_AUDIT_20260728.md`；
13. 两个冻结 Q2 release JSON；
14. 六篇本地 AAAI 写作锚点；
15. `vendor/AuthorKit27/AuthorKit27/AnonymousSubmission2027.tex`；
16. 当前 `paper/main.log`、`paper/main.aux` 和 `paper/main.pdf`。

作者最新确认的训练身份优先于历史 ledger：

- Q1--Q3 使用同一个最终 TerraState 模型；
- 模型完成 40 epochs / 14,880 updates 的完整训练协议；
- Q2 在该最终模型上进行冻结 forward intervention，不重新训练；
- 11,904/boundary80 只属于待同步的历史记录，本轮不恢复，也不据此否定当前
  4.3。

---

## 4. AAAI 机制结果写作锚点

以下锚点只用于提炼段落职责和论证顺序，不复制具体措辞，也不建议机械加入
TerraState 的参考文献。

| 锚点 | 正式来源 | 机制/消融段的组织方式 | 对 4.3 可借鉴之处 | 不应照搬 |
|---|---|---|---|---|
| *SparseWorld: A Flexible, Adaptive, and Efficient 4D Occupancy World Model Powered by Sparse and Dynamic Queries* | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/37347) | Main Results 与 Ablation Studies 分开；每个组件先报告移除后的关键下降，再解释有限含义；同时承认 IoU 没有显著优势 | 只选与机制结论直接相关的下降，不逐格复述；负面或边界信息可见 | 不能借用其模块有效性归因、占据预测或规划结论 |
| *ReconVLA: Reconstructive Vision-Language-Action Model as Effective Robot Perceiver* | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/38921) | 先说明消融改变哪些组件，再选择 pretraining、gaze region 等主要效应解释；同时报告整图重建的局限 | “操作 → 核心变化 → 解释 → 局限”的短链路；不朗读整表 | 不能把其 grounding、attention 或机器人成功率解释迁移到 predictive state |
| *WorldAgen: Unified State-Action Prediction with Test-Time World Model Training* | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/38925) | 将 world-modeling removal、LoRA sensitivity 与 data-volume analysis 分成不同证据块；明确收益递减和轻微回落 | 直接移除型证据与敏感性/支持性诊断分层，适合对应 state removal 与 \(T\to I\) | 不能借用 policy learning、test-time adaptation 或 world-modeling 因果归因 |
| *Driving in the Occupancy World: Vision-Centric 4D Occupancy Forecasting and Planning via World Models for Autonomous Driving* | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/33010) | Forecasting、controllability、planning 和 ablation 分开；正文选择少量指标解释任务含义 | 一项机制证据只回答一个问题；表给 exact aggregate，正文给有限意义 | 不能借用动作可控性、规划安全或 occupancy world 的强主张 |
| *Causal Structure Learning for Dynamical Systems with Theoretical Score Analysis* | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/40999) | 先给 sanity check，再按 NSHD/F1/AUPRC 的不同职责解释主结果，最后单列 integration-order effect | 不同 estimand 分句解释；supporting analysis 不抢主结果层级 | TerraState 不应借用 causal discovery、结构恢复或理论保证语言 |
| *Learning Hybrid Dynamics Models with Simulator-Informed Latent States* | [AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/29075) | 预测误差、轨迹案例和 latent-component analysis 相互补充；正文从性能变化推到有限的 latent-state 解释，并讨论 baseline error accumulation | 将“可见性能变化”与“内部状态含义”连接，但保留观察边界 | TerraState 不具有 simulator-informed physical latent state，也不能照搬 observer essentiality 或物理性解释 |

### 4.1 共同规律

1. 机制结果段应结论先行，而不是以 “Q2 asks...” 或 “As shown in Table...”
   开场。
2. 主干预与支持性诊断必须分层；支持性诊断不能与定义性证据共享同一结论地位。
3. 两个 split 可以平行报告，无需拆成两个重复段落。
4. 正文只保留支撑结论的效应、区间和最少必要样本量；完整数值留在表格。
5. 性能下降只能推出协议允许的有限机制含义，不能自动推出必要性、因果性或完整
   状态语义。
6. 一个成熟机制结果单元通常为 4--7 句，采用
   “结论 → primary evidence → aggregate scale → 解释 → supporting boundary”。

---

## 5. 当前 4.3 反向提纲

| 位置 | 当前唯一职责 | 当前表现 | 判断 |
|---|---|---|---|
| 开场句 1 | 重新提出 Q2：state-mediated contribution 是否改善预测 | 准确，但没有直接给出结果 | **MINOR：结论未前置** |
| 开场句 2 | 定义 state removal 为 primary、\(T\to I\) 为 supporting | 层级清楚、术语自然 | **PASS** |
| Table 2 | 给两个 split 的 full/intervention、official 与 paired exact aggregate | 统计量分列、精度一致 | **PASS** |
| 结果句 1 | 报告 state removal 的 dataset-level official drop | 数字正确，但在 paired defining evidence 之前出现 | **MINOR：证据顺序可调** |
| 结果句 2 | 报告两个 split 的 paired mean 与 CI | 数字和区间对应正确，但 split 名依赖前句顺序；未给 paired \(n\) | **PASS WITH MINOR** |
| 结果句 3 | 用两个 CI 排除零支持 load-bearing | 统计语言准确，没有使用含糊的 “significant” | **PASS** |
| 结果句 4 | 限定 identity transition 的 supporting 地位与 OOD-readout 风险 | 边界充分且紧凑 | **PASS** |

当前 prose-only 约 **116 个英文词**。它不是过长，而是证据层级可以通过轻度重排
变得更清楚。

### 5.1 对指定问题的逐项回答

| 问题 | 审计结论 |
|---|---|
| 首句是否只重新提问 | **是。**准确但不够结论先行 |
| 是否应提前 load-bearing 结论 | **是。**应在首句直接回答 Q2 |
| official delta 是否抢在 primary paired evidence 前 | **是，属于顺序 Minor。**没有统计错误，但 paired effect/CI 才直接闭合 Method 3.4 的判据 |
| paired effect 与 CI 是否正确 | **是。**均为同一逐 minicube estimand 的 mean 与 paired-bootstrap CI |
| Validation/OOD-t 是否需分别成段 | **否。**在一个并行句中明确标注 split 即可 |
| 是否逐格复述 Table 2 | **否。**正文只提取 state removal 的必要结果 |
| 是否统计语言过密 | **否。**密度可接受，重排后会更自然 |
| \(T=I\) 边界是否足够 | **是。**supporting + readout distribution-shift caveat 均明确 |
| paired \(n\) 是否应报告 | **建议报告。**最佳位置是 caption；正文只在不使句子拥挤时加入 |
| 是否应避免 “significant” | **是。**当前直接写 CI excludes zero，处理正确 |
| 是否扩大为全部 state necessity | **否。**当前只称 state-mediated path load-bearing |
| 是否达到 AAAI 成熟度 | **接近。**事实与边界成熟，叙事顺序仍可提升 |
| 最小修订能否达到 4.1 水平 | **能。**无需新增结果或扩写成新 subsection |

---

## 6. Q2 冻结事实核对

冻结源：

- Validation：
  `evidence_workspace/raw/release/val_q2_state_contract_exclusive.json`，
  SHA-256
  `33b40d3e6bf6e0190c9415a9e0421e9809063356dcba2350890defeeed35f2d9`；
- OOD-t：
  `evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json`，
  SHA-256
  `7ebc0569d705a9991ac8b8d17c42113c9da052b2bec73f7c28d021e28a65a051`。

### 6.1 State removal：primary intervention

| Split | Full \(R^2\) / RMSE | State removed \(R^2\) / RMSE | Official \(\Delta R^2\) | Paired mean \(\Delta R^2\) [95% CI] | Paired \(n\) | 核对 |
|---|---|---|---:|---|---:|---|
| Validation | 0.49732 / 0.15729 | 0.48611 / 0.17101 | 0.01121 | 0.01616 [0.00643, 0.02590] | 589 | **PASS** |
| OOD-t | 0.56935 / 0.15059 | 0.54938 / 0.16519 | 0.01997 | 0.02200 [0.01422, 0.03018] | 1,019 | **PASS** |

### 6.2 \(T_\psi=\mathrm{Id}\)：supporting diagnostic

| Split | \(T=\mathrm{Id}\) \(R^2\) / RMSE | Official \(\Delta R^2\) | Paired mean \(\Delta R^2\) [95% CI] | Paired \(n\) | 核对 |
|---|---|---:|---|---:|---|
| Validation | 0.48542 / 0.26102 | 0.01191 | 0.01742 [0.00782, 0.02696] | 589 | **PASS** |
| OOD-t | 0.54766 / 0.25832 | 0.02169 | 0.02402 [0.01609, 0.03217] | 1,019 | **PASS** |

### 6.3 统计口径

| 对象 | 正确定义 | 当前正文 | 判定 |
|---|---|---|---|
| Official \(\Delta R^2\) | dataset-level \(R^2_{\rm full}-R^2_{\rm intervention}\) | 单独报告 | **PASS** |
| Paired effect | 每个 minicube 的 full-minus-intervention \(\Delta R^2\) 后取均值 | 单独报告 | **PASS** |
| Paired CI | 对 paired per-minicube effect 做 bootstrap | 只与 paired mean 相连 | **PASS** |
| 方向 | 正值表示干预后 forecast skill 更低 | 数字、表头和结论一致 | **PASS** |
| Split comparison | 未进行 Val 与 OOD-t 效应差的统计检验 | 当前未声称 OOD-t 效应更强 | **PASS** |
| 内部 0.005 gate | 仅是历史 evaluator 内部判据，不应进入论文定义 | 当前未出现 | **PASS** |

两个 primary paired CI 均完全位于零以上，支持 state-mediated contribution 在
Validation 和 OOD-t 上均为 load-bearing。数值上 OOD-t 均值较大不能被写成
“OOD-t 上显著更强”，因为没有 split-by-intervention difference test。

---

## 7. Primary / supporting 证据层级

| 层级 | 操作 | 观察 | 可支持的最强含义 | 不能支持 |
|---|---|---|---|---|
| **Primary / defining** | 在最终加法前令 \(\alpha=0\)，移除 \(r_h\)，恢复 \(b_h\) | 两个 split 的 paired forecast-skill loss 均为正，CI 排除零；official drop 同方向 | state-mediated contribution is load-bearing；显式 state path carries a measurable forecast increment | 全部预测信息都经过 state；state 是完整物理状态；state 必要且充分 |
| **Supporting** | 用 identity 替换 learned \(T_\psi\) | 两个 split 同方向退化 | learned transition is involved in prediction | transition necessity；干净的因果必要性；独立定义 load-bearing |

当前正文已正确保持该层级。Table 2 同时展示两项操作不会自动使其证据地位相同；
caption 和正文已明确 primary/supporting。

---

## 8. Table 2 科学表达与 AAAI 格式

### 8.1 逐项检查

| 检查项 | 当前状态 | 判定 |
|---|---|---|
| 只回答 Q2 | full、state removal、\(T=Id\)；无 Q1/Q3 | **PASS** |
| 列职责 | Split / Configuration / \(R^2\) / RMSE / official / paired+CI | **PASS** |
| Official 与 paired estimand 分列 | 是 | **PASS** |
| Full TerraState | 两个 split 均标 `reference` | **PASS** |
| State removed 的 primary 身份 | caption 明确 | **PASS** |
| \(T=Id\) 的 supporting 身份 | caption 明确 | **PASS** |
| Paired \(n=589/1{,}019\) | 表、caption、当前正文均未显示 | **MINOR** |
| Caption 自包含性 | 定义 official、paired、bootstrap 和主辅层级 | **PASS WITH MINOR** |
| Caption 位置 | 表格下方 | **PASS** |
| Caption 字体 | PDF 中约 9.96 pt，Roman | **PASS** |
| Table body 字体 | PDF 中约 8.97 pt，即 nominal 9 pt | **PASS** |
| Booktabs | `toprule/midrule/bottomrule` | **PASS** |
| 竖线/密集 hline | 无 | **PASS** |
| resizebox/scalebox | 无 | **PASS** |
| negative vspace | 无 | **PASS** |
| 数值/小数/CI | 各列一致；冻结值正确舍入 | **PASS** |
| Overfull/裁切/margin intrusion | log 无 overfull；PDF 坐标均在页面边界内 | **PASS** |
| Label/reference | `tab:q2` 正常解析为 Table 2 | **PASS** |

AAAI-27 Author Kit 要求 table caption 位于表格下方、caption 为 10pt Roman、表体
必要时可使用 9pt，且禁止 `resizebox`/`scalebox`。当前 Table 2 满足这些要求。

当前 PDF 共 9 页；Table 2 位于第 7 页。4.3 正文位于第 5 页。该跨页浮动是全篇
双栏浮动/分页问题，本轮明确排除，因此不计入 4.3 或 Table 2 的格式失败。

### 8.2 Table 2 总判定

**PASS（带一个非阻塞的统计自包含性 Minor）。**

paired \(n\) 的后续处理建议为：

- **优先位置：** caption 末尾简洁写明
  `paired n=589 for Validation and 1,019 for OOD-t`；
- **无需：** 新增一列、修改任何 effect/CI 或在正文重复两遍；
- **级别：** **OPTIONAL-BUT-RECOMMENDED**，用于提高自包含性，不改变数值、
  verdict 或科学结论。

---

## 9. 推荐信息槽

不直接撰写最终英文；后续 4.3 修改建议按以下信息顺序施工。

### 槽 1：结论先行

- 首句直接回答 Q2；
- 限定对象为 TerraState 的 **state-mediated contribution**；
- 限定范围为 Validation 和 OOD-t；
- 同一句或紧邻句说明 state removal 是 primary intervention；
- 不以 `Q2 asks...` 或 `As shown in Table...` 开场。

### 槽 2：Primary paired evidence

- Validation：paired mean \(0.01616\)，95% CI
  \([0.00643,0.02590]\)，\(n=589\)；
- OOD-t：paired mean \(0.02200\)，95% CI
  \([0.01422,0.03018]\)，\(n=1{,}019\)；
- 明确两个区间均排除零；
- 不使用 “significant”，不引入内部 0.005 floor；
- 两个 split 在同一个平行句中即可，无需各成一段。

### 槽 3：Dataset-level effect size

- Validation official \(\Delta R^2=0.01121\)；
- OOD-t official \(\Delta R^2=0.01997\)；
- 明确这是 dataset-level full-minus-intervention difference；
- 与 paired mean/CI 分句，不把 paired CI 写成 official delta 的区间；
- 作用是补充总体效果规模，而不是替代 primary paired evidence。

### 槽 4：科学含义

- 移除显式 state contribution 后，两个 split 的 forecast quality 均沿预期方向
  下降；
- 因而该路径承载可测量的 forecast increment；
- 最多用一个短 scope phrase 防止被读成“整个预测都依赖 state”；
- 完整物理状态、因果必要性和普遍 world-model 定义继续由 Method/Limitations
  限定，不在结果段堆叠限制清单。

### 槽 5：Supporting transition diagnostic

- \(T=Id\) 的退化方向一致；
- 只支持 transition involvement；
- 保留 readout 可能接收训练分布外 state 的 caveat；
- 不需要在正文再次朗读四个 \(T=Id\) 精确 effect/CI，Table 2 已承担该职责；
- 不写 transition necessity。

---

## 10. 推荐段落数、句数和长度

**推荐形式：短开场 + 一个结果段。**

- **开场：** 1 句，直接给 load-bearing 结论并标明 state removal 的 primary
  地位；
- **Table 2；**
- **结果段：** 4--5 句，依次承担 paired evidence、official scale、有限机制
  含义、\(T=Id\) supporting boundary；
- **总计：** 5--6 句；
- **建议长度：** 约 **125--150 个英文词**。

不推荐：

- 拆成 Validation 和 OOD-t 两个重复段落；
- 为 Table 2 每一行分别写一句；
- 把开场扩展成重新解释 Method 3.4；
- 用一个超长段同时塞入所有限制。

---

## 11. 允许与禁止的最强主张

### 11.1 当前证据严格支持

- `the state-mediated contribution is load-bearing on both splits`;
- `removing the state contribution reduces forecast quality on Validation and OOD-t`;
- `both paired confidence intervals exclude zero`;
- `the explicit state path carries a measurable forecast increment`;
- `state removal provides the primary evidence`;
- `the identity-transition intervention provides supporting evidence of transition involvement`;
- `the learned transition is involved in prediction`，但必须保留 supporting 范围。

### 11.2 不允许

- the entire forecast depends on the state；
- all predictive information passes through the state；
- the state is necessary and sufficient；
- the state is a complete physical state；
- the transition is proven necessary；
- \(T=Id\) proves load-bearing；
- the OOD-t effect is significantly larger than the Validation effect；
- the model generalizes better under OOD because the numerical effect is larger；
- causal contribution；
- counterfactual correctness；
- Q2 alone proves a universal definition of world model；
- non-collapse；
- composition/Q4；
- 将内部 0.005 floor 写成论文或领域判据；
- 用 future-state alignment loss 替代 Q2 intervention evidence。

当前 4.3 未命中上述越界主张。

---

## 12. 世界模型主线检查

| 叙事职责 | 4.3 应承担什么 | 当前状态 |
|---|---|---|
| 区分“命名为 state”与“实际承担预测” | 用 state removal 检验显式 state-mediated contribution | **PASS** |
| 证明 state path 位于 forecast path | 移除贡献后预测质量下降 | **PASS** |
| 建立 Q2 的定义性证据 | paired effect/CI 支持 load-bearing | **PASS** |
| 与 Q1 分工 | Q1 只提供 useful forecasting prerequisite | **PASS** |
| 与 Q3 分工 | Q3 进一步检验 future-weather response fidelity | **PASS** |
| 防止范围扩大 | 不写全部预测信息、完整物理状态、因果或普遍定义 | **PASS** |

最准确的全文关系是：

> Q1 建立预测前提；Q2 支持显式 state-mediated contribution 承载可测预测增量；
> Q3 再检验这一声明路径对未来天气的响应保真度。

Q2 不能代替 Q3，Q3 也不能反向替代 Q2。当前 4.3 没有把论文改写成 benchmark、
普通 retraining ablation 或物理状态识别。

---

## 13. 中英文与简版镜像审计

### 13.1 权威英文与完整中文

`paper/main.tex` 与 `MANUSCRIPT_ZH_FULL.md` 当前 4.3 在以下方面一致：

- state removal 为主干预；
- \(T_\psi\!\to I\) 为辅助诊断；
- official 与 paired estimand 分开；
- Validation/OOD-t 数字和 CI 一致；
- 两个 paired CI 均不跨零；
- load-bearing 自然译为“承载预测”；
- \(T=Id\) 的 readout 分布外风险一致；
- 中文没有写成“完全依赖”“必要且充分”或“证明了世界模型”。

**英文 ↔ 完整中文：PASS。**

### 13.2 两个简版 Markdown

`MANUSCRIPT.md` 与 `MANUSCRIPT_ZH.md` 的 Q2 科学内容仍然安全：

- 没有 11,904/boundary80；
- 没有旧 Q2 数字；
- 没有把 official 与 paired CI 混写；
- 没有 Published/Local/Source 表格分组叙事；
- 没有把 \(T=Id\) 升格为 primary；
- 额外明确“不比较两个 split 的效应强弱”，范围安全。

但二者仍使用较旧的 8 列阅读表，省略 RMSE，并且没有当前权威稿的两句开场结构。
这不是事实错误，而是版本呈现不同步。后续 4.3 修订完成后，应同步：

1. 最终小节标题；
2. 结论先行的开场；
3. primary paired evidence → official scale 的顺序；
4. Table 2 当前六列结构与 RMSE；
5. paired \(n\) 的最终放置决定；
6. \(T=Id\) supporting caveat。

**简版镜像：科学口径 PASS；结构同步 MINOR。**

---

## 14. 质量评分

评分标准：1=明显不达标；3=基本可用；4=投稿成熟；5=高度成熟。

| 维度 | 分数 | 说明 |
|---|---:|---|
| AAAI 结果结构 | **4.0** | 链路完整，但结论尚未前置 |
| 首句力度 | **3.0** | 准确提出问题，没有直接回答 Q2 |
| Primary/supporting 层级 | **4.8** | 主辅边界非常清楚 |
| 统计表达 | **4.7** | estimand/CI 正确；paired \(n\) 未显示 |
| 结果解释深度 | **4.2** | 已到 load-bearing 含义，可再明确 measurable increment |
| 世界模型主线连接 | **4.6** | Q2 的定义性地位清楚 |
| Claim--evidence 对齐 | **5.0** | 无因果、必要充分或完整物理状态越界 |
| 英文自然度 | **4.4** | 紧凑清楚，主要问题是叙事顺序 |
| 简洁度 | **4.7** | 约 116 词，无工程日志或表格朗读 |
| Table 2 与正文分工 | **4.3** | exact aggregate 与结论分工良好 |
| 中英文一致性 | **3.9** | 完整中文一致；两个简版镜像结构较旧 |
| 与冻结 4.1 质量一致性 | **4.0** | 事实纯度一致，结论先行程度略低 |
| **平均分** | **4.3 / 5.0** | **适合进入最小修订** |

---

## 15. Critical / Major / Minor 清单

### Critical（0）

未发现。

### Major（0）

未发现。当前 4.3 不需要新实验、重算、证据修复或章节重构。

### Minor（4）

#### M1：首句没有直接回答 Q2

- **位置：** 4.3 第一段首句；
- **当前作用：** 重新提出问题；
- **风险：** 结果段显得比冻结 4.1/成熟 AAAI 段落更像 protocol 导入；
- **最小处理：** 将 load-bearing 结论前置。

#### M2：Official effect 先于 primary paired evidence

- **位置：** Table 2 后结果段前两句；
- **事实状态：** 完全正确；
- **风险：** 读者可能把 dataset-level official delta 误认为定义性统计证据；
- **最小处理：** paired mean/CI 先行，official delta 后置为 aggregate scale。

#### M3：Paired \(n\) 未显示

- **位置：** Table 2、caption 与 4.3 正文；
- **风险：** paired estimand 的统计单位不够自包含；
- **最小处理：** caption 中补 `n=589/1,019`；
- **性质：** optional-but-recommended，不改变任何结果。

#### M4：两个简版 Markdown 仍使用旧 4.3 呈现

- **位置：** `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md`；
- **事实状态：** 数字、estimand 和证据边界正确；
- **风险：** 后续人工查看时出现两个不同的 Table 2 结构；
- **最小处理：** 在 4.3 正文修订后一次性同步，不单独重写主张。

---

## 16. 精确、最小的后续修改建议

按以下顺序执行即可：

1. 把开场改为一句结论先行的 Q2 回答，同时保留 state removal primary；
2. Table 2 后先报告 Validation/OOD-t 的 paired means、CI 和 split 标签；
3. 在同一句或 caption 中补 paired \(n=589/1{,}019\)；
4. 再报告两个 dataset-level official \(\Delta R^2\)，明确它们是另一 estimand；
5. 用一句解释 state path carries a measurable forecast increment，不扩大为整个
   forecast/state necessity；
6. 保留当前 \(T=Id\) supporting + readout distribution-shift 句，不补全套
   \(T=Id\) 数字；
7. 同步 `MANUSCRIPT_ZH_FULL.md`、`MANUSCRIPT.md` 和
   `MANUSCRIPT_ZH.md` 的最终 4.3；
8. 不修改 Q2 数值、Table 2 行列职责、Section 3、4.1/4.2/4.4、Figure 或证据。

完成上述最小修订后，再进行一次只读终审即可。当前不存在进入 4.3 修订的阻塞。

---

## 17. 最终状态

# READY_FOR_4_3_REVISION
