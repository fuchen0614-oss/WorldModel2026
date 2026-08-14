# 86 · TerraState Phase-I Q2–Q4 诊断与 Phase-II 决策执行总纲

> 日期：2026-07-24  
> 状态：**后续实验执行总纲；论文科学问题与叙事仍以 84 号文档为最高依据。**  
> 适用范围：方案 B / TerraState 的 Phase-I 状态诊断、Phase-II 定向优化、最终 Q1–Q4 冻结评测与正文结果回填。  
> 核心纪律：**先诊断 Phase-I，再决定 Phase-II；最终 Q1–Q4 必须来自同一个最终 checkpoint。**

---

## 0. 文档定位与每次工作的必读顺序

本文不是新的叙事稿，也不改变已经提交的标题和摘要。它只负责回答：

1. 当前最重要的实验是什么；
2. Phase-I 的 Q2–Q4 出现不同结果时，Phase-II 应该如何变化；
3. 哪些约束绝不能为了追求单一指标而破坏；
4. 哪些前沿工作值得调研，以及调研如何服务具体失败；
5. 最终怎样得到可以写进 AAAI 正文的唯一模型和证据。

以后每次监督实验、设计训练或回填正文时，按以下顺序读取：

1. `84_ObsWorld_AAAI27文章主线_单模型方法闭环_双语标题摘要与问答_20260722.md`：回答“为什么做、论文讲什么”；
2. 本文：回答“下一步先做什么、看到结果后如何决策”；
3. 方案 B 最新会话与实际代码/日志：回答“当前做到哪里、是否偏离总纲”；
4. `TerraState_AAAI27/paper/main.tex`：回答“哪些事实已经能写、哪些仍必须保留占位”。

若临时会话建议与本文冲突，除非用户明确重新拍板，否则应先回到本文检查，不得凭临时灵感改变主线。

---

## 1. 已冻结的总决策

### 1.1 唯一论文主模型

- **方案 B / TerraState 是唯一活跃主线。**
- 方案 A 停止主动研发，不再进行 A2+ 搜索，不占用正文和主训练资源。
- 方案 A 的代码、权重与结果不删除，仅作为冻结备份。
- 论文中不出现“方案 A / 方案 B / A1 / A2 / B4 / B0-FT”等研发名称；最终只呈现一个 TerraState。

### 1.2 当前证据状态

当前 Phase-I B4 在 GreenEarthNet `ood-t_chopped` 上：

| 模型 | R² | RMSE | NSE | \|bias\| | RMSE25 |
|---|---:|---:|---:|---:|---:|
| Phase-I TerraState（内部名 B4） | 0.58252 | 0.14342 | -0.00177 | 0.09390 | 0.07879 |
| 内部预测参考（B0） | 0.58421 | 0.14536 | -0.02093 | 0.09645 | 0.08147 |
| 方案 A 最佳已测权重 | 0.55452 | 0.16877 | -0.3407 | 0.11630 | 0.09062 |

由此目前只能冻结以下事实：

- Q1“预测没有崩盘、具备充分竞争力”已经基本过门；
- B 明显优于 A，因此结束 A 的活跃研发是合理的；
- B4 相对 B0 是“四项改善、一项轻微下降”，不能写成“全面优于匹配底座”；
- B4 与 B0 接近**不能代替** Q2。正式 load-bearing 必须用同一个 B4 checkpoint 的 closure cut 与 `T_identity` 检验；
- Q2、Q3、Q4 尚无正式 Phase-I 数字，因此完整世界模型结果主张仍是 `partial`，不能提前写成事实。

### 1.3 当前最高优先级

1. 先完成 Phase-I B4 的 Q2–Q4 诊断；
2. 根据诊断结果进行定向前沿调研；
3. 锁定唯一 Phase-II 配方；
4. 实现、smoke、全量训练 Phase-II；
5. 冻结唯一最终 checkpoint；
6. 用该 checkpoint 重新完成正式 Q1–Q4；
7. 将唯一最终结果回填 AAAI 正文。

**Phase-II 全量训练不得早于 Phase-I Q2–Q4 诊断。**

---

## 2. 方法北极星：`q → T → O` 到底是什么

TerraState 的完整预测链是：

```text
过去的云遮挡卫星观测
        ↓
q：从历史推断当前预测状态 z_t
        ↓
T：结合未来天气、地理位置和时间跨度，将状态推进至 z_{t+h}
        ↓
O：把未来状态闭合为可以评分的未来 NDVI 预测
```

形式化表达为：

\[
z_t = q(o_{\le t}),
\]

\[
z_{t+h}=T(z_t, u_{t:t+h}, g, h),
\]

\[
\hat y_{t+h}=O(z_{t+h}).
\]

在当前方案 B 中，最后一步更准确地写成：

\[
\hat y_{t+h}
=
\hat y^{\mathrm{Contextformer}}_{t+h}
+
\alpha O_{\delta}(z_{t+h}).
\]

也就是说，状态路径负责对强预测底座进行可识别的修正。若该修正可以被切断而预测完全不受影响，则状态只是装饰，不能支撑本文主张。

“共享转移”是指不同预测时长和不同分段推进调用的是**同一个参数共享的 \(T\)**，而不是为 4、10、20 等时域分别训练互不相干的预测头。共享参数是组合和复用的前提，但共享架构本身不等于已经证明可组合，仍需 Q4 验证。

---

## 3. Q1–Q4 与 `q → T → O` 的关系

### Q1：最终预测是否足够准确

Q1 检查 \(O(T(q(\cdot)))\) 的最终输出能否在 GreenEarthNet OOD-t 上保持有竞争力。

Q1 的作用是精度门，而不是单独证明世界模型：

