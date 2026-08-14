# 59 ObsWorld Stage2：当前问题、证据缺口与代码约束汇总

日期：2026-07-17  
性质：研究与工程状态审计；**本文件不修改正在运行的训练，也不把任何待完成能力写成已完成结果。**

## 0. 一页结论

当前 8 卡 B64、200 epoch 的 `Direct-P4` 训练是一条有效的正式候选训练线：它已经验证了 EarthNet 数据、Stage1.5 初始化、physical4 驱动、8 卡训练、checkpoint、日志和本地缓存能够共同工作。但它**不是**完整 ObsWorld 主结论，也不能直接产出论文主表。

目前项目不是“还差把训练跑完”，而是处于下面这个状态：

```text
训练基础设施与 Direct-P4 路径：                    已能真实运行
完整 val_dev 选择 + 真实官方 ENS 评分闭环：          尚未实证闭环
严格配对的 shared open-loop Rollout：               模型代码有，正式 8,800-step 配方没有
physical4 与 full24 的最终输入选择：                尚未按同协议完成比较
Partition：                                          模型代码有，当前只应作为后续支持性证据
Observation correction / U：                         单元模块有，端到端训练与评估链路没有
论文级基线、统计、表格与结果冻结：                   尚未形成正式 bundle
```

所以最重要的边界是：

1. 当前 Direct-P4 跑完后，可以得到 **Direct-P4 的候选 checkpoint 和开发集证据**；不能据此声称共享递推更好、正式 ENS 已可信，或 U 已能校正新观测。
2. 当前的主要缺口不是 GPU 是否能跑满，也不是缓存是否能复制，而是“模型主张—真实评分—公平对照—统计结果”之间还没有形成完整证据链。
3. 代码不宜现在盲目同时加 U、Partition、full24、更多数据集。每一条都有前置门；否则会产生许多不可公平比较的 checkpoint，却没有可写入论文的一条结论。

## 1. 本次回顾的文档与口径对齐

本文件综合了下列材料，并以代码静态审计来区分“设计已写出”“模块已存在”“端到端已可训练”“已有正式结果”四种不同状态。

| 来源 | 它已经明确的主张 | 对当前问题的含义 |
|---|---|---|
| `52_ObsWorld_AAAI27中心叙事训练实验与写作总纲_20260716.md` | no-U 主干是 `Stage1 → Stage1.5 → Direct-P4 → Rollout-P4 → val 选择 → IID/OOD`；U 是条件升级 | Direct 与 Rollout 必须严格配对；U 不能因为有概念或单元测试就进入标题和主结果 |
| `56_ObsWorld_Stage2_200epoch_8卡训练计划与关键Checkpoint命令_20260717.md` | 8×H200、每卡 B64、8,800 optimizer steps、100/150/200 epoch checkpoint；本地缓存的安全语义 | 当前训练/缓存/恢复问题已大体工程化解决，但 `train_val` 缓存不能替代以后 IID/OOD 评测缓存 |
| `57_ObsWorld_Stage2_下一步建议与physical4_full24_NAS启动调查_20260717.md` | E0--E4 评估闭环、Direct24、rollout schedule、U 的端到端缺口 | 当前最紧急的代码工作应面向正式评估与公平对照，而不是重写已有 scorer 或继续调 I/O |
| `58_ObsWorld_AAAI27中文论文终稿_主实验冻结版_20260717.md` | 论文当前是 no-U 版本；所有关键结果、表格、结论均为待填且受决策门限制 | 论文文字不能领先于真实证据；`U`、`Partition`、full24 和官方分数都必须按各自门槛进入 |

说明：此前题为“Stage2 本地缓存与 manifest 暂存运行指南”的旧 58 文档已合并进 56。这里所说的 **58** 是当前的“AAAI-27 中文论文终稿（主实验冻结版）”，避免把两份不同主题的 58 混淆。

## 2. 最终想证明什么，以及每一条需要什么证据

### 2.1 当前 no-U 版本的最小方法合同

给定 50 天历史观测、未来 100 天的已知外生驱动和静态地理信息，当前主方法应当实现：

$$
z_0 = I_\theta(x_{1:T_c};\bar\phi),
$$

$$
z_{k+1} = F_\theta(z_k, D_k, C_k, G, \Delta t_k),
$$

$$
\hat{x}_{k+1} = O_\theta(z_{k+1}).
$$

