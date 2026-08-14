# TerraState AAAI-27 仅正文复现信息充分性独立审计

审计日期：2026-07-29  
审计对象：投稿正文 `paper/main.tex`；`MANUSCRIPT_ZH_FULL.md` 仅用于中英文事实交叉核对  
审计性质：只读、仅主文、提交前复现信息充分性审计  
最终判定：**MAIN_TEXT_REPRODUCIBILITY_PASS**

## 1. 审计范围与输入冻结

### 1.1 判定标准

本报告判断的是：不依赖附录时，审稿人能否从投稿正文理解并基本复核 TerraState 的
数据任务、计算链、训练目标、模型选择以及 Q1--Q3 的统计对象和结论边界。它不要求
九页主文容纳逐位复现所需的全部配置、工程 provenance 或运行环境。

本轮没有审核或要求处理 supplementary、appendix、
`ReproducibilityChecklist.tex`、代码/权重发布、服务器环境、Figure、随机种子或
多次训练，也没有把内部路径、SHA、阶段名或旧 checkpoint 身份视为应进入主文的内容。

事实冲突按以下顺序裁决：

1. 作者在本任务中确认的 40 epochs、14,880 updates、global batch 64，以及
   Q1--Q3 使用同一完整训练后最终模型；
2. 当前 `paper/main.tex`；
3. 2026-07-28 最新章节终审和全文一致性审计；
4. 冻结 Q1--Q3 结果；
5. 较早审计与历史工程记录。

因此，旧文件中的 11,904、boundary80、Stage A/B、B0/B4 不用于否定当前正文，
也不得恢复进正文。

### 1.2 指定输入及 SHA-256

| 指定输入 | SHA-256 | 读取状态 |
|---|---|---|
| `paper/main.tex` | `1fe12204bad54b2b18a8debd5792cab9dff85a1e342cc35ca8df0e9a2d6eaab9` | 完整读取 |
| `MANUSCRIPT_ZH_FULL.md` | `0577238cd6d9561fb9ca7ea9fa4d8275da74a5b5f447e1d0407c4390d66099c6` | 完整读取 |
| `METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md` | `ff2c745489ccfda5019a84f001d65403426b2c84c82d4d4a4f1f10cbdd4d1365` | 完整读取；其中旧 checkpoint 结论已被当前作者事实覆盖 |
| `FULL_TEXT_GLOBAL_CONSISTENCY_AUDIT_20260728.md` | `e0a104bbf8108a4f3886bb7c4d6908f29e15de53f5f0af90b4c0e03de15ba8b2` | 完整读取 |
| `FULL_TEXT_GLOBAL_CONSISTENCY_RECHECK_20260728.md` | `f348393c8c9e677a7bb7972a8e28705e2f1387c843401105748438f5f6a58fd1` | 完整读取 |
| `SECTION4_4_1_FINAL_AUDIT_20260728.md` | `63a7e28680da8e70635259e1dc5072c4b254a428eff68d2a4bc8b20841a6b447` | 完整读取 |
| `METHOD_3_3_FINAL_AUDIT_20260728.md` | `384691d04a71c8328ced110f8604f357a3927b6f5557db7ae9931ee3f7a6df52` | 完整读取；旧 checkpoint 段不具当前权威性 |
| `METHOD_3_4_FINAL_AUDIT_20260728.md` | `b72c9bdb4dad64dc8554778313088410d06a1c751a7f3bb65c0b3a521f2faa97` | 完整读取 |
| 根目录 `FINAL_EVIDENCE_AUDIT_20260728.md` | — | **指定路径缺失** |
| `evidence_workspace/raw/release/EVIDENCE.md` | `5b8cfc54c7f76db9a74f802a2beb6058962864d18d61ffa4be97e5026b06da4b` | 完整读取；历史 release 身份仅作结果交叉核验 |
| `evidence_workspace/PUBLIC_BASELINES.md` | `eee41e90ea12ec9e939620863eace4aa888b99f47eb36bc162ed918d824b8fd0` | 完整读取 |
| `evidence_workspace/TABLE_NOTES.md` | `3c485f58e354dfe7bbec506464a62a2f5e85a29610861aef19da12eabc593f04` | 完整读取 |

