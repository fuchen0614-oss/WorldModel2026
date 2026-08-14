# Section 3.4 “Testable Predictive-State Interfaces” 冻结前独立终审

**审计日期：** 2026-07-28  
**审计性质：** 只读终审；除本报告外未修改任何正文、中文稿、PDF、图片、代码或结果文件。  
**审计对象：** `paper/main.tex` 第 3.4 节及 `MANUSCRIPT_ZH_FULL.md` 对应中文。  
**事实优先级：** 冻结结果与 provenance > 实际评测代码 > 冻结方法规范 > 正文与 Section 4 > 中文镜像 > Figure 2 > 旧审计建议。

## 1. 最终结论

**PASS_WITH_MINOR**

- **Critical：0**
- **Major：0**
- **Minor：5**
- **独立视觉阻塞：1 组（Figure 2，未计入正文问题数量）**

修改后的 3.4 已经准确承担“训练完成后如何检验预测状态”的章节功能。它从 3.3 的 future-state alignment 自然过渡到两个无需重训练的训练后接口，并将架构、训练机制、接口定义和实验统计保持在正确层级。

Q2 的状态贡献移除与代码中的 `alpha=0` 完全一致；Q3 的三条天气路径、固定量、完整 20 步预测窗口损失以及损失差方向均与 evaluator 一致。正文没有把显式加法结构本身误写成 load-bearing 证据，也没有将天气响应扩大为因果效应、反事实正确性、极端天气增强、composition 或完整物理状态。

剩余问题均属于不阻塞冻结的术语精化、复现记录自包含性或排版问题，不要求再次打开 3.4 的技术内容。

**3.4_TEXT_FINAL_FROZEN**

此后 3.4 只允许：

- 全篇术语统一；
- 篇幅压缩；
- 引用和排版性调整。

不得改变接口定义、Equation (8)、判据方向或证据边界。

## 2. Critical / Major / Minor 问题表

| 严重度 | 位置 | 原文摘要 | 问题 | 代码/结果依据 | 最小处理建议 | 归属 |
|---|---|---|---|---|---|---|
| Critical | — | — | 未发现 | — | — | — |
| Major | — | — | 未发现 | — | — | — |
| Minor | 3.4，controlled weather-path substitution | “a nonzero, reportable masked forecast-output response statistic” | 与实际 evaluator 的方向一致，但没有直接命名统计量；单独看“nonzero”也可能容纳浮点噪声。由于当前冻结 protocol 没有预设 detectability 阈值，不能事后补门槛。该问题不影响 weather-responsive 定义，因为最终联合判断还要求两条 control 上的可靠正向 fidelity。 | `extreme_state_audit.py:96–100` 实际计算逐 minicube、固定 mask 下的 mean absolute forecast difference；84 对样本的两类响应均为有限正值。 | 3.4 保持冻结。后续仅在 Section 4/Reproducibility 明确统计量名称及报告尺度，不新增事后阈值或显著性门槛。 | Section 4 / Reproducibility |
| Minor | Equation (8) 后 | 从单时距 `\widehat y_{t+h}(u)` 切换为粗体 `\widehat{\mathbf y}(u),\mathbf y` | 上下文和 `\mathcal L_{\rm win}` 定义足以理解，但粗体符号没有单独明说表示完整 20 步预测与真值窗口。 | evaluator 对 `context_len:context_len+target_len` 的全部 20 步展平后计算 masked MSE，见 `extreme_state_audit.py:211–216`。 | 允许在最终全篇符号统一时补一个极短定义；不得改变公式含义或损失方向。 | 3.4 术语/排版校对 |
| Minor | Section 4 的 Q3 protocol 说明及 Figure 2 caption | “season- and geography-matched donor” | 冻结 protocol 还包含 quality matching；3.4 使用 `matched-donor weather` 作为已定义简称本身安全，但 Section 4/图注首次展开不应漏掉 quality。 | `results_ledger.json:281` 将 protocol 记录为 season/geography/quality-matched donor；冻结 protocol 文件保存匹配规则。 | 最终全篇术语统一时，将首次定义校准为 “season-, geography-, and quality-matched donor weather”，后文继续用 matched-donor weather。 | Section 4 / Figure 2 caption |
| Minor | Q3 release provenance | Q3 被描述为与 Q1/Q2 使用同一冻结模型 | 该身份由 release bundle、`EVIDENCE.md` 和 `q3.run.log` 串联支持，但 Q3 原始 JSON 自身没有嵌入 checkpoint SHA 与 evaluator commit。正文主张可保留，但机器可审计链不是完全自包含。 | `results_ledger.json:277–278, 381–395` 明确记录该 gap；release ledger 将其链接到 checkpoint SHA `644deaac…e1acd`。 | 在 Reproducibility/provenance 清单中保留限制，不修改 3.4，不重新生成或“修补”冻结结果。 | Reproducibility |
| Minor | `main.log`，3.4 对应行 | 3.4 两个主体段落 | 存在 Underfull `\hbox`，但无 overfull、公式越界或阅读顺序破坏。 | `main.log` 报告 lines 415–428 badness 3049、lines 430–436 badness 1132；Equation (8) 无 overfull。 | 最终排版阶段通过全篇自然换行处理；不得为此压缩字号、负间距或改动技术含义。 | 排版 |

