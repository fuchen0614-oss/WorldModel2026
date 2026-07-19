# 67 ObsWorld 核心叙事、相关工作差异、Table 1 数值与下一步

日期：2026-07-19
性质：核心叙事与实验决策文档
状态：基于当前代码、Direct-P4 已完成结果与截至 2026-07-19 的公开文献重新冻结
关联文档：[[52_ObsWorld_AAAI27中心叙事训练实验与写作总纲_20260716]]、[[58_ObsWorld_AAAI27中文论文终稿_主实验冻结版_20260717]]、[[60_ObsWorld_主实验表格代码需求梳理_基线用文献值_20260717]]、[[63_ObsWorld_U与正式评估闭环_概念代码审查指标协议与执行指南_20260718]]

---

## 0. 先给最终答案

### 0.1 当前最稳的一句话叙事

> **ObsWorld 不是声称恢复不可直接观测的“绝对真实地表”，而是从稀疏、多光谱卫星历史中构建一个保留空间结构的预测状态；在降水、温度、VPD 和太阳辐射等外生驱动下，用同一个五日状态转移连续推进 100 天，并把每一步状态解码成可由未来真实卫星观测检验的 RGBN 影像。**

更短、更适合团队沟通的版本：

> **别人主要预测“未来会看到什么”；ObsWorld 进一步显式维护“一个怎样逐步向前走的空间预测状态”，并用严格配对的 Direct 对照检验这个状态过程是不是必要。**

### 0.2 当前最能打的核心，不是哪些内容

当前最能打的不是：

- 第一次使用天气；
- 第一次预测未来卫星图像；
- 第一次使用潜状态；
- 第一次做递推；
- 第一次称作遥感世界模型；
- 第一次做气象情景模拟；
- 不确定性；
- U（观测更新）；
- “恢复了唯一真实世界状态”。

这些内容已被不同工作分别覆盖，尤其 VegSim 已经明确使用潜在植被状态、递归动力学和可控天气情景。

当前真正可能成立的核心交集是：

> **高分辨率空间预测状态 + 完整 RGBN 观测出口 + 共享短步受控转移 + 100 天开放循环 + 严格配对 Direct 结构检验。**

也就是说，ObsWorld 试图在两类现有路线之间补一个空位：

1. Contextformer、Earthformer、PredRNN、SimVP 等能够预测未来，但不以“严格检验一个共享空间状态转移过程”为中心；
2. VegSim 已经有递归潜状态和天气情景，但把每个 minicube 压成一个平均 NDVI 时间序列，不预测地块内部完整空间 RGBN 演化；
3. EO-WM 能生成完整多光谱未来并建模概率性与物理天气响应，但采用视频扩散一次建模未来潜视频，不把一个共享五日状态转移反复执行作为中心机制。

### 0.3 上一问的直接答案

你的 Direct-P4 没有白跑，也不是“没有标准训练结果”。

你已经完成：

- Direct-P4 200 epoch 正式训练；
- 8,800 optimizer updates；
- 完整 val_dev 969 个样本上的 checkpoint 选择；
- checkpoint_best.pt 冻结；
- RGBN-MAE、NDVI-MAE、long-horizon MAE、逐时距 MAE 与 Persistence 对照。

你尚未完成的是：

- 用冻结 checkpoint 在公开论文主测试轨道 OOD-t chopped 上只做推理和评分；
- 因此尚无可以填入 Table 1 本文行的 R²、RMSE、NSE、绝对 bias、Outperformance、RMSE25；
- Rollout-P4 尚未完成正式训练、验证选模和公开主测试。

外部模型不需要重训。Contextformer、PredRNN、SimVP、Earthformer 等已发表数值可以直接引用；需要补跑的是我们自己的 Direct/Rollout 推理和评分，而不是别人的训练。

---

# 1. 用最直白的比喻理解我们的工作

假设要预测一本“未来 100 天地表相册”。

## 1.1 普通未来影像预测器

它看完前 10 张照片，再把后 20 张照片直接画出来。

它可能画得很好，但论文通常主要问：

> 后 20 张画得准不准？

模型内部当然也有特征，但不一定要求这些特征构成一个明确、可重复推进的“地表状态”。

## 1.2 概率生成模型

它看完历史后，画出多套可能的未来相册。

它主要问：

> 未来有多种可能时，能否给出清晰、多样且概率合理的结果？

VegeDiff 和 EO-WM 更接近这一类。

## 1.3 VegSim 式情景模拟器

它先把一个地块压成一条平均 NDVI 历史，再维护一个潜在植被状态。每给一步天气，就让状态往前走一步，并输出未来 NDVI 分位数。

它主要问：

> 同一地块在不同天气情景下，平均植被轨迹会怎么变化？

这已经非常接近真正的“天气受控潜状态推演”。

## 1.4 ObsWorld 想做的事情

ObsWorld 不把整个地块压成一个平均数，而是维护一个 16×16 的空间状态 token 网格。每个 token 有 256 维，用来保存地块不同位置的预测信息。

模型每五天做一次：

~~~text
当前空间状态
  + 这五天的降水、温度、VPD、太阳辐射
  + 日历、时间跨度、地形
  → 下一个空间状态
  → 解码成一张 128×128 的 RGBN 未来观测
~~~

同一个转移函数连续执行 20 次，得到 100 天轨迹。

因此，ObsWorld 不只是问“最后的图像准不准”，还问：

- 同一个五日转移能否反复使用？
- 它会不会越滚越崩？
- 天气换错后，状态和预测是否按预期变化？
- 相比不递推的 Direct，对等预算下这种状态过程是否真的有价值？

这四个问题才是当前论文区别于普通预测器的关键。

---

# 2. “模拟真实世界发生了什么”现在应该怎样理解

## 2.1 真实物理状态、卫星观测和模型状态不是同一件事

可以把真实过程写成：

