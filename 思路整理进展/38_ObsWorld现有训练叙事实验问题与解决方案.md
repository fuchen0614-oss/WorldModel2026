# 38 ObsWorld 现有训练叙事、实验问题与解决方案

> 文档定位：本文用于统一说明 ObsWorld 当前训练方案、实验与论文主线之间的证明关系，审查其中仍未解决的问题，并给出在公开数据条件下可执行的修正方案。  
> 使用原则：后续训练、消融、评估和论文写作应围绕本文的“最小 AAAI 证明闭环”组织，避免重新退回单纯 EarthNet2021 像素预测，也避免在尚无证据时使用“完全解耦”“真实因果”“通用地球模拟器”等过强表述。  
> 术语原则：重要英文术语均附中文释义；后文在含义明确后可使用缩写。

---

## 0. 总体结论

### 0.1 对现有方案的总判断

ObsWorld 当前并不是一个应当被推翻重做的方案。现有代码和训练路线已经建立了如下基本骨架：

```text
多模态遥感观测
    -> 状态表示学习
    -> 历史状态聚合
    -> D/G/h 条件状态动力学
    -> 未来潜状态
    -> 未来遥感观测
```

其中：

- `Observation（观测）`：卫星实际获得的像素影像；
- `Latent state（潜在状态）`：模型内部估计的陆表状态表示；
- `D / External drivers（外生驱动）`：降水、温度、VPD、辐射等天气驱动；
- `G / Geographic context（地理背景）`：高程、位置和地理环境；
- `h / Forecast horizon（预测跨度）`：预测未来多少天；
- `Dynamics（动力学）`：状态在时间和外部条件下如何转移；
- `Decoder（解码器）`：把未来状态重新转换为可评价的未来影像。

现有方案原本设计了以下实验：

1. `EarthNet standard forecasting（EarthNet 标准预测）`；
2. `D/G/h ablation（D/G/h 条件消融）`；
3. `Weather-response diagnostic（天气响应诊断）`；
4. `Uncertainty and geographic consistency（不确定性与地理一致性）`；
5. `Downstream transfer（下游迁移）`；
6. Stage1.5 的成像条件泄漏和跨模态对齐验证。

原方案的总体证明逻辑是：

> EarthNet 标准预测证明模型具有基本未来预测能力；D/G/h 消融证明预测不是单纯依赖历史惯性，而是使用了天气、地理和预测跨度；天气响应诊断证明外生驱动能够改变模型预测；不确定性和地理一致性证明模型具有一定可信度与地理背景意识；下游迁移证明潜状态不只是 EarthNet 专用中间特征；这些实验共同证明 ObsWorld 不只是一个未来像素预测器，而是一个从遥感观测中估计地表状态、并在外生驱动下预测状态演化的世界模型。

这条逻辑总体成立，但当前仍存在一个核心缺口：

> 现有实验能够较好证明“模型会预测、会使用条件”，却还不足以严格证明“模型内部的 `z` 确实更像陆表状态，以及 `F` 确实更像状态动力学，而不只是条件化特征预测器”。

因此，现阶段最合理的策略不是推翻现有框架，也不是继续增加更多天气响应实验，而是把论文主线重新固定为：

> **ObsWorld 是一个面向异构遥感观测的结构化潜状态空间世界模型：它从带有成像条件的多源观测中估计对采集条件更稳健、且保留陆表语义的内部状态，在外生驱动、时间背景、地理背景和预测跨度条件下推进该状态，再按照目标观测条件生成可验证的未来观测。**

英文参考表述为：

> **ObsWorld is a structured latent state-space world model for Earth observation. It estimates acquisition-robust and predictively sufficient land-surface states from heterogeneous satellite observations, evolves these states under external drivers and geographic context, and renders verifiable observations under target acquisition conditions.**

中文释义：

> ObsWorld 是一个面向地球观测的结构化潜状态空间世界模型。它从异构卫星观测中估计对采集条件更稳健、且足以支持未来预测的陆表状态，在外生驱动和地理背景下推进这些状态，并在目标采集条件下生成可验证的观测。

---

# 第一部分：现有训练方案、实验安排及其叙事证明逻辑

## 1. 当前论文主线

当前主线可以概括为：

> 遥感影像不是地表世界本身，而是地表状态经过传感器、轨道、光照、云和数据处理过程之后形成的有偏观测。因此，遥感世界模型不应只学习未来像素长什么样，还应先从观测中估计内部地表状态，再学习该状态在外生驱动、地理背景和时间跨度下如何演化。

形式化表达为：

```text
z_t = E_obs(x_t, phi_t)

z_{t+h} = F(z_t, D_{t:t+h}, G, h)

x_hat_{t+h} = O(z_{t+h}, phi_{t+h})
```

其中：

- `E_obs / Observation encoder（观测编码器）`：从当前影像和成像条件中估计当前状态；
- `x_t / Current observation（当前观测）`：当前卫星影像；
- `phi_t / Imaging condition（成像条件）`：卫星、轨道、产品级别、云、观测几何等；
- `z_t / Current latent state（当前潜状态）`：模型内部的当前陆表状态表示；
- `F / State dynamics model（状态动力学模型）`：预测状态如何演化；
- `D_{t:t+h} / External forcing（外部驱动）`：当前到目标时刻之间的天气条件；
- `G / Geographic context（地理背景）`：高程、位置等稳定背景；
- `h / Forecast horizon（预测跨度）`：从当前到未来目标时刻的间隔；
- `z_{t+h} / Future latent state（未来潜状态）`：预测出的未来内部状态；
- `O / Observation decoder（观测解码器）`：把状态转换为未来观测；
- `x_hat_{t+h} / Predicted future observation（预测未来观测）`：模型生成的未来影像。

该主线的核心不是某一个模块，而是以下三个部分共同成立：

```text
观测与状态可区分
        +
状态可以被条件化地推进
        +
推进结果可以被重新观测和验证
```