- `I`：从历史 RGBN 和固定中性 $\bar\phi$ 构造初始预测状态；
- `F`：在 physical4 / full24、日历、地理和时间间隔条件下推进状态；
- `O`：把状态解码成未来可由 EarthNet 验证的 RGBN / NDVI 观测。

这只支持“预测状态在共享受控转移下被开放循环推进”的**可检验假设**。它不自动支持完整地球模拟、严格因果动力学、数字孪生或实时采集条件感知。

### 2.2 Direct、Rollout、Partition、U 分别回答什么

| 组件 | 真正的问题 | 成功时可支持的结论 | 不能单独支持的结论 |
|---|---|---|---|
| Direct-P4 | 从同一初始状态直接预测多个未来时距能做多好？ | 数据、驱动和预测管线可以形成强的长期预测器 | 共享递推有效；状态能长期自洽 |
| Rollout-P4 | 同一五日转移反复使用后，长期预测是否仍可靠？ | shared open-loop transition 的最低实证 | 严格物理定律或严格半群 |
| Partition | 10 天一次走完与 5+5 走完是否近似一致？ | 某条相同控制路径的分段一致性得到支持 | 因果正确、任何步长可组合、长期一定更优 |
| Observation correction / U | 新的部分观测到来后，后续预测能否被安全修正？ | 若优于在线更新强基线，可支持 re-observation correction | 不确定性建模、实时采集条件感知，或仅凭 no-update 自比就称创新 |

### 2.3 当前有一个需要在后续决策前明确的路线分歧

52/58 的冻结叙事把 `physical4` 视为预先选择的紧凑主驱动：先完成 `Direct-P4 → Rollout-P4` 的配对主实验，`full24` 是可选消融。57 则建议先完成同预算的 `Direct24`，再仅在完整 `val_dev` 上锁定后续 rollout 使用哪个 driver。

两种方案都可以科学成立，但不能混用：

| 路线 | 顺序 | 优点 | 代价 / 写作约束 |
|---|---|---|---|
| A：保持原冻结主线 | Direct-P4 → Rollout-P4；full24 后做为消融 | 最短，Direct 与 Rollout 的主线最清楚 | 必须明确 physical4 是预先指定的紧凑驱动，不能事后称它“经比较最优” |
| B：先锁定输入 | Direct-P4 与 Direct24 完整 `val_dev` 比较 → 选一个 driver → 配对 rollout | driver 选择更有实证依据 | 多一条完整训练；之后不能把被淘汰的 driver 当作最终主输入 |

这不是代码 bug，而是研究协议选择。下一轮开始大规模 rollout 以前，应选择其中一条并写入冻结配置与论文口径；不要并行跑多个 rollout 后再看 test 数字决定叙事。

## 3. 已经具备的基础：不要把已解决问题重复当作研究缺口

### 3.1 数据、训练和恢复基础

- 冻结的 `train_dev.json`、`val_dev.json` 和对应 physical4 统计文件已经在当前 Direct-P4 路径中使用；训练不再依赖 root glob 发现数据。
- Stage1.5 `checkpoint_step_60000.pt` 已被 Stage2 工厂加载，并在启动时有文件存在性检查。
- 8×H200、每卡 B64、global batch 512 的 Direct-P4 已经通过真实训练 smoke / 正式启动验证；此前 B64 的 OOM 来自另一作业占用约 108 GiB GPU 显存，不是 B64 的固有上限。
- `train/train_stage2_earthnet.py` 现有按 optimizer step 的 checkpoint、最佳 monitor checkpoint、epoch 命名 checkpoint、provenance、吞吐和 data/compute 日志。
- `scripts/run_stage2_earthnet_local_staged.sh` 已支持本地 `/tmp` 暂存、锁、完成性校验、`manual|auto` 清理、`all|train_val` scope 和空 GPU gate。

这些都是必要工程基础，但本身不是论文主张的证据。

### 3.2 已有模型/评估组件