- Q1 失败：方法即使概念漂亮，也难以支撑主表；
- Q1 通过：只说明预测可用，仍不能证明内部状态真的工作。

### Q2：状态是否真实承载预测（load-bearing）

Q2 检查：

> 切断 \(T \rightarrow O\) 或破坏 \(T\) 后，预测是否显著变差。

若 full、closure cut、`T_identity` 几乎完全相同，则模型可以绕开预测状态，`q → T → O` 只是附加装饰。

### Q3：天气是否真实驱动状态（weather-driven）

Q3 保持历史观测和 \(q\) 得到的当前状态不变，只改变输入 \(T\) 的未来天气：

\[
u^{\mathrm{matched}}
\quad\text{vs.}\quad
u^{\mathrm{mean}}
\quad\text{vs.}\quad
u^{\mathrm{donor}}.
\]

它检查天气是否通过：

\[
u \rightarrow T \rightarrow z_{t+h} \rightarrow O
\]

真实改变未来状态和预测，而不是作为一个被模型忽略的输入字段。

### Q4：状态是否可组合推进且没有坍缩

对于 \(h=h_1+h_2\)，比较：

\[
T(z_t,u_{1:h},h)
\]

与：

\[
T(T(z_t,u_{1:h_1},h_1),u_{h_1+1:h},h_2).
\]

Q4 同时要求：

- direct 与 composed 两条路径的 endpoint 都保持可接受精度；
- 两条路径得到的状态和输出具有合理一致性；
- 真天气路径优于 shuffled 等负对照；
- 状态有非零变化、充分方差和有效秩，不是常数、恒等映射或低秩坍缩。

因此四个问题的最简关系是：

> Q1 证明预测可用；Q2 证明状态有用；Q3 证明天气能驱动状态；Q4 证明状态可稳定推进、组合和复用。

---

## 4. 正确的实验顺序：禁止再次倒置

### Stage 0：Phase-I evaluator readiness

在正式诊断前必须满足：

- Q2–Q4 所需 arm 全部实现；
- 同 cube 配对关系可复核；
- bootstrap CI、方向、win/tie/loss 等统计测试全绿；
- evaluator 不改变 checkpoint；
- Q4 endpoint guard 的定义、阈值、来源和冻结状态明确；
- donor manifest 与 matched/mean/donor 数据关系可复核；
- smoke 必须 **all pass**，不能带着已知失败进入正式远端评测。

当前若只出现 `27/28` 等非全绿结果，即使唯一失败看似只是合成统计测试，也不能宣称 evaluator ready。必须先定位并修复测试或实现，重新全绿。

### Stage 1：Phase-I B4 Q2–Q4 预诊断

- 优先完成 Q2；
- Q3 与 Q4 在资源允许时可以相互并行；
- 使用同一个 Phase-I `checkpoint_best`；
- 不启动 Phase-II 全量训练；
- 不将 Phase-I 预诊断结果与未来 Phase-II 正式结果混写。

### Stage 2：诊断归因

将每个问题判断为：

- `PASS`：强主张可以保留；
- `PARTIAL`：只能写较弱事实，需要定向补强；
- `FAIL`：必须成为 Phase-II 的首要靶点；
- `INCONCLUSIVE`：评测证据不足，先修 evaluator，不能直接改模型。

### Stage 3：定向前沿调研

只针对 Stage 2 暴露的失败调研，不进行无边界“寻找所有前沿调参技巧”。

### Stage 4：锁定唯一 Phase-II 配方

Phase-II 必须只有：

- 一个主方案；
- 最多一个预先声明的回退方案；
- 清晰的 go/no-go 条件；
- 不允许训练过程中根据 OOD-t 反复更换目标。

### Stage 5：实现与 smoke

- 完成 partial unfreeze、optimizer groups、loss/ramp 等定向改造；
- 在当前共享服务器只做 CPU 或确认 GPU 完全空闲后的 smoke；
- 当前服务器不得进行全量训练；
- 全量训练命令必须交付给用户在另一台训练服务器运行。

### Stage 6：Phase-II 全量训练与最终选点

- 从 Phase-I B4 best 热启动；
- 不从头训练；
- 依据预先冻结的验证标准选定唯一 checkpoint；
- 不用最终 OOD-t 反复挑选 checkpoint。

### Stage 7：唯一最终 checkpoint 的正式 Q1–Q4

最终论文中的：

- Table 1 / Q1；
- Q2 load-bearing；
- Q3 driver；
- Q4 composition/non-collapse；

必须全部来自同一个最终 Phase-II checkpoint。若最终选择保留 Phase-I，也必须明确冻结 Phase-I 为唯一最终模型后，再统一生成全部证据。

---

## 5. Phase-I Q2–Q4 的最低实验合同

### 5.1 Q2 必需 arms

1. `full TerraState`；
2. `closure/gate cut`；
3. `T_identity`。

必须报告：

- 每个 arm 的绝对预测指标；
- 同 cube 配对差值；
- bootstrap 95% CI；
- win/tie/loss；
- checkpoint、数据 split、evaluator 与命令 provenance。

强 load-bearing 主张的最低条件：

- full 相对 closure cut 的主要指标改善方向正确，CI 不跨 0；
- full 相对 `T_identity` 的主要指标改善方向正确，CI 不跨 0；
- 改善不是以不可接受的 endpoint 精度下降换取的；
- 两个破坏性对照都支持时，才写强事实语气。

若只有一个对照通过，只能判为 `PARTIAL`，不得把局部证据写成完整 load-bearing。

### 5.2 Q3 必需 arms

1. matched future weather；
2. normalized-mean weather；
3. season/geo matched donor weather；
4. 必要时增加 shuffled 或 zero weather 作为负对照；
5. matched-vs-matched 重复计算作为数值噪声地板。

