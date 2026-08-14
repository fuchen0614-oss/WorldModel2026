# TerraState AAAI-27 独立全文终审

审稿日期：2026-07-29 UTC  
审稿身份：第一次接触本文的严格 AAAI 审稿人  
模式：只读、盲审式终审  
最终判定：**BLOCKED**

## 0. 审计范围、独立性与输入冻结

第一遍只读取并检查了：

- `paper/main.pdf`
- `paper/main.tex`
- `paper/references.bib`

在冻结第一遍判断之前，没有搜索或读取任何既有 `*_AUDIT*.md`、
`*_REVISION_LOG*.md`、历史聊天、提示词或历史审计结论。第一遍判断冻结后，才读取
任务明确允许的结果台账、claim--evidence map、最终证据审计、canonical method
specification 和 AAAI 2027 匿名模板。既有材料中的 PASS/FAIL 不作为本次评分依据；
它们只用于第二遍事实核验。

本次核验的投稿输入哈希为：

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `699bea9183899a5ab976addc715db97ad1c5127ef840b157045c71fdd45b4195` |
| `paper/main.pdf` | `7b7f66ac075d8e6ec9c2c1f8116424fc8006dc5473e8b6ade327a06c3b4fec23` |
| `paper/references.bib` | `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3` |

除本报告外，没有修改论文、图表、参考文献、实验、代码或证据文件。

## 1. 不看历史审计的第一印象

只看 PDF、TeX 和 BibTeX 时，本文给人的第一印象是：核心问题比一般 EO
forecasting 论文更清楚，第一页能够恢复“输出精度不足以证明内部存在可用世界状态
→显式预测状态及天气转移→冻结干预检验”的主线。Q1 被放在预测可用性的前提位置，
Q2 以 state removal 为主证据，Q3 以完整预测窗口上的天气替换为证据，整体克制，
没有用表格名次冒充世界模型证据。与此同时，第一遍即能发现 Figure 2 把 future
weather 视觉上放入 history encoder 的输入容器，且图中的乘法符号和 token-grid
readout 与正文公式不一致；训练和干预协议也仍有若干不能从主文独立复现的缺口。
因此第一遍结论已经不是 PASS，之后的证据核验只是确定这些问题的严重程度。

## 2. 一句话概括本文贡献

TerraState 将天气驱动 EO forecasting 中的“世界状态”从架构命名转化为可检验的
预测状态主张：同一个冻结模型既要具有预测可用性，其显式状态路径还要在移除时造成
性能下降，并且对真实未来天气表现出优于匹配控制的完整窗口预测忠实度。

## 3. 整体故事反向提纲

| 叙事步骤 | 当前稿承担的功能 | 审稿判断 |
|---|---|---|
| 问题 | 稀疏、云遮挡 EO history 需要结合过去天气、地理和未来天气预测地表观测 | 清楚；第一页可理解 |
| 评测缺口 | 固定时域像素精度不能识别 latent bypass、弱天气使用或不承载输出的状态 | 是本文最有辨识度的动机 |
| 核心问题 | 状态是否承载预测，并通过未来天气产生更忠实的预测响应 | 清楚、可证伪 |
| 方法合同 | \(q\rightarrow P\rightarrow T\rightarrow O\)，并以 \(b_h+r_h\) 闭合预测 | 文字和公式基本正确 |
| 训练 | GT、KD 和 future-state target 共同训练部署 student | 三种身份已区分，但 checkpoint 训练历史与证据冲突 |
| Q1 | 先证明同一模型在 OOD-t 上仍有有用预测能力 | 定位正确；不应被解释为 SOTA |
| Q2 | state removal 为 load-bearing 主检验，\(T\!\to I\) 仅为支持诊断 | 证据和措辞正确 |
| Q3 | 固定历史、状态、地理和 readout，只替换 transition 的 future weather | 结果方向正确；协议披露仍不足 |
| 限制 | 排除因果、完整物理状态、跨数据集泛化和极端特异增强 | 边界正确，但否定术语过密且触发禁用词扫描 |
| 结论 | 把 architectural assertion 转为 empirical test | 与核心结果一致，略带口号感但可接受 |

故事的主要断裂不在论文定位，而在“报告结果究竟来自哪个训练完成度的模型”。
允许核验的冻结证据将 Q1--Q3 绑定到 update 11,904 的 pre-unfreeze checkpoint，
而正文称其完成 40 epochs / 14,880 updates。只要该身份冲突存在，叙事中的
“same fully trained final model”就不成立。

## 4. 六维评分

评分尺度：1=差/阻塞，2=弱，3=混合，4=好，5=优秀。