| 组件 | 已有内容 | 当前地位 |
|---|---|---|
| `ObsWorldDirectPathModel` | 从共同 $z_0$ 和目标时距的控制路径做非递推预测 | 正在/将形成 Direct-P4 候选结果 |
| `ObsWorldRolloutModel` | 每个五日步把前一个预测状态交给同一 transition；无 teacher forcing | 代码真实存在，但还没有预算对齐的正式主实验 |
| `ObsWorldPartitionModel` | 10-day direct 与 5+5 composed 分支 | 支持性实验实现，不是当前主线结果 |
| `ObservationCorrectionCell` / `ObservationCorrectionRollout` | $q=0$ exact identity、staleness、predict-then-update 的独立单元契约 | 不是可训练的 Stage2-U 系统 |
| `eval_stage2_earthnet.py` | 冻结 manifest 上的内部 loss/RGBN/NDVI 指标，可选内存 official accumulator | 正确基础，不应重写 |
| `predict_stage2_earthnet.py` | 导出完整 20 帧 EarthNet 风格 prediction NPZ，并写 prediction manifest/hash | 正确基础 |
| `score_earthnet_prediction_dir.py` | 用官方 `EarthNetScore.get_ENS` 目录 scorer，并校验预测文件清单 | 正确基础，但 raw NetCDF 的正式 target 路径尚未做真实闭环实证 |

## 4. 当前缺口总表：缺什么、为什么缺、代码约束在哪里

下表中的“缺”并不都意味着完全没有代码。它可能意味着模块没有接线、实验协议未冻结、真实数据路径未验证，或没有足够强的对照和统计。

| 优先级 | 缺口 | 为什么现在还不能声称完成 | 主要代码/协议约束 | 最小验收产物 |
|---|---|---|---|---|
| P0 | 真实官方 EarthNetScore 闭环（E0） | 当前有预测导出和官方 scorer 入口，但尚未以真实 `.nc` cube 证明 target 目录、mask、命名和内存 scorer 一致 | `eval/predict_stage2_earthnet.py`、`eval/score_earthnet_prediction_dir.py`、原始 NetCDF 数据及官方 target 路径 | 1–2 个真实 cube 的 prediction/target/ENS provenance；与内存 `--official-score` 的差异说明或 parity 结论 |
| P0 | 完整 `val_dev` checkpoint 选择（E2） | `checkpoint_best.pt` 来自固定 512 样本 monitor，适合训练监控但不是完整开发集选择 | `train/train_stage2_earthnet.py` 的 validation subset；当前缺少候选批量评估与选择侧文件 | `selected_checkpoint.json`，列出预先锁定候选、完整 val 指标、选择规则和 hash |
| P0 | 结果 bundle / 表格汇总（E1/E3） | 单 checkpoint 可导出与评分，但没有一条命令固定所有输入、也没有防混 protocol 的表格聚合 | 需要把 config、stats、manifest、checkpoint、prediction、score 绑定在同一评估 run | `evaluation_run.json`、结果 CSV/Markdown、score provenance、tile/cube 统计输入 |
| P1 | physical4 与 full24 的公平比较 | Direct24 基础配置/数据合同存在，但目前没有与当前 B64/8,800 step 完全配对的正式实验和独立 full24 stats 证据 | full24 不能复用 physical4 的统计文件；不应修改基础 YAML 污染默认协议 | 派生 H200 配置、短 pilot、完整 val 对比；先于 IID/OOD 决定它是否只是消融或最终 driver |
| P1 | 正式 Rollout 的 H200 curriculum | rollout 模型是真实递推，但 24D 原 schedule 是 50k-step 量级；物理4配置默认 full-20，二者都不能直接当作公平的 8,800-step 配方 | `configs/train/stage2_earthnet_v2_rollout24.yaml` 的 0/2000/6000/12000/20000 schedule；当前每 epoch 44 update | 以 epoch 为单位解释的派生 rollout config，100–500 step B64 pilot，确认 full-20 真被训练 |
| P2 | Partition 的正式意义 | 分支代码有，但原 warmup 在 5,000 后开始、10,000 step 才满；8,800 结束仍只有 0.38 scale | `configs/train/stage2_earthnet_v2_partition*.yaml` 与 partition loss；还需保证 factual loss 不退化 | rollout 稳定后的一 seed val gate；只在 gap 下降且预测不退化时进入附录 |
| P1/P2 | Observation correction / U 的端到端链路 | correction cell 只接收抽象的 state/residual/q/reveal；没有真实 EarthNet 观测、reveal 数据、trainer 或 evaluator 将它们连起来 | `models/dynamics/observation_correction.py` 未被 `obsworld_factory.py` 注册；dataset/collate/trainer 不产生 reveal contract | 端到端 U model、reveal schedule、在线基线、day25/day50 evaluator、回归测试 |
| P1 | Stage1 vs Stage1.5 的预测消融 | 当前只有 Stage1.5 初始化进 Stage2；没有同预算的 Stage1 initializer 对照结果 | 旧 φ probe 有路径与切分问题，不能代替下游预测证据 | matched rollout 或最终主模型的 Stage1/Stage1.5 val、IID/OOD、长时距比较 |
| P1 | 强基线与统计 | 论文表的 Persistence/Climatology/Contextformer/PredRNN 或 SimVP 还未全部在同协议下形成结果；单 seed 也不足以宣称稳定优势 | 不能混用外部论文数值、不同 mask、不同 split 或不同 evaluator | 同协议 baseline run 或明确 †；最终 3 seed、tile-cluster paired bootstrap |
| P2 | 评测所需本地数据 scope | `train_val` local staging 只复制当前训练/开发集文件，故意不含 IID/OOD | launcher 只接受 `all|train_val`，尚无“显式任意评测 manifest” scope | `all` 本地缓存，或扩展为 manifest scope；正式 test 前确认文件清单与 provenance |

