# TerraState AAAI-27 全文正文统一审计

**审计日期：** 2026-07-28  
**审计性质：** 全文收敛、只读审计；未修改或重新编译任何既有文件  
**投稿权威源：** `paper/main.tex`  
**事实优先级：** 当前 `main.tex` → 最新章节终审 → 作者确认的 40 epochs / 14,880 updates → 冻结 Section 4 证据 → 较早历史审计

## 1. Verdict

# FULL_TEXT_GLOBAL_CONSISTENCY_REVISE

当前**投稿权威英文正文**已经形成完整、证据安全且可复述的全文闭环：标题、摘要、引言、相关工作、方法、Q1–Q3、局限性和结论使用同一套“可检验预测状态世界模型”主线；方法、公式、数字、统计单位、训练身份和结果边界没有 Critical 或 Major。

但全文文本包仍不能整体冻结，因为两个自称与 `main.tex` 同步的精简镜像
`MANUSCRIPT.md` 与 `MANUSCRIPT_ZH.md` 保留了旧版 Abstract 和 Method：

- Q3 仍写成 `endpoint predictions / 观测终点`，而权威结果是完整 20 步预测窗口；
- 仍有独立的 `Exploratory composition (Q4) / 探索性组合（Q4）` 段；
- 方法公式仍使用旧的天气区间与旧接口记号，并未同步当前 Equations (1)–(8)。

这是一个集中、可在一轮内修复的镜像一致性 Major，不要求修改 `main.tex`、实验、公式或主张。

### 问题计数

| 等级 | 数量 | 判定 |
|---|---:|---|
| Critical | **0** | 无方法、结果、引用或证据方向错误 |
| Major | **1** | 两个精简镜像保留旧 Abstract/Method/Q3/Q4 叙事 |
| Minor | **5** | 符号自包含、训练复现说明、Table 1 来源透明度、中文导航残留、PDF 分页 |
| Optional | **3** | 两条未使用 BibTeX、历史 evidence ledger 身份、局部措辞/排版优化 |
| Deferred Figure | **10** | Figure 1 一项、Figure 2 九项、Figure 3 零项；均不进入正文 verdict |

---

## 2. 全文一页式反向提纲

| 载体 | 唯一职责 | 当前实现 | 判定 |
|---|---|---|---|
| Title | 预告对象、方法身份和任务 | testable predictive-state world model + weather-driven land-surface forecasting | **PASS** |
| Abstract | problem → method → interfaces → Q1–Q3 → bounded takeaway | 明确 output accuracy 不足、on-path state、shared transition、state/weather interventions 和完整窗口结果 | **PASS** |
| Introduction | task → gap → scientific question → TerraState mechanism → evidence preview → contributions | 不把 EO forecasting 强制定义为 world modeling；三条贡献为观点/方法/证据 | **PASS** |
| Related Work | EO forecasting → EO world models → predictive-state/latent-dynamics foundations | 三条不同比较轴；公平定位 EO-WM、VegSim、PSR、LatentTSF、PLSM | **PASS** |
| Method 3.1 | 定义任务、信息边界与总计算链 | \(q/P/T/O\)、\(b_h+r_h\)、future weather only through \(T\) | **PASS** |
| Method 3.2 | 展开正式推理架构 | history state、direct-per-horizon shared residual transition、raster readout | **PASS** |
| Method 3.3 | 定义训练期 student/teacher/target 和 GT/KD/FS | future EO 只作 stopped target；teacher/target 不进入推理 | **PASS WITH MINOR NOTES** |
| Method 3.4 | 定义冻结模型上的可证伪接口 | state removal primary；\(T\to I\) supporting；actual/donor/mean substitution | **PASS** |
| Experiments 4.1 | 固定模型、协议、统计单位和比较目的 | 同一 40-epoch / 14,880-update 模型；Q2/Q3 无重训练 | **PASS** |
| Q1 | 建立预测能力前提 | 完整 OOD-t \(R^2=0.56935\)、RMSE \(=0.15059\) | **PASS** |
| Q2 | 检验状态贡献和 transition involvement | paired mean/CI 与 official \(\Delta R^2\) 分离；removal primary | **PASS** |
| Q3 | 检验 weather response 与 complete-window fidelity | 84 对；actual 优于 donor/mean；非因果、非极端增强 | **PASS** |
| Limitations | representation/deployment → intervention boundary → external validity | 不否定主线，也不恢复 Q4 | **PASS** |
| Conclusion | problem → method → evidence → significance | 收束到 empirically testable and falsifiable internal-state claim | **PASS** |

---

## 3. 主线流

