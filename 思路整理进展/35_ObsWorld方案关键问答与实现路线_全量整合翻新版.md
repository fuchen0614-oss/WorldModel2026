# 35 ObsWorld 方案关键问答与实现路线（全量整合翻新版）

> 文件定位：这是新 07 的配套问答文档。它把 `output` 01-33 中出现过的关键困惑统一回答，重点解决：我们到底创新在哪里、Stage2 怎么训、主实验是什么、为什么小模型仍有价值、EO-WM 和大模型怎么放、D/G/h/uncertainty/下游实验如何共同支撑 AAAI 叙事。

---

## A. 总体定位

### Q0：先看哪些英文术语？

后续文档会保留部分英文，是为了和代码、论文表格、已有文献对齐；但理解时可以先按下面的中文意思读。

| 英文 | 中文 | 快速理解 |
| --- | --- | --- |
| Observation | 观测影像 | 卫星真正拍到的像素图 |
| State / latent state | 状态 / 潜在状态 | 模型内部估计的地表状态，不等同于原始像素 |
| Imaging condition / phi | 成像条件 | 太阳角、云、季节、传感器等影响观测外观的因素 |
| Dynamics | 动力学 | 状态如何随时间和条件变化 |
| State transition | 状态转移 | `z_t` 怎么变成 `z_{t+h}` |
| External driver / D | 外生驱动 | 降水、温度、VPD、辐射、day_of_year 等推动地表变化的条件 |
| Geographic prior / G | 地理先验 | 海拔等稳定地理背景 |
| Horizon / h | 预测跨度 | 预测未来多少天 |
| Decoder | 解码器 | 把未来状态还原成可评估的未来影像 |
| Weather-response | 天气响应诊断 | 改变天气条件，看模型预测是否合理变化 |
| Uncertainty | 不确定性 | 模型认为哪里更难预测 |
| Downstream / Transfer | 下游 / 迁移 | 检查学到的状态能否用于其他任务 |

一个最短理解方式：

```text
Observation 是看到的图；
State 是模型认为地表真实处在什么状态；
D/G/h 是状态怎么往未来变的条件；
Decoder 是把未来状态重新变回图，方便用标准指标验证。
```

### Q1：ObsWorld 最终到底是什么？

ObsWorld 是一个 **面向遥感观测的陆表状态动力学世界模型**。

它不是简单的未来帧预测器，也不是 EarthNet2021 榜单专用模型。它的核心是学习：

```text
z_t + D_{t:t+h} + G + h -> z_{t+h}
```

其中 `z_t` 是当前陆表状态，`D` 是外生驱动，`G` 是地理先验，`h` 是预测跨度。未来影像预测只是把 `z_{t+h}` 解码回观测空间，用于标准评估。

### Q2：为什么不能直接说“我们做遥感未来预测”？

可以做预测，但不能只讲预测。只讲预测会让论文进入别人的单一赛道：谁的 ENS 更高、谁的像素更像。

我们的更强叙事是：

1. 遥感观测混合了地表状态和成像条件。
2. 世界模型应建模地表状态如何演化。
3. 演化应受天气、地理和时间跨度影响。
4. 标准预测任务只是检验这个动力学是否可观测。

### Q3：Dynamics 是什么意思？

这里的 dynamics 不等于必须写出严格物理方程。它指的是：

> 状态随时间和外部条件变化的规律。

在本文中就是：

```text
当前状态 z_t 在未来天气 D、地理背景 G 和时间跨度 h 条件下，
如何变成未来状态 z_{t+h}。
```

### Q4：State transition 是什么意思？

State transition 是“状态转移”。例如：

```text
现在是一块农田的状态 z_t；
未来 30 天降水充足、VPD 较低、辐射合适；
模型预测它 30 天后的状态 z_{t+30}。
```

这就是一次状态转移。

### Q5：为什么像素预测仍然保留？

因为遥感状态本身通常没有直接标签。我们必须把预测状态解码回影像或 NDVI，才能用 EarthNet 等标准指标评估。

所以像素预测的位置是：

