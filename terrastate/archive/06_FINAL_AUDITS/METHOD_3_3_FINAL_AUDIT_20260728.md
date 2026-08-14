# TerraState §3.3 “Future-Anchored State Learning” 冻结前独立终审

> 审计日期：2026-07-28  
> 审计性质：只读事实、公式、章节边界、双语与现有编译产物终审  
> 审计对象：`paper/main.tex` §3.3 与 `MANUSCRIPT_ZH_FULL.md` 对应中文镜像  
> 唯一写入：本审计报告  
> 事实优先级：冻结 checkpoint/selection provenance > 实际代码 > canonical method spec > 英文正文 > 中文镜像 > 旧审计建议  
> 实现基线：`WorldModel2026-planb-v2train` commit `52578ca4b1c0b434b10707cf052a623f0c4e4a99`

## 1. 最终结论

## PASS_WITH_MINOR

修改后的 §3.3 已经准确区分 TerraState student、冻结的 full-weather KD teacher
和训练开始时冻结的 future-state target encoder，并给出了三项训练目标各自不同的
mask、聚合方式和梯度边界。未来 EO 只构造停止梯度的训练目标，不进入 student
forecast 或 inference graph；KD teacher、target encoder 和 future-state cache
也不进入正式推理。

正文对完整训练协议与当前结果所用 checkpoint 的区别处理正确：

- 完整训练计划为 40 epochs、14,880 updates；
- 完整计划最后 20% 使用 \(\lambda_s=0.01\)，并允许最后一个 history block
  部分解冻；
- Q1–Q3 所用 selected TerraState model 保存于 update 11,904，即 80% 边界；
- 该 selected checkpoint 没有经历后续 \(\lambda_s=0.01\) 或 partial-unfreezing
  阶段，其 history operator 在实际训练路径中始终冻结。

未发现 Critical 或 Major 问题。剩余两项 Minor 分别是：KD teacher 输入列表中
“observation history”可进一步明确为 EO history 加 past weather，以及正文没有解释
四个 \(\epsilon\) 是数值稳定项并给出实现值。这两项不改变方法、公式、梯度、模型身份
或证据边界，不阻塞 §3.3 冻结。

### 问题计数

- Critical：**0**
- Major：**0**
- Minor：**2**

## 2. Critical / Major / Minor 问题表

| 级别 | 位置 | 原文摘要 | 问题 | 代码或 provenance 证据 | 最小修改建议 | 应归属章节 |
|---|---|---|---|---|---|---|
| Critical | — | — | 未发现训练身份、信息边界、损失公式、checkpoint 经历或主张强度方面的阻断错误 | 见第 3–7 节逐项核对 | 无 | — |
| Major | — | — | 未发现影响方法理解、可复现性或投稿主张安全的主要问题 | 旧审计的 GT/KD 公式、future-EO 边界、target mask 和 schedule/selection 混写均已修复 | 无 | — |
| Minor | `main.tex` §3.3 “Training Identities and Purpose”；中文同段 | KD teacher “reads the observation history, static geography, and the complete future-weather sequence” | 结合 §3.1 的术语，`observation history` 可能被窄读为 EO history，未显式列出 teacher 实际也读取 past weather。现有 `full-weather` 身份和上下文使其不构成错误，但输入列表可更无歧义。 | `train/train_terrastate_v2.py` 的 `teacher.encode(data, pred_start=cl, preds_length=tl)` 接收原始历史天气与完整未来天气；`PVTContextformerQ/ContextFormer` 在该调用中屏蔽 future EO image tokens | 后续全篇术语统一时，可改为 “reads the EO history, past weather, static geography, and the complete future-weather sequence, but no future EO”；中文同步加入“过去天气”。不要求为冻结单独改动。 | §3.3 术语统一 |
| Minor | 公式（5）–（6） | \(\epsilon_{\rm pix},\epsilon_{\rm GT},\epsilon_{\rm KD},\epsilon_{\rm FS}\) 出现但未解释 | 读者可将其理解为稳定项，公式逻辑完整；但精确复现信息尚未在正文或 Implementation 中集中给出。 | GT 的前两项和 KD 使用 \(10^{-8}\)：`masked_l2_ndvi.py:69–70,87–93`、`terrastate_v2.py:95–98`；FS 使用 \(10^{-6}\)：`terrastate_v2.py:110–120` | 在复现附录或 Implementation 中统一注明前三项 \(10^{-8}\)、FS \(10^{-6}\)。无需扩写 §3.3，也不影响冻结。 | Section 4 / Reproducibility appendix |

