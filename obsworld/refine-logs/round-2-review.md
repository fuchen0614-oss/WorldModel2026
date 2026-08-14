# Round 2 Review

<details>
<summary>Full raw reviewer response</summary>

# Round 2 复审

## 总判定

**Anchor preserved：是。** 修订稿保留了“稀疏 EO 下的长期预测状态及再观测校正”这一核心问题，没有漂移到大模型、概率生成或额外下游。

**Verdict：REVISE。** 相比上一轮有本质改善：dominant contribution 已收缩为 `F + U`，belief/observation 语义冲突被修复，实验也明显聚焦。但目前仍有三个 blocking issue：

1. 相对标准 RSSM/filtering 与 PredRNN 的机制增量尚未被隔离；
2. “复用并冻结 E/H”与当前真实代码/checkpoint 不一致；
3. correction protocol 仍可能因选择清晰观测样本而产生偏置。

## 1. Anchor 与 scope

Problem Anchor 的核心部分得到保留：

- history-dependent belief 与单帧 observation evidence 已分开；
- 同一 `F/U` 顺序用于 context 和 future；
- correction 由之后的预测收益验证，而非当前帧重建；
- acquisition factorization、FM、EO-WM 平行主张均被删除。

边界提醒：Anchor 中“acquisition 条件/观测形成”的范围，现在仅通过 cloud mask、clear fraction 和 observation age 实现。它没有解决跨传感器、产品或成像几何的完整 observation formation。只要论文不重新声称这一点，不构成 drift。

## 2. 最大的剩余新颖性风险

目前方法可以被审稿人概括为：

> 一个带天气输入、mask-aware learned update 的确定性 RSSM/Kalman-style filter。

这比上一版集中得多，但 `F`、prior/posterior、innovation、learned gain、mask-conditioned update 都不是单独的新机制。EO-specific novelty 能否成立，取决于是否证明：

> 普通 recurrent assimilation 或 generic learned posterior update 在局部云遮与稀疏观测下不够，而显式的 innovation + clear fraction + age 更新确实改善后续预测。

当前 Block B 只有 no update、hard replacement、restart 和 proposed U，缺少最关键的强对照。

必须在同一 Block B 中加入或替换为：

```text
VanillaFilter:
b_t+ = GRU/ResidualMLP(b_t-, [e_t, q_t, age_t])
```

它与 proposed U 使用完全相同的 `F/E/H`、训练 schedule 和参数预算。再加入：

```text
PredRNN-online:
在 reveal 时把 masked observation + mask 输入其 recurrent state，
随后继续自回归。
```

如果 proposed U 不能超过 VanillaFilter 和 PredRNN-online，论文只能说明“过滤式训练适用于 EO”，而不能说明提出的 innovation-aware update 有独立贡献。

为了控制规模，建议正文 correction controls 只保留：

- no update；
- VanillaFilter；
- proposed U；
- PredRNN-online。

hard replacement 和 restart 二选一放附录。

## 3. Blocking method issues

### B1. `H` 不能在当前条件下直接冻结

修订稿写“复用并冻结 E/H”，但当前项目的四波段 `EarthNetObservationDecoder` 是 Stage2 新 decoder，本地没有已训练 Stage2 checkpoint。冻结随机初始化的 `H` 会使 pilot 无法成立。

必须明确二选一：

- 从 repaired Stage1.5 state-bridge decoder 初始化，输出十二波段后选择 RGBN；
- 或让所有 Direct/VanillaFilter/ObsWorld 使用同一初始化，并在 GreenEarthNet 上共同训练 `H`。

第二种更简单。可以冻结 `E`，但 `H` 初期必须训练；pilot 稳定后是否冻结再由 Val 决定。

### B2. mask-aware `E` 不是现有 encoder 的直接复用

当前 EarthNet path 主要是像素乘 mask，encoder 并没有 proposal 中明确描述的 cloud-mask token/feature 接口。因此“冻结复用 E”与“E(o,m) 使用 mask token”存在实现缺口。

最小实现需要固定：

- 每个 patch 的 `q_t` 计算方式；
- patch 完全无效时是否直接跳过 `e_t`；
- 部分有效 patch 如何填充；
- mask token 是固定常量还是可学习参数；
- `age_t` 在部分 patch 更新后的递推、截断和归一化。

不要再依赖 `>5% clear` 的二值规则。推荐 clear-fraction 连续加权，并让 `q=0` 在单元测试中严格满足 identity。

### B3. correction evaluation 不能筛选“足够清晰”的样本后才报告

若 day-25/day-50 只选择有足够 clear support 的 cube，会产生容易样本选择偏差。

更严谨且更简单的协议是：

- 对所有 cube 固定 day 25 和 day 50；
- 使用当日真实 mask；
- `q=0` 时 U 自动 identity；
- 报告全体结果及按 clear fraction 分层结果；
- 同时报告各层样本量；
- 只评价 reveal 之后的 horizon。

这样不需要额外 eligibility 筛选，也更符合方法定义。

## 4. 其他必须澄清的问题

