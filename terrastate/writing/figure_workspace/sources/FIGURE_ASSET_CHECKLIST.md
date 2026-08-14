# TerraState Figure 1–2 真实素材清单与交付规范

## 0. 当前结论

本地审计未发现可直接用于新版 Figure 1/2 的、具有完整 provenance 的逐样本遥感预测图。重新设计后的Figure 1不再要求展示Q2/Q3逐样本输出，只需要少量真实历史EO和可选的真实预测图；Panel (c)使用冻结聚合证据支持结果含义，不展示详细数值。

因此：

- 蓝图已经可施工；
- 真实案例图仍需由作者/证据会话从冻结评估缓存导出；
- 若缓存不存在，必须由总控决定是否允许对冻结 checkpoint 做一次纯导出式前向；本图表会话不自行重跑评估；
- 不得以渐变色块、随机张量、旧图截图或手工绘制的“遥感图”填充。

## 1. 资产总表

状态说明：

- `AVAILABLE`：本地已存在且来源可追溯；
- `MISSING`：未找到，最终制图前必须补齐；
- `OPTIONAL`：可删，不得用伪造资产顶替。

| ID | 用途 | 必须内容 | 必须来自 | 当前状态 | 最终建议规格 |
|---|---|---|---|---|---|
| F1-A00 | Fig1(a)典型动作条件WM | scene/latent state/action/rollout原创矢量图标 | 作者绘制 | AVAILABLE AS ABSTRACT | 不用汽车或机器人照片 |
| F1-A01 | Fig1(a)稀疏EO历史 | 2–3帧Past EO RGB+云掩膜 | 真实数据样本 | MISSING | 每帧原生128×128无损PNG |
| F1-A02 | Fig1(a)未来天气符号 | temperature/rain/wind或天气序列带 | 可抽象；若画曲线则来自真实输入 | OPTIONAL | 不作结果证据 |
| F1-A03 | Fig1(a)未来EO | observed future EO/NDVI | 真实数据样本 | OPTIONAL | 无真实图时用无图槽位 |
| F1-A04 | Fig1(a)两类状态图标 | latent state与unobserved Earth-surface state抽象张量 | 作者绘制 | AVAILABLE AS ABSTRACT | 不得称物理地图或predictive state |
| F1-A05 | Fig1(a)验证带 | output评分尺、state/forcing探针问号 | 作者绘制 | AVAILABLE AS ABSTRACT | 不用对勾，避免被误读为预测正确 |
| F1-B01 | Fig1(b)历史上下文 | 2帧真实EO，可复用A01；天气/静态层只露窄标签 | 真实数据样本 | MISSING | 128×128，固定crop |
| F1-B02 | Fig1(b)TerraState forecast | 一张真实完整预测 | 冻结TerraState query | OPTIONAL | 优先与A03同cube/crop/horizon；无则用无图框 |
| F1-B03 | Fig1(b)状态图标 | `z_t`与`z_{t+h}`抽象张量 | 作者绘制 | AVAILABLE AS ABSTRACT | 同一视觉语言 |
| F1-B04 | Fig1(b)天气选择器 | actual/donor/mean三条标注轨迹 | 可抽象；若画数值则来自冻结Q3输入 | AVAILABLE AS ABSTRACT | 只进入T |
| F1-B05 | Fig1(b)context-only旁路 | 细灰线、`b_h`框和合并点 | 作者绘制 | AVAILABLE AS ABSTRACT | Q2断点必须在`r_h`分支，不得删掉整个forecast |
| F1-B06 | Fig1(b)`b_h/r_h`空间图 | 可选的真实context/state贡献图 | 同一冻结TerraState query | OPTIONAL | 无真实输出时只画符号框，严禁伪热图 |
| F1-C01 | Fig1(c)Q1–Q3结果含义 | 三条无数字结果摘要 | 冻结Q1–Q3记录 | AVAILABLE | Q3限定evaluated matched stratum；不写SOTA或普适定义 |
| F2-A01 | Fig2输入EO | 3帧Past EO | 真实数据样本 | MISSING | 与方法案例同cube |
| F2-A02 | Fig2 cloud mask | 至少1帧有效/云mask | 真实输入mask | MISSING | 二值PNG |
| F2-A03 | Fig2 past weather | 真实历史天气曲线 | 同一cube输入 | MISSING | CSV+渲染SVG |
| F2-A04 | Fig2 static geography | DEM/静态地理缩略图 | 同一cube输入 | MISSING | 16-bit源+PNG预览 |
| F2-B01 | Fig2 `z_t` | 抽象tensor即可 | 作者绘制 | AVAILABLE AS ABSTRACT | 不得称物理地图 |
| F2-C01 | Fig2 future weather | actual未来天气曲线 | 同一query输入 | MISSING | CSV+渲染SVG |
| F2-C02 | Fig2 donor/mean weather | Q3替换曲线 | 同一Q3 query | MISSING | 与C01同轴 |
| F2-C03 | Fig2 `z_{t+h}` | 抽象tensor即可 | 作者绘制 | AVAILABLE AS ABSTRACT | 4×4或6×6 glyph |
| F2-D01 | Fig2 `b_h` | context-only forecast地图 | 冻结TerraState query | MISSING | 原始float+PNG |
| F2-D02 | Fig2 `r_h` | state contribution有符号地图 | 同一query | MISSING | 原始float+发散色标PNG |
| F2-D03 | Fig2 `y_hat` | `b_h+r_h`完整预测 | 同一query | MISSING | 原始float+PNG |
| F2-E01 | Fig2预测序列 | 建议h=5/10/20预测NDVI | 同一冻结query | MISSING | 3张原生128×128 |
| F2-E02 | Fig2观测序列 | 对应horizon真实NDVI target | 评测数据 | MISSING | 同crop/mask/色标 |
| F2-T01 | Fig2 future EO target | 截至t+20的观测EO序列，future weather置零 | 训练样本或同案例 | MISSING | 可用1–2张缩略图 |
| F2-T02 | Fig2 teacher输出 | 仅当展示teacher热图时需要 | 冻结teacher | OPTIONAL | 无则只画模块框 |
| F2-T03 | Fig2 `z*_{t+20}` | 抽象tensor即可 | 作者绘制 | AVAILABLE AS ABSTRACT | 标target，不称观测图 |

