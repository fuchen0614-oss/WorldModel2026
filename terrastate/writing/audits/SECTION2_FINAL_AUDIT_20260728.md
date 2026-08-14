# TerraState Section 2 Related Work 最终只读审计

审计日期：2026-07-28  
审计对象：`paper/main.tex` 中最新 Section 2、当前 PDF 对应页面及三份 Markdown 镜像  
最终判定：**SECTION2_FROZEN**

## 1. 最终 verdict

**SECTION2_FROZEN**

- Critical：**0**
- Major：**0**
- Minor：**0**
- Optional：**2**

当前三段分别围绕“EO 预测范式与输出证据”“EO 世界模型中的 forcing/rollout/response”“预测状态与潜动力学如何定义和约束状态”展开，比较轴清楚且互不替代。最近邻定位公平、具体，TerraState 的差异被限定为方法与证据接口的差异，没有被写成世界模型的唯一合法定义。

正文共 **348 个英文词**（不含三个 paragraph 标题与引用命令），信息密度和篇幅符合紧凑的 AAAI Related Work。未发现会影响审稿人理解、事实可信度或冻结条件的问题。

## 2. 审计范围、输入与局部冻结

已完整阅读用户指定的以下材料：

- `paper/main.tex`：Abstract、Introduction、Related Work、Method 开头，并交叉检查 Section 3.4、Section 4、Limitations、Conclusion 与 Figure 1--3 captions；
- `paper/main.pdf`：Related Work 所在页面；
- `SECTION1_FINAL_AUDIT_20260728.md`；
- `SECTION1_REVISION_LOG_20260728.md`；
- `SECTION2_REVISION_LOG_20260728.md`；
- `SECTION1_2_AAAI_WRITING_CALIBRATION_AND_PREAUDIT_20260728.md`；
- `MANUSCRIPT_ZH_FULL.md`、`MANUSCRIPT.md`、`MANUSCRIPT_ZH.md`；
- `METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md`；
- `RESULTS_CLAIM_EVIDENCE_AUDIT.md`；
- `SECTION4_4_1_FINAL_AUDIT_20260728.md` 至 `SECTION4_4_4_FINAL_AUDIT_20260728.md`；
- `paper/references.bib`。

本次判定不继承修订日志的结论，而是重新完成段落结构、近邻事实、引用邻接、主张边界、中英文镜像和跨章节一致性检查。

### 当前精确哈希

| 对象 | SHA-256 |
|---|---|
| `paper/main.tex`（审计开始） | `0bd80eb824005857fb03930c74a581b153417019559974476d12d94dd3d79d00` |
| `paper/main.tex`（Figure 3 并发更新后复读） | `1fe12204bad54b2b18a8debd5792cab9dff85a1e342cc35ca8df0e9a2d6eaab9` |
| Section 2 局部区块（含 `\section{Related Work}`，不含 `\section{Method}`） | `e6609d90667a20d41e196bca0c1da50e6b928428e707439b6368d155eee4bc94` |
| `paper/main.pdf` | `a9892a795aa3f506c844cce184234f82bc507959b4dec8cde219d8386104c7e6` |
| `MANUSCRIPT.md` Related Work 局部区块 | `948e3249fa5c85d1f10447d68a6d66c03a8f32a3e1fb5a84a768e175f0462009` |
| `MANUSCRIPT_ZH.md` Related Work 局部区块 | `141a3d704ed1dcbc28c1d4b8a9348ed38440e1ad965ed365507f4d9d3cc1b212` |
| `MANUSCRIPT_ZH_FULL.md` Related Work 局部区块 | `7f1e6ffedcd1b670e4578c842531e2bc3a863c503d52caa0b402ddabd145cd83` |

审计期间 Figure 3 会话更新了 `main.tex` 的整文件 SHA。发现变化后，本审计重新读取了最新版 Abstract、Introduction、Related Work、Method 开头和 Figure 3 caption；Abstract、Introduction、Section 2 和 Method 开头的局部 SHA 均与审计起点一致，其中 Section 2 仍为上表所列 `e6609d...bc94`。因此整文件并发变化不影响本次 Section 2 判定。

## 3. 三段反向提纲

