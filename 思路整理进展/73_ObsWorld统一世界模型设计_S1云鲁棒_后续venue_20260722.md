# AAA01 · ObsWorld 统一世界模型设计（acquisition-invariant + 云鲁棒 + 可控）— 后续 venue 旗舰计划

> 日期：2026-07-22　状态：**旗舰前向计划（3–6 个月，后续 venue）**
> 目标 venue：NeurIPS / CVPR EarthVision / ICLR-2027，或 RSE / ISPRS J.（强 EO 期刊）
> 关联：[[58_ObsWorld_AAAI27中文论文终稿_主实验冻结版_20260717]]、[[69_ObsWorld_官方EarthNetScore对标_published_vs_ours_20260722]]
> 一句话：**方向对、时间线错**——把"世界模型 + 能赢的 SOTA"放到这里，在这里**把胜利挣来，而不是宣称出来**。

---

## 0. 为什么换轴（本计划存在的理由）

当前 Stage2 在 **clear-sky NDVI / EarthNetScore** 这根轴上：R² 0.524 < Contextformer 0.62、官方 ENS 低于 Persistence(0.26)。这根轴由专用小模型（6M Contextformer）结构性占优，**28M 大半冻结的世界模型在此争 SOTA = 自杀**。把广谱世界模型压成单数据集单指标跑分，是**双输**（丢广度 + 输窄轨）。

**破局 = 换到一根 SSL4EO/φ/S1 说了算、且我们天生占优的轴：S1(SAR) 云鲁棒预测。** 光学在云下无信号，雷达穿云——"技能随云量退化更平 / 高云量处反超(crossover)"是一个**新的、有物理动机、可量化的 SOTA 声明**，且只有具备 S1+跨模态预训练的模型能拿。

---

## 1. 核心理论：一个方程组，锁死 SSL4EO/φ/S1

不要把三者当三个独立选择分别辩护（那是审稿人的攻击口）。把它们锁进同一个**结构化隐变量 / POMDP 观测模型**：

**观测模型**
$$ y_t = R(s_t;\ \varphi_t)\ \odot\ M_t\ +\ \varepsilon $$
- `s_t`：**acquisition-invariant 潜在地表状态**（世界模型要预测的真正对象）
- `φ_t`：采集条件（太阳天顶/方位角、轨道 ASC/DESC、平台、DOY、视角）——**噪声/控制变量**
- `R`：受 φ 调制的渲染算子；S1、S2 是**同一个 s 的两个渲染通道** `R_S1, R_S2`
- `M_t`：云遮挡掩码；`ε`：传感器噪声

**动态**
$$ s_{t+1} = F(s_t,\ w_t),\quad w_t = \text{physical4 天气驱动} $$
（已执行的 5 天匹配控制转移；Direct 与 Rollout 是同一个 F 的两个积分器。）

**推断**
$$ q(s_t \mid y_t,\ \varphi_t)\quad \text{（FiLM 条件化 φ，把"采集引起的外观变化"explain away，而非吸收进 s）} $$

> 理论边界（必须诚实标注）：φ 分离 s 属于**非线性 ICA / 解耦**问题——单视角不可辨识，但在"给定调制噪声的辅助变量"下**motivated by** Hyvärinen 辅助变量可辨识性。其假设（条件指数族、φ 充分变化）在此**无法可验证地成立**，故**永远当动机引用，绝不当保证**。

---

## 2. 三个成分为什么各自 load-bearing（每个绑一个分数）

| 成分 | 为什么必需 | 绑定的可量化分数 |
|---|---|---|
| **SSL4EO-S12** | 采集不变的全球地表先验，只能从跨广 φ 变化与地理、配对 S1+S2、多季节的大规模语料学到 | label-efficiency 曲线（1%/10%/100%）+ OOD-region transfer + invariance 优势 |
| **φ（FiLM 条件）** | 可辨识性核心：把 s 与采集因素分离；两条腿供给——(a) 已知条件信号监督 FiLM，(b) 同一状态在不同 φ 下的多次观测 | invariance metric（带充分性约束）+ controllability metric（vs 解析光照基线）|
| **S1（SAR）** | 云鲁棒性是**推论**：云让 `R_S2` 不可逆（遮挡），`R_S1` 云无关，故光学被遮时 s 仍从雷达通道可辨识 | 技能 vs 云量退化斜率 / crossover（对 S1-equipped 基线成立）|

**关键：每个成分都被一个方程位置 + 一个分数绑死**，审稿人"为什么要它"的问题就有了可证伪的答案，而不是"预训练民俗"式的口头辩护。

---

## 3. 可赢的 SOTA 轴

### 3.1 Headline：S1 云鲁棒预测（主赢牌）
- 声明：**在高云量/遮挡条件下，ObsWorld 因融合 S1 而维持预测技能，纯光学方法崩溃**——退化斜率更平、在高云量处 crossover 反超。
- 这是一个**换轴的、有物理动机的 SOTA**，不是在 Contextformer 的 clear-sky 轴上硬拼。

### 3.2 次要：φ 可控反渲染（靠"唯一性"，非"打赢基线"）
- 把 Stage1.5 的 φ 接进 Stage2 解码器；推理时改变 φ（太阳角/传感器），量测输出是否按**解析光照方向**正确响应；且固定场景在两个真实采集几何下 s 是否坍缩到同一点。
- 这是**别人没有的世界模型能力**，一个可以"first"的轴。

---

## 4. 完整实验设计 E6–E10（后续 venue，heavy）