| 维度 | 分数 | 理由 |
|---|---:|---|
| 1. Story / Logic | **4** | 问题、缺口、可检验状态、Q1--Q3 和限制形成自然链条；world model 始终是主体 |
| 2. Method / Technical Correctness | **2** | 正文推理公式基本正确，但冻结 checkpoint 的实际训练历史与正文冲突；Figure 2 还传达错误信息边界 |
| 3. Results / Evidence | **3** | Q1--Q3 数字、estimand 和方向一致；Q2/Q3 支持受限主张，但 Q3 provenance 和协议披露不完整 |
| 4. Writing / Structure | **4** | 结构成熟、段落职责大体清楚；局部有审计式、名词堆叠和过度防御表达 |
| 5. References / Positioning | **4** | EO forecasting、EO world models 和 predictive-state 路线区分清楚；有两条未使用 Bib 项及一项正式出版元数据待确认 |
| 6. AAAI Format / Submission Readiness | **3** | 页数、匿名、字体、纸张、双栏和 caption 位置通过；图内字号与压缩表格存在 Author Kit 风险 |

核心五维中位数为 4，但 Method 为 2；因此不满足 PASS 的“无维度低于 3”条件。

## 5. 三种审稿视角与 AC 综合

| 视角 | 主要正面信号 | 决定性负面信号 | 可能立场 |
|---|---|---|---|
| Method / soundness reviewer | \(q,P,T,O\) 信息边界和 direct-per-h 公式写得较清楚 | 报告 checkpoint 并未完成正文所称的 14,880-update 协议；Figure 2 与公式不一致 | Block |
| Evidence / experiment reviewer | Q2 的 official 与 paired estimand 分离；Q3 是完整 20-step window，CI 方向正确 | Q2/Q3 bootstrap 和 donor construction 不能仅凭主文复现；Q3 JSON 身份链接依赖外部 release bundle | Major revision |
| Venue / AC reviewer | 可检验预测状态是明确的 AAAI-level conceptual contribution，主张克制 | 核心模型身份属于事实一致性问题，不能由写作质量抵消 | Block until resolved |

AC 综合：如果 checkpoint 身份与训练历史被证据一致地解决，且 Figure 2 科学语义修正，
本文可回到 borderline-positive/lean-accept 讨论；当前版本不能进入该讨论。

## 6. 方法正确性核对

| 核对项 | 正文位置 | 结论 |
|---|---|---|
| history encoder \(q_\theta\)、projector \(P_\rho\)、transition \(T_\psi\)、readout \(O_\omega\) | PDF p.3--5；TeX 204--243, 284--339 | **PASS** |
| future weather、past weather、static geography、EO history 的信息边界 | PDF p.3--4；TeX 213--243 | **正文 PASS；Figure 2 FAIL** |
| future EO 只形成 training-only future-state target | PDF p.4--5；TeX 343--415 | **PASS** |
| frozen KD teacher、future-state target encoder、student 身份 | PDF p.4--5；TeX 343--355 | **PASS WITH MAJOR REPRODUCIBILITY GAP** |
| \(q\rightarrow P\rightarrow T\rightarrow O\) | PDF p.3；TeX 220--233 | **PASS** |
| 每个 horizon 从同一 \(z_t\) direct query，非 recursive rollout | PDF p.3--4；TeX 317--324 | **PASS** |
| \(r_h\) 与 \(b_h+r_h=\hat y_{t+h}\)，\(\alpha\equiv1\) | PDF p.3--4；TeX 220--226, 326--339 | **PASS** |
| 40 epochs、14,880 updates | PDF p.6；TeX 522--525, 568--573 | **FAIL：与冻结 checkpoint 证据冲突** |
| Q1--Q3 使用同一个完成完整协议的最终模型 | PDF p.6；TeX 522--525, 571--573 | **FAIL：同一 checkpoint 可关联，但其训练只到 update 11,904** |
| Q2/Q3 为冻结前向干预、无 retraining | PDF p.5--6；TeX 431--487, 522--525 | **PASS** |

### 冻结 checkpoint 冲突的证据链

正文明确写：

- TeX 522--525：同一 final model 完成 40 epochs / 14,880 updates；
- TeX 568--573：Q1--Q3 使用完成该 full training protocol 的 final model。

第二遍允许读取的 `results_ledger.json` 和 canonical specification 则共同给出：

- checkpoint step = 11,904 / 14,880；
- 保存于最后 20% stage 和 \(q\) partial unfreezing 之前；
- 该 checkpoint 的 \(q_\theta\) 在实际经历中始终冻结；
- Q1--Q3 数字绑定的是该 boundary checkpoint，而不是 14,880-update 终点。

这不是“四舍五入”“术语选择”或“训练计划与实现相近”的问题，而是结果模型身份。
在保持“报告模型完成 14,880 updates”这一冻结要求时，现有证据不足；若改为如实报告
11,904，则必须撤回“完成完整协议的最终模型”这一事实主张。

