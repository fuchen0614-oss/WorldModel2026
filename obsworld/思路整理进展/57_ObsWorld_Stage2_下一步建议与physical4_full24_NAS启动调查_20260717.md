# 57 ObsWorld Stage2：后续路线、评估闭环与代码优先级

> 更新日期：2026-07-17<br>
> 依据：当前 `physical4_v1` 8×H200、B64、200 epoch 本地缓存训练；Stage2-v2 代码、评估入口和研究主线的静态审计。<br>
> 边界：本文只整理决策与后续实现顺序；**不改变、不重启、不影响正在运行的训练。**

## 1. 不看完整文档也应知道的结论

1. 当前正在跑的 `Direct physical4` 是一个必要的正式候选/驱动消融行，**不是完整 ObsWorld 主张的终点**。它能回答“四个物理聚合驱动能否做好直接预测”，但不能单独证明 shared rollout，更不能证明 re-observation correction。
2. Stage2 的下一步不是另起一个模糊的 “Stage3”，而是按同一 Stage2-v2 合同依次完成：**配对 Direct24 → shared open-loop rollout →（可选）partition consistency → observation correction**。
3. 评估代码不是从零开始：已有内存评估、正式 NPZ 导出、预测文件哈希清单、checkpoint 合同核验与官方 `EarthNetScore` 目录评分入口。应当**补齐闭环和真实数据验证**，而不是推倒重写。
4. 当前 `rollout24/partition24` 的模型代码能构建和训练，但原始 YAML 的 schedule 适配 50k step；直接套用到当前 8 卡 B64 的 8,800 step / 200 epoch 预算会产生错误的训练阶段。因此 rollout/partition **尚不能只改一个 `CONFIG` 就作为正式 200 epoch 实验启动**。
5. `models/dynamics/observation_correction.py` 已实现并测试了 `q=0` exact identity、staleness 和 predict-then-update 的**独立单元模块**，但它尚未接入 `obsworld_factory.py`、Stage2 trainer、数据 reveal schedule 或正式评估。因此它目前不是可训练的最终方法分支。

一句话的项目判断是：**当前 Direct physical4 run 有价值；之后最优先是“把真实评估闭环做实 + 获得严格配对的 Direct24”，而不是马上花大量 8 卡算力跑 partition 或声称 correction 已完成。**

## 2. 现在真正完成到什么程度

| 模块 | 代码/运行状态 | 能支撑什么 | 仍缺什么 |
|---|---|---|---|
| 冻结 raw EarthNet2021x 协议 | 已有 `train_dev/val_dev`、IID/OOD/Extreme/Seasonal manifest 与 train-only stats；当前 physical4 run 已实际使用 | 开发/测试分离、物理4训练可追溯 | Direct24 要使用自己的 full24 stats，不能复用 physical4 stats |
| Direct physical4 | 当前正式 8×H200、B64、8,800 step / 200 epoch 路线已跑通 | 紧凑四维驱动的直接预测候选 | 完整 `val_dev` 选择、配对 Direct24、锁定后的测试评分 |
| Direct24 / full24 | 模型工厂、loader 合同和基础 YAML 已有 | 与 physical4 进行公平的输入表示比较 | 缺少不污染基础 YAML 的 8×H200、B64、8,800 step 派生配置和正式 run |
| 验证/最佳 checkpoint | 训练中每 1,000 step 在固定 512 个 `val_dev` 样本监控，保存 `checkpoint_best.pt` | 防止盲目只取末步 checkpoint | 这只是监控/初选；还缺完整 `val_dev` 的候选比较与明确选择记录 |
| EarthNet 评估 | `eval_stage2_earthnet.py`、`predict_stage2_earthnet.py`、`score_earthnet_prediction_dir.py`、provenance 守卫均已存在 | 内部指标、正式预测导出、避免混 checkpoint/混预测文件 | 真实 NetCDF 原始数据到官方目录评分 target 的端到端实证、统一启动器、结果汇总 |
| Rollout | `ObsWorldRolloutModel` 已真正逐五日使用上一步预测 state；无 teacher forcing | 可验证 open-loop world-model 前提 | 需要为 B64/8,800 step 制定明确 curriculum 并先做 pilot |
| Partition | `ObsWorldPartitionModel` 与 partition loss 已存在；确实比较 10 day vs 5+5 day | 作为时间可组合性的支持性证据 | B64 schedule 未适配；应等 rollout 不落后 Direct 后再投入 |
| Observation correction | 单元模块与 invariance tests 已有 | 方法设计的低层安全约束 | 没有连接到真实 observation encoder/decoder、训练、reveal batch、VanillaFilter、PredRNN-online 或结果统计 |
| 主表和统计 | 有单个 checkpoint 的导出/评分侧文件 | 单次结果可追溯 | 缺少一次性 result bundle、IID/OOD 汇总、tile bootstrap 和自动表格生成 |

