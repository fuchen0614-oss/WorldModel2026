# Stage 1 交付报告：ObsWorld 观测编码器训练框架

**项目**：WorldModel2026 — Stage 1 观测编码器预训练
**日期**：2026-06-15
**状态**：✅ 已完成并验证（单卡 + 多卡 FSDP 均跑通）

---

## 一、总览

在 `/csy-mix02/cog8/zjliu17/Agent/WorldModel2026` 下完成了一套可运行的 Stage 1 训练框架：从 SSL4EO-S12-v1.1 真实数据读取，到 TinyViT 观测编码器的 MAE 掩码重建预训练，再到 PyTorch FSDP2 多卡分布式训练，全流程打通并经过实测验证。

本框架对应原始需求提示词的全部目标：数据可读性验证、最小训练脚手架、单卡冒烟测试、FSDP 多卡冒烟测试。

---

## 二、创建的文件

```
WorldModel2026/
├── 框架详细解析.md              本框架完整中文解析（核心文档）
├── README.md                    项目概览
├── STAGE1_DELIVERY_REPORT.md    本报告
├── FINAL_SUMMARY.md             工作总结
├── requirements.txt             依赖清单
├── configs/
│   ├── data/ssl4eo.yaml         数据集配置
│   ├── model/stage1_tiny_encoder.yaml  模型配置
│   └── train/
│       ├── stage1_single.yaml   单卡训练配置（嵌套 model/data）
│       └── stage1_fsdp.yaml     多卡 FSDP 配置
├── data/
│   ├── datasets/ssl4eo.py       WebDataset + zarr.zip 解析
│   └── datamodules/ssl4eo_dm.py DataModule
├── models/
│   ├── encoders/tiny_vit_encoder.py  ViT 编码器 + 随机掩码
│   ├── decoders/light_decoder.py     轻量重建解码器
│   └── losses/reconstruction.py      masked 重建损失
├── train/
│   ├── train_stage1_ssl4eo.py   训练主流程（FSDP 接入）
│   └── fsdp_utils.py            FSDP 分布式工具
├── scripts/
│   ├── inspect_ssl4eo.py        数据集结构探查
│   ├── smoke_dataloader.py      dataloader 验证
│   ├── smoke_train_single.sh    单卡冒烟（10 步）
│   ├── smoke_train_fsdp.sh      2 卡 FSDP 冒烟
│   ├── smoke_train_fsdp4.sh     4 卡 FSDP 冒烟
│   └── train_fsdp_multi.sh      参数化多卡训练（3/4/N 卡）
├── checkpoints/                 模型 checkpoint
└── logs/                        TensorBoard 日志
```

所有 Python 文件的注释与文档字符串均为中文。

---

## 三、数据集是否可读：是

`scripts/inspect_ssl4eo.py` 实测确认 SSL4EO-S12-v1.1 可流式读取：

- **划分**：train（每模态 477 个 tar shard）、val（每模态 5 个）
- **模态**：S2L2A / S2L1C / S2RGB / S1GRD / DEM / LULC / NDVI 共 7 种
- **存储格式**：WebDataset tar shard，每样本为 `.zarr.zip`（zarr v2）
- **主数组**：`bands`，S2L2A 形状 `[4季, 12波段, 264, 264]`，dtype int16
- **元数据**：cloud_mask、time、sample_id、center_lat/lon、crs 等

`scripts/smoke_dataloader.py` 实测成功读取 1 个 batch：

```
image: [B, C, H, W]   归一化到 [0,1]
phi:   sensor / season / cloud_mask / lat / lon / time
field_mask: 字段有效性标记
```

---

## 四、模型架构

| 组件 | 实现 | 参数量 |
|---|---|---|
| 编码器 | TinyViTEncoder（PatchEmbed + 4 层 Transformer，embed_dim=256） | 4.01M |
| 解码器 | LightDecoder（2 层 Transformer，decoder_embed_dim=128） | 0.86M |
| **合计** | | **4.87M** |

- 输入：S2L2A 12 波段，256×256（从 264 中心裁剪）
- 训练目标：MAE 掩码重建，遮掩比例 75%，仅在被遮 patch 上算 MSE
- 优化器：AdamW（lr=1e-4），余弦学习率调度
- 精度：bf16 混合精度

