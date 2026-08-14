# TerraState AAAI-27 摘要审计与修订建议

> 状态：PROPOSAL — 尚未写入 `paper/main.tex`  
> 日期：2026-07-27  
> 权威历史来源：
> `WorldModel2026/思路整理进展/84_ObsWorld_AAAI27文章主线_单模型方法闭环_双语标题摘要与问答_20260722.md`

## 1. 结论

作者提出的三个问题均基本成立，但需要精确表述：

1. 当前摘要并非从第二句就报告结果；前五句仍分别承担背景、问题、方法、
   训练锚定和评价设计。真正的问题是最后连续三句分别报告 Q1、Q2 和 Q3，
   使摘要的视觉重心和记忆点从方法转向数字。
2. 2026-07-22 实际上传摘要没有具体实验数字。当前版本相对提交版不仅加入结果，
   还删除了原摘要中更完整的“为什么这是世界模型”的论证，因此修改幅度确实偏大。
3. 当前英文摘要第三句已经使用 `predictive-state world model`，所以不是完全没有
   提到世界模型；但该身份只作为名称出现一次，没有成为后续机制和证据的组织轴。

因此，建议不是重新发明摘要，而是回到提交版的科学叙事，仅做两类必要修订：

- 删除已不受最终合同支持的 composition、non-degeneracy、matched-backbone 和
  shuffled/zeroed-driver 承诺；
- 用最后一个句子统一概括当前 Q1--Q3 证据。

## 2. AAAI 一手摘要锚点

| 论文 | AAAI 官方链接 | 摘要结构 | 结果位置 |
|---|---|---|---|
| ReconVLA | https://ojs.aaai.org/index.php/AAAI/article/view/38921 | 背景 → 观察到的问题 → 方法 → 机制 → 数据 → 实验 | 最后 1 句 |
| LLM2CLIP | https://ojs.aaai.org/index.php/AAAI/article/view/37427 | 背景 → 研究问题 → 框架 → 两步机制 → 效果 | 最后 2 句 |
| Model Change for Description Logic Concepts | https://ojs.aaai.org/index.php/AAAI/article/view/39008 | 问题定义 → 概念划分 → 理论贡献 → 理论结果 | 最后 1 句总结结果 |
| CADYT | https://ojs.aaai.org/index.php/AAAI/article/view/40999 | 背景 → 两个缺口 → 方法 → 理论依据 → 实现 → 实验 | 最后 1 句 |
| High-Pass Matters | https://ojs.aaai.org/index.php/AAAI/article/view/39469 | 背景 → 缺口 → 理论洞见 → 方法 → 机制 → 实验 | 最后 1 句 |
| WorldAgen | https://ojs.aaai.org/index.php/AAAI/article/view/38925 | 问题 → 缺口 → 方法 → 架构 → 测试时机制 → 效果 | 最后 2 句 |

这些例子并不说明 AAAI 存在机械的统一模板，但共同支持三个原则：

1. 结果位于摘要末尾，而不是穿插在问题和方法之间；
2. 方法型论文通常先给出缺口和解决机制，再总结效果；
3. 一个结果句完全正常；两个结果句也存在，但并非必须。

TerraState 同时需要交代 Q1、Q2 和 Q3，但这不要求写成三句。用并列结构把三类证据
压缩进最后一句，更能突出世界模型方法本身。

## 3. 当前摘要的句子角色

| 句序 | 当前职责 | 审计 |
|---|---|---|
| 1 | 遥感预测背景 | 保留，但可恢复提交版中 vegetation/agriculture/ecosystem 的具体价值 |
| 2 | endpoint accuracy 的缺口 | 保留 |
| 3 | TerraState 方法 | 保留并强化 world-model 闭环 |
| 4 | frozen future-observation encoder | 可合并到训练/验证机制句 |
| 5 | skill 与 intervention 分开报告 | 保留思想，但避免工程化措辞 |
| 6 | Q1 数字 | 与 7、8 合并 |
| 7 | Q2 数字和 CI | 与 6、8 合并 |
| 8 | Q3 数字和 CI | 与 6、7 合并 |
| 9 | 总结 | 与统一结果句合并，避免结果后再追加一层结论 |

## 4. 建议的信息顺序

1. **背景与任务**：高分辨率卫星时间序列用于理解植被和生态响应，任务是从云遮挡
   历史与气象驱动预测未来地表观测。
2. **评价缺口**：固定时域像素精度不能说明内部表示是否构成预测世界状态。
3. **可观察的失败方式**：准确预测器仍可能绕开显式状态，或对未来天气反应很弱。
4. **方法与世界模型身份**：历史状态 → 共享天气条件转移 → 未来状态 → 显式预测贡献。
5. **训练与检验机制**：未来观测状态只作训练锚点；训练后通过状态切除和天气替换
   检验同一个模型。
6. **唯一结果句**：Q1 useful skill + Q2 load-bearing + Q3 actual weather 更忠实。

