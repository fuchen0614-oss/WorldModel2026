# 56 ObsWorld Stage2：200 epoch、8 卡训练、本地缓存与关键 checkpoint 指南

日期：2026-07-17
适用配置：`configs/train/stage2_earthnet_v2_direct_physical4.yaml`

## 1. 适用范围与冻结训练规模

本文件只约束 **Stage2 的 EarthNet2021x physical4 主实验**，不改变 Stage1/Stage1.5 的 SSL4EO-S12 训练。Stage1.5 的 `checkpoint_step_60000.pt` 仅作为 Stage2 状态初始化器，不能把两套数据的 epoch 混算。

冻结的 Stage2 训练规模：

```text
train_dev episodes      = 22,847
world size              = 8 GPUs
per-GPU training batch  = 64
global training batch   = 512
gradient accumulation   = 1
steps per epoch         = 44
200 epochs              = 8,800 optimizer steps
```

这里的 `BATCH_SIZE=64` 是**每张 GPU** 的训练 batch；validation monitor 使用独立 batch 8，不影响训练 batch 或 epoch 换算。 `horizons_per_sample=6` 只选择每个 episode 的六个监督时距，不改变 epoch 定义。

## 2. checkpoint 与验证保存策略

训练会同时保存三类完整、可续训 checkpoint：

1. 普通 step checkpoint：每 1,000 个 **optimizer step** 保存一次：`checkpoint_step_1000.pt`、`checkpoint_step_2000.pt`，直到 `checkpoint_step_8000.pt`。
2. 关键 epoch checkpoint：

   ```text
   checkpoint_epoch100_step_4400.pt
   checkpoint_epoch150_step_6600.pt
   checkpoint_epoch200_step_8800.pt
   ```

3. 最佳验证 checkpoint：每 1,000 step 在 `val_dev` 的固定 512 样本 monitor 上评估；MAE 改善时覆盖更新 `checkpoint_best.pt`。

训练结束还会保存 `checkpoint_step_8800.pt`。论文主结果只能按 `val_dev` 选择 `checkpoint_best.pt`，不能使用 IID/OOD/extreme/seasonal 测试集挑模型。普通 step checkpoint 主要用于故障恢复；完成并确认结果后，若磁盘紧张可以清理它们，但建议保留 best 与三个关键 epoch 文件。

## 3. 本地暂存：目的、范围与安全规则

Stage2 的 NetCDF 从共享盘读取时，实测数据等待会明显大于 GPU 计算。启动器 `scripts/run_stage2_earthnet_local_staged.sh` 会把所需文件暂存到本机 `/tmp`，随后令 `DATA_ROOT` 自动指向本地 `EarthNet2021/`。这不改变模型、DGH、冻结 manifest 或统计量，只改变读取位置。

共享盘数据绝不会被删除或改写；checkpoint、TensorBoard、provenance 与日志始终保留在项目共享目录。此前全量 `earthnet2021x` 暂存观测到约 **219 GB**，因此启动器默认要求本地盘至少剩余 `250 GiB`。 `train_val` 暂存只复制当前训练和验证 monitor 所需文件，通常小于全量；具体大小以实际 manifest 为准。

### 3.1 三个运行开关

| 变量 | 取值 | 行为 |
| --- | --- | --- |
| `LOCAL_STAGE_CLEANUP` | `auto`（默认） | 正常成功、失败、`INT`/`TERM`/`HUP` 后自动清理本地暂存。 |
|  | `manual` | 保留已完成的本地缓存，适合 OOM 后快速重试；训练成功后也需要手动清理。 |
| `LOCAL_STAGE_DATA_SCOPE` | `all`（默认） | 暂存所有 EarthNet2021x NetCDF，适合未来全 split 评测。 |
|  | `train_val` | 仅暂存冻结 `train_dev.json` 与 `val_dev.json` 的去重并集；当前主实验推荐。 |
| `REQUIRE_EMPTY_GPUS` | `0`（默认） | 不额外检查 GPU 进程。 |
|  | `1` | 暂存前和训练前各检查一次 `nvidia-smi`；已有 compute 进程则拒绝启动。 |

默认旧行为仍然可用：`LOCAL_STAGE_CLEANUP=auto` 且 `LOCAL_STAGE_DATA_SCOPE=all`。

### 3.2 缓存复用、完整性与锁

每次启动都会重新生成本次所需文件清单，并核验：源数据根目录、scope、训练/验证 manifest 的 SHA-256、文件清单 SHA-256、计划文件数，以及每个本地 NetCDF 是否存在。仅在全部匹配时才复用，并显示：

```text
reusing verified local staging copy: ...
```

此时不会再次运行 `rsync`。未完成或不匹配的标记副本不会被误用：下次启动会安全清理后重新暂存。未带 ObsWorld marker 的 `/tmp` 目录绝不会被覆盖或删除。