~~~text
不可直接观测的真实地表状态 S_t
  --受到天气和地理环境影响-->
真实地表状态 S_{t+1}
  --经过传感器、太阳角度、轨道、云等观测过程-->
卫星图像 O_t
~~~

我们只有 O_t、部分天气和地理字段，没有 S_t 的真值标签。

因此，任何纯公开遥感数据训练的方法都不能严谨声称：

> 我的 z_t 就是唯一正确的真实地表状态 S_t。

当前 ObsWorld 学到的是 predictive state（预测状态）：

> z_t 是历史观测的一个内部摘要；只要它能够在外生驱动下产生准确、稳定、可检验的未来观测，它就具有预测意义。

形式上：

~~~text
z_0 = I(O_{1:10}, mask)
z_{k+1} = F(z_k, D_{k:k+1}, C_k, G, Δt_k)
Ô_{k+1} = H(z_{k+1})
~~~

其中：

- I 是历史状态初始化器；
- F 是共享五日受控转移；
- H 是 RGBN 观测解码器；
- D 是 physical4 外生驱动；
- C 是日历信息；
- G 是地形/地理先验；
- Δt 是时间跨度。

## 2.2 “真实”体现在哪里

当前方法中的“真实”不是指有一个真实潜状态标签，而是指：

1. 状态由真实历史卫星观测初始化；
2. 转移由真实气象轨迹和真实地理背景约束；
3. 每个未来状态都必须解码回真实卫星能观测的 RGBN 空间；
4. 预测最终由真实未来卫星观测和有效像素 mask 评分；
5. 可以用错位、打乱、置空天气检查模型是否真的使用外生驱动。

所以更严谨的说法是：

> **ObsWorld 学习“由真实观测约束的地表预测状态过程”，而不是声称恢复“真实世界的唯一隐变量”。**

## 2.3 这是否离“模拟真实世界”越来越远

不是完全远离，而是把过强、无法验证的承诺改成了可检验的承诺。

旧说法：

> 恢复真实地表状态，模拟真实世界发生了什么。

问题是无法证明“真实状态”。

新说法：

> 从历史观测构建足以预测未来的空间状态，让它在真实外生驱动下持续推进，并要求每一步都能接受未来真实观测检验。

后者更窄，但更科学，也更容易说服审稿人。

---

# 3. 当前代码实际上完成了什么样的世界模型接口

以下不是设想，而是当前代码事实。

## 3.1 I：空间预测状态初始化

ObsWorldV2Core 只读取历史 x_context 和 context_mask，不读取未来 target。

当前正式配置：

- 历史 10 帧；
- 输入为 Blue、Green、Red、NIR 四通道；
- 历史帧先经过 Stage1.5 初始化的编码器和 state projector；
- 形成 16×16 个空间状态 token；
- 每个 token 为 256 维；
- 根据有效像素覆盖率聚合历史状态。

这意味着 z_0 不是一个地块级标量，而是一张低分辨率空间状态场。

## 3.2 F：共享五日受控转移

Rollout-P4 的每一步都读取：

- 上一步模型自己预测的状态；
- 当前五日 physical4：
  - precip_sum_5d（五日累计降水）；
  - temp_mean_5d（五日平均温度）；
  - vpd_mean_5d（五日平均饱和水汽压亏缺）；
  - srad_sum_5d（五日累计太阳辐射）；
- 日历信息；
- elapsed time（经过时间）；
- token 对齐的地形/地理信息。

同一个 F 被使用 20 次。代码明确禁止未来 RGBN target 进入转移，并且 teacher_forcing_future_state=false。

这是一条真正的开放循环预测链：

~~~text
z0 → z1 → z2 → … → z20
~~~

而不是每一步偷偷使用真实未来状态。

## 3.3 H：逐状态 RGBN 观测出口

每一个 z_k 都能由共享 EarthNet observation decoder 解码成：

- 4 通道 RGBN；
- 128×128 空间分辨率；
- 进而计算 NDVI。

因此状态不是只能在内部自说自话；它必须在观测空间中接受检查。

## 3.4 Direct-P4：论文最关键的结构对照

Direct-P4 与 Rollout-P4 共享：

- 相同历史初始化；
- 相同 Stage1.5 权重；
- 相同 physical4；
- 相同日历、地理和时间；
- 相同 transition 参数；
- 相同 decoder；
- 相同训练数据和预算。

区别只有：

- Direct：每个 horizon 都从 z_0 出发，读取截至该时距的驱动前缀，一次预测终点；
- Rollout：把前一步预测状态交给下一步，连续推进。

因此 Direct vs Rollout 不是普通 baseline 对比，而是在问：

> **“显式共享状态过程”相对“直接多时距预测”到底有没有独立价值？**

## 3.5 φ 的当前真实边界

Stage1.5 使用真实 φ 做过条件化预训练，但当前 EarthNet2021x Stage2：

- 数据文件有日期、瓦片/位置、产品标识和质量信息；
- 当前 loader 没有把它们构造成与 Stage1.5 完全对齐、经过验证的逐帧真实 φ；
- 精确太阳角、S1 轨道/入射角也不是当前 EarthNet Stage2 的现成兼容输入；
- 正式代码因此使用固定 neutral φ；
- Stage2 新 RGBN decoder 不读取目标 φ。

所以当前只能说：

> Stage1.5 提供了 φ 条件化的预训练初始化权重，其是否有益要由 Stage1 vs Stage1.5 预测消融证明。

当前不能说：

- Stage2 实时感知真实采集条件；
- 推理时输入不同 φ 就能渲染同一地表的不同观测；
- z 已经完全去除了所有成像因素；
- 当前模型已经实现多传感器观测算子。

## 3.6 U 的当前边界

U 是 observation correction（观测校正），不是 uncertainty（不确定性）。

当前 no-U 主模型：

- 会把未来状态解码成可验证观测；
- 不会在中途看到新观测后自动校正后续状态。