精确指定的根目录报告不存在。项目中存在同名的
`evidence_workspace/FINAL_EVIDENCE_AUDIT_20260728.md`
（SHA-256
`ecc810445b46a969b7bc314809c0bc311045f6457c38d704f1a927ef29fcee1b`），本轮完整读取
它作为补充交叉核验，但没有把它伪装成指定路径输入。缺失的根目录文件不阻塞本次
审计，因为当前正文、最新终审和冻结 release 证据已足以完成所需判断。

## 2. 执行摘要

当前 `main.tex` 已达到 AAAI 主文合理的最小复现信息标准：

- 数据、任务、输入边界、10→20 步窗口、空间分辨率、预测目标和完整 OOD-t 范围均
  明确；
- \(q_\theta\to P_\rho\to T_\psi\to O_\omega\) 计算链、逐时距直接转移和
  \(b_h+r_h\) 输出闭环均可恢复；
- GT、KD、future-state 三类目标、冻结 target/teacher 身份、未来 EO 的训练期用途
  和推理期移除边界均明确；
- AdamW、40 epochs、14,880 updates、global batch 64、核心学习率、validation-only
  选模以及 Q1--Q3 同模型/无重训练身份均明确；
- Q1、Q2、Q3 的 split、统计单位、方向、CI 类型、样本数和最大允许结论均足以基本
  复核。

没有 `MAIN-TEXT REQUIRED` 缺失项。正文唯一轻微的自包含性歧义是：KD teacher 的
输入枚举写了 `observation history`，没有像 student 和 future-state target 段那样
显式点名 past weather。实现和上下文可恢复其含义，因此这是
`MAIN-TEXT OPTIONAL`，不是冻结阻塞。

精确的 \(\lambda_s\) schedule、partial-unfreezing schedule、\(\epsilon\) 数值、
天气变量清单、预处理、donor 匹配算法和 bootstrap 实现细节均对逐位复现有用，但
适合 supplementary/configuration，不应机械扩写主文。

## 3. 数据与任务复现表

| 信息 | 当前正文位置/表达 | 可恢复性 | 分类 | 判定 |
|---|---|---|---|---|
| GreenEarthNet 的任务角色 | 4.1 称其为 Q1--Q3 的 common evaluation setting，并引用原论文 | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| Temporal OOD-t 的角色 | 4.1 定义 temporal out-of-distribution split；4.2 用于 forecasting prerequisite | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| Validation 与 OOD-t 用途 | validation-only forecasting selection；OOD-t 和 Q2--Q3 不参与选模；Q2 同时报 Val/OOD-t | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| 30 个五日 composites | 4.1 明写 30 five-day Sentinel-2 composites | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| 10-step history / 20-step forecast | 前 10 个为历史、后 20 个为预测窗口 | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| 空间大小与地面采样 | \(128\times128\)，20 m | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| Historical EO | 3.1--3.2 的 cloud-masked EO history | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| Past weather | 3.1 定义 \(u_{\le t}^{\rm past}\)，3.2 明写进入 \(q_\theta\) | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| Future weather | 定义 \(u_{t+1:t+H}\)，且只经 \(T_\psi\) | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| Cloud/quality masks | 方法定义 history validity mask；4.1 明写 cloud and quality masks | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| Static geography | \(g\) 在 history context 和 transition condition 中均被定义 | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| NDVI 目标 | 4.1 明写 target is NDVI | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| Valid vegetation pixels | 4.1 明写 NDVI over valid vegetation pixels；Eq. (5) 定义 vegetation/clear masks | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| OOD-t 样本数 | 1,904 minicubes | 明确 | 已满足 MAIN-TEXT REQUIRED | PASS |
| 精确天气变量/归一化/缺失值处理 | 主文未展开 | 不影响任务与结论理解 | SUPPLEMENT-APPROPRIATE | 非阻塞 |
| 数据裁切、质量阈值和 evaluator 逐项规则 | 通过 benchmark 引用和 mask 定义可理解，未逐项枚举 | 基本复核足够；逐位复现不足 | SUPPLEMENT-APPROPRIATE | 非阻塞 |

