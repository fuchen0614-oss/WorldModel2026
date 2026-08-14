# Figure 2 精准施工蓝图：TerraState连续方法架构

> 状态：本文件取代此前的 Figure 2 蓝图；旧版渲染图仅视为归档草稿，不再作为施工依据。

## 1. Figure 2 的唯一任务

Figure 2 回答：

> **TerraState如何把多模态历史观测转化为显式预测状态，由未来天气驱动共享状态转移，并把状态贡献闭合到最终植被预测？**

它在全文中的分工是：

```text
Figure 1：为什么需要可检验的EO世界模型，以及用什么证据检验
Figure 2：TerraState具体如何实现这种世界模型
Figure 3：冻结实验结果是否支持这些主张
```

Figure 2 必须是一条连续的、从左到右推进的完整方法路径，而不是散开的训练流程、工程阶段或若干彼此独立的小示意图。

本图采用明确的视觉优先级：

```text
核心模型与预测闭合：约90%的视觉注意力
Q2/Q3干预接口：最多约10%的视觉注意力
```

Q2/Q3很重要，但它们在Figure 2中只是证明模型“可检验”的小型接口，不是模型主体：

- Figure 2的主体必须是`q → P → z_t → T → z_{t+h} → O → r_h`以及
  `b_h+r_h → forecast`；
- Q2只在`r_h → ⊕`上保留一个小断点；
- Q3只在`future weather → T`上保留一个小替换口；
- 如果空间不足，优先删除Q2/Q3的解释小字，不能压缩核心模型和最终预测闭合。

## 2. 参考图的借鉴原则

### 2.1 借鉴 Image #1、Image #3 和 EO-WM Figure 2

借鉴：

- 顶部连续阶段条；
- 左侧真实输入图层；
- 中部用视觉模块展开关键计算；
- 右侧用真实输出序列闭合；
- 一个区域推动下一个区域；
- 用少量网络方块、张量墙、天气条带和图像缩略图表达计算；
- 只保留连续的主推理路径，不在本图展开训练监督。

### 2.2 有限借鉴 Image #2

只借鉴：

- 清楚的彩色分区；
- 每个区域有明确标题；
- 箭头穿越分区、形成连续阅读顺序。

不借鉴：

- 手绘边框；
- 过多卡通图标；
- 大段斜体说明；
- 密集公式和装饰性网络节点；
- 与方法无关的品牌或模型图标。

### 2.3 TerraState自己的视觉识别

Figure 2 的中心视觉对象不是普通网络框，而是：

1. 历史观测形成的 `z_t`；
2. 未来天气只进入共享转移 `T`；
3. `z_t` 经 `T` 变为 `z_{t+h}`；
4. `O` 将未来状态读成状态贡献 `r_h`；
5. `r_h` 与上下文预测 `b_h` 相加形成最终预测。

## 3. 画布与区域比例

### 3.1 画布

- AAAI 双栏通栏；
- 推荐宽度：`7.0 in`；
- 推荐高度：`3.15–3.35 in`；
- 推荐施工比例：约 `2.15:1`；
- 不在图内放总标题，标题由论文 caption 承担；
- 图内只使用英文；本文件提供中文施工解释。

### 3.2 四个连续区块

| 区块 | 英文标题 | 相对宽度 | 7英寸下建议宽度 |
|---|---|---:|---:|
| (a) | Multimodal context | 19% | 1.33 in |
| (b) | History encoding & state construction | 25% | 1.75 in |
| (c) | Weather-conditioned shared dynamics | 31% | 2.17 in |
| (d) | State readout & forecast | 25% | 1.75 in |

区块之间不留大空白。使用浅色背景或细分隔线区分，但主箭头必须连续穿过四个区块。

### 3.3 垂直比例

| 垂直区域 | 高度 |
|---|---:|
| 顶部阶段条 | 9% |
| 主推理路径 | 84% |
| 图例与最小留白 | 7% |

Figure 2 不设置底部训练轨。冻结教师、未来状态目标和损失函数由方法正文说明，不进入主架构图。

### 3.4 最重要的层级：4个大块分别包住哪些小块

整张 Figure 2 **只有4个大块**。绘图时先画4个大背景框，再在每个背景框内部放置小块：

```text
Figure 2
│
├── 大块 A：Multimodal context / 多模态上下文
│   ├── A1 历史EO图片组
│   ├── A2 历史环境图片组
│   ├── A3 静态地理图片组
│   └── A4 未来天气条带
│
├── 大块 B：History encoding & state construction / 历史编码与状态构造
│   ├── B1 历史编码器 q
│   ├── B2 状态构造支路：Context features → P → z_t
│   └── B3 上下文预测支路：b_h
│
├── 大块 C：Weather-conditioned shared dynamics / 天气条件共享动力学
│   ├── C1 条件入口组：u_{t:t+h}、g、h
│   ├── C2 核心共享转移 T
│   ├── C3 演化后的状态 z_{t+h}
│   └── C4 天气干预小接口
│
└── 大块 D：State readout & forecast / 状态读出与预测
    ├── D1 状态读出支路：O → r_h
    ├── D2 预测融合：b_h + r_h
    ├── D3 最终植被预测图组
    └── D4 状态路径干预小接口（视觉上只占箭头附近的极小面积）

```

### 3.5 大块、小块和视觉元素如何区分

| 层级 | 怎么画 | 示例 |
|---|---|---|
| 大块 | 占据整段宽度的浅色背景区，有顶部英文标题 | A、B、C、D |
| 小块 | 大块内部的圆角白框、图片组或网络模块 | B1编码器、C2转移、D1读出 |
| 视觉元素 | 小块内部的图片、张量墙、曲线或图标，不再加独立大标题 | DEM图、NDVI图、天气曲线 |
| 干预接口 | 贴在箭头上的小开关或小端口，不能画成独立模块 | C4、D4 |

因此：