## 7. Q1--Q3 claim--evidence 对照

| 问题 | 论文主张 | 可核验证据 | 支持强度 | 审稿边界 |
|---|---|---|---|---|
| Q1 | TerraState 在 OOD-t 上保留有用预测能力 | \(R^2=0.56935\)，RMSE \(=0.15059\)，1,904 targets；表、正文、ledger 一致 | **adequate** | 支持“useful skill”，不支持 SOTA、严格排名或训练稳定性 |
| Q2 primary | 显式 state-mediated path 是 load-bearing | Val state removal：official \(\Delta R^2=0.01121\)，paired mean \(0.01616\), 95% CI \([0.00643,0.02590]\)；OOD-t：\(0.01997\)，paired mean \(0.02200\), CI \([0.01422,0.03018]\) | **strong under frozen intervention** | 证明该显式路径承载增量，不证明全部信息必须经过 state |
| Q2 support | learned transition 参与预测 | \(T\!\to I\) 在 Val/OOD-t 同向下降，paired CIs 排除 0 | **supporting only** | identity state 对 readout 可能 OOD；不能升级为 transition necessity |
| Q3 response | 替换 future weather 会改变 state-mediated output | actual--donor/mean 的 masked mean absolute forecast differences 分别为 0.03592/0.08137；84/84 finite and positive | **adequate** | 是输出响应，不是因果效应 |
| Q3 fidelity | actual weather 在完整 20-step window 上优于 donor/mean | donor-minus-actual \(\Delta L=0.00257\), geo-cluster CI \([0.00112,0.00399]\)；mean-minus-actual \(0.01126\), CI \([0.00547,0.01708]\) | **strong on selected 84-pair protocol** | 是 complete-window conditional predictive fidelity，不是 endpoint-only、物理真实性或反事实正确性 |
| Q4 / composition | 非核心、未验证 | 无当前核心冻结证据 | **unsupported as a core claim** | 当前稿未重新引入正面核心主张 |

数值核对结论：

- Q1 精确值及舍入均正确；
- Q2 official \(\Delta R^2\) 与 paired mean/CI 正确分开；
- state removal 始终是主证据，\(T\!\to I\) 只作 supporting diagnostic；
- Q3 正文、Figure 3、Table 3 和 Conclusion 均使用完整 20-step forecast window；
- \(\Delta L=L_{\rm control}-L_{\rm actual}\) 的符号解释正确；
- Figure 3 中 above-diagonal favors actual 的解释正确；
- 没有将 Q3 提升为因果或物理正确性；
- 没有将 Q1 排名作为世界模型主张；
- 没有正面恢复 Q4/composition 证据。

## 8. Critical / Major / Minor 问题

### 8.1 Critical

| ID | PDF 页码 | `main.tex` 行号 | 问题 | 原因 | 最小修复方向 |
|---|---:|---:|---|---|---|
| C1 | p.6 | 522--525, 568--573 | 报告模型被写成完成 40 epochs / 14,880 updates 的 final model，但冻结证据绑定 update 11,904 的 pre-unfreeze checkpoint | 直接改变 Q1--Q3 所属模型、训练身份和“same fully trained model”主张；在当前证据下不能同时保留两种说法 | 二选一并提供一致证据：如实改为 11,904 checkpoint 及其实际 freeze path；或提供真正 14,880-update 模型的 Q1--Q3 冻结结果。不得把计划训练时长写成已报告模型经历 |
| C2 | p.4, Figure 2(a) | 254--269（图像对象及 caption）；对照 235--243 | Figure 2 将 “Future meteorological forcing” 放在与历史 EO、过去环境和静态地理相同的 multimodal-context 容器，并以总箭头指向 history encoder | 视觉上允许 future weather 进入 \(q_\theta\)，违反正文和实现的唯一入口 \(u^{future}\rightarrow T_\psi\)；这是科学信息边界冲突，不是美观问题 | 从 history-encoder 输入容器移出 future weather，并只把它路由到 shared transition；正文公式无需迁就现图 |

### 8.2 Major

