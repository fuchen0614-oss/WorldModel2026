# ObsWorld Closest-Method Novelty Check

日期：2026-07-15  
范围：EarthNet-first ObsWorld，DGH，cross-observation decoding，variable-step controlled transition  
结论：**CAUTION — 值得继续，但不能把各组件分别写成首创**

## 1. Core claims under audit

| ID | 候选主张 |
|---|---|
| A | 将异构/受产品条件影响的 EO 观测映射到 predictive state，再分别建模 state transition 与 observation formation |
| B | 用 S1/S2 及 exact-acquisition L1C/L2A cross-observation decoding 约束共享预测状态 |
| C | 用同一 variable-step transition 处理 5/10/20 日 DGH 驱动，并约束直接长区间与分段组合的状态/观测一致性 |
| D | 在 EarthNet land-surface forecasting 中，将产品轴与受控时间分割轴共同施加到同一 predictive state |

## 2. Search strategy

针对每项主张使用了至少三类表述检索 2023–2026 论文/官方代码：

- A：`Earth observation world model latent state observation operator`、`heterogeneous sensor unified latent dynamics`、`predictive state transition observation model EO`；
- B：`cross-sensor shared representation remote sensing`、`S1 S2 cross reconstruction`、`Sentinel-2 L1C L2A conditional generation/translation`；
- C：`variable-step latent dynamics composition consistency`、`semigroup consistency learned simulator`、`macro micro temporal partition flow regularization`；
- D：`weather-driven EO world model`、`EarthNet latent dynamics weather DEM`、`observation product + controlled temporal consistency EO`。

检索源以 arXiv 原文、CVF/OpenReview/PMLR/NeurIPS 论文页、AAAI 官方论文页与官方 GitHub 为主。

## 3. Claim-by-claim verdict

| 主张 | 当前新颖性 | 若联合证据成立 | 审稿判断 |
|---|---:|---:|---|
| A：Q/T/O 角色分工 | 2/10 | 2/10 | 标准 state-space/world-model 骨架，只是合理基础 |
| B：cross-observation/product decoding | 2/10 | 若真正提升 future utility，3.5/10 | 对齐、重建、any-to-any generation 都有强先例 |
| C：variable-step + partition consistency | 3–3.5/10 | 4/10 | macro/micro composition 高度相似工作已存在；增量在 non-autonomous control path + EO |
| D：两轴共同约束 EarthNet predictive state | 4.5–5/10 | 6–6.5/10 | 唯一有机会成为 AAAI 主贡献的组合，但必须有协同和 OOD 证据 |

当前整体新颖性约 **4.5/10**。只有当两条轴都在同一 Stage1.5→Stage2 管线中对 EarthNet 长期/OOD 预测产生不可替代的收益，整体才可上升到约 **6–6.5/10** 的可投区间。

## 4. Strongest overlaps

### 4.1 Earth-o1