### 2.1 上一轮 Major 问题关闭情况

| 上一轮问题 | 当前状态 | 当前依据 |
|---|---|---|
| Student 的 full-model warm-start 身份缺失 | **CLOSED** | 首段已写 “exact full-model warm start from a forecasting precursor”；与 exact state-dict load 一致 |
| Student、KD teacher、future-state target encoder 混称 | **CLOSED** | 三者来源、输出和推理时去向分别定义 |
| GT/KD 仅有文字且易被误读为同一种 masked MSE | **CLOSED** | 公式（5）明确 GT 两层聚合与 KD global masked mean |
| Teacher prediction 未显式 stop-gradient | **CLOSED** | 公式（5）使用 \(\operatorname{sg}[\widehat y^{\rm tea}]\) |
| Target input 的 future EO/recorded mask/future-weather 权限不清 | **CLOSED** | 公式前文字完整定义 \(\mathcal C^*_{t+H}\) 及 future-weather zeroing |
| Target branch 未说明 all-frames-visible encode 与 terminal token | **CLOSED** | 过程文字和公式（6）均只形成 terminal target |
| Patch mask 被弱化为“存在 clear vegetation pixel” | **CLOSED** | 当前明确要求 terminal \(4\times4\) patch fully clear 且至少一个 vegetation pixel |
| Future EO “student 完全不可见”的过强说法 | **CLOSED** | 当前明确其构造 stopped training-only target，但不进入 student forecast/inference |
| Curriculum 与 checkpoint 日志混在 §3.3 | **CLOSED** | 40 epochs、14,880 updates、schedule、partial unfreezing 和 selection 已归入 Section 4 |
| FS alignment 被误当成 load-bearing 证据 | **CLOSED** | 本节末句把 load-bearing 判断明确交给后续 state-contribution intervention |

## 3. 三种训练身份事实核对表

| 身份 | 来源/初始化 | 输入权限 | 冻结状态与梯度去向 | 推理时去向 | 正文核对 |
|---|---|---|---|---|---|
| **TerraState student** | 从允许的 forecasting precursor 进行 exact full-model warm-start；代码拒绝 raw Phase-I B4 作为 student init | 正式 forecast 的 history operator 读取 cloud-masked historical EO、past weather 和 static geography；future EO 不进入 student forecast，future weather 只经 \(T_\psi\) 进入 state-mediated path | 梯度只更新 schedule 当前允许的 student 参数。完整计划前 80% 冻结 \(q_\theta\)，最后 20% 才计划部分解冻；selected 11,904-step checkpoint 的 \(q_\theta\) 实际始终冻结 | **保留**；正式推理只运行 student 的 \(q\to P\to T\to O\) 与加性预测路径 | **PASS**。`exact full-model warm start`、deployable student、schedule-controlled gradient 均准确 |
| **Frozen full-weather KD teacher** | 从独立 full-weather Phase-I B4 的 `q.*` 构造并 exact-load 为独立 `PVTContextformerQ`；不是 student 自蒸馏，也不是 future-state target encoder | 读取 EO history、past weather、static geography 和完整 future-weather sequence；future EO image tokens 在 forecast 调用中不可见 | 永久 `eval`、`requires_grad=False`；trainer 在 `no_grad` 中生成 prediction，公式中再以 \(\operatorname{sg}\) 阻断 target gradient | **丢弃**；不属于 student inference state dict，`model(data)` 不调用 teacher | **PASS WITH MINOR TERMINOLOGY NOTE**。身份、future-weather 权限、无 future EO、停止梯度和推理时删除都准确；只需将 `observation history` 在术语统一时明确含 past weather |
| **Frozen future-state target encoder** | 训练开始时复制 student 初始 \(q_{\theta^0},P_{\rho^0}\) 并永久冻结；cache 的 q/projector SHA 与 trainer 初始 pair SHA 相等 | 保留带 recorded masks 的 all-frame EO，包括 future frames；保留 past weather 与 static geography；future weather 显式置零 | encoder 在 `eval/no_grad` 下离线生成 terminal \(z^*_{t+H}\)；cache 以普通 target tensor/mask 进入 loss，\(z^*\) 再次 detach；梯度只回到 student transitioned state path | **丢弃/不调用**；inference 不构造 target encoder、不读取 cache、不接收 \(z^*\) | **PASS** |

