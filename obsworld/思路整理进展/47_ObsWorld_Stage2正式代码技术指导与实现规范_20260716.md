# 47. ObsWorld Stage2 正式代码技术指导与实现规范

> 日期：2026-07-16
> 文档性质：后续代码开发的直接依据；A–D、E-1（可追溯训练）和 E-2（可追溯导出/评分）已实施并通过测试，仍不是论文实验结果
> 适用项目：`/root/nas/users/luzheng/workspace/ssh/czj/WorldModel2026`
> 目标投稿：AAAI-27
> 当前训练与评测数据：服务器已有的 EarthNet2021x raw NetCDF 文件；正式主线固定使用其 `train/iid/ood/extreme/seasonal` 划分，GreenEarthNet 目录不作为当前 Stage2 的前置条件或自动合并来源
> 当前主线：**从受成像条件影响的遥感观测中估计地表状态，在外生驱动、地理先验和时间跨度约束下推演未来状态，再把未来状态解码为可核验的未来卫星观测。**

> **数据协议更新（2026-07-16）：**本项目当前只使用已审计通过的 raw EarthNet2021x 数据根。`train` 用于拟合，`iid/ood` 是主评测，`extreme/seasonal` 是压力测试；同一张主表只使用这一套协议和对应官方评估器。项目保留 GreenEarthNet 目录审计工具，仅供日后独立扩展，绝不自动混入本轮训练/评测。

---

## 0. 这份文档解决什么问题

前面的 01–46 号文档记录了 ObsWorld 从最初构想到当前方案的演化，其中包含很多有价值的直觉，也存在不同阶段遗留下来的口径冲突。最明显的冲突包括：

- Stage2 有时被写成直接预测多个未来时刻，有时又被写成真正逐步递推的世界模型；
- `DGH` 有时表示累计统计量，有时表示逐时间段的驱动路径；
- Stage3 有时指观测解码器，有时又指统一评估阶段；
- 当前代码已经能运行 Direct-DGH（直接预测 DGH 对照），但它还不能证明共享动力学的递推和可组合性；
- 当前 9 维 D 输入能做早期验证，却不能作为与 Contextformer 公平比较的最终 24 维气象协议；
- 现有官方评估、数据清单、三类 mask（有效标记）隔离已经有基础；Commit A 负责把 Stage2-v2 新数据契约贯通这些代码。

因此，本文件不是再提出一套完全不同的新方法，而是完成以下四件事：

1. 用小白也能理解的方式说明 Stage2 为什么要这样写；
2. 审核当前代码究竟做到哪里，哪些部分可直接复用，哪些必须重写；
3. 冻结正式 Stage2 的数据、模型、训练、评估和测试接口；
4. 给出按文件、按里程碑、按依赖关系推进的开发清单。

### 0.1 文档优先级

发生冲突时，按以下顺序理解：

1. **论文中心叙事和实验决策**：以 45 为准；
2. **并行开发和运行节奏**：以 46 为准；
3. **Stage2 具体代码实现**：以本 47 为准；
4. 39 是独立审查和风险来源；
5. 40–44 以及更早文件保留为历史依据，不再自动覆盖本文件。

本文件会对 45/46 中尚未落实到代码级别的地方进一步收紧。例如，官方代码核对后，24 维天气特征的固定顺序和缺失值处理方式在本文件中给出精确定义。

### 0.2 本文件没有声称什么

本文件没有声称以下工作已经完成：

- 新 24-D 驱动路径已经被完整模型消费并训练；
- rollout（递推推演）已经训练；
- partition consistency（时间分割一致性）已经有效；
- Stage1.5 一定优于 Stage1；
- ObsWorld 已经超过 Contextformer；
- 本地物理目录之外存在额外、未经清单证明的测试轨道。

这些都必须由后续代码、审计和实验来证明。

### 0.3 实施状态更新（2026-07-16，Commit A）

本轮已完成 **Stage2-v2 data contract（Stage2-v2 数据契约）** 的代码边界，具体包括：

- 新增 `data/earthnet_conditioning.py`，唯一固定 8 个 E-OBS（欧洲逐日气象）变量顺序、24-D 聚合顺序、部分缺失处理、`D_core12`（12 维紧凑消融）和 `cop_dem`（Copernicus 数字高程模型）标准化；
- `data/datasets/earthnet2021.py` 新增 `earthnet2021x_path_v2` 路径，输出 `D_path/C_path/delta_t_path/G`，保留旧 `legacy_direct9`（历史 9-D 直接预测）而不覆盖；
- `data/stage2_contract.py` 新增 v2 输入边界和检查：目标/官方评分字段不能进入模型，且 `h == cumsum(delta_t_path[:, 10:])`；
- 新增 train manifest（训练数据清单）驱动的 `scripts/build_earthnet_conditioning_stats.py` 和 v2 `preflight`（训练前检查）分支；
- 新增合成 NetCDF、统计量、preflight 和 legacy regression（旧路径回归）测试。

它**没有**完成 Direct24、共享 rollout（递推）、partition（一致性）模型或任何正式结果。因此，Commit A 可以安全地和正在运行的 Stage1.5 并行；只有将来启动正式 v2 训练前，才必须用完整 train manifest 生成 `conditioning_stats_v2_train.json` 并通过 preflight。

### 0.4 实施状态更新（2026-07-16，Commit B–D、E-1 与 E-2）

在 Commit A 之后，代码已经按本文件的最小依赖顺序实现了以下内容：

- **Commit B / Direct24：**同一套 24-D 五日外生驱动、状态初始化器和观测解码器下的直接多时距预测对照；它保留旧 Direct-DGH，不把旧 9-D 对照误写成新主线的公平比较。
- **Commit C / Rollout24：**共享五日状态转移的 20 步开放循环推演、由短到长的课程，以及每个 batch 都保留 100 天监督的 horizon（预测时距）采样。
- **Commit D / Partition24：**同一共享转移下的 `10 天` 与 `5 天 + 5 天` 两条路径、终点观测监督和状态/像素一致性损失。它是主方法的“可组合演化”证据，而非额外的未来真值输入。
- **Commit E-1 / 可追溯训练：**每个 Stage2 checkpoint（检查点）保存解析后的配置、训练状态、随机状态、数据位置和运行来源记录；保存操作使用临时文件、落盘同步和原子替换，避免中断留下半个权重文件。
- **Commit E-2 / 可追溯导出与评分：**评估和预测导出先核对 checkpoint 内保存的数据/模型/损失契约；每次正式预测生成带文件 SHA-256（文件内容摘要）的 `prediction_manifest.json`，评分入口拒绝缺失、被篡改或与清单混杂的预测文件，并把预测、目标目录、checkpoint 和 Git 信息写入 `score_provenance.json`。
- **E-1 验证监控修正：**v2 的 context（历史观测）和 target（目标观测）本来就允许不同空间分辨率；persistence（最后有效历史观测）基线会先重采样到 target 网格。若 persistence 误差为零，relative skill（相对技能分数）写为 `NaN`（数学上未定义），不把它伪装成极大的负分。

其中 E-1 已完成的可复现约束如下：

1. `run_provenance.json`（运行来源记录）同时写入 checkpoint 和 log 目录，绑定配置摘要、训练/验证 manifest（文件清单）摘要、conditioning stats（条件标准化统计）摘要、Stage1.5 初始化权重、续训父 checkpoint、Git commit、Python/PyTorch/CUDA 环境和 world size（进程数）。
2. 新 checkpoint 还保存 `data_position`（数据位置）：下一轮的 epoch（轮次）、下一批 batch（批次）编号、loader 长度、已处理 micro-step（微步）、world size、batch size（批大小）与梯度累积次数。
3. 恢复训练时，程序验证上述数据形状；batch size、world size、loader 长度或梯度累积不同会立即报错，不能悄悄把“近似续训”说成精确恢复。旧 checkpoint 没有该字段时会明确警告并走非精确兼容路径。
4. 非 DDP（单进程）训练使用由 `seed + epoch` 唯一决定的 shuffled sampler（打乱采样器）；每个 epoch 的 DataLoader worker seed（加载线程随机种子）也固定。因此重启不会因重新打乱而回放已训练 batch。
5. `--stop-after-steps N` 可在第 `N` 个优化器步安全停下：它不修改原来的 `max_steps` 或学习率课程，适合测试“停下—恢复”是否与连续训练一致。

验证证据（不是正式精度结果）：CPU 上构造 4 个字段完整的 NetCDF minicube，连续训练 4 步，与“训练 2 步 → 保存 → 新进程恢复 → 再训练 2 步”逐项比较；最终 model state、optimizer state、scheduler state（学习率调度器状态）和 data position 完全一致。相同试验还以 2 个 CPU DDP rank（分布式进程）执行，两个 rank 的 RNG state（随机状态）也完全一致，且没有 checkpoint barrier（检查点同步屏障）死锁；开启验证后 `checkpoint_best.pt` 也可正常保存。

E-2 的验证同样不是精度结果：同一批临时 NetCDF minicube 已实际跑通“checkpoint 契约核验 → 原子 NPZ 导出 → 文件清单/哈希核验 → `earthnet==0.3.9` 的 EarthNetScore（ENS）评分 → `score_provenance.json`”。如果把 Direct checkpoint 伪装成 rollout 配置，程序会在读取数据前拒绝；如果预测目录多出旧 `.npz` 或某个文件被改写，评分也会拒绝。全套单元测试当前为 **106 passed**（另有 11 个第三方二进制/Transformer 警告）。这证明了证据链可运行，**不等于**真实 EarthNet 主实验已经完成；模型选择仍必须只在冻结的 `val_dev` 上做，不能由工具替代研究者的试验纪律。

### 0.7 实施状态更新（2026-07-16，Commit F：再观测校正契约）

新增 `models/dynamics/observation_correction.py`，但暂不接入正式 Stage2 trainer。它把后续世界模型主张中最容易出错的状态机先固定为可测试的接口：

- 每一步先由 transition（状态转移）产生 `prior state（更新前预测状态）`，再决定是否消费新观测；
- `q_obs=0` 或 `reveal=0` 时，使用结构化 `where` 保证 posterior（更新后状态）与 prior **逐元素完全相等**；
- `0<q_obs<1` 时只按 token 的可见支持更新，并按相同支持连续重置 staleness（陈旧度）；
- 未 reveal 的未来观测特征和 mask 即使被替换，也不会改变状态、最终状态或陈旧度轨迹。

当前只证明了这个 CPU/synthetic（合成）契约，**没有**声称 correction 已在 EarthNet 上训练、优于 VanillaFilter/PredRNN-online，或者已经形成正式主实验结果。下一步仍需把该模块和共享 `ControlledTransition`、EarthNet observation encoder/decoder 接到专门的 online trainer，再按 R020–R023 的 gate（闸门）跑 `val_dev`；在此之前，Direct24/Rollout24/Partition24 的真实数据 preflight 和 32-cube sanity 仍是优先事项。

---

## 1. 小白先读：Stage2 到底要做什么，为什么这样做

### 1.1 把整个模型想成“看地表—推演地表—重新成像”

一张卫星图像不是地表本身。它同时包含：

- 地表真实状态，例如植被、水分、裸土和作物生长；
- 卫星成像条件，例如传感器类型、太阳高度、云和观测缺失；
- 时间与天气造成的真实变化。

ObsWorld 的目标不是只记住“过去图像长什么样，然后猜未来图像”，而是把过程拆成三步：

```text
过去卫星观测
    │
    ▼
状态初始化器 I：估计当前较稳定的地表状态 s0
    │
    │ 未来天气 D、地理先验 G、时间长度 H/Δt、日历 C
    ▼
共享状态转移 T：把 s0 推演成 s1、s2、……、s20
    │
    ▼
观测解码器 Dec：把每个未来状态变成可评价的 RGBN/NDVI 观测
```

