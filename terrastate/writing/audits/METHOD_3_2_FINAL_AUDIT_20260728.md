# TerraState §3.2 冻结前独立终审

**审计日期：** 2026-07-28  
**审计对象：** `paper/main.tex` §3.2 “TerraState Architecture”及
`MANUSCRIPT_ZH_FULL.md`对应中文镜像  
**审计性质：** 只读事实、结构、语言与图文一致性审计；未修改正文、中文稿、图像或
PDF，未重新编译  
**证据优先级：** 冻结实现与 checkpoint provenance > canonical method spec >
正文公式 > Figure 2 > 旧审计意见

## 1. 最终结论

## PASS_WITH_VISUAL_BLOCKER

当前 §3.2 文字已经准确描述冻结实现中的推理架构，可以正式冻结。此前审计发现的核心
技术错误——把 \(c_h\) 写成跨空间 token 相同的条件——已被正确修复为逐 patch 条件
\(c_{h,i}\)。正文现已区分：

- 跨 patch 广播的未来天气前缀编码 \(d_h\) 与时距编码 \(E_h(h)\)；
- 随 patch \(i\) 变化的地理编码 \(E_g(g)_i\)；
- 跨 patch 和 horizon 共享的编码器、融合网络与转移参数；
- 并不要求跨空间相同的条件值 \(c_{h,i}\)。

推理链 \(q_\theta\!\rightarrow P_\rho\!\rightarrow T_\psi\!\rightarrow
O_\omega\) 与代码一致：历史算子同时产生 \(b_{1:H}\) 和 \(e_t\)，投影器构造空间
预测状态 \(z_t\)，共享天气条件转移对每个 horizon 从同一个 \(z_t\) 做一次直接残差
更新，状态读出生成栅格贡献 \(r_h\)，最终通过
\(\widehat y_{t+h}=b_h+\alpha r_h\) 加入预测，其中正常训练和推理路径
\(\alpha\equiv1\)。

当前唯一投稿阻塞是 **Figure 2 的视觉信息流仍与正确正文和实际实现不一致**。正文不应
迁就该图；作者需要按照第 6 节清单手工修图。

**问题计数（仅指 §3.2 正文/中文文字）：**

- Critical：**0**
- Major：**0**
- Minor：**1**

Figure 2 的 8 项人工修图事项单独记为 **VISUAL BLOCKER**，不计入上述正文问题数量。

**3.2_TEXT_FINAL_FROZEN**

此后 §3.2 只允许三类不改变事实和结构的调整：全篇术语统一、篇幅压缩和排版性修改。
不得借修图重新改变正文的信息边界、转移形式或加性预测结构。

## 2. Critical / Major / Minor 问题表

| 级别 | 位置 | 原文摘要 | 问题 | 证据 | 最小修改建议 | 应归属章节 |
|---|---|---|---|---|---|---|
| Critical | — | — | 未发现技术事实错误、信息泄漏表述或与冻结实现相冲突的公式 | 逐项核对 `plan_b_b4.py`、`plan_b_b4_exclusive.py`、`terrastate_v2.py` 和冻结 selection record | 无 | — |
| Major | — | — | 未发现必须在冻结前修改的叙事或章节边界问题 | §3.2 仅描述一次推理所需的三个模块，不含训练课程、checkpoint 选择、Q2/Q3 判据或结果 | 无 | — |
| Minor | `main.tex:311`；中文 `MANUSCRIPT_ZH_FULL.md:169` | 英文：“\(\alpha\) remains fixed throughout training and inference.”；中文：“在正常训练和推理中始终固定为 1。” | 中文通过“正常”准确排除了训练后干预；英文未显式加 `standard`，脱离 §3.4 时可能让读者短暂疑惑 Q2 如何临时令 \(\alpha=0\)。这不是实现错误：模型参数确为固定 buffer，Q2 是评测期临时干预。 | `models/plan_b_b4_exclusive.py:49–55` 注册 non-learnable buffer；`models/terrastate_v2.py:47–53` 断言其固定为 1；§3.4 单独定义评测期移除 | 冻结后如做全篇术语统一，可将英文收紧为 “fixed at one in the standard training and inference path”；不要求为冻结而修改 | §3.2 术语统一；评测期例外继续由 §3.4 定义 |

