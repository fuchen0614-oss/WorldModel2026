# 74 · 方案A 执行引导（ObsWorld Stage2-v3 · 保留 ViT-S · 分支 `plan-a-vits`）

> 日期：2026-07-22　状态：**执行引导（活文档）**。后续方案A所有工作参考本文件。
> 定位：**不重训 Stage1**（SSL4EO 数 TB 不现实）。保留 Stage1.5 的 ViT-S 编码器当观测编码器 q，**只重写 Stage2**：套 Contextformer 精度配方 + direct/composed 状态契约 + 端到端微调；加一个**小 Stage1.8** 做可验证的产品因子化。
> 隔离：本方案独占分支 **`plan-a-vits`**；方案B在 **`plan-b-pvt`**（见 [[75_方案B执行引导_ObsWorld_Stage2v3_PVT_plan-b-pvt_20260722]]）。**两分支物理隔离，互不 merge，除非同步共享 bugfix。**
> 关联：[[71_ObsWorld_AAAI27_SOTA可达型世界模型最终主线与实验闭环_20260721]]（loss/接口定义）、[[72_ObsWorld叙事母稿与AAAI27正文蓝图_锁定版_20260722]]（叙事）、[[58_ObsWorld_AAAI27中文论文终稿_主实验冻结版_20260717]]（step/epoch 与命令格式）。

---

## 0. TL;DR（一页）

- **编码器 q**：现有 Stage1.5 `MultiModalViTEncoderFiLM`（ViT-S），加载 checkpoint，Stage2 **端到端解冻微调**。
- **精度配方（Stage2 新增，最大涨分点）**：**last-valid-NDVI 残差预测** + 云感知上下文 + 天气 cross-attention（DGH 加厚）+ 强解码器。
- **世界模型契约（Stage2 新增）**：同一个转移 T 的 **direct 路径**（headline 精度、无递推误差）+ **composed 路径**（z0→z_k→z_h，证可组合动力学）+ **latent-future 一致性**（把 z 锚成预测状态）。
- **Stage1.8（小、快）**：SSL4EO S2 **L1C/L2A 成对**子集上短预训练，产出 Table 2 因子化证据；**不含 S1、不跑全量**。
- **强基线可恢复**：新 loss 权重=0、状态头关 → 退化成"ViT-S + Contextformer 配方"纯预测器。
- **训练预算**：Stage1.8 ~几百 step（1-2 GPU-h）；Stage2 主训 **8800 step / 200 epoch**（8×H200）；第二次机会=低 LR 定向修复。

---

## 0.5 叙事对齐与约束（写死，回访必看）

### 本方案在论文里承担什么（对齐叙事母稿 [[76_ObsWorld叙事锁定与AAAI27摘要冻结_20260722]]）
- **锁定叙事**：ObsWorld = **成像条件化的预测状态世界模型**（`y=R(s;φ)⊙M+ε`，`s_{t+1}=F(s_t,w_t)`）。方案A 是这个叙事的一个骨架实现（ViT-S encoder + physical4 + 残差头 + 状态契约），**叙事不因骨架/结果改变**。
- **三柱 → 本方案阶段映射**：
  - 柱1 预测精度（Table 1）← **S1a**（残差头 + 端到端微调，🟢 正在跑）
  - 柱2 观测因子化（Table 2）← **Stage1.8** L1C/L2A cross-render + no-φ 对照
  - 柱3 状态可复用（Table 3）+ 可组合动力学 ← **S1b**（composed + latent-future）+ 冻结状态事件读出
- **result-robust（结果不理想也能证明叙事）**：world-model 主张由**柱2+柱3 的机制实验**承重，**不靠赢 SOTA**；精度只需"有竞争力"。摘要 `【结果句】` 三档（A 赢 / B 平 / C 竞争力），**G2 门未过不得写 SOTA**。
- **精度 ≠ 赢**：即使精度追上 SOTA，没有柱2/柱3 就只是 forecaster、不是世界模型论文。

