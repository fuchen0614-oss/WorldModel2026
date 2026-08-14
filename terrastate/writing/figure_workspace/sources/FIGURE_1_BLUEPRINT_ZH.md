# Figure 1 精准施工蓝图：从EO世界模型逻辑到可检验的内部路径

> 状态：可直接据此重画 Figure 1。  
> 施工语言：蓝图采用中英双语；论文成图只保留英文。  
> 图的类型：概念—主张—证据图，不是完整方法架构图，也不是结果图。

## 1. Figure 1 的唯一任务

Figure 1 必须让审稿人在十秒内读懂三件事：

1. **问题是什么**：终点预测精度可以评价输出，却不能单独说明内部状态和天气驱动路径是否真的被使用；
2. **TerraState做了什么**：把历史形成的预测状态、天气条件转移和状态读出组织成可直接干预的路径；
3. **如何证明**：用 Q1–Q3 形成由“预测有用”到“状态承载预测”再到“天气驱动有依据”的层级证据。

全图唯一叙事链：

```text
(a) Endpoint scoring leaves an internal validation gap
    终点评分留下内部验证缺口
                         →
(b) TerraState exposes testable state and forcing pathways
    TerraState暴露可干预的状态与天气路径
                         →
(c) Q1–Q3 provide hierarchical evidence
    Q1–Q3提供层级证据
```

Figure 1 不承担以下任务：

- 不展开 `q`、`P`、`T`、`O` 的完整实现细节；
- 不展示训练阶段、教师模型、未来状态监督或损失函数；
- 不放实验数值、置信区间、柱状图或折线图；
- 不宣称其他EO预测模型“不是世界模型”；
- 不宣称 temporal composition、极端天气特异性增强或物理约束；
- 不代替 Figure 2 的方法架构，也不代替 Figure 3 的定量结果。

## 2. 参考图的借鉴原则

### 2.1 可借鉴 EO-WM Figure 1

可以借鉴：

- 用上下对齐的方式映射一般世界模型与EO世界建模；
- 用真实EO缩略图建立遥感视觉锚点；
- 把外部驱动单独接入状态转移；
- 在概念映射之后自然引出本文缺口。

不能照搬：

- 不复制汽车、道路、地球图标、编号、配色或具体排版；
- 不复制极端夏季、跨年份或异常响应的任务定义；
- 不使用 EO-WM 的 climatology、anomaly 或 stress 机制；
- 不把 Figure 1 停在“action 被 weather 替代”这一层类比。

TerraState必须比概念映射多走一步：

> **Endpoint accuracy alone does not test whether the internal state or forcing pathway is used.**

### 2.2 可借鉴优秀AAAI方法概览图

可以借鉴：

- 大面板先分区，再在面板内部布置小块；
- 主路径使用粗实线，干预使用短虚线或断点；
- 每个面板只回答一个问题；
- 真实图片只作为语义锚点，不让图片数量压过逻辑关系；
- 模块名称短、字号足、层级清楚。

不借鉴：

- 不使用复杂网络层堆叠来制造“技术感”；
- 不使用彩虹节点、粗黑边框、大面积渐变或立体阴影；
- 不用装饰性图标替代核心因果关系；
- 不把概念、架构、训练和结果全部塞进同一张图。

### 2.3 TerraState自己的视觉识别

Figure 1 的视觉识别由三种元素构成：

1. **蓝灰色概念映射**：Panel (a)，说明EO世界建模中的验证缺口；
2. **蓝绿状态路径 + 橙色天气入口**：Panel (b)，突出可干预内部路径；
3. **由浅到深的Q1–Q3证据阶梯**：Panel (c)，Q2视觉权重最高。

三种元素应形成同一阅读方向，但不能画成三个互不相关的海报卡片。

## 3. 画布与区域比例

### 3.1 画布

- 形式：AAAI双栏通栏；
- 推荐尺寸：`7.0 × 3.20 in`；
- 可接受高度：`3.05–3.35 in`；
- 页面边距：左右各约 `0.10 in`，上下各约 `0.08 in`；
- 图内不放总标题；完整标题进入 caption；
- 最终导出优先使用 PDF/SVG 矢量格式，并保留可编辑 PPTX。

### 3.2 三个连续大块

| 大块 | 英文面板标题 | 中文施工解释 | 推荐宽度 |
|---|---|---|---:|
| A / Panel (a) | `World-model logic meets EO` | 世界模型逻辑进入EO后的验证缺口 | 37% |
| B / Panel (b) | `TerraState exposes testable pathways` | TerraState暴露可检验路径 | 39% |
| C / Panel (c) | `Operational evidence` | Q1–Q3操作性证据 | 22% |
| 面板间距 | — | 两条细分隔带 | 2% |

面板间使用浅灰细竖线或 `0.05–0.07 in` 留白，不使用三个厚重外框。

### 3.3 垂直比例

| 垂直区域 | 推荐占比 | 用途 |
|---|---:|---|
| 面板标题区 | 9% | `(a)/(b)/(c)` 与短标题 |
| 主体逻辑区 | 72% | 概念映射、状态路径、Q1–Q3 |
| 底部收束区 | 19% | 验证带、干预标签或层级说明 |

Panel (c)可以把主体逻辑区与底部收束区合并为一条连续证据阶梯。

### 3.4 最重要的层级：3个大块分别包住哪些小块