### 2.1 已关闭的上一轮问题

| 上一轮问题 | 当前状态 | 当前证据 |
|---|---|---|
| \(c_h\) 被错误描述为跨空间 token 共享 | **CLOSED** | 当前公式使用 \(c_{h,i}\)，并明确天气/时距广播、地理逐 patch、参数共享而条件值可不同 |
| 开场依赖 Figure 2、像图注 | **CLOSED** | 当前开场先独立说明三个推理模块，Figure 2 仅作为句末辅助引用 |
| 共享转移没有明确 direct/non-recursive | **CLOSED** | 当前明确每个 \(h\) 从同一 \(z_t\) 执行一次残差转移，并排除递归 rollout |
| “Observable Forecast Closure”产生 closed-loop/composition 歧义 | **CLOSED** | 标题已改为 “State Readout and Additive Forecast” |
| 在架构段提前写 state removal/weather substitution | **CLOSED** | 具体干预已退出 §3.2；仅保留结构可独立评估这一架构性质 |
| warm-start 混入推理架构 | **CLOSED / MOVE_TO_3_3_PENDING** | §3.2 只保留 PVT v2/Contextformer 的实现身份；完整学生模型 warm-start provenance 应在 §3.3 或 Implementation 交代 |

## 3. 逐变量与逐公式事实核对表