必须报告：

- per-cube 状态变化；
- per-cube 输出绝对变化与带符号变化；
- 预测指标差异与 CI；
- 方向一致性比例与 CI；
- donor coverage 和匹配规则。

通过 Q3 不能只依赖“输出确实变化”。还要证明：

- 变化显著超过数值噪声；
- matched weather 相比 mean/donor 在与真实目标一致的方向上更合理；
- B0/base forecast 在不同 Q3 arms 中保持不变，变化确实来自 \(T\) 路径。

### 5.3 Q4 必需比较

1. direct path；
2. composed path；
3. 训练内 partitions；
4. held-out partitions；
5. shuffled weather/order control；
6. identity 的解析或实际对照；
7. endpoint accuracy guard。

必须报告：

- direct/composed endpoint error；
- output-level path gap；
- state-level path gap；
- per-partition CI；
- shuffled reference；
- transition magnitude；
- state variance/std；
- effective rank；
- 不同 horizon 的 state movement。

重要防误判：

- identity transition 的 direct/composed gap 天然可能为 0，因此“gap 小”本身不是成功；
- 必须同时检查 endpoint accuracy 与非零 state movement；
- 只有 endpoint 可用、真实路径优于负对照且状态未坍缩时，才支持 composition/non-collapse。

---

## 6. Q2–Q4 是否需要复现外部方法

### 6.1 当前结论

**Q2–Q4 不需要大规模复现其他模型。**

原因是这些实验主要检验同一个 TerraState checkpoint 的内部因果合同。最严格的比较不是换一个架构，而是：

- 权重相同；
- 输入样本相同；
- 只切断一个路径或替换一个驱动；
- 使用配对统计判断影响。

### 6.2 三层比较关系

1. **Q1 公共预测主表**：使用公开 GreenEarthNet 数字，暂不复现所有外部模型；
2. **Q2–Q4 核心机制证据**：使用同 checkpoint matched interventions 与负对照；
3. **EO-WM 外部天气协议**：最终模型和正文闭环后，若时间与数据允许再做。

### 6.3 推荐但非当前必需的训练消融

若资源允许，可以补一个与最终 Phase-II 训练配置严格匹配、但：

\[
\lambda_{\mathrm{cmp}}=\lambda_{\mathrm{con}}=0
\]

的训练消融，用于证明 Q4 改善来自 composition/consistency 目标，而不是架构偶然性质。

它的优先级低于：

- 最终主模型；
- 正式 Q1；
- Q2 load-bearing；
- Q3 driver；
- Q4 主结果；
- 正文完整性。

若无法做到训练条件严格匹配，就不要把 Phase-I 与 Phase-II 的差异简单归因于某一个 loss。

---

## 7. Phase-II 的硬约束

### 7.1 模型身份约束

- Phase-II 仍是同一个 TerraState，不得演化为第二个并列方法；
- 保持 `q → T → O` 与共享转移；
- 状态路径必须留在 forecast path；
- 不得通过增加完全独立的预测器绕开 \(T\)；
- 不得为了追求 Q1 把状态分支重新退化为辅助头。

### 7.2 初始化与解冻约束

- 从当前 Phase-I B4 best 热启动；
- 不从头训练；
- 不直接使用“全部 backbone 一次性解冻”作为首选；
- 优先 partial unfreeze：forecast head 与最后一段 PVT；
- 较早层保持冻结，除非 Phase-I 诊断和后续证据明确支持进一步解冻。

### 7.3 优化器约束

- 状态分支使用主学习率；
- 解冻 backbone 使用独立 optimizer group；
- backbone 学习率初始建议为状态分支的 `0.05–0.1×`，最终数值在诊断后冻结；
- 必须记录每组参数名称、参数量、学习率和是否真正获得梯度。

### 7.4 损失约束

默认保留并正确命名已有目标：

- forecast；
- residual anti-starvation；
- VICReg / anti-collapse；
- composition；
- consistency。

执行原则：

- composition/consistency 使用 warmup 后 ramp，避免训练初期压垮预测；
- 不得把现有 `resid+con` 随意改名为新的 JEPA 贡献；
- 未经诊断和文献/代码核验，不新增独立 JEPA loss；
- 每个新增 loss 必须能映射到一个已观察到的失败，而不是为了“更前沿”堆叠目标。

### 7.5 精度保护约束

当前工程目标：

- 至少保持 Phase-I 的预测量级；
- 优先使 R² 超过内部参考 `0.58421`；
- 理想目标进入 `0.59+`；
- RMSE 不差于约 `0.145`；
- 同时保持或改善 NSE、\|bias\| 与 RMSE25。

这些是当前工程目标，不是对最终结果的预先承诺。若 Phase-I Q2–Q4 已经很强，Phase-II 应更加保守，避免为极小精度收益破坏状态合同。

### 7.6 最终模型选择约束

最终模型不是只看一个 R²：

1. 先满足最低 Q1 精度门；
2. Q2 必须至少支持可辩护的 load-bearing；
3. Q3 必须证明天气影响超过噪声；
4. Q4 必须通过 endpoint guard 并排除 identity/collapse；
5. 在满足状态合同的候选中选择 Q1 最优者。

如果一个 checkpoint 精度略高但完全绕开状态，它不能成为当前强叙事下的最终 TerraState。

---

## 8. Phase-I 结果到 Phase-II 的决策树

