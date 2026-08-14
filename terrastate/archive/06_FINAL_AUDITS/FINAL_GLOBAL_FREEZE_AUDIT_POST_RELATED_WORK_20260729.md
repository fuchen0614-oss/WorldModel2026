# TerraState AAAI-27 全文最终冻结审计

**日期：** 2026-07-29  
**任务性质：** 严格只读、全文独立冻结审计  
**审计对象：** 当前投稿正文、BibTeX、PDF 与三份 Markdown 镜像  
**Figure 原则：** 图内科学内容延期；图的插入、引用、caption、位置和可读性纳入本轮

## 1. 最终判定

# NON_FIGURE_MANUSCRIPT_FROZEN_READY_FOR_FIGURE_FINALIZATION

| 等级 | 数量 | 是否阻塞 |
|---|---:|---|
| P0 | **0** | 否 |
| P1 | **0** | 否 |
| P2 | **4** | 否 |
| Deferred Figure | 既有历史条目须按当前 2026-07-29 图稿重新验收；本轮未新增正文阻塞项 | 否 |

独立判定依据：

- 从标题到 Conclusion，论文始终围绕“天气驱动遥感预测中的可检验预测状态世界模型”；
- Introduction 的问题和承诺、Related Work 的谱系与缺口、Method 的计算机制、Q1--Q3
  证据、Limitations 的边界以及 Conclusion 的收束逐项闭合；
- TerraState 始终是具有显式预测状态、共享天气条件转移、状态读出和冻结干预接口的
  **方法主体**，不是 benchmark 或外接评测包装；
- Equations (1)--(8)、Table 1--3、正文数字及同一最终模型的
  `40 epochs / 14,880 updates` 身份一致；
- 28 个唯一引用 key 全部定义，missing=0、duplicate=0；逐条元数据与
  citation-to-claim 支撑未发现当前错误；
- PDF 为 9 页，第 1--7 页为正文，第 8--9 页仅为 References；未见裁切、重叠、标题
  悬空或异常空白；
- 未恢复 Q4/composition、因果、反事实正确性、完整物理状态、TerraState 的控制/规划
  能力、SOTA 或严格排名主张。

四项 P2 均为可选清理：符号局部复用、Table 1 比较语境的自包含性、一处
`lower-is-better` 表达，以及没有肉眼后果的 underfull 工具警告。它们不影响方法理解、
证据可信度或冻结判定。

## 2. 审计范围、输入身份与方法

### 2.1 权威输入 SHA-256

审计进行期间，另一个并发会话在不改变正文区块的情况下更新了 Figure 1/2 资产、重新生成
PDF 并同步三份 Markdown 的 Figure 辅助块。因而任务开始时给出的 `main.tex` 和
`main.pdf` SHA 已被后续精确版本替代。本报告在写入前重新读取当前文件，并以本表的
**审计结束时 SHA** 为最终对象；正文各区块 SHA 与最初读取值完全一致。

| 文件 | 审计结束时 SHA-256 | 与任务开始值的关系 |
|---|---|---|
| `paper/main.tex` | `865c531955f348c4cde47ec9e604b5836ba580ed0b93b98dfe2f284f01bfecc9` | 任务开始值 `05a89a...` 已被并发 Figure 集成版本替代；非 Figure 区块 SHA 未变 |
| `paper/references.bib` | `4fd6cec24ab29d097ad4fa28fdd4f8479fe059ed05e5db57a3b4023a0210cf8a` | MATCH |
| `paper/main.pdf` | `5578ad0ceaa28bf6398f55443f7b67fd633a193622ac6e5631206f1445ce4242` | 任务开始值 `6d85dc...` 已被当前 Figure 资产重编译版本替代 |
| `MANUSCRIPT.md` | `e377ab934b8adfa0448ff1a1d9fbd11dc715331ad228b609bc88c9565325eedc` | 当前镜像；Figure 1/2 辅助块已同步 |
| `MANUSCRIPT_ZH.md` | `615f85a3011d2d766e224d5e15ebe27cc255a22585a776520a3d60e72953e0a0` | 当前镜像；Figure 1/2 辅助块已同步 |
| `MANUSCRIPT_ZH_FULL.md` | `760576cb0a6e68650e49109e490dcbbf8b0a4895bbc99d948e3ebcdeca938bf7` | 当前镜像；Figure 1/2 辅助块已同步 |
| `RELATED_WORK_WORLD_MODEL_EXPANSION_POST_APPLICATION_REGRESSION_AUDIT_20260729.md` | `52965eb7035b39287997797562f4119a44a055822c47594222faf8a6cb02203d` | 质量基线 |
| `FINAL_AAAI_TEXT_REVIEWER_AUDIT_20260729.md` | `3e876b34a9d3fdab5cd02a83c8f3cf350cb306072fb9b34fcee636f7facf60ce` | 质量基线 |
| `POST_REVISION_TEXT_FORMAT_REGRESSION_AUDIT_20260729.md` | `85bbe65f5d38c1f8566429c02a69f6389ba75912d2c86b792f8d09027991f76e` | 质量基线 |
| `FULL_TEXT_GLOBAL_CONSISTENCY_RECHECK_20260728.md` | `f348393c8c9e677a7bb7972a8e28705e2f1387c843401105748438f5f6a58fd1` | 质量基线 |
| `AAAI27_FORMAT_COMPLIANCE_AUDIT_20260728.md` | `c5be1da558d06a161f34a64e4aad89f5fb17b6fa4ca11de973771ea5b32d27f0` | 质量基线 |
| `evidence_workspace/CLAIM_EVIDENCE_MAP.md` | `d84ab20e8c470e732b7fd64f51575909949b3590366362067548c32d1559c88f` | 证据边界 |

