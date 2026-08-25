# TerraState exact-resume 11,904 → 14,880 — 执行状态

- ops 目录：`terrastate/ops/resume11904_to14880/20260818_112933/`
- 仓库 HEAD：`c9503030e498e8ec86fffe9105998c3a2a540d68`（分支 main，未 push，未 commit）
- 环境：`/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python`（3.11.15 / torch 2.12.0+cu130），本轮 shell `cuda avail = False`

## 里程碑

| ID | 内容 | 状态 |
|---|---|---|
| M0 | checkpoint schema 重审 + 三方参数核对 + 数据身份证明 | **DONE** |
| M1 | 四个核心 artifact 中央存储 / registry / resolver | **DONE** |
| M2 | resume 失败回归测试（先失败） | **DONE** |
| M3 | resume 代码修复 | **DONE** |
| M4 | 全部 CPU 测试通过 | **DONE** |
| M5 | 参数审计 + launch manifest 冻结 | **DONE** |
| M6 | 安全 GPU watcher 启动 | **DONE** |
| M7 | 8×H200 稳定空闲并启动训练 | **DONE** |
| M8 | step 14,880 完成 | **DONE**（见 §M8，约 45 min，exit 0） |
| M9 | checkpoint / provenance / validation 验收 | **DONE**（31/31，`accepted=true`） |
| M10 | verified 14,880 注册为未来 anchor | **DONE**（在 E0 ops 目录执行，见下） |

> **顶部表与下方各节已对齐（M0–M10 全部 DONE）。**
> 修正记录：此表此前长期停在 "M1 IN PROGRESS / M2–M10 TODO"，
> 而文档下方各节其实已经记录了 M8/M9 完成。表格未同步是本文件的记账错误，
> 不代表当时里程碑未完成；现按磁盘真实状态更正。

M10 不在本 ops 目录执行，落在 E0 任务目录：
`ops/e0_q1q2q3_11904_vs_14880/20260818_154859/`
（`m10_publish.py` / `m10_register.py` + 两份 report）。
对象 `a5d2a0cc…`（mode 0444，源文件保留），registry revision
`ebc374b34b2e818a` → `a7fd2763935a26d1`，alias
`terrastate/v2/default-training-anchor` → `terrastate/v2/verified-resume14880@v1`。

### 双来源（不得混用）

| 角色 | checkpoint | 用途 |
|---|---|---|
| legacy 证据 checkpoint / 精确续训父节点 | 11,904 `644deaac…` | 冻结 Q1/Q2/Q3 历史证据的**唯一**来源 |
| anchor | verified 14,880 `a5d2a0cc…` | 后续旧模型评测与新阶段初始化 |

- 11,904 的历史 Q1/Q2/Q3 数字**永远不得改标成 14,880 的**。
- verified 14,880 与 historical 14,880：**权重逐字节相同**
  （`value_sha=aa98fbd2fa302727`，255 张量最大差 0），但 **file sha256 不同**
  （`a5d2a0cc` vs `99f15a35`，因多了 B5 lineage 块与本次 args/时间戳）。
- 11,904 与 14,880：**权重不同**（`aba100c138119bc0` vs `aa98fbd2fa302727`，
  最大绝对差 `1.9256e-03`）。
- 11,904 vs verified 14,880 的同协议 Q1/Q2/Q3 正式评测**尚未开始**
  （GPU 被其他用户占用），状态见 E0 目录的 `STATUS.md`。

## M0 结论（已完成）

### 1. 撤回上一轮错误阻塞结论

上一轮以 `optimizer` / `scheduler` / `rng_states` / `q_trainable_params` 为键名探测
checkpoint，键不存在即判定"两个 checkpoint 都无法 exact resume"，并给出 A/B/C 三选一。
**该结论错误，现正式撤回。** 真实 schema 使用
`optimizer_state_dict` / `scheduler_state_dict` / `rng_state` + `rng_states_by_rank` /
`q_freeze`，且 `total_steps` 是顶层字段。按正确键名复审后：
`checkpoint_boundary80.pt` 是**完整的 exact-resume checkpoint**，不存在权重缺失阻塞。

### 2. PARENT_CKPT 事实（读取自文件本身）

`WorldModel2026-planb-v2train/runs/terrastate_v2/run1/checkpoint_boundary80.pt`

```
file_sha256 = 644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd
bytes       = 37,972,401
arch/route  = TerraStateV2 / terrastate_v2
step=11904  epoch=31  micro_in_epoch=372  stage=2  candidate=stage2_end_boundary80
total_steps=14880  accum=1  world_size=8  global_batch=64  alpha=1.0
best_val=0.31334985432787643   lambda_state=0.01
b4_state_dict           : 255 keys
optimizer_state_dict    : 2 param groups (branch n=30 / q n=223), 30 个 Adam state 条目
scheduler_state_dict    : last_epoch=11904 _step_count=11905 base_lrs=[3e-05, 9.9e-07]
scaler                  : {enabled: False, note: "FP32 training; GradScaler disabled"}
rng_state               : python/numpy/torch/cuda
rng_states_by_rank      : list len=8
q_freeze                : {trainable_q: [], unfreeze_prefixes: ["core.blocks.2."]}
```