| 对象 | §3.2 当前定义 | 实际实现/冻结依据 | 核对结论 |
|---|---|---|---|
| \(q_\theta\) | 一次历史前向处理 cloud-masked EO、过去天气和静态地理，产生 \(b_{1:H}\) 与 \(e_t\) | `ObsWorldB4Exclusive._prior_state` 对 `_context_only_data` 调用一次 `q.encode`；后者清零未来 EO、未来天气和未来 mask（`plan_b_b4.py:173–184`; `plan_b_b4_exclusive.py:94–112`） | **PASS**。正文描述概念输入边界，未把实现清零细节塞入架构段 |
| \(b_{1:H}, b_h\) | \(q_\theta\) 输出的 context-only forecast；最终与 \(r_h\) 相加 | `_prior_state` 返回 `prior`；`forecast` 使用 `pred = prior + alpha * residual`（`plan_b_b4_exclusive.py:115–124`） | **PASS** |
| \(e_t\) | 历史算子的空间上下文 token，使用最后历史时刻 token | `PVTContextformerQ.encode` 返回 transformer block 输出；`_prior_state` 取 `z_ctx[:, context_len - 1]`（`pvt_contextformer_q.py:87–103,174–177`; `plan_b_b4_exclusive.py:105–112`） | **PASS** |
| \(P_\rho\) | 将 \(e_t\) 投影为 \(z_t\) | `SpatialStateProjector` 为逐 token LN–MLP–LN；实际输入和状态维均为 256（`state_projection.py:7–23`; `plan_b_b4.py:132–152`） | **PASS** |
| \(z_t\in\mathbb R^{N\times d}\) | 每个 token 对应一个空间 patch，并保留 patch 顺序 | PVT patch size 为 4；128×128 输入对应每样本 \(32\times32=1024\) 个 patch，代码运行时将 batch 与 patch 维展平 | **PASS**。正文采用省略 batch 维的标准记法，无需加入工程 shape |
| \(d_h\) | \(d_h=E_u(u_{t+1:t+h})\)，由共享 GRU 汇总有序未来天气前缀 | `WeatherEncoder24.all_prefixes` 用一个 GRU 前向产生所有前缀 hidden states；`window`编码指定前缀（`plan_b_b4.py:62–80,236–244`） | **PASS** |
| \(E_g(g)_i\) | 逐 patch 静态地理编码 | `GeoEncoder` 对 3 个静态地理通道以 patch size 4 平均池化，再逐 patch MLP 编码（`plan_b_b4.py:83–96,255–258`） | **PASS** |
| \(E_h(h)\) | 查询时距编码，并广播到所有 patch | `TimeEmbedding`生成 horizon code；`_direct_residual`在 batch-patch 维广播（`plan_b_b4.py:236–245`） | **PASS** |
| \(c_{h,i}\) | \(F([d_h;E_g(g)_i;E_h(h)])\)；随 horizon 和 patch 变化 | `_cond` 对 weather、geo、horizon 做 concat 后经共享 `fuse` MLP；weather/horizon 广播，geo 保持逐 patch（`plan_b_b4.py:206–215,240–245`） | **PASS**。当前文字已消除“条件值跨空间共享”的错误 |
| “shared” | weather encoder、geography encoder、condition-fusion network、transition parameters 跨 patch/horizon 共享；条件值不必相同 | 模块实例均只有一套；同一 `fuse` 和 `transition`向量化应用于所有 patch/horizon | **PASS**。参数共享与数值共享区分明确 |
| \(T_\psi/\Delta_\psi\) | \(z_{t+h,i}=z_{t,i}+\Delta_\psi([\operatorname{LN}(z_{t,i});c_{h,i}])\) | `HorizonTransition.forward` 返回 `z + net(cat(LN(z), cond))`（`plan_b_b4.py:99–117`） | **PASS** |
| 直接多时域查询 | 每个 \(h\) 从同一个 \(z_t\) 使用 \(u_{t+1:t+h}\) 做一次 residual transition | `_direct_residual`将同一 `z_t` 在 horizon 维展开，并一次向量化调用相同 transition；不是 \(z_{t+h-1}\) 到 \(z_{t+h}\)（`plan_b_b4.py:236–247`） | **PASS** |
| \(z_{t+h}\) | horizon-specific advanced predictive state | `z_th` shape 为 batch-patch × horizon × state dimension | **PASS** |
| \(O_\omega\) | 每个状态 token 读出局部 \(4\times4\) patch，再重组为 raster | `o_delta` 输出 `n_out * patch_size**2`，`_unpatchify`恢复 `(B,H,1,128,128)`（`plan_b_b4.py:152,246–253`） | **PASS** |
| \(r_h\) | horizon-specific raster state contribution，不是另一组 latent token | `_direct_residual`返回 unpatchified residual raster；`forecast`将其加至 prior | **PASS** |
| \(\alpha\) | 正常训练/推理固定为 1 | `register_buffer("alpha", tensor(1.0))`，非 Parameter；`TerraStateV2`强制断言为 1（`plan_b_b4_exclusive.py:49–55`; `terrastate_v2.py:47–53`） | **PASS**；§3.4 的临时 \(\alpha=0\) 是评测干预，不改变模型固定参数 |
| \(\widehat y_{t+h}\) | \(b_h+\alpha r_h\) 的加性预测 | `pred = prior + self.alpha * residual`（`plan_b_b4_exclusive.py:115–124`） | **PASS** |
| teacher / future-state target | §3.2 未出现 | `TerraStateV2.forward` 在无 teacher input 时直接调用纯 forecast，推理不访问 target/cache（`terrastate_v2.py:122–127`） | **PASS**。二者正确留在 §3.3 |

### 3.1 是否遗漏理解推理所需的变量或操作

未发现遗漏。当前 §3.2 已覆盖：

1. 历史输入到 \(b_{1:H}\)、\(e_t\) 和 \(z_t\)；
2. weather/geography/horizon 的编码与融合；
3. 逐 patch residual transition；
4. direct-per-horizon、non-recursive 计算；
5. token-to-patch readout 与 unpatchify；
6. context-only forecast 与 state-mediated contribution 的显式加法。

精确参数量、隐藏维度、优化器、warm-start 文件、freeze schedule 与 checkpoint 选择不属于
理解一次推理所必需的操作，留在 §3.3、Implementation 或复现材料更合适。

## 4. §3.1—§3.2—§3.3 边界检查表