## 2. 已冻结聚合数据

可用于核对 Figure 1 Panel (c)结果含义的现成数据文件：

`TerraState_AAAI27/figure_workspace/data/fig3_aggregate_effects.csv`

其来源为：

- `TerraState_AAAI27/evidence_workspace/raw/release/val_q2_state_contract_exclusive.json`
- `TerraState_AAAI27/evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json`
- `TerraState_AAAI27/evidence_workspace/raw/release/q3_extreme_state_audit.json`

使用规则：

- Q2只能使用 paired mean \(\Delta R^2\) 与对应 paired bootstrap CI；
- Q3只能使用 control-minus-actual endpoint loss 与对应 geographic-cluster CI；
- split 名若出现，统一写 `Validation` 与 `OOD-t`；
- 不得把 official dataset delta 与 paired CI 混画；
- 不从单个展示案例反推聚合统计；
- 当前Figure 1不建议画具体estimate或CI，只使用经冻结证据支持的方向性短句。

## 3. 真实案例选择规则

Figure 1只需要少量输入/输出视觉锚点。若决定放真实预测图：

1. Panel (a)的动作条件世界模型使用原创抽象场景，不需要也不应与EO样本作性能比较。
2. EO历史与future EO若使用真实图，优先按数据条件选择：
   - 有效植被覆盖充分；
   - 终点有效像素比例达到评测要求；
   - 历史序列具有可辨认空间结构；
   - 天气记录完整。
3. 先记录候选`cube_id`和选择理由，再查看预测图。
4. Panel (a)不再需要output-only基线预测；不要为动作条件世界模型或EO世界模型伪造模型输出。
5. Panel (c)只呈现冻结证据支持的结果含义，不用单个案例支持总体结论。

## 4. 每个导出包必须附带的 provenance

建议每个案例旁生成同名 JSON，至少包含：

