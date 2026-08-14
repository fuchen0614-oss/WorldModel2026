# TerraState 全局定位增强回归审核

**审核日期：** 2026-07-28  
**审核性质：** 只读回归审核，不重新判断研究方向，不修改论文、图、代码或结果  
**审核对象：** 当前英文正文、中文镜像、Section 3 最终审计、冻结结果与证据映射、当前编译产物  
**事实优先级：** 冻结结果与 provenance > 实际代码 > 3.1–3.4 最终审计 > 冻结方法规范 > 当前正文 > 中文镜像 > 定位审计建议

## 1. 最终结论

**PASS_WITH_MINOR：定位增强安全，可以冻结。**

- **Critical：0**
- **Major：0**
- **Minor：1**

唯一 Minor 是表达增强后当前日志新增了 1 处 underfull `\vbox` 和 3.4 附近 2 处 underfull `\hbox`。它们没有造成 overfull、文字裁切、公式越界、引用失败、页数增加或双栏阅读顺序破坏，属于最终排版阶段可以处理的非阻塞问题。

未发现：

- 方法事实变化；
- 公式、符号、label 或编号变化；
- 训练身份或输入权限变化；
- Q1/Q2/Q3 证据边界扩大；
- Section 4 数字、表格、统计协议或实验解释被误改；
- Figure 2 图像本体被修改；
- 中英文主张强度不一致；
- 未经授权的大段重写。

**POSITIONING_PASS_FINAL_FROZEN**

方法事实和证据边界继续保持冻结。可以开始 Section 4 系统审计。此后只允许根据 Section 4 审计进行全篇术语、复现说明和篇幅校准，不再重新寻找 Section 3 主线。

---

## 2. 审核材料与完整性

### 2.1 完整读取的材料

| 材料 | 审核用途 | 当前状态 |
|---|---|---|
| `paper/main.tex` | 英文事实、公式、主张、caption、Limitations、Conclusion | 已完整读取 |
| `MANUSCRIPT_ZH_FULL.md` | 中文镜像与主张强度 | 已完整读取 |
| `METHOD_GLOBAL_POSITIONING_AUDIT_20260728.md` | 定位增强允许范围与措辞目标 | 已完整读取 |
| `METHOD_3_2_FINAL_AUDIT_20260728.md` | 架构与公式冻结基准 | 已完整读取 |
| `METHOD_3_3_FINAL_AUDIT_20260728.md` | 三种训练身份、损失与信息边界 | 已完整读取 |
| `METHOD_3_4_FINAL_AUDIT_20260728.md` | Q2/Q3 接口、统计方向与证据边界 | 已完整读取 |
| 当前 3.1 英文与中文正文 | 已冻结总体合同 | 已完整读取；项目中无单独的 3.1 final-audit 文件 |
| `evidence_workspace/results_ledger.json` | 冻结数值、判据与 provenance | 已完整读取 |
| `evidence_workspace/CLAIM_EVIDENCE_MAP.md` | claim–evidence 边界 | 已完整读取 |
| `paper/main.log` | 编译、引用与排版回归 | 已完整读取 |
| `paper/main.pdf` | 10 页实际版面、公式、图表和阅读顺序 | 已逐页检查 |
| Figure 1–3 captions | 图文术语与证据边界 | 已检查 |
| Limitations 与 Conclusion | 限制可见性与正向收尾 | 已检查 |

### 2.2 当前关键文件 SHA-256

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `acc746810e8a9cb3019353b3042d2198b0b32195e6917c7616f6e916af30a554` |
| `MANUSCRIPT_ZH_FULL.md` | `7778930a88394908a1e5a308923b5b0d874046c6e934db92925b8fa327249f70` |
| `paper/main.log` | `23aba9c4f933907605bde84bb1fc4fb2d8300c80abfe5c4dad76d2c613822191` |
| `paper/main.pdf` | `ef708c2d223f8da290b6a43c3a1a3c8e4ffd2e5ee951eaa3ee0d602ecb018ff7` |
| `paper/references.bib` | `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659` |
| `evidence_workspace/results_ledger.json` | `d1f8ec7d7a51fae87afc8ba9dbc27905c6816434dc5554980d2e7c2eb472c4b2` |
| `evidence_workspace/CLAIM_EVIDENCE_MAP.md` | `d84ab20e8c470e732b7fd64f51575909949b3590366362067548c32d1559c88f` |

