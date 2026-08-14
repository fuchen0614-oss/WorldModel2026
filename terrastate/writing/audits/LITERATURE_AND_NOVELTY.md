# TerraState 前沿文献与新颖性边界

> 核验日期：2026-07-23。  
> 目的：服务正文定位，不进入投稿 PDF。近期预印本按原始 arXiv 版本核验；正式发表工作优先使用 proceedings/publisher 版本。

## 1. 最重要的定位结论

TerraState 不应把新意放在“天气驱动”“latent state”“world model”或“composition”任一单点上，因为这些点分别已有直接先例。当前唯一可守的差异是：

> 在高分辨率、云遮挡、天气驱动的地表预测中，用同一个空间预测状态、同一个共享转移和同一个最终 checkpoint，联合检验 forecast-bearing、driver-sensitive、non-degenerate、endpoint-guarded path consistency，并把这些状态证据与普通预测精度分开报告。

这是一项“联合可证伪合同”的贡献，而不是“首次提出某类架构”的贡献。

## 2. 最近邻比较

| 工作 | 它已经做了什么 | 对 TerraState 的威胁 | TerraState 必须保住的差异 |
|---|---|---|---|
| Contextformer / GreenEarthNet, CVPR 2024 | 20 m vegetation forecasting；PVT spatial backbone；weather-guided temporal transformer；cloud mask；temporal/spatial OOD | 任务、强骨干与评测高度接近 | state-carried contribution 必须经 Q2 证明可测；不能只是 Contextformer 加 auxiliary loss |
| VegeDiff, IEEE TGRS 2025 | latent diffusion；天气和静态环境条件；概率植被预测；变量敏感性探索 | 已有 latent-space vegetation forecasting 与 meteorological conditioning | 不争 latent/diffusion 首创；强调 state cut、shared transition、direct/composed endpoint guard 与 anti-collapse |
| ViT-Koop, ICCV Workshops 2025 | 将 EO 序列压缩为 latent state，用线性 Koopman operator 推进 | 已有 EO latent state 与迭代 dynamics | TerraState 的天气驱动共享转移及联合失败测试必须比“有 latent operator”更具体 |
| EO-WM, arXiv 2026 | 把 EO 预测写成 partially observed weather-driven world model；分解 climatology/anomaly/stress；Extreme Summer 与 Seasonal Matched-Pair | “weather-driven EO world model”和 forcing-response 已被占用 | 不主张 first EO world model；内部 state load-bearing + path consistency 是主要差异 |
| VegSim, arXiv 2026 | 从稀疏 NDVI 与天气推断 latent vegetation state；未来天气驱动 recurrent rollout；预测 NDVI quantiles；scenario perturbation | 最危险的架构先例 | TerraState 必须是高分辨率 spatial state，并用 matched cuts、endpoint guards 和 non-collapse 形成可证伪合同 |
| LeWM observability forecasting, arXiv 2026 | 云感知 EO latent world model；目标是下一次可用观测/恢复时间；带异常诊断 | cloud-aware latent-world-model framing 邻近 | 明确任务目标不同；不把 observability 当作本文贡献 |
| LatentTSF, ICML 2026 | 说明低误差预测器的 latent representation 仍可时间无序；转向 latent state forecasting | “accuracy does not imply good state”已有一般证据 | 把这一问题落实到 weather-driven spatial EO，并给出可切断、可组合、带端点门的实证合同 |
| Deep-OSG, JCP 2023 | variable-time autonomous operators；semigroup-aware training 和一致性 | composition/variable-time operator 不是新概念 | 天气段是有序、不可逆外部 forcing；只主张 observed-path partition consistency，不主张 semigroup theorem |
| World Models as Group Actions, arXiv 2026 | identity、inverse、composition；group-action consistency | “用 composition 检验 world model”已有明确先例 | 天气不是 agent action 或 group element；没有 inverse；采用更弱、任务适配的 path-partition test |
| PLSM, NeurIPS 2024 | 用正则使 action 对 latent state 的影响更系统、较少依赖起始状态 | structured latent transition 已有系统性动机 | 外部天气、空间状态、forecast-bearing cuts 和 endpoint accuracy 联合验证 |

## 3. 近期工作时间关系

AAAI-27 规定：在 2026-07-28 截止日前不足两个月公开的论文视为 contemporaneous，作者没有义务处理，但广为人知的预印本仍可能影响审稿人判断。EO-WM、VegSim 和 LeWM 均落在这一窗口附近或之内。正文主动讨论它们是降低新颖性争议的选择，不表示 TerraState 的初始想法依赖这些工作。

## 4. 可以写与不能写

### 安全表述

- “We operationalize a predictive-state claim through a matched set of failure tests.”
- “We do not claim that weather conditioning or latent dynamics are new.”
- “Our contribution is a joint state contract evaluated on the same accurate checkpoint.”
- “Path agreement is credited only when direct and composed forecasts are individually accurate.”
- “TerraState's residual closure is claimed to carry a measurable forecast increment.”

### 高风险表述

- “the first weather-driven EO world model”；
- “the first latent state model for vegetation”；
- “the first to evaluate weather sensitivity beyond pixel metrics”；
- “the first compositional/semigroup world model”；
- “causal”或“counterfactual correctness”；
- “physical/sufficient/complete state”；
- “the entire forecast is carried by the state”；
- 没有同协议结果时“SOTA”。

## 5. 当前唯一 TerraState 的新颖性风险

- 优点：context-only prior 不读取未来天气，天气到最终输出的唯一路径经过共享 T；同一模型可直接实施 closure cut、T→I、driver controls 与 direct/composed tests。
- 风险：残差闭环容易被审稿人描述为“Contextformer + auxiliary state branch”。
- 必需防线：Q1 保住公共预测能力；Q2 证明 full 相对 context-only prior 的可测量增量；Q3 证明只改变 T weather 时状态与输出响应；Q4 通过真实端点、broken-path control 与 anti-collapse；全部证据来自同一 checkpoint。

## 6. 文献版本修正记录

- VegeDiff 已从 2024 arXiv 条目更新为 IEEE TGRS 2025 正式版本：5 位作者，volume 63，pages 1–14，DOI `10.1109/TGRS.2025.3564317`。
- Deep-OSG 已从 arXiv 条目更新为 Journal of Computational Physics 2023 正式版本：volume 493，article 112498，DOI `10.1016/j.jcp.2023.112498`。
- LatentTSF 补充了 ICML 2026 的 PMLR volume 306；当前正式页码尚未在本地来源中确认，因此未虚构。
- Contextformer 作者 Lázaro Alonso 的重音已按论文首页修正。

## 7. 主要一手来源

- Contextformer / GreenEarthNet: https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-Modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html
- VegeDiff: https://doi.org/10.1109/TGRS.2025.3564317
- ViT-Koop: https://openaccess.thecvf.com/content/ICCV2025W/SEA/html/Shinohara_ViT-Koop_Vision-Transformer-Koopman_Operators_for_Efficient_Time-Series_Forecasting_of_Earth-Observation_Data_ICCVW_2025_paper.html
- EO-WM: https://arxiv.org/abs/2606.27277
- VegSim: https://arxiv.org/abs/2606.21961
- LeWM observability forecasting: https://arxiv.org/abs/2607.13651
- LatentTSF: https://arxiv.org/abs/2602.00297
- Deep-OSG: https://doi.org/10.1016/j.jcp.2023.112498
- World Models as Group Actions: https://arxiv.org/abs/2605.24578
- PLSM: https://proceedings.neurips.cc/paper_files/paper/2024/hash/43ba0466af2b1ac76aa85d8fbec714e3-Abstract-Conference.html
