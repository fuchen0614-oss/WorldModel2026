# Figure 1 双语视觉施工蓝图：从 EO 世界模型逻辑到可检验证据

> 本文件是一份独立施工蓝图，不替代或修改现有
> `FIGURE_1_BLUEPRINT_ZH.md`、`FIGURE_2_BLUEPRINT_ZH.md` 或任何图稿。  
> 依据：作者提供的 Figure 1 框架图
> `示例/8d05ff4abc45277ce9b0481b54435c07.png`、EO-WM Figure 1、
> `示例/ICLR.pptx` 及当前 TerraState 正文术语。  
> 施工语言：本文件中英双语；最终论文图建议只保留英文。  
> 图的性质：**概念—能力—证据总览图**，不是训练流水线，也不是 Figure 2 的缩略版。

---

## 0. 先用一分钟重新理解 Figure 1

Figure 1 只需要帮助读者记住一句话：

> **TerraState 不仅输出未来 EO，还把“历史形成的预测状态—天气驱动的共享转移—
> 状态贡献”暴露为可以直接干预和检验的路径。**

三个 panel 分别回答三个不同的问题：

| Panel | 读者脑中的问题 | 本 panel 的作用 | 应寻找的主要图片 |
|---|---|---|---|
| (a) | 为什么只看预测精度还不够？ | 从一般世界模型映射到受外生天气驱动的 EO 世界建模，并指出输出评分留下的内部验证缺口 | 一般场景/动作图标、历史与未来卫星图、天气图标、输出评分符号 |
| (b) | TerraState 到底多提供了什么？ | 展示一条可被操作的状态路径和两个干预接口 | 真实历史 EO、抽象状态张量、天气序列、真实 TerraState 预测图 |
| (c) | 什么证据才算支持这个主张？ | 把 Q1→Q2→Q3 组织成有先后层级的证据契约 | 三个简洁图标或小示意，不放详细数据图 |

最容易记忆的口令是：

```text
(a) Why / 为什么只看输出不够
    ↓
(b) What / TerraState 暴露了什么内部能力
    ↓
(c) How to test / 用什么操作证据判断它成立
```

当对某一部分有疑惑时，可以这样回忆：

```text
对 (a) 有疑惑：问“现有评价直接看到了什么、没有直接看到什么？”
对 (b) 有疑惑：问“我们究竟能切断哪条路径、替换哪个输入？”
对 (c) 有疑惑：问“预测有用、状态承载、天气忠实三者是什么逻辑关系？”
```

### 0.1 Figure 1、Figure 2、Figure 3 的分工

```text
Figure 1：为什么做 + TerraState 的核心能力 + 如何检验
Figure 2：q、P、T、O、b_h、r_h 在模型中如何精确运行
Figure 3：冻结实验中 Q2/Q3 的效应方向、区间和逐样本分布
```

因此 Figure 1 中：

- 可以出现 `z_t`、`T`、`z_{t+h}`、`O`、`b_h`、`r_h`；
- 不出现 teacher、future-state target、KD、训练目标或阶段编号；
- 不展开 `q→P` 的内部结构；
- 不放 Figure 3 的散点和置信区间；
- 不放 Q4、composition、因果或极端天气特异性主张。

---

## 1. 对当前框架的审核结论

### 1.1 总体判断

**当前框架的主逻辑是正确的，可以作为新 Figure 1 的母版。**

它已经具备正确的三段式叙事：

```text
(a) World-model logic meets EO
    世界模型逻辑如何进入 EO
        →
(b) TerraState exposes testable pathways
    TerraState 暴露可检验路径
        →
(c) Operational evidence
    用层级证据检验这些路径
```

不需要推翻这三个 panel，也不需要改成另一套故事。

### 1.2 当前图中最值得保留的内容

1. Panel (a) 没有武断地说普通 EO 预测“不是世界模型”，而是比较一般
   action-conditioned world model 与受外生驱动的 EO world modeling。
2. Panel (b) 已经出现历史上下文、历史状态、共享转移、状态读出、上下文预测和
   weather controls，方向与正文一致。
3. Panel (c) 已经把 Q1、Q2、Q3 画成纵向层级，而非三个完全并列的指标。
4. `PREREQUISITE → DEFINING EVIDENCE → FORCING GROUNDING` 的关系基本正确。

### 1.3 必须修正的内容

| 当前问题 | 为什么是问题 | 推荐修正 |
|---|---|---|
| Panel (a) 主要是文字 bullet，`Action` 和 `Future Weather` 悬浮 | 读者无法一眼看到“输入→状态→转移→未来”的对应关系 | 恢复 EO-WM 式四行视觉对应，但用自己的图标和遥感图 |
| Panel (a) 使用 `endpoint scoring` | TerraState 的 Q3 使用完整 20 步 forecast-window MSE，`endpoint` 容易造成术语混淆 | 改为 `Output-level evaluation` 或 `What output scoring establishes` |
| Panel (a) 两个范式内部没有真正的箭头 | 看起来像特征清单，不像世界模型逻辑 | 每个范式都画四步连线，并让 action/weather 只进入 transition |
| Panel (b) 天气选择器与状态框的空间关系不清 | 容易误读成天气直接生成 `z_t` | actual/donor/mean 选择器只连到 `T`；`z_t` 只连历史上下文 |
| Panel (b) `b_h`、`O`、`r_h` 和最终 forecast 没有形成清楚闭合 | TerraState 的独特点恰好是显式状态贡献加入最终预测 | 明确画 `b_h + r_h → Forecast` |
| Panel (b) 当前几乎全是文字框 | 与 EO/遥感任务缺少视觉联系 | 至少加入一组真实历史 EO 和一张真实 TerraState 预测图 |
| Panel (c) 三个卡片内部文字偏长 | 纸面缩放后容易变成段落 | 每卡只留“问题名 + 一行证据含义 + 一个图标” |
| Panel (c) `DEFINING EVIDENCE` 容易被读成全领域定义 | 本文提出的是 operational evidence contract，不是唯一世界模型定义 | 改为 `CORE STATE EVIDENCE`，或在 caption 中限定为 `our operational contract` |

### 1.4 最终建议：保留框架，重做视觉表达

```text
保留：
三 panel、A 的世界模型映射、B 的显式状态路径、C 的 Q1→Q2→Q3 层级

删除：
长 bullet、悬浮输入词、重复解释句、训练相关内容、Figure 3 的数值

新增：
真实历史 EO、真实预测图、可编辑天气/动作图标、状态张量、明确的干预端口
```

---

## 2. 画布、分区和对象层级

### 2.1 画布

- AAAI 双栏通栏：`7.0 in` 宽；
- 推荐高度：`3.10–3.30 in`；
- 推荐比例：约 `2.15:1`；
- 图内不放论文式总标题；
- 最终文字不小于 `7.5–8 pt`；
- 如果在 13.33 英寸 PPT 画布上施工，正文对象字号至少使用 `15–17 pt`；
- 更推荐直接建立 `7.0 × 3.2 in` 的自定义 PPT 页面，避免二次缩放。

### 2.2 三个大 panel 的宽度