### 约束与红线（执行时不许越）
- **Gate 链**：G0-recover(λ=0 退化成能用预测器、≥现有 0.524) ✅ → G1(状态接口不破坏预测) → **G2 SOTA 门**(3 seed R²>0.62 且 RMSE<0.14 才写 SOTA) → G3(world-model 门：cross-render>no-φ、latent-future 收敛、冻结读出优于 raw-history)。
- **🔴 硬线：z 必须承重**——最终预测从 z 解码；精度技巧一律走 z，**不许加"绕过状态直接预测"的捷径**（否则世界模型叙事塌）。"为精度不择手段"止于此线。
- **禁用词**：SOTA（除非同协议真领先且 G2 过）/ 因果 / digital twin / 实时 φ / "已实现 φ 解耦"（用修正版 probe）/ first weather-driven world model。旧 67–71% φ 泄漏数字作废。
- **协议纪律**：EarthNet2021 ENS 与 GreenEarthNet R²/RMSE **永不混表**；val_dev 数字不进 OOD-t 主表；Extreme/Seasonal 是 10→20 截断诊断、**非官方轨道**（勘误见 [[69_ObsWorld_官方EarthNetScore对标_published_vs_ours_20260722]]）。
- **驱动**：**physical4**（用户拍板）；full24 缺 `fg`。DGH 承重（外生 forcing 驱动 F），但 4-vs-21 是次要旋钮。
- **诚实计分板**：赢写赢、输写 competitive；两协议下当前战胜强 SOTA = 0（诚实起点，靠 S1a 抬精度改变，不夸大）。
- **数据**：Stage2 训练 = earthnet2021x（现成）；测试 = GreenEarthNet ood-t 官方 evaluator；**Stage1 不重训**（SSL4EO 数 TB）；Stage1.8 只取小 L1C/L2A 子集。
- **算力/分支**：训练端 8×H200 全卡；本地 8 卡仅 smoke（方案A 用 0-3、方案B 用 4-7）；分支 `plan-a-vits` 与 `plan-b-pvt` 物理隔离、不互 merge（共享 bugfix 用 cherry-pick）。

---

## 1. 架构

```
image ──q(=Stage1.5 ViT-S, 端到端微调)──► tokens ──state projector──► z0
z0 ──T(D,G,Δt)──► z_h            [direct: 每个 h 从 z0 直达]
z0 ─►z_k─►z_h                    [composed: 分段推进，证动力学]
z_h ──O(+last-valid-NDVI 残差)──► NDVI_h / RGBN_h
z_h^obs = q(X_{t+h})            [真实未来编码，锚定 z]
```

**共享组件（与方案B完全相同，但两分支各自持有一份代码，不交叉引用）**：state projector、`ControlledTransition`（direct+composed）、观测解码器 O（残差头）、DGH 条件、全部新 loss。**唯一与B不同的是 q 的实现（A=ViT-S，B=PVT）。**

**Loss（参照 71 号 §4.4）**：
```
L = L_GEN                                   # 官方 GreenEarthNet 预测损失(残差口径)
  + λ_dyn   · L_latent_future               # dist(T(z_t,D), stopgrad(q(X_{t+h})))
  + λ_pair  · L_paired_state                # dist(q(X_L1C), q(X_L2A))   [来自Stage1.8]
  + λ_cross · L_cross_render                # O(q(X_a),φ_b)->X_b, a,b∈{L1C,L2A}
  + λ_path  · L_path_consistency            # dist(z_h^direct, z_h^composed)
  + λ_reg   · L_state_reg                   # variance-covariance 防坍塌
```
初值建议：λ_dyn=0.5, λ_pair=0.5, λ_cross=0.5, λ_path=0.3, λ_reg=0.1（**第一次主训后按 Gate 调**；红队工作流回来会给精调值，接口不变）。

---

## 2. 分支与代码隔离（两分支最保险）

```bash
cd $WM                 # 训练端 WorldModel2026 根（你提供）
git fetch origin
git checkout -b plan-a-vits origin/main     # 方案A独占分支
# 之后所有A的改动都在此分支；绝不 merge plan-b-pvt
```
- 新代码放**方案专属模块/config**，不改会被B用到的共享文件的语义；若必须改共享文件（如 loss），**在 A 分支改，B 分支独立改**，靠 cherry-pick 同步而非 merge。
- 输出目录、config、checkpoint、log **全部带 `plan_a` 前缀**，与B物理分开。

---

## 3. 数据与子集（一切从最优可能性出发）

