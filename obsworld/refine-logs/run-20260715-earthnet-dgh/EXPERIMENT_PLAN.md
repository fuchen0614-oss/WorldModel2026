# ObsWorld Final Claim-Driven Experiment Plan

日期：2026-07-15  
目标：以最少但充分的实验支撑 AAAI-27 七页正文

## 1. Claim-to-evidence map

| 主张 | 最小充分证据 | 正文位置 | 失败动作 |
|---|---|---|---|
| C1：role-separated state 对预测有用 | Stage1/1.5 matched Stage2 skill；固定 source state 的 target-product cross-decoding；correct vs shuffled target condition | Mini Table/Fig. 2；若 Gate 失败删除 | fixed-product S2 + acquisition-aware initialization |
| C2：DGH transition 可组合 | 同一个 `T_delta` 的 10d direct vs 5d+5d composed；真实 target loss；horizon curve；matched Direct | Table 2 + Fig. 1 | 删除 `L_part` 或停止 compositional claim |
| C3：模型在官方任务有竞争力 | GreenEarthNet locked OOD-t 官方指标；强公开基线；自有方法三种子 **且** tile/location-cluster paired CI | Table 1 | 若明显落后，停止 AAAI 主线 |
| C4：模型使用时间对齐 D/G | true/no/plausible-shuffled D；no-G；跨 location 完整 G 置换 | Table 2 + appendix | 删除无效条件及相应 claim |

## 2. M0：协议审计

### M0-data

必须分开记录：

- GreenEarthNet official：Train、Val、OOD-t、OOD-s、OOD-st manifest；
- raw download package：`train/iid/ood/extreme/seasonal` 文件夹；
- original EarthNet2021 Extreme/Seasonal：secondary diagnostics，不称 GreenEarthNet official split。

必须通过：

1. official manifest 无 fallback root scan；
2. official NetCDF prediction format 与 evaluator parity；
3. context validity、training supervision 和 official evaluation mask 三者分开；
4. train-only normalization statistics；
5. future cloud/SCL/dlmask 只进入 loss/evaluation；
6. 复现 persistence、previous-year 或 climatology 中至少两个官方 artifact。

### M0-D fairness

- 主协议使用公开 Contextformer 相同的 24-D/5-day 天气 token：8 个 E-OBS 变量 × mean/min/max；raw daily 8-variable encoder 只是附录增强；
- Direct、rollout、ObsWorld 接收同一 24-D 序列、missingness 处理、historical weather 和 calendar；
- 同一变长 `E_D` 对 5/10/20 日分别消化 1/2/4 个五日 token，禁止为各时间跨度设独立 driver heads；
- 共享同构 driver encoder；matched Direct 与 ObsWorld 的总参数量相差不超过 10%，调参预算匹配；
- calendar 与 weather 分离；
- `D-core` 只作信息删减消融；
- plausible-shuffled/wrong-year D 在同 location 或相近 climate region、相近 DOY bin 中置换，避免明显 OOD 天气。

### M0-phi

先审计本地 SSL4EO：

1. 是否已下载 S2L1C；
2. L1C/L2A 同 shard 的 key、timestamp、file_id 是否逐样本一致；
3. common bands、cloud support、归一化与 geographic split；
4. 只改变 product level 的 `phi` 字段；
5. 先做 20 shards pilot，再根据有效 pair 数决定是否扩到 50/100 shards。

当前远程 spot check 已确认官方 SSL4EO-S12 v1.1 同时提供 L1C/L2A，且 shard 1 的前 12 个样本 timestamp 与 file_id 完全一致；本地数据是否完整仍需 M0-phi 确认。

## 3. M1：Stage1.5 证据与 repair

### M1-A：不重训，先验收 60k

比较：

1. Stage1 S2-only；
2. Stage1 dual；
3. Stage1.5 60k state bridge。

统一使用 geographic held-out split、同一 deterministic projector、三种子。报告：

- frozen future-NDVI/change probe；
- S1/S2 state agreement，按 `0–1/1–3/3–7 day` 分层；
- balanced nuisance/semantic probe，仅作诊断；
- 完全相同 Stage2-A 下的 Val forecast skill。