结论：数据和任务层面没有正文必需缺口。标准 GreenEarthNet 指标的精确聚合实现可由
基准引用和 supplementary 承担，不需要把 evaluator 代码翻译进主文。

## 4. 模型计算链复现表

| 组件/边界 | 当前正文是否说明 | 基本可恢复内容 | 判定 |
|---|---:|---|---|
| \(q_\theta\) history encoder | 是 | 输入 cloud-masked EO、past weather、geography；输出 \(b_{1:H}\) 与 \(e_t\) | PASS |
| \(P_\rho\) projector | 是 | 将 final historical tokens 投影为 \(z_t\in\mathbb R^{N\times d}\) | PASS |
| Spatial predictive state \(z_t\) | 是 | patch-organized、history-derived、on-path state | PASS |
| Shared \(T_\psi\) | 是 | GRU weather-prefix encoder + patch geography + horizon fusion + residual update | PASS |
| Direct-per-horizon transition | 是 | 每个 \(h\) 从同一 \(z_t\) 直接推进一次，明确非 recursive rollout | PASS |
| \(O_\omega\) readout | 是 | token→\(4\times4\) patch→raster contribution \(r_h\) | PASS |
| Context-only forecast \(b_h\) | 是 | 与 predictive state 来自同一 history pass，但为独立输出 | PASS |
| State-mediated raster \(r_h\) | 是 | 由 transitioned state 读出并进入最终加法 | PASS |
| 最终预测 | 是 | \(\widehat y_{t+h}=b_h+\alpha r_h,\alpha\equiv1\) | PASS |
| Future-weather 独占入口 | 是 | \(q_\theta\) 不读 future weather；future weather only through \(T_\psi\) | PASS |
| Training-only teacher/target 边界 | 是 | 两条参考分支冻结，训练后丢弃，正式推理只保留 student | PASS |
| 类名、state-dict key、缓存和文件路径 | 未写 | 不属于论文级方法定义 | UNNECESSARY / INTERNAL |

结论：读者无需查看代码即可重建正式推理图和训练期参考分支与正式模型的边界。

## 5. 训练、优化与模型选择复现表

| 项目 | 当前正文 | 充分性判断 | 分类/状态 |
|---|---|---|---|
| Observable GT objective | Eq. (5) 给出 clear-horizon 归一化与 vegetation/prediction-valid 聚合 | 充分 | 已满足 MAIN-TEXT REQUIRED |
| KD teacher 身份与用途 | independent frozen full-weather teacher；无 future EO；产生 stopped target | 基本充分 | 已满足核心要求 |
| KD teacher 的 past weather | 输入枚举未显式点名，`observation history` 可被宽读为包含它 | 可恢复但有轻微歧义 | MAIN-TEXT OPTIONAL |
| Future-state target 身份 | training-start frozen \(q_{\theta^0},P_{\rho^0}\) copy | 充分 | 已满足 MAIN-TEXT REQUIRED |
| Future EO 的用途 | 仅构造 stopped training-only target；不进入 student forecast/inference | 充分 | 已满足 MAIN-TEXT REQUIRED |
| GT/KD/FS 三类目标 | Eq. (5)--(7) 分别定义并汇总 | 充分 | 已满足 MAIN-TEXT REQUIRED |
| GT/KD/FS 权重逻辑 | GT 1、KD 0.5、FS \(\lambda_s\) | 方法逻辑充分 | 已满足 MAIN-TEXT REQUIRED |
| \(\lambda_s\) 精确 schedule | 主文未给 | 逐位复现有用，不影响方法理解 | SUPPLEMENT-APPROPRIATE |
| Partial unfreezing 与 \(q\) group LR | 主文只说 schedule-enabled student parameters；未展开 | 逐位复现有用 | SUPPLEMENT-APPROPRIATE |
| \(\epsilon\) 数值 | 公式有 \(\epsilon_{\rm pix/GT/KD/FS}\)，无数值 | 显然为数值稳定项；数值宜进配置/补充 | SUPPLEMENT-APPROPRIATE |
| Optimizer | AdamW | 充分 | 已满足 MAIN-TEXT REQUIRED |
| Epochs / updates | 40 / 14,880 | 充分且符合当前作者事实 | 已满足 MAIN-TEXT REQUIRED |
| Global batch | 64 | 充分 | 已满足 MAIN-TEXT REQUIRED |
| Core LR | non-\(q\) branch \(3\times10^{-5}\) | 主文合理最小值 | 已满足 MAIN-TEXT REQUIRED |
| Model selection | solely by validation forecasting performance | 充分 | 已满足 MAIN-TEXT REQUIRED |
| Q2/Q3 是否用于选模 | OOD-t 与 Q2--Q3 interventions held out from selection | 充分 | 已满足 MAIN-TEXT REQUIRED |
| Q2/Q3 是否重训练 | 同一 frozen final model，只改 forward computation | 充分 | 已满足 MAIN-TEXT REQUIRED |
| AdamW betas、weight decay、scheduler、augmentation | 未展开 | 执行级配置 | SUPPLEMENT-APPROPRIATE |

