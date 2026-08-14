# TerraState AAAI-27 Section 3 跨章节回归审计

审计日期：2026-07-28  
审计性质：只读跨章节回归；不重新审查研究方向，不重新设计方法  
权威正文：`paper/main.tex`  
最终状态：`SECTION3_CROSS_SECTION_REGRESSION_REVISE`

## 1. Verdict

# SECTION3_CROSS_SECTION_REGRESSION_REVISE

当前 Section 3 **正文和 Equations (1)–(8) 的方法事实通过回归**。四个小节形成稳定的

> task/state contract → inference architecture → future-anchored learning →
> post-training test interfaces

方法链，并与冻结 Introduction、Related Work、Section 4、最新 Limitations 和
Conclusion 保持一致。Q1、Q2、支持性的 \(T\!\to I\) 与 Q3 的证据职责没有混淆；
正文没有恢复 Q4、composition、non-collapse、SOTA、因果/反事实模拟器或
11,904/boundary80 最终模型叙事。

本轮不能判定 PASS 的唯一实质原因是 **Figure 2 图像本体仍与正确正文和实现不一致**：

1. 图中把 future meteorological forcing 放在 `Multimodal context` 内，并由同一
   总箭头送向 history encoder，视觉上违反 future weather 不进入
   \(q_\theta\) 的信息边界；
2. 图中以 weather tokens 与 state tokens 的乘号表示 shared transition，没有表达
   Equation (2)–(3) 的 condition fusion、残差更新和 same-\(z_t\)
   direct-per-horizon 语义；
3. 图中把 state readout 的输出继续画成 token grid，并保留 `D3 Vegetation
   forecast`；它没有准确表达 raster contribution \(r_h\)、Q2 的真实切点以及
   \(\widehat y=b+r\) 的完整结构语义。

这些是 **Figure 2 interface 的 Major 问题，不是 Section 3 正文问题**。因此最小
返修集合只要求 Figure 2 图像追上已经正确的正文与 caption；不得为了迁就现图而改写
Section 3。

### 问题计数

| 等级 | 数量 | 归属 |
|---|---:|---|
| Critical | **0** | 正文、公式和实验接口未发现阻断性事实错误 |
| Major | **3** | 均属于 Figure 2 图像本体的信息路径/算子/输出接口 |
| Minor | **3** | 两处 Section 3 自包含性/符号问题；一处 Section 4 复现配置缺口 |
| Optional | **2** | 不影响冻结的术语精化 |

---

## 2. 审计输入、权威冲突与缺失项

本轮完整阅读了任务指定的：

- `paper/main.tex` 全文；
- `paper/main.pdf` 全部 9 页；
- `MANUSCRIPT_ZH_FULL.md`；
- Section 1、Section 2 最终审计；
- Method 3.2、3.3、3.4 最终审计；
- Method global positioning audit 与 positioning regression audit；
- canonical method spec；
- Section 4.1–4.4 最终审计；
- results claim–evidence audit；
- Limitations/Conclusion revision log；
- Figure 3 单栏布局最终审计；
- `paper/references.bib`；
- 当前 Figure 2 图像本体。

`LIMITATIONS_CONCLUSION_FINAL_AUDIT_20260728.md` 在审计开始时尚不存在，但在
本报告初稿完成后的只读校验阶段生成。本轮已按要求补读全文。该终审判定
`LIMITATIONS_CONCLUSION_FROZEN`，并确认 Section 3 Method 与最新结尾章节在
predictive-state scope、shared transition、on-path contribution、future-state
anchor、Q1–Q3 证据边界和 falsifiability 上一致。其生成没有改变 `main.tex`、
PDF 或本轮任何冻结输入，因此不改变本报告的 Figure 2-only REVISE 原因。

### 2.1 历史训练身份冲突的裁决

旧 `METHOD_3_3_FINAL_AUDIT_20260728.md`、
`METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md` 和部分旧证据记录仍保留
11,904/boundary80 叙事。当前权威状态已经由作者确认并在冻结 Section 4.1–4.4、
当前 `main.tex` 和完整中文镜像中统一为：

- 最终模型完成 **40 epochs / 14,880 updates**；
- Q1–Q3 使用该同一最终模型；
- Q2/Q3 只改变冻结 forward computation，不重新训练；
- 11,904/boundary80 不得恢复为最终训练身份。