```text
输出准确不能单独验证内部世界状态
    ↓
从历史 EO、过去天气和地理构造 spatial predictive state
    ↓
未来天气、地理和 elapsed time 条件化同一个 shared transition
    ↓
从同一 z_t 对每个 horizon 直接得到 transitioned state
    ↓
state readout 产生显式 raster contribution r_h
    ↓
b_h + r_h 形成最终预测
    ↓
future-state anchor 训练状态内容；teacher/target 训练后移除
    ↓
Q1 有用预测能力 + Q2 可移除状态贡献 + Q3 天气替换响应/保真度
    ↓
在冻结协议下支持 forecast-bearing、weather-responsive predictive state
```

标题到 Conclusion 没有出现第二套创新点。论文没有被中途改写成纯 EO 精度模型、纯 benchmark、因果模拟器或完整物理状态模型。

---

## 4. 世界模型身份审计

### 4.1 为什么这是世界模型，而不仅是普通预测器

当前身份来自实际计算机制，而非文字命名：

1. 部分观测历史被压缩为显式空间状态 \(z_t\)；
2. 外生 future weather 只通过 \(T_\psi\) 推进状态；
3. 每个推进状态被解码回未来可观测量；
4. 状态读出 \(r_h\) 位于真实预测加法路径上；
5. training-only future representation anchor 塑造状态内容；
6. post-training interventions 允许同一冻结模型否证 state-use/weather-response 主张。

### 4.2 为什么状态不是旁路 probe

\(O_\omega(z_{t+h})=r_h\) 被直接加入 \(\widehat y_{t+h}=b_h+r_h\)。Q2 在加法切点令 \(\alpha=0\)，而非在旁路上训练 probe；paired degradation 因而直接检验该显式贡献是否承载预测增量。

### 4.3 为什么 Q3 不只是无定位的输出变化

Q3 的最终观测量仍是 forecast output，但干预位置被限定在 state-mediated weather path：历史、\(b_h\)、\(z_t\)、地理、时距、读出、样本、mask 和真值窗口固定，只有进入 \(T_\psi\) 的 future weather 改变。因此它检验的是所声明路径的 weather response 与 predictive fidelity；它仍不识别因果效应或保证反事实正确性。

### 4.4 TerraState 与最近邻的精确区别

- **EO-WM：** 概率 EO forecasting、物理启发 forcing 分解和 output-level extreme/seasonal response diagnostics；
- **VegSim：** latent vegetation state、用户指定天气下的 recurrent rollout、NDVI quantile scenario simulation；
- **TerraState：** 在同一个 observed-weather predictor 中，将 spatial predictive state 放到实际预测路径，直接移除其 forecast contribution，并比较 actual 与 frozen controls 的完整窗口 fidelity。

该区别是机制与证据接口的区别，不是世界模型的唯一合法定义。

**世界模型身份：4.8/5。**

---

## 5. Claim–evidence 矩阵

| 核心主张 | 出现位置 | 方法机制 | 实验证据 | 最大允许结论 | 禁止外推 |
|---|---|---|---|---|---|
| Useful OOD-t forecasting | Abstract、Intro、4.2、Conclusion | 完整 TerraState forecast | 1,904 minicubes；\(R^2=0.56935\)，RMSE \(=0.15059\) | temporal shift 下保留有用预测能力 | SOTA、严格排名、多种子稳定性 |
| Predictive state on forecast path | Abstract、Intro、3.1–3.2 | \(z_t\to T_\psi\to O_\omega\to r_h\to+\) | 架构事实 + Q2 | state 是最终预测的显式贡献源 | 所有信息都必须经过 state |
| State contribution is load-bearing | Intro、3.4、4.3、Conclusion | \(\alpha=0\Rightarrow\widehat y=b_h\) | Val paired \(0.01616\), CI \([0.00643,0.02590]\), \(n=589\)；OOD-t \(0.02200\), CI \([0.01422,0.03018]\), \(n=1,019\) | explicit state path carries measurable forecast increment | 完整物理状态、唯一信息瓶颈 |
| Official state-removal effect | 4.1、Table 2、4.3 | 同一冻结模型 | Val \(0.01121\)；OOD-t \(0.01997\) | dataset-level full-minus-removal scale | 把 official effect 配上 paired CI |
| Shared transition involvement | 3.4、4.3、Figure 3(a) | \(T_\psi\to I\) | Val paired \(0.01742\), CI \([0.00782,0.02696]\)；OOD-t \(0.02402\), CI \([0.01609,0.03217]\) | supporting evidence of learned-transition involvement | transition necessity；与 state removal 等同 |
| Detectable weather response | Abstract、3.4、4.4 | 只替换 \(T_\psi\) future-weather input | forecast-output difference 0.03592/0.08137；84/84 finite positive | supplied weather changes forecast through declared path | latent movement 即正确；因果效应 |
| Actual-weather complete-window fidelity | Intro、3.4、4.4、Conclusion | \(\Delta L=L_{\rm control}-L_{\rm actual}\) | donor \(0.00257\), CI \([0.00112,0.00399]\)；mean \(0.01126\), CI \([0.00547,0.01708]\) | actual weather has greater fidelity on frozen 84-pair complete window | 将 subset \(R^2=0.6254\) 当完整 OOD-t；counterfactual correctness |
| Future-state anchoring | Intro、3.3、Conclusion | frozen \(q_{\theta^0}/P_{\rho^0}\) 产生 terminal target；training only | 实现/训练合同，不是独立消融结论 | anchoring shapes transitioned representation | 单凭 anchor 证明 load-bearing/weather response |
| Testable/falsifiable state claim | Title、Abstract、Intro、Conclusion | removable \(r_h\) + substitutable future-weather path | Q1 prerequisite + Q2 + Q3 | evaluated protocol 下内部主张可经验检验和否证 | 世界模型普遍定义；完整验证所有内部状态 |
| Hot-dry null | Limitations | interaction guard | interaction 约 \(0.000436\)，CI \([-0.002162,0.003200]\) | 不支持 extreme-specific enhancement | 热旱条件带来额外增强 |
| Operational deployment gap | Limitations | 训练/评测使用 realized future weather | 未量化 operational forecast error shift | 部署输入差异可能影响状态和预测 | 已量化部署退化 |
| Cross-dataset limitation | Limitations | GreenEarthNet-only evaluation | 单一 temporal-shift setting | 不建立跨数据集泛化 | 普遍 EO 泛化 |

