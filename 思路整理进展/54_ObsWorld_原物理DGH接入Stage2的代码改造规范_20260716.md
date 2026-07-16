---
title: ObsWorld 原物理 DGH 接入 Stage2 的代码改造规范
aliases:
  - physical4 Stage2 实现指导
  - 原版 DGH 无破坏接入方案
tags:
  - ObsWorld
  - DGH
  - Stage2
  - 代码改造
  - 向后兼容
created: 2026-07-16
status: physical4_v1 已实现｜full24 保持兼容｜执行命令见 55
related:
  - "[[47_ObsWorld_Stage2正式代码技术指导与实现规范_20260716]]"
  - "[[51_ObsWorld_DGH字段构造与使用规范_20260716]]"
  - "[[53_ObsWorld_DGH主方案选择与AAAI整体实验安排_20260716]]"
---

# 54. ObsWorld 原物理 DGH 接入 Stage2 的代码改造规范

> [!abstract] 本文档解决什么问题
> 当前 Stage2-v2 的 full24 Direct/Rollout/Partition 路径已经代码就绪。后续需要把原物理 DGH 接入同一套世界模型，但必须采用 additive change（新增式改造）：新增协议、配置和统计文件，**绝不覆盖或悄悄改变 full24 的字段、归一化、训练逻辑、checkpoint 或输出目录。**

> [!note] 实现状态更新（2026-07-16）
> 本文原先的改造规划已经落实。`physical4_v1` 已接入数据加载、统计、模型工厂、preflight 和 Direct/Rollout/Partition 配置；请用 [[55_ObsWorld_原版DGH正式训练代码完成与训前命令指南_20260716]] 执行，不再把本文中的“尚未修改代码”理解为当前状态。

> [!important] 当前操作结论
> 可以先运行现有 full24。后续 physical4 代码合并不会影响已经启动的远端进程；但训练服务器在该进程结束前不要执行 `git pull`、不要重启 DataLoader/作业，也不要用新代码恢复旧进程。任何后续恢复必须使用与 checkpoint 记录的 commit、resolved config（解析后的完整配置）、driver protocol（驱动协议）和 stats SHA 完全匹配的代码与产物。

---

## 1. 当前 full24 到底能不能运行

当前已经具备：

- `earthnet2021x_path_v2` 数据路径；
- `D_path [30,24]`、`C_path [30,2]`、`G` 和 `delta_t_path`；
- Direct24、Rollout24、Partition24；
- checkpoint/resume（检查点/恢复）和预测来源保护；
- launcher（启动器）和 preflight（训练前检查）；
- 合成与单元测试。

因此 full24 是 code-ready（代码就绪）的，但正式训练不是“零准备启动”。以下四项仍是启动硬条件：

1. `train_dev` 与 `val_dev` 正式 manifest；
2. 与 train manifest 绑定的 full24 `conditioning_stats_v2`；
3. 真实数据 preflight 通过；
4. Stage1.5 checkpoint 的精确路径与可加载结构。

满足这些条件后，可以先运行：

```text
configs/train/stage2_earthnet_v2_direct24.yaml
configs/train/stage2_earthnet_v2_rollout24.yaml
configs/train/stage2_earthnet_v2_partition24.yaml
```

这三份现有配置在 physical4 开发中必须保持字节级语义不变；若确需通用重构，必须用 resolved-config 快照与回归测试证明 full24 输出契约没有变化。

---

## 2. 无破坏改造的六条硬规则

1. **默认值不变**：未填写 `driver_protocol` 时仍走当前 `full24`；
2. **旧配置不改**：三个 `*24.yaml` 不修改为 physical4，也不复用其输出目录；
3. **统计量隔离**：full24 与 physical4 使用不同 schema、文件名和 SHA；
4. **checkpoint 隔离**：不同 driver protocol 或输入维度禁止互相 resume；
5. **训练拓扑不变**：A/C 共享同一 `I/F/H`、rollout curriculum、loss、G/C/Δt 和 evaluator；
6. **验证器不放松**：不能为了支持 4-D，把当前“必须是 24-D”的保护简单删除；应新增带显式协议的验证分支。

---

## 3. physical4 的正式数据契约

建议协议唯一名称为：

```text
physical4_v1
```

正式 batch 为：