| ID | PDF 页码 | `main.tex` 行号 | 问题 | 原因 | 最小修复方向 |
|---|---:|---:|---|---|---|
| M1 | p.4, Figure 2(c,d) | 254--269；对照 297--339, 437--470 | Figure 2 用“×”表示 weather/state 作用，把 \(r_h\) 画成 token grid，且没有清楚显示 same-\(z_t\) direct-per-h 和 Q2 的 \(r_h\to0\) 切点 | 图暗示 elementwise product/gating，而真实方法是 concat/fusion 后的 residual MLP；readout 输出应是 raster contribution | 图中仅修正科学对象：condition fusion + residual transition；\(O_\omega\) 输出 raster \(r_h\)；标清每个 \(h\) 从同一 \(z_t\) direct query；Q2 切在加法前 |
| M2 | p.4--6 | 343--355, 417--429, 568--573 | 训练可复现性仍不完整：\(\lambda_s\) 数值/调度、checkpoint-specific freeze path、完整 warm-start provenance 和 optimizer 细节未闭合 | \(\lambda_s\) 出现在总目标中却未定义；“parameters enabled by the training schedule”要求读者猜测；C1 修复后仍会保留这一缺口 | 在不扩大实验的前提下报告实际 checkpoint 经历的 \(\lambda_s\) schedule、冻结参数组、warm-start 身份及必要优化器设置；不能只描述候选 run 计划 |
| M3 | p.5--7 | 444--446, 479--481, 546--557, 642--674 | Q2/Q3 的 uncertainty 和 control construction 不能从主文独立复现 | Q2 未给 bootstrap replicates；Q3 未写 31 clusters/10,000 replicates、cluster definition、extreme-stratum 和 donor matching 的可执行规则/容差 | 主文至少补统计单位、percentile/cluster bootstrap、cluster/replicate 数及 control construction 的唯一指针；详细 matching 可放获准的 supplement，但主判据必须在主文闭合 |
| M4 | p.2, p.4, p.5, p.7 | 70--80, 254--281, 493, 601 | 图内多处标签在当前放置尺寸下明显低于 Author Kit 的 9 pt 要求；Table 1/2 使用 `\arraystretch=0.70` 形成明显压缩风险 | AAAI 2027 要求 illustration labels 至少 9 pt，并禁止以版式技巧挤页；模板只明确允许压缩 `tabcolsep`，未授权将行距压到 0.70 | 投稿前把图内文字提高到可验证的 ≥9 pt；恢复正常 table row spacing，仅使用模板明确允许的表格压缩方式 |

### 8.3 Minor

| ID | PDF 页码 | `main.tex` 行号 | 问题 | 原因 | 最小修复方向 |
|---|---:|---:|---|---|---|
| m1 | p.6--7 | 489--515, 559--566 | Table 1 caption 本身没有说明 TerraState 与 published values 不是严格同 manifest/evaluator 比较 | 正文虽说 rank 不决定 Q1，但读者只看表仍会自然当作严格 leaderboard | caption 增加一句“nominal benchmark context, not a strict ranking”；不要引入 Published/Local 分组或运行次数讨论 |
| m2 | p.1, p.3, p.5, p.7 | 101, 192, 242, 268, 486--487, 691--700 | 禁用词以否定形式仍出现在正文：`complete physical state`、`counterfactual correctness`、`extreme-specific enhancement`，另有 `composition` 的防御式提及 | 没有发生科学过度主张，但违反本轮明确的正文禁止项，并使语气像内部 claim audit | 保留证据边界，用正向 scope statement 或“evaluates X but leaves Y untested”替换；不要弱化谨慎程度 |
| m3 | p.3, p.5 | 213--218, 410--413 | \(m_i\) 同时指 history frame mask 和 terminal patch-validity mask | 符号复用增加 future-state objective 的理解成本 | 为 terminal patch mask 使用独立符号 |
| m4 | p.5, Figure 3 caption | 276--280 | “56/84 and 69/84 are descriptive”指代略含糊 | 读者需要回看 panel 才知道它们是 actual-lower pair counts | 加入最小名词中心，如 “The actual-lower counts ... are descriptive” |
| m5 | p.6 | 577--584 | “low error”及“most favorable relative dimension”带有不必要的评价色彩 | Q1 只需证明 usable skill；该句让读者重新关注表格排名 | 中性报告 \(\mathrm{RMSE}_{25}=0.082\) 和窗口定义即可 |
| m6 | p.1--7 | 见 §12 | 有 4 个确定语法/标点问题和 9 个明显不自然或审计式表达 | 不影响科学可理解性，但低于最终投稿语言洁净度 | 按句级表执行最小修改，不重写段落 |
| m7 | p.8 / BibTeX | `references.bib` 112--119, 129--137, 121--127 | 当前有 2 个未使用条目；LatentTSF 的 ICML/PMLR volume 记录未能从官方 proceedings 页面独立确认 | citation graph 本身完整，但 unused entries 和未确认 formal metadata 降低书目洁净度 | 移除未使用的 Deep-OSG / group-actions 条目；LatentTSF 在正式 proceedings 可核验前保持版本一致，不编造 pages |
| m8 | p.4, Figure 2 | 254--269 | panel 顺序为 (a),(b),(d),(c)，`D3 Vegetation forecast` 未定义，部分 schematic raster 来源/许可无法从 PDF 核验 | 前两项是视觉/命名问题；第三项是 source package 的作者确认项 | 语义修复后再统一 panel 顺序与标签；投稿前由作者确认所有 raster tile 的自有或许可来源 |

