# TerraState AAAI-27 Section 4.3 独立最终审计

**审计日期：** 2026-07-28  
**审计对象：** 最新 Section 4.3 “Load-Bearing Predictive State”、Table 2 及四份中英文文本  
**审计性质：** 独立、只读的 AAAI 机制结果、冻结证据、主张边界、双语镜像和编译版面终审  
**权威正文：** `paper/main.tex`  
**目标 venue：** AAAI-27 Main Technical Track  

## 1. 最终结论

# SECTION4_4_3_FROZEN

最新版 4.3 已达到正式 AAAI 方法论文机制结果段的质量，可以冻结。当前内容形成了
清楚且完整的结果链：

> load-bearing 结论 → primary paired evidence → dataset-level effect size
> → 有限科学解释 → supporting diagnostic boundary

State removal 始终是定义 load-bearing 的 primary intervention；
\(T_\psi\!\rightarrow I\) 始终只是 learned-transition involvement 的 supporting
diagnostic。Validation 和 OOD-t 上的 paired mean、paired-bootstrap 95% CI、
paired \(n\) 与 official dataset-level effect 均与冻结 JSON 一致，两种 estimand
没有混写。限制句明确排除了“全部预测信息都经过状态”，最后一句进一步排除了
transition necessity。

Table 2 的六列表体和全部数值保持不变，caption 已正确补入
\(n=589/1{,}019\)，并保持 caption 在表格下方。四份文本采用相同的结论、数值、
证据顺序和主辅层级。当前编译无 LaTeX error、未定义引用、重复 label 或 overfull
box。

### 问题计数

| 等级 | 数量 | 结论 |
|---|---:|---|
| Critical | **0** | 无事实、统计、证据或编译阻塞 |
| Major | **0** | 无结构、主张边界、表格或镜像问题 |
| Minor | **0** | 修改前审计提出的四项 Minor 均已关闭 |

平均质量评分：**4.9 / 5.0**。

---

## 2. 审计范围与并行读取安全

已读取并核对：

1. `paper/main.tex`，包括当前 4.1--4.4、Section 3.4、Table 1--3 和
   Abstract/Introduction/Conclusion；
2. `MANUSCRIPT_ZH_FULL.md` 当前 4.3；
3. `MANUSCRIPT.md` 当前 4.3；
4. `MANUSCRIPT_ZH.md` 当前 4.3；
5. `SECTION4_4_3_AAAI_AUDIT_20260728.md`；
6. `SECTION4_4_3_REVISION_LOG_20260728.md`；
7. `SECTION4_4_2_FINAL_AUDIT_20260728.md`；
8. `METHOD_3_4_FINAL_AUDIT_20260728.md`；
9. 两份冻结 Q2 release JSON；
10. 当前 `paper/main.log`、`paper/main.aux` 和 `paper/main.pdf`。

本轮采用作者最新事实：

- Q1--Q3 使用同一个最终 TerraState 模型；
- 最终模型完成 40 epochs / 14,880 updates；
- Q2 是该冻结模型上的 forward intervention，不重新训练；
- 11,904/boundary80 已失效。

当前 4.1 明确写出上述身份，4.3 没有恢复任何历史 checkpoint 身份或重新训练叙事。

### 2.1 起始与结束文件 SHA-256

审计开始和报告成稿前的以下 SHA 完全一致：

| 文件 | 开始 SHA-256 | 结束 SHA-256 | 判断 |
|---|---|---|---|
| `paper/main.tex` | `7e2e5f33a6584a0d1558041e27cf31fd4c4124c9aa1cfcd33b642874a28e11c2` | 同左 | 未变 |
| `MANUSCRIPT_ZH_FULL.md` | `7c987ff0a581efa70fcad56ae5eecf24ebf107794b5f29c7694b5222ad828469` | 同左 | 未变 |
| `MANUSCRIPT.md` | `91b1de611e21c0d6f283e68e90af374804834dead982e1dce9b53c01943270db` | 同左 | 未变 |
| `MANUSCRIPT_ZH.md` | `b3d88f0d5a07e8984b0c102ec56522dbb38b8e8e0b3f2e68dd5abd0ee9303354` | 同左 | 未变 |
| `paper/main.log` | `0cedde3c65f077cf8d782261ae537a6b126f9a45f18b254753219f46e39fd63d` | 同左 | 未变 |
| `paper/main.aux` | `40f1d7bee22991f4f5efaa055fe3ba6131bfa5a6d0c0ab78bf1524564f4d74e2` | 同左 | 未变 |
| `paper/main.pdf` | `4238bcdbde2785f8a135f27165f4340e50af1de358501a97cfebecb36d8cbcd6` | 同左 | 未变 |