| Panel | 比例 | 7 英寸下约宽 | 原因 |
|---|---:|---:|---|
| (a) Conceptual gap | 32% | 2.24 in | 需要容纳两个范式和一个评分带 |
| (b) Testable pathways | 42% | 2.94 in | 是全图视觉中心，必须能看清状态路径和真实预测图 |
| (c) Evidence contract | 26% | 1.82 in | 只放三层证据卡，不承担模型细节 |

panel 间使用 `0.08–0.10 in` 的窄分隔，不画贯穿全图的大箭头。

### 2.3 最外层与内层对象关系

Figure 1 只有三个大 panel，不要误画成四个大面板。你所说的“四个大块内部按照
下面层级放置小块”，最适合落实在 **Panel (b) 内部**：

```text
Figure 1
│
├── Panel A：Conceptual gap / 概念缺口
│   ├── A1 Typical action-conditioned world model
│   ├── A2 EO world modeling under exogenous forcing
│   └── A3 Output-level evaluation gap
│
├── Panel B：TerraState testable pathways / 可检验路径
│   ├── 大块 B1 Historical context / 历史上下文
│   ├── 大块 B2 Predictive-state dynamics / 预测状态动力学
│   ├── 大块 B3 Forecast closure / 预测闭合
│   └── 大块 B4 Intervention layer / 干预接口层
│
└── Panel C：Operational evidence contract / 操作性证据契约
    ├── C1 Q1 Predictive utility
    ├── C2 Q2 Load-bearing state
    └── C3 Q3 Weather-response fidelity
```

这里的 B4 不是第四条模型路径，而是贴在 B2/B3 箭头上的两个小接口：

```text
Q3：贴在 future weather → T 上
Q2：贴在 r_h → addition 上
```

---

## 3. 全图双语线框

图例：

```text
[REAL EO]      必须换成真实 EO 或真实模型输出
[ICON]         使用 PowerPoint/Material Symbols 的可编辑矢量图标
[STATE GRID]   可使用抽象状态张量，不表示真实地理图
[PORT]         干预接口，只贴在箭头上
[TEXT]         最终图中的英文短标签
```

### 3.1 一眼可照着画的总线框

```text
┌──────────────────────────────┬──────────────────────────────────────┬────────────────────────┐
│ (a) From world-model logic   │ (b) TerraState exposes              │ (c) Operational        │
│     to EO                    │     testable pathways               │     evidence contract  │
│ 从世界模型逻辑到 EO          │ TerraState 暴露可检验路径            │ 操作性证据契约          │
│                              │                                      │                        │
│ GENERAL WORLD MODEL          │ [REAL EO][REAL EO][REAL EO]         │ Q1 Predictive utility  │
│ scene → state → T → future   │ Historical context                  │ [forecast + check]     │
│                 ↑ action     │       │                              │ Forecasting prerequisite│
│                              │       ├──────── b_h ───────────┐     │          ↓             │
│ EO WORLD MODELING            │       ↓                       │     │ Q2 Load-bearing state │
│ EO → Earth state → T → EO    │ [STATE GRID] → T → [STATE GRID]     │ [cut state path]       │
│                 ↑ weather    │      z_t       ↑      z_{t+h} │     │ Core state evidence    │
│                              │                │              ↓     │          ↓             │
│ OUTPUT-LEVEL EVALUATION      │   actual / donor / mean      O→r_h │ Q3 Weather-response    │
│ Forecast ✓ | State use ?     │                Q3 [PORT]       │    │ fidelity               │
│              Forcing use ?   │                         Q2 ×───┤    │ [weather replacement]  │
│                              │                               ⊕→[REAL FORECAST]          │
└──────────────────────────────┴──────────────────────────────────────┴────────────────────────┘
```

### 3.2 阅读顺序

```text
Panel A：先看一般世界模型，再看 EO 映射，最后看输出评分留下的问号
Panel B：从真实历史 EO 开始，沿粗状态路径到真实预测，再看 Q2/Q3 端口
Panel C：从 Q1 向下读到 Q2、Q3，理解三层证据的不同地位
```

---

## 4. Panel (a) 精准施工蓝图

### 4.1 唯一任务

Panel (a) 回答：

> **一般世界模型的“观测—状态—转移—未来”逻辑如何对应到受外生天气驱动的 EO，
> 以及为什么输出评分本身没有直接检查内部状态和驱动路径？**

它不是在宣称普通 EO forecaster 一定不是世界模型。

### 4.2 推荐内部布局

Panel (a) 分成上、中、下三层：

| 区域 | 高度 | 内容 |
|---|---:|---|
| A1 上层 | 32% | Typical action-conditioned world model |
| A2 中层 | 38% | EO world modeling under exogenous forcing |
| A3 下层 | 24% | Output-level evaluation gap |
| 留白 | 6% | 面板标题与安全间距 |

不要继续使用两个细长的并列 bullet 框。改成两条上下对齐的四步视觉链。

### 4.3 A1：典型动作条件世界模型

```text
[scene history] → [latent state] → [transition T] → [future scene]
                                       ↑
                                  [action icon]
```

最终英文：

```text
Typical action-conditioned world model
Past observations
Latent state
Transition
Action
Future prediction
```

中文施工解释：

```text
用 1–2 个场景缩略图表示过去；
用抽象小方格表示 latent state；
用一个窄转移块表示 T；
用手柄、方向盘或机械臂图标表示可控 action；
用一张变化后的场景表示 future。
```

推荐图片：

- 首选：PowerPoint 内置 Icons/Stock Images，而不是随意下载游戏截图；
- 图标搜索词：`game controller`、`steering wheel`、`robot arm`、`street scene`；
- 或使用 Google Material Symbols 中的 `sports_esports`、`directions_car`、
  `smart_toy`、`arrow_forward`。

### 4.4 A2：外生驱动下的 EO 世界建模

```text
[sparse EO history] → [Earth-surface state] → [EO transition] → [future EO]
                                                ↑
                                        [future weather]
```

最终英文：

```text
EO world modeling under exogenous forcing
Sparse observations
Earth-surface state
Transition
Future weather
Future EO
```

中文施工解释：

```text
用同一 minicube 的 2–3 张历史 Sentinel-2 RGB/NDVI 缩略图；
其中一张可叠加云或有效像素 mask，表达 sparse and incomplete；
Earth-surface state 用半透明状态格，不伪装成可观测真值；
future weather 用温度、降水、辐射三个小符号或一条天气序列；
future EO 使用真实 target EO；如果想保持纯概念，也可使用同一 AOI 的后时刻 EO。
```

### 4.5 A3：输出评分留下的内部验证缺口

推荐最终画法：

```text
Output-level evaluation

[metric/check] Forecast ✓     [probe] State use ?     [weather probe] Forcing use ?
```

最终英文：

```text
What output scoring establishes
Forecast quality ✓
State use ?
Forcing use ?
```

不建议继续使用：

```text
What endpoint scoring reveals
```

原因：正文与 Figure 3 的天气忠实度使用完整 20 步 forecast window，
`endpoint` 容易被误解为单独的 `h=20` endpoint。

### 4.6 A 区箭头清单