## 9. Figure 2：科学事实问题与纯美观问题

### 投稿前必须解决的科学事实

1. future weather 不能位于 history encoder 的 multimodal-context 输入边界内；
2. transition 不能用无定义的“weather tokens × state tokens”代表，应与
   concat/fusion + residual update 一致；
3. \(z_t\) 必须清楚进入 shared \(T_\psi\)，各 horizon 是从同一 \(z_t\) 的 direct
   query，不是隐含递归；
4. \(O_\omega\) 输出的是 unpatchified spatial/raster forecast contribution
   \(r_h\)，不是另一组 state tokens；
5. Q2 removal 的切点是 \(r_h\) 进入 \(b_h+r_h\) 之前；
6. Q3 替换发生在 transition 的 future-weather input；actual/donor/mean 共享
   history、\(z_t\)、geography、readout 和 target；
7. `normalized mean` 是 global z-score space 中的零向量，不是当地 climatology。

### 可在科学语义闭合后处理的纯美观/编辑问题

- panel 顺序 (a),(b),(d),(c)；
- 配色、边框、留白、箭头粗细和视觉对齐；
- `D3 Vegetation forecast` 改成正文已有术语；
- `P State projector` 的排版；
- schematic tile 的风格统一。

图内字号 ≥9 pt 不是纯美观问题，而是 AAAI submission-format 门禁，必须投稿前处理。

## 10. 引用、BibTeX 与定位审计

### 10.1 Citation graph

独立静态清点结果：

| 项目 | 数量 |
|---|---:|
| citation commands | 22 |
| cited-key occurrences | 31 |
| unique cited keys | 22 |
| BibTeX entries | 24 |
| missing keys | 0 |
| duplicate keys | 0 |
| unused entries | 2 (`chen2023deeposg`, `wang2026groupactions`) |
| unresolved input/include | 0 |

PDF 中未见 `??`、undefined citation 或 undefined reference。

### 10.2 Metadata screening

- True Cite 于 2026-07-29 检查 19 个可处理条目：19 个均
  `verified=true`, `titleMatch=true`，0 failed，0 API error；19 个 warning
  来自姓名顺序/TeX 重音/会场全称与简称匹配，不能解释为 19 个书目错误。
- 5 个 `@misc` 被工具跳过；其中正文使用的 EO-WM、VegSim、observability
  world model 和 World Models 已按 arXiv 官方页面人工核验。未使用的
  group-actions 条目不影响正文 claim graph。
- Bib-Check 已成功 clone/install，但 online-check 阶段持续无输出，人工中止；
  因而本报告不声称 Bib-Check 完整通过。该工具未完成不是书目失败。

### 10.3 Citation-to-claim support

| 正文位置 | 工作 | 相邻主张 | 判定 |
|---|---|---|---|
| 63--65, 141--145, 536--544 | EarthNet2021 / GreenEarthNet | guided EO forecasting、20 m、weather conditioning、vegetation/cloud-mask setting | supported |
| 86--91 | EarthNet2021 / GreenEarthNet / LatentTSF | output accuracy 不足以识别 latent-state behavior；准确输出可与 temporal disorder 共存 | supported；前半句是作者逻辑推论，引用提供背景而非定理 |
| 93--95, 177--180 | Predictive Representations of State | 用未来 observables 表征 state | supported；本文已正确排除 classical sufficient-statistic guarantee |
| 146--147 | Diaconu et al. | weather input value 与 single-variable response analysis | supported |
| 148--153 | ConvLSTM/PredRNN/SimVP/Earthformer/MCVD/VegeDiff/ViT-Koop | 方法类别和 latent/linear Koopman 定位 | supported |
| 160--175 | EO-WM / VegSim / observability WM | forcing decomposition、matched response diagnostics、recurrent latent simulation、observability target | supported by current primary sources |
| 180--188 | World Models/PlaNet/Dreamer/I-JEPA/V-JEPA/PLSM | latent dynamics、feature prediction、action-conditioned latent regularization | supported |
| 294--295 | PVT v2 / Contextformer | backbone identity | supported |

定位结论：

- Related Work 清楚区分普通 EO forecaster、EO world model 和 TerraState 的
  testable-state 路线；
- EO-WM 的 partially observed / weather-driven 定位和 response diagnostics
  被准确归因，没有说此前工作“完全没有”天气响应分析；
- GreenEarthNet/EarthNet2021 的定位准确；
- 未发现会改变核心 novelty 的明显缺失引用；
- ViT-Koop 的 CVF landing page 只列一名作者，但官方论文 PDF、workshop 页面和
  DBLP 均支持 Shinohara/Saomoto 两名作者；当前 BibTeX 双作者记录可保留；
- LatentTSF 的 arXiv 内容和 ICML 2026 接收身份可核验，但本轮未找到正式 PMLR
  volume 306 landing page，故 formal volume 字段仍为 `unable to verify`，属于
  非阻塞元数据检查项。

