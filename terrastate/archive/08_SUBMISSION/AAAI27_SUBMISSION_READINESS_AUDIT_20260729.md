# TerraState AAAI-27 提交门户与投稿包就绪情况独立审计

**审计性质：** 只读投稿就绪审计  
**审计时间：** 2026-07-29 00:27:52 UTC  
**项目目录：** `/mnt/data/users/luzheng/workspace/iclr/czj/TerraState_AAAI27/`  
**当前结论：** `SUBMISSION_READINESS_BLOCKED`

> 阻塞原因不是论文主张或匿名性，而是 AAAI-27 强制要求的 Reproducibility Checklist 尚未填写和导出。当前 `paper/ReproducibilityChecklist.tex` 仍含 34 个 `Type your response here` 占位符，项目中未发现已填写的独立 checklist PDF。与此同时，`paper/main.tex` 和 `paper/main.pdf` 在本次审计期间仍被其他流程更新，因此不得把本报告中检查的 PDF 快照当作最终投稿文件。

## 1. 官方资料、版本与查阅时间

本报告只使用 AAAI 与 OpenReview 官方来源。

| 资料 | 官方 URL | 页面/文件日期 | 本次查阅 |
|---|---|---|---|
| AAAI-27 会议页与作者时间表 | https://aaai.org/conference/aaai/aaai-27/ | 页面日期 2026-03-04 | 2026-07-29 00:25–00:28 UTC |
| Main Technical Track CFP | https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/ | 页面日期 2026-05-14 | 同上 |
| Submission Instructions | https://aaai.org/conference/aaai/aaai-27/submission-instructions/ | 页面日期 2026-06-30 | 同上 |
| Paper Modification Guidelines | https://aaai.org/conference/aaai/aaai-27/paper-modification-guidelines/ | 页面日期 2026-06-30 | 同上 |
| Supplementary Material | https://aaai.org/conference/aaai/aaai-27/supplementary-material/ | 页面日期 2026-06-30 | 同上 |
| OpenReview AAAI-27 公开会场页 | https://openreview.net/group?id=AAAI.org%2F2027%2FConference | 当前公开页面 | 同上 |
| AAAI-27 Author Kit 入口 | https://aaai.org/authorkit27/ | 当前重定向 | 同上 |
| Author Kit 直接下载 | https://aaai.org/wp-content/uploads/2026/05/AuthorKit27.zip | HTTP Last-Modified: 2026-05-28 15:54:36 UTC | 同上 |

Author Kit 核验：

- ZIP 版本：`TemplateVersion (2027.1)`
- ZIP 大小：5,495,535 bytes
- ZIP SHA-256：`e28c6ac9bc6eb3b4e2d849547d2cefb5162610ee39d0a12e0dc62d1126b44a7d`
- 官方 `aaai2027.sty` SHA-256：`391bce82815bf698b8e382dd3ae7e30c75d7ab46df140cb295b1266016bc8623`
- 官方 `aaai2027.bst` SHA-256：`5db7765ba99de5c1e4686f9b3940a0add9c5e702f2164514462bec130ccb6e3c`
- 本地 `paper/aaai2027.sty` 与 `paper/aaai2027.bst` 分别与以上官方 SHA 完全一致。

## 2. 官方时间与 UTC 换算

AAAI 官方页面明确说明所有 deadline 均为 Anywhere on Earth，即 UTC−12。

| 事项 | 官方时间（UTC−12） | 等价 UTC | 状态 |
|---|---|---|---|
| Abstract deadline | 2026-07-21 23:59 UTC−12 | 2026-07-22 11:59 UTC | 已过 |
| Full-paper deadline | 2026-07-28 23:59 UTC−12 | 2026-07-29 11:59 UTC | 审计时尚余约 11 小时 31 分 |
| Supplementary material and code deadline | 2026-07-31 23:59 UTC−12 | 2026-08-01 11:59 UTC | 尚未到期 |

OpenReview 公开会场页显示 `Submission Deadline: Jul 29 2026 11:59AM UTC-0`，与 AAAI 的 2026-07-28 23:59 UTC−12 完全一致。

官方修改窗口：

- 在 full-paper deadline 之前，可以替换 submitted paper，并可对 title、TL;DR、abstract 做非实质性修改。
- full-paper deadline 之后至 supplementary deadline，只允许修改 supplementary materials。
- supplementary deadline 之后至录用通知前，任何内容均不能修改。
- AAAI 明确表示投稿系统将在截止时间关闭，且不提供个别例外。

## 3. 官方上传要求