```text
A1 past scene → A1 latent state
A1 latent state → A1 transition
A1 action icon → A1 transition
A1 transition → A1 future scene

A2 sparse EO → A2 Earth-surface state
A2 Earth-surface state → A2 transition
A2 future weather → A2 transition
A2 transition → A2 future EO

A1/A2 的 future output → A3 Forecast quality ✓
A3 不要反向连到内部 state；问号本身表示尚未直接检验
```

---

## 5. Panel (b) 精准施工蓝图

### 5.1 唯一任务

Panel (b) 回答：

> **TerraState 暴露了哪条可操作的预测状态路径，以及 Q2/Q3 分别在哪里实施干预？**

Panel (b) 不是 Figure 2 的缩略复制。它只保留核心能力：

```text
history → z_t → weather-conditioned T → z_{t+h} → O → r_h
history → b_h
b_h + r_h → forecast
```

### 5.2 Panel (b) 的四个内部大块

| 大块 | 横向位置 | 宽度 | 包含的小块 |
|---|---|---:|---|
| B1 Historical context | 左侧 | 20% | 历史 EO 图组、past weather 小标签、static geography 小标签 |
| B2 Predictive-state dynamics | 中央 | 43% | `z_t`、`T`、`z_{t+h}`、天气选择器 |
| B3 Forecast closure | 右侧 | 27% | `O`、`r_h`、`b_h`、加法节点、真实预测图 |
| B4 Intervention layer | 覆盖在 B2/B3 箭头上 | 10%视觉注意力 | Q3 weather port、Q2 state-path cut |

### 5.3 B1：历史上下文

```text
┌─────────────────────┐
│ [REAL EO][REAL EO]  │
│ [REAL EO]           │
│ Historical context  │
│ past weather · static│
└─────────────────────┘
```

最终英文：

```text
Historical context
Past EO
Past weather
Static geography
```

推荐素材：

- 3 张同一 minicube、同一裁切范围的真实历史 RGB 或 NDVI；
- 缩略图顺序从旧到新，左下角只标 `t-2, t-1, t`；
- past weather 和 static geography 不需要再各放一张大图；
- 空间足够时，static geography 内可放一张很小的 `DEM` 或 `land cover`；
- 空间不足时只保留 `past weather · static` 两个小标签。

### 5.4 B2：预测状态动力学

```text
[STATE GRID z_t] → [Shared weather-conditioned T] → [STATE GRID z_{t+h}]
                              ↑
             actual ──────────┐
             matched donor ───┼→ [Q3 PORT]
             normalized mean ─┘
```

最终英文：

```text
History-only predictive state z_t
Shared weather-conditioned transition T
Evolved predictive state z_{t+h}
Actual future weather
Matched-donor weather
Normalized-mean weather
Q3 · Weather intervention
```

施工规则：

- `z_t` 和 `z_{t+h}` 使用同形的抽象状态格；
- `z_t` 的内部色块较稳定，`z_{t+h}` 可轻微改变纹理；
- 状态格只能表示 latent/predictive state，不使用真实地图底图；
- future weather 只连到 `T`，不能连到 `z_t`、`b_h` 或历史编码端；
- actual 用实线；matched donor 与 normalized mean 用不同虚线；
- 三种天气是一个接口的三个输入选项，不是三个模型。

### 5.5 B3：状态读出与预测闭合

```text
z_{t+h} → [State readout O] → [State contribution r_h] ──×Q2──┐
                                                               ⊕ → [REAL FORECAST]
Historical context → [Context-only forecast b_h] ─────────────┘
```

最终英文：

```text
State readout O
State contribution r_h
Context-only forecast b_h
Forecast
Q2 · State-path intervention
```

施工规则：

- `O` 使用窄漏斗或窄矩形，不画完整 decoder 网络；
- `r_h` 可用一个有正负色的抽象小图槽，也可以只写符号；
- 如果没有可确认 provenance 的真实 `r_h` 贡献图，不得随机画热力图；
- `b_h` 使用较细的灰蓝旁路，直接进入加法节点；
- Q2 断点必须位于 `r_h → ⊕`，表示 `remove r_h`；
- Figure 1 默认不放 `T→I`，它属于 Figure 2/3 的 supporting intervention；
- 最右侧 Forecast 必须优先使用真实 TerraState 模型输出。

### 5.6 B4：两个干预接口

```text
Q3 [selector/替换口]：future weather → T
Q2 [cut switch/断路口]：r_h → ⊕
```

图标建议：

- Q3：三档选择器、交换箭头或 `swap_horiz`；
- Q2：断开的链路、剪刀或 toggle-off；
- 端口图标尺寸不超过状态模块高度的 30%；
- Q2/Q3 标签使用强调色，但不要盖住正常推理主路径。

### 5.7 B 区完整箭头清单

```text
B1 Historical context → B2 z_t
B1 Historical context → B3 b_h
B2 z_t → B2 T
Q3 actual/donor/mean selector → B2 T
B2 T → B2 z_{t+h}
B2 z_{t+h} → B3 O
B3 O → B3 r_h
B3 r_h → Q2 cut → B3 addition node
B3 b_h → B3 addition node
B3 addition node → B3 real TerraState forecast
```

禁止增加：

```text
future EO → z_t
future weather → history encoder
teacher → forecast
loss → T
Q4/composition → state path
```

---

## 6. Panel (c) 精准施工蓝图

### 6.1 唯一任务

Panel (c) 回答：

> **在本文声明的 operational evidence contract 下，什么证据支持
> TerraState 的“可检验预测状态”主张？**

它不是三个并列 benchmark，而是：

```text
Q1 先证明预测有用
    ↓
Q2 再证明状态贡献真正承载预测
    ↓
Q3 最后把转移落到所声明的外部天气驱动
```

### 6.2 三卡片布局

| 卡片 | 建议高度 | 视觉权重 | 图标 |
|---|---:|---|---|
| C1 Q1 | 25% | 中 | 预测曲线/靶心/勾 |
| C2 Q2 | 34% | 最高 | 状态格 + 断开的贡献路径 |
| C3 Q3 | 29% | 中高 | 天气序列 + 替换箭头 |
| 间隔与箭头 | 12% | 低 | 两条细向下箭头 |

Q2 的边框应最深或卡片略高；不要靠大写斜体文字单独表达层级。

### 6.3 最终英文短文案

#### C1

```text
Q1 · Predictive utility
Useful forecasting under temporal shift
FORECASTING PREREQUISITE
```

中文：

```text
Q1 · 预测效用
在时间分布偏移下仍具有可用预测能力
预测前提
```

#### C2

```text
Q2 · Load-bearing state
Forecast skill degrades without the state contribution
CORE STATE EVIDENCE
```

中文：

```text
Q2 · 承载预测的状态
移除状态贡献后预测能力下降
核心状态证据
```

#### C3

```text
Q3 · Weather-response fidelity
Actual weather outperforms the frozen controls
EXTERNAL-FORCING GROUNDING
```

中文：

```text
Q3 · 天气响应保真度
真实天气优于冻结的天气对照
外部驱动落地
```

