# 80 · 评测 runbook（S1a 完成即可跑）：GreenEarthNet ood-t 主表 + 官方 ENS 诊断（两套互斥）

> 写于 2026-07-22（侦察子代理产出 + 我复核数据事实）。**用途**：S1a `checkpoint_best.pt` 一出，照此评测。命令来自代码 file:line，但**多处 env 路径需在训练/评测服务器端二次核验**（本机 `/csy-mix02` 未挂载，见 doc 79）——**跑前先 audit，别信 doc 里的老路径字符串**。

> 🔴 **数据根修正（2026-07-22，实跑后确认，来自 Plan B memory）**：GreenEarthNet **chopped 评测 track（含 `ood-t_chopped`）在 `/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet`**，**不在** `earthnet2021x`！`earthnet2021x` 只是**原始** en21x（iid/ood/train，给官方 ENS 诊断用）。所以 §2 的 `GREEN_EVAL_ROOT` 应设为 `/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet`。`iidx`（climatology）尚未下载 → 先 `RUN_BASELINES=0`。

> 🔴 **s2_mask 假警报修复（2026-07-22 实跑验证，方案 A/B 通用）**：GreenEarthNet chopped cubes 用 `s2_dlmask`+`s2_SCL`（不是 `s2_mask`）。**真实 export（`EarthNet2021Dataset` 有 `s2_mask→s2_dlmask` 回退，`earthnet2021.py:606`）+ score（`greenearthnet_protocol.py:131` 用 s2_dlmask）都 OK**；只有 `--strict` preflight（`earthnet_table1.py:138` 无回退）会 `stage2_direct_export_ready:false` 挡住整条流水线。**修复：跑评测时加 `RUN_PREFLIGHT=0`** 跳过这个过严的门即可正常出 R²/RMSE。（彻底修可给 `earthnet_table1.py` 加同款 2 行回退。）

---

## 0. 铁律：两套评分器，永不同表（doc 74:36 红线）

| 指标 | 评分器 | 协议/track |
|---|---|---|
| **NDVI R²/RMSE/NSE/bias/RMSE25/Outperformance** | `eval/score_table1_greenearthnet.py` ← `eval/greenearthnet_protocol.py` | GreenEarthNet CVPR-2024 **`ood-t_chopped`**（**论文主表 Table 1**） |
| **官方 ENS（MAD/OLS/EMD/SSIM）+ NDVI_MAE + RGBN-MAE** | `eval/eval_stage2_earthnet.py --official-score` ← `earthnet_standard_metrics.py` | **原始 en21x** `iid`/`ood`（**独立诊断，非 GreenEarthNet**） |

- **GreenEarthNet ood-t_chopped 没有 ENS**；ENS 只在原始 en21x iid/ood 上有。**两者分两次 run、分两张表、绝不混。**
- `NDVI_MAE` 是训练/val 选择诊断（`forecast_metrics.py:55,64`），不进 ood-t 主表。

---

## 1. 参照锚点（S1a 要打的靶）

已评分的 **Direct-P4 ood-t_chopped**（`evaluations/greenearthnet_oodt_20260719_214234/direct-p4/.../metrics_en21x.json`）：
> **R²=0.5243, RMSE=0.1778, NSE=−0.415, biasabs=0.126, rmse25=0.1255**

- 与记忆基线 0.524 吻合。**S1a（residual+finetune）的成败 = 能否把 R² 从 0.5243 抬向 G2 门（3-seed R²>0.62 & RMSE<0.14）。**
- Rollout-P4 也已评分（更弱）——即叙事崩盘点。**Table 1 只报 Direct 系（S1a），不报 rollout 头条。**

---

## 2. 主表命令：GreenEarthNet ood-t（R²/RMSE）—— 在**训练/评测服务器**、env `WorldModel`

一个 orchestrator 串起 audit→freeze manifest→preflight→baselines→predict→score→assemble：
`scripts/run_stage2_table1_greenearthnet_oodt.sh`。