### 不计入问题数量的视觉阻塞

当前 Figure 2 与正确方法数据流存在多处不一致，标记为：

**VISUAL_BLOCKER — FIGURE 2 ONLY**

该阻塞不影响 3.4 文字冻结；正文与实现是事实基准，不能为了迁就当前图而改错正文。

## 3. Q2 状态贡献干预事实核对表

| 核对项 | 正文表达 | 实际实现/冻结证据 | 判定 |
|---|---|---|---|
| 标准预测 | `\widehat y_{t+h}=b_h+\alpha r_h`，正常路径 `\alpha=1` | `plan_b_b4_exclusive.py:55` 将 `alpha` 注册为值 1 的非可学习 buffer；`:121` 执行 `prior + alpha * residual` | PASS |
| 干预位置 | 在 Equation (4) 加法前临时令 `\alpha=0` | `eval_b4_exclusive_contract.py:57–63` 保存、清零并恢复 `alpha` | PASS |
| 干预输出 | `\widehat y_{t+h}^{remove}=b_h` | evaluator invariant `alpha0_pred_equals_context_prior=true` | PASS |
| 是否重训练 | 无需重训练，同一冻结模型 | context manager 仅临时改变 `alpha` buffer，离开后恢复；`live_weights_restored=true` | PASS |
| 固定量 | 模型、样本、历史上下文、状态构建、transition、readout、真实预测窗口固定 | full 与 alpha-zero arm 复用相同数据、forward components 和 scorer，仅最终 residual scale 改变 | PASS |
| 状态与转移是否仍计算 | 是；仅最终加法移除 `r_h` | `alpha=0` 不删除 `q/P/T/O` 的前向计算 | PASS |
| load-bearing 定义 | 配对预测质量按预期下降，预设不确定性区间排除零 | 与冻结 paired-bootstrap 判据方向一致；Method 没有写入项目内部 `0.005` floor | PASS |
| 架构是否自动证明 load-bearing | 否，必须由干预结果支持 | Section 3.4 使用条件定义；Section 4 分别报告 val/OOD-t 结果 | PASS |
| official 与 paired 统计量 | Method 不混写；Section 4 分开报告 | Validation：official `ΔR²=0.01121`，paired mean `0.01616`，CI `[0.00643,0.02590]`；OOD-t：official `0.01997`，paired mean `0.02200`，CI `[0.01422,0.03018]` | PASS |

### Q2 可支持与不可支持的主张

**可支持：**

- 显式 state-mediated contribution 对预测质量具有可测量的正向贡献；
- 该贡献在冻结 validation 与 OOD-t 协议下满足 load-bearing 定义；
- 状态贡献可以从同一模型的加性预测路径中受控移除。

**不可支持：**

- 所有预测信息都必须经过 `z_t`；
- `z_t` 是完整物理状态；
- 架构中的加法本身已经证明 load-bearing；
- 单凭 Q2 可证明天气响应、因果性或反事实正确性。

