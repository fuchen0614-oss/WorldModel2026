# A03 TerraState 关键实验结果与决策总账

**文档状态**：E0 v3 封账版（由 `render_a03_v3.py` 从 v3 工件渲染，非手工抄录）  
**实验编号**：E0（11,904 与 14,880 同协议对照评测）  
**v3 验收判定**：ACCEPTED（检查 732 项，失败 0 项）  
**历史复现**：57/57 个正式指标通过，其中逐位相同 57 个（仅 11,904 侧复现历史参考；14,880 侧无历史参考可比）  
**渲染时间（UTC）**：2026-08-20T14:33:48.362754Z  
**GPU 执行节点**：csy-zg01-gnode39；**CPU 封账节点**：csy-zg01-gnode68  
**前一版快照**：`A03_snapshot_before_v3_correction.md`（与被替换的 v2 正文逐字节一致，另存 `.sha256` 旁证）

> 本文档记录当前证据链所能支持的结论。它不是「最终结论」：后续实验（Candidate C、Q4）可能改变其中的解释部分。

---


## 零、v3 相对 v2 修正了什么

v2 正文中的下列内容经一手工件核对为错误或无来源，v3 全部改正。改正依据写在括号内。

1. **历史复现指标个数**：v2 写 65/65。冻结参考 `historical_11904_reference.json` 的正式指标键实为 **57 个**（另有 8 个 `_` 前缀元数据键必须排除在计数之外）。v3 记 57/57。
2. **Q2 对照表数字无来源**：v2 表中 0.556762 / 0.556617 / 0.556546 / 0.484868 / 0.012454 / 0.013196 / 0.012587 / 0.012732 等值，在六份一手结果 JSON 的全部浮点数中以 |Δ|<5e-7 搜索命中集合为空（验收器 gate E8 程序化确证）。v3 的 Q2 全部数值改由脚本从 raw JSON 读出。
3. **Q1 分层与 horizon 表数字错误**：v2 的 OOD-t 分层（Forest 0.629023 等）与 horizon（0-5 天 0.113876 等）与一手结果不符。v3 见 §3.1，全部重新读出。
4. **模型状态同一性被写反**：v2 称 11,904 与 14,880「模型张量值 SHA 一致」。一手证据只支持：**verified 14,880 与历史 14,880** 两者的 255 个模型张量逐值相同（`value_sha=aa98fbd2fa302727`，max abs diff = 0）。11,904 与 14,880 是不同的模型状态，其证据是二者在同一 split 上的评测结果本身就不同（见 §3.1）。
5. **`<待补充>` 占位符**：v2 的模型状态 SHA、batch_size、lr 等处留有占位符。v3 的训练超参全部取自 `parameter_audit.json`（49 行，全部 consistent），见 §2.3。
6. **时间线含无法证明的时刻**：v2 写有 guardian 启动/退出时刻与「总耗时约 20 分钟」。v3 只保留日志与文件系统可证的时刻，并显式声明哪些量不可证（见 §2.4）。
7. **SHA 一律 `—` 占位**：v2 的工件清单 SHA 列全部为 `—`。v3 见 §5，全部为实测值。
8. **「本文档为当前最终版本」**：改为「当前证据链下的封账版」，不使用「最终」。

---


## 一、实验目标与协议


### 1.1 要回答的问题

1. 在完全相同的协议下，14,880 步与 11,904 步的表现差异有多大、方向如何？
2. 11,904 步的历史评测数字能否在本次环境与协议下复现？
3. 14,880 步能否作为后续实验的 anchor checkpoint？

本轮**没有**对两个 checkpoint 之间的差异做统计显著性检验，因此下文不出现「显著/不显著」「属于噪声」一类表述。（Q2 与 Q3 内部各自的 bootstrap 置信区间是**协议自带**的，针对的是「状态是否承载」「响应是否保真」，不是针对 11,904 与 14,880 的差异。）

### 1.2 评测协议与冻结输入

| 协议 | 冻结清单 | 文件 SHA-256 | 目标数 |
|---|---|---|---|
| Q1/Q2 Validation | `val_chopped.manifest.json` | `d9bd91d6e2aafbf66b38afca7576516823fc710b6cc3ca44ea25d2e31152bf8e` | 952 |
| Q1/Q2 OOD-t | `greenearthnet_oodt_chopped_manifest.json` | `58c8d64897193e9cffff5bc6c8524909707ebae5376b5d4dee68597ef08e1e49` | 1904 |
| Q3 极端态审计 | `extreme_audit_oodt_v1/`（冻结协议目录） | MANIFEST.SHA256 = `95f50ad30c5263db809a645e7cf22e94435586a35ce1a6c9a67728d64616e9f0` | 84 对 |

**ground truth 归属**：Q3 协议冻结于 `2026-07-26T00:00:00Z`，最早一次评测启动于 `2026-08-20T03:27:18Z`，冻结早于评测 **25.14 天**。阈值与配对数只从冻结协议文件读入，不由本轮模型输出反推。

Q3 阈值（冻结自训练集异常分布，原样施加于 OOD-t）：strict hot=1.211718, dry=1.094944；broad hot=0.845641, dry=0.820556。

Q3 协议计数（取自 `protocol.json`，非模型输出）：n_strict=36，n_broad=84，n_primary=84，n_control_unique=45。

协议冻结时的仓库状态：git_commit=`83e62e9d9e58a4705f0e7dcec74df97a1acaad21`，git_dirty=否，seed=42，n_train_used=22749，n_oodt_valid=1704。

### 1.3 evaluator 身份

- `eval/eval_b4_exclusive_contract.py`：实测 SHA-256 `c6759dec60ede433f99a97b1ba3191d9427210cd907a08d6d8776dfb8efec9b4`（与冻结 manifest 记录一致）
- `eval/extreme_state_audit.py`：实测 SHA-256 `10ef9e40f1f668a3b12c34e70accefae98ca4c419c7f122829f5531c5cd9f838`（与冻结 manifest 记录一致）

- Q1/Q2 结果 JSON 自带 evaluator commit：`repo:c950303+official:a0329636631371a4aaa9a95c75ed0a37d27b8c4f`（四份一致）
- Q3 结果 JSON **不记录** evaluator commit。Q3 结果 JSON 的 schema 不记录 evaluator commit；Q3 评测脚本身份改由 eval/extreme_state_audit.py 的实测 SHA-256 与冻结 manifest 记录值比对来确定

---


## 二、三份 checkpoint、继续训练与执行记录


### 2.1 三份 checkpoint 的身份与谱系

本实验涉及三份 checkpoint。**三者文件身份互不相同**，必须分别称呼：

| 项 | 边界 11,904 | verified 14,880 | 历史 14,880 |
|---|---|---|---|
| 逻辑 ID | `terrastate/v2/legacy-boundary11904@v1` | `terrastate/v2/verified-resume14880@v1` | `terrastate/v2/historical-full14880@v1` |
| 步数 | 11904 | 14880 | 14880 |
| 文件字节数 | 37,972,401 | 44,302,057 | 44,300,969 |
| 文件权限 | 0o444 | 0o444 | 0o444 |
| 文件 SHA-256 | `644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd` | `a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f` | `99f15a35fb9a356901c995bb0f48280a4da236f6970d0dd06343a28857fe2b8b` |
| 内容寻址路径 | `objects/sha256/64/644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd.pt` | `objects/sha256/a5/a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f.pt` | `objects/sha256/99/99f15a35fb9a356901c995bb0f48280a4da236f6970d0dd06343a28857fe2b8b.pt` |
| 文件内记录的 stage | 2 | 3 | 3 |
| epoch | 31 | 40 | 40 |
| 父节点 | 无（非 resume 产物） | `terrastate/v2/legacy-boundary11904@v1` | 无（非 resume 产物） |

**关于「模型状态相同」这一说法的准确边界**：

- 已验明：**verified 14,880 与历史 14,880** 的 255 个模型张量逐值相同 —— `value_sha hist=aa98fbd2fa302727 resume=aa98fbd2fa302727 keys_equal=True max_abs_diff=0.000e+00 over 255 tensors`。
- 同时成立：二者**文件 SHA-256 不同**（`a5d2a0cc28ad7c01…` vs `99f15a35fb9a3569…`），因为 verified 版另外携带 B5 谱系块与本次运行的 args/时间戳。「权重逐字节相同」与「文件身份独立」两句都为真，不得混为一谈。
- **11,904 与 14,880 不是同一模型状态**。11,904 的 `b4_state_sha256` = `aba100c138119bc0fc4412082412596dcf31090410643aa0736b5705b04feaa7`（64 位十六进制），与上面 16 位的 `value_sha` 是两套互不可比的摘要方案。二者不同的正向证据见 §3.1：同一 split 上评测结果本身就不同。

- 边界 11,904 的保存时机说明（取自 registry provenance_notes）：Written by the original run at step 11904 BEFORE the stage 2->3 switch, so the recorded stage is 2 while the next scheduled update belongs to stage 3.
- 边界 11,904 携带的续训状态：Complete resume state: optimizer_state_dict (2 groups / 30 Adam entries), scheduler_state_dict (last_epoch=11904), scaler record (FP32, disabled), rng_state + rng_states_by_rank (8 ranks), q_freeze.