| 章节 | 应承担的功能 | 当前状态 | 与相邻章节的关系 | 终审判断 |
|---|---|---|---|---|
| §3.1 Problem Formulation and Model Overview | 定义任务、世界模型视角、符号总合同和 forecast-time information boundary | 已冻结 | §3.2 不再重复论文动机、世界模型资格或 Q2/Q3 证据，只展开总合同中的三个推理模块 | **PASS** |
| §3.2 开场 | 从 §3.1 总合同过渡到一次推理的模块级实现 | 先概括 history/state、transition、readout 三个模块，再把 Figure 2 作为辅助 | 不依赖 Figure 2 才能理解；没有重新定义 TerraState 身份 | **PASS** |
| §3.2 Historical Context and Spatial Predictive State | 说明一次历史前向如何同时产生 context forecast 和 spatial state | 完整说明 \(q_\theta\)、\(e_t\)、\(P_\rho\)、\(z_t\) 及 patch 组织 | PVT v2/Contextformer 只占一句；没有训练课程或移除操作 | **PASS** |
| §3.2 Shared Weather-Conditioned Transition | 说明 future forcing 如何推进 state | 完整说明 prefix GRU、patch-wise geography、horizon、fusion、residual/direct update | 没有展开 donor/mean weather、bootstrap、判据或结果 | **PASS** |
| §3.2 State Readout and Additive Forecast | 说明 state 如何进入可观测预测 | 定义 \(O_\omega\)、raster \(r_h\)、\(\alpha=1\) 与加法 | 只陈述“可独立评估”的结构性质，没有宣告 load-bearing 已成立 | **PASS** |
| §3.3 Future-Anchored State Learning | 区分 student、KD teacher、future-state target，并定义训练目标和训练身份 | 开头衔接自然：“student follows the inference chain above” | 完整学生模型 warm-start 来源尚应在 §3.3 或 Implementation 校准；不应退回 §3.2 | **MOVE_TO_3_3_PENDING；不阻塞 §3.2** |
| §3.4 Testable Predictive-State Interfaces | 定义 \(\alpha=0\)、\(T\!\to I\) 和 future-weather substitution 的训练后接口 | 不在本轮改动范围 | §3.2 只提供加法与独立 forcing route；具体干预应继续留在 §3.4 | **边界正确** |
| Section 4 / Appendix | donor/mean 构造、split、bootstrap、阈值、结果和复现 provenance | §3.2 未混入 | 无需迁入 §3.2 | **边界正确** |

### 4.1 §3.2 保留 / 移动 / 删除判断

**保留在 §3.2**

- \(q_\theta\) 同时产生 \(b_{1:H}\) 和 \(e_t\)；
- \(P_\rho\) 构造保留 patch 组织的 \(z_t\)；
- shared GRU、patch-wise \(E_g(g)_i\)、horizon encoding 与 condition fusion；
- \(c_{h,i}\) 和 residual transition 公式；
- 每个 \(h\) 从同一 \(z_t\) 直接查询、非递归；
- \(O_\omega\) 的 patch readout/unpatchify；
- \(\widehat y=b+\alpha r\) 与正常路径 \(\alpha=1\)。

**MOVE_TO_3_3_PENDING**

- 完整 TerraState student 从何种冻结前驱权重进行 exact full-model warm-start；
- student、KD teacher、future-state target encoder 三者的初始化和冻结身份。

**移至 Implementation / 附录**

- checkpoint 路径与 SHA；
- 精确优化器、学习率分组、freeze/unfreeze schedule；
- 运行时 batch-flattened state shape 和全部隐藏维度；
- cache provenance 与训练日志。

**继续留在 §3.4 / Section 4**

- \(\alpha=0\) 的具体 state-removal 操作；
- \(T\!\to I\) supporting diagnostic；
- actual/matched-donor/normalized-mean weather substitution；
- bootstrap、置信区间、判定标准与所有结果。

**删除**

- §3.2 当前没有需要删除的句子；
- 不恢复 composition/Q4、causal response、recursive rollout 或所有预测都经 state 的主张。

## 5. AAAI 方法写作质量与双语一致性

### 5.1 段落功能检查