## 4. `T\rightarrow I` 证据地位核对

| 核对项 | 事实 | 正文处理 | 判定 |
|---|---|---|---|
| 实际操作 | 将 residual transition 最后一层权重与 bias 临时置零，使 `z_{t+h}=z_t` | “Replacing `T_\psi` by the identity” | PASS |
| 权重恢复 | 干预退出后恢复 live weights | 正文称 post-training interface、无需重训练 | PASS |
| 可支持主张 | learned transition update 参与预测 | 定位为 “supporting diagnostic of transition involvement” | PASS |
| 是否属于 load-bearing 主定义 | 否 | 正文明示 “not part of the load-bearing definition” | PASS |
| 主要混淆 | `O_\omega` 接收未经训练时状态推进产生的 `z_t`，输入分布可能改变 | 正文明示 states outside its trained input distribution | PASS |
| 与 state removal 的证据强度 | 辅助，不能替代 `\alpha=0` 主干预 | 没有并列成同强度主结论 | PASS |

## 5. Q3 三条天气路径与固定量核对表

### 5.1 三条路径

| 路径 | 输入 `T_\psi` 的未来天气 | 其他输入 | 实际含义 | 判定 |
|---|---|---|---|---|
| Actual | 样本自身实际未来天气 `u^{act}` | 自身 `b_h,z_t,g,h,O_\omega` 与 ground truth | 标准预测路径 | PASS |
| Matched donor | 匹配 control minicube 仅提供未来天气 `u^{don}` | 仍使用被评估样本自身的历史、`b_h,z_t,g,h,O_\omega`、mask 与真值窗口 | 受控替换未来天气，不替换 donor 的 EO、地理、状态或真值 | PASS |
| Normalized mean | 全局 z-score 天气空间中的零张量 `u^{mean}` | 其余量与 actual arm 相同 | 归一化均值天气，不是物理量意义上的“零天气” | PASS |

### 5.2 固定量和改变量

| 项目 | 是否固定 | 依据 |
|---|---:|---|
| 冻结模型与 checkpoint | 是 | frozen release bundle；Q3 linkage 见 provenance 限制 |
| 被评估样本 | 是 | donor arm 仍对 extreme/sample E 解码与评分 |
| 历史 EO 与过去天气 | 是 | `_parts` 先缓存 base/state；不同 arm 不重编码历史 |
| `b_h` / `b_{1:H}` | 是 | `_decode` 复用缓存的 base |
| `z_t` | 是 | `_decode` 复用缓存状态 |
| 静态地理 `g` | 是 | donor 只传入 `ufC`，地理仍为 `gE` |
| queried horizon `h` | 是 | 同一完整 20 步 query 和输出窗口 |
| state readout `O_\omega` | 是 | 模型参数冻结 |
| forecast mask 与 ground-truth forecast window | 是 | 三个 arm 对同一 E target/mask 评分 |
| future-weather sequence | **否；唯一改变量** | `ufE`、`ufC` 或 `zeros_like(ufE)` |

正文的固定量列表与实际 evaluator 一致，没有把 donor history、geography、state 或 ground truth 错误带入替换路径。

## 6. Equation (8)、masked loss、detectability 与 fidelity 核对