U 的基础代码虽已接通，但还没有正式训练与主结果。它不是当前世界模型身份成立的必要条件，也不应阻塞 Direct/Rollout 主实验。

---

# 4. 其他工作究竟在讲什么

下表不是为了证明“别人都不行”，而是准确划分每条路线的中心问题。

| 工作/路线 | 它眼中的“世界” | 核心输出与叙事 | 与 ObsWorld 的主要区别 |
|---|---|---|---|
| PredRNN（NeurIPS 2017） | 视频中的时空外观与运动记忆 | 用 ST-LSTM 递归预测未来视频帧 | 有递归记忆，但不是针对 EO 外生驱动与空间地表状态设计，也没有本文这种同模块 Direct 配对检验 |
| SimVP（CVPR 2022） | 可由 CNN 直接建模的时空序列 | 用简单 CNN 端到端预测未来视频 | 强调简单、准确的直接视频预测，不强调显式受控状态过程 |
| Earthformer（NeurIPS 2022） | 高维地球系统时空场 | Cuboid Attention 高效建模时空依赖 | 强调通用时空 Transformer；不是本文的外生驱动共享五日状态转移命题 |
| EarthNet2021（CVPRW 2021） | 天气条件下未来地表卫星图像 | 把地表预测定义成 guided video prediction（引导视频预测） | 它是任务/数据协议，不是本文独有方法 |
| Contextformer（CVPR 2024） | 高分辨率植被动态 | 空间 backbone + 时间 Transformer + 天气，预测像素级 NDVI | 是最重要确定性预测基线；它以预测准确度为中心，不专门证明一个共享短步状态过程 |
| VegeDiff（预印本） | 天气与静态环境下多种可能的植被未来 | 潜扩散生成概率性未来，重点是不确定性与清晰度 | 它强在概率未来；当前 ObsWorld 是确定性的，不能在不确定性上与其争首 |
| TerraMind（ICCV 2025） | 多模态 EO 表征与任意模态生成 | any-to-any 多模态基础模型与下游迁移 | 强在大规模预训练和跨模态生成，不是长期受控地表动力学 |
| Remote Sensing-Oriented World Model（预印本 2025） | 中心瓦片周围未见空间 | 根据方向指令生成相邻空间瓦片 | 它是空间外推，不是时间状态演化 |
| RS-WorldModel（预印本 2026） | 遥感语义变化与文本指定未来场景 | 变化问答 + 文本引导未来场景生成 | 强在语言理解、可控生成和大模型统一，不是天气控制的逐五日物理状态推进 |
| Earth-o1（预印本 2026） | 连续三维大气状态 | 从非规则原始观测学习无网格大气动力学 | 属于大气数字孪生方向，任务和尺度与地表 RGBN 预测不同 |
| EO-WM（预印本 2026） | 稀疏观测下不确定、受天气驱动的地表未来 | 物理信息条件的视频扩散；气候态/异常/累计胁迫；极端天气响应诊断 | 强在概率多光谱生成和物理天气响应；不是把共享五日 F 连续执行并用 Direct 对照验证 |
| VegSim（预印本 2026） | 气象情景下的潜在植被状态 | 从稀疏 NDVI 与天气初始化状态，用 GRU 递推并输出 NDVI 分位数 | 是概念最近邻；但其观测是 minicube 平均 NDVI 标量，当前不生成地块内部完整 RGBN 空间轨迹 |
| ObsWorld（本文） | 由卫星历史约束、可预测未来观测的空间地表状态 | 16×16 空间状态，physical4 驱动的共享五日 F，20 步开放循环，逐步 RGBN 解码，Direct 配对检验 | 目标是把高分辨率 EO 预测与显式、可诊断的空间状态过程连接起来 |

---

# 5. 必须认真面对的三个最近邻

## 5.1 VegSim：当前概念上最接近的工作

VegSim 已经明确完成：

- 从稀疏 NDVI 历史和过去天气推断潜在植被状态；
- 用未来天气驱动 GRU 状态递推；
- 每一步输出 NDVI 分位数；
- 替换未来天气即可做情景模拟；
- 在 val、OOD-s、OOD-t、OOD-st 上评估；
- 明确说明情景输出不是因果效应。

因此本文绝对不能再写：

- 首个使用潜状态的植被世界模型；
- 首个天气受控递推；
- 首个情景模拟；
- 现有方法都只会一次性预测，没人做 latent rollout。

ObsWorld 能够与 VegSim 切开的地方是：

1. **空间状态而非地块均值状态**
   VegSim 先对每个 minicube 的有效像素求平均 NDVI，形成一条稀疏标量时间序列；ObsWorld 保留 16×16 空间 token 状态。

2. **完整多光谱观测而非单一平均 NDVI**
   VegSim 输出 NDVI quantiles；ObsWorld 输出 128×128 RGBN，再从中派生 NDVI，因此必须保留地块内部异质性和光谱一致性。

3. **严格配对结构检验**
   ObsWorld 用共享参数、共享输入、共享预算的 Direct-P4 对照，专门检验递推状态过程；VegSim 论文没有给出这种 matched direct-vs-rollout 结构对照。

4. **预训练空间状态初始化**
   ObsWorld 使用 SSL4EO Stage1/1.5 的空间编码权重初始化；但这只能作为待消融证明的辅助优势，不能预先当作已证贡献。

最危险的审稿意见会是：

> “这只是把 VegSim 从平均 NDVI 扩展成空间 RGBN。”

要说服审稿人，不能只靠文字回答，必须用以下结果回答：

- Rollout-P4 相对 Direct-P4 的长时距证据；
- 空间预测与地块内部异质性的可视化/分层指标；
- true/no/shuffled/time-shifted weather 的响应检验；
- Stage1.5 初始化消融；
- 参数量与计算量，说明不是简单扩大模型。