| 用途 | 数据 | 取舍 |
|---|---|---|
| Stage2 预测主训 | EarthNet2021x / GreenEarthNet train（≈22.8k train_dev） | 用全量 train_dev（已冻结 manifest），沿用现有协议 |
| Stage1.8 因子化 | **SSL4EO S2 L1C/L2A 成对子集** | **小子集**（建议 4k–8k 样本，跨 4 季覆盖）；**S2-only，不加 S1**；**不跑全量几 TB** |
| Table3 事件读出 | GreenEarthNet 派生的未来 NDVI 衰退事件 | train/val 冻结事件定义，不看 test |

**季节/S1 决策（你问的）**：
- **S1 不加**——本文因子化用 L1C/L2A（产品），S1 的价值（抗云）需 SAR 下游，EarthNet 没有 → **S1 推迟到后续 venue（73 号）**。加 S1 只会拉长时间、无当前收益。
- **季节**：Stage1.8 子集**跨 4 季各取一部分**保证覆盖即可，**不需全量**；Stage2 用现有 train_dev（本身多季）。

---

## 4. 三阶段流程 + 具体 epoch/step

### 4.1 step/epoch 换算（引用 58 号 §4.3）
```
global_batch   = GPUS × BATCH_SIZE
updates/epoch  = floor(N_train / global_batch)     # drop_last
MAX_STEPS      = epochs × updates/epoch
```
**Stage2 实例**：N_train=22847, GPUS=8, BATCH_SIZE=64 → global=512 → **44 updates/epoch** → 200 epoch = **8800 steps**（与现有 Direct-P4 一致，已验证）。
> ⚠️ N_train 取决于你服务器上的 manifest，**开训前用 preflight 打印的 `EarthNet samples: N` 核对**，据此反推 MAX_STEPS。

### 4.2 Stage1.8 · 观测因子化（小、快）
- init：Stage1.5 encoder checkpoint（你提供 `$STAGE15_CKPT`）。
- 数据：SSL4EO L1C/L2A 成对子集（$DATA_SSL）。
- 预算：**子集 N≈4000, global=8×32=256 → 15 updates/epoch → 30 epoch ≈ 450 steps（~1-2 GPU-h）**。目标只是产出因子化（Table2）+ q/O_product，不追大规模。
- 产物：`plan_a_stage1_8/checkpoint_best.pt`（含 q + O_product + φ(L1C/L2A) token）。

### 4.3 Stage2 · forecasting 主训（主战场）
- init：Stage1.8 encoder（或直接 Stage1.5，若 Stage1.8 未完成可先跑）。
- **端到端微调**（`freeze: false`），套残差头 + 天气 cross-attn + 状态契约。
- 预算：**8×H200, BATCH_SIZE=64, MAX_STEPS=8800（200 epoch）**；BF16；checkpoint 里程碑 epoch 100/150/200。
- checkpoint 选择：**只看内部 val_dev**，候选 {best, ep100, ep150, ep200}，主指标 R²（或 NDVI-RMSE）最优。

### 4.4 Stage-C · 冻结状态读出（小）
- 冻结 q/T，只训 2 层 MLP 事件头；小预算（~几十 epoch 小数据）。

### 4.5 第二次 H200 机会 = 定向修复（不重来）
- 从 Stage2 最优 checkpoint **低 LR 微调**：若精度接近但机制 loss 拖累 → 降 λ_dyn/path、加强 L_GEN；若精度强但 composed 不稳 → 提 λ_path。**依据 val_dev，不看 test。**

---

## 5. 完整命令（占位路径，你填 `$…`）

### 5.0 你需要提供的路径（清单，见 §7）
```bash
export WM=/训练端/WorldModel2026                 # 仓库根
export DATA_EN=/训练端/EarthNet2021              # 含 earthnet2021x
export DATA_SSL=/训练端/SSL4EO-S12               # L1C/L2A 成对
export STAGE15_CKPT=/训练端/stage1_5_.../checkpoint_step_60000.pt
export STATS=$WM/artifacts/protocols/earthnet2021x_physical4_v1_.../conditioning_stats_physical4_v1_train_dev.json
export TRAIN_MANIFEST=$WM/artifacts/protocols/.../train_dev.json
export VAL_MANIFEST=$WM/artifacts/protocols/.../val_dev.json
```