### 2.2 `main.tex` 局部区块 SHA-256

以下按当前行区间直接计算，仅用于定位本轮审计所见的精确正文：

| 区块 | 当前行 | SHA-256 |
|---|---:|---|
| Abstract | 28--52（哈希口径 38--53） | `e99813974db7dbce85fda762f8bd0f8d4b47ff508a2887370a72c3f845fdf869` |
| Introduction | 54--137 | `359d8f6bfee7663ba299142a237e05ae1bab21d6b55d102ebbc622d21e6ba244` |
| Related Work | 138--203 | `0e3a39ecb50fafd7350231c96228143e13b20622c7731c28d04519880a988e1d` |
| Method | 204--527 | `ae0d7f54c3b663de8d9c102f98efca0dbfef9c37e4eed0e597b68dee668edaae` |
| Experiments | 528--699 | `0df73c6fcb6b58c9bd2b988e4201eda81345d17a8419dcdc9b6bc7bfe4a9d785` |
| Limitations | 700--715 | `fba5fefa415b4f0642337850ea4b58acecc6f834002293fce8c4dd40ca733777` |
| Conclusion | 716--730 | `dad397c4b6b6328ae53d9eaf64b332f26e00c21773305d5fe1f48863ef33d7cb` |

### 2.3 独立审计动作

本轮没有以此前 PASS 代替核验。实际执行了：

1. 完整重读 `main.tex` 和三份镜像；
2. 从标题到结论重建反向提纲和 claim--mechanism--evidence 闭环；
3. 逐式检查 Equations (1)--(8) 的符号、信息边界、训练/推理职责和实验接口；
4. 将正文、Table 1--3、captions 和镜像中的全部 Q1--Q3 数字交叉核对；
5. 独立提取引用图，并对 28 个正文引用条目进行元数据和相邻主张核验；
6. 读取现有 `main.log`、`main.blg`、`main.bbl`，未重新编译；
7. 独立解析并逐页渲染当前 9 页 PDF，检查正文/References 分界、图表、caption、页边距
   和视觉异常；
8. 对禁止叙事进行全文语义搜索，而不是只按关键词机械计数。

## 3. 全文一页式反向提纲

| 位置 | 唯一职责 | 读者在此处获得的信息 | 判定 |
|---|---|---|---|
| Title | 给出方法名、预测状态世界模型身份、天气驱动地表预测任务 | 论文不是一般遥感生成或控制模型 | PASS |
| Abstract | 任务 → 输出精度缺口 → 方法机制 → 可证伪接口 → Q1--Q3 | 一次阅读可恢复完整主线及证据边界 | PASS |
| Introduction P1 | 定义天气驱动 EO 预测任务及 EarthNet/GreenEarthNet 背景 | 输入、输出、部分观测和 forcing 语境 | PASS |
| Introduction P2 | 指出固定窗口输出精度不能单独验证内部状态 | 预测准确与预测状态成立是不同问题 | PASS |
| Introduction P3 | 以 predictive-state 语义提出科学问题并限定范围 | TerraState 的问题不是完整物理或因果模拟 | PASS |
| Introduction P4 | 概括 TerraState 计算链、训练锚定与两类干预 | 方法如何把状态主张变成可检验接口 | PASS |
| Introduction P5 | 预告 Q1--Q3 结果 | forecasting prerequisite、state contribution、weather fidelity | PASS |
| Contributions | 分别给出问题/观点、方法、证据 | 三项贡献互补且与正文一一对应 | PASS |
| Related Work P1 | Weather-conditioned EO forecasting | 从输出预测范式收紧到显式内部状态问题 | PASS |
| Related Work P2 | General world-model paradigms | 建立 state--transition--prediction 上位语境，不把能力赋给 TerraState | PASS |
| Related Work P3 | EO world models under forcing | 公平定位 EO-WM、VegSim、observability，并提出 TerraState 的互补落点 | PASS |
| Related Work P4 | Predictive-state semantics and testability | 从状态定义/监督/评估自然交给 Section 3 | PASS |
| Method 3.1 | 问题形式化、总计算链、信息边界 | TerraState 是什么以及为何是 on-path predictive-state model | PASS |
| Method 3.2 | history state、shared transition、readout/addition | 实际推理机制及 direct-per-horizon 属性 | PASS |
| Method 3.3 | GT/KD/future-state anchor、冻结身份、总损失 | 状态如何被未来观测锚定，teacher 为什么不进入推理 | PASS |
| Method 3.4 | state removal 与 weather substitution | Q2/Q3 的精确切点、固定项、最大允许结论 | PASS |
| Experiments 4.1 | 数据、指标、统计单位、训练与选模身份 | 同一最终模型和可复核协议 | PASS |
| Experiments 4.2 / Q1 | 完整 OOD-t 预测能力 | 世界模型内部主张成立前的预测前提 | PASS |
| Experiments 4.3 / Q2 | state removal 主证据，identity transition 辅助 | 状态路径承载可测预测增量 | PASS |
| Experiments 4.4 / Q3 | actual-vs-donor/mean 完整窗口 fidelity | 状态路径对 supplied weather 响应且 actual 更忠实 | PASS |
| Limitations | 表示/部署、干预边界、外部有效性 | 明确不支持因果、反事实、完整物理状态、极端特异增强和跨数据集外推 | PASS |
| Conclusion | method identity → Q1--Q3 → bounded takeaway | 内部预测状态主张从架构命名变为可检验问题 | PASS |

## 4. 主线与世界模型身份

### 4.1 从标题到结论的主线

