# 21 phi v3 与 geo(DEM)字段说明文档

> 配套数据: `TrainData/SSL4EO-S12-v1.1/phi_processed_v3_s1geom/`(S1 几何)与 `geo_processed/`(DEM 地理先验)
> 生成脚本: `scripts/build_phi_v3_s1geom.py`、`scripts/build_geo_dem.py`
> 配套报告: `任务描述相关/20_S1几何字段审查报告.md`(可行性与验证)
> 本文目的: 说清 v3 新增了哪些字段、各自含义/编码/缺失约定、和现有 phi 的关系、如何被模型消费、以及如何看构建进度。

---

## 0. 一页速览

ObsWorld 的成像/地理条件分三套离线 parquet,均按 `sample_key`(= tar `__key__`)对齐,互不覆盖:

| 数据 | 目录 | 模态 | 内容 | 在架构中是 |
|---|---|---|---|---|
| phi v2(现有,46列) | `phi_processed/` | S2L2A + S1GRD | 时间/季节/太阳角/云/经纬度等 | phi 成像条件 |
| **phi v3 S1 几何(新)** | `phi_processed_v3_s1geom/` | 仅 S1GRD | 升降轨/相对轨道/卫星(+incidence占位) | phi 成像条件(补 S1) |
| **geo DEM(新)** | `geo_processed/` | DEM 派生 | 高程/坡度/坡向统计 | G 地理先验 |

> [!important]
> 三套**分开存、训练时按 sample_key join**,不重写主 phi。这样:不碰训练正在读的 `phi_processed/`;只读各自模态、不重复抽取;消融时一个开关即可加/去。

---

## 1. phi v3 — S1 SAR 几何字段

### 1.1 字段表(每样本,4 个时间片 t=0..3)

| 字段(后缀 `_t`) | 类型 | 取值 | 含义 | 缺失约定 |
|---|---|---|---|---|
| `s1_orbit_direction_t` | int | 0=降轨,1=升轨,-1=缺失 | 升/降轨 | -1 |
| `s1_relative_orbit_t` | int | 1–175,-1=缺失 | 相对轨道号(观测几何轨道) | -1 |
| `s1_satellite_t` | int | 0=S1A,1=S1B,-1=缺失 | 卫星 | -1 |
| `s1_abs_orbit_t` | int | 绝对轨道号,-1=缺失 | 溯源用(一般不进模型) | -1 |
| `s1_geom_valid_t` | int | 1/0 | 该时间片几何字段是否有效 | 0 |
| `s1_incidence_angle_t` | float | NaN(占位) | 入射角(当前不取真值) | NaN |
| `s1_incidence_valid_t` | int | 0(恒) | 入射角有效性(当前恒缺失) | 0 |

### 1.2 来源与可靠性(详见 20 号报告)

- 全部解析自 S1GRD zarr 的 `file_id`(完整原始 S1 产品 ID,如 `S1A_IW_GRDH_1SDV_20200307T145157_..._031571_03A32A_72A2`)。
- `orbit_direction`:绝对轨道号 + 成像时刻 + center_lon,用太阳同步轨道局地时(LST)法离线推算;**与 Planetary Computer STAC 真值验证一致率 38/38=100%**。
- `relative_orbit`:`((abs_orbit - 73或27) % 175)+1`(S1A 偏移 73,S1B 偏移 27),与 STAC 吻合。
- 抽样审查:file_id 出现率 100%、解析率 100%(90 样本/360 时间片)。

> [!warning]
> `s1_incidence_angle` 是**占位字段,恒为 NaN**。原因:STAC 不暴露场景级入射角;精确值需下原始 annotation XML,且 patch 在 250km 幅宽的横向位置未知。其几何主成分已被 `orbit_direction + relative_orbit` 隐式捕获。保留占位 + `field_mask=0`,将来要补不需改架构。

### 1.3 模型如何消费(A 路线)

- Stage1.5 走 A 路线:**encoder 不吃 phi,phi 进 decoder**。
- 编码器侧:`ImagingConditionEncoder(use_sar_geometry=True)` 内含 `SARGeometryEncoder`:
  - orbit_direction → 3 类 embedding(asc/desc/missing)
  - relative_orbit → 176 类 embedding(0 槽=missing,1–175)
  - satellite → 3 类 embedding
  - incidence → sin/cos+MLP(当前恒走 missing embedding)
- 默认 `use_sar_geometry=False`(向后兼容);开启后这些字段并入 `phi_embed`,供 decoder 的 phi 条件。
- 单时间片对齐:dataloader 按选中季节 t 取 `*_t` 标量,经 `batch_phi_single_timestep_to_tensors`(已扩展,检测到 v3 字段才发出)送入编码器。

---

## 2. geo — DEM 地理先验字段

### 2.1 字段表(每样本,标量统计)