| 项目 | 官方要求 | 本地/门户状态 | 判定 |
|---|---|---|---|
| 主论文格式 | trouble-free、high-resolution、US Letter、AAAI 双栏 PDF，Type 1 或 TrueType 字体 | 当前 PDF 是 8 页 US Letter 候选快照，但仍非最终冻结版 | `WAIT_FINAL_PDF` |
| 主论文上传文件 | 审稿提交阶段只要求 PDF；源码仅在录用后需要 | 不应上传当前 TeX 源码包 | PASS |
| 页数 | 最多 9 页；非参考文献内容最多 7 页；第 8–9 页只能是 references | 当前候选快照为 8 页，但最终状态必须重新检查 | `WAIT_FINAL_PDF` |
| Reproducibility Checklist | 必须在 full-paper submission 时完成，并在投稿表单的指定独立字段上传 | 唯一本地 checklist 含 34 个未填写占位符；无完成版 PDF | **FAIL / CRITICAL** |
| Supplementary Document | 可选 PDF，独立于 main paper；主论文必须自洽 | 由作者决定是否上传 | `USER_ACTION_REQUIRED` |
| Supplementary Media | 可选 ZIP | 由作者决定 | `USER_ACTION_REQUIRED` |
| Supplementary Code/Data | 可选 ZIP；若用于支撑可复现性，应在提交时提供 | 由作者决定 | `USER_ACTION_REQUIRED` |
| Supplementary 匿名性 | 所有 supplementary 都必须满足双盲；主文不得放网页补充材料链接，包括 anonymous repository 链接 | 最终包需人工核对 | `USER_ACTION_REQUIRED` |
| 最大文件大小 | AAAI 官方网页和无需登录的 OpenReview 公开会场页未公开具体数值；私有投稿表单字段无法自动读取 | 不得猜测 | `UNKNOWN / USER_ACTION_REQUIRED` |
| 主 PDF 可更新到何时 | 只到 full-paper deadline | 截止后不能以 supplementary deadline 为由继续换主 PDF | PASS |

### 初次 full-paper submission 真正需要的文件

1. 最终匿名主论文 PDF：`paper/main.pdf` 的冻结副本。
2. 填写完成并导出的 Reproducibility Checklist PDF，通过 OpenReview 的独立指定字段上传。

不需要在本次审稿提交时上传 LaTeX 源码。Supplementary Document、Media、Code/Data 属于独立且可选的后续上传项，截止时间为 2026-08-01 11:59 UTC。

## 4. 标题与摘要一致性

### 4.1 当前权威正文

当前 `paper/main.tex` 标题为：

> TerraState: A Testable Predictive-State World Model for Weather-Driven Land-Surface Forecasting

当前摘要统一使用：

- 方法名 `TerraState`；
- `testable predictive-state world model` 身份；
- Q1：保留有用 temporal-shift forecasting skill；
- Q2：state-contribution removal 导致性能下降；
- Q3：actual weather 相对 matched-donor 与 normalized-mean controls 在完整 20-step forecast window 上具有更低 masked loss；
- 不含 Q4/composition 已通过的主张；
- 不再使用 endpoint-only Q3 口径。

`MANUSCRIPT.md` 的英文标题与摘要和当前 `main.tex` 一致；`MANUSCRIPT_ZH.md` 与 `MANUSCRIPT_ZH_FULL.md` 的中文标题及摘要在方法身份、Q1–Q3 和完整 20 步窗口口径上语义一致。

### 4.2 与已提交摘要记录的差异

`ABSTRACT_REVISION_FROM_AAAI_SUBMISSION_ZH.md` 未记录已注册英文标题，因此无法据此自动确认 OpenReview 标题。该文件顶部保存的是一个较早的“基于 AAAI 原提交版本的修订摘要”，而不是当前 portal 的可见快照。

当前 `main.tex` 相对该文件顶部英文摘要有三类可见变化：

1. 将“selected almost entirely”校准为“typically evaluated primarily”，降低对现有工作的过度概括；
2. 将 “augments a forecasting backbone” 调整为以空间预测状态为中心的方法定义；
3. 将 Q3 的 “endpoint predictions” 修正为完整 20-step forecast-window masked loss。

该记录的逐句变更表还显示：更早的 AAAI 原提交摘要曾包含 direct-versus-composed/Q4、旧天气对照和 matched-backbone 表述；当前摘要已删除这些未冻结主张并改为最终 Q1–Q3 证据。

**风险判断：** 核心题目、TerraState 身份和预测状态主线保持一致，但诊断接口与 Q3 estimand 已发生实质性事实校准。AAAI 官方明确警告 title/abstract 在 abstract deadline 后不应发生实质性改变。由于本审计无法查看私人 OpenReview 字段，必须由作者在 full-paper deadline 前亲自比较 portal 中的实际摘要，并确保其与当前冻结摘要一致；不得在截止后再尝试更新。