只有三者共同成立，ObsWorld 才不是普通的影像预测器。

---

## 2. 当前分阶段训练方案

### 2.1 Stage1：遥感基础表征预训练

`Stage1（第一阶段）`使用 SSL4EO-S12 v1.1 的 Sentinel-1 和 Sentinel-2 数据进行遥感表征预训练。

主要目标是：

1. 学习遥感影像的光谱、纹理和空间结构；
2. 建立光学和雷达数据的基础编码能力；
3. 为后续状态表示学习提供较好的初始化；
4. 避免直接在规模较小的 EarthNet2021 上从零训练全部编码器。

这一阶段主要属于：

`Representation pretraining（表征预训练）`

它能够证明模型具备遥感基础表示能力，但不能单独证明世界模型能力。

Stage1 在论文中的合理定位是：

> Stage1 提供遥感感知基础，使后续模型能够从多源观测中提取信息；它是训练基础，而不是论文最主要的创新。

---

### 2.2 Stage1.5：观测条件感知和跨模态状态对齐

`Stage1.5（第一点五阶段）`在 Stage1 的基础上加入：

- `Phi encoder（成像条件编码器）`；
- `FiLM / Feature-wise Linear Modulation（逐特征线性调制）`；
- S1/S2 近同时相跨模态状态对齐；
- 成像条件与状态表示之间的相关性抑制；
- 冻结 Stage1 教师的特征锚定。

当前主要损失包括：

1. `Reconstruction loss（重建损失）`：保证模型仍能理解和重建输入；
2. `Cross-modal alignment loss（跨模态对齐损失）`：使近同时相的 S1/S2 表示接近；
3. `Nuisance suppression loss（干扰因素抑制损失）`：降低状态对部分成像字段的线性依赖；
4. `Feature anchor loss（特征锚定损失）`：防止状态表示失去 Stage1 已学到的遥感语义。

这一阶段原本想证明：

> 同一地表在不同卫星和成像条件下虽然观测不同，但模型可以获得更一致的内部表示；因此后续动力学模块学习的是地表变化，而不是成像外观变化。

当前已有的理想证明链条是：

```text
S1/S2 跨模态对齐提高
        -> 说明不同传感器观测开始共享表示

线性 phi 泄漏下降
        -> 说明部分成像捷径受到抑制

重建能力不下降
        -> 说明模型没有简单丢弃全部信息

Stage2 使用 Stage1.5 后更稳定或更准确
        -> 说明该状态表示更适合未来动力学学习
```

多个实验共同希望证明：

> Stage1.5 学到的不是完全成像无关的真实状态，而是比普通遥感特征更适合作为动力学起点的、对采集条件更稳健的状态表示。

---

### 2.3 Stage2：EarthNet 条件状态动力学

`Stage2（第二阶段）`使用 EarthNet2021x 的历史 Sentinel-2、未来天气、高程和未来影像进行训练。

当前流程为：

```text
10 帧历史观测
    -> 逐帧状态编码
    -> 历史状态聚合
    -> 当前上下文状态 z_context

z_context + D + G + h
    -> 状态动力学模块
    -> 多个未来潜状态 z_{t+h}

未来潜状态
    -> EarthNet 观测解码器
    -> 未来 20 帧影像
```

其中：

- `Context state aggregator（上下文状态聚合器）`把历史多帧状态融合为当前状态；
- `Driver encoder（驱动编码器）`编码天气条件；
- `Horizon encoder（跨度编码器）`编码未来时间距离；
- `Geo tokenizer（地理标记器）`编码高程；
- `State dynamics module（状态动力学模块）`预测未来潜状态；
- `EarthNet observation decoder（EarthNet 观测解码器）`生成未来四波段影像。

当前 Stage2 损失包括：

1. `Observation loss（观测预测损失）`：未来影像与真实影像之间的误差；
2. `NDVI loss（归一化植被指数损失）`：未来植被状态指标误差；
3. `Latent alignment loss（潜状态对齐损失）`：预测未来状态与真实未来影像编码状态之间的误差；
4. `Delta alignment loss（状态增量对齐损失）`：预测状态变化方向与真实状态变化方向之间的误差；
5. `Temporal smoothness loss（时间平滑损失）`：约束多跨度状态变化不要出现无规律抖动。

Stage2 原本想证明：

> 给定当前地表状态，模型能够根据未来天气、地理背景和预测跨度预测未来地表状态，而不是只生成平均未来影像。

---

### 2.4 Stage3：未来观测解码与标准评估

`Stage3（第三阶段）`负责把未来潜状态转换为 EarthNet 可评价的未来影像。

这一阶段的作用不是重新定义论文主线，而是建立：

`Observation interface（观测评价接口）`

因为潜状态本身没有公开真值，必须通过未来影像、NDVI 和其他可观察指标判断状态预测是否合理。

Stage3 原本想证明：

> 潜状态动力学不仅在内部损失上成立，还能够产生正确的、可被标准指标检验的未来观测。

---

### 2.5 Stage4：下游迁移与状态复用

`Stage4（第四阶段）`是可选扩展，用于测试状态表示能否迁移到：

- 土地覆盖分类；
- 作物类型或农业状态识别；
- 洪涝识别；
- 其他地表相关任务。

它原本想证明：

> `z` 不只是 EarthNet 预测任务中的临时特征，而是保留了一定的通用地表语义。

这一阶段属于辅助证据，不应抢占主实验位置。

---

## 3. 原方案的实验安排与总证明逻辑

### 3.1 实验一：EarthNet 标准预测

`Standard forecasting（标准预测）`使用 EarthNet 官方或兼容协议，输入历史影像、天气和地理条件，预测未来影像。

主要指标包括：

- `ENS / EarthNetScore（EarthNet 综合分数）`，越高越好；
- `MAE / Mean Absolute Error（平均绝对误差）`，越低越好；
- `SSIM / Structural Similarity（结构相似度）`，越高越好；
- `NDVI-MAE（植被指数平均绝对误差）`，越低越好；
- 不同预测跨度下的误差。