| 段落 | 唯一比较维度 | 段内论证动作 | 段末 TerraState 定位 | 判定 |
|---|---|---|---|---|
| Weather-conditioned EO forecasting | 输入/目标、确定性与概率预测、显式潜转移及主要评价证据 | EarthNet2021/GreenEarthNet 建立任务；Diaconu 承认既有天气分析；再按 deterministic、probabilistic、latent-transition 三类综合 | 在保留输出评价的同时，增加 state-mediated contribution 与 supplied-weather response 的直接检验 | PASS |
| EO world models and forcing-conditioned simulation | 是否显式表示状态、future forcing 如何进入、是否 rollout、response 如何评价、任务目标差异 | 具体说明 EO-WM、VegSim，并以 cloud-aware observability 划定不同预测目标 | 检验 observed-weather predictor 中的 removable state contribution，以及 actual-vs-frozen-control complete-window fidelity | PASS |
| Predictive-state and latent-dynamics foundations | 状态如何定义与监督、潜动力学服务预测或控制、状态是否进入实际计算路径 | PSR 给出概念基础；World Models/PlaNet/Dreamer、JEPA、LatentTSF、PLSM 分别承担动力学、表示预测、反例和控制约束功能 | 结合 future-representation anchor、on-path transitioned state 与 intervention interfaces，同时明确不主张经典 PSR 保证、因果/物理状态或组合动力学 | PASS |

Deep-OSG、World Models as Group Actions 及原 composition-oriented 尾句已从 Section 2 正文中删除，没有残留断句或悬空引用。

## 4. AAAI Related Work 写作定式审计

| 检查项 | 结论 | 依据 |
|---|---|---|
| 主题句定义研究路线 | PASS | 三段首句分别定义 EO forecast task、近期 forcing-conditioned EO world modeling、predictive-state definition。 |
| 按范式综合而非逐篇摘要 | PASS | 第一段按三类预测路线综合；第三段按状态定义、潜动力学、表示预测与控制约束综合。第二段因只有三个直接近邻而采用必要的具体说明。 |
| 最近邻公平而具体 | PASS | EO-WM、VegSim、Diaconu、ViT-Koop 均被明确承认其已有能力，没有通过缺失性陈述制造 novelty。 |
| 段末同维度定位 TerraState | PASS | 三句分别落在 forecast evidence、forcing-conditioned world-model evidence、predictive-state mechanism/interface，功能互补。 |
| 不重复 Introduction 完整 gap | PASS | 没有重新展开 Q1--Q3 证据链，也没有复制 Introduction 的问题陈述。 |
| 不重复 Method 细节 | PASS | 仅保留辨识 TerraState 所需的接口级概括，没有公式、模块输入输出或统计协议。 |
| 不写实验结果 | PASS | 无数值、置信区间、样本数或结果方向统计。 |
| 无论文名单感 | PASS | 引用较密但由范式句法组织；模型名均承担分类或最近邻功能。 |
| 语言节奏 | PASS | 348 词；段落长度均衡。最长定位句虽密集，但语法边界清楚。 |
| 自信且不过度攻击 | PASS | 使用 “retains”“does not replace those aims”“combines”等具体定位，没有 “existing methods fail” 或 “unlike all prior work”。 |

未发现机械重复的 `however`、宣传性 novelty 口号、AI 式空泛总结或把 operational tests 升格为普遍定义的表述。

## 5. 最近邻逐项定位审计

