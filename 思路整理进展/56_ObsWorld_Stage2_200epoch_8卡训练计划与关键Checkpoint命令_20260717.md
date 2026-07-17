# 56 ObsWorld Stage2：200 epoch、8 卡训练计划与关键 checkpoint 命令

## 1. 适用范围

本文件只约束 **Stage2 的 EarthNet2021x 主实验**，不改变 Stage1/Stage1.5 的
SSL4EO-S12 训练。Stage1.5 的 `checkpoint_step_60000.pt` 只作为 Stage2 的状态
初始化器（initializer），不能把两套数据的 epoch 混算。

冻结的 Stage2 训练清单为：

```text
train_dev = 22,847 EarthNet2021x episodes
world size = 8 GPUs
per-GPU batch = 64
global batch = 512
gradient accumulation = 1
steps per epoch = 44
200 epochs = 8,800 optimizer steps
```

`horizons_per_sample=6` 只选择每个 episode 的六个监督时距，不改变 epoch 定义。

## 2. 关键 checkpoint

正式配置会保存普通 step checkpoint，并额外保存以下三个完整、可续训的文件：

```text
checkpoint_epoch100_step_4400.pt
checkpoint_epoch150_step_6600.pt
checkpoint_epoch200_step_8800.pt
```

文件名中的 step 会根据实际 `batch_size` 自动换算。这里的 `batch_size` 是**每张
GPU 的 batch**；当前 8 卡 × 64 的正式配置每个 epoch 有 44 个优化器更新。

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
pytest -q tests/test_stage2_checkpoint_schedule.py tests/test_stage2_v2_contract.py \
  tests/test_earthnet2021x_v2_loader.py tests/test_stage2_v2_training_utils.py
```

## 4. 8 卡性能冒烟测试（先执行）

这一步跑 100 个 optimizer step，用于确认 8 卡、每卡 batch 64 的显存、通信和
真实 NetCDF 读取速度。它不会覆盖正式训练目录。新版会每 20 step 打印一次
`data`（等数据）、`h2d`（主机到 GPU）、`gpu_input`（GPU 上的 context 放大）、
`gpu_compute`、`wall` 与全局吞吐量；它是判断 GPU 是否被数据管线饿住的依据。

```bash
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export HDF5_USE_FILE_LOCKING=FALSE
export TORCH_NCCL_ASYNC_ERROR_HANDLING=1

export SMOKE_CKPT_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_physical4_8gpu_smoke
export SMOKE_LOG_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs/stage2_physical4_8gpu_smoke
mkdir -p "$SMOKE_CKPT_DIR" "$SMOKE_LOG_DIR"

CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml \
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
MAX_STEPS=100 BATCH_SIZE=64 NUM_WORKERS=8 PREFETCH_FACTOR=1 \
PERSISTENT_WORKERS=1 LOG_INTERVAL=20 GPUS=8 \
CONDITIONING_STATS_PATH="$STATS" \
MANIFEST_PATH="$TRAIN_MANIFEST" \
VALIDATION_MANIFEST_PATH="$VAL_MANIFEST" \
STAGE15_CHECKPOINT="$STAGE15_CHECKPOINT" \
CHECKPOINT_DIR="$SMOKE_CKPT_DIR" LOG_DIR="$SMOKE_LOG_DIR" \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 \
PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=1 \
PREFLIGHT_OUTPUT="$RUN_DIR/preflight_8gpu_batch64.json" \
bash run_stage2_earthnet.sh 2>&1 | tee "$SMOKE_LOG_DIR/train.log"

find "$SMOKE_CKPT_DIR" -maxdepth 1 -type f -printf '%f\t%s bytes\n' | sort
```

另开终端观察显存和利用率：

```bash
watch -n 2 nvidia-smi
```

若速度日志中的 `data` 明显大于 `gpu_compute`，先只把 `NUM_WORKERS` 从 8 提到
12 重跑这一段 100 step 冒烟，并比较 `throughput`；不要同时改变 batch 和 worker，
否则无法知道提升来自哪里。`PREFETCH_FACTOR` 保持 1，避免 8 卡在共享盘上预取过多
大 batch。若 `gpu_compute` 才是主要部分，B64 已经是合理的正式 batch，不要因为显存
有余就直接改成 B128：B128 会把 200 epoch 的优化器更新数减半，属于训练方案变化。

如果 `data` 仍远大于 `gpu_compute`，说明共享 NAS 已是主瓶颈；此时再考虑把
`earthnet2021x/` 无损复制到本机高速盘后重新指向 `DATA_ROOT`。不要在未看性能日志
前盲目复制 100GB 数据，也不要修改已冻结的 manifest、统计量或 DGH 字段。

## 5. 正式 200 epoch 主实验命令

冒烟测试通过后执行：

```bash
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export HDF5_USE_FILE_LOCKING=FALSE
export TORCH_NCCL_ASYNC_ERROR_HANDLING=1

export CHECKPOINT_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_physical4_8gpu_b64_200ep_v2
export LOG_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs/stage2_physical4_8gpu_b64_200ep_v2
mkdir -p "$CHECKPOINT_DIR" "$LOG_DIR"

CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml \
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
MAX_STEPS=8800 BATCH_SIZE=64 NUM_WORKERS=8 PREFETCH_FACTOR=1 \
PERSISTENT_WORKERS=1 LOG_INTERVAL=50 GPUS=8 \
CONDITIONING_STATS_PATH="$STATS" \
MANIFEST_PATH="$TRAIN_MANIFEST" \
VALIDATION_MANIFEST_PATH="$VAL_MANIFEST" \
STAGE15_CHECKPOINT="$STAGE15_CHECKPOINT" \
CHECKPOINT_DIR="$CHECKPOINT_DIR" LOG_DIR="$LOG_DIR" \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 \
PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=1 \
PREFLIGHT_OUTPUT="$RUN_DIR/preflight_formal_b64.json" \
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

1. **普通 step checkpoint**：`checkpoint_interval=1000`，例如
   `checkpoint_step_1000.pt`、`checkpoint_step_2000.pt`；训练结束时还会保存最后一步。
2. **关键 epoch checkpoint**：100/150/200 epoch 三个命名文件，用于比较训练阶段、
   复现实验和断点续训。
3. **`checkpoint_best.pt`**：每隔 1000 step 在 `val_dev` 上验证；当主指标 MAE
   改善时覆盖保存。它代表当前训练过程中的最佳验证模型，训练结束后才是最终 best。

论文主结果应使用只根据 `val_dev` 选出的 `checkpoint_best.pt`，不能用 IID/OOD/
extreme/seasonal 测试集挑模型。普通 step 文件主要用于故障恢复；若磁盘紧张，训练
完成并确认 best 与关键 epoch 文件后，可以清理普通 step 文件，但建议先保留。

不要在正式结果中混用不同 batch 的 step 数；论文中同时报告 `global batch`、
`optimizer step` 和折算后的 EarthNet epoch。B64 的正式目标是 8,800 step；如因
显存或稳定性必须改变 batch，需先重新计算每 epoch 的 DataLoader 长度，再同步调整
三个命名 epoch checkpoint，而不能直接沿用本文件的 step 数。