| 核对项 | 正文定义 | 实现与结果依据 | 判定 |
|---|---|---|---|
| 预测路径 | `\widehat y_{t+h}(u)=b_h+O_\omega(T_\psi(z_t,u_{t+1:t+h},g,h))` | 与标准 `alpha=1` 的 base + residual route 同构；future weather 仅进入 transition/state branch | PASS |
| 是否遗漏 `\alpha` | Equation (8) 不显式写 `\alpha` | 正常推理固定 `\alpha=1`，因此省略不改变 forward | PASS |
| 天气集合 | `u\in\{u^{act},u^{don},u^{mean}\}` | 与 actual/donor/zero-normalized arms 一致 | PASS |
| 预测窗口 | 粗体预测与真值进入 `\mathcal L_{\rm win}` | evaluator 使用完整 target slice，`target_len=20` | PASS；仅有符号定义 Minor |
| mask | “same forecast mask”；20-step masked loss | vegetation × clear-observation mask，覆盖完整 20 步 | PASS |
| 损失差方向 | `ΔL_ctrl=L(control)-L(actual)` | evaluator 的 `dloss=loss_control-loss_actual` | PASS |
| 正值解释 | actual weather 的误差更低 | 数学方向与 evaluator 一致 | PASS |
| 两个 control | fidelity 分别要求 donor 与 mean 上为正 | 冻结结果两者 geo-cluster CI 下界均大于零 | PASS |
| 可靠性 | Section 4 的预设不确定性分析 | primary Q3 criterion 为 geography-cluster bootstrap CI lower bound > 0 | PASS |
| detectability 观察量 | fixed mask 下 forecast-output response | evaluator 是逐 minicube masked mean absolute output difference，不是 latent movement | PASS；统计量命名 Minor |
| weather-responsive 联合定义 | detectable forecast response + 对两条 control 的可靠正向 fidelity | 与冻结 `Q3_RESPONSE_FIDELITY_ONLY` 可支持范围一致 | PASS |

### 6.1 冻结结果方向复核

- Actual vs. matched-donor：`ΔL=0.002565`，geography-cluster 95% CI `[0.001119, 0.003987]`。
- Actual vs. normalized-mean：`ΔL=0.011261`，95% CI `[0.005466, 0.017080]`。
- 两类 forecast-output response 在 84 对样本上均为有限正值；实际统计量为完整 forecast mask 下的 mean absolute forecast difference。
- Hot-dry interaction：`0.000436`，CI `[-0.002162, 0.003200]`，不支持 extreme-specific enhancement。
- 冻结状态为 `Q3_RESPONSE_FIDELITY_ONLY`，而非因果、反事实或极端增强结论。

### 6.2 Detectability 的冻结判断

当前“nonzero, reportable”没有与代码冲突，也没有引入事后阈值。它将 detectability 限定为可观测的 forecast-output response，而非任意 latent movement。由于最终 weather-responsive 定义还要求 actual weather 相对两条 control 的 fidelity 通过预设不确定性分析，浮点噪声不会单独支撑论文核心联合主张。

因此该措辞属于可冻结的描述性接口定义；更精确的统计量名称应放在 Section 4/Reproducibility，而不是重新打开 3.4 或事后创造 threshold。

## 7. Q1 + Q2 + Q3 到核心世界模型主张的证据映射

| 论文问题 | 冻结证据 | 支持的最强表述 | 不支持的表述 |
|---|---|---|---|
| Q1：预测是否有用 | OOD-t `R²=0.56935`，`RMSE=0.15059` | TerraState retains useful forecasting skill under temporal distribution shift. | SOTA；严格跨论文排名；多种子稳定性 |
| Q2：状态贡献是否承载预测 | state removal 在 validation/OOD-t 上均降低 official `R²`；paired intervals 均排除零 | The explicit state-mediated contribution is load-bearing under the frozen protocol. | 所有预测信息都经过状态；完整物理状态 |
| Q3：天气是否通过声明路径影响预测且具有 fidelity | actual/donor/mean 仅替换 `T_\psi` 的天气输入；actual 相对两条 control 的 forecast-window loss 更低，geo-cluster CI 均排除零 | The predictive-state path is weather-responsive under the frozen matched protocol. | causal weather effect；counterfactual correctness；物理真实性 |
| Q1+Q2+Q3 联合 | 有用预测 + 可移除且正向的状态贡献 + 天气路径响应与 fidelity | TerraState exposes a testable predictive state that carries forecast information and responds to supplied future weather. | composition consistency；non-collapse；extreme-specific enhancement；完整环境模拟 |

核心联合主张必须继续以 Q1 的有用预测能力为前提。Q2 不能被 Q3 替代，Q3 也不能挽救失败的 Q2。当前 3.4 的接口层级与这一证据结构一致。

## 8. 3.3—3.4—Section 4—Limitations 边界检查

