# ObsWorld Claim-Driven Experiment Plan（EarthNet family + DGH）

> **状态说明：Round 1 历史草案。**当前实验设计以 [`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) 为准。

日期：2026-07-15  
状态：Round 1 draft；待独立复审

## Claim map

| Claim | 论文含义 | 最小充分证据 | 失败后的处理 |
|---|---|---|---|
| C1：按功能角色分离观测条件与动力学条件，可形成更有用的 predictive state | `phi` 进入 inference/observation，D/G/time 进入 transition，不直接推演混合像素 | 严格 paired observation experiment；correct/shuffled `phi`；Stage1 vs Stage1.5；future predictive utility | 删除强 disentanglement/renderer，改称 acquisition-aware initialization + fixed S2 decoder |
| C2：共享、可组合的 DGH controlled transition 能够模拟 EO-observable land evolution | D 是区间路径、G 是空间响应背景、time 是推进尺度；同一 `T_delta` 重复调用 | official full-20 forecast；matched Direct；composition gap；true/no/shuffled D/G；horizon curve | 若只剩 direct 精度，降为 conditional forecaster，不强称 compositional world model |
| C3：完整 ObsWorld 在 EarthNet family 的官方 OOD 上具有竞争力 | 世界模型不是只靠结构命名，还要能生成可核验未来观测 | GreenEarthNet OOD-t 主表，OOD-s/st 次表，三种子/配对置信区间 | 若明显落后强基线，停止 AAAI 主线或简化方法 |

## Block 0：协议与数据硬门槛

### 目的

确保后续所有结果确实来自官方 EarthNet family 协议，而不是 split、mask、weather 或 evaluator 错误。

### 必须完成

1. 明确列出 GreenEarthNet `train/iid/ood/extreme/seasonal` 文件清单；禁止找不到 split 时回退扫描根目录。
2. 使用官方 Val、`ood-t_chopped`、`ood-s_chopped`、`ood-st_chopped` manifest。
3. 输出带 time/lat/lon 的 NetCDF `ndvi_pred`，复现官方 evaluator。
4. 分开三种 mask：历史观测有效性、RGBN supervision、官方 NDVI evaluation。
5. 审计 8 个 E-OBS、三种 DEM、landcover、geomorphon、`sentinel:product_id` 的可用性和预测时可知性。
6. 任何 future cloud/dlmask/SCL 只能用于 loss/evaluation。
7. 用官方 persistence/climatology artifact 验证指标 parity。

### Gate

未通过 evaluator、manifest 和 mask parity，不进入长训练。

## Block 1：Stage1.5 / observation-state evidence

### RQ1

Stage1.5 是否真的为 Stage2 提供了更有用、对 acquisition 更稳健的状态，而不只是训练 loss 更低？

### 比较

1. Stage1 S2-only；
2. Stage1 dual-modal；
3. 当前 Stage1.5 60k；
4. 必要时只做轻量 repaired Stage1.5 fine-tune，不立即从零重训。

### 数据协议

- SSL4EO-S12 按 geographic location 严格拆 train/val/test；
- paired 实验优先同日；不足时预注册 `<=1 day`，并按时间差分层；
- 不把跨季节 pair 当 nuisance pair；
- 若做 L1C/L2A，则必须同一 Sentinel-2 acquisition/product。

### 正文最小指标

1. cross-modal retrieval / state agreement，在 held-out locations 上报告；
2. correct-phi reconstruction 相对 shuffled-phi；
3. cross-rendering（只有严格 pair 才报告）；
4. frozen state 的 future-NDVI/change probe；
5. 同一 Stage2-A 下的 Val forecast skill。

### 辅助诊断

- balanced linear/MLP phi probe，多种子；
- semantic probe；
- state effective rank/variance。

### 判据

- Stage1.5 必须至少在 paired observation evidence 与 Stage2 Val skill 中各有一项稳定收益；
- 若只有 retrieval 改善、forecast 不改善，则它是 representation result，不是主方法必要组件；
- 若 decoder 不区分 correct/shuffled `phi`，不得写 controllable rendering。

## Block 2：Direct-DGH 强基线

### RQ2

现有数据管线、DGH 字段和 observation decoder 是否能在官方任务上形成可信的强 direct baseline？

### 模型

```text
s_context = A(Q(x_1:10, phi_1:10))
s_hat_t+h = F_direct(s_context, D_1:h, C_1:h, G, h)
x_hat_t+h = O(s_hat_t+h, phi_fixed-S2)
```

### 关键修改规格（本轮仅规划）

- D 输入逐五日 path，不使用从 context end 到 endpoint 的重复累计摘要；
- 主公平版本使用官方完整 E-OBS 信息；`D-core` 为物理紧凑消融；
- 20 个 target 全监督；
- decoder 联合训练，不冻结随机权重；
- Stage1/Stage1.5 使用相同 Stage2 配置比较。

### 比较

- persistence、climatology；
- official Contextformer；
- PredRNN/SimVP/Earthformer 中能按同 evaluator 复跑的强模型；
- Direct-DGH。

### Gate

Direct-DGH 必须进入强基线合理区间；若连小样本过拟合、官方导出或 Contextformer parity 都失败，不实现最终 rollout。

## Block 3：Shared compositional DGH transition（主方法）

### RQ3

同一短步状态转移能否在 interval-specific forcing 下组合成长期模拟，并保持官方预测竞争力？

### 模型

```text
s_0 = state initializer(context observations)
for k = 1..20:
    s_k = s_{k-1} + T_delta(s_{k-1}, D_k, C_k, G, delta_t=5d)
    x_hat_k = O(s_k, phi_fixed-S2)
```

### matched control

Direct 与 rollout 必须共享：

- encoder/state projector/decoder initialization；
- D/C/G 原始信息；
- 20 target supervision；
- training cubes、steps、tuning budget；
- output/evaluator。

### 主要比较

1. matched Direct；
2. shared rollout；
3. rollout + composition consistency（若真实误差不恶化）；
4. rollout no-D；
5. rollout time-shuffled/wrong-year D；
6. rollout no-G；
7. rollout spatially shuffled G。

### 指标

- official NDVI：RMSE、R2、NSE、absolute bias、outperformance、RMSE25；
- horizon-wise NDVI RMSE；
- RGBN MAE/SAM/SSIM 作为 observation diagnostics；
- composition gap：直接十日推进与两次五日推进的 state/observation 差；
- Params、FLOPs、latency、peak memory。

### 决胜判据

预注册：shared rollout 相对 matched Direct 的 OOD-t NDVI RMSE 非劣界，具体 `delta_NI` 在 Val 分布和官方量纲审计后冻结，不能直接沿用未经校准的 0.01。

必须同时满足：

1. official forecast non-inferiority；
2. long-horizon curve 不出现不可接受崩溃；
3. true D 优于 time-shuffled/wrong-year D；
4. composition gap 的改善不以更差真实 forecast 为代价；
5. 若 G 无效则删除，不为保留缩写强行留下。

## Block 4：EarthNet family 主表与次轨

### 主表（正文 Table 1）

数据：GreenEarthNet Train/Val/locked OOD-t。  
行：Persistence、Climatology、Contextformer、强 recurrent baseline、matched Direct、ObsWorld。  
列：官方六项核心指标；三种子 mean/std 或配对 CI。

### 机制表（正文 Table 2）

压缩为最小行：

1. Direct；
2. rollout；
3. rollout + full role separation；
4. no/shuffled D；
5. no/shuffled G；
6. Stage1 vs Stage1.5（若通过 Gate）。

### 主图

- 一张 horizon degradation + composition gap 组合图；
- 一组 correct/shuffled `phi` 或跨观测渲染示例；若 phi Gate 失败，则换成 RGBN/NDVI rollout 与失败案例。

### 次轨/附录

- OOD-s/OOD-st；
- 原始 EarthNet2021 Extreme/Seasonal；
- landcover/season subgroup；
- full RGBN metrics；
- `U` correction 小实验；
- 详细效率与字段表。

## Downstream 与 foundation model

### 首篇不要求的内容

- EuroSAT 分类不能证明世界模拟；
- LLM/VLM 与核心状态转移无直接关系；
- 多个无关下游会挤压 7 页并削弱归因。

### 只有核心通过后才做的一个窄下游

优先选择 predicted-state utility：GPP、phenology 或 vegetation anomaly。比较：

- observed context state；
- direct future state；
- rollout future state；
- pixel forecast readout。

它只能作为“预测状态有应用价值”的支持，不是救主表的工具。

### 大模型 + ObsWorld

可作为兼容性消融：CROMA/AnySat/TerraMind 等 encoder initialization + 完全相同 ObsWorld transition。只有在轻量版本主张成立后再做，不做大规模 2x2。

## Run order and stop rules

| Milestone | 内容 | 进入下一阶段的门槛 |
|---|---|---|
| M0 | official split/evaluator/mask/weather audit | 全部 parity 通过 |
| M1 | Stage1.5 repaired evidence | 至少 paired evidence + predictive utility 不退化 |
| M2 | Direct-DGH small/one-seed | overfit 与 Val 强基线区间成立 |
| M3 | rollout vs Direct one-seed | official non-collapse；true D 优于 shuffled D |
| M4 | 删除无效 G/phi/composition 部件 | 在 Val 冻结最小模型 |
| M5 | 三种子 + locked OOD-t | 仅评一次主测试；按预注册统计 |
| M6 | OOD-s/st、original EN21、下游/`U` | 只做不改变主方法的支持实验 |

硬止损：

- `phi` Gate 失败：不写 controllable renderer；
- Stage1.5 不增益：移附录；
- rollout 明显落后 Direct：停止 compositional world-model 主张；
- true D 不优于 shuffled D：删除 driver-aligned 强调；
- shuffled G 与 true G 等价：删除 G；
- 核心失败时，不用 FM、下游或 `U` 追加模块挽救。

## AAAI 7-page allocation

| 内容 | 建议页数 |
|---|---:|
| Introduction + contributions | 0.75 |
| Related work | 0.55 |
| Method / role separation / DGH transition | 2.1 |
| Dataset + protocol + metrics | 0.8 |
| Main results + ablation | 1.8 |
| Analysis / qualitative / limitations | 0.7 |
| Conclusion | 0.3 |

正文只保留两个贡献点：

1. observation–dynamics role-separated predictive-state formulation；
2. shared compositional DGH transition 及其在官方 OOD、条件错配和严格 observation-pair 协议下的证据。
