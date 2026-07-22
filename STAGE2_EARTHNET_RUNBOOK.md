# ObsWorld Stage2 EarthNet2021x 执行手册

> 当前正式主线：服务器已有的 raw `EarthNet2021x` NetCDF + 原版物理 DGH
> `physical4_v1`。本手册中的 `Direct physical4` 是首个主实验；`Rollout` 和
> `Partition` 在 Direct 链路稳定后使用同一份数据协议。旧的 `legacy_direct9`
> 和完整 `full24` 保留为独立兼容/对照，不得与本手册的统计文件混用。

详细设计说明见：
`思路整理进展/55_ObsWorld_原版DGH正式训练代码完成与训前命令指南_20260716.md`。

## 1. 固定协议

- 数据根：`/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021/earthnet2021x`。
- 训练开发清单：`train_dev.json`；验证清单：`val_dev.json`。
- 最终固定训练可使用 `train_all.json`，但必须重新拟合 train-only 统计量。
- 主评测清单：`iid.json`、`ood.json`；压力测试：`extreme.json`、`seasonal.json`。
- 每个样本使用 10 帧上下文，预测未来 20 帧（`h=5,10,...,100` 天）。
- `D_path` 为 `[30,4]`：
  `precip_sum_5d`、`temp_mean_5d`、`vpd_mean_5d`、`srad_sum_5d`。
- `C_path` 为独立的年周期编码 `[30,2]`；`G` 为 `cop_dem`；`h` 和
  `delta_t_path` 的接口不变。
- VPD 由 `eobs_tg` 和 `eobs_hu` 推导，辐射由 `eobs_qq` 换算；缺失日由
  `D_mask` 显式标记，不能静默填成有效天气。

Stage1.5 不需要修改。Stage2 的 physical4 配置、统计文件、checkpoint（检查点）
和日志目录彼此隔离，避免改变已经完成的 Stage1.5 训练逻辑。

## 2. 环境和变量

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
git pull --ff-only origin main

export DATA_PARENT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021
export CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml
export RUN_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048
export STATS="$RUN_DIR/conditioning_stats_physical4_v1_train_dev.json"
export TRAIN_MANIFEST="$RUN_DIR/train_dev.json"
export VAL_MANIFEST="$RUN_DIR/val_dev.json"
export STAGE15_CHECKPOINT=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage1_5_dual_conditioned_vits_state_bridge_60k/checkpoint_step_60000.pt
```

如果重新冻结了协议目录，只需把 `RUN_DIR` 改成新的完整绝对路径；不要把路径
拆成两行，否则 shell（命令解释器）会把后半段当成新命令。

## 3. 数据协议冻结和统计量

这两步已经完成时不必重复运行。新数据版本必须重新执行：

```bash
mkdir -p artifacts/protocols logs

python -u scripts/freeze_earthnet2021x_protocol.py \
  --root "$DATA_PARENT/earthnet2021x" \
  --output-dir "artifacts/protocols/earthnet2021x_physical4_v1_$(date +%Y%m%d_%H%M%S)" \
  --val-tile-count 8 --seed 20260716 --hash-mode none \
  --workers 8 --progress-every 1000 \
  2>&1 | tee logs/earthnet_physical4_freeze.log
```

先做少量 smoke（冒烟）统计只用于检查字段，不能用于正式训练：

```bash
python -u scripts/build_earthnet_physical_stats.py \
  --config "$CONFIG" --data-root "$DATA_PARENT" \
  --manifest-path "$TRAIN_MANIFEST" \
  --output "$RUN_DIR/physical4_stats_smoke16.json" \
  --max-files 16 --workers 2 --progress-every 4
```

正式统计必须覆盖完整 `train_dev.json`：

```bash
nice -n 10 python -u scripts/build_earthnet_physical_stats.py \
  --config "$CONFIG" --data-root "$DATA_PARENT" \
  --manifest-path "$TRAIN_MANIFEST" \
  --output "$STATS" --require-full-train \
  --workers 4 --progress-every 100 \
  2>&1 | tee "$RUN_DIR/physical4_stats_train_dev.log"