- `DEM图`不是一个小块，而是 A3“静态地理图片组”内部的一张图片；
- `温度/降水/辐射`不是三个小块，而是 A4“未来天气条带”内部的三个视觉通道；
- `Context features → P → z_t`共同组成 B2“状态构造支路”；
- `actual / matched donor / normalized mean`不是三个模型，而是 C4天气干预接口的三个替换选项；
- `h=5,10,20`不是三个模块，而是 D3最终预测图组中的三张输出图。

## 4. 全图快速草图

```text
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ (a) Multimodal context │ (b) History encoding & state │ (c) Weather-conditioned │ (d) Readout │
│                        │         construction          │     shared dynamics      │   & forecast │
│                        │                               │                          │              │
│ Past EO sequence ─────▶│ q ──┬──▶ context features ─▶ P ─▶ z_t ─▶ shared T ─▶ z_t+h ─▶ O ─▶ r_h ─┐
│ mask / past context ──▶│     │                              ▲                                   │
│ static geography ─────▶│     └──────── context forecast b_h ┼───────────────────────────────────┼─▶ ⊕ ─▶ ŷ
│                        │                                    │                                   │
│ Future weather strip ──────────────────────────────────────┘                                   │
│ geography + horizon h ─────────────────────────────────────┘                                   │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

阅读顺序只有一条：

```text
输入 → 历史编码 → 当前状态 → 天气驱动转移 → 未来状态 → 状态读出 → 预测闭合
```

### 4.1 给绘图同事的中英双语施工标注

施工蓝图中的每个节点统一采用：

```text
English label used in the final figure
中文解释（建议插入的图片或视觉元素）
```

中文行只用于绘图沟通，**正式论文图中删除中文，只保留英文**。

#### Panel (a)：输入素材

| 正式英文标签 | 中文施工解释与推荐插图 |
|---|---|
| `Historical Earth observations` | 历史地球观测（插入：同一地块连续3–4帧 Sentinel-2 RGB 或 NDVI 图，按 \(t-3,\ldots,t\) 叠放） |
| `Historical environmental context` | 历史环境上下文（插入：一张云/有效像素 mask + 一条简短历史天气条带） |
| `Static geographic attributes` | 静态地理属性（插入：土地覆盖图 + DEM地形图；没有真实DEM时使用简洁等高线图标） |
| `Future meteorological forcing` | 未来气象驱动（插入：温度曲线 + 降水柱 + 辐射色带组成的横向天气序列） |

#### Panel (b)：状态构造

| 正式英文标签 | 中文施工解释与推荐视觉 |
|---|---|
| `History encoder q` | 历史编码器 \(q\)（插入：3–4层紧凑网络块或图像 patch 进入 token 墙的示意） |
| `Context features` | 上下文特征（插入：薄型彩色 token 方块墙） |
| `State projector P` | 状态投影器 \(P\)（插入：梯形漏斗或两层小型 MLP 模块） |
| `History-only predictive state z_t` | 仅由历史构造的预测状态 \(z_t\)（插入：4×4/6×6抽象张量格 + 小时钟；不能画成真实地图） |
| `Context-only forecasts b_{1:H}` | 仅由上下文得到的预测 \(b_{1:H}\)（插入：浅蓝色预测缩略图序列或薄型输出带） |

#### Panel (c)：天气驱动的共享动力学

| 正式英文标签 | 中文施工解释与推荐视觉 |
|---|---|
| `Current predictive state z_t` | 当前预测状态 \(z_t\)（沿用上一块相同形状的抽象张量格） |
| `Geographic context g` | 地理上下文 \(g\)（插入：小型土地覆盖/DEM图标，不再放大展示） |
| `Forecast horizon h` | 预测时距 \(h\)（插入：小型时钟或 \(h=1,\ldots,H\) 时间刻度） |
| `Shared transition T` | 共享转移 \(T\)（插入：状态 token 与天气 token 交互的简化注意力/门控网格） |
| `Evolved predictive state z_{t+h}` | 演化后的预测状态 \(z_{t+h}\)（与 \(z_t\) 外形相同，但内部颜色轻微变化） |
| `Weather intervention` | 天气干预接口（插入：三选一小端口，`actual / matched donor / normalized mean`） |

#### Panel (d)：读出与预测

| 正式英文标签 | 中文施工解释与推荐插图 |
|---|---|
| `State readout O` | 状态读出器 \(O\)（插入：窄型解码器或漏斗形网络模块） |
| `State contribution r_h` | 状态贡献 \(r_h\)（优先插入：真实导出的零中心发散色贡献图；没有时保留空图槽，不使用随机热力图） |
| `Forecast fusion` | 预测融合（插入：圆形加号节点，旁边写 \(\widehat y_{t+h}=b_h+r_h\)） |
| `Vegetation forecast` | 植被预测（插入：同一地块 \(h=5,10,20\) 的3张真实 NDVI 预测图） |
| `State-path intervention` | 状态路径干预接口（插入：位于 \(r_h\rightarrow\oplus\) 上的可断开小开关） |

### 4.2 一眼可照着画的双语版线框

图例：

```text
[图片组]：插入真实图片或数据图
[网络模块]：用PPT方块/漏斗/网格绘制
[抽象状态]：用彩色张量格绘制，不能伪装成真实地图
[小接口]：贴在箭头上的小开关，不占独立区域
```

最外层先画四个大块：

```text
┌─────────────┐   ┌────────────────┐   ┌────────────────┐   ┌───────────────┐
│ (a)         │   │ (b)            │   │ (c)            │   │ (d)           │
│ Multimodal  │ → │ History        │ → │ Weather-       │ → │ State readout │
│ context     │   │ encoding &     │   │ conditioned    │   │ & forecast    │
│ 多模态上下文 │   │ state building │   │ shared dynamics│   │ 状态读出与预测 │
└─────────────┘   │ 历史编码与状态构造│   │ 天气条件共享动力学│   └───────────────┘
                  └────────────────┘   └────────────────┘
