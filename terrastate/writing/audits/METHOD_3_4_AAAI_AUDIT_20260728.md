# Section 3.4 “Testable Predictive-State Interfaces” 修改前独立审计

审计日期：2026-07-28  
审计性质：只读事实核验与写作审计  
审计对象：

- `paper/main.tex` 中 Section 3.4；
- `MANUSCRIPT_ZH_FULL.md` 中对应中文；
- 冻结的 Sections 3.1–3.3、Section 4、Figure 2 及图注；
- Q2/Q3 评测代码、冻结结果、selection record 与 provenance；
- 最新 `main.log` 与 `main.pdf`。

事实优先级：

> 冻结结果 JSON 与 checkpoint provenance  
> \> 实际评测代码  
> \> 冻结方法规范  
> \> 正文公式与实验结果  
> \> Figure 2  
> \> 旧写作意见

## 1. 最终结论

**REVISE**

当前 3.4 不需要重新设计方法，也不需要明显重组。其基本结构已经合理：一段总导入、一个状态贡献接口、一个天气路径替换接口。Q2、\(T\!\to\!I\) 和 Q3 的实际操作在正文中均未出现根本性事实错误。

但本节尚不能冻结，原因是两个核心判定定义仍不够操作化：

1. `load-bearing` 目前仅定义为 “measurable loss of forecast quality”，没有明确区分预测质量下降的方向、配对统计量与不确定性要求；
2. `detectable response` 与 `forecast-window response fidelity` 尚未明确对应实际 evaluator 使用的输出变化统计量、完整 20 步窗口损失以及 actual 相对两个冻结 control 的方向。

这些不是遣词偏好，而是本节作为“可检验接口”所必须闭合的定义。修订应保持最小范围，不引入结果数值、阈值、样本数或 bootstrap 细节。

问题计数：

- **Critical：0**
- **Major：2**
- **Minor：4**

Figure 2 仍有多项视觉事实错误，但这些错误不应反向改变正确正文；它们单独列为后续人工修图事项，不计入上述正文问题数量。

## 2. Critical / Major / Minor 问题表