### 3. 三方参数核对：`parameter_audit.json`

49 条参数，来源为 checkpoint（`args` + 顶层字段）、`run1/train.log`、
`TERRASTATE_V2_RUNBOOK.md`。结果：

```
all_consistent = true
inconsistent_parameters = []
runbook_literals_missing = []
```

算术自洽：`14880 − 11904 = 2976`；`updates/epoch = floor(ceil(23816/8)/8·…) = 372`；
`372 × 8 = 2976`（epoch 32..39）；`int(0.80 × 14880) = 11904`。

### 4. 阶段边界语义（决定 M3 修复内容）

`train.log` 证据：

```
[10:08:13]   [boundary80] forced checkpoint saved at step 11904
[10:08:13]   [stage] 2 -> 3 at step 11904; trainable_q=12
```

即 boundary80 落盘时记录 `stage=2`，**落盘之后**原始 run 才切到 stage 3。
因此 exact resume 的**第 11,905 次 update 必须已经处于 stage 3**，
恰好解冻 12 个 `core.blocks.2.*` q 张量，且**不得再次写出 boundary80 checkpoint**。

当前 `train/train_terrastate_v2.py:379-380` 的行为与此相反：

```python
current_stage = int(rk["stage"])                      # = 2
apply_stage(student, current_stage, unfreeze_prefixes)  # q 全冻结
```

随后主循环在 step 变为 11905 后才调用 `maybe_transition(stage_at(11905, 14880)) = 3`，
于是产生两处偏差：
- **多一次 stage-2 update**（第 11,905 次 update 在 q 全冻结下执行）；
- **重复写出 `checkpoint_boundary80.pt`**（step=11905，候选名仍为 `stage2_end_boundary80`）。

另外识别出的相关缺陷（M3 一并修）：
- 从已完成的 14,880 checkpoint resume 会**多跑一次 update**（`step >= total_steps`
  只在一次 update 之后才检查），缺少 completed-resume no-op；
- `output_dir` 只有 `mkdir(exist_ok=True)`，无历史输出覆盖保护；
- checkpoint 不记录 parent/child 血缘（`sha` 块无 parent checkpoint SHA）。

### 5. 数据身份证明：`data_manifest_check.json`

原 run 的 `args.train_dir=/tmp/zjliu17_mix_stage_v2/train`、
`args.val_dir=/tmp/zjliu17_mix_stage_v2/val_chopped` 已不存在（暂存目录）。
用 `data_manifest_sha256`（对 `sorted((relpath, size_bytes))` 求 SHA256，
与 `train/terrastate_v2_common.py` 实现逐字一致）证明持久化根目录身份相同：

```
train : /csy-mix02/.../TrainData/GreenEarthNet/train
        n=23816 (expect 23816)
        17c645d92e9dd4c38ce5bf14a412115c5f6622109cff3c19118b098e604b2554  MATCH
val   : /csy-mix02/.../TrainData/GreenEarthNet/val_chopped
        n=952 (expect 952)
        555d44c0d59ab3902cf7d929ca86ce8bf4e3ce7cfda66c1c72b45a2ed3fd76c9  MATCH
all_match = true
```

期望值同时出现在 checkpoint 的 `sha.train_manifest_sha256` / `sha.val_manifest_sha256`
与两个 cache sidecar 的 `data_manifest_sha256` 中，三处一致。
相对路径集合与每个文件大小完全相同，因此 future-state cache 的 relpath 键在新根目录下可解析。
**未重新生成任何"相似"数据集。**

### 6. `train_cache_sha256 == val_cache_sha256` 的解释（非缺陷）

两者都等于 `2a14f0a4c3653f38ee52155d38c38f76d01cc234a5fb301a3dfb512ee0101a66`。
读 `train/terrastate_future_state_cache.py:237-241`：`config_sha256` 只覆盖
`schema, driver_protocol, field_order, horizon_h, context_len, target_len, patch_size,
state_dim, patch_mask_rule, future_weather_zeroed, q_projector_sha256`
——即**协议指纹**，不含 split / 数据内容。两个 split 协议相同，故 SHA 必然相同；
区分数据身份的是 `data_manifest_sha256`（train/val 不同，见上）与 `mask_sha256`
（`197a611a809bbc41` vs `b68046c24edd0737`）。resume 时对这两个 cache SHA 的断言仍然有效
（协议漂移会被抓住），只是它不是数据身份断言。

### 7. M1：四个核心权重的中央内容寻址存储

`/csy-mix02/cog8/zjliu17/Agent/model-artifacts`，objects 模式 0444，
tmpfile + fsync + 重新哈希 + `os.replace` 原子发布；**只复制、从不 mv / 删除源文件**。