```text
状态动力学的观测接口，而不是论文唯一目标。
```

### Q6：这是否仍然可以叫 world model？

可以，但必须讲得克制。

本文的 world model 不是“通用地球模拟器”，而是：

> 一个在遥感观测中学习陆表状态转移的条件世界模型。

它具备 world model 的关键要素。这里先给英文，再给中文：

- internal state：内部状态，即 `z_t`
- action/driver-like condition：类似“动作/驱动”的条件，即 `D`
- context：上下文或背景，即 `G`
- temporal transition：时间转移，对应 `h`
- rollout / prediction：向未来推演或预测，即 `z_t -> z_{t+h}`
- observation decoder：观测解码器，即 `z_{t+h} -> x_{t+h}`

### Q7：我们的核心观点是什么？

核心观点：

> Future EO forecasting should not only be evaluated as future-pixel reconstruction, but also as driver-conditioned land-surface state transition modeling.

中文：

> 遥感未来预测不应只被看成未来像素重建，更应被看成外生驱动条件下的陆表状态转移建模。

---

## B. 创新点与 pretrain-finetune

### Q8：Stage1 用 SSL4EO，Stage2 用 EarthNet，这是不是没有新意？

pretrain-finetune 范式本身没有新意，这是正常的。AAAI/CVPR 很多工作也使用预训练再微调的训练范式。

但本文创新不在“用了预训练”，而在预训练之后做了什么：

1. 把遥感表征拆成成像条件和状态表示。
2. 在状态空间中学习 D/G/h 条件转移。
3. 用 weather-response、DGH 消融和不确定性诊断验证机制。

因此，pretrain-finetune 是训练手段，不是贡献点。

### Q9：创新点具体写在哪里？

建议写成三点：

1. **新问题定义**：把 EO world model 定义为 land-surface state dynamics from imaging-conditioned observations，即“从带成像条件的遥感观测中学习地表状态动力学”，而非纯像素预测。
2. **新方法结构**：observation encoder（观测编码器）+ phi 条件建模 + D/G/h-conditioned dynamics（D/G/h 条件状态动力学）+ observation decoder（观测解码器）。
3. **新评估闭环**：标准预测 + DGH 消融 + weather-response + uncertainty/G consistency + downstream transfer。

### Q10：如果别人问“你不就是一个条件预测模型吗”怎么办？

回答重点：

- 是的，预测是观测协议；但我们不是只做条件像素预测。
- 我们显式区分 observation（观测影像）、state（状态）、imaging condition（成像条件）、external driver（外生驱动）、geographic prior（地理先验）和 horizon（预测跨度）。
- 我们用 DGH 消融和 response 诊断证明条件变量影响状态转移。

如果实验中 D/G/h 都有效，这个质疑可以被缓解。

### Q11：Stage1.5 的创新是否足够？

Stage1.5 不是单独撑起论文的创新，而是 ObsWorld 的必要组成：

- 它减少状态中成像因素泄漏。
- 它让后续 dynamics 更像状态转移，而不是外观转移。
- 它提供“状态表示不应依赖成像捷径”的实验证据。

但不能夸大成“彻底解耦”。

### Q12：Stage1.5 30k vs 60k 结果怎么写？

采用 60k 进入 Stage2。原因：

- 60k alignment loss 更好。
- 跨模态一致性更适合后续动力学。

但要写清楚：

- 线性 leakage 有下降。
- 非线性 probe 仍可能识别部分 phi。
- 因此只能说减少泄漏、改善一致性，不能说完全消除。

---

## C. Stage2 数据选择

### Q13：Stage2 到底用一个数据集还是两个？

第一主线用一个：EarthNet2021。

更准确地说：

- 主实验模型：`ObsWorld-E`，Stage2 EarthNet-only。
- 扩展模型：`ObsWorld-G`，EarthNet+SSL4EO 或其他数据联合训练，放附录/泛化实验。

### Q14：为什么不直接 Stage2 多数据集联合训练？

因为第一张主表需要公平。

如果我们用 EarthNet+SSL4EO 联合训练去和 EarthNet-only 方法比：