## 5. 代码层面的硬约束

这一节不是建议“立刻改代码”，而是说明后续实现不能绕过什么。它们决定了为什么某些看似简单的功能不能只加几十行。

### 5.1 数据、manifest、驱动统计和未来信息泄漏

1. `data/datasets/earthnet2021.py` 的训练 split 在 `require_manifest=True` 时必须有显式 manifest；根目录 glob fallback 已被禁用。这是对的：它避免不同机器或目录状态默默改变训练样本。
2. 训练和验证不是只需设置 `manifest_path`。`manifest_paths["train"]` / `manifest_paths["val"]` 必须与 split 对齐；此前 dataset smoke 因只设置通用 path 而报过 `split='train' requires an explicit manifest`。后续 U/正式评估不能重新绕开这个合同。
3. physical4 与 full24 的 feature name、输入维度和 train-only normalization statistics 是协议的一部分。工厂在 `models/dynamics/obsworld_factory.py` 中显式只接受 `physical4_v1` 或 `full24`，并要求 `model.driver_protocol == data.driver_protocol`。因此不能仅改 driver 名字、继续使用旧 stats，或把两个结果混在一表中而不标注。
4. 未来真实目标和 future valid mask 只能做 loss/eval，不能在该步预测前进入 $I$、$F$、$O$。对于 U，必须进一步区分：

   $$a=\text{是否揭示},\quad m_{clear}=\text{清晰像素},\quad m_{obs}=a\cdot m_{clear},$$

   以及用于 token 聚合的 $q_{obs}$。未揭示未来步的图像和 mask 即使留在 batch 中，也必须对状态更新严格无影响。

### 5.2 模型工厂约束：U 目前不在正式模型图中

`models/dynamics/obsworld_factory.py` 当前允许的 v2 模式只有三类：Direct、five-day rollout、10-day-vs-5+5 partition。它导入并构造的 wrapper 也是 `ObsWorldDirectPathModel`、`ObsWorldRolloutModel`、`ObsWorldPartitionModel`；没有导入或注册 `ObservationCorrectionCell`。

这意味着：

- 即使 `observation_correction.py` 的单元测试全部通过，任何现有 Stage2 YAML 都不会自动训练 U；
- U 不能只在 `forward` 末尾插一个 MLP。它必须决定“用哪一个真实 observation encoder/projector”“预测特征是什么”“更新后的 state 从哪一步继续 rollout”“如何同时返回 prior/posterior 供 loss/eval 使用”；
- 新 checkpoint contract 必须显式记录 correction 是否开启、reveal schedule、更新器/基线结构与 mask 语义，防止把 no-U checkpoint 误用为 U checkpoint。

### 5.3 Direct 与 Rollout 的公平性不是只改 `forecast_mode`

Direct 和 Rollout 需要保持：数据、manifest、stage1.5 checkpoint、driver、解码器、optimizer、global batch、updates、validation rule、checkpoint rule 都相同。合理的唯一差异是：

```text
Direct:  每个目标时距从相同 z0 经目标路径得到预测
Rollout: z(k+1) = F(z(k), D(k), ...)，连续把预测 state 交给下一步
```

这带来两个训练约束：

1. `horizons_per_sample` 可以为了显存只解码/监督部分 endpoint，但不能跳过内部 state 的逐步推进；否则不是完整 open-loop rollout。
2. curriculum 必须和实际优化步数匹配。当前 B64 训练的 `22,847 / 512 ≈ 44` updates/epoch，因此 200 epoch 是 8,800 updates。原 `rollout24` 到 step 12,000 才进入 12-step、step 20,000 才 full-20；机械地设 `MAX_STEPS=8800` 会在未训练 full-20 的情况下结束。