| 位置 | 应承担的功能 | 当前内容 | 判定 |
|---|---|---|---|
| 3.3 | student/teacher/target 身份；GT/KD/FS 训练目标；训练与推理信息边界 | 解释 future-state alignment 塑造状态，但不独立证明 load-bearing | PASS |
| 3.4 总导入 | 解释为什么训练目标之后仍需训练后检验；定义两个无需重训练的接口 | 准确承接 3.3，无结果、样本数或训练配置 | PASS |
| 3.4 Q2 | 检验问题、受控移除、固定量、操作性判据和边界 | 定义 `alpha=0` 与 load-bearing；T→I 明确降级为 supporting diagnostic | PASS |
| 3.4 Q3 | 三条天气路径、固定量、输出响应、forecast-window fidelity 和非因果边界 | Equation (8) 及联合定义完整 | PASS |
| Section 4 | 数据、control 构造、84 pairs、统计单元、bootstrap、CI、数值与判定 | 具体 protocol 和结果留在实验章节 | PASS；首次 donor 定义需补 quality（Minor） |
| Limitations | 不支持的外推与证据限制 | 明确非因果、非反事实、无 extreme-specific enhancement、无 composition 核心证据 | PASS |

3.3 结尾 → 3.4 开头 → Section 4 的衔接自然。3.4 没有混入 40 epochs、14,880 updates、checkpoint 选择、84 pairs、bootstrap 次数或结果数值。

## 9. AAAI 方法写作质量

### 9.1 段落功能

1. **总导入：** 说明训练目标不能替代训练后机制证据，并引出两个冻结模型接口。
2. **State-contribution intervention：** 检验状态贡献是否改善预测，定义操作、固定量、判据和 T→I 边界。
3. **Controlled weather-path substitution：** 检验 future weather 是否经 state-mediated path 改变预测，并定义 forecast-window fidelity 与主张限制。

三段均遵循“检验问题 → 受控操作 → 固定量 → 观测量/判定 → 证据边界”。Equation (8) 将三条天气路径和损失方向统一起来，明显提升清晰度，没有成为形式负担。

### 9.2 写作质量判断

- 不依赖 Figure 2 或代码即可理解两个接口；
- 没有工程日志式、checkpoint 审计式或 benchmark 式组织；
- 没有把 architecture 写成 proof；
- 没有宣传性或 AI 模板式强主张；
- 防御性限制集中在必要位置，且直接对应证据边界；
- 达到已冻结 3.1–3.3 的事实密度、专业度与段落纯度。

## 10. 中英文、公式编号与编译排版检查

### 10.1 中英文一致性

逐项核对结果：

| 项目 | 一致性 |
|---|---|
| 两个 post-training interfaces、同一冻结模型、无需重训练 | 一致 |
| `alpha=0`、`y_remove=b_h` 与固定量 | 一致 |
| load-bearing 的方向与不确定性条件 | 一致 |
| T→Identity 的 supporting 地位与 OOD-readout 限制 | 一致 |
| actual/donor/mean 三条路径 | 一致 |
| Equation (8) 与 `ΔL` 方向 | 一致 |
| 完整 20 步预测窗口 masked loss | 一致 |
| detectability、fidelity、weather-responsive 联合条件 | 一致 |
| 非因果、非反事实、非极端增强边界 | 一致 |

中文没有擅自增强或削弱英文主张。核心术语已经稳定：

- state-contribution intervention / 状态贡献干预；
- load-bearing / 承载预测；
- identity transition / 恒等转移；
- controlled weather-path substitution / 受控天气路径替换；
- detectable forecast response / 可检测预测响应；
- forecast-window response fidelity / 预测窗口响应保真度；
- weather-responsive predictive state / 天气响应型预测状态。

### 10.2 公式与交叉引用

- `eq:closure` 为 Equation (4)，位于 PDF 第 3 页；
- `eq:interfaces` 为 Equation (8)，位于 PDF 第 4 页；
- 3.4 对 Equation (4) 与 Section 4 的引用均已解析；
- `fig:architecture` 为 Figure 2，位于 PDF 第 6 页；
- 未发现 undefined reference 或 undefined citation。