test -s "$STATS" && echo "physical4 stats ready"
```

统计过程读取 NetCDF（网络数据文件）但不占 GPU；共享 NAS（网络存储）拥堵时把
`--workers` 降到 2，不要为了速度盲目开几十个进程。

## 4. 训练前 preflight（预检）

### 4.1 数据预检

```bash
CONFIG="$CONFIG" DATA_ROOT="$DATA_PARENT" \
CONDITIONING_STATS_PATH="$STATS" \
MANIFEST_PATH="$TRAIN_MANIFEST" \
VALIDATION_MANIFEST_PATH="$VAL_MANIFEST" \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 \
PREFLIGHT_CHECK_MODEL=0 RUN_TRAIN=0 \
PREFLIGHT_OUTPUT="$RUN_DIR/preflight_data16.json" \
bash run_stage2_earthnet.sh
```

报告必须满足：`ok=true`、`fatal_reasons=[]`、`driver_protocol=physical4_v1`，
且 `D_path` 为 `[30,4]`。`PREFLIGHT_MAX_FILES=16` 只控制抽查样本数，不会把
正式训练清单缩小为 16 个文件。

### 4.2 Stage1.5 模型预检

```bash
CONFIG="$CONFIG" DATA_ROOT="$DATA_PARENT" \
CONDITIONING_STATS_PATH="$STATS" \
MANIFEST_PATH="$TRAIN_MANIFEST" \
VALIDATION_MANIFEST_PATH="$VAL_MANIFEST" \
STAGE15_CHECKPOINT="$STAGE15_CHECKPOINT" \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 \
PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=0 \
PREFLIGHT_OUTPUT="$RUN_DIR/preflight_model16.json" \
bash run_stage2_earthnet.sh
```

这一步会加载 Stage1.5 的 `encoder_state_dict`、`phi_encoder_state_dict` 和
`state_projector_state_dict`，并验证 physical4 的模型维度。只有 `ok=true` 才能
启动 GPU 训练。

## 5. 首个主实验：Direct physical4

```bash
CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml \
DATA_ROOT="$DATA_PARENT" \
CONDITIONING_STATS_PATH="$STATS" \
MANIFEST_PATH="$TRAIN_MANIFEST" \
VALIDATION_MANIFEST_PATH="$VAL_MANIFEST" \
STAGE15_CHECKPOINT="$STAGE15_CHECKPOINT" \
CHECKPOINT_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_earthnet_v2_direct_physical4 \
LOG_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs/stage2_earthnet_v2_direct_physical4 \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 \
PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=1 \
GPUS=1 BATCH_SIZE=2 NUM_WORKERS=4 MAX_STEPS=50000 \
bash run_stage2_earthnet.sh 2>&1 | tee "$RUN_DIR/stage2_direct_physical4.log"
```

训练输出中应出现：

- `Stage2-v2 physical4_v1` 或等价的解析配置信息；
- `EarthNet samples: 22847`；
- `Stage2 provenance written`；
- 周期性的 `loss/total`、`obs`、`NDVI` 和 validation（验证集）指标；
- `checkpoint_step_*.pt` 与 `checkpoint_best.pt`。

如果正式训练只想先做真实数据短跑，可将 `MAX_STEPS=2`、`BATCH_SIZE=1`、
`NUM_WORKERS=0`，但该结果只能作为链路 smoke，不可作为论文结果。

## 6. 训练后的评测顺序

先用 `val_dev` 选择 checkpoint；`iid`、`ood`、`extreme`、`seasonal` 只在选择
完成后评测。预测与评分必须使用同一份配置、同一份 physical4 stats 和对应清单。

```bash
export STAGE2_CHECKPOINT=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_earthnet_v2_direct_physical4/checkpoint_best.pt

python -u eval/eval_stage2_earthnet.py \
  --config "$CONFIG" --checkpoint "$STAGE2_CHECKPOINT" \
  --split val --data-root "$DATA_PARENT" \
  --conditioning-stats-path "$STATS" \
  --manifest-path "$VAL_MANIFEST" \
  --batch-size 2 --num-workers 4 \
  --output "$RUN_DIR/eval_val_direct_physical4.json"
