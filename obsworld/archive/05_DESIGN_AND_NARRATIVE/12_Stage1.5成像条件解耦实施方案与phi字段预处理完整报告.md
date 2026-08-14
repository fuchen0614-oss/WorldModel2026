# 12 Stage 1.5：成像条件解耦实施方案与 phi 字段预处理完整报告

**版本**: v1.0  
**创建时间**: 2026-06-22  
**状态**: 📋 实施计划已确定，等待执行

---

## 0. 执行摘要

### 0.1 为什么需要 Stage 1.5

当前 Stage 1 存在**致命缺陷**：

```python
# ❌ 当前实现（错误）
X (遥感图像) → Encoder → latent

# ✅ ObsWorld 应该是（正确）
X (遥感图像) + φ (成像条件) → Encoder → 成像无关的地表状态 s_t
```

**缺失的核心机制**：
- 没有使用 phi 字段（虽然数据返回了，但训练时完全忽略）
- 没有 Imaging Condition Encoder
- 没有 FiLM 调制机制
- 无法证明学到了"成像无关的地表状态"

### 0.2 Stage 1.5 的目标

1. **预处理 phi 字段**：从 zarr 提取成像条件，缓存为 parquet
2. **实现 Imaging Condition Encoder**：将 phi 编码为可注入的特征
3. **实现 FiLM 调制**：将 phi 特征注入到 Observation Encoder
4. **成像解耦训练**：加入成像解耦损失，证明模型学到了成像无关的状态

### 0.3 为什么要预处理 phi

| 对比维度 | 训练时动态计算 | **预处理成缓存（推荐）** |
|----------|----------------|------------------------|
| 训练效率 | 每 epoch 重复解析 zarr | ✅ 一次解析，永久复用 |
| 调试体验 | phi 错误难定位 | ✅ 离线验证，问题清晰 |
| 字段质量 | 容易不一致 | ✅ 统一 schema + field_mask |
| **论文价值** | 无独立贡献 | ✅ **可作为数据工作发布** |
| 后续扩展 | 每个数据集各自实现 | ✅ 统一接口 |

---

## 0.4 ⚠️ v2.0 重要修订（2026-06-25）

完成 v1.0 全量预处理（964 文件、24.4 万样本）后，对真实 zarr 复核发现 **1 个数据 bug + 1 个表述错误**，并补齐了 2 个关键解耦字段。**v1.0 缓存已被 v2.0 覆盖重跑。**

### 修复项

| # | 问题 | v1.0（错误） | v2.0（修复） |
|---|------|-------------|-------------|
| 1 | **cloud_cover 算错**（数据 bug，严重） | `(cloud_mask>0).mean()`，把 water/snow/cloud_shadow/no_data 全算成云 | `isin([3,4]).mean()`，仅 thin_cloud+thick_cloud |
| 2 | **time 单位标错**（表述错误） | README 写 "Unix timestamp"（暗示秒） | 实为**纳秒** since 1970（已从 zarr `time.attrs` 验证） |

**bug 1 的实测影响**（同一水域样本）：v1.0 算出云量 94.1%，v2.0 实际仅 13.0%——67% 的水体被误判为云。

### 新增字段（成像解耦核心干扰因子）

| 字段 | 计算方式 | 解耦价值 |
|------|---------|---------|
| `sun_elevation_0~3` | NOAA 天文公式（纯 numpy，24万样本 0.36s） | **最强成像干扰**：决定光照/阴影 |
| `season_0~3` | time(纳秒)+lat 推导，含南北半球翻转 | 强成像协变量：物候/积雪 |
| `day_of_year_0~3` | time 推导 | 连续时间编码 |
| `cloud_shadow_0~3` | cloud_mask==5 | 云影独立统计 |
| `valid_ratio_0~3` | cloud_mask!=6 | 有效像素占比 |
| `time_valid_0~3` | time>0 | 标记损坏时间戳（少数样本为负值） |

字段总数：**22 → 46**。`cloud_mask` 类别定义（zarr attrs 验证）：
`0=land,1=water,2=snow,3=thin_cloud,4=thick_cloud,5=cloud_shadow,6=no_data`