物理4 rollout YAML 没有这一份 curriculum，等价于从 step 0 full-20。技术上可跑，但是否稳定、是否和 24D 的策略公平、B64 是否适合，仍需 pilot 而不是猜测。

### 5.4 Partition 不能被当成免费的“世界模型证明”

Partition 代码会在同一路径上比较：

$$z_{10}^{direct}\quad\text{vs.}\quad z_{10}^{5+5}.$$

它还允许辅助分支从 detached rollout state 开始，以免改变主 rollout 的显存/梯度预算。这一实现选择很合理，但也要求后续报告明确它是辅助一致性 loss，而不是另一个端到端主模型。

更关键的是 schedule：现有 partition 配置在 step 5,000 才起始、10,000 step 线性 warmup；8,800 step 结束时权重仅为：

$$
\frac{8800-5000}{10000}=0.38.
$$

所以目前不应把这份配置直接称为“完整 partition 200 epoch 正式实验”。

### 5.5 训练 monitor、checkpoint 与正式 checkpoint selection 是两层事

当前训练循环已经正确做了下列事情：

- 每 1,000 optimizer step 保存普通 `checkpoint_step_*.pt`；
- 按 44 steps/epoch 保存 epoch100@4400、epoch150@6600、epoch200@8800；
- 每 1,000 step 在 `val_dev` 的固定、确定性抽取 512 样本上计算 monitor，改善时写 `checkpoint_best.pt`；
- 记录 `best_validation`、随机状态、数据位置和 provenance，可用于恢复。

但 monitor 不是完整开发集 model selection。完整选择仍要对预先规定的有限候选（例如 best、epoch100/150/200、必要的 milestone）在**完整** `val_dev` 上用同一 evaluator 重算，并写出选择决定。否则“best”只是训练中方便查看的 best，不是论文中的最终 best。

### 5.6 评估已有骨架，缺的是正式目标路径和一次性编排

现有评估路径可概括为：

```text
checkpoint + frozen config/manifest
   ├─ eval_stage2_earthnet.py      → 内部指标 / 内存 official accumulator
   ├─ predict_stage2_earthnet.py   → 完整 prediction NPZ + prediction_manifest.json
   └─ score_earthnet_prediction_dir.py
                                  → EarthNetScore.get_ENS + score_provenance.json
```

当前尚未在仓库层面完成的不是“再写一个 ENS”，而是：

1. 找到或受控生成与原始 NetCDF manifest 对应的官方 target directory；
2. 用真实 cube 验证文件命名、mask、target 字段和 scorer 看见的是同一批样本；
3. 将上述路径、hash、evaluator 版本、checkpoint contract 绑到一次 `evaluation_run.json`；
4. 批量选择 checkpoint，再汇总结果。

在 E0 做完前，严谨说法是“有 official scorer 接口”，不是“已有正式 ENS 主结果”。

### 5.7 本地缓存解决吞吐，不会自动覆盖未来评测

本地缓存是为了解决共享盘 NetCDF 读取与 CPU 预处理造成的 GPU 空转，不改变训练数据、模型或分数：

- `LOCAL_STAGE_DATA_SCOPE=train_val`：只暂存训练和验证 monitor 的 manifest 去重并集；适合当前训练，约几十到八十余 GB 量级；
- `LOCAL_STAGE_DATA_SCOPE=all`：暂存整套 EarthNet2021x，曾观测到约 219 GB；适合以后 IID/OOD/Extreme/Seasonal 评测；
- `LOCAL_STAGE_CLEANUP=manual`：保留已验证完整副本，适合 OOM 后重试；必须在不再需要时显式运行清理脚本；
- `LOCAL_STAGE_CLEANUP=auto`：正常结束、报错或可捕获中断会清理；`kill -9`/重启无法执行 trap。

因此，“本地暂存空间下限 250 GiB”是防止复制时把系统盘填满的安全阈值，不是速度限制。当前 `train_val` 缓存正确地不覆盖 IID/OOD；将来正式测试必须换 `all` 或支持任意评测 manifest 的新 scope。

## 6. Observation correction / U：缺的不是一个层，而是一整条实验合同

### 6.1 U 到底做什么