| 工作 | 当前 Section 2 的作用与事实核对 | 公平性/边界 | 结论 |
|---|---|---|---|
| EarthNet2021 | 准确用于建立由卫星历史、未来天气和地理信息驱动的地表观测预测任务；正式状态为 CVPRW 2021。 | 未被写成 TerraState 的直接方法竞争者或新 benchmark。 | PASS |
| GreenEarthNet/Contextformer | 准确用于 vegetation forecasting、cloud-aware target/masking 与 meteorological conditioning；正式状态为 CVPR 2024。 | 未暗示 TerraState 创建或替代该基准。 | PASS |
| Diaconu weather analysis | 明确认可天气输入的预测价值及单变量天气变化下的输出响应；正式状态为 CVPRW 2022。 | 没有声称此前无人研究 weather response。 | PASS |
| VegeDiff | 与 MCVD 一起承担概率/多未来预测路线；BibTeX 年份为 2025，正式状态为 IEEE TGRS 2025。 | 未暗示它采用与 TerraState 相同的状态干预。key 中的 `2024` 未被误当作出版年份。 | PASS |
| ViT-Koop | 准确表述其使用线性 Koopman operator 推进 compressed EO state；正式状态为 ICCVW 2025。 | 承认显式潜状态推进，没有武断声称其状态未经任何结构分析。 | PASS |
| EO-WM | 准确覆盖 partially observed、weather-driven framing，climatology/anomaly/accumulated stress，以及 extreme-summer 和 seasonal matched-pair output diagnostics。 | 置于 “Recent preprints” 下；TerraState 被写成证据接口的补充，不是 EO-WM 的简单替代。 | PASS |
| VegSim | 准确覆盖 sparse NDVI history、latent vegetation state、future-weather recurrent rollout、NDVI quantiles 与 scenario-conditioned simulation。 | 置于 preprint 语境；未将场景输出写成因果估计。 | PASS |
| Cloud-aware observability | 准确说明其预测 usable acquisition 是否及何时出现，而非未来 land-surface pixels。 | 只承担任务边界例子；置于 recent-preprint 语境。 | PASS |
| Predictive-state representation | 仅借用通过未来可观测量定义状态的概念。 | 明确否认 TerraState 具备 classical PSR sufficient-statistic guarantees。 | PASS |
| LatentTSF | 准确支持“准确 observation forecasts 可与 temporally disordered latent representations 共存”。 | `references.bib` 将其记录为 ICML 2026 正式论文，正文未称其为 preprint。 | PASS |
| PLSM | 准确说明其约束 actions 如何改变 latent states，并明确是 agent-action/control setting。 | 未把外生天气等同于 agent action。 | PASS |

### 主要原始/官方来源复核

