# ObsWorld：EarthNet2021x raw 数据契约与主实验规范

> **状态：当前固定数据协议。**本文件定义本轮 raw `EarthNet2021x` 目录、manifest（文件清单）、开发验证和 EarthNet2021 standard evaluator（官方评估器）口径。GreenEarthNet 是独立的未来扩展，不影响本轮数据、代码或主表。

## 0. 一句话结论

我们使用服务器已有的 **EarthNet2021x NetCDF raw 数据发布**，并固定采用下列 **EarthNet2021 standard 协议**：

```text
训练：train
主测试：iid + ood
补充测试：extreme + seasonal
开发验证：仅从 train 中按 tile（Sentinel-2 地图格）固定划出 val_dev
```

不换训练数据、不重新下载；但也不把尚未核验的细分轨道或错误 evaluator 写入论文。

论文中的准确表述是：

> **ObsWorld is evaluated on the EarthNet2021x NetCDF release under the EarthNet2021 train/IID/OOD/Extreme/Seasonal protocol.**

中文：

> **ObsWorld 在 EarthNet2021x 的 NetCDF 数据发布上，按照 EarthNet2021 的训练、IID、OOD、极端事件和季节循环协议评测。**

## 1. 为什么这一口径与服务器数据完全一致

服务器数据根目录为：

```text
/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021/earthnet2021x
```

其现有物理目录与清单统计如下：

| 目录 | 文件数 | 时间范围 | 在论文中的用途 |
|---|---:|---|---|
| `train` | 23,816 | 2017–2020 | 训练来源 |
| `iid` | 4,205 | 2017–2020 | 同分布主测试 |
| `ood` | 4,202 | 2017–2020 | 空间域外主测试 |
| `extreme` | 3,972 | 2018 | 极端夏季、长跨度预测证据 |
| `seasonal` | 3,880 | 2017–2020 | 多年季节循环、长时程证据 |

该结构与 EarthNet2021 的四条测试轨道兼容。当前 metadata audit 已确认本项目使用的 raw release 具备这五个目录和正式字段；论文实验名称与评测规则固定采用本文件的 EarthNet2021 standard 口径。

## 2. 世界模型叙事不变，实验语言更准确

ObsWorld 仍然是：

> 一个由外生驱动和地理先验条件化的地表状态动力学遥感世界模型：从历史、有噪遥感观测中估计地表状态，以 DGH 推演未来状态，再将未来状态解码为可验证的未来遥感观测。

这里：

- `D`（driver，外生驱动）：八个 E-OBS 气象变量按五日窗口聚合的 24 维路径；
- `G`（geographic prior，地理先验）：固定 Copernicus DEM；
- `h`（horizon，预测跨度）：每一个未来五日状态的跨度；
- `phi`（observation condition，观测条件）：保留为 Stage1/Stage1.5 和跨产品 Gate 的证据，不在当前固定 Sentinel-2 产品主实验中夸大为已端到端验证的未来成像控制。

EarthNet2021 本身就是“给定未来气象驱动预测未来地表遥感观测”的基准，因此与世界模型路线天然一致。我们不需要另换一个数据集才能证明主张。

## 3. 为什么必须先冻结清单

“清单（manifest）”不是下载清单，也不是新数据；它是一份 JSON，固定本次训练或评测实际使用的文件列表、文件大小和摘要（digest，摘要校验值）。这样可以防止：

1. 训练代码递归扫描根目录，意外混入 IID/OOD；
2. 用测试集调学习率、挑 checkpoint（检查点）；
3. 统计量从测试集泄漏到训练集；
4. 日后无法复现“本次结果到底用了哪些文件”。

冻结后会得到：

```text
artifacts/protocols/earthnet2021x_standard_v1/
├── protocol.json        # 本次协议、tile 划分、主/补充测试轨道
├── inventory.json       # 文件数、tile 数、起止日期等元数据证据
├── train_dev.json       # 开发训练集；排除验证 tile
├── val_dev.json         # 开发验证集；仅来自 train 的固定 tile
├── train_all.json       # 最终固定步数重训时使用的全量 train
├── iid.json             # 锁定主测试
├── ood.json             # 锁定主测试
├── extreme.json         # 锁定补充测试
└── seasonal.json        # 锁定补充测试
```