如果这些结果没有完成，VegSim 会显著削弱我们的世界模型新颖性。

## 5.2 EO-WM：完整多光谱概率预测的强竞争者

EO-WM 与本文共享：

- EarthNet2021 10→20 任务；
- 四通道多光谱输出；
- 稀疏观测和天气驱动表述；
- 世界模型定位；
- 天气响应诊断。

EO-WM 的中心是：

- 视频 diffusion（扩散）生成；
- climatology-anomaly decomposition（气候态—异常分解）；
- cumulative physical stress（累计物理胁迫）；
- 极端夏季与季节配对天气响应；
- 概率未来。

ObsWorld 不应在“首次物理天气条件”或“首次世界模型”上与它争论。

可区分点是：

- EO-WM 联合生成未来潜视频；ObsWorld 显式保存 z_0→z_1→…→z_20 的空间状态链；
- ObsWorld 的同一个 F 被反复调用；
- ObsWorld 用 Direct-P4 做严格结构对照，检验“状态推进”相对“一次预测终点”是否有价值；
- ObsWorld 更轻量、确定性、可逐步诊断，但当前没有 EO-WM 的概率建模优势。

所以对 EO-WM 的合理表述是：

> EO-WM 代表“物理信息条件的概率多光谱视频生成”；ObsWorld 研究“共享短步空间状态转移能否构成稳定、可验证的长期预测过程”。

## 5.3 Contextformer：公开精度主表必须面对的基线

Contextformer 不是世界模型包装，而是一个非常强的高分辨率植被预测器：

- 使用空间上下文；
- 使用气象时间序列；
- 预测局部像素植被动态；
- 有清晰的 OOD-t 公开主测试与 evaluator；
- 已公布完整 Table 2 数值。

本文不能说“我们有天气而 Contextformer 没有”。

本文与它的合理区别是：

> Contextformer 回答“如何更准地预测高分辨率植被”；ObsWorld 在同样必须保证预测能力的基础上，进一步检验一个可复用的空间状态转移过程是否成立。

如果 ObsWorld 的公开预测精度太差，世界模型叙事也救不了它；如果精度接近或更好，同时 Rollout/driver 证据成立，才有区别。

---

# 6. 建议冻结的新中心叙事

## 6.1 推荐标题

当前标题可以进一步突出“空间”这一真正区别：

> **ObsWorld: Shared-Transition Spatial Predictive States for Long-Horizon Earth Observation Forecasting**

中文：

> **ObsWorld：面向长期地球观测预测的共享转移空间预测状态模型**

是否保留标题中的 World Model（世界模型），可以在结果出来后决定。若 Rollout 与驱动证据通过，可写：

> **ObsWorld: A Shared-Transition Spatial Predictive-State World Model for Long-Horizon Earth Observation Forecasting**

## 6.2 引言应按这个逻辑展开

### 第一步：承认现有方法已经很强

现有工作已经能：

- 预测未来多光谱图像；
- 使用天气和地理条件；
- 输出高分辨率 NDVI；
- 建模概率未来；
- 进行气象情景模拟；
- 甚至使用“世界模型”名称。

所以缺口不能写成“没人预测真实世界”。

### 第二步：指出仍未被同时解决的问题

> 高分辨率 EO 方法通常以输出未来序列为终点；最接近的潜状态情景模型又把空间影像压缩为地块级 NDVI。仍缺少一种模型，在保留地块内部空间结构和完整多光谱可验证性的同时，把长期预测表示为同一短步受控状态转移的重复执行，并用严格配对对照检验这种状态过程是否真的有价值。

### 第三步：给出 ObsWorld

ObsWorld：

- 从历史 RGBN 构建空间预测状态；
- 用 physical4、日历、时间和地形控制共享五日 F；
- 开放循环 20 步；
- 每一步解码 RGBN；
- 用 Direct-P4 隔离递推结构贡献。

### 第四步：给出证据，而不是只给名字

需要证明：

- 公共主测试精度可信；
- Rollout 不因误差累积迅速崩溃；
- Rollout 相对 Direct 有收益或至少非劣且长时距更稳；
- 模型确实使用天气驱动；
- Stage1.5 初始化确实有预测效用；
- 空间状态保留局部差异，而不是只拟合地块均值。

## 6.3 推荐贡献写法

在结果出来前，最多写成：

1. **空间预测状态表述**
   我们把长期 EO 预测表示为从稀疏多光谱历史初始化空间状态、再由外生驱动推进并逐步解码的过程，保留地块内部空间结构和完整 RGBN 可验证性。

2. **共享短步受控转移与严格配对检验**
   我们设计共享五日转移进行 100 天开放循环，并构造参数、输入、初始化、解码器和预算匹配的 Direct 对照，隔离状态递推本身的作用。

3. **面向世界模型能力的证据链**
   我们结合公开 OOD-t 预测、时距曲线、驱动负对照、空间诊断和预训练初始化消融，判断模型是否学到了可复用、受驱动的预测状态过程。

只有结果通过后，才能把“设计/检验”升级成“改善/实现”。

---

# 7. 怎样才能说服审稿人

## 7.1 单纯 Table 1 精度不够

Table 1 只能证明：

> 模型会预测未来。

它不能单独证明：

> 模型维护了有用的世界状态。

因为 Contextformer、SimVP、PredRNN 也能获得很好的预测分数。

## 7.2 真正的核心证据链

