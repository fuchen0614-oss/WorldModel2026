# 57 ObsWorld Stage2：下一步建议与 physical4 / full24 NAS 启动调查

> 调查日期：2026-07-17  
> 范围：只做代码与已有运行证据的审计；**本文件不修改训练代码，也不要求中断当前 physical4 正式 run。**

## 1. 结论先行

当前应让正在运行的 `physical4_v1`、8 卡、B64、200 epoch 本机盘暂存实验自然完成。
它是 A（紧凑物理驱动）主方案的首个正式 Direct 主实验。

训练结束后的下一条高价值工作线，不是立刻扩展 rollout、partition 或更多消融，而是建立和它严格配对的
C（`full24` / Direct24）基线：使用同一 Stage1.5 初始化、同一 `train_dev` / `val_dev`、同一 8 卡 B64、同一 200 epoch、同一验证和 checkpoint 策略。这样才能回答最基础也最重要的问题：四个物理聚合驱动是否足够，还是完整 24 维 E-OBS 驱动有可重复收益。

对用户此前观察到的“`sleep 20` 后 `read_bytes` 不增长”现象，结论如下：

1. 早期 physical4 preflight 的确曾卡在对冻结 manifest 中每个路径执行 `Path.resolve()` 的共享盘元数据查询；这会表现为 CPU 很低、`read_bytes` 短时间不增长、堆栈停在 `earthnet_manifest.py`。
2. 该问题不是 physical4 专属。Direct24 / full24 与 physical4 共用同一个 manifest loader，因此旧代码下也会有同类风险。
3. 当前代码已经在两条训练线共同的入口修复了它：preflight 与正式训练均关闭“逐条文件存在性验证”，只保留 JSON digest、相对路径安全性和实际抽样读取。
4. 仍有两个**下一轮应一起修复**的公共工程点：本机暂存的容量下限，以及官方评估的 manifest 逐条存在性验证。二者都同时影响 physical4 和 full24。

## 2. A / C 两条线在论文中的角色

| 代码/实验线 | 驱动 | 角色 | 当前状态 |
|---|---|---|---|
| A：Direct physical4 | 4 维物理五日聚合（降水、温度、VPD、辐射） | 优先主方案 | 当前正在进行首个 8×H200、B64、200 epoch 本机盘正式 run |
| C：Direct24 / full24 | 8 个 E-OBS 字段 × 3 聚合 = 24 维 | 配对完整字段基线 | 数据协议和 train-only stats 已有；尚未用与 A 对齐的 H200 正式配置运行 |
| Rollout / Partition | 在 A 或 C 的 Direct 成立后验证递推、组合性 | 后续机制证据 | 不应抢在 A/C Direct 可比结论之前占用主算力 |

`earthnet2021x_standard_v1` 下的 full24 产物已经存在：

```text
train_dev.json                         22,847 files
val_dev.json                              969 files
conditioning_stats_v2_train_dev.json  train-only / full24
```

其中 `train_dev.json` 的 digest 为
`c2cf69d7f57f302c2a4e8b6c7453c537031f56ae7c4ccf1d8ae6e988fff53147`，与当前
physical4 统计文件记录的训练清单 digest 相同。因此 A/C 的训练总体可以做到数据人群严格配对；不能把 physical4 的 stats 文件误用于 full24，反之亦然。

## 3. “sleep 20 后 I/O 不动”调查

### 3.1 历史根因

此前用户在服务器运行 `preflight_stage2_earthnet.py` 时，进程长时间停留在：

```text
pathlib.Path.resolve()
data/earthnet_manifest.py::load_manifest_files()
EarthNet2021Dataset.__init__()
```

在共享 NAS 上，对 22,847 个 manifest 记录逐条 `resolve()` 会触发大量路径遍历和元数据查询。它未必读取 NetCDF 的文件内容，所以只比较两次 `/proc/<pid>/io` 的 `read_bytes`，即使相隔 20 秒也可能没有变化。这是元数据等待，不等价于 Python 死锁。

### 3.2 当前修复为何同时覆盖 physical4 与 full24

`1514c6a`（`Speed up manifest-backed preflight on NAS`）将 loader 改为：只有在确实要求文件存在性、大小或哈希验证时，才对单个记录调用 `Path.resolve()`；快速路径只把已经做过安全校验的相对路径拼接到 dataset root。

