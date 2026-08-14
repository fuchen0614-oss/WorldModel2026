# TerraState Method 最终实现规范与 AAAI 写作审计

> 审计日期：2026-07-28  
> 审计性质：只读、独立、以最终 V2 实现和冻结证据为准  
> 总判定：**BLOCKED**  
> “BLOCKED”表示当前候选稿尚不能作为“与冻结实现和证据完全一致”的投稿版本通过；不表示方法实现或冻结实验失效。阻断项均可通过正文修订和 Figure 2 作者手动改图消除，不要求重新训练或创造新指标。

## 0. 审计结论摘要

最终 V2 实现具有一条清楚且可审计的推理链：

\[
\begin{aligned}
(b_{1:H},e_t)&=q_\theta(\widetilde{\mathcal C}_t),\\
z_t&=P_\rho(e_t),\\
z_{t+h}&=T_\psi(z_t,u_{t:t+h},g,h),\\
r_h&=O_\omega(z_{t+h}),\\
\widehat y_{t+h}&=b_h+\alpha r_h,\qquad \alpha\equiv 1.
\end{aligned}
\]

其中，\(q_\theta\) 的正式推理输入显式清零未来 EO、未来天气和未来掩膜；未来天气只能经共享转移 \(T_\psi\) 进入状态残差路径。每个 \(z_{t+h}\) 都由同一个 \(z_t\) 经过一次 horizon-conditioned direct transition 得到，而不是从 \(z_{t+h-1}\) 递归滚动。读出 \(O_\omega\) 产生空间栅格贡献 \(r_h\)，再与天气无关的 context-only forecast \(b_h\) 相加。

当前稿的总体结构和核心公式已接近实现，但有三个阻断性事实冲突：

1. **Q3 estimand 写错。** 冻结 evaluator 的 `loss_e_actual/donor/mean` 是对完整 20 步未来目标窗口计算的逐 minicube masked MSE，不是终端 \(h=20\) 的 endpoint loss。摘要、引言、Method、Q3 问题、Table 3 caption、结果和结论中的 “endpoint” 表述必须统一改成 “20-step target-window” 或 “forecast-window”。
2. **正式 Figure 2 破坏信息边界的视觉含义。** Panel (a) 把 “Future meteorological forcing” 放在与历史 EO、过去天气和静态地理相同的 “Multimodal context” 边界内，并用同一总箭头指向 history encoder；这会暗示未来天气进入 \(q_\theta\)，与代码相反。Panel (c) 还用乘号表示 transition，而真实实现是 weather/geography/horizon condition fusion 后的 residual MLP update。
3. **所报告 checkpoint 的实际训练经历写错。** 训练程序计划运行 14,880 updates，并在最后 20% 解冻 \(q\) 的最后 block；但论文 Q1–Q3 使用的冻结 checkpoint 是 step 11,904、stage 2 的 `boundary80`，保存发生在 stage 2→3 切换和 \(q\) 解冻之前。该 checkpoint 实际只经历前 80% 更新，且 \(q\) 始终冻结。当前 Implementation 段把完整 14,880-step curriculum 当作所报告模型的训练经历，必须改写并区分“完整候选训练计划”和“最终证据 checkpoint 的实际路径”。

此外，当前 Method 没有精确定义 \(\mathcal L_{\rm GT}\)、\(\mathcal L_{\rm KD}\)、future-state patch mask、\(\lambda_s\) 调度、warm start 和 checkpoint-specific freeze 状态；Q2 的 \(T\!\to I\) 辅助诊断只在 Results 出现；Q3 的 detectable response、weather-responsive 和 response fidelity 没有形成互不混淆的操作性定义。这些属于 Major 修订。

## 1. 输入冻结与审计边界

### 1.1 指定输入

| 输入 | SHA-256 | 审计方式 |
|---|---|---|
| `paper/main.tex` | `29a031a7b636dbdfea0c222ae3b9c0c4563365e84f9efbb559ca6354f657cf33` | 全文读取；逐段核对 Method、Figure 2 caption、Q1–Q3 与限制 |
| `MANUSCRIPT_ZH_FULL.md` | `efc3e51894d42f0ff1bedc1581f96d70c70df9fd07f552d6733602a5052738c3` | 全文读取；与英文逐项对照 |
| `paper/main.pdf` | `9d4c678915303e204acf52f2b14965b9ea0c1e286617ffe1faccdeb6ccc6c79d` | 读取 8 页文本层、元数据和 Figure 2 所在页；确认编译稿含相同 caption 与术语 |
| 正式 Figure 2 PDF | `47cc851497f6ef8c05104dfe1917b036164d47d976460df486377f69bf5e6409` | 视觉与文字核对 |
| 正式 Figure 2 PNG | `2e15fb8d5cdabb685f9b8d26e8e505fc6896935f25ea20b6e5b4e4266d420df7` | 原分辨率视觉核对 |
| `METHOD_AAAI_WRITING_AUDIT.md` | `ac525c1629e2ae253e24931223681696b1b6421e486b5bc6afffa9e7ad962e7c` | 读取其中 AAAI 方法写作锚点和既有规则 |
| `models/terrastate_v2.py` | `25251928a28320e8dcd8b8b07e870eabad34ae994ff9659d26cedf664bef52f1` | 读取 V2 inference/training API |
| `train/train_terrastate_v2.py` | `d09242c304fd21a322447d584aef6a0fc164706b18ee7115982a30da6b6d59f9` | 读取 teacher、课程、冻结、优化和 checkpoint 时序 |
| `train/terrastate_v2_common.py` | `53695c9e5f8c96d4e65229553f9cb969095b1f92167a2da579642f86ace5f73f` | 读取 full24 字段顺序与 provenance helper |
| `eval/eval_b4_exclusive_contract.py` | `c6759dec60ede433f99a97b1ba3191d9427210cd907a08d6d8776dfb8efec9b4` | 读取 Q2 evaluator 与 intervention invariants |
| `evidence_workspace/results_ledger.json` | `d1f8ec7d7a51fae87afc8ba9dbc27905c6816434dc5554980d2e7c2eb472c4b2` | 读取 Q1–Q3 结果、checkpoint 和限制 |
| Q2 validation JSON | `33b40d3e6bf6e0190c9415a9e0421e9809063356dcba2350890defeeed35f2d9` | 全量解析 |
| Q1/Q2 OOD-t JSON | `7ebc0569d705a9991ac8b8d17c42113c9da052b2bec73f7c28d021e28a65a051` | 全量解析 |
| Q3 frozen JSON | `9dae43b9a8a4fcdf0a73ef91daa58c189a88e769541ce295046cd0e938497041` | 全量解析并核对 Q3 汇总、84 行配对和判据 |

