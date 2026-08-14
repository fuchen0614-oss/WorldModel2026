# Figure 3 v2 独立证据审核

审计日期：2026-07-28 UTC  
最终判定：**FIG3_V2_EVIDENCE: PASS**

本审计为只读检查。未运行模型、未重新计算置信区间、未修改 Figure 3
脚本/图稿/data trace、正文、冻结 JSON 或 results ledger。

## 1. 冻结权威与审核对象

最高优先级权威：

- `figure_workspace/FIGURE_1_3_FROZEN_PLAN_20260728.md`
- SHA-256：
  `ef7f745bf10d557dc635e8051daa1effb77dbf806d6bccec621bc67800b827a1`

冻结证据：

| 文件 | SHA-256 |
|---|---|
| `evidence_workspace/raw/release/val_q2_state_contract_exclusive.json` | `33b40d3e6bf6e0190c9415a9e0421e9809063356dcba2350890defeeed35f2d9` |
| `evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json` | `7ebc0569d705a9991ac8b8d17c42113c9da052b2bec73f7c28d021e28a65a051` |
| `evidence_workspace/raw/release/q3_extreme_state_audit.json` | `9dae43b9a8a4fcdf0a73ef91daa58c189a88e769541ce295046cd0e938497041` |
| `evidence_workspace/results_ledger.json` | `d1f8ec7d7a51fae87afc8ba9dbc27905c6816434dc5554980d2e7c2eb472c4b2` |

最终审核对象：

| 文件 | SHA-256 |
|---|---|
| `figure_workspace/source/fig3_behavior_v2.py` | `0f9bdd66dc7586347cdf172dbdfc165d584cfaf48e9ac39473cf3404d35f0984` |
| `figure_workspace/export/fig3_behavior_v2.pdf` | `c672faa3e794cfdbb771dcd0d27719a81140ba8fa4d234d51555595abb63ab7b` |
| `figure_workspace/FIG3_V2_DATA_TRACE.md` | `5e80099a9bcc62952e7cf1659e1571bac4962a385cb17f4d54f43201c08f0a6c` |

Data trace 中记录的 authority、evidence 和 candidate-output SHA 与当前文件
逐项一致。

## 2. 十项审核结论

| # | 检查项 | 结论 | 核验依据 |
|---:|---|---|---|
| 1 | Q2 使用 paired mean 及对应 paired 95% CI | **PASS** | 脚本只从 `closure_cut_alpha0.bootstrap95` 和 `transition_identity.bootstrap95` 的同一对象读取 `mean/ci_low/ci_high/n`；未用 official delta 配 CI。 |
| 2 | Validation 与 OOD-t 未交换 | **PASS** | Validation 明确读取 val JSON，OOD-t 明确读取 oodt JSON；图中 Validation 在上、OOD-t 在下，数值与各自 split 一致。 |
| 3 | State removal 为主，\(T\to I\) 仅支持 | **PASS** | State removal 使用较强的实心橙色圆点；\(T\to I\) 使用较小灰色空心菱形，并明确标注 `T→I (support)`。 |
| 4 | Q3 严格使用 84 个 `q3_donor_rows` | **PASS** | 脚本直接读取 `models.exclusive.q3_donor_rows`，硬门检查 `n_pairs=84` 和 `len(rows)=84`。 |
| 5 | 散点坐标字段正确 | **PASS** | 两面板 x 均为 `loss_e_actual`；panel (b) y 为 `loss_e_donor`，panel (c) y 为 `loss_e_mean`。 |
| 6 | \(y>x\) 方向解释正确 | **PASS** | above-diagonal 由 `control loss > actual loss` 计算；因此上方表示 control 更差、actual weather 更忠实。图中 donor 为 56/84，mean 为 69/84。 |
| 7 | 84 对全部使用，无筛选/不利点删除/重复计数 | **PASS** | 84 个 `e_key` 唯一，84 个 `(e_key,c_key)` 唯一，84 个完整 row 唯一；两个 scatter collection 均接收 84 行。45 个 donor 按冻结协议允许复用，不是 pair 重复。 |
| 8 | 两个平均损失差与冻结汇总一致 | **PASS** | 独立逐行重算得到 donor `0.002565468112672014`、mean `0.011261332329706334`，与冻结 endpoint-fidelity summary 精确一致。 |
| 9 | 无越界主张 | **PASS** | 图内文字和 data trace 均未声称因果响应、counterfactual correctness、Q4/composition、extreme-specific enhancement、SOTA 或严格排名。 |
| 10 | 脚本直接读取 JSON，不以手填数值绘图 | **PASS** | Q2 点/CI 和 Q3 全部坐标直接来自三个已做 ledger SHA gate 的 JSON。脚本中的两个冻结均值常数只作二次一致性断言，不参与绘图数据生成。 |

## 3. Q2 原始核对表

### Paired estimand：实际绘图数据

| Split | Intervention | Paired mean \(\Delta R^2\) | Paired-bootstrap 95% CI | n |
|---|---|---:|---:|---:|
| Validation | State removal | 0.01616252595360122 | [0.006432408120151691, 0.02590229577842624] | 589 |
| Validation | \(T\to I\), supporting | 0.017417428921451206 | [0.007824839508750908, 0.026960749441100905] | 589 |
| OOD-t | State removal | 0.021997768589881533 | [0.014219898623411737, 0.03017606928017251] | 1019 |
| OOD-t | \(T\to I\), supporting | 0.024015932710944276 | [0.016086752271438905, 0.032169788967835664] | 1019 |