主线可以无断点地压缩为：

> cloud-masked EO history  
> → spatial predictive state \(z_t\)  
> → shared transition conditioned on future weather, geography, and elapsed time  
> → transitioned state \(z_{t+h}\)  
> → explicit raster contribution \(r_h\)  
> → \(b_h+r_h=\widehat y_{t+h}\)  
> → frozen state-removal and weather-substitution tests  
> → Q1--Q3 evidence for a useful, forecast-bearing, weather-responsive predictive state.

Title、Abstract、Introduction、Method、Experiments 和 Conclusion 都使用这条链。没有某一节把论文
改写成单纯精度模型、独立 benchmark、控制模型或通用生成式世界模拟器。

### 4.2 为什么 TerraState 是方法主体

| 质疑 | 当前正文的回答 | 证据位置 | 判定 |
|---|---|---|---|
| 为什么不只是普通 EO predictor？ | 显式 \(z_t\)、shared \(T_\psi\)、\(O_\omega\) 与 \(r_h\) 进入最终输出 | 3.1--3.2，Eq. (1)--(4) | PASS |
| 为什么 state 不是旁路 probe？ | \(r_h\) 被加到 \(b_h\)，Q2 在该 on-path 切点移除贡献 | Eq. (4)，3.4，Table 2 | PASS |
| 为什么不是只看 output response？ | Q3 只替换 transition 的 future-weather path，同时固定 history/state/geography/readout/target | Eq. (8)，4.4，Table 3 | PASS |
| 为什么可以称 predictive state？ | 状态从历史形成、受 future-state target 锚定、由 forcing 推进并影响未来观测 | 3.1--3.3 | PASS |
| 为什么结论仍然有边界？ | 不声称 sufficient PSR、完整物理状态、因果/反事实正确性或组合动力学 | 3.1、3.4、Limitations、Conclusion | PASS |

### 4.3 Introduction → Related Work → Method → Evidence → Conclusion

| Introduction 承诺 | Related Work 建立的缺口 | Method 回应 | 实验证据 | Conclusion 收束 |
|---|---|---|---|---|
| 输出准确不足以确认内部预测状态 | EO forecasting 证据主要落在输出，虽已有 response/representation 分析 | 显式 on-path state 与 \(b_h+r_h\) | Q1 只建立预测前提 | 不以预测精度替代状态证据 |
| state 应当真正承载预测 | predictive-state 文献强调状态语义与监督 | state readout 和可移除 \(r_h\) | Q2 state removal，两 split 的 paired CI 排除零 | forecast performance degrades after state removal |
| future weather 应当推进状态 | EO-WM/VegSim 已研究 forcing 与 scenario/output response | future weather 只进入 shared \(T_\psi\) | Q3 只替换 future-weather path | weather-responsive 但非因果 |
| actual forcing 应有预测窗口 fidelity | 现有近邻目标互补，尚未共同回答 on-path state 与 frozen-control fidelity | \(\Delta L=L_{\rm ctrl}-L_{\rm actual}\) 接口 | donor/mean 的 complete-window CI 均为正 | actual weather greater than frozen controls |
| 内部状态主张应可检验/可否证 | latent quality 与 output accuracy 可脱钩，需要专门诊断 | 训练锚定 + post-training interfaces | 同一冻结最终模型的 Q1--Q3 | bounded predictive-state claim is empirically testable |

闭环完整。Related Work 没有提出 Method 未解决的问题，Conclusion 也没有比 Abstract 或
Results 更强。

## 5. Method 承诺、信息边界与公式

### 5.1 Equations (1)--(8)

| 公式 | 职责 | 一致性检查 | 判定 |
|---|---|---|---|
| Eq. (1), `eq:contract` | \(q_\theta\to P_\rho\to T_\psi\to O_\omega\to b_h+r_h\) | 输入输出、符号类型与后文稳定 | PASS |
| Eq. (2), `eq:condition` | weather prefix、patch geography、horizon 的 condition fusion | weather/geography/horizon 三路职责清楚 | PASS |
| Eq. (3), `eq:transition` | shared residual transition | 每个 \(h\) 从同一 \(z_t\) 直接查询；正文明确非 recursive rollout | PASS |
| Eq. (4), `eq:closure` | \(r_h=O_\omega(z_{t+h})\)，\(\widehat y=b_h+\alpha r_h\) | \(\alpha\equiv1\) 训练/推理，\(\alpha=0\) 仅 Q2 干预 | PASS |
| Eq. (5), `eq:forecastlosses` | GT 与 KD forecast objectives | teacher target stop-gradient，mask 和统计对象有定义 | PASS |
| Eq. (6), `eq:futurestate` | terminal future-state target | future EO 只构造 stopped training target，不进入 inference | PASS |
| Eq. (7), `eq:total` | GT + 0.5 KD + \(\lambda_s\) FS | 训练职责与推理边界分开 | PASS |
| Eq. (8), `eq:interfaces` | future-weather substitution 与 \(\Delta L\) | control minus actual；正值含义与 4.4/Table 3 一致 | PASS |

### 5.2 信息边界

- \(q_\theta\) 只读取 EO history、past weather、static geography；
- future EO 不进入 student forecast/inference，只进入冻结 future-state target branch；
- future weather 不进入 history encoder，只通过 \(T_\psi\)；
- KD teacher 读取完整 future-weather sequence，但不读取 future EO，且训练后丢弃；
- future-state target encoder 是 training-start frozen copy，训练后丢弃；
- \(T_\psi\) 对每个 horizon 直接作用于同一个 \(z_t\)，正文明确排除 recursive rollout；
- Q2/Q3 改变冻结 forward computation，不重新训练、不改变选模。