其中：

- `I` 是 initializer（状态初始化器）；
- `T` 是 transition（状态转移函数）；
- `Dec` 是 decoder（观测解码器）；
- `D` 是外生驱动，例如天气；
- `G` 是地理先验，本阶段先固定为 Copernicus DEM 高程；
- `H` 是时间跨度；在递推里具体写成每一步的 `Δt`；
- `C` 是日历位置，例如一年中的季节相位；
- `s0...s20` 是模型内部的地表状态，不直接等于卫星像素。

### 1.2 为什么“直接预测”还不够

当前代码中的 Direct-DGH（直接预测 DGH）大致是：

```text
同一个 s0 + 第 5 天条件  -> 第 5 天预测
同一个 s0 + 第 10 天条件 -> 第 10 天预测
……
同一个 s0 + 第 100 天条件 -> 第 100 天预测
```

它能回答“给定历史和条件，最终预测准不准”，所以它非常重要，必须保留。但它没有把第 5 天预测出的状态传给第 10 天，也没有反复使用同一个状态转移函数。因此，它更接近一个多时距条件预测器，还不足以单独支撑“模型在内部模拟世界逐步演化”的中心叙事。

正式 rollout（递推推演）应当是：

```text
s1 = T(s0, 第 1 个五日驱动段)
s2 = T(s1, 第 2 个五日驱动段)
……
s20 = T(s19, 第 20 个五日驱动段)
```

这意味着：

- 20 步使用的是**同一套** `T` 参数，不允许每个预测时刻各有一套网络；
- 后一步必须接收前一步的预测状态；
- 训练时不能偷偷把真实未来图像编码成状态再塞回去；
- 100 天误差会真实累积，这既是难点，也是世界模型证据的一部分。

### 1.3 为什么还需要“时间分割一致性”

如果模型真正在学习可组合的时间演化，那么同一段 10 天演化应当满足：

```text
一次走 10 天  ≈  先走 5 天，再走 5 天
```

写成公式是：

```text
T(s, D[0:2], Δt=10)
    ≈
T(T(s, D[0:1], Δt=5), D[1:2], Δt=5)
```

这不是要求自然界严格线性，而是要求同一个模型面对同一条驱动轨迹时，不应仅仅因为我们把时间切成一段还是两段，就给出完全矛盾的未来状态。这项约束直接服务于“共享、可组合的状态动力学”叙事。

### 1.4 为什么 Stage2 里必须已经有一个解码器

只有内部状态而不把它解码成未来观测，就无法使用 EarthNet 的真实未来卫星数据监督模型，也无法运行官方 NDVI 评估。因此：

- **EarthNet 主实验所需的最小 RGBN 解码器是 Stage2 的组成部分，必须和状态动力学一起存在；**
- 后续真正独立的 Stage3，只负责多产品、多传感器或显式未来成像条件渲染等增强，不是当前 Stage2 开跑的前置条件。

这消除了旧文档中的循环依赖：不需要先完成一个庞大的 Stage3 才能训练 Stage2，但也不能训练一个完全没有可观测输出的 Stage2。

### 1.5 一句话判断它是不是世界模型

只有同时具备以下证据时，论文中的“遥感世界模型”才站得住：

1. 能从历史遥感观测形成预测性状态；
2. 能在未来真实观测不参与输入的情况下开放循环推演；
3. 同一状态转移函数能被重复调用；
4. 未来轨迹会随 D/G/H 条件合理变化，而不是完全忽略驱动；
5. 不同时间分割下的演化具有可组合性；
6. 最终状态能还原成真实卫星观测并接受公开指标检验。

如果只有第 6 条，它只是预测器；如果 1–6 条形成闭环，才是本项目要实现的 ObsWorld。

---

## 2. 常用英文词的中文说明

| 英文 | 本文中文 | 在本项目里的含义 |
|---|---|---|
| checkpoint | 检查点/权重快照 | 训练到某一步保存的模型、优化器和随机状态 |
| Direct | 直接预测 | 每个未来时距都从同一个 `s0` 出发，不把前一步预测传给后一步 |
| rollout | 递推推演 | 前一步预测状态作为后一步输入，连续推演 20 个五日步 |
| open-loop | 开放循环 | 预测期间不使用任何真实未来卫星观测来纠正状态 |
| exogenous driver | 外生驱动 | 模型外部给定的天气等驱动变量，即 D |
| partition consistency | 时间分割一致性 | 同一时间段一次演化与分段演化应相互接近 |
| manifest | 数据清单 | 冻结本次实验究竟使用哪些文件的可复现 JSON |
| mask | 有效标记 | 告诉程序哪些像素、天气值或评估位置可信 |
| probe | 探针评估 | 冻结表征后用简单模型检查其中是否包含某类信息 |
| smoke test | 冒烟测试 | 用很小数据和很少步数检查代码能否完整跑通 |
| overfit test | 小样本过拟合测试 | 故意让模型记住少量样本，以检查梯度和损失是否真的有效 |
| fallback | 后备方案 | 主方案条件不满足时的降级方案，不等于正式首选 |
| oracle future weather | 真值未来天气/上界天气 | 数据集提供的真实未来 E-OBS；不包含业务天气预报误差 |
| ablation | 消融实验 | 去掉或替换某个模块，判断提升到底来自哪里 |
| leakage | 信息泄漏 | 模型在预测时意外看到未来真值或评估专用字段 |
| provenance | 运行来源记录 | 代码版本、数据清单、配置、权重和随机种子的完整记录 |
| matched baseline | 配对公平对照 | 除了被研究因素之外，输入、参数量和训练预算尽量相同 |

---

## 3. 最终阶段划分：消除 Stage2/Stage3 混乱

### 3.1 推荐阶段名称

| 阶段 | 做什么 | 是否必须完成后才能开始下一层 | 论文角色 |
|---|---|---:|---|
| Stage1 | 学习多模态遥感视觉表示 | 已有 | 表征基础 |
| Stage1.5 | 引入纯成像条件 `φ` 和状态桥接 | 主权重正在完成 | 状态初始化来源 |
| Stage2-0 | 正式 EarthNet 数据契约、24-D D 路径、C/G/H、清单与统计量 | 是 | 可复现输入基础 |
| Stage2-D | 24-D matched Direct（配对直接预测） | 是 | 排除“只是输入变强”的解释 |
| Stage2-R | 共享五日转移的开放循环 rollout | 是 | 证明真正递推演化 |
| Stage2-P | variable-step（可变时间段）转移 + 时间分割一致性 | AAAI 主方法必须 | 证明可组合动力学 |
| Stage3-E | 多产品/多传感器/显式未来 `φ` 的观测形成扩展 | 否 | 截稿后或加分项 |
| Stage4 | 下游任务或大模型骨干组合 | 否 | 有余力再做的外部效用证据 |

### 3.2 最小依赖关系

```text
Stage1.5 最终 checkpoint ───────────┐
                                    │
Stage2-0 数据契约与统计 ──> Stage2-D ──> Stage2-R ──> Stage2-P ──> 正式评估
                                    │                         │
现有官方评估与 mask 隔离 ──────────┘                         └─> 可选 Stage3-E
```

### 3.3 哪些工作现在就能并行

即使全量数据审计仍在运行，也可以立即完成：

- 新数据契约和合成数据单元测试；
- 24-D 聚合函数及与官方实现的数值对齐测试；
- Direct/rollout/partition 模型骨架；
- checkpoint（检查点）兼容与恢复测试；
- 小模型 CPU 前向、反向测试；
- 配置文件和运行来源记录代码。

正式长训练必须等到：

- Stage1.5 最终权重路径冻结；
- 正式 train manifest（训练数据清单）冻结；
- 24-D 训练统计量生成并验证；
- 本地 split 与官方 track 的映射得到确认；
- 所有 Stage2-v2 测试通过。

### 0.4 实施状态更新（2026-07-16，Commit B：Direct24）

本项目现已实现、但尚未声称得到实验结果的代码边界如下：

- 新增 `IntervalDriverEncoder`（区间驱动编码器）：统一消费任意长度的 `D/C/delta_t` 路径，支持 `L=1/2/4/...`；全缺失天气时仍保留日历和时长；
- 新增 `ControlledTransition`（受控状态转移）：把上述编码器、`HorizonEncoder` 和原有 `StateDynamicsModule` 组合为唯一的可变步长转移接口；
- 新增 `ObsWorldV2Core`（共享核心）与 `ObsWorldDirectPathModel`（Direct24 包装器）：每个未来端点从同一个历史状态 `s0` 出发，只看从第一个未来五日段开始的天气前缀；不接收任何未来像素、目标 mask 或官方评分字段；
- `ContextStateAggregator`（上下文状态聚合器）现可处理连续 clear coverage（清晰像素占比），但旧 Direct-DGH 的默认行为保持兼容；正式 v2 才启用“完全不可观测 token 置零”；
- `train/train_stage2_earthnet.py` 已能按 `stage2_protocol=earthnet2021x_path_v2` 选择新工厂，在训练时只解码分层抽样的端点、在验证时解码完整 20 步，并在模型边界之外再对齐监督 target；
- 新增 `stage2_earthnet_v2_direct24.yaml`（正式配对 Direct 配置）和 `stage2_earthnet_v2_smoke.yaml`（非正式小样本冒烟配置）；
- preflight（训练前检查）、预测和普通 split 评估入口已经能接受 v2 的 conditioning stats（条件统计量）与 split-specific manifest（按划分清单）。

这一步**仍然没有**实现 rollout（递推）、partition consistency（时间分割一致性）、正式统计量、正式 Stage1.5 权重接入或任何主实验数值。它的作用是先建立一个与后续世界模型共享输入、状态初始化、转移和解码器的公平 Direct24 对照，而不是把 Direct24 包装成世界模型结论。

### 0.5 实施状态更新（2026-07-16，Commit C：开放循环 rollout）

Commit C 在完全相同的 shared core（共享核心）上新增了 `ObsWorldRolloutModel`：

- 每一步只向 `ControlledTransition` 传递当前五日 `D/C/delta_t` token；下一步状态严格来自上一步**预测**状态；没有 teacher forcing（教师强制）或未来 target 回灌；
- 返回当前课程长度的完整 `z_rollout`，同时只解码被抽样监督的端点，因而可以在不牺牲开放循环语义的情况下控制显存；
- 新增 `train/stage2_curriculum.py`，把“2 → 4 → 8 → 12 → 20 步”的课程写成配置数据。它是 optimizer step（优化器步数）的纯函数，checkpoint（检查点）会显式记录当前长度；续训时若配置的模式或当前长度与检查点冲突会停止，而不是悄悄改变实验；
- 新增 `stage2_earthnet_v2_rollout24.yaml`。它通过 `_base_` 继承 Direct24 配置，只覆盖预测方式、开放循环开关、课程和输出目录，以保证两者的输入、decoder（解码器）、优化器和数据协议确实配对；
- 新增 rollout 因果性、课程、配置继承和 factory（模型工厂）测试。

这仍是 **Stage2-R**，不是完整主方法：尚未加入 variable-step 的直接/组合分支和 partition consistency 损失，故不能把当前 rollout 单独写成“可组合动力学已被证明”。

### 0.6 实施状态更新（2026-07-16，Commit D：首版 partition consistency）

Commit D 将第一版 **Stage2-P** 落为可训练代码，而不是只保留公式：