### 1.2 为解释继承实现而读取的直接依赖

V2 类继承了 exclusive route，因此仅读 `terrastate_v2.py` 不足以重建真实路径。本审计还只读检查了：

- `models/plan_b_b4_exclusive.py`：天气排他路径、固定 \(\alpha\)、`_prior_state` 与最终加法；
- `models/plan_b_b4.py`：weather/geo/time encoder、direct transition、readout 和 unpatchify；
- `models/encoders/pvt_contextformer_q.py` 与 `contextformer_official.py`：\(q\) 的 token、天气和 future-image mask 行为；
- `models/encoders/state_projection.py`：\(P_\rho\)；
- `models/losses/masked_l2_ndvi.py`：真实 \(\mathcal L_{\rm GT}\)；
- `train/terrastate_future_state_cache.py`：future-state target、mask 和冻结 cache；
- `WorldModel2026-planb/eval/extreme_state_audit.py`：生成冻结 Q3 JSON 的实际 estimand 与 intervention direction；
- `evidence_workspace/raw/release/selection_record.json`：最终 checkpoint 的真实选择与训练阶段。

本审计不把代码注释本身视为证据；结论依据实际张量切片、forward path、loss 计算、checkpoint metadata 和冻结 JSON 数值。

## 2. 最终推理路径：canonical specification

### 2.1 输入与记号

对每个 GreenEarthNet minicube：

- 历史长度 \(C=10\)，目标长度 \(H=20\)；
- 历史 EO 与云/质量 mask：\(x_{1:C},m_{1:C}\)；
- 过去天气：\(u_{1:C}^{\rm past}\)；
- 未来天气：\(u_{t+1:t+H}\in\mathbb R^{H\times24}\)；
- 静态地理：代码使用 `static[0][:,:3]`；
- 目标：未来 20 帧 NDVI。

24 维天气按 aggregation-major 排列：

`mean_fg, mean_hu, mean_pp, mean_qq, mean_rr, mean_tg, mean_tn, mean_tx, min_*, max_*`。

### 2.2 Context-only history pass

`_context_only_data` 保持 30 帧张量长度，但执行：

\[
x_{C+1:C+H}=0,\qquad
u_{C+1:C+H}=0,\qquad
m_{C+1:C+H}=0.
\]

随后只调用一次共享 Contextformer：

\[
(b_{1:H},z^{q}_{1:C+H})
=q_\theta(\widetilde{\mathcal C}_t;\operatorname{pred\_start}=C,
\operatorname{preds\_length}=H).
\]

在 eval mask 规则下，未来 image tokens 被 `mask_token` 取代；未来天气又被输入侧显式置零。因此：

- \(b_{1:H}\) 是 future-weather-free 的 context-only forecast；
- \(e_t=z^q_C\) 是最后一个历史时刻的空间 token；
- 同一个 \(q_\theta\) pass 同时产生 \(b_{1:H}\) 与 \(e_t\)；
- \(q_\theta\) 同时读取历史 EO、历史 cloud mask、过去天气和静态地理。

### 2.3 Predictive-state construction

\[
z_t=P_\rho(e_t)\in\mathbb R^{1024B\times256}.
\]

每个 minicube 对应 \(32\times32=1024\) 个空间 patch state；\(P_\rho\) 是 256→512→256 的空间逐 token projector，并保留 patch 顺序。

### 2.4 Weather/geography/horizon condition

静态地理除进入 \(q_\theta\) 外，还经独立 \(E_g\) 编码为每 patch 的 64 维条件。未来 full24 weather 经共享 GRU 一次产生所有 prefix representation：

\[
d_h=E_u(u_{t+1:t+h}),\quad h=1,\ldots,H.
\]

整数时距 \(h\) 经 64 维 sinusoidal embedding \(E_h(h)\)。条件通过 concatenation 和 MLP 融合：

\[
c_h=F\bigl([d_h;E_g(g);E_h(h)]\bigr).
\]

### 2.5 Shared direct transition

\[
z_{t+h}
=z_t+\Delta_\psi\bigl([\operatorname{LN}(z_t);c_h]\bigr).
\]

关键实现性质：

1. 所有 horizon 共享同一个 GRU、fusion MLP 和 transition MLP；
2. 每个 \(h\) 使用天气前缀 \(u_{t+1:t+h}\) 和自己的 elapsed-time code；
3. 正式 forecast 对每个 horizon 都从同一个 \(z_t\) 做一次 direct transition；
4. 正式 inference 不是 \(z_t\to z_{t+1}\to\cdots\to z_{t+H}\) 的递归 rollout；
5. 代码保留的 `composed_state` 不在 V2 正式 forecast 和三项 V2 loss 中使用，不能据此主张 Q4/composition。

当前正文公式允许 direct interpretation，但 \(T_\psi(z_a,u_{a:b},g,b-a)\) 的一般写法可能被误读为任意中间状态递归。最终稿应在公式后明确：“For each queried \(h\), TerraState applies the shared transition once to the same \(z_t\), using the ordered prefix \(u_{t+1:t+h}\).”

### 2.6 Readout and additive forecast closure

`o_delta` 是每个 state token 上的共享线性层，输出 \(4\times4\) patch；随后 unpatchify 为 NDVI 栅格：

\[
r_h=O_\omega(z_{t+h}),\qquad
\widehat y_{t+h}=b_h+\alpha r_h,\qquad \alpha\equiv1.
\]

\(\alpha\) 是 non-learnable buffer，不是可收缩 gate。正文省略 \(\alpha\) 在数学上等价，但为了让 Q2 的 `alpha=0` evaluator 与实现可追溯，建议第一次定义 closure 时写出 \(\alpha\equiv1\)，并说明 `alpha=0` 仅为评测期 removal 操作。

`endpoint contribution` 应改为 `horizon-specific forecast contribution` 或 `spatial forecast contribution`。\(r_h\) 对每个 \(h=1,\ldots,20\) 都存在，不只是 terminal endpoint。

## 3. 最终训练路径：canonical specification

### 3.1 Warm start 与三个模型身份

训练中有三个不同身份，必须避免都写成“encoder”：

