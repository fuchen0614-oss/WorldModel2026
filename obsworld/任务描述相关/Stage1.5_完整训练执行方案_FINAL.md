---
title: "25 Stage1.5 双端条件化训练策略与决策记录"
aliases:
  - Stage1.5 双端条件化
  - Stage1.5 Canonical Strategy
  - ObsWorld State Estimation
created: 2026-07-03
updated: 2026-07-03
author: Zhijian Liu / Codex
project: ObsWorld
stage: "1.5"
status: implemented-and-smoke-tested
tags:
  - ObsWorld
  - stage1.5
  - imaging-condition
  - FiLM
  - state-space
  - multimodal
  - training-strategy
---

# 25 Stage1.5 双端条件化训练策略与决策记录

> [!abstract] 本文定位
> 本文是 Stage1.5 的最新权威决策与执行说明。它记录了从“φ仅进编码器”到“φ仅进解码器”，再到最终“双端条件化”的完整推理过程，并给出正式模型、数据、损失、训练、step/epoch 换算、消融和验收标准。若旧文档与本文冲突，以本文为准。

## 0. 一页结论

最终采用：

$$
s_t=E(X_t,\phi_t),\qquad
\hat X_t=R(s_t,\phi_t)
$$

- Encoder 用已知成像条件反演、校正当前观测。
- Stage1.5 辅助 Decoder 用相同 φ 解释原始观测。
- Stage2 只接收 $s_t,D,G,h$，不接收 φ。
- 不把不同季节无条件拉齐，避免删除物候、积雪、洪水等真实状态变化。
- 主一致性监督来自近同期 S1/S2；正式阈值为 7 天，14 天只做消融。
- φ 主输入只保留纯采集因素：S2 太阳高度角；S1 升降轨、相对轨道、卫星平台。
- 经度、纬度、season、day-of-year、DEM 不进入 Stage1.5 主 φ。
- 云、云影、无效像素作为重建质量 mask，不要求状态或一个标量 φ 重建云形状。

> [!success] 正式入口
> - 配置：`configs/train/stage1_5_dual_conditioned_vits.yaml`
> - 训练：`train/train_stage1_5_dual_conditioned.py`
> - 8卡启动：`scripts/train_stage1_5_dual_conditioned_fsdp8.sh`
> - 测试：`tests/test_stage1_5_dual_conditioned.py`

## 1. 与其他文档的关系

- 总纲：[[10ObsWorld 完整实验流程与字段设计]]
- 早期 Encoder-only 方案：[[12_Stage1.5成像条件解耦实施方案与phi字段预处理完整报告]]
- 早期 FiLM 约束：[[13_项目进度汇报与phi数据集结构及FiLM设计约束]]
- 旧实现报告：[[14 Stage1.5与Stage2代码实现报告]]
- 架构冲突诊断：[[18_现状评估与后续训练路线决策文档]]
- S1 几何审查：[[20_S1几何字段审查报告]]
- φ v3 字段：[[21_phi_v3与geo字段说明文档]]
- 完整方法与 Stage2：[[23_ObsWorld完整方法框架与Stage2动力学算法设计]]
- 历史 step/epoch：[[23_Step_Epoch换算与各阶段训练时长权威汇总]]
- 当前问题：[[24_当前问题梳理与解决方案]]

## 2. 本轮关键问答与决策时间线

### 2.1 问题一：φ 原本是不是只进入 Encoder？

是。12、13、14 号文档的原始方案为：

```text
Encoder(X, φ) → z
LightDecoder(z) → X_hat
```

φ 通过 FiLM/cross-attention 注入共享 Transformer，Decoder 不接 φ。

### 2.2 问题二：为什么代码后来变成 Decoder-only？

18 号文档发现旧训练同时要求：

1. Encoder 使用 φ；
2. shuffle φ 后状态保持不变。

两者互相矛盾。2026-06-29 后代码切换为 Plan A：

```text
Encoder(X) → z
Decoder(z, φ) → X_hat
```

### 2.3 问题三：最终为什么不是简单恢复 Encoder-only？

若 $z$ 已真正去除 φ，而 Decoder 不知道 φ，它无法重建带原太阳角、轨道和传感器外观的观测。重建损失会反向迫使 $z$ 偷偷保留 φ。因此 Encoder-only 与“严格状态解耦 + 原观测重建”不能同时满足。

### 2.4 最终决策：双端条件化

```text
φ ───────┬──> Encoder FiLM（反演校正）
         │
X ───────┴──> state tokens
                    │
φ ─────────────────┴──> Auxiliary Decoder FiLM ──> X_hat
```

这对应条件推断与条件生成：

$$
q(s_t\mid X_t,\phi_t),\qquad p(X_t\mid s_t,\phi_t)
$$

> [!important] 双端条件化不等于两端随意依赖 φ
> 只在 Encoder 最后4层使用零初始化 FiLM；Decoder 使用独立 FiLM；最终状态通过真实近同期跨模态监督、φ泄漏约束和状态保留评估共同约束。

## 3. ObsWorld 5+1 阶段及各自产物

| 阶段 | 目标 | 输入 | 输出/交付物 |
|---|---|---|---|
| Stage 0 | 数据、字段、划分可信 | 原始数据、metadata | schema、field mask、φ/D/G定义、时空配对 |
| Stage 1 | 学会读取遥感影像 | S1/S2、mask | 通用 MAE tokens、ViT-S encoder；尚不能称为真实状态 |
| **Stage 1.5** | 从有偏观测估计当前状态 | $X_t,\phi_t$ | 成像干扰低、真实变化保留的 $s_t$ |
| Stage 2 | 学状态如何演化 | $s_t,D,G,h$ | $p(s_{t+h}\mid s_t,D,G,h)$、转移与不确定性 |
| Stage 3 | 把未来状态投影为未来观测 | $s_{t+h},\phi_{t+h}$ | $\hat X_{t+h}$、条件可控观测模型 |
| Stage 4 | 下游与 world-model 评估 | 状态、驱动、标签 | 洪水/LULC/变化、反事实、校准实验 |
| Stage 5 | 基础模型增强与公平对比 | Prithvi/CROMA/DOFA等 | 替换骨干、LoRA/冻结基线、最终对比 |

Stage1.5 的正式产物不是一个“更好的重建器”，而是：

```text
state_encoder
+ pure_phi_encoder
+ spatial_state_projector
+ auxiliary_conditioned_decoder
+ state/phi evaluation protocol
```

## 4. 系统误差与真实变化的显式分解

对模态 $m$：

$$
X_t^{(m)}=g_m(S_t,\phi_t^{(m)})+\epsilon_t^{(m)}
$$

- $S_t$：真实地表状态；
- $\phi_t^{(m)}$：传感器与采集几何；
- $g_m$：模态相关观测过程；
- $\epsilon$：未建模噪声、云、配准误差。

两期观测变化可精确分解为：

$$
X_{t+h}-X_t=
\underbrace{g(S_{t+h},\phi_{t+h})-g(S_t,\phi_{t+h})}_{\text{真实状态变化}}
+
\underbrace{g(S_t,\phi_{t+h})-g(S_t,\phi_t)}_{\text{成像条件变化}}
$$

这是一种 counterfactual/telescoping decomposition：固定未来 φ 比较状态，固定当前状态比较 φ。Stage1.5 学逆过程，Stage2 学第一项，Stage3 使第二项可观测。