因此，不能说“Stage2 只差跑完”。更准确地说：**Direct 路线已经进入真实训练；递推、更新与论文级评估仍有明确的实现和证据门槛。**

## 3. 评估代码是否需要完善？需要，但应是定向补齐

### 3.1 已有的正确基础，不应重复造轮子

现有入口已经覆盖了很多容易出错的部分：

- `eval/eval_stage2_earthnet.py`：对一个 checkpoint 在任意冻结 manifest 上算 loss、RGBN/NDVI 指标；`--official-score` 可用官方 `CubeCalculator` 做内存聚合。
- `eval/predict_stage2_earthnet.py`：导出完整 20 帧、128×128 的 EarthNet `highresdynamic` NPZ；拒绝混入不同 checkpoint 的旧预测，并写出 `prediction_manifest.json`。
- `eval/score_earthnet_prediction_dir.py`：调用官方 `EarthNetScore.get_ENS`，验证预测清单/哈希，写出 `score_provenance.json`。
- `eval/stage2_evaluation_provenance.py`：阻止把 Direct checkpoint 以 Rollout 配置、不同 driver protocol 或不同模型契约静默评估。

这些代码说明：**核心 scorer/provenance 不是空白。** 当前工作重点应是让它们成为一次真实、可复现的实验闭环。

### 3.2 正式主表前必须补的 E0--E4

| 优先级 | 应补的代码/验证 | 为什么是硬门槛 |
|---|---|---|
| E0 | 用 1--2 个真实 EarthNet2021x cube 完成 `NetCDF loader → prediction NPZ → official EarthNetScore target directory → ENS` 的实际闭环，并记录与内存 `--official-score` 的一致性 | 仓库中已有预测 NPZ 导出，但未发现把 raw `.nc` target 显式 materialize/适配为官方目录 scorer 输入的通用脚本；必须先确认已有 target NPZ 的位置，或实现受 provenance 约束的 target adapter，不能靠合成测试假设真实主表可评分 |
| E1 | 新增一个正式评估 launcher（例如 `scripts/run_stage2_formal_eval.sh`） | 将 checkpoint、config、stats、manifest、local data root、target root、prediction dir、score dir 固定到一个 `evaluation_run.json`；避免手工命令路径/统计文件配错 |
| E2 | 完整 `val_dev` 选择记录 | 当前 `checkpoint_best.pt` 基于固定 512 样本的 MAE 监控。应对有限的 milestone candidates 在完整 `val_dev` 上评估，写 `selected_checkpoint.json`，再允许任何 IID/OOD 导出；不能在 test 上挑 checkpoint |
| E3 | 结果汇总器 | 读取每个 score 的 `earthnet_score.json` 和 provenance，生成不可混 protocol 的 CSV/Markdown 行（方法、seed、checkpoint、split、ENS/MAD/OLS/EMD/SSIM、速度、Git SHA）及 tile-level bootstrap 输入 |
| E4 | 面向评测 manifest 的本地缓存 | 当前 `LOCAL_STAGE_DATA_SCOPE=train_val` 正确地只复制训练/验证文件，约 80 GB；它**不包含 IID/OOD**。正式评测前应使用 `all`，或把 local-stage helper 扩展为“显式传入任意一个/多个 eval manifest”的 scope，避免为评分又回到 NAS 读盘 |