### 2.3 修改范围比对依据

工作目录不是可用的 Git 历史仓库，因此本次没有把 `git diff` 当作修改范围证据。范围核对采用：

1. 当前正文与 `METHOD_GLOBAL_POSITIONING_AUDIT_20260728.md` 的逐项对应；
2. 当前 PDF 与定位增强前编译留档 `/tmp/terrastate_cite_audit/build/main.pdf` 的逐页文本差异；
3. 当前与留档 `.fls` 中 Figure 1–3 的实际 include 路径；
4. 图像文件 SHA 和修改时间；
5. 当前 Section 4 数字、表格与冻结 ledger 的逐项核对。

定位增强前 PDF SHA 为
`1c434b0474dfc4a8921317e2322cada20641735e3938f8ea063a6f77051c0f5b`，
同为 10 页。该对比足以确认本轮表达增强的实际文本落点和页面回归，但不是源代码级版本历史。

---

## 3. A — 修改范围回归

| 允许的增强位置 | 当前实际变化 | 是否符合最小增强范围 | 是否触碰硬事实 |
|---|---|---:|---:|
| Abstract：gap 范围 | 加入 fixed-horizon pixel accuracy 的范围限定 | 是 | 否 |
| Abstract：state-centered 方法描述 | 加入 forecast-bearing、weather-responsive predictive state 和 spatial predictive state | 是 | 否 |
| Introduction：predictive-state 锚点 | 加入 predictive-state view 与 `littman2001predictive` | 是 | 否 |
| Introduction：Q3 预告 | 明确 forecast-window response fidelity | 是 | 否 |
| Related Work：稳健差异 | 用 “principal evidence concerns…” 描述既有范式主要证据 | 是；保留范围限定 | 否 |
| 3.2：transition 段尾 | 增加 future forcing 被约束在 state evolution 的解释 | 是 | 否 |
| 3.2：readout 段尾 | 增加 context-only forecast 是 state contribution 的 matched reference | 是 | 否 |
| 3.3：首句 | 增加训练目的的 state-centered 表达 | 是 | 否 |
| 3.3：结尾过渡 | 把 representation shaping 与后续 intervention evidence 分层 | 是 | 否 |
| 3.4：总导入 | 增加 method–evidence bridge | 是 | 否 |
| Conclusion：最后落点 | 在 frozen protocol 范围内总结 forecast-bearing 与 weather response | 是 | 否 |
| Figure 1–3 captions | 统一 predictive-state、state contribution 与 forecast-window fidelity 术语 | 是 | 否 |
| Section 4 | 未发现实验内容、结果数字、表格或统计协议变化 | 是 | 否 |
| Figure 2 图像本体 | include 路径与图文件 SHA 均未变化 | 是 | 否 |

### 3.1 未经授权重写检查

当前 PDF 与定位增强前 PDF 的文本差异集中在上表所列位置。未发现：

- Section 3 的段落结构或公式被大段重写；
- Section 4 结果段被重写；
- Table 1–3 数字或表头被改变；
- Limitations 被删除或弱化；
- 以新叙事替换已冻结的 3.1–3.4 方法主线。

**A 项结论：PASS。**

---

## 4. B — Equation (1)–(8) 与方法硬事实回归

### 4.1 公式逐项核对