| 字段 | 类型 | 含义 | 缺失约定 |
|---|---|---|---|
| `dem_mean` | float | patch 平均高程(米) | NaN |
| `dem_std` | float | 高程标准差(地形起伏强度) | NaN |
| `dem_min` / `dem_max` | float | 高程极值 | NaN |
| `slope_mean` | float | 平均坡度(°) | NaN |
| `slope_std` | float | 坡度标准差 | NaN |
| `aspect_sin` / `aspect_cos` | float | 坡向的 sin/cos 均值(∈[-1,1]) | NaN |
| `dem_valid` | int | 1/0,DEM 是否有效 | 0 |

### 2.2 设计说明

- 来源:SSL4EO 自带 **DEM 模态**(477 train shard,同 sample_key,10m 像元,单波段高程 int16)。
- slope/aspect:numpy 梯度派生(dx=dy=10m);**aspect 是角度,直接平均会在 0/360 处出错,故存 sin/cos**。
- **当前只存逐样本标量统计,不落 raster**:Stage1 阶段 G 作为标量条件即可;像素级 DEM/slope raster(供 Stage2 dynamics 的逐像素 G)留到真正用时再抽,避免现在占空间。
- 抽样验证:高程 -27~3008m、坡度 0~31°、aspect sin/cos∈[-1,1]、join 512/512、dem_valid=1 行零 NaN——数值合理。

### 2.3 在架构中的角色

- DEM 是 **G 地理先验**,喂柱2 `StateDynamicsModule` 的 `geo_dim`。
- 是 `w/o G vs w/ G` 消融所需的、最干净的真实 G(洪水"低洼易变"等物理先验靠它)。
- Stage1 阶段可暂不接;Stage2 启动动力学时直接 join。

---

## 3. 与现有 phi(v2)的关系

```text
sample_key(tar __key__)── 主键,三套对齐
   ├── phi_processed/{split}/S2L2A/*.parquet   (46列,S2 成像条件)
   ├── phi_processed/{split}/S1GRD/*.parquet   (46列,S1 成像条件)
   ├── phi_processed_v3_s1geom/{split}/S1GRD/*_phi_s1geom.parquet  (S1 几何,本文§1)
   └── geo_processed/{split}/DEM/*_geo_dem.parquet                 (DEM 先验,本文§2)
```

- v3 与 geo 都是**加列**,不动 v2。
- 训练时 PhiCache/dataloader 按 sample_key 把 v3(+geo)join 进 phi_dict 即可(待接;TODO)。
- 缺失统一约定:类别用 -1 哨兵、连续用 NaN,各带独立 valid 列;编码器走 learnable missing embedding,**不产生 NaN**(已在 [[phi-parquet-nan-int-fields]] 坑上规避)。

---

## 4. 如何查看构建进度(可视化)

构建脚本每完成一个 shard 落盘一个进度 JSON。看进度有三种方式:

### 4.1 进度可视化脚本(推荐)

```bash
PY=/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python3.11

# 看一次(带进度条)
$PY scripts/watch_phi_v3_progress.py

# 每 10 秒刷新(Ctrl-C 退出)
$PY scripts/watch_phi_v3_progress.py --loop 10
```

输出示例:
```
  S1几何 train     |█████░░░░░░░░░░░░░░░░░░░░░░░░░|  17.4%  83/477  ETA 21min
  DEM    train   |█░░░░░░░░░░░░░░░░░░░░░░░░░░░░░|   4.0%  19/477  ETA 32min
```

### 4.2 直接读进度 JSON

```bash
DATA=/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1
cat $DATA/phi_processed_v3_s1geom/_v3_s1geom_progress_train.json
cat $DATA/geo_processed/_geo_dem_progress_train.json
```
字段:`shards_done / shards_total / pct / eta_min / cum_* / updated`。

### 4.3 数文件数

```bash
ls $DATA/phi_processed_v3_s1geom/train/S1GRD/*.parquet | wc -l   # 目标 477
ls $DATA/geo_processed/train/DEM/*.parquet | wc -l               # 目标 477
```

### 4.4 断点续跑

两个脚本都支持 `--resume`,跳过已生成的 shard。中断后重跑同一命令即可继续:
```bash
$PY scripts/build_phi_v3_s1geom.py --split train --max-shards -1 --resume
$PY scripts/build_geo_dem.py       --split train --max-shards -1 --resume
```

---

## 5. 完成后的统计落盘

各 split 完成后写汇总 JSON:
- `phi_processed_v3_s1geom/_v3_s1geom_stats_{train,val}.json`(orbit 分布、geom_valid_rate)
- `geo_processed/_geo_dem_stats_{train,val}.json`(dem_valid_rate、字段清单)

---

## 6. 后续 TODO(需接入训练才生效)

- [ ] PhiCache/dataloader 把 v3 与 geo 按 sample_key join 进 phi_dict
- [ ] 训练 config 开 `use_sar_geometry=True`,做 w/o-S1geom vs w/-S1geom 消融
- [ ] Stage2 接 DEM 作 `geo_dim`,做 w/o-G vs w/-G 消融
- [ ] (future)incidence 真值:ASF/Copernicus metadata-only 取 annotation + geolocation grid 插值
- [ ] (待 state head)LULC/NDVI 抽取,作弱语义状态 S_t / 连续状态
</content>