因此，旧审计中的 boundary80 是待同步历史记录，不构成当前 Section 3 回归错误。

---

## 3. Section 3 反向提纲

| 小节 | 唯一职责 | 输入/输出或关键动作 | 与相邻章节边界 | 判定 |
|---|---|---|---|---|
| 3.1 Problem Formulation and Model Overview | 定义任务、forecast-time information boundary 和 predictive-state contract | history-only \(q_\theta/P_\rho\) → \(z_t\)；future-weather-conditioned \(T_\psi\) → \(z_{t+h}\)；\(O_\omega\) → \(r_h\)；\(\widehat y=b+r\) | 不展开训练配置或实验统计 | **PASS** |
| 3.2 TerraState Architecture | 展开一次正式推理的 history/state、transition、readout 三个模块 | Equations (2)–(4)；patch-wise geography；shared direct transition；raster additive contribution | 不混入 teacher、future target 或结果判据 | **PASS** |
| 3.3 Future-Anchored State Learning | 区分 student/KD teacher/future target，定义 GT/KD/FS 目标与 inference boundary | Equations (5)–(7)；future EO 仅作 stopped training target | 不把训练约束当成 Q2 证据；训练时长/选模放 Section 4 | **PASS WITH MINOR NOTES** |
| 3.4 Testable Predictive-State Interfaces | 定义同一冻结模型上的 state removal、支持性 \(T\!\to I\) 和 weather substitution | \(\alpha=0\)；identity transition；Equation (8) 的 actual/donor/mean arms | 不报告样本数、CI 或结果；统计细节交给 Section 4 | **PASS** |

章节顺序与实际计算路径一致，四节职责唯一。Section 3 没有把评测协议写成模型主体，
也没有把 TerraState 写成纯 benchmark。成熟度主要来自：先定义状态和信息边界，再
展开结构，再说明如何学习，最后给出可证伪接口。

---

## 4. Equations (1)–(8) 信息路径回归

| Equation | 当前功能 | 信息与梯度路径核对 | 跨章节接口 | 判定 |
|---|---|---|---|---|
| (1) | 总合同：\(q\to P\to T\to O\)，最终 \(\widehat y=b+r\) | \(q_\theta\) 只读 cloud-masked EO history、past weather、static geography；future EO/weather 均不进入 history inference；future weather 只经 \(T_\psi\) | 兑现 Introduction 的完整方法承诺 | **PASS** |
| (2) | \(d_h=E_u(u_{t+1:t+h})\)，与 patch geography、elapsed-time code 融合为 \(c_{h,i}\) | weather/horizon 广播，geography 保留 patch-wise 变化；共享的是参数而非所有空间 condition value | 支撑 Related Work 中 forcing-conditioned state path 的区别 | **PASS** |
| (3) | 残差状态转移 | 每个 \(h\) 从同一 \(z_t\) 直接调用一次 shared transition；不是 recurrent rollout | 与“不主张 recurrent composition”一致 | **PASS** |
| (4) | transitioned state 的 raster readout 与加性预测 | \(O_\omega\) 把 token 映射为局部 \(4\times4\) patches，再重组为 \(r_h\)；标准路径 \(\alpha=1\) | Q2 在 \(r_h\to+\) 前令 \(\alpha=0\) | **PASS** |
| (5) | GT 和 KD forecast objectives | GT：逐 pixel 按 clear horizons 归一化，再对 vegetation × prediction-valid pixels 平均；KD：clear × vegetation time-pixel global mean；teacher target stop-gradient | 与 Section 4 forecasting prerequisite 分层，不等于 Q2 | **PASS** |
| (6) | terminal future-state target 与 FS loss | training-start frozen \(q_{\theta^0}/P_{\rho^0}\)；all-frame EO + recorded masks；past weather/static geography；future weather zero；terminal fully-clear \(4\times4\) patch 且含 vegetation；LN 后 cosine | future EO 只作 training-only stopped target | **PASS** |
| (7) | 总训练目标 | \(\mathcal L_{\rm GT}+0.5\mathcal L_{\rm KD}+\lambda_s\mathcal L_{\rm FS}\)；teacher/target 训练后移除 | Section 4 负责训练时长与模型选择 | **PASS WITH REPRODUCIBILITY NOTE** |
| (8) | controlled weather-path substitution | 固定模型、样本、history、\(b\)、\(z_t\)、\(g\)、\(h\)、readout、mask 和 truth；只替换 future weather；\(\Delta L=L_{\rm ctrl}-L_{\rm act}\) | Section 4 使用完整 20 步窗口和 geographic-cluster CI | **PASS** |