1. **Student TerraStateV2**：从 `ObsWorldB4Exclusive` 的 MAIN-last checkpoint 全模型精确 warm start；不是只初始化 \(q_\theta\)，也不是从 raw Phase-I B4 直接创建新 branch。
2. **Frozen KD teacher**：从独立 Phase-I full-weather B4 checkpoint 提取 `q.*`，构造冻结 `PVTContextformerQ`。它读取历史 EO、过去天气、静态地理和完整未来天气；future EO image tokens 按 `pred_start=10` 被 mask，不可见。
3. **Frozen future-state target encoder**：训练开始时深拷贝 student 的初始 \(q_\theta,P_\rho\)，永久 `eval`、`no_grad`，先离线生成 SHA-locked cache。它与 KD teacher 不是同一个网络或 checkpoint。

当前正文只写 “\(q_\theta\) is initialized from a pretrained PVT v2/Contextformer forecaster”，不足以复现冻结 V2 权重链，属于 Major omission。

### 3.2 Student forward

对训练 batch，student 先走与推理完全相同的路径，得到：

\[
\widehat y_{1:H},\quad b_{1:H},\quad z_t,\quad
z_{t+H}=T_\psi(z_t,u_{t+1:t+H},g,H).
\]

训练期 target 和 teacher tensor 从 trainer 传入；`model(data)` 的推理签名不读取 teacher 或 cache。

### 3.3 Ground-truth objective 的精确定义

令 \(c_{bhp}\) 表示时刻 \(h\)、像素 \(p\) 的 clear mask，\(v_{bp}\) 表示 land-cover 位于 \([10,40]\)，\(a_{bp}\) 表示预测不是 mask value \(-1\)。实际 vendored loss 先对每个像素沿时间归一化：

\[
\bar \ell_{bp}
=\frac{\sum_{h=1}^{H}c_{bhp}
(\widehat y_{bhp}-y_{bhp})^2}
{\sum_{h=1}^{H}c_{bhp}+\epsilon},
\]

再在 vegetation/prediction-valid 像素上平均：

\[
\mathcal L_{\rm GT}
=\frac{\sum_{b,p}v_{bp}a_{bp}\bar\ell_{bp}}
{\sum_{b,p}v_{bp}a_{bp}+\epsilon}.
\]

因此它不是简单的“把所有有效 time-pixel elements 放在一起做 global MSE”。当前 “validity-masked forecast loss” 方向正确但不足以复现，至少应说明 “a per-pixel, time-normalized masked NDVI MSE averaged over valid vegetation pixels”。

### 3.4 KD objective 的精确定义

teacher 输出：

\[
\widehat y^{\rm tea}_{1:H}
=q_{\rm tea}(\mathcal H_t,u_{\le t}^{\rm past},
u_{t+1:t+H},g),
\]

其中 future EO 被 mask，未来天气完整可见。令
\(M_{bhp}=c_{bhp}v_{bp}\)，则：

\[
\mathcal L_{\rm KD}
=\frac{\sum_{b,h,p}M_{bhp}
(\widehat y_{bhp}-\operatorname{sg}\widehat y^{\rm tea}_{bhp})^2}
{\sum_{b,h,p}M_{bhp}+\epsilon}.
\]

与 \(\mathcal L_{\rm GT}\) 不同，KD 是对所有有效 time-pixel elements 的 global masked mean。当前正文没有给出该公式，也没有说明 teacher 不见 future EO，需补充。

### 3.5 Future-state target 的精确定义

target encoder 输入保留全部真实 EO，但只把未来天气清零：

\[
\mathcal C^{*}_{t+H}
=\bigl(x_{1:C+H},m_{1:C+H},
u_{1:C}^{\rm past},0_{C+1:C+H},g\bigr).
\]

它以 `pred_start=C+H, preds_length=0` 运行，使 30 帧 EO image tokens 全部可见，并只取 terminal token：

\[
z^*_{t+H,i}
=\operatorname{sg}\!\left[
P_{\rho^0}\!\left(q_{\theta^0}(\mathcal C^*_{t+H})_{C+H,i}\right)
\right].
\]

\((\theta^0,\rho^0)\) 是训练开始时 student 的冻结副本，不随 student 更新。cache 只存 \(h=20\) target，不存中间 horizon。

有效 patch mask 不是“有任意 clear vegetation pixel”：

- terminal \(4\times4\) patch 内不能有任何 cloud-masked pixel；
- patch 内至少有一个 land-cover \([10,40]\) 的 vegetation pixel。

未来状态损失为：

\[
\mathcal L_{\rm FS}
=\frac{\sum_i m_i
\left[1-\cos\bigl(\operatorname{LN}z_{t+H,i},
\operatorname{LN}z^*_{t+H,i}\bigr)\right]}
{\sum_i m_i+\epsilon}.
\]

当前正文的 cosine 公式正确，但 `q_frozen(o_{\le t+H})` 没有定义其天气和静态输入，`valid terminal patches` 也没有给出 CF-consistent 全 patch clear 规则，属于 Major omission。

### 3.6 总损失、调度与冻结

\[
\mathcal L
=1.0\,\mathcal L_{\rm GT}
+0.5\,\mathcal L_{\rm KD}
+\lambda_s\,\mathcal L_{\rm FS}.
\]

程序中的完整候选训练计划是：

| 更新区间 | \(\lambda_s\) | \(q_\theta\) | 其他 branch |
|---|---:|---|---|
| 0–20% | 线性 \(0\to0.02\) | 全冻结 | 训练 |
| 20–80% | 0.02 | 全冻结 | 训练 |
| 80–100% | 0.01 | 仅 `core.blocks.2.*` 解冻 | 训练 |

branch LR 为 \(3\times10^{-5}\)；计划解冻的 \(q\) group LR 为
\(3\times10^{-5}\times0.033=9.9\times10^{-7}\)。

### 3.7 冻结证据模型实际经历

Q1–Q3 使用的不是完整 100% 训练结束 checkpoint，而是：

- candidate：`stage2_end_boundary80`；
- step：11,904 / 14,880；
- stage：2；
- 保存时机：进入 stage 3、解冻 \(q\) 之前；
- checkpoint metadata：`freeze_b0=true`；
- 因而该 checkpoint 的 \(q_\theta\) 从 warm start 到保存始终冻结；
- 该 checkpoint 未经历最后 20% 的 \(\lambda_s=0.01\) 或 \(q\) 更新。

当前正文的 “Optimization uses ... for 40 epochs and 14,880 updates” 与 “\(q\) updates only during the final 20%” 描述的是完整 run plan，不是最终证据 checkpoint 的实际训练历史。必须改为两句明确区分：

> The candidate run was scheduled for 14,880 updates with a final 20% partial-\(q\) unfreezing stage. All reported Q1–Q3 results use the preregistered boundary checkpoint saved at update 11,904, immediately before that stage; its \(q\) backbone therefore remained frozen throughout its realized training path.