该实验理想情况下证明：

> ObsWorld 不是只有概念而没有预测能力；其内部状态动力学能够在公开标准任务上产生合理未来观测。

但该实验单独不能证明世界模型，因为普通视频预测器也可能获得较好的像素指标。

---

### 3.2 实验二：D/G/h 条件消融

`Ablation study（消融实验）`通过删除或打乱某个模块，判断该模块是否真的产生贡献。

当前建议比较：

```text
z-only：只使用当前状态
no-D：不使用天气驱动
no-G：不使用地理背景
no-h：不使用预测跨度
full：使用全部条件
```

理想结果是：

- 加入 D 后，极端天气和植被响应预测明显改善；
- 加入 h 后，中长期预测改善；
- 加入 G 后，部分地形或高程区域改善；
- full 模型优于 z-only 和主要消融版本。

该实验理想情况下证明：

> ObsWorld 的预测不是简单依赖历史影像惯性，而是显式使用外生驱动、地理背景和时间跨度。

---

### 3.3 实验三：天气响应诊断

`Weather-response diagnostic（天气响应诊断）`固定当前状态、地理背景和预测跨度，改变天气条件，观察预测结果是否发生变化。

原方案包括：

- 降水增加或减少；
- 温度增加或减少；
- VPD 增加或减少；
- 辐射增加或减少；
- 极端天气子集；
- 季节匹配样本。

该实验理想情况下证明：

> 模型不是只记住季节平均值；不同天气情景会产生不同未来状态和未来观测。

它与 D 消融共同证明：

```text
D 消融：
天气信息对预测有用

天气响应：
改变天气会改变未来预测

二者共同：
模型内部存在可诊断的驱动条件状态转移
```

---

### 3.4 实验四：不确定性

`Uncertainty estimation（不确定性估计）`让模型同时输出未来预测和模型对预测可靠程度的估计。

理想结果包括：

- 长期预测比短期预测不确定；
- 极端天气样本比普通样本不确定；
- 模型预测不确定性较高的区域，真实误差也较高；
- 置信区间覆盖率接近设定水平。

该实验理想情况下证明：

> ObsWorld 不仅给出单点未来，还能够识别哪些未来更难预测。

这属于可信度增强，不是世界模型身份的第一支柱。

---

### 3.5 实验五：地理一致性

`Geographic consistency（地理一致性）`测试高程等地理背景是否真正调节状态转移。

当前建议比较：

- full G；
- no-G；
- shuffled-G，即打乱高程；
- 按高程区间分层评价。

理想结果是：

- 正确 G 优于打乱 G；
- 高程影响在部分区域更明显；
- 同一天气驱动在不同地理背景下产生不同响应。

该实验理想情况下证明：

> G 不是无意义附加通道，而是状态转移的稳定背景条件。

由于目前 G 主要只有高程，这一实验宜作为辅助证据，而不宜承担整篇论文的核心创新。

---

### 3.6 实验六：下游迁移

`Downstream transfer（下游迁移）`冻结或轻量微调状态编码器，在其他任务上评价状态表示。

理想结果是：

- Stage1.5 或 Stage2 表示优于 Stage1；
- Stage2 后的表示没有因 EarthNet 训练而明显退化；
- 与植被、土地覆盖等状态相关任务获得提升。

该实验理想情况下证明：

> 学到的 `z` 不只是未来影像预测的临时特征，而保留了可复用的地表语义。

---

## 4. 原方案多个实验如何共同证明主线

原方案不是依赖某一个实验，而是依赖多层证据共同支撑：

```text
Stage1.5 对齐与泄漏验证
    -> 证明状态表示开始减少部分成像捷径

EarthNet 标准预测
    -> 证明模型具备可比较的未来预测能力

D/G/h 消融
    -> 证明结构化条件确实被使用

天气响应诊断
    -> 证明外生驱动会改变未来预测

不确定性与地理一致性
    -> 证明模型具有一定可信度和背景感知能力

下游迁移
    -> 证明状态保留可复用语义
```

理想情况下，这些实验共同得出：

> ObsWorld 从多源遥感观测中估计内部地表状态，使用外生驱动、地理背景和预测跨度预测状态演化，并将未来状态转换为可验证观测；其预测不仅在像素层可比较，而且在条件消融、驱动响应、状态语义和迁移能力上具有可诊断证据。

但后续审查发现，原方案的证明链条仍缺少三个最关键的中间环节：

1. `State validity（状态有效性）`：`z` 是否真的比普通特征更像状态；
2. `Observation-state separation（观测—状态分离）`：phi 是否真正控制观测而不进入动力学；
3. `Transition composition（转移组合性）`：动力学是否具有可组合的状态推进性质。

这三个问题构成第二部分的核心。

---

# 第二部分：现有方案的问题及建议

## 5. 问题总述

现有方案最大的风险不是模型完全无法训练，而是：

> 当前结构可能最终取得合理 EarthNet 指标，也可能对 D/G/h 有一定敏感性，但审稿人仍可以把它解释成“预训练编码器 + 条件化预测头 + 未来影像解码器”，而不是结构化状态空间世界模型。

因此，现阶段的问题主要是“论文主张与证据不完全匹配”，其次才是模型性能问题。

以下问题按重要性排序。

---

## 6. 问题一：变量定义存在混淆

### 6.1 当前问题

此前部分文档把以下字段都放进 phi：

- 轨道和卫星；
- 云；
- 太阳高度角；
- 季节；
- 经纬度；
- 模态。

但这些字段并不属于同一种变量：

- 轨道、卫星、产品级别主要是采集条件；
- 季节和日期会改变真实植被状态；
- 经纬度和高程属于地理背景；
- 太阳高度角同时受到日期和纬度影响，既包含观测因素，也包含季节信息。

如果把它们全部当作需要从状态中消除的干扰因素，模型可能在减少成像泄漏的同时，错误删除真实地表变化所需的信息。

