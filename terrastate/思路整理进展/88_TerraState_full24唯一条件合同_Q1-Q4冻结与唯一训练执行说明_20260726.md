# 88 · TerraState full24 唯一条件合同、Q1–Q4 冻结与唯一训练执行说明

> 日期：2026-07-26（UTC）  
> 状态：**当前方案 B 最终方法接口与唯一训练口径冻结**  
> 修改范围：本文为新增记录，不修改 84、87、代码、数据或论文正文。  
> 文档层级：84 号继续定义论文科学问题、标题和单模型方法型定位；87 号继续定义当前证据状态、极端热旱协议与结果决策树；本文专门消除 `full24`、旧 `DGH/physical4`、anomaly/stress 和 Q1–Q4 之间的接口歧义。  
> 核心纪律：**最终模型只使用一种天气输入协议；训练统计、模型输入和评测分组必须分开；最终精度与机制证据只来自同一个冻结 checkpoint。**

---

## 0. 一页结论

### 0.1 唯一模型输入口径

最终 TerraState 使用：

```text
历史 EO 观测
  + full24 未来天气路径
  + 当前 B4 已有 static geography
  + forecast horizon h
```

不向最终模型额外输入：

- 旧 `physical4_v1`；
- 显式 anomaly；
- 显式 cumulative stress；
- hot-dry 标签；
- donor 身份；
- 评测分组信息。

最终 checkpoint 必须明确记录：

```text
driver_protocol = full24
```

### 0.2 唯一训练目标

唯一新增完整训练只使用：

\[
L
=
L_{\mathrm{GT}}
+\lambda_{\mathrm{KD}}L_{\mathrm{KD}}
+\lambda_{\mathrm{state}}L_{\mathrm{future\text{-}state}}.
\]

其中：

- `GT` 保证真实预测目标；
- 单一 `KD` 保护强 B4 精度；
- `future-state` 让共享转移学习真实未来观测状态；
- 不使用重复 `distill + residual`；
- donor、composition、intervention、extreme weighting 和 Q3/Q4 专用损失全部退出训练。

### 0.3 Q1–Q4 地位

| 问题 | 内容 | 地位 |
|---|---|---|
| Q1 | 标准预测精度是否足够 | 核心硬门 |
| Q2 | 状态及共享转移是否真实承载预测 | 最核心硬门 |
| Q3 | 模型是否正确利用未来天气，且极端热旱下作用是否增强 | 天气主张核心证据 |
| Q4 | 状态转移是否支持时间组合 | 扩展／附录 |

最低方法闭环是：**同一个 checkpoint 的 Q1 合格 + Q2 PASS**。  
Q3 PASS 才能把强 weather-response 结果写入摘要；Q4 允许失败并作为限制报告。

---

## 1. 三层合同：不能再混写

### 1.1 A 层：模型输入／conditioning

这是训练和推理时真正喂给模型的张量：

| 输入 | 最终口径 |
|---|---|
| 历史观测 | cloud-masked EO history |
| 动态驱动 \(D\) | full24 future weather path |
| 静态地理 \(G\) | 当前 B4 已有 static geographic/topographic channels |
| 时间查询 \(H\) | forecast horizon \(h\) |

full24 由 8 个 E-OBS 变量：

```text
fg, hu, pp, qq, rr, tg, tn, tx
```

各自的：

```text
mean, min, max
```

组成 \(8\times 3=24\) 维天气路径。

### 1.2 B 层：仅由训练集拟合的预处理统计

这些数值不作为额外模型字段，只负责规范输入或冻结评测定义：

- full24 每个原始天气变量的 train-only mean/std；
- static geography 的 train-only normalization；
- 缺失值和有效天数规则；
- 字段顺序与统计文件 SHA；
- 若 Q3 需要季节气候态、hot/dry threshold，这些也只能由 train split 估计。

严格禁止：

- 用 val、OOD-t、extreme 结果反推统计；
- 根据模型表现修改 hot-dry threshold；
- 使用 identity/smoke stats 进行正式训练。