```text
FIGURE 1 / 图1
│
├── A / PANEL (a)
│   World-model logic meets EO / 世界模型逻辑进入EO
│   │
│   ├── A1  Typical action-conditioned world model
│   │       典型动作条件世界模型
│   │       scene history → latent state → driven transition → future rollout
│   │                                      ↑ action
│   │
│   ├── A2  EO world modeling under exogenous forcing
│   │       外生驱动下的EO世界建模
│   │       sparse EO → Earth-surface state → EO dynamics → future EO
│   │                                         ↑ future weather
│   │
│   └── A3  Endpoint-scoring gap
│           终点评分缺口
│           output directly scored | state use ? | forcing use ?
│
├── B / PANEL (b)
│   TerraState exposes testable pathways / TerraState暴露可检验路径
│   │
│   ├── B1  Historical context / 历史上下文
│   ├── B2  History-only predictive state z_t / 仅由历史形成的预测状态
│   ├── B3  Weather-conditioned transition path / 天气条件转移路径
│   │       actual | matched donor | normalized mean → T
│   ├── B4  Evolved state and readout / 演化状态与读出
│   │       z_{t+h} → O → r_h
│   ├── B5  Context-only bypass and forecast closure / 上下文旁路与预测闭合
│   │       b_h + r_h → forecast
│   ├── B6  Q2 state-path intervention / Q2状态路径干预
│   └── B7  Q3 weather intervention / Q3天气干预
│
└── C / PANEL (c)
    Operational evidence / 操作性证据
    │
    ├── C1  Q1 Predictive utility / 预测效用
    │       forecasting prerequisite / 预测前提
    ├── C2  Q2 Load-bearing state / 承载预测的状态
    │       defining state evidence / 定义性状态证据
    └── C3  Q3 Weather-response fidelity / 天气响应保真度
            external-forcing grounding / 外部驱动落地
```

### 3.5 大块、小块和视觉元素如何区分

| 层级 | 画法 | 是否带标题 | 是否允许单独底色 |
|---|---|---|---|
| 大块 A/B/C | 浅色背景区或细分隔线 | 必须 | 允许极浅底色 |
| 小块 A1–C3 | 内容组，不使用厚重卡片 | 必须有短标签 | 仅Q1–Q3允许浅色卡片 |
| 模块 \(z_t,T,O\) | 圆角矩形、张量格或窄网络块 | 使用短英文 | 允许语义色 |
| 真实图片槽 | 薄边框、统一裁切比例 | 使用极短标签 | 不使用装饰底色 |
| 干预端口 | 断点、选择器或短虚线 | 必须标Q2/Q3 | 使用橙红强调 |
| 解释句 | 仅caption或蓝图保留 | 最终图默认删除 | 不单独成框 |

## 4. 全图快速草图

```text
┌─────────────────────────────┬───────────────────────────────┬────────────────────┐
│ (a) World-model logic       │ (b) TerraState exposes       │ (c) Operational    │
│     meets EO                │     testable pathways        │     evidence       │
│                             │                               │                    │
│ ACTION-CONDITIONED WM       │                    actual     │ Q1 Predictive      │
│ scene → latent → T → future │ history       donor ──◇      │ utility            │
│                  ↑ action   │ context        mean  ──┘      │ PREREQUISITE       │
│                             │    │               ↓          │         ↓          │
│ EO WORLD MODELING           │    ├→ b_h ──────────────┐     │ Q2 Load-bearing    │
│ EO → Earth state → T → EO   │    │                    │     │ state              │
│                  ↑ weather  │    └→ z_t → T → z_h → O │     │ DEFINING EVIDENCE  │
│                             │                    → r_h│     │         ↓          │
│ ENDPOINT-SCORING GAP        │                Q2 ×  └→ ⊕→ŷ  │ Q3 Weather-        │
│ output ✓ | state ? | w ?    │                Q3 ↺ weather  │ response fidelity  │
│                             │                               │ FORCING GROUNDING  │
└─────────────────────────────┴───────────────────────────────┴────────────────────┘
```

### 4.1 给绘图同事的中英双语施工标注

#### Panel (a)：概念映射与缺口

| 编号 | 最终英文 | 中文施工解释 | 推荐视觉 |
|---|---|---|---|
| A1 | `Typical action-conditioned world model` | 典型动作条件世界模型 | 两帧场景、状态格、转移块、未来帧 |
| A2 | `EO world modeling under exogenous forcing` | 外生驱动下的EO世界建模 | 真实历史EO、抽象Earth state、天气入口、未来EO |
| A3 | `What endpoint scoring reveals` | 终点评分能直接揭示什么 | 评分尺 + 两个待检验问号 |

#### Panel (b)：可检验路径

| 编号 | 最终英文 | 中文施工解释 | 推荐视觉 |
|---|---|---|---|
| B1 | `Historical context` | 历史EO、历史天气和静态上下文的集合 | 2–3张真实EO缩略图 |
| B2 | `History-only predictive state \(z_t\)` | 只由历史形成的预测状态 | 蓝绿色张量格 |
| B3 | `Shared weather-conditioned \(T\)` | 接收未来天气的共享转移 | 蓝紫色转移块 + 橙色天气入口 |
| B4 | `Evolved predictive state \(z_{t+h}\)` | 转移后的预测状态 | 同形异纹理张量格 |
| B5 | `State readout \(O\)` | 把未来状态读出为状态贡献 | 窄漏斗或窄矩形 |
| B6 | `State contribution \(r_h\)` | 状态路径对最终预测的贡献 | 有符号图槽或符号框 |
| B7 | `Context-only forecast \(b_h\)` | 不经过状态贡献支路的上下文预测 | 细灰蓝旁路 |
| B8 | `Forecast` | 最终植被预测 | 真实预测图或预测图槽 |
| B9 | `Q2 · State-path intervention` | 在 \(r_h\) 进入合并点前切断 | 断路开关 |
| B10 | `Q3 · Weather intervention` | 仅替换进入 \(T\) 的未来天气 | 三路选择器 |

