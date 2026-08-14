# TerraState Section 2 Related Work 修订日志

**日期：** 2026-07-28  
**任务性质：** AAAI 写作校准后的定向修订  
**状态：** `SECTION2_REVISION_COMPLETE_READY_FOR_FINAL_AUDIT`

## 1. 修改范围与结论

本轮仅修改以下内容：

- `paper/main.tex` 的 Section 2 Related Work；
- `MANUSCRIPT.md` 的对应英文 Related Work；
- `MANUSCRIPT_ZH.md` 的对应中文 Related Work；
- `MANUSCRIPT_ZH_FULL.md` 的对应完整中文 Related Work；
- 由编译生成的 `paper/main.pdf` 及常规 LaTeX 中间文件；
- 新建本日志。

未修改 Title、Abstract、Introduction、Method、Experiments、Limitations、
Conclusion、Figure 1--3、caption、Table 1--3、实验数字、`references.bib`、
代码、模型、数据或证据文件。

修订后的英文 Related Work 保留三个 paragraph，正文共 **348 words**
（不含 Section/paragraph 标题；含标题为 363 words），位于建议的 330--390
词范围内。

## 2. 修改前后 SHA-256

| 文件 | 修改前 | 修改后 |
|---|---|---|
| `paper/main.tex` | `8191d0ba1de07711a5969dcb3822fe1aecd3669e5711c8d7ec58b10a540a8200` | `fffadb68876166ad12a93b2f50634494877dce44385ba5a9d809fe06d610b09a` |
| `MANUSCRIPT.md` | `08481eb5c5bb529429978a60d600d87b51118a02a1425736e333a6b94f0c66a7` | `ea801022bc815b51faeaebb9756138fc7e3caa643d5802dcd5beedd01cb98a07` |
| `MANUSCRIPT_ZH.md` | `614d94e59df4882b1fc45294567ef12ec99db75cc489d763b336f4530bec635b` | `eda2683e266c9ae37669c0c20741f7bf92879389aed9799305c02714728b7d94` |
| `MANUSCRIPT_ZH_FULL.md` | `1d26cdc8d3037116b79d3741a7be0fdeac3aae19794453a6cf23fabfd0bd2510` | `18c4637b50805c1169a7b5588e58ee9830dbb331ccd8146436e900154ee80815` |
| `paper/main.pdf` | `b35c21365f3f93545ce758a48fc1cd6cfcf7eba554ff9b6bf8605ad07b6ae306` | `a9108b654853a6df50a1350783051ba5fdafb81430d856a6c316ed0a5d9c8ba6` |

`paper/references.bib` 在修改前后均为
`e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659`。

## 3. Introduction 及范围未变验证

`paper/main.tex` 的 Introduction block（从
`\section{Introduction}` 到 `\section{Related Work}` 前）修改前后 SHA-256
均为：

`ce34d1ca444bf783eb4ccad116bfb1f4a9dde7f67a1d03dddd328eff04bc2b92`

Abstract block 修改前后均为：

`d067709e98b84830d0c5a3cd78ac1f51904e5a42ac0b70abb993186ab64721ab`

本会话完成 Section 2 替换后的首次范围检查中，从 `\section{Method}` 到文件末尾
仍为修改前 SHA：

`00c05ce0282e94d10f11323285ee964cc37125b45dde70bc4ad9e28487b95c28`

写日志期间，并行会话随后更新了该范围以及 Figure 3 导出资产；本会话没有覆盖或
回退这些外部修改。最终重新编译时，当前 Method 到文件末尾 SHA 为：

`d8d06bafd6082e7aaea423ae33d2d464b82895fab29cf861b9363f06e080b06c`

在并行更新前后，Introduction SHA 与本轮 Related Work SHA
`e6609d90667a20d41e196bca0c1da50e6b928428e707439b6368d155eee4bc94`
均保持不变。因此，表中 `main.tex` 和 PDF 的最终整文件 SHA 包含并行会话的
非 Section 2 更新；本轮可归因修改仍严格限于 Related Work。

三个 Markdown 镜像也通过分块哈希验证：各自的 Section 1 和 Section 3
以后内容均与修改前完全相同。

| 镜像 | Section 1 修改前后 SHA | Section 3 以后修改前后 SHA |
|---|---|---|
| `MANUSCRIPT.md` | `b3bb69be4770db6b682848a26bde13c1b4e3706afe96ba334eb36d71f7102f2d` | `22997a2e874df07f00fabe85e9c74fa5c67a021ca460dcc5d4fffe391f362303` |
| `MANUSCRIPT_ZH.md` | `7ed6a7c39658043fc663034fc948984f760e070fa5c5af61677853e33e53f117` | `52a180c2fde387b7c4cff1b4549ba020d8a9c0a5a8c2f7842edaac9e55d10247` |
| `MANUSCRIPT_ZH_FULL.md` | `2285cae439bae2330f5b2a6794562088bf59ed1d75a2184ffe4d8c758ea15c69` | `a7b87487adcaf8e9e1ae54123d2575f34fbe9053e9aefef1da9b40835db0aa80` |