> [!note] 暂不新增隐式 systematic-error latent
> 已知系统因素进入 φ；剩余误差先进入 $\epsilon$/不确定性。只有后续发现稳定残差无法由现有 φ 解释时，才增加 nuisance latent，避免当前架构无谓复杂化。

## 5. Stage1.5 状态定义

### 必须保留

- 植被物候、NDVI、含水量；
- 洪水、积雪、火烧、耕作变化；
- 土地覆盖、建筑与真实空间结构；
- 当前状态的不确定性线索。

### 应尽量消除

- S1/S2 传感器差异；
- 太阳高度角带来的辐射/阴影差异；
- S1 升降轨、相对轨道、卫星平台差异；
- 云、无效像素等观测污染。

### 不再使用的错误假设

```text
同一地点不同季节 = 同一状态
```

季节间包含真实物候、积雪和水文变化，不能无条件用 InfoNCE 拉齐。

## 6. 正式模型

### 6.1 Backbone

- ViT-S/16；
- embed=384，depth=12，heads=6；
- 从 `checkpoint_step_95000.pt` 严格加载153个 Encoder tensor；
- Encoder 参数约23.95M，其中仅最后4层新增16个 FiLM tensor；
- Stage1 Teacher 为冻结的22.77M原始 Encoder。

### 6.2 φ Encoder

`PureImagingConditionEncoder`：

| 模态 | 使用字段 | 排除字段 |
|---|---|---|
| S2 | sun elevation、time valid | lat/lon、season、day-of-year、cloud、DEM |
| S1 | orbit direction、relative orbit、satellite | lat/lon、season、day-of-year、cloud、DEM |

训练时10%样本将 φ embedding 置零，建立 missing/null-condition 鲁棒性。

### 6.3 双端注入

- Encoder：仅 blocks 8–11 使用 FiLM；blocks 0–7 保持 Stage1 原结构。
- Encoder cross-attention：关闭。单个 φ token 上的 cross-attention 信息增益有限且参数冗余。
- Decoder：4个轻量 Transformer block 各自使用独立 FiLM。
- 所有新增 γ/β 投影零初始化，起点严格等价 Stage1。

### 6.4 状态接口

```text
ViT tokens [B,N,384]
  → SpatialStateProjector
  → state_tokens [B,N,256]
```

后续 Stage2 只允许消费 `state_tokens`，不得直接读取 φ embedding。

## 7. 数据配对

每个地点随机选择一个季节索引 $t$，读取：

```text
S1[t], φ_S1[t], timestamp_S1[t]
S2[t], φ_S2[t], timestamp_S2[t], cloud_mask[t]
```

全量243,968地点统计：

| 阈值 | S1/S2 配对覆盖率 |
|---|---:|
| ≤7天 | 约70–72% |
| ≤14天 | 约88–90% |
| ≤30天 | 约99.98% |

正式训练只对≤7天样本启用跨模态状态一致性；其他样本仍参与重建与单模态正则。

## 8. Loss

$$
\mathcal L=
\mathcal L_{MAE}
+\alpha\mathcal L_{xmodal}
+\beta\mathcal L_{nuisance}
+\gamma\mathcal L_{anchor}
$$

### 8.1 重建

- S1/S2 masked L1 等权平均；
- S2 排除 no-data、saturated、cloud-shadow、medium/high cloud、cirrus；
- 不要求状态记住云的空间形状。

### 8.2 跨模态状态一致性

使用 VICReg 风格：

- invariance：近同期 S1/S2 状态靠近；
- variance：每个维度保持方差，防止常数坍塌；
- covariance：减少冗余维度；
- 分布式训练时跨 rank 汇聚状态再计算。

### 8.3 φ 泄漏约束

对固定的原始成像字段计算 state–φ cross covariance，不再让一个 learned φ encoder 与 state encoder 共同旋转、规避 cosine loss。

### 8.4 Stage1 anchor

冻结 Stage1 Teacher，对当前 Encoder 的 pooled token 加 cosine anchor，避免解耦训练破坏已学语义。

### 8.5 权重

| Step | alignment | nuisance | anchor | MAE |
|---:|---:|---:|---:|---:|
| 0 | 0.05 | 0.00 | 0.10 | 1.00 |
| 10k | 0.20 | 0.02 | 0.10 | 1.00 |
| 10k–30k | 0.20 | 0.02 | 0.10 | 1.00 |

## 9. 冻结、学习率与训练阶段

| 阶段 | Step | 可训练参数 | LR |
|---|---:|---|---:|
| A | 0–2k | φ Encoder、state projector、Encoder/Decoder FiLM | 新模块 $10^{-4}$ |
| B | 2k–10k | A + Encoder blocks 8–11 + norm | 旧模块 $10^{-5}$ |
| C | 10k–30k | 完整 Encoder/Decoder | 旧模块 $10^{-5}$，新模块 $10^{-4}$ 起始 |

- AdamW，betas=(0.9,0.95)，weight decay=0.05；
- warmup=1000 optimizer steps；
- cosine：旧模块最低 $10^{-6}$，新模块最低 $10^{-6}$；
- bf16；
- gradient clipping=1.0；
- 8卡 FSDP2。

## 10. Step / Epoch 权威换算

### 10.1 正式配置

```text
地点数 N_loc           = 243,968
每地点季节数          = 4
四季样本数 N_season   = 975,872
GPU数                  = 8
per-GPU micro batch    = 64
gradient accumulation = 2
effective global batch= 8 × 64 × 2 = 1,024
```

每个 optimizer step 同时处理 S1 和 S2，且两者使用同一批地点。因此：

$$
\text{steps/full-season-epoch}
=\frac{243,968\times4}{1,024}
=953
$$

> [!danger] 这里绝不能再除以2
> Stage1 的 dual 模式是 S1/S2 轮流更新；新 Stage1.5 每个 step 同时前向 S1 和 S2，每个模态都获得完整 batch 更新。

### 10.2 两种 epoch 口径

| 口径 | 定义 | Steps/epoch |
|---|---|---:|
| dataloader/location epoch | 每个地点平均被采样一次 | $243,968/1,024=238.25$ |
| **每模态四季完整覆盖 epoch** | 每个地点4个季节平均各见一次 | **953** |

论文与文献对比统一使用“四季完整覆盖 epoch”。

### 10.3 正式阶段换算

| Optimizer steps | Location epochs | 四季完整覆盖 epochs | 作用 |
|---:|---:|---:|---|
| 2,000 | 8.39 | 2.10 | 新模块热身 |
| 5,000 | 20.99 | 5.25 | 第一中间检查点 |
| 10,000 | 41.97 | 10.49 | 是否进入全解冻的门槛 |
| 20,000 | 83.95 | 20.99 | 完整训练中段 |
| 30,000 | 125.92 | 31.48 | 推荐上限 |

### 10.4 若 batch 改变

$$
B_{eff}=N_{GPU}\times B_{micro}\times N_{accum}
$$

$$
\text{steps/full-season-epoch}=975,872/B_{eff}
$$

| Effective batch | Steps/full-season epoch | 30k对应epoch |
|---:|---:|---:|
| 512 | 1,906 | 15.74 |
| 1,024 | 953 | 31.48 |
| 2,048 | 476.5 | 62.96 |

任何 GPU数、micro batch 或 accumulation 改动后，都必须重算，不能只复制30k。