**别名**：`terrastate/v2/verified-resume14880@v1` 由 `terrastate/v2/default-training-anchor` 指向（alias 文件 SHA-256 `fc57cbbb0ae00f3371b94bb846aa36160a1db74e8a3706220b75e053c8370b8c`，set_at=2026-08-18T07:52:30.155074+00:00）。
**registry**：`weight_registry.json`，revision `a7fd2763935a26d1`，schema `terrastate_weight_registry_v1`，登记 7 件工件，实测 SHA-256 `a087670624e367d8c64d2b23ae6a2452b8dab07aac3ae4fc014765bc91a74907`。

### 2.2 11,904 → 14,880 的继续训练

| 项 | 值 | 来源 |
|---|---|---|
| 续训方式 | exact-resume（resumed=是） | m9_acceptance_report.json |
| 父 checkpoint | step=11904, epoch=31, micro_in_epoch=372 | 同上 |
| 父文件内记录 stage | 2 | 同上 |
| resume 实际施加 stage | 3 | 同上 |
| 优化器更新次数 | 2976（= 14880 − 11904） | parameter_audit.json |
| 覆盖 epoch | 32..39 inclusive (start_epoch index 31 fully consumed)（剩余 8.0 个 epoch） | 同上 |
| 每 epoch 更新数 | 372 | 同上 |
| 边界公式 | int(0.80 * 14880) == 11904 | 同上 |
| 数据顺序恢复 | exact: DistributedSampler(seed, epoch) fully determines the order | m9_acceptance_report.json |
| M9 验收 | accepted=是，31/31 项检查通过 | 同上 |
| 终点 | step=14880, stage=3, best_val=0.31287648 | 同上 |

