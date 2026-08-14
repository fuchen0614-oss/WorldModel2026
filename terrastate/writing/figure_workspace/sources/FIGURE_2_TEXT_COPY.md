# Figure 2 Copy-Ready Text

本文件中的英文均可直接复制到 Figure 2。优先使用“推荐文本”，只有在空间不足时才使用“短版”。

施工时可以在英文标签下一行临时放置中文说明，便于绘图同事理解；正式论文图必须删除中文说明。

推荐格式：

```text
Static geographic attributes
静态地理属性（插入：土地覆盖图 + DEM地形图）
```

大块—小块层级见`FIGURE_2_BLUEPRINT_ZH.md`第3.4–3.5节；完整中英对照、插图建议和分块线框见第4.1–4.9节。

## 1. Panel headers

推荐：

```text
(a) Multimodal context
(b) History encoding & state construction
(c) Weather-conditioned shared dynamics
(d) State readout & forecast
```

空间不足时：

```text
(a) Inputs
(b) State construction
(c) Shared dynamics
(d) Forecast
```

不要混用推荐版与短版。

## 2. Panel (a): inputs

```text
Historical Earth observations
Historical environmental context
Static geographic attributes
Future meteorological forcing
past EO
valid / cloud mask
past weather
land cover
terrain
u_{t:t+h}
```

不使用：

```text
full24
physical4
weather features
all modalities
physics inputs
```

## 3. Panel (b): history and state

```text
History encoder q
Context features
State projector P
History-only predictive state z_t
Context-only forecasts b_{1:H}
encode
project
context branch
```

若最终图只展示单一时距：

```text
Context-only forecast b_h
```

不使用：

```text
foundation model q
world state ground truth
physical state
interpretable state map
Stage-1 encoder
```

## 4. Panel (c): shared dynamics

```text
Future meteorological forcing u_{t:t+h}
Geographic context g
Forecast horizon h
Shared transition T
state–forcing interaction
shared across forecast horizons
Current predictive state z_t
Evolved predictive state z_{t+h}
Weather intervention
actual
matched donor
normalized mean
```

若三种天气需要写在同一行：

```text
actual / matched donor / normalized mean
```

不使用：

```text
physical dynamics
physics-informed transition
MMDiT
weather rollout
composable dynamics
extreme-aware transition
```

## 5. Panel (d): readout and output

```text
State readout O
State contribution r_h
Context-only forecast b_h
Forecast fusion
Vegetation forecast ŷ_{t+h}
State-path intervention
remove state contribution
h=5
h=10
h=20
reference
```

唯一建议放入图中的公式：

```text
ŷ_{t+h} = b_h + r_h
```

不使用：

```text
state output score
residual trick
closure score
final head
Q2 PASS
load-bearing result
```

## 6. Training text excluded from Figure 2

Figure 2 是纯推理架构图。以下训练相关文字全部不进入图中：

```text
Learning signals
Forecast supervision
Observed future NDVI
Frozen forecast teacher
Teacher guidance
Frozen target encoder
Future-state target z*_{t+H}
Future-state supervision
cache
KD branch
Stage 1 / Stage 2 / Stage 3
boundary80
teacher checkpoint
```

## 7. Intervention-port text

Q2位置：

```text
State-path intervention
remove state contribution
```

Q3位置：

```text
Weather intervention
replace future weather
actual / matched donor / normalized mean
```

Figure 2 中不写：

```text
Q2 LOAD_BEARING
Q3 RESPONSE_FIDELITY
significant
PASS / FAIL
```

这些属于 Figure 3 和结果表。

## 8. Legend

推荐极简图例：

```text
inference path
intervention port
```

## 9. Caption

### English

**Figure 2: TerraState architecture and testable predictive-state pathway.**
Historical Earth observations, environmental context, and static geographic attributes are encoded by \(q\). The same history-conditioned pass produces context-only forecasts \(b_{1:H}\) and, through projector \(P\), a history-only predictive state \(z_t\). Future meteorological forcing, geographic context, and the requested horizon enter only the shared transition \(T\), which evolves the state to \(z_{t+h}\). Readout \(O\) maps the evolved state to a state contribution \(r_h\), and the final vegetation forecast closes as \(\widehat y_{t+h}=b_h+r_h\). Small intervention ports expose the state-contribution and future-weather pathways used by the behavioral tests.

### 中文

**图2：TerraState架构与可检验预测状态路径。**
历史地球观测、环境上下文和静态地理属性由 \(q\) 编码。同一次历史条件前向过程产生仅依赖上下文的预测 \(b_{1:H}\)，并经投影器 \(P\) 构造仅由历史信息形成的预测状态 \(z_t\)。未来气象驱动、地理上下文和所查询的预测时距只进入共享转移 \(T\)，由其将状态推进至 \(z_{t+h}\)。读出器 \(O\) 将未来状态映射为状态贡献 \(r_h\)，最终植被预测以 \(\widehat y_{t+h}=b_h+r_h\) 闭合。两个小型干预端口暴露状态贡献和未来天气路径，以支持行为检验。

## 10. Consistency rules

最终图、caption 和正文必须统一：

| 概念 | 唯一推荐写法 |
|---|---|
| 当前状态 | `history-only predictive state z_t` |
| 转移 | `shared weather-conditioned transition T` |
| 未来状态 | `evolved predictive state z_{t+h}` |
| 读出 | `state readout O` |
| 状态贡献 | `state contribution r_h` |
| 上下文预测 | `context-only forecast b_h` |
| 未来天气 | `future meteorological forcing` |
| Q2接口 | `state-path intervention` |
| Q3接口 | `weather intervention` |

不要在同一图中把 `state`、`latent state`、`world state` 和 `predictive representation` 交替使用。
