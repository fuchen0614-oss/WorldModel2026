# TerraState Method 3.2 AAAI 独立质量审计

> 日期：2026-07-28  
> 审计对象：`paper/main.tex` 中 `\subsection{TerraState Architecture}` 与
> `MANUSCRIPT_ZH_FULL.md` 中 `### 3.2 TerraState 架构`  
> 审计模式：只读；未修改正文、中文稿、Figure 2、代码或 PDF  
> 事实优先级：实际代码和冻结 checkpoint > 冻结方法事实 > 公式 > Figure 2 >
> 当前正文 > AAAI 写作锚点

## 1. 总体判定

**REVISE**

3.2 的模型结构与主要公式基本正确，不需要推倒重写，但尚未达到已冻结 3.1 的
质量标准。需要解决两个阻断项：

1. **正文技术错误：** 当前写道 \(c_h\) “shared across spatial tokens”，但代码
   中的地理编码 \(E_g(g)\) 是逐 patch 的，因此 \(c_h\) 也随空间 patch 变化。
   共享的是网络参数，不是条件向量本身。
2. **Figure 2 与代码不同构：** 当前图把 future meteorological forcing 放入
   Multimodal context，并以整体箭头连接 history encoder；同时使用乘号表达
   weather/state 融合。这与正式代码中的“未来天气只进入 \(T_\psi\)”“拼接后经
   MLP 融合”“残差状态更新”不一致。

其余问题主要是写作层级：

- 开场像 Figure 2 的图注，而不是独立架构小节；
- history 段混入 warm-start 和状态移除；
- transition 段提前进入 3.4 的天气替换语义；
- “Observable Forecast Closure”容易被理解为 closed-loop rollout 或
  composition；
- 末段从架构事实滑向了已验证结果措辞。

## 2. 各维度评分

| 维度 | 分数（1–5） | 依据 |
|---|---:|---|
| AAAI 架构小节成熟度 | 3 | 三模块结构完整，但开场依赖 Figure 2，段落边界仍混入训练和干预 |
| 模块目的清晰度 | 3 | transition 和 readout 目的较清楚；history 段对“为什么需要空间预测状态”解释不足 |
| 技术与代码一致性 | 3 | 主推理链正确，但 \(c_h\) “跨空间 token 共享”与逐 patch 地理条件冲突 |
| 公式与 Figure 2 一致性 | 2 | 公式基本符合代码；Figure 2 的 future-weather 边界、融合算子和残差路径不准确 |
| 世界模型机制辨识度 | 4 | 状态构建、外生驱动转移和状态读出均已出现，模型身份清楚 |
| 与 3.1/3.3/3.4 的边界 | 3 | 重复 3.1 总览，混入 3.3 warm-start 和 3.4 substitution/removal |
| 英文自然度 | 3 | 技术英语可读，但 “groups Equation into”“explicit entry”“observable closure”偏图注或审计表达 |
| 中文自然度 | 3 | 与英文强度一致，但“唯一且显式的预测入口”“可观测预测闭环”略生硬 |
| 主张安全性 | 4 | 没有 SOTA、因果、递归或 composition 强主张；“state must provide measurable contribution”仍应降为结构性表述 |

## 3. 逐段问题与严重度