### 2.2 Section 4.3、Table 2 和四份文本的局部 SHA

| 对象 | 开始 SHA-256 | 结束 SHA-256 | 判断 |
|---|---|---|---|
| 权威 Section 4.3（含 Table 2） | `393750e4bb4f8e23703ebac4dd0ccd510257e5b62f00b216a32fe15b9a5a9d3a` | 同左 | 与修订日志一致 |
| Table 2 完整 `table*` 环境 | `5281b09bbfaff9f57ed1ef17f243b161d2588ea571c7aca393ce0b62fadb1197` | 同左 | 未变 |
| Table 2 `tabular` | `a372f2ae9fa3ce9d80298fee89453e1565e0eeabc269e671537baad42ebb069b` | 同左 | 与修订前/后冻结值一致 |
| Table 2 当前 caption 正文 | `e4b2641a8ddc092ffbe3f1f39aa566bca5fb5823aa2de85d30e03075d37594ac` | 同左 | 包含 paired \(n\) |
| `MANUSCRIPT_ZH_FULL.md` 4.3 区块 | `49d174fad00a00bb0388a13e6814986b9a8db1ea8e1af6e6a663ec43313fe0c6` | 同左 | 未变 |
| `MANUSCRIPT.md` 4.3 区块 | `310dcaf4d96bb9b08cfb95cef837d8617b873c49b2b997ca8d7bead0d4e80bdd` | 同左 | 未变 |
| `MANUSCRIPT_ZH.md` 4.3 区块 | `0ce88ca14a8171750cc4e95958d192e1a05a42bdce3e6e3318f487eae63556cc` | 同左 | 未变 |

没有发生并行修改，因此无需更换审计基线。

---

## 3. 结构与写作质量终审

### 3.1 当前结果链

| 位置 | 唯一职责 | 当前实现 | 判定 |
|---|---|---|---|
| Table 2 前首句 | 直接回答 Q2，并声明主辅层级 | 结论先行；state removal primary；\(T\to I\) supporting | **PASS** |
| Table 2 | 展示两个 split 的完整 aggregate 和 paired 统计 | 六列集中呈现 exact values | **PASS** |
| 结果句 1 | 报告 primary paired evidence | 两个 split 的 paired mean、CI、\(n\)；区间均排除零 | **PASS** |
| 结果句 2 | 报告另一 estimand 的 dataset-level scale | official full-minus-removal effect 单独成句 | **PASS** |
| 结果句 3 | 给出有限机制含义 | measurable forecast increment；明确不是全部预测信息 | **PASS** |
| 结果句 4 | 报告 supporting transition diagnostic | 只解释为 transition involvement | **PASS** |
| 结果句 5 | 限定 supporting diagnostic | OOD readout-state 风险；不支持 transition necessity | **PASS** |

这正是成熟机制结果段所需的：

> conclusion → primary evidence → aggregate scale → bounded interpretation
> → supporting evidence and caveat

### 3.2 指定写作问题

| 检查项 | 终审结论 |
|---|---|
| 首句是否直接给出 load-bearing 结论 | **是** |
| State removal 是否始终为 primary | **是**；正文与 caption 均明确 |
| \(T\to I\) 是否始终为 supporting | **是**；未用于定义 load-bearing |
| 是否逐格朗读 Table 2 | **否**；正文只提取 state removal 的必要证据和 \(T\to I\) 的方向 |
| 约 135 词是否自然 | **是**；LaTeX-aware 口径约 135 词，六句职责清楚 |
| 是否像内部实验记录 | **否**；没有 checkpoint、gate、provenance 或 audit 语气 |
| 是否专业紧凑 | **是**；统计量密度高但层级明确 |
| 是否与冻结 4.1/4.2 一致 | **是**；同样采用结论先行、有限解释和稳定术语 |