| Equation | 当前内容与功能 | label / PDF 编号 | 冻结事实核对 | 结论 |
|---|---|---|---|---|
| (1) | `q_\theta → P_\rho → T_\psi → O_\omega`；同时给出 `b_h`、`z_t`、`z_{t+h}`、`r_h` 与 `\hat y=b+r` | `eq:contract` / (1)，PDF p.3 | 保持完整推理合同；teacher/target 不进入推理链 | PASS |
| (2) | future-weather code、horizon embedding、patch-wise geography 组成 `c_{h,i}` | `eq:condition` / (2)，PDF p.3 | weather/geography/horizon 条件均在；没有引入额外模块 | PASS |
| (3) | `z_{t+h,i}=z_{t,i}+F_\psi(z_{t,i},c_{h,i})` | `eq:transition` / (3)，PDF p.3 | residual transition 保持；同一 `z_t` 对每个 h 直接推进 | PASS |
| (4) | `r_h=O_\omega(z_{t+h})`；`\hat y=b_h+\alpha r_h`；标准路径 `\alpha\equiv1` | `eq:closure` / (4)，PDF p.3 | 加性预测、context-only baseline 和显式 state contribution 保持 | PASS |
| (5) | `L_GT` 与 `L_KD` 的 mask、聚合和 stop-gradient | `eq:forecastlosses` / (5)，PDF p.4 | GT/KD 身份、聚合差异和 teacher 梯度边界保持 | PASS |
| (6) | training-start frozen target 构造 `z^*_{t+H}` 与 `L_FS` | `eq:futurestate` / (6)，PDF p.4 | future EO 仅形成 stopped training target；future weather 在 target branch 置零 | PASS |
| (7) | `L=L_GT+0.5L_KD+\lambda_sL_FS` | `eq:total` / (7)，PDF p.4 | 权重与唯一总训练目标保持 | PASS |
| (8) | actual/donor/mean 三条天气路径；`ΔL_ctrl=L(control)-L(actual)` | `eq:interfaces` / (8)，PDF p.4 | Q3 路径、完整预测窗口损失和正值方向保持 | PASS |

### 4.2 推理和干预硬事实

| 硬事实 | 当前英文正文 | 中文镜像 | 冻结基准 | 结论 |
|---|---:|---:|---:|---|
| direct per-horizon | 明确 | 明确 | 同一 `z_t` 对每个 h 单独推进 | PASS |
| non-recursive transition | 明确 | 明确 | 不滚动消费前一步预测状态/输出 | PASS |
| future weather 只通过 `T_\psi` 进入正式预测 | 明确 | 明确 | 代码与 3.2 审计一致 | PASS |
| geography 与 horizon 只作为 transition condition | 明确 | 明确 | Equation (2) 一致 | PASS |
| 标准训练和推理路径 `\alpha=1` | 明确 | 中文限定为“正常训练和推理” | 固定 non-learnable buffer | PASS |
| Q2 在加法前临时令 `\alpha=0` | 明确 | 明确 | 输出严格退化为 `b_h` | PASS |
| `T→I` 仅为 supporting diagnostic | 明确 | 明确 | 不属于 load-bearing 主定义 | PASS |
| Q3 固定 `b,z,g,h,O`、样本、mask 与 ground-truth window | 明确 | 明确 | evaluator 与 3.4 审计一致 | PASS |
| Q3 只替换 future weather | 明确 | 明确 | donor 不提供 EO、状态、地理或真值 | PASS |
| Q3 `ΔL>0` 表示 actual weather loss 更低 | 明确 | 明确 | 与 evaluator 方向一致 | PASS |

3.2 最终审计中已有一项非阻塞措辞备注：英文说 `\alpha` “remains fixed throughout training and inference”，而评测接口会临时令其为 0。当前上下文和 3.4 已清楚区分 standard path 与 post-training intervention，定位增强没有改变该事实，也没有放大歧义；因此它是已知冻结备注，不构成本轮回归问题。

**B 项结论：PASS。公式、label、编号和接口定义均未变化。**

---

## 5. C — 三种训练身份回归

| 身份 | 初始化 / warm-start | 输入权限 | 梯度与 stop-gradient | 推理去向 | 回归结论 |
|---|---|---|---|---|---|
| Deployable TerraState student | 从允许的 forecasting precursor exact full-model warm-start | cloud-masked historical EO、past weather、static geography；future weather 只经 `T`；无 future EO | 按 schedule 更新允许的 student 参数；selected checkpoint 的 history operator 实际仍冻结 | 唯一部署主体 | PASS |
| Frozen full-weather KD teacher | 独立 full-weather Phase-I teacher，不是 student 自蒸馏，也不是 target encoder | EO/observation history、past weather、static geography、完整 future-weather sequence；无 future EO | 永久 frozen/eval；teacher prediction stop-gradient | 推理时删除 | PASS |
| Training-start frozen future-state target encoder | 训练开始时复制 student 初始 `q_{\theta^0},P_{\rho^0}` 并冻结 | all-frame observed EO（含 future EO 和 recorded masks）、past weather、static geography；future weather 置零 | 离线/eval/no-grad；`z^*` stopped；梯度只回 student transitioned state | 推理时删除，不读取 cache | PASS |

