# 数据方案B · ObsWorld Gate-0 → 主实验 执行汇总（分支 `plan-b-pvt`）

> **标识**:这是**方案B**（Contextformer/PVT-v2-B0 底座）的执行汇总。分支 `plan-b-pvt`,与方案A(`plan-a-vits`)**物理隔离**。活文档,持续追加。对齐 75/71/72 号 doc。

## 0. 一句话
以官方 **Contextformer(PVT-v2-B0, ImageNet 预训练)** 为精度底座,复现到 evaluator parity 后,在其特征上加 ObsWorld 状态契约(state projector + 转移 T + latent-future 一致性 + φ 观测渲染)冲 SOTA。**强基线可恢复:所有新 loss λ=0 → 精确退化回复现的 Contextformer。**

## 1. 基础设施 / 连通性（都已打通）
- **分支/worktree**:`plan-b-pvt`(从 `origin/main`)。本地 `iclr/czj/WorldModel2026-planb`,服务器 `/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb`。与方案A物理隔离,共享 bugfix 只 `cherry-pick`。
- **remote/push**:`github.com/fuchen0614-oss/WorldModel2026`。本地 deploy key + 服务器 `baballuo` 账号,双向 git 可推(小结果/checkpoint 走 git 回传)。
- **机器**:训练 = 服务器 **8×H200(始终满卡训练)**;本地 8×Blackwell 仅 smoke(方案a 0-3 / 方案b 4-7)。**服务器命令开头 `conda activate WorldModel`**(env 在 `/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel`,torch2.12+cu130,timm1.0.28;或 `export PYTHON=…/bin/python` 兜底)。
- **数据（均在服务器,不拷源盘）**:GreenEarthNet `…/TrainData/GreenEarthNet`(train **23816** + val_chopped **952** + ood-t_chopped **1904**);SSL4EO `…/TrainData/SSL4EO-S12-v1.1`(有 `S2L1C`+`S2L2A`+`phi_processed`)。
- **拷盘加速**:`scripts/stage_and_train_plan_b.sh` 把 train+val rsync 到 `/tmp`(带"已拷 SKIP"复用),B0/B1-B4 通用。
- **官方权重**:`contextformer6M/seed42.ckpt`(70MB,走 git 送上服务器,sha256 `ec6706e8…d4a4fa`);seed 27/97 推迟到 3-seed 时补。

## 2. Gate-0 状态
- **A2 架构复现**:`models/encoders/contextformer_official.py`(vendored ContextFormer,去 PL 依赖,torch2.x 可跑)。载官方权重 **0 missing/0 unexpected,6.06M 参数**。
- **A2 数值 parity**(ood-t_chopped,seed42):**RMSE 0.143 / |bias| 0.094 / RMSE25 0.079 对上公开值;R²=0.583**(公开 0.62,低 0.037)。判定=**单 seed vs 论文 3-seed 均值**(打分器已核为与官方 `eval.py` 聚合一致;架构字节级、数据逐行复制)。
- **决策 A**:0.583 记为 **matched 底座**,推进主实验;3-seed 公开 parity 推迟到写 SOTA 前。
- **B0**:8 卡 fp32 从 seed42 微调中(matched 底座,预期 ≈0.583 不跌)。

## 3. 主实验策略（时间紧,冲 SOTA）
**消融矩阵 B0–B4（config 开关驱动,λ=0=B0）**:
| 行 | = B0 + | 需要 |
|---|---|---|
| B0 | (纯复现 Contextformer) | 现成 |
| B1 | + state 接口(projector) | 现成 |
| B2 | + latent-future 一致性 | 现成(无 SSL4EO) |
| B3 | + SSL4EO 成对预训练 | Stage1.8 |
| **B4** | + φ 观测渲染器(**完整 ObsWorld**) | Stage1.8 |

**决策(2026-07-22,时间紧,只 B4 胜 SOTA 才管用)**:
- **除 B0 外,直接训 B4 终版**(唯一决定 SOTA 的行)。B1/B2/B3 **只 smoke 保证可训**,作为消融行留到 B4 成功后再补。
- **B4 前置 = Stage1.8**(SSL4EO L1C/L2A φ 因子化,**小,~450 步,从 ImageNet-PVT init,无 Stage1.5**——旧 Stage1.5 是 ViT-S 12波段,与 PVT 不兼容,不用)。
- **代码**:一套 config 驱动的可扩展模型/loss/训练(强基线可恢复)。
- **并行**:B0 占 GPU 训练时,**CPU 后台建 Stage1.8 的 L1C/L2A 成对 manifest**(不抢 GPU)。
- **batch/epoch**:每卡 batch 待测 H200 上限(8→16→32→?);**epoch 标准 50(matched,B0/B4 一致)**。

