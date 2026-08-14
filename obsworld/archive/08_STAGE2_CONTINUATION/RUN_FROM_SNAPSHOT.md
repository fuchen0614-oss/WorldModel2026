# 从 Stage2 快照继续

## 1. 本地无数据验证

```bash
SNAP=/mnt/data/users/luzheng/workspace/iclr/czj/ObsWorld_STAGE1_TO_STAGE1_5_CURATED_20260730/08_STAGE2_CONTINUATION/01_CODE_SNAPSHOT
cd "$SNAP"
export PYTHONPATH="$SNAP"
python scripts/smoke_plan_a_prime.py
python -m pytest -q \
  tests/test_aprime_eval.py \
  tests/test_obsworld_direct_path.py \
  tests/test_stage2_v2_contract.py \
  tests/test_stage2_v2_training_utils.py \
  tests/test_stage2_components.py
```

预期结果分别为 `13/13 PASS` 和 `32 passed`。

## 2. 正式训练前需要补齐

- GreenEarthNet/EarthNet2021x 训练与 validation 数据；
- 冻结的 train/validation manifest；
- physical4 conditioning stats；
- 首选 A2-best 完整 Stage2 checkpoint或 Stage1.5 checkpoint；若二者仍不可得，
  可使用 `03_KEY_WEIGHTS/direct_physical4/checkpoint_best.pt` 或
  `03_KEY_WEIGHTS/rollout_physical4/checkpoint_best.pt` 作为明确标注的历史起点；
- 独立的 checkpoint/log 输出目录。

## 3. metric-aligned 路线命令骨架

以下只是完整参数骨架，不能在缺少真实路径时直接运行：

```bash
SNAP=/path/to/a/writable/copy/of/01_CODE_SNAPSHOT
cd "$SNAP"
export PYTHONPATH="$SNAP"

CONFIG=configs/train/plan_a_metric_v1.yaml \
DATA_ROOT=/path/to/GreenEarthNet \
INIT_FROM_CHECKPOINT=/path/to/A2-best-checkpoint.pt \
CONDITIONING_STATS_PATH=/path/to/physical4-train-stats.json \
MANIFEST_PATH=/path/to/frozen-train-manifest.json \
VALIDATION_MANIFEST_PATH=/path/to/frozen-validation-manifest.json \
CHECKPOINT_DIR=/path/to/new-checkpoints \
LOG_DIR=/path/to/new-logs \
GPUS=8 \
MAX_STEPS=14880 \
BATCH_SIZE=1 \
NUM_WORKERS=8 \
bash run_stage2_earthnet.sh
```

建议从精选归档复制出一个可写工作副本再修改；归档本身继续作为来源基准。
