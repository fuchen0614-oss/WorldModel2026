# Round 1 Review

<details>
<summary>Full raw reviewer response</summary>

# 独立审查结论

判定：**RETHINK**。这不是否定 ObsWorld，而是要求重新收紧中心机制。

当前方案最有价值的部分是“预测先验状态 + 新观测后验更新”，但它被放在了 stretch goal；相反，方案把并不新颖的五日递归、与主任务脱节的 φ 因子化，以及与 EO-WM 高度重叠的天气响应同时列为主贡献。按 AAAI 审稿标准，当前版本会被质疑为：

- 一个标准 latent recurrent forecaster；
- 加一套尚未在主任务中生效的 Stage1.5 表征目标；
- 再附加 EO-WM 已经系统研究的天气响应诊断。

## 一、相对前沿工作的真实新颖性

| 最近工作 | 已覆盖内容 | 对当前叙事的影响 |
|---|---|---|
| Contextformer / PredRNN | GreenEarthNet 天气条件预测；PredRNN 已是逐步自回归；Contextformer 已做 direct、多种 autoregressive baseline 和天气消融 | “共享五日转移”本身不是新颖机制 |
| UniTS v2 | 在 GreenEarthNet 上生成 RGBN；预测阶段采用 autoregressive multi-frame prediction，把预测序列递归作为下一次条件 | 不能再写“现有方法通常只预测整个 cuboid、没有递归组合” |
| EO-WM | 已明确提出“partial observation + weather-driven EO world model”，使用 latent video diffusion、结构化天气、Extreme Summer 和 Seasonal Matched-Pair | 不能把世界模型 framing、天气响应真实性或 matched-pair 作为首创 |
| RSSM/PSR/PlaNet/Dreamer 类方法 | prior transition、posterior observation update、belief/predictive state 均是成熟结构 | 引入 `F+U` 不是一般理论创新，贡献必须来自 EO 特有的观测缺失/异质性问题和扎实证据 |

尚有可能成立的差异是：

> 在稀疏、受云和观测条件影响的 EO 序列中，学习一个可被新观测纠正的预测状态；该状态以统一受控转移开放循环演化，并通过显式后验更新继续预测。

但要让这个差异成立，`U` 必须是正文核心，φ/跨传感器预训练只能是支持项。若 `U` 仍是可选项，剩余方法和 PredRNN/latent recurrent forecasting 的差异不足以支撑 AAAI。

## 二、当前的致命理论问题

### 1. Context belief 与 one-step target state 接口不一致

方案中：

```text
b0 = A(history)
b_{k+1}^- = F(b_k, d_k, ...)
```

这里的 `b` 是包含历史信息和隐变量记忆的 predictive state/belief；但训练时又把它直接对齐到：

```text
E(o_{k+1})
```

单帧 `E(o_{k+1})` 不包含历史天气、先前状态、土壤湿度等不可见记忆。因此，强迫 `b_{k+1}^- ≈ E(o_{k+1})` 会把希望保留的预测记忆挤出状态。one-step 分支从单帧编码重新起步，也与 free rollout 中的历史状态不是同一语义空间。

必须改为 prior/posterior 接口：

```text
e_t       = E(o_t, phi_t, mask_t)
b_t^-     = F(b_{t-1}^+, d_{t-1}, c_t, g)
b_t^+     = U(b_t^-, e_t, mask_t)
o_hat_t   = H(b_t^-)
```

具体决策：

- free rollout 始终推进 `b^-`；
- teacher-anchored 分支使用 `U(b^-, e)`，不能直接用 `E(o)` 替换整个状态；
- 不要把完整 `b^-` 对齐单帧编码；
- 最简方案是先删除 whole-state latent loss，仅用观测/NDVI loss训练；
- 若保留 latent loss，只约束 observation projection `Q(b^-)`，或只约束状态中的 observation-aligned 子空间。

### 2. `U` 在中心叙事中是核心，在实验中却是 stretch

