# TerraState Figure 1–2 图内文案锁定表

## 0. 使用规则

- 最终论文图内只排英文；中文列用于作者核义，不进入英文论文图。
- 以下是短文案，不得擅自改回旧版代码式表达。
- `Q1/Q2/Q3` 可出现在 Figure 1；Figure 2只标 Q2/Q3接口，Q1由最终预测输出自然承载。
- 禁止出现内部名称：`B0`、`B4`、`boundary80`、`MAIN`、`SAFE`、`V2`。
- 禁止加入 Q4/composition 或“state is physically interpretable”等未验证主张。

## 1. 术语总表

| 符号/概念 | 锁定英文 | 中文核义 | 不再使用 |
|---|---|---|---|
| \(q\) | **context encoder** | 上下文编码器 | backbone only（图内） |
| \(P\) | **state projector** | 状态投影器 | projection head |
| \(z_t\) | **predictive state** | 预测状态 | world state、physical state |
| \(T\) | **shared transition** / **weather-conditioned** | 共享转移/天气条件驱动 | shared T / driven by w / transition |
| \(O\) | **state readout** | 状态读出 | observation decoder、state head |
| \(b_h\) | **context-only forecast** | 仅上下文预测 | prior、baseline |
| \(r_h\) | **state contribution** | 状态贡献 | residual prediction（除正文明确解释外） |
| 输出闭合 | **forecast closure** | 预测闭合 | output fusion |
| Q2主检验 | **remove \(r_h\) (\(s=0\))** | 移除状态贡献 | state-path closure cut |
| Q2支持检验 | **\(T\!\rightarrow I\)** | 将转移替换为恒等映射 | identity ablation |
| Q3条件1 | **actual** | 真实天气 | factual |
| Q3条件2 | **matched donor** | 匹配供体天气 | shuffled、counterfactual weather |
| Q3条件3 | **normalized mean** | 归一化均值天气 | zero weather、mean control |
| 时间外分布 | **OOD-t** | 时间外分布 | Temporal shift（图内split名） |
| 未来真值 | **observed future** | 真实未来观测 | ground truth image（图内可简化） |

## 2. Figure 1 图内文案

### 2.1 面板 (a)

标题：

> **(a) World-model logic meets EO**

第一行：

> **Typical action-conditioned world model**  
> Observation  
> Internal state  
> Driven transition  
> Future  
> scene history  
> latent state  
> action  
> dynamics  
> future rollout

第二行：

> **EO world modeling under exogenous forcing**  
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

可选底句：

> **Endpoint accuracy alone does not test the internal state or forcing pathway.**

中文核义：

> （a）典型动作条件世界模型与外生驱动下的EO世界建模共享“观测—状态—驱动转移—未来”的逻辑；EO的观测更稀疏且受云遮挡，驱动由action变成外生未来天气。终点评分可以观察输出，却不能单独确认state use和forcing use。

### 2.2 面板 (b)

标题：

> **(b) TerraState exposes testable pathways**

主路径：

> Historical context  
> History-only predictive state \(z_t\)  
> Shared weather-conditioned \(T\)  
> Evolved predictive state \(z_{t+h}\)  
> State readout \(O\)  
> state contribution \(r_h\)  
> context-only forecast \(b_h\)  
> Forecast

天气条件：

> actual  
> matched donor  
> normalized mean

干预接口：

> **Q2 · State-path intervention**  
> remove state contribution  
> **Q3 · Weather intervention**  
> replace future weather

中文核义：

> （b）TerraState暴露一条进入预测的状态路径：历史状态由共享天气条件转移推进，再经状态读出形成\(r_h\)，与仅上下文预测\(b_h\)合并。Q2只移除\(r_h\)，仍保留\(b_h\)；Q3只替换进入共享转移的未来天气。

### 2.3 面板 (c)

标题：

> **(c) Operational evidence**

副标题：

> **for TerraState**

Q1：

> **Q1 · Predictive utility**  
> Useful OOD-t forecast  
> PREREQUISITE