### 3.1 身份证据索引

- Student exact warm-start：
  `WorldModel2026-planb-v2train/models/terrastate_v2.py:170–191`；
  `train/train_terrastate_v2.py` 中 `warm_start_terrastate_v2(...)`。
- KD teacher：
  `train/train_terrastate_v2.py` 中 `build_teacher(...)` 和训练循环的
  `torch.no_grad()` teacher forward；
  `models/terrastate_v2.py:76–108`。
- Future-state target encoder/cache：
  `train/terrastate_future_state_cache.py:33–112,163–248,306–337`；
  `scripts/build_future_state_cache.py`。
- Selected model：
  `evidence_workspace/raw/release/selection_record.json`；
  `evidence_workspace/results_ledger.json`；
  `evidence_workspace/raw/release/EVIDENCE.md`。

## 4. GT / KD / FS 逐公式、mask、aggregation 与梯度核对

### 4.1 统一符号

| 符号 | 正文含义 | 实现对应 | 结论 |
|---|---|---|---|
| \(b\) | minicube index | batch element | **PASS** |
| \(h\) | forecast horizon | target-window time index | **PASS** |
| \(p\) | raster pixel | spatial pixel after NDVI channel selection | **PASS** |
| \(c_{bhp}\) | clear-observation indicator | `dynamic_mask < 1.0` | **PASS** |
| \(v_{bp}\) | vegetation indicator | land-cover \([10,40]\) | **PASS** |
| \(a_{bp}\) | prediction validity | \(\max_h\mathbf 1[\widehat y_{bhp}\ne-1]\) | **PASS** |
| \(i\) | terminal spatial patch across batch | flattened cube-major terminal patch index | **PASS** |
| \(m_i\) | valid future-state patch | terminal patch fully clear AND contains vegetation | **PASS** |

### 4.2 \(\mathcal L_{\rm GT}\)

正文公式先计算

\[
\bar\ell^{\rm GT}_{bp}
=
\frac{\sum_h c_{bhp}(\widehat y_{bhp}-y_{bhp})^2}
{\sum_h c_{bhp}+\epsilon_{\rm pix}},
\]

再计算

\[
\mathcal L_{\rm GT}
=
\frac{\sum_{b,p}v_{bp}a_{bp}\bar\ell^{\rm GT}_{bp}}
{\sum_{b,p}v_{bp}a_{bp}+\epsilon_{\rm GT}}.
\]

