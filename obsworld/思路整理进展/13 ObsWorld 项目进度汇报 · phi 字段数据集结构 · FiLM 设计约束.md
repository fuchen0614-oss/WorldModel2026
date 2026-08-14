---
title: "13 ObsWorld 项目进度汇报 · phi 字段数据集结构 · FiLM 设计约束"
version: v1.0
created: 2026-06-25
author: Zhijian Liu
project: ObsWorld
stage: "1.5"
tags:
  - ObsWorld
  - phi
  - imaging-condition
  - FiLM
  - stage1.5
---

# 13 ObsWorld 项目进度汇报 · phi 字段数据集结构 · FiLM 设计约束

**版本**: v1.0
**创建时间**: 2026-06-25
**维护者**: Zhijian Liu
**项目**: ObsWorld - Imaging-Decoupled Land-Surface State Dynamics
**本文定位**: 进度总览 + phi 数据集说明书 + 后续设计约束

---

## 0. 本文档导读

> [!abstract] 本文档回答四个问题
> 1. **我现在在整个项目的哪个位置？**（见 §1 框架与进度地图）
> 2. **我做的 phi 数据集到底是什么结构？**（见 §3 数据集详细结构）
> 3. **现在的数据有哪些已知问题？**（见 §4 已知问题与成因）
> 4. **接下来要注意什么、怎么设计？**（见 §5 注意事项 + §6 FiLM 设计约束）

### 与其他文档的关系

| 文档 | 角色 | 与本文的关系 |
|------|------|------------|
| [[10_ObsWorld完整实验流程与字段设计|10 ObsWorld 完整实验流程与字段设计]] | **总纲**：5+1 阶段完整路线 | 本文是总纲「阶段 1.5」的执行细节 |
| [[11_SSL4EO第一步数据处理与字段构建方案]] | 阶段 1 数据处理方案 | 本文的 phi 字段继承自 11 的 schema 设计 |
| [[12_SSL4EO第一步数据处理phi构造详情|12_Stage1.5成像条件解耦实施方案与phi字段预处理完整报告]] | 阶段 1.5 实施方案 | 本文是 12 的**进度快照 + 数据交付说明** |
| **13（本文）** | **进度汇报 + 数据集说明书** | 汇总当前状态，承上启下到 FiLM 实现 |

---

## 1. 整体框架与进度地图

### 1.1 ObsWorld 核心路线（来自总纲 §1）

```text
历史遥感观测 X + 当前成像条件 phi
    → Observation Encoder              ← 阶段 1 / 1.5【当前在这里】
    → Land-Surface State  z_t / S_t
    → State Dynamics Module            ← 阶段 2
       (输入 external driver D + geographic prior G)
    → Future Land-Surface State z_{t+h}
    → Observation Decoder              ← 阶段 3
       (输入 future imaging condition phi_{t+h})
    → Future Observation  X_hat_{t+h}
```

一句话主张：**先预测未来地表状态，再把状态解码成指定成像条件下的未来观测**，不是普通的"下一帧预测"。

### 1.2 阶段进度地图（对照总纲的 5+1 阶段）

| 阶段 | 总纲目标 | checkpoint | 状态 | 备注 |
|------|---------|-----------|------|------|
| 阶段 0 | 数据巡检 + 统一 schema | — | ✅ 完成 | zarr 字段已核查 |
| 阶段 1 | SSL4EO 观测编码器预训练（MAE） | `stage1_ssl4eo_encoder.ckpt` | ✅ 完成 | 双模态 MAE 5.7M，EuroSAT linear probing 69.57% |
| **阶段 1.5** | **状态感知 / 成像解耦辅助预训练** | `stage1_5_state_aware_encoder.ckpt` | **🔵 进行中** | **← 当前位置** |
| 阶段 2 | 未来状态与状态动力学（论文心脏） | `stage2_state_dynamics.ckpt` | ⏸ 未开始 | 需 EarthNet/DynamicEarthNet |
| 阶段 3 | 条件观测解码 | `stage3_observation_decoder.ckpt` | ⏸ 未开始 | |
| 阶段 4 | 下游任务与 world model 评估 | `stage4_task_finetune.ckpt` | ⏸ 未开始 | |
| 阶段 5 | 基础模型增强与对比 | `final_obsworld.ckpt` | ⏸ 未开始 | |