- 新增 `ObsWorldPartitionModel`，它完全继承同一个五日 rollout（递推）和 `ControlledTransition`（受控转移），不增加另一套动力学网络；
- 每个有效 minibatch（小批次）随机选择一个合法锚点 `j`，从当前预测状态 `s_j` 同时计算 `T(s_j,D[j:j+2])`（一次十日）与 `T(T(s_j,D[j]),D[j+1])`（五日加五日）。两条分支读取的是逐 token 完全相同的 `D/C/delta_t`（驱动/日历/时长）路径；
- `detach_partition_start=true`（分割起点停止梯度）只切断辅助分支回到更早 rollout 的梯度；主 RGBN/NDVI rollout loss 仍端到端训练状态初始化器。因此它是控制显存和耦合的工程选择，不是 teacher forcing（教师强制）；
- `PartitionConsistencyLoss` 采用无参数 `LayerNorm`（层归一化）和 symmetric stop-gradient（对称停止梯度）比较状态，同时比较 RGBN、NDVI，并让 direct 与 composed 两个端点都对同一个真实未来时刻负责。target（未来真值）只由 trainer（训练器）在模型 forward（前向）之后取出，不能进入转移器；
- `stage2_earthnet_v2_partition24.yaml` 继承 rollout 配置，只增加 partition loss（时间分割损失）与明确的 warm-up（预热）：前 5k optimizer steps（优化器步）为 0，之后 10k 步线性升至固定权重。课程、partition 开关、损失权重均写入 checkpoint（检查点），续训时若被改变会拒绝继续；
- 当前第一版固定为 **10 日 vs 5+5 日**。20 日 vs 10+10、20 日 vs 5+5+5+5 与不规则时间段仍是下一轮增强，不能在论文中写成已完成。

因此现在的代码已经能训练 matched Direct、普通 rollout 和首版 partition 主方法；正式数值仍必须等待数据协议冻结、预检和 smoke run（冒烟训练）通过。

---

## 4. 当前代码审计：现在做到什么程度

### 4.1 已经可以复用的部分

| 文件/模块 | 当前能力 | 结论 |
|---|---|---|
| `models/encoders/multimodal_vit_encoder_film.py` | Stage1/1.5 ViT-S 编码器与 FiLM 路径 | 复用，不重写主骨干 |
| `models/encoders/pure_imaging_condition_encoder.py` | 只编码 S2 太阳高度或 S1 几何，不含季节、位置等语义捷径 | 冻结复用 |
| `models/encoders/state_projection.py` | 把编码器 token 投影到 256 维状态空间 | 复用 |
| `models/adapters/earthnet_band_adapter.py` | EarthNet RGBN 4 通道映射到 Stage1.5 的 12 通道位置 | 复用并保留初始化 |
| `models/dynamics/context_state_aggregator.py` | 用 10 帧状态形成 `s0`，带最后有效状态残差和趋势支路 | 复用，做小幅 mask 接口增强 |
| `models/adapters/geo_tokenizer.py` | 把 DEM 转成与状态网格对齐的 G token | 复用，改为固定 `cop_dem` 协议 |
| `models/dynamics/state_dynamics_module.py` | 单次残差状态更新，支持 transformer/GRU/MLP | 作为共享转移的内部核心复用 |
| `models/decoders/earthnet_observation_decoder.py` | 状态 token 解码为 4 通道 RGBN | 复用结构，正式输出改为原生 128×128 |
| `models/losses/earthnet_forecasting.py` | RGBN、NDVI 及可选 latent/delta/smooth 损失 | 保留基本损失，新增 partition 损失 |
| `data/earthnet_manifest.py` | 确定性、可迁移的数据清单及摘要校验 | 复用，但先解决官方 track 映射 |
| `eval/earthnet_standard_metrics.py` | EarthNetScore（ENS）分量与聚合 | 复用，并以官方工具校验 |
| `eval/predict_stage2_earthnet.py` | 导出预测与运行 provenance（来源记录） | 接入新模型工厂 |
| `eval/eval_stage2_earthnet.py` | 按冻结 manifest 评分并输出 JSON/CSV | 扩充运行来源记录 |
| `data/stage2_contract.py` | 模型输入、训练监督、评估专用 mask 隔离 | 思路正确，必须升级为 v2 形状 |

### 4.2 历史 L0 原型与当前正式 v2 实现的边界

`models/dynamics/obsworld_stage2.py` 仍保留为 **legacy Direct-DGH**（旧 9 维直接预测）基线；它不能 rollout，也不能作为当前世界模型主实验的实现依据。下面这些“旧路径限制”仍对 legacy 模型成立：旧累计 D、四字段 NetCDF 读取、自动选择 DEM、`D[B,20,9]` 与单点 Direct 监督。

但它们已经不再描述当前的正式 v2 路径。当前 `earthnet2021x_path_v2` 已固定 8 个 E-OBS×3 聚合的 24-D 五日路径、`cop_dem`、`D_path/C_path/delta_t_path/G` 契约，且已经具备 Direct24、20 步共享 rollout、10 天 vs 5+5 天 partition consistency、课程、精确续训和导出/评分来源检查。新评估入口会先比较 checkpoint 内保存的 resolved config（解析后的配置）与当前运行配置；不匹配时默认拒绝，所以不会把 rollout/partition checkpoint 当作 Direct 模型加载。

因此，现在可准确称为：

> “Stage2-v2 的 Direct24、开放循环 rollout 与首版 partition 世界模型代码已完成并通过合成/小样本链路验证；真实数据 preflight、小样本过拟合、基线校准和主实验数值尚未完成。”

### 4.3 当前数据证据

已经同步到仓库的快速审计报告表明：

- `train`：23,816 个文件；
- `iid`：4,205 个文件；
- `ood`：4,202 个文件；
- 每个要求抽查的 split 已抽查 64 个文件；
- 8 个 E-OBS 字段 `fg/hu/pp/qq/rr/tg/tn/tx` 均存在；
- S2 波段、训练 mask、官方评估 mask、土地覆盖和 `cop_dem` 均存在；
- 抽查状态为 PASS（通过）。

这足以允许 24-D 代码开发，但不能替代全量数值完整性扫描。

### 4.4 旧 9-D 统计量怎么处理

现有 `artifacts/stage2_earthnet2021x/dgh_stats_train.json` 对应旧 9 维累计特征，并基于当前 10% tile holdout 后的 21,434 个训练文件生成。它的正确用途是：

- 复现旧 Direct-DGH；
- 做旧协议回归测试；
- 检查 Stage2 基础训练链路；
- 作为紧急 smoke test（冒烟测试）。

它**不能**直接用于新的 24-D 逐五日路径，不能通过改文件名冒充新统计量。

---

## 5. 正式 Stage2-v2 数据契约

### 5.1 固定符号和尺寸

| 符号 | 固定值 | 含义 |
|---|---:|---|
| `B` | 可变 | batch size（批大小） |
| `Tc` | 10 | 历史 S2 观测帧数 |
| `Tf` | 20 | 未来预测帧数 |
| `Td` | 30 | 整段五日天气 token 数 |
| `KD` | 24 | 正式 D 特征维度 |
| `KC` | 2 | 日历正弦/余弦维度 |
| `Cobs` | 4 | RGBN：蓝、绿、红、B8A 近红外 |
| `Hctx/Wctx` | 256/256 | 为兼容 Stage1.5 编码器而使用的上下文输入尺寸 |
| `Htgt/Wtgt` | 128/128 | EarthNet 原生训练目标和正式预测尺寸 |
| `N` | 256 | 16×16 状态 token 数 |
| `Dz` | 256 | 状态 token 维度 |

### 5.2 正式 batch 字段

```python
Stage2BatchV2 = {
    # 模型可见的历史观测
    "x_context":       FloatTensor[B, 10, 4, 256, 256],
    "context_mask":    FloatTensor[B, 10, 256, 256],

    # 完整 150 天的逐五日条件路径
    "D_path":          FloatTensor[B, 30, 24],
    "D_mask":          FloatTensor[B, 30, 24],
    "C_path":          FloatTensor[B, 30, 2],
    "delta_t_path":    FloatTensor[B, 30],

    # 静态地理先验
    "G":               FloatTensor[B, 1, 128, 128],
    "G_mask":          FloatTensor[B, 1, 128, 128],

    # Direct 查询和报告使用的累计时距
    "h":               FloatTensor[B, 20],

    # 仅训练监督可见，不能进入正式预测模型输入
    "x_target":        FloatTensor[B, 20, 4, 128, 128],
    "target_mask":     FloatTensor[B, 20, 128, 128],

    # 字符串、路径、日期、manifest 摘要等
    "meta":            list[dict],
}
```

其中：

```python
D_hist = D_path[:, 0:10]
D_fut  = D_path[:, 10:30]
C_hist = C_path[:, 0:10]
C_fut  = C_path[:, 10:30]
dt_fut = delta_t_path[:, 10:30]
```

### 5.3 为什么上下文用 256、目标用 128

Stage1.5 ViT-S 使用 256×256 输入和 16×16 patch，因此会产生 16×16 个状态 token。EarthNet 的原生目标是 128×128。没有必要把真实目标先放大到 256，再让解码器预测 256，最后又缩回 128。

推荐实现是：

- 历史 RGBN 仍上采样到 256，保证兼容已有 Stage1.5 权重；
- 状态仍为 16×16 token；
- 解码器使用 `img_size=128, patch_size=8`，同样接收 16×16 token，直接输出原生 128×128；
- DEM 使用原生 128，并由 `GeoTokenizer(img_size=128, patch_size=8)` 形成 16×16 G token；
- 正式导出时不再进行额外空间缩放。

这样不会增加信息，却能减少解码和损失计算开销，并避免“论文看起来像使用了 256 分辨率”的误解。

### 5.4 三类 mask 必须继续隔离

| mask | 用途 | 能否进入模型 | 能否进入训练 loss | 能否用于官方评分 |
|---|---|---:|---:|---:|
| `context_mask` | 历史像素是否可观测 | 是 | 间接 | 否 |
| `target_mask` | 未来像素训练监督是否有效 | 否 | 是 | 否 |
| `official_eval_mask/eligibility` | 官方 clear-pixel 和筛选规则 | 否 | 否 | 是 |

硬约束：

1. `model_input_view()` 默认绝不能返回 `x_target/target_mask/official_eval_*`；
2. 正式主方法的 `compute_latent_targets=false`；
3. 即使 DataLoader 为评分方便读取了完整 NetCDF，模型 forward（前向计算）也只能收到模型输入视图；
4. 修改目标像素或官方评估 mask 时，只要历史和条件不变，正式模型预测必须逐元素不变；
5. 以上要求必须有自动测试，不能只靠开发者自觉。

### 5.5 `context_phi` 怎么处理

EarthNet2021x 当前可验证字段中没有与 Stage1.5 一致的真实太阳高度/观测几何。正式 v2 默认策略是：

- modality（模态）固定为 S2；
- `time_valid=0`；
- `sun_elevation=NaN`；
- 使用 Stage1.5 已学习的“缺失成像元数据”参考嵌入；
- 不从日期、经纬度或天气反推太阳高度，不伪造 `φ`；
- 日期季节只进入独立 `C_path`，不能偷偷塞入纯成像条件编码器。

如果后续在 NetCDF 或可靠外部元数据中找到真实太阳高度，必须先完成字段来源审计，再通过配置开启；不能让同名配置在不同机器上暗中使用不同 `φ`。

---

## 6. D、G、H、C 的精确定义

### 6.1 D-main：正式 24-D 五日驱动路径

正式变量顺序固定为：

```python
EOBS_VARIABLES = ["fg", "hu", "pp", "qq", "rr", "tg", "tn", "tx"]
EOBS_AGGREGATIONS = ["mean", "min", "max"]
```

其大致物理含义是：