| 级别 | 位置 | 当前原文摘要 | 问题 | 代码/结果证据 | 最小修改建议 | 归属 |
|---|---|---|---|---|---|---|
| Major | `main.tex` 3.4，State-contribution intervention | “load-bearing if … a measurable loss of forecast quality” | “measurable” 未说明方向、统计单位与不确定性，容易形成循环定义：只要作者称某变化可测即可。它也未区分 official dataset-level \(\Delta R^2\) 与 paired effect。 | Q2 evaluator 分别计算 full/alpha0 的 dataset-level 指标和逐 minicube paired effect；冻结结果中 validation official \(\Delta R^2=0.01121\)，paired mean \(=0.01616\)，CI \([0.00643,0.02590]\)；OOD-t official \(\Delta R^2=0.01997\)，paired mean \(=0.0220\)，CI \([0.01422,0.03018]\)。 | 在 3.4 只定义：移除 \(r_h\) 后，配对预测质量必须沿预期方向下降，且预先指定的不确定性区间排除零。具体指标、CI 构造及任何项目内部阈值留在 Section 4。明确 \(T\!\to\!I\) 不参与主定义。 | 3.4；统计细节归 Section 4 |
| Major | `main.tex` 3.4，Controlled weather-path substitution | “detectable when weather substitution changes the forecast”；“actual weather yields lower masked loss … than the prespecified control weather paths” | detectability 仅写“发生变化”过弱，任意数值扰动都可满足；fidelity 未明确是 control-minus-actual 的正向差异，也未明确必须分别相对 matched-donor 和 normalized-mean controls 成立。 | Q3 evaluator 对每个 minicube 计算 actual 与 control 预测之间的 masked mean absolute output difference；fidelity 使用完整 20 步预测窗口的 masked MSE，并分别比较 actual-vs-donor 与 actual-vs-mean；冻结主判据要求两个 geography-cluster bootstrap CI 的下界均大于零。 | 定义 masked forecast-response statistic，并将 fidelity 写为 \(\Delta L_{\rm ctrl}=L_{\rm win}({\rm ctrl})-L_{\rm win}({\rm actual})>0\)，分别针对两个预冻结 control；是否显著及 bootstrap 细节留 Section 4。 | 3.4；统计细节归 Section 4 |
| Minor | `main.tex` 3.4 开场 | “TerraState exposes two post-training interfaces on the same selected model.” | “selected model”带有实验审计语气；开场也没有明确说明为什么 3.3 的训练目标之后仍需接口检验。 | 3.3 已明确 future-state alignment 不能单独证明 load-bearing；Q2/Q3 都是训练后、无需重训练的干预。 | 改为目的优先的过渡，例如：训练目标塑造状态，但不能独立证明状态参与预测或响应天气；因此在同一冻结模型上定义两个无需重训练的接口。 | 3.4 |
| Minor | `main.tex` 3.4，天气接口固定量列表 | “evaluated sample, and target” | `target` 容易与 3.3 的 future-state target encoder 混淆；固定量列表未显式包含 queried horizon。 | Q3 evaluator 对同一 minicube、相同 ground-truth 20 步窗口与相同 horizon queries 运行三条天气路径；未来状态 target encoder 不参与 Q3。 | 将 `target` 改为 `ground-truth forecast window` 或 `evaluation target`，并在固定量中加入 horizon/query。 | 3.4 |
| Minor | `main.tex` 3.4，天气控制 | “prespecified control weather paths” | 作为方法接口，正文没有给出两条 control 的最小身份，读者需跳到 Section 4 才知道替换什么。 | 冻结 Q3 只有 actual、season/geography/quality-matched donor 与 normalized-mean 三条路径；normalized mean 是全局 z-score 空间中的零。 | 在 3.4 首次命名 `matched-donor weather` 与 `normalized-mean weather`，只说明身份，不写 84 pairs、匹配特征或 bootstrap。 | 3.4；构造细节归 Section 4 |
| Minor | Q3 provenance / Section 4 reproducibility | 3.4 声称两个接口作用于同一模型 | 该主张由冻结 release bundle 和运行日志支持，但当前 Q3 原始 JSON 没有自包含 checkpoint SHA 与 evaluator commit，单看 JSON 无法机械复核同一模型身份。不是 3.4 的方法文字错误，但属于发布级 provenance 缺口。 | `selection_record.json` 冻结 step 11,904 checkpoint 及 SHA；Q2 JSON 内含 checkpoint 身份；Q3 linkage 主要来自 release `EVIDENCE.md`/run log，而非 Q3 JSON 自身。 | 保留 3.4 的“同一冻结模型”表述；在 Section 4/Reproducibility 或最终 release manifest 中补齐 Q3 checkpoint SHA、evaluator commit 和 protocol ID。不要把 SHA 写入 3.4。 | Section 4 / Reproducibility |

### 不构成问题的内容

- 3.4 没有混入 40 epochs、14,880 updates、warm-start、checkpoint 路径或模型选择细节；
- 3.4 没有恢复 Q4/composition、non-collapse、因果效应、反事实正确性或完整物理状态主张；
- \(T\!\to\!I\) 已被正确降级为 supporting diagnostic；
- 当前 3.4 将 extreme-weather subset、84 pairs、cluster bootstrap 和结果数字留在 Section 4，边界正确；
- 非因果与非反事实的限定是必要证据边界，不属于过度防御。

## 3. AAAI 方法写作锚点与组织方式

本审计只借鉴写作动作，不迁移其他论文的技术主张。

### 3.1 Learning Hybrid Dynamics Models with Simulator-Informed Latent States（AAAI 2024）

官方来源：[AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/29075)