同一个 `LOCAL_STAGE_ROOT` 同一时刻只允许一个 launcher；若提示 `another Stage2 local staging launcher already owns`，说明已有复制或训练正在使用缓存。不要删除 `.lock` 文件，也不要启动第二个 launcher。

## 4. 训练前检查

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

export P=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026
export R=$P/artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048
export C=$P/checkpoints

export CONDITIONING_STATS_PATH=$R/conditioning_stats_physical4_v1_train_dev.json
export MANIFEST_PATH=$R/train_dev.json
export VALIDATION_MANIFEST_PATH=$R/val_dev.json
export STAGE15_CHECKPOINT="$C/stage1_5_dual_conditioned_vits_state_bridge_60k/checkpoint_step_60000.pt"

test -s "$CONDITIONING_STATS_PATH" && echo "stats ok"
test -s "$MANIFEST_PATH" && echo "train manifest ok"
test -s "$VALIDATION_MANIFEST_PATH" && echo "val manifest ok"
test -f "$STAGE15_CHECKPOINT" && echo "Stage1.5 checkpoint ok"

nvidia-smi
```

开始前应看到 `No running processes found`。 `REQUIRE_EMPTY_GPUS=1` 会在 launcher 中再次检查，避免外部进程抢占显存后才报 OOM。

可选回归检查：

```bash
pytest -q tests/test_stage2_checkpoint_schedule.py \
  tests/test_stage2_local_staging_scripts.py tests/test_stage2_v2_contract.py
```

## 5. 推荐正式启动：可重试的 train+val 本地缓存

当前主实验只使用 train manifest 与 validation monitor，因此推荐 `manual + train_val`：首次复制完成后，即使训练 OOM 或被可捕获地中断，也不需重复制。以下路径都在单行中，复制时不要在路径中间按回车。

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

export P=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026
export D=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021
export R=$P/artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048
export C=$P/checkpoints
export L=$P/logs

export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export HDF5_USE_FILE_LOCKING=FALSE
export TORCH_NCCL_ASYNC_ERROR_HANDLING=1
export NCCL_DEBUG=WARN
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

export CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml
export DATA_ROOT=$D
export CONDITIONING_STATS_PATH=$R/conditioning_stats_physical4_v1_train_dev.json
export MANIFEST_PATH=$R/train_dev.json
export VALIDATION_MANIFEST_PATH=$R/val_dev.json
export STAGE15_CHECKPOINT="$C/stage1_5_dual_conditioned_vits_state_bridge_60k/checkpoint_step_60000.pt"

test -f "$STAGE15_CHECKPOINT" && echo "Stage1.5 checkpoint ok" || { echo "Stage1.5 checkpoint NOT FOUND"; exit 1; }

export RUN_ID=stage2_physical4_8gpu_b64_200ep_trainvalcache_$(date +%Y%m%d_%H%M%S)
export CHECKPOINT_DIR=$C/$RUN_ID
export LOG_DIR=$L/$RUN_ID

export MAX_STEPS=8800
export BATCH_SIZE=64
export NUM_WORKERS=8
export PREFETCH_FACTOR=1
export PERSISTENT_WORKERS=1
export LOG_INTERVAL=50
export GPUS=8

export REQUIRE_MANIFEST=1
export PREFLIGHT=1
export PREFLIGHT_MAX_FILES=16
export PREFLIGHT_CHECK_MODEL=1
export RUN_TRAIN=1
export PREFLIGHT_OUTPUT=$LOG_DIR/preflight_local_stage.json

export LOCAL_STAGE_ROOT=/tmp/${USER}_obsworld_stage2_earthnet2021x_trainval
export LOCAL_STAGE_CLEANUP=manual
export LOCAL_STAGE_DATA_SCOPE=train_val
export REQUIRE_EMPTY_GPUS=1
export MIN_LOCAL_FREE_GB=250

mkdir -p "$CHECKPOINT_DIR" "$LOG_DIR"

test -s "$CONDITIONING_STATS_PATH" && echo "stats ok"
test -s "$MANIFEST_PATH" && echo "train manifest ok"
test -s "$VALIDATION_MANIFEST_PATH" && echo "val manifest ok"

nvidia-smi

nohup bash scripts/run_stage2_earthnet_local_staged.sh > "$LOG_DIR/launcher.log" 2>&1 &
echo $! | tee "$LOG_DIR/launcher.pid"

echo "RUN_ID=$RUN_ID"
echo "LOG_DIR=$LOG_DIR"
echo "CHECKPOINT_DIR=$CHECKPOINT_DIR"
echo "LOCAL_STAGE_ROOT=$LOCAL_STAGE_ROOT"
```

如果 launcher 输出 GPU 已占用，先等待 GPU 空闲再启动；不要为了绕开保护而盲目设 `REQUIRE_EMPTY_GPUS=0`。此前 B64 的 OOM 是外部进程已占约 108 GiB 显存，并不证明 B64 对 H200 本身不可行。