E0 是最重要的调查/实现点。若真实官方 scorer 已经有对应原始 target NPZ，则 launcher 只需安全引用它；若没有，则需要从冻结 NetCDF manifest 生成只含官方评分所需字段的 target NPZ，并将 target 清单、源 manifest hash 和转换版本写入 provenance。两种情况都不能猜。

### 3.3 明确什么暂时不必做

- 不需要现在重写 EarthNetScore，也不需要另写一套“自定义 ENS”。
- 当前主协议是 raw EarthNet2021x；`eval/eval_greenearthnet_official.py` 的 NAS 全路径存在性扫描属于 GreenEarthNet 扩展维护项，不应抢占当前 EarthNet 主线的 P0。
- 不应在当前 physical4 run 中插入新的评估/模型代码；等其形成 checkpoint 后再做 E0--E3。

## 4. 一个关键配置事实：Rollout / Partition 不能直接沿用当前 8,800 step 配方

现有 YAML 的实际含义如下：

| 配置 | 当前 schedule | 若直接设置 `MAX_STEPS=8800` 的后果 |
|---|---|---|
| `stage2_earthnet_v2_rollout24.yaml` | rollout 长度在 step `0/2000/6000/12000/20000` 为 `2/4/8/12/20` | 8,800 结束时只训练到 **8 step** rollout，从未训练 12/20 step |
| `stage2_earthnet_v2_partition24.yaml` | 继承上表；partition 在 step 5000 开始、10,000 step 线性 warmup | 8,800 时 partition scale 仅 `(8800-5000)/10000 = 0.38`，且主 rollout 仍只有 8 step |
| `stage2_earthnet_v2_rollout_physical4.yaml` | 未配置 curriculum，因此代码默认从 step 0 就 full-20 rollout | 技术上会训练，但与 full24 的 curriculum 策略不对称，也未经过 B64 pilot |
| `stage2_earthnet_v2_partition_physical4.yaml` | full-20 rollout + 同样的 5000/10000 partition warmup | 8,800 时 partition scale 同样只有 0.38 |

这不是模型 wrapper 的错误，而是**原 YAML 与当前大 batch、200 epoch 预算没有对齐**。后续正式 rollout/partition 前必须新增派生配置，例如：

```text
stage2_earthnet_v2_rollout_<driver>_h200_200ep.yaml
stage2_earthnet_v2_partition_<driver>_h200_200ep.yaml
```

它们应以实际 `44 steps/epoch` 为共同标尺，显式记录：

- curriculum 在第几个 epoch 达到 20 step；
- partition 在第几个 epoch 开始与达到 full scale；
- 与 Direct 相同的 B64、workers、TF32、checkpoint、验证和 local-cache 参数；
- 为什么 schedule 用此时点，而不是从旧 50k-step YAML 机械复制数字。

在做出这些 config 前，**不要把当前 `rollout24` 或 `partition24` 直接当作 8卡 B64 200 epoch 正式配置启动。**

## 5. 建议的执行顺序

### 阶段 A：让当前 physical4 Direct run 自然完成

保留当前训练、日志、`run_provenance.json`、`checkpoint_step_*`、`checkpoint_best.pt` 和 local-stage 生命周期记录。当前 run 的价值是：验证数据/Stage1.5/8卡训练稳定性，并给出 physical4 Direct 的候选曲线。

完成后先做：