### 1.3 当前阶段 1.5 内部进度

阶段 1.5 的目标（总纲）：**让 encoder 的 latent 不只是图像纹理，而更接近成像无关的地表状态**。
拆成 4 个 Week（来自 12 号文档）：

| Week | 任务 | 状态 | 产物 |
|------|------|------|------|
| **Week 1** | **phi 字段预处理 + 统计分析** | **🔵 95% 完成** | `phi_processed/` 缓存 + 统计报告 |
| Week 2 | ImagingConditionEncoder + FiLM 实现 | ⏸ 待开始 | `models/encoders/imaging_condition_encoder.py` |
| Week 3 | 成像解耦训练 | ⏸ 待开始 | `stage1_5_state_aware_encoder.ckpt` |
| Week 4 | 消融验证（w/o phi vs w/ phi）+ 扩展 | ⏸ 待开始 | 实验报告 |

**Week 1 当前细节**：
- ✅ zarr 真实字段核查
- ✅ 预处理脚本 v2.0（修复 cloud_cover bug + 补 sun_elevation/season）
- ✅ 字段验证（1024 样本，46 字段全部正确）
- ✅ 季节/太阳高度角分布统计
- 🔵 **全量重跑进行中**（964 文件，约 2h）
- ⏸ 全量统计分析（重跑后）

> [!tip] 一句话定位
> 我们在**总纲阶段 1.5 → Week 1 收尾**，正在把成像条件字段 φ 准备成可供 FiLM 调制使用的干净数据集。

## 2. phi 数据集总览

### 2.1 这是什么

从 SSL4EO-S12-v1.1 的原始 zarr 中提取 / 计算的**成像条件字段缓存**，独立存放、不污染原始数据，训练时直接读 parquet。

### 2.2 目录结构与对应关系

```
TrainData/SSL4EO-S12-v1.1/
├── train/  S2L2A,S1GRD,...   原始 tar（不动）
├── val/    S2L2A,S1GRD,...   原始 tar（不动）
└── phi_processed/            ← 本数据集（v2.0）
    ├── README.md             自动生成的字段说明书
    ├── train/
    │   ├── S2L2A/   ssl4eos12_shard_000001_phi.parquet ... ×477 + _processing_stats.json
    │   └── S1GRD/   ×477
    └── val/
        ├── S2L2A/   ×5
        └── S1GRD/   ×5
```

**原始 tar 与 phi parquet 的对应关系**：
- 一个 `*.tar` shard → 一个 `*_phi.parquet`（同名，后缀 `_phi`）
- parquet 内一行 = tar 内一个 zarr 样本，通过 `sample_key`（= tar 的 `__key__`）一一对应
- 训练时：读图像从 tar，读 φ 从 parquet，用 `sample_key` join

### 2.3 规模

| 模态 | split | shard 数 | 样本数（约） |
|------|-------|---------|------------|
| S2L2A | train | 477 | 244,000 |
| S1GRD | train | 477 | 244,000 |
| S2L2A | val | 5 | 2,176 |
| S1GRD | val | 5 | 2,176 |
| **合计** | | **964 文件** | **~492,000** |

## 3. 字段详细结构（46 列）

每行一个样本。SSL4EO 每样本含 **4 个时间片**（4 次不同时间的拍摄），故时序字段都有 `_0~_3` 四份。

### 3.1 标识字段

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `sample_key` | str | tar `__key__` | 与原始 tar 样本一一对应的主键 |
| `sample_id` | str | zarr `sample` | zarr 内部样本号 |
| `modality` | str | 参数 | S2L2A / S1GRD |
| `sensor` | str | 推导 | Sentinel-2 / Sentinel-1 |
| `product_level` | str | 推导 | L2A / GRD |

### 3.2 空间字段（zarr 原生）

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `center_lat` | float64 | zarr `center_lat` | 中心纬度，范围 -53.6~66.6 |
| `center_lon` | float64 | zarr `center_lon` | 中心经度，范围 -125~179 |
| `crs` | int64 | zarr `crs` | EPSG 坐标系代码 |

### 3.3 时间字段（zarr 原生 + 有效性）

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `time_0~3` | int64 | zarr `time` | **单位：纳秒 since 1970-01-01**（非秒！已由 zarr `time.attrs['units']` 验证） |
| `time_valid_0~3` | int | 计算 | 时间戳有效性：`time > 0` 为 1。少数样本时间戳损坏为负值 |