| 核对项 | 自动结果 | 门户动作 |
|---|---|---|
| TerraState 方法名 | 一致 | 在 portal 再确认 |
| predictive-state world model 身份 | 一致 | 在 portal 再确认 |
| Q1–Q3 当前证据口径 | 当前正文与 Markdown 一致 | 将 portal 摘要同步到当前冻结版本 |
| Q4/composition | 当前摘要无此主张 | 确认 portal 未保留旧原提交措辞 |
| endpoint-only Q3 | 当前摘要已修正为 20-step window | 确认 portal 同步修正 |
| 注册标题 | 本地记录不足 | `USER_ACTION_REQUIRED` |

## 5. 匿名检查

### 5.1 当前 PDF 快照

审计快照：

- `paper/main.tex` SHA-256：`5b0f7e586e1da0ec9f1309245464e6f697da5e992cf8879e44c4f230655f9ff7`
- `paper/main.pdf` SHA-256：`ea8725b6dc433b1e2bb9afc81c4dd81eff447697ddc6bb6957582a5d9bb144f0`

注意：这些文件在审计期间仍被并行流程更新，以上哈希只是瞬时快照，不是最终投稿哈希。

当前 PDF 快照的只读检查结果：

- 首页显示 `Anonymous submission`；
- 源码使用 `\author{Anonymous Submission}` 和空 `\affiliations{}`；
- PDF metadata 的 Author、Title、Subject、Keywords 均为空；
- PDF 文本未检出作者姓名、单位、邮箱、致谢、GitHub/GitLab、本地服务器路径或 `/mnt`、`/home`、`/root`；
- PDF 未检出外部超链接；
- 未发现身份式自引措辞；
- 当前 PDF 可正常解析与复制文本。

**当前匿名快照：PASS。**

仍需注意：

- 无法在不知道真实作者列表的情况下自动判断参考文献中是否存在需要采用匿名措辞的作者自引；作者需人工确认。
- `paper/main.log`、`paper/main.fls` 和多份 `compile_*.log` 含构建环境信息或路径，不能上传。
- 最终 PDF 每次重新编译后都必须重新做 metadata 与文本泄漏检查。

## 6. 当前已满足的项目

- 官方 Author Kit 已核实，版本为 2027.1。
- 本地 `aaai2027.sty` 与 `aaai2027.bst` 和当前官方文件 SHA 一致。
- 当前标题、方法名和英文/中文镜像中的 TerraState 身份一致。
- 当前摘要已经统一到 Q1–Q3，未把 Q4/composition 写成成立结果。
- 当前摘要使用完整 20-step forecast-window Q3 口径，不再使用 endpoint-only 结果。
- 当前 PDF 快照匿名信息检查通过。
- 当前 PDF 快照可正常解析，页面为 US Letter。
- 既有引用审计未发现缺失 BibTeX key；当前正文还已加入先前建议的两处引用，但最终 PDF/BibTeX 回归仍待完成。

## 7. `WAIT_FINAL_PDF`

以下项目不得根据本次审计中的动态 PDF 快照宣布完成：

| 项目 | 状态 | 最终检查要求 |
|---|---|---|
| 第 8 页是否 references-only | `WAIT_FINAL_PDF` | 冻结后逐页检查 |
| Figure 3 最终页码与浮动位置 | `WAIT_FINAL_PDF` | 冻结后记录 |
| Identity-H / 字体技术问题 | `WAIT_FINAL_PDF` | 冻结后检查字体嵌入及 Type 3 |
| Table 1 / Table 2 最终浮动位置 | `WAIT_FINAL_PDF` | 冻结后检查阅读顺序 |
| BibTeX 与 citation 最终修改 | `WAIT_FINAL_PDF` | 最终编译后核对 `.log`、`.bbl` 和 PDF |
| 最终 PDF SHA-256 | `WAIT_FINAL_PDF` | 上传前立即计算 |
| 最终上传文件大小 | `WAIT_FINAL_PDF` | 上传前记录，并在私有表单验证大小限制 |
| 最终 PDF 能否从 OpenReview 下载并打开 | `WAIT_FINAL_PDF` | 上传后由作者下载回验 |

当前候选 PDF 恰为 8 页且第 8 页文本标题为 References，但由于源文件仍在并行更新，本报告不把该观察升级为最终 PASS。

## 8. OpenReview 人工核对清单

本审计无法访问用户的私人 OpenReview 投稿页面。以下每项均为 `USER_ACTION_REQUIRED`：