| 字段 | Shape | 说明 |
|---|---|---|
| `D_path` | `[B,30,4]` | 原物理四天气路径 |
| `D_mask` | `[B,30,4]` | 四字段有效性 |
| `D_valid_day_count` | `[B,30,4]` | 审计用，不进模型 |
| `C_path` | `[B,30,2]` | 与 full24 完全相同 |
| `delta_t_path` | `[B,30]` | 与 full24 完全相同 |
| `G/G_mask` | `[B,1,128,128]` | 同一个标准化 `cop_dem` |
| `h` | `[B,20]` | 同一个 5–100 天网格 |

唯一字段顺序：

```text
PHYSICAL4_FEATURE_NAMES = (
    "precip_sum_5d",
    "temp_mean_5d",
    "vpd_mean_5d",
    "srad_sum_5d",
)
```

### 3.1 VPD 的固定公式

建议以日均温 `T`（摄氏度）和日相对湿度 `RH`（百分比）计算：

$$
e_s(T)=0.6108\exp\left(\frac{17.27T}{T+237.3}\right),
$$

$$
VPD=\max\left(0,e_s(T)\left(1-\frac{RH}{100}\right)\right)\quad\text{kPa}.
$$

实现前必须审计 NetCDF 中 `tg/hu` 的单位；正式模式禁止靠数值范围自动猜单位。公式名称、常数、单位、裁剪分位和代码版本写入 stats JSON。

### 3.2 五日缺失处理

为了忠实保留 42 号方案，第一版建议：

- 降水：五个 `rr` 日值均有限才有效；
- 温度：五个 `tg` 日值均有限才有效；
- VPD：五天的 `tg` 和 `hu` 均成对有限才有效；
- 辐射：五个 `qq` 日值均有限才有效；
- 无效字段写 0，同时 `D_mask=0`，禁止把 0 当真实物理值；
- preflight 必须报告每字段 all-five-valid coverage（五天全有效覆盖率）。

这与当前 full24 的 skip-NaN（跳过缺失日）政策不同，因此 A/C 被解释为“完整条件包比较”，不是只改变变量数的纯删除消融。如果真实覆盖率不足，先在 `train_dev` 审计并形成书面决议，禁止训练时临时改规则。

---

## 4. 建议新增和修改的文件

### 4.1 新增文件

| 文件 | 作用 |
|---|---|
| `data/earthnet_physical_conditioning.py` | physical4 唯一字段、VPD、五日聚合、mask 与 schema |
| `scripts/build_earthnet_physical_stats.py` | 只用 frozen train manifest 计算转换、裁剪、标准化和 G 统计量 |
| `configs/train/stage2_earthnet_v2_direct_physical4.yaml` | 继承 Direct24，仅覆盖驱动协议、输入维度和输出目录 |
| `configs/train/stage2_earthnet_v2_rollout_physical4.yaml` | 继承 physical Direct，再覆盖 rollout mode |
| `configs/train/stage2_earthnet_v2_partition_physical4.yaml` | 继承 physical Rollout，再开启 partition |
| `tests/test_earthnet_physical_conditioning.py` | 公式、单位、聚合、缺失、顺序与统计量测试 |
| `tests/test_stage2_physical4_contract.py` | `[30,4]` batch 和泄漏边界 |
| `tests/test_obsworld_physical4_factory.py` | Direct/Rollout/Partition 创建与前向测试 |
| `tests/test_stage2_driver_protocol_isolation.py` | A/C 配置、统计量、checkpoint 不可混用 |

### 4.2 必须小心扩展的现有文件

| 文件 | 所需改动 | 不允许的改动 |
|---|---|---|
| `data/datasets/earthnet2021.py` | 根据显式 `data.driver_protocol` 选择 full24 或 physical4 builder | 不改变未设置协议时的 full24 输出 |
| `data/stage2_contract.py` | 新增 protocol-aware（协议感知）验证入口 | 不把当前固定 24-D 检查改成任意维度放行 |
| `train/train_stage2_earthnet.py` | factory、coverage 日志、preflight 与 provenance 读取显式 driver spec | 不以张量维度猜协议 |
| `scripts/preflight_stage2_earthnet.py` | 按协议检查字段名、覆盖率、stats SHA 和模型 input dim | 不让 physical stats 通过 full24 配置 |
| `train/stage2_provenance.py` | 保存 `driver_protocol/feature_names/stats_sha/formula_version` | 不允许缺字段的旧 sidecar 被标记为正式 |
| `models/dynamics/*` | 允许显式 expected driver dim，默认仍为 24 | 不修改共享转移的状态逻辑、G/C/Δt 或 loss |
| `run_stage2_earthnet.sh` | 原则上无需新增参数；配置和 stats 路径已足够 | 不新增会覆盖 driver protocol 的隐式环境变量 |