#### Panel (c)：层级证据

| 编号 | 最终英文 | 中文施工解释 | 推荐视觉 |
|---|---|---|---|
| C1 | `Q1 · Predictive utility` | 首先证明模型具有可用预测能力 | 小型预测箭头 + 勾 |
| C2 | `Q2 · Load-bearing state` | 移除状态贡献后性能下降 | 最大卡片 + 断路状态支路 |
| C3 | `Q3 · Weather-response fidelity` | 真实天气优于天气控制 | 实线天气与两条虚线控制 |

### 4.2 一眼可照着画的双语版线框

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│ A / PANEL (a)                                                                    │
│ World-model logic meets EO / 世界模型逻辑进入EO                                   │
│                                                                                  │
│ ┌──────────────────────────────────────────────────────────────────────────────┐ │
│ │ A1 Typical action-conditioned world model / 典型动作条件世界模型             │ │
│ │ [scene history/场景历史] → [latent state/潜在状态] → [T/转移] → [future/未来]│ │
│ │                                                        ↑ action/动作          │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
│                                      ↓ domain mapping / 领域映射                  │
│ ┌──────────────────────────────────────────────────────────────────────────────┐ │
│ │ A2 EO world modeling under exogenous forcing / 外生驱动下的EO世界建模         │ │
│ │ [sparse EO/稀疏EO] → [Earth state/地表状态] → [T/转移] → [future EO/未来EO]  │ │
│ │                                                     ↑ future weather/未来天气 │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
│                                      ↓                                            │
│ ┌──────────────────────────────────────────────────────────────────────────────┐ │
│ │ A3 What endpoint scoring reveals / 终点评分可揭示的内容                       │ │
│ │ [Output directly scored/输出直接评分]  [State use ?/状态是否使用？]           │ │
│ │                                        [Forcing use ?/驱动是否使用？]          │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│ B / PANEL (b)                                                                    │
│ TerraState exposes testable pathways / TerraState暴露可检验路径                   │
│                                                                                  │
│ B1 Historical context / 历史上下文                                                │
│ [real EO/真实EO] [past weather/历史天气] [static/静态属性]                        │
│            │                                                                     │
│            ├────────────→ B7 Context-only forecast b_h / 上下文预测 ─────────┐   │
│            │                                                               │   │
│            ↓                                                               │   │
│ B2 History-only z_t / 历史状态 → B3 Shared T / 共享转移 → B4 z_{t+h}/未来状态 │   │
│                                      ↑                                     │   │
│                      ┌───────────────◇ B10 Q3天气干预                       │   │
│                      │ actual / 真实天气                                    │   │
│                      │ matched donor / 匹配供体                              │   │
│                      └ normalized mean / 归一化均值                          │   │
│                                                                            ↓   │
│                                   B5 State readout O / 状态读出 → B6 r_h ──×──┤ │
│                                                                       B9 Q2 │ │
│                                                                            ⊕ │
│                                                                            ↓ │
│                                                           B8 Forecast / 预测 │
└──────────────────────────────────────────────────────────────────────────────────┘
```

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│ C / PANEL (c)                                                                    │
│ Operational evidence / 操作性证据                                                 │
│                                                                                  │
│ ┌──────────────────────────────────────────────────────────────────────────────┐ │
│ │ C1 Q1 · Predictive utility / 预测效用                                         │ │
│ │ Useful OOD-t forecast / 有用的OOD-t预测                                      │ │
│ │ PREREQUISITE / 前提                                                           │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
│                       ↓ necessary, not sufficient / 必要但不充分                  │
│ ┌──────────────────────────────────────────────────────────────────────────────┐ │
│ │ C2 Q2 · Load-bearing state / 承载预测的状态                                  │ │
│ │ Skill degrades without r_h / 移除状态贡献后性能下降                          │ │
│ │ DEFINING EVIDENCE / 定义性证据                                                │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
│                       ↓ ground the declared driver / 落实所声明的驱动             │
│ ┌──────────────────────────────────────────────────────────────────────────────┐ │
│ │ C3 Q3 · Weather-response fidelity / 天气响应保真度                           │ │
│ │ Actual weather outperforms controls / 真实天气优于控制                       │ │
│ │ FORCING GROUNDING / 驱动落地                                                  │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 补充线框一：先搭全图大块与跨块关系

```text
┌───────────────────────┐   ┆   ┌────────────────────────┐   ┆   ┌─────────────────┐
│ A CONCEPTUAL GAP      │   ┆   │ B TESTABLE PATHWAYS    │   ┆   │ C EVIDENCE      │
│ 概念缺口              │   ┆   │ 可检验路径             │   ┆   │ 层级证据        │
└───────────────────────┘   ┆   └────────────────────────┘   ┆   └─────────────────┘
              conceptual hand-off →       operationalization →       evidence
              概念交接                     操作化                     证据
```

最终图不建议画贯穿三块的大箭头。可在两个分隔带上方各放一个极小箭头，或仅依靠从左到右
的版面阅读。若加箭头，箭头不得穿过面板内部内容。

### 4.4 补充线框二：大块 A 内部怎么画

```text
A PANEL
│
├── A1 上行：一般世界模型
│   2帧抽象场景 → 潜在状态格 → 转移块 → 2帧未来场景
│                                 ↑ action
│
├── 中间：一条细向下映射箭头
│   action-conditioned → exogenous forcing
│
├── A2 下行：EO世界建模
│   3张真实历史EO → 半透明地表状态格 → EO转移块 → 1张真实未来EO
│                                         ↑ future weather strip
│
└── A3 底部验证带
    [metric ruler + Output directly scored]
    [probe + State use ?]
    [probe + Forcing use ?]
