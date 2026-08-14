# 75 · 方案B 执行引导（ObsWorld Stage2-v3 · Contextformer/PVT 底座 · 分支 `plan-b-pvt`）

> 日期：2026-07-22　状态：**执行引导（活文档）**。后续方案B所有工作参考本文件。
> 定位：**以官方 Contextformer(PVT-v2-B0, ImageNet 预训练, 下载即用) 为精度底座**（**不需重训 SSL4EO**），复现到 evaluator parity 后，在其上加 ObsWorld 的 direct/composed 状态契约与观测因子化。精度成功率最高，代价是集成成本 + "Contextformer+X"的新颖性风险（靠状态承重 + 机制实验为正化解）。
> 隔离：本方案独占分支 **`plan-b-pvt`**；方案A在 **`plan-a-vits`**（见 [[74_方案A执行引导_ObsWorld_Stage2v3_ViTS_plan-a-vits_20260722]]）。**两分支物理隔离，互不 merge。**
> 关联：[[71_ObsWorld_AAAI27_SOTA可达型世界模型最终主线与实验闭环_20260721]]（本方案的完整设计母本，§4/§7/§8/§12 直接照做）、[[72_ObsWorld叙事母稿与AAAI27正文蓝图_锁定版_20260722]]、[[58_..._主实验冻结版]]（step/epoch 与命令格式）。

---

## 0. TL;DR（一页）

- **编码器 q**：官方 Contextformer 的 **PVT-v2-B0（ImageNet 预训练，下载）**，包成统一 `q: image→z` 接口。
- **先复现 Contextformer**（Gate 0）：官方权重跑本地 evaluator parity；本地 matched fine-tune ≥ **R² 0.60**，作为不可跌破的精度底座。
- **强基线可恢复**：新 loss 权重=0、状态头关 → **精确退化成复现的 Contextformer**（保精度、可归因、有回退）。
- **世界模型契约（在 Contextformer 特征上加）**：把其时空特征显式定义为 z；加 state projector + direct/composed 转移 T + latent-future 一致性 + 观测 renderer O(z,φ)；保留原 NDVI residual head。
- **Stage1.8（小、快）**：SSL4EO S2 **L1C/L2A 成对**子集，在 **PVT 特征**上做因子化，产出 Table 2；**不含 S1、不跑全量**。
- **训练预算**：复现/matched baseline + Stage1.8 ~小；主训 **8800 step / 200 epoch**（8×H200）；第二次=定向修复。

---

## 1. 架构

```
image ──q(=PVT-v2-B0, ImageNet init, 端到端)──► 时空特征 ≜ z0
z0 ──T(D,G,Δt)──► z_h            [direct]
z0 ─►z_k─►z_h                    [composed]
z_h ──O_ndvi(+last-valid residual, 保留 Contextformer head)──► NDVI_h
z_h ──O_product(z,φ=L1C/L2A)──► 产品重建   [来自Stage1.8, 验因子化]
z_h^obs = q(X_{t+h})            [真实未来编码, 锚定 z]
```

**共享组件（与方案A逻辑相同，但B分支各自持有一份代码）**：state projector、`ControlledTransition`(direct+composed)、latent-future/factorization/path 全部 loss、DGH 条件。**唯一与A不同的是 q=PVT + 需集成官方 Contextformer 预测头/云掩码/天气编码。**

**Loss（71 号 §4.4，与A同）**：`L = L_GEN + λ_dyn·L_latent_future + λ_pair·L_paired_state + λ_cross·L_cross_render + λ_path·L_path_consistency + λ_reg·L_state_reg`。**强基线可恢复要求：所有 λ=0 且状态头旁路时，前向 ≡ 复现的 Contextformer。**

---

## 2. 分支与代码隔离
```bash
cd $WM
git fetch origin
git checkout -b plan-b-pvt origin/main       # 方案B独占分支
# 官方 Contextformer 代码放 third_party/greenearthnet（子模块或 vendored），只在 B 分支
```
输出/config/checkpoint/log 全带 `plan_b` 前缀。**与 A 分支互不 merge，共享 bugfix 用 cherry-pick。**

---

## 3. 数据与子集

| 用途 | 数据 | 取舍 |
|---|---|---|
| Stage2 预测主训 | **GreenEarthNet 官方 train**（≈23.8k） | 用官方 split/mask/target/evaluator（这是 SOTA 主表协议） |
| Contextformer 复现 | 官方权重 + 官方 evaluator | Gate 0 parity |
| Stage1.8 因子化 | SSL4EO S2 **L1C/L2A 成对**子集 | 小子集(4k–8k)、跨4季、**S2-only、无 S1、不跑全量** |
| Table3 事件读出 | GreenEarthNet 派生 NDVI 衰退事件 | train/val 冻结定义 |

