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

### 3.2 B4 方法型闭环 + 硬约束(2026-07-22)
**叙事(方法闭环)**:观点 = 植被预测应建模为**观测感知的预测态世界模型**(存在产品不变潜状态 z,在已知驱动=天气下演化,观测由 z 经 φ 渲染)→ 拆开"世界是什么(状态动力学)"与"如何观测(φ 渲染)"→ 既提升 **temporal-OOD** 预测,又获得可控/可因子化观测生成。模型 = **一个 shared-z 世界模型**;尺子 = 精度(同栈 OOD-t)+ 能力(Table2/3、Fig3);论证 = 消融 B0→B4 证明世界模型组件**既提升精度又独有能力**。

**硬约束(用户,不可让步)**:B4(权重充分微调后)**必须 > B0**;做不到相对自身基线提升的方案**不选**(**不要求胜 SOTA,只要求胜自身基线**)。

**必须坦白的风险**:当前 contract 作为 loss ≈0(teacher-student cosine 0.9996,梯度≈0 → 不改精度)。要满足硬约束,B4 的精度提升**必须另有来源**:
1. **SSL4EO φ-因子化 + 掩码预训练 共享编码器**(主杠杆:更多数据 + 物理有意义 pretext → 比 ImageNet init 更好 → 尤其利好 temporal-OOD)。
2. **非平凡动力学 aux**:latent-future 改成"用转移 T 从 context z **预测** future z"的真预测(有真实 gap),而非当前平凡项。
3. **预测主路径保持强基线可恢复**(forecasting-primary + 世界模型作 accuracy-relevant aux/init),使世界模型"**只能帮、不能崩**"。

**诚实**:近饱和 benchmark + 强基线上,提升**不保证**;预训练是最靠谱的一枪;哪怕 **+0.01~0.02** 的真实提升也验证观点并满足硬约束。


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

> ⚠️ **口径**:我们表内 0.583/0.584 用的是**最严的双层 LC 聚合(eval.py 权威口径)**。**关键更新(见 §4.2):那 ~0.037 的"gap"主要是聚合口径,不是模型弱** —— 同一预测换成官方 persistence.py 的单层口径就是 **0.664**(压过 published 0.62)。跨栈比名次仍不严格,但结论很硬:**我们在任何合理口径下都不垫底**。干净对比 = 同口径同栈;下一步用 climatology(公开 0.58)锚定 published 到底用哪种口径。粗体只标真实最佳,不虚标。

### 4.1 Table 2 · Stage1.8 因子化(train + **val held-out** 确认)
| 渲染 | MAE (train/val)↓ | SSIM (train/val)↑ |
|---|---|---|
| L1C→L1C | 0.0147 / 0.0158 | 0.902 / 0.877 |
| L1C→L2A(cross) | 0.0198 / 0.0216 | 0.835 / 0.806 |
| L2A→L1C(cross) | 0.0173 / 0.0183 | 0.899 / 0.875 |
| L2A→L2A | 0.0179 / 0.0195 | 0.847 / 0.818 |

> paired latent MSE=**0.00032**(共享状态✓);no-φ 对照 val(L1C 0.0188 / L2A 0.0281)> with-φ(0.0158 / 0.0216)→ **φ 承重✓**。**val ≈ train → 无过拟合,因子化机制真成立、可泛化。** Fig 3 φ-swap **已 Read 确认**:换 φ 有明显色调区分(φ 控制产品✓),**但渲染偏糊**(轻量 decoder + MSE + 短训 ~700 步)→ 作论文 Fig3 需加强渲染器(更大 decoder + 感知/频谱损失 + 训久)。L1C/L2A 本就相近,φ 效应真实但幅度中等,诚实写不夸。

### 4.2 口径诊断 · 0.037 gap 主要是 LC 聚合口径,不是模型弱（2026-07-22）
同一批预测(2,112,698 eligible pixels,ood-t_chopped)在三种聚合口径下打分:

| 聚合口径 | B0 R² | A2(冻结)R² | 出处 |
|---|---:|---:|---|
| **双层(per-cube→per-LC,eval.py)** | 0.5842 | 0.5827 | 官方权威 evaluator,最严 |
| **单层(per-LC over pixels,persistence.py)** | **0.6642** | **0.6623** | 官方另一脚本,pixel 加权 |
| 全局像素(无 LC 平衡) | 0.6791 | 0.6785 | 最宽松 |

> **换口径 = +0.08**(同模型同预测)。官方代码自身两个脚本口径不一致。**单层口径下我们复现的 ContextFormer = 0.664 > published 0.62。** 结论:①那 0.037 主要是**口径**,不是模型弱;②**我们在任何合理口径下都不垫底**(0.58~0.68 vs 对手 0.52~0.62);③per-LC 双层 NSE 甚至为负(-0.02),说明双层被"少像素高方差 cube"拖累,单层更稳。**严格发表要求同口径同栈**——下一步:climatology(公开 0.58)两种口径各打一次,看哪种口径能复出 0.58,即锁定 published 用的口径。

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
- 2026-07-22 **口径诊断(§4.2):双层 0.5842 / 单层 0.6642 / 全局 0.6791,换口径 +0.08**。审计 B0 推理=verbatim 无 bug → 0.583 是忠实复现;0.037 主因是 LC 聚合口径而非模型弱;**单层口径下复现 ContextFormer 0.664 > published 0.62,任何口径下都不垫底**。vendored 官方 eval.py + `eval/diagnose_aggregation_gap.py` 已 push。下一步 climatology 锚定 published 口径。
- 2026-07-22 **策略敲定(§3.2):B4=方法型闭环(观点→模型→尺子→论证);硬约束 B4>B0(否则不选,不要求胜 SOTA)**。坦白 contract-as-loss≈0 → 精度提升须来自 SSL4EO 预训练 + 非平凡动力学 aux + 可恢复主路径。本地已确认 8×Blackwell GPU + ContextFormer 官方 ckpt 在手,可本地 CPU 冒烟;②前沿基线(SimVP/Earthformer)确认可行(emp 代码 + Zenodo 权重 `10793870`)。下一步:搭 B4(一个 shared-z 模型)+ 本地冒烟。
- 2026-07-22 **B4 建成(§3.2,方案A):`models/plan_b_b4.py · ObsWorldB4` = 一个 shared-z 世界模型**(q→z 预测主干=B0 │ projector │ 零初始 `ControlledTransition` │ `PhiRenderer` O(z,φ))。加**前沿件治 contract≈0 塌缩**:**JEPA 潜未来预测**(T 从 context 状态预测 future 状态,stop-grad)+ **VICReg 反塌缩**(var hinge + cov 去相关,破 cos0.9996 退化)。本地 CPU 冒烟 **8/8 PASS**:`B4 forecast==B0` 逐值(max|Δ|=0)、λ=0 损失精确 0、λ>0 JEPA(0.255)+VICReg(var0.317/cov6.05)非平凡且梯度分别进 transition/projector。+0.87M 参数。**表示论点(可引用)**:预测态 z 满足①产品不变②驱动可控可预测③不塌缩 → "不变·可控·可预测"即支持可复用世界建模的表示。本地仅测试(GPU 4-7),全量训练待服务器 8×H200。
- 2026-07-22 **B4 训练器就绪 + 本地 GPU 训练冒烟(仅4-7)**:`train/train_plan_b_b4.py`(复用 B0 数据/eval 管线,换 ObsWorldB4 + `--lambda-dyn/--lambda-vic` + DDP find_unused=True)+ `scripts/smoke_b4_train.py`。Blackwell sm_120 上 6 步 **ALL PASS**(loss 降、backbone 更新、λ=0 可恢复、无 NaN)。修 VICReg 为标准 **25:1**(var:cov)→ `vic_var` 转为下降(反塌缩生效)、`latent_future` 随之升(状态变丰富→未来预测成真信号)。**消融阶梯:B4a=warm-start+aux;B4b=+SSL4EO 预训**。全量待用户点头 + 上服务器。