### 6.2 建议

统一采用：

```text
S：动态陆表状态
Phi：纯成像与采集条件
D：外生天气驱动
T：时间与物候背景
G：静态地理背景
h：预测跨度
```

具体建议：

| 类别 | 字段 | 是否应从状态中强制消除 |
| --- | --- | --- |
| Phi / 成像条件 | 卫星编号、轨道方向、产品级别、传感器、部分云信息 | 可以抑制，但需保留必要观测质量信息 |
| T / 时间背景 | day-of-year、季节 | 不应直接作为纯干扰消除 |
| G / 地理背景 | 经纬度、高程 | 不应作为 phi 消除 |
| D / 外生驱动 | 降水、温度、VPD、辐射 | 应进入动力学 |
| S / 状态语义 | NDVI、土地覆盖、植被状态 | 应尽量保留 |

论文中不宜再使用“消除所有 phi 信息”，而应写：

> The state representation is regularized to reduce sensitivity to acquisition-specific nuisance factors while preserving land-surface semantics.

中文释义：

> 状态表示通过正则化降低对采集特有干扰因素的敏感性，同时保留陆表语义。

---

## 7. 问题二：当前不能证明 z 就是地表状态

### 7.1 当前证据

现有结果显示：

- S1/S2 跨模态对齐得到改善；
- 训练内线性 nuisance loss 较低；
- 重建能力未明显退化；
- 但非线性 MLP probe 仍能以约 67%-71% 准确率恢复部分 orbit/satellite 信息；
- 60k 相比 30k 改善了对齐，但没有明显改善非线性泄漏。

这说明：

> 当前 `z` 可以称为“跨模态对齐的状态候选表示”，但还不能称为“完全成像解耦的真实地表状态”。

### 7.2 原实验为什么不够

只证明干扰信息下降是不够的，因为模型可能把所有信息一起删除。

例如，如果所有输入都输出同一个常数向量：

```text
z = 0
```

那么任何探针都无法预测轨道和卫星，但该表示也不包含任何地表信息。

### 7.3 建议

状态验证必须同时测试两个方向：

```text
干扰信息减少
        +
地表语义保留
```

建议增加：

1. `Nuisance probe（干扰因素探针）`
   - 卫星编号；
   - 轨道方向；
   - 产品级别；
   - 模态；
   - 云量。

2. `Semantic probe（语义探针）`
   - LULC / Land Use and Land Cover（土地利用与土地覆盖）分类；
   - NDVI 回归；
   - 跨模态检索；
   - 必要时加入地表变化或植被状态任务。

理想结果应为：

```text
成像干扰 probe 下降
地表语义 probe 不下降或提升
跨模态同地点检索提升
Stage2 未来状态预测提升
```

只有四类证据共同出现，才能较稳地说 `z` 更适合作为状态。

---

## 8. 问题三：Stage2 的 phi 路径没有真正贯穿观测模型

### 8.1 当前实现

当前 EarthNet 缺少与 SSL4EO 完全一致的采集元数据，因此 Stage2 编码时主要使用 neutral phi，即中性缺失条件。

当前 EarthNet decoder 的主要输入也是：

```text
future state -> future image
```

而不是理论定义中的：

```text
future state + target phi -> future image
```

### 8.2 影响

如果解码器无法读取 phi，为了重建目标观测，编码器就可能被迫把成像外观信息继续保留在 `z` 中。

这会造成理论与实现不一致：

```text
理论：
状态和观测条件分工

实现：
状态同时承担地表内容和观测外观
```

### 8.3 建议

让观测解码器显式接收目标成像条件：

```text
x_hat = O(z, phi_target)
```

并利用 SSL4EO-S12 v1.1 的 S2L1C/S2L2A 进行交叉解码：

```text
L1C -> z -> L1C 条件 -> L1C
L1C -> z -> L2A 条件 -> L2A
L2A -> z -> L1C 条件 -> L1C
L2A -> z -> L2A 条件 -> L2A
```

其中：

- `L1C（一级 C 产品）`：大气层顶部反射率产品；
- `L2A（二级 A 产品）`：经过大气校正的地表反射率产品。

这类数据比跨季节对更适合证明观测条件分离，因为它们可以尽量保持地表内容不变，只改变产品处理条件。

EarthNet 没有完整 phi 时，可以继续使用 neutral phi；观测模型的独立证据由 SSL4EO 提供。

---

## 9. 问题四：非线性 phi 泄漏仍未解决

### 9.1 当前问题

现有 `Cross-covariance regularization（互协方差正则）`主要减少线性相关。

但 MLP probe 能够恢复部分离散成像条件，说明 phi 信息仍以非线性方式存在于状态中。

### 9.2 建议

加入：

`Adversarial nuisance prediction（对抗式干扰因素预测）`

基本结构为：

```text
z -> nuisance predictor -> 预测卫星/轨道/产品

predictor 尽量预测正确
encoder 尽量让 predictor 预测失败
```

可使用：

`Gradient Reversal Layer（梯度反转层）`

但该对抗损失只能针对明确的采集干扰，不宜对季节、纬度、NDVI 等状态或背景变量使用。

同时保留：

- Feature anchor（特征锚定）；
- LULC/NDVI 语义头；
- 重建损失；
- 跨模态对齐损失。

这样才能避免模型为了隐藏 phi 而删除全部语义。

---

## 10. 问题五：未来状态目标可能随在线编码器漂移

### 10.1 当前问题

Stage2 使用真实未来影像经过编码器得到 `z_target`，再监督 `z_pred`。

但当在线 encoder 在训练后期被解冻时：

- 当前状态编码器会更新；
- 未来目标编码器实际上也跟随同一组参数变化；
- 虽然 target 分支不反向传播，但目标空间仍随训练发生漂移。

### 10.2 影响

模型可能出现：

- 状态目标不稳定；
- encoder 和 dynamics 共同改变坐标系；
- latent loss 下降但状态语义变弱；
- 未来状态监督缺少固定参照。