[Earth-o1](https://arxiv.org/abs/2605.06337) 已明确研究 observation-native atmospheric world model：将异构原生观测统一到 grid-free dynamical field，推进大气状态，并做 cross-sensor inference。

实质重叠：异构观测→统一 latent/state→时序演化→跨传感器输出。因此 A 不能是组件新意。ObsWorld 剩余的区别是地表而非大气、EarthNet 尺度、明确 DGH control path 与两轴行为证据。

### 4.2 EO-WM

[EO-WM](https://arxiv.org/abs/2606.27277) 已占据“部分观测、天气驱动 EO world modeling”的高层叙事，并用 climatology/anomaly/stress 条件与 Extreme/Seasonal 诊断检验天气响应。

实质重叠：EarthNet 10→20 预测、天气/DEM/元数据条件、latent video generation、“EO world model”名称。ObsWorld 不能依靠稀疏/部分观测本身区分，必须依靠 explicit state transition 与两轴一致性。

### 4.3 CROMA, X-STARS, Mixed-Modality MAE

- [CROMA](https://proceedings.neurips.cc/paper_files/paper/2023/file/11822e84689e631615199db3b75cd0e4-Paper-Conference.pdf) 已做 radar-optical contrastive alignment 与 multimodal masked reconstruction；
- [X-STARS](https://arxiv.org/abs/2405.09922) 已做 cross-sensor dense alignment 与 sensor-agnostic representation；
- [Mixed-Modality MAE](https://openaccess.thecvf.com/content/WACV2025W/GeoCV/papers/Linial_Enhancing_Remote_Sensing_Representations_Through_Mixed-Modality_Masked_Autoencoding_WACVW_2025_paper.pdf) 已用 S2 encoder 预测 S1，并实现双向模态重建。

因此 S1/S2 alignment/cross-decoding 不是新意。它只有在提升后续 EarthNet predictive state 时才与本文主线相连。

### 4.4 COP-GEN-Beta and COP-GEN

[COP-GEN-Beta](https://openaccess.thecvf.com/content/CVPR2025W/MORSE/papers/Espinosa_COP-GEN-Beta_Unified_Generative_Modelling_of_COPernicus_Imagery_Thumbnails_CVPRW_2025_paper.pdf) 已在 S1/DEM/S2L1C/S2L2A 间进行条件生成，包括 L1C↔L2A；[2026 版 COP-GEN](https://arxiv.org/abs/2603.03239) 进一步做到 native-resolution any-to-any stochastic EO generation。

因此 L1C/L2A translation 不能作贡献。ObsWorld 的 product Gate 只能检验：一个为未来预测服务的共享 state 是否仍能通过给定 product token 生成正确产品，且这一约束是否改善 Stage2。

### 4.5 Intrinsic Differential Consistency and semigroup/flow-map work

[Recovering Physical Dynamics via Intrinsic Differential Consistency](https://arxiv.org/abs/2605.08454) 已学习 time-conditioned variable-step flow，并以 macro 与 arbitrary micro partitions 的 composition error 作训练正则和推理诊断。[Semigroup Consistency as a Diagnostic](https://arxiv.org/abs/2605.26324) 已显示 direct/composed gap 与 rollout degradation 相关，且提醒该正则并不总会改善预测。[Semigroup-regularized registration](https://arxiv.org/abs/2405.18684) 也已使用同类结构性质作训练约束。

因此不能写 first semigroup/partition consistency。ObsWorld 只能守：非自治 D/C 驱动路径必须严格按时间拼接，该约束施加到 EO 部分观测下的 predictive state，并与 product-axis constraint 共同服务 EarthNet 预测。

### 4.6 EarthNet/GreenEarthNet baselines

[EarthNet2021](https://arxiv.org/abs/2104.10066)、[Weather2Land](https://openaccess.thecvf.com/content/CVPR2022W/EarthVision/html/Diaconu_Understanding_the_Role_of_Weather_Data_for_Earth_Surface_Forecasting_CVPRW_2022_paper.html) 与 [GreenEarthNet/Contextformer](https://openaccess.thecvf.com/content/CVPR2024/papers/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.pdf) 已覆盖 future weather、DEM、calendar/time 与 Earth surface/vegetation forecasting。DGH 是必要接口，不是“首次加入三类字段”的新意。

## 5. Claims that must be removed

不得使用：

- first remote-sensing/EO world model；
- first weather-driven land-surface simulator；
- first Q/T/O observation–dynamics factorization；
- first latent-state EO forecasting；
- first sensor/product-invariant shared EO state；
- first cross-observation decoder 或 L1C/L2A translation；
- first variable-step、semigroup 或 partition-consistent dynamics；
- DGH 本身是算法创新；
- latent state 就是唯一真实物理地表状态；
- L1C/L2A cross decoding 证明成像条件完全可识别地解耦；
- EarthNet observational data 支持因果/反事实天气模拟；
- 对带时变控制的非自治系统直接写普通 semigroup。

对应的正确关系是 control-aware evolution/cocycle-style composition：

```text
T_(a:c)(s; D_(a:c), C_(a:c))
≈ T_(b:c)(T_(a:b)(s; D_(a:b), C_(a:b)); D_(b:c), C_(b:c))
```

## 6. Safe central contribution

> **The predictive state is jointly constrained across observation products by cross-observation decoding and across temporal partitions by control-aware composition consistency.**

中文：

> **ObsWorld 用跨观测产品解码约束预测状态的产品稳健性，并用外生驱动感知的时间分割一致性约束其可组合演化；两种约束共同服务于可验证的长期 EO 预测。**

审稿人安全的三句 positioning：

> 我们不把状态空间分解、多模态解码或时间组合律本身作为首创。我们关注天气驱动 EO 预测中的一个具体失败模式：模型即使能拟合像素，其预测状态也可能在同一场景被表示为不同观测产品，或在同一外生驱动轨迹被划分为不同时间步时失效。ObsWorld 通过跨产品解码和受控时间分割一致性共同约束这一状态，并检验这种一致性是否改善 EarthNet 的长期及域外预测。

## 7. Minimum publishable evidence

### 7.1 First establish the failure

不能只展示 full model 更好。应先表明强 Direct/shared-T5 模型可以有不错的 pixel error，却仍存在 product inconsistency 或 temporal partition inconsistency。

### 7.2 Core 2×2 factorial experiment

| product-axis constraint | temporal-axis constraint | 模型 |
|---|---|---|
| 无 | 无 | base predictive state + variable-step no-part |
| 有 | 无 | cross-observation state + variable-step no-part |
| 无 | 有 | base predictive state + partition loss |
| 有 | 有 | full ObsWorld |

四行必须使用相同 EarthNet Stage2、D/C/G 信息、参数量、训练预算和 evaluator。交互项应在预注册的 long-horizon/OOD 指标上检验。

如果 product-axis constraint 不改善 EarthNet Stage2 主任务或 OOD，它必须降为 mechanism experiment，不得与 temporal axis 并列为主贡献。

### 7.3 Product-axis evidence

- exact L1C/L2A self/cross decoding；
- correct/removed/wrong target-product token；
- source state 固定，target pixels 不得泄漏到 source；
- geographic held-out split；
- `self-only / +cross / full w/o condition / full`；
- Stage1.5 constraint 对相同 Stage2 的迁移收益；
- 如数据允许，附加 S1/S2 证据，避免结论只来自固定处理链。

### 7.4 Temporal-axis evidence

- matched Direct、shared T5、variable-step no-part、full；
- 10/20 日乃至更长 partition gap；
- 同一 `T` 和同一变长 `E_D`；
- true D vs zero/plausible-shuffle/lagged D；
- 5–100 日误差增长曲线；
- official OOD-t，并在附录报 OOD-s/st；
- 3 seeds **AND** tile/location-cluster paired bootstrap CI；
- constant-state/projector-collapse checks；
- composition gap 下降时真实 forecast 不恶化。

### 7.5 Most valuable additional empirical finding

检验 control-aware partition gap 能否跨 checkpoint、模型、horizon 和 region 预测长期 OOD error。普通 composition diagnostic 已有先例，但若在 weather-driven EO/DGH 中形成稳定、预注册的经验规律，会显著增强论文价值。

## 8. Final recommendation

- 若继续把 A/B/C 分别包装为首创：**FAIL 风险很高**。
- 若保留 ObsWorld、EarthNet、DGH 和“状态—动力学—观测”路线，但把各组件当基础，把“产品轴 × 受控时间轴联合约束”作唯一方法核心：**CAUTION，可继续 pilot**。
- 达到 AAAI 投稿级 GO 的前提是：2×2 协同证据、official OOD 竞争力、partition gain 无 forecast harm，以及 product-axis 对 EarthNet future utility 有实际迁移收益。

