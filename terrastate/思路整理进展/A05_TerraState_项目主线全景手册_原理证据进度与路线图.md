# TerraState 项目主线全景手册：原理、证据、进度与路线图

> 文档定位：面向项目成员和首次接触本项目的读者，回答“我们究竟在研究什么、为什么这样做、已经证明了什么、尚未证明什么、当前训练在什么位置、后面怎样形成论文证据”。  
> 文档更新：**2026-08-31 更正版**（锁定集补记 2026-08-24，原稿 2026-08-21 15:40 Asia/Shanghai）；固定 4 卡 C1/C0R pair 的唯一一次 `val_locked` Q4 已完成。C1 单臂四门 PASS（`verdict=PASS`）、C0R 单臂 FAIL。臂间事实端点 `G_abs` 的 R² 腿经判定存在规格错误（对逐 cube R² 取平均，该量在目标方差趋零时无下界），其 4/19 不是有效的负面结果；用同门 RMSE 腿已在使用的 pooled 聚合重算得 19/19、三种资格口径一致（A04 §19）。事实非劣由端点描述量、pooled-RMSE 腿 19/19 与 A04 §18 的独立官方 Q1/Q2 支撑；仍不得声称预注册的 per-cube R² 版 `G_abs` 通过。早期冻结的 8 卡启动合同与实际 4 卡 pair 存在可追溯偏离，资格阈值系后验确定，这两条须继续披露。原稿中其余部分保留为历史记录；运行状态、结果身份和决策边界以本文 §0.0、A04 §17 与 §19 及原始工件为准。  
> 项目根目录：`/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate`  
> 本文性质：解释与导航手册，不替代原始结果 JSON、冻结实验合同或训练日志，也不把计划写成已完成事实。

---

## 0. 先看这一页：项目现在到底在做什么

### 0.0 当前事实、审计身份与阅读规则（2026-08-24；2026-08-31 更正）

**当前状态：`Q4_LOCKED_COMPLETE_NO_RERUN`。** 固定 4 卡 C1/C0R 内部配对均为
14,880 steps，已完成唯一一次 `val_locked`（476/476 cubes、40 tiles）Q4。
**C1 自身四门均 PASS**（`c1_score/q4_aggregate.json` 的 `verdict` 即为 `PASS`），
C0R 的 `composed_vs_direct` / `state_retention` FAIL。

> **2026-08-31 更正。** 原状态串为 `..._QUALIFIED_FAIL_...`，其中的 FAIL 来自臂间事实端点门
> `G_abs` 的 4/19。该门的 **R² 腿有规格错误**：它对逐 cube R² 取平均，而该统计量在 cube 目标
> 方差趋零时无下界，在本数据上产出 ΔR² = −35.489、CI 下界 −116.744 这类非物理取值；同一道门的
> pooled-RMSE 腿同期 **19/19 通过**。用该 RMSE 腿已在使用的 pooled 聚合重算同一批封存统计量，
> 得 **19/19，且三种资格口径一致**（A04 §19）。**4/19 是规格错误的产物，不是有效的负面结果**，
> 不再作为任何结论或阻塞的依据。原始 `compare/q4_compare.json` 保留为取证记录。

因此当前可支持的表述是：**C1 通过 Q4 四门；C1 在事实端点上不劣于 C0R**（依据：端点精度描述量
h=10/15/20 两臂差异仅 0.001–0.006、同次运行 pooled-RMSE 腿 19/19、以及 A04 §18 的独立官方
Q1/Q2）。仍**不能**声称预注册的 per-cube R² 版 `G_abs` 通过；引用该门须一并披露规格错误与两个结果。

该结果仍须带两个资格限定一起阅读（二者与 R² 腿的规格错误无关，不因更正而消失）：

1. 它是同一对 4 卡输出的锁定确认，不是 8 卡副本的结果；
2. pair 内部匹配（同父权重、seed、global batch、步数、λ），但与早期 8×8×accum1 /
   interval 372 启动合同不同（实际为 4×8×accum2 / interval 1000，且绕过 launcher）。

关于 Q4 主资格 `n_valid≥64`：它是开发集后验确定、排除约 44.7% `(cube, combo)` 的口径，仍须披露；
但它已不是决定性因素——以出错的 per-cube R² 计，none / std-v1 / 主口径分别为 1/19、5/19、4/19；
**改用 pooled R² 后三者一致为 19/19**。整条资格线调整链是在治症状。

因此本文后面仍出现“2,976 steps”“C1/C0R 未训练”“P6 阻塞”或“下一步先跑 C1/C0R”的段落时，
均为**保留的历史快照**，不得覆盖本节、A04 §15 的当前事实，也不得作为任何结果主张的依据。
CPU 审计（131/131 回归通过）、一次性输入选择收据和锁定结果的 SHA/provenance 核验均已完成。
`val_locked` 的一次性额度已用尽：不再读取、不重跑、不换 8 卡 pair。未来 C2/C3 若开展，
必须先另行冻结仅用开发信息的计划，不能用本次锁定数字调 λ、选 checkpoint 或决定重跑——
但**「因 `G_abs` 未过而不启动 C2/C3」这一阻塞理由已随本次更正失效**。

### 0.1 一句话科研问题

在云遮挡、观测不完整的地球观测（Earth Observation，EO）历史下，我们希望学习一个**可预测的地表状态**：它不仅应当预测未来地表，还应当能在给定未来天气后被同一个状态转移算子持续推进、在新的时间分段方式下保持一致，并在中途替换天气时产生可信、可检验的响应。

这里的关键词不是“把预测分数做高一点”，而是：模型内部状态是否真的成为了一个可继续计算、可组合、可干预检查的预测对象。

### 0.2 当前主线图

```mermaid
flowchart LR
    A[11,904 历史边界权重] -->|同一旧训练合同 exact resume| B[verified 14,880 权重]
    B --> C[E0: Q1/Q2/Q3 同协议复评]
    C -->|E0 v3 已封账| D[Candidate C Phase-II fork]
    D --> E[CPU 合同与代码测试 131/131]
    E --> F[8卡 32-update smoke]
    F --> G[128-update pilot]
    G --> H[C1/C0R 机械完成：14,880 updates]
    H --> I[Q4 val_dev：4卡内部配对]
    I --> J[CPU 审计 + 一次性输入选择收据]
    J --> K[只开一次 val_locked：已完成]
    K --> L[结果：C1 单臂 PASS；G_abs R² 腿规格错误，pooled 重算 19/19]
    L --> M[锁定集额度用尽；C2/C3 由自身条件决定]
    M --> N[正式 simulator 与 C0S/C4/C5]
    N --> O[完整多划分、多种子、消融与论文证据]
```

### 0.3 截至本快照的状态

| 模块 | 状态 | 可以得出的结论 |
|---|---|---|
| 11,904 → 14,880 精确续训 | 已完成 | 旧训练谱系被可靠恢复，新增 2,976 updates，M9 31/31 通过 |
| E0：11,904 与 14,880 的 Q1/Q2/Q3 | 已完成并封账 | 两者事实预测近似对齐；都使用状态、都具有响应保真，但都未证明 hot-dry 特异增强 |
| Candidate C 模型、训练器、评测器与合同 | 代码与 CPU 阶段完成 | 131/131 CPU 回归通过；这只证明实现与合同，不证明科学效果 |
| 第三次 8 卡 smoke | **已通过** | 32 updates、8 ranks、checkpoint/reload 和合同检查均通过；唯一非致命缺口是 detached launcher 未收割真实 exit code |
| 128-update pilot | **机械上完成，但验收合同被阻塞** | 128 steps 与 9/9 可计算判据通过；P6 要求一次 GPU `val_dev`，但原 `val_interval=372` 使其在 128 步内不可能触发 |
| C1 / C0R Phase-II 输出 | **均已机械完成** 14,880 步（2026-08-22/23） | 4 卡和 8 卡各一对；两对不可混比。锁定评测固定使用 4 卡内部 pair；其启动配置偏离早期 8 卡冻结合同，故只能称 qualified evidence |
| 新 Q4 组合性结果 | **`val_locked` 已完成并封存**（2026-08-24） | C1 四门 PASS（`verdict=PASS`）；C0R `composed_vs_direct`/`state_retention` FAIL；臂间 G_abs 的 R² 腿系规格错误，pooled 重算 19/19（A04 §19）。支持稳定性信号与事实非劣；仍不得声称预注册 per-cube R² 版 G_abs 通过 |
| simulator 校准 C4/C5/C0S | 硬阻塞 | 当前没有正式情景库、EO↔simulator 映射和冻结 manifest，严禁伪造 |

### 0.4 我们离正式训练还有多远

**2026-08-24 补记：P6 阻塞已解除，正式训练已完成。**
C1 与 C0R 各跑满 14,880 步（4 卡对与 8 卡对），Q4 已在 `val_dev` 上产出结果。
详情见 §14.1 和 A04 §15；下方保留原文作为历史决策记录。

原文（2026-08-21，历史记录）：