## 4. 信息边界

| 信息源 | 正式 \(q_\theta/P_\rho\) 推理 | 正式 \(T_\psi\) | \(O_\omega\)/加法 | KD teacher | Future-state target | 评测干预 |
|---|---|---|---|---|---|---|
| 历史 EO \(x_{1:C}\) | 是 | 仅通过 \(z_t,b_h\) 间接 | 间接 | 是 | 是 | 固定 |
| 历史 cloud mask | 是 | 间接 | 间接 | 是 | 是 | 固定 |
| 过去天气 \(u_{\le t}^{past}\) | 是 | 仅通过 \(z_t,b_h\) 间接 | 间接 | 是 | 是 | 固定 |
| 未来天气 \(u_{t+1:t+H}\) | **否，显式置零** | **是，唯一正式入口** | 仅经 \(z_{t+h}\) 间接 | 是 | **否，显式置零** | Q3 只替换此项 |
| 静态地理 \(g\) | 是 | 是，经独立 \(E_g\) | 间接 | 是 | 是 | 固定 |
| 未来 EO \(x_{C+1:C+H}\) | **否，置零且 token mask** | 否 | 否 | **否，future image token mask** | **是，仅训练 target** | 只作 ground truth |
| 未来 NDVI target | 否 | 否 | 否 | 否 | 是，作为未来 EO 的一部分 | GT/metrics |
| Land-cover | 不作为 forecast 输入 | 否 | 否 | 否 | 只用于 patch validity | loss/metric mask |
| Future-state cache | 否 | 否 | 否 | 否 | trainer 只读 | inference 不读取 |
| Teacher | 否 | 否 | 否 | 独立冻结模型 | 否 | inference 不存在 |

结论：

- 正式推理无 future EO leakage；
- \(b_h\) 不依赖未来天气；
- 未来天气影响输出只能通过 \(T_\psi\to O_\omega\to r_h\)；
- 静态地理有两个合法入口：history encoder 和 transition condition；
- Figure 2 必须把未来天气从 history encoder 的输入边界中视觉隔离。

## 5. 代码—公式—双语正文—Figure 2—证据对应矩阵

| 对象 | 真实代码 | Canonical 公式/定义 | 英文正文 | 中文正文 | Figure 2 | 冻结证据 | 判定 |
|---|---|---|---|---|---|---|---|
| \(q_\theta\) | `_prior_state` 对 context-only data 做单次 `q.encode` | \((b_{1:H},e_t)=q_\theta(\widetilde{\mathcal C}_t)\) | 基本一致 | 基本一致 | history encoder 与两 branch 可见，但 input boundary 错 | alpha0 精确恢复 prior | **正文 PASS；图 FAIL** |
| \(P_\rho\) | 取 `z_ctx[:,9]` 后 projector | \(z_t=P_\rho(e_t)\) | 一致 | 一致 | `P State projector` 正确 | Q2/Q3 复用同一 \(z_t\) | PASS |
| \(b_h\) | future EO/weather 均置零的 q forecast | context-only forecast | 一致 | 一致 | branch 存在 | `alpha0_pred_equals_context_prior=true` | PASS |
| \(T_\psi\) | GRU prefix + geo + time，concat/fuse，residual MLP | 单次 direct residual transition | 公式大体一致，但应明确非递归 | 同样需明确 | 用“×”画 state/weather，且输入箭头不清 | Q2 identity 辅助；Q3 T-only weather swap | **正文 Major；图 FAIL** |
| \(z_{t+h}\) | 每个 \(h\) 从同一 \(z_t\) 一次 direct transition | \(T(z_t,u_{t+1:t+h},g,h)\) | 可被误读为一般 \(z_a\) rollout | 同 | evolved state 可见，但 state 输入路径不明确 | Q3 weather_in_base=false | Major clarity |
| \(O_\omega\) | Linear state→patch，再 unpatchify | \(r_h=O_\omega(z_{t+h})\) | `endpoint contribution` 不准确 | “终点贡献”不准确 | 把 contribution 画成 token grid | Q2 在加法前切除 | **正文与图都需改** |
| \(\alpha\) | 固定 buffer 1.0 | \(\widehat y=b+\alpha r,\alpha=1\) | 省略，数学等价 | 省略 | 未画 | evaluator 以临时 `alpha=0` removal | Minor traceability |
| \(\mathcal L_{\rm GT}\) | `MaskedL2NDVILoss`，逐像素按 clear horizon 归一化 | 见 §3.3 | 只写 validity-masked | 同 | 不在 Figure 2，允许 | checkpoint training metadata | **正文 Major omission** |
| \(\mathcal L_{\rm KD}\) | global masked MSE to frozen full-weather q teacher | 见 §3.4 | 角色正确，定义不完整 | 同 | 不在 Figure 2，允许 | teacher SHA 冻结 | **正文 Major omission** |
| \(z^*_{t+H}\) | 初始 student q/P 冻结副本；真实未来 EO；未来天气清零；仅 terminal | 见 §3.5 | 主要方向正确，输入和 mask 不完整 | 同 | Figure 2 是 inference/interface 图，省略可接受 | cache SHA/coverage | Major definition |
| Q2 state removal | evaluator 临时 `alpha=0` | \(\widehat y^{remove}=b\) | 一致 | 一致 | 未标实际 cut point | Val/OOD-t LOAD_BEARING | **正文 PASS；图需补接口** |
| Q2 \(T\!\to I\) | monkeypatch transition 返回同一 \(z_t\) | supporting diagnostic only | Results 正确，Method 未定义 | 同 | 未画，允许 | `transition_margin_clean=false` | **Method omission** |
| Q3 actual | 同一 E 的 \(b_E,z_E,g_E\)，输入 \(u_E\) | reference arm | 大体一致 | 大体一致 | actual 可见 | 84 pairs | PASS |
| Q3 donor | 固定 E，只把 \(u_E\) 换成 matched control 的 \(u_C\) | matched donor arm | caption 基本一致 | 同 | donor 可见但未明确“matched”且接入点错误 | 84 pairs | 图需改 |
| Q3 mean | future weather 在全局 z-score 空间置零 | global normalized-mean arm | `normalized mean` 可接受但应定义 | 同 | 只写 mean | 84 pairs | Minor clarity |
| Q3 loss | 全 20 步目标窗口逐 cube masked MSE | \(L^{ctrl}_{window}-L^{actual}_{window}\) | 多处写 endpoint | 多处写终点 | 无 metric 定义 | frozen values/CI | **正文 Critical** |
| Q3 fidelity | donor 和 mean 的 geo-cluster CI lower bound 均 \(>0\) | forecast-window response fidelity | 未完整形式化 | 同 | diamond 无判据 | PASS；hot-dry enhancement FAIL | Major definition |