- 赢了，别人可能说数据更多。
- 输了，我们难解释是模型弱还是多数据负迁移。
- 叙事会从“机制模型”变成“训练数据策略”。

所以主线先 EarthNet-only，最干净。

### Q15：Stage1 用 SSL4EO，Stage2 用 EarthNet，算多数据集吗？

算外部预训练，但这属于标准 pretrain-finetune。

论文中要明确写：

| 阶段 | 数据 | 作用 |
| --- | --- | --- |
| Stage1/1.5 | SSL4EO | 表征预训练与成像条件建模 |
| Stage2/3 | EarthNet2021 | 主任务动力学训练与预测评估 |

这不会让主实验天然不公平，只要表格中标注 external pretrain，并做 Stage1/1.5 消融。

### Q16：EarthNet-only 会不会限制我们的世界模型叙事？

不会。主实验用 EarthNet，是因为它提供标准观测协议和未来序列。

世界模型叙事由以下实验支撑：

- EarthNet 标准预测：能预测。
- DGH 消融：条件变量有效。
- Weather-response：响应外部驱动。
- Uncertainty/G：可信且受地理背景调节。
- Downstream：状态表示可迁移。

不是靠“训练很多数据集”来支撑。

### Q17：EarthNet+SSL4EO 联合训练还有必要吗？

有价值，但不是 P0。

它适合放在：

- 附录泛化实验。
- held-out climate/region 诊断。
- 资源允许时的 ObsWorld-G。

如果时间紧，可以先不做。

---

## D. D/G/h 变量

### Q18：D 最终包括什么？

最终 D：

```text
day_of_year
precipitation
temperature
VPD
solar_radiation
```

这五个字段足够支撑天气和物候驱动。

### Q19：为什么 `ndvi_previous` 不能放进 D？

因为 NDVI 是状态量，不是外生驱动。

它可以作为：

- 从 `x_t` 或 `z_t` 派生的状态反馈。
- 辅助监督目标。
- baseline 输入。

但不应叫 external driver。

### Q20：为什么 `sun_elevation` 不放进 D？

太阳高度角主要影响观测影像的光照、阴影和辐射外观，是成像条件 phi。

它对地表过程当然也可能有间接关系，但在本文变量边界中应归 phi，避免和 D 混淆。

### Q21：season 怎么处理？

拆开：

- phi 中可以保留 `season`，帮助描述观测外观和时间片。
- D 中不用离散 `season`，改用 `day_of_year` 的 sin/cos 周期编码。

原因：

- 南北半球 season 编码容易混淆。
- 离散 season 同时在 phi 和 D 会让审稿人质疑变量作用不清。

### Q22：G 最终包括什么？

首版只用：

```text
elevation
```

这不是太弱，而是更干净：

- 稳定。
- 易获取。
- 与气候、植被、水文响应有关。
- 不会引入过多 DEM 派生噪声。

### Q23：只有一个 G 字段，审稿人会认吗？

可以，关键是实验设计。

如果 elevation 分层后：

- no-G 在某些海拔段误差更大；
- full model 在高海拔/低海拔响应曲线更合理；
- G perturbation 会改变预测；

那么 G 的作用就成立。

不要把 G 写成“强物理定律”，而应写成“地理背景条件”。

### Q24：h 是否需要优化？

需要认真设置，但不需要把 h 当成单独大调参。

推荐：

- 完整：`{5,10,15,...,100}`
- 轻量：`{5,10,20,30,60,100}`

不建议只设一个 h。

### Q25：h 的设置会影响下游任务吗？

通常不会直接影响下游数据集本身，但会影响学到的 dynamics state。

如果 h 设计太窄：

- 模型只学某一个跨度。
- 长短期变化区分不足。
- DHR 和 long-horizon 分析变弱。

因此 Stage2 训练时应做 h-conditioned dynamics。下游使用的是 encoder/state，通常不需要下游也有 h。

### Q26：旧文档里的 `{10,20,30,60}` 怎么办？

作为历史备选或轻量 ablation 保留，不作为最终主线。