| Phase-I 诊断 | 主要解释 | Phase-II 主攻方向 | 禁止的误操作 |
|---|---|---|---|
| Q2 fail，Q3/Q4 可用 | 状态有结构但不承载预测 | 强化 closure、residual anti-starvation、forecast-state coupling；控制 partial unfreeze 防止 backbone 绕过状态 | 只解冻 backbone 刷精度 |
| Q2 partial | 状态贡献太小或仅一个 cut 有效 | 提升 state contribution，同时检查 gate、renderer、梯度和 cut 定义 | 直接宣称 load-bearing |
| Q3 fail | 天气进入接口但被忽略 | 调研 weather representation、异常/气候态/累积胁迫、深层 reinjection | 仅放天气可视化 |
| Q3 有变化但 matched 不更好 | 模型对天气敏感但响应不正确 | 强化方向/幅度监督和 matched-weather fidelity | 把“变化”写成“正确响应” |
| Q4 composition fail，non-collapse pass | 状态在动，但分段推进不一致 | 增强 cmp/con、held-out partition 训练设计和共享算子约束 | 只减小 gap 而忽视 endpoint |
| Q4 non-collapse fail | 状态接近常数、identity 或低秩 | 调整 VICReg、状态容量、transition magnitude 与 anti-starvation | 用 identity 的零 gap 冒充组合成功 |
| Q2–Q4 全部 pass，Q1 一般 | 状态合同已成立，主要缺精度 | 保守 partial unfreeze、低 LR 精度微调，持续监控 cut probes | 大规模重构状态路径 |
| Q1–Q4 均强 | 当前模型可能已足够 | 缩短或取消高风险 Phase-II，只做必要复验/多 seed | 为“必须有 Phase-II”而训练 |
| evaluator inconclusive | 当前无法判断模型 | 先修评测器和统计合同 | 根据不可信数字改模型 |

### 8.1 可能的回退方案

回退方案只有在主方案触发预先声明的停止条件后启用。当前允许的回退类型包括：

- 更保守的解冻范围；
- 降低 backbone LR；
- 降低 cmp/con 最大权重或延长 ramp；
- 针对 Q1 的低权重时序 metric-aligned 辅助目标；
- 针对明确 Q2 失败的最小 load-bearing 约束。

禁止一次同时引入多项无法归因的变化。

---

## 9. Phase-II 前沿调研规则

### 9.1 调研不是“寻找所有能涨点的技巧”

每一项候选研究必须回答：

1. 它解决 Phase-I 哪个已经观察到的失败？
2. 它如何接入当前 `q → T → O`，是否会破坏单模型主线？
3. 是否有权威论文、官方代码或清晰公式支持？
4. 需要修改哪些模块，代码和训练风险多大？
5. 能否用一个明确的消融验证其作用？
6. 如果失败，如何回退到 Phase-I checkpoint？

无法回答以上问题的“前沿技巧”不进入 Phase-II。

### 9.2 按失败类型划分的优先调研方向

#### 若 Q1 的 R²/NSE 明显弱于 RMSE

优先调研：

- 逐像素沿未来 20 个 horizon 的 masked temporal correlation；
- CCC / correlation-aligned auxiliary objective；
- bias 与动态幅度校准；
- 低学习率 partial fine-tuning；
- 与 GreenEarthNet 时间统计一致的可微代理。

注意：

- 必须沿时间维计算，不能误用固定时刻的空间相关；
- 继续保留稳定的 masked MSE 主目标；
- metric-aligned loss 只能作为低权重辅助或回退，不应一次替换全部训练目标。

#### 若 Q2 load-bearing 失败

优先调研：

- load-bearing predictive bottleneck；
- residual anti-starvation；
- closure contribution / cut-aware margin；
- 预测状态与 forecast head 的耦合；
- 防止强底座绕过状态的训练结构。

注意：

- “gate 变大”不等于状态有用；
- gradient 非零不等于 cut 后预测会退化；
- 必须以同 checkpoint intervention 的最终结果验收。

#### 若 Q3 weather-driven 失败

优先调研：

- weather climatology–anomaly decomposition；
- cumulative heat/water/compound stress；
- weather condition 的多层 reinjection；
- ordered weather-segment encoder；
- forcing-response direction/magnitude 约束。

可重点参考 EO-WM 的物理化天气表示和响应评测思想，但不得直接复制其方法叙事，也不得在核心实验完成前被外部 benchmark 绑架。

#### 若 Q4 composition 失败

优先调研：

- shared variable-time operator；
- direct/composed path consistency；
- semigroup-inspired 但不夸大为严格半群定理的约束；
- held-out partition generalization；
- endpoint-guarded latent path matching。

注意：

- 天气驱动过程具有有序、不可逆的外部 forcing，不能直接套用自主系统或群作用的强数学表述；
- path gap 必须与 endpoint accuracy 一起报告。

#### 若 Q4 non-collapse 失败

优先调研：

- VICReg variance/covariance 平衡；
- predictive-state variance floor；
- effective-rank regularization；
- transition magnitude 与 identity avoidance；
- stop-gradient predictive representation 的必要性。

注意：

- 不要仅凭 loss 名称宣称 JEPA；
- anti-collapse 不能以制造无意义大幅状态变化为代价；
- 必须同时观察输出、状态与 endpoint。

### 9.3 候选方法证据卡

每个候选方法在开工前形成一张简短证据卡：

| 字段 | 必填内容 |
|---|---|
| 目标失败 | Q1 / Q2 / Q3 / Q4 的哪一项 |
| 核心机制 | 为什么理论上能解决该失败 |
| 主要来源 | 论文、官方代码、年份与发表状态 |
| 最小改动 | 文件、模块、参数组 |
| 主超参数 | 只列必须冻结的少量参数 |
| 成功指标 | 哪个配对指标/CI/guard 改善才算成功 |
| 失败风险 | 精度、状态、显存、训练稳定性 |
| 回退 | 恢复到哪个 checkpoint/config |

只有完成证据卡后，才能把候选方法加入 Phase-II 主方案或唯一回退。

---