旧 probe 不进入论文结果。

### M1-B：轻量 cross-observation repair

训练固定 source state 的交叉解码：

```text
s_s1 = Q_s1(x_s1, phi_s1)
s_s2 = Q_s2(x_s2, phi_s2)
O_s2(s_s1, phi_s2) -> x_s2
O_s1(s_s2, phi_s1) -> x_s1
```

它证明的是 cross-modal state utility，不把 S1/S2 当纯 nuisance pair。

### M1-C：product-conditioned Gate

优先 exact-acquisition L1C/L2A，使用 shared state + 同一 decoder `O(s,p_target)`，`p_target` 是产品 token，在 common bands 上做 self/cross four-way decoding。target 始终是真实 target-product pixels，L1C/L2A normalization 分别仅用 Train 统计。测试固定 source state 和全部权重，wrong condition 只替换 token，不替换整个 head。

预注册四行消融：

1. self only：shared tokenized decoder，只有 self reconstruction；
2. self + cross-observation：上行加 fixed-source cross decoding；
3. full w/o target-product condition：Stage1.5 alignment/variance/teacher + self/cross 都保留，但从同一 decoder 去掉 product token；
4. full：Stage1.5 完整约束 + self/cross + shared decoder + target-product token。

不使用两个可以独立记忆产品的大 decoder heads；消融间总参数差控制在 10% 内。

报告固定 source state 下：

- correct target product token；
- wrong/shuffled target product token；
- source-only/self reconstruction；
- cross-product reconstruction；
- held-out geography。

只有 correct 显著优于 shuffled、cross decoding 稳定，才在正文写 product-conditioned observation formation。

## 4. M2：matched Direct-DGH

```text
e_1:10 = Q(x_1:10, phi_1:10)
s_0 = I(e_1:10, D_history, C_history, G)
s_hat_h = F_direct(s_0, D_1:h, C_1:h, G, h)
x_hat_h = O(s_hat_h, fixed-S2)
```

要求：

- 20 horizons 全监督；
- full official 24-D/5-day E-OBS path，不用重复累计 9 维摘要；
- decoder 联合训练；
- 小样本 overfit、mask、band、export、official evaluator 全通过；
- Stage1 与 Stage1.5 只改变 initialization，其他配置相同。

## 5. M3：Stage2 主方法

### M3-A：shared five-day rollout

```text
s_k = T_5(s_{k-1}, D_k, C_k, G)
x_hat_k = O(s_k, fixed-S2)
```

它是必要架构对照，不单独作为方法创新。

### M3-B：variable-step control-aware partition-consistent ObsWorld

同一 `T_theta` 接收 5/10/20 日区间。训练时随机采样 anchor 与 partition：

```text
s_10_direct = T(s_0, D_1:2, C_1:2, G, 10d)
s_10_comp   = T(T(s_0,D_1,C_1,G,5d),D_2,C_2,G,5d)
```

`D_1:2/C_1:2` 必须严格等于短区间 `D_1/C_1` 与 `D_2/C_2` 的时间拼接；这是非自治受控系统的 partition/evolution consistency，不是普通 semigroup 首创主张。`D_1:2` 由同一变长 `E_D` 一次读取两个 24-D token。

损失：

```text
L = L_RGBN_visible
  + lambda_ndvi * L_NDVI_visible
  + lambda_multistep * L_5/10/20_real_target
  + lambda_part * L_partition

P(s) = LayerNorm(s, elementwise_affine=False)
L_partition includes d(P(s_direct), stopgrad(P(s_comp)))
                  and observation-space consistency
```

- NDVI 从 predicted Red/NIR 确定性计算；
- 不再把单帧 encoded latent 当完整 future-state truth；
- 两个 partition 分支都有真实 observation supervision；
- `P` 固定无参，禁止可学习一致性 projector；
- `lambda_part` 在 forecast 稳定后再从 0 warm up；
- curriculum：1 step → 2/4/8/20 step open-loop；future pixels 从不 teacher-force 输入。