U 不是“模型更不确定时加一个数字”，而是未来某天真的拿到新观测后，利用它修正内部预测状态。正确顺序必须是：

$$
z_k^- = F(z_{k-1}^+, D_k, C_k, G, \Delta t_k),
$$

$$
\hat{x}_k = O(z_k^-),
$$

$$
r_k = E(x_k^{obs}) - E(\hat{x}_k),
$$

$$
z_k^+ = U(z_k^-, r_k, q_k, a_k).
$$

- $z_k^-$：第 $k$ 步在看到新图前的 prior；
- $\hat{x}_k$：模型先做出的预测；
- $x_k^{obs}$：第 $k$ 步后来才允许看到的、可能部分清晰的真实图；
- $r_k$：真实与预测的观测特征残差；
- $q_k$：有效可见比例；
- $a_k$：距上次有效观测过去多久；
- $z_k^+$：吸收新证据后的 posterior，随后再预测未来。

若没有揭示或 $q_k=0$，必须精确满足：

$$z_k^+=z_k^-.$$

这保证“模型没有偷偷利用未来图或未来 mask”。

### 6.2 当前已经有的低层保证

`models/dynamics/observation_correction.py` 里的 `ObservationCorrectionCell` 已实现：

- visibility-weighted residual；
- state norm、残差 MLP 和质量/陈旧度门控；
- 使用 `torch.where` 使有效质量为 0 时 state exact identity；
- staleness prior/posterior 更新；
- `ObservationCorrectionRollout` 中的 predict-then-optionally-correct 顺序。

对应单元测试已经覆盖 `q=0` identity、部分可见 support、unrevealed future feature/mask 不应改变 posterior 等低层契约。

### 6.3 当前没有的端到端环节

| 还缺的环节 | 为什么必要 | 如果跳过会怎样 |
|---|---|---|
| reveal 数据字段 | 需要把“哪一天允许看”“哪些 token 清晰”“q 是多少”从监督 mask 中分离出来 | 容易发生 future target/mask leakage，结果无效 |
| 真实 observation feature path | $E(x^{obs})$ 与 $E(\hat{x})$ 必须是兼容、可比较的表征 | 只拿像素差或随意另一个 encoder，无法证明 state correction 的语义 |
| factory/wrapper 接线 | model 必须保存 prior/posterior、reveal 与更新后的 rollout | 当前 YAML 根本不会运行 U |
| trainer 日程 | 50% no-reveal、50% one-reveal；reveal 采样未来 2--15 步；主要监督 reveal 后未来 | 模型会退化为“每步偷看真实未来”或只拟合即时重建 |
| 强在线基线 | 至少 No-update、Restart/Re-encode、Naive blend、容量匹配 VanillaFilter/GRU | 只比 no-update 不能说明 U 优于普通更新器 |
| day25/day50 evaluator | 需要共同有效 support、absolute error、paired gain、Gain-AUC、清晰度分层 | 一个平均 loss 隐藏更新是否真正改善长期未来 |
| 端到端回归测试 | q=0、unrevealed-mask invariance、时间顺序、staleness 都需在真实 batch 上验证 | 单元模块正确但训练管线仍可能泄漏或接错 |

所以 U 的合理状态是“有安全设计原型”，不是“只差训练一次”。它应在 Rollout 基础稳定之后，以单 seed `val_dev` 机制门先验证；若不能击败容量匹配的 VanillaFilter / online recurrent baseline，就不能进入主标题、摘要或主表。

## 7. 论文与结果层面的缺口

### 7.1 当前可以写什么，不能写什么

| 当前允许的表述 | 仍不允许的表述 | 原因 |
|---|---|---|
| 已建立/正在执行共享状态预测的训练路径 | shared rollout 已提高长期预测 | 还没有配对 rollout 结果 |
| Direct-P4 是严格配对的非递推控制 | Direct-P4 已是最终主模型 | 当前只有候选训练，未完整 val 选择/正式评测 |
| Stage1.5 是使用真实 $\phi$ 的预训练，Stage2 使用 neutral $\bar\phi$ | Stage2 实时采集条件感知、完全去除非线性 $\phi$ 泄漏 | EarthNet Stage2 没有兼容逐帧 $\phi$，旧 probe 也不可用 |
| 有 ENS 预测导出与 scorer 接口 | 已得到可发表 official ENS | raw target/scorer parity 尚未真实验证 |
| U 的设计和单元约束存在 | U 已被端到端训练或能校正未来 | dataset/trainer/evaluator/baseline 都未完成 |
| Partition 是候选附录机制 | Partition 证明严格半群/物理定律 | 它只能支持局部分段一致性 |

