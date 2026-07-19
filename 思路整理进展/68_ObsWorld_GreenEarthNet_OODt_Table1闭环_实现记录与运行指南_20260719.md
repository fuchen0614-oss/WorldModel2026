# 68 ObsWorld GreenEarthNet OOD-t Table 1 闭环：实现记录与运行指南

日期：2026-07-19
状态：代码闭环已接通；CVPR-2024 Table 2 公开参考行已自动预填；本文 Direct/Rollout 数值待目标服务器执行 OOD-t evaluation-only 推理
关联：[[58_ObsWorld_AAAI27中文论文终稿_主实验冻结版_20260717]]、[[63_ObsWorld_U与正式评估闭环_概念代码审查指标协议与执行指南_20260718]]、[[67_ObsWorld_核心叙事_相关工作差异_Table1数值与下一步_20260719]]

---

## 0. 一句话结论

项目此前已经有不少评估代码：完整 `val_dev` 选 checkpoint、raw EarthNet2021x 的 RGBN/ENS 诊断、NDVI 转换与评分。此次补的是**另一条明确的、论文主表专用的 GreenEarthNet CVPR-2024 `ood-t_chopped` 闭环**，不是重新造评估器，也不是重新训练 Direct-P4。

目标服务器已经确认存在以下正式评估资产，因此**不需要再次下载 GreenEarthNet**：

```text
/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/ood-t_chopped
/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/iidx
```

正式主表路径是：

```text
冻结 ood-t_chopped manifest
  → 只对已训练 checkpoint 做推理（Direct/Rollout：20 个五日点）
  → 官方 Persistence（20 个五日点）/ 官方 Climatology（从原始 index 50 起的每日点）
  → 严格 GreenEarthNet scorer（prediction grid 写入 provenance）
  → 与独立官方 evaluator 数值对齐
  → 对两个 deterministic baseline 与独立公开 baseline 实现做 reference parity
  → provenance-bound Table 1
```

任何 raw EarthNet2021x IID/OOD + ENS 结果仍可保留为内部诊断/补充材料，但不能和本节 OOD-t chopped 主表混写成同一协议。

### 0.1 训练数据、选模数据和最终测试数据的关系

