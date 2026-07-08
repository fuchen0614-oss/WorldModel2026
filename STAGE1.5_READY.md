# Stage1.5 双端条件化训练 - 就绪报告

**日期**：2026-07-03 19:42  
**状态**：✅ 所有验证通过，可启动 8 卡正式训练

---

## ✅ 已完成工作清单

### 1. 模型实现
- [x] ViT-S 384/12/6 backbone
- [x] Encoder 最后 4 层零初始化 FiLM（blocks 8–11）
- [x] Decoder 4 层独立零初始化 FiLM
- [x] Pure φ 编码器（仅纯成像因素：S2 太阳角 + S1 几何）
- [x] State projector：[B,N,384] → [B,N,256]
- [x] 移除 Encoder cross-attention（冗余参数）

### 2. 数据流
- [x] 单季 S1/S2 真实时间差配对
- [x] ≤7 天对齐门控（~70% 覆盖率）
- [x] S2 cloud/invalid 质量 mask
- [x] φ v3 字段接入（含 S1 几何修正）

### 3. 损失函数
- [x] MAE 重建损失（S1/S2 masked L1）
- [x] VICReg 跨模态状态一致性（invariance + variance + covariance）
- [x] φ 泄漏约束（state–φ cross-covariance 正则）
- [x] Stage1 Teacher anchor（冻结 95k，cosine anchor）

### 4. 训练策略
- [x] 三阶段冻结/解冻（2k / 10k / 30k）
- [x] 分层学习率（新模块 1e-4，旧模块 1e-5）
- [x] 梯度累积 + FSDP2（8 卡，effective batch=1024）
- [x] bf16 + gradient clipping=1.0

### 5. 验证
- [x] CPU 集成测试：5 项全过
  - `test_model_architecture`
  - `test_film_parameters`
  - `test_phi_encoder`
  - `test_state_projector`
  - `test_loss_computation`
- [x] 真实权重加载验证
  - Stage1 95k checkpoint 严格加载
  - missing keys: 0
  - unexpected keys: 16（16 个新 FiLM γ/β，符合预期）
- [x] 单卡 smoke test
  - 1 step 成功完成
  - 生成 checkpoint_step_1.pt（144.2 MB）
  - 包含 5 个模块完整权重 + optimizer state

### 6. 清理
- [x] 删除旧 Plan A 文件（4 个）
  - `train/train_stage1_5_film.py`
  - `tests/smoke_stage1_5_planA.py`
  - `scripts/train_stage1_5_planA_fsdp8.sh`
  - `configs/train/stage1_5_film.yaml`

### 7. 文档
- [x] 权威决策文档：[25_Stage1.5双端条件化训练策略与决策记录.md](任务描述相关/25_Stage1.5双端条件化训练策略与决策记录.md)
- [x] 快速启动指南：[README_Stage1.5_Training.md](README_Stage1.5_Training.md)
- [x] 本报告：STAGE1.5_READY.md

---

## 📁 唯一正式入口

### 配置
```
configs/train/stage1_5_dual_conditioned_vits.yaml
```

### 训练脚本
```
train/train_stage1_5_dual_conditioned.py
```

### 8 卡启动脚本
```
scripts/train_stage1_5_dual_conditioned_fsdp8.sh
```

### 测试
```
tests/test_stage1_5_dual_conditioned.py
```

---

## 🚀 启动命令

### 方式一：使用启动脚本（推荐）

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
bash scripts/train_stage1_5_dual_conditioned_fsdp8.sh
```

### 方式二：手动 torchrun

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

torchrun --nproc_per_node=8 --nnodes=1 \
  --rdzv_backend=c10d --rdzv_endpoint=localhost:0 \
  train/train_stage1_5_dual_conditioned.py \
  --config configs/train/stage1_5_dual_conditioned_vits.yaml
```

---

## 📊 训练规格

| 参数 | 值 |
|---|---:|
| GPU | 8 × H200 |
| Per-GPU batch | 64 |
| Gradient accumulation | 2 |
| **Effective global batch** | **1,024** |
| 总地点数 | 243,968 |
| 四季样本数 | 975,872 |
| **Steps/完整四季覆盖 epoch** | **953** |

### Step / Epoch 换算

| Optimizer steps | 四季完整覆盖 epochs | 里程碑 |
|---:|---:|---|
| 2,000 | 2.10 | 新模块热身完成，解冻 Encoder blocks 8–11 |
| 10,000 | 10.49 | **Go/No-Go 门槛**：必须通过 6 项核心评估 |
| 20,000 | 20.99 | 中段检查点 |
| 30,000 | 31.48 | **推荐上限** |