## 11. 训练命令

### 11.1 开训前检查

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

test -f checkpoints/stage1_vits_dual_staged/checkpoint_step_95000.pt
test -d /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed
test -d /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed_v3_s1geom
```

### 11.2 CPU测试

当前环境未安装 pytest，可直接调用测试函数：

```bash
python - <<'PY'
import tests.test_stage1_5_dual_conditioned as t
for name in sorted(n for n in dir(t) if n.startswith('test_')):
    print('RUN', name)
    getattr(t, name)()
print('ALL PASSED')
PY
```

### 11.3 8卡正式训练

```bash
bash scripts/train_stage1_5_dual_conditioned_fsdp8.sh
```

或：

```bash
torchrun --nproc_per_node=8 --nnodes=1 \
  --rdzv_backend=c10d --rdzv_endpoint=localhost:0 \
  train/train_stage1_5_dual_conditioned.py \
  --config configs/train/stage1_5_dual_conditioned_vits.yaml
```

## 12. 10k Go/No-Go 门槛

不得只看总 loss。需同时满足：

1. **状态保留**：EuroSAT/LULC性能相对 Stage1 下降≤1个百分点；NDVI/变化能力无显著下降。
2. **成像解耦**：S1↔S2检索/一致性优于 Stage1 与 MAE-continue。
3. **φ泄漏**：太阳角、轨道、平台 probe 相对 Stage1 明显下降。
4. **条件有效**：正确 φ 的验证重建优于错误/shuffled φ。
5. **重建稳定**：验证 MAE 相对 MAE-continue 恶化≤5%。
6. **无坍塌**：state维度标准差、协方差与有效秩正常。

任一核心门槛失败时停在10k，分析 loss 梯度比例与字段泄漏，不盲跑30k。

## 13. 必做消融

| 实验 | 目的 |
|---|---|
| Stage1 95k | 原始状态/泄漏基线 |
| MAE-continue | 排除“只是多训练”的收益 |
| Decoder-only φ | 对比旧 Plan A |
| Encoder-only φ | 对比12–14号早期方案 |
| **Dual-ended φ** | 正式方案 |
| Dual-ended w/o S1 geometry | 验证轨道字段价值 |
| 7-day vs 14-day pair | 时间阈值敏感性 |
| w/o φ cross-cov | 验证泄漏正则 |
| w/o teacher anchor | 验证语义遗忘风险 |

## 14. 20篇前沿文章证据矩阵

> [!info] 状态说明
> “正式发表”按已知会议/期刊版本记录；2025–2026的快速演进工作中，部分仍是 arXiv 预印本，不能把预印本结果写成已同行评审结论。

| 工作 | 年份/状态 | 对本文的直接启发 |
|---|---|---|
| [SkySense](https://arxiv.org/abs/2312.10115) | CVPR 2024 | 多模态时空与多粒度对齐 |
| [CROMA](https://arxiv.org/abs/2311.00566) | NeurIPS 2023 | 雷达—光学对比与MAE互补 |
| [Presto](https://arxiv.org/abs/2304.14065) | NeurIPS 2023 | 时间/位置条件可帮助遥感编码 |
| [DeCUR](https://arxiv.org/abs/2309.05300) | ECCV 2024 | 公共状态与模态独有因素不能混为一谈 |
| [DOFA](https://arxiv.org/abs/2403.15356) | CVPR 2024 | 波长条件化与多传感器适配 |
| [SatMAE++](https://arxiv.org/abs/2403.05419) | CVPR 2024 | 多尺度、多光谱MAE设计 |
| [AnySat](https://arxiv.org/abs/2412.14123) | 2025论文版本 | JEPA与跨分辨率/模态统一 |
| [Prithvi-EO-2.0](https://arxiv.org/abs/2412.02732) | TGRS 2025 | 时间与位置embedding、全球多时相预训练 |
| [SeaMo](https://arxiv.org/abs/2412.19237) | Information Fusion 2025 | 季节是可建模信号，不应简单删除 |
| [TerraMind](https://arxiv.org/abs/2504.11171) | 2025论文版本 | 任意模态生成与token/pixel双尺度 |
| [Copernicus-FM](https://arxiv.org/abs/2503.11849) | 预印本 | 灵活metadata encoding与任意传感器 |
| [Panopticon](https://arxiv.org/abs/2503.10845) | CVPRW 2025 | 同地点跨传感器作为自然增强 |
| [TerraFM](https://arxiv.org/abs/2506.06281) | 预印本 | S1/S2局部—全局对比与跨注意力 |
| [SatDINO](https://arxiv.org/abs/2508.21402) | 预印本 | 遥感DINO、GSD编码与自适应视图 |
| [OPTIMUS](https://arxiv.org/abs/2506.13902) | 预印本 | 时间顺序用于检测持久真实变化 |
| [TerraFlow](https://arxiv.org/abs/2603.12762) | 预印本 | 变长多模态多时相目标，时间变化不可粗暴不变 |
| [LEPA](https://arxiv.org/abs/2603.07246) | 预印本 | 显式条件预测变换后的embedding |
| [RS-WorldModel](https://arxiv.org/abs/2603.14941) | 预印本 | 地理/采集metadata用于未来场景生成 |
| [EO-WM](https://arxiv.org/abs/2606.27277) | 预印本 | 天气驱动与概率EO预测；仍以观测预测为主 |
| [VegSim](https://arxiv.org/abs/2606.21961) | 预印本 | latent状态、可控forcing与概率预测 |

综合结论：

- 近同期跨传感器是最可靠的状态一致性来源；
- 时间与季节可能包含真实动力学信号，不能默认当 nuisance；
- 已知metadata可以参与条件推断；
- 状态与观测分离需要条件生成端；
- 公共状态与模态独有信息应通过明确接口与评估区分；
- 续训应使用identity初始化、阶段解冻和低主干学习率。

## 15. 失败模式与回滚

| 失败 | 诊断 | 回滚 |
|---|---|---|
| state collapse | 方差下降、有效秩低 | 降 alignment，提高 variance/anchor |
| 物候被抹掉 | NDVI/变化指标下降 | 缩短配对阈值、降低一致性权重 |
| φ完全被忽略 | correct/shuffle φ重建无差异 | 检查FiLM梯度、提高条件drop对照与Decoder条件能力 |
| 语义遗忘 | EuroSAT/LULC下降 | 延长冻结阶段、降低base LR、提高anchor |
| S1/S2过度拉齐 | 模态独有任务下降 | 仅对state projector对齐，不对raw ViT token强制相等 |
| 数据吞吐不足 | GPU利用率波动 | 使用本地staged数据、调workers/prefetch，不先改batch语义 |
| OOM | H200显存不足 | per-GPU 64→32，accum 2→4，保持effective batch=1024 |

## 16. 实施状态检查单

- [x] ViT-S 384/12/6正式配置
- [x] 95k checkpoint严格共享权重加载
- [x] Encoder最后4层FiLM
- [x] Decoder每层FiLM
- [x] 移除Encoder cross-attention
- [x] Pure φ字段接口
- [x] state tokens `[B,N,256]`
- [x] 单季S1/S2配对
- [x] 时间差与7天门控
- [x] S2 cloud/invalid质量mask
- [x] VICReg状态一致性与防坍塌
- [x] φ cross-cov泄漏约束
- [x] Stage1 Teacher anchor
- [x] 三阶段冻结/解冻
- [x] 分层LR与梯度累积
- [x] CPU集成测试（5项全过）
- [x] 真实权重加载验证（missing=0, unexpected=16个新FiLM）
- [x] 单卡smoke test（1 step成功，生成checkpoint_step_1.pt）
- [x] 唯一正式配置与启动脚本
- [x] 旧Plan A文件清理完成
- [ ] 10k Go/No-Go评估结果（训练后）
- [ ] 完整消融表（训练后）

## 17. 最终边界

- 本轮不实现 D/G/h dynamics；
- Stage1.5 Decoder是辅助条件重建器和Stage3初始化，不替代完整Stage3；
- Stage2不得读取 φ；
- 不把季节和物候当成成像误差；
- 旧 checkpoint 和历史任务文档不覆盖；
- 旧 Plan A 可执行文件在新路线验证后删除，历史设计保留在本文和旧任务文档中供审计。

---

> [!quote] 一句话复盘
> Stage1负责“看懂图像”，Stage1.5负责“在已知怎么拍的前提下估计地表现在是什么”，Stage2才负责“在D/G/h作用下地表以后会变成什么”。

---

## 18. 评估验证完整方案

### 18.1 为什么需要评估验证？

Stage1.5 有两个**原创设计**（文献中无直接先例），需要通过评估验证假设是否成立：

#### 原创设计1：φ 泄漏 cross-covariance 正则

**理论声明**：
```python
# 直接正则化 state 与原始 φ 字段的线性相关性
cross_cov = state.T @ phi_raw / (batch_size - 1)
loss_nuisance = cross_cov.square().mean()
```

**问题**：
- 这只约束了**线性独立性**
- Encoder 可能通过**非线性变换**偷偷保留 φ 信息
- 例如：`state = sin(φ) + cos(φ²)` → 线性 cross-cov 测不出，但信息仍在

**验证目的**：
- 确认 cross-covariance 正则是否真的阻止了**非线性泄漏**
- 若失败 → 需改用对抗训练（discriminator）或更强正则

#### 原创设计2：Pure φ 字段选择

**理论声明**：
- 排除 lat/lon/season/DEM，因为它们是"状态捷径"
- 只保留纯成像因素（sun elevation, orbit, satellite）

**问题**：
- 这是一个**假设**，没有定量证据
- 若 lat/lon 真的不包含状态信息 → state 应该**无法预测** lat/lon
- 但若 state 仍能高精度预测 lat → 说明假设不成立

**验证目的**：
- 确认 Pure φ 假设是否成立（state 是否真的不含 lat/lon/season）
- 若失败 → 需重新审视字段选择或加额外正则

---

### 18.2 评估脚本使用说明

#### 脚本1：非线性 φ 泄漏 probe

**文件**：`eval/eval_phi_leakage_probe.py`

**用途**：训练 3 层 MLP probe，测试 state 是否仍能预测 φ

**用法**：
```bash
python eval/eval_phi_leakage_probe.py \
  --stage1_ckpt checkpoints/stage1_vits_dual_staged/checkpoint_step_95000.pt \
  --stage1_5_ckpt checkpoints/stage1_5_dual_conditioned_vits/checkpoint_step_10000.pt \
  --split val \
  --batch_size 128 \
  --probe_epochs 5