---

## 5. 配置继承方式

physical Direct 配置应从当前 Direct24 继承，只覆盖必要字段：

```yaml
_base_: stage2_earthnet_v2_direct24.yaml

protocol:
  driver_protocol: physical4_v1
  d_feature_names:
    - precip_sum_5d
    - temp_mean_5d
    - vpd_mean_5d
    - srad_sum_5d

model:
  driver_protocol: physical4_v1
  forecast_mode: direct_path_physical4
  interval_driver_encoder:
    input_dim: 4

data:
  driver_protocol: physical4_v1
  conditioning_stats_path: null

checkpoint_dir: /csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_earthnet_v2_direct_physical4
log_dir: /csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs/stage2_earthnet_v2_direct_physical4
```

其余字段不得重复抄写，避免以后 Direct24 与 physical Direct 在解码器、优化器或训练预算上静默分叉。Rollout/Partition 继续使用 `_base_` 逐层继承。

---

## 6. 统计文件设计

不得把 physical4 写入现有 full24 `conditioning_stats_v2` 后冒充同一 schema。建议使用：

```text
conditioning_stats_physical4_v1_train_dev.json
```

最低内容：

```text
schema_version
dataset
fit_split
driver_protocol
feature_names
manifest_path
manifest_sha256
num_files
raw_variable_names_and_units
vpd_formula_version
vpd_clip_quantile_and_value
feature_transform
feature_mean/std
g_variable
g_mean/std
missingness_policy
git_commit
```

统计顺序必须是：

1. 从 frozen train manifest 读取原始逐日值；
2. 明确完成单位转换；
3. 构造五日物理字段；
4. 仅用训练集拟合 VPD 裁剪点和各字段 mean/std；
5. 保存 manifest SHA 与代码版本；
6. val/IID/OOD 只加载，不重新估计。

---

## 7. 模型和训练逻辑哪些保持不变

physical4 只改变 `IntervalDriverEncoder.input_dim: 24 → 4` 和相应数据内容。以下全部保持一致：

- Stage1.5 checkpoint 与状态初始化；
- context 10 帧、future 20 帧；
- 第 10 个 D token 是第一个未来五日区间；
- C、G、H/Δt；
- `IntervalDriverEncoder` 输出宽度 32；
- `ControlledTransition` 的输入输出状态维度；
- Direct 的 horizon 分层采样；
- Rollout 的 2→4→8→12→20 课程；
- Partition 的 10 天 vs 5+5 天逻辑；
- RGBN/NDVI loss；
- optimizer、训练步数、batch 与随机种子；
- evaluator 与预测导出；
- 后续 observation correction 的 `I-F-H-U` 状态机。

因此 A/C 的比较不会变成两套不同世界模型。

---

## 8. checkpoint 与恢复保护

每个正式 checkpoint 必须保存：

```text
driver_protocol
d_feature_names
d_input_dim
conditioning_stats_sha256
manifest_sha256
resolved_config_sha256
git_commit
```

恢复时任何一项不一致必须停止。特别禁止：

- 用 full24 checkpoint 恢复 physical4；
- 用 physical4 checkpoint 恢复 full24；
- 仅因 `IntervalDriverEncoder.out_dim` 都是 32 就认为可兼容；
- 使用同名输出目录覆盖另一协议；
- 把 full24 的 24-D 权重切片后称为 physical4 预训练。

Stage1.5 checkpoint 不含 DGH 编码器，可以由 A/C 共同使用；这与 Stage2 checkpoint 不兼容是两回事。

---

## 9. 单元测试与验收条件

### 9.1 physical4 自身测试

- [ ] 固定输入下四字段值与手算一致；
- [ ] VPD 公式、摄氏度和百分比单位一致；
- [ ] 相对湿度 100% 时 VPD 接近 0；
- [ ] 降水/辐射只保留 sum，不额外产生 mean；
- [ ] 任一天缺失时对应字段 mask 为 0；
- [ ] 日历仍是单独 `[30,2]`；
- [ ] 第 10 个路径 token 驱动第一个未来目标；
- [ ] 目标和官方评估 mask 不能进入模型；
- [ ] Direct/Rollout/Partition 均能 forward/backward/save/resume。

### 9.2 full24 非回归测试

