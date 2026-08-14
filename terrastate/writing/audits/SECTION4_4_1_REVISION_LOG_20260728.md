# TerraState Section 4.1 修订记录

**日期：** 2026-07-28  
**状态：** `READY_FOR_4_1_AUDIT`  
**范围：** Section 4.1、Table 1--3 的 AAAI-27 caption 结构及对应 Markdown 镜像  
**未触碰：** Section 3、Section 4.2--4.4 正文、Limitations、Conclusion、Figure 1--3、表格科学内容与证据文件

## 1. 作者最新确认的训练事实

> AUTHOR-CONFIRMED TRAINING FACT:  
> The final model evaluated in Q1–Q3 completed the full 40-epoch,  
> 14,880-update training protocol. Earlier 11,904/boundary80 wording is  
> obsolete and must not be restored.

本轮以该作者确认事实为最高权威。旧 evidence ledger 和旧审计中关于
`update 11,904`、`boundary80`、80% 边界 checkpoint、提前结束训练或未经历最后
20% 训练阶段的内容仅属于历史记录，不再描述 Q1--Q3 的最终实验模型。

## 2. 被废止的旧表述

以下内容已从英文 4.1、完整中文镜像及两个维护中的简版 Markdown 镜像移除：

- 最终 checkpoint 保存于 update 11,904；
- 最终模型是 boundary80 或 80% 边界模型；
- 最终模型没有经历最后 20% 训练阶段；
- 最终模型没有经历 partial unfreezing；
- history operator 在最终模型的完整训练路径中始终冻结；
- 由提前停止或边界 checkpoint 推导出的其他训练身份。

修订后，四份 4.1 均明确写明：Q1--Q3 使用同一个完成 40 epochs / 14,880
updates 完整训练协议的最终模型。

## 3. 修改前后的 4.1 结构

### 修改前 reverse outline

1. **Evaluation questions：** 列出 Q1--Q3，并在列表后说明 Q2/Q3 不重训练。
2. **Dataset and protocol：** GreenEarthNet、10→20 时序、OOD-t 样本量与
   validation-only selection。
3. **Metrics：** Q1 指标、Q2 两类 estimand、Q3 forecast-window loss 和
   geographic-cluster uncertainty。
4. **Comparisons：** 仅列出方法类别，未说明比较目的。
5. **Implementation and model selection：** 同时堆叠架构复述、精确参数统计、
   trainable 参数数、运行时 shape、optimizer 全配置、完整课程、partial
   unfreezing、候选选择以及已过时的 11,904/boundary80 身份。

### 修改后 reverse outline

1. **Evaluation questions：** 并行定义 Q1--Q3，同时固定同一个完成
   14,880 updates 的最终模型及 Q2/Q3 无需重训练。
2. **Dataset and protocol：** 建立 GreenEarthNet、10→20 时序、1,904 个
   OOD-t minicubes 及模型选择隔离。
3. **Metrics and statistical units：** 一次性区分 dataset-level、per-minicube
   paired 与 geographic-cluster 三类统计单位。
4. **Comparison purpose：** 说明 Table 1 用于确认 Q1 的 forecasting utility；
   load-bearing 与 weather response 由 Q2/Q3 同模型干预确定。
5. **Implementation and model selection：** 仅保留参数量、AdamW、40
   epochs / 14,880 updates、global batch 64、non-\(q\) learning rate、
   validation-only selection 与 final-model identity。

五个信息块均保持“一段一个职责”。

## 4. 英文单词数

采用同一 LaTeX 去命令后的 token 计数方法：

| 版本 | 4.1 英文单词数 |
|---|---:|
| 修改前 | 459 |
| 修改后 | 397 |
| 变化 | -62（-13.5%） |

压缩主要来自 implementation 段；Q1--Q3 的 protocol 和统计单位没有删除。

## 5. 保留的信息

- Q1 temporal-shift forecasting performance；
- Q2 state-mediated forecast contribution removal；
- Q3 actual / matched-donor / normalized-mean forecast-window fidelity；
- Q1--Q3 使用同一个最终 TerraState 模型；
- Q2/Q3 只改变冻结 forward computation，无需重新训练；
- GreenEarthNet、30 个五日 composites、\(128\times128\)、20 m；
- aligned meteorology、cloud/quality masks、static geography；
- 10 个历史 composites 与 20 个预测 composites；
- OOD-t 的 1,904 个 minicubes；
- validation-only model selection，OOD-t 与 intervention results 不参与选择；
- Q1 的 \(R^2\)、RMSE、NSE、absolute bias、\(\mathrm{RMSE}_{25}\)；
- Q2 的 official dataset-level \(\Delta R^2\)、per-minicube paired mean 和
  paired-bootstrap 95% CI 的分离；
- Q3 的完整 20-step masked MSE 和 geographic-cluster uncertainty；
- comparison categories；
- 7.18M 参数、AdamW、40 epochs / 14,880 updates、global batch 64、
  non-\(q\) learning rate \(3\times10^{-5}\)。

## 6. 压缩的信息

- 精确参数计数 `7,180,896 unique nn.Parameter scalars` 收敛为与 Table 1 一致的
  `7.18M parameters`；
- comparison 段从方法清单改为“比较目的 + 方法范围 + 与 Q2/Q3 的职责边界”；
- final-model identity 与 selection rule 合并为一个正向、可复核的句子；
- 数据段只保留科学协议，不再重复实现审计措辞。

## 7. 删除的信息