以上边界在 3.1、3.3、3.4 和 4.1 一致。

### 5.3 唯一非阻塞符号问题

`m_i` 在 3.1 表示 EO 历史 frame validity mask，在 Eq. (6) 附近又被局部定义为 terminal
\(4\times4\) patch mask。两处上下文均有定义，不会改变计算含义，但属于不必要的符号复用，
列为 P2-1。

## 6. Q1--Q3 与训练身份核对

### 6.1 同一最终模型

| 项目 | 当前正文 | 交叉检查 | 判定 |
|---|---|---|---|
| epochs | 40 | 4.1 两处一致 | PASS |
| updates | 14,880 | Experimental Setup 与 Implementation 一致 | PASS |
| global batch | 64 | Implementation 一致 | PASS |
| model selection | validation forecasting performance only | Q2/Q3 held out from selection | PASS |
| Q1--Q3 model | same final TerraState model | Q2/Q3 frozen interventions, no retraining | PASS |

当前正文不存在 `11,904`、`boundary80`、Stage A/B、B0/B4、MAIN-last、pilot/smoke
等历史工程身份。

### 6.2 冻结数字

#### Q1

| 项目 | 正文/Table 1 | 作用域 | 判定 |
|---|---:|---|---|
| OOD-t minicubes | 1,904 | 完整 OOD-t | PASS |
| \(R^2\) | 0.56935（表中 0.569） | 完整 OOD-t | PASS |
| RMSE | 0.15059（表中 0.151） | 完整 OOD-t | PASS |
| NSE | -0.099 | 完整 OOD-t | PASS |
| absolute bias | 0.101 | 完整 OOD-t | PASS |
| RMSE25 | 0.082 | 前 25 forecast days | PASS |

Q1 被明确限定为 forecasting prerequisite，不承担内部状态证明，也没有 SOTA/严格排名结论。

#### Q2

| Split / intervention | Full \(R^2\) | Intervened \(R^2\) | Official \(\Delta R^2\) | Paired mean [95% CI] | \(n\) | 判定 |
|---|---:|---:|---:|---:|---:|---|
| Validation / state removed | 0.49732 | 0.48611 | 0.01121 | 0.01616 [0.00643, 0.02590] | 589 | PASS |
| Validation / \(T_\psi=I\) | 0.49732 | 0.48542 | 0.01191 | 0.01742 [0.00782, 0.02696] | 589 | PASS |
| OOD-t / state removed | 0.56935 | 0.54938 | 0.01997 | 0.02200 [0.01422, 0.03018] | 1,019 | PASS |
| OOD-t / \(T_\psi=I\) | 0.56935 | 0.54766 | 0.02169 | 0.02402 [0.01609, 0.03217] | 1,019 | PASS |

- official dataset-level \(\Delta R^2\) 与 per-minicube paired mean 被分列；
- paired mean 只搭配 paired-bootstrap CI；
- state removal 是 load-bearing 的 primary evidence；
- \(T_\psi\to I\) 只支持 transition involvement，正文明确不推出 necessity。

#### Q3

| Weather | \(R^2\) | RMSE | Control-minus-actual \(\Delta L\) [95% CI] | descriptive count | 判定 |
|---|---:|---:|---:|---:|---|
| Actual | 0.6254 | 0.1492 | reference | -- | PASS |
| Matched donor | 0.5893 | 0.1584 | 0.00257 [0.00112, 0.00399] | 56/84 | PASS |
| Normalized mean | 0.5430 | 0.1971 | 0.01126 [0.00547, 0.01708] | 69/84 | PASS |

另有：

- 84 个冻结匹配对；
- actual-vs-donor/mean 的 mean absolute forecast difference 分别为
  0.03592 和 0.08137；
- \(\Delta L=L_{\rm control}-L_{\rm actual}\)，正值表示 actual weather loss 更低；
- loss 覆盖完整 20-step window；
- CI 为 geographic-cluster bootstrap；
- 56/84、69/84 仅为描述性计数；
- \(R^2=0.6254\) 和 RMSE 只属于 matched subset，caption 明确未冒充完整 OOD-t；
- hot-dry interval 不支持 extreme-specific enhancement。

## 7. Claim--evidence 矩阵

| 核心主张 | 出现位置 | 方法机制 | 冻结证据 | 最大允许结论 | 禁止外推 | 判定 |
|---|---|---|---|---|---|---|
| useful OOD-t forecasting | Abstract, Intro, 4.2, Conclusion | 完整 forecast path | \(R^2=0.56935\), RMSE=0.15059 | 有用预测能力/预测前提 | SOTA、严格排名 | supported |
| predictive state on forecast path | Intro, 3.1--3.2 | \(z_t\to z_{t+h}\to r_h\to\widehat y\) | 结构 + Q2 | 状态位于预测闭环 | 所有信息只能经过状态 | supported |
| state contribution load-bearing | 3.4, 4.3 | \(\alpha=0\) 移除 \(r_h\) | 两 split paired CI 排除零 | 显式状态路径承载可测预测增量 | 全部预测能力依赖此路径 | supported |
| shared transition involvement | 3.2, 3.4, 4.3 | shared \(T_\psi\) | \(T\to I\) 同方向退化 | learned transition 参与预测 | transition necessity | partially/appropriately supported |
| detectable weather response | 3.4, 4.4 | 只替换 \(T_\psi\) future weather | 84/84 finite positive response difference | supplied weather 改变 state-mediated forecast | causal effect | supported |
| actual-weather complete-window fidelity | Intro, 4.4, Conclusion | frozen actual/donor/mean control | 两个 \(\Delta L\) CI 均为正 | actual weather 更符合 observed complete window | counterfactual correctness | supported |
| future-state anchoring | Intro, 3.3, Conclusion | stopped terminal EO representation target | 训练机制及同一模型 Q1--Q3 | 状态受未来观测表示约束 | sufficient/complete physical state | supported as method fact |
| testable/falsifiable state claim | Title, Abstract, Intro, P4, Conclusion | on-path state + frozen interventions | Q1--Q3 闭环 | 当前协议下经验可检验/可否证 | 世界模型唯一普遍定义 | supported |
| hot-dry null | Limitations | 预声明 subset analysis | CI 跨零 | 不支持 extreme-specific enhancement | 正向 enhancement 主张 | supported |
| deployment gap | Limitations | realized future weather at evaluation | 未量化 forecast-weather shift | operational forecasts may shift inputs | 已证明部署下降 | properly bounded |
| cross-dataset scope | Limitations | GreenEarthNet only | 单数据集 temporal shift | 当前结果限于该设置 | 跨数据集泛化 | properly bounded |