```

**输出示例**：
```
φ Leakage Probe Results (Non-linear 3-layer MLP)
============================================================
Metric                         Stage1          Stage1.5        Δ
------------------------------------------------------------
Sun Elevation MAE (°)          8.20            14.70           +79.3%
Orbit Direction Acc (%)        87.30           56.20           -31.1%
Satellite Acc (%)              82.70           52.10           -37.0%
============================================================

✅ 判定：φ 泄漏约束有效（非线性 probe 准确率接近随机）
```

**判定标准**：
- ✅ **成功**：Stage1.5 准确率 < Stage1 且接近随机（Orbit/Satellite ≈50%）
- ⚠️ **部分有效**：准确率下降 > 20% 但未达随机
- ❌ **失败**：准确率 ≈ Stage1（需加对抗训练）

---

#### 脚本2：Pure φ 假设验证

**文件**：`eval/eval_pure_phi_assumption.py`

**用途**：训练 linear probe，测试 state 是否仍能预测 lat/lon/season

**用法**：
```bash
python eval/eval_pure_phi_assumption.py \
  --stage1_ckpt checkpoints/stage1_vits_dual_staged/checkpoint_step_95000.pt \
  --stage1_5_ckpt checkpoints/stage1_5_dual_conditioned_vits/checkpoint_step_10000.pt \
  --split val \
  --batch_size 128 \
  --probe_epochs 10
```

**输出示例**：
```
Pure φ Assumption Validation (Linear Probe)
============================================================
Metric                         Stage1          Stage1.5        Δ
------------------------------------------------------------
Lat/Lon MAE (°)                2.30            4.80            +108.7%
Season Acc (%)                 45.20           28.30           -16.9%
DEM MAE (m)                    180.50          320.40          +77.5%
============================================================

✅ 判定：Pure φ 假设成立（lat/lon/season 不在状态中）
```

**判定标准**：
- ✅ **成功（理想）**：Season ≈25%（随机），Lat/Lon MAE 显著升高
- ⚠️ **可接受**：Season 25-40%（可能是真实物候，不是捷径）
- ❌ **失败**：Season >40% 或 Lat/Lon MAE ≈ Stage1（Pure φ 排除不彻底）

---

#### 批量评估所有 checkpoint

**文件**：`scripts/batch_eval_all_checkpoints.sh`

**用途**：自动评估 5k/10k/15k/20k/25k/30k 所有 checkpoint

**用法**：
```bash
bash scripts/batch_eval_all_checkpoints.sh
```

**输出**：
```
logs/eval_phi_leakage_step_5000.log
logs/eval_phi_leakage_step_10000.log
logs/eval_pure_phi_step_5000.log
logs/eval_pure_phi_step_10000.log
...
```

**查看结果**：
```bash
grep "判定" logs/eval_phi_leakage_step_10000.log
grep "判定" logs/eval_pure_phi_step_10000.log
```

---

### 18.3 评估时机与流程

#### 推荐策略：全量训练 + 事后验证

```
┌─────────────────────────────────────────────────────┐
│ 阶段1：启动全量训练（无需人工介入）                │
├─────────────────────────────────────────────────────┤
│ bash scripts/train_stage1_5_dual_conditioned_fsdp8.sh│
│                                                       │
│ 训练时长：约 6-7 小时（8×H200）                     │
│ 自动保存：每 5k 一个 checkpoint                      │
├─────────────────────────────────────────────────────┤
│ 阶段2：批量验证所有 checkpoint（训练完成后）        │
├─────────────────────────────────────────────────────┤
│ bash scripts/batch_eval_all_checkpoints.sh           │
│                                                       │
│ 验证时长：约 2-3 小时/checkpoint（单 GPU）          │
│ 可并行：多个 GPU 同时验证不同 checkpoint            │
└─────────────────────────────────────────────────────┘
```

**为什么不分阶段训练？**
1. **总时长短**（<7h），即使 10k 有问题，浪费也可接受
2. **无需人工介入**，可以晚上启动
3. **可以对比不同阶段**：观察 5k→10k→30k 的验证曲线
4. **论文写作更方便**：有完整训练过程数据

---

### 18.4 验证结果解读

#### 场景1：10k 验证全部通过 ✅

**现象**：
- φ 泄漏 probe：准确率下降 >30%，接近随机
- Pure φ probe：Season ≈25-35%，Lat/Lon MAE 显著升高
- 原有 6 项（EuroSAT/LULC/S1↔S2/重建/坍塌）全通过

**判定**：✅ **方案有效，继续使用 30k checkpoint**

**后续**：
- 论文中报告 30k 结果
- 10k 验证结果放附录（证明方法稳定）

---

#### 场景2：φ 泄漏 probe 失败 ❌

**现象**：
- 非线性 MLP probe 准确率仍高（>70%）
- 说明 cross-covariance 正则无法阻止非线性泄漏

**判定**：❌ **φ 泄漏约束失效**

**解决方案**：
1. **方案A**：提高 nuisance_loss 权重（0.02 → 0.05）
2. **方案B**：改用对抗训练（加 discriminator）
3. **方案C**：加 information bottleneck 正则

**实施**：
- 从 10k checkpoint 恢复
- 修改配置，继续训练 10k→30k
- 重新验证

---

#### 场景3：Pure φ probe 失败 ❌

**现象**：
- Season 准确率仍高（>50%）
- Lat/Lon MAE ≈ Stage1（位置信息仍在 state）

**判定**：❌ **Pure φ 假设不成立**

**解决方案**：
1. **方案A**：在 φ encoder 中显式排除这些字段（已做，但可能 encoder 从图像中学到）
2. **方案B**：加额外的 lat/lon/season adversarial loss
3. **方案C**：重新审视"这些是否真的是捷径"（可能是真实状态的一部分）

**实施**：
- 与导师/合作者讨论：Season 包含物候是否可接受？
- 若不可接受 → 加对抗 loss，从 10k 恢复训练
- 若可接受 → 修改理论声明，承认 state 包含季节/物候

---

## 19. 训练执行完整清单

### 19.1 训练前检查

```bash
# 1. 检查 Stage1 95k checkpoint
test -f checkpoints/stage1_vits_dual_staged/checkpoint_step_95000.pt && echo "✓ Stage1 checkpoint OK"