- [ ] 现有 full24 测试一项不少地通过；
- [ ] 旧 yaml 解析后的 driver protocol 仍为 full24；
- [ ] 同一合成 full24 输入在改造前后输出逐项一致（固定权重/随机种子）；
- [ ] 当前 24-D stats 仍被严格验证；
- [ ] `D_path` 仍为 `[B,30,24]`；
- [ ] `forecast_mode` 与现有训练分发不变；
- [ ] 旧 full24 checkpoint 能在相同配置恢复；
- [ ] full24 与 physical4 交叉恢复均被拒绝。

只有两组测试都通过，才允许把 physical4 代码合并到 main。

---

## 10. 推荐代码实施顺序

### Commit P1：纯字段模块

新增 physical4 字段、VPD 和单元测试；不连接 Dataset/Trainer。此时 full24 行为完全不变。

### Commit P2：独立统计脚本

生成 physical stats schema，并用小型合成 NetCDF 测试单位、manifest SHA 和 train-only 限制。

### Commit P3：Dataset 显式分流

只有 `data.driver_protocol=physical4_v1` 才返回 `[30,4]`；缺省和现有配置继续 `[30,24]`。

### Commit P4：协议感知验证与 provenance

让 preflight、checkpoint 和 evaluator 明确知道协议，交叉使用立即报错。

### Commit P5：模型工厂与三个新配置

创建 physical Direct/Rollout/Partition，保持共享输出宽度和训练拓扑。

### Commit P6：完整回归与 32-cube sanity

先跑所有 CPU 测试，再分别做 full24 与 physical4 的小样本 forward/backward；最后才启动 physical4 GPU 训练。

这个顺序确保任何中间提交都不会把未完成 physical4 误当成正式路径，同时 full24 始终可用。

---

## 11. 与当前 full24 训练并行时的操作规则

### 情况 A：full24 正在另一台服务器/另一个已拉取工作区运行

可以在当前项目继续开发并推送 physical4。远端训练不会自动读取 GitHub 新代码。训练结束前不要在该远端工作区执行 `git pull`。

### 情况 B：full24 与代码开发位于同一个工作区

不建议训练过程中修改或拉取文件。虽然 Python 通常在启动时加载模块，但 DataLoader worker 重启、评估子进程和作业恢复可能重新读取代码。应使用独立 git worktree（工作树）或等当前作业结束。

### 情况 C：需要恢复 full24 checkpoint

使用 checkpoint 记录的 commit 和 resolved config 恢复。不要直接使用最新 main，除非非回归测试和 provenance 检查证明完全兼容。

---

## 12. 未来启动命令骨架

当前 full24 和未来 physical4 应使用相同 launcher，仅配置、统计量和输出目录不同：

```bash
CONFIG=configs/train/stage2_earthnet_v2_rollout_physical4.yaml \
CONDITIONING_STATS_PATH=/path/to/conditioning_stats_physical4_v1_train_dev.json \
MANIFEST_PATH=/path/to/train_dev.json \
VALIDATION_MANIFEST_PATH=/path/to/val_dev.json \
STAGE15_CHECKPOINT=/path/to/checkpoint_step_x.pt \
CHECKPOINT_DIR=/path/to/stage2_rollout_physical4 \
LOG_DIR=/path/to/logs/stage2_rollout_physical4 \
REQUIRE_MANIFEST=1 \
bash run_stage2_earthnet.sh
```

这是后续实现完成后的命令骨架，不表示 physical4 当前已经能运行。当前 full24 与 physical4 配置都已具备代码级运行路径；正式 physical4 训练仍必须先生成与 train manifest 绑定的统计量并通过 preflight。

---

## 13. 完成定义

physical4 接入只有同时满足以下条件才算完成：

1. 字段数值、单位、VPD、缺失和统计量经过测试；
2. full24 的解析配置、张量和固定输入输出不发生变化；
3. A/C stats、checkpoint、日志和预测产物完全隔离；
4. physical Direct/Rollout/Partition 均通过 32-cube 过拟合；
5. preflight 能打印协议、字段顺序、覆盖率和 SHA；
6. 同一 Stage1.5 初始化可分别启动 A/C；
7. 交叉 resume 和错误 stats 会硬失败；
8. A 进入现有 Stage2/校正主线，不创建独立论文任务。

> [!summary] 最终原则
> 先跑 full24 不会把文章锁死在 full24；新增 physical4 也不应改变 full24。两者应像同一模型的两个明确配置一样共存：共享世界模型、训练器和评估器，隔离字段协议、统计量与 checkpoint。最终只由 `val_dev` 锁定一个进入论文主结果。