`val_dev` 的 8 个 tile 由固定 seed（随机种子）确定。它只用于早停、选择 checkpoint 和调参；`iid/ood/extreme/seasonal` 全部禁止参与这些决定。

## 4. 服务器上现在可以直接执行的命令

这一步只读取目录、文件大小和文件名中的日期，**不打开全部 NetCDF 内容、不使用 GPU、不下载数据**，可以与正在运行的 Stage1.5 并行。

### 4.1 先检查工作区，再拉取最新脚本

以下命令均在 `WorldModel2026` 根目录执行。先确认本机没有未提交改动；若 `git status --short`
有输出，先不要执行 `git pull`、不要 `git stash` 或覆盖文件，保留改动并单独处理。空输出后再拉取：

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
git status --short
git pull --ff-only origin main
git rev-parse --short HEAD
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
```

本规范对应的快速冻结器会显示 `[freeze] <split>: discovered ...` 与
`[freeze] <split>: metadata 已完成/总数`，并给出当前读取速率、已耗时和 ETA。`--workers 8` 只增加共享存储的**元数据读取线程**，
不占 GPU；共享 NAS 上先用 8，不能直接设成 32 或 64，以免对文件系统造成更多排队。

### 4.2 若此前启动过无输出的旧冻结任务，先安全停止它

旧版本没有进度输出，且在所有 JSON 完成前都不会发布 `RUN_DIR`；因此看不到
`artifacts/protocols/earthnet2021x_standard_v1` **不等于成功，也不等于失败**。升级代码并确认
旧 PID 仍存在后，使用 `SIGINT` 正常终止；不要使用 `kill -9`，也不要在旧进程仍在时启动第二个冻结器：

```bash
pgrep -af 'freeze_earthnet2021x_protocol.py'
kill -INT <旧冻结PID>
ps -p <旧冻结PID> -o pid,etime,stat,wchan:32,%cpu,cmd
```

若 30 秒后该 PID 还存在，才改用 `kill -TERM <旧冻结PID>`；确认 `ps -p <旧冻结PID>` 没有输出后，
再按下一节重新启动。旧任务可能遗留 `.earthnet2021x_standard_v1.staging-*` 私有目录；不要把它当成
结果目录，也不需要手动删除它，新任务会创建自己的私有暂存目录。

### 4.3 冻结正式 EarthNet2021x 清单

以下变量使用相对短路径，避免终端显示换行时误把一个路径拆成两条命令。请整体粘贴；反斜杠 `\`
表示下一行仍是同一条 Python 命令。

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

DATA_ROOT=../TrainData/EarthNet2021/earthnet2021x
RUN_DIR=artifacts/protocols/earthnet2021x_standard_v1
mkdir -p logs
set -euo pipefail

nice -n 10 python -u scripts/freeze_earthnet2021x_protocol.py \
  --root "$DATA_ROOT" \
  --output-dir "$RUN_DIR" \
  --val-tile-count 8 \
  --seed 20260716 \
  --hash-mode none \
  --workers 8 \
  --progress-every 1000 \
  2>&1 | tee logs/earthnet2021x_freeze.log
```

`RUN_DIR` 必须是**尚不存在的新目录**；不要提前 `mkdir -p "$RUN_DIR"`，也不要用同一目录
重跑。冻结器会在私有暂存目录中完成所有 JSON 后再一次性发布，若同名目录已经存在会拒绝覆盖，
以免一次中断或重跑把两次实验的 manifest（清单）混在一起。需要重新冻结时，换一个带日期/版本的
新目录。

为避免 SSH 断开，建议先创建 tmux 会话再执行上面的冻结块：

```bash
tmux new -s earthnet_freeze
```