## 10. 重点参考方向与语言边界

以下是调研入口，不代表当前已经采用：

- GreenEarthNet / Contextformer：公共预测任务、主表指标与强底座；
- EO-WM：部分可观测、天气驱动 EO world modeling；气候态/异常/累积胁迫；Extreme/Seasonal 响应评测；
- VICReg：variance/covariance anti-collapse；
- I-JEPA / V-JEPA：stop-gradient predictive representation 的相关思想；
- Deep-OSG 等 operator/semigroup-inspired 工作：变量时长共享算子与组合约束；
- PLSM 等 control-conditioned latent dynamics：外部驱动对状态变化的结构约束。

必须坚持：

- 不否定 EO-WM 的世界模型身份；
- 不宣称其他模型“没有世界模型”；
- 不把天气驱动陆表过程写成严格自主半群；
- 不把我们自己的 Q2–Q4 包装成新的社区 benchmark；
- 不因主表不是 SOTA 而隐藏 Q1；
- 不把未通过的合同靠摘要措辞写成已经成立。

---

## 11. 服务器与工程纪律

### 11.1 当前共享服务器

- 只做静态审计、CPU smoke 或确认 GPU 完全空闲后的最小 GPU smoke；
- GPU 是否有余量不能仅凭“利用率未满”判断；
- 设置进程优先级不能保证不影响他人训练；
- 无法确认 GPU 完全空闲时，使用 CPU 或只交付命令；
- 不进行全量训练。

### 11.2 用户的全量训练服务器

Claude/Codex 应交付可复制的完整命令，至少包含：

- `cd`；
- conda 激活；
- 代码更新/commit 身份；
- 数据路径；
- checkpoint 路径与 SHA；
- GPU/DDP 设置；
- 输出目录；
- 日志重定向；
- 监控与结果汇总命令。

### 11.3 结果保护

- 不覆盖现有 Phase-I OOD-t 结果；
- 不删除 checkpoint；
- 新评测使用新输出目录；
- 每个正式结果记录 checkpoint SHA、代码 commit、evaluator commit、split、样本数与命令；
- smoke 结果不能冒充正式结果；
- Phase-I 与 Phase-II 结果不得在同一行或同一 claim 中混用。

---

## 12. AAAI 正文映射

### 12.1 Table 1 / Q1

正文公共主表建议保留：

- Climatology；
- Earthformer；
- PredRNN；
- SimVP；
- Contextformer；
- TerraState。

原则：

- 公开方法使用 published numbers 并明确标注；
- 不需要为聚合口径另建一个“CVPR Table 2”；
- 不写严格 SOTA 或虚构排名；
- 可写 `competitive`、`forecast-sufficient`；
- B0-FT 不进入正文主表。

### 12.2 Q2–Q3 表

使用最终同一 checkpoint 的：

- full；
- closure cut；
- `T_identity`；
- matched weather；
- normalized-mean weather；
- donor weather。

报告绝对性能、配对差异和 CI，避免只报内部状态量。

### 12.3 Q4 表或图

使用：

- direct/composed；
- train/held-out partitions；
- shuffled/identity controls；
- endpoint guards；
- state variance/effective rank/movement。

### 12.4 写作时机

在 Phase-II 最终结果出现前，可以立即完成：

- 最终 B 架构方法段；
- `q → T → O` 的定义；
- Q1–Q4 实验合同；
- related work；
- 结果表结构；
- 讨论和限制的安全版本。

不能提前填：

- load-bearing 已通过；
- weather response 已正确；
- composition/non-collapse 已成立；
- Phase-II 提升幅度；
- 最终摘要结果句。

---

## 13. 停止条件与叙事降级

### 13.1 Phase-II 训练停止/回退条件

出现以下情况时停止主配置并审计，不得盲目延长训练：

- Q1 明显跌破 Phase-I 且持续不能恢复；
- backbone 学会绕开状态，Q2 更差；
- gate/transition 数值异常或状态坍缩；
- composition loss 降低但 endpoint accuracy 明显恶化；
- 出现 NaN/OOM/不可复现的 DDP 行为；
- 主方案已触发预先冻结的 no-go 条件。

### 13.2 最终论文主张分级

#### 强闭环

- Q1 竞争力成立；
- Q2 load-bearing 成立；
- Q3 driver 成立；
- Q4 composition/non-collapse 成立。

可使用当前强标题和方法型闭环摘要。

#### 部分闭环

- Q1 成立；
- Q2–Q4 只有部分成立。

必须按真实结果缩窄摘要，明确哪些属性通过，不能将方法接口当作实验证据。

#### 核心失败

- Q1 明显不足，或；
- Q2 证明状态不承载预测且 Phase-II 无法修复。

此时应降低“load-bearing predictive-state world model”强度，不能靠 EO-WM 外部尺子或附加 benchmark 掩盖。

---

## 14. 当前待办清单

### P0：立即

- [ ] Q2–Q4 evaluator 全部 smoke 通过；
- [ ] 冻结 Q4 guard 配置和来源；
- [ ] 冻结 donor manifest 与验证规则；
- [ ] 交付 Phase-I B4 Q2–Q4 完整服务器命令；
- [ ] 在全量服务器完成 Phase-I Q2–Q4；
- [ ] 汇总 `PASS / PARTIAL / FAIL / INCONCLUSIVE`。

### P1：诊断后

- [ ] 针对失败项建立候选方法证据卡；
- [ ] 调研相应前沿论文和官方代码；
- [ ] 选择一个 Phase-II 主方案和一个回退；
- [ ] 冻结 partial-unfreeze、optimizer groups、loss/ramp 和 go/no-go；
- [ ] 实现并完成 smoke；
- [ ] 交付 Phase-II 全量命令。