修改前审计的四项 Minor 已全部关闭：

1. load-bearing 结论已前置；
2. paired primary evidence 已先于 official effect；
3. paired \(n\) 已加入正文和 caption；
4. 两个简版 Markdown 已同步为六列表格和相同叙事。

---

## 4. Q2 冻结证据核对

### 4.1 冻结文件

| 数据源 | SHA-256 |
|---|---|
| `evidence_workspace/raw/release/val_q2_state_contract_exclusive.json` | `33b40d3e6bf6e0190c9415a9e0421e9809063356dcba2350890defeeed35f2d9` |
| `evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json` | `7ebc0569d705a9991ac8b8d17c42113c9da052b2bec73f7c28d021e28a65a051` |

### 4.2 State removal：primary evidence

| Split | 冻结 JSON 精确值 | 当前正文/Table 2 | 判定 |
|---|---:|---:|---|
| Validation paired mean \(\Delta R^2\) | 0.01616252595360122 | 0.01616 | **PASS** |
| Validation paired 95% CI | [0.006432408120151691, 0.02590229577842624] | [0.00643, 0.02590] | **PASS** |
| Validation paired \(n\) | 589 | 589 | **PASS** |
| Validation official full-minus-removal | 0.011214424211727803 | 0.01121 | **PASS** |
| OOD-t paired mean \(\Delta R^2\) | 0.021997768589881533 | 0.02200 | **PASS** |
| OOD-t paired 95% CI | [0.014219898623411737, 0.03017606928017251] | [0.01422, 0.03018] | **PASS** |
| OOD-t paired \(n\) | 1,019 | 1,019 | **PASS** |
| OOD-t official full-minus-removal | 0.019972010271822827 | 0.01997 | **PASS** |

两个 paired-bootstrap 区间的下界均大于零。正文正确写为
`both paired-bootstrap intervals exclude zero`，没有使用含糊或额外的显著性语言。

### 4.3 Table 2 其余 full / state-removed / \(T=\mathrm{Id}\) 数值

| Split / Configuration | \(R^2\) | RMSE | Official \(\Delta R^2\) | Paired mean [95% CI] | 判定 |
|---|---:|---:|---:|---|---|
| Validation / Full | 0.49732 | 0.15729 | reference | --- | **PASS** |
| Validation / State removed | 0.48611 | 0.17101 | 0.01121 | 0.01616 [0.00643, 0.02590] | **PASS** |
| Validation / \(T=\mathrm{Id}\) | 0.48542 | 0.26102 | 0.01191 | 0.01742 [0.00782, 0.02696] | **PASS** |
| OOD-t / Full | 0.56935 | 0.15059 | reference | --- | **PASS** |
| OOD-t / State removed | 0.54938 | 0.16519 | 0.01997 | 0.02200 [0.01422, 0.03018] | **PASS** |
| OOD-t / \(T=\mathrm{Id}\) | 0.54766 | 0.25832 | 0.02169 | 0.02402 [0.01609, 0.03217] | **PASS** |

所有显示值都是冻结 JSON 精确值在当前表格精度下的正确舍入。

### 4.4 Estimand 区分

| 统计量 | 定义 | 当前处理 | 判定 |
|---|---|---|---|
| Official \(\Delta R^2\) | 两个 dataset-level \(R^2\) 的 full-minus-intervention 差 | caption 定义；正文独立成句 | **PASS** |
| Paired mean \(\Delta R^2\) | 逐 minicube paired effect 的均值 | caption 定义；作为 primary evidence 先报告 | **PASS** |
| Paired 95% CI | 对逐 minicube paired effect 的 bootstrap 区间 | 只连接 paired mean，不连接 official effect | **PASS** |
| Paired \(n\) | Validation 589；OOD-t 1,019 | caption 与正文一致 | **PASS** |