| 字段 | 含义 |
|---|---|
| `fg` | 风速 |
| `hu` | 相对湿度 |
| `pp` | 海平面气压 |
| `qq` | 辐射 |
| `rr` | 降水 |
| `tg` | 平均气温 |
| `tn` | 最低气温 |
| `tx` | 最高气温 |

#### 6.1.1 24 维固定排列

必须与公开数据代码一致，采用“聚合方式优先”的顺序：

```text
[mean_fg, mean_hu, mean_pp, mean_qq, mean_rr, mean_tg, mean_tn, mean_tx,
 min_fg,  min_hu,  min_pp,  min_qq,  min_rr,  min_tg,  min_tn,  min_tx,
 max_fg,  max_hu,  max_pp,  max_qq,  max_rr,  max_tg,  max_tn,  max_tx]
```

禁止改成：

```text
[mean_fg, min_fg, max_fg, mean_hu, min_hu, max_hu, ...]
```

两者都看似 24 维，但权重和统计量完全不兼容。代码中必须用常量生成 feature names（特征名），不能手写两份顺序。

#### 6.1.2 标准化与聚合顺序

官方 EarthNet 模型代码先对每天的 8 个 E-OBS 值做逐变量标准化，再按连续 5 天做 mean/min/max。正式实现遵循同一数值顺序：

```python
eobs_z[d, v] = (eobs_raw[d, v] - train_daily_mean[v]) / train_daily_std[v]
D_path[k] = concat(
    nanmean(eobs_z[5*k : 5*k+5], axis=0),
    nanmin (eobs_z[5*k : 5*k+5], axis=0),
    nanmax (eobs_z[5*k : 5*k+5], axis=0),
)
```

注意：

- `mean/min/max` 对部分缺失天采用 skip-NaN（忽略缺失值）口径；
- 某变量在整个五日窗口都缺失时，对应三个统计量填 0，三个 `D_mask` 都为 0；
- 只要该窗口该变量至少有一天有效，对应三个统计量可计算，三个 `D_mask` 都为 1；
- 额外记录 `valid_day_count [30,8]` 供审计，但默认不作为模型输入；
- 不再对 24 个聚合量做第二次任意标准化，否则无法直接核对官方处理；
- 训练统计量只从被冻结的训练 manifest 计算，不能读取验证或测试 split。

这是对旧“累计窗口只要缺一天就整段无效”规则的修正。旧规则只保留给 legacy 9-D（历史 9 维）路径。

#### 6.1.3 统计量文件 v2

新增统计量文件不得继续叫模糊的 `dgh_stats_train.json`，推荐：

```text
artifacts/stage2_earthnet2021x/conditioning_stats_v2_train.json
```

最低字段如下：

```json
{
  "schema_version": 2,
  "dataset": "earthnet2021x",
  "fit_split": "train",
  "manifest_sha256": "...",
  "num_files": 23816,
  "daily_variable_order": ["fg", "hu", "pp", "qq", "rr", "tg", "tn", "tx"],
  "aggregation_order": ["mean", "min", "max"],
  "feature_names": ["mean_fg", "...", "max_tx"],
  "daily_mean": {"fg": 0.0},
  "daily_std": {"fg": 1.0},
  "daily_valid_count": {"fg": 0},
  "window_any_valid_fraction": {"fg": 0.0},
  "window_all_five_valid_fraction": {"fg": 0.0},
  "g_variable": "cop_dem",
  "g_mean": 0.0,
  "g_std": 1.0,
  "created_by_git_commit": "..."
}
```

上面数字只是结构示例，实际值必须由脚本计算，不能复制示例。

### 6.2 五日窗口与 S2 帧的时间对齐

EarthNet2021x 每个普通 minicube（小立方体样本）有 150 个逐日位置。S2 帧取日索引：

```text
4, 9, 14, ..., 149
```

D token 的固定定义是：

```text
D_path[0]  = 日索引 0..4   的天气，结束于 S2 frame 0
D_path[1]  = 日索引 5..9   的天气，结束于 S2 frame 1
...
D_path[9]  = 日索引 45..49 的天气，结束于最后一帧上下文
D_path[10] = 日索引 50..54 的天气，推动 s0 到第一个未来状态
...
D_path[29] = 日索引 145..149 的天气，推动到第 100 天目标
```

最危险的实现错误是：把第一步未来演化错误地从 `D_path[0]` 或 `D_path[9]` 开始。必须有单调合成天气测试证明：

```python
D_fut[:, 0] == D_path[:, 10]
```

### 6.3 D-core 与 legacy 9-D 的定位

必须保留两种非主输入，但不能混为一谈：

#### A. `D_core12`：正式路径的紧凑消融

从 24-D 中直接选取 `rr/tg/hu/qq` 四变量的 mean/min/max，共 12 维。它使用同一 30-token 时间路径、同一统计量、同一缺失处理和同一编码器结构，只减少变量数。

用途：判断全部 8 个变量是否真的必要。

#### B. `legacy_cumulative9`：历史 Direct-DGH

保留当前的：

- 目标日 DOY 正弦/余弦；
- 累计降水和均值；
- 均温；
- VPD 均值/最大值；
- 辐射累计/均值。

用途：保护既有工作、回归测试和展示思路演化。

禁止用 `legacy_cumulative9` 的 Direct 与 24-D rollout 直接比较后声称“提升来自递推架构”。正式 Direct/rollout/partition 三者必须全部使用相同 24-D 路径。

### 6.4 C：日历条件必须与天气分离

`C_path[k]` 固定为该五日窗口中点日期的年周期编码：

```python
mid_date = start_date + timedelta(days=5*k + 2)
angle = 2*pi*day_of_year(mid_date)/365.25
C_path[k] = [sin(angle), cos(angle)]
```

为什么分开：

- no-D（去天气）实验仍然必须知道季节和预测时距；
- 如果把 DOY 混在 D 里，去掉 D 时同时去掉季节，实验无法说明模型到底依赖天气还是日历；
- shuffled-D（天气轨迹置换）时，目标地点的 C 保持不变，只替换物理天气路径。

### 6.5 H/Δt：Direct 和 rollout 的不同用法

```text
h = [5, 10, 15, ..., 100] 天
delta_t_path = [5, 5, ..., 5] 天，共 30 个
```

- Direct 使用目标累计时距 `h_j`，并读取从未来第 0 段到第 j 段的完整 D/C 前缀；
- rollout 每一步只使用本地 `Δt=5` 和对应单个 D/C token；
- variable-step 转移可以一次接收 2 个 token，并令总 `Δt=10`；
- 禁止把 `h` 同时塞进 D 特征，再独立编码一次，避免时间信息重复和含义混乱。

### 6.6 G：固定 Copernicus DEM

正式主协议只使用：

```text
G = cop_dem
```

规则：

- 不再按 `nasa_dem -> alos_dem -> cop_dem` 选择第一个可用字段；
- `cop_dem` 缺失时 formal（正式）模式直接报错；
- 只在 legacy（历史兼容）模式允许旧回退逻辑；
- 用训练 manifest 上计算的 `g_mean/g_std` 标准化；
- 无效像素标准化后填 0，并由 `G_mask` 标记；
- 原生 128×128 输入 `GeoTokenizer(img_size=128, patch_size=8)`；
- `no-G` 消融把 G 值和 mask 都清零；
- 整地点 G 置换实验按完整 raster（栅格）交换，不能逐像素打乱。

---

## 7. 模型结构的正式实现

### 7.1 总公式

第一版正式主模型采用：

```text
s0 = I(x_context, context_mask; Stage1.5 encoder)

s_{j+1} = Tθ(
    s_j,
    E_D(D_fut[j], D_mask[j], C_fut[j], Δt_j),
    E_G(G, G_mask),
    Δt_j
)

x_hat_{j+1} = Dec(s_{j+1})
```

时间分割分支允许：

```text
s_{j+2}^{direct} = Tθ(s_j, E_D(D_fut[j:j+2]), G, 10)
s_{j+2}^{compose} = Tθ(Tθ(s_j, E_D(D_fut[j:j+1]), G, 5),
                       E_D(D_fut[j+1:j+2]), G, 5)
```

### 7.2 状态初始化器 `I`：第一版不要同时大改

正式第一版继续复用：

```text
EarthNet 4-band adapter
  -> Stage1.5 ViT-S + missing-φ embedding
  -> SpatialStateProjector
  -> ContextStateAggregator
  -> s0 [B,256,256]
```

为什么不立刻让 D_hist/C_hist/G 全部进入初始化器：

- 当前最核心的未知量是递推动力学是否有效；
- 同时改初始化器和转移器会导致结果无法归因；
- 历史卫星序列本身已经包含大量状态信息；
- `D_hist/C_hist/G -> I` 可以在主链路稳定后作为单独增强，而不是 formal-v2 的阻塞项。

因此，batch 仍返回完整 `D_hist/C_hist`，但第一版 `I_obs` 不消费它们。代码接口要留扩展点，不要在论文里谎称已经使用。

### 7.3 上下文 mask 的小幅必要增强

现有代码把像素 mask 池化后，只用 `clear_fraction > 0.05` 得到布尔 token 标记。正式 v2 推荐：

1. 计算 `context_token_coverage [B,10,256]`，取值 0–1；
2. `coverage == 0` 的 token 必须完全屏蔽；
3. attention score（注意力分数）加入 `log(coverage + eps)`，让较清晰帧自然获得更高权重；
4. first/last valid state 使用可配置阈值，默认 `min_token_clear_fraction=0.25`；
5. 若某个位置 10 帧都无有效观测，初始化状态为零并输出 `state_valid_mask=0`，训练 loss 不得因此产生 NaN；
6. 这只是观测有效性处理，不把“稀疏局部观测”重新抬成论文中心贡献。

### 7.4 `IntervalDriverEncoder`：统一编码任意长度驱动段

新增：

```text
models/dynamics/interval_driver_encoder.py
```

推荐接口：

```python
class IntervalDriverEncoder(nn.Module):
    def forward(
        self,
        D_seg,       # [B,L,24]
        D_mask_seg,  # [B,L,24]
        C_seg,       # [B,L,2]
        dt_seg,      # [B,L]
    ) -> dict:
        return {
            "tokens": ...,   # [B,L,d_driver]
            "summary": ...,  # [B,d_driver]
            "segment_valid": ...,
        }
```

内部最低要求：

```text
[D * D_mask, D_mask] -> value/missingness MLP
C                     -> calendar MLP
log1p(Δt)              -> duration MLP
三者相加/拼接          -> 2 层轻量 Transformer
masked attention pool  -> segment summary
```

硬约束：

- `L=1`、`L=2`、`L=4` 等都能运行；
- 同一个 encoder 供 Direct、rollout 和 partition 共用；
- 全缺失 D 时仍然保留 C 和 Δt，不输出 NaN；
- `use_D=false` 时只清除 D 数值与 D mask，不能清除 C/Δt；
- 不允许给第 1、2、……、20 步各建一个独立 MLP；
- 输出顺序对 D 特征常量做 runtime assertion（运行时断言）。

### 7.5 `ControlledTransition`：共享的可变步长状态转移

新增：

```text
models/dynamics/controlled_transition.py
```

推荐接口：

```python
class ControlledTransition(nn.Module):
    def forward(
        self,
        state,       # [B,N,Dz]
        D_seg, D_mask_seg, C_seg, dt_seg,
        geo_tokens,  # [B,N,Dg]
    ) -> Tensor:     # [B,N,Dz]
        ...
```

第一版不要重新发明一个超大动力学网络。推荐把新 `IntervalDriverEncoder`、现有 `HorizonEncoder` 和现有 `StateDynamicsModule` 包装起来：

```text
segment_summary = IntervalDriverEncoder(...)
delta_embed = HorizonEncoder(sum(dt_seg))
state_next = StateDynamicsModule(
    state,
    driver=segment_summary,
    geo=geo_tokens,
    time_delta=delta_embed,
)
```