### 7.2 3 图 3 表目前各缺什么

| 论文项目 | 当前状态 | 真正缺口 |
|---|---|---|
| Figure 1：I–F–O 框图 | 可以绘制 | U 必须灰色/附录，不能画成已训练分支 |
| Table 1：主结果 | 尚无真实可填行 | 冻结 checkpoint、IID/OOD 导出、官方 scorer、同协议基线、统计 |
| Figure 2：时距曲线 | Direct 可在评估后开始生成 | 还需 matched rollout 及 tile/cube CI，才可回答递推何时受益/崩溃 |
| Table 2：driver/OOD 或 U 更新 | no-U 版可规划为 driver/OOD | 必须先锁定 driver/checkpoint，不用 test 选模型；U 版要等端到端 U |
| Figure 3：案例 | 可在 checkpoint 冻结后导出 | 需要固定样本、可追溯 prediction/target、同时展示失败案例 |
| Table 3：消融 | 目前只有设计 | 至少 Stage1 vs 1.5、Direct vs Rollout；full24/Partition 是条件性附录 |

### 7.3 Stage1.5 的证据边界

Stage1.5 不应只靠 SSL4EO 或 EuroSAT 历史数字支撑。项目真正要回答的是：相同 Stage2 预算下，Stage1.5 的初始化是否让最终预测更好、更稳，或至少收敛更快。

旧 $\phi$ probe 的 67%--71% 数字不能作为证据，原因包括未传入正确 $\phi$ / neutral 路径、Stage1 的随机 state projector、patch token 处理错误、没有严格空间隔离和 metadata-only 对照。因此之后若做 probe，应采用 tile/时间隔离的 metadata-only、state-only、metadata+state、shuffled-state 对照；但优先级仍低于实际预测消融。

## 8. 推荐的后续决策门，而不是立刻启动的任务清单

本节只给出“什么条件下才值得做下一步”，不代表现在开始实现或中断当前训练。

### Gate A：当前 Direct-P4 形成可评估候选

输入：训练完成的 `checkpoint_best.pt`、epoch100/150/200、normal checkpoints、run provenance。  
通过条件：文件完整、训练无 NaN/异常、候选集合预先锁定。  
不通过：先定位训练/数据异常，不跑新的模型分支。

### Gate B：真实评分与完整开发集闭环

输入：Gate A 候选。  
需要：E0 real-cube scorer parity、完整 `val_dev` 指标、`selected_checkpoint.json`。  
通过条件：明确 official target 路径或 adapter；评价与训练合同一致；未使用 IID/OOD 选 checkpoint。  
不通过：暂停任何“正式 ENS”或主表数字的解释。

### Gate C：决定 driver 路线

输入：完整 val 上的 Direct-P4，及选择 A/B 中所需要的 Direct24 证据。  
决策：保持预冻结 physical4 主线，或先以 validation 决定 final driver。  
通过条件：决策写入 config/provenance/论文口径；后续 rollout 不再根据 test 改 driver。

### Gate D：shared rollout 基础是否成立

输入：预算对齐的 rollout pilot 和正式 run。  
通过条件：完整 val 上不相对 matched Direct 出现明显事实性崩溃；full-20 rollout 真正被训练。  
不通过：先修 transition/curriculum/训练目标；不以 Partition/U 掩盖基础问题。

### Gate E：可选的 Partition

输入：Gate D 稳定 rollout。  
通过条件：partition gap 下降且 factual prediction 不退化。  
不通过：从主文删除或仅报告负结果。

### Gate F：U 的机制门

输入：冻结的稳定 rollout、端到端 reveal 数据与 evaluator。  
通过条件：在 `val_dev` 上优于 No-update、Restart、Naive blend、容量匹配 Filter / online recurrent，且 no-reveal 不退化。  
不通过：不运行三 seed IID/OOD 的 U 扩张，也不升级标题。

### Gate G：最后才是主表和统计

输入：锁定架构、driver、checkpoint rule 和 evaluator。  
需要：IID/OOD 每个最终系统每个 seed 的一次正式 export + score、tile-cluster paired bootstrap、固定结果 bundle。  
通过条件：所有结果可由 hash、manifest 和 score provenance 重现。

## 9. 对当前训练的准确定位