```

A1与A2需要在四个位置上对齐，使“scene/EO、state、transition、future”的对应关系无需
阅读长句即可理解。

### 4.5 补充线框三：大块 B 内部怎么画

```text
B PANEL
│
├── 左侧 B1：Historical context
│   [EO][EO][EO] + [weather strip] + [static tab]
│
├── 中心粗状态路径
│   B1 → B2 z_t → B3 T → B4 z_{t+h} → B5 O → B6 r_h
│
├── 上方橙色天气路径
│   actual ─────────┐
│   matched donor ──┼→ ◇ → B3 T
│   normalized mean ┘
│
├── 下方细灰蓝旁路
│   B1 → B7 b_h ───────────────────────────┐
│                                         ⊕ → B8 Forecast
│   B6 r_h ─────────────── B9 Q2断点 ─────┘
│
└── 两个接口
    B9 Q2：只切断 r_h → ⊕
    B10 Q3：只替换 future weather → T
```

Panel B是全图视觉中心。中心状态路径必须比 \(b_h\) 旁路粗；天气入口必须醒目，但不能比
状态路径更粗。

### 4.6 补充线框四：大块 C 内部怎么画

```text
C PANEL
│
├── C1 小卡：Q1 Predictive utility
│   高度约26%，浅蓝，表示预测前提
│
├── 细向下箭头：necessary, not sufficient
│
├── C2 主卡：Q2 Load-bearing state
│   高度约34%，蓝绿色，边框最深，表示定义性核心
│
├── 细向下箭头：ground the declared driver
│
└── C3 小卡：Q3 Weather-response fidelity
    高度约28%，浅橙，表示天气驱动落地
```

三个卡片不是三个同权重任务：

- Q1是必要前提；
- Q2是本文最核心的内部状态证据；
- Q3为所声明的天气驱动路径提供行为落地。

### 4.7 绘图时的推荐顺序

```text
第1步：只画 A、B、C 三个大区和两条分隔带
第2步：在 A 中画上下两行的四列对齐
第3步：在 B 中先画唯一中心状态路径，再画 b_h 旁路和天气入口
第4步：在 B 中加入 Q2 断点和 Q3 选择器
第5步：在 C 中画 Q1→Q2→Q3 层级，先确保 Q2 最醒目
第6步：替换真实EO、未来EO和预测图槽
第7步：最后检查英文、箭头、字号和caption
```

## 5. 全图逻辑与主张边界

Figure 1 必须忠实表达以下逻辑，而不展开完整实现：

\[
\text{history}\rightarrow z_t,\qquad
z_{t+h}=T(z_t,u_{t:t+h}),\qquad
r_h=O(z_{t+h}),
\]

\[
\widehat y_{t+h}=b_h+r_h.
\]

其中：

- `history`代表历史EO、历史环境上下文和静态信息的概念集合；
- \(z_t\)只由历史上下文形成；
- \(u_{t:t+h}\)代表未来气象驱动，只进入 \(T\)；
- \(T\)是天气条件状态转移；
- \(O\)把演化状态读出为状态贡献 \(r_h\)；
- \(b_h\)是仅依赖上下文的预测旁路；
- Q2移除 \(r_h\) 时必须保留 \(b_h\)；
- Q3只替换进入 \(T\) 的未来天气；
- geography \(g\)、forecast horizon \(h\)、`q`和`P`由 Figure 2 展开；
- Figure 1 不把 \(T\) 画成循环 rollout，不暗示已经证明时间组合性。

本文的操作性证据链是：

```text
Q1: forecast is useful
    预测首先具有实际效用
             ↓
Q2: the declared state path carries predictive information
    所声明的状态路径确实承载预测
             ↓
Q3: behavior changes appropriately under controlled weather replacement
    在受控天气替换下产生相应行为变化
```

这是一套针对 TerraState 主张的操作性检验，不是对所有世界模型的唯一普适定义。

## 6. Panel (a)：World-model logic meets EO

### 6.1 本区块回答什么

**世界模型的“观测—状态—驱动转移—未来”逻辑进入EO后发生了什么变化，为什么只评分
未来输出仍会留下内部验证缺口？**

### 6.2 主体结构

Panel (a)使用“两行对齐 + 一条验证带”：

```text
              OBSERVATION       INTERNAL STATE      DRIVEN TRANSITION      FUTURE

Action WM     scene history  →  latent state     →  dynamics           →  rollout
                                                       ↑ action

EO WM         sparse EO      →  Earth state      →  EO dynamics        →  future EO
                                                       ↑ future weather