### P2：Phase-II 后

- [ ] 冻结唯一最终 checkpoint；
- [ ] 重新跑正式 Q1；
- [ ] 重新跑正式 Q2；
- [ ] 重新跑正式 Q3；
- [ ] 重新跑正式 Q4；
- [ ] 确认全部结果来自同一 SHA；
- [ ] 回填正文、摘要结果句、讨论与结论。

### P3：核心闭环后

- [ ] 评估是否做 EO-WM Extreme/Seasonal 外部协议；
- [ ] 必要时补严格匹配的 `cmp/con=0` 训练消融；
- [ ] 将聚合口径、额外 provenance 与工程诊断移入附录。

---

## 15. 每次监督时必须提醒的五件事

1. **现在最重要的是正文完整性与最终 Q1–Q4，不是无限扩展 evaluator 或 benchmark。**
2. **Phase-II 必须由 Phase-I Q2–Q4 诊断驱动，不能先跑再解释。**
3. **最终只有一个 TerraState、一个 checkpoint、一个主线。**
4. **精度门与状态合同缺一不可；不能只刷精度，也不能只做漂亮状态图。**
5. **任何新想法先回答它解决哪个已观察到的失败，否则后置。**

---

## 16. 关联文件与外部入口

### 项目内

- `84_ObsWorld_AAAI27文章主线_单模型方法闭环_双语标题摘要与问答_20260722.md`
- `75_方案B执行引导_ObsWorld_Stage2v3_PVT_plan-b-pvt_20260722.md`
- `83_TableB实现方案_EO-WM_benchmark复现_20260722.md`
- `TerraState_AAAI27/paper/main.tex`
- `WorldModel2026-planb/models/plan_b_b4.py`
- `WorldModel2026-planb/train/train_plan_b_b4.py`
- `WorldModel2026-planb/eval/eval_b4_state_contract.py`

### 外部入口

- GreenEarthNet / Contextformer：<https://github.com/vitusbenson/greenearthnet>
- EO-WM 论文：<https://arxiv.org/abs/2606.27277>
- EO-WM 官方评测：<https://github.com/Luo-Z13/EO-WM>
- VICReg：<https://arxiv.org/abs/2105.04906>
- I-JEPA：<https://arxiv.org/abs/2301.08243>
- V-JEPA：<https://arxiv.org/abs/2402.08446>
- Deep-OSG：<https://arxiv.org/abs/2302.03358>

---

## 17. 本文件的变更纪律

- 本文件是执行总纲，不替代 84 号叙事锁定稿；
- 新结果出现后应先判断其是否改变决策树，再决定是否更新本文；
- 不把临时命令、长日志和每个 checkpoint 的细节全部塞入本文；
- 实际运行命令继续保留在方案 B 执行日志或独立 runbook；
- 任何涉及主线、标题、摘要或停止条件的实质变化，必须由用户重新拍板；
- 未来若要修改本文，也应获得用户明确许可。

---

## 18. 一句话执行北极星

> 先用 Phase-I Q2–Q4 找到 TerraState 当前状态合同的真实薄弱点，再以一个有边界、可归因的 Phase-II 同时守住预测精度与 `q → T → O`；最终只用一个冻结 checkpoint 完成 Q1–Q4，并把主要时间留给 AAAI 正文闭环。

---

## 19. 最终统一流程：历史预训练、当前 Stage A/B 与论文流程图

> 更新日期：2026-07-25（UTC）  
> 目的：消除“旧方案 A/B、SSL4EO Stage1/1.5、Phase-I/II、当前 Stage A/B”多套名称造成的混淆。以下流程是最终监督口径。

### 19.1 两条历史路线必须分开

旧方案 A 曾真实使用：

```text
SSL4EO-S12-v1.1
  → Stage1：S1/S2 多模态 MAE 预训练
  → Stage1.5：真实采集条件 φ + FiLM + state projector
  → EarthNet2021x 迁移（neutral φ）
  → ViT-S Direct/Rollout
```

这条路线已冻结，不进入当前 TerraState 主模型。当前方案 B 使用的是
ImageNet/Contextformer-PVT 初始化，现有 exclusive checkpoint 不加载旧 ViT-S
Stage1/1.5 权重。不得为了“不浪费”而把未进入最终 checkpoint 的 SSL4EO
模块画进主方法图。

当前唯一活跃路线是：

```text
PVT/Contextformer 初始化
  → Phase-I B4（诊断出 full-weather bypass，非最终模型）
  → exclusive predictive-state Stage A（当前训练）
  → Stage-A val Q1+Q2 选择唯一底座
  → Stage B contract refinement（MAIN/SAFE）
  → val Q1–Q4 冻结唯一 checkpoint
  → 一次性 OOD-t + 正文回填
```

### 19.2 推荐的五阶段执行命名

| 阶段 | 推荐名称 | 主要动作 | 科学意义 | 是否进入主方法图 |
|---|---|---|---|---|
| 1 | Forecast initialization | 用 Contextformer/PVT 与 Phase-I B4 初始化 student，并保留独立 frozen teacher | 提供预测语义与精度起点；teacher 仅训练期存在 | 只画成虚线 training-only teacher |
| 2 | Predictive-state bootstrap（当前 Stage A） | 冻结 `q`；训练 context-only prior + `T→O` exclusive route | 消除未来天气绕过 `T` 的捷径，优先建立 Q1/Q2 | 是，作为第一阶段优化 |
| 3 | Contract refinement（未来 Stage B） | partial unfreeze；composition/state consistency/future VICReg；preflight 通过时 MAIN 可启用低概率 intervention distillation | 在保护 Q1/Q2 的同时强化 Q3/Q4 | 是，作为第二阶段优化 |
| 4 | Validation selection | 在 val 上评估候选并冻结一个 checkpoint、SHA、manifest、阈值 | 防止事后挑 OOD-t winner；确保全文只有一个模型 | 实验设置中说明，不作为网络模块 |
| 5 | Final verification | 同一 checkpoint 完成 Q1–Q4，并只运行一次 OOD-t | 形成最终结果闭环 | 图中画 Q1–Q4 probes |