无论当前 Direct-P4 作业处于运行、恢复或完成状态，它的科学定位都相同：

```text
它解决：
  - physical4 Direct 路线能否稳定训练；
  - B64/8卡、Stage1.5 初始化、data loader、本地缓存是否可用；
  - 产生可进入完整 val 选择的候选 checkpoint。

它尚未解决：
  - 同预算 shared rollout 是否优于/不劣于 Direct；
  - physical4 是否应优于/替代 full24；
  - official ENS 是否按真实 raw NetCDF target 正确计算；
  - checkpoint 是否按完整 val_dev 选择；
  - U 是否能吸收新观测；
  - 论文主表的同协议 baseline、统计显著性和最终冻结。
```

当前训练的 `checkpoint_step_1000 ... 8000.pt`、`checkpoint_epoch100_step_4400.pt`、`checkpoint_epoch150_step_6600.pt`、`checkpoint_epoch200_step_8800.pt` 和 `checkpoint_best.pt` 是为后续 Gate A/B 准备的，不是已经完成的正式比较结果。

## 10. 以后真正需要新增或补齐的代码产物

这里列的是将来实施时应有的产物，不是本次已经修改的文件。

| 目标 | 推荐产物 | 关键约束 |
|---|---|---|
| E0 target/scorer 闭环 | 真实 cube smoke 脚本；若无现成 target，则一个 provenance-bound NetCDF-to-target adapter | 不复制无关字段；target list、源 manifest hash、转换版本必须写入 sidecar |
| E1/E2 formal eval | `scripts/run_stage2_formal_eval.sh` 或同等 launcher；`evaluation_run.json`、`selected_checkpoint.json` | 只接受冻结输入；拒绝将 Direct checkpoint 用 Rollout config 评分 |
| E3 结果汇总 | 读取 score / provenance 的 CSV、Markdown、bootstrap 输入生成器 | 显式列出 model/driver/seed/checkpoint/split/evaluator/git hash，拒绝混 protocol |
| Direct24 | 独立 `*_h200_200ep.yaml`，必要时配套测试 | 不能改基础 default YAML；stats、B64、checkpoint/val 规则与对照对齐 |
| Rollout | 独立 `rollout_<driver>_h200_200ep.yaml` | 用 44 steps/epoch 标注 curriculum，在 8,800 前到 full-20 |
| Partition | 独立 `partition_<driver>_h200_200ep.yaml` | auxiliary loss warmup 按 epoch 重标定；先 pilot |
| U | 新 wrapper/factory mode、dataset/collate reveal contract、trainer schedule、online evaluator、基线、tests | 不能把 future loss mask 当 observation mask；q=0/no-reveal 必须端到端不变 |
| 本地正式评测 | `manifest` scope 或受控 `all` cache 行为 | 不损坏 train_val reuse；IID/OOD 文件清单和 cache provenance 必须可核验 |

## 11. 结论：目前最欠缺的是什么

最欠缺的不是显存、不是“再加一次训练”，也不是再写一套泛化的世界模型名称；而是下面四条闭环：

1. **评分闭环**：真实 EarthNet NetCDF、预测导出和官方 scorer 的 target/ENS 必须在真实 cube 上对齐；
2. **选择闭环**：用完整 `val_dev` 在不看 test 的前提下选 checkpoint、选 driver（若采用路线 B）；
3. **结构闭环**：严格配对的 Direct 与真正完整训练的 Rollout 才能判断共享 transition 是否值得；
4. **更新闭环**：U 必须从单元 cell 变成不泄漏未来、优于强在线基线的完整 re-observation 实验，才可成为方法贡献。

在这四条没有补齐之前，最稳妥的论文是 no-U 的“共享转移预测状态”候选论文，而不是已经证明 correction 的世界模型论文。当前 Direct-P4 是这条路线的重要第一块砖，但还不是房子建成。

---

## 附录：本次审计不做的事

- 不修改正在运行的 Direct-P4 作业、checkpoint、缓存或日志；
- 不把 52/58 中的待填结果替成推测数字；
- 不因当前已有 `ObservationCorrectionCell` 就把 U 注册为正式模型；
- 不在没有 real-data scorer parity 前填入 ENS 主表；
- 不用 IID/OOD、Extreme 或 Seasonal 测试集选择 checkpoint、driver、loss 或 schedule；
- 不把 local cache 的性能优化误写为模型效果改善；
- 不把外部论文的跨协议数字混进本项目主表。