- 段落功能顺序：先定义状态与输出关系，再说明模型机制，最后将可验证性质与经验评估分开；
- 对 3.4 的帮助：干预接口应明确“改变什么、保持什么、观察什么”，而不是直接写结果；
- 可借鉴动作：用紧凑数学关系固定干预对象，并把统计协议留给实验章节；
- 不可借用主张：TerraState 没有 simulator-informed physical latent state，也不声称物理可观测性或完整动力学恢复。

### 3.2 Latent Space Explanation by Intervention（AAAI 2022）

官方来源：[AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/19948)

- 段落功能顺序：先把 intervention 定义为对训练后表示的受控操作，再评估下游输出差异；
- 对 3.4 的帮助：应把 Q2/Q3 写成固定模型上的操作接口，并明确输出响应统计量；
- 可借鉴动作：分开 intervention definition 与 empirical criterion；
- 不可借用主张：本文不能借用概念级解释、因果干预或反事实语义。

### 3.3 Drive-OccWorld（AAAI 2025）

官方来源：[AAAI Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/33010)

- 段落功能顺序：任务形式化后给出方法总览，再按模块说明状态、条件与输出；
- 对 3.4 的帮助：3.4 应保持为 3.2–3.3 之后的紧凑方法接口，不能扩张成完整实验协议；
- 可借鉴动作：先用一句话定位接口在整体模型中的作用，再分模块说明；
- 不可借用主张：TerraState 不采用其递归生成、动作控制或占据世界模拟主张。

锚点共同支持的组织原则是：

> 检验问题 → 受控操作 → 固定量 → 观测量/判定含义 → 证据边界

当前 3.4 已具备该结构的骨架，但“观测量/判定含义”仍需补足。

## 4. Q2 状态贡献干预事实核对表

| 项目 | 核验结论 |
|---|---|
| 主操作 | 在最终加法前临时令 \(\alpha=0\)，移除 \(\alpha r_h\)。 |
| 实际代码位置 | `eval_b4_exclusive_contract.py` 中 `_alpha_zero` 临时保存、置零并恢复 alpha；`plan_b_b4_exclusive.py` 中最终输出为 `prior + alpha * residual`。 |
| 固定量 | 同一冻结模型、同一样本、历史 EO、过去天气、静态地理、history operator、\(b_h\)、\(z_t\)、\(T_\psi\)、\(O_\omega\) 与预测目标均保持不变。 |
| 改变量 | 只改变加法前的标量门 \(\alpha:1\to0\)。 |
| 干预输出 | \(\widehat y_{t+h}^{(-r)}=b_h\)，代码 invariant 检查确认 alpha-zero 输出与 context-only forecast 一致。 |
| 主要统计量 | official dataset-level \(\Delta R^2\) 与逐 minicube paired effect/CI 是不同统计量，必须分开报告。 |
| 可支持主张 | 若移除状态贡献导致配对预测质量可靠下降，则显式状态路径对预测是 load-bearing；这表明 \(r_h\) 提供可测量的额外预测贡献。 |
| 不可支持主张 | 不能证明所有预测信息都经过 \(z_t\)；不能证明 \(z_t\) 是完整物理状态；不能证明因果表示或反事实正确性。 |
| 是否需要重训练 | 否。操作作用于同一冻结模型的 forward path。 |

### \(T\!\to\!I\) 支持性诊断

| 项目 | 核验结论 |
|---|---|
| 实现 | evaluator 将 transition residual delta 的最终映射置零，使 \(z_{t+h}=z_t\)。 |
| 固定量 | 输入样本、history operator、\(z_t\)、readout 及其他参数保持不变。 |
| 实际变化 | 取消 learned transition update，但仍运行 readout。 |
| 可支持主张 | 支持 learned transition 参与最终预测。 |
| 关键限制 | \(O_\omega\) 接收未按训练方式推进的状态，可能处于训练输入分布之外。 |
| 结论地位 | 只能是 supporting diagnostic；不能替代 state-contribution removal，也不应成为 load-bearing 的必要定义。 |