```

然后在四个大块内部按照下面的层级放置小块：

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ 大块 A / PANEL (a)                                                          │
│ Multimodal context                                                          │
│ 多模态上下文                                                                 │
│                                                                              │
│ A1 [图片组 / IMAGE GROUP]                                                    │
│     Historical Earth observations                                           │
│     历史地球观测                                                             │
│     插图：同一地块3–4帧真实 Sentinel-2 RGB 或 NDVI，错位叠放，标 t-3…t       │
│                                                                              │
│ A2 [图片组 / IMAGE GROUP]                                                    │
│     Historical environmental context                                        │
│     历史环境上下文                                                           │
│     插图：1张黑白云/有效像素 mask + 1条简短历史天气曲线                      │
│                                                                              │
│ A3 [图片组 / IMAGE GROUP]                                                    │
│     Static geographic attributes                                            │
│     静态地理属性                                                             │
│     插图：1张土地覆盖图 + 1张 DEM地形图/等高线图                             │
│                                                                              │
│ A4 [图片条带 / IMAGE STRIP]                                                  │
│     Future meteorological forcing u_{t:t+h}                                  │
│     未来气象驱动                                                             │
│     插图：温度折线 + 降水柱 + 辐射色带，组合成一条横向天气序列               │
│                                                                              │
│ 箭头：A1+A2+A3 ─→ B1；A4跨过大块B，只进入C2                                 │
└──────────────────────────────────────────────────────────────────────────────┘

                                      ↓

┌──────────────────────────────────────────────────────────────────────────────┐
│ 大块 B / PANEL (b)                                                          │
│ History encoding & state construction                                      │
│ 历史编码与状态构造                                                          │
│                                                                              │
│ B1 [网络模块 / NETWORK MODULE]                                               │
│     History encoder q                                                       │
│     历史编码器 q                                                            │
│     画法：3–4个紧凑网络方块；左侧图像patch进入，右侧输出token                │
│                              │                                               │
│                 ┌────────────┴────────────┐                                  │
│                 ↓                         ↓                                  │
│ B2 [状态构造支路 / STATE BRANCH]    B3 [预测支路 / FORECAST BRANCH]         │
│     Context features → P → z_t           Context-only forecasts b_{1:H}     │
│     上下文特征→状态投影器→历史预测状态     仅由上下文得到的预测              │
│     画法：token墙→梯形漏斗→彩色张量格      插图：浅蓝预测缩略图/输出带       │
│                                                                              │
│ 箭头：B2的 z_t ─→ C2；B3的 b_h 绕过C，直接进入D2                            │
└──────────────────────────────────────────────────────────────────────────────┘

                                      ↓

┌──────────────────────────────────────────────────────────────────────────────┐
│ 大块 C / PANEL (c)                                                          │
│ Weather-conditioned shared dynamics                                        │
│ 天气条件共享动力学                                                          │
│                                                                              │
│ C1 [条件入口组 / CONDITION GROUP]                                            │
│     Future weather u_{t:t+h} + Geographic context g + Forecast horizon h    │
│     未来天气 + 地理上下文 + 预测时距                                         │
│     插图：A4天气条带 + 土地覆盖/DEM小图标 + 小时钟                           │
│                              │                                               │
│ B2的 z_t ────────────────────┼──────────────┐                                │
│                              ↓              │                                │
│ C2 [核心网络模块 / CORE MODULE]             │                                │
│     Shared transition T                     │                                │
│     共享状态转移 T                          │                                │
│     画法：状态token与天气token交互的注意力/门控网格                          │
│                              │                                               │
│                              ↓                                               │
│ C3 [抽象状态 / ABSTRACT STATE]                                               │
│     Evolved predictive state z_{t+h}                                        │
│     演化后的预测状态                                                        │
│     画法：与 z_t 同形的彩色张量格，内部颜色轻微变化                          │
│                                                                              │
│ C4 [小接口 / SMALL PORT]                                                     │
│     Weather intervention                                                    │
│     天气干预接口                                                            │
│     画法：贴在“天气→T”箭头上的小切换端口；                                   │
│           actual/donor/mean（真实天气/匹配供体/归一化均值）                  │
│                                                                              │
│ 箭头：C3的 z_{t+h} ─→ D1                                                    │
└──────────────────────────────────────────────────────────────────────────────┘

                                      ↓

┌──────────────────────────────────────────────────────────────────────────────┐
│ 大块 D / PANEL (d)                                                          │
│ State readout & forecast                                                    │
│ 状态读出与预测                                                              │
│                                                                              │
│ D1 [读出支路 / READOUT BRANCH]                                               │
│     State readout O → State contribution r_h                               │
│     状态读出器 O → 状态贡献 r_h                                             │
│     画法：窄型解码漏斗 → 真实零中心发散色贡献图                              │
│                                       │                                      │
│ B3的 b_h ─────────────────────────────┼──────────┐                           │
│                                       ↓          │                           │
│ D2 [融合节点 / FUSION NODE]                       │                           │
│     Forecast fusion: ŷ_{t+h}=b_h+r_h              │                           │
│     预测融合：上下文预测 + 状态贡献                │                           │
│     画法：圆形“⊕”节点，公式放在节点旁              │                           │
│                                       │                                      │
│                                       ↓                                      │
│ D3 [图片组 / IMAGE GROUP]                                                    │
│     Vegetation forecast                                                     │
│     植被预测                                                                │
│     插图：同一地块 h=5、h=10、h=20 的3张真实NDVI预测图                       │
│                                                                              │
│ D4 [小接口 / SMALL PORT]                                                     │
│     State-path intervention                                                 │
│     状态路径干预接口                                                        │
│     画法：贴在“r_h→⊕”箭头上的可断开小开关                                   │
└──────────────────────────────────────────────────────────────────────────────┘

```

### 4.3 补充线框一：先搭全图大块与跨块连线

这张线框只决定 A–D 四个大块如何排列和连接，不处理大块内部细节：