## 8. Related Work 与 28 篇唯一引用

### 8.1 引用图完整性

| 检查项 | 结果 |
|---|---:|
| citation commands | 24 |
| cited key occurrences | 37 |
| unique cited keys | **28** |
| BibTeX entries | 30 |
| missing cited keys | **0** |
| duplicate BibTeX keys | **0** |
| unused BibTeX entries | 2 |
| unused keys | `chen2023deeposg`, `wang2026groupactions` |
| `main.bbl` bibitems | 28 |

未使用条目没有进入正文，不构成投稿错误；它们也没有把 Deep-OSG/group-action/composition
叙事带回正文。

### 8.2 逐条元数据与正文职责

| Key | 正式身份/状态 | 当前职责 | 元数据与支撑判定 |
|---|---|---|---|
| `requenamesa2021earthnet` | EarthNet2021, CVPRW 2021, 1132--1142 | guided EO video forecasting | PASS |
| `benson2024multimodal` | GreenEarthNet/Contextformer, CVPR 2024, 27788--27799 | vegetation forecasting、temporal shift、backbone | PASS |
| `shi2015convlstm` | NeurIPS 2015 | recurrent deterministic forecasting | PASS |
| `wang2017predrnn` | NeurIPS 2017 | recurrent predictive learning | PASS |
| `gao2022simvp` | CVPR 2022, 3170--3180 | convolutional video prediction | PASS |
| `gao2022earthformer` | NeurIPS 2022, 25390--25403 | transformer Earth-system forecasting | PASS |
| `voleti2022mcvd` | NeurIPS 2022, 23371--23385 | probabilistic/multiple-future video prediction | PASS |
| `zhao2024vegediff` | IEEE TGRS 63, 2025, DOI `10.1109/TGRS.2025.3564317` | probabilistic vegetation forecasting | PASS；key 含 2024 不改变正式 2025 identity |
| `shinohara2025vitkoop` | ICCVW 2025, 2835--2844 | compressed EO latent transition | PASS；正式 PDF 支持当前两位作者顺序 |
| `diaconu2022weather` | CVPRW 2022, 1362--1371 | weather input value/perturbation analysis | PASS |
| `ha2018worldmodels` | NeurIPS 2018, 2455--2467 | compressed latent world-model lineage | PASS；已使用正式版本 |
| `hafner2019planet` | ICML/PMLR 97, 2019, 2555--2565 | latent planning dynamics | PASS |
| `hafner2020dreamer` | ICLR 2020 | latent imagination/control lineage | PASS |
| `schrittwieser2020muzero` | Nature 588, 2020, 604--609 | policy/value/reward model targets | PASS |
| `micheli2023iris` | ICLR 2023 | agent learning inside tokenized world model | PASS |
| `bruce2024genie` | ICML/PMLR 235, 2024, 4603--4623 | action-controllable environments | PASS；25 位作者及顺序与 PMLR 一致 |
| `yang2025driveoccworld` | AAAI 2025, 39(9):9327--9335 | occupancy forecasting linked to planning | PASS |
| `luo2026eowm` | arXiv:2606.27277, preprint | EO forcing organization/output response | PASS；正文统一称 recent preprints |
| `iele2026vegsim` | arXiv:2606.21961, preprint | latent vegetation state and scenario rollout | PASS |
| `albughdadi2026observability` | arXiv:2607.13651, preprint | observation usability rather than land pixels | PASS |
| `littman2001predictive` | NeurIPS 2001 | future-observable predictive-state semantics | PASS |
| `venkatraman2017predictivestate` | NeurIPS 2017, 1172--1183 | future-observation supervision of recurrent states | PASS |
| `assran2023ijepa` | CVPR 2023, 15619--15629 | representation prediction without raw-pixel reconstruction | PASS |
| `bardes2024vjepa` | TMLR 2024 | predictive video representations | PASS |
| `yang2026latenttsf` | ICML 2026 / PMLR 306 | accurate forecasts with disordered latent temporal structure | PASS |
| `saanum2024simplifying` | NeurIPS 2024, 38355--38382 | constrained action effects in control setting | PASS |
| `vafa2024evaluating` | NeurIPS 2024, 26941--26975 | dedicated diagnostics in automaton-governed generative settings | PASS；范围未外推 |
| `wang2022pvtv2` | Computational Visual Media 8, 2022, 415--424 | PVT v2 backbone identity | PASS |

### 8.3 Citation-to-claim 审计