主文没有必要叙述候选 checkpoint 搜索、内部 gate 或阶段历史。当前
`exact full-model warm start`、三种训练身份和目标公式属于科学方法信息，不构成
过度工程化。

## 6. Q1/Q2/Q3 评测复现表

### 6.1 Q1：预测前提

| 核对项 | 当前正文 | 判定 |
|---|---|---|
| 使用完整 OOD-t | 4.1 给出完整 split 的 1,904 minicubes；4.2 明写 across 1,904 | PASS |
| 指标 | \(R^2\)、RMSE、NSE、absolute bias、\(\mathrm{RMSE}_{25}\) | PASS |
| \(\mathrm{RMSE}_{25}\) 含义 | first 25 forecast days | PASS |
| 统计对象 | valid vegetation pixels 上 NDVI；完整 OOD-t dataset-level forecasting profile | PASS |
| Q1 的证据职责 | forecasting prerequisite / performance context | PASS |
| Table 1 是否证明内部状态 | 正文明示 Q2/Q3 而非 table rank 决定 state/weather evidence | PASS |
| 标准指标精确公式与 benchmark scorer 权重 | 未在主文逐式展开，但有 GreenEarthNet 引用 | SUPPLEMENT-APPROPRIATE |

Q1 足以基本复核；没有要求或暗示 seed、\(\pm\)、Published/Local、SOTA 或严格排名。

### 6.2 Q2：状态贡献

| 核对项 | 当前正文 | 判定 |
|---|---|---|
| Primary intervention | state removal | PASS |
| \(\alpha=0\) 含义 | 在加法前令 \(\alpha=0\)，得到 \(\widehat y^{remove}=b_h\) | PASS |
| \(T\to I\) 地位 | supporting diagnostic only；说明 readout OOD caveat | PASS |
| 同一冻结模型 | 明确 | PASS |
| 无重训练 | 明确 | PASS |
| Official dataset-level \(\Delta R^2\) | 单独定义为 full minus intervened dataset-level scores | PASS |
| Paired mean \(\Delta R^2\) | 单独定义为 per-minicube mean | PASS |
| CI | paired-bootstrap 95% CI，只与 paired estimand 搭配 | PASS |
| Validation/OOD-t 单位 | Table 2 给出 \(n=589/1,019\) paired minicubes | PASS |
| 最大允许结论 | explicit state path carries a measurable forecast increment；不代表所有信息都经过 state | PASS |
| Bootstrap 重复次数、有效 cube 过滤和随机实现 | 未展开 | SUPPLEMENT-APPROPRIATE |

正文不会把 official \(\Delta R^2\) 与 paired CI 混用，也不会把 \(T\to I\) 升级为
transition necessity。

### 6.3 Q3：天气响应和完整窗口保真度