1. 从 1,000-step milestone 和 `checkpoint_best.pt` 中选少量候选；
2. 在完整 `val_dev` 完成 E0/E2 的评估与选择记录；
3. 此时仍不看 IID/OOD 来决定结构、driver 或 checkpoint。

### 阶段 B：严格配对的 Direct24 / full24

这是当前 Stage2 后**下一条最该投入正式算力的训练线**。

新增一个从 `stage2_earthnet_v2_direct24.yaml` 继承的 H200 派生 YAML，而非修改基础文件。它必须与 physical4 的如下项一致：

- Stage1.5 `checkpoint_step_60000.pt`；
- `train_dev` / `val_dev`、seed、B64 × 8、8,800 optimizer steps；
- validation/checkpoint/logging/runtime knobs/local-stage policy；
- 仅切换为 full24 driver 及 `conditioning_stats_v2_train_dev.json`。

然后只在 `val_dev` 决定 future rollout 使用 physical4 还是 full24。选择规则应在看 IID/OOD 前写死：如果 physical4 在完整 validation 上不劣且明显更省输入/时间，可作为最终 driver；否则 full24 是较稳妥的主 input。无论哪一个被选择，另一个保留为驱动表示消融。

### 阶段 C：共享 open-loop rollout（世界模型的最低证据）

只在阶段 B 锁定 driver 后做。先用 100--500 update B64 pilot 测显存、吞吐、full-20 loss 与 checkpoint/export；随后使用新的 H200 curriculum config 做正式 rollout。

这里的决策门是：在完整 `val_dev` 上，rollout 不能相对 matched Direct 出现明显事实性崩溃。若这个门失败，不应靠 correction 或额外模块掩盖 open-loop 基础不足。

### 阶段 D：Partition consistency（支持性机制，不抢跑）

Partition 只在 rollout 已经稳定后才值得做。它回答“共享 transition 对 10-day 与 5+5-day 是否一致”，是 world-model 的支持性证据，不是论文当前唯一方法新意。先做一 seed validation pilot，只有在不损伤 factual prediction 时再进入正式表/附录。

### 阶段 E：真正的 observation-correction 分支

这才是当前研究主线中尚未完成的中心方法；建议称为 **Stage2-R（re-observation branch）**，而不是在功能未接通前草率定义 Stage3。实现清单是：

1. 将 correction cell 接入 `ObsWorldV2Core` / 新 model wrapper 和 `obsworld_factory.py`；真实与预测 observation branch 使用同一 encoder/projector。
2. 在 dataset/collate 中提供与监督 mask 严格分离的 reveal availability、clear support `q_obs` 与 staleness；future 未 reveal mask 不得进状态。
3. 在 trainer 实现 50% no-reveal、50% exactly-one-reveal、predict-before-update、只监督 post-reveal gain 的 schedule。
4. 实现 capacity-matched VanillaFilter 与同协议 online recurrent baseline；不能只和 no-update 自己比。
5. 新增正式 re-reveal evaluator：all-cube day25/day50、共同 valid support、cube/tile-level paired gain-AUC、absolute post-reveal error、clear strata 和 Holm/cluster bootstrap。
6. 对 `q=0` identity、unrevealed-mask invariance、staleness、reveal ordering 写端到端回归测试，而不只保留当前单元测试。

先在 `val_dev` 做 one-seed mechanism gate；若 proposed correction 不优于 VanillaFilter 或线上 recurrent baseline，就收缩/停止该强主张，而不是直接跑三 seed IID/OOD。

### 阶段 F：锁定后才生成主实验表

只有在阶段 B--E 的结构和 checkpoint 规则锁定后，才进行：

- IID/OOD：每个最终系统、每个 seed 的一次正式 prediction export + official ENS；
- tile-cluster paired bootstrap 与主表汇总；
- Extreme/Seasonal：只作为补充压力轨道；
- 参数、吞吐、显存和失败案例：附录/效率表。