### 仍缺失字段的必要性与解决思路

| 缺失字段 | 必要性 | 状态 | 解决思路 |
|---------|-------|------|---------|
| `sun_elevation` | 高 | ✅ v2.0 已解决 | NOAA 公式，无需外部数据 |
| `season` | 高 | ✅ v2.0 已解决 | time+lat 推导 |
| `view_angle` 观测角 | 中 | ❌ 源数据缺失 | zarr/SSL4EO 均无；需 S2 官方 `MTD_TL.xml`。S2 窄视场(±10°)，第一版可忽略 |
| `sun_azimuth` 方位角 | 中 | ⏸ 可补 | NOAA 公式可扩展，按需添加 |
| `precipitation`/`temperature` | 中 | ❌ 需外部数据 | 经纬度+时间检索 ERA5，属 Stage 2 跨数据集工作 |
| `atmospheric_opacity` | 低 | ❌ 需外部数据 | 需 AOD 气溶胶产品，优先级低 |

**结论**：成像解耦最关键的两个干扰因子（太阳高度角、季节）v2.0 已补齐，FiLM 可直接使用。`view_angle` 因源缺失搁置，对 S2 影响有限。

---

## 1. 真实数据字段核查结果

### 1.1 核查方法

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
python scripts/inspect_ssl4eo.py --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1
```

### 1.2 SSL4EO-S12-v1.1 真实 zarr 字段（已验证）

通过实际解析 `ssl4eos12_shard_000001.tar` 中的 zarr 文件，确认字段如下：

| 字段 | 形状 | dtype | 说明 | 我们的处理 |
|------|------|-------|------|----------|
| `bands` | [4, 12, 264, 264] | int16 | 图像数据（4时间×12波段） | 提取形状信息 |
| `center_lat` | () | float64 | 中心纬度 | ✅ 直接使用 |
| `center_lon` | () | float64 | 中心经度 | ✅ 直接使用 |
| `cloud_mask` | [4, 264, 264] | uint8 | 云掩膜（0-5） | 计算覆盖率统计 |
| `crs` | () | int64 | 坐标系（EPSG） | ✅ 直接使用 |
| `time` | [4] | int64 | 时间戳数组 | 展开为 time_0~3 |
| `sample` | () | str | 样本ID | ✅ 直接使用 |
| `band` | [12] | str | 波段名称列表 | 暂不使用 |
| `file_id` | [4] | str | 文件ID | 暂不使用 |
| `x`, `y` | ... | ... | 坐标轴 | 暂不使用 |
| `spatial_ref` | ... | ... | 空间参考 | 暂不使用 |

### 1.3 我们能直接获取的字段（现有基础）

**✅ 100% 可用的字段**：
- `center_lat`, `center_lon`: 空间位置
- `crs`: 坐标系
- `time_0~3`: 4个时间戳
- `sample_id`: 样本标识
- `num_timesteps`, `num_bands`, `height`, `width`: 图像形状

**✅ ~85% 可用的字段**：
- `cloud_cover_0~3`: 云覆盖率（从 cloud_mask 计算）

**✅ 推导字段**：
- `sensor`: 根据 modality 推导（S2L2A → Sentinel-2）
- `product_level`: 根据 modality 推导（S2L2A → L2A）
- `spatial_resolution`: 根据 modality 设置默认值（S2L2A → 10m）

### 1.4 缺失但可扩展的字段（后续工作）

**⏸ 当前缺失，Stage 1.5 不强制需要**：
- `sun_elevation`: 太阳高度角（需要从 metadata 或计算）
- `view_angle`: 观测角度（需要从 metadata）
- `season`: 季节标签（可从时间戳推导，但需要额外逻辑）

**❌ 当前不可用，需要其他数据集**：
- `precipitation`: 降雨量（需要 ERA5 等气象数据）
- `temperature`: 温度（需要气象数据）
- `event_type`: 事件类型（需要 Sen1Floods11 等任务数据集）

---

## 2. 预处理脚本实现详解

### 2.1 脚本文件

**位置**: `/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/scripts/build_phi_cache.py`

**关键特性**：
- ✅ 基于真实 zarr 字段（已验证对应）
- ✅ 输出到独立根目录 `phi_processed/`
- ✅ 生成 field_mask 标记字段可用性
- ✅ 自动生成 README.md
- ✅ 保存处理统计 `_processing_stats.json`

### 2.2 输出目录结构（独立性设计）

```
/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/
├── train/                    # 原始数据（不动）
│   ├── S2L2A/
│   │   └── *.tar
│   └── S1GRD/
├── val/                      # 原始数据（不动）
├── train_metadata.parquet    # 官方 metadata（不动）
├── val_metadata.parquet      # 官方 metadata（不动）
└── phi_processed/            # ✅ 新增：独立的预处理根目录
    ├── README.md             # 数据集文档
    ├── train/
    │   ├── S2L2A/
    │   │   ├── ssl4eos12_shard_000001_phi.parquet
    │   │   ├── ssl4eos12_shard_000002_phi.parquet
    │   │   ├── ...
    │   │   └── _processing_stats.json
    │   └── S1GRD/
    │       └── ...
    └── val/
        └── ...