| 段落 | 设计目的 | 机制 | 所得性质 | 结论 |
|---|---|---|---|---|
| 开场 | 定位本节为 inference architecture | 概括 history/state、transition、readout | 给读者后续阅读顺序 | **PASS** |
| Historical Context | 同一历史上下文需支撑 base forecast 和可推进 state | \(q_\theta\) 一次前向 + \(P_\rho\) 投影 | 两个输出同源但结构上分离；state 保持空间组织 | **PASS** |
| Shared Transition | 让未来天气只通过状态转移发挥作用 | prefix GRU + patch-wise geo + horizon fusion + residual update | 参数共享、空间条件可变、direct non-recursive | **PASS** |
| State Readout | 让 transitioned state 对最终预测产生显式贡献 | token-to-patch readout + unpatchify + additive forecast | 暴露可单独评估的 state-mediated contribution | **PASS**，未把结构写成实验已经证明 |

当前文字没有工程日志式开场、Figure-caption 式段落、AI 式宣传语或把 architecture
当作 proof 的表述。公式前说明目的与输入，公式后解释广播、共享和直接查询性质，信息量
充分且不过度。

### 5.2 双语逐项一致性

| 核对项 | 英文 | 中文 | 判定 |
|---|---|---|---|
| 三模块开场 | history/state → transition → readout/addition | 同序同强度 | **PASS** |
| \(q_\theta\) 输入输出 | historical EO/past met./static geo → \(b,e\) | 完整对应 | **PASS** |
| state shape 与 patch 组织 | \(N\times d\)，每 token 对应 patch | 完整对应 | **PASS** |
| \(c_{h,i}\) | weather/horizon broadcast，geo patch-wise | 完整对应 | **PASS** |
| 参数共享与条件值变化 | 明确区分 | 明确区分 | **PASS** |
| direct/non-recursive | same \(z_t\), once per \(h\) | 同样明确 | **PASS** |
| readout/addition | local \(4\times4\) patch → raster \(r_h\) → addition | 完整对应 | **PASS** |
| \(\alpha\) | fixed throughout training/inference | “正常训练和推理”固定为 1 | **PASS WITH MINOR WORDING NOTE**；中文限定更精确 |
| 主张强度 | “can be evaluated independently” | “经验效应能够被单独评估” | **PASS**；均为架构 affordance，不是结果宣告 |

术语统一情况：

- `TerraState`：一致；
- `predictive state / 预测状态`：一致；
- `shared weather-conditioned transition / 共享天气条件转移`：一致；
- `state readout / 状态读出`：一致；
- `context-only forecast / 仅上下文预测`：一致；
- `state-mediated contribution / 状态介导贡献`：一致；
- `additive forecast / 加性预测`：一致。

公式编号与符号顺序一致：英文式（2）–（4）对应中文 tag（2）–（4），且均延续 §3.1
式（1）。未发现中文添加英文没有的能力或删去英文中的限制。

## 6. Figure 2 人工修改清单

本节仅判断图示，不修改 Figure 2。责任判断为：**当前 §3.2 正文与实际方法正确，
Figure 2 错误或含糊；不得让正文迎合图示。**

