# ObsWorld Stage2 EarthNet2021x 服务器执行手册

## 1. 已确认的数据协议

- 主训练数据为 EarthNet2021x 的 `train` 划分，文件格式为 NetCDF (`.nc`)。
- 输入 10 帧历史 S2，预测未来 20 帧，对应 `h=5,10,...,100` 天。
- S2 使用 `B02/B03/B04/B8A`，即蓝、绿、红、窄近红外四通道。
- EarthNet2021x 的 S2 帧位于逐日序列第 `4,9,...,149` 天；天气窗口已同步校正 4 天偏移。
- `D` 使用目标日期、降水、温度、VPD、太阳辐射。VPD 由 `eobs_tg + eobs_hu` 推导，太阳辐射来自 `eobs_qq`。
- `G` 使用高程，按 `nasa_dem -> alos_dem -> cop_dem` 顺序回退。
- EarthNet2021x 已包含构造当前 D/G 所需的字段，主路线不需要 ERA5 sidecar。
- 未来天气按给定天气情景（oracle/scenario forcing）使用，用于检验条件动力学；不能表述为无需天气预报的部署预测。

## 2. 数据完整性

完整 EarthNet2021x 包含：

```text
earthnet2021x/
  train/
  iid/
  ood/
  extreme/
  seasonal/
```

当前只有 `train` 时可以先训练，并从 train 按地理 tile 固定划分内部验证集；但最终 IID/OOD/极端/季节实验仍需下载其余划分。

检查 train 是否与官方 S3 清单逐文件一致：

```bash
python scripts/audit_earthnet2021x.py \
  --root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --required-splits train \
  --scan-mode metadata \
  --max-files-per-split 50 \
  --compare-remote \
  --output logs/earthnet2021x_audit_train.json
```

检查最终五个划分是否齐全：

```bash
python scripts/audit_earthnet2021x.py \
  --root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --required-splits all \
  --scan-mode metadata \
  --max-files-per-split 20 \
  --compare-remote \
  --output logs/earthnet2021x_audit_all.json
```

不加 `--compare-remote` 只能验证本地结构与抽样文件可读，不能证明远端文件一个不少。
默认远端检查比较相对路径，不会在共享盘上逐个读取 2 万多个文件的大小；只有确实需要
字节级核对时才增加 `--compare-sizes`，该选项可能运行很久。

若审计报告给出损坏文件，先检查远端大小与本地可读性，再显式修复：

```bash
python scripts/repair_earthnet2021x_file.py \
  --root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --split train \
  --relative-path '<tile>/<cubename>.nc'

python scripts/repair_earthnet2021x_file.py \
  --root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --split train \
  --relative-path '<tile>/<cubename>.nc' \
  --repair
```

修复工具先下载到 `.part` 并验证 NetCDF，成功后才原子替换原文件。

不要使用仅以“文件大于 50KB”为完整标准的旧下载脚本。它会把截断但仍大于
50KB 的文件误判为正常，并且直接写最终 `.nc`，强制终止时会留下损坏文件。

使用安全增量同步器检查 train，首次需要从官方 S3 构建带字节数的清单：

```bash
python scripts/sync_earthnet2021x.py \
  --root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --split train \
  --dry-run \
  --report logs/earthnet2021x_train_sync_plan.json
```

确认缺失和大小不一致数量后进行补齐：

```bash
python scripts/sync_earthnet2021x.py \
  --root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --split train \
  --workers 8 \
  --report logs/earthnet2021x_train_sync.json
```

同一脚本依次用于下载 `iid`、`ood`、`extreme`、`seasonal`。它会跳过远端大小
一致的现有文件；新文件先写入 `.part`，核对大小并验证 NetCDF 后才原子替换，
因而中断后可以安全重跑。不要同时启动多个 split，也不要再用 `kill -9`。

剩余四个测试 split 可以用一个包装脚本顺序完成：

```bash
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
WORKERS=8 MANIFEST_WORKERS=4 \
bash scripts/sync_remaining_earthnet2021x.sh
```

包装脚本按 `iid -> ood -> extreme -> seasonal` 顺序同步；每个 split 内默认使用
8 个下载线程，完成后自动再做一次只读验收。中途停止后重复同一命令即可续传。

下载缺少的官方划分，例如：