> 目前唯一阻止正式训练的硬门是 **P6 的合同矛盾**：pilot 要求至少一次真实 8 卡 `val_dev`，但训练器只在 `step % val_interval == 0` 或 `step == total_steps` 时评估；已有 pilot 是 128 steps，正式 `val_interval=372`，所以评估永远不会发生。
>
> 推荐的最小、科学上最干净的修复是：经用户明确授权后，新建一个**独立 372-update validation-capable pilot**，保持正式 C1 的全部科学参数和 `val_interval=372` 不变，只将该 pilot 的 `stop-after-step` 从 128 改为 372。这样既能在第一个正式验证点真实跑一次 `val_dev`，又不修改正式 C1/C0R 合同。新 pilot 必须使用全新目录、重新做 GPU 空闲门和验收；它不是正式训练，也不需要重做已通过的 smoke。
>
> 在这项修复通过前，不能写 `FORMAL_READY`，也不能启动正式 C1。若它通过，才按冻结队列运行 C1，再机械触发 C0R。

---

## 1. 研究背景：我们为什么需要“状态”，而不只需要预测器

### 1.1 EO 预测的困难

遥感时间序列并不是一部连续、无噪声的地表录像。它常见以下问题：

- 云、云影和传感器缺测使过去观测不完整；
- 不同区域、地类、季节和极端天气构成分布偏移；
- 未来地表既依赖历史状态，也依赖未来天气 forcing；
- 真实世界没有方便获得的“同一地块、同一时刻、只替换一种未来天气”的成对反事实标签。

普通预测器可以从过去直接输出某个 horizon 的未来值，但即便分数不错，也不能自动说明它学到了可递推的地表状态。模型可能只是记住固定 horizon 的统计相关性。

### 1.2 本项目中的“预测状态”

设：

- `H_t`：截止时刻 `t` 的 EO 历史；
- `w_{≤t}`：过去天气；
- `u_{a:b}`：区间 `(a,b]` 的未来天气 forcing；
- `g`：地理或静态信息；
- `z_t`：模型推断的潜在地表状态；
- `F`：共享状态转移算子；
- `O`：把状态解码为 EO 预测的观测头。

Candidate C 的目标接口为：

$$
z_t=q(H_t,w_{\leq t},g),
$$

$$
z_b=F(z_a,u_{a+1:b},g,\Delta t),
$$

$$
\hat y_b=O(z_b)+b(H_t,w_{\leq t},g).
$$

其中 `b` 是不读取未来天气的 context prior。未来天气只能通过 `F` 影响未来状态，因此我们可以检查模型究竟有没有使用天气、状态是否承载预测信息，以及换天气后从哪一时刻开始改变。

### 1.3 “状态”需要同时满足哪些性质

一个有用的预测状态至少需要逐级通过以下证据：

1. **事实准确（factual）**：真实未来天气下，预测不能明显变差；
2. **承载信息（load-bearing）**：合法移除状态贡献后，预测应显著变差；
3. **响应可信（response fidelity）**：真实天气的预测应优于错误或平均天气控制；
4. **可组合（compositional）**：一次走完整区间与分段递推，在未见分段上应保持一致且不坍塌；
5. **校准（calibrated）**：对成对 forcing 的方向、幅度和时间响应应接近可信参照；
6. **外推（extrapolative）**：未见 forcing 组合下不出现任意放大或失真。

这些性质构成一条证据阶梯。后一级不能用代码功能替代，也不能跳过前一级。

---

## 2. 从旧 TerraState 到 Candidate C：真正改变了什么

### 2.1 旧接口已经解决了什么

旧 TerraStateV2 已实现以下隔离：

- 状态编码器 `q` 和 context prior 不读取未来天气；
- 未来天气只经状态转移分支进入；
- 在真实未来天气下可完成事实预测；
- Q2 证明状态分支对输出是有用的；
- Q3 证明真实天气相对 donor/mean 控制具有更好的响应保真。

这为 Candidate C 提供了可信起点，但旧接口仍主要是从同一个 `z_t` 直接查询不同 horizon：

$$
z_{t+h}=T(z_t,u_{t+1:t+h},g,h).
$$

它没有充分证明：先推进到中间时刻得到的状态，能否作为下一段的合法起点继续推进。

### 2.2 Candidate C 的关键升级

Candidate C 把“按 horizon 查询”升级为“共享的可变跨度转移”：

$$
z_{t+h_1+h_2}^{\mathrm{direct}}
=F(z_t,u_{t+1:t+h_1+h_2},g,h_1+h_2),
$$

$$
z_{t+h_1+h_2}^{\mathrm{composed}}
=F(F(z_t,u_{t+1:t+h_1},g,h_1),u_{t+h_1+1:t+h_1+h_2},g,h_2).
$$

理想情况下，两条路径不要求逐位相同，但应在事实预测、状态结构和输出上近似一致。更重要的是，这两条路径共享同一个 `F`，却走不同计算图；这使“组合性”成为可被失败、控制和统计检验约束的科学问题。

### 2.3 这不是简单“加大模型”

当前 Candidate C：

- 继承 verified 14,880 的全部 255 个模型张量；
- 不新增可训练参数；
- warm start 后逐键、逐 shape 检查，继承张量最大绝对差为 0；
- 主要改变调用接口、递归路径、训练臂和评测合同。

这是一项重要控制：若 Arm-C1 和 Arm-C0R 出现差异，不能轻易归因于“C1 参数更多”。但“没有新增参数”本身也不是科学结论，仍需通过正式对照实验。

### 2.4 中途换天气为什么重要

对同一历史和同一中间状态，我们可以在时刻 `s` 后把天气 `u` 换成 `u'`：

- `s` 之前的状态和输出必须不变；
- `s` 之后应产生变化；
- 变化应通过 `F` 进入，不能倒灌到过去；
- 未来 EO 标签不得成为模型输入。

这个合同既检查 future leakage，也让“干预”具备明确的时间方向。但它只说明接口能受控换天气，不等于响应已经经过真实反事实校准。

---

## 3. 两条最终科研主张，以及它们需要什么证据

为避免命名混乱，本文把论文主张称为“主张-组合”“主张-校准”，把实验配置称为“Arm-C1、Arm-C2……”；二者不是同一套编号。

### 3.1 主张-组合：可组合预测状态

目标表述：模型状态可由共享转移算子跨多个时间段递归推进，并在未见分段方式上保持事实准确、路径一致、优于破坏性控制且不坍塌。

完整证据链为：

1. direct 与 composed 各自通过事实非劣门；
2. Q2 仍成立，说明状态继续服务输出；
3. held-out partitions 上 composed MSE 不超过 direct 的 1.05 倍；
4. 组合优势 `A_comp` 的 pooled CI 下界大于 0；
5. 至少一半 held-out partition 的 ratio 小于 1；
6. 状态标准差和 effective-rank retention 均不低于 0.5；
7. 天气顺序打乱、分段错配、identity state、constant state 等坏对照显著更差；
8. weather-switch 满足“切换前不变、切换后变化”。

只通过 1–2 项不能宣称组合性；代码能递归运行也不能替代以上统计证据。

### 3.2 主张-校准：干预响应校准

目标表述：在适用范围内，模型对未来 forcing 的响应不仅“发生变化”，而且方向、幅度和时间结构与冻结的成对参照一致，同时不损害真实 EO 事实预测。

所需证据至少包括：

- factual gate；
- 响应方向；
- 响应幅度；
- onset/peak timing；
- held-out forcing；
- 空间和时间图像逻辑；
- 对 simulator 适用地类和 domain gap 的诚实披露。

若只通过方向以及“幅度/时间”之一，最多写 `PARTIAL_CALIBRATION`。如果仅 simulator 指标强、真实 EO 指标下降，必须报告 domain gap，不能称完整成功。

### 3.3 现在能否宣称这两条主张

不能。当前正式 Arm-C1/Arm-C0R 尚未产出，而组合损失和 simulator 校准臂更未运行。现在已经具备的是：可信旧锚点、旧 Q1/Q2/Q3 证据、Candidate C 的工程实现、冻结合同和 CPU 测试。

---

## 4. Q1、Q2、Q3、Q4 分别在问什么

| 问题 | 直观问题 | 核心方法 | 能支持什么 | 不能支持什么 |
|---|---|---|---|---|
| Q1 | 预测准不准？ | 在冻结 split 上计算 R²、RMSE、NSE、bias 等 | 事实预测能力与分布偏移下表现 | 不能证明状态有用、可组合或因果 |
| Q2 | 状态真的参与预测吗？ | 在合法推理路径中移除或替换状态贡献，做 paired 比较与 CI | `load-bearing state` | 不能证明全部信息只经状态，也不是因果识别 |
| Q3 | 模型真的用对了未来天气吗？ | 固定历史/状态/地理/horizon，比较 actual 与 donor/mean weather | response fidelity | 不能证明真实反事实、hot-dry 特异性或 simulator 校准 |
| 新 Q4 | 分段走与一次走是否都可靠？ | held-out partitions、direct/composed、坏对照、noncollapse、Q2 联合门 | compositional predictive state | 结构单测或固定已见分段不能单独证明组合泛化 |

### 4.1 Q1：事实预测

Q1 首先保证模型不是为了内部结构而牺牲任务本身。R² 越高通常越好，RMSE 越低越好；但不同数据划分、归一化和聚合方式的数值不能直接混比。

### 4.2 Q2：状态承载

Q2 不是随意把某个隐藏层清零。它要求在模型定义允许的推理路径中构造 removal arm，并对同一批样本比较完整模型和控制模型。paired bootstrap CI 排除 0，才有较强证据说明状态贡献不是偶然。

### 4.3 Q3：响应保真

