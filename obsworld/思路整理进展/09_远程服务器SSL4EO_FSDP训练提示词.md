# 远程服务器 SSL4EO-S12-v1.1 与 FSDP 训练脚手架提示词

下面提示词用于交给远程服务器上的 Codex / Agent 执行。目标不是一开始就完整训练 ObsWorld，而是先在已下载的 SSL4EO-S12-v1.1 数据集上完成数据可读性验证、最小训练代码搭建、单卡 smoke test 和 FSDP 多卡训练 smoke test。

---

## 可直接使用的提示词

你现在在一台远程 Linux 服务器上工作。请在以下路径下创建并初始化一个遥感世界模型训练项目：

```text
工作目录：
/csy-mix02/cog8/zjliu17/Agent/WorldModel2026

数据集目录：
/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1
```

如果 `WorldModel2026` 不存在，请创建它。

### 1. 项目背景

这是一个遥感世界模型 ObsWorld 的第一阶段训练项目。ObsWorld 的完整目标是：

```text
历史遥感观测 + 成像条件
    -> 成像条件解耦的地表状态表征
    -> 外生驱动和地理先验条件下的未来地表状态
    -> 指定未来成像条件下的未来遥感观测
```

但当前不要直接实现完整 ObsWorld。当前只做第一阶段：

```text
Stage 1: 使用 SSL4EO-S12-v1.1 训练 Observation Encoder
```

这一阶段的目标是先让模型能够稳定读取 SSL4EO-S12-v1.1 数据，并完成一个最小的遥感观测编码器预训练闭环，例如 masked reconstruction / autoencoder / MAE-style 训练。该 encoder 后续会作为 ObsWorld 的观测编码器使用。

### 2. 当前任务目标

请按以下顺序执行，不要跳过数据验证直接开始大规模训练：

```text
1. 检查并汇报数据集目录结构
2. 验证 SSL4EO-S12-v1.1 的 tar / shard / split / modality 是否可读
3. 编写最小 dataloader 和 dataset smoke test
4. 编写一个最小 Observation Encoder 训练脚手架
5. 先单卡或单进程跑 10 step smoke test
6. 再使用 PyTorch FSDP 跑多卡 10 step smoke test
7. 保存 checkpoint、日志和运行说明
```

### 3. 数据集状态与验证要求

数据集已经下载好，路径是：

```text
/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1
```

该数据集体量约 2.3TB，可能主要是压缩包、tar shard 或 WebDataset 形式。这不是问题。请优先验证它是否能够被训练代码流式读取。

请先检查并输出：

```text
数据目录树的前几层
文件总数和主要后缀
是否存在 train / val / test 或类似 split
是否存在 S2L2A、S2RGB、S1GRD 等模态
是否存在 .tar、.zarr、.json、.csv、.parquet 或 manifest 文件
单个 shard 内部样例结构
```

然后编写并运行：

```text
scripts/inspect_ssl4eo.py
scripts/smoke_dataloader.py
```

`inspect_ssl4eo.py` 需要检查：

```text
数据路径是否存在
主要文件类型
可用 split
可用模态
样本 key
样本 tensor shape
dtype
数值范围
是否存在 NaN / Inf
```

`smoke_dataloader.py` 需要做到：

```text
读取至少 1 个 batch
打印 batch keys
打印每个 tensor 的 shape / dtype / min / max
确认 batch 能进入模型 forward
```

如果官方 SSL4EO-S12-v1.1 读取代码可用，可以复用官方 dataloader；如果不可用，请用 WebDataset / tarfile / zarr 等方式写一个最小可读版本。不要为了追求完美而卡住，先保证一个 batch 能正常读取。

### 4. 项目目录结构

请在 `WorldModel2026` 下创建如下项目结构：

```text
WorldModel2026/
  README.md
  requirements.txt
  configs/
    data/
    model/
    train/
  data/
    datasets/
    transforms/
    datamodules/
  models/
    encoders/
    decoders/
    losses/
  train/
    train_stage1_ssl4eo.py
    fsdp_utils.py
  scripts/
    inspect_ssl4eo.py
    smoke_dataloader.py
    smoke_train_single.py
    smoke_train_fsdp.sh
  checkpoints/
  logs/
  outputs/
```

第一版代码不要过度复杂，但要保证边界清楚：

```text
data/ 负责读取 SSL4EO
models/ 负责 encoder / decoder / loss
train/ 负责训练循环和 FSDP
scripts/ 负责检查、smoke test 和启动命令
configs/ 负责路径、batch size、模型大小、训练参数
```

### 5. 最小模型要求

第一版模型只需要实现 Stage 1，不需要完整 ObsWorld。

推荐最小结构：