```

正式测试时将 `--split` 和 manifest 替换为 `iid.json`、`ood.json` 等对应文件，
并使用新的输出目录。`eval/predict_stage2_earthnet.py` 会写出带来源记录的
`prediction_manifest.json`；`eval/score_earthnet_prediction_dir.py` 要求该清单与
预测文件完全一致，防止混入其他 checkpoint 的结果。

### 6.1 官方 ENS 评测的完整性字段（新结果必看）

`--official-score` 的输出现在自描述评测口径，正式跑新结果时按下面用：

- **`--per-cube-output <path>`**：落盘每个 cube 的 `MAD/OLS/EMD/SSIM/ENS`（非有限值写 `null`）。
  **算配对 bootstrap CI / Rollout-vs-Direct / ours-vs-persistence 显著性时必须带上**，否则只有点估计。
- 输出 `metrics` 里新增：
  - `eval_context_frames` / `eval_target_frames`：本次实际用的帧协议。
  - `official_protocol_match` / `is_truncated_diagnostic`：与官方 EarthNet2021 协议
    （iid/ood 10→20、extreme 20→40、seasonal 70→140）是否一致。**extreme/seasonal 在
    冻结的 30-token earthnet2021x 上必为 `is_truncated_diagnostic: true`**——下游不得把它当官方值混入 iid/ood 表。
  - `num_finite_{MAD,OLS,EMD,SSIM}`：各子分实际参与平均的 cube 数（全遮挡 cube 的 SSIM 会被官方打分器判为无效），用于识别"某分量被少数 cube 平均"的情况。
- **打分器一致性回归**：`.conda/envs/WorldModel/bin/python eval/parity_inline_vs_official_ens.py`
  必须 `PARITY OK`（退出码 0）。改动 `eval/earthnet_standard_metrics.py` 后务必重跑——它保证 inline 累加器与官方 `EarthNetScore.get_ENS` 数值一致（当前 max 分量差 4e-4）。
- **mask 极性守卫**：`metrics.mask_valid_fraction` 是目标 mask 的 clear/有效像素占比。正常 iid/ood 应在合理区间（例如 0.6–0.95）；若某次跌到 ~0 或跳到 ~1，多半是 `clear_mask` 极性被改坏（应为 1==有效），需排查再采信该次 ENS。
- **手稿路径协议贯通**：`eval/predict_stage2_earthnet.py` 的 `prediction_manifest.json` 现在带 `context_frames/target_frames` 与 `is_truncated_diagnostic`；`eval/assemble_stage2_table1.py` 在装 iid/ood 行时会**拒绝**被喂入非对应或截断诊断（extreme/seasonal）的 split，防止把 10→20 诊断值混进官方主表。

## 7. 后续 World Model 变体

Direct 数据链路稳定后，保持 `DATA_ROOT`、`STATS`、`TRAIN_MANIFEST`、
`VAL_MANIFEST` 和 Stage1.5 初始化完全相同，仅切换配置和输出目录：

```bash
CONFIG=configs/train/stage2_earthnet_v2_rollout_physical4.yaml \
CHECKPOINT_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_earthnet_v2_rollout_physical4 \
LOG_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs/stage2_earthnet_v2_rollout_physical4 \
... bash run_stage2_earthnet.sh

CONFIG=configs/train/stage2_earthnet_v2_partition_physical4.yaml \
CHECKPOINT_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_earthnet_v2_partition_physical4 \
LOG_DIR=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/logs/stage2_earthnet_v2_partition_physical4 \
... bash run_stage2_earthnet.sh
```

这里的 `...` 只表示复用上一条命令中的数据、统计量、清单、checkpoint 和
`REQUIRE_MANIFEST/PREFLIGHT` 参数，实际执行时应展开为完整环境变量；不要把
省略号直接交给 shell。

## 8. 禁止事项和证据保留

- 不把旧 `dgh_stats_train.json`、full24 stats 或 legacy checkpoint 传给 physical4。
- 不在 `iid/ood` 上调参或挑 checkpoint。
- 不使用 `train_all` 的统计量配 `train_dev` 训练，反之亦然。
- 不修改 Stage1.5 代码、权重或训练脚本来适配 Stage2。
- 保留 audit JSON、协议 `protocol.json`、所有 manifest、stats JSON、两个 preflight
  JSON、Stage2 `run_provenance.json`、训练日志和评测 sidecar（来源记录）。

出现错误时，先查看对应 JSON 的 `fatal_reasons` 和日志末尾，不要跳过 preflight
或用旧统计量强行启动。
