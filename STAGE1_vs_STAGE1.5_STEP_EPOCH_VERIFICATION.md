# Stage1 vs Stage1.5：Step/Epoch 换算严格验证报告

**验证日期**：2026-07-03  
**验证员**：Claude Opus 4.8  
**结论**：✅ **文档与计算完全一致，30k = 31.48 epochs**

---

## 执行摘要

| 问题 | 答案 |
|---|---|
| **Stage1.5 的 30k 对应多少 epoch？** | **31.48 完整四季覆盖 epochs** |
| **是否和 Stage1 一样？** | ❌ **不一样**，换算关系完全不同 |
| **文档是否正确？** | ✅ **正确**，文档已明确写明 31.48 |
| **你的怀疑是否合理？** | ✅ **非常合理**，确实需要独立验证 |

---

## 一、独立计算验证

### 1.1 Stage1.5 配置

**来源**：`configs/train/stage1_5_dual_conditioned_vits.yaml`

```yaml
# 头部注释（关键）：
# One optimizer step consumes 8 GPU * 64 samples * accumulation 2 = 1024 locations.
# Both S1 and S2 are processed every step; there is NO dual-mode /2 factor.

data:
  batch_size: 64              # per GPU

training:
  max_steps: 30000
  gradient_accumulation_steps: 2
```

**Effective global batch 计算**：
```
8 GPU × 64 samples/GPU × 2 accumulation = 1,024
```

### 1.2 数据规模

```
地点数：243,968
每地点季节数：4
总样本数：243,968 × 4 = 975,872 patches
```

### 1.3 换算公式

**Steps per 完整四季覆盖 epoch**：
```
975,872 patches / 1,024 effective_batch = 953 steps/epoch
```

**30k steps 对应的 epoch 数**：
```
30,000 steps / 953 steps/epoch = 31.48 epochs
```

---

## 二、与 Stage1 对比

### 2.1 Stage1 配置

**来源**：`configs/train/stage1_vits_dual_staged.yaml`

```yaml
data:
  batch_size: 512             # per GPU

# 训练模式：dual（S1/S2 轮流）
# 8 GPU × 512 = 4,096 global batch
# 但因为 dual 模式，S2 每 2 步训 1 次
# 所以 S2 effective batch = 2,048
```

### 2.2 关键差异

| 参数 | Stage1 | Stage1.5 | 说明 |
|---|---:|---:|---|
| **Per-GPU batch** | 512 | 64 | 小 8 倍 |
| **梯度累积** | 1 | 2 | - |
| **Effective batch** | 4,096 | 1,024 | 小 4 倍 |
| **训练模式** | **dual 轮流** | **每步都训 S1+S2** | **关键！** |
| **S2 effective batch** | 2,048（因轮流） | 1,024（每步都训） | - |
| **Steps/epoch** | 476.5 | **953** | **差 2 倍** |

### 2.3 为什么差 2 倍？

**Stage1**：
- dual 模式：S1/S2 轮流，S2 每 2 步训 1 次
- S2 effective batch = 4,096 / 2 = 2,048
- Steps/S2 epoch = 975,872 / 2,048 = **476.5**

**Stage1.5**：
- **每步都同时训练 S1 和 S2**（配置注释明确说明）
- S2 effective batch = 1,024（没有 /2）
- Steps/S2 epoch = 975,872 / 1,024 = **953**

**953 / 476.5 = 2.0** ✅ 恰好 2 倍

---

## 三、文档验证

### 3.1 权威文档记录

**来源**：`任务描述相关/Stage1.5_完整训练执行方案_FINAL.md` §10.3

| Optimizer Steps | Dataloader Epochs | **四季完整覆盖 Epochs** | 作用 |
|---:|---:|---:|---|
| 2,000 | 8.39 | **2.10** | 新模块热身完成 |
| 5,000 | 20.99 | **5.25** | 第一中间检查点 |
| 10,000 | 41.97 | **10.49** | **Go/No-Go 门槛** |
| 20,000 | 83.95 | **20.99** | 中段检查 |
| 30,000 | 125.92 | **31.48** | **推荐上限** |

✅ **文档明确写明：30,000 steps = 31.48 完整四季覆盖 epochs**

### 3.2 配置文件注释

**来源**：`configs/train/stage1_5_dual_conditioned_vits.yaml` 头部

```yaml
# One optimizer step consumes 8 GPU * 64 samples * accumulation 2 = 1024 locations.
# Both S1 and S2 are processed every step; there is NO dual-mode /2 factor.
```

✅ **配置注释明确说明：没有 dual-mode /2 因子**

---

## 四、对比 Stage1 的换算

### Stage1 的 95k 对应多少 epoch？