冻结 JSON 内部包含 `dr2_floor=0.005`，但当前 4.3、Table 2 和四份镜像均未将
该内部 gate 写为论文判据。论文判据继续是 paired effect 的预设区间排除零。

---

## 5. 主张边界终审

### 5.1 当前可以支持

- TerraState's state-mediated contribution is load-bearing on Validation and
  OOD-t；
- removing the state contribution reduces forecast quality on both splits；
- the explicit state path carries a measurable forecast increment；
- both paired-bootstrap intervals exclude zero；
- \(T\to I\) supports learned-transition involvement。

### 5.2 当前没有越界

| 禁止主张 | 当前 4.3 状态 | 判定 |
|---|---|---|
| Entire forecast depends on the state | 明确写出不意味着全部预测信息经过该路径 | **PASS** |
| All predictive information passes through it | 作为合法否定出现 | **PASS** |
| Necessary-and-sufficient state | 未出现 | **PASS** |
| Complete physical state | 未出现 | **PASS** |
| Causal contribution | 未出现 | **PASS** |
| Counterfactual correctness | 未出现 | **PASS** |
| Transition necessity | 明确写出 \(T\to I\) 不建立 necessity | **PASS** |
| OOD-t effect is significantly stronger | 未比较两个 split 的 effect difference | **PASS** |
| Non-collapse | 未出现 | **PASS** |
| Composition / Q4 | 未出现 | **PASS** |

### 5.3 Limiting sentence

当前两层限制足以阻止过度解释：

1. `without implying that all predictive information passes through it`
   将 load-bearing 限定为可测 forecast increment，而不是整个预测的必要路径；
2. `it does not establish transition necessity`
   将 identity intervention 限定为 supporting diagnostic，并由
   readout 可能接收训练分布外状态这一具体混淆支撑。

限制清楚但不过量，没有反过来削弱已支持的 Q2 结论。

---

## 6. Table 2 最终审计

### 6.1 科学内容与职责

| 检查项 | 当前状态 | 判定 |
|---|---|---|
| Table 2 只回答 Q2 | 是 | **PASS** |
| 表体列数 | 六列 | **PASS** |
| Full / state removed / \(T=Id\) | 两个 split 均完整 | **PASS** |
| Official 与 paired effect | 分列 | **PASS** |
| State removal primary | caption 明确 | **PASS** |
| \(T\to I\) supporting | caption 明确 | **PASS** |
| Paired \(n\) | caption 正确加入 589/1,019 | **PASS** |
| 表体结果是否改变 | `tabular` SHA 与冻结值一致 | **UNCHANGED** |

### 6.2 AAAI 格式与 PDF 几何

| 检查项 | 当前状态 | 判定 |
|---|---|---|
| 源码顺序 | `tabular → caption → label` | **PASS** |
| Caption 位置 | 表格下方 | **PASS** |
| Caption 字体 | PDF 约 9.96 pt、Roman | **PASS** |
| Table body 字体 | 主体约 8.97 pt，即 nominal 9 pt | **PASS** |
| Booktabs | 使用 `toprule/midrule/bottomrule` | **PASS** |
| 竖线 / 密集 `hline` | 无 | **PASS** |
| `resizebox/scalebox` | 无 | **PASS** |
| Negative spacing | 无 | **PASS** |
| 页面宽度 | 表格与 caption 的文本边界为 \(x=54.0\) 至 \(558.0\) pt | **PASS** |
| 裁切 / margin intrusion | 所有相关 span 位于 \(612\times792\) pt 页面内部 | **PASS** |
| 可见重叠 | 未发现实质性文字重叠 | **PASS** |
| Label/reference | `tab:q2` 解析为 Table 2，第 7 页 | **PASS** |

Caption 加入 paired \(n\) 后仍保持在约 36.6 pt 高度内，没有造成裁切、溢出或
不可读问题。

### 6.3 正文与表格阅读顺序