## 11. AAAI 技术门禁

| 门禁 | 结果 | 依据/说明 |
|---|---|---|
| 主内容结束于第 7 页 | **PASS** | Conclusion 完整结束于 PDF p.7 |
| 第 8 页从 References 开始 | **PASS** | PDF p.8 首项为 References |
| 匿名性 | **PASS** | `Anonymous Submission`，affiliation 为空；PDF metadata 无 author/subject/keywords |
| 图表正文引用 | **PASS** | Figure 1--3、Table 1--3 均至少被引用一次 |
| caption 独立性 | **PASS WITH MINOR** | 主要 estimand 可理解；Figure 3 descriptive counts 指代可更明确 |
| table caption 位于表格下方 | **PASS** | Table 1--3 均在下方 |
| 裁切/重叠/异常留白 | **PASS at PDF level** | 8 页目视检查未见裁切、重叠、越 margin 或异常空白 |
| 不可读字号 | **FAIL** | Figure 1--3 内部若干标签在最终放置尺寸明显小于 9 pt；Table 1/2 行距过度压缩 |
| undefined citation/reference | **PASS** | citation graph 无 missing key；PDF 无 `??` |
| overfull | **NO VISIBLE OVERFLOW / LOG-LEVEL UNVERIFIED** | 允许输入不含编译 log；PDF 层未见 overflow，不能虚构 log-level PASS |
| 嵌入字体 | **PASS** | 所有检测字体均有嵌入字节流和 subset prefix |
| Type 3 | **PASS** | 检测到的字体均为 Type 1 |
| Identity-H/CID | **PASS** | 未检测到 Identity-H |
| US Letter | **PASS** | 全部页面 612×792 pt |
| 官方双栏 | **PASS** | `letterpaper` + `submission` `aaai2027`，视觉为官方双栏 |
| 页码/header/footer | **PASS** | 无页码和运行页眉；submission footer 正常 |

## 12. Sentence-Level Language and Grammar Audit

### 12.1 数量与总判定

- 确认的局部语法/标点错误：**4**
- 另计明显不自然、工程日志式或内部审计式表达：**9**
- 语言总判定：**LANGUAGE_PASS_WITH_MINOR**

全文整体是自然、专业的美式学术英语，段落组织明显高于需要全面重写的水平。
问题集中在少量错误搭配、过密名词短语、定义式审计口吻和重复否定边界；适合一次
句级最小修订，不需要重写段落。

### 12.2 高频重复词与句型

正文区间 TeX 28--722 的词频（含 caption/table text）：

| 词 | 次数 | 判断 |
|---|---:|---|
| state | 128 | 核心术语，必要，但同段内可少量用 predictive representation 替换非定义性重复 |
| weather | 94 | 任务核心，必要 |
| forecast | 69 | 与 forecasting 分工基本稳定；可删少量 “forecast-window forecast” 式堆叠 |
| TerraState | 38 | 偏高但仍可接受；段内连续出现时可用 “the model” |
| predictive | 38 | 核心术语，基本稳定 |
| contribution | 29 | Q2 所需，重复主要集中在相关段落 |
| transition | 22 | 方法核心 |
| response | 21 | Q3 所需，但 detectable response / response fidelity 应严格分层 |
| explicit | 12 | 明显偏多；至少 4 处可直接删除而不改变事实 |
| fidelity | 11 | 核心术语，定义后保持稳定 |

句首 `We` 约 19 次、`This` 约 20 次。没有形成连续多句的严重模板化，但 Method
interfaces 和 Experiments 中存在 “This interface... / This profile...” 的可见重复。
`show(s)` 共 6 次、`provide(s)` 4 次、`falsifiable` 3 次，没有滥用
`demonstrate/significantly/crucially/fundamentally`。

### 12.3 cannot / 否定结构统计与必要性分类

排除 preamble 的 “DO NOT CHANGE” 注释后，正文共有 **28** 个指定否定结构：

| 结构 | 次数 | TeX 行号 | 必要边界 | 可正向改写 | 与邻文重复 |
|---|---:|---|---:|---:|---:|
| `cannot` | 3 | 33, 38, 87 | 2 | 1 | 0 |
| `does not` | 9 | 37, 171, 190, 321, 486, 638, 691, 699, 704 | 7 | 2 | 0 |
| `do not` | 2 | 695, 711 | 2 | 0 | 0 |
| `rather than` | 8 | 42, 94, 100, 110, 168, 179, 242, 566 | 4 | 2 | 2 |
| `without` | 6 | 111, 114, 183, 344, 382, 634 | 6 | 0 | 0 |
| `fail(s) to` | 0 | — | 0 | 0 | 0 |
| `insufficient to` | 0 | — | 0 | 0 | 0 |
| `unable to` | 0 | — | 0 | 0 | 0 |