```text
┌───────────────────┐   history / 历史输入   ┌────────────────────────┐
│ A / PANEL (a)     │ ─────────────────────→ │ B / PANEL (b)          │
│ Multimodal context│                        │ History encoding &     │
│ 多模态上下文       │                        │ state construction     │
│                   │                        │ 历史编码与状态构造       │
└───────────────────┘                        └────────────────────────┘
       │ A4 future weather / 未来天气                │          │
       │                                             │ z_t      │ b_h
       │                                             │ 历史状态  │ 上下文预测
       │                                             ↓          │
       │                                  ┌────────────────────┐│
       └────────────────────────────────→ │ C / PANEL (c)      ││
          meteorological forcing          │ Weather-conditioned││
          气象驱动                         │ shared dynamics    ││
                                          │ 天气条件共享动力学  ││
                                          └────────────────────┘│
                                                   │ z_{t+h}     │
                                                   │ 演化状态     │
                                                   ↓             ↓
                                          ┌────────────────────────┐
                                          │ D / PANEL (d)          │
                                          │ State readout &        │
                                          │ forecast               │
                                          │ 状态读出与预测          │
                                          └────────────────────────┘
                                                       │
                                                       ↓
                                          Vegetation forecast / 植被预测

```

跨块实线只有五条：

```text
A1+A2+A3 → B1        历史观测、环境和地理信息进入历史编码器
A4 → C2              未来天气绕过B，只进入共享转移T
B2(z_t) → C2         历史状态进入共享转移T
C3(z_{t+h}) → D1     演化状态进入状态读出器O
B3(b_h) → D2         上下文预测绕过C，直接进入最终融合
```

### 4.4 补充线框二：大块 A 内部怎么画

```text
┌──────────────────────────────────────────────────────────────┐
│ A / PANEL (a)                                                │
│ Multimodal context                                           │
│ 多模态上下文                                                  │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ A1 Historical Earth observations                         │ │
│ │    历史地球观测                                           │ │
│ │    [IMAGE / 图片] [IMAGE / 图片] [IMAGE / 图片]           │ │
│ │       t-3              t-2              t                │ │
│ │    插图：同一地块3–4帧真实 Sentinel-2 RGB或NDVI           │ │
│ └──────────────────────────────────────────────────────────┘ │
│                           │                                  │
│ ┌─────────────────────────┴────┐  ┌────────────────────────┐ │
│ │ A2 Historical environmental │  │ A3 Static geographic   │ │
│ │    context                   │  │    attributes          │ │
│ │    历史环境上下文             │  │    静态地理属性         │ │
│ │ [cloud mask/云掩膜]           │  │ [land cover/土地覆盖]  │ │
│ │ [past weather/历史天气曲线]   │  │ [DEM/地形图]           │ │
│ └──────────────────────────────┘  └────────────────────────┘ │
│               │                          │                   │
│               └──────────┬───────────────┘                   │
│                          └──────── history / 历史输入 ─→ B1  │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ A4 Future meteorological forcing u_{t:t+h}               │ │
│ │    未来气象驱动                                           │ │
│ │ [temperature/温度] [precipitation/降水] [radiation/辐射] │ │
│ │    插图：折线              柱状条              色带       │ │
│ └──────────────────────────────────────────────────────────┘ │
│                          └──── future weather / 未来天气 ─→ C2│
└──────────────────────────────────────────────────────────────┘
```

关键空间关系：

- A1 放上半部，作为最大的真实图片组；
- A2 与 A3 在中部左右并排；
- A4 是底部横向长条，箭头直接跨向 C，不接 B；
- DEM 只位于 A3 内部。

### 4.5 补充线框三：大块 B 内部怎么画

```text
┌────────────────────────────────────────────────────────────────────┐
│ B / PANEL (b)                                                      │
│ History encoding & state construction                             │
│ 历史编码与状态构造                                                 │
│                                                                    │
│ A1+A2+A3 / 历史输入                                                │
│          │                                                         │
│          ↓                                                         │
│ ┌─────────────────────────┐                                       │
│ │ B1 History encoder q    │                                       │
│ │    历史编码器 q          │                                       │
│ │ [patches/图像块] → [network blocks/网络块] → [tokens/特征块]    │
│ └─────────────────────────┘                                       │
│          │                                                         │
│          ├───────────────────────────────┐                         │
│          ↓                               ↓                         │
│ ┌──────────────────────────────┐  ┌─────────────────────────────┐ │
│ │ B2 State-construction branch │  │ B3 Context-forecast branch │ │
│ │    状态构造支路               │  │    上下文预测支路           │ │
│ │                              │  │                             │ │
│ │ Context features             │  │ Context-only forecasts     │ │
│ │ 上下文特征                    │  │ b_{1:H}                    │ │
│ │ [token wall/特征方块墙]       │  │ 仅由上下文得到的预测        │ │
│ │          ↓                   │  │ [forecast strip/预测图带]  │ │
│ │ State projector P            │  └─────────────────────────────┘ │
│ │ 状态投影器P [funnel/漏斗]     │                    │             │
│ │          ↓                   │                    └─ b_h ─→ D2  │
│ │ Predictive state z_t         │                                  │
│ │ 历史预测状态 [tensor/张量格] │                                  │
│ └──────────────────────────────┘                                  │
│                │                                                   │
│                └────────────────────────────── z_t / 历史状态 ─→ C2│
└────────────────────────────────────────────────────────────────────┘
```

B 中只有一次主要分叉：

```text
q → B2状态支路 → z_t → C
q → B3预测支路 → b_h → D
```

### 4.6 补充线框四：大块 C 内部怎么画