| 编号 | 内容 | 成本 | 通过条件 |
|---|---|---|---|
| **E6/E7** | **S1 云鲁棒预测**：Sentinel-1 GRD(VV/VH) 与 EarthNet/GreenEarthNet minicube 的 footprint+时间对齐，激活已存在但冻结的 `s1_proj`，重训 Stage2，按上下文云量分层评测 | **heavy（数周数据工程 + 重训）**，make-or-break | 对 **S1-equipped 基线 + S1-persistence** 仍有真 crossover |
| **E8** | 消融 (-S1)/(-SSL4EO)/(-φ FiLM) | one-train each | 云鲁棒胜利在 (-S1) 消失、(-SSL4EO) 退化 → 证明 load-bearing |
| **E9** | φ 可控反渲染 + invariance（带充分性约束 + 解析光照基线） | one-train | 响应符合解析方向；固定场景不同 φ 下 s 坍缩 |
| **E10** | 多任务广度探针（forecasting + segmentation + change-detection + cloud-removal）+ label-efficiency 曲线 | heavy | 单个冻结 s 服务多任务；低标注下 SSL 明显占优 |

---

## 5. 三个必须内置的纠错（否则后续 venue 重蹈覆辙）

1. **S1 的胜利必须打赢 S1-equipped 基线 + S1-persistence**，不能只打被你没收 S1 的光学-only 对手。"没收对手武器后的胜利"不算 SOTA。
2. **打分变量要对齐 SAR 真正有信息的通道**（土壤水分、冠层结构、洪水/扰动，或 SAR 锚定的状态 gap-fill），**不是纯 NDVI 绿度**（SAR 后向散射与绿度弱耦合）。**crossover 必须是真反超**（高云量处 ObsWorld 超过对手），不是从"到处最差"的低地板上量一条平斜率。
3. **φ 不变性必须带充分性约束**（常函数完美不变但没用——不变性不带"状态仍须预测地表变化"就是空的）；**可控性必须打赢解析 BRDF/辐射传输基线**，否则是 party trick 不是 capability。

---

## 6. 逐条审稿人应答（换轴后可辩护）

- **Q「为什么 SSL4EO？」** 贡献是**可复用的采集解耦地表状态表征**；SSL4EO-S12 是唯一大规模、配对 S1+S2、带采集元数据的语料。预测只是众多探针之一。（前提：展示了 E10 的 multi-task transfer + label-efficiency）
- **Q「φ 干什么？」** 把 s 与采集分离，使**同一状态在不同 φ 下正确渲染**；由 E9 的 controllability 分数兑现。（在纯诊断/当前版本里，如实披露 Stage2 用 neutral φ = limitation）
- **Q「为什么 S1？」** 状态必须在光学失效（云）时仍可辨识 → 雷达融合；由 E6/E7 的云鲁棒 crossover 兑现。
- **Q「为什么不坍缩成单跑分？」** 世界模型的价值是**广度 + 鲁棒性**，单个准确率数字结构性无法展示；故换轴到云鲁棒/可控/多任务，clear-sky NDVI 明确不是我们的轴。

---

## 7. 诚实赔率 + 时间线

- **后续 venue 接收率（有条件）**：E6/E7 crossover 真实 **且** E10/E4 预训练 gap 真实 ⇒ **~45–55%**；任一为空 ⇒ **~15–25%**。
- 诚实定性：即便成功，这也是"**self-defined-axis / 模态优势**"的胜利，novelty 中等、可辩护但非碾压；新意主要由世界模型侧（可辨识性、可控反渲染）承载，而非那个云鲁棒准确率数字本身。
- **里程碑**（3–6 个月）：
  - M1（3–4 周）：S1×EarthNet 时空对齐数据集冻结（**make-or-break，先做**）
  - M2（+3 周）：激活 s1_proj、重训 Stage2、云量分层评测出 E6/E7 首个 crossover 信号 → **go/no-go**
  - M3（+3 周）：E8 消融 + E9 可控性
  - M4（+4 周）：E10 多任务 + label-efficiency + 写作

---

## 8. 与当前 AAAI-27 诊断文的关系（复用/延期）

- **复用进 AAAI-27（诊断文）**：Direct-vs-Rollout 匹配控制（带"排序跨评测栈不 robust"caveat）、官方 IID/OOD ENS 诚实定位、修正版 φ-probe、（若跑）frozen-vs-finetune 消融。
- **延期到本计划**：S1 云鲁棒、φ 可控、多任务广度——这些才是"世界模型 + 可赢 SOTA"的承重件，**6 天内无法诚实落地**。

---

## 9. 数据工程清单（S1 对齐 = 整条路线 make-or-break）

- EarthNet2021x **不含 SAR** → 需从 Sentinel-1 GRD 按 minicube footprint + 时间窗对齐（重访、几何校正、VV/VH、ASC/DESC 轨道标注 = φ 的一部分）
- 复用已存在但冻结的 `s1_proj`（models 里）+ Stage1.5 的双模态编码器 `MultiModalViTEncoderFiLM`
- 云量分层需要可靠云掩膜（GreenEarthNet 已升级云 mask，可借）
- 每一步保留 provenance（manifest/SHA/config），沿用 69 号的严格纪律

---

## 10. 禁用词（沿用并强化）

- 禁：SOTA（除非在**同协议、对 S1-equipped 基线**成立）/ 因果 / digital twin / real-time φ（当前未接）/ "FiLM 已实现 φ 解耦"（未判定）/ first neural data assimilation
- φ-leakage 旧 67–71% / 64.8→70.7% 数字**作废**（5 个 bug，见 58 号附录 B.2），只能用修正版 probe。

---

## 附：一句话总方针
> **换到 S1 云鲁棒这根你天生占优、SSL4EO/φ/S1 都承重的轴上当第一**；用一个方程组给三个成分各绑一个分数，给出诚实的审稿人应答；把胜利在后续 venue **挣来而非宣称**，并且只在对 S1-equipped 基线成立、φ 指标带充分性约束和解析基线的前提下宣称。