要求：

- 输出采用 residual update（残差更新），即 `state_next = state + Δstate`；
- 20 次递推调用同一个 Python module 和同一组 parameter id（参数身份）；
- 支持 `L=1` 的 5 天步，也支持 `L=2` 的 10 天直接步；
- 不读取目标图像或目标 mask；
- 关闭 D/G/H 的消融要在统一接口内完成，不能换一个网络；
- 可选 LayerScale（小尺度残差系数）以稳定早期长 rollout；
- 第一版状态维度和现有 `StateDynamicsModule` 保持 256，不无理由扩大参数量。

### 7.6 Formal Direct：真正公平的直接预测对照

新增：

```text
models/dynamics/obsworld_direct_path.py
```

第 j 个目标的计算：

```python
z_j = transition(
    s0,
    D_fut[:, :j+1],
    D_mask_fut[:, :j+1],
    C_fut[:, :j+1],
    dt_fut[:, :j+1],
    geo_tokens,
)
```

它只调用一次转移，所以仍是 Direct；但它看到的完整驱动路径与 rollout 一致。它与 rollout 共享：

- 状态初始化器；
- 24-D 输入和 mask；
- IntervalDriverEncoder 类；
- ControlledTransition 类；
- G/C/H 编码；
- RGBN 解码器；
- 损失、训练步数、随机种子和验证协议。

当前 `obsworld_stage2.py` 的旧 9-D Direct 不删除，显式重命名/别名为：

```text
legacy_direct_9d
```

正式配对对照使用：

```text
direct_path_24d
```

### 7.7 Rollout：真正的 20 步开放循环推演

新增：

```text
models/dynamics/obsworld_rollout.py
```

核心伪代码：

```python
state = s0
states = []
for j in range(max_rollout_steps):
    state = transition(
        state,
        D_fut[:, j:j+1],
        D_mask_fut[:, j:j+1],
        C_fut[:, j:j+1],
        dt_fut[:, j:j+1],
        geo_tokens,
    )
    states.append(state)

pred = decoder(stack(selected states))
```

硬约束：

- `state` 下一步必须等于上一步预测状态；
- 不允许从 `x_target` 编码真实未来 latent（潜状态）回灌；
- 主方法不做 teacher forcing（教师强制）；
- `detach_between_steps=false`，使梯度能穿过时间传回；
- 如果显存不足，优先使用 activation checkpointing（激活重计算）、少解码几个监督时刻或减小 batch，不要偷偷切断梯度；
- 推理时固定 20 步，不能因为训练课程早期只走 4 步就输出 4 步；
- 返回 `states [B,20,N,Dz]`、`pred`、每步状态增量范数和可选诊断信息。

### 7.8 时间分割一致性模块

新增：

```text
models/dynamics/partition_consistency.py
```

第一版只做最稳妥的 10 天对 5+5 天：

```python
z_direct = T(z_start, segment[j:j+2], total_dt=10)
z_mid = T(z_start, segment[j:j+1], total_dt=5)
z_comp = T(z_mid, segment[j+1:j+2], total_dt=5)
```

`j` 从当前课程允许的合法位置随机采样。推荐默认：

- `detach_partition_start=true`：partition 分支不反向改变较早 rollout，降低显存与训练耦合；
- 主 rollout loss 仍可端到端训练状态初始化器；
- 状态比较先做无可学习参数的 LayerNorm；
- 使用 symmetric stop-gradient（对称停止梯度）：两个方向都提供梯度，但各自目标支路停止；
- `z_direct` 和 `z_comp` 都解码，并接受同一个真实日 10 终点监督；
- 额外比较两条路径的 RGBN 和 NDVI；
- 不能只最小化 latent 距离，否则常数状态可能投机取巧。

后续稳定后才扩展：

- 20 天 vs 10+10；
- 20 天 vs 5+15；
- 不规则 `Δt`；
- 多种随机 partition。

这些是增强项，不阻塞第一版 AAAI 主证据。

### 7.9 最小观测解码器属于 Stage2

正式配置：

```yaml
decoder:
  type: EarthNetObservationDecoder
  in_dim: 256
  out_channels: 4
  img_size: 128
  patch_size: 8
  output_activation: sigmoid
```

第一版固定 Sentinel-2 RGBN 产品，不注入未来 `φ`，因为当前 EarthNet2021x 主实验的目标产品一致且缺少可靠成像几何。论文应写：

> 当前 EarthNet 实验验证固定 Sentinel-2 产品空间中的未来观测形成；多传感器和显式未来成像条件渲染是 Stage3-E 扩展，不在当前结果中冒充已完成。

---

## 8. 训练目标和训练逻辑

### 8.1 主预测损失

保留两个真正必要的监督：

```text
L_obs  = clear target_mask 上 RGBN Huber loss
L_ndvi = clear target_mask 上 NDVI L1/Huber loss
```

默认：

```yaml
loss:
  obs: 1.0
  ndvi: 0.5
  latent_target: 0.0
  delta: 0.0
  smooth: 0.0
```

为什么先关闭后三项：

- future latent target（未来潜状态目标）需要编码真实未来图像，容易让逻辑和泄漏边界变复杂；
- delta/smooth（增量/平滑）可能压制真实快速变化；
- 当前最重要的是先验证观测预测和可组合转移，而不是堆很多损失。

### 8.2 partition 损失

推荐起始形式：

```text
L_part_state = MSE(LN(z_direct), stopgrad(LN(z_comp))) / 2
             + MSE(stopgrad(LN(z_direct)), LN(z_comp)) / 2

L_part_obs   = masked Huber(Dec(z_direct), Dec(z_comp))
L_part_ndvi  = masked L1(NDVI(Dec(z_direct)), NDVI(Dec(z_comp)))

L_endpoint_direct = L_obs(Dec(z_direct), target_end)
                  + 0.5 * L_ndvi(Dec(z_direct), target_end)
```

总损失初始权重建议：

```yaml
partition:
  state: 0.10
  observation: 0.10
  ndvi: 0.05
  direct_endpoint: 0.50
```

这些是 pilot（小规模试验）起点，不是不可修改的神圣数字。只有以下检查通过才允许增大：

- 每项损失数量级有日志；
- 主预测 loss 没有因 partition 激增；
- 状态方差没有塌成接近 0；
- 10 天 direct/composed gap（差距）确实下降；
- 100 天性能没有明显恶化。

### 8.3 rollout 课程学习

直接从随机初始化的新转移器做 20 步反向传播风险较大。推荐默认课程：

| optimizer step | 最大 rollout 长度 | 可监督时距 |
|---:|---:|---|
| 0–1,999 | 2 | 5/10 天 |
| 2,000–5,999 | 4 | 到 20 天 |
| 6,000–11,999 | 8 | 到 40 天 |
| 12,000–19,999 | 12 | 到 60 天 |
| 20,000 以后 | 20 | 到 100 天 |

实现为配置列表，不要把数字散落在训练循环里：

```yaml
rollout_curriculum:
  - {start_step: 0,     length: 2}
  - {start_step: 2000,  length: 4}
  - {start_step: 6000,  length: 8}
  - {start_step: 12000, length: 12}
  - {start_step: 20000, length: 20}
```

课程长度和当前阶段必须写入 checkpoint。恢复训练时，以 checkpoint 的 optimizer step 推导，而不是重新从 2 步开始。

### 8.4 每个 batch 监督哪些时距

即使每次都递推到当前课程上限，也不必解码所有时刻。达到 20 步课程后，每个样本推荐固定监督 6 个分层时距：

- 短期 1 个：5–20 天；
- 中短期 1 个：25–40 天；
- 中期 1 个：45–60 天；
- 中长期 1 个：65–80 天；
- 长期 1 个：85–95 天；
- 始终包含 100 天。

这样既控制解码显存，又不会让训练只偏向容易的短期。采样索引必须由可恢复随机状态控制。

### 8.5 冻结与解冻

推荐主配置：

| 模块 | 0–5k | 5k 以后 |
|---|---:|---:|
| Stage1.5 ViT 前 10 blocks | 冻结 | 冻结 |
| Stage1.5 ViT 后 2 blocks | 冻结 | 小学习率解冻 |
| Pure `φ` encoder | 始终冻结 | 始终冻结 |
| State projector | 冻结或极小学习率 | 小学习率解冻 |
| EarthNet band adapter | 训练 | 训练 |
| Context aggregator | 训练 | 训练 |
| Driver/Calendar/Geo encoder | 训练 | 训练 |
| Controlled transition | 训练 | 训练 |
| RGBN decoder | 训练 | 训练 |

必须注意：

- `φ` encoder 在 EarthNet 只接收缺失元数据参考，不值得解冻；
- 先让新转移和解码器适应，再轻微调整骨干；
- backbone learning rate（骨干学习率）建议是新模块的 0.1 倍；
- Direct、rollout 和 partition 使用相同冻结策略；
- 如果 Stage1.5 35k 权重只用于 smoke，要在运行名中明确；正式主表优先使用最终冻结的 state-bridge checkpoint。

### 8.6 Direct、rollout、partition 的训练配对

正式最小模型组：

| 配置名 | 状态初始化 | 预测方式 | partition | 论文用途 |
|---|---|---|---:|---|
| `legacy_direct_9d` | Stage1.5 | 旧累计 Direct | 否 | 历史保护，不做公平主结论 |
| `direct_path_24d` | Stage1.5 | 24-D 路径 Direct | 否 | 正式 matched baseline |
| `rollout_t5_24d` | Stage1.5 | 共享 5 日 rollout | 否 | 证明递推本身 |
| `obsworld_partition_24d` | Stage1.5 | variable-step rollout | 是 | 完整主方法 |

状态初始化的 2×2 证据：

| 初始化权重 | 无 partition rollout | 有 partition rollout |
|---|---|---|
| Stage1 | A | B |
| Stage1.5 | C | D |

它分别回答：

- C 对 A：Stage1.5 状态初始化是否帮助长期预测；
- B 对 A：partition 对普通 Stage1 状态是否有效；
- D 对 C：partition 在 Stage1.5 状态上是否仍有效；
- D 是否最好：两部分是否形成互补。

如果时间不足，优先运行 A/C/D，再补 B；但论文中不能把缺失格子写成已验证。

### 8.7 未来天气的声明边界

主实验使用数据集给出的真实未来 E-OBS，因此它是：

> 在给定真实未来外生驱动路径条件下的遥感状态推演上界。

它不是完整业务预报系统。论文禁止写成：

- 模型自己预测了未来天气；
- 已经包含天气预报误差；
- 可以无条件投入业务季节预报。

后续可把真实天气换成数值天气预报，但不属于当前 Stage2 必做代码。

---

## 9. 数据干预与逻辑约束

### 9.1 no-D 必须保留什么

`no_D` 只做：

```python
D_path = 0
D_mask = 0
```

必须保留：

- `C_path`；
- `delta_t_path`；
- `h`；
- `G`；
- 相同模型结构和参数预算。

否则 no-D 同时变成“无天气、无季节、无时间”，不能说明 D 是否有用。

### 9.2 shuffled-D 如何保证不是乱做

推荐新增：

```text
scripts/build_driver_intervention_map.py
```

为每个目标样本寻找一个 donor（捐赠天气轨迹样本）：

1. 来自同一评估 split；
2. donor 不能等于自身；
3. 起始 DOY 位于同一个 30 天 bin（分箱）；
4. 优先匹配中心纬度 5 度区间；
5. donor 不同 tile；
6. 一次替换完整 `D_fut + D_mask_fut`，保持内部 20 步顺序；
7. 目标样本自己的 C/G/h 和历史图像保持不变；
8. 映射写入 JSON 并冻结摘要，三种模型共用同一映射。

