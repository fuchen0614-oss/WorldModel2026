# Figure 2 Asset Checklist

## 1. 原则

Figure 2 可以混合两类素材：

1. **真实数据素材**：EO图、mask、天气曲线、静态地图、预测图；
2. **原创抽象素材**：网络块、token墙、状态张量、箭头、加法节点、干预端口。

真实数据素材必须来自本项目数据或冻结模型输出；原创抽象素材可以直接在 PPT 中绘制。不得复制外部论文的图像、网络模块或截图。

## 2. 资产总表

| ID | 区块 | 素材 | 类型 | 必须性 | 推荐形式 | 来源要求 |
|---|---|---|---|---|---|---|
| F2-A01 | (a) | 历史EO序列 | 真实 | 必须 | 3–4张重叠方形缩略图 | 同一cube、同一空间范围 |
| F2-A02 | (a) | valid/cloud mask | 真实 | 推荐 | 黑白或灰度小图 | 与A01像素对齐 |
| F2-A03 | (a) | 历史天气条带 | 真实或抽象 | 推荐 | 2–3条小曲线/色带 | 若为真实数据需同一cube |
| F2-A04 | (a) | land cover | 真实 | 推荐 | 分类色小地图 | 与A01同空间范围 |
| F2-A05 | (a) | terrain/geography | 真实或抽象 | 可选 | DEM或地理网格 | 记录来源 |
| F2-A06 | (a)/(c) | 未来天气条带 | 真实或抽象 | 必须 | 温度/降水/辐射三层时间带 | 若为真实曲线需同一query |
| F2-B01 | (b) | patch/token输入网格 | 抽象 | 必须 | 4×4矢量方块 | PPT原创 |
| F2-B02 | (b) | history encoder q | 抽象 | 必须 | 3–4层紧凑网络墙 | PPT原创 |
| F2-B03 | (b) | context feature墙 | 抽象 | 必须 | 薄token墙 | PPT原创 |
| F2-B04 | (b) | state projector P | 抽象 | 必须 | 梯形/窄MLP | PPT原创 |
| F2-B05 | (b) | z_t状态张量 | 抽象 | 必须 | 4×4或6×6张量glyph | PPT原创，不套NDVI色标 |
| F2-B06 | (b)/(d) | b_h上下文预测 | 真实 | 推荐 | 单帧或薄序列 | 冻结TerraState同一query |
| F2-C01 | (c) | Shared transition T | 抽象 | 必须 | 大圆角状态–天气交互模块 | PPT原创 |
| F2-C02 | (c) | geography g图标 | 抽象或真实 | 推荐 | 地图针/小地理网格 | 避免图库截图 |
| F2-C03 | (c) | horizon h图标 | 抽象 | 必须 | 时间轴/时钟 | PPT原创 |
| F2-C04 | (c) | z_t+h状态张量 | 抽象 | 必须 | 与B05同形、纹理变化 | PPT原创 |
| F2-C05 | (c) | 天气干预端口 | 抽象 | 推荐 | 三路汇流到T | PPT原创 |
| F2-D01 | (d) | State readout O | 抽象 | 必须 | 窄decoder/漏斗 | PPT原创 |
| F2-D02 | (d) | r_h状态贡献 | 真实 | 推荐 | 零中心发散热图 | 冻结TerraState同一query |
| F2-D03 | (d) | 加法节点 | 抽象 | 必须 | 圆形⊕ | PPT原创 |
| F2-D04 | (d) | 最终预测序列 | 真实 | 必须 | h=5/10/20三帧 | 冻结TerraState同一query |
| F2-D05 | (d) | observed future reference | 真实 | 可选 | 一张小参考图 | 只作reference，不接入推理 |
| F2-D06 | (d) | 状态路径干预端口 | 抽象 | 推荐 | r_h→⊕上的可断开节点 | PPT原创 |

## 3. 最小可施工版本

若暂时没有完整真实导出，仍可先完成蓝图/PPT骨架：

- F2-A01：使用已确认来源的历史EO缩略图；
- F2-A06：使用明确标注为“示意变量类别”的抽象天气条带；
- F2-B01–B05、F2-C01–C05、F2-D01、F2-D03、F2-D06：全部用原创矢量；
- F2-D04：保留三个带标签的真实输出槽位；
- F2-B06、F2-D02：保留槽位，不使用随机热图填充。

槽位文本可写：

```text
real model output
asset pending
```

该文字只用于施工版，正式论文图中必须删除。

## 4. 推荐寻找或导出的具体图像

### 4.1 输入端

优先选择一个：

- 植被空间结构清楚；
- 云量不过高但包含真实mask；
- 历史帧变化可辨；
- future weather记录完整；
- OOD-t预测有效像素充分；
- 不按“模型效果最好”进行事后挑选。

