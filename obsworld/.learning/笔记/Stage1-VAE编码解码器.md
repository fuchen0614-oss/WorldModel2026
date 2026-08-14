# Stage1: VAE 编码器-解码器 学习笔记

> **学习日期**: [待填写]
> **状态**: 📝 模板 - 等待学习后填充

---

## 模块概览

### 在系统中的位置
Stage1 是 WorldModel2026 的第一阶段训练,负责将高维的遥感图像压缩成低维的 latent tokens,为后续的时序建模(Stage2)提供高效的表示空间。

### 核心作用
- 图像压缩: 将 512×512×10 的 Sentinel-2 图像编码成紧凑的 token 序列
- 特征学习: 学习对遥感任务有意义的表示(通过重建任务验证)
- 解耦准备: 为 Stage1.5 的成像条件解耦打下基础

---

## 代码结构

### 编码器
**位置**: [models/encoders/multimodal_vit_encoder.py](../../models/encoders/multimodal_vit_encoder.py)

**关键代码段**:
```python
# [待学习时填写具体行号]
class MultimodalViTEncoder(nn.Module):
    def __init__(self, ...):
        # Patch embedding
        # Transformer blocks
        # Latent projection
```

**实现要点**:
- (待填写: patch size、hidden dim、attention heads 等超参数)
- (待填写: positional encoding 的处理)
- (待填写: 输出的 latent shape)

---

### 解码器
**位置**: [models/decoders/light_decoder.py](../../models/decoders/light_decoder.py)

**关键代码段**:
```python
# [待学习时填写具体行号]
class LightDecoder(nn.Module):
    # 从 latent tokens 重建原始图像
```

**实现要点**:
- (待填写: 上采样策略)
- (待填写: 解码器的轻量化设计)

---

### 损失函数
**位置**: [models/losses/reconstruction.py](../../models/losses/reconstruction.py)

**关键代码段**:
```python
# Reconstruction loss + KL divergence
loss = recon_loss + beta * kl_loss
```

**实现要点**:
- (待填写: 重建损失的具体形式,MSE? L1?)
- (待填写: KL loss 的计算方式)
- (待填写: beta 的取值和调整策略)

---

## 原理解析

### VAE (Variational Autoencoder) 基础
(待填写:学习后用自己的话总结)

**为什么用 VAE 而不是普通 AE?**
- (待填写)

**ELBO (Evidence Lower Bound) 推导**:
- (待填写: 可以手写公式或引用资源)

---

### ViT (Vision Transformer) 架构
(待填写:学习后总结)

**Patch Embedding 的作用**:
- (待填写)

**Self-Attention 在图像中的意义**:
- (待填写)

---

### Latent Space 的设计
**Token 数量**: (待填写: 比如 32×32 = 1024 tokens)
**每个 Token 的维度**: (待填写)

**为什么选这个压缩比?**
- (待填写: 权衡重建质量和压缩效率)

---

## 行业对比

### VAE vs GAN vs Diffusion
| 方法 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| VAE | (待填写) | (待填写) | (待填写) |
| GAN | (待填写) | (待填写) | (待填写) |
| Diffusion | (待填写) | (待填写) | (待填写) |

**WorldModel 为什么选 VAE?**
- (待填写: 学习后总结项目的具体考量)

---

### ViT vs CNN Encoder
(待填写: 对比 ResNet、ConvNext 等)

---

## 训练流程

### 训练脚本
**位置**: [train/train_stage1_dual.py](../../train/train_stage1_dual.py)

**关键步骤**:
1. 数据加载: (待填写)
2. 前向传播: (待填写)
3. 损失计算: (待填写)
4. 反向传播与优化: (待填写)
5. Checkpoint 保存: (待填写)

### 超参数配置
**位置**: [configs/xxx.yaml](../../configs/)

- Learning rate: (待填写)
- Batch size: (待填写)
- 训练步数: (待填写)
- 优化器: (待填写)
- LR scheduler: (待填写)

---

## 评估验证

### 线性探测 (Linear Probing)
**位置**: [eval/eval_linear_probe_eurosat.py](../../eval/eval_linear_probe_eurosat.py)

**原理**:
(待填写: 为什么线性探测能评估表示质量)

**结果**:
- 基线(ImageNet 预训练): 94.1%
- Stage1 模型: 69.57%
- 分析: (待填写: 为什么有差距,是否正常)

---

### 重建质量
**评估指标**:
- PSNR: (待填写)
- SSIM: (待填写)

**可视化**:
(待学习时截图或记录观察)

---

## 常见陷阱与最佳实践

### 训练不稳定
- **现象**: (待填写: 学习中遇到的问题)
- **原因**: (待填写)
- **解决方案**: (待填写)

### 显存优化
- Gradient checkpointing: (待填写)
- Mixed precision: (待填写)

### Checkpoint 管理
- 参考 [[stage1-checkpoint-interval-bug]]: (待填写: 总结这个坑)

---

## 实践验证

### 建议实验
1. **最小复现**: 在小数据集上跑通完整流程
2. **消融实验**: 去掉 KL loss,观察 latent space 的变化
3. **可视化**: t-SNE 可视化 latent space,看是否有聚类结构

### 我的实验记录
(待填写: 实际动手后的观察和结论)

---

## 疑问记录

(学习过程中的疑问链接到 [疑问记录.md](../疑问记录.md))

- [ ] (待填写)

---

## 相关资源

### 论文
- VAE 原论文: [链接]
- ViT 原论文: [链接]

### 教程
- (待填写: 学习过程中发现的有用资源)

### 项目文档
- [STAGE1_DELIVERY_REPORT.md](../../STAGE1_DELIVERY_REPORT.md)
- [[worldmodel-stage1-eurosat-eval]] (memory)

---

## 学习总结

(学完后用一段话总结核心收获)

**三个最重要的认知**:
1. (待填写)
2. (待填写)
3. (待填写)

**下一步学习方向**:
- 继续 Stage1.5 的条件生成
- 或者深入某个细节(比如 Transformer 架构)
