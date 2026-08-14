# TerraState Section 4.2 修订记录

**日期：** 2026-07-28  
**状态：** `READY_FOR_4_2_AUDIT`  
**范围：** Section 4.2 结果段及三份 Markdown 镜像；两份简版 Markdown 的
Table 1 向权威 `main.tex` 单表同步  
**未触碰：** Section 4.1、4.3、4.4、Section 3、其他正文、权威 LaTeX
Table 1、Table 2–3、Figure 1–3、实验与证据文件

## 1. 修改前后 reverse outline

### 修改前

1. 以 “Table 1 summarizes Q1” 导航表格；
2. 报告 \(R^2\) 与 RMSE；
3. 以 useful predictive skill 作简短结论。

该版本没有解释短时域表现、混合指标轮廓，也没有建立 Q1 到 Q2/Q3 的逻辑接口。

### 修改后

1. **Q1 结论：** TerraState 在 GreenEarthNet OOD-t 时间偏移下保留有效预测能力；
2. **核心数字：** 1,904 个 minicube，\(R^2=0.56935\)，RMSE \(=0.15059\)；
3. **短时域维度：** \(\mathrm{RMSE}_{25}=0.082\)，对应前 25 个预测日的较低误差；
4. **混合轮廓：** overall RMSE 与多种学习型预测器处于同一数值范围，但
   \(R^2\) 和 NSE 并非表中最高；
5. **证据链接口：** Q1 建立预测前提，Q2/Q3 再分别检验同一模型的状态贡献与
   天气响应。

最终为一个段落、五句话。

## 2. 英文单词数

采用同一 LaTeX-aware 计数：`\ref{}` 转写为可读表号，数学命令转写为其文本内容，
其余 LaTeX 标记移除；带连字符词计为一个词。

| 版本 | 单词数 |
|---|---:|
| 修改前 | 23 |
| 修改后 | 110 |
| 变化 | +87 |

修改后位于预定的 100–130 词范围内。

## 3. 五句话的职责

| 句子 | 唯一职责 |
|---|---|
| 1 | 直接回答 Q1，并限定 GreenEarthNet OOD-t temporal shift |
| 2 | 报告样本量、\(R^2\)、RMSE，并引用 Table 1 |
| 3 | 解释 \(\mathrm{RMSE}_{25}\) 和前 25 个预测日 |
| 4 | 透明说明 mixed metric profile |
| 5 | 把 Q1 定位为 Q2/Q3 内部状态检验的预测前提 |

## 4. 使用的 Q1 数字

- OOD-t minicubes：1,904；
- \(R^2=0.56935\)；
- RMSE \(=0.15059\)；
- \(\mathrm{RMSE}_{25}=0.082\)。

正文没有复述 NSE、absolute bias 或参数量；这些精确汇总继续由 Table 1 承担。

## 5. Mixed profile 与 trade-off

正文将 \(\mathrm{RMSE}_{25}=0.082\) 表述为 TerraState 在表中相对最有利的
性能维度，同时明确：

- overall RMSE \(=0.151\) 落在多种学习型预测器的数值范围内；
- TerraState 的 \(R^2\) 与 NSE 不是表中最高值；
- Q1 支持 useful forecasting skill，而非 uniform metric leadership。

正文没有把任何指标差距归因于 predictive-state architecture，也没有把
Q2/Q3 证据用于掩盖 Q1 的混合轮廓。

## 6. Q1 到 Q2/Q3 的接口

末句只说明证据职责：

- Q1 建立值得继续检查内部预测状态的预测前提；
- Q2 检验同一模型的 state contribution；
- Q3 检验同一模型的 weather response。

该句不提前报告 Q2/Q3 数字，也不把 Table 1 单独解释为 world-model 证据。

## 7. 禁止词与旧标签扫描

### 4.2 英文结果段

以下表述均为 0：