### 5.1 Q2 estimand 专项

- paired mean 只与 paired-bootstrap 95% CI 搭配；
- official \(\Delta R^2\) 作为独立 dataset-level statistic；
- Table 2、4.1 和 4.3 均保持这一分离；
- state removal 始终为 primary，\(T\to I\) 始终为 supporting。

### 5.2 Q3 符号专项

\[
\Delta L_{\rm ctrl}=L_{\rm control}-L_{\rm actual}.
\]

正值表示 control loss 更高、actual weather 更忠实。正文、Equation (8)、Table 3 和 Figure 3 的坐标解释一致；56/84 与 69/84 仅为描述性计数。

**Claim–evidence 对齐：5.0/5。**

---

## 6. 方法承诺兑现表

| Introduction / contribution 承诺 | Method 兑现位置 | Results 兑现位置 | 判定 |
|---|---|---|---|
| history-derived spatial predictive state | 3.1 Eq. (1)；3.2 \(q_\theta/P_\rho\) | Q2 state removal | **FULFILLED** |
| shared weather-conditioned transition | 3.1–3.2 Eq. (2)–(3) | Q2 \(T\to I\) supporting；Q3 substitution | **FULFILLED** |
| explicit state-mediated forecast path | Eq. (1)、Eq. (4) | Q2 primary intervention | **FULFILLED** |
| future-state anchoring | 3.3 Eq. (6)–(7) | 作为方法事实，不声称独立收益 | **FULFILLED WITH CORRECT SCOPE** |
| testable state contribution | 3.4 \(\alpha=0\) | Val/OOD-t paired evidence | **FULFILLED** |
| testable weather response/fidelity | 3.4 Eq. (8) | 84-pair Q3 | **FULFILLED** |
| same trained model | 4.1 | Q1–Q3 | **FULFILLED** |
| bounded world-model claim | 3.1/3.4 boundaries | Limitations/Conclusion | **FULFILLED** |

没有承诺 composition、recursive rollout、完整物理状态、因果模拟或 SOTA。

---

## 7. 数字与训练身份核对

### 7.1 训练身份

当前权威正文与三个镜像的 Section 4.1 均写为：

- 40 epochs；
- 14,880 updates；
- global batch size 64；
- non-\(q\) branch core learning rate \(3\times10^{-5}\)；
- Q1–Q3 使用同一最终模型；
- Q2/Q3 是 frozen forward interventions，不重新训练；
- teacher 和 future target encoder 只属于训练，推理时移除。

`paper/main.tex`、三份镜像正文均未出现 11,904 或 boundary80。较早
`evidence_workspace/results_ledger.json` 仍保存 11,904/boundary80 release identity；
按作者指定事实优先级，它是被 14,880-update 正文和最新 Section 4 终审覆盖的历史
记录，**不得恢复进论文**。这一外部历史记录不计入当前正文问题数量。

### 7.2 冻结数值回归

| 项目 | 当前数字 | 作用域 | 判定 |
|---|---|---|---|
| Q1 OOD-t | \(R^2=0.56935\), RMSE \(=0.15059\), \(n=1,904\) | 完整 OOD-t | **PASS** |
| Q2 Val removal | official 0.01121；paired 0.01616，CI \([0.00643,0.02590]\), \(n=589\) | Val paired units | **PASS** |
| Q2 OOD-t removal | official 0.01997；paired 0.02200，CI \([0.01422,0.03018]\), \(n=1,019\) | OOD-t paired units | **PASS** |
| Q2 \(T\to I\) | Val 0.01742；OOD-t 0.02402，各有 paired CI | supporting only | **PASS** |
| Q3 subset | 84 frozen pairs；31 geographic clusters；45 unique controls | frozen matched subset | **PASS** |
| Q3 donor | \(\Delta L=0.00257\)，CI \([0.00112,0.00399]\) | control minus actual | **PASS** |
| Q3 mean | \(\Delta L=0.01126\)，CI \([0.00547,0.01708]\) | control minus actual | **PASS** |
| Q3 descriptive | 56/84、69/84 | non-inferential counts | **PASS** |
| subset score | \(R^2=0.6254\) | Table 3 matched subset only | **PASS** |