### 5.1 损失、mask 与权重

| 项目 | 冻结定义 | 当前正文 | 结论 |
|---|---|---|---|
| `L_GT` | per-pixel clear-horizon normalization，再对 vegetation × valid pixels 平均 | 未变 | PASS |
| `L_KD` | clear × vegetation time-pixel global masked mean；无 prediction-valid mask | 未变 | PASS |
| `L_FS` | terminal patch；fully clear 且至少一个 vegetation pixel；LN 后 cosine distance | 未变 | PASS |
| 权重 | GT `1.0`，KD `0.5`，FS `\lambda_s` | 未变 | PASS |
| future EO 边界 | 仅训练期 stopped target，不进入 student forecast/test inference | 未变 | PASS |
| teacher/target inference 边界 | 全部移除 | 未变 | PASS |

3.3 最终审计已有两项非阻塞备注：

1. teacher 输入列表可进一步显式写出 past weather；
2. `\epsilon_{\rm pix},\epsilon_{\rm GT},\epsilon_{\rm KD},\epsilon_{\rm FS}` 的精确数值应在复现说明集中给出。

两项均未因定位增强发生变化，不改变训练身份、损失或证据边界，不计为本轮回归缺陷。

**C 项结论：PASS。**

---

## 6. D — Q1/Q2/Q3 claim–evidence 回归

| 问题 | 当前最强主张 | 冻结证据 | 当前是否越界 | 结论 |
|---|---|---|---:|---|
| Q1 | TerraState retains useful temporal-shift forecasting skill | OOD-t `R²=0.569349...`、`RMSE=0.150594...`、`n=1904` | 否；没有 SOTA、跨协议优势或 non-inferiority | PASS |
| Q2 主证据 | state-mediated contribution is load-bearing；配对预测能力损失区间排除零 | Validation paired mean `ΔR²=0.0161625`，95% CI `[0.0064324,0.0259023]`；OOD-t `0.0219978`，CI `[0.0142199,0.0301761]` | 否；没有把结构本身写成证明 | PASS |
| Q2 支持证据 | `T→I` supports transition involvement | identity intervention 的冻结结果；正文同时指出 OOD input-distribution confound | 否；没有升级为 transition necessity | PASS |
| Q3 donor | actual weather has better forecast-window response fidelity than matched donor under frozen protocol | 84 对；mean `ΔL=0.002565468`，geo-cluster 95% CI `[0.001118712,0.003987491]` | 否；限定完整 20 步 masked window 与匹配协议 | PASS |
| Q3 normalized mean | actual weather has better forecast-window response fidelity than normalized mean | 84 对；mean `ΔL=0.011261332`，geo-cluster 95% CI `[0.005465625,0.017079932]` | 否 | PASS |
| 联合结论 | TerraState exposes a forecast-bearing, weather-responsive predictive state | Q1 utility + Q2 load-bearing state + Q3 controlled weather-response fidelity | 否；结论限定 TerraState 与 frozen protocol | PASS |

### 6.1 明确未被引入的主张

| 禁止或未支持主张 | 当前状态 |
|---|---|
| 精度 SOTA / state-of-the-art | 未出现 |
| non-inferiority | 未出现 |
| causal effect | 未声称；明确否定因果解释 |
| counterfactual correctness | 未声称；Limitations 明确否定 |
| complete physical state | 未声称；正文明确不是完整物理状态 |
| temporal composition / Q4 | 未作为主张；Figure 1 caption 与 Limitations 明确未验证 |
| non-collapse | 未出现 |
| extreme-specific enhancement | 冻结结果为 null；正文和 Limitations 明确不支持 |
| training stability | 未声称 |
| cross-dataset generalization | 未声称 |
| 所有信息都必须经过 state | 未声称；`b_h` 明确保留 context-only route |

**D 项结论：PASS。证据边界没有扩大。**

---

## 7. E — 新增强句逐句安全性

判定定义：

- **SUPPORTED：** 由架构事实或冻结证据直接支持，且范围明确；
- **SUPPORTED_WITH_SCOPE：** 基本安全，但依赖句中已有的范围限定，不能进一步泛化；
- **OVERCLAIM：** 超过证据；
- **AMBIGUOUS：** 可产生实质性双重解释。