### 1.3 C 层：仅用于评测的协议

这些内容不进入模型、不参与反向传播、不改变 checkpoint：

- hot-dry manifest；
- matched-normal manifest；
- season/region-matched donor mapping；
- train/val/OOD manifest；
- Q1–Q4 evaluator；
- 每份 manifest、threshold、donor mapping 的 SHA 和样本数。

其中：

- train-only climatology/threshold 的**数值来源**属于 B 层；
- 由这些数值生成的 cube 清单与 donor 配对属于 C 层。

---

## 2. 旧 DGH/physical4 与最终 full24 的关系

### 2.1 必须区分“抽象角色”和“具体旧协议”

抽象上，TerraState 仍然使用：

\[
D=\text{driver},\qquad
G=\text{geography},\qquad
H=\text{horizon}.
\]

但最终方案 B 的具体实现是：

\[
D=D_{\mathrm{full24}},
\qquad
G=G_{\mathrm{B4\ static}},
\qquad
H=h.
\]

### 2.2 旧 physical4 的地位

旧 `physical4_v1` 是另一套具体天气协议：

- precipitation；
- temperature；
- VPD；
- radiation；
- calendar；
- DEM；
- horizon。

它保持历史代码和文档不变，但：

- 不进入最终 TerraState-V2；
- 不出现在最终主方法流程图；
- 不与 full24 同时作为模型输入；
- 如必须保留，只能作为历史方案／附录候选；
- 因输入协议不同，不能把 physical4 与 full24 的差异直接解释成某个状态机制的公平消融。

### 2.3 正文唯一推荐表述

中文：

> TerraState 以与 ContextFormer 骨干一致的 24 维未来气象序列、静态地理条件和预测时距来条件化共享预测状态转移；所有归一化统计仅由训练集估计。模型不接收显式的天气异常或热旱胁迫指标，这些量仅用于定义预注册的评测分组。

英文：

> TerraState conditions its shared predictive-state transition on the same 24-dimensional future meteorological sequence used by the ContextFormer backbone, together with static geographic context and forecast horizon. All normalization statistics are estimated exclusively from the training split. No anomaly or stress indicator is provided to the model; such quantities are used only to define pre-registered evaluation strata.

方法图只画一条天气输入：

```text
full24 future weather
        ↓
weather encoder
        ↓
shared predictive-state transition T
```

---

## 3. 最终方法合同

\[
z_t=q(o_{\le t}),
\]

\[
z_{t+h}=T(z_t,u^{\mathrm{full24}}_{t:t+h},g,h),
\]

\[
\hat y_{t+h}=b_h+O(z_{t+h}).
\]

约束：

1. \(b_h\) 是 context-only prior，不得读取未来天气；
2. 未来天气只能通过 \(T\) 影响状态支路；
3. \(T\) 产生的状态必须进入同一个解码器 \(O\)；
4. `alpha=1` 且不可学习；
5. teacher 与 future target 只在训练时存在；
6. 正式推理只有 `history → q → T(full24,g,h) → O`；
7. 当前只称 `shared predictive-state transition`；
8. Q4 未通过前，不称已验证的 fixed-step compositional/open-loop dynamics。

### 3.1 Future-state supervision

训练时使用冻结的 future-observation target：

\[
z^*_{t+20}
=
\operatorname{sg}
\left(
P_{\mathrm{frozen}}
\left(
q_{\mathrm{frozen}}(o_{\le t+20})
\right)
\right),
\]

\[
L_{\mathrm{future\text{-}state}}
=
1-\cos
\left(
\operatorname{LN}(z_{t+20}),
\operatorname{LN}(z^*_{t+20})
\right).
\]

target 协议：

- 复制训练开始时的 q/projector；
- 永久 `eval/no_grad`；
- target 输入包含真实未来 EO；
- target future weather 置零，避免直接复制天气；
- 只取 \(h=20\) terminal target；
- 缓存 FP16 target、mask、filepath 和 SHA；
- target 不进入正式推理。