### 10.3 建议

采用：

1. `Frozen target encoder（冻结目标编码器）`，或
2. `EMA target encoder（指数移动平均目标编码器）`。

EMA 的含义是：

> 目标编码器不直接通过梯度快速更新，而是缓慢跟随在线编码器，形成更稳定的教师。

建议训练顺序：

```text
第一阶段：
冻结 Stage1.5 encoder 和 target encoder
只训练 dynamics、条件编码器和 EarthNet decoder

第二阶段：
保持 target encoder 为 EMA/frozen
仅小学习率解冻 online encoder 最后若干层

第三阶段：
根据验证结果决定是否联合微调
```

---

## 11. 问题六：当前 dynamics 可能只是条件化回归器

### 11.1 当前实现

当前模型从同一个 `z_context` 出发，为每个 h 独立预测：

```text
F(z_context, D_h, G, h) -> z_h
```

这种 direct multi-horizon prediction（直接多跨度预测）训练稳定、计算高效，但审稿人可能认为：

> 模型只是根据 h 和天气直接回归目标特征，并没有学到可以反复推进的状态动力学。

### 11.2 建议

加入：

`Transition composition consistency（状态转移组合一致性）`

例如：

```text
直接路径：
z_100_direct = F(z_0, D_0:100, G, 100)

组合路径：
z_30 = F(z_0, D_0:30, G, 30)
z_100_composed = F(z_30, D_30:100, G, 70)
```

然后约束：

```text
z_100_direct ≈ z_100_composed ≈ z_100_target
```

该实验不要求立即采用复杂长链自回归生成，只需测试：

- 20+30 天；
- 30+70 天；
- 50+50 天；
- 直接预测与两步预测的一致性。

它能回答：

> 一个长时间状态转移能否由多个短时间状态转移组成？

如果成立，动力学主张会明显强于普通 horizon-conditioned regression（跨度条件回归）。

---

## 12. 问题七：当前天气响应主要证明敏感性，不证明正确性

### 12.1 当前问题

当前 weather-response 脚本主要计算：

- 改变 D 后的平均 NDVI 变化；
- 改变 D 后的平均像素变化。

这只能证明：

`Sensitivity（敏感性）`：输入天气变了，输出也变了。

但不能证明：

`Response correctness（响应正确性）`：输出变化方向和强度是合理的。

模型即使产生错误响应，也可能得到很大的输出变化。

### 12.2 建议

将响应实验分成四级：

1. `Driver permutation（驱动打乱）`
   - 在相似样本间打乱天气；
   - 检查预测性能是否下降；
   - 证明 D 含有有效预测信息。

2. `Natural matched pairs（自然匹配样本对）`
   - 匹配相似初始状态、季节和地理背景；
   - 选择不同天气轨迹；
   - 比较真实未来 NDVI 差异与预测差异。

3. `Observed trajectory swap（真实天气轨迹替换）`
   - 使用数据集中真实出现过的天气序列替换 D；
   - 避免构造不合理天气组合。

4. `Quantile sweep（分位数扫描）`
   - 只在训练分布的 5%-95% 范围内改变天气；
   - 明确标记超出训练支持范围的情景。

论文可写：

> Predictions exhibit driver-consistent responses on matched observational cases.

中文释义：

> 在匹配的观测样本中，模型预测表现出与外生驱动一致的响应。

不应写：

> The model identifies the causal effect of weather.

中文释义：

> 模型识别了天气的真实因果效应。

因为公开观测数据通常没有随机干预，无法严格识别因果效应。

---

## 13. 问题八：D、T 与 h 存在混淆

### 13.1 当前问题

当前 D 特征中包含：

- target day-of-year sin/cos，即目标日期周期编码；
- 降水；
- 温度；
- VPD；
- 辐射。

同时模型又输入 h。

这可能导致：

- 模型依赖目标日期记住季节平均；
- h 的独立作用被目标日期替代；
- no-D 同时删除天气和季节，难以解释；
- 天气响应与物候时间效应混合。

### 13.2 建议

拆分为：

```text
D_weather：
降水、温度、VPD、辐射

T_calendar：
day-of-year、季节相位

G：
高程、位置等地理背景

h：
预测跨度
```

新增消融：

```text
z-only
z + T
z + D
z + D + T
z + D + T + h
full D/T/G/h
```

这样才能回答：

- 模型是否只记季节；
- 天气是否提供超出季节平均的增量信息；
- h 是否具有独立作用；
- G 是否调节天气响应。

---

## 14. 问题九：G 和 uncertainty 不宜承担核心叙事

### 14.1 G 的问题

当前 G 主要只有 elevation（高程）。高程可能有价值，但它不足以代表完整地理物理规律。

建议：

- G 保留在形式化中；
- 使用 no-G、shuffled-G 和 elevation-stratified evaluation（高程分层评价）；
- 如果效果只在局部区域出现，诚实作为辅助发现；
- 不把“完整地理物理一致性”写成核心贡献。

### 14.2 uncertainty 的问题

当前主配置中 probabilistic log-variance（概率对数方差）尚未作为主训练能力启用。

建议：

- 时间紧时不把 uncertainty（不确定性）列为第一贡献；
- 先完成状态有效性、phi 解码、动力学组合性；
- 若后续实现，再作为可信度增强实验；
- 不必为了追随其他概率预测工作改成大型 diffusion model（扩散模型）。

---

## 15. 问题十：当前缺少 Stage2 主结果

当前工作区已经具备：

- EarthNet2021x loader；
- D/G/h 字段构建；
- band adapter（波段适配器）；
- context aggregator（上下文聚合器）；
- state dynamics（状态动力学）；
- decoder（解码器）；
- latent/observation losses（潜状态与观测损失）；
- 消融开关；
- 评估和天气响应脚本。

但当前仍未形成完整的 Stage2 结果证据：

- 正式主模型 checkpoint；
- EarthNet 标准预测主表；
- D/T/G/h 消融表；
- 组合一致性结果；
- 匹配样本响应结果；
- 状态有效性主表。