| 核对项 | 实际代码 | 正文 | 结论 |
|---|---|---|---|
| 时间聚合 | 每个 pixel 内先对 clear horizons 求和，并除以该 pixel 的 clear-horizon 数 | 完整写出 | **PASS** |
| 空间/样本聚合 | 再对 vegetation × prediction-valid pixels 平均 | 完整写出 | **PASS** |
| Cloud mask | \(c_{bhp}=\mathbf1[\mathrm{mask}<1]\) | 定义为 clear indicator | **PASS** |
| Prediction mask | 使用 `pred != -1`，沿 horizon 取 max | \(a_{bp}\) 完整定义 | **PASS** |
| 与 KD 的区别 | 不是 global time–pixel mean | 公式后明确解释 | **PASS** |
| 稳定项 | \(\epsilon_{\rm pix}=\epsilon_{\rm GT}=10^{-8}\) | 有符号但无数值 | **MINOR / APPENDIX DETAIL** |
| 梯度 | 回到 student forecast path；GT 无 teacher/target gradient | 符合文字 | **PASS** |

### 4.3 \(\mathcal L_{\rm KD}\)

\[
\mathcal L_{\rm KD}
=
\frac{\sum_{b,h,p}c_{bhp}v_{bp}
(\widehat y_{bhp}-\operatorname{sg}[\widehat y^{\rm tea}_{bhp}])^2}
{\sum_{b,h,p}c_{bhp}v_{bp}+\epsilon_{\rm KD}}.
\]

| 核对项 | 实际代码 | 正文 | 结论 |
|---|---|---|---|
| Mask | clear × vegetation | \(c_{bhp}v_{bp}\) | **PASS** |
| Prediction-valid mask | KD 不使用 \(a_{bp}\) | 公式未加入 \(a_{bp}\) | **PASS** |
| 聚合 | 所有 clear vegetation time–pixel elements 的一次 global masked mean | 完整写出并解释 | **PASS** |
| Teacher gradient | teacher forward 在 `no_grad`；prediction detach | \(\operatorname{sg}\) 与文字均明确 | **PASS** |
| Student gradient | KD 只正则 student prediction toward teacher target | 文字使用 `regularize`，没有提前写成已证明效果 | **PASS** |
| 稳定项 | \(\epsilon_{\rm KD}=10^{-8}\) | 有符号但无数值 | **MINOR / APPENDIX DETAIL** |

### 4.4 \(\mathcal L_{\rm FS}\)

| 核对项 | 实际代码 | 正文 | 结论 |
|---|---|---|---|
| Target encoder identity | training-start student \(q/P\) frozen copy | \((\theta^0,\rho^0)\) 明确定义 | **PASS** |
| Target EO | all-frame observed EO，含 future frames 和 recorded masks | 完整定义 \(\mathcal C^*_{t+H}\) | **PASS** |
| Target weather | past weather 保留，future weather 置零 | 完整说明 | **PASS** |
| Encoding mode | `pred_start=C+H, preds_length=0`；所有时间位置进入 encode，recorded mask 仍决定 patch token visibility | “all-frames-visible encoding mode”并立即说明 recorded masks | **PASS** |
| Target horizon | 只取 terminal token，cache 只存 \(h=H=20\) | 只形成 terminal target | **PASS** |
| Projector | terminal token 经过 frozen \(P_{\rho^0}\) | 公式（6）与文字一致 | **PASS** |
| Stop-gradient | target encoder `no_grad`，cache tensor在 loss 中 detach | \(\operatorname{sg}\) 完整写出 | **PASS** |
| Distance | student 与 target 两侧先 LN，再计算 \(1-\cos\) | 完整写出 | **PASS** |
| Patch mask | terminal \(4\times4\) patch 中无任何 cloud-masked pixel，且至少一个 vegetation pixel | “fully clear and ... at least one vegetation pixel” | **PASS** |
| Aggregation | valid terminal patches 上 masked mean | \(\sum_i m_i\ell_i/(\sum_i m_i+\epsilon_{\rm FS})\) | **PASS** |
| 稳定项 | \(\epsilon_{\rm FS}=10^{-6}\) | 有符号但无数值 | **MINOR / APPENDIX DETAIL** |
| Student gradient | loss 回到 student \(z_{t+H}\) path；target side stopped | 本节信息边界准确 | **PASS** |