```
terrastate/v2/legacy-boundary11904@v1                 37972401 B  644deaac0b1578cd
terrastate/v2/historical-full14880@v1                 44300969 B  99f15a35fb9a3569
obsworld/b4-exclusive/student-main-last-step14880@v1   28847063 B  42420f88a6aa631b
obsworld/b4/teacher-best-step13000@v1                 28846423 B  2c5d084236716d84
```

`terrastate/artifacts/weight_registry.json`（schema `terrastate_weight_registry_v1`,
revision `ebc374b34b2e818a`）：6 个 artifact + 2 个 RESERVED
（`terrastate/v2/verified-resume14880@v1` 附 7 条发布条件、`default-training-anchor` 别名）。
12GB train cache 与 478MB val cache 为 `kind="path-registered"`，**未复制进对象库**。
`terrastate/tools/resolve_artifact.py`：logical-id → 校验后的真实路径，
退出码 0 正常 / 2 未知 id 或别名 / 3 对象缺失 / 4 SHA256 不匹配；
6 个 id 全部 rc=0，两个负例 rc=2。

张量内容摘要复算（`state_sha_check.json`, `all_match=true`）证明
`student_init_sha256` / `q_projector_init_sha256` / `teacher_sha256` 与 checkpoint 记录一致，
因此 resume 的这三条断言可以通过。

### 8. M2：resume 失败回归测试（先证明会失败）

`terrastate/tests/test_resume_boundary11904.py`，13 项检查，CPU、无 CUDA context、无网络。
结构性复刻真实 11,904 的尴尬性质：`TOTAL_STEPS=10, BOUNDARY=8, UPDATES_PER_EPOCH=2`，
于是 step 8 恰好结束一个 epoch，`micro_in_epoch == 2 ==` 整个 epoch，
checkpoint 记录 `stage=2` 而下一次 update 属于 stage 3。

**未修改的 trainer：5/13 通过**（`m2_regression_baseline.json` / `m2_prefix_run.log`）：

| 失败项 | 现象 | 根因 |
|---|---|---|
| R5 | `stage(step 9)=2` | B1 |
| R8 | step 10 loss `0.36174861` vs 参考 `0.36168817` | B1 下游 |
| R8b | 最终权重 `1a55e960…` vs 参考 `e6d4ca3f…` | B1 下游 |
| R6 | 重复写出 `checkpoint_boundary80.pt` | B2 |
| R9 | 已完成 checkpoint 仍多跑 1 次 update 并重写 `checkpoint_last.pt` | B3 |
| R10 / R10b | 直接写入已有 checkpoint 的目录，历史输出被覆盖 | B4 |
| R11 | `lineage={}` | B5 |

基线已通过 R1/R2/R3/R4/R7 —— 特别是 R4 说明**步数本身没有多算**，
问题纯粹在 stage 语义、重复落盘、覆盖保护和血缘。

### 9. M3：resume 代码修复

`train/train_terrastate_v2.py`：`14b8b070…` → `d0e4051b…`，
`1 file changed, 140 insertions(+), 10 deletions(-)`（diff 存 `m3_trainer.diff`）。
**未改动**损失权重、λ_s 调度、lr/cosine/warmup、batch 算术、stage 分数、alpha、teacher 冻结。

- **B1**：`current_stage = stage_at(step, total_steps)` 取代 `int(rk["stage"])`。
  checkpoint 的 `stage` 是**被保存的那次 update 所处的 stage**，不是**下一次 update 所属的 stage**；
  在 80% 边界保存时父记录 stage 2，而不中断的原 run 在下一次 update 前已切到 stage 3。
  `apply_stage` 在 `opt.load_state_dict` 之前、DDP 包装之前执行，并打印重算日志。
- **B2**：`boundary80_saved_by_parent = (step == boundary80)`，抑制重复的强制边界 checkpoint。
- **B3**：`resume_completed = step >= stop_after_step` → 不进入任何 epoch，
  **不写 checkpoint、不写 loss_log**，指向已完成的 run 无法改动其输出。
- **B4**：`guard_output_dir()` 在 `init_process_group` **之前**抛 `FileExistsError`
  （所有 rank 行为一致，不会有 rank 卡在集合通信里）；
  唯一逃逸口 `--allow-existing-out`，正式 run 不使用。
- **B5**：每个 checkpoint 写入 `lineage`：`parent_path` / `parent_file_sha256` /
  `parent_step` / `parent_epoch` / `parent_micro_in_epoch` / `parent_stage_recorded` /
  `parent_b4_state_sha256` / `resume_stage_applied` / `data_order_restoration`。
- **B6**：stage 3 的可训练 q 集合断言恰为 unfreeze-prefix 集合（12 个 `core.blocks.2.*`），
  并与父 checkpoint 的 `q_freeze.unfreeze_prefixes` 交叉校验。

**数据顺序可恢复性据实记录**（`resume_data_order_note()`），不夸大为"精确"：
`world>1` 时 `DistributedSampler` 的排列完全由 `(seed, epoch)` 决定 → 精确；
单卡 shuffle 且在 epoch 中间恢复时，DataLoader generator 在中断点的状态未进 checkpoint
→ 标记为 approximate（模型/优化器/调度器/RNG 仍然精确）。
本轮正式 run 是 8 卡 DDP 且恢复点正好在 epoch 边界，属于精确情形。