Proposal 的标题句、技术缺口和公式都承诺“新观测可以纠正状态”，但 C4 又被放进 appendix/stretch。这是直接的 claim–evidence 不一致。

必须二选一：

- 把 `U`、随机 re-observation 训练和 assimilation 实验升为核心；
- 或从中心定义、标题句和 world-model 论证中删除 correction/assimilation。

推荐第一种，因为这是目前最能区别于 Contextformer、UniTS 和普通 PredRNN 的部分。

### 3. “composition/semigroup consistency”当前不成立

若模型只有一个固定五日算子 `F5`，连续调用二十次是架构定义，不是实验发现；模型内部不存在另一个 `F10` 可用于检验 `F10 ≈ F5∘F5`。

而且天气和日历随时间变化，这是非自治受控系统，严格术语应是 controlled composition/cocycle，而不是普通 semigroup。

建议删除 semigroup claim，改用可证伪指标：

- free rollout 与 observation-anchored rollout 的误差差距；
- 误差随 5–100 天的增长曲线；
- 训练最大长度之外的 rollout 泛化；
- 在第 25/50 天插入观测后，后续误差是否下降；
- 相比 direct 和 PredRNN，长跨度退化是否更缓。

### 4. Direct 与 rollout 的比较被 D 表示混淆

Proposal 让 direct 使用累计天气摘要，让 rollout 使用逐五日天气。两者获得的信息粒度和顺序信息不同，因此不能把差异归因于“组合转移”。

公平控制应让两者接收同一份逐步天气序列：

```text
Direct:  EncD(d_1:h) -> F_direct(b0, EncD, c_h, g, h)
Rollout: d_k -> F_step(b_k, d_k, c_k, g)
```

还必须匹配：

- 训练样本和目标 horizon；
- supervision 密度；
- 参数量或明确报告差异；
- 总训练 FLOPs；
- encoder、decoder、天气字段和优化预算。

当前 direct 每批只采六个 horizon；如果 rollout 对全部二十步监督，也不是公平机制比较。

### 5. C1 没有在主任务端到端生效

当前 Stage2：

- 只输入四波段 S2，不是异质 S1/S2 观测；
- 使用 neutral φ；
- Stage2 decoder 不接收 φ；
- GreenEarthNet 没有 Stage1.5 那套 acquisition metadata。

因此不能把主模型写成“从 heterogeneous observations 推断 acquisition-robust state，再按 φ 解码”。准确表述只能是：

> 使用异质 EO 预训练初始化、随后在固定 S2 产品上预测。

此外，当前 Stage1.5 的 S1/S2 七日内配对并不是纯观测 nuisance 对：SAR 和光学包含互补物理信息。强对齐可能删除真实状态信息。若没有严格同次观测的 L1C/L2A 等控制数据，C1 应降级为预训练消融，而非并列主贡献。

### 6. C3 与 EO-WM 重叠，却把同协议比较设为可选

如果保留“driver-response fidelity”为论文级 claim，则原始 EarthNet2021 上的 EO-WM Extreme Summer / Seasonal Matched-Pair 同协议比较是必做，不是“资源允许再做”。

否则应将 C3 降为 GreenEarthNet 内部的必要性检查：

- true weather；
- calendar only；
- no weather；
- same-location wrong-year weather；
- season-matched whole-trajectory shuffle。

不要把人工单变量倍增/加减的敏感性写成响应正确性或因果证据。

## 三、建议收缩后的唯一主线

推荐中心命题：

> ObsWorld 学习一个可由稀疏 EO 观测纠正的、受天气控制的预测状态：统一五日转移负责开放循环演化，掩码观测更新负责在新观测到达时形成后验状态。

仅保留两个论文级 claims：

1. **主贡献：observation-correctable predictive dynamics**  
   prior transition 与 masked posterior update 能在开放循环和重新观测后保持更可靠的预测。