---

## 五、单卡冒烟测试：通过 ✅

```bash
bash scripts/smoke_train_single.sh
```

结果：
- 运行模式：单卡
- 10 步训练完成，loss 正常（约 0.7–1.9，归一化后量级合理）
- forward → loss → backward → optimizer → checkpoint 全流程通过
- checkpoint 保存于 `checkpoints/checkpoint_step_10.pt`

---

## 六、FSDP 多卡冒烟测试：通过 ✅

使用 **FSDP2（fully_shard）**，实测 2 / 3 / 4 卡均真分片：

| 配置 | 参数分片为 DTensor | 每卡本地持有 |
|---|---|---|
| 2 卡 | ✅ True | 2.48M（≈1/2） |
| 3 卡 | ✅ True | 1.70M（≈1/3） |
| 4 卡 | ✅ True | 1.29M（≈1/4） |

诊断日志（rank 0）示例：
```
运行模式: 多卡 FSDP (world_size=4)
[FSDP 诊断] 参数已分片为 DTensor: True
[FSDP 诊断] 全量参数 4.87M | 本卡(rank 0)本地持有 1.29M (约 1/4)
```

**关键修复说明**：项目早期版本里 `fsdp_utils.py` 写好了但从未被训练脚本调用——即旧的"FSDP 测试"实际是多个独立进程各跑各的，并非真正的分片训练；且其 FSDP2 包装代码混用了 FSDP1 的 API，本身有误。本次已：
1. 修正 `fsdp_utils.py` 为 torch 2.12 正确的 FSDP2 API（`fully_shard(model, mp_policy=MixedPrecisionPolicy(...))`）
2. 补全 `setup_distributed` / `cleanup_distributed` 等分布式辅助
3. 将 FSDP 真正接入 `train_stage1_ssl4eo.py` 的 `main()`，并加诊断打印证明分片生效

---

## 七、Checkpoint 保存格式

保存内容（单个 `.pt` 文件）：
```
global_step          训练步数
encoder_state_dict   编码器完整权重
decoder_state_dict   解码器完整权重
optimizer_state_dict 优化器完整状态
config               训练配置
```

**FSDP checkpoint 格式说明**：采用 **full state dict（汇聚完整权重）**，非 sharded state dict。
通过 `get_model_state_dict` / `get_optimizer_state_dict` 配合 `full_state_dict=True` 把分片在各卡的
DTensor 汇聚成完整 Tensor，仅由 rank 0 写盘。实测：

- checkpoint 内 0 个 DTensor 残留（含优化器动量状态）
- 3 卡训练得到的 checkpoint 可在单卡 / CPU 上成功加载（**卡数解耦验证通过**）

---

## 八、踩过并已修复的问题

| 问题 | 修复 |
|---|---|
| zarr v3 API 与读取代码不兼容 | 降级到 zarr 2.x |
| webdataset shard 模式不匹配 | 改用 brace expansion |
| 图像 264 不能被 patch_size=16 整除 | 中心裁剪到 256 |
| mask 维度在 patch/pixel 空间不一致 | 损失函数内做 patch→pixel 上采样 |
| YAML 把 `1e-4` 解析成字符串 | 配置里改写为 `0.0001` |
| FSDP 工具未接入训练脚本（假分布式） | 真正接入 main()，加诊断验证 |
| FSDP2 包装误用 FSDP1 API | 修正为 `mp_policy=MixedPrecisionPolicy` |
| 优化器状态含 DTensor 无法跨卡数加载 | 用 get_optimizer_state_dict 汇聚 |
| 文件误放在 /Agent/ 下 | 移动到 WorldModel2026/ |

---

## 九、当前阶段边界

**已做**：数据可读性验证、Stage 1 观测编码器 MAE 预训练脚手架、单卡冒烟、FSDP 多卡冒烟。

**未做（留待后续）**：状态动力学、外生驱动 D、地理先验 G、未来状态预测、条件观测解码、扩散 decoder、下游任务头、大规模正式训练。

---

## 十、如何继续

完整使用说明、S2RGB 切换、FSDP 详解、关键代码定位、训练命令大全，详见
**[框架详细解析.md](框架详细解析.md)**。

---

最后更新：2026-06-15