| 主张 | 必须实验 | 理想通过条件 | 失败后怎么写 |
|---|---|---|---|
| 模型具有基本预测技能 | OOD-t Table 1 | 接近或超过强公开基线 | 若差距过大，先修预测，不能靠 world model 名称弥补 |
| 共享状态递推有用 | Rollout-P4 vs Direct-P4 | 总体更好，或总体非劣且长时距/OOD 更稳 | 若明显更差，只能称结构探索，不能称有效状态动力学 |
| 误差没有快速累积 | 5–100 天 Figure 2 | Rollout 曲线不在早期迅速发散 | 若发散，修 curriculum/transition |
| 天气不是装饰 | true/no/shuffled/time-shifted D | 正确天气最好，错位天气显著变差 | 若无差异，不能把外生驱动作为贡献 |
| 空间状态确有意义 | 空间误差图、局部异质性样本、RGBN/NDVI | 能保留地块内部差异和局部变化 | 若只能预测均值，无法与 VegSim 拉开 |
| Stage1.5 有用 | Stage1-init vs Stage1.5-init | 最终预测、收敛或 OOD 至少一项稳定改善 | 若无收益，Stage1.5 降为工程预训练，不列核心贡献 |
| U 有用 | day25/day50 reveal | 胜过强在线更新基线 | 未完成时不进入标题、摘要和主表 |

## 7.3 最关键的说服句

若实验通过，最有力的结论不是：

> 我们模拟了真实地球。

而是：

> **在保留像素级空间与多光谱可验证性的条件下，一个共享、外生驱动的短步预测状态转移能够稳定推进 100 天，并相对严格配对的非递推预测器在长期或分布外测试中获得可测量收益。**

这句话每一部分都有对应实验，审稿人可以验证或反驳，因此比宏大的“真实世界模拟”更有力量。

---

# 8. 上一问：现有准确数值到底在哪里

## 8.1 Direct-P4 checkpoint 选择结果

这些是已经完成、可以确认的准确数值：

| Direct-P4 候选 | val_dev RGBN-MAE ↓ | NDVI-MAE ↓ | long-horizon MAE ↓ | skill vs Persistence ↑ |
|---|---:|---:|---:|---:|
| checkpoint_best.pt | **0.0331381** | 0.1087442 | **0.0367183** | **19.22%** |
| epoch100 / step4400 | 0.0344239 | 0.1169737 | 0.0377538 | 16.09% |
| epoch150 / step6600 | 0.0334920 | 0.1097534 | 0.0370541 | 18.36% |
| epoch200 / step8800 | 0.0331626 | **0.1085097** | 0.0368423 | 19.16% |

冻结选择：

- checkpoint：checkpoint_best.pt；
- 完整 val_dev 样本数：969；
- 选择规则：RGBN-MAE 最小；
- SHA256：1158ffe6644e6a05345cba3fa56ee73af8d1390a2eb078b4b0bc3a94746f91d2。

epoch200 的 NDVI-MAE 略低，但不能看完结果后把预先规定的 RGBN-MAE 选模规则改掉。

## 8.2 已完成的开发集诊断

| 指标 | 数值 |
|---|---:|
| RGBN-MAE ↓ | **0.0331** |
| NDVI-MAE ↓ | **0.1087** |
| Persistence-MAE ↓ | 0.0410 |
| Skill vs Persistence ↑ | **19.22%** |
| 60–100 天 long-horizon MAE ↓ | **0.0367** |
| day25 RGBN / NDVI-MAE ↓ | 0.0302 / 0.0948 |
| day50 RGBN / NDVI-MAE ↓ | 0.0330 / 0.1133 |
| day100 RGBN / NDVI-MAE ↓ | 0.0424 / 0.1425 |

这些数值不是没体现，而是应该放在：

- checkpoint 选择表；
- 开发集诊断表；
- Figure 2 开发版时距曲线。

它们不能填进公开主表的 RMSE、R² 或 Outperformance 列，因为：

- val_dev 与 OOD-t 不是同一测试集；
- MAE 与 RMSE 不是同一指标；
- 当前 RGBN 有效像素汇总与 Contextformer 的植被 mask/evaluator 不同；
- 19.22% 是相对 Persistence-MAE 的下降，不是论文定义的 Outperformance。

把 0.0331 写到 Contextformer 0.14 的 RMSE 同列，会看起来领先很多，但这是错误比较。

---

# 9. Table 1 可以直接使用的已发表数值

以下数值直接来自 Contextformer CVPR 2024 Table 2，不需要我们重新训练外部模型。

公开主测试是 OOD-t chopped，并使用其植被像素、有效观测和聚合 evaluator。

| 方法 | R² ↑ | RMSE ↓ | NSE ↑ | 绝对 bias ↓ | Outperf ↑ | RMSE25 ↓ | Params |
|---|---:|---:|---:|---:|---:|---:|---:|
| Persistence | 0.00 | 0.23 | -1.28 | 0.17 | 21.8% | 0.09 | 0 |
| Previous year | 0.56 | 0.20 | -0.40 | 0.14 | 19.3% | 0.18 | 0 |
| Climatology | 0.58 | 0.18 | -0.34 | 0.13 | — | 0.16 | 0 |
| ConvLSTM | 0.58±0.01 | 0.16±0.00 | -0.13±0.02 | 0.11±0.00 | 53.1±1.2% | 0.11±0.00 | 1.0M |
| Earthformer† | 0.52 | 0.16 | -0.13 | 0.10 | 56.5% | 0.09 | 60.6M |
| PredRNN | 0.62±0.00 | 0.15±0.00 | 0.03±0.00 | 0.10±0.00 | 64.7±1.2% | 0.10±0.00 | 1.4M |
| SimVP | 0.60±0.00 | 0.15±0.00 | 0.03±0.01 | 0.09±0.00 | 64.1±1.0% | 0.10±0.00 | 6.6M |
| Contextformer | 0.62±0.00 | 0.14±0.00 | 0.09±0.01 | 0.09±0.00 | 66.8±0.3% | 0.08±0.00 | 6.1M |
| Direct-P4 | 【待 OOD-t 同协议评分】 | 【待填】 | 【待填】 | 【待填】 | 【待填】 | 【待填】 | 【待统计】 |
| ObsWorld Rollout-P4 | 【待训练与 OOD-t 同协议评分】 | 【待填】 | 【待填】 | 【待填】 | 【待填】 | 【待填】 | 【待统计】 |