future-state loss 是训练方法，不是 Q2 的替代证据。最终仍必须通过端点干预证明状态承重。

---

## 4. 唯一训练配置

### 4.1 初始化

- student：**冻结为当前 exclusive MAIN-last**，即产生 `val R²=0.49027、RMSE=0.16038、Full-alpha0 ΔR²=+0.00416、Full-T-id ΔR²=+0.00869` 的同一个 checkpoint；它由强 Phase-I B4 初始化并已经过 exclusive state-route takeover，不是 raw B4，也不是从头训练；
- KD teacher：原始强 Phase-I B4 `checkpoint_best.pt`（已知文件 SHA 前缀 `2c5d08423671`）；训练代码只抽取其中的 `q.*` 构造冻结的 full-weather `PVTContextformerQ`，因此论文中应称 **frozen full-weather forecasting teacher**，不能误写成完整 B4 residual 输出；
- future-target q/projector：从上述 exact student checkpoint 在 V2 训练开始时复制其 `q + projector` 并永久冻结；它读取真实未来 EO、将 future weather 置零，只生成训练期 \(h=20\) target cache，不进入推理；
- 天气输入：原 B4 full24；
- 不重新引入 physical4 或 Stage1/Stage1.5 状态。

冻结权重链：

```text
原始强 Phase-I B4 checkpoint_best
  ├─ q.* → frozen full-weather KD teacher
  └─ 曾初始化 exclusive state-route takeover
                    ↓
          exclusive MAIN-last
                    ↓
             TerraState-V2 student
                    ↓
       复制初始 q + projector 并冻结
                    ↓
        future-state target cache encoder
```

正式执行前必须从 exclusive MAIN-last 的评测 JSON 解析并记录 exact checkpoint path，同时冻结：

- student 文件 SHA256 与 `b4_state_dict` SHA256；
- teacher 文件 SHA256、`q.*`/teacher state SHA256；
- student 初始 `q + projector` SHA256；
- train/val future-state cache SHA 与 live data manifest SHA。

runbook 或 CLI 中虽然可能仍兼容 raw Phase-I B4，但**正式唯一训练不得在 raw B4 与 exclusive MAIN-last 之间临时任选**。

### 4.2 损失

\[
L
=
1.0L_{\mathrm{GT}}
+0.5L_{\mathrm{KD}}
+\lambda_sL_{\mathrm{future\text{-}state}}.
\]

\[
\lambda_s=
\begin{cases}
0\rightarrow0.02, & 0\%-20\%,\\
0.02, & 20\%-80\%,\\
0.01, & 80\%-100\%.
\end{cases}
\]

### 4.3 三阶段单 run

#### 0%–20%

- q 冻结；
- 训练 projector、weather encoder、\(T\)、\(O\)；
- state loss 从 0 线性升到 0.02；
- 不加入 donor、composition 或 extreme sampling。

#### 20%–80%

- q 继续冻结；
- GT、单 KD、future-state 三项固定；
- 保存固定间隔 checkpoint；
- 强制保存 80% 解冻边界 checkpoint。

#### 80%–100%

- 只解冻 q 最后一个 Transformer block；
- q LR 为 \(T/O\) LR 的 0.02–0.05 倍；
- state loss 降为 0.01；
- GT/KD 不变；
- 其余 q 层继续冻结。

### 4.4 优化器口径

- global batch 64；
- FP32；
- AdamW；
- branch LR 建议 \(3\times10^{-5}\)；
- q LR 约 \(1\sim1.5\times10^{-6}\)；
- 保持现有 weight decay 口径；
- warm-up 200–500 steps；
- cosine decay；
- grad clip 1.0；
- 40 epochs；
- 8 卡 DDP 只能在保持 global batch、有效 updates 和 LR 口径不变时使用；
- checkpoint 必须包含 optimizer、scheduler、step 与 RNG，以支持严格断点恢复。

---

## 5. Q1–Q4 冻结定义

### 5.1 Q1 · Forecast sufficiency

问题：