```

**独立性优势**：
- ✅ 明确标识：一看就知道这是我们做的工作
- ✅ 易于版本管理：可以打包分发
- ✅ 不污染原始数据：原始 tar 文件完全不动
- ✅ 易于检查：所有预处理结果集中在一个目录

### 2.3 生成的 phi 字段详细说明

**每个 parquet 文件包含的列**：

| 列名 | 数据类型 | 示例值 | 说明 |
|------|----------|--------|------|
| `sample_key` | str | `ssl4eos12_train_seasonal_data_0000001` | tar 文件中的 __key__ |
| `sample_id` | str | `0216839` | zarr 中的 sample 字段 |
| `modality` | str | `S2L2A` | 模态类型 |
| `sensor` | str | `Sentinel-2` | 传感器（推导） |
| `product_level` | str | `L2A` | 产品级别（推导） |
| `center_lat` | float64 | `33.670509` | 中心纬度 |
| `center_lon` | float64 | `47.222477` | 中心经度 |
| `crs` | int64 | `32638` | EPSG 代码 |
| `time_0` | int64 | `1582014000` | 第1个时间戳 |
| `time_1` | int64 | `1591260000` | 第2个时间戳 |
| `time_2` | int64 | `1599310000` | 第3个时间戳 |
| `time_3` | int64 | `1607220000` | 第4个时间戳 |
| `cloud_cover_0` | float32 | `0.15` | 第1个时间片云覆盖率 |
| `cloud_cover_1` | float32 | `0.08` | 第2个时间片云覆盖率 |
| `cloud_cover_2` | float32 | `0.32` | 第3个时间片云覆盖率 |
| `cloud_cover_3` | float32 | `0.02` | 第4个时间片云覆盖率 |
| `num_timesteps` | int32 | `4` | 时间步数 |
| `num_bands` | int32 | `12` | 波段数 |
| `height` | int32 | `264` | 图像高度 |
| `width` | int32 | `264` | 图像宽度 |
| `spatial_resolution` | float32 | `10.0` | 空间分辨率（米） |
| `_field_mask` | str | `{"center_lat": 1, ...}` | JSON 字符串，标记字段可用性 |

### 2.4 Field Mask 设计

**field_mask 的作用**：标记每个字段是否真实存在（1=可用，0=缺失）

**示例**：
```python
{
    "sample_key": 1,
    "modality": 1,
    "sensor": 1,
    "product_level": 1,
    "center_lat": 1,
    "center_lon": 1,
    "crs": 1,
    "time": 1,
    "cloud_mask": 1,
    "cloud_cover": 1,
    "bands_info": 1,
    "spatial_resolution": 1
}
```

**训练时如何使用**：
```python
if field_mask['cloud_cover'] == 0:
    cloud_feat = self.missing_embed  # 可学习的缺失 embedding