### `load-bearing` 的推荐最小定义

3.4 应只定义判定逻辑，不写数字或项目内部阈值：

> A state-mediated contribution is load-bearing when removing \(r_h\) degrades paired forecast quality in the expected direction and the prespecified uncertainty interval excludes zero.

Section 4 再规定指标、统计单位、confidence interval 和报告方式。内部 `0.005` 等 gate 不应包装成领域通用标准。

## 5. Q3 受控天气路径替换事实核对表

| 项目 | Actual weather | Matched-donor weather | Normalized-mean weather |
|---|---|---|---|
| 历史上下文 | 固定 | 与 actual 完全相同 | 与 actual 完全相同 |
| \(b_{1:H}\)、\(z_t\) | 固定 | 复用 actual 样本的缓存值 | 复用 actual 样本的缓存值 |
| 静态地理 \(g\) | 固定 | 使用 actual 样本的地理条件，不替换 | 使用 actual 样本的地理条件，不替换 |
| horizon/query | 固定 | 固定 | 固定 |
| readout \(O_\omega\) | 固定 | 固定 | 固定 |
| evaluation sample / ground truth | 固定 | 固定 | 固定 |
| 输入 \(T_\psi\) 的未来天气 | actual 样本的真实未来天气 | 来自 season/geography/quality-matched donor 的未来天气 | 全局 z-score 标准化空间中的零，即 normalized mean |
| 预测路径 | \(b_h+O_\omega(T_\psi(z_t,u^{\rm act},g,h))\) | \(b_h+O_\omega(T_\psi(z_t,u^{\rm don},g,h))\) | \(b_h+O_\omega(T_\psi(z_t,u^{\rm mean},g,h))\) |

### 5.1 匹配与替换对象

- donor 匹配使用硬性 season 约束，并在日期、经纬度、植被比例、历史云量/有效比例、历史 NDVI 与未来有效比例等冻结特征上匹配；
- donor 只提供未来天气序列，不替换 actual 样本的 EO 历史、空间状态、地理条件、readout 或 ground truth；
- normalized mean 是经过冻结 normalizer 后的零向量，不是原始物理单位中的零天气；
- 84 个 extreme-weather matched pairs、45 个唯一 controls、31 个 geography clusters 与 10,000 次 bootstrap 属于 Section 4，不应进入 3.4。

### 5.2 Masked loss 与统计单元

| 项目 | 实际定义 |
|---|---|
| 预测误差 | 每个 minicube 上，针对完整 20 步未来窗口计算 vegetation × clear-observation mask 下的 masked MSE。 |
| 注意 | evaluator 中历史函数名含 `endpoint`，但实现会展平全部时间与空间元素；正文必须使用 `20-step forecast-window masked loss`，不能写 endpoint loss。 |
| detectability 统计 | 每个 minicube 上，actual 与 control 预测之间的 masked mean absolute forecast difference。 |
| fidelity 差异 | \(\Delta L_{\rm ctrl}=L_{\rm win}({\rm ctrl})-L_{\rm win}({\rm actual})\)。正值表示 actual weather 的预测窗口误差更低。 |
| 主要统计单元 | matched minicube pair；不确定性按 geography cluster bootstrap。 |
| 主判据 | actual 相对 matched-donor 与 normalized-mean 两条 control 的 \(\Delta L\) 均为正，且各自预先指定的区间排除零。 |

### 5.3 可支持与不可支持的主张

| 类型 | 内容 |
|---|---|
| 可支持 | 替换未来天气会通过状态路径改变预测；在冻结 matched subset 上，actual weather 相比 matched-donor 和 normalized-mean controls 产生更低的完整 20 步预测窗口 masked loss；这支持 detectable weather response 与 forecast-window response fidelity。 |
| 在 Q2 同时成立时可支持 | TerraState 暴露出一个承载预测且响应天气条件的可检验预测状态。 |
| 不可支持 | 因果天气效应、正确反事实、完整物理状态、真实气象机制识别。 |
| 不可支持 | hot-dry extreme-specific enhancement。interaction CI 跨零只否定“额外极端增强效应”，不否定已经成立的 actual-vs-control fidelity。 |