# 2. 检查 φ 数据
test -d /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed && echo "✓ φ v2 OK"
test -d /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed_v3_s1geom && echo "✓ φ v3 OK"

# 3. 激活环境
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
python --version  # 应该是 Python 3.9+

# 4. 运行 CPU 测试（可选）
python -c "
import tests.test_stage1_5_dual_conditioned as t
for name in sorted(n for n in dir(t) if n.startswith('test_')):
    print('RUN', name)
    getattr(t, name)()
print('✅ ALL PASSED')
"
```

---

### 19.2 启动训练

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

# 启动 8 卡训练
bash scripts/train_stage1_5_dual_conditioned_fsdp8.sh
```

**预期输出**：
```
[Step 100] loss=2.345 mae=1.234 xmodal=0.456 nuisance=0.012 anchor=0.089
[Step 200] loss=2.012 mae=1.105 xmodal=0.398 nuisance=0.011 anchor=0.078
...
[Step 2000] Unfreezing Encoder blocks 8-11
[Step 5000] Saving checkpoint...
[Step 10000] Unfreezing full Encoder/Decoder
[Step 10000] Saving checkpoint...
...
[Step 30000] Saving checkpoint...
Training complete!
```

---

### 19.3 监控训练

```bash
# 实时查看训练日志
tail -f logs/stage1_5_dual_conditioned_vits/train.log

# 查看 TensorBoard
tensorboard --logdir logs/stage1_5_dual_conditioned_vits

# 检查 GPU 利用率
watch -n 1 nvidia-smi
```

**健康指标**：
- GPU 利用率：~90%+
- 训练速度：1.2-1.5 steps/sec
- loss 下降稳定（无 NaN/Inf）
- 每 5k 步自动保存 checkpoint

---

### 19.4 训练完成后验证

```bash
# 批量验证所有 checkpoint
bash scripts/batch_eval_all_checkpoints.sh

# 查看 10k 验证结果（关键门槛）
cat logs/eval_phi_leakage_step_10000.log | grep "判定"
cat logs/eval_pure_phi_step_10000.log | grep "判定"

# 查看 30k 最终结果
cat logs/eval_phi_leakage_step_30000.log | grep "判定"
cat logs/eval_pure_phi_step_30000.log | grep "判定"
```

---

## 20. Step / Epoch 严谨推导与换算

### 20.1 基础参数

```yaml
数据规模：
  地点数 N_loc = 243,968
  每地点季节数 = 4
  四季样本数 N_season = 975,872

训练配置：
  GPU 数 = 8
  per-GPU batch size = 64
  gradient accumulation = 2
  
计算：
  effective global batch = 8 × 64 × 2 = 1,024
```

---

### 20.2 Epoch 定义（两种口径）

#### 口径1：Dataloader Epoch（地点遍历）
- 定义：每个**地点**平均被采样一次
- 每次随机选择该地点的一个季节
- Steps/epoch = 243,968 / 1,024 = **238.25 steps**

#### 口径2：完整四季覆盖 Epoch（推荐用于论文）
- 定义：每个地点的**4个季节平均各被采样一次**
- 更符合"看过所有数据"的直觉
- Steps/epoch = 975,872 / 1,024 = **953 steps**

**论文中使用口径2**，因为：
1. 与文献对比时更公平（大家都说"N epochs"）
2. 更直观（1 epoch = 看过所有四季数据）
3. 避免混淆（dataloader epoch 容易被误解为"只看了 1/4 数据"）

---

### 20.3 关键里程碑换算表

| Optimizer Steps | Dataloader Epochs | **四季完整覆盖 Epochs** | 作用 |
|---:|---:|---:|---|
| 2,000 | 8.39 | **2.10** | 新模块热身完成 |
| 5,000 | 20.99 | **5.25** | 第一中间检查点 |
| 10,000 | 41.97 | **10.49** | **Go/No-Go 门槛** |
| 20,000 | 83.95 | **20.99** | 中段检查 |
| 30,000 | 125.92 | **31.48** | **推荐上限** |

---

### 20.4 为什么是 30k？（文献对比）

| 工作 | 预训练 epochs | 微调 epochs | 数据规模 | 备注 |
|---|---:|---:|---|---|
| MAE (He et al.) | 1600 | - | ImageNet-1K (1.28M) | 从零开始 |
| ViT (Dosovitskiy et al.) | 300 | - | ImageNet-21K (14M) | 从零开始 |
| **Stage1（本项目）** | **≈200** | - | SSL4EO (976k) | 从零开始，95k steps |
| **Stage1.5（本项目）** | - | **≈31** | SSL4EO (976k) | 续训，30k steps |

**推理**：
- Stage1.5 是**续训**，不是从零开始
- Encoder 已有 95k 步预训练（≈200 epochs）
- 只需额外 30-50 epochs 让新模块（FiLM, φ encoder, state projector）收敛
- 过多训练会破坏 Stage1 语义（即使有 Teacher anchor）

---

### 20.5 若 Batch Size 改变，如何重算？

**公式**：
$$
B_{eff} = N_{GPU} \times B_{micro} \times N_{accum}
$$

$$
\text{Steps/完整四季覆盖 epoch} = \frac{975,872}{B_{eff}}
$$