| 主张组 | 相邻引用 | 原子支撑 | 判定 |
|---|---|---|---|
| EO task/protocol | EarthNet2021, GreenEarthNet | guided EO forecasting、weather inputs、vegetation/temporal shift | supported |
| deterministic methods | ConvLSTM, PredRNN, SimVP, Earthformer | recurrent/convolutional/transformer prediction identities | supported |
| probabilistic futures | MCVD, VegeDiff | diffusion/multiple-future prediction | supported |
| explicit latent/weather analysis | ViT-Koop, Diaconu | compressed transition与 meteorological perturbation | supported |
| general world-model lineage | World Models, PlaNet, Dreamer | latent transitions for rollout/planning/imagination | supported |
| differentiated WM objectives | MuZero, IRIS, Genie, Drive-OccWorld | task-relevant targets、tokenized agent、interactive generation、occupancy planning | supported |
| EO world-model nearest neighbors | EO-WM, VegSim, observability | forcing、scenario simulation、observation availability | supported and fairly bounded |
| predictive-state semantics | PSR, PSD | state by future observables and explicit future supervision | supported |
| predictive representations | I-JEPA, V-JEPA | representation prediction without raw-pixel reconstruction | supported |
| output/latent decoupling | LatentTSF | accurate output can coexist with disordered latent structure | supported |
| constrained/evaluated latent dynamics | PLSM, Vafa | control-setting action constraints；automaton-specific world-model evaluation | supported with stated domains |
| Method backbone | PVT v2, Contextformer | backbone identity | supported |

“Across these strands, evidence centers on forecast outputs, with some studies also analyzing weather
response or learned representations” 是经过限定的综合判断；其后半句明确承认 Diaconu、
ViT-Koop 等例外，因此没有把整类文献绝对化。未发现引用被迫支撑整句中超出原论文的技术
结论。

### 8.4 工具与人工核验说明

- 静态 citation inventory：28 cited / 30 BibTeX / 0 missing / 0 duplicate；
- True Cite eligible entries：26/26 标题命中，26/26 被判为真实论文；
- 自动工具对若干正式会议年份和作者字段给出格式性 warning，但官方 Proceedings/PDF
  支持当前 BibTeX；
- Bib-Check 深检在 180 秒限制内未产出完整报告，属于工具超时，不是论文错误；
- 正式/预印本身份最终以会议、期刊、PMLR、OpenReview、NeurIPS/CVF PDF 或 arXiv 原文
  人工裁决。

## 9. 表格、正文与 caption 接口

| 对象 | 核查结果 | 判定 |
|---|---|---|
| Table 1 | TerraState 数字与 4.2 一致；无 ±、seed、Published/Local、SOTA；正文明确 table rank 不决定 Q2/Q3 | PASS，见 P2-2/P2-3 |
| Table 2 | official dataset-level 与 paired effect/CI 分开；state removal primary、identity supporting；\(n\) 正确 | PASS |
| Table 3 | 84 pairs；control-minus-actual；正值解释、cluster CI、descriptive counts、subset scope 均明确 | PASS |
| Figure 1 caption | 与问题—机制—Q1--Q3 主线一致 | PASS |
| Figure 2 caption | 信息边界、Q2/Q3 切点和 non-composition/non-causal 边界在文字层面正确 | PASS；图内科学内容延期 |
| Figure 3 caption | paired mean/CI、坐标解释、84 pairs、descriptive counts 与正文一致 | PASS |

Table 1 没有声称严格排行榜。为了 caption 脱离 4.1 prose 后也完全自包含，可在未来仅作
可选语言清理时增加“nominal benchmark context, not a strict cross-implementation
ranking”一类限定，并弱化“compares most favorably”的相对比较语气；这属于 P2-2，不是
当前证据错误。

## 10. 摘要、重点段落与全文语言

### 10.1 Abstract

- 任务：weather-driven land-surface forecasting；
- gap：fixed-horizon pixel accuracy 不能确认 forecast-bearing/weather-responsive state；
- 方法：history state、shared transition、state readout；
- 可检验性：state removal、identity support、actual/donor/mean substitution；
- 结果：useful skill、Validation/OOD-t degradation、actual lower complete-window loss。

最后一句同时概括 Q1--Q3，scope 是 frozen heat--drought subset，不把 subset 数字冒充完整
OOD-t。句子较长但语法、并列结构和证据层级清楚，无需局部重写。

### 10.2 Introduction contributions

1. 第一项是可证伪的科学问题；
2. 第二项是显式 state-mediated path、shared transition、future-state anchoring；
3. 第三项是同一模型的 Q1--Q3 证据。

三项互补，无因果、完整物理状态、SOTA 或 Q4 越界。

### 10.3 Section 2 四段

- P1 从 EO forecast outputs 转到 internal path；
- P2 建立 general world-model 上位语境而不赋予 TerraState 控制/规划能力；
- P3 落到 EO forcing 和最近邻；
- P4 从 predictive-state semantics/testability 正向交给 Section 3。

段间递进成立；没有四次机械以 TerraState 自我介绍结尾，没有 citation dump、防御式
rebuttal 语气或 AI 化口号。

### 10.4 Method 各节首段

- 3.1 首段定义任务和 predictive-state formulation；
- 3.2 首段给出 architecture 三模块；
- 3.3 首段解释 future-state anchoring 和两条冻结 reference branch；
- 3.4 首段明确 same frozen model、designated forward changes、no retraining。

首段职责均清楚，公式前有自然语言铺垫。

### 10.5 Experiments、Limitations、Conclusion

- Results 先说 estimand 和证据层级，再解释允许结论；
- Q2 明确不推出“全部信息经过状态”或 transition necessity；
- Q3 明确不推出 causal/counterfactual/extreme-specific enhancement；
- Limitations 按 representation/deployment → intervention boundary → external validity 组织；
- Conclusion 保留 shared transition 与 future-state anchoring，以 bounded evidence 收束。