Q3 使用真实未来天气 `actual`、其他样本天气 `donor`、平均天气 `mean`。若 actual 的损失显著低于 donor/mean，说明模型对实际天气响应更忠实。但真实世界没有提供“同一地块只改变天气”的直接标签，所以 Q3 仍是响应保真诊断，不是因果反事实证明。

### 4.4 新 Q4：组合性

新 Q4 的重点是“未见分段方式”。例如总长度 20 个时间步：训练可见 `(20)`、`(10,10)`、`(10,5,5)`、`(5,5,5,5)`，评测可保留 `(8,12)`、`(2,18)`、`(2,6,12)`、`(1,4,6,9)`。如果模型只会训练时固定结构，held-out partition 会暴露这一点。

必须注意：代码中 `one_segment == direct` 或包装器 bit-exact，只能证明 API 语义正确；真正的 Q4 证据来自 held-out 性能、composition gap、坏对照、状态秩和 Q2 的联合结果。

---

## 5. 实验臂为什么这样设计

| 实验臂 | 作用 | 当前状态 | 主要排除的替代解释 |
|---|---|---|---|
| C0 | 旧 AAAI direct-horizon 基准 | 历史模型 | 提供旧事实起点，不是同预算 Phase-II 对照 |
| C0R | 同父权重、同预算的 direct Phase-II control | 已冻结，未训练 | 排除“只是多训练 2,976 updates” |
| C1 | recursive/segment，composition loss 为 0 | 已冻结，未训练 | 测递归接口本身是否有效或伤害事实性 |
| C2 | C1 + latent composition | 规划中 | 测内部状态路径一致约束的增量 |
| C3 | C2 + output composition | 规划中 | 测任务输出一致约束的增量 |
| C4 | C3 + paired calibration | 被 simulator 阻塞 | 测天气响应是否变得更正确，而不只是会变 |
| C5 | C4 + noncollapse/full method | 被 simulator 阻塞 | 完整方法候选 |
| C6 | C5 去掉 noncollapse | 后续消融 | 验证防坍塌约束是否必要 |
| C7 | 加/去旧 future-state anchor | 后续按需 | 验证旧 anchor 是否必要，不能预设必要 |
| C0S | direct + 与 C4/C5 完全匹配的 simulator 监督 | 被 simulator 阻塞 | 排除收益仅来自更多样本、标签或 updates |

### 5.1 当前为什么先跑 C1 与 C0R

C1 和 C0R 使用相同：父权重、数据、seed、batch、更新数、优化器、学习率和四个辅助损失权重。冻结合同中只有 `arm` 和 `factual_path` 不同：C1 为 recursive，C0R 为 direct。

因此这对实验优先回答最干净的问题：**在不增加参数、不给 composition loss、不给 simulator 数据的条件下，仅把事实训练路径改成递归接口，会发生什么？**

C0R 必须在 C1 机械完成后运行，触发条件不是 C1 指标好坏。这防止“只有 C1 好看才跑对照”的选择性报告。

### 5.2 C0R 与 C0S 不同

- C0R：当前真实 EO 阶段的同更新 direct control；
- C0S：未来 paired simulator 阶段的监督量公平 direct control。

C0R 不能替代 C0S。等 C4/C5 启动时，C0S 还要严格匹配 simulator sample IDs、可观测 labels、exposures、domain mix、optimizer updates、seed、选择规则和最好也匹配计算预算。

---

## 6. 训练目标：每个损失负责什么

完整候选目标为：

$$
\mathcal L=
\mathcal L_{EO}
+\lambda_z\mathcal L_{cmp}^{z}
+\lambda_y\mathcal L_{cmp}^{y}
+\lambda_{pair}\mathcal L_{pair}
+\lambda_{nc}\mathcal L_{noncollapse}.
$$

| 项 | 直观含义 | 主要风险 |
|---|---|---|
| `L_EO` | 用真实 EO 标签保证事实预测 | 单独使用不保证组合性 |
| `L_cmp^z` | direct 与 composed 的终态接近 | 可能被常数状态投机满足 |
| `L_cmp^y` | 两条路径的任务输出接近 | 输出接近不必然说明状态结构健康 |
| `L_pair` | 用同一 simulator 情景下的 paired trajectory 校准响应 | 没有正式 paired truth 时绝不能启用 |
| `L_noncollapse` | 用方差、去相关、运动/秩诊断防止状态坍塌 | 权重过大可能损害事实预测 |

### 6.1 当前各阶段的真实 λ

- 正式 Arm-C1 与 Arm-C0R：`λ_z=0, λ_y=0, λ_pair=0, λ_nc=0`；
- 32-update smoke：`λ_z=0.1, λ_y=1.0, λ_pair=0, λ_nc=0.01`；
- 128-update pilot：严格继承正式 C1，四个 λ 都为 0；
- `λ_pair=0.5` 只可作为未来的候选起点，当前未被正式数据验证。

所以，本轮 C1/C0R 即使完成，也只能回答 recursive 与 direct 的差异，不能宣称 composition loss 或 noncollapse loss 已经有效。smoke 中非零 λ 的作用是检查计算图、梯度路由和数值稳定性，不是选正式超参数。

### 6.2 为什么要先测 loss/gradient scale

不同损失的数值大小和梯度大小可能相差几个数量级。直接照搬 `0.1/1.0/0.5/0.01` 会导致某一项支配训练。正式启用 C2–C5 前应：

1. 在 held-out validation 之外的 pilot 数据上记录每项 raw loss；
2. 记录各项对目标模块的梯度范数；
3. 先冻结 log-grid 或候选集合与相同 tuning budget；
4. 只用 validation factual floor、composition/calibration 规则选择；
5. 在看 test/OOD 前冻结最终 λ。

这比给出一个未经量纲分析的单点“最佳 λ”更科学。

## 7. 数据、时间轴与防泄漏设计

### 7.1 当前 EO 数据角色

当前 Candidate C 的正式真实 EO 阶段使用：

- 训练集：23,816 cubes，85 个地理组；
- 验证集：952 cubes；
- `val_dev`：476 cubes、40 个 S2 tiles，用于开发、pilot 和训练期监控；
- `val_locked`：476 cubes、40 个 S2 tiles，只在 `FORMAL_READY` 后按合同打开一次；
- tiles/地理组不得跨 `val_dev` 与 `val_locked`。

`val_locked` 应称为“Candidate C 阶段的锁定验证门”，不应写成从项目诞生起完全未见的外部 test，因为历史 E0 曾在完整 validation 上做过汇总。真正的 OOD/test 仍禁止用于调参和 checkpoint 选择。

### 7.2 时间单位与 Q4 partitions

冻结协议以一个模型时间步约 5 天计：

- 10 步约 50 天；
- 15 步约 75 天；
- 20 步约 100 天。

训练侧 partitions：

- 10：`(10)`、`(5,5)`、`(5,3,2)`；
- 15：`(15)`、`(7,8)`、`(7,4,4)`；
- 20：`(20)`、`(10,10)`、`(10,5,5)`、`(5,5,5,5)`。

held-out partitions：

- 10：`(3,7)`、`(6,4)`、`(2,3,5)`；
- 15：`(4,11)`、`(3,5,7)`；
- 20：`(8,12)`、`(2,18)`、`(2,6,12)`、`(1,4,6,9)`。

两组必须完全不交。控制 seed 为 4242，破坏性控制包括天气顺序打乱、分段天气错配、identity state 和 constant state。

### 7.3 什么是 future leakage

未来 EO 是监督标签，不是模型输入。未来天气是合法条件，但只能经 `F` 影响状态。项目用以下不变量检查“偷看答案”：

- 只扰动未来 EO，context prior 和 `z_t` 必须逐位不变；
- 只扰动未来天气，context prior 和 `z_t` 必须不变，而完整未来预测应改变；
- `alpha0`/context-only 路径不得随未来天气改变；
- weather switch 前状态逐位一致，switch 后状态才允许变化；
- held-out partitions 和 broken controls 不得进入训练更新。

这些测试主要排除实现泄漏；它们不能代替真实泛化评测。

### 7.4 manifest、SHA 与 provenance

可以把三者理解为：

- **manifest**：实验“名单和规则书”，规定用哪些样本、情景、划分和参数；
- **SHA-256**：字节“封条”，用于证明某个文件没有悄悄变化；
- **provenance**：实验“物流单”，记录权重从哪里来、用什么代码/数据/环境/命令产生了什么输出。

SHA 相同只证明字节相同，不证明内容科学正确。当前部分数据指纹仅基于排序后的相对路径与文件大小，能够发现增删或大小变化，却可能漏掉“路径和大小都不变、内容被改”的情况。最终论文归档最好补充数据版本快照或分层内容哈希。

---

## 8. 权重谱系：11,904、历史 14,880、verified 14,880

### 8.1 三个身份不能混为一谈

| 角色 | Logical ID | File SHA-256 | 大小 | 说明 |
|---|---|---|---:|---|
| 历史边界/续训父节点 | `terrastate/v2/legacy-boundary11904@v1` | `644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd` | 37,972,401 B | step 11,904，stage 2，旧 Q1–Q3 历史证据来源 |
| verified 续训端点/默认新锚点 | `terrastate/v2/verified-resume14880@v1` | `a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f` | 44,302,057 B | 本次从 11,904 验证续训得到，Candidate C 默认父权重 |
| 历史完整日程端点 | `terrastate/v2/historical-full14880@v1` | `99f15a35fb9a356901c995bb0f48280a4da236f6970d0dd06343a28857fe2b8b` | 44,300,969 B | 原 uninterrupted run 的历史文件 |