> [!warning] 常见误区：time 是纳秒不是秒
> 用秒解读会得到「50131 年」的荒谬结果。
> 正确：`pd.to_datetime(time_0, unit='ns')`

### 3.4 衍生时间字段（本脚本计算）

| 字段 | 类型 | 计算方法 | 说明 |
|------|------|---------|------|
| `season_0~3` | int | 见下 §3.4.1 | 0=春 1=夏 2=秋 3=冬，**已按南北半球翻转** |
| `day_of_year_0~3` | int | `pd.to_datetime(ts,'ns').dayofyear` | 年内天数 1-366 |
| `sun_elevation_0~3` | float | NOAA 天文公式，见 §3.4.2 | 太阳高度角（度），范围实测 9.3~72.3° |

#### 3.4.1 season 计算方法

```python
month = pd.to_datetime(ts, unit='ns', utc=True).month
# 北半球
if   month in (3,4,5):   season_n = 0  # 春
elif month in (6,7,8):   season_n = 1  # 夏
elif month in (9,10,11): season_n = 2  # 秋
else:                    season_n = 3  # 冬
# 南半球季节相反
flip = {0:2, 1:3, 2:0, 3:1}
season = season_n if lat >= 0 else flip[season_n]
```

#### 3.4.2 sun_elevation 计算方法

用 **NOAA 太阳位置算法**（纯 numpy，无需 pvlib），步骤：
1. 纳秒时间戳 → 儒略日 → 自 J2000 起天数 n
2. 太阳平黄经 L、平近点角 g → 黄道经度 λ
3. 黄赤交角 ε → 赤纬 decl = arcsin(sin ε · sin λ)
4. 赤经 + 格林尼治恒星时 → 地方时角 H
5. 高度角 = arcsin(sin lat·sin decl + cos lat·cos decl·cos H)

精度 <0.5°，24.4 万样本 0.36 秒（已向量化）。夜间为负值（本数据集 0% 夜间，遥感卫星都在白天过境）。

### 3.5 云 / 质量字段（v2.0 修复 + 新增）

| 字段 | 类型 | 计算方法 | 说明 |
|------|------|---------|------|
| `cloud_cover_0~3` | float32 | `isin(cloud_mask,[3,4]).mean()` | **真实云量** [0-1]，仅薄云+厚云 |
| `cloud_shadow_0~3` | float32 | `(cloud_mask==5).mean()` | 云影占比 [0-1] |
| `valid_ratio_0~3` | float32 | `(cloud_mask!=6).mean()` | 有效像素占比（非 no_data） |

**cloud_mask 类别定义**（来自 zarr `cloud_mask.attrs['cloud_classes']`）：

| 值 | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|----|---|---|---|---|---|---|---|
| 含义 | land | water | snow | thin_cloud | thick_cloud | cloud_shadow | no_data |

### 3.6 图像元信息（zarr 原生）

| 字段 | 类型 | 值 | 说明 |
|------|------|-----|------|
| `num_timesteps` | int32 | 4 | 时间片数 |
| `num_bands` | int32 | 12(S2)/2(S1) | 波段数 |
| `height` / `width` | int32 | 264 | 原始尺寸（训练时中心裁剪到 256） |
| `spatial_resolution` | float32 | 10.0 | 米/像素 |

### 3.7 字段掩码

| 字段 | 类型 | 说明 |
|------|------|------|
| `_field_mask` | str(JSON) | 标记各字段组是否可用（1/0），训练时缺失字段走 missing embedding |

## 4. 已知问题与成因（基于 1024 样本统计）

### 4.1 已修复的历史问题（v1.0 → v2.0）

| 问题 | v1.0 错误 | 实测影响 | v2.0 修复 |
|------|----------|---------|----------|
| **cloud_cover 算错** | `(cloud_mask>0)` 把水/雪/云影/no_data 全当云 | 一个水域样本算出 94.1%，实际仅 13% | 改为 `isin([3,4])` |
| time 单位标错 | README 写 "Unix timestamp"（秒） | 按秒解读得 5 万年 | 改注为纳秒 |

> [!danger] v1.0 缓存的 cloud_cover 不可用
> 已覆盖重跑。