### 4.1 关键路径结论

实际逻辑在正文中完整成立：

> cloud-masked EO history  
> \(\rightarrow\) history-derived spatial predictive state  
> \(\rightarrow\) future-weather/geography/elapsed-time-conditioned shared transition  
> \(\rightarrow\) transitioned state  
> \(\rightarrow\) explicit state-mediated contribution  
> \(\rightarrow\) final observation forecast

未来天气没有泄漏到历史状态推断；context-only \(b_h\) 是独立、匹配的历史上下文
预测；TerraState 采用 direct-horizon shared transition，而不是未实现的 recurrent
simulator。

---

## 5. 训练身份与目标回归

### 5.1 三种训练身份

| 身份 | 初始化/来源 | 输入 | 冻结与梯度 | 推理时去向 | 判定 |
|---|---|---|---|---|---|
| TerraState student | forecasting precursor 的 exact full-model warm start | 正式路径：cloud-masked historical EO、past weather、static geography；future weather 只经 \(T_\psi\) | 只更新训练 schedule 允许的 student 参数 | **保留，唯一部署主体** | **PASS** |
| Frozen full-weather KD teacher | 独立 full-weather teacher | EO history、past weather、static geography、complete future-weather sequence；无 future EO | 永久冻结，输出 stop-gradient | **训练后移除** | **PASS WITH MINOR WORDING NOTE** |
| Future-state target encoder | training-start student \(q_\theta/P_\rho\) 的冻结副本 | all-frame observed EO（含 future frames 和 recorded masks）、past weather、static geography；future weather zero | 永久冻结；target stop-gradient；梯度只回 student transitioned-state path | **训练后移除** | **PASS** |

### 5.2 目标、mask、权重与日程

| 项目 | 当前正文/冻结事实 | 判定 |
|---|---|---|
| GT objective | 公式、clear mask、vegetation mask、prediction-valid aggregation 均正确 | **PASS** |
| KD objective | clear × vegetation global mean，权重 0.5，teacher stopped | **PASS** |
| Future-state objective | terminal \(h=H\) target、fully-clear+vegetation patch mask、LN-cosine | **PASS** |
| 总权重 | GT 1.0、KD 0.5、FS \(\lambda_s\) | **PASS** |
| 最终训练长度 | 40 epochs / 14,880 updates | **PASS** |
| 同一最终模型 | Q1–Q3 均使用同一完成完整训练的 final model | **PASS** |
| 11,904/boundary80 | 当前正文无此叙事；不得恢复 | **PASS** |
| \(\lambda_s\) 数值 schedule | 当前投稿只保留符号 \(\lambda_s\)，Section 4 未给数值日程 | **MINOR：复现配置缺口，不是事实冲突** |

Future-state anchoring 是训练约束，用来塑造 transitioned representation；Q2 的
state removal 才是 state path 是否 load-bearing 的主要证据。当前正文没有把二者
混淆。

---

## 6. Introduction promise → Method realization

| 冻结 Introduction 承诺 | Section 3 落点 | 是否兑现 | 是否多说 |
|---|---|---:|---:|
| testable predictive-state world model | 3.1 的 contract；3.4 的两个 post-training interfaces | **是** | 否 |
| spatial state inferred from cloud-masked histories | Eq. (1)，3.2 history/state paragraph | **是** | 否 |
| shared transition conditioned on future weather/geography/elapsed time | Eq. (2)–(3) | **是** | 否 |
| explicit contribution to final forecast | Eq. (4) 的 \(b_h+\alpha r_h\) | **是** | 否 |
| future-state anchor | Eq. (6)–(7) | **是** | 否 |
| state-removal interface | 3.4，\(\alpha=0\) | **是** | 否 |
| weather-substitution interface | Eq. (8)，actual/donor/mean | **是** | 否 |

