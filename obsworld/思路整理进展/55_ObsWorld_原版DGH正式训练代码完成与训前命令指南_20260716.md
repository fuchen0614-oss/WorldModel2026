---
title: ObsWorld 原版 DGH 正式训练代码完成与训前命令指南
created: 2026-07-16
status: physical4_v1 代码已完成｜等待服务器真实数据审计和正式训练
related:
  - "[[42_ObsWorld_DGH字段详细设计与落实思路_最终版]]"
  - "[[47_ObsWorld_Stage2正式代码技术指导与实现规范_20260716]]"
  - "[[48_ObsWorld_EarthNet2021x统一数据协议与主实验规范_20260716]]"
  - "[[54_ObsWorld_原物理DGH接入Stage2的代码改造规范_20260716]]"
---

# 55. 这次工作的结论

本次已经把**原版物理 DGH**接入当前的 EarthNet2021x `earthnet2021x_path_v2` 世界模型路径，正式协议名称为 `physical4_v1`。这里的 `4` 指四个天气字段，不是把世界模型改成了另一个任务。

- 原版 DGH 的天气字段：`rr`（降水）、`tg`（日均温）、`hu`（相对湿度）、`qq`（辐射）。
- 每 5 天聚合成：`precip_sum_5d`、`temp_mean_5d`、`vpd_mean_5d`、`srad_sum_5d`，因此模型输入 `D_path` 是 `[30,4]`。
- `C_path [30,2]` 仍单独保存年周期 `doy_sin/doy_cos`；`G` 仍是 `cop_dem`；`h`/`delta_t` 的时间接口不变。
- Stage1.5 不修改；已有 `full24` 配置、统计量、checkpoint（检查点）目录和训练逻辑不修改。physical4 使用独立配置、统计文件和输出目录。
- 旧的 `dgh_stats_train.json` 不能用于这个正式路径；必须由冻结的 `role=train` 清单生成新的 `physical4` 统计文件。

这意味着当前可以开始的是：**先做真实数据的快速审计和清单冻结，再跑 physical4 的正式 Direct 主实验**。不需要先改 Stage1.5，也不需要重新下载另一套数据。

## 1. 为什么代码这样组织

`D_path` 是天气如何随时间变化，`C_path` 是季节背景，`G` 是静态地形，`h/delta_t` 是“推演多远”。它们共同进入共享状态转移模块；观测编码器和 `phi`（成像条件编码器）仍负责从 Sentinel-2 历史观测初始化状态。这样保留了原来的“模拟地表状态、再渲染未来观测”的世界模型叙事，只更换了外生天气字段的具体协议。

physical4 是显式协议（explicit protocol，显式协议）：代码不会根据张量最后一维猜测含义，也不会把 4 维偷偷当成 24 维。模型配置、数据配置和统计 JSON 三者的 `driver_protocol` 必须一致。

## 2. 已完成的代码范围

| 位置 | 已完成内容 |
|---|---|
| `data/earthnet_physical_conditioning.py` | 固定字段顺序、VPD 公式、五日聚合、缺失日 mask、单位转换、统计量 schema（结构）和 DEM 归一化 |
| `data/datasets/earthnet2021.py` | NetCDF physical4 读取；输出 `[30,4]` 的 `D_path/D_mask/D_valid_day_count`；保留原 `C/G/h` |
| `scripts/build_earthnet_physical_stats.py` | 只读取冻结 train manifest；拟合天气统计、VPD 裁剪点、`cop_dem` 均值/标准差；记录清单 SHA 和代码版本 |
| `scripts/preflight_stage2_earthnet.py` | 检查字段、形状、日期、覆盖率、统计量清单 SHA、`qq` 换算系数和物理模型输入维度 |
| `models/dynamics/interval_driver_encoder.py` | 在显式 physical4 下接受 4 维；默认仍是 full24 |
| `models/dynamics/obsworld_factory.py` | physical Direct/Rollout/Partition 三种入口；禁止 model/data 协议不一致 |
| `data/stage2_contract.py` 与三个 wrapper | 支持 `D=4`，并保留 full24 的输入保护 |
| `configs/train/*physical4.yaml` | Direct、Rollout、Partition 和 smoke（最小冒烟）配置；输出目录隔离 |
| `tests/` | physical4 公式、单位、统计、loader、工厂、课程和 batch 契约测试 |