**修复后：13/13 通过**（`m3_postfix_run.log`）。决定性证据是 R8b：
恢复运行的最终权重与不中断参考**逐比特相同**（`e6d4ca3fda535f61`），
R8 的 loss 轨迹也完全重合（step 10 = `0.36168817` 双方一致）。

### 10. M4：CPU 测试门（进行中）

- `tests/test_resume_boundary11904.py`：**13/13 PASS**。
- `tests/smoke_terrastate_v2_ddp.py`（2 进程 torchrun / gloo / CPU）：**7/7 PASS**
  —— D6/D7 覆盖 DDP 下的精确恢复，两 rank 权重 SHA 一致（`55e170d991fb95a4`）。
- `tests/smoke_terrastate_v2.py`：首次运行在 check 1 崩溃，**与本次修复无关**，两点证据：
  1. 崩溃点在 `build_cache` 结果的 f-string（`sanity['effective_rank']`），
     位于 `train/terrastate_future_state_cache.py`，该文件与 HEAD **逐字节相同**，
     且崩溃发生在任何 `run_training` 调用之前；
  2. 真正原因是 fixture 缺失：runbook 记录 fixture 是
     `runs/smoke_v2/data/{train,val}` 下指向真实 cube 的符号链接，
     而该目录现在是空的 → 数据集 0 个 cube → `_Sanity.report()` 走空分支
     只返回 `{n_patches: 0, n_nan: 0}` → f-string KeyError。
  在本任务目录内用 4 个 train + 2 个 val **符号链接**重建 fixture（不复制、不触碰真实数据）后，
  check 1 正常输出 `cov train=0.7495 eff_rank=6.18`，
  且 **12 / 12b / 12c / 12d 四项 resume 检查全部 PASS**。

**`13/iso` 在本 worktree 永久失败，且不应"修复"**：该检查断言 B-session 的
evaluator/protocol 文件在本 worktree 中不存在，但这些文件是**已提交的仓库状态**
（commit `e4c1158`, 作者 `luzheng`, 2026-08-14 的 terrastate/obsworld 拆分），
`git status` 显示我对它们零改动。删除它人已提交的成果违反共享资源约束，
因此按环境既有条件如实记录，不做任何删除或改写。

### 11. M5：参数审计与 launch manifest 冻结（完成）

`launch_manifest.json`（mode `0444`，SHA `1c7ea6c862a177d8abf8e6777f07275869fc179b83b0799b6234cbc558167d0a`）
在**任何 GPU 被触碰之前**把整次正式运行钉死：repo HEAD `c9503030e498`、
唯一被改动的已跟踪文件 `train/train_terrastate_v2.py`、11 个关键文件 SHA、
registry revision `ebc374b34b2e818a`、四个权重 artifact 经
`tools/resolve_artifact.py` 按**逻辑 id** 解析后的 store 路径、数据/cache 指纹、
完整 torchrun 命令、以及必须复现的算术。

**算术独立复算通过**（与 checkpoint 记录一致）：

```
23816 cubes / world 8 = 2977 per rank -> 372 batches (drop_last) -> accum 1
updates_per_epoch = 372     total_steps = 40 x 372 = 14880
boundary80 = int(0.80 x 14880) = 11904 = parent step
remaining = 14880 - 11904 = 2976 updates, epochs 32..39
```

`run1/train.log` 采样吞吐中位数 **1.57 it/s**（min 0.69 / max 1.79 / n=297），
故 2,976 步 ≈ **32 分钟**计算时间，另加 epoch 31 的一次纯 I/O 跳过。

**冻结命令已对 argparse 逐项校验**：trainer 定义 30 个选项，命令使用 26 个，
未知或畸形 flag **0**，required 缺失 **0**。刻意省略 4 个并已核对其默认值：
`--max-steps 0`、`--stop-after-step 0`（两者为 0 → `total_steps = 40×372 = 14880`、
`stop_after_step = 14880`，因此 `resume_completed = (11904 >= 14880)` 为 False，训练照常进行）、
`--deterministic` 缺省 False（与 parent `deterministic=False` 一致）、
`--allow-existing-out` 缺省 False（**覆盖保护处于激活状态**）。
`--future-state-scale` 显式写 `1.0`；`CUDA_VISIBLE_DEVICES` 故意不设置，
以保证使用全部 8 卡而非子集。