### 4.5 总损失

\[
\mathcal L
=
\mathcal L_{\rm GT}
+0.5\,\mathcal L_{\rm KD}
+\lambda_s\,\mathcal L_{\rm FS}.
\]

| 核对项 | 结果 |
|---|---|
| GT 权重 \(1.0\) | **PASS** |
| KD 权重 \(0.5\) | **PASS** |
| FS 权重 \(\lambda_s\) | **PASS** |
| Composition objective | **不存在于正式 V2 loss；正文未加入** |
| VICReg | **不存在于正式 V2 loss；正文未加入** |
| Intervention/driver distillation | **不存在于正式 V2 loss；正文未加入** |
| 额外 KD 或 residual objective | **不存在于正式 V2 loss；正文未加入** |

## 5. Future EO 监督与推理信息边界

### 5.1 结论

**PASS：Future EO 是合法的训练监督来源，不是 student forecast 或 test-time
inference 输入。**

| 路径 | Future EO | Future weather | Cache/teacher | 梯度 | 推理时存在 |
|---|---|---|---|---|---|
| Student history/state construction | 不可见 | 不可见 | 不读取 | 按 schedule 更新 student | 是 |
| Student transition | 不可见 | 可见，仅经 \(T_\psi\) | 不读取 | 按 schedule 更新 student | 是 |
| KD teacher | future image token 不可见 | 完整可见 | 独立 teacher | teacher 无梯度 | 否 |
| Future-state target encoder | 可见，但保留 recorded masks | future 部分置零 | 离线生成 cache | encoder/target 无梯度 | 否 |
| \(\mathcal L_{\rm FS}\) | 仅通过 stopped \(z^*\) 构成监督 | 不作为 target shortcut | trainer 读取 tensor/mask | 梯度只回 student \(z_{t+H}\) path | 否 |

正文句子：

> Future EO is used only to construct a stopped, training-only target; it is
> never an input to the student forecast or inference graph.

与实际梯度路径一致。该句没有否认 future EO 对 student loss 的监督作用，只排除了
future EO 作为 student forward/inference input。

### 5.2 主张安全检查

| 潜在越界主张 | §3.3 当前状态 | 结论 |
|---|---|---|
| FS alignment 已证明 state load-bearing | 明确否认，并交由后续 intervention | **PASS** |
| FS alignment 已证明 non-collapse | 未声称 | **PASS** |
| Target 等于完整物理状态 | 未声称 | **PASS** |
| Future EO 进入正式推理 | 明确排除 | **PASS** |
| Target encoder/cache 是部署模块 | 明确排除 | **PASS** |
| Causal/physical correctness | 未声称 | **PASS** |
| Composition/VICReg 等额外目标 | 未出现 | **PASS** |

## 6. §3.2—§3.3—§3.4—Section 4 边界检查表

| 章节 | 应承担的功能 | 当前内容 | 边界结论 |
|---|---|---|---|
| §3.2 Architecture | 一次 inference 如何从 historical context 构造 state、transition、readout 和 additive forecast | 只定义 \(q,P,T,O,b,z,r,\alpha\) 与 direct transition | **PASS**；没有 teacher、target、loss 或 schedule |
| §3.3 Future-Anchored State Learning | 三种训练身份；GT/KD/FS 目标；future-EO supervision 与 inference boundary | 当前四段分别承担 identity、forecast objectives、future-state target、total objective/boundary | **PASS**；只保留核心学习机制 |
| §3.4 Testable Interfaces | 训练后 state-contribution removal、\(T\to I\) supporting diagnostic、future-weather substitution 及非因果限定 | §3.3 只在结尾把 load-bearing 证据交给后续 intervention，没有提前展开协议 | **PASS** |
| Section 4 Implementation / Model Selection | optimizer、epochs、updates、\(\lambda_s\) schedule、partial unfreezing、candidate selection 与 selected checkpoint 实际路径 | 完整计划与 selected 11,904-step checkpoint 已明确分开 | **PASS** |

