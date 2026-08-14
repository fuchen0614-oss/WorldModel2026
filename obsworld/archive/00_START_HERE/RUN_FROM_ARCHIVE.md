# 从精选归档继续 Stage 1 → Stage 1.5

这份说明把冻结代码快照转换为可操作入口。`01_CODE_SNAPSHOT/` 和
`02_CONFIGS/` 保留原始 commit 的字节，不为了可移植性篡改历史文件；运行前应复制
配置到新的实验目录并修改路径。

## 1. 当前能做什么

- Stage 1 和 Stage 1.5 的核心 Python 入口已完成真实导入验证。
- 代码、模型、损失、数据读取、phi 构建和 probe 入口均已归档。
- 数据集、phi cache 和 checkpoint 二进制未复制进来。
- 若找回 Stage 1 95k 权重，可以直接继续 Stage 1.5。
- 若权重无法找回，只能从 Stage 1 重新训练，不能从结果文档还原参数。

## 2. 建议目录变量

```bash
ARCHIVE=/path/to/ObsWorld_STAGE1_TO_STAGE1_5_CURATED_20260730
CODE=$ARCHIVE/01_CODE_SNAPSHOT
CONFIGS=$ARCHIVE/02_CONFIGS/configs
TOOLS=$ARCHIVE/03_TRAINING_AND_EVAL
DATA=/path/to/SSL4EO-S12-v1.1
RUNS=/path/to/new_experiment_outputs

export PYTHONPATH="$CODE:${PYTHONPATH:-}"
```

不要直接运行归档中的旧 shell。它们保留了原服务器绝对路径，作用是复盘真实运行
方式。正式重跑时应新建自己的 launcher。

## 3. 数据与缓存

Stage 1 需要 SSL4EO-S12 v1.1 的 S1 GRD 与 S2 L2A 数据。Stage 1.5 另外需要：

- `$DATA/phi_processed`
- `$DATA/phi_processed_v3_s1geom`

相关构建代码位于：

- `03_TRAINING_AND_EVAL/scripts/build_phi_cache.py`
- `03_TRAINING_AND_EVAL/scripts/build_phi_cache_v2.py`
- `03_TRAINING_AND_EVAL/scripts/build_phi_v3_s1geom.py`

构建后先运行 `test_dual_dataloader.py` 和 `verify_alignment.py`，确认样本 ID、
时间配对与 phi 字段一致，再开始大规模训练。

## 4. Stage 1

复制并修改：

`02_CONFIGS/configs/train/stage1_vits_dual_staged.yaml`

至少替换：

- `data.data_root`
- `checkpoint_dir`

然后在代码根目录运行：

```bash
cd "$CODE"
torchrun --standalone --nproc_per_node=8 \
  -m train.train_stage1_vits \
  --config /path/to/edited_stage1_vits_dual_staged.yaml
```

冻结计划的最终初始化点是 95,000 steps。只有实际 checkpoint 能证明该状态存在。

## 5. Stage 1.5

复制并修改：

`02_CONFIGS/configs/train/stage1_5_dual_conditioned_vits_state_bridge_60k.yaml`

至少替换：

- `data.data_root`
- `data.phi_cache_root`
- `data.v3_geom_root`
- `resume_from`
- `checkpoint_dir`

其中 `resume_from` 必须指向 Stage 1 的 95k checkpoint。运行：

```bash
cd "$CODE"
torchrun --standalone --nproc_per_node=8 \
  -m train.train_stage1_5_dual_conditioned \
  --config /path/to/edited_stage1_5_state_bridge_60k.yaml
```

## 6. 结果门禁

恢复或重训后，至少重新确认：

1. checkpoint 能在 CPU 和单卡上加载；
2. S1/S2 reconstruction 与 alignment 指标可复现；
3. nonlinear phi leakage probe 能运行；
4. 结果与 `04_RESULTS/29_Stage1.5_30k_vs_60k_Phi泄漏对比.md` 对齐；
5. 不以低 cross-covariance 代替非线性解耦证明。

当前最重要的后续方法问题不是继续堆训练步数，而是改进对非线性 nuisance
信息的约束，并检验更强解耦是否真正改善后续动力学。