### 6.4 C 区箭头

```text
C1 → C2
箭头旁可放：Forecasting prerequisite

C2 → C3
箭头旁可放：Ground the declared driver
```

如果纸面空间不足，删除箭头旁的小字，只保留向下箭头和三卡片的视觉权重差异。

### 6.5 Panel (c) 不建议放 Figure 3 小截图

不建议把 Figure 3 的散点或置信区间缩成图标放入 Figure 1：

- 会重复 Figure 3；
- 缩小后不可读；
- 会让概念图混入详细数值证据；
- Figure 1 的任务是说明“要检验什么”，不是复述结果。

应使用可编辑的简化视觉符号：

```text
Q1：forecast → target + check
Q2：full path → cut path
Q3：actual weather ↔ donor/mean replacement
```

---

## 7. 可直接复制到最终图中的英文清单

### Panel titles

```text
(a) From world-model logic to EO
(b) TerraState exposes testable pathways
(c) Operational evidence contract
```

当前 `(a) World-model logic meets EO` 也可以使用，但
`From world-model logic to EO` 更明确地表达“领域映射”，不暗示两者发生理论冲突。

### Panel (a)

```text
Typical action-conditioned world model
Past observations
Latent state
Transition
Action
Future prediction

EO world modeling under exogenous forcing
Sparse observations
Earth-surface state
Transition
Future weather
Future EO

What output scoring establishes
Forecast quality ✓
State use ?
Forcing use ?
```

### Panel (b)

```text
Historical context
Past EO
Past weather
Static geography
History-only predictive state z_t
Shared weather-conditioned transition T
Evolved predictive state z_{t+h}
State readout O
State contribution r_h
Context-only forecast b_h
Forecast
Q2 · State-path intervention
Q3 · Weather intervention
Actual future weather
Matched-donor weather
Normalized-mean weather
```

### Panel (c)

```text
Q1 · Predictive utility
Useful forecasting under temporal shift
FORECASTING PREREQUISITE

Q2 · Load-bearing state
Forecast skill degrades without the state contribution
CORE STATE EVIDENCE

Q3 · Weather-response fidelity
Actual weather outperforms the frozen controls
EXTERNAL-FORCING GROUNDING
```

---

## 8. 图片与图标资产清单

### 8.1 哪些素材必须是真实 TerraState 数据

| 位置 | 素材 | 是否必须真实 | 原因 |
|---|---|---:|---|
| A2 Sparse EO | 同一 minicube 的历史 EO | 推荐必须 | 让图真正属于遥感任务 |
| A2 Future EO | 同一 AOI 的后时刻观测 | 推荐必须 | 表达 EO 世界建模的观测输出 |
| B1 Historical context | TerraState 实际输入的历史 RGB/NDVI | 必须 | 不能把外部场景伪装成模型输入 |
| B3 Forecast | TerraState 实际模型预测 | 必须 | 这是模型输出，不能用下载图片代替 |
| 可选 target 对照 | 同一 minicube 的真实未来目标 | 必须 | 如果标为 target/observed future，就必须来自真实评测样本 |
| 可选 `r_h` 图 | 真实导出的状态贡献图 | 必须 | 没有真实输出时宁可只用符号框 |

### 8.2 哪些素材可以使用抽象可编辑图形

| 素材 | 推荐画法 |
|---|---|
| `z_t`、`z_{t+h}` | 4×4 或 5×5 的状态张量格，两个状态外形完全一致 |
| `T` | 窄圆角模块 + 天气入口，不画不存在的内部网络 |
| `O` | 窄漏斗/解码器符号 |
| `b_h` 旁路 | 细灰蓝箭头 |
| Q2 cut | 可断开开关或 broken-link SVG |
| Q3 selector | 三档输入选择器或 swap SVG |
| action | 手柄、方向盘或机械臂 SVG |
| metric | ruler、analytics、check-circle SVG |

### 8.3 可选的真实地理素材类别

这些素材只在 B1 的 static geography 小槽中使用；空间不足时可以删除。

| 类别名称 | 图中含义 | 推荐来源 |
|---|---|---|
| `DEM` / Digital Elevation Model | 地形或海拔 | Copernicus DEM、SRTM、OpenTopography |
| `Land cover` | 土地覆盖类型 | ESA WorldCover 2021 |
| `RGB / True color` | 可视化历史 EO | Sentinel-2 L2A |
| `NDVI` | 植被状态 | TerraState 本地输入/目标，或 Copernicus Browser NDVI 层 |
| `Valid-pixel mask` | 云和无效像素 | TerraState 实际 mask；没有时用抽象黑白 mask |
| `Weather sequence` | 温度、降水、辐射等未来驱动 | TerraState 实际天气输入，压缩成三行微型曲线 |

---

## 9. 不手搓素材的优先获取路线

### 9.1 第一优先级：从 TerraState 冻结样本导出

最理想的素材包是同一个 minicube 的：

```text
history_rgb_t-2.png
history_rgb_t-1.png
history_rgb_t.png
history_ndvi_t.png              可选
valid_mask_t.png                可选
forecast_ndvi_h20.png
target_ndvi_h20.png             可选
future_weather_actual.svg/png
future_weather_donor.svg/png
future_weather_mean.svg/png
```

选择标准：

- 历史帧中至少两帧有足够有效像素；
- 地块边界或植被纹理清晰；
- forecast 与 target 不需要“最好看”，但必须是冻结模型真实输出；
- 所有 EO 图使用完全相同的 AOI 和裁切范围；
- 不重新评估模型，只从已有预测记录或缓存中导出；
- 如果本地没有可追溯 qualitative output，先留空槽，不从网上找图冒充模型输出。

### 9.2 第二优先级：PowerPoint 内置矢量 Icons

PowerPoint 路径：

```text
Insert → Icons
Insert → Stock Images → Icons / Illustrations
```

推荐搜索词：

```text
satellite
cloud
rain
thermometer
sun
terrain
layers
map
game controller
steering wheel
robot
switch
broken link
swap
analytics
check
target
```

Microsoft 说明其 Microsoft 365 素材库含 royalty-free 图片、图标和插图，并且
Office 图标可无损缩放和改色：