### 10.3 编译与版面

只读检查最新构建：

- `paper/main.pdf`：10 页，1,103,706 bytes；
- `main.log`：成功写出 PDF；
- LaTeX errors：0；
- undefined citations/references：0；
- overfull boxes：0；
- Equation (8) 溢出：无；
- 3.4 对应 Underfull `\hbox`：2 处，属非阻塞排版问题；
- 双栏阅读顺序：正常；
- Figure 2 浮动至第 6 页，属于独立视觉/浮动体任务，不影响 3.4 文字冻结。

## 11. Figure 2 独立人工修改清单

当前正文与实际实现优先。Figure 2 应由作者按下列项目人工校准：

| 图中当前表达 | 正确表达 | 具体人工修改方式 |
|---|---|---|
| future meteorological forcing 位于 Multimodal context/history encoder 输入边界内 | history encoder 只能读取 historical EO、past weather 与 static geography | 将 future weather 从历史输入分区移出 |
| future weather 与历史模态一起汇入 history encoder | future weather 只能进入 `T_\psi` 的 weather path | 从 future-weather sequence 直接连到 weather encoder/condition fusion/transition |
| weather/state 之间使用乘号式关系 | transition 条件由 weather prefix、patch-wise geography 与 horizon 进行 concat/fusion | 删除乘号，改为 condition-fusion 节点 |
| `z_t` 到 transition 的主状态路径不清楚 | `z_t` 是 transition 的被推进状态 | 明确绘制 `z_t → T_\psi` |
| 没有 residual state update | `z_{t+h}=z_t+\Delta_\psi(\cdot)` | 添加从 `z_t` 到更新后状态的 residual skip/add |
| 容易读成逐步 recursive rollout | 每个 horizon 从同一 `z_t` 执行一次 direct query | 标注 “one direct query per horizon” 或等价简短标签 |
| readout 输出仍像 token grid | `O_\omega` 输出空间 raster contribution `r_h` | 将 readout 后对象改为空间栅格，并标注 `r_h` |
| `b_h` 与 `r_h` 的加法不够明确 | `\widehat y_{t+h}=b_h+r_h` | 添加显式加法节点与两条输入箭头 |
| Q2 位置未落在真实切点 | Q2 在 `r_h` 进入加法之前临时令 `\alpha=0` | 将 state-contribution removal 标在 `r_h → +` 的边上 |
| Q3 controls 更像下游比较框 | Q3 只替换 transition 上游的 future-weather input | 在 `T_\psi` 天气入口前设置 actual/matched-donor/normalized-mean selector |
| `matched donor` 首次展开不完整 | season-, geography-, and quality-matched donor weather | 在图注首次定义中补齐 quality，图内可保持短标签 |
| “D3 Vegetation forecast”等内部标签 | 论文级输出命名 | 删除 D3 等研发标签，保留 land-surface/vegetation forecast |

3.2 对 Figure 2 的一次引用已经足够；3.4 无需为了定位接口而重复引用 Figure 2。

## 12. 冻结结论与 Section 3 闭环

3.4 已满足以下冻结条件：

- 技术事实与 forward/evaluator 一致；
- Q2 主干预与 T→I 辅助诊断层级正确；
- Q3 三条天气路径、固定量和损失方向正确；
- detectability 与 fidelity 没有越过冻结证据；
- 英中语义、符号和主张强度一致；
- 无 Critical 或 Major；
- 现有编译与 Equation (8) 版面不构成阻塞。

因此：

**3.4_TEXT_FINAL_FROZEN**

随着 3.1、3.2、3.3 和 3.4 均完成文字冻结，**Section 3 Method 已形成完整文字闭环**：

> 问题定义与模型概览 → 推理架构 → future-anchored learning → 训练后可检验接口。

当前方法部分只剩：

1. Figure 2 的独立视觉对齐；
2. 全篇术语、caption、复现说明与排版统一校对。

上述剩余事项不得改变已冻结的方法事实、接口定义、公式或证据边界。