Endpoint      output directly scored | state use ? | forcing use ?
```

这不是“普通预测器 vs TerraState”的胜负对比，也不判断其他EO方法是否属于世界模型。

### 6.3 视觉结构

#### A1 Typical action-conditioned world model

- 使用2张原创抽象场景帧表示scene history；
- 使用4×4灰蓝张量格表示latent state；
- 使用带一个下方驱动端口的紧凑转移块表示dynamics；
- action以小弯箭头从下方进入dynamics；
- 使用2–3张轻微变化的抽象未来帧表示future rollout。

#### A2 EO world modeling under exogenous forcing

- 使用同一minicube的2–3张真实历史EO图；
- 使用半透明空间张量表示unobserved Earth-surface state；
- 未来天气以窄橙色条带从下方进入EO dynamics；
- 使用同一cube/crop的真实未来EO或NDVI图；
- A2四个位置必须与A1四个位置对齐。

#### A3 Endpoint-scoring gap

- `Output directly scored`使用小型评分尺或勾；
- `State use ?`与`Forcing use ?`使用探针或问号；
- 后两项视觉相同，表示都需要专门验证；
- 不画“not a world model”、红叉或贬低其他方法的图标。

### 6.4 相对位置

| 区域 | Panel (a)内部高度 |
|---|---:|
| 面板标题 | 9% |
| 四列短标题 | 7% |
| A1上行 | 22% |
| 行间映射与留白 | 5% |
| A2下行 | 28% |
| A3验证带 | 23% |
| 底部留白 | 6% |

四列宽度：

| 列 | 相对宽度 |
|---|---:|
| Observation | 23% |
| Internal state | 20% |
| Driven transition | 28% |
| Future | 23% |
| 箭头与留白 | 6% |

### 6.5 箭头

1. scene history → latent state；
2. latent state → dynamics；
3. action从下方进入dynamics；
4. dynamics → future rollout；
5. sparse EO history → unobserved Earth-surface state；
6. Earth-surface state → EO dynamics；
7. future weather从下方进入EO dynamics；
8. EO dynamics → future EO；
9. future EO向下对应`Output directly scored`；
10. Earth-surface state向下对应`State use ?`；
11. future-weather入口向下对应`Forcing use ?`。

### 6.6 可直接使用的英文

面板标题：

> **(a) World-model logic meets EO**

行标题：

> **Typical action-conditioned world model**  
> **EO world modeling under exogenous forcing**

列标题：

> **Observation**  
> **Internal state**  
> **Driven transition**  
> **Future**

模块：

> scene history  
> latent state  
> action  
> dynamics  
> future rollout  
> sparse EO history  
> unobserved Earth-surface state  
> future weather  
> EO dynamics  
> future EO

验证带：

> **What endpoint scoring reveals**  
> Output directly scored  
> State use ?  
> Forcing use ?

以下收束句只进入caption，默认不放在图内：

> Endpoint accuracy alone does not test the internal state or forcing pathway.

## 7. Panel (b)：TerraState exposes testable pathways

### 7.1 本区块回答什么

**TerraState怎样把EO世界模型中原本只能假设存在的状态和天气路径，变成可以直接干预的
预测载体？**

### 7.2 主体结构

```text
                         actual
Historical context      matched donor ──◇──→ shared weather-conditioned T
 [EO + past w + static] normalized mean          │
        │                                         ▼
        ├────────→ context-only forecast b_h ──────────────┐
        │                                                  │
        └→ history-only z_t → shared T → z_{t+h} → O → r_h ├→ ⊕ → forecast
                                                   Q2 × ───┘
                              Q3 ↺ replace weather
```

### 7.3 视觉结构

#### Historical context

- 2–3张同一minicube的真实EO缩略图；
- 可附一张小mask、一条历史天气带和一个静态属性tab；
- 不在Figure 1逐项列出全部字段。

#### Predictive state \(z_t\)

- 使用蓝绿色4×4或6×6张量格；
- 加一个极小历史时钟，表示history-only；
- 不使用NDVI色标；
- 不声称latent channel对应具体物理变量。

#### Shared weather-conditioned \(T\)

- 使用单个紧凑转移块；
- 左侧接收\(z_t\)，上方接收未来天气；
- 不展开内部网络层；
- 不画循环箭头或多步rollout。

#### Evolved state \(z_{t+h}\) and readout \(O\)

- \(z_{t+h}\)与\(z_t\)外形一致，内部颜色或纹理轻微改变；
- \(O\)用窄漏斗或窄矩形表示；
- \(O\)只读取\(z_{t+h}\)；
- \(O\)输出状态贡献\(r_h\)。

#### Forecast closure

- \(b_h\)从Historical context直接形成一条细灰蓝旁路；
- \(r_h\)与\(b_h\)在加法节点汇合；
- 加法节点旁可写 \(\widehat y_{t+h}=b_h+r_h\)；
- 最终Forecast若使用真实图，必须来自冻结模型。

#### Q2 and Q3 intervention ports

- Q2断点只位于\(r_h\rightarrow\oplus\)；
- 切断Q2后\(b_h\)仍然连接；
- Q3选择器只位于future weather \(\rightarrow T\)；
- actual用实线，matched donor用紫色虚线，normalized mean用灰色点线。

### 7.4 相对位置

| 区域 | Panel (b)内部占比 |
|---|---:|
| 标题 | 9%高 |
| 三路天气选择器 | 上方20%高 |
| 中心状态路径 | 中部40%高 |
| \(b_h\)旁路与预测闭合 | 下方17%高 |
| Q2/Q3短标签 | 8%高 |
| 呼吸空间 | 6%高 |

水平宽度：

| 区域 | 相对宽度 |
|---|---:|
| Historical context | 18% |
| \(z_t\) | 11% |
| \(T\)及天气选择器 | 22% |
| \(z_{t+h}\)与\(O\) | 18% |
| \(r_h/b_h\)、合并点与forecast | 25% |
| 留白 | 6% |

### 7.5 箭头

正常路径：

1. historical context → history-only \(z_t\)；
2. \(z_t\) → shared weather-conditioned \(T\)；
3. weather selector → \(T\)的唯一未来天气端口；
4. \(T\) → evolved \(z_{t+h}\)；
5. \(z_{t+h}\) → state readout \(O\)；
6. \(O\) → state contribution \(r_h\)；
7. \(r_h\) → merge；
8. historical context → context-only forecast \(b_h\) → merge；
9. merge → forecast。

干预：

10. Q2断点放在\(r_h\to merge\)上；
11. Q3三路天气先进入空心选择节点，再进入\(T\)；
12. future weather不得连接\(z_t\)、\(O\)、\(b_h\)或forecast。

### 7.6 可直接使用的英文

面板标题：

> **(b) TerraState exposes testable pathways**

模块：

> **Historical context**  
> **History-only predictive state \(z_t\)**  
> **Shared weather-conditioned \(T\)**  
> **Evolved predictive state \(z_{t+h}\)**  
> **State readout \(O\)**  
> **State contribution \(r_h\)**  
> **Context-only forecast \(b_h\)**  
> **Forecast**

天气：

> actual  
> matched donor  
> normalized mean

干预：

> **Q2 · State-path intervention**  
> remove state contribution  
> **Q3 · Weather intervention**  
> replace future weather

以下问题仅用于作者理解和caption，不进入最终图：

> Does forecast skill degrade?  
> Does actual weather help?

## 8. Panel (c)：Operational evidence

### 8.1 本区块回答什么

**我们以什么层级证据判断TerraState具有可检验的预测状态与天气驱动路径？**

### 8.2 主体结构

```text
Q1  Predictive utility
    Useful OOD-t forecasting skill
    FORECASTING PREREQUISITE
                ↓ necessary, not sufficient

