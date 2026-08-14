# TerraState 3.3 `Future-Anchored State Learning`：AAAI 前置审计

> 日期：2026-07-28  
> 审计对象：`paper/main.tex:316–379` 中
> `\subsection{Future-Anchored State Learning}`，并以
> `MANUSCRIPT_ZH_FULL.md:172–227` 检查中文镜像  
> 审计状态：**WAIT_FOR_3_2_FREEZE**  
> 审计模式：只读；除本报告外，未修改英文正文、中文稿、Figure 2、PDF、代码或结果  
> 事实优先级：冻结 checkpoint 与选择记录 > 实际训练代码 > 冻结方法规范 >
> 当前正文/中文稿 > 写作锚点  
> 代码基线：`WorldModel2026-planb-v2train` commit
> `52578ca4b1c0b434b10707cf052a623f0c4e4a99`，审计时工作树无改动

## 1. 总体判定

**REVISE，且在 3.2 冻结前保持 WAIT。**

当前 3.3 的三模型身份、future-state target、patch mask、cosine loss、三项总损失和
selected-checkpoint 冻结事实总体正确，已经从早期的概念性说明推进到可审计的方法
描述。它不需要改变模型、训练目标或实验结果，也不需要推倒重写。

但目前仍有三个 AAAI 方法写作层面的主要问题：

1. **GT 与 KD 只有文字描述，没有与 future-state loss 平行的公式。** 两者采用不同
   聚合方式：GT 是逐像素、沿时间归一化后再对植被/预测有效像素平均；KD 是所有
   clear-vegetation time–pixel elements 的全局 masked mean。只用文字容易让审稿人
   把二者误读为同一种 masked MSE。
2. **“does not expose future observations to the student”表述过强。** Future EO
   确实不作为 student forward 或 inference 的输入，但它通过冻结 target 产生
   supervision，并通过 \(\mathcal L_{\rm FS}\) 的梯度训练 student。这是合法的
   future-label supervision，不是信息泄漏；正文必须精确区分“训练目标”与
   “student/inference input”。
3. **核心学习机制与实验运行记录混在同一末段。** 总损失和“target/teacher 仅训练
   时存在”属于 Method；40 epochs、14,880 updates、分段调度、partial unfreezing
   和 checkpoint selection 属于 Section 4 的 Implementation / Model Selection。
   当前末段虽已正确区分完整计划与 selected boundary checkpoint，但会削弱 3.3 的
   方法中心。

### 1.1 各维度评分

| 维度 | 分数（1–5） | 判定依据 |
|---|---:|---|
| AAAI 训练目标小节成熟度 | 3 | 三类信号角色清楚，但 GT/KD 缺少平行公式，末段混入运行日志 |
| 三种模型身份清晰度 | 4 | student、独立 KD teacher、training-start target copy 已分开；student 的完整 warm-start 身份仍未写 |
| 输入与信息边界 | 4 | teacher 不见 future EO、target 不见 future weather、两者不进入 inference 均正确；“complete EO”与“does not expose”需精确化 |
| 损失可复现性 | 3 | FS 公式、mask、总权重完整；GT/KD 的 mask 与聚合仅用文字表达 |
| 表示学习叙事 | 4 | terminal transitioned state 与 observed-future representation 的关系明确，且没有把 FS loss 当成 load-bearing 证据 |
| 代码一致性 | 4 | 当前公式和主要事实与冻结代码一致；target 的 all-frame encode/terminal-token 机制尚未在符号中完全展开 |
| 训练/推理分离 | 4 | teacher、cache、future observation 均声明为 training-only；还需把“监督可见”与“前向不可见”分开表述 |
| Method / Experiments 边界 | 3 | 完整 curriculum、update 数和 checkpoint 选择应下沉 Section 4 |
| 主张安全性 | 4 | 已明确 FS anchor 不证明 load-bearing；没有因果、完整物理状态或 non-collapse 强主张 |
| 英文自然度与论证流 | 3 | 可读，但首段偏身份清单、末段偏审计日志；缺少“目的→平行目标→表示锚定→边界”的完整节奏 |
| 中文镜像一致性 | 4 | `MANUSCRIPT_ZH_FULL.md` 与英文基本同步，问题也同步存在 |
| 与 3.1 的整体质量一致性 | 3 | 技术密度足够，但尚未达到 3.1 的形式化完整性和段落纯度 |

**综合判断：3.6/5。** 事实基础接近 PASS，写作组织仍为 REVISE。

## 2. 逐段问题、严重度与最小修改计划

严重度定义：

- **BLOCKER**：事实错误或信息泄漏风险，冻结前必须解决；
- **MAJOR**：影响方法理解、可复现性或章节边界；
- **MINOR**：不改变技术事实，但影响精确性、自然度或篇章效率；
- **NONE**：可直接保留。