- Section 3 已经定义的 PVT v2/Contextformer、projector、transition 和 readout
  架构复述；
- 两阶段精确 trainable-parameter 数；
- state/runtime tensor shape；
- AdamW \(\beta\)、zero weight decay；
- warmup steps、cosine decay、gradient clipping；
- \(\lambda_s\) 的逐阶段课程；
- partial-unfreezing learning rate；
- teacher/target parameter-count audit；
- preregistered candidate 的工程叙述；
- 所有 11,904/boundary80、提前结束和“未经历最后阶段”表述。

这些删除不改变 Section 3 方法事实、Q1--Q3 结果或任何统计判据。

## 8. Final-model identity 核对

| 核对项 | 结果 |
|---|---|
| 完整训练协议 | 40 epochs / 14,880 updates |
| Q1 使用最终完整训练模型 | PASS |
| Q2 使用同一最终完整训练模型 | PASS |
| Q3 使用同一最终完整训练模型 | PASS |
| Q2/Q3 干预期间重新训练 | 否 |
| 模型选择依据 | validation forecasting performance only |
| OOD-t 参与模型选择 | 否 |
| Q2/Q3 intervention results 参与模型选择 | 否 |
| 4.1 中仍含 11,904/boundary80 | 否 |

## 9. 中英文与 Markdown 镜像同步

已同步：

- `paper/main.tex` 的英文 4.1；
- `MANUSCRIPT_ZH_FULL.md` 的完整中文 4.1；
- `MANUSCRIPT.md` 的英文阅读镜像 4.1；
- `MANUSCRIPT_ZH.md` 的中文阅读镜像 4.1。

四份文本的段落顺序、数字、统计单位、final-model identity 和主张强度一致。

## 10. Table 1--3 AAAI-27 compliance

AAAI-27 Author Kit 要求 table caption 位于表格下方、使用 10pt Roman；表体必要时
可使用 9pt，且不得通过 `resizebox` 或 `scalebox` 整体缩放。

| Table | Caption below | Caption 10pt | Body ≥9pt | No resizebox | Values unchanged |
|---|---|---|---|---|---|
| Table 1 | PASS | PASS | PASS | PASS | PASS |
| Table 2 | PASS | PASS | PASS | PASS | PASS |
| Table 3 | PASS | PASS | PASS | PASS | PASS |

三张表均采用：

`centering → {\small ... tabular ...} → caption → label`

PDF 字体检查显示三张 caption 均为 `TeXGyreTermesX-Regular`、约 9.96 pt；表体为
约 8.97 pt。`\small` 只包围表体。三张表的 tabular SHA-256 与修改前完全一致：

- Table 1：`e138d52fbfb8c374a48cd6342d8cc5b53a4f95773e228805092b4501dedbdf36`
- Table 2：`a372f2ae9fa3ce9d80298fee89453e1565e0eeabc269e671537baad42ebb069b`
- Table 3：`c33059fe7767b658cc70d193e83567ce34053f9d153e815dcd84122b48c8d991`

caption 文案的 SHA-256 也与修改前一致：

- Table 1：`2f0f82661d756fd2673eb02fba825f3e5eaadefdb09a0ad60987b3ab66adb832`
- Table 2：`2690aad11f7a8000b79d14fefacbc130a571f92230eac83673952973a93d9d1b`
- Table 3：`884c9a73d62adf4a93b398a4ffb370a6f4970a1a99559e02cc589d016c55d566`

## 11. 冻结内容回归

- 英文 Section 3 修改前后 SHA-256：
  `b054a42ed0783ad8bfbfa731bef5137cde11b68a58f1048ce12ad14fc4dbdf7d`
  （一致）；
- Section 4.2--4.4 正文（排除表格/图片环境）修改前后 SHA-256：
  `e8db1f805fa655588c27965b22b880573545cbbd336318cabace75d876828a13`
  （一致）；
- Figure 1--3 资产 SHA-256 与修改前一致；
- Table 1--3 的数值、行、列、CI、样本量、指标方向和 caption 文案均未改变。

## 12. 编译结果

使用项目内 TeX Live 2026：

`latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`

结果：

- PDF：`paper/main.pdf`
- 总页数：9（本轮按要求不处理分页）
- LaTeX errors：0
- undefined citations：0
- undefined references：0
- multiply-defined labels：0
- overfull boxes：0
- underfull hboxes：7
- underfull vboxes：1

普通 underfull 已记录，不在本轮反复改写。

## 13. 修改后 SHA-256

- `paper/main.tex`：
  `5e8b5c25464d9c80f82cbdecef546ca35d1ebd716cdf60795f711fa32dba6e5e`
- `MANUSCRIPT_ZH_FULL.md`：
  `50051d4ed77e424248e6e982f8a8820f1a9f3ea52df89757898021b1104fc4a4`
- `MANUSCRIPT.md`：
  `8458b4f7f31d7d7818fc813017dfa5b2ff08861da0d49dfda2c7b5826939e7fb`
- `MANUSCRIPT_ZH.md`：
  `b4ca861a423be7b19df1076d6d5b29896e026e86ad336f61b0cb98920abc7f94`
- `paper/main.pdf`：
  `b91c9bca08719e119388c8bc7a5a4900a9b70fa406f1e4b0a1d773e8833521fc`

## 14. 尚未处理

- Section 4.2；
- Section 4.3；
- Section 4.4；
- Figure 1--3；
- 全篇分页。

本轮没有自行继续上述任务。

## 15. 最终状态

`READY_FOR_4_1_AUDIT`