Introduction 没有暗示 Section 3 未实现的 complete physical state、causal/general
generative simulator、recurrent composition 或“所有信息都必须经过状态”。

---

## 7. Related Work distinction → Method support

| Related Work 区别 | Section 3 的结构支持 | 结论 |
|---|---|---|
| 相比只以 predicted observations 为主要证据的 EO forecasting，增加 state-mediated path 的直接检验 | Eq. (4) 暴露 \(r_h\)，3.4 定义 state removal | **SUPPORTED** |
| 相比 EO-WM/VegSim 的相邻目标，检验同一 observed-weather predictor 中的 removable state contribution | \(\alpha=0\) 精确恢复 \(b_h\)；同一冻结模型无需重训练 | **SUPPORTED** |
| actual-vs-control complete-window fidelity 有可执行接口 | Eq. (8) 固定所有非天气条件，只替换 future weather | **SUPPORTED** |
| future-representation anchor 塑造 state content | training-start frozen future target + \(\mathcal L_{\rm FS}\) | **SUPPORTED** |
| on-path state 真正存在 | \(z_{t+h}\to O_\omega\to r_h\to\widehat y\) | **SUPPORTED** |
| 不声称经典 PSR sufficient-statistic guarantee | 3.1、Related Work 的 scope 限定一致 | **SUPPORTED_WITH_SCOPE** |
| 不恢复 compositional dynamics | direct-per-horizon、non-recursive 明确；无 Q4 | **PASS** |

Section 3 支撑的是结构和可检验接口差异，不声称 TerraState 是唯一合法 world model，
也不否定 EO-WM/VegSim 的原有目标。

---

## 8. Method component → Q1/Q2/Q3 evidence

| Method component | 证据问题 | Section 4 实际证据 | 允许结论 | 禁止外推 |
|---|---|---|---|---|
| 完整 forecast model | Q1 | OOD-t \(R^2=0.56935\)，RMSE \(=0.15059\)，\(n=1{,}904\) | useful temporal-shift forecasting skill | SOTA、strict ranking、non-inferiority |
| 显式 state-mediated contribution \(r_h\) | Q2 primary | Validation/OOD-t state removal；paired CIs 均排除零 | state path is load-bearing under the protocol | 所有信息必须经过 state；完整物理状态 |
| shared transition \(T_\psi\) | \(T\!\to I\) supporting | 两个 split 同方向退化 | transition involvement 的支持性诊断 | transition necessity；与 state removal 同强度 |
| future-weather conditioning | Q3 | 84 frozen pairs；actual/donor/mean；完整 20 步窗口；两个 geographic-cluster CIs 均排除零 | detectable response + greater actual-weather complete-window fidelity | causal correctness、counterfactual correctness、任意天气干预有效 |
| future-state anchor | 训练机制/潜在消融接口 | 当前主结果没有把它单独作为 Q2 证明 | shapes transitioned representation | 不伪装成 load-bearing 的直接证据 |

### 8.1 Q3 专项

- matched donor 首次定义为 season-, geography-, and quality-matched；
- normalized mean 是 frozen global z-score space 中的零；
- \(R^2=0.6254\) 与 RMSE \(=0.1492\) 只属于 84-pair matched subset；
- 56/84 与 69/84 只是描述性计数；
- hot-dry interaction CI 跨零，正文没有把它写成正结果；
- 当前没有 Q4。

---

## 9. 术语与符号表