### 4.2 季节缺失问题（你关注的"缺春"）

**现象**：部分样本 4 个时间片不能覆盖全部 4 季，例如出现"冬-夏-秋-冬"（缺春）。

**成因**：SSL4EO 采样间隔**不是正好 3 个月**。实测样本0：

```
时间片: 02-18(冬) → 06-04(夏) → 09-05(秋) → 12-01(冬)
间隔:        107天        93天        87天
```

第一个间隔 **107 天（3.5 月）**，从 2 月（冬末）直接跨到 6 月（初夏），**整个春季核心月份（3-5月）被跨过**，所以缺春。

**各季节缺失率**（1024 样本，每季都可能缺）：

| 缺失季节 | 占比 | 缺失季节 | 占比 |
|---------|------|---------|------|
| 缺春 | 4.1% | 缺秋 | 3.3% |
| 缺夏 | 4.5% | **缺冬** | **6.3%** |

**季节覆盖完整度**：

| 覆盖季节数 | 占比 |
|-----------|------|
| 4 季全覆盖 | 83.1% |
| 3 季 | 15.5% |
| 2 季 | 1.4% |

**最常见的 4 种组合**（占 83%，本质是同一个春→夏→秋→冬循环的不同起点）：

```
冬-春-夏-秋  23.3%      春-夏-秋-冬  19.6%（"标准"顺序只是其一）
夏-秋-冬-春  21.6%      秋-冬-春-夏  18.6%
```

**结论**：季节缺失是数据本身特性，非 bug。起始季节随机、间隔约 3 个月有浮动，导致约 17% 样本缺某一季。FiLM 用 season 时**不能假设 4 片必然覆盖 4 季**。

### 4.3 数值分布速查（FiLM 归一化参考）

| 字段 | min | max | mean | std | 备注 |
|------|-----|-----|------|-----|------|
| sun_elevation | 9.3° | 72.3° | 49.3° | 14.5° | 0% 夜间，信息量最大的连续成像变量 |
| cloud_cover | 0 | 1 | 5.9% | — | 中位数 0%，**长尾稀疏**：仅 18.6% 时间片有云 |

## 5. 缺失字段与扩展规划

### 5.1 当前缺失字段：必要性与解决思路

| 缺失字段 | 对解耦必要性 | 状态 | 解决思路 |
|---------|------------|------|---------|
| `sun_elevation` 太阳高度角 | **高**（最强成像干扰） | ✅ 已解决 | NOAA 公式，无需外部数据 |
| `season` 季节 | **高**（物候/积雪协变量） | ✅ 已解决 | time+lat 推导 |
| `view_angle` 观测角 | 中（影响 BRDF/几何） | ❌ 源数据缺失 | zarr/SSL4EO 均无；需 S2 官方 `MTD_TL.xml`。S2 视场窄(±10°)，第一版可忽略 |
| `sun_azimuth` 太阳方位角 | 中（与高度角定阴影方向） | ⏸ 可补 | NOAA 公式可扩展，按需添加 |
| `precipitation`/`temperature` 气象 | 中（地表湿度/反照率） | ❌ 需外部数据 | 经纬度+时间检索 ERA5，属阶段 2 跨数据集工作 |
| `atmospheric_opacity` 大气透明度 | 低 | ❌ 需外部数据 | 需 AOD 气溶胶产品，优先级低 |

### 5.2 是否需要进一步扩展？

> [!important] 第一版 FiLM 不需要再扩展字段
> 成像解耦最关键的两个干扰因子（太阳高度角、季节）已齐备。

后续可考虑（按优先级）：
1. **sun_azimuth**（容易，NOAA 公式扩展一行）——若发现阴影方向重要
2. **ERA5 气象**（阶段 2）——跨数据集融合时统一做
3. **view_angle**（搁置）——源数据缺失，且对 S2 影响有限

## 6. FiLM / ImagingConditionEncoder 设计约束

基于 §4 的统计，明确以下设计约束（Week 2 实现时遵循）：

### 6.1 ⭐ 核心约束：season 必须与 lat + sun_elevation 联合输入

