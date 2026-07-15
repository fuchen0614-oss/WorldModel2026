# Initial Revised Proposal：ObsWorld with Observation–Dynamics Role Separation

> **状态说明：Round 1 历史草案。**其中未定义的 `T_10`、S1/S2 renderer-pair 表述和实验过载问题已在 [`FINAL_PROPOSAL.md`](FINAL_PROPOSAL.md) 与 [`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) 中修正；请勿把本文件当最终方案。

日期：2026-07-15  
版本：Round 1 after reverse review

## 1. 推荐中心叙事

> **ObsWorld 是一个观测条件分解的地表过程遥感世界模型：它从多源、受传感器与成像条件 `phi` 影响的遥感观测中推断对未来足够的地表预测状态；在动态外生驱动 `D`、静态地理背景 `G` 与时间跨度 `h/delta_t` 的约束下推演该状态；再通过条件观测模型将未来状态生成成可由真实卫星数据核验的未来观测。**

英文候选：

> **ObsWorld models Earth-observation forecasting through role-separated predictive states: an acquisition-aware inference model estimates a predictive land-surface state from heterogeneous observations, a shared transition advances it under dynamic forcing, static geography and elapsed time, and an observation model maps the evolved state to verifiable satellite products.**

一句直觉：

> **不要直接推演混合了观测条件的像素；先估计“地表可能是什么”，再模拟“地表如何变化”，最后决定“卫星会如何看到它”。**

这保留了原始 ObsWorld 的三柱结构：

```text
多源观测 x_t + 已知观测条件 phi_t
        -> acquisition-aware state inference Q
        -> predictive land state s_t
        -> controlled transition T(s_t, D_path, G, h/delta_t)
        -> future state s_{t+h}
        -> observation model O(s_{t+h}, phi_{t+h})
        -> verifiable future observation x_hat_{t+h}
```

新观测校正 `U` 是同一状态接口的自然 Stage3/4 扩展，不再是首篇论文唯一新意。

## 2. 主张强度分层

### 2.1 系统愿景，可以保留

- 多源、有偏、带观测条件的遥感像素不是世界状态；
- 状态推断、状态演化和观测生成应有不同条件入口；
- DGH 驱动地表变化，`phi` 描述如何观察；
- 未来结果应回到像素/产品空间由真实观测核验；
- 新观测到达后，同一状态可以进一步校正。

### 2.2 当前论文可直接声称

- acquisition-aware predictive state，而非唯一真实状态；
- role-separated observation and dynamics interfaces；
- compositional, forcing-conditioned state transition；
- fixed-product Sentinel-2 observation forecasting；
- 在严格配对实验成立后，声称跨观测条件的一致性与 condition-aware rendering。

### 2.3 只有补齐证据后才能声称

- imaging-condition disentanglement；
- controllable future sensor/product rendering；
- 同一状态跨 S1/S2 或跨产品仍完整保持动态信息。

### 2.4 禁止声称

- identifiable physical state；
- complete Earth simulator；
- causal weather response；
- operational weather forecast；
- first EO world model。

## 3. 方法的统一贡献，而非三个字段的堆叠

不能写“我们提出 D、G、h”。Contextformer 已经使用天气和 elevation，EarthNet2021 从一开始就提供 future weather。真正的方法贡献应是：

> **Observation–dynamics role separation with a compositional controlled predictive-state transition.**

中文：

> **观测过程与地表动力学按功能角色分离，并在预测状态空间中用可组合的受控转移模拟未来。**

形式化为：

```text
s_t      = Q(x_<=t, phi_<=t, masks)
s_{k+1}  = T_delta(s_k, D_k, C_k, G, delta_t)
x_hat_k  = O(s_k, phi_k)
```

- `phi` 只进入状态推断 `Q` 与观测模型 `O`；
- weather path `D`、calendar `C`、static geography `G` 与 elapsed time 只控制 `T`；
- `h` 在 Direct 中是终点查询，在 rollout 中由 `delta_t` 和组合次数实现；
- future cloud truth 只用于 loss/evaluation mask，不进入 `Q/T/O`。

## 4. DGH 保留方式

### D：动态外生驱动

保留 D，而且把它从“累计到终点的 9 维摘要”改为“每个五日区间的驱动路径”。推荐正式接口：

```text
D_path: [B, 20, d_D]
```

为了与官方 Contextformer 公平，主模型读取全部 8 个 E-OBS 变量的五日统计；编码时按物理角色分组，而不是直接把 24 个数视为同质 token：

- water supply：rainfall；
- thermal state：mean/min/max temperature；
- atmospheric demand：humidity/VPD；
- energy：shortwave radiation；
- circulation/background：wind speed/sea-level pressure。

原 DGH 的四个核心物理量（降水、均温、VPD、短波辐射）作为 `D-core` 消融保留。这样既不丢失已有设计，也避免主表因输入信息少于官方强基线而不公平。

### G：静态地理背景

P1 主模型使用空间 DEM token；其角色是调制同一驱动下不同位置的响应，不把经纬度直接作为捷径。必须做：

- no-G；
- spatially shuffled G；
- OOD-s/OOD-st 检查。

landcover/geomorphon 只作为 P2 扩展，避免首篇字段膨胀。

### h：时间接口

- Direct：`h_days` 是合法的 endpoint query；
- Rollout：每次只输入 `delta_t=5 days` 与当前 calendar，总 `h` 由调用次数决定；
- 禁止把最终 `h=100` 注入每个五日 step。

因此 DGH 名称可以保留，但正文更准确地写成 `D/G/time interface`。

## 5. 数据集决策

主数据不应写成“放弃 EarthNet2021，改用另一个 GreenEarthNet”。推荐统一写法：

> **We evaluate on the EarthNet2021 benchmark family, using the revised GreenEarthNet/EarthNet2021x release as the primary protocol and the original EarthNet2021 tracks for secondary compatibility and extreme/seasonal diagnostics.**

原因：GreenEarthNet/EarthNet2021x 是 EarthNet2021 的重制/增强版本和代码名，不是它的子集；它保留兼容性，同时修复 cloud mask 和评估，增加时间 OOD、完整 E-OBS、地理坐标及静态层，更适合 DGH。

主任务：GreenEarthNet official Train/Val/OOD-t。  
次任务：OOD-s/OOD-st；原始 EarthNet2021 Extreme/Seasonal 仅在核心通过后做。

## 6. Stage 设计

### Stage 1：保留

现有 S1/S2 masked pretraining 作为通用 EO 初始化，不承担世界模型主张。

### Stage 1.5：保留并重新验收，不推倒重来

合理身份：

> acquisition-aware paired multi-modal state initialization

必须修复/补充的验收：

1. spatially disjoint train/val/test；
2. 真实 conditioned `phi` 路径；
3. Stage1 与 Stage1.5 使用相同、确定的 projector；
4. same-day 或更严格时间差的 S1/S2 paired consistency；
5. correct-phi vs shuffled-phi reconstruction/rendering；
6. predictive probe：状态能否预测未来 NDVI/变化；
7. 最终 Stage2 skill：Stage1 与 Stage1.5 初始化的 matched 对比。

旧 phi probe 结果只作问题记录，不进入论文证据。

若希望保留强 renderer 主张，还要在正文完成至少一个严格观测算子实验：

- 推荐 A：严格同日 S1/S2 的 cross-rendering；
- 推荐 B：同次 Sentinel-2 L1C/L2A 的四向交叉解码；
- 若 A/B 都无法构建，则将 GreenEarthNet decoder 明确降为 fixed-product S2 observation model。

### Stage 2-A：先跑现有 Direct-DGH，作为强基线和数据验证

```text
s_context + D_path + G + h -> s_{t+h} -> RGBN
```

它不是最终方法，但能最快验证 band、mask、weather、DEM、decoder 和 evaluator 是否工作，也是后续 rollout 的 matched Direct。

### Stage 2-B：最终 shared controlled transition

```text
s_{k+1} = s_k + T_delta(s_k, D_k, C_k, G, delta_t)
x_hat_{k+1} = O(s_{k+1}, phi_fixed-S2)
```

- context 使用 acquisition-aware encoder 获得 state sequence，再通过同一 transition/update 或轻量 temporal state initializer 形成 `s_t`；
- future 20 步使用共享 `T_delta`；
- 每一步都可监督 RGBN/NDVI；
- Direct 与 rollout 使用相同 encoder、decoder、D 信息和 20 个 target。

composition regularization 只作轻量项：

```text
T_10(s, D_1:2, G) ~= T_5(T_5(s,D_1,G),D_2,G)
```

只有真实 forecast error 不恶化时才保留。

### Stage 3：观测模型强化或新观测校正，二选一优先

优先补齐 `phi` 证据：strict paired cross-rendering / target-condition rendering。  
若 `phi` 已通过，再实现 `U`：新观测到达后的 state correction。`U` 是同一世界模型接口的增强，不是首篇论文必须依赖的唯一叙事。

### Stage 4：过程诊断与可选应用

- 原始 EarthNet2021 Extreme/Seasonal；
- correct/no/shuffled/wrong-year D；
- 可选 future-state utility（GPP、phenology 或 vegetation anomaly），不做无关 EuroSAT 分类；
- 可选 FM encoder initialization，不改变主机制。

## 7. 与最近工作的边界

### Contextformer

Contextformer 已有 S2、weather、elevation 与强官方精度。ObsWorld 的差异不能写成“也使用 D/G”，而应由以下证据成立：

- 明确 predictive state；
- `phi` 与 DGH 条件角色分路；
- shared interval transition 可组合；
- state 有跨观测与未来预测效用；
- 可选 state correction。

### EO-WM

EO-WM 的重点是概率视频生成、天气 climatology/anomaly/stress 与响应诊断。ObsWorld 不复制其“稀疏、部分可观测”措辞作为中心，也不竞争 weather decomposition；ObsWorld 的正交重点是：

- acquisition-aware multi-source state estimation；
- observation/dynamics role separation；
- compositional latent state transition；
- fixed or known-condition observation formation。

EO-WM 在 Related Work 中是重要近邻，但不应成为全文语言模板。

## 8. 失败时如何收缩而不推翻项目

- Stage1.5 无 Stage2 增益：保留 Stage1.5 为附录/负结果，主模型用 Stage1；
- phi renderer 不成立：保留 acquisition-aware inference，decoder 限定 fixed S2；
- rollout 落后 Direct：保留 Direct 作为强 forecaster，停止强 compositional world-model claim；
- D shuffled 与 true 等价：删除 driver-response 强调，只保留 calendar-conditioned forecast；
- G shuffled 不影响：删除 G 或仅称 terrain context；
- U 无收益：不影响 Stage2 主论文。

这些是证据驱动的降准，不是把已有 Stage1/1.5/DGH 工作全部推倒。