- [EarthNet2021，CVPRW 2021](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/html/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.html)
- [GreenEarthNet，CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html)
- [Diaconu et al.，CVPRW 2022](https://openaccess.thecvf.com/content/CVPR2022W/EarthVision/html/Diaconu_Understanding_the_Role_of_Weather_Data_for_Earth_Surface_Forecasting_CVPRW_2022_paper.html)
- [ViT-Koop，ICCVW 2025](https://openaccess.thecvf.com/content/ICCV2025W/SEA/html/Shinohara_ViT-Koop_Vision-Transformer-Koopman_Operators_for_Efficient_Time-Series_Forecasting_of_Earth-Observation_Data_ICCVW_2025_paper.html)
- [EO-WM，arXiv preprint](https://arxiv.org/abs/2606.27277)
- [VegSim，arXiv preprint](https://arxiv.org/abs/2606.21961)
- [Cloud-aware EO observability，arXiv preprint](https://arxiv.org/abs/2607.13651)
- [LatentTSF，论文版本](https://arxiv.org/abs/2602.00297)；[ICML 2026 官方论文下载索引](https://icml.cc/Downloads/2026)
- [Predictive Representations of State，NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2001/hash/1e4d36177d71bbb3558e43af9577d70e-Abstract.html)
- [PLSM，NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/43ba0466af2b1ac76aa85d8fbec714e3-Abstract-Conference.html)
- [VegeDiff DOI，IEEE TGRS 2025](https://doi.org/10.1109/TGRS.2025.3564317)

上述核验只用于确认现有句子的事实与出版状态，没有扩张文献范围。

## 6. TerraState 三段差异分工

| 段落 | TerraState 增加的内容 | 与其他段的区别 | 主张安全性 |
|---|---|---|---|
| 第一段 | 对 state-mediated forecast contribution 和 supplied-weather response 的直接检验 | 回答“除了输出评价，还检查什么” | 不否认既有天气响应或表示分析 |
| 第二段 | 同一 observed-weather predictor 中的 removable state contribution，以及 actual weather 相对冻结 donor/mean controls 的 complete-window fidelity | 回答“相对最近 EO world models，证据接口具体不同在哪里” | 不声称因果、反事实正确性或替代 scenario simulation |
| 第三段 | future-representation anchor、显式 on-path transitioned state、状态/天气干预接口 | 回答“该状态在定义、训练和计算路径上如何落地” | 明确排除经典 PSR 充分性、完整物理状态、因果状态与组合动力学 |

三句定位具体、互补且与冻结 Introduction 一致。它们没有：

- 把 operational tests 写成世界模型的唯一合法定义；
- 把 TerraState 写成完整物理状态或通用生成模拟器；
- 将天气响应写成因果效应或 counterfactual correctness；
- 把 Q2/Q3 接口写成独立 benchmark；
- 恢复 Q4、non-collapse 或 composition 作为已验证主张；
- 声称 SOTA 或严格排名。

第三段的 “does not claim ... compositional dynamics” 是范围否定，不是恢复 Q4；它与 Limitations 中 “Temporal composition remains unexplored” 一致。

## 7. 引用准确性

### 静态检查

- Section 2 含 **14 处引用命令、21 个唯一 BibTeX key**。
- 21 个 key 均存在于 `paper/references.bib`。
- `references.bib` 共 24 个条目，未发现重复 key。
- 三份 Markdown 镜像均使用同一组 21 个 Section 2 key。
- Section 2 中不存在 `chen2023deeposg` 或 `wang2026groupactions`；删去相关正文后无残句。
- `zhao2024vegediff` 的 key 保持不变，但 BibTeX `year={2025}`、TGRS 卷 63、DOI `10.1109/TGRS.2025.3564317` 均按正式 2025 论文记录。
- “Recent preprints” 覆盖 EO-WM、VegSim 和 cloud-aware observability，比易失效的 “concurrent preprints” 更稳妥。
- 没有加入 RS-WorldModel、RemoteBAGEL、Earth-o1 等任务不同的工作。

### 引用邻接与支持范围

- EarthNet2021、GreenEarthNet、Diaconu、ViT-Koop、EO-WM、VegSim 和 observability 的引用均紧邻其具体事实陈述。
- ConvLSTM、PredRNN、SimVP、Earthformer 被综合为确定性时空预测背景；句子没有声称它们全部采用 TerraState 的 EO/weather protocol。
- MCVD 与 VegeDiff 只支持概率/多未来路线，没有被迫支持状态干预主张。
- World Models、PlaNet、Dreamer 只支持紧凑潜动力学用于预测/控制的概括。
- I-JEPA/V-JEPA 只支持 representation prediction，不承担 TerraState 世界模型身份的证明。
- LatentTSF 和 PLSM 的结论均带有必要边界，未外推到 EO weather forcing。

结论：未发现 missing key、错邻接引用、出版状态误写或引用被迫支撑超范围主张。

## 8. 英文与中文镜像

### 英文

- 三个标题准确概括段落比较轴。
- `world model`、`predictive state`、`latent dynamics`、`forcing`、`compressed EO state` 和 `transitioned state` 使用稳定。
- 没有过度使用机械转折；第二段的 “TerraState does not replace those aims” 对最近邻保持公平。
- 第一段模型数量较多，但通过 deterministic/probabilistic/latent-transition 三类句法综合，不构成名单式写作。
- 无 endpoint-only Q3、Q4、Deep-OSG、group-action、non-collapse、SOTA、counterfactual 或 hot-dry enhancement 表述。

### 中文

- `MANUSCRIPT_ZH_FULL.md` 与 `MANUSCRIPT_ZH.md` 的 Section 2 文本一致；`MANUSCRIPT.md` 与 LaTeX 英文正文一致。
- 中英文三段顺序、引用集合、最近邻事实和 TerraState 主张强度一致。
- “不取代这些目标”“不主张经典 PSR 的充分统计保证”等限定没有在中文中被提升为更强 novelty claim。
- 中文已清除旧 endpoint/Q4/composition 正向叙事。

中文中的“匹配 donor”保留了协议术语且不会造成理解错误；若以后进行全篇中文语言统一，可选改为“匹配供体（donor）天气”，但这不影响英文权威正文或本次冻结。

## 9. 跨章节一致性

| 对照对象 | 结果 | 说明 |
|---|---|---|
| Abstract | 一致 | 同为 forecast-bearing、weather-responsive predictive state；Related Work 没有增加结果强度。 |
| 冻结 Introduction | 一致 | 延续“输出准确不足以建立状态承载性”的问题，但未重复完整 gap 和 Q1--Q3 结果。 |
| Section 3 计算路径 | 一致 | on-path transitioned state、future-representation anchor、state/weather interfaces 均与真实 `q/P/T/O` 路径一致；未暗示 recursive TerraState rollout。 |
| Section 4 Q1--Q3 | 一致 | Related Work 只描述接口差异，不报告 Q1 数字、Q2 统计量或 Q3 数值。actual-vs-control 的方向与完整窗口 fidelity 定义一致。 |
| Limitations | 一致 | 都否认完整物理状态、因果/反事实正确性和已验证 composition；没有 extreme-specific enhancement。 |
| Conclusion | 一致 | 都只支持预测承载与真实天气相对冻结控制的忠实度。 |
| Figure 1--3 captions | 一致 | 图注中的 state contribution、forecast-window response fidelity 和非因果边界与 Section 2 定位一致。 |

未发现属于其他章节、需要后续同步的科学冲突。局部措辞差异均属于合理的章节功能差异。

## 10. 问题分级

### Critical（0）

NONE。

### Major（0）

NONE。

### Minor（0）

NONE。

### Optional（2）

| 位置/原句 | 原因 | 对审稿人理解的影响 | 可选最小方向 |
|---|---|---|---|
| 第二段末句：“TerraState does not replace those aims: it tests whether ...” | 该句约 35 词，同时承载 state contribution 与 complete-window fidelity 两个并列区别，信息较密。 | 不影响理解；冒号和并列结构已清楚划分两项证据。 | 仅在以后全篇节奏精修时考虑拆成两句；本轮无需修改。 |
| 中文第二段：“冻结的匹配 donor 和归一化均值控制” | 中英混排略弱于自然学术中文。 | 不改变技术含义、控制类型或主张强度。 | 后续中文统一时可写“冻结的匹配供体（donor）天气和归一化均值控制”；英文正文无需改。 |

两项均不影响可信度、事实准确性或审稿人对核心差异的理解，不构成返修条件。

## 11. 核心维度评分与冻结判定

评分范围为 1--5。

| 维度 | 分数 | 主要依据 |
|---|---:|---|
| AAAI 结构成熟度 | **4.8** | 三段均有主题句、范式综合、最近邻说明和同维度定位。 |
| 三段比较轴清晰度 | **5.0** | forecast evidence、forcing-conditioned world models、state/dynamics foundations 分工明确。 |
| 英文自然度 | **4.7** | 紧凑、专业，无宣传口号；仅一处可选的长定位句。 |
| 引用准确性 | **4.9** | 21 个 key 完整存在，邻接合理，正式/预印本状态准确。 |
| 最近邻定位 | **4.9** | 公平承认 EO-WM、VegSim、Diaconu、ViT-Koop 的已有能力，并限定 TerraState 差异。 |
| TerraState 主线一致性 | **4.9** | state on path、removable contribution、actual-vs-control fidelity 三层定位与冻结主线一致。 |
| 主张边界安全性 | **5.0** | 无 SOTA、因果、反事实、完整物理状态、Q4/non-collapse 或 extreme-specific enhancement。 |
| 中英文镜像一致性 | **4.8** | 结构、引用和主张强度一致；仅有可选术语自然化。 |
| 跨章节一致性 | **4.9** | 与 Abstract、Introduction、Method、Q1--Q3、Limitations、Conclusion 和图注无事实冲突。 |

所有冻结要求均满足：

- Critical = 0，Major = 0；
- 三段具有明确且不同的比较维度；
- 最近邻定位公平、准确；
- 无论文名单式组织；
- 与冻结 Introduction 一致；
- 未恢复 Q4、因果、完整物理状态、SOTA 或严格排名；
- 所有核心维度均高于 4/5。

因此，**Section 2 可以冻结**。

## 12. Figure 3 并发状态声明

Figure 3 正由其他会话处理布局。本审计：

- 仅以 Section 2 局部正文、引用、定位和镜像为判定对象；
- 未把 Figure 3 的临时布局、浮动、页数或 overfull 状态计入问题；
- 未依赖 `main.tex` 的易变整文件状态作唯一依据，而是记录并复核了 Section 2 局部 SHA；
- 审计期间 `main.tex` 整文件因并发工作发生变化；发现后已重新读取最新版，Section 2 局部区块始终未变化；
- 未因 Figure 3 尚在处理而降低或阻塞 Section 2 判定。

## 13. 只读声明

本次未修改 `paper/main.tex`、`paper/main.pdf`、任何 MANUSCRIPT、`references.bib`、正文其他章节、Figure、Table、实验、证据、代码、模型或数据；未运行 LaTeX 编译。唯一新建文件为本审计报告。

**FINAL STATUS: SECTION2_FROZEN**