## 4. 新 Section 2 三段反向提纲

| Paragraph | 唯一职责 | 正文词数 |
|---|---|---:|
| `Weather-conditioned EO forecasting.` | 建立任务输入与预测目标；按 deterministic、probabilistic 和 explicit latent-transition 三类综合工作；公平承认已有天气响应或表示分析；用一句话定位 TerraState 增加的 state-mediated contribution 与 supplied-weather response 检验 | 109 |
| `EO world models and forcing-conditioned simulation.` | 具体定位 EO-WM、VegSim 和 cloud-aware observability；比较未来 forcing、状态推进、输出响应和预测目标；用一句话定位 TerraState 的 removable state contribution 与 actual-vs-frozen-control complete-window fidelity | 135 |
| `Predictive-state and latent-dynamics foundations.` | 按状态定义、状态监督、动力学用途及是否进入预测/控制路径组织 PSR、latent world models、JEPA、LatentTSF 与 PLSM；用一句边界句限定 TerraState 不主张经典 PSR 保证、因果/完整物理状态或组合动力学 | 104 |

## 5. 每段的统一比较维度

1. **Weather-conditioned EO forecasting：** 输入条件、预测对象、预测分布形式以及主要输出级证据。
2. **EO world models and forcing-conditioned simulation：** 是否显式表示状态、未来 forcing 如何进入、如何推进/解码、如何评价 forcing response。
3. **Predictive-state and latent-dynamics foundations：** 状态如何定义、由什么监督、动力学如何使用，以及状态是否位于实际预测或控制路径上。

每段均采用“主题句 → 两至三类研究范式 → 最近邻的公平说明 → TerraState
在同一比较维度上的定位”结构，没有重复 Introduction 的完整 gap，也没有展开
Q1--Q3 公式、统计量或实验结果。

## 6. 模型名单到研究范式的综合

- ConvLSTM、PredRNN、SimVP 和 Earthformer 不再逐篇摘要，而被综合为 recurrent、
  convolutional 和 transformer deterministic predictors。
- MCVD 与 VegeDiff 被综合为表示多个可能未来的 probabilistic video/diffusion
  路线。
- ViT-Koop 单独保留为 explicit compressed latent transition 的代表，因为其
  Koopman operator 与本段统一比较轴直接相关。
- World Models、PlaNet 与 Dreamer 被综合为 compact latent dynamics for
  prediction/control。
- I-JEPA 与 V-JEPA 被综合为 representation prediction 路线。
- EO-WM、VegSim、LatentTSF 和 PLSM 因与本文定位最近或承担关键反例功能，保留
  更具体说明。

## 7. 重要近邻定位核对

- **EarthNet2021：** 继续作为 weather-guided land-surface forecasting 的任务锚点；
  `references.bib` 记录为 CVPRW 2021。
- **GreenEarthNet/Contextformer：** 继续定位为植被动态预测任务与方法；
  `references.bib` 记录为 CVPR 2024。
- **Diaconu et al.：** 明确承认其同时研究天气输入的预测价值与单变量天气改变时
  的输出响应，没有写成此前无人检查天气；`references.bib` 记录为 CVPRW 2022。
- **VegeDiff：** 作为 probabilistic diffusion 路线综合引用；正式年份按
  `references.bib` 条目正文为 IEEE TGRS 2025，未因 key 含 `2024` 而改 key。
- **ViT-Koop：** 准确保留线性 Koopman operator 推进压缩 EO state 的定位；
  `references.bib` 记录为 ICCVW 2025。
- **EO-WM：** 保留 partially observed、weather-driven framing，
  climatology/anomaly/accumulated-stress forcing，以及 extreme-summer /
  seasonal matched-pair output diagnostics；继续作为 recent preprint。
- **VegSim：** 保留 sparse NDVI history、latent vegetation state、
  user-specified future weather 下 recurrent rollout 与 NDVI quantiles；
  只称 forecasting/scenario-conditioned simulation，不作因果解释；继续作为
  recent preprint。
- **Cloud-aware observability：** 保留为 latent EO world model 但预测目标不同
  的边界例子，明确目标是 usable acquisition，而非 future land-surface pixels；
  继续作为 recent preprint。
- **LatentTSF：** 用于支持 accurate forecasts 与 temporally disordered latent
  representations 可以并存；按 `references.bib` 保持 ICML 2026 正式论文身份，
  未称为 preprint。
- **PLSM：** 明确限定在 agent-action control setting，避免把 control action
  直接类比为天气的因果控制。

本轮未修改任何 BibTeX 元数据。未发现需要在本日志中新增的元数据阻塞。

## 8. 删除、保留和引用变化

修订后 Section 2 使用 21 个不同 citation keys。

- **删除正文引用：** `chen2023deeposg`、`wang2026groupactions`。
- **删除文字：** structured operator、Deep-OSG、World Models as Group Actions
  及其 group-action/temporal-composition 尾句。
