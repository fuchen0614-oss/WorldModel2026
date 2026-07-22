# 79 · 现实核查（阻断）：Stage1.8 / Table 2（L1C/L2A 因子化）数据+代码双缺 —— 需你决策

> 写于 2026-07-22。**状态：已亲自核实（不是推测）。这是威胁 76 号冻结叙事的问题，列为醒来第一优先级。**
> 我**没有**改动任何"锁死"的东西（摘要、叙事主线）。本文档只陈述核实事实 + 给选项 + 我的建议。**决策权在你。**

> 🔴 **重大修正（2026-07-22，来自 Plan B 共享 memory）**：本文"L1C/L2A 数据没了"是**本地机 `/csy-mix02` 未挂载的假象**。**服务器上 `SSL4EO-S12-v1.1/train` 同时有 `S2L1C` 和 `S2L2A`（+S1GRD/DEM/LULC/NDVI/S2RGB）→ 真·L1C/L2A 因子化在服务器上可行**（下面的"选项 B 放期刊版"结论作废）。仍缺的是**因子化代码**（loader/loss/renderer/eval 全需新写）+ 一个小 Stage2v3 训练/评测。故 Table 2 现在是"数据已备、代码待写"，不是"数据没了"。等 S1a 的 R²/RMSE 出来后一并重排优先级。

---

## 1. 核实到的硬事实（both 子代理 + 我亲手 bash 复核）

**代码侧：Stage1.8 / L1C/L2A 因子化 = 几乎从零。**
- 计划文档（74/75/76）里引用的这些文件**全部不存在**：
  `configs/train/plan_a_stage1_8_factorize.yaml`、`scripts/train_stage1_8_factorize.sh`、`models/losses/obsworld_v3.py`（`L_paired_state`/`L_cross_render`）、`eval/eval_factorization.py`（Table 2 评测器）。
- 全代码库无 `factoriz`/`cross_render`/`paired_state`/`TOA`/`BOA`/`atmospheric` 逻辑。
- 只有 `S2L1C` 作为**模态字符串**出现在枚举里（`data/datasets/ssl4eo.py:115` 等），但**从未接到 loader / 归一化 / 数据**；`normalize_image` 只有 L2A/RGB/S1 分支，无 L1C。
- "dual" 配对 loader（`ssl4eo_dual.py`）配的是 **S1GRD+S2L2A**，不是 L1C/L2A。

**数据侧：L1C/L2A 配对数据在本机完全不可达（我亲手确认）。**
- `/csy-mix02` **未挂载**（`ls /csy-mix02` → No such file or directory）。配置里所有数据根（`/csy-mix02/cog8/zjliu17/Agent/TrainData/...`）本机都不解析。
- 本机可达 TrainData **只有** `/mnt/data/users/luzheng/workspace/iclr/czj/TrainData/EarthNet2021`。
- 全盘（`/mnt/data/users/luzheng`、`/mnt/public_data`）未找到任何 `*ssl4eo*`/`*l1c*`/`*l2a*` 目录。
- 子代理还指出：即便当年挂载过 SSL4EO，历史文档只提 **S2L2A + S1GRD** 分片被处理过，**没有证据 S2L1C 分片曾被下载/处理**。

**历史一致性：** 更早的 `思路整理进展/45_...20260715.md` 明确写过 **"L1C 放截稿后"、"SSL4EO S2L1C AAAI-27 不下"**——即曾**主动推迟**。76 号摘要又把它写回核心。**计划在这点上反复过。**

→ **净结论**：在 07-28 截稿前，要做出 Table 2（真·L1C/L2A 因子化），需要同时：(a) 重挂 SSL4EO blob 且**首次**下载/处理 L1C 分片（13 band，本就没下过），(b) 写全套 loader+loss+renderer+eval 新代码，(c) 还要在已被 S1a/S1b 占用的 GPU 上再训一个阶段。**这在 6 天内、与 S1a/S1b 并行，几乎不现实。**

---

## 2. 为什么这件事重要（对 76 冻结叙事的冲击）