verified 14,880 与 historical 14,880 的 255 个模型张量逐值相同，`value_sha16=aa98fbd2fa302727`，最大绝对差为 0；它们的完整文件 SHA 不同，是因为 checkpoint 的元数据、RNG 或保存上下文不同。11,904 与 14,880 的模型权重并不相同。

### 8.2 11,904 → 14,880 是 exact resume

旧谱系的恢复包括模型、optimizer、scheduler、每 rank RNG 和数据位置等，并修复了边界 stage 的 off-by-one 语义。正式续训：

- 8×H200；
- 2,976 optimizer updates，即 8 epochs；
- per-GPU batch 8、gradient accumulation 1、global batch 64；
- 372 updates/epoch；
- branch LR `3e-5`；
- q LR scale `0.033`，即约 `9.9e-7`；
- warmup 300；
- AdamW，weight decay 0，gradient clip 1；
- seed 42；
- q prefix `core.blocks.2.`，state dimension 256。

M9 验收 31/31 通过，`teacher_unchanged=true`、`stage3_qgrad_seen=true`。这一步的目的首先是修复权重谱系和恢复语义，不是重新挑一个 OOD 最优 checkpoint。

### 8.3 verified 14,880 → Candidate C 是 weights-only fork

Candidate C 会载入全部 255 个父模型张量，但故意不继承父训练的 optimizer、scheduler、RNG 和 global step：

- 新 optimizer；
- 新 scheduler；
- 新 RNG 流；
- Phase-II `step=0`；
- lineage 记录 parent logical ID、路径、file SHA 和 model-value SHA。

因此应写“以 14,880 权重初始化一个新的 Phase-II 分支”，不能写“从 14,880 exact resume 继续原训练”。只有 Candidate C 自身中断后，在同一 Phase-II 合同中恢复模型、optimizer、scheduler、RNG 和数据位置，才属于 exact resume。

### 8.4 为什么 14,880 仍是默认锚点

14,880 是在看本轮 E0 OOD 结果前就冻结的扩展端点。E0 发现它相对 11,904 的 Q1 有极轻微下降，但差异远小于描述性 `0.01` 阈值。我们不按 OOD 结果回选 checkpoint，否则会产生 cherry-picking。

11,904 继续保留为：

- 历史证据来源；
- exact-resume 父节点；
- supplementary checkpoint-sensitivity 参照；
- 必要时预注册的辅助初始化敏感性 arm。

它不因本轮结果而替换 14,880 的默认 Phase-II anchor。

---

## 9. 已完成的关键结果：E0 到底告诉了我们什么

E0 v3 已正式封账：6 个同协议任务通过，732 checks、0 failed；11,904 历史参照 57/57 数值叶 bit-exact 复现。以下 `Δ` 均为 `14,880 − 11,904`。

### 9.1 Q1：事实预测几乎完全对齐

| Split | 指标 | 11,904 | 14,880 | Δ |
|---|---:|---:|---:|---:|
| Validation，n=952 | R² | 0.4973219642 | 0.4970935562 | -0.0002284080 |
| Validation，n=952 | RMSE | 0.1572881669 | 0.1573339951 | +0.0000458281 |
| OOD-t，n=1904 | R² | 0.5693493612 | 0.5692781483 | -0.0000712129 |
| OOD-t，n=1904 | RMSE | 0.1505941191 | 0.1506271192 | +0.0000330001 |

两处 `|ΔR²|<0.01`，所以可描述为“基本对齐”。它不是经过统计等价性检验的“完全相等”，也不能说 14,880 提升了 Q1；准确说法是**事实能力几乎保持，点估计极轻微下降**。

### 9.2 Q2：两者的状态都继续承载预测信息

| Split | 量 | 11,904 | 14,880 |
|---|---|---:|---:|
| Validation | official full−alpha0 ΔR² | 0.0112144242 | 0.0122623688 |
| Validation | paired mean | 0.0161625260 | 0.0171614514 |
| Validation | paired 95% CI，n=589 | [0.0064324081, 0.0259022958] | [0.0073616461, 0.0269625763] |
| OOD-t | official full−alpha0 ΔR² | 0.0199720103 | 0.0203318513 |
| OOD-t | paired mean | 0.0219977686 | 0.0222476481 |
| OOD-t | paired 95% CI，n=1019 | [0.0142198986, 0.0301760693] | [0.0143654012, 0.0304918869] |

两者均通过 `dr2_floor=0.005` 且 CI 下界大于 0，裁决都是 `LOAD_BEARING`。14,880 保持并略增强 Q2 点估计。

`T_identity` 的结果仍标记 `transition_margin_clean=false`，因此可用作“状态转移参与了预测”的辅助证据，不能提升为“这一具体转移形式具有必要性”。

### 9.3 Q3：响应保真成立，hot-dry 特异增强不成立

冻结审计使用 OOD-t 84 pairs、45 个唯一 controls、31 个地理 clusters、10,000 次 bootstrap。

| 指标 | 11,904 | 14,880 |
|---|---:|---:|
| actual R² / RMSE | 0.6253516463 / 0.1491516260 | 0.6268869271 / 0.1489683766 |
| donor R² / RMSE | 0.5893404938 / 0.1584189321 | 0.5888111442 / 0.1582941263 |
| mean R² / RMSE | 0.5430064799 / 0.1970936896 | 0.5426842406 / 0.1973694314 |
| donor control−actual loss | 0.0025654681 | 0.0025695094 |
| donor geo 95% CI | [0.0011187122, 0.0039874911] | [0.0011268149, 0.0039868076] |
| mean control−actual loss | 0.0112613323 | 0.0113893372 |
| mean geo 95% CI | [0.0054656245, 0.0170799321] | [0.0055480442, 0.0172659392] |

两者都是：

- endpoint fidelity：`PASS`；
- hot-dry enhancement：`FAIL`；
- overall：`Q3_RESPONSE_FIDELITY_ONLY`。

科学上应表述为：状态对未来天气具有可检测的响应保真，actual 优于 donor/mean；在当前 checkpoint 和协议下，没有证据支持 hot-dry-specific enhancement。不能把这个失败归因成“架构固有限制”，除非有额外消融证据。

### 9.4 E0 的最终决策

E0 关闭了“11,904 与 14,880 是否错位”的工程与证据风险：

- 11,904 的历史数值被精确复现；
- 14,880 的事实能力基本保持；
- Q2 与 Q3 的主要合同保持；
- 14,880 继续作为 Candidate C 默认锚点；
- 11,904 作为历史/父节点/supplementary 保留；
- 旧模型仍不能宣称组合性、因果反事实或 hot-dry 特异性。

---

## 10. Candidate C 已经实现了什么

### 10.1 模型与 API

`terrastate/models/terrastate_candidate_c.py` 已实现：

- 继承 TerraStateV2，无新增参数；
- 任意 N 段的共享状态递推；
- direct 与 composed 路径；
- mid-course weather switch；
- Q2 removal arms；
- state standard deviation、movement 和 effective rank；
- VICReg 风格 noncollapse；
- 在缺少正式 simulator truth 时对 `L_pair` fail closed；
- synthetic fixture 明确标注只用于 schema/shape 测试。

### 10.2 训练器与安全语义

训练线已实现或复用了：

- 8-rank DDP/global-batch 合同；
- 权重身份、key、shape 和 value SHA 检查；
- fresh output directory，拒绝覆盖旧 run；
- 原子 checkpoint 写入与 CPU reload；
- finite 检查和所有 rank 对称跳过；
- Candidate C phase 内 checkpoint roundtrip/exact resume；
- 每 rank RNG、epoch/micro/data position 的恢复；
- 配置、代码、环境、数据和命令 provenance；
- `--stop-after-step` 用于 smoke/pilot，而不改变正式 `total_steps=2976`。

### 10.3 评测器

新 Q4 evaluator 已覆盖：

- train/held-out partition 结构检查；
- direct/composed endpoint；
- weather-order shuffled；
- segment-weather mismatch；
- identity/constant state；
- composition advantage 与置信区间；
- state retention/noncollapse；
- Q2 联合 gate；
- C1 与 C0R 的同协议绝对比较。

正式使用前仍要解决一项统计合同冲突：Q4 manifest/evaluator 当前倾向 `paired minicube bootstrap, B=10000`，selection contract 记录了 `geo-clustered bootstrap, B=2000`。两者会产生不同置信区间，必须在看正式 Q4 结果前选择唯一 canonical 口径并重新冻结相关 SHA，不能结果出来后选更有利的一套。

**2026-08-24 补记：上述冲突已解决。** 裁决规则：四道门（broken_control / composed_vs_direct / state_retention / semigroup_bit_exact）内部使用 `minicube-paired bootstrap B=10000`；臂间 G_abs 绝对比较门单独使用 `geo-clustered bootstrap（tile 聚类）B=2000`，由 selection_contract 冻结件决定。两者服务不同合同、不可互换。结论写进源码常量与结果 JSON，任何后续会话可复核。

### 10.4 CPU 验收

当前记录为 119/119 通过，包括：