EarthNet 的时间协议更自然地支持 5-day lead-time，所以最终应按 EarthNet lead-time 来写。

---

## E. 未来天气与泄露

### Q27：未来 ERA5 到底是不是泄露？

不能一概而论。

分两种协议：

| 协议 | 能否用未来真实天气/reanalysis | 解释 |
| --- | --- | --- |
| Scenario/oracle forcing | 可以 | 给定未来天气情景，研究地表响应 |
| Deployment forecasting | 不可以 | 真实未来不可知，必须用 forecast/climatology |

### Q28：我们的主线应该采用哪种协议？

主线建议采用 scenario-conditioned forecasting。

原因：

- 它最符合 DGH 和 world model 叙事。
- 我们关心模型是否理解给定驱动下的状态响应。
- Weather-response 诊断天然需要改变未来 D。

但论文中要诚实说明：真实部署预测需要替换为天气预报或气候平均。

### Q29：什么才是真正不可接受的泄露？

不可接受：

- 把未来观测影像直接作为输入。
- 把未来 NDVI/标签作为 D。
- 训练/测试区域在空间上泄露，导致相邻 patch 共享过强。
- 用测试集统计量归一化训练。

scenario forcing 下使用未来天气作为条件，不等于这些泄露。

---

## F. 主实验与论文叙事

### Q30：主实验究竟是什么？

主实验是：

> EarthNet2021 标准预测协议下的条件状态动力学验证。

它用标准预测指标证明模型具备基本预测能力，再用机制实验说明为什么它不是普通预测模型。

### Q31：第一张表应该是什么？

第一张表应是 EarthNet 标准预测对比：

| Method | Type | Params | External pretrain | ENS↑ | MAD/MAE↓ | OLS↑ | EMD↑ | SSIM↑ | NDVI-MAE↓ | DHR↑ |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |

注意：

- `ENS↑`，不是 `ENS↓`。
- 标注参数量。
- 标注 external pretrain。
- 不只报一个指标。

### Q32：为什么主实验不是下游任务？

因为本文核心是状态动力学。下游任务只能证明 state representation 可迁移，不能直接证明动态预测能力。

因此：

- 主实验：EarthNet 标准预测。
- 核心机制实验：DGH + weather-response。
- 下游实验：辅助证明状态表示价值。

### Q33：为什么预测实验能支撑世界模型叙事？

预测是检验动力学最标准的观测协议。

如果模型声称学到了状态转移，却无法预测未来观测，那叙事不成立。

但预测本身不够，所以还要加：

- DGH 消融。
- Weather-response。
- h 多跨度。
- uncertainty/error。
- downstream transfer。

### Q34：我们的实验逻辑怎么串起来？

完整逻辑：

```text
Table 1: 能预测吗？
Table 2: 靠 D/G/h 条件转移预测吗？
Table 3: 改变天气驱动会改变未来状态吗？
Table 4: 模型知道哪里难、是否受地理背景调节吗？
Table 5: 状态表示能迁移吗？
```

这五个问题共同支撑 AAAI 叙事。

### Q35：什么结果可以支撑论文？

可支撑：

- 标准预测至少接近主流 baseline。
- D 或 h 消融有明显收益。
- Weather-response 有清楚趋势。
- uncertainty 与误差正相关。
- CropHarvest 等状态相关下游任务优于 Stage1-only 或有小样本优势。

### Q36：什么结果会让叙事危险？

危险：

- 输给 persistence/climatology。
- D/G/h 消融无差异。
- 改变 D 输出不变。
- h 不影响输出。
- uncertainty 是随机噪声。
- Stage2 让下游表示大幅退化。

---

## G. EO-WM、大模型与公平性

### Q37：我们是不是太看重 EO-WM？

EO-WM 重要，但不能成为唯一中心。

它应作为：

- 标准预测强基线之一。
- 大模型路线代表。
- discussion 中的对照对象。

但本文主线不是“打败 EO-WM”，而是提出结构化 D/G/h 状态动力学框架。

### Q38：EO-WM 参数大很多，怎么比？