- 4.3 正文位于 PDF 第 5 页右栏；
- Table 2 作为双栏浮动体位于第 7 页，紧接 Table 1，并位于 Figure 3 之前；
- 4.3 正文自身完整报告 primary paired evidence、official scale、科学含义和
  supporting boundary，因此表格延后不会造成逻辑断裂；
- Table 2 caption 自包含，读者在第 7 页仍能独立恢复两种 estimand 和主辅层级。

在当前双栏浮动约束下，阅读顺序可以接受，不构成 4.3 冻结问题。

---

## 7. 中英文与镜像同步

### 7.1 四份文本语义

| 信息 | `main.tex` | 完整中文 | 英文简版 | 中文简版 | 判定 |
|---|---:|---:|---:|---:|---|
| 结论先行 | 是 | 是 | 是 | 是 | **PASS** |
| State removal primary | 是 | 是 | 是 | 是 | **PASS** |
| \(T\to I\) supporting | 是 | 是 | 是 | 是 | **PASS** |
| Paired evidence 先于 official effect | 是 | 是 | 是 | 是 | **PASS** |
| Validation \(n=589\) | 是 | 是 | 是 | 是 | **PASS** |
| OOD-t \(n=1{,}019\) | 是 | 是 | 是 | 是 | **PASS** |
| Measurable forecast increment | 是 | “可测量的预测增量” | 是 | 同义 | **PASS** |
| 非全部预测信息 | 明确 | 明确 | 明确 | 明确 | **PASS** |
| \(T\to I\) OOD-readout caveat | 明确 | 明确 | 明确 | 明确 | **PASS** |

中文的“承载可测量的预测增量”与英文 `carries a measurable forecast increment`
强度一致，没有扩大为“整个预测完全依赖状态”“必要且充分”或完整物理状态。

### 7.2 简版 Table 2

`MANUSCRIPT.md` 和 `MANUSCRIPT_ZH.md` 当前 Table 2 均为：

- 7 个内容行：1 个表头 + 6 个配置行；
- 六列；
- 包含 \(R^2\)、RMSE、official effect 和 paired effect/CI；
- caption/表注包含 \(n=589/1{,}019\)；
- 不再使用旧八列结构。

**四份文本同步：PASS。**

---

## 8. 冻结回归

### 8.1 修订日志区块 SHA

当前区块 SHA 与 `SECTION4_4_3_REVISION_LOG_20260728.md` 的“修改前后保持一致”
基线逐项相同：

| 冻结区块 | 修订日志基线 | 当前 SHA-256 | 判定 |
|---|---|---|---|
| Section 3 | `b054a42ed0783ad8bfbfa731bef5137cde11b68a58f1048ce12ad14fc4dbdf7d` | 同值 | **UNCHANGED** |
| Section 4.1 | `9feea977ba80119b27150811ca2cb50471f7bf0c8380d7e2aad95466cf8b5f45` | 同值 | **UNCHANGED** |
| Section 4.2 | `1255639a23e12090bece746b81f879ac3adcaa3af789d018adb22c3898666740` | 同值 | **UNCHANGED / FROZEN** |
| Section 4.4 | `017ba3a9643c878a4cd885709d7cddd634859fef759b050059f4ae5964da74b4` | 同值 | **UNCHANGED** |

### 8.2 表格与其他范围

| 对象 | 回归依据 | 判定 |
|---|---|---|
| Table 1 | 当前 `tabular` SHA `e138d52f…bdf36` 与既有冻结基线一致 | **UNCHANGED** |
| Table 2 body | 当前 `tabular` SHA `a372f2ae…69b` 与修订前/后基线一致 | **UNCHANGED** |
| Table 3 | 当前 `tabular` SHA `c33059fe…991` 与既有冻结基线一致 | **UNCHANGED** |
| Figure 1--3 | 修订日志明确排除；当前 `main.tex` 全文件 SHA 与修订日志最终值一致 | **UNCHANGED BY 4.3 REVISION** |
| Abstract / Introduction / Conclusion | 修订日志明确排除；当前全文件 SHA 与修订日志最终值一致 | **UNCHANGED BY 4.3 REVISION** |