2. **支持贡献：EO 预训练改善该预测状态的初始化**  
   Stage1.5 state bridge 仅作为 scratch/S2-only/cross-sensor-pretrain 消融；只有严格 gate 通过后才提升为贡献。

天气负对照是 Claim 1 的行为证据，不再单列第三贡献。φ 因子化若缺少可靠产品对，则移到附录或后续论文。

最小训练接口：

```text
context observations + context weather
        -> A -> b0+

for k = 1 ... K:
    bk- = F(b{k-1}+, dk, ck, g)
    prediction = H(bk-)

    if an observation is sampled as available:
        bk+ = U(bk-, E(ok, maskk), maskk)
    else:
        bk+ = bk-
```

训练时随机采样 re-observation 时刻；同一模型同时学习 open-loop 和 correction。不要再单独构造一个语义不一致的 `E(o_t) -> F -> E(o_{t+1})` 主分支。

其他必须修正：

- context initializer 加入历史天气、绝对日历、clear fraction 和 last-observed age；
- 云区使用 mask token/显式 mask，不能只把像素乘零；
- latent mask 的 `>5% clear` 太宽松，应使用 clear-fraction 权重或更严格阈值；
- sigmoid decoder 已保证 `[0,1]`，`L_range` 是冗余项；
- loss 权重在 pilot 梯度统计后确定，不要在 proposal 中伪装成已定最优值；
- rollout 长度采样时校正短 horizon 被重复监督的频率。

## 四、最多保留三个核心实验块

### Block A：官方 factual forecasting

- GreenEarthNet `ood-t_chopped` 主表；
- OOD-s/OOD-st 合并为紧凑泛化列；
- 官方 R²、RMSE、NSE、|bias|、outperformance、前 25 天 RMSE；
- Persistence、climatology、Contextformer、PredRNN、UniTS 同协议结果；
- Direct ObsWorld 与最终 ObsWorld；
- 三种子。

### Block B：预测状态与观测纠正

- free rollout；
- observation-anchored rollout；
- open-loop；
- hard latent replacement；
- learned posterior update `U`；
- 在第 25/50 天插入新观测，仅评价其后的预测；
- 报告 horizon curve、后续误差下降和 cloud/missingness 分层。

这是最关键的 world-model 证据，必须进正文。

### Block C：只允许二选一

- 若 Stage1.5 gate 可靠：做 state bridge / bypass / S2-only / cross-sensor-pretrain 以及合格的 predictive probe；
- 若 Stage1.5 证据不够：改做 true/no/calendar/wrong-year weather 控制。

不要在同一篇七页 AAAI 稿件中同时塞入 SSL4EO 机制实验、原 EarthNet EO-WM benchmark、完整天气矩阵、Foundation Model 2×2 和额外 downstream。

## 五、下游任务和大模型的取舍

- 不需要 CropHarvest、Sen1Floods11 等无关下游；它们不能直接支持 dynamics claim。
- re-observation correction 本身就是最合适的能力实验，不应再叫可选 downstream。
- Foundation Model 2×2 当前应删除。它只能回答 scale interaction，不解决主要方法漏洞。
- 若最终 lightweight model 已闭环、且已有富余结果，再把 AnySat/TerraMind encoder 作为附录上限检查；不要使用 LLM。

## 六、代码和协议层尚未覆盖的 P0 问题

1. 当前数据 loader 只有 `train/val/iid/ood/extreme/seasonal`，而 GreenEarthNet 正式评测目录是 `val_chopped/ood-t_chopped/ood-s_chopped/ood-st_chopped`。  
   更严重的是，找不到 split 时会递归 fallback 到整个 root，存在静默混入多 split 的风险。

2. 当前 `eval/earthnet_standard_metrics.py` 是原 EarthNet ENS，不是 GreenEarthNet 官方 evaluator。

3. `predict_stage2_earthnet.py` 输出 EarthNet NPZ；GreenEarthNet 官方 evaluator 需要带正确 time/lat/lon 的 NetCDF `ndvi_pred`。