## 6. Q2 与 Q3 evaluator 对齐

### 6.1 Q2 state-contribution removal

实现：

- evaluator 临时把 non-learnable `alpha` buffer 从 1 置 0；
- 保持 \(q,P,T,O\)、样本和权重不变；
- 输出精确等于 context-only prior；
- evaluator 验证 `alpha0_pred_equals_context_prior=true`。

因此正文的 “remove \(r_h\) immediately before addition” 与 evaluator 一致。Q2 主证据应始终是 state removal，而不是 \(T\!\to I\)。

### 6.2 Q2 identity transition

实现：

- 临时把 transition forward 替换为返回输入 state；
- 所有 horizon 都得到同一个 frozen \(z_t\)；
- readout \(O_\omega\) 因而接收到训练分布外输入；
- Val/OOD-t 均有 `transition_margin_clean=false`。

可支持：“transition involvement 的方向性辅助证据”。不能支持：

- transition 是被完全隔离且严格必要的因果组件；
- identity effect 与 state-removal effect 可直接比较；
- \(T\!\to I\) 比 state removal 更强；
- “预测状态”的定义性核心证据来自 \(T\!\to I\)。

Method 应补一句定义，但保留 supporting-only caveat；Figure 2 无需把 \(T\!\to I\) 画成主接口。

### 6.3 Q3 weather substitution

每个 extreme/control pair 中，对 extreme 样本 \(E\)：

\[
\begin{aligned}
\widehat y_E^{actual}
&=b_E+O(T(z_E,u_E,g_E)),\\
\widehat y_E^{donor}
&=b_E+O(T(z_E,u_C,g_E)),\\
\widehat y_E^{mean}
&=b_E+O(T(z_E,0,g_E)).
\end{aligned}
\]

因此固定的是：历史样本、\(b_E\)、\(z_E\)、\(g_E\)、horizon、readout、checkpoint 和 ground truth；只替换未来天气 tensor。`0` 是全局标准化空间的 per-variable training mean，不是 day-of-year/location climatology。

### 6.4 Q3 estimand 与方向

实际函数虽然名为 `_endpoint_masked_mse`，但代码切片是：

```text
target = data["dynamic"][0][:, context_len:context_len+target_len, 0:1]
```

随后 flatten 全部 \(H\times\)pixel elements。因此：

\[
L_{E,\mathrm{window}}^{a}
=\frac{\sum_{h,p}M_{Ehp}
(\widehat y^{a}_{Ehp}-y_{Ehp})^2}
{\sum_{h,p}M_{Ehp}},
\]

\[
\Delta L_{E}^{donor}
=L_{E,\mathrm{window}}^{donor}
-L_{E,\mathrm{window}}^{actual},
\quad
\Delta L_{E}^{mean}
=L_{E,\mathrm{window}}^{mean}
-L_{E,\mathrm{window}}^{actual}.
\]

正值表示 control loss 更高，即 actual future weather 在该完整预测窗口上更忠实。JSON 内的 `endpoint_fidelity`、`loss_e_*` 等字段名是历史 schema 名称，不能覆盖实际计算定义。

### 6.5 三个 Q3 术语的建议唯一化

| 术语 | 建议操作性定义 | 当前证据 |
|---|---|---|
| detectable response | 在固定 \(b,z,g,O\) 时替换 future weather 会改变输出；报告 response magnitude，且 84/84 donor weather tensors 不同 | 支持；actual-vs-donor 和 actual-vs-mean response magnitude 均非零 |
| forecast-window response fidelity | 对 donor 和 normalized mean 两个 control，\(\Delta L=L_{control}-L_{actual}\) 的 primary geo-cluster 95% CI 下界均 \(>0\) | 支持 |
| weather-responsive predictive state | 结构上 weather 只经 \(T\to O\to r\)；输出响应可检测；且 actual weather 通过上述 fidelity criterion。再结合 Q2，state-mediated path 是 load-bearing | 在该冻结协议和一个 checkpoint 上支持 |

三者不能混写：

- detectable 不等于 fidelity；
- fidelity 不等于 causal effect；
- weather-responsive 不等于 extreme-specific enhancement；
- latent state movement 本身不构成 fidelity；
- 当前证据不提供 counterfactual correctness guarantee。

## 7. 冻结证据边界

### 7.1 Q2

| Split | 主干预 | Official \(\Delta R^2\) | Paired mean 与 paired bootstrap 95% CI | 判定 |
|---|---|---:|---|---|
| Validation | state removal | 0.011214 | 0.016163 \([0.006432,0.025902]\), \(n=589\) | LOAD_BEARING |
| OOD-t | state removal | 0.019972 | 0.021998 \([0.014220,0.030176]\), \(n=1019\) | LOAD_BEARING |

Official dataset-level \(\Delta R^2\) 与 per-minicube paired mean 是不同 estimand。当前 Table 2 已分开报告，正确。不能把 paired CI 画在 official \(\Delta R^2\) 上。

### 7.2 Q3

84 个冻结 pair、31 个 geographic clusters：

| Control | Mean \(L_{control}-L_{actual}\) | Primary geo-cluster 95% CI | 判定 |
|---|---:|---|---|
| Matched donor | 0.002565 | \([0.001119,0.003987]\) | actual 更好 |
| Normalized mean | 0.011261 | \([0.005466,0.017080]\) | actual 更好 |

Hot-dry-minus-normal donor-loss interaction mean 为 0.000436，geo-cluster CI
\([-0.002162,0.003200]\)，因此 extreme-specific enhancement 不成立。

Q3 raw JSON 没有内嵌 checkpoint SHA 或 evaluator commit。它通过 frozen release bundle、run log 和 results ledger 关联到同一 boundary80 checkpoint。该 provenance gap 不推翻现有结果，但正文不应把 Q3 描述成比其 provenance 更强的独立复现实验。

## 8. 图文冲突责任判断