层级关系：

> necessary, not sufficient

Q2：

> **Q2 · Load-bearing state**  
> Skill degrades without \(r_h\)  
> DEFINING EVIDENCE

层级关系：

> ground the declared driver

Q3：

> **Q3 · Weather-response fidelity**  
> Actual weather outperforms controls  
> FORCING GROUNDING

中文核义：

> （c）证据具有层级：Q1确认OOD-t预测效用；Q2检查移除状态贡献是否导致退化，是定义性核心证据；Q3检查真实天气是否优于匹配供体和归一化均值控制，使状态转移落到外部天气驱动上。

## 3. Figure 2 图内文案

### 3.1 顶部区域标签

> **INFERENCE**

> **MULTIMODAL HISTORY**

> **PREDICTIVE STATE**

> **WEATHER-DRIVEN TRANSITION**

> **FORECAST CLOSURE**

> **FUTURE OUTPUT**

中文核义：

> 推理；多模态历史；预测状态；天气驱动转移；预测闭合；未来输出。

### 3.2 输入区

> **Past EO**  
> cloud masks + time

> **past weather**

> **static geography \(g\)**

可选图像角标：

> RGB context  
> valid / cloud  
> elevation

### 3.3 状态编码区

> **\(q\): context encoder**

> **\(P\): state projector**

> **predictive state \(z_t\)**

> **context forecasts \(b_{1:H}\)**

### 3.4 共享转移区

主框：

> **shared transition \(T\)**  
> weather-conditioned

主框下方可选小字：

> same \(T\) for every horizon

输入：

> future weather \(u_{t:t+h}\)  
> static \(g\)  
> horizon \(h\)

Q3接口：

> **Q3: replace future weather**  
> actual / matched donor / normalized mean  
> all other inputs fixed

### 3.5 未来状态、读出与闭合

> **future state \(z_{t+h}\)**

> **\(O\): state readout**

> **state contribution \(r_h\)**

> **context-only forecast \(b_h\)**

> **forecast closure**  
> \(\widehat y_{t+h}=b_h+r_h\)

Q2接口：

> **Q2 primary: remove \(r_h\) (\(s=0\))**

> **Q2 support: \(T\!\rightarrow I\)**

### 3.6 输出区

> **Predicted NDVI**

> \(h=5,\ 10,\ 20\)

> **Observed future**

> EO reference · not an inference input

若只放 target NDVI，不放 RGB EO 参考，则最后一行删去，不得留下含混标签。

### 3.7 训练区

区域标题：

> **TRAINING ONLY**

摘要：

> **Training objectives: forecasting + distillation + future-state alignment**

三条监督：

> ground-truth future  
> forecasting loss

> frozen full-weather teacher  
> teacher prediction  
> distillation loss

> observed EO through \(t+20\) · future weather zeroed  
> frozen \(q/P\) target encoder  
> future-state target \(z^*_{t+20}\)  
> future-state alignment

底部约束：

> teacher and future EO targets are absent at inference

禁止改回：

> `L = LGT + 0.5 LKD + λs Lfuture-state`

具体损失公式只属于正文 Method。

## 4. Figure 1 英文 caption

**Figure 1: From EO world-model structure to testable state and forcing pathways.**
**(a)** Typical action-conditioned world models and EO world modeling under exogenous forcing share an observation–state–transition–future structure. In EO, sparse and cloud-obscured observations replace dense scene histories, while future weather replaces agent action as the external driver. Endpoint scoring directly evaluates the future output, but does not by itself test whether the internal state or forcing pathway is used. **(b)** TerraState exposes a history-only predictive state, a shared weather-conditioned transition, and a state readout whose contribution \(r_h\) is combined with a context-only forecast \(b_h\). Q2 removes \(r_h\) while retaining \(b_h\); Q3 replaces only the future weather entering the transition with matched-donor or normalized-mean controls. **(c)** The evidence is hierarchical: Q1 establishes forecasting utility as a prerequisite, Q2 tests whether the state is load-bearing, and Q3 grounds the transition in actual weather within the evaluated matched stratum. This is our operational test of TerraState, not a universal definition of world modeling.