所以“当前 physical4 训练完成后能否直接生成主实验表”的答案是：**不能直接生成完整主表；它最多生成 Direct physical4 的一行候选结果。完整主表至少还需要配对 Direct24、锁定后的 rollout，以及若保留核心 thesis 则需要 correction 的在线实验。**

## 6. 推荐的代码任务单（按实际优先级）

| 序号 | 工作项 | 产物/验收 | 何时做 |
|---|---|---|---|
| C1 | E0：真实 cube 的官方 scorer target 路径审计与 parity test | `formal_eval_smoke.json`、预测/target/score provenance，明确 target NPZ 来源或转换器 | 当前 run 结束后第一件事 |
| C2 | E1/E2：正式评估 launcher + 完整 `val_dev` checkpoint selector | `evaluation_run.json`、`selected_checkpoint.json`；无 test 参与选择 | 与 C1 一起 |
| C3 | Direct24 H200 paired config + 100--500 step pilot | 配置契约测试、显存/吞吐/loss、同 physical4 的保存策略 | C1/C2 通过后 |
| C4 | Direct24 200 epoch | 完整 Direct A/C validation comparison | C3 通过后 |
| C5 | eval local staging 扩展为 manifest scope | IID/OOD 可以按冻结 manifest 本机缓存，而非全量 NAS 读取 | 在第一次正式 test 前 |
| C6 | Rollout H200 curriculum config + pilot | full-20 rollout 真正被训练、schedule/checkpoint provenance 正确 | B 的 driver 选择后 |
| C7 | Partition H200 config + one-seed gate | 只在 rollout 稳定时执行 | C6 通过后 |
| C8 | 端到端 observation-correction / online evaluator | R020--R023 one-seed val decision evidence | C6 成立后 |
| C9 | result aggregator / bootstrap / table renderer | 可审计 IID/OOD 主表 | 最终配置锁定后 |

## 7. 明确的 stop rules，防止继续堆算力

- Direct24 与 physical4 的完整 validation 比较没有清晰差异：选更简单/更快者，并把另一个作为消融；不要无限扩大 driver 维度。
- Rollout 在 validation 上相对 Direct 明显崩溃：先修 shared-transition/curriculum，不启动 partition 或 correction 大规模训练。
- Partition 不能保持/改善 factual prediction：保留为负结果或从主文删除。
- correction 不胜过 capacity-matched VanillaFilter 或 online recurrent baseline：不能称它是方法创新；停止三 seed test 扩张。
- 真实正式 scorer 与内存评估不一致：先修 E0 的数据/target/mask 适配，任何 ENS 数字都不进入表。

## 8. 本次审计与旧版本 57 的差异

此前文档把 local staging 容量、选择性暂存、GreenEarthNet manifest 扫描与 Direct24 配置都列为同级近期问题。现在应更新为：

- local staging 已支持 `manual|auto` cleanup、`all|train_val` scope、空 GPU gate、250 GB free-space gate；当前 `train_val` cache 是正确的训练优化，而不是故障。
- GreenEarthNet `verify_exists=True` 是独立扩展维护项，不是当前 raw EarthNet2021x 主表阻塞项。
- 当前最实质的新增发现是：**正式评估的真实 target 目录闭环尚未被 repository-level real-data test 证明；rollout/partition 的 schedule 也未适配 8,800 step。**
- 因而后续不应把“修 NAS/I/O”当作主要研究工作；应把工程重点转向 E0--E4 与公平的 Direct/rollout/correction evidence chain。

## 9. 本文不做的事

- 不把当前 physical4 训练中断、替换 checkpoint 或改变其配置；
- 不把未完成的 observation correction 描述为已训练方法；
- 不用 IID/OOD 选 driver、loss、checkpoint 或 schedule；
- 不把 GreenEarthNet、`*_chopped`、外部论文数字或不同 raw split 混进 EarthNet 主表；
- 不在没有 C1 real-score 证据前报告“正式 ENS 主结果”。