- [ ] 投稿记录状态不是 draft，并且 full paper 已正式提交。
- [ ] portal title 与当前标题逐字一致。
- [ ] portal abstract 与当前 `main.tex` 冻结摘要一致。
- [ ] portal 未残留 Q4/composition、endpoint-only 或旧天气对照表述。
- [ ] author list 完整，姓名和顺序正确；注意 full-paper deadline 后不能新增作者。
- [ ] 所有作者 OpenReview profile 已完成并使用正确邮箱。
- [ ] author registration 已完成。
- [ ] nominated reciprocal reviewer / reviewer registration 已按会场要求完成。
- [ ] conflicts 已完整申报。
- [ ] primary/secondary subject areas 与 Main Technical Track 选择正确。
- [ ] keywords 合理且与 TerraState、EO forecasting、world models/predictive states 相符。
- [ ] 已上传最终匿名主 PDF，OpenReview 预览和下载均可正常打开。
- [ ] 已上传**填写完成**的 Reproducibility Checklist PDF 到指定独立字段。
- [ ] 最终主 PDF 的上传时间早于 2026-07-29 11:59 UTC。
- [ ] supplementary document / media / code-data 是否计划上传已经决定；若上传，按类型分别提交并保持匿名。
- [ ] 所有 ethics、declaration、terms、simultaneous-submission 与 author-attendance/reviewer-pool 声明均已阅读并勾选。
- [ ] portal 显示的最终文件大小未触发隐藏限制；官方公开页面未给出具体上限。
- [ ] 上传后使用 OpenReview 的 “Email” 功能向作者发送确认，或至少保存页面截图与下载回验结果。

## 9. 投稿包洁净度

### 应上传

- Full-paper deadline 前：最终匿名 `main.pdf`。
- Full-paper deadline 前：填写完成并独立导出的 Reproducibility Checklist PDF。
- Supplementary deadline 前（可选且独立）：Supplementary Document PDF、Media ZIP、Code/Data ZIP。

### 不应上传

- `paper/main.log`
- `paper/main.fls`
- `paper/main.aux`
- `paper/main.out`
- `paper/main.bbl`
- `paper/main.blg`
- `paper/main.fdb_latexmk`
- `paper/*.synctex.gz`
- `paper/compile_*.log`
- 页面预览 PNG、内部 Figure 工作区文件、PPTX 和绘图脚本
- `main.tex`、`references.bib` 或整个源码目录（审稿阶段官方不要求）
- evidence ledger、JSON、checkpoint、审计 Markdown、状态文件
- 未填写的 `paper/ReproducibilityChecklist.tex`
- `paper/supplementary_q4_table.tex`：Q4 已退出当前主线，且该文件不是正式 supplementary package

构建日志中的用户路径不等于 PDF 泄漏；风险来自误把这些构建产物一起上传。

## 10. 风险分级

### Critical

1. **必需的 Reproducibility Checklist 未完成。** 34 个回答仍是占位符，且没有完成版 PDF。若不在 full-paper deadline 前完成并上传到指定字段，投稿包不满足 AAAI-27 明确要求。

### Major

1. **最终 PDF 尚未冻结。** `main.tex` 和 `main.pdf` 在审计期间多次变化，当前哈希不能作为上传依据。
2. **私人 OpenReview metadata 无法自动核验。** 标题、摘要、作者、profile、conflict、track、keywords 和提交状态都需要作者在截止前人工确认。
3. **portal 摘要可能仍是旧注册版本。** 当前摘要已删除 Q4/旧控制并把 endpoint 修正为完整预测窗口；必须核对 portal 实际文本。

### Minor / Unknown

1. AAAI 与 OpenReview 的公开页面未给出主 PDF 的最大文件大小；须在登录后的上传字段中确认。
2. 当前 PDF 匿名快照通过，但最终重新编译后仍须重复 metadata、字体和文本泄漏检查。

## 11. 当前最大提交风险与执行优先级

1. 立即填写并导出 Reproducibility Checklist；这是当前唯一已确认的官方硬阻塞。
2. 停止正文并行写入后生成、检查并冻结唯一最终 `main.pdf`。
3. 在 OpenReview 中逐字同步 title/abstract，确认作者、track、conflicts、keywords 和 declarations。
4. 上传最终 PDF 与 checklist，随后从 OpenReview 下载回验并记录最终 SHA、大小和提交时间。
5. Supplementary/code 可在之后的独立截止时间前处理，但不能替代 full-paper deadline 前必须完成的主 PDF 和 checklist。

## 12. 最终判定

`SUBMISSION_READINESS_BLOCKED`

解除阻塞的最低条件：

1. Reproducibility Checklist 34 项全部填写并生成可上传 PDF；
2. 最终主 PDF 停止变化并完成 `WAIT_FINAL_PDF` 清单；
3. 作者完成全部 `USER_ACTION_REQUIRED` 的 OpenReview 私有字段核对；
4. 两个必需 PDF 在 2026-07-29 11:59 UTC 前成功上传并下载回验。