不要假装公平。

表格中明确写：

- Params。
- External pretrain。
- Training data。
- Type。

然后解释：

- EO-WM 可能在视觉生成或 ENS 上更强。
- ObsWorld 关注显式驱动响应、地理调节、多跨度状态转移和机制诊断。

### Q39：如果比不过 EO-WM 会不会被拒？

不一定。

如果我们只是写“我们是更强预测模型”，那会危险。

如果我们写：

> 我们提出一种结构化状态动力学世界模型，并通过 DGH/response/uncertainty/downstream 验证它学习了不同于纯像素预测的能力。

那么即使 ENS 不是第一，仍有学术贡献空间。

### Q40：SkySense/Prithvi/Galileo 放哪里？

放在：

- Related Work。
- Downstream / Transfer 表。
- 可选 foundation model 对比。

不建议放在 EarthNet 标准预测主表，除非我们真的实现了同协议预测。

### Q41：“大模型 + ours”需要做吗？

不是主线必要条件。

它可以作为 optional plugin：

```text
大 foundation encoder 提取 z_t
ObsWorld dynamics head 接 D/G/h
比较 foundation-only vs foundation+ObsWorld dynamics
```

但如果时间紧，应删除或放附录，不要让它干扰主线。

### Q42：终版模型到底是 ours 还是 ours+大模型？

终版主模型是：

```text
ObsWorld-S / ObsWorld-E
```

即我们自己的观测条件感知状态动力学模型。

“大模型 + ours”只是证明模块可插拔，不是终版定义。

---

## H. 小参数与信心

### Q43：只有二三千万参数，够 AAAI 吗？

参数小不是致命问题。

前提是：

- 标准预测不弱到不可接受。
- 机制实验强。
- 表格中诚实标注参数。
- 叙事强调结构化动力学，而不是 brute-force 大模型能力。

### Q44：小模型的优势怎么写？

可以写：

- 更轻量。
- 更容易做机制诊断。
- 显式 D/G/h 条件化。
- 不确定性和 response 更透明。

不要写：

- 小模型全面击败所有大模型。

### Q45：是否必须训练 ObsWorld-M？

不是必须，但资源允许建议做。

优先级：

1. 先把 ObsWorld-S 的 Stage2 和机制实验做完整。
2. 如果标准预测差距较大，再考虑 ObsWorld-M。
3. 不要为了追参数规模而牺牲机制实验。

---

## I. 下游任务

### Q46：下游任务为什么重要？

下游任务证明：

> 学到的 `z` 不是 EarthNet 专用预测中间变量，而是有一定地表状态语义。

但下游不是主实验。

### Q47：最推荐的下游是什么？

P0：CropHarvest。

原因：

- 与植被、农业、物候、天气响应相关。
- 更贴近 EarthNet 的植被动态叙事。
- 可以检验状态表示是否对作物类别/农业状态有用。

### Q48：Sen1Floods11 要不要做？

作为 P1。

它能体现跨任务和灾害响应，但与 EarthNet 植被动态距离更远，实现上也可能涉及 SAR/光学差异。

如果时间紧：

- 主文做 CropHarvest。
- Sen1Floods11 放附录或备选。

### Q49：下游怎么训练？

建议：

1. 冻结 ObsWorld encoder/state，训练 linear head。
2. 轻量 fine-tune 或 adapter。
3. 对比 Stage1-only、Stage1.5、Stage2 full。

核心比较不是“我们一定赢所有 foundation model”，而是：

```text
Stage2 dynamics 是否让状态表示更适合地表状态相关任务？
```

### Q50：下游表怎么放大模型？

如果能运行：

| Model | Pretrain | Params | Protocol | CropHarvest | Sen1Floods11 |
| --- | --- | ---: | --- | ---: | ---: |
| SSL4EO baseline | SSL4EO |  | frozen |  |  |
| Prithvi | large EO FM |  | frozen |  |  |
| SkySense | large EO FM |  | frozen |  |  |
| Galileo | large EO FM |  | frozen |  |  |
| ObsWorld-S | ours |  | frozen |  |  |

