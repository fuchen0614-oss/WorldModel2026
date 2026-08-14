# Figure 2 中文结构审阅说明

## 1. 这张图只回答什么

Figure 2 只回答：**TerraState 在一次预测中如何把历史上下文构造成显式预测状态，让未来天气通过同一个共享转移演化该状态，再把状态贡献读出并与 context-only forecast 闭合；Q2/Q3 在哪里实施干预。**

它不是训练流程图。因此本候选稿没有 teacher、future-state cache、KD、训练阶段编号或完整损失，也没有 Q4、composition、causal 或 counterfactual 图示。

## 2. 四列总线框

```text
┌──────────────────┐  ┌────────────────────┐  ┌─────────────────────────────┐  ┌──────────────────────┐
│ A Historical     │  │ B Predictive-State │  │ C Shared Weather-Conditioned│  │ D State Readout and  │
│ Context          │→ │ Construction       │→ │ Transition                  │→ │ Forecast Closure      │
│                  │  │                    │  │                             │  │                      │
│ historical EO    │  │ qθ ─→ e_t ─→ Pρ    │  │ actual / matched donor /    │  │ z_{t+h}              │
│ recorded mask    │  │          └→ z_t ───┼─→│ normalized mean ─→ E_u      │  │   ↓ Oω               │
│ past weather     │  │                    │  │                 ↓ d_h       │  │ spatial r_h           │
│ static geography │  │ qθ ─→ b_h ─────────┼──┼─────────────────────────────┼─→│   ↓ Q2 cut            │
└──────────────────┘  └────────────────────┘  │ geography + horizon → F     │  │ b_h + αr_h            │
                                               │              ↓ c_{h,i}      │  │   ↓                  │
                                               │ z_t → LN → Δψ → (+)         │  │ NDVI forecast         │
                                               │       └ residual skip ┘     │  └──────────────────────┘
                                               └─────────────────────────────┘
```

画布为 7.0 × 4.05 英寸。相对宽度约为 A 18%、B 23%、C 35%、D 23%；C 最宽，因为它同时容纳 Q3 三路天气、条件融合和残差转移。阅读顺序严格为 A→B→C→D。

## 3. A区：Historical Context

### 作用

把“模型真正看到的历史信息”集中放在最左侧，并清楚排除未来天气进入 `qθ`。

### 当前对象

- 顶部：同一冻结 minicube 的三帧历史 RGB。
- 中部：recorded mask、DEM hillshade、ESA WorldCover。
- 下部：从同一 minicube 的真实历史降雨和温度字段渲染的 past-weather strip。
- 右侧汇流线：四类输入合并后只进入 B 区的 history encoder。

### 必须保持

- future weather 不得放进 A 区。
- 不得画 future-weather 箭头进入 `qθ`。
- 静态地理在 A 区作为输入出现，在 C 区仅以 `E_g(g)_i` 的编码形式参与条件融合。

## 4. B区：Predictive-State Construction

### 作用

明确 `qθ` 有两个输出，而不是把所有信息压成一条不可区分的预测支路。

### 上支路

```text
qθ → spatial context tokens e_t → Pρ → history-only predictive state z_t
```

`z_t` 只由历史上下文得到。它沿主链进入 C 区的共享转移。

### 下支路

```text
qθ → context-only forecast b_h ─────────────────────→ D区加法节点
```

这条蓝色下方旁路独立保留。图中的蓝色格子只是“空间 forecast field”的方法示意，不是 observed future，也不是声称来自某个挑选样本的真实模型输出。

## 5. C区：Shared Weather-Conditioned Transition

### Q3入口

顶部紫色虚线框只切换未来天气输入：

- actual
- season-, geography-, and quality-matched donor
- normalized mean

三路素材全部进入同一个 `E_u`，没有为不同天气对照复制不同的 transition。

### 条件融合

```text
d_h + patch-wise geography E_g(g)_i + horizon E_h(h)
                         ↓
                 Condition fusion F
                         ↓
                       c_{h,i}
```

### 共享残差转移

```text
z_t → LN(z_t) → Δψ([LN(z_t); c_{h,i}]) → (+) → z_{t+h}
  └──────────────── residual skip ───────────────┘
```

图中明确写出：

`z_{t+h}=z_t+Δψ([LN(z_t);c_{h,i}])`

以及：

`one direct query per horizon`

因此不会被读成 recursive rollout。灰色小标签 `Q2: T→I` 只表示 supporting intervention，视觉强度明显低于 D 区橙色主干预。

## 6. D区：State Readout and Forecast Closure

### 作用

把“latent state”与“空间预测贡献”区分开，并明确最终预测如何闭合。

```text
z_{t+h} → State readout Oω → spatial raster contribution r_h
                                          ↓
b_h ───────────────────────────────────→ (+) → NDVI forecast ŷ_{t+h}
```

正常路径使用 `b_h + αr_h`，其中主路径为 `α=1`。Q2 primary 的橙色切点放在 `r_h` 进入加法节点之前：

`remove r_h (α=0)`

所以图不会误导为删除 decoder、删除 `z_t` 或修改 `b_h`。

## 7. 真实项目素材与方法示意

### 使用真实项目素材的槽位

- A：历史 RGB、recorded mask、DEM hillshade、land cover。
- A：历史天气曲线来自冻结 minicube 的真实 `eobs_rr/eobs_tn/eobs_tg/eobs_tx` 数值，但曲线图本身为本地渲染。
- C：actual、matched-donor、normalized-mean 三条 full24 future-weather strip，来自冻结 Q3 选定 pair。

### 只作为方法示意的槽位

- B：`e_t` token grid、`z_t` grid、`b_h` forecast field。
- C：`c_{h,i}`、`Δψ`、residual add、`z_{t+h}` grid。
- D：`r_h` raster contribution 和最终 NDVI forecast field。

这些示意图块不带卫星地貌，也没有标为 sample/output，避免伪造定性结果。

## 8. 仍需作者手工决定

1. **输出名称**：当前使用 `NDVI forecast ŷ_{t+h}`，因为正文主评测目标和 tensor channel 是 NDVI。若正文希望 Figure 2 保持任务级泛化，可统一改为 `Land-surface forecast ŷ_{t+h}`；只能二选一，并同步 caption。
2. **历史天气细节量**：当前保留四条真实历史曲线以增强 EO 视觉。若版面最终过高，可以用素材包内的简化天气 icon 替换，但不能改成 future-weather 图。
3. **是否在图中保留完整 donor 定义**：当前已按冻结术语完整写出。若 caption 首次完整定义，也可把图内缩成 `matched-donor`，但图和 caption 至少一处必须出现 quality-matched。