建议导出：

```text
history_rgb_or_ndvi_t-3.png
history_rgb_or_ndvi_t-2.png
history_rgb_or_ndvi_t-1.png
history_rgb_or_ndvi_t.png
valid_mask_t.png
landcover.png
terrain.png
past_weather.csv
future_weather.csv
```

### 4.2 输出端

同一query导出：

```text
context_forecast_h20.npy/png
state_contribution_h20.npy/png
prediction_h5.npy/png
prediction_h10.npy/png
prediction_h20.npy/png
target_h20.npy/png            # optional reference
```

必须检查：

\[
\widehat y_{t+h}=b_h+r_h.
\]

建议记录最大绝对闭合误差与平均绝对闭合误差。

## 5. 天气条带

最多展示三个直观变量类别：

- temperature；
- precipitation；
- radiation。

如果使用抽象条带：

- 不标具体数值；
- 图注或资产记录说明其只是变量类别示意；
- 不声称来自某一极端事件。

如果使用真实曲线：

- actual、matched donor、normalized mean使用同一时间轴与纵轴；
- 保存CSV；
- 记录cube、donor、时间范围和归一化定义；
- normalized mean 不写成 `no weather`。

## 6. 状态张量glyph

`z_t`、`z_{t+h}`、`z^*_{t+H}`可以人工绘制，但必须满足：

- 相同网格尺寸；
- 使用抽象配色；
- 不采用NDVI/温度/降水色标；
- 不写“physical state map”；
- 不暗示单个通道具有已验证的物理语义；
- `z_{t+h}`只通过颜色/纹理变化表示“已更新”；
- `z^*`使用灰紫色并明确为target。

## 7. Provenance记录

每组真实图像建议附一个JSON：

```json
{
  "figure": "Figure 2",
  "cube_id": "REQUIRED",
  "split": "Validation_or_OOD-t",
  "checkpoint_sha256": "REQUIRED_FOR_MODEL_OUTPUT",
  "horizons": [5, 10, 20],
  "history_dates": ["REQUIRED"],
  "future_dates": ["REQUIRED"],
  "mask_policy": "REQUIRED",
  "weather_fields_displayed": ["temperature", "precipitation", "radiation"],
  "ndvi_display_range": ["REQUIRED_MIN", "REQUIRED_MAX"],
  "source_array_sha256": {
    "context_forecast": "REQUIRED",
    "state_contribution": "REQUIRED",
    "prediction_h20": "REQUIRED"
  }
}
```

## 8. 图像与色标

### NDVI与预测

- 所有预测和reference使用相同显示范围；
- invalid/cloud像素统一浅灰；
- 不对每张图单独min-max；
- 原始float数组与PNG同时保留；
- 不使用AI超分。

### r_h

- 必须使用有符号值；
- 发散色标中心固定为0；
- 单独标注 `State contribution r_h`；
- 不与NDVI共用顺序色标。

### RGB

- 同一历史序列共用拉伸参数；
- 记录band mapping；
- 不做生成式补云或锐化；
- 不能使用外部卫星图库代替项目样本。

## 9. PPT矢量素材建议

以下均适合直接用PPT形状构建：

- token墙：重复小矩形并组合；
- encoder：3–4个错位圆角矩形；
- projector：梯形；
- state tensor：4×4小方格；
- transition：大圆角框+内部两路token交互；
- readout：漏斗或逐渐收窄的网络块；
- weather strip：三条细曲线/色带；
- horizon：简化时间轴；
- intervention port：小空心圆或可断开节点；
- addition：圆形加号；
- forecast stack：三张等尺寸图像卡片。

不要使用复杂神经网络图库图标。统一由简单形状组成，更容易与论文风格匹配并保持可编辑。

## 10. 最终验收

- [ ] 所有真实图来自项目数据或冻结输出；
- [ ] 输入和输出若展示同一案例，则cube、空间范围和时间信息一致；
- [ ] `b_h`、`r_h`和`\widehat y`来自同一query；
- [ ] 预测闭合检查通过；
- [ ] future weather只在视觉上进入`T`；
- [ ] observed future若出现，只作为不接入推理路径的reference；
- [ ] 抽象状态没有伪装成物理地图；
- [ ] 外部参考论文只用于布局，不复制其素材；
- [ ] 所有图内文本来自`FIGURE_2_TEXT_COPY.md`；
- [ ] 正式图中不存在`asset pending`；
- [ ] PPTX、PDF和SVG版本均保留；PPTX/SVG可编辑，PDF保持矢量清晰；
- [ ] 缩小到AAAI双栏宽度后仍可辨认输入、状态、转移、读出和输出。
