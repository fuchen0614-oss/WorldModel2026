# ObsWorld：EarthNet2021x raw 数据契约与主实验规范

> **状态：当前固定数据协议。**本文件定义本轮 raw `EarthNet2021x` 目录、manifest（文件清单）、开发验证和 EarthNet2021 standard evaluator（官方评估器）口径。GreenEarthNet 是独立的未来扩展，不影响本轮数据、代码或主表。

## 0. 一句话结论

我们使用服务器已有的 **EarthNet2021x NetCDF raw 数据发布**，并固定采用下列 **EarthNet2021 standard 协议**：

```text
训练：train
主测试：iid + ood
补充测试：extreme + seasonal
开发验证：仅从 train 中按 tile（Sentinel-2 地图格）固定划出 val_dev
```

不换训练数据、不重新下载；但也不把尚未核验的细分轨道或错误 evaluator 写入论文。

论文中的准确表述是：

> **ObsWorld is evaluated on the EarthNet2021x NetCDF release under the EarthNet2021 train/IID/OOD/Extreme/Seasonal protocol.**

中文：

> **ObsWorld 在 EarthNet2021x 的 NetCDF 数据发布上，按照 EarthNet2021 的训练、IID、OOD、极端事件和季节循环协议评测。**

## 1. 为什么这一口径与服务器数据完全一致

服务器数据根目录为：

```text
/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021/earthnet2021x
```

其现有物理目录与清单统计如下：

| 目录 | 文件数 | 时间范围 | 在论文中的用途 |
|---|---:|---|---|
| `train` | 23,816 | 2017–2020 | 训练来源 |
| `iid` | 4,205 | 2017–2020 | 同分布主测试 |
| `ood` | 4,202 | 2017–2020 | 空间域外主测试 |
| `extreme` | 3,972 | 2018 | 极端夏季、长跨度预测证据 |
| `seasonal` | 3,880 | 2017–2020 | 多年季节循环、长时程证据 |

该结构与 EarthNet2021 的四条测试轨道兼容。当前 metadata audit 已确认本项目使用的 raw release 具备这五个目录和正式字段；论文实验名称与评测规则固定采用本文件的 EarthNet2021 standard 口径。

## 2. 世界模型叙事不变，实验语言更准确

ObsWorld 仍然是：

> 一个由外生驱动和地理先验条件化的地表状态动力学遥感世界模型：从历史、有噪遥感观测中估计地表状态，以 DGH 推演未来状态，再将未来状态解码为可验证的未来遥感观测。

这里：

- `D`（driver，外生驱动）：八个 E-OBS 气象变量按五日窗口聚合的 24 维路径；
- `G`（geographic prior，地理先验）：固定 Copernicus DEM；
- `h`（horizon，预测跨度）：每一个未来五日状态的跨度；
- `phi`（observation condition，观测条件）：保留为 Stage1/Stage1.5 和跨产品 Gate 的证据，不在当前固定 Sentinel-2 产品主实验中夸大为已端到端验证的未来成像控制。

EarthNet2021 本身就是“给定未来气象驱动预测未来地表遥感观测”的基准，因此与世界模型路线天然一致。我们不需要另换一个数据集才能证明主张。

## 3. 为什么必须先冻结清单

“清单（manifest）”不是下载清单，也不是新数据；它是一份 JSON，固定本次训练或评测实际使用的文件列表、文件大小和摘要（digest，摘要校验值）。这样可以防止：

1. 训练代码递归扫描根目录，意外混入 IID/OOD；
2. 用测试集调学习率、挑 checkpoint（检查点）；
3. 统计量从测试集泄漏到训练集；
4. 日后无法复现“本次结果到底用了哪些文件”。

冻结后会得到：

```text
artifacts/protocols/earthnet2021x_standard_v1/
├── protocol.json        # 本次协议、tile 划分、主/补充测试轨道
├── inventory.json       # 文件数、tile 数、起止日期等元数据证据
├── train_dev.json       # 开发训练集；排除验证 tile
├── val_dev.json         # 开发验证集；仅来自 train 的固定 tile
├── train_all.json       # 最终固定步数重训时使用的全量 train
├── iid.json             # 锁定主测试
├── ood.json             # 锁定主测试
├── extreme.json         # 锁定补充测试
└── seasonal.json        # 锁定补充测试
```