**示例**：

| 配置 | Effective Batch | Steps/Epoch | 30k 对应 Epochs |
|---|---:|---:|---:|
| 4 GPU × 64 × 2 | 512 | 1,906 | 15.74 |
| **8 GPU × 64 × 2** | **1,024** | **953** | **31.48** |
| 8 GPU × 128 × 2 | 2,048 | 476.5 | 62.96 |

**注意**：
- 任何 GPU 数、micro batch 或 accumulation 改动后，都必须重算
- 不能只复制"30k steps"，要确保"约 30 epochs"
- Effective batch 越大，收敛越快，但通信开销也越大

---

## 21. 约束条件与护栏完整清单

### 21.1 设计约束（7 项护栏）

| # | 护栏 | 实现位置 | 验证方式 |
|:---:|---|---|---|
| 1 | **φ 只含纯成像因素** | `PureImagingConditionEncoder` | 代码审查 ✓ |
| 2 | **零初始化 FiLM 后部层** | `FiLMModulation.__init__` | 权重加载验证 ✓ |
| 3 | **Decoder 独立 FiLM** | `DecoderFiLM` | 参数不共享 ✓ |
| 4 | **删除 shuffle-φ 约束** | `stage1_5_state.py` | 无相关代码 ✓ |
| 5 | **近同期 state 一致性** | `CrossModalVICRegLoss` | ≤7天 门控 ✓ |
| 6 | **10% φ-dropout** | `condition_dropout=0.10` | 配置验证 ✓ |
| 7 | **泄漏 probe + 状态保留** | `eval/eval_phi_leakage_probe.py` | 10k 时执行 |

---

### 21.2 训练约束

- **不覆盖 Stage1 权重**：Stage1.5 保存到独立目录
- **冻结策略严格执行**：2k/10k 自动解冻
- **梯度累积必须启用**：保证 effective batch = 1024
- **bf16 混合精度**：H200 必须使用 bf16
- **FSDP2 分布式**：8 卡训练必须用 FSDP2
- **Checkpoint 定期保存**：每 5k 一次，防止意外中断

---

### 21.3 数据约束

- **近同期配对**：≤7 天作为主方案，≤14 天只做消融
- **云 mask 必须使用**：S2 排除 cloud/shadow/invalid
- **φ v3 几何字段**：必须使用 S1 几何修正版本
- **单季采样**：每个样本只选一个季节，不做时序聚合
- **normalize=True**：图像必须归一化到 [0, 1]

---

### 21.4 损失函数约束

- **MAE 权重固定为 1.0**：重建是基础任务
- **Alignment 逐步增加**：0.05 → 0.20（0-10k 线性）
- **Nuisance 逐步增加**：0.00 → 0.02（0-10k 线性）
- **Anchor 固定为 0.10**：防止语义遗忘
- **VICReg 三项同时启用**：invariance/variance/covariance 缺一不可

---

### 21.5 评估约束

- **10k 门槛必须评估**：8 项验证（6 项原有 + 2 项新增）
- **任一核心指标失败 → 停训分析**：不盲跑 30k
- **EuroSAT 下降 ≤1%**：状态保留底线
- **S1↔S2 检索优于 Stage1**：成像解耦底线
- **φ probe 准确率下降 >20%**：泄漏约束底线
- **无坍塌**：方差/协方差/有效秩正常

---


## 22. 文献对齐与理论空白

### 22.1 有明确文献支撑的设计

| 核心设计 | 文献支撑 | 对齐度 | 备注 |
|---|---|:---:|---|
| **双端条件化** | CVAE (Sohn et al., NeurIPS 2015)<br>SPADE (Park et al., CVPR 2019) | ✅ 强 | 条件推断 + 条件生成 |
| **FiLM 注入** | FiLM (Perez et al., AAAI 2018)<br>DOFA (CVPR 2024) | ✅ 强 | 零初始化，后部层 |
| **近同期跨模态对齐** | CROMA (NeurIPS 2023)<br>Panopticon (CVPRW 2025) | ✅ 强 | 同地点跨传感器 |
| **VICReg 防坍塌** | VICReg (Bardes et al., ICLR 2022) | ✅ 强 | 3 项损失防坍塌 |
| **零初始化续训** | LoRA (Hu et al., ICLR 2022)<br>Adapter tuning 最佳实践 | ✅ 强 | Identity 起点 |
| **状态与观测分离** | DeCUR (ECCV 2024)<br>LEPA (arXiv 2026) | ✅ 强 | 公共状态 vs 模态独有 |
| **时间阈值 ≤7 天** | Sentinel-2 重访周期 5 天<br>Panopticon 隐含近同期 | ✅ 中 | 70-72% 覆盖率合理 |

---

### 22.2 理论空白与风险缓解

#### 空白1：φ 泄漏 cross-covariance 正则（原创设计）

**当前做法**：
```python
# 直接正则化 state 与原始 φ 字段的线性相关性
nuisance_features = [sin(sun), orbit_onehot, satellite_onehot, ...]
cross_cov = (state - state.mean(0)).T @ (nuisance - nuisance.mean(0)) / (B - 1)
loss_nuisance = cross_cov.square().mean()
```

**文献对比**：
- **DeCUR (ECCV 2024)**：用**对抗性分类器**测 nuisance 泄漏
- **DOFA (CVPR 2024)**：用**线性 probe**测波长/传感器可预测性
- **本方案**：直接正则化 cross-covariance（更高效但理论保证弱）

**理论依据**（可补充到论文）：
- **Invariant Risk Minimization** (Arjovsky et al., ICML 2020)：线性独立性是因果解耦的必要条件
- **Canonical Correlation Analysis (CCA)**：最小化 CCA 系数 = 最小化线性相关性

**风险**：
- ✅ **优势**：计算高效，梯度稳定，无需额外判别器
- ⚠️ **风险**：线性独立 ≠ 非线性独立；复杂非线性变换后仍可能泄漏
- 💡 **缓解**：10k 时补充**非线性 MLP probe**验证有效性

**论文写作建议**：
```markdown
### 3.2.3 Nuisance Leakage Constraint

Unlike adversarial approaches (DeCUR), we directly regularize the 
cross-covariance between state embeddings and raw acquisition fields:

$$\mathcal{L}_{\text{nuisance}} = \|\text{Cov}(z_{\text{state}}, \phi_{\text{raw}})\|_F^2$$

This is computationally efficient and provides a necessary (though not 
sufficient) condition for independence. To verify that non-linear leakage 
is also prevented, we train a 3-layer MLP probe (§4.2.2) and confirm 
that acquisition field predictability drops significantly (Table 2).
```

---

#### 空白2：Pure φ 字段选择（经验驱动）

**当前做法**：
- **包含**：sun_elevation, orbit_direction, relative_orbit, satellite
- **排除**：lat/lon, season, day_of_year, DEM

**文献对比**：
- **Presto (NeurIPS 2023)**：包含 lat/lon/time 作为条件
- **DOFA (CVPR 2024)**：包含波长/传感器，不排除位置
- **本方案**：显式排除可能包含状态信息的字段

**理论依据**（可补充到论文）：
- **Spurious Correlation**：lat/lon → 气候带 → 植被类型（非因果）
- **InfoMax 原则**：若 I(lat; NDVI | state) > 0，则 lat 包含状态信息
- **经验假设**：纯成像因素（太阳角/轨道）不应包含地表状态