- parent 255 tensors 完整载入、最大差 0；
- future leakage 不变量；
- direct、2 段和多段 forward/backward；
- weather switch 前后语义；
- 各 loss 的梯度路由；
- held-out/broken controls 不更新；
- collapse fixtures；
- checkpoint roundtrip；
- 2-rank gloo exact resume；
- launcher 正负例与配置一致性。

这些结果说明代码有资格进入 GPU smoke，不说明模型已经学会组合性。

---

## 11. 当前正式训练合同

### 11.1 C1 与 C0R 的共同参数

| 项目 | 冻结值 |
|---|---:|
| 父权重 | `terrastate/v2/verified-resume14880@v1` |
| GPU / world size | 8×H200 / 8 ranks |
| per-GPU batch | 8 |
| gradient accumulation | 1 |
| global batch | 64 |
| 训练 cubes | 23,816 |
| updates/epoch | 372 |
| epochs / total updates | 8 / 2,976 |
| checkpoint interval | 372 |
| validation interval | 372 |
| 唯一主 checkpoint | update 2,976 |
| seed | 42 |
| state dimension | 256 |
| 时间步 | 5 天 |
| branch LR | `3e-5` |
| q LR scale / q LR | `0.033` / `9.9e-7` |
| warmup | 100 updates |
| scheduler | warmup 后 cosine，到 update 2,976 |
| optimizer | AdamW，betas `(0.9,0.999)` |
| weight decay | 0 |
| gradient clip | 1 |
| data workers | 8 |
| q prefix | `core.blocks.2.` |
| EO trajectory / endpoint weight | 1 / 1 |
| 四个辅助 λ | 全部 0 |

训练样本数除以 global batch：`23816 // 64 = 372`，每 epoch 因 `drop_last` 实际处理 23,808 个样本，剩余 8 个被丢弃。sampler 每 epoch 重洗牌，因此“8 epochs”表示大约八遍数据，不意味着每个 cube 恰好被看到八次。

### 11.2 唯一正式差异

- Arm-C1：`arm=C1`，`factual_path=recursive`；
- Arm-C0R：`arm=C0R`，`factual_path=direct`。

其余 39 项关键参数一致。正式配置禁止临时 `--set` 覆盖。

### 11.3 OOM 回退

若 per-GPU batch 8 发生 OOM，只允许对两个 arm 同时改为：

```text
per-GPU batch: 4
gradient accumulation: 2
global batch: 仍为 64
```

修改后必须重新冻结两臂配置并重跑 resume/parity 测试。不能只给某一臂减少 batch，也不能因吞吐不满意临时改变 total updates。

### 11.4 checkpoint 选择

本轮主 checkpoint 固定为 update 2,976，不按 OOD/test 或训练曲线事后回选。`val_dev` 用于运行期诊断；`val_locked` 只在 `FORMAL_READY` 后按合同打开。OOD/test 不参与 λ、arm 或 checkpoint 选择。

---

## 12. CPU、smoke、pilot、formal 分别是什么

### 12.1 CPU 测试：证明“逻辑能被检查”

CPU 测试快、便宜，适合检查 shape、数据泄漏、梯度路由、配置解析、checkpoint schema 和小规模 DDP 恢复。它不具备真实 8 卡显存、NCCL、吞吐和大 batch 行为，因此不能直接进入论文结果。

### 12.2 Smoke：证明“真实 GPU 路径能跑”

第三次 smoke 已经通过。它的合同为：

- 8-rank；
- 正式 `total_steps` 仍为 2,976；
- 使用 `stop-after-step=32` 提前停止；
- 检查 8 ranks、forward/backward、损失/梯度 finite、显存、checkpoint、CPU reload 和至少一次恢复；
- λ 为 `0.1/1.0/0/0.01`，仅用于覆盖计算图。

前两次 smoke 均在 0 训练 step、0 checkpoint 时 fail closed：

1. 错误地把 `λ_pair=0.5` 带入没有 simulator truth 的配置；
2. validation selector 写成不存在的 `splits.val_dev.ids`，正确路径是 `validation_subsplit.val_dev.ids`。

两处根因已在生成器、配置和 preflight 源头修复。第三次 smoke 实际完成 32 updates，并产出可加载 checkpoint；22 项检查中 21 项通过、0 项致命失败。唯一登记为 warning 的缺口是 detached launcher 没有收割进程 exit code，正式 run 必须补强该记录。这说明 smoke 是发现配置、环境和分布式问题的保险丝，而不是一个小型效果实验。

### 12.3 Pilot：证明“正式合同的动态可接受”

已完成的 pilot 为 128 updates，严格继承正式 C1 参数，唯一允许的差异是 `stop-after-step=128`。它完成了 128 个 updates：无 OOM、无 NaN/Inf、末 20 步/首 20 步总损失比为 0.818、LR 与冻结 schedule 逐点一致、checkpoint 可加载、参数未漂移、未访问禁止 split。它的实测训练时间约 109 秒，约 1.17 updates/s。

它原本应只观察 `val_dev`，重点记录：

- 吞吐与 ETA；
- 总损失和分项损失；
- 梯度范数；
- LR 曲线；
- 显存余量；
- NaN/Inf/OOM/NCCL；
- checkpoint 完整性和恢复。

但该 pilot 没有产生一次 GPU 上的 `val_dev`，不是因为 validation 失败，而是 P6 与 `128 < val_interval=372` 数学冲突。因此 `pilot_verdict=PASS_EXCEPT_P6_UNSATISFIABLE`，且它正确阻止 formal launch。pilot 不能作为论文主结果，也不能拿 OOD 指标挑配置。

### 12.4 FORMAL_READY 与正式训练

只有 smoke、validation-capable pilot 的全部硬门通过、运行环境和源码 SHA 重新绑定、GPU 资源安全检查通过后，才能写 `FORMAL_READY`。

正式队列严格为：

1. Arm-C1，2,976 updates；
2. C1 跑满且主 checkpoint 可加载后，无论指标好坏，启动 Arm-C0R，2,976 updates；
3. 两臂完成后先做同协议 validation 和 Q4，再决定 C2/C3，而不是直接跳到完整方法。

## 13. 从零理解训练：本项目涉及的机器学习知识

### 13.1 这是“大模型项目”吗

TerraState 使用深度神经网络、分布式训练和大规模时空数据，但它不是以文本 token 为输入的通用大语言模型（LLM）。它更接近一个**面向 EO 与天气条件的时空世界模型/状态空间模型**。

两者共享的技术包括：Transformer 类模块、潜在表示、AdamW、学习率调度、混合精度、DDP、checkpoint 和严格评测；但任务、数据和输出不同：

- LLM 主要建模文字 token 的条件分布；
- TerraState 建模地表观测、潜在状态与天气驱动下的时序演化；
- LLM 的“幻觉”通常指文本事实错误；本项目更关心泄漏、分布偏移、状态坍塌、响应失真和伪组合性。

所以可以借鉴“大模型训练工程”，但不能直接套用语言模型的评价标准。

### 13.2 权重、optimizer、scheduler、RNG

把训练想象成在山地中寻找低损失位置：

- **模型权重**：当前位置，承载已经学到的映射；
- **optimizer**：走路方式和惯性，AdamW 还保存一阶/二阶动量；
- **scheduler**：每一步走多远的时间表，即学习率曲线；
- **RNG**：随机抽样、shuffle、dropout 等随机过程的状态；
- **global step**：已经做了多少次 optimizer update；
- **checkpoint**：把以上关键状态和数据位置一起保存的快照。

只加载权重相当于“从已有位置出发，但换一套走路惯性和时间表”；这就是 weights-only fork。加载全部训练状态并回到正确的下一 batch，才是 exact resume。

### 13.3 Batch、gradient accumulation、update 与 epoch

8 卡 DDP 中，每张 GPU 有一个模型进程。每张卡先对自己的 mini-batch 算梯度，随后通过 all-reduce 合并，再共同做一次 optimizer update。

$$
\text{global batch}
=\text{per-GPU batch}\times\text{world size}\times\text{gradient accumulation}.
$$

本项目是 `8 × 8 × 1 = 64`。一个 update 不是“某一张卡处理一个 batch”，而是八张卡同步后共同前进一步。

gradient accumulation 表示先累积多轮小 batch 的梯度再更新。例如 OOM 回退 `8×4×2=64`，保持 global batch 不变，但运行速度和数值细节仍可能变化，所以需要重新做恢复与公平性验证。

epoch 通常表示大约遍历一次训练集。本项目因为 `drop_last` 和分布式采样，不应理解为每个样本精确出现一次。

### 13.4 学习率与 warmup

学习率控制每次更新幅度。过大可能发散，过小可能学不动。warmup 在训练初期逐渐提高学习率，减少从新 optimizer 状态突然大步更新的风险；cosine scheduler 随后平滑衰减。

q 分支使用约 `9.9e-7`，远低于 branch 的 `3e-5`，表示对已学得的状态编码器更谨慎，而允许新训练路径更快适应。这是一种分组学习率策略，不等于 q 完全冻结。

### 13.5 损失、λ 与梯度路由

损失是训练优化的目标；λ 是不同目标间的权衡。某项 loss 数值很小，不代表它的梯度也小；真正影响参数更新的是梯度。

“梯度路由测试”要回答：