**季节/S1（你问的）**：同方案A——**S1 不加**（推迟到 73 号后续 venue）；Stage1.8 跨 4 季小子集即可，不需全量几 TB。**PVT 是 ImageNet 预训练，本身不碰 SSL4EO 全量。**

---

## 4. 三阶段 + 具体 epoch/step

### 4.1 step/epoch 换算（同 58 号 §4.3）
`global=GPUS×BATCH_SIZE; updates/epoch=floor(N_train/global); MAX_STEPS=epochs×updates/epoch`
**GreenEarthNet 实例**：N_train≈23816, GPUS=8, BATCH_SIZE=64 → global=512 → **≈46 updates/epoch** → 200 epoch ≈ **9200 steps**（**以 preflight 打印的实际 N 为准反推**）。

### 4.2 Gate 0 · 复现 Contextformer（先做，不加任何新东西）
- 拉官方代码+权重 → 本地 evaluator parity（数值与公开量级一致）。
- 跑一个 matched fine-tune baseline（相同额外训练预算），确认额外训练本身不制造不公平增益，且 ≥ **R² 0.60**。
- **G0 不过就先修协议/复现，不加状态契约。**

### 4.3 Stage1.8 · 因子化（PVT 特征上，小）
- init：ImageNet-PVT（或 Gate0 复现后的编码器）。
- 数据：SSL4EO L1C/L2A 成对子集。
- 预算：**N≈4000, global=8×32=256 → 15/epoch → 30 epoch ≈ 450 steps（~1-2 GPU-h）**。产出 q + O_product + φ(L1C/L2A)。

### 4.4 Stage2 · forecasting 主训（复现底座 + 状态契约）
- init：Gate0 的 PVT 编码器 + Stage1.8 的 q/O_product。
- **端到端**；保留 Contextformer residual head；加 state projector + direct/composed + latent-future。
- 预算：**8×H200, BATCH_SIZE=64, MAX_STEPS≈9200（200 epoch，按实际 N 反推）**，BF16，里程碑 epoch 100/150/200。
- 消融行（Table1）：B0 复现 Contextformer / B1 +state接口 / B2 +latent-future / B3 +SSL4EO pair / B4 完整。**各行同 init/data/预算。**

### 4.5 Stage-C 冻结读出 + 第二次机会（同方案A §4.4/4.5）

---

## 5. 完整命令（占位路径，你填 `$…`）

### 5.0 你需要提供 / 本方案额外
```bash
export WM=/训练端/WorldModel2026
export DATA_GEN=/训练端/GreenEarthNet                 # 官方 train + ood-t_chopped + iidx
export DATA_SSL=/训练端/SSL4EO-S12
# 方案B额外：
export CTX_REPO=$WM/third_party/greenearthnet          # 官方 Contextformer 代码
export CTX_WEIGHTS=/训练端/contextformer_model_weights # zenodo 10793870 解压
```

### 5.1 环境 + 分支 + 官方 Contextformer
```bash
cd $WM && source scripts/activate_worldmodel.sh
git checkout plan-b-pvt
# 拉官方代码与权重
git clone https://github.com/vitusbenson/greenearthnet $CTX_REPO   # 或 submodule
# 权重：https://zenodo.org/records/10793870/files/model_weights.zip → 解压到 $CTX_WEIGHTS
```

### 5.2 Gate 0 · evaluator parity + matched baseline
```bash
# 官方权重跑官方 evaluator，确认 parity（脚本参照 CTX_REPO 的 eval 入口）
python eval/eval_greenearthnet_official.py --weights $CTX_WEIGHTS --data $DATA_GEN --split ood-t_chopped \
  --output $WM/evaluations/plan_b_ctx_parity.json
# matched fine-tune baseline（本地复现，≥0.60 才继续）
GPUS=8 BATCH_SIZE=64 MAX_STEPS=9200 CONFIG=configs/train/plan_b_contextformer_repro.yaml \
DATA_ROOT=$DATA_GEN CHECKPOINT_DIR=$WM/checkpoints/plan_b_ctx_repro LOG_DIR=$WM/logs/plan_b_ctx_repro \
RUN_TRAIN=1 bash run_stage2_earthnet.sh 2>&1 | tee $WM/logs/plan_b_ctx_repro/train.log
```

### 5.3 Stage1.8 因子化（PVT）
```bash
GPUS=8 BATCH_SIZE=32 MAX_STEPS=450 CONFIG=configs/train/plan_b_stage1_8_factorize_pvt.yaml \
DATA_ROOT=$DATA_SSL INIT_ENCODER=imagenet_pvt_v2_b0 \
CHECKPOINT_DIR=$WM/checkpoints/plan_b_stage1_8 LOG_DIR=$WM/logs/plan_b_stage1_8 \
RUN_TRAIN=1 bash scripts/train_stage1_8_factorize.sh 2>&1 | tee $WM/logs/plan_b_stage1_8/train.log
```