没有明显主谓、冠词、单复数、时态、介词、从句或连接词错误。P2-3 是 Table 1 caption 的
`are lower-is-better`，属于不够自然而非语义不明。

## 11. 英文正文与三份镜像

### 11.1 非 Figure 正文

`MANUSCRIPT.md`、`MANUSCRIPT_ZH.md`、`MANUSCRIPT_ZH_FULL.md` 的非 Figure 正文与
当前 LaTeX 在以下方面同步：

- Section 2 四段及 28-key 引用集合；
- direct-per-horizon shared transition；
- future-state training-only boundary；
- Q1--Q3 同一 40-epoch / 14,880-update 最终模型；
- Q2 official/paired effect 分工和全部数值；
- Q3 84 pairs、符号、CI、描述性计数和 matched-subset scope；
- Limitations 与 Conclusion 的主张强度。

中文没有把 `supports` 翻译成“证明”，没有把 `may introduce` 翻译成必然下降，也没有把
weather response 改写成因果或反事实正确性。

### 11.2 Figure 辅助块

并发 Figure 集成完成后，三份镜像均已同步到：

- `terrastate_concept_overview_author_layout_20260729.png`；
- `terrastate_architecture_fig2_author_layout_20260729.png`；
- 当前 LaTeX caption 的 Q2/Q3、quality-matched 和 non-causal/non-composition 边界。

因此旧 `DEFERRED_FIGURE_ISSUES_20260728.md` 中的 Markdown 路径/说明问题不再存在于当前
镜像。图内科学内容仍按用户要求延期；最终 Figure 阶段应以当前图片为对象重新核销旧图
条目，不能从旧文件的 PASS/FAIL 自动继承。

## 12. 禁止叙事回归

| 禁止项 | 当前语义结果 | 判定 |
|---|---|---|
| Q4 | 正文无 Q4 主张 | PASS |
| composition/compositional dynamics/non-collapse/group action | 仅 Figure 2 caption 的否定边界 `not composition`；无正向主张 | PASS |
| causal | 只出现在范围否定、控制诊断边界或相关工作语境 | PASS |
| counterfactual | 只出现在明确否定 `does not ... guarantee` / `not ... validity` | PASS |
| complete physical state | 只是否定边界 | PASS |
| TerraState control/planning capability | control/planning 只描述 general-WM prior work；未赋予 TerraState | PASS |
| SOTA/state-of-the-art/strict ranking | 无相关主张 | PASS |
| extreme-specific enhancement | 只在明确不支持的边界句中出现 | PASS |
| 11,904/boundary80 | 不存在 | PASS |
| endpoint-only Q3 | 不存在；统一为 complete 20-step window | PASS |
| single-run/Published/Local/± | 不存在于投稿正文/表格叙事 | PASS |
| Stage A/B、B0/B4、pilot/smoke/cache/checkpoint path | 不存在 | PASS |

## 13. PDF、模板与版面

### 13.1 页面结构

| 检查 | 结果 |
|---|---|
| 总页数 | **9** |
| Page 1--7 | 正文；Page 7 完整结束 Limitations 和 Conclusion |
| Page 8--9 | 仅 References |
| 页面尺寸 | 612 × 792 pt，US Letter |
| Conclusion / References 分界 | 自然；Conclusion 未被 Figure/Table 打断 |
| 页 9 留白 | 最后 3 条参考文献后的自然留白，不是异常分页 |

### 13.2 视觉与模板

- `\documentclass[letterpaper]{article}` 与 `\usepackage[submission]{aaai2027}`；
- Anonymous Submission，无作者身份泄露；
- Figure 1--3、Table 1--3 均在正文引用，caption 位置与编号正常；
- 逐页渲染未见裁切、重叠、图表越界、标题悬空、异常跨栏或不可读文字；
- Figure 3 保持单栏布局；
- 字体对象均为 Type 1，未见 Type 3/异常替换；
- 无模板、字号、页边距或负间距异常。

### 13.3 现有日志

| 日志项 | 数量 | 判定 |
|---|---:|---|
| LaTeX errors | 0 | PASS |
| undefined citations | 0 | PASS |
| undefined references | 0 | PASS |
| BibTeX warnings | 0 | PASS |
| overfull hbox/vbox | 0 | PASS |
| underfull hbox | 7 | 工具级 P2 |
| underfull vbox | 1 | 工具级 P2 |

8 个 underfull warning 没有对应的肉眼异常，按用户要求合并为 P2-4，不阻塞。

## 14. Figure 延期汇总

本轮遵守“图内科学内容不阻塞非图正文冻结”：

- **Figure 1：** 插入、引用、caption、尺寸和可读性通过；三份 Markdown 辅助说明与当前
  文件名和 caption 职责已同步。
- **Figure 2：** 当前 caption 与 Section 3 事实一致，插入和版面通过。既有延期清单中的
  future-weather boundary、transition visualization、direct-horizon、\(r_h\) readout、
  \(b_h+r_h\)、Q2/Q3 切点和内部标签等问题均属于图内对象；当前正式资产已换为
  `terrastate_architecture_fig2_author_layout_20260729.png`，最终 Figure 阶段应逐项重新
  验收，不能用旧图的 PASS/FAIL 自动继承。
- **Figure 3：** 插入、caption、位置和可读性通过；既有状态为
  `FIG3_SINGLECOL_LAYOUT_FROZEN`，本轮未发现正文接口矛盾。

当前插入文件 SHA：