else:
    cloud_feat = self.numerical_encoder(cloud_cover)
```

---

## 3. 脚本与文档一致性检查

### 3.1 脚本已验证的字段

**`build_phi_cache.py` 中提取的字段**：

✅ 与真实 zarr 结构完全对应：
```python
# 空间字段
phi['center_lat'] = float(root['center_lat'][()])
phi['center_lon'] = float(root['center_lon'][()])

# CRS
phi['crs'] = int(root['crs'][()])

# 时间字段
time = np.array(root['time'])  # [4] int64
phi['time_0'] = int(time[0])
phi['time_1'] = int(time[1])
phi['time_2'] = int(time[2])
phi['time_3'] = int(time[3])

# 云覆盖统计
cloud_mask = np.array(root['cloud_mask'])  # [4, H, W] uint8
phi['cloud_cover_0'] = float((cloud_mask[0] > 0).mean())
# ...

# 图像形状
bands = np.array(root['bands'])
phi['num_timesteps'] = int(bands.shape[0])
phi['num_bands'] = int(bands.shape[1])
phi['height'] = int(bands.shape[2])
phi['width'] = int(bands.shape[3])

# 样本ID
phi['sample_id'] = str(root['sample'][()])
```

### 3.2 与任务文档的对应关系

**参考文档**: `11_SSL4EO第一步数据处理与字段构建方案.md`

| 文档中建议的字段 | 我们的实现 | 状态 |
|-----------------|----------|------|
| `sample_id` | ✅ 提取自 zarr['sample'] | 已实现 |
| `center_lon`, `center_lat` | ✅ 直接提取 | 已实现 |
| `crs` | ✅ 直接提取 | 已实现 |
| `timestamp` | ✅ 提取为 time_0~3 | 已实现 |
| `cloud_mask` | ✅ 计算覆盖率统计 | 已实现 |
| `sensor`, `product_level` | ✅ 根据 modality 推导 | 已实现 |
| `spatial_resolution` | ✅ 根据 modality 设置 | 已实现 |

---

## 4. 立即执行的命令清单

### 4.1 环境准备

```bash
# 激活环境
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

# 安装缺失依赖（只安装需要的）
pip install pandas pyarrow seaborn
```

**依赖检查结果**：
- ✅ numpy: 2.4.6
- ✅ torch: 2.12.0
- ✅ webdataset: 1.0.2
- ✅ zarr: 2.18.7
- ✅ matplotlib: 3.11.0
- ✅ tqdm: 4.68.2
- ❌ pandas: 需要安装
- ❌ pyarrow: 需要安装
- ❌ seaborn: 需要安装

### 4.2 测试预处理（5个 shards）

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026

python scripts/build_phi_cache.py \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 \
  --modality S2L2A \
  --split train \
  --max-shards 5
```

**预期输出**：
```
================================================================================
SSL4EO-S12 成像条件字段预处理
================================================================================
数据根目录: /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1
模态: S2L2A
划分: train
找到 5 个 tar shards
输出目录: /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed/train/S2L2A
================================================================================

Processing shards: 100%|████████| 5/5 [02:30<00:00, 30.12s/it]
✓ ssl4eos12_shard_000001: 512 samples
✓ ssl4eos12_shard_000002: 512 samples
...

================================================================================
预处理完成！
  处理的 shards: 5 / 5
  总样本数: 2560
  失败的 shards: 0
  统计文件: .../phi_processed/train/S2L2A/_processing_stats.json
================================================================================
```

### 4.3 检查输出

```bash
# 查看生成的文件
ls /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed/train/S2L2A/

# 查看 README
cat /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed/README.md

# 查看统计
cat /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed/train/S2L2A/_processing_stats.json

# 测试读取 parquet
python -c "
import pandas as pd
df = pd.read_parquet('/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed/train/S2L2A/ssl4eos12_shard_000001_phi.parquet')
print(f'Shape: {df.shape}')
print(f'Columns: {df.columns.tolist()}')
print(df.head())
"
```

### 4.4 运行统计分析