| # | 新增强句 / 定位 | 判定 | 依据与边界 |
|---:|---|---|---|
| 1 | “typically evaluated primarily by fixed-horizon pixel accuracy” | **SUPPORTED_WITH_SCOPE** | `typically` 和 `primarily` 避免把全部 EO forecasting 文献绝对化；与定位审计的 gap 范围一致。不可改成 “only evaluated”。 |
| 2 | “forecast-bearing, weather-responsive predictive state” | **SUPPORTED_WITH_SCOPE** | Abstract 中既是所需证据对象，也由后文 Q2/Q3 冻结结果支持；不是预设所有 latent state 已具备该性质。 |
| 3 | “TerraState structures forecasting around a spatial predictive state” | **SUPPORTED** | Equation (1)–(4) 和 `q/P/T/O` 实现直接支持；没有声称状态完备或物理真实。 |
| 4 | predictive-state literature 锚点及 `littman2001predictive` | **SUPPORTED** | Littman et al. 的 predictive representation 以可观测未来预测表征状态，足以支持概念锚点；当前文本没有声称 TerraState 等同于经典 PSR。 |
| 5 | “Across these forecasting paradigms, the principal evidence concerns the quality of predicted observations.” | **SUPPORTED_WITH_SCOPE** | `Across these forecasting paradigms` 与 `principal evidence` 是范围化、比较性的表述；没有说 EO-WM/VegSim “没有内部状态”或“不是世界模型”。仍应保留 `principal`，不可强化为 `only evidence`。 |
| 6 | “isolates future meteorological forcing within state evolution” | **SUPPORTED** | 正式 student forward 中 future weather 仅进入 `T_\psi`；`b_h` 由 history-only operator 形成。这里的 isolates 是架构输入路由，不是因果识别。 |
| 7 | “context-only forecast as its matched reference” | **SUPPORTED** | Equation (4) 中 state removal 仅令 `\alpha=0`，同一样本、模型和上下文下输出变为 `b_h`。 |
| 8 | future-state alignment 目的句 | **SUPPORTED** | 由 Equation (6)、training-start frozen target 与 stopped target construction 支持；当前句没有说 alignment 已独立证明 load-bearing 或 non-collapse。 |
| 9 | 3.3→3.4 method–evidence bridge | **SUPPORTED** | 正确区分“训练塑造表示”和“干预检验承载性/响应性”，没有提前写入实验结果。 |
| 10 | Conclusion：“under the frozen protocol... carries forecast information and responds more faithfully to actual weather than to matched controls” | **SUPPORTED_WITH_SCOPE** | `under the frozen protocol`、TerraState 主语和 `matched controls` 都保留；“more faithfully”严格落在完整 20 步 masked forecast-window loss，而非物理真实性、因果性或任意 control。 |

### 7.1 特别风险判断

- **“principal evidence”与稻草人风险：** 当前版本没有把 EO-WM、VegSim 或全部既有工作描述为只看像素分数，也没有否定其 world-model 身份；句子只指出这些范式的主要经验依据落在 predicted observations。因此判为 `SUPPORTED_WITH_SCOPE`，不是 overclaim。
- **“responds more faithfully”：** 由完整 20 步 forecast-window masked MSE 的 donor/mean 两条正向差异支持；正文和 caption 没有把它扩成物理真实性。
- **“forecast-bearing”：** Abstract 中用来定义需要验证的 state property，后文 Q2 给出对应证据；不是无证据的结果替代。
- **“isolates”：** 指输入通路结构约束，不指随机化、因果识别或外部混杂消除。
- **Conclusion 范围：** 主语始终是 TerraState，且显式含 `under the frozen protocol`；没有泛化到所有 forecasters。

**E 项结论：10 句中 SUPPORTED 5，SUPPORTED_WITH_SCOPE 5，OVERCLAIM 0，AMBIGUOUS 0。**

---

## 8. F — 限制与正向表达平衡

### 8.1 Limitations 保留情况