```text
┌────────────────────────────────────────────────────────────────────┐
│ C / PANEL (c)                                                      │
│ Weather-conditioned shared dynamics                               │
│ 天气条件共享动力学                                                 │
│                                                                    │
│ A4 Future meteorological forcing                                  │
│    未来气象驱动 [weather strip/天气条带]                           │
│                         │                                          │
│                         ◇  C4 tiny weather-replacement port         │
│                            C4极小天气替换口                          │
│ ┌───────────────────────┴───────────────────────────────────────┐  │
│ │ C1 Conditioning inputs / 条件入口组                           │  │
│ │ [weather u/天气] + [geography g/地理] + [horizon h/预测时距] │  │
│ │                    [DEM icon/DEM小图]   [clock/时钟]           │  │
│ └───────────────────────┬───────────────────────────────────────┘  │
│                         │                                          │
│                         ↓                                          │
│ B2 z_t / 历史状态 ─→ ┌─────────────────────────────────────────┐  │
│                      │ C2 Shared transition T                  │  │
│                      │    共享状态转移 T                       │  │
│                      │ [state tokens/状态token]                │  │
│                      │          ×                              │  │
│                      │ [weather tokens/天气token]              │  │
│                      │ 画法：简化注意力或门控交互网格          │  │
│                      └───────────────────┬─────────────────────┘  │
│                                          ↓                        │
│                      ┌─────────────────────────────────────────┐  │
│                      │ C3 Evolved predictive state z_{t+h}    │  │
│                      │    演化后的预测状态                     │  │
│                      │ [abstract tensor/抽象彩色张量格]        │  │
│                      └───────────────────┬─────────────────────┘  │
│                                          └──── z_{t+h} ─→ D1      │
└────────────────────────────────────────────────────────────────────┘
```

注意：

- C2 是整张图视觉上最大的单个网络模块；
- C1 只是条件入口组，不要画成另一个大型模型；
- C4 是贴在天气箭头上的空心菱形或极小替换口，不是独立模块；
- 主实线路径只画`actual future weather`；`donor/mean`最多作为替换口旁的灰色小字，
  也可以完全交给caption和Figure 1；
- C 中不画循环 rollout。

### 4.7 补充线框五：大块 D 内部怎么画

```text
┌────────────────────────────────────────────────────────────────────────┐
│ D / PANEL (d)                                                          │
│ State readout & forecast / 状态读出与预测                               │
│                                                                        │
│ C3 Evolved state z_{t+h} / 演化状态                                    │
│             │                                                          │
│             ↓                                                          │
│    ┌───────────────────────┐                                           │
│    │ D1 State readout O    │                                           │
│    │    状态读出器O        │                                           │
│    │ [narrow funnel/窄漏斗]│                                           │
│    └───────────┬───────────┘                                           │
│                ↓                                                       │
│    ┌───────────────────────┐                                           │
│    │ State contribution r_h│                                           │
│    │ 状态贡献r_h           │                                           │
│    │ [signed map/真实贡献图│                                           │
│    │  or empty slot/或空槽]│                                           │
│    └───────────┬───────────┘                                           │
│                │ × D4 tiny state-path port / 极小状态路径断点           │
│                └──────────────────────┐                                 │
│                                       ↓                                │
│ B3 Context-only forecast b_h ───────→  ⊕  ─→ ŷ_{t+h}=b_h+r_h           │
│ B3上下文预测旁路                         预测闭合                        │
│                                       │                                │
│                                       ↓                                │
│                     ┌─────────────────────────────────────────────┐     │
│                     │ D3 Vegetation forecast / 植被预测           │     │
│                     │ [NDVI h=5] [NDVI h=10] [NDVI h=20]        │     │
│                     │ 同一地块、同一色标、真实冻结模型输出       │     │
│                     └─────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────────┘
```

Panel D的阅读顺序必须一眼可见：

```text
z_{t+h} → O → r_h
                    \
                     ⊕ → final vegetation forecast
                    /
              b_h ─
```

视觉权重建议：

| D区元素 | D区内部视觉权重 |
|---|---:|
| `O → r_h`状态读出支路 | 30% |
| `b_h+r_h`预测闭合与核心公式 | 30% |
| 最终植被预测图组 | 35% |
| D4状态路径干预小接口 | 不超过5% |

注意：

- D2不需要画成一个厚重的大网络框；加法节点和公式本身就是预测融合；
- D3必须是Panel D最直观的视觉落点，让读者看到模型最终预测了什么；
- D4只是`r_h → ⊕`线上的一个极小断点，不能单独占一张卡片；
- 如果没有真实\(r_h\)导出，保留标有`State contribution \(r_h\)`的空图槽，
  不使用随机发散色热图；
- 如果空间不足，D3可以由三张预测图缩为“一张主预测图 + h=5/10/20小标签”，
  但不能删除\(\widehat y_{t+h}=b_h+r_h\)。

### 4.8 绘图时的推荐顺序

```text
第1步：只画4个大背景框 A → B → C → D
第2步：按4.4–4.7分别画每个大块内部的小块
第3步：连接5条跨块实线
第4步：先确认D中的O→r_h、b_h+r_h与最终预测完整闭合
第5步：最后加入C4和D4两个极小接口
第6步：把图片槽替换为真实EO、mask、土地覆盖、DEM和NDVI预测图
```

## 5. 与真实模型严格一致的数据流

Figure 2 必须忠实表达以下计算：

\[
z_t=P(q(\text{history})),
\]

\[
b_h=q_{\mathrm{forecast}}(\text{history}),
\]

\[
z_{t+h}=T(z_t,u_{t:t+h},g,h),
\]

\[
r_h=O(z_{t+h}),
\]

\[
\widehat y_{t+h}=b_h+r_h.
\]

其中：

- `history` 可以包含历史 EO、历史环境上下文、掩膜和静态属性；
- `z_t` 不读取未来 EO，也不读取未来天气；
- `b_h` 是仅由历史信息得到的上下文预测；
- 未来天气 `u_{t:t+h}` 只能进入 `T`；
- `T` 是跨查询时距共享的天气条件转移；
- `O` 将转移后的状态读出为状态贡献；
- 最终输出是上下文预测与状态贡献之和。

Figure 2 不得把 `T` 画成循环 rollout，因为当前主张不是已证明的时序组合性；应画成一次共享的、由 `h` 条件化的状态转移。

## 6. Panel (a)：Multimodal context

### 6.1 本区块回答什么

**TerraState从哪些观测与驱动信息开始？**

### 6.2 视觉结构

区块内使用三个上下排列的视觉组：

