# ObsWorld：EarthNet 主线、DGH 保留与 Stage2/AAAI 实验重整

> 日期：2026-07-15  
> 状态：**历史重整稿；EarthNet+DGH+世界模型的方向仍有效，但数据下载、L1C/L2A 和截稿优先级已由 45/46 更新。**  
> 范围：本轮只整理叙事、数据、Stage2 及实验；**没有修改训练代码。**
> 当前入口：[45：最终方法与实验决策](45_ObsWorld_AAAI27最终决策_数据DGH叙事与主实验_20260715.md)；[46：代码改造与并行执行路线](46_ObsWorld_AAAI27代码改造与并行执行路线_20260715.md)。

---

## 0. 结论先行

1. **GreenEarthNet 不是 EarthNet2021 的一个子集。**它沿用 EarthNet2021 的训练位置和时空规格，是增强后的兼容版本；论文称 GreenEarthNet，代码中又叫 `earthnet2021x/en21x`。
2. **不必在 EarthNet2021 和 GreenEarthNet 之间二选一。**论文主线写 **EarthNet2021 benchmark family**，主实验采用 **GreenEarthNet protocol over the EarthNet2021x release**；这仍然是 EarthNet 路线，而且更适合目前的 DGH。
3. **DGH 应保留并继续发展。**但“加入天气、DEM、horizon”本身不是创新；需要把 D/G/H 升级为共享状态转移的区间驱动、地理响应背景和可组合时间接口。
4. **原始 ObsWorld 立意不需要大改。**保留“状态推断—状态演化—观测生成”，把过强的“真实物理状态/任意条件渲染”改成可验证的 predictive state 与 product-conditioned/fixed-product observation model。
5. **43 的风险审计有价值，但叙事确实矫枉过正。**它受 EO-WM 的“部分观测、稀疏观测”语言影响较重，又把 `U` 校正抬成唯一新意，导致已经投入很久的 `phi`、DGH 和三柱世界模型被弱化。44 恢复三柱，`U` 回到 Stage3/4。
6. **Stage2 最终不能只是当前 Direct，也不能只把固定 `T_5` 重复 20 次。**推荐同一 transition 学习 5/10/20 日区间，并约束 10 日直接推进与 5+5 日组合推进一致；这才把“连续模拟真实世界”变成可训练、可证伪的算法性质。严格说，有随时间变化的 `D/C` 时这是 **control-aware partition consistency（控制感知的时间分割一致性）**，不是普通自治系统的 semigroup。

总体判断：**这条路线可行，并保留了初版 ObsWorld 大约 80%–90% 的立意；真正需要大改的是 Stage2 的动力学实现和实验协议，不是推倒 Stage1/1.5 与 DGH。**

最终独立复核给出 **CAUTION，8.7/10**：方案已可冻结并进入 `M0 + 单种子 Val pilot`，但在核心 2×2 与 official OOD 结果产生前，不得宣布 AAAI 主张已成立。

---

## 1. GreenEarthNet 多大，与 EarthNet2021 什么关系？

### 1.1 不是子集，而是增强且兼容的 EarthNet 路线