| 冲突 | 责任判断 | 正文动作 | Figure 2 手动作图动作 |
|---|---|---|---|
| Future weather 看似进入 history encoder | **Figure 2 错误**；caption/正文信息边界正确 | 无需迁就图 | 见 M1 |
| Transition 用 weather tokens × state tokens | **Figure 2 错误** | 保留 concat/fusion residual 公式 | 见 M2 |
| 每个 horizon 是否从同一 \(z_t\) direct transition | **二者均不够清楚** | 明写 one direct call from same \(z_t\) per \(h\) | 见 M3 |
| Readout 后仍画成 token grid | **Figure 2 错误** | 把 `endpoint contribution` 改为 horizon-specific spatial contribution | 见 M4 |
| Q2 removal 的切点 | **Figure 2 缺失**，正文正确 | 保留 \(r_h\to0\) 定义 | 见 M5 |
| Q3 intervention 看似位于 transition 下游 | **Figure 2 错误** | 保留“只替换输入 \(T\) 的 future weather” | 见 M6 |
| donor/mean 的精确定义 | **正文与图均不够精确** | 写 protocol-matched donor；mean=zero in global z-score space | 见 M7 |
| Q3 endpoint loss | **英文和中文正文错误**；图没有该 metric | 全文改为 target-window/forecast-window | 图无需增加 endpoint |
| 14,880-step/full curriculum 被当作 evidence checkpoint 经历 | **正文错误** | 区分 planned full run 与 selected boundary checkpoint | Figure 2 不负责训练课程 |
| Figure 2 不展示 KD/GT/future-state target | **可接受视觉简化** | caption 明确 Figure 2 仅画 inference/intervention；Figure 1 承担 training supervision | 无需增加训练 branch |
| 历史 EO 只画少数 tile、天气只画少数曲线 | **可接受视觉简化** | caption 保留 schematic 声明 | 无需修改数量 |

## 9. Figure 2 Manual Correction List

以下仅为作者手动修改清单；本审计未修改任何 PPTX、PDF、PNG、SVG 或图内对象。

### M1 — Panel (a)，输入区域边界与总箭头（Critical）

- 把 “Future meteorological forcing” 及其两张曲线图从当前黑色圆角 `Multimodal context` 容器中移出。
- history encoder 的总输入容器只保留：
  - Historical Earth observations；
  - Historical environmental context（应明确为 past meteorological observations）；
  - Static geographic attributes。
- 当前从整个 panel (a) 指向 Panel (b) history encoder 的白色粗箭头，只能覆盖上述历史/静态容器。
- Future meteorological forcing 应单独沿一条不经过 history encoder 的箭头进入 Panel (c) 的 weather encoder/condition fusion。
- 对应代码：`_context_only_data` 清零 future weather；`_geo_weather` 才切出 future full24。

### M2 — Panel (c)，Shared transition 内的乘号（Critical）

- 删除 weather tokens 与 state tokens 之间的黑色 “×”。
- 替换为一个明确模块，例如：
  - `Condition fusion F([weather; geography; horizon])`；
  - `Residual transition Δψ([LN(z_t); c_h])`；
  - 输出标为 `z_{t+h}=z_t+Δψ(...)`。
- 不能画成 elementwise multiplication、attention product 或 gating，因为代码没有这些操作。
- 对应代码：`torch.cat([d,geo,h_emb])→fuse`，再 `torch.cat([LN(z),cond])→MLP`，最后 residual addition。

### M3 — Panel (b)→(c)，state 输入和 horizon 路径（Major）

- 从 `Predictive state z_t` 画一条明确箭头直接进入 `Shared transition Tψ` 的 state input。
- 在 transition 输出附近标注 `one direct call per h` 或 `shared over h=1,…,H`。
- 不要画成 `z_t→z_{t+1}→…→z_{t+H}` 的串联状态序列。
- 如保留多个 evolved-state 方块，应标注它们分别为从同一 \(z_t\) 查询得到的 \(\{z_{t+h}\}_{h=1}^H\)，不是递归链。

### M4 — Panel (d)，State readout 后的对象类型（Major）

- `State readout Oω` 的输入是 evolved predictive-state tokens；输出不是另一组 latent token。
- 把当前蓝色 `State contribution` token grid 改成空间栅格/patch-unpatchified residual map，并标注 `r_h` 或 `spatial forecast contribution r_h`。
- 保留该 raster contribution 指向加法节点。
- 对应代码：`o_delta(z_th)` 后 `_unpatchify` 得到 `(B,H,1,128,128)`。

### M5 — Panel (d)，Q2 切点（Major）

- 在 `r_h` 进入最终加法节点之前的箭头上添加清楚的 intervention marker：
  - `Q2: state-path removal (r_h→0 / α=0)`。
- 切点不得画在 \(q_\theta\)、\(P_\rho\)、\(T_\psi\) 或 \(z_t\) 上。
- 不要把 `T→I` 画成 Q2 主证据；如需要，可在旁注写 `supporting diagnostic only`。

### M6 — Panel (c)，Q3 Weather intervention 的位置（Critical）

- 当前 `Weather intervention` 区域必须改成 transition 的**上游输入选择器**。
- actual / matched donor / normalized mean 三个 arm 应汇入同一个 weather encoder，再进入同一个 shared transition。
- 删除任何让人理解为“先得到 evolved state，再在其下游做 weather intervention”的箭头或区域关系。
- Q3 输出比较可以放在 transition/readout/final forecast 后，但 intervention 本身必须发生在 \(u_{t+1:t+H}\to E_u\) 处。
- 对应 evaluator：同一 \(b_E,z_E,g_E,O\)，只替换 `uf` 后重新执行 residual decode。

### M7 — Panel (c)，Q3 标签（Minor）

- `donor` 改为 `matched donor weather`。
- `mean` 改为 `normalized mean weather (0 in global z-score space)`；若版面不足，写 `normalized mean` 并在 caption 精确定义。
- donor caption 建议用 `protocol-matched donor`，或完整写 `season/geography/quality-matched donor`。
- 不使用 `climatology`，除非明确只是全局训练均值而非地点/年内日气候态。

### M8 — Panel (d)，最终输出标签（Minor）

- 把 `D3 Vegetation forecast` 改成 `NDVI forecast \hat y_{t+1:t+H}` 或 `Vegetation forecast`。
- `D3` 不是论文中的方法、数据或 metric 记号，容易被视为内部工程名称。

### M9 — Figure 2 caption（Major）

caption 应继续明确：

- Figure 2 只展示 inference path 与 post-training interventions；
- future weather 不进入 history encoder；
- Q2 在加法前移除 \(r_h\)；
- Q3 只替换 transition 的 future-weather path；
- intervention 是 diagnostic substitution，不是 causal/counterfactual operation；
- mean weather 是全局 z-score 空间的零向量；
- 不增加 composition、Q4、SOTA、extreme-specific enhancement 文字。

### M10 — 图像资产 provenance（Minor）

