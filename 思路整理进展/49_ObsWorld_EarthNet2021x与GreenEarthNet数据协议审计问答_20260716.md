# 49. ObsWorld：EarthNet2021x 数据协议定稿与 GreenEarthNet 历史审计问答

> 日期：2026-07-16  
> 状态：**历史审计说明，数据决策已定稿。**服务器 `EarthNet2021/earthnet2021x` 的 metadata audit（元数据审计）为 `PASS`：`train=23,816`、`iid=4,205`、`ood=4,202`、`extreme=3,972`、`seasonal=3,880`，并通过 8 个 E-OBS、`cop_dem` 与官方评分字段的抽样检查。当前 Stage2 固定只用这套 raw EarthNet2021x 数据和 EarthNet2021 standard 协议；GreenEarthNet 目录不下载、不合并、不作为本轮主表依据。
> 代码对应：`scripts/audit_earthnet2021x.py`（当前只读审计）以及 `scripts/audit_greenearthnet_layout.py`（保留作未来独立扩展，不是当前闸门）。

---

## 一句话结论

**不重新下载，也不再二选一。**当前主线固定为服务器已有的
`EarthNet2021/earthnet2021x` raw release：`train` 训练、`val_dev` 开发选择、`iid/ood`
主评测、`extreme/seasonal` 压力测试，并使用同一套 EarthNet2021 standard evaluator
（官方评估器）。另一个 `GreenEarthNet` 目录及其 `*_chopped` 轨道不进入本轮训练、验证、
预测导出或主表；以下涉及 Green 的问答只解释此前为何需要区分目录名称，不能覆盖这一最终决定。

## Q1：为什么会有 EarthNet2021、EarthNet2021x 和 GreenEarthNet 三个名字？

**答：它们有关联，但“名字相似”不等于“评测规则相同”。**