**stage 记录的已知歧义**：`stage_at_11904 = 3`，而边界文件内记录的是 `2`。原因：train.log: '[boundary80] forced checkpoint saved at step 11904' immediately followed by '[stage] 2 -> 3 at step 11904; trainable_q=12'。要求：the first post-resume update (#11905) must run in stage 3 with exactly the 12 core.blocks.2.* q tensors trainable, and the run must NOT re-save checkpoint_boundary80.pt。本文如实保留这一差异，不做抹平。

**warm-start / teacher / q_projector 身份核对**（`state_sha_check.json`）：

- 全部匹配 all_match=是；teacher_load_exact=是（missing=0, unexpected=0）
- warm_start_exact=是（missing=0, unexpected=0），来源架构 ObsWorldB4Exclusive
- teacher：ObsWorldB4，q keys=223，SHA-256 `bbe2c3ee6de540ae6eabeb7798f331388112ad370dbcae9533187344f2f8a302`
- student_init：ObsWorldB4Exclusive，SHA-256 `488052d97c7d1c8a2e805d9838f344daef7ad02e5f185d3025031a5f1c026338`
- q_projector 初始化 SHA-256 `da978b0243c8dae070d8a9a3db8e09b889ba9e4c91b36724370c5d747593243d`

### 2.3 训练超参（全部有值，无占位符）

下表取自 `parameter_audit.json`（SHA-256 `24465586b2b3bd8f2267db43cefc90c42e38d5e6377eb5ac645f9126a8804cc5`，49 行，all_consistent=是，inconsistent_parameters=[]）。「见证」列表示该值在 checkpoint / runbook / train.log 中各自是否独立出现。

| 参数 | 冻结值 | 见证 |
|---|---|---|
| `world_size` | `8` | checkpoint + runbook + train.log |
| `per_gpu_batch` | `8` | checkpoint + runbook + train.log |
| `accum` | `1` | checkpoint + runbook + train.log |
| `global_batch` | `64` | checkpoint + runbook + train.log |
| `updates_per_epoch` | `372` | train.log |
| `max_epochs` | `40` | checkpoint + runbook |
| `max_steps` | `0` | checkpoint + runbook |
| `total_steps` | `14880` | checkpoint + train.log |
| `boundary80` | `11904` | train.log |
| `branch_lr` | `3e-05` | checkpoint + runbook |
| `q_lr_scale` | `0.033` | checkpoint + runbook |
| `lr_warmup_steps` | `300` | checkpoint + runbook |
| `weight_decay` | `0.0` | checkpoint + runbook |
| `grad_clip` | `1.0` | checkpoint + runbook |
| `unfreeze_q_prefixes` | `core.blocks.2.` | checkpoint + runbook |
| `alpha` | `1.0` | checkpoint + runbook |
| `loss_weights.gt` | `1.0` | checkpoint + runbook |
| `loss_weights.kd` | `0.5` | checkpoint + runbook |
| `lambda_state@11904` | `0.01` | checkpoint + runbook |
| `state_dim` | `256` | checkpoint + runbook |
| `seed` | `42` | checkpoint + runbook |
| `deterministic` | `False` | checkpoint + runbook |
| `device` | `cuda` | checkpoint + runbook |
| `num_workers` | `8` | checkpoint |
| `val_interval` | `1000` | checkpoint + runbook |
| `ckpt_interval` | `2000` | checkpoint + runbook |
| `log_interval` | `50` | checkpoint + runbook |
| `cache_fail_closed_gb` | `4.0` | checkpoint |
| `train_cache_cubes` | `23816` | train.log |
| `val_cache_cubes` | `952` | train.log |
| `cache_horizon_h` | `20` | train.log |
| `resume.step` | `11904` | checkpoint + train.log |
| `resume.epoch` | `31` | checkpoint |
| `resume.micro_in_epoch` | `372` | checkpoint |
| `resume.stage` | `2` | checkpoint |
| `resume.q_freeze.trainable_q` | `[]` | checkpoint |
| `resume.best_val` | `0.31334985432787643` | checkpoint |

训练侧数据指纹（**与评测侧冻结清单是不同文件，不得互换引用**）：

- `sha.train_manifest_sha256` = `17c645d92e9dd4c38ce5bf14a412115c5f6622109cff3c19118b098e604b2554`
- `sha.val_manifest_sha256` = `555d44c0d59ab3902cf7d929ca86ce8bf4e3ce7cfda66c1c72b45a2ed3fd76c9`
- `sha.train_cache_sha256` = `2a14f0a4c3653f38ee52155d38c38f76d01cc234a5fb301a3dfb512ee0101a66`
- `sha.val_cache_sha256` = `2a14f0a4c3653f38ee52155d38c38f76d01cc234a5fb301a3dfb512ee0101a66`
- `sha.q_projector_init_sha256` = `da978b0243c8dae070d8a9a3db8e09b889ba9e4c91b36724370c5d747593243d`

> 训练用 train/val manifest 与评测用 val_952 / oodt_1904 冻结清单是不同文件，A03 中不得互相替代。验收器 gate F6 断言训练侧与评测侧 SHA 集合交集为空。

### 2.4 执行记录与可证时间线

六份正式作业与其物理 GPU 的对应关系，**唯一权威来源是 launch shard**；逻辑作业名（gpu0…gpu5）与物理 GPU 编号无对应关系，不得由名字推断。

| 逻辑作业名 | 类型 | split | checkpoint | 物理 GPU | PID | exit | 启动（UTC） |
|---|---|---|---|---|---|---|---|
| `gpu0_v14880_val_q1q2` | q1q2 | val | verified14880 | 5 | 3859325 | 0 | 2026-08-20T03:27:18Z |
| `gpu1_v14880_oodt_q1q2` | q1q2 | oodt | verified14880 | 2 | 3859216 | 0 | 2026-08-20T03:40:08Z |
| `gpu2_v14880_oodt_q3` | q3 | oodt | verified14880 | 5 | 3933274 | 0 | 2026-08-20T03:46:39Z |
| `gpu3_legacy11904_val_q1q2` | q1q2 | val | boundary11904 | 6 | 3859405 | 0 | 2026-08-20T03:40:23Z |
| `gpu4_legacy11904_oodt_q1q2` | q1q2 | oodt | boundary11904 | 4 | 3859304 | 0 | 2026-08-20T04:10:01Z |
| `gpu5_legacy11904_oodt_q3` | q3 | oodt | boundary11904 | 6 | 3949454 | 0 | 2026-08-20T03:57:49Z |

实际使用的物理 GPU：[2, 4, 5, 6]。

**可证时间线**（每一行都有指定证据；两类事件性质不同，不得相减当作单作业耗时）：

| 时刻（UTC） | 事件 | 作业 | 证据 |
|---|---|---|---|
| 2026-08-20T03:27:18Z | job_started | `gpu0_v14880_val_q1q2` | launch_record_shard_pgpu5.json 的 started_utc 字段 |
| 2026-08-20T03:29:45.156176Z | result_json_written | `gpu0_v14880_val_q1q2` | runs/gpu0_v14880_val_q1q2/state_contract_exclusive.json 的文件 mtime |
| 2026-08-20T03:40:08Z | job_started | `gpu1_v14880_oodt_q1q2` | launch_record_shard_pgpu2.json 的 started_utc 字段 |
| 2026-08-20T03:40:23Z | job_started | `gpu3_legacy11904_val_q1q2` | launch_record_shard_pgpu6.json 的 started_utc 字段 |
| 2026-08-20T03:42:35.610052Z | result_json_written | `gpu1_v14880_oodt_q1q2` | runs/gpu1_v14880_oodt_q1q2/state_contract_exclusive.json 的文件 mtime |
| 2026-08-20T03:42:50.566358Z | result_json_written | `gpu3_legacy11904_val_q1q2` | runs/gpu3_legacy11904_val_q1q2/state_contract_exclusive.json 的文件 mtime |
| 2026-08-20T03:46:39Z | job_started | `gpu2_v14880_oodt_q3` | launch_record_shard_pgpu5.json 的 started_utc 字段 |
| 2026-08-20T03:49:06.048221Z | result_json_written | `gpu2_v14880_oodt_q3` | runs/gpu2_v14880_oodt_q3/extreme_state_audit.json 的文件 mtime |
| 2026-08-20T03:57:49Z | job_started | `gpu5_legacy11904_oodt_q3` | launch_record_shard_pgpu6.json 的 started_utc 字段 |
| 2026-08-20T04:00:16.708652Z | result_json_written | `gpu5_legacy11904_oodt_q3` | runs/gpu5_legacy11904_oodt_q3/extreme_state_audit.json 的文件 mtime |
| 2026-08-20T04:10:01Z | job_started | `gpu4_legacy11904_oodt_q1q2` | launch_record_shard_pgpu4.json 的 started_utc 字段 |
| 2026-08-20T04:12:28.251210Z | result_json_written | `gpu4_legacy11904_oodt_q1q2` | runs/gpu4_legacy11904_oodt_q1q2/state_contract_exclusive.json 的文件 mtime |

- 最早启动：2026-08-20T03:27:18Z；最后一份结果落盘：2026-08-20T04:12:28.251210Z
- 最早启动 2026-08-20T03:27:18Z 至最后一份结果落盘 2026-08-20T04:12:28.251210Z 之间的跨度可由文件系统证明，但该跨度包含 GPU 共享等待，不等于计算耗时

**明确不可证的量**（因此本文不写）：
- 单个作业的精确 wall-clock 时长（runner 日志未记录逐作业结束时刻）
- 六作业总耗时的精确值（存在 GPU 共享与排队，不能由首启到末写直接相减）

---


## 三、结果

下文所有数值由渲染脚本从 `e0_comparison_11904_vs_14880_v3.json` 读出，该文件本身由验收器从六份一手结果 JSON 生成。**Δ 的约定：delta = 14880 - 11904**。

### 3.1 Q1 预测精度


#### Validation（952 targets，冻结清单 SHA-256 `d9bd91d6e2aafbf6…`）

| 指标 | 11,904 | 14,880 | Δ |
|---|---|---|---|
| R² | 0.497322 | 0.497094 | -0.000228 |
| RMSE | 0.157288 | 0.157334 | +4.583e-05 |
| NSE | -0.154755 | -0.155997 | -0.001243 |
| |bias| | 0.099720 | 0.099729 | +9.007e-06 |

**Validation — 预测步长分解（RMSE）**

| Horizon | 11,904 | 14,880 | Δ |
|---|---|---|---|
| 0–5 天 | 0.090905 | 0.090860 | -4.482e-05 |
| 5–10 天 | 0.133933 | 0.133826 | -0.000107 |
| 10–15 天 | 0.166326 | 0.166270 | -5.584e-05 |
| 15–20 天 | 0.174422 | 0.174658 | +0.000236 |
| rmse25 | 0.090905 | 0.090860 | -4.482e-05 |

**Validation — 植被分层**

| 分层 | 指标 | 11,904 | 14,880 | Δ |
|---|---|---|---|---|
| Forest | R² | 0.466217 | 0.465644 | -0.000573 |
| Forest | RMSE | 0.152815 | 0.152772 | -4.295e-05 |
| Forest | NSE | -0.178001 | -0.178590 | -0.000589 |
| Forest | |bias| | 0.094069 | 0.093960 | -0.000109 |
| Shrub | R² | 0.451020 | 0.451080 | +6.036e-05 |
| Shrub | RMSE | 0.143278 | 0.143370 | +9.193e-05 |
| Shrub | NSE | -0.212657 | -0.214805 | -0.002147 |
| Shrub | |bias| | 0.090878 | 0.090951 | +7.310e-05 |
| Grass | R² | 0.516876 | 0.516679 | -0.000197 |
| Grass | RMSE | 0.153771 | 0.153832 | +6.113e-05 |
| Grass | NSE | -0.120028 | -0.121131 | -0.001103 |
| Grass | |bias| | 0.096887 | 0.096909 | +2.205e-05 |
| Crop | R² | 0.555176 | 0.554972 | -0.000204 |
| Crop | RMSE | 0.179290 | 0.179363 | +7.321e-05 |
| Crop | NSE | -0.111549 | -0.112719 | -0.001170 |
| Crop | |bias| | 0.117044 | 0.117094 | +4.957e-05 |

#### OOD-t（1904 targets，冻结清单 SHA-256 `58c8d64897193e9c…`）

| 指标 | 11,904 | 14,880 | Δ |
|---|---|---|---|
| R² | 0.569349 | 0.569278 | -7.121e-05 |
| RMSE | 0.150594 | 0.150627 | +3.300e-05 |
| NSE | -0.098656 | -0.099753 | -0.001097 |
| |bias| | 0.100829 | 0.100810 | -1.927e-05 |

**OOD-t — 预测步长分解（RMSE）**

| Horizon | 11,904 | 14,880 | Δ |
|---|---|---|---|
| 0–5 天 | 0.082050 | 0.082097 | +4.768e-05 |
| 5–10 天 | 0.129362 | 0.129295 | -6.668e-05 |
| 10–15 天 | 0.160206 | 0.160142 | -6.407e-05 |
| 15–20 天 | 0.167954 | 0.168123 | +0.000169 |
| rmse25 | 0.082050 | 0.082097 | +4.768e-05 |

**OOD-t — 植被分层**

| 分层 | 指标 | 11,904 | 14,880 | Δ |
|---|---|---|---|---|
| Forest | R² | 0.552058 | 0.551455 | -0.000603 |
| Forest | RMSE | 0.147263 | 0.147244 | -1.881e-05 |
| Forest | NSE | -0.098031 | -0.098756 | -0.000724 |
| Forest | |bias| | 0.096320 | 0.096211 | -0.000109 |
| Shrub | R² | 0.556196 | 0.555644 | -0.000552 |
| Shrub | RMSE | 0.147816 | 0.148010 | +0.000194 |
| Shrub | NSE | -0.196695 | -0.200338 | -0.003643 |
| Shrub | |bias| | 0.101088 | 0.101221 | +0.000134 |
| Grass | R² | 0.584470 | 0.584881 | +0.000411 |
| Grass | RMSE | 0.145102 | 0.145107 | +5.217e-06 |
| Grass | NSE | -0.048830 | -0.049476 | -0.000646 |
| Grass | |bias| | 0.096849 | 0.096798 | -5.052e-05 |
| Crop | R² | 0.584673 | 0.585132 | +0.000459 |
| Crop | RMSE | 0.162196 | 0.162147 | -4.859e-05 |
| Crop | NSE | -0.057479 | -0.057156 | +0.000322 |
| Crop | |bias| | 0.109059 | 0.109008 | -5.101e-05 |

**读法**：两个 checkpoint 在 Q1 上的差异出现在小数点后第四位及更小的量级，方向在不同 split、不同分层、不同预测步长上并不一致（既有 Δ<0 也有 Δ>0）。本轮未对这些差异做显著性检验，因此只描述量级与方向，不做「等价」「无差别」一类判断。

**同时，这些非零差异本身就是 11,904 与 14,880 属于不同模型状态的正向证据** —— 若两者权重相同，同一冻结清单、同一 evaluator 下的结果应当逐位一致。

### 3.2 Q2 状态承载能力


#### Validation

| 臂 | 指标 | 11,904 | 14,880 | Δ |
|---|---|---|---|---|
| full | R² | 0.497322 | 0.497094 | -0.000228 |
| full | RMSE | 0.157288 | 0.157334 | +4.583e-05 |
| α₀（context-prior） | R² | 0.486108 | 0.484831 | -0.001276 |
| α₀（context-prior） | RMSE | 0.171013 | 0.171148 | +0.000135 |
| T-identity | R² | 0.485416 | 0.484090 | -0.001326 |
| T-identity | RMSE | 0.261018 | 0.261570 | +0.000552 |

| 官方 Δ | 11,904 | 14,880 | Δ |
|---|---|---|---|
| R²(full) − R²(α₀) | 0.011214 | 0.012262 | +0.001048 |
| R²(full) − R²(T-identity) | 0.011906 | 0.013004 | +0.001098 |

**bootstrap 与配对统计**（该 CI 针对「状态是否承载」，不是针对两 checkpoint 之差）

| 家族 | 量 | 11,904 | 14,880 | Δ |
|---|---|---|---|---|
| closure_cut_α₀ | bootstrap95 mean | 0.016163 | 0.017161 | +0.000999 |
| closure_cut_α₀ | bootstrap95 ci_low | 0.006432 | 0.007362 | +0.000929 |
| closure_cut_α₀ | bootstrap95 ci_high | 0.025902 | 0.026963 | +0.001060 |
| closure_cut_α₀ | frac_pos | 0.580645 | 0.580645 | +0.000000 |
| closure_cut_α₀ | n | 589 | 589 | +0 |
| closure_cut_α₀ | significant>0 | 是 | 是 | — |
| closure_cut_α₀ | paired n | 589 | 589 | +0 |
| closure_cut_α₀ | win | 342 | 342 | +0 |
| closure_cut_α₀ | tie | 0 | 0 | +0 |
| closure_cut_α₀ | loss | 247 | 247 | +0 |
| closure_cut_α₀ | paired mean ΔR² | 0.016163 | 0.017161 | +0.000999 |
| closure_cut_α₀ | paired median ΔR² | 0.014943 | 0.015203 | +0.000260 |
| transition_identity | bootstrap95 mean | 0.017417 | 0.018379 | +0.000962 |
| transition_identity | bootstrap95 ci_low | 0.007825 | 0.008767 | +0.000942 |
| transition_identity | bootstrap95 ci_high | 0.026961 | 0.027928 | +0.000967 |
| transition_identity | frac_pos | 0.594228 | 0.595925 | +0.001698 |
| transition_identity | n | 589 | 589 | +0 |
| transition_identity | significant>0 | 是 | 是 | — |
| transition_identity | paired n | 589 | 589 | +0 |
| transition_identity | win | 350 | 351 | +1 |
| transition_identity | tie | 0 | 0 | +0 |
| transition_identity | loss | 239 | 238 | -1 |
| transition_identity | paired mean ΔR² | 0.017417 | 0.018379 | +0.000962 |
| transition_identity | paired median ΔR² | 0.016288 | 0.016880 | +0.000591 |

| 判定项 | 11,904 | 14,880 |
|---|---|---|
| ΔR² floor | 0.005000 | 0.005000 |
| floor 通过 | 是 | 是 |
| transition_margin_clean | 否 | 否 |
| verdict | LOAD_BEARING | LOAD_BEARING |

| 不变量 | 11,904 | 14,880 |
|---|---|---|
| `alpha0_pred_equals_context_prior` | 是 | 是 |
| `T_identity_is_state_identity` | 是 | 是 |
| `live_weights_restored` | 是 | 是 |

#### OOD-t

| 臂 | 指标 | 11,904 | 14,880 | Δ |
|---|---|---|---|---|
| full | R² | 0.569349 | 0.569278 | -7.121e-05 |
| full | RMSE | 0.150594 | 0.150627 | +3.300e-05 |
| α₀（context-prior） | R² | 0.549377 | 0.548946 | -0.000431 |
| α₀（context-prior） | RMSE | 0.165188 | 0.165218 | +3.012e-05 |
| T-identity | R² | 0.547664 | 0.547335 | -0.000329 |
| T-identity | RMSE | 0.258316 | 0.258746 | +0.000430 |

| 官方 Δ | 11,904 | 14,880 | Δ |
|---|---|---|---|
| R²(full) − R²(α₀) | 0.019972 | 0.020332 | +0.000360 |
| R²(full) − R²(T-identity) | 0.021685 | 0.021943 | +0.000258 |

**bootstrap 与配对统计**（该 CI 针对「状态是否承载」，不是针对两 checkpoint 之差）

| 家族 | 量 | 11,904 | 14,880 | Δ |
|---|---|---|---|---|
| closure_cut_α₀ | bootstrap95 mean | 0.021998 | 0.022248 | +0.000250 |
| closure_cut_α₀ | bootstrap95 ci_low | 0.014220 | 0.014365 | +0.000146 |
| closure_cut_α₀ | bootstrap95 ci_high | 0.030176 | 0.030492 | +0.000316 |
| closure_cut_α₀ | frac_pos | 0.569185 | 0.572130 | +0.002944 |
| closure_cut_α₀ | n | 1019 | 1019 | +0 |
| closure_cut_α₀ | significant>0 | 是 | 是 | — |
| closure_cut_α₀ | paired n | 1019 | 1019 | +0 |
| closure_cut_α₀ | win | 580 | 583 | +3 |
| closure_cut_α₀ | tie | 0 | 0 | +0 |
| closure_cut_α₀ | loss | 439 | 436 | -3 |
| closure_cut_α₀ | paired mean ΔR² | 0.021998 | 0.022248 | +0.000250 |
| closure_cut_α₀ | paired median ΔR² | 0.012725 | 0.012969 | +0.000243 |
| transition_identity | bootstrap95 mean | 0.024016 | 0.024177 | +0.000161 |
| transition_identity | bootstrap95 ci_low | 0.016087 | 0.016207 | +0.000120 |
| transition_identity | bootstrap95 ci_high | 0.032170 | 0.032358 | +0.000189 |
| transition_identity | frac_pos | 0.576055 | 0.581943 | +0.005888 |
| transition_identity | n | 1019 | 1019 | +0 |
| transition_identity | significant>0 | 是 | 是 | — |
| transition_identity | paired n | 1019 | 1019 | +0 |
| transition_identity | win | 587 | 593 | +6 |
| transition_identity | tie | 0 | 0 | +0 |
| transition_identity | loss | 432 | 426 | -6 |
| transition_identity | paired mean ΔR² | 0.024016 | 0.024177 | +0.000161 |
| transition_identity | paired median ΔR² | 0.014242 | 0.014964 | +0.000722 |

| 判定项 | 11,904 | 14,880 |
|---|---|---|
| ΔR² floor | 0.005000 | 0.005000 |
| floor 通过 | 是 | 是 |
| transition_margin_clean | 否 | 否 |
| verdict | LOAD_BEARING | LOAD_BEARING |

| 不变量 | 11,904 | 14,880 |
|---|---|---|
| `alpha0_pred_equals_context_prior` | 是 | 是 |
| `T_identity_is_state_identity` | 是 | 是 |
| `live_weights_restored` | 是 | 是 |

**`transition_margin_clean = False` 的原因（协议自带说明，非本文推测）**：T-identity feeds O a FROZEN z_t (OOD for O trained on evolved states); a perfectly clean transition-only ablation is not achievable on this route — margin partly reflects OOD.

因此 T-identity 一臂的 margin 有一部分来自 OOD 效应，不能整体解释为「状态转移的贡献」。这一标记在两个 checkpoint 上同时为 False，属于该评测路径的共有属性。

### 3.3 Q3 极端态审计

配对结构：n_pairs=84，protocol_n_pairs=84，n_extreme=84，n_control_unique=45，geo cluster 数=31，reused-control cluster 数=45，bootstrap 重抽样 10000 次。

**三臂聚合精度（极端态）**

| 臂 | 指标 | 11,904 | 14,880 | Δ |
|---|---|---|---|---|
| actual | R² | 0.625352 | 0.626887 | +0.001535 |
| actual | RMSE | 0.149152 | 0.148968 | -0.000183 |
| actual | NSE | -0.014218 | -0.012435 | +0.001783 |
| donor | R² | 0.589340 | 0.588811 | -0.000529 |
| donor | RMSE | 0.158419 | 0.158294 | -0.000125 |
| donor | NSE | -0.134540 | -0.133157 | +0.001383 |
| mean | R² | 0.543006 | 0.542684 | -0.000322 |
| mean | RMSE | 0.197094 | 0.197369 | +0.000276 |
| mean | NSE | -0.673407 | -0.678468 | -0.005061 |

**端点保真（endpoint fidelity）**：Δloss = 对照臂损失 − actual 损失，>0 表示 actual 更贴合真实极端终点。

| 对照 | 家族 | 量 | 11,904 | 14,880 | Δ |
|---|---|---|---|---|---|
| actual vs donor | — | delta_loss_mean | 0.002565 | 0.002570 | +4.041e-06 |
| actual vs donor | paired | mean | 0.002565 | 0.002570 | +4.041e-06 |
| actual vs donor | paired | ci_low | 0.001195 | 0.001195 | -2.350e-07 |
| actual vs donor | paired | ci_high | 0.003983 | 0.003988 | +5.086e-06 |
| actual vs donor | paired | n | 84 | 84 | +0 |
| actual vs donor | paired | significant_gt0 | 是 | 是 | — |
| actual vs donor | paired | frac_pos | 0.666667 | 0.654762 | -0.011905 |
| actual vs donor | geo-cluster | mean | 0.002565 | 0.002570 | +4.041e-06 |
| actual vs donor | geo-cluster | ci_low | 0.001119 | 0.001127 | +8.103e-06 |
| actual vs donor | geo-cluster | ci_high | 0.003987 | 0.003987 | -6.835e-07 |
| actual vs donor | geo-cluster | n | 84 | 84 | +0 |
| actual vs donor | geo-cluster | significant_gt0 | 是 | 是 | — |
| actual vs donor | geo-cluster | n_clusters | 31 | 31 | +0 |
| actual vs donor | reused-control | mean | 0.002565 | 0.002570 | +4.041e-06 |
| actual vs donor | reused-control | ci_low | 0.001003 | 0.000996 | -6.841e-06 |
| actual vs donor | reused-control | ci_high | 0.004140 | 0.004141 | +8.868e-07 |
| actual vs donor | reused-control | n | 84 | 84 | +0 |
| actual vs donor | reused-control | significant_gt0 | 是 | 是 | — |
| actual vs donor | reused-control | n_clusters | 45 | 45 | +0 |
| actual vs mean | — | delta_loss_mean | 0.011261 | 0.011389 | +0.000128 |
| actual vs mean | paired | mean | 0.011261 | 0.011389 | +0.000128 |
| actual vs mean | paired | ci_low | 0.007530 | 0.007645 | +0.000115 |
| actual vs mean | paired | ci_high | 0.015303 | 0.015450 | +0.000147 |
| actual vs mean | paired | n | 84 | 84 | +0 |
| actual vs mean | paired | significant_gt0 | 是 | 是 | — |
| actual vs mean | paired | frac_pos | 0.821429 | 0.809524 | -0.011905 |
| actual vs mean | geo-cluster | mean | 0.011261 | 0.011389 | +0.000128 |
| actual vs mean | geo-cluster | ci_low | 0.005466 | 0.005548 | +8.242e-05 |
| actual vs mean | geo-cluster | ci_high | 0.017080 | 0.017266 | +0.000186 |
| actual vs mean | geo-cluster | n | 84 | 84 | +0 |
| actual vs mean | geo-cluster | significant_gt0 | 是 | 是 | — |
| actual vs mean | geo-cluster | n_clusters | 31 | 31 | +0 |
| actual vs mean | reused-control | mean | 0.011261 | 0.011389 | +0.000128 |
| actual vs mean | reused-control | ci_low | 0.005212 | 0.005319 | +0.000107 |
| actual vs mean | reused-control | ci_high | 0.017714 | 0.017873 | +0.000159 |
| actual vs mean | reused-control | n | 84 | 84 | +0 |
| actual vs mean | reused-control | significant_gt0 | 是 | 是 | — |
| actual vs mean | reused-control | n_clusters | 45 | 45 | +0 |

**响应幅度（response magnitude）**

| 对照 | 量 | 11,904 | 14,880 | Δ |
|---|---|---|---|---|
| 极端 actual vs donor | mean | 0.035918 | 0.036017 | +9.861e-05 |
| 极端 actual vs donor | n | 84 | 84 | +0 |
| 极端 actual vs mean | mean | 0.081369 | 0.081731 | +0.000362 |
| 极端 actual vs mean | n | 84 | 84 | +0 |
| 常态 actual vs donor | mean | 0.034739 | 0.034851 | +0.000112 |
| 常态 actual vs donor | n | 84 | 84 | +0 |
| 常态 actual vs mean | mean | 0.063186 | 0.063683 | +0.000498 |
| 常态 actual vs mean | n | 84 | 84 | +0 |

**热干交互（hot-dry − normal）**：这是 `hotdry_enhancement` 判定所依据的量。

| 效应量 | 家族 | 量 | 11,904 | 14,880 | Δ |
|---|---|---|---|---|---|
| `dloss_donor` | paired | mean | 0.000436 | 0.000427 | -9.012e-06 |
| `dloss_donor` | paired | ci_low | -0.001719 | -0.001729 | -1.052e-05 |
| `dloss_donor` | paired | ci_high | 0.002629 | 0.002611 | -1.716e-05 |
| `dloss_donor` | paired | significant_gt0 | 否 | 否 | — |
| `dloss_donor` | geo-cluster | mean | 0.000436 | 0.000427 | -9.012e-06 |
| `dloss_donor` | geo-cluster | ci_low | -0.002162 | -0.002173 | -1.056e-05 |
| `dloss_donor` | geo-cluster | ci_high | 0.003200 | 0.003175 | -2.511e-05 |
| `dloss_donor` | geo-cluster | significant_gt0 | 否 | 否 | — |
| `dloss_donor` | reused-control | mean | 0.000436 | 0.000427 | -9.012e-06 |
| `dloss_donor` | reused-control | ci_low | -0.002527 | -0.002524 | +2.900e-06 |
| `dloss_donor` | reused-control | ci_high | 0.003306 | 0.003289 | -1.746e-05 |
| `dloss_donor` | reused-control | significant_gt0 | 否 | 否 | — |
| `dloss_mean` | paired | mean | 0.008021 | 0.008094 | +7.236e-05 |
| `dloss_mean` | paired | ci_low | 0.004334 | 0.004404 | +6.937e-05 |
| `dloss_mean` | paired | ci_high | 0.011935 | 0.012020 | +8.459e-05 |
| `dloss_mean` | paired | significant_gt0 | 是 | 是 | — |
| `dloss_mean` | geo-cluster | mean | 0.008021 | 0.008094 | +7.236e-05 |
| `dloss_mean` | geo-cluster | ci_low | 0.003173 | 0.003226 | +5.263e-05 |
| `dloss_mean` | geo-cluster | ci_high | 0.012358 | 0.012448 | +8.922e-05 |
| `dloss_mean` | geo-cluster | significant_gt0 | 是 | 是 | — |
| `dloss_mean` | reused-control | mean | 0.008021 | 0.008094 | +7.236e-05 |
| `dloss_mean` | reused-control | ci_low | 0.002693 | 0.002743 | +5.000e-05 |
| `dloss_mean` | reused-control | ci_high | 0.013822 | 0.013931 | +0.000109 |
| `dloss_mean` | reused-control | significant_gt0 | 是 | 是 | — |
| `resp_donor` | paired | mean | 0.001179 | 0.001165 | -1.387e-05 |
| `resp_donor` | paired | ci_low | -0.000915 | -0.000923 | -8.515e-06 |
| `resp_donor` | paired | ci_high | 0.003378 | 0.003378 | +2.523e-07 |
| `resp_donor` | paired | significant_gt0 | 否 | 否 | — |
| `resp_donor` | geo-cluster | mean | 0.001179 | 0.001165 | -1.387e-05 |
| `resp_donor` | geo-cluster | ci_low | -0.001001 | -0.001021 | -1.959e-05 |
| `resp_donor` | geo-cluster | ci_high | 0.003260 | 0.003244 | -1.602e-05 |
| `resp_donor` | geo-cluster | significant_gt0 | 否 | 否 | — |
| `resp_donor` | reused-control | mean | 0.001179 | 0.001165 | -1.387e-05 |
| `resp_donor` | reused-control | ci_low | -0.001379 | -0.001394 | -1.494e-05 |
| `resp_donor` | reused-control | ci_high | 0.003562 | 0.003556 | -5.912e-06 |
| `resp_donor` | reused-control | significant_gt0 | 否 | 否 | — |
| `resp_mean` | paired | mean | 0.018184 | 0.018048 | -0.000136 |
| `resp_mean` | paired | ci_low | 0.009961 | 0.009794 | -0.000166 |
| `resp_mean` | paired | ci_high | 0.026469 | 0.026368 | -0.000101 |
| `resp_mean` | paired | significant_gt0 | 是 | 是 | — |
| `resp_mean` | geo-cluster | mean | 0.018184 | 0.018048 | -0.000136 |
| `resp_mean` | geo-cluster | ci_low | 0.005526 | 0.005400 | -0.000126 |
| `resp_mean` | geo-cluster | ci_high | 0.029643 | 0.029484 | -0.000158 |
| `resp_mean` | geo-cluster | significant_gt0 | 是 | 是 | — |
| `resp_mean` | reused-control | mean | 0.018184 | 0.018048 | -0.000136 |
| `resp_mean` | reused-control | ci_low | 0.006874 | 0.006795 | -7.822e-05 |
| `resp_mean` | reused-control | ci_high | 0.029347 | 0.029196 | -0.000151 |
| `resp_mean` | reused-control | significant_gt0 | 是 | 是 | — |

**分层精度（两个 cohort × 四条臂）**

| cohort | 臂 | 指标 | 11,904 | 14,880 | Δ |
|---|---|---|---|---|---|
| hotdry | `closure_zero_scale` | R² | 0.575078 | 0.575375 | +0.000297 |
| hotdry | `closure_zero_scale` | RMSE | 0.184398 | 0.184210 | -0.000188 |
| hotdry | `full` | R² | 0.625352 | 0.626887 | +0.001535 |
| hotdry | `full` | RMSE | 0.149152 | 0.148968 | -0.000183 |
| hotdry | `t_identity` | R² | 0.575256 | 0.575508 | +0.000252 |
| hotdry | `t_identity` | RMSE | 0.253929 | 0.254088 | +0.000160 |
| hotdry | `weather_in_base` | R² | 未记录 | 未记录 | — |
| hotdry | `weather_in_base` | RMSE | 未记录 | 未记录 | — |
| matched_normal | `closure_zero_scale` | R² | 0.520639 | 0.521009 | +0.000369 |
| matched_normal | `closure_zero_scale` | RMSE | 0.182254 | 0.182148 | -0.000106 |
| matched_normal | `full` | R² | 0.560255 | 0.561318 | +0.001063 |
| matched_normal | `full` | RMSE | 0.159097 | 0.159115 | +1.736e-05 |
| matched_normal | `t_identity` | R² | 0.520226 | 0.520603 | +0.000376 |
| matched_normal | `t_identity` | RMSE | 0.257460 | 0.258072 | +0.000612 |
| matched_normal | `weather_in_base` | R² | 未记录 | 未记录 | — |
| matched_normal | `weather_in_base` | RMSE | 未记录 | 未记录 | — |

> `weather_in_base` 一臂的 R²/RMSE 两侧均为 null，与 `weather_in_base=否` 一致 —— 该消融臂本轮未运行，不是缺失数据。

**判定**

| 判定项 | 11,904 | 14,880 |
|---|---|---|
| 端点保真 | PASS | PASS |
| 热干增强 | FAIL | FAIL |
| raw_status | Q3_RESPONSE_FIDELITY_ONLY | Q3_RESPONSE_FIDELITY_ONLY |
| overall_status | Q3_RESPONSE_FIDELITY_ONLY | Q3_RESPONSE_FIDELITY_ONLY |
| 主判据 | geo_cluster_bootstrap_ci_low_gt0 | geo_cluster_bootstrap_ci_low_gt0 |
| 全部配对 uf 有差异 | 是 | 是 |
| weather_in_base | 否 | 否 |
| 证据角色 | final | final |

**口径边界**：`overall_status = Q3_RESPONSE_FIDELITY_ONLY` 的含义是 —— 在冻结协议下，actual 状态相对 donor / mean 对照更贴合极端终点（端点保真 PASS）；但**未**取得「热干条件下存在额外增强」的支持（热干增强 FAIL，主判据 geo-cluster CI 下界 ≤ 0）。不能据此声称模型整体通过了极端态审计，也不能声称模型能正确预测真实极端状态或具备因果反事实正确性。

热干增强判 FAIL 的原因本轮**无法区分**，候选包括架构能力边界、训练数据中极端样本的分布、损失函数对非线性交互的引导不足、协议对该效应的敏感度等。本文不选定其中任何一种。

### 3.4 历史复现

**范围**：仅 11,904 侧复现历史参考；14,880 侧无历史参考可比。

- 冻结参考：`historical_11904_reference.json`，SHA-256 `0b97406c3bd44cd68bb3f098b6ee2fb5da914f1198bd4684a1a55c813bd493f4`（验收器对该 SHA 做 fail-closed 校验，不符即停止封账）
- 正式指标键 **57 个**；被排除的 `_` 前缀元数据键 8 个：`_checkpoint`, `_generated_at`, `_generated_by`, `_note`, `_sources`, `_tolerance`, `_tolerance_rationale`, `_tolerances`
- 结果：57/57 通过，其中 **逐位相同 57 个**
- 默认容差 1e-06；按模式指定的容差：`{".R2": 1e-05, ".biasabs": 1e-05, ".nse": 1e-05, ".paired.n": 0.0, ".rmse": 1e-05, "_bootstrap.ci_": 0.0001, "bootstrap95.": 0.0001, "delta_loss_mean": 1e-05, "n_control": 0.0, "n_extreme": 0.0, "n_pairs": 0.0, "official_R2_": 1e-05}`
- 容差理由：['Counts (n, n_pairs, n_extreme, n_control) must match EXACTLY -- a changed count means a changed manifest or dataloader, which is harness drift by definition.', 'Point metrics carry 1e-5: the frozen numbers were measured on GPU, and cuDNN/TF32 reduction order is not bit-stable across driver/library versions.  Real harness drift (different scorer, mask, manifest or split) moves these by orders of magnitude more.', 'Bootstrap CI bounds carry 1e-4: both evaluators seed np.random.default_rng(--seed, default 0), so resampling is deterministic given identical inputs, but tiny per-sample perturbations propagate into the quantiles.', 'These tolerances bound FLOAT NOISE only.  They are not a licence to wave through a mismatch: anything outside them is reported as DRIFT_TO_DIAGNOSE and must be traced to evaluator / manifest / scorer / dataloader before any comparison is read.']

**限定**：本项验证的是「在本次环境与本协议下，用同一 checkpoint 重跑能否得到同样的数字」。它不主张跨环境的完全确定性，也不主张 SHA 与结果之间存在唯一映射。14,880 一侧没有历史参考可比 —— 仅 11,904 侧复现历史参考；14,880 侧无历史参考可比。

---


## 四、决策


### 4.1 结论

**14,880（`terrastate/v2/verified-resume14880@v1`）继续作为后续实验的 anchor checkpoint。**

依据：

1. **Q1**：与 11,904 的差异在小数点后第四位及更小量级，方向在各 split / 分层 / 步长上不一致（见 §3.1）。
2. **Q2**：两者在 Validation 与 OOD-t 上的 verdict 均为 `LOAD_BEARING`，ΔR² 均超过 floor 0.005000（见 §3.2）。
3. **Q3**：两者的三项判定完全一致（端点保真 PASS、热干增强 FAIL、overall `Q3_RESPONSE_FIDELITY_ONLY`）。
4. **续训过程可验证**：exact-resume，M9 31/31 项检查通过，2976 次优化器更新全部在 stage 3，数据顺序按 DistributedSampler(seed, epoch) 精确恢复（见 §2.2）。
5. **评测系统可复现**：11,904 一侧 57/57 复现，逐位相同 57 个（见 §3.4）。

**这条决策不依赖「两个 checkpoint 模型状态相同」** —— 该说法本身不成立（见 §2.1）。

### 4.2 |ΔR²| < 0.01 这条规则的地位

- 它是一条**描述性对齐标准**，用于陈述两个 checkpoint 的表现接近程度。
- 它**不是**统计显著性检验：本轮未对 checkpoint 间差异做任何显著性检验。
- 它**不是**成功门或 checkpoint 选择门：接纳 14,880 的依据是 Q1/Q2/Q3 三维证据加续训可验证性。
- 它**没有被废除**，仍作为描述性口径继续使用。

### 4.3 不按 OOD 结果回选 checkpoint

OOD-t 上 R² 的 Δ 为 -7.121e-05，量级极小且方向与其它切面不一致。即便如此，也不回退到 11,904：

- 按 OOD 结果回选会引入「事后挑选最优点」的选择偏差；
- 14,880 承载了更多训练信号，且其续训过程已被 M9 独立验收；
- 该差异未经显著性检验，不足以支撑任何回选主张。

---


## 五、证据分区与工件清单


### 5.1 严格分区

本次尝试目录下的产物按下列分区处理，**任何一类都不得混入正式结果集**：

1. **正式重跑**（6 份）：本轮六份正式结果
   - `gpu0_v14880_val_q1q2`
   - `gpu1_v14880_oodt_q1q2`
   - `gpu2_v14880_oodt_q3`
   - `gpu3_legacy11904_val_q1q2`
   - `gpu4_legacy11904_oodt_q1q2`
   - `gpu5_legacy11904_oodt_q3`
2. **历史参考**：11,904 的历史 Q1/Q2/Q3 数字（57 个正式指标） —— 复现基准，不是本轮新测结果，SHA-256 `0b97406c3bd44cd68bb3f098b6ee2fb5da914f1198bd4684a1a55c813bd493f4`
3. **无效 partial 目录**（3 个）：无最终结果 JSON 的中途目录
   - `runs/gpu2_v14880_oodt_q1q2`：950 个文件，1,256,981,100 B ≈ 1.17 GiB，子项 ['q1_full']；无最终结果 JSON，永久保留为审计证据，不进入正式结果集
   - `runs/gpu5_v14880_val_q1q2`：1014 个文件，1,489,558,677 B ≈ 1.39 GiB，子项 ['q1_full', 'q2_alpha0']；无最终结果 JSON，永久保留为审计证据，不进入正式结果集
   - `runs/gpu6_legacy11904_val_q1q2`：887 个文件，1,172,305,212 B ≈ 1.09 GiB，子项 ['q1_full']；无最终结果 JSON，永久保留为审计证据，不进入正式结果集
4. **smoke 产物**：
   - `/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/ops/e0_q1q2q3_11904_vs_14880/20260818_154859/smoke`，子项 ['q1q2', 'q1q2.log', 'q3', 'q3_cpu', 'q3_cpu.log']；smoke 产物：永久保留为审计证据，绝不进入正式结果集
4. **自检 fixture**：
   - `/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/ops/e0_q1q2q3_11904_vs_14880/20260818_154859/selftest`，子项 ['fixture_clean', 'fixture_interrupted', 'smi_6gpu.sh', 'smi_foreign.sh', 'smi_idle.sh', 'smi_partial.sh']；selftest 产物：永久保留为审计证据，绝不进入正式结果集
5. **20260818 中断尝试**：`20260818_154859`，验收状态 `NOT_READY`（SHA-256 `70db57616c672ebca653e050c69fdf880064cca55593ae18e1ebc9339ee4734a`），3 个 INTERRUPTED 标记：
   - `runs/gpu0_v14880_val_q1q2/INTERRUPTED.json`
   - `runs/gpu1_v14880_oodt_q1q2/INTERRUPTED.json`
   - `runs/gpu2_v14880_oodt_q3/INTERRUPTED.json`
   watcher 轮询 486 次，jobs_launched=否；让出对象 PID [{'pid': '1057914', 'mem': '4752', 'user': 'xddu2'}, {'pid': '1057916', 'mem': '5814', 'user': 'xddu2'}, {'pid': '1057917', 'mem': '5814', 'user': 'xddu2'}, {'pid': '1057918', 'mem': '5814', 'user': 'xddu2'}, {'pid': '1057919', 'mem': '5814', 'user': 'xddu2'}]。该目录完整保留为审计证据。

### 5.2 六份一手结果

| 逻辑作业名 | 结果文件 | 字节 | 落盘时刻（UTC） | SHA-256 |
|---|---|---|---|---|
| `gpu0_v14880_val_q1q2` | `state_contract_exclusive.json` | 7,479 | 2026-08-20T03:29:45.156176Z | `229918a49a42887614d1cfce99dae70c2f0ccdc3590490bce73d5a2e8434314f` |
| `gpu1_v14880_oodt_q1q2` | `state_contract_exclusive.json` | 7,535 | 2026-08-20T03:42:35.610052Z | `965a46d249f816c0b17df903185a74bc3c6c371ca10b5ef7472d4459e31c9670` |
| `gpu2_v14880_oodt_q3` | `extreme_state_audit.json` | 135,432 | 2026-08-20T03:49:06.048221Z | `4a51ce5d2877305df1f10fe4c3e278945c4decca657ffcfc6d0f242ebf7bcc43` |
| `gpu3_legacy11904_val_q1q2` | `state_contract_exclusive.json` | 7,313 | 2026-08-20T03:42:50.566358Z | `10a903185fd14c16d0fec49b2e730a2bd451d3ff25b2fcaef40cf242f4960354` |
| `gpu4_legacy11904_oodt_q1q2` | `state_contract_exclusive.json` | 7,361 | 2026-08-20T04:12:28.251210Z | `d0ebbbbea74de549bba481ae5e3ee40fd478a8b5552cbfff09c84ec0e115f7c0` |
| `gpu5_legacy11904_oodt_q3` | `extreme_state_audit.json` | 135,430 | 2026-08-20T04:00:16.708652Z | `ccd1a9a107237bc409c96b92032497a84e5d8153d76270f04665153bab6a00fa` |

全部六份的实测 SHA-256 与本轮清点值一致（`sha256_matches_inventory` 均为 true），本轮只读校验，未修改。

### 5.3 v3 封账工件

| 文件 | 字节 | SHA-256 |
|---|---|---|
| `e0_comparison_11904_vs_14880_v3.json` | 240,571 | `2e1529ca4e24b3ef8f3498f35f9de2a5912f817aa6ffe0bfc87274df8e2cde4a` |
| `e0_metric_inventory_v3.json` | 82,211 | `e1b1c8c902d004267847197ea87970a0e7dd4993908ad01e80f218bed07e5a2e` |
| `e0_artifact_index_v3.json` | 42,046 | `59365d48c9c2be6c49da872e23c72efa3971a91f04eae9d25fa159e489a69855` |
| `e0_provenance_v3.json` | 37,491 | `719975c53699fa6a7a513e167e11136e34e58f95c9ad316a6dd7ec3abe18c1c6` |
| `e0_launch_record_v3.json` | 8,827 | `9e07243ed156c0850249f0352d97c17fffafb67454ebe2cd4e3a18a0780c222d` |
| `attempt_manifest_v3.json` | 9,675 | `41cee90e3d60dcd110b040eeaa896bc485d90f2cd63eaa7f02039b13b092602a` |
| `e0_acceptance_report_v3.json` | 166,619 | `f53232870def9ff219093052fd2bacfd035769443ab399fca49051bbf5363f57` |
| `verify_and_aggregate_retry_v3.py` | 111,147 | `9b7b6c0e7671460b3e4fcd9a4d0efd753fcf0e0e7545ce5550b8f984512174b8` |
| `closeout_audit_v3.json` | 5,058 | `00337d15e846cfdf7aa2ee8c5808bdf9097ae8c44c5bfec9c37d376abec2c008` |

> `closeout_audit_v3.json` 自身的 SHA 由本文档记录，以避免验收器自指哈希。

### 5.4 目录规模与上游证据

- 本次尝试目录合计 **21,610 个文件**，30,952,467,110 B ≈ 28.83 GiB
- 正式 run 目录 6 个，无效 partial 目录 3 个，日志 18 个，上游证据 22 项，既有 v1/v2 封账工件 27 项（全部保留，且不作为 v3 的数据来源）

| 正式 run 目录 | 文件数 | 字节 |
|---|---|---|
| `gpu0_v14880_val_q1q2` | 2,872 | 4,242,276,218 B ≈ 3.95 GiB |
| `gpu1_v14880_oodt_q1q2` | 5,740 | 8,227,751,690 B ≈ 7.66 GiB |
| `gpu2_v14880_oodt_q3` | 715 | 1,045,259,179 B ≈ 0.97 GiB |
| `gpu3_legacy11904_val_q1q2` | 2,872 | 4,242,281,564 B ≈ 3.95 GiB |
| `gpu4_legacy11904_oodt_q1q2` | 5,740 | 8,227,756,759 B ≈ 7.66 GiB |
| `gpu5_legacy11904_oodt_q3` | 715 | 1,045,259,213 B ≈ 0.97 GiB |

### 5.5 已如实登记的证据缺口

下列缺口是**已确认存在**的，登记而非掩盖：

- e0_launch_record.gpu{2,4,5,6}.json 的 jobs 列表为空
- Q3 结果 JSON 不记录 checkpoint SHA 与 evaluator commit（sidecar 绑定）
- Q3 协议文件计数三个口径不同：磁盘 8 / MANIFEST 7 / 结果 JSON 绑定 5
- 单作业 wall-clock 时长不可由现有日志证明
- 边界 checkpoint 记录 stage=2，而其后第一次更新属 stage=3

其中两项展开：

1. **Q3 身份为 sidecar 绑定**：extreme_state_audit.json 记录 protocol_sha，但不记录 checkpoint SHA；身份由 run 目录名、launch shard 的 checkpoint_sha256 与 runner 日志首行的加载记录三方共同确定，并直接校验磁盘上的 checkpoint 文件 SHA
   - `gpu2_v14880_oodt_q3`：checkpoint SHA-256 `a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f`，证明方式 `sidecar`，依据 ['launch_record_shard', 'run_dir_name', 'runner_log(result_path+metrics only)']
     身份基础：launch shard 记录的 checkpoint_sha256 + run 目录名角色标记；日志只能证明结果路径与指标一致，不能独立证明权重身份
   - `gpu5_legacy11904_oodt_q3`：checkpoint SHA-256 `644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd`，证明方式 `sidecar`，依据 ['launch_record_shard', 'run_dir_name', 'runner_log(result_path+metrics only)']
     身份基础：launch shard 记录的 checkpoint_sha256 + run 目录名角色标记；日志只能证明结果路径与指标一致，不能独立证明权重身份
2. **空的 launch record**：
   - `e0_launch_record.gpu2.json`（SHA-256 `f3c16a49f302f685bcfa149d0f6f311b108241980b4127571d43ea341bbe09f7`，n_jobs=0）：jobs 列表为空；真实启动记录只存在于 launch_record_shard_pgpu*.json，本文件不可作为启动证据
   - `e0_launch_record.gpu4.json`（SHA-256 `5681c92afe761609f5c6b6386d928db5acb912a94f0f2849c1ce791e20321587`，n_jobs=0）：jobs 列表为空；真实启动记录只存在于 launch_record_shard_pgpu*.json，本文件不可作为启动证据
   - `e0_launch_record.gpu5.json`（SHA-256 `5551442be2a3a9dd0389a9614e61905a672ef8627d7902640789027d56773d15`，n_jobs=0）：jobs 列表为空；真实启动记录只存在于 launch_record_shard_pgpu*.json，本文件不可作为启动证据
   - `e0_launch_record.gpu6.json`（SHA-256 `4dc43ac0c0dd1669465d02587c8e5ce2f88c720f5e7520c645abad417737bbf1`，n_jobs=0）：jobs 列表为空；真实启动记录只存在于 launch_record_shard_pgpu*.json，本文件不可作为启动证据
   - `e0_launch_record.json`（SHA-256 `f1bd3b79c03f5e4f83b148dc0e17a12edd84dd885bcd71822a70c82ae4ff91d8`，n_jobs=6）：合并产物；job 名称字段曾缺失，v2 阶段以 e0_launch_record_reconstructed.json 补齐，v3 直接改用 shard 为准

3. **Q3 协议文件计数三个口径不同**：磁盘 8 个、MANIFEST.SHA256 列出 7 个（不含自身）、结果 JSON 绑定 5 个。三个数字都如实报告，不择一掩盖。

---


## 六、验收与审计


### 6.1 v3 验收

验收器：`verify_and_aggregate_retry_v3.py`（SHA-256 `9b7b6c0e7671460b3e4fcd9a4d0efd753fcf0e0e7545ce5550b8f984512174b8`），fail-closed（任一检查失败即整体 BLOCKED；不得在存在失败项时写「正式封账」）。

| 门 | 主题 | 检查数 | 失败 |
|---|---|---|---|
| A | 作业清单、启动记录与 checkpoint 身份 | 111 | 0 |
| B | 四份 Q1/Q2 结果：状态、契约、绑定、数值有限性与 Q2 schema 完整性 | 185 | 0 |
| C | 两份 Q3 结果：证据角色、配对数、协议绑定、CI 完整性与 sidecar 身份 | 180 | 0 |
| D | 11,904 复现历史参考：57 个正式指标逐项比对 | 119 | 0 |
| E | 完整性：无 smoke/partial/中断混入、无幽灵结果、ground truth 归属、口径边界 | 42 | 0 |
| F | sanity anchor、M9 验收、参数审计与 evaluator 源码指纹交叉核对 | 95 | 0 |
| **合计** | — | **732** | **0** |

**sanity anchor**（用户下发的期望值；不一致即停止封账，禁止改数字迁就）：

| 作业 | 路径 | 期望 | 实测 |
|---|---|---|---|
| `gpu3_legacy11904_val_q1q2` | `Q1_forecast.full.R2` | 0.49732196418835595 | 0.49732196418835595 |
| `gpu0_v14880_val_q1q2` | `Q1_forecast.full.R2` | 0.49709355615470024 | 0.49709355615470024 |
| `gpu4_legacy11904_oodt_q1q2` | `Q1_forecast.full.R2` | 0.5693493611664086 | 0.5693493611664086 |
| `gpu1_v14880_oodt_q1q2` | `Q1_forecast.full.R2` | 0.5692781483135535 | 0.5692781483135535 |

### 6.2 封账环境

- CPU 封账节点 `csy-zg01-gnode68`；GPU 执行节点 `csy-zg01-gnode39`（GPU 执行节点与本轮 CPU 封账节点是两台不同机器，两者都必须如实记录，任何一方都不得覆盖另一方）
- `CUDA_VISIBLE_DEVICES` = `''`（严格 CPU-only，未创建 CUDA context，未导入 torch）
- Python 3.13.12
- git 仓库根 `/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2`，HEAD `c9503030e498e8ec86fffe9105998c3a2a540d68`，分支 `main`
- 工作树 dirty：是，共 63 条，其中 obsworld 之外 9 条
- 工作树确实是 dirty 的：obsworld/** 由另一会话并发修改，本轮不触碰；obsworld 之外的条目多为本封账自身新增的 untracked 目录/文档。本脚本只读 git，不执行 add/commit/push/reset/checkout/stash/clean。

本轮约束：
- 严格 CPU-only：CUDA_VISIBLE_DEVICES=""，不创建 CUDA context
- 不重跑任何 GPU 作业，不启动训练 / Q4 / Candidate C / simulator
- 不删除、移动、覆盖任何 raw JSON、checkpoint、旧 manifest、v1/v2 工件
- 不进行任何进程操作，不执行 git 写操作

### 6.3 已纠正的缺陷记录

- **A03 v2 的 Q2 对照表数字无来源**
  - 涉及数值：[0.556762, 0.556617, 0.556546, 0.484868, 0.012454, 0.013196, 0.012587, 0.012732]
  - 证据：对六份一手结果全部浮点值做 |Δ|<5e-7 搜索，命中集合为空
  - 处理：v3 一律从 raw JSON 重新推导 Q2 三臂与官方 Δ

### 6.4 明确未被用作数据来源的文件

- 思路整理进展/A03_TerraState_关键实验结果与决策总账.md（待本轮重写的文档本身）
- e0_comparison_11904_vs_14880.json / _v2.json / _v2_comprehensive.json
- e0_acceptance_report.json / _v2.json
- closeout_audit_v2.json

---


## 七、后续行动


### 7.1 可直接使用

- `terrastate/v2/verified-resume14880@v1` 作为 anchor，用于 Candidate C 对比基线、Q4 评测与其它下游实验。
- 评测协议已冻结：后续实验必须引用相同的冻结清单 SHA-256 与 Q3 协议目录，否则结果不可比。
- 下一步动作：`CANDIDATE_C_T3_CPU_CONTRACT`。

### 7.2 待解决问题

1. **Q3 热干增强 FAIL 的根因**：需要能区分「架构 / 数据分布 / 损失引导 / 协议敏感度」的实验设计；与 Candidate C 的同协议 Q3 结果对比是第一步。
2. **`transition_margin_clean = False`**：其成因已由协议说明指出（T-identity 喂入冻结 z_t 造成 OOD），需要设计能把「转移贡献」与「OOD 效应」分开的消融。
3. **checkpoint 间差异的显著性**：若后续需要主张两个 checkpoint 表现「有/无」差异，必须补做针对该差异的检验，当前 0.01 描述性标准不足以支撑此类主张。
4. **`weather_in_base` 消融臂未运行**：Q3 中该臂 R²/RMSE 为 null，如需该维度证据须单独运行。

### 7.3 A01/A02 同步事项

已在 A01/A02 中同步的最小事实集见两份文档自身的更新说明；本文只登记同步项：

1. E0 与 T0 的完成状态；
2. 三份 checkpoint 的角色区分（边界 11,904 / verified 14,880 / 历史 14,880）；
3. 0.01 的语义（描述性对齐标准，非显著性门、非选择门）；
4. 组合损失 λ 取值为**暂定**，须先做 loss/gradient scale pilot 再冻结，且只在 validation 上选择；
5. C0S 公平匹配的定义；
6. T3 smoke 与 T5 正式 scenario manifest 的冻结时机与外部 sidecar SHA 要求；
7. 五轴结构、Q4 与 Candidate C 的既有结构保持不变。

---


## 附录 A：核心数字速查

```
Q1 Validation (952 targets)
  11,904: R2=0.497322  RMSE=0.157288
  14,880: R2=0.497094  RMSE=0.157334
  dR2   = -0.000228

Q1 OOD-t (1904 targets)
  11,904: R2=0.569349  RMSE=0.150594
  14,880: R2=0.569278  RMSE=0.150627
  dR2   = -7.121e-05

Q2 verdict: 两个 checkpoint、两个 split 均为 LOAD_BEARING；transition_margin_clean 均为 False
Q3 overall: 两个 checkpoint 均为 Q3_RESPONSE_FIDELITY_ONLY（端点保真 PASS，热干增强 FAIL）

历史复现: 57/57 通过，逐位相同 57 个（仅 11,904 侧）
v3 验收 : ACCEPTED，732 项检查，0 项失败
```

## 附录 B：常见问题

**Q：14,880 的 R² 略低于 11,904，说明模型变差了吗？**  
A：Validation 上 ΔR² = -0.000228，OOD-t 上 ΔR² = -7.121e-05，量级在小数点后第四位及更小，且在分层与预测步长上方向并不一致（既有变好也有变差，见 §3.1）。本轮未对该差异做显著性检验，因此既不能说「变差了」，也不能说「没有差别」。

**Q：11,904 和 14,880 的模型权重是一样的吗？**  
A：不是。已验明权重逐值相同的是 **verified 14,880 与历史 14,880** 这一对（255 个张量，`value_sha=aa98fbd2fa302727`，max abs diff = 0）。11,904 与 14,880 之间不存在这样的证据，且二者的评测结果本身就不同。

**Q：Q3 判 FAIL，模型还能用吗？**  
A：FAIL 只落在「热干增强」这一项上。端点保真为 PASS，Q1 精度正常。结论的准确表述是 `Q3_RESPONSE_FIDELITY_ONLY`：支持响应保真，不支持热干条件下的额外增强。FAIL 的原因本轮无法区分。

**Q：0.01 阈值被废除了吗？**  
A：没有。它继续作为描述性对齐标准使用，只是明确了它不是显著性门，也不是 checkpoint 选择门。

**Q：这份文档是最终结论吗？**  
A：不是。它是当前证据链下的封账版。Candidate C 与 Q4 的结果可能改变其中的解释部分；已记录的一手数值与 SHA 不会因此改变。

**Q：怎么核对本文的任何一个数字？**  
A：本文由 `render_a03_v3.py` 从 `e0_comparison_11904_vs_14880_v3.json` 等 v3 工件渲染，没有手工抄录环节。逐项核对路径见每张表所标注的字段名，最终可追到六份一手结果 JSON 的 SHA-256（§5.2）。

---

**渲染脚本**：`render_a03_v3.py`  
**渲染时间（UTC）**：2026-08-20T14:33:48.362754Z  
**数据来源**：render_a03_v3.py 顶部 docstring 所列 v3 工件与 parameter_audit.json  
**文档结束**