| 段落 | 功能是否完成 | 具体问题 | 严重度 | 建议动作 |
|---|---|---|---|---|
| 3.2 开场 | 部分完成 | “Figure 2 groups Equation...”以图为主语，像图注；基本重复 3.1；teacher/target 提醒属于 3.3 | MAJOR | 改成推理架构的科学目的和三模块关系；只说本节描述 inference architecture |
| Historical Context 开头 | 基本完成 | 首句强调信息隔离，但没有说明为何需要保持空间组织的预测状态 | MINOR | 首句建立“从同一历史上下文同时获得基础预测和空间状态”的目的 |
| \(q_\theta\) 输出 | 完成 | 同一次 `q.encode` 产生 \(b_{1:H}\) 和历史 token，正文准确 | NONE | 保留 |
| \(P_\rho\) 与空间状态 | 部分完成 | 只写 “preserving spatial ordering”，没有说明 token 与空间 patch/raster 的对应关系 | MINOR | 用一句话说明每个 token 对应一个空间 patch，避免堆实现尺寸 |
| “share exactly the same historical evidence” | 基本准确 | 代码上成立，但 “exactly”略带审计语气 | MINOR | 改成 “are derived from the same historical context” |
| “allowing removal without recomputing context” | 结构上正确 | 已提前进入 3.4 的具体干预逻辑 | MINOR | 3.2 只写两条输出分支保持显式分离；精确移除语义放 3.4 |
| PVT v2/Contextformer | 事实正确 | 两句放在模块结尾尚可，但 warm-start 不是 inference architecture | MINOR | 保留一句 backbone 实现；warm-start 移至 3.3 或 Implementation |
| Transition 开场 | 基本完成 | “single, explicit entry”略像信息流审计，但动机正确 | MINOR | 改成未来天气如何条件化状态演化的正向表述 |
| \(d_h\) 定义 | 完成 | 共享 GRU 确实编码有序前缀 \(u_{t+1:t+h}\) | NONE | 保留 |
| \(c_h\) 解释 | 未完成 | “shared across spatial tokens”错误：天气和 horizon 被广播，但地理编码逐 patch 变化 | **BLOCKER** | 改为 patch-wise、horizon-specific condition；明确共享的是编码器和融合参数 |
| 残差转移 | 完成 | 一次 direct transition、共享参数、非递归 rollout 均与代码一致 | NONE | 保留并适当压缩 |
| 天气替换句 | 技术上正确 | “permits future weather to be replaced...”属于 3.4 接口语义 | MINOR | 3.2 只保留历史状态与未来 forcing 分离；具体替换移至 3.4 |
| Closure 标题 | 功能明确、命名不自然 | “closure”可能被理解为 closed-loop 或 composition | MAJOR | 建议改为 “State Readout and Additive Forecast” |
| token→patch→raster | 完成 | 与共享线性读出和 unpatchify 一致 | NONE | 保留 |
| \(b_h+\alpha r_h\) | 完成 | \(\alpha\equiv1\) 的位置合理，与训练、推理及 3.4 removal 一致 | NONE | 保留 |
| Closure 末句 | 部分完成 | “state must provide ... measurable”混合结构要求和结果结论 | MAJOR | 改成该结构“exposes a contribution whose effect can be measured and removed”；load-bearing 留给 Results |
| 中文镜像 | 基本同步 | 英文的层级问题被完整镜像；没有额外扩大主张 | MINOR | 与英文同步修订，不需要重新翻译整节 |
| Figure 2 | 未完成同构 | future weather 进入历史上下文；乘号不符合 concat+MLP；缺少清楚的 \(z_t\to T_\psi\) 残差更新 | **BLOCKER** | 正文修订后单独手工修图，不能让正文迁就错误图示 |

## 4. AAAI 写作锚点映射

### 4.1 SparseWorld，AAAI 2026