```bash
python -c "import earthnet; earthnet.download(dataset='earthnet2021x', split='iid', save_directory='/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021')"
python -c "import earthnet; earthnet.download(dataset='earthnet2021x', split='ood', save_directory='/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021')"
python -c "import earthnet; earthnet.download(dataset='earthnet2021x', split='extreme', save_directory='/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021')"
python -c "import earthnet; earthnet.download(dataset='earthnet2021x', split='seasonal', save_directory='/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021')"
```

## 3. 环境与测试

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
pip install -r requirements.txt

python -m pytest -q \
  tests/test_earthnet_loader.py \
  tests/test_earthnet2021x_loader.py \
  tests/test_stage2_components.py \
  tests/test_era5_sidecars.py
```

`tests/conftest.py` 已处理项目导入路径，不再需要手动设置 `PYTHONPATH`。

## 4. 真实样本检查

```bash
python scripts/inspect_earthnet2021.py \
  --config configs/train/stage2_earthnet_main.yaml \
  --root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --split train \
  --max-files 1 \
  --try-loader
```

应得到：

```text
x_context = [10, 4, 256, 256]
x_target  = [20, 4, 256, 256]
D         = [20, 9]
G         = [1, 256, 256]
h         = [20]
```

九个 D 特征的 `driver_valid_rate` 均应为 `1.0`。

## 5. 构建 train-only 统计量

归一化统计只能由 train 构建，不能混入测试划分：

```bash
mkdir -p artifacts/stage2_earthnet2021x

python scripts/build_earthnet_dgh_stats.py \
  --config configs/train/stage2_earthnet_main.yaml \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --output artifacts/stage2_earthnet2021x/dgh_stats_train.json \
  --require-complete
```

## 6. 正式训练前检查

```bash
python scripts/preflight_stage2_earthnet.py \
  --config configs/train/stage2_earthnet_main.yaml \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --dgh-stats-path artifacts/stage2_earthnet2021x/dgh_stats_train.json \
  --stage15-checkpoint checkpoints/stage1_5_dual_conditioned_vits_60k/checkpoint_step_60000.pt \
  --max-files 64 \
  --check-model \
  --output artifacts/stage2_earthnet2021x/preflight_train.json
```

确认报告为 `"ok": true` 后再启动训练。先做 2 step 真实数据冒烟：

```bash
DGH_STATS_PATH=artifacts/stage2_earthnet2021x/dgh_stats_train.json \
STAGE15_CHECKPOINT=checkpoints/stage1_5_dual_conditioned_vits_60k/checkpoint_step_60000.pt \
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
MAX_STEPS=2 BATCH_SIZE=1 NUM_WORKERS=0 GPUS=1 PREFLIGHT=1 \
CHECKPOINT_DIR=checkpoints/stage2_earthnet2021x_smoke \
LOG_DIR=logs/stage2_earthnet2021x_smoke \
bash run_stage2_earthnet.sh
```

## 7. 正式训练

单卡：

```bash
DGH_STATS_PATH=artifacts/stage2_earthnet2021x/dgh_stats_train.json \
STAGE15_CHECKPOINT=checkpoints/stage1_5_dual_conditioned_vits_60k/checkpoint_step_60000.pt \
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
GPUS=1 BATCH_SIZE=2 NUM_WORKERS=4 PREFLIGHT=1 \
bash run_stage2_earthnet.sh
```

多卡时只修改 `GPUS` 和按显存调整单卡 `BATCH_SIZE`：

```bash
GPUS=8 BATCH_SIZE=2 NUM_WORKERS=4 ...
```

断点续训使用 Stage2 checkpoint，不再依赖原 Stage1.5 文件：

```bash
RESUME_FROM=checkpoints/stage2_earthnet_main/checkpoint_step_10000.pt \
DGH_STATS_PATH=artifacts/stage2_earthnet2021x/dgh_stats_train.json \
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
GPUS=1 BATCH_SIZE=2 NUM_WORKERS=4 \
bash run_stage2_earthnet.sh
```

## 8. 首轮反馈应保留

- 数据审计 JSON；
- 真实样本的变量范围、张量形状和九个 D 特征有效率；
- preflight JSON；
- 2 step 冒烟训练完整日志；
- GPU 显存、单 step 耗时及各项 loss；
- 正式训练前 100 到 500 step 的 loss 曲线。