| 核对项 | 当前正文 | 判定 |
|---|---|---|
| Actual weather | 标准路径，明确定义 | PASS |
| Matched donor | season-, geography-, quality-matched | PASS |
| Normalized mean | frozen global z-score space 中的零 | PASS |
| 唯一改变量 | only future weather entering \(T_\psi\) | PASS |
| 固定量 | history、\(b_h\)、\(z_t\)、geography、horizon、readout、sample、mask、ground truth | PASS |
| 主指标 | complete 20-step forecast-window masked MSE | PASS |
| 差值方向 | \(\Delta L=L_{\rm control}-L_{\rm actual}\) | PASS |
| 正值含义 | actual weather error 更低、fidelity 更高 | PASS |
| 样本数 | 84 frozen matched pairs | PASS |
| 主 CI | geographic-cluster 95% CI | PASS |
| 描述性计数 | 56/84、69/84 明示 descriptive | PASS |
| Subset \(R^2=0.6254\) | Table 3 caption 明示只适用于 matched subset | PASS |
| Detectable response | 结果段报告 common-mask per-minicube masked mean absolute forecast difference | PASS |
| 非因果/非反事实/非极端增强 | Method 与 Limitations 明确排除；hot-dry null 明确披露 | PASS |
| 精确 donor 候选池、距离、阈值、cluster 构造和 bootstrap 次数 | 主文未展开 | SUPPLEMENT-APPROPRIATE |

Q3 的干预方向、统计单位和证据边界足以由主文独立恢复。

## 7. 四级分类

以下分类只针对“当前正文可能未展开的信息”，不把已经充分写明的项目重复计为缺失。

| 级别 | 项目 | 裁决 |
|---|---|---|
| **MAIN-TEXT REQUIRED** | 无 | 当前没有会阻止方法、实验或核心结论理解/基本复核的主文缺失 |
| **MAIN-TEXT OPTIONAL** | KD teacher 输入枚举显式加入 `past weather` | 可消除一处轻微歧义；不影响现有可信度 |
| **MAIN-TEXT OPTIONAL** | Eq. (8) 后明说粗体预测/真值表示完整 20 步窗口 | 上下文已可恢复；只改善局部符号自包含性 |
| **SUPPLEMENT-APPROPRIATE** | \(\lambda_s\) 数值调度与 partial-unfreezing schedule | 对完整训练复现有用，不应挤占方法主线 |
| **SUPPLEMENT-APPROPRIATE** | \(\epsilon\) 精确值、AdamW 次级超参数、完整 LR/scheduler | 配置级信息 |
| **SUPPLEMENT-APPROPRIATE** | 天气变量清单、归一化、数据预处理和质量阈值 | 数据管线级信息 |
| **SUPPLEMENT-APPROPRIATE** | Q2 有效 paired-cube 规则、bootstrap 重复次数 | 统计实现级信息 |
| **SUPPLEMENT-APPROPRIATE** | Q3 donor 候选池、匹配距离/阈值、地理 cluster 定义、bootstrap 实现 | 协议完整复现信息 |
| **SUPPLEMENT-APPROPRIATE** | 完整 benchmark scorer 配置和标准 metric 聚合细节 | 可由基准引用理解，逐位复现宜放补充 |
| **UNNECESSARY / INTERNAL** | checkpoint SHA、commit SHA、manifest SHA、JSON 字段路径 | 证据台账信息，不是主文方法信息 |
| **UNNECESSARY / INTERNAL** | 服务器/conda/GPU/cache/绝对路径、state-dict key | 工程运行信息 |
| **UNNECESSARY / INTERNAL** | 11,904、boundary80、Stage A/B、B0/B4、MAIN-last、exclusive | 被当前权威事实覆盖的历史工程身份 |
| **UNNECESSARY / INTERNAL** | 内部 gate、qualifier、pilot/smoke、候选选择故事 | 会把科学叙事退化为研发日志 |
| **UNNECESSARY / INTERNAL** | single-run/seed/\(\pm\)、Published/Local、公开/本地身份标签 | 本任务明确排除，不构成当前主文缺口 |
| **UNNECESSARY / INTERNAL** | Q4/composition/non-collapse、SOTA/严格排名扩展 | 不属于冻结主张 |