4.3 修改没有改变 Section 3、4.1、冻结的 4.2、4.4、Table 1、Table 3、
Figure 1--3、Abstract、Introduction 或 Conclusion。4.2 继续保持
`SECTION4_4_2_FROZEN`，本轮没有重新打开。

---

## 9. 编译与 PDF 只读检查

当前构建状态：

- PDF：`paper/main.pdf`；
- 总页数：9；
- 文件大小：10,365,026 bytes；
- LaTeX errors：0；
- undefined references：0；
- undefined citations：0；
- multiply-defined labels：0；
- overfull hboxes/vboxes：0；
- underfull hboxes：7；
- underfull vboxes：0。

普通 underfull 没有发生在 4.3 结果段或 Table 2 上，也没有造成裁切或阅读顺序
破坏，因此不升级为问题。

`main.aux` 中：

- `tab:q2` 正常解析为 Table 2；
- Table 2 位于 PDF 第 7 页；
- `tab:forecast`、`fig:behavior` 和 `tab:q3` 引用也均正常解析。

PDF 文本与几何检查确认：

- 4.3 标题、首句和五句结果解释均完整；
- Table 2 表体、caption 和 paired \(n\) 均可提取；
- 表格未裁切、未越界、未与相邻 Figure 3 重叠；
- caption 位于表体之后；
- 双栏阅读顺序可接受。

**编译与 PDF：PASS。**

---

## 10. 质量评分

评分标准：1=明显不达标；3=基本可用；4=投稿成熟；5=高度成熟。

| 维度 | 分数 | 判断 |
|---|---:|---|
| AAAI 结果结构 | **4.9** | 完整遵循结论—证据—解释—边界链 |
| 首句力度 | **4.9** | 直接回答 Q2，并同时声明主辅层级 |
| Primary/supporting 层级 | **5.0** | 正文、表格 caption 和 caveat 完全一致 |
| 统计表达 | **5.0** | 两种 estimand、CI、\(n\) 和方向均清楚 |
| 世界模型主线 | **4.9** | Q2 定义性证据地位明确，不替代 Q1/Q3 |
| Claim--evidence 对齐 | **5.0** | 无必要性、因果性、完整状态或 split 比较越界 |
| 英文自然度 | **4.8** | 专业紧凑，无工程日志或宣传语气 |
| 简洁度 | **4.8** | 约 135 词，六句职责互不重复 |
| Table 2 与正文分工 | **4.8** | 表给 exact values，正文给证据顺序和科学意义 |
| 中英文一致性 | **5.0** | 四份文本的数字、顺序与主张强度一致 |
| 与冻结 4.1/4.2 质量一致性 | **4.8** | 达到相同段落纯度和审稿人可读性 |
| **平均分** | **4.9 / 5.0** | **达到冻结标准** |

---

## 11. Critical / Major / Minor

### Critical（0）

未发现。

### Major（0）

未发现。

### Minor（0）

修改前审计提出的结论位置、证据顺序、paired \(n\) 和简版镜像四项 Minor 均已
关闭。当前没有需要在冻结前继续修改的局部写作或格式问题。

---

## 12. 冻结判断

当前 4.3 满足全部冻结条件：

- Critical = 0；
- Major = 0；
- 平均分 \(4.9\ge4.0\)；
- 所有 Q2 数值与冻结 JSON 一致；
- paired 与 official estimand 没有混淆；
- 两个 primary paired CI 均排除零；
- state removal / \(T\to I\) 主辅层级稳定；
- 主张没有越界；
- 四份文本和六列 Table 2 同步；
- 修订日志中的冻结区块 SHA 全部保持；
- 编译和 PDF 无阻塞。

因此最终状态为：

# SECTION4_4_3_FROZEN

后续不得借 4.4、图表或全篇排版修改重新打开 4.3 的 Q2 数值、estimand、主辅证据
层级、load-bearing 定义或 4.1/4.2 的冻结事实。