关键事实：

| 入口 | 当前行为 | 对 physical4 | 对 Direct24 / full24 |
|---|---|---|---|
| `scripts/preflight_stage2_earthnet.py` | 强制 `verify_manifest_exists=false`，随后只真正打开 `PREFLIGHT_MAX_FILES` 个样本 | 已覆盖 | 已覆盖 |
| `stage2_earthnet_v2_direct24.yaml` | 固定 `verify_manifest_exists: false`、size/hash 也为 false | physical4 从它继承 | 已覆盖 |
| `stage2_earthnet_v2_direct_physical4.yaml` | `_base_: stage2_earthnet_v2_direct24.yaml`，因此继承上述 manifest 快路径 | 已覆盖 | 不改变 Direct24 |
| `EarthNet2021Dataset` | 两条线都调用同一个 `load_manifest_files()` | 相同代码路径 | 相同代码路径 |

本次调查还重新执行了 manifest / launcher / full24 stats / physical4 stats 的相关测试：

```text
14 passed, 1 known NumPy binary-compatibility warning
```

因此，**当前的正式训练启动和 16-file preflight 不应再因为全 manifest 的 `Path.resolve()` 而重复出现原始的停滞。**

### 3.3 为什么单看父进程 `read_bytes` 仍可能误判

不同阶段由不同进程实际读取数据：

| 阶段 | 真正执行 I/O 的进程 | 父训练/控制进程 `read_bytes` 不涨是否正常 |
|---|---|---|
| preflight manifest 快路径 | 主要是 Python 解析 JSON 和少量样本读取 | 可以短暂不涨；应看日志和抽样样本是否推进 |
| full24 / physical4 全量 stats | `ProcessPoolExecutor` 的子进程（`--workers > 1` 时） | 正常，父进程主要做确定性归约 |
| DDP 训练 | 每个 rank 的 DataLoader worker | 正常，rank 父进程大部分时间等待 batch 或 GPU |
| 本机 rsync 暂存 | `rsync` 子进程 | 正常，launcher bash 几乎不读数据 |

所以今后若怀疑“卡住”，不要只查看一个父 PID。先在服务器执行下面的只读检查：

```bash
PID=<可疑父进程PID>

ps -p "$PID" -o pid,etime,stat,wchan:32,%cpu,%mem,rss,cmd
ps --ppid "$PID" -o pid,etime,stat,wchan:32,%cpu,%mem,rss,cmd

cat /proc/$PID/io | grep -E 'read_bytes|write_bytes'
sleep 20
cat /proc/$PID/io | grep -E 'read_bytes|write_bytes'
```

若存在子进程，应对实际 `python` worker、`rsync` 或 DataLoader worker 重复检查，而不是仅凭 launcher / torchrun 父进程下结论。若预检超过合理时间且没有打印 `v2 preflight scanned ...`，再采集 Python stack；不要在正式训练过程中对所有 rank 使用侵入式 `strace`。

## 4. 当前 local staging 的真实含义与容量风险

当前运行日志证明 staging 正在复制完整 `earthnet2021x` 树：

```text
source_nc_files = 40,075
rsync 已复制约 159 GB 时仍显示约 95%
```

这不是重复复制，也不是错误数据；当前脚本有意复制 `train/iid/ood/extreme/seasonal` 五个 split，确保训练后可以在同一本地目录完成验证/后续评估。`rsync --info=progress2` 使用增量目录扫描，`ir-chk=<remaining>/<currently-discovered>` 的分母会变化，因此百分比可能短暂回落，不能把它当作固定文件总数。

不过这揭示出一个真实的可靠性问题：当前 launcher 的默认
`MIN_LOCAL_FREE_GB=140` 小于这次实际复制规模的保守估计（约 160–170 GB）。本次节点 `/tmp` 有约 354 GB 可用空间，所以**当前 run 安全，不需要中断**；但下一次运行不能再把 140 GB 当作足够的通用门槛。

## 5. 尚未修复、但应同时覆盖 A/C 的问题

### P0：local staging 容量 gate

建议下一轮把 `MIN_LOCAL_FREE_GB` 从固定的 140 改成以下二者之一：