### M3-C：冻结的 partition sampling 协议

在完整 2×2 和 locked OOD 前冻结以下规则：

- 单区间真实 target 的 `delta_t={5,10,20}` 抽样比例默认为 `0.50/0.25/0.25`；
- partition anchors 中，`10d vs 5d+5d`、`20d vs 10d+10d`、`20d vs 5d+5d+5d+5d` 的比例默认为 `0.50/0.25/0.25`；
- anchor 在 context 结束后的 20 个 target intervals 中均匀抽取，但要求所有分支的终点相同且不越界；
- 长分支的 `D[a:c]/C[a:c]` 必须逐 token 等于短分支 `D[a:b]/C[a:b]` 与 `D[b:c]/C[b:c]` 的拼接，`G` 不变；
- terminal observation mask 对所有分支共用；中间真实像素可以做 loss target，但绝不输入后续 transition；
- `lambda_part` 先为 0，在 forecast warm-up 后用前 20% 主训练 steps 线性升到冻结值。冻结值只能从预先声明的 `{0.01,0.05,0.1}` 小网格中用 Val 选择，并在查看 locked OOD 前固定；
- 所有分支的 RGBN/NDVI 损失按可见像素和通道归一化；state/observation partition loss 分别记录，不在看到 OOD 后再改组合。

如果计算预算不足，优先保留 `10d vs 5+5` 和 `20d vs 10+10`；删除 `20d vs 4x5` 必须在主 2×2 开始前记录，不得根据结果选择 partition。

### M3-D：2×2 干预隔离

四格从同一 Stage1/1.5 起点开始，使用相同的 product-pair 数据、batch 数、更新数、Stage2 schedule、D/C/G、参数预算和 evaluator。无 product-axis 行仍处理相同 product batch 并保留 self/alignment loss，只设 `lambda_crossobs=0`；无 temporal-axis 行仍计算 direct/composed 分支并用真实 endpoint 监督，只设 `lambda_part=0`。四格之间不允许更换 checkpoint family 或增加数据/计算。

### matched controls

Direct、shared rollout、main ObsWorld 共享：

- encoder、initializer、decoder；
- raw D/C/G 信息；
- 20 targets；
- 总参数差不超过 10%，并报告 FLOPs/throughput；
- training cubes、optimizer steps 与 tuning budget；
- output/evaluator。

## 6. 正文四个 artifact

### Table 1：Official OOD-t main result

建议行：Persistence、Previous Year/Climatology、Contextformer、一个强 recurrent/video baseline、matched Direct、ObsWorld。  
建议列：R2、RMSE、NSE、absolute bias、Outperformance、RMSE25。

Contextformer 是公开竞争参照；只有拿到逐样本 predictions 时才对它做 paired non-inferiority。Own Direct vs ObsWorld 三种子全部运行，同时使用 tile/location-cluster paired bootstrap 95% CI；报告 seed 均值±标准差与 clustered paired CI，两者不二选一。

### Table 2：Mechanism evidence

分两个 panel。

**Panel A — core factorial + architecture controls**：

1. matched Direct；
2. shared `T_5` rollout；
3. base state + variable-step no-part；
4. cross-observation state + variable-step no-part；
5. base state + `L_part`；
6. cross-observation state + `L_part` = full ObsWorld。

第 3–6 行是 product-axis × temporal-axis 2×2，使用同一 Stage2/D/C/G/参数预算/evaluator。预注册检验 long-horizon/OOD 上的两个主效应与交互项。若 product-axis 不改善 EarthNet forecast/OOD，它降为 mechanism-only，不再作核心贡献。

对于越低越好的 loss/RMSE，预注册 `Delta_int=L_11-L_10-L_01+L_00`。只有 `upper95CI(Delta_int)<0` 才使用 **synergistic**；否则只使用不需要交互显著的 **jointly constrained**。

**Panel B — D/G use**：full、no-D、plausible-shuffled D、no-G。shuffled-G、wrong-year/lagged D、D-core、calendar-only 放附录。

### Figure 1：Horizon + composition