如果匹配不足，可以按记录的顺序放宽纬度到 10 度，但必须在报告中列出放宽比例，不能静默随机替换。

### 9.3 D 干预的理想结果和失败解释

| 结果 | 支持什么 | 不能支持什么 |
|---|---|---|
| true-D 优于 no-D | 模型使用了天气信息 | 不能直接声称因果机制正确 |
| true-D 优于 plausible-shuffled-D | 模型对样本匹配的未来天气轨迹敏感 | 不能声称已能做任意反事实 |
| 三者几乎一样 | D 被忽略或历史/日历已足够 | 不能继续把天气控制作为强贡献 |
| shuffled-D 反而更好 | 数据对齐、尺度或过拟合可能有问题 | 需要先查代码，不应包装成正结果 |

### 9.4 G 干预

最小做：

- full G；
- no-G；
- whole-location shuffled-G（整地点 DEM 交换）。

G 的作用通常比 D 弱，不要求为了证明世界模型强行制造大提升。若 no-G 持平，应把 G 降为有物理解释的可选先验，而不是夸大。

---

## 10. EarthNet2021x 数据、manifest（清单）和测试轨道约束

### 10.1 当前可用的正式轨道

服务器本地数据只有以下五个顶层目录，并且它们就是本项目的正式协议：

```text
train/       # 训练来源
iid/         # 同分布主测试
ood/         # 空间域外主测试
extreme/     # 极端夏季补充测试
seasonal/    # 长时程季节循环补充测试
```

禁止根据目录名猜测不存在的细分测试轨道，也禁止找不到指定目录时回退扫描数据根目录。当前数据的时间范围和文件数由冻结脚本写入 `inventory.json`，而不是靠口头描述。

### 10.2 只读冻结脚本与输出

新增脚本：

```text
scripts/freeze_earthnet2021x_protocol.py
```

它只读取文件路径、大小和文件名日期，不打开 NetCDF 阵列、不下载数据、不使用 GPU。它输出：

```text
train_dev.json     # role=train，开发训练
val_dev.json       # role=val，固定 train-tile 验证
train_all.json     # role=train，最终固定预算重训
iid.json           # 锁定主测试
ood.json           # 锁定主测试
extreme.json       # 锁定补充测试
seasonal.json      # 锁定补充测试
protocol.json      # tile 选择、seed、禁止测试集调参规则
inventory.json     # 文件数、tile 数、日期范围
```

冻结输出目录必须是新目录。实现会先在同级私有 staging（暂存）目录中写全套 JSON，并在所有文件
完成落盘后才一次性发布；已有目录会被拒绝覆盖。这样一次被取消的 NAS 任务不会留下看似完整、实际
混杂版本的正式 protocol（协议）目录。

### 10.3 两种 manifest 不要混淆

数据下载目录中的：

```text
.manifests/earthnet2021x_train.json
```

记录远程对象、远程路径和文件大小，服务于下载/同步。

项目冻结脚本生成的：

```text
artifacts/protocols/earthnet2021x_standard_v1/train_dev.json
```

记录本次正式训练使用的本地相对路径、sample id、大小、role（训练/验证用途）和摘要，服务于可复现训练。两者不能互相替代。

### 10.4 正式训练、验证与测试顺序

1. `train_dev` 训练，`val_dev` 选择 checkpoint 和固定训练步数；
2. IID/OOD/Extreme/Seasonal 从不参与调参；
3. 开发决策冻结后，可以用 `train_all` 按固定预算重训；
4. 主表报告 IID 与 OOD 的 EarthNetScore（ENS）及分量；
5. Extreme 与 Seasonal 作为极端驱动与长时程世界模型证据。

---

## 11. 训练工程必须补齐的内容

### 11.1 模型工厂，而不是在一个类里堆 mode 分支

建议新增：

```text
models/dynamics/obsworld_factory.py
```

工厂接受：

```yaml
model:
  family: obsworld_stage2_v2
  forecast_mode: direct_path | rollout_t5 | rollout_partition
  driver_protocol: full24 | core12 | legacy9
```

创建共享组件后，实例化不同薄 wrapper（包装器）。不要继续把所有逻辑塞进旧 `ObsWorldStage2Model.forward()`，否则 Direct 和 rollout 很容易意外走不同输入或不同模块。

### 11.2 训练入口需要怎样改

保留：

```text
train/train_stage2_earthnet.py
```

但将它升级为以下职责：

1. 加载并深度校验 v2 配置；
2. 创建 v2 dataset 和 model factory；
3. 根据 checkpoint step 选择 rollout curriculum；
4. 选择分层监督 horizon；
5. 可选采样 partition 位置；
6. 计算主损失和 partition 损失；
7. 记录每步状态增量、状态方差、partition gap、D 有效率；
8. 原子保存完整 checkpoint；
9. 定期在开发验证集运行无泄漏评估；
10. 支持 Direct/rollout/full 三类配置，而不改变 CLI 主入口。

建议把可独立测试的逻辑移出大脚本：

```text
train/stage2_curriculum.py
train/stage2_checkpoint.py
```

### 11.3 move-to-device 必须递归

当前 `move_batch_to_device()` 只移动顶层 tensor。正式接口虽然默认不提供 `context_phi`，但未来可能包含嵌套字典。因此应实现递归移动：

```python
Tensor -> tensor.to(device)
dict   -> 对每个 value 递归
list   -> 对 tensor/dict 递归，meta 字符串保持 CPU
tuple  -> 同理
```

必须测试嵌套 dict，避免未来开启真实 `φ` 后出现 CPU/GPU 混用错误。

### 11.4 checkpoint 必须保存哪些内容

正式 checkpoint 最低包括：

```text
global optimizer step
micro step / gradient accumulation state
model_state_dict
optimizer_state_dict
scheduler_state_dict
AMP scaler（若使用）
完整 resolved config（解析后的配置）
rollout curriculum 当前阶段
best validation 记录
Python/NumPy/Torch/CUDA RNG states
git commit 与 dirty 状态
train/val manifest path 与 digest
conditioning stats path 与 digest
Stage1.5 checkpoint path 与 sha256
官方 evaluator commit
PyTorch/CUDA/cuDNN 版本
world size、batch size、accumulation steps
```

保存仍采用：

```text
先写 .tmp -> fsync/关闭 -> os.replace 原子替换
```

### 11.5 精确续训测试

新增测试必须验证：

```text
固定 CPU、小模型、固定 batch：
连续训练 4 步得到 loss_4
训练 2 步保存 -> 重新创建模型并恢复 -> 再训练 2 步
两条路径第 4 步 loss、参数和采样 horizon 在容差内一致
```

现有兼容加载函数能处理旧 GeoTokenizer 参数名，但没有这项端到端恢复证据。正式 20 步训练成本高，不能等中断后才发现 resume（续训）不等价。

### 11.6 DDP 与未使用参数

不同模式可能导致分支未被调用。要求：

- 每个配置只实例化需要训练的 wrapper；
- `find_unused_parameters=false` 保持为默认；
- 单元测试检查所有 `requires_grad=True` 参数在一次相应模式前向后都有梯度；
- 关闭 D/G/H 时，对应 encoder 可冻结，但主网络结构不另换；
- partition 分支不开启时，不创建只属于它的可训练参数。

---

## 12. 配置文件规划

### 12.1 先把旧配置冻结下来

当前：

```text
configs/train/stage2_earthnet_main.yaml
```

应复制并明确保存为：

```text
configs/train/stage2_earthnet_legacy_direct9.yaml
```

它保留旧 checkpoint/旧 D 接口的回归能力。随后原 `stage2_earthnet_main.yaml` 可以改成指向正式 full model，或者只作为注释入口；不能让同一个文件名在不同 commit 下悄悄代表两种完全不同协议而没有 schema version。

### 12.2 正式配置矩阵

最低新增：

```text
configs/train/stage2_earthnet_v2_smoke.yaml
configs/train/stage2_earthnet_v2_direct24.yaml
configs/train/stage2_earthnet_v2_rollout24.yaml
configs/train/stage2_earthnet_v2_partition24.yaml
```

消融由脚本从正式配置生成：

```text
stage1_init
stage15_init
no_D
shuffled_D
core12
no_G
```

### 12.3 正式配置必须显式出现的字段

```yaml
protocol:
  schema_version: 2
  dataset_protocol: earthnet2021_standard_v1
  driver_protocol: full24
  eobs_variables: [fg, hu, pp, qq, rr, tg, tn, tx]
  eobs_aggregations: [mean, min, max]
  dem_variable: cop_dem

data:
  root: /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021
  manifest_path: null          # formal run 必填
  require_manifest: true
  conditioning_stats_path: null # formal run 必填
  context_img_size: 256
  target_img_size: 128
  geo_img_size: 128
  context_frames: 10
  target_frames: 20
  weather_steps: 30

model:
  forecast_mode: rollout_partition
  stage15_checkpoint: null      # formal run 必填或 CLI 覆盖
  compute_latent_targets: false
  decoder:
    img_size: 128
    patch_size: 8

training:
  open_loop: true
  teacher_forcing_future_state: false
  max_steps: 50000
  horizons_per_sample: 6
  rollout_curriculum: [...]

partition:
  enabled: true
  direct_steps: 2
  substeps: [1, 1]
  detach_start: true
```

正式 preflight（运行前检查）遇到 `null` 必须退出，不允许自动猜服务器路径。

---

## 13. 按文件列出的具体代码改造

### 13.1 数据层

#### 新增 `data/earthnet_conditioning.py`

必须实现：

- 8 字段和 3 聚合方式的唯一常量；
- 24-D feature names 自动生成；
- daily train z-score；
- 30×24 五日聚合；
- `D_mask` 和 `valid_day_count`；
- 30×2 `C_path`；
- `delta_t_path`；
- full24/core12/legacy9 的显式协议选择；
- stats-v2 读取、schema 和 manifest digest 校验。

#### 修改 `data/datasets/earthnet2021.py`

必须实现：

- `protocol_version=1/2` 显式分流；
- v2 NetCDF 必须读取全部 8 个 E-OBS；
- 生成完整 30 token，而非只生成 20 个累计目标条件；
- context 与 target 使用不同空间尺寸；
- formal 模式只读取 `cop_dem`；
- 返回 Stage2BatchV2；
- legacy 路径行为保持不变；
- strict 模式不允许从指定 split 回退到数据根目录；
- meta 记录源文件、start/end date、tile、manifest digest。

#### 修改 `data/stage2_contract.py`

必须实现：

- v1/v2 两套显式 validator（校验器）；
- v2 逐字段形状、dtype、有限性和时间长度校验；
- `D_path[:,10]` 是第一未来段的语义注释和测试入口；
- model/training/evaluation 三视图继续隔离；
- `official_eval_*` 出现在 model view 时立即报错；
- `x_target/target_mask` 只在明确辅助分支开关时进入模型，主配置永远关闭。

#### 新增 `scripts/build_earthnet_conditioning_stats.py`

必须实现：

- 只接受 train manifest；
- 流式计算 8 个 daily mean/std，避免把全量数据放内存；
- 计算 D/G 有效率和审计摘要；
- 写 stats-v2 和独立 log；
- 支持 `--max-files` 仅用于 smoke，并在输出中标记 `is_full_train=false`；
- 正式 preflight 拒绝使用不完整统计量。

#### 修改 `scripts/preflight_stage2_earthnet.py`

新增检查：

- protocol schema 为 2；
- 8 字段和顺序一致；
- 30×24 与 30×2 时间路径；
- stats manifest digest 与 train manifest 相同；
- `cop_dem` 有效；
- Stage1.5 checkpoint 三部分严格兼容；
- Direct/rollout/full 模型能创建；
- 正式 split 清单非空且名称没有静默回退。