### 19.3 论文主方法图只画真实推理链

```text
历史卫星观测 + 云掩膜
        ├──────────────→ context-only prior b_h（不见未来天气）
        ↓
q：上下文状态推断 → z_t
        ↓
T(z_t, future weather, geography, h) → z_{t+h}
        ↓
O(z_{t+h}) → state-carried residual
        ↓
b_h + residual → 最终预测 ŷ_{t+h}
```

训练期 full-weather teacher 必须用虚线标注 `training only / discarded at
inference`。Q1 放在最终输出旁；Q2 画 closure cut 与 `T→I`；Q3 画
matched/mean/donor weather；Q4 画 direct 与 composed 两条共享 `T` 的路径。
不要把 cfgA–D、MAIN/SAFE 或旧方案 A/B 画成多个论文模型。

---

## 20. Q1–Q4 判定线：代码硬门、内部解释档位与论文边界

> 这些阈值首先是项目内部的冻结判定，不是领域普适标准，也不定义谁“有资格”
> 被称为世界模型。正式表格必须同时报告绝对数值、连续效应量、配对 CI 与
> PASS/FAIL，不能只报告人为二值结论。

### 20.1 三类阈值必须区分

1. **代码硬门**：当前 evaluator 实际执行的 PASS/FAIL。
2. **工程目标**：用于判断是否值得继续训练和是否保护了精度。
3. **论文解释档位**：用于决定摘要和正文能写多强，不直接写入 evaluator。

### 20.2 Q1：预测精度

Q1 当前没有代码级二值 verdict，必须区分 `val_chopped` 选模与最终
`ood-t_chopped` 报告。

#### Stage-A/Stage-B val 选模内部档位（同本地 evaluator）

| 档位 | R² | RMSE | 含义 |
|---|---:|---:|---|
| 最低 qualifier | `≥0.502` | `≤0.156` | 没有明显跌出当前本地可用范围；只允许进入 Q2 检查，不代表论文精度已经成立 |
| 强/目标 | `≥0.512` | `≤0.151` | 达到或超过 Phase-I B4 val 锚点（约 `0.51197/0.15089`） |
| 优秀（内部） | `≥0.520` | `≤0.148` | 在相同 val 口径上同时出现有意义的 R² 与 RMSE 改善；仍不能与 published OOD-t 数字混比 |

#### 最终 OOD-t 论文解释档位

| 档位 | 建议联合条件 | 允许的论文表述 |
|---|---|---|
| 完整正文保底 | R² `≥0.55`、RMSE `≤0.160`，且诚实报告 NSE/bias/RMSE25 | 可完成论文，但不能称充分竞争；需要结果降级叙事 |
| 方法论文合格 | R² `≥0.58`、RMSE `≤0.150`、NSE 不明显低于 0（建议 `≥-0.05`） | `forecast-sufficient` / `competitive in scale`，不写 SOTA |
| 强 | R² `≥0.59`、RMSE `≤0.145`、NSE `≥0` | “保持强预测能力”的结果句较稳 |
| 优秀 | R² `≥0.60`、RMSE `≤0.140`、NSE `≥0.05` | 接近公开前沿量级；仍须同 split/evaluator/aggregation 才能谈排名 |

以上 OOD-t 数字是基于当前项目锚点（Phase-I `0.58252/0.14342/-0.00177`、
公开 Contextformer 约 `0.62/0.14/0.09`）形成的内部解释线，不是
GreenEarthNet 官方等价性标准。

### 20.3 Q2：load-bearing predictive state

当前代码 `eval_b4_exclusive_contract.py` 的硬门：

1. `full − alpha0` 的逐 cube paired-bootstrap 95% CI 下界 `>0`；
2. `full − T_identity` 的逐 cube paired-bootstrap 95% CI 下界 `>0`；
3. 两个绝对 aggregate `ΔR²` 均 `≥0.005`；
4. checkpoint/intervention invariants 通过。

| 档位 | 两个 cut 中较弱者的 `ΔR²` | 额外要求 |
|---|---:|---|
| 合格（代码 PASS） | `≥0.005` | 两个 CI 下界均 `>0`，且 Q1 合格 |
| 强 | `≥0.010` | 两个 cut 方向一致，RMSE/NSE 不出现相反的严重退化解释 |
| 优秀 | `≥0.020` | paired CI 稳定、绝大多数 cube 方向一致，且 final Q1 仍在强档 |

`T_identity` 会把未推进状态交给为未来状态训练的 `O`，存在一定 OOD-state
混淆，因此正式正文必须同时报告 closure cut；不能只靠 `T_identity` 宣称
动力学成立。

### 20.4 Q3：weather driver

当前代码硬门要求：

1. matched weather 相对 normalized-mean/zero 与 season-geo donor 两个 arm 的
   paired `ΔR²` CI 下界均 `>0`；
2. 两个 arm 的 aggregate `matched − arm ΔR²` 均达到冻结的
   `min_matched_minus_arm_dr2`；
3. 输出变化的 CI 下界达到冻结的 `min_output_abs_delta`；
4. context-only prior 在各 arm 中逐位不变；
5. donor v2 coverage、DOY/geo/divergence/reuse validator 全部通过。

其中建议冻结：

- `min_matched_minus_arm_dr2 = 0.005`；
- `min_output_abs_delta` **不得拍脑袋填数**，必须由 Phase-I 重复计算/
  two-scorer numerical noise floor 派生，并在 Stage B 正式训练前记录 JSON 与 SHA。