| 术语/符号 | 当前统一含义 | 首次或主要落点 | 一致性 |
|---|---|---|---|
| predictive state | 由历史推断、服务未来预测的任务相关表示 | 3.1 | **一致** |
| spatial predictive state | 保留 patch-level spatial organization 的 \(z_t\) | 3.2 | **一致** |
| transitioned state | 经 \(T_\psi\) 推进的 \(z_{t+h}\) | 3.2–3.3 | **一致**；3.1 的 `advanced state` 为同义表述 |
| state-mediated contribution/path | \(O_\omega(z_{t+h})=r_h\) 及其到最终加法的路径 | Eq. (4) | **一致** |
| shared transition | 参数跨 patch/horizon 共享的 \(T_\psi\)，condition value 可变 | Eq. (2)–(3) | **一致** |
| future forcing / future weather | supplied future meteorological sequence；正式预测只进入 \(T_\psi\) | 3.1–3.4 | **语义一致** |
| future-state anchor | training-only future-representation target/constraint | 3.3 | **一致** |
| context-only prediction/forecast | history-only \(b_h\) | Eq. (1)、(4) | **一致** |
| state removal | 评测期在加法前临时令 \(\alpha=0\) | 3.4 | **一致** |
| identity transition | 令 \(T_\psi\) 返回 state identity；不是删除整个模型 | 3.4 | **一致** |
| matched-donor weather | season/geography/quality-matched donor future weather | 3.4/4.4 | **一致** |
| normalized-mean weather | frozen global z-score weather space 中的零 | 3.4/4.4 | **一致** |
| complete-window fidelity | 完整 20 步 masked forecast-window loss 上 actual 优于 controls | 3.4/4.4 | **一致** |
| \(q_\theta\) | history operator；输出 \(b_{1:H},e_t\) | Eq. (1) | **首次定义清楚** |
| \(P_\rho\) | spatial state projector | Eq. (1) | **首次定义清楚** |
| \(T_\psi\) | future-weather/geography/horizon-conditioned shared transition | Eq. (1) | **首次定义清楚** |
| \(O_\omega\) | transitioned-state raster readout | Eq. (1) | **首次定义清楚** |

`state`、`representation` 和一次性的 `latent target` 没有产生能力漂移；正文始终以
predictive state 为正式身份。`forcing`、`driver`、`weather` 也未被扩张为因果干预。

### 9.1 符号 Minor

3.1 用 \(m_i\) 表示历史观测 validity mask；Equation (6) 又用 \(m_i\) 表示 terminal
patch 的 future-state validity mask。局部上下文足以消歧，但属于可避免的符号复用。
若未来仅做全篇符号校对，可把 Equation (6) 的 patch mask 改成其他符号；本项不要求
重新打开方法事实。

---

## 10. Figure 2 interface

### 10.1 Caption

`paper/main.tex:461–473` 的 caption 与真实方法一致：

- history encoder 的输入只含 cloud-masked EO history、past meteorology 和 static
  geography；
- future meteorological forcing 进入 shared transition；
- transitioned state 读出为显式 state contribution 并与 context-only forecast
  结合；
- Q2 移除 state contribution；
- Q3 使用 season/geography/quality-matched donor 或 normalized mean；
- 接口检验 contribution 与 complete-window fidelity，不是 composition 或 causal
  effect。

**Caption：PASS。**

### 10.2 图像本体

当前实际提交图：

`paper/figures/terrastate_architecture_fig2_author_noborder_20260728.png`

SHA-256：

`9192e1d0f66253bad3391ac7208a5de91e663586157776fa8c8d30a46aa714f5`

| 图像问题 | 与正文/实现的冲突 | 严重度 | 责任 |
|---|---|---|---|
| Future meteorological forcing 位于 `Multimodal context` 内，整体箭头指向 history encoder | 视觉上允许 future weather 进入 \(q_\theta\)，违反 Eq. (1) 和 `main.tex:234–237` | **Major M1** | Figure 2 |
| Shared transition 以 weather tokens × state tokens 表示 | 实现为 weather/geography/horizon concat/fusion 后的 residual MLP update；不是乘法或 gate | **Major M2** | Figure 2 |
| 无 same-\(z_t\) direct-per-horizon 与 residual skip；readout 输出仍是 token grid，且保留 `D3` | 不能恢复 Eq. (3) 的 direct residual semantics、\(r_h\) 的 raster 类型及真实 Q2 切点 | **Major M3** | Figure 2 |

Figure 2 的问题不是纯美学问题。它直接改变读者对 information boundary、transition
operator 和 state contribution 类型的理解，因此触发本轮 REVISE。正文和 caption
均不应迁就该图。

### 10.3 Figure 3

Figure 3 已冻结，当前单栏 asset 与 caption 一致：

- state removal 为 filled/primary；
- \(T\!\to I\) 为 open/supporting；
- Q3 展示 84 frozen pairs 的完整 20 步 masked MSE；
- 56/84 与 69/84 仅为 descriptive counts。