如果不能运行，不要编造结果；相关工作里讨论即可。

---

## J. 不确定性

### Q51：不确定性是否重要？

重要，但不是第一贡献。它的作用是增强世界模型可信度。

它回答：

> 模型是否知道哪些未来不可确定？

### Q52：Uncertainty-error correlation 是什么？

中文就是“不确定性和误差的相关性”。

如果模型预测某个区域很不确定，而这个区域真实误差也大，说明不确定性有意义。

### Q53：怎么做不确定性？

轻量方案：

- dynamics head 输出 `mu` 和 `logvar`。
- 用 heteroscedastic Gaussian loss。
- 评估 predicted variance 与 absolute error 的 Pearson/Spearman correlation。

备选：

- dropout 多次前向。
- 小 ensemble。

### Q54：不确定性可视化怎么画？

三列：

```text
prediction error map | uncertainty map | overlap / calibration bins
```

如果高误差区域和高不确定性区域重合，就是好证据。

---

## K. 地理先验 G

### Q55：地理先验一致性约束是什么意思？

不要把它理解成强行加入物理定律。

它更像：

> 给模型一个稳定地理背景，让模型知道不同海拔/地形区域对同样天气驱动可能有不同响应。

### Q56：G consistency 实验有什么意义？

它证明 G 不是装饰字段。

例如：

- 高海拔地区植被响应较慢。
- 低海拔地区降水响应更明显。
- no-G 模型在某些 elevation bin 中误差更大。

### Q57：别的前沿文章也会做这种附属实验吗？

很多机制型、物理启发型、可解释模型都会做类似分析：

- 按区域/气候/地形分层评估。
- 做条件变量消融。
- 做 response curve 或 counterfactual sweep。

本文不需要声称“这是物理定律证明”，而是说它验证模型是否使用地理背景。

---

## L. 可视化

### Q58：可视化结果应该对应哪些实验？

至少四类：

1. 标准预测可视化。
2. Weather-response 可视化。
3. Uncertainty-error 可视化。
4. G/h 分层或响应可视化。

### Q59：标准预测图怎么画？

推荐：

```text
Input context | Ground truth future | ObsWorld prediction | baseline prediction | error map | NDVI curve
```

不要只放 RGB，要放 NDVI 或 error。

### Q60：Weather-response 图怎么画？

固定同一个 `z_t, G, h`，展示：

```text
low precipitation / normal / high precipitation
high VPD / normal / low VPD
```

看预测 NDVI 或状态图如何变化。

### Q61：h 可视化怎么画？

固定 `z_t,D,G`，展示不同 h：

```text
h=5, 10, 20, 30, 60, 100
```

画 NDVI 曲线或未来状态变化。如果模型真的使用 h，输出应随时间跨度有合理变化。

---

## M. 具体实验安排

### Q62：AAAI 主文最合理的实验顺序是什么？

推荐顺序：

1. EarthNet 标准预测。
2. DGH / Stage1.5 消融。
3. Weather-response 诊断。
4. Uncertainty + G consistency。
5. Downstream / Transfer。

### Q63：如果篇幅不够，哪些必须保留？

必须保留：

- 标准预测。
- DGH 消融。
- Weather-response。

尽量保留：

- uncertainty-error correlation。
- CropHarvest 下游。

可放附录：

- ObsWorld-G 联合训练。
- 更多 G 字段。
- 更多大模型下游对比。

### Q64：消融最小集合是什么？

最小集合：

| Config | 目的 |
| --- | --- |
| full | 主模型 |
| no-D | 验证外生驱动 |
| no-G | 验证地理背景 |
| single-h / no-h | 验证多跨度 |
| no-Stage1.5 | 验证成像条件建模 |
| Stage1-only | 验证 dynamics 训练价值 |

### Q65：Weather-response 最小集合是什么？

最小集合：

1. precipitation sweep。
2. VPD sweep。
3. drought/extreme subset。

如果时间更紧，优先 precipitation + VPD。

### Q66：第一张表是否需要 ours+其他基础模型机制？