| 当前段落 | 已完成的功能 | 问题 | 严重度 | 最小修改计划 |
|---|---|---|---|---|
| P1，`main.tex:318–325`，三种身份 | 正确区分 trainable student、独立 frozen KD teacher 与 training-start frozen target encoder；明确两个冻结分支不进入 inference | 没有说明 student 是从 `ObsWorldB4Exclusive` forecasting precursor **全模型精确 warm-start**，容易被理解为只复制/初始化 \(q_\theta\)；teacher 的“完整未来天气但无 future EO”正确；target 的“complete EO”可能被误读为无云真值，而实际是保留真实 EO 和 mask，cloudy token 仍被 mask | MAJOR | 在不增加 checkpoint 路径的前提下补一句 student 的完整 warm-start 身份；把 target 输入写成“the observed EO sequence with its masks, including future frames”；保留一次 training-only/inference-discard 声明 |
| P1 末句，`Neither frozen branch enters student inference` | 给出必要的信息边界 | 与 P4 的 `We discard both frozen branches after training` 轻度重复 | MINOR | 两句保留其一作为本节最终 inference 边界；另一处压缩，避免防御式重复 |
| P2，`main.tex:327–335`，GT/KD 文字定义 | 正确指出 GT 与 KD 的聚合不同，也正确解释二者用途 | 没有公式、符号或 mask 定义；“preserves true NDVI prediction / teacher behavior”更像经验结果，宜写为“trains against ground truth / regularizes toward the teacher” | MAJOR | 用一个紧凑公式块平行定义 \(c_{bhp},v_{bp},a_{bp}\)、\(\mathcal L_{\rm GT}\) 与 \(\mathcal L_{\rm KD}\)；公式后用一句解释 aggregation difference |
| P2 的 GT 聚合 | 基本符合 vendored loss：先按 pixel 对 clear horizons 做时间归一化，再对 vegetation/prediction-valid pixels 平均 | 应明确 \(a_{bp}\) 是 prediction-mask validity，而不是 cloud validity；代码对没有 clear horizon 的像素产生零 numerator/epsilon-normalized 项，但外层 denominator 由 vegetation × prediction-valid mask 决定，不能改写成简单 global valid-element MSE | MAJOR | 直接采用代码同构的两层公式，不增加“只对至少一个 clear horizon 的像素平均”这一代码中不存在的条件 |
| P2 的 KD 聚合 | 正确描述为 global masked mean | 应明确 teacher prediction stop-gradient，mask 为 clear × vegetation，不使用 GT 的逐像素时间归一化，也不使用 prediction mask \(a_{bp}\) | MAJOR | 给出全局分子/分母公式，并在公式中写 \(\operatorname{sg}(\widehat y^{\rm tea})\) |
| P3 开头，`main.tex:337–341`，target input | 正确说明 FS anchor 的目的，并写出 complete EO/mask、past weather、static geography、future-weather zeroing | `complete EO` 语义略宽；还未明确只缓存 terminal \(H=20\) target，不监督中间 horizon | MINOR | 改成 observed all-frame EO sequence with recorded masks；补“only the terminal target is formed/cached” |
| P3 target 公式，`main.tex:342–357` | 正确给出 training-start frozen \((\theta^0,\rho^0)\)、stop-gradient、terminal patch target 与 cosine alignment | 早先 \(q_\theta\) 被定义为产生 \(b_{1:H}\) 和历史 token \(e_t\)，此处直接写 \(q_{\theta^0}(\mathcal C^*)_{t+H,i}\) 会让读者不清楚 target branch 使用 all-frames-visible encode 并取 terminal hidden token，而不是用 forecast output | MAJOR | 在公式前后增加一句：target copy runs the same encoder with all EO frames visible, then selects the terminal spatial token before \(P_{\rho^0}\)；不展开工程 API 名称 |
| P3 的 LN-cosine 与聚合 | 与代码一致：student/target 两侧均 LN，按有效 patch 做 \(1-\cos\) masked mean | \(i\) 最好说明跨 batch 的 terminal spatial patches；\(\epsilon\) 数值无需 Method 展开 | MINOR | 保留公式，只补 index scope；数值 \(\epsilon=10^{-6}\) 留复现说明或附录 |
| P3 patch mask，`main.tex:357–360` | 已准确写出 terminal \(4\times4\) patch 必须 fully clear 且至少一个 vegetation pixel | “fully clear”应保持为“patch 内没有任何 `dynamic_mask>0`”；不能降级为“至少一个 clear vegetation pixel” | NONE | 原则上原句可保留；如修改，只增强与 token visibility 的因果解释，不改规则 |
| P3 末句，`does not expose future observations to the student` | 试图排除 future EO leakage | 过度绝对。Future EO 通过 target loss 合法地监督 student，只是不进入 student forward/inference；若保持原句，审稿人可能指出语义矛盾 | **MAJOR** | 改为“Future EO is used only to construct a stopped training target; it is never an input to the student forecast or inference graph.” |
| P4 总损失，`main.tex:363–370` | 三项权重正确，且只含 GT、KD、FS | \(\lambda_s\) 的角色可用一句话解释；不应引入其他 inherited loss | NONE | 保留总式和固定 \(0.5\) KD 权重；明确不存在 composition/VICReg/intervention training objective，但不必用防御式长清单 |
| P4 curriculum，`main.tex:371–374` | 数字和分段正确描述完整候选训练计划 | 属于 Implementation；放在 3.3 会让核心表示学习机制被 update 日志淹没 | MAJOR | 整段移至 Section 4；Method 最多保留“\(\lambda_s\) is scheduled during training”或完全交给 Implementation |
| P4 checkpoint selection，`main.tex:374–377` | 正确说明 selection 在查看 Q2/Q3 前完成，selected checkpoint 位于 partial unfreezing 前，\(q\) 在其 realized path 始终冻结 | checkpoint selection 不是学习机制；正文还应明确 selected step 是 11,904/14,880，且未经历最后 20%，但该精确信息应集中在 Section 4 | MAJOR | 移至 Section 4 的 Data and Model Selection / Implementation；与现有 Section 4 句子合并，避免两处重复 |
| P4 末句，`main.tex:378–379` | 正确说明两个冻结分支训练后丢弃；正确区分 FS learning signal 与 Q2 load-bearing evidence | 两个独立信息点可以成为本节有力结尾，但现在夹在 curriculum 后面 | MINOR | 将其提前/重组为本节最后两句：training-only branches are discarded；FS alignment alone does not establish load-bearing use |