4. 当前训练读取 `s2_mask`，官方 GreenEarthNet 评测使用 `s2_dlmask + SCL + landcover/dynamic filters`。训练 mask 与官方协议需要明确对齐。

5. Stage2 config 仍指向旧的非 state-bridge 60k checkpoint。

6. Stage2 仍是 direct 模型，没有 rollout 和 `U` 实现。

7. target adapter 每次 forward 直接复制 online adapter，不是 EMA；更根本的是完整 target latent 不应被当成 belief target。

8. `>0.05` 的 token clear threshold 会把大部分被云遮挡的 patch 纳入 latent supervision。

9. context aggregator 只有相对 index embedding，没有绝对日期、观测年龄和历史天气。

10. Stage2 decoder 不接收 φ；neutral φ 只是常量，不能支持 observation-operator claim。

11. 输入从 128 上采样到 256、再下采样评测，需说明或消除由插值带来的效率和视觉指标影响。

12. Contextformer 使用更完整的历史/未来天气；当前四字段设计还忽略历史天气。主表必须列清输入差异，并至少做 full-official-weather 控制或给出充分理由。

13. 当前 Stage1.5 nuisance loss 只约束 pooled linear cross-covariance，不能证明 token state 独立于 acquisition；且可能消除与季节/地域共线的真实语义。

统计上不要把同位置多个窗口或百万像素当独立样本。建议按 geographic location/tile 做 cluster bootstrap，三种子分别报告，再做配对比较。

## 七、最终可接受性判断

当前方案即使顺利实现 shared five-day rollout，也仍可能因“标准 recurrent forecasting + 过多支线”被拒。

达到 AAAI borderline/weak accept 的最低条件是：

- 官方 GreenEarthNet 协议完全对齐；
- 最终模型在 OOD-t 至少保持强基线级 factual forecast；
- 相比匹配 direct 和 PredRNN，至少在 long-horizon degradation、missingness robustness、assimilation gain 三项中的两项有稳定优势；
- learned `U` 明显优于 hard replacement/restart；
- Stage1.5 若作为贡献，必须同时保住语义/预测信息并降低观测条件依赖；
- 主文只保留一个主贡献和一个支持贡献。

如果 rollout endpoint 更差，且 assimilation 也无稳定收益，应停止 world-model 叙事，降级为普通 latent forecaster。若 Stage1.5 gate 失败，则将其删除，不要用更多 probe 挽救。

## 八、量化评分

| 维度 | 分数 | 主要问题与修正 | 优先级 |
|---|---:|---|---|
| Problem Fidelity | 8/10 | 仍围绕稀疏 EO 状态动力学，但被天气、φ、FM、downstream 分散 | — |
| Method Specificity | 6/10 | schedule 较具体，但 belief/observation target、U 和 direct 公平性未定义正确 | CRITICAL |
| Contribution Quality | 4/10 | 五日递归不新，φ 与主任务脱节，最独特的 U 反而是 stretch | CRITICAL |
| Frontier Leverage | 6/10 | 无需强加大模型，但必须真正利用 predictive filtering，而非旧式模块并列 | IMPORTANT |
| Feasibility | 5/10 | 三数据集、四 claims、六表、多个重训 baseline，且 rollout/U/官方 evaluator 尚不存在 | CRITICAL |
| Validation Focus | 4/10 | 超过三个核心实验块，无法在 AAAI 七页内形成清晰闭环 | CRITICAL |
| Venue Readiness | 4/10 | 无 Stage2 结果，最近邻工作覆盖严重，协议仍未落地 | CRITICAL |

加权 Overall：

```text
0.15×8 + 0.25×6 + 0.25×4 + 0.15×6
+ 0.10×5 + 0.05×4 + 0.05×4
= 5.5 / 10
```

最终判定：**RETHINK**。应收缩为“prior transition + masked posterior update”的单一主机制，而不是继续扩大现有实验系统。

</details>