### 3.1 各阶段 step/epoch 预算
| 阶段 | 数据 | N | 每卡 batch | global | steps/epoch | epoch | 总 steps |
|---|---|---:|---:|---:|---:|---:|---:|
| **B0/B4 主训** | GreenEarthNet train | 23816 | **8**(待测加大) | 64 | 372 | **50** | **18600** |
| — 若每卡16 | 同上 | 23816 | 16 | 128 | 186 | 50 | 9300 |
| — 若每卡32 | 同上 | 23816 | 32 | 256 | 93 | 50 | 4650 |
| **Stage1.8 φ因子化** | SSL4EO L1C/L2A 成对子集 | ~4000 | 32 | 256 | 15 | 30 | **~450** |
| B0 当前(管线验证) | GreenEarthNet train | 23816 | 8 | 64 | 372 | 40 | 14880 |

> `steps/epoch = N / global_batch`(drop_last);`总 steps = epoch × steps/epoch`。doc 的"8800=200ep"是 **global512(每卡64)** 口径,Contextformer+PVT 未必塞得下,**以 epoch 为准,batch 待 OOM 实测后 B0/B4 统一**。


## 4. 精度对比表（GreenEarthNet OOD-t · 我们 vs SOTA，标注年份）
| 方法 | 年份/来源 | R²↑ | RMSE↓ | 参数 | 备注 |
|---|---|---:|---:|---:|---|
| Persistence | 基线 | 0.00 | 0.23 | 0 | 公开 Benson CVPR24 T2 |
| Previous-year | 基线 | 0.56 | 0.20 | 0 | 公开 |
| Climatology | 基线 | 0.58 | 0.18 | 0 | 公开 |
| Earthformer | **NeurIPS 2022** | 0.52 | 0.16 | 60.6M | 公开 |
| SimVP | **CVPR 2022** | 0.60 | 0.15 | 6.6M | 公开 |
| PredRNN | **NeurIPS 2017** | 0.62 | 0.15 | 1.4M | 公开 |
| **Contextformer** | **CVPR 2024** | **0.62** | **0.14** | 6.1M | 公开 SOTA(本方案底座) |
| — 以下为我们（本地评测栈） — | | | | | |
| 旧 Direct-P4 | ours 诊断 | 0.524 | 0.178 | 28M | 弃用底座 |
| **复现 Contextformer**(seed42,冻结) | ours 复现 | **0.583** | 0.143 | 6.06M | A2 parity |
| B0 matched fine-tune | ours | **0.584** | 0.145 | 6.06M | ✅ ≈底座(fine-tune 未跌);赢 Earthformer/Prev-year、≈Climatology |
| B4 完整 ObsWorld | ours | _待填_ | _待填_ | ~6M+ | 主目标:competitive + 世界模型能力 |

> ⚠️ **口径**:公开值来自各自论文评测;我们的值来自**本地评测栈**(同一栈给"公开 0.62 的模型"打 0.583,即偏严 ~0.037)。跨栈比名次不严格——**干净对比是"我们复现的 Contextformer(0.583)vs 我们的 ObsWorld"**;公开值作参考行,3-seed 对齐后再谈与顶格 competitive。粗体只标真实最佳,不虚标。

### 4.1 Table 2 · Stage1.8 因子化（初步,**train-data**,val 待补）
| 渲染 | MAE↓ | RMSE↓ | SAM↓ | SSIM↑ |
|---|---:|---:|---:|---:|
| L1C→L1C | 0.0147 | 0.021 | 0.065 | 0.902 |
| L1C→L2A(cross) | 0.0198 | 0.030 | 0.095 | 0.835 |
| L2A→L1C(cross) | 0.0173 | 0.026 | 0.074 | 0.899 |
| L2A→L2A | 0.0179 | 0.027 | 0.092 | 0.847 |

> paired latent MSE=**0.00032**(共享状态✓);no-φ 对照 MAE(L1C 0.0183 / L2A 0.0264)> with-φ(0.0147 / 0.0198)→ **φ 承重✓**。⚠️ 此为 **train-data**(过拟合高估风险),正式 Table 2 用 **val** held-out;L1C/L2A 本就相近,φ 效应真实但幅度中等(MAE 改善 ~25–33%),诚实写不夸;Fig 3 φ-swap 待 Read 图确认视觉区分。

## 5. 待办
- [ ] config 驱动骨架:state_projector + `ControlledTransition` T + latent-future loss + φ/O_product;λ 开关
- [ ] Stage1.8:CPU prep(L1C/L2A 成对 manifest)+ 小预训练(φ 因子化)
- [ ] B0 训完评测(R² vs 底座 0.583)
- [ ] **B4 终版训练 + 评测(>0.62 才算 SOTA)**
- [ ] B4 过后:补 B1/B2/B3 消融;3-seed;世界模型 Table2/Fig3(φ 可控渲染)

## 执行记录
- 2026-07-21 A2 复现 + parity(R²=0.583);B0 训练管线 + staging + 双向 push 连通性打通;B0 起训。
- 2026-07-22 策略调整:**B0 + B4 直训**,B1/B2/B3 smoke-only;确认无 Stage1.5、Stage1.8 从 ImageNet-PVT。
- 2026-07-22 **B0 训完 + 评测:R²=0.584 / RMSE=0.145(≈底座 0.583,matched 底座确立)**。config 驱动契约脚手架就绪(λ=0=B0,DDP 安全);Stage1.8 配对 6000 对(0 mismatch)+ 缓存 + 因子化训练/评测代码就绪,Stage1.8 训练已起。