不需要。

第一张表应展示 `ObsWorld-S` 主模型与标准预测 baseline 的比较。

`foundation model + ObsWorld dynamics` 可以作为附录或 Table 5 的扩展，不应抢主线。

---

## N. 实现路线

### Q67：下一步最急的代码任务是什么？

P0：

1. EarthNet2021 loader。
2. 样本构造：`x_t, x_{t+h}, D, G, h, phi`。
3. h embedding。
4. D/G encoder。
5. state dynamics module 接真实 D/G/h。
6. EarthNet 指标脚本，确认 `ENS↑`。
7. DGH ablation switch。

### Q68：Stage2 loader 应该输出什么？

建议 batch：

```python
batch = {
    "x_t": ...,              # current observation
    "x_future": ...,         # target future observation(s)
    "phi_t": ...,            # current imaging condition
    "phi_future": ...,       # target/future observation condition if available
    "D": ...,                # external drivers over t:t+h
    "G": ...,                # elevation
    "h": ...,                # lead time in days or index
    "mask": ...,             # valid/cloud/evaluation mask
    "meta": ...              # region/time metadata
}
```

### Q69：D 是一个时间点还是一个序列？

最好是 `t:t+h` 的聚合或序列。

轻量首版可以做统计聚合：

- mean precipitation
- cumulative precipitation
- mean temperature
- mean VPD
- mean radiation
- day_of_year target encoding

更完整版本可用 temporal driver encoder。

### Q70：h 怎么输入模型？

建议：

- 数值归一化 `h / 100`。
- 再用 MLP 或 sinusoidal embedding。
- 与 D/G embedding 融合后送入 dynamics block。

### Q71：G 怎么输入模型？

首版：

- elevation map resize 到 state spatial resolution。
- elevation 归一化。
- 通过小 CNN/MLP 投到和 state token 对齐的 embedding。

如果 state 是 global token，也可先对 elevation 做 patch pooling。

### Q72：Dynamics module 第一版用什么结构？

建议保守：

- residual MLP / transformer block over state tokens。
- condition modulation from D/G/h。
- 输出 `delta_z`，即 `z_{t+h}=z_t+delta_z`。

这样比从零生成 state 更稳。

### Q73：是否需要 rollout 多步？

首版不必做自回归 rollout 主线。

推荐 direct multi-horizon prediction：

```text
z_t + D + G + h -> z_{t+h}
```

这样减少累积误差，也符合多 h 条件化。

### Q74：Stage2 损失怎么设计？

建议：

1. observation reconstruction / prediction loss。
2. NDVI auxiliary loss。
3. state consistency loss，可选。
4. uncertainty NLL，可选。
5. masking loss，只在有效像素/区域评估。

不要一开始堆太多损失，先保证主预测和 DGH 消融跑通。

---

## O. 结果解读模板

### Q75：如果 ENS 不是第一，怎么写？

可以写：

> ObsWorld is not optimized solely for high-fidelity pixel synthesis. Although large generative EO models achieve stronger visual reconstruction, ObsWorld provides explicit driver-conditioned state transitions, leading to better response diagnostics and competitive long-horizon vegetation dynamics.

中文逻辑：

- 承认像素不是第一。
- 强调机制指标。
- 强调参数量差异。
- 不硬说全面更强。

### Q76：如果 D 有效但 G 不明显，怎么办？

可以接受。

写法：

- D 是主驱动，G 是背景调节。
- elevation 单字段的整体提升可能小。
- 分层或极端区域中若有差异，就足以作为辅助证据。

如果 G 完全无效，则把 G 降级为探索性分析，不要强行作为核心贡献。

### Q77：如果 Stage1.5 对预测指标帮助不大，怎么办？

看 leakage 和 response。

如果 Stage1.5：

- 降低 phi leakage；
- 改善 cross-modal consistency；
- 让 response 更稳定；

则仍有价值。

不要只用 ENS 判断 Stage1.5。

### Q78：如果下游任务一般，怎么办？

下游是辅助，不是主线。

如果 CropHarvest 不明显：