- 76 号**冻结摘要**核心句："we learn it from **paired Sentinel-2 products (L1C/L2A)**"——这是"observation-aware"主张的**具体实验支撑**。
- 76 §2："φ 的必要性由 SSL4EO **cross-render + no-φ 对照**验证"、"SSL4EO 解 observation identifiability"。
- 76 §7 幸好留了后门："world model 主张由**机制实验**承担…**即便精度只到有竞争力，叙事仍完整**"——但那是针对**精度**解耦，不是针对"Table 2 直接做不出来"。**若 Table 2 缺席，则'observation-aware / 产品因子化'这条支柱失去实验**，只剩 Table 3（状态复用）+ latent 一致性扛世界模型主张。

**这不是可以糊过去的**——审稿人会直接问"你说 observation-aware 靠 L1C/L2A，实验在哪"。所以必须现在决策，而不是等写作时才发现。

---

## 3. 三个选项（供你决策；我不擅自定）

### 选项 A（**推荐**，deadline 可行）：把 φ 重定义为**可得的采集条件**，做"可运行版 Table 2"
- 不需要任何 L1C/L2A 外部数据。用**已存在**的成像条件 φ 机器（`PureImagingConditionEncoder`：季节/太阳角/SAR 几何/云——Stage1.5 已训）作为"观测条件"。
- 具体实验：EarthNet 同一 minicube 的不同帧本就有**不同采集条件 φ**（太阳角/季节随时间变）。做 **cross-render**：把状态在"自身 φ" vs "另一帧 φ"下渲染，比较；再做 **no-φ 对照**。→ 一个**真能跑、无需新数据**的观测因子化 Table 2。
- 代价：写一个小 eval（复用现成 φ+FiLM+decoder 机器），**无需新训练数据**。
- **叙事代价（必须你点头）**：摘要那句 "paired L1C/L2A" 要**软化**为 "observation/acquisition conditions"。这**触碰了"锁死"的摘要一句**——76 说"永不再变"，所以**只有你能决定**。好在 76 §2 对 φ 的总定义本就是"观测产品/处理/**采集**条件"，L1C/L2A 只是"最小版"，所以软化仍在叙事既定范围内，不算推翻主线。

### 选项 B（高风险，可能来不及）：真做 L1C/L2A
- 重挂 SSL4EO → 首次下载+处理 S2L1C 分片 → 写全套因子化代码 → 再训一个阶段。
- 现实评估：数据是否还能挂上未知；L1C 从没下过；6 天内与 S1a/S1b 抢 GPU。**大概率赶不上截稿**，适合放"扩展版/期刊版"。

### 选项 C（最保守）：Table 2 降级为 limitation/future work
- 世界模型主张只靠 **Table 3（状态复用 + 冻结读出）+ direct/composed latent 一致性**。摘要删 L1C/L2A 句，明确把产品因子化列为 future work。
- 代价：观测感知支柱变弱（只剩 Table 3 扛），但**诚实、零数据风险**。同样需你改摘要。

---

## 4. 我的建议
**选项 A**：它在截稿前**能真跑出一个观测因子化实验**（保住"observation-aware"这条支柱不落空），只需小 eval、零新数据，且落在 76 对 φ 的既定定义内。唯一代价是摘要一句从 "L1C/L2A" 软化为 "observation/acquisition conditions"——**这需要你明确授权改那一句**（我不擅自动锁死内容）。
若你坚持 L1C/L2A 的具体卖点 → 选项 B 放期刊版，AAAI 版走选项 A 的采集条件因子化 + 在 limitation 里点名 L1C/L2A 为后续。

---

## 5. 我没做的事（守约束）
- **没**改摘要、没改 76/叙事任何一字。
- **没**新建 Stage1.8 代码/数据（既然数据不可达、且要动叙事，先等你决策）。
- 只：核实事实 + 写本文档 + 在 doc 78 论文草稿里把 Table 2 标为 `[TBD—侦察中]`（现应据本文更新为"数据+代码阻断，待决策"）。

---

## 6. 醒来待办（与 doc 77 §8 合并决策）
1. Table 2 走 A / B / C？（A 需授权软化摘要一句。）
2. 若走 A：我立刻写 `eval/eval_factorization.py`（采集条件 cross-render + no-φ），复用现成 φ/decoder，无需新数据。
3. 对应更新 doc 78 论文 Method 3.6（paired-state → 采集条件因子化）与 Setup。