| 必要限制 | 当前是否保留 | 说明 |
|---|---:|---|
| 非因果 | 是 | weather substitution 明确不构成 causal identification |
| 非反事实 | 是 | 不声称 counterfactual correctness |
| 非完整物理状态 | 是 | predictive state 被限定为任务相关预测表示 |
| hot-dry / extreme-specific enhancement 不成立 | 是 | interaction CI 跨零，明确不支持 |
| 单次训练 | 是 | 限制复现与训练方差推断 |
| 单个 OOD-t 轨道 | 是 | 不泛化到任意 temporal shift |
| 非严格跨实现排名 | 是 | 不把 Q1 写成跨协议 SOTA |
| composition 未验证 | 是 | 没有作为核心证据或已证主张 |

### 8.2 Conclusion 的平衡

Conclusion 不再重复完整限制清单，但：

1. 直接使用 `under the frozen protocol`；
2. 只总结 TerraState 的 forecast-bearing 与 matched-control weather response；
3. 紧邻且独立可见的 Limitations 已完整列出不可支持外推；
4. Abstract、3.4、Figure captions 同样保留边界。

因此“正向收尾 + 独立 Limitations”不会误导，也不需要把全部限制重新塞回 Conclusion。

**F 项结论：PASS。**

---

## 9. G — 术语与 captions 回归

| 目标术语 | 当前使用情况 | Caption 对齐 | 结论 |
|---|---|---|---|
| testable predictive-state world model | 核心定位一致 | Figure 1 一致 | PASS |
| predictive state | 全文统一 | Figure 1/2 一致 | PASS |
| context-only forecast | `b_h` 统一命名 | Figure 2 一致 | PASS |
| state-mediated contribution | 3.2/3.4/Results 一致 | Figure 2 一致 | PASS |
| shared weather-conditioned transition | 3.2 一致 | Figure 1/2 一致 | PASS |
| future-state alignment / anchoring | 3.3 区分 objective 与作用 | Figure 2 一致 | PASS |
| state-contribution intervention | 3.4/Q2 一致 | Figure 1/2/3 一致 | PASS |
| load-bearing | 仅用于 Q2 判据与证据 | Figure 1 一致 | PASS |
| identity-transition supporting diagnostic | 明确 supporting | Figure 2/3 一致 | PASS |
| controlled weather-path substitution | 3.4 一致 | Figure 1/2 一致 | PASS |
| forecast-window response fidelity | Q3 与 Conclusion 一致 | Figure 3 一致 | PASS |
| weather-responsive predictive state | Abstract/Intro/Conclusion 一致 | Figure 1 语义一致 | PASS |
| season-, geography-, and quality-matched donor weather | Q3 首次展开完整 | Figure 2 caption 完整 | PASS |
| normalized-mean weather | 全文统一 | Figure 1–3 一致 | PASS |

### 9.1 Figure captions

- **Figure 1：** 仍定位为 conceptual contract，区分 predictive utility、load-bearing state 与 weather-response fidelity；没有把本文协议宣称为领域唯一 world-model 定义。
- **Figure 2：** caption 的输入边界、shared transition、context-only route、state contribution、future-state alignment 与 intervention interfaces 与正文一致。
- **Figure 3：** 保留 paired per-minicube `ΔR²`、paired-bootstrap 95% CI、state removal 主证据、`T→I` 支持证据、84 frozen pairs、完整 20 步 forecast-window masked MSE 以及描述性对角线计数；没有 endpoint、causal 或 counterfactual 误读。

Caption 增强没有改变结果数值或证据含义。

### 9.2 Figure 2 独立视觉任务

**Figure 2 仍是独立视觉任务。** 当前图像本体中已记录的输入分组、future-weather 视觉位置、direct per-horizon/residual route 表达和干预接口等视觉问题，不应通过修改正确正文或 caption 来迁就。定位增强没有修改 Figure 2 文件：

- 当前 Figure 2 SHA-256：
  `47cc851497f6ef8c05104dfe1917b036164d47d976460df486377f69bf5e6409`
- 当前 PDF 与定位增强前编译留档均引用同一 Figure 2 路径；
- 图像修改时间早于定位增强审计。

**G 项结论：PASS；Figure 2 visual task 保持独立。**

---

## 10. H — 中英文回归

