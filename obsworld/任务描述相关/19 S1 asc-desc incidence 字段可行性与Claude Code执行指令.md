# 19 S1 asc/desc 与 incidence 字段可行性与 Claude Code 执行指令

> 本文目的:补充 18 号文档第 7 节的第 5 点。若 SSL4EO-S12-v1.1 当前缓存内没有 S1 的升/降轨与入射角字段,不能简单写"不存在",而要判断能否从 Sentinel 原始产品元数据、公开 STAC/API 或官方 XML 反查并补入 phi。

---

## 0. 一页结论

**我的判断:值得查,但要分级执行。**

| 字段 | 优先级 | 可行性判断 | 推荐处理 |
|---|---:|---|---|
| S1 `asc/desc` / orbit direction | 高 | 中到高。若 SSL4EO 样本保留原始产品 ID、SAFE 名称、scene id 或 STAC link,通常可从产品元数据/STAC 查询得到 | 优先查,能可靠获得就加入 phi |
| S1 `incidence_angle` | 高 | 中。Sentinel-1 原始产品 annotation XML 有 incidence angle 网格;部分平台也有 angle/localIncidenceAngle。但前提是能反查原始产品或使用同位置同时间查询公开 catalog | 先做小样本可行性验证,再决定是否全量 join |
| S2 view/incidence angle | 中低 | 理论上可从 S2 tile metadata `MTD_TL.xml` 或平台角度元数据获得,但 SSL4EO 已用 S2 L2A 且 S2 窄视场,优先级低于 S1 | 暂不阻塞 Stage1.5 A 主线 |

**最重要的限制:**  
如果 SSL4EO 的 zarr/tar 样本里只有 `sample_key / center_lat / center_lon / time`,没有原始 Sentinel 产品 ID,那仍然可以尝试按 `(lat, lon, time)` 去 STAC/catalog 反查,但这会变成近似匹配,必须报告匹配置信度和失败率,不能静默当真值用。

---

## 1. 为什么不是"字段不存在就结束"

S1 的几何成像条件对本文很重要。当前 phi 主要覆盖 S2 的太阳角、季节、云量;但 S1 真正的成像差异来自:

- 升轨 / 降轨:ascending / descending;
- 入射角:incidence angle 或 local incidence angle;
- 相对轨道 / 观测几何;
- 极化 VV/VH,目前已经体现在输入通道里。

如果 S1 这些字段完全缺席,"双模态成像解耦"就会变成 S2 较强、S1 较弱。因此应先查:

```text
SSL4EO 内部是否已有字段
  ↓ 若没有
能否从原始 Sentinel-1 SAFE/XML 或公开 STAC 反查
  ↓ 若能
生成 phi v3,用 field_mask 标记有效性
  ↓ 若不能
在报告中明确 unavailable,不要伪造
```

---

## 2. 公开资料支持的可行来源

### 2.1 Sentinel-1 原始 SAFE / annotation XML

Sentinel-1 Level-1 产品采用 SAFE 结构,包含 `manifest.safe` 和 annotation XML。公开产品规格/平台文档显示,annotation/geolocation grid 中存在 `incidenceAngle` 字段。

可行路径:

```text
原始 S1 SAFE 或产品 ZIP
  ├── manifest.safe
  │     └── orbitProperties / pass / relative orbit 等
  └── annotation/*.xml
        └── geolocationGridPoint / incidenceAngle
```

如果能拿到原始产品或能远程读取 XML,就可以:

1. 解析 `orbitProperties/pass` 得到 ascending / descending;
2. 解析 annotation XML 的 geolocation grid;
3. 按 SSL4EO patch 中心点或 patch footprint 插值得到平均 incidence angle;
4. 写入 `s1_orbit_direction_t`、`s1_incidence_angle_t` 等 phi 字段。

### 2.2 STAC / 云平台元数据

如果拿不到 SAFE XML,可以查公开 catalog:

- Microsoft Planetary Computer Sentinel-1 GRD STAC 通常包含 orbit、polarization、instrument mode 等属性;
- Google Earth Engine 的 Sentinel-1 GRD 资产提供 `angle` band,其说明是由 annotation 中 `geolocationGridPoint` 的 `incidenceAngle` 插值得到;
- Sentinel Hub 对 S1 GRD 支持 `localIncidenceAngle`,但通常依赖其服务环境和 orthorectification 设置。