### 5.1 保留全量（all scope）启动版本

代码支持完整 EarthNet 暂存版本。若后续需要本地完成 IID/OOD/extreme/seasonal 等全 split 评测，或不希望使用 manifest-only scope，请使用上面完整命令，但替换为以下设置，并使用不同本地目录：

```bash
export RUN_ID=stage2_physical4_8gpu_b64_200ep_allcache_$(date +%Y%m%d_%H%M%S)
export CHECKPOINT_DIR=$C/$RUN_ID
export LOG_DIR=$L/$RUN_ID
export PREFLIGHT_OUTPUT=$LOG_DIR/preflight_local_stage.json

export LOCAL_STAGE_ROOT=/tmp/${USER}_obsworld_stage2_earthnet2021x_all
export LOCAL_STAGE_CLEANUP=auto
export LOCAL_STAGE_DATA_SCOPE=all
export REQUIRE_EMPTY_GPUS=1
export MIN_LOCAL_FREE_GB=250

mkdir -p "$CHECKPOINT_DIR" "$LOG_DIR"
nohup bash scripts/run_stage2_earthnet_local_staged.sh > "$LOG_DIR/launcher.log" 2>&1 &
echo $! | tee "$LOG_DIR/launcher.pid"
```

上述替换应在完整命令的 `mkdir -p` 与 `nohup` 行之前完成。`all` 复制量接近全量数据，
不建议为了当前 train+val 主训练而使用它；它保留了不使用 manifest-only scope 的完整运行路线。

## 6. 进度、暂存和 GPU 监控

启动后，优先从 launcher 日志确认处于复制还是训练阶段。为避免长路径误换行，可先进入对应日志目录：

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs
cd <RUN_ID>
tail -F launcher.log | tr '\r' '\n'
```

暂存阶段会出现 `local staging starts` 与 rsync 进度；出现下列两行后代表复制成功并转入训练：

```text
local staging verified
training starts
```

此后查看训练 loss、吞吐、data/compute 时间：

```bash
tail --retry -F train_200epoch.log
```

实时查看显存与利用率：

```bash
watch -n 2 nvidia-smi
```

查看普通、关键 epoch 与 best checkpoint：

```bash
watch -n 30 'find "$CHECKPOINT_DIR" -maxdepth 1 -type f -name "checkpoint*.pt" -printf "%f %s bytes\n" | sort'
```

`Ctrl+C` 只会退出 `tail` 或 `watch`，不会停止后台训练。

## 7. 中断、重试与清理

`LOCAL_STAGE_CLEANUP=manual` 时：

- 训练成功、训练报错、OOM、`Ctrl+C`、`TERM` 或 `HUP` 后，启动器不自动删除本地副本。
- 若本地副本已完成并通过 metadata 校验，下次使用**相同** `LOCAL_STAGE_ROOT`、相同 manifest 与 scope 启动，会直接复用，不再 rsync。
- 若在 rsync 尚未完成时中断，残缺文件会暂时留在 `/tmp`；下一次会识别它不完整、安全清理后重复制，不能将它视为可复用完成缓存。

`LOCAL_STAGE_CLEANUP=auto` 时，正常成功、失败和可捕获的 `INT`/`TERM`/`HUP` 都会自动删除副本。 `kill -9` 和节点重启无法执行 shell trap；此时本地目录通常仍在，可在恢复后手动清理。

清理前先确保没有 launcher 占锁。下面命令只接受 `/tmp` 下带正确 marker 的目录，不会删除共享盘数据、checkpoint 或日志：

```bash
bash scripts/cleanup_stage2_earthnet_local_staged.sh \
  --stage-root "$LOCAL_STAGE_ROOT" --force
```

可先核验缓存与 metadata：

```bash
du -sh "$LOCAL_STAGE_ROOT"
test -f "$LOCAL_STAGE_ROOT/.obsworld_stage2_local_stage_metadata.env" && \
  sed -n '1,120p' "$LOCAL_STAGE_ROOT/.obsworld_stage2_local_stage_metadata.env"
```

若希望主动停止仍在运行的 launcher，优先使用 `TERM`，不要先用 `kill -9`：

```bash
kill -TERM "$(cat "$LOG_DIR/launcher.pid")"
```

## 8. 训练完成后的核对

```bash
find "$CHECKPOINT_DIR" -maxdepth 1 -type f \
  -name 'checkpoint*.pt' -printf '%f\t%s bytes\n' | sort

grep -E 'named epoch checkpoints|checkpoint saved|validation step=|new best' \
  "$LOG_DIR/train_200epoch.log" | tail -80
```

若未来因为显存或稳定性必须改变 per-GPU batch，不能沿用这里的 `4400/6600/8800`：必须按新的实际 DataLoader 长度重新换算 epoch step，并同步调整关键 checkpoint 计划。