```json
{
  "figure_asset_id": "F1-B02",
  "cube_id": "REQUIRED",
  "split": "Validation_or_OOD-t",
  "checkpoint_path_or_id": "REQUIRED",
  "checkpoint_sha256": "REQUIRED",
  "evaluation_record": "REQUIRED",
  "evaluator_commit": "IF_AVAILABLE",
  "query_type": "output_only_baseline_or_terrastate_full_or_intervention",
  "horizon": 20,
  "history_dates": ["REQUIRED"],
  "target_date": "REQUIRED",
  "weather_condition": "actual_or_matched_donor_or_normalized_mean",
  "donor_cube_id": "REQUIRED_FOR_DONOR",
  "mask_policy": "REQUIRED",
  "ndvi_display_range": ["REQUIRED_MIN", "REQUIRED_MAX"],
  "rgb_band_mapping": "REQUIRED_FOR_RGB",
  "rgb_stretch": "REQUIRED_FOR_RGB",
  "source_array_sha256": "REQUIRED",
  "rendered_png_sha256": "REQUIRED"
}
```

不得只交PNG而没有cube、checkpoint、条件和horizon信息。

## 5. 数值一致性验收

### 5.1 Figure 2闭合

对展示的每个有效像素验证：

\[
\widehat y_{t+h}=b_h+r_h.
\]

需要在资产导出报告中记录：

- 最大绝对误差；
- 平均绝对误差；
- 有效像素数；
- 允许误差阈值。

若误差超过正常浮点舍入范围，不得进入图。

### 5.2 Q2同条件检查

Full、state removal、`T→I` 必须一致：

- cube和split；
- history、past weather和static geography；
- future weather；
- checkpoint；
- mask与horizon。

唯一变化：

- state removal：闭合时令 `s=0`；
- `T→I`：只将 `T` 替换为 identity。

### 5.3 Q3同条件检查

actual、matched donor、normalized mean 必须一致：

- cube、history和由其得到的 \(z_t\)；
- static geography、horizon、readout和checkpoint；
- target与mask。

唯一变化是进入 `T` 的 future-weather path。

## 6. 图像与色标规范

### 6.1 NDVI

- 输出无损PNG，同时保留原始 float 数组；
- Full、两种Q2干预、三种Q3天气输出、target共用统一NDVI显示范围；
- 图例在整张图中只出现一次；
- 不对每张图单独做min-max归一化；
- invalid/cloud像素统一浅灰并用同一mask。

### 6.2 状态贡献 \(r_h\)

- 保留有符号值；
- 使用色盲友好的发散色标，中心严格为0；
- 图例写 `state contribution r_h`，不能写 `predicted NDVI`；
- 若对显示范围做对称截断，记录阈值和截断比例。

### 6.3 RGB

- 记录可见光band mapping；
- 同一时间序列共用拉伸参数；
- 不进行天空替换、锐化、生成式补云或伪彩增强；
- 如果某帧云量高，应同时展示真实mask，不挑掉困难帧。

### 6.4 天气微型曲线

- 源数据保留CSV；
- 三种Q3条件使用相同变量、时间坐标和纵轴；
- 最多选2–3个读者可理解的变量；选择标准在渲染前固定；
- normalized mean在标准化空间为零时，标签仍写 `normalized mean`，不写 `no weather`。

## 7. 裁剪与最终放置尺寸

| 素材 | 原始建议 | Figure 1放置 | Figure 2放置 | 裁剪 |
|---|---|---:|---:|---|
| EO/NDVI minicube | 原生128×128或更高 | 0.42–0.50 in | 0.36–0.44 in | 1:1，同一case固定窗口 |
| cloud mask | 与EO同分辨率 | 可省 | 0.24–0.30 in | 与EO像素对齐 |
| DEM | 与cube对齐 | 不用 | 0.28–0.34 in | 同空间范围 |
| weather strip | 矢量SVG | 高0.12–0.16 in | 高0.14–0.18 in | 同时间轴 |
| state tensor | 原生矢量 | 0.30–0.38 in | 0.42×0.52 in | 非真实空间裁剪 |
| `r_h` | 原始float+PNG | 不用 | 0.40–0.44 in | 与target逐像素对齐 |

原生128像素在300 dpi下对应约0.427英寸。若放置更大，应采用最近邻整数倍显示，不能使用AI超分。