- [Microsoft 365：插入图片、图标等](https://support.microsoft.com/en-us/powerpoint/insert-images-icons-and-more-in-microsoft-365)
- [PowerPoint 图标的编辑与缩放](https://support.microsoft.com/en-us/powerpoint/icons-a-new-kind-of-office-clip-art)

### 9.3 第三优先级：Google Material Symbols

推荐图标名：

```text
satellite_alt
landscape
cloud
rainy
thermostat
sunny
history
arrow_forward
swap_horiz
toggle_off
link_off
analytics
check_circle
target
sports_esports
directions_car
smart_toy
```

Material Symbols 可下载 SVG/PNG，并使用 Apache 2.0 许可：

- [Google Material Symbols 指南与许可](https://developers.google.com/fonts/docs/material_symbols)

使用 SVG，不使用 32×32 的 PNG；插入 PPT 后统一线宽和颜色。

### 9.4 第四优先级：官方 EO 数据门户

#### Sentinel-2 RGB / NDVI

- [Copernicus Browser](https://dataspace.copernicus.eu/ecosystem/services/copernicus-browser)
- [Copernicus Browser 使用文档](https://documentation.dataspace.copernicus.eu/Applications/Browser.html)

检索与导出方法：

```text
1. 选择 Sentinel-2 L2A；
2. 搜索 cropland / forest / grassland 明显的区域；
3. 最大云量设为 10–30%；
4. 选择 True color 或 NDVI；
5. 关闭道路、行政边界和地名；
6. Crop to AOI；
7. 下载 PNG 或 GeoTIFF；
8. 记录日期、AOI 和 attribution。
```

推荐搜索词：

```text
Sentinel-2 L2A true color cropland
Sentinel-2 NDVI agricultural field
cloud-masked Sentinel-2 vegetation
```

注意：外部 Sentinel-2 图只能作为概念性的 EO 图或背景素材，不能标成 TerraState
真实输入或输出。

#### ESA WorldCover

- [ESA WorldCover 数据与下载](https://esa-worldcover.org/en/data-access)

推荐类别：

```text
WorldCover 2021 cropland
WorldCover grassland
WorldCover tree cover
```

WorldCover 提供 10 m 土地覆盖、RGB、false color 和 NDVI 合成，并使用
CC BY 4.0；最终使用时按官方页面写 attribution。

#### DEM

- [Copernicus DEM](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM)
- [OpenTopography 数据入口](https://opentopography.org/start)
- [OpenTopography 全球 DEM 列表/API](https://opentopography.org/developers)
- [USGS EarthExplorer](https://earthexplorer.usgs.gov/)

推荐搜索词：

```text
Copernicus DEM GLO-30 same AOI
SRTM GL1 30m DEM cropland
OpenTopography hillshade GeoTIFF
```

导出后使用灰度 hillshade 或简洁等高线，不使用彩虹色 DEM。

#### NASA NDVI 与地球观测图片

- [NASA Earth Observations：NDVI 等数据](https://neo.gsfc.nasa.gov/)
- [NASA NEO 图片使用政策](https://neo.gsfc.nasa.gov/about/)

NASA NEO 图片可公开使用，但需要保留数据集 credit；它更适合表达“EO/NDVI
是什么”，不适合冒充 GreenEarthNet minicube 或 TerraState 输出。

### 9.5 文献检索只用于找布局，不直接截进最终图

推荐检索词：

```text
earth observation world model figure weather forcing
remote sensing forecasting framework real input output
AAAI world model architecture satellite imagery
predictive state intervention diagram
weather conditioned EO forecasting figure
```

可优先查看：

- [EO-WM arXiv 页面](https://arxiv.org/abs/2606.27277)
- 本地 `TerraState_AAAI27/literature/eo_wm_2606.27277.pdf`
- 本地 `TerraState_AAAI27/literature/aaai_figure_anchors/`

从论文中只借鉴：

```text
信息层级
图片与模块的相对比例
箭头如何进入 transition
输入和输出如何用真实图像闭合
```

不要把论文截图、图标、遥感地块或网络小图直接裁下来放入 TerraState Figure 1。

---

## 10. `示例/ICLR.pptx` 可复用对象审核

源文件：

```text
TerraState_AAAI27/示例/ICLR.pptx
```

该文件共 6 页，画布为 `13.33 × 7.50 in`。其中的科学内容是 EEG 模型，
**不能直接变成 TerraState 素材**；但可以复制其原生 PPT 分组、图片框和箭头。

### 10.1 第 1 页：最有用

#### 可复用 1：左侧三帧图片组

原位置：

```text
Raw EEG Data
x ≈ 0.65 in
y ≈ 0.57 / 1.56 / 2.52 in
每张约 1.42 × 0.83 in
```

TerraState 用法：

```text
复制整组到 Figure 1 的 B1 Historical context；
删除原 EEG 波形；
替换成同一 minicube 的 3 张历史 EO；
保持统一裁切和三帧层级；
把 “Contains 84 channels” 删除。
```

#### 可复用 2：第二组三帧平行图片框

原位置：

```text
Augmentation
x ≈ 2.64 in
y ≈ 0.61 / 1.60 / 2.55 in
每张约 1.42 × 0.79 in
```

TerraState 用法：

```text
可以复制其三行对齐关系，改成：
actual future weather
matched-donor weather
normalized-mean weather

但不要保留原 EEG 图片。
最终建议把图片框缩成三条天气 strip，而不是三张大图。
```

#### 可复用 3：特征小块与 token 墙

原位置大致在：

```text
x ≈ 4.6–7.9 in
y ≈ 0.9–5.9 in
```

TerraState 用法：

```text
只复制其中 4×4 小方块、短箭头和模块框的分组方式；
将其简化为 z_t 与 z_{t+h} 的两个状态格；
不保留 Q/K/V、Time2Freq、FFN、Res 等 EEG/Transformer 字段。
```

#### 可复用 4：顶部模块标题条

原位置：

```text
Heterogeneous Feature Projection Module
x ≈ 5.0 in, y ≈ 0.2 in
```

TerraState 用法：

```text
可复制文本框高度、居中方式和无背景标题风格；
用于 B2 “Predictive-state dynamics” 或 panel 小标题；
不要复制原文字。
```

### 10.2 第 2 页：与第 1 页几乎相同

第 2 页已经给主要模块加上 `(a)–(e)` 标签。可复用：

```text
panel label 的位置和字号；
图片组、模块组的整体 grouping；
不同大区之间的水平对齐方式。
```

不建议同时从第 1、2 页复制对象，以免得到重复且难管理的分组。

### 10.3 第 3 页：不建议作为整体母版

第 3 页把 raw data 和 augmentation 放到右侧，部分对象越过画布边界。

可有限复用：

```text
三张并排图片的对齐方式；
小模块之间的均匀水平分布。
```

不复用其整体方向和密集 cross-attention 结构。

### 10.4 第 4–5 页：只借鉴卡片对齐

第 4 页左侧为 Q1/Q2/Q3 文本，右侧为结果图；第 5 页为两个大结果卡。

对 Figure 1 的帮助：

```text
可以借鉴 Panel (c) 三个问题在同一竖直轴上的对齐；
可以复制圆角大容器的边界和内部留白。
```

不复用：

```text
雷达图、模型比较图、Q&A 段落文本、Uni-NTFM 标题。
```

### 10.5 第 6 页：最适合复制原生方框和箭头

原页中可用的平行小卡片：

```text
x ≈ 2.33 / 3.51 / 4.68 in
y ≈ 3.36 in
每张约 1.14–1.16 × 0.58 in
```

TerraState 用法：

```text
复制三张 sibling cards，改成：
EO
Past weather
Static

将其放入 B1 Historical context 内；
统一缩小后组合成一个输入组。
```

原页的纵向箭头和两列大容器也可以复制，用于：

```text
Panel (c) 的 Q1→Q2→Q3 纵向层级；
Panel (b) 中 history 与 weather 两条输入的分组。
```

不要复制：

```text
MoE1/MoE2、Query/Key/Value、Transformer 等文字和模块含义。
```

### 10.6 `ICLR.pptx` 中不能直接使用的媒体

媒体审核结果：

```text
image1–image8：EEG 波形
image9/image11：雷达图
image19/image21：模型比较图例
其余小图：灯泡、对话框、checklist 等普通位图/SVG
```

结论：

- EEG 波形、雷达图和模型图例与 TerraState 无关，禁止进入最终图；
- 灯泡、对话框、checklist 也不推荐，因为 Material/PowerPoint 有更干净的矢量替代；
- 真正值得复用的是 PPT 原生分组、图片框位置、箭头和卡片，而不是其中的位图。

---

## 11. 其他本地示例可借鉴什么

### `示例/24569e2812660d34d186783a76e28eb2.png`

借鉴：

- 多通道地图缩略图叠放；
- 顶部阶段条；
- 真实输入图与网络模块交替出现。

不借鉴：

- 过多火焰、雪花、地球等装饰；
- 过密的子流程和长时间 rollout；
- 具体地图像素。

### `示例/29e267060d2d707e94c7caa5a1429769.png`

借鉴：

- `真实输入 → 机制 → 真实输出` 的视觉节奏；
- 每个阶段有明确图片锚点；
- 图像组使用统一大小。

不借鉴：

- 复杂图网络节点；
- 过多鲜艳颜色；
- 下半部多个 benchmark 子图。

### `示例/54a6634916c0c8e4a231f1a7a0421f3c.png`

借鉴：

- 真实 Initial Conditions 与 Forecast/Target 在两端闭合；
- latent core 使用抽象张量而非虚构地图；
- 预测与真实目标使用相同裁切。

不借鉴：

- 多种虚线同时穿越全图；
- 大量 skip connection；
- 深层网络内部结构。

### 当前框架 `示例/8d05ff4abc45277ce9b0481b54435c07.png`

继续作为：

```text
三 panel 的基本宽度关系
Panel (a) 的两个范式
Panel (b) 的状态/天气路径
Panel (c) 的垂直证据层级
```

但需按本蓝图把文字框替换成图片、状态格和清楚箭头。

---

## 12. 图片尺寸与裁剪规范

### 12.1 历史 EO 与预测图

| 图片 | 图内推荐尺寸 | 原始素材最低建议 | 裁剪 |
|---|---|---|---|
| A2 历史 EO | 每张约 `0.28–0.34 in` | `300×300 px` | 正方形，同一 AOI |
| A2 future EO | 约 `0.32–0.38 in` | `300×300 px` | 与历史 EO 完全同范围 |
| B1 历史 EO | 每张约 `0.34–0.42 in` | `400×400 px` | 正方形或 4:3 |
| B3 forecast | `0.46–0.58 in` | `512×512 px` | 与 B1 同范围 |
| 可选 target | 与 forecast 同尺寸 | `512×512 px` | 与 forecast 同范围 |

### 12.2 裁剪规则

```text
同一个视觉故事只使用一个 AOI；
历史、forecast、target 保持相同坐标范围；
不把不同地点拼成“时间变化”；
不使用带网页导航栏、图例或水印的大截图；
保留必要 attribution，但放在 caption/acknowledgment，不塞进小图；
RGB 与 NDVI 不要混用同一色标而不标注；
NDVI 使用固定色标，所有帧一致；
```

### 12.3 天气 strip

```text
宽高比：约 3.5:1–5:1
每条高度：0.10–0.14 in
actual：实线
matched donor：长虚线
normalized mean：点线或水平线
```

不要把天气网页截图直接缩入图中。优先从真实输入数组导出简短折线，或使用
温度/降水/辐射三个矢量图标。

---

## 13. 推荐 caption

### English caption

> **Conceptual overview of testable EO world modeling in TerraState.**
> (a) EO world modeling maps the observation–state–transition logic of
> action-conditioned world models to sparse satellite observations under exogenous
> weather forcing; output scores alone do not establish whether the internal state
> and forcing paths are used. (b) TerraState exposes a history-derived predictive
> state, a shared weather-conditioned transition, and an explicit state contribution,
> enabling state-path and weather-input interventions. (c) Our operational evidence
> contract proceeds from predictive utility to a load-bearing state and
> weather-response fidelity.

### 中文图注

> **TerraState 可检验 EO 世界建模的概念总览。**
> (a) EO 世界建模把动作条件世界模型中的“观测—状态—转移”逻辑映射到稀疏卫星观测
> 和外生天气驱动；仅有输出评分并不能说明内部状态与天气路径是否真正被使用。
> (b) TerraState 暴露由历史形成的预测状态、天气条件共享转移和显式状态贡献，使状态
> 路径与天气输入能够被直接干预。(c) 本文的操作性证据契约依次检验预测效用、承载预测
> 的状态和天气响应保真度。

---

## 14. 术语与主张一致性检查

### 14.1 必须保持的术语

```text
History-only predictive state z_t
Shared weather-conditioned transition T
Evolved predictive state z_{t+h}
State readout O
State contribution r_h
Context-only forecast b_h
Q1 · Predictive utility
Q2 · Load-bearing state
Q3 · Weather-response fidelity
Actual future weather
Matched-donor weather
Normalized-mean weather
OOD-t
```

### 14.2 路径语义

- `z_t` 只来自历史上下文；
- future weather 只进入共享转移 `T`；
- `O` 把 `z_{t+h}` 读出为 `r_h`；
- `b_h + r_h` 形成最终 forecast；
- Q2 主干预是移除 `r_h`；
- `T→I` 是支持性干预，建议不在 Figure 1 展开；
- Q3 只替换 actual / matched donor / normalized mean weather；
- Q3 是 weather-response fidelity，不是因果效应或 counterfactual correctness。

### 14.3 禁止写入 Figure 1

```text
SOTA
proves a world model
causal response
counterfactual correctness
extreme-specific enhancement
temporal composition
Q4
future-state cache
teacher / KD
Stage A / Stage B
smoke / full24
训练阶段编号
详细损失公式
```

### 14.4 当前框架建议替换的字段

| 当前字段 | 建议字段 |
|---|---|
| `What endpoint scoring reveals` | `What output scoring establishes` |
| `Output directly scored` | `Forecast quality ✓` |
| `PREREQUISITE` | `FORECASTING PREREQUISITE` |
| `DEFINING EVIDENCE` | `CORE STATE EVIDENCE` |
| `FORCING GROUNDING` | `EXTERNAL-FORCING GROUNDING` |
| `Useful OOD-t forecast` | `Useful forecasting under temporal shift` |
| `Actual weather outperforms controls` | `Actual weather outperforms the frozen controls` |

---

## 15. AAAI 双栏缩放检查

在最终 `7.0 in` 宽度下必须满足：

- Panel (a) 的两条世界模型链无需放大即可区分；
- Panel (b) 是最先吸引视线的区域；
- 真实历史 EO 与 forecast 至少能看出是同类地表影像；
- `future weather → T` 和 `r_h → cut → ⊕` 两个接口不混淆；
- Panel (c) 的 Q1/Q2/Q3 标题清晰，说明行不超过两行；
- Q2 的卡片比 Q1/Q3 更醒目；
- 图内没有小于 7.5 pt 的文字；
- 不依赖斜体和浅黄色文字表达层级；
- 灰度打印时，实线/虚线、填充/空心、深浅边框仍可区分；
- caption 承担完整解释，图内只留短文案。

推荐纸面测试：

```text
1. 将 PPT 导出为 PDF；
2. 以 7.0 in 宽插入空白 AAAI 双栏页；
3. 按 100% 页面大小导出 300 dpi PNG；
4. 不放大查看 panel 标题、z_t/T/O、Q1/Q2/Q3；
5. 再转灰度检查天气路径与状态路径是否仍可区分。
```

---

## 16. 作者实际开工时的最短清单

### 素材包 1：历史与未来 EO

```text
[ ] 同一 minicube 的 3 张历史 EO
[ ] 同一 minicube 的 TerraState forecast
[ ] 可选：同一 minicube 的 target
[ ] 所有图片具有一致裁切和色标
```

### 素材包 2：天气

```text
[ ] actual future weather strip
[ ] matched-donor weather strip
[ ] normalized-mean weather strip
[ ] 三条 strip 使用相同坐标和变量顺序
```

### 素材包 3：静态地理（可选）

```text
[ ] 同一 AOI 的 DEM 或 hillshade
[ ] 同一 AOI 的 land-cover map
[ ] 如果找不到同一 AOI，删除图片，改用 static geography 图标
```

### 素材包 4：可编辑矢量对象

```text
[ ] action icon
[ ] weather icons
[ ] z_t / z_{t+h} 状态格
[ ] T 和 O 模块
[ ] Q2 cut switch
[ ] Q3 selector
[ ] forecast-quality check
[ ] Q1/Q2/Q3 三张证据卡
```

### 组装顺序

```text
第 1 步：先搭 A/B/C 三个 panel 和宽度；
第 2 步：完成 A 中两条四步视觉链；
第 3 步：完成 B 中唯一粗状态路径；
第 4 步：加入 b_h 旁路和预测闭合；
第 5 步：把 Q2/Q3 端口贴到正确箭头；
第 6 步：放入真实历史 EO 和真实 forecast；
第 7 步：完成 C 的 Q1→Q2→Q3 层级；
第 8 步：检查术语、字号、灰度和纸面预览。
```

最终验收问题：

> 如果遮住所有 caption，审稿人能否在十秒内从真实 EO 图、状态张量、天气替换口和
> 状态断路口看出：**TerraState 把一个天气驱动的预测状态变成了可以直接检验的模型
> 部件？**

如果答案是“能”，Figure 1 的任务就完成了。

---

## 17. 当前本地真实素材审计（2026-07-28）

### 17.1 先说结论

前文列出的：

```text
history_rgb_t-2.png
history_ndvi_t.png
forecast_ndvi_h20.png
target_ndvi_h20.png
future_weather_actual.png
future_weather_donor.png
future_weather_mean.png
```

是**建议导出后的统一文件名**，不是声称这些 PNG 已经存在。

当前本地状态可分为两类：

1. **数据集素材真实存在，可以从冻结 minicube 只读导出**：历史 EO、未来观测
   target、有效性掩膜、actual weather，以及 matched donor 样本中的天气；
2. **模型侧可视化尚未在 Figure/evidence 产物中找到**：TerraState forecast、
   context-only forecast \(b_h\)、state contribution \(r_h\)、\(z_t\) 和
   \(z_{t+h}\) 的逐样本张量。

因此，不能把“建议文件名”理解成“现成文件清单”，也不能用下载的遥感图替代
TerraState 的真实模型输出。

### 17.2 已核实的数据与路径

冻结 Q3 配对记录：

```text
TerraState_AAAI27/evidence_workspace/raw/release/
q3_extreme_state_audit.json
```

逐配对字段：

```text
models.exclusive.q3_donor_rows[*].e_key
models.exclusive.q3_donor_rows[*].c_key
```

- `e_key`：extreme 样本，即 actual-weather 路径使用的原始 minicube；
- `c_key`：与该 extreme 样本匹配的 normal donor minicube；
- JSON 中还保存了冻结的逐配对标量损失，但**没有保存 EO 像素、天气数组或预测图**。

对应原始数据根目录：

```text
TrainData/EarthNet2021/earthnet2021x/ood-t_chopped/
```

本次只读路径核验结果：

| 项目 | 冻结记录数 | 唯一样本数 | 本地 `.nc` 存在数 |
|---|---:|---:|---:|
| extreme `e_key` | 84 | 84 | 84/84 |
| donor `c_key` | 84 | 45 | 84/84 配对均可解析 |

协议与 provenance：

```text
WorldModel2026-planb/artifacts/protocols/extreme_audit_oodt_v1/
```

该目录包含 protocol、manifest、threshold 和 provenance，但没有现成的定性 PNG、
预测张量或状态张量。

### 17.3 `.nc` 中的素材分别是什么

对冻结样本做只读字段检查后，可以确认至少包含以下数据类别：

| Figure 1 素材 | 原始数据字段/构造 | 含义 |
|---|---|---|
| 历史 RGB | Sentinel-2 `s2_B04 / s2_B03 / s2_B02` | 同一 minicube 的红、绿、蓝波段组合 |
| 历史 NDVI | `s2_B8A` 与 `s2_B04` 派生 | \((NIR-Red)/(NIR+Red)\)，是数据派生可视化 |
| 有效性/云掩膜 | `s2_SCL`、`s2_avail` | 区分云、无效观测与可用像素 |
| 真实未来 target | context 之后的 Sentinel-2/NDVI | 同一 minicube 后续真实观测，不是模型生成 |
| actual weather | 同一 `e_key` 的未来 E-OBS 字段 | 真实未来外部驱动 |
| donor weather | 配对 `c_key` 的未来 E-OBS 字段 | matched-donor 天气控制 |
| normalized mean | 标准化天气空间中的均值控制 | 实验协议构造的控制，不是一张原始卫星图 |
| land cover | `esawc_lc` 类字段 | 静态地表覆盖，可选 |

当前样本中可识别的 E-OBS 类变量包括降水、温度、湿度/辐射/风等天气字段。正式
导出时必须沿用模型实际采用的变量顺序与归一化定义，不能凭字段名称自行挑选。

### 17.4 哪些是“数据集里的”，哪些不是

| 建议文件 | 是否来自数据集 | 当前是否已有现成 PNG | 正确处理 |
|---|---|---|---|
| `history_rgb_t-2/t-1/t.png` | 是 | 未发现 | 从同一冻结 `.nc` 导出 |
| `history_ndvi_t.png` | 是，波段派生 | 未发现 | 从 B8A/B04 计算后导出 |
| `valid_mask_t.png` | 是 | 未发现 | 从 SCL/availability 导出 |
| `target_ndvi_h20.png` | 是，未来真实观测 | 未发现 | 从同一 `.nc` 的未来 target 导出 |
| `future_weather_actual.png` | 是 | 未发现 | 从 `e_key` 未来天气画条带/折线 |
| `future_weather_donor.png` | donor 数据集样本 | 未发现 | 从对应 `c_key` 的未来天气导出 |
| `future_weather_mean.png` | 否，是协议控制 | 未发现 | 按冻结 normalization 定义生成 |
| `forecast_ndvi_h20.png` | 否，是模型输出 | 未发现 | 只能从已有预测缓存导出 |
| `b_h.png` | 否，是模型输出 | 未发现 | 只能从已有模型中间输出导出 |
| `r_h.png` | 否，是模型内部贡献 | 未发现 | 只能从已有模型中间输出导出 |
| `z_t / z_{t+h}` | 否，是内部状态 | 未发现 | Figure 1 可用抽象张量图标，不冒充真实热图 |

注：`target_ndvi_h2e.png` 是此前清单中的笔误，应为 `target_ndvi_h20.png`；若最终
选的不是第 20 个预测步，应按真实步号重命名，不能为了版面沿用错误的 `h20`。

### 17.5 同一 minicube / 同一 AOI 到底是什么意思

- **同一 minicube**：同一个时空样本文件；历史 EO、未来 target 和 actual weather
  来自同一条样本记录；
- **同一 AOI**：相同经纬度范围、相同像素网格和相同裁切框；
- 图中的 historical EO、forecast 与 observed future 必须像“同一块地的前后变化”，
  不能分别从三个不同地点找好看的图拼起来；
- matched donor 只替换天气输入，不把 donor 地点的 EO 当作 extreme 样本的未来
  target。

### 17.6 当前 Figure 1 可以立即使用与必须等待的元素

可以立即制作：

```text
✓ Panel (a) 的概念性 action / weather / EO 图标
✓ Panel (b) 的 q/P、T、O、z_t、z_{t+h} 抽象可编辑对象
✓ Q2 state-removal 断路口
✓ Q3 actual / donor / mean 三选一接口
✓ Panel (c) 的 Q1→Q2→Q3 证据层级
✓ 从冻结 .nc 导出的 historical EO、target 和天气可视化
```

必须等待可追溯模型缓存，或暂时保留为空槽：

```text
! TerraState actual-weather forecast
! donor-weather forecast
! normalized-mean-weather forecast
! context-only forecast b_h
! state contribution r_h
! 真实内部状态热图
```

若拿不到这些缓存，Figure 1 仍可成立：Panel (b) 用真实历史 EO 作为输入，用抽象
forecast 小图框表示输出类型；但不得把互联网图片标成 “TerraState forecast”，也不得
把随机热图标成 \(r_h\) 或内部状态。

### 17.7 建议交给证据/模型会话的只读导出请求

不要重新评估模型。应请求从**冻结样本与已有预测缓存**中整理一个定性素材包：

```text
sample_id.txt
source_nc_sha256.txt
history_rgb_01.png
history_rgb_02.png
history_rgb_03.png
history_ndvi_last.png
valid_mask_last.png
target_ndvi_step20.png
weather_actual.csv
weather_donor.csv
weather_normalized_mean.csv
forecast_actual_step20.png
forecast_donor_step20.png          # 可选
forecast_mean_step20.png           # 可选
context_only_b_h_step20.png        # 可选
state_contribution_r_h_step20.png  # 可选
ASSET_PROVENANCE.json
```

`ASSET_PROVENANCE.json` 至少记录：

```text
e_key / c_key
原始 .nc SHA
checkpoint 标识
预测缓存路径与 SHA
时间步定义
波段与 NDVI 变换
mask 定义
天气变量顺序
归一化版本
导出脚本版本
```

样本选择不应按“效果最大”挑点。优先使用预先声明的可视化质量标准，例如：

```text
1. 所有来源与 SHA 完整；
2. 历史和未来有效像素比例足够；
3. 地表纹理/地块边界可辨；
4. 无大面积云遮挡；
5. 不依据模型误差或干预效果挑选。
```

这样，Figure 1 使用的真实图片既有视觉辨识度，也不会构成结果导向的挑样。

### 17.8 已生成的可直接使用素材包

真实素材现已导出到：

```text
TerraState_AAAI27/figure_workspace/fig1_real_asset_pack/
```

最先查看：

```text
fig1_real_asset_pack/qa/FIG1_REAL_ASSET_CONTACT_SHEET.png
```

完整文件—用途对应说明：

```text
fig1_real_asset_pack/ASSET_INDEX_ZH.md
```

作者直接排图时，优先使用已经整理并重新命名的：

```text
fig1_real_asset_pack/copy_ready_primary/
```

#### 对应本蓝图的具体位置

| 本蓝图位置 | 直接可用文件 |
|---|---|
| Panel (a) Historical/Sparse EO | `copy_ready_primary/panel_a_eo/historical_observation.png` |
| Panel (a) Future EO/observation | `copy_ready_primary/panel_a_eo/future_observation.png` |
| Panel (b) B1 Historical context | `copy_ready_primary/panel_b_historical_context/history_rgb_strip.png` |
| Panel (b) B1 单张历史 RGB | `copy_ready_primary/panel_b_historical_context/history_rgb_latest.png` |
| Panel (b) B1 历史 NDVI | `copy_ready_primary/panel_b_historical_context/history_ndvi_latest.png` |
| Panel (b) actual weather | `copy_ready_primary/panel_b_weather_intervention/actual_weather_strip.png` |
| Panel (b) matched donor | `copy_ready_primary/panel_b_weather_intervention/matched_donor_weather_strip.png` |
| Panel (b) normalized mean | `copy_ready_primary/panel_b_weather_intervention/normalized_mean_weather_strip.png` |
| Panel (b) 三种天气参考 | `copy_ready_primary/panel_b_weather_intervention/weather_three_arm_reference.png` |
| Panel (b) observed future/target | `copy_ready_primary/panel_b_observed_future/observed_future_ndvi_step20.png` |
| 可选 DEM | `copy_ready_primary/optional_static/dem_elevation.png` |
| 可选 hillshade | `copy_ready_primary/optional_static/dem_hillshade.png` |
| 可选 land cover | `copy_ready_primary/optional_static/landcover_esa_worldcover.png` |

这里的 `future_observation` 和 `observed_future` 都是数据集真实 target，不是
TerraState forecast。当前仍然没有可追溯的：

```text
forecast
b_h
r_h
真实 z_t / z_{t+h} 热图
```

对应提醒文件：

```text
fig1_real_asset_pack/copy_ready_primary/
model_outputs_NOT_AVAILABLE/README.md
```

推荐主样本是：

```text
sample_01_JAS21_minicube_197_34SEJ_39.50_21.71
```

它在固定导出时点的平均有效像素比例为 0.9978，最低为 0.9869，并含有清晰的耕地、
道路和建成区纹理。另有两个备选样本保存在 `samples/` 中。

导出脚本、选择记录、逐样本 provenance 和全部 SHA 分别位于：

```text
fig1_real_asset_pack/source/export_fig1_real_assets.py
fig1_real_asset_pack/data/selection_record.json
fig1_real_asset_pack/samples/<sample>/provenance/ASSET_PROVENANCE.json
fig1_real_asset_pack/SHA256SUMS.txt
```