所有正文、表格和正式 captions 中的数值作用域正确；没有把 subset
\(R^2=0.6254\) 写成完整 OOD-t。

---

## 8. 术语表

| 规范术语 | 当前含义 | 使用情况 |
|---|---|---|
| TerraState | 方法名 | 一致 |
| predictive state | 由历史推断、被 forcing 推进且进入预测的表示 | 一致 |
| spatial predictive state | \(z_t\in\mathbb R^{N\times d}\) 的 patch-token state | 一致 |
| transitioned / advanced state | \(z_{t+h}\) | 两词均可恢复同一对象；`transitioned` 更稳定 |
| context-only prediction/forecast | \(b_h\) | 一致 |
| state-mediated contribution | raster \(r_h\) | 一致 |
| shared transition | 参数跨 patch/horizon 共享；condition value 可空间变化 | 一致 |
| future weather / meteorological forcing | \(u_{t+1:t+h}\) | 作为普通语言同义词，路径一致 |
| future-state anchor/anchoring | terminal training-only representation target | 一致 |
| state removal | 评测期 \(\alpha=0\) | 一致 |
| identity transition | \(T_\psi\to I\)，supporting | 一致 |
| matched-donor weather | season-, geography-, quality-matched control weather | 一致 |
| normalized-mean weather | frozen global z-score weather space 中的零 | 一致 |
| complete-window fidelity | 完整 20-step masked loss 的 actual-vs-control comparison | 一致 |
| EO world model | 任务限定的 predictive-state world-modeling identity | 一致且有范围 |

投稿英文正文没有混入 B0/B4、Stage A/B、exclusive、MAIN-last、boundary80、
pilot、smoke、cache、teacher SHA 或 checkpoint path。`contract` 只在 Figure 1
caption 的 “testable EO world-modeling contract” 中作为自然的接口概括出现，不是
内部 gate 语言。

---

## 9. 符号和公式审计

### 9.1 Equations (1)–(8)

| 公式 | 核对 | 判定 |
|---|---|---|
| (1) | \(q/P/T/O\)、\(z_t,z_{t+h},b_h,r_h,\widehat y\) 的职责和类型稳定 | **PASS** |
| (2) | weather prefix、patch geography、horizon condition 融合正确 | **PASS** |
| (3) | residual update；每个 horizon 从同一 \(z_t\) 直接推进 | **PASS** |
| (4) | \(O_\omega\) 输出 raster \(r_h\)，正常路径 \(\alpha=1\) | **PASS** |
| (5) | GT 与 KD 的 mask/aggregation 不混淆；teacher stop-gradient | **PASS** |
| (6) | terminal future-state target；future EO training only；future weather zero | **PASS** |
| (7) | GT + 0.5 KD + \(\lambda_s\) FS；teacher/target 推理期移除 | **PASS WITH REPRO NOTE** |
| (8) | actual/donor/mean；完整窗口；control-minus-actual 方向 | **PASS** |

### 9.2 Minor m1：符号自包含与复用

- **位置：** `main.tex:212–216,326–345,354–382,428–444`。
- **问题：** \(b_h\) 已表示 context-only forecast，Eq. (5) 又用 \(b\) 作为 minicube
  index；\(m_i\) 先表示历史帧 validity mask，Eq. (6) 又表示 terminal patch mask；
  Eq. (8) 的粗体 \(\widehat{\mathbf y},\mathbf y\) 没有单独说明是完整 20-step window。
- **影响：** 不改变公式事实，但增加读者恢复不同粒度 index/mask 的负担。
- **最小方向：** 最终文本修订时只改 index/mask 符号并补一句粗体 window 定义；
  不改变任何 loss、mask 或 inference path。

---

## 10. 训练与复现身份

### 10.1 已满足的主文信息

- 模型参数量、optimizer、epochs、updates、global batch、核心学习率；
- validation-only model selection；
- Q1–Q3 同一最终模型；
- frozen intervention / no retraining；
- student、KD teacher、future-state target 的输入权限和推理去向；
- GT/KD/FS 目标的数学定义。

### 10.2 Minor m2：训练自包含与复现配置

- **位置：** `main.tex:312–324,386–398`。
- **问题：** KD teacher 的输入列表写为 observation history、static geography 和
  complete future weather，没有显式点名实际还读取的 past weather；正文说 student
  参数按 training schedule 更新，却没有报告 \(\lambda_s\) 数值 schedule 和具体
  unfreezing schedule。