### 13.2 模型层

#### 新增文件

```text
models/dynamics/interval_driver_encoder.py
models/dynamics/controlled_transition.py
models/dynamics/obsworld_core.py
models/dynamics/obsworld_direct_path.py
models/dynamics/obsworld_rollout.py
models/dynamics/partition_consistency.py
models/dynamics/obsworld_factory.py
```

`obsworld_core.py` 只放共享的：

- observation encoder（观测编码）；
- state initializer（状态初始化）；
- geo token；
- decoder；
- 条件消融统一处理。

Direct 和 rollout wrapper 不得复制两套 Stage1.5 编码代码。

#### 修改 `models/dynamics/context_state_aggregator.py`

- 允许 float coverage；
- coverage 为 0 时严格屏蔽；
- 可配置 first/last 有效阈值；
- 保持旧布尔 mask 兼容；
- 不增加破坏 checkpoint 的无必要参数。

#### 修改 `models/losses/earthnet_forecasting.py`

- 保留现有基本损失；
- 接收可选 partition 输出；
- 每项损失分开返回和记录；
- 分母为有效像素数，0 有效像素时安全返回 0；
- 不让 NaN target 先参与减法再乘 mask；
- NDVI 的 red/nir 索引由 BandSpec 传入，不硬编码猜测。

### 13.3 训练和评估层

#### 修改 `train/train_stage2_earthnet.py`

- 使用新 factory；
- 使用 v2 horizon/curriculum；
- 递归 move-to-device；
- partition 采样；
- 新日志和 checkpoint provenance；
- 保持 legacy config 可运行；
- 验证时始终运行完整 20 步，而不是当前课程长度。

#### 修改 `eval/predict_stage2_earthnet.py`

- 从 checkpoint 中恢复准确模型 mode 和协议；
- 默认拒绝 config/checkpoint mode 不一致；
- v2 直接输出 128×128，避免无必要 resize；
- summary 记录 checkpoint digest、manifest digest、stats digest、git commit；
- 保持只把 model-input view 送入模型。

#### 修改 `eval/eval_stage2_earthnet.py` 与 `eval/score_earthnet_prediction_dir.py`

- 按冻结 manifest 评分并写入 target/prediction manifest 摘要；
- 使用 EarthNetScore（ENS）与 MAD/OLS/EMD/SSIM 分量；
- 记录模型运行来源；
- 测试集评分不负责选择 best checkpoint。

---

## 14. 必须新增的测试

### 14.1 数据与协议测试

新增：

```text
tests/test_earthnet_conditioning_v2.py
tests/test_stage2_contract_v2.py
```

最低用例：

1. 8 个字段×3 聚合得到 24 维；
2. 24 维顺序与公开实现一致；
3. 单调天气证明 5 日窗口边界正确；
4. `D_path[10]` 使用日 50–54；
5. 部分 NaN 时跳过 NaN，mask 为 1；
6. 整个五日变量全 NaN 时值为 0、mask 为 0；
7. stats 只能匹配同一 train manifest；
8. v2 formal 模式缺任意 E-OBS 或 `cop_dem` 时失败；
9. context=256、target/G=128；
10. model/training/eval 三类字段隔离。

### 14.2 模型测试

新增：

```text
tests/test_interval_driver_encoder.py
tests/test_obsworld_direct_path.py
tests/test_obsworld_rollout.py
tests/test_partition_consistency.py
tests/test_stage2_model_fairness.py
```

最低用例：

- interval encoder 支持 L=1/2/4；
- 全缺 D 时仍有限；
- rollout 输出 20 个状态；
- 改变 `x_target` 不改变正式预测；
- 改变未来第 k 个 D token 不能影响 k 之前的 rollout 预测；
- 第 k 个 D token 应能影响 k 及之后预测；
- 20 步 transition 的 parameter id 完全相同；
- 人工加法转移下，10 天与 5+5 严格相等；
- partition 两支都收到 endpoint 梯度；
- Direct24 与 rollout24 的共享核心参数量一致；
- 所有 trainable parameter 在对应模式下有梯度；
- decoder 输出 `[B,T,4,128,128]`。

### 14.3 训练工程测试

新增：

```text
tests/test_stage2_curriculum.py
tests/test_stage2_checkpoint_resume.py
tests/test_stage2_v2_smoke.py
```

最低用例：

- curriculum 在边界 step 切换正确；
- 100 天在完整阶段始终被抽到；
- checkpoint 恢复后 next-step（下一步）结果可复现；
- DDP 不存在未使用可训练参数；
- CPU 小模型 Direct/rollout/partition 都能 forward+backward；
- 4 个合成样本 overfit 时 loss 明显下降。

### 14.4 官方评估集成测试

新增：

```text
tests/test_earthnet_export_v2.py
```

最低用例：

- 输出变量名为 `ndvi_pred`；
- 时间坐标严格为未来 20 个五日时刻；
- lat/lon 与目标一致；
- 128×128 RGBN 转 NDVI 的 band 索引正确；
- manifest 缺预测文件时失败；
- evaluator 与已锁定官方 commit 的合成结果一致；
- 评分 mask 从不进入模型输入。

---

## 15. 从开发到正式训练的执行顺序

### M0：保护现有代码

要做：

1. 把当前配置复制为 `legacy_direct9`；
2. 记录当前 36 tests 基线；
3. 增加旧 Direct 一次前向回归测试；
4. 不删除当前 `ObsWorldStage2Model/DriverEncoder/build_earthnet_dgh_stats.py`。

通过条件：旧测试不退化，旧 checkpoint 仍可加载。

### M1：完成 Stage2-0 数据契约

要做：

1. 写 `earthnet_conditioning.py`；
2. 写合成全 8 字段 NetCDF；
3. 通过官方 24-D 数值口径测试；
4. 改 loader 输出 v2；
5. 固定 cop_dem；
6. 完成 stats-v2 和 preflight-v2。

通过条件：随机真实样本和合成样本均输出正确形状、无泄漏、无 NaN。

### M2：完成 matched Direct24

要做：

1. IntervalDriverEncoder；
2. ControlledTransition；
3. Formal Direct wrapper；
4. 128 解码器；
5. CPU/GPU smoke；
6. 32–128 个真实 cube 小样本过拟合。

通过条件：Direct24 loss 能下降，正式导出和官方评分链路跑通。

### M3：完成 rollout24

要做：

1. 20 步共享递推；
2. curriculum；
3. 分层 horizon 解码；
4. 长度/梯度/因果时间测试；
5. 与 Direct24 相同设置的小规模比较。

通过条件：20 步无 NaN；100 天优于或接近简单 persistence；没有未来真值回灌。

### M4：完成 partition full model

要做：

1. 10 天 vs 5+5；
2. 状态、观测和 endpoint 三类约束；
3. partition gap 日志；
4. 状态方差/增量范数监测；
5. 对照 rollout-no-partition。

通过条件：gap 下降且主预测不明显退化；否则先调权重，不进入正式主表。

### M5：小规模 result-to-claim（结果到论点）闸门

运行：

- persistence；
- Direct24；
- rollout24；
- full partition；
- true-D/no-D/shuffled-D 的小子集；
- Stage1/Stage1.5 至少一组配对。

只有方向合理才放大正式训练。

### M6：正式种子和论文评估

优先：

1. 完整主方法 3 seeds；
2. 正式 Direct24 3 seeds；
3. rollout-no-partition 3 seeds；
4. 关键 D 干预；
5. 2×2 中剩余格子；
6. core12/no-G 等次级消融。

时间不足时，先保证与两条中心 claim（论点）直接对应的结果，不要为了堆实验牺牲主表完整性。

---

## 16. 实验—论点—代码的闭环

AAAI 正文建议最多突出两个方法论点。

### Claim 1：可预测地表状态能在外生驱动下进行稳定开放循环推演

| 证据 | 为什么做 | 理想现象 | 失败时怎么解释 |
|---|---|---|---|
| 官方 IID/OOD 预测主表 | 证明最终未来观测可核验 | Full competitive，明显胜 persistence/climatology | 若很差，不能靠世界模型措辞掩盖 |
| Direct24 vs rollout24 | 区分直接拟合与递推 | rollout 长期不崩，差距可接受或更好 | rollout 明显差说明误差累积未解决 |
| horizon curve | 看 5–100 天退化 | 平滑退化，100 天仍有 skill | 中途突增通常提示索引/状态不稳 |
| Stage1 vs Stage1.5 初始化 | 检查状态学习投资是否有效 | Stage1.5 长期更好或更稳 | 持平则把 Stage1.5 降为工程初始化 |

### Claim 2：共享转移对驱动轨迹敏感，并具有时间可组合性

| 证据 | 为什么做 | 理想现象 | 失败时怎么解释 |
|---|---|---|---|
| true/no/shuffled D | 排除模型忽略 D | true-D 最好，paired delta 一致 | 持平则不能强说驱动控制 |
| 10 天 vs 5+5 gap | 直接测组合性 | Full 的 gap 小于 no-partition | gap 降但预测变差说明约束过强 |
| Direct/compose 两支 endpoint | 防止常数塌缩 | 两支都保持真实预测能力 | 只一致但不准不构成世界模型证据 |
| G/no-G | 检查地理先验 | OOD 或长期小幅稳定增益 | 持平可诚实降级为可选先验 |

### 16.1 下游任务是不是必须

当前不是硬性必须。只要上面两条 claim 的证据完整，公开主表、递推、驱动干预和组合性已经构成比普通预测更强的世界模型闭环。

下游任务只有在以下条件满足后才做：

- Full 主表已经完成；
- 组合性和 D 干预成立；
- 正文或补充材料仍有时间；
- 下游任务能使用预测状态，而不是另起一篇无关工作。

### 16.2 大模型 + ours 是否无用

不是无用，而是当前优先级低。最合理的后续方式是：

- 用 SkySense/Prithvi/DOFA 等强骨干替换 `I`；
- 保持相同 `T/DGH/partition/Dec`；
- 检查机制增益是否跨骨干存在。

如果现在同时换骨干和写新动力学，会让贡献边界更加模糊，也增加截止风险。因此它属于 Stage4，而不是 Stage2 的依赖。

---

## 17. 什么结果才算“可继续”，什么才算“AAAI 就绪”

### 17.1 工程可继续标准

以下全部满足才允许长训练：

- v2 数据测试全部通过；
- 全 8 字段和固定 feature order 通过；
- manifest/stats/checkpoint digest 对齐；
- 三类 mask 隔离测试通过；
- Direct/rollout/partition 小模型 forward/backward 通过；
- 4–32 样本 overfit loss 能下降；
- 20 步无 NaN/Inf；
- checkpoint 精确恢复通过；
- 官方导出和合成评分通过。

### 17.2 小试验可放大标准

建议至少满足：

- 100 天 rollout 不比 persistence 灾难性更差；
- Direct24 和 rollout24 的差距可以解释；
- partition gap 下降而主预测基本不退化；
- true-D 相比 no-D/shuffled-D 至少出现稳定方向；
- 状态 token 方差不塌缩；
- 不同样本预测不是几乎完全一样。

### 17.3 AAAI 证据标准

理想情况：

- 官方指标上 Full 与 Contextformer 等强基线有竞争力，最好有提升；
- Full 优于 matched Direct 或至少在长期/组合性上明显更强；
- partition 显著缩小 direct/composed gap；
- true-D 的配对收益在多种子上方向一致；
- Stage1.5 对长期状态有可复现收益；
- 关键差值报告均值、标准差和 paired bootstrap confidence interval（配对自助置信区间）。

风险边界：