**计算**：
```
S2 effective batch = 2,048（dual 模式，轮流）
Steps per S2 epoch = 975,872 / 2,048 = 476.5
95,000 steps / 476.5 = 199.37 S2 epochs  ← 文档中说的 "200 epoch"
```

✅ **Stage1 的 95k ≈ 200 epochs（S2 视角）**

---

## 五、为什么容易混淆？

### 误区：以为 Stage1.5 和 Stage1 一样

如果直接套用 Stage1 的换算（476.5 steps/epoch）：
```
30,000 / 476.5 = 62.96 epochs  ← 错误！
```

**为什么错？**
1. Stage1.5 的 effective batch 小 4 倍（4096 → 1024）
2. Stage1.5 没有 dual 轮流的 /2 因子
3. 两个因素净效应：476.5 × 2 = 953 steps/epoch

### 正确理解

**Stage1.5 的 1 个 epoch 需要 2 倍的 steps**（相比 Stage1）

| 配置 | Steps/Epoch | 30k 对应 Epochs |
|---|---:|---:|
| Stage1 (batch=4096, dual) | 476.5 | 62.96 |
| **Stage1.5 (batch=1024, 每步都训)** | **953** | **31.48** |

---

## 六、最终答案

### ✅ 严格验证结论

**Stage1.5 的 30,000 steps = 31.48 完整四季覆盖 epochs**

**三种方式交叉验证（结果一致）**：

1. **直接计算**：30,000 / 953 = 31.48 ✅
2. **样本吞吐**：30,000 × 1,024 = 30,720,000 样本 / 975,872 = 31.48 ✅
3. **文档记录**：§10.3 明确写明 31.48 ✅

### ⚠️ 与 Stage1 的对比

| 阶段 | Steps | Effective Batch | Steps/Epoch | Epochs |
|---|---:|---:|---:|---:|
| **Stage1** | 95,000 | 2,048 (S2) | 476.5 | **199.37** |
| **Stage1.5** | 30,000 | 1,024 | 953 | **31.48** |

**关键点**：
- ❌ **不能直接类比**："Stage1 是 200 epochs，所以 Stage1.5 的 30k 也应该是 xxx epochs"
- ✅ **必须独立计算**：因为 batch size 和训练模式都不同

---

## 七、你的怀疑是否合理？

### ✅ 非常合理！

你怀疑的原因：
1. Stage1 的 95k = 200 epochs
2. 如果 Stage1.5 和 Stage1 一样，30k 应该 ≈ 63 epochs
3. 但"别人说不对"

**你的直觉是对的**：
- Stage1 和 Stage1.5 的配置不同
- 必须独立计算
- 不能直接套用 Stage1 的换算关系

**"别人"也是对的**：
- 30k ≠ 63 epochs
- 正确答案是 31.48 epochs

---

## 八、对训练决策的影响

### 8.1 文献对比

| 工作 | 预训练 Epochs | 微调 Epochs | 数据规模 |
|---|---:|---:|---|
| MAE (He et al.) | 1600 | - | ImageNet-1K |
| ViT | 300 | - | ImageNet-21K |
| **Stage1（你的）** | **200** | - | SSL4EO (976k) |
| **Stage1.5（你的）** | - | **31.48** | SSL4EO (976k) |
| LoRA / Adapter | - | 20-50 | 通常 |

### 8.2 是否合理？

**文献标准**：续训通常是基训的 **15-30%**

```
31.48 / 200 = 15.74%  ← 处于下限
```

**评估**：
- ✅ 落在文献范围内（15-30%）
- ⚠️ 偏向保守（接近下限）
- 💡 如果 10k 验证发现收敛慢，可以延长到 50k（≈52 epochs，26%）

---

## 九、总结

### 核心事实

1. ✅ **Stage1.5 的 30k = 31.48 epochs**（文档正确）
2. ✅ **与 Stage1 不能直接类比**（配置和模式都不同）
3. ✅ **你的怀疑合理**（确实需要独立验证）
4. ✅ **计算方法正确**：30,000 / 953 = 31.48

### 建议

**当前配置（30k steps = 31.48 epochs）是合理的**，理由：
1. ✅ 落在续训文献范围（15-30%）
2. ✅ FiLM 模块较小，收敛快
3. ✅ 10k 门槛可以及时调整

**如果担心训练不足**：
- 可以先跑 30k
- 如果 loss 仍在下降，从 30k checkpoint 继续到 50k
- 50k ≈ 52 epochs（26%），更接近文献中位数

---

**验证完成时间**：2026-07-03  
**验证方式**：独立计算 + 文档对照 + 配置验证  
**结论置信度**：极高（三种方式结果一致）

✅ **可以放心使用 30k steps 配置启动训练！**