执行中按 `Ctrl-b` 后按 `d` 可退出而不停止；之后用 `tmux attach -t earthnet_freeze` 回到会话。
另一个终端可用以下命令查看进度和完成状态：

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
pgrep -af 'freeze_earthnet2021x_protocol.py'
tail -n 30 logs/earthnet2021x_freeze.log
test -s artifacts/protocols/earthnet2021x_standard_v1/protocol.json && test -s artifacts/protocols/earthnet2021x_standard_v1/train_dev.json && echo 已完成 || echo 尚未完成
```

最后一条只有输出 `已完成` 才能进入统计步骤。成功后快速查看协议：

```bash
python -m json.tool "$RUN_DIR/protocol.json"
```

预期要点：`primary_test_tracks` 是 `iid` 与 `ood`；`supplementary_test_tracks` 是 `extreme` 与 `seasonal`；`validation_tile_count` 是 8。

## 5. 清单后、正式 Stage2 前还要做什么

清单完成后即可继续写和调试 Stage2 模型。正式启动大规模训练前，再从**同一份** `train_dev.json` 计算 D/G 标准化统计量：

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

DATA_ROOT=../TrainData/EarthNet2021/earthnet2021x
RUN_DIR=artifacts/protocols/earthnet2021x_standard_v1
set -euo pipefail

nice -n 10 python -u scripts/build_earthnet_conditioning_stats.py \
  --config configs/train/stage2_earthnet_v2_data.yaml \
  --data-root "$DATA_ROOT" \
  --manifest-path "$RUN_DIR/train_dev.json" \
  --output "$RUN_DIR/conditioning_stats_v2_train_dev.json" \
  --require-full-train \
  --workers 8 \
  --progress-every 100 \
  2>&1 | tee "$RUN_DIR/conditioning_stats_v2_train_dev.log"
```

这第二条命令会实际读取完整 `train_dev` NetCDF，用于计算八个 E-OBS 字段和 `cop_dem` 的统计量；
它比冻结清单慢。这里的 `--workers 8` 是**总共 8 个 NetCDF 读取进程**，不是每张 GPU 8 个进程，
也不使用 GPU。共享 NAS 上从 8 开始，只有确认 I/O 仍有余量时才小幅调到 12 或 16；不要直接设成
32/64。日志每处理 100 个文件会更新一次，完成的唯一判据是：

```bash
test -s "$RUN_DIR/conditioning_stats_v2_train_dev.json" && echo 统计完成 || echo 统计未完成
```

建议在独立 tmux 会话运行该步骤：`tmux new -s earthnet_stats`。执行中可通过
`tail -n 30 "$RUN_DIR/conditioning_stats_v2_train_dev.log"` 观察已处理文件数。

统计完成后，先只做**无 GPU 训练的真实数据预检**。以下命令只读取清单中的 64 个
`train_dev` cube，核对字段、统计量、mask（有效标记）和最终 DataLoader；`RUN_TRAIN=0`
保证它不会启动训练：

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

DATA_PARENT=../TrainData/EarthNet2021
RUN_DIR=artifacts/protocols/earthnet2021x_standard_v1
set -euo pipefail