- 如果 Full 比强基线 RMSE 明显差很多，同时组合性和 D 干预也不成立，不能投稿为强世界模型；
- 如果预测略逊但组合性、D 响应和长期稳定性非常强，可以收紧为机制型世界模型论文；
- 如果 Stage1.5 持平，不必推翻 Stage2，但不能把成像解耦写成已被 EarthNet 主实验强证明；
- 如果 D-core12 与 full24 持平，这是“紧凑驱动足够”的有效结果，不是失败；
- 单次 seed 的小差异不能写成稳定提升。

本文件不预先伪造具体性能数字。正式阈值应根据 persistence、climatology、Contextformer 复现和首个 pilot 的尺度冻结。

---

## 18. 日志与故障诊断

每次训练至少记录：

### 18.1 优化指标

- total/obs/ndvi loss；
- 各 partition loss；
- learning rate；
- gradient norm；
- sec/step、显存峰值；
- 当前 rollout 长度。

### 18.2 状态诊断

- `mean/std/norm` of `s0`；
- 每步 `||s_{j+1}-s_j||`；
- 第 1/5/10/20 步状态方差；
- direct/composed state gap；
- direct/composed observation gap；
- 全无效 context token 比例。

### 18.3 数据诊断

- 每个 E-OBS 变量 any-valid/all-five-valid 比例；
- G 有效率；
- target clear fraction；
- 每个 batch 的 sample id；
- manifest/stats digest；
- 实际使用的 Stage1.5 checkpoint。

### 18.4 常见异常对应排查

| 异常 | 优先排查 |
|---|---|
| 第一步就 NaN | D 全缺窗口、NDVI 分母、全空 mask、AMP 溢出 |
| 预测全常数 | decoder 饱和、partition 权重过大、状态塌缩 |
| 5 天好、100 天突然爆炸 | rollout 索引、残差尺度、梯度、状态范数 |
| Direct 好、rollout 很差 | 误差累积、课程过快、T 只会长段摘要 |
| no-D 与 true-D 一样 | D 未接入、mask 全零、C 泄漏天气季节替代、模型忽略 D |
| shuffled-D 更好 | donor 映射错误、D 时间错位、过拟合或统计量错误 |
| Stage1.5 比 Stage1 差 | checkpoint 路径错误、state projector 不匹配、EarthNet φ 缺失域差异 |
| 官方分数异常但内部 MAE 正常 | NDVI band、输出时间、mask/eligibility、128 resize、聚合顺序 |

---

## 19. 明确不在第一轮做的内容

为了防止开发无边界扩张，以下不是 Stage2-v2 第一轮必做：

- 下载全新无关主数据集；
- 重新训练一个完全不同的大骨干；
- 预测未来天气；
- 多传感器未来成像渲染；
- L1C/L2A 跨产品主实验；
- 不确定性扩散生成；
- 复杂 ODE/SDE 动力学；
- 土地覆盖、火灾、洪水等多个下游任务；
- 20 天以上的多种随机 partition；
- 把极端/季节长序列全部塞入正文主表；
- 为追求“物理”而加入无法核验的守恒损失。

这些都可以在核心 Stage2 通过后继续，但不能阻塞当前世界模型闭环。

---

## 20. Definition of Done：Stage2 到什么程度才算完成

### L0：旧原型完成（当前大致状态）

- 旧 9-D Direct 可运行；
- 官方评估基础存在；
- mask 隔离基础存在。

这不等于正式 Stage2。

### L1：数据和协议完成

- v2 contract；
- full24/core12/legacy9 分离；
- 30-token 时间对齐；
- stats-v2；
- fixed cop_dem；
- manifest/track gate；
- 数据单测通过。

### L2：公平预测模型完成

- Direct24；
- rollout24；
- 相同输入/模块/预算；
- CPU/GPU smoke 和小样本 overfit；
- 官方导出可运行。

### L3：完整 ObsWorld 动力学完成

- shared transition；
- 20 步 open-loop；
- variable-step；
- 10 vs 5+5 partition；
- endpoint 监督；
- D 干预；
- 无泄漏和续训测试。

### L4：论文级完成

- 官方测试主表；
- matched Direct/rollout/full；
- horizon curve；
- partition gap；
- true/no/shuffled D；
- Stage1/Stage1.5 配对；
- 多种子与统计；
- 完整运行来源记录；
- 结果支持两条中心 claim。

只有达到 L4，才可以说“Stage2 已经支撑 AAAI 论文”。

---

## 21. 开发者逐项勾选表

### 数据

- [ ] 保存 legacy 9-D 配置和测试；
- [ ] 新增 full24 常量和唯一 feature order；
- [ ] 新增 daily train normalization；
- [ ] 新增 30×24 D_path/D_mask；
- [ ] 新增 30×2 C_path；
- [ ] 新增 delta_t_path；
- [ ] 固定 D_fut 从 index 10 开始；
- [ ] 固定 cop_dem；
- [ ] context 256、target/G 128；
- [ ] stats-v2 与 manifest digest；
- [ ] 官方 track 映射报告。

### 模型

- [ ] 共享 observation-state core；
- [ ] IntervalDriverEncoder；
- [ ] ControlledTransition；
- [ ] Direct24 wrapper；
- [ ] Rollout24 wrapper；
- [ ] Partition helper；
- [ ] 128×128 decoder；
- [ ] coverage-aware context aggregation；
- [ ] no-D/no-G 统一开关；
- [ ] legacy Direct 不被删除。

### 训练

- [x] rollout curriculum（递推课程）；
- [x] stratified horizon supervision（分层预测时距监督）；
- [x] 100 天必选；
- [x] 主损失；
- [x] partition 四项损失；
- [x] 冻结/解冻；
- [x] 递归 move-to-device；
- [x] checkpoint provenance（检查点来源记录）；
- [x] 精确 resume（续训）测试；
- [x] 状态与 gap（两路径差距）日志；
- [ ] 真实数据的 32–128 cube overfit（小样本过拟合）和 one-seed Gate（单随机种子闸门）。

### 评估

- [ ] 物理 split 与论文 track 名一致；
- [x] v2 export（checkpoint 契约、原子 NPZ、prediction manifest）；
- [x] 官方指标链路（EarthNetScore 与评分 provenance 的合成小样本验证）；
- [ ] persistence/climatology；
- [ ] Direct/rollout/full；
- [ ] horizon curve；
- [ ] true/no/shuffled D；
- [ ] partition gap；
- [ ] Stage1/Stage1.5；
- [ ] 多种子与置信区间。

### 安全与可复现

- [x] target/eval mask 不进入模型；
- [x] checkpoint/config 契约、prediction manifest 与 score provenance；
- [ ] 不使用测试集选 checkpoint（E-2 记录并保护测试导出，但最终仍须在 `val_dev` 锁定选择）；
- [ ] 不伪造 EarthNet `φ`；
- [ ] 不把真值天气写成业务预报；
- [ ] 不把 9-D vs 24-D 差异写成架构收益；
- [x] 训练 checkpoint 可追溯到 git/config/data/stats/checkpoint；
- [x] 预测目录与官方评分 JSON 的同等来源记录（E-2）。

---

## 22. 推荐的第一次开发提交边界

第一次代码提交不要同时包含所有模型。实际实现边界为：

```text
Commit A：Stage2-v2 data contract
  - earthnet_conditioning.py
  - dataset v2 path
  - stage2_contract v2
  - stats-v2 script
  - preflight v2
  - synthetic tests
  - legacy regression tests
```

截至本次更新，上述 Commit A 项目均已实现并通过 CPU 合成/legacy 回归测试；下一次代码修改应从 Commit B 开始，避免把模型结构改动混进数据提交。

第二次：

```text
Commit B：Matched Direct24
  - interval driver encoder
  - controlled transition
  - shared core
  - direct wrapper/factory
  - 128 decoder path
  - forward/backward/overfit tests
```

第三次：

```text
Commit C：Rollout24
  - recursive model
  - curriculum
  - horizon sampling
  - resume and temporal-causality tests
```

第四次：

```text
Commit D：Partition full model
  - variable-step branch
  - partition losses
  - state/gap diagnostics
  - matched experiment configs
```

第五次拆成两个小而可核验的提交：

```text
Commit E-1：训练 provenance 与精确恢复（已完成）
  - 原子 checkpoint 保存
  - config/manifest/stats/Stage1.5/Git/runtime 来源记录
  - RNG + deterministic sampler + data-position 恢复
  - CPU 中断/恢复等价测试

Commit E-2：正式 export/evaluation provenance（已完成）
  - checkpoint/config/manifest 协议兼容性检查
  - prediction manifest 与输出摘要
  - 官方 evaluator 结果 JSON 的输入来源记录
  - 测试集导出与 best-checkpoint 选择在来源记录上隔离；研究流程仍必须只在 `val_dev` 选模型
```

这样每次出错都能定位，不会在一个巨大 commit 中同时混入数据、网络和评估问题。

---

## 23. 当前立即行动建议

按今天的实际状态，推荐顺序是：

1. 等当前 Stage1.5 自然结束，不中断；
2. 记录最终 `state_bridge_60k` checkpoint 的真实文件名和 sha256；
3. 全量审计继续后台运行，但不要让多个全盘 NAS 扫描同时争抢 I/O；
4. A–D、E-1 与 E-2 已完成；用 64 个真实样本生成 smoke stats-v2，仅做代码验证；
5. 合成测试通过后再生成完整 train stats-v2；
6. 用 Direct24、rollout24、partition24 分别跑 32–128 cube overfit；
7. 先跑单 seed 小规模 result-to-claim 闸门；
8. 方向成立再投入 3-seed 正式训练。

当前不需要用户再提供新的数据字段样例，除非：

- 全量审计发现某些 E-OBS 数值类型/维度异常；
- 本地 `iid/ood` 无法从文件名和官方配置解析成论文 track；
- 最终 Stage1.5 checkpoint 缺少 encoder/phi/state_projector 其中之一。

---

## 24. 参考依据

### 本项目内部

- [48：EarthNet2021x 统一数据协议与主实验规范](./48_ObsWorld_EarthNet2021x统一数据协议与主实验规范_20260716.md)
- [39：独立审查](./39_ObsWorld_AAAI叙事前沿文献公开数据与代码独立审查_完整汇总.md)
- [45：AAAI-27 最终数据、DGH、叙事与主实验决策](./45_ObsWorld_AAAI27最终决策_数据DGH叙事与主实验_20260715.md)
- [46：代码改造与并行执行路线](./46_ObsWorld_AAAI27代码改造与并行执行路线_20260715.md)

### 官方公开依据

- [EarthNet2021 原论文与 EarthNetScore](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf)
- [EarthNet Models PyTorch](https://github.com/earthnet2021/earthnet-models-pytorch)
- [Contextformer 官方模型代码（相关工作与强基线参考）](https://github.com/earthnet2021/earthnet-models-pytorch/blob/main/earthnet_models_pytorch/model/contextformer.py)

---

## 25. 最终结论

后续代码开发不应把现有 Stage2 原型直接延长训练后就当成完成。真正需要完成的是：

> 在保留 Stage1/1.5 和 DGH 投资的基础上，把旧 9-D 累计 Direct 原型升级为同一 24-D 五日驱动路径下的 matched Direct、共享五日 rollout 和可变步长 partition 三层系统；以固定 Copernicus DEM、独立日历/时间条件和严格 mask 隔离保证输入逻辑，以原生 128×128 RGBN 解码和 49 审计后冻结的官方指标保证结果可核验，以 D 干预和时间分割一致性证明它不是普通图像预测器。

这条路线没有放弃“模拟真实世界”的核心思想，也没有推翻已经完成的 Stage1.5。它做的是把“世界模型”从叙事词汇落实成可检查的代码属性和实验属性。