[GreenEarthNet/Contextformer 的 CVPR 2024 论文](https://openaccess.thecvf.com/content/CVPR2024/papers/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.pdf)说明：GreenEarthNet 复用 EarthNet2021 的训练位置与 predictor dimensions，并将自己描述为解决原版缺点的 enhanced version。其[官方代码仓库](https://github.com/vitusbenson/greenearthnet)进一步注明：论文中叫 GreenEarthNet，开发代码里也叫 `earthnet2021x` 或 `en21x`。

| 说法 | 判断 | 原因 |
|---|---|---|
| GreenEarthNet 是 EarthNet2021 的一小部分 | 错 | 不是从原版简单抽子集 |
| GreenEarthNet 与 EarthNet2021 毫无关系 | 错 | 位置、维度和 benchmark 血统保持兼容 |
| GreenEarthNet 是 EarthNet2021 路线的增强/重制数据发布 | 对 | 这是最适合本文的准确表述 |

推荐写法：

> **We study the EarthNet2021 benchmark family and adopt the GreenEarthNet protocol over the EarthNet2021x data release for primary evaluation.**

中文：

> **我们围绕 EarthNet2021 基准系谱开展研究，并在 EarthNet2021x 数据发布上采用 GreenEarthNet 协议进行主评估。**

这不是“改投另一个数据集”，而是把原始 EarthNet 路线切换到更可靠的评估版本。

### 1.2 样本与任务规格

[原始 EarthNet2021](https://arxiv.org/abs/2104.10066)约有 32,000 个样本，包含 20 m Sentinel-2、匹配地形和约 1.28 km 气象变量，任务被定义为 future-weather-guided video prediction。

GreenEarthNet 的正式任务是：

- 每个 minicube 为 `128×128` 像素，即约 `2.56×2.56 km`；
- 30 个五日时刻：10 个历史 context + 20 个未来 target；
- 合计 150 天 daily meteorology；
- 4 个 Sentinel-2 波段：Blue、Green、Red、NIR；
- 8 个 E-OBS 字段：`fg, hu, pp, qq, rr, tg, tn, tx`；
- 三套 DEM、landcover、geomorphon、经纬度与增强云掩码；
- Train 为 23,816 cubes；Val 为 245 cubes；OOD-s 为 800 cubes；OOD-t 是主测试，OOD-s/OOD-st 是空间与时空外推测试。

### 1.3 实际下载大小

2026-07-15 对官方匿名对象存储逐对象统计得到：

| raw package folder | NetCDF 数 | 十进制 GB | GiB |
|---|---:|---:|---:|
| `train` | 23,816 | 80.392 | 74.871 |
| `iid` | 4,205 | 14.190 | 13.216 |
| `ood` | 4,202 | 14.166 | 13.193 |
| `extreme` | 3,972 | 25.530 | 23.776 |
| `seasonal` | 3,880 | 84.588 | 78.779 |
| **合计** | **40,075** | **218.866** | **203.835** |

要区分：上表是 raw download package 的物理文件夹；正式论文评估使用 Train/Val/OOD-t/OOD-s/OOD-st manifests，不能把 raw `extreme/seasonal` 直接称成 GreenEarthNet official splits。

官方仓库建议预留 1 TB，是把解压、缓存、预测结果和重复实验空间都算进去的保守建议，不表示原始对象本身就是 1 TB。

---

## 2. 为什么主协议选 GreenEarthNet？

### 2.1 它反而更适合 DGH

| ObsWorld 接口 | GreenEarthNet 直接支撑 | 对叙事的价值 |
|---|---|---|
| `D`：dynamic forcing | 完整 daily E-OBS 8 variables，覆盖历史与未来 | 天气可写成逐区间 path，而不是终点摘要 |
| `G`：geography | 三套 DEM、landcover、geomorphon、georeferencing | 可检验同一 forcing 在不同地点是否响应不同 |
| `H/Δt`：time | 规则五日格点、20 个未来时刻 | 可训练共享短步与 5/10/20 日分区一致性 |
| observation target | 未来 RGBN + 更可靠 cloud mask | latent rollout 可回到真实产品空间核验 |
| OOD protocol | OOD-t/OOD-s/OOD-st | 时间、空间、时空泛化可分开验证 |

因此，**保留 DGH 与选择 GreenEarthNet 不冲突，而是相互加强。**

### 2.2 原版 EarthNet2021 仍保留什么位置？

最合理的组合是：

```text
论文研究对象：EarthNet2021 benchmark family
主实验：GreenEarthNet official OOD-t
次实验：OOD-s / OOD-st
过程诊断：original EarthNet2021 Extreme / Seasonal
```

原版作为唯一主表会受到旧 cloud mask、ENS 混合感知质量与过程预测、以及新版强基线可比性不足的限制。上述组合既满足 EarthNet2021 主线，又让 AAAI 证据更新、更可靠。

---

## 3. DGH 是否可行？应保留到什么程度？

### 3.1 结论：保留，但从字段升级成动力学接口

DGH 的物理直觉成立：

- `D` 决定这段时间外界施加了什么；
- `G` 决定同一驱动在什么地理背景上发生；
- `H/Δt` 决定状态推进多长时间。

但 Contextformer 已使用 weather + elevation，EarthNet2021 本来就是 weather-guided prediction。因此，**DGH 不能以“我们第一次加入这些字段”的形式成为创新。**

应改写为：

> **DGH 是 ObsWorld 的动力学控制接口；真正的算法贡献是让同一预测状态转移在不同区间驱动和时间分区下可组合，并与观测条件 `phi` 严格分工。**

### 3.2 D：从累计摘要改成逐区间路径

当前代码把 context 结束到每个 endpoint 的天气累计成 9 维特征，且 sum/mean 在固定窗口中存在冗余。这适合 Direct 原型，不适合共享 rollout。

主实验先与公开 Contextformer 协议对齐。其[官方模型代码](https://github.com/earthnet2021/earthnet-models-pytorch/blob/main/earthnet_models_pytorch/model/contextformer.py)默认 `n_weather=24`；[官方数据代码](https://github.com/earthnet2021/earthnet-models-pytorch/blob/main/earthnet_models_pytorch/data/en21x_data.py)对 8 个 E-OBS 变量每 5 日做 mean/min/max，因而每个五日时刻是 24 维。推荐主接口：

```text
weather_5d: [B, 30 intervals, 24 features]
d_k = [mean/min/max of 8 E-OBS variables in interval k]
D[a:b] = E_D([d_a, ..., d_(b-1)], calendar[a:b], missingness)
```

其中 `E_D` 是同一个可处理变长序列的 interval encoder：5/10/20 日分别消化 1/2/4 个五日 token，不为不同 `delta_t` 设独立天气 head。matched Direct、shared rollout 和 ObsWorld 必须接收同一 24-D 序列、同一历史天气、同一 `E_D` 架构和 Train-only normalization。raw daily 8-EOBS encoder 可以做附录增强，不用它制造与公开强基线的输入不对称。

原有核心字段保留成 `D-core`：`rr/tg/hu/qq` 加由温湿度派生的 VPD。其身份是紧凑物理信息消融，而不是故意少给主模型信息后去和 full-EOBS Contextformer 比。

### 3.3 G：保留空间 DEM，不用经纬度记忆捷径

P1 主模型只放一个与强基线匹配的空间 DEM 表征。验证包括 no-G、在 batch/气候区内跨 location 置换整张 G，以及 OOD-s/OOD-st。不要随机打乱 DEM 像素，因为那只会生成明显不真实的地形。landcover/geomorphon 放 P2。

### 3.4 H：不再只是 endpoint 编号

Direct 中 `h_days` 仍可作为查询；最终模型中 `H` 变成 variable elapsed-time interface：

```text
T_theta(s, D_interval, C_interval, G, delta_t)
delta_t in {5, 10, 20 days}
```

100 日正式 rollout 用 20 次五日推进；10/20 日分支用于训练和检验分区一致性。这样 `H` 获得真正的方法含义。

---

## 4. 重新整理后的中心叙事

### 4.1 中文正式版

> **ObsWorld 是一个按观测过程与地表动力学进行角色分工的对地观测世界模型：它从多源、受传感器、产品和成像条件 `phi` 影响的遥感观测中，推断对未来足够的 EO 可观测地表动力学状态；在区间外生驱动 `D`、静态地理背景 `G`、日历 `C` 与时间跨度 `H/Δt` 的约束下推演该状态；再通过给定产品条件的观测模型，把未来状态生成成可由真实卫星数据核验的未来观测。**

### 4.2 英文及中文说明

> **ObsWorld is a role-separated Earth-observation world model.**  
> ObsWorld 是一个按功能角色分工的对地观测世界模型。

> **It infers a predictive state of EO-observable land-surface dynamics from heterogeneous observations affected by sensor, product, and acquisition conditions.**  
> 它从受传感器、产品级别与采集条件影响的多源观测中，推断能够支持未来预测的 EO 可观测地表动力学状态。

> **It advances that state under interval-specific exogenous forcing, static geography, calendar, and elapsed time.**  
> 它利用每个时间区间对应的外生驱动、静态地理背景、日历和经过时间来推演该状态。

> **It then maps the evolved state to future satellite products that can be verified against real observations.**  
> 它再把演化后的状态生成成未来卫星产品，从而能用真实观测直接核验。

### 4.3 直觉版

> **不要直接推演混合了观测条件的像素；先估计地表是什么，再模拟它如何变化，最后模拟卫星如何看到它。**

### 4.4 “模拟真实世界”可以怎么写？

可写：simulate EO-observable land-surface trajectories；model the evolution of a predictive land-surface state under given forcing。中文就是“模拟在给定外生驱动下、可被 EO 观测核验的地表演化轨迹”。

现阶段不写：完整真实地球模拟器、latent 就是真实物理状态、天气输入具有因果反事实意义、任意传感器/太阳角可控渲染。

世界模型要由四项行为成立：内部状态、受控连续转移、不同时间分区的一致推演、回到真实观测空间核验。

---

## 5. 43 是否被 EO-WM 带偏？

你的担心成立一半，而且是值得纠正的一半。

[EO-WM](https://arxiv.org/abs/2606.27277)于 2026-06-25 发布 arXiv v1，中心是 partially observed/weather-driven world modeling、概率 video diffusion、climatology/anomaly/stress forcing 与 Extreme/Seasonal response benchmarks。它是重要近邻，但目前是 28 页 arXiv 预印本，不应反向规定 ObsWorld 的全部语言。

43 做对了：不能声称 first EO world model；不能把 future weather conditioning 当首创；不能把当前 Direct 写成 rollout；不能用旧 phi probe 证明 disentanglement；必须切换官方 evaluator/mask/split。

43 偏掉了：把“稀疏、局部、部分观测”从背景抬成全文中心；把尚未实现的 `U` correction 抬成唯一 dominant mechanism；因担心 EO-WM 而弱化 `phi`、DGH 与 observation formation；容易让人误以为 Stage1.5 和 DGH 可被丢弃。

| 工作 | 主要问题 | 主要机制 | ObsWorld 的区别 |
|---|---|---|---|
| Contextformer | 高分辨率植被预测 | spatial encoder + weather transformer + direct delta | D/G 本身不是我们的新意 |
| EO-WM | 不确定未来与天气响应 | video diffusion + weather decomposition | 不让“稀疏部分观测”主导全文 |
| [Earth-o1](https://arxiv.org/abs/2605.06337) | 原生异构大气观测的统一建模 | unified grid-free dynamical field + latent evolution + cross-sensor inference | 证明 Q/T/O 角色分工不是组件首创；我们只能守 land-surface DGH 与两轴行为约束 |
| [COP-GEN](https://arxiv.org/abs/2603.03239) | 异构 EO 多模态联合生成 | native-resolution any-to-any stochastic generation | L1C/L2A 翻译不是新意；product Gate 只能证明 ObsWorld state/decoder 的角色与预测效用 |
| [Intrinsic Differential Consistency](https://arxiv.org/abs/2605.08454) | 离散观测下恢复连续动力学 | time-conditioned variable-step flow + macro/micro composition regularization | 可变步长/分割一致不是首创；我们的增量只在非自治 `D/C` 路径、EO 部分观测与产品轴联合约束 |
| ObsWorld | 观测过程与动力学混杂、长期转移缺少组合约束 | cross-observation role constraint + DGH variable-step partition consistency | 角色分工与组合行为必须可训练、可检验 |

正文中心词恢复为：`observation–dynamics role separation`、`predictive land-surface state`、`DGH-controlled compositional transition`、`verifiable observation formation`。方法上用一句话串起两条可验证的约束轴：

> **The predictive state is constrained across observation products by cross-observation decoding and across temporal partitions by control-aware partition-consistent transitions.**  
> 中文：该预测状态一方面通过跨观测解码受到产品轴约束，另一方面通过控制感知的分割一致转移受到时间轴约束。

### 5.1 查新后的安全贡献边界

不再主张：首个 EO world model；首个 Q/T/O 分工；首个 multi-sensor shared state；首个 L1C/L2A 翻译；首个 variable-step/semigroup/partition regularizer；首次使用 weather + DEM + horizon。

可以守但必须靠实验成立的是：

1. **特定失败模式**：EarthNet 长时预测中，观测/产品变化与受天气驱动的地表变化缺少联合的行为约束；
2. **两轴联合方法**：同一 predictive state 在产品轴接受 cross-observation decoding，在时间轴接受 DGH control-path partition consistency；
3. **不可替代的行为证据**：跨产品约束必须提升 EarthNet future utility，partition loss 必须降低 composition gap 且不伤害真实 forecast，true D/G 必须优于可信置换，且上述行为在 OOD-t/s/st 中仍成立。

因此新颖性不是架构图自动提供的，而是一个需要 Gate 的组合主张。如果 cross-observation 不改善 Stage2，或 controlled partition 不改善长期行为，就不足以用“两轴一致的 EO world model”作 AAAI 方法贡献。

---

## 6. Stage1/1.5：保留已有投入，重新定义证据

### 6.1 Stage1 保留

Stage1 是 multi-modal EO initialization，不单独承担世界模型主张。

### 6.2 Stage1.5 已训练，不应写成“没有做过”

现有 Stage1.5 60k 已完成 S1/S2 shared state bridge、两个 `phi`-conditioned self-reconstruction heads、近时 S1/S2 VICReg alignment、nuisance penalty 与 teacher anchor。

它没有完成的是 target-condition cross-decoding。正确说法是：

> **Stage1.5 训练已完成，但尚缺 paper-grade、geographic-held-out 的角色分离与 future utility 证据。**

### 6.3 先验收 60k，不立即重练

先做 geographic held-out split、同一 deterministic projector、pair 时间差分层、frozen future-NDVI/change probe、完全相同 Stage2-A 下的 forecast skill。旧 phi probe 因路径、projector、split 与类别平衡问题，不进入论文数字。

### 6.4 轻量 repair：把角色分离写进 loss

当前只有 self-reconstruction；repair 增加固定 source state 的交叉解码：

```text
s_s1 = Q_s1(x_s1, phi_s1)
s_s2 = Q_s2(x_s2, phi_s2)
O_s2(s_s1, phi_s2) -> x_s2
O_s1(s_s2, phi_s1) -> x_s1
```

现有 dual heads/state bridge 使其在架构上可行，但训练脚本仍需修改。S1/S2 观测不同物理量，因此它证明 cross-modal predictive-state utility，不证明二者仅差 `phi`。

### 6.5 更严格的 `phi` 证据：L1C/L2A

[SSL4EO-S12 v1.1 数据卡](https://huggingface.co/datasets/embed2scale/SSL4EO-S12-v1.1)确认同一位置具有 S2L1C、S2L2A、S1GRD 等模态。本轮对官方远程数据 spot check 发现：train shard 1 前 12 个 L1C/L2A 样本的 key、4 个 timestamp 与 file_id 完全一致，说明 exact-acquisition product pair 路线高度可行。

但当前工作区指向的原训练机数据目录未挂载，不能确认本地是否已下载 L1C。因此先做 `M0-phi`：查本地 L1C、全量核对 key/time/file_id/common bands/cloud support/geographic split，先做 20 matched shards pilot，通过后再扩 50/100 shards。

它最多支持 **product-conditioned S2 observation formation**，不能外推成任意传感器与太阳角 renderer。主方法必须使用同一解码器 `O(s, p_target)`，`p_target`是 L1C/L2A 产品 token；评估 wrong/shuffled condition 时只替换 token，不能把整个 decoder head 换掉。固定 source state，target 仍是真实 target-product pixels，L1C/L2A 归一化只用各自 Train 统计。

预注册的 product ablation 为：

| 行 | 训练/解码设置 | 回答的问题 |
|---|---|---|
| self only | shared tokenized decoder，仅同产品重建 | 只重建观测是否已足够 |
| self + cross-observation | 在上行加固定 source state 的交叉监督 | 产品轴交叉约束的直接增量 |
| full w/o target-product condition | 保留 Stage1.5 alignment/variance/teacher 与 self+cross，但从同一 decoder 移除 product token | 无产品条件时是否只能输出折中观测 |
| full | Stage1.5 完整约束 + self/cross + shared decoder + target-product token | `phi_product` 是否真正决定观测生成 |

四行不使用两套独立大 decoder；只有第三行移除 product token，其余都用相同 shared decoder 定义。若为公平需调整宽度，总参数差仍限制在 10% 内。

---

## 7. Stage2 最终应该长什么样？

### 7.1 当前实现是真实有用的 Direct baseline

当前 `obsworld_stage2.py` 把 context 聚成同一个 `z_context`，每个 horizon 独立预测 endpoint，不把未来状态传给下一步；同时使用 neutral `phi`，decoder 不接 `phi`。所以它是 Direct multi-horizon baseline，不是 rollout。应保留成 matched control。

### 7.2 最终模型

观测与 context state：

```text
e_i = Q(x_i, phi_i, validity_i)
s_0 = I(e_1:10, D_history, C_history, G)
```

固定一个轻量 history initializer `I`，不再在“同一 transition/另一个 initializer”之间摇摆。

variable-step transition：

```text
s_b = T_theta(s_a, E_D(d_5day[a:b], C[a:b]), C[a:b], G, delta_t=b-a)
x_hat_b = O_psi(s_b, phi_product)
```

同一 `T_theta` 训练 `Δt∈{5,10,20 days}`；同一变长 `E_D` 分别读取 1/2/4 个 24-D 五日驱动 token。

partition consistency：

```text
s_10_direct = T(s_0, D_1:2, C_1:2, G, 10d)
s_10_comp   = T(T(s_0,D_1,C_1,G,5d),D_2,C_2,G,5d)

P(s) = LayerNorm(s, elementwise_affine=False)
L_part = d(P(s_10_direct), stopgrad(P(s_10_comp)))
       + d(O(s_10_direct), stopgrad(O(s_10_comp)))
```

两个分支还必须各自对真实第 10 日观测监督，防止“一致地错”。`P` 固定为无可学习 affine 参数的 LayerNorm，不使用可学习 projector，从而不让模型通过投影器塌缩伪造一致性。

这个等式是对非自治、受驱动演化的 **control-aware partition/evolution consistency**：长区间分支读取的 `D_1:2/C_1:2` 必须与两个短区间的驱动严格按时间拼接。不将它写成“我们首次提出 semigroup loss”。

### 7.3 训练 curriculum

1. 先训练 5/10/20 日单区间真实 target；
2. 再训练 2/4/8 step open-loop；
3. 稳定后扩到 20 step/100 days；
4. `lambda_part` 从 0 warm up；
5. future pixels 永远不作为 teacher-forcing 输入；
6. 每个可见 target step 监督 RGBN；NDVI 由 Red/NIR 确定性计算；
7. 删除“用未来单帧 latent 当完整 predictive state 真值”的强损失。

### 7.4 三种对照的明确定义

| 模型 | 未来状态关系 | 时间尺度 | partition loss | 身份 |
|---|---|---|---|---|
| matched Direct | 每个 h 从同一 `s0` 独立查询 | endpoint h | 无 | 强基线 |
| shared `T5` rollout | 前一步状态传给下一步 | 固定 5 日 | 无 | 架构对照 |
| ObsWorld main | shared variable-step transition | 5/10/20 日 | 有 | 主方法 |

### 7.5 GreenEarthNet 主任务中的 `phi`

GreenEarthNet 是固定 S2 L2A forecasting，且没有完整 future sun/view angles。future cloud mask 和目标 product metadata 也不能输入。主实验先写 `O(s_future, phi_fixed-S2-L2A)`；只有 L1C/L2A Gate 通过，才加入较窄的 product-conditioned observation head。

---

## 8. AAAI 主实验安排

[AAAI-27 Main Track](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/)限制 7 页正文、总长 9 页，额外页只能放参考文献。正文冻结为四个 artifact。

### Table 1：GreenEarthNet official OOD-t

行：Persistence、Previous Year/Climatology、Contextformer、一个强 recurrent/video baseline、matched Direct-DGH、ObsWorld。列：R²、RMSE、NSE、absolute bias、Outperformance、RMSE25。

Contextformer 的主实验是在未参与训练的 official/OOD split 上比较，不是在训练集上比精度，也不要求换无关数据集做主测试。

### Table 2：机制证据

分成两个紧凑 panel。

**Panel A：两轴 2×2 + rollout 归因。**

| product-axis cross-observation constraint | temporal partition constraint | 身份 |
|---|---|---|
| 无 | 无 | base state + variable-step no-part |
| 有 | 无 | cross-observation state + variable-step no-part |
| 无 | 有 | base state + `L_part` |
| 有 | 有 | full ObsWorld |

另加 matched Direct 和 shared `T5` 两行作架构基线。四个 2×2 模型必须使用同一 Stage2、D/C/G、预算与 evaluator。如果 product-axis constraint 不改善 EarthNet forecast/OOD，它必须降为 mechanism-only 证据，不能与 temporal axis 并列为主贡献。

四格必须从同一 Stage1/1.5 起点开始，保持相同的 product-pair 数据量、更新次数、Stage2 schedule、D/C/G、参数量和前向计算次数；唯一允许的因子是 `lambda_crossobs` 与 `lambda_part` 是否为零。无 cross-observation 行仍读取相同 product batches 并训练 self/alignment 项，无 partition 行仍计算且用真实终点监督 direct/composed 分支，只关闭两分支之间的一致性损失。这样可以排除“数据更多/计算更多/checkpoint 不同”的替代解释。

以越低越好的 long-horizon/OOD loss `L_ij` 记录四格，`i` 表示 product axis，`j` 表示 temporal axis。除两个主效应外，预注册交互对比 `Delta_int = L_11 - L_10 - L_01 + L_00`。只有其聚类 paired 95% CI 上界小于 0 时才写 **synergistic（协同）**；否则只写结构上 **jointly constrained（联合受约束）**。

**Panel B：D/G 驱动证据。** full、no-D、plausible-shuffled D、no-G。wrong-year/lagged D、shuffled-G、D-core、calendar-only 进附录。

### Figure 1：长期退化 + composition gap

左侧为 5–100 日 horizon-wise NDVI error；右侧为同一 variable-step model 的 10/20 日不同 partition observation gap，并同时显示真实 forecast error。增加一个小 inset：跨 checkpoint/model/region 的 control-aware partition gap 与 long-horizon OOD error 的预注册相关性；这个新经验规律比“又用了一个 consistency loss”更能补足查新后的新意。

### Mini Table/Figure 2：严格 `phi` 证据

若 L1C/L2A Gate 通过，报告 `self only / self+cross / full w/o target-product condition / full` 四行，再展示固定 source state 下 correct/wrong target token 可视化；若失败，整块删除并把 decoder 叙述收缩为 fixed S2。

### 附录

OOD-s/OOD-st、original EarthNet Extreme/Seasonal、RGBN 指标、Stage1/1.5 probes、效率、G 置换、`U`、downstream/FM。

### 8.5 若目标就是本轮 AAAI-27：必须采用截稿冲刺版

截至 2026-07-15，[官方日程](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/)是 7 月 21 日摘要截止、7 月 28 日全文截止（UTC-12）。因此不能同时承诺完整 Stage1.5 repair、全量 L1C、全新 Stage2、三种子、下游和 `U`。

本轮截稿的最小闭环只允许：

1. M0 official protocol/evaluator；
2. matched Direct；
3. shared/variable-step transition 与 `L_part`；
4. Table 1、Table 2、Figure 1；
5. `phi` mini-result 只有现成数据和一轮 pilot 已通过时才加入。

建议止损时间：若 7 月 18 日前 M0/M2 smoke test 未通过，或 7 月 22 日前主 transition one-seed 不能稳定优于/接近 Direct，就不要用 `U`、FM 或下游仓促填洞。若“AAAI”只是质量标准而非本轮截稿，则按第 11 节完整路线执行。

---

## 9. 下游任务与“大模型 + ours”

### 9.1 不需要为 AAAI 形式强行做通用下游

Contextformer 的 CVPR accepted version依靠主任务、强基线、消融和 OOD 证据成立，没有靠 EuroSAT 等通用下游支撑。ObsWorld 最有力的证据是 official forecast、long-horizon rollout、partition consistency、D/G intervention 和 observation-role Gate。

### 9.2 核心通过后只选一个窄 downstream

可选 GPP、phenology 或 vegetation anomaly/stress；它只支持 predicted-state utility，不救主结果。

### 9.3 大模型 + ObsWorld 仍有位置

选一个最适配的 CROMA/AnySat/TerraMind initializer，保持相同 `I/T/O`：比较我们的 Stage1/1.5 encoder 与 FM encoder。它回答 ObsWorld transition 是否兼容强观测编码器，不回答核心动力学是否成立；只放附录，不做大规模 2×2。

---

## 10. 现有代码与目标方案的差距

| 现状 | 审计结论 | 后续方向 |
|---|---|---|
| config 写 `dataset: earthnet2021x`，root 名叫 EarthNet2021 | 实际已走 GreenEarthNet 格式，只是目录名误导 | 明确 release/protocol，不必重选数据 |
| current Stage2 复制同一 `z_context` 到每个 horizon | Direct，不是 rollout | 保留为 matched Direct；新增 transition |
| 9 维累计 weather | 不适合逐步动态 | 主实验用官方 24-D/5-day E-OBS + 共享变长 interval encoder；raw daily 仅附录 |
| neutral `phi`，decoder 不接 `phi` | 不支持 controllable renderer | fixed S2 主任务；product Gate 后再扩 |
| Stage1.5 self-reconstruct + alignment | 已训练，但无 cross-decoding | 先验收 60k，再轻量 repair |
| train holdout by tile | 不等于 official protocol | official manifest + locked OOD-t |
| legacy ENS/NPZ evaluator | 不等于 Green evaluator | 官方 NetCDF + 六项指标 |
| mask 主要依赖 `s2_mask` | 与 official eligibility 不同 | context/train/eval masks 分开 |
| future single-frame latent target | 不代表完整 predictive state | observation supervision + within-model partition consistency |

这些均属 Stage2 以后允许修改的范围，不否定已完成的 Stage1/1.5。

---

## 11. 后续执行顺序

1. **M0 protocol/data/phi audit**：manifest、evaluator、mask、官方 24-D E-OBS、L1C/L2A pair、公开 baseline parity。
2. **M1 Stage1.5 60k 验收**：geographic holdout、future utility、matched Stage2 skill；决定原 checkpoint、轻量 repair 或退回 Stage1。
3. **M2 matched Direct**：raw D path、20 targets、official export/eval、small-overfit、one-seed Val。
4. **M3 shared `T5` rollout**：1/2/4/8/20 step curriculum；先过 non-collapse 和 true-D > shuffled-D。
5. **M4 variable-step + partition consistency**：`Δt={5,10,20}`，真实 error 不得因降 composition gap 而恶化。
6. **M5 freeze + three seeds + clustered paired CI + locked OOD-t**：删除无效组件，在看到 ObsWorld OOD 结果前根据公开基线波动/业务容差冻结 non-inferiority margin；自有方法必须既跑三种子，又报告以 tile/location 为重采样单位的 paired 95% CI。测试集只正式评一次。
7. **M6 secondary evidence**：OOD-s/st、original Extreme/Seasonal、product phi、downstream 或 FM 二选一、最后才是 `U`。

---

## 12. 硬门槛

| 如果发生 | 处理 |
|---|---|
| Stage1.5/cross-observation 不提升 Stage2 forecast 或 OOD | 主模型用 Stage1/base state；product axis 降为 mechanism-only，不再声称两轴协同 |
| correct `phi` 不优于 shuffled | 删除 product renderer；fixed S2 decoder |
| rollout 明显弱于 Direct | 停止强 compositional world-model claim |
| `L_part` 降 gap 却升真实 error | 删除 `L_part` |
| true D 与 plausible-shuffled D 等价 | 删除 driver-aligned 强调 |
| no-G 与 full G 等价 | 删除 G，不为缩写硬留 |
| `U`、下游或 FM 失败 | 不影响已经成立的 Stage2 主线 |

---

## 13. 最终定位

> **ObsWorld does not directly extrapolate observation-conditioned pixels. It learns role-separated predictive states and a DGH-controlled, variable-step transition whose forecasts remain consistent across temporal partitions, while an observation model maps the evolved state back to verifiable satellite products.**

中文：

> **ObsWorld 不直接外推混合了观测条件的像素，而是学习按角色分工的预测状态，并用受 DGH 控制、支持不同时间步长且具有时间分区一致性的状态转移推演未来，最后通过观测模型回到可由真实卫星产品核验的空间。**

这比“稀疏观测 + 一个 U 校正模块”更接近初版世界模型，也比“天气、DEM、horizon 三个字段拼接”更像能支撑 AAAI 的方法贡献。

---

## 14. 本轮产物与依据

- [方法定稿候选](../refine-logs/run-20260715-earthnet-dgh/FINAL_PROPOSAL.md)
- [Claim-driven 实验计划](../refine-logs/run-20260715-earthnet-dgh/EXPERIMENT_PLAN.md)
- [实验追踪表](../refine-logs/run-20260715-earthnet-dgh/EXPERIMENT_TRACKER.md)
- [独立复审与修改记录：Round 2](../refine-logs/run-20260715-earthnet-dgh/REVIEW_ROUND2.md)
- [独立复审与修改记录：Round 3](../refine-logs/run-20260715-earthnet-dgh/REVIEW_ROUND3.md)
- [最终独立复核：Round 4](../refine-logs/run-20260715-earthnet-dgh/REVIEW_ROUND4.md)
- [最接近方法查新与安全贡献边界](../refine-logs/run-20260715-earthnet-dgh/NOVELTY_CHECK.md)

主要外部依据：

- [EarthNet2021 paper](https://arxiv.org/abs/2104.10066)
- [GreenEarthNet / Contextformer CVPR 2024 paper](https://openaccess.thecvf.com/content/CVPR2024/papers/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.pdf)
- [GreenEarthNet official repository and evaluator](https://github.com/vitusbenson/greenearthnet)
- [SSL4EO-S12 v1.1 official dataset card](https://huggingface.co/datasets/embed2scale/SSL4EO-S12-v1.1)
- [CROMA, NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/file/11822e84689e631615199db3b75cd0e4-Paper-Conference.pdf)
- [EO-WM arXiv v1](https://arxiv.org/abs/2606.27277)
- [AAAI-27 Main Technical Track Call](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/)