## 6. Detectability、fidelity 与 weather-responsive 的定义审查

### Detectability

当前“weather substitution changes the forecast”表达方向正确，但不足以作为冻结定义。浮点级微小变化也满足“changes”。建议把它约束为：

> 在固定 forecast mask 上，actual 与 control weather paths 产生非零并可报告的 masked forecast-response statistic。

3.4 不必给阈值，但需要说清观察量是输出响应，而不是任意内部数值变化。

### Forecast-window response fidelity

当前完整 20 步窗口口径正确。建议将方向写明：

> actual weather 相比每条预冻结 control weather path 产生更低的完整预测窗口 masked loss，即 control-minus-actual loss 为正。

“每条 control”很重要，因为冻结 Q3 要求 actual 同时优于 matched donor 和 normalized mean。

### Weather-responsive predictive state

可保留组合定义，但应避免将最终 Q3 输出响应写成“latent state 已被直接测量”。准确表述是：

1. 天气替换通过 exclusive state-mediated path 产生可检测的 forecast response；
2. actual weather 相对两条 control 具有正向 forecast-window fidelity。

该组合与冻结 Q3 结果一致。它支持 weather-responsive predictive state，但不支持 causal、counterfactual 或 physical correctness。

## 7. Q2 + Q3 到“可检验预测状态世界模型”的证据映射

| 方法主张 | 所需接口 | 观测证据 | 支持强度 | 不能推出 |
|---|---|---|---|---|
| 状态贡献显式进入最终预测 | 架构加法 \(\widehat y=b_h+r_h\) | Q2 可在同一模型中移除 \(r_h\) 并精确恢复 \(b_h\) | 结构事实 | 不代表 \(r_h\) 必然有用 |
| 状态路径承载预测 | Q2 state-contribution removal | 移除后配对预测质量可靠下降 | load-bearing state-mediated contribution | 不代表全部预测信息都经过状态 |
| learned transition 参与预测 | \(T\!\to\!I\) | identity substitution 降低预测质量 | 支持性证据 | 不能单独证明 load-bearing；存在 readout 分布偏移 |
| 模型预测响应未来天气 | Q3 weather substitution | actual/control 输出具有可检测差异 | detectable driver response | 不等于响应方向正确 |
| actual weather 的响应具有预测保真度 | Q3 actual vs matched donor/mean | actual 在完整预测窗口上对两条 control 均具有更低 masked loss | forecast-window response fidelity | 不等于因果或反事实正确 |
| 可检验、承载预测且响应天气的 predictive-state world model | Q1 + Q2 + Q3 | Q1 保证预测有用；Q2 支持状态贡献；Q3 支持天气响应及预测保真度 | 论文允许的核心联合主张 | 不支持完整物理世界状态、composition、non-collapse 或 causal simulator |

Q1 不能被 Q2/Q3 替代：若基础预测无用，内部干预的论文意义会显著下降。3.4 只定义 Q2/Q3 接口；Q1 及其数值应保留在 Section 4。

## 8. 3.3—3.4—Section 4—Limitations 边界检查表