### 单位和缺失规则

统计脚本和 loader（数据加载器）共用同一个单位适配函数：`tg` 自动识别 K/°C，`hu` 自动识别 0–1 fraction（比例）/0–100 percent（百分比），`qq` 按配置的 `netcdf_solar_scale`（默认 `0.0864`，W/m² 到 MJ/m²/day）换算。湿度若换算后超出 `[0,100]` 会直接失败，不会悄悄裁剪。

每个五日窗口默认要求所需的 5 个日值全部有效；否则该字段的 `D_mask=0`，数值填 0，`D_valid_day_count` 只用于审计，不进模型。VPD 由日均温和相对湿度计算，再取五日均值；VPD 裁剪点只从训练清单拟合。

## 3. 当前已经做过的验证

- 最终完整项目测试：`135 passed, 13 warnings`（警告来自 NumPy/NetCDF 二进制兼容提示和 Transformer 的非致命提示）。
- 已用最小 NetCDF（150 天、S2 四波段、mask、四个 E-OBS、`cop_dem`）跑通：统计脚本、preflight、launcher（启动器）和 1-step CPU forward/backward（前向/反向）。
- 最小训练确实保存了 `checkpoint_step_1.pt`，日志中能看到 `physical4_v1` 和四个字段的有效率。
- 当前执行环境没有挂载服务器的 `/csy-mix02` 数据目录，因此真实 3 万份文件的字段覆盖率仍必须在你的训练服务器上运行；这不是代码失败，而是数据不在本地执行容器内。

## 4. 服务器操作顺序

以下命令都在服务器项目目录执行。先同步代码并进入正确虚拟环境；不要用系统 `python`，否则可能出现 `No module named numpy`。

### 4.1 进入项目、环境和数据审计

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
git pull --ff-only origin main

export DATA_PARENT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021
export CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml

mkdir -p artifacts/audits logs
python -u scripts/audit_earthnet2021x.py \
  --root "$DATA_PARENT" \
  --required-splits train iid ood extreme seasonal \
  --scan-mode metadata \
  --max-files-per-split 4 \
  --output "artifacts/audits/earthnet2021x_physical4_metadata.json"
```

这一步只抽查每个划分的少量文件，主要确认目录、NetCDF、S2、四个原始天气字段和 DEM；不读取全量数组，通常比全量统计快很多。若这一小步报缺字段，先不要启动训练。

### 4.2 冻结不可变文件清单（manifest，清单）

`freeze` 只读文件路径、大小和文件名日期，不读取 150 天数组；`--hash-mode none` 是有意的快速模式。不要提前创建 `RUN_DIR`，冻结器会自己原子发布；同名目录不能覆盖。

```bash
export RUN_DIR="artifacts/protocols/earthnet2021x_physical4_v1_$(date +%Y%m%d_%H%M%S)"
mkdir -p artifacts/protocols

nice -n 10 python -u scripts/freeze_earthnet2021x_protocol.py \
  --root "$DATA_PARENT" \
  --output-dir "$RUN_DIR" \
  --val-tile-count 8 \
  --seed 20260716 \
  --hash-mode none \
  --workers 8 \
  --progress-every 1000 \
  2>&1 | tee logs/earthnet_physical4_freeze.log

python -m json.tool "$RUN_DIR/protocol.json" | head -80
```

输出中应有：

- `train_dev.json`：排除验证 tile 的开发训练清单；
- `val_dev.json`：从 train 固定划出的 tile 验证清单；
- `train_all.json`：最终固定预算重训才使用的全量 train 清单；
- `iid.json`、`ood.json`、`extreme.json`、`seasonal.json`：只用于评测，不用于选模型。

如果清单过程中想查看进度：

```bash
pgrep -af freeze_earthnet2021x_protocol.py
tail -n 30 logs/earthnet_physical4_freeze.log
```

### 4.3 先做一次少量统计烟雾测试（可选但推荐）

这一步只为提前发现字段/单位问题，生成的文件**不能**用于正式训练：

```bash
python -u scripts/build_earthnet_physical_stats.py \
  --config "$CONFIG" \
  --data-root "$DATA_PARENT" \
  --manifest-path "$RUN_DIR/train_dev.json" \
  --output "$RUN_DIR/physical4_stats_smoke16.json" \
  --max-files 16 \
  --workers 2 \
  --progress-every 4