Section 3.4、Section 4 和 Figure 3 的证据接口一致，未发现回归。

---

## 11. Limitations / Conclusion 一致性

| 最新限制或结论 | Section 3 是否支持/保持边界 | 判定 |
|---|---|---|
| predictive representation \(\ne\) complete physical state | 3.1 明确限定 \(z_t\) 为 predictive representation | **PASS** |
| operational weather forecast deployment gap | Section 3 只定义 supplied future weather，不声称已评测 forecast-error shift | **PASS** |
| conditional fidelity \(\ne\) causal/counterfactual identification | 3.4 明确否定 causal effect 与 counterfactual guarantee | **PASS** |
| state-path increment \(\ne\) all information through state | Eq. (4) 保留 \(b_h\)；3.4 只定义 removable contribution | **PASS** |
| Conclusion 的 history state/shared transition/explicit contribution | Eq. (1)–(4) 全部存在 | **PASS** |
| Conclusion 的 future-state anchoring | Eq. (6)–(7) 存在 | **PASS** |
| Conclusion 的 state/weather post-training interfaces | 3.4 与 Eq. (8) 存在 | **PASS** |
| empirically testable and falsifiable | \(\alpha=0\) 和 controlled weather substitution 提供明确切点 | **PASS** |

最新 Limitations/Conclusion 没有与 Method 冲突，也没有借结论恢复 complete state、
causal/counterfactual correctness、all-information bottleneck、Q4 或 extreme-specific
enhancement。

独立终审 `LIMITATIONS_CONCLUSION_FINAL_AUDIT_20260728.md` 进一步给出
Critical \(=0\)、Major \(=0\) 和 `LIMITATIONS_CONCLUSION_FROZEN`，与本节结论一致。

---

## 12. 禁止回归扫描

对 Section 3 进行语境化搜索后：

- 无 Q4；
- 无正向 composition/non-collapse 主张；
- 无 causal/counterfactual simulator 主张；
- 无 complete physical state 主张；
- 无 SOTA/state-of-the-art/strict-ranking；
- 无 Published/Local/Source 标签；
- 无 seed/run/\(\pm\) 结果叙事；
- 无 11,904/boundary80；
- 无 endpoint-only Q3；
- 无正向 extreme-specific enhancement；
- 无 Stage A/Stage B、B4、exclusive、pilot、smoke、full24、physical4 工程词。

搜索命中的 `complete physical state`、`causal`、`counterfactual`、
`extreme-specific enhancement` 和 `composition` 均出现在合法否定句中；`local`
只出现在 `local \(4\times4\) patch`，`runs` 只描述 frozen encoder 的执行，不是
实验 run 叙事。

---

## 13. Critical / Major / Minor / Optional

### Critical（0）

无。Section 3 正文、Equations (1)–(8)、训练身份和 Q1–Q3 接口未发现 Critical
错误。

### Major（3）

#### M1 — Figure 2 视觉上把 future weather 送入 history encoder

- **位置：** Figure 2 panel (a)→(b)，PDF 第 6 页；
- **问题：** future forcing 与历史输入共处一个 `Multimodal context`，同一总箭头
  进入 history encoder；
- **可信度影响：** 读者会合理推断 forecast-time future-weather leakage，直接破坏
  论文最重要的信息边界；
- **归属：** Figure 2；
- **最小方向：** 把 future weather 完全移出 history-context 容器，并以独立箭头只
  送入 transition weather path。

#### M2 — Figure 2 的 transition operator 类型错误

- **位置：** Figure 2 panel (c)；
- **问题：** weather tokens 与 state tokens 用乘号组合；
- **可信度影响：** 与 Eq. (2)–(3) 的 condition fusion + residual transition 不同，
  会让读者误判算子和参数共享语义；
- **归属：** Figure 2；
- **最小方向：** 用 condition-fusion 节点和 residual update 取代乘号，并标出
  geography/horizon 条件。

#### M3 — Figure 2 未忠实表达 direct transition、raster readout 和干预切点

- **位置：** Figure 2 panel (c)–(d)；
- **问题：** 没有 same-\(z_t\) direct-per-horizon/residual skip；readout 后仍是
  token grid；Q2 切点和 `D3` 标签不准确；