| # | 图中当前表达 | 正确表达 | 具体人工修改方式 |
|---:|---|---|---|
| 1 | Panel (a) 将 “Future meteorological forcing” 与历史 EO、历史环境上下文、静态地理共同放入 “Multimodal context”，总箭头指向 History encoder | \(q_\theta\) 只能读取 historical EO、past meteorological observations 和 static geography；future weather 不进入 history encoder | 把 future meteorological forcing 从历史上下文容器中移出；历史容器到 \(q_\theta\) 的箭头只覆盖三类允许输入 |
| 2 | Future weather 的路径先视觉上进入 history encoder 区域，后又绕向 transition | future weather 只进入 weather encoder/condition fusion，再进入 \(T_\psi\) | 从独立 future-weather 输入块直接画箭头到 shared weather-conditioned transition；不得经过或接触 history encoder 边界 |
| 3 | Panel (c) 用“weather tokens × state tokens”的乘号表示动力学 | 实现为 weather prefix、patch-wise geography、horizon 的 concat/fusion，随后与 \(\operatorname{LN}(z_t)\) concat 进入 residual MLP | 删除乘号；增加简洁的 “condition fusion” 节点或 concat 符号，并以 \(c_{h,i}\) 标注逐 patch 条件 |
| 4 | geography 和 horizon 只是并列图标，未表达广播/逐 patch 角色 | weather code 与 horizon code 广播到各 patch；geography condition 为 patch-wise | 在不增加长句的前提下标注 “broadcast weather/horizon” 与 “patch-wise geography”，或用视觉重复/索引 \(i\) 区分 |
| 5 | predictive state 到 transition 的输入关系不清，transition 内也没有 residual skip | \(z_{t+h,i}=z_{t,i}+\Delta_\psi([\operatorname{LN}(z_{t,i});c_{h,i}])\) | 画出明确的 \(z_t\to T_\psi\) 主箭头，并增加从 \(z_t\) 绕到加号的 skip path；输出标为 \(z_{t+h}\) |
| 6 | 图只显示一个泛化 “evolved predictive state”，未说明不同 horizon 的调用方式 | 对每个 \(h\)，从同一个 \(z_t\) 使用 \(u_{t+1:t+h}\) 做一次 direct query；不是递归 rollout | 在 transition 邻近加短标签 “one direct query per \(h\)”；避免画 \(z_t\to z_{t+1}\to\cdots\) 链 |
| 7 | State readout 后的 “State contribution” 仍画成 token cube grid | \(O_\omega\) 将 state tokens 映射为局部 patches，并 unpatchify 为空间 raster contribution \(r_h\) | 将 readout 输出改为空间栅格/残差图，标注 `state contribution \(r_h\)`；保留 token grid 只作为 readout 输入 |
| 8 | 最终输出标为内部式 “D3 Vegetation forecast”；Q3 只写 actual/donor/mean，且 intervention 位置像 transition 下游 | 最终输出是 \(\widehat y_{t+h}=b_h+r_h\)；Q3 替换的是 \(T_\psi\) 上游 future weather，名称为 actual / matched donor / normalized mean | 将最终输出改为 “land-surface forecast \(\widehat y_{t+h}\)”或等价论文标签，删除 `D3`；把三种 weather arm 放在 weather encoder 上游并使用冻结术语；保留 \(b_h\) 与 \(r_h\) 的显式加号 |

### 6.1 Figure 2 caption

当前 LaTeX caption 的信息边界总体正确：它把 historical EO/past weather/static
geography 送入 history encoder，把 future weather/static geography/horizon 送入
transition，并把 Q2/Q3 描述为 state-contribution removal 和 future-weather
replacement。caption 不需要为了现图而降级。作者修图时应让图像本体追上 caption 与
§3.2。

### 6.2 非方法性视觉风险

Figure 2 使用了多张遥感、地形与天气 raster tile。其来源、许可与匿名性不属于 §3.2
技术事实，但进入最终投稿前仍需由图表工作流确认 provenance。该项不改变
`PASS_WITH_VISUAL_BLOCKER` 的文字判断，也不应通过修改正文解决。

## 7. 冻结判断与下一步

### 7.1 是否达到冻结 §3.1 的质量标准

**是。** §3.2 已达到 §3.1 的事实准确性、段落功能和主张克制标准：

- §3.1 给出任务和总体合同，§3.2 只展开一次推理的架构；
- 每个模块都按“目的 → 机制 → 数学形式 → 结构性质”组织；
- 世界模型身份由 state construction、weather-conditioned transition 和 readout
  的真实路径体现，而不是重复口号；
- 文字没有把 Q2/Q3 的结构可检验性提前写成实验已通过；
- 英文和中文在符号、机制和主张强度上同步。

### 7.2 是否可以启动 §3.3 正文修改

**可以。** Figure 2 的视觉修订与 §3.3 的训练写作可以独立推进。§3.3 修改阶段应重点
接住本报告中的 `MOVE_TO_3_3_PENDING`：

1. 明确完整 TerraState student 的 full-model warm-start 身份；
2. 区分 student、frozen full-weather KD teacher 与 training-start frozen
   future-state target encoder；
3. 继续确保 teacher/target 仅用于训练，不回流 §3.2 推理路径。

Figure 2 未修复前不能视为整篇方法图文闭环完成，但不阻塞 §3.3 的文字校准。

---

**最终状态：**

`PASS_WITH_VISUAL_BLOCKER`  
`3.2_TEXT_FINAL_FROZEN`  
`3.3_REVISION_MAY_START`