- **影响：** 不影响方法身份或结果解释，但单靠主文不能完整恢复训练。
- **最小方向：** 在附录/reproducibility checklist 或代码配置中给出 past-weather
  teacher input、\(\lambda_s\) schedule 和解冻计划；不把工程 checkpoint/SHA 塞回
  Section 3。

---

## 11. Related Work 与引用

### 11.1 Citation graph

| 项目 | 结果 |
|---|---:|
| `\cite...{}` 中的 key occurrences | 28 |
| unique cited keys | 22 |
| BibTeX entries | 24 |
| missing cited keys | 0 |
| duplicate BibTeX keys | 0 |
| unused entries | 2 |

未使用项为 `chen2023deeposg` 和 `wang2026groupactions`，均对应已退出正文的
composition/group-action 分支。未使用条目不会出现在最终参考文献列表，不构成引用
错误；可在最终 bibliography hygiene 阶段清理，但本轮不得修改。

### 11.2 最近邻状态与主张支持

| 工作 | 当前状态 | 正文定位 | 审计 |
|---|---|---|---|
| EarthNet2021 | CVPRW 2021 | future-weather-conditioned guided video prediction dataset/task | **SUPPORTED** |
| GreenEarthNet/Contextformer | CVPR 2024 | vegetation forecasting、cloud mask、temporal-shift evaluation | **SUPPORTED** |
| Diaconu weather analysis | CVPRW 2022 | weather value + single-variable output response | **SUPPORTED** |
| VegeDiff | IEEE TGRS 2025 | probabilistic/multiple-future vegetation forecasting | **SUPPORTED**；key 含 2024 不改变正式年份 |
| ViT-Koop | ICCVW 2025 | compressed EO latent state + linear Koopman advancement | **SUPPORTED** |
| EO-WM | arXiv preprint 2026 | partially observed/weather-driven framing、forcing decomposition、output diagnostics | **SUPPORTED** |
| VegSim | arXiv preprint 2026 | latent vegetation state、user-weather recurrent rollout、NDVI quantiles | **SUPPORTED** |
| Cloud observability | arXiv preprint 2026 | usable-acquisition observability，而非 land-surface pixel forecast | **SUPPORTED** |
| PSR | NeurIPS 2001 | state through future observables | **SUPPORTED WITH SCOPE**；未声称充分统计保证 |
| World Models/PlaNet/Dreamer | arXiv/ICML/ICLR | compact latent dynamics for prediction/control | **SUPPORTED** |
| I-JEPA/V-JEPA | CVPR 2023/TMLR 2024 | representation prediction | **SUPPORTED** |
| LatentTSF | ICML 2026, PMLR 306 | accurate forecasts can coexist with temporally disordered latent representations | **SUPPORTED** |
| PLSM | NeurIPS 2024 | action-conditioned latent-state regularization in control | **SUPPORTED WITH SCOPE** |