- **可信度影响：** 图无法与 Eq. (3)–(4) 和 Q2 evaluator 同构；
- **归属：** Figure 2；
- **最小方向：** 标出 one direct query per \(h\)，将 readout 输出改为 raster
  \(r_h\)，在 \(r_h\to+\) 处标 Q2 removal，并把最终输出改为论文符号
  \(\widehat y_{t+h}\)。

### Minor（3）

#### m1 — KD teacher 输入列表未显式写出 past weather

- **位置：** `paper/main.tex:317–319`；
- **问题：** `observation history` 可能被窄读为 EO history，而实际 teacher 还读取
  past weather；
- **影响：** 不改变 full-weather teacher 身份，但训练输入表述不完全自包含；
- **归属：** Section 3.3 正文；
- **最小方向：** 若以后因 Figure 2 之外另有获批的术语同步，只增加 `past weather`，
  不改 teacher 身份或公式。

#### m2 — \(m_i\) 在历史 mask 与 future-state patch mask 间复用

- **位置：** `paper/main.tex:213–214` 与 `381–382`；
- **问题：** 两种不同粒度的 validity mask 使用同一符号；
- **影响：** 上下文可消歧，不影响公式数值，但降低符号局部清晰度；
- **归属：** Section 3 符号；
- **最小方向：** 仅在获批的全篇符号校对中更名 future-state patch mask。

#### m3 — \(\lambda_s\) 的数值 schedule 未在当前投稿中给出

- **位置：** Eq. (7) 与 Section 4 implementation；
- **问题：** 当前能核对 40 epochs / 14,880 updates 和总目标层级，但不能从论文恢复
  \(\lambda_s\) 的数值日程；
- **影响：** 复现完整性受限，不构成方法事实冲突；
- **归属：** Section 4 / reproducibility material；
- **最小方向：** 后续只在获批的复现配置同步任务中补充，不移入 Section 3。

### Optional（2）

1. `main.tex:305` 可在未来纯术语同步中写成 standard training and inference path，
   使其与 3.4 的临时 \(\alpha=0\) 干预更直接区分；当前 3.4 已足以消歧。
2. Equation (8) 的粗体 \(\widehat{\mathbf y},\mathbf y\) 可在未来符号校对中明确为
   complete 20-step windows；现有 \(\mathcal L_{\rm win}\) 说明已足够。

---

## 14. 评分表

评分：1=阻塞，3=可用但需实质修改，4=投稿成熟，5=高度成熟。

| 维度 | 分数 / 5 | 判断 |
|---|---:|---|
| Section 3 内部结构 | **4.9** | contract→architecture→training→interfaces 自然完整 |
| 方法信息路径（正文/公式） | **5.0** | 无 future-weather leakage；direct transition 和 explicit state path 清楚 |
| 训练身份与目标 | **4.7** | student/teacher/target 与三项 loss 分层正确；有两项自包含性 Minor |
| Introduction 承诺兑现 | **5.0** | 逐项兑现，不多不少 |
| Related Work 区别的结构支持 | **4.9** | on-path/removable/fidelity/anchor 均有真实结构 |
| Method→Q1/Q2/Q3 证据映射 | **5.0** | primary/supporting、完整窗口和 subset scope 准确 |
| Limitations/Conclusion 一致性 | **5.0** | 所有必要限制和结论组件均闭合 |
| 术语与符号 | **4.5** | 核心术语稳定；存在 mask 符号复用 |
| 禁止回归控制 | **5.0** | 无 Q4、SOTA、causal、boundary80 或工程语言回归 |
| Figure 2 方法接口 | **2.0** | 图像本体仍传达错误信息路径和算子 |
| Figure 3 证据接口 | **5.0** | frozen primary/supporting 与完整窗口语义一致 |
| AAAI 方法叙事力度 | **4.8** | 正文成熟，不像训练日志或 benchmark 协议 |

除 Figure 2 interface 外，所有核心正文与跨章节维度均不低于 4/5。Figure 2 属于当前
提交版本中的方法载体，不能从总判定中排除，因此不满足 PASS 条件。

---

## 15. 最小修复建议

### 必须修复

只修改 Figure 2 图像本体，使其与现有正文/caption 同构：