Figure 2 使用了多张遥感图、地形图、天气截图式 tile。即使 caption 称其为 schematic，也不能自动解决来源、许可和匿名性问题。作者应在图表会话保留每个 raster tile 的自有/许可来源清单；若无法证明，替换为原创 vector schematic。该项不改变方法技术含义。

## 10. Method 段落 reverse outline

| 当前段落 | 该段实际功能 | “动机/要求→机制→公式→性质/接口”检查 | 判定与修订 |
|---|---|---|---|
| §3.1 P1，main.tex 202–210 | 定义任务、输入和 forecasting-time information set | 要求→定义；信息边界清楚 | PASS |
| §3.1 P2，212–231 | 给 \(q,P,T,O,b,z,r\) 总合同并解释 predictive state | 机制→公式→性质 | PASS WITH REVISION：加 \(\alpha=1\)，明确 direct-per-h |
| §3.2 overview，235–239 | 给架构路线图并分开 inference/training | 路线图→边界 | PASS |
| History paragraph，241–253 | 描述 q/P、共享历史上下文和可移除 branch | 机制→性质；动机隐含 | PASS WITH REVISION：补 exact warm-start 身份，不要只写 q 初始化 |
| Transition P1，255–270 | 说明 future weather 驱动与 residual transition | 动机→机制→公式 | PASS WITH REVISION：区间记号与实际 prefix 对齐 |
| Transition P2，271–274 | 说明共享参数和 weather substitution interface | 性质/接口 | PASS |
| Closure P1，276–285 | 把 state 放到输出路径并给加法 | 动机→机制→公式 | MAJOR：`endpoint contribution` 改为 horizon-specific spatial contribution |
| Closure P2，286–288 | 限定 additive closure 的主张强度 | 性质/边界 | PASS |
| Future learning P1，292–300 | 说明 GT/KD/FS 三个目标的角色 | 要求→三个机制 | MAJOR：GT/KD 只有名称，无可复现定义 |
| Future learning P2，302–323 | 定义 terminal future-state target 和 cosine loss | 机制→公式→边界 | MAJOR：补 target input、初始化身份和 exact patch mask |
| Future learning P3，324–335 | 给 total loss 并区分 learning signal 与 Q2 evidence | 公式→性质/证据边界 | MAJOR：补 \(\lambda_s\) schedule、freeze path 和 selected checkpoint distinction |
| Interfaces overview，339–341 | 说明 post-training interface 的地位 | 要求/范围 | PASS |
| State-removal paragraph，343–348 | 定义 Q2 主干预和 load-bearing criterion | 机制→接口→可检验性质 | PASS |
| Weather-substitution paragraph，350–359 | 定义 Q3 substitution 和非因果边界 | 机制→接口→边界 | MAJOR：detectable/fidelity/weather-responsive 未分层；endpoint 用词错误 |

总体上，小节标题已经符合 AAAI 方法稿的层级，但 paragraph-level argument 仍有两个结构缺口：

1. Training 小节从角色说明直接跳到 FS 公式，GT/KD 没有形成平行的机制和公式；
2. Operational interface 小节定义了 “detectable”，却把通过判据留成模糊的 “observable endpoint”，导致 Method、Results 和 abstract 中的 “weather-responsive” 没有唯一逻辑入口。

## 11. AAAI 段落写法对照

本节使用 `METHOD_AAAI_WRITING_AUDIT.md` 已整理的近期 AAAI 方法论文作为写作锚点，不把它们当作 TerraState 技术证据。

| AAAI 写法原则 | 当前 TerraState | 推荐落实 |
|---|---|---|
| Problem Setting 先定义输入、状态、输出 | 已基本做到 | 保留 §3.1 的紧凑结构，不加入实验数字 |
| 总公式与图同构 | 公式接近，Figure 2 不同构 | 先修图的信息边界、transition operator 和 intervention location |
| latent state 与 observable equation 分开 | \(z\) transition 与 \(b+r\) 已分开 | 把 \(r_h\) 明确为 raster forecast contribution |
| 每模块采用要求→机制→公式→性质 | Transition/Closure 较好 | History 补目的；Training 为 GT/KD/FS 各建平行定义 |
| training-only branch 与 inference path 分开 | 文字正确 | 增加三种模型身份和 future-information table |
| 名称跟在可检验性质之后 | predictive state 基本做到 | weather-responsive 必须先给 detectable + fidelity 的操作定义 |
| 方法事实与结果主张分开 | Future-state loss 不等于 load-bearing 已明确 | 继续保留；不要把 target alignment 写成 non-collapse 证据 |
| 复现信息要精确但不淹没机制 | 当前 Implementation 数字多且 checkpoint-specific 事实错 | 主文写 selected checkpoint 的实际训练路径；完整 run curriculum 可放 checklist/appendix |

### 推荐的逐段骨架

1. **Problem formulation**：给定什么、预测什么、forecast-time 可用信息是什么。
2. **Predictive-state contract**：一组与图同构的 \(q\to P\to T\to O\) 方程；随后限定“operational”含义。
3. **History/state paragraph**：为什么需要共享 history pass → q/P 如何产生 \(b,z\) → state removal 为什么不改变 history。
4. **Transition paragraph**：为什么 future weather 必须有唯一入口 → prefix GRU/geo/time/fusion/residual update → direct-per-h 与 substitution interface。
5. **Closure paragraph**：为什么 state 必须处于 observable path → readout/unpatchify/addition → exact removal property。
6. **Training overview**：三个 objective 分别保护 observable skill、teacher behavior、future representation。
7. **GT/KD paragraph**：平行给 mask、aggregation 和 teacher access boundary。
8. **FS paragraph**：给 training-start frozen copy、target input、terminal patch mask 和 cosine loss。
9. **Schedule/checkpoint paragraph**：先给完整 curriculum，再明确所报告 boundary checkpoint 截止于 80%。
10. **Interventions paragraph**：Q2 primary state removal；\(T\!\to I\) supporting only；Q3 T-input substitution。
11. **Operational criteria paragraph**：detectable response、forecast-window fidelity、weather-responsive state 三层定义；最后写非因果边界。

## 12. 越界表述审计