> ⚠️ **重要**：每个 step 同时前向 S1 和 S2，**绝不能再除以 2**。

---

## 🎯 10k Go/No-Go 门槛

在 10k 步必须**同时满足**以下 6 项，任一失败则停训分析：

1. ✓ **状态保留**：EuroSAT/LULC ≤1% 下降，NDVI/变化无显著下降
2. ✓ **成像解耦**：S1↔S2 检索/一致性优于 Stage1 与 MAE-continue
3. ✓ **φ 泄漏降低**：太阳角/轨道/平台 probe 相对 Stage1 明显下降
4. ✓ **条件有效**：正确 φ 重建优于 shuffled φ
5. ✓ **重建稳定**：验证 MAE ≤5% 恶化
6. ✓ **无坍塌**：state 方差、协方差、有效秩正常

---

## 📦 输出位置

### Checkpoint
```
checkpoints/stage1_5_dual_conditioned_vits/checkpoint_step_*.pt
```

### TensorBoard 日志
```
logs/stage1_5_dual_conditioned_vits/
```

### Checkpoint 结构
```python
{
  'global_step': int,
  'config': dict,
  'encoder_state_dict': 169 tensors,          # 含 16 个新 FiLM
  'phi_encoder_state_dict': 23 tensors,       # Pure φ encoder
  'decoder_state_dict': 144 tensors,          # 含独立 FiLM
  'state_projector_state_dict': 8 tensors,    # 384→256
  'optimizer_state_dict': dict
}
```

---

## 🔍 监控要点

### 训练过程
- [ ] 总 loss 下降稳定
- [ ] S1/S2 重建 loss 平衡（不出现一个模态完全被忽略）
- [ ] xmodal_loss（跨模态一致性）有效下降
- [ ] nuisance_loss（φ 泄漏）保持低位或下降
- [ ] anchor_loss（Stage1 语义保留）不异常升高
- [ ] GPU 利用率稳定（~90%+）
- [ ] 训练速度：约 1.2–1.5 steps/sec（8 卡 H200）

### 阶段转换
- [ ] 2k 步：自动解冻 Encoder blocks 8–11 + norm
- [ ] 10k 步：自动解冻完整 Encoder/Decoder
- [ ] xmodal_loss 权重：0→10k 线性升至 0.20
- [ ] nuisance_loss 权重：0→10k 线性升至 0.02

---

## 📚 参考文档

### 快速上手
- [README_Stage1.5_Training.md](README_Stage1.5_Training.md) - 完整使用指南（含常见问题）

### 权威决策
- [25_Stage1.5双端条件化训练策略与决策记录.md](任务描述相关/25_Stage1.5双端条件化训练策略与决策记录.md) - 完整理论、推理过程、文献综述

### 历史文档（仅供审计）
- [12_Stage1.5成像条件解耦实施方案](任务描述相关/)（早期 Encoder-only 方案）
- [18_现状评估与后续训练路线决策文档](任务描述相关/)（发现旧方案矛盾）
- [24_当前问题梳理与解决方案](任务描述相关/)（最终双端条件化决策起点）

---

## ⚠️ 关键约束与边界

1. **Stage2 只允许消费 `state_tokens [B,N,256]`**，不得读取 φ embedding
2. 不把季节和物候当成成像误差（真实变化必须保留）
3. φ 主输入只保留纯采集因素（排除经纬度/季节/DEM 捷径）
4. 云作为重建质量 mask，不要求状态重建云形状
5. 旧 checkpoint 和历史任务文档保留不覆盖
6. 若 10k 门槛失败，必须停训分析，不盲跑 30k

---

## ✅ 验证摘要

```
CPU 集成测试：        5/5 通过
权重加载验证：        严格匹配（missing=0, unexpected=16 新 FiLM）
单卡 smoke test：     1 step 成功，checkpoint 完整
旧文件清理：          4 个 Plan A 文件已删除
文档完整性：          决策文档 + 使用指南 + 本报告

状态：✅ 就绪，可启动 8 卡正式训练
```

---

## 🎬 现在可以启动了！

```bash
# 复制粘贴即可
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
bash scripts/train_stage1_5_dual_conditioned_fsdp8.sh
```

**预期**：
- 前 2k 步：新模块热身，loss 快速下降
- 2k–10k 步：Encoder 后 4 层解冻，跨模态一致性逐步建立
- 10k 步：**关键评估点**，决定是否继续 30k

**祝训练顺利！** 🚀

---

*生成时间：2026-07-03 19:42*  
*验证状态：所有测试通过*  
*下一步：启动 8 卡训练*