1. 将 future weather 从 history/multimodal context 边界彻底移出，只连接
   \(T_\psi\) 的 weather input；
2. 用 weather-prefix + patch-wise geography + horizon condition fusion 和 residual
   state update 替换乘号；
3. 明确每个 \(h\) 从同一 \(z_t\) direct query，不画 recurrent rollout；
4. 将 state readout 输出改为 raster contribution \(r_h\)，显示
   \(b_h+r_h=\widehat y_{t+h}\)；
5. 把 Q2 removal 标在 \(r_h\to+\) 的真实切点；
6. 把 Q3 actual/matched-donor/normalized-mean selector 放在 transition 的 future
   weather 上游；
7. 删除 `D3` 等内部标签。

### 不应修改

- 不改 Section 3 正文或 Equations (1)–(8)；
- 不改 Figure 2 caption 的正确事实边界；
- 不改 Section 4、Figure 3、Table 1–3 或任何结果；
- 不恢复 11,904/boundary80；
- 不新增 recurrent simulator、composition、Q4、causal/counterfactual 或 SOTA
  叙事。

### 修图后的最小回归门禁

1. 只读核对新 Figure 2 的 future-information boundary；
2. 逐项对照 Eq. (2)–(4) 的 condition fusion、residual/direct transition、
   raster readout 和 additive forecast；
3. 核对 Q2/Q3 切点；
4. 核对现有 caption 无需为图降级；
5. 由获授权的独立流程编译并检查 PDF；本轮不编译。

---

## 16. Section 3 局部 SHA

局部 SHA 使用当前 `paper/main.tex` 中从 `\section{Method}` 起，到
`\section{Experiments}` 之前止的原始文本。

| 对象 | 行数 | SHA-256 |
|---|---:|---|
| Section 3 全区块 | 296 | `ac8c836546f41efdddda3be863abf6a22baf2562ce6d92b31405065afc28f6aa` |
| Section 3.1 | 49 | `68324eb4381a776660c61efca5824a543b2f4edcb943a4b9acadf89895cd4321` |
| Section 3.2 | 66 | `1caa0540ce3d1589c0d427769ac529d82afee6b8406aece6777670b22cbad530` |
| Section 3.3 | 90 | `22091590e25134c1467524f34778ea3c6dfdc59155ec20d00e54b3d7231e35bd` |
| Section 3.4 | 58 | `f6891a3bd1cbadf3b1a900387c6ec4b29c3a2769c8e886bb653e68b49ef9b41c` |

审计输入的关键整文件 SHA：

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `1fe12204bad54b2b18a8debd5792cab9dff85a1e342cc35ca8df0e9a2d6eaab9` |
| `paper/main.pdf` | `5f3931e373643d7aa3674fa3517e2e4f1e58f1632bd279b513d11f28bc021691` |
| `MANUSCRIPT_ZH_FULL.md` | `0577238cd6d9561fb9ca7ea9fa4d8275da74a5b5f447e1d0407c4390d66099c6` |
| `paper/references.bib` | `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659` |
| `LIMITATIONS_CONCLUSION_FINAL_AUDIT_20260728.md` | `894c132ef2df438e1fae2ca3d878234b097ba73480239ed67244b7d956d91a3a` |
| Figure 2 当前图像 | `9192e1d0f66253bad3391ac7208a5de91e663586157776fa8c8d30a46aa714f5` |
| Figure 3 frozen PDF | `3b9c764152a867b2d1aef1b82b5661eb18bbd613236cb37dc45d58dfac7f0a53` |

---

## 17. 只读声明

本轮：

- 未修改 `paper/main.tex`；
- 未修改 `paper/main.pdf`；
- 未修改任何 `MANUSCRIPT`；
- 未修改 `paper/references.bib`；
- 未修改 Figure 1–3、Table 1–3；
- 未修改任何实验、证据、代码、模型或数据文件；
- 未运行 LaTeX 编译；
- 唯一写入是新建本报告
  `SECTION3_CROSS_SECTION_REGRESSION_AUDIT_20260728.md`。

Section 3 正文事实继续冻结；待处理对象仅为 Figure 2 图像接口。

# SECTION3_CROSS_SECTION_REGRESSION_REVISE