- 打开某个 loss 时，它是否给预期模块非零、有限的梯度；
- 关闭该 loss 时，是否不再产生对应影响；
- detached 分支是否真的不接收梯度；
- 没有 paired truth 时，`L_pair` 是否直接拒绝而不是悄悄变成 0。

### 13.6 什么是表示坍塌

假设我们要求 direct state 与 composed state 相同。最简单的作弊方式是：对所有输入都输出同一个常数状态。两条路径当然一致，但状态毫无信息。

因此要同时观察：

- 每个维度的标准差；
- 协方差/去相关；
- effective rank；
- 状态随天气和时间的 movement；
- Q2 是否仍 load-bearing；
- constant/identity broken controls 是否更差。

组合一致性只有和事实性、状态利用及 noncollapse 联合成立，才有意义。

### 13.7 R²、RMSE、NSE 与 bias

- **R²**：预测解释目标变化的程度；越高通常越好，但可为负；
- **RMSE**：平方误差开方，保留目标尺度；越低越好，对大误差敏感；
- **NSE**：水文/环境建模常用的相对均值基线指标；
- **bias**：系统性高估或低估。

单个指标可能掩盖问题，所以项目同时看多个指标、不同 horizon、地表类型和 split。

### 13.8 IID、OOD 与 held-out

- **IID**：训练与测试分布较接近；
- **OOD-t**：时间分布发生变化；
- **OOD-s**：空间分布发生变化；
- **OOD-st**：空间和时间都变化；
- **held-out partition**：总 horizon 相同，但训练未见这种时间分段方式。

OOD 不是一个单一数字。模型可能对新年份稳健，却对新区域或新分段失败，所以最终 T6 需要四 split 和五轴分层重评。

### 13.9 Bootstrap、paired CI 与 cluster

点估计只告诉我们观察到的平均差，置信区间（CI）帮助判断这个差异是否稳定。

- paired bootstrap：同一样本的两个方法成对重采样，保留配对关系；
- geo-cluster bootstrap：以地理 cluster 为单位重采样，考虑同一区域样本相关性；
- minicube bootstrap：以 minicube 为单位，样本更多但可能低估空间相关性。

统计单位会改变 CI，所以 Q4 当前 `minicube/B=10000` 与 `geo-cluster/B=2000` 的冲突必须在看结果前解决。不能看到哪个 CI 更容易过门后再选哪个。

**2026-08-24 补记：此冲突已解决**（对应 §10.3 的补记）。裁决是：两套 CI 方法服务于不同的统计合同，各自保留。四道内部门用 minicube-paired B=10000；臂间绝对比较门用 geo-clustered（tile 聚类）B=2000。

### 13.10 消融实验为什么重要

完整方法变好可能有很多原因：更多更新、更多数据、更多参数、不同随机种子、递归路径、composition loss、simulator 监督或 noncollapse。消融的目的不是简单删模块，而是让每个对照只改变一个可解释因素。

本轮 C1/C0R 的意义就在于先把“递归接口”从“额外训练预算”中分离。未来 C0S 则把 simulator 数据量/监督量从机制中分离。

### 13.11 Seed 与复现

seed=42 固定伪随机过程的起点，有利于 C1/C0R 公平配对。但 CUDA、bf16、并行规约和不同硬件可能不是逐位确定的。要区分：

- checkpoint 身份与 exact-resume 可复现；
- 同一父权重下 continuation 的随机性；
- 从头训练的完整多 seed 方差。

当前单 seed 正式臂只能支持 seed 42 条件下的结论。最终稳健性需要预注册多个 seed，且不能按 OOD 表现挑最优 seed。

---

## 14. 当前执行状态与已发生问题

### 14.1 当前状态机

**2026-08-24 补记**（下方保留原 2026-08-21 快照，加注释说明哪些已变化）：

- E0 v3：`ACCEPTED`（不变）；
- 第三次 smoke：`GPU_SMOKE_PASSED`（不变）；
- 128-update pilot：`PASS_EXCEPT_P6_UNSATISFIABLE`（不变，P6 阻塞**已通过用户决策绕行**，直接进入正式队列）；
- C1（recursive，4 卡）：**`COMPLETE`**，`run_c1_20260822T131006Z`，14,880/14,880 步，`reason=schedule_complete`；
- C0R（direct，4 卡）：**`COMPLETE`**，`run_c0r_20260823T063516Z`，14,880/14,880 步；
- C1（8 卡副本）：**`COMPLETE`**，`run_c1_8gpu_20260823T160544Z`，14,880 步；
- C0R（8 卡副本）：**`COMPLETE`**，`run_c0r_8gpu_20260823T162637Z`，14,880 步；
- Q4（val_dev，主口径 `n_valid≥64`）：**`COMPLETE`**，`q4_eval_20260824T160741Z`；
  - C1：四门全 PASS；C0R：`composed_vs_direct`/`state_retention` FAIL；臂间 G_abs：7/19 FAIL；
- Q4（唯一一次 val_locked，主口径 `n_valid≥64`）：**`COMPLETE`**，
  `q4_eval_locked_4gpu_20260824T101119Z`；
  - C1：四门全 PASS（`verdict=PASS`）；C0R：`composed_vs_direct`/`state_retention` FAIL；
    臂间 G_abs 的 R² 腿系规格错误，pooled 重算 **19/19**（A04 §19）；
- **Candidate C 总状态：`Q4_LOCKED_COMPLETE_NO_RERUN`**。

**注意**：4 卡组与 8 卡组不可混比（`world`/`accum` 差异改变梯度归约时机）；
Q4 的锁定集已经按输入收据只访问一次并封存（见 A04 §17）；不得再跑、换 pair 或以其数字调整后续训练。

启动证据链偏离（如实记录）：正式四个 run 均绕过 `launch_gpu_run.py` 直接 `torchrun`，
无 launch_record / 空闲门收据，详情见各 run 目录的 `ARM_INFO.txt` 偏离登记块和 A04 §15.1。

原 2026-08-21 快照（保留为历史记录，当时 C1/C0R 均为 PENDING）：
> - Candidate C 总状态：`BLOCKED_P6_VAL_DEV_UNSATISFIABLE_PENDING_USER_RULING`；
> - C1：`PENDING`，step 0；C0R：`PENDING`，step 0。

### 14.2 已发现并修复的四类启动风险

1. **simulator 闸门**：smoke 错带 `λ_pair=0.5`；在 GPU 训练前被拒绝；
2. **manifest selector**：配置路径写错，8 ranks 在第 0 step 退出；
3. **pilot 漂移**：派生配置原本可能改变父合同；已加入“只允许 stop-after 改为 128”的一致性 guard；随后发现 P6 与 128-step 长度/372-step 验证间隔矛盾，已 fail closed 登记；
4. **Python 环境漂移**：base Conda Python 3.13 缺少 `timm`；正式环境已冻结为 `/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python`，Python 3.11.15、PyTorch 2.12.0+cu130、NumPy 2.4.6。

这些是工程失败，不是模型科学失败；两次旧 smoke 都没有产生训练 step 或 checkpoint。

### 14.3 当前不应做什么

- 不把旧失败目录删除或改名成成功；
- 不增加第四次 smoke；
- 不把 smoke 改叫 pilot 规避预算；
- 不因 GPU 空闲就跳过环境/manifest/preflight；
- 不把 C1/C0R 当成 full Candidate C；
- 不在 simulator 缺失时启动 C4/C5/C0S；
- 不用 OOD/test 选择 λ 或 checkpoint；
- 不触碰 ObsWorld 或他人 GPU 进程。

---

## 15. 下一步决策树

### 15.0 锁定集已给出的当前决策（2026-08-24）

本节以下的 smoke/pilot/“先跑 C1/C0R”树均为保留的历史计划。它们已被实际机械完成和
一次性 `val_locked` 结果取代：C1 自身的四道 Q4 门 PASS、C0R FAIL，但 C1 相对 C0R 的
事实端点门仅 4/19，overall FAIL。最小且诚实的当前结论是：**递归接口在固定 pair 上呈现
分段稳定性信号，但没有通过“事实预测不劣”的联合门**。

`val_locked` 额度已用尽，不再访问。原「因 G_abs 未过而不启动 C2/C3」的理由已随 A04 §19 的规格错误判定失效；C2/C3 是否推进改由其自身条件决定。下一条研究工作须是一个新的、只以开发信息
冻结的诊断/设计包（例如明确的 factual-retention 诊断与预先写定的 λ 选择规则）；其目的不是
把 locked 数字调好，而是决定新问题是否值得进入 C2/C3。C0S/C4/C5 仍受 simulator 数据与
scenario 合同缺失阻塞。

### 15.1 已关闭的 smoke 门与当前 P6 决策

```text
第 3 次 smoke：PASS（32 updates，最后一次授权已使用）
                 │
                 ▼
128-step pilot：训练机械项通过，但 P6 不可满足
                 │
          ┌──────┴─────────┐
          │                │
  用户授权新 372-step pilot   不授权或新 pilot 失败
          │                │
          ▼                ▼
首次 GPU val_dev + 完整验收  继续 BLOCKED，
          │                 不进 formal
          ▼
FORMAL_READY → C1 → C0R
```

smoke 的工程门已经关闭；不会再进行第四次 smoke。唯一合理的下一次 GPU 前置任务，是获得明确授权后新建 372-step pilot，并让它在 step 372 触发一次冻结 `val_dev`。

### 15.2 Pilot