图中横轴方向为：

\[
\Delta R^2=R^2_{\mathrm{full}}-R^2_{\mathrm{intervention}}.
\]

向右表示干预后的预测能力损失更大。

### Dataset-level official \(\Delta R^2\)：未用于 Figure 3 CI 点

| Split | State removal | \(T\to I\) |
|---|---:|---:|
| Validation | 0.011214424211727803 | 0.011905889808750292 |
| OOD-t | 0.019972010271822827 | 0.021685122441562066 |

这些 official dataset-level 数值与 paired mean 是不同 estimand。脚本没有读取
它们作为 Figure 3 点，因此不存在 official \(\Delta R^2\) 错配 paired CI。

冻结记录同时给出 `transition_margin_clean=false`。当前图用较弱视觉样式和
`support` 标签处理 \(T\to I\)，没有将其升级为定义性或纯净 transition 必要性
证据。

## 4. Q3 84 对完整性与方向

冻结行路径：
`$.models.exclusive.q3_donor_rows`。

| 检查 | 结果 |
|---|---:|
| 冻结行数 | 84 |
| 唯一 `e_key` | 84 |
| 唯一 `(e_key,c_key)` | 84 |
| 唯一完整 row | 84 |
| 唯一 donor/control | 45 |
| 缺失或非有限坐标 | 0 |
| `uf_differs=true` | 84/84 |

坐标与独立重算：

| Panel | x | y | Mean \(y-x\) | \(y>x\) | \(y=x\) | \(y<x\) |
|---|---|---|---:|---:|---:|---:|
| (b) Matched donor | `loss_e_actual` | `loss_e_donor` | 0.002565468112672014 | 56 | 0 | 28 |
| (c) Normalized mean | `loss_e_actual` | `loss_e_mean` | 0.011261332329706334 | 69 | 0 | 15 |

对每一行均验证：

- `dloss_e_donor = loss_e_donor - loss_e_actual`；
- `dloss_e_mean = loss_e_mean - loss_e_actual`。

两条等式的逐行误差均为 0（以冻结浮点值直接核对）。因此 \(y>x\) 只能解释为
control loss 更高、actual weather endpoint fidelity 更好，不能解释为因果响应或
counterfactual correctness。

两条不同的 `e_key` 在两个面板中恰有一组完全相同的数值坐标：
`minicube_86` 与 `minicube_87`。二者具有不同 pair identity，但共享同一 donor，
属于自然散点重叠，不是重复计数或样本删除。脚本仍向每个面板传入全部 84 行。

## 5. 脚本与 provenance 审核

数据流为：

1. 读取 `results_ledger.json`；
2. 从 ledger 取得三个 raw JSON 的冻结 SHA；
3. 对当前三个 raw JSON 重算 SHA 并执行 mismatch hard-fail；
4. 从 Q2 JSON 的 paired-bootstrap 对象读取点和 CI；
5. 从 Q3 JSON 的全部 `q3_donor_rows` 读取三个 loss 字段；
6. 用 84 行计算 \(y-x\)、above-diagonal count，并与 JSON 内冻结汇总做
   `1e-12` 一致性门禁；
7. 将完整数组直接传入 scatter。

没有发现：

- 读取旧 Figure 3 aggregate CSV；
- 手填散点；
- 重新估算或替换置信区间；
- 基于结果方向筛选样本；
- 去除不利点；
- 模型/评测重跑；
- Q4、hot-dry interaction 或无 provenance 定性案例。

`EXPECTED_DONOR_DELTA` 与 `EXPECTED_MEAN_DELTA` 是额外的冻结值断言。实际 plotted
coordinates 和 plotted Q2 estimates/intervals 不由这两个常数提供；即使移除这两个
常数，绘图数据仍完全由 JSON 读取。因此它们不构成手填实验图数。

## 6. 图面与 caption 边界

PDF 目视核对：

- 三个要求的 panel 均存在；
- Validation/OOD-t 标签与数据位置正确；
- Q2 primary/supporting 视觉层级明确；
- Q3 两个 panel 使用相同 `[0,0.12]` x/y 范围和 \(y=x\) 线；
- `56/84`、`69/84` 为代码从冻结行计算的计数；
- 图内没有无来源实验数字；
- 图内没有因果、Q4、extreme-specific enhancement 或 SOTA 表述。

三个要求的审核对象中不包含独立 v2 LaTeX caption。因此本轮 caption 审核覆盖：

- PDF 内标题、轴标签和注释；
- `FIG3_V2_DATA_TRACE.md` 的解释；
- 冻结计划给出的 caption 语义边界。

当前这些内容全部合规。未来正文整合形成的最终 LaTeX caption 仍必须经过单独门禁，
并至少明确：

> In panels (b) and (c), points above \(y=x\) have higher loss under the
> control weather input, so actual weather is more faithful to the observed
> endpoint.

该 caption 不得扩展为因果响应、counterfactual correctness、Q4/composition、
extreme-specific enhancement、SOTA 或严格排名。这是后续正文整合门禁，不是当前
Figure 3 v2 证据阻塞项。

## 7. 最终结论与修复项

**FIG3_V2_EVIDENCE: PASS**

需要修复的 Figure 3 v2 证据问题：**无**。

非阻塞的后续整合检查：正文会话生成最终 caption 后，按第 6 节重新核对方向解释和
主张边界；本证据会话不修改 caption 或正文。