- **保留但综合：** 通用 deterministic predictors、probabilistic predictors、
  latent world models 与 joint-embedding predictors。
- **保留具体定位：** EarthNet2021、GreenEarthNet/Contextformer、Diaconu、
  ViT-Koop、EO-WM、VegSim、cloud-aware observability、LatentTSF、PLSM。
- **未新增引用：** 没有加入 RS-WorldModel、RemoteBAGEL、Earth-o1 或其他任务
  不同的遥感生成工作。

删除只发生在 Section 2 正文；`references.bib` 中相应条目按要求保留。

## 9. 英中镜像同步

- `paper/main.tex` 与 `MANUSCRIPT.md` 的三段标题、段落顺序、英文事实和主张边界
  一致。
- `MANUSCRIPT_ZH_FULL.md` 与 `MANUSCRIPT_ZH.md` 使用同一份自然学术中文：
  “天气条件 EO 预测”“EO 世界模型与驱动条件模拟”“预测状态与潜动力学基础”。
- 两个中文镜像均同步删除 endpoint、composition/group-action 旧叙事，并统一为
  actual weather 相对 frozen matched-donor / normalized-mean controls 的完整窗口
  预测保真度。
- 中文没有增强因果、反事实、SOTA、完整物理状态或 generative simulator
  主张。

## 10. 跨节一致性

- **Abstract：** Section 2 继续服务“可检验预测状态”主线，不把架构命名本身当作
  world-model 证据。
- **Introduction：** 第一段承认输出级评价及已有 response/representation
  analysis，避免把近邻统一写成只报告精度；第二、三段精确支撑 Introduction
  中 on-path state、weather forcing 和完整窗口 fidelity 的定位。
- **Method：** Related Work 只保留机制层面的对照，没有重复 \(q/P/T/O\) 公式、
  direct-horizon transition、训练系数或干预协议。
- **Results：** 没有写实验数字。Q1 仍只支持 useful forecasting skill；Q2
  state removal 仍是 primary evidence；Q3 仍区分 output response 与
  complete-window fidelity；没有恢复 hot-dry enhancement 或 Q4。

## 11. 编译与版面检查

编译目录：

`/mnt/data/users/luzheng/workspace/iclr/czj/TerraState_AAAI27/paper/`

编译命令：

```bash
PATH=/mnt/data/users/luzheng/workspace/iclr/czj/.tools/texlive-2026/bin/x86_64-linux:$PATH \
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

结果：

| 检查项 | 结果 |
|---|---|
| LaTeX error / undefined control sequence | 0 |
| Undefined citation | 0 |
| Undefined reference | 0 |
| Overfull hbox / vbox | 0 / 0 |
| Underfull hbox / vbox | 14 / 1 |
| PDF 页数 | 9 |
| Related Work 位置 | 第 2--3 页 |
| Method 开始 | 第 3 页 |
| Figure 2 caption | 第 6 页 |

Underfull 警告来自双栏中的长 paragraph 标题、长作者列表及其他既有段落；
没有 overfull 或内容越界。已视觉检查 PDF 第 2、3、6 页：Section 2 阅读顺序
正常，Method 自然接续，Figure 2 的浮动位置没有与 Section 2 冲突。所有引用均
紧邻其所支持的工作类别或具体事实。并行 Figure 3 会话完成后，最终 PDF 已再次
确认可由 PyPDF 与 MuPDF 正常解析，9 页均可渲染。

## 12. 保持冻结的内容

本轮保持不变：

- Title、Abstract、Section 1、Section 3--6；
- Figure 1--3 及其 caption、源文件和导出文件；
- Table 1--3；
- Q1--Q3 的全部数字、estimand、置信区间和主辅证据层级；
- Q1 useful-skill 边界；
- Q2 state removal 为 primary、identity transition 为 supporting 的边界；
- Q3 84-pair matched protocol、detectable output response、actual-vs-control
  complete-window fidelity 和 hot-dry null；
- 不主张 SOTA、严格排名、因果/反事实正确性、完整物理状态、
  extreme-specific enhancement、Q4/composition/non-collapse；
- `references.bib` 和所有证据、代码、模型、数据文件。

## 13. Section 1 后续终审接口

当前没有必须等待 Section 1 终审才能解决的阻塞。若 Section 1 终审产生少量定位
变化，只需回归以下三个接口，不应重新打开 Section 2 的文献范围：

1. Introduction 对“现有研究主要报告 output quality”的限定范围，应与 Section 2
   第一段的 “sometimes complemented by response or representation analysis” 一致；
2. Introduction 对 TerraState world-model 身份与 on-path state 的表述，应与
   Section 2 第二、三段的 removable contribution 定位一致；
3. Introduction 对 Q3 的概述，应继续使用 actual-vs-frozen-control
   complete-window fidelity，不恢复 endpoint、因果或 extreme-specific 叙事。

完成这些接口的跨节回归前，不宣布 `SECTION2_FROZEN`。