已有 pilot 已留下真实吞吐、损失、LR、checkpoint 和 provenance；但 P6 缺少真正的 GPU validation forward。推荐的 372-step pilot 应额外保留 val 结果、评估耗时、显存峰值、checkpoint/recovery 及完整 provenance。若新 pilot 暴露数值问题，必须回到 CPU/配置修复并新建 attempt，不能直接 formal。

### 15.3 正式 C1 与 C0R

```text
C1 跑满 2,976 + 主 checkpoint 可加载
                 │
                 ├── 指标好 ──┐
                 └── 指标差 ──┤
                              ▼
                     都必须运行 C0R
                              │
                              ▼
              validation + Q4 同协议比较
```

机械完成与科学成功是两件事：

- 机械完成：step、checkpoint、finite、provenance 全部正确；
- 科学成功：通过预注册 factual、composition、control 和 state gates。

即使 C1 指标差，只要机械完成，C0R 仍必须跑，这样失败也能被解释。

### 15.4 C1/C0R 后的四种典型结局

| 观察 | 解释 | 下一步 |
|---|---|---|
| C1 factual≈C0R，Q4 更好 | 递归接口有希望，且不伤事实性 | 进入 C2/C3，分离 composition loss 增量 |
| C1 factual 明显差 | 递归训练路径损害事实预测 | 诊断误差累积/跨度/优化；不能强推 Q4 主张 |
| C1 factual 好但 Q4 不过 | 会预测不等于可组合 | 检查路径漂移、坏对照、noncollapse；再设计 C2/C3 |
| C1/C0R 都异常 | 更可能是 Phase-II 合同、数据或训练问题 | 停止科学解释，先做工程审计 |

---

## 16. 后续科研路线：每个工作包回答一个问题

### WP1：关闭当前 GPU 工程门

目标：解决 P6 合同矛盾 → validation-capable pilot → `FORMAL_READY`。  
产物：验收 JSON、GPU `val_dev` 证据、运行 provenance、checkpoint 恢复证据、真实 ETA。  
停止条件：用户不授权新 pilot 或新 pilot 失败，即停止并报告。

### WP2：Arm-C1 与 Arm-C0R

目标：在同父权重、同数据、同预算条件下，隔离 recursive vs direct。  
预算：各 2,976 updates，seed 42，global batch 64。  
关键证据：机械完成、val_dev/val_locked、同协议 factual gate、Q2、Q4。  
不能主张：composition loss、simulator calibration、multi-seed 稳健性。

### WP3：统一并运行新 Q4

在正式评测前解决 bootstrap 统计口径冲突，并冻结唯一版本。随后检查：

- direct/composed factual；
- held-out partition gap；
- broken controls；
- weather switch；
- state std/rank/movement；
- Q2 retention；
- C1 vs C0R 的绝对与相对差。

### WP4：Arm-C2 与 Arm-C3

目标：把递归接口与 composition losses 分开归因。

- C2 增加 latent composition；
- C3 再增加 output composition；
- 每个 arm 应与适用对照共享 tuning budget、seed、数据和 updates；
- λ 候选在 tuning 前冻结，最终 λ 在看 test/OOD 前冻结。

### WP5：正式 simulator 基础设施

在训练 C4/C5/C0S 前必须具备：

- 明确 simulator engine/version，如 WOFOST/PCSE 与适用范围；
- initial-state/site 分组的 train/val/test，不能把同一初态的不同 forcing 拆到不同 split；
- 每行记录 initial_state_id、scenario/arm ID、24 维 forcing、物理单位、归一化、20×5-day 时间轴、target schema、适用地类和 adapter version；
- EO↔simulator 一一映射；
- train/validation/test scenario IDs；
- canonical JSON 序列化和整个文件 SHA-256 sidecar；
- smoke manifest 与 formal manifest 分开，synthetic 明确标为 non-evidence。

T3 只允许生成 synthetic 小样本验证 schema；T5 正式训练前才冻结正式情景库。当前环境没有这些真实工件，所以此 WP 是科学硬门。

### WP6：C0S、C4、C5 与响应校准

目标：区分“多了 simulator 监督”和“组合/校准机制有效”。

- C0S：direct、相同 paired 样本/labels/exposures/updates/domain mix；
- C4：C3 + paired response calibration；
- C5：C4 + noncollapse/full method；
- C6：去 noncollapse 的反向消融。

先通过真实 EO factual gate，再讨论 simulator 响应。若方向、幅度、时间或 held-out forcing 失败，应按预注册级别降级主张。

### WP7：完整重评 T6

选定唯一 Candidate C checkpoint 后，全部数字必须重跑，不能继承旧模型数值：

- Q1–Q4；
- IID、OOD-t、OOD-s、OOD-st；
- 五轴分层；
- 方法消融；
- 多 seed；
- 计算效率和显存；
- 失败案例。

### WP8：图表、论文叙事与 venue 决策

只有 Q4、校准和外推证据都成立，才适合完整的 ICLR/NeurIPS 叙事。若组合性成立但 simulator 证据不完整，应收缩主张；若机制解释强但方法增量有限，可转向 TGRS/ISPRS。TIP 还会要求更重的图像/光谱与数据工作，不应在主线证据未闭合前挤占资源。

---

## 17. T0–T8 总进度表

| 阶段 | 内容 | 当前状态 | 完成定义 |
|---|---|---|---|
| T0 / E0 | 11,904/14,880 对齐与 Q1–Q3 | **完成** | v3 ACCEPTED，原始结果、SHA、总账一致 |
| T1 / E1 | 强基线事实背景 | 部分历史可用，待按最终协议整理 | 同 protocol、同 split、完整 provenance |
| T2 | 旧模型深度画像/消融 | 非当前最高优先级 | 只按论文解释需要补充 |
| T3 | Candidate C 代码与合同贯通 | **代码/CPU 验收、smoke 与两臂机械运行已完成**；4 卡运行偏离已登记 | 不把运行完成误作严格 8 卡合同复现；原始工件与偏离完整保留 |
| T4 | 新 Q4 | **`val_locked` 已完成并封存**（2026-08-24） | C1 单臂 PASS、C0R FAIL；臂间 G_abs 的 R² 腿系规格错误，pooled 重算 19/19（A04 §19）；locked 额度已用尽，不得重跑或用其调参 |
| T5 | simulator 校准/外推 | **硬阻塞** | 正式情景库、mapping、manifest、C0S/C4/C5 |
| T6 | 全套多 split/多 seed 重评 | 未开始 | 唯一选定模型的完整重跑 |
| T7 | 图表与失败案例 | 可预写工具，不能填最终数值 | 只使用 T6 正式结果 |
| T8 | venue 与论文决策 | 未开始 | 依据可支持主张选择叙事与投稿方向 |

## 18. 资源安全、并发与运行纪律

### 18.1 GPU 的最高原则

本项目共享 GPU 环境，正式训练不是“看到一张空卡就先跑”。启动 8 卡任务前必须在目标节点确认：

- 8 张目标 H200 全部可见；
- 无外部 compute PID；
- 显存接近驱动基线、利用率低；
- 无未校正 ECC 异常；
- 磁盘空间足够；
- 连续 5 轮、每轮约 60 秒都满足；
- 启动前再做最终复查。

发现他人进程时，唯一动作是等待或退出自己的启动流程；绝不 kill、pkill、renice、reset、抢占或干预他人。后续正式运行若有外部任务进入，也只能安全停止自己的任务并记录状态，不能操作对方。

### 18.2 为什么必须使用新输出目录

每个 run 都应有唯一目录，至少保存：

- resolved config；
- 父权重和输入 SHA；
- 完整命令、环境、GPU UUID；
- PID/PGID/SID；
- train log、loss log、checkpoint、summary；
- 状态标记和验收报告。

目录存在或已有 checkpoint 时应 fail closed。失败、被中断或 partial 的输出都应保留并标注，不能删除后假装从未发生。

### 18.3 断线存活不等于持续监控

`setsid` / `nohup` 能防止 VS Code 或 SSH 断开直接杀掉训练，但它不自动说明训练健康。正式 run 需要独立、只读的 watchdog 记录：

- rank/PID 是否仍存活；
- log 是否持续推进；
- 最近 step、loss、NaN/Inf；
- GPU、磁盘、NCCL/OOM；
- 最近 checkpoint 是否完整、mtime 是否稳定。

当前 smoke 的退出码未被 detached launcher 收割，是已登记的非致命证据缺口；正式运行必须改为可记录真实 exit code 的监督方式。

### 18.4 并发文件修改

本仓库已有其他会话的 ObsWorld 与 TerraState 改动。后续任何会话应：

- 默认只修改用户授权的子目录；
- 写前重新查看 `git status` 和目标文件；
- 不使用 `reset --hard`、`checkout --`、`stash`、`clean`、宽泛批量格式化；
- 不把 checkpoint、cache、日志提交进 Git；
- 未明确授权时不 commit/push；
- 不让两个会话同时编辑同一文件。

---

## 19. 证据—主张矩阵：哪些话现在能说，哪些不能说