一手来源：[SparseWorld: A Flexible, Adaptive, and Efficient 4D Occupancy
World Model Powered by Sparse and Dynamic
Queries](https://ojs.aaai.org/index.php/AAAI/article/view/37347)。

- **段落功能顺序：** 先形式化既有预测路径，再用一个短段给出完整架构及组件
  列表，随后各模块分别展开。
- **可借鉴写作动作：**
  - overview 段独立于图注；
  - 先说每个模块解决的结构性问题，再进入内部结构；
  - 组件段末解释设计性质，而不是提前报告实验结论。
- **TerraState 对应内容：**
  - 3.1 已完成整体形式化；
  - 3.2 开场只需解释历史状态构建、天气转移、状态读出如何分工；
  - 三个模块分别采用“目的→机制→公式→结构性质”。
- **不可借用的技术主张：** SparseWorld 的稀疏 query、自回归预测、自动驾驶
  规划和 extended-range perception 都不适用于 TerraState。

### 4.2 Modeling Latent Non-Linear Dynamical System over Time Series，AAAI 2025

一手来源：[Modeling Latent Non-Linear Dynamical System over Time
Series](https://ojs.aaai.org/index.php/AAAI/article/view/33269)。

- **段落功能顺序：** 先区分 latent state 与 observable value，再分别定义状态
  转移和 observation projection，最后解释各算子的角色。
- **可借鉴写作动作：**
  - 清楚区分 \(z_{t+h}\) 与可观测预测贡献 \(r_h\)；
  - 公式之后解释算子作用，不逐行复述；
  - observation/readout 与 latent transition 分段描述。
- **TerraState 对应内容：**
  - \(T_\psi\) 负责推进预测状态；
  - \(O_\omega\) 把状态转成空间 raster contribution；
  - \(b_h+r_h\) 明确连接潜状态和可观测预测。
- **不可借用的技术主张：** 不能引入其稀疏动力学、多项式状态方程或
  latent-system identification 主张。

### 4.3 Learning Hybrid Dynamics Models with Simulator-Informed Latent States，AAAI 2024

一手来源：[Learning Hybrid Dynamics Models with Simulator-Informed Latent
States](https://ojs.aaai.org/index.php/AAAI/article/view/29075)。

- **段落功能顺序：** 先定义 latent dynamics，再定义 observation model，并明确
  additive output 中不同分支的角色。
- **可借鉴写作动作：**
  - 将加性输出写成模型机制，而不是防御性免责声明；
  - 解释每个加性分支承载什么信息；
  - 把 latent transition 与 observable reconstruction 严格分离。
- **TerraState 对应内容：**
  - \(b_h\) 是 context-only forecast；
  - \(r_h\) 是由 transitioned state 解码的空间预测贡献；
  - 显式相加提供可分离的状态路径。
- **不可借用的技术主张：** 不可引入 simulator-informed state、物理保证、
  observer 收敛或混合动力学解释。

## 5. 代码与方法事实核验

审计时 `WorldModel2026-planb-v2train` 工作树位于冻结 commit
`52578ca4b1c0b434b10707cf052a623f0c4e4a99`，检查未发现工作树改动。

| 核验项 | 实际事实 | 当前 3.2 | 代码或冻结依据与判定 |
|---|---|---|---|
| \(q_\theta\) 输入 | context-only 数据包含历史 EO、历史 mask、过去天气和前三个静态地理通道；future EO、future mask 和 future weather 在输入侧清除 | 准确 | `models/plan_b_b4.py:173–184`；`models/plan_b_b4_exclusive.py:95–112` |
| \(q_\theta\) 输出 | 一次 `q.encode` 同时得到 20-step context-only forecast 和 transformer token sequence；取最后历史时刻 token | 准确 | `models/plan_b_b4_exclusive.py:105–111`；`models/encoders/pvt_contextformer_q.py:174–177` |
| \(P_\rho\) 输入 | 最后历史时刻的 256 维空间 token | 准确 | `models/encoders/pvt_contextformer_q.py:31–40`；`models/plan_b_b4_exclusive.py:111` |
| 状态形状 | 每个 \(128\times128\) minicube 经 patch size 4 形成 \(32\times32=1024\) 个 token；代码展开为 \((1024B,256)\) | \(\mathbb R^{N\times d}\) 抽象上正确，但空间含义解释不足 | `models/encoders/state_projection.py:7–23`；canonical spec §2.3 |
| Weather encoder | 24 维 future weather 由一个共享 GRU 编码 | 准确 | `models/plan_b_b4.py:62–80` |
| Weather prefix | GRU 第 \(h\) 个输出编码 \(u_{t+1:t+h}\)；正式批量预测通过一次 GRU forward 取得所有 prefix 表示 | 准确 | `models/plan_b_b4.py:74–80,236–247` |
| Geography | 三通道静态地理先 patch-average，再由 MLP 产生逐 patch 64 维编码 | 当前未说明其逐 patch 性质 | `models/plan_b_b4.py:83–96` |
| Horizon | 整数 \(h\) 使用共享的 64 维 sinusoidal embedding | 准确 | `models/plan_b_b4.py:45–59` |
| 条件融合 \(c_h\) | weather 与 horizon 被广播到各 patch；geography 随 patch 变化；三者 concat 后经共享 MLP | “shared across spatial tokens”错误 | `models/plan_b_b4.py:206–215,236–247`：**BLOCKER** |
| Shared 的含义 | 所有 horizons 和 patches 复用同一 GRU、fusion MLP、transition MLP；不是所有 token 使用相同 \(c_h\) 数值 | 当前部分混淆 | `models/plan_b_b4.py:127–152` |
| Transition 调用 | 对每个 horizon，从相同 \(z_t\) 做一次 direct transition；批量实现只是向量化多个 direct queries | 准确 | `models/plan_b_b4.py:236–247` |
| Residual update | \(z_{t+h}=z_t+\mathrm{MLP}([\mathrm{LN}(z_t);c_h])\) | 准确 | `models/plan_b_b4.py:99–117` |
| Recursive rollout | 正式 forecast 不执行 \(z_t\to z_{t+1}\to\cdots\) | 准确 | `models/plan_b_b4.py:236–247` |
| \(O_\omega\) | 每个 state token 经共享线性层产生 \(4\times4\) patch，再 unpatchify 成 raster | 准确 | `models/plan_b_b4.py:152,246–253,273–276` |
| \(\alpha\) | non-learnable buffer，训练和推理固定为 1 | 准确 | `models/plan_b_b4_exclusive.py:49–55`；`models/terrastate_v2.py:47–53` |
| 最终加法 | `pred = prior + alpha * residual` | 准确 | `models/plan_b_b4_exclusive.py:115–124` |
| Warm-start | student 从 exclusive forecasting precursor 的完整 state dict 精确加载；不是只加载 \(q\) | 当前事实正确，但表述位置不合适 | `models/terrastate_v2.py:170–191`；`evidence_workspace/raw/release/selection_record.json:43–54` |
| KD teacher | 独立冻结 `PVTContextformerQ`，由 trainer 建立，只输出训练 tensor | 不参与推理 | `train/train_terrastate_v2.py:124–141` |
| Future-state target | 由训练起点冻结的 \(q/P\) 离线生成 cache；训练时只传入 tensor | 不参与推理 | `train/terrastate_future_state_cache.py:180–240` |
| 纯推理入口 | `teacher_pred is None` 时只调用 `forecast(data)`，不读取 teacher 或 target cache | 准确 | `models/terrastate_v2.py:123–127` |

### 5.1 关键事实结论

1. 当前 3.2 的 \(q\to P\to T\to O\) 主路径与代码一致。
2. future weather 的唯一正式输入路径是 \(T_\psi\)，不会进入 context-only
   history pass。
3. 正式预测是从相同 \(z_t\) 对每个 horizon 执行一次 direct transition，不是
   recursive rollout。
4. \(O_\omega\) 输出逐预测时距的空间 raster contribution，而非另一组 latent
   tokens。
5. 当前正文唯一明确的代码事实错误是 \(c_h\) “shared across spatial tokens”。
6. teacher 与 future-state target 均为 training-only，不参与推理。

## 6. 与 3.1、3.3、3.4 的边界

### 6.1 3.1 已讲过、3.2 不应重复

- TerraState 是 testable predictive-state world model；
- 完整 \(q_\theta\to P_\rho\to T_\psi\to O_\omega\) 总路径；
- \(b_h+r_h\) 的总体方法身份；
- future weather 只进入 transition 的总体信息边界；
- 状态贡献和天气响应可被分别检验的总体动机；
- 不声称完整物理状态或因果模拟器。

3.2 应当从“这三个架构模块如何实现上述总览”进入，而不是重新证明 TerraState
为何是世界模型。

### 6.2 3.2 必须讲清、不能推给 Figure 2

- \(q_\theta\) 同时输出 \(b_{1:H}\) 和历史空间 token；
- \(P_\rho\) 如何把最后历史时刻 token 转成空间预测状态；
- weather prefix、patch-wise geography 和 horizon 分别如何进入条件；
- 哪些模块的参数跨 horizon 共享；
- direct transition 与 recursive rollout 的区别；
- residual update 的数学形式；
- \(O_\omega\) 如何从 token 重建 patch/raster；
- \(b_h+\alpha r_h,\alpha=1\) 的加性输出关系。

### 6.3 应移入 3.3 的内容

- 完整模型 warm-start 的来源与加载身份；
- teacher 与 future-state target 的具体身份；
- teacher/target 只在训练出现的详细解释；
- checkpoint、冻结状态、future-state cache 和训练目标。

3.2 开场最多保留一句“This subsection describes the inference architecture.”
不需要列举 teacher 和 target。

### 6.4 应移入 3.4 的内容

- “removal without recomputing context”对应的精确干预语义；
- “permits future weather to be replaced”；
- 临时令 \(\alpha=0\)；
- 固定 readout/history 后替换天气；
- \(T\to I\) 的 supporting-diagnostic 身份及其分布外限制。

### 6.5 应移入 Section 4 的内容

- matched-donor 与 normalized-mean 的构造；
- paired effects、bootstrap 和置信区间；
- load-bearing/weather-responsive 的结果判定；
- Q1/Q2/Q3 编号和具体数据子集。

## 7. KEEP / REWRITE / MOVE / DELETE 清单

### 7.1 KEEP

- \(q_\theta\) 同时产生 \(b_{1:H}\) 与 \(e_t\)；
- \(P_\rho\) 保留 patch 空间组织并构造 \(z_t\)；
- spatial predictive state；
- weather prefix、geography、horizon 的条件组成；
- shared GRU、fusion 和 residual transition；
- 每个 horizon 从同一 \(z_t\) 执行一次 direct transition；
- non-recursive inference；
- token→patch→raster 的 state readout；
- \(b_h+\alpha r_h,\ \alpha\equiv1\)；
- context-only forecast；
- state-mediated contribution；
- queried horizon；
- PVT v2/Contextformer 仅作为一句实现说明。

### 7.2 REWRITE

| 当前词语或句式 | 推荐方向 | 原因 |
|---|---|---|
| `Figure ... groups Equation into...` | 以 inference architecture 的目的为主语，Figure 放句末 | 当前像图注，且依赖 Figure 才能理解 |
| `share exactly the same historical evidence` | `are derived from the same historical context` | 减少审计语气 |
| `single, explicit entry` | `future weather conditions only the transition` 或 `enters only through the transition` | 更自然、具体 |
| `c_h ... shared across spatial tokens` | patch-wise, horizon-specific condition；参数共享 | 当前技术错误 |
| `Shared Weather-Conditioned Direct Transition` | 标题可简化为 `Shared Weather-Conditioned Transition`，正文定义 direct | 当前标题过密 |
| `Observable Forecast Closure` | `State Readout and Additive Forecast` | 避免 closed-loop/composition 歧义 |
| `additive closure` | `additive forecast` 或 `additive readout path` | 更符合直观模型含义 |
| `state must provide ... measurable contribution` | `the architecture exposes a contribution whose effect can be measured and removed` | 区分方法结构与 Q2 结果 |

### 7.3 MOVE

- 完整 warm-start 身份：移到 3.3 或 Implementation；
- state removal 的精确语义：移到 3.4；
- weather substitution 的精确语义：移到 3.4；
- `trained input distribution`：只保留在 3.4 的 \(T\to I\) 限制中；
- teacher 和 future-observation target 的详细身份：移到 3.3；
- control 构造与统计判定：移到 Section 4。

### 7.4 DELETE

仅从 3.2 删除，而不是从整篇论文删除：

- 以 Figure 2 为主语的重复性模块枚举；
- `c_h is ... shared across spatial tokens`；
- 已由 3.1 完整说明的世界模型身份与总体信息边界；
- 把“measurable contribution”写成模型已经实现的经验事实；
- 3.2 开场对 teacher/target 的具体列举。

## 8. 最小修改计划

### Step 1：重写开场段

- 用一到两句说明 3.2 解释 inference architecture；
- 从“历史信息推断—天气驱动推进—空间预测读出”的功能关系进入；
- Figure 2 放在句末作为辅助，不让图承担定义；
- 不重复 3.1 的世界模型身份和完整总公式。

### Step 2：收敛 Historical Context 段

- 首句说明从同一历史上下文产生基础预测和空间预测状态的目的；
- 保留 \(q_\theta\) 与 \(P_\rho\)；
- 增加 token 与空间 patch 对应的简短解释；
- 删除精确 state-removal 语义；
- 将 warm-start 移出本段；
- PVT v2/Contextformer 只保留一句实现说明。

### Step 3：修正 Transition 段

- 保留 \(d_h\)、\(c_h\) 和 residual transition 公式；
- 将 \(c_h\) 改为逐 patch、逐 horizon 条件；
- 明确天气和 horizon 表示被广播，而 geography 逐 patch 变化；
- 明确共享的是 GRU、fusion 和 transition 参数；
- 保留 direct-per-h 与 non-recursive 说明；
- 将天气替换句移至 3.4。

### Step 4：收敛 Readout 段

- 标题改成 `State Readout and Additive Forecast`；
- 保留 token→patch→raster 和加法公式；
- 保留 \(\alpha\equiv1\)；
- 将末句改成结构性可测接口，不提前宣告 load-bearing；
- 不使用 closure、closed-loop 或 composition 暗示。

### Step 5：中英文同步回归

- 逐段同步，不机械翻译；
- 检查 “shared” 在中文中明确指参数共享；
- 不把 \(c_h\) 译成跨空间相同条件；
- 保持英文和中文的主张强度一致。

### Step 6：Figure 2 独立修正

Figure 2 不在 3.2 正文修改中处理，但冻结 3.2 前应满足：

1. future weather 移出 history encoder 输入边界；
2. 明确 \(z_t\to T_\psi\)；
3. 乘号改为 condition fusion + residual update；
4. state readout 输出 raster \(r_h\)；
5. 状态贡献与 \(b_h\) 的加法关系清楚；
6. 删除 `D3` 等内部工程标签。

## 9. 是否达到 3.1 的质量标准

### 9.1 当前判断

- **是否达到 3.1 的质量标准：否。**
- **是否可以直接冻结：否。**
- **是否需要大规模重写：否。**

### 9.2 冻结前的可验证条件

1. 修正 \(c_h\) 的空间性质，明确共享的是参数而非条件值；
2. 让开场成为独立架构说明，不再像 Figure 2 caption；
3. 将 warm-start、state removal 和 weather substitution 分别归位到
   3.3/3.4；
4. 将 Closure 标题与末句改为不歧义、不过度结果化的架构表达；
5. Figure 2 修正 future-weather 边界、条件融合和残差转移，使其与代码和公式
   同构；
6. 英文与中文逐段同步，且不扩大主张。

完成以上条件后，3.2 可以从 **REVISE** 收敛为 **PASS**，无需改变模型、公式、
实验协议或论文主线。