### 5.4 Stage2 主训（复现底座 + 状态契约）
```bash
# preflight 核对 N_train → 反推 MAX_STEPS
CONFIG=configs/train/plan_b_stage2v3_pvt.yaml DATA_ROOT=$DATA_GEN \
CTX_WEIGHTS=$CTX_WEIGHTS INIT_FACTORIZE=$WM/checkpoints/plan_b_stage1_8/checkpoint_best.pt \
CHECKPOINT_DIR=$WM/checkpoints/plan_b_stage2v3 LOG_DIR=$WM/logs/plan_b_stage2v3 \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=0 \
bash run_stage2_earthnet.sh          # 看 N → 反推 MAX_STEPS

CONFIG=configs/train/plan_b_stage2v3_pvt.yaml DATA_ROOT=$DATA_GEN \
CTX_WEIGHTS=$CTX_WEIGHTS INIT_FACTORIZE=$WM/checkpoints/plan_b_stage1_8/checkpoint_best.pt \
CHECKPOINT_DIR=$WM/checkpoints/plan_b_stage2v3 LOG_DIR=$WM/logs/plan_b_stage2v3 \
REQUIRE_MANIFEST=1 PREFLIGHT=1 PREFLIGHT_CHECK_MODEL=1 RUN_TRAIN=1 \
GPUS=8 BATCH_SIZE=64 NUM_WORKERS=8 MAX_STEPS=9200 \
bash run_stage2_earthnet.sh 2>&1 | tee $WM/logs/plan_b_stage2v3/train.log
```

### 5.5 评测（官方 GreenEarthNet OOD-t，沿用 68 号 export→score→parity）
```bash
python eval/eval_stage2_earthnet.py --config configs/train/plan_b_stage2v3_pvt.yaml \
  --checkpoint $WM/checkpoints/plan_b_stage2v3/checkpoint_best.pt --split val \
  --data-root $DATA_GEN --output $WM/evaluations/plan_b_val.json
# 冻结后上官方 ood-t_chopped：eval/export_greenearthnet_predictions.py → score_table1_greenearthnet.py → parity
```

---

## 6. Gates / 止损（照 71 号 §8）
- **G0**：官方 parity + 本地 matched ≥0.60。不过 → 修复现，不加状态。
- **G1**：B1(加接口不加loss) ≈ B0，接口不破坏预测。
- **G2 SOTA 门**：3 seed R²>0.62 且 RMSE<0.14 才写 SOTA；否则 competitive。
- **G3 世界模型门**：cross-render>no-φ；latent-future 收敛；冻结状态读出优于 raw-history。
- **G4 SSL4EO 保留门**：B4 相对 B3 有增益（因子化/鲁棒/精度至少一项），否则 SSL4EO 降为对照。
- **止损**：G0 反复不过（复现失败）→ 该分支存疑，转看方案A。

---

## 7. 需要你提供的路径
1. `$WM`　2. `$DATA_GEN`（GreenEarthNet 官方，含 train / ood-t_chopped / iidx）　3. `$DATA_SSL`
4. `$CTX_WEIGHTS`（zenodo 10793870 解压路径；若训练端无网，你先下好）
5. 训练端能否 `git clone` 官方 greenearthnet（无网则你 vendored 进 `third_party/`）

---

## 8. 并行协作提示
- 与方案A `plan-a-vits` 只共享设计、不共享代码；bugfix 用 `git cherry-pick`。
- **方案B 集成成本更高（官方代码+权重+PVT 接线）**，建议先把 Gate 0 打通再上状态契约——G0 是本方案 make-or-break。
- 每步在末尾追加执行记录。

## 9. 参考的现有代码格式（避免出错）
- 训练启动/流程/工厂/评测同 74 号 §9；**方案B额外**：`configs/train/plan_b_contextformer_repro.yaml`、`plan_b_stage2v3_pvt.yaml`、`plan_b_stage1_8_factorize_pvt.yaml`；`models/encoders/pvt_contextformer_q.py`（把 PVT 包成 `q:image→z` 接口）；`third_party/greenearthnet`（官方代码）。**全在 B 分支。**
- 官方资源：代码 https://github.com/vitusbenson/greenearthnet ；权重 https://zenodo.org/records/10793870/files/model_weights.zip ；论文 Benson CVPR 2024。

---

## 执行记录（持续追加）
- [ ] 分支创建 / 官方代码权重就位
- [ ] Gate0 parity：官方=__ / 本地 matched R²=__
- [ ] Stage1.8：steps=__ 因子化=__
- [ ] Stage2 preflight：N_train=__ → MAX_STEPS=__
- [ ] Stage2 主训：val R²=__ SHA=__
- [ ] G0/G1/G2/G3/G4：__