必要的否定主要保护 future-EO leakage、non-recursive transition、\(T\!\to I\)
限制、Q3 非因果边界和跨数据集边界，不能为了降低计数而删除。可精简的是摘要与
Introduction 对“pixel metrics cannot establish state”的重复，以及 Related Work /
Limitations 中连续使用的 defensive contrast。优先替换为：

- “leaves state use untested”；
- “evaluates conditional predictive fidelity, while causal identification remains untested”；
- “distinguishes a forecast-bearing representation from a sufficient physical state”。

这些替换必须保持原主张强度，不能把谨慎陈述改成更强的因果或物理主张。

### 12.4 最需要修改的句子

| PDF 页码 | `main.tex` 行号 | 原句 | 问题类型 | 推荐的最小句级改法 | 可能改变主张强度 |
|---:|---:|---|---|---|---|
| p.1 | 29--32 | “High-resolution satellite time series are a primary tool ... and are increasingly cast as weather-driven forecasting: predicting ...” | 错误搭配/选择限制 | 将 “are increasingly cast as” 改为 “are increasingly used for”；把冒号后的内容保留为 forecasting 定义 | 否 |
| p.1 | 46--52 | “On GreenEarthNet ... while, on a frozen heat--drought subset, actual weather yields ...” | 标点、过长句、术语不一致 | 删除 `while` 后多余逗号；统一为全文使用的 matched/extreme-weather subset；必要时只在分号处拆成两句 | 否 |
| p.2 | 116--123 | “On GreenEarthNet OOD-t, TerraState obtains ...” | 冠词/自然度 | 改为 “On the GreenEarthNet OOD-t split, ...” | 否 |
| p.3 | 171--175 | “... the spatial predictive state in the observed-weather forecast makes a removable contribution ...” | 不自然复合词 | 将 “observed-weather forecast” 改为 “forecast under actual weather” | 否 |
| p.4 | 346--355 | “An exact full-model warm start from a forecasting precursor initializes the student ...” | 名词堆叠/动作主体过晚 | 改为主动而直接的 “We initialize the student with the exact full-model weights of ...”；保留三种模型身份 | 可能；必须先确认 precursor 身份 |
| p.5 | 390--394 | “The frozen copy runs the history operator in all-frames-visible encoding mode ...” | 工程式标签/多层修饰 | 改为 “The frozen copy encodes all observed frames together with their recorded masks ...” | 否 |
| p.5 | 394--395 | “For terminal spatial patch \(i\), ...” | 缺少限定词 | 改为 “For each terminal spatial patch \(i\), ...” | 否 |
| p.5 | 477--484 | “A response is detectable when actual and control weather produce a nonzero, reportable masked forecast-output response statistic ...” | 内部审计式、名词堆叠、定义近似同义反复 | 直接说明“替换 future weather 改变 common-mask forecast output”，并把 response magnitude 与 fidelity criterion 分开报告 | 可能；需保持 detectable ≠ fidelity |
| p.6 | 568--573 | “We train it ... for 40 epochs (14,880 updates) ... The final model ... completes this full training protocol ...” | **事实冲突，不是单纯语言问题** | 暂停语言润色；先按 C1 确定 11,904 或 14,880 的真实证据身份，再作句级修订 | **是** |
| p.6 | 577--584 | “Its \(\mathrm{RMSE}_{25}=0.082\) indicates low error ... and represents TerraState's most favorable relative dimension ...” | 空泛评价/排名导向 | 中性报告数值和 “first 25 forecast days”；删除 “low” 与 “most favorable” | 仅弱化修辞，不改变证据 |
| p.6 | 642--649 | “Across 84 frozen matched pairs from the predeclared extreme-weather stratum ...” | 内部审计式/协议名词不透明 | 改为 “Across 84 pairs selected by the prespecified matched evaluation protocol ...”，并在后句给规则 | 否 |
| p.7 | 512--514 | “RMSE, absolute bias, and \(\mathrm{RMSE}_{25}\) are lower-is-better.” | 明确语法错误 | 改为 “Lower values are better for RMSE, absolute bias, and \(\mathrm{RMSE}_{25}\).” | 否 |
| p.7 | 697--700 | “... not causal identification or counterfactual correctness. The ... evidence does not support extreme-specific enhancement.” | 禁用词、连续否定、过度防御 | 用正向 scope statement 说明只评估 conditional predictive fidelity，并说 hot-dry interaction interval crosses zero；避免复述禁用标签 | 可能；必须保留非因果边界 |

### 12.5 段落衔接与文体一致性

- Abstract、Introduction 和 Conclusion 的贡献强度基本一致；
- 各 Method 小节首段能说明该节任务，Training identities、Forecast objectives、
  Future-state target 三段职责清楚；