CONFIG=configs/train/stage2_earthnet_v2_direct24.yaml \
DATA_ROOT="$DATA_PARENT" \
MANIFEST_PATH="$RUN_DIR/train_dev.json" \
VALIDATION_MANIFEST_PATH="$RUN_DIR/val_dev.json" \
CONDITIONING_STATS_PATH="$RUN_DIR/conditioning_stats_v2_train_dev.json" \
PREFLIGHT=1 PREFLIGHT_CHECK_MODEL=0 RUN_TRAIN=0 \
PREFLIGHT_OUTPUT="$RUN_DIR/preflight_train_dev.json" \
bash run_stage2_earthnet.sh 2>&1 | tee "$RUN_DIR/preflight_train_dev.log"
```

确认这份报告的 `ok` 为 `true`，并且最终 Stage1.5 的 `state_bridge` checkpoint（状态桥接权重）
已冻结后，才把 `PREFLIGHT_CHECK_MODEL=1`、`RUN_TRAIN=1`，再传入
`STAGE15_CHECKPOINT=/真实/最终/checkpoint.pt` 启动 Direct24。Rollout24 和 Partition24
只替换 `CONFIG` 为各自 YAML；它们继承同一数据、清单和统计量。最终 `train_all` 重训前必须用
`train_all.json` **重新**计算一份对应的 conditioning stats，不能复用 `train_dev` 的统计文件。

### 5.1 正式 Stage2 启动命令（先 Direct24，再 Rollout24，再 Partition24）

先确认八张 GPU 确实空闲或已明确分配给自己；出现其他用户的进程时，**绝不能停止它们**。正式训练的
推荐起点是 `GPUS=8 NUM_WORKERS=4`：`NUM_WORKERS` 是每个 DDP rank 的 DataLoader worker 数，
因此总共是 `8 × 4 = 32` 个读取进程。不要把它设置成 32 或 64（那会变成 256 或 512 个进程）。
如果日志和 `nvidia-smi` 表明 GPU 长期低利用率、而 CPU/NAS 仍有余量，再依次试 6（总计 48）和
8（总计 64），并在所有正式对照实验中固定同一数值。

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
nvidia-smi
ls -lh checkpoints/stage1_5_dual_conditioned_vits_state_bridge_60k/checkpoint_step_*.pt
tmux new -s stage2_direct24
```

在新 tmux 会话中，先将下一块中唯一需要人工替换的 `STAGE15_CKPT` 设为上一步确认的最终
Stage1.5 checkpoint，再整体执行：

```bash
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
DATA_PARENT=../TrainData/EarthNet2021
RUN_DIR=artifacts/protocols/earthnet2021x_standard_v1
STAGE15_CKPT=/绝对路径/到/确认过的/stage1_5/checkpoint_step_*.pt
test -s "$STAGE15_CKPT" || { echo "Stage1.5 checkpoint 不存在" >&2; exit 1; }
mkdir -p logs
set -euo pipefail

CONFIG=configs/train/stage2_earthnet_v2_direct24.yaml \
DATA_ROOT="$DATA_PARENT" \
MANIFEST_PATH="$RUN_DIR/train_dev.json" \
VALIDATION_MANIFEST_PATH="$RUN_DIR/val_dev.json" \
CONDITIONING_STATS_PATH="$RUN_DIR/conditioning_stats_v2_train_dev.json" \
STAGE15_CHECKPOINT="$STAGE15_CKPT" \
GPUS=8 NUM_WORKERS=4 BATCH_SIZE=2 MAX_STEPS=50000 \
PREFLIGHT=1 PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=1 \
bash run_stage2_earthnet.sh 2>&1 | tee logs/stage2_direct24.log
```

`test -s` 没有报错才会继续；请把示例中的 `checkpoint_step_*.pt` 替换成一个实际文件名。
它能防止把文档中的占位路径误传入正式训练。Direct24 通过完整开发验证后，
分别把 `CONFIG` 改为 `configs/train/stage2_earthnet_v2_rollout24.yaml` 和
`configs/train/stage2_earthnet_v2_partition24.yaml` 启动匹配的两个对照/主模型，不改变数据根、清单、
统计量、Stage1.5 checkpoint、GPU 数或 DataLoader worker 数。

运行中：`tail -n 50 logs/stage2_direct24.log` 看训练和验证日志；按 `Ctrl-b`、`d` 脱离 tmux；
`tmux attach -t stage2_direct24` 回到训练。需要安全停止时，优先在该 tmux 前台按 `Ctrl-c`；如果只能
从另一个终端处理，先确认主 `torchrun` PID 后再发送 SIGINT：

```bash
pgrep -af 'train_stage2_earthnet.py'
kill -INT <确认过的torchrun主PID>
```

等待 checkpoint 写完后才关闭会话。恢复时使用同一配置和同一清单，并额外传入
`RESUME_FROM=/绝对路径/到/stage2/checkpoint_step_实际步数.pt`；不要从不匹配的数据协议或不同模型配置恢复。