† Contextformer 论文对 Earthformer 只重训一个 seed。

## 9.1 为什么外部数值现在可以填，而我们的行仍然待填

外部行已经由论文作者在 OOD-t chopped 公开协议上计算。

我们的 Direct 训练和 val_dev 选模虽已完成，但还没有在同一个 OOD-t chopped 轨道上计算上述六项指标。

因此正确的主表状态是：

| 环节 | 状态 | 是否需要重新训练 |
|---|---|---|
| Direct-P4 200 epoch 训练 | 已完成 | 否 |
| Direct-P4 完整 val_dev 选模 | 已完成 | 否 |
| Direct-P4 OOD-t 推理与评分 | 未完成 | 不训练，只推理 |
| 外部公开基线 | 已有发表数值 | 不复现 |
| Persistence/Climatology 的本地 Outperf 支持 | 尚需同协议生成/核验 | 非学习基线，不训练 |
| Rollout-P4 | 未完成 | 需要训练本文主模型 |

## 9.2 EarthNet2021x 与论文名称的准确说明

Contextformer 官方仓库明确写明：

- 论文中数据集名称是 GreenEarthNet；
- 代码开发阶段还使用 earthnet2021x 和 en21x 名称；
- 论文推理示例使用 ood-t_chopped。

因此：

- 我们仍可把训练数据称为 raw EarthNet2021x；
- 引用 Contextformer 数值时必须在表注中说明公开 OOD-t chopped 协议；
- raw ood 与 ood-t_chopped 不能当成同一个目录；
- 想把我们的行与公开数值放在同一主表，必须让我们自己的 checkpoint 在 ood-t_chopped 上同协议评分。

这不是要求重训 Direct，也不是把项目改成另一个训练数据集；它是在训练完成后增加一个公开可比测试轨道。

---

# 10. 你接下来具体应该怎么做

## 10.1 明确不要做的事情

现在不要：

- 重训 Direct-P4；
- 为了填主表重新训练 Contextformer；
- 重新训练 PredRNN、SimVP、Earthformer；
- 把 0.0331 当成 OOD-t RMSE；
- 在 Rollout 完成前分散去做 full24、Partition、U 或额外数据集；
- 直接宣称 SOTA。

## 10.2 主线最短路径

### 步骤 A：冻结 Direct，保持不动

保留：

- checkpoint_best.pt；
- selected_checkpoint.json；
- checkpoint SHA256；
- 完整 val_dev bundle。

Direct 的训练已经结束。

### 步骤 B：打通 OOD-t chopped 数据与 manifest

当前机器已有 raw train/iid/ood/extreme/seasonal，但公开 Contextformer 主表使用 ood-t_chopped。

需要：

1. 只下载 ood-t_chopped，不下载或重训外部模型；
2. 给当前 manifest/loader 增加显式 chopped split 支持；
3. 冻结该清单、样本数和 hash；
4. 确认预测导出器与官方 mask/target 约定一致。

当前代码在这一点仍有 split/manifest 缺口，所以现在不应给服务器直接运行一个假装完整的正式评分命令。下一轮应先把该代码契约修好并测试，再给一键命令。

> [!NOTE]
> **对 2026-07-19 新增评估代码的复核结果：不是“整套评估都没实现”。**
>
> 当前代码已经具备以下组成部分：
>
> - `eval/earthnet_table1.py` 与 `eval/export_earthnet_score_targets.py`：把 raw NetCDF 目标转换为 EarthNetScore 所需格式，并记录来源信息；
> - `eval/export_earthnet_table1_baseline.py`：可在 raw IID/OOD 等划分上导出 Persistence（持久性）与 Climatology（气候态）基线；
> - `eval/stage2_result_statistics.py`：可计算逐时距统计和按 tile（瓦片）聚类的配对 bootstrap（自助法置信区间）；
> - `eval/export_greenearthnet_predictions.py` 与 `eval/eval_greenearthnet_official.py`：已经提供预测导出和官方评分器的基本骨架。
>
> 真正尚未闭合的不是“所有评估代码”，而是：`ood-t_chopped` 的显式 split/manifest 角色、数据加载器对该轨道的端到端支持、一次小规模导出—评分 smoke test（冒烟测试）与官方结果 parity check（一致性核验），以及该轨道上用于 Outperformance（超越率）的 Climatology 分数。换句话说，下一步应补齐这一小段协议桥接，**不需要推倒重写评估系统，也不需要重训 Direct 或外部方法**。现有 raw IID/OOD 评分仍可作为本文内部诊断或补充实验，但不能冒充公开论文 Table 1 的 `OOD-t chopped` 数值。

### 步骤 C：Direct 只做正式推理与评分

使用已经选中的 checkpoint_best.pt：

1. 对 OOD-t chopped 导出预测；
2. 计算 R²、RMSE、NSE、绝对 bias、RMSE25；
3. 生成或核验 Climatology score，计算 Outperformance；
4. 把六个数值填入 Table 1 的 Direct 行。

这一步不更新任何模型权重。

### 步骤 D：正式训练 Rollout-P4

Rollout 使用与 Direct 相同：

- physical4；
- Stage1.5 初始化；
- train_dev / val_dev；
- 200 epoch 等价预算；
- 8,800 updates；
- checkpoint 候选与选择规则；
- OOD-t evaluator。

然后补：

- Rollout Table 1 行；
- Direct vs Rollout 的逐时距曲线；
- 配对 bootstrap；
- driver 负对照。

### 步骤 E：形成第一套完整主实验后冻结主干

最小完整结果是：

- 外部论文值；
- Direct-P4；
- Rollout-P4；
- Persistence/Climatology；
- Figure 2；
- true/no/shuffled/time-shifted D 中至少核心三项。