`val_dev` 的 8 个 tile 由固定 seed（随机种子）确定。它只用于早停、选择 checkpoint 和调参；`iid/ood/extreme/seasonal` 全部禁止参与这些决定。

## 4. 服务器上现在可以直接执行的命令

这一步只读取目录、文件大小和文件名中的日期，**不打开全部 NetCDF 内容、不使用 GPU、不下载数据**，可以与正在运行的 Stage1.5 并行。

先拉取包含本规范和脚本的最新代码：

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
git pull --ff-only origin main
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
```

然后冻结清单：

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021/earthnet2021x
RUN_DIR="$PWD/artifacts/protocols/earthnet2021x_standard_v1"

nice -n 10 python scripts/freeze_earthnet2021x_protocol.py \
  --root "$DATA_ROOT" \
  --output-dir "$RUN_DIR" \
  --val-tile-count 8 \
  --seed 20260716 \
  --hash-mode none
```

`RUN_DIR` 必须是**尚不存在的新目录**；不要提前 `mkdir -p "$RUN_DIR"`，也不要用同一目录
重跑。冻结器会在私有暂存目录中完成所有 JSON 后再一次性发布，若同名目录已经存在会拒绝覆盖，
以免一次中断或重跑把两次实验的 manifest（清单）混在一起。需要重新冻结时，换一个带日期/版本的
新目录。

成功后快速查看协议：

```bash
python -m json.tool "$RUN_DIR/protocol.json"
```

预期要点：`primary_test_tracks` 是 `iid` 与 `ood`；`supplementary_test_tracks` 是 `extreme` 与 `seasonal`；`validation_tile_count` 是 8。

## 5. 清单后、正式 Stage2 前还要做什么

清单完成后即可继续写和调试 Stage2 模型。正式启动大规模训练前，再从**同一份** `train_dev.json` 计算 D/G 标准化统计量：

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021/earthnet2021x
RUN_DIR="$PWD/artifacts/protocols/earthnet2021x_standard_v1"

nice -n 10 python scripts/build_earthnet_conditioning_stats.py \
  --config configs/train/stage2_earthnet_v2_data.yaml \
  --data-root "$DATA_ROOT" \
  --manifest-path "$RUN_DIR/train_dev.json" \
  --output "$RUN_DIR/conditioning_stats_v2_train_dev.json" \
  --require-full-train
```

这第二条命令会实际读取全部训练 NetCDF，用于计算八个 E-OBS 字段和 `cop_dem` 的统计量；它比冻结清单慢，建议在 Stage1.5 结束或磁盘 I/O 空闲时运行。

## 6. Stage2 的训练和评测顺序

1. `train_dev.json → val_dev.json`：开发、过拟合小样本、选 checkpoint；
2. 固定模型结构、损失权重、训练步数；
3. 需要最终结果时，用 `train_all.json` 按固定步数重训；
4. 一次性评测 `iid.json` 与 `ood.json`，形成主表；
5. 再评测 `extreme.json` 与 `seasonal.json`，形成世界模型长时程与极端驱动证据；
6. 最后补 Direct-DGH、Persistence、Climatology、强时空基线和消融。

主评测使用 EarthNetScore（ENS，EarthNet 综合分数）及其 MAD/OLS/EMD/SSIM 分量；NDVI 误差、预测跨度曲线、D/G 干预和 partition consistency（时间分割一致性）作为支持“学习到动力学而非普通图像预测”的证据。

## 7. 明确禁止的做法

- 不能把整个 `iid` 或 `ood` 目录改名为不存在的更细测试轨道；
- 不能从根目录递归扫描后混合训练和测试文件；
- 不能用 IID/OOD 结果调学习率、选择 epoch 或决定损失权重；
- 不能用测试集参与 D/G 标准化；
- 不能把当前固定 Sentinel-2 主实验夸大为“任意未来成像条件可控渲染”。

## 8. 本规范对应的代码命名

正式配置统一为：

```yaml
data:
  dataset: earthnet2021x
  dataset_protocol: earthnet2021_standard_v1
  stage2_protocol: earthnet2021x_path_v2
```

这样，数据名称、配置名称、训练清单、论文实验表和服务器目录全部使用同一口径。

## 参考

- [EarthNet2021: A Large-Scale Dataset and Challenge for Earth Surface Forecasting as a Guided Video Prediction Task](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf)
- [EarthNet Models PyTorch](https://github.com/earthnet2021/earthnet-models-pytorch)