Primary-source checks used the
[CVF EarthNet2021 record](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/html/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.html),
[CVF GreenEarthNet record](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html),
[Diaconu paper](https://openaccess.thecvf.com/content/CVPR2022W/EarthVision/papers/Diaconu_Understanding_the_Role_of_Weather_Data_for_Earth_Surface_Forecasting_CVPRW_2022_paper.pdf),
[CVF ViT-Koop record](https://openaccess.thecvf.com/content/ICCV2025W/SEA/html/Shinohara_ViT-Koop_Vision-Transformer-Koopman_Operators_for_Efficient_Time-Series_Forecasting_of_Earth-Observation_Data_ICCVW_2025_paper.html),
[EO-WM](https://arxiv.org/abs/2606.27277),
[VegSim](https://arxiv.org/abs/2606.21961),
[cloud-observability preprint](https://arxiv.org/abs/2607.13651),
[official ICML 2026 downloads](https://icml.cc/Downloads/2026), and
[VegeDiff DOI](https://doi.org/10.1109/TGRS.2025.3564317).

未发现已确认的作者、题目、venue、年份、页码、DOI 或 arXiv identity 错误。
`yang2026latenttsf` 的 PMLR volume 和正式 ICML 身份可由正式 PDF确认；当前未能从
PMLR landing page 独立取得最终 page range，记为非阻塞 metadata unknown。

### 11.3 Minor m3：Table 1 数值来源与不确定性透明度

- **位置：** `main.tex:530–570`。
- **事实：** 公共 baseline 数值与 GreenEarthNet 正式论文 Table 2 的 central
  values 一致；原文对 ConvLSTM、PredRNN、SimVP、Contextformer 报告
  mean \(\pm\) std，而 Earthformer 是单 seed。当前 Table 1 只显示 central values，
  不声称它们都是单 seed，也不声称严格排名。
- **问题：** comparison paragraph/Table 1 caption 没有邻接引用
  `benson2024multimodal`，也没有说明源论文中的 uncertainty terms 被省略。
- **影响：** 数字本身正确，且正文明确不由表格排名建立 Q2/Q3；但来源和省略规则对
  审稿人不够自证。
- **最小方向：** 后续只在 comparison sentence 或 caption 加一个 GreenEarthNet
  citation 和简短 central-value/uncertainty-omission note；不要加入
  Published/Local、run/seed 标签或严格排行榜叙事。

### 11.4 可比性

公共行与 TerraState 属于同一 GreenEarthNet temporal-shift benchmark family，但
公开论文没有暴露 TerraState 当前 manifest SHA/evaluator revision，因而不是严格
同协议排行榜。当前正文通过 “performance context”“mixed profile”“not by table
rank” 正确处理这一点。

**引用准确性：4.6/5。**

---

## 12. 表格与正文接口

| 表 | 检查 | 判定 |
|---|---|---|
| Table 1 | TerraState 数值与 4.2 一致；公共 central values 未人为降低；无 \(\pm\)、SOTA、Published/Local、single-run 标签 | **PASS WITH MINOR SOURCE NOTE** |
| Table 2 | full/intervention scores、official estimand、paired mean/CI、\(n\)、primary/supporting 层级与正文一致 | **PASS** |
| Table 3 | 84-pair subset；\(\Delta L=\) control minus actual；geo-cluster CI；counts descriptive；subset \(R^2\) 限定清楚 | **PASS** |

TerraState 是三表唯一主体方法。Table 1 只建立 Q1 forecasting context；Table 2–3
负责同模型内部证据。没有 matched subset 冒充完整 OOD-t。

---

## 13. Abstract 最终一致性

Abstract 与最终正文一致：

- problem：fixed-horizon output accuracy 不能单独建立 forecast-bearing/weather-responsive state；
- identity：testable predictive-state world model；
- mechanism：history state、shared future-weather transition、explicit contribution；
- interfaces：state removal、identity supporting、actual/donor/mean；
- evidence：useful forecast、Val/OOD-t state-removal degradation、84-pair complete-window fidelity；
- takeaway：load-bearing/weather-responsive，且不延伸到 causal/composition/SOTA。

**Abstract 一致性：5.0/5。**

---

## 14. 英文写作统一

投稿正文的段落首句、术语、时态和证据顺序达到成熟 AAAI 方法论文标准：

- Introduction 为 task→gap→question→method→evidence；
- Related Work 每段有独立比较轴；
- Method 为 requirement→mechanism→equation→interface；
- Results 先结论、再统计、再有限解释；
- Limitations 按 representation/deployment→evidence→external validity；
- Conclusion 为 problem→method→evidence→significance。

未发现影响审稿理解的 AI 式宣传、空泛 novelty、反复防御或内部审计语气。
`operational`, `contract`, `frozen` 等词均出现在有明确科学/协议含义的位置，未形成
工程报告风格。

**英文写作：4.8/5。**

---

## 15. 中文与 Markdown 镜像

### 15.1 `MANUSCRIPT_ZH_FULL.md`

正文 Sections 1–6 与 `main.tex` 的机制、公式、数字、限定词和主张强度基本同步。
中文没有把 `may/supports` 放大为必然或证明，也没有把 conditional fidelity 写成
因果/反事实正确性。

### 15.2 Major M1：两个精简镜像保留旧 Abstract/Method

- **位置：**
  - `MANUSCRIPT.md:3,7,47–119`；
  - `MANUSCRIPT_ZH.md:3,7,47–117`。
- **问题：**
  1. 两文件都声称已与 `main.tex` 同步，但 Abstract 仍使用
     `selected almost entirely`、`reusable world states` 和
     `endpoint predictions / 端点预测`；
  2. 旧 Method 使用 \(u_{t:t+H}\) / \(u_{t:t+h}\)，而权威边界是
     \(u_{t+1:t+H}\) / \(u_{t+1:t+h}\)；
  3. 旧 Method 使用 \(s\in\{0,1\}\) 的简化接口并省略当前 Equations (5)–(8) 的
     精确定义；
  4. Q3 仍被写成 endpoint fidelity；
  5. 独立恢复 `Exploratory composition (Q4)`。
- **审稿/作者影响：** 两文件不是投稿权威源，但它们是明确标注的英文/中文审阅镜像；
  作者按镜像审阅或复制时会重新引入已冻结删除的 Q4 和 endpoint-only Q3，破坏全文
  主线与证据边界。
- **最小修复方向：** 仅把两个精简镜像的 Abstract 和 Section 3 同步到当前
  `main.tex` / `MANUSCRIPT_ZH_FULL.md`，删除 Q4 段并恢复 complete-window Q3；
  Sections 1、2、4–6 当前内容不需要重写。
- **是否需改投稿正文：** **否。**

### 15.3 Minor m4：完整中文的非投稿导航仍含历史审计残留

- **位置：** `MANUSCRIPT_ZH_FULL.md:471–499`。
- **问题：** 导航称“正文引用键共 24 个”，而当前 `main.tex` 实际引用 22 个 unique
  keys、BibTeX 才有 24 条；问题清单仍写“一次训练、不同协议公开比较”，claim 表仍
  保留 Q4 行。
- **影响：** 明确标为“非投稿正文”，不影响英文稿；但会误导作者的最终肉眼审核。
- **最小方向：** 在镜像同步轮删除或更新这些导航项；不得把其历史语言写回论文。

**完整中文正文：4.8/5；精简镜像一致性：2.5/5。**

---

## 16. 禁止叙事回归

### 16.1 投稿权威正文

| 词项/叙事 | 语义核对 |
|---|---|
| Q4 | 0 次 |
| composition/compositional | 只在 Related Work 和 Figure 2 caption 的否定边界中出现 |
| non-collapse/group action | 0 次 |
| causal/counterfactual | 只在范围否定中出现 |
| complete physical state | 只是否定边界 |
| SOTA/state-of-the-art/strict ranking | 0 次 |
| extreme-specific enhancement | 只是否定边界 |
| 11,904/boundary80 | 0 次 |
| endpoint-only | 0 次 |
| single-run/Published/Local | 0 次 |
| \(\pm\) / `±` | 0 次 |
| Stage A/B、B0/B4、pilot/smoke | 0 次 |

### 16.2 镜像

`MANUSCRIPT.md` 与 `MANUSCRIPT_ZH.md` 各恢复一段 Q4，并把 Q3 写为 endpoint；
这是 Major M1。`MANUSCRIPT_ZH_FULL.md` 仅在非投稿导航保留历史 Q4/一次训练措辞，
是 Minor m4。

---

## 17. PDF 只读检查

当前 `paper/main.pdf`：

- 9 页；
- metadata 不含作者、机构或路径泄漏；
- 0 个越出页面边界的文本 block；
- 当前构建日志无 LaTeX error、undefined citation/reference 或 overfull；
- Figure 3 保持单栏布局；
- Tables 1–3、Conclusion 和 References 可恢复正常阅读顺序；
- 无裁切、覆盖、跨栏侵入或阻塞性空白。

### Minor m5：Limitations 的跨页断词

`Optical` 在第 6 页末断为 `Op-`，第 7 页在页顶三张表之后续为 `tical`。语义可恢复，
无文字丢失或覆盖，但阅读节奏不理想。最终 layout gate 可自然消除；不得通过负间距、
缩小字号或改动科学内容强行修复。

**PDF 呈现：4.5/5。**

---

## 18. Critical / Major / Minor / Optional

### Critical（0）

无。

### Major（1）

#### M1 — 两个精简镜像保留旧 Abstract、旧 Method、endpoint Q3 与 Q4

见第 15.2 节。只需同步 `MANUSCRIPT.md` 和 `MANUSCRIPT_ZH.md`；不修改投稿正文。

### Minor（5）

1. **m1：** Eq. (5)/(6)/(8) 的 \(b\)、\(m_i\) 和粗体窗口符号自包含性；
2. **m2：** KD teacher 未显式点名 past weather，\(\lambda_s\)/解冻 schedule 未在
   主文或当前 checklist 中给出；
3. **m3：** Table 1 缺邻接 baseline source citation 与 uncertainty-omission note；
4. **m4：** `MANUSCRIPT_ZH_FULL.md` 非投稿导航的 24-key、一次训练和 Q4 历史残留；
5. **m5：** PDF 中 `Optical` 被页顶浮动表隔开的跨页断词。

这些 Minor 不改变方法、数字、主线或可信度；若 M1 修复，均可留到最终文本/附录/
排版门禁处理。

### Optional（3）

1. 最终 bibliography hygiene 可移除两条未使用的 composition 条目；
2. 历史 `results_ledger.json` 仍记录 11,904/boundary80，应在独立证据台账维护任务中
   标为 superseded；本轮不得修改；
3. 可在最终排版自然改善 Introduction 结果句跨 Figure 1 分页和 Conclusion 末句的
   轻微修辞密度。

---

## 19. 评分表

评分：1=明显不成熟；3=可用但需实质修改；4=投稿成熟；5=高度成熟。

| 维度 | 分数 / 5 | 判断 |
|---|---:|---|
| 标题到结论的主线 | **4.9** | 单一 testable predictive-state story |
| 世界模型身份 | **4.8** | 机制、on-path state 与 evidence interface 闭合 |
| 方法承诺兑现 | **4.8** | 所有 Introduction 承诺均有 Method/Result 落点 |
| Q1–Q3 claim–evidence | **5.0** | 数字、统计单位、方向和最大结论准确 |
| 训练身份 | **4.9** | 正文统一 40 epochs / 14,880 updates |
| 术语一致性 | **4.7** | 权威英文与完整中文稳定 |
| 符号/公式可读性 | **4.5** | 事实正确，有局部符号复用 |
| Related Work/引用 | **4.6** | 最近邻公平准确；Table 1 attribution 可加强 |
| 表格—正文接口 | **4.8** | primary/supporting/subset 层级清楚 |
| Abstract 一致性 | **5.0** | 与最终正文完全同构 |
| 英文写作 | **4.8** | 成熟、紧凑、无内部报告感 |
| 完整中文镜像 | **4.8** | 正文同步且主张强度一致 |
| 精简镜像同步 | **2.5** | 旧 Abstract/Method/Q3/Q4 阻止全文文本包冻结 |
| PDF 呈现 | **4.5** | 无阻塞，存在一项跨页断词 |

因为“精简镜像同步”低于 4/5 且构成 Major，当前不满足
`FULL_TEXT_GLOBAL_CONSISTENCY_PASS` 的全部条件。

---

## 20. 一轮最小修复集合

### 必须

1. 仅同步 `MANUSCRIPT.md` 的 Abstract 与 Section 3 到当前 `main.tex`；
2. 仅同步 `MANUSCRIPT_ZH.md` 的 Abstract 与 Section 3 到
   `MANUSCRIPT_ZH_FULL.md`；
3. 删除两个精简镜像中的 Q4/composition 段，将 Q3 从 endpoint 恢复为完整 20-step
   forecast-window fidelity；
4. 回归确认 Sections 1、2、4–6、所有数字和 14,880 updates 未变化。

### 可与上述同轮处理但不阻塞

- 更新 `MANUSCRIPT_ZH_FULL.md` 的非投稿导航；
- 表格 caption/复现 checklist/符号的小幅收敛；
- 不修改任何实验、结果、方法事实、公式语义、Figure 或 BibTeX。

---

## 21. 当前文件和局部 SHA-256

### 21.1 文件

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `1fe12204bad54b2b18a8debd5792cab9dff85a1e342cc35ca8df0e9a2d6eaab9` |
| `paper/main.pdf` | `5f3931e373643d7aa3674fa3517e2e4f1e58f1632bd279b513d11f28bc021691` |
| `MANUSCRIPT_ZH_FULL.md` | `0577238cd6d9561fb9ca7ea9fa4d8275da74a5b5f447e1d0407c4390d66099c6` |
| `MANUSCRIPT.md` | `8c8c47c00bc1ebc7337269f268539dfb9869fb73bc9a4feb2cc385a0ac3ebe21` |
| `MANUSCRIPT_ZH.md` | `d957d421af7efafb73d94ebd4775b3a1c150f01574d927c22197d27ac4c2f4ac` |
| `paper/references.bib` | `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659` |

### 21.2 `main.tex` 局部区块

| 区块 | SHA-256 |
|---|---|
| Abstract | `d6b87d771098c2678e263cd60c5b84bdd556acd5b4a1f7f678db3d398ce757fc` |
| Introduction | `ce34d1ca444bf783eb4ccad116bfb1f4a9dde7f67a1d03dddd328eff04bc2b92` |
| Related Work | `e6609d90667a20d41e196bca0c1da50e6b928428e707439b6368d155eee4bc94` |
| Method | `ac8c836546f41efdddda3be863abf6a22baf2562ce6d92b31405065afc28f6aa` |
| Experiments | `85f681270b339a1c4f9e0cb73bb2777dc131d1f1e5585329609c6f778b0452a4` |
| Limitations | `e4f1456ff2609d44d8f74ad66474e6e8a831184cd59cdffdd0411f6dba4fa186` |
| Conclusion | `21f9dadc2155a1d21c48e1c2456cc9fdc05dc088eaa0e9510ee21d244337f5b1` |
| Table 1 environment | `ec5b1dd99126d54306894f5263c9f1dad6247ae2c805899fc00e0d75c2f3cfce` |
| Table 2 environment | `5281b09bbfaff9f57ed1ef17f243b161d2588ea571c7aca393ce0b62fadb1197` |
| Table 3 environment | `f2f9dd7ec9f212ce132d7e597d2be04085b54d9979327783d81eaacc552dc55d` |

---

## 22. 只读声明

本审计没有修改或重新编译：

- `paper/main.tex`、`paper/main.pdf`；
- 三份 MANUSCRIPT；
- `references.bib`；
- Figure 1–3、Table 1–3；
- 实验 JSON、模型、代码、checkpoint 或数据。

本轮只新建：

- `FULL_TEXT_GLOBAL_CONSISTENCY_AUDIT_20260728.md`；
- `DEFERRED_FIGURE_ISSUES_20260728.md`。

Figure 问题全部进入独立延期清单，未计入正文 Critical/Major。当前返修原因仅为两个
精简文本镜像未同步。