| 内容 | 3.3 | 3.4 | Section 4 | Limitations |
|---|---:|---:|---:|---:|
| Student / KD teacher / future-state target encoder 身份 | 保留 | 不重复 | 只给实现必要信息 | 否 |
| \(\mathcal L_{\rm GT}+0.5\mathcal L_{\rm KD}+\lambda_s\mathcal L_{\rm FS}\) | 保留 | 不重复 | 训练配置可简述 | 否 |
| future-state alignment 不能单独证明 load-bearing | 结尾铺垫 | 接续并定义 Q2 | 报告 Q2 | 可总结限制 |
| 同一冻结模型、无需重训练的接口 | 否 | 保留 | 给 provenance | 否 |
| \(\alpha=0\) 移除 \(r_h\) | 否 | 保留 | 给指标、CI 与结果 | 否 |
| \(T\!\to\!I\) 及分布偏移限制 | 否 | 简洁保留 | 报告辅助结果 | 可重申局限 |
| actual / matched-donor / normalized-mean 三条路径 | 否 | 最小命名 | 完整构造与匹配协议 | 否 |
| 完整 20 步窗口 masked loss | 否 | 定义 estimand | 给 mask、统计单位、CI | 否 |
| 84 pairs、匹配字段、cluster bootstrap | 否 | 不放 | 保留 | 否 |
| Q1/Q2/Q3 数字和 PASS/PARTIAL 判定 | 否 | 不放 | 保留 | 否 |
| hot-dry interaction CI 跨零 | 否 | 不放 | 如需报告则诚实报告 | 用于限制 extreme-specific 解释 |
| 非因果、非反事实、非完整物理状态 | 否 | 天气接口末尾一句 | 结果解释保持限定 | 系统总结 |
| composition/Q4、non-collapse | 不恢复 | 不恢复 | 非核心/不报告 | 可说明未验证 |

### 衔接判断

- **3.2 → 3.3：** 架构之后解释如何学习状态，衔接成立；
- **3.3 → 3.4：** 逻辑上应明确“训练锚定不等于经验上 load-bearing”，当前已有含义，但 3.4 开场可更自然地接住；
- **3.4 → Section 4：** 当前已把 control construction 和 statistical tests 指向 Section 4，边界正确；
- **3.4 → Limitations：** 3.4 只需保留非因果/非反事实的一句界限，极端增强失败及更广泛限制由 Limitations 承担。

## 9. 是否需要数学公式

### 结论

**建议增加一个紧凑的天气路径公式；Q2 只需保留最小干预等式。**

原因：

- Q2 的 \(\alpha=0\) 与 \(\widehat y^{(-r)}=b_h\) 已足够清楚；
- Q3 当前依靠长固定量列表，容易让读者忽略“只有 \(u\) 改变”的核心控制；
- 一个公式可以同时固定三个 weather arms、共同历史状态和相同 readout，不是为了形式感增加符号。

### 推荐最小形式

\[
\widehat y_{t+h}(u)
=
b_h+O_\omega\!\left(T_\psi(z_t,u_{t+1:t+h},g,h)\right),
\qquad
u\in\{u^{\rm act},u^{\rm don},u^{\rm mean}\}.
\]

随后用一行或行内定义 fidelity 方向：

\[
\Delta L_{\rm ctrl}
=
L_{\rm win}\!\left(\widehat y(u^{\rm ctrl}),y\right)
-
L_{\rm win}\!\left(\widehat y(u^{\rm act}),y\right),
\qquad
{\rm ctrl}\in\{{\rm don},{\rm mean}\}.
\]

解释要求：

- \(L_{\rm win}\) 是完整 20 步预测窗口的 masked loss；
- 正的 \(\Delta L_{\rm ctrl}\) 表示 actual weather 更忠实；
- 是否可靠为正由 Section 4 的预先指定不确定性分析判定；
- 3.4 不应加入 84 pairs、bootstrap 次数或结果数字。

若版面紧张，可只保留第一式，把 \(\Delta L_{\rm ctrl}\) 用一句自然语言说明。无需为 detectability 再增加第三个 display equation。

## 10. Figure 2 与 3.4 接口的人工对齐清单

当前 Figure 2 不能作为方法事实来源。以下为后续人工修改项：

