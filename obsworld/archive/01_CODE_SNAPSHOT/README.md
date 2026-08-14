# WorldModel2026 — ObsWorld 第一阶段

> 遥感世界模型 ObsWorld：在 SSL4EO-S12-v1.1 上预训练观测编码器（Observation Encoder）

---

## 这是什么

**WorldModel2026** 是遥感世界模型 ObsWorld 的工程仓库。ObsWorld 的完整目标是把遥感图像看作"地表状态在某成像条件下的有偏观测"，进而建模：

```
历史遥感观测 + 成像条件 → 成像无关的地表状态
地表状态 + 外生驱动 + 地理先验 → 未来地表状态
未来地表状态 + 未来成像条件 → 未来遥感观测
```

本仓库当前只实现 **第一阶段（Stage 1）**：用 SSL4EO-S12-v1.1 数据集，通过 **MAE 掩码重建** 自监督预训练一个观测编码器。后续的状态动力学、观测解码、下游任务等留待 Stage 2/3/4。

> 📖 **想快速看懂全部代码，请直接读 [框架详细解析.md](框架详细解析.md)** —— 那里详尽讲解了当前模式、S2RGB 切换、FSDP 架构、关键代码位置、训练命令等。本 README 只做概览。

---

## 当前状态一览

| 项目 | 状态 |
|---|---|
| 数据可读性验证 | ✅ SSL4EO-S12-v1.1 真实可流式读取 |
| 数据流水线 | ✅ WebDataset + zarr.zip 解析 |
| 模型 | ✅ TinyViT 编码器 + 轻量解码器（约 4.87M 参数） |
| 单卡训练 | ✅ 完整闭环跑通 |
| 多卡 FSDP（FSDP2） | ✅ 1/2/3/4 卡实测真分片（参数 DTensor 化） |
| checkpoint 卡数解耦 | ✅ 多卡训练的可在单卡/CPU 加载 |
| 当前输入模态 | **S2L2A**（12 波段），可切 S2RGB |

**硬件环境**：8 × NVIDIA H200（每卡 143GB），PyTorch 2.12.0 + CUDA 13.0。
（注：当前 tiny 模型单卡足够，FSDP 是为验证多卡流程、给后续大模型铺路。）

---

## 快速开始

### 1. 激活环境

```bash
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
```

> 环境名为 `WorldModel`（conda），依赖见 [requirements.txt](requirements.txt)：
> torch、zarr(2.x)、webdataset、einops、pyyaml、tensorboard、tqdm。

### 2. 检查数据

```bash
python scripts/inspect_ssl4eo.py \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1
```

### 3. 单卡训练

```bash
bash scripts/smoke_train_single.sh                      # 10 步快速验证
# 或正式训练：
python train/train_stage1_ssl4eo.py \
  --config configs/train/stage1_single.yaml --max-steps 5000
```

### 4. 多卡 FSDP 训练（含 3-4 卡）

```bash
bash scripts/train_fsdp_multi.sh 3          # 3 卡
bash scripts/train_fsdp_multi.sh 4 5000     # 4 卡，5000 步
GPUS=0,1,2 bash scripts/train_fsdp_multi.sh 3   # 指定具体 GPU
```

### 5. 切换到 S2RGB 模式

改配置文件（`configs/train/stage1_single.yaml` 或 `stage1_fsdp.yaml`）两处：

```yaml
data:
  modality: S2RGB        # S2L2A → S2RGB
model:
  encoder: { in_channels: 3 }    # 12 → 3
  decoder: { out_channels: 3 }   # 12 → 3
```

---

## 目录结构

```
WorldModel2026/
├── 框架详细解析.md          ★ 完整代码解析（强烈建议先读）
├── README.md                本文件
├── STAGE1_DELIVERY_REPORT.md 交付报告
├── FINAL_SUMMARY.md         工作总结
├── requirements.txt
├── configs/                 配置（改超参数只看这里）
│   ├── data/ssl4eo.yaml
│   ├── model/stage1_tiny_encoder.yaml
│   └── train/{stage1_single,stage1_fsdp}.yaml
├── data/
│   ├── datasets/ssl4eo.py           数据读取 + zarr 解析
│   └── datamodules/ssl4eo_dm.py     DataModule
├── models/
│   ├── encoders/tiny_vit_encoder.py ViT 编码器 + 随机掩码
│   ├── decoders/light_decoder.py    重建解码器
│   └── losses/reconstruction.py     masked 重建损失
├── train/
│   ├── train_stage1_ssl4eo.py       训练主流程（FSDP 接入）
│   └── fsdp_utils.py                FSDP 分布式工具
├── scripts/                 探查 / 冒烟测试 / 启动脚本
├── checkpoints/             模型 checkpoint
└── logs/                    TensorBoard 日志
```

---

## 数据集：SSL4EO-S12-v1.1

- **路径**：`/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1`
- **格式**：WebDataset（tar shard），每样本为 `.zarr.zip`
- **规模**：train 每模态 477 shard，val 每模态 5 shard
- **模态与形状**（每样本 4 个季节、空间 264×264）：

| 模态 | bands 形状 | dtype | 说明 |
|---|---|---|---|
| S2L2A | `[4,12,264,264]` | int16 | Sentinel-2 L2A 12 波段（**当前默认**） |
| S2L1C | `[4,13,264,264]` | int16 | Sentinel-2 L1C 13 波段 |
| S2RGB | `[4,3,264,264]` | uint8 | RGB |
| S1GRD | `[4,2,264,264]` | float16 | Sentinel-1 SAR（VV/VH） |
| DEM | `[1,1,264,264]` | int16 | 高程（静态） |
| LULC | `[4,264,264]` | — | 土地覆盖 |
| NDVI | 4 时相 | — | 植被指数 |

每样本还含 `cloud_mask / time / 经纬度 / sample_id` 等元数据，作为 ObsWorld 成像条件 `phi` 的来源。

- GitHub：https://github.com/DLR-MF-DAS/SSL4EO-S12-v1.1

---

## 后续阶段（Stage 2+）

当前编码器训好后，按 ObsWorld 方案继续：

1. **状态空间** — 学习成像解耦的地表状态表征
2. **状态动力学** — 外生驱动 + 地理先验下预测未来状态
3. **条件观测解码** — 指定未来成像条件生成未来观测
4. **下游任务 + 世界模型能力评估** — 洪水/土地覆盖/建筑变化等

详见 [任务描述相关/](任务描述相关/) 下的完整方案文档。

---

最后更新：2026-06-15