```text
Past EO sequence
[t-3] [t-2] [t-1] [t]

Historical context
[cloud/valid mask] [weather strip]

Static geography
[land cover] [terrain/geography]
```

未来天气不要混在历史输入堆中。它应从 Panel (a) 下方开始形成一条独立的彩色时间带，跨过 Panel (b)，只进入 Panel (c) 的 `T`。

### 6.3 素材形式

#### Past EO sequence

- 使用 3–4 张同一 minicube 的真实 EO 或 NDVI 图；
- 轻微错位叠放，右下角标 `t-3 … t`；
- 若历史帧存在云，可叠加真实 mask，不手工移除；
- 不需要列出 Sentinel 波段名称。

#### Historical context

- 云/有效像素：一张小型黑白 mask；
- 历史天气：一条极简彩色时间带或 2–3 条小曲线；
- 不展开全部天气变量。

#### Static geography

- 一张土地覆盖缩略图；
- 一张地形或静态地理缩略图；
- 若没有可追溯真实素材，可退化为简洁矢量图标，不使用网络图库截图。

#### Future weather

- 一条从 Panel (a) 底部向右延伸的天气时间带；
- 最多显示温度、降水、辐射三个易懂视觉通道；
- 标签只写 `Future meteorological forcing`；
- 箭头终点只能是 `T`。

### 6.4 可直接使用的英文

面板标题：

> **(a) Multimodal context**

组标签：

> **Historical Earth observations**  
> **Historical environmental context**  
> **Static geographic attributes**  
> **Future meteorological forcing**

小标签：

> past EO  
> valid / cloud mask  
> past weather  
> land cover  
> terrain  
> \(u_{t:t+h}\)

### 6.5 箭头

1. Past EO → `q`；
2. historical context → `q`；
3. static attributes → `q` 或作为上下文输入；
4. future meteorological forcing 跨过 `q/P/z_t`，只进入 `T`；
5. geography `g` 和 horizon `h` 从下方进入 `T`。

## 7. Panel (b)：History encoding & state construction

### 7.1 本区块回答什么

**历史观测如何同时形成上下文预测和显式预测状态？**

### 7.2 主体结构

```text
historical inputs
       ↓
History encoder q
   ┌───┴─────────────────────┐
   │                         │
   ▼                         ▼
context forecast b_1:H    context features
                             │
                             ▼
                      State projector P
                             │
                             ▼
             History-only predictive state z_t
```

这是 Figure 2 中唯一的分叉：

- 上方细支路产生 `b_{1:H}`，横跨后续区块到最终加法节点；
- 中心粗支路经 `P` 形成 `z_t`，进入 `T`。

### 7.3 视觉形式

#### History encoder q

- 使用一组 3–4 个紧凑网络块；
- 输入侧是图像 patch/token 网格；
- 输出侧是特征方块墙；
- 不画 PVT 的逐层细节，不写 backbone 型号。

#### Context features

- 使用一面薄的彩色 token 墙；
- 与 `z_t` 采用不同轮廓，避免把 encoder feature 与预测状态混为一谈。

#### State projector P

- 用梯形、漏斗或窄 MLP 图标表示；
- 框内只写 `P`；
- 框外短标签写 `state projector`。

#### Predictive state z_t

- 使用 4×4 或 6×6 彩色张量网格；
- 加一个很小的历史时钟符号，表示 `history-only`；
- 不能使用 NDVI 色标；
- 不能把状态张量称为物理地图或可解释变量图。

#### Context forecast b_h

- 使用一张浅色的小型预测图槽或一条薄预测序列；
- 从 `q` 直接产生；
- 用一条细蓝线直接连接 Panel (d) 的加法节点。

### 7.4 可直接使用的英文

面板标题：

> **(b) History encoding & state construction**

模块：

> **History encoder \(q\)**  
> **Context features**  
> **State projector \(P\)**  
> **History-only predictive state \(z_t\)**  
> **Context-only forecasts \(b_{1:H}\)**

分支箭头可选短词：

> encode  
> project  
> context branch

### 7.5 结构约束

- `Future meteorological forcing` 不得进入 `q`、`P` 或 `z_t`；
- observed future EO 不得进入本区块的主实线路径；
- `b_h` 与 `z_t` 必须来自同一次历史条件编码；
- 不画 Stage 1/2/3、checkpoint 初始化或冻结计划。

## 8. Panel (c)：Weather-conditioned shared dynamics

### 8.1 本区块回答什么

**未来天气如何在共享动力学中推进预测状态？**

这是全图的视觉中心和 TerraState 的核心方法区。

### 8.2 主体结构

```text
                         future weather u_t:t+h
                                  │
geography g ───────────────┐      │
horizon h ─────────────────┼──────▼
                           │  Shared transition T
z_t ───────────────────────┘      │
                                  ▼
                    Evolved predictive state z_t+h
```

### 8.3 Shared transition T 的视觉设计

推荐画成一个较大的圆角模块：

```text
┌─────────────────────────────┐
│ weather tokens              │
│       ↓                     │
│ state–forcing interaction   │
│       ↓                     │
│ shared transition T         │
└─────────────────────────────┘
```

内部只保留三层视觉：

1. 上方天气时间 token；
2. 中间 state–forcing interaction；
3. 下方/右侧更新后的状态 token。

可以使用：

- 一组天气条带伸入网络；
- 状态方块墙从左侧伸入；
- 中间用交叉注意力或门控样式的简化网格；
- 输出端状态方块发生颜色/纹理变化。

不要使用：

- 循环箭头；
- 多步 rollout 轨迹；
- `composition`、`cocycle`或 Q4 标签；
- 复杂 MMDiT 名称，因为真实方法并不是 MMDiT；
- 物理方程求解器图标；
- “physically constrained”或“physics-informed”表述，除非正文给出真实物理约束。

### 8.4 未来天气视觉

天气条带建议由三层构成：

```text
temperature  ─╱╲──╱─
precipitation ▂▁▆▁▃
radiation    ▃▅▇▆▄
```