| 对照位置 | 关键语义 | 中英文强度 | 结论 |
|---|---|---|---|
| Abstract | fixed-horizon output gap；forecast-bearing/weather-responsive state；spatial predictive state | 一致 | PASS |
| Introduction 新增句 | predictive-state 锚点；Q3 forecast-window fidelity | 一致 | PASS |
| Related Work | `principal evidence` 的范围化比较，不否定既有世界模型 | 一致 | PASS |
| 3.2 transition 段尾 | future weather 只经 T 进入 state evolution | 一致 | PASS |
| 3.2 readout 段尾 | `b_h` 是 state contribution 的 matched context-only reference | 一致 | PASS |
| 3.3 首尾 | alignment 塑造 state，但承载性由 intervention 检验 | 一致 | PASS |
| 3.4 开场 | 训练后两个接口连接 method 与 evidence | 一致 | PASS |
| Conclusion | `under the frozen protocol` 下的联合结论 | 一致，中文保留“在冻结协议下” | PASS |
| Figure 1–3 中文说明 | predictive utility、load-bearing、weather response、完整预测窗口 | 一致 | PASS |

### 10.1 强度敏感词专项

- `under the frozen protocol`：中文保留为“在冻结协议下”，未丢失。
- `supports`：中文使用“支持”，没有升级为“证明”。
- `matched controls`：中文使用“匹配对照”，没有泛化成任意 control。
- `forecast-window fidelity`：中文使用“预测窗口保真度/预测窗口响应保真度”，没有翻译为物理真实性。
- `actual weather ... more faithfully`：中文仍限定观测未来下的预测误差关系，没有变成天气物理正确性。

**H 项结论：PASS。中英文事实、范围和主张强度一致。**

---

## 11. I — 引用回归

### 11.1 引用闭合

对当前 `main.tex` 与 `references.bib` 做完整 inventory：

- 正文唯一引用 key：24；
- BibTeX 唯一条目：24；
- 缺失 key：0；
- 未使用条目：0；
- 重复 key：0；
- undefined citation：0；
- undefined reference：0。

### 11.2 `littman2001predictive`

- 存在于 `references.bib`；
- 当前正文实际引用；
- 编译已解析；
- 原文提出以关于未来可观测量的预测来表征状态，能够支持当前有限的 predictive-state view 锚点；
- 当前正文没有声称 TerraState 是经典 PSR 的直接实现，也没有把该引用用于支持 Q2/Q3 实验结果。

### 11.3 Composition 背景

压缩后的 composition 背景仍保留对应的 autonomous/group-action 语境及引用，没有留下悬空引用、孤立术语或段落逻辑断裂。正文和 Limitations 继续明确 composition 未被本文验证。

**I 项结论：PASS。未新增文献，引用完整解析。**

---

## 12. J — 风险词命中分类

以下计数采用英文正文单词/短语边界搜索，不把 `improves` 等包含字串误计为 `prove`。

| 风险词 | 命中数 | 分类 | 回归判断 |
|---|---:|---|---|
| `first` | 4 | 训练/评测顺序、第一项协议、阶段事实 | 合法事实，不是 novelty-first |
| `only` | 30 | `context-only` 术语；future weather / future EO 等方法硬边界；model selection 约束；Limitations 中的必要限定 | 合法；未出现“only world model”式排他主张 |
| `SOTA` | 0 | — | 无风险 |
| `state-of-the-art` | 0 | — | 无风险 |
| `outperform` | 0 | — | 无风险 |
| `non-inferior` | 0 | — | 无风险 |
| `causal` | 5 | 概念边界、合法否定和 Limitations | 未声称 causal effect |
| `counterfactual` | 2 | 合法否定和 Limitations | 未声称 counterfactual correctness |
| `composition` | 2 | Figure 1 caption 的未纳入说明；Limitations 的未验证说明 | 合法否定 |
| `non-collapse` | 0 | — | 无风险 |
| `extreme-specific` | 3 | Q3 null 结果、Figure caption/Limitations 的明确否定 | 合法否定 |
| `prove` | 0 | — | 无风险 |
| `guarantee` | 1 | “does not guarantee” | 合法否定 |
| `physical state` | 2 | predictive state 不等于完整物理状态 | 合法否定 |

### 12.1 `only` 的语义分类

30 次 `only` 并非同一风险：

1. **方法硬事实中的必要 only：** future weather only through `T`、future EO training-only、只替换指定天气路径、只保留 deployable student；
2. **固定术语：** `context-only forecast`；
3. **协议约束：** checkpoint selection only by validation forecasting；
4. **必要限制/合法否定：** 证据只支持指定范围，不支持 causal/composition 等外推。