### 5.1 环境 + 分支
```bash
cd $WM
source scripts/activate_worldmodel.sh            # 或 .conda/envs/WorldModel/bin/python
git checkout plan-a-vits
python -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.cuda.device_count())"
```

### 5.2 Stage1.8 因子化（短）
```bash
# 配置：configs/train/plan_a_stage1_8_factorize.yaml （本方案新增，见 §9 骨架）
GPUS=8 BATCH_SIZE=32 MAX_STEPS=450 NUM_WORKERS=8 \
CONFIG=configs/train/plan_a_stage1_8_factorize.yaml \
DATA_ROOT=$DATA_SSL INIT_CHECKPOINT=$STAGE15_CKPT \
CHECKPOINT_DIR=$WM/checkpoints/plan_a_stage1_8 LOG_DIR=$WM/logs/plan_a_stage1_8 \
RUN_TRAIN=1 \
bash scripts/train_stage1_8_factorize.sh 2>&1 | tee $WM/logs/plan_a_stage1_8/train.log
# 完成后跑因子化评测(Table2): eval/eval_factorization.py --checkpoint ... --pairs ...
```

### 5.3 Stage2 forecasting 主训（参照现有 run_stage2_earthnet.sh 格式）
```bash
# 先 preflight 核对 N_train 与协议
CONFIG=configs/train/plan_a_stage2v3_vits.yaml DATA_ROOT=$DATA_EN \
CONDITIONING_STATS_PATH=$STATS MANIFEST_PATH=$TRAIN_MANIFEST VALIDATION_MANIFEST_PATH=$VAL_MANIFEST \
STAGE15_CHECKPOINT=$WM/checkpoints/plan_a_stage1_8/checkpoint_best.pt \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=0 \
bash run_stage2_earthnet.sh          # 看 "EarthNet samples: N" 核对 → 反推 MAX_STEPS

# 正式训练（N=22847→MAX_STEPS=8800；若N不同按 §4.1 反推）
CONFIG=configs/train/plan_a_stage2v3_vits.yaml DATA_ROOT=$DATA_EN \
CONDITIONING_STATS_PATH=$STATS MANIFEST_PATH=$TRAIN_MANIFEST VALIDATION_MANIFEST_PATH=$VAL_MANIFEST \
STAGE15_CHECKPOINT=$WM/checkpoints/plan_a_stage1_8/checkpoint_best.pt \
CHECKPOINT_DIR=$WM/checkpoints/plan_a_stage2v3 LOG_DIR=$WM/logs/plan_a_stage2v3 \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_MAX_FILES=16 PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=1 \
GPUS=8 BATCH_SIZE=64 NUM_WORKERS=8 MAX_STEPS=8800 \
bash run_stage2_earthnet.sh 2>&1 | tee $WM/logs/plan_a_stage2v3/train.log
```

### 5.4 评测（官方 GreenEarthNet 协议 + 内部 val_dev 选模）
```bash
# val_dev 选 checkpoint（不看 test）
python eval/eval_stage2_earthnet.py --config configs/train/plan_a_stage2v3_vits.yaml \
  --checkpoint $WM/checkpoints/plan_a_stage2v3/checkpoint_best.pt --split val \
  --data-root $DATA_EN --conditioning-stats-path $STATS --manifest-path $VAL_MANIFEST \
  --batch-size 8 --num-workers 8 --output $WM/evaluations/plan_a_val.json
# 冻结后再上官方 OOD-t（GreenEarthNet），沿用 68 号的 export→score→parity 流程
```

---

## 6. checkpoint 选择 / Gates / 止损

- **G0 强基线可恢复**：λ_*=0 + 状态头关 → 复现"ViT-S+配方"纯预测器，先确认它 ≥ 现有 0.524（否则配方接错）。
- **G1 接口不破坏预测**：加状态接口(不加动力学 loss)后 val R² 不显著下降。
- **G2 SOTA 门**：同协议 3 seed 均值 R²>0.62 且 RMSE<0.14 才写 SOTA；否则写 competitive。
- **G3 世界模型门**：L1C/L2A cross-render 显著优于 no-φ；latent-future 随训练下降；冻结状态事件读出优于 raw-history。
- **止损**：若 Stage2 主训 val 仍≈0.52 且无机制收益 → 该分支存疑，转看方案B结果。