- 原始 [EarthNet2021](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf) 使用 `train/iid/ood/extreme/seasonal` 这一组发布划分，常用 EarthNetScore（ENS）评估。
- [GreenEarthNet / Contextformer 官方仓库](https://github.com/vitusbenson/greenearthnet) 明确说明：论文名是 **GreenEarthNet**，开发时也会把同一新版数据/代码称作 `earthnet2021x` 或 `en21x`。它的 CVPR-2024 主协议使用 `train`、`val_chopped`、`ood-t_chopped`，并有 `ood-s_chopped`、`ood-st_chopped` 作为补充轨道。
- 所以 `earthnet2021x` 是一个很有价值的**发布/兼容名称**，但不是足以确定论文该用 ENS 还是 GreenEarthNet CVPR-2024 evaluator（评估器）的证据。

这不是推翻原有路线；恰恰相反，它解释了为什么现有 raw NetCDF 有 8 个 E-OBS 字段、`cop_dem` 等更适合 DGH 的字段，也解释了为什么项目中已经存在 GreenEarthNet 的 NetCDF 导出和评测代码。

## Q2：目前两套服务器目录已经知道什么？

用户已提供的事实如下。

| 位置 | 已观察到的内容 | 可以确认什么 | 还不能确认什么 |
|---|---|---|---|
| `/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021/earthnet2021x` | `train/iid/ood/extreme/seasonal`、`.manifests`，其中 `train` 清单的远端前缀为 `earthnet/earthnet2021x/train/...` | 有完整原始训练根；可立刻用于 Stage2-v2 的训练数据审计与统计量计算 | 这套 raw split 在论文中最终应叫原始 EarthNet2021 协议，还是 GreenEarthNet 的 raw release |
| `/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet` | `iid_chopped`、`ood-t_chopped`、`ood-s_chopped`、`ood-st_chopped`，以及 `iid/ood/extreme` 等目录；用户统计到 31,390 个 `.nc` | 已经有 Green 风格的若干评测轨道，不一定要重新下载 | 截至已给出的目录列表，**未见** `train` 与 `val_chopped`；因此尚不能自动组成完整官方 Green 主协议 |

特别注意：`*_chopped` 的文件数会因为一个原始 minicube（小立方体）被切成多个评测片段而大于原始样本数。它不能与 raw 文件数一一比较，更不能拿来证明“全部下载完成”。

## Q3：现在推荐用哪一套做主实验？

**最终推荐：固定 raw EarthNet2021x，不换数据集。**

1. **训练数据根**：继续使用
   `/TrainData/EarthNet2021/earthnet2021x/train`。它已有完整训练规模，且 Stage2-v2
   loader（加载器）正是为其 150 天 NetCDF、8 个 E-OBS 字段和 `cop_dem` 写的；不需要重下。
2. **开发与选择**：由 frozen manifest（冻结清单）从 `train` 按 tile（地图格）划分
   `train_dev/val_dev`；只有 `val_dev` 用于 best checkpoint（最佳检查点）选择和超参数判断。
3. **论文主表**：`iid + ood`；**压力测试**：`extreme + seasonal`。训练、开发验证和测试
   使用互不重叠的 manifest，EarthNetScore（ENS）与内部 RGBN/NDVI 指标均在同一口径下报告。
4. **GreenEarthNet**：不作为本轮对照、测试或“更高版本数据集”的替换。以后若另起扩展，
   必须有单独的数据根、manifest、训练运行和表格，不能与这套 ENS 数字混在一起。

因此不是“退而求其次”，而是**使用已经完整、可审计、与现有 DGH/Stage1.5 完全匹配的
EarthNet2021x raw release，把世界模型方法和实验论证先做扎实。**

## Q4：服务器上现在应运行什么？

下面命令可与 Stage1.5 训练并行：只扫描目录和少量样本，不使用 GPU，不下载文件，不修改数据集。

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
git pull --ff-only origin main
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

RAW_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021/earthnet2021x
REPORT=reports/earthnet_protocol/audit_metadata.json

nice -n 10 python scripts/audit_earthnet2021x.py \
  --root "$RAW_ROOT" \
  --required-splits train iid ood extreme seasonal \
  --schema earthnet2021x-standard \
  --scan-mode metadata \
  --max-files-per-split 64 \
  --output "$REPORT"

python - <<'PY'
import json
from pathlib import Path
p = Path("reports/earthnet_protocol/audit_metadata.json")
r = json.loads(p.read_text())
print(r["status"])
print({name: item["num_files"] for name, item in r["splits"].items()})
PY
```

随后冻结本轮所有清单（这一步只读取路径、文件名和大小）：

```bash
RUN_DIR=artifacts/earthnet2021_standard
nice -n 10 python scripts/freeze_earthnet2021x_protocol.py \
  --root "$RAW_ROOT" \
  --output-dir "$RUN_DIR/manifests" \
  --val-tile-count 8 \
  --seed 20260716 \
  --hash-mode none
```

这会生成 `train_dev.json`、`val_dev.json`、`train_all.json`、`iid.json`、`ood.json`、
`extreme.json`、`seasonal.json`；它们就是后续 stats、训练、预测和评分的唯一文件来源。

## Q5：为什么不能把 raw `train` 和 `ood-t_chopped` 直接拼起来？

**答：本轮不这样做。**

需要同时确认四件事：

1. raw `train` 和 chopped track 都有 Stage2 所需的 150 天、RGBN、8 个 E-OBS、`cop_dem` 字段；
2. chopped track 具有 Green evaluator 所需的 `s2_dlmask`、`s2_SCL`、`esawc_lc`、`geom_cls`；
3. 两边的日期/坐标和样本命名没有错位，且不是把相同地点时间泄漏到 train 和 OOD；
4. 正式 manifest（文件清单）能明确记录每个文件来自哪一个根，不能用递归 glob（全目录模糊扫描）偷偷混入其它目录。

本项目代码会拒绝把两根数据自动合并；即使未来扩展，也必须重新训练并单独报告，不能把
raw EarthNet 训练与 chopped 评分包装成同一主实验。

## Q6：这对 DGH、phi 和“模拟真实世界”叙事有什么影响？

**几乎没有负面影响，反而让主张更准确。**

- `D`：仍是 8 个 E-OBS 气象字段的 24-D 五日路径；它直接建立在 raw NetCDF 上，并由 EarthNet2021 standard 指标核验。
- `G`：仍固定 `cop_dem`；`C`（日历）和 `Δt`（真实五日步长）仍与 D 分离。
- `phi`：固定 Sentinel-2 主任务不虚构未来太阳角/几何；Stage1.5 仍作为更好状态初始化的候选，而不是被丢弃。
- 世界模型：真正需要证明的是**受驱动的开环状态递推、时间可组合性和可观测未来核验**。这三点由 Direct24、rollout 和 partition 对照来证明，不依赖把数据集改名。

## Q7：接下来代码工作按什么顺序？

1. 完成当前 raw 数据清单冻结与完整 train-only conditioning stats（条件统计）。
2. E-2：把 checkpoint、预测清单、EarthNetScore 结果绑定为不可混用的来源记录。
3. 对 Direct24、rollout24、partition24 分别跑 32–128 个 cube 的小样本过拟合。
4. 跑 one-seed Gate（单随机种子闸门）：Direct/rollout/partition 与 D 干预证据。
5. 方向成立后再进行三随机种子主实验与置信区间。

## 相关来源与文件

- [GreenEarthNet 官方仓库](https://github.com/vitusbenson/greenearthnet)：说明 `GreenEarthNet`、`earthnet2021x`、`en21x` 的命名关系，并给出 `ood-t_chopped` 推理/评测入口。
- [GreenEarthNet CVPR 2024 论文](https://openaccess.thecvf.com/content/CVPR2024/papers/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.pdf)：官方数据与植被预测协议背景。
- [EarthNet2021 原论文](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf)：ENS 和原始 split 的背景。
- `scripts/audit_greenearthnet_layout.py`：这次新增的可执行审计。
- `47_ObsWorld_Stage2正式代码技术指导与实现规范_20260716.md`：后续 Direct24/rollout/partition 具体实现规范。