因此当前可以说：

> 现有框架具有支持 AAAI 叙事的潜力。

但还不能说：

> 现有实验已经证明 AAAI 主线成立。

---

# 第三部分：针对现有框架的解决思路与方案

## 16. 解决方案总述

### 16.1 一句话方案

> **不推翻现有 Stage1—Stage1.5—Stage2 架构，而是重新明确变量分工，使用 SSL4EO 证明“观测如何形成状态”，使用 EarthNet 证明“状态如何随外生驱动演化”，并增加状态语义保持、phi 条件解码、稳定目标编码器和状态转移组合一致性四类关键证据。**

### 16.2 多模块共同证明逻辑

修正后的总证明链条应为：

```text
SSL4EO 状态语义与 nuisance 双向 probe
    -> 证明 z 减少部分采集捷径，同时保留陆表信息

L1C/L2A 或多模态 phi 条件交叉解码
    -> 证明状态内容和观测形式可以分工

EarthNet 潜状态预测与标准观测预测
    -> 证明状态能够被推进，并能产生可验证未来观测

D/T/G/h 消融
    -> 证明天气、时间、地理和跨度具有可区分作用

状态转移组合一致性
    -> 证明 F 不只是根据 h 回归未来特征，而具有可组合推进性质

匹配样本与真实天气轨迹响应
    -> 证明驱动响应不仅存在，而且与观测证据方向一致

下游或语义迁移
    -> 证明 z 不是 EarthNet 专用特征
```

这些实验共同证明：

> ObsWorld 学到了一种对采集条件更稳健、保留地表语义、能够在外生驱动下进行一致未来推进、并可重新映射为目标观测的内部状态表示。

这比“我们做了一个更强的天气条件预测器”更独立，也比“我们完全恢复了真实世界状态”更严谨。

---

## 17. 修正后的研究问题

建议论文围绕四个研究问题组织。

### RQ1：状态有效性

`Research Question 1（研究问题一）`

> 模型能否从异构遥感观测中学习一种降低采集因素敏感性、同时保留陆表语义的状态表示？

英文：

> Does the model learn an acquisition-robust state representation while preserving land-surface semantics?

需要的证据：

- nuisance probe 下降；
- LULC/NDVI probe 保持或提升；
- 跨模态检索提升；
- 非塌缩验证。

---

### RQ2：观测—状态分离

> 在共享状态下，模型能否根据不同目标成像条件生成对应观测？

英文：

> Can the model render condition-specific observations from a shared latent state?

需要的证据：

- L1C/L2A 同条件重建；
- L1C/L2A 交叉解码；
- 有 phi 优于无 phi；
- 改变 phi 时语义稳定、观测外观按预期改变。

---

### RQ3：状态动力学

> 显式潜状态动力学是否优于普通特征或像素预测，并具有多跨度组合一致性？

英文：

> Does explicit latent-state dynamics outperform direct feature or pixel forecasting and exhibit transition composition across horizons?

需要的证据：

- latent target error；
- delta alignment；
- direct/composed consistency；
- 长跨度性能；
- 与等参数预测基线比较。

---

### RQ4：驱动条件响应

> 天气驱动是否提供超出季节和历史惯性的预测信息，并产生与匹配观测证据一致的状态响应？

英文：

> Do weather drivers provide predictive information beyond seasonality and historical persistence, and do they induce observation-consistent state responses?

需要的证据：

- D 与 T 分离消融；
- driver permutation；
- matched pairs；
- observed trajectory swap；
- response direction/correlation。

---

## 18. 数据集分工

### 18.1 SSL4EO-S12 v1.1

主要负责：

```text
观测 -> 状态
```

可用信息包括：

- S1GRD；
- S2L1C；
- S2L2A；
- S2RGB；
- LULC；
- DEM；
- NDVI；
- cloud mask；
- 时间、经纬度和文件元数据。

主要实验：

- S1/S2 近同时相对齐；
- L1C/L2A 产品级交叉解码；
- acquisition nuisance probe；
- LULC/NDVI semantic probe；
- 多模态检索；
- phi 条件生成。

注意：

> 同地点不同季节不能直接当作完全相同状态。跨季节数据应当用于学习状态变化或稳定语义，不应强制全部细节完全一致。

---

### 18.2 EarthNet2021x

主要负责：

```text
当前状态 -> 未来状态
```

使用：

- train；
- iid；
- ood；
- extreme；
- seasonal。

其中：

- `IID / Independent and Identically Distributed（独立同分布）`测试标准同分布泛化；
- `OOD / Out of Distribution（分布外）`测试跨地区或不同分布泛化；
- `Extreme（极端天气）`测试极端事件响应；
- `Seasonal（季节测试）`用于控制季节背景、判断天气是否提供额外信息。

主要实验：

- 标准预测；
- latent dynamics；
- D/T/G/h 消融；
- composition consistency；
- extreme response；
- matched-pair response；
- 跨地区泛化。

---

### 18.3 可选外部验证：SEN12MS-CR-TS

若时间和存储允许，可使用 SEN12MS-CR-TS 作为外部观测鲁棒性验证。

它可以提供：

- 多时相 S1/S2；
- 云覆盖和较清晰光学观测；
- 多地区测试；
- 外部数据分布。

它主要用于：

> 验证状态表示是否对云和模态变化具有外部泛化能力。

不建议将其加入第一轮主训练，以免扩大工程范围。

---

## 19. 模型修改方案

### 19.1 明确 state 与 observation 两条路径

建议最终结构为：

```text
x, phi
  -> encoder
  -> z_state

z_state, D, T, G, h
  -> dynamics
  -> z_future

z_future, phi_target
  -> decoder
  -> x_future
```

关键原则：

- dynamics 不读取 phi；
- decoder 必须能够读取 phi_target；
- `z_state` 接受 acquisition nuisance 抑制；
- `z_state` 同时接受语义保持监督；
- D/T/G/h 在动力学中分开编码。