---

## 7. 需要你提供的路径（在另一窗口回填上面 `$…`）
1. `$WM`（训练端 WorldModel2026 根）
2. `$DATA_EN`（EarthNet2021x/GreenEarthNet 根）+ manifest/stats 实际路径
3. `$DATA_SSL`（SSL4EO-S12 根，含 L1C/L2A）
4. `$STAGE15_CKPT`（Stage1.5 checkpoint；若训练端没有，从权重 release `stage1.5` tag 拉）
5. GreenEarthNet OOD-t 评测目录（最终主表用）

---

## 8. 并行协作提示
- 本分支 `plan-a-vits` 与方案B `plan-b-pvt` **只共享设计、不共享代码**；共享 bugfix 用 `git cherry-pick <sha>` 双向同步，**不 merge**。
- 两节点各跑一个分支；哪个 Gate 通过用哪个。
- 每完成一步在本 MD 末尾追加"执行记录"（step 数、val 指标、checkpoint SHA、耗时），保证可续。

## 9. 参考的现有代码格式（避免出错）
- 训练启动：`run_stage2_earthnet.sh`（env-var 驱动，见 58 号 §5 / STAGE2_EARTHNET_RUNBOOK）。
- 训练主流程：`train/train_stage2_earthnet.py`（freeze/unfreeze 在 472-514；config `encoder.freeze/unfreeze_*`）。
- 模型工厂：`models/dynamics/obsworld_factory.py`（按 config 选变体、加载 Stage1.5 三模块）。
- 评测：`eval/eval_stage2_earthnet.py`（`--official-score` 走官方 ENS；GreenEarthNet 走 68 号流程）。
- 新增文件（本方案）：`configs/train/plan_a_stage2v3_vits.yaml`、`configs/train/plan_a_stage1_8_factorize.yaml`、`models/dynamics/obsworld_stage2v3.py`（残差头+direct/composed+锚定）、`models/losses/obsworld_v3.py`（上面 6 项 loss）、`scripts/train_stage1_8_factorize.sh`。**这些都在 A 分支，不进 B。**

---

## 执行记录（持续追加）
- [x] 2026-07-22 分支 `plan-a-vits` 已建（本地）
- [x] 2026-07-22 代码审计完成（decoder/core/direct/rollout/partition/loss/staged-train 接口全摸清）
- [x] 2026-07-22 **设计修正（审计发现的坑）**：主模型用 **`ObsWorldDirectPathModel`（direct，无递推误差，强）**，不用 partition/rollout 的递归主路径（弱）；composed 一致性分支后续嫁接到 direct 上。
- [x] 2026-07-22 **S1a 残差头实现（向后兼容，未破坏现有模型）**：
  - `models/decoders/earthnet_observation_decoder.py`：加 `residual` 开关 + `forward(baseline=)`，残差 = `clamp(baseline + tanh(y),0,1)`，分辨率自适应插值。
  - `models/dynamics/obsworld_core.py`：`initialize_state` 产出 `last_valid_rgbn`（新 helper `last_valid_pixels`，逐像素最近无云帧、无有效则用时间均值）；`decode_states(baseline=)` 穿线（None 时走原路径）。
  - `models/dynamics/obsworld_direct_path.py`：decode 传入 baseline（decoder 非残差时自动忽略）。
  - `configs/train/plan_a_stage2v3_vits.yaml`：继承 direct24(full24) + `decoder.residual:true` + `encoder.freeze:false` + smoke 用 `require_stage15_checkpoint:false`。