Q2  Load-bearing state
    Skill degrades when r_h is removed
    DEFINING STATE EVIDENCE
                ↓ ground the declared driver

Q3  Weather-response fidelity
    Actual weather outperforms controls
    EXTERNAL-FORCING GROUNDING
```

证据层级：

- Q1证明模型首先具有预测效用，但不单独证明内部世界模型路径；
- Q2检验所声明的状态贡献是否真正承担预测作用，是视觉和论证核心；
- Q3检验在预先定义的matched stratum内，真实天气是否优于matched donor和normalized mean；
- Figure 1只定义问题，不写通过/失败或具体数值；
- 数值、置信区间和结果解释交给Figure 3与表格。

### 8.3 视觉结构

#### Q1 card

- 浅蓝色；
- 小型history-to-future箭头；
- 一个克制的勾，不使用奖杯、皇冠或排行榜。

#### Q2 card

- 蓝绿色；
- 高度和边框都比Q1/Q3更强；
- 图标为状态支路、Q2断点和下降箭头；
- 不在卡片内放精度数值。

#### Q3 card

- 浅橙色；
- 一条actual实线与两条control虚线进入同一个\(T\)；
- 不使用卡通太阳、干旱裂土或极端事件照片。

### 8.4 可直接使用的英文

面板标题：

> **(c) Operational evidence**

可选小字：

> **for TerraState**

Q1：

> **Q1 · Predictive utility**  
> Useful OOD-t forecast  
> **PREREQUISITE**

连接：

> necessary, not sufficient

Q2：

> **Q2 · Load-bearing state**  
> Skill degrades without \(r_h\)  
> **DEFINING EVIDENCE**

连接：

> ground the declared driver

Q3：

> **Q3 · Weather-response fidelity**  
> Actual weather outperforms controls  
> **FORCING GROUNDING**

## 9. 图片、图标与真实性要求

| 位置 | 类型 | 给设计者的简要提示词 | 真实性要求 |
|---|---|---|---|
| A1 scene history | 原创矢量 | `two neutral 2D scene frames, simple agent and geometric objects` | 可抽象 |
| A1 latent state | 抽象张量 | `stacked 4×4 latent tensor, muted blue-gray` | 可抽象 |
| A1 action | 驱动箭头 | `small curved control arrow entering transition only` | 可抽象 |
| A1 future rollout | 原创矢量 | `two future scene frames with changed positions` | 可抽象 |
| A2 sparse EO history | 真实图片 | `three Sentinel-2 RGB or NDVI crops, same location and scale` | 必须来自真实数据 |
| A2 Earth-surface state | 抽象张量 | `semi-transparent spatial tensor with partially hidden outline` | 可抽象 |
| A2 future weather | 天气条带 | `thin multivariate weather strip, no cartoon weather icons` | 真实曲线需可追溯；符号可抽象 |
| A2 future EO | 真实图片 | `observed future EO or NDVI, same cube and crop as history` | 必须来自真实future target |
| A3 validation band | 线性图标 | `metric ruler plus two probe/question glyphs` | 可抽象 |
| B1 Historical context | 真实图组 | `real EO frames, one mask tab, narrow past-weather strip, static tab` | EO必须真实 |
| B2/B4 state | 抽象状态 | `teal 4×4 tensor with visible ports; same shape, changed texture` | 可抽象 |
| B3 weather selector | 三路输入 | `actual solid; donor dashed; mean dotted; hollow selector` | 真实曲线必须来自冻结条件 |
| B3 \(T\) | 转移模块 | `single transition block with state and weather ports` | 可抽象 |
| B5 \(O\) | 读出模块 | `narrow readout rectangle or funnel marked O` | 可抽象 |
| B6 \(r_h\) | 状态贡献 | `signed contribution slot with orange outline` | 空间图必须来自真实模型输出 |
| B7 \(b_h\) | 上下文旁路 | `thin gray-blue bypass and compact forecast slot` | 空间图必须来自真实模型输出 |
| B8 Forecast | 真实输出 | `TerraState NDVI prediction, same sample and horizon` | 必须来自冻结模型 |
| B9 Q2 | 干预图标 | `open-circuit switch on r_h branch; b_h remains connected` | 可抽象 |
| B10 Q3 | 干预图标 | `three weather traces merged before T only` | 可抽象或真实条件 |
| C1 Q1 | 证据图标 | `history-to-future arrow with restrained check mark` | 可抽象 |
| C2 Q2 | 证据图标 | `state branch, open-circuit cut, skill-down arrow` | 可抽象 |
| C3 Q3 | 证据图标 | `one solid weather path versus two dashed controls` | 可抽象 |

真实素材优先级：

1. 必须优先补齐A2历史EO；
2. A2若展示future EO，必须与历史EO来自同一cube/crop；
3. B8若展示Forecast，必须来自冻结TerraState checkpoint；
4. A2 future EO与B8 Forecast优先使用同一`cube/crop/horizon`；
5. \(z_t,z_{t+h}\)允许使用抽象张量，不伪装成可解释物理地图；
6. \(b_h,r_h\)若无可追溯导出，保留明确图片槽，不用随机热图填充；
7. 外部论文截图只能作为排版参考，不能进入最终成图。

## 10. 完整可复制英文

```text
(a) World-model logic meets EO
Typical action-conditioned world model
EO world modeling under exogenous forcing
Observation
Internal state
Driven transition
Future
scene history
latent state
action
dynamics
future rollout
sparse EO history
unobserved Earth-surface state
future weather
EO dynamics
future EO
What endpoint scoring reveals
Output directly scored
State use ?
Forcing use ?