## 8. 当前正文已经充分交代的信息

1. 数据任务和预测窗口：GreenEarthNet、30×五日、10→20、128×128、20 m、
   OOD-t 1,904。
2. 模态及未来信息边界：历史 EO、过去天气、静态地理进入 history encoder；未来
   weather 只进入 transition；future EO 只作为停止梯度的训练目标。
3. 正式计算链：history encoder、projector、spatial state、direct shared
   transition、raster readout、context-only prediction 和显式加法。
4. 三类训练目标的数学逻辑、mask/aggregation 差异、冻结 reference branch 与推理期
   去除。
5. AdamW、40 epochs、14,880 updates、global batch 64、核心学习率和
   validation-only selection。
6. Q1--Q3 使用同一个完成完整训练的最终模型；Q2/Q3 不重训练。
7. Q1 完整 OOD-t 的指标与 forecasting-prerequisite 职责。
8. Q2 official 与 paired estimand 分离、paired-bootstrap CI、split-specific \(n\)、
   primary/supporting 层级和 load-bearing 边界。
9. Q3 三种天气、固定量、84 pairs、完整窗口 loss、差值符号、cluster CI、描述性计数
   和 subset score 作用域。
10. 非因果、非反事实、非完整物理状态、非极端增强、非 Q4/SOTA 的结论边界。

## 9. 真正缺失的信息

### 9.1 主文必需缺失

**NONE。**

当前没有 Critical 或 Major 复现缺口，也没有任何信息缺失会使 Q1--Q3 无法理解或
无法基本复核。

### 9.2 轻微主文自包含性问题

**一项 Minor：** `main.tex` §3.3 “Training Identities and Purpose” 将 KD teacher
输入写为 `observation history, static geography, and the complete future-weather
sequence`，没有显式点名它也读取 past weather。结合 §3.1 的 context 定义、
`full-weather teacher` 身份和完整中文镜像，读者可以合理恢复；但如果作者进行最后
一轮术语校对，增加 `past weather` 两词会更精确。

这不是冻结阻塞，也不要求打开训练叙事或加入工程信息。

### 9.3 完整复现而非主文理解所缺的信息

精确 schedule、unfreezing、\(\epsilon\)、预处理、匹配算法和 bootstrap 实现未在
主文展开。它们属于 supplementary/configuration 层级；本轮明确不处理附录，因此
不应转化为主文失败。

## 10. 明确不应加入正文的信息

以下内容即使存在于内部证据记录，也不应因“可复现”被搬进投稿主文：

- checkpoint/commit/manifest SHA、JSON path、服务器路径和 cache 结构；
- conda 命令、GPU 型号、内部 state-dict key 或类名；
- 11,904、boundary80、Stage A/B、B0/B4、exclusive、MAIN-last；
- 内部 gate、开发候选、pilot/smoke 和 checkpoint 选择故事；
- single-seed、single-run、\(\pm\)、Published/Local 或公开/本地来源标签；
- Q4/composition/non-collapse、SOTA、严格排名或额外 benchmark 叙事；
- 为证明可复现而重复 Section 3 已经清楚定义的整个计算图。

## 11. 十个特别问题逐项回答

### 1. 当前 `main.tex` 是否足以支撑 Q1--Q3 的基本复核？

**是。** Q1 的完整 split、指标和职责，Q2 的 intervention/estimand/CI/unit，以及
Q3 的 arms/fixed quantities/loss direction/cluster CI 均明确。

### 2. 是否存在真正阻塞正文冻结的复现缺口？

**否。** `MAIN-TEXT REQUIRED` 缺失为 0；Critical=0，Major=0。

### 3. \(\lambda_s\) schedule、partial unfreezing、\(\epsilon\) 数值是否必须进入主文？

**不必须。** 它们对逐位训练复现有用，但不影响方法身份、损失逻辑或 Q1--Q3 解释，
应归入 `SUPPLEMENT-APPROPRIATE`。主文保留 \(\lambda_s\) 和 \(\epsilon\) 符号已经
足以说明目标结构。