### 6.1 完整协议与 selected checkpoint 的事实分离

| 事实 | 代码 / provenance | 正文 | 结论 |
|---|---|---|---|
| 完整计划 | 40 epochs，14,880 updates | Section 4 明确写完整 schedule | **PASS** |
| 0–20% | \(\lambda_s:0\to0.02\)，\(q\) frozen | Section 4 一致 | **PASS** |
| 20–80% | \(\lambda_s=0.02\)，\(q\) frozen | Section 4 一致 | **PASS** |
| 80–100% | \(\lambda_s=0.01\)，last history block eligible for updates | Section 4 一致 | **PASS** |
| Selected candidate | validation forecast performance only，选择发生在 intervention results 之前 | Section 4 一致 | **PASS** |
| Selected step/stage | update 11,904，stage 2，80% boundary | Section 4 一致 | **PASS** |
| Selected realized path | 未经历 final 20% 或 partial unfreezing，history operator 始终 frozen | Section 4 明确写出 | **PASS** |

冻结 provenance：

- checkpoint file SHA-256：
  `644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd`
- weight SHA-256：
  `aba100c138119bc0fc4412082412596dcf31090410643aa0736b5705b04feaa7`
- target q/projector init SHA-256：
  `da978b0243c8dae070d8a9a3db8e09b889ba9e4c91b36724370c5d747593243d`
- KD teacher SHA-256：
  `bbe2c3ee6de540ae6eabeb7798f331388112ad370dbcae9533187344f2f8a302`

本地仓库 HEAD 与 selection record 的 V2 commit 完全一致。checkpoint binary 本身不在
当前本地可见路径，因此本轮没有重新计算 checkpoint SHA；上述身份来自已冻结 release
bundle、selection record 和 results ledger。该限制不造成 §3.3 方法事实冲突。

## 7. AAAI 方法写作质量

| 段落 | 单一功能 | “目的→机制→公式/过程→边界或性质” | 写作判断 |
|---|---|---|---|
| Training Identities and Purpose | 区分 deployable student 与两条冻结 reference branch | 先说明训练为何分身份，再给来源、输入、冻结和 inference 去向 | **PASS** |
| Forecast Objectives | 区分 observable GT supervision 与 KD regularization | 先说明两个目标，再定义索引/mask、给公式、解释聚合差异 | **PASS** |
| Future-State Representation Target | 定义 future-state anchor 的来源和精确 mask | 先给目的，再给 target construction、公式、mask 和 future-EO boundary | **PASS** |
| Total Objective and Inference Boundary | 汇总唯一 loss 并限定其能证明什么 | 给总式、删除 training-only branches、把 load-bearing 交给后续 intervention | **PASS** |

语言检查：

- 未发现工程日志式 checkpoint 路径、SHA、阶段代号或服务器配置；
- 未发现 `smoke`、`gate pass`、`rescue`、`contract evaluator` 等研发语言；
- 未发现 `novel`、`remarkably`、`effectively`、`superior` 等无证据宣传；
- 未发现把 architecture/training objective 写成 empirical proof；
- §3.3 英文 prose 未发现超过 35 个英文词的复杂句；最长句约 32 词；
- 未发现无明确先行词、影响理解的 `this/it/they`；
- 四个段落均可脱离代码理解，且公式前后解释充分；
- 专业度、段落纯度与已冻结 §3.1、§3.2 相当。

## 8. 中英文一致性