- [x] S1a smoke（GPU0，earthnet2021x 小子集）**通过**：`total=28.18M, trainable=27.77M`（编码器全解冻端到端）、loss 有限下降、`obs≈0.022`（残差头锚定 last-valid 生效）、checkpoint 保存、无 traceback。
- [x] 驱动维度决策：**physical4（4）**（用户拍板）。文献：Contextformer/GreenEarthNet 用 8 个 E-OBS 变量 `[fg,hu,qq,rr,pp,tg,tn,tx]`；本数据缺 `fg`（风速，天气 sidecar 未抽取，非卫星数据缺）。full24-minus-fg(21) 曾评估，但用户选 physical4（物理优雅、精度差距小、DGH 叙事干净）。DGH 主线地位=**承重**（外生 forcing 驱动转移 T），但 4-vs-21 是次要旋钮。
- [x] H200 preflight **全绿**：`checkpoint_kind:stage1.5, compatible:true`（Stage1.5 加载）、`total_files_in_split:22847`→MAX_STEPS=8800、`trainable=27.76M`、`ok:true`。
- [x] **S1a 正式训练启动**（2026-07-22 03:08，8×H200，physical4，残差+微调）：复用 `..._trainval` staged 副本（跳过 rsync）、`loaded Stage1.5`、健康收敛（step150 loss0.109 → step596 loss0.062、obs0.003、ndvi0.117）、~2.2s/it、ETA~2-5h。
- [ ] **epoch100（step≈4400）早看**：val RGBN-MAE vs 旧 Direct-P4 `0.0331`、NDVI-MAE vs `0.1087` → 判断残差+微调是否抬起精度（决定是否加 S1b）。**里程碑记得上传 checkpoint。**
- [ ] Gate G0-recover ✅ / G1 / G2 / G3：待训练+评测

---

## 踩坑与修复（S1a，2026-07-22，回访排查用）

| 现象 | 根因 | 修复 |
|---|---|---|
| `EnvironmentLocationNotFound: .../.conda/envs/WorldModel`（本地 zsh + H200 都报） | `source scripts/activate_worldmodel.sh` 是 bash 脚本，zsh 下 `BASH_SOURCE` 解析错；且 H200 的 env 不在 repo-local `.conda`，在系统 conda | **本地**：直接用 `.conda/envs/WorldModel/bin/python`；**H200**：`conda activate WorldModel`（按名字，不用那个脚本） |
| `missing configured D features: ['mean_fg','min_fg','max_fg']`（line 1424） | full24 需 8 个 E-OBS 变量含 `fg`，本数据无 `fg` | 用 **physical4**（4 变量全有）；若坚持 full24 → config 加 `training.require_all_driver_features:false` |
| `driver valid-rate falls below min_driver_valid_fraction=0.900`（line 1436） | 第二道驱动完整性检查 | config 加 `training.min_driver_valid_fraction:0.0`（physical4 不需要，仅 full24-minus-fg 时） |
| `Manifest role='train' does not match requested split='val'` | smoke 的 val manifest 从 train_dev.json 建（role=train） | val smoke manifest 必须从 `val_dev.json` 建（role=val） |
| staging `ERROR: local disk has only 233G free; need at least 250G` | `MIN_LOCAL_FREE_GB` 默认 250 太保守（数据仅 ~75GB） | 加 `MIN_LOCAL_FREE_GB=100` |
| staging 重复拷贝、不复用已有副本 | 未设 `LOCAL_STAGE_ROOT`，默认路径 `..._earthnet2021x`≠已有副本 `..._trainval` | 加 `LOCAL_STAGE_ROOT=/tmp/${USER}_obsworld_stage2_earthnet2021x_trainval` + `LOCAL_STAGE_CLEANUP=manual`（复用+保留） |
| tail 启动器 log 看不到 step | 训练在独立进程组、写**另一个** log | tail `logs/plan_a_s1a/train_200epoch.log`（不是启动器 tee 的 `plan_a_s1a_train.log`） |

## 关键路径 / 命令速查（S1a）
- 代码改动：`models/decoders/earthnet_observation_decoder.py`(residual)、`models/dynamics/obsworld_core.py`(last_valid_pixels + decode_states baseline)、`models/dynamics/obsworld_direct_path.py`(穿 baseline)。
- config：`configs/train/plan_a_stage2v3_vits.yaml`(smoke, require:false)、`plan_a_stage2v3_vits_train.yaml`(正式, require:true)。
- 本地 smoke stats/manifest：`artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048/conditioning_stats_physical4_v1_train_dev.json` + `evaluations/_smoke/plan_a_{train,val}_dev_p4_smoke8.json`。
- H200 训练日志：`logs/plan_a_s1a/train_200epoch.log`（step/loss）；启动器日志：`logs/plan_a_s1a_train.log`（staging）。
- checkpoint：`checkpoints/plan_a_s1a/`（best + epoch100/150/200）。
- staged 副本（可复用）：`/tmp/${USER}_obsworld_stage2_earthnet2021x_trainval`（75G，sha256=84e9cfa…）。
- 找 val：`grep -iE "valid|RGBN|NDVI_MAE|skill|best" logs/plan_a_s1a/train_200epoch.log`（打印 RGBN-MAE/NDVI-MAE，非 R²；R²/RMSE 需训后另跑 GreenEarthNet ood-t 评测）。
- 正式训练命令：见本窗口对话（conda activate WorldModel + MIN_LOCAL_FREE_GB=100 + LOCAL_STAGE_ROOT=…trainval + LOCAL_STAGE_CLEANUP=manual + CONFIG=plan_a_stage2v3_vits_train.yaml + GPUS=8 MAX_STEPS=8800）。