| 图中当前表达 | 正确表达 | 具体人工修改方式 |
|---|---|---|
| Future meteorological forcing 位于 “Multimodal context” 内，并与历史输入共同进入 history encoder | future weather 不进入 \(q_\theta\) | 将 future-weather 模块移出历史上下文边界；删除其指向 history encoder 的箭头 |
| 历史编码器输入边界含糊 | \(q_\theta\) 只接收 historical EO、recorded masks、past weather 和 static geography | 在 history encoder 左侧重新整理输入分区，并明确 future information 不在其中 |
| future weather 与状态通过乘号组合 | weather prefix、patch-wise geography 与 horizon 经 condition fusion 后条件化 transition | 删除乘号；改成 concat/fusion 节点，并分别标明 weather、geography、horizon |
| geography 看起来是全局统一条件 | \(E_g(g)_i\) 是 patch-wise，weather/horizon 广播到各 patch | 在 geography 分支注明 patch-wise；在 fusion 后用 indexed condition 或 patch-wise cue 表达 |
| \(z_t\) 到 \(T_\psi\) 的主箭头不清楚 | \(z_t\) 是 transition 的状态输入 | 画出明确的 \(z_t\rightarrow T_\psi\) 实线箭头 |
| transition 像一次黑盒替换 | \(z_{t+h}=z_t+\Delta_\psi(\cdot)\) | 在 transition 模块中增加 residual skip 或简短 residual-update 标注 |
| 容易被理解为递归 rollout | 每个 \(h\) 从同一个 \(z_t\) 执行一次 direct transition | 标注 “one direct query per horizon”；不要画 \(z_{t+1}\to z_{t+2}\) 链 |
| state readout 输出仍像 token grid | \(O_\omega\) 输出空间 raster contribution \(r_h\) | 将 readout 后对象画成 raster，并标注 \(r_h\) |
| 最终预测加法关系不够显式 | \(\widehat y_{t+h}=b_h+r_h\) | 增加显式加法节点，并让 \(b_h\) 与 \(r_h\) 分别进入 |
| Q2 切点位置缺失或模糊 | 在 \(r_h\) 进入加法前临时令 \(\alpha=0\) | 在 \(r_h\to+\) 的边上标出 state-contribution removal，不切断 \(z_t\) 或 \(T_\psi\) |
| Q3 weather arms 与 transition 输入位置不一致 | actual / matched donor / normalized mean 只替换 \(T_\psi\) 的 future-weather input | 将三条天气路径放在 weather encoder/transition 上游，其他路径保持共用 |
| 图内出现 D3 等工程标签 | 正文只使用 Q2/Q3 的学术术语 | 删除 D3 及内部研发名称 |
| 图可能暗示天气替换是因果干预 | 这是 controlled diagnostic substitution | 在验证侧栏或 caption 中保留非因果限定，不使用 causal/counterfactual 图标或措辞 |

3.4 可在 Figure 2 完成人工修正后增加一次轻量引用，用于帮助读者定位 Q2/Q3 切点。目前图存在事实错误，不建议为了建立引用而让正文迎合现图。

## 11. 中英文一致性检查

### 结论

英文与中文 3.4 在当前主张强度、公式含义和证据边界上总体一致，没有发现中文擅自增强结论。

| 项目 | 英文 | 中文 | 结论 |
|---|---|---|---|
| 同一模型、无需重训练 | same selected model; without retraining | 同一个选定模型；无需重新训练 | 语义一致；共同建议改为“同一冻结模型” |
| Q2 操作 | set \(\alpha=0\) before addition | 在加法前令 \(\alpha=0\) | 一致 |
| 恢复 \(b_h\) | exactly recovering \(b_h\) | 精确恢复 \(b_h\) | 一致 |
| \(T\!\to\!I\) 地位 | supporting diagnostic | 支持性诊断 | 一致 |
| readout 分布风险 | outside trained input distribution | 训练分布之外 | 一致 |
| Q3 固定量 | context, \(b\), \(z_t\), geography, readout, sample, target | 同项固定量 | 一致；两者都应将 target 改为 evaluation target/真实预测窗口 |
| 完整 20 步窗口 | complete 20-step forecast window | 完整 20 步预测窗口 | 一致 |
| weather-responsive | detectable + positive fidelity | 可检测变化 + 正向保真度 | 一致，但两者都需操作化 |
| 非因果/非反事实 | explicit limitation | 明确限定 | 一致 |