### 2.1 最小段落重组

在 3.2 冻结后，3.3 只需重组为四个短段，不改变任何方法事实：

1. **Training identities and purpose**：student、KD teacher、future-state target encoder；
2. **Forecast objectives**：平行定义 GT/KD 的 mask、公式和不同聚合；
3. **Future-state representation target**：target input、冻结身份、terminal token、
   patch mask、cosine loss；
4. **Total objective and inference boundary**：总损失、teacher/target 丢弃、FS 不替代
   Q2 证据。

完整 schedule、update 数、解冻阶段和 checkpoint selection 全部下沉 Section 4。

## 3. AAAI 训练目标 / 表示学习写作锚点映射

以下锚点只用于**组织方式**，不作为 TerraState 技术事实或效果证据。

| AAAI 写作锚点 | 可借鉴的写法 | 3.3 对应内容 | 应避免照搬的技术主张 |
|---|---|---|---|
| [Unlocking Efficient Vehicle Dynamics Modeling via Analytic World Models, AAAI 2026](https://ojs.aaai.org/index.php/AAAI/article/view/39629) | 先列清 notation/strategy，再为每个任务明确输入、预测量和监督量 | 用身份表明确 student、teacher、target encoder；用损失表明确谁产生 \(\widehat y\)、\(\widehat y^{\rm tea}\)、\(z^*\)，谁接收梯度 | analytic dynamics、车辆动力学先验及其效率结论 |
| [Modeling Latent Non-Linear Dynamical System over Time Series, AAAI 2025](https://ojs.aaai.org/index.php/AAAI/article/view/33269) | 分开 latent state、observable 和学习目标，状态方程与观测方程先于 objective | 将 \(z_{t+H}\) 的表示对齐与 \(\widehat y\) 的 GT/KD 预测监督分开；说明 FS 是 latent target，GT/KD 是 observable forecast targets | 概率生成模型、可识别性或一般非线性动力系统结论 |
| [SparseWorld, AAAI 2026](https://ojs.aaai.org/index.php/AAAI/article/view/37347) | 核心模块先按问题→机制展开，训练策略最后出现 | 3.3 先解释三种 objective 各自解决什么，再给公式；curriculum 只在机制之后简述或下沉 Section 4 | 自动驾驶 sparse query、自回归世界模型和规划能力 |
| [WorldAgen, AAAI 2026](https://ojs.aaai.org/index.php/AAAI/article/view/38925) | Task formulation 与 world modeling / action learning / test-time path 分层 | 把 training-only teacher/target 与 student inference chain 明确拆开，避免让训练支路看似 test-time module | action prediction、test-time adaptation 或 agent 能力 |
| [Learning Hybrid Dynamics Models with Simulator-Informed Latent States, AAAI 2024](https://ojs.aaai.org/index.php/AAAI/article/view/29075) | Problem setting 与 method 分开；latent contribution 和 observable equation 清楚分层 | FS 对齐只塑造 transitioned state；最终预测仍由 \(b_h+r_h\) 定义；“state 是否有用”由 Q2 而非 alignment loss 判断 | simulator-informed state、物理保证、observer 收敛 |

从这些锚点抽出的 3.3 写作原则是：

1. 每个监督信号必须同时回答**来源、可见信息、目标张量、mask、聚合和梯度去向**；
2. training-only branch 与 inference branch 必须在文字中分离，不能只靠 Figure 1；
3. 表示对齐是训练机制，不是表示已经 load-bearing、non-collapsed 或 physically correct
   的结果证据；
4. 精确复现信息应存在，但 optimizer、GPU、update count 和 checkpoint selection 不应
   打断核心 objective 的论证流。

## 4. 三种模型身份、输入、冻结状态与推理时去向

| 身份 | 初始化/来源 | 实际输入与不可见信息 | 训练时冻结状态与梯度 | 推理时去向 | 代码/冻结依据 |
|---|---|---|---|---|---|
| **TerraState student** | 从允许的 `ObsWorldB4Exclusive` forecasting precursor 完整 state dict 精确 warm-start；不是只初始化 \(q_\theta\)，也不是 raw Phase-I B4 直接建新分支 | \(q_\theta/P_\rho\) 只使用历史 EO、历史 mask、过去天气和静态地理；future EO 与 future weather 在 history pass 清除。\(T_\psi\) 合法读取 future weather、static geography 和 horizon。GT、teacher tensor、\(z^*\) 只用于 loss，不作为 forecast 输入 | student 的 projector/transition/readout 等分支训练；完整计划前 80% 冻结 \(q_\theta\)，最后 20% 计划只解冻最后 block。Q1–Q3 所用 boundary checkpoint 在 80% 边界保存，因此其 realized path 中 \(q_\theta\) 始终冻结 | **保留**；正式 inference 只运行 student 的 \(q\to P\to T\to O\) 路径 | `models/terrastate_v2.py:38–73,123–127,170–191`；`train/train_terrastate_v2.py:248–258,276–309`；`selection_record.json:9–21` |
| **Frozen KD teacher** | 独立 Phase-I full-weather B4 checkpoint 的 `q.*`，精确加载为 `PVTContextformerQ`；不是 student 自蒸馏，也不是 future-state target encoder | 读取历史 EO/mask、过去天气、静态地理和完整 future weather；预测窗口的 future EO image tokens 被 mask，因此不读取 future EO | 永久 `eval`、所有参数 `requires_grad=False`；trainer 在 `no_grad` 中生成 \(\widehat y^{\rm tea}\)，student loss 对 teacher prediction 使用 stop-gradient | **丢弃**；不序列化为 student inference module，不进入 `model(data)` | `train/train_terrastate_v2.py:124–141,260–274,403–412,482`；`models/terrastate_v2.py:76–108,123–127` |
| **Frozen future-state target encoder** | 训练开始时深拷贝 student 初始 \(q_{\theta^0}\) 与 \(P_{\rho^0}\)；其 SHA 必须与 cache provenance 及 trainer 初始 pair SHA 一致；与 KD teacher 不是同一网络或 checkpoint | 保留真实的 all-frame EO 与记录的 masks，包括 future EO；保留过去天气和 static geography；future weather 显式置零。Land-cover 只参与 patch validity。使用 all-frames-visible encode，取 terminal spatial token 后经 \(P_{\rho^0}\) 得到 \(z^*_{t+H}\) | 永久 `eval`、`no_grad`、参数冻结；离线生成只读 FP16 cache，训练时以普通 tensor \(z^*\) 和 bool patch mask 传入；target 在 loss 中再次 detach | **丢弃**；inference 不构造 encoder、不读 cache、不接收 \(z^*\) | `train/terrastate_future_state_cache.py:33–78,92–112,163–248,306–313`；`scripts/build_future_state_cache.py:84–106`；`models/terrastate_v2.py:111–127` |

### 4.1 必须保持的身份区分

- **KD teacher** 提供的是可观测预测 \(\widehat y^{\rm tea}_{1:H}\)，作用于
  \(\mathcal L_{\rm KD}\)。
- **Future-state target encoder** 提供的是 terminal latent target
  \(z^*_{t+H}\)，作用于 \(\mathcal L_{\rm FS}\)。
- 两者来源不同、输入权限不同、输出空间不同，不能统称为一个 “frozen encoder”。
- Student 的 \(q_\theta\) 即使在 selected checkpoint 的 realized path 中冻结，
  student 也不是“全冻结模型”；\(P_\rho,T_\psi,O_\omega\) 等分支仍被优化。

## 5. GT、KD 与 future-state loss：公式、mask、聚合、权重及代码依据

### 5.1 统一记号

令 \(b\) 为 minicube，\(h\in\{1,\ldots,H\}\) 为预测时距，\(p\) 为 raster
pixel，\(i\) 为 batch 内 terminal spatial patch：

- \(\widehat y_{bhp}\)：student 最终 NDVI forecast；
- \(y_{bhp}\)：真实 NDVI；
- \(\widehat y^{\rm tea}_{bhp}\)：冻结 full-weather KD teacher forecast；
- \(c_{bhp}=\mathbf 1[\texttt{dynamic\_mask}_{bhp}<1]\)：clear mask；
- \(v_{bp}=\mathbf 1[10\leq\text{landcover}_{bp}\leq40]\)：vegetation mask；
- \(a_{bp}=\max_h\mathbf 1[\widehat y_{bhp}\neq-1]\)：prediction-valid mask；
- \(m_i\)：terminal patch validity。

### 5.2 Ground-truth loss

代码先对每个 pixel 沿时间做 clear-mask 归一化：

\[
\bar\ell^{\rm GT}_{bp}
=
\frac{\sum_{h=1}^{H}c_{bhp}
\left(\widehat y_{bhp}-y_{bhp}\right)^2}
{\sum_{h=1}^{H}c_{bhp}+\epsilon_{\rm pix}},
\]

再对 vegetation × prediction-valid pixels 平均：

\[
\mathcal L_{\rm GT}
=
\frac{\sum_{b,p}v_{bp}a_{bp}\bar\ell^{\rm GT}_{bp}}
{\sum_{b,p}v_{bp}a_{bp}+\epsilon_{\rm GT}}.
\]

关键点：

- 它不是把所有 clear vegetation time–pixel elements 放进同一个 global mean；
- 每个 pixel 先按自身 clear horizon 数归一化，因此不同 cloud availability 的 pixel
  在外层平均中获得相同 pixel-level 权重；
- 当前代码的 \(\epsilon_{\rm pix}=\epsilon_{\rm GT}=10^{-8}\)；
- 当前正文 P2 的文字方向正确，但公式缺失。

代码依据：

- `models/plan_b_b4.py:161–167`：实例化实际 NDVI loss，land-cover 范围
  \([10,40]\)、prediction mask value \(-1\)；
- `models/losses/masked_l2_ndvi.py:51–70`：clear mask、target/prediction slicing、
  per-pixel temporal normalization；
- `models/losses/masked_l2_ndvi.py:87–95`：vegetation/prediction-valid 外层平均；
- `models/terrastate_v2.py:89–101`：正式 V2 total loss 调用该 GT loss。

### 5.3 KD loss

令 \(M_{bhp}=c_{bhp}v_{bp}\)，则：

\[
\mathcal L_{\rm KD}
=
\frac{
\sum_{b,h,p}M_{bhp}
\left(
\widehat y_{bhp}
-\operatorname{sg}\!\left[\widehat y^{\rm tea}_{bhp}\right]
\right)^2
}{
\sum_{b,h,p}M_{bhp}+\epsilon_{\rm KD}
}.
\]

关键点：

- KD 是所有 clear vegetation time–pixel elements 的**全局 masked mean**；
- 它不采用 GT 的 per-pixel time normalization；
- 它不使用 GT 的 prediction-valid mask \(a_{bp}\)；
- teacher output 被 detach，teacher 本身也在 `no_grad` 中计算；
- 当前 \(\epsilon_{\rm KD}=10^{-8}\)。

代码依据：

- `models/terrastate_v2.py:89–101`：clear × vegetation mask、global numerator /
  denominator、固定 KD 权重；
- `train/train_terrastate_v2.py:124–141`：teacher 的独立来源与永久冻结；
- `train/train_terrastate_v2.py:403–412`：trainer 在 `no_grad` 中生成 teacher
  prediction 并传给 student loss。

### 5.4 Future-state loss

Target encoder 输入为：

\[
\mathcal C^*_{t+H}
=
\left(
x_{1:C+H},m_{1:C+H},
u^{\rm past}_{1:C},0_{C+1:C+H},g
\right),
\]

其中 future EO 保留为训练 target 所需的真实观测，future weather 显式置零。冻结
target copy 使用 all-frames-visible encode，并取 terminal spatial token：

\[
z^*_{t+H,i}
=
\operatorname{sg}\!\left[
P_{\rho^0}
\left(
q_{\theta^0}(\mathcal C^*_{t+H})_{t+H,i}
\right)
\right].
\]

逐 patch loss 与 masked aggregation 为：

\[
\ell_i^{\rm FS}
=
1-\cos\!\left(
\operatorname{LN}(z_{t+H,i}),
\operatorname{LN}(z^*_{t+H,i})
\right),
\]

\[
\mathcal L_{\rm FS}
=
\frac{\sum_i m_i\ell_i^{\rm FS}}
{\sum_i m_i+\epsilon_{\rm FS}}.
\]

Patch mask 的精确规则是：

\[
m_i=1
\iff
\begin{cases}
\text{terminal }4\times4\text{ patch 内没有任何 }
\texttt{dynamic\_mask}>0,\\
\text{该 patch 至少包含一个 land-cover }\in[10,40]\text{ 的 pixel}.
\end{cases}
\]

这条规则对应 ContextFormer token visibility：只要 patch 中任一 pixel 被 cloud mask，
该 image token 就会被替换为 mask token。因此不能把它改成“patch 中至少有一个 clear
vegetation pixel”。当前 \(\epsilon_{\rm FS}=10^{-6}\)。

代码依据：

- `train/terrastate_future_state_cache.py:41–78`：training-start deep copy、
  future-weather zeroing、all-frame encode 与 terminal token；
- `train/terrastate_future_state_cache.py:92–112`：fully-clear × contains-vegetation
  patch mask；
- `train/terrastate_future_state_cache.py:180–240`：terminal target/mask cache 与
  provenance；
- `models/terrastate_v2.py:110–120`：两侧 LN、cosine distance、masked mean。

### 5.5 总损失与权重

\[
\boxed{
\mathcal L
=1.0\,\mathcal L_{\rm GT}
+0.5\,\mathcal L_{\rm KD}
+\lambda_s\,\mathcal L_{\rm FS}
}
\]

固定事实：

- GT 权重为 \(1.0\)；
- KD 权重为 \(0.5\)；
- \(\lambda_s\) 在完整候选训练计划中按
  \(0\to0.02\)（0–20%）、\(0.02\)（20–80%）、\(0.01\)（80–100%）调度；
- 正式 V2 训练没有第二个 KD，也没有 composition、VICReg、
  driver-intervention distillation 或 Q2/Q3 intervention loss；
- Q1–Q3 selected checkpoint 位于 step 11,904，即 80% 边界，未经历
  \(\lambda_s=0.01\) 的最后阶段。

代码/冻结依据：

- `models/terrastate_v2.py:43–45,76–108`；
- `train/train_terrastate_v2.py:55–85,294–309,403–447`；
- `evidence_workspace/raw/release/selection_record.json:9–21,43–72`。

## 6. Future-state target 是否造成未来信息泄漏

### 6.1 判定

**不会造成推理时未来信息泄漏，但它确实使用 future EO 构造训练监督。**

两者必须同时写清：

- “使用 future EO 作为训练 target”是监督学习设计；
- “future EO 进入 student forward 或 test-time inference”才是本任务要排除的
  leakage。

### 6.2 为什么不会泄漏到 student inference

1. **Student forecast path 不读取 future EO。** History pass 会清除 future EO，
   future weather 只进入 transition。代码还提供了 future-EO perturbation
   invariance guard：改变 future EO 不应改变 forecast。
2. **Target encoder 是独立冻结副本。** 它永久 `eval/no_grad`，只为训练样本离线
   产生 \(z^*\)；student 不共享其更新后的权重，也不在 inference 时调用它。
3. **Cache 与 inference API 隔离。** Trainer 根据 filepath 读取 cache，并把
   \(z^*\) 和 mask 作为 loss tensor 传入；`model(data)` 在
   `teacher_pred is None` 时直接走 `forecast(data)`，不访问 teacher、target
   encoder 或 cache。
4. **Stop-gradient 方向正确。** 梯度从 \(\mathcal L_{\rm FS}\) 回到 student 的
   \(z_{t+H}\) 路径，但不会更新 \(z^*\) 或 target encoder。这是“用未来标签训练
   当前模型”，不是“让模型在预测时读取未来标签”。
5. **Target 的 future weather 被置零。** 这避免 \(z^*\) 通过未来天气形成另一个
   weather shortcut，使 target 更接近 observed-future representation。它不是排除
   future-EO leakage 的唯一理由；真正的无泄漏依据仍是 target branch 与 student
   inference graph 的结构隔离。
6. **只为 train/validation 构造训练与选择所需 target。** OOD-t future EO 不用于
   训练或 checkpoint selection；selected checkpoint 在 OOD-t 评测前冻结。

### 6.3 当前正文应避免的两种错误说法

- 不写“the student never sees future observations”而不加限定，因为 student
  的 loss 确实接收由 future observations 构造的监督；
- 不写“future-state supervision proves no leakage / proves a predictive state”。
  无泄漏由 forward/API 边界证明；predictive state 是否 load-bearing 由 Q2 的
  post-training intervention 证明。

推荐的事实强度是：

> Future EO is used only to construct a stopped, training-only target. It is
> never an input to the student forecast or the inference graph.

## 7. 核心方法与应移至 Section 4 的内容

| 内容 | 归属 | 理由 |
|---|---|---|
| 三种模型身份及其信息权限 | **3.3 核心方法** | 决定训练监督与 inference 的边界 |
| Student 沿正式 \(q\to P\to T\to O\) 路径产生 \(\widehat y,z_{t+H}\) | **3.3 核心方法** | 说明 loss 作用于哪条可部署路径 |
| GT/KD/FS 的目的、公式、mask 与聚合差异 | **3.3 核心方法** | 训练目标必须可理解且可复现 |
| Target encoder 是 training-start frozen \(q/P\) copy | **3.3 核心方法** | 决定 representation target 的语义 |
| Target 保留 future EO、future weather 置零、只取 terminal \(H=20\) | **3.3 核心方法** | 决定监督信息与 horizon |
| Fully-clear × contains-vegetation patch mask | **3.3 核心方法** | 决定哪些 latent patches接收监督 |
| \(\mathcal L=\mathcal L_{\rm GT}+0.5\mathcal L_{\rm KD}+\lambda_s\mathcal L_{\rm FS}\) | **3.3 核心方法** | 唯一正式训练目标 |
| Teacher/target 在训练后丢弃；FS 不替代 Q2 | **3.3 核心方法边界** | 防止误读 deployment cost 与 evidence |
| 40 epochs、372 updates/epoch、14,880 total updates | **移至 Section 4** | 运行配置，不是表示学习机制 |
| 0–20% / 20–80% / 80–100% 的精确 step 区间 | **移至 Section 4** | curriculum 实现细节 |
| \(\lambda_s\) 的精确分段数值 | **Section 4 为主**；3.3 最多一句引用 | 权重调度影响复现，但不应打断目标定义 |
| Last \(q\) block 的 partial unfreezing 与 \(q\)-LR | **移至 Section 4** | optimizer/freeze schedule |
| AdamW、warmup、cosine、batch、gradient clipping | **Section 4** | 标准 Implementation 信息 |
| Preregistered candidate set 与 validation-only fallback rule | **Section 4 Model Selection** | 属于实验选择协议 |
| selected `boundary80`、step 11,904、stage 2、SHA | **Section 4 / reproducibility record** | checkpoint-specific evidence |
| “selected checkpoint 的 \(q\) 在 realized path 始终冻结” | **Section 4 必须明确**；3.3 可不重复 | 防止把完整候选计划错写成最终证据模型经历 |

建议 3.3 不保留完整 curriculum 段；Section 4 已有 Implementation and statistics
位置，可以集中说明：

- 完整候选 run 计划为 14,880 updates；
- selected boundary checkpoint 在 update 11,904、stage 3 之前保存；
- 所报告模型未经历最后 20% partial unfreezing 或 \(\lambda_s=0.01\)；
- selection 仅使用 validation forecast performance，Q2/Q3 与 OOD-t 不参与。

## 8. 与尚未冻结 3.2 的依赖

当前 3.3 不应先行改写或冻结，原因不是其 loss 事实不确定，而是以下接口仍依赖 3.2：

1. **Student inference chain 的文字接口。** 3.3 首句说 student “follows the
   inference chain above”；只有 3.2 的 \(q_\theta,P_\rho,T_\psi,O_\omega\) 定义和
   模块边界冻结后，这个指代才稳定。
2. **Target copy 的模块身份。** Future-state encoder 是 training-start student
   \(q_\theta/P_\rho\) 的冻结 copy。3.2 必须先决定 warm-start 事实放在 3.2 还是
   3.3，避免两节重复或遗漏。依据 3.2 审计，完整 warm-start 身份应移入 3.3 或
   Section 4，而不应继续留在架构段。
3. **\(q_\theta\) 输出记号。** 3.2 当前把 \(q_\theta\) 描述为输出 context
   forecast 和历史 tokens；3.3 target branch 又需要 all-frame terminal token。
   3.2 冻结后，3.3 必须用一句局部说明 target-mode terminal token，不能静默改变
   \(q_\theta\) 的主推理定义。
4. **State tensor 的空间语义。** 3.3 的 patch index \(i\)、\(4\times4\) mask 和
   \(z_{t+H,i}\) 依赖 3.2 明确 token ↔ spatial patch 的对应关系。
5. **Transition condition 的技术修正。** 3.2 尚需修正
   \(c_h\) “shared across spatial tokens”的错误：地理条件逐 patch，只有参数共享。
   这不改变 \(\mathcal L_{\rm FS}\)，但会改变 3.3 所说 student
   \(z_{t+H}\) 的准确生成描述。
6. **章节交接。** 3.2 应只描述 inference architecture，teacher/target 的详细身份
   移入 3.3。只有这一边界执行后，3.3 开场才不会与 3.2 重复。
7. **Figure 2 不构成 3.3 的先决技术证据。** 3.3 的 teacher/target 主要由
   Figure 1 和公式承担；本轮保持 Figure 2 不动。待 3.2 冻结后再统一检查图文边界。

因此当前正确状态是：

**3.3 审计结论可保存，但正文修订与冻结必须等待 3.2 的符号、模块和章节边界冻结。**

## 9. KEEP / REWRITE / MOVE / DELETE 清单

### 9.1 KEEP

- 小节标题 `Future-Anchored State Learning`；
- student / KD teacher / future-state target encoder 三身份框架；
- KD teacher 读取完整 future weather、但不读取 future EO；
- target encoder 是 training-start frozen \(q_{\theta^0}/P_{\rho^0}\) copy；
- target 输入保留 future EO、future weather 置零；
- 只监督 terminal \(z_{t+H}\)；
- 双侧 LN 后的 \(1-\cos\) future-state loss；
- terminal \(4\times4\) patch fully clear 且至少一个 vegetation pixel 的 mask；
- 三项总损失及 \(1.0/0.5/\lambda_s\) 权重；
- teacher 与 target encoder 不进入 inference、训练后丢弃；
- “FS anchor 不证明 state load-bearing”，并将 Q2 保持为唯一对应证据。

### 9.2 REWRITE

- P1 补 student 的完整 exact warm-start 身份，避免只像“一个可训练模型”；
- `complete EO` 改为“observed all-frame EO with recorded masks”；
- 为 target branch 补 all-frames-visible encode → terminal token → projector 的
  局部解释；
- 将 GT/KD 的文字描述改成平行公式，显式给出 mask 和不同 aggregation；
- `preserves true NDVI prediction / teacher behavior` 改为训练目的表述，不提前
  当作结果；
- `does not expose future observations to the student` 改成“不作为 student
  forecast/inference input，只构造 stopped training target”；
- 将末段重组为 total objective → discard training-only branches →
  FS-not-Q2-evidence。

### 9.3 MOVE

从 3.2 移入 3.3 或 Section 4：

- student 从 forecasting precursor 完整 exact warm-start 的身份；
- teacher/target 的具体训练期身份与输入权限。

从 3.3 移入 Section 4：

- 40 epochs；
- 14,880 planned updates 与各阶段 update 区间；
- \(\lambda_s\) 的完整 schedule；
- last history block 的 partial unfreezing 与学习率；
- preregistered candidate set、Q1 fallback rule 和 validation-only selection；
- selected boundary checkpoint 的 step/stage/实际冻结路径；
- checkpoint SHA、cache SHA、optimizer、batch、warmup、cosine、gradient clipping 等
  复现记录。

### 9.4 DELETE

这里的 DELETE 指从 3.3 删除或合并，不是从论文证据记录中抹除：

- 删除 P1 与 P4 对“两条冻结支路不进入 inference”的重复表达，只保留一次有力边界；
- 删除/移走“40-epoch schedule contains 14,880 updates”及其后完整运行日志；
- 删除任何把 future EO 描述为“student 完全不可见”的绝对说法；
- 删除任何暗示 \(\mathcal L_{\rm FS}\) 已证明 load-bearing、non-collapse、physical
  correctness 或 causal dynamics 的句子；
- 不加入 inherited precursor 中存在但正式 V2 没有调用的 composition、VICReg、
  intervention-distillation 或额外 KD loss。

## 10. 当前 3.3 是否达到 3.1 的写作质量标准

### 10.1 当前判断

- **是否达到已冻结 3.1 的写作质量标准：否。**
- **是否可以直接冻结：否。**
- **是否存在需要改变代码或实验的技术阻断：否。**
- **是否需要大规模重写：否。**
- **当前动作：WAIT_FOR_3_2_FREEZE。**

### 10.2 与 3.1 的具体差距

已冻结 3.1 的优势是：

- 输入、输出、状态与推理链在一个统一符号系统中定义；
- 每段只承担一个科学功能；
- 方法事实、可检验性质与结果主张分离；
- 公式足以独立于图和工程日志理解。

当前 3.3 尚未达到同一标准，主要因为：

1. GT/KD 不能脱离代码复现其 mask 与聚合；
2. target branch 的 terminal hidden-token 生成方式仍隐含在
   \(q_{\theta^0}(\mathcal C^*)_{t+H,i}\) 中；
3. “不暴露 future observation”没有严格区分 supervision 与 forward input；
4. 核心 objective 与 update/checkpoint 日志混段；
5. student 的完整 warm-start 身份尚未归位；
6. 3.3 的符号与交接仍依赖未冻结的 3.2。

### 10.3 达到 3.1 标准的最小退出条件

3.2 冻结后，3.3 满足以下六项即可从 **REVISE** 收敛为 **PASS**：

1. 补齐 student、KD teacher、target encoder 的来源、输入权限和梯度去向；
2. 给出 GT 与 KD 的平行公式，保留二者不同 aggregation；
3. 明确 target branch 的 all-frame encode、terminal token 和 exact patch mask；
4. 把 future EO 限定为 stopped training target，而非 student/inference input；
5. 只在 3.3 保留核心三项总损失与 evidence boundary，将 schedule/selection 下沉
   Section 4；
6. 保留“FS alignment 不等于 Q2 load-bearing evidence”，不扩大为 non-collapse、
   physical-state 或 causal claim。

完成这些最小修改后，3.3 可达到 3.1 的“形式化完整、段落单一职责、方法与证据分离”
标准，不需要改变模型、loss 权重、训练代码、checkpoint 或任何已报告结果。

## 11. 审计依据索引

### 11.1 当前稿

- `TerraState_AAAI27/paper/main.tex:316–379`
- `TerraState_AAAI27/MANUSCRIPT_ZH_FULL.md:172–227`
- `TerraState_AAAI27/METHOD_3_2_AAAI_AUDIT_20260728.md`

### 11.2 代码

- `WorldModel2026-planb-v2train/models/terrastate_v2.py:38–127,170–191`
- `WorldModel2026-planb-v2train/models/losses/masked_l2_ndvi.py:51–103`
- `WorldModel2026-planb-v2train/train/train_terrastate_v2.py:55–141,152–188,248–309,403–482`
- `WorldModel2026-planb-v2train/train/terrastate_future_state_cache.py:33–112,163–248,306–313`
- `WorldModel2026-planb-v2train/scripts/build_future_state_cache.py:84–106`

### 11.3 冻结方法与 checkpoint 依据

- `TerraState_AAAI27/METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md:165–323`
- `TerraState_AAAI27/evidence_workspace/raw/release/selection_record.json:1–115`
- `TerraState_AAAI27/AUTHOR_NOTES.md:23–31,74–92`
- `TerraState_AAAI27/RESULT_INGESTION_SCHEMA.md:148–152`

---

**冻结状态：WAIT_FOR_3_2_FREEZE**