```

### 4.4 生成正式 train-dev 统计量

统计量必须来自和训练使用的同一份 `train_dev.json`。它会读取完整的开发训练清单，是整个准备阶段最慢的一步，但只需做一次；`--workers 4` 或 `8` 是 NetCDF 读取进程，不占 GPU。共享 NAS 如果 I/O 已经拥堵，把它降为 2，不要盲目开几十个进程。

```bash
nice -n 10 python -u scripts/build_earthnet_physical_stats.py \
  --config "$CONFIG" \
  --data-root "$DATA_PARENT" \
  --manifest-path "$RUN_DIR/train_dev.json" \
  --output "$RUN_DIR/conditioning_stats_physical4_v1_train_dev.json" \
  --require-full-train \
  --workers 4 \
  --progress-every 100 \
  2>&1 | tee "$RUN_DIR/physical4_stats_train_dev.log"

test -s "$RUN_DIR/conditioning_stats_physical4_v1_train_dev.json" && echo "physical4 stats ready"
```

`--require-full-train` 的含义是“没有使用 `--max-files` 子集”；这里的 full train 指完整 `train_dev` 清单，不是 `train_all`。后续若决定用 `train_all` 做最终固定预算重训，必须再用 `train_all.json` 单独生成一份统计量，不能复用这份文件。

### 4.5 真实数据快速 preflight（训练前检查）

先只检查 16 个 cube（数据块），不占 GPU，也不启动训练：

```bash
export STATS="$RUN_DIR/conditioning_stats_physical4_v1_train_dev.json"
export TRAIN_MANIFEST="$RUN_DIR/train_dev.json"
export VAL_MANIFEST="$RUN_DIR/val_dev.json"

CONFIG="$CONFIG" \
DATA_ROOT="$DATA_PARENT" \
CONDITIONING_STATS_PATH="$STATS" \
MANIFEST_PATH="$TRAIN_MANIFEST" \
VALIDATION_MANIFEST_PATH="$VAL_MANIFEST" \
REQUIRE_MANIFEST=1 \
PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 PREFLIGHT_CHECK_MODEL=0 RUN_TRAIN=0 \
PREFLIGHT_OUTPUT="$RUN_DIR/preflight_data16.json" \
bash run_stage2_earthnet.sh
```

检查报告的 `ok` 必须为 `true`，且 `driver_protocol` 为 `physical4_v1`、`D_path` 为 `[30,4]`、四个字段覆盖率没有被门槛判为低。不要把旧 `dgh_stats_train.json` 填给 `CONDITIONING_STATS_PATH`。

### 4.6 确认 Stage1.5 checkpoint，再做模型 preflight

先列出目录里的真实权重文件，不能把目录本身当成 checkpoint：

```bash
find /csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage1_5_dual_conditioned_vits_state_bridge_60k \
  -maxdepth 2 -type f \( -name '*.pt' -o -name '*.pth' \) -printf '%p\n' | sort
```

把下面变量改成实际存在、包含 `encoder_state_dict`、`phi_encoder_state_dict`、`state_projector_state_dict` 的 `.pt` 文件：

```bash
export STAGE15_CHECKPOINT=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage1_5_dual_conditioned_vits_state_bridge_60k/实际文件.pt