如果只想先验证真实字段、梯度和 checkpoint（检查点）链路，可以额外做一个 **32/128 cube sanity
bundle（小样本包）**。它从已冻结的 `train_dev/val_dev` 以确定性 tile round-robin（按 tile 轮转）
选择样本，写出新的带父清单摘要的 `train_sanity.json/val_sanity.json`；它被明确标记为
`formal_result_eligible=false`，绝不能报告为验证集、IID/OOD 或主实验结果：

```bash
SANITY_DIR="$RUN_DIR/sanity_32_20260716"  # 必须是新的、尚不存在的目录

python scripts/build_stage2_sanity_bundle.py \
  --data-root "$DATA_ROOT" \
  --train-manifest "$RUN_DIR/train_dev.json" \
  --validation-manifest "$RUN_DIR/val_dev.json" \
  --output-dir "$SANITY_DIR" \
  --train-count 32 \
  --validation-count 32 \
  --seed 20260716 \
  --hash-mode none

python scripts/build_earthnet_conditioning_stats.py \
  --config configs/train/stage2_earthnet_v2_data.yaml \
  --data-root "$DATA_ROOT" \
  --manifest-path "$SANITY_DIR/train_sanity.json" \
  --output "$SANITY_DIR/conditioning_stats_v2_train_sanity.json" \
  --require-full-train
```

这里的 “full train” 仅指 **完整读取该 32-cube 清单**，并不指完整 `train_dev`；脚本会把这一区别写入
`bundle.json` 和 manifest 的 `selection` 字段。正式结果仍只能使用完整的 `train_dev` 或最终 `train_all`。

## 6. Stage2 的训练和评测顺序

1. `train_dev.json → val_dev.json`：开发、过拟合小样本、选 checkpoint；
2. 固定模型结构、损失权重、训练步数；
3. 需要最终结果时，用 `train_all.json` 按固定步数重训；
4. 一次性评测 `iid.json` 与 `ood.json`，形成主表；
5. 再评测 `extreme.json` 与 `seasonal.json`，形成世界模型长时程与极端驱动证据；
6. 最后补 Direct-DGH、Persistence、Climatology、强时空基线和消融。

主评测使用 EarthNetScore（ENS，EarthNet 综合分数）及其 MAD/OLS/EMD/SSIM 分量；NDVI 误差、预测跨度曲线、D/G 干预和 partition consistency（时间分割一致性）作为支持“学习到动力学而非普通图像预测”的证据。

## 7. 明确禁止的做法

- 不能把整个 `iid` 或 `ood` 目录改名为不存在的更细测试轨道；
- 不能从根目录递归扫描后混合训练和测试文件；
- 不能用 IID/OOD 结果调学习率、选择 epoch 或决定损失权重；
- 不能用测试集参与 D/G 标准化；
- 不能把当前固定 Sentinel-2 主实验夸大为“任意未来成像条件可控渲染”。
- 不能把 `TrainData/GreenEarthNet`、`*_chopped`、`ood-t/ood-s/ood-st` 或旧 `refine-logs/`
  的历史草稿带入本轮数据、训练命令、主表、图注或结论；它们只属于未来独立扩展。
- 不能为本规范重新运行 GreenEarthNet/S3 下载器；当前正式数据根只能是
  `TrainData/EarthNet2021/earthnet2021x`。

## 8. 本规范对应的代码命名

正式配置统一为：

```yaml
data:
  dataset: earthnet2021x
  dataset_protocol: earthnet2021_standard_v1
  stage2_protocol: earthnet2021x_path_v2
```

这样，数据名称、配置名称、训练清单、论文实验表和服务器目录全部使用同一口径。

## 参考

- [EarthNet2021: A Large-Scale Dataset and Challenge for Earth Surface Forecasting as a Guided Video Prediction Task](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf)
- [EarthNet Models PyTorch](https://github.com/earthnet2021/earthnet-models-pytorch)