[GreenEarthNet 官方仓库](https://github.com/vitusbenson/greenearthnet)也使用 `earthnet2021x` / `en21x` 作为开发期标识；[CVPR-2024 论文](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html)明确写明 GreenEarthNet 与 EarthNet2021 保持相同训练地点和时空尺寸，并在 Table 2 中评估了直接复用 EarthNet2021 权重的模型。因此，本文在现有 EarthNet2021x raw train 上训练、到 GreenEarthNet OOD-t 做冻结测试，是有官方先例的兼容/迁移评测，而不是随意用 benchmark B 挑结果。

但这不等于训练发布完全相同：GreenEarthNet 引入了改进的云 mask 和新的植被评估；当前也没有另存一份 Green `train/` 与 raw train 做逐文件 hash 对齐。因此准确表述必须是“训练规模与地点/时空协议兼容，最终测试口径相同”，而不是“和 Contextformer 使用逐字节相同的训练文件”。正式数据流是：

```text
EarthNet2021x raw train：23,816（规模与官方 Green Train 一致）
  ├─ train_dev 22,847：梯度更新
  └─ val_dev      969：完整验证、选择 checkpoint_best.pt
                              ↓
ood-t_chopped：独立的 2021–2022 temporal-OOD 最终测试

iidx：仅供官方 Climatology 构造，不用于 Direct/Rollout 训练
```

因此：

1. `train_dev` 决定模型学到了什么；
2. `val_dev` 只在预先固定的候选 checkpoint 中选一个，不进入最终主表；
3. checkpoint 冻结后才打开 `ood-t_chopped` 做一次正式 Table 1 测试；
4. Direct、Rollout、Persistence、Climatology 必须复用同一个 frozen OOD-t manifest、mask 和 scorer；
5. 公共方法使用 Benson et al., CVPR 2024 Table 2 的同轨道报告值，属于 benchmark-level 同测试协议比较；其中重新在 GreenEarthNet 训练的公开行与本文不具备完全相同的训练条件，不能写成严格受控对照；
6. Direct 与 Rollout 使用相同 raw train、内部 split、初始化、预算和 scorer，是更严格的 paired comparison；
7. 本项目从 23,816 个 raw train 中留出 969 个样本做内部选模，实际梯度训练量为 22,847；这是一项偏保守且必须披露的差异，不构成测试泄漏。

模型输入前 10 个五日 context，输出后 20 个五日预测点（100 天）。`ood-t_chopped` 提供最终目标与 mask；`iidx` 只用于 Climatology。已有 `val_dev` MAE 是选模诊断，不能直接填入 OOD-t Table 1。

---

## 1. 当前已完成与尚缺内容

### 已完成的代码能力

1. **协议隔离**
   - `greenearthnet_cvpr2024_chopped_v1` 是独立 manifest 协议；`ood-t_chopped` 不能被映射为 raw `ood`。
   - 所有正式 exporter、baseline、score 都校验 frozen manifest 的文件身份、protocol、track 和 hash 记录。

2. **训练 checkpoint 的正式推理**
   - `eval/export_greenearthnet_predictions.py` 可加载 Direct-P4 或 Rollout-P4 checkpoint，输出 20 个官方五日预测时间点的 `ndvi_pred` NetCDF，并在 `prediction_manifest.json` 固定写入 `prediction_grid=official_5day_20`。
   - 不需要重新训练 Direct-P4。

3. **正式 deterministic baselines**
   - `eval/generate_baseline_predictions.py --baseline persistence` 复现公开 GreenEarthNet 的五日 context persistence，输出 20 个五日点。
   - `--baseline climatology` 使用 OOD-t 对应 full `iidx/<cubename>.nc` minicube，做 leave-target-year-out 的像素级 climatology。公开源码本身输出 `target.time.isel(time=slice(50, None))`：在通常的 150 日 minicube 上即 **100 个每日点**，而不是 20 个五日点。
   - 这是公开实现的时间网格不对称，不是本项目私自引入的重采样。代码会把它记录成 `official_climatology_day50_daily`；禁止把它无声压成 20 步后再称“官方 Climatology”。

4. **正式评分与表格**
   - `eval/score_table1_greenearthnet.py` 输出 R²、RMSE、NSE、absolute bias、RMSE25；它读取 prediction manifest 的 grid，并拒绝不兼容的 comparison。非 Climatology 的 Outperformance 只允许相对同一 frozen manifest 的公开 Climatology score。
   - `eval/assemble_greenearthnet_oodt_table1.py` 生成 CSV、Markdown、JSON bundle；每行都校验应有的 grid（Climatology=daily，其余=20-step）。缺少行、官方 evaluator parity 或 deterministic baseline reference parity 时，bundle 都会显式标为 `partial/provisional`。
   - 输出中的 `RMSE25†` 会保留公开 evaluator 的 `rmse_0_5` 数值，同时标注网格语义：20-step 行的前五点是前 25 天，daily Climatology 的前五点是 5 天。不能把这两个单元格解释成严格等 horizon 的横向排名；主结论应优先看经 parity 的 R² / RMSE / NSE / bias / Outperformance。
   - `eval/greenearthnet_published_table2.py` 冻结保存 Benson et al., CVPR 2024 Table 2 的 Persistence、Previous year、Climatology、Earthformer、PredRNN、SimVP、Contextformer 报告值。assembler 会将这些行自动放入同一张 Markdown/CSV，并用 `result_source=published_reference` 标记；若同一 method 已有本地评分行，本地行会替换显示对应公开行。

5. **预检与安全运行**
   - `scripts/preflight_greenearthnet_oodt_table1.py` 是只读预检：同时抽查 Stage2 的 150-day 输入契约、20-step 五日网格，以及 Climatology 的 day-50-plus 每日网格。
   - `scripts/run_stage2_table1_greenearthnet_oodt.sh` 是 evaluation-only runner：不会训练、不会删除本地缓存或数据。

### 仍然缺少的真实实验产物

- GreenEarthNet OOD-t chopped 的 frozen manifest（数据已存在，仍需由目标服务器真实目录冻结）；
- Direct-P4 checkpoint 的正式 OOD-t prediction + score；
- Rollout-P4 训练结束、完整 `val_dev` 选 checkpoint 后的正式 OOD-t prediction + score；
- 同一 manifest 上 Persistence / Climatology score；
- 用独立 checkout 的公开 GreenEarthNet evaluator 对每个本地 score 做数值 parity；
- 用独立 checkout 的公开 Persistence / Climatology 实现分别产生 reference score，确认本地 deterministic baseline 的构造也一致；公开方法行及来源已经冻结进代码，不再是缺项。

所以：**当前 Direct-P4 的完整 `val_dev` 结果只能证明选模完成，不是 Table 1 OOD-t 数值。**

---

## 2. 路径确认：先审计，绝不猜目录

在实际服务器的 WorldModel2026 根目录执行。`RAW_ROOT` 是 raw EarthNet2021x 训练根；`GREEN_EVAL_ROOT` 是 GreenEarthNet 评估根。本次 Table 1 必需的是其中的 `ood-t_chopped/` 与 `iidx/`；它不要求为了评估重新下载 Green `train/` 或 `val_chopped/`。

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

export P=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026
export RAW_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021
export GREEN_EVAL_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet
export EVAL_ROOT=$P/evaluations/greenearthnet_oodt_$(date +%Y%m%d_%H%M%S)
mkdir -p "$EVAL_ROOT"

python scripts/audit_greenearthnet_layout.py \
  --raw-root "$RAW_ROOT" \
  --eval-root "$GREEN_EVAL_ROOT" \
  --sample-schema \
  --output "$EVAL_ROOT/layout_audit.json" \
  --strict-main
```

只有 audit 明确显示 `ood-t_chopped` 非空、抽样 schema 通过后，才继续。目录不对时停在这里修路径，不允许以 raw `ood` 替代。`--strict-main` 还会要求完整主布局中的 `train/` 与 `val_chopped/`；如果服务器仅保留了本次 Table 1 必需的 `ood-t_chopped/` 和 `iidx/`，可去掉该参数，后续 frozen-manifest strict preflight 仍会严格检查本次实际使用的 OOD-t 文件。

---

## 2.1 当前服务器：Direct-P4 一键后台正式评估

下面是一段可以整体复制的 evaluation-only 命令。它不会训练、不会修改 checkpoint，也不会删除 `EarthNet2021`、`GreenEarthNet` 或本地训练缓存。默认使用 GPU 0；启动前会检查该卡显存占用，若超过 500 MiB 只打印错误并拒绝启动，不会用 `exit 1` 杀掉当前 VS Code 终端。

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

git pull --ff-only origin main

export P=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026
export RAW_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021
export GREEN_EVAL_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet
export CONDITIONING_STATS_PATH=$P/artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048/conditioning_stats_physical4_v1_train_dev.json
export DIRECT_CHECKPOINT=$P/checkpoints/stage2_physical4_8gpu_b64_200ep_trainvalcache_20260717_165126/checkpoint_best.pt

# 改成一张当前空闲的卡；单卡即可，评估不需要重新占 8 卡。
export EVAL_GPU=0
export CUDA_VISIBLE_DEVICES=$EVAL_GPU
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export HDF5_USE_FILE_LOCKING=FALSE
export PYTHONPATH=$P:${PYTHONPATH:-}
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

export RUN_ID=table1_greenearthnet_oodt_direct_$(date +%Y%m%d_%H%M%S)
export EVAL_ROOT=$P/evaluations/$RUN_ID
export OODT_MANIFEST=$EVAL_ROOT/greenearthnet_oodt_chopped_manifest.json

export CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml
export CHECKPOINT=$DIRECT_CHECKPOINT
export METHOD_ID=direct-p4
export METHOD_LABEL=Direct-P4
export METHOD_KIND=paired-direct
export METHOD_PARAMS_MILLIONS=28.17
export METHOD_SEED=42

export RUN_PREFLIGHT=1
export RUN_BASELINES=1
export RUN_MODEL=1
export RUN_ASSEMBLE=1
export MODEL_BATCH_SIZE=16
export MODEL_NUM_WORKERS=8
export SCORE_WORKERS=8
export HASH_MODE=sha256
export VERIFY_MANIFEST_SIZES=0
export CLIMATOLOGY_FULL_CUBE_ROOT=$GREEN_EVAL_ROOT/iidx

mkdir -p "$EVAL_ROOT"

launch_ready=1
for required_path in \
  "$GREEN_EVAL_ROOT/ood-t_chopped" \
  "$GREEN_EVAL_ROOT/iidx" \
  "$DIRECT_CHECKPOINT" \
  "$CONDITIONING_STATS_PATH"
do
  if [[ -e "$required_path" ]]; then
    echo "OK: $required_path"
  else
    echo "MISSING: $required_path"
    launch_ready=0
  fi
done

gpu_used_mib=$(nvidia-smi -i "$EVAL_GPU" --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
echo "GPU $EVAL_GPU memory.used=${gpu_used_mib} MiB"
if [[ ! "$gpu_used_mib" =~ ^[0-9]+$ ]] || (( gpu_used_mib > 500 )); then
  echo "GPU $EVAL_GPU 不是空闲卡；请修改 EVAL_GPU 后重新执行。"
  launch_ready=0
fi

if [[ "$launch_ready" == 1 ]]; then
  nohup bash -c '
    set -euo pipefail
    cd "$P"

    python scripts/audit_greenearthnet_layout.py \
      --raw-root "$RAW_ROOT" \
      --eval-root "$GREEN_EVAL_ROOT" \
      --sample-schema \
      --output "$EVAL_ROOT/layout_audit.json"

    python scripts/freeze_greenearthnet_chopped_protocol.py \
      --eval-root "$GREEN_EVAL_ROOT" \
      --track ood-t_chopped \
      --output "$OODT_MANIFEST" \
      --hash-mode sha256 \
      --audit-report "$EVAL_ROOT/layout_audit.json"

    bash scripts/run_stage2_table1_greenearthnet_oodt.sh
  ' > "$EVAL_ROOT/table1_eval.log" 2>&1 &

  echo $! | tee "$EVAL_ROOT/table1_eval.pid"
  echo "RUN_ID=$RUN_ID"
  echo "EVAL_ROOT=$EVAL_ROOT"
  echo "LOG=$EVAL_ROOT/table1_eval.log"
else
  echo "正式评估未启动；修正上面的 MISSING/GPU 提示后重试。"
fi
```

新终端中查看进度时，把下方 `RUN_ID` 替换为启动命令打印的真实值：

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
export P=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026
export RUN_ID=table1_greenearthnet_oodt_direct_实际时间戳
export EVAL_ROOT=$P/evaluations/$RUN_ID

ps -p "$(cat "$EVAL_ROOT/table1_eval.pid")" -o pid,etime,stat,%cpu,%mem,cmd
tail --retry -F "$EVAL_ROOT/table1_eval.log"
```

日志前半段长时间处于 manifest SHA256、Climatology 或 Persistence 的 CPU/I/O 阶段时，GPU 为空是正常的；进入 `export_greenearthnet_predictions.py` 后才会使用 GPU。另一个窗口可执行：

```bash
watch -n 2 nvidia-smi
```

完成后直接读取：

```bash
cat "$EVAL_ROOT/table1_oodt_chopped/table1_oodt_chopped.md"
python -m json.tool "$EVAL_ROOT/direct-p4/oodt_chopped/score/metrics_en21x.json"
```

核心产物是：

```text
$EVAL_ROOT/greenearthnet_oodt_chopped_manifest.json
$EVAL_ROOT/baselines_oodt_chopped/{climatology,persistence}/score/metrics_en21x.json
$EVAL_ROOT/direct-p4/oodt_chopped/score/metrics_en21x.json
$EVAL_ROOT/table1_oodt_chopped/table1_oodt_chopped.{md,csv,json}
```

首次本地评分完成后，Table 1 会包含公开论文参考行、本地 Persistence/Climatology 和真实 Direct-P4 行；在独立官方 evaluator/reference parity 尚未补齐时，bundle 会诚实标为 `provisional`，但 Direct-P4 的 OOD-t 本地正式数值已经可以读取和分析。

---

## 3. 冻结正式 OOD-t manifest 与预检

```bash
export OODT_MANIFEST=$EVAL_ROOT/greenearthnet_oodt_chopped_manifest.json

python scripts/freeze_greenearthnet_chopped_protocol.py \
  --eval-root "$GREEN_EVAL_ROOT" \
  --track ood-t_chopped \
  --output "$OODT_MANIFEST" \
  --hash-mode sha256 \
  --audit-report "$EVAL_ROOT/layout_audit.json"

python scripts/preflight_greenearthnet_oodt_table1.py \
  --dataset-root "$GREEN_EVAL_ROOT" \
  --manifest "$OODT_MANIFEST" \
  --manifest-protocol greenearthnet_cvpr2024_chopped_v1 \
  --split ood-t_chopped \
  --full-cube-root "$GREEN_EVAL_ROOT/iidx" \
  --output "$EVAL_ROOT/preflight_oodt_chopped.json" \
  --strict
```

这两个命令都不会训练、不会把数据复制到本地盘、不会删除数据。`sha256` 冻结会读取全量 target 文件，首次执行耗时是正常的；它换来的是后续表格可审计。

---

## 4. Direct-P4：不重训，只评估

Direct-P4 已完成完整 `val_dev` 选模，正式 checkpoint 路径如下；不需要重新训练：

```bash
export CONFIG=configs/train/stage2_earthnet_v2_direct_physical4.yaml
export DIRECT_CHECKPOINT=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/checkpoints/stage2_physical4_8gpu_b64_200ep_trainvalcache_20260717_165126/checkpoint_best.pt
export CONDITIONING_STATS_PATH=$P/artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048/conditioning_stats_physical4_v1_train_dev.json

export CHECKPOINT=$DIRECT_CHECKPOINT
export METHOD_ID=direct-p4
export METHOD_LABEL=Direct-P4
export METHOD_KIND=paired-direct
export METHOD_PARAMS_MILLIONS=28.17
export METHOD_SEED=42

export RUN_PREFLIGHT=1
export RUN_BASELINES=1
export RUN_MODEL=1
export RUN_ASSEMBLE=1
export MODEL_BATCH_SIZE=16
export MODEL_NUM_WORKERS=8
export SCORE_WORKERS=8
export HASH_MODE=sha256
export CLIMATOLOGY_FULL_CUBE_ROOT=$GREEN_EVAL_ROOT/iidx

bash scripts/run_stage2_table1_greenearthnet_oodt.sh
```

产物默认位于：

```text
$EVAL_ROOT/baselines_oodt_chopped/climatology/{predictions,score}
$EVAL_ROOT/baselines_oodt_chopped/persistence/{predictions,score}
$EVAL_ROOT/direct-p4/oodt_chopped/{predictions,score}
$EVAL_ROOT/table1_oodt_chopped/table1_oodt_chopped.{md,csv,json}
```

`EVAL_ROOT` 应为一个新目录；不要把 Direct 与 Rollout prediction 混写在同一个 method output 目录。

---

## 5. Rollout-P4：训练结束后只替换四个变量

Rollout-P4 必须先完成训练，并在完整 `val_dev` 上选 checkpoint。之后不重做 baseline，复用与 Direct **同一个 frozen OOD-t manifest 和同一个 climatology score**：

```bash
export CONFIG=configs/train/stage2_earthnet_v2_rollout_physical4_h200_200ep.yaml
export CHECKPOINT=/实际/Rollout-P4/checkpoint_best.pt
export METHOD_ID=rollout-p4
export METHOD_LABEL=Rollout-P4
export METHOD_KIND=shared-transition-rollout
export METHOD_PARAMS_MILLIONS=28.17
export METHOD_SEED=42

export RUN_PREFLIGHT=1
export RUN_BASELINES=0
export RUN_MODEL=1
export RUN_ASSEMBLE=1
# 复用 Direct 第一次 run 产生的 baseline 位置：
export BASELINE_ROOT=/Direct评估的EVAL_ROOT/baselines_oodt_chopped
export CLIMATOLOGY_SCORE_DIR=$BASELINE_ROOT/climatology/score
export PERSISTENCE_SCORE_DIR=$BASELINE_ROOT/persistence/score
export CLIMATOLOGY_SCORE=$CLIMATOLOGY_SCORE_DIR/metrics_en21x.json
export CLIMATOLOGY_SCORE_PROVENANCE=$CLIMATOLOGY_SCORE_DIR/score_provenance.json
export PERSISTENCE_SCORE=$PERSISTENCE_SCORE_DIR/metrics_en21x.json
export PERSISTENCE_SCORE_PROVENANCE=$PERSISTENCE_SCORE_DIR/score_provenance.json

# 重要：使用与 Direct 同一个 table root，才能把两行汇总到同一张表。
export TABLE_ROOT=/Direct评估的EVAL_ROOT/table1_oodt_chopped
export EVAL_ROOT=/新的Rollout评估输出目录
export METHOD_ROOT=$EVAL_ROOT/rollout-p4/oodt_chopped

bash scripts/run_stage2_table1_greenearthnet_oodt.sh
```

若 Direct 与 Rollout 使用不同 `OODT_MANIFEST` 文件（即使肉眼看文件列表相同），assembler 会拒绝混表；这是设计目的。

---

## 6. 两个独立 parity 门槛：主表最终闭环

### 6.1 Evaluator parity：同一 prediction 是否被同样评分

本仓库 scorer 的公式来自公开 GreenEarthNet `eval.py`，但正式投稿前仍应在**独立 checkout 的公开仓库**，对**同一 prediction tree 与同一 frozen OOD-t target tree**运行一次官方 evaluator。它验证的是“评分实现一致”，不验证本地 baseline 生成算法本身。

```bash
python eval/verify_greenearthnet_evaluator_parity.py \
  --local-score "$EVAL_ROOT/direct-p4/oodt_chopped/score/metrics_en21x.json" \
  --reference-score /独立官方evaluator/direct_p4_metrics_en21x.json \
  --manifest "$OODT_MANIFEST" \
  --manifest-protocol greenearthnet_cvpr2024_chopped_v1 \
  --split ood-t_chopped \
  --reference-command '记录实际公开eval.py命令（同一 prediction tree）' \
  --output "$EVAL_ROOT/direct-p4/oodt_chopped/official_evaluator_parity.json"
```

对 Direct、Rollout、Persistence、Climatology 分别做一次；每份 report 会绑定其对应 local score 的 SHA-256，不能拿 Direct 的 report 去给其它行背书。

### 6.2 Baseline reference parity：本地 Persistence/Climatology 是否就是公开 baseline

这一步只针对两个 deterministic baseline，验证的是“本地生成的 baseline”与独立公开代码的结果一致。特别是 Climatology 的 daily grid 与 learned 20-step grid 不同，不能只靠 evaluator parity 推断 baseline 算法正确。

先在独立的公开 GreenEarthNet checkout 中，对同一 frozen OOD-t population 跑原始 `model_pixelwise/persistence.py` 或 `model_pixelwise/climatology.py` 加官方 `eval.py`，保存 reference metrics（不写入本仓库的 prediction/score 目录）。然后记录：

```bash
python eval/verify_greenearthnet_baseline_reference.py \
  --baseline persistence \
  --local-score "$BASELINE_ROOT/persistence/score/metrics_en21x.json" \
  --reference-score /独立公开baseline/persistence_metrics_en21x.json \
  --manifest "$OODT_MANIFEST" \
  --manifest-protocol greenearthnet_cvpr2024_chopped_v1 \
  --split ood-t_chopped \
  --reference-command '记录实际公开 persistence.py + eval.py 命令' \
  --output "$BASELINE_ROOT/persistence/baseline_reference_parity.json"

python eval/verify_greenearthnet_baseline_reference.py \
  --baseline climatology \
  --local-score "$BASELINE_ROOT/climatology/score/metrics_en21x.json" \
  --reference-score /独立公开baseline/climatology_metrics_en21x.json \
  --manifest "$OODT_MANIFEST" \
  --manifest-protocol greenearthnet_cvpr2024_chopped_v1 \
  --split ood-t_chopped \
  --reference-command '记录实际公开 climatology.py + eval.py 命令' \
  --output "$BASELINE_ROOT/climatology/baseline_reference_parity.json"
```

最后只重注册已有结果（不推理、不评分、不训练）：

```bash
export CLIMATOLOGY_PARITY_REPORT=$BASELINE_ROOT/climatology/official_evaluator_parity.json
export PERSISTENCE_PARITY_REPORT=$BASELINE_ROOT/persistence/official_evaluator_parity.json
export METHOD_PARITY_REPORT=$EVAL_ROOT/direct-p4/oodt_chopped/official_evaluator_parity.json
export CLIMATOLOGY_BASELINE_REFERENCE_REPORT=$BASELINE_ROOT/climatology/baseline_reference_parity.json
export PERSISTENCE_BASELINE_REFERENCE_REPORT=$BASELINE_ROOT/persistence/baseline_reference_parity.json

export RUN_PREFLIGHT=0
export RUN_BASELINES=0
export RUN_MODEL=0
export RUN_ASSEMBLE=1
export ASSEMBLE_OVERWRITE_ROW=1
bash scripts/run_stage2_table1_greenearthnet_oodt.sh
```

`ASSEMBLE_OVERWRITE_ROW=1` 只覆盖同一 method 的已注册表格行；它不会覆盖 prediction、score 或 checkpoint。只有核心四行都存在、非 Climatology 行都有 Outperformance、所有 evaluator parity=`passed`、且 Persistence/Climatology 的 baseline reference parity=`passed`，bundle 的 `paper_ready` 才会变为 `true`。

若已有旧 prediction/score artifact 没有 `prediction_grid` 字段，当前代码会故意拒绝它进入正式表。请用当前 exporter/score 重新生成该 artifact；这是一次性协议升级，不是数值重训。

---

## 7. 解释几个容易混淆的点

- **Direct-P4 需要重训吗？** 不需要。只需用选定 checkpoint 推理 OOD-t。
- **Rollout-P4 和 Direct-P4 是否放在同一表？** 是。它们是本文最关键的严格配对比较：Direct 是非递推对照，Rollout 是共享五日状态转移。
- **为什么不把现有 raw IID/OOD/ENS 表直接当主表？** raw EarthNet2021x 与 GreenEarthNet chopped 的样本、target、mask、指标协议不同；硬合并会产生无法审计的比较。
- **Climatology 为什么不是 20 步？这会不会是 bug？** 不是本仓库的额外处理。公开 `model_pixelwise/climatology.py` 对 target 用 `slice(50, None)`，而公开 Persistence 用 20 个五日点。现在代码忠实保留并记录这种差异；真正的可比性由相同公开 scorer、独立 baseline reference parity 和 frozen manifest 共同约束。
- **为什么表里写 `RMSE25†` 而不是把它当普通 RMSE25？** 公开 evaluator 的字段实际名是 `rmse_0_5`。对 20 个五日点，它等于前五个点（25 天）；对公开 daily Climatology，它等于前五个每日点。数值仍按公开源码保留，但论文不能据此宣称 Climatology 的该列与模型完全同 horizon。
- **是否会删除本地缓存？** 新 OOD-t runner不包含 staging 或 cleanup 命令；它只读 data、写 `EVAL_ROOT`。任何既有 `/tmp` 本地数据保留策略由训练/缓存 launcher 单独控制。
- **最先能填进 Table 1 的是什么？** Baselines + Direct-P4 OOD-t local score；但在两类 parity 前 bundle 仍是 provisional。Rollout 完成后补齐第四行。