---

## 睡眠期并行进展（2026-07-22，S1a 训练中并行准备，全部不依赖 S1a 结果）

> 原则：不急、多审查、可以慢、不能错。全程未动正在跑的 S1a、未碰 plan-b-pvt、未改锁死的 76 摘要。

**A. S1b（世界模型证据）——重大发现：机器已存在，S1b 是配置非新代码。** 详见 **doc 77**。
- 既有 `ObsWorldPartitionModel` + `PartitionConsistencyLoss` + 训练循环激活 + `stage2_curriculum.partition_loss_scale` + 工厂 `V2_PARTITION_MODES` 全已接线。`obsworld_partition_physical4` 是受支持模式。
- 已写 **inert** config：`configs/train/plan_a_s1b_partition_physical4.yaml`（继承 Plan A recipe，切 partition，`decoder.residual:false`）。**未启动**，门禁 = S1a epoch100 val 抬精度才上。
- 澄清：v2 正式路径**不**用 `compute_latent_targets`（那是遗留模型）；S1b 潜态证据 = composed-consistency（`z_direct≈z_composed`）。
- 诚实边界：partition 继承递归 rollout，头条精度弱，**不进 Table 1**；Table 1 永远 S1a Direct。

**B. Table 2（L1C/L2A 因子化）——已核实：数据+代码双缺，威胁 76 摘要核心支柱，待你决策。** 详见 **doc 79**。
- `/csy-mix02` 未挂载；本机只有 EarthNet2021；全盘无 SSL4EO/L1C/L2A；因子化代码全不存在；doc 45 曾主动推迟 L1C/L2A。
- 三选项：A=用可得的采集条件 φ 做可运行版因子化（**推荐**，需授权软化摘要一句"L1C/L2A"→"observation/acquisition conditions"）；B=真做 L1C/L2A（大概率赶不上，放期刊版）；C=降级为 future work。

**C. 评测 runbook——S1a 一完成即可跑。** 详见 **doc 80**。
- 两套互斥评分器：GreenEarthNet **ood-t R²/RMSE**（主表 Table 1）vs 官方 **ENS**（原始 en21x iid/ood 诊断）——**永不同表**。
- **参照锚点（S1a 要打的靶）**：Direct-P4 ood-t **R²=0.5243 / RMSE=0.1778**；G2 门 3-seed R²>0.62 & RMSE<0.14。
- 数据现实：chopped 只有 ood-t 在位（1904/8 区），其余 chopped track 缺 → 只报 ood-t，不称完整官方协议；iidx/baselines 未闭合（`RUN_BASELINES=1` 需 iidx，或复用旧 Direct-P4 baselines）。
- ENS 陷阱：SSIM×10.319，模型 ENS 输给 persistence → ENS 只作诊断。

**D. 论文草稿（Intro/Related/Method/Setup）已起。** 详见 **doc 78**（英文正文可直接粘 LaTeX，方法细节全取自已核实代码；Results 占位受结果句门禁）。

**醒来一次性决策清单**（合并 doc 77 §8 + doc 79 §3）：
1. S1b 走选项 A（partition 就绪）还是 B（Direct 加 compose 辅助，需签字，最强"合一"故事）？A 先行 B 后补？
2. S1b 全新冷启还是 resume-from-S1a-best？S1a/S1b 是否平分 H200 并行？
3. Table 2 走 A/B/C？（A 需授权改摘要一句。）