- 左：5–100 日 NDVI error curve；
- 右：同一 variable-step model 的 10/20 日不同 partition observation gap；
- 同时显示真实 forecast error，防止只优化一致性。
- inset：跨 checkpoint/model/region 的 partition gap 与 long-horizon OOD error 相关，方向和统计方法预注册。

### Mini Table/Figure 2：phi Gate

若 L1C/L2A Gate 通过：`self only / self+cross / full w/o target-product condition / full` + correct/wrong product-token decoding + 一组可视化。  
若失败：整块删除，把篇幅用于 D/G interventions 和 failure cases；不得保留强 renderer 文字。

## 7. Appendix / secondary track

- OOD-s/OOD-st；
- original EarthNet2021 Extreme/Seasonal；
- full RGBN MAE/SAM/SSIM；
- G full-location permutation；
- Stage1/1.5 全部 probes；
- efficiency、missingness、landcover/season subgroup；
- `U` observation correction；
- 一个 FM initializer 或一个 narrow downstream，二选一。

## 8. 统计与测试纪律

- Val 上冻结 architecture 和 loss weights；non-inferiority margin `delta_NI` 必须在查看 ObsWorld locked-OOD 结果前，根据公开基线波动、指标量纲和科学/业务容差预先登记；不能用 ObsWorld 结果反推 margin；
- `delta_NI` 不套用官方 Outperformance 的 `0.01`；
- 最终 own methods 三种子，且进行 tile/location-cluster paired CI；
- locked OOD-t 只在冻结后正式评估；
- CI 以 location/tile cluster 为重采样单位；
- 所有 normalization、imputation 和 DOY pairing 只用 Train 统计。

预先冻结的形式化判定（以 loss/RMSE 越低越好为例）：

```text
Competitiveness: upper95CI(L_ours - L_matchedDirect) <= delta_NI
Partition value: upper95CI(gap_full - gap_noPart) < 0
No forecast harm: upper95CI(L_full - L_noPart) <= delta_part
D usage: upper95CI(L_trueD - L_plausibleShuffleD) < 0
G usage: upper95CI(L_trueG - L_noG) < 0
Product role: upper95CI(L_correctToken - L_wrongToken) < 0
```

`delta_part` 同样在主方法结果之前预注册。如果不等式不成立，按 Stop rules 降级，不在事后换指标或放宽门槛。

## 9. 七页分配

| 内容 | 页数 |
|---|---:|
| Introduction + contributions | 0.75 |
| Related work | 0.45 |
| Method | 2.25 |
| Protocol | 0.65 |
| Table 1 + Table 2 | 1.25 |
| Figure 1 + phi mini result/limitations | 1.35 |
| Conclusion | 0.30 |

AAAI-27 正文限 7 页、总长 9 页且额外页只能放参考文献，因此四个 artifact 之外的证据不能假设审稿人一定看 supplement。

### AAAI-27 deadline sprint boundary

截至 2026-07-15，官方摘要/全文截止分别为 2026-07-21 和 2026-07-28（UTC-12）。若目标是本轮截稿，mandatory scope 只包括 M0、matched Direct、M3 variable-step/partition one-to-three seeds，以及 Table 1/Table 2/Figure 1；product `phi` 只有现成 pilot 已通过时才进入。OOD-s/st、original Extreme/Seasonal、`U`、downstream、FM 和 full Stage1.5 repair 全部后置。

## 10. Stop rules

| Gate | Pass | Fail |
|---|---|---|
| Protocol | evaluator/mask/baseline parity | 不跑长训练 |
| Stage1.5/product axis | cross-observation 对 EarthNet Stage2 forecast/OOD 有预注册收益，且 product Gate 成立 | 主文用 Stage1/base state；product axis 降 mechanism-only |
| Product phi | correct > shuffled 且 cross decode 成立 | fixed S2 claim |
| Rollout | long horizon 不崩且接近 Direct | 停止 compositional claim |
| Partition | gap 降低且真实 error 不恶化 | 删除 `L_part` |
| D | true > plausible shuffle | 删除 driver-aligned claim |
| G | no-G 明显退化 | 删除 G |