未发现用 `only` 宣称 TerraState 是唯一有效世界模型、唯一可检验方法或既有工作完全没有状态。

**J 项结论：PASS。所有命中均为硬事实、必要限制或合法否定。**

---

## 13. K — 编译与排版回归

### 13.1 编译状态

| 检查项 | 当前结果 |
|---|---|
| LaTeX fatal error | 0 |
| Undefined citation | 0 |
| Undefined reference | 0 |
| Overfull `\hbox` | 0 |
| Overfull `\vbox` | 0 |
| 当前 PDF 页数 | 10 |
| 定位增强前 PDF 页数 | 10 |
| PDF 可打开与逐页提取 | 正常 |

### 13.2 Underfull 告警

当前日志包含：

- underfull `\hbox`：正文/参考文献共 7 处；
- underfull `\vbox`：2 处。

其中相较定位增强前留档，新增：

- 1 处 underfull `\vbox`，badness 3088；
- 3.4 附近 2 处 underfull `\hbox`，badness 3049 与 1132。

它们没有造成文字重叠、裁切、公式越界或双栏顺序错误。此项记为本轮唯一 **Minor**。

### 13.3 公式、图和表的实际位置

| 对象 | 当前 PDF 位置 | 回归判断 |
|---|---|---|
| Equation (1)–(4) | p.3 | 编号连续、未越界 |
| Equation (5)–(8) | p.4 | 编号连续、未越界 |
| Figure 1 | p.2 | 与定位增强前一致 |
| Figure 2 | p.6，整页双栏图 | 与定位增强前一致；视觉内容问题是独立任务 |
| Table 1 / Table 2 | p.7 | 数值与冻结记录一致 |
| Table 3 | p.8 | 数值与冻结记录一致 |
| Figure 3 | p.9 顶部 | 与定位增强前一致；未因增强继续后移 |
| References | p.9–10 | 引用解析完整 |

Figure 3 当前位于 Conclusion 后的下一页顶部、References 开始处之前。这是定位增强前已经存在的浮动位置，不是本轮造成的新回退；图仍被 Results 正确引用，caption 和内容完整。若后续 Section 4 排版审计需要调整，只能调整浮动布局，不得改图或证据语义。

### 13.4 表达增强是否造成新分页或图表回退

- 页数保持 10 页；
- Figure 1–3 页码与定位增强前留档一致；
- Table 1–3 未移位到不可读位置；
- 未出现新的 overfull、裁切、未定义引用或浮动体丢失；
- 新增问题仅为 underfull 告警，不影响可读性。

**K 项结论：PASS_WITH_MINOR。PDF 正常，存在 1 项非阻塞排版 Minor。**

---

## 14. Section 4 与 Figure 2 的明确结论

### 14.1 Section 4 是否被意外修改

**否。**

当前 Section 4 的数据划分、Implementation and Model Selection、Q1/Q2/Q3 protocol、Table 1–3 数字、bootstrap/cluster 单位、84 个 matched pairs、完整 20 步 forecast-window loss 及限制均与冻结 ledger 和 claim–evidence map 一致。定位增强的实际文本差异没有进入 Section 4 结果数字、表格或统计协议。

### 14.2 Figure 2 是否仍为独立视觉任务

**是。**

Figure 2 图像本体未被本轮修改，其既有视觉数据流问题仍应由图表任务独立处理。正文与公式是事实基准，不能为了迁就当前图像而修改已冻结方法。

---

## 15. 冻结判定与后续权限

### 15.1 最终状态

**PASS_WITH_MINOR**

- Critical：**0**
- Major：**0**
- Minor：**1**
- 方法事实变化：**无**
- 证据边界扩大：**无**
- 中英文不一致：**无**
- PDF：**正常，10 页，无错误、未定义引用或 overfull**

### 15.2 冻结声明

**POSITIONING_PASS_FINAL_FROZEN**

1. 方法事实和证据边界保持冻结；
2. 允许开始 Section 4 系统审计；
3. 后续只允许根据 Section 4 审计做全篇术语、复现说明和篇幅校准；
4. 不再重新寻找 Section 3 主线；
5. Figure 2 继续作为独立视觉任务，不通过修改正文消解。