```text
SSL4EO image batch
    -> patch embedding / small CNN / tiny ViT encoder
    -> lightweight decoder
    -> reconstruct image or masked image
```

可以先只使用一个模态，例如：

```text
S2L2A
```

或者如果官方数据中有更易读取的 RGB / S2RGB 版本，也可以先用：

```text
S2RGB
```

训练目标可以先用：

```text
L1 reconstruction loss
MSE reconstruction loss
masked reconstruction loss
```

输出 checkpoint：

```text
checkpoints/stage1_ssl4eo_encoder.pt
```

请在代码中保留后续扩展接口：

```text
phi / imaging condition
modality id
season / timestamp
field_mask
```

但第一版不要求完整实现 ObsWorld 的 dynamics、driver、geo prior 和 observation decoder。

### 6. FSDP 训练要求

请使用 PyTorch FSDP 作为分布式训练框架。注意：这里说的是 **FSDP**，不是 FDGP / FDPG。

FSDP 是 PyTorch 的 Fully Sharded Data Parallel，用于多 GPU 训练大模型。它会把参数、梯度和优化器状态分片到不同 GPU 上，以降低显存占用。

请实现：

```text
torchrun 启动
FSDP 包装模型
mixed precision，优先 bf16，如果硬件不支持则 fp16 或 fp32 fallback
activation checkpointing 可选
rank 0 日志输出
checkpoint 保存
单卡 fallback
```

如果当前 PyTorch 版本支持新接口，可以优先尝试 FSDP2 / fully_shard；如果服务器环境较旧，则使用：

```python
torch.distributed.fsdp.FullyShardedDataParallel
```

第一版不要求使用 CPU offload，除非显存明显不足。

### 7. 推荐配置文件

请至少创建：

```text
configs/data/ssl4eo.yaml
configs/model/stage1_tiny_encoder.yaml
configs/train/stage1_single.yaml
configs/train/stage1_fsdp.yaml
```

配置中需要包含：

```text
dataset_root
modality
split
batch_size
num_workers
image_size / crop_size
model_dim
learning_rate
max_steps
precision
checkpoint_dir
log_dir
```

不要把关键超参数硬编码在训练脚本里。

### 8. 执行顺序

请严格按下面顺序执行：

```bash
# 1. 检查数据目录
python scripts/inspect_ssl4eo.py --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1

# 2. dataloader smoke test
python scripts/smoke_dataloader.py --config configs/data/ssl4eo.yaml

# 3. 单卡训练 10 step
python scripts/smoke_train_single.py --config configs/train/stage1_single.yaml

# 4. 多卡 FSDP 训练 10 step
bash scripts/smoke_train_fsdp.sh
```

如果某一步失败，请先修复该步骤，不要继续进入下一步。

### 9. 训练输出要求

训练日志至少需要显示：

```text
当前 step
loss
学习率
batch shape
GPU 显存占用，如果方便
checkpoint 保存路径
```

checkpoint 至少保存：

```text
model state dict
optimizer state dict，如果实现了
config
global step
```

如果是 FSDP checkpoint，请说明保存格式是 full state dict 还是 sharded state dict。

### 10. 交付物

完成后请汇报：

```text
1. 创建了哪些文件
2. 数据集是否可读
3. 读取到的样本结构是什么
4. 单卡 smoke test 是否跑通
5. FSDP smoke test 是否跑通
6. checkpoint 保存在哪里
7. 如果失败，失败在哪一步、原因是什么、下一步如何修复
```

不要只写“代码已完成”。必须说明是否真的读到了 SSL4EO-S12-v1.1 的 batch，并是否真的完成了 forward / backward / optimizer step。

### 11. 当前阶段的边界

当前只做：

```text
SSL4EO-S12-v1.1 数据可读性验证
Stage 1 Observation Encoder 预训练脚手架
单卡 smoke test
FSDP 多卡 smoke test
```

当前不要做：

```text
完整 ObsWorld dynamics
未来地表状态预测
外生驱动 D
地理先验 G
未来成像条件解码
扩散模型 decoder
大规模正式训练
```

这些内容放到 Stage 2 / Stage 3。

### 12. 最终目标表述

这一步的最终目标是：

```text
在远程服务器上确认 SSL4EO-S12-v1.1 数据可以被训练代码稳定读取，
并搭建一个支持 PyTorch FSDP 的 Stage 1 遥感观测编码器训练脚手架，
先以 10 step smoke test 跑通完整 forward / loss / backward / optimizer / checkpoint 流程。
```

如果完成，该项目后续会继续扩展为：

```text
Observation Encoder
    -> Land-Surface State Space
    -> State Dynamics Module
    -> Conditional Observation Decoder
```

也就是完整 ObsWorld。