**第一次冻结被我自己作废并保留为证据**
（`launch_manifest.rejected_c4c8e7a9.json` + 同名 README）：
它把被改动文件记成 `rain/train_terrastate_v2.py`（丢了首字母 `t`）。
原因是 `git()` 对整个 stdout 做了 `.strip()`，吃掉了 `git status --short`
固定 3 字符前缀 `"XY "` 的前导空格，使 `l[3:]` 路径切片整体偏移一位。
修法是新增 `git_raw()` / `status_modified()` 按固定前缀解析、不 strip 流，
并加一条断言：**唯一允许的已跟踪改动只能是 `train/train_terrastate_v2.py`**
（对应共享资源第 13 条，保护工作区他人未提交内容）。
该缺陷只影响 provenance 记录本身，未触碰 GPU、未启动训练、未覆盖任何产物。
生成器也拒绝覆盖已存在的 manifest。

数据路径已从 parent 记录的 `/tmp/zjliu17_mix_stage_v2/{train,val_chopped}`
（已失效的 staging 路径）重新指向持久冻结根，三方 `data_manifest_sha256` 一致，
因此重指向不会触发 resume 断言。

## 共享资源状态

本轮所有命令均为只读探测或写入本任务自建目录，未启动任何 GPU 进程，
未 kill / renice / 迁移任何进程，未使用 sudo，未修改 crontab，未 push，未 `git add`。
`nvidia-smi` 单次采样显示 8 卡 4MiB / 0%，但**当前不据此启动训练**：
参数审计、代码修复、CPU gate 未完成前不进入 M7。

补充：M2–M4 期间新建的进程全部是本任务自己的 CPU 测试进程
（PID 1923837 / 1954751 / 1958979 / 1958980 / 1977567，均为前台启动后台运行、自行退出），
未复制 12GB/478MB cache，未删除任何他人文件；
smoke fixture 使用符号链接指向只读数据根，真实数据未被写入。
唯一被修改的已跟踪文件是 `train/train_terrastate_v2.py`（本任务授权范围内的 resume 修复）。

### 12. M6：GPU 空闲 watcher（完成）

`gpu_watcher.sh` 是一个失败即关闭的单实例轮询器，从 05:02:07 UTC 运行至 05:11:29 UTC，
累积 **10 次连续 idle 判定**（每次间隔 60 秒，共 ≥10 分钟无中断空闲），
然后写入 `m6_gpu_ready.json` 并自行退出。

**Idle 标准**（**所有 8 张 GPU 同时满足，连续 10 轮**）：
- `memory.used < 1024 MiB`
- `utilization.gpu < 5 %`

任一 GPU 任一指标超限、nvidia-smi 超时/错误、GPU 数量 ≠ 8、或发现任何 compute app，
立即重置 streak 为 0。该标准在整个等待期间**从未降低**。

**安全特性（self-test 7/7 PASS 验证）**：
- **A** 忙检测：mem/util 超限 → idle=false, streak=0
- **B** streak 恢复：最近 poll < 3×间隔 → 恢复旧 streak；否则丢弃（unobserved time ≠ idle time）
- **C** 幂等：READY 已存在 → 不重写，立即 exit 0
- **D** 过期 streak 丢弃：时间间隔过大 → 从 1 重新计数
- **E** deadline 上界（72h）：到期未达标 → 写 timeout 记录、exit 4、不降低标准、不启动训练
- **F** flock 单实例：第二个实例被拒绝 (exit 3)；fd 9 对子进程 close-on-exec，
      orphaned `sleep` 不持有锁（验证：holder 死亡后立即 restart rc=0）
- **G** TERM 信号 trap：reap 自己记录 PID 的 sleep 子进程，不留 orphan，不持有锁

**外部 compute 进程处理**：**仅记录**，从不 signal/renice/migrate，
任何发现都标记 NOT idle 并阻止启动。

### 13. M7：preflight + 正式启动（完成）

`launch_resume.py` 在 05:13:21 UTC 执行 **32/32 preflight checks PASS** 后，
用 `start_new_session=True` 启动 PID 2091229 / PGID 2091229。

**Preflight gates（任一失败 → 写 `m7_preflight_failed.json`、exit 2、启动零进程）**：
1. manifest 存在 + SHA `1c7ea6c8...` 不变 + mode `0o444` (immutable)
2. 11 个 key file SHA 全部匹配冻结记录（trainer `d0e4051bc86f8116...` 等）
3. git HEAD `c950303` 不变；tracked 改动 **只有** `train/train_terrastate_v2.py`
4. output dir `runs/resume11904_to14880/20260818_112933` **不存在**（trainer 会自己创建）
5. `--allow-existing-out` **缺失**（overwrite 保护 active）
6. `--future-state-scale 1.0`；`--nproc_per_node=8`（全 8 卡，非子集）
7. 六个 artifact 经 `tools/resolve_artifact.py` 重新解析，SHA256 全部 verified=True
   （包括两个 12GB path-registered cache，哈希耗时 ~80 秒但提供 provenance 保证）
8. 本用户无其他 `train_terrastate_v2` 进程（避免双写同一 output dir）
9. `m6_gpu_ready.json` 存在且 valid（consecutive_idle=10, n_gpu=8, bar 未被篡改）
10. **FRESH** nvidia-smi 查询（launcher 自己读，不依赖 watcher 的历史记录）：
    8 GPU 全部 idle（`g0..g7 = 4MiB/0%`），无 compute app