| 核对项 | 英文 | 中文 | 结论 |
|---|---|---|---|
| 四段结构 | identities / forecast objectives / FS target / total boundary | 训练身份 / 预测目标 / 未来状态目标 / 总目标边界 | **PASS** |
| Student warm-start | exact full-model warm start | 完整模型精确 warm-start | **PASS** |
| Teacher identity | frozen full-weather KD teacher | 冻结的完整天气 KD 教师 | **PASS** |
| Target identity | training-start frozen \(q/P\) copy | 训练开始时复制并冻结的 \(q/P\) | **PASS** |
| GT/KD formula | 公式（5） | 中文 tag（5） | **PASS** |
| FS formula/mask | 公式（6），fully-clear × contains-vegetation | 中文 tag（6），完全无云且至少一个植被像素 | **PASS** |
| Total loss | 公式（7） | 中文 tag（7） | **PASS** |
| Future EO boundary | stopped training-only target；非 student input | 同等限定 | **PASS** |
| Load-bearing boundary | FS alone cannot establish | 中文同强度 | **PASS** |
| Teacher past-weather wording | 英文 `observation history` 略宽 | 中文“观测历史”同样略宽 | **MINOR，同步存在但无主张强度差异** |

公式编号和交叉引用：

- `eq:forecastlosses` → Equation (5)，PDF 第 4 页；
- `eq:futurestate` → Equation (6)，PDF 第 4 页；
- `eq:total` → Equation (7)，PDF 第 4 页；
- §3.3 对 Equation (1) 的引用已解析；
- 中英文符号、下标、三项权重和公式顺序一致。

## 9. 现有编译与排版只读检查

审计读取的是 2026-07-28 17:00 UTC 生成的最新：

- `paper/main.log`
- `paper/main.pdf`

检查结果：

| 项目 | 结果 |
|---|---|
| PDF 页数 | **10 pages** |
| §3.3 所在页 | **第 4 页** |
| Equation (5)–(7) | 均在第 4 页，未越出版心 |
| LaTeX error | **0** |
| Undefined citation | **0** |
| Undefined reference | **0** |
| Overfull hbox/vbox | **0** |
| Underfull hbox | **5**；均不指向 §3.3（正文 §3.1/§3.2 与 bibliography） |
| Underfull vbox | **1**；全篇浮动/分页警告，不是 §3.3 公式溢出 |
| §3.3 双栏阅读顺序 | 左栏 identity/GT-KD/FS 起始，右栏完成 FS、总目标并进入 §3.4；顺序正常 |
| 明显公式裁切或重叠 | **未发现** |

当前全篇的 underfull 与分页问题属于后续统一排版检查，不构成 §3.3 冻结问题，本报告
不计入 §3.3 的 Minor 数量。

## 10. 冻结判定

### 3.3_TEXT_FINAL_FROZEN

§3.3 已达到已冻结 §3.1 与 §3.2 的事实准确性、公式完整性、章节纯度和主张安全标准，
可以正式冻结。

此后 §3.3 只允许：

1. 全篇术语统一；
2. 篇幅压缩；
3. 引用与排版性调整。

不得改变：

- student、KD teacher、future-state target encoder 的身份；
- GT、KD、FS 的公式、mask、聚合与权重；
- future EO / future weather 的输入权限；
- stop-gradient 与训练/推理边界；
- selected checkpoint 的实际训练经历；
- future-state alignment 与 load-bearing evidence 的逻辑边界。

两项 Minor 的处理方式不阻塞冻结：

- teacher 的 past-weather 输入可在全篇术语统一时显式化；
- epsilon 精确值应放在 Section 4 或复现附录，而不是扩写本节。

## 11. 是否可以开始 §3.4 修改

**可以。**

§3.4 修改可直接以冻结的 §3.2 加性预测接口和本节末句为起点，继续限定：

- state-contribution removal 是 load-bearing 主干预；
- \(T\to I\) 只是 supporting diagnostic；
- weather substitution 固定历史上下文并只替换 \(T_\psi\) 的 future-weather input；
- 不把诊断替换写成 causal effect、counterfactual correctness 或 composition 证据。

---

**最终状态：**

`PASS_WITH_MINOR`  
`3.3_TEXT_FINAL_FROZEN`  
`3.4_REVISION_MAY_START`