```bash
python scripts/analyze_phi_stats.py \
  --phi-cache-dir /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed/train/S2L2A \
  --output-dir outputs/phi_analysis/s2l2a_train \
  --max-files 5

# 查看生成的设计建议
cat outputs/phi_analysis/s2l2a_train/imaging_condition_encoder_design.md
```

### 4.5 完整预处理（测试成功后执行）

```bash
# S2L2A train split（477 shards，预计 2-4 小时）
nohup python scripts/build_phi_cache.py \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 \
  --modality S2L2A \
  --split train \
  > logs/build_phi_s2l2a_train.log 2>&1 &

# 查看进度
tail -f logs/build_phi_s2l2a_train.log

# S2L2A val split
python scripts/build_phi_cache.py \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 \
  --modality S2L2A \
  --split val

# S1GRD（如果需要双模态）
python scripts/build_phi_cache.py \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 \
  --modality S1GRD \
  --split train
```

---

## 5. 后续工作计划（3-4周）

### Week 1: phi 字段预处理 + 统计分析 ✅

**任务**：
- [x] 核查真实 zarr 字段
- [x] 修正 `build_phi_cache.py`（确保字段对应）
- [x] 设计独立输出目录
- [ ] 运行测试预处理（5 shards）
- [ ] 运行完整预处理（477 shards）
- [ ] 运行统计分析

**产物**：
- `phi_processed/` 目录
- 统计报告和可视化
- Imaging Condition Encoder 设计建议文档

### Week 2: Imaging Condition Encoder 实现

**任务**：
- [ ] 实现 `ImagingConditionEncoder` 模块
- [ ] 修改 `MultiModalViTEncoder`（加入 FiLM 调制）
- [ ] 单元测试
- [ ] Smoke test

**产物**：
- `models/encoders/imaging_condition_encoder.py`
- 修改后的 `multimodal_vit_encoder.py`

### Week 3: 成像解耦训练

**任务**：
- [ ] 修改数据加载器（读取 phi_cache）
- [ ] 实现成像解耦损失
- [ ] 修改训练脚本
- [ ] 单卡 + 多卡训练验证

**产物**：
- 修改后的 `train_stage1_dual.py`
- 成像解耦 checkpoint

### Week 4: 验证与扩展

**任务**：
- [ ] 消融实验：w/o phi vs w/ phi
- [ ] 跨模态一致性验证
- [ ] S1GRD phi 预处理
- [ ] 文档整理

**产物**：
- 实验报告
- Stage 1.5 交付文档

---

## 6. 可扩展字段规划（后续持续推进）

### 6.1 当前已具备的字段（立即可用）

**第一版 Imaging Condition Encoder 使用的字段**：
- ✅ `sensor`（类别）
- ✅ `modality`（类别）
- ✅ `center_lat`, `center_lon`（数值）
- ✅ `cloud_cover_avg`（数值，4个时间片平均）

### 6.2 可通过简单计算扩展的字段

**优先级高（Week 4 可加入）**：
- `season`: 从 `time_0~3` 推导（需要经纬度 + 时间戳）
- `time_of_day`: 从时间戳提取小时
- `day_of_year`: 从时间戳提取天数

**实现方式**：
```python
import pandas as pd
from datetime import datetime

# 从时间戳推导季节
def get_season(timestamp, lat):
    dt = pd.to_datetime(timestamp, unit='s')
    month = dt.month
    # 北半球 vs 南半球
    if lat > 0:  # 北半球
        if month in [3, 4, 5]: return 'spring'
        elif month in [6, 7, 8]: return 'summer'
        elif month in [9, 10, 11]: return 'autumn'
        else: return 'winter'
    else:  # 南半球（季节相反）
        ...
```

### 6.3 需要外部数据源的字段

**优先级中（Stage 2 配合其他数据集）**：
- `sun_elevation`: 需要 `pvlib` 库 + 时间戳 + 经纬度计算
- `view_angle`: 需要从 Sentinel 官方 metadata 提取
- `precipitation`: 需要 ERA5 气象数据
- `temperature`: 需要 ERA5 气象数据