### 4. KD teacher 是否需要在正文明确点名 past weather？

**不是冻结所必需，但建议作为可选的一处短语级澄清。** 当前上下文可以恢复 teacher
的 full-weather 身份；显式加入 `past weather` 会使输入枚举更自包含。

### 5. 数据 preprocessing、donor matching 细节是否可以留给补充材料？

**可以。** 主文已经给出任务、mask、matching axes、normalized-mean 定义、唯一改变量
和统计单位。精确阈值、候选池、距离和预处理步骤适合 supplement。

### 6. 正文是否清楚表明 Q1--Q3 使用同一完整训练后的最终模型？

**是。** 4.1 明写 `same final TerraState model after the complete 40-epoch,
14,880-update training protocol`，并再次说明 final model completes the full
training protocol。

### 7. 是否有旧 11,904/boundary80 叙事渗入当前正文？

**没有。** 当前 `main.tex` 对 11,904、boundary80、Stage A/B、B0/B4 均为零命中。
这些只存在于较早审计/release 记录，已按本任务事实优先级排除。

### 8. 是否存在为了“可复现”而写得过于工程化的段落？

**没有。** §3.3 的三种训练身份和 Eq. (5)--(7) 是理解训练机制所需的科学信息；
4.1 的实现段只保留参数量、optimizer、训练长度、batch、核心 LR 和选模规则，没有
退化为日志、路径或 checkpoint 叙事。

### 9. 在不处理附录的前提下，正文能否独立成立？

**能。** 主文足以理解、审查和基本复核核心实验；它不是独立的 bitwise reproduction
package，但 AAAI 主文也不应承担这一功能。

### 10. 如果需要修改，最小修改是否可以控制在 1--3 句？

**没有必需修改。** 若作者选择关闭唯一 Minor，只需在 §3.3 KD teacher 输入列表中
增加 `past weather`，属于一个短语而非新增段落；Eq. (8) 的窗口符号说明同样最多一
个短句且为 Optional。

## 12. 问题计数

| 等级 | 数量 | 说明 |
|---|---:|---|
| Critical | **0** | 无事实、方法、统计或核心复核阻断 |
| Major | **0** | 无主文必需信息缺失 |
| Minor | **1** | KD teacher 输入枚举未显式点名 past weather |
| Optional | **2** | teacher past-weather 短语澄清；Eq. (8) 粗体窗口符号自包含性 |

补充材料适合项按六个信息族归档，不计入正文严重度：训练 schedule、数值稳定/优化
配置、数据预处理、Q1 scorer 细节、Q2 bootstrap/eligibility、Q3 matching/cluster
实现。

## 13. 最小、限定位置的建议

### 必须修改

**NONE。**

### 可选且不影响冻结

1. **位置：** §3.3 `Training Identities and Purpose` 的 KD teacher 输入句。  
   **方向：** 在 `observation history` 后明确 past weather，保持 no-future-EO 和
   complete-future-weather 边界不变。  
   **规模：** 一个短语。
2. **位置：** Equation (8) 后第一次出现
   \(\widehat{\mathbf y},\mathbf y\)。  
   **方向：** 如最终符号校对需要，可用一个短句说明粗体对象是完整 20 步预测/真值
   窗口。  
   **规模：** 一个短句。

不得借这两项可选澄清加入 schedule、checkpoint、内部身份、seed、Q4 或排名叙事。

## 14. 主线保护结论

当前复现信息服务并强化唯一主线：

> TerraState 是天气驱动的遥感预测状态世界模型；其显式状态贡献和未来天气路径可在
> 同一个冻结模型上通过状态移除与天气替换接受经验检验和否证。

主文已经在“足够审查”与“不过度工程化”之间取得合理平衡。进一步的执行级配置应放在
补充材料或发布配置中，而不是抢夺 Q1--Q3 的科学证据链。

## 15. 只读声明与最终判定

本轮没有修改或重新编译任何既有文件，没有运行训练、评测或公开方法复现，也没有
读取/修改附录和 checklist。唯一新建文件为本报告。

# MAIN_TEXT_REPRODUCIBILITY_PASS