| 陈述 | 当前状态 | 依据 | 表述边界 |
|---|---|---|---|
| 11,904→14,880 的旧训练恢复可靠 | 已支持 | M9 31/31、模型张量一致性、E0 重评 | 是旧谱系 exact resume，不等同 Candidate C fork |
| 14,880 相对 11,904 的 Q1 基本对齐 | 已支持 | Val/OOD-t 的 `|ΔR²|<0.01` | 是描述性对齐，不是严格统计等价或 Q1 改善 |
| 旧模型的状态为输出提供信息 | 已支持 | Q2 `LOAD_BEARING`、paired CI | 不等于所有信息都只经状态，也非因果证明 |
| 旧模型对真实天气有响应保真 | 已支持 | Q3 actual 优于 donor/mean | 不等于真实反事实、因果校准或极端特异性 |
| old model 有 hot-dry 特异增强 | 不支持 | Q3 hot-dry gate 为 FAIL | 不得宣称 |
| Candidate C 能正常运行 | 部分支持 | CPU 119/119、smoke 通过 | 只能说明工程路径，不是方法有效 |
| recursive path 的分段稳定性更强 | **部分支持（qualified）** | 固定 4 卡 pair 的 `val_locked`：C1 四门 PASS，C0R composition/retention FAIL；最差分段退化 0.8%–1.2% vs 9.1%–14.7% | 不等于事实端点非劣、overall Q4 PASS、严格 8 卡复现或多 seed 结论 |
| composition losses 有效 | 尚无证据 | C2/C3 未运行 | 正式 C1/C0R 的 λ 全为 0 |
| 可组合预测状态 | **单 split 上成立，尚待多 seed / 多 split 加固** | C1 单臂四门 PASS；事实非劣由端点描述量、pooled-RMSE 腿 19/19 与 A04 §18 独立评测支撑（原 4/19 系 R² 腿规格错误，见 A04 §19） | 补足预先冻结的独立设计与多 seed 证据 |
| simulator 校准 | 被阻塞 | 缺 formal paired data/manifest | synthetic fixture 不构成证据 |
| 因果反事实预测 | 不支持 | 本项目没有真实干预标签 | 禁止使用该表述 |
| SOTA | 不支持 | 未完成统一强基线与完整协议重评 | 禁止使用该表述 |

这是论文写作和汇报时最重要的“刹车表”。研究可以有雄心，但每一句结论都必须落到已完成的证据层级上。

---

## 20. 常见问题

### Q：为什么不直接把 14,880 往后再训练？

因为旧训练的 scheduler 在 14,880 时已经结束，且 Candidate C 引入了新的训练路径/合同。把旧 optimizer 和 scheduler 硬接到新目标上，会模糊“旧训练恢复”和“新方法训练”的边界。正确做法是 weights-only Phase-II fork。

### Q：既然 11,904 与 14,880 几乎一样，为什么还要保留两个？

它们角色不同。11,904 是历史证据和 exact-resume 父节点；14,880 是预先固定的扩展端点和 Candidate C 新锚点。保留两者能防止篡改历史来源，也能量化 checkpoint 阶段敏感性。

### Q：smoke 成功后是不是说明模型成功？

不是。smoke 只说明真实 8 卡路径、数据、环境和 checkpoint 能正确运行。它不证明模型比对照好、更可组合或更可校准。

### Q：pilot 的 loss 降了，是否已经可以说方法有效？

不可以。短 pilot 的目标是发现发散、OOM、学习率和恢复问题。它既不在完整训练预算内，也不用于 test/OOD 或模型选择。

### Q：为什么 C1/C0R 不用 composition loss？

这是有意的第一步。先隔离递归接口本身，才知道之后 C2/C3 的 composition loss 是否带来真正增量。否则多个改变同时发生，任何提升都难以解释。

### Q：为什么不先跑 full Candidate C（C5）？

C5 需要真实 paired simulator 轨迹、EO↔simulator mapping、scenario manifest 和 C0S 公平对照。当前这些不存在。用随机轨迹或 Q3 donor 代替会制造看似完整、实际无效的结果。

### Q：为什么不能在 OOD 上选最好的 checkpoint？

因为 OOD/test 是用来检验泛化主张的。如果看完这些结果再选 checkpoint，就把检验集变成调参集，会高估泛化能力。选择规则必须先用 validation 冻结。

### Q：为什么同一 seed 还需要多 seed？

同一 seed 能让 C1/C0R 的对照更公平，但一次随机训练的结果可能偶然。多 seed 才能估计训练随机性；它是后续 T6 的必要证据，不是当前一对机械对照能替代的。

---

## 21. 推荐阅读顺序

如果你刚加入项目，建议按以下顺序：

1. 阅读本文第 0、1、2、4 节，先建立问题和接口直觉；
2. 阅读第 8、9 节，理解已有权重和 E0 事实；
3. 阅读第 5、6、11 节，理解为什么当前先跑 C1/C0R；
4. 阅读第 12、13 节，理解 CPU/smoke/pilot/formal 与训练基础；
5. 阅读第 15、16、19 节，理解后续分支和每类主张的证据门；
6. 需要追溯原始依据时，再打开下节的权威工件。

---

## 22. 权威来源、优先级与维护规则

### 22.1 来源优先级

当不同文档出现冲突时，按以下优先级判断：

1. 原始 checkpoint、结果 JSON、训练日志和由它们生成的验收报告；
2. 冻结 JSON/YAML 合同与其 SHA sidecar；
3. 实际模型、训练器、评测器代码；
4. A03（E0 结果总账）和 A04（Candidate C 实现/训练总账）；
5. A01/A02 研究规划；
6. 本 A05 解释手册。

换言之：A05 负责让人读懂项目，但不覆盖原始事实。运行状态尤其应以最新 `state.json`、run summary、verdict 和日志为准。

### 22.2 关键工件

| 用途 | 路径 |
|---|---|
| 科学主张、判据、禁止边界 | `terrastate/思路整理进展/A01_TerraState_AAAI后续研究与实验总纲.md` |
| 简明研究计划 | `terrastate/思路整理进展/A02_TerraState_后续研究计划.md` |
| 11,904/14,880 关键结果总账 | `terrastate/思路整理进展/A03_TerraState_关键实验结果与决策总账.md` |
| Candidate C 执行总账 | `terrastate/思路整理进展/A04_TerraState_CandidateC_实现训练与实验总账.md` |
| Candidate C 设计合同 | `terrastate/artifacts/protocols/candidate_c_v1/candidate_c_design_contract_v1.json` |
| 选择/验证合同 | `terrastate/artifacts/protocols/candidate_c_v1/candidate_c_selection_contract_v1.json` |
| 正式队列 | `terrastate/artifacts/protocols/candidate_c_v1/candidate_c_formal_queue_v1.json` |
| Candidate C 模型 | `terrastate/models/terrastate_candidate_c.py` |
| Candidate C 训练器 | `terrastate/train/train_terrastate_candidate_c.py` |
| Candidate C 启动器 | `terrastate/train/launch_candidate_c.py` |
| Q4 评测器 | `terrastate/eval/eval_terrastate_candidate_c_q4.py` |
| 当前 nightly 状态与工件 | `terrastate/ops/candidate_c_nightly/20260820T155316Z/` |

### 22.3 更新本手册的规则

每次更新 A05 时：

1. 先读取最新 `state.json`、verdict、summary 和原始 JSON；
2. 用“已完成 / 正在运行 / 已冻结未运行 / 阻塞”四类标签，不把计划写成结果；
3. 引用指标时标明 split、样本数、统计单位和 checkpoint 身份；
4. 发现合同、代码与文档不一致时，显式登记冲突，不静默选择有利版本；
5. 修改后生成 `.sha256` sidecar；
6. 原始数据、失败 attempt 和旧版本保留，不覆盖历史。

### 22.4 允许与禁止主张速查

允许：

- “E0 证明 14,880 与 11,904 的 Q1 基本对齐，并保持 Q2/Q3 的主要合同。”
- “Candidate C 已完成代码和 CPU 工程验收，GPU smoke/pilot 仅提供工程证据。”
- “当前 C1/C0R 用于隔离递归接口与同预算 direct 对照。”
- “C4/C5/C0S 被正式 simulator 数据与 scenario 合同阻塞。”

禁止：

- “我们已经证明可组合状态。”
- “模型已经完成 simulator 校准/因果反事实预测。”
- “smoke 或 pilot 已证明方法有效。”
- “14,880 在 Q1 上明显更好。”
- “hot-dry 特异增强已成立。”
- “旧 Q4 就是组合性成功。”

---

## 23. 最简结论

项目主线是：先把旧 TerraState 的可信预测状态证据固定下来，再把它从“固定 horizon 查询器”升级为“可递推、可分段、可换天气的状态模型”，随后用严格对照证明组合性，最后在真实 simulator 轨迹存在时检验响应校准。

我们已经完成旧权重谱系和 E0 Q1/Q2/Q3 的严谨封账，也完成了 Candidate C 固定 4 卡 C1/C0R pair
的一次性锁定 Q4。它给出的是一个有价值但受限的结果：C1 自身可通过组合/保持等门，且比 C0R
更稳定地承受分段递推；事实端点非劣由端点描述量、pooled-RMSE 腿 19/19 与 A04 §18 支撑（原 4/19 系 R² 腿规格错误，见 A04 §19）。仍不得声称预注册 per-cube R² 版 G_abs 通过。
`val_locked` 已封存，下一步不是重跑或改阈值，而是先冻结不使用 locked 结果的新诊断/设计包，
再决定是否值得开展 C2/C3；simulator 校准仍受正式数据、mapping 与 scenario manifest 缺失的硬阻塞。