| 主张/风险 | 当前稿状态 | 审计结论 |
|---|---|---|
| TerraState 是 world model | 使用 operational predictive-state world model，并在 Limitations 排除完整物理状态 | **支持，限于本文操作性定义** |
| predictive state 是 load-bearing | Q2 state removal 在 Val/OOD-t paired CI 均排除零 | **支持** |
| transition 对预测“必要” | \(T\!\to I\) 有正 effect，但 readout input OOD；`clean=false` | **只支持 involvement，不支持严格必要性或因果隔离** |
| weather input 影响 prediction behavior | 84 pairs 的替换 response 非零，prior 固定 | **支持** |
| actual weather 更忠实 | 两个 control 的 target-window loss difference primary CI 均为正 | **支持，但必须改为 forecast-window fidelity** |
| causal weather effect | 当前明确否认 | PASS；禁止升级 |
| counterfactual guarantee/correctness | 当前明确否认 | PASS；禁止升级 |
| composition/Q4 | 只在 related work/limitations 作为非核心事项 | PASS；不进入 Method 性质或 Figure 2 |
| non-collapse | 正文只把 collapse 作为一般失败模式，没有声称已证明 non-collapse | PASS；future-state variance/sanity 不能升级成核心 claim |
| SOTA/严格排名 | Table 1 分面且否认严格 cross-panel ranking | PASS |
| extreme-specific enhancement | 当前明确报告 interaction CI 跨零并否认 | PASS |
| backbone-agnostic | 当前未主张 | PASS；不要新增 |
| one-seed/training stability | 当前说明 one training run，不建立 stability | PASS |
| “正确预测方向” | 可由 control loss−actual loss \(>0\) 支持 | 仅限冻结匹配协议；不等于物理或因果方向 |

## 13. Critical / Major / Minor 问题

### Critical

C1. Q3 的 `endpoint loss/prediction/fidelity` 与冻结 evaluator 的完整 20-step target-window estimand 不符。影响摘要、引言、Method、Q3 question、Targets and metrics、Table 3 caption、Q3 Results、Limitations 和 Conclusion。

C2. Figure 2 Panel (a) 的边界和总箭头视觉上允许 future weather 进入 history encoder，违反实现的 exclusive weather route。

C3. 当前 Implementation 把完整 14,880-update run 与 final-20% \(q\) unfreeze 写成报告模型的实际训练经历；冻结结果使用的是 step 11,904、stage 2、pre-unfreeze checkpoint。

### Major

M1. Figure 2 Panel (c) 用乘法而不是真实 concat/fusion + residual transition。

M2. Figure 2 没有清楚显示 \(z_t\to T_\psi\)，也没有说明所有 horizon 从同一 \(z_t\) direct query。

M3. Figure 2 把 readout 后的 \(r_h\) 继续画成 state token，而代码输出是 unpatchified raster contribution。

M4. Figure 2 的 Q3 intervention 位置在视觉上像 transition 下游，真实替换发生在 transition 的 weather input。

M5. Method 没有给出 GT/KD 的精确 mask 与 aggregation；两者的 aggregation 实际不同。

M6. Future-state target 没有完整定义其输入、训练开始时冻结身份和全 patch clear mask。

M7. Method 没有说明全模型 warm start、\(\lambda_s\) schedule、freeze/unfreeze 和 selected checkpoint 实际路径。

M8. Method 没有定义 supporting \(T\!\to I\) diagnostic；Results 中直接出现。

M9. detectable response、forecast-window fidelity 和 weather-responsive predictive state 没有唯一、分层的定义。

M10. Q3 JSON 自身不内嵌 checkpoint/evaluator identity，当前关联依赖 release bundle；主张需保留 single-checkpoint/frozen-protocol 限定。

### Minor

m1. 公式省略固定 \(\alpha=1\)，使 `alpha=0` evaluator 的可追溯性较弱。

m2. `normalized mean` 应明确为 globally z-scored weather 的全零向量，不是地点/季节 climatology。

m3. `endpoint contribution`/“终点贡献”应改成 horizon-specific spatial forecast contribution。

m4. Figure 2 的 `D3 Vegetation forecast` 是无定义的内部式标签。

m5. Figure 2 raster tile 的来源/许可/匿名性需要单独 provenance 记录。

## 14. 最小修改清单

按阻断优先级执行：

1. 全文把 Q3 的 `endpoint loss/prediction/fidelity` 改为 `20-step target-window masked loss`、`forecast-window prediction` 和 `forecast-window response fidelity`；不要修改冻结数字。
2. 在 Q3 protocol 首次出现处定义：
   \[
   \Delta L=L_{\rm control,window}-L_{\rm actual,window};
   \]
   正值 favor actual；primary 判据是 donor 与 mean 的 geo-cluster CI 下界均 \(>0\)。
3. 改写 Implementation：完整 run 计划为 14,880 updates，但 Q1–Q3 checkpoint 为 step 11,904 的 boundary80、保存于 \(q\) 解冻前，实际 \(q\) 始终冻结。
4. 在 Method 明确 student 是从 exclusive MAIN-last **全模型** exact warm start；KD teacher 是独立 frozen Phase-I full-weather q；FS target 是 training-start student q/P frozen copy。
5. 为 GT、KD、FS 各给一条可复现公式或精确定义；写清 GT 与 KD aggregation 不同、FS patch 必须 terminal 4×4 fully clear 且含 vegetation。
6. 在 transition 段明确每个 horizon 从同一个 \(z_t\) 做一次 direct query，不是 recurrent rollout。
7. 在 closure 首式写 \(\alpha\equiv1\)，并把 `endpoint contribution` 改为 `horizon-specific spatial forecast contribution`。
8. 在 Method interfaces 中补 \(T\!\to I\) 是 supporting diagnostic only，且 readout input OOD。
9. 用 §6.5 的三层定义统一 detectable、fidelity 和 weather-responsive；继续明确非因果、非 counterfactual。
10. 作者按 §9 的 M1–M9 手动修 Figure 2；不得为了保留现图而改变正文的真实信息边界。

## 15. 最终判定

**BLOCKED**

当前 V2 代码、Q2 evaluator、Q3 weather substitution 和冻结结果之间总体一致，且能够支持以下受限论文主线：

- TerraState 保留有用的 OOD-t 预测能力；
- state-mediated contribution 在 validation 和 OOD-t 上是 load-bearing；
- 在冻结的 84-pair 协议中，未来天气替换会改变 state-mediated output，且 actual weather 在完整 20-step target window 上比 matched donor 和 normalized mean 两个 control 具有更低 loss；
- 这些结果不支持 causal effect、counterfactual correctness、composition、SOTA 或 extreme-specific enhancement。

但在修复 C1–C3 及 Figure 2 M1–M6 之前，当前候选稿仍会向读者传达错误的 Q3 estimand、错误的 future-information route 和错误的 evidence-checkpoint training history，因此不能判为 PASS WITH REVISION。完成最小修改清单并逐项回归核对后，可重新评估为 PASS。