---

### 19.2 Stage1.5 损失修改

建议总损失为：

```text
L_stage1.5
  = L_recon
  + lambda_align * L_cross_modal
  + lambda_adv * L_nuisance_adversarial
  + lambda_sem * L_semantic
  + lambda_anchor * L_anchor
```

中文解释：

- `L_recon（重建损失）`：防止丢失观测信息；
- `L_cross_modal（跨模态损失）`：对齐近同时相 S1/S2；
- `L_nuisance_adversarial（对抗干扰损失）`：减少可恢复的纯采集因素；
- `L_semantic（语义保持损失）`：保留 LULC/NDVI 等地表信息；
- `L_anchor（特征锚定损失）`：防止偏离原始遥感表征。

---

### 19.3 Stage2 损失修改

建议总损失为：

```text
L_stage2
  = L_obs
  + lambda_ndvi * L_ndvi
  + lambda_latent * L_latent
  + lambda_delta * L_delta
  + lambda_comp * L_composition
  + lambda_smooth * L_smooth
```

新增：

`L_composition（状态转移组合一致性损失）`

用于约束：

```text
F(z, D_0:h2, h2)
≈
F(F(z, D_0:h1, h1), D_h1:h2, h2-h1)
```

训练初期可先不启用或使用较小权重，在主预测稳定后逐步增加。

---

### 19.4 使用稳定目标编码器

建议：

```text
online encoder（在线编码器）：
编码当前状态，可在后期小学习率更新

target encoder（目标编码器）：
编码真实未来状态，使用 frozen 或 EMA 更新
```

这样未来状态目标不会随在线模型快速漂移。

---

## 20. 修正后的实验安排

### 20.1 Table 1：标准 EarthNet 预测

目的：

> 证明方法在标准任务上可工作，而不是只讲状态概念。

对比：

- Persistence（持续性基线）；
- Climatology（气候平均基线）；
- ConvLSTM；
- SimVP；
- EarthFormer 或可复现同类模型；
- ObsWorld。

指标：

- ENS；
- MAE；
- SSIM；
- NDVI-MAE；
- 短、中、长期误差。

该表不承担“状态一定成立”的全部证明。

---

### 20.2 Table 2：状态有效性

建议表格：

| Model（模型） | LULC↑ | NDVI R²↑ | Cross-modal retrieval↑（跨模态检索） | Orbit probe↓（轨道探针） | Satellite probe↓（卫星探针） | Product probe↓（产品探针） |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage1 | | | | | | |
| Stage1.5 current | | | | | | |
| + adversarial nuisance | | | | | | |
| + phi-conditioned decoder | | | | | | |

该表要同时证明：

```text
减少干扰
但不损失语义
```

---

### 20.3 Table 3：观测条件解码

建议比较：

| Encoder input（编码输入） | Decoder condition（解码条件） | Target（目标） | Reconstruction error↓（重建误差） | Semantic consistency↑（语义一致性） |
| --- | --- | --- | ---: | ---: |
| L1C | L1C | L1C | | |
| L1C | L2A | L2A | | |
| L2A | L1C | L1C | | |
| L2A | L2A | L2A | | |
| L1C | no-phi | L2A | | |

该表证明：

> 共享状态与目标观测条件可以分工生成不同产品观测。

---

### 20.4 Table 4：动力学与组合一致性

建议表格：

| Model（模型） | Latent error↓（潜状态误差） | Delta error↓（状态增量误差） | Composition error↓（组合误差） | Long-horizon error↓（长期误差） |
| --- | ---: | ---: | ---: | ---: |
| feature predictor | | | | |
| z-only dynamics | | | | |
| +D | | | | |
| +D+T+h | | | | |
| full D/T/G/h | | | | |
| full + composition loss | | | | |

该表证明：

> 显式状态动力学不仅能预测未来，还具有一定的跨跨度组合一致性。

---

### 20.5 Table 5：驱动响应正确性

建议指标：

- `Driver permutation degradation（驱动打乱后的性能下降）`；
- `Directional hit rate（方向命中率）`；
- `Matched-pair response accuracy（匹配样本响应准确率）`；
- `Response correlation（响应相关性）`；
- `Extreme subset error（极端天气子集误差）`。

该表证明：

> 天气驱动提供超出季节和历史惯性的有效信息，模型响应与真实观测中的变化方向具有一致性。

---

## 21. 修正后的消融实验

### 21.1 状态表示消融

```text
Stage1
Stage1.5 current
Stage1.5 no-nuisance
Stage1.5 adversarial-nuisance
Stage1.5 no-semantic-preservation
Stage1.5 full
```

### 21.2 观测模型消融

```text
decoder no-phi
decoder with product phi
decoder with full available phi
cross-product decoding
```

### 21.3 动力学条件消融

```text
z-only
z + T
z + D
z + D + T
z + D + T + h
z + D + T + G + h
```

### 21.4 动力学结构消融

```text
direct-only
direct + temporal smoothness
direct + composition consistency
one-step composed rollout
two-step composed rollout
```

### 21.5 响应实验消融

```text
real D
shuffled D
climatology D
matched observed D
empirical quantile sweep
```

---

## 22. 建议训练顺序

### Phase A：重新验证和修正状态表示

`Phase A（阶段 A）`

1. 重新整理 Phi/D/T/G 字段；
2. 保留当前 60k checkpoint 作为基线；
3. 增加 LULC/NDVI semantic probes；
4. 增加 product-level 和 nonlinear nuisance probes；
5. 训练 adversarial nuisance 版本；
6. 选择“干扰下降且语义不下降”的 checkpoint。

### Phase B：完成观测条件解码

`Phase B（阶段 B）`

1. decoder 接收 phi；
2. 先做 S2L1C/S2L2A；
3. 完成同条件和交叉条件重建；
4. 验证 no-phi 与 with-phi 差异；
5. 再决定是否扩展到 S1/S2 双模态解码。