- `competitive`；
- `SOTA` / `state of the art`；
- `best-performing`；
- `uniformly superior`；
- `outperforms`；
- `non-inferior`；
- `statistically equivalent`；
- `nearly matches`。

### 两份简版 Markdown 的 Table 1–4.2 区间

以下旧双面板标签和结构均为 0：

- `Published`；
- `Reported`；
- `Local` / `local OOD-t`；
- `public panel` / `published panel` / `local panel`；
- `Source / protocol` / `来源/协议`；
- `公开面板` / `本地面板` / `本地评测`。

旧双面板、来源列、来源说明和防御性 4.2 句子均已从该区间清除。

## 8. 四份文本同步

| 文件 | 4.2 状态 | Table 1 状态 |
|---|---|---|
| `paper/main.tex` | 英文权威段已更新 | 权威表未修改 |
| `MANUSCRIPT_ZH_FULL.md` | 完整中文镜像已同步 | 原有统一表保持不变 |
| `MANUSCRIPT.md` | 英文阅读镜像已同步 | 旧双面板已逐项同步为权威统一表 |
| `MANUSCRIPT_ZH.md` | 中文阅读镜像已同步 | 旧双面板已逐项同步为权威统一表 |

简版表格逐项复制权威 Table 1 的九行、七列和全部显示精度，没有反向修改
`main.tex`。

## 9. Table 1 冻结回归

权威 LaTeX Table 1 修改前后均未变化：

- 完整 `table*` 环境 SHA-256：  
  `ec5b1dd99126d54306894f5263c9f1dad6247ae2c805899fc00e0d75c2f3cfce`
- `tabular` 内容 SHA-256：  
  `e138d52fbfb8c374a48cd6342d8cc5b53a4f95773e228805092b4501dedbdf36`

Section 3、4.1 与 4.3 的区间 SHA-256 也保持修改前基线：

- Section 3：  
  `b054a42ed0783ad8bfbfa731bef5137cde11b68a58f1048ce12ad14fc4dbdf7d`
- Section 4.1：  
  `9feea977ba80119b27150811ca2cb50471f7bf0c8380d7e2aad95466cf8b5f45`
- Section 4.3：  
  `83213677f51c2ea4dab3f0ef0470fafbabf9e9f9e2077b095c6b0ed74abcb229`

## 10. 编译结果

使用工作区内 TeX Live 2026：

`latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`

结果：

- PDF：`paper/main.pdf`
- 编译成功：是；
- LaTeX errors：0；
- undefined citations：0；
- undefined references：0；
- multiply-defined labels：0；
- overfull boxes：0；
- underfull hboxes：7；
- underfull vboxes：0。

普通 underfull 已记录；本轮按约束不为其改写其他正文或调整浮动布局。

## 11. 修改后 SHA-256

- `paper/main.tex`：  
  `f6859f34c0585715bb59d6ebf4bc8fa96640874b3f030c0a931252c9cf4f6aa3`
- `MANUSCRIPT_ZH_FULL.md`：  
  `c65ca3f9f6ade20951bf129945c6b0e938530e185755969c569f99df09c80b4c`
- `MANUSCRIPT.md`：  
  `01a89e1133509878ad7743a31a221399ce7d2f0c1be4d05aa51f25fb61e064e2`
- `MANUSCRIPT_ZH.md`：  
  `47899d628bf3a6c7e6d230e7888230a57254e72840d99766670fd2dccb434d2e`
- `paper/main.pdf`：  
  `d1e4b8dded5d477a6bbd89d04b00875c8051b0edd61769a0aa1630e0c721fa6d`
- 4.2 英文正文：  
  `57d9fd6e63d336d00391ecc3dea1bb3713035b94fd77910f14186f96c3253d73`

## 12. 尚未处理

- Section 4.3；
- Section 4.4；
- Figure 1–3；
- 全篇分页和浮动布局。

本轮没有自行继续这些任务。

## 13. 最终状态

`READY_FOR_4_2_AUDIT`