```bash
export WM=<repo-root>/WorldModel2026
cd "$WM"; conda activate WorldModel
# ↓ 服务器真实数据根：先 audit 确认，别信字符串。侦察给的最后真实路径是：
#   /root/nas/users/luzheng/workspace/ssh/czj/TrainData/EarthNet2021/earthnet2021x
export GREEN_EVAL_ROOT=<datadir>/EarthNet2021/earthnet2021x      # 含 ood-t_chopped/ 和 iidx/
export CONDITIONING_STATS_PATH=$WM/artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048/conditioning_stats_physical4_v1_train_dev.json
export RUN_ID=table1_greenearthnet_oodt_plan_a_s1a_s42_best_<ts>
export EVAL_ROOT=$WM/evaluations/$RUN_ID
export OODT_MANIFEST=$EVAL_ROOT/greenearthnet_oodt_chopped_manifest.json
mkdir -p "$EVAL_ROOT"

# (i) audit + (ii) 冻结 ood-t_chopped manifest（首次 sha256 读全 target，慢）
python scripts/audit_greenearthnet_layout.py --raw-root "$GREEN_EVAL_ROOT" \
  --eval-root "$GREEN_EVAL_ROOT" --sample-schema --output "$EVAL_ROOT/layout_audit.json"
python scripts/freeze_greenearthnet_chopped_protocol.py --eval-root "$GREEN_EVAL_ROOT" \
  --track ood-t_chopped --output "$OODT_MANIFEST" --hash-mode sha256 \
  --audit-report "$EVAL_ROOT/layout_audit.json"

# (iii) evaluation-only：predict+score+assemble（Plan A S1a）
CONFIG=configs/train/plan_a_stage2v3_vits_train.yaml \
CHECKPOINT=$WM/checkpoints/plan_a_s1a/checkpoint_best.pt \
CONDITIONING_STATS_PATH="$CONDITIONING_STATS_PATH" \
GREEN_EVAL_ROOT="$GREEN_EVAL_ROOT" OODT_MANIFEST="$OODT_MANIFEST" EVAL_ROOT="$EVAL_ROOT" \
METHOD_ID=plan-a-s1a METHOD_LABEL=Plan-A-S1a METHOD_KIND=paired-direct \
METHOD_PARAMS_MILLIONS=28.18 METHOD_SEED=42 \
CLIMATOLOGY_FULL_CUBE_ROOT=$GREEN_EVAL_ROOT/iidx \
RUN_PREFLIGHT=1 RUN_BASELINES=1 RUN_MODEL=1 RUN_ASSEMBLE=1 \
MODEL_BATCH_SIZE=16 MODEL_NUM_WORKERS=8 SCORE_WORKERS=8 HASH_MODE=sha256 \
bash scripts/run_stage2_table1_greenearthnet_oodt.sh
```
- 输出：`$EVAL_ROOT/plan-a-s1a/oodt_chopped/score/metrics_en21x.json` + `$EVAL_ROOT/table1_oodt_chopped/table1_oodt_chopped.{md,csv,json}`。
- **若 baselines 已在 Direct-P4 run 里跑过**：`RUN_BASELINES=0` 并把 `BASELINE_ROOT/CLIMATOLOGY_SCORE_DIR/PERSISTENCE_SCORE_DIR` 指向旧 run（doc 68:387-416），省一大截时间。
- 手动等价（绕过 wrapper）：`eval/export_greenearthnet_predictions.py` → `eval/score_table1_greenearthnet.py`（参数见侦察，`--manifest-protocol greenearthnet_cvpr2024_chopped_v1 --split ood-t_chopped`）。

## 3. 诊断命令：官方 ENS（原始 en21x iid/ood，另一次 run）
```bash
python eval/eval_stage2_earthnet.py --config configs/train/plan_a_stage2v3_vits_train.yaml \
  --checkpoint $WM/checkpoints/plan_a_s1a/checkpoint_best.pt \
  --split iid --data-root <datadir>/EarthNet2021 \
  --conditioning-stats-path "$CONDITIONING_STATS_PATH" \
  --manifest-path $WM/artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048/iid.json \
  --official-score --per-cube-output <out>/iid_percube.json \
  --batch-size 8 --num-workers 8 --output <out>/ens_iid.json
# 再跑 --split ood + ood.json
```
- `--per-cube-output` 必给（bootstrap CI / 配对显著性）。`--official-score` 触发 `EarthNetScoreAccumulator`。

---