### Phase C：训练稳定的 Stage2 主模型

`Phase C（阶段 C）`

1. 使用修正后的 Stage1.5 encoder；
2. 使用 frozen/EMA target encoder；
3. 先冻结主 encoder；
4. 训练 D/T/G/h dynamics 和 EarthNet decoder；
5. 完成标准预测；
6. 再进行小学习率联合微调。

### Phase D：加入组合一致性

`Phase D（阶段 D）`

1. loader 输出分段天气统计；
2. 构造 direct 和 composed 两条路径；
3. 先作为评估；
4. 若不一致明显，再加入 composition loss；
5. 重新比较长期预测。

### Phase E：完成机制实验

`Phase E（阶段 E）`

1. D/T/G/h 消融；
2. driver permutation；
3. extreme/seasonal matched pairs；
4. observed trajectory swap；
5. G 分层；
6. 可选 uncertainty 和 downstream。

---

## 23. 最小 AAAI 证明闭环

时间有限时，必须保留：

```text
1. EarthNet 标准预测
2. 状态语义保持 + nuisance 抑制双向验证
3. phi 条件观测解码
4. D/T/h 核心消融
5. 状态转移组合一致性
6. 匹配观测下的天气响应正确性
```

可以降为附录或暂缓：

- uncertainty；
- 完整 G 扩展；
- 第二个下游数据集；
- SEN12MS-CR-TS；
- 大模型插件；
- 多数据集 Stage2 联合训练；
- 长链自回归生成。

最小闭环的总叙事是：

> 状态实验首先证明 ObsWorld 的 `z` 在降低采集因素敏感性的同时保留地表语义；观测条件解码实验进一步证明状态内容和观测形式可以分工；EarthNet 标准预测证明该状态能够产生可比较的未来观测；D/T/h 消融和匹配天气响应证明状态转移使用了外生驱动而非只记季节平均；组合一致性证明多个短跨度状态转移可以形成较一致的长跨度推进。这些实验共同证明 ObsWorld 学到的是可诊断、可推进、可重新观测的陆表内部状态，而不是普通的未来像素回归特征。

---

## 24. AAAI Go/No-Go 判断

### 24.1 Go：可以支撑主线

满足以下多数条件时，可以继续 world model（世界模型）叙事：

1. EarthNet 标准预测明显优于 persistence/climatology 等简单基线；
2. nuisance probe 下降，同时 LULC/NDVI 不下降；
3. phi-conditioned decoder 优于 no-phi，并能完成产品级交叉解码；
4. latent dynamics 优于普通 feature predictor；
5. direct/composed transition 具有明显一致性；
6. D 提供超出 T 的增量信息；
7. matched-pair response 方向合理；
8. OOD/extreme 结果不崩溃。

### 24.2 Yellow：可以投稿但需降调

以下情况可以接受：

- 像素指标不是第一，但明显优于简单基线；
- G 整体贡献较小；
- uncertainty 尚未完成；
- phi 泄漏未完全消失，但较 Stage1 明显下降；
- composition 误差仍随跨度增加，但优于无约束模型；
- 下游任务只有一个或只在附录。

此时应写：

> acquisition-robust state representation（采集条件稳健状态表示）

而不是：

> fully imaging-invariant state（完全成像不变状态）。

### 24.3 No-Go：不应硬撑世界模型叙事

出现以下组合时，应降级为 structured forecasting（结构化预测）：

- 状态语义 probe 不如 Stage1；
- nuisance probe 没有改善或进一步升高；
- phi decoder 无效果；
- latent dynamics 不优于直接预测头；
- direct 和 composed 结果完全不一致；
- D 打乱后性能不下降；
- 改变天气只产生无规律输出；
- 标准预测弱于 persistence/climatology。

---

## 25. 最终论文贡献建议

建议最终贡献写成三点。

### Contribution 1：问题与形式化

英文：

> We formulate Earth-observation world modeling as structured latent-state learning from heterogeneous, acquisition-conditioned observations, explicitly separating land-surface states, observation conditions, external drivers, temporal context, and geographic context.

中文释义：

> 我们将遥感世界建模形式化为从异构、带采集条件的观测中学习结构化潜状态，并明确区分陆表状态、观测条件、外生驱动、时间背景和地理背景。

### Contribution 2：模型

英文：

> We propose ObsWorld, which learns acquisition-robust state representations, evolves them through driver-conditioned latent dynamics, and renders target observations through a condition-aware observation decoder.

中文释义：

> 我们提出 ObsWorld：它学习对采集条件更稳健的状态表示，通过外生驱动条件下的潜状态动力学推进状态，并利用观测条件感知解码器生成目标观测。

### Contribution 3：评估

英文：

> We introduce a state-centric evaluation protocol combining semantic preservation, nuisance suppression, conditional observation rendering, transition composition, standard forecasting, and matched driver-response diagnostics.

中文释义：

> 我们提出以状态为中心的评估协议，联合检验语义保持、干扰抑制、条件观测生成、状态转移组合性、标准预测和匹配驱动响应。

---

## 26. 最终一句话定稿

最简洁的中文表述：

> **ObsWorld 的核心不是根据天气生成一段未来遥感影像，而是从多源、有偏的遥感观测中估计对采集条件更稳健的陆表状态，学习该状态在外生驱动下如何一致地演化，并在指定观测条件下重新生成可验证的未来观测。**

对应英文：

> **ObsWorld does not merely generate future satellite imagery from weather conditions. It estimates acquisition-robust land-surface states from heterogeneous and biased observations, learns their consistent evolution under external drivers, and renders verifiable future observations under specified acquisition conditions.**

中文释义：

> ObsWorld 不只是根据天气条件生成未来卫星影像；它从异构、有偏观测中估计对采集条件更稳健的陆表状态，学习这些状态在外生驱动下的一致演化，并在指定采集条件下生成可验证的未来观测。

这应当成为后续模型修改、实验排序和论文写作的统一总纲。