**Resume block 验证（log 13:15:05–13:15:06）**：
- `stage recomputed from schedule: recorded=2 -> 3` ← **B1 修复生效**
- `step 11904 epoch=31 micro=372 stage=3 best_val=0.31335`
- `stage 3 trainable q tensors = 12 (prefixes ['core.blocks.2.'])` ← **B6 断言通过**
- `parent sha256=644deaac0b1578cd data_order=exact`

**首次实际训练 update（step 11950, 13:20:33）**：
- `st3 lam_s_raw=0.0100 lam_s_effective=0.0100` ← STAGE3 late schedule 符合预期
- `fs_scale=1` ← 默认 1.0 正确传递
- `lr=2.89e-06` ← 从 warmup 末尾 cosine decay 阶段恢复

**首次 val（step 12000, 13:21:29）**：
- `future_state=0.31292 < best 0.31335` → 写入 `checkpoint_fsval_best.pt`
- GPU 利用率 65–97%，显存 12607 MiB/卡

训练正常进行中，目标 step 14,880。中位吞吐 ~1.34 it/s（log step 12000），
剩余 ~2,880 更新预计 35–40 分钟完成。

## 共享资源状态

**本任务启动的进程**（均已记录 PID/PGID，只管理自己创建的）：
- Watcher PID 2065448：已自行退出（写 READY 后正常结束）
- Trainer PID 2091229 / PGID 2091229：运行中（8×H200，12607 MiB/卡，65–97% util）

**未执行的操作**：未 kill/renice/migrate 任何非本任务进程；未 sudo；
未修改 MIG/clock/power/persistence；未用 GPU 子集；未修改 crontab；
未 push；`git add` 限定本任务修改的文件。
未删除、覆盖或移动任何历史权重或他人产物。


---

## M8 结论（已完成）

**Training completed at step 14,880 — 2026-08-18 13:58:46 UTC**

### 1. 训练过程摘要

- **启动时刻**: 2026-08-18 05:13:21 UTC = **13:13:21 本地 (CST, UTC+8)** (PID 2091229, PGID 2091229)
- **首条 resume 日志**: 13:15:05 本地(启动后 1m44s,期间做 cache verify + 模型加载)
- **完成时刻**: 13:58:46 **本地 (CST)** = 05:58:46 UTC
- **墙上时钟**: **~45min** (13:13:21 → 13:58:46 本地),resume 11904 → 14880 = 2976 updates
- **吞吐**: 1.07–1.52 it/s (median ~1.35 it/s)

> **修正记录**:本节初稿写"墙上时钟 ~8h45min",错误。原因是把启动时刻的 **UTC**
> (05:13:21) 与训练日志的**本地时间**戳 (13:58:46) 直接相减,混用了两个时区,虚增了 8 小时。
> 交叉验证 ~45min 才是对的:2976 updates ÷ 1.35 it/s ≈ 37min 纯计算,加 3 次 validation
> 与 checkpoint 落盘开销 ≈ 45min,与 M5 记录的吞吐估算(31.6min 纯计算)同量级。
- **验证点**: step 12000 (best_val=0.31292 改进), step 14000 (best_val=0.31288 改进), step 14880 (final best_val=0.31288)

### 2. 最终日志确认

来自 `m7_train.log` 最后一行：

```
[13:58:46] done step=14880 best_val=0.31288 teacher_unchanged=True stage3_qgrad_seen=True out=runs/resume11904_to14880/20260818_112933
```

**关键特征**:
- `done step=14880`: 正常完成，未超额更新（B3 fix 生效）
- `teacher_unchanged=True`: 整个训练期间 teacher 冻结
- `stage3_qgrad_seen=True`: stage-3 期间至少一个 q 参数产生了梯度（B6 sanity check）
- 输出目录未被覆盖（B4 fix 生效）

### 3. 输出 artifacts

```
runs/resume11904_to14880/20260818_112933/
├── checkpoint_last.pt           (step=14880, stage=3, candidate=last)
├── checkpoint_fsval_best.pt     (future_state_val best candidate)
├── checkpoint_step12000.pt      (periodic save)
├── checkpoint_step14000.pt      (periodic save)
└── loss_log.jsonl               (2976 entries: steps 11905–14880)
```

**无** `checkpoint_boundary80.pt` — parent 已保存，未重复写入（B2 fix 生效）。

### 4. 进程状态

训练进程 PID 2091229 已退出（exit code 0）。GPU watcher PID 2065448 已在 M6 完成后正常退出。

---

## M9 结论（已完成）

**Acceptance verification: 31/31 checks PASSED — 2026-08-18 15:0x 本地 (CST)**

### 1. 验收检查清单

运行：`verify_acceptance.py --compare-historical`

**所有 31 项检查通过**（初稿为 28 项；teacher 段的 2 项被替换为 4 项可falsify检查，
historical 段的 1 项被拆为 value/arch 2 项，详见 §2 与 §5 的修正记录）:

| ID | 检查项 | 结果 |
|---|---|---|
| 1 | output_dir_exists | ✓ |
| 2 | checkpoint_last_exists | ✓ |
| 3 | final_step_is_14880 | ✓ step=14880 |
| 4 | candidate_is_last | ✓ candidate=last |
| 5 | total_steps_14880 | ✓ |
| 6 | lineage_resumed_true | ✓ resumed=True |
| 7 | lineage_parent_step_11904 | ✓ parent_step=11904 |
| 8 | lineage_parent_sha256 | ✓ 644deaac0b1578cd... |
| 9 | lineage_data_order_exact | ✓ exact (DistributedSampler deterministic) |
| 10 | final_stage_is_3 | ✓ stage=3 |
| 11 | no_duplicate_boundary80 | ✓ (B2 fix) |
| 12 | loss_log_exists | ✓ |
| 13 | loss_log_count_2976 | ✓ 2976 = 14880 - 11904 |
| 14 | all_updates_stage_3 | ✓ all 2976 updates in stage 3 (B1 fix) |
| 15 | loss_log_first_step_11905 | ✓ |
| 16 | loss_log_last_step_14880 | ✓ |
| 17 | trainable_q_count_12 | ✓ 12 trainable q tensors (B6 fix) |
| 18 | trainable_q_all_core_blocks_2 | ✓ all prefixed `core.blocks.2.` |
| 19 | teacher_digest_parent_matches_child | ✓ parent(11904)=child(14880)=`bbe2c3ee6de540ae...` |
| 20 | teacher_path_divergence_explained | ✓ 两侧路径不同属设计预期（M1 重新发布进 artifact store） |
| 21 | teacher_artifact_content_addressed | ✓ 文件 sha256 == 文件名 == `2c5d084236716d84...` |
| 22 | trainer_asserted_teacher_unchanged | ✓ done 行 `teacher_unchanged=True` |
| 23 | optimizer_state_present | ✓ 42 param states |
| 24 | scheduler_state_present | ✓ last_epoch=14880 |
| 25 | scheduler_last_epoch_14880 | ✓ |
| 26 | best_val_finite | ✓ best_val=0.31288 |
| 27 | b4_state_dict_present | ✓ 255 model keys |
| 28 | expected_artifacts_present | ✓ {checkpoint_last.pt, loss_log.jsonl, checkpoint_fsval_best.pt} |
| 29 | no_forbidden_artifacts | ✓ no boundary80 duplicate |
| 30 | historical_bit_exact | ✓ **value_sha 相同且 max_abs_diff=0（255 张量逐字节相同）** |
| 31 | historical_arch_tag_matches | ✓ state_sha 相同（仅 arch tag，非权重证明） |

### 2. 比特级完全一致性（bit-exact）

对 255 个张量做**数值级**逐字节比对（`value_sha` = 按 key 排序后哈希张量原始字节）：

```
keys_equal                        = True   (255 == 255)
historical b4 value_sha           = aa98fbd2fa302727
resume     b4 value_sha           = aa98fbd2fa302727
max |historical - resume|         = 0.000e+00   (遍历全部 255 个张量)
--> BYTE-IDENTICAL
```

**RESUME WEIGHTS ARE BYTE-IDENTICAL TO HISTORICAL**（provenance 不同：路径/lineage/时间戳）

这证明：
- B1 fix（stage 重计算）完全修复了原始 bug
- 数据顺序恢复（exact）成功
- optimizer/scheduler 状态正确加载
- 整个训练轨迹与未中断的参考运行完全一致

> **修正记录**:本节初稿把 `state_sha`（=`d050ea390d4cc815`）当作"比特级一致"的证据,
> **该证据无效**。`state_sha` 只哈希 `dtype/shape/stride`,**完全不含张量数值**——两个权重
> 截然不同但架构相同的 checkpoint 会得到同一个 `state_sha`。它只能当 arch tag(现列为第 31
> 项),不能证明权重相等。补做数值级比对后,结论(byte-identical)本身**成立且更强**:
> `value_sha` 相同且 max abs diff = 0。`verify_acceptance.py` 已新增 `value_sha()`,并在
> `state_sha()` docstring 中写明该局限,防止后续复用时再次误用。

### 3. Lineage provenance (B5)

```json
{
  "resumed": true,
  "parent_path": "/csy-mix02/.../checkpoint_boundary80.pt",
  "parent_file_sha256": "644deaac0b1578cd...",
  "parent_step": 11904,
  "parent_epoch": 31,
  "parent_micro_in_epoch": 372,
  "parent_stage_recorded": 2,
  "parent_b4_state_sha256": "86e5b36a01f7da43",
  "resume_stage_applied": 3,
  "data_order_restoration": "exact: DistributedSampler(seed, epoch) fully determines the shard assignment and shuffle..."
}
```

完整的父子链记录（B5 fix 生效）。

### 4. Stage-3 q-gradient 断言（B6）