这些来源可用于 feasibility check,但要注意:

- STAC 查询按 `(lat, lon, time)` 反查可能匹配到多个产品;
- SSL4EO 的裁剪 patch 不一定保留完整 footprint;
- 如果只能获得场景级平均角度,不能包装成像素级真值;
- 如果使用平台派生字段,论文里要写清楚来源与近似。

### 2.3 Sentinel-2 MTD_TL.xml

S2 tile metadata `MTD_TL.xml` 中有太阳角、观测角网格。理论上可用于补 S2 view angle / sun azimuth,但当前优先级低于 S1,原因是:

- S2 的太阳高度角已由 NOAA 公式计算;
- S2 view angle 对 Sentinel-2 窄视场第一版影响较小;
- 当前最明显短板是 S1 几何字段完全缺席。

---

## 3. 执行策略:不要影响当前训练

你当前正在训练模型,因此 phi 扩展必须与训练隔离。

**硬规则:**

1. 不覆盖当前训练正在读取的 `phi_processed`。
2. 新字段审查和构建写入新目录,例如:

```text
phi_processed_v3_s1geom_audit/
phi_processed_v3_s1geom/
```

3. 先做小样本 audit,不要直接全量跑。
4. phi 构建应主要是 CPU/I/O 工作,不要占 GPU。
5. 若在远程服务器执行,建议低优先级后台跑:

```bash
tmux new -s s1geom_audit
nice -n 10 ionice -c2 -n7 python scripts/audit_s1_metadata.py ...
```

6. 当前训练若是旧 C 路线 Stage1.5,保留 checkpoint 可作为 ablation,但不要再新开旧 C 路线长训。

---

## 4. Claude Code 执行指令

下面这段可以直接发给 Claude Code。