它们只是变量类别的视觉代表，不应伪装成真实数值曲线；如果使用真实曲线，必须来自同一展示样本并保留来源。

Panel (c) 中可在天气入口放一个**极小型**替换端口：

> `weather intervention`

主路径默认只显示真实未来天气。若版面充足，替换口旁边可用低对比度小字列：

> actual / matched donor / normalized mean

该端口对应 Q3，但不在 Figure 2 中展示结果，也不能画成与`Shared transition \(T\)`
同等级的模块。若它使Panel (c)拥挤，保留一个空心菱形并把三种条件移入caption。

### 8.5 z_t 与 z_t+h

- 两者使用完全相同的张量外形；
- `z_{t+h}` 的内部颜色或纹理轻微变化；
- 中间必须经过 `T`；
- 不将 `z_{t+h}` 显示成真实 NDVI 地图；
- 不暗示每个 latent channel 有固定物理含义。

### 8.6 可直接使用的英文

面板标题：

> **(c) Weather-conditioned shared dynamics**

输入：

> **Future meteorological forcing \(u_{t:t+h}\)**  
> **Geographic context \(g\)**  
> **Forecast horizon \(h\)**

模块：

> **Shared transition \(T\)**  
> state–forcing interaction  
> shared across forecast horizons

状态：

> **Current predictive state \(z_t\)**  
> **Evolved predictive state \(z_{t+h}\)**

可选干预标签：

> **Weather intervention**  
> actual / matched donor / normalized mean

## 9. Panel (d)：State readout & forecast

### 9.1 本区块回答什么

**未来状态如何产生可检验的预测贡献，并与上下文预测闭合为最终输出？**

### 9.2 主体结构

```text
Evolved predictive state z_{t+h}
                  │
                  ▼
           State readout O
                  │
                  ▼
      State contribution r_h ───┐
                                ⊕ → Vegetation forecast y_hat_{t+h}
Context-only forecast b_h ──────┘
```

Panel D不是Q2实验图，而是核心模型的输出闭环。读者必须先看到：

1. 演化状态如何经\(O\)形成\(r_h\)；
2. \(r_h\)如何与\(b_h\)合并；
3. 合并结果具体对应未来植被预测。

Q2断点只作为第4层信息出现。

### 9.3 视觉形式

#### State readout O

- 使用一个窄解码网络或漏斗形模块；
- 框内写 `O`；
- 外侧写 `state readout`；
- 不需要展开反卷积或逐层结构。
- `O`应直接位于\(z_{t+h}\)之后，不能与加法节点或Q2断点混在同一个大框里。

#### State contribution r_h

- 最优形式是同一真实 query 导出的有符号贡献图；
- 使用零中心发散色标；
- 若缺少真实导出，使用明确标注的空图槽；
- 不得使用随机热力图替代。
- 它表示状态路径对最终预测的空间修正，不是最终NDVI预测，也不宣称每个颜色具有固定
  物理语义。

#### Context-only forecast b_h

- 从 Panel (b) 上方支路进入；
- 与 `r_h` 在加法节点前并排；
- 若展示真实图，必须与 `r_h`、最终预测来自同一 checkpoint、cube 和 horizon。

#### Forecast closure

加法圆圈旁写：

\[
\widehat y_{t+h}=b_h+r_h.
\]

这是全图最重要的公式，只保留这一条即可。

加法节点不需要外包一个很大的`Forecast fusion`网络框。推荐直接使用：

```text
b_h ─┐
     ⊕ → y_hat
r_h ─┘
```

这样可以把空间留给最终预测图，并让模型闭合比干预接口更突出。

#### Final output

- 使用 3 张未来 NDVI 预测缩略图，如 `h=5,10,20`；
- 同一色标、同一空间范围；
- 最右侧标题写 `Vegetation forecast`；
- 若放 observed future，只能以小型参考框放在输出下方，必须标 `reference`，不得接入主实线。
- 若D区空间不足，可使用一张较大的主预测图，并在下方放`h=5 / h=10 / h=20`三个
  小时距标签；不应为了保留三张小图把公式和模块文字缩得不可读。

### 9.4 Q2 干预端口

在 `r_h → ⊕` 之间放一个小型可断开端口：

> **State-path intervention**

旁边小字：

> remove state contribution

它只说明模型允许在哪里干预，不在 Figure 2 中展示 Q2 数值。

支持性 `T→I` 不放入主方法图，避免使 Figure 2 拥挤并弱化主要闭合干预。

视觉约束：

- 端口面积不得超过Panel D的5%；
- 端口使用橙红色细线，主模型仍使用蓝绿/绿色；
- 不画Q2结果、下降百分比或置信区间；
- 空间不足时可以只保留断点图标，把`State-path intervention`移到caption。

### 9.5 可直接使用的英文

面板标题：

> **(d) State readout & forecast**

模块：

> **State readout \(O\)**  
> **State contribution \(r_h\)**  
> **Context-only forecast \(b_h\)**  
> **Forecast fusion**  
> **Vegetation forecast \(\widehat y_{t+h}\)**

闭合：

> \(\widehat y_{t+h}=b_h+r_h\)

干预：

> **State-path intervention**  
> remove state contribution

输出：

> \(h=5\)  
> \(h=10\)  
> \(h=20\)

## 10. 训练目标不进入 Figure 2

Figure 2 只展示推理架构。冻结预测教师、未来状态目标编码器、真实未来 NDVI、损失权重和训练阶段均由方法正文或附录说明，不在本图出现。这样既避免把 future EO 误画成推理输入，也为核心状态路径和真实图片留出足够空间。

## 11. 推荐配色

| 语义 | 颜色建议 |
|---|---|
| 历史 EO 与输入 | 低饱和蓝 |
| 当前/未来预测状态 | 蓝绿色 |
| 未来天气与天气入口 | 暖橙色 |
| 共享转移 T | 蓝紫色 |
| 状态读出与贡献 | 绿色或青色 |
| 上下文预测支路 | 浅蓝 |
| 最终预测 | 深绿色 |
| Q2/Q3 干预端口 | 橙红色小标记 |