完成后再决定是否补 3 seed。不要在此之前开启 full24 与 U 大训练。

## 10.3 你本人现在需要记住的最简单版本

> **Direct 已经训练完，不动；外部模型不重跑；下一步先让代码支持 OOD-t 正式测试，同时训练 Rollout。最后只把我们两个 checkpoint 放到同一公开 evaluator 上评分。**

---

# 11. 3 图 3 表怎样围绕新叙事闭环

## Figure 1：空间预测状态世界模型总图

必须明确：

- 历史 RGBN → 空间 z_0；
- physical4/G/C/h → 共享五日 F；
- z_1→…→z_20；
- 每一步 z → RGBN；
- Direct 虚线分支；
- Stage1.5 只作为初始化；
- neutral φ；
- U 灰色可选，不纳入当前结果。

逻辑意义：

> 让读者一眼看出本文不是一次性生成 20 张图，而是在推进一个空间状态过程。

## Table 1：公开 OOD-t 预测能力

内容：

- 已发表 Persistence、Climatology、ConvLSTM、Earthformer、PredRNN、SimVP、Contextformer；
- Direct-P4；
- Rollout-P4。

逻辑意义：

> 证明这种状态过程不是以牺牲基本预测能力为代价。

## Figure 2：5–100 天时距曲线

曲线：

- Persistence；
- Direct；
- Rollout；
- 若公开论文无逐时距数值，不强行伪造 Contextformer 曲线。

逻辑意义：

> 判断递推何时开始累积错误，以及长期是否比 Direct 更稳。

## Table 2：结构与驱动主消融

建议紧凑包含：

- Direct + true D；
- Rollout + true D；
- Rollout + no D；
- Rollout + shuffled D；
- Rollout + time-shifted D；
- 可选 Stage1-init vs Stage1.5-init。

逻辑意义：

> 分别证明状态递推和外生驱动不是装饰。

## Figure 3：空间轨迹与失败模式

展示：

- day 5/25/50/75/100；
- Ground truth、Direct、Rollout、误差图；
- RGB 与 NDVI；
- 规则化选样，不人工只挑最好案例；
- 可增加地块内部不同区域的 NDVI 轨迹。

逻辑意义：

> 直接展示 ObsWorld 相对 VegSim 式地块平均轨迹的空间信息优势。

## Table 3：预训练与状态机制消融

建议：

- Stage1.5 + Direct + P4；
- Stage1.5 + Rollout + P4；
- Stage1 + Rollout + P4；
- 可选 no-G 或 no-h；
- full24 不阻塞，可放附录。

逻辑意义：

> 判断收益来自共享状态、Stage1.5 初始化还是额外输入。

---

# 12. AAAI 是否还有希望

有希望，但不是“只要叫世界模型就有希望”。

## 12.1 足以形成有竞争力论文的条件

至少满足：

1. Direct 和 Rollout 都有公开同协议可信分数；
2. Rollout 相对 Direct 更好，或总体非劣且长时距/OOD 更稳；
3. 正确天气显著优于 no/shuffled/time-shifted weather；
4. 空间 RGBN 结果展示出地块内部结构，而不是只预测平均季节曲线；
5. Stage1.5 至少在预测、收敛或 OOD 中有一项稳定效用；
6. 文中不夸大真实状态、因果、不确定性和 φ。

如果这些成立，文章可以被定位成：

> **一个把高分辨率多光谱 EO 预测重构为可检验空间状态过程的紧凑世界模型。**

## 12.2 哪些结果会使主线失效

- 只有 Direct 结果，没有 Rollout；
- Rollout 明显弱于 Direct；
- 换错天气预测不受影响；
- 公开主测试远低于强基线；
- 空间输出只是模糊季节均值；
- 论文仍声称首个天气世界模型；
- 把 Stage1.5 φ 写成当前 Stage2 的真实实时条件。

若只有 Table 1 精度而没有机制证据，论文更像一个 EarthNet predictor（预测器），而不是有说服力的世界模型。

---

# 13. 审稿人最可能问什么

## Q1：这不就是另一个视频预测模型吗？

回答必须是：

> 我们不仅给出未来帧，还显式保存并推进空间状态；更重要的是，我们用参数与输入严格匹配的 Direct 对照隔离了状态递推的作用，并用时距和驱动负对照验证状态过程。

证据：Direct vs Rollout、Figure 2、Table 2。

## Q2：VegSim 已经做潜状态和天气递推，你们新在哪里？

回答：

> VegSim 对每个 minicube 的有效像素求平均，建模地块级 NDVI 概率轨迹；ObsWorld 保留空间 token 状态并逐步解码完整 RGBN 场，同时用 matched Direct 对照检验共享空间状态过程。

证据：空间输出、局部异质性指标、Direct 对照。

## Q3：EO-WM 已经是物理天气驱动世界模型，你们新在哪里？

回答：

> EO-WM 侧重物理条件的视频扩散与概率天气响应；ObsWorld 侧重显式、共享、短步空间状态转移的反复执行和结构可检验性。

证据：状态链、共享 F、Direct 对照、参数量和长时距曲线。

## Q4：你们的 z 真的是地表状态吗？

不能回答“是唯一真实状态”。

正确回答：

> z 是由观测监督学习的 spatial predictive state（空间预测状态）。我们通过未来预测充分性、驱动响应和结构消融证明它有预测意义，但不声称它等于不可观测的真实物理状态。

## Q5：没有 action 为什么叫 world model？

回答：

> 本文不是强化学习式 agent world model。地球观测中，系统由天气等 exogenous forcing（外生驱动）推进；模型仍具有状态、受控动力学和观测映射三部分。我们把世界模型限定为外生驱动的地表预测状态模型。

## Q6：为什么不直接用公开 baseline 数值？

回答：

> 外部 baseline 正是直接使用已发表数值，不重训。为了公平，我们只要求自己的 Direct/Rollout 在相同 OOD-t chopped 目标、mask 和 evaluator 上评分。