**风险**：
- ✅ **优势**：避免模型走捷径（用位置预测状态）
- ⚠️ **风险**：缺少定量证据证明这些确实是捷径
- 💡 **缓解**：10k 时补充**lat/lon/season probe**验证假设

**论文写作建议**：
```markdown
### 3.2.1 Pure Acquisition Conditioning

To prevent the encoder from learning geographic or seasonal shortcuts, 
we explicitly exclude lat/lon, season, and DEM from φ, retaining only 
acquisition geometry (solar elevation, orbit parameters). We validate 
this design by training linear probes (§4.2.3) and confirming that 
state embeddings cannot predict these excluded fields (Table 3).
```

---

### 22.3 补充文献建议

在 25 号文档（现 Stage1.5_完整训练执行方案_FINAL.md）§14 中补充：

| 工作 | 会议/期刊 | 年份 | 本文引用点 |
|---|---|---|---|
| [Invariant Risk Min](https://arxiv.org/abs/1907.02893) | ICML | 2020 | 线性独立性作为因果解耦必要条件 |
| [CCA Analysis](https://www.jstor.org/stable/2333955) | Biometrika | 1936 | Cross-covariance 正则的理论基础 |

---

## 23. 常见问题 FAQ

### Q1：为什么不用对抗训练去除 φ 泄漏？

**A**：
- 对抗训练（discriminator）更强但**计算开销大**（需额外网络 + 交替优化）
- Cross-covariance 正则是**必要条件**，先用简单方法
- 若 10k probe 发现非线性泄漏严重，再加对抗训练

**权衡**：
- Cross-cov：快速、稳定，但只约束线性
- 对抗训练：更强，但慢、难调参、可能不稳定

---

### Q2：为什么 Season 准确率 30-40% 不算失败？

**A**：
- **真实物候**：春天开花、夏天茂盛、秋天落叶、冬天枯萎
- 这些是**真实状态变化**，不是捷径
- 若 state 包含"当前是生长旺季"→ 合理
- 若 state 包含"当前是6月"→ 捷径（但 Season 是季节级别，不是月份）

**判定**：
- Season ≈25%（随机）→ 理想（完全无季节信息）
- Season 25-40% → 可接受（可能是真实物候）
- Season >50% → 失败（明显走捷径）

---

### Q3：为什么近同期配对只用 ≤7 天？

**A**：
- **Sentinel-2 重访周期**：5 天
- **真实变化发生**：洪水/火灾/耕作 可能在 7-14 天内发生
- **70-72% 覆盖率**：足够建立跨模态一致性

**消融对照**：
- ≤14 天：88-90% 覆盖率，但可能引入真实变化
- 用于消融实验，证明 7 天阈值的必要性

---

### Q4：10k 验证失败怎么办？

**A**：
- **不要盲目继续 30k**
- 分析失败原因：
  - φ 泄漏？→ 提高 nuisance_loss 权重或加对抗训练
  - Pure φ 失败？→ 讨论是否可接受或加额外约束
  - 状态坍塌？→ 提高 variance_weight
  - 语义遗忘？→ 提高 anchor_weight
- 从 10k checkpoint 恢复，调整后继续训练

---

### Q5：可以用更少的 GPU 训练吗？

**A**：可以，但需要调整配置保持 effective batch ≈ 1024

**示例（4 GPU）**：
```yaml
# 原配置（8 GPU）
batch_size: 64
gradient_accumulation_steps: 2
# effective batch = 8 × 64 × 2 = 1024

# 新配置（4 GPU）
batch_size: 64
gradient_accumulation_steps: 4
# effective batch = 4 × 64 × 4 = 1024
```

**注意**：
- Effective batch 保持不变，训练动力学相同
- 但梯度累积步数增加 → 训练速度变慢（wall-clock time 增加）

---

### Q6：训练中途中断了怎么办？

**A**：从最近的 checkpoint 恢复

```bash
# 找到最近的 checkpoint
ls -lt checkpoints/stage1_5_dual_conditioned_vits/ | head -5

# 从 checkpoint 恢复训练
python train/train_stage1_5_dual_conditioned.py \
  --config configs/train/stage1_5_dual_conditioned_vits.yaml \
  --resume-from checkpoints/stage1_5_dual_conditioned_vits/checkpoint_step_15000.pt \
  --max-steps 30000  # 继续到 30k
```

**自动恢复**：
- 若训练脚本支持，可以自动检测最新 checkpoint 并恢复

---

### Q7：如何确认训练没有 bug？

**A**：监控以下指标

**正常现象**：
- ✅ Loss 稳定下降（无 NaN/Inf）
- ✅ S1/S2 重建 loss 平衡（不出现一个模态完全被忽略）
- ✅ Xmodal loss 有效下降（≤7天样本比例 ≈70%）
- ✅ GPU 利用率稳定（~90%+）
- ✅ 每 5k 步自动保存 checkpoint

**异常现象与处理**：
- ❌ Loss 突然爆炸（NaN）→ 降低学习率或检查数据
- ❌ S1 loss >> S2 loss（或反之）→ 检查 modality 采样是否均衡
- ❌ Xmodal loss 不下降 → 检查 pair_max_days 是否太大
- ❌ GPU 利用率波动 → 检查数据加载（可能 I/O 瓶颈）

---

## 24. 论文写作策略

### 24.1 AAAI 篇幅分配（7 页主文）

```
§1 Introduction (1 页)
  - 问题：遥感观测受成像条件污染
  - 挑战：去除 φ 又保留真实变化
  - 贡献：双端条件化 + Pure φ + 近同期对齐

§2 Related Work (1 页)
  - 遥感预训练（MAE/ViT/Prithvi）
  - 跨模态对齐（CROMA/Panopticon）
  - 条件生成（CVAE/SPADE/FiLM）

§3 Method (2.5 页)
  §3.1 Stage 1: 简述（引用已有 MAE 验证）
  §3.2 Stage 1.5: 详细写（本文核心）
    - 双端条件化设计（0.5 页）
    - Pure φ 字段选择（0.3 页）
    - 损失函数（0.5 页）
      - MAE 重建
      - VICReg 跨模态对齐
      - Cross-cov φ 泄漏约束
      - Teacher anchor
  §3.3 Stage 2: 简述（动力学模块）

§4 Experiments (2 页)
  §4.1 Setup（0.3 页）
  §4.2 Stage 1.5 核心验证（1.2 页）
    - Table 1: 状态保留（EuroSAT, LULC, NDVI）
    - Table 2: φ 泄漏验证（线性 + 非线性 probe）
    - Table 3: Pure φ 验证（lat/lon/season probe）
    - Figure 2: S1/S2 t-SNE 可视化
  §4.3 End-to-End 结果（0.5 页）
    - Table 4: 下游任务（洪水/变化检测）

§5 Ablation (0.3 页)
  - Table 5: 关键消融（只放 2-3 个最重要的）
    1. Dual-ended vs Encoder-only vs Decoder-only
    2. Pure φ vs Full φ
    3. ≤7 天 vs ≤14 天

§6 Conclusion (0.2 页)

References (不限页)
```

---

### 24.2 附录内容（不限页）

```
Appendix A: 完整消融实验表
  - 所有 9 个消融的完整结果
  - 不同超参数的敏感性分析

Appendix B: 详细 φ 泄漏分析
  - 每个 φ 字段的 probe 结果
  - t-SNE 可视化（按 φ 着色）
  - 训练曲线（5k/10k/30k 对比）

Appendix C: Pure φ 字段完整说明
  - v3 几何字段列表
  - 每个字段的统计分布
  - 为什么排除 lat/lon/season/DEM

Appendix D: 更多下游任务
  - LULC 分类详细结果
  - Crop type 分类
  - 变化检测多个数据集

Appendix E: 训练细节
  - 完整超参数表
  - 学习率曲线
  - Loss 曲线（各项分解）
  - GPU 内存占用分析

Appendix F: 失败案例分析
  - 哪些样本 φ 泄漏严重
  - 哪些地区 S1/S2 对齐困难
  - 极端天气（台风/洪水）表现
```

---

### 24.3 主文验证写作示例

**紧凑版（主文，0.3 页）**：

```markdown
### 4.2 φ Leakage and State Preservation

We validate that our dual-ended conditioning removes acquisition 
biases while preserving semantic content. Table 2 shows Stage 1.5 
significantly reduces φ predictability (non-linear 3-layer MLP probe) 
compared to Stage 1, with orbit accuracy dropping from 87.3% to 56.2% 
(approaching random 50%), while maintaining EuroSAT performance 
(93.4% vs 94.1%, <1% drop).

| Method | Orbit Acc↓ | Sun MAE↓ | EuroSAT↑ |
|--------|------------|----------|----------|
| Stage 1 | 87.3% | 8.2° | 94.1% |
| Stage 1.5 | 56.2% | 14.7° | 93.4% |
| Random | 50.0% | ~20° | - |

To verify that lat/lon/season are successfully excluded, we train 
linear probes and confirm low predictability (Season 28.3% ≈ random 
25%, Lat/Lon MAE +108%, see Appendix B for details).
```

---

## 25. 最终检查清单

### 25.1 代码完整性

- [x] 训练脚本：`train/train_stage1_5_dual_conditioned.py`
- [x] 配置文件：`configs/train/stage1_5_dual_conditioned_vits.yaml`
- [x] 启动脚本：`scripts/train_stage1_5_dual_conditioned_fsdp8.sh`
- [x] CPU 测试：`tests/test_stage1_5_dual_conditioned.py`（已通过）
- [x] φ 泄漏 probe：`eval/eval_phi_leakage_probe.py`
- [x] Pure φ probe：`eval/eval_pure_phi_assumption.py`
- [x] 批量评估脚本：`scripts/batch_eval_all_checkpoints.sh`
- [x] 所有模型模块：encoder/decoder/losses/projector

---

### 25.2 数据完整性

- [x] Stage1 95k checkpoint 存在
- [x] φ v2 数据（phi_processed）就绪
- [x] φ v3 几何数据（phi_processed_v3_s1geom）就绪
- [x] 训练集 split 正确
- [x] 验证集 split 正确

---

### 25.3 文档完整性

- [x] 权威决策文档：`Stage1.5_完整训练执行方案_FINAL.md`（本文档）
- [x] 快速启动指南：`README_Stage1.5_Training.md`
- [x] 就绪报告：`STAGE1.5_READY.md`
- [x] 审查报告：`STAGE1.5_IMPLEMENTATION_AUDIT.md`
- [x] 审查总结：`STAGE1.5_AUDIT_SUMMARY.md`

---

### 25.4 理论完整性

- [x] 双端条件化理论依据
- [x] Pure φ 字段选择理由
- [x] Cross-cov 正则理论基础
- [x] 近同期对齐时间阈值
- [x] Step/Epoch 严谨换算
- [x] 文献对齐分析
- [x] 理论空白与缓解方案

---

### 25.5 验证完整性

- [x] 7 项护栏实现验证
- [x] CPU 测试通过
- [x] 真实权重加载验证
- [x] 单卡 smoke test 通过
- [x] 评估脚本编写完成
- [ ] 10k 验证（训练后执行）
- [ ] 30k 最终验证（训练后执行）

---

## 26. 启动命令（最终版）

```bash
# ===== 第1步：环境检查 =====
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

# 检查 Stage1 checkpoint
test -f checkpoints/stage1_vits_dual_staged/checkpoint_step_95000.pt && echo "✓ Stage1 OK" || echo "✗ Stage1 缺失"

# 检查 φ 数据
test -d /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed && echo "✓ φ v2 OK"
test -d /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed_v3_s1geom && echo "✓ φ v3 OK"

# ===== 第2步：启动训练（全量 30k） =====
bash scripts/train_stage1_5_dual_conditioned_fsdp8.sh

# 训练时长：约 6-7 小时（8×H200）
# 自动保存：5k/10k/15k/20k/25k/30k

# ===== 第3步：批量验证（训练完成后） =====
bash scripts/batch_eval_all_checkpoints.sh

# 验证时长：约 2-3 小时/checkpoint
# 可并行：多 GPU 同时验证不同 checkpoint

# ===== 第4步：查看关键结果 =====
# 10k 验证（Go/No-Go 门槛）
cat logs/eval_phi_leakage_step_10000.log | grep "判定"
cat logs/eval_pure_phi_step_10000.log | grep "判定"

# 30k 最终验证
cat logs/eval_phi_leakage_step_30000.log | grep "判定"
cat logs/eval_pure_phi_step_30000.log | grep "判定"

# ===== 第5步：分析与决策 =====
# 若 10k/30k 全部通过 → 论文写作，报告 30k 结果
# 若 10k 失败 → 分析原因，调整方案，从 10k 恢复训练
# 若 30k 失败但 10k 通过 → 使用 10k checkpoint（可能已过拟合）
```

---

## 27. 总结：一页速查

### 核心设计

$$
s_t = E(X_t, \phi_t), \quad \hat{X}_t = R(s_t, \phi_t)
$$

- **双端条件化**：Encoder + Decoder 均接收 φ
- **Pure φ**：只保留纯成像因素（sun/orbit），排除 lat/lon/season/DEM
- **近同期对齐**：≤7 天 S1/S2，VICReg 防坍塌
- **Zero-init FiLM**：后 4 层，identity 起点

### 训练参数

- **30k steps** ≈ **31.48 完整四季覆盖 epochs**
- Effective batch = 1,024（8 GPU × 64 × 2 accum）
- 训练时长：6-7 小时（8×H200）
- 关键门槛：10k（Go/No-Go 决策点）

### 验证要求

**10k 必须通过 8 项**：
1. EuroSAT/LULC ≤1% 下降
2. S1↔S2 检索优于 Stage1
3. **φ 泄漏 probe**：非线性准确率下降 >20%
4. 条件有效：correct > shuffled φ
5. 重建稳定：验证 MAE ≤5% 恶化
6. 无坍塌：方差/协方差正常
7. **Pure φ probe**：Season ≈25-40%
8. **Pure φ probe**：Lat/Lon MAE 显著升高

### 启动命令

```bash
bash scripts/train_stage1_5_dual_conditioned_fsdp8.sh  # 30k 全量训练
bash scripts/batch_eval_all_checkpoints.sh            # 事后验证
```

---

**文档版本**：v3.0 Final  
**最后更新**：2026-07-03 21:00  
**状态**：✅ 完整、可执行、包含所有关键信息  
**下一步**：启动训练 🚀