## 5. 推荐英文摘要

> High-resolution satellite time series are a primary tool for monitoring
> vegetation, agriculture, and ecosystem response, and are increasingly cast
> as weather-driven forecasting: predicting future land-surface observations
> from cloud-obscured image histories and meteorological drivers. Yet such
> models are selected largely by fixed-horizon pixel accuracy, which cannot
> establish whether their internal representations act as predictive world
> states rather than one-shot features. An accurate forecaster may still route
> most of its prediction around the declared state or respond weakly to the
> supplied future weather---failures that endpoint metrics alone cannot reveal.
> We introduce **TerraState**, a testable predictive-state world model that
> infers a spatial state from cloud-masked histories, advances it with a shared
> transition conditioned on future weather, geography, and elapsed time, and
> decodes the transitioned state as an explicit contribution to the final
> forecast. A frozen future-observation encoder anchors the transitioned state
> during training, while matched post-training interventions remove the state
> contribution or replace the future weather without retraining the selected
> model. On GreenEarthNet under temporal shift, TerraState retains useful
> forecasting skill; state removal lowers forecast performance on both
> validation and OOD-t with positive paired effects whose confidence intervals
> exclude zero, while actual weather predicts the endpoint more faithfully than
> matched-donor and normalized-mean controls.

### 推荐理由

- 六句，对应六个明确的信息槽；
- 只有最后一句属于结果；
- 第四句同时完成命名、世界模型身份和核心机制；
- 与提交版前四句保持高度接近；
- 不出现 SOTA、competitive、composition、hot-dry enhancement 或因果主张；
- 不用多组小数主导摘要，但仍准确覆盖 Q1--Q3。

## 6. 推荐中文对应版本

> 高分辨率卫星时间序列是监测植被、农业与生态系统响应的重要手段，如今越来越多地
> 被建模为天气驱动的预测任务：根据受云遮挡的历史影像与气象驱动，预测未来地表
> 观测。然而，这类模型主要依据固定时域的像素精度进行选择，而该指标无法判断其
> 内部表示究竟是预测性世界状态，还是仅服务于一次预测的特征。一个准确的预测器
> 仍可能让大部分预测绕开所声明的状态，或对输入的未来天气反应很弱；这些失效仅靠
> 终点误差无法识别。我们提出 **TerraState**，一个可检验的预测状态世界模型：
> 它从云掩膜历史中推断空间状态，使用由未来天气、地理与经过时间共同条件化的共享
> 转移推进该状态，并将转移后的状态解码为最终预测中的显式贡献。训练期间，冻结的
> 未来观测编码器为转移后的状态提供锚定；训练完成后，我们在不重新训练所选模型的
> 前提下，通过移除状态贡献或替换未来天气进行匹配干预。在 GreenEarthNet 时间偏移
> 设置下，TerraState 保留了有效的预测能力；移除状态会同时降低验证集和 OOD-t 上的
> 预测表现，逐样本配对效应为正且置信区间不跨零，而真实天气比匹配供体天气和
> 归一化均值天气更忠实地预测终点。

## 7. 可选的单句数字版本

如果作者最终希望摘要保留精确数值，也应只替换最后一句，不改变前五句：

> On GreenEarthNet under temporal shift, TerraState attains
> \(R^2=0.56935\) and RMSE \(=0.15059\); state removal lowers the official
> \(R^2\) by \(0.01121\) on validation and \(0.01997\) on OOD-t, with positive
> paired effects whose 95% confidence intervals exclude zero, while replacing
> actual weather with matched-donor or normalized-mean controls increases
> endpoint loss by \(0.00257\) and \(0.01126\), respectively.

该版本统计上正确，但信息密度过高，也会把审稿人的注意力引向绝对 Q1 数值。当前更
推荐第 5 节的不带小数版本。

## 8. 与已提交摘要的修改幅度

| 内容 | 处理 |
|---|---|
| 首句任务背景 | 基本保留 |
| pixel accuracy 无法验证世界状态 | 保留 |
| persistence/composition 失败例子 | 改为 state bypass / weak weather response |
| TerraState 名称与世界模型身份 | 保留并按最终结构校准 |
| direct-versus-recursive / composition | 删除，因 Q4 非核心且无最终证据 |
| shuffled/zeroed driver | 改为最终 matched-donor / normalized-mean controls |
| matched-backbone 比较 | 删除，release-level provenance 不完整 |
| non-degenerate / composition-consistent | 删除 |
| 最终证据 | 新增一个统一结果句 |

这属于“保留科学问题和方法身份、更新已经变化的证据合同”，而不是更换论文叙事。

## 9. 写入门槛

本文件只是建议稿。获得作者确认前：

- 不修改 `paper/main.tex` 的摘要；
- 不修改上传系统中的摘要；
- 不把建议版本视为新的冻结文本；
- 可以继续进行 Introduction 的只读结构审计，但不得让 Introduction 与尚未批准的
  摘要形成两套主线。