## Q7：为什么 0.0331 不填进主表？

回答：

> 0.0331 是内部 val_dev 的 RGBN-MAE，公开 0.14 是 OOD-t 植被 RMSE。测试集、目标、mask 与指标都不同，不能混写。

---

# 14. 最终术语冻结

| 术语 | 推荐中文 | 当前是否可用 |
|---|---|---|
| spatial predictive state | 空间预测状态 | 主线可用 |
| shared transition | 共享转移 | 主线可用 |
| driver-conditioned rollout | 外生驱动条件推演 | 主线可用 |
| observation-grounded | 由观测约束/以观测为检验 | 可用 |
| true latent state | 真实潜状态 | 禁止 |
| acquisition-robust | 对采集条件更稳健 | 只有新 probe/消融通过后再用强表述 |
| sensor-invariant | 传感器不变 | 当前不能用 |
| scenario response | 情景响应 | 驱动扰动实验可用，不等于因果 |
| causal effect | 因果效应 | 禁止 |
| uncertainty | 不确定性 | 当前 no-U 主线没有 |
| observation correction / U | 观测校正 | 条件升级，不是当前主线 |
| digital twin | 数字孪生 | 禁止 |
| full Earth simulator | 完整地球模拟器 | 禁止 |
| SOTA | 当前最佳 | 只有同协议正式领先后可用 |

---

# 15. 可以直接用于论文沟通的一段话

> 现有地球观测预测已经覆盖高分辨率植被预测、天气条件、多模态 Transformer、概率扩散和气象情景模拟，因此 ObsWorld 不以“首次预测未来”“首次使用天气”或“首次世界模型”为贡献。本文关注一个更具体、可证伪的问题：在保留地块内部空间结构和完整多光谱观测出口的条件下，长期地球观测预测能否由一个共享的短步预测状态转移稳定构成？ObsWorld 从历史 RGBN 观测初始化空间预测状态，在紧凑物理驱动、日历和地形条件下复用同一五日转移进行 100 天开放循环，并逐步解码未来 RGBN。我们进一步构造参数、输入、初始化、解码器和预算匹配的非递推 Direct 对照，以隔离共享状态推进本身的作用。本文不声称恢复不可观测的唯一真实地表状态，而通过公开预测、长时距曲线、驱动负对照、空间诊断和预训练消融判断该预测状态过程是否真实有用。

---

# 16. 文献来源与发表状态

## 已正式发表

- Ha and Schmidhuber, World Models, NeurIPS 2018：[arXiv / official project](https://arxiv.org/abs/1803.10122)
- PredRNN, NeurIPS 2017：[NeurIPS proceedings](https://papers.nips.cc/paper_files/paper/2017/hash/e5f6ad6ce374177eef023bf5d0c018b6-Abstract.html)
- EarthNet2021, CVPR EarthVision Workshop 2021：[CVF Open Access](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/html/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.html)
- SimVP, CVPR 2022：[CVF Open Access](https://openaccess.thecvf.com/content/CVPR2022/html/Gao_SimVP_Simpler_Yet_Better_Video_Prediction_CVPR_2022_paper.html)
- Earthformer, NeurIPS 2022：[NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2022/hash/a2affd71d15e8fedffe18d0219f4837a-Abstract-Conference.html)
- Contextformer / Multi-modal Learning for Geospatial Vegetation Forecasting, CVPR 2024：[CVF Open Access](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html)
- Contextformer official code and protocol：[official GitHub](https://github.com/vitusbenson/greenearthnet)
- TerraMind, ICCV 2025：[paper](https://arxiv.org/abs/2504.11171)

## 截至 2026-07-19 的预印本/新近公开工作

- VegeDiff：[arXiv](https://arxiv.org/abs/2407.12592)
- Remote Sensing-Oriented World Model：[arXiv](https://arxiv.org/abs/2509.17808)
- RS-WorldModel：[arXiv](https://arxiv.org/abs/2603.14941)
- Earth-o1：[arXiv](https://arxiv.org/abs/2605.06337)
- VegSim：[arXiv HTML](https://arxiv.org/html/2606.21961)
- EO-WM：[arXiv HTML](https://arxiv.org/html/2606.27277)

---

# 17. 本文件的冻结结论

> **现在的 ObsWorld 不是“恢复绝对真实世界”的模型，而是“由真实卫星观测约束、在外生驱动下逐步推进、并能逐步回到完整 RGBN 观测接受检验的空间预测状态模型”。它与普通预测器的区别要由 Direct vs Rollout、长时距曲线和驱动负对照证明；它与 VegSim 的区别要由空间 RGBN 状态和局部异质性证明；它与 EO-WM 的区别在于显式共享短步状态过程而非概率视频扩散。Direct-P4 已经完成训练与 val_dev 选模，现有准确数值已全部记录；外部主表数值可以直接引用，不需复现。下一步只需打通 OOD-t chopped 同协议评分、完成 Rollout-P4，并形成第一套 Direct/Rollout 公平主实验。**


---

## 追加：2026-07-19 正式 Table 1 实现状态

正式 GreenEarthNet CVPR-2024 `ood-t_chopped` 路径已经独立接通：冻结 manifest、预检、Direct/Rollout checkpoint 推理、公开定义的 Persistence/Climatology、严格 scorer、official-evaluator parity 记录和表格汇总均有对应脚本。它不会替代本节所述的 raw EarthNet2021x 内部诊断，而是防止两套协议混表。

详见：[[68_ObsWorld_GreenEarthNet_OODt_Table1闭环_实现记录与运行指南_20260719]]。当前仍待实际生成的结果是 Direct-P4 OOD-t、Rollout-P4 OOD-t、完整 baseline 与官方 parity；在这些产物齐全前，任何 Table 1 bundle 都必须保持 provisional。