> 同一个最终 checkpoint 是否保持足够的标准预测能力？

val qualifier：

- \(R^2\ge0.502\)；
- RMSE \(\le0.156\)。

最终 OOD-t 目标：

- \(R^2\) 尽量保持约 0.58；
- RMSE \(\le0.150\)。

Q1 是 Table 1 和正文核心，不得用 Q2–Q4 替代。

### 5.2 Q2 · Load-bearing predictive state

问题：

> 切断 state-to-output 或破坏共享转移后，真实端点预测是否显著变差？

核心 arms：

- Full；
- alpha0/state-output cut；
- T-identity。

理想通过条件：

- Full-alpha0 aggregate \(\Delta R^2\ge0.005\)；
- Full-T-id aggregate \(\Delta R^2\ge0.005\)；
- paired/cluster bootstrap CI 下界 \(>0\)；
- prior 不变、权重恢复、checkpoint 不变等 invariants 全通过。

证据地位：

- alpha0 是主证据；
- T-identity 因可能产生 OOD state，只作转移依赖辅证；
- latent cosine、future-state loss、state movement 不能替代端点 Q2。

### 5.3 Q3 · Weather-conditioned response fidelity

问题：

> actual weather 是否比 normalized-mean 或 season/region-matched donor 产生更正确的真实端点预测？

核心 arms：

- actual weather；
- normalized-mean weather；
- matched donor weather。

hot-dry 增强检验：

\[
\Delta_{\mathrm{interaction}}
=
E_{\mathrm{hotdry}}
-E_{\mathrm{matched\text{-}normal}}.
\]

若要写“极端热旱下状态/天气作用增强”，必须：

- 直接检验 interaction；
- cluster bootstrap CI 下界 \(>0\)；
- actual weather 具有端点正确性优势；
- 不能只报告输出发生变化。

Q3 PASS 才能把强 weather-response 结果写入摘要。只有 output delta 时只能写 sensitivity/PARTIAL。

### 5.4 Q4 · Temporal composition / non-collapse

问题：

> direct 与 composed 路径是否在非坍塌条件下得到相容状态和端点预测？

Q4：

- 保留冻结 direct/composed partitions；
- 必须有 endpoint guard；
- 必须有 state variance、effective rank、movement 等 non-collapse guard；
- 不能用近恒等或常量状态制造“一致性”；
- 不能替代 Q2。

当前唯一训练不为 Q4 添加 loss，因此：

- Q4 降为扩展／附录；
- 失败时诚实报告限制；
- 不进入安全标题；
- 未通过前不声称 compositional rollout 已成立。

---

## 6. 唯一训练前／中／后任务链

### 6.1 训练前

1. 冻结 A 层模型输入：
   - full24 字段名和顺序；
   - static geography；
   - horizon；
   - 缺失值规则。
2. 冻结 B 层统计：
   - train-only full24 stats；
   - static normalization；
   - stats/manifest SHA；
   - 确认 val/OOD 不参与拟合。
3. 冻结 future-target cache：
   - q/projector SHA；
   - future weather 置零；
   - \(h=20\)；
   - mask/patch 对齐；
   - target variance/effective-rank sanity。
4. 冻结 C 层评测：
   - val/OOD manifest；
   - hot-dry/matched-normal；
   - donor mapping；
   - Q1–Q4 evaluator；
   - checkpoint 选择规则。
5. 只做 smoke：
   - forward/backward；
   - 无 target inference leakage；
   - 单 KD、无重复 loss；
   - checkpoint 可精确恢复；
   - 无 NaN。

### 6.2 训练中

1. 只运行一个正式 full training；
2. 不查看 OOD/test；
3. 不改变 loss、字段、threshold、manifest；
4. 固定间隔保存 checkpoint；
5. 监控 GT/KD/state loss、state rank、NaN、吞吐和 target SHA；
6. 只有工程故障或 NaN 才允许停止修复；
7. 算法结果不理想不能中途换方法或加 loss。

### 6.3 训练后