1. 对当前 EarthNet2021x 节点保守固定为至少 200 GB；或
2. 在启动前计算/缓存 source tree 的逻辑大小，再加明确的安全余量（例如 20–30 GB）。

设计要求：容量检查只读、不会删除共享源；失败时在 rsync 前退出；physical4 和 full24 都走同一 launcher。

### P0：官方评估入口仍逐条验证 manifest 路径

`eval/eval_greenearthnet_official.py` 当前调用 `load_manifest_files(..., verify_exists=True)`。这会在评估开始前再次对每条目标路径进行 NAS 元数据查询，故 full24 和 physical4 的评估都可能重现“长时间无 `read_bytes` 增长”的表象。

建议下一轮设计为：

- 正式 manifest 的 JSON digest、路径安全性仍强制检查；
- 将“每条 target 文件在启动前 `stat`”改为显式 opt-in 审计选项，或在 local staged root 下执行；
- scoring 过程本身仍会打开每个 target/prediction，缺失文件仍必须硬失败；
- 为两条协议各加一条回归测试，证明 fast manifest mode 不会绕过实际评分时的缺失文件检查。

这不是降低科学可复现性，而是删除一次冗余的 NAS 元数据全扫描。

### P1：为 Direct24 增加不污染基线的 H200 配对配置

不要直接改写 `stage2_earthnet_v2_direct24.yaml` 的既有默认值。建议新增一个派生配置（例如 `stage2_earthnet_v2_direct24_h200_paired.yaml`），只覆盖：

- 8 GPU × B64；
- worker / prefetch / persistent worker；
- GPU-side context resize、TF32 和 cuDNN performance 开关；
- 8,800 step / 200 epoch；
- 1000-step、epoch100/150/200、best checkpoint 的同一保存策略；
- 独立的 full24 checkpoint / log 输出目录。

`scripts/run_stage2_earthnet_local_staged.sh` 已经通过环境变量接收任意 `CONFIG`，所以不必为 Direct24 再写一份不安全的复制/清理脚本；只需传入 full24 的 stats 与同一对 manifest。

### P2：选择性暂存（可选优化）

当前 launcher 为完整五 split 复制，优点是一次复制后可直接评估，缺点是启动时间和本机盘占用更大。以后可以考虑按运行角色暂存：训练阶段只复制 `train + val`，官方 `iid/ood/extreme/seasonal` 评测时再按需要暂存。该优化应等待 P0/P1 完成后再做，因为它会增加生命周期和实验来源管理复杂度。

## 6. 推荐的项目执行顺序

### 当前 physical4 run 期间

1. 不改代码、不启动另一个 8 卡作业。
2. 等 staging 完成，确认日志出现 `local staging verified` 和 `training process-group leader PID`。
3. 关注每 50 step 的 `loss`、`data`、`gpu_compute`、`throughput`；在第一次验证（step 1000）确认 `val_dev` 指标和 `checkpoint_best.pt` 是否正常产生。

### physical4 run 完成后

1. 从 `val_dev` 选择 best checkpoint，而不是盲目以 epoch200 为最终模型。
2. 运行冻结的 IID / OOD（及补充 extreme / seasonal）评估，生成 A 的主表原始结果与 provenance。
3. 再实施本文件第 5 节 P0/P1 的小改动，并用 B64、8 卡、100 step 的 **full24 local-staged pilot** 验证：显存、loss、DataLoader timing 和 manifest 快路径。
4. pilot 通过后，启动 Direct24/full24 的配对 200 epoch run。
5. A/C Direct 都有正式结果后，再决定是否值得投入 rollout、partition、D intervention 与多 seed。

这个顺序把“工程是否能稳定运行”“四维物理驱动是否足够”“世界模型递推是否有额外价值”拆成可判定的三步，避免在还没有 A/C 对照前提前消耗大量 8×H200 算力。

## 7. 本次调查的边界

本次没有修改以下任何代码或运行状态：

- 没有中断当前 rsync、本机暂存或 physical4 训练；
- 没有更改 physical4 / Direct24 的模型、损失、学习率或数据协议；
- 没有删除 checkpoint、日志、manifest 或共享数据；
- 没有宣称 full24 已完成正式训练或任何模型优于另一个模型。

下一次代码改动应以本文件第 5 节 P0/P1 为独立、可测试的提交，并且要同时对 physical4 与 full24 做回归验证。