- Experiments 的 Q1--Q3 架构很有效，避免了表格逐格复述；
- Q2 按“机制/干预→证据→解释→边界”展开，完成度最高；
- Q3 首段同时承担 claim、样本构造、固定量、control 定义和图表导航，认知负担偏高；
- “prediction”多指输出/质量，“forecasting”多指任务，基本一致；
- “state / predictive state / representation”总体稳定；
- “weather forcing / future weather / meteorological forcing”可互换但没有概念漂移；
- “heat--drought subset / extreme-weather stratum / hot-dry interaction”不统一，应仅在
  interaction 的具体统计语境使用 `hot-dry`；
- “intervention”用于冻结替换，“control”用于 donor/mean，“diagnostic”用于
  \(T\!\to I\)，分工正确；
- `load-bearing`、`weather-responsive`、`forecast-window fidelity` 的含义稳定，
  但 Abstract/Introduction/Method/Results 多次重复完整定义，造成轻度机械感。

## 13. 禁止项扫描

| 禁止项 | 扫描结果 | 判定 |
|---|---|---|
| SOTA / best-performing / strict ranking | 未出现 | PASS |
| Published/Local 显眼分组 | 未出现 | PASS |
| single-seed / single-run / ± / 运行次数讨论 | 未出现 | PASS |
| B0 / B4 / Stage A / Stage B / boundary80 / 11,904 | 未出现 | PASS；但这也导致 C1 的真实 checkpoint 未披露 |
| composition/Q4 核心主张 | 无正面核心主张；仅两处防御式 mention | PASS WITH MINOR |
| causal correctness | 未出现；有 `causal effect/identification` 的否定边界 | 科学边界正确 |
| counterfactual correctness | 出现 2 次（486--487, 697--698），均为否定 | **字面禁用项 FAIL；无过度主张** |
| complete physical state | 出现 3 次（101, 242, 691），均为否定 | **字面禁用项 FAIL；无过度主张** |
| extreme-specific enhancement | 出现 2 次（487, 700），均为否定 | **字面禁用项 FAIL；无过度主张** |
| 未经支持的代码公开承诺 | 未出现 | PASS |

## 14. 投稿前必须修复项

1. **解决 C1 checkpoint 身份。** 当前证据不能支持“Q1--Q3 模型完成
   14,880 updates”。在证据和正文一致前不得投稿。
2. **修正 Figure 2 的科学语义。** future weather route、transition operator、
   direct-per-h、readout object 和 intervention cut points 必须与公式一致。
3. **补足 checkpoint-specific training disclosure。** 至少闭合 \(\lambda_s\)、
   freeze path、warm start 和必要 optimizer/schedule 信息。
4. **闭合 Q2/Q3 统计协议。** 报告 bootstrap 类型/次数、Q3 clusters 和 donor
   matching 的可执行定义或唯一 supplement 指针。
5. **通过 AAAI 字号与表格门禁。** 图内文字 ≥9 pt；去除 `arraystretch=0.70`
   的压缩风险。
6. **使 Table 1 caption 自包含。** 明确它是 nominal benchmark context，不是严格
   leaderboard；保持不讨论运行次数。
7. **清除明确禁用词和确认成立的句级问题。** 保持同等谨慎，不升级主张。
8. **提交前重新检查 source package。** 确认 Figure 2 raster provenance、LatentTSF
   正式元数据和编译 log 中无 overfull。

## 15. 可延期项目

以下不应阻止在修复上述问题后投稿，也不要求本轮扩大实验：

- Figure 2 的配色、留白、边框、箭头粗细和 panel 美化；
- 除科学必要标签外的完整视觉重设计；
- cross-dataset generality；
- operational weather forecast error 的新实验；
- 更完整的物理变量、土壤水分、灌溉和植被类型建模；
- composition/Q4；
- 更广泛的 causal/counterfactual study；
- camera-ready 的完整配置表、硬件/软件环境和 artifact packaging；
- 投稿后的代码公开决定；当前稿不得提前承诺。

## 16. 最终判定

**Critical = 2；Major = 4；Minor = 8。**

最终判定：**BLOCKED**。

判定理由不是 Q1--Q3 数字失败。相反，现有数字足以支持受限的
useful-forecasting、load-bearing state-path 和 complete-window weather-response
fidelity 主线。阻塞来自更基础的事实一致性：正文要求读者相信这些结果来自完成
14,880 updates 的 final model，而允许核验的冻结证据把它们绑定到 update 11,904
的 pre-unfreeze checkpoint。若坚持前者，当前缺少对应结果证据；若接受后者，则
必须修改冻结的训练事实。Figure 2 的 future-weather route 又独立违反方法信息边界。
在这两项解决之前，不能判为 PASS 或仅作普通 REVISE。