1. 在冻结 val 上选 checkpoint：
   - 先满足 Q1；
   - 合格者中按非干预 future-state val loss 选择；
   - 不按 Q2 ablation margin 选模。
2. 只比较预注册候选：
   - 80% 解冻边界；
   - val-loss best；
   - last。
3. 冻结唯一 checkpoint SHA；
4. 依次运行：
   - val Q1；
   - global Q2；
   - Q3 hot-dry/matched-normal/donor；
   - Q4（最后且可选）；
   - 一次冻结 OOD-t；
5. OOD-t 后不得重新换 checkpoint；
6. Table 1、Q2–Q4 和摘要结果句全部使用这个 checkpoint。

---

## 7. 主线一致性审计

### 7.1 主线没有漂移

当前单一主线是：

```text
history
  → q 得到空间预测状态
  → full24 / geography / horizon 条件化共享 T
  → future predictive state
  → O 解码未来观测
```

训练时用真实未来观测的冻结 target state 强化这一状态；训练后：

- Q1 验证预测可用性；
- Q2 验证状态承重；
- Q3 验证天气条件响应正确性；
- Q4 验证更强的时间组合能力。

这仍然是：

> 遥感 + 方法型世界模型 + 内部可检验预测状态。

### 7.2 需要避免的三种漂移

1. 把 anomaly/stress 分组写成模型模块；
2. 用极端子集 Q2/Q3 替代失败的 global Q2；
3. 在 Q4 未通过前，把 horizon-conditioned shared \(T\) 写成已验证的固定一步 open-loop dynamics。

### 7.3 论文贡献顺序

1. 问题：固定时域精度不能证明内部表示是可复用预测状态；
2. 方法：future-state-supervised、full24-conditioned shared predictive-state transition；
3. 证据：同一 checkpoint 的 Q1–Q3，Q4 作为扩展；
4. 极端热旱：Q3 的压力场景，不是新模型、第三套输入或新 benchmark。

---

## 8. 结果出口与正文保证

### 档 A：Q1 + Q2 + Q3 通过

- 保留强方法型、weather-driven、load-bearing predictive-state 主张；
- hot-dry interaction 可进入摘要；
- Q4 按结果进入正文或附录。

### 档 B：Q1 + Q2 通过，Q3 partial

- 方法型 world-model 主张仍成立；
- 不写极端天气响应增强；
- Q3 作为 sensitivity/限制报告。

### 档 C：Q1 通过，Q2 仅 T-id/partial

- 只能称 transition-sensitive future-state-supervised forecaster；
- 不写一般性 load-bearing；
- 正文仍可完整，但标题/摘要结果句需收窄。

### 档 D：Q2 通过，Q1 不足

- 写 forecast–state trade-off；
- 不写 competitive forecast；
- 方法证据存在，但 AAAI 竞争力较弱。

### 档 E：Q1/Q2 均不足

- 不再追加模块或临时修改尺子；
- 报告 state-takeover 的有原则负面结果；
- 正文可无 TBD 完成，但必须更换强成功式标题/摘要。

---

## 9. 时间预算

| 工作 | 预计墙钟 |
|---|---:|
| train/val future-target cache | 0.5–2 小时 |
| cache 与 target sanity | 0.5–1 小时 |
| 唯一完整训练 | 9–11 小时 |
| 三个 checkpoint 的 Q1 筛选 | 1–2 小时 |
| 最终 Q2 + OOD-t | 2–4 小时 |
| Q3 hot-dry/donor 与可选 Q4 | 1–3 小时 |

整体建议按 14–18 小时规划；I/O 或 scorer 较慢时预留到 20–24 小时。

---

## 10. 最终执行句

> 最终 TerraState 只使用 full24、static geography 和 horizon 作为模型条件；训练集统计只负责规范化，hot-dry、stress 和 donor 只负责 Q3 评测。唯一训练通过 future-state supervision 争取 Q2，通过单一 KD 保护 Q1，Q4 保持为扩展。所有论文结果只能来自同一个冻结 checkpoint。