整图最多使用 5 个主色。禁止彩虹色网络节点和大面积渐变背景。

## 12. 字体与线条

- 图内字体：Arial、Helvetica 或论文统一无衬线字体；
- 面板标题：8.5–9 pt；
- 模块标题：7.5–8 pt；
- 辅助标签：6.5–7 pt；
- 缩放到双栏宽度后，任何文字不得小于约 6.5 pt；
- 主箭头：1.2–1.5 pt；
- 上下文预测支路：0.8–1.0 pt；
- 面板边界：0.6–0.8 pt；
- 不使用阴影、立体浮雕和粗黑边框。

## 13. PPT 施工顺序

1. 将页面设为 `7.0 × 3.25 in`；
2. 建立四个浅色背景区块；
3. 添加顶部连续阶段条；
4. 先画唯一主实线路径；
5. 从 `q` 画出 `b_h` 上方细支路；
6. 加入 future-weather 下方时间带，只接到 `T`；
7. 添加 `r_h + b_h` 加法闭合；
8. 完成Panel D的`O → r_h → ⊕`和最终预测图组；
9. 替换真实 EO、mask、地图和输出图；
10. 最后加入 Q2/Q3 小型干预端口；任何接口都不得压过核心模型；
11. 导出 PDF/SVG 检查缩小后的可读性；
12. 保存原始 PPTX，所有文字、模块和箭头保持可编辑。

## 14. Figure 2 英文 caption

**Figure 2: TerraState architecture and testable predictive-state pathway.**
Historical Earth observations, environmental context, and static geographic attributes are encoded by \(q\). The same history-conditioned pass produces context-only forecasts \(b_{1:H}\) and, through projector \(P\), a history-only predictive state \(z_t\). Future meteorological forcing, geographic context, and the requested horizon enter only the shared transition \(T\), which evolves the state to \(z_{t+h}\). Readout \(O\) maps the evolved state to a state contribution \(r_h\), and the final vegetation forecast closes as \(\widehat y_{t+h}=b_h+r_h\). Small intervention ports expose the state-contribution and future-weather pathways used by the behavioral tests.

## 15. Figure 2 中文 caption

**图2：TerraState架构与可检验预测状态路径。**
历史地球观测、环境上下文和静态地理属性由 \(q\) 编码。同一次历史条件前向过程产生仅依赖上下文的预测 \(b_{1:H}\)，并经投影器 \(P\) 构造仅由历史信息形成的预测状态 \(z_t\)。未来气象驱动、地理上下文和所查询的预测时距只进入共享转移 \(T\)，由其将状态推进至 \(z_{t+h}\)。读出器 \(O\) 将未来状态映射为状态贡献 \(r_h\)，最终植被预测以 \(\widehat y_{t+h}=b_h+r_h\) 闭合。两个小型干预端口暴露状态贡献和未来天气路径，以支持行为检验。

## 16. 与 Figure 1 的去重边界

Figure 1 已经负责：

- 动作条件世界模型与天气驱动 EO 世界模型的概念对齐；
- TerraState“可检验状态路径”的概念卖点；
- Q1–Q3 的层级证据契约。

Figure 2 不重复：

- “为什么只看输出不足”；
- Q1、Q2、Q3 的完整定义；
- 结果通过/失败；
- 世界模型的宏观定义争论。

Figure 2 只保留两个极小干预端口，说明它们在真实架构中的位置。它们合计不得占据超过
约10%的视觉注意力；Figure 2的主体始终是模型计算路径和最终预测闭合。

## 17. 禁止项

- 不写 `full24`、`Stage A/B`、`Phase I/II`、`boundary80`、`MAIN-last`；
- 不画 cache、checkpoint、SHA、DDP、GPU 或 batch；
- 不把未来天气输入 `q`、`P`、`z_t`、`O` 或 `b_h`；
- 不把 observed future EO 接入推理主实线；
- 不把 `T` 画成循环 rollout；
- 不宣称 temporal composition；
- 不宣称 extreme-specific enhancement；
- 不使用 `physics-informed`、`physically constrained` 等未被方法支持的词；
- 不使用 `MMDiT`，除非模型真实采用该结构；
- 不把随机张量热图当作真实内部状态可视化；
- 不使用外部论文截图作为本方法素材；
- 不把 Q2/Q3 的结果数值塞进方法图；
- 不在 Figure 2 中画 teacher、future-state target 或其他训练监督。

## 18. 最终验收清单

- [ ] 四个区块从左到右形成唯一连续主路径；
- [ ] `q` 同时产生 `b_{1:H}` 与供 `P` 使用的 context features；
- [ ] `P` 明确产生 history-only `z_t`；
- [ ] future meteorological forcing 只进入 `T`；
- [ ] geography 与 horizon 进入 `T`；
- [ ] `T` 是共享转移，但没有 rollout 循环；
- [ ] `O` 只读取 `z_{t+h}`；
- [ ] 最终闭合写为 \(\widehat y_{t+h}=b_h+r_h\)；
- [ ] Panel D清楚呈现`z_{t+h} → O → r_h`、`b_h+r_h`与最终预测图；
- [ ] Panel D的最终预测是明确视觉落点，不是只剩公式或干预符号；
- [ ] Q2 端口位于 `r_h → ⊕`；
- [ ] Q3 端口位于 future weather → `T`；
- [ ] Q2/Q3接口合计不超过约10%的视觉注意力，且均未画成独立大模块；
- [ ] 图中完全不出现 teacher、future EO target 或训练监督轨；
- [ ] 图内无工程命名、训练阶段和未支持主张；
- [ ] 所有英文与 `FIGURE_2_TEXT_COPY.md` 一致；
- [ ] 所有真实素材满足 `FIGURE_2_ASSET_CHECKLIST.md`；
- [ ] PPTX 与 SVG 保持可编辑；PDF 保持矢量清晰；
- [ ] 缩小到论文双栏宽度后仍能在十秒内读懂主路径。