> [!important] 核心设计约束
> 同一个 season 编码值"1=夏"，在北半球是 6 月、在南半球是 1 月，**对应的太阳角、物候、积雪完全不同**。我们的数据**横跨南北半球**（lat -53.6~66.6），统计中"夏"的 day_of_year 横跨 1~366 就是南北半球混合的证据。
>
> **约束**：
> - season **不能单独**作为成像条件输入，否则模型无法区分"北半球的夏"和"南半球的夏"
> - **必须**和 `center_lat`（定半球）、`sun_elevation`（定实际光照）一起喂给 ImagingConditionEncoder
> - 推荐：sun_elevation 作为主连续信号，season 作为辅助类别，lat 提供半球上下文

### 6.2 字段编码方式

| 字段 | 编码方式 | 理由 |
|------|---------|------|
| `sun_elevation` | 连续，归一化 `(e-9)/(73-9)` 或 `sin(e)` | 信息量最大，无夜间无需特判 |
| `season` | 4 类 **Embedding**（非有序数值） | 起点随机，顺序本身无意义；配合 lat 用 |
| `center_lat/lon` | 连续，可加 `sin/cos` 周期编码 | 提供半球与地理上下文 |
| `cloud_cover` | log 变换或二值"有云/无云" | 长尾稀疏（中位数 0%，仅 18.6% 有云） |
| `sensor/modality` | Embedding | 单模态训练时为常数，双模态才有区分度 |

### 6.3 缺失值处理

- 用 `_field_mask` + `time_valid_*` 判断字段有效性
- 缺失字段（如损坏时间戳导致 season/sun_elevation 为 None）→ 走可学习的 **missing embedding**
- season 缺某季是数据特性（§4.2），**不算缺失**，正常编码即可

### 6.4 FiLM 调制位置

```python
phi_embed = ImagingConditionEncoder(sun_elev, season, lat, lon, cloud)  # [B, D]
gamma = gamma_proj(phi_embed)   # [B, D]
beta  = beta_proj(phi_embed)    # [B, D]
# 注入共享 Transformer 每一层（阶段1的双模态共享编码器）
x = x * (1 + gamma.unsqueeze(1)) + beta.unsqueeze(1)
```

> [!note] 注入位置说明
> 阶段 1 的编码器是**双模态共享 Transformer**（S1/S2 共享权重，靠 modality embedding 区分）。
> FiLM 注入到共享层，目标是让同一地表在不同成像条件（季节/光照/模态）下编码到**相同的状态空间**。

### 6.5 解耦验证目标（Week 4）

- 消融：w/o phi vs w/ phi 的 EuroSAT linear probing
- 跨成像一致性：同一地点不同季节/光照，latent 应更接近
- 反事实：替换 phi，重建应随成像条件改变而地表状态不变

## 7. 复现命令与下一步

### 7.1 全量预处理（tmux 前台）

```bash
tmux new -s phi
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
rm -rf /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed

python scripts/build_phi_cache.py --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 --modality S2L2A --split train && \
python scripts/build_phi_cache.py --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 --modality S1GRD --split train && \
python scripts/build_phi_cache.py --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 --modality S2L2A --split val && \
python scripts/build_phi_cache.py --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 --modality S1GRD --split val
```

### 7.2 全量统计分析

```bash
python scripts/analyze_phi_stats.py \
  --phi-cache-dir /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed/train/S2L2A \
  --output-dir outputs/phi_analysis/s2l2a_train
```

### 7.3 下一步（Week 2）

1. 实现 `models/encoders/imaging_condition_encoder.py`（遵循 §6 约束）
2. 修改 `multimodal_vit_encoder.py` 加入 FiLM 调制
3. 单元测试 + smoke test

---

## 8. 关键脚本与文件索引

| 文件 | 作用 |
|------|------|
| `scripts/build_phi_cache.py` | phi 提取主脚本（v2.0） |
| `scripts/analyze_phi_stats.py` | 统计分析 + 设计建议生成 |
| `scripts/inspect_ssl4eo.py` | zarr 字段巡检 |
| `TrainData/SSL4EO-S12-v1.1/phi_processed/` | 输出数据集 |
| `models/encoders/multimodal_vit_encoder.py` | 阶段 1 双模态共享编码器（FiLM 注入目标） |

---

**最后更新**: 2026-06-25
**维护者**: Zhijian Liu
**项目**: ObsWorld - Imaging-Decoupled Land-Surface State Dynamics