## 5. Figure 1 中文解释

**图1：从EO世界模型结构到可检验的状态与驱动路径。**
（a）典型动作条件世界模型与外生驱动下的EO世界建模共享“观测—状态—转移—未来”结构。在EO中，稀疏且受云遮挡的遥感观测取代密集场景历史，未来天气取代agent action成为外部驱动。终点评分可以直接评价未来输出，却不能单独检验内部状态或天气路径是否被真正使用。（b）TerraState暴露仅由历史上下文形成的预测状态、共享天气条件转移，以及与仅上下文预测\(b_h\)合并的状态贡献\(r_h\)。Q2在保留\(b_h\)的同时移除\(r_h\)；Q3只替换进入转移的未来天气为匹配供体或归一化均值控制。（c）证据具有层级：Q1将预测效用作为前提，Q2检验状态是否真正承载预测，Q3在所评估的匹配样本层内把转移落到真实天气驱动上。这是本文对TerraState的操作性检验，不是世界模型的唯一普适定义。

## 6. Figure 2 英文 caption

**Figure 2: TerraState inference, forecast closure, and intervention interfaces.**
Cloud-masked EO history, past weather, and static geography are encoded by \(q\); the projector \(P\) exposes the spatial predictive state \(z_t\), while the same history-only pass produces context forecasts \(b_{1:H}\). A single weather-conditioned transition \(T\), shared across horizons, advances the state using future weather, geography, and the requested horizon. The state readout \(O\) produces \(r_h\), and the endpoint forecast closes as \(\widehat y_{t+h}=b_h+r_h\). Q2 removes the state contribution by setting \(s=0\) as the primary intervention and uses \(T\!\rightarrow I\) as supporting evidence. Q3 replaces only future weather with matched-donor or normalized-mean controls. The lower band shows training-only forecasting, teacher-distillation, and terminal future-state alignment; the frozen teacher and observed future EO target are absent at inference. Inference image tiles must be exported from the same frozen model query and are not schematic predictions.

## 7. Figure 2 中文解释

**图2：TerraState的推理过程、预测闭合与干预接口。**
带云掩膜的历史EO、历史天气和静态地理由 \(q\) 编码；投影器 \(P\) 暴露空间预测状态 \(z_t\)，同一次仅历史信息的前向过程同时产生上下文预测 \(b_{1:H}\)。跨预测时距共享的天气条件转移 \(T\) 使用未来天气、地理信息和所查询的时距推进状态。状态读出 \(O\) 生成 \(r_h\)，终点预测以 \(\widehat y_{t+h}=b_h+r_h\) 闭合。Q2以设置 \(s=0\) 移除状态贡献作为主干预，并以 \(T\!\rightarrow I\) 作为支持证据；Q3只把未来天气替换为匹配供体或归一化均值控制。底部展示仅训练期使用的预测监督、teacher蒸馏和终点未来状态对齐；冻结teacher与观测未来EO目标在推理时均不存在。所有推理图像块都必须由同一次冻结模型查询导出，而非示意预测。

## 8. Figure 1证据文案边界

Figure 1只表达三类结果含义，不放详细数字：

- Q1：保留temporal-shift/OOD-t预测能力；
- Q2：移除状态贡献后预测显著退化；
- Q3：actual weather优于matched-donor和normalized-mean控制。

不允许写：

- “all samples degrade”；
- “state explains the full prediction”；
- “weather causes physically correct dynamics”；
- “extreme events amplify the effect”；
- “TerraState is state of the art”；
- “composition/group property is verified”；
- “本文契约是世界模型的唯一标准”。

若以后决定加入数值，必须从冻结记录读取，并保持estimate与其对应CI属于同一统计量；
当前蓝图不建议在Figure 1中放数值。
