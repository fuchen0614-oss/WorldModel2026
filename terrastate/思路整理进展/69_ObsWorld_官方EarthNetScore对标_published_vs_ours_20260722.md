# 官方 EarthNetScore 精度对标追踪：published vs ours

> [!warning] 勘误 (2026-07-22，采纳用户审计，8 条全部成立)
> 本 MD 早期版本有多处过强/不准确表述，逐条更正如下，正文相关结论以此为准：
> 1. **Extreme/Seasonal 不是官方轨道结果**。官方协议 IID/OOD=10→20、Extreme=20→40、Seasonal=70→140；本代码硬编码 10→20 并截断前 30 帧（`earthnet2021.py:682/735`、`obsworld_factory.py:179` 已核实）。故 extreme 0.061 / seasonal 0.109 只能叫"这些目录上的 10→20 截断诊断"，**不能与官方 Extreme/Seasonal 比较**；"Rollout 四划分全胜 Direct"收缩为"在 4 个本地评测切片上点估计更高（IID/OOD 官方协议，Extreme/Seasonal 为截断诊断）"。
> 2. **原 5.B 的 Earthformer/PredRNN ENS 来源不成立**：Earthformer(NeurIPS'22) 无 EarthNet2021 实验。正确可核验值取自 EarthNet2021 原论文 Table 1 + 补充 Table 3（见下 §1.A）。
> 3. **EarthNet2021 ≠ EarthNet2021x 测试集**：原论文 IID/OOD 为 4219/4214，本地 4205/4202。已发表值只作 "published reference"，严格"是否过 persistence"以本地同 manifest 全量 persistence 为准（我们 0.15 < 本地 persistence 0.209，成立）。
> 4. **smoke16 不能验证 persistence=0.248**：该表述过强，已由全量 persistence(iid 0.209) 取代。~~inline scorer 与官方目录 `get_ENS` 的 parity 仍未做~~ → **✅ 2026-07-21 parity 已做，通过**（见 §1.B-parity）：同一批 cube 两个打分器最大分量差 4e-4、ENS 差 7e-5，inline 累加器是官方 `EarthNetScore.get_ENS` 的忠实复刻，故 0.15 / 0.209 是可信 ENS、**不会因换官方打分器而变**。残留开放项只剩"帧协议"（第1条 extreme/seasonal 截断），非打分器层面。
> 5. **GreenEarthNet "险胜 Earthformer" 违反自定规则**：0.524−0.52=0.004<0.005，应为"≈平"；且对手仅两位小数，不能据四舍五入判胜负。
> 6. **"0/4 SOTA" 非科学表述**：Earthformer/PredRNN/SimVP 是 published learned baselines，唯 Contextformer 为该表最强；正文应报精确指标+差值+置信区间，不以"击败数量"为核心统计量。
> 7. **"协议/指标反转" 降级**：两次比较同时变了指标、数据版本、split、target、mask、聚合，混淆无法拆开；只能说"Direct/Rollout 的汇总排序在两套评测栈下发生变化"，不能归因于"指标"。
> 8. **过度平滑是假设、非已证根因，且不是对 ENS 的有效批评**：低 MAE 也可能来自均值化/模糊；空间结构本就是预测质量的一部分。安全表述："SSIM 是当前 ENS 主要瓶颈，结果与空间过度平滑假设一致；仍需频谱/边缘能量、时间方差、定性轨迹进一步验证。"

## §1.A 官方 EarthNet2021 ENS 已发表参考值（用户核验，来源：EarthNet2021 原论文 Table 1 + 补充 Table 3）

| Split | Persistence | Channel-U-Net | Arcon | 我们最好 |
|---|---:|---:|---:|---:|
| IID | 0.2625 | 0.2902 | 0.2803 | 0.1500 |
| OOD | 0.2587 | 0.2854 | 0.2655 | 0.1231 |
| Extreme | 0.1939 | 0.2364 | 0.2215 | 0.0612* |
| Seasonal | 0.2676 | 0.1955 | 0.1587 | 0.1092* |

\* Extreme/Seasonal 因时间协议不同（我们是 10→20 截断诊断，官方是 20→40 / 70→140），**不能直接比较**。IID/OOD 时间协议相同，但样本集非严格同清单，故为 published reference。

## §1.B-parity 打分器一致性核验（2026-07-21，关闭审计第4条）

脚本：`eval/parity_inline_vs_official_ens.py`（env `.conda/envs/WorldModel`）。方法：自造 8 个 128×128×4×20 cube（含 cloud mask，预测覆盖 perfect/persistence/blur+noise 三档，使 4 分量非退化），**同一批数组**分别过 ① inline `EarthNetScoreAccumulator` 与 ② 官方 `earthnet.parallel_score.EarthNetScore.get_ENS`（NPZ 目录、`n_workers=0`），逐分量比对。

| 分量 | inline | 官方 get_ENS | 绝对差 |
|---|---:|---:|---:|
| ENS | 0.409313 | 0.409386 | 7.4e-05 |
| MAD | 0.477394 | 0.477792 | 4.0e-04 |
| OLS | 0.446895 | 0.446895 | 3.7e-07 |
| EMD | 0.360454 | 0.360454 | 0 |
| SSIM | 0.375117 | 0.375119 | 2.5e-06 |

**结论**：最大分量差 4e-4（MAD，中位数算子对 float32/resize no-op 的敏感），ENS 差 7e-5，均远小于第二位小数。inline 与官方**聚合方式一致**（每 cube 四分量 → 跨 cube `nanmean` → 谐波平均，`summarize()` 476–482 ≡ `compute()` 94–100）、**分量函数同源**（直接调 `CubeCalculator`）、**NDVI/裁剪一致**。故 `officialENS_run1` 的 0.15（ours）/0.209（persistence）是可信 ENS，换官方目录打分器不改变数值与"我们<persistence、胜 SOTA=0"的方向。

> ⚠️ 本核验只证"打分器适配器忠实"，**不证**帧协议正确（extreme/seasonal 仍是 10→20 截断，第1条）；也未在 model output≠128 的分辨率下测（run1 中 target=128、模型输出 128，resize 为 no-op，具代表性）。

> 以下早期章节（§1–§6）保留作过程记录，但凡与上面勘误冲突处，一律以勘误为准。

> 日期：2026-07-22　状态：**进行中**（本地官方 ENS 全量评测运行中；published ENS 检索中）
> 目的：用**官方 EarthNet2021 协议 + 官方 EarthNetScore (ENS)** 给 ObsWorld 的 Direct-P4 / Rollout-P4 建立一张"别人已发表精度 vs 我们本地实测精度"的对标表，作为主表协议选择（EarthNet2021 ENS vs GreenEarthNet R²）的依据。
> 关联：[[58_ObsWorld_AAAI27中文论文终稿_主实验冻结版_20260717]]、[[67_ObsWorld_核心叙事_相关工作差异_Table1数值与下一步_20260719]]

---

## 0. 两套协议不可混（load-bearing）

| 协议 | 数据 | 划分 | 官方指标 | 谁在用 |
|---|---|---|---|---|
| **EarthNet2021 (原版)** | EarthNet2021 / EarthNet2021x | iid / ood / extreme / seasonal | **ENS**（MAD·OLS·EMD·SSIM 的谐波平均，均∈[0,1]，越高越好） | 2021–2022 一代方法、官方挑战赛排行榜 |
| **GreenEarthNet (Benson CVPR24)** | GreenEarthNet | val/iid/ood-t/ood-s/ood-st `_chopped` | **veg R²/RMSE/NSE/bias/Outperf/RMSE25**（基于 NDVI） | Contextformer / EO-WM / VegSim 等新方法 |

> ⚠️ ENS ≠ R²/RMSE，两表**永不混列**。我们此前主表建在 GreenEarthNet OOD-t（跨协议、劣势），本 MD 是要看回到 EarthNet2021 ENS "主场"后我们到底站在哪。

> ⚠️ **ENS 的 SSIM 子分有内置幂次缩放**（官方 `parallel_score.py`：`ssim = ssim ** 10.319`，注释"Scales SSIM=0.8 down to 0.1"）。所以 SSIM 子分天然很低（原始 SSIM 0.75 → 子分 ≈0.05），**不是 bug**；ENS 数值整体偏小是协议特性，只能和同协议 ENS 比，不能和直觉中的"相似度百分比"比。

---

## 1. 别人已发表精度（可直接引用，不复现）

### 1.A 官方 EarthNet2021 ENS（iid/ood/extreme/seasonal）— **检索中**

> 来源目标：EarthNet2021 原论文（Requena-Mesa CVPRW 2021, arXiv:2104.10066）+ earthnet.tech 排行榜 + 后续复现论文。填入时每行标注 method / split / ENS / MAD / OLS / EMD / SSIM / 来源URL / 置信度。

| 方法 | split | ENS | MAD | OLS | EMD | SSIM | 来源 | 置信度 |
|---|---|---|---|---|---|---|---|---|
| 【待检索工作流回填】 | | | | | | | | |

### 1.B GreenEarthNet OOD-t 已发表值（Benson et al., CVPR 2024, Table 2；仅作 R²/RMSE 参考，不与 ENS 混）

| 方法 | R²↑ | RMSE↓ | NSE↑ | \|bias\|↓ | Outperf↑ | RMSE25↓ | Params | 来源 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Persistence | 0.00 | 0.23 | -1.28 | 0.17 | 21.8% | 0.09 | 0 | Benson CVPR24 T2 |
| Previous year | 0.56 | 0.20 | -0.40 | 0.14 | 19.3% | 0.18 | 0 | Benson CVPR24 T2 |
| Climatology | 0.58 | 0.18 | -0.34 | 0.13 | — | 0.16 | 0 | Benson CVPR24 T2 |
| Earthformer | 0.52 | 0.16 | -0.13 | 0.10 | 56.5% | 0.09 | 60.6M | Benson CVPR24 T2 |
| PredRNN | 0.62 | 0.15 | 0.03 | 0.10 | 64.7% | 0.10 | 1.4M | Benson CVPR24 T2 |
| SimVP | 0.60 | 0.15 | 0.03 | 0.09 | 64.1% | 0.10 | 6.6M | Benson CVPR24 T2 |
| Contextformer | 0.62 | 0.14 | 0.09 | 0.09 | 66.8% | 0.08 | 6.1M | Benson CVPR24 T2 |

---

## 2. 我们的精度（本地实测）

### 2.A 官方 EarthNet2021 ENS — 本地实测（run1, seed42, checkpoint_best）

评测器：`eval/eval_stage2_earthnet.py --official-score`（内部调用官方 `earthnet==0.3.9` 的 `parallel_score.CubeCalculator` 算 MAD/OLS/EMD/SSIM，谐波平均得 ENS）。数据：`TrainData/EarthNet2021/earthnet2021x`，manifest = physical4_v1 协议冻结清单。

| 模型 | split | N | ENS | MAD | OLS | EMD | SSIM | 状态 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Direct-P4 | iid | 4205 | 0.1410 | 0.2386 | 0.3422 | 0.2373 | 0.0587 | full ✅ |
| Rollout-P4 | iid | 4205 | **0.1500** | 0.2406 | 0.3384 | 0.2375 | 0.0652 | full ✅ |
| Direct-P4 | ood | 4202 | 0.1157 | 0.2305 | 0.3427 | 0.2384 | 0.0433 | full ✅ |
| Rollout-P4 | ood | 4202 | **0.1231** | 0.2310 | 0.3421 | 0.2414 | 0.0474 | full ✅ |
| Direct-P4 | extreme | 3972 | 0.0589 | 0.1978 | 0.2718 | 0.1530 | 0.0190 | full ✅ |
| Rollout-P4 | extreme | 3972 | **0.0612** | 0.2031 | 0.2718 | 0.1584 | 0.0198 | full ✅ |
| Direct-P4 | seasonal | 3880 | 0.1060 | 0.2269 | 0.3912 | 0.2320 | 0.0378 | full ✅ |
| Rollout-P4 | seasonal | 3880 | **0.1092** | 0.2263 | 0.3850 | 0.2353 | 0.0395 | full ✅ |

> **全量观察（4 划分 × ~4000 样本）**：官方 ENS 上 **Rollout ≥ Direct 在全部 4 个划分上都成立**（iid 0.1500>0.1410, ood 0.1231>0.1157, extreme 0.0612>0.0589, seasonal 0.1092>0.1060），与 GreenEarthNet OOD-t 上"Direct 全指标更好"**方向相反**。即 Direct-vs-Rollout 的胜负**依赖评测协议/指标**。
>
> ⚠️ **诚实注意 1（margin 小 + SSIM 非线性）**：ENS 上 Rollout 的优势 margin 很小（iid ~6% 相对），且部分被 SSIM 的 `x^10.3` 非线性放大——底层原始 SSIM 差异极小；但 MAD（RGBN 像素、线性）在 iid 上也是 Rollout 略优，所以不纯是 SSIM 假象。是否显著需配对 bootstrap。
>
> ⚠️ **诚实注意 2（绝对值仍低）**：我们最好的 ENS≈0.15（iid），预计仍**低于** EarthNet2021 排行榜（persistence ENS≈0.26、学习方法≈0.28–0.33，待检索确认）。原因同一个：ENS 重奖结构锐利度（SSIM），而我们预测偏平滑（过度平滑）。skill_vs_persistence 为正是 RGBN-MAE 口径（我们时序更准），与 ENS 口径不同，不矛盾。

### 2.B GreenEarthNet OOD-t — 本地已算（doc 58 冻结值，单 seed，provisional）

| 模型 | R²↑ | RMSE↓ | NSE↑ | \|bias\|↓ | RMSE25↓ | Params | 来源 |
|---|---:|---:|---:|---:|---:|---:|---|
| Direct-P4 | 0.524 | 0.178 | -0.415 | 0.126 | 0.126 | 28.17M | `evaluations/greenearthnet_oodt_20260719_214234/direct-p4` |
| Rollout-P4 | 0.504 | 0.184 | -0.476 | 0.131 | 0.128 | 28.17M | `evaluations/greenearthnet_oodt_20260719_214234/rollout-p4` |

---

## 3. 可引用 / 不可引用 判定

- ✅ **可直接引用**：官方 EarthNet2021 排行榜/论文的 ENS 值（1.A）——正文写明"官方 EarthNet2021 协议已发表值"，不自己复现别人模型。
- ✅ **可直接引用**：Benson CVPR24 Table 2 的 GreenEarthNet R²/RMSE（1.B）——但只与我们的 GreenEarthNet 行同表比。
- ⚠️ **不可同表**：把我们的 ENS(2.A) 与别人的 R²/RMSE(1.B) 放一起；或把 val_dev 的 RGBN-MAE 塞进 ENS/R² 列。
- ⚠️ **注意可比性**：新方法（Contextformer/EO-WM/VegSim）**不报 ENS**，所以"官方 ENS 表"里能同表比的多是 2021–2022 一代方法；"在 ENS 上好看"≠"赢了 Contextformer"。

---

## 4. 复现信息（provenance）

- checkpoint：`checkpoints_pulled/{direct-p4,rollout-p4}/checkpoint_best.pt`
  - Direct SHA256 `1158ffe6…f91d2`；Rollout SHA256 `8908c62e…ad31`（doc 58）
- config：`configs/train/stage2_earthnet_v2_{direct,rollout}_physical4.yaml`（契约校验 `matches: true`）
- conditioning stats：`artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048/conditioning_stats_physical4_v1_train_dev.json`
- manifest：同目录 `iid.json` (4205) / `ood.json` (4202)
- 评测器：`eval/eval_stage2_earthnet.py --official-score` → 官方 `earthnet==0.3.9`
- 输出：`evaluations/officialENS_run1/{direct-p4,rollout-p4}/{iid,ood}.json`
- **待补 parity**：最终论文数应再用 `eval/score_earthnet_prediction_dir.py`（官方 `EarthNetScore.get_ENS` over 导出的预测目录）交叉核验 inline accumulator 的一致性。

---

## 5. SOTA 胜负计分板（win/loss scoreboard）

> 规则：以"我们的最好模型"对每个已发表方法逐指标判胜负（R² 高者胜 / RMSE 低者胜 / ENS 高者胜）；差距 <0.005 记为"≈平"。**SOTA = 已发表的强学习方法**（非 Persistence/Climatology/Previous-year 这类基线）。

### 5.A GreenEarthNet OOD-t（已知，doc 58 冻结值，单 seed provisional）

我们最好模型 = **Direct-P4**：R²=0.524, RMSE=0.178, NSE=-0.415, |bias|=0.126, RMSE25=0.126。

| 对手 | 类型 | 对手 R² | R²胜负 | 对手 RMSE | RMSE胜负 | 综合 |
|---|---|---:|:--:|---:|:--:|---|
| Persistence | 基线 | 0.00 | ✅赢 | 0.23 | ✅赢 | 赢 |
| Previous year | 基线 | 0.56 | ❌输 | 0.20 | ✅赢 | 互有 |
| Climatology | 基线 | 0.58 | ❌输 | 0.18 | ≈平 | 输/平 |
| Earthformer | **SOTA** | 0.52 | ✅赢(险) | 0.16 | ❌输 | 互有 |
| PredRNN | **SOTA** | 0.62 | ❌输 | 0.15 | ❌输 | **输** |
| SimVP | **SOTA** | 0.60 | ❌输 | 0.15 | ❌输 | **输** |
| **Contextformer**（该赛道 SOTA） | **SOTA** | 0.62 | ❌输 | 0.14 | ❌输 | **输** |

**GreenEarthNet OOD-t 战绩（Direct-P4）**：
- 对 **4 个 SOTA**（Earthformer/PredRNN/SimVP/Contextformer）：**仅在 R² 上险胜 Earthformer 1 项，其余全输**；对真正 SOTA 的 Contextformer 及强基线 PredRNN/SimVP **全指标落败**。
- 对 3 个非学习基线：赢 Persistence，与 Previous-year/Climatology 互有胜负。
- ⚠️ 诚实结论：**在 GreenEarthNet OOD-t 这条（跨协议、对我们不利的）赛道上，我们没有战胜任何一个强 SOTA。** Rollout-P4 更弱，战绩更差。

### 5.B 官方 EarthNet2021 ENS（我们的"主场"）— 全量已测，对手精确值待工作流核验

我们最好模型 = **Rollout-P4**（ENS 上全划分 ≥ Direct）：iid **0.150**、ood 0.123、extreme 0.061、seasonal 0.109。

| 对手 | 类型 | 对手 ENS(iid) | ENS胜负 | 来源/置信 |
|---|---|---:|:--:|---|
| **Persistence** | 基线 | **0.209**（本地同 pipeline 全量 4205；ood 0.207 / extreme 0.077 / seasonal 0.218） | ❌**输**（我们最好 0.150；4 划分全输） | 本项目 `officialENS_run1/persistence` |
| ConvLSTM | 学习 | ≈0.28 | ❌**输** | Earthformer论文表, 待核验 |
| PredRNN | **SOTA** | ≈0.29 | ❌**输** | 待核验 |
| Earthformer | **SOTA** | ≈0.32 | ❌**输** | Earthformer NeurIPS'22, 待核验 |
| SGED-ConvLSTM/挑战赛冠军 | **SOTA** | ≈0.32–0.33 | ❌**输** | EarthNet2021 挑战赛, 待核验 |

**EarthNet2021 ENS 战绩（Rollout-P4，我们最好）**：
- **战胜强 SOTA = 0 个**；**全部 4 个划分我们都低于 persistence 基线**（本地同 pipeline 全量：persistence iid 0.209 / ood 0.207 / extreme 0.077 / seasonal 0.218，我们均更低）。
- 根因：ENS 谐波平均被 SSIM 子分（`x^10.3` 幂缩放，重奖结构锐利度）压制，我们预测偏平滑（persistence SSIM 0.149 vs 我们 ~0.06）。
- 🔑 **可写进论文的关键张力**：我们的模型在 **RGBN-MAE / 时序精度上优于 persistence**（skill_vs_persistence≈+0.25），却在 **ENS 上输给一张静态复制**——因为 ENS 的 SSIM 分量重奖锐利/静态结构。这既是"过度平滑"的干净证据，也是对 EarthNetScore 度量本身的合理批评（奖励静态复制胜过时序正确但平滑的预测）。
- ⚠️ 注：本地 persistence ENS 0.209 略低于文献 ~0.26（协议版本 earthnet2021x vs 原版 / persistence 聚合方式差异），但**同 pipeline 对比"我们<persistence"是稳的**；正式论文如需绝对可比，再用官方 `get_ENS` 做一次 parity。
- ⚠️ 精确学习对手 ENS 待核验；方向（我们全输、且 4 划分全低于 persistence）已由全量同 pipeline 实测确定，不会变。

### 5.C 计分板总结（两协议合并，诚实）

| 协议 | 我们最好 | 战胜强 SOTA 数 | 是否过 persistence/climatology 基线 |
|---|---|---|---|
| GreenEarthNet OOD-t (R²/RMSE) | Direct-P4 | **0 / 4** | 过 persistence；≈平 climatology；不及学习基线 |
| 官方 EarthNet2021 ENS | Rollout-P4 | **0 / ~4** | **未过 persistence(ENS)** |

- **两协议下战胜的强 SOTA 都是 0 个**——这是必须如实写入正文的事实。
- 但**有价值的真发现**不依赖"赢 SOTA"：① Direct-vs-Rollout 胜负随协议反转（受控、可诊断）；② 过度平滑是一致的失败机制（ENS-SSIM 与 GreenEarthNet 都指向它）。
- 论文说服力来源 = **诚实计分板 + 内部受控对照 + 机制诊断**，不是"赢了几个 SOTA"。

---

## 6. 结论（随数据更新）

【待全量 iid/ood + published ENS 落地后填写：我们在官方 EarthNet2021 ENS 主场上，相对已发表 ENS 处于什么位置；Direct vs Rollout 在 ENS 协议下的方向是否与 OOD-t 一致；这对主表协议选择与叙事意味着什么。】