```text
请补充执行 S1 asc/desc + incidence 字段可行性审查与 phi v3 方案。注意:当前用户正在训练模型,不要覆盖当前训练正在使用的 phi_processed,不要停止训练。

背景决策:
1. Stage1.5 主线采用 A 路线: encoder 不吃 phi,decoder 接 (z, phi)。
2. 论文战略目标仍按三柱甲路线,但当前工程优先柱1+3证据。
3. S1 asc/desc + incidence 是 phi 补强项,需要先核实是否可可靠获得。
4. 如果 SSL4EO 内部没有字段,不能只报告"没有";必须继续评估能否从 Sentinel 原始 SAFE/XML、公开 STAC/catalog 或平台角度元数据反查。

任务 A:本地 SSL4EO 样本元数据审查
请检查 SSL4EO-S12-v1.1 的 S1GRD train/val 多个 shard,至少抽样:
- train 前 5 个 shard;
- train 随机 5 个 shard;
- val 全部或至少 5 个 shard。

检查范围:
- zarr arrays;
- zarr attrs;
- tar member names;
- WebDataset __key__;
- sample 字段;
- 现有 phi parquet;
- 是否存在 product_id / scene_id / SAFE name / original filename / STAC id / orbit / pass / incidence 等字段。

重点搜索字段名:
- ascending, descending, asc, desc
- orbit_direction, pass_direction, orbitProperties, relative_orbit, absolute_orbit
- incidence, incidence_angle, local_incidence_angle, look_angle, view_angle
- SAFE, product_id, scene_id, granule, annotation, manifest

任务 B:如果本地已有可靠字段
1. 输出字段位置、样例值、缺失率、是否每个时间片都有。
2. 修改 build_phi_cache.py,写入 phi v3 新字段。
3. 修改 PhiCache / batch_phi_single_timestep_to_tensors。
4. 修改 ImagingConditionEncoder,新增可选 SAR geometry encoder:
   - orbit direction: categorical embedding;
   - incidence angle: numeric sin/cos 或 normalized scalar + MLP;
   - 缺失走 missing embedding。
5. 所有字段必须有 field_mask,不能产生 NaN。
6. 输出到新目录 phi_processed_v3_s1geom,不要覆盖旧目录。

任务 C:如果本地没有可靠字段
继续做可行性反查,不要直接结束。

C1. 先判断是否有原始 Sentinel 产品 ID 或 SAFE 名称。
如果有:
- 尝试通过 Copernicus Data Space / ASF / STAC / Microsoft Planetary Computer 等公开 catalog 查询对应产品;
- 优先下载或读取 metadata/XML,不要下载完整影像大文件;
- 对 Sentinel-1,重点读取 manifest.safe 与 annotation/*.xml;
- 从 manifest.safe 或 STAC property 获取 asc/desc;
- 从 annotation geolocation grid 的 incidenceAngle 获取 patch 中心或平均 incidence angle。

C2. 如果没有产品 ID,只有 lat/lon/time:
- 用 sample 的 center_lat, center_lon, time 做 STAC/catalog 近似查询;
- 时间窗口先设 ±1 天,必要时 ±3 天;
- 空间上要求产品 footprint 覆盖 patch 中心;
- 若多产品匹配,按时间最近、同极化、IW/GRD、VV/VH、覆盖中心点筛选;
- 输出匹配置信度与失败率。

C3. 若近似匹配可靠率低:
- 不要把 incidence 当真值加入主训练;
- 只保留 schema 占位字段,field_mask=0;
- 报告不可用原因和未来可行路线。

任务 D:生成 Obsidian 友好的 Markdown 报告
请生成 md 报告,路径建议:
output/20_S1几何字段审查报告.md

报告必须包含:
1. 执行摘要;
2. 本地字段审查结果;
3. 外部 XML/STAC 反查可行性;
4. 字段级结论表:
   - asc/desc 是否可用;
   - incidence 是否可用;
   - 来源;
   - 缺失率;
   - 置信度;
   - 是否建议进 phi v3;
5. 是否已生成 phi v3;
6. 对当前训练是否有影响;
7. 下一步建议;
8. 关键命令和日志路径。

Markdown 需兼容 Obsidian:
- 使用标准标题 # / ## / ###;
- 表格用普通 markdown table;
- 可使用 > [!important] / > [!warning] callout;
- 不要使用需要额外插件才能渲染的语法。

任务 E:安全并行要求
- 不要停止当前训练;
- 不要覆盖旧 phi_processed;
- 不要占用 GPU;
- 全量构建前先给出小样本 audit 结果;
- 如果需要下载外部 metadata,先估算数量、大小、时间和失败风险,再执行。

最终交付:
1. output/20_S1几何字段审查报告.md
2. 若可行:phi v3 小样本结果与代码修改清单
3. 若不可行:明确不可行原因与替代方案,不能含糊
```

---

## 5. 对用户当前路线的影响

这个 S1 几何字段任务可以和当前训练并行,但它不应阻塞 Stage1.5 A 架构的决策。

推荐优先级:

```text
P0: 拍板 Stage1.5 A 路线
P1: 训练/改造 A 路线柱1+3证据
P1 并行: S1 metadata audit,判断 asc/desc + incidence 能否进 phi v3
P2: 若可行,把 S1 几何字段接入 phi 与 decoder 条件
P3: DEM/LULC/state head 与 Stage2 动力学
```

---

## 6. 参考来源

- Sentinel-1 产品结构与 annotation XML: [Copernicus SentiWiki S1 Products](https://sentiwiki.copernicus.eu/web/s1-products)
- Sentinel-1 incidence angle 来自 annotation geolocation grid 的公开说明: [Google Earth Engine COPERNICUS/S1_GRD](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD)
- Sentinel-1 `localIncidenceAngle` 平台字段说明: [Sentinel Hub Sentinel-1 GRD docs](https://docs.sentinel-hub.com/api/latest/data/sentinel-1-grd/)
- Sentinel-2 角度元数据示例: [Sentinel Hub angle metadata FAQ](https://www.sentinel-hub.com/faq/how-can-i-access-meta-data-information-sentinel-2-l2a/)
- SSL4EO-S12-v1.1 数据模态说明: [Hugging Face SSL4EO-S12-v1.1](https://huggingface.co/datasets/embed2scale/SSL4EO-S12-v1.1)