CONFIG="$CONFIG" \
DATA_ROOT="$DATA_PARENT" \
CONDITIONING_STATS_PATH="$STATS" \
MANIFEST_PATH="$TRAIN_MANIFEST" \
VALIDATION_MANIFEST_PATH="$VAL_MANIFEST" \
STAGE15_CHECKPOINT="$STAGE15_CHECKPOINT" \
REQUIRE_MANIFEST=1 \
PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=0 \
PREFLIGHT_OUTPUT="$RUN_DIR/preflight_model16.json" \
bash run_stage2_earthnet.sh
```

只有这一步也 `ok=true`，才进入 GPU 训练。它会同时检查 Stage1.5 初始化权重与 physical4 的模型输入维度是否匹配。

### 4.7 启动第一个正式主实验：Direct physical4

第一轮建议先跑 Direct（直接多跨度预测），因为它最容易定位数据、loss（损失）和 checkpoint 问题；这不是另起论文主线，而是同一 ObsWorld 转移模块的主实验起点。训练过程中 launcher 默认先做一次小 preflight。

```bash
CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml \
DATA_ROOT="$DATA_PARENT" \
CONDITIONING_STATS_PATH="$STATS" \
MANIFEST_PATH="$TRAIN_MANIFEST" \
VALIDATION_MANIFEST_PATH="$VAL_MANIFEST" \
STAGE15_CHECKPOINT="$STAGE15_CHECKPOINT" \
CHECKPOINT_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_earthnet_v2_direct_physical4 \
LOG_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs/stage2_earthnet_v2_direct_physical4 \
REQUIRE_MANIFEST=1 \
PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=1 \
GPUS=1 BATCH_SIZE=2 NUM_WORKERS=4 MAX_STEPS=50000 \
bash run_stage2_earthnet.sh 2>&1 | tee "$RUN_DIR/stage2_direct_physical4.log"
```

`GPUS=1` 是最容易复现的起点；如果服务器明确分配了多张空闲 GPU，再把 `GPUS` 改为相应数量，并在所有对照中保持相同训练预算。不要停止其他用户的进程。

## 5. 训练完成后如何判断是否成功

至少确认：

```bash
find /csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_earthnet_v2_direct_physical4 \
  -maxdepth 1 -type f -name '*.pt' -printf '%f\n' | sort | tail
cat /csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_earthnet_v2_direct_physical4/run_provenance.json | head -80
```

`run_provenance.json`（运行来源记录）应记录 physical4 协议、四个字段顺序、stats 的 manifest SHA、Stage1.5 checkpoint 和 resolved config（解析后的完整配置）。之后才能在 `val_dev` 选择 checkpoint，再在锁定后评测 `iid/ood`；`extreme/seasonal` 是补充压力测试，不参与选模。

Rollout 和 Partition 只在 Direct 数据链路稳定后使用：

```bash
# 仅替换 CONFIG 和输出目录，其余 DATA_ROOT/STATS/MANIFEST/STAGE15_CHECKPOINT 保持同一份
CONFIG=configs/train/stage2_earthnet_v2_rollout_physical4.yaml ... bash run_stage2_earthnet.sh
CONFIG=configs/train/stage2_earthnet_v2_partition_physical4.yaml ... bash run_stage2_earthnet.sh
```

## 6. 目前不需要做的事

- 不要重新下载 GreenEarthNet；本轮唯一数据身份仍是服务器已有的 EarthNet2021x raw NetCDF。
- 不要修改 Stage1.5 的代码或用旧 Stage1.5 训练脚本重跑。
- 不要把旧 `dgh_stats_train.json`、full24 stats 或 full24 checkpoint 与 physical4 混用。
- 不要在 `iid/ood` 上调参或挑 checkpoint。
- 不要为了“加快”而跳过 train-only stats；那会造成训练归一化和正式证据链不成立。

## 7. 仍需用户侧确认的两件事

1. 真实 `STAGE15_CHECKPOINT` 的 `.pt` 文件名（目录路径已经明确，但文件名必须核实）。
2. 服务器上 `audit_earthnet2021x.py` 抽查的 `eobs_tg/eobs_hu/eobs_qq` 数值范围是否符合转换规则。若抽查报湿度越界或缺少四字段，先把报告保留，不要训练；代码会硬失败而不是静默修数据。

除此之外，代码层面暂时没有必须拍板的阻塞项。当前最短安全路线就是：**抽查 → 冻结清单 → 生成 train-dev physical4 stats → 16-cube preflight → 指定 Stage1.5 `.pt` → Direct physical4 正式训练**。