### Direct-Seq 的天气编码仍未具体化

`EncD(D_1:h)` 是必要接口，但尚未定义是 GRU、Transformer 还是 pooling。它影响参数量和公平性。

建议明确：

- 所有模型先共享逐五日 weather encoder；
- Direct-Seq 再使用一个轻量 temporal aggregator；
- rollout 逐步消费相同 weather embeddings；
- 不强求完全相同参数量，但必须匹配输入、supervision、训练样本，并报告参数/FLOPs。

### “训练长度外外推”应删除或落实

训练 curriculum 最终包含 length 20，因此在 GreenEarthNet 的 20 步内没有训练长度外外推。若不单独训练 max-length 12 的诊断模型，就删除该表述，只保留 free/anchored gap 和 horizon degradation。

### Weather control 与 Block C 的二选一存在逻辑冲突

Method Thesis 把 `F` 称为 weather-controlled，Success condition 又要求排除 calendar shortcut；但若 Stage1.5 gate 通过，Block C 就不做天气控制。

二选一：

- 删除论文级 weather-use claim，把天气仅称为 benchmark forcing；
- 或无论 Block C 选择什么，都在 Block A/附录固定保留一个极小的 `true weather vs wrong-year/no-weather` 检查。

不需要完整 EO-WM 风格天气实验。

### Stage1.5 仍可进一步降级

为了保持一篇论文一个 dominant contribution，建议 Stage1.5 永远只作为 initialization ablation，不再列 Claim 2。即使 gate 通过，也只说明初始化有帮助，不把它提升为并列贡献。

## 5. Validation focus

三块实验已经基本合理：

- Block A：官方 factual forecast；
- Block B：correction，是最核心证据；
- Block C：支持项。

建议最终进一步收缩为：

1. Block A 保留 Direct、Contextformer、PredRNN、final model；
2. Block B 保留 no update、VanillaFilter、PredRNN-online、proposed U；
3. Stage1.5 与天气控制均放紧凑消融/附录，不设第二个论文级 claim。

UniTS 若无法同官方 evaluator 运行，可在相关工作中讨论，不能混用其 PSNR/SSIM 表格数字。

## 6. Simplification Opportunities

1. 删除“Conditional Claim 2”，Stage1.5 只作 initialization ablation。
2. correction 正文删除 hard replacement/restart 中的一个，并加入更重要的 VanillaFilter。
3. 删除训练长度外 extrapolation；Direct 只承担 open-loop benchmark，不再强行设计复杂的 direct assimilation。

## 7. Modernization Opportunities

**NONE。**

当前不需要 LLM、VLM、diffusion、随机 RSSM 或 Foundation Model。继续强化最小 deterministic filtering interface 比增加现代模块更合理。

## 8. Remaining Action Items

按优先级：

1. **CRITICAL**：加入 VanillaFilter 和 PredRNN-online，定义 proposed U 的真正机制增量。
2. **CRITICAL**：决定 `H` 的初始化与训练方式，不能冻结随机 Stage2 decoder。
3. **CRITICAL**：固定 mask-aware evidence、`q`、`age` 的精确张量契约。
4. **CRITICAL**：固定全样本 day-25/day-50 correction protocol，禁止按清晰度筛样本后只报子集。
5. **IMPORTANT**：具体定义 Direct-Seq weather aggregator 和预算公平性。
6. **IMPORTANT**：让所有 correction baselines 使用相同 reveal schedule 训练。
7. **IMPORTANT**：修复官方 split manifests、NetCDF export、mask parity 和 evaluator 后再做 pilot。
8. **MINOR**：删除 train-length extrapolation 和 Stage1.5 并列 claim 的表述。

## 9. 评分

| 维度 | 分数 | 判断 |
|---|---:|---|
| Problem Fidelity | 8.5/10 | 核心问题保留，scope 明显收紧 |
| Method Specificity | 7.0/10 | 接口已具体，但 H、mask-aware E 和 Direct weather encoder 尚未闭合 |
| Contribution Quality | 6.5/10 | dominant contribution 清楚，但相对 vanilla filtering 的增量尚未证明 |
| Frontier Leverage | 7.5/10 | 正确拒绝无关大模型，predictive filtering 与问题匹配 |
| Feasibility | 6.0/10 | 六周可行，但核心代码、decoder 初始化和官方协议仍未实现 |
| Validation Focus | 7.5/10 | 已压至三块；仍可删除 conditional Claim 2 和弱 correction controls |
| Venue Readiness | 6.0/10 | 若强 filtering baselines 下仍成立，有 AAAI 潜力；当前尚未达到提交级 |

加权 Overall：

```text
0.15×8.5 + 0.25×7.0 + 0.25×6.5 + 0.15×7.5
+ 0.10×6.0 + 0.05×7.5 + 0.05×6.0
= 7.05 ≈ 7.1 / 10
```

**Verdict：REVISE**

**Drift Warning：NONE。** 但 acquisition/process-observation decomposition 已被主动收缩为 cloud/missingness-aware correction，后续不能重新扩大成跨传感器可识别状态主张。

</details>