## 8. 允许的抽象元素

以下不要求从模型中导出：

- `q/P/T/O`模块框；
- `z_t`、`z_{t+h}`、`z^*_{t+20}`的抽象张量glyph；
- 加法节点、切口、虚线干预端口；
- teacher与target encoder的模块框。

要求：

- 抽象状态张量必须与真实EO/NDVI图有明显边框或纹理差异；
- 标签必须明确为 `predictive state` 或 `future-state target`；
- 不得给抽象张量套NDVI色标；
- 不得把随机激活热图描述为模型学到的空间语义。

## 9. 禁止替代方案

- 用旧Revision 2 SVG中的彩色网格替代真实输出；
- 从EO-WM或AAAI锚点论文截图；
- 使用图库卫星图、Google Earth截图或无许可证网络图；
- 用随机噪声、插值、手绘差值模拟干预输出；
- 从不同cube拼接Full、removal、`T→I`；
- 为使差异明显而给每张输出单独调色；
- 省略matched donor ID；
- 在没有逐样本输出的情况下声称展示“representative effect”；
- 重跑评估后覆盖冻结聚合结果。

## 10. 交付目录建议

真实素材获得授权后，建议只在figure workspace内新建：

```text
figure_workspace/
└── assets/
    ├── q2_case_<cube_id>/
    │   ├── history_rgb_t*.png
    │   ├── full_h20.npy
    │   ├── full_h20.png
    │   ├── state_removal_h20.npy
    │   ├── state_removal_h20.png
    │   ├── T_to_I_h20.npy
    │   ├── T_to_I_h20.png
    │   ├── target_h20.npy
    │   ├── target_h20.png
    │   └── provenance.json
    ├── q3_case_<cube_id>/
    │   ├── weather_actual.csv
    │   ├── weather_matched_donor.csv
    │   ├── weather_normalized_mean.csv
    │   ├── prediction_actual_h20.*
    │   ├── prediction_matched_donor_h20.*
    │   ├── prediction_normalized_mean_h20.*
    │   ├── target_h20.*
    │   └── provenance.json
    └── method_case_<cube_id>/
        ├── input_*
        ├── b_h20.*
        ├── r_h20.*
        ├── prediction_h*.*
        ├── target_h*.*
        └── provenance.json
```

`*`表示同时保留原始数组和无损预览；不得覆盖论文现有图源。

## 11. 最终素材验收清单

Figure 1：

- [ ] (a) 使用action-conditioned WM与weather-driven EO WM的对齐路径，不写output-only对比；
- [ ] (a) 动作条件WM使用原创中性场景，不复制EO-WM汽车/道路图形；
- [ ] (a) EO路径的future weather只进入weather-conditioned transition；
- [ ] (a) 若放EO图，必须来自真实样本；无真实图时使用无图槽位；
- [ ] (b) `z_t`明确为history-only state；
- [ ] (b) 状态路径干预指向state contribution，天气干预只指向`T`的天气端口；
- [ ] (b) 未出现teacher、KD、future-state target或训练阶段；
- [ ] (c) Q1为prerequisite、Q2为defining core、Q3为external-forcing grounding；
- [ ] (c) 三条结果含义来自冻结Q1–Q3证据，不写详细数字；
- [ ] caption明确本文契约不是世界模型的唯一普适定义。

Figure 2：

- [ ] Past EO、mask、weather、static geography均为真实同case输入；
- [ ] `b_h`、`r_h`、`\widehat y`来自同一query；
- [ ] 数值检查通过 `b_h+r_h=\widehat y`；
- [ ] `r_h`使用零中心发散色标；
- [ ] future weather只进入`T`；
- [ ] observed future不进入推理路径；
- [ ] teacher/future EO target明确为training only；
- [ ] 抽象状态未伪装成可解释物理地图。

通用：

- [ ] 每个真实图有provenance JSON；
- [ ] 所有原始数组与渲染图有SHA-256；
- [ ] 所有case ID、split、horizon、checkpoint已锁定；
- [ ] 不含外部论文截图或无来源图片；
- [ ] 未修改`main.tex`、训练/评测代码或实验结果原文件。