修订时建议固定译法：

- `state-contribution removal`：状态贡献移除；
- `load-bearing predictive state`：承载预测的预测状态，首次可括注 load-bearing；
- `identity transition`：恒等转移；
- `controlled weather-path substitution`：受控天气路径替换；
- `detectable forecast response`：可检测的预测响应；
- `forecast-window response fidelity`：预测窗口响应保真度；
- `weather-responsive predictive state`：响应天气条件的预测状态。

## 12. 编译与排版只读检查

- 最新 `paper/main.pdf`：**10 页**；
- 3.4 位于 PDF 第 **4 页**；
- Figure 2 位于 PDF 第 **6 页**，距离 3.4 较远；该浮动位置属于后续图稿/版面问题，不是 3.4 文字事实问题；
- `main.log` 未发现 LaTeX error；
- 未发现 undefined citation；
- 未发现 undefined reference；
- 未发现 overfull box；
- 存在若干其他页面的 underfull box/vbox 提示，但 3.4 对应行没有独立溢出警告；
- 当前 PDF 可正常阅读，3.4 没有明显公式或双栏断裂问题；
- 本轮未重新编译，也未修改 PDF。

## 13. 最小修改方案

审计支持以下三部分结构，不需要 `RESTRUCTURE`：

### 13.1 总导入

功能：

1. 承接 3.3：future-state alignment 塑造状态，但不能独立证明状态实际参与预测或正确响应天气；
2. 定义两个作用于同一冻结模型、无需重训练的 post-training interfaces；
3. 不在此列结果、阈值或数据集。

### 13.2 State-Contribution Intervention

按以下顺序：

1. 检验问题：显式状态贡献是否实际改善预测；
2. 受控操作：在加法前临时令 \(\alpha=0\)，得到 \(b_h\)；
3. 固定量：相同模型、样本、历史上下文、状态计算、transition、readout 与目标；
4. 判定含义：配对预测质量沿预期方向下降，预先指定的不确定性区间排除零；
5. 证据边界：只支持 state-mediated contribution；\(T\!\to\!I\) 是 supporting diagnostic，且存在 readout 分布偏移。

具体 official \(\Delta R^2\)、paired effect、CI、内部 gate 和结果全部留 Section 4。

### 13.3 Controlled Weather-Path Substitution

按以下顺序：

1. 检验问题：未来天气是否通过声明的状态路径影响预测，并具有预测窗口保真度；
2. 最小公式：只改变 \(u\)，固定 \(b_h,z_t,g,h,O_\omega\)、样本与 ground-truth window；
3. 三条路径：actual、matched donor、normalized mean；
4. detectability：用 masked forecast-response statistic 描述；
5. fidelity：actual 相对两个 control 的完整窗口 masked loss 均更低，方向为 control-minus-actual；
6. 证据边界：构造、matched subset 和 bootstrap 在 Section 4；不支持因果、反事实或 extreme-specific enhancement。

## 14. 冻结判断

当前 3.4 **尚不可冻结**。

需要关闭的可验证条件仅有：

1. `load-bearing` 定义明确包含配对下降方向与预先指定不确定性，而不把项目内部阈值写入 Method；
2. `detectability` 对应实际 masked forecast-response statistic；
3. `fidelity` 明确为完整 20 步窗口上 actual 相对 matched donor 与 normalized mean 两条 control 的正向 loss 差；
4. `target` 改为无歧义的 evaluation target 或 ground-truth forecast window；
5. 开场从“selected model 审计”改成由 3.3 自然引出的科学目的。

完成上述最小修订后，3.4 可进入独立冻结终审。Figure 2 的事实错误应作为单独视觉 blocker 处理，不阻止正确的 3.4 文字先行修订。