- **trainable_q**: 12 个参数，全部前缀为 `core.blocks.2.*`
- **frozen**: 211 个其他 q 参数保持冻结
- **与 parent q_freeze 记录一致**: unfreeze_prefixes = `["core.blocks.2."]`
- 所有 2976 个 updates 均在 stage=3 执行（B1 stage 重计算生效）

### 5. Teacher 冻结验证（三个互相独立的证人）

| 证人 | 内容 | 为何独立 |
|---|---|---|
| (a) parent↔child digest | parent(11904) 与 child(14880) 记录的 `teacher_sha256` 同为 `bbe2c3ee6de540ae...` | parent checkpoint 由**原始 run** 在本任务存在之前写入，是外部证人 |
| (b) 内容寻址完整性 | 本次实际加载的 teacher 文件 sha256 == 其文件名 == `2c5d084236716d84...` | 内容寻址存储：文件名即内容摘要，改动即暴露 |
| (c) trainer 运行时断言 | done 行 `teacher_unchanged=True`（trainer 自己在训练结束时比对 teacher state） | 由 trainer 在 GPU 上实测，非事后推断 |

注：parent 与 child 的 `teacher_b4_path` **不同**（parent 指向
`WorldModel2026-planb/checkpoints/plan_b_b4a/checkpoint_best.pt`，child 指向 M1 发布后的
content-addressed 副本）。这是 M1 重新发布造成的**预期差异**，所以路径相等不是有效的
同一性判据；(a) 的张量摘要相等才是。

> **修正记录**:本节的检查我改过两轮,前一轮改错了,现已纠正。
> - 原始检查 `teacher_sha256_unchanged` 拿 `teacher_sha256`(16-hex,`state_sha` 出的**张量
>   元数据摘要**)去比 `2c5d0842...`(64-hex,**文件** sha256)。两者是**不同种类的对象**,
>   永不可能相等——所以它报 FAIL 是**本脚本自身的 bug**,不代表 teacher 变了。
> - 我第一轮"修复"时,把从**被验证对象自身**读出的 `bbe2c3ee...` 写成期望值,变成**循环
>   论证**:该检查在任何情况下都会通过,零证明力。这是比原 bug 更糟的改法。
> - 现改为上表三个独立证人,每一项都可能失败(可falsify)。

### 6. 无重写/无覆盖（B4）

- 输出目录 `runs/resume11904_to14880/20260818_112933/` 在启动前不存在
- `--allow-existing-out` 未使用
- 历史参考 checkpoint `WorldModel2026-planb-v2train/runs/terrastate_v2/run1/checkpoint_last.pt` 保持只读，未被触碰

### 7. 报告文件

所有验收结果写入：
- `m9_acceptance_report.json` (31 checks, accepted=True)
- checkpoint SHA256: `checkpoint_last.pt` 文件摘要已记录
- `verify_acceptance.py` 本轮共 3 处改动（均为**验证脚本**改动，未触碰训练产物）：
  1. `torch.load(..., weights_only=False)`（torch 2.12 默认 `weights_only=True`，checkpoint 含
     numpy 标量，反序列化被拒；训练侧 `train_terrastate_v2.py` 一直显式传 `False`，故 M8 未受影响）
  2. teacher 检查 → 三个独立证人（见 §5 修正记录）
  3. 新增 `value_sha()` 做数值级 bit-exact 证明（见 §2 修正记录）

---

## 最终状态

**所有里程碑 M0–M10 完成。**

| Milestone | Status |
|---|---|
| M0–M5 | DONE |
| M6 (GPU watcher) | DONE |
| M7 (launch) | DONE |
| M8 (training) | DONE |
| M9 (acceptance) | DONE |
| M10 (register anchor) | **DONE**（在 `ops/e0_q1q2q3_11904_vs_14880/20260818_154859/` 执行） |

> 修正记录：此表原记 `M10 TODO`，是写表时 M10 尚未执行；M10 已于同日在 E0 ops 目录
> 完成（对象 `a5d2a0cc…` mode 0444、registry `ebc374b34b2e818a` → `a7fd2763935a26d1`、
> alias 已建、三个 ID 全部 rc=0 且 `sha256_verified=True`），故更正。

**Exact resume 11,904 → 14,880 验证成功**:
- 比特级与历史 checkpoint 一致
- 所有 6 个 resume bugs (B1–B6) 修复并验证
- Lineage / stage / teacher / q-freeze / 无重写 / 无超额更新 全部符合预期

M10（已完成）：`checkpoint_last.pt` 已发布为 `terrastate/v2/verified-resume14880@v1`
（对象 `a5d2a0cc…`，mode 0444，copy-only，源文件保留），并由 alias
`terrastate/v2/default-training-anchor` 指向它。

下一步不在本 ops 目录：11,904 vs verified 14,880 的同协议 Q1/Q2/Q3 正式评测，
状态见 `ops/e0_q1q2q3_11904_vs_14880/20260818_154859/STATUS.md`
（当前 `WAITING_FOR_SHARED_GPU`，六项正式任务 `NOT_STARTED`）。