- 可以报告为附录。
- 强调主线仍由 prediction + DGH + response 支撑。
- 检查 Stage2 是否过拟合 EarthNet。

### Q79：什么情况下应暂缓投稿？

如果出现以下组合：

- 标准预测弱于 naive。
- DGH 无增益。
- response 无变化。
- 不确定性无意义。

这说明 world model 叙事暂时没有实验支撑，应先修 Stage2。

---

## P. 写作模板

### Q80：Abstract 可以怎么组织？

结构：

1. 现有 EO 模型擅长表征/预测，但常混淆成像外观和地表状态。
2. 提出 ObsWorld，学习观测条件下的状态动力学。
3. 方法：`z_t, D, G, h -> z_{t+h}`。
4. 实验：EarthNet 标准预测 + DGH + response + downstream。
5. 结论：显式驱动条件状态转移提供更可解释的 EO world modeling。

### Q81：Introduction 末段怎么写？

可以写：

> In this work, we introduce ObsWorld, an Earth-observation world model for land-surface state dynamics. ObsWorld estimates latent land-surface states from imaging-conditioned observations and learns state transitions conditioned on meteorological drivers, geographic priors, and prediction horizons. We evaluate it not only through standard EarthNet forecasting metrics, but also through driver ablations, weather-response diagnostics, uncertainty-error correlation, and downstream transfer.

### Q82：Contribution 怎么写？

三点：

1. We formulate EO world modeling as land-surface state transition learning from imaging-conditioned observations.
2. We propose ObsWorld, a D/G/h-conditioned state dynamics framework with observation decoding.
3. We design an evaluation protocol combining standard forecasting, mechanism ablations, response diagnostics, uncertainty analysis, and transfer evaluation.

### Q83：哪些话不要写？

不要写：

- 我们首次使用 SSL4EO pretrain-finetune。
- 我们完全解决遥感世界模型。
- 我们完全去除了成像因素。
- 我们全面超过所有大模型。
- 未来 ERA5 一定是泄露。
- ENS 越低越好。

---

## Q. 最终执行优先级

### Q84：时间紧急时先做什么？

优先级：

1. EarthNet loader + D/G/h 字段。
2. Stage2 dynamics full model。
3. EarthNet 标准指标。
4. no-D / no-h / no-Stage1.5 消融。
5. Weather-response sweep。
6. 预测可视化。
7. uncertainty 或 CropHarvest 二选一先做。
8. 再补 G consistency 和更多下游。

### Q85：什么是最小可投稿闭环？

最小闭环：

```text
ObsWorld-S
EarthNet standard prediction
D/G/h ablation
Weather-response diagnostic
Stage1.5 leakage/alignment evidence
Prediction + response visualization
```

如果这套结果扎实，就可以写出 AAAI 主线。

### Q86：什么是理想完整闭环？

完整闭环：

```text
ObsWorld-S + optional ObsWorld-M
EarthNet standard prediction
D/G/h/Stage1.5 ablation
Weather-response
Uncertainty-error correlation
G elevation strata
CropHarvest downstream
Optional ObsWorld-G generalization
```

---

## R. 最终信心判断

### Q87：现在这条路线是否值得继续？

值得，但前提是执行时不再摇摆。

最终路线应固定：

```text
观测条件感知的状态表示
        +
D/G/h 条件状态动力学
        +
EarthNet 标准预测观测协议
        +
机制诊断和迁移验证
```

这条线比“单纯预测精度竞赛”更有 AAAI 叙事空间。

### Q88：最应该警惕什么？

三件事：

1. 把论文重新写成 EarthNet 榜单竞争。
2. 把变量堆太多，导致 D/G/h 解释不清。
3. 机制实验没做完，只剩标准预测表。

### Q89：最终一句话怎么给自己定心？

> 我们不是用小模型硬刚大模型的像素生成能力，而是在一个标准预测平台上证明：从遥感观测中估计的地表状态可以被外生驱动、地理背景和时间跨度条件化地建模与诊断。

这就是 ObsWorld 最稳的 AAAI 主线。
