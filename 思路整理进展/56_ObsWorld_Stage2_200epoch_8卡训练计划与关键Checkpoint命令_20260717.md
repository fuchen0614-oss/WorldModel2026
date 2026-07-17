# 56 ObsWorld Stage2：200 epoch、8 卡训练计划与关键 checkpoint 命令

## 1. 适用范围

本文件只约束 **Stage2 的 EarthNet2021x 主实验**，不改变 Stage1/Stage1.5 的
SSL4EO-S12 训练。Stage1.5 的 `checkpoint_step_60000.pt` 只作为 Stage2 的状态
初始化器（initializer），不能把两套数据的 epoch 混算。

冻结的 Stage2 训练清单为：

```text
train_dev = 22,847 EarthNet2021x episodes
world size = 8 GPUs
per-GPU batch = 8
global batch = 64
gradient accumulation = 1
steps per epoch = 357
200 epochs = 71,400 optimizer steps
```

`horizons_per_sample=6` 只选择每个 episode 的六个监督时距，不改变 epoch 定义。

## 2. 关键 checkpoint

正式配置会保存普通 step checkpoint，并额外保存以下三个完整、可续训的文件：

```text
checkpoint_epoch100_step_35700.pt
checkpoint_epoch150_step_53550.pt
checkpoint_epoch200_step_71400.pt
```

文件名中的 step 会根据实际 `batch_size` 自动换算。例如每卡 batch=16 时，
同样的三个文件会对应 step 17,800、26,700、35,600，而不会错误地沿用
batch=8 的 step。

最终模型仍然按照 `val_dev` 的最佳指标选择；200 epoch 是训练上限，不强制声称
最佳模型一定出现在最后一步。

## 3. 训练前确认

在服务器上执行：

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

export RUN_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048
export STATS="$RUN_DIR/conditioning_stats_physical4_v1_train_dev.json"
export TRAIN_MANIFEST="$RUN_DIR/train_dev.json"
export VAL_MANIFEST="$RUN_DIR/val_dev.json"
export STAGE15_CHECKPOINT=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage1_5_dual_conditioned_vits_state_bridge_60k/checkpoint_step_60000.pt

test -s "$STATS"
test -s "$TRAIN_MANIFEST"
test -s "$VAL_MANIFEST"
test -s "$STAGE15_CHECKPOINT"

nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader

# 在 WorldModel 环境中验证新增的 checkpoint 调度测试
pytest -q tests/test_stage2_checkpoint_schedule.py tests/test_stage2_v2_contract.py
```

## 4. 8 卡冒烟测试（先执行）

这一步只跑 2 个 optimizer step，用于确认 8 卡和每卡 batch 8 的显存、通信和
真实 NetCDF 读取。它不会覆盖正式训练目录。

```bash
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

export SMOKE_CKPT_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_physical4_8gpu_smoke
export SMOKE_LOG_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs/stage2_physical4_8gpu_smoke
mkdir -p "$SMOKE_CKPT_DIR" "$SMOKE_LOG_DIR"

CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml \
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
MAX_STEPS=2 BATCH_SIZE=8 NUM_WORKERS=4 GPUS=8 \
CONDITIONING_STATS_PATH="$STATS" \
MANIFEST_PATH="$TRAIN_MANIFEST" \
VALIDATION_MANIFEST_PATH="$VAL_MANIFEST" \
STAGE15_CHECKPOINT="$STAGE15_CHECKPOINT" \
CHECKPOINT_DIR="$SMOKE_CKPT_DIR" LOG_DIR="$SMOKE_LOG_DIR" \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 \
PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=1 \
PREFLIGHT_OUTPUT="$RUN_DIR/preflight_8gpu_batch8.json" \
bash run_stage2_earthnet.sh 2>&1 | tee "$SMOKE_LOG_DIR/train.log"

find "$SMOKE_CKPT_DIR" -maxdepth 1 -type f -printf '%f\t%s bytes\n' | sort
```

另开终端观察显存和利用率：

```bash
watch -n 2 nvidia-smi
```

如果想测试更快的 batch，只需把下面的 `BATCH_TRIAL` 改成 4 或 16，
每次使用不同的输出目录；这只是容量测试，不是论文实验：

```bash
export BATCH_TRIAL=16
export TRIAL_CKPT_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_physical4_8gpu_b${BATCH_TRIAL}_smoke
export TRIAL_LOG_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs/stage2_physical4_8gpu_b${BATCH_TRIAL}_smoke
mkdir -p "$TRIAL_CKPT_DIR" "$TRIAL_LOG_DIR"

CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml \
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
MAX_STEPS=2 BATCH_SIZE="$BATCH_TRIAL" NUM_WORKERS=4 GPUS=8 \
CONDITIONING_STATS_PATH="$STATS" MANIFEST_PATH="$TRAIN_MANIFEST" \
VALIDATION_MANIFEST_PATH="$VAL_MANIFEST" STAGE15_CHECKPOINT="$STAGE15_CHECKPOINT" \
CHECKPOINT_DIR="$TRIAL_CKPT_DIR" LOG_DIR="$TRIAL_LOG_DIR" \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 \
PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=1 \
PREFLIGHT_OUTPUT="$RUN_DIR/preflight_b${BATCH_TRIAL}.json" \
bash run_stage2_earthnet.sh 2>&1 | tee "$TRIAL_LOG_DIR/train.log"
```

容量选择原则：优先选不 OOM（显存溢出）且有明显显存余量的最大 batch。推荐顺序是
先试 8，再试 16；batch 16 若稳定，200 epoch 的上限是 35,600 step，但每个
epoch 会因 `drop_last` 丢弃少量样本。batch 8 是覆盖最整齐、风险最低的正式选择；
batch 4 是显存不足时的 fallback（备用）方案，对应 142,800 step。

## 5. 正式 200 epoch 主实验命令

冒烟测试通过后执行：

```bash
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

export CHECKPOINT_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_earthnet_v2_direct_physical4
export LOG_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs/stage2_earthnet_v2_direct_physical4
mkdir -p "$CHECKPOINT_DIR" "$LOG_DIR"

CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml \
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
MAX_STEPS=71400 BATCH_SIZE=8 NUM_WORKERS=4 GPUS=8 \
CONDITIONING_STATS_PATH="$STATS" \
MANIFEST_PATH="$TRAIN_MANIFEST" \
VALIDATION_MANIFEST_PATH="$VAL_MANIFEST" \
STAGE15_CHECKPOINT="$STAGE15_CHECKPOINT" \
CHECKPOINT_DIR="$CHECKPOINT_DIR" LOG_DIR="$LOG_DIR" \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 \
PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=1 \
PREFLIGHT_OUTPUT="$RUN_DIR/preflight_formal_8gpu.json" \
bash run_stage2_earthnet.sh 2>&1 | tee "$LOG_DIR/train_200epoch.log"
```

## 6. 训练完成后的核对

```bash
find "$CHECKPOINT_DIR" -maxdepth 1 -type f \
  \( -name 'checkpoint_epoch*.pt' -o -name 'checkpoint_best.pt' \) \
  -printf '%f\t%s bytes\n' | sort

grep -E 'named epoch checkpoints|checkpoint saved|validation step=' \
  "$LOG_DIR/train_200epoch.log" | tail -80
```

## 7. checkpoint 保存逻辑

当前配置同时保留三类文件：

1. **普通 step checkpoint**：`checkpoint_interval=5000`，例如
   `checkpoint_step_5000.pt`、`checkpoint_step_10000.pt`；训练结束时还会保存最后一步。
2. **关键 epoch checkpoint**：100/150/200 epoch 三个命名文件，用于比较训练阶段、
   复现实验和断点续训。
3. **`checkpoint_best.pt`**：每隔 1000 step 在 `val_dev` 上验证；当主指标 MAE
   改善时覆盖保存。它代表当前训练过程中的最佳验证模型，训练结束后才是最终 best。

论文主结果应使用只根据 `val_dev` 选出的 `checkpoint_best.pt`，不能用 IID/OOD/
extreme/seasonal 测试集挑模型。普通 step 文件主要用于故障恢复；若磁盘紧张，训练
完成并确认 best 与关键 epoch 文件后，可以清理普通 step 文件，但建议先保留。

如果 batch 8 显存不足，保持同样的 200 epoch 预算，退回每卡 batch 4，
将 `MAX_STEPS` 改为 `142800`。如果 batch 16 的 8 卡冒烟稳定，则可以用
`MAX_STEPS=35600`，但它会因 `drop_last=True` 每 epoch 丢弃少量样本，优先级低于
batch 8。不要在正式结果中混用不同 batch 的 step 数，论文中同时报告
`global batch`、`optimizer step` 和折算后的 EarthNet epoch。