| 档位 | matched 相对两个 arm 的较弱 `ΔR²` | 输出变化 |
|---|---:|---|
| 合格（代码 PASS） | `≥0.005` 且 CI 下界 `>0` | CI 下界超过冻结噪声地板 |
| 强 | `≥0.010` | CI 下界至少约为噪声地板的 `2×`，h=5/10/20 均有稳定响应 |
| 优秀 | `≥0.020` | donor 与 mean/zero 均稳定、方向/幅度分析一致，且 Q1 不下降到保底档 |

Q3 只能支持 `weather-conditioned predictive dependence / response fidelity`，
不能写 causal counterfactual correctness。

### 20.5 Q4：composition 与 non-collapse

当前代码硬门要求：

1. 所有 held-out partitions 的 composed endpoint 相对 direct endpoint
   非劣：`MSE_cmp ≤ MSE_dir × (1+0.05)`；
2. direct/composed endpoint 均通过冻结的绝对 endpoint guard；
3. pooled held-out `A_comp = gap_broken − gap_real` 的 cube-clustered bootstrap
   CI 下界 `>0`；
4. 至少一半 held-out partitions 的 `gap_real/gap_broken <1`；
5. h=20 的 state std retention 与 effective-rank retention 均 `≥0.5`；
6. Q2 同时 PASS。

| 档位 | Endpoint 非劣 | Broken control | 状态保留 |
|---|---|---|---|
| 合格（代码 PASS） | 所有 held-out `≤5%` | pooled CI 下界 `>0`，至少一半 ratio `<1` | std/eff-rank retention `≥0.5` |
| 强 | 所有 held-out `≤3%` | 大多数 partitions ratio `<1` | retention `≥0.7` |
| 优秀 | 所有 held-out `≤2%` | 所有 partitions ratio `<1` 且 pooled 优势稳定 | retention `≥0.8`，movement 非零且跨 cube 不退化 |

绝对 endpoint guard 的真值仍必须由 Phase-I endpoint-MSE 分布派生并冻结到
`guard_config.json`；缺失时 formal evaluator 必须 fail-closed。

### 20.6 当前已发现的 Q4 文字性不一致（正式评测前 P0）

截至代码 commit `0ca6750`：

- `EXCL_TRAIN_PARTITIONS` 实际包含 `(10,10)`，因此训练覆盖 total horizon 20；
- evaluator 的 `heldout_note_h20` 却写成“`(10,10)->h=20` composition is NEVER
  trained / cmp/con reach h<=10”。

这是 provenance/结果解释文字错误，不影响已实现的数值计算，但必须在正式 Q4
前修正并重新 smoke。正确表述应是：**total horizon 20 在 `(10,10)` 上训练过，
而 `(8,12)`、`(2,18)` 等 h=20 分段比例是 held-out partition generalization**。

---

## 21. “保证精度时 Q2 能否通过”的当前信心与决策门

### 21.1 为什么比 Phase-I 更有希望

当前 exclusive route 同时具备：

- context-only prior 看不到未来天气；
- 未来天气只能通过 `T`；
- `alpha` 固定为 1，不能学习为 0；
- Stage A 冻结 `q`，不能通过改变 prior 隐藏 state branch；
- `L_fore + L_distill + L_resid` 共同把 teacher–prior gap 压到 `T→O`；
- 既有 full-teacher vs context-prior 诊断存在约 `ΔR²=0.026`、
  `ΔRMSE=0.020` 的可学习空间，而 Q2 代码 floor 为 `0.005`。

因此 Q2 不再像 Phase-I 那样被结构性旁路预先判死。

### 21.2 为什么仍不能保证

- teacher–prior gap 不等于 student 最终一定能捕获的 Q2 贡献；
- context-only prior 可能已解释大部分季节信号；
- 强化 state contribution 可能与 Q1 精度保护发生冲突；
- `T_identity` arm 存在 OOD-state 混淆；
- Q3/Q4 训练目标可能改变 Q2 与 Q1 的平衡。

当前负责任的判断是：**Q2 在保护 Q1 的同时通过，属于“中等偏上信心、值得押注，
但远非稳过”**。在 Stage-A 正式 val Q1+Q2 出来前，不给伪精确成功概率。

### 21.3 Stage-A 后的 go/no-go

1. 至少一个候选达到 Q1 qualifier，且 Q2 两个 cut 均 PASS：进入 Stage B。
2. Q1 合格，Q2 两个 cut 均为正但仅差 effect floor/CI：进入 MAIN/SAFE，但把
   Q2 作为 Stage B 首要监控。
3. Q1 合格，但所有候选 Q2 接近 0 或为负：暂停原定 Stage B，评估
   state-primary fallback，不用 Q3/Q4 掩盖 Q2。
4. Q2 PASS 但 Q1 跌破 qualifier：优先使用 SAFE/精度保护，不把机制结果冒充
   完整方法成功。

### 21.4 全文最低与理想闭环

- **完整正文最低闭环**：Q1 至少保底；所有 Q1–Q4 有真实结果；失败项诚实进入
  结果与限制，不留 TBD。
- **可辩护方法闭环**：Q1 方法论文合格 + Q2 PASS + Q3/Q4 至少一项 PASS、
  另一项 PARTIAL。
- **强闭环**：Q1 强档 + Q2/Q3/Q4 全部 PASS。
- **优秀闭环**：Q1 接近公开前沿量级，且 Q2/Q3/Q4 达到上述强/优秀档。

无论落在哪一档，实验只决定标题、摘要和主张强度，不决定是否完成一篇无占位、
可编译、结果诚实的正文。