(b) TerraState exposes testable pathways
Historical context
History-only predictive state z_t
Shared weather-conditioned T
Evolved predictive state z_{t+h}
State readout O
State contribution r_h
Context-only forecast b_h
Forecast
actual
matched donor
normalized mean
Q2 · State-path intervention
remove state contribution
Q3 · Weather intervention
replace future weather

(c) Operational evidence
for TerraState
Q1 · Predictive utility
Useful OOD-t forecast
PREREQUISITE
necessary, not sufficient
Q2 · Load-bearing state
Skill degrades without r_h
DEFINING EVIDENCE
ground the declared driver
Q3 · Weather-response fidelity
Actual weather outperforms controls
FORCING GROUNDING
```

## 11. 推荐配色

| 语义 | 颜色建议 |
|---|---|
| Panel (a)一般世界模型 | 中性蓝灰 |
| Panel (a) EO视觉锚点 | 低饱和自然色 |
| 当前/未来预测状态 | 蓝绿色 |
| 天气与Q3入口 | 暖橙色 |
| 共享转移 \(T\) | 蓝紫色 |
| 状态读出与\(r_h\) | 青绿色 |
| \(b_h\)旁路 | 浅灰蓝 |
| Q2干预 | 橙红色小标记 |
| Q1卡片 | 极浅蓝 |
| Q2卡片 | 浅蓝绿，边框最深 |
| Q3卡片 | 极浅橙 |

整图最多使用5个主色。状态路径、天气入口和证据卡片必须复用同一语义色，不为每个模块
另设新颜色。

## 12. 字体与线条

- 图内字体：Arial、Helvetica或论文统一无衬线字体；
- 面板标题：`8.5–9 pt`；
- 行标题与Q卡标题：`7.5–8 pt`；
- 模块标签：`7.0–7.5 pt`；
- 辅助标签：`6.5–7 pt`；
- 缩放到双栏宽度后任何文字不得小于约`6.5 pt`；
- Panel (b)中心主路径：`1.2–1.5 pt`；
- \(b_h\)旁路：`0.8–1.0 pt`；
- 干预虚线：`0.9–1.1 pt`；
- 面板分隔线：`0.5–0.7 pt`；
- 小卡边框：`0.7–0.9 pt`，Q2可提高到`1.1 pt`；
- 不使用阴影、立体浮雕、手绘抖动线或粗黑边框。

若图面拥挤，按以下顺序删减：

1. 删除四个列标题；
2. 删除`for TerraState`；
3. 把模块全称缩短为\(z_t,T,z_{t+h},O,r_h,b_h\)；
4. 缩减装饰图标；
5. 不得删除\(b_h\)旁路、Q2断点、Q3天气入口或Q1–Q3层级。

## 13. PPT施工顺序

1. 将页面设为`7.0 × 3.20 in`；
2. 建立A/B/C三个浅色背景区和两条分隔带；
3. 在A中建立四列网格，先画A1与A2的对齐关系；
4. 在A底部加入A3验证带；
5. 在B中先画粗状态主路径；
6. 从Historical context画出细\(b_h\)旁路；
7. 从上方加入三路天气选择器，只连接\(T\)；
8. 加入\(r_h+b_h\)预测闭合；
9. 最后放置Q2断点和Q3替换接口；
10. 在C中建立Q1→Q2→Q3阶梯，确保Q2最醒目；
11. 替换真实EO、future EO和Forecast图片槽；
12. 检查所有英文与本蓝图第10节一致；
13. 导出PDF/SVG并检查缩小后的可读性；
14. 保存原始PPTX，所有文字、模块、箭头和图片槽保持可编辑。

## 14. Figure 1 英文 caption

**Figure 1: From EO world-model structure to testable state and forcing pathways.**
**(a)** Typical action-conditioned world models and EO world modeling under exogenous forcing
share an observation–state–transition–future structure. In EO, sparse and cloud-obscured
observations replace dense scene histories, while future weather serves as the external driver.
Endpoint scoring directly evaluates the future output, but does not by itself test whether the
internal state or forcing pathway is used. **(b)** TerraState exposes a history-only predictive
state, a shared weather-conditioned transition, and a state readout whose contribution \(r_h\)
is combined with a context-only forecast \(b_h\). Q2 removes \(r_h\) while retaining \(b_h\);
Q3 replaces only the future weather entering the transition with matched-donor or
normalized-mean controls. **(c)** The evidence is hierarchical: Q1 establishes forecasting
utility as a prerequisite, Q2 tests whether the state is load-bearing, and Q3 grounds the
transition in actual weather within the evaluated matched stratum. This is our operational test
of TerraState rather than a universal definition of world modeling.

## 15. Figure 1 中文 caption

**图1：从EO世界模型结构到可检验的状态与驱动路径。**
**（a）**典型动作条件世界模型与外生驱动下的EO世界建模共享“观测—状态—转移—未来”
结构。在EO中，稀疏且受云遮挡的遥感观测取代密集场景历史，未来天气成为外部驱动。终点
评分可以直接评价未来输出，却不能单独检验内部状态或天气路径是否被真正使用。
**（b）**TerraState暴露仅由历史上下文形成的预测状态、共享天气条件转移，以及与仅上下文
预测\(b_h\)合并的状态贡献\(r_h\)。Q2在保留\(b_h\)的同时移除\(r_h\)；Q3只把进入
转移的未来天气替换为匹配供体或归一化均值控制。**（c）**证据具有层级：Q1将预测效用作为
前提，Q2检验状态是否真正承载预测，Q3在所评估的匹配样本层内把转移落到真实天气驱动上。
这是本文对TerraState的操作性检验，而不是世界模型的唯一普适定义。

## 16. 与 Figure 2 和 Figure 3 的去重边界

### 16.1 Figure 1 负责

- 为什么终点预测精度不足以支持内部世界模型主张；
- TerraState暴露了哪两类可干预路径；
- Q1、Q2、Q3之间的证据层级；
- “可检验预测状态”这一核心卖点。

### 16.2 Figure 2 负责

- 历史输入如何进入`q`；
- `q`如何同时产生\(b_{1:H}\)和供`P`使用的特征；
- `P`如何形成\(z_t\)；
- geography \(g\)和horizon \(h\)如何进入\(T\)；
- \(T\)、\(O\)以及\(\widehat y_{t+h}=b_h+r_h\)的完整方法架构；
- Q2/Q3干预端口在真实架构中的准确位置。

因此Figure 1中的Panel (b)只画最小概念闭合，不展开`q/P/g/h`或网络内部结构。

### 16.3 Figure 3 负责

- Q1预测结果；
- Q2移除状态贡献后的定量变化与置信区间；
- Q3真实天气和控制天气的定量比较；
- 结果图、统计量和视觉案例。

Figure 1的Panel (c)只定义证据问题，不提前呈现数值或结论强度。

## 17. 禁止项

- 不写`full24`、`Stage A/B`、`Phase I/II`、`boundary80`、`MAIN-last`；
- 不画cache、checkpoint、SHA、DDP、GPU、batch或工程目录；
- 不出现teacher、KD、future-state target、训练阶段或损失权重；
- 不把future weather输入\(z_t\)、\(O\)、\(b_h\)或最终forecast；
- 不把observed future EO接入推理主路径；
- 不把\(T\)画成循环rollout；
- 不宣称temporal composition或Q4；
- 不宣称extreme-specific enhancement；
- 不使用`physics-informed`、`physically constrained`或未实现的物理机制；
- 不使用`MMDiT`等与真实模型不符的网络名称；
- 不把普通EO预测模型写成“不是世界模型”；
- 不把本文Q1–Q3写成所有世界模型的唯一标准；
- 不使用随机热图冒充内部状态、状态贡献或真实预测；
- 不把外部论文截图作为本方法图素材；
- 不在Figure 1放表格数值、误差条、置信区间或排行榜；
- 不把三个Q卡画成完全等权；Q2必须是视觉核心。

## 18. 最终验收清单

- [ ] A/B/C三个大块从左到右形成“缺口→路径→证据”；
- [ ] Panel (a)的A1与A2在observation/state/transition/future四处严格对齐；
- [ ] Panel (a)没有贬低或排除其他EO世界模型；
- [ ] Panel (a)底部清楚区分`output scored`与`state/forcing use ?`；
- [ ] Panel (b)存在连续的\(z_t\to T\to z_{t+h}\to O\to r_h\)路径；
- [ ] \(z_t\)明确为history-only；
- [ ] future weather只进入\(T\)；
- [ ] \(b_h\)旁路完整保留；
- [ ] 最终闭合正确表达为\(\widehat y_{t+h}=b_h+r_h\)；
- [ ] Q2断点只位于\(r_h\to\oplus\)；
- [ ] Q3选择器只位于future weather \(\to T\)；
- [ ] Panel (c)按Q1→Q2→Q3排列；
- [ ] Q1标为prerequisite而非世界模型充分证据；
- [ ] Q2视觉权重最高并标为defining evidence；
- [ ] Q3明确比较actual与matched donor/normalized mean controls；
- [ ] 图内不出现具体实验数值、训练阶段或工程术语；
- [ ] 图内无Q4、composition、极端特异增强或物理约束主张；
- [ ] 所有英文与第10节一致；
- [ ] 所有真实图片具有可追溯来源；
- [ ] \(z_t,z_{t+h}\)等抽象张量未被表述为物理变量地图；
- [ ] PPTX中的文字、箭头、模块和图片槽均可编辑；
- [ ] PDF/SVG缩小到AAAI双栏宽度后仍能在十秒内读懂主线；
- [ ] Figure 1与Figure 2、Figure 3不存在任务重复。