| Figure | 当前文件 | SHA-256 |
|---|---|---|
| Figure 1 | `paper/figures/terrastate_concept_overview_author_layout_20260729.png` | `cdb52b05f51a8412ee3de34cdf4cfc9d22dbd89495301a5d32432fd54a405481` |
| Figure 2 | `paper/figures/terrastate_architecture_fig2_author_layout_20260729.png` | `88611ce3b0b26e3ec8daeec75f4ac0369c72890d04d64c43c07d9d7d26f6968f` |
| Figure 3 | `figure_workspace/export/fig3_behavior_singlecol_aaai_cropped.pdf` | `b9049a5a66990a7d026b2049aa4956c817ea3b6764ae5466d16d14197584d17e` |

## 15. P0 / P1 / P2

### P0（0）

NONE。

### P1（0）

NONE。

### P2（4）

#### P2-1：`m_i` 的局部符号复用

- **位置：** `main.tex:224--225` 与 `main.tex:416--423`。
- **问题：** 前者是历史 EO frame validity mask，后者是 terminal patch validity mask。
- **证据：** 两处均有局部定义，公式计算和实验解释没有歧义。
- **审稿影响：** 极低；细读者可能短暂回看定义。
- **最小方向：** 若最终语言清理仍开放，可只重命名 Eq. (6) 的 patch mask；否则保留。
- **阻塞：** 否。

#### P2-2：Table 1 比较语境可更自包含

- **位置：** `main.tex:569--576`、`main.tex:587--595`、Table 1 caption。
- **问题：** prose 已说明 Table 1 是 Q1 performance context、rank 不决定 Q2/Q3，且
  overall profile mixed；caption 本身没有重复“非严格 cross-implementation ranking”
  的限定，正文另有 `compares most favorably`。
- **证据：** 无 SOTA 或严格排名主张；数值和相邻引用正确。
- **审稿影响：** 仅在读者脱离正文单看表格时，可能把 nominal context 读得比作者意图更强。
- **最小方向：** 最终语言清理若开放，可在 caption 增加一句简短 non-ranking context，
  或把相对比较限定为 “among the listed values”。
- **阻塞：** 否。

#### P2-3：`are lower-is-better` 不够自然

- **位置：** `main.tex:522--524`。
- **原文：** `RMSE, absolute bias, and RMSE25 are lower-is-better.`
- **问题：** 可理解，但作表语时不如 `Lower values are better for ...` 自然。
- **审稿影响：** 纯局部语言品质，不改变 metric direction。
- **最小方向：** 仅做等义语法清理。
- **阻塞：** 否。

#### P2-4：underfull 工具警告

- **位置：** 当前 `main.log`。
- **问题：** 7 个 underfull hbox、1 个 underfull vbox。
- **证据：** 9 页逐页渲染无可见异常；overfull=0。
- **审稿影响：** 无。
- **最小方向：** 不需要为消除工具 warning 而改变内容或使用负间距。
- **阻塞：** 否。

## 16. 核心评分

| 维度 | 分数（1--5） | 依据 |
|---|---:|---|
| 全文主线统一 | 5 | 标题至结论保持单一 predictive-state world-model story |
| 世界模型身份 | 5 | state、transition、readout、forecast closure 和训练锚定完整 |
| Introduction--Method 承诺兑现 | 5 | 每项承诺均有明确机制 |
| Q1--Q3 claim--evidence 闭环 | 5 | estimand、CI、统计单位和最大结论一致 |
| Related Work 谱系与最近邻公平性 | 5 | 四段连续递进，近邻不被贬低 |
| 公式与信息边界 | 4 | 技术一致；仅有非阻塞 `m_i` 复用 |
| 数字与训练身份 | 5 | 14,880 updates 和全部冻结数字一致 |
| 引用完整性与元数据 | 5 | 28 unique，missing/duplicate=0，支撑准确 |
| 英文学术表达 | 4 | 整体成熟；仅一处表注语法和一处可选比较语境 |
| 中文镜像一致性 | 5 | 非 Figure 正文、Figure 1/2 辅助路径与 caption 强度均同步 |
| AAAI 格式与 PDF 呈现 | 5 | 9 页结构、模板、图表、引用和视觉均通过 |
| 主张边界安全性 | 5 | 无 Q4、因果、SOTA、完整物理状态等回归 |

所有核心评分均不低于 4/5。

## 17. 冻结建议与下一阶段

非 Figure 正文已经满足冻结条件：

- P0=0；
- P1=0；
- 主线、方法、证据、数字、训练身份、引用和 PDF 页面结构一致；
- 四项 P2 不影响理解、可信度或投稿合规。

因此不建议重新打开正文做结构性或主张性修改。下一步可以进入最终 Figure 阶段：

1. 以当前 2026-07-29 Figure 1/2 文件为对象重新核销既有 deferred items；
2. 保持三份镜像当前已同步的 Figure 辅助路径/说明；
3. 保持 Figure 3 已冻结状态；
4. 图最终定稿后只做一次图文/PDF 回归，不重新设计已冻结的非 Figure 正文。

## 18. 只读声明

本审计没有修改：

- `paper/main.tex`；
- `paper/references.bib`；
- `paper/main.pdf`；
- `MANUSCRIPT.md`、`MANUSCRIPT_ZH.md`、`MANUSCRIPT_ZH_FULL.md`；
- Figure、Table、caption；
- 任何实验、证据、模型、代码或数据文件。

本轮唯一新建文件为：

`FINAL_GLOBAL_FREEZE_AUDIT_POST_RELATED_WORK_20260729.md`

---

# NON_FIGURE_MANUSCRIPT_FROZEN_READY_FOR_FIGURE_FINALIZATION