**优先级低（后续研究扩展）**：
- `atmospheric_opacity`: 需要大气数据
- `soil_moisture`: 需要土壤数据
- `elevation`: 可从 DEM 模态获取

### 6.4 字段扩展流程

```
1. 修改 build_phi_cache.py，加入新字段提取逻辑
2. 重新运行预处理（只处理新增字段）
3. 更新 ImagingConditionEncoder（加入新字段编码）
4. 重新训练，评估新字段的贡献
```

---

## 7. 论文价值与数据集发布计划

### 7.1 预处理 phi 的独立价值

这个预处理工作本身就是**可发布的数据集增强**：

**潜在标题**：
- *Imaging Condition Fields for SSL4EO-S12: Enabling Imaging-Decoupled Remote Sensing Representation Learning*

**贡献**：
- 统一的成像条件 schema
- 为遥感社区提供即用的 phi 字段
- field_mask 设计用于处理缺失字段
- 完整的字段文档和使用示例

**投稿方向**：
- CVPR Datasets and Benchmarks Track
- NeurIPS Datasets and Benchmarks Track
- 或作为 ObsWorld 主论文的数据处理章节

### 7.2 数据发布清单

**需要发布的内容**：
- ✅ `phi_processed/` 完整目录
- ✅ `build_phi_cache.py` 脚本
- ✅ `analyze_phi_stats.py` 分析脚本
- ✅ README.md 文档
- ✅ 字段统计报告
- ✅ 可视化图表

**发布平台**：
- Hugging Face Datasets
- Zenodo
- 或项目 GitHub repository

---

## 8. 检查清单

### 8.1 脚本正确性检查

- [x] `build_phi_cache.py` 中的字段名与真实 zarr 一致
- [x] 输出路径设计为独立根目录 `phi_processed/`
- [x] 生成 field_mask 标记字段可用性
- [x] 自动生成 README.md
- [ ] 测试运行成功（5 shards）

### 8.2 文档一致性检查

- [x] 本文档与 `build_phi_cache.py` 字段对应
- [x] 与 `11_SSL4EO第一步数据处理与字段构建方案.md` 对应
- [x] 与 `STAGE1.5_PHI_PROCESSING_PLAN.md` 对应
- [ ] 与后续 `ImagingConditionEncoder` 实现对应（Week 2）

### 8.3 输出质量检查

- [ ] parquet 文件可读
- [ ] 字段类型正确
- [ ] field_mask JSON 可解析
- [ ] 统计信息合理
- [ ] README 内容完整

---

## 9. 风险与应对

| 风险 | 严重性 | 应对 |
|------|--------|------|
| zarr 字段缺失 | 中 | 使用 field_mask=0 标记，训练时跳过 |
| 预处理时间过长 | 低 | 后台运行，分批处理 |
| 磁盘空间不足 | 低 | parquet 压缩后每个文件 <500KB |
| 字段推导错误 | 中 | 统计分析时发现异常值并修正 |
| phi 对训练无帮助 | 高 | 消融实验验证，必要时调整 phi 字段选择 |

---

## 10. 总结

### 10.1 当前状态

- ✅ 真实 zarr 字段已验证
- ✅ 预处理脚本已完成（字段对应正确）
- ✅ 输出目录设计为独立根目录
- ✅ 文档完整且与脚本一致
- ⏳ 等待执行测试预处理

### 10.2 下一步行动

**立即执行**（今天）：
```bash
pip install pandas pyarrow seaborn
python scripts/build_phi_cache.py --max-shards 5 ...
```

**本周内**：
- 测试成功后，运行完整预处理（477 shards）
- 运行统计分析
- 根据统计报告确定 Imaging Condition Encoder 架构

**下周开始**：
- 实现 Imaging Condition Encoder
- 集成到训练流程
- 成像解耦训练与验证

---

**最后更新**: 2026-06-22  
**维护者**: Zhijian Liu  
**项目**: ObsWorld - Imaging-Decoupled Land-Surface State Dynamics