## 4. 数据现实（**已核实，doc 79 呼应**）
- 本机 `/csy-mix02` 未挂载；`configs/train/stage2_earthnet_v2_data.yaml:9` 仍硬编码失效老根——**服务器端跑前 audit 校准**。
- **GreenEarthNet chopped 只有 `ood-t_chopped` 在位**（1904 文件，8 区 JAS/MAM/MJJ/SON×21/22）；`val_chopped/iid_chopped/ood-s/ood-st_chopped` **全缺** → `official_validation_available=false`。**不能声称"完整官方 GreenEarthNet 协议"，只能报 ood-t track。**
- **`iidx`（climatology baseline 需要）在位性未验证**；20260719 run 无 `baselines_oodt_chopped/`、无 assembled 主表（只 score 了 direct-p4/rollout-p4）→ **climatology/persistence/Outperformance 从未闭合**。这是 Plan A run 的开口：`RUN_BASELINES=1` 需 `iidx`。
- 原始 en21x `iid`(4205)/`ood`(4202)/`extreme`(3972)/`seasonal`(3880)/`train`(23816) 在位；冻结 manifest+stats **本地已有** `artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048/`。

---

## 5. 评测必备输入
- **conditioning stats（physical4）**：`.../conditioning_stats_physical4_v1_train_dev.json`（本地已有；没有单独 dataset_stats.json，这个 train-only 文件就是 stats）。经 `--conditioning-stats-path` 或 `CONDITIONING_STATS_PATH`。
- **冻结 ood-t manifest**：`freeze_greenearthnet_chopped_protocol.py --track ood-t_chopped`（protocol `greenearthnet_cvpr2024_chopped_v1`）。scorer 会 hash-exact 校验预测 NetCDF 树与 manifest 一致（`score_table1_greenearthnet.py:137-231`）。
- **checkpoint 契约校验**：每个评测器都 `verify_checkpoint_contract(...)`（`eval_stage2_earthnet.py:103`）——config 与 checkpoint 存的 Stage2 契约不符会**硬失败**，除非 `--allow-checkpoint-contract-mismatch`。评测强制 `encoder.from_checkpoint=None` + `compute_latent_targets=False`，故评测不需 Stage1.5 路径/未来观测。
- **env**：`.conda/envs/WorldModel/bin/python`；`earthnet==0.3.9` 已装（ENS 需要）。

---

## 6. 陷阱清单（file:line，写作/评测都要记）
- **ENS SSIM ×10.319 缩放**（`earthnet/parallel_score.py:254`）：原始 SSIM~0.75→subscore~0.05；**ENS 只在同协议内可比**，这是模型 ENS 输给静态 persistence 的原因（doc 69:178）。persistence ENS iid **0.209** > 我们 ~**0.15**，四 split 全输 ENS。→ **论文别把 ENS 当主指标**；主表用 GreenEarthNet R²/RMSE。
- **inline-vs-official ENS parity 门**：`eval/parity_inline_vs_official_ens.py` 须 `PARITY OK`（改过 `earthnet_standard_metrics.py` 后重跑）。
- **mask 极性守卫**：`mask_valid_fraction` 应 ~0.6–0.95；跳到 ~0/~1 说明 clear_mask 极性坏了。
- **截断诊断守卫**：`extreme/seasonal` 在 30-token 布局是 10→20 截断，**非**官方 20→40/70→140；评测器自标 `is_truncated_diagnostic`，`assemble_stage2_table1.py:246-252` 拒绝把截断 split 塞进 iid/ood 槽。
- **RMSE25 网格语义**：`rmse25=rmse_0_5`；20 步网格是前 25 天，但公开 Climatology 的日网格 day-50 是前 5 个日点——**非等 horizon 比较**，别静默重采样。
- **paper_ready 双 parity 闭合**：`bundle.paper_ready` 仅当核心行齐 + evaluator parity + baseline-reference parity 全过才 true，否则 `provisional`（doc 68:§6）。

---

## 7. 醒来待办
1. S1a 完成 → 先跑 §2 主表（先确认服务器 `GREEN_EVAL_ROOT` 与 `iidx`）；若 iidx 缺，`RUN_BASELINES=0` 复用旧 Direct-P4 baselines 得 Outperformance。
2. R²/RMSE 出来 → 决定 76 摘要结果句 A/B/C 档 + 更新 doc 78 Table 1。
3. ENS 诊断（§3）可选，**只作诊断表**，不进主表。
